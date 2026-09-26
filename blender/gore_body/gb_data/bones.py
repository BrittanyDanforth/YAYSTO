"""Bone dimensions and skeletal reference points (RB §7.3 bone table; R05 §6-8). Left side.

B3 builds the skeleton from these; B0's placeholder uses them for simple
bone stand-ins.  Long bones are double shells (periosteal outer + endosteal
inner surface) so a cut shows the cortex ring and the marrow (plan §8.2 B3).
"""

# name: (length_cm, midshaft_d_mm (w, d), cortex_mm, marrow, tag)
LONG_BONES = {
    "femur":    dict(length_cm=47.0, length_range=(47.0, 48.5), shaft_mm=(29, 27), cortex_mm=7.0,
                     cortex_range=(6, 8), canal_mm=(12, 14), marrow="yellow shaft #E4C36A; red neck/head", tag="C"),
    "tibia":    dict(length_cm=41.0, shaft_mm=(32, 23), cortex_mm=6.0, cortex_range=(5, 7), canal_mm=(10, 12),
                     marrow="yellow shaft", note="anteromedial face subcutaneous (3-6 mm)", tag="C"),
    "fibula":   dict(length_cm=39.5, shaft_mm=(15, 15), cortex_mm=3.0, cortex_range=(2.5, 3.5), tag="C"),
    "humerus":  dict(length_cm=34.0, length_range=(33.5, 34.5), shaft_mm=(22, 20), cortex_mm=5.0,
                     cortex_range=(4, 6), canal_mm=(10, 12), note="radial nerve in the spiral groove", tag="C"),
    "radius":   dict(length_cm=26.0, shaft_mm=(14, 12), cortex_mm=3.0, cortex_range=(2.5, 3.5), tag="C"),
    "ulna":     dict(length_cm=27.5, shaft_mm=(13, 12), cortex_mm=3.0, cortex_range=(2.5, 3.5),
                     note="back border subcutaneous", tag="C"),
    "clavicle": dict(length_cm=14.8, shaft_mm=(13, 10), cortex_mm=2.5, cortex_range=(2, 3), tag="M"),
}
# Acceptance lengths for B3 (plan §8.2): femur 47 +-1, tibia 41, fibula 39.5, humerus 34, radius 26,
# ulna 27.5, clavicle 14.8 cm.
ACCEPT_LENGTH_CM = {"femur": 47.0, "tibia": 41.0, "fibula": 39.5, "humerus": 34.0, "radius": 26.0,
                    "ulna": 27.5, "clavicle": 14.8}

# ---------------------------------------------------------------------------
# Key points (left side, body frame m)
# ---------------------------------------------------------------------------
CLAVICLE_WAYPOINTS = [(0.025, -0.040, 1.450), (0.070, -0.050, 1.452), (0.125, -0.020, 1.462),
                      (0.165, 0.010, 1.462)]                         # S-curve, R05 §6.1 E
CLAVICLE_SECTION_MM = {"sternal": (25, 20), "mid": (13, 10), "acromial": (25, 10)}

SCAPULA = {
    "superior_angle": (0.080, 0.085, 1.475), "spine_root": (0.075, 0.095, 1.440),
    "inferior_angle": (0.085, 0.105, 1.325), "glenoid_centre": (0.156, 0.022, 1.415),
    "acromion_tip": (0.200, 0.015, 1.458), "acromion_posterior_angle": (0.180, 0.050, 1.455),
    "coracoid_tip": (0.135, -0.020, 1.425),
    "height_cm": 15.5, "breadth_cm": 10.5, "plane_from_coronal_deg": (35, 40),
    "blade_thickness_mm": (1, 3), "glenoid_mm": (38, 28), "tag": "K/E (M)",
}

HUMERUS = {"head_centre": (0.180, 0.020, 1.415), "head_d_mm": 48, "elbow_centre": (0.325, 0.020, 1.164),
           "epicondylar_width_mm": 63, "articular_width_mm": 42, "retroversion_deg": (20, 30)}
FOREARM = {"radius_side": "-Y (thumb side), y ~ +0.010", "ulna_side": "+Y (posteromedial), y ~ +0.030",
           "radius_head_below_elbow_axis_m": 0.010, "olecranon_above_axis_m": 0.025,
           "interosseous_gap_mm": (15, 20)}

HAND_BONES = {
    "carpal_block_mm": (30, 55, 20), "carpal_centre": (0.463, 0.020, 0.925),
    "metacarpal_mm": (46, 69, 66, 58, 54), "proximal_phalanx_mm": (32, 41, 46, 43, 34),
    "middle_phalanx_mm": (None, 24, 28, 27, 20), "distal_phalanx_mm": (23, 18, 19, 19, 17),
    "rest_flexion_deg": {"mcp": (15, 20), "pip": (20, 30), "dip": 10, "thumb_abduction": 30},
}

PELVIS = {
    "iliac_crest_top": (0.140, 0.025, 1.070), "iliac_tubercle": (0.135, -0.030, 1.055),
    "asis": (0.122, -0.062, 0.992), "aiis": (0.105, -0.055, 0.958), "psis": (0.045, 0.090, 1.010),
    "acetabulum_centre": (0.087, -0.015, 0.918), "acetabulum_d_mm": 55,
    "pubic_tubercle": (0.022, -0.068, 0.913),
    "symphysis_top": (0.0, -0.068, 0.911), "symphysis_centre": (0.0, -0.062, 0.888),
    "symphysis_lower": (0.0, -0.055, 0.866),
    "ischial_spine": (0.045, 0.035, 0.898), "ischial_tuberosity": (0.055, 0.020, 0.841),
    "obturator_centre": (0.050, -0.040, 0.878), "obturator_mm": (50, 35),
    "iliac_wing_thickness_mm": {"fossa": (2, 4), "crest": (10, 15), "acetabulum": 30},
    "bicristal_cm": 27.0, "inter_asis_cm": 24.5, "tag": "K/E (M)",
}

FEMUR = {"head_centre": (0.087, -0.015, 0.918), "head_d_mm": 49, "neck_shaft_deg": 127, "anteversion_deg": 12,
         "greater_trochanter_tip": (0.145, 0.000, 0.923), "greater_trochanter_lateral": (0.158, 0.000, 0.913),
         "lesser_trochanter": (0.075, 0.010, 0.863),
         "shaft_axis": ((0.120, 0.005, 0.923), (0.092, 0.015, 0.487)),
         "bicondylar_width_mm": 84, "condylar_ap_mm": (60, 65), "knee_centre": (0.092, 0.020, 0.492)}

KNEE_LEG = {
    "patella_centre": (0.090, -0.035, 0.497), "patella_mm": (53, 51, 25),
    "tibial_tuberosity": (0.090, -0.025, 0.434), "tibial_plateau_z": 0.480, "tibial_plateau_mm": (78, 50),
    "tibial_plafond_z": 0.090, "medial_malleolus_tip": (0.065, 0.045, 0.068),
    "fibular_head": (0.130, 0.035, 0.452), "lateral_malleolus_tip": (0.132, 0.060, 0.055),
    "ankle_centre": (0.095, 0.050, 0.075),
}

FOOT_BONES = {
    "axis": (0.122, -0.993, 0.0), "talus_mm": (55, 40, 32), "talus_dome_z": 0.090,
    "calcaneus_mm": (80, 42, 45), "calcaneus_tuber": (0.095, 0.100, 0.035), "heel_pad_mm": (15, 20),
    "midfoot_block_mm": (50, 70, 30), "midfoot_centre": (0.100, -0.005, 0.045),
    "metatarsal_mm": (64, 75, 70, 68, 69), "mtp1": (0.084, -0.083, 0.020), "mtp5": (0.161, -0.049, 0.018),
    "toe2_tip": (0.128, -0.151, 0.010), "heel_skin": (0.095, 0.115, 0.030),
}

SKULL = {  # thickness (mm) [RB §7.3]; the skull itself comes from the head project
    "frontal": 7.0, "frontal_range": (5.8, 8.0), "parietal": 6.0, "parietal_range": (5.4, 7.0),
    "temporal_squama": (2, 5), "occipital": (8.0, 8.6), "orbital_roof_floor": (0.25, 1.0),
    "table_each": (1.5, 2.0), "diploe_colour": "#A4574A",
}

# Materials and colours (RB §7.3)
BONE_MATERIAL = dict(cortical_density_g_cm3=1.9, cortical_E_gpa=(17, 20), ultimate_mpa=(130, 190, 70),
                     trabecular_mpa=(1, 7), bending_failure_kn={"femur": (3, 5), "tibia": (2.5, 4),
                                                                  "humerus": (1.5, 2.5), "radius_ulna": (1, 1.5)})
BONE_COLOURS = {"cortical_cut": "#E9DFCC", "periosteum": "#E6CFC4", "articular_cartilage": "#DDE3E6",
                "costal_cartilage": "#CBD5D8", "disc_annulus": "#E3E0D6", "disc_nucleus": "#D8DDD2",
                "dura": "#D9D6CE", "red_marrow": "#B5524A", "yellow_marrow": "#E4C36A", "diploe": "#A4574A"}

# bone class codes for UV2.y of GB_Skeleton / GB_Frac_* (plan §5.5)
BONE_CLASS = {0: "long_bone_cortex", 1: "flat", 2: "vertebra", 3: "skull", 4: "cartilage", 5: "tooth"}
