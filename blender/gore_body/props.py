"""Weapons, tools and the forensic test room (owner B8).  Plan §1.3, §5.2, §5.7, §8.2 B8.

``build_weapons()`` -> pistol (9 mm, GBP_muzzle), shotgun (12 ga), knife (GBP_blade_edge_0..7), claw hammer
                       (GBP_hammer_face, GBP_claw), propane torch (GBP_torch_nozzle), fist glove, ruler,
                       penlight, thermometer
``build_room()``    -> 6 x 6 x 3 m tiled room, drain, backstop, lights, table, trolley, GBP_room_* markers

Status: B8 stub.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402


def build_weapons():
    """Weapons and tools - B8."""
    gbc.not_built("B8", "props.build_weapons")


def build_room():
    """Forensic room - B8."""
    gbc.not_built("B8", "props.build_room")
