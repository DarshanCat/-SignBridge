"""Select every available video of a split (up to PER_CLASS per class, seeded), extract sampled frames for 16:9 and 4:3 framings.
usage: python select_all.py <val|test> <per_class> [count]    Writes next to this script into <split>/ (samples.json, frames/)."""
import csv
import json
import random
import re
import sys
import zipfile
from pathlib import Path

import cv2
import numpy as np

HERE = Path(__file__).parent
ROOT = Path(r"C:\Users\Darshan\Downloads\MONEY Bank\3d project")
split, per_class = sys.argv[1], int(sys.argv[2])
count_only = len(sys.argv) > 3
OUT = HERE / split
STEP, SEED = 3, 0

rows = [r for r in csv.DictReader(open(ROOT / "data/processed/include_v2/manifest.csv", encoding="utf-8")) if r["split"] == split]
index = {}
for z in sorted((ROOT / "zips_keep").glob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            m = re.match(r".*/\d+\.\s*([^/]+)/([^/]+)\.(?:MOV|mov|mp4|MP4)$", n)
            if m:
                index[(m.group(1).strip().lower(), m.group(2))] = (z.name, n)
by_class = {}
for r in rows:
    mm = re.match(r"(?:s_)?[0-9a-f]+_(.*)\.npy$", Path(r["path"]).name)
    if not mm:
        continue
    hit = index.get((r["label"].strip().lower(), mm.group(1)))
    if hit:
        by_class.setdefault(r["label"], []).append((Path(r["path"]).name, mm.group(1), hit))
print(split, "rows", len(rows), "with video", sum(len(v) for v in by_class.values()), "classes", len(by_class), flush=True)
rng = random.Random(SEED)
picked = []
for c in sorted(by_class):
    items = sorted(by_class[c])
    rng.shuffle(items)
    for npy, stem, (zname, member) in items[:per_class]:
        picked.append({"id": f"{split[0]}{len(picked):03d}", "label": c, "npy": npy, "stem": stem, "zip": zname, "member": member})
print("selected", len(picked), flush=True)
if count_only:
    sys.exit(0)


def letterbox(frame, W=640, H=480):
    h, w = frame.shape[:2]
    s = min(W / w, H / h)
    nw, nh = int(round(w * s)), int(round(h * s))
    small = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((H, W, 3), dtype=np.uint8)
    y0, x0 = (H - nh) // 2, (W - nw) // 2
    out[y0 : y0 + nh, x0 : x0 + nw] = small
    return out


(OUT / "videos").mkdir(parents=True, exist_ok=True)
for fr in ("16x9", "4x3"):
    (OUT / "frames" / fr).mkdir(parents=True, exist_ok=True)
for s in picked:
    src = OUT / "videos" / f"{s['id']}.mov"
    with zipfile.ZipFile(ROOT / "zips_keep" / s["zip"]) as zf, zf.open(s["member"]) as fi:
        src.write_bytes(fi.read())
    cap = cv2.VideoCapture(str(src))
    i = n = 0
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        if i % STEP == 0:
            for fr, img in (("16x9", cv2.resize(bgr, (1280, 720), interpolation=cv2.INTER_AREA)), ("4x3", letterbox(bgr))):
                d = OUT / "frames" / fr / s["id"]
                d.mkdir(exist_ok=True)
                cv2.imwrite(str(d / f"{n:03d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            n += 1
        i += 1
    s["video_frames"], s["sampled_frames"] = i, n
    cap.release()
    src.unlink()
json.dump({"seed": SEED, "step": STEP, "per_class": per_class, "samples": picked}, open(OUT / "samples.json", "w"), indent=1)
print("done", len(picked), flush=True)
