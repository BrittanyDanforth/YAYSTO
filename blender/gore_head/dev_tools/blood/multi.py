"""Render many (preset, hit, view, seconds) jobs in one process.
usage: [NOREBUILD=1] python3 multi.py OUTPREFIX RES SAMPLES DIST job job ...
job = preset:hit:view1,view2:t1,t2
"""
import os, sys, time
HEAD = "/home/user/YAYSTO/blender/gore_head"
sys.path.insert(0, HEAD)
SCR = os.path.dirname(os.path.abspath(__file__))
sys.argv = [sys.argv[0]] + sys.argv[1:]
import bpy
from mathutils import Vector
NOREB = os.environ.get("NOREBUILD", "0") == "1"
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend" if NOREB else "base.blend"))
import gh_common as ghc, materials, gore, build
sys.path.insert(0, SCR)
from dev_cam import cam_for

def rebuild():
    t = time.time()
    if os.environ.get("REMAT", "0") == "1":
        mats = materials.build_materials()
    else:
        mats = {m.name: m for m in bpy.data.materials}
    gore.build_gore_node_group()
    bpy.data.node_groups[gore.GROUP_NAME]["gh_gore_version"] = gore._GROUP_VERSION
    gore.build_gore_system(None, mats)
    print(f"[multi] rebuilt in {time.time() - t:.1f}s")

out, res, samples, dist = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), float(sys.argv[4])
if not NOREB:
    rebuild()
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCR, "work.blend"), compress=False)
build.setup_cameras()
sc = bpy.context.scene
sc.render.threads_mode = 'FIXED'; sc.render.threads = 2
ctrl = ghc.ensure_controls()
cur = None
for job in sys.argv[5:]:
    preset, hit_name, views, times = job.split(":")
    if preset != cur:
        build.apply_preset(preset); cur = preset
    hit = bpy.data.objects[hit_name]
    for v in views.split(","):
        cam = cam_for(hit, v, dist)
        for s in times.split(","):
            ctrl["drip_time"] = float(s) / 60.0; ctrl.update_tag()
            t = time.time()
            path = os.path.join(SCR, f"{out}_{hit_name[7:]}_{v}_{int(float(s)):02d}s.png")
            ghc.render(path, cam, samples, (res, res))
            print(f"[multi] {path} {time.time() - t:.1f}s", flush=True)
