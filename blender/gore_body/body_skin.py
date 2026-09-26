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
    (1.200, 0.145, -0.108, 0.096, 3.1, 2.9),
    (1.260, 0.146, -0.104, 0.112, 3.4, 3.1),
    (1.300, 0.146, -0.108, 0.120, 3.7, 3.3),     # chest 100 cm; xiphisternal joint -0.110
    (1.340, 0.147, -0.100, 0.125, 3.5, 3.3),     # T7 spinous skin 0.122
    (1.400, 0.142, -0.081, 0.117, 3.0, 2.9),     # sternal angle -0.075 (bone) + skin
    (1.430, 0.126, -0.068, 0.108, 2.6, 2.6),
    (1.455, 0.094, -0.050, 0.097, 2.3, 2.4),     # jugular notch -0.048
    (1.470, 0.074, -0.051, 0.090, 2.2, 2.3),
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
    # lower border: level medially, rising to the anterior axillary fold
    z_low = 1.266 + 6.5 * np.maximum(ax - 0.065, 0.0) ** 2 + 0.02 * sstep(0.12, 0.16, ax)
    lower = sstep(z_low - 0.004, z_low + 0.010, z)
    upper = sstep(1.445, 1.395, z)                                  # fades under the clavicle
    medial = sstep(0.008, 0.028, ax)                                # sternal furrow between the heads
    lateral = sstep(0.175, 0.135, ax)
    bulk = 0.0075 * lower * upper * medial * lateral
    bulk *= 0.75 + 0.25 * gauss(z - 1.305, 0.05) * gauss(ax - 0.085, 0.05)   # fullest low and mid
    areola = 0.0009 * gauss(np.hypot(ax - 0.100, (z - 1.300)), 0.012)
    nipple = 0.0026 * np.exp(-(np.hypot(ax - 0.100, z - 1.300) / 0.0042) ** 4)
    return bulk + areola + nipple


def _abdomen_relief(x, z):
    """Rectus abdominis, linea alba, tendinous intersections, linea semilunaris, navel, inguinal line."""
    ax = np.abs(x)
    rect = band(z, 0.965, 1.255, 0.03) * sstep(0.095, 0.060, ax)
    bulk = 0.0045 * rect * (0.7 + 0.3 * gauss(z - 1.00, 0.06))      # lower belly slightly rounded
    alba = -0.0022 * gauss(ax, 0.0055) * band(z, 1.09, 1.26, 0.02)
    inter = sum(-0.0010 * gauss(z - zi, 0.006) for zi in (1.140, 1.198)) * sstep(0.070, 0.050, ax)
    semil = -0.0018 * gauss(ax - 0.078, 0.008) * band(z, 1.0, 1.23, 0.03)
    # navel [RB §7.1 navel (0, -0.108, 1.075)]: pit with a soft rim
    rn = np.hypot(ax, (z - 1.075) * 0.85)
    navel = -0.0085 * np.exp(-(rn / 0.0065) ** 2.5) + 0.0012 * gauss(rn - 0.009, 0.005)
    # inguinal groove: ASIS skin (0.122, 0.992) -> pubic tubercle (0.022, 0.913)
    t = np.clip(((ax - 0.122) * -0.100 + (z - 0.992) * -0.079) / (0.100 ** 2 + 0.079 ** 2), 0.0, 1.2)
    px, pz = 0.122 - 0.100 * t, 0.992 - 0.079 * t
    ing = -0.0040 * gauss(np.hypot(ax - px, z - pz), 0.014) * sstep(1.2, 0.9, t)
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
    c = GH + 0.018 * ARM_D + 0.013 * ARM_LAT + np.array([0.0, -0.003, 0.0])
    delt = sd_oellipsoid(ax, y, z, c, (0.100, 0.046, 0.057), delt_axes, n=2.0)
    # deltoid insertion: the cap narrows to a V on the lateral mid-humerus
    tub = sd_capsule(ax, y, z, GH + 0.05 * ARM_D + 0.036 * ARM_LAT, GH + 0.150 * ARM_D + 0.034 * ARM_LAT,
                     0.014, 0.005)
    delt = smin(delt, tub, 0.02)
    # upper trapezius: broad slope from the nape to the acromion
    trap = sd_polyline(ax, y, z, [(0.030, 0.052, 1.488), (0.090, 0.040, 1.476), (0.170, 0.022, 1.450)],
                       [0.028, 0.027, 0.017], k=0.02)
    clav = sd_polyline(ax, y, z, [np.array(p) + np.array([0.0, -0.001, 0.001]) for p in
                                  ((0.022, -0.040, 1.451), (0.070, -0.050, 1.453), (0.125, -0.021, 1.463),
                                   (0.168, 0.008, 1.463))], [0.0115, 0.0100, 0.0095, 0.0110], k=0.01)
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
    (1.000, -0.052, 0.085, 0.040, 0.160, 2.3),
    (0.950, -0.064, 0.100, 0.018, 0.172, 2.3),      # femoral triangle below the inguinal crease
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
    R = R + bump(0.497, 90, 0.0060, 0.019, 28)           # patella
    R = R + bump(0.530, 90, -0.0030, 0.012, 30)          # suprapatellar dip
    R = R + bump(0.462, 90, 0.0020, 0.012, 14)           # patellar tendon
    R = R + bump(0.470, 55, 0.0020, 0.012, 16)           # infrapatellar fat pads
    R = R + bump(0.470, 125, 0.0020, 0.012, 16)
    R = R + bump(0.436, 90, 0.0030, 0.011, 18)           # tibial tuberosity
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
        s_top = (1.0 - HIP[2]) / LEG_W[2]
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
    (0.045, 0.031, 0.031, 0.083, 0.040, 2.4),
    (0.075, 0.030, 0.033, 0.080, 0.040, 2.6),
    (0.110, 0.032, 0.038, 0.068, 0.036, 2.8),
    (0.145, 0.038, 0.045, 0.056, 0.030, 3.0),
    (0.175, 0.045, 0.052, 0.044, 0.024, 3.0),
    (0.200, 0.049, 0.051, 0.036, 0.020, 3.0),       # ball of the foot (MTP row)
    (0.225, 0.047, 0.043, 0.029, 0.016, 3.0),
    (0.250, 0.040, 0.027, 0.023, 0.013, 2.8),
    (0.270, 0.030, 0.012, 0.018, 0.011, 2.5),
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
        FOOT_TUBE = StarTube(FOOT_O, FOOT_F, FOOT_L, (0, 0, 1), -0.01, 0.28, _foot_profile, offset=off,
                             ds=0.002, nth=120, cap0=0.004, cap1=0.262, cap_k=0.02)
    return FOOT_TUBE


TOES = [  # base s, w, tip s, tip w, radius base, radius tip, tip height
    (0.205, -0.030, 0.262, -0.031, 0.0135, 0.0120, 0.013),     # hallux
    (0.212, -0.008, FOOT_LEN - 0.006, -0.002, 0.0090, 0.0074, 0.009),
    (0.207, 0.010, 0.254, 0.014, 0.0086, 0.0071, 0.008),
    (0.200, 0.025, 0.244, 0.028, 0.0082, 0.0068, 0.008),
    (0.190, 0.038, 0.229, 0.041, 0.0078, 0.0064, 0.007),
]


def _foot(ax, y, z):
    d = _foot_tube()._eval(ax, y, z)
    # heel: rounded calcaneal pad
    heel = sd_oellipsoid(ax, y, z, foot_point(0.036, 0.001, 0.034), (0.030, 0.032, 0.036), np.eye(3))
    d = smin(d, heel, 0.02)
    # toes merged (plan D4) but individually shaped at the tips
    toes = None
    for s0, w0, s1, w1, r0, r1, h1 in TOES:
        t = sd_capsule(ax, y, z, foot_point(s0, w0, r0 + 0.003), foot_point(s1 - r1, w1, h1), r0, r1)
        toes = t if toes is None else smin(toes, t, 0.0035)
    d = smin(d, toes, 0.010)
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
    sh = Box((0.0, -0.10, 1.25), (0.30, 0.10, 1.53), margin=0.03)
    delt, trap, clav, afold, pfold = sh.run_multi(_shoulder, ax, y, z)[:5]
    out.update(deltoid=delt, trapezius=trap, clavicle=clav, ant_fold=afold, post_fold=pfold)
    nk = Box((0.0, -0.08, 1.43), (0.08, 0.05, 1.62), margin=0.03)
    out["scm"], out["larynx"] = nk.run_multi(_neck_parts, ax, y, z)[:2]
    out["arm"] = _arm_tube()(ax, y, z)
    out["hand"] = _hand_box().run(_hand, ax, y, z)
    out["leg"] = _leg_tube()(ax, y, z)
    out["glute"] = Box((0.0, -0.05, 0.78), (0.19, 0.16, 1.05)).run(_glute, ax, y, z)
    out["glute_k"] = 0.010 + 0.045 * sstep(0.85, 0.99, z) + 0.02 * sstep(0.10, 0.15, ax)
    out["foot"] = FOOT_BOX.run(_foot, ax, y, z)
    return out


def union_components(c, off=None):
    """Blend the components into the body (``off``: per-component inward offsets, m)."""
    o = off or {}
    g = {k: (v + o.get(k, 0.0) if not k.endswith("_k") else v) for k, v in c.items()}
    trunk = smin(g["torso"], g["scm"], 0.012)
    trunk = smin(trunk, g["larynx"], 0.008)
    trunk = smin(trunk, g["trapezius"], 0.028)
    trunk = smin(trunk, g["clavicle"], 0.010)
    arm = smin(g["arm"], g["deltoid"], 0.022)
    arm = smin(arm, g["hand"], 0.012)
    body = smin(trunk, arm, 0.010)
    body = smin(body, g["ant_fold"], 0.028)
    body = smin(body, g["post_fold"], 0.030)
    leg = smin(g["leg"], g["foot"], 0.012)
    body = smin(body, leg, 0.022)
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


# ---------------------------------------------------------------------------
# (temporary) builders
# ---------------------------------------------------------------------------
def build_body_skin():
    gbc.not_built("B1", "body_skin.build_body_skin")


def build_shorts(skin):
    gbc.not_built("B1", "body_skin.build_shorts")


def build_muscle_shell(skin):
    gbc.not_built("B1", "body_skin.build_muscle_shell")


def paint_codes(obj):
    import placeholder
    return placeholder.set_skin_codes(obj)
