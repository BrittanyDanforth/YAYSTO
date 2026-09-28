import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import build
build.apply_preset(sys.argv[1])
dg = bpy.context.evaluated_depsgraph_get()
for name in ("GH_Tongue","GH_MouthCavity","GH_Gums","GH_Muscle"):
    ob = bpy.data.objects[name]
    base = len(ob.data.vertices)
    me = ob.evaluated_get(dg).to_mesh()
    co = np.empty(len(me.vertices)*3); me.vertices.foreach_get("co", co); co=co.reshape(-1,3)
    sel = (np.abs(co[:,0])<0.02)&(co[:,2]>-0.075)&(co[:,2]<-0.04)
    print(name, "base", base, "eval", len(me.vertices), "in mouth box", sel.sum(), "y range", co[sel,1].min().round(3) if sel.any() else None, co[sel,1].max().round(3) if sel.any() else None)
    ob.evaluated_get(dg).to_mesh_clear()
