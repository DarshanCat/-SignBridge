"""Headless Blender: import the FBX and print what is in it (objects, transforms, armature bones). Read only."""
import sys

import bpy

path = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=path)
for o in bpy.data.objects:
    print("OBJ", o.type, o.name, "loc", tuple(round(v, 3) for v in o.location), "rot", tuple(round(v, 3) for v in o.rotation_euler), "scale", tuple(round(v, 3) for v in o.scale), "parent", o.parent.name if o.parent else None)
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("BONES", len(arm.data.bones))
for b in arm.data.bones:
    print("BONE", b.name, "parent", b.parent.name if b.parent else None, "head", tuple(round(v, 3) for v in b.head_local), "tail", tuple(round(v, 3) for v in b.tail_local))
for o in bpy.data.objects:
    if o.type == "MESH":
        print("MESH", o.name, "verts", len(o.data.vertices), "mods", [m.type for m in o.modifiers], "vgroups", len(o.vertex_groups), "mats", [m.name for m in o.data.materials], "shape_keys", bool(o.data.shape_keys))
print("ANIMS", [a.name for a in bpy.data.actions])
