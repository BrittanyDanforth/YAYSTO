"""Assemble the procedural gore head: anatomy, materials, live gore, presets.

Everything is generated from code (see CONTRACT.md): no downloaded meshes,
textures, HDRIs or add-ons.  This script

  1. builds every anatomical layer (anatomy.py),
  2. builds and assigns the procedural materials (materials.py),
  3. adds the live, layered gore system (gore.py),
  4. sets up the stage lighting and one camera per view,
  5. renders every wound preset, a side cutaway of the intact head and a
     close-up of the gunshot exit wound into renders/,
  6. saves gore_head.blend with the 'gunshot' preset active and an animation
     (damage 0 -> 1 over frames 1-12, drip_time 0 -> 1 over frames 12-120).

Usage (bpy module or Blender):

    python3 build.py [--preset NAME] [--no-render] [--out FILE] [--samples N] [--res N]
    blender -b --python build.py -- [same options]

--preset NAME   preset that is active in the saved file (default: gunshot); when
                given, only that preset is rendered
--no-render     build and save only
--out FILE      .blend path (default: gore_head.blend next to this script)
--samples N     Cycles samples per render (default 40, denoised)
--res N         square render resolution (default 640)
--only A,B      render only these items: preset names, 'cutaway', 'closeup_exit'
--render-dir D  where the PNGs go (default: renders/)
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import gh_common as ghc  # noqa: E402
import anatomy  # noqa: E402
import materials  # noqa: E402
import gore  # noqa: E402

BLEND_NAME = "gore_head.blend"
ANIM_FRAMES = (1, 120)
DAMAGE_KEYS = ((1, 0.0), (12, 1.0))
DRIP_KEYS = ((12, 0.0), (120, 1.0))

# ---------------------------------------------------------------------------
# Presets
# ---------------------------------------------------------------------------
# A hit is (kind, location, keyword arguments for gore.add_hit). Locations are
# rough points near the skin in head space (metres, face toward -Y, character's
# right = -X); add_hit snaps them onto the surface. `toward` (build.py only)
# aims the hit at a point instead of giving a direction: the wound track then
# runs from the hit toward that point.

# bullet path of the gunshot: right temple -> left side of the back of the head
_ENTRY = (-0.070, -0.040, 0.046)
_EXIT = (0.052, 0.066, 0.058)

PRESETS = {
    "intact": dict(
        hits=[],
        controls={},
    ),
    "gunshot": dict(
        hits=[
            ("bullet", _ENTRY, dict(toward=_EXIT, size=1.0, depth=1.0, name="GH_Hit_Entry")),
            ("exit", _EXIT, dict(toward=_ENTRY, size=1.25, depth=1.0, name="GH_Hit_Exit")),
        ],
        controls=dict(bleed=0.85, drip_time=1.0),
    ),
    "slash": dict(
        hits=[
            # deep cut down across the right cheek, from below the cheekbone toward the jaw
            ("slash", (-0.050, -0.078, -0.028), dict(size=1.15, elongation=2.6, depth=0.8, roll=-0.55,
                                                     name="GH_Hit_Slash_Cheek")),
            # shallower cut across the forehead
            ("slash", (0.004, -0.090, 0.066), dict(size=1.0, elongation=3.0, depth=0.5, roll=0.12,
                                                   name="GH_Hit_Slash_Forehead")),
        ],
        controls=dict(bleed=0.8),
    ),
    "blunt": dict(
        hits=[
            # jaw / mouth: splits the lip, knocks out and tilts front teeth
            ("blunt", (-0.010, -0.100, -0.056), dict(size=1.0, depth=0.75, name="GH_Hit_Blunt_Jaw")),
            # cranium: depressed skull fracture
            ("blunt", (-0.052, -0.035, 0.092), dict(size=1.2, depth=0.9, name="GH_Hit_Blunt_Cranium")),
        ],
        controls=dict(bleed=0.7, bruising=0.8, swelling=0.6),
    ),
    "burn": dict(
        hits=[
            # overlapping burns covering the right half of the face
            ("burn", (-0.042, -0.080, -0.010), dict(size=1.7, elongation=1.3, depth=0.6, name="GH_Hit_Burn_Cheek")),
            ("burn", (-0.040, -0.075, 0.050), dict(size=1.3, elongation=1.0, depth=0.5, name="GH_Hit_Burn_Brow")),
            ("burn", (-0.040, -0.060, -0.070), dict(size=1.2, elongation=1.0, depth=0.5, name="GH_Hit_Burn_Jaw")),
        ],
        controls=dict(bleed=0.5),
    ),
    "carnage": dict(
        hits=[
            ("bullet", (0.018, -0.092, 0.075), dict(toward=(-0.02, 0.09, 0.07), depth=1.0, name="GH_Hit_C_Entry")),
            ("exit", (-0.055, -0.045, 0.080), dict(size=1.5, depth=1.0, name="GH_Hit_C_Exit_Temple")),
            ("exit", (-0.020, 0.090, 0.070), dict(size=1.2, depth=1.0, name="GH_Hit_C_Exit_Back")),
            ("slash", (-0.052, -0.072, -0.030), dict(size=1.1, elongation=2.4, depth=0.8, roll=-0.5,
                                                     name="GH_Hit_C_Slash_Cheek")),
            ("slash", (0.045, -0.075, 0.000), dict(size=1.0, elongation=2.0, depth=0.6, roll=0.7,
                                                   name="GH_Hit_C_Slash_L")),
            ("blunt", (-0.010, -0.100, -0.056), dict(size=1.0, depth=0.8, name="GH_Hit_C_Blunt_Jaw")),
            ("burn", (0.050, -0.050, 0.030), dict(size=1.1, elongation=1.2, depth=0.6, name="GH_Hit_C_Burn")),
        ],
        controls=dict(bleed=1.0, bruising=0.8, swelling=0.6),
    ),
}
PRESET_NAMES = tuple(PRESETS)

# control values every preset starts from (then its own overrides)
BASE_CONTROLS = dict(damage=1.0, bleed=0.7, drip_time=1.0, wetness=0.8, blood_age=0.0,
                     bruising=0.6, swelling=0.5, skin_tone=0.25, pallor=0.0)


def _aim(location, target):
    """Direction from a surface point toward a target inside / across the head."""
    return (Vector(target) - Vector(location)).normalized()


def apply_preset(name):
    """Replace every hit with the hits of preset `name` and set its control values.

    Returns the list of hit empties that were created.
    """
    if name not in PRESETS:
        raise ValueError(f"unknown preset {name!r}, expected one of {PRESET_NAMES}")
    preset = PRESETS[name]
    gore.clear_hits()
    ctrl = ghc.ensure_controls()
    # keyframes would override the control values; presets are static states
    if ctrl.animation_data is not None:
        ctrl.animation_data_clear()
    for prop, value in dict(BASE_CONTROLS, **preset["controls"]).items():
        ctrl[prop] = value
    ctrl.update_tag()
    empties = []
    for kind, loc, kw in preset["hits"]:
        kw = dict(kw)
        target = kw.pop("toward", None)
        if target is not None:
            kw["direction"] = _aim(loc, target)
        empties.append(gore.add_hit(kind, loc, **kw))
    bpy.context.scene["gh_preset"] = name
    bpy.context.view_layer.update()
    return empties


# ---------------------------------------------------------------------------
# Stage, cameras, animation
# ---------------------------------------------------------------------------
# name: (location, target, lens)
CAMERAS = {
    "front":   ((0.0, -0.78, 0.035), (0.0, -0.02, 0.005), 85.0),
    "three_q": ((-0.52, -0.56, 0.12), (-0.005, -0.02, 0.01), 85.0),
    "side":    ((-0.78, -0.02, 0.035), (0.0, -0.02, 0.005), 85.0),
    "back":    ((0.40, 0.66, 0.20), (0.0, 0.01, 0.02), 85.0),
}


def setup_cameras():
    """Stage lights and one camera per view (GH_Cam_<view>). Returns {view: camera}."""
    ghc.setup_stage()
    scene = bpy.context.scene
    scene.view_settings.exposure = materials.STAGE_EXPOSURE
    cams = {}
    for view, (loc, tgt, lens) in CAMERAS.items():
        cams[view] = ghc.add_camera(f"GH_Cam_{view}", loc, tgt, lens)
    scene.camera = cams["front"]
    return cams


def closeup_camera(hit, name="GH_Cam_closeup_exit", dist=0.15, lens=85.0, tilt=0.18, offset=(0.0, 0.0, -0.012)):
    """Camera looking at a hit from outside along its axis, slightly from above."""
    z = (hit.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))).normalized()
    view = (z + Vector((0.0, 0.0, tilt))).normalized()
    target = hit.matrix_world.translation + Vector(offset)
    return ghc.add_camera(name, target + view * dist, target, lens)


def animate_controls(frames=ANIM_FRAMES):
    """Keyframe GH_Controls: damage 0 -> 1 over 1-12, drip_time 0 -> 1 over 12-120."""
    scene = bpy.context.scene
    ctrl = ghc.ensure_controls()
    if ctrl.animation_data is not None:
        ctrl.animation_data_clear()
    for prop, keys in (("damage", DAMAGE_KEYS), ("drip_time", DRIP_KEYS)):
        for frame, value in keys:
            ctrl[prop] = value
            ctrl.keyframe_insert(f'["{prop}"]', frame=frame)
    # ease out: the wound opens fast, the blood slows down as it runs
    for fc in ctrl.animation_data.action.fcurves if hasattr(ctrl.animation_data.action, "fcurves") else []:
        for kp in fc.keyframe_points:
            kp.interpolation = 'BEZIER'
    scene.frame_start, scene.frame_end = frames
    scene.render.fps = 24
    return ctrl


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------
def build_scene():
    """Build anatomy, materials and the gore system from scratch.

    Returns (objs, mats, timings) where timings maps step -> seconds.
    """
    timings = {}
    t0 = time.time()
    ghc.reset_scene()
    ghc.ensure_controls()
    objs = anatomy.build_anatomy()
    timings["anatomy"] = time.time() - t0
    t = time.time()
    mats = materials.build_materials()
    materials.assign_materials(objs, mats)
    timings["materials"] = time.time() - t
    t = time.time()
    gore.build_gore_system(objs, mats)
    timings["gore"] = time.time() - t
    setup_cameras()
    timings["build"] = time.time() - t0
    return objs, mats, timings


def evaluate_all(objs):
    """Force a full evaluation of every layer (all modifiers). Returns seconds."""
    for ob in objs.values():
        ob.update_tag()
    t0 = time.time()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    for ob in objs.values():
        if ob.type == 'MESH':
            ev = ob.evaluated_get(dg)
            ev.to_mesh()
            ev.to_mesh_clear()
    return time.time() - t0


# ---------------------------------------------------------------------------
# Cutaway
# ---------------------------------------------------------------------------
CUT_LAYERS = {"GH_Skin_cut": 0, "GH_Muscle": 1, "GH_Skull": 2, "GH_Jaw": 2, "GH_Eye_L": 2,
              "GH_Gums": 2, "GH_Brain": 3, "GH_Teeth_Upper": 3, "GH_Teeth_Lower": 3, "GH_Tongue": 3}


def add_cutaway(objs, x_hi=0.030, x_lo=0.003, z_step=-0.036):
    """Cut the head open on the character's left: x > x_hi everywhere (through
    the left eye) and x > x_lo below z_step (the mid-line of mouth and jaw).

    The skin is open at the lips, so a closed copy (skin + mouth lining) is cut
    instead. Returns a cleanup function that restores the scene.
    """
    import bmesh
    skin, cav = objs["GH_Skin"], objs["GH_MouthCavity"]
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    n_skin = len(bm.faces)
    bm.from_mesh(cav.data)
    bm.faces.ensure_lookup_table()
    for f in bm.faces[n_skin:]:
        f.material_index = 1
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    me = bpy.data.meshes.new("GH_Skin_cut")
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.materials.append(skin.data.materials[0])
    me.materials.append(cav.data.materials[0])
    joined = bpy.data.objects.new("GH_Skin_cut", me)
    ghc.get_collection("GoreHead").objects.link(joined)
    hidden = [skin, cav]
    for ob in hidden:
        ob.hide_render = True
    obs = dict(objs, GH_Skin_cut=joined)
    added = []
    for name, lvl in CUT_LAYERS.items():
        # an L-shaped prism (profile in x/z, extruded along y); inner layers are
        # cut slightly further out so their caps step back from the outer caps
        off = 0.0006 * lvl
        prof = [(x_lo + off, -1.0), (1.0, -1.0), (1.0, 1.0), (x_hi + off, 1.0),
                (x_hi + off, z_step), (x_lo + off, z_step)]
        n = len(prof)
        verts = [(px, -1.0, pz) for px, pz in prof] + [(px, 1.0, pz) for px, pz in prof]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i)[::-1] for i in range(n)]
        cm = bpy.data.meshes.new(f"GH_cut_{name}")
        cm.from_pydata(verts, [], faces)
        cm.validate()
        cutter = bpy.data.objects.new(f"GH_cut_{name}", cm)
        ghc.get_collection("Stage").objects.link(cutter)
        cutter.hide_render = cutter.hide_viewport = True
        mod = obs[name].modifiers.new("GH_Cutaway", 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'MANIFOLD'
        mod.object = cutter
        added.append((obs[name], mod, cutter))

    def cleanup():
        for ob, mod, cutter in added:
            ob.modifiers.remove(mod)
            bpy.data.objects.remove(cutter, do_unlink=True)
        bpy.data.objects.remove(joined, do_unlink=True)
        bpy.data.meshes.remove(me)
        for ob in hidden:
            ob.hide_render = False
    return cleanup


# ---------------------------------------------------------------------------
# Renders
# ---------------------------------------------------------------------------
def _render(path, cam, samples, res):
    t = time.time()
    bpy.context.scene.view_settings.exposure = materials.STAGE_EXPOSURE
    ghc.render(path, cam, samples, (res, res))
    dt = time.time() - t
    print(f"[build] rendered {os.path.relpath(path, HERE)} in {dt:.1f} s")
    return dt


def render_all(objs, presets, out_dir, samples=40, res=640, only=None):
    """Render the presets (front + three_q), the cutaway and the exit close-up.

    Returns {image name: seconds}.
    """
    want = (lambda k: only is None or k in only)  # noqa: E731
    cams = setup_cameras()
    times = {}
    for name in presets:
        if not want(name):
            continue
        apply_preset(name)
        for view in ("front", "three_q"):
            key = f"preset_{name}_{view}"
            times[key] = _render(os.path.join(out_dir, key + ".png"), cams[view], samples, res)
    if want("closeup_exit"):
        apply_preset("gunshot")
        hit = bpy.data.objects["GH_Hit_Exit"]
        cam = closeup_camera(hit)
        times["closeup_exit"] = _render(os.path.join(out_dir, "closeup_exit.png"), cam, samples, res)
    if want("cutaway"):
        apply_preset("intact")
        cleanup = add_cutaway(objs)
        cam = ghc.add_camera("GH_Cam_cutaway", (0.58, -0.40, 0.07), (0.0, -0.02, -0.01), 85.0)
        times["cutaway"] = _render(os.path.join(out_dir, "cutaway.png"), cam, samples, res)
        cleanup()
    bpy.context.scene.camera = cams["front"]
    return times


def save_blend(path, preset="gunshot"):
    """Apply `preset`, animate the controls and save a compressed .blend (relative paths)."""
    scene = bpy.context.scene
    apply_preset(preset)
    animate_controls()
    hit = bpy.data.objects.get("GH_Hit_Exit")
    if hit is not None:
        closeup_camera(hit)
    scene.camera = bpy.data.objects["GH_Cam_front"]
    scene.frame_set(ANIM_FRAMES[1])
    # compact, reasonably fast defaults for whoever opens the file
    ghc.configure_render(40, (1080, 1080))
    scene.view_settings.exposure = materials.STAGE_EXPOSURE
    path = os.path.abspath(path)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, relative_remap=True)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args(argv=None):
    """Parse options (after '--' when run as `blender -b --python build.py -- ...`)."""
    import argparse
    if argv is None:
        argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(prog="build.py", description="Build the procedural gore head.")
    p.add_argument("--preset", choices=PRESET_NAMES, default=None,
                   help="preset active in the saved file (default gunshot); limits the renders to it")
    p.add_argument("--no-render", action="store_true", help="build and save only")
    p.add_argument("--out", default=os.path.join(HERE, BLEND_NAME), help=".blend output path")
    p.add_argument("--samples", type=int, default=40)
    p.add_argument("--res", type=int, default=640)
    p.add_argument("--only", default=None, help="comma list: preset names, cutaway, closeup_exit")
    p.add_argument("--render-dir", default=ghc.RENDER_DIR)
    return p.parse_args(argv)


def main():
    args = parse_args()
    objs, mats, timings = build_scene()
    print("[build] anatomy %.1f s, materials %.1f s, gore %.1f s, total build %.1f s"
          % (timings["anatomy"], timings["materials"], timings["gore"], timings["build"]))
    for name in PRESET_NAMES:
        apply_preset(name)
        print(f"[build] evaluate '{name}': {evaluate_all(objs):.2f} s")
    if not args.no_render:
        presets = (args.preset,) if args.preset else PRESET_NAMES
        only = set(args.only.split(",")) if args.only else None
        times = render_all(objs, presets, args.render_dir, args.samples, args.res, only)
        print("[build] render times: " + ", ".join(f"{k} {v:.0f} s" for k, v in times.items()))
    path = save_blend(args.out, args.preset or "gunshot")
    print(f"[build] saved {path} ({os.path.getsize(path) / 1e6:.1f} MB)")


if __name__ == "__main__":
    main()
