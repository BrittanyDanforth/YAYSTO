"""Skeleton, fracture variants, bone capsules (owner B3).  Plan D5, §3.3.5, §5.2, §8.2 B3.

Final entry points
------------------
``build_skeleton()``            -> {"GB_Skeleton": obj (+ "GB_Skeleton_HR")}: UV2 = (piece id, bone class),
                                   long bones as double shells (cortex + marrow), piece ids from
                                   gb_data.bones.BONE_PIECE_ID (append-only)
``build_fracture_variants()``   -> {"GB_Frac_*": obj} (gb_common.VARIANT_OBJECTS)
``bone_capsules()``             -> list of ~60 hit capsules {"piece", "bone", "a", "b", "r"} (body frame)

Status: B3 stub (the placeholder skeleton and split-copy variants stand in).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402


def build_skeleton():
    """GB_Skeleton - B3."""
    gbc.not_built("B3", "skeleton.build_skeleton")


def build_fracture_variants():
    """GB_Frac_* Voronoi variants - B3."""
    gbc.not_built("B3", "skeleton.build_fracture_variants")


def bone_capsules():
    """Hit capsules for the anatomy query - B3."""
    gbc.not_built("B3", "skeleton.bone_capsules")
