"""Spinal cord, brainstem, brain and brain labels (owner B4).

Plan §3.3.6, §5.2, §5.7-5.8, §8.2 B4.

Final entry points
------------------
``build_cord()``    -> {"GB_Cord": obj}: cord C1-S5 (CSV ellipses), dura tube, cauda equina, root stubs
``spine_table()``   -> spine.json payload (vertebrae, cord segments, conus, thecal end, brainstem)
``brain_labels()``  -> (labels uint8[64,64,64] indexed [k(z), j(y), i(x)], meta dict) for brain_labels.png/json

Status: ``build_cord`` is a B4 stub (the placeholder cord stands in).
``spine_table`` and ``brain_labels`` are working **v0** implementations by B0
straight from ``gb_data`` so the export and the Godot loaders work from day
one; B4 refines them (label lobes cut by the head's CENTRAL_SULCUS /
LATERAL_FISSURE curves, internal capsule, thalamus ...).
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import brain as BR  # noqa: E402
from gb_data import myotomes as MYO  # noqa: E402
from gb_data import vertebrae as VT  # noqa: E402


def build_cord():
    """Build GB_Cord (cord, dura, cauda equina, root stubs) - B4."""
    gbc.not_built("B4", "neuro.build_cord")


def spine_table():
    """spine.json 'data' (plan §5.8) from gb_data.vertebrae (v0, B0)."""
    verts = []
    for r in VT.VERTEBRAE:
        verts.append({
            "level": r["level"], "c": list(r["c"]),
            "body_hwd_mm": [r["body_h_mm"], r["body_w_mm"], r["body_d_mm"]],
            "disc_below_mm": r["disc_below_mm"], "canal_ap_w_mm": [r["canal_ap_mm"], r["canal_w_mm"]],
            "spinous_dy_mm": r["spinous_dy_mm"],
            "cord": ({"c": [0.0, r["cord_y"], r["z"]], "w_mm": r["cord_w_mm"], "ap_mm": r["cord_ap_mm"]}
                     if r["cord_w_mm"] > 0 else None),
            "cauda_only": r["cord_w_mm"] == 0,
            "lesioned_segments": list(MYO.VERTEBRA_TO_SEGMENTS.get(r["level"], ())),
        })
    brainstem = [{"id": k, "a": list(a), "b": list(b), "r": rr, "concussive_r_mm": VT.CONCUSSIVE_RADIUS_MM}
                 for k, (a, b, rr) in VT.BRAINSTEM_HIT.items()]
    return {
        "vertebrae": verts,
        "cord_segments": VT.cord_segments(),
        "conus_tip": list(VT.CONUS_TIP), "thecal_end": list(VT.THECAL_END),
        "cervicomedullary_junction": list(VT.CERVICOMEDULLARY_JUNCTION),
        "cauda": {"points": [list(p) for p in VT.CAUDA_CHAIN], "radius": VT.CAUDA_RADIUS},
        "brainstem": brainstem,
        "brainstem_chain": {"points": [list(p) for p in VT.BRAINSTEM_CHAIN], "radius": VT.BRAINSTEM_RADIUS},
        "cauda_vertebrae": list(MYO.CAUDA_VERTEBRAE),
        "resp_capacity": [{"from": a, "to": b, "vc_fraction": f} for a, b, f in MYO.RESP_CAPACITY],
        "cord_index": MYO.CORD_INDEX,
        "status": "v0 (B0 from gb_data; B4 refines)",
    }


# ---------------------------------------------------------------------------
# Brain regions (v0 rules in the head frame; B4 replaces them)
# ---------------------------------------------------------------------------
# central sulcus y(z) and lateral fissure z(y) in the head frame, from the head's
# CENTRAL_SULCUS / LATERAL_FISSURE curves (gore_head/anatomy.py)
_CS_Z = [0.050, 0.068, 0.086, 0.103]
_CS_YV = [-0.016, -0.012, -0.008, -0.002]
_LF_Y = [-0.042, -0.030, -0.015, 0.002, 0.018]
_LF_Z = [0.012, 0.017, 0.024, 0.031, 0.040]


def _seg_dist(p, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


def brain_region_at(points_body, inside=None):
    """Region id (``gb_data.brain.BRAIN_REGIONS``) for body-frame points (v0 geometric rules).

    ``inside``: optional bool mask of points inside the brain; others get 0."""
    p = np.asarray(points_body, float)
    hp = p - gbc.HEAD_OFFSET
    x, y, z = hp[:, 0], hp[:, 1], hp[:, 2]
    ax = np.abs(x)
    L = x > 0
    ID = BR.BRAIN_REGION_ID

    def side(name):
        return np.where(L, ID[name + "_L"], ID[name + "_R"])
    ycs = np.interp(z, _CS_Z, _CS_YV)
    zlf = np.interp(y, _LF_Y, _LF_Z)
    out = np.where(y < ycs - 0.032, side("prefrontal"), side("parietal"))
    fef = (y >= ycs - 0.032) & (y < ycs - 0.013)
    out = np.where(fef & (z > 0.055), side("frontal_eye_field"), out)
    out = np.where(fef & (z <= 0.055), side("prefrontal"), out)
    motor = (y >= ycs - 0.013) & (y < ycs) & (z > zlf)
    out = np.where(motor, side("motor_strip"), out)
    out = np.where(y > 0.045, side("occipital"), out)
    temporal = (z < zlf - 0.002) & (ax > 0.018) & (y < 0.045) & (y > -0.060)
    out = np.where(temporal, side("temporal"), out)
    broca = L & (y > -0.068) & (y < -0.028) & (z > zlf) & (z < zlf + 0.024) & (ax > 0.034)
    out = np.where(broca, ID["broca_L"], out)
    wern = L & (y > -0.005) & (y < 0.035) & (z > zlf - 0.014) & (z < zlf + 0.004) & (ax > 0.042)
    out = np.where(wern, ID["wernicke_L"], out)
    cc = (ax < 0.006) & (z > 0.030) & (z < 0.055) & (y > -0.040) & (y < 0.040)
    out = np.where(cc, ID["corpus_callosum"], out)
    thal = ((ax - 0.010) / 0.010) ** 2 + ((y - 0.002) / 0.017) ** 2 + ((z - 0.030) / 0.011) ** 2 < 1.0
    out = np.where(thal, side("thalamus"), out)
    caps = ((ax - 0.023) / 0.0055) ** 2 + ((y + 0.004) / 0.020) ** 2 + ((z - 0.033) / 0.014) ** 2 < 1.0
    out = np.where(caps, side("internal_capsule"), out)
    cereb = (y > 0.025) & (z < 0.004)
    out = np.where(cereb, np.where(ax < 0.011, ID["vermis"], side("cerebellum")), out)
    for name, (a, b, r) in VT.BRAINSTEM_HIT.items():
        if name == "cord_C1_C2":
            continue
        m = _seg_dist(p, a, b) < r + 0.002
        out = np.where(m, ID[name], out)
    if inside is not None:
        out = np.where(inside, out, 0)
    return out.astype(np.int32)


def brain_labels(dims=BR.GRID_DIMS):
    """64^3 label grid over the brain bounds (v0).  Returns (labels[k, j, i] uint8, meta).

    Voxel (i, j, k) centre = origin + (i + 0.5, j + 0.5, k + 0.5) * voxel_size in the
    body frame; 0 = outside.  Inside = head-project brain SDF < 0, plus the brainstem capsules."""
    A = gbc.import_head().anatomy
    lo = np.array(A.BRAIN_BOX[0], float) + gbc.HEAD_OFFSET
    hi = np.array(A.BRAIN_BOX[1], float) + gbc.HEAD_OFFSET
    lo[2] = min(lo[2], 1.590)                  # include the medulla down to C1
    nx, ny, nz = dims
    size = (hi - lo) / np.array([nx, ny, nz])
    ii, jj, kk = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    pts = lo + (np.stack([ii, jj, kk], -1).reshape(-1, 3) + 0.5) * size
    hp = pts - gbc.HEAD_OFFSET
    inside = A.eval_points(A.brain_sdf, hp) < 0
    for name, (a, b, r) in VT.BRAINSTEM_HIT.items():
        inside |= _seg_dist(pts, a, b) < r
    lab = brain_region_at(pts, inside).reshape(nx, ny, nz)
    labels = np.transpose(lab, (2, 1, 0)).astype(np.uint8)          # [k, j, i]
    meta = {"origin": lo.tolist(), "voxel_size": size.tolist(), "dims": [nx, ny, nz],
            "atlas": {"file": "brain_labels.png", "tiles": list(BR.ATLAS_TILES), "tile_px": [nx, ny],
                      "slice_order": "tile t = k (z index) at column t % 8, row t // 8 from the top",
                      "pixel": "column i (x), row j (y) from the top of the tile; R = region id"},
            "regions": {str(k): {"name": v[0], "side": v[1], "rb_row": v[2]} for k, v in BR.BRAIN_REGIONS.items()},
            "counts": {str(k): int((labels == k).sum()) for k in BR.BRAIN_REGIONS},
            "status": "v0 (B0 geometric rules; B4 refines)"}
    return labels, meta


def labels_atlas(labels):
    """Pack labels[k, j, i] into the 8 x 8 tile atlas (uint8, rows from the top)."""
    nz, ny, nx = labels.shape
    tx, ty = BR.ATLAS_TILES
    img = np.zeros((ty * ny, tx * nx), dtype=np.uint8)
    for k in range(nz):
        r, c = divmod(k, tx)
        img[r * ny:(r + 1) * ny, c * nx:(c + 1) * nx] = labels[k]
    return img


if __name__ == "__main__":
    lab, meta = brain_labels()
    print({meta["regions"][k]["name"]: v for k, v in meta["counts"].items() if v})
