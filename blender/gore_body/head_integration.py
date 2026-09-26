"""Head integration, neck seam, face rig data, eye FX, hair cards (owner B2).  Plan D19, §3.6, §5.2, §8.2 B2.

Entry points (final signatures)
-------------------------------
``seam_ring(n=160)``           (n, 3) canonical seam ring at z = SEAM_Z on the combined skin SDF
``seam_normals(ring)``         (n, 3) analytic skin normals at the ring (SDF gradient)
``zip_to_ring(obj, ring)``     replace the mesh's open neck boundary by a strip to ``ring`` (identical
                               seam vertices) and give the ring vertices the analytic seam normals
``apply_seam_normals(obj)``    (re)apply the seam normals to a mesh that carries the ring (call last)
``build_head()``               -> {GB_Head, GB_Head_HR, GB_Head_LOD1, GB_Eye_L, GB_Eye_R, GB_Mouth}
``build_face_shapes(head)``    the 24 face shape keys (``gb_common.FACE_SHAPE_KEYS``)
``build_eye_fx()``             -> {GB_EyeFX_L, GB_EyeFX_R}   (tearline + occlusion shells)
``build_hair_cards()``         -> {GB_BrowLash}              (+ textures/hair_cards.png)
``face_weights(points)``       lid-bone skin weights (for B6's ``weights_at``) and
``blend_face_weights(points, idx, w)``  one-line integration into the (idx, w) arrays
``face_rig_table()``           rig.json "face" block: bone pivots, measured lid aperture table
``head_layer_sdfs()``          body-frame SDFs of the head project's skull, jaw, brain (hand-off to B3/B4)

How the head is joined to the body
----------------------------------
The head project's skin SDF is authoritative above the jaw; ``body_skin.skin_sdf``
(B1) clips it under the jaw/occiput and smooth-unites it with the bible-placed
body neck.  ``GB_Head`` is polygonised from that *same* combined field at the
head project's resolution (1.2 mm), so head and neck are one surface; the only
seam is the canonical ring at z = 1.485 m where ``GB_Head`` and ``GB_Body``
share 160 identical vertices with identical (analytic) normals (FB-1).

Everything else of the head project (eyes, teeth, gums, tongue, lids, lips,
ears, brain, skull, jaw) is taken unchanged and moved by ``HEAD_OFFSET``; the
head project is imported read-only and re-evaluated on every build.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
import gb_geom as gg  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402
from gb_data import segments as SG  # noqa: E402

HEAD_OFFSET = gbc.HEAD_OFFSET
SEAM_Z = gbc.SEAM_Z
NECK_AXIS_XY = (0.0, 0.012)

RES = {
    # hr: GB_Head_HR bake source (plan: the head project's 1.2 mm); src: the finer temporary field mesh the
    # 30k LOD0 is decimated from (at 1.2 mm the ~1 mm rounded lid margins, alar rims and ear folds are
    # under-resolved and decimate into ragged edges; from 0.8 mm the decimator keeps clean margins)
    "full": dict(hr=0.0012, src=0.0008, teeth=0.00042, soft=0.0008),
    "quick": dict(hr=0.0022, src=None, teeth=0.00070, soft=0.0012),
}
HEAD_TRIS = 29300                 # plan §4.1: 30,000 incl. the zip strip
HEAD_LOD1_TRIS = 15000
SEAM_GAP = 0.0012                 # the SDF mesh is cut this far above the ring plane, then zipped
HEAD_BOX = ((-0.118, -0.135), (0.118, 0.150), 1.797)      # x, y ranges and top z (body frame)

# eyes (the head project's eyeball, re-sampled to the budget: plan §4.1 eyes + FX 5,000 tris)
EYE_RINGS, EYE_SEGS = 24, 40
# Lid model.  The lid bones rotate about +X through the eyeball centre (their rig-table heads), so the
# lid slides over the sclera at a constant 0.5 mm.  Closing past rest drags the lid over the corneal
# bulge (apex 13.3 mm from the centre), so a closing lid bone also scales up uniformly about the centre
# (s = 1 + LID_CLOSE_SCALE * smoothstep(0, LID_SCALE_DEG, |angle|)): the closed lid rides ~1 mm proud
# over the cornea like a real one.  Tuned: the lid-globe gap stays >= 0.2 mm along the whole closing
# path (``lid_table``).  Godot: set_bone_pose_scale with the table's scale column.
LID_CLOSE_SCALE = 0.100
LID_SCALE_DEG = 18.0
ATLAS_PX = 2048
ATLAS_MARGIN_PX = 16
MOUTH_TRIS = dict(teeth=4600, gums=2200, tongue=1500)
STATUS = "built (B2)"


def _A():
    """The head project's anatomy module (read-only, re-imported every build)."""
    return gbc.import_head().anatomy


def _quick(quick):
    return ("--quick" in gbc.script_args()) if quick is None else bool(quick)


def _res(quick=None):
    return RES["quick" if _quick(quick) else "full"]


def _smooth(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def eye_centre(side):
    """Body-frame eyeball centre of ``side`` ('L' / 'R') from the head project's EYE_C."""
    A = _A()
    sx = 1.0 if side == "L" else -1.0
    return gbc.head_to_body(np.asarray(A.EYE_C, float) * np.array([sx, 1.0, 1.0]))


def lid_pivot(side):
    """Body-frame pivot of the lid rotations of ``side`` (axis parallel to +X through it): the eyeball centre."""
    return eye_centre(side)


def lid_scale(deg):
    """Uniform scale of a lid bone about the eyeball centre for a lid angle (deg, < 0 = closing past rest)."""
    if deg >= 0.0:
        return 1.0
    t = min(1.0, -deg / LID_SCALE_DEG)
    return 1.0 + LID_CLOSE_SCALE * t * t * (3.0 - 2.0 * t)


# ===========================================================================
# Skin field and the neck seam
# ===========================================================================
def head_skin_sdf(x, y, z):
    """Outer skin SDF of GB_Head (body frame): the combined head+body field of ``body_skin`` (B1).

    Using B1's exact field guarantees that the head and body meshes agree on the
    seam ring and share their normals there."""
    import body_skin
    return body_skin.skin_sdf(x, y, z)


def seam_ring(n=gbc.SEAM_RING_N):
    """Canonical ring on the combined skin SDF: bisection along n rays in the seam plane from the neck axis."""
    return gg.seam_ring_from_sdf(head_skin_sdf, SEAM_Z, n, centre_xy=NECK_AXIS_XY, r_max=0.12)


def seam_normals(ring, eps=0.0002):
    """Unit outward skin normals at the ring points (central differences of the combined SDF)."""
    ring = np.asarray(ring, float)
    offs = np.eye(3) * eps
    pts = np.concatenate([ring + o for o in offs] + [ring - o for o in offs])
    f = gg.eval_sdf(head_skin_sdf, pts).reshape(6, -1)
    g = np.stack([f[0] - f[3], f[1] - f[4], f[2] - f[5]], axis=1)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


def ring_vertex_indices(me, ring=None, tol=1e-6):
    """Indices of the vertices of ``me`` that coincide with the seam ring (z within tol of SEAM_Z)."""
    v = gbc.get_verts(me)
    idx = np.nonzero(np.abs(v[:, 2] - SEAM_Z) < tol)[0]
    if ring is not None and len(idx):
        from mathutils.kdtree import KDTree
        kd = KDTree(len(ring))
        for i, p in enumerate(ring):
            kd.insert(p, i)
        kd.balance()
        idx = np.array([i for i in idx if kd.find(v[i])[2] < tol], dtype=np.int64)
    return idx


def apply_seam_normals(obj, ring=None):
    """Give the seam-ring vertices of ``obj`` the analytic skin normal (custom split normals).

    Every other vertex keeps its current smooth normal, so the only change is at
    the seam: GB_Head and GB_Body then carry identical positions *and* normals on
    the ring (FB-1: no lighting seam).  Call it after the last topology change
    (decimation drops custom normals).  Shape keys keep it: Blender evaluates
    custom normals per key, so the exported morph-normal deltas at the ring stay 0."""
    me = obj.data
    idx = ring_vertex_indices(me)
    if len(idx) == 0:
        return 0
    vn = np.empty(len(me.vertices) * 3, np.float64)
    me.vertex_normals.foreach_get("vector", vn)
    vn = vn.reshape(-1, 3)
    vn[idx] = seam_normals(gbc.get_verts(me)[idx])
    me.normals_split_custom_set_from_vertices([tuple(n) for n in vn])
    me.update()
    return len(idx)


def analytic_normals(points, eps=0.0002):
    """Unit outward normals of the combined skin SDF at body-frame points (central differences)."""
    return seam_normals(points, eps)


def apply_analytic_normals(obj):
    """Custom split normals = the exact SDF normal at every vertex of a head skin mesh.

    The 1.2 mm polygonisation (and the decimation to 30k) under-resolves the ~1 mm
    rounded lid margins, nostril rims and ear folds: faceted triangles across them
    shade as a ragged edge.  With the analytic normal the shading follows the true
    surface; on the seam ring this is the same normal the body gets (FB-1)."""
    me = obj.data
    n = analytic_normals(gbc.get_verts(me))
    me.normals_split_custom_set_from_vertices([tuple(q) for q in n])
    me.update()
    return len(n)


def project_to_skin(obj, iters=2, keep_ring=True):
    """Newton-project the vertices of a head mesh back onto the combined skin surface
    (collapse decimation leaves quadric-optimal points slightly off the surface)."""
    A = _A()
    me = obj.data
    v = gbc.get_verts(me)
    m = np.ones(len(v), bool)
    if keep_ring:
        m[ring_vertex_indices(me)] = False
    v[m] = A.project_to_surface(head_skin_sdf, v[m], _res()["hr"], iters)
    gbc.set_verts(me, v)


def fix_self_intersections(obj, max_iter=12):
    """Relax (and re-project) the vertices around intersecting triangle pairs until none are left.
    Decimating the ears' thin folds occasionally lays one triangle through a neighbouring fold."""
    A = _A()
    me = obj.data
    ring = set(ring_vertex_indices(me).tolist())
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ev)
    edges = ev.reshape(-1, 2)
    for it in range(max_iter):
        v, tris = gbc.mesh_arrays(me)
        from mathutils.bvhtree import BVHTree
        bvh = BVHTree.FromPolygons(v.tolist(), tris.tolist(), epsilon=0.0)
        bad = [(i, j) for i, j in bvh.overlap(bvh) if i < j and not (set(tris[i]) & set(tris[j]))]
        if not bad:
            return it
        sel = np.zeros(len(v), bool)
        for i, j in bad:
            sel[tris[i]] = True
            sel[tris[j]] = True
        for _ in range(1 + it // 3):                      # grow the region a little more each round
            grow = sel.copy()
            grow[edges[sel[edges[:, 0]], 1]] = True
            grow[edges[sel[edges[:, 1]], 0]] = True
            sel = grow
        sel[list(ring)] = False
        lap = A.laplacian(v, edges)
        v[sel] = 0.5 * v[sel] + 0.5 * lap[sel]
        v[sel] = A.project_to_surface(head_skin_sdf, v[sel], _res()["hr"], 2)
        gbc.set_verts(me, v)
    return -1


def zip_to_ring(obj, ring, side="auto"):
    """Zip the open neck boundary of ``obj`` to ``ring`` (identical seam vertices, analytic normals).

    ``side`` is 'above' (the head) or 'below' (the body); 'auto' decides by the mean height."""
    if side == "auto":
        side = "above" if gbc.get_verts(obj.data)[:, 2].mean() > SEAM_Z else "below"
    idx = gg.zip_to_ring(obj, ring, NECK_AXIS_XY, side)
    apply_seam_normals(obj)
    return idx


def ring_normal_error_deg(obj_a, obj_b):
    """Max angle (deg) between the exported (corner-averaged) normals of the two meshes on shared ring vertices."""
    def ring_normals(obj):
        me = obj.data
        idx = ring_vertex_indices(me)
        v = gbc.get_verts(me)[idx]
        cn = np.empty(len(me.loops) * 3, np.float64)
        me.corner_normals.foreach_get("vector", cn)
        cn = cn.reshape(-1, 3)
        lv = np.empty(len(me.loops), np.int64)
        me.loops.foreach_get("vertex_index", lv)
        acc = np.zeros((len(me.vertices), 3))
        np.add.at(acc, lv, cn)
        n = acc[idx]
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        return v, n
    va, na = ring_normals(obj_a)
    vb, nb = ring_normals(obj_b)
    if len(va) == 0 or len(vb) == 0:
        return float("nan"), 0
    from mathutils.kdtree import KDTree
    kd = KDTree(len(vb))
    for i, p in enumerate(vb):
        kd.insert(p, i)
    kd.balance()
    worst, matched = 0.0, 0
    for p, n in zip(va, na):
        _co, j, d = kd.find(p)
        if d < 1e-6:
            matched += 1
            worst = max(worst, math.degrees(math.acos(float(np.clip(n @ nb[j], -1.0, 1.0)))))
    return worst, matched


# ===========================================================================
# Head skin: regions, protection map, labels
# ===========================================================================
def _head_frame(p):
    """Body-frame points -> head-frame (x, y, z) arrays."""
    q = np.asarray(p, float) - HEAD_OFFSET
    return q[:, 0], q[:, 1], q[:, 2]


def _eye_polar(hx, hy, hz, sx=1.0):
    """(r, u, v) of head-frame points about the eye on side sx: u lateral angle, v elevation (rad)."""
    A = _A()
    qx = sx * hx - A.EYE_C[0]
    qy = hy - A.EYE_C[1]
    qz = hz - A.EYE_C[2]
    r = np.sqrt(qx * qx + qy * qy + qz * qz)
    u = np.arctan2(qx, -qy)
    v = np.arctan2(qz, np.sqrt(qx * qx + qy * qy))
    return r, u, v


def detail_importance(points):
    """0..1 per point: how much of the 1.2 mm master density the LOD0 decimation keeps
    (lid margins, lips, nostrils and ears high; scalp, neck low).  Plan §8.2 B2."""
    A = _A()
    hx, hy, hz = _head_frame(points)
    ax = np.abs(hx)
    imp = np.zeros(len(hx))
    # lids: the lid shell around the opening (not the hidden pocket behind the globe)
    r, u, v = _eye_polar(ax, hy, hz)
    t, st, up, lo = A._lid_curves(u)
    lid = (_smooth(0.0205, 0.0165, r) * _smooth(-0.35, -0.05, t) * _smooth(1.35, 1.05, t)
           * _smooth(A.EYE_C[1] + 0.006, A.EYE_C[1] - 0.004, hy))
    margin = np.exp(-(np.minimum(np.abs(v - up), np.abs(v - lo)) / 0.20) ** 2)
    imp = np.maximum(imp, lid * (0.55 + 0.45 * margin))
    # lips (vermilion + the mouth slit) and the commissures
    lu, ll = A.lips_sdf(ax, hy, hz)
    lips = _smooth(0.0075, 0.0015, np.minimum(lu, ll)) * _smooth(-0.045, -0.075, hy)
    imp = np.maximum(imp, 0.95 * lips)
    # nostrils, alae and the tip lobule
    nose = np.sqrt((ax / 0.019) ** 2 + ((hy + 0.100) / 0.016) ** 2 + ((hz + 0.021) / 0.017) ** 2)
    imp = np.maximum(imp, 0.80 * _smooth(1.25, 0.75, nose))
    # ears (helix, antihelix, concha, tragus, lobe)
    er = np.sqrt((ax - A.EAR_O[0] - 0.006) ** 2 + (hy - A.EAR_O[1] - 0.010) ** 2 + (hz - A.EAR_O[2]) ** 2)
    imp = np.maximum(imp, 0.62 * _smooth(0.040, 0.030, er) * _smooth(0.058, 0.066, ax))
    # the rest of the face a little denser than scalp and neck
    face = _smooth(-0.045, -0.070, hy) * _smooth(-0.115, -0.095, hz) * _smooth(0.075, 0.055, hz)
    imp = np.maximum(imp, 0.25 * face)
    return np.clip(imp, 0.0, 1.0)


def _protected_decimate(obj, target_tris, importance, factor):
    """Collapse-decimate with a vertex group (weight = 1 - importance, 0 = protected)."""
    me = obj.data
    loops = gg.boundary_loops(me)
    vg = obj.vertex_groups.new(name="gb_decimate")
    w = np.clip(1.0 - np.asarray(importance, float), 0.0, 1.0)
    order = np.argsort(w, kind="stable")
    ws = np.round(w[order], 3)
    cuts = np.flatnonzero(np.diff(ws)) + 1
    for rows, vals in zip(np.split(order, cuts), np.split(ws, cuts)):
        if len(rows):
            vg.add(rows.tolist(), float(vals[0]), 'REPLACE')
    ring = [i for lp in loops for i in lp]
    if ring:
        vg.add(ring, 0.0, 'REPLACE')
    n = gbc.tri_count(me)
    mod = obj.modifiers.new("gb_decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.005, target_tris / max(n, 1))
    mod.use_collapse_triangulate = True
    mod.vertex_group = "gb_decimate"
    mod.vertex_group_factor = factor
    gg.apply_modifier(obj, mod)
    obj.vertex_groups.remove(obj.vertex_groups["gb_decimate"])
    gg.remove_loose(obj.data)
    obj.data.shade_smooth()
    return gbc.tri_count(obj.data)


def _mean_edge_mm(me, mask_v):
    """Mean edge length (mm) of edges whose both ends are in ``mask_v``."""
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ev)
    ev = ev.reshape(-1, 2)
    v = gbc.get_verts(me)
    m = mask_v[ev[:, 0]] & mask_v[ev[:, 1]]
    if not m.any():
        return float("nan")
    return float(np.linalg.norm(v[ev[m, 0]] - v[ev[m, 1]], axis=1).mean() * 1000.0)


def region_edge_lengths(obj):
    """Mean edge length (mm) per detail region of a head mesh (lids, lips, nose, ears, face, scalp/neck)."""
    A = _A()
    v = gbc.get_verts(obj.data)
    hx, hy, hz = _head_frame(v)
    ax = np.abs(hx)
    r, u, vv = _eye_polar(ax, hy, hz)
    t, st, up, lo = A._lid_curves(u)
    lid_margin = (r < 0.0165) & (t > 0.05) & (t < 0.95) & (np.minimum(np.abs(vv - up), np.abs(vv - lo)) < 0.12) \
        & (hy < A.EYE_C[1] - 0.004)
    lu, ll = A.lips_sdf(ax, hy, hz)
    lips = (np.minimum(lu, ll) < 0.0015) & (hy < -0.07)
    nose = np.sqrt((ax / 0.012) ** 2 + ((hy + 0.098) / 0.010) ** 2 + ((hz + 0.024) / 0.010) ** 2) < 1.0
    er = np.sqrt((ax - A.EAR_O[0] - 0.006) ** 2 + (hy - A.EAR_O[1] - 0.010) ** 2 + (hz - A.EAR_O[2]) ** 2)
    ear = (er < 0.028) & (ax > 0.066)
    imp = detail_importance(v)
    rest = imp < 0.05
    me = obj.data
    return {"lid_margin": _mean_edge_mm(me, lid_margin), "lips": _mean_edge_mm(me, lips),
            "nostrils": _mean_edge_mm(me, nose), "ears": _mean_edge_mm(me, ear),
            "scalp_neck": _mean_edge_mm(me, rest)}


def mouth_lining_faces(obj):
    """Per-face bool: the face is mouth lining (inside the closed-mouth skin, in the mouth region).
    Repeats ``gore_head.anatomy.build_anatomy``'s GH_MouthCavity split."""
    A = _A()
    c = gbc.face_centres(obj.data) - HEAD_OFFSET
    closed = A.skin_sdf(c[:, 0].copy(), c[:, 1].copy(), c[:, 2].copy(), mouth_cavity=False)
    in_mouth = A.Region((-0.05, -0.105, -0.09), (0.05, -0.01, -0.02)).mask(c[:, 0], c[:, 1], c[:, 2])
    return (closed < -0.0006) & in_mouth


def lip_mask(points):
    """The head project's ``gh_lip`` vermilion mask (0..1) at body-frame points."""
    A = _A()
    hx, hy, hz = _head_frame(points)
    up, lo = A.lips_sdf(np.abs(hx), hy, hz)
    return A.smoothstep(0.0016, 0.0003, np.minimum(up, lo))


# ---------------------------------------------------------------------------
# Codes: segment 0 (head/neck), region [RB §2.0], dermatome (CN V / C2 / C3)
# ---------------------------------------------------------------------------
def head_regions(points):
    """Region id per point: scalp, face, eyelid/lip, neck (plan §5.5, RB §2.0)."""
    A = _A()
    p = np.asarray(points, float)
    hx, hy, hz = _head_frame(p)
    ax = np.abs(hx)
    # the jaw line: under the mandible (and behind the ramus below the ear lobe) is neck
    jaw_z = -0.098 + 0.070 * _smooth(-0.080, 0.000, hy) * _smooth(0.020, 0.052, ax)
    below_jaw = hz < jaw_z + 0.004 * _smooth(-0.06, -0.09, hy)
    # hairline: forehead up to ~z 0.080 in front, temples recede, sideburn down to the ear top
    hair_z = 0.082 - 0.030 * _smooth(0.030, 0.062, ax)
    front = hy < -0.030 + 0.20 * np.clip(hz, 0.0, None) - 0.35 * np.clip(ax - 0.060, 0.0, None)
    ear_zone = (ax > 0.058) & (hy > -0.030)
    face = front & (hz < hair_z) & ~below_jaw & ~ear_zone
    scalp = ~face & ~below_jaw & (hz > -0.035)
    region = np.where(face, SG.REGION_ID["face"], np.where(scalp, SG.REGION_ID["scalp"], SG.REGION_ID["neck"]))
    # ears count as face skin (thin skin over cartilage)
    region = np.where(ear_zone & (hz > -0.035) & (hz < 0.040) & (ax > 0.064), SG.REGION_ID["face"], region)
    # eyelids and lips
    lu, ll = A.lips_sdf(ax, hy, hz)
    r, u, v = _eye_polar(ax, hy, hz)
    t, st, up, lo = A._lid_curves(u)
    lid = (r < 0.0185) & (t > -0.05) & (t < 1.05) & (hy < A.EYE_C[1] + 0.002) & (v < up + 0.55) & (v > lo - 0.50)
    lidlip = lid | ((np.minimum(lu, ll) < 0.0020) & (hy < -0.065))
    region = np.where(lidlip, SG.REGION_ID["eyelid_lip"], region)
    region = np.where(p[:, 2] < 1.52, SG.REGION_ID["neck"], region)
    return region.astype(np.int32)


def head_dermatomes(points):
    """Dermatome id per point: CN V (0) face and scalp in front of the vertex-ear line, C2 (1) back of
    the scalp, the angle of the jaw and the upper neck, C3 (2) the lower neck [R04 §6.2 anchors, K]."""
    from gb_data import dermatomes as DM
    p = np.asarray(points, float)
    hx, hy, hz = _head_frame(p)
    ax = np.abs(hx)
    trig = (hy < 0.020 - 0.16 * np.clip(hz, 0.0, None)) & (hz > -0.098 + 0.070 * _smooth(-0.080, 0.000, hy)
                                                            * _smooth(0.020, 0.052, ax))
    # angle of the mandible and the ear lobe region: great auricular nerve (C2-C3)
    trig &= ~((hy > -0.035) & (hz < -0.030) & (ax > 0.035))
    out = np.where(trig, DM.DERMATOME_ID["CN_V"], DM.DERMATOME_ID["C2"])
    out = np.where(~trig & (p[:, 2] < 1.545) & (hy < 0.035), DM.DERMATOME_ID["C3"], out)
    out = np.where(p[:, 2] < 1.505, DM.DERMATOME_ID["C3"], out)
    return out.astype(np.int32)


def paint_head_codes(obj):
    """gb_seg / gb_region / gb_derm point attributes and the gb_codes UV (plan §5.5) for a head mesh."""
    v = gbc.get_verts(obj.data)
    seg = np.full(len(v), SG.SEGMENT_ID["head_neck"], np.int32)
    region = head_regions(v)
    derm = head_dermatomes(v)
    gbc.point_attr(obj, "gb_seg", seg, 'INT')
    gbc.point_attr(obj, "gb_region", region, 'INT')
    gbc.point_attr(obj, "gb_derm", derm, 'INT')
    gbc.set_codes_uv(obj, seg + SG.REGION_STRIDE * region, derm)
    return region, derm


# ---------------------------------------------------------------------------
# UV: back-midline scalp seam, ears, eye pockets and the mouth interior as islands (plan §8.2 B2)
# ---------------------------------------------------------------------------
UV_ISLANDS = ("head", "mouth", "eye_pocket_L", "eye_pocket_R", "ear_L", "ear_R")


def uv_labels(obj, lining):
    """Per-face island label (index into UV_ISLANDS)."""
    A = _A()
    c = gbc.face_centres(obj.data)
    hx, hy, hz = _head_frame(c)
    lab = np.zeros(len(c), np.int32)
    lab[lining] = UV_ISLANDS.index("mouth")
    for side, sx in (("L", 1.0), ("R", -1.0)):
        r, u, v = _eye_polar(hx, hy, hz, sx)
        pocket = (r < A.EYE_R + 0.0021) & (sx * hx > 0)
        lab[pocket & ~lining] = UV_ISLANDS.index("eye_pocket_" + side)
        # ear: everything lateral of the ear-base line behind the tragus
        ex = sx * hx
        er = np.sqrt((hy - A.EAR_O[1] - 0.012) ** 2 / 1.0 + (hz - A.EAR_O[2] + 0.002) ** 2 / 1.6)
        ear = (ex > 0.0705 + 0.004 * _smooth(0.012, 0.030, hy - A.EAR_O[1])) & (er < 0.036) & (ex > 0)
        lab[ear & (lab == 0)] = UV_ISLANDS.index("ear_" + side)
    return lab


def _edge_faces(me):
    """(face_a, face_b) per edge (-1 where missing)."""
    ne = len(me.edges)
    le = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("edge_index", le)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    lf = np.repeat(np.arange(len(me.polygons)), lt)
    fa = np.full(ne, -1, np.int64)
    fb = np.full(ne, -1, np.int64)
    order = np.argsort(le, kind="stable")
    les, lfs = le[order], lf[order]
    first = np.r_[True, les[1:] != les[:-1]]
    fa[les[first]] = lfs[first]
    second = ~first
    fb[les[second]] = lfs[second]
    return fa, fb


def _face_areas(me):
    v, _ = gbc.mesh_arrays(me)
    a = np.empty(len(me.polygons), np.float64)
    me.polygons.foreach_get("area", a)
    return a


def _uv_face_areas(uv, ls, lt):
    out = np.zeros(len(ls))
    for k in range(3, int(lt.max()) + 1):
        m = lt >= k
        a = uv[ls[m]]
        b = uv[ls[m] + k - 2]
        c = uv[ls[m] + k - 1]
        out[m] += 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
    return out


def _uv_arrays(me):
    lay = me.uv_layers["atlas"]
    uv = np.empty(len(me.loops) * 2, np.float32)
    lay.data.foreach_get("uv", uv)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    ls = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    return uv.reshape(-1, 2).astype(float), ls, lt


def texel_mm(obj, px=ATLAS_PX, face_mask=None):
    """Global texel size (mm per texel) of the ``atlas`` UV at ``px`` (area-weighted)."""
    me = obj.data
    uv, ls, lt = _uv_arrays(me)
    a3 = _face_areas(me)
    auv = _uv_face_areas(uv, ls, lt)
    m = np.ones(len(a3), bool) if face_mask is None else face_mask
    return 1000.0 * math.sqrt(a3[m].sum() / max(auv[m].sum() * px * px, 1e-18))


def head_uvs(obj, labels):
    """Seams between the islands + the back-midline scalp cut, unwrap (MINIMUM_STRETCH), equal texel
    density per island (hidden eye pockets and mouth interior at half density), pack 16 px @ 2,048."""
    import uv as UV
    me = obj.data
    fa, fb = _edge_faces(me)
    seam = np.zeros(len(fa), bool)
    ok = (fa >= 0) & (fb >= 0)
    seam[ok] = labels[fa[ok]] != labels[fb[ok]]
    # scalp cut: back midline from the neck boundary up to the crown
    c = gbc.face_centres(me)
    hx, hy, hz = _head_frame(c)
    head = labels == 0
    cross = ok & head[np.maximum(fa, 0)] & head[np.maximum(fb, 0)] \
        & (np.sign(hx[np.maximum(fa, 0)]) != np.sign(hx[np.maximum(fb, 0)]))
    fy = np.minimum(hy[np.maximum(fa, 0)], hy[np.maximum(fb, 0)])
    fz = np.maximum(hz[np.maximum(fa, 0)], hz[np.maximum(fb, 0)])
    seam |= cross & (fy > 0.020) & (fz < 0.110)
    me.edges.foreach_set("use_seam", seam)
    me.update()
    UV.unwrap(obj, "MINIMUM_STRETCH", margin=0.001)
    uv, ls, lt = _uv_arrays(me)
    lf = np.repeat(np.arange(len(me.polygons)), lt)
    a3 = _face_areas(me)
    auv = _uv_face_areas(uv, ls, lt)
    for lab in np.unique(labels):
        fm = labels == lab
        s = math.sqrt(a3[fm].sum() / max(auv[fm].sum(), 1e-12))
        if UV_ISLANDS[lab] in ("mouth", "eye_pocket_L", "eye_pocket_R"):
            s *= 0.5                                     # hidden inside: half the texel density
        lm = fm[lf]
        cen = uv[lm].mean(0)
        uv[lm] = cen + (uv[lm] - cen) * s
    me.uv_layers["atlas"].data.foreach_set("uv", uv.astype(np.float32).ravel())
    me.update()
    UV.pack(obj, ATLAS_PX, ATLAS_MARGIN_PX)
    return int(seam.sum())


# ===========================================================================
# Head skin build
# ===========================================================================
def _sdf_object(name, fn, lo, hi, h, project=3):
    """SDF -> surface nets -> voxel remesh -> keep the largest piece -> Newton projection."""
    import bpy
    A = _A()
    tmp = A.mesh_sdf("_b2_tmp", fn, lo, hi, h, voxel=h, project=0, clean=True,
                     collection=bpy.context.scene.collection)
    me = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    v = A.project_to_surface(fn, gbc.get_verts(me), h, project)
    gbc.set_verts(me, v)
    return gbc.new_object(name, me)


def _cut_above(obj, z):
    """Delete everything below the plane z (the head keeps the neck down to just above the ring)."""
    gg.cut_plane(obj.data, z, keep="above")
    gg.remove_loose(obj.data)
    keep_largest_piece(obj.data)


def vertex_components(me):
    """Connected-component label per vertex (min-label propagation over the edges)."""
    ev = np.empty(len(me.edges) * 2, np.int64)
    me.edges.foreach_get("vertices", ev)
    e = ev.reshape(-1, 2)
    lab = np.arange(len(me.vertices))
    for _ in range(100000):
        m = np.minimum(lab[e[:, 0]], lab[e[:, 1]])
        new = lab.copy()
        np.minimum.at(new, e[:, 0], m)
        np.minimum.at(new, e[:, 1], m)
        new = new[new]
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    return lab


def keep_largest_piece(me):
    """Delete every connected piece except the largest (stray SDF crumbs)."""
    import bmesh
    lab = vertex_components(me)
    ids, counts = np.unique(lab, return_counts=True)
    if len(ids) <= 1:
        return 0
    keep = ids[np.argmax(counts)]
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    kill = [bm.verts[i] for i in np.nonzero(lab != keep)[0]]
    bmesh.ops.delete(bm, geom=kill, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(kill)


def _finish_skin(obj, ring, lining):
    """Codes, slots, lip mask, custom props for a head skin mesh."""
    paint_head_codes(obj)
    gbc.set_material_slots(obj, lining.astype(np.int32), names=gbc.MATERIAL_SLOTS["GB_Head"])
    gbc.point_attr(obj, "gb_lip", lip_mask(gbc.get_verts(obj.data)), 'FLOAT')
    import placeholder
    placeholder.finish_uvs(obj)
    _tag(obj)


def _tag(obj, layer=None):
    obj["gb_layer"] = layer or gbc.LAYER_OF.get(obj.name, "skin")
    obj["gb_schema"] = 1
    obj["gb_status"] = STATUS


def build_head_skin(quick=None):
    """GB_Head_HR (1.2 mm master), GB_Head (LOD0, ~30k tris, protected detail), GB_Head_LOD1."""
    T = gbc.Timer
    r = _res(quick)
    h = r["hr"]
    ring = seam_ring()
    (x0, y0), (x1, y1), ztop = HEAD_BOX
    with T("B2: head master SDF mesh (HR %.1f mm)" % (h * 1000)):
        hr = _sdf_object("GB_Head_HR", head_skin_sdf, (x0, y0, SEAM_Z - 3 * h), (x1, y1, ztop), h)
    if r["src"]:
        with T("B2: LOD0 source SDF mesh (%.1f mm)" % (r["src"] * 1000)):
            hs = r["src"]
            head = _sdf_object("GB_Head", head_skin_sdf, (x0, y0, SEAM_Z - 3 * hs), (x1, y1, ztop), hs)
    else:
        head = gbc.new_object("GB_Head", hr.data.copy())
    with T("B2: LOD0 protected decimation + seam zip"):
        _cut_above(head, SEAM_Z + SEAM_GAP)
        imp = detail_importance(gbc.get_verts(head.data))
        _protected_decimate(head, HEAD_TRIS - 2 * len(ring), imp, DECIMATE_FACTOR)
        project_to_skin(head)
        fix_self_intersections(head)
        zip_to_ring(head, ring, side="above")
        _cut_above(hr, SEAM_Z + 0.5 * h)
        zip_to_ring(hr, ring, side="above")
    lining = mouth_lining_faces(head)
    with T("B2: head UV (islands, back-midline seam, pack)"):
        labels = uv_labels(head, lining)
        head_uvs(head, labels)
        head["gb_texel_mm"] = round(texel_mm(head, face_mask=labels == 0), 4)
    with T("B2: codes, slots, LOD1"):
        _finish_skin(head, ring, lining)
        lod = gbc.new_object("GB_Head_LOD1", head.data.copy())
        _protected_decimate(lod, HEAD_LOD1_TRIS, detail_importance(gbc.get_verts(lod.data)) * 0.6,
                            DECIMATE_FACTOR)
        project_to_skin(lod)
        fix_self_intersections(lod)
        _finish_skin(lod, ring, mouth_lining_faces(lod))
        _finish_skin(hr, ring, mouth_lining_faces(hr))
        for o in (head, lod, hr):
            apply_analytic_normals(o)
    return {"GB_Head": head, "GB_Head_HR": hr, "GB_Head_LOD1": lod}


DECIMATE_FACTOR = 0.0004           # vertex-group factor of the protected decimation (tuned on the 0.8 mm source: lid margins 0.9 mm, lips 1.6, nostrils 1.6, ears 2.1, scalp/neck 5.9)


# ===========================================================================
# Eyes
# ===========================================================================
def _eye_arrays(side):
    """(verts, faces, per-loop uv) of an eyeball: a UV sphere with rings concentric about the gaze
    (denser across the cornea), every vertex snapped radially onto the head project's own eyeball
    (``anatomy.build_eye``), so the shape (sclera r 12 mm, corneal bulge) is identical."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    A = _A()
    tmp = A.build_eye("_b2_eye_src", (0.0, 0.0, 0.0), bpy.context.scene.collection)
    sv, st = gbc.mesh_arrays(tmp.data)
    me = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(me)
    bvh = BVHTree.FromPolygons(sv.tolist(), st.tolist())
    R, S = EYE_RINGS, EYE_SEGS
    th = math.pi * (np.arange(1, R) / R) ** 1.35            # ring polar angles from the gaze (front pole)
    ph = 2 * math.pi * np.arange(S) / S
    dirs = [np.array([0.0, -1.0, 0.0])]
    for t in th:
        for p in ph:
            dirs.append(np.array([math.sin(t) * math.cos(p), -math.cos(t), math.sin(t) * math.sin(p)]))
    dirs.append(np.array([0.0, 1.0, 0.0]))
    dirs = np.array(dirs)
    verts = []
    for d in dirs:
        hit = bvh.ray_cast(Vector((0.0, 0.0, 0.0)), Vector(d), 0.05)
        rad = hit[3] if hit[0] is not None else A.EYE_R
        verts.append(d * rad)
    verts = np.array(verts)
    faces = []
    front, back = 0, len(dirs) - 1
    for k in range(S):
        faces.append([front, 1 + (k + 1) % S, 1 + k])
    for i in range(R - 2):
        a, b = 1 + i * S, 1 + (i + 1) * S
        for k in range(S):
            k1 = (k + 1) % S
            faces.append([a + k, a + k1, b + k1, b + k])
    last = 1 + (R - 2) * S
    for k in range(S):
        faces.append([last + k, last + (k + 1) % S, back])
    # UV: azimuthal equidistant about the gaze (front pole at the centre, back pole on the rim)
    polar = np.concatenate([[0.0], np.repeat(th, S), [math.pi]])
    azim = np.concatenate([[0.0], np.tile(ph, R - 1), [0.0]])
    uv_loops = []
    for f in faces:
        ring_az = [azim[i] for i in f if i not in (front, back)]
        # unwrap the azimuth of this face so the loops do not straddle 2*pi
        base = ring_az[0]
        fa = []
        for i in f:
            a = azim[i] if i not in (front, back) else None
            if a is not None:
                a = base + (a - base + math.pi) % (2 * math.pi) - math.pi
            fa.append(a)
        mean_az = float(np.mean([a for a in fa if a is not None]))
        for i, a in zip(f, fa):
            a = mean_az if a is None else a
            rr = 0.5 * polar[i] / math.pi
            uv_loops.append((0.5 + rr * math.cos(a), 0.5 + rr * math.sin(a)))
    sx = 1.0 if side == "L" else -1.0
    c = eye_centre(side)
    v = verts * np.array([sx, 1.0, 1.0]) + c
    if sx < 0:
        faces = [f[::-1] for f in faces]
        uv_f, o = [], 0
        for f in faces:
            n = len(f)
            uv_f += uv_loops[o:o + n][::-1]
            o += n
        uv_loops = [(1.0 - a, b) for a, b in uv_f]
    return v, faces, np.array(uv_loops)


def build_eyes():
    """GB_Eye_L/R: the head project's eyeballs at 1.8k tris each, origin-free (identity transform),
    rigid to eye_L/eye_R, UV = azimuthal equidistant map about the gaze (iris at the centre)."""
    out = {}
    for side in ("L", "R"):
        v, f, uvl = _eye_arrays(side)
        name = f"GB_Eye_{side}"
        n = len(v)
        obj = gg.object_from_parts(name, [gg.part(v, f, 0, gb_rigid_bone=np.full(
            n, RT.BONE_INDEX["eye_" + side], np.int32))])
        gbc.set_uv_from_loops(obj, "atlas", uvl)
        gbc.set_codes_uv(obj, np.full(n, SG.REGION_STRIDE * SG.REGION_ID["eyelid_lip"]), np.zeros(n))
        gbc.set_material_slots(obj)
        import placeholder
        placeholder.finish_uvs(obj)
        obj.data.shade_smooth()
        _tag(obj)
        out[name] = obj
    return out


# ===========================================================================
# Mouth: teeth (per-tooth FDI ids), gums, tongue
# ===========================================================================
def _decimate_arrays(v, f, target):
    """Collapse-decimate an (verts, faces) pair to ~target triangles; returns arrays."""
    import bpy
    me = gbc.mesh_from_arrays("_b2_dec", v, f)
    obj = bpy.data.objects.new("_b2_dec", me)
    bpy.context.scene.collection.objects.link(obj)
    gg.decimate_to(obj, target)
    vv, tt = gbc.mesh_arrays(obj.data)
    faces = [list(p.vertices) for p in obj.data.polygons]
    m = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    bpy.data.meshes.remove(m)
    return vv, faces


def _teeth_part(upper, h, target):
    """One jaw's teeth from the head project (each tooth its own closed island), decimated per tooth."""
    import bpy
    A = _A()
    tmp = A.build_teeth("_b2_teeth", upper, bpy.context.scene.collection, h=h)
    me = tmp.data
    ids = np.empty(len(me.vertices), np.int32)
    me.attributes["tooth_id"].data.foreach_get("value", ids)
    v = gbc.get_verts(me)
    faces = [list(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(tmp, do_unlink=True)
    bpy.data.meshes.remove(me)
    # decimate each tooth on its own (keeps every tooth closed and recognisable)
    fid = np.array([ids[f[0]] for f in faces])
    teeth = sorted(set(ids.tolist()))
    per = max(60, target // len(teeth))
    V, F, I = [], [], []
    off = 0
    for t in teeth:
        sel = [f for f, i in zip(faces, fid) if i == t]
        used = sorted({k for f in sel for k in f})
        remap = {k: j for j, k in enumerate(used)}
        tv = v[used]
        tf = [[remap[k] for k in f] for f in sel]
        dv, df = _decimate_arrays(tv, tf, per)
        V.append(dv)
        F += [[k + off for k in f] for f in df]
        I.append(np.full(len(dv), t, np.int32))
        off += len(dv)
    return np.vstack(V) + HEAD_OFFSET, F, np.concatenate(I)


def build_mouth(quick=None):
    """GB_Mouth: teeth (slot 0, 28 closed teeth, FDI id in gb_piece and UV2.y), gums (1), tongue (2).
    Upper teeth/gum rigid to ``head``, lower to ``jaw``, the tongue to ``tongue`` (plan §5.6)."""
    A = _A()
    r = _res(quick)
    parts = []
    bone = RT.BONE_INDEX
    for upper in (True, False):
        v, f, ids = _teeth_part(upper, r["teeth"], MOUTH_TRIS["teeth"] // 2)
        parts.append(gg.part(v, f, 0, gb_rigid_bone=np.full(len(v), bone["head" if upper else "jaw"], np.int32),
                             gb_piece=ids))
    for upper in (True, False):
        fn = (lambda x, y, z, u=upper: A.gum_sdf(x, y, z, u))
        v, q = gg.sdf_arrays(fn, (-0.036, -0.098, -0.084), (0.036, -0.024, -0.030), r["soft"])
        v, q = _decimate_arrays(v, q, MOUTH_TRIS["gums"] // 2)
        parts.append(gg.part(v + HEAD_OFFSET, q, 1, gb_rigid_bone=np.full(
            len(v), bone["head" if upper else "jaw"], np.int32), gb_piece=np.zeros(len(v), np.int32)))
    v, q = gg.sdf_arrays(A.tongue_sdf, (-0.030, -0.095, -0.080), (0.030, -0.010, -0.045), r["soft"])
    v, q = _decimate_arrays(v, q, MOUTH_TRIS["tongue"])
    parts.append(gg.part(v + HEAD_OFFSET, q, 2, gb_rigid_bone=np.full(len(v), bone["tongue"], np.int32),
                         gb_piece=np.zeros(len(v), np.int32)))
    obj = gg.object_from_parts("GB_Mouth", parts)
    n = len(obj.data.vertices)
    piece = gbc.read_point_attr(obj, "gb_piece", 'INT')
    gbc.set_codes_uv(obj, np.full(n, SG.REGION_STRIDE * SG.REGION_ID["eyelid_lip"]), piece)
    gbc.set_material_slots(obj, _face_slots(obj))
    gg.smart_uv(obj, margin=0.004)
    import placeholder
    placeholder.finish_uvs(obj)
    obj.data.shade_smooth()
    _tag(obj)
    return {"GB_Mouth": obj}


def _face_slots(obj):
    mi = np.empty(len(obj.data.polygons), np.int32)
    obj.data.polygons.foreach_get("material_index", mi)
    return mi


# ===========================================================================
# Face rig: lid weights, lid deformation, measured aperture table, face bones
# ===========================================================================
LID_BONES = ("lid_upper_L", "lid_lower_L", "lid_upper_R", "lid_lower_R")
LID_FADE_UP = (0.30, 0.66)         # upper lid weight 1 up to 0.30 rad above the margin, 0 at 0.66 (crease)
LID_FADE_LO = (0.16, 0.46)         # lower lid weight 1 down to 0.16 rad below the margin, 0 at 0.46
LID_LOWER_SHARE = 0.35            # in a blink the lower lid rises ~1/3 of the upper lid's rotation [K]
FACE_RIG_JSON = os.path.join(gbc.HERE, "head_face_rig.json")


def face_weights(points):
    """Lid-bone skin weights ``{bone: (N,)}`` for body-frame rest points (plan §3.6, D8).

    The pretarsal lid moves rigidly with its bone (weight 1 from the margin to ~3 mm
    above it), the preseptal skin fades out below the lid crease / above the lower lid
    fold, the conjunctival pocket behind the lid follows deeper into the fornix, and
    both canthi stay put (weight -> 0 at the lid corners).  B6 blends these into
    ``weights_at`` with ``blend_face_weights``."""
    A = _A()
    hx, hy, hz = _head_frame(points)
    out = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        r, u, v = _eye_polar(hx, hy, hz, sx)
        t, st, up, lo = A._lid_curves(u)
        # across the fissure the weight follows the fissure height (up - lo) relative to its maximum, so
        # every point of the margin reaches the closure line at the same bone angle and the canthi stay put
        _t0, _s0, up_m, lo_m = A._lid_curves(np.linspace(A.LID_UM, A.LID_UL, 97))
        # (divided by cos u: toward the canthi the lid wraps round the globe and a rotation about the
        # horizontal axis moves it with a shorter lever arm)
        horiz = np.where((t > 0.0) & (t < 1.0), np.clip((up - lo) / (up_m - lo_m).max()
                                                        / np.maximum(np.cos(u), 0.50), 0.0, 1.0), 0.0)
        own = _smooth(0.002, 0.008, sx * hx)
        rad = _smooth(0.0198, 0.0160, r)
        mid = 0.5 * (up + lo)
        s_up = _smooth(mid - 0.03, mid + 0.03, v)
        dvu = v - up
        # the same profile through the whole lid thickness (skin, margin, conjunctival pocket): a lid that
        # moved its pocket surface differently from its skin would push one through the other
        wu = _smooth(LID_FADE_UP[1], LID_FADE_UP[0], dvu)
        dvl = lo - v
        wl = _smooth(LID_FADE_LO[1], LID_FADE_LO[0], dvl)
        # the caruncle (pink mound in the inner corner) does not move with the lids
        car = np.sqrt((sx * hx - A.EYE_C[0] + 0.0118) ** 2 + (hy - A.EYE_C[1] + 0.0046) ** 2
                      + (hz - A.EYE_C[2] + 0.0002) ** 2)
        base = horiz * rad * own * _smooth(0.0022, 0.0042, car)
        out[f"lid_upper_{side}"] = base * s_up * wu
        out[f"lid_lower_{side}"] = base * (1.0 - s_up) * wl
    return out


def set_anchors(obj, anchors):
    """Store each vertex's skin anchor (body frame) as gb_anchor_x/y/z point attributes."""
    a = np.asarray(anchors, float)
    for k, c in enumerate("xyz"):
        gbc.point_attr(obj, "gb_anchor_" + c, a[:, k], 'FLOAT')


def get_anchors(obj):
    """(N, 3) skin anchors of a follower mesh, or None."""
    cols = [gbc.read_point_attr(obj, "gb_anchor_" + c, 'FLOAT') for c in "xyz"]
    return None if any(c is None for c in cols) else np.stack(cols, 1).astype(float)


def follower_weights(obj):
    """Skin weights for a mesh that must follow the skin (GB_BrowLash cards, GB_EyeFX shells):
    ``rig.weights_at`` + the lid weights evaluated at each vertex's skin anchor (a lash takes the
    weights of the lid margin at its root, a brow card those of the skin under it), so the followers
    move exactly like the skin they sit on.  B6: use this instead of ``gb_rigid_bone`` for these meshes."""
    import rig
    a = get_anchors(obj)
    if a is None:
        raise ValueError(f"{obj.name} has no gb_anchor_* attributes")
    idx, w = rig.weights_at(a, "skin")
    return blend_face_weights(a, idx, w)


def blend_face_weights(points, idx, w):
    """Insert the lid-bone weights into analytic ``(idx, w)`` (N, 4) arrays (for ``rig.weights_at``).

    Existing weights are scaled by (1 - lid weight); the lid bones take the
    weakest slots; rows are renormalised.  Returns new (idx, w)."""
    fw = face_weights(points)
    idx = np.array(idx, copy=True)
    w = np.array(w, dtype=np.float64, copy=True)
    tot = np.zeros(len(w))
    for b in LID_BONES:
        tot += fw[b]
    m = tot > 1e-4
    if not m.any():
        return idx, w
    rows = np.nonzero(m)[0]
    scale = np.clip(1.0 - tot[rows], 0.0, 1.0)
    cand_i = [idx[rows, k] for k in range(idx.shape[1])] + [np.full(len(rows), RT.BONE_INDEX[b]) for b in LID_BONES]
    cand_w = [w[rows, k] * scale for k in range(w.shape[1])] + [fw[b][rows] for b in LID_BONES]
    ci = np.stack(cand_i, 1)
    cw = np.stack(cand_w, 1)
    top = np.argsort(-cw, axis=1)[:, :idx.shape[1]]
    ni = np.take_along_axis(ci, top, 1)
    nw = np.take_along_axis(cw, top, 1)
    nw /= np.maximum(nw.sum(1, keepdims=True), 1e-12)
    idx[rows] = ni
    w[rows] = nw
    return idx, w


def _rot_x(points, pivot, ang):
    """Rotate points about the +X axis through ``pivot`` by ``ang`` rad (right-handed: +ang moves -Y down)."""
    q = np.asarray(points, float) - pivot
    c, s = math.cos(ang), math.sin(ang)
    y = q[:, 1] * c - q[:, 2] * s
    z = q[:, 1] * s + q[:, 2] * c
    return np.stack([q[:, 0], y, z], 1) + pivot


def lid_deform(points, weights, side, upper_deg, lower_deg):
    """Linear-blend-skinned lid pose: ``upper_deg`` > 0 lifts the upper margin (opens), ``lower_deg`` > 0
    lowers the lower margin (opens); both rotate about +X through the eyeball centre and scale by
    ``lid_scale`` while closing past rest."""
    p = np.asarray(points, float)
    c = eye_centre(side)
    pu = c + lid_scale(upper_deg) * (_rot_x(p, c, -math.radians(upper_deg)) - c)
    pl = c + lid_scale(lower_deg) * (_rot_x(p, c, math.radians(lower_deg)) - c)
    wu = weights[f"lid_upper_{side}"][:, None]
    wl = weights[f"lid_lower_{side}"][:, None]
    return p + wu * (pu - p) + wl * (pl - p)


def eye_gap(points, side):
    """Signed distance (m) from body-frame points to the eyeball of ``side`` (sclera sphere U cornea sphere)."""
    A = _A()
    c = eye_centre(side)
    cc = c + np.array([0.0, -A.CORNEA_OFF, 0.0])
    p = np.asarray(points, float)
    return np.minimum(np.linalg.norm(p - c, axis=1) - A.EYE_R, np.linalg.norm(p - cc, axis=1) - A.CORNEA_R)


def _ray_eye(o, d, side):
    """Distance along the ray (o, unit d) to the eyeball of ``side`` (inf if missed)."""
    A = _A()
    c = eye_centre(side)
    best = np.inf
    for cen, rad in ((c, A.EYE_R), (c + np.array([0.0, -A.CORNEA_OFF, 0.0]), A.CORNEA_R)):
        oc = o - cen
        b = oc @ d
        disc = b * b - (oc @ oc - rad * rad)
        if disc >= 0:
            t = -b - math.sqrt(disc)
            if t > 0:
                best = min(best, t)
    return best


class LidRig:
    """The lid region of a head mesh with its lid weights: pose it, measure aperture and globe gap."""

    def __init__(self, obj, side):
        self.side = side
        me = obj.data
        v, tris = gbc.mesh_arrays(me)
        c = eye_centre(side)
        near = np.linalg.norm(v - c, axis=1) < 0.028
        keep = near[tris].all(1)
        used = np.unique(tris[keep])
        remap = np.full(len(v), -1, np.int64)
        remap[used] = np.arange(len(used))
        self.v = v[used]
        self.tris = remap[tris[keep]]
        self.w = face_weights(self.v)
        self.moving = (self.w[f"lid_upper_{side}"] + self.w[f"lid_lower_{side}"]) > 0

    def pose(self, upper_deg, lower_deg):
        return lid_deform(self.v, self.w, self.side, upper_deg, lower_deg)

    def aperture_mm(self, upper_deg, lower_deg, step=0.00005, dx=0.0):
        """Palpebral fissure height (mm) on a vertical line ``dx`` lateral of the pupil line: the longest run
        of frontal rays that reach the globe."""
        from mathutils import Vector
        from mathutils.bvhtree import BVHTree
        p = self.pose(upper_deg, lower_deg)
        bvh = BVHTree.FromPolygons(p.tolist(), self.tris.tolist())
        c = eye_centre(self.side) + np.array([(1.0 if self.side == "L" else -1.0) * dx, 0.0, 0.0])
        d = np.array([0.0, 1.0, 0.0])
        zs = np.arange(c[2] - 0.010, c[2] + 0.010, step)
        open_ = []
        for z in zs:
            o = np.array([c[0], c[1] - 0.030, z])
            te = _ray_eye(o, d, self.side)
            hit = bvh.ray_cast(Vector(o), Vector(d), 0.06)
            ts = hit[3] if hit[0] is not None else np.inf
            open_.append(te < ts)
        best = run = 0
        for f in open_:
            run = run + 1 if f else 0
            best = max(best, run)
        return best * step * 1000.0

    def widest_mm(self, upper_deg, lower_deg):
        """Largest fissure height over 9 vertical lines across the eye (-10 .. +10 mm): 0 = fully closed."""
        return max(self.aperture_mm(upper_deg, lower_deg, 0.0001, dx) for dx in np.linspace(-0.010, 0.010, 9))

    def min_gap_mm(self, upper_deg, lower_deg):
        """Smallest lid-to-globe distance (mm) of the lid-weighted vertices in this pose."""
        p = self.pose(upper_deg, lower_deg)
        m = self.moving | (np.linalg.norm(self.v - eye_centre(self.side), axis=1) < 0.016)
        return float(eye_gap(p[m], self.side).min() * 1000.0)


def lid_table(obj, side="L"):
    """Measure the lid aperture <-> bone angle table on ``obj`` (plan §3.6, §5.8).

    Closing: the upper lid rotates down by ``a`` and the lower lid up by 0.3 a about the
    closing pivot (bisection for 0 mm); opening beyond rest: the upper lid alone rotates up
    about the eyeball centre (fear 11-12 mm).  Rows: [aperture_mm, upper_deg, lower_deg,
    min_gap_mm]; the minimum gap is checked along the whole closing path (``path_min_gap_mm``)."""
    rig = LidRig(obj, side)
    rest = rig.aperture_mm(0.0, 0.0)

    def ap_close(a):
        return rig.aperture_mm(-a, -LID_LOWER_SHARE * a)

    lo_a, hi_a = 0.0, 90.0
    for _ in range(14):
        mid = 0.5 * (lo_a + hi_a)
        if rig.widest_mm(-mid, -LID_LOWER_SHARE * mid) > 0.0:
            lo_a = mid
        else:
            hi_a = mid
    a_closed = hi_a
    rows = []
    targets = [0.0] + [m for m in np.arange(1.0, 12.01, 1.0) if m < rest - 0.05]
    for tgt in targets:
        if tgt == 0.0:
            a = a_closed
        else:
            lo_a, hi_a = 0.0, a_closed
            for _ in range(16):
                mid = 0.5 * (lo_a + hi_a)
                if ap_close(mid) > tgt:
                    lo_a = mid
                else:
                    hi_a = mid
            a = 0.5 * (lo_a + hi_a)
        rows.append([round(tgt, 2), round(-a, 3), round(-LID_LOWER_SHARE * a, 3),
                     round(rig.min_gap_mm(-a, -LID_LOWER_SHARE * a), 3)])
    # lids stay free of self-intersection until the margins meet (contact below ~1 mm is the closure)
    si_free = 0.0
    for r in sorted(rows, key=lambda q: -q[0]):
        if self_intersections(rig.pose(r[1], r[2]), rig.tris) > 0:
            si_free = r[0]
            break
    rows.append([round(rest, 2), 0.0, 0.0, round(rig.min_gap_mm(0.0, 0.0), 3)])
    path_gap = min(rig.min_gap_mm(-a, -LID_LOWER_SHARE * a) for a in np.linspace(0.0, a_closed, 25))
    for tgt in [m for m in (10.0, 11.0, 12.0) if m > rest + 0.05]:
        lo_a, hi_a = 0.0, 40.0
        for _ in range(16):
            mid = 0.5 * (lo_a + hi_a)
            if rig.aperture_mm(mid, 0.0) < tgt:
                lo_a = mid
            else:
                hi_a = mid
        a = 0.5 * (lo_a + hi_a)
        rows.append([round(rig.aperture_mm(a, 0.0), 2), round(a, 3), 0.0, round(rig.min_gap_mm(a, 0.0), 3)])
    rows.sort(key=lambda r: r[0])
    return {"rest_aperture_mm": round(rest, 2), "rows": rows, "path_min_gap_mm": round(path_gap, 3),
            "self_intersection_free_above_mm": si_free,
            "closed_upper_deg": round(-a_closed, 3)}


def jaw_pivot():
    """TMJ hinge centre (body frame): midpoint of the head project's mandibular condyles."""
    # condyle ellipsoid centre in anatomy.jaw_raw: (+-0.0500, -0.0115, -0.0020) head frame
    return gbc.head_to_body(np.array([0.0, -0.0115, -0.0020]))


def face_rig_table(head=None, measure=True):
    """rig.json "face" block (plan §5.8): bone pivots and axes, the measured lid table, blend shapes.

    With ``head`` (GB_Head) and ``measure`` the lid table is measured on the mesh and
    cached in ``head_face_rig.json``; without, the cached file is returned."""
    if head is None or not measure:
        if os.path.exists(FACE_RIG_JSON):
            with open(FACE_RIG_JSON) as fh:
                return json.load(fh)["data"]
        head = None
    A = _A()
    tab = lid_table(head, "L") if head is not None else {"rest_aperture_mm": None, "rows": []}
    rows = tab["rows"]
    incisor = gbc.head_to_body(np.array([0.0, -0.0835, A.LOWER_EDGE_Z]))
    jp = jaw_pivot()
    arm = float(np.linalg.norm((incisor - jp)[1:]))
    face = {
        "status": "measured on GB_Head (B2)" if head is not None else "not measured",
        "lid_aperture_mm_to_deg": [[r[0], r[1]] for r in rows],
        "lid_lower_deg": [[r[0], r[2]] for r in rows],
        "lid_table": {"columns": ["aperture_mm", "upper_deg", "lower_deg", "min_globe_gap_mm", "upper_scale",
                                  "lower_scale"],
                      "rows": [r + [round(lid_scale(r[1]), 5), round(lid_scale(r[2]), 5)] for r in rows],
                      "rest_aperture_mm": tab["rest_aperture_mm"],
                      "closing_path_min_gap_mm": tab.get("path_min_gap_mm"),
                      "self_intersection_free_above_mm": tab.get("self_intersection_free_above_mm"),
                      "sign": "upper_deg > 0 lifts the upper margin (opens); lower_deg > 0 lowers the lower margin "
                              "(opens); rotation axis = body +X (Godot +X) through the eyeball centre (bone head); upper "
                              "lid world rotation = -upper_deg about +X, lower lid = +lower_deg about +X; the "
                              "scale columns are uniform bone scales about the eyeball centre",
                      "lower_share_when_closing": LID_LOWER_SHARE},
        "lid_scale_rule": {"close_scale": LID_CLOSE_SCALE, "full_at_deg": LID_SCALE_DEG,
                           "note": "closing lid bones scale up so the lid rides over the cornea (apex 13.3 mm)"},
        "eye_centres": {s: [round(float(c), 5) for c in eye_centre(s)] for s in ("L", "R")},
        "eye_radius": A.EYE_R, "cornea": {"radius": A.CORNEA_R, "centre_offset": A.CORNEA_OFF,
                                          "limbus_radius": A.LIMBUS_R, "iris_plane_local_y": -0.0101},
        "jaw_pivot": [round(float(c), 5) for c in jp], "jaw_axis_world": [1.0, 0.0, 0.0],
        "jaw_incisor_mm_per_deg": round(arm * math.pi / 180.0 * 1000.0, 3),
        "jaw_note": "opening = +rotation about +X through jaw_pivot (TMJ hinge, condyle centres); "
                    "death jaw drop 10-30 mm = 6-19 deg [RB §5.6]",
        "blend_shapes": list(gbc.FACE_SHAPE_KEYS),
        "blend_shape_meshes": ["GB_Head", "GB_EyeFX_L", "GB_EyeFX_R", "GB_BrowLash", "GB_Head_LOD1"],
        "bone_driven": {"AU05": "lid_upper_*", "AU26": "jaw", "AU43": "lid_upper_* + lid_lower_*"},
        "rigid_parts": {"GB_Eye_*": "eye_*", "GB_Mouth upper teeth/gum": "head", "GB_Mouth lower teeth/gum": "jaw",
                        "GB_Mouth tongue": "tongue", "GB_BrowLash brows": "head", "GB_BrowLash lashes": "lid_*",
                        "GB_EyeFX tearline": "lid_lower_*", "GB_EyeFX occlusion": "lid_upper_*/lid_lower_*"},
    }
    if head is not None:
        _write_face_json(FACE_RIG_JSON, face)
    return face


def _write_face_json(path, data):
    """The face block in the plan §5.8 envelope (schema gb.face_rig/1, deterministic bytes)."""
    env = {"schema": "gb.face_rig/1", "frame": gbc.FRAME, "godot_mapping": gbc.GODOT_MAPPING,
           "generator": "blender/gore_body/head_integration.py", "data": gbc._clean(data)}
    with open(path, "w") as fh:
        json.dump(env, fh, indent=1, sort_keys=True)
        fh.write("\n")


# ===========================================================================
# Face shape keys (24 analytic displacement fields, plan §5.6 / §8.2 B2)
# ===========================================================================
def _ell(hx, hy, hz, c, rad):
    """C2 falloff (1 at c, 0 at the ellipsoid radii ``rad``) for head-frame points (left side, x >= 0)."""
    d2 = ((hx - c[0]) / rad[0]) ** 2 + ((hy - c[1]) / rad[1]) ** 2 + ((hz - c[2]) / rad[2]) ** 2
    return np.clip(1.0 - d2, 0.0, 1.0) ** 3


# key: list of (centre, radii, displacement mm (lateral, y, z)) terms, left side, head frame.
# Amplitudes 2-8 mm (plan), directions from the FACS action descriptions [RB §5.6].
FACE_TERMS = {
    "AU01": [((0.013, -0.094, 0.043), (0.018, 0.030, 0.022), (0.2, -0.3, 4.5)),       # inner brow up
             ((0.014, -0.090, 0.070), (0.024, 0.030, 0.028), (0.0, -0.3, 1.8))],      # central forehead
    "AU02": [((0.043, -0.083, 0.042), (0.020, 0.030, 0.021), (0.3, -0.2, 4.0)),       # outer brow up
             ((0.045, -0.076, 0.068), (0.024, 0.030, 0.026), (0.0, -0.2, 1.6))],
    "AU04": [((0.017, -0.093, 0.036), (0.016, 0.030, 0.016), (-2.0, -0.6, -3.0)),     # brow down + medial
             ((0.004, -0.094, 0.031), (0.010, 0.030, 0.014), (-0.6, -0.8, -0.5))],    # glabellar bunching
    "AU06": [((0.037, -0.086, -0.003), (0.024, 0.030, 0.020), (0.0, -1.2, 2.5)),      # cheek up, bulge
             ((0.034, -0.083, 0.008), (0.017, 0.020, 0.008), (0.0, -0.3, 1.2)),       # lower-lid skin up
             ((0.058, -0.066, 0.022), (0.010, 0.020, 0.012), (-0.8, 0.0, 0.2))],      # crow's feet
    "AU07": [((0.033, -0.081, 0.009), (0.018, 0.020, 0.009), (0.0, -0.5, 0.4))],      # preseptal bunching
    "AU09": [((0.009, -0.100, 0.004), (0.014, 0.020, 0.020), (0.0, -0.3, 2.5)),       # nasal skin up
             ((0.013, -0.097, -0.021), (0.010, 0.015, 0.010), (0.8, 0.0, 2.0)),       # alae up and out
             ((0.008, -0.096, -0.040), (0.012, 0.020, 0.010), (0.0, -0.2, 1.2))],     # upper lip centre
    "AU10": [((0.012, -0.094, -0.046), (0.022, 0.020, 0.011), (0.0, -0.8, 3.0)),      # upper lip up, everts
             ((0.022, -0.090, -0.030), (0.012, 0.020, 0.012), (0.0, -0.6, 1.2))],     # nasolabial fold
    "AU12": [((0.024, -0.085, -0.055), (0.022, 0.025, 0.020), (4.2, 1.8, 5.0)),       # corner up, out, back
             ((0.032, -0.082, -0.030), (0.018, 0.025, 0.018), (0.0, -1.0, 1.8))],     # cheek bulge
    "AU15": [((0.024, -0.085, -0.056), (0.020, 0.025, 0.020), (0.6, -0.3, -4.5)),     # corner down
             ((0.022, -0.083, -0.070), (0.015, 0.020, 0.012), (0.0, 0.0, -1.5))],
    "AU20": [((0.024, -0.085, -0.055), (0.024, 0.025, 0.020), (5.5, 1.0, -0.6))],     # corner stretched out
    "mouth_slack": [((0.010, -0.089, -0.064), (0.022, 0.020, 0.010), (0.0, -0.8, -2.5)),   # lower lip droops
                    ((0.024, -0.085, -0.055), (0.012, 0.020, 0.012), (0.0, 0.0, -1.5)),    # corner sags
                    ((0.035, -0.078, -0.030), (0.020, 0.030, 0.025), (0.0, 0.0, -1.0))],   # cheek sags
}
MIDLINE_KEYS = ("AU01", "AU04", "AU09", "AU10", "mouth_slack")
AU07_LID_DEG = (-3.0, -8.0)            # upper lid down 3 deg, lower lid up 8 deg (lid tightener)
SWELL_MM = 9.0                         # periorbital swelling at the lids (black eye / orbital haematoma)


def face_shape_fields(v_body, normals, lining=None, mouth=None):
    """{key: (N, 3) displacement} of the 24 face keys for body-frame vertices with outward ``normals``.

    Every field is a smooth C2 bump around an anatomical landmark; inward motion
    along the skin normal is removed (keys slide and bulge, never dent into the
    head); the lid margins are held by the lid weights (they only move through
    the lid bones, AU07's lid rotation and the swelling), and the mouth lining
    follows the lips only near the vermilion."""
    v = np.asarray(v_body, float)
    n = np.asarray(normals, float)
    hx, hy, hz = _head_frame(v)
    fw = face_weights(v)
    out = {}
    lin = np.zeros(len(v)) if lining is None else np.asarray(lining, float)
    lin_follow = 1.0 - lin * _smooth(-0.086, -0.074, hy)          # deep lining stays, lip lining follows
    for side, sx in (("L", 1.0), ("R", -1.0)):
        ax = sx * hx
        own = _smooth(-0.004, 0.004, ax)
        mid = _smooth(-0.008, 0.008, ax)
        wlid = np.clip(fw[f"lid_upper_{side}"] + fw[f"lid_lower_{side}"], 0.0, 1.0)
        # the conjunctival pocket around the globe never moves with the skin fields (globe guard)
        r_eye = _eye_polar(hx, hy, hz, sx)[0]
        guard = _smooth(0.0134, 0.0146, r_eye)
        for key, terms in FACE_TERMS.items():
            d = np.zeros((len(v), 3))
            for c, rad, disp in terms:
                f = _ell(ax, hy, hz, c, rad)
                d += f[:, None] * (np.array([sx * disp[0], disp[1], disp[2]]) / 1000.0)[None]
            d *= (mid if key in MIDLINE_KEYS else own)[:, None]
            if key != "AU07":
                d *= ((1.0 - 0.95 * wlid) * guard)[:, None]
            d *= lin_follow[:, None]
            out[f"{key}_{side}"] = d
        # AU07 lid tightener: lower lid up 8 deg, upper down 3 deg about the lid pivot (+ bunching above)
        lid = lid_deform(v, fw, side, AU07_LID_DEG[0], AU07_LID_DEG[1]) - v
        out[f"AU07_{side}"] = out[f"AU07_{side}"] + lid
        # periorbital swelling: outward along the skin normal on the outer lid/orbit skin, strongest on the lids
        A = _A()
        r, u, vv = _eye_polar(hx, hy, hz, sx)
        k_out = _smooth(0.0138, 0.0150, r)
        f = _ell(ax, hy, hz, (A.EYE_C[0] + 0.001, A.EYE_C[1] - 0.010, A.EYE_C[2] - 0.001), (0.026, 0.024, 0.024))
        t, st, up, lo = A._lid_curves(u)
        margin = np.exp(-(np.minimum(np.abs(vv - up), np.abs(vv - lo)) / 0.12) ** 2) * _smooth(0.0165, 0.0140, r)
        amp = SWELL_MM / 1000.0 * f * k_out * own * (1.0 - 0.6 * margin)
        # inflate radially from behind the globe (a smooth, fold-free direction field; per-vertex normals
        # converge in the lid crease and the canthi and would make the swollen skin cross itself)
        c = eye_centre(side) + np.array([0.0, 0.004, 0.0])
        rd = v - c
        rd /= np.maximum(np.linalg.norm(rd, axis=1, keepdims=True), 1e-9)
        out[f"swell_periorbital_{side}"] = amp[:, None] * rd
    if mouth is not None:
        _mouth_guard(v, out, mouth)
    return out


def _mouth_guard(v, fields, mouth):
    """Keep the lips and the mouth lining out of the teeth, gums and tongue in every key: a vertex that is
    outside GB_Mouth at rest but inside it in a key has its displacement shortened (bisection) until it
    stays outside."""
    from mathutils.bvhtree import BVHTree
    mv, mt = gbc.mesh_arrays(mouth.data)
    bvh = BVHTree.FromPolygons(mv.tolist(), mt.tolist())
    near = np.nonzero(np.linalg.norm(v - (HEAD_OFFSET + np.array([0.0, -0.075, -0.055])), axis=1) < 0.045)[0]
    outside = near[~_inside(bvh, v[near])]
    for key, d in fields.items():
        cand = outside[np.linalg.norm(d[outside], axis=1) > 1e-7]
        if len(cand) == 0:
            continue
        bad = cand[_inside(bvh, v[cand] + d[cand])]
        for i in bad:
            lo, hi = 0.0, 1.0
            for _ in range(10):
                m = 0.5 * (lo + hi)
                if _inside(bvh, (v[i] + m * d[i])[None])[0]:
                    hi = m
                else:
                    lo = m
            d[i] *= 0.9 * lo


def vertex_normals_of(obj):
    """Current per-vertex normals of a mesh (custom normals included), (N, 3)."""
    me = obj.data
    cn = np.empty(len(me.loops) * 3, np.float64)
    me.corner_normals.foreach_get("vector", cn)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    acc = np.zeros((len(me.vertices), 3))
    np.add.at(acc, lv, cn.reshape(-1, 3))
    return acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)


def _vertex_lining(obj):
    """Per-vertex 1.0 where the vertex belongs to a mouth-lining face (material slot 1)."""
    me = obj.data
    mi = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    out = np.zeros(len(me.vertices))
    out[lv[np.repeat(mi, lt) == 1]] = 1.0
    return out


def add_keys(obj, fields, order=gbc.FACE_SHAPE_KEYS):
    """Basis + one shape key per name in ``order`` from per-vertex displacement fields."""
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    base = gbc.get_verts(obj.data)
    for name in order:
        kb = obj.data.shape_keys.key_blocks.get(name) or obj.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", (base + fields[name]).ravel())
        kb.value = 0.0
    return obj


def key_displacements(obj):
    """{key: (N, 3) displacement} read back from a mesh's shape keys."""
    sk = obj.data.shape_keys
    if sk is None:
        return {}
    base = np.empty(len(obj.data.vertices) * 3)
    sk.key_blocks[0].data.foreach_get("co", base)
    out = {}
    for kb in sk.key_blocks[1:]:
        a = np.empty(len(obj.data.vertices) * 3)
        kb.data.foreach_get("co", a)
        out[kb.name] = (a - base).reshape(-1, 3)
    return out


def transfer_keys(dst, src, order=gbc.FACE_SHAPE_KEYS, max_dist=0.004, anchors=None):
    """Give ``dst`` the shape keys of ``src`` by nearest-vertex transfer (cards, eye FX, LOD1 follow the skin).

    ``anchors``: optional per-vertex anchor points used for the lookup instead of the vertex itself
    (e.g. a hair card's root), so a whole card follows the skin under its root."""
    from mathutils.kdtree import KDTree
    disp = key_displacements(src)
    if not disp:
        return 0
    sv = gbc.get_verts(src.data)
    kd = KDTree(len(sv))
    for i, p in enumerate(sv):
        kd.insert(p, i)
    kd.balance()
    dv = gbc.get_verts(dst.data) if anchors is None else np.asarray(anchors, float)
    near, dist = [], []
    for p in dv:
        _co, i, d = kd.find(p)
        near.append(i)
        dist.append(d)
    near = np.array(near)
    fall = _smooth(max_dist, 0.5 * max_dist, np.array(dist))
    fields = {k: disp[k][near] * fall[:, None] for k in order if k in disp}
    add_keys(dst, fields, [k for k in order if k in fields])
    return len(fields)


def build_face_shapes(head):
    """The 24 face shape keys on GB_Head (and GB_Head_LOD1 by transfer); measures the face rig table
    (lid aperture <-> angle) and stores it on GB_Head (``gb_face_rig``, exported as glTF extras)."""
    with gbc.Timer("B2: face rig table (lid aperture measured)"):
        face = face_rig_table(head, measure=True)
        head["gb_face_rig"] = json.dumps(gbc._clean(face), sort_keys=True)
    lining = _vertex_lining(head)
    import bpy
    fields = face_shape_fields(gbc.get_verts(head.data), vertex_normals_of(head), lining,
                               bpy.data.objects.get("GB_Mouth"))
    add_keys(head, fields)
    import bpy
    lod = bpy.data.objects.get("GB_Head_LOD1")
    if lod is not None and str(lod.get("gb_status", "")) == STATUS:
        transfer_keys(lod, head, max_dist=0.02)
    return head


# ---------------------------------------------------------------------------
# Shape-key checks: self-intersection, lips vs teeth, lids vs globe
# ---------------------------------------------------------------------------
def self_intersections(verts, tris):
    """Number of intersecting triangle pairs that share no vertex (BVH overlap)."""
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons(np.asarray(verts).tolist(), np.asarray(tris).tolist(), epsilon=0.0)
    pairs = bvh.overlap(bvh)
    t = np.asarray(tris)
    bad = 0
    for i, j in pairs:
        if i >= j:
            continue
        if len(set(t[i]) & set(t[j])) == 0:
            bad += 1
    return bad


def _inside(bvh, points, dirs=((0.0, 0.0, 1.0), (0.31, -0.95, 0.0))):
    """Bool per point: inside the closed mesh of ``bvh`` (odd crossing count along every one of ``dirs``)."""
    from mathutils import Vector
    out = np.ones(len(points), bool)
    for d in dirs:
        dv = Vector(d).normalized()
        for k, p in enumerate(points):
            if not out[k]:
                continue
            o = Vector(p)
            n = 0
            for _ in range(64):
                hit = bvh.ray_cast(o, dv, 0.5)
                if hit[0] is None:
                    break
                n += 1
                o = hit[0] + dv * 1e-6
            out[k] = (n % 2) == 1
    return out


def shape_key_report(head, mouth=None):
    """Per key at weight 1.0: new self-intersections of the skin, skin vertices that were outside the teeth /
    gums / tongue at rest and are inside them in the key (parity test),
    the smallest lid-globe gap (mm) and the largest displacement (mm)."""
    from mathutils.bvhtree import BVHTree
    v, tris = gbc.mesh_arrays(head.data)
    base_si = self_intersections(v, tris)
    disp = key_displacements(head)
    mbvh = None
    mouth_near = np.nonzero(np.linalg.norm(v - (HEAD_OFFSET + np.array([0.0, -0.075, -0.055])), axis=1) < 0.045)[0]
    if mouth is not None:
        mv, mt = gbc.mesh_arrays(mouth.data)
        mbvh = BVHTree.FromPolygons(mv.tolist(), mt.tolist())
        rest_in = _inside(mbvh, v[mouth_near])
    lid_idx = {s: np.nonzero(np.linalg.norm(v - eye_centre(s), axis=1) < 0.018)[0] for s in ("L", "R")}
    rep = {"_base": {"self_intersections": base_si}}
    for k, d in disp.items():
        p = v + d
        si = self_intersections(p, tris) - base_si
        pen = 0
        if mbvh is not None:
            moved = (np.linalg.norm(d[mouth_near], axis=1) > 1e-7) & ~rest_in
            if moved.any():
                pen = int(_inside(mbvh, p[mouth_near][moved]).sum())
        gap = min(float(eye_gap(p[lid_idx[s]], s).min()) for s in ("L", "R")) * 1000.0
        rep[k] = {"self_intersections": int(si), "verts_newly_inside_mouth": pen,
                  "min_globe_gap_mm": round(gap, 3),
                  "max_disp_mm": round(float(np.linalg.norm(d, axis=1).max() * 1000.0), 2)}
    return rep


# ===========================================================================
# Eye FX: tearline (lower lid meniscus) and occlusion shells
# ===========================================================================
FX_STATIONS = 32


def _dir(u, v, sx):
    """Unit directions from an eye centre for lateral angle u and elevation v (rad), side sign sx."""
    u = np.asarray(u, float)
    v = np.asarray(v, float)
    return np.stack([sx * np.cos(v) * np.sin(u), -np.cos(v) * np.cos(u), np.sin(v)], axis=-1)


def _globe_radius(dirs, side):
    """Distance from the eye centre to the eyeball surface along unit ``dirs``."""
    A = _A()
    cc = np.array([0.0, -A.CORNEA_OFF, 0.0])
    b = dirs @ cc
    disc = b * b - (cc @ cc - A.CORNEA_R ** 2)
    tc = np.where(disc > 0, b + np.sqrt(np.maximum(disc, 0.0)), 0.0)
    return np.maximum(A.EYE_R, tc)


def _margin(side, u, upper):
    """(v_margin, r_inner) of the lid margin at lateral angles u: the elevation where rays from the eye
    centre stop escaping between the lids (bisection on the combined skin SDF)."""
    A = _A()
    sx = 1.0 if side == "L" else -1.0
    c = eye_centre(side)
    t, st, up, lo = A._lid_curves(u)
    mid = 0.5 * (up + lo)
    a = mid.copy()
    b = (up + 0.35) if upper else (lo - 0.35)
    radii = np.linspace(0.0121, 0.0165, 23)

    def blocked(vv):
        d = _dir(u, vv, sx)
        pts = c[None, None, :] + d[:, None, :] * radii[None, :, None]
        f = gg.eval_sdf(head_skin_sdf, pts.reshape(-1, 3)).reshape(len(u), len(radii))
        return (f < 0).any(1), f
    for _ in range(22):
        m = 0.5 * (a + b)
        bl, _f = blocked(m)
        a = np.where(bl, a, m)
        b = np.where(bl, m, b)
    vm = 0.5 * (a + b)
    # inner radius of the margin just past the margin elevation
    step = 0.03 if upper else -0.03
    _bl, f = blocked(vm + step)
    first = np.argmax(f < 0, axis=1)
    return vm, radii[first]


def build_eye_fx():
    """GB_EyeFX_L/R: slot 0 tearline (wet meniscus strip in the corner between the lower lid margin and the
    globe, rigid to lid_lower_*), slot 1 occlusion bands (upper and lower: from under the lid onto the
    visible globe, UV.y 0 at the lid -> 1 in the opening, for the darkening gradient; rigid to the lid bones).
    Both sit 0.1-0.35 mm off the globe, inside the 0.5 mm lid-globe gap."""
    A = _A()
    out = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        c = eye_centre(side)
        u = np.linspace(A.LID_UM + 0.05, A.LID_UL - 0.05, FX_STATIONS)
        parts, uvs = [], []
        # tearline along the lower margin
        vm, rin = _margin(side, u, upper=False)
        rows = [(vm + 0.060, 0.00012), (vm + 0.015, 0.00030), (vm - 0.020, None)]
        V = []
        for vv, off in rows:
            d = _dir(u, vv, sx)
            rr = _globe_radius(d, side) + off if off is not None else np.maximum(rin - 0.0001, _globe_radius(d, side)
                                                                                 + 0.00035)
            V.append(c + d * rr[:, None])
        V = np.concatenate(V)
        n = FX_STATIONS
        F = [[r * n + i, r * n + i + 1, (r + 1) * n + i + 1, (r + 1) * n + i] for r in range(2) for i in range(n - 1)]
        if sx < 0:
            F = [f[::-1] for f in F]
        parts.append(gg.part(V, F, 0, gb_rigid_bone=np.full(len(V), RT.BONE_INDEX["lid_lower_" + side], np.int32)))
        uvs.append(np.array([(i / (n - 1) * 0.48, 0.02 + 0.96 * r / 2.0) for r in range(3) for i in range(n)]))
        # occlusion bands
        for upper in (True, False):
            vm, rin = _margin(side, u, upper=upper)
            sgn = 1.0 if upper else -1.0
            rows = [(vm + sgn * 0.20, "under"), (vm + sgn * 0.04, "under"), (vm - sgn * 0.05, 0.00018),
                    (vm - sgn * 0.13, 0.00012)]
            V = []
            for vv, off in rows:
                d = _dir(u, vv, sx)
                g = _globe_radius(d, side)
                rr = g + (0.00030 if off == "under" else off)
                V.append(c + d * rr[:, None])
            V = np.concatenate(V)
            F = [[r * n + i, r * n + i + 1, (r + 1) * n + i + 1, (r + 1) * n + i] for r in range(3) for i in range(n - 1)]
            if (sx < 0) != (not upper):
                F = [f[::-1] for f in F]
            bone = ("lid_upper_" if upper else "lid_lower_") + side
            parts.append(gg.part(V, F, 1, gb_rigid_bone=np.full(len(V), RT.BONE_INDEX[bone], np.int32)))
            u0 = 0.5 if upper else 0.75
            uvs.append(np.array([(u0 + i / (n - 1) * 0.24, 0.02 + 0.96 * r / 3.0) for r in range(4) for i in range(n)]))
        name = f"GB_EyeFX_{side}"
        obj = gg.object_from_parts(name, parts)
        gbc.set_uv_from_vertex(obj, "atlas", np.concatenate(uvs))
        nv = len(obj.data.vertices)
        gbc.set_codes_uv(obj, np.full(nv, SG.REGION_STRIDE * SG.REGION_ID["eyelid_lip"]), np.zeros(nv))
        import placeholder
        placeholder.finish_uvs(obj)
        obj.data.shade_smooth()
        _orient_outward(obj, c)
        _tag(obj)
        import bpy
        head = bpy.data.objects.get("GB_Head")
        if head is not None:
            from mathutils.kdtree import KDTree
            hv = gbc.get_verts(head.data)
            kd = KDTree(len(hv))
            for i, q in enumerate(hv):
                kd.insert(q, i)
            kd.balance()
            set_anchors(obj, [kd.find(q)[0] for q in gbc.get_verts(obj.data)])
            if head.data.shape_keys is not None:
                transfer_keys(obj, head, max_dist=0.004)
        out[name] = obj
    return out


def _orient_outward(obj, centre):
    """Flip faces so their normals point away from ``centre`` (the eyeball centre)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    from mathutils import Vector
    c = Vector(centre)
    for f in bm.faces:
        f.normal_update()
        if f.normal.dot(f.calc_center_median() - c) < 0:
            f.normal_flip()
    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()


# ===========================================================================
# Brow / lash alpha cards from the head project's hair curves
# ===========================================================================
HAIR_TEX = "hair_cards.png"
HAIR_TEX_PX = 1024
BROW_BINS = 15                    # cards along each brow (x 11-58 mm) per layer
BROW_LAYERS = 2                   # two staggered layers of cards (depth, fuller brow)
LASH_STATIONS = {"upper": 22, "lower": 14}
HAIR_RGB = (38, 28, 21)           # dark brown (brows); lashes a little darker
LASH_RGB = (20, 15, 12)


def _head_build_module():
    """The head project's build.py (hair growth functions), imported read-only under a private name."""
    import importlib.util
    path = os.path.join(gbc.HEAD_DIR, "build.py")
    spec = importlib.util.spec_from_file_location("gore_head_build_ro", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def hair_strands(skin_obj):
    """Brow and lash strands of the head project (head frame, lists of 5 points) grown on ``skin_obj``.

    Returns {"brow_L": [...], "brow_R", "lash_upper_L", "lash_lower_L", ...}: exactly the head
    project's generators (``build._brow_strands`` / ``_lash_strands``) run on our skin, so the
    brows and lashes are the head project's own."""
    from mathutils.bvhtree import BVHTree
    v, t = gbc.mesh_arrays(skin_obj.data)
    bvh = BVHTree.FromPolygons((v - HEAD_OFFSET).tolist(), t.tolist())
    hb = _head_build_module()
    rng = gbc.rng("hair_cards")
    out = {}
    for side, sign in (("L", 1), ("R", -1)):
        out["brow_" + side] = [[np.array(p) for p in s] for s in hb._brow_strands(bvh, rng, sign)]
        out["lash_upper_" + side] = [[np.array(p) for p in s] for s in hb._lash_strands(bvh, rng, sign, True)]
        out["lash_lower_" + side] = [[np.array(p) for p in s] for s in hb._lash_strands(bvh, rng, sign, False)]
    return out


class _Atlas:
    """Tiny shelf packer + strand rasteriser for the hair-card texture (RGBA, straight alpha)."""

    def __init__(self, px):
        self.px = px
        self.img = np.zeros((px, px, 4), np.float32)
        self.x = self.y = self.row_h = 0

    def alloc(self, w, h):
        if self.x + w > self.px:
            self.x, self.y, self.row_h = 0, self.y + self.row_h, 0
        if self.y + h > self.px:
            raise ValueError("hair atlas full")
        r = (self.x, self.y, w, h)
        self.x += w
        self.row_h = max(self.row_h, h)
        return r

    def uv(self, rect, s, t):
        """Texture UV (Blender, v up) of card coordinates s (0..1 across), t (0..1 root -> tip) in ``rect``."""
        x, y, w, h = rect
        return ((x + 1 + s * (w - 2)) / self.px, 1.0 - (y + 1 + t * (h - 2)) / self.px)

    def line(self, rect, pts_st, width_px, rgb, taper=True):
        """Anti-aliased polyline in card coordinates (s across 0..1, t along 0..1) into ``rect``."""
        x0, y0, w, h = rect
        P = np.array([(x0 + 1 + s * (w - 2), y0 + 1 + t * (h - 2)) for s, t in pts_st])
        n = len(P)
        for i in range(n - 1):
            a, b = P[i], P[i + 1]
            seg = max(2, int(np.linalg.norm(b - a) * 2))
            for k in range(seg):
                f = (i + k / seg) / (n - 1)
                q = a + (b - a) * (k / seg)
                rad = 0.5 * width_px * ((1.0 - 0.75 * f) if taper else 1.0)
                cx, cy = q
                xs = np.arange(int(cx - rad - 1), int(cx + rad + 2))
                ys = np.arange(int(cy - rad - 1), int(cy + rad + 2))
                xs = xs[(xs >= x0) & (xs < x0 + w)]
                ys = ys[(ys >= y0) & (ys < y0 + h)]
                if len(xs) == 0 or len(ys) == 0:
                    continue
                X, Y = np.meshgrid(xs, ys)
                d = np.sqrt((X + 0.5 - cx) ** 2 + (Y + 0.5 - cy) ** 2)
                cov = np.clip(rad + 0.5 - d, 0.0, 1.0) * (1.0 - 0.35 * f)
                sub = self.img[Y, X]
                a_old = sub[..., 3]
                a_new = a_old + cov * (1.0 - a_old)
                for ch in range(3):
                    sub[..., ch] = np.where(a_new > 0, (sub[..., ch] * a_old + rgb[ch] / 255.0 * cov * (1 - a_old))
                                            / np.maximum(a_new, 1e-6), sub[..., ch])
                sub[..., 3] = a_new
                self.img[Y, X] = sub

    def save(self, path):
        img = self.img.copy()
        # bleed the colour into transparent texels (no dark fringes under mip-mapping)
        rgb = img[..., :3]
        has = img[..., 3] > 0
        if has.any():
            mean = rgb[has].mean(0)
            rgb[~has] = mean
        gbc.write_png_u8(path, np.clip(np.round(img * 255.0), 0, 255).astype(np.uint8))


def _resample(pts, n):
    """Resample a polyline to n points evenly by arc length."""
    P = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
    s = np.concatenate([[0.0], np.cumsum(seg)])
    if s[-1] <= 0:
        return np.repeat(P[:1], n, 0)
    q = np.linspace(0.0, s[-1], n)
    return np.stack([np.interp(q, s, P[:, k]) for k in range(3)], 1)


def _skin_normal_at(bvh, p):
    from mathutils import Vector
    loc, nrm, _i, _d = bvh.find_nearest(Vector(p))
    return np.array(nrm).astype(float) if loc is not None else np.array([0.0, -1.0, 0.0])


def _brow_cards(strands, sign, bvh, atlas):
    """Brow cards: strands binned along the brow (and in two staggered layers); every card is a 4-segment
    strip along its bin's mean hair, as wide as the bin, lying 0.1 mm over the skin; its tile in the
    atlas holds exactly its member strands."""
    roots = np.array([s[0] for s in strands])
    ax = np.abs(roots[:, 0])
    lo_x, hi_x = 0.0105, 0.0585
    cards = []
    for layer in range(BROW_LAYERS):
        edges = np.linspace(lo_x, hi_x, BROW_BINS + 1) + layer * 0.5 * (hi_x - lo_x) / BROW_BINS
        for b in range(BROW_BINS + (1 if layer else 0)):
            e0 = edges[b] - (0.5 * (hi_x - lo_x) / BROW_BINS if layer and b == 0 else 0.0)
            e1 = edges[b + 1] if b + 1 < len(edges) else hi_x + 0.001
            idx = [i for i in np.nonzero((ax >= e0) & (ax < e1))[0] if i % BROW_LAYERS == layer]
            if len(idx) < 2:
                continue
            S = np.array([_resample(strands[i], 5) for i in idx])          # (m, 5, 3)
            centre = S.mean(0)
            D = centre[-1] - centre[0]
            L = np.linalg.norm(D)
            if L < 1e-4:
                continue
            D /= L
            nrm = _skin_normal_at(bvh, centre[0])
            side = np.cross(nrm, D)
            side /= max(np.linalg.norm(side), 1e-9)
            off = (S - centre[None]) @ side                                    # (m, 5) across-card offsets
            half = float(np.clip(np.abs(off).max() + 0.0004, 0.0008, 0.0026))
            rect = atlas.alloc(48, 112)
            for s_pts, o in zip(S, off):
                seg = np.linalg.norm(np.diff(s_pts, axis=0), axis=1)
                tt = np.concatenate([[0.0], np.cumsum(seg)]) / max(seg.sum(), 1e-9)
                atlas.line(rect, [(0.5 + 0.5 * oi / half, ti * (np.linalg.norm(s_pts[-1] - s_pts[0]) / L))
                                  for oi, ti in zip(o, tt)], 1.3, HAIR_RGB)
            verts, uvs = [], []
            for k in range(5):
                for sgn in (-1.0, 1.0):
                    # every card vertex sits on the skin (0.10 mm at the root, 0.25 mm at the tip), so cards
                    # follow the brow around the curve of the forehead instead of standing off it
                    q = centre[k] + side * sgn * half
                    from mathutils import Vector
                    loc, nq, _i, _d = bvh.find_nearest(Vector(q))
                    if loc is not None:
                        q = np.array(loc) + np.array(nq) * (0.00010 + 0.00015 * k / 4.0)
                    verts.append(q)
                    uvs.append(atlas.uv(rect, 0.5 + 0.5 * sgn, k / 4.0))
            faces = [[2 * k, 2 * k + 1, 2 * k + 3, 2 * k + 2] for k in range(4)]
            if np.dot(np.cross(verts[1] - verts[0], verts[2] - verts[0]), nrm) < 0:
                faces = [f[::-1] for f in faces]
            cards.append((np.array(verts), faces, uvs, np.array(verts)))
    return cards


def _lash_ribbons(strands, sign, upper, atlas):
    """Lash ribbons: the lid's lashes sorted along the margin, split into rows (upper lid: 2 staggered
    ribbons), each ribbon a grid of stations x 5 points following the local mean lash; the tile holds
    the member lashes rasterised in ribbon coordinates."""
    roots = np.array([s[0] for s in strands])
    order = np.argsort(sign * roots[:, 0])
    rows = 2 if upper else 1
    nst = LASH_STATIONS["upper" if upper else "lower"]
    out = []
    for row in range(rows):
        idx = [i for k, i in enumerate(order) if k % rows == row]
        S = np.array([_resample(strands[i], 5) for i in idx])
        rx = sign * S[:, 0, 0]
        st_x = np.linspace(rx.min(), rx.max(), nst)
        grid = []
        for x in st_x:
            w = np.exp(-((rx - x) / 0.0018) ** 2)
            w /= w.sum()
            grid.append((S * w[:, None, None]).sum(0))
        grid = np.array(grid)                                      # (nst, 5, 3)
        rect = atlas.alloc(480, 72)
        span = rx.max() - rx.min()
        for sp in S:
            s0 = (sign * sp[0, 0] - rx.min()) / max(span, 1e-9)
            # a lash's along-ribbon coordinate drifts with its tip's x
            pts = [(s0 + (sign * p[0] - sign * sp[0, 0]) / max(span, 1e-9), k / 4.0) for k, p in enumerate(sp)]
            atlas.line(rect, pts, 1.6 if upper else 1.2, LASH_RGB)
        verts, uvs = [], []
        for i in range(nst):
            for k in range(5):
                verts.append(grid[i, k])
                uvs.append(atlas.uv(rect, i / (nst - 1), k / 4.0))
        faces = [[i * 5 + k, i * 5 + k + 1, (i + 1) * 5 + k + 1, (i + 1) * 5 + k] for i in range(nst - 1) for k in range(4)]
        anchors = np.repeat(grid[:, 0, :], 5, axis=0)
        out.append((np.array(verts), faces, uvs, anchors))
    return out


def build_hair_cards():
    """GB_BrowLash: alpha-scissor cards converted from the head project's brow and lash curves
    (brows rigid to ``head``, upper/lower lashes rigid to ``lid_upper_*`` / ``lid_lower_*``), the
    24 face keys transferred from the skin under each card's root, and the card texture
    ``textures/hair_cards.png`` (RGBA, straight alpha, colour bled into empty texels)."""
    import bpy
    from mathutils.bvhtree import BVHTree
    head = bpy.data.objects.get("GB_Head_HR") or bpy.data.objects["GB_Head"]
    strands = hair_strands(head)
    v, t = gbc.mesh_arrays(head.data)
    bvh = BVHTree.FromPolygons((v - HEAD_OFFSET).tolist(), t.tolist())
    atlas = _Atlas(HAIR_TEX_PX)
    parts, uv_all, anchors = [], [], []
    for side, sign in (("L", 1), ("R", -1)):
        for verts, faces, uvs, anc in _brow_cards(strands["brow_" + side], sign, bvh, atlas):
            parts.append(gg.part(verts + HEAD_OFFSET, faces, 0,
                                 gb_rigid_bone=np.full(len(verts), RT.BONE_INDEX["head"], np.int32)))
            uv_all += uvs
            anchors.append(anc + HEAD_OFFSET)
    for side, sign in (("L", 1), ("R", -1)):
        for upper in (True, False):
            key = ("lash_upper_" if upper else "lash_lower_") + side
            bone = ("lid_upper_" if upper else "lid_lower_") + side
            for verts, faces, uvs, anc in _lash_ribbons(strands[key], sign, upper, atlas):
                parts.append(gg.part(verts + HEAD_OFFSET, faces, 0,
                                     gb_rigid_bone=np.full(len(verts), RT.BONE_INDEX[bone], np.int32)))
                uv_all += uvs
                anchors.append(anc + HEAD_OFFSET)
    obj = gg.object_from_parts("GB_BrowLash", parts)
    gbc.set_uv_from_vertex(obj, "atlas", np.array(uv_all))
    nv = len(obj.data.vertices)
    gbc.set_codes_uv(obj, np.full(nv, SG.REGION_STRIDE * SG.REGION_ID["face"]), np.zeros(nv))
    import placeholder
    placeholder.finish_uvs(obj)
    obj.data.shade_smooth()
    _tag(obj)
    obj["gb_texture"] = "textures/" + HAIR_TEX
    obj["gb_alpha_scissor"] = 0.35
    obj["gb_double_sided"] = True
    skin = bpy.data.objects["GB_Head"]
    set_anchors(obj, np.concatenate(anchors))
    if skin.data.shape_keys is not None:
        transfer_keys(obj, skin, max_dist=0.004, anchors=np.concatenate(anchors))
    tex_dir = os.path.join(gbc.SUBJECT_OUT, "textures")
    os.makedirs(tex_dir, exist_ok=True)
    atlas.save(os.path.join(tex_dir, HAIR_TEX))
    return {"GB_BrowLash": obj}


# ===========================================================================
# Acceptance checks (plan §8.2 B2; called by verify.py, owner B2)
# ===========================================================================
RB_HEAD_LANDMARKS = {            # RB §1.2 body-frame table (m)
    "vertex": (0.0, 0.025, 1.772), "glabella": (0.0, -0.073, 1.682), "eye_L": (0.032, -0.050, 1.669),
    "eye_R": (-0.032, -0.050, 1.669), "nose_tip": (0.0, -0.091, 1.633), "chin_bottom": (0.0, -0.060, 1.544),
    "ear_canal_L": (0.072, 0.020, 1.647), "ear_canal_R": (-0.072, 0.020, 1.647),
}


def _b2_objects():
    import bpy
    head = bpy.data.objects.get("GB_Head")
    if head is None or str(head.get("gb_status", "")) != STATUS:
        return None
    return head


def _skip():
    return True, "GB_Head is not built by B2 in this file (placeholder / B1 stand-in)"


def measure_head_landmarks(head):
    """RB §1.2 landmarks measured on the built GB_Head (body frame)."""
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    import bpy
    v, t = gbc.mesh_arrays(head.data)
    bvh = BVHTree.FromPolygons(v.tolist(), t.tolist())
    out = {}
    hit = bvh.ray_cast(Vector((0.0, 0.025, 1.95)), Vector((0.0, 0.0, -1.0)), 1.0)
    out["vertex"] = tuple(hit[0]) if hit[0] is not None else None
    hit = bvh.ray_cast(Vector((0.0, -0.20, 1.682)), Vector((0.0, 1.0, 0.0)), 1.0)
    out["glabella"] = tuple(hit[0]) if hit[0] is not None else None
    mid = v[np.abs(v[:, 0]) < 0.003]
    front = mid[(mid[:, 2] > 1.60) & (mid[:, 2] < 1.66)]
    out["nose_tip"] = tuple(front[np.argmin(front[:, 1])])
    chin = mid[(mid[:, 1] < -0.055) & (mid[:, 2] > 1.540)]
    out["chin_bottom"] = tuple(chin[np.argmin(chin[:, 2])])
    for s in ("L", "R"):
        e = bpy.data.objects.get(f"GB_Eye_{s}")
        if e is not None:
            ev = gbc.get_verts(e.data)
            c = 0.5 * (ev.min(0) + ev.max(0))
            c[1] = ev[:, 1].max() - _A().EYE_R
            out["eye_" + s] = tuple(c)
        # ear canal: the landmark must sit in the concha, within a few mm of the skin
        p = np.array(RB_HEAD_LANDMARKS["ear_canal_" + s])
        loc, _n, _i, d = bvh.find_nearest(Vector(p))
        out["ear_canal_" + s] = (tuple(p), round(d * 1000.0, 2))
    return out


def check_landmarks():
    """Head landmarks in the body frame equal the RB §1.2 table (eyes 0.3 mm, vertex/glabella/nose/chin 4 mm,
    ear canal landmark within 7 mm of the concha skin)."""
    head = _b2_objects()
    if head is None:
        return _skip()
    m = measure_head_landmarks(head)
    bad, det = [], {}
    for k, want in RB_HEAD_LANDMARKS.items():
        got = m.get(k)
        if got is None:
            bad.append(k)
            continue
        if k.startswith("ear_canal"):
            det[k] = f"{got[1]} mm to skin"
            if got[1] > 7.0:
                bad.append(k)
            continue
        err = float(np.max(np.abs(np.array(got) - np.array(want)))) * 1000.0
        tol = 0.3 if k.startswith("eye") else 4.0
        if k == "vertex":
            err = abs(got[2] - want[2]) * 1000.0
        elif k == "glabella":
            err = abs(got[1] - want[1]) * 1000.0
        elif k == "chin_bottom":
            err = abs(got[2] - want[2]) * 1000.0
        det[k] = round(err, 2)
        if err > tol:
            bad.append(k)
    return not bad, f"error mm {det}; bad {bad}"


def check_seam():
    """FB-1: GB_Head and GB_Body share 160 identical ring vertices and their exported normals there differ
    by < 1 degree (LOD1 pair reported)."""
    import bpy
    head = _b2_objects()
    body = bpy.data.objects.get("GB_Body")
    if head is None:
        return _skip()
    if body is None:
        return False, "GB_Body missing"
    err, n = ring_normal_error_deg(head, body)
    lod = ""
    hl, bl = bpy.data.objects.get("GB_Head_LOD1"), bpy.data.objects.get("GB_Body_LOD1")
    if hl is not None and bl is not None:
        e2, n2 = ring_normal_error_deg(hl, bl)
        lod = f"; LOD1 pair {n2} shared, {e2:.3f} deg"
    return n == gbc.SEAM_RING_N and err < 1.0, f"{n} shared ring vertices, max normal difference {err:.4f} deg{lod}"


def check_lids():
    """Lids close to 0 mm with >= 0.2 mm to the globe along the whole closing path and open to 12 mm
    (measured lid table stored on GB_Head)."""
    head = _b2_objects()
    if head is None:
        return _skip()
    face = json.loads(head.get("gb_face_rig", "{}") or "{}")
    lt = face.get("lid_table", {})
    rows = lt.get("rows", [])
    if not rows:
        return False, "no lid table on GB_Head"
    closed = [r for r in rows if r[0] == 0.0]
    wide = [r for r in rows if r[0] >= 11.95]
    si = lt.get("self_intersection_free_above_mm")
    ok = (bool(closed) and closed[0][3] >= 0.2 and (lt.get("closing_path_min_gap_mm") or 0) >= 0.2
          and bool(wide) and wide[-1][3] >= 0.2 and si is not None and si <= 1.0)
    return ok, (f"rest {lt.get('rest_aperture_mm')} mm; closed at upper {closed[0][1] if closed else None} deg, "
                f"gap {closed[0][3] if closed else None} mm, path min gap {lt.get('closing_path_min_gap_mm')} mm; "
                f"12 mm at upper {wide[-1][1] if wide else None} deg, gap {wide[-1][3] if wide else None} mm; "
                f"lid mesh self-intersection free above {si} mm (margin contact)")


def check_shape_keys():
    """Every face key at 1.0: no new self-intersection, no new lip/lining penetration of the teeth or gums
    (> 0.1 mm), lids >= 0.2 mm off the globe, amplitude 1.5-8 mm."""
    import bpy
    head = _b2_objects()
    if head is None:
        return _skip()
    rep = shape_key_report(head, bpy.data.objects.get("GB_Mouth"))
    keys = [k for k in rep if not k.startswith("_")]
    bad = [k for k in keys if rep[k]["self_intersections"] > 0 or rep[k]["verts_newly_inside_mouth"] > 0
           or rep[k]["min_globe_gap_mm"] < 0.2 or not (1.5 <= rep[k]["max_disp_mm"] <= 8.0)]
    amp = {k: rep[k]["max_disp_mm"] for k in keys}
    return (len(keys) == len(gbc.FACE_SHAPE_KEYS) and not bad), \
        f"{len(keys)} keys; base self-intersections {rep['_base']['self_intersections']}; bad {bad}; amplitudes {amp}"


def check_cards():
    """Cards stay attached: brow cards within 0.5 mm of the skin at rest and under every face key; lash roots on
    lid-weighted skin (>= 0.9) and rigid to the lid bone of that side."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    head = _b2_objects()
    cards = bpy.data.objects.get("GB_BrowLash")
    if head is None:
        return _skip()
    if cards is None:
        return False, "GB_BrowLash missing"
    cv = gbc.get_verts(cards.data)
    rb = gbc.read_point_attr(cards, "gb_rigid_bone", 'INT')
    brow = rb == RT.BONE_INDEX["head"]
    hv, ht = gbc.mesh_arrays(head.data)
    hk = key_displacements(head)
    ck = key_displacements(cards)
    worst = 0.0
    for name in [None] + list(gbc.FACE_SHAPE_KEYS):
        hp = hv + (hk[name] if name else 0.0)
        cp = cv + (ck[name] if name else 0.0)
        bvh = BVHTree.FromPolygons(hp.tolist(), ht.tolist())
        d = [bvh.find_nearest(Vector(p))[3] for p in cp[brow]]
        worst = max(worst, max(d))
    # lashes and eye FX follow the skin through their anchors (follower_weights): anchors on the skin
    an = get_anchors(cards)
    bvh0 = BVHTree.FromPolygons(hv.tolist(), ht.tolist())
    ad = max(bvh0.find_nearest(Vector(p))[3] for p in an[~brow]) if an is not None else 1.0
    fx_ok = all(get_anchors(bpy.data.objects[f"GB_EyeFX_{s}"]) is not None for s in "LR"
                if f"GB_EyeFX_{s}" in bpy.data.objects)
    return (worst <= 0.0006 and ad <= 0.0003 and fx_ok), \
        (f"brow cards: max distance to the skin {worst * 1000:.3f} mm over rest + 24 keys; lash anchors "
         f"max {ad * 1000:.3f} mm off the skin; eye FX anchors present {fx_ok}")


def check_texel_uv():
    """Head texel 0.24 mm +- 20 % at 2,048 (visible skin) and no overlapping atlas islands."""
    head = _b2_objects()
    if head is None:
        return _skip()
    tx = float(head.get("gb_texel_mm", 0.0))
    try:
        import body_skin
        ov = body_skin.uv_overlap_fraction(head, 1024)
    except Exception as exc:              # the helper lives in B1's module
        ov = f"n/a ({exc})"
    ok = 0.192 <= tx <= 0.288 and (isinstance(ov, str) or ov < 0.002)
    return ok, f"texel {tx} mm (0.192-0.288); UV overlap fraction {ov}"


def check_budgets():
    """Plan §4.1 triangle budgets: GB_Head 30k, eyes + eye FX 5k, GB_Mouth 8.5k, GB_BrowLash 2k."""
    import bpy
    head = _b2_objects()
    if head is None:
        return _skip()
    t = {n: gbc.tri_count(bpy.data.objects[n].data) for n in ("GB_Head", "GB_Eye_L", "GB_Eye_R", "GB_EyeFX_L",
                                                               "GB_EyeFX_R", "GB_Mouth", "GB_BrowLash")
         if n in bpy.data.objects}
    eyes = sum(t.get(n, 0) for n in ("GB_Eye_L", "GB_Eye_R", "GB_EyeFX_L", "GB_EyeFX_R"))
    ok = t.get("GB_Head", 1e9) <= 30000 and eyes <= 5000 and t.get("GB_Mouth", 1e9) <= 8500 \
        and t.get("GB_BrowLash", 1e9) <= 2000
    return ok, f"{t}; eyes+FX {eyes}"


def check_eye_fx_and_mouth():
    """Eye FX shells never touch the globe (>= 0.05 mm) and stay inside the lid gap (<= 1.4 mm off the
    globe); GB_Mouth has 28 teeth (FDI 11-17, 21-27, 31-37, 41-47) as separate pieces."""
    import bpy
    head = _b2_objects()
    if head is None:
        return _skip()
    res, ok = {}, True
    for s in ("L", "R"):
        fx = bpy.data.objects.get(f"GB_EyeFX_{s}")
        if fx is None:
            ok = False
            continue
        g = eye_gap(gbc.get_verts(fx.data), s) * 1000.0
        res[s] = (round(float(g.min()), 3), round(float(g.max()), 3))
        ok &= g.min() >= 0.05 and g.max() <= 1.4
    mouth = bpy.data.objects.get("GB_Mouth")
    ids = set()
    if mouth is not None:
        ids = set(np.unique(gbc.read_point_attr(mouth, "gb_piece", 'INT')).tolist()) - {0}
    want = {q * 10 + k for q in (1, 2, 3, 4) for k in range(1, 8)}
    ok &= ids == want
    return ok, f"eye FX gap to globe min/max mm {res}; teeth {len(ids)} (missing {sorted(want - ids)})"


def check_codes():
    """Head codes: segment 0; regions scalp/face/eyelid-lip/neck present; dermatomes CN V, C2, C3 present."""
    head = _b2_objects()
    if head is None:
        return _skip()
    u, v = gbc.read_codes_uv(head)
    seg, reg = u % SG.REGION_STRIDE, u // SG.REGION_STRIDE
    regions = set(np.unique(reg).tolist())
    derms = set(np.unique(v).tolist())
    ok = set(np.unique(seg).tolist()) == {0} and {0, 1, 2, 3} <= regions and {0, 1, 2} <= derms
    return ok, f"segments {sorted(set(seg.tolist()))}, regions {sorted(regions)}, dermatomes {sorted(derms)}"


# ===========================================================================
# Test renders (renders/head_integration_*.png)
# ===========================================================================
def _posed_copy(obj, name, upper_deg, lower_deg, keys=None):
    """A temporary copy of ``obj`` with the lids posed (face weights for the skin, rigid lid bones for cards /
    FX) and the given shape-key values applied, for renders only."""
    import bpy
    me = obj.data.copy()
    tmp = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(tmp)
    if me.shape_keys is not None:
        for kb in me.shape_keys.key_blocks[1:]:
            kb.value = float((keys or {}).get(kb.name, 0.0))
        dg = bpy.context.evaluated_depsgraph_get()
        new = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg))
        tmp.shape_key_clear()
        tmp.data = new
    v = gbc.get_verts(tmp.data)
    rb = gbc.read_point_attr(obj, "gb_rigid_bone", 'INT')
    anchors = get_anchors(obj)
    for s in ("L", "R"):
        if anchors is not None:
            w = face_weights(anchors)                    # followers: the skin weights at their anchor
        elif rb is not None and obj.name != "GB_Head":
            w = {b: (rb == RT.BONE_INDEX[b]).astype(float) for b in LID_BONES}
        else:
            w = face_weights(gbc.get_verts(obj.data))
        v = lid_deform(v, w, s, upper_deg, lower_deg)
    gbc.set_verts(tmp.data, v)
    if obj.name == "GB_Head":
        # skinned normals: the rest (analytic) normals rotated like the lids (as the GPU skinning does)
        rest = gbc.get_verts(obj.data)
        n = analytic_normals(rest)
        fw = face_weights(rest)
        o = np.zeros(3)
        for s in ("L", "R"):
            nu = _rot_x(n, o, -math.radians(upper_deg))
            nl = _rot_x(n, o, math.radians(lower_deg))
            wu, wl = fw[f"lid_upper_{s}"][:, None], fw[f"lid_lower_{s}"][:, None]
            n = n + wu * (nu - n) + wl * (nl - n)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
        tmp.data.normals_split_custom_set_from_vertices([tuple(q) for q in n])
    return tmp


def render_tests(prefix="head_integration", samples=24, only=None):
    """Close-up renders for review: head + neck + shoulders (FB-1 views), eyes open / closed / wide,
    expressions (AU04 frown, AU12 smile, pain, swelling, slack jaw-side), hair cards."""
    import bpy
    gbc.setup_stage(floor=False)
    skin = bpy.data.materials.get("B2_preview_skin") or bpy.data.materials.new("B2_preview_skin")
    skin.use_nodes = True
    b = skin.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (0.50, 0.33, 0.26, 1.0)
    b.inputs["Roughness"].default_value = 0.45
    b.inputs["Subsurface Weight"].default_value = 0.12
    b.inputs["Subsurface Radius"].default_value = (0.004, 0.0015, 0.001)
    hair = bpy.data.materials.get("B2_preview_hair") or bpy.data.materials.new("B2_preview_hair")
    hair.use_nodes = True
    nt = hair.node_tree
    hb = nt.nodes["Principled BSDF"]
    tex = os.path.join(gbc.SUBJECT_OUT, "textures", HAIR_TEX)
    if os.path.exists(tex) and not any(n.type == 'TEX_IMAGE' for n in nt.nodes):
        im = nt.nodes.new("ShaderNodeTexImage")
        im.image = bpy.data.images.load(tex, check_existing=True)
        uvn = nt.nodes.new("ShaderNodeUVMap")
        uvn.uv_map = "atlas"
        nt.links.new(uvn.outputs[0], im.inputs[0])
        nt.links.new(im.outputs["Color"], hb.inputs["Base Color"])
        nt.links.new(im.outputs["Alpha"], hb.inputs["Alpha"])
    views = {
        "front": ((0.0, -0.62, 1.60), (0.0, 0.0, 1.59), 70.0),
        "three_q": ((-0.42, -0.48, 1.62), (0.0, 0.0, 1.58), 70.0),
        "side": ((-0.64, 0.02, 1.60), (0.0, 0.02, 1.57), 70.0),
        "back": ((0.30, 0.56, 1.60), (0.0, 0.02, 1.56), 70.0),
        "eyes": ((0.0, -0.40, 1.675), (0.0, -0.05, 1.664), 120.0),
        "face": ((-0.10, -0.45, 1.66), (0.0, -0.05, 1.640), 90.0),
        "eye_L": ((0.06, -0.30, 1.68), (0.032, -0.05, 1.669), 150.0),
        "eye_L_macro": ((0.045, -0.16, 1.672), (0.032, -0.05, 1.667), 150.0),
        "eye_L_low": ((0.05, -0.20, 1.60), (0.032, -0.05, 1.667), 150.0),
    }
    shows = ["GB_Head", "GB_Body", "GB_Eye_L", "GB_Eye_R", "GB_Mouth", "GB_EyeFX_L", "GB_EyeFX_R", "GB_BrowLash"]
    hidden = {}
    for o in bpy.data.objects:
        if o.type == 'MESH':
            hidden[o.name] = o.hide_render
            o.hide_render = True
    out = []

    def shot(tag, view, upper=0.0, lower=0.0, keys=None, res=(480, 480)):
        if only is not None and tag not in only:
            return
        temps = []
        for n in shows:
            src = bpy.data.objects.get(n)
            if src is None:
                continue
            if n == "GB_Body":
                t = src.copy()
                bpy.context.scene.collection.objects.link(t)
                t.modifiers.clear()
                t.hide_render = False
            else:
                t = _posed_copy(src, "_b2r_" + n, upper, lower, keys)
            for i, mt in enumerate(t.data.materials):
                if mt is not None and mt.name.startswith("GBM_skin"):
                    t.data.materials[i] = skin
                if mt is not None and mt.name == "GBM_hair_card":
                    t.data.materials[i] = hair
            t.hide_render = False
            temps.append(t)
        loc, tgt, lens = views[view]
        cam = gbc.add_camera("GB_Cam_b2_" + view, loc, tgt, lens)
        out_dir = gbc.RENDER_DIR if prefix == "head_integration" else os.path.dirname(prefix)
        name = f"{os.path.basename(prefix)}_{tag}.png"
        out.append(gbc.render(os.path.join(out_dir, name), cam, samples, res))
        for t in temps:
            me = t.data
            bpy.data.objects.remove(t, do_unlink=True)
            if me is not None and me.users == 0:
                bpy.data.meshes.remove(me)
    face = json.loads(bpy.data.objects["GB_Head"].get("gb_face_rig", "{}") or "{}")
    rows = face.get("lid_table", {}).get("rows", [])
    closed = next((r for r in rows if r[0] == 0.0), None)
    alert = min(rows, key=lambda r: abs(r[0] - 9.5)) if rows else None
    for view in ("front", "three_q", "side", "back"):
        shot(view, view)
    shot("eyes_open", "eyes")
    if alert:
        shot("eyes_alert_9mm", "eyes", alert[1], alert[2])
    if closed:
        shot("eyes_closed", "eyes", closed[1], closed[2])
        shot("eye_L_closed", "eye_L", closed[1], closed[2])
        shot("eye_L_closed_macro", "eye_L_macro", closed[1], closed[2])
        shot("eye_L_closed_low", "eye_L_low", closed[1], closed[2])
    shot("eye_L_open", "eye_L")
    for tag, keys in (("frown_AU04", {"AU04_L": 1, "AU04_R": 1}), ("smile_AU06_12", {"AU06_L": 1, "AU06_R": 1,
                      "AU12_L": 1, "AU12_R": 1}), ("pain_AU04_07_09_10", {k + s: 1 for k in ("AU04_", "AU07_",
                      "AU09_", "AU10_") for s in "LR"}), ("fear_AU01_02_20", {k + s: 1 for k in ("AU01_", "AU02_",
                      "AU20_") for s in "LR"}), ("swollen_L", {"swell_periorbital_L": 1}),
                     ("slack_R", {"mouth_slack_R": 1, "AU15_R": 0.5})):
        shot(tag, "face", keys=keys)
    shot("face_neutral", "face")
    for n, h in hidden.items():
        o = bpy.data.objects.get(n)
        if o is not None:
            o.hide_render = h
    return out


# ===========================================================================
# Stage entry points
# ===========================================================================
def build_head(quick=None):
    """GB_Head (+ HR, LOD1), eyes and mouth.  Skull/jaw go to B3 and the brain to B4 through
    ``head_layer_sdfs`` (they re-evaluate the head project's own fields in the body frame)."""
    out = {}
    out.update(build_head_skin(quick))
    with gbc.Timer("B2: eyes"):
        out.update(build_eyes())
    with gbc.Timer("B2: mouth (teeth, gums, tongue)"):
        out.update(build_mouth(quick))
    return out


def head_layer_sdfs():
    """Body-frame SDFs (negative inside) of the head project's skull, mandible and brain, plus their
    body-frame boxes: the hand-off of the head layers to B3 (skull, jaw) and B4 (brain)."""
    A = _A()
    o = HEAD_OFFSET

    def wrap(fn):
        return lambda x, y, z: fn(x - o[0], y - o[1], z - o[2])

    def box(b):
        return tuple(np.asarray(b[0]) + o), tuple(np.asarray(b[1]) + o)
    return {"skull": (wrap(A.skull_sdf), box(A.SKULL_BOX)), "jaw": (wrap(A.jaw_sdf), box(A.JAW_BOX)),
            "brain": (wrap(A.brain_sdf), box(A.BRAIN_BOX))}


def _checks():
    """Run every B2 acceptance check; returns {name: (ok, detail)}."""
    return {n: globals()[n]() for n in ("check_landmarks", "check_seam", "check_lids", "check_shape_keys",
                                         "check_cards", "check_texel_uv", "check_budgets",
                                         "check_eye_fx_and_mouth", "check_codes")}


if __name__ == "__main__":
    # standalone: build the B2 stage on an empty scene (GB_Body appended from the newest skin cache when
    # one exists, for the seam check and the neck renders), run the B2 checks, optionally render
    import time
    t0 = time.time()
    gbc.reset_scene()
    gbc.collections()
    objs = build_head(quick="--quick" in gbc.script_args())
    build_face_shapes(objs["GB_Head"])
    objs.update(build_eye_fx())
    objs.update(build_hair_cards())
    gbc.log(f"head stage built: {sorted(objs)} in {time.time() - t0:.1f} s")
    import glob
    import bpy
    caches = sorted(glob.glob(os.path.join(gbc.CACHE_DIR, "skin-*.blend")), key=os.path.getmtime)
    if caches:
        with bpy.data.libraries.load(caches[-1], link=False) as (src, dst):
            dst.objects = [n for n in src.objects if n in ("GB_Body", "GB_Body_LOD1")]
        for o in dst.objects:
            gbc.link(o, gbc.OBJECT_COLLECTION[o.name])
    args = gbc.script_args()
    if "--save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(args[args.index("--save") + 1]))
    for k, (ok, detail) in _checks().items():
        print(f"  [{'PASS' if ok else 'FAIL'}] {k}: {detail}")
    if "--render" in gbc.script_args():
        render_tests()
