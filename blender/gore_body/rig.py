"""Rig, weights, poses and rig.json (owner B6).  Plan §3.1, §3.2, §5.4, §5.8, §8.2 B6.

Entry points (final signatures)
-------------------------------
``build_armature()``            -> ``GB_Armature`` (39 deform bones, A-pose bind, B6 bone fits applied)
``bone_rows()``                 -> the rig table as built (``gb_data.rig_table`` + ``BONE_FIT``)
``weights_at(points, layer)``   -> (idx[N,4], w[N,4]): ONE analytic weight function for every layer (D8)
``skin_all(objs)``              -> parent + vertex groups + a single ARMATURE modifier on every mesh
``build_poses(arm)``            -> single-frame key-pose actions pose_idle / guard / cower / brace
``rig_table()``                 -> rig.json payload (bones, bodies, kinematic drivers, face, weight model)
``pose_matrices(arm, pose)``    -> (39, 4, 4) skinning matrices for a joint-angle pose (tests, poses)
``lbs(points, idx, w, mats)``   -> linear-blend-skinned points (exactly what Godot's skinning does)

Weight model (plan §8.2 B6: "analytic smooth weights from distance to bone segments with joint
blend zones scaled by the local limb radius, twist bones sharing along their length, face bones
by angular regions around the eyes and under the mouth line; the same function for every layer")
------------------------------------------------------------------------------------------------
The body is a partition of unity over *territories*:

* **limb territories** (arm L/R, leg L/R, neck + head) are cut off the trunk by a joint *gate*
  at the shoulder, hip and C7/T1; the **shoulder girdle** (clavicle + scapula + acromion) is a
  territory of its own between the trunk and the arm;
* the **trunk** remainder is split along the hips -> spine -> chest -> upper_chest chain;
* inside a limb, every joint gate splits parent from child along the chain.

A gate is ``smootherstep((a - o(phi)) / w(phi))`` of the axial coordinate ``a`` measured from the
joint along the child bone.  ``phi`` is the angle around the joint (0 = the flexor / compression
side), and the offset ``o`` and half-width ``w`` are interpolated between the flexor, lateral,
extensor and medial sides (four values each, all multiples of the local limb radius ``R_J``).
Two consequences drive the numbers:

1. **Columnar weights.**  Away from the bone axis a gate depends only on (a, phi), never on the
   distance from the axis, so skin, fat wall, muscle shell, vessels and organs on the same radial
   line get *identical* weights; linear blend skinning is then an affine map along that line and
   the layers stay nested in every pose.  Near the axis (``r < r_att``) the sector offsets fade to
   one axial value so the spinal canal, cord and deep vessels follow the vertebra/bone line.
2. **Extensor-side shift.**  A blended vertex is pulled toward the joint centre by
   cos(theta/2) of its distance (the linear-blend "chord").  On the extensor side of the elbow
   and knee the rigid olecranon / patella lie right under the skin, so the blend there is moved
   proximally (the skin over the olecranon / patella moves 100 % with the forearm / shin) where
   the chord stays far outside the bone.  The acromion, malleoli, styloids and ischial tuberosity
   are handled the same way (their skin stays with the bone they belong to).

Twist bones: ``upper_arm_twist_*`` carries the proximal half of the upper arm and is driven at
**-50 %** of the shoulder's twist (world twist 50 %); ``forearm_twist_*`` carries the mid/distal
forearm at **+50 %** of the hand's pronation/supination.  The skin twists 0 -> 50 -> 100 %
along the limb instead of collapsing (rig.json ``kinematic.*.driver``).

Face: the jaw territory is the Voronoi cell of the head project's mandible against its skull
(skin over the mandible, lower lip, chin, mouth floor -> ``jaw``; upper lip, palate, cheeks over
the zygoma -> ``head``; the mouth corners and masseter blend), cut off below by the head gate so
the submandibular skin stretches between chin and neck.  Lid weights are B2's measured angular
lid regions (``head_integration.face_weights``) blended into the same function, and the brow /
lash cards and eye FX shells take the weights of the skin at their anchors (``follower_weights``).

Everything is a pure function of the rest position: the head/body seam ring gets identical
weights from both meshes, and the Godot game can evaluate nothing of this at runtime - weights
are baked into the glb (4 influences, 1/4096 grid, rows sum exactly to 1).
"""
import math
import os
import sys

import numpy as np

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402
from gb_data import myotomes as MYO  # noqa: E402

BONE_NAMES = RT.BONE_NAMES
BONE_INDEX = RT.BONE_INDEX
NB = len(BONE_NAMES)
QUANT = 4096         # weight grid (exact float sums)
MAX_INF = 4          # influences per vertex (plan §5.9 export_influence_nb)


# ===========================================================================
# B6 bone fits on top of the rig table (the table's rows marked E)
# ===========================================================================
def _thumb_fit():
    """Thumb bone = B1's thumb: CMC -> tip (the table's thumb row is an E guess 9 mm off)."""
    import body_skin as BS
    pts = [np.asarray(BS.hand_point(*p), float) for p in BS.THUMB_PTS]
    tip = pts[-1] + (pts[-1] - pts[-2]) / np.linalg.norm(pts[-1] - pts[-2]) * BS.THUMB_R[-1]
    return tuple(round(float(c), 5) for c in pts[0]), tuple(round(float(c), 5) for c in tip)


def _jaw_fit():
    """Jaw bone head = measured TMJ hinge (B2: midpoint of the head project's condyle centres)."""
    try:
        import head_integration as hi
        jp = hi.jaw_pivot()
        return tuple(round(float(c), 5) for c in jp)
    except Exception:                                             # pragma: no cover - head import failed
        return (0.0, 0.0085, 1.645)


def _bone_fit():
    """{bone: {"head": .., "tail": .., "why": ..}} applied by ``bone_rows`` (left rows mirrored)."""
    th_h, th_t = _thumb_fit()
    return {
        "jaw": {"head": _jaw_fit(), "why": "B2 measured TMJ hinge (condyle centres); plan row is E"},
        "thumb_L": {"head": th_h, "tail": th_t, "why": "B1 thumb geometry (CMC -> tip); plan row is E"},
    }


_ROWS = None


def bone_rows():
    """The 39 bone rows as built: ``gb_data.rig_table.bones()`` with the B6 fits (``_bone_fit``)."""
    global _ROWS
    if _ROWS is None:
        fit = _bone_fit()
        rows = []
        for b in RT.bones():
            b = dict(b)
            f = fit.get(b["name"])
            if f is None and b["name"].endswith("_R"):
                fl = fit.get(b["name"][:-2] + "_L")
                if fl is not None:
                    f = {k: (tuple(gbc.mirror_x(v)) if k in ("head", "tail") else v) for k, v in fl.items()}
            if f is not None:
                for k in ("head", "tail"):
                    if k in f:
                        b[k] = tuple(float(c) for c in f[k])
                b["note"] = (b["note"] + "; " if b["note"] else "") + "B6 fit: " + f["why"]
                b["fit"] = True
            rows.append(b)
        _ROWS = rows
    return _ROWS


def bone_rows_frame(frame="final"):
    """``bone_rows`` in the final body frame (neck lengthened, ``gbc.NECK_LIFT``: the armature, poses and
    tests) or the authoring frame (weight gates, geometry stages, rig.json before export warps it)."""
    if frame == "authoring":
        return bone_rows()
    out = []
    for b in bone_rows():
        b = dict(b)
        b["head"] = tuple(float(c) for c in gbc.warp_points(b["head"]))
        b["tail"] = tuple(float(c) for c in gbc.warp_points(b["tail"]))
        out.append(b)
    return out


def bone_map(frame="final"):
    return {b["name"]: b for b in bone_rows_frame(frame)}


# ===========================================================================
# Small maths
# ===========================================================================
def _unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


def _sstep(e0, e1, x):
    """Quintic smootherstep from 0 at e0 to 1 at e1 (C2; e0 > e1 allowed for a falling step)."""
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * t * (t * (6.0 * t - 15.0) + 10.0)


def _sector(vals, c, s):
    """Periodic Catmull-Rom interpolation of N values at phi = k * 360/N (cos phi = c, sin phi = s)."""
    v = np.asarray(vals, float)
    n = len(v)
    f = (np.arctan2(s, c) % (2.0 * np.pi)) / (2.0 * np.pi) * n
    i = np.floor(f).astype(int)
    t = f - i
    p0, p1, p2, p3 = v[(i - 1) % n], v[i % n], v[(i + 1) % n], v[(i + 2) % n]
    return 0.5 * ((2.0 * p1) + (-p0 + p2) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t * t
                  + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * t * t * t)


def _mirror(p):
    q = np.array(p, float, copy=True)
    q[..., 0] = -q[..., 0]
    return q


# ===========================================================================
# Joint gates
# ===========================================================================
class Gate:
    """Smooth 0 -> 1 split between a parent and a child territory at a joint (see module doc).

    ``J`` joint centre, ``u`` axial direction into the child, ``ref0`` the flexor-side direction
    (phi = 0), ``ref90`` the phi = 90 deg direction.  ``o`` / ``w``: offsets / half-widths at N
    equally spaced angles phi = 0, 360/N, ... (N = 4 or 8, periodic Catmull-Rom in between).

    ``mode="axial"``: the gate coordinate is the axial distance ``a`` (m), so o/w are metres.
    ``mode="ray"``:   the coordinate is the elevation angle psi = atan2(a, sqrt(r^2 + r0^2)) seen from
    the joint centre (degrees; o/w in degrees): points on one ray from the joint share weights, so
    layers nested around the joint (skin, fat wall, muscle shell) stay nested under the same
    blended transform even where deep flexion folds the skin; ``r0`` makes it axial near the axis.

    Within ``r_att`` of the axis the sector values fade to ``o_axis`` / ``w_axis``.  ``contain``:
    optional (r_in, r_out) per sector - points further than r_out from the axis are outside the
    child (where a limb meets the trunk); beyond ``contain_a`` (axial range) the radii blend to
    ``contain_far`` (the free limb: excludes the hand next to the thigh, the other limbs)."""

    def __init__(self, J, u, ref0, ref90, o, w, o_axis=None, w_axis=None, r_att=(0.02, 0.04),
                 contain=None, contain_a=(1.0, 1.1), contain_far=(0.5, 0.6), mode="axial", r0=0.02):
        self.J = np.asarray(J, float)
        self.u = _unit(u)
        e0 = np.asarray(ref0, float)
        e0 = _unit(e0 - (e0 @ self.u) * self.u)
        e1 = np.asarray(ref90, float)
        e1 = e1 - (e1 @ self.u) * self.u - (e1 @ e0) * e0
        self.e0, self.e1 = e0, _unit(e1)
        self.o, self.w = tuple(o), tuple(w)
        self.o_axis = float(np.mean(o)) if o_axis is None else o_axis
        self.w_axis = float(np.mean(w)) if w_axis is None else w_axis
        self.r_att = r_att
        self.contain = contain
        self.contain_a = contain_a
        self.contain_far = contain_far
        self.mode = mode
        self.r0 = r0

    def coords(self, p):
        q = p - self.J
        a = q @ self.u
        x0, x1 = q @ self.e0, q @ self.e1
        r = np.sqrt(x0 * x0 + x1 * x1)
        rr = np.maximum(r, 1e-9)
        return a, r, x0 / rr, x1 / rr

    def __call__(self, p):
        a, r, c, s = self.coords(p)
        att = _sstep(self.r_att[0], self.r_att[1], r)
        o = self.o_axis + (_sector(self.o, c, s) - self.o_axis) * att
        w = self.w_axis + (_sector(self.w, c, s) - self.w_axis) * att
        x = np.degrees(np.arctan2(a, np.sqrt(r * r + self.r0 * self.r0))) if self.mode == "ray" else a
        g = _sstep(-1.0, 1.0, (x - o) / w)
        if self.contain is not None:
            far = _sstep(self.contain_a[0], self.contain_a[1], a)
            r_in = _sector(self.contain[0], c, s) * (1.0 - far) + self.contain_far[0] * far
            r_out = _sector(self.contain[1], c, s) * (1.0 - far) + self.contain_far[1] * far
            g = g * _sstep(r_out, r_in, r)
        return g


def _polyline_param(p, pts):
    """(distance, normalised arc parameter 0..1) of points to a polyline."""
    pts = np.asarray(pts, float)
    seg_len = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)])
    best_d = np.full(len(p), np.inf)
    best_t = np.zeros(len(p))
    for i in range(len(pts) - 1):
        a, b = pts[i], pts[i + 1]
        ab = b - a
        t = np.clip(((p - a) @ ab) / (ab @ ab), 0.0, 1.0)
        d = np.linalg.norm(p - (a + t[:, None] * ab), axis=1)
        m = d < best_d
        best_d[m] = d[m]
        best_t[m] = (cum[i] + t[m] * seg_len[i]) / cum[-1]
    return best_d, best_t


# ---------------------------------------------------------------------------
# Joint geometry (left side; the right side evaluates the same functions on x-mirrored points)
# ---------------------------------------------------------------------------
ANT = (0.0, -1.0, 0.0)
POST = (0.0, 1.0, 0.0)
LEFT = (1.0, 0.0, 0.0)
UP = (0.0, 0.0, 1.0)
ARM_D = _unit((0.5, 0.0, -0.8660254))
ARM_LAT = _unit((0.8660254, 0.0, 0.5))          # lateral / superior side of the A-pose arm
ARM_MED = -ARM_LAT                              # palm side (medial) in the A-pose

# local limb radii R_J (m) measured on B1's skin (cross-sections at the joint); gates are k * R_J
R_J = {"shoulder": 0.055, "elbow": 0.040, "wrist": 0.029, "mcp": 0.030, "hip": 0.090, "knee": 0.056,
       "ankle": 0.034, "mtp": 0.030, "neck": 0.060, "head": 0.060, "trunk": 0.140}


def _k(joint, *ks):
    """k * R_J for a tuple of multipliers."""
    return tuple(round(k * R_J[joint], 5) for k in ks)


_GATES = None


def _gates():
    """Build the joint gates once (they read the bone rows and B1's hand/foot layout)."""
    global _GATES
    if _GATES is not None:
        return _GATES
    import body_skin as BS
    bm = bone_map("authoring")
    g = {}
    GH = np.array(bm["upper_arm_L"]["head"])
    EL = np.array(bm["forearm_L"]["head"])
    WR = np.array(bm["hand_L"]["head"])
    HIP = np.array(bm["thigh_L"]["head"])
    KN = np.array(bm["shin_L"]["head"])
    AN = np.array(bm["foot_L"]["head"])
    TO = np.array(bm["toes_L"]["head"])
    u_thigh = _unit(np.array(bm["thigh_L"]["tail"]) - HIP)
    u_shin = _unit(np.array(bm["shin_L"]["tail"]) - KN)
    # ---- arm --------------------------------------------------------------------------------
    # shoulder: sectors lateral(superior) / anterior / medial(axilla) / posterior
    g["shoulder"] = Gate(GH, ARM_D, ARM_LAT, ANT,
                         o=_k("shoulder", 0.27, 0.82, 1.55, 0.91), w=_k("shoulder", 0.91, 1.18, 1.00, 1.18),
                         o_axis=0.020, w_axis=0.030, r_att=(0.020, 0.045),
                         contain=(_k("shoulder", 1.55, 1.36, 1.13, 1.45), _k("shoulder", 2.45, 2.18, 1.82, 2.27)),
                         contain_a=(0.14, 0.24), contain_far=(0.090, 0.130))
    # elbow: flexor = anterior; on the olecranon side the blend sits proximal of the olecranon (ray gate)
    g["elbow"] = Gate(EL, ARM_D, ANT, ARM_LAT, mode="ray", r0=0.6 * R_J["elbow"],
                      o=(4.0, -8.0, -58.0, -8.0), w=(14.0, 22.0, 26.0, 22.0),
                      o_axis=-15.0, w_axis=30.0, r_att=(0.012, 0.030))
    # wrist: flexor = palm (medial in the A-pose), phi 90 = radial (thumb, anterior)
    g["wrist"] = Gate(WR, ARM_D, ARM_MED, ANT,
                      o=_k("wrist", 0.14, 0.20, -0.14, 0.20), w=_k("wrist", 0.48, 0.48, 0.48, 0.48),
                      o_axis=0.0, w_axis=0.014, r_att=(0.008, 0.020))
    # ---- hand: finger MCP arc and thumb polyline (B1 layout) ----------------------------------------
    mcp = sorted((BS.FINGERS[n][0], BS.FINGERS[n][1]) for n in BS.FINGERS)        # (radial r, distal s)
    g["mcp_r"] = np.array([m[0] for m in mcp])
    g["mcp_s"] = np.array([m[1] for m in mcp])
    g["wrist_pt"] = np.asarray(BS.WRIST, float)
    g["hand_f"] = np.asarray(BS.HAND_F, float)
    g["hand_n"] = np.asarray(BS.HAND_N, float)
    g["arm_d"] = np.asarray(BS.ARM_D, float)
    g["thumb_pts"] = np.array([BS.hand_point(*p) for p in BS.THUMB_PTS], float)
    g["thumb_r"] = np.array(BS.THUMB_R, float)
    # ---- leg ---------------------------------------------------------------------------------------
    # hip: flexor = anterior (groin crease), lateral (trochanter), posterior (buttock: the blend sits
    # at the gluteal fold so the skin over the ischial tuberosity stays with the pelvis), medial
    g["hip"] = Gate(HIP, u_thigh, ANT, LEFT,
                    o=_k("hip", -0.22, -0.28, 1.20, 0.40), w=_k("hip", 0.22, 0.40, 0.80, 0.33),
                    o_axis=0.0, w_axis=0.030, r_att=(0.030, 0.070),
                    contain=((0.13,) * 4, (0.18,) * 4), contain_a=(0.30, 0.40), contain_far=(0.30, 0.40))
    # knee: flexor = posterior; on the patella side the blend sits above the patella (ray gate: the
    # shin share reaches ~16 cm up the thigh front, 50 % at ~7 cm, full over the patella)
    g["knee"] = Gate(KN, u_shin, POST, LEFT, mode="ray", r0=0.6 * R_J["knee"],
                     o=(6.0, -24.0, -45.0, -24.0), w=(20.0, 26.0, 20.0, 26.0),
                     o_axis=-15.0, w_axis=30.0, r_att=(0.020, 0.045))
    # ankle: phi 0 = front (dorsum), 90 = lateral (malleolus stays with the shin), 180 = heel
    g["ankle"] = Gate(AN, u_shin, ANT, LEFT,
                      o=_k("ankle", -1.03, 0.88, -0.29, 0.65), w=_k("ankle", 0.59, 0.35, 0.59, 0.35),
                      o_axis=0.0, w_axis=0.015, r_att=(0.015, 0.035))
    # toes: plane along the oblique MTP row (hallux base distal of the little-toe base)
    t0, t4 = BS.TOES[0], BS.TOES[4]
    ds, dw = t4[0] - t0[0], t4[1] - t0[1]
    n_sw = _unit((dw, -ds))                                          # normal of the row in (s, w)
    u_toe = _unit(n_sw[0] * np.asarray(BS.FOOT_F) + n_sw[1] * np.asarray(BS.FOOT_L))
    g["toes"] = Gate(TO, u_toe, UP, LEFT,
                     o=_k("mtp", 0.20, 0.30, 0.60, 0.30), w=_k("mtp", 0.40, 0.40, 0.40, 0.40),
                     o_axis=0.010, w_axis=0.012, r_att=(0.010, 0.025))
    # ---- neck and head (midline) ---------------------------------------------------------------------
    NK = np.array(bm["neck"]["head"])
    HD = np.array(bm["head"]["head"])
    g["neck"] = Gate(NK, (0.0, 0.0, 1.0), ANT, LEFT,
                     o=_k("neck", -0.20, 0.0, 0.42, 0.0), w=_k("neck", 0.47, 0.50, 0.50, 0.50),
                     o_axis=0.0, w_axis=0.020, r_att=(0.020, 0.050),
                     contain=((0.068, 0.066, 0.068, 0.066), (0.112, 0.108, 0.112, 0.108)), contain_a=(0.04, 0.07),
                     contain_far=(0.5, 0.6))
    u_head = _unit(np.array(bm["head"]["tail"]) - HD)
    g["head"] = Gate(HD, u_head, ANT, LEFT,
                     o=_k("head", -0.83, -0.60, -0.37, -0.60), w=_k("head", 0.20, 0.30, 0.30, 0.30),
                     o_axis=0.003, w_axis=0.012, r_att=(0.028, 0.060))
    # ---- trunk chain (gates inside the trunk remainder): vertical axes through the joint, 8 sectors
    # (0 front, 45 front-lateral, 90 lateral, ... 180 back).  The boundaries follow the rigid bones
    # the skin lies on: the spine gate sits above the iliac crest / ASIS / sacrum (pelvis skin stays
    # with the hips), the chest gate below the costal margin (skin over costal cartilages 8-10 and
    # ribs 11-12 moves with the chest), the upper_chest gate between ribs 7 and 8 (T7/T8 at the back).
    # (the front widths are larger: forward bending folds the belly there, a wide blend folds it softly)
    trunk = {"spine": ((0.040, 0.070, 0.095, 0.080, 0.050, 0.080, 0.095, 0.070), (0.040,) * 8),
             "chest": ((-0.020, -0.060, -0.105, -0.075, -0.010, -0.075, -0.105, -0.060),
                       (0.060, 0.050, 0.035, 0.035, 0.035, 0.035, 0.035, 0.050)),
             "upper_chest": ((-0.118, -0.098, -0.078, -0.053, -0.013, -0.053, -0.078, -0.098),
                             (0.035, 0.030, 0.018, 0.018, 0.018, 0.018, 0.018, 0.030))}
    for name, (o, w) in trunk.items():
        b = bm[name]
        g[name] = Gate(b["head"], UP, ANT, LEFT, o=o, w=w, o_axis=float(o[4]), w_axis=float(w[4]),
                       r_att=(0.03, 0.07))
    g["GH"], g["EL"], g["WR"], g["HIP"], g["KN"] = GH, EL, WR, HIP, KN
    _GATES = g
    return g


# ---------------------------------------------------------------------------
# Territories
# ---------------------------------------------------------------------------
def _girdle(p):
    """Shoulder-girdle territory (left, 0..1): skin over the clavicle, the acromion, the top of the
    shoulder (supraspinous fossa, upper trapezius) and the scapula - it moves with ``clavicle_L``
    (the scapula is rigid to it), so a shrug lifts the skin with the shoulder blade."""
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    d, _t = _polyline_param(p, [(0.040, -0.046, 1.452), (0.125, -0.024, 1.462), (0.205, 0.016, 1.458)])
    clav = _sstep(0.058, 0.025, d) * _sstep(0.035, 0.080, x)
    d, _t = _polyline_param(p, [(0.075, 0.098, 1.432), (0.140, 0.076, 1.446), (0.205, 0.022, 1.455)])
    spine = _sstep(0.068, 0.035, d) * _sstep(0.030, 0.062, x)
    q = np.sqrt(((x - 0.140) / 0.080) ** 2 + ((y - 0.090) / 0.075) ** 2 + ((z - 1.385) / 0.090) ** 2)
    body = _sstep(1.15, 0.65, q) * _sstep(0.020, 0.060, y)
    a = np.linalg.norm(p - np.array([0.195, 0.018, 1.447]), axis=1)
    acr = _sstep(0.062, 0.030, a)
    m = np.stack([clav, spine, body, acr], 1)
    return np.clip((m ** 4).sum(1) ** 0.25, 0.0, 1.0)


def _fingers_thumb(p, g):
    """(fingers gate, thumb gate) inside the hand (left)."""
    q = p - g["wrist_pt"]
    s = q @ g["arm_d"]
    r = q @ g["hand_f"]
    n = q @ g["hand_n"]
    s0 = np.interp(r, g["mcp_r"], g["mcp_s"])
    o = -0.004 + 0.016 * _sstep(-0.008, 0.008, n)                   # dorsal knuckle line / palmar digital crease
    fing = _sstep(-1.0, 1.0, (s - s0 - o) / 0.010)
    d, t = _polyline_param(p, g["thumb_pts"])
    R = np.interp(t, np.linspace(0.0, 1.0, len(g["thumb_r"])), g["thumb_r"])
    thumb = _sstep(1.9, 1.2, d / R) * _sstep(0.05, 0.40, t)
    fing = fing * (1.0 - thumb)
    return fing, thumb


def _arm_split(p, g):
    """Weights inside the left arm territory: {bone base: weight} (sum 1)."""
    a = (p - g["GH"]) @ ARM_D
    ael = (p - g["EL"]) @ ARM_D
    e = g["elbow"](p)
    wr = g["wrist"](p)
    tw_off = _sstep(0.10, 0.20, a)                    # upper_arm_twist -> upper_arm handover
    ftw_on = _sstep(0.03, 0.14, ael)                  # forearm -> forearm_twist handover
    fing, thumb = _fingers_thumb(p, g)
    hand = e * wr
    return {"upper_arm_twist": (1.0 - tw_off) * (1.0 - e), "upper_arm": tw_off * (1.0 - e),
            "forearm": e * (1.0 - ftw_on) * (1.0 - wr), "forearm_twist": e * ftw_on * (1.0 - wr),
            "hand": hand * (1.0 - fing - thumb), "fingers": hand * fing, "thumb": hand * thumb}


def _leg_split(p, g):
    k = g["knee"](p)
    an = g["ankle"](p)
    to = g["toes"](p)
    return {"thigh": 1.0 - k, "shin": k * (1.0 - an), "foot": k * an * (1.0 - to), "toes": k * an * to}


_HEAD_SDF = None


def _head_sdfs():
    global _HEAD_SDF
    if _HEAD_SDF is None:
        import head_integration as hi_
        f = hi_.head_layer_sdfs()
        _HEAD_SDF = (f["skull"][0], f["jaw"][0])
    return _HEAD_SDF


# head / jaw box: outside it the head project's skull and mandible are far away (the box reaches down
# to the lower neck for the throat sheet)
_HJ_LO = np.array([-0.090, -0.120, 1.440])
_HJ_HI = np.array([0.090, 0.070, 1.710])
MANDIBLE_NEAR = (0.012, 0.022)      # skin within 12 mm of the mandible is head/jaw, beyond 22 mm neck
# Throat sheet (submental + anterior neck skin and everything under it on the same ray from the neck
# axis): the share of the jaw rises from 0 low on the neck to 1 at the chin, so opening the mouth
# stretches / compresses the whole front of the neck smoothly instead of tearing a 1-2 cm band under
# the chin.  Columns are rays from the neck axis (x = 0, y = NECK_AXIS_Y): skin, fat and muscle shell
# on one ray share the weight; the fade toward the axis keeps the spine, cord and deep vessels on the
# neck bone.
JAW_THROAT = {"z_m": (1.545, 1.575), "sector_deg": (55.0, 95.0), "axis_r_m": (0.030, 0.048),
              "neck_axis_y": 0.015}


def _throat(p):
    """Jaw share of the throat sheet (0..1) for body-frame points (see JAW_THROAT)."""
    c = JAW_THROAT
    dy = c["neck_axis_y"] - p[:, 1]
    r = np.hypot(p[:, 0], dy)
    psi = np.degrees(np.arctan2(np.abs(p[:, 0]), dy))
    return (_sstep(c["sector_deg"][1], c["sector_deg"][0], psi) * _sstep(c["axis_r_m"][0], c["axis_r_m"][1], r)
            * _sstep(c["z_m"][0], c["z_m"][1], p[:, 2]))


# Layers that ride on the skin surface (the throat sheet and the 12-22 mm mandible band apply to them).
# Every deeper layer (bone, organs, vessels, nerves, cord, brain) never takes the throat sheet and joins
# the jaw only within 2-6 mm of the mandible: opening the mouth must not drag the larynx, the carotids,
# the IJV or the vertebral arteries out of the neck (they hang from the skull base and the spine).
SUPERFICIAL_LAYERS = ("skin", "cloth", "muscle", "hair", "eye", "eye_fx", "mouth")


def _head_jaw(p, g_axial, layer="skin"):
    """(head gate, jaw gate, throat sheet) inside the neck territory.

    The head gate is the axial gate (face, occiput, under the ears) united with the skin near the
    mandible (chin, jaw line: the mandible lies right under it, so it must go with the jaw); the jaw
    gate is the Voronoi cell of the head project's mandible against its skull (lower lip, chin,
    mouth floor, skin over the mandible -> jaw; upper lip, palate -> head).  The throat sheet moves
    the front of the neck part of the way with the jaw (``JAW_THROAT``)."""
    n = len(p)
    gh = np.array(g_axial, float, copy=True)
    gj = np.zeros(n)
    th = np.zeros(n)
    m = np.all((p >= _HJ_LO) & (p <= _HJ_HI), axis=1)
    if not m.any():
        return gh, gj, th
    skull, jaw = _head_sdfs()
    q = p[m]
    superficial = layer in SUPERFICIAL_LAYERS
    th[m] = _throat(q) if superficial else 0.0
    dj = jaw(q[:, 0], q[:, 1], q[:, 2])
    # the same 12-22 mm band around the mandible joins the HEAD for every layer (turning / nodding the head
    # moves the skin and what lies under it together); only superficial layers and deep points within
    # 2-6 mm of the bone also take the JAW share (opening the mouth moves the skin over the mandible, not
    # the vessels and glands under the jaw line)
    near = _sstep(MANDIBLE_NEAR[1], MANDIBLE_NEAR[0], dj)
    # ... but not below the jaw line: the submental skin under the mandible's inferior border (and the tissue
    # over the hyoid and larynx) is only STRETCHED by opening the mouth (throat sheet), it does not swing
    # back with the chin into the throat (the larynx then poked 3-12 mm through the skin in jaw_open)
    import body_skin as BS_
    clip = BS_.head_clip_z(q[:, 0], q[:, 1])
    near = near * _sstep(clip, clip + 0.008, q[:, 2])
    gh[m] = np.maximum(gh[m], near)
    ds = np.full(len(q), 1.0)
    need = gh[m] > 1e-6
    if need.any():
        qq = q[need]
        ds[need] = skull(qq[:, 0], qq[:, 1], qq[:, 2])
    gj[m] = _sstep(-0.004, 0.004, ds - dj)
    # the back of the mouth floor (tongue base, vallecula, oropharyngeal lining over the hyoid and epiglottis)
    # hangs from the hyoid, not the chin: it follows the jaw only 30 %, so a dropped jaw stretches the floor
    # instead of swinging it 2 cm down through the top of the larynx
    back = (_sstep(-0.052, -0.036, q[:, 1]) * _sstep(0.030, 0.018, np.abs(q[:, 0]))
            * _sstep(1.588, 1.576, q[:, 2]) * _sstep(1.536, 1.546, q[:, 2]))
    gj[m] *= 1.0 - 0.7 * back
    if not superficial:
        gj[m] *= _sstep(0.006, 0.002, dj)
    return gh, gj, th


def dense_weights(points, layer="skin"):
    """(N, 39) analytic weights before the 4-influence cut (rows sum to 1); ``layer`` only changes the
    jaw/throat share of deep layers (``SUPERFICIAL_LAYERS``)."""
    p = np.asarray(points, float).reshape(-1, 3)
    g = _gates()
    n = len(p)
    W = np.zeros((n, NB))
    pm = _mirror(p)
    # --- limb territories
    arm = {"L": g["shoulder"](p), "R": g["shoulder"](pm)}
    leg = {"L": g["hip"](p) * _sstep(0.002, 0.020, p[:, 0]),
           "R": g["hip"](pm) * _sstep(0.002, 0.020, pm[:, 0])}
    neck = g["neck"](p)
    S = arm["L"] + arm["R"] + leg["L"] + leg["R"] + neck
    sc = np.where(S > 1.0, 1.0 / np.maximum(S, 1e-12), 1.0)
    for d in (arm, leg):
        for k in d:
            d[k] = d[k] * sc
    neck = neck * sc
    S = np.minimum(S, 1.0)
    gird = {"L": _girdle(p) * (1.0 - S), "R": _girdle(pm) * (1.0 - S)}
    G = gird["L"] + gird["R"]
    scg = np.where(G > 1.0 - S, (1.0 - S) / np.maximum(G, 1e-12), 1.0)
    for k in gird:
        gird[k] = gird[k] * scg
    trunk = np.clip(1.0 - S - gird["L"] - gird["R"], 0.0, 1.0)
    # --- trunk chain
    gs, gc, gu = g["spine"](p), g["chest"](p), g["upper_chest"](p)
    for bone, val in (("hips", 1.0 - gs), ("spine", gs * (1.0 - gc)), ("chest", gs * gc * (1.0 - gu)),
                      ("upper_chest", gs * gc * gu)):
        W[:, BONE_INDEX[bone]] += trunk * val
    for side, q in (("L", p), ("R", pm)):
        W[:, BONE_INDEX["clavicle_" + side]] += gird[side]
        for base, val in _arm_split(q, g).items():
            W[:, BONE_INDEX[f"{base}_{side}"]] += arm[side] * val
        for base, val in _leg_split(q, g).items():
            W[:, BONE_INDEX[f"{base}_{side}"]] += leg[side] * val
    # --- neck, head, jaw
    gh, gj, th = _head_jaw(p, g["head"](p), layer)
    W[:, BONE_INDEX["neck"]] += neck * (1.0 - gh) * (1.0 - th)
    W[:, BONE_INDEX["head"]] += neck * gh * (1.0 - gj)
    W[:, BONE_INDEX["jaw"]] += neck * (gh * gj + (1.0 - gh) * th)
    W = np.clip(W, 0.0, None)
    W /= np.maximum(W.sum(1, keepdims=True), 1e-12)
    return W


def _top4(W):
    idx = np.argsort(-W, axis=1, kind="stable")[:, :MAX_INF].astype(np.int32)
    w = np.take_along_axis(W, idx, axis=1)
    w /= np.maximum(w.sum(1, keepdims=True), 1e-12)
    return idx, w


def weights_at(points, layer="skin", frame="final"):
    """Analytic skin weights for body-frame rest points (plan D8: every layer uses this).

    Returns ``(idx, w)`` with shapes (N, 4): bone indices into ``BONE_NAMES`` and weights on a
    1/4096 grid that sum exactly to 1 (unused slots: weight 0).  The lid regions of B2's face
    rig are part of the function.  ``layer="head_rigid"`` gives 100 % head (kept for callers
    that need a rigid head attachment); every other layer uses the shared function, where deep
    layers (not in ``SUPERFICIAL_LAYERS``) skip the throat sheet and the wide mandible band."""
    p = np.asarray(points, dtype=float).reshape(-1, 3)
    n = len(p)
    if n == 0:
        return np.zeros((0, 4), np.int32), np.zeros((0, 4))
    # rest points arrive in the final frame (neck lengthened); the weight model is authored in the RB frame
    if frame == "final":
        p = gbc.unwarp_points(p)
    if layer == "head_rigid":
        return rigid_weights(n, "head")
    out_i = np.empty((n, MAX_INF), np.int32)
    out_w = np.empty((n, MAX_INF))
    chunk = 40000
    for s in range(0, n, chunk):
        q = p[s:s + chunk]
        idx, w = _top4(dense_weights(q, layer))
        idx, w = _face(q, idx, w)
        out_i[s:s + chunk] = idx
        out_w[s:s + chunk] = w
    return _quantise(out_i, out_w)


def _face(p, idx, w):
    """Blend B2's lid-bone weights in (only points near the eyes are touched)."""
    near = np.zeros(len(p), bool)
    for sx in (1.0, -1.0):
        c = np.array([sx * 0.032, -0.050, 1.669])
        near |= np.linalg.norm(p - c, axis=1) < 0.024
    if not near.any():
        return idx, w
    import head_integration as hi
    i2, w2 = hi.blend_face_weights(p[near], idx[near], w[near])
    idx = idx.copy()
    w = w.copy()
    idx[near] = i2
    w[near] = w2
    return idx, w


def _merge_duplicates(idx, w):
    """Sum the weights of a bone that appears in two slots of a row (keeps the first slot)."""
    idx = np.array(idx, np.int32, copy=True)
    w = np.array(w, float, copy=True)
    for a in range(idx.shape[1]):
        for b in range(a + 1, idx.shape[1]):
            dup = (idx[:, a] == idx[:, b]) & (w[:, b] > 0)
            if dup.any():
                w[dup, a] += w[dup, b]
                w[dup, b] = 0.0
    return idx, w


def _quantise(idx, w):
    """Snap weights to a 1/QUANT grid; the largest absorbs the remainder so rows sum exactly to 1."""
    idx, w = _merge_duplicates(idx, w)
    w = np.clip(w, 0.0, None)
    w = w / np.maximum(w.sum(axis=1, keepdims=True), 1e-12)
    q = np.floor(w * QUANT + 0.5)
    big = np.argmax(w, axis=1)
    rows = np.arange(len(w))
    q[rows, big] = 0
    q[rows, big] = QUANT - q.sum(axis=1)
    idx = np.where(q > 0, idx, idx[rows, big][:, None])
    return idx.astype(np.int32), q / QUANT


def rigid_weights(n, bone):
    """(idx, w) assigning all ``n`` points 100 % to ``bone``."""
    idx = np.zeros((n, 4), dtype=np.int32)
    w = np.zeros((n, 4), dtype=np.float64)
    idx[:, :] = BONE_INDEX[bone]
    w[:, 0] = 1.0
    return idx, w


# ===========================================================================
# Armature
# ===========================================================================
def build_armature():
    """Create ``GB_Armature`` (identity transform, 39 deform bones, A-pose bind) in GB_Rig."""
    gbc.collections()
    arm_data = bpy.data.armatures.get(gbc.ARMATURE)
    if arm_data is not None and arm_data.users == 0:
        bpy.data.armatures.remove(arm_data)
    arm_data = bpy.data.armatures.new(gbc.ARMATURE)
    arm = gbc.new_object(gbc.ARMATURE, arm_data)
    arm.show_in_front = True
    arm_data.display_type = 'STICK'
    view_layer = bpy.context.view_layer
    view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for b in bone_rows_frame("final"):
        eb = arm_data.edit_bones.new(b["name"])
        eb.head = Vector(b["head"])
        eb.tail = Vector(b["tail"])
        eb.use_deform = True
        eb.use_connect = False
        eb.align_roll(Vector(b["roll_align"]))
        if b["parent"]:
            eb.parent = ebs[b["parent"]]
        ebs[b["name"]] = eb
    bpy.ops.object.mode_set(mode='OBJECT')
    arm["gb_layer"] = "rig"
    arm["gb_schema"] = 1
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm


def ensure_armature_fit():
    """Rebuild GB_Armature if its bones differ from ``bone_rows`` (a cached/placeholder armature)."""
    arm = bpy.data.objects.get(gbc.ARMATURE)
    if arm is None:
        return build_armature(), True
    bm = bone_map()
    off = [b.name for b in arm.data.bones
           if (b.head_local - Vector(bm[b.name]["head"])).length > 1e-6
           or (b.tail_local - Vector(bm[b.name]["tail"])).length > 1e-6]
    if not off:
        return arm, False
    children = [o for o in bpy.data.objects if o.parent == arm]
    acts = {}
    bpy.data.objects.remove(arm, do_unlink=True)
    new = build_armature()
    for o in children:
        o.parent = new
        o.matrix_parent_inverse.identity()
        for m in o.modifiers:
            if m.type == 'ARMATURE':
                m.object = new
    _ = acts
    build_poses(new)
    return new, True


def rest_basis(arm, name):
    """Armature-space 3x3 rest basis of a bone (columns = local x, y, z in the body frame)."""
    return arm.data.bones[name].matrix_local.to_3x3()


# ===========================================================================
# Skinning
# ===========================================================================
_LAST = {}          # object name -> (idx, w) written by the last skin_object call (tests reuse it)


def assign_weights(obj, arm, idx, w):
    """Write (idx, w) into vertex groups of ``obj`` (one group per used bone)."""
    obj.vertex_groups.clear()
    used = np.unique(idx[w > 0])
    groups = {int(b): obj.vertex_groups.new(name=BONE_NAMES[int(b)]) for b in used}
    for b, vg in groups.items():
        rows, cols = np.nonzero((idx == b) & (w > 0))
        vals = w[rows, cols]
        order = np.argsort(vals, kind="stable")
        vals_s, rows_s = vals[order], rows[order]
        cuts = np.flatnonzero(np.diff(vals_s)) + 1
        for grp_rows, grp_vals in zip(np.split(rows_s, cuts), np.split(vals_s, cuts)):
            if len(grp_rows):
                vg.add(grp_rows.tolist(), float(grp_vals[0]), 'REPLACE')


def read_weights(obj):
    """(idx[N,4], w[N,4]) from the vertex groups of ``obj`` (bone indices into BONE_NAMES)."""
    if obj.name in _LAST and len(_LAST[obj.name][0]) == len(obj.data.vertices):
        return _LAST[obj.name]
    gmap = {g.index: BONE_INDEX.get(g.name, -1) for g in obj.vertex_groups}
    n = len(obj.data.vertices)
    idx = np.zeros((n, 4), np.int32)
    w = np.zeros((n, 4))
    for v in obj.data.vertices:
        gs = sorted(((g.weight, gmap[g.group]) for g in v.groups if g.weight > 0), reverse=True)[:4]
        for k, (wt, b) in enumerate(gs):
            idx[v.index, k] = b
            w[v.index, k] = wt
    return idx, w


# meshes whose vertices follow the skin at their anchors (B2's gb_anchor_x/y/z)
FOLLOWERS = ("GB_BrowLash", "GB_EyeFX_L", "GB_EyeFX_R")


# meshes whose weights are transferred from the nearest skin point: {name: (source skins, smoothing iterations)}.
# The shorts hang 1-3 cm off the thigh, so their own position can fall outside the thigh territory.  (The
# muscle shell was tried here too: nearest-point transfer mis-assigns it in the groin / perineum creases,
# where the nearest skin belongs to the other side of the crease; it keeps the analytic weights.)
TRANSFERRED = {"GB_Shorts": (("GB_Body",), 6), "GB_MuscleShell": (("GB_Body",), 2)}
# The muscle shell takes the skin weights at the skin point straight OUT along its own normal (fix round 2): its
# analytic weights differed from the skin above it by up to 0.4 (L1) at the axillary folds and the sole, so in
# shoulder abduction / toe extension the shell slid 3-7 mm out through the skin.  Casting along the normal
# (not the nearest skin point) keeps the groin / perineum creases on the correct side of the fold.
RAY_TRANSFER = ("GB_MuscleShell",)
RAY_TRANSFER_MAX = 0.060
TRANSFER_SMOOTH_ITERS = 6


def transfer_weights(obj, src_names=None, smooth_iters=None):
    """Skin-following weights: every vertex takes the analytic skin weights at its nearest point on the skin
    (not at its own position: a loose leg tube 1-3 cm off the thigh used to fall outside the thigh territory
    and stayed on the pelvis, so hip flexion tore the hem off), then (cloth) the dense weights are smoothed
    over the mesh's own edges so the leg opening and the crotch deform as one sheet."""
    cfg = TRANSFERRED.get(obj.name, (("GB_Body",), TRANSFER_SMOOTH_ITERS))
    src_names = cfg[0] if src_names is None else src_names
    smooth_iters = cfg[1] if smooth_iters is None else smooth_iters
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    V, T = [], []
    off = 0
    for n in src_names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        v, t = gbc.mesh_arrays(o.data)
        V.append(v)
        T.append(t + off)
        off += len(v)
    me = obj.data
    pv = gbc.get_verts(me)
    if not V:
        return weights_at(pv)
    bvh = BVHTree.FromPolygons(np.vstack(V).tolist(), np.vstack(T).tolist())
    near = np.array([tuple(bvh.find_nearest(Vector(p))[0]) for p in pv])
    if obj.name in RAY_TRANSFER:
        vn = np.empty(len(pv) * 3)
        me.vertex_normals.foreach_get("vector", vn)
        vn = vn.reshape(-1, 3)
        for i, (p, n) in enumerate(zip(pv, vn)):
            hit = bvh.ray_cast(Vector(p), Vector(n), RAY_TRANSFER_MAX)
            if hit[0] is not None:
                near[i] = tuple(hit[0])
    W = np.zeros((len(pv), NB))
    near = gbc.unwarp_points(near)                  # final frame -> the weight model's authoring frame
    for s0 in range(0, len(pv), 40000):
        W[s0:s0 + 40000] = dense_weights(near[s0:s0 + 40000], "skin")
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ev)
    e = ev.reshape(-1, 2)
    deg = np.maximum(np.bincount(e.ravel(), minlength=len(pv)).astype(float), 1.0)[:, None]
    for _ in range(smooth_iters):
        acc = np.zeros_like(W)
        np.add.at(acc, e[:, 0], W[e[:, 1]])
        np.add.at(acc, e[:, 1], W[e[:, 0]])
        W = 0.5 * W + 0.5 * acc / deg
    W /= np.maximum(W.sum(1, keepdims=True), 1e-12)
    return _quantise(*_top4(W))


def object_weights(obj, layer="skin"):
    """(idx, w) for a mesh: rigid parts (``gb_rigid_bone``), followers (skin anchors), cloth transferred from
    the body skin (``TRANSFERRED``) or analytic."""
    n = len(obj.data.vertices)
    if obj.name in TRANSFERRED:
        return transfer_weights(obj)
    if obj.name in FOLLOWERS and _has_anchors(obj):
        # B2 followers: the weights of the skin at each vertex's anchor (weights_at includes the lid regions,
        # so this is head_integration.follower_weights without blending the lids in twice)
        a = np.stack([gbc.read_point_attr(obj, "gb_anchor_" + c, 'FLOAT') for c in "xyz"], 1).astype(float)
        return weights_at(a)
    rigid = gbc.read_point_attr(obj, "gb_rigid_bone", 'INT')
    if rigid is not None and np.all(rigid >= 0):
        idx = np.repeat(rigid.astype(np.int32)[:, None], 4, axis=1)
        w = np.zeros((n, 4))
        w[:, 0] = 1.0
        return idx, w
    v = gbc.get_verts(obj.data)
    idx, w = weights_at(v, layer=layer)
    if rigid is not None:
        m = rigid >= 0
        if m.any():
            idx[m] = rigid[m, None]
            w[m] = 0.0
            w[m, 0] = 1.0
    return idx, w


def _has_anchors(obj):
    return all(gbc.read_point_attr(obj, "gb_anchor_" + c, 'FLOAT') is not None for c in "xyz")


def skin_object(obj, arm, layer="skin"):
    """Parent to the armature (OBJECT), weight every vertex, add the single ARMATURE modifier."""
    idx, w = object_weights(obj, layer)
    assign_weights(obj, arm, idx, w)
    _LAST[obj.name] = (idx, w)
    for mod in list(obj.modifiers):
        obj.modifiers.remove(mod)
    obj.parent = arm
    obj.parent_type = 'OBJECT'
    obj.matrix_parent_inverse.identity()
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    mod.use_vertex_groups = True
    mod.use_bone_envelopes = False
    mod.use_deform_preserve_volume = False          # Godot skins linearly: preview exactly that
    return idx, w


SKIN_LAYER = {}      # per-object layer override (none: every layer uses the shared function)


def skin_all(objs):
    """Skin every exported mesh in ``objs`` (dict name -> object) to ``GB_Armature``.

    Also brings the armature to the B6 bone fits (a placeholder/cached armature is rebuilt)."""
    arm, _rebuilt = ensure_armature_fit()
    for name, obj in objs.items():
        if obj is None or obj.type != 'MESH':
            continue
        skin_object(obj, arm, SKIN_LAYER.get(name, gbc.LAYER_OF.get(name, "skin")))
    return arm


# ===========================================================================
# Posing (shared by the key poses, the deformation tests and rig.json)
# ===========================================================================
# kinematic bones: rotation axes resolved like the physical joints (approx axis, probe, toward, pos, neg)
KIN_TEMPLATES = {
    "fingers": {"flex": ((0.0, 1.0, 0.0), "tail", tuple(ARM_MED), "grip", "open")},
    "thumb": {"flex": ((0.0, 0.0, 1.0), "tail", tuple(ARM_MED), "grip", "open"),
              "abd": (tuple(ARM_MED), "tail", (0.0, -1.0, 0.0), "abd", "add")},
    "toes": {"flex": ((-1.0, 0.0, 0.0), "tail", (0.0, 0.0, -1.0), "flex", "ext")},
    "upper_arm_twist": {"twist": ("bone", (0.0, -0.05, 0.0), tuple(ARM_LAT), "rot_ext", "rot_int")},
    "forearm_twist": {"twist": ("bone", tuple(0.03 * ARM_MED), (0.0, -1.0, 0.0), "sup", "pron")},
}
KIN_LIMITS = {   # degrees about the resolved axes (K: typical adult active ranges, relaxed-curl mesh)
    "fingers": {"flex": [-15.0, 85.0]}, "thumb": {"flex": [-15.0, 50.0], "abd": [-10.0, 45.0]},
    "toes": {"flex": [-40.0, 30.0]},
}


def resolve_axes_rows(bone, template):
    """``rig_table.resolve_axes`` on the B6 bone rows (fitted thumb/jaw)."""
    b = bone_map()[bone]
    head, tail = np.array(b["head"], float), np.array(b["tail"], float)
    t = _unit(tail - head)
    right = bone.endswith("_R")
    out, used = {}, []
    for name, (approx, probe, toward, pos, neg) in template.items():
        toward = np.array(toward, float) * (np.array([-1.0, 1.0, 1.0]) if right else 1.0)
        if isinstance(approx, str):
            a = t.copy() if approx == "bone" else -t
        else:
            a = np.array(approx, float) * (np.array([-1.0, 1.0, 1.0]) if right else 1.0)
            a = a - (a @ t) * t
            for u in used:
                a = a - (a @ u) * u
            a = _unit(a)
            used.append(a)
        if isinstance(probe, str):
            pnt = tail
        else:
            off = np.array(probe, float) * (np.array([-1.0, 1.0, 1.0]) if right else 1.0)
            pnt = head + off
        if np.cross(a, pnt - head) @ toward < 0:
            a = -a
        out[name] = {"world": [float(x) for x in a], "sign": 1, "pos": pos, "neg": neg}
    return out


_AXES = None


def world_axes():
    """{bone: {axis: world unit vector}} for every physical joint and every kinematic bone."""
    global _AXES
    if _AXES is None:
        out = {}
        for row in RT.bodies():
            if row["joint"]:
                out[row["bone"]] = {k: np.array(v["world"]) for k, v in row["joint"]["axes"].items()}
        for side in ("L", "R"):
            for base, tpl in KIN_TEMPLATES.items():
                out[f"{base}_{side}"] = {k: np.array(v["world"]) for k, v in
                                         resolve_axes_rows(f"{base}_{side}", tpl).items()}
        out["jaw"] = {"open": np.array([1.0, 0.0, 0.0])}
        _AXES = out
    return _AXES


def _local_quat(arm, bone, world_axis, deg):
    """Pose-bone quaternion that rotates about a rest-pose world axis by ``deg``."""
    m = rest_basis(arm, bone)
    ax_local = m.inverted() @ Vector(world_axis)
    return Quaternion(ax_local.normalized(), math.radians(deg))


def expand_pose(pose):
    """``{"forearm": [("flex", 90)]}`` (base names = both sides) -> per-bone entries."""
    out = {}
    for key, rots in pose.items():
        if key.startswith("_"):
            continue
        names = [key] if key in BONE_INDEX else [f"{key}_L", f"{key}_R"]
        for n in names:
            out.setdefault(n, []).extend(rots)
    return out


def apply_pose(arm, pose, twist_drivers=True):
    """Set pose-bone rotations from a joint-angle pose (rotations about resolved world axes).

    ``pose``: {bone or base name: [(axis, deg), ...], "_hips_loc": (x, y, z)}.  Rotations of one
    bone compose in list order.  With ``twist_drivers`` the twist bones follow their drivers
    (plan: upper_arm_twist -50 % of the shoulder twist, forearm_twist +50 % of the hand twist)."""
    axes = world_axes()
    per = expand_pose(pose)
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
        pb.rotation_quaternion = Quaternion()
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    for bone, rots in per.items():
        pb = arm.pose.bones[bone]
        q = Quaternion()
        for axis, deg in rots:
            q = _local_quat(arm, bone, axes[bone][axis], deg) @ q
        pb.rotation_quaternion = q
    if twist_drivers:
        for side in ("L", "R"):
            for tw_bone, src, axis, factor in TWIST_DRIVERS:
                tb, sb = f"{tw_bone}_{side}", f"{src}_{side}"
                ang = twist_angle(arm, sb, axes[sb][axis])
                if abs(ang) > 1e-9:
                    arm.pose.bones[tb].rotation_quaternion = _local_quat(arm, tb, axes[tb]["twist"],
                                                                          math.degrees(factor * ang))
    jaw_open = sum(deg for axis, deg in per.get("jaw", []) if axis == "open")
    if jaw_open > 0.0:
        pb = arm.pose.bones["jaw"]
        m = arm.data.bones["jaw"].matrix_local.to_3x3()
        pb.location = m.inverted() @ Vector(jaw_glide(jaw_open))
    if "_hips_loc" in pose:
        pb = arm.pose.bones["hips"]
        m = arm.data.bones["hips"].matrix_local.to_3x3()
        pb.location = m.inverted() @ Vector(pose["_hips_loc"])
    bpy.context.view_layer.update()


# TMJ glide (K: the condyle slides forward and down the articular eminence as the mouth opens: about
# 15-20 mm at a full 45-50 mm opening, less early in the opening).  Without it a pure hinge swings the
# chin straight back into the throat.  Body-frame metres per degree of "open"; closing (< 0) has none.
JAW_GLIDE_M_PER_DEG = (0.0, -0.00045, -0.00025)


def jaw_glide(open_deg):
    """Jaw bone translation (body frame, m) for an opening angle in degrees (rig.json kinematic.jaw)."""
    k = max(float(open_deg), 0.0)
    return tuple(c * k for c in JAW_GLIDE_M_PER_DEG)


# (twist bone, driver source bone, source axis, factor): twist bone local rotation about its own
# twist axis = factor x the source bone's twist angle about that axis (swing-twist decomposition)
TWIST_DRIVERS = (("upper_arm_twist", "upper_arm", "twist", -0.5), ("forearm_twist", "hand", "twist", 0.5))


def twist_angle(arm, bone, world_axis):
    """Twist angle (rad) of a pose bone's local rotation about a rest-pose world axis."""
    pb = arm.pose.bones[bone]
    q = pb.rotation_quaternion
    m = rest_basis(arm, bone)
    ax = (m.inverted() @ Vector(world_axis)).normalized()
    proj = Vector((q.x, q.y, q.z)).dot(ax)
    tw = Quaternion((q.w, *(ax * proj)))
    if tw.magnitude < 1e-12:
        return 0.0
    tw.normalize()
    ang = 2.0 * math.atan2(Vector((tw.x, tw.y, tw.z)).dot(ax), tw.w)
    return (ang + math.pi) % (2.0 * math.pi) - math.pi


def pose_matrices(arm, pose=None):
    """(39, 4, 4) skinning matrices (posed armature-space bone matrix x rest inverse), rig order.

    With ``pose`` the armature is posed first (``apply_pose``); without, the current pose is used."""
    if pose is not None:
        apply_pose(arm, pose)
    mats = np.zeros((NB, 4, 4))
    for i, n in enumerate(BONE_NAMES):
        pb = arm.pose.bones[n]
        mats[i] = np.array(pb.matrix @ arm.data.bones[n].matrix_local.inverted())
    return mats


def lbs(points, idx, w, mats):
    """Linear blend skinning of rest points (what Godot's skinning computes)."""
    p = np.asarray(points, float)
    ph = np.concatenate([p, np.ones((len(p), 1))], 1)
    M = np.einsum("nk,nkij->nij", w, mats[idx])
    return np.einsum("nij,nj->ni", M, ph)[:, :3]


def reset_pose(arm):
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    bpy.context.view_layer.update()


# ===========================================================================
# Key poses (single-frame actions; G5 adds procedural motion in Godot)
# ===========================================================================
# Joint angles about the resolved world axes (E, checked in renders).  Bent knees drop and move the
# hips so both feet stay planted (``_plant_feet``).
POSES = {
    # relaxed standing: arms hang close to the body (A-pose 30 deg -> ~10 deg), soft elbows and knees
    "pose_idle": {"upper_arm": [("abd", -19.0), ("flex", 4.0)], "forearm": [("flex", 14.0)],
                  "hand": [("flex", 6.0)], "fingers": [("flex", 10.0)], "thumb": [("flex", 8.0)],
                  "shin": [("flex", 4.0)], "thigh": [("flex", 2.0)], "foot": [("flex", 2.0)],
                  "neck": [("flex", 3.0)]},
    # defensive guard: forearms up in front of the face, fists half closed, chin tucked, knees soft
    "pose_guard": {"upper_arm": [("abd", -28.0), ("flex", 40.0), ("twist", 4.0)],
                   "forearm": [("flex", 125.0)], "hand": [("flex", 8.0)], "fingers": [("flex", 70.0)],
                   "thumb": [("flex", 35.0)], "clavicle": [("protr", 6.0)],
                   "neck": [("flex", 10.0)], "head": [("flex", 4.0)],
                   "upper_chest": [("flex", 4.0)], "thigh": [("flex", 10.0)], "shin": [("flex", 16.0)],
                   "foot": [("flex", 6.0)]},
    # cower: trunk curled, head ducked, forearms crossed over the head, knees bent
    "pose_cower": {"spine": [("flex", 16.0)], "chest": [("flex", 12.0)], "upper_chest": [("flex", 8.0)],
                   "neck": [("flex", 22.0)], "head": [("flex", 10.0)], "clavicle": [("protr", 10.0), ("elev", 8.0)],
                   "upper_arm": [("abd", -18.0), ("flex", 95.0), ("twist", -20.0)], "forearm": [("flex", 125.0)],
                   "hand": [("flex", 15.0)], "fingers": [("flex", 45.0)], "thumb": [("flex", 25.0)],
                   "thigh": [("flex", 34.0)], "shin": [("flex", 52.0)], "foot": [("flex", 18.0)]},
    # brace for impact / a fall: arms thrust forward, wrists extended (palms out), head back
    "pose_brace": {"upper_arm": [("abd", -16.0), ("flex", 75.0)], "forearm": [("flex", 12.0)],
                   "hand": [("flex", -50.0)], "fingers": [("flex", -12.0)], "thumb": [("abd", 20.0)],
                   "clavicle": [("protr", 10.0)], "spine": [("flex", 6.0)], "neck": [("flex", -10.0)],
                   "head": [("flex", -6.0)], "thigh": [("flex", 12.0)], "shin": [("flex", 22.0)],
                   "foot": [("flex", 10.0)]},
}


def _plant_feet(arm, pose, iters=4):
    """Hips translation that puts both ankles back on their rest position (bent-knee poses)."""
    bm = bone_map()
    rest = np.array([bm["foot_L"]["head"], bm["foot_R"]["head"]], float)
    loc = np.zeros(3)
    for _ in range(iters):
        apply_pose(arm, dict(pose, _hips_loc=tuple(loc)))
        now = np.array([np.array(arm.pose.bones["foot_L"].head), np.array(arm.pose.bones["foot_R"].head)])
        loc += (rest - now).mean(0)
    return tuple(float(c) for c in loc)


def build_poses(arm):
    """Create the single-frame key-pose actions (plan §5.6) on ``arm``; leaves the rest pose active."""
    arm.animation_data_create()
    solved = {}
    for name in gbc.POSE_ACTIONS:
        old = bpy.data.actions.get(name)
        if old is not None:
            bpy.data.actions.remove(old)
        pose = dict(POSES[name])
        pose["_hips_loc"] = _plant_feet(arm, pose)
        solved[name] = pose
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm.animation_data.action = act
        apply_pose(arm, pose)
        for pb in arm.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=1)
            if pb.name == "hips":
                pb.keyframe_insert("location", frame=1)
    arm.animation_data.action = None
    reset_pose(arm)
    arm["gb_pose_hips_loc"] = {k: list(v["_hips_loc"]) for k, v in solved.items()}
    return [bpy.data.actions[n] for n in gbc.POSE_ACTIONS]


# ===========================================================================
# rig.json payload (plan §5.8)
# ===========================================================================
# directional torque caps: strongest anatomical direction at the top of the plan's range, weakest at
# the bottom (K: isometric peak-torque ratios of adult males; magnitudes stay in the plan §3.1.2 range;
# where the plan gives one E value (chest 150, upper_chest 100) the split stays within +-7 % of it)
CAP_SPLIT = {
    "spine": {"flex": 230, "ext": 300, "lat_L": 220, "lat_R": 220, "rot_L": 200, "rot_R": 200},
    "chest": {"flex": 140, "ext": 160, "lat_L": 150, "lat_R": 150, "rot_L": 150, "rot_R": 150},
    "upper_chest": {"flex": 95, "ext": 105, "lat_L": 100, "lat_R": 100, "rot_L": 100, "rot_R": 100},
    "neck": {"flex": 25, "ext": 40, "lat_L": 28, "lat_R": 28, "rot_L": 20, "rot_R": 20},
    "head": {"flex": 20, "ext": 34, "lat_L": 22, "lat_R": 22, "rot_L": 20, "rot_R": 20},
    "clavicle": {"elev": 40, "depr": 40, "protr": 40, "retr": 40, "roll_fwd": 40, "roll_back": 40},
    "upper_arm": {"flex": 75, "ext": 90, "abd": 70, "add": 100, "rot_int": 65, "rot_ext": 60},
    "forearm": {"flex": 75, "ext": 52},
    "hand": {"flex": 15, "ext": 10, "rad": 12, "uln": 11, "sup": 9, "pron": 9},
    "thigh": {"flex": 220, "ext": 300, "abd": 210, "add": 230, "rot_int": 200, "rot_ext": 200},
    "shin": {"flex": 200, "ext": 250},
    "foot": {"dorsi": 100, "plantar": 150, "inv": 100, "ev": 100, "abd": 100, "add": 100},
}


def _bodies_table():
    out = []
    for row in RT.bodies():
        row = dict(row)
        j = row["joint"]
        if j:
            j = dict(j)
            base = row["bone"][:-2] if row["bone"].endswith(("_L", "_R")) else row["bone"]
            split = CAP_SPLIT.get(base)
            if split:
                j["torque_cap_nm"] = {k: float(split.get(k, j["torque_cap_nm"][k])) for k in j["torque_cap_nm"]}
                j["torque_cap_tag"] = ("K: directional split (strongest anatomical direction at the top of the "
                                       "plan range, weakest at the bottom); E magnitudes")
            row["joint"] = j
        out.append(row)
    return out


def _kinematic_table():
    """Kinematic bones: axes, ranges, twist drivers, myotomes (plan §3.1.1 'kinematic' rows)."""
    out = {}
    for side in ("L", "R"):
        for base, tpl in KIN_TEMPLATES.items():
            bone = f"{base}_{side}"
            row = {"axes": resolve_axes_rows(bone, tpl)}
            if base in KIN_LIMITS:
                row["limits_deg"] = KIN_LIMITS[base]
            myo = MYO.myotomes_for(base)
            if myo:
                row["myotomes"] = myo
            out[bone] = row
        for tw_bone, src, axis, factor in TWIST_DRIVERS:
            out[f"{tw_bone}_{side}"]["driver"] = {
                "source": f"{src}_{side}", "component": "twist", "source_axis": axis, "factor": factor,
                "rule": "swing-twist decompose the source bone's local rotation about its rest twist axis "
                        "(axes.twist of the source joint, world at rest); set this bone's local rotation to "
                        "factor x that twist angle about its own axes.twist"}
    out["upper_arm_twist_L"]["note"] = out["upper_arm_twist_R"]["note"] = (
        "carries the proximal upper arm; world twist = 50 % of the shoulder twist (skin twists 0/50/100 %)")
    out["forearm_twist_L"]["note"] = out["forearm_twist_R"]["note"] = (
        "carries the mid/distal forearm; 50 % of the hand's pronation/supination (the hand body folds "
        "forearm rotation into its twist axis)")
    out["toes_L"]["note"] = out["toes_R"]["note"] = "kinematic toe curl/extension (EHL L5, FHL S1-S2)"
    out["jaw"] = {"axes": {"open": {"world": [1.0, 0.0, 0.0], "sign": 1, "pos": "open", "neg": "close"}},
                  "limits_deg": {"open": [-2.0, 26.0]},
                  "glide_m_per_deg": list(JAW_GLIDE_M_PER_DEG),
                  "rule": "open = rotation about axes.open.world through the bone head (TMJ hinge) PLUS a "
                          "bone translation of glide_m_per_deg x max(open, 0) in body-frame metres (condyle "
                          "sliding down the articular eminence); the weights assume both",
                  "note": "hinge about +X through the TMJ pivot (bone head, B2 measured); see face.jaw_*"}
    out["tongue"] = {"note": "child of jaw; falls back at death (G6)", "limits_deg": {"flex": [-15.0, 15.0]}}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        out[f"eye_{side}"] = {"axes": {"yaw": {"world": [0.0, 0.0, 1.0], "sign": 1, "pos": "look_left",
                                              "neg": "look_right"},
                                      "pitch": {"world": [-1.0, 0.0, 0.0], "sign": 1, "pos": "look_up",
                                                "neg": "look_down"}},
                              "limits_deg": {"yaw": [-40.0, 40.0], "pitch": [-40.0, 30.0]},
                              "note": "gaze = bone -Y (body frame); B2: clamp beyond ~30 deg near the corners"}
        for lid in ("upper", "lower"):
            out[f"lid_{lid}_{side}"] = {"note": "rotation about +X through the eyeball centre plus the uniform "
                                                "scale of face.lid_table (B2)"}
    return out


def weight_model_table():
    """rig.json 'weights': a readable summary of the weight model (numbers used by the gates)."""
    g = _gates()
    rows = {}
    for k in ("shoulder", "elbow", "wrist", "hip", "knee", "ankle", "toes", "neck", "head", "spine", "chest",
              "upper_chest"):
        G = g[k]
        unit = "deg (elevation angle from the joint centre)" if G.mode == "ray" else "m (axial)"
        rows[k] = {"joint": G.J.tolist(), "axis": G.u.tolist(), "phi0": G.e0.tolist(), "phi90": G.e1.tolist(),
                   "mode": G.mode, "unit": unit, "r0_m": G.r0 if G.mode == "ray" else None,
                   "offset": list(G.o), "half_width": list(G.w), "offset_axis": G.o_axis,
                   "half_width_axis": G.w_axis, "axis_fade_r_m": list(G.r_att)}
    return {"model": "territories + joint gates (rig.py module doc)", "influences": MAX_INF, "grid": QUANT,
            "limb_radius_m": R_J, "gates": rows,
            "twist_handover_m": {"upper_arm": [0.10, 0.20], "forearm_from_elbow": [0.03, 0.14]},
            "jaw": "Voronoi mandible vs skull (head project SDFs), +-4 mm blend; throat sheet JAW_THROAT",
            "jaw_throat": {k: list(v) if isinstance(v, tuple) else v for k, v in JAW_THROAT.items()},
            "head_near_mandible_m": list(MANDIBLE_NEAR),
            "lids": "head_integration.face_weights (B2)",
            "followers": list(FOLLOWERS)}


def rig_table():
    """rig.json 'data': bones, bodies (directional caps), kinematic bones, face (B2), weight model."""
    arm = bpy.data.objects.get(gbc.ARMATURE)
    physical = {b["bone"] for b in RT.bodies()}
    bones = []
    for b in bone_rows():                      # authoring frame: export.write_sidecars warps every point
        row = {"name": b["name"], "parent": b["parent"], "head": list(b["head"]), "tail": list(b["tail"]),
               "deform": True, "physical": b["name"] in physical, "kinematic": b["kinematic"]}
        if arm is not None and b["name"] in arm.data.bones:
            m = rest_basis(arm, b["name"])
            row["rest_basis_world"] = {"x": list(m.col[0]), "y": list(m.col[1]), "z": list(m.col[2])}
        if b["note"]:
            row["note"] = b["note"]
        bones.append(row)
    try:
        import head_integration as hi
        face = hi.face_rig_table(None)
    except Exception as exc:                                          # pragma: no cover
        face = {"status": f"face table unavailable: {exc}"}
    face = dict(face)
    face.setdefault("blend_shapes", list(gbc.FACE_SHAPE_KEYS))
    face["jaw_bone_head"] = list(bone_map("authoring")["jaw"]["head"])
    kin = {}
    for n in ("forearm_twist", "fingers", "thumb", "toes"):
        kin[n] = {k: v for k, v in MYO.myotomes_for(n).items()}
    hips_loc = dict(arm.get("gb_pose_hips_loc", {})) if arm is not None else {}
    return {"bones": bones, "bodies": _bodies_table(), "kinematic": _kinematic_table(), "face": face,
            "kinematic_myotomes": kin,
            "poses": {n: {"joint_angles_deg": {k: [list(r) for r in v] for k, v in POSES[n].items()},
                          "hips_location_m": [round(float(c), 5) for c in hips_loc.get(n, (0.0, 0.0, 0.0))]}
                      for n in gbc.POSE_ACTIONS},
            "friction": RT.FRICTION, "weights": weight_model_table(),
            "notes": {"limits": "degrees about axes[*].world; positive = axes[*].pos direction",
                      "torque_cap_nm": "per direction key, before tone/paralysis multipliers (plan §3.2)",
                      "b2g": "Godot = (x, z, -y) of every vector here",
                      "twist_bones": "drive kinematic.*_twist_*.driver every frame, else they carry 100 % of the "
                                     "twist like their parent (no candy-wrap relief)"}}


if __name__ == "__main__":
    gbc.reset_scene()
    arm = build_armature()
    build_poses(arm)
    print(f"{len(arm.data.bones)} bones; actions: {[a.name for a in bpy.data.actions]}")
