"""Vessel network and nerves (owner B5).  Plan §3.4.1, §5.2, §5.8 vessels.json, §8.2 B5.

Final entry points
------------------
``build_vessels()`` -> {"GB_Vessels_Art": obj, "GB_Vessels_Ven": obj, "GBV_*": curves, "GBN_*": curves}
``vessel_table()``  -> vessels.json payload: segments (resampled centreline [x, y, z, r], bones per point),
                       beds, nerves, collaterals, pulse data

Status: ``build_vessels`` is a B5 stub (the placeholder tubes stand in).
``vessel_table`` is a working v0 by B0 from ``gb_data.vessels`` / ``gb_data.nerves``
(Catmull-Rom through the waypoints, arc-length resampling at min(10 mm, 2 x diameter),
radius tapering to ``d_end_mm``); B5 refines paths, depths and adds the K additions.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import nerves as NV  # noqa: E402
from gb_data import vessels as VS  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402


def build_vessels():
    """Build GB_Vessels_Art/_Ven tubes and the GBV_/GBN_ data curves - B5."""
    gbc.not_built("B5", "vascular.build_vessels")


def mesh_for(seg):
    """Mesh a segment belongs to ('GB_Vessels_Art' / 'GB_Vessels_Ven'), None below 1.5 mm (data only)."""
    if VS.tube_sides(seg["d_mm"]) == 0:
        return None
    return "GB_Vessels_Ven" if seg["kind"] == "V" else "GB_Vessels_Art"


def centreline(seg):
    """Resampled centreline (P[M,3], r[M], t[M]) of a segment (plan §3.4.1 step 2)."""
    import gb_geom as gg
    d0 = seg["d_mm"] / 1000.0
    d1 = (seg["d_end_mm"] or seg["d_mm"]) / 1000.0
    step = min(0.010, 2.0 * d0)
    P, t = gg.resample(seg["points"], step, smooth=len(seg["points"]) > 2)
    r = 0.5 * (d0 + (d1 - d0) * t)
    return P, r, t


def vessel_table():
    """vessels.json 'data' (plan §5.8), v0 by B0."""
    import rig
    segs = VS.vessel_segments()
    out = []
    for s in segs:
        P, r, t = centreline(s)
        idx, w = rig.weights_at(P)
        dom = idx[np.arange(len(idx)), np.argmax(w, axis=1)]
        rec = {k: s[k] for k in ("id", "vessel", "branch", "name", "side", "kind", "circuit", "d_mm", "d_end_mm",
                                 "d_range_mm", "rest_flow_ml_min", "parent", "extra_parents", "children", "root",
                                 "depth_mm", "compressible", "self_stop", "stump_frac", "collaterals",
                                 "outlet_default", "in_bone_canal", "air_entry", "pulse_delay_ms", "landmarks",
                                 "bleed_ref", "fit_points", "tag", "note", "source")}
        rec["waypoints"] = [list(p) for p in s["points"]]
        rec["points"] = np.column_stack([P, r]).tolist()
        rec["bones"] = [RT.BONE_NAMES[i] for i in dom]
        rec["mesh"] = mesh_for(s)
        rec["vessel_index"] = s["vessel_index"]
        rec["tube_sides"] = VS.tube_sides(s["d_mm"])
        out.append(rec)
    nerves = []
    for nid, n in NV.NERVES.items():
        for side, sx in (("L", 1.0), ("R", -1.0)):
            pts = [[sx * p[0], p[1], p[2]] for p in n["points"]]
            nerves.append({"id": f"{nid}_{side}", "nerve": nid, "side": side, "roots": n["roots"],
                           "radius": n["radius"], "points": pts, "deficit": n["deficit"], "note": n["note"],
                           "tag": NV.TAG})
    return {"segments": out, "beds": VS.BEDS, "nerves": nerves, "collaterals": VS.COLLATERALS,
            "pulse": VS.PULSE, "colours": VS.COLOURS, "both_ends_bleed": list(VS.SCALP_FACE_BOTH_ENDS),
            "roots": [s["id"] for s in segs if s["root"]],
            "status": "v0 (B0 from gb_data; B5 refines paths/depths and adds the K additions)"}
