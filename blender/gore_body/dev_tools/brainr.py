import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np, gb_common as gbc, skeleton as SK, neuro
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
h = float(sys.argv[sys.argv.index('--') + 2])
bpy.ops.wm.read_factory_settings(use_empty=True)
v, f = SK.mesh_sdf(neuro.brain_sdf, neuro.brain_box(), h)
me = gbc.mesh_from_arrays("b", v, f); o = bpy.data.objects.new("b", me); bpy.context.scene.collection.objects.link(o)
m = bpy.data.materials.new("m"); m.use_nodes = True; b = m.node_tree.nodes["Principled BSDF"]
b.inputs["Base Color"].default_value = (0.62, 0.45, 0.40, 1); b.inputs["Roughness"].default_value = 0.4
me.materials.append(m); me.shade_smooth()
gbc.setup_stage()
c = (0.0, 0.02, 1.67)
V = {"side": ((0.45, 0.02, 1.68), c, 70), "back": ((0.0, 0.45, 1.64), c, 70), "under": ((0.25, 0.25, 1.40), c, 70)}
for k, (l, t, fl) in V.items():
    gbc.render(os.path.join(out, f"br_{k}.png"), gbc.add_camera("C" + k, l, t, fl), 16, (420, 420))
print("DONE", len(f))
