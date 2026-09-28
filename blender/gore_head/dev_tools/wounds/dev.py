"""Dev harness for the wound fix pass: load the built head, rebuild the gore
group (and optionally materials) from the working files, apply presets and
render views.

usage: GH_THREADS=2 python3 dev.py OUTPREFIX JOB [JOB ...]
  JOB = preset/hit/views/times[/dist]
    hit   = hit empty name (GH_Hit_...) or '-' for preset cameras
    views = comma list: front,three_q,side,back (preset cams) or straight,45,graze,wide,up,profile
    times = comma list of seconds (drip time)
env: REMAT=1 rebuild materials, RES=400, SAMPLES=24, NOREBUILD=1 use work.blend
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

RES = int(os.environ.get("RES", "400"))
SAMPLES = int(os.environ.get("SAMPLES", "24"))


def rebuild():
    t = time.time()
    if os.environ.get("REMAT", "0") == "1":
        mats = materials.build_materials()
        objs = {o.name: o for o in bpy.data.objects}
        materials.assign_materials(objs, mats)
    else:
        mats = {m.name: m for m in bpy.data.materials}
    gore.build_gore_node_group()
    ng = bpy.data.node_groups[gore.GROUP_NAME]
    ng["gh_gore_version"] = gore._GROUP_VERSION
    if os.environ.get("FULL", "0") == "1":
        gore.build_gore_system(None, mats)
    else:
        # light re-wire: keep the snapped vessels and the baked bone depth
        vessels = bpy.data.objects[gore.VESSEL_OBJECT]
        ident = {it.name: it.identifier for it in ng.interface.items_tree
                 if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
        walls, blood, bone = gore._wall_materials(mats)
        strand = mats.get("GH_Muscle") or walls[gore.LAYER_MUSCLE]
        cols = gore.ensure_hit_collections()
        for name, layer in gore.LAYERS.items():
            ob = bpy.data.objects.get(name)
            if ob is None:
                continue
            mod = ob.modifiers[gore.MOD_NAME]
            mod.node_group = ng
            mod[ident["Layer"]] = layer
            for k in gore.KINDS:
                mod[ident[f"{k.capitalize()} Hits"]] = cols[k]
            if name in gore.OWN_WALL_MATERIAL:
                wall = gore._object_material(ob) or walls.get(layer) or bone
            else:
                wall = walls.get(layer) or gore._object_material(ob) or bone
            mod[ident["Wall Material"]] = wall
            mod[ident["Blood Material"]] = blood
            mod[ident["Bone Material"]] = bone
            mod[ident["Strand Material"]] = strand
            mod[ident["Pulp Material"]] = mats.get("GH_Brain") or strand
            mod[ident["Tooth Root"]] = -1.0 if name.endswith("Lower") else 1.0
            mod[ident["Vessels"]] = vessels
            if ob.animation_data is not None:
                for fc in list(ob.animation_data.drivers):
                    if fc.data_path.startswith(f'modifiers["{gore.MOD_NAME}"]'):
                        ob.animation_data.drivers.remove(fc)
            for prop, sock in (("damage", "Damage"), ("bleed", "Bleed"), ("drip_time", "Drip Time"),
                               ("bruising", "Bruising"), ("swelling", "Swelling"), ("wound_age", "Wound Age")):
                ghc.drive(ob, f'modifiers["{gore.MOD_NAME}"]["{ident[sock]}"]', prop)
    print(f"[dev] rebuilt in {time.time() - t:.1f}s")


def cam_for(hit, view, dist):
    if view.startswith("cam:"):
        _, a, b = view.split(":")
        return ghc.add_camera("DEV_custom", tuple(map(float, a.split(";"))), tuple(map(float, b.split(";"))), 85.0)
    if hit is None or view in build.CAMERAS:
        return bpy.data.objects["GH_Cam_" + view]
    m = hit.matrix_world.to_3x3().normalized()
    z = (m @ Vector((0.0, 0.0, 1.0))).normalized()
    tgt = hit.matrix_world.translation + Vector((0, 0, -0.004))
    horiz = Vector((0, 0, 1)).cross(z).normalized()
    if view == "straight":
        d = z
    elif view == "45":
        d = (z + horiz * 1.0).normalized()
    elif view == "graze":
        d = (z * 0.26 + (horiz * 0.7 + Vector((0, 0, -0.7))).normalized() * 0.97).normalized()
    elif view == "profile":
        d = (z * 0.12 + horiz).normalized()
    elif view == "up":
        d = (z + Vector((0, 0, 0.6))).normalized()
    elif view == "wide":
        d = (z + horiz * 0.5 + Vector((0, 0, 0.2))).normalized()
        dist = dist * 2.6
        tgt = tgt + Vector((0, 0, -0.02))
    return ghc.add_camera(f"DEV_{view}", tgt + d * dist, tgt, 85.0)


def main():
    a = sys.argv[1:]
    out = a[0]
    if not NOREB:
        rebuild()
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(SCR, "work.blend"), compress=False)
    build.setup_cameras()
    for nm in os.environ.get("HIDE", "").split(","):
        if nm and bpy.data.objects.get(nm):
            bpy.data.objects[nm].hide_render = True
    sc = bpy.context.scene
    ctrl = ghc.ensure_controls()
    for job in a[1:]:
        parts = job.split("/")
        preset, hit_name, views, times = parts[:4]
        dist = float(parts[4]) if len(parts) > 4 else 0.07
        build.apply_preset(preset)
        for kv in os.environ.get("CTRL", "").split(","):
            if kv:
                k, v = kv.split("=")
                ctrl[k] = float(v)
        ctrl.update_tag()
        hit = None if hit_name == "-" else bpy.data.objects[hit_name]
        for v in views.split(","):
            cam = cam_for(hit, v, dist)
            for s in times.split(","):
                ctrl["drip_time"] = float(s) / 60.0
                ctrl.update_tag()
                t = time.time()
                tag = preset if hit is None else hit_name[7:]
                vt = "cam" if v.startswith("cam:") else v
                path = os.path.join(SCR, f"{out}_{tag}_{vt}{views.split(',').index(v)}_{int(float(s)):02d}s.png")
                ghc.render(path, cam, SAMPLES, (RES, RES))
                print(f"[dev] {path} {time.time() - t:.1f}s", flush=True)


main()
