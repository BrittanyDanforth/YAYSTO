"""Organs (owner B4).  Plan §3.3.6, §5.2, §5.8 organs.json, §8.2 B4.

Final entry points
------------------
``build_organs()``  -> {"GB_Organs": obj}: heart (4 chambers, walls, pericardium), lungs (lobes, hila),
                       diaphragm, liver + gallbladder, spleen, kidneys, adrenals, stomach, pancreas,
                       bladder, larynx, trachea + rings, bronchi, oesophagus, thyroid, greater omentum;
                       UV2 = (organ id, sub-part id); shape keys heart_systole, lung_inhale_L/R,
                       lung_collapse_L/R, diaphragm_inhale.
``organ_table()``   -> organs.json payload

Status: ``build_organs`` is a B4 stub (the placeholder organs stand in).
``organ_table`` is a working v0 by B0 straight from ``gb_data.organs``.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import organs as OR  # noqa: E402


def build_organs():
    """Build GB_Organs (all organs in one mesh, organ id in UV2.x) - B4."""
    gbc.not_built("B4", "viscera.build_organs")


def _mass(o):
    if o["id"] == "heart":
        return OR.HEART["mass_g"]
    if o["hit"]:
        return sum(OR.PRIMITIVES[h].get("mass_g", 0.0) for h in o["hit"]) or None
    return None


def organ_table():
    """organs.json 'data' (plan §5.8): organ records with hit and sub primitives, plus tubes (v0, B0)."""
    organs = []
    for o in OR.ORGANS:
        rec = {"id": o["id"], "organ_id": o["organ_id"], "mesh": "GB_Organs",
               "parent_bones": o["parent_bones"], "mass_g": _mass(o), "compartment": o["compartment"],
               "hit_priority": o["hit_priority"], "surface_colour": o["surface_colour"],
               "interior_colour": o["interior_colour"], "hit": OR.organ_hit_primitives(o),
               "sub": OR.organ_sub_primitives(o), "blend_shapes": o["blend_shapes"]}
        if o.get("tube"):
            t = OR.TUBES[o["tube"]]
            rec["tube"] = {"id": o["tube"], "radius": t["radius"], "points": [list(p) for p in t["points"]]}
        if o.get("note"):
            rec["note"] = o["note"]
        organs.append(rec)
    tubes = [{"id": k, "radius": v["radius"], "points": [list(p) for p in v["points"]]} for k, v in OR.TUBES.items()]
    return {"organs": organs, "tubes": tubes,
            "facts": {"heart": OR.HEART, "lungs": OR.LUNGS, "diaphragm": OR.DIAPHRAGM, "liver": OR.LIVER,
                      "spleen": OR.SPLEEN, "kidneys": OR.KIDNEYS, "omentum": OR.OMENTUM},
            "density_g_cm3": OR.ORGAN_DENSITY_G_CM3,
            "shapes": {"obb": "c = centre, size = full lengths along u, v, w = u x v",
                       "ellipsoid": "size = full diameters along u, v, w", "sphere": "size[0] = diameter",
                       "capsule": "size[0] = total length along u, size[1] = diameter"},
            "status": "v0 (B0 from gb_data; B4 refines)"}
