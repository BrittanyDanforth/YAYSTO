import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import build
build.apply_preset("carnage")
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.objects["GH_Skin"].evaluated_get(dg).to_mesh()
names = [m.name if m else "" for m in me.materials]
cnt = {}
for p in me.polygons:
    c = p.center
    if -0.142 < c.z < -0.125 and abs(c.x) < 0.025 and c.y > -0.056:
        k = names[p.material_index]
        cnt[k] = cnt.get(k, 0) + p.area
print({k: round(v * 1e6, 1) for k, v in cnt.items()}, "mm^2")
n = len(me.vertices); co = np.empty(n*3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
run = np.zeros(n, np.float32); a = me.attributes.get("gore_run"); a.data.foreach_get("value", run)
sel = (co[:,2] > -0.142) & (co[:,2] < -0.125) & (np.abs(co[:,0]) < 0.025) & (co[:,1] > -0.056)
print("verts in cut box", sel.sum(), "with run", (sel & (run > 0.5)).sum(), "ymin", co[sel][:,1].min().round(4) if sel.sum() else "")
