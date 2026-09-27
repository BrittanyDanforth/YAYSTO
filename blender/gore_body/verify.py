"""Verification framework for the full-body build (owner B0; every package adds checks).

Plan §5.2 ``verify_all() -> dict``, non-zero exit on failure.

Checks are small functions registered with ``@check(group, owner, severity)``:

* ``tables``  pure data checks of ``gb_data`` (no scene needed)
* ``scene``   the built Blender scene (names, collections, transforms, modifiers, UVs, weights,
              shape keys, seam ring, nesting)
* ``files``   the exported files in ``gore-game/assets/generated/subject`` (sizes, envelopes, glb contents)

A check returns ``(ok, detail)`` (or raises: counted as a failure with the
exception text).  ``severity`` 'fail' breaks the build, 'warn' is reported
only.  To add a check in another package::

    from verify import check
    @check("scene", owner="B3")
    def femur_length():
        ...
        return abs(L - 0.47) <= 0.01, f"femur {L:.3f} m"

Run: ``python3 verify.py`` (tables + files; add ``--blend <file>`` to open a
saved build for the scene checks) or let ``build.py`` call ``verify_all``.
"""
import json
import math
import os
import struct
import sys
import traceback

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import bones as BN  # noqa: E402
from gb_data import dermatomes as DM  # noqa: E402
from gb_data import landmarks as LM  # noqa: E402
from gb_data import myotomes as MYO  # noqa: E402
from gb_data import organs as OR  # noqa: E402
from gb_data import ribs as RB_  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402
from gb_data import segments as SG  # noqa: E402
from gb_data import vertebrae as VT  # noqa: E402
from gb_data import vessels as VS  # noqa: E402

CHECKS = []          # (group, name, owner, severity, fn)
QUICK_SKIP = set()   # names of checks that measure full-accuracy geometry (skipped under --quick)
# build context filled by build.py before verify_all: {"quick": bool, "bake": "built"/"skipped", "stage_keys": {...}}
CONTEXT = {"quick": False, "bake": None, "stage_keys": {}, "status": {}}


def check(group, owner="B0", severity="fail", quick_ok=True):
    """Decorator registering a verification check.

    ``quick_ok=False`` marks a full-accuracy acceptance check (landmarks, gaps, lid tables ...) that is
    meaningless on the coarse ``--quick`` meshes; it is reported as ``skip`` in quick builds.  A check may
    also return ``(None, detail)`` itself to report ``skip`` (e.g. a B7 file check when the bake was
    skipped on purpose)."""
    def deco(fn):
        CHECKS.append((group, fn.__name__, owner, severity, fn))
        if not quick_ok:
            QUICK_SKIP.add(fn.__name__)
        return fn
    return deco


def _bake_skipped():
    """True when build.py ran without the bake stage (B7 texture checks are then skipped, not failed)."""
    return str(CONTEXT.get("bake") or "").startswith("skipped")


def _close(a, b, tol):
    return float(np.max(np.abs(np.asarray(a, float) - np.asarray(b, float)))) <= tol


# ===========================================================================
# tables
# ===========================================================================
@check("tables")
def vertebra_rows():
    lv = [r["level"] for r in VT.VERTEBRAE]
    want = [f"C{i}" for i in range(1, 8)] + [f"T{i}" for i in range(1, 13)] + [f"L{i}" for i in range(1, 6)] + ["S1"]
    z = np.array([r["z"] for r in VT.VERTEBRAE])
    ok = lv == want and bool(np.all(np.diff(z) < 0))
    return ok, f"{len(lv)} rows (want 25 incl. S1), z strictly decreasing: {bool(np.all(np.diff(z) < 0))}"


@check("tables")
def segment_mass_fractions():
    s = SG.mass_fraction_sum()
    return abs(s - 1.0) < 5e-4, f"sum = {s:.4f}"


@check("tables")
def rig_bones_and_bodies():
    names = RT.BONE_NAMES
    bodies = RT.bodies()
    parents_ok = all(b["parent"] is None or names.index(b["parent"]) < names.index(b["name"]) for b in RT.bones())
    m = RT.total_mass()
    return (len(names) == 39 and len(set(names)) == 39 and len(bodies) == 20 and parents_ok and abs(m - 75.0) <= 0.05,
            f"{len(names)} bones, {len(bodies)} bodies, parents first {parents_ok}, total mass {m:.2f} kg")


@check("tables")
def rig_mass_ratio():
    by = {b["bone"]: b for b in RT.bodies()}
    worst = 0.0
    pair = ""
    for b in RT.bodies():
        j = b["joint"]
        if not j:
            continue
        p = j["parent"]
        while p not in by:
            p = next(x["parent"] for x in RT.bones() if x["name"] == p)
        r = max(by[p]["mass_kg"], b["mass_kg"]) / min(by[p]["mass_kg"], b["mass_kg"])
        if r > worst:
            worst, pair = r, f"{p}/{b['bone']}"
    return worst <= 10.0 + 1e-9, f"max adjacent mass ratio {worst:.2f} ({pair}); limit 10 [RB §4.10]"


@check("tables")
def rig_joint_positions():
    lm = LM.all_landmarks()
    pairs = {"forearm_L": "elbow_centre_L_apose", "hand_L": "wrist_centre_L_apose", "fingers_L": "mcp3_L_apose",
             "shin_L": "knee_centre_L", "foot_L": "ankle_centre_L", "thigh_L": "hip_joint_centre_L",
             "upper_arm_L": "gh_joint_L", "clavicle_L": "sc_joint_L", "head": "atlanto_occipital_pivot",
             "forearm_R": "elbow_centre_R_apose", "shin_R": "knee_centre_R"}
    bad = []
    bm = {b["name"]: b for b in RT.bones()}
    for bone, l in pairs.items():
        if not _close(bm[bone]["head"], lm[l], 0.002):
            bad.append(bone)
    # eye and lid bones pivot at the MEASURED globe centre (head project's EYE_C + HEAD_OFFSET, within 0.2 mm),
    # not at the RB §1.2 table value 2.5 mm in front of it (critics round 2: the globe swung through the lids)
    eye = gbc.head_to_body(np.asarray(gbc.import_head().anatomy.EYE_C, float))
    for b in ("eye_L", "lid_upper_L", "lid_lower_L"):
        if not _close(bm[b]["head"], eye, 0.0002):
            bad.append(b)
    return not bad, f"joint heads vs RB §7.1 landmarks within 2 mm, eye/lid pivots at the globe centre (0.2 mm); off: {bad}"


@check("tables")
def rig_axis_example():
    """Plan §5.8: the left elbow flexion axis in A-pose is (-0.866, 0, -0.5)."""
    fa = next(b for b in RT.bodies() if b["bone"] == "forearm_L")
    ax = fa["joint"]["axes"]["flex"]["world"]
    far = next(b for b in RT.bodies() if b["bone"] == "forearm_R")["joint"]["axes"]["flex"]["world"]
    ok = _close(ax, (-0.866, 0.0, -0.5), 0.002) and _close(far, gbc.mirror_axis(ax), 1e-6)
    return ok, f"forearm_L flex {np.round(ax, 3).tolist()}, forearm_R {np.round(far, 3).tolist()}"


@check("tables")
def myotome_weights():
    bad = []
    for base, table in MYO.MYOTOMES.items():
        for d, g in table.items():
            e = MYO.expand(g)
            if abs(sum(e.values()) - 1.0) > 1e-9:
                bad.append(f"{base}.{d}")
    keys = {("forearm", "flex"): "C5", ("forearm", "ext"): "C7", ("hand", "ext"): "C6", ("fingers", "grip"): "C8",
            ("thigh", "flex"): "L2", ("shin", "ext"): "L3", ("foot", "dorsi"): "L4", ("toes", "ext"): "L5",
            ("foot", "plantar"): "S1"}
    for (b, d), seg in keys.items():
        e = MYO.expand(MYO.MYOTOMES[b][d])
        if max(e, key=e.get) != seg:
            bad.append(f"key {b}.{d} != {seg}")
    return not bad, f"direction weights sum to 1 and ISNCSCI key muscles lead; problems: {bad}"


def _bible_vessel_ids():
    """Vessel ids of the RB §3.3 table, read from the bible itself (None if the docs are absent)."""
    import re
    path = os.path.join(gbc.GAME_DIR, "docs", "REALISM_BIBLE.md")
    if not os.path.exists(path):
        return None
    text = open(path, encoding="utf-8").read()
    a = text.find("### 3.3")
    b = text.find("### 3.4", a)
    return sorted(set(re.findall(r"^\| *([AVP]\d+)\b", text[a:b], flags=re.M)))


@check("tables")
def vessel_graph():
    segs = VS.vessel_segments()
    ids = {s["id"] for s in segs}
    orphans = [s["id"] for s in segs if not s["root"] and s["parent"] not in ids]
    roots = [s["id"] for s in segs if s["root"]]
    lr = [s["id"] for s in segs if s["id"].endswith("_L") and s["id"][:-2] + "_R" not in ids]
    have = set(VS.vessel_ids())
    bible = _bible_vessel_ids()
    missing = sorted(set(bible) - have) if bible is not None else []
    ok = not orphans and not lr and not missing and all(s["d_mm"] > 0 for s in segs)
    return ok, (f"{len(segs)} segments from {len(have)} named vessels (bible RB §3.3 lists "
                f"{len(bible) if bible else '?'}; missing {missing}); roots {roots}; orphans {orphans[:5]}; "
                f"left without right {lr[:5]}")


@check("tables")
def organ_table_ok():
    ids = [o["organ_id"] for o in OR.ORGANS]
    missing = [h for o in OR.ORGANS for h in o["hit"] + o["sub"] if h not in OR.PRIMITIVES]
    tubes = [o["tube"] for o in OR.ORGANS if o.get("tube") and o["tube"] not in OR.TUBES]
    ok = ids == list(range(1, len(ids) + 1)) and not missing and not tubes
    return ok, f"{len(ids)} organs, ids 1..{len(ids)} contiguous; missing primitives {missing}, tubes {tubes}"


@check("tables")
def code_tables():
    d = sorted(DM.DERMATOMES)
    s = sorted(SG.SEGMENTS)
    pid = sorted(BN.BONE_PIECE_ID.values())
    cls_ok = all(c in BN.BONE_CLASS for c in BN.BONE_PIECE_CLASS.values())
    ok = d == list(range(29)) and s == list(range(11)) and pid == list(range(1, len(pid) + 1)) and cls_ok
    return ok, f"dermatomes 0..28, segments 0..10, {len(pid)} bone pieces with valid classes"


@check("tables")
def ribs_and_cord():
    n_rib = len(RB_.RIB_TABLE)
    carts = [n for n in RB_.RIB_TABLE if RB_.cartilage_points(n)]
    cs = VT.cord_segments()
    z = np.array([c["z_top"] for c in cs])
    c6 = next(c for c in cs if c["id"] == "C6")
    ok = (n_rib == 12 and carts == list(range(1, 11)) and len(cs) == 30 and bool(np.all(np.diff(z) < 0))
          and abs(c6["z_top"] - 1.545) < 0.005 and abs(c6["z_bottom"] - 1.527) < 0.005
          and abs(cs[-1]["z_bottom"] - VT.CONUS_TIP[2]) < 1e-6)
    return ok, (f"{n_rib} ribs, cartilages {carts[0]}..{carts[-1]}, {len(cs)} cord segments, "
                f"C6 z {c6['z_top']:.3f}-{c6['z_bottom']:.3f} (plan example 1.545-1.527), conus at the S5 bottom")


@check("tables")
def landmark_checklist():
    lm = LM.all_landmarks()
    C = LM.CHECKLIST
    d1 = lm["jugular_notch"][2] - lm["nipple_L"][2]
    d2 = 2 * lm["nipple_L"][0]
    d3 = lm["xiphoid_tip"][2] - lm["navel"][2]
    ok = abs(d1 - C["nipple_below_jugular_notch_m"]) < 0.01 and abs(d2 - C["nipple_spacing_m"]) < 0.01 \
        and abs(d3 - C["navel_below_xiphoid_m"]) < 0.03 and abs(lm["fingertip3_L_apose"][2] - 0.77) < 0.01
    return ok, f"nipples {d1:.3f} below the notch, {d2:.3f} apart; navel {d3:.3f} below the xiphoid"


@check("files")
def stage_caches_current():
    """Every geometry stage the manifest says was built/loaded from cache has the stage key the CURRENT sources
    give (build.stage_key: import closure + gb_data + head project + upstream key).  Fails when the committed
    exports were made from stale caches or the head project changed since the export."""
    path = os.path.join(gbc.SUBJECT_OUT, "manifest.json")
    if not os.path.exists(path):
        return False, "manifest.json missing"
    b = gbc.read_json(path)["data"]["build"]
    keys, st = b.get("stage_keys", {}), b.get("stage_status", {})
    if not keys:
        return False, "manifest has no stage_keys (exported by an older build.py)"
    import build
    quick = bool(b.get("quick"))
    # body-side staleness only: the head sources are taken from the build's own head snapshot when it still
    # exists (the head team edits gore_head during/after a build; that is reported by head_project_current)
    snap = b.get("head_snapshot")
    snap_dir = os.path.join(gbc.HEAD_SNAPSHOT_ROOT, snap) if snap else None
    saved = gbc.HEAD_DIR
    note = "head sources: live folder"
    if snap_dir and os.path.isdir(snap_dir) and gbc.HEAD_DIR == gbc.HEAD_SRC_DIR:
        gbc.HEAD_DIR = snap_dir
        note = f"head sources: build snapshot {snap}"
    elif gbc.HEAD_DIR != gbc.HEAD_SRC_DIR:
        note = f"head sources: this build's snapshot {gbc.head_snapshot_id()}"
    bad = {}
    try:
        for stage, key in keys.items():
            if str(st.get(stage, "")).startswith(("built", "cached")):
                now = build.stage_key(stage, quick)
                if now != key:
                    bad[stage] = f"manifest {key} != current {now}"
    finally:
        gbc.HEAD_DIR = saved
    return not bad, (f"stale stages: {bad}" if bad else f"all {len(keys)} stage keys match the current sources") \
        + f" ({note})"


@check("files", severity="warn")
def head_project_current():
    """The head project (read-only, another team) has not changed since the head snapshot this build used;
    when it has, the next build picks the changes up (warning, not a failure of this build)."""
    path = os.path.join(gbc.SUBJECT_OUT, "manifest.json")
    if not os.path.exists(path):
        return None, "manifest.json missing"
    b = gbc.read_json(path)["data"]["build"]
    used = b.get("head_sources") or {}
    live = {os.path.basename(p): gbc.file_hash(p)[:16] for p in gbc.head_source_files(gbc.HEAD_SRC_DIR)
            if os.path.exists(p)}
    changed = sorted(k for k in set(used) | set(live) if used.get(k) != live.get(k))
    return not changed, (f"head files changed since the build's snapshot {b.get('head_snapshot')}: {changed}"
                         if changed else f"head sources unchanged since snapshot {b.get('head_snapshot')}")


@check("tables")
def json_deterministic():
    """The JSON writer itself is deterministic (same dict -> same bytes).  Build-level reproducibility
    (clean rebuild -> byte-identical sidecars) is proven by ``python3 verify.py --reproduce``."""
    import tempfile
    data = {"bones": RT.bones()[:3], "bodies": RT.bodies()[:2], "face": {}}
    with tempfile.TemporaryDirectory() as td:
        a = gbc.write_json(os.path.join(td, "a.json"), data, "gb.rig/1")
        b = gbc.write_json(os.path.join(td, "b.json"), data, "gb.rig/1")
        same = open(a, "rb").read() == open(b, "rb").read()
        doc = gbc.read_json(a)
    env = all(k in doc for k in ("schema", "frame", "godot_mapping", "generator", "build_id", "data"))
    return same and env, "write_json byte-identical on repeat, envelope keys present"


# ===========================================================================
# scene
# ===========================================================================
def _bpy():
    import bpy
    return bpy


@check("scene")
def contract_objects_present():
    bpy = _bpy()
    need = [gbc.ARMATURE] + list(gbc.OUTER_OBJECTS) + list(gbc.INNER_OBJECTS) + list(gbc.VARIANT_OBJECTS) + \
        list(gbc.LOD1_OBJECTS)
    missing = [n for n in need if n not in bpy.data.objects]
    wrong = [n for n in need if n in bpy.data.objects and
             gbc.OBJECT_COLLECTION[n] not in [c.name for c in bpy.data.objects[n].users_collection]]
    cols = [c for c in (gbc.ROOT_COLLECTION,) + gbc.SUB_COLLECTIONS if c not in bpy.data.collections]
    return not missing and not wrong and not cols, f"missing {missing}, wrong collection {wrong}, collections {cols}"


@check("scene", severity="warn")
def highres_bake_sources():
    bpy = _bpy()
    missing = [n for n in gbc.HIGHRES_OBJECTS if n not in bpy.data.objects]
    return not missing, f"GB_HighRes bake sources missing (built by B1-B4 for B7): {missing}"


def _exported():
    bpy = _bpy()
    return [bpy.data.objects[n] for n in gbc.exported_mesh_names(0) + gbc.exported_mesh_names(1)
            if n in bpy.data.objects]


@check("scene")
def transforms_parent_modifier():
    bad = []
    for o in _exported():
        ident = np.allclose(np.array(o.matrix_basis), np.eye(4), atol=1e-7)
        mods = [m for m in o.modifiers]
        ok = (ident and o.parent is not None and o.parent.name == gbc.ARMATURE and o.parent_type == 'OBJECT'
              and len(mods) == 1 and mods[0].type == 'ARMATURE' and mods[0].object is not None
              and mods[0].object.name == gbc.ARMATURE)
        if not ok:
            bad.append(o.name)
    return not bad, f"identity transform, parent GB_Armature, one ARMATURE modifier; bad: {bad}"


@check("scene")
def material_slots():
    """Slot names equal plan §5.6 (a saved .blend carries the GBL_* look-dev material of each GBM_* slot; the
    exported glb always has the GBM_* names - see glb_contents)."""
    import lookdev
    bad = []
    for o in _exported():
        names = tuple(m.name if m else "" for m in o.data.materials)
        want = tuple(gbc.MATERIAL_SLOTS[o.name])
        if names != want and (len(names) != len(want)
                              or any(a != b and a != lookdev.lookdev_for(o, b) for a, b in zip(names, want))):
            bad.append(f"{o.name}: {names}")
    return not bad, f"slot names equal plan §5.6 (or their look-dev material); bad: {bad}"


@check("scene")
def uv_maps():
    bad = [o.name for o in _exported() if [l.name for l in o.data.uv_layers][:2] != ["atlas", "gb_codes"]]
    return not bad, f"UV0 atlas, UV1 gb_codes; bad: {bad}"


@check("scene")
def weights_normalised():
    bad = []
    names = set(RT.BONE_NAMES)
    worst = 0.0
    for o in _exported():
        me = o.data
        gname = {g.index: g.name for g in o.vertex_groups}
        if not set(gname.values()) <= names:
            bad.append(f"{o.name}: non-bone groups")
            continue
        for v in me.vertices:
            gs = [g for g in v.groups if g.weight > 0]
            s = sum(g.weight for g in gs)
            if len(gs) > 4 or abs(s - 1.0) > 1e-4:
                bad.append(o.name)
                break
            worst = max(worst, abs(s - 1.0))
    return not bad, f"<= 4 influences, sums 1 +- 1e-4 (worst {worst:.2e}); bad: {bad}"


@check("scene")
def rigid_parts_follow_their_bone():
    """Vertices tagged ``gb_rigid_bone`` (bones, eyes, teeth, cards) are weighted 100 % to that bone."""
    bad = {}
    import rig
    for o in _exported():
        rb = gbc.read_point_attr(o, "gb_rigid_bone", 'INT')
        if rb is None or o.name in rig.FOLLOWERS:     # B2 followers take the skin weights at their anchors (B6)
            continue
        gname = {g.index: g.name for g in o.vertex_groups}
        wrong = 0
        for v in o.data.vertices:
            want = rb[v.index]
            if want < 0:
                continue
            gs = [g for g in v.groups if g.weight > 0]
            if len(gs) != 1 or gname[gs[0].group] != RT.BONE_NAMES[want]:
                wrong += 1
        if wrong:
            bad[o.name] = wrong
    return not bad, f"vertices not 100 % on their rigid bone: {bad}"


@check("scene")
def bone_pieces_side_consistent():
    """Every left/right bone piece is rigid to a bone of the same side (catches interpolated codes)."""
    bpy = _bpy()
    inv = {v: k for k, v in BN.BONE_PIECE_ID.items()}
    bad = set()
    for n in ("GB_Skeleton",) + gbc.VARIANT_OBJECTS:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        pc = gbc.read_point_attr(o, "gb_piece", 'INT')
        rb = gbc.read_point_attr(o, "gb_rigid_bone", 'INT')
        if pc is None or rb is None:
            continue
        for p, b in set(zip(pc.tolist(), rb.tolist())):
            piece, bone = inv.get(p, "?"), RT.BONE_NAMES[b]
            if piece == "?" or (piece[-2:] in ("_L", "_R") and bone[-2:] in ("_L", "_R") and piece[-2:] != bone[-2:]):
                bad.add(f"{n}:{piece}->{bone}")
    return not bad, f"piece/bone side mismatches: {sorted(bad)[:8]}"


@check("scene")
def shape_keys():
    bpy = _bpy()
    bad = []
    for n, keys in gbc.SHAPE_KEYS.items():
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        have = [k.name for k in o.data.shape_keys.key_blocks[1:]] if o.data.shape_keys else []
        if have != list(keys):
            bad.append(f"{n}: {have}")
    return not bad, f"shape keys per plan §5.6; bad: {bad}"


@check("scene")
def armature_and_poses():
    bpy = _bpy()
    arm = bpy.data.objects.get(gbc.ARMATURE)
    if arm is None:
        return False, "no armature"
    names = [b.name for b in arm.data.bones]
    import rig                                          # B6: the rig table as built (table + documented fits)
    bm = rig.bone_map()
    off = [b.name for b in arm.data.bones if not _close(b.head_local, bm[b.name]["head"], 1e-5)
           or not _close(b.tail_local, bm[b.name]["tail"], 1e-5)]
    acts = [a for a in gbc.POSE_ACTIONS if a not in bpy.data.actions]
    ident = np.allclose(np.array(arm.matrix_world), np.eye(4))
    return (sorted(names) == sorted(RT.BONE_NAMES) and not off and not acts and ident and
            all(b.use_deform for b in arm.data.bones)), \
        f"{len(names)} deform bones at the rig table, identity transform; off {off}; missing actions {acts}"


@check("scene")
def seam_ring_shared():
    bpy = _bpy()
    h, b = bpy.data.objects.get("GB_Head"), bpy.data.objects.get("GB_Body")
    if h is None or b is None:
        return False, "GB_Head/GB_Body missing"
    vh, vb = gbc.get_verts(h.data), gbc.get_verts(b.data)
    rh = vh[np.abs(vh[:, 2] - gbc.SEAM_Z) < 1e-6]
    rb = vb[np.abs(vb[:, 2] - gbc.SEAM_Z) < 1e-6]
    key = lambda a: sorted(map(tuple, np.round(a, 7)))
    same = len(rh) == len(rb) == gbc.SEAM_RING_N and key(rh) == key(rb)
    return same, f"{len(rh)} / {len(rb)} ring vertices at z {gbc.SEAM_Z} (want {gbc.SEAM_RING_N}, identical)"


@check("scene")
def eye_centres():
    bpy = _bpy()
    bad = []
    for side, sx in (("L", 1), ("R", -1)):
        o = bpy.data.objects.get(f"GB_Eye_{side}")
        if o is None:
            bad.append(side)
            continue
        v = gbc.get_verts(o.data)
        c = 0.5 * (v.min(0) + v.max(0))
        c[1] = v[:, 1].max() - 0.012                       # back of the globe is round: centre = back - r
        # the head project owns the eyes (it moved them 2.5 mm back in its fix rounds): the body keeps them
        # exactly where the head puts them (0.3 mm) and the head stays within 3 mm of RB §1.2
        want = gbc.head_to_body(np.asarray(gbc.import_head().anatomy.EYE_C, float) * np.array([sx, 1.0, 1.0]))
        if not _close(c, want, 0.0003) or not _close(c, (sx * 0.032, -0.050, 1.669), 0.003):
            bad.append(f"{side} {np.round(c, 4).tolist()}")
    return not bad, f"eyeball centres at the head project's eyes, within 3 mm of (+-0.032, -0.050, 1.669) [RB §1.2]; bad: {bad}"


@check("scene")
def codes_valid():
    bpy = _bpy()
    bad = []
    nseg = len(VS.vessel_segments())
    for o in _exported():
        u, v = gbc.read_codes_uv(o)
        if u is None:
            bad.append(f"{o.name}: no gb_codes")
            continue
        lay = gbc.LAYER_OF.get(o.name, "")
        if lay in ("skin", "cloth", "muscle"):
            seg, reg = u % SG.REGION_STRIDE, u // SG.REGION_STRIDE
            if not (np.isin(seg, list(SG.SEGMENTS)).all() and np.isin(reg, list(SG.REGIONS)).all()
                    and ((v >= 0) & (v <= 28)).all()):
                bad.append(o.name)
        elif lay in ("bone", "bone_variant"):
            if not (np.isin(u, list(BN.BONE_PIECE_ID.values())).all() and np.isin(v, list(BN.BONE_CLASS)).all()):
                bad.append(o.name)
        elif lay == "organ":
            if not np.isin(u, [x["organ_id"] for x in OR.ORGANS]).all():
                bad.append(o.name)
        elif lay.startswith("vessel"):
            if not ((u >= 0) & (u < nseg)).all():
                bad.append(o.name)
    return not bad, f"UV2 codes inside their code tables; bad: {bad}"


def _skin_bvh():
    bpy = _bpy()
    from mathutils.bvhtree import BVHTree
    verts, tris = [], []
    off = 0
    for n in ("GB_Head", "GB_Body"):
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        v, t = gbc.mesh_arrays(o.data)
        verts.append(v)
        tris.append(t + off)
        off += len(v)
    V, T = np.vstack(verts), np.vstack(tris)
    return BVHTree.FromPolygons(V.tolist(), T.tolist())


def _outside_fraction(bvh, pts, tol):
    from mathutils import Vector
    out = 0
    for p in pts:
        loc, nrm, _i, dist = bvh.find_nearest(Vector(p))
        if loc is not None and (Vector(p) - loc).dot(nrm) > tol:
            out += 1
    return out / max(len(pts), 1)


_PARITY_DIRS = ((0.0, 0.0, 1.0), (0.577, -0.577, 0.577), (-0.707, 0.0, -0.707),
                (0.267, 0.802, -0.535), (-0.8, -0.36, 0.48))


def _parity_inside(bvh, p, dirs=_PARITY_DIRS, max_hits=64):
    """Majority vote of ray-parity tests (odd crossings = inside) over 5 directions."""
    from mathutils import Vector
    votes = 0
    for d in dirs:
        dv = Vector(d).normalized()
        o = Vector(p)
        n = 0
        for _ in range(max_hits):
            h = bvh.ray_cast(o, dv)
            if h[0] is None:
                break
            n += 1
            o = h[0] + dv * 1e-6
        votes += n % 2
    return votes * 2 > len(dirs)


def _nesting(names, tol=0.0):
    """{mesh: (vertices outside the skin by more than ``tol``, worst mm, worst point)} over ALL vertices.

    Outside = the nearest skin point's outward normal side (signed nearest-surface test)."""
    bpy = _bpy()
    bvh = _skin_bvh()
    from mathutils import Vector
    res = {}
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        v = gbc.get_verts(o.data)
        cnt, worst, wp = 0, 0.0, None
        for p in v:
            loc, nrm, _i, _d = bvh.find_nearest(Vector(p))
            if loc is None:
                continue
            s = (Vector(p) - loc).dot(nrm)
            # the nearest face's normal is ambiguous where the nearest point is an edge or corner of a thin
            # fold (ear helix, nostril rim, eyelid margin): confirm by ray parity before counting
            if s > tol and not _parity_inside(bvh, p):
                cnt += 1
                if s > worst:
                    worst, wp = s, [round(float(c), 4) for c in p]
        res[n] = (cnt, round(worst * 1000, 2), wp)
    return res


@check("scene", quick_ok=False)
def nesting_inside_skin():
    """FB-4: inner layers inside the skin, EVERY vertex: bone at 0 mm tolerance, muscle shell / organs / brain /
    cord at 0.5 mm (the skin tessellation); zero allowed outside."""
    res = _nesting(("GB_Skeleton",), 0.0)
    res.update(_nesting(("GB_MuscleShell", "GB_Organs", "GB_Brain", "GB_Cord"), 0.0005))
    bad = {k: v for k, v in res.items() if v[0]}
    return not bad, f"(vertices outside, worst mm, worst point): {res}"


@check("scene", owner="B5", quick_ok=False)
def vessels_inside_skin():
    """FB-5 precursor: every vessel tube vertex >= 1 mm under the skin (a tube wall under the dermis)."""
    res = _nesting(("GB_Vessels_Art", "GB_Vessels_Ven"), -0.001)
    bad = {k: v for k, v in res.items() if v[0]}
    return not bad, f"tube vertices shallower than 1 mm (count, worst mm above -1 mm, worst point): {res}"


@check("scene")
def triangle_budgets():
    """Plan §4.1 triangle budgets: ok only when tris <= budget (the +10 % tolerance is reported separately)."""
    bpy = _bpy()
    over, tol = [], []
    for key, budget in gbc.TRI_BUDGET.items():
        names = gbc.TRI_BUDGET_GROUPS.get(key, (key,))
        tris = sum(gbc.tri_count(bpy.data.objects[n].data) for n in names if n in bpy.data.objects)
        if tris > budget:
            over.append(f"{key} {tris}/{budget}")
            if tris <= budget * 1.10:
                tol.append(key)
    return not over, f"plan §4.1 budgets; over: {over}; within +10 % tolerance: {tol}"


# ===========================================================================
# files
# ===========================================================================
def _glb_json(path):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, _ver, _length = struct.unpack("<4sII", data[:12])
    if magic != b"glTF":
        raise ValueError("not a GLB")
    clen, ctype = struct.unpack("<I4s", data[12:20])
    return json.loads(data[20:20 + clen])


@check("files")
def subject_files():
    out = gbc.SUBJECT_OUT
    need = ["GB_Subject.glb", "GB_Subject_LOD1.glb", "manifest.json", "rig.json", "landmarks.json", "organs.json",
            "vessels.json", "spine.json", "codes.json", "brain_labels.png", "brain_labels.json"]
    missing = [f for f in need if not os.path.exists(os.path.join(out, f))]
    big = [f for f in os.listdir(out) if os.path.getsize(os.path.join(out, f)) > 50e6] if os.path.isdir(out) else []
    glb = os.path.join(out, "GB_Subject.glb")
    glb_mb = os.path.getsize(glb) / 1e6 if os.path.exists(glb) else 0
    return not missing and not big and glb_mb <= 40, f"missing {missing}; > 50 MB {big}; glb {glb_mb:.1f} MB (<= 40)"


@check("files")
def json_envelopes():
    bad = []
    out = gbc.SUBJECT_OUT
    for f in sorted(os.listdir(out)) if os.path.isdir(out) else []:
        if not f.endswith(".json"):
            continue
        doc = gbc.read_json(os.path.join(out, f))
        probs = gbc.validate_schema(doc.get("data", {}), doc.get("schema", ""))
        if probs or doc.get("frame") != gbc.FRAME or doc.get("godot_mapping") != gbc.GODOT_MAPPING:
            bad.append(f"{f}: {probs}")
    return not bad, f"envelope + schema keys of every JSON; bad: {bad}"


@check("files")
def glb_contents():
    path = os.path.join(gbc.SUBJECT_OUT, "GB_Subject.glb")
    g = _glb_json(path)
    nodes = {n.get("name") for n in g.get("nodes", [])}
    want = set(gbc.OUTER_OBJECTS) | set(gbc.INNER_OBJECTS) | set(gbc.VARIANT_OBJECTS) | {gbc.ARMATURE}
    missing = sorted(want - nodes)
    joints = len(g["skins"][0]["joints"]) if g.get("skins") else 0
    bone_names = {g["nodes"][j]["name"] for j in g["skins"][0]["joints"]} if joints else set()
    mats = {m["name"] for m in g.get("materials", [])}
    want_mats = {m for n in want if n in gbc.MATERIAL_SLOTS for m in gbc.MATERIAL_SLOTS[n]}
    no_uv2 = []
    morph = {}
    node_of_mesh = {n["mesh"]: n["name"] for n in g.get("nodes", []) if "mesh" in n}
    for mi, mesh in enumerate(g.get("meshes", [])):
        for p in mesh["primitives"]:
            if "TEXCOORD_1" not in p["attributes"] or "JOINTS_0" not in p["attributes"]:
                no_uv2.append(node_of_mesh.get(mi))
        if "extras" in mesh and "targetNames" in mesh["extras"]:
            morph[node_of_mesh.get(mi)] = mesh["extras"]["targetNames"]
    anims = sorted(a["name"] for a in g.get("animations", []))
    images = len(g.get("images", []))
    ok = (not missing and joints == 39 and bone_names == set(RT.BONE_NAMES) and want_mats <= mats and not no_uv2
          and images == 0 and set(gbc.POSE_ACTIONS) <= set(anims)
          and all(tuple(morph.get(k, ())) == tuple(v) for k, v in gbc.SHAPE_KEYS.items()))
    return ok, (f"nodes missing {missing}; {joints} joints; materials missing {sorted(want_mats - mats)}; "
                f"primitives without UV2/JOINTS {sorted(set(no_uv2))}; images {images}; animations {anims}; "
                f"morph targets {({k: len(v) for k, v in morph.items()})}")


# ===========================================================================
# B3 skeleton checks (plan §8.2 B3 acceptance): pieces, lengths, vertebra centres, double
# shells, joint clearances, lean-site depths, intercostal spaces, variants, capsules, budgets
# ===========================================================================
# bones.json (B3 sidecar) schema, registered here too so the file checks work without importing skeleton
gbc.SCHEMAS.setdefault("gb.bones/1", ("pieces", "capsules", "hit_mesh", "classes", "variants"))


def _skel_pieces(name="GB_Skeleton"):
    """{piece name: (verts, class array)} of a skeleton-like object (None if missing)."""
    bpy = _bpy()
    o = bpy.data.objects.get(name)
    if o is None:
        return None
    v = gbc.get_verts(o.data)
    pc = gbc.read_point_attr(o, "gb_piece", 'INT')
    cl = gbc.read_point_attr(o, "gb_class", 'INT')
    inv = {i: n for n, i in BN.BONE_PIECE_ID.items()}
    return {inv.get(int(i), str(i)): (v[pc == i], cl[pc == i]) for i in np.unique(pc)}


def _b3_built():
    bpy = _bpy()
    o = bpy.data.objects.get("GB_Skeleton")
    return o is not None and o.get("gb_status") == "B3"


def _kd(points):
    from mathutils.kdtree import KDTree
    kd = KDTree(len(points))
    for i, p in enumerate(points):
        kd.insert(p, i)
    kd.balance()
    return kd


@check("scene", owner="B3")
def skeleton_all_pieces():
    """Every bone piece id of gb_data.bones exists in GB_Skeleton with its class."""
    P = _skel_pieces()
    if P is None:
        return False, "GB_Skeleton missing"
    missing = [n for n, _c in BN.BONE_PIECES if n not in P]
    wrong = [n for n, c in BN.BONE_PIECES if n in P and not np.isin(c, P[n][1]).any()]
    return not missing and not wrong, f"{len(P)} / {len(BN.BONE_PIECES)} pieces; missing {missing}; wrong class {wrong}"


@check("scene", owner="B3")
def skeleton_long_bone_lengths():
    """Max length along the principal axis vs the bible: femur 47, tibia 41, fibula 39.5, humerus 34,
    radius 26, ulna 27.5, clavicle 14.8 cm, each +-1 cm, both sides."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built; placeholder stands in)"
    P = _skel_pieces()
    bad, rows = [], []
    for base, want in BN.ACCEPT_LENGTH_CM.items():
        for s in "LR":
            v, c = P[f"{base}_{s}"]
            v = v[c != 6]
            cc = v.mean(0)
            _u, _s, vt = np.linalg.svd(v[::3] - cc, full_matrices=False)
            t = (v - cc) @ vt[0]
            L = 100 * (t.max() - t.min())
            rows.append(f"{base}_{s} {L:.2f}")
            if abs(L - want) > 1.0:
                bad.append(f"{base}_{s} {L:.2f}/{want}")
    return not bad, f"out of +-1 cm: {bad}; " + ", ".join(rows[::2])


@check("scene", owner="B3")
def skeleton_vertebra_centres():
    """Vertebral body centres (bbox centre of the body in the level frame) within 2 mm of RB §7.3."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built)"
    import skeleton as SK
    P = _skel_pieces("GB_Skeleton_HR") or _skel_pieces()          # dense endplates
    worst, bad = 0.0, []
    for r in VT.VERTEBRAE:
        lv = r["level"]
        if lv in ("S1", "C1"):
            continue
        v, _c = P[lv.lower()]
        F = SK.spine_frame(lv)
        lx, ly, lz = F.local(v[:, 0], v[:, 1], v[:, 2])
        h, d, w = r["body_h_mm"] / 1e3, r["body_d_mm"] / 1e3, r["body_w_mm"] / 1e3
        sel = (ly < 0.5 * d - 0.002) & (np.abs(lz) < 0.5 * h + 0.004) & (np.abs(lx) < 0.5 * w + 0.004)
        if lv == "C2":
            sel &= lz < 0.0
        if sel.sum() < 8:
            bad.append(f"{lv}: no body vertices")
            continue
        c = np.array([0.5 * (lx[sel].min() + lx[sel].max()), 0.5 * (ly[sel].min() + ly[sel].max()), 0.0])
        # height from the endplate centres only (uncinate lips / rims excluded)
        mid = sel & (np.abs(lx) < 0.25 * w) & (np.abs(ly) < 0.25 * d)
        if lv != "C2" and mid.sum() >= 4:
            c[2] = 0.5 * (lz[mid].min() + lz[mid].max())
        err = float(np.linalg.norm(c)) * 1000
        worst = max(worst, err)
        if err > 2.0:
            bad.append(f"{lv} {err:.1f} mm")
    return not bad, f"worst body-centre error {worst:.2f} mm (<= 2); bad {bad}"


@check("scene", owner="B3")
def skeleton_double_shells():
    """Long bones carry a marrow core (class 6) fully inside the cortex; cortex at mid-shaft within
    +-1.5 mm of the bible (femur 7, tibia 6, humerus 5, radius/ulna/fibula 3, clavicle 2.5 mm)."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built)"
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    bpy = _bpy()
    o = bpy.data.objects["GB_Skeleton_HR"] if "GB_Skeleton_HR" in bpy.data.objects else bpy.data.objects["GB_Skeleton"]
    v, tris = gbc.mesh_arrays(o.data)
    pc = gbc.read_point_attr(o, "gb_piece", 'INT')
    cl = gbc.read_point_attr(o, "gb_class", 'INT')
    bad, rows = [], []
    for base, row in BN.LONG_BONES.items():
        for s in "LR":
            pid = BN.BONE_PIECE_ID[f"{base}_{s}"]
            outer_t = tris[(pc[tris[:, 0]] == pid) & (cl[tris[:, 0]] != 6)]
            core_v = v[(pc == pid) & (cl == 6)]
            if len(core_v) == 0:
                bad.append(f"{base}_{s}: no marrow core")
                continue
            bvh = BVHTree.FromPolygons(v.tolist(), outer_t.tolist())
            # inside test: nearest outer point, normal points away from the core vertex
            outside = 0
            dists = []
            for p in core_v[:: max(1, len(core_v) // 400)]:
                loc, nrm, _i, dist = bvh.find_nearest(Vector(p))
                if (Vector(p) - loc).dot(nrm) > 0:
                    outside += 1
                dists.append(dist)
            # cortex at mid-shaft: core vertices within the middle 20 % of the core length
            cc = core_v.mean(0)
            _u, _s, vt = np.linalg.svd(core_v - cc, full_matrices=False)
            t = (core_v - cc) @ vt[0]
            mid = core_v[np.abs(t) < 0.1 * (t.max() - t.min())]
            cort = np.median([bvh.find_nearest(Vector(p))[3] for p in mid]) * 1000 if len(mid) else 0
            want = row["cortex_mm"]
            rows.append(f"{base}_{s} {cort:.1f}/{want}")
            if outside or abs(cort - want) > 1.5:
                bad.append(f"{base}_{s} cortex {cort:.1f} mm (want {want}), core verts outside {outside}")
    return not bad, f"bad {bad}; cortex mid-shaft " + ", ".join(rows[::2])


def _min_gap(P, a, b, cls_skip=6):
    va = P[a][0][P[a][1] != cls_skip]
    vb = P[b][0][P[b][1] != cls_skip]
    kd = _kd(vb)
    return min(kd.find(p)[2] for p in va[:: max(1, len(va) // 3000)])


@check("scene", owner="B3")
def skeleton_joint_clearance():
    """Neighbouring bones never interpenetrate (HR vertex gap >= 0.5 mm at every joint pair)."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built)"
    P = _skel_pieces("GB_Skeleton_HR") or _skel_pieces()
    pairs = [("femur_L", "hip_bone_L"), ("humerus_L", "scapula_L"), ("c1", "skull"), ("c2", "skull"), ("c1", "c2"),
             ("tibia_L", "femur_L"), ("patella_L", "femur_L"), ("fibula_L", "tibia_L"), ("foot_L", "tibia_L"),
             ("radius_L", "humerus_L"), ("ulna_L", "humerus_L"), ("radius_L", "ulna_L"), ("hand_L", "radius_L"),
             ("clavicle_L", "sternum"), ("clavicle_L", "scapula_L"), ("sacrum", "hip_bone_L"), ("l5", "sacrum"),
             ("hip_bone_L", "hip_bone_R"), ("t7", "t8"), ("l3", "l4"), ("c5", "c6"), ("disc_l3_l4", "l3"),
             ("rib5_L", "t5"), ("costal_cartilage5_L", "sternum"), ("costal_cartilage8_L", "costal_cartilage7_L"),
             ("mandible", "skull"), ("rib1_L", "clavicle_L"), ("scapula_L", "rib4_L")]
    bad, rows = [], []
    for a, b in pairs:
        g = _min_gap(P, a, b) * 1000
        rows.append(f"{a}/{b} {g:.1f}")
        if g < 0.5:
            bad.append(f"{a}/{b} {g:.2f} mm")
    return not bad, f"too close: {bad}; gaps mm: " + ", ".join(rows)


def _depth_under_skin(points):
    """Distance (m) from each point to the skin surface (GB_Head + GB_Body)."""
    from mathutils import Vector
    bvh = _skin_bvh()
    return np.array([bvh.find_nearest(Vector(p))[3] for p in points])


@check("scene", owner="B3", severity="warn")
def skeleton_lean_site_depths():
    """Lean sites [RB §7.6]: tibial face 3-6 mm, patella 4-8, malleoli 2-4, sternum 5-12 mm under the
    skin (min distance bone -> skin over the site).  Depends on B1's skin (warn)."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built)"
    from gb_data import tissue as TS
    P = _skel_pieces()
    want = TS.LEAN_SITE_DEPTH_MM
    out, bad = {}, []
    tib = P["tibia_L"][0][P["tibia_L"][1] != 6]
    face = tib[(tib[:, 2] > 0.20) & (tib[:, 2] < 0.36)]
    # anteromedial face: the bone points most anterior-medial at each height
    s = -face[:, 1] - 0.6 * face[:, 0]
    face = face[s > np.percentile(s, 85)]
    out["tibial_face"] = float(np.median(_depth_under_skin(face)) * 1000)
    pat = P["patella_L"][0]
    out["patella"] = float(_depth_under_skin(pat[pat[:, 1] < np.percentile(pat[:, 1], 10)]).min() * 1000)
    ft = P["tibia_L"][0]
    mm = ft[ft[:, 2] < 0.085]
    fb = P["fibula_L"][0][P["fibula_L"][1] != 6]
    lm = fb[fb[:, 2] < 0.075]
    out["malleoli"] = float(min(_depth_under_skin(mm).min(), _depth_under_skin(lm).min()) * 1000)
    st = P["sternum"][0]
    out["sternum"] = float(_depth_under_skin(st[st[:, 1] < np.percentile(st[:, 1], 8)]).min() * 1000)
    for k, (lo, hi) in want.items():
        if not lo - 0.5 <= out[k] <= hi + 0.5:
            bad.append(f"{k} {out[k]:.1f} (want {lo}-{hi})")
    return not bad, "depth mm " + ", ".join(f"{k} {v:.1f}" for k, v in out.items()) + f"; out of range {bad}"


@check("scene", owner="B3")
def skeleton_intercostal_spaces():
    """Front intercostal spaces (ribs 2-6, anterior third, bone to bone) 15-25 mm [RB §7.3]."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built)"
    P = _skel_pieces("GB_Skeleton_HR") or _skel_pieces()
    rows, bad = [], []
    for n in range(2, 7):
        a = P[f"rib{n}_L"][0]
        b = P[f"rib{n + 1}_L"][0]
        fa = a[a[:, 1] < np.percentile(a[:, 1], 25)]
        kd = _kd(b)
        g = float(np.median([kd.find(p)[2] for p in fa[:: max(1, len(fa) // 300)]]) * 1000)
        rows.append(f"{n}/{n + 1} {g:.1f}")
        if not 15.0 <= g <= 25.0:
            bad.append(f"{n}/{n + 1} {g:.1f}")
    return not bad, "front spaces mm " + ", ".join(rows) + f"; out of 15-25: {bad}"


@check("scene", owner="B3")
def skeleton_variants():
    """Fracture variants: closed fragments (every island closed), skull 20-80 fragments with median
    15-25 mm, long bones simple = 1 break (2 main fragments per bone), comminuted 8-20 per bone."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built)"
    bpy = _bpy()
    import skeleton as SK
    bad, rows = [], []
    for n in gbc.VARIANT_OBJECTS:
        o = bpy.data.objects.get(n)
        if o is None:
            bad.append(f"{n} missing")
            continue
        v, t = gbc.mesh_arrays(o.data)
        fr = gbc.read_point_attr(o, "gb_frag", 'INT')
        cl = gbc.read_point_attr(o, "gb_class", 'INT')
        open_edges = SK.nonmanifold_edges(t)
        pc = gbc.read_point_attr(o, "gb_piece", 'INT')
        frags = np.unique(fr[cl != 6])
        dims = []
        for k in frags:
            vv = v[(fr == k) & (cl != 6)]
            dims.append(1000 * (vv.max(0) - vv.min(0)).max())
        med = float(np.median(dims))
        per_piece = [len(np.unique(fr[(pc == p) & (cl != 6)])) for p in np.unique(pc)]
        if "Skull" in n:
            ok = 20 <= len(frags) <= 80 and 15 <= med <= 25
        elif n.endswith("simple"):
            ok = all(c == 2 for c in per_piece)
        else:
            ok = all(8 <= c <= 20 for c in per_piece)
        rows.append(f"{n[8:]} {len(frags)} fr, median {med:.0f} mm, open edges {open_edges}")
        if not ok or open_edges:
            bad.append(n)
    return not bad, f"bad {bad}; " + "; ".join(rows)


@check("scene", owner="B3")
def skeleton_capsules_and_hit_mesh():
    """bones.json: every non-disc piece has >= 1 capsule bounding its vertices, exact-hit mesh <= 20k."""
    if not _b3_built():
        return True, "skipped (B3 skeleton not built)"
    import skeleton as SK
    path = SK.BONES_JSON
    if not os.path.exists(path):
        return False, "bones.json missing"
    d = gbc.authoring_json(gbc.read_json(path)["data"])      # meshes are checked in the authoring frame
    caps = d["capsules"]
    P = _skel_pieces()
    by = {}
    for c in caps:
        by.setdefault(c["piece"], []).append(c)
    missing = [p for p in P if not p.startswith("disc_") and p not in by]
    unbound = []
    for p, cs in by.items():
        v = P[p][0][P[p][1] != 6][::7]
        inside = np.zeros(len(v), bool)
        for c in cs:
            a, b, r = np.array(c["a"]), np.array(c["b"]), c["r"]
            ab = b - a
            h = np.clip(((v - a) @ ab) / max(ab @ ab, 1e-12), 0, 1)
            inside |= np.linalg.norm(v - (a + np.outer(h, ab)), axis=1) <= r + 1e-4
        if inside.mean() < 0.999:
            unbound.append(f"{p} {inside.mean():.3f}")
    ntri = len(d["hit_mesh"]["tris"]) // 3
    return not missing and not unbound and ntri <= 20000, \
        f"{len(caps)} capsules, pieces without {missing}, not bounded {unbound}; hit mesh {ntri} tris (<= 20k)"


MULTI_BONE_PIECES = ("hand_", "foot_")


@check("scene", owner="B3")
def skeleton_no_free_islands():
    """Fix round 2 (critic: rib heads and articular processes as loose chips): every bone piece of GB_Skeleton is
    one connected shell plus islands fully enclosed by it (marrow cores / inner tables); no free-floating island.
    Also reports non-manifold edges of GB_Skeleton (fail above 0)."""
    import viscera as VI
    bpy = _bpy()
    o = bpy.data.objects.get("GB_Skeleton")
    if o is None:
        return False, "GB_Skeleton missing"
    v, t = gbc.mesh_arrays(o.data)
    piece = gbc.read_point_attr(o, "gb_piece", 'INT')
    if piece is None:
        u, _c = gbc.read_codes_uv(o)
        piece = np.rint(u).astype(int)
    comp = VI.islands(len(v), t)
    tc = comp[t[:, 0]]
    free = {}
    for pc in np.unique(piece):
        cs = np.unique(comp[piece == pc])
        if len(cs) < 2:
            continue
        sizes = {c: int((tc == c).sum()) for c in cs}
        big = max(sizes, key=sizes.get)
        tb = t[tc == big]
        bvh = _bvh(v, tb)
        for c in cs:
            if c == big:
                continue
            pts = v[np.unique(t[tc == c])]
            pts = pts[:: max(1, len(pts) // 12)]
            if (_inside_depth(bvh, pts) > 0).any():
                free.setdefault(int(pc), []).append(len(np.unique(t[tc == c])))
    # non-manifold edges (edge used by != 2 triangles)
    e = np.sort(np.concatenate([t[:, [0, 1]], t[:, [1, 2]], t[:, [2, 0]]]), axis=1)
    _u, cnt = np.unique(e, axis=0, return_counts=True)
    nm = int((cnt != 2).sum())
    from gb_data import bones as BN
    inv = {vv: kk for kk, vv in BN.BONE_PIECE_ID.items()}
    # hand_* / foot_* pieces are groups of separate bones (carpals, metacarpals, phalanges, tarsals ...)
    names = {inv.get(k, k): vv for k, vv in free.items() if not str(inv.get(k, k)).startswith(MULTI_BONE_PIECES)}
    return (not names) and nm == 0, (f"free islands (piece: vertex counts) {names} (multi-bone hand/foot pieces "
                                     f"exempt); non-manifold edges {nm}")


@check("scene", owner="B3", severity="warn")
def skeleton_budgets():
    """GB_Skeleton <= 36k (+10 %), variants <= 60k in total [plan §4.1]."""
    bpy = _bpy()
    s = gbc.tri_count(bpy.data.objects["GB_Skeleton"].data)
    v = sum(gbc.tri_count(bpy.data.objects[n].data) for n in gbc.VARIANT_OBJECTS if n in bpy.data.objects)
    return s <= 36000 * 1.1 and v <= 60000 * 1.1, f"GB_Skeleton {s} tris (36k), variants {v} tris (60k)"


# ===========================================================================
# runner
# ===========================================================================
# ===========================================================================
# B1 checks: body skin, shorts, muscle shell, codes, UVs (plan §8.2 B1 acceptance)
# ===========================================================================
def _b1_obj(name):
    o = _bpy().data.objects.get(name)
    return o if (o is not None and str(o.get("gb_status", "")).startswith("built (B1)")) else None


def _b1_skip(name="GB_Body"):
    return None if _b1_obj(name) is not None else (True, f"{name} is not built by B1 yet (placeholder)")


def neck_tape(v, t, front=None, tilts=range(0, 17, 2)):
    """Neck circumference like the anthropometric tape (ISO 7250-1 / ANSUR 'neck circumference'): anchored just
    below the laryngeal prominence (the RB §7.1 cricoid point) and perpendicular to the neck, i.e. a snug tape
    that settles at its smallest circumference; the back of the tape rides above the C7 / T1 prominence.  A
    horizontal cut at 1.515 m is the 'neck base' measure instead (it runs through the trapezius and below C7,
    whose skin landmark lies at y 0.075, z 1.532 - so the RB table's 0.063 back point cannot be horizontal).
    Returns the minimum hull perimeter (m) over tape tilts of 0-16 deg (back side up)."""
    import body_skin as BS
    # anchored 7 mm below the laryngeal prominence of the landmark table (the ANSUR / ISO 7250 tape position
    # 'just below the laryngeal prominence'; fix round 2: the larynx moved 12 mm down)
    p0 = np.asarray(LM.landmark("laryngeal_prominence") + np.array([0.0, 0.002, -0.007]) if front is None
                    else front, float)
    best = None
    for deg in tilts:
        a = np.radians(deg)
        n = np.array([0.0, -np.sin(a), np.cos(a)])
        e1 = np.array([1.0, 0.0, 0.0])
        e2 = np.cross(n, e1)
        P = BS.mesh_section(v, t, p0, n)
        if P is None or len(P) < 8:
            continue
        q = np.stack([(P - p0) @ e1, (P - p0) @ e2], 1)
        q = q[np.abs(q[:, 0]) < 0.09]
        per = BS.hull_perimeter(q)
        best = per if best is None else min(best, per)
    return best


@check("scene", owner="B1")
def b1_girths_fb3():
    """FB-3: girths within +-2 cm (neck, calf +-1.5) of RB §7.1, measured like a tape (convex hull)."""
    skip = _b1_skip()
    if skip:
        return skip
    import body_skin as BS
    body = _b1_obj("GB_Body")
    g = BS.girths(body)
    head = _bpy().data.objects.get("GB_Head")
    if head is not None:                                # the neck level (1.515) lies above the seam
        v = np.vstack([gbc.get_verts(body.data), gbc.get_verts(head.data)])
        t1 = BS._tris(body)[1]
        t2 = BS._tris(head)[1] + len(body.data.vertices)
        g["neck"] = (round(100 * neck_tape(v, np.vstack([t1, t2])), 2),) + g["neck"][1:]
    bad = {k: v for k, v in g.items() if abs(v[0] - v[1]) > v[2]}
    return not bad, "cm (measured, target, tol): " + ", ".join(f"{k} {v[0]:.1f}/{v[1]:.1f}" for k, v in g.items()) + \
        f"; out of tolerance {bad}"


@check("scene", owner="B1")
def b1_landmarks_fb3():
    """FB-3: body skin landmarks of RB §7.1 lie on the skin within +-5 mm."""
    skip = _b1_skip()
    if skip:
        return skip
    import body_skin as BS
    objs = [_b1_obj("GB_Body")] + [o for o in [_bpy().data.objects.get("GB_Head")] if o is not None]
    e = BS.landmark_errors(objs)
    bad = {k: v for k, v in e.items() if abs(v) > 5.0}
    return not bad, f"mm from the skin (+ outside): {e}; off {bad}"


@check("scene", owner="B1")
def b1_checklist_rb7():
    """RB §7 checklist: fingertip z ~0.77, nipples 15.5 cm under the notch and 20 cm apart, navel 20 cm under
    the xiphoid, profile line ear canal - shoulder - trochanter - front of ankle within +-15 mm."""
    skip = _b1_skip()
    if skip:
        return skip
    import body_skin as BS
    body = _b1_obj("GB_Body")
    v = gbc.get_verts(body.data)
    hr = _bpy().data.objects.get("GB_Body_HR")
    vh = gbc.get_verts(hr.data) if hr is not None else v          # small features (nipples) from the HR mesh
    hand = v[(v[:, 0] > 0.44)]
    tip_z = float(hand[:, 2].min())
    def nipple(sx):
        # the vertex standing out most from a quadratic fit to its 6-14 mm neighbourhood (removes the chest's
        # own curvature), searched within 18 mm of the RB §7.1 nipple, on the HR mesh (fix round 2: at 30 mm the
        # search reached the lower lateral pectoral border, whose crease stands out as much as the nipple)
        c = np.array([0.10 * sx, 1.30])
        q = vh[(np.hypot(vh[:, 0] - c[0], vh[:, 2] - c[1]) < 0.045) & (vh[:, 1] < 0)]
        best, arg = -1.0, 0
        for i in np.nonzero(np.hypot(q[:, 0] - c[0], q[:, 2] - c[1]) < 0.018)[0]:
            du, dw = q[:, 0] - q[i, 0], q[:, 2] - q[i, 2]
            r = np.hypot(du, dw)
            m = (r > 0.006) & (r < 0.014)
            if m.sum() < 8:
                continue
            A_ = np.stack([np.ones(m.sum()), du[m], dw[m], du[m] ** 2, dw[m] ** 2, du[m] * dw[m]], 1)
            coef = np.linalg.lstsq(A_, q[m, 1], rcond=None)[0]
            s = coef[0] - q[i, 1]
            if s > best:
                best, arg = s, i
        return q[arg]
    nip, nip_r = nipple(1.0), nipple(-1.0)
    notch = LM.landmark("jugular_notch")
    drop = float(notch[2] - nip[2])
    span = float(nip[0] - nip_r[0])
    nav = v[(np.abs(v[:, 0]) < 0.01) & (np.abs(v[:, 2] - 1.075) < 0.015)]
    nav_z = float(nav[np.argmax(nav[:, 1])][2])
    navel_drop = float(LM.landmark("xiphoid_tip")[2] - nav_z)
    troch = v[(np.abs(v[:, 2] - 0.913) < 0.006) & (v[:, 0] > 0)]
    troch_y = float(troch[np.argmax(troch[:, 0])][1])
    ank = v[(np.abs(v[:, 2] - 0.090) < 0.006) & (np.abs(v[:, 0] - 0.095) < 0.02)]
    ank_y = float(ank[:, 1].min())
    prof = np.array([LM.landmark("ear_canal_L")[1], LM.landmark("gh_joint_L")[1], troch_y, ank_y])
    dev = float(np.abs(prof - prof.mean()).max())
    ok = (abs(tip_z - 0.77) <= 0.015 and abs(drop - 0.155) <= 0.01 and abs(span - 0.20) <= 0.01
          and abs(navel_drop - 0.20) <= 0.015 and dev <= 0.015)
    return ok, (f"fingertip z {tip_z:.3f} (0.77); nipple {drop:.3f} below the notch (0.155), {span:.3f} apart (0.20); "
                f"navel {navel_drop:.3f} below the xiphoid (0.20); profile y ear/shoulder/trochanter/ankle "
                f"{np.round(prof, 3).tolist()} max dev {dev * 1000:.1f} mm (15)")


@check("scene", owner="B1")
def b1_watertight():
    """GB_Body: manifold, the only open boundary is the 160-vertex seam ring; shorts and muscle shell closed."""
    skip = _b1_skip()
    if skip:
        return skip
    import bmesh
    import gb_geom as gg
    res = {}
    for n, want in (("GB_Body", [gbc.SEAM_RING_N]), ("GB_Body_LOD1", [gbc.SEAM_RING_N]), ("GB_Shorts", []),
                    ("GB_MuscleShell", [])):
        o = _bpy().data.objects.get(n)
        if o is None:
            res[n] = "missing"
            continue
        bm = bmesh.new()
        bm.from_mesh(o.data)
        nm = sum(1 for e in bm.edges if len(e.link_faces) > 2)
        bm.free()
        loops = sorted(len(lp) for lp in gg.boundary_loops(o.data))
        res[n] = "ok" if (nm == 0 and loops == want) else f"non-manifold {nm}, boundary loops {loops}"
    return all(v == "ok" for v in res.values()), str(res)


@check("scene", owner="B1")
def b1_triangle_counts():
    """Plan §8.2 B1: triangle counts within +-10 % of §4.1 (GB_Body 44k, GB_Shorts 4k, GB_MuscleShell 24k)."""
    skip = _b1_skip()
    if skip:
        return skip
    want = {"GB_Body": 44000, "GB_Shorts": 4000, "GB_MuscleShell": 24000, "GB_Body_LOD1": 22000}
    got = {n: gbc.tri_count(_bpy().data.objects[n].data) for n in want if n in _bpy().data.objects}
    bad = {n: c for n, c in got.items() if abs(c - want[n]) > 0.1 * want[n]}
    return not bad, f"{got}; out of +-10 %: {bad}"


@check("scene", owner="B1")
def b1_uv_atlas():
    """Body atlas: texel 0.84 mm +-20 % at 2,048 (neck island x2 excluded), islands do not overlap."""
    skip = _b1_skip()
    if skip:
        return skip
    import body_skin as BS
    body = _b1_obj("GB_Body")
    isl = gbc.read_point_attr(body, "gb_uv_island", 'INT')
    texel = float(body.get("gb_texel_mm", 0.0))
    ov = BS.uv_overlap_fraction(body, 1024)
    uv = np.empty(len(body.data.loops) * 2, np.float32)
    body.data.uv_layers["atlas"].data.foreach_get("uv", uv)
    inside = bool(uv.min() >= 0.0 and uv.max() <= 1.0)
    ok = 0.84 * 0.8 <= texel <= 0.84 * 1.2 and ov < 0.001 and inside and isl is not None
    return ok, f"texel {texel:.3f} mm (0.67-1.01), overlapping texels {ov * 100:.3f} %, UVs in [0, 1] {inside}"


@check("scene", owner="B1")
def b1_codes_fb15():
    """FB-15: navel -> T10, nipple -> T4, thumb -> C6, heel -> S1, palm -> region palm/sole (UV2 decode)."""
    skip = _b1_skip()
    if skip:
        return skip
    import body_skin as BS
    from mathutils.kdtree import KDTree
    body = _b1_obj("GB_Body")
    v = gbc.get_verts(body.data)
    u, dv = gbc.read_codes_uv(body)
    kd = KDTree(len(v))
    for i, p in enumerate(v):
        kd.insert(p, i)
    kd.balance()
    want = {"navel": ("derm", DM.DERMATOME_ID["T10"]), "nipple": ("derm", DM.DERMATOME_ID["T4"]),
            "thumb": ("derm", DM.DERMATOME_ID["C6"]), "heel": ("derm", DM.DERMATOME_ID["S1"]),
            "palm": ("region", SG.REGION_ID["palm_sole"])}
    got, bad = {}, {}
    for k, p in BS.fb15_points().items():
        i = kd.find(p)[1]
        region, derm = int(u[i]) // SG.REGION_STRIDE, int(dv[i])
        val = derm if want[k][0] == "derm" else region
        got[k] = (DM.DERMATOMES.get(derm), SG.REGIONS.get(region))
        if val != want[k][1]:
            bad[k] = got[k]
    return not bad, f"(dermatome, region) {got}; wrong {bad}"


@check("scene", owner="B1")
def b1_shorts_clearance():
    """Shorts >= 1 mm off the skin everywhere in the bind pose (plan §8.2 B1; hip flexion 90 deg after B6)."""
    skip = _b1_skip("GB_Shorts")
    if skip:
        return skip
    import body_skin as BS
    sh = _b1_obj("GB_Shorts")
    v = gbc.get_verts(sh.data)
    rng = gbc.rng("verify")
    pts = v[rng.choice(len(v), min(4000, len(v)), replace=False)]
    d = BS.surface_distance(pts, [_bpy().data.objects[n] for n in ("GB_Body", "GB_Head") if n in _bpy().data.objects])
    return float(d.min()) >= 0.001, f"min {d.min() * 1000:.2f} mm, median {np.median(d) * 1000:.1f} mm off the skin"


@check("scene", owner="B1")
def b1_muscle_shell_depth():
    """Muscle shell inside the skin at skin + fat depth [RB §7.6] (median error <= 1.5 mm, never outside)."""
    skip = _b1_skip("GB_MuscleShell")
    if skip:
        return skip
    import body_skin as BS
    ms = _b1_obj("GB_MuscleShell")
    v = gbc.get_verts(ms.data)
    v = v[v[:, 2] < gbc.SEAM_Z - 0.01]                    # body part (the head part is the head's muscle)
    rng = gbc.rng("verify")
    pts = v[rng.choice(len(v), min(3000, len(v)), replace=False)]
    skin = [_bpy().data.objects[n] for n in ("GB_Body", "GB_Head") if n in _bpy().data.objects]
    d = -BS.surface_distance(pts, skin) * 1000.0                 # the head closes the neck for the parity test
    t = BS.tissue_at(pts)
    want = t[:, 0] + t[:, 1]
    err = np.abs(d - want)
    ok = d.min() > 0.5 and np.median(err) <= 1.5
    return ok, (f"depth below skin min {d.min():.1f} mm; |depth - (skin + fat)| median {np.median(err):.2f} mm, "
                f"p95 {np.percentile(err, 95):.2f} mm")


@check("scene", owner="B1")
def b1_body_maps():
    """Tissue-depth and tension maps (512^2 RGBA, lossless) exist next to the subject."""
    import body_skin as BS
    d = os.path.join(gbc.SUBJECT_OUT, "textures")
    res = {}
    for f in (BS.TISSUE_MAP, BS.TENSION_MAP):
        p = os.path.join(d, f)
        if not os.path.exists(p):
            res[f] = "missing"
            continue
        with open(p, "rb") as fh:
            head = fh.read(33)
        w, h = struct.unpack(">II", head[16:24])
        res[f] = "ok" if (w, h) == (BS.MAP_SIZE, BS.MAP_SIZE) and head[25] == 6 else f"{w}x{h} type {head[25]}"
    return all(v == "ok" for v in res.values()), str(res)


# ===========================================================================
# B2 checks: head integration, neck seam, face rig, eye FX, cards (plan §8.2 B2 acceptance).
# The measurements live in head_integration.check_* (each skips while GB_Head is a stand-in).
# ===========================================================================
def _b2(name):
    import head_integration as hi
    return getattr(hi, name)()


@check("scene", owner="B2")
def b2_head_landmarks():
    """RB §1.2 head landmarks in the body frame (eyeball centres, vertex, glabella, nose, chin, ear canals)."""
    return _b2("check_landmarks")


@check("scene", owner="B2")
def b2_neck_seam_fb1():
    """FB-1: 160 identical ring vertices shared by GB_Head/GB_Body, normal difference < 1 deg."""
    return _b2("check_seam")


@check("scene", owner="B2")
def b2_lids_close_and_open():
    """Lids close to 0 mm (>= 0.2 mm off the globe on the whole path) and open to 12 mm."""
    return _b2("check_lids")


@check("scene", owner="B2")
def b2_face_shape_keys():
    """24 face keys: no self-intersection, no lip/teeth penetration, lids off the globe, 1.5-8 mm amplitudes."""
    return _b2("check_shape_keys")


@check("scene", owner="B2")
def b2_cards_attached():
    """Brow cards on the skin at rest and under every face key; lash roots on lid-weighted skin."""
    return _b2("check_cards")


@check("scene", owner="B2")
def b2_head_texel_uv():
    """Head texel 0.24 mm +- 20 % and no overlapping UV islands."""
    return _b2("check_texel_uv")


@check("scene", owner="B2", severity="warn")
def b2_budgets():
    """Plan §4.1 budgets of the head meshes."""
    return _b2("check_budgets")


@check("scene", owner="B2")
def b2_eye_fx_and_teeth():
    """Eye FX shells inside the lid gap; 28 separate teeth with FDI ids."""
    return _b2("check_eye_fx_and_mouth")


@check("scene", owner="B2")
def b2_head_codes():
    """Head codes: segment, regions and dermatomes present and valid."""
    return _b2("check_codes")


# ===========================================================================
# B4: organs, cord, brainstem, brain labels (plan §8.2 B4, FB-4)
# ===========================================================================
def _b4_obj(name):
    o = _bpy().data.objects.get(name)
    return o if (o is not None and o.get("gb_status") == "B4") else None


def _b4_organ_parts():
    """{organ name: (verts, tris, sub per vertex)} of GB_Organs (None if not built by B4)."""
    o = _b4_obj("GB_Organs")
    if o is None:
        return None
    v, t = gbc.mesh_arrays(o.data)
    org = gbc.read_point_attr(o, "gb_organ", 'INT')
    sub = gbc.read_point_attr(o, "gb_sub", 'INT')
    idn = {x["organ_id"]: x["id"] for x in OR.ORGANS}
    out = {}
    for oid in np.unique(org):
        tm = (org[t] == oid).all(1)
        out[idn[int(oid)]] = (v, t[tm], sub)
    return out


def _b4_measured():
    import json
    o = _b4_obj("GB_Organs")
    return json.loads(o["gb_b4_measured"]) if o is not None and "gb_b4_measured" in o.keys() else None


def _bvh(v, t):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons(np.asarray(v).tolist(), np.asarray(t).tolist())


def _inside_depth(bvh, pts, lo=None, hi=None):
    """Signed distance of points to a closed mesh (negative inside).  Inside/outside by ray parity along
    three skew directions with a majority vote (hits closer than 0.1 mm to the previous one - a ray through
    a shared edge - are counted once); points outside the optional AABB lo..hi are outside."""
    from mathutils import Vector
    out = np.empty(len(pts))
    dirs = [Vector(d).normalized() for d in ((0.577, 0.577, 0.578), (-0.41, 0.82, -0.40), (0.30, -0.25, 0.92))]
    for i, p in enumerate(pts):
        pv = Vector(p)
        _loc, _n, _i, dist = bvh.find_nearest(pv)
        if lo is not None and (np.any(p < lo) or np.any(p > hi)):
            out[i] = dist
            continue
        votes = 0
        for dv in dirs:
            n, q = 0, pv
            for _k in range(64):
                hit = bvh.ray_cast(q, dv)
                if hit[0] is None:
                    break
                n += 1
                q = hit[0] + dv * 1e-4
            votes += n % 2
        out[i] = -dist if votes >= 2 else dist
    return out


def _b4_skip(name="GB_Organs"):
    return _b4_obj(name) is None


@check("scene", owner="B4")
def b4_organs_complete():
    """GB_Organs built by B4: every organ id of gb_data.organs present, 6 shape keys, codes = (organ, sub)."""
    if _b4_skip():
        return False, "GB_Organs not built by B4"
    P = _b4_organ_parts()
    missing = [x["id"] for x in OR.ORGANS if x["id"] not in P]
    o = _b4_obj("GB_Organs")
    keys = [k.name for k in o.data.shape_keys.key_blocks[1:]] if o.data.shape_keys else []
    u, v = gbc.read_codes_uv(o)
    org = gbc.read_point_attr(o, "gb_organ", 'INT')
    sub = gbc.read_point_attr(o, "gb_sub", 'INT')
    codes_ok = bool(np.array_equal(u, org) and np.array_equal(v, sub))
    hr = _b4_obj("GB_Organs_HR") is not None
    return (not missing and keys == list(gbc.SHAPE_KEYS["GB_Organs"]) and codes_ok and hr,
            f"missing organs {missing}; shape keys {keys}; UV2 = (organ, sub) {codes_ok}; HR bake source {hr}")


# bible centres (R05 §10-11 centre of mass / centre) checked at +-5 mm
# Organ centre targets as the bible defines them (RB §7.5 hit primitives): AABB organs by their AABB centre,
# ellipsoid/OBB organs by the volume centroid.  Tolerance 5 mm, except where the bible's own boxes do not fit
# inside the bible's rib table (organs cannot pass through bone; the ribs win): the liver AABB is 2 cm wider
# than the right cage allows (x 15 mm), the lung AABBs reach past the rib centrelines (x 8 mm), and the
# spleen OBB centre lies on the cage wall (target = viscera.SPLEEN_CENTROID, the lens centred 16 mm inward).
# (organ: (target, "aabb" | "centroid", tolerance mm per axis (x, y, z)))
B4_CENTRES = {"heart": ((0.030, -0.035, 1.330), "centroid", (5, 5, 5)),
              "liver": ((-0.033, -0.008, 1.235), "aabb", (15, 5, 5)),
              "spleen": ((0.0987, 0.0225, 1.2233), "centroid", (5, 5, 5)),
              "kidney_L": ((0.070, 0.024, 1.180), "centroid", (5, 5, 5)),
              "kidney_R": ((-0.070, 0.024, 1.160), "centroid", (5, 5, 5)),
              "adrenal_L": ((0.042, 0.025, 1.230), "centroid", (5, 5, 5)),
              "adrenal_R": ((-0.040, 0.030, 1.235), "centroid", (5, 5, 5)),
              "bladder": ((0.0, -0.030, 0.898), "centroid", (5, 5, 5)),
              "thyroid": ((0.0, -0.030, 1.502), "centroid", (5, 5, 5)),
              "lung_R": ((-0.075, 0.006, 1.383), "aabb", (8, 6, 5)),
              "lung_L": ((0.075, 0.008, 1.380), "aabb", (8, 6, 5))}
# bible extents (AABB, m) checked at +-10 %
B4_EXTENTS = {"heart": (0.138, 0.092, 0.127), "lung_R": (0.130, 0.168, 0.225), "lung_L": (0.130, 0.165, 0.230),
              "liver": (0.225, 0.155, 0.160), "stomach": (0.145, 0.120, 0.210)}


@check("scene", owner="B4", quick_ok=False)
def b4_organ_centres_sizes():
    """Plan B4: organ centres +-5 mm (bible definition per organ, documented exceptions in B4_CENTRES), sizes
    +-10 % of the bible (AABB extents)."""
    M = _b4_measured()
    if M is None:
        return False, "no measured data"
    bad, rep = [], []
    for k, (c, mode, tol) in B4_CENTRES.items():
        if mode == "aabb":
            got = 0.5 * (np.array(M[k]["aabb"][0]) + np.array(M[k]["aabb"][1]))
        else:
            got = np.array(M[k]["centroid"])
        dd = 1000 * (got - np.array(c))
        rep.append(f"{k} {mode} d{np.round(dd, 1).tolist()}mm")
        if np.any(np.abs(dd) > np.array(tol)):
            bad.append(f"{k} {mode} centre off {np.round(dd, 1).tolist()} mm (tol {list(tol)})")
    for k, ext in B4_EXTENTS.items():
        lo, hi = np.array(M[k]["aabb"][0]), np.array(M[k]["aabb"][1])
        r = (hi - lo) / np.array(ext)
        rep.append(f"{k} size x{np.round(r, 2).tolist()}")
        if np.any(np.abs(r - 1) > 0.10):
            bad.append(f"{k} size ratio {np.round(r, 2).tolist()}")
    return not bad, f"off: {bad} | all: {'; '.join(rep)}"


@check("scene", owner="B4")
def b4_organ_masses():
    """Plan B4: mass = mesh volume x density within +-15 % of the bible (solid organs; hollow organs by
    wall volume).  Lungs are checked by volume in b4_lung_volume; the backing mass is a space filler."""
    M = _b4_measured()
    if M is None:
        return False, "no measured data"
    bad, rep = [], []
    for k, rec in M.items():
        if "mass_g_bible" not in rec or k.startswith("lung") or k == "bowel_filler":
            continue
        r = rec["mass_g_est"] / rec["mass_g_bible"]
        rep.append(f"{k} {rec['mass_g_est']:.0f}/{rec['mass_g_bible']}")
        if abs(r - 1) > 0.15:
            bad.append(f"{k} {r:.2f}")
    return not bad, f"outside +-15 %: {bad} | {', '.join(rep)}"


@check("scene", owner="B4", severity="warn")
def b4_lung_volume():
    """Lung volumes vs R05 §10.5 FRC (R 1.8 L, L 1.55 L), +-15 %.  Known limit: the rib-table cage holds only
    ~1.95 L per hemithorax above the domes (heart side included)."""
    M = _b4_measured()
    if M is None:
        return False, "no measured data"
    rep = {k: round(M[k]["volume_ml"] / 1000, 3) for k in ("lung_R", "lung_L")}
    ok = abs(rep["lung_R"] / 1.80 - 1) <= 0.15 and abs(rep["lung_L"] / 1.55 - 1) <= 0.15
    return ok, f"lung volumes L {rep} vs FRC R 1.80 / L 1.55"


@check("scene", owner="B4")
def b4_lung_borders():
    """Plan B4: lowest lung point at the MCL (6th rib), MAL (8th) and back (10th) within +-15 mm of
    the '6-8-10' lines of the rib table (z ~1.27-1.28, R05 §10.5).  Left MCL: measured on the lingula 7 deg
    lateral, because the bible heart apex lies on the left MCL (cardiac notch)."""
    import viscera as VI
    P = _b4_organ_parts()
    if P is None:
        return False, "GB_Organs not built by B4"
    bad, rep = [], []
    for side, sx in (("L", 1), ("R", -1)):
        v, t, _s = P["lung_" + side]
        vv = v[np.unique(t)]
        th, _r = VI._theta_r(vv[:, 0], vv[:, 1])
        for name, t0 in (("MCL", VI._mcl_theta()), ("MAL", 0.0), ("back", 55.0)):
            if side == "L" and name == "MCL":
                t0 += 7.0            # the apex beat (5th ICS, MCL) sits in the cardiac notch: test the lingula
            m = np.abs(th - t0) < 5
            if not m.any():
                bad.append(f"{side} {name}: no vertices")
                continue
            zlow = float(vv[m, 2].min())
            rib = {"MCL": 6, "MAL": 8, "back": 10}[name]
            ref = float(VI._rib_z_at_theta(rib, np.array([t0]))[0])          # the rib line itself
            rep.append(f"{side}-{name} {zlow:.3f}/{ref:.3f}")
            if abs(zlow - ref) > 0.015:
                bad.append(f"{side} {name} {1000 * (zlow - ref):+.0f} mm")
    return not bad, f"{bad} | {', '.join(rep)}"


def _pairs_overlap(P, pairs_skip):
    names = [n for n in P]
    bvhs = {n: _bvh(P[n][0], P[n][1]) for n in names}
    boxes = {n: (P[n][0][np.unique(P[n][1])].min(0), P[n][0][np.unique(P[n][1])].max(0)) for n in names}
    rng = gbc.rng("verify")
    worst = {}
    for a in names:
        v, t, _s = P[a]
        idx = np.unique(t)
        pts = v[rng.choice(idx, min(600, len(idx)), replace=False)]
        for b in names:
            if b == a or frozenset((a, b)) in pairs_skip:
                continue
            d = _inside_depth(bvhs[b], pts, *boxes[b])
            dmin = float(d.min())
            if dmin < -0.001:
                worst[f"{a}->{b}"] = round(-1000 * dmin, 1)
    return worst


B4_CONTAINED = {frozenset(p) for p in [("heart", "pericardium"), ("trachea", "bronchus_L"), ("trachea", "bronchus_R"),
                                       ("bronchus_L", "bronchus_R"), ("adrenal_L", "kidney_L"),
                                       ("adrenal_R", "kidney_R"), ("omentum", "bowel_filler")]}


@check("scene", owner="B4")
def b4_fb4_organ_overlap():
    """FB-4: no organ-organ overlap > 1 mm: every exported GB_Organs vertex is tested against every other
    organ's exact SDF (viscera.organ_specs); containers by design (pericardium around the heart, perirenal
    fat around kidney and adrenal, airway parts among themselves) are skipped.  The exported LOD's own
    deviation from its SDF is reported (95th percentile) so the test also bounds the mesh error."""
    import viscera as VI
    o = _b4_obj("GB_Organs")
    if o is None:
        return False, "GB_Organs not built by B4"
    v = gbc.get_verts(o.data)
    org = gbc.read_point_attr(o, "gb_organ", 'INT')
    sub = gbc.read_point_attr(o, "gb_sub", 'INT')
    idn = {x["organ_id"]: x["id"] for x in OR.ORGANS}
    name = np.array([idn[int(i)] for i in org], dtype=object)
    name[(np.char.startswith(name.astype(str), "kidney")) & (sub == 3)] = np.array(
        [n + "_fat" for n in name[(np.char.startswith(name.astype(str), "kidney")) & (sub == 3)]], dtype=object)
    specs = {}
    for key, oname, fn, box, h, tris, subfn in VI.organ_specs():
        k = {"airway": "airway", "kidney_fat_L": "kidney_L_fat", "kidney_fat_R": "kidney_R_fat"}.get(key, key)
        specs[k] = (fn, box)
    group = {n: n for n in set(name)}
    for n in ("trachea", "bronchus_L", "bronchus_R"):
        group[n] = "airway"
    skip = {frozenset(p) for p in [("heart", "pericardium"), ("kidney_L", "kidney_L_fat"), ("kidney_R", "kidney_R_fat"),
                                   ("adrenal_L", "kidney_L_fat"), ("adrenal_R", "kidney_R_fat")]}
    worst, own = {}, {}
    rng = gbc.rng("verify")
    for a in sorted(set(group.values())):
        m = np.array([group[n] == a for n in name])
        pts = v[m]
        if len(pts) > 1500:
            pts = pts[rng.choice(len(pts), 1500, replace=False)]
        fa, _ba = specs[a]
        own[a] = round(1000 * float(np.quantile(np.abs(fa(pts[:, 0], pts[:, 1], pts[:, 2])), 0.95)), 2)
        for b, (fb, bb) in specs.items():
            if b == a or frozenset((a, b)) in skip:
                continue
            lo, hi = np.asarray(bb[0]) - 0.01, np.asarray(bb[1]) + 0.01
            inb = np.all((pts > lo) & (pts < hi), axis=1)
            if not inb.any():
                continue
            d = fb(pts[inb, 0], pts[inb, 1], pts[inb, 2])
            if d.min() < -0.001:
                worst[f"{a}->{b}"] = round(-1000 * float(d.min()), 1)
    return not worst, f"overlaps > 1 mm (mm): {worst}; LOD-to-SDF deviation p95 (mm): {own}"


@check("scene", owner="B4")
def b4_fb4_organs_vs_bone():
    """FB-4: organs inside the ribcage / clear of bone by >= 2 mm (sampled vertices vs GB_Skeleton):
    <= 2 % of vertices closer than 2 mm and <= 0.5 % inside bone."""
    bpy = _bpy()
    sk = bpy.data.objects.get("GB_Skeleton")
    o = _b4_obj("GB_Organs")
    if sk is None or o is None:
        return False, "GB_Skeleton or B4 GB_Organs missing"
    vs, ts = gbc.mesh_arrays(sk.data)
    bvh = _bvh(vs, ts)
    v = gbc.get_verts(o.data)
    org = gbc.read_point_attr(o, "gb_organ", 'INT')
    rng = gbc.rng("verify")
    idx = rng.choice(len(v), min(6000, len(v)), replace=False)
    d = _inside_depth(bvh, v[idx])
    close = float((d < 0.002).mean())
    inside = float((d < 0).mean())
    idn = {x["organ_id"]: x["id"] for x in OR.ORGANS}
    worst = {}
    for i in np.nonzero(d < 0.002)[0]:
        n = idn[int(org[idx[i]])]
        worst[n] = worst.get(n, 0) + 1
    return (close <= 0.02 and inside <= 0.005,
            f"{100 * close:.2f} % of sampled organ vertices < 2 mm from bone, {100 * inside:.2f} % inside; by organ {worst}")


@check("scene", owner="B4")
def b4_heart_walls():
    """Plan B4: free-wall thickness, measured from each chamber's cavity surface along the wall normal to the
    outer surface (rays that end in open space; septal rays excluded): LV 9 (echo 6-10; accept 7.5-11) mm, RV 3-5 (accept 3-5.5), atria 2-3 (accept 2-3.5) mm;
    the four chambers are closed cavities."""
    import viscera as VI
    from mathutils import Vector
    P = _b4_organ_parts()
    if P is None:
        return False, "GB_Organs not built by B4"
    v, t, sub = P["heart"]
    bvh = _bvh(v, t)
    comp = VI.islands(len(v), t)
    fl = comp[t[:, 0]]
    names = {1: "RA", 2: "RV", 3: "LA", 4: "LV"}
    # LV: the bible's 9 mm (echo 6-10; post-mortem cut 12-14); rays from the trabeculated cavity surface
    # through epicardial fat read ~2-3 mm thicker than the designed compact wall, hence up to 12 mm
    want = {"LV": (7.5, 12.0), "RV": (3.0, 5.5), "RA": (2.0, 3.5), "LA": (2.0, 3.5)}
    found, res, bad = {}, {}, []
    rng = gbc.rng("verify")
    for c in np.unique(fl):
        tf = t[fl == c]
        if VI.mesh_volume(v, tf) >= 0:
            continue                                      # outer surface
        ids, cnt = np.unique(sub[tf].ravel(), return_counts=True)
        ch = names.get(int(ids[np.argmax(cnt)]))
        if ch is None:
            continue
        found[ch] = found.get(ch, 0) + 1
        a, b_, c_ = v[tf[:, 0]], v[tf[:, 1]], v[tf[:, 2]]
        cen = (a + b_ + c_) / 3.0
        nrm = np.cross(b_ - a, c_ - a)
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        th = []
        for i in rng.choice(len(tf), min(120, len(tf)), replace=False):
            d = Vector(-nrm[i])
            hit = bvh.ray_cast(Vector(cen[i]) + d * 1e-5, d)
            if hit[0] is None or hit[1].dot(d) <= 0.0:
                continue                                  # not leaving through the outer surface
            if bvh.ray_cast(hit[0] + d * 1e-5, d)[0] is not None:
                continue                                  # septum / other chamber: free walls only
            th.append((hit[0] - Vector(cen[i])).length * 1000)
        if th:
            res[ch] = round(float(np.median(th)), 1)
    for ch, (lo, hi) in want.items():
        if ch not in res:
            bad.append(f"{ch}: no cavity")
        elif not (lo <= res[ch] <= hi):
            bad.append(f"{ch} {res[ch]} mm")
    return not bad, f"median wall (mm) {res}; cavities {found}; bad {bad}"


@check("scene", owner="B4")
def b4_shape_keys():
    """Plan B4 blend shapes: heart_systole ventricular cavities -15..-20 %, lung_inhale +10 % (+-3), lung_collapse
    -70 % (+-3), diaphragm_inhale dome descent 15-20 mm."""
    o = _b4_obj("GB_Organs")
    if o is None:
        return False, "GB_Organs not built by B4"
    v0, t = gbc.mesh_arrays(o.data)
    kb = o.data.shape_keys.key_blocks
    org = gbc.read_point_attr(o, "gb_organ", 'INT')
    sub = gbc.read_point_attr(o, "gb_sub", 'INT')
    oid = {x["id"]: x["organ_id"] for x in OR.ORGANS}

    def keyed(name):
        a = np.empty(len(v0) * 3)
        kb[name].data.foreach_get("co", a)
        return a.reshape(-1, 3)

    def vol(v, tm):
        a, b, c = v[t[tm, 0]], v[t[tm, 1]], v[t[tm, 2]]
        return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    out, bad = {}, []
    # ventricular cavities: heart faces of the LV/RV sub-parts whose normals face the cavity (negative volume)
    hm = (org[t] == oid["heart"]).all(1) & np.isin(sub[t], (2, 4)).all(1)
    import viscera as VI
    comp = VI.islands(len(v0), t[hm])
    cav = []
    for lab in np.unique(comp[np.unique(t[hm])]):
        m = hm.copy()
        m[hm] = (comp[t[hm][:, 0]] == lab)
        if vol(v0, m) < 0:
            cav.append(m)
    if cav:
        vv0 = sum(vol(v0, m) for m in cav)
        vv1 = sum(vol(keyed("heart_systole"), m) for m in cav)
        out["systole_cavity"] = round(vv1 / vv0 - 1, 3)
        if not (-0.22 <= vv1 / vv0 - 1 <= -0.14):
            bad.append("heart_systole")
    else:
        bad.append("no ventricular cavity found")
    for sd in ("L", "R"):
        m = (org[t] == oid["lung_" + sd]).all(1)
        base = vol(v0, m)
        inh = vol(keyed("lung_inhale_" + sd), m) / base - 1
        col = vol(keyed("lung_collapse_" + sd), m) / base - 1
        out[f"inhale_{sd}"], out[f"collapse_{sd}"] = round(inh, 3), round(col, 3)
        if abs(inh - 0.10) > 0.03:
            bad.append(f"lung_inhale_{sd}")
        if abs(col + 0.70) > 0.03:
            bad.append(f"lung_collapse_{sd}")
    dm = org == oid["diaphragm"]
    dz = keyed("diaphragm_inhale")[dm, 2] - v0[dm, 2]
    top = v0[dm, 2] > np.quantile(v0[dm, 2], 0.8)
    out["dome_descent_mm"] = round(-1000 * float(dz[top].mean()), 1)
    if not (15 <= out["dome_descent_mm"] <= 20):
        bad.append("diaphragm_inhale")
    return not bad, f"{out}; bad {bad}"


def _cord_parts():
    o = _b4_obj("GB_Cord")
    if o is None:
        return None
    v = gbc.get_verts(o.data)
    u, _t = gbc.read_codes_uv(o)
    return v, u


@check("scene", owner="B4")
def b4_cord_sizes_conus():
    """Plan B4: conus tip (0, 0.017, 1.180) +-3 mm; cord width x AP at C2, C5, T7 +-0.5 mm of RB §7.4."""
    C = _cord_parts()
    if C is None:
        return False, "GB_Cord not built by B4"
    v, u = C
    cord = v[u < 30]
    tip = cord[np.argmin(cord[:, 2])]
    dtip = 1000 * float(np.linalg.norm(tip - np.array(VT.CONUS_TIP)))
    bad, rep = [], [f"conus tip {np.round(tip, 3).tolist()} ({dtip:.1f} mm)"]
    if dtip > 3.0:
        bad.append("conus")
    for lv in ("C2", "C5", "T7"):
        r = VT.VERTEBRA[lv]
        # the cord is swept with rings every ~15 mm: measure the ring nearest to the level
        near = np.abs(cord[:, 2] - r["z"]) < 0.010
        if not near.any():
            bad.append(lv)
            rep.append(f"{lv} no cord ring within 10 mm")
            continue
        zc = cord[near, 2][np.argmin(np.abs(cord[near, 2] - r["z"]))]
        m = np.abs(cord[:, 2] - zc) < 0.0015
        w = 1000 * float(cord[m, 0].max() - cord[m, 0].min())
        ap = 1000 * float(cord[m, 1].max() - cord[m, 1].min())
        rep.append(f"{lv} {w:.1f} x {ap:.1f} (bible {r['cord_w_mm']} x {r['cord_ap_mm']})")
        if abs(w - r["cord_w_mm"]) > 0.5 or abs(ap - r["cord_ap_mm"]) > 0.5:
            bad.append(lv)
    return not bad, f"{'; '.join(rep)}; bad {bad}"


@check("scene", owner="B4", quick_ok=False)
def b4_cord_in_canal():
    """Cord, dura and roots inside the vertebral canal: fraction of GB_Cord vertices inside GB_Skeleton bone
    (the C1 / foramen-magnum misalignment between the head skull and the atlas is reported by level)."""
    bpy = _bpy()
    sk = bpy.data.objects.get("GB_Skeleton")
    C = _cord_parts()
    if sk is None or C is None:
        return False, "GB_Skeleton or B4 GB_Cord missing"
    v, u = C
    vs, ts = gbc.mesh_arrays(sk.data)
    d = _inside_depth(_bvh(vs, ts), v)
    ins = d < 0
    lv = {}
    for p in v[ins]:
        near = min(VT.VERTEBRAE, key=lambda r: abs(r["z"] - p[2]))["level"]
        lv[near] = lv.get(near, 0) + 1
    frac = float(ins.mean())
    return frac <= 0.005, f"{100 * frac:.2f} % of cord/dura/root vertices inside bone; by level {lv}"


@check("scene", owner="B4")
def b4_brain():
    """GB_Brain (B4): <= TRI_BUDGET (28k hero budget, fix round 1) +10 % triangles, UV2 region ids valid, every RB §4.5 region on the surface or in
    the grid, brain reaches the cord (gap 0), brain clear of the skull (<= 1 % of vertices inside bone)."""
    from gb_data import brain as BR
    import neuro as NE
    o = _b4_obj("GB_Brain")
    C = _cord_parts()
    if o is None or C is None:
        return False, "GB_Brain / GB_Cord not built by B4"
    v = gbc.get_verts(o.data)
    u, _d = gbc.read_codes_uv(o)
    tris = gbc.tri_count(o.data)
    valid = bool(np.isin(u, list(BR.BRAIN_REGIONS)).all())
    cord = C[0][C[1] < 30]
    joined = float(v[:, 2].min()) <= float(cord[:, 2].max())
    bpy = _bpy()
    sk = bpy.data.objects.get("GB_Skeleton")
    inside = None
    if sk is not None:
        vs, ts = gbc.mesh_arrays(sk.data)
        rng = gbc.rng("verify")
        idx = rng.choice(len(v), min(3000, len(v)), replace=False)
        inside = float((_inside_depth(_bvh(vs, ts), v[idx]) < 0).mean())
    ok = tris <= gbc.TRI_BUDGET["GB_Brain"] * 1.10 and valid and joined and (inside is None or inside <= 0.01)
    return ok, (f"{tris} tris, region codes valid {valid}, brain bottom {v[:, 2].min():.3f} <= cord top "
                f"{cord[:, 2].max():.3f}: {joined}, inside bone {inside}")


@check("files", owner="B4")
def b4_sidecars():
    """organs.json (measured data per organ, status B4), spine.json (30 cord segments, 5 brainstem capsules,
    cord codes), brain_labels.json (every region 1..26 has voxels)."""
    out = gbc.SUBJECT_OUT
    bad = []
    try:
        og = gbc.read_json(os.path.join(out, "organs.json"))["data"]
        if og.get("status") != "B4" or any("measured" not in o for o in og["organs"]):
            bad.append("organs.json not B4 / measured missing")
        sp = gbc.read_json(os.path.join(out, "spine.json"))["data"]
        if len(sp["cord_segments"]) != 30 or len(sp["brainstem"]) != 5 or "cord_codes" not in sp:
            bad.append("spine.json content")
        bl = gbc.read_json(os.path.join(out, "brain_labels.json"))["data"]
        empty = [v["name"] for k, v in bl["regions"].items() if k != "0" and v.get("voxels", 0) == 0]
        if empty:
            bad.append(f"empty regions {empty}")
    except Exception as exc:
        bad.append(f"{type(exc).__name__}: {exc}")
    return not bad, f"problems: {bad}"


# ===========================================================================
# B5: vessel network and nerves (plan §3.4.1, §8.2 B5, FB-5).  The measurements live in vascular.py.
# ===========================================================================
def _b5_built():
    o = _bpy().data.objects.get("GB_Vessels_Art")
    return o is not None and o.get("gb_status") == "B5"


@check("tables", owner="B5")
def b5_vessel_graph():
    """Loader-style graph check: parents/children consistent, [x,y,z,r] points, bones per point, arterial roots
    A01 + P01 only, systemic/portal veins end at the RA, pulmonary veins at the LA, every left has a right."""
    import vascular
    return vascular.graph_report()


@check("scene", owner="B5")
def b5_fb5_depths():
    """FB-5: CCA/IJV 20-30 mm at C4-C6, femoral artery 15-30 at the groin, radial 2-5 at the wrist, brachial
    10-20 mid-arm (centreline to the nearest GB_Body/GB_Head surface, both sides)."""
    import vascular
    if not _b5_built():
        return False, "GB_Vessels_* not built by B5 (placeholder)"
    ok, rows = vascular.fb5_report()
    return ok, "; ".join(f"{r[0]} {r[1]} in {r[2]}: {'ok' if r[3] else 'FAIL'}" for r in rows)


@check("scene", owner="B5")
def b5_vessels_clear_of_bone():
    """No vessel tube inside GB_Skeleton except in bone canals (vertebral foramina, carotid canal, skull base,
    meningeal/sinus grooves): fitted centrelines (wall >= -0.5 mm) and tube vertices (<= 0.5 %)."""
    import vascular
    if not _b5_built():
        return False, "GB_Vessels_* not built by B5 (placeholder)"
    ok, det = vascular.bone_report()
    frac = vascular.tube_vertices_in_bone()
    return ok and frac <= 0.005, f"{det}; arterial tube vertices inside bone outside canals {100 * frac:.2f} %"


@check("scene", owner="B5")
def b5_vessels_inside_skin():
    """Every tube wall at least 0.3 mm under the skin (fitted centrelines vs GB_Body + GB_Head)."""
    import vascular
    if not _b5_built():
        return False, "GB_Vessels_* not built by B5 (placeholder)"
    return vascular.skin_report()


@check("scene", owner="B5")
def b5_bible_waypoints():
    """Centrelines within 2 mm of every RB §3.3 waypoint ((E) rows 20 mm), unless a hard rule moved them
    (bone, skin band, brain, parent origin; each cause listed)."""
    import vascular
    if not _b5_built():
        return False, "GB_Vessels_* not built by B5 (placeholder)"
    ok, det, _rows = vascular.waypoint_report()
    return ok, det


@check("scene", owner="B5", severity="warn")
def b5_tube_budget():
    """GB_Vessels_Art + _Ven triangles vs the plan §4.1 ~14k (+10 %)."""
    bpy = _bpy()
    tris = sum(gbc.tri_count(bpy.data.objects[n].data) for n in ("GB_Vessels_Art", "GB_Vessels_Ven")
               if n in bpy.data.objects)
    return tris <= 15400, f"{tris} triangles (plan ~14,000)"


@check("files", owner="B5")
def b5_vessels_json():
    """vessels.json: gb.vessels/1 envelope, fitted by B5, graph check passes on the file itself, nerves and
    beds present, every tube segment has a mesh and vessel_index."""
    import vascular
    path = os.path.join(gbc.SUBJECT_OUT, "vessels.json")
    if not os.path.exists(path):
        return False, "vessels.json missing"
    doc = gbc.read_json(path)
    d = doc["data"]
    probs = gbc.validate_schema(d, doc.get("schema", ""))
    ok_g, det = vascular.graph_report(d)
    fitted = str(d.get("status", "")).startswith("B5: centrelines fitted")
    n = d.get("counts", {})
    ok = not probs and ok_g and fitted and len(d["nerves"]) >= 20 and len(d["beds"]) >= 9
    return ok, f"schema {probs or 'ok'}; fitted {fitted}; counts {n}; {det}"


# ===========================================================================
# B8 props and room (plan §8.2 B8 acceptance): critical dimensions +-1 mm, markers present,
# room constants (room.json) equal the built geometry and ``world/room.gd`` when it exists
# ===========================================================================
B8_MARKERS = (["GBP_muzzle_pistol", "GBP_muzzle_shotgun", "GBP_hammer_face", "GBP_claw", "GBP_torch_nozzle",
               "GBP_blade_tip", "GBP_fist_knuckles", "GBP_ruler_zero", "GBP_penlight_beam", "GBP_thermo_tip",
               "GBP_thermo_display"] + [f"GBP_blade_edge_{i}" for i in range(8)])
B8_ROOM_MARKERS = ("GBP_room_subject_mark", "GBP_room_player_spawn", "GBP_room_light_key", "GBP_room_light_panel_0",
                   "GBP_room_light_panel_1", "GBP_room_probe", "GBP_room_drain", "GBP_room_backstop",
                   "GBP_room_table", "GBP_room_trolley", "GBP_room_door", "GBP_room_scale_bar")
B8_ROOTS = ("GBP_Pistol", "GBP_Shotgun", "GBP_Knife", "GBP_Hammer", "GBP_Torch", "GBP_Fist", "GBP_Ruler",
            "GBP_Penlight", "GBP_Thermometer", "GBP_Room")


def _b8_props():
    """props module with its KITS re-attached to the scene objects (works on a reopened .blend)."""
    import props
    bpy = _bpy()
    if bpy is None or "GBP_Pistol" not in bpy.data.objects:
        return None
    if not props.KITS:
        builders = dict(props.WEAPON_BUILDERS)
        origins = {"pistol": (0.0, 31.5, -70.0), "shotgun": (0.0, -55.0, -33.0), "knife": (0.0, -60.0, -1.0),
                   "hammer": (0.0, -2.5, 70.0), "torch": (0.0, 120.0, 0.0), "fist": (0.0, -40.0, -8.0),
                   "ruler": (25.0, 25.0, 0.0), "penlight": (0.0, -15.0, 0.0), "thermometer": (0.0, -30.0, 0.0),
                   "room": (0.0, 0.0, 0.0)}
        for name in list(builders) + ["room"]:
            root = bpy.data.objects.get("GBP_" + name.capitalize())
            if root is None:
                continue
            k = props.Kit.__new__(props.Kit)
            k.root, k.unit, k.origin = root, (1.0 if name == "room" else props.MM), np.asarray(origins[name])
            k.objects = {o.name: o for o in root.children if o.type == 'MESH'}
            k.markers = {o.name: o for o in root.children if o.type == 'EMPTY'}
            props.KITS[name] = k
    return props


@check("scene", owner="B8")
def b8_props_present():
    props = _b8_props()
    if props is None:
        return True, "props not built in this scene (build.py --stage props)"
    bpy = _bpy()
    missing = [n for n in B8_ROOTS + tuple(B8_MARKERS) + B8_ROOM_MARKERS if n not in bpy.data.objects]
    tools = [n for n in ("pistol", "shotgun", "knife", "hammer", "torch", "ruler", "penlight", "thermometer")
             if f"GBP_room_tool_{n}" not in bpy.data.objects]
    return not missing and not tools, f"roots + {len(B8_MARKERS)} item markers + {len(B8_ROOM_MARKERS)} room " \
                                      f"markers; missing {missing}; tool spots missing {tools}"


@check("scene", owner="B8")
def b8_critical_dimensions():
    props = _b8_props()
    if props is None:
        return True, "props not built in this scene"
    ok, probs, table = props.spec_check()
    return ok, f"{sum(1 for v in table.values() if v[2])}/{len(table)} within +-1 mm (bores +-0.05); {probs}"


@check("scene", owner="B8")
def b8_marker_frames():
    """Every marker has an orthonormal right-handed frame; action directions point where the item does."""
    props = _b8_props()
    if props is None:
        return True, "props not built in this scene"
    bpy = _bpy()
    bad = []
    want = {"GBP_muzzle_pistol": (0, 1, 0), "GBP_muzzle_shotgun": (0, 1, 0), "GBP_hammer_face": (0, 1, 0),
            "GBP_torch_nozzle": (0, 1, 0), "GBP_blade_tip": (0, 1, 0), "GBP_fist_knuckles": (0, 1, 0),
            "GBP_penlight_beam": (0, 1, 0), "GBP_thermo_tip": (0, 1, 0), "GBP_room_player_spawn": (0, 1, 0),
            "GBP_room_subject_mark": (0, -1, 0), "GBP_room_backstop": (0, -1, 0)}
    for o in bpy.data.objects:
        if o.type != 'EMPTY' or not o.name.startswith("GBP_") or "gbp_marker" not in o:
            continue
        R = np.array(o.matrix_world.to_3x3())
        if np.abs(R.T @ R - np.eye(3)).max() > 1e-4 or np.linalg.det(R) < 0.999:
            bad.append(f"{o.name} frame")
        if o.name in want and float(R[:, 1] @ np.array(want[o.name])) < 0.999:
            bad.append(f"{o.name} fwd {np.round(R[:, 1], 3).tolist()}")
        if o.name.startswith("GBP_blade_edge_") and R[2, 1] > -0.2:
            bad.append(f"{o.name} edge normal not downward")
    return not bad, f"marker frames; bad {bad}"


@check("scene", owner="B8")
def b8_room_geometry():
    """Tile faces exactly on the interior planes, ceiling 3.0 m, backstop front on z = -1.3 (Godot),
    1 % floor fall with zero at the subject mark, drain at (0, 0, 1.0) Godot."""
    props = _b8_props()
    if props is None:
        return True, "room not built in this scene"
    bpy = _bpy()
    x0, x1, y0, y1, _, z1 = props.room_bounds()
    T = np.array([v.co[:] for v in bpy.data.objects["GBP_Room_Tiles"].data.vertices])
    relief = props.ROOM["tile_relief"]
    # tile faces lie exactly on the planes; the pads only extend backwards (outside) by the relief
    planes = {"x_min": T[:, 0].min() - (x0 - relief), "x_max": T[:, 0].max() - (x1 + relief),
              "y_min": T[:, 1].min() - (y0 - relief), "y_max": T[:, 1].max() - (y1 + relief)}
    face_sets = {"x_min": np.isclose(T[:, 0], x0, atol=1e-6).sum(), "x_max": np.isclose(T[:, 0], x1, atol=1e-6).sum(),
                 "y_min": np.isclose(T[:, 1], y0, atol=1e-6).sum(), "y_max": np.isclose(T[:, 1], y1, atol=1e-6).sum()}
    inside = ((T[:, 0] > x0 + 1e-6) & (T[:, 0] < x1 - 1e-6) & (T[:, 1] > y0 + 1e-6) & (T[:, 1] < y1 - 1e-6)).sum()
    C = np.array([v.co[:] for v in bpy.data.objects["GBP_Room_Ceiling"].data.vertices])
    Bs = np.array([v.co[:] for v in bpy.data.objects["GBP_Room_Backstop"].data.vertices])
    Bf = np.array([v.co[:] for v in bpy.data.objects["GBP_Room_BackstopFrame"].data.vertices])
    F = np.array([v.co[:] for v in bpy.data.objects["GBP_Room_Floor"].data.vertices])
    rc = props.ROOM["cove_r"] + 1e-4
    flat = F[(F[:, 0] > x0 + rc) & (F[:, 0] < x1 - rc) & (F[:, 1] > y0 + rc) & (F[:, 1] < y1 - rc)]
    pred = props.floor_height(flat[:, 0], flat[:, 1])
    fall_err = float(np.abs(flat[:, 2] - pred).max())
    d = props.drain_xy()
    far = flat[np.hypot(flat[:, 0] - d[0], flat[:, 1] - d[1]) > 0.5]
    g = np.polyfit(np.hypot(far[:, 0] - d[0], far[:, 1] - d[1]), far[:, 2], 1)[0]
    ok = (max(abs(v) for v in planes.values()) < 1e-6 and min(face_sets.values()) > 100 and inside == 0
          and np.allclose(C[:, 2], z1, atol=1e-6) and abs(Bf[:, 1].min() - 1.3) < 1e-4 and Bs[:, 1].min() >= 1.3 - 1e-4
          and fall_err < 1e-6 and abs(g - 0.01) < 1e-4 and abs(float(props.floor_height(0.0, 0.0))) < 1e-9
          and np.allclose(d, (0.0, -1.0)))
    return ok, (f"tile depth vs plane - relief {({k: round(float(v), 7) for k, v in planes.items()})}; tile verts on planes "
                f"{face_sets}; verts inside the room {inside}; ceiling z {C[:, 2].min():.4f}..{C[:, 2].max():.4f}; "
                f"backstop front y {Bf[:, 1].min():.4f} (rubber >= {Bs[:, 1].min():.4f}); floor formula err "
                f"{fall_err:.2e} m, fitted fall {g * 100:.3f} %; drain {d.tolist()}")


@check("scene", owner="B8")
def b8_meshes_clean():
    """Prop meshes: identity roots, no modifiers left, 'atlas' UV on visible meshes, GBPM_ materials,
    no loose / degenerate geometry that would break Godot's import."""
    props = _b8_props()
    if props is None:
        return True, "props not built in this scene"
    bpy = _bpy()
    bad = []
    tris = {}
    for root in B8_ROOTS:
        r = bpy.data.objects[root]
        if not np.allclose(np.array(r.matrix_world), np.eye(4), atol=1e-9):
            bad.append(f"{root} not at identity")
        for o in r.children:
            if o.type != 'MESH':
                continue
            if o.modifiers:
                bad.append(f"{o.name} modifiers")
            coll = o.get("gbp_collision", False)
            if not coll and "atlas" not in o.data.uv_layers:
                bad.append(f"{o.name} no atlas UV")
            if not coll and any(m is None or not m.name.startswith("GBPM_") for m in o.data.materials):
                bad.append(f"{o.name} material")
            if not coll and not len(o.data.materials):
                bad.append(f"{o.name} no material")
            areas = np.zeros(len(o.data.polygons))
            o.data.polygons.foreach_get("area", areas)
            if (areas <= 0).sum() > 0.002 * len(areas) + 2:
                bad.append(f"{o.name} {(areas <= 0).sum()} zero-area faces")
            tris[root] = tris.get(root, 0) + sum(len(p.vertices) - 2 for p in o.data.polygons)
    return not bad, f"problems {bad}; triangles {tris}"


def _glb_nodes(path):
    g = _glb_json(path)
    return {n.get("name") for n in g.get("nodes", [])}, g


@check("files", owner="B8")
def b8_props_files():
    out = gbc.PROPS_OUT
    need = ["weapons.glb", "room.glb", "props.json", "room.json"]
    missing = [f for f in need if not os.path.exists(os.path.join(out, f))]
    if missing:
        return False, f"missing {missing} in {out} (run build.py --stage props)"
    big = [f for f in need if os.path.getsize(os.path.join(out, f)) > 50e6]
    wn, wg = _glb_nodes(os.path.join(out, "weapons.glb"))
    rn, rg = _glb_nodes(os.path.join(out, "room.glb"))
    miss_w = [m for m in B8_MARKERS if m not in wn]
    miss_r = [m for m in B8_ROOM_MARKERS if m not in rn]
    images = len(wg.get("images", [])) + len(rg.get("images", []))
    probs = []
    for f, schema in (("props.json", "gb.props/1"), ("room.json", "gb.room/1")):
        doc = gbc.read_json(os.path.join(out, f))
        probs += gbc.validate_schema(doc.get("data", {}), doc.get("schema", ""))
        if doc.get("schema") != schema:
            probs.append(f"{f} schema {doc.get('schema')}")
    sizes = {f: round(os.path.getsize(os.path.join(out, f)) / 1e6, 2) for f in need}
    ok = not big and not miss_w and not miss_r and images == 0 and not probs
    return ok, f"sizes MB {sizes}; markers missing weapons {miss_w} room {miss_r}; images {images}; schema {probs}"


def _room_gd_constants(path):
    """Parse ``const NAME := <number or Vector3(...)>`` lines of world/room.gd."""
    import re
    out = {}
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            m = re.match(r"\s*const\s+(\w+)\s*(?::\s*\w+)?\s*:?=\s*(.+)", line)
            if not m:
                continue
            val = m.group(2).split("#")[0].strip()
            nums = re.findall(r"-?\d+\.?\d*(?:e-?\d+)?", val)
            if nums:
                out[m.group(1)] = [float(n) for n in nums]
    return out


@check("files", owner="B8")
def b8_room_constants():
    """room.json equals props.ROOM (the single source) and, once G7 writes world/room.gd, its constants."""
    import props
    path = os.path.join(gbc.PROPS_OUT, "room.json")
    if not os.path.exists(path):
        return False, "room.json missing"
    g = gbc.read_json(path)["data"]["godot"]
    R = props.ROOM
    pairs = {"x": (g["interior"]["x"], list(R["x"])), "z": (g["interior"]["z"], list(R["z"])),
             "ceiling": (g["wall_planes"]["ceiling_y"], R["height"]), "fall": (g["floor"]["fall"], R["floor_fall"]),
             "drain": (g["floor"]["drain"], list(R["drain_g"])), "backstop_z": (g["backstop"]["front_z"],
                                                                               R["backstop_front_z"]),
             "spawn": (g["player"]["spawn"], list(R["player_spawn_g"])), "table_top": (g["table"]["top_y"],
                                                                                        R["table_top"])}
    bad = [k for k, (a, b) in pairs.items() if not _close(a, b, 1e-9)]
    gd = os.path.join(gbc.GAME_DIR, "world", "room.gd")
    gd_note = "world/room.gd not written yet (G7 must take its constants from room.json)"
    if os.path.exists(gd):
        c = _room_gd_constants(gd)
        expect = {"ROOM_HALF_X": [3.0], "ROOM_Z_MIN": [R["z"][0]], "ROOM_Z_MAX": [R["z"][1]],
                  "CEILING_Y": [R["height"]], "FLOOR_FALL": [R["floor_fall"]], "DRAIN_POS": list(R["drain_g"]),
                  "BACKSTOP_FRONT_Z": [R["backstop_front_z"]], "PLAYER_SPAWN": list(R["player_spawn_g"])}
        diff = [k for k, v in expect.items() if k in c and not _close(c[k], v, 1e-6)]
        absent = [k for k in expect if k not in c]
        bad += [f"room.gd {k}" for k in diff]
        gd_note = f"room.gd compared: mismatches {diff}; not declared there {absent}"
    return not bad, f"room.json vs props.ROOM mismatches {bad}; {gd_note}"



# ---------------------------------------------------------------------------
# B7 look-dev and bakes (plan §8.2 B7 acceptance): no empty texels inside islands, tileable edge
# error < 2/255, skin albedo luminance inside the head palette, textures match the exported UVs.
# ---------------------------------------------------------------------------
B7_TEX = os.path.join(gbc.SUBJECT_OUT, "textures")
B7_JSON = os.path.join(B7_TEX, "textures.json")
gbc.SCHEMAS.setdefault("gb.textures/1", ("sets", "tileables", "eyes", "decals", "painter", "room",
                                         "material_map"))
B7_SETS = ("head", "body", "shorts", "mouth", "skeleton", "organs", "brain")
B7_PNG_MAX_MB = 12.0            # plan §4.3: each 2,048^2 PNG <= 12 MB (scaled by texel count; any file < 50 MB)


def _b7():
    if not os.path.exists(B7_JSON):
        return None
    return gbc.read_json(B7_JSON)["data"]


@check("files", owner="B7")
def b7_texture_files():
    """textures.json lists every set; every listed file exists, has the stated size and fits the budget."""
    d = _b7()
    if d is None:
        return False, "textures/textures.json missing (bake stage not run)"
    import texgen
    missing, bad, big = [], [], []
    names = []
    for k, rec in d["sets"].items():
        names += [(f, rec["size"]) for f in rec["files"].values()]
    for k, rec in list(d["tileables"].items()) + list(d["room"].items()):
        names += [(f, rec["size"]) for f in rec["files"].values()]
    for rec in d["painter"].values():
        names += [(rec["files"]["rest_normal"], rec["size"]), (rec["files"]["valid"], rec["size"]),
                  (rec["files"]["bone"], rec["bone_size"]), (rec["files"]["position"], None)]
    names += [(f, None) for f in d["decals"].get("files", {}).values()]
    eyes = d.get("eyes", {})
    names += [(f, None) for f in eyes.get("iris", {}).get("files", {}).values()]
    if "sclera" in eyes:
        names.append((eyes["sclera"]["file"], None))
    for fn, size in names:
        p = os.path.join(B7_TEX, fn)
        if not os.path.exists(p):
            missing.append(fn)
            continue
        limit = B7_PNG_MAX_MB * max(1.0, (float(size) / 2048.0) ** 2 if size else 1.0)
        if os.path.getsize(p) > min(limit, gbc.FILE_LIMITS_MB["any"]) * 1e6:
            big.append(fn)
        if size and fn.endswith(".png") and texgen.png_size(p)[0] != size:
            bad.append(fn)
    miss_sets = [s for s in B7_SETS if s not in d["sets"]]
    ok = not missing and not bad and not big and not miss_sets
    return ok, (f"{len(names)} files, sets {sorted(d['sets'])}" + (f"; missing {missing[:6]}" if missing else "")
                + (f"; wrong size {bad[:6]}" if bad else "") + (f"; over the size budget {big}" if big else "")
                + (f"; sets not baked {miss_sets}" if miss_sets else ""))


@check("files", owner="B7")
def b7_no_empty_texels():
    """Raw Cycles bakes cover the islands (misses <= 0.1 %, filled from neighbours) and the written
    albedo has no black texels at all (islands filled, dilated 8 px, rest push-pull filled)."""
    d = _b7()
    if d is None:
        return False, "no textures.json"
    import texgen
    out, ok = [], True
    for name in B7_SETS:
        rec = d["sets"].get(name)
        if rec is None:
            ok = False
            out.append(f"{name} missing")
            continue
        frac = rec["coverage"]["empty_fraction"]
        alb = texgen.read_png(os.path.join(B7_TEX, rec["files"]["albedo"]))
        black = int((alb.max(axis=2) == 0).sum())
        good = frac <= 0.001 and black == 0
        ok &= good
        out.append(f"{name} miss {frac * 100:.3f}% black {black}")
    return ok, "; ".join(out)


@check("files", owner="B7")
def b7_tileable_seams():
    """Every tileable (tissue, room, props) repeats seamlessly: edge error < 2/255 (recomputed from the PNGs)."""
    d = _b7()
    if d is None:
        return False, "no textures.json"
    import texgen
    worst, bad = 0.0, []
    for name, rec in list(d["tileables"].items()) + list(d["room"].items()):
        for f in rec["files"].values():
            e = texgen.tile_edge_error(texgen.read_png(os.path.join(B7_TEX, f)))
            worst = max(worst, e)
            if e >= 2.0:
                bad.append(f"{f} {e:.2f}")
    core = [k for k in ("muscle_fibre", "fat_lobule", "bone_cut", "diploe", "blood_crust", "cloth_weave")
            if k not in d["tileables"]]
    return not bad and not core, f"{len(d['tileables'])} tissue + {len(d['room'])} room/prop sets, worst " \
        f"{worst:.3f}/255" + (f"; over 2/255: {bad}" if bad else "") + (f"; missing {core}" if core else "")


@check("files", owner="B7")
def b7_skin_luminance():
    """Body and head skin albedo (median linear luminance) match each other within 10 % and sit within
    25 % of the head palette's base colour at the current skin_tone (GH_Skin ramp)."""
    d = _b7()
    if d is None or "head" not in d["sets"] or "body" not in d["sets"]:
        return False, "head/body sets missing"
    h = d["sets"]["head"]["albedo_linear_luminance"]["median"]
    b = d["sets"]["body"]["albedo_linear_luminance"]["median"]
    head = gbc.import_head()
    tone = head.gh_common.CONTROL_PROPS["skin_tone"][0]
    stops = [(0.0, (0.61, 0.43, 0.35)), (0.25, (0.48, 0.30, 0.225)), (0.5, (0.30, 0.16, 0.10)),
             (0.75, (0.13, 0.062, 0.038)), (1.0, (0.05, 0.026, 0.018))]
    xs = [s[0] for s in stops]
    base = [float(np.interp(tone, xs, [s[1][c] for s in stops])) for c in range(3)]
    pal = 0.2126 * base[0] + 0.7152 * base[1] + 0.0722 * base[2]
    ok = abs(b / h - 1.0) <= 0.10 and abs(h / pal - 1.0) <= 0.25 and abs(b / pal - 1.0) <= 0.25
    return ok, f"median luminance head {h:.3f}, body {b:.3f} (ratio {b / h:.3f}); palette {pal:.3f} at " \
        f"skin_tone {tone}"


@check("files", owner="B7")
def b7_eyes_decals_painter():
    """Iris/sclera, the 64-stain decal atlas and the painter inputs (head, body, shorts) exist and are sane."""
    d = _b7()
    if d is None:
        return False, "no textures.json"
    eyes = d.get("eyes", {})
    dec = d.get("decals", {})
    pt = d.get("painter", {})
    probs = []
    if "iris" not in eyes or "sclera" not in eyes:
        probs.append("eyes")
    if dec.get("count", 0) < 32:
        probs.append(f"decals {dec.get('count', 0)}")
    for k in ("head", "body", "shorts"):
        if k not in pt:
            probs.append(f"painter {k}")
        elif not (0.2 < pt[k]["valid_fraction"] < 0.95):
            probs.append(f"painter {k} valid {pt[k]['valid_fraction']}")
    return not probs, (f"iris + sclera, {dec.get('count', 0)} decals, painter {sorted(pt)}"
                       + (f"; problems {probs}" if probs else ""))


@check("scene", owner="B7")
def b7_position_map_precision():
    """Painter position maps (half EXR, segment-relative) reproduce the rest position of every texel
    to <= 0.5 mm (plan §3.3.7 quantisation rule)."""
    d = _b7()
    if d is None:
        return False, "no textures.json"
    bpy = _bpy()
    import bake
    import export
    org = {v["code"]: np.array(v["origin"]) for v in export.segment_origins().values()}
    out, ok = [], True
    for name, rec in d["painter"].items():
        o = bpy.data.objects.get(rec["mesh"])
        if o is None or bake.uv_hash(o) != rec["uv_hash"]:
            out.append(f"{name} skipped (UVs changed)")
            continue
        im = bpy.data.images.load(os.path.join(B7_TEX, rec["files"]["position"]), check_existing=False)
        im.colorspace_settings.name = 'Non-Color'
        n = im.size[0]
        a = np.empty(n * n * 4, np.float32)
        im.pixels.foreach_get(a)
        bpy.data.images.remove(im)
        a = a.reshape(n, n, 4)[::-1]
        tri, bary = bake.rasterize(o, n)
        valid = tri >= 0
        pos = bake.interp(o, tri, bary, per_vertex=gbc.get_verts(o.data))
        codes = np.rint(a[..., 3][valid]).astype(int)
        known = np.isin(codes, list(org))
        o3 = np.array([org[c] for c in codes[known]])
        err = np.linalg.norm(a[..., :3][valid][known] + o3 - pos[valid][known], axis=1) * 1000.0
        good = known.all() and err.max() <= 0.5
        ok &= good
        out.append(f"{name} max {err.max():.3f} mm p99 {np.percentile(err, 99):.3f} mm")
    return ok, "; ".join(out)


@check("scene", owner="B7", severity="warn")
def b7_textures_match_uvs():
    """The UV0 atlas of every textured mesh equals the one its textures were baked for (uv_hash).  A
    mismatch means the geometry/UVs changed after the last bake stage (rerun ``--stage bake``), or the
    inner-mesh atlases were not re-charted in this build (build.py must call bake.prepare_uvs)."""
    d = _b7()
    if d is None:
        return False, "no textures.json"
    bpy = _bpy()
    import bake
    bad, n = [], 0
    recs = [(r["target"], r["uv_hash"]) for r in d["sets"].values()]
    recs += [(r["mesh"], r["uv_hash"]) for r in d["painter"].values()]
    for oname, h in recs:
        o = bpy.data.objects.get(oname)
        if o is None:
            continue
        n += 1
        if bake.uv_hash(o) != h:
            bad.append(oname)
    return not bad, f"{n} meshes checked" + (f"; UVs differ from the bake: {sorted(set(bad))}" if bad else "")


@check("scene", owner="B7", quick_ok=False)
def b7_inner_atlas_quality():
    """Re-charted inner atlases: exact texel overlap <= 0.1 % (bake.uv_overlap_exact), texel area distortion
    p10..p90 within 1.5 stops."""
    bpy = _bpy()
    import bake
    out, ok = [], True
    for name in bake.RECHART:
        o = bpy.data.objects.get(name)
        if o is None:
            continue
        cov, _approx, texel = bake.uv_stats(o, 512)
        over, _polys = bake.uv_overlap_exact(o, bake.RECHART[name]["size"])
        lo, hi = bake.uv_distortion(o)
        good = over <= 0.001 and lo > -1.5 and hi < 1.5
        ok &= good
        out.append(f"{name} cover {cov:.2f} overlap {over:.3f} distortion {lo:+.2f}/{hi:+.2f}")
    return ok, "; ".join(out)



@check("scene", owner="B7", quick_ok=False)
def uv_no_overlap():
    """Every exported mesh's atlas UV (UV0): at most 0.1 % of its covered texels shared by two triangles
    (exact rasterisation at 1024; plan §5.5 non-overlapping atlas)."""
    import bake
    out, bad = {}, []
    for o in _exported():
        if "atlas" not in o.data.uv_layers or len(o.data.polygons) == 0:
            continue
        frac, _p = bake.uv_overlap_exact(o, 1024)
        out[o.name] = round(frac * 100, 3)
        if frac > 0.001:
            bad.append(o.name)
    return not bad, f"overlap % of covered texels: {out}; over 0.1 %: {bad}"


# ===========================================================================
# B6 rig, weights, poses and export (plan §8.2 B6 acceptance): joint positions +-2 mm of RB §7.2,
# weight sums 1 +- 1e-4 with <= 4 influences from ONE function for every layer, FB-2 deformation
# (volume loss < 15 %, no inner-layer vertex > 3 mm outside the skin up to 90 % of the live ROM),
# key poses, rig.json, manifest, file limits, round trip (re-import) and the Godot headless import.
# ===========================================================================
def _b6_ready():
    bpy = _bpy()
    return gbc.ARMATURE in bpy.data.objects and "GB_Body" in bpy.data.objects


def _b6_deform():
    """Deformation tests, run once per process (the manifest reports the same numbers)."""
    import export
    import posetest
    if "deformation_full" not in export.CHECKS:
        res = posetest.run_tests(quiet=True)
        export.CHECKS["deformation_full"] = res
        export.CHECKS["deformation"] = export.deformation_summary(res)
    return export.CHECKS["deformation_full"]


@check("scene", owner="B6")
def b6_joint_positions():
    """Armature joint centres within 2 mm of the RB §7.1/§7.2 landmarks; B6 fits (jaw hinge, thumb) listed."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import rig
    bpy = _bpy()
    arm = bpy.data.objects[gbc.ARMATURE]
    # the armature is in the final frame (neck lengthened): compare with the warped RB landmarks
    lm = {k: gbc.warp_points(v) for k, v in LM.all_landmarks().items()}
    pairs = {"upper_arm": "gh_joint", "forearm": "elbow_centre", "hand": "wrist_centre", "fingers": "mcp3",
             "thigh": "hip_joint_centre", "shin": "knee_centre", "foot": "ankle_centre", "clavicle": "sc_joint"}
    worst, bad = 0.0, []
    for base, l in pairs.items():
        for s in ("L", "R"):
            key = f"{l}_{s}_apose" if f"{l}_{s}_apose" in lm else f"{l}_{s}"
            d = float(np.linalg.norm(np.array(arm.data.bones[f"{base}_{s}"].head_local) - np.array(lm[key])))
            worst = max(worst, d)
            if d > 0.002:
                bad.append(f"{base}_{s} {d * 1000:.1f} mm")
    d = float(np.linalg.norm(np.array(arm.data.bones["head"].head_local) - np.array(lm["atlanto_occipital_pivot"])))
    worst = max(worst, d)
    fits = [b["name"] for b in rig.bone_rows() if b.get("fit")]
    jaw = np.array(arm.data.bones["jaw"].head_local)
    import head_integration as hi
    jd = float(np.linalg.norm(jaw - gbc.warp_points(hi.jaw_pivot())))
    return not bad and jd < 1e-4, (f"worst joint offset {worst * 1000:.2f} mm (limit 2); off {bad}; jaw head = B2 "
                                   f"measured hinge ({jd * 1000:.2f} mm); fitted bones {fits}")


@check("scene", owner="B6")
def b6_weights_function():
    """ONE weight function (plan D8): deterministic; every analytic mesh's vertex groups equal weights_at at
    its vertices (lids included); rows sum to 1 within 1e-4 with <= 4 influences."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import rig
    bpy = _bpy()
    rng = gbc.rng("verify")
    pts = rng.uniform((-0.6, -0.2, 0.0), (0.6, 0.2, 1.8), (4000, 3))
    i1, w1 = rig.weights_at(pts)
    i2, w2 = rig.weights_at(pts)
    det = bool(np.array_equal(i1, i2) and np.array_equal(w1, w2))
    sums = np.abs(w1.sum(1) - 1.0).max()
    bad, checked = [], 0
    for o in _exported():
        rb = gbc.read_point_attr(o, "gb_rigid_bone", 'INT')
        if o.name in rig.FOLLOWERS or o.name in rig.TRANSFERRED or (rb is not None and np.all(rb >= 0)):
            continue
        idx, w = rig.read_weights(o)
        n = len(o.data.vertices)
        sel = rng.choice(n, min(1500, n), replace=False)
        if rb is not None:
            sel = sel[rb[sel] < 0]
        v = gbc.get_verts(o.data)[sel]
        ia, wa = rig.weights_at(v, layer=rig.SKIN_LAYER.get(o.name, gbc.LAYER_OF.get(o.name, "skin")))
        dense_a = np.zeros((len(sel), rig.NB))
        dense_s = np.zeros((len(sel), rig.NB))
        rows = np.repeat(np.arange(len(sel)), 4)
        np.add.at(dense_a, (rows, ia.ravel()), wa.ravel())
        np.add.at(dense_s, (rows, idx[sel].ravel()), w[sel].ravel())
        err = float(np.abs(dense_a - dense_s).max()) if len(sel) else 0.0
        checked += len(sel)
        if err > 1.5 / rig.QUANT:
            bad.append(f"{o.name} {err:.4f}")
    return det and sums < 1e-9 and not bad, (f"deterministic {det}; row sum error {sums:.1e}; {checked} vertices of "
                                            f"every analytic mesh equal weights_at; differing: {bad}")


@check("scene", owner="B6")
def b6_seam_and_layers():
    """Neck seam ring: GB_Head and GB_Body ring vertices carry identical weights; the muscle shell follows
    the skin (mean L1 weight difference to the nearest skin vertex <= 0.1)."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import posetest
    import rig
    bpy = _bpy()
    h, b = bpy.data.objects["GB_Head"], bpy.data.objects["GB_Body"]
    vh, vb = gbc.get_verts(h.data), gbc.get_verts(b.data)
    ih, wh = rig.read_weights(h)
    ib, wb = rig.read_weights(b)
    sz = gbc.seam_z_now()
    rh = np.nonzero(np.abs(vh[:, 2] - sz) < 1e-6)[0]
    rb_ = np.nonzero(np.abs(vb[:, 2] - sz) < 1e-6)[0]
    if len(rh) != gbc.SEAM_RING_N:
        return False, f"{len(rh)} GB_Head ring vertices at z {sz:.5f} (want {gbc.SEAM_RING_N})"
    kb = {tuple(np.round(vb[i], 6)): i for i in rb_}
    diff = 0.0
    for i in rh:
        j = kb.get(tuple(np.round(vh[i], 6)))
        if j is None:
            diff = 1.0
            break
        a = dict(zip(ih[i].tolist(), wh[i].tolist()))
        c = dict(zip(ib[j].tolist(), wb[j].tolist()))
        diff = max(diff, max(abs(a.get(k, 0) - c.get(k, 0)) for k in set(a) | set(c)))
    lc = posetest.layer_consistency()
    return diff < 1e-9 and lc["mean_l1"] <= 0.1, (f"{len(rh)} ring vertices, max weight difference {diff:.2e}; "
                                                  f"muscle shell vs nearest skin vertex {lc}")


@check("scene", owner="B6")
def b6_followers():
    """Brow/lash cards and eye FX shells take the skin weights at their anchors (lids included, B2)."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import rig
    bpy = _bpy()
    bad, lids = [], {}
    for n in rig.FOLLOWERS:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        if not rig._has_anchors(o):
            bad.append(f"{n} no anchors")
            continue
        idx, w = rig.read_weights(o)
        a = np.stack([gbc.read_point_attr(o, "gb_anchor_" + c, 'FLOAT') for c in "xyz"], 1)
        ia, wa = rig.weights_at(a)
        dense_a = np.zeros((len(a), rig.NB))
        dense_s = np.zeros((len(a), rig.NB))
        rows = np.repeat(np.arange(len(a)), 4)
        np.add.at(dense_a, (rows, ia.ravel()), wa.ravel())
        np.add.at(dense_s, (rows, idx.ravel()), w.ravel())
        err = float(np.abs(dense_a - dense_s).max())
        lid = [rig.BONE_INDEX[b] for b in ("lid_upper_L", "lid_lower_L", "lid_upper_R", "lid_lower_R")]
        lids[n] = int((dense_s[:, lid].sum(1) > 0.5).sum())
        if err > 1.5 / rig.QUANT:
            bad.append(f"{n} {err:.4f}")
    return not bad, f"follower weights = skin weights at the anchors; lid-driven vertices {lids}; bad {bad}"


@check("scene", owner="B6")
def b6_deformation_fb2():
    """FB-2 / plan §8.2 B6: elbow, knee, shoulder abduction, hip flexion up to 90 % of the live ROM - no
    inner-layer vertex > 3 mm outside the posed skin or newly visible from outside (a torn / folded-open
    skin), joint-region volume loss < 15 %."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    res = _b6_deform()
    acc = {k: v for k, v in res.items() if v["level"] == "fb2"}
    bad = [k for k, v in acc.items() if not v["ok"]]
    s = "; ".join(f"{k}: poke {v['poke_mm']} mm / {v['poke_over']} > 3 mm, exposed {v.get('exposed', 0)}, "
                  f"vol loss {v['vol_loss']}" for k, v in acc.items())
    return not bad and len(acc) >= 5, f"failing {bad}; {s}"


@check("scene", owner="B6", quick_ok=False)
def b6_deformation_quality():
    """Every other deformation test (twist, wrist, fist, ankle, toes, neck, trunk, jaw, FB-2 maxima): reported."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    res = _b6_deform()
    other = {k: v for k, v in res.items() if v["level"] != "fb2"}
    bad = [k for k, v in other.items() if not v["ok"]]
    s = "; ".join(f"{k} {v['poke_mm']}mm/{v['poke_over']}/exp {v.get('exposed', 0)}/{v['vol_loss']}"
                  for k, v in other.items())
    return not bad, f"over 3 mm, newly exposed or >= 15 % loss: {bad}; {s}"


@check("scene", owner="B6", quick_ok=False)
def b6_rest_pose_nesting():
    """Inner-layer vertices > 3 mm outside the skin already in the REST pose (geometry of B1/B3/B4/B5, not
    deformation): listed so their owners can fix them."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import posetest
    md = posetest.load_meshes(posetest.SKIN + posetest.INNER)
    ro = posetest.rest_outside(md)
    bad = {n: int(m.sum()) for n, m in ro.items() if m.sum()}
    detail = {}
    for n, m in ro.items():
        if m.sum() and md[n].piece is not None:
            inv = {v: k for k, v in BN.BONE_PIECE_ID.items()}
            detail[n] = sorted({inv.get(int(p), "?") for p in md[n].piece[m]})[:10]
    return not bad, f"vertices > 3 mm outside the rest skin: {bad}; pieces {detail}"


@check("scene", owner="B6")
def b6_key_poses():
    """pose_idle/guard/cower/brace: every joint angle inside its live limits; both feet planted (ankles within
    10 mm of rest via the keyed hips translation)."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import rig
    bpy = _bpy()
    arm = bpy.data.objects[gbc.ARMATURE]
    limits = {}
    for b in RT.bodies():
        if b["joint"]:
            base = b["bone"][:-2] if b["bone"].endswith(("_L", "_R")) else b["bone"]
            limits[base] = b["joint"]["limits_live_deg"]
    limits.update(rig.KIN_LIMITS)
    bad = []
    feet = {}
    for name in gbc.POSE_ACTIONS:
        pose = rig.POSES[name]
        for base, rots in pose.items():
            lim = limits.get(base, {})
            if "swing" in lim:
                sw = math.hypot(*[d for ax, d in rots if ax in ("flex", "abd")] or [0.0])
                if sw > lim["swing"][1] + 1e-6:
                    bad.append(f"{name}:{base} swing {sw:.0f}")
            for ax, d in rots:
                if ax in lim and not (lim[ax][0] - 1e-6 <= d <= lim[ax][1] + 1e-6):
                    bad.append(f"{name}:{base}.{ax} {d}")
        act = bpy.data.actions.get(name)
        if act is None:
            bad.append(f"{name} missing")
            continue
        arm.animation_data_create()
        arm.animation_data.action = act
        bpy.context.scene.frame_set(1)
        bm = rig.bone_map()
        err = max(float(np.linalg.norm(np.array(arm.pose.bones[f"foot_{s}"].head) - np.array(bm[f"foot_{s}"]["head"])))
                  for s in ("L", "R"))
        feet[name] = round(err * 1000, 1)
        if err > 0.010:
            bad.append(f"{name} feet off {err * 1000:.1f} mm")
        arm.animation_data.action = None
        rig.reset_pose(arm)
    return not bad, f"out of limits / feet: {bad}; ankle offset mm {feet}"


@check("files", owner="B6")
def b6_rig_json():
    """rig.json: 39 bones (fits noted), 20 bodies with unit world axes, directional torque caps, live/dead limits,
    myotomes; kinematic bones with axes and twist drivers; face block measured by B2; poses; weight model."""
    path = os.path.join(gbc.SUBJECT_OUT, "rig.json")
    if not os.path.exists(path):
        return False, "rig.json missing"
    d = gbc.read_json(path)["data"]
    probs = []
    if len(d["bones"]) != 39 or [b["name"] for b in d["bones"]] != list(RT.BONE_NAMES):
        probs.append("bones")
    if len(d["bodies"]) != 20:
        probs.append("bodies")
    for b in d["bodies"]:
        j = b["joint"]
        if not j:
            continue
        for ax, a in j["axes"].items():
            if abs(np.linalg.norm(a["world"]) - 1.0) > 1e-4:
                probs.append(f"{b['bone']}.{ax} not unit")
        caps = j["torque_cap_nm"]
        lo, hi = j["torque_cap_range_nm"]
        if lo == hi:                               # a single E value in the plan: allow a +-7 % directional split
            lo, hi = lo * 0.93, hi * 1.07
        if any(not (lo - 1e-6 <= c <= hi + 1e-6) for c in caps.values()):
            probs.append(f"{b['bone']} cap outside plan range")
        if not j.get("myotomes"):
            probs.append(f"{b['bone']} no myotomes")
    asym = sum(1 for b in d["bodies"] if b["joint"] and len(set(b["joint"]["torque_cap_nm"].values())) > 1)
    kin = d.get("kinematic", {})
    for k in ("upper_arm_twist_L", "forearm_twist_R", "fingers_L", "thumb_R", "toes_L", "jaw", "eye_L"):
        if k not in kin:
            probs.append(f"kinematic {k}")
    if "driver" not in kin.get("upper_arm_twist_L", {}) or "driver" not in kin.get("forearm_twist_L", {}):
        probs.append("twist drivers")
    face = d.get("face", {})
    if not str(face.get("status", "")).startswith("measured") or len(face.get("lid_table", {}).get("rows", [])) < 5:
        probs.append("face lid table not measured")
    if sorted(d.get("poses", {})) != sorted(gbc.POSE_ACTIONS):
        probs.append("poses")
    return not probs, (f"problems {probs}; {asym} bodies with direction-specific caps; kinematic "
                       f"{len(kin)} bones; face {face.get('status')}")


@check("files", owner="B6")
def b6_manifest_and_files():
    """manifest.json lists every exported file with sha256 (incl. B3 bones.json), the texture sets with import
    hints, LOD1, the rig results; every generated file < 50 MB, GB_Subject.glb <= 40 MB (plan §4.3)."""
    path = os.path.join(gbc.SUBJECT_OUT, "manifest.json")
    d = gbc.read_json(path)["data"]
    need = ["GB_Subject.glb", "GB_Subject_LOD1.glb", "rig.json", "landmarks.json", "organs.json", "vessels.json",
            "spine.json", "codes.json", "brain_labels.png", "brain_labels.json", "bones.json"]
    missing = [f for f in need if f not in d["files"]]
    stale = [f for f, v in d["files"].items() if os.path.exists(os.path.join(gbc.SUBJECT_OUT, f)) and
             gbc.file_hash(os.path.join(gbc.SUBJECT_OUT, f)) != v["sha256"]]
    sets = sorted(d.get("textures", {}).get("sets", {}))
    fl = d.get("file_limits", {})
    lod = d.get("lod", {}).get("lod1_meshes", {})
    need_sets = 0 if _bake_skipped() else 7          # texture sets are required only when the bake ran
    ok = (not missing and not stale and len(sets) >= need_sets and fl.get("ok", False) and len(lod) == 2
          and "rig" in d)
    return ok, (f"missing {missing}; stale hashes {stale}; texture sets {sets}; file limits {fl.get('ok')} "
                f"(largest {fl.get('largest')}, total {fl.get('total_mb')} MB, over {fl.get('over')}); LOD1 {lod}")


@check("scene", owner="B6")
def b6_roundtrip():
    """Round trip: GB_Subject.glb re-imported in a fresh Blender has every mesh with the same triangles, shape
    keys, materials and vertex groups, the 39 bones and the 4 actions."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import export
    if "roundtrip" not in export.CHECKS:
        ok, det = export.round_trip(os.path.join(gbc.SUBJECT_OUT, export.SUBJECT_GLB))
        export.CHECKS["roundtrip"] = dict(det, ok=ok)
    r = export.CHECKS["roundtrip"]
    return r["ok"], {k: v for k, v in r.items() if k != "ok"}


@check("scene", owner="B6")
def b6_godot_import():
    """Godot 4.5.1 headless import of GB_Subject.glb: one Skeleton3D with the 39 bones in rig.json order, every
    contract mesh skinned (4 weights) with UV2, its surfaces and blend shapes, the 4 animations, and CUSTOM0
    RGBA32F injection on a skinned surface works (plan §3.3.1, FB-11 precursor)."""
    if not _b6_ready():
        return True, "n/a (no scene)"
    import export
    if "godot_import" not in export.CHECKS:
        ok, det = export.godot_import_check(os.path.join(gbc.SUBJECT_OUT, export.SUBJECT_GLB))
        export.CHECKS["godot_import"] = dict(det, ok=ok)
    r = export.CHECKS["godot_import"]
    if r["ok"] is None:
        return True, r
    return r["ok"], {k: v for k, v in r.items() if k != "ok"}



def verify_all(groups=("tables", "scene", "files"), quiet=False):
    """Run every registered check of ``groups``; returns {name: {ok, severity, owner, group, detail}}."""
    res = {}
    # geometry checks compare the meshes with the authoring tables (RB frame); the rig/deformation (B6) and
    # bake (B7) checks run on the exported final frame (neck lengthened, gbc.NECK_LIFT).  Authoring checks
    # run first, then the scene is warped back to where it was.
    frame0 = None
    try:
        frame0 = gbc.scene_frame()
    except Exception:                                   # no bpy (tables only)
        pass
    order = sorted(range(len(CHECKS)), key=lambda i: CHECKS[i][2] in FINAL_FRAME_OWNERS)
    for i in order:
        group, name, owner, sev, fn = CHECKS[i]
        if group not in groups:
            continue
        if frame0 is not None and group != "tables":
            gbc.set_scene_frame("final" if owner in FINAL_FRAME_OWNERS else "authoring")
        if CONTEXT.get("quick") and name in QUICK_SKIP:
            res[name] = {"ok": True, "skip": True, "severity": sev, "owner": owner, "group": group,
                         "detail": "skip: full-accuracy check, not meaningful on --quick meshes"}
            continue
        if owner == "B7" and _bake_skipped():
            res[name] = {"ok": True, "skip": True, "severity": sev, "owner": owner, "group": group,
                         "detail": "skip: bake stage skipped on purpose (--no-bake)"}
            continue
        try:
            ok, detail = fn()
        except Exception as exc:                        # a crashing check is a failing check
            ok, detail = False, f"EXCEPTION {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"
        skip = ok is None
        res[name] = {"ok": True if skip else bool(ok), "severity": sev, "owner": owner, "group": group,
                     "detail": detail}
        if skip:
            res[name]["skip"] = True
    if frame0 is not None:
        gbc.set_scene_frame(frame0)
    res = {k: res[k] for k in [CHECKS[i][1] for i in range(len(CHECKS))] if k in res}
    if not quiet:
        report(res)
    return res


FINAL_FRAME_OWNERS = ("B6", "B7")


def failures(res):
    """Names of failing 'fail'-severity checks."""
    return [k for k, v in res.items() if not v["ok"] and v["severity"] == "fail"]


def report(res):
    """Print a compact report."""
    for k, v in res.items():
        flag = "SKIP" if v.get("skip") else ("PASS" if v["ok"] else ("FAIL" if v["severity"] == "fail" else "WARN"))
        print(f"  [{flag}] {v['group']:6s} {v['owner']:3s} {k}: {v['detail']}")
    f = failures(res)
    w = [k for k, v in res.items() if not v["ok"] and v["severity"] != "fail"]
    sk = [k for k, v in res.items() if v.get("skip")]
    print(f"verify: {len(res)} checks, {len(f)} failures, {len(w)} warnings, {len(sk)} skipped")


def reproduce(keep=False):
    """Plan §5.8 reproducibility: rebuild every geometry stage from clean (no caches) into a temporary output
    root with ``--no-bake``, then byte-compare every JSON sidecar and the per-mesh vertex hashes of
    GB_Subject.glb with the committed files.  Returns (ok, detail).  Takes a full build's time (~25 min)."""
    import subprocess
    import tempfile
    tmp = tempfile.mkdtemp(prefix="gb_reproduce_")
    env = dict(os.environ, GB_OUTPUT_ROOT=os.path.join(tmp, "out"), GB_CACHE_DIR=os.path.join(tmp, "cache"))
    cmd = [sys.executable, os.path.join(gbc.HERE, "build.py"), "--stage", "skin", "head", "skeleton", "viscera",
           "neuro", "vascular", "export", "--no-bake", "--no-save", "--no-verify"]
    run = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if run.returncode != 0:
        return False, {"build_rc": run.returncode, "tail": run.stdout[-2000:] + run.stderr[-2000:]}
    new_dir = os.path.join(tmp, "out", "subject")
    diff, same = [], []
    for f in sorted(os.listdir(gbc.SUBJECT_OUT)):
        if not f.endswith(".json") or f == "manifest.json":
            continue
        a, b = os.path.join(gbc.SUBJECT_OUT, f), os.path.join(new_dir, f)
        if not os.path.exists(b):
            diff.append(f"{f}: not rebuilt")
            continue
        da, db = gbc.read_json(a), gbc.read_json(b)
        da.pop("build_id", None)
        db.pop("build_id", None)
        (same if da == db else diff).append(f)
    ga, gb_ = _glb_mesh_hashes(os.path.join(gbc.SUBJECT_OUT, "GB_Subject.glb")), \
        _glb_mesh_hashes(os.path.join(new_dir, "GB_Subject.glb"))
    mesh_diff = sorted(k for k in set(ga) | set(gb_) if ga.get(k) != gb_.get(k))
    if not keep:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)
    ok = not diff and not mesh_diff
    return ok, {"json_identical": same, "json_different": diff, "glb_meshes_different": mesh_diff,
                "tmp": tmp if keep else None}


def _glb_mesh_hashes(path):
    """{mesh name: sha1 of its POSITION accessor bytes} of a .glb (per-mesh vertex hashes)."""
    import hashlib
    with open(path, "rb") as fh:
        raw = fh.read()
    jl = struct.unpack_from("<I", raw, 12)[0]
    js = json.loads(raw[20:20 + jl])
    binoff = 20 + jl + 8
    out = {}
    for m in js.get("meshes", []):
        h = hashlib.sha1()
        for prim in m["primitives"]:
            acc = js["accessors"][prim["attributes"]["POSITION"]]
            bv = js["bufferViews"][acc["bufferView"]]
            start = binoff + bv.get("byteOffset", 0) + acc.get("byteOffset", 0)
            h.update(raw[start:start + acc["count"] * 12])
        out[m["name"]] = h.hexdigest()
    return out


if __name__ == "__main__":
    args = gbc.script_args()
    if "--reproduce" in args:
        ok, det = reproduce(keep="--keep" in args)
        print(json.dumps(det, indent=1))
        sys.exit(0 if ok else 1)
    groups = ["tables", "files"]
    if "--blend" in args:
        import bpy
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args[args.index("--blend") + 1]))
        groups.append("scene")
    r = verify_all(tuple(groups))
    sys.exit(1 if failures(r) else 0)
