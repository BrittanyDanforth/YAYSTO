"""Cycles look-dev materials (owner B7).  Plan §4.2, §5.2, §8.2 B7.

``build_materials()`` -> Cycles materials for renders and bakes (reusing gore_head/materials.py read-only).
The exported glb keeps the named placeholder materials (plan §5.6); these are bake sources only.

Status: B7 stub.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402


def build_materials():
    """Look-dev materials - B7."""
    gbc.not_built("B7", "lookdev.build_materials")
