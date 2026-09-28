"""Dev harness: load the built head, rebuild the gore group from the working
gore.py (and optionally the materials), apply a preset and render close-ups.

usage: python3 dev.py PRESET HIT_NAME TIMES(comma s) VIEWS(comma: straight,45,graze,wide) OUTPREFIX [res] [samples] [dist]
"""
import os
import sys
import time

HEAD = "/home/user/YAYSTO/blender/gore_head"
sys.path.insert(0, HEAD)
SCR = os.path.dirname(os.path.abspath(__file__))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

NOREB = os.environ.get("NOREBUILD", "0") == "1"
bpy.ops.wm.open_mainfile(filepath=os.path.join(SCR, "work.blend" if NOREB else "base.blend"))
import gh_common as ghc  # noqa: E402
import materials  # noqa: E402
import gore  # noqa: E402
import build  # noqa: E402

REBUILD_MATS = os.environ.get("REMAT", "0") == "1"


def rebuild():
    t = time.time()
    if REBUILD_MATS:
        mats = materials.build_materials()
    else:
        mats = {m.name: m for m in bpy.data.materials}
    gore.build_gore_node_group()
    bpy.data.node_groups[gore.GROUP_NAME]["gh_gore_version"] = gore._GROUP_VERSION
    gore.build_gore_system(None, mats)
    print(f"[dev] rebuilt in {time.time() - t:.1f}s")


def cam_for(hit, view, dist):
    if view in build.CAMERAS:
        return bpy.data.objects["GH_Cam_" + view]
    m = hit.matrix_world.to_3x3().normalized()
    z = (m @ Vector((0.0, 0.0, 1.0))).normalized()
    # look at the point just below the hit: rim + first cm of the stream
    tgt = hit.matrix_world.translation + Vector((0, 0, -0.006))
    horiz = Vector((0, 0, 1)).cross(z).normalized()
    if view == "straight":
        d = z
    elif view == "45":
        d = (z + horiz * 1.0).normalized()
    elif view == "graze":
        # grazing along the surface from below-side: 75 deg off the normal
        d = (z * 0.26 + (horiz * 0.7 + Vector((0, 0, -0.7))).normalized() * 0.97).normalized()
    elif view == "wide":
        d = (z + horiz * 0.5 + Vector((0, 0, 0.2))).normalized()
        dist = dist * 2.6
        tgt = tgt + Vector((0, 0, -0.03))
    return ghc.add_camera(f"DEV_{view}", tgt + d * dist, tgt, 85.0)


def main():
    a = sys.argv[1:]
    preset, hit_name, times, views, out = a[0], a[1], a[2], a[3], a[4]
    res = int(a[5]) if len(a) > 5 else 320
    samples = int(a[6]) if len(a) > 6 else 24
    dist = float(a[7]) if len(a) > 7 else 0.07
    if not NOREB:
        rebuild()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCR, "work.blend"), compress=False)
    cams = build.setup_cameras()
    build.apply_preset(preset)
    sc = bpy.context.scene
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 2
    ctrl = ghc.ensure_controls()
    for hit_name in hit_name.split("+"):
      hit = bpy.data.objects[hit_name]
      for v in views.split(","):
        cam = cam_for(hit, v, dist)
        for s in times.split(","):
            ctrl["drip_time"] = float(s) / 60.0
            ctrl.update_tag()
            t = time.time()
            path = os.path.join(SCR, f"{out}_{hit_name[7:]}_{v}_{int(float(s)):02d}s.png")
            ghc.render(path, cam, samples, (res, res))
            print(f"[dev] {path} {time.time() - t:.1f}s")


main()
