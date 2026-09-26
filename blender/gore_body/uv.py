"""UV helpers (owners B1 body, B2 head; working v0 by B0).  Plan §5.2, §5.5.

``mark_seams(obj, rules)``                     rules: callables f(p0, p1) -> bool on edge end points (body frame)
``unwrap(obj, method='MINIMUM_STRETCH')``      unwrap the ``atlas`` map (methods verified in 5.0: ANGLE_BASED,
                                               CONFORMAL, MINIMUM_STRETCH)
``pack(obj, size=2048, margin_px=16)``         pack islands, margin_method FRACTION (16 px at 2,048 = 0.0078)
"""
import os
import sys

import numpy as np

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402


def _edit(obj):
    vl = bpy.context.view_layer
    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    vl.objects.active = obj
    obj.select_set(True)
    me = obj.data
    if "atlas" not in me.uv_layers:
        me.uv_layers.new(name="atlas")
    me.uv_layers.active = me.uv_layers["atlas"]


def mark_seams(obj, rules):
    """Mark edges as UV seams where any rule returns True for the edge's two end points."""
    me = obj.data
    v = gbc.get_verts(me)
    ev = np.empty(len(me.edges) * 2, dtype=np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    seam = np.zeros(len(ev), dtype=bool)
    for rule in rules:
        seam |= np.asarray(rule(v[ev[:, 0]], v[ev[:, 1]]), dtype=bool)
    me.edges.foreach_set("use_seam", seam)
    me.update()
    return int(seam.sum())


def unwrap(obj, method="MINIMUM_STRETCH", margin=0.001):
    """Unwrap the whole mesh into ``atlas`` using the marked seams."""
    _edit(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.unwrap(method=method, margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)


def pack(obj, size=2048, margin_px=16):
    """Pack the atlas islands with a FRACTION margin of ``margin_px / size``."""
    _edit(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(margin_method='FRACTION', margin=margin_px / float(size), rotate=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
