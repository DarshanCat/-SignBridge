import json
import math
from pathlib import Path

HERE = Path(__file__).parent
d = json.load(open(HERE / "results.json"))
rows = d["rows"]
N = len(rows)
SRC = ["offline", "py16x9", "br16x9", "py4x3", "br4x3", "py4x3_raw", "br4x3_raw"]


def wilson(k, n, z=1.96):
    p = k / n
    den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return c - h, c + h


def outcome(r, s):
    o = r[s]
    if o.get("status") not in ("ok", None) and "top" not in o:
        return "no_result"
    if not o["accepted"]:
        return "unrecognized"
    return "correct" if o["top"].lower() == r["label"].lower() else "wrong"


out = {}
for s in SRC:
    c = {"correct": 0, "wrong": 0, "unrecognized": 0, "no_result": 0}
    top1 = 0
    for r in rows:
        c[outcome(r, s)] += 1
        o = r[s]
        if "top" in o and o["top"].lower() == r["label"].lower():
            top1 += 1
    answered = c["correct"] + c["wrong"]
    out[s] = {**c, "top1_any_conf": top1, "answered": answered, "acc_answered": c["correct"] / answered if answered else None}
for s in SRC:
    o = out[s]
    lo, hi = wilson(o["correct"], N)
    print(f"{s:10s} acc {o['correct']/N:.2f} [{lo:.2f},{hi:.2f}]  wrong-accepted {o['wrong']/N:.2f}  unrec {o['unrecognized']/N:.2f}  no_result {o['no_result']}  top1(any conf) {o['top1_any_conf']/N:.2f}  acc|answered {o['acc_answered']}")
# agreement and extraction
def agree(a, b):
    return sum(1 for r in rows if outcome(r, a) == outcome(r, b) == "correct"), sum(1 for r in rows if outcome(r, a) == "correct" and outcome(r, b) != "correct"), sum(1 for r in rows if outcome(r, a) != "correct" and outcome(r, b) == "correct")
for a, b in [("offline", "br16x9"), ("offline", "br4x3"), ("py16x9", "br16x9"), ("py4x3", "br4x3"), ("offline", "py16x9")]:
    print("both correct / only", a, "/ only", b, agree(a, b))
for k in ("py16x9", "br16x9", "py4x3", "br4x3"):
    ex = [r["extract"][k] for r in rows]
    print(k, "frames mean", sum(e["frames"] for e in ex) / N, "pose", sum(e["pose"] for e in ex) / N, "hand", sum(e["hand"] for e in ex) / N)
json.dump(out, open(HERE / "summary.json", "w"), indent=1)
# list the browser 4x3 misses
for s in ("br16x9", "br4x3"):
    print(s, "not correct:", [(r["label"], r[s].get("top"), r[s].get("conf")) for r in rows if outcome(r, s) != "correct"][:30])
