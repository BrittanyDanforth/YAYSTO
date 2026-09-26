"""Vertebral column, spinal cord segments and brainstem (RB §7.3, §7.4, §4.6; R05 §4, §9).

``VERTEBRA_CSV`` is RB §7.3 verbatim (25 rows, C1-L5 and S1; x = 0; body
centres; ``cord_y`` = cord centre y; L2-S1 have no cord, only cauda equina).
Known fit conflict (RB §7.3): the ANSUR II cervicale skin bump (1.532) sits
~3 cm above the C7 body centre (1.500); expect +-2-3 cm in C4-T3 until a refit.
"""
import numpy as np

from .myotomes import CORD_SEGMENTS, CORD_INDEX

# level,y,z,body_h_mm,body_w_mm,body_d_mm,disc_below_mm,canal_ap_mm,canal_w_mm,spinous_dy_mm,cord_y,cord_w_mm,cord_ap_mm
VERTEBRA_CSV = """\
C1,0.020,1.610,10,78,45,0,30,28,30,0.024,11.5,8.5
C2,0.012,1.590,23,17,15.5,5,16,24,43,0.027,11.9,7.9
C3,0.007,1.570,14,16.5,15.5,5,14.5,23,40,0.023,12.5,8.0
C4,0.004,1.553,14,17.5,15.5,5,14,24,40,0.020,13.0,7.8
C5,0.003,1.536,13.5,18.5,16,5,14,24,42,0.019,13.5,7.7
C6,0.004,1.518,13.5,20,16.5,5,14,24,45,0.020,13.0,7.5
C7,0.010,1.500,15,22,16.5,5,14,23,57,0.026,12.0,7.5
T1,0.019,1.481,16,26,16.5,4.5,14,19,60,0.035,10.5,7.0
T2,0.028,1.461,17,27,17.5,4.5,14,17,60,0.044,9.0,6.5
T3,0.036,1.441,17.5,27,18.5,4.5,14,16,61,0.053,8.8,6.5
T4,0.042,1.420,18,27.5,20,5,13.5,15.5,62,0.060,8.5,6.5
T5,0.046,1.398,18.5,28.5,22,5,13.5,15.5,63,0.065,8.5,6.4
T6,0.049,1.376,19,30,24,5,13.5,15.5,64,0.069,8.3,6.4
T7,0.049,1.353,19.5,31,26,5,13.5,15.5,64,0.069,8.0,6.3
T8,0.046,1.329,20,32.5,27.5,5.5,14,16,63,0.067,8.0,6.3
T9,0.040,1.305,21,34,28.5,6,14,16,62,0.061,8.3,6.5
T10,0.031,1.280,22,37,29.5,6.5,14.5,17,62,0.053,8.5,7.0
T11,0.020,1.254,23,40,31,7,15,18,58,0.043,9.5,7.5
T12,0.008,1.227,24,42,32,8,16,21,58,0.031,10.0,8.0
L1,-0.004,1.197,25.5,43,33,10,17,22,68,0.021,8.0,7.0
L2,-0.013,1.161,26.5,45,34,11,17,23,70,0.013,0,0
L3,-0.018,1.124,27,48,35,12,16,23,70,0.008,0,0
L4,-0.016,1.087,27,50,35,12,16,24,70,0.011,0,0
L5,-0.005,1.050,26.5,52,35,11,17,26,65,0.022,0,0
S1,0.014,1.012,30,50,30,0,15,30,0,0.035,0,0
"""
_FIELDS = ("level", "y", "z", "body_h_mm", "body_w_mm", "body_d_mm", "disc_below_mm", "canal_ap_mm",
           "canal_w_mm", "spinous_dy_mm", "cord_y", "cord_w_mm", "cord_ap_mm")


def _parse():
    rows = []
    for line in VERTEBRA_CSV.strip().splitlines():
        parts = line.split(",")
        row = {"level": parts[0]}
        for k, v in zip(_FIELDS[1:], parts[1:]):
            row[k] = float(v)
        row["c"] = (0.0, row["y"], row["z"])
        rows.append(row)
    return rows


VERTEBRAE = _parse()
LEVELS = tuple(r["level"] for r in VERTEBRAE)
VERTEBRA = {r["level"]: r for r in VERTEBRAE}

# Curvatures (R05 §4.2, V ranges), surface levels (RB §7.3)
CURVATURE_DEG = {"cervical_lordosis": 30, "thoracic_kyphosis": 36, "lumbar_lordosis": 60, "pelvic_incidence": 53}
SURFACE_LEVELS = {"jugular_notch": "T2/T3", "sternal_angle": "T4/T5", "xiphisternum": "T9",
                  "subcostal_plane": "L3", "iliac_crests": "L4/L5", "navel": "L3/4-L4"}

# Sacrum and coccyx beyond S1 (R05 §4.3; E): the sacrum is one fused wedge, the coccyx a chain.
SACRUM = dict(top_c=(0.0, 0.014, 1.012), tip=(0.0, 0.050, 0.925), width_top_mm=100, tag="E (R05 §4.3)")
COCCYX_TIP = (0.0, 0.040, 0.905)             # R05 §1 row 44, L

# ---------------------------------------------------------------------------
# Spinal cord (RB §7.4, R05 §9): conus tip L1/L2, thecal sac to S2, cauda radius 7 mm.
# ---------------------------------------------------------------------------
CERVICOMEDULLARY_JUNCTION = (0.0, 0.030, 1.619)   # R05 §9.2 (corrected -0.008)
CONUS_TIP = (0.0, 0.017, 1.180)                   # L1/L2 disc [RB §7.4] V level
THECAL_END = (0.0, 0.035, 0.995)                  # S2
CAUDA_RADIUS = 0.007
CAUDA_CHAIN = [(0.000, 0.017, 1.180), (0.000, 0.013, 1.161), (0.000, 0.008, 1.124), (0.000, 0.011, 1.087),
               (0.000, 0.022, 1.050), (0.000, 0.035, 0.995)]   # RB §7.5 tube row
CORD_LENGTH_M = 0.45
CORD_COLOURS = {"white": "#EEE5D6", "grey_butterfly": "#B9A89E", "dura": "#D9D6CE"}
CORD_DEPTH_FROM_BACK_SKIN_MM = {"C5": 45, "T7": 53, "conus": 60}

# Continuous cord-segment coordinate s (0 = top of C1 at the cervicomedullary
# junction, k..k+1 = segment k, 30 = conus tip) at each vertebral body centre.
# Fit (E) of RB §4.6 offsets: cervical +1 (segment C(n+1) centred on vertebra Cn,
# reproducing the plan §5.8 example C6: z 1.545-1.527), upper thoracic +2,
# lower thoracic +3, T10 -> L1, T11 -> L2/L3, T12 -> L3-S1 midpoint, L1 -> S2-S5.
CORD_S_AT_VERTEBRA = {
    "C1": 1.5, "C2": 2.5, "C3": 3.5, "C4": 4.5, "C5": 5.5, "C6": 6.5, "C7": 7.5,
    "T1": 9.0, "T2": 10.5, "T3": 11.75, "T4": 13.0, "T5": 14.5, "T6": 15.75, "T7": 17.0,
    "T8": 18.25, "T9": 19.5, "T10": 20.5, "T11": 22.0, "T12": 24.0, "L1": 28.0,
}


def _s_to_z_table():
    zs = [CERVICOMEDULLARY_JUNCTION[2]] + [VERTEBRA[l]["z"] for l in CORD_S_AT_VERTEBRA] + [CONUS_TIP[2]]
    ss = [0.0] + list(CORD_S_AT_VERTEBRA.values()) + [30.0]
    return np.array(ss), np.array(zs)


def cord_z_at(s):
    """Body-frame z of cord coordinate ``s`` (piecewise linear through the anchors)."""
    ss, zs = _s_to_z_table()
    return float(np.interp(s, ss, zs))


def _cord_profile():
    """Cord centreline samples (z, y, half-width, half-AP) from the CMJ to the conus tip."""
    pts = [(CERVICOMEDULLARY_JUNCTION[2], CERVICOMEDULLARY_JUNCTION[1], 0.0055, 0.0045)]
    for r in VERTEBRAE:
        if r["cord_w_mm"] > 0:
            pts.append((r["z"], r["cord_y"], r["cord_w_mm"] / 2000.0, r["cord_ap_mm"] / 2000.0))
    pts.append((CONUS_TIP[2], CONUS_TIP[1], 0.0015, 0.0015))
    return np.array(pts)


def cord_centre_at_z(z):
    """(y, half_width, half_ap) of the cord at height ``z`` (interpolated between vertebrae)."""
    p = _cord_profile()[::-1]        # ascending z for np.interp
    return (float(np.interp(z, p[:, 0], p[:, 1])), float(np.interp(z, p[:, 0], p[:, 2])),
            float(np.interp(z, p[:, 0], p[:, 3])))


def cord_segments():
    """30 cord segments C1..S5 with z ranges (plan §5.8 spine.json ``cord_segments``)."""
    out = []
    for i, name in enumerate(CORD_SEGMENTS):
        z_top, z_bot = cord_z_at(i), cord_z_at(i + 1)
        zc = 0.5 * (z_top + z_bot)
        nearest = min(VERTEBRAE, key=lambda r: abs(r["z"] - zc))["level"]
        y, hw, hap = cord_centre_at_z(zc)
        out.append({"id": name, "index": i, "z_top": z_top, "z_bottom": z_bot, "vertebra": nearest,
                    "c": [0.0, y, zc], "w_mm": 2000 * hw, "ap_mm": 2000 * hap})
    return out


# ---------------------------------------------------------------------------
# Brainstem (RB §7.4) - positions relative to the head origin; body = rel + (0, 0.020, 1.647)
# ---------------------------------------------------------------------------
BRAINSTEM_REL_HEAD = {
    # id: (centre rel. head origin, (length, width, AP) mm, note)
    "midbrain": ((0.0, -0.010, 0.035), (17.5, 30.0, 25.0), "tentorial notch; CN III"),
    "pons": ((0.0, -0.006, 0.012), (26.0, 36.5, 25.0), "basis front at y_rel ~ -0.019 on the clivus"),
    "pontomedullary_junction": ((0.0, 0.000, 0.000), None, "at the head origin (CN VII/VIII exit)"),
    "medulla": ((0.0, 0.005, -0.014), (30.0, 16.0, 12.5), "respiratory/vasomotor centres"),
    "cervicomedullary_junction": ((0.0, 0.010, -0.028), (11.0, 11.0, 9.0), "at the foramen magnum"),
    "cerebellum": ((0.0, 0.045, -0.005), (55.0, 100.0, 50.0), "hemispheres at x +-0.045; 140-150 g"),
}
# Capsule chain "brainstem" in the body frame, r 11 mm, long axis tilted 15-25 deg top-forward [RB §7.4]
BRAINSTEM_CHAIN = [(0.0, 0.030, 1.619), (0.0, 0.025, 1.633), (0.0, 0.020, 1.647), (0.0, 0.014, 1.659),
                   (0.0, 0.010, 1.682)]
BRAINSTEM_RADIUS = 0.011
CONCUSSIVE_RADIUS_MM = 18        # handgun [R04 §2.1]
# Labelled hit capsules (a, b, r) in the body frame (E: split of the chain above;
# medulla CMJ -> pontomedullary junction, pons 26 mm split into the front basis
# (y 0.001-0.013) and the back tegmentum (y 0.013-0.026), midbrain 17.5 mm).
BRAINSTEM_HIT = {
    "medulla": ((0.0, 0.030, 1.619), (0.0, 0.022, 1.644), 0.0080),
    "pons_tegmentum": ((0.0, 0.022, 1.648), (0.0, 0.017, 1.670), 0.0065),
    "pons_basis": ((0.0, 0.009, 1.648), (0.0, 0.004, 1.670), 0.0070),
    "midbrain": ((0.0, 0.013, 1.674), (0.0, 0.008, 1.690), 0.0120),
    "cord_C1_C2": ((0.0, 0.027, 1.590), (0.0, 0.030, 1.619), 0.0060),
}
