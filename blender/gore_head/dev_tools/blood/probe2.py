import os, sys
HEAD = "/home/user/YAYSTO/blender/gore_head"; sys.path.insert(0, HEAD)
SCR = os.path.dirname(os.path.abspath(__file__))
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend"))
import gh_common as ghc, gore, build
sys.argv=[sys.argv[0]]+sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv
build.apply_preset(sys.argv[1])
ctrl = ghc.ensure_controls(); ctrl["drip_time"] = float(sys.argv[2]) / 60.0; ctrl.update_tag()
for o in bpy.data.objects:
    if o.name.startswith("GH_Hit"): print(o.name, tuple(round(x,4) for x in o.matrix_world.translation))
dg = bpy.context.evaluated_depsgraph_get(); dg.update()
me = bpy.data.objects["GH_Skin"].evaluated_get(dg).data
n=len(me.vertices); co=np.empty(n*3); me.vertices.foreach_get("co",co); co=co.reshape(-1,3)
def arr(nm):
    a=me.attributes.get(nm); v=np.zeros(n)
    if a is not None and a.domain=='POINT': a.data.foreach_get("value",v)
    return v
run, rf = arr("gore_run"), arr("gore_runf")
for rid in np.unique(np.round(run[run>0.5])):
    sel=np.round(run)==rid
    i=np.argmin(np.where(sel, rf, 9)); j=np.argmax(np.where(sel, rf, -9))
    print(f"run {int(rid)} n={sel.sum()} start={np.round(co[i],4)} end={np.round(co[j],4)}")
