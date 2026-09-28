"""Print the bleed sources per wound for presets (from the evaluated skin's blood attributes)."""
import os, sys, time
HEAD = "/home/user/YAYSTO/blender/gore_head"
sys.path.insert(0, HEAD)
SCR = os.path.dirname(os.path.abspath(__file__))
import bpy, numpy as np
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].endswith(".blend") else "base.blend"))
import gh_common as ghc, gore, build
if os.environ.get("REBUILD", "1") == "1":
    mats = {m.name: m for m in bpy.data.materials}
    gore.build_gore_node_group(); bpy.data.node_groups[gore.GROUP_NAME]["gh_gore_version"] = gore._GROUP_VERSION
    gore.build_gore_system(None, mats)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCR, "work.blend"), compress=False)
presets = [a for a in sys.argv[1:] if not a.endswith(".blend")] or list(build.PRESET_NAMES)
ids = [r["id"] + " " + r["name"] for r in gore.HEAD_VESSELS]
for p in presets:
    build.apply_preset(p)
    ctrl = ghc.ensure_controls(); ctrl["drip_time"] = float(os.environ.get("DRIP", "1.0")); ctrl.update_tag()
    dg = bpy.context.evaluated_depsgraph_get(); dg.update()
    ev = bpy.data.objects["GH_Skin"].evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    def arr(name):
        a = me.attributes.get(name)
        if a is None: return np.zeros(n)
        v = np.zeros(len(a.data)); a.data.foreach_get("value", v); return v
    q, src, art, bthin = arr("gore_bq"), arr("gore_bsrc"), arr("gore_art"), arr("gore_bthin")
    m = q > 0
    print(f"== {p}: {m.sum()} blood verts, total verts {n}")
    keys = sorted(set(zip(np.round(q[m], 2), np.round(src[m]).astype(int), np.round(art[m], 2))))
    for qq, s, a in keys[:40]:
        print(f"   Q={qq:7.2f} mL/min  art={a:4.2f}  src={ids[s-1] if s>0 else 'bed/ooze only'}")
    ev.to_mesh_clear()
