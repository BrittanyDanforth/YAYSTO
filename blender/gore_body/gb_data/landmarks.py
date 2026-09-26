"""Body landmarks, head contract landmarks and girths.

Sources
-------
* ``LANDMARK_CSV``: RB §7.1 (R05 §13.1, corrected values from the R05 fact-check).
  Left side; ``landmark(name)`` mirrors ``_R`` names.  kind: skin | bone | joint.
* ``LANDMARK_EXTRA_CSV``: further R05 §1 rows the bible CSV does not repeat
  (epicondyles, MTP joints, spinous tips, pelvis points).  Head rows of R05 §1
  are NOT used: inside the head the contract head is authoritative [RB §1.2].
* ``HEAD_CONTRACT``: RB §1.2 table in the head frame; ``head_landmarks_body()``
  converts it.  ``build`` code should prefer ``gb_common.import_head()``'s
  measured ``anatomy.ANATOMY_LANDMARKS`` (the head team may move things).
* ``GIRTHS``: RB §7.1 / R05 §2.1 circumferences, breadths, depths and section
  centres of the skin envelope (ANSUR II subsample corrected).
"""
import numpy as np

# name, x, y, z, kind   (RB §7.1 verbatim; left side)
LANDMARK_CSV = """\
vertex,0.000,0.020,1.780,skin
head_origin_mid_ear_canals,0.000,0.020,1.647,joint
ear_canal_L,0.068,0.020,1.647,skin
mastoid_tip_L,0.055,0.030,1.612,bone
inion,0.000,0.112,1.654,skin
basion,0.000,0.018,1.626,bone
atlanto_occipital_pivot,0.000,0.015,1.622,joint
menton,0.000,-0.068,1.550,skin
gonion_L,0.052,-0.005,1.577,skin
hyoid_body,0.000,-0.030,1.556,bone
laryngeal_prominence,0.000,-0.062,1.537,skin
cricoid,0.000,-0.055,1.515,skin
c7_spinous_cervicale,0.000,0.075,1.532,skin
jugular_notch,0.000,-0.048,1.455,skin
sc_joint_L,0.025,-0.040,1.450,joint
ac_joint_L,0.165,0.010,1.462,joint
acromion_L,0.200,0.015,1.458,bone
gh_joint_L,0.180,0.020,1.415,joint
sternal_angle,0.000,-0.075,1.405,skin
nipple_L,0.100,-0.112,1.300,skin
xiphisternal_joint,0.000,-0.110,1.305,skin
xiphoid_tip,0.000,-0.094,1.273,bone
scapula_inferior_angle_L,0.085,0.105,1.325,bone
costal_margin_lowest_L,0.112,-0.050,1.125,bone
navel,0.000,-0.108,1.075,skin
iliac_crest_top_L,0.140,0.025,1.070,bone
asis_L,0.122,-0.062,0.992,bone
psis_L,0.045,0.090,1.010,bone
pubic_symphysis_top,0.000,-0.068,0.911,bone
mid_inguinal_point_L,0.065,-0.068,0.940,skin
hip_joint_centre_L,0.087,-0.015,0.918,joint
greater_trochanter_L,0.158,0.000,0.913,bone
ischial_tuberosity_L,0.055,0.020,0.841,bone
crotch,0.000,0.005,0.860,skin
elbow_centre_L_apose,0.325,0.020,1.164,joint
wrist_centre_L_apose,0.460,0.020,0.930,joint
mcp3_L_apose,0.508,0.020,0.848,joint
fingertip3_L_apose,0.553,0.020,0.770,skin
knee_centre_L,0.092,0.020,0.492,joint
patella_centre_L,0.090,-0.035,0.497,bone
tibial_tuberosity_L,0.090,-0.025,0.434,bone
fibular_head_L,0.130,0.035,0.452,bone
ankle_centre_L,0.095,0.050,0.075,joint
lateral_malleolus_L,0.132,0.060,0.055,bone
medial_malleolus_L,0.065,0.045,0.068,bone
heel_L,0.095,0.115,0.030,skin
toe2_tip_L,0.128,-0.151,0.010,skin
"""

# Extra R05 §1 rows (body rows only; corrected values).  name, x, y, z, kind, tag
LANDMARK_EXTRA_CSV = """\
tragion_L,0.073,0.012,1.650,skin,M
t7_spinous_skin,0.000,0.122,1.335,skin,E
l4_spinous_skin,0.000,0.080,1.080,skin,E
iliac_tubercle_L,0.135,-0.030,1.055,bone,M
pubic_tubercle_L,0.022,-0.068,0.913,bone,M
pubic_symphysis_centre,0.000,-0.062,0.888,bone,M
pubic_symphysis_lower,0.000,-0.055,0.866,bone,M
coccyx_tip,0.000,0.040,0.905,bone,L
gluteal_fold_L,0.090,0.120,0.820,skin,L
lateral_epicondyle_L_apose,0.353,0.020,1.180,bone,E
medial_epicondyle_L_apose,0.295,0.020,1.147,bone,E
mtp1_L,0.084,-0.083,0.020,joint,E
mtp5_L,0.161,-0.049,0.018,joint,E
skin_over_greater_trochanter_L,0.178,0.000,0.913,skin,H
patella_skin_L,0.090,-0.047,0.497,skin,H
asis_skin_L,0.122,-0.072,0.992,skin,M
psis_dimple_L,0.045,0.100,1.010,skin,M
"""


def _parse(csv_text, with_tag=False):
    out = {}
    for line in csv_text.strip().splitlines():
        parts = line.split(",")
        name = parts[0]
        p = tuple(float(v) for v in parts[1:4])
        row = {"p": p, "kind": parts[4]}
        row["tag"] = parts[5] if with_tag else "V/C"
        out[name] = row
    return out


LANDMARKS = _parse(LANDMARK_CSV)
LANDMARKS_EXTRA = _parse(LANDMARK_EXTRA_CSV, with_tag=True)


def all_landmarks(include_right=True, include_extra=True):
    """``{name: (x, y, z)}`` for every landmark; ``_L`` rows also produce mirrored ``_R`` rows.

    Names like ``elbow_centre_L_apose`` mirror to ``elbow_centre_R_apose``."""
    rows = dict(LANDMARKS)
    if include_extra:
        rows.update(LANDMARKS_EXTRA)
    out = {}
    for name, row in rows.items():
        out[name] = row["p"]
        if include_right and "_L" in name:
            rname = name.replace("_L_", "_R_") if "_L_" in name else (
                name[:-2] + "_R" if name.endswith("_L") else name.replace("_L", "_R"))
            x, y, z = row["p"]
            out[rname] = (-x, y, z)
    return out


def landmark(name):
    """Position of one landmark (mirrors ``_R`` names from the left rows)."""
    return np.array(all_landmarks()[name], dtype=float)


# ---------------------------------------------------------------------------
# Head contract landmarks (RB §1.2; head frame = origin between the ear canals)
# The head project's own measured table (anatomy.ANATOMY_LANDMARKS) overrides
# these at build time; this copy is the reference the verifier compares with.
# ---------------------------------------------------------------------------
HEAD_CONTRACT = {
    "vertex": (0.0, 0.005, 0.125),
    "glabella": (0.0, -0.093, 0.035),
    "eye_L": (0.032, -0.070, 0.022),
    "eye_R": (-0.032, -0.070, 0.022),
    "nose_tip": (0.0, -0.111, -0.014),
    "mouth_center": (0.0, -0.094, -0.055),
    "chin_bottom": (0.0, -0.080, -0.103),
    "ear_canal_L": (0.072, 0.0, 0.0),
    "ear_canal_R": (-0.072, 0.0, 0.0),
}
HEAD_NECK_CUT_Z_HEAD = -0.200          # head-frame neck cut plane (body z 1.447)
NECK_BLEND_Z = (1.47, 1.52)            # blend head neck into body neck [RB §1.2] G
EYE_RADIUS = 0.012                     # [RB §1.2], head materials
EYE_CONSTANTS = {                      # head materials / anatomy constants (plan §3.6, §7)
    "radius_m": 0.012, "cornea_radius_m": 0.0075, "cornea_offset_m": 0.00582,
    "limbus_radius_m": 0.0059, "cornea_ior": 1.376, "iris_plane_y_local_m": -0.0101,
    "gaze_local_axis": "-Y",
}

# ---------------------------------------------------------------------------
# Girths of the skin envelope (RB §7.1 checks + R05 §2.1 table; cm and m)
# level: (z, circumference_cm, breadth_x_cm, depth_y_cm, centre_x, centre_y, tag)
# Section centres y: chest front -0.112 / back +0.118; navel front -0.118 / back
# +0.087; buttocks front -0.090 / back +0.145; neck front -0.055 / back +0.063;
# calf: shin front +0.008 / calf back +0.133.  Limb rows use the left side.
# ---------------------------------------------------------------------------
GIRTHS = {
    "head_max":      dict(z=1.692, girth_cm=57.5, breadth_cm=15.5, depth_cm=19.5, c=(0.0, 0.020), tag="H/V"),
    "neck":          dict(z=1.515, girth_cm=38.0, breadth_cm=12.0, depth_cm=11.7, c=(0.0, 0.004), tag="H/V"),
    "bideltoid":     dict(z=1.400, girth_cm=None, breadth_cm=49.0, depth_cm=None, c=(0.0, 0.0), tag="H/V"),
    "biacromial":    dict(z=1.458, girth_cm=None, breadth_cm=42.0, depth_cm=None, c=(0.0, 0.0), tag="H/V"),
    "chest":         dict(z=1.300, girth_cm=100.0, breadth_cm=28.7, depth_cm=23.0, c=(0.0, 0.003), tag="H/V"),
    "natural_waist": dict(z=1.130, girth_cm=81.0, breadth_cm=28.0, depth_cm=19.5, c=(0.0, -0.018), tag="M"),
    "waist_navel":   dict(z=1.075, girth_cm=84.0, breadth_cm=29.5, depth_cm=20.5, c=(0.0, -0.016), tag="H/V"),
    "hips":          dict(z=0.885, girth_cm=97.0, breadth_cm=33.0, depth_cm=23.5, c=(0.0, 0.028), tag="H/V"),
    "upper_thigh":   dict(z=0.790, girth_cm=58.0, breadth_cm=17.5, depth_cm=18.5, c=(0.090, 0.020), tag="H/V"),
    "mid_thigh":     dict(z=0.700, girth_cm=51.0, breadth_cm=16.0, depth_cm=16.5, c=(0.092, 0.015), tag="M"),
    "knee":          dict(z=0.495, girth_cm=37.5, breadth_cm=11.0, depth_cm=11.5, c=(0.091, 0.010), tag="M"),
    "calf":          dict(z=0.370, girth_cm=37.5, breadth_cm=11.5, depth_cm=12.5, c=(0.094, 0.0705), tag="H/V"),
    "ankle":         dict(z=0.120, girth_cm=22.5, breadth_cm=6.5, depth_cm=7.5, c=(0.095, 0.055), tag="M"),
}
# Limb girths measured along the A-pose arm axis (R05 §2.1): breadth is the
# medial-lateral size, depth the front-back size; the wrist and hand breadth is
# radial-ulnar, which in the A-pose (palms to thighs, thumbs forward) is along Y.
ARM_GIRTHS = {
    "upper_arm_mid": dict(girth_cm=30.0, breadth_cm=9.0, depth_cm=10.0, tag="M"),
    "forearm_max":   dict(girth_cm=27.5, breadth_cm=8.5, depth_cm=7.5, below_elbow_m=0.05, tag="M"),
    "wrist":         dict(girth_cm=17.0, breadth_cm=5.8, depth_cm=4.0, tag="M"),
}
HAND = dict(length_m=0.192, breadth_m=0.087, thickness_m=0.030, tag="H")      # R05 §2.1, ANSUR II
FOOT = dict(length_m=0.268, breadth_m=0.102, toe_out_deg=7.0, tag="H")        # R05 §2.1 / §7.4
STATURE_M = 1.78
MASS_KG = 75.0
BODY_FAT_PCT = 15.0
BSA_M2 = 1.93                                                                  # DuBois [RB §7]
ARM_DIRECTION_L = (0.5, 0.0, -0.8660254)     # A-pose limb direction d (RB §3.3 upper limb, R05 §6)
ARM_MEDIAL_NORMAL_L = (-0.8660254, 0.0, -0.5)  # palm-side normal n_m (RB §3.3)
FOOT_AXIS_L = (0.122, -0.993, 0.0)           # heel -> 2nd toe, 7 deg toe-out (R05 §7.4)

# Checklist relations (RB §7 checklist) used by verify.py
CHECKLIST = {
    "nipple_below_jugular_notch_m": 0.155,
    "nipple_spacing_m": 0.20,
    "navel_below_xiphoid_m": 0.20,
    "fingertip_z_apose": 0.77,
}
