"""Scratch: assembled head+neck (body blend) vs standalone gore_head GH_Skin from the SAME cameras (clay)."""
import sys, os; sys.path.insert(0, '/home/user/YAYSTO/blender/gore_body')
import bpy, numpy as np, gb_common as gbc
a = sys.argv[sys.argv.index('--') + 1:]
blend, out = a[0], a[1]; os.makedirs(out, exist_ok=True)
views = (a[2] if len(a) > 2 else "front,side,tq,back,under,backtq").split(",")
bpy.ops.wm.open_mainfile(filepath=blend)
keep = {"GB_Head", "GB_Body", "GB_Eye_L", "GB_Eye_R", "GB_Shorts"}
for o in list(bpy.data.objects):
    if o.type in ('MESH', 'CURVE') and o.name not in keep:
        o.hide_render = True
for o in bpy.data.objects:
    if o.type == 'MESH' and o.name in keep:
        for m in o.modifiers:
            if m.type == 'ARMATURE':
                m.show_render = False
clay = bpy.data.materials.new("clay"); clay.use_nodes = True
b = clay.node_tree.nodes["Principled BSDF"]; b.inputs["Base Color"].default_value = (0.55, 0.40, 0.34, 1)
b.inputs["Roughness"].default_value = 0.5
for n in ("GB_Head", "GB_Body"):
    o = bpy.data.objects[n]
    for i in range(len(o.data.materials)):
        o.data.materials[i] = clay
# standalone head: GH_Skin from the head project's saved scene, moved to the final body frame
hb = os.path.join(gbc.HEAD_SRC_DIR, "gore_head.blend")
with bpy.data.libraries.load(hb, link=False) as (src, dst):
    dst.objects = [n for n in src.objects if n == "GH_Skin"]
gh = dst.objects[0]
bpy.context.scene.collection.objects.link(gh)
for m in list(gh.modifiers):
    gh.modifiers.remove(m)
off = np.array(gbc.HEAD_OFFSET) + np.array([0.0, 0.0, gbc.NECK_LIFT])
gh.location = tuple(off)
gh.data.materials.clear(); gh.data.materials.append(clay)
gh.data.shade_smooth()
gbc.setup_stage()
for n in ("GB_Key", "GB_Fill", "GB_Rim"):
    o_ = bpy.data.objects.get(n)
    if o_ is not None: o_.data.energy *= 0.35
ld = bpy.data.lights.new("rk", 'SUN'); ld.energy = 3.0; lo = bpy.data.objects.new("rk", ld)
bpy.context.scene.collection.objects.link(lo); lo.rotation_euler = (np.radians(62), 0, np.radians(-30))
z0 = 1.56
V = {"side": ((-0.75, -0.02, z0 + 0.02), (0, -0.005, z0 - 0.01), 85), "tq": ((-0.45, -0.60, z0 + 0.04), (0, 0, z0 - 0.01), 85),
     "front": ((0, -0.8, z0 + 0.02), (0, 0, z0 - 0.01), 85), "back": ((0.30, 0.75, z0 - 0.01), (0, 0.02, z0 - 0.04), 85),
     "under": ((-0.25, -0.55, 1.40), (0, -0.02, z0 - 0.005), 85), "backtq": ((0.45, 0.55, z0 + 0.07), (0, 0.03, z0 - 0.02), 85),
     "sidelow": ((-0.75, -0.05, 1.49), (0, 0.0, 1.52), 85)}
for k in views:
    l, t, f = V[k]
    cam = gbc.add_camera("C" + k, l, t, f)
    for which in ("asm", "std"):
        for n in ("GB_Head", "GB_Body", "GB_Eye_L", "GB_Eye_R", "GB_Shorts"):
            o = bpy.data.objects.get(n)
            if o is not None: o.hide_render = which == "std"
        gh.hide_render = which == "asm"
        gbc.render(os.path.join(out, f"{k}_{which}.png"), cam, 16, (420, 420))
print("DONE")
