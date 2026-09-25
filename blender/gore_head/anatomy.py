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


def ellipse2(a, b, ra, rb):
    """2D ellipse distance approximation (IQ bound) for arrays a, b."""
    k0 = np.sqrt((a / ra) ** 2 + (b / rb) ** 2)
    k1 = np.sqrt((a / ra ** 2) ** 2 + (b / rb ** 2) ** 2) + 1e-12
    return k0 * (k0 - 1.0) / k1


def extrude(d2, dz, half, rnd=0.0):
    """Extrude a 2D distance d2 along an axis with half height `half` and rounding."""
    wx = d2 + rnd
    wy = np.abs(dz) - half + rnd
    return (np.minimum(np.maximum(wx, wy), 0.0)
            + np.sqrt(np.maximum(wx, 0) ** 2 + np.maximum(wy, 0) ** 2) - rnd)


# ---------------------------------------------------------------------------
# Skin
# ---------------------------------------------------------------------------
# Eye opening, in angles around the eyeball centre: u = horizontal angle
# (positive = lateral), v = elevation.  M = medial canthus, L = lateral canthus.
LID_UM, LID_VM = -1.12, -0.05
LID_UL, LID_VL = 1.22, 0.07
LID_UP, LID_LO = 0.47, 0.54          # lid arc heights (rad) above/below the canthal line
LID_R = 0.0148                        # outer radius of the eyelid shell
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
    # upper lid peaks slightly medial, lower lid slightly lateral
    up = base + LID_UP * np.clip(st, 0, 1) ** 0.75 * (1.0 + 0.10 * (0.5 - t))
    lo = base - LID_LO * np.clip(st, 0, 1) ** 1.05 * (1.0 - 0.12 * (0.5 - t))
    return t, st, up, lo


def _eye_region(d, ax, y, z):
    """Orbit, eyelids, lid opening, lid crease and eyeball cavity."""
    qx, qy, qz = ax - EYE_C[0], y - EYE_C[1], z - EYE_C[2]
    r = np.sqrt(qx * qx + qy * qy + qz * qz)
    # eyelid shell hugging the globe
    d = smin(d, r - LID_R, 0.0045)
    u = np.arctan2(qx, -qy)
    v = np.arctan2(qz, np.sqrt(qx * qx + qy * qy))
    t, st, up, lo = _lid_curves(u)
    rr = np.maximum(r, EYE_R)
    # upper lid crease (supratarsal fold) and a faint lower lid fold
    crease_v = up + 0.36 * st ** 0.6
    g = np.exp(-(((v - crease_v) * rr) / 0.0009) ** 2) * smoothstep(0.1, 0.45, st)
    g2 = np.exp(-(((v - (lo - 0.30 * st ** 0.7)) * rr) / 0.0013) ** 2) * smoothstep(0.2, 0.6, st)
    band = smoothstep(0.024, 0.016, r)
    d = d + (0.00055 * g + 0.00025 * g2) * band
    # palpebral opening: a cone around the eye centre, limited in radius
    dopen = np.maximum(np.maximum(v - up, lo - v),
                       (np.abs(t - 0.5) - 0.5) * (LID_UL - LID_UM)) * rr
    cut = np.maximum(dopen, r - 0.0195)
    d = smax(d, -cut, 0.0010)
    # eyeball + cornea cavity (keeps the lids EYE_GAP off the eye)
    cav = np.minimum(r - (EYE_R + EYE_GAP),
                     np.sqrt(qx * qx + (qy + CORNEA_OFF) ** 2 + qz * qz) - (CORNEA_R + EYE_GAP))
    d = np.maximum(d, -cav)
    return d


def _nose(d, ax, y, z):
    """Nasal dorsum, tip, alae, columella and nostrils."""
    body = sd_ellipsoid(ax, y, z, (0.0, -0.0905, -0.002), (0.0095, 0.0115, 0.026),
                        rot=rot_xyz(-24, 0, 0))
    dors = sd_capsule(ax, y, z, (0.0, -0.0858, 0.021), (0.0, -0.1047, -0.0045), 0.0046, 0.0058)
    tip = sd_ellipsoid(ax, y, z, (0.0, -0.1035, -0.0125), (0.0090, 0.0085, 0.0082))
    dome = sd_sphere(ax, y, z, (0.0036, -0.1063, -0.0112), 0.0050)
    colu = sd_capsule(ax, y, z, (0.0, -0.1040, -0.0195), (0.0, -0.0968, -0.0262), 0.0030, 0.0034)
    ala = sd_ellipsoid(ax, y, z, (0.0138, -0.0922, -0.0183), (0.0072, 0.0092, 0.0066),
                       rot=rot_xyz(0, 0, 22))
    n = smin(body, dors, 0.006)
    n = smin(n, tip, 0.006)
    n = smin(n, dome, 0.003)
    n = smin(n, colu, 0.003)
    n = smin(n, ala, 0.0025)
    d = smin(d, n, 0.0035)
    # nostrils: oval openings on the underside running up into the nose
    nos = sd_ellipsoid(ax, y, z, (0.0063, -0.0990, -0.0228), (0.0031, 0.0058, 0.0040),
                       rot=rot_xyz(12, 0, -20))
    nos = smin(nos, sd_capsule(ax, y, z, (0.0065, -0.0985, -0.021), (0.0085, -0.0915, -0.009),
                               0.0027, 0.0020), 0.002)
    d = smax(d, -nos, 0.0012)
    return d


def _lip_tube(ax, y, z, yc0, yc2, zc0, zc2, r0, rexp=0.7, half_w=0.0255, n=15):
    """Lip as a tube along the mouth arc; radius tapers to the corners."""
    s = np.linspace(0.0, 1.0, n)
    pts = np.stack([half_w * s, yc0 + yc2 * s ** 2, zc0 + zc2 * s ** 2], 1)
    rad = 0.0010 + r0 * (1.0 - s ** 2) ** rexp
    d, _ = sd_polyline(ax, y, z, pts, rad)
    return d


def _mouth(d, ax, y, z):
    """Lips, philtrum, mouth opening, nasolabial and labiomental folds."""
    mound = sd_ellipsoid(ax, y, z, (0.0, -0.0790, -0.0505), (0.030, 0.0185, 0.026))
    d = smin(d, mound, 0.012)
    # cheek fat lateral of the nasolabial fold
    cheek = sd_ellipsoid(ax, y, z, (0.037, -0.0735, -0.029), (0.013, 0.0120, 0.021),
                         rot=rot_xyz(0, 0, 20))
    d = smin(d, cheek, 0.009)
    fold, _ = sd_polyline(ax, y, z, [(0.0195, -0.0890, -0.0205), (0.0245, -0.0878, -0.0330),
                                     (0.0285, -0.0850, -0.0460), (0.0312, -0.0808, -0.0580),
                                     (0.0322, -0.0765, -0.0680)],
                          [0.0010, 0.0013, 0.0013, 0.0011, 0.0006])
    d = smax(d, -fold, 0.0035)
    # philtral columns and groove
    col = sd_capsule(ax, y, z, (0.0043, -0.0985, -0.0433), (0.0034, -0.0968, -0.0290), 0.0013)
    d = smin(d, col, 0.0022)
    grv = sd_capsule(ax, y, z, (0.0, -0.0998, -0.0425), (0.0, -0.0985, -0.0305), 0.0016)
    d = smax(d, -grv, 0.0018)
    upper = _lip_tube(ax, y, z, -0.0962, 0.0122, -0.0467, -0.0045, 0.0038)
    lower = _lip_tube(ax, y, z, -0.0914, 0.0096, -0.0645, 0.0075, 0.0048)
    d = smin(d, upper, 0.0028)
    d = smin(d, lower, 0.0030)
    # labiomental fold under the lower lip
    lm = sd_capsule(ax, y, z, (0.0, -0.0905, -0.0765), (0.013, -0.0870, -0.0740), 0.0012)
    d = smax(d, -lm, 0.0045)
    # mouth slit between the lips (lens shaped, closing at the corners)
    xs = np.clip(ax / 0.0250, 0.0, 1.5)
    zhi = -0.0516 - 0.0030 * xs ** 2
    zlo = -0.0584 + 0.0028 * xs ** 2
    slot = np.maximum(np.maximum(z - zhi, zlo - z), np.maximum(ax - 0.0250, y + 0.070))
    slot = np.maximum(slot, -0.12 - y)
    d = smax(d, -slot, 0.0014)
    return d


def oral_void(ax, y, z):
    """The mouth cavity (vestibule + oral cavity proper), negative inside."""
    front = extrude(ellipse2(ax, y + 0.0700, 0.0265, 0.0205), z + 0.0565, 0.0150, 0.0060)
    back = sd_box(ax, y, z, (0.0, -0.0500, -0.0565), (0.0315, 0.0240, 0.0150), round_=0.0080)
    v = smin(front, back, 0.010)
    vault = sd_ellipsoid(ax, y, z, (0.0, -0.0520, -0.0440), (0.0160, 0.0280, 0.0085))
    return smin(v, vault, 0.008)


def _ear(ax, y, z):
    """Auricle: helix, antihelix with crura, concha, tragus, antitragus, lobe."""
    px, py, pz = ax - EAR_O[0], y - EAR_O[1], z - EAR_O[2]
    s = px * EAR_U[0] + py * EAR_U[1] + pz * EAR_U[2]
    t = px * EAR_V[0] + py * EAR_V[1] + pz * EAR_V[2]
    n = px * EAR_W[0] + py * EAR_W[1] + pz * EAR_W[2]
    zero = np.zeros_like(s)

    def P(pts, nz):
        return [(a, b, nz) for a, b in pts]

    # cartilage plate following the ear outline
    outline = smin(ellipse2(s - 0.0115, t - 0.0045, 0.0142, 0.0262),
                   ellipse2(s - 0.0088, t + 0.0200, 0.0085, 0.0095), 0.006)
    nm = 0.0008 * (s / 0.02)  # plate slightly cupped outward toward the back
    plate = np.maximum(outline + 0.0012, np.abs(n - nm) - 0.0016)
    block = sd_ellipsoid(s, t, n, (0.0065, 0.0005, -0.0045), (0.0100, 0.0125, 0.0070))
    e = smin(plate, block, 0.004)
    # concha bowl
    bowl = sd_ellipsoid(s, t, n, (0.0068, 0.0012, 0.0050), (0.0072, 0.0095, 0.0078))
    e = smax(e, -bowl, 0.0015)
    # helix rim (starts as the crus inside the concha)
    hel = catmull([(0.0060, 0.0072), (0.0010, 0.0112), (-0.0022, 0.0185), (0.0012, 0.0268),
                   (0.0082, 0.0312), (0.0168, 0.0306), (0.0232, 0.0238), (0.0264, 0.0128),
                   (0.0258, 0.0008), (0.0224, -0.0090), (0.0172, -0.0158)], 5)
    k = np.linspace(0, 1, len(hel))
    hrad = 0.0014 + 0.0014 * smoothstep(0.0, 0.25, k) - 0.0008 * smoothstep(0.75, 1.0, k)
    hn = 0.0006 + 0.0006 * smoothstep(0.0, 0.3, k)
    hel3 = np.column_stack([hel, hn])
    h, _ = sd_polyline(s, t, n, hel3, hrad)
    e = smin(e, h, 0.0012)
    # antihelix with superior and inferior crura
    ah = catmull([(0.0122, -0.0082), (0.0158, -0.0010), (0.0168, 0.0068), (0.0148, 0.0138),
                  (0.0134, 0.0198), (0.0142, 0.0248)], 4)
    ah3 = np.column_stack([ah, np.full(len(ah), 0.0012)])
    a1, _ = sd_polyline(s, t, n, ah3, np.linspace(0.0021, 0.0013, len(ah)))
    ic = catmull([(0.0150, 0.0135), (0.0095, 0.0162), (0.0040, 0.0168)], 4)
    ic3 = np.column_stack([ic, np.full(len(ic), 0.0010)])
    a2, _ = sd_polyline(s, t, n, ic3, np.linspace(0.0016, 0.0010, len(ic)))
    e = smin(e, smin(a1, a2, 0.001), 0.0014)
    # tragus, antitragus, lobe
    trag = sd_ellipsoid(s, t, n, (-0.0030, -0.0012, 0.0006), (0.0036, 0.0048, 0.0034))
    anti = sd_ellipsoid(s, t, n, (0.0108, -0.0092, 0.0010), (0.0034, 0.0027, 0.0026))
    lobe = sd_ellipsoid(s, t, n, (0.0088, -0.0205, 0.0002), (0.0082, 0.0090, 0.0030))
    e = smin(e, trag, 0.0015)
    e = smin(e, anti, 0.0015)
    e = smin(e, lobe, 0.004)
    # triangular fossa and scapha get a touch deeper
    tri = sd_ellipsoid(s, t, n, (0.0092, 0.0205, 0.0030), (0.0030, 0.0035, 0.0022))
    e = smax(e, -tri, 0.001)
    # ear canal
    canal = sd_capsule(s, t, n, (0.0012, -0.0006, 0.0010), (0.0010, -0.0010, -0.0120), 0.0032, 0.0026)
    e = smax(e, -canal, 0.0012)
    del zero
    return e


def skin_sdf(x, y, z):
    """Signed distance to the outer skin (head + neck), negative inside."""
    ax = np.abs(x)
    # cranium + fuller, upright forehead
    d = sd_ellipsoid(ax, y, z, (0.0, 0.004, 0.030), (0.0740, 0.0970, 0.0950))
    d = smin(d, sd_ellipsoid(ax, y, z, (0.0, -0.040, 0.060), (0.0570, 0.0500, 0.0530)), 0.02)
    # temples: slight hollow in front of the temporalis
    d = smax(d, -sd_ellipsoid(ax, y, z, (0.0700, -0.058, 0.030), (0.0100, 0.0180, 0.0180)), 0.012)
    # midface, cheekbones, jaw, chin
    face = sd_ellipsoid(ax, y, z, (0.0, -0.050, -0.018), (0.0540, 0.0440, 0.0460))
    d = smin(d, face, 0.025)
    cb = sd_ellipsoid(ax, y, z, (0.0470, -0.0620, 0.0000), (0.0200, 0.0180, 0.0135),
                      rot=rot_xyz(0, 0, -25))
    d = smin(d, cb, 0.012)
    jfill = sd_ellipsoid(ax, y, z, (0.0, -0.040, -0.062), (0.0470, 0.0480, 0.0400))
    d = smin(d, jfill, 0.02)
    jaw, _ = sd_polyline(ax, y, z, [(0.012, -0.0780, -0.0970), (0.030, -0.0600, -0.0920),
                                    (0.046, -0.0300, -0.0830), (0.0520, -0.0080, -0.0700),
                                    (0.0560, -0.0040, -0.0450), (0.0600, -0.0040, -0.0200)],
                         [0.011, 0.011, 0.011, 0.010, 0.011, 0.011])
    d = smin(d, jaw, 0.012)
    chin = sd_ellipsoid(ax, y, z, (0.0, -0.0790, -0.0930), (0.0190, 0.0135, 0.0150))
    d = smin(d, chin, 0.012)
    # neck, sternocleidomastoids, larynx
    ny = (y - 0.016) * (0.055 / 0.050)
    neck = sd_capsule(ax, ny, z, (0.0, 0.004, -0.26), (0.0, -0.004, -0.060), 0.055)
    d = smin(d, neck, 0.02)
    scm = sd_capsule(ax, y, z, (0.052, 0.022, -0.035), (0.012, -0.030, -0.195), 0.0090, 0.0085)
    d = smin(d, scm, 0.012)
    d = smin(d, sd_ellipsoid(ax, y, z, (0.0, -0.036, -0.135), (0.0085, 0.0080, 0.0120)), 0.010)
    # brow ridge
    brow, _ = sd_polyline(ax, y, z, [(0.000, -0.0865, 0.0355), (0.014, -0.0858, 0.0375),
                                     (0.028, -0.0830, 0.0385), (0.041, -0.0775, 0.0370),
                                     (0.052, -0.0670, 0.0320)],
                          [0.0065, 0.0065, 0.0060, 0.0055, 0.0050])
    d = smin(d, brow, 0.010)
    # orbital hollow
    d = smax(d, -sd_ellipsoid(ax, y, z, (0.0320, -0.0880, 0.0200), (0.0180, 0.0130, 0.0130)), 0.008)
    # local detail regions
    d = apply_local(d, ax, y, z, Region((0.0, -0.13, -0.045), (0.035, -0.07, 0.035)),
                    lambda dd, a, b, c: _nose(dd, a, b, c))
    d = apply_local(d, ax, y, z, Region((0.0, -0.13, -0.095), (0.050, -0.055, -0.010)),
                    lambda dd, a, b, c: _mouth(dd, a, b, c))
    d = apply_local(d, ax, y, z, Region((0.004, -0.105, -0.010), (0.062, -0.045, 0.055)),
                    lambda dd, a, b, c: _eye_region(dd, a, b, c))
    d = apply_local(d, ax, y, z, Region((0.050, -0.025, -0.045), (0.105, 0.050, 0.050)),
                    lambda dd, a, b, c: smin(dd, _ear(a, b, c), 0.0022))
    # mouth cavity
    d = apply_local(d, ax, y, z, Region((0.0, -0.10, -0.085), (0.048, -0.015, -0.025)),
                    lambda dd, a, b, c: np.maximum(dd, -oral_void(a, b, c)))
    # flat cut at the bottom of the neck
    return np.maximum(d, -0.20 - z)


SKIN_BOX = ((-0.105, -0.125, -0.205), (0.105, 0.115, 0.135))
