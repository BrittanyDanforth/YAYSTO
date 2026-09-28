import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import build
build.apply_preset("carnage")
dg = bpy.context.evaluated_depsgraph_get()
ob = bpy.data.objects["GH_Skin"]
me = ob.evaluated_get(dg).to_mesh()
n=len(me.vertices); co=np.empty(n*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
def att(nm):
    a=me.attributes.get(nm); v=np.zeros(n,np.float32)
    if a is not None and a.domain=='POINT': a.data.foreach_get("value",v)
    return v
run, runf, bthin, bq = att("gore_run"), att("gore_runf"), att("gore_bthin"), att("gore_bq")
# neck radius at the cut height: distance from neck axis (0, 0.015)
r = np.hypot(co[:,0], co[:,1]-0.015)
sel = np.where((co[:,2]<-0.12)&(co[:,2]>-0.15)&(r>0.066))[0]
print("outside neck verts", len(sel))
if len(sel):
    print(co[sel].min(0).round(3), co[sel].max(0).round(3))
    for rid in np.unique(run[sel])[:12]:
        m = sel[run[sel]==rid]
        print(" run", rid, len(m), "runf", runf[m].min().round(2), runf[m].max().round(2), "bq", bq[m].max().round(1), "bthin", bthin[m].min(), bthin[m].max())
mi=np.empty(len(me.polygons),int); me.polygons.foreach_get("material_index",mi)
fs=set(sel.tolist()); cnt={}
for p in me.polygons:
    if p.vertices[0] in fs:
        k=me.materials[p.material_index].name; cnt[k]=cnt.get(k,0)+1
print(cnt)
from mathutils.bvhtree import BVHTree
base = ob.data
bvh = BVHTree.FromPolygons([v.co for v in base.vertices], [p.vertices for p in base.polygons])
tis, art = att("gore_tis"), att("gore_art")
cand = np.where((co[:,2]<-0.115)&(co[:,2]>-0.155)&(np.abs(co[:,0])>0.035))[0]
far = [i for i in cand[::2] if bvh.find_nearest(co[i])[3] > 0.003]
far = np.array(far)
print("side far", len(far))
if len(far):
    print(co[far].min(0).round(3), co[far].max(0).round(3), "run", np.unique(run[far])[:8], "tis", tis[far].max(), "art", art[far].min(), art[far].max(), "bthin", bthin[far].min(), bthin[far].max())
