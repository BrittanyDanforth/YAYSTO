"""Texture bakes (owner B7).  Plan §3.3.7, §4.2, §5.2, §8.2 B7.

``bake_all(objs, out)``              albedo / normal / ORM+SSS sets per mesh (2,048^2), textures/*.png
``bake_tileables(out)``              seamless 512^2 tileables (muscle fibre, fat lobule, bone cut, diploe,
                                     blood crust, cloth weave)
``bake_painter_inputs(objs, out)``   position (EXR half, segment-relative), rest normal, valid mask,
                                     tissue depth, tension, dominant-bone maps

Status: B7 stub.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402


def bake_all(objs, out):
    """Surface bakes - B7."""
    gbc.not_built("B7", "bake.bake_all")


def bake_tileables(out):
    """Tileable textures - B7."""
    gbc.not_built("B7", "bake.bake_tileables")


def bake_painter_inputs(objs, out):
    """Painter input maps - B7."""
    gbc.not_built("B7", "bake.bake_painter_inputs")
