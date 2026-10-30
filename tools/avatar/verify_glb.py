"""Verify a GLB by parsing it (no Blender needed): skeleton hierarchy, finger joints, node transforms, size. Run from the repo root:

    python tools/avatar/verify_glb.py frontend/public/avatar/signer.glb [--json out.json]

Exits 1 if the wrist or any finger joint is missing on either hand, or if animations or no skin are present.
"""

import json
import struct
import sys
from pathlib import Path

FINGERS = ("Thumb", "Index", "Middle", "Ring", "Pinky")


def read_glb(path: Path) -> tuple[dict, int]:
    data = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("not a valid glTF 2.0 binary file")
    chunk_len, chunk_type = struct.unpack_from("<II", data, 12)
    if chunk_type != 0x4E4F534A:
        raise ValueError("first chunk is not JSON")
    return json.loads(data[20 : 20 + chunk_len]), len(data)


def skeleton(gltf: dict) -> dict:
    nodes = gltf["nodes"]
    if not gltf.get("skins"):
        raise ValueError("the file has no skin")
    joints = set(gltf["skins"][0]["joints"])
    parent: dict[int, int] = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    names = {i: nodes[i].get("name", f"node{i}") for i in joints}
    tree = {names[i]: names.get(parent.get(i, -1)) for i in joints}
    return {"joints": names, "parent_of": tree}


def finger_report(bones: set[str], prefix: str = "") -> dict:
    out = {}
    for side in ("Left", "Right"):
        wrist = f"{prefix}{side}Hand" in bones
        fingers = {f: [f"{prefix}{side}Hand{f}{k}" in bones for k in (1, 2, 3)] for f in FINGERS}
        out[side] = {"wrist": wrist, "fingers": fingers, "complete": wrist and all(all(v) for v in fingers.values())}
    return out


def print_tree(tree: dict[str, str | None]) -> None:
    kids: dict[str | None, list[str]] = {}
    for child, par in tree.items():
        kids.setdefault(par, []).append(child)

    def walk(name: str, depth: int) -> None:
        print("  " * depth + name)
        for c in sorted(kids.get(name, [])):
            walk(c, depth + 1)

    for root in sorted(kids.get(None, [])):
        walk(root, 0)


def main() -> int:
    args = sys.argv[1:]
    path = Path(args[0])
    gltf, size = read_glb(path)
    sk = skeleton(gltf)
    bones = set(sk["joints"].values())
    prefix = "mixamorig:" if any(b.startswith("mixamorig:") for b in bones) else next((b[: b.index("Hips")] for b in bones if "Hips" in b), "")
    rep = finger_report(bones, prefix)
    print(f"file {path.name}: {size} bytes ({size / 1e6:.2f} MB)")
    print(f"nodes {len(gltf['nodes'])}, skins {len(gltf['skins'])}, skeleton joints {len(bones)}, meshes {len(gltf.get('meshes', []))}, "
          f"materials {len(gltf.get('materials', []))}, images {len(gltf.get('images', []))}, animations {len(gltf.get('animations', []))}")
    print(f"bone name prefix: {prefix!r}")
    print("hierarchy:")
    print_tree(sk["parent_of"])
    for side, r in rep.items():
        print(f"{side} hand: wrist {r['wrist']}, joints 1 to 3 per finger present: "
              + ", ".join(f"{f}={all(v)}" for f, v in r["fingers"].items()) + f" -> complete {r['complete']}")
    roots = [i for i, n in enumerate(gltf["nodes"]) if "mesh" in n or "skin" in n or n.get("name", "").lower().startswith("armature")]
    for i in roots[:5]:
        n = gltf["nodes"][i]
        print("node", n.get("name"), {k: n[k] for k in ("translation", "rotation", "scale") if k in n})
    ok = all(r["complete"] for r in rep.values()) and not gltf.get("animations")
    if "--json" in args:
        Path(args[args.index("--json") + 1]).write_text(json.dumps({"size": size, "bones": sorted(bones), "report": rep}, indent=1), encoding="utf-8")
    print("RESULT:", "complete rig, no animations" if ok else "PROBLEM: missing joints or animations present")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
