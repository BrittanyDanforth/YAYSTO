"""Probe the evaluated skin: blood attribute stats on skin vs blood material."""
import os, sys
HEAD = "/home/user/YAYSTO/blender/gore_head"; sys.path.insert(0, HEAD)
SCR = os.path.dirname(os.path.abspath(__file__))
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend"))
import gh_common as ghc, gore, build
build.apply_preset(sys.argv[1])
ctrl = ghc.ensure_controls(); ctrl["drip_time"] = float(sys.argv[2]) / 60.0; ctrl.update_tag()
dg = bpy.context.evaluated_depsgraph_get(); dg.update()
ob = bpy.data.objects["GH_Skin"].evaluated_get(dg)
me = ob.data
n = len(me.vertices)
def arr(name, dom=None):
    a = me.attributes.get(name)
    if a is None: return None
    v = np.zeros(len(a.data)); a.data.foreach_get("value", v); return v
mi = np.zeros(len(me.polygons), int); me.polygons.foreach_get("material_index", mi)
names = [m.name if m else None for m in me.materials]
print("verts", n, "faces", len(me.polygons), "materials", names)
for k in range(len(names)):
    print("  mat", names[k], (mi == k).sum())
gb = arr("gore_blood"); bt = arr("gore_bthin")
print("gore_blood >0.05:", (gb > 0.05).sum(), " >0.3:", (gb > 0.3).sum(), "bthin present", bt is not None)
lv = np.zeros(len(me.loops), int); me.loops.foreach_get("vertex_index", lv)
ls = np.zeros(len(me.polygons), int); me.polygons.foreach_get("loop_start", ls)
lt = np.zeros(len(me.polygons), int); me.polygons.foreach_get("loop_total", lt)
fid = np.repeat(np.arange(len(me.polygons)), lt)
skinv = np.zeros(n, bool); skinv[lv[mi[fid] == 0]] = True
print("skin verts", skinv.sum(), "skin gore_blood>0.05", (gb[skinv] > 0.05).sum(), ">0.2", (gb[skinv] > 0.2).sum(), "max", gb[skinv].max())
