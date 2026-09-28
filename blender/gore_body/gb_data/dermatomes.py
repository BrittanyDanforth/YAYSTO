"""Dermatome codes (plan §5.5) and anchors (R04 §6.2, C32/K).

Codes: 0 cranial (CN V), 1 C2 ... 7 C8, 8 T1 ... 19 T12, 20 L1 ... 24 L5,
25 S1, 26 S2, 27 S3, 28 S4-5.  Anchors are the clinical "no reaction below
here" points; boundaries between anchors are interpolated (K).  B1's
``paint_codes`` computes the final per-vertex map; ``dermatome_v0`` is B0's
coarse rule used by the placeholder so the code pipeline (UV2, codes.json,
FB-15) can be tested end to end from day one.
"""
import numpy as np

DERMATOMES = {0: "CN_V"}
DERMATOMES.update({i: f"C{i + 1}" for i in range(1, 8)})            # 1 C2 ... 7 C8
DERMATOMES.update({8 + i: f"T{i + 1}" for i in range(12)})          # 8 T1 ... 19 T12
DERMATOMES.update({20 + i: f"L{i + 1}" for i in range(5)})          # 20 L1 ... 24 L5
DERMATOMES.update({25: "S1", 26: "S2", 27: "S3", 28: "S4-5"})
DERMATOME_ID = {v: k for k, v in DERMATOMES.items()}

# Anchors (R04 §6.2): name -> (dermatome, landmark or point, note)
ANCHORS = {
    "C4": ("top of the shoulder / clavicle", "ac_joint_L"),
    "C6": ("thumb", "thumb_tip_L"),
    "C7": ("middle finger", "fingertip3_L_apose"),
    "C8": ("little finger", "little_finger_tip_L"),
    "T4": ("nipple line", "nipple_L"),
    "T6": ("xiphoid", "xiphoid_tip"),
    "T10": ("umbilicus", "navel"),
    "T12": ("groin", "mid_inguinal_point_L"),
    "L4": ("medial ankle", "medial_malleolus_L"),
    "L5": ("top (dorsum) of the foot", "foot_dorsum_L"),
    "S1": ("lateral foot and heel", "heel_L"),
    "S4-5": ("perianal", "crotch"),
}
# anchor points not in the landmark table (E, fit B0)
EXTRA_POINTS = {
    "thumb_tip_L": (0.500, -0.030, 0.840),          # thumb bone tail (rig table)
    "little_finger_tip_L": (0.545, 0.050, 0.785),
    "foot_dorsum_L": (0.110, -0.040, 0.060),
}

# Trunk dermatome levels at the front midline (z of the anchor band centres, E/K):
TRUNK_FRONT_Z = [(1.455, "T2"), (1.300, "T4"), (1.273, "T6"), (1.075, "T10"), (0.940, "T12"), (0.900, "L1")]
# Back: dermatomes run roughly horizontally, ~1 vertebral level lower laterally (K); use spinous heights
TRUNK_BACK_Z = [(1.532, "C7"), (1.481, "T1"), (1.420, "T4"), (1.353, "T7"), (1.280, "T10"), (1.227, "T12"),
                (1.160, "L2"), (1.087, "L4"), (1.012, "S1"), (0.950, "S3")]


def _interp_level(z, table):
    """Interpolate a dermatome code along a (z, name) table sorted by decreasing z."""
    zs = np.array([t[0] for t in table])[::-1]
    codes = np.array([DERMATOME_ID[t[1]] for t in table], dtype=float)[::-1]
    return np.rint(np.interp(z, zs, codes)).astype(int)


def dermatome_v0(points, segment_names):
    """Coarse per-point dermatome codes (B0 placeholder rule; B1 replaces it).

    ``points``: (N, 3) body-frame positions; ``segment_names``: per-point skin
    segment names from ``segments.BONE_SEGMENT``.  Rules (K): head/face -> CN V
    (0) above the jaw line, C2-C3 on the neck; trunk by height (front and back
    tables); arm: C4 shoulder cap -> C5 lateral arm -> C6 radial forearm/thumb,
    C7 middle finger, C8 ulnar hand, T1 medial forearm, T2 medial arm; leg:
    L1-L3 front of thigh, L4 medial shin/ankle, L5 lateral shin and dorsum,
    S1 heel/lateral foot/calf back, S2 back of thigh, S3/S4-5 perineum."""
    p = np.asarray(points, dtype=float)
    seg = np.asarray(segment_names)
    out = np.zeros(len(p), dtype=int)
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)

    head = seg == "head_neck"
    face = head & (z > 1.560)
    out[face] = DERMATOME_ID["CN_V"]
    neck = head & ~face
    out[neck] = np.where(z[neck] > 1.520, DERMATOME_ID["C2"], DERMATOME_ID["C3"])
    # back of the head/upper neck is C2
    occ = head & (y > 0.04) & (z < 1.70)
    out[occ] = DERMATOME_ID["C2"]

    torso = (seg == "torso") | (seg == "shorts")
    front = torso & (y < 0.0)
    back = torso & ~front
    out[front] = _interp_level(z[front], TRUNK_FRONT_Z)
    out[back] = _interp_level(z[back], TRUNK_BACK_Z)
    # shoulder cap and the top of the trapezius: C4
    cap = torso & (z > 1.44)
    out[cap] = DERMATOME_ID["C4"]
    # perineum / buttock cleft
    per = torso & (z < 0.905) & (ax < 0.035)
    out[per] = DERMATOME_ID["S4-5"]

    arm = np.isin(seg, ["arm_L", "arm_R", "hand_L", "hand_R"])
    if arm.any():
        d = np.array([0.5, 0.0, -0.8660254])
        sx = np.sign(x[arm])
        local = np.stack([ax[arm] - 0.180, y[arm] - 0.020, z[arm] - 1.415], axis=1)
        t = local @ d                                      # distance along the arm from the shoulder
        nm = np.array([-0.8660254, 0.0, -0.5])
        medial = local @ nm                                 # >0 on the palm/medial side
        ant = -(local[:, 1])                                # >0 on the anterior (radial) side
        code = np.full(arm.sum(), DERMATOME_ID["C5"])
        code[t < 0.03] = DERMATOME_ID["C4"]
        forearm = (t >= 0.29)
        code[forearm & (ant >= -0.005)] = DERMATOME_ID["C6"]
        code[forearm & (ant < -0.005)] = DERMATOME_ID["T1"]
        code[(t < 0.29) & (t >= 0.03) & (medial > 0.015)] = DERMATOME_ID["T2"]
        hand = t >= 0.56
        code[hand & (ant > 0.018)] = DERMATOME_ID["C6"]       # thumb side
        code[hand & (ant <= 0.018) & (ant >= -0.012)] = DERMATOME_ID["C7"]
        code[hand & (ant < -0.012)] = DERMATOME_ID["C8"]
        _ = sx
        out[arm] = code

    leg = np.isin(seg, ["leg_L", "leg_R", "foot_L", "foot_R"])
    if leg.any():
        lx, ly, lz = ax[leg], y[leg], z[leg]
        code = np.full(leg.sum(), DERMATOME_ID["L3"])
        code[(lz > 0.80) & (ly < 0.02)] = DERMATOME_ID["L1"]
        code[(lz <= 0.80) & (lz > 0.62) & (ly < 0.02)] = DERMATOME_ID["L2"]
        code[(lz > 0.50) & (ly >= 0.02)] = DERMATOME_ID["S2"]
        shin = (lz <= 0.50) & (lz > 0.10)
        code[shin & (lx < 0.090)] = DERMATOME_ID["L4"]
        code[shin & (lx >= 0.090)] = DERMATOME_ID["L5"]
        code[shin & (ly > 0.075)] = DERMATOME_ID["S1"]
        foot = lz <= 0.10
        code[foot] = DERMATOME_ID["L5"]
        code[foot & (lx < 0.085) & (ly > -0.02)] = DERMATOME_ID["L4"]
        code[foot & ((ly > 0.070) | (lx > 0.140))] = DERMATOME_ID["S1"]
        out[leg] = code
    return out
