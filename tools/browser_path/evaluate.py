"""Classify the same 100 videos from five landmark sources with the live code path (process_sequence, then the recognizer and the validation
threshold) and write per-video rows and the summary. Run from backend/ with the backend venv.

sources
  offline      the stored INCLUDE features (data/processed), 16:9 1080p, every frame: the normal evaluation path
  py16x9       Python MediaPipe on the same sampled 1280x720 JPEG frames the browser got
  py4x3        Python MediaPipe on the same sampled 640x480 letterboxed JPEG frames, y rescaled to 16:9 like the browser does
  py4x3_raw    the same Python landmarks without the rescaling
  br16x9       browser MediaPipe (frame stepping) on the 1280x720 frames
  br4x3        browser MediaPipe on the 640x480 letterboxed frames, y rescaled (what the app sends now)
  br4x3_raw    the same browser landmarks without the rescaling (what the app sent before the correction)
"""
import json
import math
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

BACKEND = Path(r"C:\Users\Darshan\Downloads\MONEY Bank\3d project\backend")
sys.path.insert(0, str(BACKEND))
HERE = Path(__file__).parent
ROOT = BACKEND.parent

from app.recognition.inference import get_recognizer  # noqa: E402
from app.recognition.landmarks import process_sequence  # noqa: E402
from app.schemas.landmarks import LandmarkFrame, LandmarkSequenceRequest  # noqa: E402
from app.services.live_service import load_threshold  # noqa: E402
from training.video_features import results_to_frame  # noqa: E402

MODEL_DIR = BACKEND / "models"
rec = get_recognizer(MODEL_DIR)
THRESH, _ = load_threshold(MODEL_DIR, 0.7)
samples = json.load(open(HERE / "samples.json"))["samples"]
MAX_MISSING, BUFFER = 15, 60  # the app's buffer rules (lib/landmarks.ts appendFrame)


def buffer_frames(frames: list[LandmarkFrame]) -> list[LandmarkFrame]:
    buf, miss = [], 0
    for f in frames:
        miss = 0 if f.pose else miss + 1
        if miss > MAX_MISSING:
            buf = []
            continue
        buf = (buf + [f])[-BUFFER:]
    return buf


def classify_rows(rows: np.ndarray) -> dict:
    top = rec.predict(rows)[0]
    ok = top.confidence >= THRESH
    return {"top": top.label, "conf": round(top.confidence, 4), "accepted": ok}


def classify_frames(frames: list[LandmarkFrame]) -> dict:
    buf = buffer_frames(frames)
    if not buf:
        return {"status": "no_pose"}
    proc = process_sequence(LandmarkSequenceRequest(frames=buf))
    if not proc.usable:
        return {"status": "unusable"}
    rows = np.array([f for f, r in zip(proc.features, proc.frame_reports) if r.valid], dtype=np.float32)
    return {"status": "ok", "frames": len(rows), **classify_rows(rows)}


def scale_y(frames: list[LandmarkFrame], k: float) -> list[LandmarkFrame]:
    def pts(p):
        return None if p is None else [q.model_copy(update={"y": q.y * k}) for q in p]

    return [LandmarkFrame(pose=pts(f.pose), left_hand=pts(f.left_hand), right_hand=pts(f.right_hand)) for f in frames]


def python_frames(framing: str, sid: str) -> list[LandmarkFrame]:
    out = []
    d = HERE / "frames" / framing / sid
    with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as h:
        for p in sorted(d.glob("*.jpg")):
            out.append(results_to_frame(h.process(cv2.cvtColor(cv2.imread(str(p)), cv2.COLOR_BGR2RGB))))
    return out


def browser_frames(framing: str, sid: str) -> list[LandmarkFrame]:
    data = json.load(open(HERE / "browser" / framing / f"{sid}.json"))
    return [LandmarkFrame.model_validate(f) for f in data["frames"]]


def stats(frames: list[LandmarkFrame]) -> dict:
    n = max(len(frames), 1)
    return {"frames": len(frames), "pose": sum(f.pose is not None for f in frames) / n, "hand": sum((f.left_hand or f.right_hand) is not None for f in frames) / n}


rows_out = []
for s in samples:
    sid, label = s["id"], s["label"]
    r = {"id": sid, "label": label, "sampled": s["sampled_frames"], "video_frames": s["video_frames"]}
    npy = np.load(ROOT / "data/processed" / ("include_v2" if s["npy"].startswith("s_") else "include") / s["npy"]) if False else None
    for d in ("include", "include_v2"):
        pth = ROOT / "data/processed" / d / s["npy"]
        if pth.exists():
            npy = np.load(pth)
            break
    r["offline"] = classify_rows(npy.astype(np.float32)) if npy is not None else {"status": "no_features"}
    r["offline"].setdefault("status", "ok")
    py169, py43 = python_frames("16x9", sid), python_frames("4x3", sid)
    br169, br43 = browser_frames("16x9", sid), browser_frames("4x3", sid)
    k = (16 / 9) / (4 / 3)
    r["py16x9"], r["py4x3_raw"], r["py4x3"] = classify_frames(py169), classify_frames(py43), classify_frames(scale_y(py43, k))
    r["br16x9"], r["br4x3"], r["br4x3_raw"] = classify_frames(br169), classify_frames(br43), classify_frames(scale_y(br43, 1 / k))
    r["extract"] = {"py16x9": stats(py169), "py4x3": stats(py43), "br16x9": stats(br169), "br4x3": stats(br43)}
    rows_out.append(r)
    print(sid, label, {key: (r[key].get("top"), r[key].get("conf"), r[key].get("status")) for key in ("offline", "py16x9", "br16x9", "py4x3", "br4x3")}, flush=True)
json.dump({"threshold": THRESH, "rows": rows_out}, open(HERE / "results.json", "w"), indent=1)
