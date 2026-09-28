import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import build, gh_common as ghc
build.apply_preset(sys.argv[1])
dg = bpy.context.evaluated_depsgraph_get()
for name in sys.argv[2].split(","):
    ob = bpy.data.objects[name]
    me = ob.evaluated_get(dg).to_mesh()
    n = len(me.vertices); co = np.empty(n*3); me.vertices.foreach_get("co", co); co = co.reshape(-1,3)
    mats = [m.name if m else None for m in me.materials]
    mi = np.empty(len(me.polygons), int); me.polygons.foreach_get("material_index", mi)
    print(name, n, "bbox", co.min(0).round(3), co.max(0).round(3))
    far = np.where((co[:,0] < -0.085) | (co[:,1] < -0.13))[0]
    print(" far verts", len(far), co[far][:5].round(3) if len(far) else "")
    if len(far):
        # which material faces use them
        fs=set(far.tolist()); cnt={}
        for p in me.polygons:
            if p.vertices[0] in fs: cnt[mats[p.material_index]]=cnt.get(mats[p.material_index],0)+1
        print(" far faces by material", cnt)
    ob.evaluated_get(dg).to_mesh_clear()
ob = bpy.data.objects["GH_Skin"]
me = ob.evaluated_get(dg).to_mesh()
n = len(me.vertices); co = np.empty(n*3); me.vertices.foreach_get("co", co); co = co.reshape(-1,3)
far = np.where(co[:,0] < -0.1)[0]
print("x<-0.1:", len(far), co[far].min(0).round(3), co[far].max(0).round(3))
for a in ("gore_bthin","gore_clot","gore_tis","gore_art","gore_bq"):
    at = me.attributes.get(a)
    if at is not None and at.domain=='POINT':
        v=np.empty(n,np.float32); at.data.foreach_get("value",v); print(a, v[far].min(), v[far].max())
