"""Extract the face block (eyebrows, eyes, mouth: 50 points) for every INCLUDE sample already in the v2 manifest. Run from backend/:

    python -m training.face_stream --parts ..\\data\\processed\\include\\_parts ..\\data\\processed\\include_v2\\_parts_supplement ^
        --local-zips ..\\zips_keep ..\\data\\raw\\include\\zips --work ..\\data\\raw\\include\\face_work --out ..\\data\\processed\\face_v1 --workers 12

Each video is run through MediaPipe Holistic again with the SAME frame rule as the first extraction (stride, frames without a pose dropped), the body
block that comes out is compared with the stored feature file (they must be equal), and only the face block is written, as <out>/<stored name>.npy
with shape (T, 150). The stored features are never touched. Zips that exist locally (zips_keep, data/raw/include/zips) are read in place and never
deleted; a zip that is not local is downloaded one at a time into <work>/zips and deleted after it is processed. Resumable: a finished zip has
<out>/_parts/<zip>.csv and is skipped; a zip that was interrupted is simply done again.
"""

import argparse
import csv
import shutil
import sys
import time
import zipfile
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from pathlib import Path

import httpx
import numpy as np

from training.include_stream import RECORD_API, VIDEO_RE, download

FIELDS = ["member", "npy", "status", "frames", "stored_frames", "body_max_abs_diff", "face_frames_with_face", "message"]


def read_rows(parts_dirs: list[Path]) -> dict[str, list[dict]]:
    """zip stem -> rows (member, npy) with a feature file, from the part records of the first run and of the supplement run."""
    out: dict[str, list[dict]] = {}
    for d in parts_dirs:
        for p in sorted(d.glob("*.csv")):
            with p.open(newline="", encoding="utf-8") as f:
                out.setdefault(p.stem, []).extend(r for r in csv.DictReader(f) if r["npy"])
    return out


def _job(args: tuple[str, str, str, int]) -> dict:
    video, stored, out_npy, stride = args
    import cv2

    cv2.setNumThreads(1)
    from training.data import DatasetError
    from training.video_features import video_to_features_face

    row = {"npy": Path(stored).name, "status": "", "frames": 0, "stored_frames": 0, "body_max_abs_diff": "", "face_frames_with_face": 0, "message": ""}
    try:
        body, face = video_to_features_face(Path(video), stride)
    except DatasetError as exc:
        row.update(status="error", message=str(exc))
        return row
    old = np.load(stored)
    row.update(frames=int(body.shape[0]), stored_frames=int(old.shape[0]), face_frames_with_face=int(face.any(axis=1).sum()))
    if body.shape != old.shape:
        row.update(status="frame_mismatch", message=f"re-extraction gave {body.shape}, stored {old.shape}")
        return row
    diff = float(np.abs(body - old).max())
    row["body_max_abs_diff"] = f"{diff:.6g}"
    np.save(out_npy, face.astype(np.float32))
    row["status"] = "ok" if diff <= 1e-3 else "body_differs"
    return row


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--parts", type=Path, nargs="+", required=True)
    p.add_argument("--stored", type=Path, nargs="+", default=[Path("..") / "data" / "processed" / "include", Path("..") / "data" / "processed" / "include_v2"],
                   help="folders that hold the stored feature files (searched in order)")
    p.add_argument("--local-zips", type=Path, nargs="*", default=[])
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--workers", type=int, default=8)
    p.add_argument("--stride", type=int, default=2)
    p.add_argument("--only", help="process just this zip (trial run)")
    a = p.parse_args()

    rows_by_zip = read_rows(a.parts)
    files = [f for f in httpx.get(RECORD_API, timeout=30).json()["files"] if f["key"].endswith(".zip")]
    files = sorted((f for f in files if Path(f["key"]).stem in rows_by_zip and (not a.only or f["key"] == a.only)), key=lambda f: f["key"])
    parts = a.out / "_parts"
    parts.mkdir(parents=True, exist_ok=True)
    (a.work / "zips").mkdir(parents=True, exist_ok=True)
    todo = [f for f in files if not (parts / f"{Path(f['key']).stem}.csv").exists()]
    print(f"{len(files)} zips with samples, {len(files) - len(todo)} already done, {len(todo)} to go", flush=True)

    def local(f: dict) -> Path | None:
        for d in a.local_zips:
            c = d / f["key"]
            if c.is_file() and c.stat().st_size == f["size"]:
                return c
        return None

    def stored_path(name: str) -> Path:
        for d in a.stored:
            if (d / name).is_file():
                return d / name
        raise FileNotFoundError(name)

    total_t0 = time.time()
    with ThreadPoolExecutor(max_workers=1) as dl, ProcessPoolExecutor(max_workers=a.workers) as pool:
        pending: dict[str, object] = {}

        def fetch(f: dict) -> Path:
            if (c := local(f)) is not None:
                return c
            dest = a.work / "zips" / f["key"]
            download(f["links"]["self"], dest, f["size"])
            return dest

        if todo:
            pending[todo[0]["key"]] = dl.submit(fetch, todo[0])
        for n, f in enumerate(todo):
            key, stem = f["key"], Path(f["key"]).stem
            zpath = pending.pop(key).result()
            if n + 1 < len(todo):  # one download at a time: the next zip downloads while this one is processed
                pending[todo[n + 1]["key"]] = dl.submit(fetch, todo[n + 1])
            free = shutil.disk_usage(a.work).free
            print(f"[{key}] ready ({'local' if local(f) else 'downloaded'}), free disk {free / 1e9:.1f} GB", flush=True)
            tmp = a.work / "tmp" / stem
            shutil.rmtree(tmp, ignore_errors=True)
            tmp.mkdir(parents=True)
            want = {r["member"]: r["npy"] for r in rows_by_zip[stem]}
            jobs, missing = [], []
            with zipfile.ZipFile(zpath) as z:
                names = set(z.namelist())
                for member, npy in want.items():
                    if member not in names or not VIDEO_RE.search(member):
                        missing.append(member)
                        continue
                    z.extract(member, tmp)
                    jobs.append((str(tmp / member), str(stored_path(npy)), str(a.out / npy), a.stride))
            t0 = time.time()
            res = list(pool.map(_job, jobs, chunksize=1))
            by_npy = {Path(j[1]).name: m for j, m in zip(jobs, want)}
            for r in res:
                r["member"] = next(m for m, n_ in want.items() if n_ == r["npy"])
            for m in missing:
                res.append({"member": m, "npy": want[m], "status": "video_missing", "frames": 0, "stored_frames": 0, "body_max_abs_diff": "", "face_frames_with_face": 0, "message": "not in the zip"})
            tmp_csv = parts / f"{stem}.csv.tmp"
            with tmp_csv.open("w", newline="", encoding="utf-8") as fh:
                w = csv.DictWriter(fh, fieldnames=FIELDS)
                w.writeheader()
                w.writerows(res)
            tmp_csv.replace(parts / f"{stem}.csv")
            shutil.rmtree(tmp, ignore_errors=True)
            if zpath.parent == a.work / "zips":
                zpath.unlink()  # only zips this run downloaded; the local copies are never deleted
            ok = sum(r["status"] == "ok" for r in res)
            bad = [r["status"] for r in res if r["status"] != "ok"]
            print(f"[{key}] {ok}/{len(res)} ok in {time.time() - t0:.0f}s; not ok: {sorted(set(bad)) or 'none'}", flush=True)
    print(f"finished in {(time.time() - total_t0) / 60:.1f} min", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
