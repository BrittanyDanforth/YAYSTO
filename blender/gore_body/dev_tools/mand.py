import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np, gb_common as gbc, skeleton as SK, skull as SKL
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
h = float(sys.argv[sys.argv.index('--') + 2])
bpy.ops.wm.read_factory_settings(use_empty=True)
O = gbc.HEAD_OFFSET
fn, box = SK.mandible_sdf()
raw = lambda x, y, z: SKL.mandible_raw(x - O[0], y - O[1], z - O[2])
mat = bpy.data.materials.new("b"); mat.use_nodes = True; bb = mat.node_tree.nodes["Principled BSDF"]
bb.inputs["Base Color"].default_value = (0.35, 0.30, 0.24, 1); bb.inputs["Roughness"].default_value = 0.6
objs = {}
for nm, f, dx in (("raw", raw, 0.0), ("clamped", fn, 0.0)):
    v, fa = SK.mesh_sdf(f, box, h)
    me = gbc.mesh_from_arrays(nm, v, fa); o = bpy.data.objects.new(nm, me); bpy.context.scene.collection.objects.link(o)
    me.materials.append(mat); me.shade_smooth(); objs[nm] = o
gbc.setup_stage()
c = (0.0, -0.03, 1.60)
V = {"side": ((-0.40, -0.03, 1.60), c, 70), "tq": ((-0.30, -0.30, 1.62), c, 70), "front": ((0, -0.4, 1.62), c, 70), "under": ((-0.12, -0.2, 1.35), c, 60)}
for k, (l, t, fl) in V.items():
    cam = gbc.add_camera("C" + k, l, t, fl)
    for nm in objs:
        for n2, o in objs.items(): o.hide_render = n2 != nm
        gbc.render(os.path.join(out, f"{nm}_{k}.png"), cam, 12, (360, 360))
print("DONE")
