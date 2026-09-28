import os, sys
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import gh_common as ghc, build, proof_blood as pb
build.setup_cameras()
build.apply_preset("slash")
hit = bpy.data.objects["GH_Hit_Slash_Cheek"]; centre = np.array(hit.matrix_world.translation)
ctrl = ghc.ensure_controls(); ctrl["drip_time"] = 20/60; ctrl.update_tag(); bpy.context.view_layer.update()
m = pb._mesh_arrays(bpy.data.objects["GH_Skin"])
axis, rim = pb._main_axis(m, centre, 0.05)
print("centre", centre, "axis", None if axis is None else (len(axis), rim, axis[0], axis[-1]))
cams = pb._cameras(hit, 0.07)
d = pb._densify(axis); 
for v, c in cams.items():
    uv = pb._project(c, d, 200); vis = pb._visible(c, d)
    print(v, "vis", vis.sum(), len(vis), "uv range", uv.min(0), uv.max(0))
