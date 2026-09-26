"""Body skin, shorts, muscle shell, per-vertex codes and body UVs (owner B1).  Plan §1.2, §5.2, §5.5, §8.2 B1.

Final entry points
------------------
``body_sdf(x, y, z)``          body skin SDF (no head), body frame, negative inside
``skin_sdf(x, y, z)``          gore_head head (neck column clipped under the jaw) united with the body
``muscle_sdf(x, y, z)``        muscle shell SDF: body skin offset inward by skin + fat [RB §7.6]
``shorts_sdf(x, y, z)``        loose mid-thigh shorts (outer cloth surface)
``tissue_at(points)``          per point skin / fat / muscle thickness (mm) [RB §7.6]
``tension_at(points)``         per point unit tangent of the Langer / RSTL line [RB §2.3.1]
``build_body_skin()``          -> {"GB_Body", "GB_Body_HR", "GB_Body_LOD1"}
``build_shorts(skin)``         -> {"GB_Shorts"}
``build_muscle_shell(skin)``   -> {"GB_MuscleShell"}
``paint_codes(obj)``           gb_seg / gb_region / gb_derm + UV2 ``gb_codes`` (plan §5.5)

How the body is modelled
------------------------
The skin is one signed-distance field, polygonised by the head project's
surface-nets mesher.  The big masses are *generalised cylinders*
(``StarTube``): a straight axis through the bible's joint centres [RB §7.2]
and, for every station along it, a polar cross-section ``R(s, theta)`` built
from a four-radius superellipse (lateral / anterior / medial / posterior skin
distances taken from the landmark and girth tables [RB §7.1]) plus smooth
muscle reliefs (pectoralis with its lower border, rectus and linea alba,
obliques over the iliac crest, latissimus, scapulae, erector columns and the
spinal furrow; biceps, triceps, brachioradialis; the quadriceps with the
vastus medialis teardrop, sartorius furrow, adductors, hamstrings, both
gastrocnemius heads, Achilles tendon ...).  Shoulders, clavicles, trapezius,
sternocleidomastoid, larynx, axillary folds, buttocks, simplified hands (plan
D4: fused fingers in a relaxed curl) and feet (toes merged, arch, heel pad,
malleoli) are smooth-unioned primitives.  The left side is authored; every
component takes ``|x|``.

All numbers are metres in the body frame (Z up, face -Y, character's left +X,
origin on the floor between the feet).

Run alone: ``python3 body_skin.py [--quick] [--render]`` builds the stage into
an empty scene (placeholder rig for the codes) and renders
``renders/body_skin_*.png``.
"""
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import landmarks as LM  # noqa: E402

HEAD_OFFSET = gbc.HEAD_OFFSET
SEAM_Z = gbc.SEAM_Z
PI = math.pi


def _A():
    """The head project's anatomy module (read-only import, re-imported on every build)."""
    return gbc.import_head().anatomy


# ===========================================================================
# SDF helpers (arrays of points; k may be an array)
# ===========================================================================
def smin(a, b, k):
    """Cubic smooth union with blend radius ``k`` (scalar or per-point array)."""
    k = np.maximum(k, 1e-9)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * h * k * (1.0 / 6.0)


def smax(a, b, k):
    """Cubic smooth intersection (``smax(a, -b, k)`` subtracts b)."""
    return -smin(-a, -b, k)


def sstep(e0, e1, x):
    """Hermite step from 0 at e0 to 1 at e1 (e0 > e1 gives a falling step)."""
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def gauss(x, s):
    """exp(-(x/s)^2)."""
    return np.exp(-(x / s) ** 2)


def wrap(a):
    """Angle wrapped to (-pi, pi]."""
    return (a + PI) % (2.0 * PI) - PI


def unit(v):
    v = np.asarray(v, dtype=float)
    return v / np.linalg.norm(v)


def band(x, lo, hi, soft):
    """1 inside [lo, hi] with ``soft``-wide smooth shoulders."""
    return sstep(lo - soft, lo + soft, x) * sstep(hi + soft, hi - soft, x)


def quad_radius(th, r_lat, r_ant, r_med, r_post, n):
    """Polar radius of a superellipse with a different radius in each half-axis.

    theta 0 = lateral (+U), 90 deg = anterior (+V), 180 = medial, -90 = posterior."""
    c = np.cos(th)
    s = np.sin(th)
    rx = np.where(c >= 0.0, r_lat, r_med)
    ry = np.where(s >= 0.0, r_ant, r_post)
    return 1.0 / ((np.abs(c) / rx) ** n + (np.abs(s) / ry) ** n) ** (1.0 / n)


def sd_capsule(x, y, z, a, b, ra, rb=None):
    """Capsule a->b with a linearly tapering radius."""
    rb = ra if rb is None else rb
    a = np.asarray(a, float)
    ba = np.asarray(b, float) - a
    dx, dy, dz = x - a[0], y - a[1], z - a[2]
    h = np.clip((dx * ba[0] + dy * ba[1] + dz * ba[2]) / float(ba @ ba), 0.0, 1.0)
    ex, ey, ez = dx - ba[0] * h, dy - ba[1] * h, dz - ba[2] * h
    return np.sqrt(ex * ex + ey * ey + ez * ez) - (ra + (rb - ra) * h)


def sd_polyline(x, y, z, pts, radii, k=0.0):
    """Tube along a polyline (radius per vertex), optionally smooth-unioned per segment."""
    d = None
    for i in range(len(pts) - 1):
        di = sd_capsule(x, y, z, pts[i], pts[i + 1], radii[i], radii[i + 1])
        d = di if d is None else (smin(d, di, k) if k > 0 else np.minimum(d, di))
    return d


def sd_oellipsoid(x, y, z, c, r, axes, n=2.0):
    """Oriented (super)ellipsoid: centre c, semi-axes r along the rows of ``axes`` (3x3), exponent n."""
    dx, dy, dz = x - c[0], y - c[1], z - c[2]
    u = (dx * axes[0][0] + dy * axes[0][1] + dz * axes[0][2]) / r[0]
    v = (dx * axes[1][0] + dy * axes[1][1] + dz * axes[1][2]) / r[1]
    w = (dx * axes[2][0] + dy * axes[2][1] + dz * axes[2][2]) / r[2]
    if n == 2.0:
        k0 = np.sqrt(u * u + v * v + w * w)
        k1 = np.sqrt((u / r[0]) ** 2 + (v / r[1]) ** 2 + (w / r[2]) ** 2) + 1e-12
        return k0 * (k0 - 1.0) / k1
    q = (np.abs(u) ** n + np.abs(v) ** n + np.abs(w) ** n) ** (1.0 / n)
    return (q - 1.0) * min(r)


def frame(a_axis, b_hint):
    """Orthonormal rows (a, b', a x b') with b' = b_hint made orthogonal to a."""
    a = unit(a_axis)
    b = np.asarray(b_hint, float)
    b = unit(b - (b @ a) * a)
    return np.array([a, b, np.cross(a, b)])


class Box:
    """Axis-aligned box used to skip far points.

    ``lo``/``hi`` must enclose the component; outside the box expanded by
    ``margin`` the component is not evaluated and ``distance to the expanded
    box + margin`` is returned, a lower bound of the true distance that is
    never below ``margin`` (so smooth unions with k < margin see no seam)."""

    def __init__(self, lo, hi, margin=0.03):
        self.margin = margin
        self.lo = np.asarray(lo, float) - margin
        self.hi = np.asarray(hi, float) + margin

    def run(self, fn, x, y, z):
        """fn(x, y, z) inside the box; outside, the distance to the box (a lower bound)."""
        return self.run_multi(lambda a, b, c: (fn(a, b, c),), x, y, z)[0]

    def run_multi(self, fn, x, y, z):
        """Like ``run`` for a function returning a tuple of SDF arrays."""
        m = ((x >= self.lo[0]) & (x <= self.hi[0]) & (y >= self.lo[1]) & (y <= self.hi[1])
             & (z >= self.lo[2]) & (z <= self.hi[2]))
        dx = np.maximum(np.maximum(self.lo[0] - x, x - self.hi[0]), 0.0)
        dy = np.maximum(np.maximum(self.lo[1] - y, y - self.hi[1]), 0.0)
        dz = np.maximum(np.maximum(self.lo[2] - z, z - self.hi[2]), 0.0)
        far = np.sqrt(dx * dx + dy * dy + dz * dz) + self.margin
        if not m.any():
            return [far] * 64
        idx = np.nonzero(m)[0]
        res = fn(x[idx], y[idx], z[idx])
        outs = []
        for r in res:
            o = far.copy()
            o[idx] = r
            outs.append(o)
        return outs


class StarTube:
    """Generalised cylinder: straight axis, per-station centre offset, polar radius table R(s, theta).

    ``s`` is the distance (m) from ``origin`` along ``axis``; ``lateral`` and
    ``anterior`` are hints for the section axes U (theta = 0) and V (theta = 90 deg).
    ``profile(S, TH) -> R`` and ``offset(S) -> (cu, cv)`` are evaluated once on
    a table (``ds`` spacing, ``nth`` angles); queries interpolate bilinearly.
    The returned distance is normalised by the analytic gradient of the table,
    so it stays close to a true distance even on steep flanks.  Ends are capped
    with smooth planes (``cap0`` / ``cap1`` = s of the cap planes, or None)."""

    def __init__(self, origin, axis, lateral, anterior, s0, s1, profile, offset=None, ds=0.002, nth=180,
                 cap0=None, cap1=None, cap_k=0.01):
        self.o = np.asarray(origin, float)
        self.w = unit(axis)
        U = np.asarray(lateral, float)
        U = unit(U - (U @ self.w) * self.w)
        V = np.asarray(anterior, float)
        V = V - (V @ self.w) * self.w - (V @ U) * U
        self.U, self.V = U, unit(V)
        self.s0, self.s1, self.ds, self.nth = s0, s1, ds, nth
        self.S = np.arange(s0, s1 + 0.5 * ds, ds)
        self.TH = -PI + 2.0 * PI * np.arange(nth) / nth
        R = np.asarray(profile(self.S[:, None], self.TH[None, :]), float)
        R = np.broadcast_to(R, (len(self.S), nth)).copy()
        self.R = np.maximum(R, 1e-4)
        self.Rs = np.gradient(self.R, ds, axis=0)
        dth = 2.0 * PI / nth
        self.Rt = (np.roll(self.R, -1, axis=1) - np.roll(self.R, 1, axis=1)) / (2.0 * dth)
        if offset is None:
            self.CU = np.zeros(len(self.S))
            self.CV = np.zeros(len(self.S))
        else:
            cu, cv = offset(self.S)
            self.CU = np.broadcast_to(np.asarray(cu, float), self.S.shape).copy()
            self.CV = np.broadcast_to(np.asarray(cv, float), self.S.shape).copy()
        self.cap0, self.cap1, self.cap_k = cap0, cap1, cap_k
        # conservative bounding box
        rmax = float(self.R.max()) + float(np.abs(self.CU).max()) + float(np.abs(self.CV).max())
        ends = np.array([self.o + s0 * self.w, self.o + s1 * self.w])
        self.box = Box(ends.min(0) - rmax, ends.max(0) + rmax, margin=0.03)

    def local(self, x, y, z):
        """(s, u, v) of points in the tube frame (u, v relative to the station centre)."""
        qx, qy, qz = x - self.o[0], y - self.o[1], z - self.o[2]
        w, U, V = self.w, self.U, self.V
        s = qx * w[0] + qy * w[1] + qz * w[2]
        sc = np.clip(s, self.s0, self.s1)
        u = qx * U[0] + qy * U[1] + qz * U[2] - np.interp(sc, self.S, self.CU)
        v = qx * V[0] + qy * V[1] + qz * V[2] - np.interp(sc, self.S, self.CV)
        return s, u, v

    def _eval(self, x, y, z):
        s, u, v = self.local(x, y, z)
        sc = np.clip(s, self.s0, self.s1)
        fi = (sc - self.s0) / self.ds
        i0 = np.clip(np.floor(fi).astype(np.int64), 0, len(self.S) - 2)
        fs = fi - i0
        rho = np.sqrt(u * u + v * v)
        th = np.arctan2(v, u)
        fj = (th + PI) / (2.0 * PI) * self.nth
        j0f = np.floor(fj)
        ft = fj - j0f
        j0 = j0f.astype(np.int64) % self.nth
        j1 = (j0 + 1) % self.nth

        def bil(T):
            return ((1 - fs) * ((1 - ft) * T[i0, j0] + ft * T[i0, j1])
                    + fs * ((1 - ft) * T[i0 + 1, j0] + ft * T[i0 + 1, j1]))
        R = bil(self.R)
        Rs = bil(self.Rs)
        Rt = bil(self.Rt)
        g = np.sqrt(1.0 + Rs * Rs + (Rt / np.maximum(rho, 0.5 * R)) ** 2)
        d = (rho - R) / g
        if self.cap0 is not None:
            d = smax(d, self.cap0 - s, self.cap_k)
        if self.cap1 is not None:
            d = smax(d, s - self.cap1, self.cap_k)
        return d

    def __call__(self, x, y, z):
        return self.box.run(self._eval, x, y, z)


# ===========================================================================
# Torso and neck (vertical StarTube, U = +x, V = -y (front))
# ===========================================================================
# Stations [RB §7.1 landmarks + girth table, R05 §2.1; E where the tables are silent]:
# z, half width, front y, back y, superellipse n (front), n (back)
TORSO = np.array([
    (0.850, 0.118, -0.062, 0.078, 2.2, 2.2),
    (0.880, 0.146, -0.078, 0.096, 2.3, 2.4),
    (0.930, 0.157, -0.090, 0.100, 2.3, 2.4),     # pubic fat pad; inguinal groove carves the sides
    (0.990, 0.154, -0.106, 0.095, 2.5, 2.4),     # ASIS level (asis skin -0.072 at x 0.122)
    (1.040, 0.149, -0.113, 0.093, 2.7, 2.5),
    (1.075, 0.1465, -0.117, 0.0895, 2.8, 2.6),   # navel 84 cm: 29.5 x 20.5 (front -0.118 / back +0.087)
    (1.130, 0.1435, -0.114, 0.088, 2.9, 2.7),    # natural waist 81 cm; L4 spinous skin 0.080 (furrow)
    (1.200, 0.146, -0.108, 0.096, 2.8, 2.7),
    (1.260, 0.150, -0.105, 0.112, 2.9, 2.8),
    (1.300, 0.153, -0.108, 0.120, 3.0, 2.9),     # chest 100 cm; xiphisternal joint -0.110
    (1.340, 0.154, -0.100, 0.125, 3.0, 2.9),     # T7 spinous skin 0.122
    (1.400, 0.145, -0.081, 0.117, 3.0, 2.9),     # sternal angle -0.075 (bone) + skin
    (1.430, 0.150, -0.068, 0.108, 2.6, 2.6),     # shoulder girdle: clavicles in front, scapular spines behind
    (1.455, 0.148, -0.050, 0.097, 2.3, 2.4),     # jugular notch -0.048
    (1.470, 0.104, -0.050, 0.090, 2.2, 2.3),
    (1.485, 0.063, -0.054, 0.082, 2.1, 2.2),     # seam plane (plan D19)
    (1.515, 0.0595, -0.057, 0.069, 2.1, 2.2),    # neck 38 cm: 12 x 11.7 (front -0.055 / back +0.063)
    (1.540, 0.058, -0.054, 0.072, 2.1, 2.2),     # C7 spinous skin 0.075 at 1.532 (bump added)
    (1.565, 0.058, -0.047, 0.077, 2.1, 2.2),
    (1.595, 0.059, -0.033, 0.084, 2.1, 2.2),
    (1.625, 0.060, -0.020, 0.089, 2.1, 2.2),
    (1.660, 0.058, -0.010, 0.090, 2.1, 2.2),
])
TORSO_Z0, TORSO_Z1 = 0.862, 1.655


def torso_station(z):
    """(half width, front y, back y, n_front, n_back) interpolated at z."""
    T = TORSO
    return tuple(np.interp(z, T[:, 0], T[:, i]) for i in range(1, 6))


def torso_centre_y(z):
    """Mid y between the front and back skin at z (front/back split for regions and codes)."""
    _a, yf, yb, _nf, _nb = torso_station(z)
    return 0.5 * (yf + yb)


def _pec_relief(x, z):
    """Pectoralis major (+ areola / nipple) as outward relief of the front (m)."""
    ax = np.abs(x)
    # lower border: level medially, sweeping up laterally into the anterior axillary fold
    z_low = 1.265 + 2.8 * np.maximum(ax - 0.060, 0.0) ** 2 + 0.035 * sstep(0.110, 0.155, ax)
    lower = sstep(z_low - 0.010, z_low + 0.022, z)
    dome = np.interp(z, [1.26, 1.30, 1.36, 1.42, 1.455], [1.0, 1.0, 0.75, 0.35, 0.0])
    medial = sstep(0.006, 0.030, ax)                                # sternal furrow between the heads
    lateral = sstep(0.180, 0.130, ax)
    bulk = 0.0085 * lower * dome * medial * lateral
    areola = 0.0009 * gauss(np.hypot(ax - 0.100, (z - 1.300)), 0.012)
    nipple = 0.0026 * np.exp(-(np.hypot(ax - 0.100, z - 1.300) / 0.0042) ** 4)
    return bulk + areola + nipple


def _abdomen_relief(x, z):
    """Rectus abdominis, linea alba, tendinous intersections, linea semilunaris, navel, inguinal line."""
    ax = np.abs(x)
    rect = band(z, 0.965, 1.255, 0.03) * sstep(0.095, 0.060, ax)
    bulk = 0.0045 * rect * (0.7 + 0.3 * gauss(z - 1.00, 0.06))      # lower belly slightly rounded
    alba = -0.0022 * gauss(ax, 0.0055) * band(z, 1.09, 1.26, 0.02)
    inter = sum(-0.0008 * gauss(z - zi, 0.010) for zi in (1.140, 1.198)) * sstep(0.070, 0.045, ax)
    semil = -0.0018 * gauss(ax - 0.078, 0.008) * band(z, 1.0, 1.23, 0.03)
    # navel [RB §7.1 navel (0, -0.108, 1.075)]: pit with a soft rim
    rn = np.hypot(ax, (z - 1.075) * 0.85)
    navel = -0.0085 * np.exp(-(rn / 0.0065) ** 2.5) + 0.0012 * gauss(rn - 0.009, 0.005)
    # inguinal groove: ASIS skin (0.122, 0.992) -> pubic tubercle (0.022, 0.913)
    t = np.clip(((ax - 0.122) * -0.100 + (z - 0.992) * -0.079) / (0.100 ** 2 + 0.079 ** 2), 0.0, 1.2)
    px, pz = 0.122 - 0.100 * t, 0.992 - 0.079 * t
    ing = -0.0028 * gauss(np.hypot(ax - px, z - pz), 0.016) * sstep(1.2, 0.9, t)
    # costal margin: slight hollow below the ribs, epigastric fossa
    epi = -0.0022 * gauss(ax, 0.03) * gauss(z - 1.245, 0.025)
    jug = -0.004 * gauss(ax, 0.012) * gauss(z - 1.458, 0.010)
    return bulk + alba + inter + semil + navel + ing + epi + jug


def _tri_sdf2(px, pz, P):
    """2-D signed distance to a convex polygon P (list of (x, z), counter-clockwise)."""
    d = None
    inside = np.ones(px.shape, bool)
    for i in range(len(P)):
        ax_, az_ = P[i]
        bx_, bz_ = P[(i + 1) % len(P)]
        ex, ez = bx_ - ax_, bz_ - az_
        wx, wz = px - ax_, pz - az_
        h = np.clip((wx * ex + wz * ez) / (ex * ex + ez * ez), 0.0, 1.0)
        di = np.hypot(wx - ex * h, wz - ez * h)
        d = di if d is None else np.minimum(d, di)
        inside &= (ex * wz - ez * wx) >= 0.0
    return np.where(inside, -d, d)


# scapula outline on the back (x, z), counter-clockwise seen from behind with |x|:
SCAPULA = [(0.072, 1.470), (0.085, 1.322), (0.150, 1.410), (0.165, 1.455)]


def _back_relief(x, z):
    """Spinal furrow, erector columns, scapulae (+ spine of scapula), PSIS dimples, trapezius."""
    ax = np.abs(x)
    depth = np.interp(z, [0.95, 1.00, 1.05, 1.15, 1.22, 1.30, 1.40, 1.47, 1.55],
                      [0.003, 0.006, 0.0090, 0.0085, 0.006, 0.0025, 0.0020, 0.002, 0.004])
    width = np.interp(z, [0.95, 1.10, 1.25, 1.45, 1.55], [0.010, 0.016, 0.012, 0.010, 0.012])
    furrow = -depth * gauss(ax, width)
    erect = 0.0055 * gauss(ax - 0.036, 0.020) * band(z, 1.00, 1.30, 0.06)
    sd = _tri_sdf2(ax, z, SCAPULA)
    scap = 0.0055 * sstep(0.016, -0.022, sd)
    scap += 0.0025 * gauss(np.hypot(ax - 0.086, z - 1.330), 0.015)            # inferior angle
    # spine of the scapula: ridge from the medial border up-laterally to the acromion
    t = np.clip(((ax - 0.075) * 0.095 + (z - 1.428) * 0.030) / (0.095 ** 2 + 0.030 ** 2), 0.0, 1.0)
    ridge = 0.0025 * gauss(np.hypot(ax - (0.075 + 0.095 * t), z - (1.428 + 0.030 * t)), 0.006)
    fossa = -0.002 * gauss(np.hypot(ax - 0.115, z - 1.448), 0.012)            # supraspinous hollow
    psis = -0.0045 * gauss(np.hypot(ax - 0.045, z - 1.010), 0.008)            # [RB §7.1 psis_dimple]
    lat = 0.003 * gauss(ax - 0.12, 0.03) * band(z, 1.18, 1.36, 0.05)
    trap = 0.004 * gauss(ax - 0.035, 0.03) * band(z, 1.40, 1.52, 0.04)         # upper trapezius mass
    return furrow + erect + scap + ridge + fossa + psis + lat + trap


def _side_relief(y, z):
    """Latissimus flare, obliques over the iliac crest (the flank pad), serratus."""
    lat = 0.009 * band(z, 1.20, 1.36, 0.06) * gauss(y - 0.050, 0.045)
    obl = 0.0065 * gauss(z - 1.045, 0.035) * gauss(y + 0.010, 0.05)
    waist = -0.003 * gauss(z - 1.140, 0.04)
    serr = 0.0025 * band(z, 1.24, 1.34, 0.03) * gauss(y + 0.050, 0.025)
    return lat + obl + waist + serr


def _torso_profile(Z, TH):
    a, yf, yb, nf, nb = torso_station(Z)
    n = np.where(np.sin(TH) >= 0.0, nf, nb)
    R0 = quad_radius(TH, a, -yf, a, yb, n)
    xs = R0 * np.cos(TH)
    ys = -R0 * np.sin(TH)
    sn = np.sin(TH)
    wf = sstep(0.15, 0.55, sn)
    wb = sstep(0.15, 0.55, -sn)
    ws = sstep(0.25, 0.75, np.abs(np.cos(TH)))
    trunk = sstep(1.53, 1.47, Z)                    # reliefs belong to the trunk, not the neck
    rel = wf * (_pec_relief(xs, Z) + _abdomen_relief(xs, Z)) + wb * _back_relief(xs, Z)
    rel = rel * trunk + ws * _side_relief(ys, Z) * trunk
    # neck: laryngeal prominence handled as a primitive; nuchal furrow at the back midline
    nuchal = -0.0025 * gauss(xs, 0.010) * band(Z, 1.55, 1.62, 0.03) * wb
    nuchal = nuchal + 0.0045 * gauss(xs, 0.012) * gauss(Z - 1.530, 0.012) * wb       # C7 vertebra prominens
    return R0 + rel + nuchal


TORSO_TUBE = None


def _torso_tube():
    global TORSO_TUBE
    if TORSO_TUBE is None:
        TORSO_TUBE = StarTube((0.0, 0.0, 0.0), (0, 0, 1), (1, 0, 0), (0, -1, 0), TORSO_Z0 - 0.01,
                              TORSO_Z1 + 0.01, _torso_profile, ds=0.002, nth=240,
                              cap0=TORSO_Z0, cap1=TORSO_Z1, cap_k=0.02)
    return TORSO_TUBE


# ===========================================================================
# Arm (left, A-pose: d = (0.5, 0, -0.866), palms to the thighs, thumbs forward)
# ===========================================================================
ARM_D = np.array(LM.ARM_DIRECTION_L)
ARM_NM = np.array(LM.ARM_MEDIAL_NORMAL_L)          # palm-side (medial) normal
ARM_LAT = -ARM_NM
GH = LM.landmark("gh_joint_L")
ELBOW = LM.landmark("elbow_centre_L_apose")
WRIST = LM.landmark("wrist_centre_L_apose")
S_ELBOW = float((ELBOW - GH) @ ARM_D)               # 0.290
S_WRIST = float((WRIST - GH) @ ARM_D)               # 0.560

# s from the shoulder joint, radii lateral / anterior / medial / posterior, n
ARM = np.array([
    (-0.050, 0.044, 0.047, 0.040, 0.049, 2.2),
    (0.000, 0.046, 0.049, 0.041, 0.050, 2.2),
    (0.060, 0.044, 0.047, 0.040, 0.050, 2.2),
    (0.120, 0.041, 0.045, 0.040, 0.049, 2.2),
    (0.180, 0.039, 0.044, 0.038, 0.045, 2.2),
    (0.235, 0.037, 0.041, 0.036, 0.039, 2.25),
    (0.275, 0.036, 0.037, 0.038, 0.036, 2.3),       # elbow (epicondyles, olecranon added)
    (0.310, 0.040, 0.040, 0.038, 0.037, 2.3),
    (0.345, 0.040, 0.042, 0.037, 0.036, 2.3),       # forearm max 27.5 cm, 5 cm below the elbow
    (0.400, 0.035, 0.039, 0.032, 0.034, 2.35),
    (0.455, 0.028, 0.034, 0.025, 0.031, 2.45),
    (0.510, 0.021, 0.030, 0.020, 0.029, 2.7),
    (0.545, 0.019, 0.0285, 0.019, 0.028, 2.9),      # wrist 17 cm: 5.8 radial-ulnar (Y) x 4.0
    (0.590, 0.017, 0.029, 0.017, 0.028, 3.0),
])


def _arm_profile(S, TH):
    A_ = ARM
    rl, ra, rm, rp, n = (np.interp(S, A_[:, 0], A_[:, i]) for i in range(1, 6))
    R = quad_radius(TH, rl, ra, rm, rp, n)

    def bump(s0, th0, amp, ss, sth):
        return amp * gauss(S - s0, ss) * gauss(wrap(TH - np.radians(th0)), np.radians(sth))
    R = R + bump(0.185, 100, 0.0085, 0.055, 38)          # biceps
    R = R + bump(0.120, -95, 0.0060, 0.070, 50)          # triceps (long + lateral heads)
    R = R + bump(0.205, -150, 0.0030, 0.050, 30)         # triceps medial head
    R = R + bump(0.215, 35, 0.0025, 0.040, 30)           # brachialis lateral to the biceps
    R = R + bump(0.090, 150, -0.0030, 0.050, 30)         # bicipital furrow (medial)
    R = R + bump(0.285, 170, 0.0045, 0.014, 22)          # medial epicondyle
    R = R + bump(0.283, 0, 0.0020, 0.012, 25)            # lateral epicondyle
    R = R + bump(0.278, -90, 0.0055, 0.013, 28)          # olecranon
    R = R + bump(0.272, 95, -0.0045, 0.016, 35)          # antecubital fossa
    R = R + bump(0.325, 55, 0.0065, 0.045, 38)           # brachioradialis / extensor mass
    R = R + bump(0.335, 150, 0.0050, 0.050, 40)          # flexor mass
    R = R + bump(0.470, -100, -0.0010, 0.070, 25)        # subcutaneous ulnar border (lean)
    R = R + bump(0.540, -95, 0.0022, 0.009, 25)          # ulnar head / styloid
    R = R + bump(0.545, 95, 0.0015, 0.010, 30)           # radial styloid
    return R


ARM_TUBE = None


def _arm_tube():
    global ARM_TUBE
    if ARM_TUBE is None:
        ARM_TUBE = StarTube(GH, ARM_D, ARM_LAT, (0, -1, 0), -0.06, 0.60, _arm_profile, ds=0.002, nth=144,
                            cap0=-0.045, cap1=0.585, cap_k=0.012)
    return ARM_TUBE


def _fold(ax, y, z, a, b, half_thick, half_height, up=(0.0, 0.0, 1.0)):
    """Flattened ellipsoid spanning a -> b (axillary fold web): long axis a->b, height along ``up``."""
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    L = np.linalg.norm(b - a)
    axes = frame(b - a, up)
    return sd_oellipsoid(ax, y, z, 0.5 * (a + b), (0.5 * L + 0.012, half_height, half_thick), axes)


def _shoulder(ax, y, z):
    """Deltoid cap, trapezius, clavicle, axillary folds (left, |x|)."""
    delt_axes = frame(ARM_D, ARM_LAT)
    c = GH + 0.036 * ARM_D + 0.013 * ARM_LAT + np.array([0.0, -0.003, 0.0])
    delt = sd_oellipsoid(ax, y, z, c, (0.090, 0.046, 0.057), delt_axes, n=2.0)
    # deltoid insertion: the cap narrows to a V on the lateral mid-humerus
    tub = sd_capsule(ax, y, z, GH + 0.05 * ARM_D + 0.036 * ARM_LAT, GH + 0.150 * ARM_D + 0.034 * ARM_LAT,
                     0.014, 0.005)
    delt = smin(delt, tub, 0.02)
    # upper trapezius: broad slope from the nape to the acromion
    # the lateral neck point sits at z ~1.49 (between the jugular notch 1.455 and C7 1.532) and the
    # shoulder line falls ~11 deg to the acromion; below the seam plane beyond |x| 0.075 (plan D19 ring)
    trap = sd_polyline(ax, y, z, [(0.035, 0.050, 1.459), (0.100, 0.038, 1.4525), (0.186, 0.020, 1.446)],
                       [0.022, 0.0235, 0.016], k=0.02)
    clav = sd_polyline(ax, y, z, [np.array(p) + np.array([0.0, -0.001, 0.001]) for p in
                                  ((0.022, -0.040, 1.451), (0.070, -0.050, 1.453), (0.125, -0.021, 1.463),
                                   (0.168, 0.008, 1.463))], [0.0095, 0.0080, 0.0078, 0.0095], k=0.01)
    # axillary folds: the pectoralis (front) and latissimus/teres (back) sweep from the chest wall into
    # the arm; only their lower borders show, the web above them fills up to the shoulder
    a_arm = GH + 0.075 * ARM_D - 0.018 * ARM_LAT + np.array([0.0, -0.022, 0.0])
    ant_fold = _fold(ax, y, z, (0.120, -0.058, 1.380), a_arm, 0.016, 0.040)
    p_arm = GH + 0.085 * ARM_D - 0.016 * ARM_LAT + np.array([0.0, 0.028, 0.0])
    post_fold = _fold(ax, y, z, (0.120, 0.070, 1.350), p_arm, 0.020, 0.045)
    return delt, trap, clav, ant_fold, post_fold


# ===========================================================================
# Hand (left): simplified per plan D4 - relaxed curl, fused webbing, no nails/knuckle geometry
# local axes: d (distal), f = -Y (radial / thumb side, forward), n = ARM_NM (palmar)
# ===========================================================================
HAND_F = np.array([0.0, -1.0, 0.0])
HAND_N = ARM_NM


def hand_point(s, r, p):
    """Body-frame point from hand-local (distal s, radial r, palmar p) about the wrist centre."""
    return WRIST + s * ARM_D + r * HAND_F + p * HAND_N


# fingers: radial offset at the MCP, MCP distal s, length (MCP -> tip), base radius, tip radius, spread deg
FINGERS = {
    "index": (0.0255, 0.0905, 0.076, 0.0098, 0.0078, 4.0),
    "middle": (0.0060, 0.0950, 0.084, 0.0100, 0.0080, 0.0),
    "ring": (-0.0125, 0.0915, 0.079, 0.0094, 0.0075, -3.0),
    "little": (-0.0290, 0.0835, 0.063, 0.0082, 0.0066, -7.0),
}
FINGER_CURL = (14.0, 22.0, 16.0)          # per joint (MCP, PIP, DIP) toward the palm, relaxed [plan §1.2]


def finger_polyline(name):
    """MCP, PIP, DIP, tip points (body frame) of a left finger in the relaxed curl."""
    r0, s0, L, _rb, _rt, spread = FINGERS[name]
    seg = np.array([0.46, 0.30, 0.24]) * L
    sp = math.radians(spread)
    fwd = math.cos(sp) * ARM_D + math.sin(sp) * HAND_F
    pts = [hand_point(s0, r0, 0.001)]
    ang = 0.0
    for L_i, c in zip(seg, FINGER_CURL):
        ang += math.radians(c)
        d = math.cos(ang) * fwd + math.sin(ang) * HAND_N
        pts.append(pts[-1] + L_i * d)
    return np.array(pts)


THUMB_PTS = [(0.012, 0.020, 0.006), (0.050, 0.037, 0.017), (0.078, 0.046, 0.024), (0.100, 0.049, 0.028)]
THUMB_R = [0.0135, 0.0112, 0.0098, 0.0086]


def _palm_profile(S, TH):
    # hand-local tube: U = palmar (n), V = radial (f); radii palmar / radial / dorsal / ulnar
    rp = np.interp(S, [-0.02, 0.01, 0.03, 0.06, 0.085, 0.10], [0.019, 0.018, 0.017, 0.015, 0.012, 0.010])
    rr = np.interp(S, [-0.02, 0.01, 0.04, 0.07, 0.09, 0.10], [0.030, 0.030, 0.033, 0.036, 0.036, 0.034])
    rd = np.interp(S, [-0.02, 0.01, 0.04, 0.08, 0.10], [0.017, 0.015, 0.012, 0.011, 0.010])
    ru = np.interp(S, [-0.02, 0.01, 0.04, 0.07, 0.09, 0.10], [0.028, 0.029, 0.034, 0.036, 0.034, 0.030])
    n = np.interp(S, [-0.02, 0.02, 0.06], [2.6, 3.2, 3.6])
    return quad_radius(TH, rp, rr, rd, ru, n)


PALM_TUBE = None


def _palm_tube():
    global PALM_TUBE
    if PALM_TUBE is None:
        PALM_TUBE = StarTube(WRIST, ARM_D, HAND_N, HAND_F, -0.03, 0.105, _palm_profile, ds=0.0015, nth=120,
                             cap0=-0.02, cap1=0.098, cap_k=0.012)
    return PALM_TUBE


def _hand(ax, y, z):
    d = _palm_tube()._eval(ax, y, z)
    ax3 = frame(ARM_D, HAND_F)
    then = sd_oellipsoid(ax, y, z, hand_point(0.036, 0.021, 0.013), (0.030, 0.016, 0.012), ax3)
    hypo = sd_oellipsoid(ax, y, z, hand_point(0.045, -0.026, 0.011), (0.035, 0.011, 0.009), ax3)
    d = smin(d, then, 0.010)
    d = smin(d, hypo, 0.010)
    fingers = None
    for name, (_r0, _s0, _L, rb, rt, _sp) in FINGERS.items():
        P = finger_polyline(name)
        f = sd_polyline(ax, y, z, P, [rb, rb * 0.93, rt * 1.03, rt * 0.92], k=0.003)
        # finger pads (palmar fullness of each phalanx)
        fingers = f if fingers is None else smin(fingers, f, 0.0035)
    d = smin(d, fingers, 0.007)
    th = sd_polyline(ax, y, z, [hand_point(*p) for p in THUMB_PTS], THUMB_R, k=0.004)
    return smin(d, th, 0.009)


HAND_BOX = None


def _hand_box():
    global HAND_BOX
    if HAND_BOX is None:
        pts = [hand_point(s, r, p) for s in (-0.03, 0.2) for r in (-0.05, 0.07) for p in (-0.03, 0.06)]
        pts = np.array(pts)
        HAND_BOX = Box(pts.min(0), pts.max(0), margin=0.03)
    return HAND_BOX


# ===========================================================================
# Leg (left): axis hip joint centre -> ankle centre [RB §7.2], U = +X, V = -Y
# ===========================================================================
HIP = LM.landmark("hip_joint_centre_L")
KNEE = LM.landmark("knee_centre_L")
ANKLE = LM.landmark("ankle_centre_L")
LEG_W = unit(ANKLE - HIP)

# z, front y, back y, medial x, lateral x, n   [RB §7.1 girths: upper thigh 58, mid 51, knee 37.5, calf 37.5,
#                                                ankle 22.5; landmarks: trochanter skin 0.178, patella skin -0.047]
LEG = np.array([
    (1.010, -0.040, 0.070, 0.050, 0.130, 2.3),      # thigh top buried in the pelvis
    (0.960, -0.060, 0.095, 0.020, 0.160, 2.3),      # femoral triangle below the inguinal crease
    (0.910, -0.075, 0.108, 0.008, 0.177, 2.3),
    (0.860, -0.079, 0.116, 0.004, 0.177, 2.3),
    (0.820, -0.076, 0.118, 0.004, 0.177, 2.3),      # gluteal fold (0.090, 0.120, 0.820)
    (0.790, -0.073, 0.108, 0.004, 0.176, 2.3),      # upper thigh 58 cm (17.5 x 18.5)
    (0.740, -0.070, 0.099, 0.009, 0.173, 2.3),
    (0.700, -0.067, 0.093, 0.014, 0.169, 2.3),      # mid thigh 51 cm
    (0.650, -0.064, 0.089, 0.020, 0.166, 2.3),
    (0.600, -0.060, 0.080, 0.029, 0.159, 2.3),
    (0.555, -0.056, 0.071, 0.036, 0.152, 2.3),
    (0.520, -0.052, 0.067, 0.038, 0.148, 2.3),
    (0.495, -0.043, 0.066, 0.037, 0.146, 2.35),     # knee 37.5 cm (patella adds 6 mm -> skin -0.049)
    (0.465, -0.041, 0.069, 0.038, 0.144, 2.35),
    (0.440, -0.033, 0.078, 0.040, 0.144, 2.3),
    (0.410, -0.020, 0.097, 0.040, 0.146, 2.3),
    (0.370, -0.002, 0.116, 0.040, 0.148, 2.3),      # calf 37.5 cm
    (0.330, 0.008, 0.119, 0.043, 0.145, 2.3),
    (0.280, 0.016, 0.116, 0.048, 0.141, 2.3),
    (0.220, 0.023, 0.101, 0.055, 0.135, 2.35),
    (0.160, 0.024, 0.092, 0.061, 0.129, 2.4),
    (0.120, 0.019, 0.091, 0.0625, 0.1275, 2.4),     # ankle 22.5 cm
    (0.090, 0.016, 0.089, 0.062, 0.128, 2.4),
    (0.050, 0.018, 0.090, 0.062, 0.128, 2.4),
])


def leg_axis_at_z(z):
    """Point of the hip->ankle axis at height z."""
    t = (HIP[2] - z) / (HIP[2] - ANKLE[2])
    return HIP[None, :] + np.asarray(t)[..., None] * (ANKLE - HIP)[None, :]


def _leg_s_to_z(S):
    return HIP[2] + S * LEG_W[2]


def _leg_profile(S, TH):
    z = _leg_s_to_z(S)
    L_ = LEG
    yf, yb, xm, xl, n = (np.interp(z, L_[::-1, 0], L_[::-1, i]) for i in range(1, 6))
    P = leg_axis_at_z(z.ravel()).reshape(z.shape + (3,))
    px, py = P[..., 0], P[..., 1]
    R = quad_radius(TH, xl - px, py - yf, px - xm, yb - py, n)

    def bump(z0, th0, amp, sz, sth):
        return amp * gauss(z - z0, sz) * gauss(wrap(TH - np.radians(th0)), np.radians(sth))
    R = R + bump(0.585, 145, 0.0085, 0.040, 32)          # vastus medialis teardrop
    R = R + bump(0.700, 20, 0.0045, 0.100, 40)           # vastus lateralis
    R = R + bump(0.720, 88, 0.0040, 0.090, 25)           # rectus femoris
    R = R + bump(0.790, 172, 0.0040, 0.060, 30)          # adductors (inner upper thigh)
    R = R + bump(0.690, -95, 0.0040, 0.090, 45)          # hamstrings
    R = R + bump(0.690, -10, -0.0020, 0.090, 12)         # iliotibial band flat
    # sartorius furrow: spirals from the front-lateral hip to the medial knee
    th_s = np.radians(np.interp(z, [0.50, 0.62, 0.75, 0.88], [175, 150, 120, 95]))
    R = R - 0.0022 * gauss(wrap(TH - th_s), np.radians(10)) * band(z, 0.52, 0.86, 0.03)
    # knee [RB §7.1 patella skin (0.090, -0.047, 0.497)]: flat-topped patella, tendon, fat pads, tuberosity
    arc = wrap(TH - np.radians(90)) * 0.050                 # ~ metres along the front of the knee
    rp = np.hypot(arc / 0.021, (z - 0.500) / 0.024)
    R = R + 0.0060 * np.exp(-rp ** 4)
    rt = np.hypot(arc / 0.0065, (z - 0.455) / 0.020)
    R = R + 0.0022 * np.exp(-rt ** 2)
    for side in (-1.0, 1.0):
        rf = np.hypot((arc - side * 0.020) / 0.010, (z - 0.462) / 0.012)
        R = R + 0.0018 * np.exp(-rf ** 2)
    rtt = np.hypot(arc / 0.012, (z - 0.434) / 0.010)
    R = R + 0.0025 * np.exp(-rtt ** 2)
    R = R + bump(0.500, -90, -0.0035, 0.025, 25)         # popliteal fossa
    R = R + bump(0.530, -55, 0.0020, 0.030, 12)          # biceps femoris tendon
    R = R + bump(0.530, -125, 0.0022, 0.030, 12)         # semitendinosus tendon
    R = R + bump(0.452, -25, 0.0022, 0.012, 20)          # fibular head
    R = R + bump(0.365, -125, 0.0075, 0.050, 34)         # gastrocnemius medial head (lower)
    R = R + bump(0.395, -58, 0.0050, 0.045, 30)          # gastrocnemius lateral head
    R = R + bump(0.330, 55, 0.0030, 0.080, 25)           # tibialis anterior
    R = R + bump(0.300, 125, -0.0020, 0.100, 20)         # flat subcutaneous tibial face (lean)
    R = R + bump(0.150, -50, -0.0020, 0.040, 25)         # hollows beside the Achilles tendon
    R = R + bump(0.150, -130, -0.0020, 0.040, 25)
    return R


def _leg_offset(S):
    return np.zeros_like(S), np.zeros_like(S)


LEG_TUBE = None


def _leg_tube():
    global LEG_TUBE
    if LEG_TUBE is None:
        s_top = (1.01 - HIP[2]) / LEG_W[2]
        s_bot = (0.05 - HIP[2]) / LEG_W[2]
        LEG_TUBE = StarTube(HIP, LEG_W, (1, 0, 0), (0, -1, 0), s_top - 0.01, s_bot + 0.01, _leg_profile,
                            ds=0.002, nth=144, cap0=s_top, cap1=s_bot, cap_k=0.015)
    return LEG_TUBE


def _glute(ax, y, z):
    """Gluteus maximus mass (left): overhangs the gluteal fold at z 0.82 [RB §7.1 gluteal_fold (0.090, 0.120)]."""
    axes = frame((0.10, 0.0, -1.0), (1.0, 0.0, 0.0))
    return sd_oellipsoid(ax, y, z, (0.074, 0.058, 0.905), (0.098, 0.083, 0.087), axes, n=2.0)


# ===========================================================================
# Foot (left): heel (0.095, 0.115, 0.030) -> 2nd toe tip (0.128, -0.151, 0.010), length 26.8, breadth 10.2
# ===========================================================================
HEEL = LM.landmark("heel_L")
TOE2 = LM.landmark("toe2_tip_L")
FOOT_F = unit(np.array([TOE2[0] - HEEL[0], TOE2[1] - HEEL[1], 0.0]))     # heel -> toe (7 deg toe-out)
FOOT_L = np.array([-FOOT_F[1], FOOT_F[0], 0.0])                           # lateral (+x side)
FOOT_O = np.array([HEEL[0], HEEL[1], 0.0])                                # heel back on the floor
FOOT_LEN = float(np.linalg.norm((TOE2 - HEEL)[:2]))


def foot_point(s, w, h):
    """Body-frame point from foot-local (s from the heel back, w lateral, h height)."""
    return FOOT_O + s * FOOT_F + w * FOOT_L + np.array([0.0, 0.0, h])


# stations: s, medial w, lateral w, top h, sole centre h (tube centre height), n
FOOT = np.array([
    (0.000, 0.020, 0.020, 0.050, 0.032, 2.2),
    (0.020, 0.029, 0.029, 0.070, 0.036, 2.3),
    (0.045, 0.031, 0.031, 0.086, 0.042, 2.4),
    (0.075, 0.031, 0.033, 0.084, 0.042, 2.5),
    (0.110, 0.033, 0.038, 0.072, 0.036, 2.7),     # navicular / cuneiforms: instep
    (0.145, 0.038, 0.045, 0.058, 0.030, 2.9),
    (0.175, 0.045, 0.051, 0.045, 0.024, 3.0),
    (0.200, 0.049, 0.052, 0.036, 0.020, 3.0),     # ball of the foot (MTP row): breadth 10.2 cm
    (0.220, 0.046, 0.047, 0.030, 0.017, 3.0),
    (0.235, 0.040, 0.040, 0.026, 0.015, 2.8),
])


def _foot_profile(S, TH):
    F_ = FOOT
    wm, wl, top, hc, n = (np.interp(S, F_[:, 0], F_[:, i]) for i in range(1, 6))
    # section: U = lateral, V = up; centre height hc; bottom reaches below the floor (clipped)
    return quad_radius(TH, wl, top - hc, wm, hc + 0.006, n)


FOOT_TUBE = None


def _foot_tube():
    global FOOT_TUBE
    if FOOT_TUBE is None:
        def off(S):
            F_ = FOOT
            return np.zeros_like(S), np.interp(S, F_[:, 0], F_[:, 4])
        FOOT_TUBE = StarTube(FOOT_O, FOOT_F, FOOT_L, (0, 0, 1), -0.01, 0.24, _foot_profile, offset=off,
                             ds=0.002, nth=120, cap0=0.004, cap1=0.228, cap_k=0.015)
    return FOOT_TUBE


TOES = [  # base s, w, tip s, tip w, radius base, radius tip, tip centre height
    (0.200, -0.031, 0.262, -0.032, 0.0140, 0.0118, 0.0125),     # hallux (medial)
    (0.212, -0.008, FOOT_LEN - 0.0065, -0.004, 0.0092, 0.0070, 0.0085),
    (0.206, 0.010, 0.256, 0.013, 0.0088, 0.0068, 0.0080),
    (0.198, 0.025, 0.246, 0.028, 0.0084, 0.0066, 0.0077),
    (0.188, 0.039, 0.231, 0.043, 0.0080, 0.0062, 0.0072),       # little toe (lateral)
]


def _foot(ax, y, z):
    d = _foot_tube()._eval(ax, y, z)
    # heel: rounded calcaneal pad
    heel = sd_oellipsoid(ax, y, z, foot_point(0.036, 0.001, 0.034), (0.030, 0.032, 0.036), np.eye(3))
    d = smin(d, heel, 0.02)
    # toes merged (plan D4) but individually shaped at the tips
    toes = None
    for s0, w0, s1, w1, r0, r1, h1 in TOES:
        mid = foot_point(0.5 * (s0 + s1 - r1) + 0.004, 0.5 * (w0 + w1), h1 + 0.4 * r0)   # toes arch slightly up
        t = sd_polyline(ax, y, z, [foot_point(s0, w0, r0 + 0.004), mid, foot_point(s1 - r1, w1, h1)],
                        [r0, 0.5 * (r0 + r1) * 1.02, r1], k=0.004)
        toes = t if toes is None else smin(toes, t, 0.0028)
    d = smin(d, toes, 0.012)
    # medial longitudinal arch: carve under the medial mid-foot
    arch = sd_oellipsoid(ax, y, z, foot_point(0.125, -0.040, -0.004), (0.060, 0.026, 0.020),
                         frame(FOOT_F, FOOT_L))
    d = smax(d, -arch, 0.012)
    # malleoli [RB §7.1]: lateral lower and posterior, medial higher
    mal = smin(sd_oellipsoid(ax, y, z, (0.129, 0.060, 0.057), (0.010, 0.013, 0.016), np.eye(3)),
               sd_oellipsoid(ax, y, z, (0.069, 0.046, 0.069), (0.010, 0.014, 0.015), np.eye(3)), 0.01)
    d = smin(d, mal, 0.012)
    # Achilles tendon into the heel
    ach = sd_capsule(ax, y, z, (0.096, 0.080, 0.200), (0.095, 0.092, 0.050), 0.0085, 0.0115)
    d = smin(d, ach, 0.014)
    return np.maximum(d, -z)                         # flat sole on the floor


FOOT_BOX = Box((0.02, -0.17, -0.01), (0.19, 0.14, 0.24), margin=0.03)


# ===========================================================================
# Neck primitives
# ===========================================================================
def _neck_parts(ax, y, z):
    """Sternocleidomastoid ridges and the laryngeal prominence [RB §7.1 (0, -0.062, 1.537)]."""
    scm = sd_capsule(ax, y, z, (0.018, -0.049, 1.462), (0.058, 0.022, 1.600), 0.0105, 0.0135)
    lar = sd_oellipsoid(ax, y, z, (0.0, -0.050, 1.535), (0.013, 0.0125, 0.017), np.eye(3))
    return scm, lar


# ===========================================================================
# Body skin SDF
# ===========================================================================
BODY_BOX_LO = (-0.62, -0.20, -0.005)
BODY_BOX_HI = (0.62, 0.20, 1.68)


def body_components(x, y, z):
    """Component SDFs of the body (left authored, |x|).  Returns a dict of arrays."""
    ax = np.abs(x)
    out = {"torso": _torso_tube()(ax, y, z)}
    sh = Box((0.0, -0.10, 1.25), (0.30, 0.10, 1.53), margin=0.05)
    delt, trap, clav, afold, pfold = sh.run_multi(_shoulder, ax, y, z)[:5]
    out.update(deltoid=delt, trapezius=trap, clavicle=clav, ant_fold=afold, post_fold=pfold)
    nk = Box((0.0, -0.08, 1.43), (0.08, 0.05, 1.62), margin=0.03)
    out["scm"], out["larynx"] = nk.run_multi(_neck_parts, ax, y, z)[:2]
    out["arm"] = _arm_tube()(ax, y, z)
    out["hand"] = _hand_box().run(_hand, ax, y, z)
    out["leg"] = _leg_tube()(ax, y, z)
    out["glute"] = Box((0.0, -0.05, 0.78), (0.19, 0.16, 1.05), margin=0.08).run(_glute, ax, y, z)
    out["glute_k"] = 0.010 + 0.045 * sstep(0.85, 0.99, z) + 0.02 * sstep(0.10, 0.15, ax)
    out["foot"] = FOOT_BOX.run(_foot, ax, y, z)
    out["_y"] = y
    return out


def union_components(c, off=None):
    """Blend the components into the body (``off``: per-component inward offsets, m)."""
    o = off or {}
    g = {k: (v + o.get(k, 0.0) if not (k.endswith("_k") or k.startswith("_")) else v) for k, v in c.items()}
    trunk = smin(g["torso"], g["scm"], 0.012)
    trunk = smin(trunk, g["larynx"], 0.008)
    trunk = smin(trunk, g["trapezius"], 0.020)
    trunk = smin(trunk, g["clavicle"], 0.016)
    arm = smin(g["arm"], g["deltoid"], 0.030)
    arm = smin(arm, g["hand"], 0.012)
    body = smin(trunk, arm, 0.010)
    body = smin(body, g["ant_fold"], 0.028)
    body = smin(body, g["post_fold"], 0.030)
    leg = smin(g["leg"], g["foot"], 0.012)
    body = smin(body, leg, 0.022 + 0.015 * sstep(0.02, -0.06, g["_y"]))
    # gluteal fold stays crisp below, the upper and outer buttock melt into the back and hip
    return smin(body, g["glute"], g["glute_k"])


def body_sdf(x, y, z):
    """Body skin SDF (no head), body frame, negative inside."""
    return union_components(body_components(x, y, z))


# ===========================================================================
# Head join: the head project's neck column is ~3 cm behind the bible neck (B0/B2 finding), so the
# head skin is clipped under the jaw and the occiput and the body neck (bible-placed) takes over.
# ===========================================================================
def head_clip_z(x, y):
    """Height below which the head project's skin is replaced by the body neck (body frame)."""
    ax = np.abs(x)
    zc = np.interp(y, [-0.12, -0.030, 0.000, 0.030, 0.070, 0.12], [1.536, 1.540, 1.560, 1.590, 1.612, 1.622])
    return zc + 0.010 * sstep(0.04, 0.07, ax) * sstep(0.03, -0.02, y)


def _head_part(x, y, z):
    A = _A()
    h = A.skin_sdf(x, y - HEAD_OFFSET[1], z - HEAD_OFFSET[2])
    return smax(h, head_clip_z(x, y) - z, 0.006)


HEAD_BOX = Box((-0.12, -0.135, 1.50), (0.12, 0.15, 1.80), margin=0.03)


def skin_sdf(x, y, z):
    """Combined outer skin: gore_head head (clipped under the jaw/occiput) smooth-united with the body."""
    b = body_sdf(x, y, z)
    h = HEAD_BOX.run(_head_part, x, y, z)
    k = 0.004 + 0.012 * sstep(1.52, 1.56, z)
    return smin(b, h, k)




# ===========================================================================
# Tissue thickness [RB §7.6] and skin tension lines [RB §2.3.1]
# ===========================================================================
FAT_SCALE = LM.BODY_FAT_PCT / 15.0          # fat map is for 15 % body fat (tissue.FAT_MM)
GROUPS = {"torso": ("torso", "scm", "larynx", "trapezius", "clavicle", "ant_fold", "post_fold"),
          "glute": ("glute",), "arm": ("arm", "deltoid"), "hand": ("hand",), "leg": ("leg",), "foot": ("foot",)}


def _group_distances(c):
    """Minimum component distance per tissue group."""
    out = {}
    for g, names in GROUPS.items():
        d = c[names[0]]
        for n in names[1:]:
            d = np.minimum(d, c[n])
        out[g] = d
    return out


def arm_local(ax, y, z):
    """(s along the arm from the shoulder joint, theta: 0 lateral, 90 anterior, 180 medial, -90 posterior)."""
    q = np.stack([ax - GH[0], y - GH[1], z - GH[2]], -1)
    s = q @ ARM_D
    return s, np.arctan2(-(q[..., 1]), q @ ARM_LAT)


def leg_local(ax, y, z):
    """(z, theta about the hip->ankle axis: 0 lateral, 90 anterior, 180 medial, -90 posterior)."""
    P = leg_axis_at_z(z)
    return z, np.arctan2(-(y - P[..., 1]), ax - P[..., 0])


def foot_local(ax, y, z):
    """(s from the heel back along the foot, w lateral, h)."""
    q = np.stack([ax - FOOT_O[0], y - FOOT_O[1]], -1)
    return q @ FOOT_F[:2], q @ FOOT_L[:2], z


def _tissue_group(g, ax, y, z):
    """(skin, fat, muscle) thickness in mm for one group at the points (15 % fat reference)."""
    one = np.ones_like(z)
    if g == "torso":
        cy = torso_centre_y(z)
        wf = sstep(cy + 0.02, cy - 0.02, y)                      # 1 front, 0 back
        _a, yf, yb, _nf, _nb = torso_station(z)
        side = sstep(0.75, 0.95, np.abs(ax) / np.maximum(_a, 1e-3))
        neck = sstep(1.455, 1.49, z)
        skin = wf * 2.0 + (1 - wf) * 3.5
        skin = skin * (1 - neck) + neck * (wf * 1.6 + (1 - wf) * 3.0)
        chest = sstep(1.22, 1.28, z)
        fat_f = chest * 6.0 + (1 - chest) * np.interp(z, [0.86, 0.92, 0.98, 1.10, 1.20, 1.25],
                                                      [10.0, 13.0, 16.0, 15.0, 11.0, 7.0])
        stern = sstep(0.028, 0.012, ax) * band(z, 1.27, 1.45, 0.01)
        fat_f = fat_f * (1 - stern) + stern * 4.0
        fat_b = np.interp(z, [0.86, 0.95, 1.05, 1.15, 1.25, 1.45], [14.0, 14.0, 12.0, 10.0, 8.0, 7.0])
        spinous = sstep(0.014, 0.004, ax)
        fat_b = fat_b * (1 - spinous) + spinous * 4.0
        fat = wf * fat_f + (1 - wf) * fat_b
        flank = side * band(z, 0.98, 1.16, 0.04)
        fat = fat * (1 - flank) + flank * 15.0
        fat = fat * (1 - neck) + neck * (wf * 3.5 + (1 - wf) * 5.0)
        mus_f = chest * 25.0 + (1 - chest) * 11.0
        mus_f = mus_f * (1 - stern)
        mus = wf * mus_f + (1 - wf) * 40.0 * (1 - spinous)
        mus = mus * (1 - neck) + neck * (wf * 8.0 + (1 - wf) * 30.0)
        return skin, fat, mus
    if g == "glute":
        return 2.7 * one, 20.0 * one, 40.0 * one
    if g == "arm":
        s, th = arm_local(ax, y, z)
        fore = sstep(0.26, 0.31, s)
        wrist = sstep(0.47, 0.53, s)
        ulnar = gauss(wrap(th + np.radians(100)), np.radians(30)) * fore
        olec = gauss(s - 0.28, 0.02) * gauss(wrap(th + np.radians(90)), np.radians(40))
        skin = 1.5 * (1 - fore) + 1.2 * fore - 0.2 * wrist
        fat = 6.0 * (1 - fore) + 4.0 * fore - 1.5 * wrist
        fat = fat * (1 - np.maximum(ulnar, olec)) + np.maximum(ulnar, olec) * 2.0
        mus = 35.0 * (1 - fore) + 20.0 * fore - 12.0 * wrist
        mus = mus * (1 - 0.8 * np.maximum(ulnar, olec))
        return skin, fat, mus
    if g == "hand":
        q = np.stack([ax - WRIST[0], y - WRIST[1], z - WRIST[2]], -1)
        palm = sstep(-0.004, 0.006, q @ HAND_N)
        return 1.2 + 1.3 * palm, 2.0 + 1.0 * palm, 3.0 + 5.0 * palm
    if g == "leg":
        zz, th = leg_local(ax, y, z)
        knee = gauss(zz - 0.495, 0.03) * gauss(wrap(th - np.radians(90)), np.radians(35))
        shin = band(zz, 0.10, 0.43, 0.02) * gauss(wrap(th - np.radians(120)), np.radians(28))
        ankle = sstep(0.16, 0.10, zz)
        calf = band(zz, 0.20, 0.45, 0.03)
        skin = np.where(zz > 0.52, 1.8, 1.5) * one
        fat = 9.0 * sstep(0.47, 0.56, zz) + 6.0 * calf * (1 - sstep(0.47, 0.56, zz))
        fat = np.maximum(fat, 2.0)
        lean = np.maximum(np.maximum(knee, shin), ankle)
        skin = skin * (1 - lean) + lean * 1.3
        fat = fat * (1 - lean) + lean * 1.7
        mus = 50.0 * sstep(0.47, 0.56, zz) + 35.0 * calf * (1 - sstep(0.47, 0.56, zz))
        mus = mus * (1 - lean)
        return skin, fat, mus
    if g == "foot":
        s, _w, h = foot_local(ax, y, z)
        sole = sstep(0.018, 0.006, h)
        heel = sstep(0.075, 0.050, s) * sole
        skin = 1.2 * (1 - sole) + 3.0 * sole
        fat = 1.8 * (1 - sole) + 8.0 * sole + 7.0 * heel
        mus = 5.0 * (1 - sole) + 10.0 * sole
        return skin, fat, mus
    raise KeyError(g)


def tissue_fields(x, y, z, comps=None):
    """Per point (skin_mm, fat_mm, muscle_mm) blended between tissue groups by distance.

    The fat map is scaled by body fat % / 15 [RB §7.6].  Continuous in 3-D, so it
    also drives the muscle-shell offset."""
    ax = np.abs(x)
    c = comps if comps is not None else body_components(x, y, z)
    gd = _group_distances(c)
    dmin = np.min(np.stack(list(gd.values())), axis=0)
    acc = [np.zeros_like(z) for _ in range(3)]
    wsum = np.zeros_like(z)
    for g, d in gd.items():
        w = np.exp(-np.minimum((d - dmin) / 0.010, 30.0))
        use = w > 1e-4
        if not use.any():
            continue
        vals = _tissue_group(g, ax[use], y[use], z[use])
        for k in range(3):
            acc[k][use] += w[use] * vals[k]
        wsum += np.where(use, w, 0.0)
    skin, fat, mus = (a / np.maximum(wsum, 1e-9) for a in acc)
    return skin, fat * FAT_SCALE, mus


def tissue_at(points):
    """(N, 3) body-frame points -> (N, 3) array of skin / fat / muscle thickness in mm."""
    p = np.asarray(points, float)
    out = np.zeros((len(p), 3))
    for s0 in range(0, len(p), 200000):
        q = p[s0:s0 + 200000]
        vals = tissue_fields(q[:, 0].copy(), q[:, 1].copy(), q[:, 2].copy())
        out[s0:s0 + 200000] = np.stack(vals, 1)
    return out


def _segment_axis(ax, y, z, group):
    """Long axis of the tissue group at the points (left side, |x|), for the tension lines."""
    n = len(z)
    if group in ("arm", "hand"):
        return np.broadcast_to(ARM_D, (n, 3)).copy()
    if group == "leg":
        return np.broadcast_to(LEG_W, (n, 3)).copy()
    if group == "foot":
        f = np.array([FOOT_F[0], FOOT_F[1], 0.0])
        return np.broadcast_to(f, (n, 3)).copy()
    return np.broadcast_to(np.array([0.0, 0.0, 1.0]), (n, 3)).copy()


def tension_at(points, normals):
    """Unit tangent of the skin tension (Langer) lines per point [RB §2.3.1].

    Trunk, neck and limbs: circumferential about the local long axis (a cut
    across this line gapes most, one along it least); on the lower abdomen the
    lines dip toward the pubis, on the chest they sag toward the sternum, on the
    back they rise slightly laterally (K).  Right side mirrored."""
    p = np.asarray(points, float)
    nrm = np.asarray(normals, float)
    x, y, z = p[:, 0].copy(), p[:, 1].copy(), p[:, 2].copy()
    ax = np.abs(x)
    sgn = np.where(x < 0, -1.0, 1.0)
    c = body_components(x, y, z)
    gd = _group_distances(c)
    names = list(gd.keys())
    g_idx = np.argmin(np.stack([gd[g] for g in names]), axis=0)
    axis = np.zeros((len(p), 3))
    for gi, g in enumerate(names):
        m = g_idx == gi
        if m.any():
            axis[m] = _segment_axis(ax[m], y[m], z[m], g)
    axis[:, 0] *= sgn                                  # mirror to the right side
    n_ = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    t = np.cross(axis, n_)
    bad = np.linalg.norm(t, axis=1) < 1e-3            # normal parallel to the axis (sole, top of shoulder)
    t[bad] = np.cross(np.array([1.0, 0.0, 0.0]), n_[bad])
    t /= np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)
    # regional tilt (rotate t about the normal)
    torso = np.array(names)[g_idx] == "torso"
    front = y < torso_centre_y(z)
    tilt = np.zeros(len(p))
    tilt += np.radians(-22.0) * (torso & front) * band(z, 0.90, 1.05, 0.04) * sstep(0.01, 0.06, ax)
    tilt += np.radians(-12.0) * (torso & front) * band(z, 1.22, 1.40, 0.03) * sstep(0.01, 0.05, ax)
    tilt += np.radians(10.0) * (torso & ~front) * band(z, 1.05, 1.45, 0.05) * sstep(0.01, 0.06, ax)
    tilt *= sgn * np.sign(t[:, 0] + 1e-9)             # keep the dip toward the midline on both sides
    b = np.cross(n_, t)
    t = np.cos(tilt)[:, None] * t + np.sin(tilt)[:, None] * b
    return t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)


# ===========================================================================
# Muscle shell SDF: skin offset inward by skin + fat (plan §8.2 B1, [RB §7.6])
# ===========================================================================
def _body_muscle(x, y, z):
    c = body_components(x, y, z)
    d = union_components(c)
    skin, fat, _m = tissue_fields(x, y, z, comps=c)
    return d + (skin + fat) * 1e-3


def _head_muscle(x, y, z):
    A = _A()
    h = A.muscle_sdf(x, y - HEAD_OFFSET[1], z - HEAD_OFFSET[2])
    return smax(h, head_clip_z(x, y) + 0.004 - z, 0.006)


def muscle_sdf(x, y, z):
    """Muscle shell SDF (negative inside): body skin inset by skin + fat, head part = gore_head muscle."""
    b = _body_muscle(x, y, z)
    h = HEAD_BOX.run(_head_muscle, x, y, z)
    return smin(b, h, 0.004 + 0.010 * sstep(1.52, 1.56, z))


# ===========================================================================
# Shorts SDF (plan D2, §1.2): loose mid-thigh athletic shorts, charcoal cotton jersey
# ===========================================================================
SHORTS_TOP, SHORTS_HEM, SHORTS_BAND = 1.045, 0.680, 0.035
SHORTS_GUSSET = 0.812
SHORTS_THICK = 0.0012


def _shorts_folds(ax, y, z):
    """Outward cloth relief (m): gathered waistband, hem band, groin diagonals, hanging leg folds."""
    cy = torso_centre_y(np.clip(z, 0.85, 1.1))
    ang = np.arctan2(-(y - cy), ax)
    band_w = band(z, SHORTS_TOP - SHORTS_BAND, SHORTS_TOP, 0.002)
    gather = 0.0007 * np.cos(ang * 42.0) * band_w + 0.0012 * band_w                 # elastic gathers
    under = -0.0010 * gauss(z - (SHORTS_TOP - SHORTS_BAND - 0.003), 0.003)           # stitch line under the band
    hem = 0.0008 * band(z, SHORTS_HEM, SHORTS_HEM + 0.022, 0.002) - 0.0006 * gauss(z - SHORTS_HEM - 0.024, 0.002)
    zz, th = leg_local(ax, y, z)
    legw = sstep(0.83, 0.74, z)
    drape = 0.0022 * legw * (0.6 + 0.4 * np.cos(3.0 * th + 0.8)) * np.cos(5.0 * th + 0.3 * np.sin(40 * z))
    # diagonal compression folds from the crotch toward the hips (front)
    diag = (ax * 0.9 + (z - 0.86) * 1.4)
    groin = 0.0014 * np.sin(diag / 0.022 * 2 * PI) * band(z, 0.83, 0.93, 0.02) * sstep(0.0, -0.04, y) \
        * band(ax, 0.03, 0.15, 0.02)
    seat = 0.0010 * np.sin((z - 0.80) / 0.03 * 2 * PI) * band(z, 0.78, 0.86, 0.02) * sstep(0.04, 0.09, y)
    return gather + under + hem + drape + groin + seat


def shorts_sdf(x, y, z):
    """Outer cloth surface of the shorts (negative inside); cut at the waistband and hem by the builder."""
    ax = np.abs(x)
    c = body_components(x, y, z)
    zc = np.maximum(z, 0.79)                         # below the upper thigh the leg openings hang straight
    leg = _leg_tube()(ax, y, zc)
    trunk = smin(c["torso"], c["glute"], 0.05)        # the cloth bridges the natal cleft and the creases
    base = smin(trunk, leg, 0.05)
    ease = np.interp(z, [0.68, 0.72, 0.80, 0.88, 0.95, 1.01, 1.045], [0.016, 0.014, 0.010, 0.008, 0.007, 0.005, 0.004])
    d = base - ease - _shorts_folds(ax, y, z)
    split = 0.004 - ax - 2.0 * np.maximum(z - SHORTS_GUSSET, 0.0)       # separate leg tubes below the gusset
    d = smax(d, split, 0.004)
    body = union_components(c)
    return np.minimum(d, body - 0.0032)              # never closer than 3.2 mm to the skin (outer surface)


# ===========================================================================
# Codes: segment / region / dermatome (plan §5.5)
# ===========================================================================
def _region_codes(p, seg, nrm):
    """Region code per point [RB §2.0]: 3 neck, 4 trunk front, 5 trunk back, 6 limb, 7 palm/sole."""
    from gb_data import segments as SG
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    out = np.full(len(p), SG.REGION_ID["limb"])
    torso = np.isin(seg, ["torso", "shorts"])
    front = y < torso_centre_y(z)
    out[torso & front] = SG.REGION_ID["trunk_front"]
    out[torso & ~front] = SG.REGION_ID["trunk_back"]
    neck = (seg == "head_neck") | (torso & (z > 1.462) & (ax < 0.085))
    out[neck] = SG.REGION_ID["neck"]
    hand = np.isin(seg, ["hand_L", "hand_R"])
    hn = np.stack([HAND_N[0] * np.sign(x + 1e-12), np.full(len(x), HAND_N[1]), np.full(len(x), HAND_N[2])], 1)
    palmar = (nrm * hn).sum(1) > 0.35
    out[hand & palmar] = SG.REGION_ID["palm_sole"]
    foot = np.isin(seg, ["foot_L", "foot_R"])
    out[foot & ((nrm[:, 2] < -0.45) | (z < 0.004))] = SG.REGION_ID["palm_sole"]
    return out


def _derm_codes(p, seg, nrm):
    """Dermatome code per point (plan §5.5 table; anchors R04 §6.2; boundaries K).

    Trunk: bands from the front/back level tables blended around the body
    (dermatomes run obliquely, lower in front); arm: C4 cap, C5 lateral arm, T1/T2
    medial arm, C6 radial forearm + thumb/index, C7 middle finger / dorsal
    forearm, C8 ulnar forearm and ring/little fingers; leg: L1 below the groin,
    L2/L3 front of the thigh, L4 medial shin + medial ankle, L5 lateral shin +
    dorsum, S1 heel / lateral foot / lower calf, S2 back of the thigh and
    popliteal area, S3 inner buttock, S4-5 perineum."""
    from gb_data import dermatomes as DM
    D = DM.DERMATOME_ID
    x, y, z = p[:, 0], p[:, 1], p[:, 2]
    ax = np.abs(x)
    out = np.zeros(len(p), dtype=int)
    torso = np.isin(seg, ["torso", "shorts", "head_neck"])
    if torso.any():
        zt, yt, at = z[torso], y[torso], ax[torso]
        fl = np.interp(zt, [t[0] for t in DM.TRUNK_FRONT_Z][::-1], [D[t[1]] for t in DM.TRUNK_FRONT_Z][::-1])
        bl = np.interp(zt, [t[0] for t in DM.TRUNK_BACK_Z][::-1], [D[t[1]] for t in DM.TRUNK_BACK_Z][::-1])
        _a, yf, yb, _nf, _nb = torso_station(zt)
        w = np.clip((yt - yf) / np.maximum(yb - yf, 1e-3), 0.0, 1.0)
        w = sstep(0.35, 0.75, w)
        code = np.rint((1 - w) * fl + w * bl).astype(int)
        code[zt > 1.445] = D["C4"]
        code[(zt > 1.47) & (at < 0.075)] = D["C3"]
        per = (zt < 0.905) & (at < 0.035) & (np.abs(yt - 0.01) < 0.05)
        code[(zt < 0.96) & (w > 0.5) & (at < 0.08)] = D["S3"]
        code[per] = D["S4-5"]
        out[torso] = code
    arm = np.isin(seg, ["arm_L", "arm_R", "hand_L", "hand_R"])
    if arm.any():
        s, th = arm_local(ax[arm], y[arm], z[arm])
        thd = np.degrees(th)
        code = np.full(arm.sum(), D["C5"])
        code[s < 0.0] = D["C4"]
        med = (np.abs(thd) >= 100) & (s >= 0.0) & (s < 0.28)
        code[med & (s < 0.12)] = D["T2"]
        code[med & (s >= 0.12)] = D["T1"]
        fore = (s >= 0.28) & (s < S_WRIST - 0.005)
        code[fore & (thd >= 30) & (thd < 150)] = D["C6"]
        code[fore & (thd >= -40) & (thd < 30)] = D["C7"]
        code[fore & (thd < -40) & (thd >= -150)] = D["C8"]
        palm = fore & (np.abs(thd) >= 150)
        code[palm & (s < 0.40)] = D["T1"]
        code[palm & (s >= 0.40) & (thd < 0)] = D["C8"]
        code[palm & (s >= 0.40) & (thd >= 0)] = D["C6"]
        hand = s >= S_WRIST - 0.005
        q = np.stack([ax[arm] - WRIST[0], y[arm] - WRIST[1], z[arm] - WRIST[2]], -1)
        r = q @ HAND_F
        code[hand & (r > 0.016)] = D["C6"]
        code[hand & (r <= 0.016) & (r > -0.004)] = D["C7"]
        code[hand & (r <= -0.004)] = D["C8"]
        out[arm] = code
    leg = np.isin(seg, ["leg_L", "leg_R", "foot_L", "foot_R"])
    if leg.any():
        zz, th = leg_local(ax[leg], y[leg], z[leg])
        thd = np.degrees(th)
        ant = np.abs(thd - 90) < 75
        post = (thd < -20) & (thd > -160)
        medial = (np.abs(thd) >= 125)
        code = np.full(leg.sum(), D["L3"])
        code[(zz > 0.80) & ~post] = D["L1"]
        code[(zz > 0.64) & (zz <= 0.80) & ant] = D["L2"]
        code[(zz > 0.64) & (zz <= 0.80) & medial] = D["L3"]
        code[(zz > 0.44) & (zz <= 0.64) & ~post] = D["L3"]
        code[(zz > 0.44) & post] = D["S2"]
        shin = (zz > 0.10) & (zz <= 0.44)
        code[shin & ((thd >= 100) | (thd <= -160))] = D["L4"]
        code[shin & (thd >= -20) & (thd < 100)] = D["L5"]
        code[shin & post & (zz > 0.30)] = D["S2"]
        code[shin & post & (zz <= 0.30)] = D["S1"]
        foot = zz <= 0.10
        s, w, h = foot_local(ax[leg], y[leg], z[leg])
        fcode = np.full(leg.sum(), D["L5"])
        fcode[w < -0.024] = D["L4"]                           # medial border, medial malleolus, hallux side
        fcode[w > 0.030] = D["S1"]                            # lateral border, little toe
        fcode[s < 0.075] = D["S1"]                            # heel
        sole = nrm[leg][:, 2] < -0.45
        fcode[sole & (w <= 0.0)] = D["L5"]
        fcode[sole & (w > 0.0)] = D["S1"]
        fcode[sole & (s < 0.075)] = D["S1"]
        code[foot] = fcode[foot]
        out[leg] = code
    return out


def vertex_normals(obj):
    me = obj.data
    n = np.empty(len(me.vertices) * 3, np.float32)
    try:
        me.vertex_normals.foreach_get("vector", n)
    except AttributeError:
        me.vertices.foreach_get("normal", n)
    return n.reshape(-1, 3).astype(float)


def paint_codes(obj, code_segment=None, body_segment=None):
    """Write gb_seg / gb_region / gb_derm and the ``gb_codes`` UV (plan §5.5) on a skin-like mesh.

    ``code_segment`` forces the written segment (``'shorts'``); ``body_segment``
    forces the anatomical segment used for regions and dermatomes.  Head-segment
    vertices (the neck under the seam, or the head part of the muscle shell) use
    the placeholder's head region rules (face / scalp / eyelid-lip) so B2's head
    and this body agree.  Returns the per-vertex anatomical segment names."""
    import placeholder
    from gb_data import segments as SG
    v = gbc.get_verts(obj.data)
    nrm = vertex_normals(obj)
    under = placeholder.segment_names_for(v, body_segment)
    region = _region_codes(v, under, nrm)
    derm = _derm_codes(v, under, nrm)
    head = (under == "head_neck") & (v[:, 2] > 1.50)
    if head.any():
        region[head] = placeholder.skin_regions(v[head], under[head])
        from gb_data import dermatomes as DM
        derm[head] = DM.dermatome_v0(v[head], under[head])
    names = np.array([code_segment] * len(v)) if code_segment else under
    seg = np.array([SG.SEGMENT_ID[n] for n in names])
    gbc.point_attr(obj, "gb_seg", seg, 'INT')
    gbc.point_attr(obj, "gb_region", region, 'INT')
    gbc.point_attr(obj, "gb_derm", derm, 'INT')
    gbc.set_codes_uv(obj, seg + SG.REGION_STRIDE * region, derm)
    return under


# ===========================================================================
# Builders
# ===========================================================================
RES = {
    "quick": dict(master=0.0050, muscle=0.0085, shorts=0.0060),
    "full": dict(master=0.0025, muscle=0.0050, shorts=0.0040),
}
BODY_TRIS = 43600                 # plan §4.1: 44,000 incl. the zip strip (TRI_BUDGET GB_Body)
BODY_LOD1_TRIS = 21800
MUSCLE_TRIS = 23800
SHORTS_OUTER_TRIS = 1880          # x2 by the solidify + rims -> ~4,000 (plan §4.1)
ATLAS_PX = 2048
ATLAS_MARGIN_PX = 16
NECK_UV_SCALE = 2.0               # plan §8.2 B1: soften the texel jump at the neck seam


def _quick(quick):
    return ("--quick" in gbc.script_args()) if quick is None else bool(quick)


def _res(quick):
    return RES["quick" if _quick(quick) else "full"]


def _edge_faces(me):
    """(face_a, face_b) per edge (-1 where missing)."""
    ne = len(me.edges)
    le = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("edge_index", le)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    lp = np.repeat(np.arange(len(me.polygons)), lt)
    order = np.argsort(le, kind="stable")
    le_s, lp_s = le[order], lp[order]
    starts = np.searchsorted(le_s, np.arange(ne))
    counts = np.bincount(le_s, minlength=ne)
    fa = np.full(ne, -1)
    fb = np.full(ne, -1)
    fa[counts >= 1] = lp_s[starts[counts >= 1]]
    fb[counts >= 2] = lp_s[starts[counts >= 2] + 1]
    return fa, fb


def face_normals(me):
    n = np.empty(len(me.polygons) * 3, np.float32)
    me.polygons.foreach_get("normal", n)
    return n.reshape(-1, 3).astype(float)


def face_areas(me):
    a = np.empty(len(me.polygons), np.float32)
    me.polygons.foreach_get("area", a)
    return a.astype(float)


def _smooth_labels(fa, fb, labels, nf, iters=4):
    """Majority filter: a face whose neighbours mostly carry another label takes it (straight seams)."""
    labels = labels.copy()
    L = int(labels.max()) + 1
    for _ in range(iters):
        votes = np.zeros((nf, L), np.int32)
        np.add.at(votes, (fa, labels[fb]), 1)
        np.add.at(votes, (fb, labels[fa]), 1)
        best = votes.argmax(1)
        strong = votes[np.arange(nf), best] >= 2
        new = np.where(strong & (votes[np.arange(nf), labels] <= 1), best, labels)
        if np.array_equal(new, labels):
            break
        labels = new
    return labels


def _cleanup_labels(me, labels, min_faces=40, iters=6):
    """Straighten label borders and merge tiny label islands into a neighbour (clean UV islands)."""
    fa, fb = _edge_faces(me)
    ok = (fa >= 0) & (fb >= 0)
    fa, fb = fa[ok], fb[ok]
    labels = _smooth_labels(fa, fb, labels, len(me.polygons))
    for _ in range(iters):
        # connected components of equal labels by label propagation
        comp = np.arange(len(labels))
        same = labels[fa] == labels[fb]
        a, b = fa[same], fb[same]
        for _k in range(400):
            m = np.minimum(comp[a], comp[b])
            new = comp.copy()
            np.minimum.at(new, a, m)
            np.minimum.at(new, b, m)
            new = new[new]
            if np.array_equal(new, comp):
                break
            comp = new
        size = np.bincount(comp, minlength=len(labels))[comp]
        small = size < min_faces
        if not small.any():
            break
        # vote from neighbours that are not small
        diff = labels[fa] != labels[fb]
        changed = False
        for f, g in ((fa, fb), (fb, fa)):
            m = diff & small[f] & ~small[g]
            if m.any():
                labels[f[m]] = labels[g[m]]
                changed = True
        if not changed:
            break
    return labels


ISLANDS = ["torso_front", "torso_back", "neck", "arm_L", "arm_R", "palm_L", "palm_R", "dorsum_L", "dorsum_R",
           "leg_L", "leg_R", "foot_top_L", "foot_top_R", "sole_L", "sole_R"]
ISL = {n: i for i, n in enumerate(ISLANDS)}


def uv_islands(me):
    """Per-face UV island label on the body skin (planned seams, plan §8.2 B1).

    Islands follow anatomy: arm vs trunk along the axillary / deltoid crease,
    leg vs trunk along the inguinal crease and gluteal fold, wrist and ankle
    rings, palm vs dorsum along the hand borders, sole vs dorsum along the sole
    edge, trunk front vs back along the lateral lines, and a lower-neck band."""
    c = gbc.face_centres(me)
    n = face_normals(me)
    x, y, z = c[:, 0].copy(), c[:, 1].copy(), c[:, 2].copy()
    ax = np.abs(x)
    L = x >= 0
    comps = body_components(x, y, z)
    gd = _group_distances(comps)
    trunk = np.minimum(gd["torso"], gd["glute"])
    armg = np.minimum(gd["arm"], gd["hand"])
    legg = np.minimum(gd["leg"], gd["foot"])
    lab = np.where(y < torso_centre_y(z), ISL["torso_front"], ISL["torso_back"])
    neck = (z > 1.460 + 0.12 * (y + 0.05)) & (ax < 0.10)
    lab[neck] = ISL["neck"]
    s_arm, _th = arm_local(ax, y, z)
    is_arm = (armg < trunk) & (armg < legg) & (s_arm > -0.03)
    hand = is_arm & (s_arm > S_WRIST - 0.004)
    hn = np.stack([HAND_N[0] * np.where(L, 1, -1), np.full(len(x), HAND_N[1]), np.full(len(x), HAND_N[2])], 1)
    palmar = (n * hn).sum(1) > 0.0
    lab[is_arm & ~hand] = np.where(L, ISL["arm_L"], ISL["arm_R"])[is_arm & ~hand]
    lab[hand & palmar] = np.where(L, ISL["palm_L"], ISL["palm_R"])[hand & palmar]
    lab[hand & ~palmar] = np.where(L, ISL["dorsum_L"], ISL["dorsum_R"])[hand & ~palmar]
    is_leg = (legg < trunk) & ~is_arm
    zz = z
    foot = is_leg & (zz < 0.105 - 0.25 * np.maximum(y - 0.06, 0.0))
    sole = foot & ((n[:, 2] < -0.45) | (z < 0.0035))
    lab[is_leg & ~foot] = np.where(L, ISL["leg_L"], ISL["leg_R"])[is_leg & ~foot]
    lab[foot & ~sole] = np.where(L, ISL["foot_top_L"], ISL["foot_top_R"])[foot & ~sole]
    lab[sole] = np.where(L, ISL["sole_L"], ISL["sole_R"])[sole]
    return _cleanup_labels(me, lab)


def _cut_edges(me, labels):
    """Seams inside an island that would otherwise be a closed tube (inner arm, inner leg, neck back, heel)."""
    c = gbc.face_centres(me)
    x, y, z = c[:, 0], c[:, 1], c[:, 2]
    ax = np.abs(x)
    ang = np.zeros(len(c))
    cut_at = np.full(len(c), np.nan)
    arm = np.isin(labels, [ISL["arm_L"], ISL["arm_R"]])
    _s, th = arm_local(ax, y, z)
    ang[arm], cut_at[arm] = th[arm], PI                    # inner (medial) arm line
    leg = np.isin(labels, [ISL["leg_L"], ISL["leg_R"]])
    _z, thl = leg_local(ax, y, z)
    ang[leg], cut_at[leg] = thl[leg], PI                   # inner leg line
    ft = np.isin(labels, [ISL["foot_top_L"], ISL["foot_top_R"]])
    s_f, w_f, _h = foot_local(ax, y, z)
    angf = np.arctan2(s_f - 0.03, w_f)                     # about a vertical line near the heel
    ang[ft], cut_at[ft] = angf[ft], -PI / 2                # heel back
    nk = labels == ISL["neck"]
    angn = np.arctan2(x, -(y - 0.01))
    ang[nk], cut_at[nk] = angn[nk], PI                     # back of the neck
    fa, fb = _edge_faces(me)
    ok = (fa >= 0) & (fb >= 0)
    cut = np.zeros(len(fa), bool)
    f1, f2 = fa[ok], fb[ok]
    same = labels[f1] == labels[f2]
    has = ~np.isnan(cut_at[f1])
    p1 = wrap(ang[f1] - np.nan_to_num(cut_at[f1]))
    p2 = wrap(ang[f2] - np.nan_to_num(cut_at[f1]))
    straddle = (np.sign(p1) != np.sign(p2)) & (np.abs(p1) < 1.2) & (np.abs(p2) < 1.2)
    idx = np.nonzero(ok)[0]
    cut[idx[same & has & straddle]] = True
    return cut


def body_uvs(obj, labels):
    """Mark planned seams, unwrap (MINIMUM_STRETCH), equalise texel density, neck x2, pack 16 px."""
    import bpy
    import uv as UV
    me = obj.data
    fa, fb = _edge_faces(me)
    seam = np.zeros(len(fa), bool)
    ok = (fa >= 0) & (fb >= 0)
    seam[ok] = labels[fa[ok]] != labels[fb[ok]]
    seam |= _cut_edges(me, labels)
    me.edges.foreach_set("use_seam", seam)
    me.update()
    UV.unwrap(obj, "MINIMUM_STRETCH", margin=0.001)
    # per island: scale UVs so every island has the same texel density (neck island x2)
    lay = me.uv_layers["atlas"]
    uv = np.empty(len(me.loops) * 2, np.float32)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(float)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    ls = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lf = np.repeat(np.arange(len(me.polygons)), lt)
    a3 = face_areas(me)
    auv = _uv_face_areas(uv, ls, lt)
    for lab in np.unique(labels):
        fm = labels == lab
        s = math.sqrt(a3[fm].sum() / max(auv[fm].sum(), 1e-12))
        if lab == ISL["neck"]:
            s *= NECK_UV_SCALE
        lm = fm[lf]
        cen = uv[lm].mean(0)
        uv[lm] = cen + (uv[lm] - cen) * s
    lay.data.foreach_set("uv", uv.astype(np.float32).ravel())
    me.update()
    UV.pack(obj, ATLAS_PX, ATLAS_MARGIN_PX)
    return int(seam.sum())


def _uv_face_areas(uv, ls, lt):
    """UV area per polygon (fan triangulation)."""
    out = np.zeros(len(ls))
    for k in range(3, int(lt.max()) + 1):
        m = lt >= k
        a = uv[ls[m]]
        b = uv[ls[m] + k - 2]
        c = uv[ls[m] + k - 1]
        out[m] += 0.5 * np.abs((b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (c[:, 0] - a[:, 0]) * (b[:, 1] - a[:, 1]))
    return out


def texel_density_mm(obj, exclude_labels=None, labels=None, px=ATLAS_PX):
    """Median-free global texel size (mm per texel) of the ``atlas`` UV at ``px``."""
    me = obj.data
    lay = me.uv_layers["atlas"]
    uv = np.empty(len(me.loops) * 2, np.float32)
    lay.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(float)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    ls = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    a3 = face_areas(me)
    auv = _uv_face_areas(uv, ls, lt)
    m = np.ones(len(a3), bool)
    if exclude_labels is not None and labels is not None:
        m &= ~np.isin(labels, exclude_labels)
    return 1000.0 * math.sqrt(a3[m].sum() / max(auv[m].sum() * px * px, 1e-18))


def body_shape_fields(v):
    """GB_Body shape keys (plan §5.6): chest_inhale, belly_distension, thigh_swell_L/R (displacements, m)."""
    v = np.asarray(v, float)
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    ax = np.abs(x)
    cy = torso_centre_y(z)
    trunk = sstep(0.20, 0.17, ax)
    out = {}
    # quiet inspiration: rib cage out and up ~7 mm at the lower chest [RB §4 respiration] E
    w = trunk * band(z, 1.20, 1.42, 0.05)
    rad = np.stack([x, y - cy, np.zeros_like(x)], 1)
    rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-6)
    out["chest_inhale"] = (0.007 * w)[:, None] * rad + (0.003 * w)[:, None] * np.array([[0, 0, 1.0]])
    # belly distension (haemoperitoneum): anterior abdomen out up to 25 mm E
    w = trunk * sstep(cy + 0.01, cy - 0.03, y) * band(z, 0.96, 1.22, 0.05) * sstep(0.16, 0.08, ax)
    out["belly_distension"] = (0.025 * w)[:, None] * np.array([[0.0, -1.0, 0.0]])
    for side, sx in (("L", 1.0), ("R", -1.0)):
        P = leg_axis_at_z(z)
        rel = np.stack([x - sx * P[:, 0], y - P[:, 1], np.zeros_like(x)], 1)
        dist = np.linalg.norm(rel, axis=1)
        w = (x * sx > 0.0) * band(z, 0.56, 0.86, 0.05) * sstep(0.13, 0.10, dist)
        out["thigh_swell_" + side] = (0.008 * w / np.maximum(dist, 1e-6))[:, None] * rel
    return out


def _new_mesh_object(name, me):
    obj = gbc.new_object(name, me)
    obj.data.shade_smooth()
    return obj


def _tag(obj, status="built (B1)"):
    import placeholder
    placeholder.tag(obj)
    obj["gb_status"] = status


def _largest_piece(me):
    """Keep only the largest connected piece (label propagation run to convergence).

    The head toolkit's ``remove_small_islands`` caps propagation at 200 passes; on
    a long thin chain (shoulder -> fingertip) that leaves the fingertip with its
    own label and deletes it, opening a hole.  This version never stops early."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.verts.ensure_lookup_table()
    seen = np.zeros(len(bm.verts), bool)
    pieces = []
    for v0 in bm.verts:
        if seen[v0.index]:
            continue
        stack, comp = [v0], []
        seen[v0.index] = True
        while stack:
            v = stack.pop()
            comp.append(v)
            for e in v.link_edges:
                o = e.other_vert(v)
                if not seen[o.index]:
                    seen[o.index] = True
                    stack.append(o)
        pieces.append(comp)
    pieces.sort(key=len, reverse=True)
    removed = sum(len(p) for p in pieces[1:])
    if removed:
        bmesh.ops.delete(bm, geom=[v for p in pieces[1:] for v in p], context='VERTS')
        bm.to_mesh(me)
        me.update()
    bm.free()
    return removed


def _sdf_object(name, fn, lo, hi, h, project=3):
    """SDF -> surface nets -> voxel remesh -> keep the largest piece -> Newton projection."""
    A = _A()
    import bpy
    tmp = A.mesh_sdf("_b1_tmp", fn, lo, hi, h, voxel=h, project=0, clean=False,
                     collection=bpy.context.scene.collection)
    me = tmp.data
    bpy.data.objects.remove(tmp, do_unlink=True)
    _largest_piece(me)
    v = A.project_to_surface(fn, gbc.get_verts(me), h, project)
    gbc.set_verts(me, v)
    me.name = name
    return _new_mesh_object(name, me)


def cut_neck(me, z, radius=0.095, centre_xy=(0.0, 0.012)):
    """Bisect the mesh at the plane ``z`` inside the neck cylinder only and delete what lies above it there
    (the shoulders never lose geometry even if something rises above the seam plane)."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(me)
    cx, cy = centre_xy

    def inside(co):
        return (co.x - cx) ** 2 + (co.y - cy) ** 2 < radius * radius
    geom = [f for f in bm.faces if any(inside(v.co) for v in f.verts)]
    edges = list({e for f in geom for e in f.edges})
    verts = list({v for f in geom for v in f.verts})
    bmesh.ops.bisect_plane(bm, geom=verts + edges + geom, dist=1e-7, plane_co=(0.0, 0.0, z),
                           plane_no=(0.0, 0.0, 1.0))
    kill = [f for f in bm.faces if f.calc_center_median().z > z and inside(f.calc_center_median())]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    bmesh.ops.delete(bm, geom=loose, context='VERTS')
    bm.to_mesh(me)
    bm.free()
    me.update()
    return me


def _cut_and_zip(obj, ring, gap):
    """Cut ``gap`` below the seam plane (neck only) and zip the open neck to the canonical ring (plan D19)."""
    import head_integration as hi
    cut_neck(obj.data, SEAM_Z - gap)
    return hi.zip_to_ring(obj, ring, side="below")


def _material_by_segment(obj, prefix, surf_map):
    import placeholder
    from gb_data import segments as SG
    placeholder.face_slots_by_segment(obj, list(gbc.MATERIAL_SLOTS[obj.name]),
                                      lambda n: prefix + surf_map.get(n, SG.SEGMENT_SURFACE[n]))


def _write_tissue_attrs(obj):
    v = gbc.get_verts(obj.data)
    t = tissue_at(v)
    gbc.point_attr(obj, "gb_skin_mm", t[:, 0], 'FLOAT')
    gbc.point_attr(obj, "gb_fat_mm", t[:, 1], 'FLOAT')
    gbc.point_attr(obj, "gb_muscle_mm", t[:, 2], 'FLOAT')
    tan = tension_at(v, vertex_normals(obj))
    for i, a in enumerate("xyz"):
        gbc.point_attr(obj, f"gb_tension_{a}", tan[:, i], 'FLOAT')
    return t, tan


def _protect_ring_decimate(obj, target_tris):
    """Collapse-decimate keeping the boundary (seam ring) vertices exactly (vertex group weight 0)."""
    import bpy
    import gb_geom as gg
    me = obj.data
    loops = gg.boundary_loops(me)
    vg = obj.vertex_groups.new(name="gb_decimate")
    allv = list(range(len(me.vertices)))
    vg.add(allv, 1.0, 'REPLACE')
    ring = [i for lp in loops for i in lp]
    if ring:
        vg.add(ring, 0.0, 'REPLACE')
    n = gbc.tri_count(me)
    mod = obj.modifiers.new("gb_decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.01, target_tris / max(n, 1))
    mod.use_collapse_triangulate = True
    mod.vertex_group = "gb_decimate"
    mod.vertex_group_factor = 1000.0
    gg.apply_modifier(obj, mod)
    obj.vertex_groups.remove(obj.vertex_groups["gb_decimate"])
    gg.remove_loose(obj.data)
    obj.data.shade_smooth()
    return gbc.tri_count(obj.data)


def build_body_skin(quick=None):
    """GB_Body (LOD0, 44k tris, 5 surfaces), GB_Body_HR (bake source) and GB_Body_LOD1.

    master SDF mesh at h 2.5 mm (quick 5 mm) -> HR; copy -> collapse decimate to
    the budget -> cut at the seam plane and zip to the canonical ring shared with
    GB_Head -> planned UV seams, unwrap, pack -> codes, tissue/tension attributes,
    material surfaces, shape keys.  LOD1 is decimated from LOD0 with the ring and
    UVs kept."""
    import gb_geom as gg
    T = gbc.Timer
    r = _res(quick)
    h = r["master"]
    ring = gbc.seam_ring()
    with T("B1: master skin SDF mesh"):
        hr = _sdf_object("GB_Body_HR", skin_sdf, (-0.60, -0.20, -0.004), (0.60, 0.20, SEAM_Z + 4 * h), h)
    with T("B1: LOD0 decimate + seam zip"):
        body = _new_mesh_object("GB_Body", hr.data.copy())
        gg.decimate_to(body, BODY_TRIS - 2 * len(ring))
        _cut_and_zip(body, ring, 0.0030)
        _cut_and_zip(hr, ring, 0.5 * h)
    with T("B1: UV islands, seams, unwrap, pack"):
        labels = uv_islands(body.data)
        body_uvs(body, labels)
        body["gb_texel_mm"] = round(texel_density_mm(body, [ISL["neck"]], labels), 4)
        gbc.point_attr(body, "gb_uv_island", _face_to_vertex(body.data, labels), 'INT')
    with T("B1: codes, tissue + tension attributes, surfaces"):
        paint_codes(body)
        _write_tissue_attrs(body)
        gbc.set_material_slots(body)
        _material_by_segment(body, "GBM_skin_", {"head_neck": "torso", "shorts": "torso"})
        paint_codes(hr)
    with T("B1: shape keys + LOD1"):
        lod = _new_mesh_object("GB_Body_LOD1", body.data.copy())
        _protect_ring_decimate(lod, BODY_LOD1_TRIS)
        paint_codes(lod)
        gbc.set_material_slots(lod)
        _material_by_segment(lod, "GBM_skin_", {"head_neck": "torso", "shorts": "torso"})
        import placeholder
        placeholder.add_shape_keys(body, body_shape_fields(gbc.get_verts(body.data)), gbc.SHAPE_KEYS["GB_Body"])
    for o in (body, lod, hr):
        import placeholder
        placeholder.finish_uvs(o)
        _tag(o)
    hr.data.materials.clear()
    hr.data.materials.append(gbc.placeholder_material("GBM_skin_torso"))
    with T("B1: tissue-depth + tension maps (512^2)"):
        bake_body_maps(body, os.path.join(gbc.SUBJECT_OUT, "textures"))
    return {"GB_Body": body, "GB_Body_HR": hr, "GB_Body_LOD1": lod}


def _face_to_vertex(me, face_vals):
    """Per-vertex value from per-face labels (last writer wins; used for debugging/verification)."""
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    out = np.zeros(len(me.vertices), np.int32)
    out[lv] = np.repeat(np.asarray(face_vals), lt)
    return out


def build_shorts(skin=None, quick=None):
    """GB_Shorts: loose charcoal mid-thigh shorts as a real 1.2 mm cloth shell (plan D2, §1.2)."""
    import gb_geom as gg
    import uv as UV
    T = gbc.Timer
    h = _res(quick)["shorts"]
    with T("B1: shorts SDF mesh"):
        obj = _sdf_object("GB_Shorts", shorts_sdf, (-0.27, -0.20, SHORTS_HEM - 0.02), (0.27, 0.22, SHORTS_TOP + 0.02), h)
        gg.cut_plane(obj.data, SHORTS_TOP, keep="below")
        gg.cut_plane(obj.data, SHORTS_HEM, keep="above")
        gg.remove_loose(obj.data)
        gg.decimate_to(obj, SHORTS_OUTER_TRIS)
    with T("B1: shorts solidify + UV"):
        mod = obj.modifiers.new("gb_solidify", 'SOLIDIFY')
        mod.thickness = SHORTS_THICK
        mod.offset = -1.0
        mod.use_even_offset = True
        mod.use_rim = True
        gg.apply_modifier(obj, mod)
        obj.data.shade_smooth()
        me = obj.data
        c = gbc.face_centres(me)
        dc = gg.eval_sdf(shorts_sdf, c)
        outer = dc > -0.5 * SHORTS_THICK
        cy = np.where(c[:, 2] > 0.85, torso_centre_y(np.clip(c[:, 2], 0.85, 1.1)), leg_axis_at_z(c[:, 2])[:, 1])
        front = c[:, 1] < cy
        lab = outer * 2 + front
        fa, fb = _edge_faces(me)
        ok = (fa >= 0) & (fb >= 0)
        seam = np.zeros(len(fa), bool)
        seam[ok] = lab[fa[ok]] != lab[fb[ok]]
        me.edges.foreach_set("use_seam", seam)
        UV.unwrap(obj, "MINIMUM_STRETCH", margin=0.001)
        UV.pack(obj, 1024, 8)
    with T("B1: shorts codes"):
        paint_codes(obj, code_segment="shorts")
        gbc.set_material_slots(obj)
        import placeholder
        placeholder.finish_uvs(obj)
        _tag(obj)
    return {"GB_Shorts": obj}


def build_muscle_shell(skin=None, quick=None):
    """GB_MuscleShell: closed shell at skin + fat depth [RB §7.6], 24k tris, 6 surfaces."""
    import gb_geom as gg
    T = gbc.Timer
    h = _res(quick)["muscle"]
    with T("B1: muscle shell SDF mesh"):
        obj = _sdf_object("GB_MuscleShell", muscle_sdf, (-0.60, -0.20, -0.004), (0.60, 0.20, 1.80), h)
        gg.decimate_to(obj, MUSCLE_TRIS)
    with T("B1: muscle shell codes + surfaces + UV"):
        paint_codes(obj)
        gbc.set_material_slots(obj)
        _material_by_segment(obj, "GBM_muscle_", {"head_neck": "head", "shorts": "torso"})
        gg.smart_uv(obj, margin=0.003)
        import placeholder
        placeholder.finish_uvs(obj)
        _tag(obj)
    return {"GB_MuscleShell": obj}


# ===========================================================================
# Painter input maps baked by B1 (plan §3.3.4, §8.2 B1): tissue depth + tension, 512^2, atlas UV
# ===========================================================================
MAP_SIZE = 512
TISSUE_MAP = "body_tissue_depth.png"
TENSION_MAP = "body_tension.png"
MAPS_JSON = "body_maps.json"
TISSUE_SCALE_MM = (8.0, 40.0, 80.0)        # R skin, G fat, B muscle: value/255 * scale = mm


def _raster(obj, per_loop, size, channels):
    """Rasterise per-loop values (fan-triangulated polygons) into a (size, size, C) float image
    in the ``atlas`` UV space; returns (image, coverage mask).  Pure numpy, deterministic."""
    me = obj.data
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["atlas"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(float) * size - 0.5
    ls = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    img = np.zeros((size, size, channels))
    cov = np.zeros((size, size), bool)
    tris = [(ls[m], ls[m] + k - 1, ls[m] + k) for k in range(2, int(lt.max()))
            for m in [np.nonzero(lt > k)[0]]]
    ia = np.concatenate([t[0] for t in tris])
    ib = np.concatenate([t[1] for t in tris])
    ic = np.concatenate([t[2] for t in tris])
    for a, b, c in zip(ia, ib, ic):
        pa, pb, pc = uv[a], uv[b], uv[c]
        x0 = max(int(np.floor(min(pa[0], pb[0], pc[0]))), 0)
        x1 = min(int(np.ceil(max(pa[0], pb[0], pc[0]))), size - 1)
        y0 = max(int(np.floor(min(pa[1], pb[1], pc[1]))), 0)
        y1 = min(int(np.ceil(max(pa[1], pb[1], pc[1]))), size - 1)
        if x1 < x0 or y1 < y0:
            continue
        X, Y = np.meshgrid(np.arange(x0, x1 + 1), np.arange(y0, y1 + 1))
        den = (pb[1] - pc[1]) * (pa[0] - pc[0]) + (pc[0] - pb[0]) * (pa[1] - pc[1])
        if abs(den) < 1e-12:
            continue
        l1 = ((pb[1] - pc[1]) * (X - pc[0]) + (pc[0] - pb[0]) * (Y - pc[1])) / den
        l2 = ((pc[1] - pa[1]) * (X - pc[0]) + (pa[0] - pc[0]) * (Y - pc[1])) / den
        l3 = 1.0 - l1 - l2
        m = (l1 >= -1e-6) & (l2 >= -1e-6) & (l3 >= -1e-6)
        if not m.any():
            continue
        val = l1[m, None] * per_loop[a] + l2[m, None] * per_loop[b] + l3[m, None] * per_loop[c]
        img[Y[m], X[m]] = val
        cov[Y[m], X[m]] = True
    return img, cov


def _dilate(img, cov, px):
    """Grow the covered texels ``px`` times into empty neighbours (no black bleeding at island borders)."""
    img, cov = img.copy(), cov.copy()
    for _ in range(px):
        acc = np.zeros_like(img)
        cnt = np.zeros(cov.shape)
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            sc = np.roll(cov, (dy, dx), (0, 1))
            acc += np.roll(img, (dy, dx), (0, 1)) * sc[..., None]
            cnt += sc
        new = ~cov & (cnt > 0)
        img[new] = acc[new] / cnt[new][:, None]
        cov |= new
    return img, cov


def _loop_values(obj, per_vertex):
    me = obj.data
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    return np.asarray(per_vertex, float)[lv]


def _uv_tangent_dirs(obj, t3):
    """Per-loop 2-D UV-space unit direction of the 3-D tangent vectors ``t3`` (per vertex)."""
    me = obj.data
    v = gbc.get_verts(me)
    lv = np.empty(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", lv)
    uv = np.empty(len(me.loops) * 2, np.float32)
    me.uv_layers["atlas"].data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2).astype(float)
    ls = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_start", ls)
    lt = np.empty(len(me.polygons), np.int64)
    me.polygons.foreach_get("loop_total", lt)
    out = np.zeros((len(me.loops), 2))
    # per polygon Jacobian from its first triangle: P = P0 + Pu du + Pv dv
    a, b, c = ls, ls + 1, ls + 2
    e1, e2 = v[lv[b]] - v[lv[a]], v[lv[c]] - v[lv[a]]
    d1, d2 = uv[b] - uv[a], uv[c] - uv[a]
    det = d1[:, 0] * d2[:, 1] - d2[:, 0] * d1[:, 1]
    det = np.where(np.abs(det) < 1e-14, 1e-14, det)
    Pu = (e1 * d2[:, 1:2] - e2 * d1[:, 1:2]) / det[:, None]
    Pv = (e2 * d1[:, 0:1] - e1 * d2[:, 0:1]) / det[:, None]
    lf = np.repeat(np.arange(len(ls)), lt)
    t = t3[lv]
    # solve t ~ a Pu + b Pv (least squares, 2x2 normal equations)
    A11 = (Pu[lf] * Pu[lf]).sum(1)
    A12 = (Pu[lf] * Pv[lf]).sum(1)
    A22 = (Pv[lf] * Pv[lf]).sum(1)
    r1 = (t * Pu[lf]).sum(1)
    r2 = (t * Pv[lf]).sum(1)
    dd = A11 * A22 - A12 * A12
    dd = np.where(np.abs(dd) < 1e-20, 1e-20, dd)
    out[:, 0] = (r1 * A22 - r2 * A12) / dd
    out[:, 1] = (r2 * A11 - r1 * A12) / dd
    n = np.maximum(np.linalg.norm(out, axis=1, keepdims=True), 1e-12)
    return out / n


def bake_body_maps(obj, out_dir, size=MAP_SIZE):
    """Bake the tissue-depth and tension maps of GB_Body into ``out_dir`` (lossless 8-bit PNG + JSON).

    * ``body_tissue_depth.png``: R skin, G fat, B muscle thickness (mm = value / 255 x (8, 40, 80)),
      A = coverage (255 inside an island, dilated 4 px).
    * ``body_tension.png``: RG = unit direction of the Langer line in atlas UV space
      (u = R / 127.5 - 1, v = G / 127.5 - 1; the sign is irrelevant, lines are axial),
      B = anisotropy weight (255 = fully directional), A = coverage.
    Rows are written top to bottom (v = 1 at the top), like Godot's image origin."""
    import json
    t = np.stack([gbc.read_point_attr(obj, f"gb_{k}_mm", 'FLOAT') for k in ("skin", "fat", "muscle")], 1)
    t3 = np.stack([gbc.read_point_attr(obj, f"gb_tension_{a}", 'FLOAT') for a in "xyz"], 1)
    img_t, cov = _raster(obj, _loop_values(obj, t), size, 3)
    img_t, cov_d = _dilate(img_t, cov, 4)
    q = np.clip(np.rint(img_t / np.array(TISSUE_SCALE_MM) * 255.0), 0, 255)
    rgba = np.concatenate([q, (cov_d * 255)[..., None]], 2).astype(np.uint8)[::-1]
    d2 = _uv_tangent_dirs(obj, t3)
    d2 = d2 * np.where(d2[:, :1] < 0, -1.0, 1.0)            # axial: keep u >= 0 for smooth interpolation
    img_d, cov2 = _raster(obj, np.concatenate([d2, np.ones((len(d2), 1))], 1), size, 3)
    img_d, cov2d = _dilate(img_d, cov2, 4)
    n = np.maximum(np.linalg.norm(img_d[..., :2], axis=2, keepdims=True), 1e-9)
    img_d[..., :2] = img_d[..., :2] / n
    q2 = np.clip(np.rint((img_d[..., :2] + 1.0) * 127.5), 0, 255)
    rgba2 = np.concatenate([q2, np.full(q2.shape[:2] + (1,), 255.0), (cov2d * 255)[..., None]], 2)
    rgba2 = rgba2.astype(np.uint8)[::-1]
    os.makedirs(out_dir, exist_ok=True)
    p1 = gbc.write_png_u8(os.path.join(out_dir, TISSUE_MAP), rgba)
    p2 = gbc.write_png_u8(os.path.join(out_dir, TENSION_MAP), rgba2)
    meta = gbc.envelope({
        "mesh": obj.name, "uv": "atlas (UV0)", "size": size, "origin": "top-left row = v 1",
        "tissue_depth": {"file": TISSUE_MAP, "channels": {"r": "skin_mm", "g": "fat_mm", "b": "muscle_mm",
                                                          "a": "coverage"},
                         "scale_mm_per_255": list(TISSUE_SCALE_MM), "fat_reference_pct": 15.0,
                         "body_fat_pct": LM.BODY_FAT_PCT, "source": "RB §7.6"},
        "tension": {"file": TENSION_MAP, "channels": {"rg": "Langer line direction in UV space, (c/127.5 - 1)",
                                                      "b": "anisotropy weight", "a": "coverage"},
                    "source": "RB §2.3.1 (Langer / RSTL, K)"},
        "coverage_fraction": round(float(cov.mean()), 4),
    }, "gb.body_maps/1")
    with open(os.path.join(out_dir, MAPS_JSON), "w", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(gbc._clean(meta), indent=1) + "\n")
    return [p1, p2]


# ===========================================================================
# Stand-alone run
# ===========================================================================
if __name__ == "__main__":
    args = gbc.script_args()
    quick = "--quick" in args
    t0 = time.time()
    gbc.reset_scene()
    gbc.collections()
    objs = {}
    objs.update(build_body_skin(quick))
    objs.update(build_shorts(objs["GB_Body"], quick))
    objs.update(build_muscle_shell(objs["GB_Body"], quick))
    gbc.log(f"B1 stage built in {time.time() - t0:.1f} s: " + ", ".join(
        f"{n} {gbc.tri_count(o.data)} tris" for n, o in objs.items()))
    if "--render" in args:
        gbc.render_views("body_skin", samples=24)
