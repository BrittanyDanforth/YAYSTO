"""idpass.py PRESET HIT VIEW DIST OUT: flat material-ID render (blood green, fat blue, muscle yellow, skin grey)."""
import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy
from mathutils import Vector
SCR = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend"))
import build, gh_common as ghc
preset, hn, view, dist, out = sys.argv[1:6]
build.setup_cameras(); build.apply_preset(preset)
ctrl = ghc.ensure_controls(); ctrl["drip_time"] = 40 / 60.0; ctrl.update_tag()
cols = {"GH_Blood": (0, 1, 0), "GH_Fat": (0, 0, 1), "GH_Muscle": (1, 1, 0), "GH_Skin": (0.4, 0.4, 0.4)}
for name, c in cols.items():
    m = bpy.data.materials[name]; nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs[0].default_value = (*c, 1); o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0], o.inputs[0])
hit = bpy.data.objects[hn]
m = hit.matrix_world.to_3x3().normalized(); z = (m @ Vector((0, 0, 1))).normalized()
tgt = hit.matrix_world.translation + Vector((0, 0, -0.004)); horiz = Vector((0, 0, 1)).cross(z).normalized()
d = z if view == "straight" else (z + horiz).normalized()
cam = ghc.add_camera("ID", tgt + d * float(dist), tgt, 85.0)
ghc.render(os.path.join(SCR, out), cam, 1, (300, 300))
