"""WCAG 2.1 AA check of the design tokens in frontend/src/app/globals.css (light and dark). Reads the CSS, so the ratios cannot drift from the code.
usage: python -I tools/ui/check_contrast.py        exit code 1 if any pair fails"""
import re
import sys
from pathlib import Path

css = (Path(__file__).resolve().parents[2] / "frontend" / "src" / "app" / "globals.css").read_text(encoding="utf-8")


def block(selector_start):
    i = css.index(selector_start)
    j = css.index("{", i)
    depth, k = 0, j
    while True:
        if css[k] == "{":
            depth += 1
        elif css[k] == "}":
            depth -= 1
            if depth == 0:
                return css[j + 1 : k]
        k += 1


def tokens(body):
    return {m.group(1): tuple(int(x) for x in m.group(2).split()) for m in re.finditer(r"--([a-z0-9-]+):\s*(\d+ \d+ \d+);", body)}


light = tokens(block(":root {"))
dark = dict(light)
dark.update(tokens(block(':root[data-theme="dark"]')))
# the media-query copy must match the explicit dark block
media = tokens(block(":root:not([data-theme=\"light\"])"))
assert all(dark[k] == v for k, v in media.items()), "dark tokens differ between the media query and data-theme"


def lum(c):
    f = lambda v: (v / 255) / 12.92 if v / 255 <= 0.03928 else ((v / 255 + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def ratio(a, b):
    la, lb = lum(a), lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def over(fg, bg, alpha):
    return tuple(round(alpha * f + (1 - alpha) * b) for f, b in zip(fg, bg))


PAIRS = [  # (foreground, background, minimum, what)
    ("ink", "canvas", 4.5, "body text on page"), ("ink", "surface", 4.5, "text on cards"), ("ink", "surface2", 4.5, "text on inset blocks"),
    ("ink2", "canvas", 4.5, "secondary text on page"), ("ink2", "surface", 4.5, "secondary text on cards"), ("ink2", "surface2", 4.5, "secondary text on inset blocks"),
    ("ink2", "field", 4.5, "placeholder text"),
    ("onaccent", "accent", 4.5, "primary button text"), ("accent", "surface", 4.5, "accent as text on cards"), ("accent", "canvas", 4.5, "accent as text on page"),
    ("ink", "soft", 4.5, "selected item text"),
    ("edge", "surface", 3.0, "input and button borders on cards"), ("edge", "canvas", 3.0, "input borders on page"), ("edge", "field", 3.0, "input borders on fields"),
    ("lav", "surface", 3.0, "focus ring on cards"), ("lav", "canvas", 3.0, "focus ring on page"), ("lav", "surface2", 3.0, "focus ring on inset blocks"),
    ("good-fg", "good-bg", 4.5, "good notice"), ("warn-fg", "warn-bg", 4.5, "warning notice"), ("bad-fg", "bad-bg", 4.5, "error notice"), ("info-fg", "info-bg", 4.5, "info notice"),
    ("good-fg", "surface", 4.5, "good text on cards"), ("warn-fg", "surface", 4.5, "warning text on cards"), ("bad-fg", "surface", 4.5, "error text on cards"),
    ("info-fg", "surface", 4.5, "info text on cards"),
]
bad = 0
for name, t in (("light", light), ("dark", dark)):
    print(f"--- {name}")
    for fg, bg, need, what in PAIRS:
        r = ratio(t[fg], t[bg])
        ok = r >= need
        bad += not ok
        print(f"  {'OK  ' if ok else 'FAIL'} {r:5.2f} (need {need})  {what}: {fg} on {bg}")
    # text on the stage gradient sits on a glass card (surface at 0.92 alpha over the gradient)
    for stage in ("stage1", "stage2", "stage3"):
        glass = over(t["surface"], t[stage], 0.92)
        for fg in ("ink", "ink2"):
            r = ratio(t[fg], glass)
            ok = r >= 4.5
            bad += not ok
            print(f"  {'OK  ' if ok else 'FAIL'} {r:5.2f} (need 4.5)  {fg} on glass over {stage}")
print("failures:", bad)
sys.exit(1 if bad else 0)
