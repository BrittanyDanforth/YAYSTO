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
    P = _skel_pieces()
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
    d = gbc.read_json(path)["data"]
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
        P = BS.mesh_section(v, np.vstack([t1, t2]), np.array([0, 0, 1.515]), np.array([0, 0, 1.0]))
        P = P[np.abs(P[:, 0]) < 0.09]
        g["neck"] = (round(100 * BS.hull_perimeter(P[:, :2]), 2),) + g["neck"][1:]
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
        # the vertex that stands out most from its 6-12 mm ring of neighbours near the RB §7.1 nipple
        c = np.array([0.10 * sx, 1.30])
        q = vh[(np.hypot(vh[:, 0] - c[0], vh[:, 2] - c[1]) < 0.045) & (vh[:, 1] < 0)]
        dd = np.hypot(q[:, None, 0] - q[None, :, 0], q[:, None, 2] - q[None, :, 2])
        ring = (dd > 0.006) & (dd < 0.012)
        mean_y = (ring * q[None, :, 1]).sum(1) / np.maximum(ring.sum(1), 1)
        score = np.where(np.hypot(q[:, 0] - c[0], q[:, 2] - c[1]) < 0.03, mean_y - q[:, 1], -1.0)
        return q[np.argmax(score)]
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
