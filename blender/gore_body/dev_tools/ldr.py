"""Scratch: look-dev renders of a saved body blend (GBL materials as saved)."""
import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]
blend, out = a[0], a[1]; os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
import gb_common as gbc, lookdev, bake
bake.show_all_collections()
SK = ["GB_Body", "GB_Head", "GB_Shorts", "GB_Eye_L", "GB_Eye_R", "GB_Mouth", "GB_BrowLash", "GB_EyeFX_L", "GB_EyeFX_R"]
V = {
 "face_tq": (SK, ((-0.30, -0.42, 1.70), (0.0, -0.03, 1.665), 85)),
 "eye_close": (SK, ((0.02, -0.22, 1.690), (0.0315, -0.0475, 1.684), 85)),
 "eye_side": (SK, ((0.20, -0.12, 1.690), (0.0315, -0.06, 1.684), 100)),
 "neck_side": (SK, ((-0.75, -0.02, 1.57), (0, -0.005, 1.53), 85)),
 "chest": (SK, ((0.0, -1.2, 1.30), (0, 0, 1.25), 60)),
 "back": (SK, ((0.0, 1.5, 1.20), (0, 0, 1.18), 50)),
 "knee": (SK, ((0.25, -0.60, 0.55), (0.09, -0.02, 0.50), 85)),
 "brain": (["GB_Brain", "GB_Cord"], ((-0.35, -0.30, 1.78), (0, 0.02, 1.685), 85)),
 "brain_side": (["GB_Brain", "GB_Cord"], ((0.45, 0.02, 1.70), (0, 0.02, 1.685), 70)),
 "heart": (["GB_Organs", "GB_Vessels_Art", "GB_Vessels_Ven"], ((0.05, -0.55, 1.36), (0.015, -0.03, 1.34), 70)),
 "organs": (["GB_Organs"], ((0.0, -1.0, 1.22), (0, -0.02, 1.18), 50)),
 "skull_side": (["GB_Skeleton", "GB_Mouth"], ((-0.50, 0.0, 1.70), (0, 0.0, 1.66), 70)),
 "skull_tq": (["GB_Skeleton", "GB_Mouth"], ((-0.36, -0.38, 1.66), (0, -0.01, 1.66), 70)),
}
sel = a[2].split(",") if len(a) > 2 else list(V)
lookdev._studio()
for k in sel:
    vis, (loc, tgt, lens) = V[k]
    cam = gbc.add_camera("C_" + k, loc, tgt, lens)
    for o in bpy.data.objects:
        if o.type in ('MESH', 'CURVE'):
            o.hide_render = o.name not in vis and o.name != "GB_StageFloor"
            if not o.hide_render:
                for c in o.users_collection: c.hide_render = False
    gbc.render(os.path.join(out, k + ".png"), cam, 24, (480, 480))
print("DONE")
