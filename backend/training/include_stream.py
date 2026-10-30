"""Stream the INCLUDE ISL dataset from Zenodo into landmark features without keeping the videos. Run from backend/:

    python -m training.include_stream --raw ..\\data\\raw\\include --out ..\\data\\processed\\include --workers 6

Why streaming: the record is 56.75 GB of zip files and Zenodo does not support HTTP range requests, so each zip is
downloaded whole, the videos named in the authors' split lists are extracted, converted to normalized landmark features
(same code path as training/inference), and then the zip and the videos are deleted. Only the small .npy feature files stay.
Resumable: finished zips are recorded in <out>/_parts and skipped on re-run.

Source: https://zenodo.org/records/4010759 (CC BY 4.0 per the record metadata; cite Sridhar et al., ACM MM 2020).
Split lists: https://github.com/AI4Bharat/INCLUDE/tree/master/train_test_paths (predefined; signer independence is NOT verified;
the dataset publishes no signer IDs, so every sample gets signer_id "unknown").
"""

import argparse
import csv
import hashlib
import json
import re
import shutil
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import httpx
import numpy as np

RECORD_API = "https://zenodo.org/api/records/4010759"
VIDEO_RE = re.compile(r"\.(mov|mp4)$", re.I)
SPLIT_FILES = {"train": "include_train.txt", "val": "include_val.txt", "test": "include_test.txt"}


def load_splits(split_dir: Path) -> dict[str, str]:
    """Map lower-cased 'Category/N. Label/file.MOV' to train/val/test."""
    out: dict[str, str] = {}
    for split, name in SPLIT_FILES.items():
        for line in (split_dir / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if VIDEO_RE.search(line):
                out[line.lower()] = split
    return out


def label_of(member: str) -> str:
    """Class name from the class folder (second path component). Nested folders such as 'Extra' belong to their parent class."""
    parts = member.split("/")
    folder = parts[1] if len(parts) > 2 else parts[0]
    m = re.match(r"\s*\d+\.\s*(.*)", folder)
    return (m.group(1) if m else folder).strip()


def _process(args: tuple[str, str, str, int]) -> tuple[str, str | None, str]:
    """Worker: returns (member, npy_name or None, message)."""
    video, npy_path, member, stride = args
    import cv2

    cv2.setNumThreads(1)
    from training.data import DatasetError
    from training.video_features import video_to_features

    try:
        np.save(npy_path, video_to_features(Path(video), stride))
        return member, Path(npy_path).name, ""
    except DatasetError as exc:
        return member, None, str(exc)


def download(url: str, dest: Path, size: int) -> None:
    if dest.exists() and dest.stat().st_size == size:
        return
    part = dest.with_suffix(".part")
    for attempt in range(1, 4):
        try:
            with httpx.stream("GET", url, follow_redirects=True, timeout=60) as r, part.open("wb") as f:
                r.raise_for_status()
                for chunk in r.iter_bytes(1 << 20):
                    f.write(chunk)
            if part.stat().st_size != size:
                raise OSError(f"size mismatch: got {part.stat().st_size}, expected {size}")
            part.replace(dest)
            return
        except (httpx.HTTPError, OSError) as exc:
            print(f"  download attempt {attempt} failed for {dest.name}: {exc}", flush=True)
            time.sleep(5 * attempt)
    raise RuntimeError(f"could not download {dest.name}")


def finalize(out: Path) -> None:
    rows, excl = [], []
    for p in sorted((out / "_parts").glob("*.csv")):
        with p.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                (rows if r["npy"] else excl).append(r)
    names: dict[str, set[str]] = {}
    for r in rows:
        names.setdefault(r["label"].lower(), set()).add(r["category"])
    with (out / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "signer_id", "split"])
        for r in rows:
            label = r["label"] if len(names[r["label"].lower()]) == 1 else f"{r['category']}/{r['label']}"
            w.writerow([r["npy"], label, "unknown", r["split"]])
    with (out / "exclusions.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["member", "reason"])
        w.writerows([[r["member"], r["message"]] for r in excl])
    (out / "dataset_info.json").write_text(
        json.dumps(
            {
                "name": "INCLUDE (Sridhar et al., ACM MM 2020), landmark features extracted with MediaPipe Holistic",
                "language": "ISL",
                "license": "CC BY 4.0 per the Zenodo record metadata; a third-party page states CC BY-NC-SA 4.0 (unresolved). Treat as non-commercial academic use, attribution required, no redistribution",
                "source_url": "https://zenodo.org/records/4010759",
                "consent_required": False,
                "notes": "Predefined authors' split (AI4Bharat/INCLUDE train_test_paths); no signer IDs published, signer independence unverified.",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    print(f"manifest: {len(rows)} samples, {len(excl)} excluded -> {out}", flush=True)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True, help="working dir with splits/ (the authors' split lists)")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--stride", type=int, default=2, help="process every Nth video frame")
    p.add_argument("--only", help="process just this zip name (for a trial run)")
    p.add_argument("--prefetch", type=int, default=2, help="zips downloaded ahead of processing")
    a = p.parse_args()

    splits = load_splits(a.raw / "splits")
    files = [f for f in httpx.get(RECORD_API, timeout=30).json()["files"] if f["key"].endswith(".zip")]
    files.sort(key=lambda f: f["key"])
    if a.only:
        files = [f for f in files if f["key"] == a.only]
    parts = a.out / "_parts"
    parts.mkdir(parents=True, exist_ok=True)
    zips = a.raw / "zips"
    zips.mkdir(parents=True, exist_ok=True)
    todo = [f for f in files if not (parts / f"{Path(f['key']).stem}.csv").exists()]
    print(f"{len(files) - len(todo)} zip(s) already done, {len(todo)} to go", flush=True)

    with ThreadPoolExecutor(max_workers=a.prefetch) as dl, ProcessPoolExecutor(max_workers=a.workers) as pool:
        futures = {}
        for f in todo[: a.prefetch + 1]:
            futures[f["key"]] = dl.submit(download, f["links"]["self"], zips / f["key"], f["size"])
        nxt = a.prefetch + 1
        for f in todo:
            key = f["key"]
            futures[key].result()
            if nxt < len(todo):
                g = todo[nxt]
                futures[g["key"]] = dl.submit(download, g["links"]["self"], zips / g["key"], g["size"])
                nxt += 1
            free = shutil.disk_usage(a.raw).free
            print(f"[{key}] downloaded; processing (free disk {free / 1e9:.1f} GB)", flush=True)
            tmp = a.raw / "tmp" / Path(key).stem
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True)
            jobs, skipped = [], []
            with zipfile.ZipFile(zips / key) as z:
                for member in z.namelist():
                    if not VIDEO_RE.search(member):
                        continue
                    split = splits.get(member.lower())
                    if split is None:
                        skipped.append(member)
                        continue
                    z.extract(member, tmp)
                    npy = f"{hashlib.md5(member.encode()).hexdigest()[:8]}_{Path(member).stem}.npy"
                    jobs.append((str(tmp / member), str(a.out / npy), member, a.stride))
            t0 = time.time()
            rows = []
            for member, npy, msg in pool.map(_process, jobs, chunksize=1):
                rows.append(
                    {
                        "member": member, "npy": npy or "", "message": msg, "split": splits[member.lower()],
                        "label": label_of(member), "category": member.split("/")[0],
                    }
                )
            with (parts / f"{Path(key).stem}.csv.tmp").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=["member", "npy", "message", "split", "label", "category"])
                w.writeheader()
                w.writerows(rows)
            (parts / f"{Path(key).stem}.csv.tmp").replace(parts / f"{Path(key).stem}.csv")
            shutil.rmtree(tmp, ignore_errors=True)
            (zips / key).unlink()
            ok = sum(1 for r in rows if r["npy"])
            print(
                f"[{key}] done: {ok}/{len(rows)} usable, {len(skipped)} videos not in the split lists, "
                f"{time.time() - t0:.0f}s; e.g. unmatched: {skipped[:2]}", flush=True,
            )
    finalize(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
