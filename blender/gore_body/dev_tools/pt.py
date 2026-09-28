import sys; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np
a = sys.argv[sys.argv.index('--') + 1:]
bpy.ops.wm.open_mainfile(filepath=a[0])
import posetest, gb_common as gbc, rig
if len(a) > 2 and a[2] == "reskin":
    objs = {n: bpy.data.objects[n] for n in gbc.exported_mesh_names(0) + gbc.exported_mesh_names(1) if n in bpy.data.objects}
    rig.skin_all(objs)
md = posetest.load_meshes(posetest.SKIN + posetest.INNER + ("GB_Shorts",))
ro = posetest.rest_outside(md)
for n, m in ro.items():
    if m.sum():
        v = md[n].v[m]
        print("REST-OUT", n, int(m.sum()), "z range", v[:, 2].min().round(3), v[:, 2].max().round(3), "x", v[:, 0].min().round(3), v[:, 0].max().round(3), "y", v[:, 1].min().round(3), v[:, 1].max().round(3))
res = posetest.run_tests(a[1].split(","), md=md, quiet=True)
for k, v in res.items():
    print("RES", k, v.get("ok"), "shorts", v.get("shorts_mm"), v.get("shorts_worst_rest"), "pinched", v.get("shorts_pinched"), "poke", v.get("poke_mm"))
