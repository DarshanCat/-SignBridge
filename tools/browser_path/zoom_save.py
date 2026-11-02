"""Python MediaPipe landmarks of validation videos shrunk toward the image centre; saved so every model can be evaluated on them.
usage: python zoom_save.py <part> <parts>   (videos part::parts of the first 60 of bpv/samples.json)"""
import json
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

sys.path.insert(0, r"C:\Users\Darshan\Downloads\MONEY Bank\3d project\backend")
from training.video_features import results_to_frame  # noqa: E402

HERE = Path(__file__).parent
BPV = HERE.parent / "bpv"
part, parts = int(sys.argv[1]), int(sys.argv[2])
samples = json.load(open(BPV / "samples.json"))["samples"][:60][part::parts]
(HERE / "zoom").mkdir(exist_ok=True)
for s in samples:
    files = sorted((BPV / "frames" / "16x9" / s["id"]).glob("*.jpg"))
    for f in (1.0, 0.8, 0.6, 0.45):
        out = HERE / "zoom" / f"{s['id']}_{f}.json"
        if out.exists():
            continue
        frames = []
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as h:
            for p in files:
                img = cv2.imread(str(p))
                if f != 1.0:
                    small = cv2.resize(img, (int(1280 * f), int(720 * f)), interpolation=cv2.INTER_AREA)
                    canvas = np.zeros_like(img)
                    y0, x0 = (720 - small.shape[0]) // 2, (1280 - small.shape[1]) // 2
                    canvas[y0 : y0 + small.shape[0], x0 : x0 + small.shape[1]] = small
                    img = canvas
                frames.append(results_to_frame(h.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))).model_dump())
        json.dump({"id": s["id"], "label": s["label"], "factor": f, "frames": frames}, open(out, "w"))
    print(s["id"], flush=True)
