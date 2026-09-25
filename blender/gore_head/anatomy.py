"""Procedural human head anatomy for the gore head (Blender 5.x).

Builds every anatomical layer of the head from code: skin, soft tissue
(muscle), skull, mandible, brain, eyes, teeth, gums, tongue and the mouth
lining.  No downloaded data of any kind is used.

Technique
---------
Every organic shape is written as a signed distance function (SDF) in numpy
(negative inside), in the spirit of Inigo Quilez' SDF modelling: ellipsoids,
tapered capsules and swept tubes combined with smooth unions/subtractions.
An SDF is polygonised with a sparse two-level grid and a vectorised
*surface nets* mesher, cleaned with Blender's voxel remesher and finally every
vertex is projected back onto the exact iso-surface with a few Newton steps,
so features smaller than the voxel size (lid margins, lip borders, ear folds)
survive.  Teeth are small deformed quad spheres instead, one closed island per
tooth.

Space: metres, Z up, the face looks toward -Y, origin between the ear canals
(see CONTRACT.md).  Character's left is +X.

Run ``python3 anatomy.py`` for test renders and an interpenetration report.
"""
import math
import os
import sys
import time

import numpy as np

import bpy
from mathutils import Matrix, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_common as ghc  # noqa: E402

COLLECTION = "GoreHead"

# ---------------------------------------------------------------------------
# Landmarks (metres).  Mirrored features are given for the left (+X) side.
# ---------------------------------------------------------------------------
EYE_C = np.array([0.032, -0.070, 0.022])
EYE_R = 0.012

ANATOMY_LANDMARKS = {}  # filled in by _collect_landmarks() after building


# ---------------------------------------------------------------------------
# SDF toolkit.  Points are passed as three flat float64 arrays (x, y, z).
# ---------------------------------------------------------------------------
def smin(a, b, k):
    """Polynomial smooth minimum (smooth union) with blend radius k."""
    if k <= 0.0:
        return np.minimum(a, b)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


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


def sd_polyline(x, y, z, pts, radii):
    """Tube swept along a polyline, radius interpolated per vertex.

    Returns (distance, t) where t in [0, 1] is the arc parameter of the
    closest point, useful for shaping along the curve.
    """
    pts = np.asarray(pts, float)
    radii = np.asarray(radii, float)
    seg_len = np.linalg.norm(pts[1:] - pts[:-1], axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg_len)]) / max(seg_len.sum(), 1e-9)
    best = np.full(x.shape, 1e9)
    best_t = np.zeros(x.shape)
    for i in range(len(pts) - 1):
        h, d = seg_param(x, y, z, pts[i], pts[i + 1])
        d = d - (radii[i] + (radii[i + 1] - radii[i]) * h)
        m = d < best
        best = np.where(m, d, best)
        best_t = np.where(m, cum[i] + (cum[i + 1] - cum[i]) * h, best_t)
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
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Region:
    """Axis-aligned box used to evaluate a feature only where it matters."""

    def __init__(self, lo, hi):
        self.lo = np.asarray(lo, float)
        self.hi = np.asarray(hi, float)

    def mask(self, x, y, z):
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
    near = cmin < 1.3 * H
    dil = near.copy()
    for ax in range(3):
        sl_a = [slice(None)] * 3
        sl_b = [slice(None)] * 3
        sl_a[ax] = slice(1, None)
        sl_b[ax] = slice(None, -1)
        dil[tuple(sl_a)] |= near[tuple(sl_b)]
        dil[tuple(sl_b)] |= near[tuple(sl_a)]
    nf = (nc - 1) * ratio + 1
    ci = [np.minimum(np.arange(nf[i]) // ratio, nc[i] - 2) for i in range(3)]
    ni = [np.minimum((np.arange(nf[i]) + ratio // 2) // ratio, nc[i] - 1) for i in range(3)]
    F = Fc[np.ix_(ni[0], ni[1], ni[2])].astype(np.float32)
    mask = dil[np.ix_(ci[0], ci[1], ci[2])]
    ii, jj, kk = np.nonzero(mask)
    pts = np.stack([lo[0] + h * ii, lo[1] + h * jj, lo[2] + h * kk], 1)
    F[ii, jj, kk] = eval_points(fn, pts)
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
    v = np.empty(len(me.vertices) * 3, np.float32)
    me.vertices.foreach_get('co', v)
    return v.reshape(-1, 3).astype(np.float64)


def set_verts(me, v):
    me.vertices.foreach_set('co', np.asarray(v, np.float32).ravel())
    me.update()


def project_to_surface(fn, v, h, iters=3):
    """Newton-project points onto the zero level set of fn."""
    e = 0.25 * h
    offs = np.array([[e, 0, 0], [-e, 0, 0], [0, e, 0], [0, -e, 0], [0, 0, e], [0, 0, -e]])
    for _ in range(iters):
        allp = np.concatenate([v] + [v + o for o in offs])
        f = eval_points(fn, allp).reshape(7, -1)
        g = np.stack([(f[1] - f[2]), (f[3] - f[4]), (f[5] - f[6])], 1) / (2 * e)
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


def mesh_sdf(name, fn, lo, hi, h, voxel=None, project=2, relax=0, collection=None):
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
