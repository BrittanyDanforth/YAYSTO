"""pix.py PRESET CAM x,y [x,y ...]: ray-cast the preset camera through 640px image pixels
(x right, y down) and report object / material / gore attributes of the hit face."""
import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy, numpy as np
from mathutils import Vector
SCR = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend"))
import build, gh_common as ghc
preset, camn = sys.argv[1], sys.argv[2]
build.setup_cameras()
build.apply_preset(preset)
ctrl = ghc.ensure_controls(); ctrl["drip_time"] = float(os.environ.get("T", "40")) / 60.0; ctrl.update_tag()
for kv in os.environ.get("CTRL", "").split(","):
    if kv:
        k, v = kv.split("="); ctrl[k] = float(v)
ctrl.update_tag()
sc = bpy.context.scene
if camn.startswith("hit:"):
    _, hn, view, dist = camn.split(":")
    hit = bpy.data.objects[hn]
    m = hit.matrix_world.to_3x3().normalized()
    z = (m @ Vector((0.0, 0.0, 1.0))).normalized()
    tgt = hit.matrix_world.translation + Vector((0, 0, -0.004))
    horiz = Vector((0, 0, 1)).cross(z).normalized()
    d = z if view == "straight" else (z + horiz).normalized()
    cam = ghc.add_camera("PX", tgt + d * float(dist), tgt, 85.0)
else:
    cam = bpy.data.objects["GH_Cam_" + camn]
sc.render.resolution_x = sc.render.resolution_y = 640
dg = bpy.context.evaluated_depsgraph_get()
fr = cam.data.view_frame(scene=sc)  # tr, br, bl, tl in cam space
tr, br, bl, tl = fr
cache = {}
for arg in sys.argv[3:]:
    x, y = map(float, arg.split(","))
    u, v = x / 640.0, y / 640.0
    p = tl + (tr - tl) * u + (bl - tl) * v
    o = cam.matrix_world.translation
    d = (cam.matrix_world.to_3x3() @ p).normalized()
    hit, loc, nor, fi, ob, mw = sc.ray_cast(dg, o, d)
    if not hit:
        print(arg, "miss"); continue
    ev = ob.evaluated_get(dg)
    me = cache.get(ob.name) or ev.to_mesh(); cache[ob.name] = me
    poly = me.polygons[fi]
    mat = me.materials[poly.material_index].name if me.materials else "-"
    at = {}
    for a in me.attributes:
        if a.name.startswith(("gore_", "d_")) and a.data_type == 'FLOAT':
            if a.domain == 'POINT':
                at[a.name] = round(float(np.mean([a.data[i].value for i in poly.vertices])), 3)
            elif a.domain == 'FACE':
                at[a.name] = round(a.data[fi].value, 3)
    at = {k: v for k, v in at.items() if abs(v) > 1e-4}
    print(arg, ob.name, mat, tuple(round(c, 4) for c in (mw.inverted() @ loc)), at)
