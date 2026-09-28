import sys, os
sys.path.insert(0, "/home/user/YAYSTO/blender/gore_head")
import bpy
SCR = os.path.dirname(os.path.abspath(__file__))
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend"))
import build, gh_common as ghc, materials
RES = int(os.environ.get("RES", "400")); S = int(os.environ.get("SAMPLES", "20"))
build.setup_cameras()
build.apply_preset("intact")
objs = {o.name: o for o in bpy.data.objects}
cleanup = build.add_cutaway(objs)
bpy.context.scene.view_settings.exposure = materials.STAGE_EXPOSURE
for name, loc, tgt in (("wide", (0.58, -0.40, 0.07), (0.0, -0.02, -0.01)),
                       ("eye", (0.20, -0.14, 0.03), (0.03, -0.068, 0.022)),
                       ("brain", (0.40, -0.05, 0.10), (0.03, 0.01, 0.04))):
    cam = ghc.add_camera("CT_" + name, loc, tgt, 85.0 if name == "wide" else 100.0)
    ghc.render(os.path.join(SCR, f"{sys.argv[1]}_cut_{name}.png"), cam, S, (RES, RES))
    print("[cut]", name, flush=True)
