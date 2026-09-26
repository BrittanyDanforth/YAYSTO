"""Head integration, neck seam, face rig data, eye FX, hair cards (owner B2).  Plan D19, §3.6, §5.2, §8.2 B2.

Final entry points
------------------
``seam_ring(n=160)``        (n, 3) canonical seam ring at z ~ 1.485 on the combined skin SDF
``zip_to_ring(obj, ring)``  replace the mesh's open neck boundary by a strip to ``ring`` (identical seam vertices)
``build_head()``            -> {"GB_Head", "GB_Head_HR", "GB_Eye_L", "GB_Eye_R", "GB_Mouth", ...}
``build_face_shapes(head)`` 24 face shape keys (gb_common.FACE_SHAPE_KEYS)
``build_eye_fx()``          -> {"GB_EyeFX_L", "GB_EyeFX_R"}
``build_hair_cards()``      -> {"GB_BrowLash"}

Status: B2 stub.  ``seam_ring`` and ``zip_to_ring`` are working v0 versions (B0,
used by the placeholder: GB_Head and GB_Body already share the ring); the
builders raise ``NotBuiltYet`` and the placeholder head stands in.

Finding for B2 (from B0): the head project's neck column (``anatomy._neck``) is
centred ~3 cm behind the bible's neck (body y ~ +0.039 at z 1.49, front
surface ~ -0.013, vs RB §7.1 front -0.055 / back +0.063 and the laryngeal
prominence at y -0.062).  The placeholder cuts the head's neck below z 1.515
and unites it with a bible-placed neck capsule.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
import gb_geom as gg  # noqa: E402

NECK_AXIS_XY = (0.0, 0.012)


def seam_ring(n=gbc.SEAM_RING_N):
    """Canonical ring on the combined skin SDF (v0: bisection along rays from the neck axis)."""
    import body_skin
    return gg.seam_ring_from_sdf(body_skin.skin_sdf, gbc.SEAM_Z, n, centre_xy=NECK_AXIS_XY, r_max=0.12)


def zip_to_ring(obj, ring, side="auto"):
    """Zip the open neck boundary of ``obj`` to ``ring``; ``side`` 'above'/'below' (auto: by mean z)."""
    if side == "auto":
        side = "above" if gbc.get_verts(obj.data)[:, 2].mean() > gbc.SEAM_Z else "below"
    return gg.zip_to_ring(obj, ring, NECK_AXIS_XY, side)


def build_head():
    """GB_Head (+ HR), eyes, mouth; hands skull/jaw to B3 and brain to B4 - B2."""
    gbc.not_built("B2", "head_integration.build_head")


def build_face_shapes(head):
    """The 24 face shape keys - B2."""
    gbc.not_built("B2", "head_integration.build_face_shapes")


def build_eye_fx():
    """GB_EyeFX_L/R (tearline, occlusion) - B2."""
    gbc.not_built("B2", "head_integration.build_eye_fx")


def build_hair_cards():
    """GB_BrowLash alpha cards from the head project's hair curves - B2."""
    gbc.not_built("B2", "head_integration.build_hair_cards")
