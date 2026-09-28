"""Scratch: mesh the heart SDF (+ sub colours) and render clay views."""
import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np, gb_common as gbc, skeleton as SK, viscera as VC
out = sys.argv[sys.argv.index('--') + 1]; os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
lo, hi = VC.heart_box()
v, f = SK.mesh_sdf(VC.heart_sdf, (lo, hi), 0.0012)
me = gbc.mesh_from_arrays("heart", v, f); o = bpy.data.objects.new("heart", me); bpy.context.scene.collection.objects.link(o)
sub = VC.heart_sub(v)
cols = {1: (0.45, 0.10, 0.10), 2: (0.42, 0.09, 0.09), 3: (0.40, 0.08, 0.08), 4: (0.38, 0.07, 0.07), 5: (0.80, 0.62, 0.20)}
ca = me.color_attributes.new("c", 'FLOAT_COLOR', 'POINT')
ca.data.foreach_set("color", np.array([cols.get(int(k), (0.4, 0.1, 0.1)) + (1.0,) for k in sub]).ravel())
m = bpy.data.materials.new("m"); m.use_nodes = True; nt = m.node_tree; b = nt.nodes["Principled BSDF"]
at = nt.nodes.new("ShaderNodeAttribute"); at.attribute_name = "c"; nt.links.new(at.outputs["Color"], b.inputs["Base Color"])
b.inputs["Roughness"].default_value = 0.45; me.materials.append(m); me.shade_smooth()
gbc.setup_stage()
c = 0.5 * (lo + hi)
V = {"front": ((0.02, -0.45, 1.36), (0.015, -0.03, 1.34), 60), "tq": ((0.30, -0.35, 1.42), (0.015, -0.03, 1.34), 60),
     "back": ((0.0, 0.40, 1.36), (0.015, -0.03, 1.34), 60)}
for k, (l, t, fl) in V.items():
    gbc.render(os.path.join(out, f"h_{k}.png"), gbc.add_camera("C" + k, l, t, fl), 16, (420, 420))
print("DONE", len(v))
