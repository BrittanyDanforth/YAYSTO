"""Scratch: render skeleton skull/mandible + mouth from a saved body blend (clay), and measure teeth-in-bone."""
import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np, gb_common as gbc
a = sys.argv[sys.argv.index('--') + 1:]
blend, out = a[0], a[1]; os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=blend)
show = {"GB_Skeleton", "GB_Mouth"}
for o in bpy.data.objects:
    if o.type in ('MESH', 'CURVE'):
        o.hide_render = o.name not in show
    if o.type == 'MESH':
        for m in o.modifiers:
            if m.type == 'ARMATURE': m.show_render = False
bone = bpy.data.materials.new("bone"); bone.use_nodes = True
b = bone.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.62, 0.56, 0.45, 1); b.inputs["Roughness"].default_value = 0.6
for n in show:
    o = bpy.data.objects.get(n)
    if o:
        for i in range(len(o.data.materials)): o.data.materials[i] = bone
gbc.setup_stage()
bpy.context.scene.world.color = (0.25, 0.25, 0.27)
z = 1.66 + 0.015
V = {"front": ((0, -0.55, z + 0.03), (0, 0.0, z), 70), "side": ((-0.55, 0.0, z + 0.03), (0, 0.0, z), 70),
     "tq": ((-0.40, -0.40, z - 0.03), (0, 0.0, z), 70), "under": ((-0.25, -0.30, z - 0.28), (0, 0.0, z - 0.03), 60),
     "back": ((0.30, 0.45, z - 0.01), (0, 0.0, z), 70)}
for k in (a[2] if len(a) > 2 else "front,side,tq,under").split(","):
    l, t, fl = V[k]
    gbc.render(os.path.join(out, f"s_{k}.png"), gbc.add_camera("C" + k, l, t, fl), 20, (480, 480))
print("DONE")
