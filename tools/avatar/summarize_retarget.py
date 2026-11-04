"""Turn docs/avatar_retarget/measurement_*.json (written by frontend/src/lib/avatar/retargetMeasure.test.ts with RETARGET_REPORT_DIR set) into
docs/avatar_retarget/MEASUREMENT.md. usage (repository root): python -I tools/avatar/summarize_retarget.py"""
import json
from pathlib import Path

D = Path(__file__).resolve().parents[2] / "docs" / "avatar_retarget"
load = lambda n: json.load(open(D / f"measurement_{n}.json", encoding="utf-8"))
M = {n: load(n)["report"][n] for n in ("legacy", "solver_plain", "solver_no_collision", "solver")}
meta = load("legacy")
f = lambda s: f"{s['mean']:.2f}"
g = lambda s: f"{s['p90']:.2f}"
o = []
P = o.append
P("# Retarget measurement: avatar against the source landmarks\n")
P(f"Real `signer.vrm` (shoulder width {meta['anatomy']['sw']:.3f} m, mouth read from the model's own mouth morph) and 10 real clips ({', '.join(meta['clips'])}), every source frame of every clip, both hands where the source has them (n = {M['legacy']['position']['wrist']['n']} hand frames). Forward kinematics of the pose each method produces, applied to the avatar's skeleton, against the source landmarks of the same frame. Authors' predefined split is not involved (no model is evaluated); the recognition model and its results were not touched.\n")
P("Methods: **legacy** = the clips' own rotation tracks (what the avatar played before). **new** = the retargeter of this change (aspect correction, depth from bone length, face anchored mapping, IK with an elbow hinge, collision, full palm orientation, per joint finger and thumb directions). **plain** and **no collision** are the new retargeter with parts switched off, to show where the change comes from.\n")
P("Units: position error in shoulder widths of each body measured from the shoulder midpoint (so arm length and proportions count); direction error in degrees between a bone of the avatar and the same segment of the source. The **picture plane (2D)** error ignores depth: the depth of the source is its least reliable number, so the 2D error is the one to trust; the 3D error is given for completeness and is worse for the new retargeter by construction (it replaces the noisy source depth by one that respects bone lengths).\n")
P("## Position error per joint (shoulder widths, mean and 90th percentile)\n")
P("| Joint | legacy 2D | new 2D | legacy 2D p90 | new 2D p90 | legacy 3D | new 3D |")
P("|---|---|---|---|---|---|---|")
for k in ["elbow", "wrist", "thumb.CMC", "thumb.MCP", "thumb.IP", "thumb.tip", "index.MCP", "index.PIP", "index.DIP", "index.tip", "middle.tip", "ring.tip", "pinky.tip"]:
    a, b = M["legacy"], M["solver"]
    P(f"| {k} | {f(a['position2d'][k])} | {f(b['position2d'][k])} | {g(a['position2d'][k])} | {g(b['position2d'][k])} | {f(a['position'][k])} | {f(b['position'][k])} |")
P("\n## Direction error per bone (degrees, mean and 90th percentile)\n")
P("| Bone | legacy | new | legacy p90 | new p90 |")
P("|---|---|---|---|---|")
for k in ["upperArm", "foreArm", "hand", "thumb.CMC-MCP", "thumb.MCP-IP", "index.MCP-PIP", "index.PIP-DIP", "middle.MCP-PIP", "middle.PIP-DIP", "ring.MCP-PIP", "ring.PIP-DIP", "pinky.MCP-PIP", "pinky.PIP-DIP"]:
    a, b = M["legacy"]["direction"][k], M["solver"]["direction"][k]
    P(f"| {k} | {f(a)} | {f(b)} | {g(a)} | {g(b)} |")
P("\nThe forearm direction is measured against the raw source depth and is the one bone where the new number is higher: see the note on depth above (2D wrist error 0.23 to 0.004 shoulder widths).\n")
P("## Hands near the face: wrist and index tip relative to the mouth (shoulder widths, difference of the vectors from the mouth)\n")
P("| | legacy | new |")
P("|---|---|---|")
for k in ("wrist", "indexTip"):
    a, b = M["legacy"]["face"].get(k), M["solver"]["face"].get(k)
    if a and b:
        P(f"| {k} (n = {a['n']}) | {f(a)} | {f(b)} |")
P("\n## Hands inside the body (share of hand frames in which the wrist, the palm or a fingertip is inside the head or torso)\n")
P("| Method | any | head | torso |")
P("|---|---|---|---|")
for n in ("legacy", "solver_plain", "solver_no_collision", "solver"):
    p = M[n]["penetration"]
    P(f"| {n} | {p['any']['mean'] * 100:.1f} % | {p['head']['mean'] * 100:.1f} % | {p['torso']['mean'] * 100:.1f} % |")
P("\n## Where the improvement comes from\n")
P("| Method | wrist 2D | index tip 2D | index knuckle direction | hand direction | inside the body |")
P("|---|---|---|---|---|---|")
for n in ("legacy", "solver_plain", "solver_no_collision", "solver"):
    r = M[n]
    P(f"| {n} | {f(r['position2d']['wrist'])} | {f(r['position2d']['index.tip'])} | {f(r['direction']['index.MCP-PIP'])} | {f(r['direction']['hand'])} | {r['penetration']['any']['mean'] * 100:.1f} % |")
(D / "MEASUREMENT.md").write_text("\n".join(o) + "\n", encoding="utf-8", newline="\n")
print("\n".join(o))
