import os, sys, time
HEAD = "/home/user/YAYSTO/blender/gore_head"
sys.path.insert(0, HEAD)
SCR = os.path.dirname(os.path.abspath(__file__))
import bpy
from mathutils import Vector
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "base.blend"))
import gh_common as ghc
import gore
import build

t = time.time()
cs = gore.vessel_courses()
print("courses", len(cs), time.time() - t)
for c in cs:
    a, b = Vector(c["course"][0]), Vector(c["course"][-1])
    L = sum((Vector(c["course"][i + 1]) - Vector(c["course"][i])).length for i in range(len(c["course"]) - 1))
    print(f"{c['id']}_{c['side_tag']:1s} {c['name'][:40]:40s} n={len(c['course']):3d} len={L*1000:6.1f}mm start={tuple(round(x,3) for x in a)}")
ob = gore.build_vessels()
gore.export_vessel_table(os.path.join(SCR, "vessels_head.json"))
# visual: vessels as red/blue tubes, skin semi-transparent
build.apply_preset("intact")
cu = bpy.data.curves.new("vviz", 'CURVE')
cu.dimensions = '3D'
cu.bevel_depth = 0.0009
for c in cs:
    sp = cu.splines.new('POLY')
    sp.points.add(len(c["course"]) - 1)
    for i, p in enumerate(c["course"]):
        sp.points[i].co = (*p, 1.0)
    sp.material_index = {"artery": 0, "deep_artery": 0, "vein": 1, "sinus": 1}[c["cls"]]
vo = bpy.data.objects.new("vviz", cu)
bpy.context.scene.collection.objects.link(vo)
for col in ((0.8, 0.02, 0.02), (0.05, 0.1, 0.7)):
    m = bpy.data.materials.new("vm")
    m.use_nodes = True
    m.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (*col, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Emission Color"].default_value = (*col, 1)
    m.node_tree.nodes["Principled BSDF"].inputs["Emission Strength"].default_value = 2.0
    cu.materials.append(m)
skin = bpy.data.objects["GH_Skin"]
skin.visible_camera = False
for n in ("GH_Muscle",):
    o = bpy.data.objects.get(n)
    if o: o.visible_camera = False
sc = bpy.context.scene
sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
cams = build.setup_cameras()
for v in ("three_q", "side", "front", "back"):
    ghc.render(os.path.join(SCR, f"vessels_{v}.png"), cams[v], 12, (400, 400))
