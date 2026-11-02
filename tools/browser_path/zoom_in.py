"""Signer size ABOVE the dataset range: validation videos cropped toward the signer (centre of the crop = median shoulder midpoint of the uncropped
run) and resized back to 1280x720, Python MediaPipe, baseline CNN, live threshold 0.7. A crop to a fraction c of the width and height makes the
shoulders 1/c times wider. Also records how often a hand is found, because a tight crop can cut the hands off.
usage: python zoom_in.py   (validation corpus bpv: first 30 videos, 16:9 frames; zoom/<id>_1.0.json from zoom_save.py gives the signer centre)"""
import json
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

BACKEND = Path(r"C:\Users\Darshan\Downloads\MONEY Bank\3d project\backend")
sys.path.insert(0, str(BACKEND))
HERE = Path(__file__).parent
BPV = HERE.parent / "bpv"

from app.recognition.inference import get_recognizer  # noqa: E402
from app.recognition.landmarks import process_sequence  # noqa: E402
from app.schemas.landmarks import LandmarkFrame, LandmarkSequenceRequest  # noqa: E402
from training.video_features import results_to_frame  # noqa: E402

rec = get_recognizer(BACKEND.parent / "data" / "models_v2" / "cnn")
samples = json.load(open(BPV / "samples.json"))["samples"][:30]
CROPS = (0.75, 0.6, 0.5)
rows = []
for s in samples:
    base = json.load(open(HERE / "zoom" / f"{s['id']}_1.0.json"))["frames"]
    mids = [((f["pose"][11]["x"] + f["pose"][12]["x"]) / 2, (f["pose"][11]["y"] + f["pose"][12]["y"]) / 2) for f in base if f["pose"]]
    cx, cy = float(np.median([m[0] for m in mids])), float(np.median([m[1] for m in mids]))
    files = sorted((BPV / "frames" / "16x9" / s["id"]).glob("*.jpg"))
    for c in CROPS:
        cw, ch = int(1280 * c), int(720 * c)
        x0 = int(min(max(cx * 1280 - cw / 2, 0), 1280 - cw))
        y0 = int(min(max(cy * 720 - ch * 0.4, 0), 720 - ch))  # shoulders a little above the centre so that the raised hands stay in
        frames = []
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as h:
            for p in files:
                img = cv2.imread(str(p))[y0 : y0 + ch, x0 : x0 + cw]
                img = cv2.resize(img, (1280, 720), interpolation=cv2.INTER_LINEAR)
                frames.append(results_to_frame(h.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))))
        widths = [abs(f.pose[11].x - f.pose[12].x) for f in frames if f.pose]
        buf, miss = [], 0
        for f in frames:
            miss = 0 if f.pose else miss + 1
            if miss > 15:
                buf = []
                continue
            buf = (buf + [f])[-60:]
        out = {"id": s["id"], "label": s["label"], "crop": c, "width": float(np.median(widths)) if widths else None,
               "pose_rate": len(widths) / max(len(frames), 1), "hand_rate": sum((f.left_hand or f.right_hand) is not None for f in frames) / max(len(frames), 1)}
        proc = process_sequence(LandmarkSequenceRequest(frames=buf)) if buf else None
        if proc is not None and proc.usable:
            r = np.array([f for f, rp in zip(proc.features, proc.frame_reports) if rp.valid], dtype=np.float32)
            top = rec.predict(r, top_k=1)[0]
            out.update(top=top.label, conf=round(top.confidence, 4), accepted=top.confidence >= 0.7, correct=top.label.lower() == s["label"].lower())
        else:
            out.update(top=None, conf=0.0, accepted=False, correct=False)
        rows.append(out)
    print(s["id"], flush=True)
json.dump(rows, open(HERE / "zoom_in.json", "w"))
for c in CROPS:
    r = [x for x in rows if x["crop"] == c]
    w = [x["width"] for x in r if x["width"]]
    acc = sum(1 for x in r if x["accepted"] and x["correct"]) / len(r)
    wa = sum(1 for x in r if x["accepted"] and not x["correct"]) / len(r)
    print(f"crop {c}: median width {np.median(w):.3f} acc {acc:.2f} wrong-accepted {wa:.2f} hand rate {np.mean([x['hand_rate'] for x in r]):.2f} n {len(r)}")
