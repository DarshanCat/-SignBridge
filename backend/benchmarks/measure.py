"""Latency measurements for the components that can be measured on this machine. Run from backend/:

    python -m benchmarks.measure --api http://localhost:8010 --out ..\\docs\\benchmarks\\latest.json

Measured only when possible, and each result records its method and sample count:
  * preprocessing   - app.recognition.landmarks.process_sequence on a 60-frame synthetic landmark sequence
  * api_roundtrip   - HTTP POST /api/landmarks/extract (same payload) and GET /api/health against a running server
  * mediapipe_python_blank_frame - Python MediaPipe Holistic on a blank frame (NO person: a lower bound, not
                       representative of real extraction; browser extraction needs a real camera)
  * model_inference - only if a real trained model exists in backend/models; otherwise reported as not measured
Synthetic payloads are used for timing only; nothing here measures recognition quality.
"""

import argparse
import json
import platform
import statistics
import subprocess
import sys
import time
from pathlib import Path

import httpx
import numpy as np

from app.core.config import get_settings
from app.recognition.landmarks import process_sequence
from app.recognition.model_status import get_model_status
from app.schemas.landmarks import LandmarkFrame, LandmarkSequenceRequest

SEQ_FRAMES = 60
WARMUP = 10


def stats(samples_ms: list[float]) -> dict:
    s = sorted(samples_ms)
    return {
        "n": len(s),
        "mean_ms": round(statistics.fmean(s), 3),
        "median_ms": round(s[len(s) // 2], 3),
        "p95_ms": round(s[min(len(s) - 1, int(len(s) * 0.95))], 3),
        "min_ms": round(s[0], 3),
        "max_ms": round(s[-1], 3),
    }


def timeit(fn, n: int) -> list[float]:
    for _ in range(WARMUP):
        fn()
    out = []
    for _ in range(n):
        t = time.perf_counter()
        fn()
        out.append((time.perf_counter() - t) * 1000)
    return out


def synthetic_frames() -> list[dict]:
    pose = [{"x": 0.5, "y": 0.5, "z": 0.0}] * 33
    pose[11], pose[12] = {"x": 0.4, "y": 0.4, "z": 0.0}, {"x": 0.6, "y": 0.4, "z": 0.0}
    hand = [{"x": 0.3, "y": 0.6, "z": 0.0}] * 21
    return [{"pose": pose, "left_hand": hand, "right_hand": hand}] * SEQ_FRAMES


def hardware() -> dict:
    cpu = subprocess.run(
        ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_Processor).Name"],
        capture_output=True, text=True, check=False,
    ).stdout.strip() or platform.processor()
    return {"cpu": cpu, "platform": platform.platform(), "python": platform.python_version()}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--api", default="http://localhost:8000")
    p.add_argument("--n", type=int, default=100)
    p.add_argument("--out", type=Path)
    a = p.parse_args()

    frames = synthetic_frames()
    req = LandmarkSequenceRequest(frames=[LandmarkFrame.model_validate(f) for f in frames])
    results: dict = {"hardware": hardware(), "samples_per_measurement": a.n, "warmup_runs": WARMUP}
    results["preprocessing_60_frames"] = {
        "method": "process_sequence() in-process, synthetic landmarks", **stats(timeit(lambda: process_sequence(req), a.n)),
    }

    try:
        with httpx.Client(base_url=a.api, timeout=10) as c:
            payload = {"frames": frames}
            results["api_health_roundtrip"] = {
                "method": "GET /api/health over HTTP to a running uvicorn", **stats(timeit(lambda: c.get("/api/health"), a.n)),
            }
            results["api_landmarks_extract_roundtrip"] = {
                "method": "POST /api/landmarks/extract, 60 synthetic frames, includes JSON encode/decode",
                "payload_bytes": len(json.dumps(payload)),
                **stats(timeit(lambda: c.post("/api/landmarks/extract", json=payload).raise_for_status(), a.n)),
            }
    except httpx.HTTPError as exc:
        results["api_roundtrip"] = {"measured": False, "reason": f"server not reachable at {a.api}: {exc}"}

    try:
        import cv2
        import mediapipe as mp

        blank = cv2.cvtColor(np.zeros((480, 640, 3), np.uint8), cv2.COLOR_BGR2RGB)
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as h:
            results["mediapipe_python_blank_frame"] = {
                "method": "Python Holistic (complexity 0) on a blank 640x480 frame; no person, lower bound only",
                **stats(timeit(lambda: h.process(blank), min(a.n, 100))),
            }
    except Exception as exc:  # noqa: BLE001 - report instead of failing the whole run
        results["mediapipe_python_blank_frame"] = {"measured": False, "reason": str(exc)}

    status = get_model_status(get_settings().model_dir)
    if status.loaded:
        from app.recognition.inference import get_recognizer

        rec = get_recognizer(get_settings().model_dir)
        feats = np.array(process_sequence(req).features, dtype=np.float32)
        results["model_inference"] = {
            "method": "SignRecognizer.predict on one 60-frame sequence, CPU, real trained model",
            "classes": status.classes, **stats(timeit(lambda: rec.predict(feats), a.n)),
        }
    else:
        results["model_inference"] = {"measured": False, "reason": f"no real model: {status.state}"}
    results["end_to_end"] = {"measured": False, "reason": "needs a real camera, a real model and in-browser extraction"}

    text = json.dumps(results, indent=2)
    print(text)
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
