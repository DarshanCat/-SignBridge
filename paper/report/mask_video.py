"""Make a fake-camera video (y4m, 1280x720) from an INCLUDE video with the head hidden by a coarse mosaic, so that screenshots of the app in the report
show a landmark overlay on a body but no recognizable face. The output stays outside the repository.

    python paper/report/mask_video.py <input video> <output .y4m>
"""
import sys
from pathlib import Path

import cv2
import mediapipe as mp
import numpy as np

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
cap = cv2.VideoCapture(str(src))
fps = cap.get(cv2.CAP_PROP_FPS) or 25.0
W, H = 1280, 720
n = 0
with mp.solutions.pose.Pose(static_image_mode=False, model_complexity=0) as pose, dst.open("wb") as f:
    f.write(f"YUV4MPEG2 W{W} H{H} F{int(round(fps * 1000))}:1000 Ip A1:1 C420jpeg\n".encode())
    last = None
    while True:
        ok, bgr = cap.read()
        if not ok:
            break
        img = cv2.resize(bgr, (W, H), interpolation=cv2.INTER_AREA)
        r = pose.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        if r.pose_landmarks:
            lm = r.pose_landmarks.landmark
            sw = abs(lm[11].x - lm[12].x) * W
            last = (lm[0].x * W, lm[0].y * H, max(sw * 0.75, 40))
        if last:
            cx, cy, half = last
            x0, x1 = int(max(cx - half, 0)), int(min(cx + half, W))
            y0, y1 = int(max(cy - half * 1.15, 0)), int(min(cy + half * 1.0, H))
            if x1 > x0 and y1 > y0:
                roi = img[y0:y1, x0:x1]
                small = cv2.resize(roi, (4, 5), interpolation=cv2.INTER_AREA)  # mosaic of 4 by 5 blocks: a head shaped blob, no face
                img[y0:y1, x0:x1] = cv2.resize(small, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
        f.write(b"FRAME\n")
        f.write(cv2.cvtColor(img, cv2.COLOR_BGR2YUV_I420).tobytes())
        n += 1
print(n, "frames written to", dst)
