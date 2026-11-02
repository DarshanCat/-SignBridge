"""Validate the extracted browser landmark files of one corpus (val or test). usage: python validate_corpus.py <val|test> [--delete-bad]
Checks per framing: exactly one readable JSON per video of samples.json and nothing else in the folder, expected keys and aspect, the frame count
equals the number of sampled JPEG frames of that video, every frame has pose / left_hand / right_hand with 33 / 21 landmarks of finite x, y, z or
null, and the video has a body pose in at least 8 frames. Bad files are listed (and deleted with --delete-bad so the harness re-extracts them)."""
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).parent
split = sys.argv[1]
delete = "--delete-bad" in sys.argv
CORPUS = HERE / split
samples = json.load(open(CORPUS / "samples.json"))["samples"]
ids = [s["id"] for s in samples]
EXPECT = {"16x9": 16 / 9, "4x3": 4 / 3}
total_bad = 0


def check_points(pts, n, what):
    if pts is None:
        return None
    if not isinstance(pts, list) or len(pts) != n:
        return f"{what}: {0 if not isinstance(pts, list) else len(pts)} landmarks, expected {n}"
    for p in pts:
        if not isinstance(p, dict) or any(k not in p for k in ("x", "y", "z")):
            return f"{what}: landmark without x, y, z"
        if not all(isinstance(p[k], (int, float)) and math.isfinite(p[k]) for k in ("x", "y", "z")):
            return f"{what}: non-finite value"
    return None


print(f"corpus {split}: {len(ids)} videos in samples.json, {len(set(ids))} unique ids")
for framing in ("16x9", "4x3"):
    d = CORPUS / "browser" / framing
    files = sorted(p.name for p in d.iterdir()) if d.is_dir() else []
    problems = {}
    extra = [f for f in files if not (f.endswith(".json") and f[:-5] in set(ids))]
    for f in extra:
        problems[f] = "unexpected file (partial, temporary or not in samples.json)"
    missing = [i for i in ids if f"{i}.json" not in files]
    seen = {}
    for s in samples:
        f = d / f"{s['id']}.json"
        if not f.is_file():
            continue
        seen[s["id"]] = seen.get(s["id"], 0) + 1
        try:
            data = json.load(open(f))
        except Exception as e:  # noqa: BLE001
            problems[f.name] = f"unreadable: {type(e).__name__}"
            continue
        if not isinstance(data, dict) or set(data) != {"id", "aspect", "frames"}:
            problems[f.name] = f"unexpected keys {sorted(data) if isinstance(data, dict) else type(data).__name__}"
            continue
        if data["id"] != s["id"]:
            problems[f.name] = f"id inside the file is {data['id']}"
            continue
        if abs(data["aspect"] - EXPECT[framing]) > 1e-6:
            problems[f.name] = f"aspect {data['aspect']}"
            continue
        n_jpg = len(list((CORPUS / "frames" / framing / s["id"]).glob("*.jpg")))
        fr = data["frames"]
        if len(fr) != n_jpg or len(fr) != s["sampled_frames"]:
            problems[f.name] = f"{len(fr)} frames, expected {n_jpg} (samples.json says {s['sampled_frames']})"
            continue
        err = None
        for i, x in enumerate(fr):
            if not isinstance(x, dict) or set(x) != {"pose", "left_hand", "right_hand"}:
                err = f"frame {i}: unexpected keys"
                break
            err = check_points(x["pose"], 33, f"frame {i} pose") or check_points(x["left_hand"], 21, f"frame {i} left") or check_points(x["right_hand"], 21, f"frame {i} right")
            if err:
                break
        if err:
            problems[f.name] = err
            continue
        if sum(x["pose"] is not None for x in fr) < 8:
            problems[f.name] = "body pose found in fewer than 8 frames"
    dup = [i for i, c in seen.items() if c > 1]
    ok = len(ids) - len(missing) - len([f for f in problems if f[:-5] in set(ids)])
    print(f"{framing}: files {len(files)}, valid {ok}, missing {len(missing)}, bad {len(problems)}, duplicates {len(dup)}")
    for f, why in list(problems.items())[:15]:
        print("   bad:", f, "-", why)
    if missing:
        print("   missing:", missing[:10], "..." if len(missing) > 10 else "")
    total_bad += len(problems)
    if delete:
        for f in problems:
            (d / f).unlink()
            print("   deleted", f)
print("RESULT:", "all files valid" if total_bad == 0 else f"{total_bad} bad file(s)")
