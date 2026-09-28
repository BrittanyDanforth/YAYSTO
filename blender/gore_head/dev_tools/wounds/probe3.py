import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import build
build.apply_preset("blast")
dg = bpy.context.evaluated_depsgraph_get()
ob = bpy.data.objects["GH_Tongue"]
me = ob.evaluated_get(dg).to_mesh()
co = np.empty(len(me.vertices)*3); me.vertices.foreach_get("co", co); co=co.reshape(-1,3)
base = np.empty(len(ob.data.vertices)*3); ob.data.vertices.foreach_get("co", base); base=base.reshape(-1,3)
print("base y min", base[:,1].min(), "eval y min", co[:,1].min())
for lo in np.arange(-0.08,-0.01,0.01):
    print(round(lo,3), "base", ((base[:,1]>=lo)&(base[:,1]<lo+0.01)).sum(), "eval", ((co[:,1]>=lo)&(co[:,1]<lo+0.01)).sum())
hit = bpy.data.objects["GH_Hit_Blast_Mouth"]
print("hit loc", tuple(round(v,4) for v in hit.location), "rot", tuple(round(v,3) for v in hit.rotation_euler))
