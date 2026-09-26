"""Geometry helpers shared by the body builders (owner B0).

numpy-first mesh utilities on top of the head project's SDF toolkit
(``gore_head/anatomy.py``: ``sample_grid``, ``surface_nets``, ``mesh_sdf`` ...):

* ``sdf_mesh``          - polygonise an SDF into a contract-named object (remesh + projection)
* ``sweep``             - tube / ribbon sweep with parallel-transport frames (vessels, ribs, cord)
* ``cut_plane``         - keep one side of a mesh at a plane (bmesh bisect)
* ``seam_ring_from_sdf``- canonical ring of points on an SDF's zero contour in a horizontal plane
* ``zip_to_ring``       - replace a mesh's open boundary by a strip to a given ring (exact seam)
* ``decimate_to``       - collapse-decimate to a triangle budget (modifier applied)
* ``split_pieces``      - split faces into loose pieces by a per-face id (fracture variants)
* ``join_meshes``       - merge (verts, faces, per-vertex attrs) parts into one object
* ``smart_uv``          - quick atlas UV (Smart UV Project) into the ``atlas`` map

All coordinates are body frame metres.
"""
import math

import numpy as np

import bmesh
import bpy
from mathutils import Vector

import gb_common as gbc


def head():
    """Shortcut to the head project's anatomy module (SDF toolkit)."""
    return gbc.import_head().anatomy


# ---------------------------------------------------------------------------
# SDF -> mesh
# ---------------------------------------------------------------------------
def sdf_mesh(name, fn, lo, hi, h, project=2, remesh=True, relax=0):
    """Polygonise ``fn(x, y, z)`` (negative inside) in the box ``lo..hi`` at spacing ``h``.

    Returns a mesh datablock (not linked to an object) so callers decide the
    object name/collection.  Uses the head toolkit: sparse grid -> surface
    nets -> voxel remesh -> Newton projection onto the exact surface."""
    A = head()
    col = bpy.context.scene.collection
    tmp = A.mesh_sdf("_gb_tmp_sdf", fn, lo, hi, h, voxel=h if remesh else None, project=project,
                     relax=relax, collection=col)
    me = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    me.name = name
    return me


def eval_sdf(fn, pts):
    """Evaluate an SDF on an (N, 3) array."""
    return head().eval_points(fn, np.asarray(pts, dtype=float))


# ---------------------------------------------------------------------------
# Polyline utilities and sweeps
# ---------------------------------------------------------------------------
def resample(points, step, smooth=True):
    """Catmull-Rom densify (if ``smooth``) then resample a polyline at ~``step`` arc length.

    Returns (P[M,3], t[M]) with t the normalised arc parameter (0..1)."""
    p = np.asarray(points, dtype=float)
    if smooth and len(p) > 2:
        p = head().catmull(p, n=8)
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    keep = np.concatenate([[True], seg > 1e-9])
    p = p[keep]
    seg = np.linalg.norm(np.diff(p, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    total = cum[-1]
    if total < 1e-9:
        return p[:1].repeat(2, axis=0), np.array([0.0, 1.0])
    m = max(2, int(math.ceil(total / max(step, 1e-6))) + 1)
    s = np.linspace(0.0, total, m)
    out = np.stack([np.interp(s, cum, p[:, i]) for i in range(3)], axis=1)
    return out, s / total


def _frames(P, up_hint=None):
    """Parallel-transport frames (T, N, B) along a polyline."""
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    up = np.array(up_hint if up_hint is not None else (0.0, 0.0, 1.0), dtype=float)
    if abs(up @ T[0]) > 0.95:
        up = np.array([1.0, 0.0, 0.0]) if abs(T[0][0]) < 0.9 else np.array([0.0, 1.0, 0.0])
    N = np.zeros_like(P)
    n0 = up - (up @ T[0]) * T[0]
    N[0] = n0 / np.linalg.norm(n0)
    for i in range(1, len(P)):
        n = N[i - 1] - (N[i - 1] @ T[i]) * T[i]
        ln = np.linalg.norm(n)
        N[i] = n / ln if ln > 1e-9 else N[i - 1]
    B = np.cross(T, N)
    return T, N, B


def sweep(points, radii, sides=8, step=None, smooth=True, ellipse=None, normal_fn=None, caps=True,
          up_hint=None):
    """Sweep a closed section along a polyline.

    radii: scalar, per-control-point list, or (K, 2) per-point (radius along N, radius along B).
    ellipse: optional (ratio_N, ratio_B) scaling of the section (e.g. flat ribs).
    normal_fn: optional f(P) -> preferred section normal per sample (overrides transport).
    Returns (verts[V,3], faces[list], t_per_vertex[V])."""
    ctrl = np.asarray(points, dtype=float)
    r_in = np.asarray(radii, dtype=float)
    if r_in.ndim == 2:                                  # per-point (radius_N, radius_B)
        r_ctrl = r_in
    else:
        r1 = np.broadcast_to(r_in, (len(ctrl),)).astype(float)
        r_ctrl = np.stack([r1, r1], axis=1)
    if step is None:
        step = max(0.004, 2.0 * float(r_ctrl.mean()))
    P, t = resample(ctrl, step, smooth)
    # radius along the arc: interpolate on the control points' cumulative length
    cl = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(ctrl, axis=0), axis=1))])
    cl = cl / max(cl[-1], 1e-9)
    RN = np.interp(t, cl, r_ctrl[:, 0])
    RB = np.interp(t, cl, r_ctrl[:, 1])
    T, N, B = _frames(P, up_hint)
    if normal_fn is not None:
        pref = np.asarray(normal_fn(P), dtype=float)
        pref = pref - (pref * T).sum(1, keepdims=True) * T
        ok = np.linalg.norm(pref, axis=1) > 1e-9
        pref[ok] /= np.linalg.norm(pref[ok], axis=1, keepdims=True)
        N[ok] = pref[ok]
        B = np.cross(T, N)
    ex, ey = (1.0, 1.0) if ellipse is None else ellipse
    phi = np.linspace(0.0, 2.0 * np.pi, sides, endpoint=False)
    ring = (np.cos(phi)[None, :, None] * N[:, None, :] * (ex * RN)[:, None, None]
            + np.sin(phi)[None, :, None] * B[:, None, :] * (ey * RB)[:, None, None])
    V = P[:, None, :] + ring                                        # (M, sides, 3)
    M = len(P)
    verts = V.reshape(-1, 3)
    tv = np.repeat(t, sides)
    faces = []
    for i in range(M - 1):
        a0, b0 = i * sides, (i + 1) * sides
        for k in range(sides):
            k1 = (k + 1) % sides
            faces.append((a0 + k, a0 + k1, b0 + k1, b0 + k))
    if caps:
        c0 = len(verts)
        verts = np.vstack([verts, P[0], P[-1]])
        tv = np.concatenate([tv, [0.0, 1.0]])
        last = (M - 1) * sides
        for k in range(sides):
            k1 = (k + 1) % sides
            faces.append((c0, k1, k))
            faces.append((c0 + 1, last + k, last + k1))
    return verts, faces, tv


# ---------------------------------------------------------------------------
# bmesh helpers
# ---------------------------------------------------------------------------
def cut_plane(me, z, keep="below"):
    """Bisect mesh ``me`` at the horizontal plane ``z`` and keep one side (in place)."""
    bm = bmesh.new()
    bm.from_mesh(me)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-7, plane_co=(0.0, 0.0, z), plane_no=(0.0, 0.0, 1.0),
                           clear_inner=(keep == "above"), clear_outer=(keep == "below"))
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def boundary_loops(me):
    """Ordered boundary loops (lists of vertex indices) of a mesh."""
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    edges = [e for e in bm.edges if e.is_boundary]
    adj = {}
    for e in edges:
        a, b = e.verts[0].index, e.verts[1].index
        adj.setdefault(a, []).append(b)
        adj.setdefault(b, []).append(a)
    bm.free()
    loops, seen = [], set()
    for start in adj:
        if start in seen:
            continue
        loop = [start]
        seen.add(start)
        prev, cur = None, start
        while True:
            nxt = [n for n in adj[cur] if n != prev and n not in seen]
            if not nxt:
                break
            prev, cur = cur, nxt[0]
            loop.append(cur)
            seen.add(cur)
        loops.append(loop)
    return loops


def delete_band(me, z, band, side):
    """Delete faces with any vertex within ``band`` of plane z (on ``side`` 'above'/'below'),
    then loose vertices; leaves a clean open boundary about one band away from the plane."""
    bm = bmesh.new()
    bm.from_mesh(me)
    kill = [f for f in bm.faces if any(abs(v.co.z - z) < band for v in f.verts)]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def seam_ring_from_sdf(fn, z, n, centre_xy=(0.0, 0.0), r_max=0.15, iters=40):
    """``n`` points on the zero contour of ``fn`` in the plane ``z``, by bisection along rays
    from ``centre_xy`` at equal angles (counter-clockwise seen from +Z, starting at +X)."""
    ang = 2.0 * np.pi * np.arange(n) / n
    d = np.stack([np.cos(ang), np.sin(ang)], axis=1)
    lo = np.full(n, 0.0)
    hi = np.full(n, r_max)
    cx, cy = centre_xy
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        pts = np.stack([cx + d[:, 0] * mid, cy + d[:, 1] * mid, np.full(n, z)], axis=1)
        f = eval_sdf(fn, pts)
        inside = f < 0
        lo = np.where(inside, mid, lo)
        hi = np.where(inside, hi, mid)
    r = 0.5 * (lo + hi)
    return np.stack([cx + d[:, 0] * r, cy + d[:, 1] * r, np.full(n, z)], axis=1)


def zip_to_ring(obj, ring, centre_xy, side):
    """Bridge the single open boundary loop of ``obj`` to ``ring`` with a triangle strip.

    ``ring``: (n, 3) points ordered by angle (``seam_ring_from_sdf``).  The ring
    vertices are appended verbatim, so every mesh zipped to the same ring
    shares exactly identical seam vertices (plan FB-1, gap 0).  ``side``
    'above' / 'below' tells where the mesh lies relative to the ring, for
    face orientation (normals point away from the neck axis)."""
    me = obj.data
    loops = boundary_loops(me)
    if not loops:
        raise ValueError(f"{obj.name}: no open boundary to zip")
    v = gbc.get_verts(me)
    cx, cy = centre_xy
    # the loop nearest the ring plane and axis is the seam loop
    def score(lp):
        q = v[lp]
        return abs(q[:, 2].mean() - ring[0, 2]) + np.hypot(q[:, 0] - cx, q[:, 1] - cy).mean()
    loop = min(loops, key=score)
    q = v[loop]
    ang_a = np.mod(np.arctan2(q[:, 1] - cy, q[:, 0] - cx), 2 * np.pi)
    order = np.argsort(ang_a)
    A = [loop[i] for i in order]
    aa = ang_a[order]
    ang_r = np.mod(np.arctan2(ring[:, 1] - cy, ring[:, 0] - cx), 2 * np.pi)
    ordr = np.argsort(ang_r)
    ring = ring[ordr]
    ar = ang_r[ordr]
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    RV = [bm.verts.new(Vector(p)) for p in ring]
    AV = [bm.verts[i] for i in A]
    na, nr = len(AV), len(RV)
    # merge the two angular sequences (cyclic): walk both loops once
    i = j = 0
    aa_ext = np.concatenate([aa, aa[:1] + 2 * np.pi])
    ar_ext = np.concatenate([ar, ar[:1] + 2 * np.pi])
    faces = []
    while i < na or j < nr:
        adv_a = j >= nr or (i < na and aa_ext[i + 1] <= ar_ext[j + 1])
        if adv_a:
            tri = (AV[i % na], AV[(i + 1) % na], RV[j % nr])
            i += 1
        else:
            tri = (RV[j % nr], RV[(j + 1) % nr], AV[i % na])
            j += 1
        faces.append(tri)
    for tri in faces:
        if len({id(x) for x in tri}) < 3:
            continue
        try:
            f = bm.faces.new(tri)
        except ValueError:
            continue
        f.normal_update()
        c = f.calc_center_median()
        radial = Vector((c.x - cx, c.y - cy, 0.0))
        if f.normal.dot(radial) < 0:
            f.normal_flip()
        f.smooth = True
    bm.to_mesh(me)
    bm.free()
    me.update()
    ring_idx = np.arange(len(v), len(v) + nr)
    return ring_idx


def decimate_to(obj, target_tris, keep_boundary=False):
    """Collapse-decimate ``obj`` in place to about ``target_tris`` triangles (no-op if already below)."""
    n = gbc.tri_count(obj.data)
    if n <= target_tris or n == 0:
        return n
    mod = obj.modifiers.new("gb_decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.01, target_tris / n)
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.remove(mod)
    obj.data = new
    new.name = old.name
    bpy.data.meshes.remove(old)
    new.shade_smooth()
    return gbc.tri_count(new)


def apply_modifier(obj, mod):
    """Apply one modifier by evaluating the object (no operators)."""
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.remove(mod)
    obj.data = new
    new.name = old.name
    if old.users == 0:
        bpy.data.meshes.remove(old)
    return obj


def split_pieces(me, face_piece):
    """Split edges between faces of different piece ids so every piece becomes a loose island."""
    face_piece = np.asarray(face_piece)
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    cut = []
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) == 2 and face_piece[lf[0].index] != face_piece[lf[1].index]:
            cut.append(e)
    if cut:
        bmesh.ops.split_edges(bm, edges=cut)
    bm.to_mesh(me)
    bm.free()
    me.update()
    return len(cut)


def join_parts(name, parts):
    """Merge parts into one mesh datablock.

    parts: list of dicts {verts, faces, [slot], [attrs: {name: (kind, per-vertex array)}]}.
    Returns (mesh, per-face slot array, {attr: per-vertex array})."""
    verts, faces, slots, attrs = [], [], [], {}
    off = 0
    names = set()
    for p in parts:
        names.update(p.get("attrs", {}).keys())
    for p in parts:
        v = np.asarray(p["verts"], dtype=float)
        verts.append(v)
        for f in p["faces"]:
            faces.append([int(i) + off for i in f])
        slots += [p.get("slot", 0)] * len(p["faces"])
        for nme in names:
            kind, default = ("INT", 0) if nme.startswith(("gb_rigid", "gb_piece", "gb_part")) else ("FLOAT", 0.0)
            vals = p.get("attrs", {}).get(nme)
            if vals is None:
                vals = (kind, np.full(len(v), -1 if nme == "gb_rigid_bone" else default))
            attrs.setdefault(nme, (vals[0], []))[1].append(np.asarray(vals[1]))
        off += len(v)
    V = np.vstack(verts) if verts else np.zeros((0, 3))
    me = gbc.mesh_from_arrays(name, V, faces)
    out_attrs = {k: (kind, np.concatenate(arrs)) for k, (kind, arrs) in attrs.items()}
    return me, np.asarray(slots, dtype=np.int32), out_attrs


def mesh_to_part(me, slot=0, attrs=None):
    """Convert a mesh datablock into a join_parts() part dict (removes nothing)."""
    v = gbc.get_verts(me)
    f = [list(p.vertices) for p in me.polygons]
    return {"verts": v, "faces": f, "slot": slot, "attrs": attrs or {}}


def smart_uv(obj, margin=0.004, angle_deg=66.0):
    """Quick atlas UV in the map named ``atlas`` (Smart UV Project; B1/B2 replace with planned seams)."""
    me = obj.data
    if "atlas" not in me.uv_layers:
        me.uv_layers.new(name="atlas")
    me.uv_layers.active = me.uv_layers["atlas"]
    vl = bpy.context.view_layer
    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    vl.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(angle_deg), island_margin=margin)
    bpy.ops.object.mode_set(mode='OBJECT')
    obj.select_set(False)
