"""Convert the Mixamo FBX to GLB (skin on, animation off). Run headless from the repository root:

    blender --background --factory-startup --python tools/avatar/convert_fbx.py -- tools/avatar/source/T-Pose.fbx frontend/public/avatar/signer.glb

The FBX is only read. Mixamo FBX files are in centimetres with a 90 degree X rotation on the armature; the glTF exporter converts to
metres and Y up, so the exported node transforms are inspected by tools/avatar/verify_glb.py after every conversion.
"""

import sys
from pathlib import Path

import bpy


def main() -> None:
    args = sys.argv[sys.argv.index("--") + 1 :]
    if len(args) != 2:
        raise SystemExit("usage: convert_fbx.py <input.fbx> <output.glb>")
    src, dst = Path(args[0]).resolve(), Path(args[1]).resolve()
    if not src.is_file():
        raise SystemExit(f"FBX not found: {src}")

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(src))
    armatures = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if len(armatures) != 1 or not meshes:
        raise SystemExit(f"expected one armature and at least one mesh, found {len(armatures)} and {len(meshes)}")
    for action in list(bpy.data.actions):  # the T-pose file carries a one frame action; animation is not wanted
        bpy.data.actions.remove(action)
    if armatures[0].animation_data:
        armatures[0].animation_data_clear()

    dst.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(
        filepath=str(dst),
        export_format="GLB",
        use_selection=False,
        export_skins=True,
        export_animations=False,
        export_morph=False,
        export_yup=True,
        export_apply=False,
    )
    print(f"exported {dst} ({dst.stat().st_size} bytes) with {len(armatures[0].data.bones)} bones and {len(meshes)} meshes")


main()
