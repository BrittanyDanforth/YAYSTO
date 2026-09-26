"""Spinal cord, brainstem, brain and brain labels (owner B4).

Plan §3.3.6, §5.2, §5.5, §5.7-5.8, §8.2 B4; RB §4.5-4.6, §7.4; R05 §9.

Final entry points
------------------
``build_cord()``    -> {"GB_Cord", "GB_Brain", "GB_Brain_HR"}: the whole neuro stage.
                       GB_Cord: cord C1 -> conus with the RB §7.3 cross-sections (ellipses), dural
                       tube to S2 (the cord floats in CSF inside it), cauda equina roots L2-Co fanning
                       to their foramina, root stubs C1-L1 to the intervertebral foramina.
                       GB_Brain: the head project's brain (gyri, cerebellum, brainstem) with the lower
                       medulla re-routed through the foramen magnum so it meets the cord in the canal;
                       UV2 = (region id, sulcus depth).  ``build_brain()`` builds only the brain.
``spine_table()``   -> spine.json payload (vertebrae, canal chain, cord segments with the meshed
                       centreline, conus, thecal end, brainstem hit capsules on the mesh, cord codes)
``brain_labels()``  -> (labels uint8[64,64,64] indexed [k(z), j(y), i(x)], meta) for brain_labels.png/json
``brain_region_at(points)`` -> region id per body-frame point (the same rules as the grid)

Head vs bible
-------------
Inside the head the head project is authoritative [RB §1.2]: its brainstem sits ~2 cm lower than
the RB §7.4 node table (pons centre z_rel -0.010 vs +0.012) and its clivus lies where the bible puts
the pons basis, so the brainstem labels and hit capsules follow the *mesh* (``BRAINSTEM_MESH``);
the bible nodes are kept in spine.json as ``brainstem_bible``.

Cord codes in GB_Cord UV2.x: 0-29 cord segment C1..S5, 30 cauda equina, 31 dura (thecal sac),
40 + n root stub of segment n (UV2.y = t along the part).
"""
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import brain as BR  # noqa: E402
from gb_data import myotomes as MYO  # noqa: E402
from gb_data import vertebrae as VT  # noqa: E402

O = gbc.HEAD_OFFSET
CODE_CAUDA, CODE_DURA, CODE_ROOT0 = 30, 31, 40
BRAIN_H = 0.0011                   # brain polygonisation (head project: 0.95 mm)
BRAIN_TRIS = 13800                 # plan §4.1: 14k
CORD_TRIS = 3000


def _A():
    return gbc.import_head().anatomy


def quick():
    return "--quick" in gbc.script_args()


def _V():
    import viscera
    return viscera


# ===========================================================================
# Cord path: medulla at the foramen magnum -> RB §7.3 cord centres -> conus
# ===========================================================================
# The head's foramen magnum (behind the basion lip, y 0.031-0.050 at z 1.612) and the atlas canal
# (y 0.022-0.032 at z 1.604) do not line up (B2/B3 finding): the cord threads the gap here.
CMJ_PATH = [(0.0, 0.0345, 1.628), (0.0, 0.0330, 1.616), (0.0, 0.0300, 1.607), (0.0, 0.0280, 1.598)]
BRAIN_CUT_Z = 1.623                # below this the head's own stem is replaced by CMJ_PATH
BRAIN_BOTTOM = 1.600               # GB_Brain ends here, GB_Cord starts 3 mm above (overlap)
CORD_TOP = 1.603


def cord_profile():
    """Cord centreline samples (z, y, half width, half AP) from the brain junction to the conus tip."""
    rows = [(CORD_TOP, 0.0285, 0.0056, 0.0044)]
    for r in VT.VERTEBRAE:
        if r["cord_w_mm"] > 0 and r["z"] < CORD_TOP - 0.004:
            rows.append((r["z"], r["cord_y"], r["cord_w_mm"] / 2000.0, r["cord_ap_mm"] / 2000.0))
    # conus medullaris: tapers from the L1 size to a point at the tip [RB §7.4]
    rows.append((VT.CONUS_TIP[2] + 0.008, VT.CONUS_TIP[1] + 0.002, 0.0030, 0.0028))
    rows.append((VT.CONUS_TIP[2], VT.CONUS_TIP[1], 0.0008, 0.0008))
    return np.array(rows)


def cord_centre(z):
    """(y, half width, half AP) of the meshed cord at height z."""
    p = cord_profile()[::-1]
    return (float(np.interp(z, p[:, 0], p[:, 1])), float(np.interp(z, p[:, 0], p[:, 2])),
            float(np.interp(z, p[:, 0], p[:, 3])))


def _canal_half(z):
    """(half width, half AP) of the vertebral canal at z (RB §7.3 CSV)."""
    rows = VT.VERTEBRAE[::-1]
    zs = [r["z"] for r in rows]
    return (float(np.interp(z, zs, [r["canal_w_mm"] / 2000.0 for r in rows])),
            float(np.interp(z, zs, [r["canal_ap_mm"] / 2000.0 for r in rows])))


def _seg_of_z(z):
    segs = VT.cord_segments()
    ztop = np.array([s["z_top"] for s in segs])
    zbot = np.array([s["z_bottom"] for s in segs])
    idx = np.clip(np.searchsorted(-ztop, -np.asarray(z), side="right") - 1, 0, 29)
    t = np.clip((ztop[idx] - z) / np.maximum(ztop[idx] - zbot[idx], 1e-6), 0.0, 1.0)
    return idx, t


def _foramen_z(seg_name):
    """Height of the intervertebral foramen a root exits: C1-C7 above their vertebra, C8 below C7,
    T1 onward below their vertebra [R05 §9.1]."""
    V = VT.VERTEBRA
    lv = [r["level"] for r in VT.VERTEBRAE]
    if seg_name == "C1":
        return V["C1"]["z"] + 0.004
    if seg_name[0] == "C" and seg_name != "C8":
        n = int(seg_name[1:])
        return 0.5 * (V[f"C{n - 1}"]["z"] + V[f"C{n}"]["z"])
    if seg_name == "C8":
        return 0.5 * (V["C7"]["z"] + V["T1"]["z"])
    i = lv.index(seg_name) if seg_name in lv else None
    if i is None or i + 1 >= len(lv):
        return None
    return 0.5 * (V[seg_name]["z"] + V[lv[i + 1]]["z"])


# ===========================================================================
# GB_Cord
# ===========================================================================
def _sweep_part(points, radii2, sides, step, code, t_mode="along", caps=True):
    """gb_geom.sweep with the lateral axis as the section normal; returns a join_parts part."""
    import gb_geom as gg
    v, f, t = gg.sweep(points, radii2, sides=sides, step=step, smooth=True, caps=caps,
                       normal_fn=lambda P: np.tile([1.0, 0.0, 0.0], (len(P), 1)))
    if np.isscalar(code):
        code = np.full(len(v), code, np.int32)
    return gg.part(v, f, 0, gb_piece=code(v) if callable(code) else code, gb_tt=t)


def cord_parts(q=False):
    """join_parts parts of the cord, dura, cauda and root stubs (budget ~3k triangles)."""
    import gb_geom as gg
    prof = cord_profile()
    P = np.column_stack([np.zeros(len(prof)), prof[:, 1], prof[:, 0]])
    parts = []
    # --- cord proper (ellipse sections), segment code by z, t within the segment
    v, f, tt = gg.sweep(P, prof[:, 2:4], sides=8, step=0.011, smooth=True,
                        normal_fn=lambda Q: np.tile([1.0, 0.0, 0.0], (len(Q), 1)))
    seg, tseg = _seg_of_z(v[:, 2])
    parts.append(gg.part(v, f, 0, gb_piece=seg.astype(np.int32), gb_tt=tseg))
    # --- dural tube: cord + CSF (2-4 mm), limited by the canal (epidural fat 1 mm), cauda sac to S2
    zs = np.concatenate([np.linspace(CORD_TOP + 0.004, VT.CONUS_TIP[2], 34)])
    dy, dw, da = [], [], []
    for z in zs:
        y, hw, ha = cord_centre(z)
        cw, ca = _canal_half(z)
        dw.append(min(max(hw, 0.004) + 0.0028, cw - 0.0030))
        da.append(max(min(max(ha, 0.004) + 0.0022, ca - 0.0030), ha + 0.0008))
        dy.append(y + 0.0006)
    cauda = np.array(VT.CAUDA_CHAIN[1:])
    Pd = np.vstack([np.column_stack([np.zeros(len(zs)), dy, zs]), cauda])
    rd = np.vstack([np.column_stack([dw, da]),
                    np.column_stack([np.linspace(0.0065, 0.0040, len(cauda)),
                                     np.linspace(0.0045, 0.0034, len(cauda))])])
    v, f, tt = gg.sweep(Pd, rd, sides=8, step=0.020, smooth=True,
                        normal_fn=lambda Q: np.tile([1.0, 0.0, 0.0], (len(Q), 1)))
    parts.append(gg.part(v, f, 0, gb_piece=np.full(len(v), CODE_DURA, np.int32), gb_tt=tt))
    # --- cauda equina: L2-S2 root pairs fan down inside the sac and leave at their foramina;
    #     S3-Co + filum run on to the end of the sac [R05 §9.1]
    tip = np.array(VT.CONUS_TIP)
    names = MYO.CORD_SEGMENTS
    for sx in (1.0, -1.0):
        for k, nm in enumerate(("L2", "L3", "L4", "L5", "S1", "S2")):
            fz = _foramen_z(nm) if nm[0] == "L" else {"S1": 1.000, "S2": 0.985}[nm]
            def yc(zz):
                """Canal (cauda chain) y at height zz."""
                return float(np.interp(zz, [c[2] for c in VT.CAUDA_CHAIN[::-1]], [c[1] for c in VT.CAUDA_CHAIN[::-1]]))
            lat = 0.0010 + 0.0007 * (5 - k)
            zm = 0.5 * (tip[2] + fz) + 0.01
            pts = [tip + [sx * 0.0015, 0.001 * (k % 3 - 1), 0.012 - 0.002 * k],
                   (sx * lat, yc(zm) - 0.001 * (k % 2), zm),
                   (sx * (lat + 0.0008), yc(fz + 0.012), fz + 0.012),
                   (sx * 0.0040, yc(fz) - 0.0010, fz)]                   # leaves through its dural sleeve
            v, f, tt = gg.sweep(pts, 0.0011, sides=4, step=0.022, smooth=True)
            parts.append(gg.part(v, f, 0, gb_piece=np.full(len(v), CODE_CAUDA, np.int32), gb_tt=tt))
    for dx in (-0.0012, 0.0012):
        pts = [tip + [dx, 0.0, 0.004], (dx, cauda[2][1], cauda[2][2]), (dx * 0.5, cauda[-1][1] - 0.001,
                                                                        cauda[-1][2] + 0.006)]
        v, f, tt = gg.sweep(pts, 0.0012, sides=4, step=0.025, smooth=True)
        parts.append(gg.part(v, f, 0, gb_piece=np.full(len(v), CODE_CAUDA, np.int32), gb_tt=tt))
    # --- root stubs C1-L1: from the cord's side (segment centre) out through the dura to the foramen
    for i, nm in enumerate(names):
        if i > 21:                                   # L2 and below leave as cauda roots
            break
        seg = VT.cord_segments()[i]
        z0 = 0.5 * (seg["z_top"] + seg["z_bottom"])
        fz = _foramen_z(nm)
        if fz is None:
            continue
        y0, hw, ha = cord_centre(z0)
        cw, _ca = _canal_half(fz)
        for sx in (1.0, -1.0):
            a = np.array([sx * (hw - 0.0008), y0 + 0.0005, z0])
            b = np.array([sx * (cw - 0.0010), cord_centre(fz)[0] + 0.0010, fz])   # dural sleeve at the foramen
            m = 0.5 * (a + b) + np.array([0.0, 0.0, 0.25 * (a[2] - b[2])])
            v, f, tt = gg.sweep([a, m, b], [0.0011, 0.0012, 0.0010], sides=4, step=0.030, smooth=True)
            parts.append(gg.part(v, f, 0, gb_piece=np.full(len(v), CODE_ROOT0 + i, np.int32), gb_tt=tt))
    return parts


def build_cord_only():
    """GB_Cord object (~3k triangles), UV2 = (cord code, t)."""
    import gb_geom as gg
    import placeholder as PH
    obj = gg.object_from_parts("GB_Cord", cord_parts())
    u = gbc.read_point_attr(obj, "gb_piece", 'INT')
    t = gbc.read_point_attr(obj, "gb_tt", 'FLOAT')
    gbc.set_codes_uv(obj, u, np.clip(t, 0.0, 1.0))
    gg.smart_uv(obj, margin=0.004)
    PH.finish_uvs(obj)
    obj.data.shade_smooth()
    obj["gb_layer"] = gbc.LAYER_OF["GB_Cord"]
    obj["gb_schema"] = 1
    obj["gb_status"] = "B4"
    return obj


# ===========================================================================
# GB_Brain: the head project's brain + re-routed lower medulla
# ===========================================================================
def brain_sdf(x, y, z):
    """Body-frame brain SDF: head-project brain above BRAIN_CUT_Z (its stem below is replaced by a
    medulla that follows CMJ_PATH through the foramen magnum), closed at BRAIN_BOTTOM."""
    A = _A()
    V = _V()
    d = A.brain_sdf(x - O[0], y - O[1], z - O[2])
    low = (BRAIN_CUT_Z - z) * 1.0
    d = V.smax(d, np.where(y < 0.062, low, -1.0), 0.004)            # remove the head's lower stem
    med = V.chain(x / 0.82, y, z, [(0.0, 0.0365, 1.640)] + CMJ_PATH, [0.0068, 0.0060, 0.0050, 0.0047, 0.0046])
    d = V.smin(d, med, 0.006)
    return V.smax(d, BRAIN_BOTTOM - z, 0.001)


def brain_box():
    A = _A()
    lo = np.array(A.BRAIN_BOX[0]) + O
    hi = np.array(A.BRAIN_BOX[1]) + O
    lo[2] = BRAIN_BOTTOM - 0.004
    return lo, hi


def build_brain():
    """GB_Brain (LOD0, 14k tris) + GB_Brain_HR (bake source); UV2 = (region id, sulcus depth 0..1)."""
    import gb_geom as gg
    import placeholder as PH
    V = _V()
    A = _A()
    h = BRAIN_H * (1.9 if quick() else 1.0)
    t0 = time.perf_counter()
    v, f = V.mesh_sdf(brain_sdf, brain_box(), h)
    hr = V.decimate_components(v, f, 12 * BRAIN_TRIS)
    lod = V.decimate_components(*hr, BRAIN_TRIS)
    gbc.log(f"  B4 brain  raw {len(f)}  hr {len(hr[1])}  lod {len(lod[1])} tris  {time.perf_counter() - t0:.1f} s")
    out = {}
    for name, (vv, ff) in (("GB_Brain", lod), ("GB_Brain_HR", hr)):
        region = brain_region_at(vv)
        hp = vv - O
        s = A.gyri_field(np.abs(hp[:, 0]), hp[:, 1], hp[:, 2])
        depth = np.exp(-(s / 0.0016) ** 2)
        obj = gg.object_from_parts(name, [gg.part(vv, ff, 0)], slots=gbc.MATERIAL_SLOTS["GB_Brain"])
        gbc.point_attr(obj, "gb_region", region, 'INT')
        gbc.point_attr(obj, "gb_depth", depth, 'FLOAT')
        gbc.set_codes_uv(obj, region, depth)
        if name == "GB_Brain":
            gg.smart_uv(obj, margin=0.003)
        else:
            obj.data.uv_layers.new(name="atlas")
        PH.finish_uvs(obj)
        obj.data.shade_smooth()
        obj["gb_layer"] = "brain"
        obj["gb_schema"] = 1
        obj["gb_status"] = "B4"
        out[name] = obj
    return out


def build_cord():
    """The neuro stage: GB_Cord, GB_Brain, GB_Brain_HR (see module docstring)."""
    with gbc.Timer("B4 neuro: cord"):
        out = {"GB_Cord": build_cord_only()}
    with gbc.Timer("B4 neuro: brain"):
        out.update(build_brain())
    return out


# ===========================================================================
# Brainstem hit capsules on the mesh (head frame -> body frame)
# ===========================================================================
def _rel(p):
    return tuple(float(a) for a in np.asarray(p) + O)


# head-project brainstem: stem polyline A.STEM_PTS and the pons ellipsoid (0, 0.004, -0.010) (rel)
BRAINSTEM_MESH = {
    "midbrain": (_rel((0.0, 0.000, 0.024)), _rel((0.0, 0.004, 0.005)), 0.0095),
    "pons_basis": (_rel((0.0, -0.0015, -0.001)), _rel((0.0, 0.0010, -0.019)), 0.0075),
    "pons_tegmentum": (_rel((0.0, 0.0110, 0.001)), _rel((0.0, 0.0140, -0.020)), 0.0065),
    "medulla": (_rel((0.0, 0.0165, -0.021)), (0.0, 0.0330, 1.613), 0.0070),
    "cord_C1_C2": ((0.0, 0.0310, 1.609), (0.0, 0.0270, 1.585), 0.0060),
}


def _seg_dist(p, a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((p - a) @ ab) / (ab @ ab), 0.0, 1.0)
    return np.linalg.norm(p - (a + t[:, None] * ab), axis=1)


# ===========================================================================
# Brain regions (RB §4.5 rows; lobes cut by the head's CENTRAL_SULCUS / LATERAL_FISSURE curves)
# ===========================================================================
def _sulcus_tables():
    A = _A()
    cs = np.array(A.CENTRAL_SULCUS)          # (x, y, z) left hemisphere, head frame, top -> down
    lf = np.array(A.LATERAL_FISSURE)         # front -> back
    return cs, lf


def brain_region_at(points_body, inside=None, depth=None):
    """Region id (``gb_data.brain.BRAIN_REGIONS``) for body-frame points.

    Cortex: frontal pole -> prefrontal; the precentral gyrus (12 mm in front of the central sulcus,
    above the Sylvian fissure) -> motor strip; posterior middle frontal gyrus -> frontal eye field;
    left pars opercularis/triangularis -> Broca; behind the central sulcus -> parietal; behind the
    parieto-occipital plane -> occipital; below the Sylvian fissure -> temporal (left posterior
    superior temporal gyrus -> Wernicke).  Deep: thalamus, internal capsule, corpus callosum as
    ellipsoids; cerebellum below the tentorium (vermis within 11 mm of the midline); brainstem parts
    by the mesh capsules.  ``inside``: optional mask; points outside get 0.  ``depth``: optional depth below
    the brain surface (m); cortical areas (frontal eye field, Broca, Wernicke) are limited to the outer
    15 mm (cortex + subjacent white matter); mesh vertices have depth 0."""
    p = np.asarray(points_body, float)
    hp = p - O
    x, y, z = hp[:, 0], hp[:, 1], hp[:, 2]
    ax = np.abs(x)
    L = x > 0
    ID = BR.BRAIN_REGION_ID
    cs, lf = _sulcus_tables()

    def side(name):
        return np.where(L, ID[name + "_L"], ID[name + "_R"])
    # central sulcus: y as a function of z (and a lateral lean), extended as a surface into the depth
    ycs = np.interp(z, cs[::-1, 2], cs[::-1, 1])
    zlf = np.interp(y, lf[:, 1], lf[:, 2], left=lf[0, 2] - 0.004, right=lf[-1, 2] + 0.006)
    dep = np.zeros(len(p)) if depth is None else np.asarray(depth, float)
    cortex = dep < 0.015
    # frontal lobe: everything in front of the central-sulcus surface (the sulcus leans back with depth)
    ycs_d = ycs + 0.45 * dep
    out = np.where(y < ycs_d, side("prefrontal"), side("parietal"))
    fef = (y >= ycs - 0.032) & (y < ycs - 0.016) & (z > 0.052) & (z < 0.088) & (ax > 0.020) & cortex
    out = np.where(fef, side("frontal_eye_field"), out)
    motor = (y >= ycs_d - 0.012) & (y < ycs_d) & (z > zlf)
    out = np.where(motor, side("motor_strip"), out)
    occ = y > 0.034 - 0.08 * np.clip(z - 0.06, 0, None)                 # parieto-occipital sulcus plane
    out = np.where(occ & (z > zlf - 0.01), side("occipital"), out)
    temporal = (z < zlf - 0.002) & (ax > 0.016) & (y < 0.050) & (y > -0.064)
    out = np.where(temporal, side("temporal"), out)
    broca = L & (y > ycs - 0.052) & (y < ycs - 0.012) & (z > zlf - 0.002) & (z < zlf + 0.030) & (ax > 0.022) & cortex
    out = np.where(broca, ID["broca_L"], out)
    wern = L & (y > -0.004) & (y < 0.034) & (z > zlf - 0.016) & (z < zlf + 0.003) & (ax > 0.036) & cortex
    out = np.where(wern, ID["wernicke_L"], out)
    cc = (ax < 0.007) & (z > 0.030) & (z < 0.052) & (y > -0.042) & (y < 0.040)
    out = np.where(cc, ID["corpus_callosum"], out)
    thal = ((ax - 0.0105) / 0.0095) ** 2 + ((y - 0.004) / 0.016) ** 2 + ((z - 0.028) / 0.010) ** 2 < 1.0
    out = np.where(thal, side("thalamus"), out)
    caps = ((ax - 0.0225) / 0.0050) ** 2 + ((y + 0.002) / 0.019) ** 2 + ((z - 0.031) / 0.014) ** 2 < 1.0
    out = np.where(caps, side("internal_capsule"), out)
    # cerebellum: under the tentorium (head brain_sdf: z_t = 0.010 - 0.010 smoothstep(0.02, 0.09, y))
    t = np.clip((y - 0.02) / 0.07, 0, 1)
    zt = 0.010 - 0.010 * t * t * (3 - 2 * t)
    cereb = (y > 0.018) & (z < zt + 0.001)
    out = np.where(cereb, np.where(ax < 0.0062, ID["vermis"], side("cerebellum")), out)
    for name, (a, b, r) in BRAINSTEM_MESH.items():
        if name == "cord_C1_C2":
            continue
        m = _seg_dist(p, a, b) < r + 0.0015
        out = np.where(m, ID[name], out)
    if inside is not None:
        out = np.where(inside, out, 0)
    return out.astype(np.int32)


def brain_labels(dims=BR.GRID_DIMS):
    """64^3 label grid over the GB_Brain bounds.  Returns (labels[k, j, i] uint8, meta).

    Voxel (i, j, k) centre = origin + (i + 0.5, j + 0.5, k + 0.5) * voxel_size (body frame);
    0 = outside.  Inside = ``brain_sdf`` < 0 (the exact GB_Brain surface)."""
    lo, hi = brain_box()
    lo = lo.copy()
    lo[2] = BRAIN_BOTTOM
    nx, ny, nz = dims
    size = (hi - lo) / np.array([nx, ny, nz])
    ii, jj, kk = np.meshgrid(np.arange(nx), np.arange(ny), np.arange(nz), indexing="ij")
    pts = lo + (np.stack([ii, jj, kk], -1).reshape(-1, 3) + 0.5) * size
    A = _A()
    sd = A.eval_points(brain_sdf, pts)
    inside = sd < 0
    lab = brain_region_at(pts, inside, depth=np.clip(-sd, 0.0, None)).reshape(nx, ny, nz)
    labels = np.transpose(lab, (2, 1, 0)).astype(np.uint8)          # [k, j, i]
    counts = {str(k): int((labels == k).sum()) for k in BR.BRAIN_REGIONS}
    meta = {"origin": lo.tolist(), "voxel_size": size.tolist(), "dims": [nx, ny, nz],
            "atlas": {"file": "brain_labels.png", "tiles": list(BR.ATLAS_TILES), "tile_px": [nx, ny],
                      "slice_order": "tile t = k (z index) at column t % 8, row t // 8 from the top",
                      "pixel": "column i (x), row j (y) from the top of the tile; R = region id"},
            "regions": {str(k): {"name": v[0], "side": v[1], "rb_row": v[2],
                                 "voxels": counts[str(k)],
                                 "volume_ml": round(counts[str(k)] * float(np.prod(size)) * 1e6, 2)}
                        for k, v in BR.BRAIN_REGIONS.items()},
            "counts": counts,
            "method": "inside = GB_Brain SDF; lobes cut by the head's CENTRAL_SULCUS / LATERAL_FISSURE "
                      "curves + parieto-occipital plane; thalamus, internal capsule, corpus callosum "
                      "ellipsoids; cerebellum under the tentorium, vermis |x| < 11 mm; brainstem by "
                      "the mesh capsules (spine.json brainstem)",
            "status": "B4"}
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


# ===========================================================================
# spine.json
# ===========================================================================
def spine_table():
    """spine.json 'data' (plan §5.8): vertebrae with canal/cord, the canal chain, 30 cord segments with
    their meshed centre and size, conus, thecal end, cauda chain, brainstem hit capsules (mesh) and
    the bible nodes, cord codes of GB_Cord."""
    verts = []
    for r in VT.VERTEBRAE:
        c = None
        if r["cord_w_mm"] > 0:
            y, hw, ha = cord_centre(r["z"])
            c = {"c": [0.0, y, r["z"]], "w_mm": 2000 * hw, "ap_mm": 2000 * ha,
                 "bible": {"c": [0.0, r["cord_y"], r["z"]], "w_mm": r["cord_w_mm"], "ap_mm": r["cord_ap_mm"]}}
        verts.append({
            "level": r["level"], "c": list(r["c"]),
            "body_hwd_mm": [r["body_h_mm"], r["body_w_mm"], r["body_d_mm"]],
            "disc_below_mm": r["disc_below_mm"], "canal_ap_w_mm": [r["canal_ap_mm"], r["canal_w_mm"]],
            "spinous_dy_mm": r["spinous_dy_mm"], "cord": c, "cauda_only": r["cord_w_mm"] == 0,
            "lesioned_segments": list(MYO.VERTEBRA_TO_SEGMENTS.get(r["level"], ())),
        })
    segs = []
    for s in VT.cord_segments():
        zc = 0.5 * (s["z_top"] + s["z_bottom"])
        y, hw, ha = cord_centre(zc)
        rec = dict(s)
        rec.update({"c": [0.0, y, zc], "w_mm": 2000 * hw, "ap_mm": 2000 * ha, "code": s["index"],
                    "root_code": CODE_ROOT0 + s["index"] if s["index"] <= 21 else CODE_CAUDA,
                    "foramen_z": _foramen_z(s["id"])})
        segs.append(rec)
    canal = [{"c": [0.0, r["y"] + (r["body_d_mm"] + r["canal_ap_mm"]) / 2000.0, r["z"]],
              "r_ap": r["canal_ap_mm"] / 2000.0, "r_w": r["canal_w_mm"] / 2000.0, "level": r["level"]}
             for r in VT.VERTEBRAE if r["level"] != "C1"]
    prof = cord_profile()
    brainstem = [{"id": k, "a": list(a), "b": list(b), "r": rr, "concussive_r_mm": VT.CONCUSSIVE_RADIUS_MM}
                 for k, (a, b, rr) in BRAINSTEM_MESH.items()]
    bible = [{"id": k, "a": list(a), "b": list(b), "r": rr} for k, (a, b, rr) in VT.BRAINSTEM_HIT.items()]
    return {
        "vertebrae": verts,
        "canal_chain": canal,
        "cord_segments": segs,
        "cord_centreline": [[0.0, q[1], q[0], q[2], q[3]] for q in prof],
        "cord_centreline_format": "[x, y, z, half_width, half_ap] from the brain junction to the conus tip",
        "conus_tip": list(VT.CONUS_TIP), "thecal_end": list(VT.THECAL_END),
        "cervicomedullary_junction": list(CMJ_PATH[1]),
        "cmj_bible": list(VT.CERVICOMEDULLARY_JUNCTION),
        "cauda": {"points": [list(p) for p in VT.CAUDA_CHAIN], "radius": VT.CAUDA_RADIUS},
        "brainstem": brainstem,
        "brainstem_bible": bible,
        "brainstem_note": "hit capsules follow the head mesh (authoritative inside the head, RB §1.2); the head's "
                          "pons sits ~2 cm lower than RB §7.4",
        "cauda_vertebrae": list(MYO.CAUDA_VERTEBRAE),
        "resp_capacity": [{"from": a, "to": b, "vc_fraction": f} for a, b, f in MYO.RESP_CAPACITY],
        "cord_index": MYO.CORD_INDEX,
        "cord_codes": {"0-29": "cord segment C1..S5 (UV2.y = t within the segment)", str(CODE_CAUDA): "cauda equina",
                       str(CODE_DURA): "dura / thecal sac", f"{CODE_ROOT0}+n": "root stub of segment n (C1..L1)"},
        "status": "B4",
    }


# ===========================================================================
# Test renders (renders/neuro_*.png)
# ===========================================================================
CORD_COLOURS = {"cord": "#EEE5D6", "dura": "#CFCBC2", "root": "#E8DCC8", "cauda": "#EDE2CF"}
BRAIN_COLOUR = "#B79C94"


def _colour_copy(src, name, colfn, keep=None):
    import bpy
    V = _V()
    v, t = gbc.mesh_arrays(src.data)
    u, dd = gbc.read_codes_uv(src)
    if keep is not None:
        t = t[keep(v, u)[t].all(1)]
    me = gbc.mesh_from_arrays(name, v, t)
    ob = bpy.data.objects.new(name, me)
    gbc.link(ob, "Stage")
    col = np.ones((len(v), 4), np.float32)
    col[:, :3] = colfn(v, u)
    a = me.color_attributes.new("b4_col", 'FLOAT_COLOR', 'POINT')
    a.data.foreach_set("color", col.ravel())
    s = me.attributes.new("b4_speck", 'FLOAT', 'POINT')
    s.data.foreach_set("value", np.zeros(len(v), np.float32))
    me.materials.append(V.render_material())
    return ob


def render_neuro(prefix="neuro", samples=32):
    """renders/<prefix>_*.png: cord in the canal (side, half skeleton), cervicomedullary junction,
    brain regions (label colours), cauda equina."""
    import bpy
    V = _V()
    lin = lambda h: np.array(gbc.hex_to_linear(h)[:3])
    scene = gbc.setup_stage(floor=False)
    for nm in ("GB_Key", "GB_Fill", "GB_Rim"):
        o = bpy.data.objects.get(nm)
        if o is not None:
            o.hide_render = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.012, 0.014, 1.0)
    shown = {o.name: o.hide_render for o in bpy.data.objects}

    def cordcol(v, u):
        c = np.tile(lin(CORD_COLOURS["cord"]), (len(v), 1))
        c[u == CODE_DURA] = lin(CORD_COLOURS["dura"])
        c[u == CODE_CAUDA] = lin(CORD_COLOURS["cauda"])
        c[u >= CODE_ROOT0] = lin(CORD_COLOURS["root"])
        return c
    import colorsys
    pal = {k: np.array(colorsys.hsv_to_rgb((k * 0.381966) % 1.0, 0.55, 0.75)) ** 2.2 for k in BR.BRAIN_REGIONS}
    cord = _colour_copy(bpy.data.objects["GB_Cord"], "B4_n_cord", cordcol)
    cord_open = _colour_copy(bpy.data.objects["GB_Cord"], "B4_n_cord_open", cordcol,
                             keep=lambda v, u: ~((u == CODE_DURA) & (v[:, 0] < 0.0)))
    brain = _colour_copy(bpy.data.objects["GB_Brain"], "B4_n_brain", lambda v, u: np.tile(lin(BRAIN_COLOUR), (len(v), 1)))
    brainlab = _colour_copy(bpy.data.objects["GB_Brain"], "B4_n_brainlab", lambda v, u: np.array([pal[int(k)] for k in u]))
    skel = None
    if "GB_Skeleton" in bpy.data.objects:
        sk = bpy.data.objects["GB_Skeleton"]
        v, t = gbc.mesh_arrays(sk.data)
        t = t[(v[t].mean(1)[:, 0] > 0.004)]
        me = gbc.mesh_from_arrays("B4_n_skel", v, t)
        skel = bpy.data.objects.new("B4_n_skel", me)
        gbc.link(skel, "Stage")
        me.materials.append(bpy.data.materials.get("GBM_bone") or gbc.placeholder_material("GBM_bone"))
    out = []

    def only(*objs):
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = o not in objs

    def shot(name, loc, tgt, lens=55, res=(420, 620)):
        V._close_light(tgt, loc)
        cam = gbc.add_camera("B4_Cam", loc, tgt, lens)
        out.append(gbc.render(os.path.join(gbc.RENDER_DIR, f"{prefix}_{name}.png"), cam, samples, res))
    only(*[o for o in (cord, brain, skel) if o is not None])
    c = np.array([0.0, 0.03, 1.42])
    shot("spine_side", c + (-1.05, 0.0, 0.0), c, 50, (400, 640))
    j = np.array([0.0, 0.03, 1.60])
    shot("junction", j + (-0.30, -0.02, 0.02), j, 60, (480, 480))
    only(cord_open)
    k = np.array([0.0, 0.02, 1.085])
    shot("cauda", k + (-0.16, 0.20, 0.02), k, 55, (420, 560))
    shot("cervical_roots", np.array([0.0, 0.03, 1.53]) + (-0.12, 0.16, 0.02), (0.0, 0.03, 1.53), 60, (480, 480))
    only(brainlab)
    b = np.array([0.0, 0.02, 1.68])
    shot("brain_regions_left", b + (0.42, -0.10, 0.08), b, 60, (520, 480))
    shot("brain_regions_top", b + (0.0, 0.02, 0.45), b, 60, (480, 520))
    only(brain, cord)
    shot("brain_three_q", b + (-0.30, -0.30, 0.10), b, 60, (520, 480))
    for o in bpy.data.objects:
        if o.name.startswith("B4_n_"):
            bpy.data.objects.remove(o, do_unlink=True)
        elif o.name in shown:
            o.hide_render = shown[o.name]
    return out


if __name__ == "__main__":
    t0 = time.time()
    if "--render" in gbc.script_args():
        gbc.reset_scene()
        gbc.collections()
        objs = build_cord()
        cache = gbc.stage_cache("skeleton", [os.path.join(gbc.HERE, "skeleton.py")],
                                extra="quick" if quick() else "full")
        if cache.hit:
            cache.load()
        render_neuro()
        gbc.log(f"neuro: cord {gbc.tri_count(objs['GB_Cord'].data)} tris, brain "
                f"{gbc.tri_count(objs['GB_Brain'].data)} tris, {time.time() - t0:.1f} s")
    else:
        lab, meta = brain_labels()
        print({meta["regions"][k]["name"]: v for k, v in meta["counts"].items() if v}, f"{time.time() - t0:.1f} s")
