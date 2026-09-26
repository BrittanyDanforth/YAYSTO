"""Texture bakes (owner B7).  Plan §3.3.7, §4.2, §5.2, §8.2 B7.

Entry points (called by ``build.py`` in the ``bake`` stage, after the rig and before the export):

``prepare_uvs(objs)``               re-charts the ``atlas`` UVs of GB_Skeleton, GB_Organs and GB_Brain
                                    (their build-time smart-project atlases used 4-17 % of the texture)
``bake_all(objs, out)``             albedo / normal / ORM+SSS sets per mesh (plan §4.2) with Cycles
``bake_tileables(out)``             seamless tileables, iris, sclera, blood decal atlas, room/prop sets
``bake_painter_inputs(objs, out)``  position (EXR half, segment-relative), rest normal, valid mask and
                                    dominant-bone maps for the head, body and shorts painter atlases
``write_texture_manifest(out)``     ``textures/textures.json`` (schema gb.textures/1): every file with its
                                    channels, colour space, import hint, mesh/surfaces and UV hash

Conventions (all images)
========================
* Rows are written top to bottom with v = 1 at the top (Godot / glTF image origin).
* Albedo PNGs are sRGB; normal maps are tangent space, OpenGL / Godot convention (+Y = +v), baked
  with MikkTSpace on the LOD0 mesh; ORM = R ambient occlusion, G roughness, B metallic,
  A = subsurface (SSS) mask for mesh sets, height (0-1) for tileables.
* Every mesh texture is dilated past its islands (8 px) and the rest of the image is filled by
  push-pull, so mip maps never pull in black.
* The ``uv_hash`` of each mesh set is the hash of the LOD0 ``atlas`` UVs the set was baked for;
  ``verify.py`` compares it with the exported mesh (textures and UVs must match).

Mesh sets (plan §4.2)
=====================
======== ==================== ================= ====== =================================
set      target (UV0 atlas)   bake source       size   look-dev materials
======== ==================== ================= ====== =================================
head     GB_Head              GB_Head_HR        2048   GBL_skin_head, GBL_mouth_lining
body     GB_Body              GB_Body_HR        2048   GBL_skin_body
shorts   GB_Shorts            GB_Shorts         1024   GBL_cloth
mouth    GB_Mouth             GB_Mouth          1024   GBL_teeth, GBL_gums, GBL_tongue
skeleton GB_Skeleton          GB_Skeleton_HR    2048   GBL_bone, GBL_cartilage
organs   GB_Organs            GB_Organs_HR      2048   GBL_organ
brain    GB_Brain             GB_Brain_HR       1024   GBL_brain
======== ==================== ================= ====== =================================
GB_Head_LOD1 / GB_Body_LOD1 share their LOD0's atlas layout and use the same sets.
"""
import hashlib
import json
import os
import sys
import time

import numpy as np

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402

SCHEMA = "gb.textures/1"
gbc.SCHEMAS.setdefault(SCHEMA, ("sets", "tileables", "eyes", "decals", "painter", "room", "material_map"))

DILATE_PX = 8
UV_MARGIN_PX = 8          # island margin of the re-charted atlases (at the set's resolution)

SETS = {
    # name: target, source, size, cage extrusion (m), max ray (m), AO distance (m), surfaces
    "head": dict(target="GB_Head", source="GB_Head_HR", size=2048, cage=0.003, ray=0.008, ao=0.03,
                 surfaces=["GBM_skin_head", "GBM_mouth_lining"], lod1=["GB_Head_LOD1"]),
    "body": dict(target="GB_Body", source="GB_Body_HR", size=2048, cage=0.003, ray=0.008, ao=0.06,
                 surfaces=["GBM_skin_torso", "GBM_skin_arm_L", "GBM_skin_arm_R", "GBM_skin_leg_L",
                           "GBM_skin_leg_R"], lod1=["GB_Body_LOD1"]),
    "shorts": dict(target="GB_Shorts", source=None, size=1024, cage=0.0, ray=0.0, ao=0.05,
                   surfaces=["GBM_cloth"]),
    "mouth": dict(target="GB_Mouth", source=None, size=1024, cage=0.0, ray=0.0, ao=0.008,
                  surfaces=["GBM_teeth", "GBM_gums", "GBM_tongue"]),
    "skeleton": dict(target="GB_Skeleton", source="GB_Skeleton_HR", size=2048, cage=0.003, ray=0.008, ao=0.02,
                     surfaces=["GBM_bone", "GBM_cartilage"]),
    "organs": dict(target="GB_Organs", source="GB_Organs_HR", size=2048, cage=0.003, ray=0.008, ao=0.02,
                   surfaces=["GBM_organ"]),
    "brain": dict(target="GB_Brain", source="GB_Brain_HR", size=1024, cage=0.003, ray=0.008, ao=0.01,
                  surfaces=["GBM_brain"]),
}
RECHART = {"GB_Skeleton": dict(size=2048, smooth=2, interior_scale=0.45, cone=60.0, margin=6),
           "GB_Organs": dict(size=2048, smooth=2, interior_scale=0.6, cone=60.0, margin=6),
           "GB_Brain": dict(size=1024, smooth=0, interior_scale=1.0, cone=62.0, margin=3)}
PAINTER = {"head": ("GB_Head", 1024, 512), "body": ("GB_Body", 1024, 512), "shorts": ("GB_Shorts", 1024, 512)}

_RESULTS = {"sets": {}, "tileables": {}, "eyes": {}, "decals": {}, "painter": {}, "room": {}, "uv": {},
            "timings_s": {}}


# ---------------------------------------------------------------------------
# Small helpers
# ---------------------------------------------------------------------------
def _log(msg):
    gbc.log(f"bake: {msg}")


def _quick():
    return bool(os.environ.get("GB_BAKE_QUICK"))


def _sz(size):
    return max(128, size // 4) if _quick() else size


def uv_hash(obj):
    """Stable hash of an object's ``atlas`` UVs (1e-5 quantised) and loop topology."""
    me = obj.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["atlas"].data.foreach_get("uv", uv)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    h = hashlib.sha256()
    h.update(np.rint(uv.astype(np.float64) * 1e5).astype(np.int64).tobytes())
    h.update(lv.tobytes())
    return h.hexdigest()[:16]


def _write_png(path, img):
    gbc.write_png_u8(path, img)
    return path


def srgb_encode(lin):
    lin = np.clip(lin, 0.0, 1.0)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(lin, 1.0 / 2.4) - 0.055)


def u8(x):
    return np.clip(np.rint(np.asarray(x, float) * 255.0), 0, 255).astype(np.uint8)


def write_exr_half(path, rgba_top_down):
    """Write a float (H, W, 4) array (row 0 = top) as a half-float ZIP OpenEXR via Blender."""
    h, w = rgba_top_down.shape[:2]
    name = "GB7_exr_tmp"
    old = bpy.data.images.get(name)
    if old is not None:
        bpy.data.images.remove(old)
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    img.pixels.foreach_set(np.ascontiguousarray(rgba_top_down[::-1], np.float32).ravel())
    img.filepath_raw = path
    img.file_format = 'OPEN_EXR'
    try:
        img.use_half_precision = True
    except AttributeError:
        pass
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save()
    bpy.data.images.remove(img)
    return path


# ---------------------------------------------------------------------------
# UV rasteriser (numpy) and image fill
# ---------------------------------------------------------------------------
def loop_triangles(obj):
    """(tri loops (T,3), tri verts (T,3), tri polygon index (T,))."""
    me = obj.data
    me.calc_loop_triangles()
    n = len(me.loop_triangles)
    tl = np.empty(n * 3, np.int64)
    me.loop_triangles.foreach_get("loops", tl)
    tv = np.empty(n * 3, np.int64)
    me.loop_triangles.foreach_get("vertices", tv)
    tp = np.empty(n, np.int64)
    me.loop_triangles.foreach_get("polygon_index", tp)
    return tl.reshape(-1, 3), tv.reshape(-1, 3), tp


def rasterize(obj, size, uv_name="atlas"):
    """Rasterise the UV triangles at texel centres.

    Returns (tri (H, W) int32 = triangle index or -1, bary (H, W, 3) float32), row 0 = top (v = 1)."""
    me = obj.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers[uv_name].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(np.float64) * size - 0.5
    tl, _tv, _tp = loop_triangles(obj)
    tri_img = np.full((size, size), -1, np.int32)
    bary = np.zeros((size, size, 3), np.float32)
    P = uv[tl]                                            # (T, 3, 2)
    x0 = np.clip(np.floor(P[:, :, 0].min(1)).astype(int), 0, size - 1)
    x1 = np.clip(np.ceil(P[:, :, 0].max(1)).astype(int), 0, size - 1)
    y0 = np.clip(np.floor(P[:, :, 1].min(1)).astype(int), 0, size - 1)
    y1 = np.clip(np.ceil(P[:, :, 1].max(1)).astype(int), 0, size - 1)
    for i in range(len(tl)):
        if x1[i] < x0[i] or y1[i] < y0[i]:
            continue
        (ax, ay), (bx, by), (cx, cy) = P[i]
        den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
        if abs(den) < 1e-12:
            continue
        X, Y = np.meshgrid(np.arange(x0[i], x1[i] + 1), np.arange(y0[i], y1[i] + 1))
        l1 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
        l2 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
        l3 = 1.0 - l1 - l2
        m = (l1 >= -1e-7) & (l2 >= -1e-7) & (l3 >= -1e-7)
        if not m.any():
            continue
        tri_img[Y[m], X[m]] = i
        bary[Y[m], X[m]] = np.stack([l1[m], l2[m], l3[m]], -1)
    return tri_img[::-1].copy(), bary[::-1].copy()


def interp(obj, tri_img, bary, per_loop=None, per_vertex=None):
    """Interpolate per-loop or per-vertex values (N, C) over a rasterised image."""
    tl, tv, _ = loop_triangles(obj)
    idx = tl if per_loop is not None else tv
    val = np.asarray(per_loop if per_loop is not None else per_vertex, float)
    if val.ndim == 1:
        val = val[:, None]
    out = np.zeros(tri_img.shape + (val.shape[1],))
    m = tri_img >= 0
    t = tri_img[m]
    b = bary[m].astype(float)
    out[m] = (val[idx[t, 0]] * b[:, :1] + val[idx[t, 1]] * b[:, 1:2] + val[idx[t, 2]] * b[:, 2:3])
    return out


def dilate(img, mask, px=DILATE_PX):
    """Grow covered texels ``px`` times into empty 8-neighbours (average of covered neighbours)."""
    img = np.array(img, float)
    cov = np.array(mask, bool)
    if img.ndim == 2:
        img = img[..., None]
    for _ in range(px):
        acc = np.zeros_like(img)
        cnt = np.zeros(cov.shape)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if dx == 0 and dy == 0:
                    continue
                sc = np.roll(cov, (dy, dx), (0, 1))
                acc += np.roll(img, (dy, dx), (0, 1)) * sc[..., None]
                cnt += sc
        new = ~cov & (cnt > 0)
        img[new] = acc[new] / cnt[new][:, None]
        cov |= new
    return img, cov


def push_pull_fill(img, mask):
    """Fill every empty texel from a coverage-weighted mip pyramid (keeps covered texels)."""
    img = np.array(img, float)
    if img.ndim == 2:
        img = img[..., None]
    w = np.asarray(mask, float)
    levels = [(img * w[..., None], w)]
    while levels[-1][1].shape[0] > 1:
        c, ww = levels[-1]
        h2, w2 = c.shape[0] // 2, c.shape[1] // 2
        c2 = c[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2, -1).sum((1, 3))
        ww2 = ww[:h2 * 2, :w2 * 2].reshape(h2, 2, w2, 2).sum((1, 3))
        levels.append((c2, ww2))
    c, ww = levels[-1]
    filled = c / np.maximum(ww[..., None], 1e-12)
    for c, ww in reversed(levels[:-1]):
        up = np.repeat(np.repeat(filled, 2, 0), 2, 1)[:c.shape[0], :c.shape[1]]
        own = c / np.maximum(ww[..., None], 1e-12)
        k = np.clip(ww, 0.0, 1.0)[..., None]
        filled = own * k + up * (1.0 - k)
    out = np.where(np.asarray(mask, bool)[..., None], img, filled)
    return out


def finish_map(img, mask, px=DILATE_PX):
    """Dilate ``px`` texels, then push-pull fill the rest."""
    d, cov = dilate(img, mask, px)
    return push_pull_fill(d, cov)


# ---------------------------------------------------------------------------
# Scene visibility for bakes
# ---------------------------------------------------------------------------
class Visibility:
    """Context manager: include every collection, show only ``names`` to the renderer."""

    def __init__(self, names):
        self.names = set(names)

    def __enter__(self):
        self.state = {"lc": [], "col": [], "obj": []}
        vl = bpy.context.view_layer

        def walk(lc):
            self.state["lc"].append((lc, lc.exclude, lc.hide_viewport))
            lc.exclude = False
            lc.hide_viewport = False
            for c in lc.children:
                walk(c)
        walk(vl.layer_collection)
        for c in bpy.data.collections:
            self.state["col"].append((c, c.hide_render, c.hide_viewport))
            c.hide_render = False
            c.hide_viewport = False
        for o in bpy.data.objects:
            self.state["obj"].append((o, o.hide_render, o.hide_viewport, o.hide_get()))
            show = o.name in self.names
            o.hide_render = not show
            o.hide_viewport = False
            try:
                o.hide_set(not show)
            except RuntimeError:
                pass
        return self

    def __exit__(self, *exc):
        for o, hr, hv, hs in self.state["obj"]:
            o.hide_render, o.hide_viewport = hr, hv
            try:
                o.hide_set(hs)
            except RuntimeError:
                pass
        for c, hr, hv in self.state["col"]:
            c.hide_render, c.hide_viewport = hr, hv
        for lc, ex, hv in self.state["lc"]:
            lc.exclude, lc.hide_viewport = ex, hv
        return False


def show_all_collections():
    """Include every layer collection (for scripts that open a saved build)."""
    def walk(lc):
        lc.exclude = False
        for c in lc.children:
            walk(c)
    walk(bpy.context.view_layer.layer_collection)


# ---------------------------------------------------------------------------
# Atlas re-charting for the inner meshes
# ---------------------------------------------------------------------------
def _label_components(n, pairs):
    """Connected-component labels of n items joined by index ``pairs`` (min-label propagation)."""
    lab = np.arange(n)
    if len(pairs) == 0:
        return lab
    a, b = pairs[:, 0], pairs[:, 1]
    for _ in range(10000):
        la, lb = lab[a], lab[b]
        m = np.minimum(la, lb)
        new = lab.copy()
        np.minimum.at(new, a, m)
        np.minimum.at(new, b, m)
        new = new[new]
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    _, lab = np.unique(lab, return_inverse=True)
    return lab


def _face_topology(me):
    """(face normals, centres, areas, face adjacency pairs (E,2), edge index per pair, loops per face)."""
    F = len(me.polygons)
    fn = np.empty(F * 3, np.float32)
    me.polygons.foreach_get("normal", fn)
    fc = np.empty(F * 3, np.float32)
    me.polygons.foreach_get("center", fc)
    fa = np.empty(F, np.float32)
    me.polygons.foreach_get("area", fa)
    ls = np.empty(F, np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(F, np.int64)
    me.polygons.foreach_get("loop_total", lt)
    le = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("edge_index", le)
    lf = np.repeat(np.arange(F), lt)
    order = np.argsort(le, kind="stable")
    e_sorted, f_sorted = le[order], lf[order]
    same = e_sorted[1:] == e_sorted[:-1]
    pairs = np.stack([f_sorted[:-1][same], f_sorted[1:][same]], 1)
    pedge = e_sorted[1:][same]
    return (fn.reshape(-1, 3).astype(float), fc.reshape(-1, 3).astype(float), fa.astype(float), pairs, pedge,
            le, lf)


def _euler_ok(me, faces_by_chart, le, lf, lv):
    """Charts that cannot be flattened: closed pieces (Euler characteristic >= 2).  Disks (1) and
    disks with holes (<= 0) have planar conformal maps and are kept."""
    bad = []
    F = len(me.polygons)
    for cid, fidx in faces_by_chart.items():
        sel = np.zeros(F, bool)
        sel[fidx] = True
        lm = sel[lf]
        V = len(np.unique(lv[lm]))
        E = len(np.unique(le[lm]))
        if V - E + len(fidx) >= 2:
            bad.append(cid)
    return bad


def chart_faces(obj, smooth_iters=6, min_frac=0.02, min_faces=40):
    """Segment a mesh into disk-like charts: faces grouped by their neighbourhood-smoothed normal
    (6 axis directions), majority-filtered, small charts merged into neighbours, non-disk charts
    split by planes.  Returns chart id per polygon."""
    me = obj.data
    fn, fc, fa, pairs, pedge, le, lf = _face_topology(me)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    F = len(fn)
    comp = _label_components(F, pairs)
    # neighbourhood-smoothed normals (area weighted)
    ns = fn * fa[:, None]
    for _ in range(smooth_iters):
        acc = ns.copy()
        np.add.at(acc, pairs[:, 0], ns[pairs[:, 1]])
        np.add.at(acc, pairs[:, 1], ns[pairs[:, 0]])
        ns = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12) * fa[:, None]
    ns = ns / np.maximum(np.linalg.norm(ns, axis=1, keepdims=True), 1e-12)
    dirs = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]], float)
    lab = np.argmax(ns @ dirs.T, axis=1)
    for _ in range(3):                                 # majority filter
        hist = np.zeros((F, 6))
        hist[np.arange(F), lab] += 1.5 * fa
        np.add.at(hist, (pairs[:, 0], lab[pairs[:, 1]]), fa[pairs[:, 1]])
        np.add.at(hist, (pairs[:, 1], lab[pairs[:, 0]]), fa[pairs[:, 0]])
        lab = np.argmax(hist, axis=1)
    key = comp * 8 + lab

    def charts_from(key):
        keep = key[pairs[:, 0]] == key[pairs[:, 1]]
        return _label_components(F, pairs[keep])
    chart = charts_from(key)
    comp_area = np.bincount(comp, weights=fa)
    for _ in range(12):                                # merge small charts into their best neighbour
        ch_area = np.bincount(chart, weights=fa)
        ch_n = np.bincount(chart)
        ch_comp = np.zeros(len(ch_area), int)
        ch_comp[chart] = comp
        small = (ch_area < comp_area[ch_comp] * min_frac) | (ch_n < min_faces)
        ca, cb = chart[pairs[:, 0]], chart[pairs[:, 1]]
        cross = ca != cb
        if not (small[ca] & cross).any() and not (small[cb] & cross).any():
            break
        # for every small chart, the neighbour with the longest shared boundary (count of edges)
        src = np.concatenate([ca[cross], cb[cross]])
        dst = np.concatenate([cb[cross], ca[cross]])
        m = small[src] & ~(small[dst] & (ch_area[dst] < ch_area[src]))
        src, dst = src[m], dst[m]
        if len(src) == 0:
            break
        k = src.astype(np.int64) * (len(ch_area) + 1) + dst
        uk, cnt = np.unique(k, return_counts=True)
        s_, d_ = uk // (len(ch_area) + 1), uk % (len(ch_area) + 1)
        best = {}
        for s, d, c in zip(s_, d_, cnt):
            if s not in best or c > best[s][1]:
                best[s] = (d, c)
        remap = np.arange(len(ch_area))
        for s, (d, _c) in best.items():
            remap[s] = d
        for _ in range(8):
            remap = remap[remap]
        chart = remap[chart]
        _, chart = np.unique(chart, return_inverse=True)
    # split charts that are not disks (closed pieces, rings around holes) by planes
    for _ in range(8):
        groups = {}
        for i, c in enumerate(chart):
            groups.setdefault(c, []).append(i)
        groups = {c: np.asarray(f) for c, f in groups.items()}
        bad = _euler_ok(me, groups, le, lf, lv)
        if not bad:
            break
        nxt = chart.max() + 1
        for c in bad:
            f = groups[c]
            pts = fc[f]
            cen = (pts * fa[f, None]).sum(0) / max(fa[f].sum(), 1e-12)
            ext = pts.max(0) - pts.min(0)
            side = pts[:, int(np.argmax(ext))] > cen[int(np.argmax(ext))]
            if side.all() or (~side).all():
                side = np.arange(len(f)) % 2 == 0
            chart[f[side]] = nxt
            nxt += 1
        # a plane split can disconnect a side: relabel by connectivity inside each chart
        chart = charts_from(chart)
    return chart


def _set_seams(me, chart):
    """UV seams on every edge between different charts (and on non-manifold/boundary edges)."""
    fn, fc, fa, pairs, pedge, le, lf = _face_topology(me)
    seam = np.ones(len(me.edges), bool)                 # boundary edges stay seams
    inner = chart[pairs[:, 0]] == chart[pairs[:, 1]]
    counts = np.bincount(le, minlength=len(me.edges))
    ok = inner & (counts[pedge] == 2)
    seam[pedge[ok]] = False
    me.edges.foreach_set("use_seam", seam)
    me.update()


def _select_only(obj):
    vl = bpy.context.view_layer
    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    obj.hide_set(False)
    obj.select_set(True)
    vl.objects.active = obj


def grow_charts(obj, cone_deg=55.0, max_frac=0.03, absorb_deg=75.0, min_faces=6, smooth=0):
    """Greedy normal-cone charts: from the largest unassigned face, grow over edge neighbours whose
    normal lies within ``cone_deg`` of the seed normal (area capped at ``max_frac`` of the mesh).
    Every chart is then a height field over the plane normal to its seed, so a planar projection
    maps it without folds and with at most 1 / cos(cone) stretch.  Tiny charts are absorbed by a
    neighbour whose cone they fit within ``absorb_deg``.  Returns (chart per face, axis per chart)."""
    from collections import deque
    me = obj.data
    fn, fc, fa, pairs, pedge, le, lf = _face_topology(me)
    F = len(fn)
    for _ in range(smooth):          # optional light smoothing of the growth normals (noisy meshes)
        acc = fn * fa[:, None]
        np.add.at(acc, pairs[:, 0], fn[pairs[:, 1]] * fa[pairs[:, 1], None])
        np.add.at(acc, pairs[:, 1], fn[pairs[:, 0]] * fa[pairs[:, 0], None])
        fn = acc / np.maximum(np.linalg.norm(acc, axis=1, keepdims=True), 1e-12)
    nbr = [[] for _ in range(F)]
    for a_, b_ in pairs.tolist():
        nbr[a_].append(b_)
        nbr[b_].append(a_)
    cos_c = np.cos(np.radians(cone_deg))
    cap = fa.sum() * max_frac
    chart = np.full(F, -1, np.int64)
    axes = []
    order = np.argsort(-fa, kind="stable")
    k = 0
    for seed in order.tolist():
        if chart[seed] >= 0:
            continue
        ax = fn[seed]
        chart[seed] = k
        area = fa[seed]
        q = deque([seed])
        while q:
            f = q.popleft()
            for g in nbr[f]:
                if chart[g] < 0 and area < cap and fn[g] @ ax >= cos_c:
                    chart[g] = k
                    area += fa[g]
                    q.append(g)
        axes.append(ax)
        k += 1
    axes = np.asarray(axes)
    # absorb tiny charts into a neighbour whose axis they still face
    cnt = np.bincount(chart, minlength=k)
    cos_a = np.cos(np.radians(absorb_deg))
    for c in np.nonzero(cnt < min_faces)[0].tolist():
        faces = np.nonzero(chart == c)[0]
        cand = {chart[g] for f in faces.tolist() for g in nbr[f] if chart[g] != c}
        best, best_s = None, cos_a
        for d in cand:
            s = float((fn[faces] @ axes[d]).min())
            if s >= best_s:
                best, best_s = d, s
        if best is not None:
            chart[faces] = best
    _, chart = np.unique(chart, return_inverse=True)
    used = np.unique(chart)
    # recompute each chart's projection axis as its area-weighted mean normal (still inside the cone)
    ax = np.zeros((len(used), 3))
    np.add.at(ax, chart, fn * fa[:, None])
    ax /= np.maximum(np.linalg.norm(ax, axis=1, keepdims=True), 1e-12)
    return chart, ax


def rechart(obj, size=2048, smooth=0, interior_scale=1.0, margin_px=UV_MARGIN_PX, cone_deg=55.0):
    """Replace ``obj``'s ``atlas`` UVs with normal-cone charts, planar-projected and packed.

    Charts are projected in metres (uniform texel density by construction), interior surfaces (bone
    marrow cores: ``gb_class`` 6; organ cavities: negative-volume components) are scaled by
    ``interior_scale`` since they only show in cuts, then Blender packs the islands with a
    ``margin_px`` margin at ``size``."""
    me = obj.data
    chart, axes = grow_charts(obj, cone_deg, smooth=smooth)
    _, _, _, _, _, le, lf = _face_topology(me)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    v = gbc.get_verts(me)
    lc = chart[lf]
    ax = axes[lc]
    ref = np.where(np.abs(ax[:, 2:3]) < 0.9, np.array([[0.0, 0.0, 1.0]]), np.array([[1.0, 0.0, 0.0]]))
    e1 = np.cross(ref, ax)
    e1 /= np.maximum(np.linalg.norm(e1, axis=1, keepdims=True), 1e-12)
    e2 = np.cross(ax, e1)
    p = v[lv]
    uv = np.stack([(p * e1).sum(1), (p * e2).sum(1)], 1)
    scale = np.ones(len(chart))
    if interior_scale != 1.0:
        scale[_interior_faces(obj)] = interior_scale
    uv = uv * scale[lf][:, None]
    # small offsets per chart so islands never share UV coordinates before packing
    uv = uv + (lc[:, None] % 97) * 0.0
    if "atlas" not in me.uv_layers:
        me.uv_layers.new(name="atlas")
    me.uv_layers["atlas"].data.foreach_set("uv", uv.astype(np.float32).ravel())
    # mark chart borders as seams so the packer sees the islands, then clear them again
    _set_seams(me, chart)
    me.uv_layers.active = me.uv_layers["atlas"]
    _select_only(obj)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(udim_source='CLOSEST_UDIM', margin_method='FRACTION', margin=margin_px / float(size),
                            rotate=True, shape_method='CONCAVE', scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
    me.edges.foreach_set("use_seam", np.zeros(len(me.edges), bool))
    return int(chart.max() + 1)


def _interior_faces(obj):
    """Per-polygon mask of interior surfaces (marrow cores, organ cavities)."""
    me = obj.data
    F = len(me.polygons)
    cls = gbc.read_point_attr(obj, "gb_class", 'INT')
    ls = np.empty(F, np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    if cls is not None:
        return cls[lv[ls]] == 6
    import lookdev
    inner = lookdev.organ_interior(obj)
    return inner[lv[ls]] > 0.5


def uv_stats(obj, size=1024):
    """(coverage fraction, overlap fraction of covered texels, texel size mm at ``size``)."""
    me = obj.data
    tl, tv, _ = loop_triangles(obj)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["atlas"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(float)
    t = uv[tl]
    a_uv = 0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
                        - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1]))
    v = gbc.get_verts(me)
    P = v[tv]
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    tri_img, _ = rasterize(obj, size)
    cov = (tri_img >= 0).mean()
    over = max(0.0, a_uv.sum() - cov) / max(a_uv.sum(), 1e-9)
    texel = np.sqrt(a3.sum() / max(a_uv.sum(), 1e-12)) / size * 1000.0
    return float(cov), float(over), float(texel)


def prepare_uvs(objs=None, force=False):
    """Re-chart GB_Skeleton, GB_Organs and GB_Brain atlases (cached by mesh hash in .cache/)."""
    t0 = time.perf_counter()
    for name, cfg in RECHART.items():
        obj = bpy.data.objects.get(name)
        if obj is None:
            continue
        me = obj.data
        v = gbc.get_verts(me)
        lv = np.empty(len(me.loops), np.int64)
        me.loops.foreach_get("vertex_index", lv)
        h = hashlib.sha256(np.rint(v * 1e5).astype(np.int64).tobytes() + lv.tobytes()
                           + open(__file__, "rb").read()).hexdigest()[:16]
        path = os.path.join(gbc.CACHE_DIR, f"uv-{name}-{h}.npy")
        if os.path.exists(path) and not force:
            uv = np.load(path)
            if uv.shape[0] == len(me.loops) * 2:
                me.uv_layers["atlas"].data.foreach_set("uv", uv)
                me.update()
                _RESULTS["uv"][name] = {"cached": True}
                continue
        before = uv_stats(obj, 512)
        n = rechart(obj, cfg["size"], cfg["smooth"], cfg["interior_scale"], cfg["margin"], cfg["cone"])
        after = uv_stats(obj, 512)
        uv = np.empty(len(me.loops) * 2, np.float32)
        me.uv_layers["atlas"].data.foreach_get("uv", uv)
        os.makedirs(gbc.CACHE_DIR, exist_ok=True)
        np.save(path, uv)
        _RESULTS["uv"][name] = {"charts": n, "coverage_before": round(before[0], 3),
                                "coverage": round(after[0], 3), "overlap": round(after[1], 5),
                                "texel_mm_at_set_size": round(after[2] * 512 / cfg["size"], 3)}
        _log(f"{name}: {n} charts, coverage {before[0]:.3f} -> {after[0]:.3f}, overlap {after[1]:.4f}")
    _RESULTS["timings_s"]["uvs"] = round(time.perf_counter() - t0, 1)
    return _RESULTS["uv"]


# ---------------------------------------------------------------------------
# Cycles bakes
# ---------------------------------------------------------------------------
def _main_bsdf(mat):
    """The principled BSDF that shades intact tissue (first shader of a Mix Shader chain)."""
    nt = mat.node_tree
    out = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial' and n.is_active_output), None)
    if out is None:
        out = next(n for n in nt.nodes if n.bl_idname == 'ShaderNodeOutputMaterial')
    node = out.inputs['Surface'].links[0].from_node
    for _ in range(10):
        if node.bl_idname == 'ShaderNodeBsdfPrincipled':
            return node, out
        if node.bl_idname == 'ShaderNodeMixShader':
            node = node.inputs[1].links[0].from_node
            continue
        break
    return None, out


PASS_INPUT = {"albedo": "Base Color", "rough": "Roughness", "sss": "Subsurface Weight", "metal": "Metallic"}


def emission_variant(mat, what):
    """Copy of ``mat`` whose surface is an Emission of its main BSDF input ``PASS_INPUT[what]``."""
    name = f"{mat.name}__{what}"
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    m = mat.copy()
    m.name = name
    bsdf, out = _main_bsdf(m)
    nt = m.node_tree
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    if bsdf is None:
        em.inputs['Color'].default_value = (0.5, 0.5, 0.5, 1.0)
    else:
        sock = bsdf.inputs[PASS_INPUT[what]]
        if sock.is_linked:
            nt.links.new(sock.links[0].from_socket, em.inputs['Color'])
        else:
            dv = sock.default_value
            em.inputs['Color'].default_value = tuple(dv)[:3] + (1.0,) if hasattr(dv, "__len__") else (dv, dv, dv, 1.0)
    for lk in list(out.inputs['Surface'].links):
        nt.links.remove(lk)
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    return m


def _bake_image(name, size):
    img = bpy.data.images.get(name)
    if img is not None:
        bpy.data.images.remove(img)
    img = bpy.data.images.new(name, size, size, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'
    img.generated_color = (0.0, 0.0, 0.0, 0.0)
    return img


def _target_material(img):
    mat = bpy.data.materials.get("GB7_bake_target") or bpy.data.materials.new("GB7_bake_target")
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = img
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = "atlas"
    nt.links.new(uvn.outputs[0], tex.inputs['Vector'])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tex.outputs['Color'], out.inputs['Surface'])
    nt.nodes.active = tex
    return mat


def _read(img):
    size = img.size[0]
    a = np.empty(size * size * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(size, size, 4)[::-1].astype(float)


def _cycles(samples):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_denoising = False
    try:
        sc.cycles.use_adaptive_sampling = False
    except AttributeError:
        pass
    return sc


def _bake(pass_type, target, source, img, spec, samples, **kw):
    """One Cycles bake of ``pass_type`` into ``img`` for ``target`` (from ``source`` if given)."""
    sc = _cycles(samples)
    bk = sc.render.bake
    bk.use_selected_to_active = source is not None
    bk.use_cage = False
    bk.cage_extrusion = spec["cage"]
    bk.max_ray_distance = spec["ray"]
    bk.margin = 0
    bk.use_clear = False
    # unbaked texels keep alpha 0: that is how coverage (and holes inside islands) is measured
    img.pixels.foreach_set(np.zeros(img.size[0] * img.size[1] * 4, np.float32))
    bk.target = 'IMAGE_TEXTURES'
    vl = bpy.context.view_layer
    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    if source is not None:
        source.select_set(True)
    target.select_set(True)
    vl.objects.active = target
    bpy.ops.object.bake(type=pass_type, **kw)
    return _read(img)


def _swap_materials(obj, mapping):
    """Replace ``obj``'s slot materials using ``mapping(material) -> material``; returns restore list."""
    me = obj.data
    st = []
    for i, m in enumerate(me.materials):
        nm = mapping(m)
        if nm is not None and nm is not m:
            st.append((me, i, m))
            me.materials[i] = nm
    return st


def _restore(st):
    for me, i, m in reversed(st):
        me.materials[i] = m


def bake_set(name, spec, out):
    """Bake one mesh set (albedo, normal, ORM + SSS).  Returns its record for textures.json."""
    import lookdev
    t0 = time.perf_counter()
    target = bpy.data.objects.get(spec["target"])
    if target is None:
        return None
    source = bpy.data.objects.get(spec["source"]) if spec.get("source") else None
    size = _sz(spec["size"])
    q = _quick()
    s_emit, s_nrm, s_ao = (1, 1, 4) if q else (4, 4, 32)
    visible = [target.name] + ([source.name] if source is not None else [])
    shade = source if source is not None else target
    tri_img, _bary = rasterize(target, size)
    valid = tri_img >= 0
    rec = {"target": target.name, "source": shade.name, "size": size, "uv_hash": uv_hash(target),
           "surfaces": spec["surfaces"], "lod1": spec.get("lod1", []), "files": {}}
    restore = []
    with Visibility(visible):
        img = _bake_image(f"GB7_{name}", size)
        tmat = _target_material(img)
        ld_state = lookdev.lookdev_on([shade])
        base_mats = list(shade.data.materials)
        if source is not None:
            restore += _swap_materials(target, lambda m: tmat)
        else:
            # self-bake: the same object is shaded and receives the image, so every look-dev
            # material gets the image node as its active node
            for m in base_mats:
                if m is None:
                    continue
                nt = m.node_tree
                tex = nt.nodes.get("GB7_target") or nt.nodes.new('ShaderNodeTexImage')
                tex.name = "GB7_target"
                tex.image = img
                nt.nodes.active = tex
        maps = {}
        for what in ("albedo", "rough", "sss"):
            variants = {m.name: emission_variant(m, what) for m in base_mats if m is not None}
            if source is None:
                for m in variants.values():
                    tex = m.node_tree.nodes.get("GB7_target")
                    if tex is not None:
                        m.node_tree.nodes.active = tex
            st = _swap_materials(shade, lambda m: variants.get(m.name) if m is not None else None)
            maps[what] = _bake('EMIT', target, source, img, spec, s_emit)
            _restore(st)
            for m in variants.values():
                bpy.data.materials.remove(m)
        maps["normal"] = _bake('NORMAL', target, source, img, spec, s_nrm, normal_space='TANGENT',
                               normal_r='POS_X', normal_g='POS_Y', normal_b='POS_Z')
        world = bpy.context.scene.world or bpy.data.worlds.new("GB7_world")
        bpy.context.scene.world = world
        world.light_settings.distance = spec["ao"]
        # the target must not shadow its own source during the AO bake
        vis_state = [(target, target.visible_diffuse, target.visible_shadow, target.visible_glossy)]
        if source is not None:
            target.visible_diffuse = target.visible_shadow = target.visible_glossy = False
        maps["ao"] = _bake('AO', target, source, img, spec, s_ao)
        for o, d, s, g in vis_state:
            o.visible_diffuse, o.visible_shadow, o.visible_glossy = d, s, g
        lookdev.lookdev_off(ld_state)
        _restore(restore)
        if source is None:
            for m in base_mats:
                if m is not None and m.node_tree.nodes.get("GB7_target") is not None:
                    m.node_tree.nodes.remove(m.node_tree.nodes["GB7_target"])
        bpy.data.images.remove(img)
    covered = maps["albedo"][..., 3] > 0.5
    holes = valid & ~covered
    rec["coverage"] = {"valid_texels": int(valid.sum()), "empty_inside_islands": int(holes.sum()),
                       "empty_fraction": round(float(holes.sum()) / max(int(valid.sum()), 1), 6),
                       "baked_outside_raster": int((covered & ~valid).sum())}
    mask = covered | valid
    # holes (if any) are filled from their neighbours before dilation
    alb = finish_map(maps["albedo"][..., :3], covered)
    nrm = finish_map(maps["normal"][..., :3], covered)
    nv = nrm * 2.0 - 1.0
    nv /= np.maximum(np.linalg.norm(nv, axis=-1, keepdims=True), 1e-6)
    nrm = nv * 0.5 + 0.5
    rough = finish_map(maps["rough"][..., :1], covered)[..., 0]
    sss = finish_map(maps["sss"][..., :1], covered)[..., 0]
    ao = finish_map(maps["ao"][..., :1], covered)[..., 0]
    orm = np.stack([ao, rough, np.zeros_like(ao), sss], -1)
    files = {"albedo": f"{name}_albedo.png", "normal": f"{name}_normal.png", "orm": f"{name}_orm.png"}
    _write_png(os.path.join(out, files["albedo"]), u8(srgb_encode(alb)))
    _write_png(os.path.join(out, files["normal"]), u8(nrm))
    _write_png(os.path.join(out, files["orm"]), u8(orm))
    rec["files"] = files
    lum = alb[..., 0] * 0.2126 + alb[..., 1] * 0.7152 + alb[..., 2] * 0.0722
    rec["albedo_linear_luminance"] = {"median": round(float(np.median(lum[valid])), 4),
                                      "p5": round(float(np.percentile(lum[valid], 5)), 4),
                                      "p95": round(float(np.percentile(lum[valid], 95)), 4)}
    rec["albedo_linear_median_rgb"] = [round(float(np.median(alb[..., c][valid])), 4) for c in range(3)]
    rec["ao_mean"] = round(float(ao[valid].mean()), 3)
    rec["normal_mean_z"] = round(float(nv[..., 2][valid].mean()), 4)
    rec["seconds"] = round(time.perf_counter() - t0, 1)
    _log(f"set {name}: {size}^2, empty {rec['coverage']['empty_inside_islands']} texels, "
         f"{rec['seconds']} s")
    return rec


def bake_all(objs, out, only=None):
    """Bake every mesh set of SETS into ``out`` (prepare_uvs + lookdev attributes first)."""
    import lookdev
    t0 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    prepare_uvs(objs)
    lookdev.build_materials()
    lookdev.prepare_attributes()
    for name, spec in SETS.items():
        if only and name not in only:
            continue
        rec = bake_set(name, spec, out)
        if rec is not None:
            _RESULTS["sets"][name] = rec
    bake_eyes(out)
    _RESULTS["timings_s"]["sets"] = round(time.perf_counter() - t0, 1)
    write_texture_manifest(out)
    return _RESULTS["sets"]


# ---------------------------------------------------------------------------
# Eyes (numpy): iris disc + sclera in the GB_Eye atlas
# ---------------------------------------------------------------------------
def bake_eyes(out):
    """eye_iris_albedo.png (RGB + A height), eye_iris_normal.png, eye_sclera_albedo.png (atlas UV of
    GB_Eye_L/R; A = 1 on the sclera, 0 inside the cornea where the refracted iris shows)."""
    import texgen as tg
    import lookdev
    n = _sz(1024)
    d = tg.iris(n)
    h = d["height"]
    hn = np.clip((h - h.min()) / max(np.ptp(h), 1e-9), 0, 1)
    alb = np.concatenate([tg.to_u8(tg.linear_to_srgb(d["albedo"])), tg.to_u8(hn)[..., None]], -1)
    _write_png(os.path.join(out, "eye_iris_albedo.png"), alb)
    nrm = tg.height_to_normal(h, d["texel_mm"], wrap=False, strength=1.0)
    _write_png(os.path.join(out, "eye_iris_normal.png"), tg.to_u8(nrm * 0.5 + 0.5))
    rec = {"iris": {"files": {"albedo_height": "eye_iris_albedo.png", "normal": "eye_iris_normal.png"},
                    "size": n, "radius_m": d["radius_m"], "iris_r_m": tg.IRIS_R, "pupil_r_m": tg.PUPIL_R,
                    "limbus_r_m": tg.LIMBUS_R, "mapping": "image centre = gaze axis; edge (uv radius 0.5) = "
                    "radius_m; +u = eye-local +X, +v = eye-local +Z; pupil drawn at pupil_r_m, remap "
                    "rn = (r - pupil) / (iris_r - pupil) for dilation", "height_range_mm":
                    [round(float(h.min()), 4), round(float(h.max()), 4)]}}
    eye = bpy.data.objects.get("GB_Eye_L")
    if eye is not None:
        size = _sz(1024)
        tri, bary = rasterize(eye, size)
        v = gbc.get_verts(eye.data)
        c = np.array(lookdev.eye_centre(eye))
        p = interp(eye, tri, bary, per_vertex=v - c)
        valid = tri >= 0
        col, hh, iris_m = tg.sclera(p[valid].reshape(-1, 3))
        img = np.zeros((size, size, 3))
        img[valid] = col
        a = np.zeros((size, size))
        a[valid] = 1.0 - iris_m
        img = finish_map(img, valid)
        a = finish_map(a[..., None], valid)[..., 0]
        _write_png(os.path.join(out, "eye_sclera_albedo.png"),
                   np.concatenate([u8(srgb_encode(img)), u8(a)[..., None]], -1))
        rec["sclera"] = {"file": "eye_sclera_albedo.png", "size": size, "uv": "atlas of GB_Eye_L and GB_Eye_R",
                         "uv_hash": uv_hash(eye), "alpha": "1 sclera, 0 cornea/iris window"}
    _RESULTS["eyes"] = rec
    return rec


# ---------------------------------------------------------------------------
# Tileables, decals, room
# ---------------------------------------------------------------------------
def _write_set(out, prefix, d, metal=0.0):
    import texgen as tg
    s = tg.pack_set(d["albedo"], d["height"], d["rough"], d["ao"], d["texel_mm"], d.get("metal", metal))
    files = {}
    for k in ("albedo", "normal", "orm"):
        fn = f"{prefix}_{k}.png"
        _write_png(os.path.join(out, fn), s[k])
        files[k] = fn
    err = max(tg.tile_edge_error(s[k]) for k in s)
    return files, err


def bake_tileables(out):
    """Seamless tissue tileables, decals and room/prop tileables (numpy, deterministic)."""
    import texgen as tg
    t0 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    n = 128 if _quick() else tg.TILE_SIZE
    for name, fn in tg.TILEABLES.items():
        d = fn(n)
        files, err = _write_set(out, f"tile_{name}", d)
        _RESULTS["tileables"][name] = {"files": files, "size": n, "tile_m": tg.TILE_M[name],
                                       "edge_error_255": round(err, 3), "core": name in tg.CORE_TILEABLES,
                                       "albedo_is_detail": bool(d.get("albedo_is_detail", False))}
    alb, nrm, orm, info = tg.decal_atlas(64 if _quick() else 256)
    _write_png(os.path.join(out, "decal_blood_albedo.png"), alb)
    _write_png(os.path.join(out, "decal_blood_normal.png"), nrm)
    _write_png(os.path.join(out, "decal_blood_orm.png"), orm)
    _RESULTS["decals"] = {"files": {"albedo": "decal_blood_albedo.png", "normal": "decal_blood_normal.png",
                                    "orm": "decal_blood_orm.png"}, "grid": 8, "tile_px": alb.shape[0] // 8,
                          "count": len(info), "tiles": info,
                          "channels": "albedo RGB fresh blood colour (sRGB), A coverage; ORM A = thickness 0-1"}
    for name, fn in tg.ROOM_TEXTURES.items():
        d = fn()
        files, err = _write_set(out, name, d)
        _RESULTS["room"][name] = {"files": files, "size": d["albedo"].shape[0], "tile_m": tg.ROOM_TILE_M[name],
                                  "metallic": float(d.get("metal", 0.0)), "edge_error_255": round(err, 3)}
    _RESULTS["timings_s"]["tileables"] = round(time.perf_counter() - t0, 1)
    write_texture_manifest(out)
    return _RESULTS["tileables"]


# ---------------------------------------------------------------------------
# Painter inputs
# ---------------------------------------------------------------------------
def bake_painter_inputs(objs, out):
    """Position (segment-relative, half EXR), rest normal, valid mask and dominant-bone maps."""
    import export
    import rig
    t0 = time.perf_counter()
    os.makedirs(out, exist_ok=True)
    origins = export.segment_origins()
    by_code = {v["code"]: np.array(v["origin"]) for v in origins.values()}
    for name, (oname, size, bsize) in PAINTER.items():
        obj = bpy.data.objects.get(oname)
        if obj is None:
            continue
        size, bsize = _sz(size), _sz(bsize)
        me = obj.data
        v = gbc.get_verts(me)
        seg = gbc.read_point_attr(obj, "gb_seg", 'INT')
        seg = np.full(len(v), 10 if name == "shorts" else 0) if seg is None else seg
        tri, bary = rasterize(obj, size)
        valid = tri >= 0
        pos = interp(obj, tri, bary, per_vertex=v)
        # segment per texel: the triangle's first-corner segment (segments do not blend)
        tl, tv, _ = loop_triangles(obj)
        tseg = seg[tv[:, 0]]
        segimg = np.where(valid, tseg[np.maximum(tri, 0)], -1)
        org = np.zeros(pos.shape)
        for code, o in by_code.items():
            org[segimg == code] = o
        rel = pos - org
        rgba = np.concatenate([rel, segimg[..., None].astype(float)], -1)
        rgba[~valid] = 0.0
        rgba[~valid, 3] = -1.0
        # dilation keeps the segment code of the nearest island (positions extend smoothly)
        dil, cov = dilate(rgba, valid, DILATE_PX)
        dil[~cov] = 0.0
        dil[~cov, 3] = -1.0
        # a dilated texel between two segments gets an averaged code: snap back to the nearest valid code
        codes = dil[..., 3]
        dil[..., 3] = np.where(cov, np.rint(codes), -1.0)
        write_exr_half(os.path.join(out, f"{name}_position.exr"), dil)
        # rest normal (object space), 8-bit
        nrm = np.empty(len(me.loops) * 3, np.float32)
        me.loops.foreach_get("normal", nrm)
        n_img = interp(obj, tri, bary, per_loop=nrm.reshape(-1, 3))
        n_img /= np.maximum(np.linalg.norm(n_img, axis=-1, keepdims=True), 1e-9)
        n_img = finish_map(n_img, valid)
        n_img /= np.maximum(np.linalg.norm(n_img, axis=-1, keepdims=True), 1e-9)
        _write_png(os.path.join(out, f"{name}_rest_normal.png"), u8(n_img * 0.5 + 0.5))
        _write_png(os.path.join(out, f"{name}_valid.png"), u8(valid.astype(float)))
        # dominant bone at the lower resolution
        tri_b, bary_b = rasterize(obj, bsize)
        vb = tri_b >= 0
        pb = interp(obj, tri_b, bary_b, per_vertex=v)
        idx, w = rig.weights_at(pb[vb])
        order = np.argsort(-w, axis=1)
        i0 = idx[np.arange(len(idx)), order[:, 0]]
        i1 = idx[np.arange(len(idx)), order[:, 1]]
        w0 = w[np.arange(len(w)), order[:, 0]]
        bone = np.zeros((bsize, bsize, 4))
        bone[vb, 0] = i0
        bone[vb, 1] = i1
        bone[vb, 2] = w0 * 255.0
        bone[vb, 3] = 255.0
        # nearest-neighbour dilation for the indices (never average bone ids)
        bone = _dilate_nearest(bone, vb, DILATE_PX)
        _write_png(os.path.join(out, f"{name}_bone.png"), np.clip(np.rint(bone), 0, 255).astype(np.uint8))
        _RESULTS["painter"][name] = {
            "mesh": oname, "uv_hash": uv_hash(obj), "size": size, "bone_size": bsize,
            "files": {"position": f"{name}_position.exr", "rest_normal": f"{name}_rest_normal.png",
                      "valid": f"{name}_valid.png", "bone": f"{name}_bone.png"},
            "valid_fraction": round(float(valid.mean()), 4),
            "position": "RGB = rest position - segment origin (m, body frame); A = segment code, -1 outside "
                        "islands + dilation; origins in manifest.json segment_origins",
            "bone": "R = dominant bone index (rig.json order), G = second bone, B = dominant weight x 255, "
                    "A = 255 inside islands (dilated 8 px, nearest)",
            "rest_normal": "object/body-frame rest normal, 0.5 + 0.5 n"}
        if name == "body":
            _RESULTS["painter"][name]["tissue_depth"] = "body_tissue_depth.png (B1)"
            _RESULTS["painter"][name]["tension"] = "body_tension.png (B1)"
    _RESULTS["timings_s"]["painter"] = round(time.perf_counter() - t0, 1)
    write_texture_manifest(out)
    return _RESULTS["painter"]


def _dilate_nearest(img, mask, px):
    img = np.array(img, float)
    cov = np.array(mask, bool)
    for _ in range(px):
        new_img = img.copy()
        new_cov = cov.copy()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (-1, -1), (1, -1), (-1, 1)):
            sc = np.roll(cov, (dy, dx), (0, 1))
            take = sc & ~new_cov
            new_img[take] = np.roll(img, (dy, dx), (0, 1))[take]
            new_cov |= take
        img, cov = new_img, new_cov
    return img


# ---------------------------------------------------------------------------
# textures.json
# ---------------------------------------------------------------------------
MATERIAL_MAP = {
    "GBM_skin_head": "head", "GBM_mouth_lining": "head", "GBM_skin_torso": "body", "GBM_skin_arm_L": "body",
    "GBM_skin_arm_R": "body", "GBM_skin_leg_L": "body", "GBM_skin_leg_R": "body", "GBM_cloth": "shorts",
    "GBM_teeth": "mouth", "GBM_gums": "mouth", "GBM_tongue": "mouth", "GBM_bone": "skeleton",
    "GBM_cartilage": "skeleton", "GBM_organ": "organs", "GBM_brain": "brain",
    "GBM_eye": "eyes (iris + sclera)", "GBM_muscle_*": "tile_muscle_fibre / tile_muscle_cross (triplanar)",
    "GB_Frac_* GBM_bone": "tile_bone_surface outside, tile_bone_cut / tile_diploe on fracture faces (triplanar)",
    "GBM_hair_card": "hair_cards.png (B2)",
}


def write_texture_manifest(out):
    """Write textures/textures.json from everything baked in this process (merged with a previous file)."""
    path = os.path.join(out, "textures.json")
    prev = {}
    if os.path.exists(path):
        try:
            prev = gbc.read_json(path)["data"]
        except (ValueError, KeyError):
            prev = {}
    data = {}
    for k in ("sets", "tileables", "eyes", "decals", "painter", "room", "uv"):
        merged = dict(prev.get(k, {}))
        merged.update(_RESULTS.get(k, {}))
        data[k] = merged
    data["material_map"] = MATERIAL_MAP
    data["conventions"] = {
        "rows": "top to bottom, v = 1 at the top (Godot image origin)",
        "albedo": "sRGB PNG (import as BC7 sRGB)",
        "normal": "tangent space, OpenGL/Godot +Y, MikkTSpace on the LOD0 mesh (import as RGTC normal map)",
        "orm": "R ambient occlusion, G roughness, B metallic, A SSS mask (mesh sets) or height 0-1 "
               "(tileables); linear (BC7 linear)",
        "painter": "lossless, uncompressed import (position EXR half)",
        "tile_m": "physical size of one tileable repeat in metres (triplanar / metre UV scale)"}
    tim = dict(prev.get("timings_s", {}))
    tim.update(_RESULTS["timings_s"])
    data["timings_s"] = tim
    files = {}
    for fn in sorted(os.listdir(out)):
        if fn.endswith((".png", ".exr")):
            p = os.path.join(out, fn)
            files[fn] = {"bytes": os.path.getsize(p), "sha256": gbc.file_hash(p)[:16]}
    data["files"] = files
    gbc.write_json(path, data, SCHEMA)
    return path


# ---------------------------------------------------------------------------
# Baked-material preview (renders what the game shows)
# ---------------------------------------------------------------------------
def _baked_material(set_name, rec, out, sss_radius=(1.0, 0.4, 0.22), sss_scale=0.0035):
    name = f"GB7_baked_{set_name}"
    old = bpy.data.materials.get(name)
    if old is not None:
        bpy.data.materials.remove(old)
    mat = bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    uvn = nt.nodes.new('ShaderNodeUVMap')
    uvn.uv_map = "atlas"

    def tex(fn, cs):
        img = bpy.data.images.load(os.path.join(out, fn), check_existing=True)
        img.colorspace_settings.name = cs
        n = nt.nodes.new('ShaderNodeTexImage')
        n.image = img
        nt.links.new(uvn.outputs[0], n.inputs['Vector'])
        return n
    a = tex(rec["files"]["albedo"], 'sRGB')
    nm = tex(rec["files"]["normal"], 'Non-Color')
    orm = tex(rec["files"]["orm"], 'Non-Color')
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(orm.outputs['Color'], sep.inputs[0])
    nmap = nt.nodes.new('ShaderNodeNormalMap')
    nmap.uv_map = "atlas"
    nt.links.new(nm.outputs['Color'], nmap.inputs['Color'])
    bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.subsurface_method = 'RANDOM_WALK_SKIN' if set_name in ("head", "body") else 'RANDOM_WALK'
    mixao = nt.nodes.new('ShaderNodeMix')
    mixao.data_type = 'RGBA'
    mixao.blend_type = 'MULTIPLY'
    mixao.inputs['Factor'].default_value = 1.0
    nt.links.new(a.outputs['Color'], mixao.inputs['A'])
    nt.links.new(sep.outputs[0], mixao.inputs['B'])
    nt.links.new(mixao.outputs['Result'], bsdf.inputs['Base Color'])
    nt.links.new(sep.outputs[1], bsdf.inputs['Roughness'])
    nt.links.new(sep.outputs[2], bsdf.inputs['Metallic'])
    nt.links.new(orm.outputs['Alpha'], bsdf.inputs['Subsurface Weight'])
    bsdf.inputs['Subsurface Radius'].default_value = sss_radius
    bsdf.inputs['Subsurface Scale'].default_value = sss_scale
    nt.links.new(nmap.outputs[0], bsdf.inputs['Normal'])
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(bsdf.outputs[0], o.inputs['Surface'])
    return mat


def apply_baked_materials(out=None):
    """Put preview materials using the baked sets on the LOD0 targets (for renders). Returns restore list."""
    out = out or os.path.join(gbc.SUBJECT_OUT, "textures")
    data = gbc.read_json(os.path.join(out, "textures.json"))["data"]
    st = []
    for name, rec in data["sets"].items():
        obj = bpy.data.objects.get(rec["target"])
        if obj is None:
            continue
        mat = _baked_material(name, rec, out)
        st += _swap_materials(obj, lambda m: mat)
    return st


def main():
    """Standalone: open the saved build, bake (``--only set,set``, ``--tiles``, ``--painter``), no save."""
    args = gbc.script_args()
    if "--quick" in args:
        os.environ["GB_BAKE_QUICK"] = "1"
    blend = args[args.index("--blend") + 1] if "--blend" in args else gbc.BLEND_PATH
    out = args[args.index("--out") + 1] if "--out" in args else os.path.join(gbc.SUBJECT_OUT, "textures")
    bpy.ops.wm.open_mainfile(filepath=blend)
    show_all_collections()
    only = args[args.index("--only") + 1].split(",") if "--only" in args else None
    if "--tiles" in args:
        bake_tileables(out)
    if "--painter" in args:
        bake_painter_inputs(None, out)
    if only is not None or not ("--tiles" in args or "--painter" in args):
        bake_all(None, out, only)
    if "--save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=args[args.index("--save") + 1], compress=True)


if __name__ == "__main__":
    main()


def uv_distortion(obj):
    """Area distortion of the atlas: (p10, p90) of log2(UV area / 3-D area) per triangle, relative to
    the area-weighted median (0 = perfectly uniform texel density)."""
    me = obj.data
    tl, tv, _ = loop_triangles(obj)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["atlas"].data.foreach_get("uv", uv)
    t = uv.reshape(-1, 2).astype(float)[tl]
    a_uv = 0.5 * np.abs((t[:, 1, 0] - t[:, 0, 0]) * (t[:, 2, 1] - t[:, 0, 1])
                        - (t[:, 2, 0] - t[:, 0, 0]) * (t[:, 1, 1] - t[:, 0, 1]))
    P = gbc.get_verts(me)[tv]
    a3 = 0.5 * np.linalg.norm(np.cross(P[:, 1] - P[:, 0], P[:, 2] - P[:, 0]), axis=1)
    ok = a3 > 1e-12
    r = np.log2(np.maximum(a_uv[ok], 1e-20) / a3[ok])
    w = a3[ok]
    o = np.argsort(r)
    cw = np.cumsum(w[o]) / w.sum()
    med = r[o][np.searchsorted(cw, 0.5)]
    return (float(r[o][np.searchsorted(cw, 0.1)] - med), float(r[o][np.searchsorted(cw, 0.9)] - med))
