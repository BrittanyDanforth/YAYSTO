"""Tissue layers, depths to structures and cut colours (RB §7.6; R05 §12, C/M).

B1 bakes these into the tissue-depth map and builds the muscle shell from
them; G3's wound walls band by depth using the colours; B5/FB-5 checks vessel
depths against ``DEPTH_CHECKS``.
"""

# region point -> (skin_mm, fat_mm, muscle_mm, depth-to-structure notes)
LAYERS = {
    "scalp": dict(skin=(3.5, 5.5), total_to_bone=(5, 8), structure={"outer_table": 6}),
    "neck_anterior_midline": dict(skin=1.5, fat=(2, 5), muscle=(3, 4), structure={"trachea": (8, 12),
                                                                                "thyroid_isthmus": 10}),
    "neck_over_carotid": dict(skin=1.5, fat=(3, 6), muscle="platysma 1-2 + SCM 8-12",
                              structure={"cca_ijv": (20, 30)}),
    "neck_posterior_c4": dict(skin=3, fat=(3, 8), muscle=(25, 35), structure={"lamina": 35, "cord": (45, 55)}),
    "over_sternum": dict(skin=(1.5, 2), fat=(3, 8), muscle=None, structure={"bone": (5, 12), "rv": (25, 35)}),
    "chest_2nd_ics_mcl": dict(skin=2, fat=(5, 10), muscle=(15, 35), structure={"pleura": 42}),
    "chest_lateral_5th_ics_mal": dict(skin=2, fat=(5, 15), muscle=(10, 22), structure={"pleura": (32, 34)}),
    "upper_back_t4_t7": dict(skin=(3, 4), fat=(5, 10), muscle=(30, 50), structure={"rib": (40, 60),
                                                                                  "spinous_tips": (8, 12)}),
    "abdomen_paramedian_navel": dict(skin=2, fat=(12, 20), muscle="rectus 10-12",
                                     structure={"peritoneum": (25, 40), "aorta": 75}),
    "flank_mal_l2": dict(skin=2, fat=(10, 25), muscle=(15, 20), structure={"peritoneum": (30, 45),
                                                                          "kidney_edge": (60, 80)}),
    "lower_back_l3": dict(skin=(3, 4), fat=(8, 20), muscle=(40, 55), structure={"kidney": (50, 70),
                                                                               "canal_midline": 70}),
    "groin": dict(skin=1.5, fat=(8, 15), muscle=None, structure={"femoral_artery": (15, 30)}),
    "upper_arm_anterior": dict(skin=1.5, fat=(4, 7), muscle=(30, 40), structure={"humerus": (40, 45),
                                                                                "brachial_artery": (10, 20)}),
    "wrist_volar": dict(skin=1.0, fat=(2, 3), muscle="tendons", structure={"radial_artery": (2, 5),
                                                                          "ulnar_artery": (4, 7)}),
    "thigh_anterior_mid": dict(skin=(1.5, 2), fat=(6, 12), muscle=(45, 55), structure={"femur": (55, 70)}),
    "shin_anteromedial": dict(skin=(1.5, 2), fat=(1, 3), muscle=None, structure={"tibia": (3, 6)}),
    "knee_malleoli_heel": dict(structure={"patella": (4, 8), "malleoli": (2, 4), "calcaneus": (18, 24)}),
    "buttock_upper_outer": dict(skin=(2.5, 3), fat=(15, 30), muscle="gluteus maximus 30-50, medius 15-25",
                                structure={"ilium": (50, 80), "sciatic_nerve": (60, 90)}),
}

# skin thickness by region (mm) [RB §7.6]
SKIN_MM = {"eyelid": (0.5, 0.7), "face": (1.5, 2.0), "trunk_front": (1.5, 2.5), "back": (2.5, 4.0),
           "limbs": (1.0, 2.0), "palm_sole": (1.5, 4.0), "scalp": (3.5, 5.5), "neck": (1.5, 3.0)}

# subcutaneous fat map (mm at 15 % body fat; scale x fat% / 15) [RB §7.6]
FAT_MM = {"chest": 6, "abdomen": 15, "flank": 15, "back": 8, "buttock": 20, "thigh": 9, "arm": 6,
          "forearm": 4, "calf": 6, "shin": 2, "hands": 2, "feet": 2}
FAT_REFERENCE_PCT = 15.0

# cut-surface colours [RB §7.6, §7.3] and plan §3.3.4 wall banding
CUT_COLOURS = {"epidermis_dermis": "#EAD2C8", "fat": "#F2D16B", "fascia": "#E8E6DF", "muscle": "#9B2F2B",
               "muscle_deoxygenated": "#6E2020", "bone": "#E9DFCC", "backface_flesh": "#3A0A0C",
               "wound_bottom_blood": "#5E070C"}

# FB-5 vessel depth acceptance (mm) [plan §8.1, RB §7.6]
DEPTH_CHECKS = {
    "A04": ("CCA at C4-C6", (20, 30)), "V01": ("IJV at C4-C6", (20, 30)),
    "A28": ("femoral artery at the groin", (15, 30)), "A42": ("radial artery at the wrist", (2, 5)),
    "A41": ("brachial mid-arm", (10, 20)),
}

# Lean sites: bone right under the dermis (B3 acceptance depths, mm) [plan §8.2 B3]
LEAN_SITE_DEPTH_MM = {"tibial_face": (3, 6), "patella": (4, 8), "malleoli": (2, 4), "sternum": (5, 12)}

# Muscle shell offset rule (plan §8.2 B1): skin SDF offset inward by skin + fat
MUSCLE_SHELL = dict(offset="skin + fat (region maps above)", triangles=24000, surfaces=6)
