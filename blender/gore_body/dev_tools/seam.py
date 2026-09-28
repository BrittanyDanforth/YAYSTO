import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0]); out = a[1]; os.makedirs(out, exist_ok=True)
import gb_common as gbc
for o in bpy.data.objects:
    if o.type in ('MESH', 'CURVE'):
        o.hide_render = o.name not in ("GB_Body", "GB_Head")
        for m in o.modifiers:
            if m.type == 'ARMATURE': m.show_render = False
z = gbc.lift_z(gbc.SEAM_Z)
print("seam z", z)
# ring gap diagnostics
H, B = bpy.data.objects["GB_Head"], bpy.data.objects["GB_Body"]
import gb_geom as gg
for o in (H, B):
    loops = gg.boundary_loops(o.data)
    v = gbc.get_verts(o.data)
    print(o.name, "boundary loops", [len(l) for l in loops], [round(float(v[l][:, 2].mean()), 4) for l in loops])
hv = gbc.get_verts(H.data); bv = gbc.get_verts(B.data)
lh = gg.boundary_loops(H.data)[0]; lb = [l for l in gg.boundary_loops(B.data) if abs(bv[l][:, 2].mean() - z) < 0.01][0]
from mathutils.kdtree import KDTree
kd = KDTree(len(lb))
for i, j in enumerate(lb): kd.insert(bv[j].tolist(), i)
kd.balance()
d = [kd.find(hv[i].tolist())[2] for i in lh]
print("ring vertex mismatch max mm", max(d) * 1000)
gbc.setup_stage()
cam = gbc.add_camera("c", (-0.20, -0.05, z + 0.01), (0, 0.0, z), 85)
gbc.render(os.path.join(out, "seam_close.png"), cam, 16, (480, 480))
