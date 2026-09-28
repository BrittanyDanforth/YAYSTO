"""Brain region ids for the 64^3 label grid and the GB_Brain UV2.x code (plan §3.3.6, §5.5, §5.7).

Regions are the rows of RB §4.5 (the physiology's brain-damage table), split by
side where the bible's deficit is lateralised.  ``x > 0`` is the character's
LEFT (body frame).  Id 0 = outside the brain.  B4 owns the final label grid
(lobes cut by the head's CENTRAL_SULCUS / LATERAL_FISSURE curves); these ids
are the stable contract between the grid, ``brain_labels.json`` and G1/G2.
"""

# id: (name, side, RB §4.5 row)
BRAIN_REGIONS = {
    0: ("none", "-", ""),
    1: ("prefrontal_L", "L", "Prefrontal"),
    2: ("prefrontal_R", "R", "Prefrontal"),
    3: ("motor_strip_L", "L", "Motor strip / internal capsule"),
    4: ("motor_strip_R", "R", "Motor strip / internal capsule"),
    5: ("frontal_eye_field_L", "L", "Frontal eye field"),
    6: ("frontal_eye_field_R", "R", "Frontal eye field"),
    7: ("broca_L", "L", "Left (dominant) language areas"),
    8: ("wernicke_L", "L", "Left (dominant) language areas"),
    9: ("parietal_L", "L", "(parietal, sensory; left: language support)"),
    10: ("parietal_R", "R", "Right parietal (left neglect)"),
    11: ("occipital_L", "L", "Occipital"),
    12: ("occipital_R", "R", "Occipital"),
    13: ("temporal_L", "L", "Temporal"),
    14: ("temporal_R", "R", "Temporal"),
    15: ("thalamus_L", "L", "Thalamus / diencephalon"),
    16: ("thalamus_R", "R", "Thalamus / diencephalon"),
    17: ("internal_capsule_L", "L", "Motor strip / internal capsule"),
    18: ("internal_capsule_R", "R", "Motor strip / internal capsule"),
    19: ("cerebellum_L", "L", "Cerebellar hemisphere"),
    20: ("cerebellum_R", "R", "Cerebellar hemisphere"),
    21: ("vermis", "mid", "Vermis"),
    22: ("midbrain", "mid", "Midbrain"),
    23: ("pons_tegmentum", "mid", "Pons, tegmentum"),
    24: ("pons_basis", "mid", "Pons, ventral basis only"),
    25: ("medulla", "mid", "Medulla"),
    26: ("corpus_callosum", "mid", "(midline white matter; part of bilateral hemisphere damage)"),
}
BRAIN_REGION_ID = {v[0]: k for k, v in BRAIN_REGIONS.items()}
GRID_DIMS = (64, 64, 64)            # plan §3.3.6: ~2.9 mm voxels over the brain bounds
ATLAS_TILES = (8, 8)                # 64 slices of 64 x 64 -> 512 x 512 PNG, R = region id (lossless)
