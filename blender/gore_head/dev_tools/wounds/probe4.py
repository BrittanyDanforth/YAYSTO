import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
from mathutils.bvhtree import BVHTree
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import build
build.apply_preset("carnage")
dg = bpy.context.evaluated_depsgraph_get()
ob = bpy.data.objects["GH_Skin"]
bm_base = ob.data
bvh = BVHTree.FromPolygons([v.co for v in bm_base.vertices], [p.vertices for p in bm_base.polygons])
me = ob.evaluated_get(dg).to_mesh()
n=len(me.vertices); co=np.empty(n*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
def att(nm):
    a=me.attributes.get(nm); v=np.zeros(n,np.float32)
    if a is not None and a.domain=='POINT': a.data.foreach_get("value",v)
    return v
bthin, tis, run = att("gore_bthin"), att("gore_tis"), att("gore_run")
sel = np.where((co[:,2]<-0.11)&(co[:,2]>-0.16))[0]
far=[]
for i in sel[::3]:
    loc,nrm,idx,d = bvh.find_nearest(co[i])
    if d>0.004: far.append(i)
far=np.array(far)
print("neck verts", len(sel), "far >4mm", len(far))
if len(far):
    print(co[far].min(0).round(3), co[far].max(0).round(3), "run", np.unique(run[far])[:10], "tis", tis[far].max(), "bthin", bthin[far].min(), bthin[far].max())
