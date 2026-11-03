"""Copy the captured tab screenshots into paper/report/figures (the English to Sign page is cropped above the long vocabulary list) and build the montage of
avatar frames across one sentence.   python paper/report/finalize_images.py <screenshots folder> <avatar frames folder>"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

shots, frames = Path(sys.argv[1]), Path(sys.argv[2])
OUT = Path(__file__).parent / "figures"
OUT.mkdir(exist_ok=True)

for src, dst, crop in [
    ("tab_conversation.png", "screenshot_conversation.png", None),
    ("tab_sign_to_english.png", "screenshot_sign_to_english.png", None),
    ("tab_english_to_sign.png", "screenshot_english_to_sign.png", 1010),
    ("tab_record_sign.png", "screenshot_record_sign.png", None),
    ("tab_landmark_check.png", "screenshot_landmark_check.png", None),
]:
    im = Image.open(shots / src).convert("RGB")
    if crop:
        im = im.crop((0, 0, im.width, min(crop, im.height)))
    im.save(OUT / dst, optimize=True)
    print(dst, im.size)

files = sorted(frames.glob("f*.png"))
# the sentence is signed while the pose differs from the final rest pose: take 8 frames evenly spaced over that stretch
import numpy as np

arr = [np.asarray(Image.open(f).convert("L"), dtype=np.float32) for f in files]
rest = arr[-1]
diff = np.array([np.abs(a - rest).mean() for a in arr])
active = np.where(diff > 0.25 * diff.max())[0]
lo, hi = (int(active[0]), int(active[-1])) if len(active) else (0, len(files) - 1)
idx = [int(round(lo + i * (hi - lo) / 7)) for i in range(8)]
tiles = [Image.open(files[i]).convert("RGB") for i in idx]
w, h = tiles[0].size
scale = 330 / w
tiles = [t.resize((330, int(h * scale))) for t in tiles]
tw, th = tiles[0].size
sheet = Image.new("RGB", (4 * tw + 5 * 6, 2 * (th + 22) + 6), (255, 255, 255))
d = ImageDraw.Draw(sheet)
try:
    font = ImageFont.truetype("arial.ttf", 13)
except OSError:
    font = ImageFont.load_default()
for k, (t, i) in enumerate(zip(tiles, idx)):
    x = 6 + (k % 4) * (tw + 6)
    y = 6 + (k // 4) * (th + 22)
    sheet.paste(t, (x, y + 18))
    d.text((x + 2, y), f"frame {k + 1} of 8", fill=(30, 41, 59), font=font)
sheet.save(OUT / "avatar_frames_sentence.png", optimize=True)
print("avatar_frames_sentence.png", sheet.size, "from", len(files), "captured frames")
