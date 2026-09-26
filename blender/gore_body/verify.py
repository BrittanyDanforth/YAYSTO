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


def check(group, owner="B0", severity="fail"):
    """Decorator registering a verification check."""
    def deco(fn):
        CHECKS.append((group, fn.__name__, owner, severity, fn))
        return fn
    return deco


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
    eye = gbc.head_to_body(LM.HEAD_CONTRACT["eye_L"])
    if not _close(bm["eye_L"]["head"], eye, 0.001):
        bad.append("eye_L")
    return not bad, f"joint heads vs RB §7.1/§1.2 landmarks within 2 mm; off: {bad}"


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


@check("tables")
def json_deterministic():
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
    bad = []
    for o in _exported():
        names = tuple(m.name if m else "" for m in o.data.materials)
        if names != tuple(gbc.MATERIAL_SLOTS[o.name]):
            bad.append(f"{o.name}: {names}")
    return not bad, f"slot names equal plan §5.6; bad: {bad}"


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
    for o in _exported():
        rb = gbc.read_point_attr(o, "gb_rigid_bone", 'INT')
        if rb is None:
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
    bm = {b["name"]: b for b in RT.bones()}
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
        if not _close(c, (sx * 0.032, -0.050, 1.669), 0.0015):
            bad.append(f"{side} {np.round(c, 4).tolist()}")
    return not bad, f"eyeball centres at (+-0.032, -0.050, 1.669) [RB §1.2]; bad: {bad}"


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


def _nesting(names, tol=0.0005):
    bpy = _bpy()
    bvh = _skin_bvh()
    rng = gbc.rng("verify")
    res = {}
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        v = gbc.get_verts(o.data)
        pts = v[rng.choice(len(v), min(3000, len(v)), replace=False)]
        res[n] = round(_outside_fraction(bvh, pts, tol), 4)
    return res


@check("scene")
def nesting_inside_skin():
    """FB-4 style: inner layers stay inside the skin (sampled vertices, 0.5 mm tolerance, <= 1 %)."""
    res = _nesting(("GB_MuscleShell", "GB_Skeleton", "GB_Organs", "GB_Brain", "GB_Cord"))
    return all(v <= 0.01 for v in res.values()), f"fraction of sampled vertices outside the skin: {res}"


@check("scene", owner="B5", severity="warn")
def vessels_inside_skin():
    """FB-5 precursor: vessel tubes inside the skin (B5 fits the waypoints to the final skin)."""
    res = _nesting(("GB_Vessels_Art", "GB_Vessels_Ven"))
    return all(v <= 0.01 for v in res.values()), f"fraction of sampled tube vertices outside the skin: {res}"


@check("scene", severity="warn")
def triangle_budgets():
    bpy = _bpy()
    over = []
    for key, budget in gbc.TRI_BUDGET.items():
        names = gbc.TRI_BUDGET_GROUPS.get(key, (key,))
        tris = sum(gbc.tri_count(bpy.data.objects[n].data) for n in names if n in bpy.data.objects)
        if tris > budget * 1.10:
            over.append(f"{key} {tris}/{budget}")
    return not over, f"plan §4.1 budgets (+10 %); over: {over}"


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
# runner
# ===========================================================================
def verify_all(groups=("tables", "scene", "files"), quiet=False):
    """Run every registered check of ``groups``; returns {name: {ok, severity, owner, group, detail}}."""
    res = {}
    for group, name, owner, sev, fn in CHECKS:
        if group not in groups:
            continue
        try:
            ok, detail = fn()
        except Exception as exc:                        # a crashing check is a failing check
            ok, detail = False, f"EXCEPTION {type(exc).__name__}: {exc}\n{traceback.format_exc(limit=3)}"
        res[name] = {"ok": bool(ok), "severity": sev, "owner": owner, "group": group, "detail": detail}
    if not quiet:
        report(res)
    return res


def failures(res):
    """Names of failing 'fail'-severity checks."""
    return [k for k, v in res.items() if not v["ok"] and v["severity"] == "fail"]


def report(res):
    """Print a compact report."""
    for k, v in res.items():
        flag = "PASS" if v["ok"] else ("FAIL" if v["severity"] == "fail" else "WARN")
        print(f"  [{flag}] {v['group']:6s} {v['owner']:3s} {k}: {v['detail']}")
    f = failures(res)
    w = [k for k, v in res.items() if not v["ok"] and v["severity"] != "fail"]
    print(f"verify: {len(res)} checks, {len(f)} failures, {len(w)} warnings")


if __name__ == "__main__":
    args = gbc.script_args()
    groups = ["tables", "files"]
    if "--blend" in args:
        import bpy
        bpy.ops.wm.open_mainfile(filepath=os.path.abspath(args[args.index("--blend") + 1]))
        groups.append("scene")
    r = verify_all(tuple(groups))
    sys.exit(1 if failures(r) else 0)
