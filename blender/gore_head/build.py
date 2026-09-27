"""Assemble the procedural gore head: anatomy, materials, live gore, presets.

Everything is generated from code (see CONTRACT.md): no downloaded meshes,
textures, HDRIs or add-ons.  This script

  1. builds every anatomical layer (anatomy.py),
  2. builds and assigns the procedural materials (materials.py),
  3. adds the live, layered gore system (gore.py),
  4. grows eyebrows and eyelashes (hair curves) that follow the wounded skin,
  5. sets up the stage lighting and one camera per view,
  6. renders every wound preset, a side cutaway of the intact head, a
     close-up of the gunshot exit wound, the blood time sequence, a wound
     contact sheet, the hero image and the 4-stage strip into renders/,
  7. saves gore_head.blend with the 'gunshot' preset active and an animation
     (damage 0 -> 1 over frames 1-12, drip_time 0 -> 1 over frames 12-120).

Usage (bpy module or Blender):

    python3 build.py [--preset NAME] [--no-render] [--out FILE] [--samples N] [--res N]
    blender -b --python build.py -- [same options]

--preset NAME   preset that is active in the saved file (default: gunshot); when
                given, only that preset's views are rendered (plus the cutaway
                and the exit close-up, unless --only says otherwise)
--no-render     build and save only
--out FILE      .blend path (default: gore_head.blend next to this script)
--samples N     Cycles samples per render (default 40, denoised)
--res N         square render resolution (default 640)
--only A,B      render only these items: preset names, 'cutaway', 'closeup_exit',
                'sequence', 'contact_sheet', 'hero', 'stages'
--render-dir D  where the PNGs go (default: renders/)
--force         render and save even when the verification fails (exit code 1 then)

The saved file asks Cycles for the GPU; Blender uses the CPU when no GPU
compute device is set up in Preferences > System.
"""
import math
import os
import sys
import time

import bpy
import numpy as np
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
            # mouth / jaw (right of the mid-line): split lips, the right front
            # teeth knocked out or pushed in, the left ones still in place
            # (aimed at the lower lip: a point in the lip gap would land on the teeth)
            ("blunt", (-0.009, -0.099, -0.064), dict(toward=(-0.004, -0.07, -0.058), size=1.0, depth=0.84,
                                                     name="GH_Hit_Blunt_Jaw")),
            # cranium: burst scalp over a depressed skull fracture
            ("blunt", (-0.052, -0.035, 0.092), dict(size=1.2, depth=0.95, name="GH_Hit_Blunt_Cranium")),
        ],
        # ~3 h after the blows: swollen, bruised
        controls=dict(bleed=0.75, bruising=0.8, swelling=0.6, wound_age=0.25),
    ),
    "burn": dict(
        hits=[
            # a large burn over the right half of the face (local Y ~ vertical),
            # a second one continuing it down over the jaw
            ("burn", (-0.045, -0.076, 0.015), dict(size=2.3, elongation=1.35, depth=0.7, name="GH_Hit_Burn_Face")),
            ("burn", (-0.040, -0.072, -0.060), dict(size=1.9, elongation=1.1, depth=0.6, roll=0.4,
                                                    name="GH_Hit_Burn_Jaw")),
        ],
        # ~1 h after the burn: blisters have formed
        controls=dict(bleed=0.5, wound_age=0.15),
    ),
    "carnage": dict(
        hits=[
            # shot from behind: entry low on the left of the back of the head, a
            # large torn exit over the right temple (9 mm: at most ~30 mm across,
            # pulped brain and bone chips in the opening -- a handgun does not
            # blow the skull open; that needs a rifle or a contact shotgun)
            ("bullet", (0.050, 0.070, 0.050), dict(toward=(-0.052, -0.060, 0.075), depth=1.0,
                                                   name="GH_Hit_C_Entry_Back")),
            ("exit", (-0.052, -0.060, 0.075), dict(toward=(0.050, 0.070, 0.050), size=1.5, depth=1.0,
                                                   name="GH_Hit_C_Exit_Temple")),
            # second shot: entry in the left forehead, exit behind the right ear
            ("bullet", (0.026, -0.089, 0.066), dict(toward=(-0.050, 0.070, 0.020), depth=1.0,
                                                    name="GH_Hit_C_Entry_Forehead")),
            ("exit", (-0.050, 0.070, 0.020), dict(toward=(0.026, -0.089, 0.066), size=1.2, depth=1.0,
                                                  name="GH_Hit_C_Exit_Back")),
            # face: deep gash across the right cheek, a cut over the left brow
            ("slash", (-0.050, -0.076, -0.030), dict(size=1.15, elongation=2.5, depth=0.85, roll=-0.55,
                                                     name="GH_Hit_C_Slash_Cheek")),
            ("slash", (0.040, -0.082, 0.045), dict(size=1.0, elongation=1.8, depth=0.55, roll=0.35,
                                                   name="GH_Hit_C_Slash_Brow")),
            # smashed mouth
            ("blunt", (-0.006, -0.099, -0.064), dict(toward=(0.0, -0.07, -0.058), size=1.0, depth=0.86,
                                                     name="GH_Hit_C_Blunt_Jaw")),
            # cut throat
            ("slash", (0.0, -0.050, -0.135), dict(size=1.2, elongation=3.2, depth=0.8, roll=0.08,
                                                  name="GH_Hit_C_Slash_Throat")),
            # burned left cheek and jaw
            ("burn", (0.046, -0.068, -0.035), dict(size=1.5, elongation=1.3, depth=0.6, name="GH_Hit_C_Burn")),
        ],
        controls=dict(bleed=1.0, bruising=0.8, swelling=0.4),
    ),
    "blast": dict(
        hits=[
            # explosive / contact blast in the open mouth (REFERENCE_NOTES §5.11,
            # refs/13): the lower-mid face torn open, a mandible segment with
            # its teeth hanging out, loose and missing teeth, soot and searing
            ("blast", (0.0, -0.12, -0.056), dict(direction=(0.0, 1.0, 0.0), size=1.5, depth=1.0,
                                                 name="GH_Hit_Blast_Mouth")),
        ],
        controls=dict(bleed=1.0, bruising=0.6, swelling=0.5, wound_age=0.1),
    ),
    "crushed": dict(
        hits=[
            # repeated heavy blows to the right mid-face (REFERENCE_NOTES §5.13,
            # refs/15-16): the blows' energy adds up, the cheek and orbit cave
            # in, skin tears away in flaps, bone plates and the eye sink
            ("blunt", (-0.036, -0.080, 0.012), dict(size=1.2, depth=0.95, name="GH_Hit_Crush_1")),
            ("blunt", (-0.030, -0.085, -0.002), dict(size=1.2, depth=0.95, name="GH_Hit_Crush_2")),
            ("blunt", (-0.042, -0.074, 0.020), dict(size=1.1, depth=0.9, name="GH_Hit_Crush_3")),
            ("blunt", (-0.014, -0.100, -0.018), dict(size=1.0, depth=0.9, name="GH_Hit_Crush_Nose")),
        ],
        # ~10 h after the beating: massively swollen, deep purple (§5.18 D);
        # the blood on the face is partly dried -- dark, tacky, clotted, with
        # the fresh flow from the nose and the torn vessels on top of it
        controls=dict(bleed=1.0, bruising=1.0, swelling=0.9, wound_age=0.45, blood_age=0.3),
    ),
}
PRESET_NAMES = tuple(PRESETS)

# control values every preset starts from (then its own overrides)
BASE_CONTROLS = dict(damage=1.0, bleed=0.7, drip_time=1.0, wetness=0.8, blood_age=0.0,
                     bruising=0.6, swelling=0.5, wound_age=0.2, skin_tone=0.25, pallor=0.0)


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
    "front":   ((0.0, -0.80, 0.0), (0.0, -0.02, -0.012), 85.0),
    "three_q": ((-0.53, -0.58, 0.09), (-0.005, -0.02, -0.006), 85.0),
    "side":    ((-0.80, -0.02, 0.0), (0.0, -0.02, -0.012), 85.0),
    "back":    ((0.42, 0.66, 0.16), (0.0, 0.01, 0.0), 85.0),
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


CLOSEUP_LIGHT = "GH_Closeup_Light"


def closeup_light(cam, target, energy=1.6, enable=True):
    """Soft 'flash' light above the close-up camera, so the inside of a wound on
    the unlit back of the head is visible. Disabled for the other renders."""
    data = bpy.data.lights.get(CLOSEUP_LIGHT) or bpy.data.lights.new(CLOSEUP_LIGHT, 'AREA')
    data.energy = energy
    data.size = 0.08
    data.color = (1.0, 0.97, 0.93)
    ob = bpy.data.objects.get(CLOSEUP_LIGHT) or bpy.data.objects.new(CLOSEUP_LIGHT, data)
    if ob.name not in bpy.context.scene.collection.all_objects:
        ghc.get_collection("Stage").objects.link(ob)
    cam_m = cam.matrix_world
    up = (cam_m.to_3x3() @ Vector((0.0, 1.0, 0.0))).normalized()
    ob.location = cam_m.translation + up * 0.03
    ghc.look_at(ob, target)
    ob.hide_render = not enable
    return ob


def remove_closeup_light():
    """Delete the close-up light (it is only used while rendering close-ups)."""
    ob = bpy.data.objects.get(CLOSEUP_LIGHT)
    if ob is not None:
        data = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
        bpy.data.lights.remove(data)


ANIM_ACTION = "GH_ControlsAnim"


def animate_controls(frames=ANIM_FRAMES):
    """Keyframe GH_Controls: damage 0 -> 1 over 1-12, drip_time 0 -> 1 over 12-120.

    Always writes into one action named GH_ControlsAnim (an old one is
    replaced), so the Dope Sheet shows a clean name."""
    scene = bpy.context.scene
    ctrl = ghc.ensure_controls()
    if ctrl.animation_data is not None:
        ctrl.animation_data_clear()
    old = bpy.data.actions.get(ANIM_ACTION)
    if old is not None:
        bpy.data.actions.remove(old)
    for act in [a for a in bpy.data.actions if a.name.startswith(ghc.CONTROLS_NAME) and a.users == 0]:
        bpy.data.actions.remove(act)
    ctrl.animation_data_create()
    ctrl.animation_data.action = bpy.data.actions.new(ANIM_ACTION)
    for prop, keys in (("damage", DAMAGE_KEYS), ("drip_time", DRIP_KEYS)):
        for frame, value in keys:
            ctrl[prop] = value
            ctrl.keyframe_insert(f'["{prop}"]', frame=frame)
    scene.frame_start, scene.frame_end = frames
    scene.render.fps = 24
    return ctrl


# ---------------------------------------------------------------------------
# Facial hair: eyebrows and eyelashes
# ---------------------------------------------------------------------------
# Hair curves grown on the skin from code. A small geometry-nodes modifier
# keeps them on the *wounded* skin: every strand is moved with the skin under
# its root (swelling, burn shrinkage) and strands whose root is burned or torn
# open are removed, so a burned brow is bald and a cut brow is split.
BROWS_NAME = "GH_Eyebrows"
LASHES_NAME = "GH_Eyelashes"
HAIR_MAT = "GH_Hair"
HAIR_GN = "GH_HairOnSkin"


def _brow_band(ax):
    """Eyebrow centre height and half height (m) at |x| = ax."""
    zc = np.interp(ax, [0.011, 0.020, 0.032, 0.045, 0.057], [0.0352, 0.0372, 0.0392, 0.0382, 0.0342])
    hh = np.interp(ax, [0.011, 0.020, 0.035, 0.050, 0.058], [0.0040, 0.0044, 0.0035, 0.0023, 0.0010])
    return zc, hh


def _brow_angle(ax, rel):
    """In-plane growth angle (rad, 0 = lateral, pi/2 = up) of a brow hair.

    Hairs at the head of the brow grow upward, along the body they lie
    lateral, the tail points down; upper and lower rows converge a little."""
    base = np.interp(ax, [0.011, 0.017, 0.024, 0.045, 0.058],
                     [1.35, 1.05, 0.30, 0.05, -0.35])
    return base - rel * 0.28


def _hair_bvh(skin):
    """BVH of the undeformed skin (object space = head space)."""
    from mathutils.bvhtree import BVHTree
    me = skin.data
    verts = [v.co.copy() for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons]
    return BVHTree.FromPolygons(verts, polys)


def _lay_on_skin(bvh, pts, lift):
    """Keep every point of a strand at least lift[i] above the skin surface."""
    out = [pts[0]]
    for p, h in zip(pts[1:], lift[1:]):
        q, n, _i, _d = bvh.find_nearest(p)
        if q is not None:
            n = n.normalized()
            hgt = (p - q).dot(n)
            if hgt < h:
                p = p + n * (h - hgt)
        out.append(p)
    return out


def _brow_strands(bvh, rng, sign, count=330):
    """Strands (lists of Vectors) of one eyebrow; sign = +1 left (+X), -1 right."""
    strands = []
    tries = 0
    while len(strands) < count and tries < count * 20:
        tries += 1
        ax = rng.uniform(0.011, 0.058)
        zc, hh = _brow_band(ax)
        rel = rng.uniform(-1.0, 1.0)
        # denser in the middle of the band, thin ragged edges
        if rng.random() > (1.0 - abs(rel) ** 3) * (0.35 + 0.65 * min(1.0, (0.058 - ax) / 0.012)):
            continue
        z = zc + rel * hh
        loc, nrm, _i, _d = bvh.ray_cast(Vector((sign * ax, -0.2, z)), Vector((0.0, 1.0, 0.0)), 0.3)
        if loc is None:
            continue
        n = nrm.normalized()
        ang = _brow_angle(ax, rel) + rng.normal(0.0, 0.14)
        d = Vector((sign * math.cos(ang), 0.0, math.sin(ang)))
        d = (d - n * d.dot(n)).normalized()
        length = np.interp(ax, [0.011, 0.02, 0.035, 0.058], [0.0055, 0.0075, 0.0085, 0.0055]) \
            * rng.uniform(0.75, 1.15)
        lift = 0.28 + rng.uniform(-0.08, 0.1)
        root = loc + n * 0.00005
        pts = []
        for i in range(5):
            s = i / 4.0
            # rises off the skin, then lies down along it
            pts.append(root + d * (s * length) + n * (length * lift * s * (1.0 - 0.75 * s)))
        strands.append(_lay_on_skin(bvh, pts, [0.0, 0.00012, 0.0002, 0.00025, 0.0003]))
    return strands


def _lash_strands(bvh, rng, sign, upper=True):
    """Eyelashes of one lid: rooted on the lid margin, curling away from the eye."""
    ec = Vector((sign * anatomy.EYE_C[0], anatomy.EYE_C[1], anatomy.EYE_C[2]))
    # ~90 upper / 50 lower lashes in two or three staggered rows, as on a real lid
    count = 80 if upper else 50
    strands = []
    for k in range(count):
        t = (k + rng.uniform(0.0, 0.9)) / count
        t = 0.05 + 0.92 * t
        u = anatomy.LID_UM + t * (anatomy.LID_UL - anatomy.LID_UM)
        _t, st, up, lo = anatomy._lid_curves(np.array([u]))
        # root just outside the lid margin (the rim of the lid opening)
        row = (k % 3) * 0.012
        v = float(up[0]) + 0.015 + row if upper else float(lo[0]) - 0.008 - row * 0.6

        def direction(vv):
            return Vector((sign * math.cos(vv) * math.sin(u), -math.cos(vv) * math.cos(u), math.sin(vv)))
        guess = ec + direction(v) * (anatomy.LID_R + 0.0003)
        q, n, _i, _d = bvh.find_nearest(guess)
        if q is None:
            continue
        # lashes leave the margin nearly straight forward (not along the lid)
        radial = direction(v * 0.35)
        ev = Vector((-sign * math.sin(v) * math.sin(u), math.sin(v) * math.cos(u), math.cos(v)))
        if not upper:
            ev = -ev
        stf = float(st[0])
        # longest at the middle and a little toward the outer corner
        if upper:
            length = (0.0026 + 0.0032 * stf ** 0.7) * (1.0 + 0.2 * (t - 0.5))
        else:
            length = 0.0011 + 0.0013 * stf
        length *= rng.uniform(0.75, 1.15)
        # they grow forward out of the lid margin (lower ones down and out) ...
        d = (radial + ev * (0.12 if upper else 0.45)).normalized()
        if not upper:
            d = (d + Vector((sign * 0.25, 0.0, 0.0))).normalized()
        wob = Vector((rng.normal(0, 0.06), rng.normal(0, 0.06), rng.normal(0, 0.06)))
        d = (d + wob).normalized()
        pts = []
        for i in range(5):
            s = i / 4.0
            # ... and curl up (upper lid) or down (lower lid) toward their tips
            pts.append(q + d * (s * length) + ev * (length * 0.6 * s * s))
        strands.append(pts)
    # real lashes clump: groups of 3-5 neighbours whose tips pull together
    i = 0
    while i < len(strands):
        n = int(rng.integers(3, 6))
        grp = strands[i:i + n]
        tip = sum((st_[-1] for st_ in grp), Vector()) / len(grp)
        for st_ in grp:
            for k in range(1, len(st_)):
                w = (k / (len(st_) - 1)) ** 2 * 0.55
                st_[k] = st_[k] + (tip - st_[-1]) * w
        i += n
    return strands


def _hair_material(name):
    """GH_Hair: eyebrows, dark brown Principled Hair BSDF with lighter tips."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:        # (5.x materials always have one)
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    hair = nt.nodes.new('ShaderNodeBsdfHairPrincipled')
    hair.parametrization = 'MELANIN'
    hair.inputs['Melanin Redness'].default_value = 0.3
    hair.inputs['Roughness'].default_value = 0.32
    hair.inputs['Radial Roughness'].default_value = 0.45
    info = nt.nodes.new('ShaderNodeHairInfo')
    rmp = nt.nodes.new('ShaderNodeMapRange')
    rmp.inputs['To Min'].default_value = 0.95      # melanin at the root
    rmp.inputs['To Max'].default_value = 0.84      # ... and at the tip
    nt.links.new(info.outputs['Intercept'], rmp.inputs['Value'])
    nt.links.new(rmp.outputs['Result'], hair.inputs['Melanin'])
    nt.links.new(hair.outputs[0], out.inputs['Surface'])
    mat.diffuse_color = (0.05, 0.035, 0.025, 1.0)
    return mat


def _lash_material(name):
    """GH_Hair_Lash: near-black, softly glossy lashes.

    A plain dark BSDF instead of the hair model: at head scale the hair
    model's highlights and transmission turn the sub-pixel lashes into a
    pale fringe, while real lashes read as a dark line along the lid."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:        # (5.x materials always have one)
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = (0.012, 0.008, 0.006, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.45
    bsdf.inputs['Specular IOR Level'].default_value = 0.3
    nt.links.new(bsdf.outputs[0], out.inputs['Surface'])
    mat.diffuse_color = (0.012, 0.008, 0.006, 1.0)
    return mat


def _hair_node_group():
    """GN group: snap strands onto the evaluated (wounded) skin, drop burned / torn ones."""
    t = gore.NodeTree(HAIR_GN, (("Geometry", 'NodeSocketGeometry'), ("Skin", 'NodeSocketObject'),
                                ("Burn Limit", 'NodeSocketFloat', 0.12), ("Wound Limit", 'NodeSocketFloat', 0.3)),
                      (("Geometry", 'NodeSocketGeometry'),), modifier=True,
                      description="Eyebrows and lashes follow the wounded skin")
    skin = t.out(t.node('GeometryNodeObjectInfo', {'Object': t.inp("Skin")}, transform_space='RELATIVE'),
                 'Geometry')
    # root position of every strand, evaluated per curve
    first = t.out(t.node('GeometryNodePointsOfCurve', {'Curve Index': t.index()}), 'Point Index')
    root_pt = t.out(t.node('GeometryNodeFieldAtIndex', {'Value': t.pos(), 'Index': first},
                           domain='POINT', data_type='FLOAT_VECTOR'))
    root = t.out(t.node('GeometryNodeFieldOnDomain', {'Value': root_pt}, domain='CURVE',
                        data_type='FLOAT_VECTOR'))

    def near(value, dtype):
        n = t.node('GeometryNodeSampleNearestSurface', {'Mesh': skin, 'Value': value, 'Sample Position': root},
                   data_type=dtype)
        return t.out(n, 'Value')
    burn = near(t.attr("gore_burn"), 'FLOAT')
    wound = near(t.attr("gore_wound"), 'FLOAT')
    surf = near(t.pos(), 'FLOAT_VECTOR')
    kill = t.bool('OR', burn.gt(t.inp("Burn Limit")), wound.gt(t.inp("Wound Limit")))
    g = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': t.inp("Geometry"), 'Selection': kill},
                     domain='CURVE'))
    offset = t.out(t.node('GeometryNodeFieldOnDomain', {'Value': surf - root}, domain='CURVE',
                          data_type='FLOAT_VECTOR'))
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Offset': offset}))
    t.result("Geometry", g)
    t.layout()
    return t.ng


def _hair_object(name, strands, mat, skin, node_group):
    """Hair-curves object from [(points, root radius, tip radius)] that follows `skin`."""
    old = bpy.data.objects.get(name)
    if old is not None:
        data = old.data
        bpy.data.objects.remove(old, do_unlink=True)
        bpy.data.hair_curves.remove(data)
    cv = bpy.data.hair_curves.new(name)
    cv.add_curves([len(pts) for pts, _r0, _r1 in strands])
    cv.position_data.foreach_set("vector", [c for pts, _r0, _r1 in strands for p in pts for c in p])
    radii = []
    for pts, r0, r1 in strands:
        n = len(pts)
        radii += [r0 + (r1 - r0) * (i / (n - 1)) for i in range(n)]
    cv.attributes.new("radius", 'FLOAT', 'POINT').data.foreach_set("value", radii)
    cv.materials.append(mat)
    ob = bpy.data.objects.new(name, cv)
    ghc.get_collection("GoreHead").objects.link(ob)
    mod = ob.modifiers.new(HAIR_GN, 'NODES')
    mod.node_group = node_group
    ident = {it.name: it.identifier for it in node_group.interface.items_tree
             if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
    mod[ident["Skin"]] = skin
    return ob


def build_facial_hair(objs, seed=7):
    """Eyebrows (GH_Eyebrows) and eyelashes (GH_Eyelashes) as hair curves on GH_Skin.

    Two objects, because Cycles renders one material per hair-curves object
    (brows: GH_Hair, lashes: GH_Hair_Lash).
    Returns {name: object}.
    """
    skin = objs["GH_Skin"]
    bvh = _hair_bvh(skin)
    rng = np.random.default_rng(seed)
    brows, lashes = [], []
    for sign in (1.0, -1.0):
        brows += [(s, 0.000055, 0.000018) for s in _brow_strands(bvh, rng, sign)]
        lashes += [(s, 0.00008, 0.00002) for s in _lash_strands(bvh, rng, sign, True)]
        lashes += [(s, 0.00005, 0.000012) for s in _lash_strands(bvh, rng, sign, False)]
    ng = _hair_node_group()
    return {
        BROWS_NAME: _hair_object(BROWS_NAME, brows, _hair_material(HAIR_MAT), skin, ng),
        LASHES_NAME: _hair_object(LASHES_NAME, lashes, _lash_material(HAIR_MAT + "_Lash"), skin, ng),
    }


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
    # the snapped head vessel table, machine-readable for the Godot game
    gore.export_vessel_table(os.path.join(ghc.HERE, "vessels_head.json"))
    timings["gore"] = time.time() - t
    t = time.time()
    build_facial_hair(objs)
    timings["hair"] = time.time() - t
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


def _signature(ob):
    """(vertex count, face count, coordinate checksum, gore attribute maxima) of the evaluated mesh."""
    import numpy as np
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3, np.float64)
    me.vertices.foreach_get("co", co)
    peaks = {}
    for name in gore.ATTRS:
        att = me.attributes.get(name)
        if att is not None and att.domain == 'POINT' and len(att.data):
            vals = np.empty(len(att.data), np.float32)
            att.data.foreach_get("value", vals)
            peaks[name] = float(vals.max())
    sig = (len(me.vertices), len(me.polygons), round(float((co * np.resize([1.7, 3.1, 5.3], co.size)).sum()), 5),
           peaks)
    ev.to_mesh_clear()
    return sig


def verify(objs):
    """Integration checks on the real anatomy. Prints a report, returns True if all pass.

    * every damageable layer ends with the GH_Gore modifier
    * every preset evaluates, writes all gore_* attributes and opens wounds
    * damage = 0 (and frame 1 of the animation) is identical to the intact head
    """
    lines, ok = [], True
    evals = {}

    def check(name, cond, info=""):
        nonlocal ok
        ok &= bool(cond)
        lines.append(f"  [{'PASS' if cond else 'FAIL'}] {name}{': ' + info if info else ''}")

    layers = {n: objs[n] for n in gore.LAYERS if n in objs}
    last = [n for n, ob in layers.items() if not ob.modifiers or ob.modifiers[-1].name != gore.MOD_NAME]
    check("GH_Gore is the last modifier on every layer", not last, ", ".join(last))
    apply_preset("intact")
    intact = {n: _signature(ob) for n, ob in layers.items()}
    for name in PRESET_NAMES[1:]:
        apply_preset(name)
        secs = evals[name] = evaluate_all(objs)
        sigs = {n: _signature(ob) for n, ob in layers.items()}
        missing = [n for n, sg in sigs.items() if len(sg[3]) != len(gore.ATTRS)]
        skin = sigs["GH_Skin"][3]
        opened = skin.get("gore_wound", 0.0) > 0.5
        check(f"preset '{name}'", not missing and opened,
              f"{secs:.2f} s, skin {sigs['GH_Skin'][0]} verts, peaks "
              + " ".join(f"{k[5:]}={v:.2f}" for k, v in skin.items()))
    brows = bpy.data.objects.get(BROWS_NAME)
    if brows is not None:
        def n_strands():
            ev = brows.evaluated_get(bpy.context.evaluated_depsgraph_get())
            return len(ev.data.curves)
        apply_preset("intact")
        n0 = n_strands()
        apply_preset("burn")
        n1 = n_strands()
        check("eyebrows follow the skin: burned brow hairs are gone", 0 < n1 < n0 * 0.8,
              f"{n0} -> {n1} strands")
    for name in ("gunshot", "carnage"):
        apply_preset(name)
        ghc.ensure_controls()["damage"] = 0.0
        ghc.ensure_controls().update_tag()
        evaluate_all(objs)
        diff = [n for n, ob in layers.items() if _signature(ob)[:3] != intact[n][:3]]
        check(f"damage = 0 with the '{name}' hits is the intact head", not diff, ", ".join(diff))
    apply_preset("gunshot")
    animate_controls()
    scene = bpy.context.scene
    scene.frame_set(ANIM_FRAMES[0])
    diff = [n for n, ob in layers.items() if _signature(ob)[:3] != intact[n][:3]]
    check("animation frame 1 (damage 0) is intact", not diff, ", ".join(diff))
    scene.frame_set(60)
    ctrl = ghc.ensure_controls()
    check("animation frame 60 is wounded and bleeding",
          ctrl["damage"] > 0.99 and 0.2 < ctrl["drip_time"] < 0.8
          and _signature(layers["GH_Skin"])[0] > intact["GH_Skin"][0],
          f"damage {ctrl['damage']:.2f}, drip_time {ctrl['drip_time']:.2f}")
    # the gore module's own self-test (moving / rotating / scaling a hit,
    # bleed 0, drip_time) on the real anatomy
    apply_preset("intact")
    gore_ok = gore.verify_gore(objs)
    check("gore.verify_gore() self-test", gore_ok)
    lines.append("RESULT: " + ("all checks passed" if ok else "SOME CHECKS FAILED"))
    print("[build] verification\n" + "\n".join(lines))
    verify.evals = evals
    return ok


# ---------------------------------------------------------------------------
# Cutaway
# ---------------------------------------------------------------------------
CUT_LAYERS = {"GH_Skin_cut": 0, "GH_Muscle": 1, "GH_Skull": 2, "GH_Jaw": 2, "GH_Eye_L": 2,
              "GH_Gums": 2, "GH_Brain": 3, "GH_Teeth_Upper": 3, "GH_Teeth_Lower": 3, "GH_Tongue": 3,
              "GH_Cervical": 2}


class _SN:
    """Tiny shader-node helper for the cutaway materials (constants or sockets)."""

    def __init__(self, mat):
        if mat.node_tree is None:
            mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.N, self.L = self.nt.nodes, self.nt.links
        self.out = self.N.new('ShaderNodeOutputMaterial')
        self.bsdf = self.N.new('ShaderNodeBsdfPrincipled')
        self.L.new(self.bsdf.outputs[0], self.out.inputs['Surface'])
        tc = self.N.new('ShaderNodeTexCoord')
        self.p = tc.outputs['Object']

    def _in(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.L.new(v, sock)
        elif isinstance(v, (tuple, list)):
            sock.default_value = (*v, 1.0) if sock.type == 'RGBA' and len(v) == 3 else v
        else:
            sock.default_value = v

    def math(self, op, a, b=None, c=None):
        m = self.N.new('ShaderNodeMath')
        m.operation = op
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self._in(m.inputs[i], v)
        return m.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        m = self.N.new('ShaderNodeVectorMath')
        m.operation = op
        for i, v in enumerate((a, b)):
            if v is not None:
                self._in(m.inputs[i], v)
        if scale is not None:
            self._in(m.inputs['Scale'], scale)
        return m.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else m.outputs['Vector']

    def sep(self, v):
        n = self.N.new('ShaderNodeSeparateXYZ')
        self.L.new(v, n.inputs[0])
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def vec(self, x, y, z):
        n = self.N.new('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            self._in(n.inputs[i], v)
        return n.outputs[0]

    def smooth(self, x, e0, e1):
        m = self.N.new('ShaderNodeMapRange')
        m.interpolation_type = 'SMOOTHSTEP'
        self._in(m.inputs['Value'], x)
        self._in(m.inputs['From Min'], e0)
        self._in(m.inputs['From Max'], e1)
        return m.outputs['Result']

    def noise(self, v, scale, detail=2.0, rough=0.5):
        n = self.N.new('ShaderNodeTexNoise')
        self.L.new(v, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        return n.outputs['Fac']

    def noise_col(self, v, scale, detail=2.0):
        n = self.N.new('ShaderNodeTexNoise')
        self.L.new(v, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        return n.outputs['Color']

    def voronoi(self, v, scale, feature='F1'):
        n = self.N.new('ShaderNodeTexVoronoi')
        n.feature = feature
        self.L.new(v, n.inputs['Vector'])
        n.inputs['Scale'].default_value = scale
        return n.outputs['Distance'], n.outputs['Color']

    def mix(self, f, a, b):
        m = self.N.new('ShaderNodeMix')
        m.data_type = 'RGBA'
        self._in(m.inputs['Factor'], f)
        self._in(m.inputs[6], a)
        self._in(m.inputs[7], b)
        return m.outputs[2]

    def fmix(self, f, a, b):
        m = self.N.new('ShaderNodeMix')
        m.data_type = 'FLOAT'
        self._in(m.inputs['Factor'], f)
        self._in(m.inputs[2], a)
        self._in(m.inputs[3], b)
        return m.outputs[0]

    def set(self, name, v):
        self._in(self.bsdf.inputs[name], v)


def _eye_section_material():
    """GH_EyeSection: the cut face of the eyeball, a real globe section.

    Eye object space (origin at the centre, -Y = gaze, R 12 mm): the white
    sclera wall (~1 mm) with the dark brown choroid and the thin pink-red
    retina lining its back two thirds, the clear cornea in front, the aqueous
    front chamber, the pigmented iris band with the pupil gap, the ciliary body
    at the limbus, the biconvex amber lens behind the iris, clear vitreous gel
    filling the rest and the optic nerve leaving at the back.
    """
    mat = bpy.data.materials.get("GH_EyeSection") or bpy.data.materials.new("GH_EyeSection")
    t = _SN(mat)
    x, y, z = t.sep(t.p)
    r = t.vmath('LENGTH', t.p)
    rp = t.vmath('LENGTH', t.vec(x, 0.0, z))                        # distance from the visual axis
    R = materials.EYE_R
    back = t.smooth(y, -0.0085, -0.0070)                            # behind the limbus
    # cornea: the front sphere (centre 0, -CORNEA_OFF, 0; r 7.5 mm), ~0.6 mm thick
    rc = t.vmath('DISTANCE', t.p, (0.0, -materials.CORNEA_OFF, 0.0))
    front = t.math('SUBTRACT', 1.0, back)
    cornea = t.math('MULTIPLY', t.smooth(rc, materials.CORNEA_R - 0.0007, materials.CORNEA_R - 0.0005), front)
    sclera = t.math('MULTIPLY', t.smooth(r, R - 0.0011, R - 0.0009), back)
    choroid = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(r, R - 0.0015, R - 0.0013),
                                        t.math('SUBTRACT', 1.0, sclera)), t.smooth(y, -0.0075, -0.0055))
    retina = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(r, R - 0.0019, R - 0.0017),
                                       t.math('SUBTRACT', 1.0, t.smooth(r, R - 0.0015, R - 0.0013))),
                    t.smooth(y, -0.006, -0.004))
    # iris: a thin pigmented band in the iris plane, from the pupil to the limbus
    iris_y = materials.IRIS_PLANE_Y
    iris = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(t.math('ABSOLUTE', t.math('SUBTRACT', y, iris_y)),
                                                          0.00045, 0.0003),
                                     t.smooth(rp, materials.PUPIL_R, materials.PUPIL_R + 0.0003)),
                  t.smooth(rp, materials.LIMBUS_R + 0.0004, materials.LIMBUS_R))
    ciliary = t.math('MULTIPLY', t.smooth(t.vmath('DISTANCE', t.vec(rp, y, 0.0), (0.0060, -0.0085, 0.0)), 0.0013, 0.0009),
                     1.0)
    # lens: biconvex, centre 3.5 mm behind the iris, 9 mm across, 4 mm thick
    lq = t.vmath('LENGTH', t.vmath('DIVIDE', t.vec(rp, t.math('ADD', y, 0.0078), 0.0), (0.0046, 0.0020, 1.0)))
    lens = t.smooth(lq, 1.0, 0.94)
    ant = t.math('MULTIPLY', t.smooth(y, iris_y + 0.0001, iris_y - 0.0002), front)     # aqueous chamber
    nerve = t.math('MULTIPLY', t.smooth(rp, 0.0017, 0.0013), t.smooth(y, R - 0.0025, R - 0.0012))
    n1 = t.noise(t.p, 900.0, 3.0)
    col = t.mix(n1, (0.20, 0.205, 0.20), (0.26, 0.26, 0.25))        # clear vitreous gel (dark behind)
    col = t.mix(ant, col, (0.05, 0.055, 0.06))
    col = t.mix(lens, col, t.mix(t.smooth(lq, 0.2, 0.9), (0.62, 0.52, 0.30), (0.48, 0.40, 0.22)))
    col = t.mix(retina, col, t.mix(n1, (0.40, 0.12, 0.10), (0.52, 0.20, 0.15)))
    col = t.mix(choroid, col, (0.035, 0.014, 0.010))
    col = t.mix(ciliary, col, (0.05, 0.02, 0.014))
    col = t.mix(iris, col, t.mix(n1, (0.05, 0.035, 0.02), (0.12, 0.08, 0.045)))
    col = t.mix(sclera, col, t.mix(n1, (0.66, 0.63, 0.57), (0.74, 0.71, 0.65)))
    col = t.mix(cornea, col, (0.50, 0.52, 0.54))
    col = t.mix(nerve, col, (0.66, 0.60, 0.50))
    t.set('Base Color', col)
    wall = t.math('MAXIMUM', t.math('MAXIMUM', sclera, choroid), t.math('MAXIMUM', iris, nerve))
    t.set('Roughness', t.fmix(wall, 0.06, 0.35))
    t.set('Coat Weight', 0.6)
    t.set('Coat Roughness', 0.04)
    t.set('Subsurface Weight', t.fmix(t.math('MAXIMUM', lens, ant), 0.15, 0.4))
    t.bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.8, 0.6)
    t.bsdf.inputs['Subsurface Scale'].default_value = 0.001
    mat.diffuse_color = (0.3, 0.3, 0.3, 1.0)
    return mat


def _sulcus_distance(t, pa):
    """Shader version of anatomy.gyri_field: distance (m) to the sulcus sheets.

    The same monochromatic random wave fields (directions, phases,
    wavelengths and domain warp) whose nodal lines fold the brain surface;
    in 3D their nodal sets are sheets running from the surface into the
    depth -- exactly where the sulci cut into a section of the brain. The
    gradient is replaced by its RMS value k sqrt(N / 2)."""
    kw = 2.0 * math.pi / 0.060
    w = None
    for i, (d, ph) in enumerate(zip(anatomy._WARP_K, anatomy._WARP_PH)):
        s = t.math('SINE', t.math('ADD', t.math('MULTIPLY', t.vmath('DOT_PRODUCT', pa, tuple(float(c) for c in d)), kw),
                                  float(ph)))
        a = anatomy._WARP_K[(i + 2) % len(anatomy._WARP_K)]
        term = t.vmath('SCALE', tuple(float(c) for c in a), scale=s)
        w = term if w is None else t.vmath('ADD', w, term)
    pw = t.vmath('ADD', pa, t.vmath('SCALE', w, scale=0.0035))

    def field(dirs, phases, wl):
        k = 2.0 * math.pi / wl
        acc = None
        for d, ph in zip(dirs, phases):
            c = t.math('COSINE', t.math('ADD', t.math('MULTIPLY', t.vmath('DOT_PRODUCT', pw, tuple(float(v) for v in d)), k),
                                        float(ph)))
            acc = c if acc is None else t.math('ADD', acc, c)
        return t.math('DIVIDE', t.math('ABSOLUTE', acc), k * math.sqrt(len(dirs) / 2.0))
    s1 = field(anatomy._GYRI_K, anatomy._GYRI_PH, 0.0175)
    s2 = field(anatomy._GYRI_K2, anatomy._GYRI_PH2, 0.0300)
    return t.math('MINIMUM', s1, t.math('ADD', s2, 0.0008))


def _matter_material(white):
    """Cut brain tissue: grey cortex (outer rim) or white matter (the core's cap).

    The white-matter cap shows the cortex folding into it: the sulci are the
    nodal sheets of anatomy's own gyri field (_sulcus_distance), so every
    sulcus on the brain surface continues into the section as a dark,
    blood-lined cleft, lined on both sides by a ~2.5 mm ribbon of grey
    cortex that wraps round its floor; they reach 10-20 mm deep from the
    surface and the deep white matter (centrum semiovale) stays cream. A grey
    island (basal ganglia), a dark CSF slit (ventricle) and the cerebellum's
    folia with their white core (arbor vitae) complete the section.
    """
    name = "GH_WhiteMatterCut" if white else "GH_GreyMatterCut"
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    t = _SN(mat)
    x, y, z = t.sep(t.p)
    pa = t.vec(t.math('ABSOLUTE', x), y, z)
    sd = _sulcus_distance(t, pa)
    # depth into the cerebrum: normalised ellipsoid radius (1 at the cortex)
    ln = t.vmath('LENGTH', t.vmath('DIVIDE', t.vmath('SUBTRACT', pa, (0.0, 0.005, 0.043)), (0.066, 0.086, 0.066)))
    # (sulci run in from the surface and end blindly 8-15 mm deep; deeper
    # the nodal sheets of the wave field close into cells, which read as a
    # crackle web, so they are faded out there)
    reach = t.smooth(ln, t.math('ADD', 0.66, t.math('MULTIPLY', t.noise(t.p, 45.0, 2.0), 0.06)), 0.86)
    reach = t.math('MULTIPLY', reach, t.smooth(t.noise(t.p, 60.0, 2.0), 0.2, 0.4))
    n1 = t.noise(t.p, 900.0, 3.0)
    # (grey matter is clearly darker than the cream white matter: pinkish
    # grey-brown, the contrast that makes the folding readable)
    grey = t.mix(n1, (0.17, 0.10, 0.09), (0.24, 0.15, 0.13))
    # white matter: cream with a faint pink-grey blush and a fibrous grain
    # (a flat uniform cream reads as a plaster disc)
    fib = t.noise(t.vmath('MULTIPLY', t.p, (1.0, 0.35, 1.0)), 420.0, 3.0)
    blush = t.smooth(t.noise(t.p, 70.0, 3.0), 0.45, 0.75)
    whitec = t.mix(n1, (0.50, 0.44, 0.36), (0.60, 0.54, 0.45))
    whitec = t.mix(t.math('MULTIPLY', blush, 0.55), whitec, (0.52, 0.38, 0.33))
    whitec = t.mix(t.math('MULTIPLY', t.smooth(fib, 0.45, 0.7), 0.35), whitec, (0.44, 0.39, 0.32))
    # cerebellum (behind the tentorium, below the cerebrum)
    cb = t.math('MULTIPLY', t.smooth(y, 0.018, 0.032), t.smooth(z, 0.012, 0.0))
    if white:
        ribbon = t.math('MULTIPLY', t.smooth(sd, 0.0030, 0.0022), reach)
        sulc = t.math('MULTIPLY', t.smooth(sd, 0.00055, 0.0002), reach)
        col = t.mix(ribbon, whitec, grey)
        # basal ganglia: a grey island deep in the white matter; a dark CSF slit
        # (a soft-edged, irregular island, warped by noise: a clean ellipse
        # reads as a sticker)
        pw = t.vmath('ADD', pa, t.vmath('SCALE', t.vmath('SUBTRACT', t.noise_col(t.p, 70.0), (0.5, 0.5, 0.5)),
                                        scale=0.006))
        bg = t.smooth(t.vmath('LENGTH', t.vmath('DIVIDE', t.vmath('SUBTRACT', pw, (0.0, -0.002, 0.030)),
                                                (1.0, 0.013, 0.008))), 1.05, 0.7)
        col = t.mix(t.math('MULTIPLY', bg, 0.7), col, t.mix(n1, (0.24, 0.15, 0.13), (0.30, 0.20, 0.17)))
        # lateral ventricle: a C-shaped CSF slit (body above, atrium behind,
        # temporal horn curving down and forward), 1-3 mm, dark with a
        # blood-tinged lining, lateral to the septum (|x| > 5 mm)
        vr = t.vmath('LENGTH', t.vec(0.0, t.math('SUBTRACT', y, 0.0), t.math('SUBTRACT', z, 0.019)))
        arc = t.math('ABSOLUTE', t.math('SUBTRACT', vr, t.math('ADD', 0.027, t.math('MULTIPLY', t.noise(t.p, 90.0), 0.002))))
        # (open toward the front-bottom: no slit below-in-front of the arc centre)
        ang_ok = t.math('MAXIMUM', t.smooth(y, -0.004, 0.006), t.smooth(z, 0.012, 0.022))
        vhw = t.math('ADD', 0.0007, t.math('MULTIPLY', t.smooth(y, 0.005, 0.03), 0.0011))
        vent = t.math('MULTIPLY', t.math('MULTIPLY', t.smooth(arc, vhw, t.math('MULTIPLY', vhw, 0.5)), ang_ok),
                      t.math('MULTIPLY', t.smooth(pa_x := t.sep(pa)[0], 0.004, 0.007), t.smooth(pa_x, 0.036, 0.03)))
        vent = t.math('MULTIPLY', vent, t.smooth(y, -0.034, -0.028))
        col = t.mix(t.math('MULTIPLY', t.smooth(arc, t.math('MULTIPLY', vhw, 2.2), vhw), t.math('MULTIPLY', ang_ok, 0.5)),
                    col, (0.30, 0.16, 0.14))
        col = t.mix(vent, col, t.mix(n1, (0.03, 0.012, 0.012), (0.09, 0.02, 0.02)))
        # cerebellum: folia in thin grey leaves around a branching white core
        cr = t.vmath('LENGTH', t.vmath('MULTIPLY', t.vmath('SUBTRACT', pa, (0.0, 0.030, 0.004)), (1.0, 0.9, 1.2)))
        fol = t.math('COSINE', t.math('MULTIPLY', t.math('ADD', cr, t.math('MULTIPLY', t.noise(t.p, 120.0), 0.001)),
                                      2.0 * math.pi / 0.0030))
        arbor = t.math('MAXIMUM', t.smooth(fol, -0.55, -0.9), t.smooth(cr, 0.016, 0.011))
        cbcol = t.mix(arbor, grey, whitec)
        col = t.mix(cb, col, cbcol)
    else:
        sulc = t.smooth(sd, 0.00055, 0.0002)
        col = grey
    # the sulcal clefts hold blood and pia: dark red, clotted in places
    clot = t.smooth(t.noise(t.p, 180.0, 2.0), 0.55, 0.7)
    col = t.mix(t.math('MULTIPLY', sulc, 0.95), col, t.mix(clot, (0.16, 0.02, 0.018), (0.05, 0.006, 0.006)))
    # small vessels cut across (dark red dots) and a thin blood film
    vd, _vc = t.voronoi(t.p, 700.0)
    dots = t.math('MULTIPLY', t.smooth(vd, 0.08, 0.03), t.smooth(t.noise(t.p, 200.0), 0.52, 0.64))
    col = t.mix(dots, col, (0.18, 0.02, 0.02))
    t.set('Base Color', col)
    t.set('Roughness', t.fmix(sulc, 0.32, 0.12))
    t.set('Coat Weight', 0.35)
    t.set('Coat Roughness', 0.08)
    t.set('Subsurface Weight', 0.35)
    t.bsdf.inputs['Subsurface Radius'].default_value = (1.0, 0.5, 0.4)
    t.bsdf.inputs['Subsurface Scale'].default_value = 0.0015
    mat.diffuse_color = (0.6, 0.5, 0.45, 1.0)
    return mat


def _diploe_material():
    """GH_DiploeCut: cancellous bone between the two tables of the skull (and in
    the mandible): pale trabeculae around dark red marrow spaces, matte."""
    mat = bpy.data.materials.get("GH_DiploeCut") or bpy.data.materials.new("GH_DiploeCut")
    t = _SN(mat)
    d1, c1 = t.voronoi(t.p, 1500.0)
    d2, _c2 = t.voronoi(t.p, 520.0)
    holes = t.math('MAXIMUM', t.smooth(d1, 0.5, 0.28), t.math('MULTIPLY', t.smooth(d2, 0.4, 0.18), 0.85))
    n1 = t.noise(t.p, 300.0, 3.0)
    # (red-brown spongy bone, clearly different from the dense ivory tables)
    trab = t.mix(n1, (0.40, 0.27, 0.19), (0.52, 0.38, 0.27))
    marrow = t.mix(t.noise(t.p, 800.0), (0.08, 0.012, 0.01), (0.22, 0.045, 0.03))
    col = t.mix(holes, trab, marrow)
    t.set('Base Color', col)
    t.set('Roughness', t.fmix(holes, 0.7, 0.35))
    mat.diffuse_color = (0.5, 0.35, 0.25, 1.0)
    return mat


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
    # the eyebrows and lashes cannot be cut; the cut side's would float
    hidden = [skin, cav] + [ob for ob in map(bpy.data.objects.get, (BROWS_NAME, LASHES_NAME)) if ob is not None]
    for ob in hidden:
        ob.hide_render = True
    obs = dict(objs, GH_Skin_cut=joined)
    # white matter under a 2.5-3 mm grey cortex: an inner copy of the brain
    # (the brain field moved 2.8 mm inward, so it follows the gyri as cores),
    # cut a hair further out so its cap covers the grey cap except for the
    # cortex ribbon; both caps take their colour from the cutter
    brain = objs.get("GH_Brain")
    white = None
    if brain is not None:
        white = anatomy.mesh_sdf("GH_WhiteMatter", lambda x, y, z: anatomy.brain_sdf(x, y, z) + 0.0028,
                                 *anatomy.BRAIN_BOX, 0.0012, voxel=0.0012, project=1,
                                 collection=ghc.get_collection("GoreHead"))
        white.data.shade_smooth()
        white.data.materials.append(brain.data.materials[0] if brain.data.materials else None)
        obs["GH_WhiteMatter"] = white
    # the spongy diploe between the two tables of the vault (and the cancellous
    # core of the mandible): the bone field moved ~1.4 mm inward from both of
    # its surfaces; its cap covers the bone's cap except for the dense ivory
    # cortex along both edges (thin face bones stay all cortex)
    cores = {}
    for base, fn, box, inset in (("GH_Skull", anatomy.skull_sdf, anatomy.SKULL_BOX, 0.0014),
                                 ("GH_Jaw", anatomy.jaw_sdf, anatomy.JAW_BOX, 0.0016)):
        if objs.get(base) is None:
            continue
        name = base + "_Diploe"
        core = anatomy.mesh_sdf(name, lambda x, y, z, fn=fn, inset=inset: fn(x, y, z) + inset,
                                *box, 0.001, voxel=0.001, project=1, collection=ghc.get_collection("GoreHead"))
        core.data.shade_smooth()
        core.data.materials.append(_diploe_material())
        obs[name] = core
        cores[name] = core
    added = []
    layers = dict(CUT_LAYERS)
    if white is not None:
        layers["GH_WhiteMatter"] = 3.4
    for name in cores:
        layers[name] = 2.4
    for name, lvl in layers.items():
        if obs.get(name) is None:
            continue
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
        if name.startswith("GH_Eye"):
            # the cut eye is a real globe section: sclera, choroid, retina,
            # cornea, iris, lens, vitreous (not a grey disc)
            cm.materials.append(_eye_section_material())
            mod.material_mode = 'TRANSFER'
        elif name in ("GH_Brain", "GH_WhiteMatter"):
            cm.materials.append(_matter_material(name == "GH_WhiteMatter"))
            mod.material_mode = 'TRANSFER'
        added.append((obs[name], mod, cutter))

    def cleanup():
        for ob, mod, cutter in added:
            ob.modifiers.remove(mod)
            bpy.data.objects.remove(cutter, do_unlink=True)
        bpy.data.objects.remove(joined, do_unlink=True)
        bpy.data.meshes.remove(me)
        for ob_ in [white] + list(cores.values()):
            if ob_ is not None:
                me_ = ob_.data
                bpy.data.objects.remove(ob_, do_unlink=True)
                bpy.data.meshes.remove(me_)
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


# views rendered for every preset, plus extra views where the main damage
# faces away from the front cameras
PRESET_VIEWS = ("front", "three_q")
EXTRA_VIEWS = {"gunshot": ("back",)}


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
        for view in PRESET_VIEWS + EXTRA_VIEWS.get(name, ()):
            key = f"preset_{name}_{view}"
            times[key] = _render(os.path.join(out_dir, key + ".png"), cams[view], samples, res)
    if want("closeup_exit"):
        apply_preset("gunshot")
        hit = bpy.data.objects["GH_Hit_Exit"]
        cam = closeup_camera(hit)
        closeup_light(cam, hit.matrix_world.translation)
        times["closeup_exit"] = _render(os.path.join(out_dir, "closeup_exit.png"), cam, samples, res)
        remove_closeup_light()
    if want("sequence"):
        times.update(render_blood_sequence(out_dir, samples, min(res, 480)))
    if want("contact_sheet"):
        times.update(render_contact_sheet(out_dir, samples, res))
    if want("hero"):
        times["hero"] = render_hero(out_dir)
    if want("stages"):
        times.update(render_stages(out_dir, times, samples))
    if want("cutaway"):
        apply_preset("intact")
        cleanup = add_cutaway(objs)
        cam = ghc.add_camera("GH_Cam_cutaway", (0.58, -0.40, 0.07), (0.0, -0.02, -0.01), 85.0)
        times["cutaway"] = _render(os.path.join(out_dir, "cutaway.png"), cam, samples, res)
        cleanup()
    bpy.context.scene.camera = cams["front"]
    return times


HERO_PRESET = "carnage"
HERO_RES = 1024
HERO_SAMPLES = 96


def render_hero(out_dir, preset=HERO_PRESET, res=HERO_RES, samples=HERO_SAMPLES):
    """The showcase image: three-quarter view of `preset` at high quality (renders/hero.png)."""
    cams = setup_cameras()
    apply_preset(preset)
    return _render(os.path.join(out_dir, "hero.png"), cams["three_q"], samples, res)


STAGES = ("intact", "blunt", "gunshot", "carnage")


def _load_rgba(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    bpy.data.images.remove(img)
    return px


def render_stages(out_dir, done=None, samples=40, cell=512, gutter=6):
    """One strip of 4 three-quarter panels: intact -> blunt -> gunshot -> carnage
    (renders/stages.png). Reuses preset_<name>_three_q.png when this run already
    rendered it, otherwise renders the panel into a temporary file."""
    done = done or {}
    cams = setup_cameras()
    panels, times = [], {}
    tmp = os.path.join(out_dir, ".stages_tmp")
    for name in STAGES:
        path = os.path.join(out_dir, f"preset_{name}_three_q.png")
        if f"preset_{name}_three_q" not in done:
            apply_preset(name)
            path = os.path.join(tmp, f"{name}.png")
            times[f"stages_{name}"] = _render(path, cams["three_q"], samples, cell)
        px = _load_rgba(path)
        if px.shape[0] != cell:
            # nearest-neighbour resample to the panel size (numpy only)
            idx = (np.arange(cell) * px.shape[0] / cell).astype(int)
            px = px[idx][:, idx]
        panels.append(px)
        if path.startswith(tmp):
            os.remove(path)
    try:
        os.rmdir(tmp)
    except OSError:
        pass
    sep = np.zeros((cell, gutter, 4), dtype=np.float32)
    sep[..., 3] = 1.0
    row = [panels[0]]
    for px in panels[1:]:
        row += [sep, px]
    strip = np.concatenate(row, axis=1)
    h, w = strip.shape[:2]
    dst = os.path.join(out_dir, "stages.png")
    out = bpy.data.images.new("stages", w, h, alpha=True)
    out.pixels[:] = strip.ravel()
    out.filepath_raw = dst
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    print(f"[build] composed {dst} ({w}x{h})")
    return times


# blood-source time sequence: seconds after the shot (drip_time = s / 60)
SEQ_SECONDS = (0, 5, 10, 20, 40, 60)


def _hit_camera(name, hit, dist, side=0.55, up=0.25, lens=85.0, drop=0.015):
    """Camera looking at a hit from outside, turned `side` toward its local X and
    tilted up, aimed `drop` metres below the hit (where the blood runs)."""
    m = hit.matrix_world.to_3x3().normalized()
    z = (m @ Vector((0.0, 0.0, 1.0))).normalized()
    x = (m @ Vector((1.0, 0.0, 0.0))).normalized()
    view = (z + x * side + Vector((0.0, 0.0, up))).normalized()
    target = hit.matrix_world.translation + Vector((0.0, 0.0, -drop))
    return ghc.add_camera(name, target + view * dist, target, lens)


def render_blood_sequence(out_dir, samples=40, res=480):
    """Entry and exit of the gunshot preset at 0/5/10/20/40/60 s: the blood must
    visibly start in the wound and travel from it (CLAUDE.md §8 blood rule)."""
    times = {}
    apply_preset("gunshot")
    ctrl = ghc.ensure_controls()
    for tag, hit_name in (("entry", "GH_Hit_Entry"), ("exit", "GH_Hit_Exit")):
        hit = bpy.data.objects[hit_name]
        cam = _hit_camera(f"GH_Cam_seq_{tag}", hit, 0.19 if tag == "entry" else 0.22)
        for sec in SEQ_SECONDS:
            ctrl["drip_time"] = sec / 60.0
            ctrl.update_tag()
            key = f"seq_{tag}_{sec:02d}s"
            times[key] = _render(os.path.join(out_dir, key + ".png"), cam, samples, res)
    ctrl["drip_time"] = 1.0
    ctrl.update_tag()
    return times


# close-ups for the reviewers' side-by-side comparison with the reference
# photos (refs/ is never committed; the sheet only holds our renders)
SHEET = (("gunshot", "GH_Hit_Entry", 0.09, "entry"), ("gunshot", "GH_Hit_Exit", 0.11, "exit"),
         ("slash", "GH_Hit_Slash_Cheek", 0.12, "cheek slash"), ("blunt", "GH_Hit_Blunt_Cranium", 0.12, "scalp split"),
         ("blast", "GH_Hit_Blast_Mouth", 0.26, "blast"), ("crushed", "GH_Hit_Crush_1", 0.22, "crushed"))


def render_contact_sheet(out_dir, samples=40, res=640):
    """One image with close-ups of every major wound type (3 x 2 panels)."""
    import numpy as np
    times = {}
    cell = res // 3
    panels = []
    tmp = os.path.join(out_dir, ".sheet_tmp")
    for preset, hit_name, dist, _label in SHEET:
        apply_preset(preset)
        hit = bpy.data.objects[hit_name]
        cam = _hit_camera(f"GH_Cam_sheet_{hit_name}", hit, dist, side=0.35, up=0.2, drop=0.004)
        p = os.path.join(tmp, f"{hit_name}.png")
        t = time.time()
        bpy.context.scene.view_settings.exposure = materials.STAGE_EXPOSURE
        ghc.render(p, cam, samples, (cell, cell))
        times[f"sheet_{hit_name}"] = time.time() - t
        img = bpy.data.images.load(p)
        panels.append(np.array(img.pixels[:], dtype=np.float32).reshape(cell, cell, 4))
        bpy.data.images.remove(img)
        os.remove(p)
    try:
        os.rmdir(tmp)
    except OSError:
        pass
    rows = [np.concatenate(panels[i:i + 3], axis=1) for i in (0, 3)]
    # (image rows run bottom-up in Blender: the first row goes on top)
    sheet = np.concatenate(rows[::-1], axis=0)
    out = bpy.data.images.new("contact_sheet", cell * 3, cell * 2, alpha=True)
    out.pixels[:] = sheet.ravel()
    out.filepath_raw = os.path.join(out_dir, "contact_sheet_wounds.png")
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    return times


def _has_gpu():
    """True when Cycles has a GPU compute device here (else the saved file uses the CPU)."""
    try:
        addon = bpy.context.preferences.addons.get("cycles")
        if addon is None:
            return False
        prefs = addon.preferences
        prefs.refresh_devices()
        return any(d.type != 'CPU' for d in prefs.devices)
    except Exception:     # noqa: BLE001  (no device API in this build: stay on the CPU)
        return False


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
    # compact, reasonably fast defaults for whoever opens the file; GPU when
    # the user's Blender has a compute device set up (Cycles falls back to CPU)
    ghc.configure_render(40, (1080, 1080))
    scene.cycles.device = 'GPU' if _has_gpu() else 'CPU'
    scene.view_settings.exposure = materials.STAGE_EXPOSURE
    path = os.path.abspath(path)
    bpy.ops.wm.save_as_mainfile(filepath=path, compress=True, relative_remap=True)
    return path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def _script_args():
    """Command line options meant for this script.

    Inside Blender (`blender -b --python build.py -- ...`) they follow '--';
    without '--' Blender's own arguments must not be parsed.
    """
    argv = sys.argv
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    if any(a in ("--python", "-P", "--python-expr", "--background", "-b") for a in argv):
        return []
    return argv[1:]


def parse_args(argv=None):
    """Parse options (after '--' when run as `blender -b --python build.py -- ...`)."""
    import argparse
    if argv is None:
        argv = _script_args()
    p = argparse.ArgumentParser(prog="build.py", description="Build the procedural gore head.")
    p.add_argument("--preset", choices=PRESET_NAMES, default=None,
                   help="preset active in the saved file (default gunshot); limits the renders to it")
    p.add_argument("--no-render", action="store_true", help="build and save only")
    p.add_argument("--out", default=os.path.join(HERE, BLEND_NAME), help=".blend output path")
    p.add_argument("--samples", type=int, default=40)
    p.add_argument("--res", type=int, default=640)
    p.add_argument("--only", default=None,
                   help="comma list: preset names, cutaway, closeup_exit, sequence, contact_sheet, hero, stages")
    p.add_argument("--render-dir", default=ghc.RENDER_DIR)
    p.add_argument("--force", action="store_true", help="render and save even if verification fails")
    return p.parse_args(argv)


def main():
    """Build everything, verify, render and save (see the module docstring)."""
    t_start = time.time()
    args = parse_args()
    objs, mats, timings = build_scene()
    print("[build] anatomy %.1f s, materials %.1f s, gore %.1f s, hair %.1f s, total build %.1f s"
          % (timings["anatomy"], timings["materials"], timings["gore"], timings["hair"], timings["build"]))
    # verify() applies and evaluates every preset once and records the timings
    ok = verify(objs)
    evals = getattr(verify, "evals", {})
    print("[build] evaluation (all layers): " + ", ".join(f"{k} {v:.2f} s" for k, v in evals.items()))
    if not ok and not args.force:
        print("[build] verification FAILED: not rendering or saving (use --force to save anyway)")
        sys.exit(1)
    times = {}
    if not args.no_render:
        presets = (args.preset,) if args.preset else PRESET_NAMES
        only = set(args.only.split(",")) if args.only else None
        times = render_all(objs, presets, args.render_dir, args.samples, args.res, only)
    path = save_blend(args.out, args.preset or "gunshot")
    size = os.path.getsize(path) / 1e6
    print("[build] summary")
    print(f"  build {timings['build']:.1f} s (anatomy {timings['anatomy']:.1f}, materials "
          f"{timings['materials']:.1f}, gore {timings['gore']:.1f}, hair {timings['hair']:.1f})")
    print("  evaluation " + ", ".join(f"{k} {v:.2f} s" for k, v in evals.items()))
    if times:
        print(f"  renders {sum(times.values()):.0f} s: " + ", ".join(f"{k} {v:.0f}" for k, v in times.items()))
    print(f"  saved {path} ({size:.1f} MB)")
    print(f"  total {time.time() - t_start:.0f} s")
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
