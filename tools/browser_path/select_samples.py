"""Pick up to 100 test-split INCLUDE samples (one per class, seeded), find their videos in zips_keep, extract them, and write sampled JPEG frames
for two framings: 16:9 (1280x720) and 4:3 letterboxed (640x480). Everything stays in the scratchpad (never under data/)."""
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
STEP = 3  # every third video frame, about 8 to 10 frames per second like the live path
N = 100
SEED = 0

rows = [r for r in csv.DictReader(open(ROOT / "data/processed/include_v2/manifest.csv", encoding="utf-8")) if r["split"] == "test"]
index = {}  # (label lower, stem) -> (zip, member)
for z in sorted((ROOT / "zips_keep").glob("*.zip")):
    with zipfile.ZipFile(z) as zf:
        for n in zf.namelist():
            m = re.match(r".*/\d+\.\s*([^/]+)/([^/]+)\.(?:MOV|mov|mp4|MP4)$", n)
            if m:
                index[(m.group(1).strip().lower(), m.group(2))] = (z.name, n)

by_class = {}
missing = 0
for r in rows:
    mm = re.match(r"(?:s_)?[0-9a-f]+_(.*)\.npy$", Path(r["path"]).name)
    if not mm:
        print("unparsed", r["path"])
        continue
    stem = mm.group(1)
    hit = index.get((r["label"].strip().lower(), stem))
    if not hit:
        missing += 1
        continue
    by_class.setdefault(r["label"], []).append((Path(r["path"]).name, stem, hit))
print("test rows", len(rows), "with video in zips_keep", sum(len(v) for v in by_class.values()), "classes", len(by_class), "no video", missing)

rng = random.Random(SEED)
classes = sorted(by_class)
rng.shuffle(classes)
picked = []
for c in classes[:N]:
    npy, stem, (zname, member) = rng.choice(sorted(by_class[c]))
    picked.append({"id": f"s{len(picked):03d}", "label": c, "npy": npy, "stem": stem, "zip": zname, "member": member})

(HERE / "videos").mkdir(exist_ok=True)
for fr in ("16x9", "4x3"):
    (HERE / "frames" / fr).mkdir(parents=True, exist_ok=True)


def letterbox(frame, W=640, H=480):
    h, w = frame.shape[:2]
    s = min(W / w, H / h)
    nw, nh = int(round(w * s)), int(round(h * s))
    small = cv2.resize(frame, (nw, nh), interpolation=cv2.INTER_AREA)
    out = np.zeros((H, W, 3), dtype=np.uint8)
    y0, x0 = (H - nh) // 2, (W - nw) // 2
    out[y0 : y0 + nh, x0 : x0 + nw] = small
    return out


for s in picked:
    src = HERE / "videos" / f"{s['id']}.mov"
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
                d = HERE / "frames" / fr / s["id"]
                d.mkdir(exist_ok=True)
                cv2.imwrite(str(d / f"{n:03d}.jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
            n += 1
        i += 1
    s["video_frames"], s["sampled_frames"], s["size"] = i, n, [int(cap.get(3)), int(cap.get(4))]
    cap.release()
    src.unlink()
    print(s["id"], s["label"], s["video_frames"], s["sampled_frames"], s["size"], flush=True)
json.dump({"seed": SEED, "step": STEP, "samples": picked}, open(HERE / "samples.json", "w"), indent=1)
