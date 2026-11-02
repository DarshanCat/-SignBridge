"""Python-only diagnostics on the same sampled 1280x720 frames: is the 4:3 loss about the aspect ratio or about the smaller picture?
  small16x9   resized to 640x360 (16:9, same resolution as the letterboxed picture), no y correction needed
  crop4x3     centre crop to 4:3 (960x720) resized to 640x480 (a webcam-like fill), y rescaled by 4/3
"""
import json
import sys
from pathlib import Path

import cv2
import mediapipe as mp

HERE = Path(__file__).parent
sys.argv = [sys.argv[0]]
BACKEND = Path(r"C:\Users\Darshan\Downloads\MONEY Bank\3d project\backend")
sys.path.insert(0, str(BACKEND))
from app.recognition.inference import get_recognizer  # noqa: E402
from app.services.live_service import load_threshold  # noqa: E402
from training.video_features import results_to_frame  # noqa: E402

# reuse the helpers of evaluate.py without running it
src = (HERE / "evaluate.py").read_text(encoding="utf-8").split("rows_out = []")[0]
exec(compile(src, "evaluate_helpers", "exec"))

res = {"small16x9": [], "crop4x3": []}
for s in samples:
    d = HERE / "frames" / "16x9" / s["id"]
    for name in res:
        frames = []
        with mp.solutions.holistic.Holistic(static_image_mode=False, model_complexity=0) as h:
            for p in sorted(d.glob("*.jpg")):
                img = cv2.imread(str(p))
                if name == "small16x9":
                    img = cv2.resize(img, (640, 360), interpolation=cv2.INTER_AREA)
                else:
                    img = cv2.resize(img[:, 160:1120], (640, 480), interpolation=cv2.INTER_AREA)
                frames.append(results_to_frame(h.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))))
        if name == "crop4x3":
            frames = scale_y(frames, (16 / 9) / (4 / 3))
        o = classify_frames(frames)
        o["label"] = s["label"]
        res[name].append(o)
for name, lst in res.items():
    n = len(lst)
    corr = sum(1 for o in lst if o.get("accepted") and o["top"].lower() == o["label"].lower())
    wrong = sum(1 for o in lst if o.get("accepted") and o["top"].lower() != o["label"].lower())
    unrec = sum(1 for o in lst if not o.get("accepted"))
    print(name, f"acc {corr/n:.2f} wrong-accepted {wrong/n:.2f} unrec {unrec/n:.2f}")
json.dump(res, open(HERE / "diag.json", "w"))
