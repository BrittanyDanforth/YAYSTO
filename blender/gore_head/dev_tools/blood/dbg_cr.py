import os, sys
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import gh_common as ghc, build, proof_blood as pb
build.setup_cameras(); build.apply_preset("crushed")
hit = bpy.data.objects["GH_Hit_Crush_2"]; centre = np.array(hit.matrix_world.translation)
ctrl = ghc.ensure_controls(); ctrl["drip_time"] = 20/60; ctrl.update_tag(); bpy.context.view_layer.update()
m = pb._mesh_arrays(bpy.data.objects["GH_Skin"])
axis, rim = pb._main_axis(m, centre, 0.05)
print("centre", centre, "n", len(axis), "rim", rim, axis[0], axis[rim], axis[-1])
cams = pb._cameras(hit, 0.09, axis[rim] + np.array([0, 0, -0.002]))
dg = bpy.context.evaluated_depsgraph_get(); sc = bpy.context.scene
for v, c in cams.items():
    o = c.matrix_world.translation
    for p in axis[rim:rim+3]:
        d = Vector(p) - o
        hit_, loc, n, i, ob, mm = sc.ray_cast(dg, o, d.normalized(), distance=d.length + 0.001)
        print(v, "cam", tuple(round(x,3) for x in o), "dist", round(d.length,4), "hit", hit_, ob.name if ob else None, round((loc-o).length,4) if hit_ else None)
