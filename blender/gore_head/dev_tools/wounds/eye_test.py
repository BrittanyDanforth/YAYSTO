"""eye_test.py OUT: eye damage close-ups: bullet into the right globe, blunt blow
to the left orbital rim (black eye, subconjunctival haemorrhage, hyphaema)."""
import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy
SCR = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend"))
import build, gore, gh_common as ghc
RES = int(os.environ.get("RES", "400")); S = int(os.environ.get("SAMPLES", "24"))
out = sys.argv[1]
build.setup_cameras()
build.apply_preset("intact")
ctrl = ghc.ensure_controls()
for k, v in dict(damage=1.0, bleed=0.8, drip_time=0.4, bruising=1.0, swelling=0.7, wound_age=0.3).items():
    ctrl[k] = v
ctrl.update_tag()
# right eye (character's right = -X): bullet from the front, slightly from the side
gore.add_hit("bullet", (-0.032, -0.085, 0.022), direction=(0.15, 1.0, 0.0), size=1.0, elongation=1.0,
             depth=1.0, name="GH_Hit_EyeShot")
# left orbit: a punch on the lateral orbital rim / cheekbone
gore.add_hit("blunt", (0.050, -0.070, 0.012), direction=(-0.6, 0.8, 0.1), size=1.0, depth=0.8,
             name="GH_Hit_BlackEye")
bpy.context.view_layer.update()
for name, loc, tgt in (("R", (-0.075, -0.20, 0.035), (-0.032, -0.072, 0.020)),
                       ("L", (0.085, -0.20, 0.035), (0.034, -0.072, 0.018)),
                       ("both", (0.0, -0.36, 0.03), (0.0, -0.07, 0.012))):
    cam = ghc.add_camera("ET_" + name, loc, tgt, 85.0)
    ghc.render(os.path.join(SCR, f"{out}_eye_{name}.png"), cam, S, (RES, RES))
    print("[eye]", name, flush=True)
