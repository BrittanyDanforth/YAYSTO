"""Skeleton, fracture variants and bone capsules (owner B3).  Plan D5, §3.3.5, §5.2, §8.2 B3.

Final entry points
------------------
``build_skeleton()``            -> {"GB_Skeleton": obj, "GB_Skeleton_HR": obj}
                                   UV2 = (bone piece id, bone class); every piece rigid to one rig bone
                                   (hands/feet per sub-bone); long bones as double shells
``build_fracture_variants()``   -> {"GB_Frac_*": obj} (gb_common.VARIANT_OBJECTS); fragments are
                                   closed loose islands with real fracture faces
``bone_capsules()``             -> list of ~60 broad-phase hit capsules {"piece", "bone", "a", "b", "r"}
``bone_table()``                -> ``bones.json`` data (pieces, capsules, exact-hit mesh, variants)

How the bones are made
----------------------
Every bone is a numpy signed-distance field (negative inside) in the body frame
(metres, +Z up, face -Y, character's left +X), polygonised by the head
project's surface nets with Newton projection onto the exact surface (the
same toolkit as the head: ``gore_head/anatomy.py``, imported read-only).  The
left side is authored and mirrored.  Shapes follow the bible tables
[RB §7.3]: vertebra body sizes, canals and spinous offsets from the CSV in
per-level frames that follow the spinal curve; ribs, cartilages and sternum
from the rib table; long bones at the joint centres of the rig table
[RB §7.2] with bible lengths, shaft diameters and cortex thickness.  Skull and
mandible are the head project's own bones, re-imported at every build.

Double shells.  Long bones (femur, tibia, fibula, humerus, radius, ulna,
clavicle) carry a second closed surface, the **marrow core** (the endosteal
surface of the medullary canal, normals outward, bone class 6
``marrow``).  A discard hole through the periosteal surface therefore shows
the cortex ring (outer shell back faces, cortical-cut colour) around the
marrow (the core's faces).  Flat bones, vertebrae and the skull are single
closed shells whose back faces render as red marrow / diploe (plan §3.3.6).

LOD0 vs HR.  ``GB_Skeleton_HR`` (GB_HighRes, bake source, never exported)
keeps the full surface-net resolution (0.6-1.3 mm); ``GB_Skeleton`` is
decimated per piece to the plan §4.1 budget (36k triangles: skull 12k,
spine 6.5k, ribs 5k, pelvis 3k, limbs 8k, rest).

Run alone::

    python3 skeleton.py [--quick] [--only femur_L,c5] [--render] [--variants]
"""
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import bones as BN  # noqa: E402
from gb_data import landmarks as LM  # noqa: E402
from gb_data import ribs as RB_  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402
from gb_data import vertebrae as VT  # noqa: E402

HEAD_OFFSET = gbc.HEAD_OFFSET
ARM_D = np.array(LM.ARM_DIRECTION_L, float)            # A-pose arm direction (left, distal)
ARM_NM = np.array(LM.ARM_MEDIAL_NORMAL_L, float)       # palm-side (medial) normal
ARM_LAT = -ARM_NM                                      # lateral (dorsal in the neutral forearm)
EX, EY, EZ = np.eye(3)
ANT = -EY                                              # anterior

MARROW_CLASS = 6                                       # bone class of the marrow core (gb_data.bones.BONE_CLASS)
CARTILAGE_SLOT = 1                                     # material slot GBM_cartilage


def _A():
    """The head project's SDF toolkit (read-only import)."""
    return gbc.import_head().anatomy


def _quick():
    return "--quick" in gbc.script_args()


def _n(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


# ===========================================================================
# SDF helpers (flat numpy arrays x, y, z; negative inside)
# ===========================================================================
def smin(a, b, k):
    return _A().smin(a, b, k)


def smax(a, b, k):
    return _A().smax(a, b, k)


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


class Frame:
    """Orthonormal frame (origin ``c``, rows ``R`` = local x, y, z axes in world coords)."""

    def __init__(self, c, ax, ay=None, az=None):
        self.c = np.asarray(c, float)
        ax = _n(ax)
        if ay is None:
            az = _n(az)
            ay = np.cross(az, ax)
        ay = np.asarray(ay, float)
        ay = _n(ay - (ay @ ax) * ax)
        self.R = np.array([ax, ay, np.cross(ax, ay)])

    def local(self, x, y, z):
        dx, dy, dz = x - self.c[0], y - self.c[1], z - self.c[2]
        R = self.R
        return (R[0, 0] * dx + R[0, 1] * dy + R[0, 2] * dz,
                R[1, 0] * dx + R[1, 1] * dy + R[1, 2] * dz,
                R[2, 0] * dx + R[2, 1] * dy + R[2, 2] * dz)

    def world(self, p):
        return self.c + np.asarray(p, float) @ self.R


def ell3(x, y, z, c, r, axes=None):
    """Ellipsoid (IQ bound) with semi-axes ``r`` along ``axes`` (rows, default world)."""
    if axes is None:
        return _A().sd_ellipsoid(x, y, z, c, r)
    dx, dy, dz = x - c[0], y - c[1], z - c[2]
    A = np.asarray(axes, float)
    lx = A[0, 0] * dx + A[0, 1] * dy + A[0, 2] * dz
    ly = A[1, 0] * dx + A[1, 1] * dy + A[1, 2] * dz
    lz = A[2, 0] * dx + A[2, 1] * dy + A[2, 2] * dz
    return _A().sd_ellipsoid(lx, ly, lz, (0.0, 0.0, 0.0), r)


def sphere(x, y, z, c, r):
    return _A().sd_sphere(x, y, z, c, r)


def ecap(x, y, z, a, b, r1, r2, ref):
    """Capsule a -> b with an elliptical section: radius ``r1`` (at a, at b) along ``ref``
    (orthogonalised to the axis) and ``r2`` along the third axis.  Ends are elliptical caps."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    ab = b - a
    L2 = float(ab @ ab)
    u = ab / math.sqrt(L2)
    e1 = np.asarray(ref, float) - (np.asarray(ref, float) @ u) * u
    e1 = e1 / np.linalg.norm(e1)
    e2 = np.cross(u, e1)
    dx, dy, dz = x - a[0], y - a[1], z - a[2]
    t = (dx * ab[0] + dy * ab[1] + dz * ab[2]) / L2
    h = np.clip(t, 0.0, 1.0)
    ex, ey, ez = dx - ab[0] * h, dy - ab[1] * h, dz - ab[2] * h
    c1 = ex * e1[0] + ey * e1[1] + ez * e1[2]
    c2 = ex * e2[0] + ey * e2[1] + ez * e2[2]
    ca = (ex * u[0] + ey * u[1] + ez * u[2])
    ra = np.asarray(r1, float)
    rb = np.asarray(r2, float)
    R1 = ra[0] + (ra[-1] - ra[0]) * h
    R2 = rb[0] + (rb[-1] - rb[0]) * h
    # ellipsoidal end caps: scale the axial overshoot by the smaller radius
    k0 = np.sqrt((c1 / R1) ** 2 + (c2 / R2) ** 2 + (ca / np.minimum(R1, R2)) ** 2)
    return (k0 - 1.0) * np.minimum(R1, R2)


def ebox(x, y, z, c, half, axes, rnd=0.0):
    """Rounded box with half extents along ``axes`` (rows)."""
    dx, dy, dz = x - c[0], y - c[1], z - c[2]
    A = np.asarray(axes, float)
    lx = A[0, 0] * dx + A[0, 1] * dy + A[0, 2] * dz
    ly = A[1, 0] * dx + A[1, 1] * dy + A[1, 2] * dz
    lz = A[2, 0] * dx + A[2, 1] * dy + A[2, 2] * dz
    return _A().sd_box(lx, ly, lz, (0.0, 0.0, 0.0), half, round_=rnd)


def plane(x, y, z, p0, n):
    """Signed distance to a plane (positive on the side ``n`` points to)."""
    n = _n(n)
    return (x - p0[0]) * n[0] + (y - p0[1]) * n[1] + (z - p0[2]) * n[2]


def poly2d(u, v, P):
    """Signed distance to a closed (possibly concave) polygon ``P`` (K, 2); negative inside."""
    P = np.asarray(P, float)
    d = (u - P[0, 0]) ** 2 + (v - P[0, 1]) ** 2
    s = np.ones_like(u)
    K = len(P)
    j = K - 1
    for i in range(K):
        ex, ey = P[j, 0] - P[i, 0], P[j, 1] - P[i, 1]
        wx, wy = u - P[i, 0], v - P[i, 1]
        t = np.clip((wx * ex + wy * ey) / (ex * ex + ey * ey), 0.0, 1.0)
        bx, by = wx - ex * t, wy - ey * t
        d = np.minimum(d, bx * bx + by * by)
        c1 = v >= P[i, 1]
        c2 = v < P[j, 1]
        c3 = ex * wy > ey * wx
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        s = np.where(flip, -s, s)
        j = i
    return s * np.sqrt(d)


def _hash01(ix, iy, iz, seed):
    h = (ix.astype(np.int64) * 73856093) ^ (iy.astype(np.int64) * 19349663) ^ \
        (iz.astype(np.int64) * 83492791) ^ np.int64(seed)
    h = h.astype(np.uint64)
    h ^= h >> np.uint64(13)
    h *= np.uint64(0x5bd1e995)
    h ^= h >> np.uint64(15)
    return (h & np.uint64(0xFFFFFF)).astype(np.float64) / float(0xFFFFFF)


def vnoise(x, y, z, freq, seed=0):
    """Smooth value noise in [-1, 1] (trilinear with smoothstep), deterministic."""
    px, py, pz = x * freq, y * freq, z * freq
    ix, iy, iz = np.floor(px), np.floor(py), np.floor(pz)
    fx, fy, fz = px - ix, py - iy, pz - iz
    fx, fy, fz = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy), fz * fz * (3 - 2 * fz)
    out = 0.0
    for dx in (0, 1):
        wx = fx if dx else 1 - fx
        for dy in (0, 1):
            wy = fy if dy else 1 - fy
            for dz in (0, 1):
                wz = fz if dz else 1 - fz
                out = out + wx * wy * wz * _hash01(ix + dx, iy + dy, iz + dz, seed)
    return 2.0 * out - 1.0


def fbm(x, y, z, freq, octaves=3, seed=0):
    """Fractal value noise, amplitude ~1."""
    out, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        out = out + amp * vnoise(x, y, z, freq * (2.03 ** o), seed + 101 * o)
        tot += amp
        amp *= 0.5
    return out / tot


class Tube:
    """Swept solid along a smooth centreline with a per-station 2D section.

    ``sec(n, b, t)`` returns the 2D signed distance of a point with section
    coordinates (n along the frame's N axis, b along B) at arc parameter t
    (0..1).  Frames: N follows ``ref_fn(P)`` (preferred direction per sample,
    orthogonalised) or parallel transport.  Ends are flat (use ``caps`` to
    round them with the section's size)."""

    def __init__(self, pts, sec, ref_fn=None, step=0.002, smooth=True, round_ends=True):
        P = np.asarray(pts, float)
        if smooth and len(P) > 2:
            P = _A().catmull(P, n=10)
        seg = np.linalg.norm(np.diff(P, axis=0), axis=1)
        keep = np.concatenate([[True], seg > 1e-9])
        P = P[keep]
        cum = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        L = cum[-1]
        m = max(2, int(math.ceil(L / step)) + 1)
        s = np.linspace(0.0, L, m)
        P = np.stack([np.interp(s, cum, P[:, i]) for i in range(3)], axis=1)
        T = np.gradient(P, axis=0)
        T /= np.linalg.norm(T, axis=1, keepdims=True)
        if ref_fn is not None:
            N = np.asarray(ref_fn(P), float) * np.ones_like(P)
        else:
            N = np.zeros_like(P)
            up = EZ if abs(T[0] @ EZ) < 0.9 else EX
            N[0] = up
            for i in range(1, len(P)):
                n = N[i - 1] - (N[i - 1] @ T[i]) * T[i]
                N[i] = n / np.linalg.norm(n)
        N = N - (N * T).sum(1, keepdims=True) * T
        N /= np.linalg.norm(N, axis=1, keepdims=True)
        self.P, self.T, self.N, self.B = P, T, N, np.cross(T, N)
        self.t = s / L
        self.L = L
        self.sec = sec
        self.round_ends = round_ends

    def __call__(self, x, y, z):
        P, T = self.P, self.T
        best = np.full(x.shape, np.inf)
        bi = np.zeros(x.shape, np.int64)
        bh = np.zeros(x.shape)
        for i in range(len(P) - 1):
            a, ab = P[i], P[i + 1] - P[i]
            L2 = float(ab @ ab)
            dx, dy, dz = x - a[0], y - a[1], z - a[2]
            h = np.clip((dx * ab[0] + dy * ab[1] + dz * ab[2]) / L2, 0.0, 1.0)
            ex, ey, ez = dx - ab[0] * h, dy - ab[1] * h, dz - ab[2] * h
            d = ex * ex + ey * ey + ez * ez
            m = d < best
            best = np.where(m, d, best)
            bi = np.where(m, i, bi)
            bh = np.where(m, h, bh)
        i0, i1 = bi, bi + 1
        w = bh[:, None]
        C = P[i0] * (1 - w) + P[i1] * w
        N = self.N[i0] * (1 - w) + self.N[i1] * w
        B = self.B[i0] * (1 - w) + self.B[i1] * w
        Tt = T[i0] * (1 - w) + T[i1] * w
        D = np.stack([x, y, z], axis=1) - C
        n = (D * N).sum(1)
        b = (D * B).sum(1)
        ax = (D * Tt).sum(1)
        t = self.t[i0] * (1 - bh) + self.t[i1] * bh
        d2 = self.sec(n, b, t)
        end0 = (bi == 0) & (bh <= 0.0)
        end1 = (bi == len(P) - 2) & (bh >= 1.0)
        over = np.maximum(np.where(end0, -ax, np.where(end1, ax, -1.0)), 0.0)
        if self.round_ends:
            # dome of the local section size: r0 = depth of the axis inside the section
            r0 = np.maximum(-self.sec(np.zeros_like(t), np.zeros_like(t), t), 1e-5)
            dome = np.sqrt(over ** 2 + np.maximum(d2 + r0, 0.0) ** 2) - r0
            return np.where(over > 0, np.maximum(dome, d2), d2)
        return np.where(over > 0, np.sqrt(np.maximum(d2, 0.0) ** 2 + over ** 2) + np.minimum(d2, 0.0), d2)


def ell2(n, b, rn, rb):
    return _A().ellipse2(n, b, rn, rb)


def interp(t, knots, vals):
    """Piecewise-linear profile helper: ``np.interp`` with a smoothstep between knots."""
    k = np.asarray(knots, float)
    v = np.asarray(vals, float)
    i = np.clip(np.searchsorted(k, t) - 1, 0, len(k) - 2)
    u = np.clip((t - k[i]) / (k[i + 1] - k[i]), 0.0, 1.0)
    u = u * u * (3 - 2 * u)
    return v[i] + (v[i + 1] - v[i]) * u


class Sheet:
    """Thin curved plate: mid-surface ``w0(u, v)`` (thin-plate spline through 3D points) inside a
    2D outline, thickness ``thick(u, v, e)`` (e = signed distance to the outline, negative inside)."""

    def __init__(self, frame, outline3d, extra3d=(), thick=None):
        self.f = frame
        pts = np.asarray(list(outline3d) + list(extra3d), float)
        loc = np.stack(frame.local(pts[:, 0], pts[:, 1], pts[:, 2]), axis=1)
        self.outline = loc[:len(outline3d), :2]
        self.ctrl = loc[:, :2]
        self.wv = loc[:, 2]
        K = len(loc)
        r = np.linalg.norm(self.ctrl[:, None] - self.ctrl[None], axis=2)
        Phi = np.where(r > 0, r * r * np.log(np.maximum(r, 1e-12)), 0.0)
        Pm = np.hstack([np.ones((K, 1)), self.ctrl])
        M = np.zeros((K + 3, K + 3))
        M[:K, :K] = Phi + 1e-7 * np.eye(K)
        M[:K, K:] = Pm
        M[K:, :K] = Pm.T
        rhs = np.concatenate([self.wv, np.zeros(3)])
        sol = np.linalg.solve(M, rhs)
        self.wk, self.aff = sol[:K], sol[K:]
        self.thick = thick or (lambda u, v, e: 0.003)

    def w0(self, u, v):
        out = self.aff[0] + self.aff[1] * u + self.aff[2] * v
        for (cu, cv), wk in zip(self.ctrl, self.wk):
            r2 = (u - cu) ** 2 + (v - cv) ** 2
            out = out + wk * np.where(r2 > 0, 0.5 * r2 * np.log(np.maximum(r2, 1e-24)), 0.0)
        return out

    def __call__(self, x, y, z):
        u, v, w = self.f.local(x, y, z)
        e = poly2d(u, v, self.outline)
        m = self.w0(u, v)
        eps = 1e-4
        gu = (self.w0(u + eps, v) - m) / eps
        gv = (self.w0(u, v + eps) - m) / eps
        dw = np.abs(w - m) / np.sqrt(1 + gu * gu + gv * gv)
        return _sheet_combine(e, dw - 0.5 * self.thick(u, v, e))


def _sheet_combine(e, dw):
    """Intersection of the outline prism and the thickness slab with rounded rim."""
    q1, q2 = np.maximum(e, 0.0), np.maximum(dw, 0.0)
    return np.sqrt(q1 * q1 + q2 * q2) + np.minimum(np.maximum(e, dw), 0.0)


# ===========================================================================
# Spine [RB §7.3 CSV]: per-level frames that follow the curve, typical vertebrae, C1, C2,
# discs, sacrum, coccyx.  Local frame: x lateral (left), y posterior, z up along the spine.
# ===========================================================================
ROWS = VT.VERTEBRAE
ROW = VT.VERTEBRA


def spine_frame(level):
    """Frame of a vertebra: origin at the body centre, z = local up of the curve, y = posterior."""
    lv = [r["level"] for r in ROWS]
    i = lv.index(level)
    C = np.array([r["c"] for r in ROWS])
    a, b = C[max(i - 1, 0)], C[min(i + 1, len(C) - 1)]
    if level == "S1":                       # sacral slope: the S1 endplate faces up-forward ~40 deg
        up = _n((0.0, -math.sin(math.radians(38)), math.cos(math.radians(38))))
    else:
        up = _n(a - b)
    post = EY - (EY @ up) * up
    return Frame(C[i], EX, post)


def _joint_plane(upper, lower):
    """Shared facet-joint plane between two levels: (point, normal pointing to the upper level).

    Facet orientation by region [R05 §4]: cervical ~45 deg (faces up-back), thoracic ~65 deg
    (nearly coronal), lumbar clipped horizontally (sagittal facets interlock medio-laterally)."""
    fu, fl = spine_frame(upper), spine_frame(lower)
    ru, rl = ROW[upper], ROW[lower]
    up = _n(fu.R[2] + fl.R[2])
    post = _n(fu.R[1] + fl.R[1])
    zu = ru["body_h_mm"] / 2000.0
    zl = rl["body_h_mm"] / 2000.0
    mid_body = 0.5 * ((fu.c - up * zu) + (fl.c + up * zl))
    yc = 0.5 * (ru["body_d_mm"] + ru["canal_ap_mm"]) / 1000.0
    p0 = mid_body + post * yc
    ang = {"C": 45.0, "T": 65.0, "L": 0.0}[upper[0]]
    n = _n(math.cos(math.radians(ang)) * up + math.sin(math.radians(ang)) * post)
    return p0, n


def _region_params(lvl):
    """Per-region shape parameters (mm unless noted)."""
    reg = lvl[0]
    k = int(lvl[1:]) if lvl[1:].isdigit() else 0
    if reg == "C":
        return dict(n_body=2.6, back_indent=0.0, ped_w=5.0, ped_h=0.55, lam_t=4.5, lam_h=1.05,
                    tilt=0.35, sp_rx=(3.0, 2.0), sp_rz=(4.5, 3.2), drop=4.0 + (6.0 if k == 7 else 0.0),
                    tp=None, facet_x=16.5, facet_r=(5.0, 6.0, 5.5))
    if reg == "T":
        return dict(n_body=2.2, back_indent=2.0, ped_w=6.0 + 0.25 * k, ped_h=0.55, lam_t=5.5, lam_h=1.15,
                    tilt=0.55, sp_rx=(3.2, 2.4), sp_rz=(5.0, 3.6),
                    drop={1: 10, 2: 13, 3: 16, 4: 20, 5: 24, 6: 27, 7: 28, 8: 27, 9: 24, 10: 20, 11: 14,
                          12: 10}[k],
                    tp=dict(len=(38 - 1.1 * k), up=4.0, back=7.0 - 0.3 * k, r=(4.6, 5.2)),
                    facet_x=9.0 + 0.3 * k, facet_r=(4.0, 5.5, 4.0))
    return dict(n_body=2.4, back_indent=3.0, ped_w=9.0 + 1.2 * k, ped_h=0.5, lam_t=6.5, lam_h=1.0,
                tilt=0.25, sp_rx=(3.8, 3.4), sp_rz=(7.5, 9.0), drop=5.0,
                tp=dict(len={1: 30, 2: 35, 3: 42, 4: 38, 5: 36}[k], up=0.0, back=-3.0, r=(5.0, 2.2)),
                facet_x=12.0 + 1.3 * k, facet_r=(5.5, 7.0, 6.0))


def vertebra_sdf(lvl):
    """SDF (world coords) of vertebra ``lvl`` (C3-L5 typical; C1, C2 special) and its box."""
    if lvl == "C1":
        return _atlas_sdf()
    if lvl == "C2":
        return _axis_sdf()
    r = ROW[lvl]
    F = spine_frame(lvl)
    P = _region_params(lvl)
    reg = lvl[0]
    h, w, d = r["body_h_mm"] / 1e3, r["body_w_mm"] / 1e3, r["body_d_mm"] / 1e3
    cap, cw = r["canal_ap_mm"] / 1e3, r["canal_w_mm"] / 1e3
    spy = r["spinous_dy_mm"] / 1e3
    yb = 0.5 * d                                   # back of the body
    yc = yb + 0.5 * cap                            # canal centre
    pw = P["ped_w"] / 1e3
    lt = P["lam_t"] / 1e3
    lvls = [x["level"] for x in ROWS]
    i = lvls.index(lvl)
    up_pl = _joint_plane(lvls[i - 1], lvl) if i > 0 else None
    lo_pl = _joint_plane(lvl, lvls[i + 1]) if i + 1 < len(lvls) else None
    A = _A()

    def fn(x, y, z):
        lx, ly, lz = F.local(x, y, z)
        ax = np.abs(lx)
        # --- body: superellipse section with a waist, concave back (T/L), dished endplates
        zz = np.clip(2.0 * lz / h, -1.5, 1.5)
        s = 1.0 - 0.07 * (1.0 - np.minimum(zz * zz, 1.0))
        sec = gg_superellipse(ax, ly, 0.5 * w * s, 0.5 * d * s, P["n_body"])
        if P["back_indent"] > 0:
            R = 0.9 * w
            ind = -(np.sqrt(ax * ax + (ly - (yb + R - P["back_indent"] / 1e3)) ** 2) - R)
            sec = smax(sec, ind, 0.002)
        if reg == "T":                           # heart shape: narrower in front
            sec = sec + 0.0025 * sstep(0.0, -0.5 * d, ly) * (ax / (0.5 * w))
        rr = np.clip((ax / (0.5 * w)) ** 2 + (ly / (0.5 * d)) ** 2, 0.0, 1.0)
        hh = 0.5 * h - 0.0009 * (1.0 - rr)            # endplate dish, rim (ring apophysis) intact
        body = A.extrude(sec, lz, hh, 0.0014)
        if reg == "C":                           # uncinate processes: lips on the upper lateral rims
            unc = A.sd_ellipsoid(ax, ly, lz, (0.5 * w - 0.0012, 0.0015, 0.5 * h), (0.0016, 0.35 * d, 0.0028))
            body = smin(body, unc, 0.0015)
        # --- neural arch: pedicles (lateral walls) + laminae (roof) as a ring around the canal
        lzs = lz + P["tilt"] * np.maximum(ly - yc, 0.0)          # laminae shingle downward behind
        ring_o = A.ellipse2(ax, ly - yc, 0.5 * cw + pw, 0.5 * cap + lt)
        ring_i = A.ellipse2(ax, ly - yc, 0.5 * cw, 0.5 * cap)
        ring = smax(ring_o, -ring_i, 0.0008)
        ring = smax(ring, (yb - 0.0025) - ly, 0.001)            # only behind the body
        half_h = 0.5 * h * (P["ped_h"] + (P["lam_h"] - P["ped_h"]) * sstep(yc - 0.3 * cap, yc + 0.3 * cap, ly))
        zc = 0.12 * h * sstep(yc + 0.2 * cap, yc - 0.4 * cap, ly)       # pedicles sit on the upper body
        arch = A.extrude(ring, lzs - zc, half_h, 0.0012)
        d0 = smin(body, arch, 0.0025)
        # --- spinous process: from the lamina junction back (and down) to the tip
        root = np.array([0.0, yc + 0.5 * cap + 0.4 * lt, 0.0])
        tip = np.array([0.0, spy - 0.004, -P["drop"] / 1e3])
        spx = P["sp_rx"]
        spz = P["sp_rz"]
        sp = ecap(ax, ly, lz, root, tip, (spz[0] / 1e3, spz[1] / 1e3), (spx[0] / 1e3, spx[1] / 1e3), EZ)
        if reg == "C" and lvl != "C7":           # bifid tip
            for sx in (1.0,):
                tb = A.sd_ellipsoid(ax, ly, lz, (0.0032 * sx, spy - 0.004, -P["drop"] / 1e3),
                                    (0.0028, 0.0035, 0.0030))
                sp = smin(sp, tb, 0.002)
        else:                                    # tubercle at the tip
            tb = A.sd_ellipsoid(ax, ly, lz, tip + np.array([0, 0.001, 0]),
                                (spx[1] / 1e3 * 1.25, 0.0045, spz[1] / 1e3 * 1.15))
            sp = smin(sp, tb, 0.002)
        d0 = smin(d0, sp, 0.003)
        # --- transverse processes
        jx = 0.5 * cw + 0.6 * pw
        if reg == "C":
            # anterior + posterior bars around the transverse foramen, tubercles at the tips
            fx, fy = 0.5 * w + 0.0028, yb - 0.0030
            bar_o = A.sd_ellipsoid(ax, ly, lz, (fx + 0.0015, fy, 0.0004), (0.0068, 0.0055, 0.0030))
            tub = A.sd_ellipsoid(ax, ly, lz, (fx + 0.0060, fy - 0.0010, 0.0010), (0.0030, 0.0042, 0.0034))
            tp = smin(bar_o, tub, 0.002)
            if lvl == "C7":
                tp = smin(tp, ecap(ax, ly, lz, (jx, yc - 0.002, 0.001), (0.5 * w + 0.014, yc, 0.002),
                                   (0.0032, 0.0028), (0.0030, 0.0030), EZ), 0.003)
            tp = smax(tp, -A.sd_capsule(ax, ly, lz, (fx, fy, -0.02), (fx, fy, 0.02), 0.0026), 0.0006)
            d0 = smin(d0, tp, 0.002)
        else:
            tpp = P["tp"]
            a0 = np.array([jx - 0.001, yc + (0.0 if reg == "T" else -0.003), 0.08 * h])
            a1 = np.array([tpp["len"] / 1e3, yc + tpp["back"] / 1e3, 0.08 * h + tpp["up"] / 1e3])
            r1, r2 = tpp["r"]
            if reg == "T":
                tp = ecap(ax, ly, lz, a0, a1, (r1 / 1e3, r2 / 1e3), (r1 / 1e3 * 0.9, r2 / 1e3 * 0.9), EZ)
                tp = smin(tp, A.sd_ellipsoid(ax, ly, lz, a1, (0.0048, 0.0052, 0.0058)), 0.002)
            else:
                tp = ecap(ax, ly, lz, a0, a1, (0.0060, 0.0045), (0.0032, 0.0022), EZ)
            d0 = smin(d0, tp, 0.003)
        # --- articular processes (clipped at the shared joint planes -> no overlap between levels)
        fxs = P["facet_x"] / 1e3
        fr = np.array(P["facet_r"]) / 1e3
        sup = A.sd_ellipsoid(ax, ly, lz, (fxs, yc + 0.1 * cap, 0.5 * h + 0.3 * fr[2]), fr)
        inf = A.sd_ellipsoid(ax, ly, lz, (fxs - 0.001, yc + 0.45 * cap, -0.5 * h - 0.1 * fr[2]),
                             (fr[0], fr[1], fr[2] * 1.1))
        if reg == "L":                           # mammillary processes on the superior facets
            sup = smin(sup, A.sd_ellipsoid(ax, ly, lz, (fxs + 0.004, yc + 0.1 * cap + 0.004, 0.5 * h),
                                           (0.003, 0.004, 0.004)), 0.002)
        if up_pl is not None:
            sup = np.maximum(sup, -(plane(x, y, z, *up_pl) - 0.0004))
        if lo_pl is not None:
            inf = np.maximum(inf, plane(x, y, z, *lo_pl) + 0.0004)
        d0 = smin(d0, smin(sup, inf, 0.001), 0.0025)
        # --- keep the canal open
        canal = A.ellipse2(ax, ly - yc, 0.5 * cw, 0.5 * cap)
        d0 = smax(d0, -canal, 0.0008)
        return d0

    ext = max(0.5 * w, 0.5 * cw + pw + 0.012, (P["tp"]["len"] / 1e3 + 0.007) if P.get("tp") else 0.03) + 0.006
    return fn, _frame_box(F, (-ext, -0.5 * d - 0.006, -0.5 * h - P["drop"] / 1e3 - 0.016),
                          (ext, spy + 0.010, 0.5 * h + 0.016))


def gg_superellipse(a, b, ra, rb, n):
    r = (np.abs(a / ra) ** n + np.abs(b / rb) ** n) ** (1.0 / n)
    return (r - 1.0) * np.minimum(ra, rb)


def _frame_box(F, lo, hi):
    """World AABB of a local box."""
    corners = np.array([[a, b, c] for a in (lo[0], hi[0]) for b in (lo[1], hi[1]) for c in (lo[2], hi[2])])
    W = np.array([F.world(p) for p in corners])
    return W.min(0), W.max(0)


def _head_clear(x, y, z, gap):
    """Positive where a point is at least ``gap`` away from the head project's skull (body frame)."""
    A = _A()
    hx, hy, hz = x - HEAD_OFFSET[0], y - HEAD_OFFSET[1], z - HEAD_OFFSET[2]
    return A.skull_sdf(hx, hy, hz) - gap


def _atlas_sdf():
    """C1 atlas: anterior arch with tubercle, lateral masses with superior facets, posterior arch,
    wide transverse processes with foramina.  No body (the dens of C2 sits in the ring)."""
    r = ROW["C1"]
    F = spine_frame("C1")
    A = _A()
    W = r["body_w_mm"] / 1e3              # 78: tip-to-tip of the transverse processes
    D = r["body_d_mm"] / 1e3              # 45: ring depth
    y0 = -0.0205                          # anterior arch (local)
    y1 = y0 + D                           # posterior tubercle

    def fn(x, y, z):
        lx, ly, lz = F.local(x, y, z)
        ax = np.abs(lx)
        ring_c = 0.5 * (y0 + y1)
        ring_o = A.ellipse2(ax, ly - ring_c, 0.024, 0.5 * D)
        ring_i = A.ellipse2(ax, ly - ring_c - 0.0005, 0.0145, 0.5 * D - 0.0050)
        ring = A.extrude(smax(ring_o, -ring_i, 0.001), lz, 0.0042, 0.002)
        lat = A.sd_ellipsoid(ax, ly, lz, (0.0195, -0.004, 0.0005), (0.0078, 0.0115, 0.0078))
        facet = A.sd_ellipsoid(ax, ly, lz, (0.0215, -0.004, 0.0105), (0.0065, 0.0105, 0.0040))
        lat = smax(lat, -facet, 0.0015)                       # concave superior facets (condyles)
        atub = A.sd_ellipsoid(ax, ly, lz, (0.0, y0 - 0.0005, 0.0), (0.0055, 0.0035, 0.0065))
        ptub = A.sd_ellipsoid(ax, ly, lz, (0.0, y1 - 0.003, -0.001), (0.0045, 0.0045, 0.0060))
        tp = ecap(ax, ly, lz, (0.022, -0.002, 0.0), (0.5 * W - 0.004, 0.001, 0.0), (0.0055, 0.0050),
                  (0.0045, 0.0040), EZ)
        tp = smax(tp, -A.sd_capsule(ax, ly, lz, (0.0295, -0.0015, -0.02), (0.0295, -0.0015, 0.02), 0.0027),
                  0.0006)
        d = smin(ring, lat, 0.004)
        d = smin(d, atub, 0.003)
        d = smin(d, ptub, 0.003)
        d = smin(d, tp, 0.003)
        # vertebral canal + dens space stay open; clear the skull (occipital condyles)
        d = smax(d, -A.ellipse2(ax, ly - (y0 + 0.004 + 0.5 * 0.030), 0.0125, 0.0148), 0.001)
        return np.maximum(d, -_head_clear(x, y, z, 0.0015))

    return fn, _frame_box(F, (-0.5 * W - 0.006, y0 - 0.008, -0.016), (0.5 * W + 0.006, y1 + 0.008, 0.016))


def _axis_sdf():
    """C2 axis: body with the dens rising into the atlas ring, broad superior facets, thick
    laminae and a big bifid spinous process [RB §7.3 row C2]."""
    r = ROW["C2"]
    F = spine_frame("C2")
    A = _A()
    w, d = r["body_w_mm"] / 1e3, r["body_d_mm"] / 1e3
    cap, cw = r["canal_ap_mm"] / 1e3, r["canal_w_mm"] / 1e3
    spy = r["spinous_dy_mm"] / 1e3
    yb, yc = 0.5 * d, 0.5 * d + 0.5 * cap
    lo_pl = _joint_plane("C2", "C3")
    c1 = spine_frame("C1")
    dens_top = F.local(*[np.array([v]) for v in c1.world((0.0, -0.0205 + 0.0085, 0.0095))])
    dt = np.array([dens_top[0][0], dens_top[1][0], dens_top[2][0]])

    def fn(x, y, z):
        lx, ly, lz = F.local(x, y, z)
        ax = np.abs(lx)
        body = A.extrude(gg_superellipse(ax, ly, 0.5 * w, 0.5 * d, 2.6), lz + 0.0025, 0.0085, 0.0015)
        dens = A.sd_capsule(ax, ly, lz, (0.0, 0.0005, 0.004), dt, 0.0052, 0.0042)
        facet = A.sd_ellipsoid(ax, ly, lz, (0.0155, 0.0015, 0.0055), (0.0075, 0.0095, 0.0045))
        ring_o = A.ellipse2(ax, ly - yc, 0.5 * cw + 0.0055, 0.5 * cap + 0.0060)
        ring = smax(ring_o, -A.ellipse2(ax, ly - yc, 0.5 * cw, 0.5 * cap), 0.001)
        ring = smax(ring, (yb - 0.0025) - ly, 0.001)
        arch = A.extrude(ring, lz + 0.0035 + 0.35 * np.maximum(ly - yc, 0), 0.0065, 0.0015)
        sp = ecap(ax, ly, lz, (0.0, yc + 0.5 * cap + 0.003, -0.002), (0.0, spy - 0.005, -0.008),
                  (0.0068, 0.0055), (0.0045, 0.0032), EZ)
        bif = A.sd_ellipsoid(ax, ly, lz, (0.0045, spy - 0.005, -0.008), (0.0040, 0.0048, 0.0052))
        tp = A.sd_ellipsoid(ax, ly, lz, (0.5 * w + 0.0045, yb - 0.003, -0.001), (0.0055, 0.0050, 0.0040))
        tp = smax(tp, -A.sd_capsule(ax, ly, lz, (0.5 * w + 0.0035, yb - 0.003, -0.02),
                                    (0.5 * w + 0.0035, yb - 0.003, 0.02), 0.0024), 0.0006)
        inf = A.sd_ellipsoid(ax, ly, lz, (0.0150, yc + 0.35 * cap, -0.0105), (0.0050, 0.0060, 0.0060))
        inf = np.maximum(inf, plane(x, y, z, *lo_pl) + 0.0004)
        dd = smin(body, dens, 0.003)
        dd = smin(dd, facet, 0.003)
        dd = smin(dd, arch, 0.003)
        dd = smin(dd, smin(sp, bif, 0.002), 0.003)
        dd = smin(dd, tp, 0.002)
        dd = smin(dd, inf, 0.002)
        dd = smax(dd, -A.ellipse2(ax, ly - yc, 0.5 * cw, 0.5 * cap), 0.0008)
        return np.maximum(dd, -_head_clear(x, y, z, 0.0015))

    return fn, _frame_box(F, (-0.032, -0.5 * d - 0.006, -0.03), (0.032, spy + 0.012, 0.04))


def disc_sdf(upper, lower):
    """Intervertebral disc between the endplates of two levels (a wedge following the curve)."""
    fu, fl = spine_frame(upper), spine_frame(lower)
    ru, rl = ROW[upper], ROW[lower]
    A = _A()
    pu = fu.c - fu.R[2] * (ru["body_h_mm"] / 2000.0 - 0.0006)
    pl = fl.c + fl.R[2] * (rl["body_h_mm"] / 2000.0 - 0.0006)
    if upper == "C2":
        pu = fu.c - fu.R[2] * (0.0025 + 0.0085 - 0.0006)
    mid = Frame(0.5 * (pu + pl), EX, _n(fu.R[1] + fl.R[1]))
    w = 0.5 * (ru["body_w_mm"] + rl["body_w_mm"]) / 1e3
    d = 0.5 * (ru["body_d_mm"] + rl["body_d_mm"]) / 1e3
    reg = lower[0]
    n = 2.6 if reg == "C" else (2.2 if reg == "T" else 2.4)
    half_t = 0.5 * np.linalg.norm(pu - pl)

    def fn(x, y, z):
        lx, ly, lz = mid.local(x, y, z)
        ax = np.abs(lx)
        bulge = 0.0008 * (1.0 - np.minimum((lz / max(half_t, 1e-4)) ** 2, 1.0))
        sec = gg_superellipse(ax, ly, 0.5 * w * 0.97, 0.5 * d * 0.97, n) - bulge
        top = plane(x, y, z, pu, -fu.R[2])          # below the upper endplate
        bot = plane(x, y, z, pl, fl.R[2])           # above the lower endplate
        return smax(sec, np.maximum(top, bot), 0.0007)
    lo = np.minimum(pu, pl) - np.array([0.5 * w + 0.004, 0.5 * d + 0.006, 0.006])
    hi = np.maximum(pu, pl) + np.array([0.5 * w + 0.004, 0.5 * d + 0.006, 0.006])
    return fn, (lo, hi)


def sacrum_sdf():
    """Sacrum: S1 body and endplate, alae to the SI joints, concave pelvic surface with four
    pairs of anterior foramina, dorsal wall with median crest and posterior foramina, sacral
    canal and hiatus; fused wedge from S1 to the tip [RB §7.3, R05 §4.3]."""
    A = _A()
    F1 = spine_frame("S1")
    r = ROW["S1"]
    tip = np.array(VT.SACRUM["tip"])
    top_front = F1.world((0.0, -0.5 * r["body_d_mm"] / 1e3, 0.5 * r["body_h_mm"] / 1e3))
    # centreline of the sacral bodies (front third), concave forward
    pts = np.array([F1.world((0.0, 0.0, 0.5 * r["body_h_mm"] / 1e3)), (0.0, 0.020, 0.992), (0.0, 0.031, 0.965),
                    (0.0, 0.042, 0.942), tip + np.array([0.0, -0.001, 0.002])])
    half_w = lambda t: interp(t, [0.0, 0.18, 0.45, 0.75, 1.0], [0.052, 0.050, 0.040, 0.024, 0.012])
    body_rn = lambda t: interp(t, [0.0, 0.3, 0.7, 1.0], [0.0150, 0.0105, 0.0075, 0.0045])

    def sec(n, b, t):
        # n: anterior (-), posterior (+) along the frame N (= posterior); b lateral
        hw = half_w(t)
        th = body_rn(t)
        # overall wedge: thick at the alae/bodies, thinner laterally at the bottom
        dorsal = 0.010 + 0.012 * (1 - t)
        s = gg_superellipse(b, n - 0.4 * dorsal, hw, th + 0.5 * dorsal, 2.4)
        # anterior concavity across the width (pelvic surface)
        s = smax(s, -(n + th + 0.0025 - 0.006 * (b / hw) ** 2 * (1 - 0.5 * t)), 0.002)
        return s
    core = Tube(pts, sec, ref_fn=lambda P: np.tile(EY, (len(P), 1)), step=0.0015, round_ends=True)
    axis_pts = core.P

    def fn(x, y, z):
        d = core(x, y, z)
        ax = np.abs(x)
        # S1 body: flat endplate facing up-forward
        F = F1
        lx, ly, lz = F.local(x, y, z)
        s1 = A.extrude(gg_superellipse(np.abs(lx), ly, 0.5 * r["body_w_mm"] / 1e3, 0.5 * r["body_d_mm"] / 1e3,
                                       2.4), lz + 0.004, 0.5 * r["body_h_mm"] / 1e3 + 0.004, 0.0015)
        d = smin(d, s1, 0.004)
        d = smax(d, lz - 0.5 * r["body_h_mm"] / 1e3, 0.0015)         # cut at the S1 endplate plane
        # alae: thick wings to the auricular surfaces (SI joints) at x ~ 0.045
        ala = ecap(ax, y, z, (0.012, 0.030, 1.012), (0.044, 0.040, 1.000), (0.012, 0.010), (0.016, 0.018),
                   (0.0, -0.45, 0.9))
        aur = A.sd_ellipsoid(ax, y, z, (0.043, 0.050, 0.985), (0.009, 0.020, 0.030))
        d = smin(d, smin(ala, aur, 0.008), 0.006)
        # superior articular processes (for L5)
        sap = A.sd_ellipsoid(ax, y, z, (0.020, 0.048, 1.022), (0.0065, 0.0070, 0.0080))
        lpl = _joint_plane("L5", "S1")
        sap = np.maximum(sap, -(plane(x, y, z, *lpl) - 0.0004))
        d = smin(d, sap, 0.004)
        # median sacral crest (fused spinous tubercles) and lateral crests
        crest = A.sd_polyline(ax, y, z, [(0.0, 0.062, 1.005), (0.0, 0.066, 0.985), (0.0, 0.062, 0.962),
                                         (0.0, 0.058, 0.944)], [0.0035, 0.0035, 0.0030, 0.0022])[0]
        d = smin(d, crest, 0.004)
        # sacral canal (continues the lumbar canal; opens at the hiatus low down)
        canal = A.sd_polyline(ax, y, z, [(0.0, 0.050, 1.030), (0.0, 0.048, 1.000), (0.0, 0.052, 0.975),
                                         (0.0, 0.054, 0.952), (0.0, 0.058, 0.935)],
                              [0.0075, 0.0068, 0.0055, 0.0042, 0.0030])[0]
        canal = gg_superellipse(ax, 0.0, 1.0, 1.0, 2.0) * 0.0 + canal
        d = smax(d, -canal, 0.0008)
        # four pairs of anterior and posterior sacral foramina
        for k, (zf, xf) in enumerate(((0.998, 0.016), (0.975, 0.015), (0.955, 0.013), (0.940, 0.011))):
            yf = float(np.interp(-zf, -axis_pts[:, 2], axis_pts[:, 1]))
            ant = A.sd_capsule(ax, y, z, (xf, yf - 0.030, zf + 0.002), (xf, yf + 0.004, zf), 0.0042 - 0.0004 * k)
            post = A.sd_capsule(ax, y, z, (xf - 0.002, yf + 0.010, zf), (xf - 0.002, yf + 0.040, zf + 0.004),
                                0.0028 - 0.0002 * k)
            d = smax(d, -np.minimum(ant, post), 0.0008)
        return d
    return fn, (np.array([-0.062, -0.015, 0.915]), np.array([0.062, 0.080, 1.040]))


def coccyx_sdf():
    """Coccyx: three to four fused, shrinking segments curving forward to the tip."""
    A = _A()
    top = np.array(VT.SACRUM["tip"]) + np.array([0.0, 0.001, -0.004])
    tipc = np.array(VT.COCCYX_TIP)
    mid = 0.5 * (top + tipc) + np.array([0.0, 0.004, 0.0])
    segs = [top, top + 0.33 * (mid - top) * 2, mid + 0.4 * (tipc - mid), tipc + np.array([0.0, 0.0, 0.002])]

    def fn(x, y, z):
        ax = np.abs(x)
        d = np.full(x.shape, 1e3)
        radii = [(0.0085, 0.0045, 0.0045), (0.0065, 0.0040, 0.0040), (0.0050, 0.0034, 0.0034),
                 (0.0036, 0.0028, 0.0028)]
        for c, rr in zip(segs, radii):
            d = smin(d, A.sd_ellipsoid(ax, y, z, c, rr), 0.0022)
        cornu = A.sd_ellipsoid(ax, y, z, top + np.array([0.006, 0.004, 0.003]), (0.0022, 0.0022, 0.0035))
        return smin(d, cornu, 0.0015)
    return fn, (np.array([-0.016, 0.028, 0.892]), np.array([0.016, 0.062, 0.930]))


# ===========================================================================
# Meshing: SDF -> triangles (surface nets + Newton projection), island cleanup, decimation
# ===========================================================================
def quads_to_tris(v, q):
    """Split quads along the shorter diagonal."""
    q = np.asarray(q, np.int64)
    if len(q) == 0:
        return np.zeros((0, 3), np.int64)
    d02 = np.linalg.norm(v[q[:, 0]] - v[q[:, 2]], axis=1)
    d13 = np.linalg.norm(v[q[:, 1]] - v[q[:, 3]], axis=1)
    a = d02 <= d13
    t1 = np.where(a[:, None], q[:, [0, 1, 2]], q[:, [0, 1, 3]])
    t2 = np.where(a[:, None], q[:, [0, 2, 3]], q[:, [1, 2, 3]])
    return np.vstack([t1, t2])


def compact(v, f):
    """Drop unreferenced vertices."""
    used = np.unique(f)
    remap = np.full(len(v), -1, np.int64)
    remap[used] = np.arange(len(used))
    return v[used], remap[f]


def islands(nv, f):
    """Connected-component label per vertex."""
    lab = np.arange(nv)
    e = np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]])
    for _ in range(400):
        m = np.minimum(lab[e[:, 0]], lab[e[:, 1]])
        new = lab.copy()
        np.minimum.at(new, e[:, 0], m)
        np.minimum.at(new, e[:, 1], m)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    return lab


def drop_crumbs(v, f, min_verts=24):
    """Remove tiny islands (surface-net crumbs at thin features)."""
    if len(f) == 0:
        return v, f
    lab = islands(len(v), f)
    ids, cnt = np.unique(lab, return_counts=True)
    keepv = np.isin(lab, ids[cnt >= min_verts])
    keepf = keepv[f].all(1)
    return compact(v, f[keepf])


def mesh_sdf(fn, box, h, project=3):
    """Polygonise ``fn`` inside ``box`` at spacing ``h``: (verts, tris)."""
    import gb_geom as gg
    lo, hi = box
    v, q = gg.sdf_arrays(fn, np.asarray(lo) - 2 * h, np.asarray(hi) + 2 * h, h, project=project)
    if len(q) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    f = quads_to_tris(v, q)
    return drop_crumbs(v, f)


def decimate_arrays(v, f, target):
    """Collapse-decimate a triangle soup to ~``target`` triangles (Blender's quadric collapse)."""
    import bpy
    if len(f) <= target or target <= 0:
        return v, f
    me = gbc.mesh_from_arrays("_b3_dec", v, f, smooth=False)
    ob = bpy.data.objects.new("_b3_dec", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("dec", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.002, target / len(f))
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me2 = bpy.data.meshes.new_from_object(ev)
    v2, f2 = gbc.mesh_arrays(me2)
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(me2)
    return compact(v2, f2) if len(f2) else (v2, f2)


def mirror_arrays(v, f):
    """Mirror across x = 0 (winding reversed so normals stay outward)."""
    v2 = np.array(v, float)
    v2[:, 0] *= -1.0
    return v2, np.asarray(f)[:, ::-1].copy()


# ===========================================================================
# Thorax: ribs 1-12, costal cartilages 1-10, sternum [RB §7.3 rib table, R05 §5]
# ===========================================================================
def _rib_normal_fn(n):
    """Preferred section normal N along a rib: outward from the cage axis (flat faces in/out);
    rib 1 lies flat (faces up/down), rib 2 in between."""
    def fn(P):
        out = np.stack([P[:, 0], P[:, 1] - 0.012, np.zeros(len(P))], axis=1)
        out /= np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-9)
        if n == 1:
            return np.tile(EZ, (len(P), 1)) * 0.85 + out * 0.15
        if n == 2:
            return out * 0.55 + EZ * 0.45
        return out
    return fn


def rib_sdf(n):
    """Rib ``n`` (left): head with facets, neck, tubercle, angle, flattened shaft with a costal
    groove on the inner lower edge, cupped costochondral end (floating ribs taper)."""
    A = _A()
    pts = np.array(RB_.rib_points(n))
    hmm, tmm = RB_.RIB_SECTION_MM.get(n, RB_.RIB_SECTION_MM["default"])
    H, Tk = hmm / 1e3, tmm / 1e3
    floating = n >= 11
    head = pts[0]
    # section profile along the rib: head/neck round, shaft full, costochondral end oval
    kn = [0.0, 0.05, 0.14, 0.30, 0.85, 1.0]
    if floating:
        hv = [0.0075, 0.0065, 0.8 * H, H, 0.6 * H, 0.0030]
        tv = [0.0070, 0.0050, Tk, Tk, 0.8 * Tk, 0.0022]
    elif n == 1:
        hv = [0.0070, 0.0060, 0.7 * H, H, H, 0.85 * H]
        tv = [0.0065, 0.0050, 0.0045, Tk, Tk, 0.0060]
    else:
        hv = [0.0080, 0.0068, 0.75 * H, H, 0.95 * H, 0.90 * H]
        tv = [0.0075, 0.0055, 0.0060, Tk, Tk, 0.0080]

    def sec(nn, b, t):
        hh = 0.5 * interp(t, kn, hv)
        tt = 0.5 * interp(t, kn, tv)
        shaft = sstep(0.12, 0.3, t) * (1 - sstep(0.9, 1.0, t))
        # thinner towards the lower border (teardrop), costal groove on the inner-lower edge
        tloc = tt * (1.0 - 0.30 * shaft * np.clip(-b / hh, 0, 1))
        s = gg_superellipse(nn, b, tloc, hh, 2.4)
        groove = A.ellipse2(nn + 0.55 * tt, b + 0.55 * hh, 0.35 * tt, 0.28 * hh)
        return smax(s, -groove * 1.0 - 0.0003 + (1 - shaft) * 0.01, 0.0006)
    tube = Tube(pts, sec, ref_fn=_rib_normal_fn(n), step=0.0018, round_ends=True)
    # tubercle: where the rib passes the tip of its transverse process
    tub_t = 0.13
    k = int(tub_t * (len(tube.P) - 1))
    tubc = tube.P[k] + tube.N[k] * (0.4 * Tk) - tube.B[k] * 0.002
    ccj = pts[-1]
    tan_end = _n(tube.T[-1])

    def fn(x, y, z):
        d = tube(x, y, z)
        d = smin(d, A.sd_ellipsoid(x, y, z, head, (0.0050, 0.0052, 0.0060)), 0.003)
        d = smin(d, A.sd_sphere(x, y, z, tubc, 0.0042), 0.003)
        if not floating:
            d = np.maximum(d, plane(x, y, z, ccj, tan_end) + 0.0003)         # flat costochondral end
        return d
    lo = pts.min(0) - 0.02
    hi = pts.max(0) + 0.02
    return fn, (lo, hi)


def sternum_parts():
    """Sternum SDF (manubrium, body, xiphoid) as one piece, front surface on the RB points."""
    A = _A()
    S = RB_.STERNUM
    back = np.array([0.0, 0.940, -0.342])
    m, b, xp = S["manubrium"], S["body"], S["xiphoid"]
    th = [0.0150, 0.0110, 0.0045]
    front = [np.array(m["top"]), np.array(m["bottom"]), 0.5 * (np.array(b["top"]) + np.array(b["bottom"])),
             np.array(b["bottom"]), np.array(xp["bottom"])]
    pts = np.array([front[0] + back * 0.0075, front[1] + back * 0.0065, front[2] + back * 0.0055,
                    front[3] + back * 0.0040, front[4] + back * 0.0022 + np.array([0, 0.0, 0.004])])
    kn = [0.0, 0.10, 0.25, 0.28, 0.45, 0.66, 0.80, 0.83, 1.0]
    wv = [0.0275, 0.0240, 0.0150, 0.0130, 0.0150, 0.0175, 0.0125, 0.0088, 0.0030]
    tv = [0.0075, 0.0072, 0.0060, 0.0055, 0.0055, 0.0055, 0.0040, 0.0023, 0.0015]

    def sec(n, bb, t):
        return gg_superellipse(bb, n, interp(t, kn, wv), interp(t, kn, tv), 2.8)
    tube = Tube(pts, sec, ref_fn=lambda P: np.tile(EY, (len(P), 1)), step=0.0015, round_ends=True)
    clav = clavicle_sdf()[0]

    def fn(x, y, z):
        d = tube(x, y, z)
        ax = np.abs(x)
        # jugular notch, clavicular notches (clear the clavicles' sternal ends), sternal angle ridge
        d = smax(d, -A.sd_ellipsoid(ax, y, z, (0.0, -0.040, 1.462), (0.009, 0.020, 0.0085)), 0.002)
        d = np.maximum(d, -(clav(ax, y, z) - 0.0012))
        ridge = A.sd_capsule(ax, y, z, (0.0, -0.0600, 1.406), (0.012, -0.0592, 1.406), 0.0020)
        d = smin(d, ridge, 0.002)
        return d
    return fn, (np.array([-0.035, -0.11, 1.26]), np.array([0.035, -0.03, 1.47]))


def cartilage_sdf(n):
    """Costal cartilage ``n`` (1-10, left): CCJ -> sternum (1-7) or the cartilage above (8-10);
    clipped against the sternum / upper cartilage so pieces never overlap."""
    A = _A()
    cp = RB_.cartilage_points(n)
    ccj, end = np.array(cp[0]), np.array(cp[1])
    rib_pts = np.array(RB_.rib_points(n))
    t_in = _n(rib_pts[-1] - rib_pts[-2])
    # leave the CCJ along the rib's direction, bend (costal cartilages rise medially), bulge forward
    p1 = ccj + t_in * 0.006
    mid = 0.5 * (p1 + end) + np.array([0.0, -0.004, 0.0]) + np.array([0.0, 0.0, 0.004 if n >= 5 else 0.0])
    pts = [ccj + t_in * 0.0006, p1, mid, end]
    ch, ct = RB_.CARTILAGE_SECTION_MM
    w = 1.0 if n > 1 else 1.6

    def sec(nn, b, t):
        hh = 0.5 * ch / 1e3 * w * (1.0 - 0.25 * t)
        tt = 0.5 * ct / 1e3 * (1.0 - 0.2 * t)
        return gg_superellipse(nn, b, tt, hh, 2.2)
    tube = Tube(pts, sec, ref_fn=_rib_normal_fn(n), step=0.0015, round_ends=True)
    stern = sternum_parts()[0] if n <= 7 else None
    upper = cartilage_sdf(n - 1)[0] if n >= 8 else None

    def fn(x, y, z):
        d = tube(x, y, z)
        d = np.maximum(d, -plane(x, y, z, ccj, t_in) + 0.0003)             # starts at the CCJ
        if stern is not None:
            d = np.maximum(d, -(stern(x, y, z) - 0.0006))
        if upper is not None:
            d = np.maximum(d, -(upper(x, y, z) - 0.0006))
        return d
    P = np.array(pts)
    return fn, (P.min(0) - 0.015, P.max(0) + 0.015)


# ===========================================================================
# Shoulder girdle: clavicle, scapula [RB §7.3, R05 §6.1]
# ===========================================================================
def clavicle_sdf():
    """Clavicle (left): S-curved shaft, bulbous sternal end, flattened acromial end."""
    wp = np.array(BN.CLAVICLE_WAYPOINTS, float)
    sc, ac = wp[0], wp[-1]
    kn = [0.0, 0.12, 0.35, 0.55, 0.78, 1.0]
    rn = [0.0100, 0.0072, 0.0058, 0.0052, 0.0048, 0.0050]      # vertical half
    rb = [0.0122, 0.0080, 0.0068, 0.0066, 0.0090, 0.0115]      # horizontal half

    def sec(n, b, t):
        return gg_superellipse(n, b, interp(t, kn, rn), interp(t, kn, rb), 2.3)
    tube = Tube(wp, sec, ref_fn=lambda P: np.tile(EZ, (len(P), 1)), step=0.0015, round_ends=True)
    t0, t1 = _n(tube.T[0]), _n(tube.T[-1])

    def fn(x, y, z):
        d = tube(x, y, z)
        d = smax(d, -plane(x, y, z, sc + t0 * 0.0012, t0), 0.003)          # sternal facet
        d = smax(d, plane(x, y, z, ac - t1 * 0.0015, t1), 0.003)            # acromial facet
        return d
    return fn, (wp.min(0) - 0.02, wp.max(0) + 0.02)


def _pca_frame(pts):
    P = np.asarray(pts, float)
    c = P.mean(0)
    _u, _s, vt = np.linalg.svd(P - c)
    return Frame(c, vt[0], vt[1])


GH_L = np.array(BN.HUMERUS["head_centre"], float)
HUM_HEAD_R = 0.0235
G_DIR = _n((0.94, -0.34, 0.0))                  # glenoid faces lateral-forward (blade 35-40 deg)


def scapula_sdf():
    """Scapula (left): thin curved blade (fossae 2-3 mm) with rolled lateral border, spine and
    crest, flat acromion, coracoid, shallow glenoid clearing the humeral head."""
    A = _A()
    S = BN.SCAPULA
    Sa, root, Ia = np.array(S["superior_angle"]), np.array(S["spine_root"]), np.array(S["inferior_angle"])
    gf = GH_L - (HUM_HEAD_R + 0.0035) * G_DIR
    outline = [Sa, root, (0.079, 0.103, 1.390), Ia, (0.112, 0.078, 1.357), (0.137, 0.046, 1.392),
               (0.140, 0.040, 1.403), (0.139, 0.036, 1.436), (0.128, 0.042, 1.452), (0.110, 0.058, 1.462),
               (0.094, 0.073, 1.471)]
    extra = [(0.100, 0.083, 1.410), (0.110, 0.074, 1.385)]
    blade = Sheet(_pca_frame(outline), outline, extra,
                  thick=lambda u, v, e: 0.0024 + 0.0020 * np.exp(-(e / 0.004) ** 2))
    lat = [Ia, (0.100, 0.093, 1.340), (0.118, 0.073, 1.362), (0.137, 0.046, 1.392)]
    med = [Sa, root, (0.079, 0.103, 1.390), Ia]
    crest = [(0.077, 0.101, 1.438), (0.105, 0.100, 1.448), (0.140, 0.086, 1.455), (0.168, 0.066, 1.458),
             tuple(S["acromion_posterior_angle"])]
    base = [(0.076, 0.094, 1.440), (0.105, 0.082, 1.446), (0.132, 0.062, 1.442), (0.140, 0.043, 1.432)]
    spine_outline = base + [crest[3], crest[2], crest[1], crest[0]]
    spine = Sheet(_pca_frame(spine_outline), spine_outline, (), thick=lambda u, v, e: 0.0040)
    acro_outline = [tuple(S["acromion_posterior_angle"]), (0.203, 0.040, 1.457), (0.204, 0.022, 1.458),
                    tuple(S["acromion_tip"]), (0.188, 0.006, 1.460), (0.172, 0.010, 1.462), (0.164, 0.028, 1.459),
                    (0.163, 0.052, 1.456)]
    acro = Sheet(_pca_frame(acro_outline), acro_outline, (), thick=lambda u, v, e: 0.0068 - 0.002 * sstep(
        -0.004, 0.0, e))
    gax = np.array([G_DIR, _n(EZ - (EZ @ G_DIR) * G_DIR), np.cross(G_DIR, _n(EZ - (EZ @ G_DIR) * G_DIR))])
    cor = [(0.134, 0.034, 1.444), (0.139, 0.016, 1.458), (0.140, -0.004, 1.448), tuple(S["coracoid_tip"])]

    def fn(x, y, z):
        d = blade(x, y, z)
        d = smin(d, A.sd_polyline(x, y, z, lat, [0.0030, 0.0042, 0.0050, 0.0058])[0], 0.004)
        d = smin(d, A.sd_polyline(x, y, z, med, [0.0020, 0.0022, 0.0020, 0.0028])[0], 0.002)
        d = smin(d, spine(x, y, z), 0.004)
        d = smin(d, A.sd_polyline(x, y, z, crest, [0.0030, 0.0036, 0.0040, 0.0042, 0.0045])[0], 0.003)
        d = smin(d, acro(x, y, z), 0.005)
        glen = ell3(x, y, z, gf - G_DIR * 0.006, (0.0075, 0.0190, 0.0140), gax)
        neck = ecap(x, y, z, (0.132, 0.046, 1.415), gf - G_DIR * 0.006, (0.009, 0.013), (0.007, 0.010), EZ)
        d = smin(d, smin(glen, neck, 0.004), 0.005)
        d = smin(d, A.sd_polyline(x, y, z, cor, [0.0062, 0.0060, 0.0055, 0.0048])[0], 0.004)
        # glenoid fossa: clear the humeral head + 2 x 1.75 mm cartilage
        d = smax(d, -(A.sd_sphere(x, y, z, GH_L, HUM_HEAD_R + 0.0035)), 0.0015)
        return d
    return fn, (np.array([0.06, -0.035, 1.30]), np.array([0.215, 0.12, 1.49]))


# ===========================================================================
# Pelvis: hip bone (ilium, ischium, pubis) [RB §7.3 PELVIS points, R05 §7]
# ===========================================================================
ACET_C = np.array(BN.PELVIS["acetabulum_centre"], float)
FEM_HEAD_R = BN.FEMUR["head_d_mm"] / 2000.0
ACET_DIR = _n((0.664, -0.242, -0.707))          # opens lateral, anterior (~20 deg), inferior (~45 deg)
OBT_AXES = np.array([_n((0.35, 0.94, 0.0)), EZ, _n(np.cross((0.35, 0.94, 0.0), EZ))])


def hip_bone_sdf():
    """Left os coxae: thin iliac fossa between thick crest and borders, acetabulum with lunate
    rim and notch around the femoral head, pubic body and rami, ischium and tuberosity, the
    obturator foramen left open, pelvic brim, ischial spine, greater/lesser sciatic notches."""
    A = _A()
    P = BN.PELVIS
    asis, aiis, top, tub = (np.array(P[k]) for k in ("asis", "aiis", "iliac_crest_top", "iliac_tubercle"))
    psis = np.array(P["psis"])
    crest_back = np.array((0.092, 0.072, 1.058))
    piis = np.array((0.052, 0.086, 0.986))
    notch = np.array((0.068, 0.058, 0.948))
    acet_top = ACET_C + np.array((0.004, 0.004, 0.034))
    wing_outline = [asis, tub, top, crest_back, psis, piis, (0.060, 0.070, 0.965), notch,
                    (0.080, 0.030, 0.945), acet_top, (0.100, -0.036, 0.950), aiis, (0.113, -0.060, 0.975)]
    extra = [(0.100, 0.020, 1.020), (0.085, 0.040, 0.990), (0.115, -0.020, 1.010)]
    wing = Sheet(_pca_frame(wing_outline), wing_outline, extra,
                 thick=lambda u, v, e: 0.0030 + 0.004 * np.exp(-(e / 0.006) ** 2))
    crest = [asis, tub, top, (0.123, 0.056, 1.068), crest_back, (0.066, 0.086, 1.040), psis]
    crest_r = [0.0055, 0.0075, 0.0065, 0.0060, 0.0058, 0.0060, 0.0065]
    post_border = [psis, piis, (0.058, 0.072, 0.968), notch, (0.058, 0.044, 0.925),
                   np.array(P["ischial_spine"])]
    ant_border = [asis, (0.117, -0.060, 0.975), aiis, (0.098, -0.048, 0.945)]
    # thick posterior ilium (auricular part) that meets the sacral ala at the SI joint
    brim = [(0.056, 0.048, 0.990), (0.066, 0.020, 0.960), (0.074, -0.020, 0.936), (0.060, -0.048, 0.922),
            (0.035, -0.064, 0.915), np.array(P["pubic_tubercle"])]
    sup_ramus = [(0.080, -0.030, 0.926), (0.050, -0.058, 0.914), (0.024, -0.064, 0.905)]
    inf_ramus = [(0.008, -0.054, 0.868), (0.026, -0.036, 0.852), (0.044, -0.004, 0.844),
                 np.array(P["ischial_tuberosity"]) + np.array((0.0, -0.004, 0.0))]
    isch = [ACET_C + np.array((-0.006, 0.020, -0.020)), (0.068, 0.028, 0.880), (0.058, 0.024, 0.852)]
    sacrum_fn = sacrum_sdf()[0]

    def fn(x, y, z):
        d = wing(x, y, z)
        d = smin(d, A.sd_polyline(x, y, z, crest, crest_r)[0], 0.006)
        d = smin(d, A.sd_polyline(x, y, z, post_border, [0.0065, 0.0060, 0.0060, 0.0080, 0.0085, 0.0045])[0],
                 0.006)
        d = smin(d, A.sd_polyline(x, y, z, ant_border, [0.0050, 0.0045, 0.0055, 0.0070])[0], 0.005)
        # auricular (SI) part: thick posterior ilium
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.060, 0.062, 0.992), (0.010, 0.020, 0.030)), 0.008)
        # body around the acetabulum + the cup (lunate rim), acetabular notch below
        body = A.sd_sphere(x, y, z, ACET_C, 0.0355)
        body = smin(body, A.sd_ellipsoid(x, y, z, ACET_C + np.array((-0.012, 0.012, 0.018)),
                                         (0.018, 0.026, 0.026)), 0.010)
        d = smin(d, body, 0.010)
        d = smin(d, A.sd_polyline(x, y, z, brim, [0.0065, 0.0060, 0.0062, 0.0060, 0.0065, 0.0050])[0], 0.005)
        d = smin(d, A.sd_polyline(x, y, z, sup_ramus, [0.0100, 0.0085, 0.0080])[0], 0.005)
        pub = ebox(x, y, z, (0.0130, -0.0605, 0.889), (0.0105, 0.0065, 0.0215),
                   np.array([EX, _n((0.0, 0.94, 0.34)), _n((0.0, -0.34, 0.94))]), rnd=0.0055)
        d = smin(d, pub, 0.006)
        d = smin(d, A.sd_polyline(x, y, z, inf_ramus, [0.0055, 0.0052, 0.0058, 0.0080])[0], 0.005)
        d = smin(d, A.sd_polyline(x, y, z, isch, [0.0120, 0.0115, 0.0110])[0], 0.008)
        d = smin(d, A.sd_ellipsoid(x, y, z, np.array(P["ischial_tuberosity"]) + np.array((0.002, 0.003, 0.004)),
                                   (0.0115, 0.0145, 0.0185)), 0.006)
        # obturator foramen (open), acetabular socket (femoral head + 2 x 2 mm cartilage)
        obt = ell3(x, y, z, np.array(P["obturator_centre"]) + np.array((0.002, 0.004, 0.0)),
                   (0.0235, 0.0165, 0.016), OBT_AXES)
        d = smax(d, -obt, 0.004)
        cup = A.sd_sphere(x, y, z, ACET_C, FEM_HEAD_R + 0.0040)
        d = smax(d, -cup, 0.0015)
        # the rim stops at the acetabular opening plane; notch at the inferior rim
        rim_cut = smax(plane(x, y, z, ACET_C + ACET_DIR * 0.006, ACET_DIR),
                       A.sd_sphere(x, y, z, ACET_C, 0.045) , 0.004)
        d = smax(d, -rim_cut, 0.003)
        notch_c = ACET_C + np.array((0.004, 0.006, -0.028))
        d = smax(d, -A.sd_ellipsoid(x, y, z, notch_c, (0.012, 0.011, 0.010)), 0.003)
        # pubic symphysis gap (disc 2 x 2.5 mm) and SI joint clearance to the sacrum
        d = smax(d, 0.0025 - x, 0.002)
        d = np.maximum(d, -(sacrum_fn(x, y, z) - 0.0012))
        return d
    return fn, (np.array([0.0, -0.085, 0.815]), np.array([0.165, 0.110, 1.085]))
