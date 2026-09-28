import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(os.path.dirname(os.path.abspath(__file__)), "work.blend"))
import build
build.apply_preset(sys.argv[1])
for o in bpy.data.objects:
    if o.name.startswith("GH_Hit_"):
        m = o.matrix_world
        print(o.name, tuple(round(c, 4) for c in m.translation), "Z", tuple(round(c, 3) for c in m.to_3x3().col[2].normalized()), "S", tuple(round(c,2) for c in o.scale))
dg = bpy.context.evaluated_depsgraph_get()
me = bpy.data.objects["GH_Skin"].evaluated_get(dg).to_mesh()
n = len(me.vertices); co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
def att(nm):
    a = me.attributes.get(nm); v = np.zeros(n, np.float32)
    if a is not None and a.domain == 'POINT': a.data.foreach_get("value", v)
    return v
bl, run, bs = att("gore_blood"), att("gore_run"), att("gore_bsrc")
mi = np.empty(len(me.polygons), int); me.polygons.foreach_get("material_index", mi)
names = [m.name if m else "" for m in me.materials]
bmat = names.index("GH_Blood")
fv = np.zeros(n, bool)
for p in me.polygons:
    if p.material_index == bmat:
        fv[list(p.vertices)] = True
pool = fv & (run < 0.5)
sel = pool & (co[:, 2] < -0.11)
print("pool verts below z -0.11:", sel.sum())
if sel.sum():
    print(co[sel].min(0).round(4), co[sel].max(0).round(4))
    far = sel & (co[:, 1] < -0.07)
    print("floating (y<-0.07):", far.sum(), co[far].min(0).round(4) if far.sum() else "", co[far].max(0).round(4) if far.sum() else "")
