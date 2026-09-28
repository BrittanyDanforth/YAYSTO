"""Segment and region codes (plan §5.5) and body-segment masses (RB §7.2, R05 §2.2).

Codes are written per vertex into the ``gb_codes`` UV map (UV2 in Godot) and
listed in ``codes.json``; ``segment`` is also ``CUSTOM0.w`` at runtime.
"""

# segment code -> name (plan §5.5)
SEGMENTS = {
    0: "head_neck", 1: "torso", 2: "arm_L", 3: "arm_R", 4: "leg_L", 5: "leg_R",
    6: "hand_L", 7: "hand_R", 8: "foot_L", 9: "foot_R", 10: "shorts",
}
SEGMENT_ID = {v: k for k, v in SEGMENTS.items()}

# region code -> name [RB §2.0] (drives wound tables: skin thickness, laceration rules)
REGIONS = {
    0: "scalp", 1: "face", 2: "eyelid_lip", 3: "neck", 4: "trunk_front", 5: "trunk_back",
    6: "limb", 7: "palm_sole",
}
REGION_ID = {v: k for k, v in REGIONS.items()}

# UV2.x of skin-like meshes = segment + REGION_STRIDE * region (plan §5.5)
REGION_STRIDE = 32

# deform bone -> skin segment (used for material surfaces and dominant-bone maps)
BONE_SEGMENT = {
    "root": "torso", "hips": "torso", "spine": "torso", "chest": "torso", "upper_chest": "torso",
    "neck": "head_neck", "head": "head_neck", "jaw": "head_neck", "tongue": "head_neck",
    "eye_L": "head_neck", "eye_R": "head_neck", "lid_upper_L": "head_neck", "lid_lower_L": "head_neck",
    "lid_upper_R": "head_neck", "lid_lower_R": "head_neck",
}
for _s in ("L", "R"):
    BONE_SEGMENT.update({
        f"clavicle_{_s}": "torso",
        f"upper_arm_{_s}": f"arm_{_s}", f"upper_arm_twist_{_s}": f"arm_{_s}",
        f"forearm_{_s}": f"arm_{_s}", f"forearm_twist_{_s}": f"arm_{_s}",
        f"hand_{_s}": f"hand_{_s}", f"fingers_{_s}": f"hand_{_s}", f"thumb_{_s}": f"hand_{_s}",
        f"thigh_{_s}": f"leg_{_s}", f"shin_{_s}": f"leg_{_s}",
        f"foot_{_s}": f"foot_{_s}", f"toes_{_s}": f"foot_{_s}",
    })

# skin segment -> GB_Body / GB_MuscleShell material surface (plan §5.6)
SEGMENT_SURFACE = {
    "head_neck": "head", "torso": "torso", "arm_L": "arm_L", "arm_R": "arm_R", "hand_L": "arm_L",
    "hand_R": "arm_R", "leg_L": "leg_L", "leg_R": "leg_R", "foot_L": "leg_L", "foot_R": "leg_R",
    "shorts": "torso",
}

# ---------------------------------------------------------------------------
# Segment masses: Dempster via Winter (RB §7.2, R05 §2.2) V.
# name: (fraction of body mass, COM fraction from the proximal joint, radius of
#        gyration about the COM / segment length, proximal -> distal definition)
# Per-side limb rows count once per side.  Fractions sum to 1.000.
# ---------------------------------------------------------------------------
SEGMENT_MASS = {
    "head_neck":   (0.081, 1.000, 0.495, "C7/T1 -> ear canal (COM at the ear canal)"),
    "thorax":      (0.216, 0.82, None, "C7/T1 -> T12/L1"),
    "abdomen":     (0.139, 0.44, None, "T12/L1 -> L4/L5"),
    "pelvis":      (0.142, 0.105, None, "L4/L5 -> greater trochanter"),
    "upper_arm_L": (0.028, 0.436, 0.322, "glenohumeral -> elbow"),
    "upper_arm_R": (0.028, 0.436, 0.322, "glenohumeral -> elbow"),
    "forearm_L":   (0.016, 0.430, 0.303, "elbow -> wrist"),
    "forearm_R":   (0.016, 0.430, 0.303, "elbow -> wrist"),
    "hand_L":      (0.006, 0.506, 0.297, "wrist -> middle MCP"),
    "hand_R":      (0.006, 0.506, 0.297, "wrist -> middle MCP"),
    "thigh_L":     (0.100, 0.433, 0.323, "hip centre -> knee centre"),
    "thigh_R":     (0.100, 0.433, 0.323, "hip centre -> knee centre"),
    "shank_L":     (0.0465, 0.433, 0.302, "knee centre -> ankle"),
    "shank_R":     (0.0465, 0.433, 0.302, "knee centre -> ankle"),
    "foot_L":      (0.0145, 0.50, 0.475, "ankle -> 2nd metatarsal head"),
    "foot_R":      (0.0145, 0.50, 0.475, "ankle -> 2nd metatarsal head"),
}
BODY_MASS_KG = 75.0
WHOLE_BODY_COM_Z = 0.96          # standing [RB §7.2, R2-03 §11]
# de Leva alternative thigh mass if falls look top-heavy [RB §7.2]
DE_LEVA_THIGH_KG = 10.6


def segment_mass_kg(name):
    """Mass of a Dempster/Winter segment for the 75 kg reference body."""
    return SEGMENT_MASS[name][0] * BODY_MASS_KG


def mass_fraction_sum():
    """Sum of all segment fractions (must be 1.000)."""
    return sum(v[0] for v in SEGMENT_MASS.values())
