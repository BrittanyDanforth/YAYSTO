"""Procedural human head anatomy for the gore head (Blender 5.x).

Builds every anatomical layer of the head from code: skin, soft tissue
(muscle), skull, mandible, brain, eyes, teeth, gums, tongue and the mouth
lining.  No downloaded data of any kind is used.

Technique
---------
Every organic shape is a signed distance function (SDF) written in numpy
(negative inside), in the spirit of Inigo Quilez' SDF modelling: ellipsoids,
tapered capsules and swept tubes combined with C2 smooth unions/subtractions.
The face itself is a frontal height field (profile splines + bumps) carved
out of a head volume.  An SDF is polygonised with a sparse two-level grid and
a vectorised *surface nets* mesher, cleaned with Blender's voxel remesher,
and every vertex is then Newton-projected back onto the exact iso-surface,
so features smaller than the voxel size (lid margins, lip borders, ear folds,
brain sulci) survive.  Inner layers are derived from the skin SDF by offsets
and clamps, which makes the nesting (skin > muscle > skull > brain) hold by
construction; ``check_report`` verifies it on the meshes.

Space: metres, Z up, the face looks toward -Y, origin between the ear canals
(see CONTRACT.md).  Character's left is +X.

Notes for the other modules
---------------------------
* Eyes: object origin = eyeball centre, local -Y = gaze, sclera radius
  EYE_R = 0.012.  The cornea bulges ~1.3 mm (apex at local y = -0.0133); the
  limbus (iris edge) is at |local xz| = LIMBUS_R = 0.0059, i.e. 29.4 deg from
  -Y.  Iris/pupil are for the shader to paint from object coordinates.
* GH_MouthCavity is a separate object (the lining of the oral cavity).  It
  shares its border vertices with GH_Skin just inside the lips, so GH_Skin is
  a manifold with one boundary loop there; skin + lining together are closed.
* Point attributes: GH_Skin ``gh_lip`` (0..1 vermilion mask), GH_Brain
  ``gh_sulcus`` (0..1, 1 deep in a sulcus), GH_Teeth_* ``tooth_id`` (int, FDI
  number; each tooth is its own closed island).
* GH_Muscle is the whole soft-tissue volume: its outer surface is 3.5 mm
  under the skin, its inner surface ~1.2 mm off bone, eyes, gums and jaw.
  Where there is no bone (neck, lips, nose, cheeks, orbits) it is solid.
* Teeth roots sit inside GH_Gums; the gums' root side is embedded in the
  tissue behind the mouth lining.  Those are the only intended overlaps.

Run ``python3 anatomy.py`` for test renders and an interpenetration report.
"""
import math
import os
import sys
import time

import numpy as np

import bpy
import bmesh  # noqa: E402  (bmesh is only importable once bpy is loaded)
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_common as ghc  # noqa: E402

COLLECTION = "GoreHead"

# ---------------------------------------------------------------------------
# Landmarks (metres).  Mirrored features are given for the left (+X) side.
# ---------------------------------------------------------------------------
EYE_C = np.array([0.032, -0.070, 0.022])
EYE_R = 0.012

# Design values; build_anatomy() replaces them with values measured on the meshes.
ANATOMY_LANDMARKS = {
    "vertex_top": (0.0, 0.005, 0.125), "back_of_head": (0.0, 0.100, 0.030),
    "glabella": (0.0, -0.093, 0.035), "nasion": (0.0, -0.089, 0.023),
    "nose_tip": (0.0, -0.111, -0.014), "subnasale": (0.0, -0.097, -0.031),
    "mouth_center": (0.0, -0.094, -0.055), "lip_gap": 0.0069,
    "mouth_corner_L": (0.0238, -0.0848, -0.0552), "mouth_width": 0.0476,
    "pogonion": (0.0, -0.094, -0.092), "chin_bottom": (0.0, -0.080, -0.103),
    "eye_L": (0.032, -0.070, 0.022), "eye_R": (-0.032, -0.070, 0.022), "eye_radius": 0.012,
    "ear_canal_L": (0.072, 0.0, 0.0), "ear_canal_R": (-0.072, 0.0, 0.0),
    "head_half_width": 0.074, "neck_radius": 0.055, "neck_center_y": 0.015,
    "neck_cut_z": -0.20, "gonion_L": (0.050, -0.004, -0.075),
    "upper_incisal_edge_z": -0.0544, "lower_incisal_edge_z": -0.0569,
}


# ---------------------------------------------------------------------------
# SDF toolkit.  Points are passed as three flat float64 arrays (x, y, z).
# ---------------------------------------------------------------------------
def smin(a, b, k):
    """Cubic smooth minimum (smooth union), C2 continuous, blend radius k."""
    if k <= 0.0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * h * k * (1.0 / 6.0)


def smax_k(a, b, k):
    """Smooth maximum with a per-point blend radius array k (> 0)."""
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.maximum(a, b) + h * h * h * k * (1.0 / 6.0)


def smax(a, b, k):
    """Smooth maximum (smooth intersection / subtraction with -b)."""
    return -smin(-a, -b, k)


def _local(x, y, z, c, rot=None):
    """Translate (and optionally rotate by 3x3 matrix `rot`, world->local)."""
    dx, dy, dz = x - c[0], y - c[1], z - c[2]
    if rot is None:
        return dx, dy, dz
    r = rot
    return (r[0][0] * dx + r[0][1] * dy + r[0][2] * dz,
            r[1][0] * dx + r[1][1] * dy + r[1][2] * dz,
            r[2][0] * dx + r[2][1] * dy + r[2][2] * dz)


def rot_xyz(ax=0.0, ay=0.0, az=0.0):
    """World->local rotation matrix (inverse of Euler XYZ rotation in degrees)."""
    m = Matrix.Rotation(math.radians(az), 3, 'Z') @ Matrix.Rotation(math.radians(ay), 3, 'Y') \
        @ Matrix.Rotation(math.radians(ax), 3, 'X')
    return np.array(m.transposed())


def sd_ellipsoid(x, y, z, c, r, rot=None):
    """Approximate ellipsoid distance (IQ's bound, exact on the axes)."""
    dx, dy, dz = _local(x, y, z, c, rot)
    ax_, ay_, az_ = dx / r[0], dy / r[1], dz / r[2]
    k0 = np.sqrt(ax_ * ax_ + ay_ * ay_ + az_ * az_)
    bx, by, bz = ax_ / r[0], ay_ / r[1], az_ / r[2]
    k1 = np.sqrt(bx * bx + by * by + bz * bz) + 1e-12
    return k0 * (k0 - 1.0) / k1


def sd_sphere(x, y, z, c, r):
    """Sphere distance."""
    dx, dy, dz = x - c[0], y - c[1], z - c[2]
    return np.sqrt(dx * dx + dy * dy + dz * dz) - r


def seg_param(x, y, z, a, b):
    """Clamped parameter h of the closest point on segment ab, and the distance."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ba = b - a
    dx, dy, dz = x - a[0], y - a[1], z - a[2]
    h = np.clip((dx * ba[0] + dy * ba[1] + dz * ba[2]) / float(ba @ ba), 0.0, 1.0)
    ex, ey, ez = dx - ba[0] * h, dy - ba[1] * h, dz - ba[2] * h
    return h, np.sqrt(ex * ex + ey * ey + ez * ez)


def sd_capsule(x, y, z, a, b, ra, rb=None):
    """Capsule from a to b with radius linearly tapering from ra to rb."""
    rb = ra if rb is None else rb
    h, d = seg_param(x, y, z, a, b)
    return d - (ra + (rb - ra) * h)


def sd_box(x, y, z, c, half, rot=None, round_=0.0):
    """Rounded box (half extents), optionally rotated."""
    dx, dy, dz = _local(x, y, z, c, rot)
    qx = np.abs(dx) - half[0] + round_
    qy = np.abs(dy) - half[1] + round_
    qz = np.abs(dz) - half[2] + round_
    mx, my, mz = np.maximum(qx, 0), np.maximum(qy, 0), np.maximum(qz, 0)
    outside = np.sqrt(mx * mx + my * my + mz * mz)
    inside = np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0.0)
    return outside + inside - round_


def sd_polyline(x, y, z, pts, radii, want_t=False):
    """Tube swept along a polyline, radius interpolated per vertex.

    Returns (distance, t) where t in [0, 1] is the arc parameter of the
    closest point (only computed when want_t is set, otherwise None).
    """
    pts = np.asarray(pts, float)
    radii = np.asarray(radii, float)
    seg_len = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)]) / max(seg_len.sum(), 1e-9)
    best = np.full(x.shape, 1e9)
    best_t = np.zeros(x.shape) if want_t else None
    for i in range(len(pts) - 1):
        h, d = seg_param(x, y, z, pts[i], pts[i + 1])
        d = d - (radii[i] + (radii[i + 1] - radii[i]) * h)
        if want_t:
            m = d < best
            best_t = np.where(m, cum[i] + (cum[i + 1] - cum[i]) * h, best_t)
        best = np.minimum(best, d)
    return best, best_t


def catmull(points, n=8):
    """Densify a list of control points with a centripetal-ish Catmull-Rom spline."""
    p = np.asarray(points, float)
    p = np.vstack([2 * p[0] - p[1], p, 2 * p[-1] - p[-2]])
    out = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(p[-2])
    return np.array(out)


def smoothstep(e0, e1, x):
    """Hermite step from 0 at e0 to 1 at e1 (e0 > e1 gives a falling step)."""
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Region:
    """Axis-aligned box used to evaluate a feature only where it matters."""

    def __init__(self, lo, hi):
        self.lo = np.asarray(lo, float)
        self.hi = np.asarray(hi, float)

    def mask(self, x, y, z):
        """Boolean array: which points lie inside the box."""
        return ((x >= self.lo[0]) & (x <= self.hi[0]) & (y >= self.lo[1]) & (y <= self.hi[1])
                & (z >= self.lo[2]) & (z <= self.hi[2]))


def apply_local(d, x, y, z, region, fn):
    """d = fn(d_sub, x_sub, y_sub, z_sub) evaluated only inside `region`."""
    m = region.mask(x, y, z)
    if m.any():
        idx = np.nonzero(m)[0]
        d = d.copy()
        d[idx] = fn(d[idx], x[idx], y[idx], z[idx])
    return d


# ---------------------------------------------------------------------------
# Mesher: sparse grid -> surface nets -> voxel remesh -> Newton projection
# ---------------------------------------------------------------------------
_CORNERS = np.array([[i, j, k] for i in (0, 1) for j in (0, 1) for k in (0, 1)])
_EDGES = [(a, b) for a in range(8) for b in range(a + 1, 8)
          if np.abs(_CORNERS[a] - _CORNERS[b]).sum() == 1]


def eval_points(fn, pts, chunk=400000):
    """Evaluate an SDF on an (N,3) array in chunks."""
    out = np.empty(len(pts))
    for s in range(0, len(pts), chunk):
        p = pts[s:s + chunk]
        out[s:s + chunk] = fn(p[:, 0].copy(), p[:, 1].copy(), p[:, 2].copy())
    return out


def sample_grid(fn, lo, hi, h, ratio=3):
    """Sample fn on a grid of spacing h, only near the surface.

    A coarse grid (spacing ratio*h) finds the cells the surface passes near;
    fine samples are evaluated only there, elsewhere the coarse sign is kept.
    Returns (F, origin).
    """
    H = h * ratio
    lo = np.asarray(lo, float)
    hi = np.asarray(hi, float)
    nc = np.ceil((hi - lo) / H).astype(int) + 1
    axes_c = [lo[i] + H * np.arange(nc[i]) for i in range(3)]
    gx, gy, gz = np.meshgrid(*axes_c, indexing='ij')
    Fc = eval_points(fn, np.stack([gx.ravel(), gy.ravel(), gz.ravel()], 1)).reshape(nc)
    # coarse cells close to the surface (dilated by one cell)
    a = np.abs(Fc)
    cmin = a[:-1, :-1, :-1]
    for (i, j, k) in _CORNERS[1:]:
        cmin = np.minimum(cmin, a[i:i + nc[0] - 1, j:j + nc[1] - 1, k:k + nc[2] - 1])
    # a fine sample outside these cells keeps the sign of its nearest coarse
    # sample, which is correct as long as |f| there exceeds half a cell diagonal
    dil = cmin < 1.1 * H
    nf = (nc - 1) * ratio + 1
    ci = [np.minimum(np.arange(nf[i]) // ratio, nc[i] - 2) for i in range(3)]
    ni = [np.minimum((np.arange(nf[i]) + ratio // 2) // ratio, nc[i] - 1) for i in range(3)]
    F = Fc[np.ix_(ni[0], ni[1], ni[2])].astype(np.float32)
    mask = dil[np.ix_(ci[0], ci[1], ci[2])]
    ii, jj, kk = np.nonzero(mask)
    pts = np.stack([lo[0] + h * ii, lo[1] + h * jj, lo[2] + h * kk], 1)
    F[ii, jj, kk] = eval_points(fn, pts)
    # force 'outside' on the border so every surface is closed inside the box
    for ax in range(3):
        sl = [slice(None)] * 3
        for end in (0, -1):
            sl[ax] = end
            F[tuple(sl)] = np.maximum(F[tuple(sl)], 0.5 * h)
    return F, lo


def surface_nets(F, origin, h):
    """Naive surface nets on a dense grid (inside < 0). Returns (verts, quads)."""
    inside = F < 0
    n = np.array(F.shape)
    m = n - 1
    cnt = np.zeros(m, np.uint8)
    for (i, j, k) in _CORNERS:
        cnt += inside[i:i + m[0], j:j + m[1], k:k + m[2]]
    active = (cnt > 0) & (cnt < 8)
    del cnt
    ci = np.argwhere(active)
    acc = np.zeros((len(ci), 3))
    num = np.zeros(len(ci))
    for a, b in _EDGES:
        ca, cb = _CORNERS[a], _CORNERS[b]
        fa = F[ci[:, 0] + ca[0], ci[:, 1] + ca[1], ci[:, 2] + ca[2]].astype(np.float64)
        fb = F[ci[:, 0] + cb[0], ci[:, 1] + cb[1], ci[:, 2] + cb[2]].astype(np.float64)
        cross = (fa < 0) != (fb < 0)
        t = np.where(cross, fa / np.where(cross, fa - fb, 1.0), 0.0)
        acc += np.where(cross[:, None], ca[None, :] + t[:, None] * (cb - ca)[None, :], 0.0)
        num += cross
    verts = origin[None, :] + h * (ci + acc / np.maximum(num, 1)[:, None])
    vid = np.full(m, -1, np.int64)
    vid[active] = np.arange(len(ci))
    quads = []
    # edges along axis `ax`; the four cells around each sign-changing edge form a quad
    for ax in range(3):
        a1, a2 = (ax + 1) % 3, (ax + 2) % 3
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, n[ax] - 1)
        sl1[ax] = slice(1, n[ax])
        for s in (sl0, sl1):
            s[a1] = slice(1, n[a1] - 1)
            s[a2] = slice(1, n[a2] - 1)
        e0 = inside[tuple(sl0)]
        e1 = inside[tuple(sl1)]
        chg = e0 != e1
        idx = np.nonzero(chg)
        flip = e0[idx]
        base = [idx[0].copy(), idx[1].copy(), idx[2].copy()]
        base[a1] += 1
        base[a2] += 1

        def cell(d1, d2):
            c = [base[0].copy(), base[1].copy(), base[2].copy()]
            c[a1] -= d1
            c[a2] -= d2
            return vid[c[0], c[1], c[2]]
        q = np.stack([cell(1, 1), cell(0, 1), cell(0, 0), cell(1, 0)], 1)
        q[~flip] = q[~flip][:, ::-1]
        quads.append(q)
    quads = np.concatenate(quads)
    quads = quads[(quads >= 0).all(1)]
    return verts, quads


def mesh_from_arrays(name, verts, faces):
    """Create a mesh datablock from vertex (N,3) and quad/tri (M,k) arrays."""
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(verts))
    me.vertices.foreach_set('co', np.asarray(verts, np.float32).ravel())
    k = faces.shape[1]
    me.loops.add(len(faces) * k)
    me.loops.foreach_set('vertex_index', faces.astype(np.int32).ravel())
    me.polygons.add(len(faces))
    me.polygons.foreach_set('loop_start', np.arange(0, len(faces) * k, k, dtype=np.int32))
    me.update(calc_edges=True)
    return me


def get_verts(me):
    """Vertex positions of a mesh as an (N, 3) float64 array."""
    v = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', v)
    return v.reshape(-1, 3).astype(np.float64)


def set_verts(me, v):
    """Write (N, 3) vertex positions back into a mesh."""
    me.vertices.foreach_set('co', np.asarray(v, np.float32).ravel())
    me.update()


def mesh_arrays(me):
    """(verts (N,3) float64, faces (M,k) int) of a mesh whose faces all have k corners."""
    v = get_verts(me)
    tot = np.empty(len(me.polygons), np.int32)
    me.polygons.foreach_get('loop_total', tot)
    k = int(tot[0]) if len(tot) else 4
    assert (tot == k).all(), "mixed face sizes"
    f = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get('vertex_index', f)
    return v, f.reshape(-1, k)


def project_to_surface(fn, v, h, iters=3):
    """Newton-project points onto the zero level set of fn (forward differences)."""
    e = 0.2 * h
    offs = np.array([[e, 0, 0], [0, e, 0], [0, 0, e]])
    for _ in range(iters):
        allp = np.concatenate([v] + [v + o for o in offs])
        f = eval_points(fn, allp).reshape(4, -1)
        g = np.stack([f[1] - f[0], f[2] - f[0], f[3] - f[0]], 1) / e
        g2 = (g * g).sum(1) + 1e-12
        step = (f[0] / g2)[:, None] * g
        # clamp steps so a bad gradient can never throw a vertex far away
        sl = np.linalg.norm(step, axis=1)
        step *= np.minimum(1.0, 0.6 * h / np.maximum(sl, 1e-12))[:, None]
        v = v - step
    return v


def remesh_object(obj, voxel):
    """Apply a voxel remesh to obj in place (no operators)."""
    mod = obj.modifiers.new("remesh", 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = voxel
    mod.adaptivity = 0.0
    mod.use_smooth_shade = True
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(obj.evaluated_get(dg))
    old = obj.data
    obj.modifiers.remove(mod)
    obj.data = new
    bpy.data.meshes.remove(old)
    return obj


def vertex_neighbors(me):
    """Return (edges (E,2) array) for Laplacian operations."""
    e = np.empty(len(me.edges) * 2, np.int32)
    me.edges.foreach_get('vertices', e)
    return e.reshape(-1, 2)


def laplacian(v, edges, n=None):
    """Umbrella average of neighbours for every vertex."""
    n = len(v) if n is None else n
    acc = np.zeros((n, 3))
    cnt = np.zeros(n)
    np.add.at(acc, edges[:, 0], v[edges[:, 1]])
    np.add.at(acc, edges[:, 1], v[edges[:, 0]])
    np.add.at(cnt, edges[:, 0], 1)
    np.add.at(cnt, edges[:, 1], 1)
    return acc / np.maximum(cnt, 1)[:, None]


def remove_small_islands(me, keep_frac=0.02):
    """Delete connected pieces with fewer than keep_frac of the largest piece's vertices."""
    v, f = mesh_arrays(me)
    # connected components by repeated min-label propagation over face edges
    e = np.concatenate([f[:, [i, (i + 1) % f.shape[1]]] for i in range(f.shape[1])])
    lab = np.arange(len(v))
    for _ in range(200):
        a, b = lab[e[:, 0]], lab[e[:, 1]]
        m = np.minimum(a, b)
        new = lab.copy()
        np.minimum.at(new, e[:, 0], m)
        np.minimum.at(new, e[:, 1], m)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    ids, counts = np.unique(lab, return_counts=True)
    keep_ids = ids[counts >= keep_frac * counts.max()]
    keep_v = np.isin(lab, keep_ids)
    if keep_v.all():
        return me, 0
    keep_f = keep_v[f].all(1)
    used = np.unique(f[keep_f])
    remap = np.full(len(v), -1, np.int64)
    remap[used] = np.arange(len(used))
    new_me = mesh_from_arrays(me.name, v[used], remap[f[keep_f]])
    return new_me, int((~keep_v).sum())


def mesh_sdf(name, fn, lo, hi, h, voxel=None, project=2, relax=0, collection=None, clean=True):
    """Polygonise an SDF into a new smooth-shaded object.

    h: grid spacing, voxel: remesh voxel size (None = keep surface nets mesh),
    project: Newton iterations back onto the exact surface,
    relax: tangential relaxation passes (each followed by reprojection).
    """
    t0 = time.time()
    F, origin = sample_grid(fn, lo, hi, h)
    verts, quads = surface_nets(F, origin, h)
    del F
    me = mesh_from_arrays(name, verts, quads)
    obj = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(obj)
    if voxel:
        remesh_object(obj, voxel)
    if clean:
        new_me, removed = remove_small_islands(obj.data)
        if removed:
            old_me = obj.data
            obj.data = new_me
            bpy.data.meshes.remove(old_me)
            new_me.name = name
    me = obj.data
    v = get_verts(me)
    if project:
        v = project_to_surface(fn, v, voxel or h, project)
    if relax:
        edges = vertex_neighbors(me)
        for _ in range(relax):
            v = 0.5 * v + 0.5 * laplacian(v, edges)
            v = project_to_surface(fn, v, voxel or h, 1)
    set_verts(me, v)
    me.shade_smooth()
    obj["gh_build_seconds"] = round(time.time() - t0, 2)
    return obj


def ellipse2(a, b, ra, rb):
    """2D ellipse distance approximation (IQ bound) for arrays a, b."""
    k0 = np.sqrt((a / ra) ** 2 + (b / rb) ** 2)
    k1 = np.sqrt((a / ra ** 2) ** 2 + (b / rb ** 2) ** 2) + 1e-12
    return k0 * (k0 - 1.0) / k1


def box2(a, b, ha, hb, rnd=0.0):
    """2D rounded box distance."""
    qa = np.abs(a) - ha + rnd
    qb = np.abs(b) - hb + rnd
    return (np.minimum(np.maximum(qa, qb), 0.0)
            + np.sqrt(np.maximum(qa, 0) ** 2 + np.maximum(qb, 0) ** 2) - rnd)


def extrude(d2, dz, half, rnd=0.0):
    """Extrude a 2D distance d2 along an axis with half height `half` and rounding."""
    wx = d2 + rnd
    wy = np.abs(dz) - half + rnd
    return (np.minimum(np.maximum(wx, wy), 0.0)
            + np.sqrt(np.maximum(wx, 0) ** 2 + np.maximum(wy, 0) ** 2) - rnd)


class Curve1D:
    """C2 natural cubic spline through a (key, value) table, clamped at the ends."""

    def __init__(self, table):
        t = np.array(sorted(table), float)
        x, y = t[:, 0], t[:, 1]
        n = len(x)
        h = np.diff(x)
        A = np.zeros((n, n))
        r = np.zeros(n)
        A[0, 0] = A[-1, -1] = 1.0
        for i in range(1, n - 1):
            A[i, i - 1], A[i, i], A[i, i + 1] = h[i - 1], 2 * (h[i - 1] + h[i]), h[i]
            r[i] = 6 * ((y[i + 1] - y[i]) / h[i] - (y[i] - y[i - 1]) / h[i - 1])
        self.x, self.y, self.h, self.M = x, y, h, np.linalg.solve(A, r)

    def __call__(self, q):
        x = self.x
        q = np.clip(q, x[0], x[-1])
        i = np.clip(np.searchsorted(x, q) - 1, 0, len(x) - 2)
        h = self.h[i]
        a = (x[i + 1] - q) / h
        b = 1.0 - a
        return (a * self.y[i] + b * self.y[i + 1]
                + ((a ** 3 - a) * self.M[i] + (b ** 3 - b) * self.M[i + 1]) * h * h / 6.0)


def dist2_polyline(a, b, pts):
    """Unsigned 2D distance from (a, b) to a polyline."""
    best = np.full(a.shape, 1e9)
    for (a0, b0), (a1, b1) in zip(pts[:-1], pts[1:]):
        da, db = a1 - a0, b1 - b0
        h = np.clip(((a - a0) * da + (b - b0) * db) / (da * da + db * db), 0, 1)
        ea, eb = a - a0 - da * h, b - b0 - db * h
        best = np.minimum(best, np.sqrt(ea * ea + eb * eb))
    return best



# ---------------------------------------------------------------------------
# Skin: a "carved block".  A head volume (cranium, face block with a jaw floor,
# neck) is intersected with a frontal height field y = Y(x, z) that carries
# the facial profile, then 3D features (eyelids, nose tip and alae, lips,
# ears) are blended on and openings (eyes, nostrils, mouth) carved out.
# ---------------------------------------------------------------------------
# midline profile of the face without nose and lips: z -> y
FACE_PROFILE = Curve1D([
    (0.130, -0.020), (0.118, -0.050), (0.106, -0.0655), (0.094, -0.0760), (0.082, -0.0835),
    (0.070, -0.0880), (0.058, -0.0908), (0.047, -0.0925), (0.039, -0.0930), (0.032, -0.0919),
    (0.025, -0.0893), (0.018, -0.0874), (0.008, -0.0868), (-0.004, -0.0875), (-0.014, -0.0890),
    (-0.026, -0.0925), (-0.034, -0.0952), (-0.043, -0.0960), (-0.052, -0.0950), (-0.062, -0.0938),
    (-0.069, -0.0920), (-0.075, -0.0895), (-0.081, -0.0902), (-0.088, -0.0930),
    (-0.095, -0.0915), (-0.101, -0.0868), (-0.107, -0.0775), (-0.114, -0.0640),
    (-0.124, -0.080), (-0.136, -0.150), (-0.156, -0.260)])
# how fast the face recedes sideways: Y += C2 x^2 + C4 x^4
FACE_C2 = Curve1D([(0.13, 7.5), (0.09, 6.5), (0.06, 5.0), (0.04, 4.2), (0.02, 4.4), (0.00, 5.0),
                   (-0.02, 6.5), (-0.04, 9.0), (-0.055, 10.5), (-0.068, 11.5), (-0.081, 14.0),
                   (-0.096, 17.0), (-0.126, 20.0)])
FACE_C4 = Curve1D([(0.13, 0.0), (0.09, 300.0), (0.06, 800.0), (0.04, 1250.0), (0.02, 1700.0),
                   (0.0, 1900.0), (-0.02, 1800.0), (-0.05, 1700.0), (-0.076, 1900.0),
                   (-0.096, 2500.0), (-0.126, 3000.0)])
# nose ridge: protrusion over the base profile, half width, cross-section exponent
NOSE_PROJ = Curve1D([(0.030, 0.0), (0.022, 0.0012), (0.014, 0.0050), (0.006, 0.0092),
                     (-0.002, 0.0138), (-0.008, 0.0175), (-0.012, 0.0192), (-0.015, 0.0190),
                     (-0.019, 0.0162), (-0.023, 0.0108), (-0.028, 0.0040), (-0.034, 0.0)])
NOSE_W = Curve1D([(0.030, 0.0085), (0.014, 0.0095), (0.000, 0.0110), (-0.011, 0.0125),
                  (-0.020, 0.0140), (-0.034, 0.0140)])
NOSE_P = Curve1D([(0.030, 1.5), (0.012, 1.2), (0.000, 1.0), (-0.013, 0.85), (-0.034, 0.85)])
# brow ridge height and the height of its crest, along x
BROW_H = Curve1D([(0.0, 0.0010), (0.012, 0.0026), (0.025, 0.0044), (0.040, 0.0042),
                  (0.050, 0.0020), (0.060, 0.0)])
BROW_Z = Curve1D([(0.0, 0.036), (0.030, 0.0390), (0.050, 0.0355), (0.060, 0.034)])
# face block half width and the jaw's lower border
FACE_W = Curve1D([(0.115, 0.045), (0.09, 0.058), (0.07, 0.0625), (0.05, 0.0635), (0.03, 0.0630),
                  (0.015, 0.0635), (0.0, 0.0640), (-0.015, 0.0632), (-0.03, 0.0615),
                  (-0.05, 0.0590), (-0.068, 0.0545), (-0.082, 0.0470), (-0.096, 0.0370),
                  (-0.111, 0.028)])
JAW_Z = Curve1D([(-0.095, -0.1045), (-0.075, -0.1040), (-0.06, -0.1015), (-0.045, -0.0970),
                 (-0.03, -0.0910), (-0.015, -0.0835), (0.0, -0.0760), (0.012, -0.0690)])
NASOLABIAL = [(0.0185, -0.0225), (0.0235, -0.0340), (0.0280, -0.0460), (0.0310, -0.0575),
              (0.0322, -0.0680)]
# alar rim: a tube wrapping the nostril from the tip round to the nostril sill
ALA_PATH = [(0.0065, -0.1008, -0.0225), (0.0105, -0.0990, -0.0200), (0.0132, -0.0955, -0.0195),
            (0.0142, -0.0918, -0.0215), (0.0132, -0.0893, -0.0250), (0.0098, -0.0905, -0.0278)]
ALA_R = [0.0024, 0.0038, 0.0046, 0.0044, 0.0034, 0.0024]


def face_height(ax, z, nose=True):
    """Frontal height field Y(x, z): the face surface is y = Y (face looks to -y)."""
    x2 = ax * ax
    Y = FACE_PROFILE(z) + FACE_C2(z) * x2 + FACE_C4(z) * x2 * x2
    # nose ridge
    if nose:
        u = np.clip(ax / NOSE_W(z), 0.0, 1.0)
        Y = Y - NOSE_PROJ(z) * (1.0 - u * u) ** NOSE_P(z)
    # brow ridge
    Y = Y - BROW_H(ax) * np.exp(-((z - BROW_Z(ax)) / 0.0080) ** 2)
    # orbital hollow, deepest under the brow and beside the nose
    ex, ez = (ax - 0.0300) / 0.0170, (z - 0.0255) / 0.0120
    Y = Y + 0.0062 * np.exp(-(ex * ex + ez * ez) ** 1.2)
    # malar fullness under the eye and cheek lateral of the nasolabial fold
    cx, cz = (ax - 0.0420) / 0.0150, (z + 0.0010) / 0.0120
    Y = Y - 0.0040 * np.exp(-(cx * cx + cz * cz))
    # soft hollow under the cheekbone, in front of the masseter
    cx, cz = (ax - 0.0450) / 0.0110, (z + 0.0380) / 0.0150
    Y = Y + 0.0016 * np.exp(-(cx * cx + cz * cz))
    cx, cz = (ax - 0.0385) / 0.0120, (z + 0.0330) / 0.0190
    Y = Y - 0.0028 * np.exp(-(cx * cx + cz * cz))
    # soft nasolabial fold
    g = dist2_polyline(ax, z, NASOLABIAL)
    Y = Y + 0.0009 * np.exp(-(g / 0.0035) ** 2)
    return Y


class _Grid2D:
    """Bilinear lookup table of a 2D function and its gradient on a regular grid."""

    def __init__(self, fn, lo, hi, step):
        self.lo = np.asarray(lo, float)
        self.step = step
        self.n = (np.ceil((np.asarray(hi) - self.lo) / step)).astype(int) + 1
        a = self.lo[0] + step * np.arange(self.n[0])
        b = self.lo[1] + step * np.arange(self.n[1])
        aa, bb = np.meshgrid(a, b, indexing='ij')
        self.v = fn(aa, bb)
        self.ga, self.gb = np.gradient(self.v, step, step)

    def __call__(self, a, b):
        fa = np.clip((a - self.lo[0]) / self.step, 0, self.n[0] - 1.001)
        fb = np.clip((b - self.lo[1]) / self.step, 0, self.n[1] - 1.001)
        i, j = fa.astype(np.int64), fb.astype(np.int64)
        u, w = fa - i, fb - j
        out = []
        for g in (self.v, self.ga, self.gb):
            out.append((g[i, j] * (1 - u) + g[i + 1, j] * u) * (1 - w)
                       + (g[i, j + 1] * (1 - u) + g[i + 1, j + 1] * u) * w)
        return out


_FACE_GRID = None


def face_sdf(ax, y, z):
    """Distance-like function of the half space behind the face height field."""
    global _FACE_GRID
    if _FACE_GRID is None:
        _FACE_GRID = _Grid2D(face_height, (0.0, -0.215), (0.11, 0.145), 0.00025)
    Y, gx, gz = _FACE_GRID(ax, z)
    return (Y - y) / np.sqrt(1.0 + gx * gx + gz * gz)


def _neck(ax, y, z):
    """Neck column leaning forward, widening toward the shoulders; open at both ends."""
    tz = np.clip((-0.060 - z) / 0.14, 0.0, 1.5)
    # the throat sits well forward (larynx ~5 cm behind the chin), the nape
    # curves in under the occiput
    yc = 0.0060 + 0.0045 * tz
    top = smoothstep(-0.105, -0.045, z)          # wider under the skull (mastoids, SCM origin)
    base = smoothstep(-0.165, -0.205, z)         # trapezius / shoulders begin
    a = 0.0515 + 0.0040 * tz * tz + 0.0060 * top + 0.0100 * base
    b = 0.0560 + 0.0040 * tz * tz + 0.0015 * top
    return ellipse2(ax, y - yc, a, b)


def head_volume(ax, y, z):
    """Cranium, face block with the jaw floor, cheekbones, neck and its muscles."""
    d = sd_ellipsoid(ax, y, z, (0.0, 0.001, 0.025), (0.0740, 0.0990, 0.1000))
    # face block: rounded box in plan, width varying with height, jaw floor below
    blk = box2(ax, y + 0.055, FACE_W(z), 0.064, 0.030)
    blk = smax(blk, z - 0.115, 0.03)
    blk = smax(blk, JAW_Z(y) - z, 0.012)
    d = smin(d, blk, 0.020)
    # cheekbone (zygomatic body) and arch running back to the ear
    zyg = sd_ellipsoid(ax, y, z, (0.0525, -0.0555, 0.0025), (0.0130, 0.0200, 0.0120),
                       rot=rot_xyz(0, 0, -38))
    arch = sd_capsule(ax, y, z, (0.0585, -0.0440, 0.0030), (0.0625, -0.0150, 0.0020), 0.0060, 0.0052)
    d = smin(d, smin(zyg, arch, 0.01), 0.012)
    # temple and buccal hollows
    d = smax(d, -sd_ellipsoid(ax, y, z, (0.0720, -0.0480, 0.0400), (0.0090, 0.0220, 0.0200)), 0.016)
    d = smax(d, -sd_ellipsoid(ax, y, z, (0.0660, -0.0440, -0.0380), (0.0080, 0.0180, 0.0150)), 0.020)
    # neck (capped just under the skull so it only shows below the jaw)
    neck = smax(_neck(ax, y, z), z + 0.030, 0.02)
    # (a tighter blend under the jaw: the jaw's lower border casts a shadow)
    d = smin(d, neck, 0.024)
    d = smin(d, sd_ellipsoid(ax, y, z, (0.0500, 0.0180, -0.0400), (0.0120, 0.0220, 0.0260)), 0.020)
    # sternocleidomastoid: mastoid -> sternum, standing out in front of the neck
    scm = sd_capsule(ax, y, z, (0.052, 0.012, -0.034), (0.014, -0.044, -0.198), 0.0086, 0.0072)
    d = smin(d, scm, 0.010)
    # laryngeal prominence (Adam's apple)
    d = smin(d, sd_ellipsoid(ax, y, z, (0.0, -0.0520, -0.1330), (0.0085, 0.0065, 0.0110)), 0.008)
    return d


# Eye opening, in angles around the eyeball centre: u = horizontal angle
# (positive = lateral), v = elevation.  M = medial canthus, L = lateral canthus.
# The upper lid covers the top 1.5-2 mm of the iris, the lower lid touches
# its bottom edge; the outer corner sits ~2-3 mm higher than the inner one.
LID_UM, LID_VM = -1.22, -0.05
LID_UL, LID_VL = 1.18, 0.14
LID_UP, LID_LO = 0.335, 0.465        # lid arc heights (rad) above/below the canthal line
LID_R = 0.0145                        # outer radius of the eyelid shell (~2 mm thick lids)
CORNEA_R = 0.0075                     # cornea sphere radius
CORNEA_OFF = 0.00582                  # cornea sphere centre, in front of eye centre
EYE_GAP = 0.0005                      # clearance between eyeball and lids

# Ear frame: origin near the concha, u = backward along the ear, v = up, w = out
EAR_O = np.array([0.0725, 0.0015, 0.0010])


def _ear_frame(protrude=24.0, tilt=12.0):
    ph, ta = math.radians(protrude), math.radians(tilt)
    u = np.array([math.sin(ph), math.cos(ph), 0.0])
    v0 = np.array([0.0, math.sin(ta), math.cos(ta)])
    v = v0 - (v0 @ u) * u
    v /= np.linalg.norm(v)
    w = np.cross(u, v)
    return u, v, w


EAR_U, EAR_V, EAR_W = _ear_frame()


def _lid_curves(u):
    """Upper and lower lid margin elevations for horizontal eye angle u."""
    t = (u - LID_UM) / (LID_UL - LID_UM)
    base = LID_VM + (LID_VL - LID_VM) * t
    st = np.sin(np.pi * np.clip(t, 0.0, 1.0))
    up = base + LID_UP * np.clip(st, 0, 1) ** 0.75 * (1.0 + 0.10 * (0.5 - t))
    lo = base - LID_LO * np.clip(st, 0, 1) ** 1.05 * (1.0 - 0.12 * (0.5 - t))
    return t, st, up, lo


def _eye_region(d, ax, y, z):
    """Eyelids, lid opening, lid crease and eyeball cavity."""
    qx, qy, qz = ax - EYE_C[0], y - EYE_C[1], z - EYE_C[2]
    r = np.sqrt(qx * qx + qy * qy + qz * qz)
    d = smin(d, r - LID_R, 0.0055)
    u = np.arctan2(qx, -qy)
    v = np.arctan2(qz, np.sqrt(qx * qx + qy * qy))
    t, st, up, lo = _lid_curves(u)
    rr = np.maximum(r, EYE_R)
    # upper lid crease ~6-8 mm above the margin, a soft hollow (sulcus)
    # between it and the brow, and the lower lid's fold
    crease_v = up + 0.50 * st ** 0.6
    g = np.exp(-(((v - crease_v) * rr) / 0.0012) ** 2) * smoothstep(0.1, 0.45, st)
    hol = np.exp(-(((v - (crease_v + 0.28)) * rr) / 0.0030) ** 2) * smoothstep(0.15, 0.5, st)
    g2 = np.exp(-(((v - (lo - 0.30 * st ** 0.7)) * rr) / 0.0013) ** 2) * smoothstep(0.2, 0.6, st)
    band = smoothstep(0.026, 0.017, r)
    d = d + (0.0012 * g + 0.0009 * hol + 0.00030 * g2) * band
    dopen = np.maximum(np.maximum(v - up, lo - v),
                       (np.abs(t - 0.5) - 0.5) * (LID_UL - LID_UM)) * rr
    cut = np.maximum(dopen, r - 0.0195)
    d = smax(d, -cut, 0.0011)
    # caruncle: the small pink mound in the inner corner of the eye
    car_c = EYE_C + np.array([-0.0118, -0.0046, -0.0002])
    d = smin(d, sd_ellipsoid(qx + EYE_C[0], qy + EYE_C[1], qz + EYE_C[2], car_c, (0.0019, 0.0015, 0.0017)), 0.0008)
    cav = np.minimum(r - (EYE_R + EYE_GAP),
                     np.sqrt(qx * qx + (qy + CORNEA_OFF) ** 2 + qz * qz) - (CORNEA_R + EYE_GAP))
    return np.maximum(d, -cav)


def _nose(d, ax, y, z):
    """Tip lobule, columella, alar rims and teardrop nostrils on top of the nose ridge."""
    tip = sd_ellipsoid(ax, y, z, (0.0, -0.1025, -0.0140), (0.0074, 0.0088, 0.0078))
    colu = sd_capsule(ax, y, z, (0.0, -0.1030, -0.0215), (0.0, -0.0962, -0.0296), 0.0030, 0.0036)
    d = smin(d, tip, 0.005)
    d = smin(d, colu, 0.004)
    pts = catmull(ALA_PATH, 4)
    rad = np.interp(np.linspace(0, 1, len(pts)), np.linspace(0, 1, len(ALA_R)), ALA_R)
    ala, _ = sd_polyline(ax, y, z, pts, rad)
    d = smin(d, ala, 0.0028)
    nos = sd_ellipsoid(ax, y, z, (0.0060, -0.0978, -0.0258), (0.0028, 0.0052, 0.0034),
                       rot=rot_xyz(10, 0, -25))
    nos = smin(nos, sd_capsule(ax, y, z, (0.0064, -0.0968, -0.0245), (0.0080, -0.0930, -0.0150),
                               0.0022, 0.0018), 0.002)
    return smax(d, -nos, 0.0018)


def _lip(ax, y, z, yc0, yc2, zc0, zc2, ra, rb, tilt, half_w=0.0255, taper=1.8, bow=0.0):
    """Lip body: an elliptic cross-section swept along the mouth arc.

    The section (radii ra along the tilted axis, rb across it) shrinks to the
    mouth corners; `bow` raises the section at the cupid's bow peaks."""
    s = np.clip(ax / half_w, 0.0, 1.0)
    f = np.sqrt(np.maximum(1.0 - s ** taper, 0.0))
    yc = yc0 + yc2 * s * s
    zc = zc0 + zc2 * s * s + bow * (np.exp(-((ax - 0.0046) / 0.0035) ** 2)
                                     - 0.6 * np.exp(-(ax / 0.0022) ** 2))
    dy, dz = y - yc, z - zc
    c, sn = math.cos(tilt), math.sin(tilt)
    a = c * dy + sn * dz
    b = -sn * dy + c * dz
    d = ellipse2(a, b, 0.0007 + ra * f, 0.0007 + rb * f)
    over = np.maximum(ax - half_w, 0.0)
    return np.where(d > 0, np.sqrt(np.maximum(d, 0) ** 2 + over ** 2), d + over)


def lips_sdf(ax, y, z):
    """Upper and lower lip bodies (vermilion), as two distance fields."""
    upper = _lip(ax, y, z, -0.0951, 0.0125, -0.0470, -0.0048, 0.0050, 0.0039,
                 math.radians(30), bow=0.0013)
    lower = _lip(ax, y, z, -0.0899, 0.0092, -0.0643, 0.0078, 0.0058, 0.0046,
                 math.radians(-32))
    return upper, lower


def _mouth(d, ax, y, z):
    """Lips, philtrum, mouth opening and labiomental fold."""
    col = sd_capsule(ax, y, z, (0.0046, -0.0945, -0.0425), (0.0036, -0.0935, -0.0315), 0.0020)
    d = smin(d, col, 0.0030)
    grv = sd_capsule(ax, y, z, (0.0, -0.0995, -0.0420), (0.0, -0.0985, -0.0330), 0.0014)
    d = smax(d, -grv, 0.0025)
    upper, lower = lips_sdf(ax, y, z)
    d = smin(d, upper, 0.0020)
    d = smin(d, lower, 0.0024)
    lm = sd_capsule(ax, y, z, (0.0, -0.0898, -0.0752), (0.011, -0.0878, -0.0738), 0.0016)
    d = smax(d, -lm, 0.0060)
    # chin (mental protuberance) as its own soft mound
    chin = sd_ellipsoid(ax, y, z, (0.0, -0.0820, -0.0895), (0.0165, 0.0110, 0.0125))
    d = smin(d, chin, 0.008)
    xs = np.clip(ax / 0.0235, 0.0, 1.5)
    zhi = -0.0516 - 0.0032 * xs ** 2
    zlo = -0.0584 + 0.0030 * xs ** 2
    slot = np.maximum(np.maximum(z - zhi, zlo - z), np.maximum(ax - 0.0235, y + 0.070))
    slot = np.maximum(slot, -0.12 - y)
    d = smax(d, -slot, 0.0025)
    # commissure pits
    pit = sd_sphere(ax, y, z, (0.0238, -0.0848, -0.0552), 0.0013)
    return smax(d, -pit, 0.0020)


def oral_void(ax, y, z):
    """The mouth cavity (vestibule + oral cavity proper), negative inside."""
    front = extrude(ellipse2(ax, y + 0.0700, 0.0265, 0.0205), z + 0.0565, 0.0170, 0.0060)
    back = sd_box(ax, y, z, (0.0, -0.0500, -0.0565), (0.0315, 0.0240, 0.0170), round_=0.0080)
    v = smin(front, back, 0.010)
    vault = sd_ellipsoid(ax, y, z, (0.0, -0.0520, -0.0440), (0.0160, 0.0280, 0.0085))
    v = smin(v, vault, 0.008)
    # keep at least 4.5 mm of tissue between the cavity and the facial surface
    return smax(v, face_sdf(ax, y, z) + 0.0045, 0.002)


def _ear_region(d, ax, y, z):
    """Blend the auricle onto the head, then hollow the concha and the ear canal
    out of the union (so the head's own surface cannot bulge into the bowl)."""
    e, hollow = _ear(ax, y, z)
    d = smin(d, e, 0.0022)
    return smax(d, -hollow, 0.0015)


def _ear(ax, y, z):
    """Auricle: helix, antihelix with crura, tragus, antitragus, lobe.

    Returns (ear solid, hollow) where hollow is the concha bowl + ear canal."""
    px, py, pz = ax - EAR_O[0], y - EAR_O[1], z - EAR_O[2]
    s = px * EAR_U[0] + py * EAR_U[1] + pz * EAR_U[2]
    t = px * EAR_V[0] + py * EAR_V[1] + pz * EAR_V[2]
    n = px * EAR_W[0] + py * EAR_W[1] + pz * EAR_W[2]
    outline = smin(ellipse2(s - 0.0115, t - 0.0045, 0.0142, 0.0262),
                   ellipse2(s - 0.0088, t + 0.0200, 0.0085, 0.0095), 0.006)
    nm = 0.0022 * np.clip(s / 0.024, 0.0, 1.2) ** 2      # plate cups outward toward the rim
    plate = np.maximum(outline + 0.0012, np.abs(n - nm) - 0.0016)
    block = sd_ellipsoid(s, t, n, (0.0065, 0.0005, -0.0045), (0.0100, 0.0125, 0.0070))
    e = smin(plate, block, 0.004)
    bowl = sd_ellipsoid(s, t, n, (0.0066, 0.0010, 0.0035), (0.0070, 0.0092, 0.0078))
    hel = catmull([(0.0085, 0.0062), (0.0030, 0.0098), (-0.0022, 0.0185), (0.0012, 0.0268),
                   (0.0082, 0.0312), (0.0168, 0.0306), (0.0232, 0.0238), (0.0264, 0.0128),
                   (0.0258, 0.0008), (0.0224, -0.0090), (0.0172, -0.0158)], 3)
    k = np.linspace(0, 1, len(hel))
    hrad = 0.0008 + 0.0020 * smoothstep(0.0, 0.30, k) - 0.0008 * smoothstep(0.75, 1.0, k)
    hn = -0.0006 + 0.0012 * smoothstep(0.0, 0.3, k) + 0.0022 * smoothstep(0.35, 0.6, k)
    h, _ = sd_polyline(s, t, n, np.column_stack([hel, hn]), hrad)
    e = smin(e, h, 0.0012)
    ah = catmull([(0.0122, -0.0082), (0.0158, -0.0010), (0.0168, 0.0068), (0.0148, 0.0138),
                  (0.0134, 0.0198), (0.0142, 0.0248)], 4)
    ah_n = 0.0014 + 0.0022 * np.clip(ah[:, 0] / 0.024, 0, 1.2) ** 2      # follows the cupped plate
    a1, _ = sd_polyline(s, t, n, np.column_stack([ah, ah_n]),
                        np.linspace(0.0021, 0.0013, len(ah)))
    ic = catmull([(0.0150, 0.0135), (0.0095, 0.0162), (0.0040, 0.0168)], 4)
    a2, _ = sd_polyline(s, t, n, np.column_stack([ic, np.full(len(ic), 0.0010)]),
                        np.linspace(0.0016, 0.0010, len(ic)))
    e = smin(e, smin(a1, a2, 0.001), 0.0014)
    trag = sd_ellipsoid(s, t, n, (-0.0030, -0.0012, 0.0006), (0.0036, 0.0048, 0.0034))
    anti = sd_ellipsoid(s, t, n, (0.0108, -0.0092, 0.0010), (0.0034, 0.0027, 0.0026))
    lobe = sd_ellipsoid(s, t, n, (0.0088, -0.0205, 0.0002), (0.0082, 0.0090, 0.0030))
    e = smin(e, trag, 0.0015)
    e = smin(e, anti, 0.0015)
    e = smin(e, lobe, 0.004)
    tri = sd_ellipsoid(s, t, n, (0.0095, 0.0205, 0.0032), (0.0042, 0.0026, 0.0016),
                       rot=rot_xyz(0, 0, 0))
    e = smax(e, -tri, 0.0015)
    canal = sd_capsule(s, t, n, (0.0015, -0.0006, -0.0015), (0.0012, -0.0010, -0.0085), 0.0030, 0.0024)
    # the crus of the helix must survive the bowl: carve the bowl around it
    hollow = smax(smin(bowl, canal, 0.002), -(h - 0.0004), 0.001)
    hollow = smax(hollow, -(trag - 0.0004), 0.001)
    return e, hollow


def skin_sdf(x, y, z, mouth_cavity=True):
    """Signed distance to the outer skin (head + neck), negative inside.

    With mouth_cavity=False the oral cavity is left filled (used to tell the
    mouth lining apart from the outer skin)."""
    ax = np.abs(x)
    # wider blend at temple height where the face turns into the side of the skull
    k = 0.020 + 0.016 * smoothstep(-0.010, 0.035, z) * smoothstep(0.100, 0.070, z)
    d = smax_k(head_volume(ax, y, z), face_sdf(ax, y, z), k)
    d = apply_local(d, ax, y, z, Region((0.0, -0.13, -0.045), (0.035, -0.07, 0.01)),
                    lambda dd, a, b, c: _nose(dd, a, b, c))
    d = apply_local(d, ax, y, z, Region((0.0, -0.13, -0.115), (0.045, -0.055, -0.022)),
                    lambda dd, a, b, c: _mouth(dd, a, b, c))
    d = apply_local(d, ax, y, z, Region((0.004, -0.105, -0.010), (0.062, -0.045, 0.055)),
                    lambda dd, a, b, c: _eye_region(dd, a, b, c))
    d = apply_local(d, ax, y, z, Region((0.050, -0.025, -0.045), (0.105, 0.050, 0.050)),
                    lambda dd, a, b, c: _ear_region(dd, a, b, c))
    if mouth_cavity:
        d = apply_local(d, ax, y, z, Region((0.0, -0.10, -0.085), (0.048, -0.015, -0.025)),
                        lambda dd, a, b, c: np.maximum(dd, -oral_void(a, b, c)))
    return np.maximum(d, -0.20 - z)


SKIN_BOX = ((-0.105, -0.125, -0.205), (0.105, 0.115, 0.135))


# ---------------------------------------------------------------------------
# Eyes
# ---------------------------------------------------------------------------
LIMBUS_R = 0.0059   # iris radius measured perpendicular to the view axis


def build_eye(name, center, collection):
    """UV-sphere eyeball, origin at its centre, local -Y forward, with a cornea bulge.

    Rings are concentric around the visual axis (denser toward the cornea) so
    the limbus and the bulge stay round; iris/pupil are left to the shader.
    """
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=72, v_segments=48, radius=1.0)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    C = np.array([0.0, -CORNEA_OFF, 0.0])
    for v in bm.verts:
        d = np.array(v.co, float)
        d /= np.linalg.norm(d)
        th = math.acos(max(-1.0, min(1.0, -d[1])))
        # squeeze ring latitudes toward the front: more rings across the cornea
        th2 = math.pi * (th / math.pi) ** 1.35
        s = math.sin(th2)
        horiz = np.array([d[0], 0.0, d[2]])
        hn = np.linalg.norm(horiz)
        horiz = horiz / hn if hn > 1e-9 else np.array([1.0, 0.0, 0.0])
        d = np.array([horiz[0] * s, -math.cos(th2), horiz[2] * s])
        dc = d @ C
        t = dc + math.sqrt(max(dc * dc - C @ C + CORNEA_R ** 2, 0.0))
        # soft max between the sclera sphere and the cornea sphere
        k = 0.0004
        h = max(k - abs(t - EYE_R), 0.0) / k
        r = max(t, EYE_R) + h * h * k * 0.25
        v.co = Vector(d * r)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    obj = bpy.data.objects.new(name, me)
    obj.location = Vector(center)
    collection.objects.link(obj)
    return obj


# ---------------------------------------------------------------------------
# Dental arches, teeth, gums, tongue
# ---------------------------------------------------------------------------
# Arch curves through the crown centres (left half, x >= 0), plan view (x, y).
UPPER_ARCH = [(0.000, -0.0868), (0.0060, -0.0858), (0.0115, -0.0828), (0.0160, -0.0782),
              (0.0192, -0.0722), (0.0215, -0.0655), (0.0235, -0.0585), (0.0252, -0.0510),
              (0.0265, -0.0430), (0.0275, -0.0350)]
LOWER_ARCH = [(0.000, -0.0822), (0.0050, -0.0815), (0.0100, -0.0789), (0.0143, -0.0748),
              (0.0176, -0.0693), (0.0200, -0.0632), (0.0220, -0.0565), (0.0236, -0.0494),
              (0.0248, -0.0420), (0.0256, -0.0345)]
# kind, mesiodistal width W, labiolingual depth D, crown height Hc, root length Hr,
# labial crown tilt (deg).  Real adult sizes in mm (scaled by TOOTH_SCALE);
# roots are kept short because they are hidden inside the gums.
UPPER_TEETH = [("I1", 8.5, 7.0, 10.5, 4.2, 16), ("I2", 6.5, 6.0, 9.0, 4.2, 14),
               ("C", 7.5, 8.0, 10.0, 4.5, 9), ("P1", 7.0, 9.0, 8.5, 4.0, 5),
               ("P2", 6.5, 9.0, 8.0, 4.0, 4), ("M1", 10.0, 11.0, 7.5, 4.0, 2),
               ("M2", 9.0, 10.5, 7.0, 4.0, 0)]
LOWER_TEETH = [("I1", 5.3, 5.7, 9.0, 4.2, 18), ("I2", 5.9, 6.0, 9.5, 4.2, 16),
               ("C", 6.9, 7.5, 11.0, 4.5, 10), ("P1", 7.0, 7.5, 8.5, 4.0, 6),
               ("P2", 7.1, 8.0, 8.0, 4.0, 4), ("M1", 11.0, 10.5, 7.5, 4.0, 2),
               ("M2", 10.5, 10.0, 7.0, 4.0, 0)]
TOOTH_SCALE = 0.00095          # mm -> m, slightly smaller than average adult teeth
UPPER_EDGE_Z = -0.0544         # upper incisal edge (≈3 mm below the upper lip)
LOWER_EDGE_Z = -0.0569         # lower incisal edge; the jaw hangs ~2.5 mm open
UPPER_OCCL_Z = (-0.0544, -0.0522)   # occlusal height at the incisors / at M2
LOWER_OCCL_Z = (-0.0569, -0.0553)


class Arch:
    """Dense arch polyline with arc length, tangents and outward normals."""

    def __init__(self, pts):
        p = catmull(pts, 6)
        self.p = p
        seg = np.linalg.norm(p[1:] - p[:-1], axis=1)
        self.s = np.concatenate([[0.0], np.cumsum(seg)])

    def at(self, s):
        """Point, unit tangent (distal) and outward normal at arc length s."""
        i = int(np.clip(np.searchsorted(self.s, s) - 1, 0, len(self.p) - 2))
        t = (s - self.s[i]) / (self.s[i + 1] - self.s[i])
        pt = self.p[i] * (1 - t) + self.p[i + 1] * t
        tg = self.p[i + 1] - self.p[i]
        tg = tg / np.linalg.norm(tg)
        return pt, tg, np.array([tg[1], -tg[0]])

    def project(self, a, b):
        """Arc length s and signed outward offset q of plan points (a, b)."""
        best = np.full(a.shape, 1e9)
        s_out = np.zeros(a.shape)
        q_out = np.zeros(a.shape)
        for i in range(len(self.p) - 1):
            p0, p1 = self.p[i], self.p[i + 1]
            d = p1 - p0
            L2 = d @ d
            h = np.clip(((a - p0[0]) * d[0] + (b - p0[1]) * d[1]) / L2, 0.0, 1.0)
            ea, eb = a - p0[0] - d[0] * h, b - p0[1] - d[1] * h
            dist = ea * ea + eb * eb
            m = dist < best
            best = np.where(m, dist, best)
            s_out = np.where(m, self.s[i] + h * np.sqrt(L2), s_out)
            n = np.array([d[1], -d[0]]) / np.sqrt(L2)
            q_out = np.where(m, ea * n[0] + eb * n[1], q_out)
        return s_out, q_out


ARCH_U = Arch(UPPER_ARCH)
ARCH_L = Arch(LOWER_ARCH)


def tooth_sdf(u, v, h, kind, W, D, Hc, Hr):
    """One tooth in its local frame (metres).

    u: mesiodistal (along the arch), v: labial/buccal (+) to lingual (-),
    h: along the tooth axis from the cemento-enamel junction toward the
    biting edge.  Crown and root are one generalised cylinder whose section
    changes with h; the biting surface is shaped per tooth kind.
    """
    hn = np.clip(h / Hc, 0.0, 1.0)
    front = kind[0] in "IC"
    if kind[0] == "I":
        w = 0.5 * W * (0.70 + 0.30 * smoothstep(0.0, 0.55, hn))
        dd = 0.5 * D * (1.0 - 0.80 * hn ** 1.25)
        vc = 0.5 * D * 0.32 * hn
        top = Hc - 0.12 * Hc * smoothstep(0.55, 1.0, np.abs(u) / (0.5 * W))
    elif kind[0] == "C":
        w = 0.5 * W * (0.70 + 0.30 * smoothstep(0.0, 0.45, hn))
        dd = 0.5 * D * (1.0 - 0.62 * hn ** 1.4)
        vc = 0.5 * D * 0.22 * hn
        top = Hc - 0.30 * Hc * np.abs(u) / (0.5 * W)
    elif kind[0] == "P":
        w = 0.5 * W * (0.80 + 0.20 * smoothstep(0.0, 0.40, hn) - 0.10 * hn * hn)
        dd = 0.5 * D * (0.82 + 0.18 * smoothstep(0.0, 0.45, hn) - 0.12 * hn * hn)
        vc = 0.0
        cusp = np.exp(-((v - 0.2 * D) / (0.22 * D)) ** 2) + 0.8 * np.exp(-((v + 0.2 * D) / (0.22 * D)) ** 2)
        top = Hc - 0.22 * Hc + 0.20 * Hc * cusp - 0.06 * Hc * (u / (0.5 * W)) ** 2
    else:
        w = 0.5 * W * (0.84 + 0.16 * smoothstep(0.0, 0.40, hn) - 0.08 * hn * hn)
        dd = 0.5 * D * (0.84 + 0.16 * smoothstep(0.0, 0.45, hn) - 0.08 * hn * hn)
        vc = 0.0
        cu = np.zeros_like(u)
        for cu_u, cu_v in ((0.24, 0.22), (-0.24, 0.22), (0.24, -0.22), (-0.24, -0.22)):
            cu = cu + np.exp(-(((u - cu_u * W) / (0.20 * W)) ** 2 + ((v - cu_v * D) / (0.20 * D)) ** 2))
        top = Hc - 0.20 * Hc + 0.18 * Hc * np.minimum(cu, 1.0)
    # root: taper from the cervical section to a rounded apex
    rn = np.clip(-h / Hr, 0.0, 1.0)
    w0 = 0.5 * W * (0.70 if front else 0.80)
    d0 = 0.5 * D * (1.0 if front else 0.82)
    taper = 1.0 - 0.72 * rn ** 1.3
    under = h < 0
    w = np.where(under, w0 * taper, w)
    dd = np.where(under, d0 * taper, dd)
    vc = np.where(under, 0.0, vc)
    if front:
        sec = ellipse2(u, v - vc, w, dd)
    else:
        sec = box2(u, v - vc, w, dd, 0.8 * np.minimum(w, dd))
    d = smax(sec, h - top, 0.0005 * (1.0 if front else 1.6))
    return smax(d, -Hr - h, 0.0015)


def tooth_frames(upper):
    """World placement of each tooth of one side: (name, kind, dims, origin, X, Y, Z)."""
    arch = ARCH_U if upper else ARCH_L
    table = UPPER_TEETH if upper else LOWER_TEETH
    z0, z1 = UPPER_OCCL_Z if upper else LOWER_OCCL_Z
    s = 0.0
    out = []
    total = sum(t[1] for t in table) * TOOTH_SCALE
    for i, (kind, W, D, Hc, Hr, tilt) in enumerate(table):
        W, D, Hc, Hr = (v * TOOTH_SCALE for v in (W, D, Hc, Hr))
        s += 0.5 * W
        pt, tg, nrm = arch.at(s)
        s += 0.5 * W
        edge_z = z0 + (z1 - z0) * (s / total) ** 1.5
        axis = np.array([0.0, 0.0, -1.0 if upper else 1.0])        # toward the biting edge
        X = np.array([tg[0], tg[1], 0.0])
        Yb = np.array([nrm[0], nrm[1], 0.0])
        a = math.radians(tilt)
        Z = axis * math.cos(a) + Yb * math.sin(a)                     # crown tipped labially
        Y = Yb * math.cos(a) - axis * math.sin(a)
        origin = np.array([pt[0], pt[1], edge_z]) - Z * Hc
        fdi = (20 if upper else 30) + i + 1                            # FDI number, left side
        out.append((fdi, kind, (W, D, Hc, Hr), origin, X, Y, Z))
    return out


def _tooth_world_sdf(frame):
    fdi, kind, (W, D, Hc, Hr), o, X, Y, Z = frame

    def fn(x, y, z):
        dx, dy, dz = x - o[0], y - o[1], z - o[2]
        u = dx * X[0] + dy * X[1] + dz * X[2]
        v = dx * Y[0] + dy * Y[1] + dz * Y[2]
        h = dx * Z[0] + dy * Z[1] + dz * Z[2]
        return tooth_sdf(u, v, h, kind, W, D, Hc, Hr)
    corners = [o + X * a + Y * b + Z * c for a in (-W, W) for b in (-D, D) for c in (-Hr - 0.001, Hc + 0.001)]
    lo = np.min(corners, 0) - 0.0015
    hi = np.max(corners, 0) + 0.0015
    return fn, lo, hi


def build_teeth(name, upper, collection, h=0.00042):
    """Mesh every tooth of one jaw as its own closed island in a single object.

    Adds an integer point attribute `tooth_id` (FDI number: 21-27 upper left
    (+X), 11-17 upper right, 31-37 lower left, 41-47 lower right) so the gore
    system can knock out individual teeth.
    """
    all_v, all_f, ids = [], [], []
    nv = 0
    for frame in tooth_frames(upper):
        fn, lo, hi = _tooth_world_sdf(frame)
        F, org = sample_grid(fn, lo, hi, h, ratio=2)
        v, q = surface_nets(F, org, h)
        # voxel remesh each tooth on its own: guarantees a clean closed manifold
        tmp = bpy.data.objects.new("_tooth", mesh_from_arrays("_tooth", v, q))
        collection.objects.link(tmp)
        remesh_object(tmp, h)
        v, q = mesh_arrays(tmp.data)
        bpy.data.meshes.remove(tmp.data)
        v = project_to_surface(fn, v, h, 2)
        for side in (1, -1):
            vv, ff = v.copy(), q.copy()
            fdi = frame[0]
            if side < 0:
                vv[:, 0] *= -1.0
                ff = ff[:, ::-1]
                fdi = fdi - 10 if upper else fdi + 10
            all_v.append(vv)
            all_f.append(ff + nv)
            ids.append(np.full(len(vv), fdi, np.int32))
            nv += len(vv)
    me = mesh_from_arrays(name, np.concatenate(all_v), np.concatenate(all_f))
    att = me.attributes.new("tooth_id", 'INT', 'POINT')
    att.data.foreach_set("value", np.concatenate(ids))
    me.shade_smooth()
    obj = bpy.data.objects.new(name, me)
    collection.objects.link(obj)
    return obj


class CervicalArch:
    """Arch through the cemento-enamel junctions of one jaw with per-arc properties."""

    def __init__(self, upper):
        fr = tooth_frames(upper)
        pts = [o[:2] for (_, _, _, o, _, _, _) in fr]
        first = pts[0] * np.array([-1.0, 1.0])
        last = pts[-1] + (pts[-1] - pts[-2]) * 2.0
        self.arch = Arch([tuple(first)] + [tuple(p) for p in pts] + [tuple(last)])
        # arc length of each tooth centre along this arch
        s_c, _ = self.arch.project(np.array([p[0] for p in pts]), np.array([p[1] for p in pts]))
        self.s_c = s_c
        self.zc = np.array([o[2] for (_, _, _, o, _, _, _) in fr])
        self.D = np.array([dims[1] for (_, _, dims, _, _, _, _) in fr])
        self.W = np.array([dims[0] for (_, _, dims, _, _, _, _) in fr])
        self.s_end = s_c[-1] + 0.5 * self.W[-1]

    def props(self, s):
        """Cervical height, labiolingual depth and papilla factor (1 between teeth)."""
        zc = np.interp(s, self.s_c, self.zc)
        D = np.interp(s, self.s_c, self.D)
        # papilla: 0 at each tooth centre, 1 at the contact points
        pap = np.zeros_like(s)
        for c, w in zip(self.s_c, 0.5 * self.W):
            pap = np.where(np.abs(s - c) <= w, (np.abs(s - c) / w) ** 2.5, pap)
        return zc, D, pap


_CERV = {}


def _cerv(upper):
    if upper not in _CERV:
        _CERV[upper] = CervicalArch(upper)
    return _CERV[upper]


def gum_sdf(x, y, z, upper):
    """Gum band around the tooth necks with scalloped margins and papillae."""
    ax = np.abs(x)
    ca = _cerv(upper)
    s, q = ca.arch.project(ax, y)
    zc, D, pap = ca.props(s)
    sgn = 1.0 if upper else -1.0
    # height above the gum margin, measured toward the roots
    margin = zc - sgn * (0.0006 + 0.0027 * pap)
    hr = (z - margin) * sgn
    thick = 0.5 * D + 0.0009 + 0.0016 * smoothstep(0.0, 0.005, hr)
    qc = -0.0004 * smoothstep(0.0, 0.006, hr)
    d = np.abs(q - qc) - thick
    d = smax(d, -hr, 0.0012)
    # a 5-6 mm band: below it the alveolar bone is covered by thin mucosa only
    d = smax(d, hr - 0.0058, 0.002)
    # close the band behind the last molar (tuberosity / retromolar pad)
    d = smax(d, s - (ca.s_end + 0.0035), 0.004)
    return d


def tongue_sdf(x, y, z):
    """Tongue resting on the floor of the mouth behind the lower teeth."""
    ax = np.abs(x)
    body = sd_ellipsoid(ax, y, z, (0.0, -0.0500, -0.0655), (0.0205, 0.0330, 0.0105))
    tip = sd_ellipsoid(ax, y, z, (0.0, -0.0730, -0.0612), (0.0135, 0.0078, 0.0048))
    d = smin(body, tip, 0.008)
    # median sulcus along the dorsum
    dorsum = smoothstep(-0.080, -0.068, y) * smoothstep(-0.064, -0.058, z)
    d = d + 0.0007 * np.exp(-(ax / 0.0022) ** 2) * dorsum
    # stay behind the lower teeth and gums and inside the mouth cavity
    ca = _cerv(False)
    s, q = ca.arch.project(ax, y)
    _, D, _ = ca.props(s)
    d = smax(d, q + 0.5 * D + 0.0048, 0.002)
    return np.maximum(d, oral_void(ax, y, z) + 0.0009)


# ---------------------------------------------------------------------------
# Skull
# ---------------------------------------------------------------------------
CRANIUM_C = np.array([0.0, 0.001, 0.025])
CRANIUM_R = np.array([0.0740, 0.0990, 0.1000])   # the skin's cranium ellipsoid
SCALP = 0.0060         # skin surface -> outer table of the vault
BONE_T = 0.0065        # vault thickness (outer + inner table)
BRAIN_ENV_GAP = 0.0020  # inner table -> gyri crests (the sulci are carved deeper)
BRAIN_GAP = 0.0019      # safety clamp: nothing of the brain closer than this


def _vault(ax, y, z, inset):
    """The skin's cranium ellipsoid moved inward by `inset` (approximate offset)."""
    return sd_ellipsoid(ax, y, z, CRANIUM_C, CRANIUM_R - inset)


def tissue_depth(ax, z):
    """Soft tissue thickness over the face bones (skin -> bone), metres."""
    t = 0.0056 + 0.0010 * smoothstep(0.03, -0.01, z)
    # malar / infraorbital fat, maxilla under the lips, chin
    t = t + 0.0048 * np.exp(-((ax - 0.030) / 0.017) ** 2 - ((z + 0.012) / 0.016) ** 2)
    t = t + 0.0060 * np.exp(-(ax / 0.022) ** 2 - ((z + 0.040) / 0.014) ** 2)
    # thin over the lateral orbital rim / zygomatic arch
    t = t - 0.0012 * np.exp(-((ax - 0.050) / 0.010) ** 2 - ((z - 0.012) / 0.020) ** 2)
    return t


def _bone_face_height(ax, z):
    return face_height(ax, z, nose=False) + tissue_depth(ax, z)


_BONE_GRID = None


def bone_face_sdf(ax, y, z):
    """Half space behind the facial bone surface (face height field minus soft tissue)."""
    global _BONE_GRID
    if _BONE_GRID is None:
        _BONE_GRID = _Grid2D(_bone_face_height, (0.0, -0.215), (0.11, 0.145), 0.0004)
    Y, gx, gz = _BONE_GRID(ax, z)
    return (Y - y) / np.sqrt(1.0 + gx * gx + gz * gz)


def _floor_height(ax, y):
    over_orbit = smoothstep(0.006, 0.018, ax) * smoothstep(0.064, 0.050, ax)
    z_ant = 0.030 + 0.013 * over_orbit
    z_mid = -0.010 + 0.014 * np.exp(-(ax / 0.011) ** 2)
    z_post = -0.031
    return (z_ant + (z_mid - z_ant) * smoothstep(-0.046, -0.018, y)
            + (z_post - z_mid) * smoothstep(0.002, 0.030, y))


def cranial_floor(ax, y, z):
    """Floor of the cranial cavity (positive below): anterior, middle, posterior fossae."""
    e = 1e-4
    zf = _floor_height(ax, y)
    gx = (_floor_height(ax + e, y) - zf) / e
    gy = (_floor_height(ax, y + e) - zf) / e
    return (zf - z) / np.sqrt(1.0 + gx * gx + gy * gy)


# brain stem channel through the foramen magnum
STEM_PTS = [(0.0, 0.002, 0.016), (0.0, 0.012, -0.010), (0.0, 0.021, -0.034), (0.0, 0.025, -0.060)]


def _stem(ax, y, z, grow=0.0):
    d, _ = sd_polyline(ax, y, z, STEM_PTS, np.array([0.0085, 0.0135, 0.0095, 0.0075]) + grow)
    return d


def cranial_cavity(ax, y, z):
    """The space inside the skull that holds the brain (+ gap), negative inside."""
    c = smax(_vault(ax, y, z, SCALP + BONE_T), bone_face_sdf(ax, y, z) + BONE_T, 0.004)
    c = smax(c, cranial_floor(ax, y, z), 0.012)
    # where the skin dips in (temples) keep 4 mm tissue + 3.5 mm bone above the cavity
    c = apply_local(c, ax, y, z, Region((0.045, -0.075, -0.02), (0.08, 0.02, 0.075)),
                    lambda cc, a, b, zz: smax(cc, skin_sdf(a, b, zz) + 0.0080, 0.003))
    return smin(c, _stem(ax, y, z, BRAIN_GAP + 0.0012), 0.004)


def _orbit(ax, y, z):
    """Eye socket: a cone-like cavity whose apex converges back toward the midline."""
    # (opening ~40 x 35 mm at the rim)
    return sd_ellipsoid(ax, y, z, (0.0300, -0.0615, 0.0215), (0.0205, 0.0300, 0.0188),
                        rot=rot_xyz(0, 0, 22))


def _nasal(ax, y, z):
    """Piriform aperture and nasal cavity."""
    # pear-shaped piriform aperture: narrow under the nasal bones, widest low
    w = 0.0050 + 0.0072 * smoothstep(0.013, -0.017, z) - 0.0030 * smoothstep(-0.020, -0.028, z)
    ap2 = smax(ax - w, np.abs(z + 0.0060) - 0.0205, 0.0045)
    ap = extrude(ap2, y + 0.100, 0.030, 0.002)
    cav = sd_box(ax, y, z, (0.0, -0.0520, -0.0035), (0.0125, 0.0240, 0.0230), round_=0.006)
    return smin(ap, cav, 0.006)


def skull_envelope(ax, y, z):
    """Outer bone surface with the cranial cavity still filled (used by muscle/jaw)."""
    vault = _vault(ax, y, z, SCALP)
    face = bone_face_sdf(ax, y, z)
    # face skeleton block: maxilla, zygomatic bodies, nasal root
    wz = 0.0600 - 0.0200 * smoothstep(-0.005, -0.040, z)
    blk = box2(ax, y + 0.058, wz, 0.040, 0.012)
    blk = smax(blk, -0.0425 - z, 0.006)
    blk = smax(blk, z - 0.040, 0.01)
    env = smin(vault, blk, 0.010)
    env = smax(env, face, 0.004)
    # skull base: nothing below the occiput / mastoids
    zb = -0.040 + 0.012 * smoothstep(-0.030, -0.010, y) * smoothstep(0.012, -0.004, y)
    env = smax(env, zb - z, 0.006)
    # temporal fossa between the cranial wall and the zygomatic arch
    # (deep enough for a 8-12 mm temporalis between bone and skin)
    env = smax(env, -sd_ellipsoid(ax, y, z, (0.0680, -0.0300, 0.0120), (0.0150, 0.0290, 0.0330)), 0.008)
    # infratemporal space under the cheekbones, behind the maxilla
    env = smax(env, -sd_box(ax, y, z, (0.050, -0.012, -0.030), (0.016, 0.024, 0.024), round_=0.008), 0.008)
    # zygomatic arches and bodies, mastoid processes, nasal bones
    # the arch stands free of the temporal fossa, from the cheekbone to above
    # the jaw joint in front of the ear
    arch = sd_capsule(ax, y, z, (0.0520, -0.0520, 0.0010), (0.0615, -0.0120, 0.0030), 0.0040, 0.0034)
    zyg = sd_ellipsoid(ax, y, z, (0.0450, -0.0600, 0.0020), (0.0100, 0.0120, 0.0110),
                       rot=rot_xyz(0, 0, -35))
    env = smin(env, smin(arch, zyg, 0.006), 0.004)
    mast = sd_ellipsoid(ax, y, z, (0.0500, 0.0120, -0.0300), (0.0075, 0.0095, 0.0140), rot=rot_xyz(15, 0, 0))
    env = smin(env, mast, 0.006)
    nb = sd_capsule(ax, y, z, (0.0, -0.0835, 0.0215), (0.0, -0.0935, 0.0030), 0.0040, 0.0055)
    env = smin(env, nb, 0.004)
    # whatever was carved above, keep at least 3.5 mm of bone around the brain case;
    # not below the skull base, so the foramen magnum stays open (a sealed cavity
    # would be filled in by the voxel remesher)
    shell = np.maximum(cranial_cavity(ax, y, z) - 0.0035, -0.033 - z)
    return smin(env, shell, 0.002)


def skull_sdf(x, y, z):
    """Skull (cranium + face bones) as a closed solid with real bone thickness."""
    ax = np.abs(x)
    env = skull_envelope(ax, y, z)
    cav = cranial_cavity(ax, y, z)
    d = smax(env, -cav, 0.002)
    # openings and air spaces, never closer than 2.5 mm to the brain case
    holes = smin(_orbit(ax, y, z), _nasal(ax, y, z), 0.002)
    # maxillary sinus: an internal air space kept 2 mm inside the bone surface
    sinus = sd_ellipsoid(ax, y, z, (0.0250, -0.0580, -0.0100), (0.0115, 0.0150, 0.0120))
    holes = np.minimum(holes, smax(sinus, env + 0.002, 0.002))
    holes = np.minimum(holes, sd_capsule(ax, y, z, (0.0720, 0.0, 0.0), (0.0540, 0.0, 0.0), 0.0040))
    holes = np.minimum(holes, sd_sphere(ax, y, z, (0.0500, -0.0120, -0.0010), 0.0068))
    holes = smax(holes, -(cav - 0.0025), 0.002)
    d = smax(d, -holes, 0.0025)
    # never closer than 4 mm to the skin (incl. the mouth cavity), clear of gums and eyes
    d = np.maximum(d, skin_sdf(x, y, z) + 0.004)
    d = np.maximum(d, -(sd_sphere(ax, y, z, EYE_C, EYE_R) - 0.0015))
    return apply_local(d, ax, y, z, Region((0.0, -0.10, -0.085), (0.040, -0.020, -0.025)),
                       lambda dd, a, b, c: np.maximum(dd, -(_gums_both(a, b, c) - 0.0016)))


def _gums_both(x, y, z):
    return np.minimum(gum_sdf(x, y, z, True), gum_sdf(x, y, z, False))


SKULL_BOX = ((-0.085, -0.110, -0.075), (0.085, 0.110, 0.130))


# ---------------------------------------------------------------------------
# Mandible
# ---------------------------------------------------------------------------
JAW_LINE = [(0.0, -0.0835), (0.0100, -0.0810), (0.0180, -0.0730), (0.0230, -0.0620),
            (0.0262, -0.0500), (0.0290, -0.0380), (0.0340, -0.0260), (0.0410, -0.0150),
            (0.0460, -0.0060), (0.0480, 0.0000)]
_JAW_ARCH = None


def jaw_sdf(x, y, z):
    """Mandible: U-shaped body with symphysis and chin, rami with condyles and coronoids."""
    ax = np.abs(x)
    d = jaw_raw(ax, y, z)
    # clamps: 5 mm inside the outer skin, but only ~1.5 mm of mucosa between
    # the bone and the mouth lining (the vestibule behind the lower lip), so
    # the front of the mandible keeps its full height; clear of skull and gums
    d = np.maximum(d, skin_sdf(x, y, z, mouth_cavity=False) + 0.005)
    d = np.maximum(d, skin_sdf(x, y, z) + 0.0015)
    d = np.maximum(d, -(skull_envelope(ax, y, z) - 0.0012))
    return apply_local(d, ax, y, z, Region((0.0, -0.10, -0.090), (0.040, -0.020, -0.050)),
                       lambda dd, a, b, c: np.maximum(dd, -(gum_sdf(a, b, c, False) - 0.0010)))


def jaw_raw(ax, y, z):
    """Unclamped mandible shape (x already mirrored)."""
    global _JAW_ARCH
    if _JAW_ARCH is None:
        _JAW_ARCH = Arch([(-0.010, -0.0810)] + JAW_LINE)
    s, q = _JAW_ARCH.project(ax, y)
    s = s - _JAW_ARCH.project(np.array([0.0]), np.array([-0.0835]))[0][0]
    sn = np.clip(s / 0.090, 0.0, 1.0)
    zbot = -0.0985 + 0.0110 * sn ** 1.4 + 0.0150 * smoothstep(0.70, 1.0, sn)
    # the alveolar ridge rises to just under the gum margin and holds the roots
    ztop = -0.0668 + 0.0026 * smoothstep(0.25, 0.6, sn) - 0.0060 * smoothstep(0.75, 1.0, sn)
    zm, hh = 0.5 * (zbot + ztop), 0.5 * (ztop - zbot)
    # thicker at the base than at the ridge (rounded, teardrop section)
    th = (0.0058 + 0.0014 * smoothstep(0.3, 0.7, sn) - 0.0020 * smoothstep(0.85, 1.0, sn)) \
        * (1.0 + 0.18 * smoothstep(zm + hh * 0.2, zbot, z))
    body = extrude(np.abs(q + 0.0008) - th, z - zm, hh, 0.0040)
    # ramus plate with condyle and coronoid process
    rz = np.clip((z + 0.078) / 0.070, 0.0, 1.0)
    yb = -0.0020 - 0.0050 * rz          # posterior border leans back going up
    yf = -0.0300 + 0.0020 * rz
    plate = box2(y - 0.5 * (yb + yf), z + 0.043, 0.5 * (yb - yf) + 0.0 * rz, 0.036, 0.012)
    # the angle flares slightly outward (masseter insertion)
    plate = smax(plate, np.abs(ax - (0.0465 + 0.004 * rz + 0.002 * (1.0 - rz) ** 3)) - 0.0028, 0.002)
    notch = sd_ellipsoid(ax, y, z, (0.048, -0.021, 0.000), (0.02, 0.0075, 0.0085))
    plate = smax(plate, -notch, 0.003)
    cond = sd_ellipsoid(ax, y, z, (0.0500, -0.0115, -0.0020), (0.0085, 0.0048, 0.0050), rot=rot_xyz(0, 0, 12))
    cor = sd_capsule(ax, y, z, (0.0460, -0.0270, -0.020), (0.0445, -0.0340, -0.0045), 0.0035, 0.0012)
    ram = smin(smin(plate, cond, 0.004), cor, 0.004)
    d = smin(body, ram, 0.008)
    # chin: mental protuberance
    return smin(d, sd_ellipsoid(ax, y, z, (0.0, -0.0835, -0.0890), (0.0120, 0.0045, 0.0085)), 0.006)


JAW_BOX = ((-0.065, -0.100, -0.112), (0.065, 0.012, 0.012))


# ---------------------------------------------------------------------------
# Brain
# ---------------------------------------------------------------------------
def _fib_dirs(n, seed=3):
    rng = np.random.default_rng(seed)
    i = np.arange(n) + 0.5
    phi = np.arccos(1 - 2 * i / n)
    th = np.pi * (1 + 5 ** 0.5) * i + rng.uniform(0, 1)
    d = np.stack([np.cos(th) * np.sin(phi), np.sin(th) * np.sin(phi), np.cos(phi)], 1)
    return d, rng.uniform(0, 2 * np.pi, n)


_GYRI_K, _GYRI_PH = _fib_dirs(26)
_GYRI_K2, _GYRI_PH2 = _fib_dirs(22, seed=7)
_WARP_K, _WARP_PH = _fib_dirs(6, seed=11)


def gyri_field(x, y, z):
    """Sulcus distance: a primary labyrinth plus sparser branching sulci."""
    s1 = _wave_nodal_distance(x, y, z, _GYRI_K, _GYRI_PH, 0.0175)
    s2 = _wave_nodal_distance(x, y, z, _GYRI_K2, _GYRI_PH2, 0.0300)
    return np.minimum(s1, s2 + 0.0008)


def _wave_nodal_distance(x, y, z, dirs, phases, wavelength):
    """Distance (m, approx.) to the nodal lines of a monochromatic random wave field.

    The nodal set of such a field is a labyrinth of meandering lines with an
    almost constant spacing - the sulci; the regions between are the gyri.
    """
    k = 2 * np.pi / wavelength
    # low frequency domain warp so the folds meander instead of looking periodic
    kw = 2 * np.pi / 0.060
    wx = wy = wz = 0.0
    for i, (d, ph) in enumerate(zip(_WARP_K, _WARP_PH)):
        s = np.sin(kw * (d[0] * x + d[1] * y + d[2] * z) + ph)
        a = _WARP_K[(i + 2) % len(_WARP_K)]
        wx, wy, wz = wx + a[0] * s, wy + a[1] * s, wz + a[2] * s
    amp = 0.0035
    px, py, pz = x + amp * wx, y + amp * wy, z + amp * wz
    n = np.zeros_like(x)
    gx = np.zeros_like(x)
    gy = np.zeros_like(x)
    gz = np.zeros_like(x)
    for d, ph in zip(dirs, phases):
        arg = k * (d[0] * px + d[1] * py + d[2] * pz) + ph
        n += np.cos(arg)
        s = np.sin(arg)
        gx -= s * d[0]
        gy -= s * d[1]
        gz -= s * d[2]
    g = k * np.sqrt(gx * gx + gy * gy + gz * gz) + 1e-6
    return np.abs(n) / g


def _sulcus_profile(s, depth=0.0030, width=0.0008, half_gyrus=0.0044, round_d=0.0034):
    """How far the surface is pushed in at distance s from a sulcus line.

    A narrow deep slit (the sulcus) plus a convex (1-t)^2 fall-off that rounds
    each gyrus like a tube pressed against its neighbours."""
    t = np.clip(s / half_gyrus, 0.0, 1.0)
    return depth * np.exp(-(s / width) ** 2) + round_d * (1.0 - t) ** 2


# major sulci (left hemisphere), traced over the brain surface
CENTRAL_SULCUS = [(0.003, -0.002, 0.103), (0.020, -0.004, 0.098), (0.036, -0.008, 0.086),
                  (0.048, -0.012, 0.068), (0.055, -0.016, 0.050)]
LATERAL_FISSURE = [(0.047, -0.042, 0.012), (0.053, -0.030, 0.017), (0.057, -0.015, 0.024),
                   (0.058, 0.002, 0.031), (0.056, 0.018, 0.040)]
TENTORIUM_Y0 = 0.012


def brain_sdf(x, y, z):
    """Cerebrum (two gyrified hemispheres), cerebellum with folia, brain stem."""
    ax = np.abs(x)
    cav = cranial_cavity(ax, y, z)
    env = smax(_vault(ax, y, z, SCALP + BONE_T + BRAIN_ENV_GAP),
               bone_face_sdf(ax, y, z) + BONE_T + BRAIN_ENV_GAP, 0.004)
    env = smax(env, cranial_floor(ax, y, z) + BRAIN_ENV_GAP, 0.012)
    # tentorium: cerebrum above, cerebellum below (behind the temporal lobes)
    zt = 0.010 - 0.010 * smoothstep(0.02, 0.09, y)
    behind = smoothstep(TENTORIUM_Y0, TENTORIUM_Y0 + 0.012, y)
    cerebrum = smax(env, (zt + 0.0008 - z) * behind - 0.02 * (1 - behind), 0.003)
    cereb = smax(env, z - (zt - 0.0008), 0.003)
    cereb = smax(cereb, sd_ellipsoid(ax, y, z, (0.0, 0.050, -0.010), (0.050, 0.034, 0.030)), 0.004)
    # longitudinal fissure, closed underneath by the corpus callosum
    zcc = 0.046 - 0.30 * (smoothstep(0.034, 0.050, y) + smoothstep(-0.036, -0.052, y))
    fis = np.maximum(ax - 0.0013, zcc - z)
    cerebrum = smax(cerebrum, -fis, 0.0030)
    # sylvian fissure (separates the temporal lobe) and central sulcus
    lf, _ = sd_polyline(ax, y, z, LATERAL_FISSURE, [0.0012] * 5)
    deep = [(p[0] - 0.008, p[1] + 0.001, p[2] + 0.002) for p in LATERAL_FISSURE]   # 8 mm deeper
    lf2, _ = sd_polyline(ax, y, z, deep, [0.0010] * 5)
    cerebrum = smax(cerebrum, -smin(lf, lf2, 0.004), 0.0022)
    cs, _ = sd_polyline(ax, y, z, CENTRAL_SULCUS, [0.0009] * 5)
    cerebrum = smax(cerebrum, -cs, 0.0022)
    # gyri and sulci, only in the outer shell of the cerebrum
    shell = smoothstep(-0.012, -0.004, env)
    s = gyri_field(ax + 0.0, y, z)
    cerebrum = cerebrum + _sulcus_profile(s) * shell
    # cerebellum: bilobed with fine transverse folia
    cc = np.array([0.0, 0.030, 0.004])
    r = np.sqrt((ax - cc[0]) ** 2 + ((y - cc[1]) * 0.9) ** 2 + ((z - cc[2]) * 1.2) ** 2)
    fol = 0.5 + 0.5 * np.cos(2 * np.pi * r / 0.0030)
    cereb = cereb + 0.0016 * fol ** 4 * smoothstep(-0.007, -0.002, env)
    cereb = smax(cereb, -sd_ellipsoid(ax, y, z, (0.0, 0.080, -0.012), (0.004, 0.012, 0.030)), 0.004)
    d = smin(cerebrum, cereb, 0.0015)
    # brain stem (midbrain, pons, medulla) through the foramen magnum
    stem = _stem(ax, y, z)
    pons = sd_ellipsoid(ax, y, z, (0.0, 0.004, -0.010), (0.0135, 0.0100, 0.0120))
    d = smin(d, smin(stem, pons, 0.006), 0.005)
    # always inside the cranial cavity with at least the minimum gap
    return smax(d, cav + BRAIN_GAP, 0.001)


BRAIN_BOX = ((-0.070, -0.090, -0.065), (0.070, 0.100, 0.115))


# ---------------------------------------------------------------------------
# Soft tissue (muscle / fat) layer
# ---------------------------------------------------------------------------
SKIN_T = 0.0035        # skin + subcutis thickness above the muscle layer


def muscle_sdf(x, y, z):
    """Soft tissue between skin and bone: skin inset, minus bone, eyes and teeth."""
    ax = np.abs(x)
    d = skin_sdf(x, y, z) + SKIN_T
    # everything that is not soft tissue (dilated by a clearance)
    env = skull_envelope(ax, y, z)
    orbit = smax(_orbit(ax, y, z), -(cranial_cavity(ax, y, z) - 0.0025), 0.002)
    env = smax(env, -orbit, 0.003)                  # orbital fat fills the orbits
    hard = np.minimum(env, jaw_raw(ax, y, z) - 0.0008)
    hard = np.minimum(hard, sd_sphere(ax, y, z, EYE_C, EYE_R + 0.0003))
    hard = np.minimum(hard, _stem(ax, y, z, BRAIN_GAP + 0.0005))
    d = np.maximum(d, -(hard - 0.0012))
    return apply_local(d, ax, y, z, Region((0.0, -0.10, -0.090), (0.040, -0.020, -0.025)),
                       lambda dd, a, b, c: np.maximum(dd, -(_gums_both(a, b, c) - 0.0012)))


MUSCLE_BOX = ((-0.105, -0.125, -0.205), (0.105, 0.115, 0.135))


# ---------------------------------------------------------------------------
# Assembly
# ---------------------------------------------------------------------------
# grid spacing / voxel size per layer (metres).  Finer = slower.
RES = {
    "skin": 0.0012, "muscle": 0.0019, "skull": 0.0014, "jaw": 0.0010,
    "brain": 0.00095, "gums": 0.0007, "tongue": 0.0007,
}


def _split_faces(obj, mask, new_name, collection):
    """Move the faces selected by `mask` from obj into a new object (shared border verts)."""
    v, f = mesh_arrays(obj.data)
    parts = []
    for sel, name in ((~mask, obj.data.name), (mask, new_name)):
        ff = f[sel]
        used = np.unique(ff)
        remap = np.full(len(v), -1, np.int64)
        remap[used] = np.arange(len(used))
        parts.append((name, v[used], remap[ff]))
    (n0, v0, f0), (n1, v1, f1) = parts
    old = obj.data
    obj.data = mesh_from_arrays(n0, v0, f0)
    bpy.data.meshes.remove(old)
    obj.data.name = n0
    obj.data.shade_smooth()
    me = mesh_from_arrays(n1, v1, f1)
    me.shade_smooth()
    new = bpy.data.objects.new(new_name, me)
    collection.objects.link(new)
    return new


def _face_centres(me):
    v, f = mesh_arrays(me)
    return v[f].mean(1)


def _point_attr(obj, name, values):
    att = obj.data.attributes.get(name) or obj.data.attributes.new(name, 'FLOAT', 'POINT')
    att.data.foreach_set("value", np.asarray(values, np.float32))


def _ray_hit(fn, p0, p1, n=6000):
    t = np.linspace(0.0, 1.0, n)
    p = np.asarray(p0, float)[None] + t[:, None] * (np.asarray(p1, float) - np.asarray(p0, float))[None]
    d = fn(p[:, 0].copy(), p[:, 1].copy(), p[:, 2].copy())
    i = np.nonzero(d < 0)[0]
    return None if len(i) == 0 else tuple(round(float(c), 4) for c in p[i[0]])


def _collect_landmarks(objs):
    """Measure the landmark table on the built geometry."""
    L = {}
    sk = objs["GH_Skin"]
    v = get_verts(sk.data)
    L["vertex_top"] = _ray_hit(skin_sdf, (0.0, 0.005, 0.20), (0.0, 0.005, 0.0))
    L["back_of_head"] = _ray_hit(skin_sdf, (0.0, 0.20, 0.030), (0.0, 0.0, 0.030))
    L["glabella"] = _ray_hit(skin_sdf, (0.0, -0.20, 0.035), (0.0, 0.0, 0.035))
    L["nasion"] = _ray_hit(skin_sdf, (0.0, -0.20, 0.023), (0.0, 0.0, 0.023))
    front = v[np.abs(v[:, 0]) < 0.004]
    tip = front[np.argmin(front[:, 1])]
    L["nose_tip"] = tuple(round(float(c), 4) for c in tip)
    L["subnasale"] = _ray_hit(skin_sdf, (0.0, -0.20, -0.031), (0.0, 0.0, -0.031))
    up = _ray_hit(skin_sdf, (0.0, -0.094, -0.056), (0.0, -0.094, -0.030))
    lo = _ray_hit(skin_sdf, (0.0, -0.094, -0.056), (0.0, -0.094, -0.080))
    L["mouth_center"] = (0.0, -0.094, round(0.5 * (up[2] + lo[2]), 4))
    L["lip_gap"] = round(up[2] - lo[2], 4)
    L["mouth_corner_L"] = (0.0238, -0.0848, -0.0552)
    L["mouth_width"] = 2 * 0.0238
    L["pogonion"] = _ray_hit(skin_sdf, (0.0, -0.20, -0.092), (0.0, 0.0, -0.092))
    chin = v[(np.abs(v[:, 0]) < 0.004) & (v[:, 1] < -0.06) & (v[:, 2] > -0.13)]
    L["chin_bottom"] = tuple(round(float(c), 4) for c in chin[np.argmin(chin[:, 2])])
    L["eye_L"] = tuple(float(c) for c in EYE_C)
    L["eye_R"] = (-float(EYE_C[0]), float(EYE_C[1]), float(EYE_C[2]))
    L["eye_radius"] = EYE_R
    L["ear_canal_L"] = (0.072, 0.0, 0.0)
    L["ear_canal_R"] = (-0.072, 0.0, 0.0)
    side = v[(np.abs(v[:, 1]) < 0.06) & (v[:, 2] > 0.045) & (v[:, 2] < 0.10)]   # above the ears
    L["head_half_width"] = round(float(np.abs(side[:, 0]).max()), 4)
    L["neck_radius"] = 0.054
    L["neck_center_y"] = 0.008
    L["neck_cut_z"] = -0.20
    L["gonion_L"] = (0.050, -0.004, -0.075)
    L["upper_incisal_edge_z"] = UPPER_EDGE_Z
    L["lower_incisal_edge_z"] = LOWER_EDGE_Z
    return L


def build_anatomy():
    """Build every anatomical layer in collection GoreHead.

    Returns a dict name -> object for GH_Skin, GH_Muscle, GH_Skull, GH_Jaw,
    GH_Brain, GH_Eye_L, GH_Eye_R, GH_Teeth_Upper, GH_Teeth_Lower, GH_Gums,
    GH_Tongue and GH_MouthCavity.  ANATOMY_LANDMARKS is filled in as well.
    """
    t0 = time.time()
    col = ghc.get_collection(COLLECTION)
    objs = {}

    def timed(name, fn):
        t = time.time()
        o = fn()
        objs[name] = o
        print(f"  {name:16s} {len(o.data.vertices):7d} verts  {time.time() - t:5.1f} s")
        return o

    # skin, then split the mouth lining off into GH_MouthCavity
    skin = timed("GH_Skin", lambda: mesh_sdf("GH_Skin", skin_sdf, *SKIN_BOX, RES["skin"],
                                             voxel=RES["skin"], project=2, collection=col))
    c = _face_centres(skin.data)
    closed = skin_sdf(c[:, 0], c[:, 1], c[:, 2], mouth_cavity=False)
    in_mouth = Region((-0.05, -0.105, -0.09), (0.05, -0.01, -0.02)).mask(c[:, 0], c[:, 1], c[:, 2])
    objs["GH_MouthCavity"] = _split_faces(skin, (closed < -0.0006) & in_mouth, "GH_MouthCavity", col)
    v = get_verts(skin.data)
    up, lo = lips_sdf(np.abs(v[:, 0]), v[:, 1], v[:, 2])
    _point_attr(skin, "gh_lip", smoothstep(0.0016, 0.0003, np.minimum(up, lo)))

    timed("GH_Muscle", lambda: mesh_sdf("GH_Muscle", muscle_sdf, *MUSCLE_BOX, RES["muscle"],
                                        voxel=RES["muscle"], project=1, collection=col))
    timed("GH_Skull", lambda: mesh_sdf("GH_Skull", skull_sdf, *SKULL_BOX, RES["skull"],
                                       voxel=RES["skull"], project=1, collection=col))
    timed("GH_Jaw", lambda: mesh_sdf("GH_Jaw", jaw_sdf, *JAW_BOX, RES["jaw"],
                                     voxel=RES["jaw"], project=2, collection=col))
    brain = timed("GH_Brain", lambda: mesh_sdf("GH_Brain", brain_sdf, *BRAIN_BOX, RES["brain"],
                                               voxel=RES["brain"], project=1, collection=col))
    v = get_verts(brain.data)
    s = gyri_field(np.abs(v[:, 0]), v[:, 1], v[:, 2])
    _point_attr(brain, "gh_sulcus", np.exp(-(s / 0.0016) ** 2))
    timed("GH_Eye_L", lambda: build_eye("GH_Eye_L", EYE_C, col))
    timed("GH_Eye_R", lambda: build_eye("GH_Eye_R", EYE_C * np.array([-1, 1, 1]), col))
    timed("GH_Teeth_Upper", lambda: build_teeth("GH_Teeth_Upper", True, col))
    timed("GH_Teeth_Lower", lambda: build_teeth("GH_Teeth_Lower", False, col))
    gums = lambda x, y, z: np.minimum(gum_sdf(x, y, z, True), gum_sdf(x, y, z, False))
    timed("GH_Gums", lambda: mesh_sdf("GH_Gums", gums, (-0.036, -0.098, -0.084), (0.036, -0.024, -0.030),
                                      RES["gums"], voxel=RES["gums"], project=2, collection=col))
    timed("GH_Tongue", lambda: mesh_sdf("GH_Tongue", tongue_sdf, (-0.030, -0.095, -0.080),
                                        (0.030, -0.010, -0.045), RES["tongue"], voxel=RES["tongue"],
                                        project=2, collection=col))
    for o in objs.values():
        o.data.shade_smooth()
    ANATOMY_LANDMARKS.clear()
    ANATOMY_LANDMARKS.update(_collect_landmarks(objs))
    print(f"  build_anatomy total {time.time() - t0:.1f} s")
    order = ["GH_Skin", "GH_Muscle", "GH_Skull", "GH_Jaw", "GH_Brain", "GH_Eye_L", "GH_Eye_R",
             "GH_Teeth_Upper", "GH_Teeth_Lower", "GH_Gums", "GH_Tongue", "GH_MouthCavity"]
    return {k: objs[k] for k in order}


# ---------------------------------------------------------------------------
# Test harness: look-dev materials, interpenetration report, renders
# ---------------------------------------------------------------------------
def _principled(name, color, rough=0.5, sss=0.0, sss_radius=(0.004, 0.0015, 0.001), coat=0.0):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if m.node_tree is None:
        m.use_nodes = True
    b = m.node_tree.nodes.get("Principled BSDF")
    b.inputs["Base Color"].default_value = (*color, 1.0)
    b.inputs["Roughness"].default_value = rough
    if sss:
        b.inputs["Subsurface Weight"].default_value = sss
        b.inputs["Subsurface Radius"].default_value = sss_radius
        b.inputs["Subsurface Scale"].default_value = 1.0
    if coat:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = 0.05
    return m


def _eye_lookdev():
    """White sclera, dark iris disc and black pupil from the eye's local -Y axis."""
    m = _principled("LD_Eye", (0.85, 0.83, 0.8), 0.25, coat=1.0)
    nt = m.node_tree
    b = nt.nodes.get("Principled BSDF")
    tc = nt.nodes.new("ShaderNodeTexCoord")
    nm = nt.nodes.new("ShaderNodeVectorMath")
    nm.operation = 'NORMALIZE'
    sp = nt.nodes.new("ShaderNodeSeparateXYZ")
    neg = nt.nodes.new("ShaderNodeMath")
    neg.operation = 'MULTIPLY'
    neg.inputs[1].default_value = -1.0
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    el = ramp.color_ramp.elements
    el[0].position, el[0].color = 0.862, (0.85, 0.82, 0.78, 1)
    el[1].position, el[1].color = 0.872, (0.16, 0.11, 0.07, 1)
    el.new(0.960).color = (0.22, 0.15, 0.09, 1)
    el.new(0.975).color = (0.005, 0.005, 0.005, 1)
    # inside the globe (only seen on cut faces): milky vitreous instead of the iris
    ln = nt.nodes.new("ShaderNodeVectorMath")
    ln.operation = 'LENGTH'
    inner = nt.nodes.new("ShaderNodeMath")
    inner.operation = 'LESS_THAN'
    inner.inputs[1].default_value = EYE_R * 0.97
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.inputs["B"].default_value = (0.75, 0.72, 0.70, 1)
    nt.links.new(tc.outputs["Object"], nm.inputs[0])
    nt.links.new(tc.outputs["Object"], ln.inputs[0])
    nt.links.new(ln.outputs["Value"], inner.inputs[0])
    nt.links.new(nm.outputs[0], sp.inputs[0])
    nt.links.new(sp.outputs["Y"], neg.inputs[0])
    nt.links.new(neg.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], mix.inputs["A"])
    nt.links.new(inner.outputs[0], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], b.inputs["Base Color"])
    return m


def lookdev_materials(objs):
    """Simple temporary materials so the test renders read clearly."""
    mats = {
        "GH_Skin": _principled("LD_Skin", (0.50, 0.31, 0.23), 0.42, sss=0.15),
        "GH_Muscle": _principled("LD_Muscle", (0.45, 0.07, 0.06), 0.4),
        "GH_Skull": _principled("LD_Bone", (0.80, 0.72, 0.52), 0.55),
        "GH_Jaw": _principled("LD_Bone", (0.80, 0.72, 0.52), 0.55),
        "GH_Brain": _principled("LD_Brain", (0.74, 0.42, 0.44), 0.35, sss=0.2),
        "GH_Eye_L": _eye_lookdev(), "GH_Eye_R": _eye_lookdev(),
        "GH_Teeth_Upper": _principled("LD_Teeth", (0.86, 0.82, 0.70), 0.25),
        "GH_Teeth_Lower": _principled("LD_Teeth", (0.86, 0.82, 0.70), 0.25),
        "GH_Gums": _principled("LD_Gums", (0.62, 0.20, 0.22), 0.35, sss=0.1),
        "GH_Tongue": _principled("LD_Tongue", (0.60, 0.24, 0.25), 0.4, sss=0.1),
        "GH_MouthCavity": _principled("LD_Mouth", (0.20, 0.03, 0.03), 0.5),
    }
    lip = mats["GH_Skin"]
    nt = lip.node_tree
    attr = nt.nodes.new("ShaderNodeAttribute")
    attr.attribute_name = "gh_lip"
    mix = nt.nodes.new("ShaderNodeMix")
    mix.data_type = 'RGBA'
    mix.inputs["A"].default_value = (0.50, 0.31, 0.23, 1)
    mix.inputs["B"].default_value = (0.42, 0.17, 0.16, 1)
    nt.links.new(attr.outputs["Fac"], mix.inputs["Factor"])
    nt.links.new(mix.outputs["Result"], nt.nodes["Principled BSDF"].inputs["Base Color"])
    for name, o in objs.items():
        if name in mats:
            o.data.materials.clear()
            o.data.materials.append(mats[name])


def _bvh(obj):
    """World-space BVH of an object's mesh."""
    from mathutils.bvhtree import BVHTree
    me = obj.data
    me.calc_loop_triangles()
    f = np.empty(len(me.loop_triangles) * 3, np.int32)
    me.loop_triangles.foreach_get("vertices", f)
    f = f.reshape(-1, 3)
    v = get_verts(me)
    mw = np.array(obj.matrix_world)
    v = v @ mw[:3, :3].T + mw[:3, 3]
    return BVHTree.FromPolygons(v.tolist(), f.tolist())


def _min_gap(src, dst_bvh, stride=1):
    """Smallest distance from src vertices to the dst surface (world space) and where."""
    mw = src.matrix_world
    best, where = 1e9, None
    for i, v in enumerate(src.data.vertices):
        if i % stride:
            continue
        p = mw @ v.co
        hit = dst_bvh.find_nearest(p)
        if hit[0] is not None and hit[3] < best:
            best, where = hit[3], p
    return best, where


def mesh_quality(obj):
    """(verts, faces, boundary edges, non-manifold edges) of an object's mesh."""
    me = obj.data
    e = np.empty(len(me.loops), np.int32)
    me.loops.foreach_get("edge_index", e)
    per_edge = np.bincount(e, minlength=len(me.edges))
    return len(me.vertices), len(me.polygons), int((per_edge == 1).sum()), int((per_edge > 2).sum())


def check_report(objs):
    """Mesh quality plus interpenetration tests between layers (overlaps, minimum gaps)."""
    print("\nMesh quality (boundary edges are expected only where skin and mouth lining meet)")
    for k, o in objs.items():
        nv, nf, nb, nm = mesh_quality(o)
        print(f"  {k:15s} verts={nv:7d} faces={nf:7d} boundary={nb:5d} non-manifold={nm}")
    sv = get_verts(objs["GH_Skull"].data)
    inner = int((np.abs(cranial_cavity(np.abs(sv[:, 0]), sv[:, 1], sv[:, 2])) < 0.001).sum())
    print(f"  GH_Skull inner table (cranial cavity wall) vertices: {inner}  {'OK' if inner else 'MISSING'}")
    mv = get_verts(objs["GH_Muscle"].data)
    under = int((np.abs(skull_envelope(np.abs(mv[:, 0]), mv[:, 1], mv[:, 2])) < 0.0025).sum())
    print(f"  GH_Muscle inner surface (lying on the bone) vertices: {under}  {'OK' if under else 'MISSING'}")
    trees = {k: _bvh(o) for k, o in objs.items()}
    pairs = [
        ("GH_Brain", "GH_Skull"), ("GH_Skull", "GH_Muscle"), ("GH_Muscle", "GH_Skin"),
        ("GH_Jaw", "GH_Skull"), ("GH_Jaw", "GH_Muscle"), ("GH_Jaw", "GH_Skin"),
        ("GH_Eye_L", "GH_Skin"), ("GH_Eye_R", "GH_Skin"), ("GH_Eye_L", "GH_Skull"),
        ("GH_Eye_L", "GH_Muscle"), ("GH_Teeth_Upper", "GH_Skin"), ("GH_Teeth_Lower", "GH_Skin"),
        ("GH_Teeth_Upper", "GH_MouthCavity"), ("GH_Teeth_Lower", "GH_MouthCavity"),
        ("GH_Teeth_Upper", "GH_Teeth_Lower"), ("GH_Tongue", "GH_Skin"),
        ("GH_Tongue", "GH_MouthCavity"), ("GH_Tongue", "GH_Teeth_Lower"),
        ("GH_Tongue", "GH_Teeth_Upper"), ("GH_Tongue", "GH_Gums"), ("GH_Brain", "GH_Muscle"),
        ("GH_Skull", "GH_Skin"), ("GH_Brain", "GH_Skin"), ("GH_Gums", "GH_Skull"),
        ("GH_Gums", "GH_Jaw"), ("GH_Gums", "GH_Muscle"),
    ]
    print("\nInterpenetration report (triangle-pair overlaps, min vertex->surface gap)")
    ok_all = True
    for a, b in pairs:
        n = len(trees[a].overlap(trees[b]))
        gap, where = _min_gap(objs[a], trees[b], stride=2)
        ok = n == 0
        ok_all &= ok
        w = "" if where is None else f"  at ({where.x:+.3f},{where.y:+.3f},{where.z:+.3f})"
        tag = "OK  " if ok else "FAIL"
        print(f"  {tag} {a:15s} vs {b:15s} overlaps={n:6d}  min gap={gap * 1000:6.2f} mm{w}")
    # brain sits inside the skull cavity with the intended gap (gyri crests are the
    # closest points; sulci and the medial surfaces are naturally further away)
    t = trees["GH_Skull"]
    d = np.array([t.find_nearest(v.co)[3] for v in objs["GH_Brain"].data.vertices]) * 1000
    p = np.percentile(d, [0, 1, 5])
    print(f"  brain -> skull gap: min {p[0]:.2f} mm, 1% {p[1]:.2f} mm, 5% {p[2]:.2f} mm")
    # teeth crowns behind the lips: the most anterior upper tooth point vs skin front
    tv = np.array([objs["GH_Teeth_Upper"].matrix_world @ v.co for v in objs["GH_Teeth_Upper"].data.vertices])
    print(f"  most anterior tooth point y = {tv[:, 1].min():.4f} (upper lip front ≈ -0.101)")
    print(f"  intended contacts not listed: tooth roots inside gums, gums embedded in the mouth lining")
    return ok_all


def _cutaway(objs, x_hi=0.030, x_lo=0.004, z_step=-0.035):
    """Cut away x > x_hi (and x > x_lo below z_step) with staggered caps per layer."""
    # the skin is open at the mouth; rejoin it with the lining so it is closed
    skin, cav = objs["GH_Skin"], objs["GH_MouthCavity"]
    bm = bmesh.new()
    bm.from_mesh(skin.data)
    bm.from_mesh(cav.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
    me = bpy.data.meshes.new("GH_Skin_cut")
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    joined = bpy.data.objects.new("GH_Skin_cut", me)
    ghc.get_collection(COLLECTION).objects.link(joined)
    joined.data.materials.append(skin.data.materials[0])
    skin.hide_render = cav.hide_render = True
    layers = {"GH_Skin_cut": 0, "GH_Muscle": 1, "GH_Skull": 2, "GH_Jaw": 2, "GH_Eye_L": 2,
              "GH_Gums": 2, "GH_Brain": 3, "GH_Teeth_Upper": 3, "GH_Teeth_Lower": 3, "GH_Tongue": 3}
    obs = dict(objs)
    obs["GH_Skin_cut"] = joined
    for name, lvl in layers.items():
        # an L-shaped prism (profile in x/z, extruded along y): removes x > x_hi
        # everywhere and x > x_lo below z_step; inner layers are cut slightly
        # further out so their caps sit in front of the outer layers' caps
        off = 0.0006 * lvl
        prof = [(x_lo + off, -1.0), (1.0, -1.0), (1.0, 1.0), (x_hi + off, 1.0),
                (x_hi + off, z_step), (x_lo + off, z_step)]
        n = len(prof)
        verts = [(px, -1.0, pz) for px, pz in prof] + [(px, 1.0, pz) for px, pz in prof]
        faces = [tuple(range(n)), tuple(range(2 * n - 1, n - 1, -1))]
        faces += [(i, (i + 1) % n, n + (i + 1) % n, n + i)[::-1] for i in range(n)]
        cm = bpy.data.meshes.new(f"cut_{name}")
        cm.from_pydata(verts, [], faces)
        cm.validate()
        cutter = bpy.data.objects.new(f"cut_{name}", cm)
        ghc.get_collection("Stage").objects.link(cutter)
        cutter.hide_render = True
        cutter.hide_viewport = True
        mod = obs[name].modifiers.new("cutaway", 'BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.solver = 'MANIFOLD'
        mod.object = cutter


def _render_tests(objs):
    out = ghc.RENDER_DIR
    bpy.context.scene.view_settings.exposure = -0.4
    ghc.render_views("anatomy", ("front", "three_q", "side"), out, samples=40, res=(640, 640))
    _cutaway(objs)
    cam = ghc.add_camera("GH_Cam_cutaway", (0.60, -0.42, 0.06), (0.0, -0.025, -0.01), 85.0)
    ghc.render(os.path.join(out, "anatomy_cutaway.png"), cam, 40, (640, 640))


if __name__ == "__main__":
    ghc.reset_scene()
    ghc.ensure_controls()
    parts = build_anatomy()
    print("\nLandmarks:")
    for k, v in ANATOMY_LANDMARKS.items():
        print(f"  {k:22s} {v}")
    lookdev_materials(parts)
    check_report(parts)
    _render_tests(parts)
