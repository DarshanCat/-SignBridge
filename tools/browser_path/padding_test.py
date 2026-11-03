"""Does letterbox padding explain the residual 4:3 loss? Python MediaPipe on the sampled 1280x720 frames of the 100 VALIDATION videos (baseline CNN, seed 0,
live threshold 0.7, same landmark path as the app: vertical rescale to 16:9, process_sequence, recognizer). Validation only; no test video is touched.

conditions (every picture shape except the first two is rescaled with y' = y (16/9)/(w/h))
  native16x9   1280x720, no padding
  small16x9    640x360, no padding: the resolution of the letterboxed content
  lb4x3_black  16:9 content 640x360 centred with black bars in a 640x480 picture (what the app and the earlier study used)
  lb4x3_edge   the same picture with the bars filled by replicating the edge rows instead of black (padding that is not black)
  lb1x1_black  the same content in a 640x640 picture: more black padding, same resolution
  crop4x3      centre crop of the 16:9 frame to 4:3 (960x720), resized to 640x480: unpadded 4:3 (the sides of the picture are lost)
usage (from the repository root, backend venv):  backend\\.venv\\Scripts\\python tools\\browser_path\\padding_test.py <dir with frames/16x9 and samples.json> <out.json>
"""
import json
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))

from app.recognition.inference import get_recognizer  # noqa: E402
from app.recognition.landmarks import process_sequence  # noqa: E402
from app.schemas.landmarks import LandmarkFrame, LandmarkSequenceRequest  # noqa: E402
from training.video_features import results_to_frame  # noqa: E402

BPV, OUT = Path(sys.argv[1]), Path(sys.argv[2])
TAU = 0.7
rec = get_recognizer(ROOT / "data" / "models_v2" / "cnn")
samples = json.load(open(BPV / "samples.json"))["samples"]


def letterbox(img, w, h, fill):
    small = cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA)
    top = (h - 360) // 2
    if fill == "black":
        canvas = np.zeros((h, w, 3), dtype=np.uint8)
        canvas[top : top + 360, (w - 640) // 2 : (w - 640) // 2 + 640] = small
        return canvas
    return cv2.copyMakeBorder(small, top, h - 360 - top, 0, 0, cv2.BORDER_REPLICATE)


CONDITIONS = {
    "native16x9": (lambda im: im, 16 / 9),
    "small16x9": (lambda im: cv2.resize(im, (640, 360), interpolation=cv2.INTER_AREA), 16 / 9),
    "lb4x3_black": (lambda im: letterbox(im, 640, 480, "black"), 4 / 3),
    "lb4x3_edge": (lambda im: letterbox(im, 640, 480, "edge"), 4 / 3),
    "lb1x1_black": (lambda im: letterbox(im, 640, 640, "black"), 1.0),
    "crop4x3": (lambda im: cv2.resize(im[:, 160:1120], (640, 480), interpolation=cv2.INTER_AREA), 4 / 3),
}


def rescale(frames, aspect):
    k = (16 / 9) / aspect
    if abs(k - 1) < 1e-9:
        return frames

    def pts(p):
        return None if p is None else [q.model_copy(update={"y": q.y * k}) for q in p]

    return [LandmarkFrame(pose=pts(f.pose), left_hand=pts(f.left_hand), right_hand=pts(f.right_hand)) for f in frames]


def classify(frames):
    buf, miss = [], 0
    for f in frames:
        miss = 0 if f.pose else miss + 1
        if miss > 15:
            buf = []
            continue
        buf = (buf + [f])[-60:]
    if not buf:
        return None, 0.0
    proc = process_sequence(LandmarkSequenceRequest(frames=buf))
    if not proc.usable:
        return None, 0.0
    rows = np.array([f for f, r in zip(proc.features, proc.frame_reports) if r.valid], dtype=np.float32)
    top = rec.predict(rows, top_k=1)[0]
    return top.label, float(top.confidence)


result = {"tau": TAU, "n": len(samples), "conditions": {}}
for name, (tf, aspect) in CONDITIONS.items():
    rows, hand_frames, frames_total = [], 0, 0
    for s in samples:
        frames = []
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as h:
            for p in sorted((BPV / "frames" / "16x9" / s["id"]).glob("*.jpg")):
                img = tf(cv2.imread(str(p)))
                frames.append(results_to_frame(h.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))))
        frames_total += len(frames)
        hand_frames += sum(1 for f in frames if f.left_hand or f.right_hand)
        label, conf = classify(rescale(frames, aspect))
        rows.append({"id": s["id"], "label": s["label"], "top": label, "conf": conf, "correct": label is not None and label.lower() == s["label"].lower()})
    acc = sum(1 for r in rows if r["conf"] >= TAU and r["correct"]) / len(rows)
    wa = sum(1 for r in rows if r["conf"] >= TAU and not r["correct"]) / len(rows)
    result["conditions"][name] = {"rows": rows, "accuracy": acc, "wrong_accepted": wa, "unrecognized": 1 - acc - wa, "hand_frame_rate": hand_frames / frames_total,
                                  "top1": sum(1 for r in rows if r["correct"]) / len(rows)}
    print(name, f"acc {acc:.2f} wrong-accepted {wa:.2f} unrec {1 - acc - wa:.2f} top1 {result['conditions'][name]['top1']:.2f} hand-frames {hand_frames / frames_total:.2f}", flush=True)
    json.dump(result, open(OUT, "w"))
print("done", flush=True)
