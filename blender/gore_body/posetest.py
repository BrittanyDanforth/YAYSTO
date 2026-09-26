"""Deformation tests and pose renders for the rig (owner B6).  Plan §8.2 B6, FB-2.

Poses every exported mesh with **linear blend skinning in numpy** (exactly Godot's skinning,
using the weights written by ``rig.skin_all``) and measures, per test pose:

* ``poke_mm``   - how far inner-layer vertices (muscle shell, skeleton, vessels, organs, cord,
                  brain) near the joint end up outside the posed skin (0 = all inside).  Inside /
                  outside is the **signed ray-crossing winding number** of the posed skin (GB_Body +
                  GB_Head), so self-overlapping skin at a deep flexion crease counts as inside;
* ``poke_frac`` - fraction of those vertices more than 3 mm outside (acceptance: none up to 90 %
                  of the live ROM);
* ``vol_loss``  - volume change of the joint region: cone volume of the skin triangles within the
                  region, seen from the joint centre, posed vs rest (acceptance < 15 %);
* ``radius_p5`` - 5th percentile of (posed / rest) distance of region skin vertices from the
                  bone axis: candy-wrapping shows up as a low value;
* ``shorts_mm`` - smallest shorts-to-skin clearance in the region (B1: >= 1 mm at 90 deg hip flexion).

Run alone on a saved build: ``python3 posetest.py [--blend gore_body.blend] [--render] [--only a,b]``
(renders go to ``renders/rig_pose_*.png``).  ``build.py`` runs ``run_tests`` through verify.py.
"""
import math
import os
import sys
import time

import numpy as np

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
import rig  # noqa: E402

SKIN = ("GB_Body", "GB_Head")
INNER = ("GB_MuscleShell", "GB_Skeleton", "GB_Vessels_Art", "GB_Vessels_Ven", "GB_Organs", "GB_Cord", "GB_Brain")
POKE_LIMIT_MM = 3.0
VOL_LIMIT = 0.15

# name: (pose, joint bone (region centre = its head), region radius m, ROM note, level)
#   "fb2":     plan §8.2 B6 / FB-2 acceptance (elbow, knee, shoulder abduction, hip flexion) at 90 % of the
#              live ROM: no inner-layer vertex > 3 mm outside the skin, volume loss < 15 %
#   "max":     the same joints at the full FB-2 value (reported)
#   "quality": every other joint and twist (reported; the same limits are the target)
# Angles are about the rig's resolved axes from the A-pose bind (arm 30 deg abducted): anatomical shoulder
# abduction 90 deg (arm horizontal) is +60 here, +90 is anatomical 120.
TESTS = {
    "elbow_130": ({"forearm_L": [("flex", 130.5)]}, "forearm_L", 0.13, "90 % of live 145", "fb2"),
    "elbow_145": ({"forearm_L": [("flex", 145.0)]}, "forearm_L", 0.13, "FB-2 max", "max"),
    "knee_121": ({"shin_L": [("flex", 121.5)]}, "shin_L", 0.16, "90 % of live 135", "fb2"),
    "knee_135": ({"shin_L": [("flex", 135.0)]}, "shin_L", 0.16, "FB-2 max", "max"),
    "shoulder_abd_60": ({"upper_arm_L": [("abd", 60.0)]}, "upper_arm_L", 0.15, "anatomical 90 (arm horizontal)",
                        "fb2"),
    "shoulder_abd_90": ({"upper_arm_L": [("abd", 90.0)]}, "upper_arm_L", 0.15, "FB-2 90 from the bind = 90 % of "
                        "swing 100 (anatomical 120)", "fb2"),
    "hip_flex_108": ({"thigh_L": [("flex", 108.0)]}, "thigh_L", 0.20, "90 % of live 120", "fb2"),
    "hip_flex_110": ({"thigh_L": [("flex", 110.0)]}, "thigh_L", 0.20, "FB-2 max", "max"),
    "hip_flex_90": ({"thigh_L": [("flex", 90.0)]}, "thigh_L", 0.20, "B1 shorts clearance pose (sitting)",
                    "quality"),
    "shoulder_flex_90": ({"upper_arm_L": [("flex", 90.0)]}, "upper_arm_L", 0.15, "90 % of swing 100", "quality"),
    "shoulder_rhythm_90": ({"upper_arm_L": [("abd", 60.0)], "clavicle_L": [("elev", 27.0)]}, "upper_arm_L", 0.15,
                           "2:1 scapulohumeral rhythm, 90 % of clavicle elevation", "quality"),
    "shoulder_twist_63": ({"upper_arm_L": [("twist", 63.0)]}, "upper_arm_L", 0.16, "90 % of twist 70", "quality"),
    "shoulder_twist_-63": ({"upper_arm_L": [("twist", -63.0)]}, "upper_arm_L", 0.16, "90 % of twist 70",
                           "quality"),
    "hip_abd_40": ({"thigh_L": [("abd", 40.5)]}, "thigh_L", 0.20, "90 % of abd 45", "quality"),
    "hip_ext_22": ({"thigh_L": [("flex", -22.5)]}, "thigh_L", 0.20, "90 % of ext 25", "quality"),
    "pronation_72": ({"hand_L": [("twist", -72.0)]}, "forearm_L", 0.22, "90 % of hand twist 80", "quality"),
    "supination_72": ({"hand_L": [("twist", 72.0)]}, "forearm_L", 0.22, "90 % of hand twist 80", "quality"),
    "wrist_flex_67": ({"hand_L": [("flex", 67.5)]}, "hand_L", 0.08, "90 % of flex 75", "quality"),
    "wrist_ext_58": ({"hand_L": [("flex", -58.5)]}, "hand_L", 0.08, "90 % of ext 65", "quality"),
    "fist_76": ({"fingers_L": [("flex", 76.5)], "thumb_L": [("flex", 45.0)]}, "fingers_L", 0.07,
                "90 % of finger curl 85", "quality"),
    "ankle_plantar_45": ({"foot_L": [("flex", -45.0)]}, "foot_L", 0.12, "90 % of plantar 50", "quality"),
    "ankle_dorsi_18": ({"foot_L": [("flex", 18.0)]}, "foot_L", 0.12, "90 % of dorsi 20", "quality"),
    "toes_ext_36": ({"toes_L": [("flex", -36.0)]}, "toes_L", 0.07, "90 % of toe extension 40", "quality"),
    "neck_flex_42": ({"neck": [("flex", 25.2)], "head": [("flex", 17.1)]}, "neck", 0.16, "90 % of live flex",
                     "quality"),
    "neck_ext_50": ({"neck": [("flex", -29.7)], "head": [("flex", -19.8)]}, "neck", 0.16, "90 % of live ext",
                    "quality"),
    "neck_rot_63": ({"neck": [("twist", 31.5)], "head": [("twist", 31.5)]}, "neck", 0.18, "90 % of live rot",
                    "quality"),
    "neck_lat_40": ({"neck": [("lat", 24.3)], "head": [("lat", 16.2)]}, "neck", 0.16, "90 % of live lat",
                    "quality"),
    "trunk_flex_76": ({"spine": [("flex", 36.0)], "chest": [("flex", 27.0)], "upper_chest": [("flex", 13.5)]},
                      "spine", 0.30, "90 % of live flex", "quality"),
    "trunk_ext_31": ({"spine": [("flex", -13.5)], "chest": [("flex", -9.0)], "upper_chest": [("flex", -9.0)]},
                     "spine", 0.30, "90 % of live ext", "quality"),
    "trunk_rot_40": ({"spine": [("twist", 13.5)], "chest": [("twist", 18.0)], "upper_chest": [("twist", 9.0)]},
                     "chest", 0.30, "90 % of live rot", "quality"),
    "jaw_open_19": ({"jaw": [("open", 19.0)]}, "jaw", 0.16, "death jaw drop 30 mm (volume n/a: the mouth opens)",
                    "quality"),
    "jaw_open_26": ({"jaw": [("open", 26.0)]}, "jaw", 0.16, "kinematic limit: about 45 mm incisal opening",
                    "quality"),
}
NO_VOLUME = {"jaw_open_19", "jaw_open_26"}      # opening the mouth enlarges the oral cavity: a real volume change


# ---------------------------------------------------------------------------
# Scene data
# ---------------------------------------------------------------------------
class MeshData:
    """Rest vertices, triangles and skin weights of one object."""

    def __init__(self, obj):
        self.name = obj.name
        self.v, self.t = gbc.mesh_arrays(obj.data)
        self.idx, self.w = rig.read_weights(obj)
        self.piece = gbc.read_point_attr(obj, "gb_piece", 'INT')


def load_meshes(names):
    return {n: MeshData(bpy.data.objects[n]) for n in names if n in bpy.data.objects}


def _bvh(v, t):
    from mathutils.bvhtree import BVHTree
    return BVHTree.FromPolygons(v.tolist(), t.tolist(), all_triangles=True)


def skin_arrays(md, mats=None):
    """Combined skin (posed if ``mats``): vertices, triangles, triangle normals."""
    V, T, off = [], [], 0
    for n in SKIN:
        m = md[n]
        v = m.v if mats is None else rig.lbs(m.v, m.idx, m.w, mats)
        V.append(v)
        T.append(m.t + off)
        off += len(v)
    V, T = np.vstack(V), np.vstack(T)
    N = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-18)
    return V, T, N


RAYS = (np.array([0.0, 0.0, 1.0]), np.array([0.577, -0.577, 0.577]), np.array([-0.7071, 0.0, -0.7071]))


def winding(bvh, tri_n, pts, rays=RAYS, max_hits=64):
    """Signed ray-crossing winding number of points w.r.t. a closed, outward-oriented surface
    (median over three rays; robust to self-overlapping skin)."""
    from mathutils import Vector
    out = np.zeros((len(pts), len(rays)))
    for k, d in enumerate(rays):
        dv = Vector(d / np.linalg.norm(d))
        for i, p in enumerate(pts):
            o = Vector(p)
            s = 0
            for _ in range(max_hits):
                loc, _nrm, fi, _dist = bvh.ray_cast(o, dv)
                if loc is None:
                    break
                s += 1 if tri_n[fi] @ np.asarray(dv) > 0 else -1
                o = loc + dv * 1e-6
            out[i, k] = s
    return np.median(out, axis=1)


_DIRS26 = np.array([d for d in ((x, y, z) for x in (-1, 0, 1) for y in (-1, 0, 1) for z in (-1, 0, 1))
                    if d != (0, 0, 0)], float)
_DIRS26 /= np.linalg.norm(_DIRS26, axis=1, keepdims=True)


def exposed(bvh, pts, dirs=_DIRS26):
    """True where a point can see out of the skin: at least one of 26 rays leaves without hitting it.

    A torn or folded-open skin can leave inner layers visible while the winding number still counts
    them as inside (the fold adds a layer); this is the camera's view of the same question."""
    from mathutils import Vector
    out = np.zeros(len(pts), bool)
    dv = [Vector(d) for d in dirs]
    for i, p in enumerate(pts):
        o = Vector(p)
        for d in dv:
            if bvh.ray_cast(o, d)[0] is None:
                out[i] = True
                break
    return out


def _cone_volume(V, T, c):
    a, b, d = V[T[:, 0]] - c, V[T[:, 1]] - c, V[T[:, 2]] - c
    return np.einsum("ij,ij->i", a, np.cross(b, d)) / 6.0


_REGION_VOL = {}


def region_volume(V, T, centre, radius, step=0.006):
    """Rest volume (m^3) of the body inside a sphere: grid points inside the closed rest skin (ray parity)."""
    key = (tuple(np.round(centre, 5)), round(radius, 4), len(V))
    if key in _REGION_VOL:
        return _REGION_VOL[key]
    from mathutils import Vector
    bvh = _bvh(V, T)
    g = np.arange(-radius, radius + 1e-9, step)
    X, Y, Z = np.meshgrid(g, g, g, indexing="ij")
    P = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    P = P[np.linalg.norm(P, axis=1) <= radius] + centre
    d = Vector((0.2672612, 0.5345225, 0.8017837))
    inside = 0
    for p in P:
        o = Vector(p)
        n = 0
        for _ in range(64):
            loc, _nrm, _i, _dist = bvh.ray_cast(o, d)
            if loc is None:
                break
            n += 1
            o = loc + d * 1e-6
        inside += n & 1
    vol = inside * step ** 3
    _REGION_VOL[key] = vol
    return vol


def _axis_dist(p, a, b):
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), -0.5, 1.5)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
def run_test(md, arm, name, spec, rest=None):
    """Metrics of one test pose (see module doc)."""
    pose, bone, radius, note, level = spec
    t0 = time.perf_counter()
    mats = rig.pose_matrices(arm, pose)
    bm = rig.bone_map()
    J = np.array(bm[bone]["head"], float)
    tail = np.array(bm[bone]["tail"], float)
    if rest is None:
        rest = skin_arrays(md)
    V0, T, _N0 = rest
    V1, _T, N1 = skin_arrays(md, mats)
    cen = V0[T].mean(1)
    reg_t = np.linalg.norm(cen - J, axis=1) < radius
    # joint-region volume change: the whole skin is closed, so the global signed volume change is
    # exactly the change of the deforming region (everything else moves rigidly); normalised by the
    # rest volume of body tissue inside the region sphere (grid count, inside = ray parity at rest)
    vol0 = region_volume(V0, T, J, radius)
    c = V0.mean(0)
    dvol = _cone_volume(V1, T, c).sum() - _cone_volume(V0, T, c).sum()
    vol1 = vol0 + dvol
    # candy-wrap: skin distance to the bone axis (rest vs posed axis) for vertices along the bone
    reg_v = np.linalg.norm(V0 - J, axis=1) < radius
    bi = rig.BONE_INDEX[bone]
    tailp = (mats[bi] @ np.append(tail, 1.0))[:3]
    headp = (mats[bi] @ np.append(J, 1.0))[:3]
    along = ((V0 - J) @ (tail - J)) / ((tail - J) @ (tail - J))
    sel = reg_v & (along > 0.05) & (along < 0.95)
    if sel.sum() > 20:
        r0 = _axis_dist(V0[sel], J, tail)
        r1 = _axis_dist(V1[sel], headp, tailp)
        radius_p5 = float(np.percentile(r1 / np.maximum(r0, 1e-6), 5))
    else:
        radius_p5 = float("nan")
    bvh = _bvh(V1, T)
    res = {"pose": note, "level": level, "vol_loss": round(1.0 - vol1 / vol0, 4) if vol0 > 0 else None,
           "radius_p5": round(radius_p5, 3)}
    worst, total, over, per, n_exposed = 0.0, 0, 0, {}, 0
    base = rest_outside(md, rest)
    for n in INNER:
        m = md.get(n)
        if m is None:
            continue
        # vertices already outside the skin in the rest pose are geometry issues of their owner
        # package (reported by rest_outside), not deformation: they are left out here
        sel = (np.linalg.norm(m.v - J, axis=1) < radius) & ~base[n]
        if not sel.any():
            continue
        P = rig.lbs(m.v[sel], m.idx[sel], m.w[sel], mats)
        # cheap pre-filter: only points close to the posed skin can be outside
        dist = np.array([bvh.find_nearest(p.tolist())[3] for p in P])
        cand = dist < 0.012
        wn = np.ones(len(P))
        exp = np.zeros(len(P), bool)
        if cand.any():
            wn[cand] = winding(bvh, N1, P[cand])
            # newly visible from outside (rest-visible points are the owner's geometry issue)
            ci = np.nonzero(cand)[0]
            e1 = exposed(bvh, P[ci])
            if e1.any():
                e0 = exposed(rest_bvh(rest), m.v[sel][ci[e1]])
                exp[ci[e1][~e0]] = True
        # outside = winding says outside OR visible from outside through a tear / fold; both count by
        # their distance to the posed skin (the same 3 mm tessellation tolerance)
        outside = (wn < 0.5) | exp
        d_out = np.where(outside, dist, 0.0)
        exp &= dist > POKE_LIMIT_MM / 1000.0
        mx = float(d_out.max() * 1000.0) if len(d_out) else 0.0
        n_over = int((d_out > POKE_LIMIT_MM / 1000.0).sum())
        per[n] = {"n": int(len(P)), "max_mm": round(mx, 2), "over": n_over, "exposed": int(exp.sum())}
        n_exposed += int(exp.sum())
        if n_over and m.piece is not None:
            pieces = np.unique(m.piece[np.nonzero(sel)[0][d_out > POKE_LIMIT_MM / 1000.0]])
            per[n]["pieces"] = [int(x) for x in pieces[:8]]
        if n_over:
            worst_i = np.argsort(-d_out)[:3]
            ids = np.nonzero(sel)[0][worst_i]
            per[n]["worst"] = [{"rest": [round(float(c), 4) for c in m.v[i]], "mm": round(float(d_out[k]) * 1000, 2),
                                "w": {rig.BONE_NAMES[b]: round(float(x), 3) for b, x in zip(m.idx[i], m.w[i]) if x > 0}}
                               for k, i in zip(worst_i, ids)]
        worst = max(worst, mx)
        total += len(P)
        over += n_over
    res.update({"poke_mm": round(worst, 2), "poke_over": over, "poke_frac": round(over / max(total, 1), 5),
                "exposed": n_exposed, "layers": per})
    sh = md.get("GB_Shorts")
    if sh is not None:
        sel = np.linalg.norm(sh.v - J, axis=1) < radius
        if sel.any():
            P = rig.lbs(sh.v[sel], sh.idx[sel], sh.w[sel], mats)
            dist = np.array([bvh.find_nearest(p.tolist())[3] for p in P])
            cand = dist < 0.004
            wn = np.zeros(len(P))
            if cand.any():
                wn[cand] = winding(bvh, N1, P[cand])
            signed = np.where(wn >= 0.5, -dist, dist)
            res["shorts_mm"] = round(float(signed.min() * 1000.0), 2)
            res["shorts_inside"] = int((signed < 0).sum())
    if name in NO_VOLUME:
        res["vol_loss"] = None
    if name.startswith("jaw_open"):
        res["deep_drag"] = deep_drag(md, mats)
    # every level has the same limits: no poke, nothing newly exposed, volume change (loss OR gain) < 15 %,
    # shorts >= 1 mm off the skin in the hip poses, no deep structure dragged by the jaw
    vol_ok = abs(res["vol_loss"] or 0.0) < VOL_LIMIT
    shorts_ok = not (name.startswith("hip_") and res.get("shorts_mm") is not None and res["shorts_mm"] < SHORTS_MIN_MM)
    deep_ok = not res.get("deep_drag", {}).get("over", 0)
    res["ok"] = bool(res["poke_frac"] == 0.0 and res["exposed"] == 0 and vol_ok and shorts_ok and deep_ok)
    res["seconds"] = round(time.perf_counter() - t0, 2)
    return res


SHORTS_MIN_MM = 1.0             # B1: the shorts stay >= 1 mm off the skin at 90 deg hip flexion
DEEP_LAYERS = ("GB_Vessels_Art", "GB_Vessels_Ven", "GB_Organs", "GB_Cord", "GB_Brain")
DEEP_DRAG_MM = 2.0


def deep_drag(md, mats):
    """Jaw poses: deep neck/head structures (vessels, organs, cord, brain above z 1.40) must move with the bone
    they hang from - the nearest skull / vertebra piece (the mandible excluded; points within 8 mm of it may
    follow the jaw).  Returns {"over": n > 2 mm, "worst_mm": .., "by_layer": {...}}."""
    from mathutils.kdtree import KDTree
    sk = md.get("GB_Skeleton")
    if sk is None:
        return {"over": 0, "note": "no skeleton"}
    rigid = gbc.read_point_attr(bpy.data.objects["GB_Skeleton"], "gb_rigid_bone", 'INT')
    jaw_i = rig.BONE_INDEX["jaw"]
    keep = (sk.v[:, 2] > 1.38) & (rigid != jaw_i)
    kd = KDTree(int(keep.sum()))
    kv, kr = sk.v[keep], rigid[keep]
    for i, p in enumerate(kv):
        kd.insert(p.tolist(), i)
    kd.balance()
    jv = sk.v[rigid == jaw_i]
    kj = KDTree(len(jv))
    for i, p in enumerate(jv):
        kj.insert(p.tolist(), i)
    kj.balance()
    over, worst, by = 0, 0.0, {}
    for n in DEEP_LAYERS:
        m = md.get(n)
        if m is None:
            continue
        sel = np.nonzero(m.v[:, 2] > 1.40)[0]
        if not len(sel):
            continue
        P = rig.lbs(m.v[sel], m.idx[sel], m.w[sel], mats)
        cnt, wmm = 0, 0.0
        for k, i in enumerate(sel):
            if kj.find(m.v[i].tolist())[2] < 0.008:
                continue
            _co, j, _d = kd.find(m.v[i].tolist())
            Q = (mats[int(kr[j])] @ np.append(m.v[i], 1.0))[:3]
            d = float(np.linalg.norm(P[k] - Q)) * 1000.0
            wmm = max(wmm, d)
            if d > DEEP_DRAG_MM:
                cnt += 1
        by[n] = {"over": cnt, "worst_mm": round(wmm, 2)}
        over += cnt
        worst = max(worst, wmm)
    return {"over": over, "worst_mm": round(worst, 2), "by_layer": by}


_REST_OUT = {}
_REST_BVH = {}


def rest_bvh(rest):
    """BVH of the rest skin (cached per skin array)."""
    key = id(rest[0])
    if key not in _REST_BVH:
        _REST_BVH.clear()
        _REST_BVH[key] = _bvh(rest[0], rest[1])
    return _REST_BVH[key]


def rest_outside(md, rest=None, tol=POKE_LIMIT_MM / 1000.0):
    """{layer: bool mask} of inner vertices more than ``tol`` outside the skin in the REST pose."""
    key = tuple(sorted((n, len(m.v)) for n, m in md.items()))
    if key in _REST_OUT:
        return _REST_OUT[key]
    V, T, N = rest if rest is not None else skin_arrays(md)
    bvh = _bvh(V, T)
    out = {}
    for n in INNER:
        m = md.get(n)
        if m is None:
            continue
        dist = np.array([bvh.find_nearest(p.tolist())[3] for p in m.v])
        mask = np.zeros(len(m.v), bool)
        cand = dist > tol
        if cand.any():
            wn = winding(bvh, N, m.v[cand])
            mask[np.nonzero(cand)[0][wn < 0.5]] = True
        out[n] = mask
    _REST_OUT[key] = out
    return out


def run_tests(names=None, arm=None, md=None, quiet=False):
    """Run the deformation tests; returns {test: metrics}.  Leaves the armature in the rest pose."""
    arm = arm or bpy.data.objects[gbc.ARMATURE]
    md = md or load_meshes(SKIN + INNER + ("GB_Shorts",))
    rest = skin_arrays(md)
    out = {}
    for name, spec in TESTS.items():
        if names and name not in names:
            continue
        out[name] = run_test(md, arm, name, spec, rest)
        if not quiet:
            r = out[name]
            gbc.log(f"pose {name:20s} vol {r['vol_loss'] if r['vol_loss'] is not None else float('nan'):+.3f}  "
                    f"poke {r['poke_mm']:6.2f} mm exposed {r['exposed']} "
                    f"({r['poke_over']} > 3 mm)  r_p5 {r['radius_p5']:.3f}  shorts {r.get('shorts_mm', '-')} "
                    f"{'OK' if r['ok'] else 'FAIL'}  {r['seconds']} s")
    rig.reset_pose(arm)
    return out


def layer_consistency(md=None):
    """Mean / p95 L1 weight difference between muscle-shell vertices and their nearest skin vertex."""
    from mathutils.kdtree import KDTree
    md = md or load_meshes(SKIN + ("GB_MuscleShell",))
    V = np.vstack([md[n].v for n in SKIN])
    I = np.vstack([md[n].idx for n in SKIN])
    W = np.vstack([md[n].w for n in SKIN])
    kd = KDTree(len(V))
    for i, p in enumerate(V):
        kd.insert(p.tolist(), i)
    kd.balance()
    m = md["GB_MuscleShell"]
    dense_s = np.zeros((len(m.v), rig.NB))
    dense_m = np.zeros((len(m.v), rig.NB))
    for i, p in enumerate(m.v):
        _co, j, _d = kd.find(p.tolist())
        np.add.at(dense_s[i], I[j], W[j])
    np.add.at(dense_m, (np.repeat(np.arange(len(m.v)), 4), m.idx.ravel()), m.w.ravel())
    d = np.abs(dense_s - dense_m).sum(1)
    return {"mean_l1": round(float(d.mean()), 4), "p95_l1": round(float(np.percentile(d, 95)), 4)}


# ---------------------------------------------------------------------------
# Cross-section plots (numpy rasteriser: plane / triangle intersection lines)
# ---------------------------------------------------------------------------
SECTION_COLOURS = {"GB_Body": (20, 20, 20), "GB_Head": (20, 20, 20), "GB_MuscleShell": (200, 30, 30),
                   "GB_Skeleton": (30, 170, 40), "GB_Vessels_Art": (230, 40, 200), "GB_Vessels_Ven": (60, 60, 230),
                   "GB_Organs": (230, 140, 20), "GB_Cord": (240, 200, 0), "GB_Brain": (240, 200, 0),
                   "GB_Shorts": (120, 120, 120)}


def _draw_line(img, p0, p1, col, thick=1):
    n = int(max(abs(p1[0] - p0[0]), abs(p1[1] - p0[1]))) + 1
    xs = np.linspace(p0[0], p1[0], n + 1)
    ys = np.linspace(p0[1], p1[1], n + 1)
    h, w = img.shape[:2]
    for dx in range(-(thick // 2), thick // 2 + 1):
        for dy in range(-(thick // 2), thick // 2 + 1):
            xi = np.clip(np.rint(xs).astype(int) + dx, 0, w - 1)
            yi = np.clip(np.rint(ys).astype(int) + dy, 0, h - 1)
            img[yi, xi] = col


def section_png(md, mats, point, normal, up, half_extent, path, px=640, layers=None):
    """PNG of the intersection lines of every layer with a plane (posed with ``mats`` or rest if None).

    ``up`` is the image's vertical direction (projected into the plane).  Skin black, muscle red,
    bone green, vessels magenta/blue, organs orange, cord/brain yellow, shorts grey; 1 cm grid."""
    point, normal = np.asarray(point, float), rig._unit(normal)
    upv = np.asarray(up, float)
    upv = rig._unit(upv - (upv @ normal) * normal)
    right = np.cross(upv, normal)
    img = np.full((px, px, 3), 255, np.uint8)
    scale = px / (2.0 * half_extent)
    for k in range(-int(half_extent * 100), int(half_extent * 100) + 1):        # 1 cm grid
        c = int(round(px / 2 + k * 0.01 * scale))
        if 0 <= c < px:
            img[:, c] = np.minimum(img[:, c], 235)
            img[c, :] = np.minimum(img[c, :], 235)
    for n in layers or SECTION_COLOURS:
        m = md.get(n)
        if m is None:
            continue
        v = m.v if mats is None else rig.lbs(m.v, m.idx, m.w, mats)
        d = (v - point) @ normal
        t = m.t
        dt = d[t]
        cross = (dt.min(1) < 0) & (dt.max(1) > 0)
        near = np.abs(((v[t].mean(1) - point) @ right)) < half_extent * 1.5
        near &= np.abs(((v[t].mean(1) - point) @ upv)) < half_extent * 1.5
        for tri in t[cross & near]:
            pts = []
            for a, b in ((0, 1), (1, 2), (2, 0)):
                da, db = d[tri[a]], d[tri[b]]
                if (da < 0) != (db < 0):
                    q = v[tri[a]] + (v[tri[b]] - v[tri[a]]) * (da / (da - db))
                    pts.append(q)
            if len(pts) == 2:
                uv = [((q - point) @ right * scale + px / 2, px / 2 - (q - point) @ upv * scale) for q in pts]
                _draw_line(img, uv[0], uv[1], SECTION_COLOURS[n], 2 if n in ("GB_Body", "GB_Head") else 1)
    return gbc.write_png_u8(path, img)


# ---------------------------------------------------------------------------
# Renders
# ---------------------------------------------------------------------------
# name: (pose, camera location, target, lens); "_clear" limbs are moved out of the camera's way
_ARM_UP = {"upper_arm_L": [("abd", 55.0)]}
RENDERS = {
    "elbow_145": ({"forearm_L": [("flex", 145.0)]}, (0.70, 0.42, 1.30), (0.33, 0.02, 1.16), 60.0),
    "elbow_145_front": ({"forearm_L": [("flex", 145.0)]}, (0.62, -0.50, 1.22), (0.33, -0.03, 1.16), 60.0),
    "knee_135": ({"shin_L": [("flex", 135.0)], **_ARM_UP}, (0.70, -0.30, 0.55), (0.09, 0.06, 0.50), 55.0),
    "knee_135_front": ({"shin_L": [("flex", 135.0)], **_ARM_UP}, (0.30, -0.75, 0.62), (0.09, 0.0, 0.50), 55.0),
    "shoulder_abd_60": ({"upper_arm_L": [("abd", 60.0)]}, (0.42, -0.70, 1.40), (0.20, 0.02, 1.36), 50.0),
    "shoulder_abd_90": ({"upper_arm_L": [("abd", 90.0)]}, (0.45, -0.70, 1.40), (0.20, 0.02, 1.38), 50.0),
    "shoulder_abd_90_back": ({"upper_arm_L": [("abd", 90.0)]}, (0.50, 0.75, 1.45), (0.20, 0.04, 1.38), 50.0),
    "shoulder_flex_90": ({"upper_arm_L": [("flex", 90.0)]}, (0.75, -0.25, 1.45), (0.22, -0.10, 1.35), 50.0),
    "hip_flex_110": ({"thigh_L": [("flex", 110.0)], **_ARM_UP}, (0.85, -0.25, 0.95), (0.08, -0.08, 0.88), 45.0),
    "hip_flex_110_back": ({"thigh_L": [("flex", 110.0)], **_ARM_UP}, (0.60, 0.80, 0.80), (0.07, 0.05, 0.86), 45.0),
    "pronation_80": ({"hand_L": [("twist", -80.0)]}, (0.85, -0.35, 1.05), (0.40, 0.02, 1.02), 50.0),
    "shoulder_twist_70": ({"upper_arm_L": [("twist", 70.0)], "forearm_L": [("flex", 90.0)]},
                          (0.60, -0.75, 1.35), (0.25, -0.05, 1.25), 50.0),
    "neck_rot_flex": ({"neck": [("twist", 35.0), ("flex", 20.0)], "head": [("twist", 30.0), ("flex", 15.0)]},
                      (0.35, -0.70, 1.62), (0.0, 0.0, 1.55), 55.0),
    "neck_flex_42": ({"neck": [("flex", 25.2)], "head": [("flex", 17.1)]}, (0.55, -0.35, 1.50), (0.0, -0.02, 1.52),
                     55.0),
    "neck_ext_50": ({"neck": [("flex", -29.7)], "head": [("flex", -19.8)]}, (0.45, -0.50, 1.52), (0.0, -0.02, 1.55),
                    55.0),
    "jaw_open_19": ({"jaw": [("open", 19.0)]}, (0.22, -0.45, 1.60), (0.0, -0.03, 1.57), 60.0),
    "jaw_open_19_side": ({"jaw": [("open", 19.0)]}, (0.50, -0.10, 1.58), (0.0, -0.02, 1.56), 60.0),
    "jaw_open_19_under": ({"jaw": [("open", 19.0)]}, (0.10, -0.40, 1.38), (0.0, -0.03, 1.55), 60.0),
    "jaw_open_26": ({"jaw": [("open", 26.0)]}, (0.22, -0.45, 1.60), (0.0, -0.03, 1.57), 60.0),
    "fist": ({"fingers_L": [("flex", 80.0)], "thumb_L": [("flex", 45.0)], "forearm_L": [("flex", 90.0)]},
             (0.66, -0.50, 1.10), (0.46, -0.12, 1.08), 60.0),
    "ankle_plantar_50": ({"foot_L": [("flex", -50.0)]}, (0.60, -0.35, 0.20), (0.10, 0.00, 0.08), 50.0),
    "trunk_flex_76": ({"spine": [("flex", 36.0)], "chest": [("flex", 27.0)], "upper_chest": [("flex", 13.5)]},
                      (1.10, -0.60, 1.10), (0.0, -0.10, 1.05), 40.0),
}


def _render_setup():
    """Plain skin-like and inner-layer materials so any poke-through shows as a coloured patch."""
    mats = {}

    def mat(name, rgb, rough=0.5):
        m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        m.use_nodes = True
        bsdf = m.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Base Color"].default_value = (*rgb, 1.0)
        bsdf.inputs["Roughness"].default_value = rough
        return m
    mats["skin"] = mat("RIG_skin", (0.42, 0.25, 0.18), 0.5)
    mats["muscle"] = mat("RIG_muscle", (0.55, 0.02, 0.02), 0.4)
    mats["bone"] = mat("RIG_bone", (0.05, 0.9, 0.1), 0.4)          # vivid green: any bone poking out is obvious
    mats["organ"] = mat("RIG_organ", (0.1, 0.2, 0.95), 0.4)
    mats["shorts"] = mat("RIG_shorts", (0.06, 0.06, 0.07), 0.9)
    mats["eye"] = mat("RIG_eye", (0.80, 0.80, 0.78), 0.1)           # eyes and mouth are meant to be seen:
    mats["mouth"] = mat("RIG_mouth", (0.62, 0.36, 0.34), 0.4)       # neutral colours, not "poke" colours
    return mats


def render_weights(bones, views, samples=8, res=(400, 400), out_dir=gbc.RENDER_DIR, pose=None, tag="w"):
    """Weight maps on the skin: each listed bone paints its weight in its own colour (emission, so the
    picture shows the weights, not the lighting).  ``views``: {name: (cam loc, target, lens)}."""
    arm = bpy.data.objects[gbc.ARMATURE]
    cols = [(1.0, 0.1, 0.05), (0.05, 0.8, 0.1), (0.1, 0.3, 1.0), (1.0, 0.85, 0.0), (0.9, 0.1, 0.9),
            (0.0, 0.9, 0.9), (1.0, 0.5, 0.0), (0.5, 0.2, 1.0)]
    mat = bpy.data.materials.get("RIG_weights") or bpy.data.materials.new("RIG_weights")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "rig_w"
    em = nt.nodes.new("ShaderNodeEmission")
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(attr.outputs["Color"], em.inputs["Color"])
    nt.links.new(em.outputs["Emission"], outn.inputs["Surface"])
    saved = {}
    for o in bpy.data.objects:
        if o.type == 'MESH':
            saved[o.name] = (o.hide_render, [s.material for s in o.material_slots])
            o.hide_render = o.name not in SKIN
    for n in SKIN:
        o = bpy.data.objects[n]
        idx, w = rig.read_weights(o)
        c = np.full((len(idx), 3), 0.18)
        for k, b in enumerate(bones):
            bi = rig.BONE_INDEX[b]
            wb = (w * (idx == bi)).sum(1)
            c = c * (1.0 - wb[:, None]) + np.array(cols[k % len(cols)]) * wb[:, None]
        me = o.data
        if "rig_w" in me.color_attributes:
            me.color_attributes.remove(me.color_attributes["rig_w"])
        ca = me.color_attributes.new("rig_w", 'FLOAT_COLOR', 'POINT')
        ca.data.foreach_set("color", np.column_stack([c, np.ones(len(c))]).astype(np.float32).ravel())
        for s in o.material_slots:
            s.material = mat
    paths = []
    try:
        if pose:
            rig.apply_pose(arm, pose)
        for name, (loc, tgt, lens) in views.items():
            cam = gbc.add_camera("RIG_cam", loc, tgt, lens=lens)
            path = os.path.join(out_dir, f"rig_{tag}_{name}.png")
            gbc.render(path, cam, samples=samples, res=res)
            paths.append(path)
    finally:
        rig.reset_pose(arm)
        for n, (hr, slots) in saved.items():
            o = bpy.data.objects.get(n)
            o.hide_render = hr
            for s, m in zip(o.material_slots, slots):
                s.material = m
    return paths


def render_poses(names=None, samples=24, res=(480, 480), out_dir=gbc.RENDER_DIR):
    """Close-up renders of the extreme poses: skin opaque, inner layers in loud colours
    (muscle red, bone green, organs/vessels blue) - a coloured patch on the skin = poke-through."""
    arm = bpy.data.objects[gbc.ARMATURE]
    mats = _render_setup()
    assign = {"GB_Body": "skin", "GB_Head": "skin", "GB_Shorts": "shorts", "GB_MuscleShell": "muscle",
              "GB_Skeleton": "bone", "GB_Organs": "organ", "GB_Vessels_Art": "organ", "GB_Vessels_Ven": "organ",
              "GB_Cord": "organ", "GB_Brain": "organ", "GB_Mouth": "mouth", "GB_Eye_L": "eye", "GB_Eye_R": "eye"}
    saved = {}
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith("GB_"):
            saved[o.name] = (o.hide_render, [s.material for s in o.material_slots])
            if o.name in assign:
                o.hide_render = False
                for s in o.material_slots:
                    s.material = mats[assign[o.name]]
            else:
                o.hide_render = True
    for o in bpy.data.objects:                     # props / room never in these renders
        if o.name.startswith("GBP_"):
            o.hide_render = True
    gbc.setup_stage(floor=False)
    paths = []
    try:
        for name, (pose, loc, tgt, lens) in RENDERS.items():
            if names and name not in names:
                continue
            rig.apply_pose(arm, pose)
            cam = gbc.add_camera("RIG_cam", loc, tgt, lens=lens)
            path = os.path.join(out_dir, f"rig_pose_{name}.png")
            gbc.render(path, cam, samples=samples, res=res)
            paths.append(path)
    finally:
        rig.reset_pose(arm)
        for n, (hr, slots) in saved.items():
            o = bpy.data.objects.get(n)
            if o is None:
                continue
            o.hide_render = hr
            for s, m in zip(o.material_slots, slots):
                s.material = m
    return paths


KEY_VIEWS = {"front": ((0.0, -3.4, 1.05), (0.0, 0.0, 0.92), 42.0),
             "three_q": ((2.3, -2.5, 1.25), (0.0, 0.0, 0.90), 42.0),
             "side": ((3.4, 0.0, 1.05), (0.0, 0.0, 0.92), 42.0)}


def render_key_poses(names=gbc.POSE_ACTIONS, views=KEY_VIEWS, samples=20, res=(360, 540), out_dir=gbc.RENDER_DIR):
    """Full-body renders of the key-pose actions (as keyed, hips translation included)."""
    arm = bpy.data.objects[gbc.ARMATURE]
    mats = _render_setup()
    assign = {"GB_Body": "skin", "GB_Head": "skin", "GB_Shorts": "shorts", "GB_Mouth": "mouth",
              "GB_Eye_L": "eye", "GB_Eye_R": "eye"}
    saved = {}
    for o in bpy.data.objects:
        if o.type == 'MESH':
            saved[o.name] = (o.hide_render, [s.material for s in o.material_slots])
            o.hide_render = o.name not in assign and o.name != "GB_StageFloor"
            if o.name in assign:
                for s in o.material_slots:
                    s.material = mats[assign[o.name]]
    gbc.setup_stage(floor=True)
    paths = []
    arm.animation_data_create()
    try:
        for name in names + ("rest",):
            if name == "rest":
                arm.animation_data.action = None
                rig.reset_pose(arm)
            else:
                arm.animation_data.action = bpy.data.actions[name]
                bpy.context.scene.frame_set(1)
            for v, (loc, tgt, lens) in views.items():
                cam = gbc.add_camera("RIG_cam", loc, tgt, lens=lens)
                path = os.path.join(out_dir, f"rig_{name}_{v}.png")
                gbc.render(path, cam, samples=samples, res=res)
                paths.append(path)
    finally:
        arm.animation_data.action = None
        rig.reset_pose(arm)
        for n, (hr, slots) in saved.items():
            o = bpy.data.objects.get(n)
            o.hide_render = hr
            for s, m in zip(o.material_slots, slots):
                s.material = m
    return paths


def main():
    args = gbc.script_args()
    blend = gbc.BLEND_PATH
    only = None
    if "--blend" in args:
        blend = args[args.index("--blend") + 1]
    if "--only" in args:
        only = args[args.index("--only") + 1].split(",")
    bpy.ops.wm.open_mainfile(filepath=blend)
    if "--reskin" in args:
        objs = {n: bpy.data.objects[n] for n in gbc.exported_mesh_names(0) + gbc.exported_mesh_names(1)
                if n in bpy.data.objects}
        with gbc.Timer("reskin"):
            rig.skin_all(objs)
    if "--render" in args:
        render_poses(only)
    if "--no-tests" not in args:
        md = load_meshes(SKIN + INNER + ("GB_Shorts",))
        ro = rest_outside(md)
        gbc.log("rest pose, inner vertices > 3 mm outside the skin: " +
                ", ".join(f"{n} {int(m.sum())}/{len(m)}" for n, m in ro.items()))
        res = run_tests(only, md=md)
        for k, v in res.items():
            if not v["ok"] or "-v" in args:
                gbc.log(f"  {k}: " + "; ".join(f"{n} max {d['max_mm']} over {d['over']} {d.get('pieces', '')}"
                                               for n, d in v["layers"].items() if d["over"] or d["max_mm"] > 0))
                if "--detail" in args:
                    for n, d in v["layers"].items():
                        for wv in d.get("worst", []):
                            gbc.log(f"      {n} {wv}")
        bad = [k for k, v in res.items() if not v["ok"]]
        gbc.log(f"{len(res)} tests, failing: {bad}")
        if "--consistency" in args:
            gbc.log(f"muscle vs skin weights: {layer_consistency()}")


if __name__ == "__main__":
    main()
