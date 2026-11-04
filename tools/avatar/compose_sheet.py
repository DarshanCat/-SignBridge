"""Compose docs/screenshots/avatar_retarget/raw/{before,after}_<sign>_<k>.png into one frame sheet (rows = signs, columns = before, after).
usage (repository root): python -I tools/avatar/compose_sheet.py hello doctor hospital book market"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw

D = Path(__file__).resolve().parents[2] / "docs" / "screenshots" / "avatar_retarget"
signs = sys.argv[1:] or ["hello", "doctor", "hospital", "book", "market"]
cols = [("before", 0), ("before", 1), ("after", 0), ("after", 1)]
W = 380
head = 34
imgs = {(s, c, k): Image.open(D / "raw" / f"{c}_{s}_{k}.png").convert("RGB") for s in signs for c, k in cols}
h = int(next(iter(imgs.values())).height * W / next(iter(imgs.values())).width)
sheet = Image.new("RGB", (W * 4 + 90, head + h * len(signs)), "white")
d = ImageDraw.Draw(sheet)
for j, (c, k) in enumerate(cols):
    d.text((90 + j * W + 8, 10), f"{'before (clip tracks)' if c == 'before' else 'after (retargeter, source skeleton at left)'}, frame {k + 1}", fill="black")
for i, s in enumerate(signs):
    d.text((8, head + i * h + h // 2), s.upper(), fill="black")
    for j, (c, k) in enumerate(cols):
        sheet.paste(imgs[(s, c, k)].resize((W, h)), (90 + j * W, head + i * h))
out = D / "frame_sheet.jpg"
sheet.save(out, quality=82)
print(out, sheet.size)
