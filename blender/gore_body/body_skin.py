"""Body skin, shorts, muscle shell, per-vertex codes (owner B1).  Plan §1.2, §5.2, §5.5, §8.2 B1.

Final entry points
------------------
``body_sdf(x, y, z)``          body skin SDF (no head), body frame, negative inside
``skin_sdf(x, y, z)``          head (gore_head) united with the body: the combined outer skin
``build_body_skin()``          -> {"GB_Body": obj, "GB_Body_HR": obj}   (44k tris, 5 surfaces, codes, UVs)
``build_shorts(skin)``         -> {"GB_Shorts": obj}
``build_muscle_shell(skin)``   -> {"GB_MuscleShell": obj}
``paint_codes(obj)``           write gb_seg/gb_region/gb_derm + UV2 ``gb_codes`` (plan §5.5)

Status: B1 stub.  ``body_sdf``/``skin_sdf``/``paint_codes`` delegate to the B0
placeholder mannequin (so B2's seam ring and every other package can already
call them); the ``build_*`` functions raise ``NotBuiltYet`` and ``build.py``
keeps the placeholder objects.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402


def body_sdf(x, y, z):
    """Body skin SDF (v0 = placeholder mannequin until B1)."""
    import placeholder
    return placeholder.body_sdf(x, y, z)


def skin_sdf(x, y, z):
    """Combined head + body skin SDF (v0 = placeholder until B1)."""
    import placeholder
    return placeholder.skin_sdf(x, y, z)


def build_body_skin():
    """GB_Body (+ GB_Body_HR bake source) - B1."""
    gbc.not_built("B1", "body_skin.build_body_skin")


def build_shorts(skin):
    """GB_Shorts from the skin - B1."""
    gbc.not_built("B1", "body_skin.build_shorts")


def build_muscle_shell(skin):
    """GB_MuscleShell (skin SDF offset inward by skin + fat, 6 surfaces) - B1."""
    gbc.not_built("B1", "body_skin.build_muscle_shell")


def paint_codes(obj):
    """Segment / region / dermatome codes (v0 = placeholder rules until B1)."""
    import placeholder
    return placeholder.set_skin_codes(obj)
