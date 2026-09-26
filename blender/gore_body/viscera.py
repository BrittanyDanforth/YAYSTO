"""Organs (owner B4).  Plan §3.3.6, §5.2, §5.8 organs.json, §8.2 B4; RB §7.5, R05 §10-11.

Final entry points
------------------
``build_organs()``  -> {"GB_Organs": obj, "GB_Organs_HR": obj}: heart (4 chambers as real cavities,
                       walls LV 9 / RV 4 / atria 2.5-3 mm, epicardial fat in the grooves), pericardial
                       sac, lungs (lobes split by real fissures, hila, cardiac notch, vessel grooves),
                       diaphragm (domes, central tendon, crura, hiatus openings), liver (lobes, bare
                       area, IVC groove, gallbladder fossa), gallbladder, spleen, kidneys (hilum, sinus)
                       in perirenal fat, adrenals, stomach (hollow, 3 mm wall), pancreas, bladder
                       (hollow), larynx (thyroid + cricoid cartilage, airway), trachea (hollow, C-rings,
                       membranous back wall), bronchi, oesophagus (collapsed lumen), thyroid, greater
                       omentum and the dark peritoneal backing mass (bowel filler, no intestines).
                       UV2 = (organ id, sub-part id); shape keys heart_systole, lung_inhale_L/R,
                       lung_collapse_L/R, diaphragm_inhale.
``organ_table()``   -> organs.json payload (bible hit primitives + measured mesh data).

How it works
------------
Every organ is a numpy signed-distance function (negative inside) placed in the body frame from
the bible's numbers (RB §7.5, R05 §10-11).  The chest organs are fitted to a **thoracic cage
model** built from the same rib table B3 uses (``gb_data.ribs``), so the lungs fill the pleural
space to the 6-8-10 rib borders and stay >= 2 mm inside the ribs; the diaphragm domes are shaped
by the bible dome heights and attach along the costal margin.  Neighbouring organs carve each
other (``carve``) so every organ keeps a >= 1 mm gap and carries the neighbour's impression (the
liver's renal and gastric impressions, the lungs' cardiac notch and aortic groove...).
Each SDF is polygonised on its own (surface nets + Newton projection onto the exact surface,
from the head project's toolkit), decimated to its share of the 22k budget and joined.
Hollow organs keep a closed inner surface (normals into the lumen) so a cut shows the wall
thickness and the lining, as plan §3.3.6 renders back faces as the cut interior.

Run alone: ``python3 viscera.py [--quick] [--render]`` (writes renders/viscera_*.png).
"""
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import organs as OR  # noqa: E402
from gb_data import ribs as RB_  # noqa: E402
from gb_data import vertebrae as VT  # noqa: E402

# ---------------------------------------------------------------------------
# Resolution and budgets
# ---------------------------------------------------------------------------
# per-organ polygonisation spacing (m) for the high-res mesh; quick builds use QUICK_SCALE x
QUICK_SCALE = 1.8
# thin-walled organs cannot be meshed coarser than this even in --quick (walls would vanish)
THIN_HMAX = {"heart": 0.0014, "stomach": 0.0013, "diaphragm": 0.0014, "airway": 0.0009, "larynx": 0.0008,
             "oesophagus": 0.0010, "bladder": 0.0014, "omentum": 0.0017, "adrenal_L": 0.0010, "adrenal_R": 0.0010}
# LOD0 triangle share of the 22k GB_Organs budget (plan §4.1); HR keeps up to HR_FACTOR x
HR_FACTOR = 8
DENSITY_G_ML = OR.ORGAN_DENSITY_G_CM3


def _A():
    """Head project anatomy module (SDF toolkit: smin/smax, primitives, surface nets)."""
    return gbc.import_head().anatomy


def quick():
    """True when the build runs with ``--quick`` (coarse meshes)."""
    return "--quick" in gbc.script_args()


# ===========================================================================
# SDF toolkit (flat numpy arrays; negative inside; metres, body frame)
# ===========================================================================
def smin(a, b, k):
    """Smooth union (polynomial, radius k)."""
    if k <= 0:
        return np.minimum(a, b)
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def smax(a, b, k):
    """Smooth intersection."""
    return -smin(-a, -b, k)


def carve(d, other, gap, k=0.0):
    """Remove ``other`` dilated by ``gap`` from ``d`` (keeps a gap, leaves an impression)."""
    return smax(d, -(other - gap), k) if k > 0 else np.maximum(d, -(other - gap))


def sstep(e0, e1, x):
    """Smoothstep from e0 to e1 (either order)."""
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v)


class Frame:
    """Orthonormal frame: origin ``o`` and axes U, V, W (W = U x V, Gram-Schmidt on V)."""

    def __init__(self, o, u, v):
        self.o = np.asarray(o, float)
        self.U = unit(u)
        v = np.asarray(v, float)
        v = v - (v @ self.U) * self.U
        self.V = unit(v)
        self.W = np.cross(self.U, self.V)

    def local(self, x, y, z):
        dx, dy, dz = x - self.o[0], y - self.o[1], z - self.o[2]
        return tuple(a[0] * dx + a[1] * dy + a[2] * dz for a in (self.U, self.V, self.W))

    def world(self, p):
        p = np.asarray(p, float)
        return self.o + p[..., 0:1] * self.U + p[..., 1:2] * self.V + p[..., 2:3] * self.W


def ell(x, y, z, c, r):
    """Axis-aligned ellipsoid (IQ distance bound) in whatever coordinates are passed."""
    k0 = np.sqrt(((x - c[0]) / r[0]) ** 2 + ((y - c[1]) / r[1]) ** 2 + ((z - c[2]) / r[2]) ** 2)
    k1 = np.sqrt(((x - c[0]) / r[0] ** 2) ** 2 + ((y - c[1]) / r[1] ** 2) ** 2 + ((z - c[2]) / r[2] ** 2) ** 2)
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def capsule(x, y, z, a, b, ra, rb=None):
    """Capsule / cone segment a->b with radius ra (-> rb)."""
    rb = ra if rb is None else rb
    a, b = np.asarray(a, float), np.asarray(b, float)
    ab = b - a
    t = np.clip(((x - a[0]) * ab[0] + (y - a[1]) * ab[1] + (z - a[2]) * ab[2]) / (ab @ ab), 0.0, 1.0)
    px, py, pz = x - a[0] - t * ab[0], y - a[1] - t * ab[1], z - a[2] - t * ab[2]
    return np.sqrt(px * px + py * py + pz * pz) - (ra + (rb - ra) * t)


def chain(x, y, z, pts, radii, k=0.0):
    """Smooth union of tapered capsules through ``pts`` (radii per point)."""
    pts = np.asarray(pts, float)
    radii = np.broadcast_to(np.asarray(radii, float), (len(pts),))
    d = None
    for i in range(len(pts) - 1):
        s = capsule(x, y, z, pts[i], pts[i + 1], radii[i], radii[i + 1])
        d = s if d is None else smin(d, s, k)
    return d


def polyline_param(x, y, z, pts):
    """(distance, t in 0..1 by arc length, index of the nearest segment) to a polyline."""
    pts = np.asarray(pts, float)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)])
    best = np.full(x.shape, np.inf)
    tt = np.zeros(x.shape)
    idx = np.zeros(x.shape, np.int32)
    for i in range(len(pts) - 1):
        a, ab = pts[i], pts[i + 1] - pts[i]
        t = np.clip(((x - a[0]) * ab[0] + (y - a[1]) * ab[1] + (z - a[2]) * ab[2]) / (ab @ ab), 0.0, 1.0)
        d = np.sqrt((x - a[0] - t * ab[0]) ** 2 + (y - a[1] - t * ab[1]) ** 2 + (z - a[2] - t * ab[2]) ** 2)
        m = d < best
        best = np.where(m, d, best)
        tt = np.where(m, (cum[i] + t * seg[i]) / cum[-1], tt)
        idx = np.where(m, i, idx)
    return best, tt, idx


def dense(points, step=0.002):
    """Catmull-Rom densified polyline (head toolkit) resampled at ~step."""
    import gb_geom as gg
    P, _t = gg.resample(points, step, smooth=True)
    return P


def fbm3(x, y, z, scale, seed, octaves=3):
    """Cheap smooth value-free noise (sum of random plane waves) in [-1, 1]-ish; deterministic."""
    rng = np.random.default_rng(seed)
    out = np.zeros_like(x)
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        for _ in range(4):
            d = unit(rng.normal(size=3))
            ph = rng.uniform(0, 2 * np.pi)
            k = 2 * np.pi / scale * (2.03 ** o)
            out += amp * np.sin(k * (d[0] * x + d[1] * y + d[2] * z) + ph)
            tot += amp
        amp *= 0.5
    return out / tot * 2.0


# ===========================================================================
# Thoracic cage model (from the rib table B3 builds the ribs from)
# ===========================================================================
CAGE_YC = 0.012                   # cage axis (x = 0, y = CAGE_YC): same axis B3 orients ribs about
RIB_HALF_T = 0.0045               # rib/cartilage half thickness toward the lung (6-8 mm sections, B3 fit)
PLEURA_GAP = 0.0022               # endothoracic fascia + parietal pleura + >= 2 mm FB-4 margin
_CAGE = None


def _theta_r(x, y):
    """Cage coordinates: theta (deg; -90 front midline, 0 lateral, +90 back midline), radius."""
    dy = y - CAGE_YC
    return np.degrees(np.arctan2(dy, np.abs(x))), np.sqrt(x * x + dy * dy)


def _rib_curves():
    """Dense left rib curves (rib + costal cartilage; ribs 1-7 continued to the sternum), each as
    (P, theta, r) ordered by increasing theta and trimmed to the part where theta is monotonic:
    from the posterior angle forward, plus the head/neck part only while theta keeps growing
    (the lower ribs' heads curl forward onto the lordotic bodies)."""
    global _RIBS
    if _RIBS is not None:
        return _RIBS
    out = {}
    for n in range(1, 13):
        kind, head, angle, _l, _c, cart_end, joins, *_r = RB_.RIB_TABLE[n]
        pts = list(RB_.rib_points(n, include_cartilage=True))
        if n <= 7 and cart_end is not None:
            pts = pts + [(0.0, cart_end[1] + 0.006, cart_end[2])]
        P = dense(pts, 0.002)
        th, r = _theta_r(P[:, 0], P[:, 1])
        ia = int(np.argmin(np.linalg.norm(P - np.asarray(angle), axis=1)))
        keep = list(range(ia, len(P)))
        j = ia - 1
        while j >= 0 and th[j] > th[j + 1]:
            keep.insert(0, j)
            j -= 1
        P, th, r = P[keep], th[keep], r[keep]
        # front part must be monotonic too (cartilage tips): cut where theta turns back
        mono = np.concatenate([[True], np.diff(th) < 0])
        stop = np.argmin(mono) if not mono.all() else len(P)
        P, th, r = P[:stop], th[:stop], r[:stop]
        o = np.argsort(th)
        out[n] = (P[o], th[o], r[o])
    _RIBS = out
    return out


_RIBS = None


def cage_table():
    """Precomputed inner cage radius r(theta, z) at the rib centrelines' level (lazy, cached).

    For every theta the ribs crossing that direction give (z_n, r_n); r(z) is interpolated between
    consecutive ribs (the intercostal muscles close the wall), clamped above rib 1 and below the
    lowest rib.  Returns dict(th, z, R) with R[theta_i, z_j] = rib centreline radius."""
    global _CAGE
    if _CAGE is not None:
        return _CAGE
    th_grid = np.linspace(-90.0, 90.0, 181)
    z_grid = np.arange(1.080, 1.540, 0.002)
    per = [(th, r, P[:, 2]) for P, th, r in _rib_curves().values()]
    R = np.zeros((len(th_grid), len(z_grid)))
    for i, t in enumerate(th_grid):
        zs, rs = [], []
        for th, r, z in per:
            if th[0] - 0.5 <= t <= th[-1] + 0.5:
                zs.append(np.interp(t, th, z))
                rs.append(np.interp(t, th, r))
        if not zs:
            R[i] = np.nan
            continue
        o = np.argsort(zs)
        R[i] = np.interp(z_grid, np.array(zs)[o], np.array(rs)[o])
    # paravertebral directions beyond the rib heads: carry the nearest valid column
    for i in range(len(th_grid)):
        if np.isnan(R[i, 0]):
            j = np.nanargmin([abs(k - i) if not np.isnan(R[k, 0]) else 1e9 for k in range(len(th_grid))])
            R[i] = R[j]
    _CAGE = dict(th=th_grid, z=z_grid, R=R)
    return _CAGE


def _bilinear(T, th, z):
    """Sample cage_table R at (theta deg, z)."""
    tg, zg, R = T["th"], T["z"], T["R"]
    fi = np.clip((th - tg[0]) / (tg[1] - tg[0]), 0, len(tg) - 1.001)
    fj = np.clip((z - zg[0]) / (zg[1] - zg[0]), 0, len(zg) - 1.001)
    i0, j0 = np.floor(fi).astype(int), np.floor(fj).astype(int)
    a, b = fi - i0, fj - j0
    return ((1 - a) * (1 - b) * R[i0, j0] + a * (1 - b) * R[i0 + 1, j0] + (1 - a) * b * R[i0, j0 + 1]
            + a * b * R[i0 + 1, j0 + 1])


def cage_radius(x, y, z):
    """Rib-centreline radius of the cage wall in the direction of (x, y) at height z."""
    th, _r = _theta_r(x, y)
    return _bilinear(cage_table(), th, z)


def cage_sdf(x, y, z, inset=RIB_HALF_T + PLEURA_GAP):
    """Radial distance to the inner cage wall (negative inside), inset from the rib centrelines."""
    th, r = _theta_r(x, y)
    return r - (_bilinear(cage_table(), th, z) - inset)


# ---------------------------------------------------------------------------
# Pleural and lung borders, costal-margin attachment of the diaphragm (theta -> z)
# ---------------------------------------------------------------------------
def _rib_z_at_theta(n, theta):
    """z of rib ``n`` (with its cartilage) in the direction theta (clamped at its ends)."""
    P, th, _r = _rib_curves()[n]
    return np.interp(theta, th, P[:, 2])


def _mcl_theta():
    """Theta of the mid-clavicular line on the lower chest (x = 0.09 at the 6th cartilage)."""
    return float(np.degrees(np.arctan2(-0.080 - CAGE_YC, 0.090)))


def lung_border_z(theta):
    """Lower lung border (quiet expiration): 6th rib at the MCL, 8th at the MAL, 10th at the back
    (R05 §10.5 '6-8-10'); in front of the MCL it rises along the 6th cartilage to the sternum."""
    th = np.asarray(theta, float)
    t_mcl, t_mal, t_back = _mcl_theta(), 0.0, 55.0
    # the thin inferior margin runs along the inner face of the rib: allow it ~6 mm below the centreline
    a = [(t_mcl, float(_rib_z_at_theta(6, t_mcl)) - 0.003), (t_mal, float(_rib_z_at_theta(8, t_mal)) - 0.006),
         (t_back, float(_rib_z_at_theta(10, t_back)) - 0.006)]
    z = np.interp(th, [p[0] for p in a], [p[1] for p in a])
    return np.where(th < t_mcl, _rib_z_at_theta(6, th) - 0.003, z)


def pleura_border_z(theta):
    """Lower pleural reflection '8-10-12' (floor of the costodiaphragmatic recess)."""
    th = np.asarray(theta, float)
    t_mcl, t_mal, t_back = _mcl_theta(), 0.0, 40.0
    a = [(t_mcl, float(_rib_z_at_theta(8, t_mcl))), (t_mal, float(_rib_z_at_theta(10, t_mal))),
         (t_back, float(_rib_z_at_theta(12, t_back)))]
    z = np.interp(th, [p[0] for p in a], [p[1] for p in a])
    front = _rib_z_at_theta(7, th) - 0.012        # along the 7th cartilage to the xiphoid
    return np.where(th < t_mcl, np.minimum(front, a[0][1] + (t_mcl - th) * 0.0015), z)


# costal-margin / arcuate-ligament attachment of the diaphragm: theta (deg) -> z (R05 §10.6, E fit)
_ATTACH = [(-90, 1.276), (-75, 1.262), (-55, 1.205), (-38, 1.150), (-20, 1.128), (0, 1.140), (20, 1.160),
           (40, 1.175), (60, 1.182), (75, 1.170), (90, 1.160)]


def attach_z(theta):
    """Height where the diaphragm leaves the body wall (xiphoid, costal margin, ribs 11-12, arcuate lig.)."""
    a = np.array(_ATTACH)
    return np.interp(theta, a[:, 0], a[:, 1])


# ---------------------------------------------------------------------------
# Diaphragm upper surface (standing, end-expiration) [R05 §10.6]
# ---------------------------------------------------------------------------
DOME_R = np.array([-0.070, -0.005, 1.320])
DOME_L = np.array([0.075, 0.005, 1.300])
CENTRAL_TENDON = np.array([0.000, -0.030, 1.310])
DIAPHRAGM_T = 0.0040              # muscle 3-5 mm
TENDON_T = 0.0025                 # central tendon 1-2 mm (meshable minimum)


def dome_height(x, y):
    """Top surface z of the diaphragm: two domes and the central tendon plateau, falling to the
    pleural reflection line at the chest wall (the zone of apposition continues down the wall)."""
    def dome(c, sx, sy):
        syy = np.where(y > c[1], 0.058, sy)        # steeper behind: the deep posterior costophrenic recess
        return c[2] - 0.5 * (((x - c[0]) / sx) ** 2 + ((y - c[1]) / syy) ** 2) * 0.050
    hr = dome(DOME_R, 0.070, 0.075)
    hl = dome(DOME_L, 0.065, 0.070)
    ht = CENTRAL_TENDON[2] - 0.5 * ((x / 0.060) ** 2 + ((y - CENTRAL_TENDON[1]) / 0.045) ** 2) * 0.030
    top = smin(-hr, -hl, 0.012)
    top = -smin(top, -ht, 0.010)
    # fall toward the chest wall: the rim meets the pleural reflection line
    th, r = _theta_r(x, y)
    rw = _bilinear(cage_table(), th, np.full_like(x, 1.290)) - RIB_HALF_T - PLEURA_GAP
    dw = np.clip(rw - r, 0.0, None)
    s = 1.0 - np.exp(-(dw / 0.006) ** 2)
    rim = pleura_border_z(th) - 0.004
    return rim + (top - rim) * s


# ---------------------------------------------------------------------------
# Vertebral column and the great vessels (exclusion volumes)
# ---------------------------------------------------------------------------
def spine_sdf(x, y, z):
    """Vertebral bodies + discs as a superelliptic column through the RB §7.3 body centres."""
    rows = VT.VERTEBRAE
    zs = np.array([r["z"] for r in rows])[::-1]
    ys = np.array([r["y"] for r in rows])[::-1]
    ws = np.array([r["body_w_mm"] for r in rows])[::-1] / 2000.0
    ds = np.array([r["body_d_mm"] for r in rows])[::-1] / 2000.0
    ws[-1] = min(ws[-1], 0.012)          # C1 row lists the transverse-process span; the column is narrow
    ds[-1] = min(ds[-1], 0.009)
    yc = np.interp(z, zs, ys)
    a = np.interp(z, zs, ws)
    b = np.interp(z, zs, ds)
    rr = (np.abs(x / a) ** 2.5 + np.abs((y - yc) / b) ** 2.5) ** (1 / 2.5)
    d = (rr - 1.0) * np.minimum(a, b)
    return np.maximum(d, np.maximum(zs[0] - 0.02 - z, z - zs[-1] - 0.01))


_RIB_TUBES = None


def rib_tubes_sdf(x, y, z, grow=0.0):
    """Ribs + costal cartilages as tubes around the rib-table centrelines (both sides): half height ~7 mm,
    half thickness ~4.5 mm modelled as a 6 mm round tube + ``grow``; gives the lungs their rib impressions
    and keeps every organ clear of B3's ribs."""
    global _RIB_TUBES
    if _RIB_TUBES is None:
        segs = []
        for n in range(1, 13):
            P = dense(RB_.rib_points(n, include_cartilage=True), 0.004)
            r = {1: 0.0115, 2: 0.0085}.get(n, 0.0060)            # rib 1 is a flat 27 mm plate [RB §7.3]
            for sx in (1.0, -1.0):
                Q = P * np.array([sx, 1.0, 1.0])
                segs.append((Q, r))
        _RIB_TUBES = segs
    d = np.full(x.shape, 1.0)
    for Q, rr in _RIB_TUBES:
        lo, hi = Q.min(0) - 0.02, Q.max(0) + 0.02
        m = (x > lo[0]) & (x < hi[0]) & (y > lo[1]) & (y < hi[1]) & (z > lo[2]) & (z < hi[2])
        if m.any():
            dd, _t, _i = polyline_param(x[m], y[m], z[m], Q)
            d[m] = np.minimum(d[m], dd - (rr + grow))
    return d


def sternum_sdf(x, y, z):
    """Sternum plate (manubrium -> body -> xiphoid), 11-12 mm thick behind its front-surface points,
    55 -> 25-35 -> 17 mm wide [R05 §5.1]."""
    down = np.array(RB_.STERNUM_DOWN_AXIS, float)
    back = unit(np.cross(down, [1.0, 0.0, 0.0]))
    if back[1] < 0:
        back = -back
    pts = np.array([RB_.STERNUM["manubrium"]["top"], RB_.STERNUM["body"]["top"], RB_.STERNUM["body"]["bottom"],
                    RB_.STERNUM["xiphoid"]["bottom"]], float) + back * 0.0058
    half_w = np.array([0.0275, 0.0150, 0.0165, 0.0085])
    dist, t, idx = polyline_param(np.zeros_like(x), y, z, pts)
    seg = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    cum = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
    hw = np.interp(t, cum, half_w)
    lat = np.maximum(np.abs(x) - hw, 0.0)
    return np.sqrt(dist ** 2 + lat ** 2) - 0.0058


def paravertebral_sdf(x, y, z):
    """Posterior vertebral elements the column model lacks (pedicles, transverse processes, rib heads and
    necks) as a band beside and behind each body [RB §7.3]."""
    rows = VT.VERTEBRAE[::-1]
    zs = np.array([r["z"] for r in rows])
    yb = np.array([r["y"] + r["body_d_mm"] / 2000.0 for r in rows])
    ybc = np.interp(z, zs, yb)
    ax = np.abs(x)
    d = np.sqrt(np.maximum(ax - 0.048, 0.0) ** 2 + ((y - (ybc + 0.016)) / 1.0) ** 2) - 0.014
    return np.maximum(d, np.maximum(zs[0] - 0.01 - z, z - 1.50))


def boxed(fn, lo, hi, far=1.0):
    """Evaluate ``fn`` only for points inside the box lo..hi (elsewhere return ``far``): expensive
    neighbour fields used by ``carve`` cost nothing away from their organ."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)

    def g(x, y, z):
        m = (x > lo[0]) & (x < hi[0]) & (y > lo[1]) & (y < hi[1]) & (z > lo[2]) & (z < hi[2])
        out = np.full(x.shape, far)
        if m.any():
            out[m] = fn(x[m], y[m], z[m])
        return out
    g.__name__ = getattr(fn, "__name__", "boxed")
    return g


_VESSEL_CACHE = {}


def vessel_sdf(ids, grow=0.0, zmin=-1.0, zmax=9.0):
    """Union of tubes (bible waypoints, gb_data.vessels) of the given segment ids, radius d/2 + grow.

    B5 refines the centrelines within 2 mm of these waypoints, so carving organs around them keeps
    the organs clear of the final vessel tubes."""
    from gb_data import vessels as VS
    key = (tuple(ids), grow)
    if key not in _VESSEL_CACHE:
        segs = {s["id"]: s for s in VS.vessel_segments()}
        tubes = []
        for i in ids:
            s = segs.get(i)
            if s is None:
                continue
            P = np.asarray(s["points"], float)
            d0 = s["d_mm"] / 2000.0
            d1 = (s["d_end_mm"] or s["d_mm"]) / 2000.0
            tubes.append((P, np.linspace(d0, d1, len(P)) + grow))
        _VESSEL_CACHE[key] = tubes
    tubes = _VESSEL_CACHE[key]

    def fn(x, y, z):
        d = np.full(x.shape, 1.0)
        for P, r in tubes:
            if P[:, 2].max() + 0.03 < zmin or P[:, 2].min() - 0.03 > zmax:
                continue
            d = np.minimum(d, chain(x, y, z, P, r))
        return d
    return fn


# vessel groups used for carving (bible ids, B5 keeps them within 2 mm)
MEDIASTINAL_VESSELS = ["A01", "A02", "A03", "A04_L", "A04_R", "A14_L", "A14_R", "A20", "V03_L", "V03_R",
                       "V05", "V10", "P01", "P01_RPA", "P01_LPA", "P02_L_sup", "P02_L_inf", "P02_R_sup",
                       "P02_R_inf", "V01_L", "V01_R", "V04_L", "V04_R"]
ABDOMINAL_VESSELS = ["A20", "A21", "V10", "V13", "A22", "A23", "A24_L", "A24_R", "V12_L", "V12_R",
                     "V11_right", "V11_middle", "V11_left"]


# ===========================================================================
# Heart and pericardium [RB §7.5; R05 §10.3]
# ===========================================================================
HEART_BASE = np.array(OR.HEART["axis_base"])        # (0, -0.005, 1.360)
HEART_APEX = np.array(OR.HEART["axis_apex"])        # (0.082, -0.068, 1.285)
HEART_FRAME = Frame(HEART_BASE, HEART_APEX - HEART_BASE, OR.PRIMITIVES["heart"]["v"])
# local coordinates: a from the base toward the apex, b up (V), c anterior-right (W = U x V)
WALL = dict(LV=0.0080, RV=0.0036, RA=0.0025, LA=0.0024, septum_atrial=0.0030)
HEART_SUB = {"RA": 1, "RV": 2, "LA": 3, "LV": 4, "fat": 5}
PERICARDIUM_GAP = 0.0025


def _cone(a, b, c):
    """Ventricular mass: a rounded cone along the long axis (base a = 0.014 -> apex a = 0.127) with a
    flattened diaphragmatic (inferior, -b) surface and a fuller anterior-right (RV) side."""
    a0, a1 = 0.012, HEART_LEN
    t = np.clip((a - a0) / (a1 - a0), 0.0, 1.0)
    s = np.clip(1.0 - t ** 2.1, 0.0, 1.0) ** 0.60
    s = np.maximum(s, 0.0)
    rb = 0.0020 + 0.0435 * s
    rc = 0.0020 + 0.0335 * s
    cb = -0.004 - 0.006 * t
    cc = 0.006 - 0.004 * t
    rr = np.sqrt(((b - cb) / rb) ** 2 + ((c - cc) / rc) ** 2)
    side = (rr - 1.0) * np.minimum(rb, rc)
    ends = np.maximum(a0 - a, a - a1)
    d = smax(side, ends, 0.010)
    return smax(d, -0.0355 - b, 0.012)                    # flat diaphragmatic surface


HEART_LEN = float(np.linalg.norm(HEART_APEX - HEART_BASE))   # 0.1277 m
LV_CAV = dict(c=(0.064, 0.000, -0.006), r=(0.047, 0.0205, 0.0190))
SEPTUM_N = unit([0.0, -0.30, 1.0])                 # (b, c) normal of the interventricular septum


def _lv_cavity(a, b, c):
    k = np.clip(1.0 - 0.30 * np.clip((a - 0.064) / 0.047, 0.0, 1.0) ** 2, 0.5, 1.0)
    cc = LV_CAV["c"]
    return ell(a, (b - cc[1]) / k + cc[1], (c - cc[2]) / k + cc[2], cc, LV_CAV["r"]) * k


def _world_parts(x, y, z):
    """Atria, auricles and the outflow tracts, placed in the body frame (R05 §10.3 chamber table)."""
    ra = ell(x, y, z, (-0.029, -0.022, 1.338), (0.0215, 0.0235, 0.0355))
    ra_app = ell(x, y, z, (-0.012, -0.054, 1.372), (0.018, 0.0080, 0.0115))
    ra_app = smax(ra_app, -ell(x, y, z, (0.004, -0.050, 1.366), (0.008, 0.02, 0.007)), 0.003)   # notched tip
    la = ell(x, y, z, (0.010, -0.004, 1.366), (0.028, 0.0155, 0.0195))
    la_app = ell(x, y, z, (0.041, -0.036, 1.372), (0.0150, 0.0080, 0.0080))
    rvot = capsule(x, y, z, (0.032, -0.062, 1.343), (0.022, -0.058, 1.380), 0.0165, 0.0128)
    lvot = capsule(x, y, z, (0.025, -0.030, 1.335), (0.008, -0.038, 1.362), 0.0135, 0.0125)
    return dict(ra=ra, ra_app=ra_app, la=la, la_app=la_app, rvot=rvot, lvot=lvot)


def _heart_fields(x, y, z):
    """(outer myocardium incl. grooves, cavities by chamber, fat solid, groove-free outer) in the body frame."""
    a, b, c = HEART_FRAME.local(x, y, z)
    W = _world_parts(x, y, z)
    lv_cav = _lv_cavity(a, b, c)
    lv_out = lv_cav - WALL["LV"]
    vent = smin(_cone(a, b, c), lv_out, 0.010)
    vent = smin(vent, W["rvot"], 0.018)
    atria = smin(smin(W["ra"], W["ra_app"], 0.006), smin(W["la"], W["la_app"], 0.006), 0.006)
    full = smin(vent, atria, 0.012)
    full = smin(full, W["lvot"], 0.004)
    full = carve(full, _STERN(x, y, z), 0.0050, 0.006)           # anterior surface clears the sternum
    # grooves: AV sulcus ring and the anterior/posterior interventricular grooves (septum plane)
    sep = SEPTUM_N[1] * b + SEPTUM_N[2] * (c - 0.017)
    g_av = np.exp(-((a - 0.021) / 0.0070) ** 2) * sstep(-0.004, 0.012, a)
    g_iv = np.exp(-(sep / 0.0060) ** 2) * sstep(0.02, 0.035, a) * (1.0 - sstep(0.108, 0.124, a))
    patch = sstep(0.95, 1.35, fbm3(x, y, z, 0.022, 5, 2)) * (1.0 - sstep(0.030, 0.065, a))
    groove = np.maximum(g_av, g_iv)
    outer = full + 0.0032 * groove
    # cavities (walls LV 9 incl. septum, RV 4.2, atria 2.6-2.8 mm); valves close the AV plane
    trab = 0.0009 * fbm3(x, y, z, 0.006, 11, 2)                  # trabeculae carneae roughness
    lv_c = smax(lv_cav + np.maximum(trab, 0.0), 0.030 - a, 0.004)
    pap = np.minimum(capsule(a, b, c, (0.085, 0.014, -0.004), (0.047, 0.006, -0.004), 0.0070, 0.0035),
                     capsule(a, b, c, (0.080, -0.012, -0.013), (0.045, -0.006, -0.008), 0.0070, 0.0035))
    lv_c = carve(lv_c, pap, 0.0, 0.003)
    rv_c = smax(vent + WALL["RV"] + np.abs(trab) * 0.6, -(lv_out - 0.0004), 0.003)
    rv_c = smax(rv_c, np.maximum(0.028 - a, a - 0.104), 0.005)
    rv_pap = capsule(a, b, c, (0.080, -0.022, 0.030), (0.048, -0.012, 0.024), 0.0055, 0.0030)
    rv_c = carve(rv_c, rv_pap, 0.0, 0.003)
    ra_c = smax(smin(W["ra"], W["ra_app"], 0.008) + WALL["RA"], -(W["la"] + WALL["septum_atrial"] - WALL["LA"]),
                0.002)
    ra_c = smax(ra_c, a - 0.016, 0.003)
    la_c = smax(smin(W["la"], W["la_app"], 0.006) + WALL["LA"], -(W["ra"] - 0.0005), 0.002)
    la_c = smax(la_c, np.maximum(a - 0.016, -(W["lvot"] - 0.0025)), 0.003)
    walls = {"LV": WALL["LV"], "RV": WALL["RV"], "RA": WALL["RA"], "LA": WALL["LA"]}
    cav = {k: np.maximum(cv, outer + walls[k]) for k, cv in
           {"LV": lv_c, "RV": rv_c, "RA": ra_c, "LA": la_c}.items()}   # walls also under grooves
    fat = np.maximum(full - 0.0009, 0.004 * (0.45 - np.maximum(groove, patch)))
    return outer, cav, fat, full


def heart_sdf(x, y, z):
    """Heart solid: myocardium + epicardial fat with the four chambers as closed cavities."""
    outer, cav, fat, _full = _heart_fields(x, y, z)
    solid = np.minimum(outer, fat)
    cavity = np.minimum(np.minimum(cav["LV"], cav["RV"]), np.minimum(cav["RA"], cav["LA"]))
    return np.maximum(solid, -cavity)


def heart_sub(v):
    """Sub-part per vertex: nearest cavity if on a cavity wall, else the chamber whose wall it
    covers (1 RA, 2 RV, 3 LA, 4 LV); 5 = epicardial fat."""
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    outer, cav, fat, _full = _heart_fields(x, y, z)
    cv = np.stack([cav["RA"], cav["RV"], cav["LA"], cav["LV"]], 1)
    near_cav = np.abs(cv).min(1) < 0.0012
    ids = np.argmin(np.abs(cv) if False else cv, 1) + 1
    ids = np.where(near_cav, np.argmin(np.abs(cv), 1) + 1, ids)
    on_fat = (fat <= outer + 1e-5) & ~near_cav & (fat < 0.0008)
    return np.where(on_fat, HEART_SUB["fat"], ids).astype(np.int32)


def heart_box():
    lo = np.array([-0.075, -0.100, 1.255])
    hi = np.array([0.110, 0.035, 1.425])
    return lo, hi


def pericardium_sdf(x, y, z):
    """Fibrous pericardial sac: the heart dilated by 2.5 mm, rising 2-3 cm up the great-vessel roots
    (ascending aorta, pulmonary trunk, SVC) and fused below with the central tendon."""
    outer, _cav, fat, full = _heart_fields(x, y, z)
    sac = np.minimum(full, fat) - PERICARDIUM_GAP
    roots = chain(x, y, z, [(0.006, -0.036, 1.358), (-0.004, -0.044, 1.398)], [0.0205, 0.0185])
    roots = smin(roots, chain(x, y, z, [(0.020, -0.056, 1.376), (0.012, -0.034, 1.402)], [0.0180, 0.0165]), 0.008)
    roots = smin(roots, chain(x, y, z, [(-0.028, -0.029, 1.372), (-0.028, -0.033, 1.405)], [0.0130, 0.0125]), 0.008)
    sac = smin(sac, roots, 0.012)
    sac = carve(sac, sternum_sdf(x, y, z), 0.0025, 0.004)
    return smax(sac, z - 1.410, 0.004)


# ===========================================================================
# Airway: trachea (C-rings, membranous back wall) + main bronchi, one Y-shaped hollow solid
# [R05 §10.1: cricoid -> carina 11 cm, outer 20 x 18 mm, wall ~3 mm, 16-20 C-rings ~4 mm]
# ===========================================================================
TRACHEA_PTS = [(0.000, -0.0295, 1.5045), (0.000, -0.018, 1.455), (-0.003, 0.008, 1.402)]
BRONCHUS_PTS = {"R": [(-0.003, 0.008, 1.402), (-0.028, 0.012, 1.380), (-0.043, 0.016, 1.371)],
                "L": [(-0.003, 0.008, 1.402), (0.042, 0.020, 1.380), (0.051, 0.023, 1.377)]}
AIR_R = {"trachea": (0.0100, 0.0090), "R": (0.0075, 0.0070), "L": (0.0062, 0.0058)}
AIR_WALL = {"trachea": 0.0027, "R": 0.0022, "L": 0.0020}
RING_PERIOD = 0.0056            # 4 mm ring + 1.6 mm annular ligament (18 rings over 10.5 cm)
_AIR = {}


def _airway_tube(x, y, z, key, pts):
    """(outer, lumen, ring mask, posterior mask, t) of one airway tube with a D-shaped section."""
    P = dense(pts, 0.0015) if len(pts) > 2 else np.asarray(pts, float)
    d, t, idx = polyline_param(x, y, z, P)
    seg = np.diff(P, axis=0)
    T = seg / np.linalg.norm(seg, axis=1, keepdims=True)
    Ti = T[idx]
    foot = P[idx] + ((np.stack([x, y, z], 1) - P[idx]) * Ti).sum(1, keepdims=True) * Ti
    rel = np.stack([x, y, z], 1) - foot
    # section frame: lateral = world x projected; posterior = T x lateral (points +y roughly)
    lat = np.tile([1.0, 0.0, 0.0], (len(x), 1)) - Ti[:, :1] * Ti
    lat /= np.linalg.norm(lat, axis=1, keepdims=True)
    post = np.cross(Ti, lat)
    post = np.where((post[:, 1:2] < 0), -post, post)
    u = (rel * lat).sum(1)
    w = (rel * post).sum(1)
    ra, rb = AIR_R[key]
    L = float(np.linalg.norm(np.diff(P, axis=0), axis=1).sum())
    s_len = t * L
    ring = 0.5 + 0.5 * np.cos(2 * np.pi * s_len / RING_PERIOD)
    ring = sstep(0.35, 0.65, ring)
    backm = sstep(0.25 * rb, 0.55 * rb, w)                   # posterior membranous wall (flat)
    rr = np.sqrt((u / ra) ** 2 + (w / rb) ** 2)
    d2 = (rr - 1.0) * min(ra, rb)
    d2 = smax(d2, w - 0.70 * rb, 0.002)                        # flat back
    outer = d2 - 0.00075 * ring * (1.0 - backm)
    lum = d2 + AIR_WALL[key]
    # length limits (closed ends at the cricoid and at the hila)
    along = (np.stack([x, y, z], 1) - P[0]) @ unit(P[1] - P[0])
    endv = unit(P[-1] - P[-2])
    past = (np.stack([x, y, z], 1) - P[-1]) @ endv
    return outer, lum, ring * (1 - backm), backm, t, along, past


def airway_fields(x, y, z):
    """(solid, lumen, which part 0 trachea 1 R 2 L, ring mask, back mask)."""
    tr = _airway_tube(x, y, z, "trachea", TRACHEA_PTS)
    br = _airway_tube(x, y, z, "R", BRONCHUS_PTS["R"])
    bl = _airway_tube(x, y, z, "L", BRONCHUS_PTS["L"])
    outs = [smax(tr[0], -tr[5], 0.001), smax(br[0], np.maximum(br[6], -br[5] - 0.006), 0.002),
            smax(bl[0], np.maximum(bl[6], -bl[5] - 0.006), 0.002)]
    lums = [smax(tr[1], -tr[5] + 0.0022, 0.001), smax(br[1], np.maximum(br[6] + 0.0022, -br[5] - 0.008), 0.002),
            smax(bl[1], np.maximum(bl[6] + 0.0020, -bl[5] - 0.008), 0.002)]
    # the trachea stops at the carina: below it only the bronchi
    below = z - 1.404
    outs[0] = smax(outs[0], -below - 0.004, 0.004)
    lums[0] = smax(lums[0], -below - 0.004, 0.004)
    solid = smin(smin(outs[0], outs[1], 0.004), outs[2], 0.004)
    lumen = smin(smin(lums[0], lums[1], 0.003), lums[2], 0.003)
    part = np.argmin(np.stack([outs[0], outs[1], outs[2]], 1), 1)
    ringm = np.choose(part, [tr[2], br[2], bl[2]])
    backm = np.choose(part, [tr[3], br[3], bl[3]])
    return solid, lumen, part, ringm, backm


def airway_sdf(x, y, z):
    solid, lumen, *_r = airway_fields(x, y, z)
    return np.maximum(solid, -lumen)


def airway_outer(x, y, z):
    return airway_fields(x, y, z)[0]


# ===========================================================================
# Larynx: thyroid cartilage (shield), cricoid (signet ring), mucosal tube with the glottis
# [R05 §10.1: prominence (0, -0.058, 1.537), laminae 40 mm; cricoid (0, -0.033, 1.513)]
# ===========================================================================
LARYNX_SUB = {"thyroid_cartilage": 1, "cricoid": 2, "soft": 3, "lumen": 4}


def _larynx_parts(x, y, z):
    ax = np.abs(x)
    # thyroid cartilage: two laminae meeting in front at ~90 deg (the prominence), 2.5 mm plates
    yp, zc = -0.058, 1.531
    dpl = np.abs(0.7071 * ax - 0.7071 * (y - yp) + 0.0015) - 0.0015  # 3 mm plates, outer face on the line
    back = (y - (yp + 0.028))                                   # laminae ~30 mm deep
    lam = np.maximum(dpl, back)
    lam = np.maximum(lam, np.abs(z - zc) - 0.0150)              # 30 mm tall
    notch = ell(x, y, z, (0.0, yp - 0.002, zc + 0.0165), (0.006, 0.012, 0.009))   # superior notch
    lam = np.maximum(lam, -notch)
    lam = np.maximum(lam, ax - 0.021)                           # 42 mm across the laminae
    horn = capsule(ax, y, z, (0.020, yp + 0.029, zc + 0.010), (0.019, yp + 0.031, zc + 0.018), 0.0022)
    thyroid = smin(lam, horn, 0.002)
    # cricoid: low anterior arch, tall posterior lamina (signet ring)
    cz, cy = 1.5105, -0.033
    ring_o = np.sqrt((x / 0.0128) ** 2 + ((y - cy) / 0.0132) ** 2) - 1.0
    ring_i = np.sqrt((x / 0.0090) ** 2 + ((y - cy) / 0.0092) ** 2) - 1.0
    ring = np.maximum(ring_o * 0.012, -ring_i * 0.009)
    height = 0.0035 + 0.0090 * sstep(-0.006, 0.010, y - cy)     # 7 mm arch in front, 25 mm lamina behind
    zc2 = cz + 0.0090 * sstep(-0.006, 0.010, y - cy)
    cric = np.maximum(ring, np.abs(z - zc2) - height)
    # mucosal/muscular tube (vocal folds, arytenoids, conus elasticus) between the cartilages
    soft_o = chain(x, y, z, [(0.0, -0.0325, 1.505), (0.0, -0.0350, 1.528), (0.0, -0.036, 1.550)],
                   [0.0115, 0.0140, 0.0135])
    soft_o = smax(soft_o, np.maximum(1.5062 - z, z - 1.552), 0.002)
    epig = ell(x, y, z, (0.0, -0.045, 1.551), (0.010, 0.0035, 0.008))
    soft_o = smin(soft_o, epig, 0.003)
    # airway: subglottis -> glottis slit (rima ~ 8 x 16 mm) -> vestibule; closed at the inlet
    lz = np.clip((z - 1.505) / 0.050, 0, 1)
    rx = 0.0080 - 0.0045 * np.exp(-((z - 1.527) / 0.0035) ** 2)
    ry = 0.0085 - 0.0010 * np.exp(-((z - 1.527) / 0.0035) ** 2)
    lumen = np.sqrt((x / rx) ** 2 + ((y - (-0.031 - 0.004 * lz)) / ry) ** 2) - 1.0
    lumen = np.maximum(lumen * 0.006, np.maximum(1.5075 - z, z - 1.545))
    return thyroid, cric, soft_o, lumen


def larynx_sdf(x, y, z):
    th, cr, so, lu = _larynx_parts(x, y, z)
    d = smin(smin(so, cr, 0.0015), th, 0.0015)
    return np.maximum(d, -lu)


def larynx_sub(v):
    th, cr, so, lu = _larynx_parts(v[:, 0], v[:, 1], v[:, 2])
    ids = np.full(len(v), LARYNX_SUB["soft"], np.int32)
    ids = np.where(cr < 0.0006, LARYNX_SUB["cricoid"], ids)
    ids = np.where(th < 0.0006, LARYNX_SUB["thyroid_cartilage"], ids)
    ids = np.where(np.abs(lu) < 0.0008, LARYNX_SUB["lumen"], ids)
    return ids


# ===========================================================================
# Oesophagus (collapsed, slit lumen) and thyroid
# ===========================================================================
OESO_PTS = [(0.000, -0.0125, 1.506), (0.004, 0.012, 1.450), (0.000, 0.022, 1.415), (0.002, 0.024, 1.355),
            (0.012, 0.012, 1.310), (0.022, -0.008, 1.280), (0.027, -0.014, 1.264)]


def _oeso_fields(x, y, z):
    P = dense(OESO_PTS, 0.002)
    d, t, idx = polyline_param(x, y, z, P)
    seg = np.diff(P, axis=0)
    T = seg / np.linalg.norm(seg, axis=1, keepdims=True)
    Ti = T[idx]
    foot = P[idx] + ((np.stack([x, y, z], 1) - P[idx]) * Ti).sum(1, keepdims=True) * Ti
    rel = np.stack([x, y, z], 1) - foot
    lat = np.tile([1.0, 0.0, 0.0], (len(x), 1)) - Ti[:, :1] * Ti
    lat /= np.linalg.norm(lat, axis=1, keepdims=True)
    ap = np.cross(Ti, lat)
    u, w = (rel * lat).sum(1), (rel * ap).sum(1)
    ra = 0.0100 + 0.0012 * t                                   # 20 x 15 mm collapsed, wider distally
    rb = 0.0072 + 0.0010 * t
    outer = (np.sqrt((u / ra) ** 2 + (w / rb) ** 2) - 1.0) * rb
    lum = (np.sqrt((u / (ra - 0.0038)) ** 2 + (w / 0.0016) ** 2) - 1.0) * 0.0016
    ends = np.maximum(((np.stack([x, y, z], 1) - P[0]) @ unit(P[0] - P[1])),
                      ((np.stack([x, y, z], 1) - P[-1]) @ unit(P[-1] - P[-2])))
    outer = smax(outer, ends, 0.002)
    lum = np.maximum(lum, ends + 0.003)
    return outer, lum


def oesophagus_outer(x, y, z):
    o, _l = _oeso_fields(x, y, z)
    o = carve(o, _AIRB(x, y, z), 0.0015, 0.002)
    return carve(o, spine_sdf(x, y, z), 0.002, 0.002)


def oesophagus_sdf(x, y, z):
    o, l = _oeso_fields(x, y, z)
    o = carve(o, _AIRB(x, y, z), 0.0015, 0.002)
    o = carve(o, spine_sdf(x, y, z), 0.002, 0.002)
    o = carve(o, _LARB(x, y, z), 0.0012, 0.002)
    o = carve(o, _PERI(x, y, z), 0.0015, 0.003)
    o = carve(o, vessel_sdf(["A02", "A20"])(x, y, z), 0.0015, 0.002)
    return np.maximum(o, -l)


def oesophagus_sub(v):
    _o, l = _oeso_fields(v[:, 0], v[:, 1], v[:, 2])
    return np.where(np.abs(l) < 0.0008, 2, 1).astype(np.int32)


def thyroid_sdf(x, y, z):
    """Thyroid: two lobes (50 x 20 x 18 mm) and the isthmus over tracheal rings 2-4, hugging the
    trachea (impression) with the carotid sheath lateral [R05 §10.1]."""
    d = None
    for sx in (1.0, -1.0):
        lobe = ell(x * sx, y, z, (0.0215, -0.0265, 1.505), (0.0095, 0.0090, 0.0250))
        pole = ell(x * sx, y, z, (0.0170, -0.0245, 1.524), (0.0055, 0.0055, 0.0070))
        lobe = smin(lobe, pole, 0.006)
        d = lobe if d is None else smin(d, lobe, 0.002)
    isth = ell(x, y, z, (0.0, -0.0415, 1.492), (0.012, 0.0032, 0.0085))
    d = smin(d, isth, 0.005)
    d = carve(d, _AIRB(x, y, z), 0.0012, 0.002)
    d = carve(d, _LARB(x, y, z), 0.0012, 0.002)
    d = carve(d, _OESB(x, y, z), 0.0012, 0.002)
    return carve(d, vessel_sdf(["A04_L", "A04_R", "V01_L", "V01_R"])(x, y, z), 0.0010, 0.002)


# ===========================================================================
# Lungs and pleura [R05 §10.5]
# ===========================================================================
HILUM = {"R": np.array([-0.050, 0.020, 1.380]), "L": np.array([0.050, 0.025, 1.388])}
LUNG_SUB = {"R": {"upper": 1, "middle": 2, "lower": 3}, "L": {"upper": 1, "lower": 2}}


def _plane3(p1, p2, p3):
    p1, p2, p3 = (np.asarray(p, float) for p in (p1, p2, p3))
    n = unit(np.cross(p2 - p1, p3 - p1))
    return n, float(n @ p1)


def _fissures(side):
    """Oblique fissure (T3 spinous behind -> 5th rib laterally -> 6th costal cartilage in front) and the
    right horizontal fissure (4th costal cartilage -> meets the oblique at the MAL).  Planes (n, d),
    n pointing toward the upper lobe."""
    s = 1.0 if side == "L" else -1.0
    n, d = _plane3((s * 0.030, 0.085, 1.448), (s * 0.132, 0.020, 1.352), (s * 0.068, -0.078, 1.286))
    if n[2] < 0:
        n, d = -n, -d
    hor = None
    if side == "R":
        hn, hd = _plane3((-0.060, -0.080, 1.346), (-0.132, -0.005, 1.357), (-0.030, -0.040, 1.351))
        if hn[2] < 0:
            hn, hd = -hn, -hd
        hor = (hn, hd)
    return (n, d), hor


def _lung_raw(x, y, z, side):
    s = 1.0 if side == "L" else -1.0
    d = cage_sdf(x, y, z)
    zc = 1.405
    cap = ell(x, y, zc + np.maximum(z - zc, 0.0), (s * 0.048, 0.014, zc), (0.105, 0.115, 0.090))  # cupola 1.495
    d = smax(d, cap, 0.010)
    th, _r = _theta_r(x, y)
    base = np.maximum(0.0035 - dome_dist(x, y, z, max_slope=2.0), lung_border_z(th) - z)
    d = smax(d, base, 0.005)
    d = smax(d, 0.009 - s * x, 0.006)                                          # mediastinal pleura
    return d


def lung_fields(x, y, z, side):
    """(lung solid, lobe id per sample) for one side."""
    s = 1.0 if side == "L" else -1.0
    d = _lung_raw(x, y, z, side)
    d = carve(d, _PERI(x, y, z), 0.0020, 0.006)
    d = carve(d, spine_sdf(x, y, z), 0.004, 0.006)
    d = carve(d, _AIRB(x, y, z), 0.0025, 0.004)
    d = carve(d, _OESB(x, y, z), 0.0025, 0.004)
    d = carve(d, vessel_sdf(MEDIASTINAL_VESSELS, zmin=1.30)(x, y, z), 0.0020, 0.004)
    d = carve(d, ell(x, y, z, HILUM[side], (0.010, 0.014, 0.020)), 0.0, 0.006)   # hilar depression
    d = carve(d, _THYB(x, y, z), 0.0025, 0.003)
    d = carve(d, _RIBT(x, y, z), 0.0018, 0.004)                   # shallow rib impressions
    d = carve(d, _STERN(x, y, z), 0.0025, 0.004)
    d = carve(d, _PARAV(x, y, z), -0.0040, 0.004)                 # tips of transverse processes, rib necks
    # fissures: 2.8 mm clefts opening slightly at the surface, reaching to ~3 cm from the hilum
    (n, dd), hor = _fissures(side)
    P = np.stack([x, y, z], 1)
    hil = np.linalg.norm(P - HILUM[side], axis=1)
    pd = P @ n - dd
    open_ = np.clip(d + 0.006, 0.0, None) * 0.25
    obl = np.maximum(np.abs(pd) - 0.0014 - open_, 0.030 - hil)
    d = smax(d, -obl, 0.0008)
    lobe = np.where(pd > 0, LUNG_SUB[side]["upper"], LUNG_SUB[side]["lower"])
    if hor is not None:
        hn, hd = hor
        ph = P @ hn - hd
        hz = np.maximum(np.abs(ph) - 0.0014 - open_, np.maximum(0.028 - hil, -pd + 0.0014))
        d = smax(d, -hz, 0.0008)
        lobe = np.where((pd > 0) & (ph < 0), LUNG_SUB["R"]["middle"], lobe)
    return d, lobe.astype(np.int32)


def lung_sdf(side):
    return lambda x, y, z: lung_fields(x, y, z, side)[0]


def lung_sub(side):
    return lambda v: lung_fields(v[:, 0], v[:, 1], v[:, 2], side)[1]


def lung_box(side):
    s = 1.0 if side == "L" else -1.0
    xs = sorted([s * 0.004, s * 0.148])
    return np.array([xs[0], -0.100, 1.225]), np.array([xs[1], 0.105, 1.500])


# ===========================================================================
# Diaphragm [R05 §10.6]: domes, central tendon (trefoil), zone of apposition, crura, hiatuses
# ===========================================================================
def _tendon_mask(x, y):
    """Trefoil central tendon (1 inside)."""
    c = np.array([0.000, -0.020])
    lobes = [(0.000, -0.040, 0.030, 0.026), (-0.040, -0.005, 0.030, 0.030), (0.035, -0.005, 0.026, 0.026)]
    m = np.zeros_like(x)
    for cx, cy, rx, ry in lobes:
        m = np.maximum(m, 1.0 - sstep(0.8, 1.15, np.sqrt(((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2)))
    return m


def crura_sdf(x, y, z):
    """Crura: muscular bands down the front of L1-L3 (right longer), meeting over the aortic hiatus."""
    cr = None
    for sx, z_end in ((-1.0, 1.122), (1.0, 1.158)):
        c = chain(x, y, z, [(sx * 0.014, -0.018, 1.262), (sx * 0.016, -0.030, 1.205),
                            (sx * 0.014, -0.036, z_end)], [0.0055, 0.0060, 0.0040])
        cr = c if cr is None else np.minimum(cr, c)
    return carve(cr, spine_sdf(x, y, z), 0.0015, 0.002)


def diaphragm_fields(x, y, z):
    th, _r = _theta_r(x, y)
    top = dome_height(x, y)
    e = 0.0005
    gx = (dome_height(x + e, y) - top) / e
    gy = (dome_height(x, y + e) - top) / e
    tend = _tendon_mask(x, y)
    t = DIAPHRAGM_T * (1 - tend) + TENDON_T * tend
    omega = smax((z - top) / np.sqrt(1.0 + gx * gx + gy * gy), cage_sdf(x, y, z, inset=RIB_HALF_T + 0.0008),
                 0.004)
    sheet = np.abs(omega + 0.5 * t) - 0.5 * t
    sheet = smax(sheet, attach_z(th) - z, 0.003)
    d = smin(sheet, crura_sdf(x, y, z), 0.006)
    d = carve(d, _PERI(x, y, z), 0.0008, 0.002)
    # openings: IVC (T8, in the tendon), oesophagus (T10), aorta (T12, behind the median arcuate lig.)
    d = carve(d, vessel_sdf(["V10", "A20", "A21"])(x, y, z), 0.0010, 0.002)
    d = carve(d, _OESB(x, y, z), 0.0012, 0.002)
    d = carve(d, spine_sdf(x, y, z), 0.0025, 0.002)
    d = carve(d, _PARAV(x, y, z), 0.0020, 0.002)
    d = carve(d, _RIBT(x, y, z), 0.0015, 0.002)
    return d, tend


def diaphragm_sdf(x, y, z):
    return diaphragm_fields(x, y, z)[0]


def diaphragm_sub(v):
    _d, tend = diaphragm_fields(v[:, 0], v[:, 1], v[:, 2])
    return np.where(tend > 0.5, 2, 1).astype(np.int32)


def dome_dist(x, y, z, max_slope=None):
    """Signed distance-like height above the diaphragm's top surface (slope-normalised).  ``max_slope``
    clamps the correction: at the near-vertical rim the first-order estimate grossly underestimates the
    distance of points well above the dome."""
    top = dome_height(x, y)
    e = 0.0005
    gx = (dome_height(x + e, y) - top) / e
    gy = (dome_height(x, y + e) - top) / e
    g2 = gx * gx + gy * gy
    if max_slope is not None:
        g2 = np.minimum(g2, max_slope ** 2)
    return (z - top) / np.sqrt(1.0 + g2)


def under_diaphragm(x, y, z, gap=0.0035):
    """Distance-like term keeping abdominal organs under the diaphragm's lower surface, including where the
    diaphragm dips under the pericardium (the central tendon carries the heart)."""
    tend = _tendon_mask(x, y)
    t = DIAPHRAGM_T * (1 - tend) + TENDON_T * tend
    d = dome_dist(x, y, z) + t + gap
    d = smax(d, cage_sdf(x, y, z, inset=RIB_HALF_T + 0.0008 + DIAPHRAGM_T + gap), 0.004)   # costal part
    d = np.maximum(d, -(_PERI(x, y, z) - (t + gap + 0.0008)))
    return np.maximum(d, -(_CRURA(x, y, z) - gap))


# ===========================================================================
# Abdominal cavity (inside the abdominal wall), from the body skin stations of B1
# ===========================================================================
def abdominal_cavity(x, y, z):
    """Peritoneal cavity + retroperitoneum envelope: skin stations inset by the wall
    (front: skin 2 + fat 15 x fat% / 15 + rectus 10-12 mm; sides: obliques; back: the paraspinal
    muscles + quadratus lumborum, 50-70 mm to the kidneys) [RB §7.6]."""
    import body_skin as BS
    a, yf, yb, nf, nb = BS.torso_station(z)
    fat = 0.015 * BS.FAT_SCALE
    af = a - (0.002 + fat + 0.016) + 0.012 * sstep(1.12, 1.20, z)     # thin wall under the ribs
    front = yf + (0.002 + fat + 0.012)
    back = yb - 0.048
    cy = 0.5 * (front + back)
    ry = np.where(y < cy, cy - front, back - cy)
    n = np.where(y < cy, 2.6, 2.3)
    rr = (np.abs(x / af) ** n + np.abs((y - cy) / ry) ** n) ** (1.0 / n)
    return (rr - 1.0) * np.minimum(af, ry)


# ===========================================================================
# Kidneys (in perirenal fat) and adrenals [R05 §11.3]
# ===========================================================================
def _kidney_frame(side):
    p = OR.PRIMITIVES["kidney_" + side]
    return Frame(p["c"], p["u"], p["v"])


def kidney_sdf(side):
    F = _kidney_frame(side)

    def fn(x, y, z):
        a, b, c = F.local(x, y, z)
        # bean: ellipsoid 115 x 60 x 40 bent toward the hilum (+v = anteromedial), sinus notch
        bend = 0.18 * (a / 0.0575) ** 2 * 0.0060
        d = ell(a, b + bend, c, (0.0, 0.0, 0.0), (0.0570, 0.0305, 0.0205))
        lob = 0.0006 * fbm3(x, y, z, 0.020, 21 if side == "L" else 22, 1)
        d = d + lob
        sinus = ell(a, b, c, (0.0, 0.0300, 0.0), (0.0200, 0.0140, 0.0105))
        return smax(d, -sinus, 0.004)
    return fn


def kidney_sub(side):
    F = _kidney_frame(side)

    def fn(v):
        a, b, c = F.local(v[:, 0], v[:, 1], v[:, 2])
        return np.where(ell(a, b, c, (0.0, 0.0300, 0.0), (0.024, 0.018, 0.014)) < 0.0015, 2, 1).astype(np.int32)
    return fn


def kidney_fat_sdf(side):
    """Perirenal fat capsule (lean man 5-10 mm) filling the sinus, around the kidney."""
    k = kidney_sdf(side)
    F = _kidney_frame(side)

    def fn(x, y, z):
        a, b, c = F.local(x, y, z)
        d = ell(a, b, c, (0.002, -0.002, 0.0), (0.0635, 0.0360, 0.0265))
        d = smin(d, k(x, y, z) - 0.0050, 0.010)
        d = d + 0.0010 * fbm3(x, y, z, 0.018, 31 if side == "L" else 32, 2)
        d = carve(d, spine_sdf(x, y, z), 0.004, 0.004)
        return smax(d, abdominal_cavity(x, y, z) + 0.002, 0.004)
    return fn


def adrenal_sdf(side):
    """Left: crescent over the upper-medial pole; right: pyramid above the pole behind the IVC
    (5 x 3 x 0.6 cm, flattened; meshed at >= 5 mm thickness) [R05 §11.3]."""
    p = OR.PRIMITIVES["adrenal_" + side]
    kid = kidney_sdf(side)
    c = np.array(p["c"])

    def fn(x, y, z):
        cc = c + (np.array([0.001, 0.0, 0.0]) if side == "L" else 0.0)
        d = ell(x, y, z, cc, (0.0150, 0.0053, 0.0255) if side == "L" else (0.0125, 0.0045, 0.0215))
        d = smax(d, -(kid(x, y, z) - 0.0035), 0.004)
        if side == "R":
            d = carve(d, vessel_sdf(["V10"])(x, y, z), 0.0015, 0.002)
        return d
    return fn


# ===========================================================================
# Stomach (hollow, 3 mm wall, rugae), spleen, pancreas, gallbladder, liver
# ===========================================================================
STOMACH_PTS = [(0.032, -0.016, 1.262), (0.064, 0.002, 1.262), (0.076, -0.032, 1.212),
               (0.062, -0.056, 1.150), (0.040, -0.064, 1.124), (0.006, -0.070, 1.136),
               (-0.016, -0.064, 1.160), (-0.030, -0.058, 1.172)]
STOMACH_R = [0.018, 0.032, 0.034, 0.030, 0.027, 0.021, 0.0125, 0.0120]
STOMACH_WALL = 0.0023


def _stomach_outer_raw(x, y, z):
    d = chain(x, y, z, STOMACH_PTS, STOMACH_R, k=0.012)
    fundus = ell(x, y, z, (0.064, 0.003, 1.266), (0.032, 0.030, 0.032))
    d = smin(d, fundus, 0.010)
    pyl = np.exp(-(np.sum((np.stack([x, y, z], 1) - np.array([-0.020, -0.063, 1.163])) ** 2, 1)) / 0.004 ** 2)
    d = d - 0.002 * pyl                                                        # pyloric sphincter ring
    d = smax(d, under_diaphragm(x, y, z), 0.006)
    d = smax(d, abdominal_cavity(x, y, z) + 0.002, 0.006)
    return d


def stomach_outer(x, y, z):
    d = _STOM(x, y, z)
    d = carve(d, _OESB(x, y, z), 0.0025, 0.002)
    d = carve(d, _KFAT["L"](x, y, z), 0.0025, 0.004)
    d = carve(d, _ADRB_L(x, y, z), 0.0030, 0.003)
    return d


def stomach_fields(x, y, z):
    o = stomach_outer(x, y, z)
    rug = 0.0012 * sstep(0.2, 0.8, np.abs(fbm3(x * 2.2, y * 2.2, z * 0.55, 0.030, 41, 2)))
    lumen = o + STOMACH_WALL + rug
    return o, lumen


def stomach_sdf(x, y, z):
    o, l = stomach_fields(x, y, z)
    return np.maximum(o, -l)


def stomach_sub(v):
    o, l = stomach_fields(v[:, 0], v[:, 1], v[:, 2])
    return np.where(np.abs(l) < np.abs(o), 2, 1).astype(np.int32)


def spleen_sdf(x, y, z):
    """Spleen 12 x 7 x 3 cm under ribs 9-11: a lens moulded to the underside of the diaphragm (convex
    diaphragmatic surface), up to 30 mm thick, concave visceral surface against the stomach and kidney,
    notched superior border [R05 §11.2].  Footprint: the bible OBB (long axis along the 10th rib)."""
    p = OR.PRIMITIVES["spleen"]
    F = Frame(np.array(p["c"]), p["u"], p["v"])
    a, b, _c = F.local(x, y, z)
    r2 = (a / 0.066) ** 2 + ((b - 0.004) / 0.043) ** 2
    thick = 0.040 * np.sqrt(np.clip(1.0 - r2, 0.0, None)) + 0.004
    D = under_diaphragm(x, y, z, 0.0025)                         # < 0 inside the abdomen side
    d = smax(D, -D - thick, 0.004)
    d = smax(d, (np.sqrt(r2) - 1.0) * 0.040, 0.006)
    d = smax(d, np.abs(_c + 0.004) - 0.030, 0.006)                # only the posterolateral recess
    notch = 1e9
    for aa in (-0.030, -0.008, 0.016):
        notch = np.minimum(notch, ell(a, b, _c, (aa, 0.040, 0.000), (0.0030, 0.0080, 0.0200)))
    d = smax(d, -notch, 0.002)
    d = carve(d, _STOM(x, y, z), 0.0025, 0.004)
    d = carve(d, _KFAT["L"](x, y, z), 0.0020, 0.004)
    d = carve(d, _KID["L"](x, y, z), 0.0030, 0.004)
    return d


def pancreas_sdf(x, y, z):
    """Pancreas 14 cm, head 3 cm (in the duodenal C) -> neck -> body over L1 -> tail at the splenic
    hilum; lobulated [R05 §11.4]."""
    pts = np.array([(-0.038, -0.030, 1.150), (-0.028, -0.038, 1.164), (-0.005, -0.046, 1.180),
                    (0.025, -0.043, 1.192), (0.060, -0.018, 1.203), (0.088, 0.012, 1.214)])
    r = [0.0188, 0.0183, 0.0134, 0.0140, 0.0124, 0.0100]
    up, dn = pts + [0, 0, 0.0055], pts - [0, 0, 0.0055]
    up[0, 2] += 0.004
    dn[0, 2] -= 0.006
    d = smin(chain(x, y, z, up, r, k=0.010), chain(x, y, z, dn, r, k=0.010), 0.006)
    d = d + 0.0009 * fbm3(x, y, z, 0.010, 51, 2)
    d = carve(d, _STOM(x, y, z), 0.0015, 0.004)
    d = carve(d, _KFAT["L"](x, y, z), 0.0015, 0.003)
    d = carve(d, vessel_sdf(["A21", "V10", "A23", "A22", "A22_splenic", "V12_L", "V13", "A24_L"])(x, y, z),
              0.0015, 0.003)
    d = carve(d, spine_sdf(x, y, z), 0.003, 0.003)
    d = carve(d, _SPLB(x, y, z), 0.0025, 0.003)
    return smax(d, under_diaphragm(x, y, z), 0.003)


def gallbladder_sdf(x, y, z):
    """Pear-shaped gallbladder 8 x 3.5 cm, fundus at the tip of the right 9th costal cartilage
    (-0.075, -0.065, 1.190), neck up and back into the porta [R05 §11.1]."""
    p = OR.PRIMITIVES["gallbladder"]
    u = unit(p["u"])
    c = np.array(p["c"]) + np.array([0.0, 0.007, -0.019])      # fundus just below the liver's inferior border
    fundus = c - u * 0.0240
    neck = c + u * 0.0300
    d = capsule(x, y, z, fundus, neck, 0.0172, 0.0075)
    hook = capsule(x, y, z, neck, neck + np.array([0.010, 0.006, 0.004]), 0.0060, 0.0045)
    return smax(smin(d, hook, 0.004), under_diaphragm(x, y, z), 0.003)


LIVER_EDGE = [(-0.150, 1.138), (-0.130, 1.148), (-0.100, 1.168), (-0.075, 1.180), (-0.040, 1.186),
              (0.000, 1.188), (0.040, 1.200), (0.080, 1.212)]      # follows the right costal margin [R05 §11.1]


def _liver_base(x, y, z):
    ex = np.array(LIVER_EDGE)
    zedge = np.interp(x, ex[:, 0], ex[:, 1])
    slope = np.interp(x, [-0.10, -0.02, 0.02, 0.06], [0.08, 0.30, 0.75, 0.95])
    zlow = zedge + slope * np.clip(y + 0.080, 0.0, None)
    d = zlow - z
    d = smax(d, under_diaphragm(x, y, z, 0.0018), 0.004)
    d = smax(d, cage_sdf(x, y, z, inset=RIB_HALF_T + 0.0040), 0.010)
    d = smax(d, abdominal_cavity(x, y, z) + 0.002, 0.006)
    # left lobe tapers to a thin tip at the left MCL; nothing left-posterior (stomach/oesophagus)
    d = smax(d, x - 0.086 - 0.20 * np.clip(-y - 0.02, 0, None), 0.012)
    d = smax(d, y - (0.072 - 1.5 * np.clip(x, 0, None)), 0.010)
    # bare area / back: the liver reaches the posterior wall on the right only
    d = smax(d, y - 0.072, 0.008)
    # umbilical notch (ligamentum teres) at the inferior border
    d = carve(d, capsule(x, y, z, (0.010, -0.095, 1.190), (0.010, -0.040, 1.215), 0.004), 0.0, 0.003)
    return d


def liver_sdf(x, y, z):
    d = _LIVB(x, y, z)
    d = carve(d, _GALB(x, y, z), 0.0015, 0.004)
    d = carve(d, _KFAT["R"](x, y, z), 0.0015, 0.006)
    d = carve(d, _ADRB_R(x, y, z), 0.0015, 0.003)
    d = carve(d, _STOM(x, y, z), 0.0015, 0.006)
    d = carve(d, _OESB(x, y, z), 0.0015, 0.003)
    d = carve(d, vessel_sdf(["V10", "V13", "A21", "A20"])(x, y, z), 0.0012, 0.003)
    d = carve(d, spine_sdf(x, y, z), 0.004, 0.004)
    d = carve(d, _PARAV(x, y, z), 0.003, 0.004)
    d = carve(d, _RIBT(x, y, z), 0.0025, 0.004)
    d = carve(d, _PANB(x, y, z), 0.0015, 0.004)
    return d


def liver_sub(v):
    """1 right lobe, 2 left lobe (left of the falciform plane), 3 caudate (behind the porta)."""
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    ids = np.where(x > 0.008 - 0.25 * (y + 0.02), 2, 1)
    caud = ell(x, y, z, (-0.012, 0.030, 1.255), (0.018, 0.018, 0.035)) < 0.002
    return np.where(caud, 3, ids).astype(np.int32)


# ===========================================================================
# Bladder (hollow), greater omentum, peritoneal backing mass (no intestines)
# ===========================================================================
def bladder_fields(x, y, z):
    p = OR.PRIMITIVES["bladder_empty"]
    c = np.array(p["c"]) + np.array([0.0, 0.0, 0.004])
    o = ell(x, y, z, c, (0.0300, 0.0260, 0.0230))
    o = smax(o, (z - c[2]) - 0.012 - 0.35 * np.abs(y - c[1] + 0.004), 0.008)   # flattened (empty) dome
    lum = o + 0.0080                                            # contracted empty bladder: thick wall
    return o, lum


def bladder_sdf(x, y, z):
    o, l = bladder_fields(x, y, z)
    return np.maximum(o, -l)


def bladder_sub(v):
    o, l = bladder_fields(v[:, 0], v[:, 1], v[:, 2])
    return np.where(np.abs(l) < np.abs(o), 2, 1).astype(np.int32)


def omentum_sdf(x, y, z):
    """Greater omentum: a fatty apron 5-10 mm thick hanging from the greater curvature (z ~1.12) to
    z ~0.95, just inside the anterior abdominal wall: loose vertical drape folds, lobulated fat
    globules, an irregular free lower edge [RB §7.5, plan §8.2 B4]."""
    cav = abdominal_cavity(x, y, z)
    fold = 0.0022 * np.sin(x * 95.0 + 0.8) * sstep(1.10, 1.00, z) + 0.0012 * np.sin(x * 210.0 + 2.0)
    lob = 0.0011 * fbm3(x, y, z, 0.009, 62, 2)
    thick = np.maximum(0.0046 + 0.0012 * fbm3(x, y, z, 0.022, 61, 2) - lob, 0.0034)
    d = np.abs(cav + 0.0065 + fold) - thick
    import body_skin as BS
    _a, yf, yb, _nf, _nb = BS.torso_station(z)
    d = smax(d, y - (0.62 * yf + 0.38 * yb), 0.006)
    width = 0.100 + 0.012 * sstep(1.10, 1.02, z)
    d = smax(d, np.abs(x) - width, 0.010)
    top = 1.118 - 0.020 * sstep(0.00, 0.10, -x) + 0.012 * sstep(0.02, 0.09, x)
    bottom = 0.958 + 0.010 * np.sin(x * 48.0 + 1.3) + 0.006 * fbm3(x, y, z, 0.030, 63, 1) \
        + 0.030 * sstep(0.06, 0.11, np.abs(x))
    d = smax(d, np.maximum(z - top, bottom - z), 0.008)
    d = carve(d, _STOM(x, y, z), 0.0015, 0.004)
    d = carve(d, _GALB(x, y, z), 0.0015, 0.004)
    d = carve(d, _LIVB(x, y, z), 0.0015, 0.004)
    return d


def bowel_filler_sdf(x, y, z):
    """Peritoneal backing mass: fills the abdominal cavity the intestines would occupy (below the
    liver, stomach and spleen; in front of the kidneys, great vessels and spine; above the bladder).
    A smooth dark mass with shallow undulations - NOT modelled intestines (user scope)."""
    d = abdominal_cavity(x, y, z) + 0.0015
    d = smax(d, z - 1.205, 0.012)
    d = smax(d, under_diaphragm(x, y, z, 0.0045), 0.006)
    d = smax(d, 0.925 - z, 0.012)
    # pelvic inlet / iliac fossae narrowing
    wmax = np.interp(z, [0.92, 0.99, 1.07, 1.20], [0.060, 0.085, 0.118, 0.125])
    d = smax(d, np.abs(x) - wmax, 0.010)
    d = d + 0.0015 * fbm3(x, y, z, 0.045, 71, 2)
    d = carve(d, _OMEB(x, y, z), 0.0030, 0.004)
    d = carve(d, _LIVB(x, y, z), 0.0035, 0.008)
    d = carve(d, _STOM(x, y, z), 0.0035, 0.008)
    d = carve(d, _GALB(x, y, z), 0.0035, 0.004)
    d = carve(d, _SPLB(x, y, z), 0.0035, 0.004)
    d = carve(d, _PANB(x, y, z), 0.0035, 0.004)
    for sd in ("L", "R"):
        d = carve(d, _KFAT[sd](x, y, z), 0.0035, 0.006)
    d = carve(d, _BLAB(x, y, z), 0.0020, 0.006)
    d = carve(d, vessel_sdf(ABDOMINAL_VESSELS + ["A25_L", "A25_R", "V14_L", "V14_R"])(x, y, z), 0.0020, 0.006)
    d = carve(d, spine_sdf(x, y, z) - 0.010, 0.002, 0.010)          # + psoas bulk beside the column
    sacrum = ell(x, y, z, (0.0, 0.036, 0.975), (0.056, 0.034, 0.058))  # sacral promontory and ala
    d = carve(d, sacrum, 0.004, 0.006)
    return d


# ===========================================================================
# Meshing: SDF -> closed triangle mesh (surface nets + projection), cleanup, decimation
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
    for _ in range(2000):
        m = np.minimum(lab[e[:, 0]], lab[e[:, 1]])
        new = lab.copy()
        np.minimum.at(new, e[:, 0], m)
        np.minimum.at(new, e[:, 1], m)
        new = new[new]
        if np.array_equal(new, lab):
            break
        lab = new
    return lab


def drop_crumbs(v, f, min_verts=40):
    """Remove tiny islands (surface-net crumbs at thin features)."""
    if len(f) == 0:
        return v, f
    lab = islands(len(v), f)
    ids, cnt = np.unique(lab, return_counts=True)
    keepv = np.isin(lab, ids[cnt >= min_verts])
    return compact(v, f[keepv[f].all(1)])


def edge_stats(f):
    """(boundary edges, non-manifold edges) of a triangle list."""
    e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
    _u, cnt = np.unique(e, axis=0, return_counts=True)
    return int((cnt == 1).sum()), int((cnt > 2).sum())


# Kuhn subdivision of the unit cube into 6 tetrahedra along the main diagonal; consistent across
# neighbouring cubes, so marching tetrahedra gives a watertight, manifold surface.
_KUHN = []
for _perm in ((0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)):
    _c = [np.zeros(3, int)]
    for _ax in _perm:
        _n = _c[-1].copy()
        _n[_ax] = 1
        _c.append(_n)
    _KUHN.append(np.array(_c))
_KUHN = np.array(_KUHN)                      # (6 tets, 4 corners, 3)
_TET_EDGES = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]


def _mt_tables():
    """Per inside-mask (4 bits) the list of triangles as tet-edge indices."""
    edge_of = {tuple(sorted(e)): i for i, e in enumerate(_TET_EDGES)}
    tabs = []
    for m in range(16):
        ins = [c for c in range(4) if m >> c & 1]
        out = [c for c in range(4) if not m >> c & 1]
        tri = []
        if len(ins) in (1, 3):
            lone, others = (ins[0], out) if len(ins) == 1 else (out[0], ins)
            tri.append([edge_of[tuple(sorted((lone, o)))] for o in others])
        elif len(ins) == 2:
            a0, a1 = ins
            b0, b1 = out
            e00, e01 = edge_of[tuple(sorted((a0, b0)))], edge_of[tuple(sorted((a0, b1)))]
            e10, e11 = edge_of[tuple(sorted((a1, b0)))], edge_of[tuple(sorted((a1, b1)))]
            tri += [[e00, e01, e11], [e00, e11, e10]]
        tabs.append(tri)
    return tabs


_MT = _mt_tables()


def marching_tets(F, origin, h):
    """Watertight manifold triangle mesh of {F < 0} on a regular grid (outward normals)."""
    F = np.where(F == 0.0, 1e-9, F).astype(np.float64)
    nx, ny, nz = F.shape
    inside = F < 0
    m = np.array(F.shape) - 1
    cnt = np.zeros(m, np.uint8)
    for (i, j, k) in np.array([[a, b, c] for a in (0, 1) for b in (0, 1) for c in (0, 1)]):
        cnt += inside[i:i + m[0], j:j + m[1], k:k + m[2]]
    ci, cj, ck = np.nonzero((cnt > 0) & (cnt < 8))
    base = np.stack([ci, cj, ck], 1)
    V_list, T_list = [], []
    for t in range(6):
        corners = base[:, None, :] + _KUHN[t][None]                        # (N, 4, 3)
        gid = (corners[..., 0] * ny + corners[..., 1]) * nz + corners[..., 2]
        val = F[corners[..., 0], corners[..., 1], corners[..., 2]]
        mask = ((val < 0) * np.array([1, 2, 4, 8])).sum(1)
        for mcase in range(1, 15):
            sel = np.nonzero(mask == mcase)[0]
            if len(sel) == 0:
                continue
            for tri in _MT[mcase]:
                ids = []
                for ei in tri:
                    c0, c1 = _TET_EDGES[ei]
                    ids.append(np.stack([gid[sel, c0], gid[sel, c1]], 1))
                ids = np.stack(ids, 1)                                       # (S, 3, 2)
                # orientation: outward = from inside corners toward outside corners
                ins = ((val[sel] < 0)[..., None] * corners[sel]).sum(1) / np.maximum((val[sel] < 0).sum(1), 1)[:, None]
                ous = ((val[sel] >= 0)[..., None] * corners[sel]).sum(1) / np.maximum((val[sel] >= 0).sum(1), 1)[:, None]
                T_list.append((ids, sel, t, ous - ins))
    # unique edge vertices
    allpairs = np.concatenate([np.sort(x[0].reshape(-1, 2), 1) for x in T_list])
    N = nx * ny * nz
    key = allpairs[:, 0] * N + allpairs[:, 1]
    uk, inv = np.unique(key, return_inverse=True)
    g0, g1 = uk // N, uk % N
    def pos(g):
        k = g % nz
        j = (g // nz) % ny
        i = g // (ny * nz)
        return np.stack([i, j, k], 1).astype(np.float64), F[i, j, k]
    p0, f0 = pos(g0)
    p1, f1 = pos(g1)
    tt = np.clip(f0 / (f0 - f1), 0.0, 1.0)[:, None]
    verts = np.asarray(origin, float) + (p0 + (p1 - p0) * tt) * h
    faces = inv.reshape(-1, 3)
    # orient
    dirs = np.concatenate([np.repeat(x[3], 1, 0) for x in T_list])
    a, b, c = verts[faces[:, 0]], verts[faces[:, 1]], verts[faces[:, 2]]
    nrm = np.cross(b - a, c - a)
    flip = (nrm * dirs).sum(1) < 0
    faces[flip] = faces[flip][:, ::-1]
    good = (faces[:, 0] != faces[:, 1]) & (faces[:, 1] != faces[:, 2]) & (faces[:, 0] != faces[:, 2])
    return verts, faces[good]


def mesh_sdf(fn, box, h, project=1, min_verts=0):
    """Polygonise ``fn`` in ``box`` = (lo, hi) at spacing ``h`` -> (verts, tris), outward normals.

    Sparse grid sampling (head toolkit) + marching tetrahedra (watertight and manifold, keeps the
    sealed cavities of hollow organs, unlike a voxel remesh) + Newton projection onto the exact
    zero set; tiny crumbs removed."""
    A = _A()
    lo = np.asarray(box[0], float) - 2 * h
    hi = np.asarray(box[1], float) + 2 * h
    F, origin = A.sample_grid(fn, lo, hi, h)
    v, f = marching_tets(F, origin, h)
    del F
    if len(f) == 0:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    if project:
        v = A.project_to_surface(fn, v, h, project)
    v, f = weld(v, f, 1e-6)          # marching tets leaves near-duplicate vertices; they derail decimation
    return drop_crumbs(v, f, min_verts) if min_verts else (v, f)


def weld(v, f, eps=1e-7):
    """Merge coincident vertices, drop degenerate triangles."""
    key = np.round(v / eps).astype(np.int64)
    _u, idx, inv = np.unique(key, axis=0, return_index=True, return_inverse=True)
    f2 = inv.ravel()[f]
    ok = (f2[:, 0] != f2[:, 1]) & (f2[:, 1] != f2[:, 2]) & (f2[:, 0] != f2[:, 2])
    return compact(v[idx], f2[ok])


def split_nonmanifold(v, f):
    """Make a surface-nets mesh manifold without opening it: at every vertex of a non-manifold edge
    (two sheets touching in one cell) the incident triangles are grouped into fans connected through
    manifold edges, and each fan gets its own copy of the vertex.  The sheets then only touch
    (coincident vertices) and quadric decimation no longer stalls there."""
    f = np.asarray(f, np.int64)
    for _it in range(3):
        e = np.sort(np.concatenate([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]]), axis=1)
        key = e[:, 0] * (len(v) + 1) + e[:, 1]
        uk, inv, cnt = np.unique(key, return_inverse=True, return_counts=True)
        ecount = cnt[inv].reshape(3, -1).T                       # per face, per edge (01, 12, 20)
        badv = np.unique(e[cnt[inv] > 2].ravel())
        if len(badv) == 0:
            break
        isbad = np.zeros(len(v), bool)
        isbad[badv] = True
        faces_of = {}
        for ti in np.nonzero(isbad[f].any(1))[0]:
            for k in range(3):
                if isbad[f[ti, k]]:
                    faces_of.setdefault(int(f[ti, k]), []).append(int(ti))
        newv = [v]
        nv = len(v)
        f = f.copy()
        for vi, tris in faces_of.items():
            parent = {t: t for t in tris}

            def find(t):
                while parent[t] != t:
                    parent[t] = parent[parent[t]]
                    t = parent[t]
                return t
            # union faces sharing a manifold edge through vi
            owner = {}
            for t in tris:
                row = f[t]
                for k in range(3):
                    a_, b_ = row[k], row[(k + 1) % 3]
                    if vi not in (a_, b_) or ecount[t, k] != 2:
                        continue
                    other = int(b_ if a_ == vi else a_)
                    if other in owner:
                        ra, rb = find(owner[other]), find(t)
                        if ra != rb:
                            parent[ra] = rb
                    else:
                        owner[other] = t
            groups = {}
            for t in tris:
                groups.setdefault(find(t), []).append(t)
            if len(groups) < 2:
                continue
            for gi, (_r, ts) in enumerate(sorted(groups.items())):
                if gi == 0:
                    continue
                newv.append(v[vi][None])
                for t in ts:
                    f[t][f[t] == vi] = nv
                nv += 1
        v = np.vstack(newv)
    return v, f


def decimate_arrays(v, f, target, _depth=0):
    """Quadric collapse (Blender DECIMATE) to ~target triangles, in passes of at most 5x (a single extreme
    ratio collapses small closed shells inward: -24 % volume on a 60 mm bladder at 74k -> 300)."""
    import bpy
    if target <= 0 or len(f) <= target:
        return v, f
    while _depth == 0 and len(f) > 5 * target:
        n0 = len(f)
        v, f = decimate_arrays(v, f, max(target, len(f) // 5), _depth=1)
        if len(f) >= 0.9 * n0:
            break
    if _depth == 0:
        v, f = split_nonmanifold(v, f)
    me = gbc.mesh_from_arrays("_b4_dec", v, f, smooth=False)
    ob = bpy.data.objects.new("_b4_dec", me)
    bpy.context.scene.collection.objects.link(ob)
    mod = ob.modifiers.new("dec", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.002, target / len(f))
    mod.use_collapse_triangulate = True
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    v2, f2 = gbc.mesh_arrays(me2)
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.meshes.remove(me)
    bpy.data.meshes.remove(me2)
    v2, f2 = compact(v2, f2) if len(f2) else (v2, f2)
    if len(f2) > 1.25 * target and _depth < 3:
        v2, f2 = weld(v2, f2)
        return decimate_arrays(v2, f2, target, _depth + 1)
    return v2, f2


def close_holes(v, f):
    """Fill the few small boundary loops decimation can leave (bmesh holes_fill), so every organ surface is
    closed (plan §3.3.6 renders back faces as the cut interior)."""
    be, _nm = edge_stats(f)
    if be == 0:
        return v, f
    import bmesh
    me = gbc.mesh_from_arrays("_b4_holes", v, f, smooth=False)
    bm = bmesh.new()
    bm.from_mesh(me)
    edges = [e for e in bm.edges if e.is_boundary]
    bmesh.ops.holes_fill(bm, edges=edges, sides=0)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.to_mesh(me)
    bm.free()
    v2, f2 = gbc.mesh_arrays(me)
    import bpy
    bpy.data.meshes.remove(me)
    return v2, f2


def decimate_components(v, f, target, min_faces=40):
    """Decimate every connected surface separately with a budget proportional to its area (so the inner
    lumen / cavity surfaces of hollow organs keep their share and the wall never collapses)."""
    lab = islands(len(v), f)
    fl = lab[f[:, 0]]
    comps = [c for c in np.unique(fl) if (fl == c).sum() >= min_faces]
    areas = {c: mesh_area(v, f[fl == c]) for c in comps}
    tot = sum(areas.values()) or 1.0
    comps = [c for c in comps if areas[c] >= 0.004 * tot]          # drop carving crumbs
    tot = sum(areas[c] for c in comps) or 1.0
    vs, fs, off = [], [], 0
    for c in comps:
        vv, ff = compact(v, f[fl == c])
        vv, ff = close_holes(*decimate_arrays(vv, ff, max(20, int(round(target * areas[c] / tot)))))
        vs.append(vv)
        fs.append(ff + off)
        off += len(vv)
    if not vs:
        return np.zeros((0, 3)), np.zeros((0, 3), np.int64)
    return np.vstack(vs), np.vstack(fs)


def mesh_volume(v, f):
    """Signed volume (m^3) of a closed triangle mesh (cavities with inward normals subtract)."""
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)


def mesh_area(v, f):
    a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
    return float(0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1).sum())


# ---------------------------------------------------------------------------
# Box-gated neighbour fields for carving (evaluated only near their organ)
# ---------------------------------------------------------------------------
def _pbox(c, half):
    c = np.asarray(c, float)
    return c - np.asarray(half), c + np.asarray(half)


_PERI = boxed(pericardium_sdf, heart_box()[0] - 0.012, heart_box()[1] + 0.012)
_STOM = boxed(_stomach_outer_raw, (-0.060, -0.110, 1.070), (0.130, 0.060, 1.320))
_KFAT = {sd: boxed(kidney_fat_sdf(sd), *_pbox(OR.PRIMITIVES["kidney_" + sd]["c"], (0.060, 0.060, 0.085)))
         for sd in ("L", "R")}
_KID = {sd: boxed(kidney_sdf(sd), *_pbox(OR.PRIMITIVES["kidney_" + sd]["c"], (0.050, 0.050, 0.075)))
        for sd in ("L", "R")}
_THYB = boxed(thyroid_sdf, (-0.040, -0.055, 1.465), (0.040, -0.008, 1.550))
_CRURA = boxed(crura_sdf, (-0.030, -0.050, 1.110), (0.030, -0.005, 1.275))
_LIVB = boxed(_liver_base, (-0.160, -0.110, 1.120), (0.110, 0.090, 1.340))
_SPLB = boxed(spleen_sdf, *_pbox(OR.PRIMITIVES["spleen"]["c"], (0.070, 0.070, 0.075)))
_PANB = boxed(pancreas_sdf, (-0.080, -0.080, 1.100), (0.120, 0.050, 1.250))
_GALB = boxed(gallbladder_sdf, (-0.100, -0.090, 1.150), (-0.020, 0.000, 1.250))
_OMEB = boxed(omentum_sdf, (-0.140, -0.130, 0.930), (0.140, 0.010, 1.140))
_AIRB = boxed(airway_outer, (-0.070, -0.050, 1.350), (0.075, 0.045, 1.520))
_OESB = boxed(lambda x, y, z: _oeso_fields(x, y, z)[0], (-0.030, -0.040, 1.240), (0.055, 0.050, 1.520))
_LARB = boxed(larynx_sdf, (-0.035, -0.070, 1.495), (0.035, -0.005, 1.570))
_ADRB_L = boxed(adrenal_sdf("L"), *_pbox(OR.PRIMITIVES["adrenal_L"]["c"], (0.025, 0.020, 0.035)))
_RIBT = rib_tubes_sdf
_STERN = boxed(sternum_sdf, (-0.040, -0.110, 1.260), (0.040, -0.030, 1.470))
_PARAV = paravertebral_sdf
_ADRB_R = boxed(adrenal_sdf("R"), *_pbox(OR.PRIMITIVES["adrenal_R"]["c"], (0.025, 0.020, 0.035)))
_BLAB = boxed(lambda x, y, z: bladder_fields(x, y, z)[0], (-0.045, -0.075, 0.860), (0.045, 0.010, 0.940))


# ===========================================================================
# Organ specs: what to mesh, where, how fine, how many LOD0 triangles
# ===========================================================================
def _box(c, half):
    c, half = np.asarray(c, float), np.asarray(half, float)
    return c - half, c + half


def _const(i):
    return lambda v: np.full(len(v), i, np.int32)


def organ_specs():
    """[(mesh key, organ id name, sdf, box, h (m), LOD0 tris, sub(v) -> ids)] in build order."""
    S = []
    S.append(("heart", "heart", heart_sdf, heart_box(), 0.0011, 3300, heart_sub))
    S.append(("pericardium", "pericardium", pericardium_sdf, (heart_box()[0] - 0.006, heart_box()[1] + 0.006),
              0.0020, 550, _const(1)))
    for sd, n in (("R", 1900), ("L", 1700)):
        S.append(("lung_" + sd, "lung_" + sd, lung_sdf(sd), lung_box(sd), 0.0017, n, lung_sub(sd)))
    S.append(("diaphragm", "diaphragm", diaphragm_sdf, (np.array([-0.150, -0.110, 1.100]),
                                                         np.array([0.150, 0.100, 1.345])), 0.0011, 1800,
              diaphragm_sub))
    S.append(("airway", "trachea", airway_sdf, (np.array([-0.055, -0.045, 1.360]), np.array([0.062, 0.035, 1.512])),
              0.00065, 1400, None))
    S.append(("larynx", "larynx", larynx_sdf, (np.array([-0.030, -0.066, 1.498]), np.array([0.030, -0.012, 1.565])),
              0.0006, 900, larynx_sub))
    S.append(("oesophagus", "oesophagus", oesophagus_sdf, (np.array([-0.020, -0.030, 1.250]),
                                                           np.array([0.045, 0.040, 1.512])), 0.0007, 800,
              oesophagus_sub))
    S.append(("thyroid", "thyroid", thyroid_sdf, (np.array([-0.036, -0.050, 1.470]), np.array([0.036, -0.012, 1.545])),
              0.0008, 480, _const(1)))
    S.append(("stomach", "stomach", stomach_sdf, (np.array([-0.055, -0.100, 1.080]), np.array([0.125, 0.055, 1.315])),
              0.0010, 2400, stomach_sub))
    S.append(("liver", "liver", liver_sdf, (np.array([-0.155, -0.100, 1.130]), np.array([0.100, 0.085, 1.335])),
              0.0020, 2000, liver_sub))
    S.append(("gallbladder", "gallbladder", gallbladder_sdf, _box((-0.058, -0.040, 1.205), (0.034, 0.038, 0.042)),
              0.0012, 250, _const(1)))
    S.append(("spleen", "spleen", spleen_sdf, _box(OR.PRIMITIVES["spleen"]["c"], (0.060, 0.060, 0.065)),
              0.0014, 500, _const(1)))
    for sd in ("L", "R"):
        c = OR.PRIMITIVES["kidney_" + sd]["c"]
        S.append(("kidney_" + sd, "kidney_" + sd, kidney_sdf(sd), _box(c, (0.045, 0.045, 0.068)), 0.0013, 550,
                  kidney_sub(sd)))
        S.append(("kidney_fat_" + sd, "kidney_" + sd, kidney_fat_sdf(sd), _box(c, (0.058, 0.055, 0.080)), 0.0020,
                  300, _const(3)))
        S.append(("adrenal_" + sd, "adrenal_" + sd, adrenal_sdf(sd), _box(OR.PRIMITIVES["adrenal_" + sd]["c"],
                                                                        (0.022, 0.014, 0.032)), 0.0008, 120,
                  _const(1)))
    S.append(("pancreas", "pancreas", pancreas_sdf, (np.array([-0.062, -0.070, 1.125]), np.array([0.105, 0.035, 1.235])),
              0.0012, 450, _const(1)))
    S.append(("bladder", "bladder", bladder_sdf, _box((0.0, -0.030, 0.900), (0.035, 0.032, 0.030)), 0.0010, 480,
              bladder_sub))
    S.append(("omentum", "omentum", omentum_sdf, (np.array([-0.130, -0.125, 0.940]), np.array([0.130, 0.000, 1.130])),
              0.0016, 750, _const(1)))
    S.append(("bowel_filler", "bowel_filler", bowel_filler_sdf, (np.array([-0.135, -0.120, 0.915]),
                                                                 np.array([0.135, 0.060, 1.215])), 0.0030, 400,
              _const(1)))
    return S


AIRWAY_ORGANS = ("trachea", "bronchus_R", "bronchus_L")


def airway_ids(v):
    """Organ id name and sub id per airway vertex (1 cartilage ring, 2 annular ligament, 3 membranous
    back wall, 4 lumen/mucosa)."""
    solid, lumen, part, ringm, backm = airway_fields(v[:, 0], v[:, 1], v[:, 2])
    names = np.array(AIRWAY_ORGANS)[part]
    sub = np.where(ringm > 0.5, 1, 2)
    sub = np.where(backm > 0.5, 3, sub)
    sub = np.where(np.abs(lumen) < np.abs(solid), 4, sub)
    return names, sub.astype(np.int32)


# ===========================================================================
# Meshing all organs (cached per process) and the Blender objects
# ===========================================================================
_MESHED = {}


def mesh_organs(q=None, only=None, log=True):
    """{key: dict(v, f, organ (N,), sub (N,), hr=(v, f), lod=(v, f))} for every organ spec."""
    q = quick() if q is None else q
    out = {}
    for key, oname, fn, box, h, tris, subfn in organ_specs():
        if only and key not in only:
            continue
        t0 = time.perf_counter()
        hh = min(h * QUICK_SCALE, max(h, THIN_HMAX.get(key, 9.0))) if q else h
        v, f = mesh_sdf(fn, box, hh)
        if len(f) == 0:
            raise RuntimeError(f"B4: organ {key} produced no surface (check its SDF and box)")
        hr = decimate_components(v, f, HR_FACTOR * tris)
        lod = decimate_components(*hr, tris)
        rec = dict(key=key, organ=oname, fn=fn, hr=hr, lod=lod, raw_tris=len(f),
                   raw_volume=mesh_volume(v, f), raw_bounds=(v.min(0), v.max(0)))
        for lvl in ("hr", "lod"):
            vv = rec[lvl][0]
            if key == "airway":
                names, sub = airway_ids(vv)
                oid = np.array([OR.ORGAN_BY_ID[n]["organ_id"] for n in names], np.int32)
            else:
                oid = np.full(len(vv), OR.ORGAN_BY_ID[oname]["organ_id"], np.int32)
                sub = subfn(vv) if subfn is not None else np.zeros(len(vv), np.int32)
            rec[lvl + "_organ"] = oid
            rec[lvl + "_sub"] = np.asarray(sub, np.int32)
        out[key] = rec
        if log:
            be, nm = edge_stats(lod[1])
            gbc.log(f"  B4 {key:14s} raw {len(f):7d}  hr {len(hr[1]):6d}  lod {len(lod[1]):5d} tris  "
                    f"vol {rec['raw_volume'] * 1e6:8.1f} mL  open/nm edges {be}/{nm}  "
                    f"{time.perf_counter() - t0:5.1f} s")
    _MESHED.update(out)
    return out


def _parts(meshed, level):
    import gb_geom as gg
    parts = []
    for key, rec in meshed.items():
        v, f = rec[level]
        parts.append(gg.part(v, f, 0, gb_organ=rec[level + "_organ"], gb_sub=rec[level + "_sub"]))
    return parts


# ---------------------------------------------------------------------------
# Shape keys (plan §5.6, §3.3.6; RB §7.5, R05 §10.6/§14)
# ---------------------------------------------------------------------------
SYSTOLE_RADIAL = 0.915            # ventricles: 0.925^2 x 0.96 axial = 0.82 -> -18 % volume (-15..-20 %)
SYSTOLE_AXIAL = 0.955
DIAPHRAGM_EXCURSION = 0.017       # quiet breathing 1.5-2 cm
LUNG_INHALE_RADIAL = 0.0          # outward expansion on top of the base descent (tuned: +10 % volume)
LUNG_BASE_DROP = 0.0155            # lung bases follow the domes (quiet breathing 1.5-2 cm)
LUNG_COLLAPSE_SCALE = 0.67        # 0.67^3 = 0.30 -> -70 % volume toward the hilum
ABDOMINAL_FOLLOW = {"liver": 1.0, "gallbladder": 1.0, "spleen": 1.0, "stomach": 0.9, "adrenal_L": 0.8,
                    "adrenal_R": 0.8, "kidney_L": 0.7, "kidney_R": 0.7, "pancreas": 0.6}


def organ_shape_keys(v, organ, sub):
    """Displacements (N, 3) for the six GB_Organs shape keys."""
    keys = {}
    oid = {o["id"]: o["organ_id"] for o in OR.ORGANS}
    # heart_systole: ventricles contract toward the long axis and shorten toward the base
    m = organ == oid["heart"]
    a, b, c = HEART_FRAME.local(v[:, 0], v[:, 1], v[:, 2])
    w = sstep(0.000, 0.026, a) * m
    new_a = a * (1 - w * (1 - SYSTOLE_AXIAL))
    new_b = b * (1 - w * (1 - SYSTOLE_RADIAL))
    new_c = c * (1 - w * (1 - SYSTOLE_RADIAL))
    newp = HEART_FRAME.world(np.stack([new_a, new_b, new_c], 1))
    keys["heart_systole"] = np.where(m[:, None], newp - v, 0.0)
    # lungs: inhale = base descends with the diaphragm + slight outward expansion (tuned to +10 %)
    for sd in ("L", "R"):
        m = organ == oid["lung_" + sd]
        d = np.zeros_like(v)
        low = sstep(1.42, 1.30, v[:, 2])
        d[:, 2] = -LUNG_BASE_DROP * low
        hil = HILUM[sd]
        radial = v - np.array([hil[0], hil[1], v[:, 2].mean()])
        radial[:, 2] = 0.0
        d += LUNG_INHALE_RADIAL * radial * (1 - 0.5 * low)[:, None]
        keys["lung_inhale_" + sd] = np.where(m[:, None], d, 0.0)
        keys["lung_collapse_" + sd] = np.where(m[:, None], (hil - v) * (1 - LUNG_COLLAPSE_SCALE), 0.0)
    # diaphragm_inhale: domes descend (fixed at the costal attachment); the upper abdominal organs
    # ride down with it (R05 §14), the backing mass and omentum are pushed down and forward
    d = np.zeros_like(v)
    th, _r = _theta_r(v[:, 0], v[:, 1])
    m = organ == oid["diaphragm"]
    d[:, 2] = np.where(m, -DIAPHRAGM_EXCURSION * sstep(attach_z(th) + 0.005, attach_z(th) + 0.045, v[:, 2]), 0.0)
    for name, f in ABDOMINAL_FOLLOW.items():
        mm = organ == oid[name]
        d[mm, 2] = -DIAPHRAGM_EXCURSION * f
    for name in ("bowel_filler", "omentum"):
        mm = organ == oid[name]
        w = sstep(0.93, 1.20, v[mm, 2])
        d[mm, 2] = -0.55 * DIAPHRAGM_EXCURSION * w
        d[mm, 1] = -0.30 * DIAPHRAGM_EXCURSION * w
    keys["diaphragm_inhale"] = d
    return keys


def add_shape_keys(obj, keys):
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    base = gbc.get_verts(obj.data)
    for name in gbc.SHAPE_KEYS["GB_Organs"]:
        kb = obj.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", (base + keys[name]).ravel())
        kb.value = 0.0
    obj.data.update()


def _finish(obj, atlas=True):
    """Codes UV (organ id, sub id), atlas UV, UV order, smooth shading, glTF extras."""
    import gb_geom as gg
    import placeholder as PH
    u = gbc.read_point_attr(obj, "gb_organ", 'INT')
    v = gbc.read_point_attr(obj, "gb_sub", 'INT')
    gbc.set_codes_uv(obj, u, v)
    if atlas:
        gg.smart_uv(obj, margin=0.003)
    PH.finish_uvs(obj)
    obj.data.shade_smooth()
    obj["gb_layer"] = gbc.LAYER_OF.get(obj.name, "organ")
    obj["gb_schema"] = 1
    obj["gb_status"] = "B4"


_LAST = {}


# ===========================================================================
# Entry points (organ_table v0 kept working while B4 builds the meshes)
# ===========================================================================
def build_organs():
    """GB_Organs (LOD0, exported, 6 shape keys) + GB_Organs_HR (bake source): every organ in one mesh,
    UV2 = (organ id, sub-part id).  Also keeps the measured per-organ data for ``organ_table``."""
    import gb_geom as gg
    with gbc.Timer("B4 organs: mesh"):
        meshed = mesh_organs()
    with gbc.Timer("B4 organs: objects"):
        obj = gg.object_from_parts("GB_Organs", _parts(meshed, "lod"))
        _finish(obj)
        v = gbc.get_verts(obj.data)
        org = gbc.read_point_attr(obj, "gb_organ", 'INT')
        sub = gbc.read_point_attr(obj, "gb_sub", 'INT')
        add_shape_keys(obj, organ_shape_keys(v, org, sub))
        hr = gg.object_from_parts("GB_Organs_HR", _parts(meshed, "hr"), slots=gbc.MATERIAL_SLOTS["GB_Organs"])
        _finish(hr, atlas=False)
    import json
    _LAST["measured"] = measure(meshed)
    obj["gb_b4_measured"] = json.dumps(gbc._clean(_LAST["measured"]), sort_keys=True)
    return {"GB_Organs": obj, "GB_Organs_HR": hr}


# per organ: bible mass (g) and the density used for the mesh mass estimate (lungs: FRC tissue + blood)
MASS_REF = {"heart": (320, 1.05), "lung_R": (550, 0.30), "lung_L": (480, 0.30), "liver": (1550, 1.05),
            "gallbladder": (40, 1.02), "spleen": (150, 1.05), "kidney_L": (150, 1.05), "kidney_R": (150, 1.05),
            "adrenal_L": (5, 1.05), "adrenal_R": (5, 1.05), "stomach": (150, 1.05), "pancreas": (115, 1.05),
            "bladder": (50, 1.05), "thyroid": (20, 1.05), "larynx": (30, 1.10), "omentum": (300, 0.93),
            "bowel_filler": (2200, 1.05)}
LUNG_FRC_L = {"lung_R": 1.80, "lung_L": 1.55}         # R05 §10.5 volumes at FRC
SUB_PARTS = {
    "heart": {"RA": 1, "RV": 2, "LA": 3, "LV": 4, "epicardial_fat": 5},
    "lung_R": {"upper": 1, "middle": 2, "lower": 3}, "lung_L": {"upper": 1, "lower": 2},
    "liver": {"right_lobe": 1, "left_lobe": 2, "caudate": 3},
    "kidney_L": {"kidney": 1, "hilum_sinus": 2, "perirenal_fat": 3},
    "kidney_R": {"kidney": 1, "hilum_sinus": 2, "perirenal_fat": 3},
    "stomach": {"serosa": 1, "mucosa_lumen": 2}, "bladder": {"serosa": 1, "mucosa_lumen": 2},
    "oesophagus": {"wall": 1, "lumen": 2}, "diaphragm": {"muscle": 1, "central_tendon": 2},
    "trachea": {"cartilage_ring": 1, "annular_ligament": 2, "membranous_wall": 3, "mucosa_lumen": 4},
    "bronchus_L": {"cartilage_ring": 1, "annular_ligament": 2, "membranous_wall": 3, "mucosa_lumen": 4},
    "bronchus_R": {"cartilage_ring": 1, "annular_ligament": 2, "membranous_wall": 3, "mucosa_lumen": 4},
    "larynx": {"thyroid_cartilage": 1, "cricoid": 2, "soft_tissue": 3, "lumen": 4},
}
CONTAINERS = {"pericardium": ["heart"], "kidney_L": ["kidney_L (perirenal fat sub 3 encloses sub 1-2)"],
              "kidney_R": ["kidney_R (perirenal fat sub 3 encloses sub 1-2)"]}


def measure(meshed):
    """Per organ (by organ id name): LOD0 triangles, volume, centroid, AABB, mass estimate vs the bible."""
    acc = {}
    for key, rec in meshed.items():
        v, f = rec["lod"]
        org = rec["lod_organ"]
        names = [o["id"] for o in OR.ORGANS]
        idmap = {o["organ_id"]: o["id"] for o in OR.ORGANS}
        for oid in np.unique(org):
            name = idmap[int(oid)]
            fm = (org[f] == oid).all(1)
            ff = f[fm]
            e = acc.setdefault(name, dict(tris=0, vol=0.0, cen=np.zeros(3), lo=np.full(3, 9.0), hi=np.full(3, -9.0),
                                          parts=[]))
            e["tris"] += int(len(ff))
            e["parts"].append(key)
            if key.startswith("kidney_fat"):
                continue                               # the fat capsule encloses the kidney: not tissue
            vol = mesh_volume(v, ff)
            a_, b_, c_ = v[ff[:, 0]], v[ff[:, 1]], v[ff[:, 2]]
            tv = np.einsum("ij,ij->i", a_, np.cross(b_, c_)) / 6.0
            cen = ((a_ + b_ + c_) / 4.0 * tv[:, None]).sum(0)
            e["vol"] += vol
            e["cen"] += cen
            vv = v[np.unique(ff)]
            e["lo"] = np.minimum(e["lo"], vv.min(0))
            e["hi"] = np.maximum(e["hi"], vv.max(0))
    out = {}
    for name, e in acc.items():
        vol_ml = e["vol"] * 1e6
        rec = {"tris": e["tris"], "volume_ml": round(vol_ml, 2),
               "centroid": (e["cen"] / e["vol"]).tolist() if e["vol"] > 0 else None,
               "aabb": [e["lo"].tolist(), e["hi"].tolist()], "mesh_parts": sorted(set(e["parts"]))}
        if name in MASS_REF:
            ref, rho = MASS_REF[name]
            rec["mass_g_est"] = round(vol_ml * rho, 1)
            rec["mass_g_bible"] = ref
            rec["density_g_ml"] = rho
        out[name] = rec
    return out


def _measured_from_scene():
    try:
        import bpy
        import json
        o = bpy.data.objects.get("GB_Organs")
        if o is not None and "gb_b4_measured" in o.keys():
            return json.loads(o["gb_b4_measured"])
    except Exception:
        pass
    return _LAST.get("measured")


def organ_table():
    """organs.json 'data' (plan §5.8): organ records with the bible hit and sub primitives, the
    measured mesh data (volume, centroid, AABB, mass estimate), sub-part ids, tubes, facts."""
    measured = _measured_from_scene() or {}
    organs = []
    for o in OR.ORGANS:
        ref = MASS_REF.get(o["id"])
        rec = {"id": o["id"], "organ_id": o["organ_id"], "mesh": "GB_Organs",
               "parent_bones": o["parent_bones"], "mass_g": ref[0] if ref else None,
               "compartment": o["compartment"], "hit_priority": o["hit_priority"],
               "surface_colour": o["surface_colour"], "interior_colour": o["interior_colour"],
               "hit": OR.organ_hit_primitives(o), "sub": OR.organ_sub_primitives(o),
               "sub_parts": SUB_PARTS.get(o["id"], {}), "blend_shapes": o["blend_shapes"]}
        if o.get("tube"):
            t = OR.TUBES[o["tube"]]
            rec["tube"] = {"id": o["tube"], "radius": t["radius"], "points": [list(p) for p in t["points"]]}
        if o["id"] in CONTAINERS:
            rec["encloses"] = CONTAINERS[o["id"]]
        if o["id"] in measured:
            rec["measured"] = measured[o["id"]]
        if o.get("note"):
            rec["note"] = o["note"]
        organs.append(rec)
    tubes = [{"id": k, "radius": v["radius"], "points": [list(p) for p in v["points"]]} for k, v in OR.TUBES.items()]
    return {"organs": organs, "tubes": tubes,
            "facts": {"heart": OR.HEART, "lungs": OR.LUNGS, "diaphragm": OR.DIAPHRAGM, "liver": OR.LIVER,
                      "spleen": OR.SPLEEN, "kidneys": OR.KIDNEYS, "omentum": OR.OMENTUM,
                      "lung_frc_l": LUNG_FRC_L},
            "density_g_cm3": OR.ORGAN_DENSITY_G_CM3,
            "blend_shape_notes": {
                "heart_systole": "ventricles -18 % volume (radial x0.925, axial x0.96); atria fixed",
                "lung_inhale_L/R": "base -1.7 cm with the diaphragm + 1.2 % outward; use with diaphragm_inhale",
                "lung_collapse_L/R": "x0.67 toward the hilum = -70 % volume (pneumothorax)",
                "diaphragm_inhale": "domes -1.7 cm (fixed at the costal attachment); liver, spleen, stomach, "
                                    "kidneys, adrenals, pancreas ride down 0.6-1.0 x; backing mass and omentum "
                                    "pushed down and forward"},
            "shapes": {"obb": "c = centre, size = full lengths along u, v, w = u x v",
                       "ellipsoid": "size = full diameters along u, v, w", "sphere": "size[0] = diameter",
                       "capsule": "size[0] = total length along u, size[1] = diameter"},
            "status": "B4" if measured else "B4 (no GB_Organs mesh in the scene: bible primitives only)"}


# ===========================================================================
# Test renders (plan §5.1: <= 640 px, <= 48 samples, denoised).  Render-only copies carry a colour
# attribute; the exported GB_Organs keeps its plain GBM_organ placeholder slot.
# ===========================================================================
RENDER_COLOURS = {
    "heart": "#6E2222", "pericardium": "#D6CCBE", "lung_L": "#D9918E", "lung_R": "#D9918E",
    "diaphragm": "#8E3230", "trachea": "#E4DDD0", "bronchus_L": "#E4DDD0", "bronchus_R": "#E4DDD0",
    "larynx": "#DCD2C4", "oesophagus": "#B86A60", "thyroid": "#8B3A2E", "stomach": "#CDA3A0",
    "liver": "#6A2A20", "gallbladder": "#4F6E3E", "spleen": "#5A2232", "kidney_L": "#6E2A26",
    "kidney_R": "#6E2A26", "adrenal_L": "#D9A441", "adrenal_R": "#D9A441", "pancreas": "#D8B49A",
    "bladder": "#D8B5A5", "omentum": "#E8C766", "bowel_filler": "#3A1414"}
SUB_COLOURS = {("heart", 5): "#E6C45A", ("diaphragm", 2): "#E4E0D8", ("kidney_L", 3): "#E8C766",
               ("kidney_R", 3): "#E8C766", ("kidney_L", 2): "#C9A56A", ("kidney_R", 2): "#C9A56A",
               ("stomach", 2): "#C4676B", ("bladder", 2): "#C98C84", ("oesophagus", 2): "#D9A9A0",
               ("trachea", 2): "#D9A6A0", ("trachea", 3): "#C98A84", ("trachea", 4): "#D98A8A",
               ("bronchus_L", 2): "#D9A6A0", ("bronchus_L", 4): "#D98A8A", ("bronchus_R", 2): "#D9A6A0",
               ("bronchus_R", 4): "#D98A8A", ("larynx", 3): "#C98A84", ("larynx", 4): "#D98A8A",
               ("larynx", 2): "#D8D2C8"}


def render_material():
    """Look-dev test material: colour attribute + fine mottling, anthracotic speckle mask, wet coat."""
    import bpy
    mat = bpy.data.materials.get("B4_render")
    if mat is not None:
        return mat
    mat = bpy.data.materials.new("B4_render")
    mat.use_nodes = True
    nt = mat.node_tree
    bs = nt.nodes["Principled BSDF"]
    col = nt.nodes.new("ShaderNodeAttribute")
    col.attribute_name = "b4_col"
    spk = nt.nodes.new("ShaderNodeAttribute")
    spk.attribute_name = "b4_speck"
    tc = nt.nodes.new("ShaderNodeTexCoord")
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 180.0
    noise.inputs["Detail"].default_value = 6.0
    nt.links.new(tc.outputs["Object"], noise.inputs["Vector"])
    mot = nt.nodes.new("ShaderNodeMix")
    mot.data_type = 'RGBA'
    mot.blend_type = 'MULTIPLY'
    mot.inputs["Factor"].default_value = 0.35
    nt.links.new(col.outputs["Color"], mot.inputs["A"])
    nt.links.new(noise.outputs["Color"], mot.inputs["B"])
    vor = nt.nodes.new("ShaderNodeTexVoronoi")
    vor.inputs["Scale"].default_value = 420.0
    nt.links.new(tc.outputs["Object"], vor.inputs["Vector"])
    ramp = nt.nodes.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.06
    ramp.inputs["From Max"].default_value = 0.16
    ramp.inputs["To Min"].default_value = 1.0
    ramp.inputs["To Max"].default_value = 0.0
    nt.links.new(vor.outputs["Distance"], ramp.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = 'MULTIPLY'
    nt.links.new(ramp.outputs["Result"], mul.inputs[0])
    nt.links.new(spk.outputs["Fac"], mul.inputs[1])
    dark = nt.nodes.new("ShaderNodeMix")
    dark.data_type = 'RGBA'
    dark.inputs["B"].default_value = gbc.hex_to_linear("#3A3A3A")
    nt.links.new(mul.outputs[0], dark.inputs["Factor"])
    nt.links.new(mot.outputs["Result"], dark.inputs["A"])
    nt.links.new(dark.outputs["Result"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.38
    for k, val in (("Coat Weight", 0.55), ("Coat Roughness", 0.12), ("Subsurface Weight", 0.10)):
        if k in bs.inputs:
            bs.inputs[k].default_value = val
    if "Subsurface Radius" in bs.inputs:
        bs.inputs["Subsurface Radius"].default_value = (0.003, 0.0012, 0.0008)
    return mat


def _render_copy(src, name, cut=None, hide_organs=()):
    """Render-only copy of GB_Organs with per-vertex colours; optionally drop faces beyond a plane
    (cut = (normal, d): keep n.x < d) and whole organs."""
    import bpy
    v, t = gbc.mesh_arrays(src.data)
    org = gbc.read_point_attr(src, "gb_organ", 'INT')
    sub = gbc.read_point_attr(src, "gb_sub", 'INT')
    idn = {o["id"]: o["organ_id"] for o in OR.ORGANS}
    keep = ~np.isin(org[t], [idn[h] for h in hide_organs]).any(1)
    t = t[keep]
    me = gbc.mesh_from_arrays(name, v, t)
    if cut is not None:                       # clean planar cut (bisect), keeps n.x < d
        import bmesh
        n, d = np.asarray(cut[0], float), cut[1]
        n = n / np.linalg.norm(n)
        bm = bmesh.new()
        bm.from_mesh(me)
        vi = bm.verts.layers.int.new("b4_src")
        for bv in bm.verts:
            bv[vi] = bv.index
        bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=tuple(n * d),
                               plane_no=tuple(n), clear_outer=True)
        # new vertices on the cut take the attributes of the nearest original vertex
        src = np.array([bv[vi] for bv in bm.verts])
        co = np.array([bv.co[:] for bv in bm.verts])
        bm.to_mesh(me)
        bm.free()
        from mathutils.kdtree import KDTree
        kd = KDTree(len(v))
        for i, p in enumerate(v):
            kd.insert(p, i)
        kd.balance()
        src = np.array([kd.find(c)[1] for c in co])
        org, sub, v = org[src], sub[src], co
    ob = bpy.data.objects.new(name, me)
    gbc.link(ob, "Stage")
    names = {o["organ_id"]: o["id"] for o in OR.ORGANS}
    col = np.zeros((len(v), 4), np.float32)
    col[:, 3] = 1
    rng = gbc.rng("viscera")
    for oid, nm in names.items():
        m = org == oid
        col[m, :3] = gbc.hex_to_linear(RENDER_COLOURS[nm])[:3]
        for (on, sid), hx in SUB_COLOURS.items():
            if on == nm:
                col[m & (sub == sid), :3] = gbc.hex_to_linear(hx)[:3]
    col[:, :3] *= (0.92 + 0.16 * rng.random(len(v)))[:, None]
    a = me.color_attributes.new("b4_col", 'FLOAT_COLOR', 'POINT')
    a.data.foreach_set("color", col.ravel())
    speck = np.isin(org, [idn["lung_L"], idn["lung_R"]]).astype(np.float32) * 0.8
    s = me.attributes.new("b4_speck", 'FLOAT', 'POINT')
    s.data.foreach_set("value", speck)
    me.materials.append(render_material())
    return ob


def _close_light(target, loc, energy=1.0):
    import bpy
    for nm, off, e, sz in (("B4_Key", (-0.8, -0.6, 0.9), 3.0, 0.5), ("B4_Fill", (0.9, -0.5, 0.2), 1.0, 0.8),
                           ("B4_Rim", (0.4, 1.0, 0.7), 2.0, 0.4)):
        L = bpy.data.objects.get(nm)
        if L is None:
            L = bpy.data.objects.new(nm, bpy.data.lights.new(nm, 'AREA'))
            gbc.link(L, "Stage")
        dist = float(np.linalg.norm(np.asarray(loc) - np.asarray(target)))
        L.data.energy = e * energy * (dist / 0.6) ** 2
        L.data.size = sz * dist / 0.6
        L.location = tuple(np.asarray(target) + np.asarray(off) * dist)
        gbc.look_at(L, target)


def render_organs(prefix="viscera", with_skeleton=True, samples=32):
    """renders/<prefix>_*.png: front (sac + apron), front opened, back, side, heart close-up and
    cut, thorax and abdomen cross-sections, organs inside the skeleton."""
    import bpy
    src = bpy.data.objects["GB_Organs"]
    scene = gbc.setup_stage(floor=False)
    for nm in ("GB_Key", "GB_Fill", "GB_Rim"):
        o = bpy.data.objects.get(nm)
        if o is not None:
            o.hide_render = True
    scene.world.node_tree.nodes["Background"].inputs[0].default_value = (0.012, 0.012, 0.014, 1.0)
    try:
        scene.view_settings.look = 'AgX - Base Contrast'
    except TypeError:
        pass
    shown = {o.name: o.hide_render for o in bpy.data.objects}
    for o in bpy.data.objects:
        if o.type == 'MESH':
            o.hide_render = True
    out = []

    def shot(name, loc, tgt, lens=55, res=(480, 600)):
        _close_light(tgt, loc)
        cam = gbc.add_camera("B4_Cam", loc, tgt, lens)
        out.append(gbc.render(os.path.join(gbc.RENDER_DIR, f"{prefix}_{name}.png"), cam, samples, res))

    def only(*objs):
        for o in bpy.data.objects:
            if o.type == 'MESH':
                o.hide_render = o not in objs
    c = np.array([0.0, -0.005, 1.215])
    full = _render_copy(src, "B4_r_full")
    only(full)
    shot("front", c + (0, -1.45, 0.05), c)
    shot("side", c + (-1.45, 0.0, 0.05), c)
    shot("back", c + (0, 1.45, 0.05), c)
    opened = _render_copy(src, "B4_r_open", hide_organs=("pericardium", "omentum", "bowel_filler", "diaphragm"))
    only(opened)
    shot("front_open", c + (0, -1.45, 0.05), c)
    shot("three_q_open", c + (-0.85, -1.18, 0.15), c)
    hc = np.array([0.020, -0.034, 1.335])
    heart = _render_copy(src, "B4_r_heart", hide_organs=[o["id"] for o in OR.ORGANS if o["id"] != "heart"])
    only(heart)
    shot("heart_front", hc + (0.02, -0.40, 0.03), hc, 70, (480, 480))
    W = HEART_FRAME.W
    heartcut = _render_copy(src, "B4_r_heartcut", cut=(W, float(W @ HEART_BASE) + 0.010),
                            hide_organs=[o["id"] for o in OR.ORGANS if o["id"] != "heart"])
    only(heartcut)
    shot("heart_cut", hc + np.array([-0.05, -0.40, 0.06]), hc, 70, (480, 480))
    for nm, z in (("section_T7", 1.352), ("section_L1", 1.192)):
        sec = _render_copy(src, f"B4_r_{nm}", cut=((0, 0, 1.0), z),
                           hide_organs=("omentum",) if z < 1.2 else ())
        only(sec)
        shot(nm, (0.0, -0.20, z + 0.55), (0.0, 0.0, z), 45, (560, 480))
    if with_skeleton and "GB_Skeleton" in bpy.data.objects:
        sk = bpy.data.objects["GB_Skeleton"]
        only(opened, sk)
        shot("in_skeleton", c + (-0.80, -1.30, 0.12), c)
    for o in bpy.data.objects:
        if o.name.startswith("B4_r_"):
            bpy.data.objects.remove(o, do_unlink=True)
        elif o.name in shown:
            o.hide_render = shown[o.name]
    return out


if __name__ == "__main__":
    import bpy
    t0 = time.time()
    gbc.reset_scene()
    gbc.collections()
    objs = build_organs()
    if "--render" in gbc.script_args():
        cache = gbc.stage_cache("skeleton", [os.path.join(gbc.HERE, "skeleton.py")],
                                extra="quick" if quick() else "full")
        if cache.hit:
            cache.load()
        render_organs()
    gbc.log(f"viscera: {gbc.tri_count(objs['GB_Organs'].data)} tris, {time.time() - t0:.1f} s")
