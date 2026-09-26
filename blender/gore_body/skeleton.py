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
                    tilt=0.55, sp_rx=(3.4, 2.6), sp_rz=(7.0, 4.2),
                    drop={1: 10, 2: 13, 3: 16, 4: 20, 5: 24, 6: 27, 7: 28, 8: 27, 9: 24, 10: 20, 11: 14,
                          12: 10}[k],
                    tp=dict(len=(38 - 1.1 * k), up=4.0, back=7.0 - 0.3 * k, r=(4.6, 5.2)),
                    facet_x=9.5 + 0.3 * k, facet_r=(5.0, 6.0, 5.5))
    return dict(n_body=2.4, back_indent=3.0, ped_w=9.0 + 1.2 * k, ped_h=0.5, lam_t=6.5, lam_h=1.0,
                tilt=0.25, sp_rx=(3.8, 3.4), sp_rz=(7.5, 9.0), drop=5.0,
                tp=dict(len={1: 30, 2: 35, 3: 42, 4: 38, 5: 36}[k], up=0.0, back=-3.0, r=(5.0, 2.2)),
                facet_x=12.0 + 1.3 * k, facet_r=(6.5, 8.0, 7.5))


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
        tip = np.array([0.0, spy - (0.007 if lvl in ("T1", "T2", "T3") else 0.004), -P["drop"] / 1e3])
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
    pu = fu.c - fu.R[2] * (ru["body_h_mm"] / 2000.0 + 0.0007)
    pl = fl.c + fl.R[2] * (rl["body_h_mm"] / 2000.0 + 0.0007)
    if upper == "C2":
        pu = fu.c - fu.R[2] * (0.0025 + 0.0085 + 0.0002)
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
        top = plane(x, y, z, pu, fu.R[2])           # outside above the upper body's endplate
        bot = plane(x, y, z, pl, -fl.R[2])          # outside below the lower body's endplate
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


def nonmanifold_edges(f):
    """Number of edges not shared by exactly two triangles."""
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _u, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt != 2).sum())


def _remesh(v, f, voxel):
    """Blender voxel remesh (manifold quads) -> triangles."""
    import bpy
    me = gbc.mesh_from_arrays("_b3_rm", v, f, smooth=False)
    ob = bpy.data.objects.new("_b3_rm", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("rm", 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = voxel
    mod.adaptivity = 0.0
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    v2, f2 = gbc.mesh_arrays(me2)
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(me2)
    return v2, f2


def mesh_sdf(fn, box, h, project=3):
    """Polygonise ``fn`` inside ``box`` at spacing ``h``: (verts, tris), closed and manifold.

    Surface nets + Newton projection; where the nets produce non-manifold edges (thin features)
    the mesh is voxel-remeshed at the same spacing and re-projected onto the exact surface."""
    import gb_geom as gg
    lo, hi = box
    v, q = gg.sdf_arrays(fn, np.asarray(lo) - 2 * h, np.asarray(hi) + 2 * h, h, project=project)
    if len(q) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    f = quads_to_tris(v, q)
    v, f = drop_crumbs(v, f)
    if len(f) and nonmanifold_edges(f):
        v, f = _remesh(v, f, h)
        v = _A().project_to_surface(fn, v, h, 3)
        v, f = drop_crumbs(v, f)
    return v, f


def decimate_arrays(v, f, target, _depth=0):
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
    v2, f2 = compact(v2, f2) if len(f2) else (v2, f2)
    if len(f2) > 1.25 * target and _depth < 3:
        # collapse stalls at non-manifold spots: weld, then decimate the result again
        v2, f2 = _weld(v2, f2)
        return decimate_arrays(v2, f2, target, _depth + 1)
    return v2, f2


def _weld(v, f, eps=1e-6):
    """Merge coincident vertices and drop degenerate triangles."""
    key = np.round(v / eps).astype(np.int64)
    _u, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    inv = inv.ravel()
    f2 = inv[f]
    ok = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2])
    return compact(v[idx], f2[ok])


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
    if n in (2, 3):
        hmm = 15.0                      # upper ribs at the top of the 12-15 mm range (front spaces <= 25 mm)
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
    elif n in (2, 3):
        hv = [0.0080, 0.0068, 0.75 * H, H, 1.13 * H, 1.05 * H]
        tv = [0.0075, 0.0055, 0.0060, Tk, Tk, 0.0080]
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
HUM_HEAD_R = BN.HUMERUS["head_d_mm"] / 2000.0
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
    extra = [(0.100, 0.089, 1.410), (0.110, 0.080, 1.385), (0.092, 0.094, 1.440)]     # convex back
    blade = Sheet(_pca_frame(outline), outline, extra,
                  thick=lambda u, v, e: 0.0024 + 0.0020 * np.exp(-(e / 0.004) ** 2))
    lat = [Ia, (0.100, 0.093, 1.340), (0.118, 0.073, 1.362), (0.137, 0.046, 1.392)]
    med = [Sa, root, (0.079, 0.103, 1.390), Ia]
    crest = [(0.077, 0.100, 1.438), (0.105, 0.096, 1.447), (0.138, 0.080, 1.452), (0.166, 0.062, 1.456),
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


def _smooth_loop(pts, n=6):
    """Closed Catmull-Rom densification of an outline (list of 3D points)."""
    P = np.asarray(pts, float)
    out = []
    K = len(P)
    for i in range(K):
        p0, p1, p2, p3 = P[i - 1], P[i], P[(i + 1) % K], P[(i + 2) % K]
        for s in range(n):
            t = s / n
            t2, t3 = t * t, t * t * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2
                              + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return np.array(out)


def hip_bone_sdf():
    """Left os coxae: fan-shaped wing with a concave iliac fossa (2-4 mm) between a thick S-curved
    crest and borders, iliac pillar from the tubercle to the acetabulum, acetabulum (socket for
    the femoral head + cartilage, lunate rim, inferior notch), pubic body and rami, ischium and
    tuberosity, obturator foramen, pelvic brim, ischial spine and the sciatic notches."""
    A = _A()
    P = BN.PELVIS
    asis, aiis, top, tub = (np.array(P[k]) for k in ("asis", "aiis", "iliac_crest_top", "iliac_tubercle"))
    psis = np.array(P["psis"])
    crest_back = np.array((0.098, 0.070, 1.060))
    piis = np.array((0.052, 0.086, 0.986))
    notch = np.array((0.068, 0.056, 0.950))
    acet_top = ACET_C + np.array((0.002, 0.006, 0.036))
    ctrl = [asis, tub, top, (0.121, 0.052, 1.064), crest_back, (0.064, 0.086, 1.042), psis, piis,
            (0.062, 0.070, 0.966), notch, (0.078, 0.030, 0.950), acet_top, (0.100, -0.038, 0.952), aiis,
            (0.114, -0.060, 0.974)]
    outline = _smooth_loop(ctrl, 5)
    fr = _pca_frame(outline)
    outer = fr.R[2] if fr.R[2] @ np.array((0.66, 0.40, -0.61)) > 0 else -fr.R[2]   # gluteal (convex) side
    fossa = [np.array(p) + outer * dz for p, dz in (((0.108, 0.010, 1.020), 0.0105), ((0.090, 0.035, 1.000), 0.0070),
                                                    ((0.118, -0.028, 1.012), 0.0070), ((0.100, 0.020, 0.985), 0.0055),
                                                    ((0.120, 0.012, 1.045), 0.0060))]
    wing = Sheet(fr, outline, fossa, thick=lambda u, v, e: 0.0028 + 0.0045 * np.exp(-(e / 0.007) ** 2))
    crest = [asis, tub, top, (0.121, 0.052, 1.064), crest_back, (0.064, 0.086, 1.042), psis]
    crest_r = [0.0055, 0.0072, 0.0062, 0.0058, 0.0058, 0.0060, 0.0068]
    post_border = [psis, piis, (0.060, 0.072, 0.968), notch, (0.058, 0.043, 0.925),
                   np.array(P["ischial_spine"])]
    ant_border = [asis, (0.117, -0.060, 0.975), aiis, (0.098, -0.046, 0.945)]
    pillar = [tub, (0.118, -0.018, 1.010), (0.102, -0.006, 0.965)]
    brim = [(0.050, 0.052, 0.996), (0.060, 0.030, 0.972), (0.070, -0.004, 0.948), (0.068, -0.036, 0.930),
            (0.048, -0.056, 0.920), (0.028, -0.066, 0.914)]
    sup_ramus = [(0.082, -0.028, 0.928), (0.052, -0.056, 0.915), (0.026, -0.063, 0.906)]
    inf_ramus = [(0.008, -0.054, 0.868), (0.026, -0.036, 0.852), (0.044, -0.004, 0.845),
                 np.array(P["ischial_tuberosity"]) + np.array((0.0, -0.004, 0.0))]
    isch = [ACET_C + np.array((-0.008, 0.020, -0.018)), (0.066, 0.028, 0.880), (0.058, 0.024, 0.853)]
    sacrum_fn = sacrum_sdf()[0]
    pub_axes = np.array([EX, _n((0.0, 0.94, 0.34)), _n((0.0, -0.34, 0.94))])

    def fn(x, y, z):
        d = wing(x, y, z)
        d = smin(d, A.sd_polyline(x, y, z, crest, crest_r)[0], 0.007)
        d = smin(d, A.sd_polyline(x, y, z, post_border, [0.0065, 0.0060, 0.0062, 0.0082, 0.0085, 0.0040])[0],
                 0.006)
        d = smin(d, A.sd_polyline(x, y, z, ant_border, [0.0050, 0.0042, 0.0055, 0.0072])[0], 0.005)
        d = smin(d, A.sd_polyline(x, y, z, pillar, [0.0065, 0.0075, 0.0110])[0], 0.008)
        # auricular (SI) part: thick posterior ilium
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.060, 0.064, 0.994), (0.010, 0.020, 0.030)), 0.008)
        # body around the acetabulum
        body = A.sd_sphere(x, y, z, ACET_C, 0.0345)
        body = smin(body, A.sd_ellipsoid(x, y, z, ACET_C + np.array((-0.012, 0.012, 0.020)),
                                         (0.017, 0.024, 0.024)), 0.010)
        d = smin(d, body, 0.010)
        d = smin(d, A.sd_polyline(x, y, z, brim, [0.0062, 0.0058, 0.0060, 0.0060, 0.0062, 0.0055])[0], 0.004)
        d = smin(d, A.sd_polyline(x, y, z, sup_ramus, [0.0095, 0.0082, 0.0078])[0], 0.005)
        pub = ebox(x, y, z, (0.0130, -0.0605, 0.889), (0.0105, 0.0065, 0.0215), pub_axes, rnd=0.0055)
        d = smin(d, pub, 0.006)
        d = smin(d, A.sd_ellipsoid(x, y, z, np.array(P["pubic_tubercle"]), (0.0045, 0.0045, 0.0045)), 0.003)
        d = smin(d, A.sd_polyline(x, y, z, inf_ramus, [0.0055, 0.0052, 0.0058, 0.0080])[0], 0.005)
        d = smin(d, A.sd_polyline(x, y, z, isch, [0.0115, 0.0110, 0.0105])[0], 0.008)
        d = smin(d, A.sd_ellipsoid(x, y, z, np.array(P["ischial_tuberosity"]) + np.array((0.002, 0.003, 0.004)),
                                   (0.0110, 0.0140, 0.0180)), 0.006)
        # obturator foramen (open)
        obt = ell3(x, y, z, np.array(P["obturator_centre"]) + np.array((0.002, 0.004, 0.0)),
                   (0.0235, 0.0165, 0.016), OBT_AXES)
        d = smax(d, -obt, 0.004)
        # acetabulum: socket = femoral head + 2 x 2 mm cartilage; open beyond the rim plane; notch
        d = smax(d, -A.sd_sphere(x, y, z, ACET_C, FEM_HEAD_R + 0.0040), 0.0015)
        mouth = np.maximum(-plane(x, y, z, ACET_C + ACET_DIR * 0.004, ACET_DIR), A.sd_sphere(x, y, z, ACET_C, 0.050))
        d = smax(d, -mouth, 0.003)
        notch_c = ACET_C + np.array((0.006, 0.004, -0.027))
        d = smax(d, -A.sd_ellipsoid(x, y, z, notch_c, (0.011, 0.010, 0.010)), 0.003)
        # pubic symphysis gap (disc 2 x 2.5 mm) and SI joint clearance to the sacrum
        d = smax(d, 0.0025 - x, 0.002)
        d = np.maximum(d, -(sacrum_fn(x, y, z) - 0.0012))
        return d
    return fn, (np.array([0.0, -0.085, 0.815]), np.array([0.165, 0.110, 1.085]))


# ===========================================================================
# Long bones (left) at the rig joint centres [RB §7.2, §7.3]; each returns (outer, box, core)
# where ``core`` is the marrow core SDF (outer inset by the cortex, diaphysis only).
# ===========================================================================
ELB_L = np.array(BN.HUMERUS["elbow_centre"], float)
WRI_L = np.array(LM.landmark("wrist_centre_L_apose"), float)
HIP_L = np.array(BN.FEMUR["head_centre"], float)
KNEE_L = np.array(BN.FEMUR["knee_centre"], float)
ANK_L = np.array(BN.KNEE_LEG["ankle_centre"], float)
EPI_AX = _n(np.array(LM.landmark("lateral_epicondyle_L_apose")) - np.array(LM.landmark("medial_epicondyle_L_apose")))


def _core(outer, cortex, a, b, k=0.006):
    """Marrow core: the outer surface inset by ``cortex`` between the planes through a and b."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    u = _n(b - a)

    def fn(x, y, z):
        d = outer(x, y, z) + cortex
        clip = np.maximum(-plane(x, y, z, a, u), plane(x, y, z, b, u))
        return smax(d, clip, k)
    return fn


def humerus_sdf():
    """Humerus (left): retroverted head, anatomical neck, greater/lesser tubercles with the
    intertubercular groove, shaft with deltoid tuberosity, flattened distal end with medial and
    lateral epicondyles, capitulum, trochlea, olecranon and coronoid fossae."""
    A = _A()
    E, G = ELB_L, GH_L
    D, LAT = ARM_D, ARM_LAT
    # head faces medial + up (neck-shaft 135 deg) and back (retroversion 25 deg)
    hd = _n(math.cos(math.radians(45)) * (-LAT) + math.sin(math.radians(45)) * (-D))
    hd = _n(hd * math.cos(math.radians(25)) + EY * math.sin(math.radians(25)))
    s0 = G + 0.010 * LAT + 0.030 * D
    s1 = E - 0.040 * D + 0.004 * EY
    mid = 0.5 * (s0 + s1) + 0.002 * LAT
    kn = [0.0, 0.15, 0.5, 0.8, 1.0]
    rn = [0.0150, 0.0120, 0.0100, 0.0092, 0.0090]         # antero-posterior half
    rb = [0.0155, 0.0120, 0.0110, 0.0140, 0.0195]         # medio-lateral half (flattens distally)

    def sec(n, b, t):
        return gg_superellipse(n, b, interp(t, kn, rn), interp(t, kn, rb), 2.3)
    shaft = Tube([s0 - 0.012 * D, mid, s1], sec, ref_fn=lambda P: np.tile(ANT, (len(P), 1)), step=0.003,
                 round_ends=True)
    cap_c = E + 0.0140 * EPI_AX - 0.0020 * EY + 0.0010 * D
    tro_c = E - 0.0080 * EPI_AX + 0.0010 * D
    epi_m = np.array(LM.landmark("medial_epicondyle_L_apose"))
    epi_l = np.array(LM.landmark("lateral_epicondyle_L_apose"))
    lat_ax = np.array([EPI_AX, _n(np.cross(D, EPI_AX)), _n(np.cross(EPI_AX, np.cross(D, EPI_AX)))])

    def fn(x, y, z):
        head = A.sd_sphere(x, y, z, G, HUM_HEAD_R)
        head = smax(head, -plane(x, y, z, G - hd * 0.007, hd), 0.004)             # anatomical neck
        neck = A.sd_capsule(x, y, z, G - hd * 0.004, s0, 0.0180, 0.0150)
        d = smin(head, neck, 0.006)
        gt = A.sd_ellipsoid(x, y, z, G + 0.0175 * LAT + 0.0040 * D - 0.0030 * EY, (0.0100, 0.0120, 0.0135))
        lt = A.sd_ellipsoid(x, y, z, G + 0.0040 * LAT + 0.0150 * D - 0.0150 * EY, (0.0060, 0.0065, 0.0085))
        d = smin(d, smin(gt, lt, 0.004), 0.006)
        groove = A.sd_capsule(x, y, z, G + 0.0120 * LAT - 0.0165 * EY - 0.004 * D,
                              G + 0.0110 * LAT - 0.0150 * EY + 0.045 * D, 0.0030)
        d = smax(d, -groove, 0.002)
        d = smin(d, shaft(x, y, z), 0.010)
        d = smin(d, A.sd_ellipsoid(x, y, z, G + 0.105 * D + 0.0115 * LAT, (0.0045, 0.0060, 0.0180)), 0.006)
        # distal end: epicondylar plate, epicondyles, capitulum, trochlea
        plate = ell3(x, y, z, E - 0.024 * D + 0.003 * EY, (0.0235, 0.0100, 0.0300), lat_ax)
        d = smin(d, plate, 0.012)
        d = smin(d, A.sd_ellipsoid(x, y, z, E - 0.0240 * EPI_AX - 0.004 * D + 0.004 * EY, (0.0080, 0.0075, 0.0100)),
                 0.009)
        d = smin(d, A.sd_ellipsoid(x, y, z, E + 0.0215 * EPI_AX - 0.006 * D + 0.002 * EY, (0.0065, 0.0070, 0.0100)),
                 0.009)
        cap = A.sd_sphere(x, y, z, cap_c, 0.0095)
        tro = A.sd_capsule(x, y, z, tro_c - 0.0110 * EPI_AX, tro_c + 0.0095 * EPI_AX, 0.0115)
        tro = smin(tro, A.sd_capsule(x, y, z, tro_c - 0.0125 * EPI_AX + 0.0020 * D, tro_c - 0.0080 * EPI_AX
                                     + 0.0020 * D, 0.0130), 0.002)                      # medial trochlear lip
        tgroove = _torus(x, y, z, tro_c + 0.0005 * EPI_AX, EPI_AX, 0.0122, 0.0030)
        tro = smax(tro, -tgroove, 0.0015)
        d = smin(d, smin(cap, tro, 0.002), 0.004)
        # fossae: olecranon (posterior), coronoid + radial (anterior)
        d = smax(d, -A.sd_ellipsoid(x, y, z, E - 0.018 * D + 0.0135 * EY - 0.004 * EPI_AX, (0.0095, 0.0060, 0.0095)),
                 0.002)
        d = smax(d, -A.sd_ellipsoid(x, y, z, E - 0.016 * D - 0.0125 * EY - 0.004 * EPI_AX, (0.0070, 0.0040, 0.0065)),
                 0.002)
        return d
    core = _core(fn, 0.0048, G + 0.070 * D, E - 0.060 * D)
    lo = np.minimum(G, E) - 0.04
    hi = np.maximum(G, E) + 0.04
    return fn, (lo, hi), core


def _torus(x, y, z, c, axis, R, r):
    """Torus around ``axis`` through ``c`` (major R, minor r)."""
    ax = _n(axis)
    dx, dy, dz = x - c[0], y - c[1], z - c[2]
    h = dx * ax[0] + dy * ax[1] + dz * ax[2]
    q = np.sqrt(np.maximum(dx * dx + dy * dy + dz * dz - h * h, 0.0))
    return np.sqrt((q - R) ** 2 + h * h) - r


RAD_HEAD_C = ELB_L + 0.0140 * EPI_AX + 0.0190 * ARM_D - 0.0025 * EY


def radius_sdf():
    """Radius (left, neutral forearm: thumb forward): disc-shaped head under the capitulum, neck,
    radial tuberosity, laterally bowed shaft with a sharp interosseous border, broad distal end
    with the styloid on the thumb side (-Y) and the dorsal tubercle."""
    A = _A()
    D, LAT = ARM_D, ARM_LAT
    hc = RAD_HEAD_C
    dist_c = WRI_L - 0.0150 * D + np.array((0.0, -0.0010, 0.0))
    p = [hc + 0.012 * D, hc + 0.035 * D + 0.002 * LAT, 0.5 * (hc + dist_c) + 0.006 * LAT - 0.004 * EY,
         dist_c - 0.030 * D - 0.002 * EY]
    kn = [0.0, 0.2, 0.6, 1.0]
    rn = [0.0062, 0.0068, 0.0062, 0.0085]
    rb = [0.0062, 0.0070, 0.0075, 0.0110]

    def sec(n, b, t):
        s = gg_superellipse(n, b, interp(t, kn, rn), interp(t, kn, rb), 2.2)
        # interosseous border: a sharp edge toward the ulna (+Y side)
        ridge = A.ellipse2(n - 0.0, b - interp(t, kn, rb) * 0.85, 0.0018, 0.0030)
        return smin(s, ridge, 0.0015)
    shaft = Tube(p, sec, ref_fn=lambda P: np.tile(LAT, (len(P), 1)), step=0.003, round_ends=True)
    dax = np.array([D, EY, _n(np.cross(D, EY))])

    def fn(x, y, z):
        head = A.sd_capsule(x, y, z, hc - 0.0035 * D, hc + 0.0040 * D, 0.0105)
        head = smax(head, -A.sd_sphere(x, y, z, hc - 0.0115 * D, 0.0105), 0.001)      # concave fovea
        d = smin(head, A.sd_capsule(x, y, z, hc + 0.003 * D, hc + 0.018 * D, 0.0065, 0.0060), 0.004)
        d = smin(d, A.sd_ellipsoid(x, y, z, hc + 0.030 * D + 0.004 * EY - 0.002 * LAT, (0.0050, 0.0055, 0.0085)),
                 0.004)
        d = smin(d, shaft(x, y, z), 0.008)
        dist = ebox(x, y, z, dist_c, (0.0100, 0.0150, 0.0095), dax, rnd=0.0060)
        d = smin(d, dist, 0.008)
        sty = A.sd_capsule(x, y, z, dist_c - 0.0110 * EY, WRI_L - 0.0010 * D - 0.0150 * EY + 0.001 * LAT,
                           0.0050, 0.0026)
        d = smin(d, sty, 0.004)
        d = smin(d, A.sd_ellipsoid(x, y, z, dist_c + 0.0095 * LAT - 0.002 * EY - 0.004 * D, (0.0050, 0.0030, 0.0030)),
                 0.002)
        # carpal articular surface (concave) and the ulnar notch
        d = smax(d, -A.sd_sphere(x, y, z, WRI_L + 0.004 * D + np.array((0.0, -0.001, 0.0)), 0.0125), 0.002)
        return d
    core = _core(fn, 0.0028, hc + 0.045 * D, dist_c - 0.035 * D)
    lo = np.minimum(ELB_L, WRI_L) - 0.035
    hi = np.maximum(ELB_L, WRI_L) + 0.035
    return fn, (lo, hi), core


def ulna_sdf():
    """Ulna (left): olecranon and coronoid around the trochlear notch (clears the trochlea),
    radial notch, triangular shaft thinning distally, head and styloid (posteromedial, +Y)."""
    A = _A()
    D, LAT = ARM_D, ARM_LAT
    tro_c = ELB_L - 0.0080 * EPI_AX + 0.0010 * D
    head_c = WRI_L - 0.0290 * D + np.array((0.0, 0.0140, 0.0)) - 0.0020 * LAT
    p = [ELB_L + 0.010 * D + 0.0100 * EY - 0.0060 * EPI_AX, ELB_L + 0.060 * D + 0.0110 * EY - 0.004 * EPI_AX,
         0.5 * (ELB_L + head_c) + 0.010 * EY * 0.0, head_c - 0.012 * D]
    kn = [0.0, 0.25, 0.7, 1.0]
    rn = [0.0105, 0.0085, 0.0062, 0.0058]
    rb = [0.0085, 0.0072, 0.0058, 0.0062]

    def sec(n, b, t):
        s = gg_superellipse(n, b, interp(t, kn, rn), interp(t, kn, rb), 2.2)
        ridge = A.ellipse2(n, b + interp(t, kn, rb) * 0.85, 0.0017, 0.0030)       # interosseous border (-Y)
        return smin(s, ridge, 0.0015)
    shaft = Tube(p, sec, ref_fn=lambda P: np.tile(LAT, (len(P), 1)), step=0.003, round_ends=True)

    def fn(x, y, z):
        prox = A.sd_ellipsoid(x, y, z, tro_c + 0.0060 * EY - 0.0020 * D, (0.0130, 0.0120, 0.0150))
        olec = A.sd_ellipsoid(x, y, z, ELB_L - 0.0150 * D + 0.0150 * EY - 0.0060 * EPI_AX, (0.0100, 0.0095, 0.0100))
        coro = A.sd_ellipsoid(x, y, z, ELB_L + 0.0140 * D - 0.0070 * EY - 0.0060 * EPI_AX, (0.0085, 0.0070, 0.0075))
        d = smin(smin(prox, olec, 0.006), coro, 0.005)
        # trochlear notch: clear the trochlea + 2 x 1.5 mm cartilage; radial notch clears the radial head
        d = smax(d, -A.sd_capsule(x, y, z, tro_c - 0.014 * EPI_AX, tro_c + 0.012 * EPI_AX, 0.0145), 0.0015)
        d = smax(d, -A.sd_capsule(x, y, z, RAD_HEAD_C - 0.005 * D, RAD_HEAD_C + 0.006 * D, 0.0125), 0.0015)
        d = smin(d, shaft(x, y, z), 0.008)
        d = smin(d, A.sd_sphere(x, y, z, head_c, 0.0078), 0.005)
        sty = A.sd_capsule(x, y, z, head_c + 0.0040 * EY, WRI_L - 0.0195 * D + np.array((0.0, 0.0205, 0.0)),
                           0.0034, 0.0018)
        d = smin(d, sty, 0.003)
        return d
    core = _core(fn, 0.0028, ELB_L + 0.050 * D, head_c - 0.030 * D)
    lo = np.minimum(ELB_L, WRI_L) - 0.04
    hi = np.maximum(ELB_L, WRI_L) + 0.04
    return fn, (lo, hi), core


def femur_sdf():
    """Femur (left): head with fovea, neck (127 deg, anteversion 12 deg), greater trochanter with
    trochanteric fossa, lesser trochanter, intertrochanteric crest, anteriorly bowed shaft with
    linea aspera, flared metaphysis, condyles, epicondyles, intercondylar notch, patellar groove."""
    A = _A()
    F = BN.FEMUR
    H = HIP_L
    s_top = np.array((0.124, 0.004, 0.884))
    s_bot = np.array((0.094, 0.018, 0.575))
    mid = 0.5 * (s_top + s_bot) + np.array((0.0, -0.008, 0.0))
    kn = [0.0, 0.15, 0.5, 0.85, 1.0]
    rn = [0.0150, 0.0138, 0.0135, 0.0150, 0.0180]          # AP half
    rb = [0.0165, 0.0148, 0.0145, 0.0180, 0.0240]          # ML half

    def sec(n, b, t):
        s = gg_superellipse(n, b, interp(t, kn, rn), interp(t, kn, rb), 2.1)
        la = A.ellipse2(n + interp(t, kn, rn) * 0.92, b, 0.0035, 0.0032)          # linea aspera (posterior)
        return smin(s, la + 0.0006 * (1 - sstep(0.2, 0.5, t) * (1 - sstep(0.7, 0.9, t))) * 3, 0.002)
    shaft = Tube([s_top + np.array((0.004, -0.001, 0.02)), s_top, mid, s_bot], sec,
                 ref_fn=lambda P: np.tile(ANT, (len(P), 1)), step=0.003, round_ends=True)
    neck_end = np.array((0.128, -0.002, 0.896))
    K = KNEE_L

    def dsec(n, b, t):
        kk = [0.0, 0.35, 0.7, 1.0]
        return gg_superellipse(b, n, interp(t, kk, [0.0180, 0.0240, 0.0360, 0.0400]),
                               interp(t, kk, [0.0160, 0.0180, 0.0240, 0.0270]), interp(t, kk, [2.2, 2.3, 2.7, 3.0]))
    dist = Tube([(0.096, 0.017, 0.610), (0.093, 0.019, 0.560), (0.092, 0.022, 0.520), (0.092, 0.024, 0.500)], dsec,
                ref_fn=lambda P: np.tile(ANT, (len(P), 1)), step=0.002, round_ends=True)
    cz = 0.5045

    def fn(x, y, z):
        head = A.sd_sphere(x, y, z, H, FEM_HEAD_R)
        head = smax(head, -A.sd_sphere(x, y, z, H + _n(np.array((-0.55, 0.15, -0.6))) * 0.025, 0.004), 0.001)
        nk = ecap(x, y, z, H, neck_end, (0.0150, 0.0160), (0.0125, 0.0150), EZ)
        d = smin(head, nk, 0.007)
        gt = A.sd_ellipsoid(x, y, z, (0.140, 0.006, 0.899), (0.0170, 0.0210, 0.0260))
        d = smin(d, gt, 0.008)
        d = smax(d, -A.sd_ellipsoid(x, y, z, (0.130, 0.014, 0.918), (0.006, 0.007, 0.009)), 0.002)   # troch. fossa
        lt = A.sd_ellipsoid(x, y, z, np.array(F["lesser_trochanter"]) + np.array((0.006, 0.002, 0.002)),
                            (0.0085, 0.0090, 0.0120))
        d = smin(d, lt, 0.008)
        calcar = A.sd_ellipsoid(x, y, z, (0.104, 0.006, 0.876), (0.0200, 0.0150, 0.0260))
        d = smin(d, calcar, 0.010)
        d = smin(d, A.sd_capsule(x, y, z, (0.140, 0.020, 0.902), (0.090, 0.016, 0.866), 0.0055), 0.006)  # crest
        d = smin(d, shaft(x, y, z), 0.012)
        # distal end: metaphysis, condyles, epicondyles
        d = smin(d, dist(x, y, z), 0.010)
        mc = A.sd_ellipsoid(x, y, z, (0.071, 0.024, cz), (0.0140, 0.0300, 0.0230))
        lc = A.sd_ellipsoid(x, y, z, (0.113, 0.022, cz + 0.001), (0.0145, 0.0295, 0.0225))
        d = smin(d, smin(mc, lc, 0.010), 0.008)
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.058, 0.022, 0.518), (0.0070, 0.0120, 0.0120)), 0.009)
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.127, 0.020, 0.518), (0.0065, 0.0110, 0.0110)), 0.009)
        # intercondylar notch (posterior-inferior) and patellar groove (anterior)
        d = smax(d, -A.sd_ellipsoid(x, y, z, (0.092, 0.042, 0.488), (0.0095, 0.0260, 0.0200)), 0.002)
        d = smax(d, -A.sd_capsule(x, y, z, (0.093, -0.0165, 0.545), (0.092, -0.0120, 0.495), 0.0055), 0.003)
        return d
    core = _core(fn, 0.0070, (0.119, 0.007, 0.840), (0.095, 0.017, 0.600), k=0.010)
    return fn, (np.array((0.035, -0.045, 0.465)), np.array((0.185, 0.075, 0.955))), core


def patella_sdf():
    """Patella (left): rounded triangle with the apex down, thick centre, ridged articular back;
    the front ~6 mm under the skin (lean site 4-8 mm)."""
    A = _A()
    c = np.array(BN.KNEE_LEG["patella_centre"]) + np.array((0.0, 0.0045, 0.0))

    def fn(x, y, z):
        zz = (z - c[2]) / 0.0265
        sx = 1.0 / (1.0 - 0.40 * sstep(0.0, -1.0, zz))               # narrower towards the apex
        d = A.sd_ellipsoid((x - c[0]) * sx, y, z, (0.0, c[1], c[2]), (0.0255, 0.0115, 0.0265)) / sx
        ridge = A.sd_ellipsoid(x, y, z, (c[0] - 0.002, c[1] + 0.006, c[2]), (0.0060, 0.0065, 0.0200))
        return smin(d, ridge, 0.004)
    return fn, (c - 0.035, c + 0.035)


def tibia_sdf():
    """Tibia (left): plateau with two condyles flaring out of the shaft, dished facets and the
    intercondylar eminence, tuberosity, triangular shaft (sharp anterior crest, subcutaneous
    anteromedial face), quadrilateral distal end with a flat plafond and the medial malleolus."""
    A = _A()
    K = BN.KNEE_LEG
    top = K["tibial_plateau_z"] - 0.0025
    plaf = K["tibial_plafond_z"] + 0.0035
    p = [(0.092, 0.008, 0.450), (0.093, 0.026, 0.300), (0.091, 0.040, 0.170), (0.090, 0.046, plaf + 0.006)]
    kn = [0.0, 0.12, 0.45, 0.78, 1.0]
    rA = [0.0165, 0.0135, 0.0118, 0.0120, 0.0185]      # centre -> anterior crest
    rP = [0.0150, 0.0115, 0.0102, 0.0105, 0.0175]      # centre -> posterior surface
    rW = [0.0220, 0.0150, 0.0112, 0.0125, 0.0215]      # half width (medio-lateral)
    sq = [2.4, 2.2, 2.2, 2.4, 3.2]                     # rounded square at the distal end

    def sec(n, b, t):
        a_, p_, w_, e_ = interp(t, kn, rA), interp(t, kn, rP), interp(t, kn, rW), interp(t, kn, sq)
        crest = np.clip(1.0 - np.abs(t - 0.45) / 0.45, 0.0, 1.0)            # sharp crest mid-shaft
        s_front = gg_superellipse(n + 0.25 * p_ * crest, b, a_ + 0.25 * p_ * crest, w_, e_ - 1.0 * crest)
        s_back = gg_superellipse(n, b, p_, w_, e_)
        return np.where(n > 0, s_front, s_back)
    shaft = Tube(p, sec, ref_fn=lambda P: np.tile(ANT, (len(P), 1)), step=0.003, round_ends=True)
    mm_tip = np.array(K["medial_malleolus_tip"])

    def csec(n, b, t):
        kk = [0.0, 0.10, 0.30, 0.55, 0.80, 1.0]
        return gg_superellipse(b, n, interp(t, kk, [0.0385, 0.0378, 0.0325, 0.0265, 0.0222, 0.0205]),
                               interp(t, kk, [0.0245, 0.0245, 0.0228, 0.0200, 0.0178, 0.0165]), 2.15)
    cond = Tube([(0.092, 0.024, top), (0.092, 0.020, top - 0.030), (0.092, 0.013, top - 0.062)], csec,
                ref_fn=lambda P: np.tile(EY, (len(P), 1)), step=0.002, round_ends=False)

    def fn(x, y, z):
        d = smin(cond(x, y, z), shaft(x, y, z), 0.012)
        d = smax(d, z - top, 0.006)                                           # rounded plateau rim
        for dx in (-0.020, 0.019):
            d = smax(d, -A.sd_ellipsoid(x, y, z, (0.092 + dx, 0.024, top + 0.0045), (0.0140, 0.0170, 0.0055)), 0.002)
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.092, 0.024, top - 0.001), (0.0040, 0.0060, 0.0048)), 0.002)
        d = smin(d, A.sd_ellipsoid(x, y, z, np.array(K["tibial_tuberosity"]) + np.array((0.0, 0.0180, 0.002)),
                                   (0.0110, 0.0090, 0.0180)), 0.009)
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.121, 0.036, 0.456), (0.0080, 0.0080, 0.0070)), 0.006)  # fibular facet
        mm = A.sd_capsule(x, y, z, (0.073, 0.046, 0.102), mm_tip + np.array((0.0, 0.0, 0.0055)), 0.0085, 0.0055)
        d = smax(d, plaf - z, 0.003)                                          # flat plafond
        d = smin(d, mm, 0.006)
        d = smax(d, -A.sd_ellipsoid(x, y, z, (0.124, 0.052, 0.100), (0.0055, 0.010, 0.020)), 0.002)  # fibular notch
        return d
    core = _core(fn, 0.0058, (0.092, 0.012, 0.410), (0.091, 0.043, 0.150), k=0.010)
    return fn, (np.array((0.040, -0.040, 0.050)), np.array((0.145, 0.080, 0.490))), core


def fibula_sdf():
    """Fibula (left): head with apex, neck, slender shaft, lateral malleolus."""
    A = _A()
    K = BN.KNEE_LEG
    hc = np.array(K["fibular_head"]) + np.array((0.0, 0.0, -0.004))
    lm = np.array(K["lateral_malleolus_tip"])
    p = [hc + np.array((0.0, 0.002, -0.012)), (0.128, 0.045, 0.330), (0.127, 0.054, 0.200), (0.126, 0.058, 0.090)]

    def sec(n, b, t):
        r = interp(t, [0.0, 0.2, 0.8, 1.0], [0.0068, 0.0072, 0.0068, 0.0085])
        return gg_superellipse(n, b, r * 0.95, r, 2.0)
    shaft = Tube(p, sec, ref_fn=lambda P: np.tile(ANT, (len(P), 1)), step=0.003, round_ends=True)

    def fn(x, y, z):
        head = A.sd_ellipsoid(x, y, z, hc, (0.0120, 0.0110, 0.0100))
        apex = A.sd_capsule(x, y, z, hc, hc + np.array((0.003, 0.005, 0.0075)), 0.0050, 0.0028)
        d = smin(head, apex, 0.003)
        d = smin(d, shaft(x, y, z), 0.008)
        mal = A.sd_ellipsoid(x, y, z, lm + np.array((-0.0055, -0.002, 0.021)), (0.0085, 0.0115, 0.0210))
        d = smin(d, mal, 0.008)
        return d
    core = _core(fn, 0.0030, hc - np.array((0.0, 0.0, 0.045)), (0.131, 0.058, 0.130), k=0.006)
    return fn, (np.array((0.105, 0.010, 0.030)), np.array((0.150, 0.080, 0.475))), core


# ===========================================================================
# Hand and foot bones (left).  Sub-bones are separate islands of the "hand_L" / "foot_L" piece;
# each carries its own rigid bone (hand / thumb / fingers, foot / toes).  Packed short bones
# (carpals, tarsals) are separated by Voronoi planes with a 1.2 mm joint gap, so none overlap.
# Finger and toe layout follows the skin's relaxed-curl fingers (placeholder / B1 hand).
# ===========================================================================
MCP3 = np.array(LM.landmark("mcp3_L_apose"), float)
CARPAL_C = np.array(BN.HAND_BONES["carpal_centre"], float)
THUMB_PTS = (np.array((0.468, -0.005, 0.915)), np.array((0.482, -0.021, 0.878)), np.array((0.500, -0.030, 0.840)))
FINGER_LAYOUT = [(-0.001, 0.080, 0.0095, 0.0080, 0.002), (0.020, 0.090, 0.0098, 0.0082, 0.0),
                 (0.038, 0.084, 0.0092, 0.0078, 0.003), (0.054, 0.068, 0.0082, 0.0070, 0.010)]
CURL_DEG = (8.0, 18.0, 28.0)
HAND_AX = np.array([ARM_D, EY, ARM_NM])        # distal, ulnar (+Y; thumb is -Y), palmar


def finger_polyline(y0, length, setback):
    """MCP -> PIP -> DIP -> tip of a left finger in the relaxed A-pose curl (skin layout)."""
    base = MCP3 - setback * ARM_D + np.array([0.0, y0 - MCP3[1], 0.0])
    seg = np.array([0.45, 0.30, 0.25]) * length
    pts = [base]
    for s_, ang in zip(seg, CURL_DEG):
        a = math.radians(ang)
        pts.append(pts[-1] + s_ * (math.cos(a) * ARM_D + math.sin(a) * ARM_NM))
    return np.array(pts)


def _cluster(items, gap=0.0012):
    """Separate packed ellipsoids by Voronoi planes: [(name, centre, radii, axes, extra_fn|None)] ->
    [(name, fn, box)] with every pair at least ``gap`` apart."""
    A = _A()
    C = np.array([it[1] for it in items])
    out = []
    for i, (name, c, r, axes, extra) in enumerate(items):
        def fn(x, y, z, i=i, c=c, r=r, axes=axes, extra=extra):
            d = ell3(x, y, z, c, r, axes)
            if extra is not None:
                d = smin(d, extra(x, y, z), 0.002)
            for j in range(len(C)):
                if j == i:
                    continue
                n = C[j] - C[i]
                L = np.linalg.norm(n)
                m = 0.5 * (C[i] + C[j])
                d = np.maximum(d, plane(x, y, z, m, n / L) + 0.5 * gap)
            return d
        R = max(r) + 0.006
        out.append((name, fn, (np.asarray(c) - R, np.asarray(c) + R)))
    return out


def _clip_near(fn, other, gap, lo, hi):
    """``fn`` with ``other`` (grown by ``gap``) carved away, evaluated only inside the box lo..hi."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)

    def g(x, y, z):
        d = fn(x, y, z)
        m = (x >= lo[0]) & (x <= hi[0]) & (y >= lo[1]) & (y <= hi[1]) & (z >= lo[2]) & (z <= hi[2])
        if m.any():
            o = other(x[m], y[m], z[m])
            d = d.copy()
            d[m] = np.maximum(d[m], -(o - gap))
        return d
    return g


def _clipped(fn, others, gap):
    """``fn`` with every SDF in ``others`` (grown by ``gap``) carved away."""
    def g(x, y, z):
        d = fn(x, y, z)
        for q in others:
            d = np.maximum(d, -(q(x, y, z) - gap))
        return d
    return g


def _hl(p):
    """Hand-local offset (distal, ulnar, palmar) from the carpal centre -> world."""
    return CARPAL_C + np.asarray(p, float) @ HAND_AX


def _long_small(a, b, r_base, r_shaft, r_head):
    """A short tubular bone (metacarpal, phalanx, metatarsal): base knob, waisted shaft, head."""
    A = _A()
    a, b = np.asarray(a, float), np.asarray(b, float)

    def fn(x, y, z):
        d = A.sd_capsule(x, y, z, a, b, r_base * 0.85, r_head * 0.8)
        h, _dd = A.seg_param(x, y, z, a, b)
        waist = (r_shaft - 0.5 * (r_base + r_head)) * np.sin(np.pi * h) ** 0.6
        d = d - waist                                  # waisted shaft
        d = smin(d, A.sd_sphere(x, y, z, a + 0.3 * r_base * _n(b - a), r_base), 0.002)
        d = smin(d, A.sd_sphere(x, y, z, b - 0.3 * r_head * _n(b - a), r_head), 0.002)
        return d
    R = max(r_base, r_head) + 0.004
    return fn, (np.minimum(a, b) - R, np.maximum(a, b) + R)


def hand_parts():
    """Left hand bones: [(name, fn, box, rigid bone)]: 8 carpals, 5 metacarpals, 14 phalanges."""
    ax = HAND_AX
    carpals = [("scaphoid", (-0.004, -0.012, 0.001), (0.0080, 0.0060, 0.0065), None),
               ("lunate", (-0.006, 0.001, 0.000), (0.0070, 0.0065, 0.0072), None),
               ("triquetrum", (-0.003, 0.013, -0.002), (0.0065, 0.0060, 0.0062), None),
               ("pisiform", (-0.002, 0.015, 0.009), (0.0045, 0.0040, 0.0045), None),
               ("trapezium", (0.012, -0.021, 0.003), (0.0068, 0.0062, 0.0068), None),
               ("trapezoid", (0.013, -0.009, 0.000), (0.0062, 0.0052, 0.0060), None),
               ("capitate", (0.011, 0.002, 0.000), (0.0110, 0.0060, 0.0072), None),
               ("hamate", (0.012, 0.013, 0.000), (0.0092, 0.0062, 0.0072), None)]
    items = [(n, _hl(p), r, ax, e) for n, p, r, e in carpals]
    rad = radius_sdf()[0]
    uln = ulna_sdf()[0]
    out = []
    for name, fn, box in _cluster(items):
        def g(x, y, z, fn=fn):
            d = fn(x, y, z)
            return np.maximum(np.maximum(d, -(rad(x, y, z) - 0.0015)), -(uln(x, y, z) - 0.0015))
        out.append((name, g, box, "hand_L"))
    bases_y = (-0.010, 0.000, 0.009, 0.017)
    for k, ((y0, L, r0, r1, sb), by) in enumerate(zip(FINGER_LAYOUT, bases_y)):
        P = finger_polyline(y0, L, sb)
        u0 = _n(P[1] - P[0])
        base = _hl((0.0215, by, 0.0))
        head = P[0] - 0.0040 * ARM_D
        fn, box = _long_small(base, head, 0.0048, 0.0036, 0.0060)
        out.append((f"metacarpal{k + 2}", fn, box, "hand_L"))
        # phalanges: proximal, middle, distal (distal tip 3 mm inside the skin)
        u1, u2 = _n(P[2] - P[1]), _n(P[3] - P[2])
        tip = P[3] + u2 * (0.75 * r1)
        segs = [(P[0] + u0 * 0.0080, P[1] - u0 * 0.0022, 0.0050, 0.0034, 0.0040),
                (P[1] + u1 * 0.0032, P[2] - u1 * 0.0020, 0.0040, 0.0028, 0.0033),
                (P[2] + u2 * 0.0028, tip - u2 * 0.0030, 0.0033, 0.0022, 0.0030)]
        for j, (a, b, rb_, rs, rh) in enumerate(segs):
            fn, box = _long_small(a, b, rb_, rs, rh)
            out.append((f"phalanx{k + 2}_{j + 1}", fn, box, "fingers_L"))
    # thumb: metacarpal from the trapezium (CMC) to the MCP, proximal + distal phalanx
    t0, t1, t2 = THUMB_PTS
    u = _n(t1 - t0)
    fn, box = _long_small(t0 + u * 0.0060, t1 - u * 0.0045, 0.0060, 0.0042, 0.0065)
    out.append(("metacarpal1", fn, box, "thumb_L"))
    v = _n(t2 - t1)
    fn, box = _long_small(t1 + v * 0.0075, t1 + v * 0.0310, 0.0055, 0.0038, 0.0045)
    out.append(("phalanx1_1", fn, box, "thumb_L"))
    fn, box = _long_small(t1 + v * 0.0345, t1 + v * 0.0485, 0.0045, 0.0030, 0.0036)
    out.append(("phalanx1_2", fn, box, "thumb_L"))
    return out


TARSAL_BOX = {"talus": ((0.075, 0.028, 0.038), (0.116, 0.080, 0.094)),
              "calcaneus": ((0.062, 0.000, 0.008), (0.132, 0.116, 0.066)),
              "navicular": ((0.062, -0.016, 0.032), (0.106, 0.012, 0.068)),
              "cuboid": ((0.104, -0.012, 0.016), (0.138, 0.024, 0.048)),
              "cuneiform_med": ((0.070, -0.034, 0.022), (0.096, -0.002, 0.060)),
              "cuneiform_int": ((0.085, -0.029, 0.030), (0.107, -0.001, 0.061)),
              "cuneiform_lat": ((0.096, -0.028, 0.026), (0.120, 0.002, 0.059))}
FOOT_AX = np.array([_n(np.cross(LM.FOOT_AXIS_L, EZ)), _n(LM.FOOT_AXIS_L), EZ])   # lateral, forward, up


def foot_parts():
    """Left foot bones: talus (trochlea, neck, head), calcaneus (tuber, sustentaculum), navicular,
    cuboid, three cuneiforms, five metatarsals, 14 toe phalanges."""
    A = _A()
    ax = FOOT_AX
    tib = tibia_sdf()[0]
    fib = fibula_sdf()[0]

    def talus(x, y, z):
        body = _A().extrude(gg_superellipse(x - 0.095, y - 0.053, 0.0140, 0.0165, 3.0), z - 0.066, 0.0140, 0.004)
        troch = np.maximum(np.abs(x - 0.0955) - 0.0138, np.sqrt((y - 0.053) ** 2 + (z - 0.0705) ** 2) - 0.0180)
        troch = smax(troch, -_torus(x, y, z, (0.0955, 0.053, 0.0705), EX, 0.0195, 0.0022), 0.001)   # central groove
        d = smin(body, troch, 0.003)
        neck = A.sd_capsule(x, y, z, (0.093, 0.040, 0.064), (0.090, 0.020, 0.057), 0.0095)
        head = A.sd_ellipsoid(x, y, z, (0.088, 0.012, 0.055), (0.0120, 0.0105, 0.0110))
        post = A.sd_ellipsoid(x, y, z, (0.097, 0.071, 0.058), (0.0060, 0.0050, 0.0050))
        return smin(smin(smin(d, neck, 0.005), head, 0.005), post, 0.003)

    def csec(n, b, t):
        return gg_superellipse(b, n, interp(t, [0.0, 0.3, 0.7, 1.0], [0.0135, 0.0140, 0.0130, 0.0120]),
                               interp(t, [0.0, 0.3, 0.7, 1.0], [0.0200, 0.0165, 0.0140, 0.0130]), 2.6)
    ctube = Tube([(0.095, 0.098, 0.037), (0.098, 0.068, 0.037), (0.104, 0.040, 0.036), (0.113, 0.020, 0.033)], csec,
                 ref_fn=lambda P: np.tile(EZ, (len(P), 1)), step=0.002, round_ends=True)

    def calcaneus(x, y, z):
        d = ctube(x, y, z)
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.095, 0.092, 0.036), (0.0140, 0.0120, 0.0200)), 0.006)   # tuber
        d = smin(d, A.sd_ellipsoid(x, y, z, (0.080, 0.046, 0.046), (0.0090, 0.0110, 0.0045)), 0.004)   # sustentac.
        return d

    def navicular(x, y, z):
        d = ell3(x, y, z, (0.086, -0.002, 0.051), (0.0130, 0.0060, 0.0110))
        return smin(d, A.sd_sphere(x, y, z, (0.074, 0.001, 0.045), 0.0050), 0.003)

    def block(c, r, n=3.0, rnd=0.003):
        """Rounded tarsal block (superelliptic plan, flat top and bottom)."""
        return lambda x, y, z: A.extrude(gg_superellipse(x - c[0], y - c[1], r[0], r[1], n), z - c[2], r[2], rnd)

    def mt5_base(x, y, z):
        return A.sd_sphere(x, y, z, (0.141, -0.004, 0.025), 0.0058)
    cuboid = block((0.121, 0.006, 0.032), (0.0105, 0.0125, 0.0105), 2.8)
    cun = block
    order = [("talus", talus, "foot_L"), ("calcaneus", calcaneus, "foot_L"), ("navicular", navicular, "foot_L"),
             ("cuboid", cuboid, "foot_L"), ("cuneiform_med", cun((0.083, -0.018, 0.040), (0.0075, 0.0100, 0.0135)), "foot_L"),
             ("cuneiform_int", cun((0.096, -0.015, 0.045), (0.0058, 0.0080, 0.0100)), "foot_L"),
             ("cuneiform_lat", cun((0.108, -0.013, 0.042), (0.0065, 0.0092, 0.0105)), "foot_L")]
    out = []
    done = []
    for name, f0, rb in order:
        def g(x, y, z, f0=f0, prev=tuple(done)):
            d = f0(x, y, z)
            d = np.maximum(d, -(tib(x, y, z) - 0.0035))
            d = np.maximum(d, -(fib(x, y, z) - 0.0020))
            for q in prev:
                d = np.maximum(d, -(q(x, y, z) - 0.0015))
            return d
        done.append(f0)
        lo, hi = TARSAL_BOX[name]
        out.append((name, g, (np.array(lo), np.array(hi)), rb))
    F = BN.FOOT_BONES
    mtp1, mtp5 = np.array(F["mtp1"]), np.array(F["mtp5"])
    heads = [mtp1, np.array((0.104, -0.084, 0.019)), np.array((0.122, -0.076, 0.018)),
             np.array((0.141, -0.064, 0.018)), mtp5]
    bases = [np.array((0.083, -0.031, 0.040)), np.array((0.096, -0.027, 0.044)), np.array((0.108, -0.024, 0.041)),
             np.array((0.119, -0.010, 0.033)), np.array((0.132, -0.005, 0.029))]
    rads = [(0.0080, 0.0058, 0.0090), (0.0060, 0.0040, 0.0062), (0.0058, 0.0040, 0.0060), (0.0058, 0.0040, 0.0058),
            (0.0065, 0.0042, 0.0058)]
    for k in range(5):
        u = _n(heads[k] - bases[k])
        fn, box = _long_small(bases[k] + u * 0.004, heads[k], *rads[k])
        if k == 4:
            fn0 = fn
            fn = lambda x, y, z, fn0=fn0: smin(fn0(x, y, z), mt5_base(x, y, z), 0.003)
        fn = _clipped(fn, done, 0.0015)
        out.append((f"metatarsal{k + 1}", fn, (box[0] - 0.006, box[1] + 0.006), "foot_L"))
    # toes: tips 5 mm inside the skin's toe block front edge
    tipx = [0.086, 0.106, 0.122, 0.138, 0.153]
    nseg = [2, 3, 3, 3, 3]
    for k in range(5):
        yf = -0.116 - 0.032 * math.sqrt(max(1.0 - ((tipx[k] - 0.119) / 0.044) ** 2, 0.0)) + 0.006
        tip = np.array((tipx[k], yf, 0.012))
        mtp = heads[k]
        u = _n(tip - mtp)
        L = np.linalg.norm(tip - mtp)
        r0 = 0.0060 if k == 0 else 0.0040
        fr = (0.62, 0.38) if nseg[k] == 2 else (0.52, 0.26, 0.22)
        s0 = (rads[k][2] + 0.0015)
        pos = s0
        for j, f_ in enumerate(fr):
            seg_len = (L - s0) * f_
            a = mtp + u * (pos + 0.0012)
            b = mtp + u * (pos + seg_len - 0.0012)
            sc = 1.0 - 0.18 * j
            fn, box = _long_small(a, b, r0 * sc, r0 * 0.65 * sc, r0 * 0.8 * sc)
            out.append((f"toe{k + 1}_{j + 1}", fn, box, "toes_L"))
            pos += seg_len
    return out


# ===========================================================================
# Skull and mandible: the head project's bones (6.5 mm vault with outer/inner tables),
# re-imported read-only at every build and moved into the body frame
# ===========================================================================
def skull_sdf():
    A = _A()
    o = HEAD_OFFSET

    def fn(x, y, z):
        return A.skull_sdf(x - o[0], y - o[1], z - o[2])
    return fn, (np.array(A.SKULL_BOX[0]) + o, np.array(A.SKULL_BOX[1]) + o)


def mandible_sdf():
    A = _A()
    o = HEAD_OFFSET

    def fn(x, y, z):
        return A.jaw_sdf(x - o[0], y - o[1], z - o[2])
    return fn, (np.array(A.JAW_BOX[0]) + o, np.array(A.JAW_BOX[1]) + o)


# ===========================================================================
# Piece table (plan §4.1 budgets) and assembly
# ===========================================================================
LEVELS = [r["level"] for r in ROWS]


def level_bone(z):
    """Rig bone that carries a spine-level piece at height z (the rig's trunk segmentation)."""
    for zz, b in ((1.490, "neck"), (1.353, "upper_chest"), (1.212, "chest"), (1.027, "spine")):
        if z >= zz:
            return b
    return "hips"


def _one(fnbox, rigid, core=None):
    """A single-island piece; a third element of ``fnbox`` is its marrow core."""
    fn, box = fnbox[0], fnbox[1]
    if core is None and len(fnbox) > 2:
        core = fnbox[2]
    return [("main", fn, box, rigid, core)]


def _below(lv):
    """Vertebra ``lv`` clipped 0.8 mm clear of the vertebra above (facets, laminae, spinous)."""
    fn, box = vertebra_sdf(lv)
    i = LEVELS.index(lv)
    if i == 0:
        return fn, box
    up, ubox = vertebra_sdf(LEVELS[i - 1])
    return _clip_near(fn, up, 0.0011, *ubox), box


def _rib_clipped(n):
    """Rib ``n`` with its head kept 1 mm clear of the two vertebrae it articulates with."""
    fn, box = rib_sdf(n)
    head = np.array(RB_.RIB_TABLE[n][1])
    for lv in {f"T{n}", f"T{max(n - 1, 1)}"}:
        vf, _vb = vertebra_sdf(lv)
        fn = _clip_near(fn, vf, 0.0011, head - 0.03, head + 0.03)
    return fn, box


def _sacrum_clipped():
    fn, box = sacrum_sdf()
    l5, b5 = vertebra_sdf("L5")
    return _clip_near(fn, l5, 0.0008, *b5), box


def _elbow_box():
    return ELB_L - 0.045, ELB_L + 0.045


def _wrist_box():
    return WRI_L - 0.045, WRI_L + 0.03


def _ulna_clipped():
    fn, box, core = ulna_sdf()
    return _clip_near(fn, humerus_sdf()[0], 0.0015, *_elbow_box()), box, core


def _radius_clipped():
    fn, box, core = radius_sdf()
    hum, uln = humerus_sdf()[0], ulna_sdf()[0]
    fn = _clip_near(fn, hum, 0.0015, *_elbow_box())
    fn = _clip_near(fn, uln, 0.0012, np.minimum(ELB_L, WRI_L) - 0.03, np.maximum(ELB_L, WRI_L) + 0.03)
    return fn, box, core


def _tibia_clipped():
    fn, box, core = tibia_sdf()
    return _clip_near(fn, femur_sdf()[0], 0.0025, (0.03, -0.03, 0.455), (0.16, 0.08, 0.53)), box, core


def _fibula_clipped():
    fn, box, core = fibula_sdf()
    tib = tibia_sdf()[0]
    fn = _clip_near(fn, tib, 0.0010, (0.09, 0.0, 0.40), (0.16, 0.08, 0.48))
    fn = _clip_near(fn, tib, 0.0010, (0.09, 0.02, 0.03), (0.16, 0.09, 0.16))
    return fn, box, core


def piece_table():
    """[(piece, mirrored, h_hr (m), lod0 triangles, subs())] in BONE_PIECES order.

    ``subs()`` -> [(sub name, sdf, box, rigid bone, marrow-core sdf | None)].  Left pieces
    (``*_L``) are mirrored into their ``*_R`` twins."""
    T = []
    T.append(("skull", False, 0.0013, 9500, lambda: _one(skull_sdf(), "head")))
    T.append(("mandible", False, 0.0008, 1600, lambda: _one(mandible_sdf(), "jaw")))
    lod = {"C1": 300, "C2": 320}
    for lv in LEVELS[:-1]:
        n = lod.get(lv, {"C": 200, "T": 190, "L": 250}[lv[0]])
        T.append((lv.lower(), False, 0.0008 if lv[0] != "L" else 0.0009, n,
                  lambda lv=lv: _one(_below(lv), level_bone(ROW[lv]["z"]))))
    T.append(("sacrum", False, 0.0010, 550, lambda: _one(_sacrum_clipped(), "hips")))
    T.append(("coccyx", False, 0.0007, 60, lambda: _one(coccyx_sdf(), "hips")))
    for a, b in zip(LEVELS[1:-1], LEVELS[2:]):
        T.append((f"disc_{a.lower()}_{b.lower()}", False, 0.0008, 30,
                  lambda a=a, b=b: _one(disc_sdf(a, b), level_bone(0.5 * (ROW[a]["z"] + ROW[b]["z"])))))
    T.append(("sternum", False, 0.0009, 300, lambda: _one(sternum_parts(), "upper_chest")))
    for n in range(1, 13):
        head_z = RB_.RIB_TABLE[n][1][2]
        T.append((f"rib{n}_L", True, 0.0009, {1: 130, 11: 110, 12: 80}.get(n, 150),
                  lambda n=n, hz=head_z: _one(_rib_clipped(n), level_bone(hz))))
    for n in range(1, 11):
        head_z = RB_.RIB_TABLE[n][1][2]
        T.append((f"costal_cartilage{n}_L", True, 0.0009, 45,
                  lambda n=n, hz=head_z: _one(cartilage_sdf(n), level_bone(hz))))
    T.append(("clavicle_L", True, 0.0009, 180,
              lambda: _one(clavicle_sdf(), "clavicle_L", _core(clavicle_sdf()[0], 0.0024,
                                                                  np.array(BN.CLAVICLE_WAYPOINTS[0]) + (0.03, 0, 0),
                                                                  np.array(BN.CLAVICLE_WAYPOINTS[-1]) - (0.03, 0.02, 0),
                                                                  k=0.004))))
    T.append(("scapula_L", True, 0.0008, 450, lambda: _one(scapula_sdf(), "clavicle_L")))
    T.append(("humerus_L", True, 0.0010, 600, lambda: _one(humerus_sdf(), "upper_arm_L")))
    T.append(("radius_L", True, 0.0009, 300, lambda: _one(_radius_clipped(), "forearm_L")))
    T.append(("ulna_L", True, 0.0009, 330, lambda: _one(_ulna_clipped(), "forearm_L")))
    T.append(("hand_L", True, 0.0006, 900, lambda: [(n, f, b, r, None) for n, f, b, r in hand_parts()]))
    T.append(("hip_bone_L", True, 0.0010, 1300, lambda: _one(hip_bone_sdf(), "hips")))
    T.append(("femur_L", True, 0.0011, 850, lambda: _one(femur_sdf(), "thigh_L")))
    T.append(("patella_L", True, 0.0008, 90, lambda: _one(patella_sdf(), "shin_L")))
    T.append(("tibia_L", True, 0.0010, 650, lambda: _one(_tibia_clipped(), "shin_L")))
    T.append(("fibula_L", True, 0.0009, 240, lambda: _one(_fibula_clipped(), "shin_L")))
    T.append(("foot_L", True, 0.0007, 950, lambda: [(n, f, b, r, None) for n, f, b, r in foot_parts()]))
    return T


CORE_TRIS = {"humerus_L": 50, "radius_L": 40, "ulna_L": 40, "femur_L": 60, "tibia_L": 50, "fibula_L": 30,
             "clavicle_L": 30}
HR_FACTOR = 18                    # GB_Skeleton_HR keeps ~18x the LOD0 triangles (bake source)


def _mirror_bone(b):
    return b[:-2] + "_R" if b.endswith("_L") else b


def _right(name):
    return name[:-2] + "_R" if name.endswith("_L") else name


_MESHED = {}                      # piece -> meshed data (reused by the variants, capsules, bones.json)


def mesh_pieces(quick=False, only=None, log=True):
    """Polygonise every piece: {piece: {"subs": [{sub, rigid, hr:(v,f), lod:(v,f)}], "core": {...}|None,
    "cls": int, "slot": int, "fn": sdf, "core_fn": sdf|None}} for left and mirrored right pieces."""
    out = {}
    scale = 1.7 if quick else 1.0
    for piece, mirrored, h, lod, subs_fn in piece_table():
        if only and piece not in only and _right(piece) not in only:
            continue
        t0 = time.perf_counter()
        subs = subs_fn()
        cls = BN.BONE_PIECE_CLASS[piece]
        slot = CARTILAGE_SLOT if cls == 4 else 0
        meshed = []
        for sub, fn, box, rigid, core in subs:
            v, f = mesh_sdf(fn, box, h * scale)
            meshed.append(dict(sub=sub, rigid=rigid, fn=fn, box=box, core_fn=core, hr=(v, f)))
        tot = sum(len(m["hr"][1]) for m in meshed)
        for m in meshed:
            share = len(m["hr"][1]) / max(tot, 1)
            m["lod"] = decimate_arrays(*m["hr"], max(24, int(round(lod * share))))
            m["hr"] = decimate_arrays(*m["hr"], max(200, int(round(HR_FACTOR * lod * share))))
            if m["core_fn"] is not None:
                vc, fc = mesh_sdf(m["core_fn"], m["box"], h * scale)
                m["core_hr"] = decimate_arrays(vc, fc, 30 * CORE_TRIS.get(piece, 40))
                m["core_lod"] = decimate_arrays(vc, fc, CORE_TRIS.get(piece, 40))
        rec = dict(subs=meshed, cls=cls, slot=slot)
        out[piece] = rec
        if mirrored:
            rsubs = []
            for m in meshed:
                r = dict(sub=m["sub"], rigid=_mirror_bone(m["rigid"]), fn=None, box=None, core_fn=None,
                         hr=mirror_arrays(*m["hr"]), lod=mirror_arrays(*m["lod"]))
                if "core_lod" in m:
                    r["core_hr"] = mirror_arrays(*m["core_hr"])
                    r["core_lod"] = mirror_arrays(*m["core_lod"])
                rsubs.append(r)
            out[_right(piece)] = dict(subs=rsubs, cls=cls, slot=slot)
        if log:
            gbc.log(f"  B3 {piece:22s} hr {sum(len(m['hr'][1]) for m in meshed):7d}  lod "
                    f"{sum(len(m['lod'][1]) for m in meshed):5d} tris  {time.perf_counter() - t0:5.1f} s")
    _MESHED.update(out)
    return out


def _parts(meshed, level):
    """join_parts() parts of every piece at ``level`` ('hr' | 'lod'), marrow cores included."""
    import gb_geom as gg
    parts = []
    for piece, rec in meshed.items():
        pid = BN.BONE_PIECE_ID[piece]
        for m in rec["subs"]:
            v, f = m[level]
            rb = RT.BONE_INDEX[m["rigid"]]
            parts.append(gg.part(v, f, rec["slot"], gb_piece=pid, gb_class=rec["cls"], gb_rigid_bone=rb))
            ck = "core_" + level
            if ck in m:
                vc, fc = m[ck]
                parts.append(gg.part(vc, fc, 0, gb_piece=pid, gb_class=MARROW_CLASS, gb_rigid_bone=rb))
    return parts


def _finish(obj, atlas=True):
    """Codes UV (piece, class), atlas UV, UV order, smooth shading, glTF extras."""
    import gb_geom as gg
    import placeholder as PH
    u = gbc.read_point_attr(obj, "gb_piece", 'INT')
    v = gbc.read_point_attr(obj, "gb_class", 'INT')
    gbc.set_codes_uv(obj, u, v)
    if atlas:
        gg.smart_uv(obj, margin=0.004)
    PH.finish_uvs(obj)
    obj.data.shade_smooth()
    obj["gb_layer"] = gbc.LAYER_OF.get(obj.name, "bone")
    obj["gb_schema"] = 1
    obj["gb_status"] = "B3"


def build_skeleton():
    """GB_Skeleton (LOD0, exported) + GB_Skeleton_HR (bake source): every bone piece, codes in UV2,
    rigid bone per vertex, long bones as double shells.  Also writes ``bones.json``."""
    import gb_geom as gg
    quick = _quick()
    with gbc.Timer("B3 skeleton: mesh pieces"):
        meshed = mesh_pieces(quick)
    with gbc.Timer("B3 skeleton: objects"):
        skel = gg.object_from_parts("GB_Skeleton", _parts(meshed, "lod"))
        _finish(skel)
        hr = gg.object_from_parts("GB_Skeleton_HR", _parts(meshed, "hr"), slots=gbc.MATERIAL_SLOTS["GB_Skeleton"])
        _finish(hr, atlas=False)
    with gbc.Timer("B3 skeleton: bones.json"):
        write_bones_json(meshed)
    return {"GB_Skeleton": skel, "GB_Skeleton_HR": hr}


# ===========================================================================
# Broad-phase hit capsules and bones.json (pieces, capsules, exact-hit mesh, variants)
# ===========================================================================
CAPSULES_PER_PIECE = {"skull": 3, "mandible": 2, "sternum": 2, "scapula": 2, "humerus": 2, "radius": 2,
                      "ulna": 2, "hand": 2, "hip_bone": 3, "femur": 2, "tibia": 2, "foot": 2, "clavicle": 2}


def _fit_capsules(V, k):
    """k bounding capsules along the principal axis of point set V: [(a, b, r)]."""
    V = np.asarray(V, float)
    c = V.mean(0)
    _u, _s, vt = np.linalg.svd(V - c, full_matrices=False)
    t = (V - c) @ vt[0]
    qs = np.quantile(t, np.linspace(0.0, 1.0, k + 1))
    out = []
    for i in range(k):
        lo, hi = qs[i], qs[i + 1]
        pad = 0.08 * (hi - lo)
        sel = V[(t >= lo - pad) & (t <= hi + pad)]
        if len(sel) < 4:
            continue
        cc = sel.mean(0)
        _u, _s, w = np.linalg.svd(sel - cc, full_matrices=False)
        tt = (sel - cc) @ w[0]
        perp = np.linalg.norm((sel - cc) - np.outer(tt, w[0]), axis=1)
        r0 = float(np.percentile(perp, 90))
        a = cc + w[0] * max(tt.min() + r0, tt.min() * 0.5 if tt.min() < 0 else 0)
        b = cc + w[0] * min(tt.max() - r0, tt.max() * 0.5 if tt.max() > 0 else 0)
        # exact bounding radius to the segment
        ab = b - a
        L2 = max(float(ab @ ab), 1e-12)
        h = np.clip(((sel - a) @ ab) / L2, 0, 1)
        r = float(np.linalg.norm(sel - (a + np.outer(h, ab)), axis=1).max())
        out.append((a, b, r))
    return out


def _piece_vertices():
    """{piece name: vertices} from the meshed pieces or, if the stage came from the cache, GB_Skeleton."""
    if _MESHED:
        return {p: np.vstack([m["lod"][0] for m in rec["subs"]]) for p, rec in _MESHED.items()}
    import bpy
    o = bpy.data.objects.get("GB_Skeleton")
    if o is None:
        return {}
    v = gbc.get_verts(o.data)
    pc = gbc.read_point_attr(o, "gb_piece", 'INT')
    cl = gbc.read_point_attr(o, "gb_class", 'INT')
    inv = {i: n for n, i in BN.BONE_PIECE_ID.items()}
    return {inv[i]: v[(pc == i) & (cl != MARROW_CLASS)] for i in np.unique(pc)}


def bone_capsules():
    """Broad-phase hit capsules (body frame): [{"piece", "bone", "a", "b", "r"}].

    One per vertebra and cartilage, two per rib, 2-3 for large or bent bones (skull, hip bone,
    long bones split into proximal/distal halves); discs are covered by the exact-hit mesh."""
    verts = _piece_vertices()
    bones = _piece_rigid_bones()
    out = []
    for piece, _cls in BN.BONE_PIECES:
        if piece not in verts or piece.startswith("disc_") or len(verts[piece]) < 8:
            continue
        base = piece[:-2] if piece.endswith(("_L", "_R")) else piece
        base = "rib" if base.startswith("rib") else base
        k = 2 if base == "rib" else CAPSULES_PER_PIECE.get(base, 1)
        for a, b, r in _fit_capsules(verts[piece], k):
            out.append({"piece": piece, "piece_id": BN.BONE_PIECE_ID[piece], "bone": bones.get(piece, ""),
                        "a": a, "b": b, "r": r})
    return out


def _piece_rigid_bones():
    """{piece: main rig bone} (hands/feet: hand / foot; fingers, thumb and toes per vertex)."""
    fixed = {"skull": "head", "mandible": "jaw", "sacrum": "hips", "coccyx": "hips", "sternum": "upper_chest"}
    for lv in LEVELS[:-1]:
        fixed[lv.lower()] = level_bone(ROW[lv]["z"])
    for side in "LR":
        fixed.update({f"clavicle_{side}": f"clavicle_{side}", f"scapula_{side}": f"clavicle_{side}",
                      f"humerus_{side}": f"upper_arm_{side}", f"radius_{side}": f"forearm_{side}",
                      f"ulna_{side}": f"forearm_{side}", f"hand_{side}": f"hand_{side}",
                      f"hip_bone_{side}": "hips", f"femur_{side}": f"thigh_{side}", f"patella_{side}": f"shin_{side}",
                      f"tibia_{side}": f"shin_{side}", f"fibula_{side}": f"shin_{side}", f"foot_{side}": f"foot_{side}"})
        for n in range(1, 13):
            fixed[f"rib{n}_{side}"] = level_bone(RB_.RIB_TABLE[n][1][2])
        for n in range(1, 11):
            fixed[f"costal_cartilage{n}_{side}"] = level_bone(RB_.RIB_TABLE[n][1][2])
    for a, b in zip(LEVELS[1:-1], LEVELS[2:]):
        fixed[f"disc_{a.lower()}_{b.lower()}"] = level_bone(0.5 * (ROW[a]["z"] + ROW[b]["z"]))
    return fixed


LONG_BONE_KEY = {"femur": "femur", "tibia": "tibia", "fibula": "fibula", "humerus": "humerus", "radius": "radius",
                 "ulna": "ulna", "clavicle": "clavicle"}
INTERIOR = {0: BN.BONE_COLOURS["yellow_marrow"], 1: BN.BONE_COLOURS["red_marrow"], 2: BN.BONE_COLOURS["red_marrow"],
            3: BN.BONE_COLOURS["diploe"], 4: BN.BONE_COLOURS["costal_cartilage"], 5: "#E6DDC8",
            6: BN.BONE_COLOURS["yellow_marrow"]}
HIT_MESH_TRIS = 20000
gbc.SCHEMAS.setdefault("gb.bones/1", ("pieces", "capsules", "hit_mesh", "classes", "variants"))
BONES_JSON = os.path.join(gbc.SUBJECT_OUT, "bones.json")


def piece_lengths(verts=None):
    """Maximum length (cm) of each long bone along its principal axis (osteometric board)."""
    verts = verts or _piece_vertices()
    out = {}
    for piece, V in verts.items():
        base = piece[:-2] if piece.endswith(("_L", "_R")) else piece
        if base in LONG_BONE_KEY and len(V):
            c = V.mean(0)
            _u, _s, vt = np.linalg.svd(V[::3] - c, full_matrices=False)
            t = (V - c) @ vt[0]
            out[piece] = float(100.0 * (t.max() - t.min()))
    return out


def bone_table(meshed=None, variants=None):
    """``bones.json`` data: pieces (id, class, rigid bone, bounds, length, cortex, interior colour),
    capsules, exact-hit mesh (<= 20k triangles, per-triangle piece id), classes, variants."""
    meshed = meshed or _MESHED
    verts = _piece_vertices()
    rig = _piece_rigid_bones()
    lengths = piece_lengths(verts)
    pieces = []
    for piece, cls in BN.BONE_PIECES:
        if piece not in verts:
            continue
        V = verts[piece]
        base = piece[:-2] if piece.endswith(("_L", "_R")) else piece
        row = {"id": BN.BONE_PIECE_ID[piece], "name": piece, "class": cls, "class_name": BN.BONE_CLASS[cls],
               "bone": rig.get(piece), "bounds": [V.min(0), V.max(0)], "interior_colour": INTERIOR[cls]}
        if base in BN.LONG_BONES:
            row["length_cm"] = lengths.get(piece)
            row["length_bible_cm"] = BN.LONG_BONES[base]["length_cm"]
            row["cortex_mm"] = BN.LONG_BONES[base]["cortex_mm"]
            row["marrow_core"] = True
        pieces.append(row)
    # exact-hit mesh: the LOD0 surfaces (no marrow cores) decimated to <= 20k triangles
    hv, ht, hp = [], [], []
    off = 0
    total = sum(len(m["lod"][1]) for rec in meshed.values() for m in rec["subs"]) if meshed else 0
    ratio = min(1.0, HIT_MESH_TRIS / max(total, 1)) * 0.97
    for piece, rec in meshed.items():
        for m in rec["subs"]:
            v, f = m["lod"]
            if ratio < 1.0:
                v, f = decimate_arrays(v, f, max(12, int(len(f) * ratio)))
            hv.append(v)
            ht.append(f + off)
            hp.append(np.full(len(f), BN.BONE_PIECE_ID[piece]))
            off += len(v)
    hit = {"verts": np.vstack(hv).ravel() if hv else [], "tris": np.vstack(ht).ravel().astype(int) if ht else [],
           "tri_piece": np.concatenate(hp).astype(int) if hp else [],
           "note": "rest pose, body frame; build a ConcavePolygonShape3D per piece or one static body"}
    return {"pieces": pieces, "capsules": bone_capsules(), "hit_mesh": hit,
            "classes": {str(k): v for k, v in BN.BONE_CLASS.items()},
            "interior_colours": {str(k): v for k, v in INTERIOR.items()},
            "colours": BN.BONE_COLOURS, "material": BN.BONE_MATERIAL, "variants": variants or {}}


def write_bones_json(meshed=None, variants=None):
    """Write ``bones.json`` (schema gb.bones/1) next to the other sidecars."""
    if variants is None and os.path.exists(BONES_JSON):
        try:
            variants = gbc.read_json(BONES_JSON)["data"].get("variants", {})
        except Exception:
            variants = {}
    return gbc.write_json(BONES_JSON, bone_table(meshed, variants), "gb.bones/1")


# ===========================================================================
# Fracture variants [plan §3.3.5, RB §2.2.3]: closed fragments with real fracture faces.
# Fragment i = bone ∩ (warped Voronoi cell i shrunk by half the crack gap).  The cells are
# evaluated on domain-warped coordinates (fbm, 2-3 mm) so the fracture lines are jagged;
# long-bone fragments are the hollow cortex (outer minus the marrow core) plus the matching
# piece of the marrow core, so every broken end shows the cortex ring around the marrow.
# ===========================================================================
CRACK_GAP = 0.0004                 # visible hairline between assembled fragments
VARIANT_BUDGET = {"skull": 8000, "Humerus": 2000, "RadUlna": 2200, "Femur": 2400, "Tibia": 2200}


class Cells:
    """Warped Voronoi cells with optional additive weights (a power-diagram-like butterfly)."""

    def __init__(self, seeds, warp=0.0025, freq=55.0, seed=0, weights=None):
        self.S = np.asarray(seeds, float)
        self.w = np.zeros(len(self.S)) if weights is None else np.asarray(weights, float)
        self.warp, self.freq, self.seed = warp, freq, seed
        D = np.linalg.norm(self.S[:, None] - self.S[None], axis=2)
        self.nbrs = [list(np.argsort(D[i])[1:min(len(self.S), 17)]) for i in range(len(self.S))]

    def _warp(self, x, y, z):
        if self.warp <= 0:
            return x, y, z
        f, s = self.freq, self.seed
        return (x + self.warp * fbm(x, y, z, f, 2, s), y + self.warp * fbm(x, y, z, f, 2, s + 7),
                z + self.warp * fbm(x, y, z, f, 2, s + 13))

    def cell(self, i, x, y, z):
        """Signed distance-like value of cell i (negative inside), exact bisector distance."""
        x, y, z = self._warp(x, y, z)
        S = self.S
        si = S[i]
        di = (x - si[0]) ** 2 + (y - si[1]) ** 2 + (z - si[2]) ** 2 - self.w[i]
        out = np.full(x.shape, -1.0)
        for j in self.nbrs[i]:
            sj = S[j]
            L = np.linalg.norm(sj - si)
            dj = (x - sj[0]) ** 2 + (y - sj[1]) ** 2 + (z - sj[2]) ** 2 - self.w[j]
            out = np.maximum(out, (di - dj) / (2.0 * L))
        return out

    def owner(self, P):
        x, y, z = self._warp(P[:, 0], P[:, 1], P[:, 2])
        d = np.stack([(x - s[0]) ** 2 + (y - s[1]) ** 2 + (z - s[2]) ** 2 - w for s, w in zip(self.S, self.w)], 1)
        return np.argmin(d, axis=1)


def _fragment_meshes(solid, cells, surf_pts, box, h, extra=None):
    """Mesh every non-empty cell of ``solid`` (and of ``extra`` = marrow core, if given):
    [(frag index, (v, f), (vc, fc) | None)].  ``surf_pts`` (points on the solid) find the cells
    that own material and their bounding boxes."""
    own = cells.owner(surf_pts)
    out = []
    lo_all, hi_all = np.asarray(box[0]), np.asarray(box[1])
    for i in np.unique(own):
        P = surf_pts[own == i]
        lo = np.maximum(P.min(0) - 0.012, lo_all)
        hi = np.minimum(P.max(0) + 0.012, hi_all)

        def fn(x, y, z, i=i):
            return np.maximum(solid(x, y, z), cells.cell(i, x, y, z) + 0.5 * CRACK_GAP)
        v, f = mesh_sdf(fn, (lo, hi), h)
        if len(f) == 0:
            continue
        core = None
        if extra is not None:
            def cfn(x, y, z, i=i):
                return np.maximum(extra(x, y, z), cells.cell(i, x, y, z) + 0.5 * CRACK_GAP)
            vc, fc = mesh_sdf(cfn, (lo, hi), h)
            core = (vc, fc) if len(fc) else None
        out.append((int(i), (v, f), core))
    return out


def _skull_seeds(direction, rng, n_cap=70, n_plates=6, cap_deg=54.0):
    """Seeds on the vault (head frame): ``n_cap`` in a cap around the exit ``direction`` (small
    fragments, median ~20 mm) and ``n_plates`` over the rest of the vault (big plates 40-100 mm)."""
    d = _n(direction)
    c = np.array((0.0, 0.0, 0.035))
    r = np.array((0.074, 0.098, 0.099))
    cos_cap = math.cos(math.radians(cap_deg))
    cap, plates = [], []
    while len(cap) < n_cap or len(plates) < n_plates:
        u = rng.normal(size=3)
        u /= np.linalg.norm(u)
        if u[2] < -0.25:
            continue
        p = c + u * r * 0.95
        if u @ d >= cos_cap:
            if len(cap) < n_cap:
                cap.append(p)
        elif len(plates) < n_plates and all(np.linalg.norm(p - q) > 0.06 for q in plates):
            plates.append(p)
    return np.array(cap + plates)


def skull_variants(meshed):
    """GB_Frac_Skull_L/R/T: vault bursts toward the left, right and top exit (20-80 fragments,
    smaller near the exit); the face and skull base stay one large fragment."""
    A = _A()
    rng = gbc.rng("fracture_skull")
    fn, box = skull_sdf()
    hq = 0.0022 if _quick() else 0.0015
    surf = meshed["skull"]["subs"][0]["hr"][0] - HEAD_OFFSET
    out = {}
    for name, dvec in (("GB_Frac_Skull_L", (1.0, 0.0, 0.25)), ("GB_Frac_Skull_R", (-1.0, 0.0, 0.25)),
                       ("GB_Frac_Skull_T", (0.0, 0.05, 1.0))):
        seeds = _skull_seeds(dvec, rng)
        # base/face seed: a heavily weighted cell under the vault
        seeds = np.vstack([seeds, [(0.0, -0.030, -0.060)]])
        wts = np.zeros(len(seeds))
        wts[-1] = 0.0105 ** 2 * 60
        cells = Cells(seeds + 0.0, warp=0.0030, freq=45.0, seed=int(rng.integers(1, 1 << 20)), weights=wts)

        def solid(x, y, z):
            return A.skull_sdf(x, y, z)
        frags = _fragment_meshes(solid, cells, surf, (np.array(A.SKULL_BOX[0]), np.array(A.SKULL_BOX[1])), hq)
        out[name] = [(i, (v + HEAD_OFFSET, f), None) for i, (v, f), _c in frags]
    return out


def _break_plane_fn(p0, n, amp, freq, seed):
    """Jagged break surface: signed distance to a plane perturbed by fbm (serrated edges)."""
    n = _n(n)

    def fn(x, y, z):
        return plane(x, y, z, p0, n) + amp * fbm(x, y, z, freq, 3, seed)
    return fn


def long_variants(meshed):
    """GB_Frac_{Humerus,RadUlna,Femur,Tibia}_{L,R}_{simple,comminuted}: ``simple`` = one oblique,
    serrated break through the mid-shaft (2 fragments); ``comminuted`` = butterfly wedge plus
    small fragments in a 6-8 cm zone between the two main ends (8-20 fragments)."""
    rng = gbc.rng("fracture_long")
    src = {"Humerus": [("humerus_L", humerus_sdf)], "RadUlna": [("radius_L", radius_sdf), ("ulna_L", ulna_sdf)],
           "Femur": [("femur_L", femur_sdf)], "Tibia": [("tibia_L", tibia_sdf)]}
    hq = 0.0020 if _quick() else 0.0013
    out = {}
    for key, bones in src.items():
        for kind in ("simple", "comminuted"):
            frags = []
            for piece, sdf in bones:
                outer, box, core = sdf()
                shell = (lambda o, c: (lambda x, y, z: smax(o(x, y, z), -(c(x, y, z) - 0.0003), 0.0006)))(outer, core)
                V = meshed[piece]["subs"][0]["hr"][0]
                c0 = V.mean(0)
                _u, _s, vt = np.linalg.svd(V[::5] - c0, full_matrices=False)
                ax = vt[0]
                t = (V - c0) @ ax
                mid = c0 + ax * (0.5 * (t.min() + t.max()) + rng.uniform(-0.03, 0.03) * (t.max() - t.min()))
                side = _n(np.cross(ax, rng.normal(size=3)))
                if kind == "simple":
                    ang = math.radians(rng.uniform(20, 40))
                    nrm = _n(math.cos(ang) * ax + math.sin(ang) * side)
                    seeds = np.array([mid + nrm * 0.05, mid - nrm * 0.05])
                    cells = Cells(seeds, warp=0.0040, freq=60.0, seed=int(rng.integers(1, 1 << 20)))
                else:
                    zone = 0.035 if piece.startswith(("radius", "ulna")) else 0.045
                    n_small = int(rng.integers(8, 14)) if not piece.startswith(("radius", "ulna")) else int(rng.integers(12, 15))
                    r = np.linalg.norm((V - c0) - np.outer(t, ax), axis=1)
                    rad = float(np.median(r[np.abs(t - (mid - c0) @ ax) < 0.02])) if np.any(
                        np.abs(t - (mid - c0) @ ax) < 0.02) else 0.012
                    pts = [mid + ax * 0.25, mid - ax * 0.25]                      # the two main ends
                    wts = [0.0, 0.0]
                    pts.append(mid + side * rad * 0.9)                               # butterfly wedge
                    wts.append((0.6 * zone) ** 2)
                    for _k in range(n_small):
                        a = rng.uniform(0, 2 * math.pi)
                        s2 = np.cross(ax, side)
                        pts.append(mid + ax * rng.uniform(-0.8, 0.8) * zone + rad * (math.cos(a) * side +
                                                                                   math.sin(a) * s2) * rng.uniform(0.7, 1.1))
                        wts.append(0.0)
                    # push the main-end seeds so the comminuted zone is ~2*zone long
                    pts[0] = mid + ax * (zone + 0.20)
                    pts[1] = mid - ax * (zone + 0.20)
                    wts[0] = wts[1] = (0.20 ** 2)
                    cells = Cells(np.array(pts), warp=0.0032, freq=70.0, seed=int(rng.integers(1, 1 << 20)),
                                  weights=np.array(wts) * 0.98)
                fr = _fragment_meshes(shell, cells, V, box, hq, extra=lambda x, y, z, c=core: c(x, y, z) + 0.0003)
                frags.append((piece, fr))
            for side_ in ("L", "R"):
                name = f"GB_Frac_{key}_{side_}_{kind}"
                rows = []
                for piece, fr in frags:
                    for i, vf, core in fr:
                        if side_ == "R":
                            vf = mirror_arrays(*vf)
                            core = mirror_arrays(*core) if core is not None else None
                        rows.append((piece if side_ == "L" else _right(piece), i, vf, core))
                out[name] = rows
    return out


def _variant_object(name, rows, cls_of, rigid_of, budget):
    """Decimate fragments (budget share by size, >= 16 tris) and join them into ``name``."""
    import gb_geom as gg
    tot = sum(len(vf[1]) for _p, _i, vf, _c in rows)
    parts = []
    info = []
    for k, (piece, i, (v, f), core) in enumerate(rows):
        share = len(f) / max(tot, 1)
        v2, f2 = _closed_decimate(v, f, max(16, int(budget * 0.93 * share)))
        pid = BN.BONE_PIECE_ID[piece]
        rb = RT.BONE_INDEX[rigid_of[piece]]
        parts.append(gg.part(v2, f2, 0, gb_piece=pid, gb_class=cls_of[piece], gb_rigid_bone=rb, gb_frag=k))
        if core is not None:
            vc, fc = _closed_decimate(*core, max(12, int(budget * 0.07 * share)))
            parts.append(gg.part(vc, fc, 0, gb_piece=pid, gb_class=MARROW_CLASS, gb_rigid_bone=rb, gb_frag=k))
        ext = v.max(0) - v.min(0)
        vol = _mesh_volume(v, f)
        info.append({"frag": k, "piece": piece, "centroid": v.mean(0), "extent_mm": 1000 * ext,
                     "max_dim_mm": float(1000 * ext.max()), "volume_cm3": vol * 1e6,
                     "debris": bool(1000 * ext.max() >= 20.0)})
    obj = gg.object_from_parts(name, parts)
    _finish(obj)
    return obj, info


def _closed_decimate(v, f, target):
    """Decimate but never return a fragment with open / non-manifold edges (fall back to more
    triangles, finally the undecimated fragment)."""
    for mult in (1.0, 1.6, 2.5):
        v2, f2 = decimate_arrays(v, f, int(target * mult))
        if len(f2):
            v2, f2 = drop_crumbs(v2, f2, min_verts=8)       # lone slivers left by the collapse
        if len(f2) and nonmanifold_edges(f2) == 0:
            return v2, f2
    if nonmanifold_edges(f):
        v, f = _remesh(v, f, 0.0010)                     # last resort: manifold voxel shell
    return v, f


def _mesh_volume(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(abs(np.einsum("ij,ij->i", a, np.cross(b, c)).sum()) / 6.0)


def build_fracture_variants():
    """GB_Frac_*: skull bursts L/R/T and long-bone simple/comminuted variants per side (closed
    fragments, loose islands, piece id + class in UV2, ``gb_frag`` fragment index).  The fragment
    table (centroid, size, volume, debris flag >= 20 mm) is added to ``bones.json``."""
    meshed = _MESHED or mesh_pieces(_quick(), only={"skull", "humerus_L", "radius_L", "ulna_L", "femur_L",
                                                     "tibia_L"}, log=False)
    rigid = _piece_rigid_bones()
    cls = {p: c for p, c in BN.BONE_PIECES}
    out, table = {}, {}
    with gbc.Timer("B3 variants: skull bursts"):
        sk = skull_variants(meshed)
    with gbc.Timer("B3 variants: long bones"):
        lb = long_variants(meshed)
    with gbc.Timer("B3 variants: objects"):
        for name, rows in sk.items():
            obj, info = _variant_object(name, [("skull", i, vf, c) for i, vf, c in rows], cls, rigid,
                                        VARIANT_BUDGET["skull"])
            out[name], table[name] = obj, info
        for name, rows in lb.items():
            key = name.split("_")[2]
            obj, info = _variant_object(name, rows, cls, rigid, VARIANT_BUDGET[key])
            out[name], table[name] = obj, info
    summary = {}
    for name, info in table.items():
        dims = sorted(r["max_dim_mm"] for r in info)
        summary[name] = {"fragments": len(info), "median_max_dim_mm": float(np.median(dims)),
                         "debris_fragments": int(sum(r["debris"] for r in info)),
                         "triangles": gbc.tri_count(out[name].data), "table": info}
    write_bones_json(variants=summary)
    return out
