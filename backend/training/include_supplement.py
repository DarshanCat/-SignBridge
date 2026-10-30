"""Recover INCLUDE videos that the first streaming run skipped because the authors' lists say .MOV but many zips hold .MP4.

Run from backend/ (reads the old outputs, never modifies them; writes a new folder):

    python -m training.include_supplement --raw ..\\data\\raw\\include --old ..\\data\\processed\\include --new ..\\data\\processed\\include_v2 --logs ..\\data\\raw\\include\\stream.log ...

Matching ignores the file extension. If the full path (without extension) is not listed, a fallback matches category plus file
name when that is unique in the lists; such rows are flagged `filename_fallback` and take the AUTHORS' label and split. Videos
that still match nothing are recorded as skipped, never dropped silently. Only zips that had unmatched videos are fetched.
The new folder gets its own manifest.csv that references the old feature files by relative path, so the old manifest stays intact.
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

from training.include_stream import RECORD_API, SPLIT_FILES, VIDEO_RE, _process, download, label_of

FIELDS = ["member", "npy", "message", "split", "label", "category", "match"]


def stem_key(path: str) -> str:
    return re.sub(r"\.(mov|mp4)$", "", path.strip(), flags=re.I).lower()


def load_listed(split_dir: Path) -> tuple[dict[str, tuple[str, str]], dict[tuple[str, str], list[str]]]:
    """stem key -> (split, original list path); and (category, file stem) -> [stem keys] for the fallback."""
    listed: dict[str, tuple[str, str]] = {}
    for split, name in SPLIT_FILES.items():
        for line in (split_dir / name).read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if VIDEO_RE.search(line):
                listed[stem_key(line)] = (split, line)
    by_name: dict[tuple[str, str], list[str]] = {}
    for key in listed:
        parts = key.split("/")
        by_name.setdefault((parts[0], parts[-1]), []).append(key)
    return listed, by_name


def classify(member: str, listed, by_name, have: set[str]) -> tuple[str, str | None]:
    """Return (decision, listed key): decision is have, stem, filename_fallback or skip."""
    key = stem_key(member)
    if key in have:
        return "have", key
    if key in listed:
        return "stem", key
    parts = key.split("/")
    cands = by_name.get((parts[0], parts[-1]), [])
    cands = [c for c in cands if c not in have]
    if len(cands) == 1:
        return "filename_fallback", cands[0]
    return "skip", None


def affected_zips(logs: list[Path]) -> list[str]:
    seen: dict[str, int] = {}
    for p in logs:
        if p.is_file():
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                m = re.match(r"\[(\S+\.zip)\] done: \d+/\d+ usable, (\d+) videos not in", line)
                if m and m.group(1) not in seen:
                    seen[m.group(1)] = int(m.group(2))
    return sorted(k for k, v in seen.items() if v > 0)


def path_label(member: str, extra_policy: str = "merge") -> str:
    """Class label from the path. A nested folder under the class folder (named Extra in the data) is merged into its parent
    class (approved 2026-10-30, default policy 'merge'); policy 'separate' keeps it as its own label such as 'Bird/Extra'."""
    parts = member.split("/")
    cls = label_of(member)
    if extra_policy == "merge" or len(parts) <= 3:
        return cls
    return f"{cls}/{parts[2]}"


def build_manifest(old: Path, new: Path, extra_policy: str = "merge") -> int:
    rows = []
    for d, rel in ((old, "../" + old.name + "/"), (new, "")):
        pdir = d / ("_parts" if d == old else "_parts_supplement")
        for p in sorted(pdir.glob("*.csv")):
            with p.open(newline="", encoding="utf-8") as f:
                for r in csv.DictReader(f):
                    if r["npy"]:
                        rows.append({**r, "rel": rel + r["npy"]})
    for r in rows:  # labels come from the class folder in the path; filename fallbacks keep the authors' list label
        if r.get("match") != "filename_fallback":
            r["label"] = path_label(r["member"], extra_policy)
    names: dict[str, set[str]] = {}
    for r in rows:
        names.setdefault(r["label"].lower(), set()).add(r["category"])
    with (new / "manifest.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["path", "label", "signer_id", "split"])
        for r in rows:
            label = r["label"] if len(names[r["label"].lower()]) == 1 else f"{r['category']}/{r['label']}"
            w.writerow([r["rel"], label, "unknown", r["split"]])
    info = json.loads((old / "dataset_info.json").read_text(encoding="utf-8"))
    info["notes"] = (
        "Authors' predefined split (AI4Bharat/INCLUDE train_test_paths); no signer IDs published, signer independence unverified. "
        "v2 combines the first run with an extension insensitive supplement; labels and splits come from the authors' lists."
    )
    (new / "dataset_info.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    return len(rows)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--raw", type=Path, required=True)
    p.add_argument("--old", type=Path, required=True)
    p.add_argument("--new", type=Path, required=True)
    p.add_argument("--logs", type=Path, nargs="+", required=True, help="first run logs, used to find the affected zips")
    p.add_argument("--extra-policy", choices=["separate", "merge"], default="merge")
    p.add_argument("--manifest-only", action="store_true", help="only rebuild the v2 manifest from the part records")
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--stride", type=int, default=2)
    p.add_argument("--prefetch", type=int, default=2)
    a = p.parse_args()

    if a.manifest_only:
        print(f"v2 manifest: {build_manifest(a.old, a.new, a.extra_policy)} samples -> {a.new}", flush=True)
        return 0
    listed, by_name = load_listed(a.raw / "splits")
    have: set[str] = set()
    for pf in (a.old / "_parts").glob("*.csv"):
        with pf.open(newline="", encoding="utf-8") as f:
            have.update(stem_key(r["member"]) for r in csv.DictReader(f) if r["npy"])
    zips_needed = affected_zips(a.logs)
    files = {f["key"]: f for f in httpx.get(RECORD_API, timeout=30).json()["files"] if f["key"].endswith(".zip")}
    parts = a.new / "_parts_supplement"
    parts.mkdir(parents=True, exist_ok=True)
    todo = [files[k] for k in zips_needed if not (parts / f"{Path(k).stem}.csv").exists()]
    print(f"{len(have)} videos already processed; {len(zips_needed)} affected zips, {len(todo)} to go", flush=True)
    zdir = a.raw / "zips"
    zdir.mkdir(exist_ok=True)

    with ThreadPoolExecutor(max_workers=a.prefetch) as dl, ProcessPoolExecutor(max_workers=a.workers) as pool:
        fut = {f["key"]: dl.submit(download, f["links"]["self"], zdir / f["key"], f["size"]) for f in todo[: a.prefetch + 1]}
        nxt = a.prefetch + 1
        for f in todo:
            key = f["key"]
            fut[key].result()
            if nxt < len(todo):
                g = todo[nxt]
                fut[g["key"]] = dl.submit(download, g["links"]["self"], zdir / g["key"], g["size"])
                nxt += 1
            tmp = a.raw / "tmp_supplement" / Path(key).stem
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True)
            jobs, rows = [], []
            with zipfile.ZipFile(zdir / key) as z:
                for member in z.namelist():
                    if not VIDEO_RE.search(member):
                        continue
                    decision, lk = classify(member, listed, by_name, have)
                    if decision == "have":
                        continue
                    if decision == "skip":
                        rows.append(dict(member=member, npy="", message="not matched to any listed video", split="", label="", category=member.split("/")[0], match="skip"))
                        continue
                    split, orig = listed[lk]
                    have.add(lk)
                    z.extract(member, tmp)
                    npy = f"s_{hashlib.md5(lk.encode()).hexdigest()[:8]}_{Path(member).stem}.npy"
                    jobs.append((str(tmp / member), str(a.new / npy), member, a.stride, split, label_of(orig), orig.split("/")[0], decision))
            t0 = time.time()
            for job, (member, npy, msg) in zip(jobs, pool.map(_process, [j[:4] for j in jobs], chunksize=1)):
                rows.append(dict(member=member, npy=npy or "", message=msg, split=job[4], label=job[5], category=job[6], match=job[7]))
            with (parts / f"{Path(key).stem}.csv.tmp").open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(rows)
            (parts / f"{Path(key).stem}.csv.tmp").replace(parts / f"{Path(key).stem}.csv")
            shutil.rmtree(tmp, ignore_errors=True)
            (zdir / key).unlink()
            ok = sum(1 for r in rows if r["npy"])
            fb = sum(1 for r in rows if r["match"] == "filename_fallback" and r["npy"])
            skip = sum(1 for r in rows if r["match"] == "skip")
            print(f"[{key}] done: {ok} recovered ({fb} by filename fallback), {skip} unmatched, {time.time() - t0:.0f}s", flush=True)
    print(f"v2 manifest: {build_manifest(a.old, a.new, a.extra_policy)} samples -> {a.new}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
