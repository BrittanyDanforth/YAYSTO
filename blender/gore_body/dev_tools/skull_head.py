"""Body-side facial skeleton, skull base, dentition and mandible (owners B3 skeleton / B2 mouth).  Fix round 3.

The head project's ``anatomy.skull_sdf`` is a vault with a solid midface block (a few round holes for the
sinuses) and ``anatomy.jaw_sdf`` a flat plank once its clamps are applied; its teeth have 4 mm roots that end in
the gums (critics round 2: 0 % of the root vertices inside bone, the lower arch floating in the mouth air, the
maxilla and skull base one solid slab with no air spaces, no ear canal, no infratemporal fossa).  The gore_head
files are read-only for the body team, so this module refines them in the body build (head frame, metres,
origin between the ear canals, face -Y, left +X; every function takes signed x and mirrors with |x|):

``tooth_frames_long(upper)``   the head's tooth frames with anatomical root lengths (RB/R05: upper incisors
                               13 mm, canines 17, premolars 14, molars 12-13; lower 12.5-16) [C]
``tooth_sdf_long(frame)``      head crown + body-side root(s): 1 root for incisors / canines / premolars,
                               2 (mesial + distal) for lower molars, 3 (2 buccal + palatal) for upper molars
``teeth_sdf(x, y, z, upper)``  union of one jaw's teeth;  ``socket_sdf`` = teeth grown by the 0.25 mm PDL
``gum_sdf(x, y, z, upper)``    the head's gum band, 8.5 mm tall (covers the alveolar crest down to the void floor)
``tongue_sdf(x, y, z)``        a tongue that fills the oral cavity proper (dorsum 1.5 mm under the palate)
``face_skull(x, y, z, base)``  refines a skull SDF: midface refill, then nasal cavity (bony septum, 3 turbinates
                               per side), maxillary sinuses (1.5-2 mm walls), ethmoid / sphenoid / mastoid air
                               cells (Voronoi porosity, 0.6-1 mm septa), external acoustic meatus (7 mm, 25 mm)
                               and tympanic cavity, infratemporal / temporal fossa (the zygomatic arch left as a
                               free 5-6 mm bridge, pterygoid plates kept), hard palate (4-6 mm) and the maxillary
                               alveolar process with real sockets, a raised middle-fossa roof over the TMJ / ear
``mandible_sdf(x, y, z)``      swept mandible: body 31 mm tall at the symphysis tapering to 25 mm at M2, 10-14 mm
                               thick, mental protuberance, ramus 30 x 52 mm, gonial angle ~122 deg, coronoid and
                               condyle separated by the sigmoid notch, alveolar process with sockets
``AIR_SPACES``                 analytic air volumes (bones.json 'air_spaces', for G3's wound shading)
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402


def _A():
    return gbc.import_head().anatomy


# ---------------------------------------------------------------------------
# small SDF helpers (numpy, arrays)
# ---------------------------------------------------------------------------
def smin(a, b, k):
    k = np.maximum(k, 1e-9)
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * h * k * (1.0 / 6.0)


def smax(a, b, k):
    return -smin(-a, -b, k)


def sstep(e0, e1, x):
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def ell(x, y, z, c, r):
    """Ellipsoid (IQ bound)."""
    u, v, w = (x - c[0]) / r[0], (y - c[1]) / r[1], (z - c[2]) / r[2]
    k0 = np.sqrt(u * u + v * v + w * w)
    k1 = np.sqrt((u / r[0]) ** 2 + (v / r[1]) ** 2 + (w / r[2]) ** 2) + 1e-12
    return k0 * (k0 - 1.0) / k1


def capsule(x, y, z, a, b, ra, rb=None):
    rb = ra if rb is None else rb
    a = np.asarray(a, float)
    ba = np.asarray(b, float) - a
    dx, dy, dz = x - a[0], y - a[1], z - a[2]
    h = np.clip((dx * ba[0] + dy * ba[1] + dz * ba[2]) / float(ba @ ba), 0.0, 1.0)
    ex, ey, ez = dx - ba[0] * h, dy - ba[1] * h, dz - ba[2] * h
    return np.sqrt(ex * ex + ey * ey + ez * ez) - (ra + (rb - ra) * h)


def rbox(x, y, z, lo, hi, r=0.0):
    """Rounded axis-aligned box between lo and hi (corner radius r)."""
    c = 0.5 * (np.asarray(lo) + np.asarray(hi))
    h = 0.5 * (np.asarray(hi) - np.asarray(lo)) - r
    qx, qy, qz = np.abs(x - c[0]) - h[0], np.abs(y - c[1]) - h[1], np.abs(z - c[2]) - h[2]
    out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
    return out + np.minimum(np.maximum(qx, np.maximum(qy, qz)), 0.0) - r


def _hash3(ix, iy, iz, seed):
    """Deterministic per-cell pseudo-random vector in [0, 1)^3."""
    h = (ix * 73856093) ^ (iy * 19349663) ^ (iz * 83492791) ^ (seed * 2654435761)
    h = h.astype(np.int64) & 0x7FFFFFFF
    out = []
    for k in range(3):
        h = (h * 1103515245 + 12345 + k * 977) & 0x7FFFFFFF
        out.append((h % 10007) / 10007.0)
    return np.stack(out, -1)


def cell_walls(x, y, z, size, seed, jitter=0.75):
    """Distance (m) from each point to the nearest Voronoi cell wall of a jittered grid of cell ``size``
    (the bisector plane of the two nearest cell sites).  Small = on a septum; air cells are where it exceeds
    half the septum thickness.  Deterministic (plan §5.1)."""
    p = np.stack([x, y, z], -1) / size
    c = np.floor(p).astype(np.int64)
    n = len(p)
    d1 = np.full(n, np.inf)
    d2 = np.full(n, np.inf)
    q1 = np.zeros((n, 3))
    q2 = np.zeros((n, 3))
    for dx in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dz in (-1, 0, 1):
                cc = c + np.array([dx, dy, dz])
                q = cc + 0.5 + jitter * (_hash3(cc[:, 0], cc[:, 1], cc[:, 2], seed) - 0.5)
                d = np.sum((p - q) ** 2, -1)
                m1 = d < d1
                m2 = (~m1) & (d < d2)
                d2 = np.where(m1, d1, np.where(m2, d, d2))
                q2 = np.where(m1[:, None], q1, np.where(m2[:, None], q, q2))
                d1 = np.where(m1, d, d1)
                q1 = np.where(m1[:, None], q, q1)
    mid = 0.5 * (q1 + q2)
    nrm = q2 - q1
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    return np.sum((mid - p) * nrm, -1) * size


# ===========================================================================
# Dentition: anatomical root lengths [R05 / dental anatomy tables, C]
# ===========================================================================
ROOT_MM = {True: {"I1": 13.0, "I2": 13.0, "C": 17.0, "P1": 14.0, "P2": 14.0, "M1": 12.5, "M2": 12.0},
           False: {"I1": 12.5, "I2": 14.0, "C": 16.0, "P1": 14.0, "P2": 14.5, "M1": 14.0, "M2": 13.0}}
PDL = 0.00025                   # periodontal ligament space around every root (socket = tooth + PDL)
CREST_BELOW_CEJ = 0.0017        # alveolar crest 1.5-2 mm apical to the cemento-enamel junction


def tooth_frames_long(upper):
    """The head's tooth frames (fdi, kind, (W, D, Hc, Hr), CEJ origin, X, Y, Z) with Hr = ROOT_MM x TOOTH_SCALE."""
    A = _A()
    out = []
    for fdi, kind, (W, D, Hc, _hr), o, X, Y, Z in A.tooth_frames(upper):
        out.append((fdi, kind, (W, D, Hc, ROOT_MM[upper][kind] * A.TOOTH_SCALE), o, X, Y, Z))
    return out


def _molar_roots(u, v, h, W, D, Hr, upper):
    """Molar roots in the tooth frame (h < 0 toward the apex): a root trunk to the furcation (~30 % of the root)
    that splits into 3 roots (upper: mesiobuccal, distobuccal, palatal) or 2 (lower: mesial, distal), diverging
    slightly and tapering to rounded apices."""
    A = _A()
    rn = np.clip(-h / Hr, 0.0, 1.0)
    w0, d0 = 0.40 * W, 0.41 * D
    trunk = A.box2(u, v, w0 * (1.0 - 0.2 * rn), d0 * (1.0 - 0.2 * rn), 0.6 * min(w0, d0))
    trunk = np.maximum(trunk, -h - 0.30 * Hr)
    if upper:
        roots = [(0.45, 0.40, 0.42, 0.40), (-0.45, 0.40, 0.40, 0.38), (0.0, -0.55, 0.46, 0.44)]
    else:
        roots = [(0.52, 0.0, 0.40, 0.72), (-0.52, 0.0, 0.38, 0.70)]
    d = trunk
    for cu, cv, fw, fd in roots:
        spread = 1.0 + 0.35 * rn
        t = 1.0 - 0.6 * rn ** 1.2
        d = np.minimum(d, A.ellipse2(u - cu * w0 * spread, v - cv * d0 * spread, w0 * fw * t, d0 * fd * t))
    d = smax(d, h, 0.0006)                                       # only below the CEJ
    return smax(d, -Hr - h, 0.0012)                              # rounded apices


def tooth_sdf_long(frame, upper):
    """(fn(x, y, z), lo, hi) of one tooth (left side, |x|): the head's crown and, for incisors, canines and
    premolars, the head's tapered root profile at the anatomical length; molars get 2-3 separate roots."""
    A = _A()
    fdi, kind, (W, D, Hc, Hr), o, X, Y, Z = frame

    def fn(x, y, z):
        dx, dy, dz = x - o[0], y - o[1], z - o[2]
        u = dx * X[0] + dy * X[1] + dz * X[2]
        v = dx * Y[0] + dy * Y[1] + dz * Y[2]
        h = dx * Z[0] + dy * Z[1] + dz * Z[2]
        if kind[0] != "M":
            return A.tooth_sdf(u, v, h, kind, W, D, Hc, Hr)
        crown = smax(A.tooth_sdf(u, v, h, kind, W, D, Hc, 0.0025), -h - 0.0006, 0.0006)
        return smin(crown, _molar_roots(u, v, h, W, D, Hr, upper), 0.0008)
    corners = [o + X * a + Y * b + Z * c for a in (-W, W) for b in (-D, D) for c in (-Hr - 0.0015, Hc + 0.0015)]
    return fn, np.min(corners, 0) - 0.0015, np.max(corners, 0) + 0.0015


_TEETH = {}


def _teeth_fns(upper):
    if upper not in _TEETH:
        _TEETH[upper] = [tooth_sdf_long(f, upper) for f in tooth_frames_long(upper)]
    return _TEETH[upper]


def teeth_sdf(x, y, z, upper, grow=0.0):
    """Union of one jaw's teeth (both sides), grown by ``grow`` (m)."""
    ax = np.abs(x)
    d = np.full(np.shape(ax), 1.0)
    for fn, lo, hi in _teeth_fns(upper):
        m = np.all((np.stack([ax, y, z], -1) > lo - 0.004) & (np.stack([ax, y, z], -1) < hi + 0.004), -1)
        if np.any(m):
            v = np.full(np.shape(ax), 1.0)
            v[m] = fn(ax[m], y[m], z[m])
            d = np.minimum(d, v)
    return d - grow


def socket_sdf(x, y, z, upper):
    """Tooth sockets: the roots (and necks) grown by the periodontal ligament."""
    return teeth_sdf(x, y, z, upper, grow=PDL)


def root_sheaths(x, y, z, upper, wall=0.0019):
    """Alveolar bone around every root: each tooth grown by ``wall`` + PDL, cut 1.7 mm apical to its CEJ (the
    alveolar crest), smooth-unioned (interdental septa, juga over the roots, the canine eminence)."""
    ax = np.abs(x)
    d = np.full(np.shape(ax), 1.0)
    for (fn, lo, hi), (fdi, kind, dims, o, X, Y, Z) in zip(_teeth_fns(upper), tooth_frames_long(upper)):
        m = np.all((np.stack([ax, y, z], -1) > lo - 0.006) & (np.stack([ax, y, z], -1) < hi + 0.006), -1)
        if not np.any(m):
            continue
        v = np.full(np.shape(ax), 1.0)
        a, b, c = ax[m], y[m], z[m]
        h = (a - o[0]) * Z[0] + (b - o[1]) * Z[1] + (c - o[2]) * Z[2]
        s = fn(a, b, c) - wall - PDL
        s = smax(s, h + CREST_BELOW_CEJ, 0.0012)                  # crest below the CEJ
        s = smax(s, -h - dims[3] - 0.0035, 0.002)                 # 3.5 mm of bone beyond the apex
        v[m] = s
        d = smin(d, v, 0.0030)
    return d


def alveolar_ridge(x, y, z, upper, height=0.016):
    """Continuous alveolar process along one dental arch: from the crest (1.7 mm apical to the CEJ, a little
    higher between the teeth) toward the roots over ``height``, 0.5 x tooth depth + 2-3.5 mm about the arch line;
    ends behind the last molar (maxillary tuberosity / retromolar region).  The root sheaths add the juga."""
    A = _A()
    ax = np.abs(x)
    ca = A._cerv(upper)
    s, q = ca.arch.project(ax, y)
    zc, D, pap = ca.props(s)
    sgn = 1.0 if upper else -1.0
    hr = (z - zc) * sgn
    w = 0.5 * D + 0.0020 + 0.0015 * A.smoothstep(0.004, 0.012, hr)
    d = np.abs(q + 0.0004) - w
    d = smax(d, (CREST_BELOW_CEJ - 0.0006 * pap) - hr, 0.0012)
    d = smax(d, hr - height, 0.004)
    return smax(d, s - (ca.s_end + 0.0045), 0.004)


def maxilla_flare(x, y, z):
    """Lower maxilla envelope: the alveolar arch at the crest widening smoothly upward (a concave lateral surface)
    into the zygomatic buttress / canine fossa level at z -0.011 - no shelf between the face and the teeth."""
    A = _A()
    ax = np.abs(x)
    ca = A._cerv(True)
    s, q = ca.arch.project(ax, y)
    zc, D, _pap = ca.props(s)
    w = 0.5 * D + 0.0032 + 0.026 * sstep(-0.040, -0.010, z) ** 1.4
    d = np.abs(q + 0.0004) - w
    d = smax(d, (zc + CREST_BELOW_CEJ) - z, 0.0015)
    return smax(d, s - (ca.s_end + 0.0080), 0.005)


GUM_BAND = {True: 0.0085, False: 0.0125}


def gum_sdf(x, y, z, upper, band=None):
    """The head's gum band (scalloped margin, papillae) with the alveolar mucosa: tall enough to cover the alveolar
    process down to the floor of the head's mouth void (upper 8.5 mm, lower 12.5 mm; head: 5.8 mm) and 4.3 mm
    thick over the root surfaces at depth, so the bone under it is never exposed to the mouth's air."""
    A = _A()
    band = GUM_BAND[upper] if band is None else band
    ax = np.abs(x)
    ca = A._cerv(upper)
    s, q = ca.arch.project(ax, y)
    zc, D, pap = ca.props(s)
    sgn = 1.0 if upper else -1.0
    margin = zc - sgn * (0.0006 + 0.0027 * pap)
    hr = (z - margin) * sgn
    thick = 0.5 * D + 0.0009 + 0.0034 * A.smoothstep(0.0, 0.006, hr)
    qc = -0.0004 * A.smoothstep(0.0, 0.006, hr)
    d = np.abs(q - qc) - thick
    d = smax(d, -hr, 0.0012)
    d = smax(d, hr - band, 0.002)
    return smax(d, s - (ca.s_end + 0.0035), 0.004)


def tongue_sdf(x, y, z):
    """Tongue at rest in a closed mouth (fix round 3, critics: 'flat-topped slab in an empty air box'): a domed
    muscular body whose dorsum lies 1.5 mm under the palate and whose sides rest against the lingual gums of the
    lower teeth; the tip sits behind the lower incisors, the root curves down toward the vallecula."""
    A = _A()
    ax = np.abs(x)
    segs = [((0.0, -0.0735, -0.0600), (0.0125, 0.0060, 0.0048)),
            ((0.0, -0.0650, -0.0545), (0.0195, 0.0110, 0.0110)),
            ((0.0, -0.0520, -0.0520), (0.0230, 0.0140, 0.0145)),
            ((0.0, -0.0370, -0.0545), (0.0225, 0.0140, 0.0170)),
            ((0.0, -0.0240, -0.0640), (0.0190, 0.0110, 0.0160))]
    d = None
    for c, r in segs:
        e = ell(ax, y, z, c, r)
        d = e if d is None else smin(d, e, 0.008)
    d = smin(d, ell(ax, y, z, (0.0, -0.046, -0.0700), (0.0205, 0.030, 0.0080)), 0.006)
    # median sulcus
    d = d + 0.0008 * np.exp(-(ax / 0.0022) ** 2) * sstep(-0.078, -0.066, y) * sstep(-0.060, -0.050, z)
    # stay inside the mouth void (1 mm), behind / inside the lower gums and teeth, under the palate
    d = np.maximum(d, A.oral_void(ax, y, z) + 0.0010)
    d = np.maximum(d, -(gum_sdf(x, y, z, False) - 0.0006))
    d = np.maximum(d, -(teeth_sdf(x, y, z, False) - 0.0006))
    d = np.maximum(d, -(teeth_sdf(x, y, z, True) - 0.0008))
    return np.maximum(d, -(gum_sdf(x, y, z, True) - 0.0006))


# ===========================================================================
# Skull: midface refill, air spaces, fossae, palate, alveolar process
# ===========================================================================
NASAL_FLOOR = -0.0280           # top of the hard palate (nasal floor): 4-5 mm of palate over the mouth vault
CHOANA_Y = -0.0310              # posterior edge of the hard palate / vomer (choanae)


def _nasal_halfwidth(z):
    """Half width of each nasal fossa pair (m) vs height: wide at the floor, a narrow olfactory cleft above."""
    return np.interp(z, [-0.029, -0.015, 0.000, 0.012, 0.022], [0.0150, 0.0135, 0.0095, 0.0055, 0.0035])


def nasal_cavity(ax, y, z):
    """Nasal cavity air (both fossae), bony septum not yet subtracted."""
    roof = np.interp(y, [-0.085, -0.070, -0.045, -0.035, -0.028], [0.010, 0.021, 0.022, 0.010, 0.000])
    w = _nasal_halfwidth(z)
    d = ax - w
    d = smax(d, NASAL_FLOOR - z, 0.002)
    d = smax(d, z - roof, 0.003)
    d = smax(d, -0.092 - y, 0.003)                 # in front: the piriform aperture (head carve) takes over
    return smax(d, y - (CHOANA_Y + 0.004), 0.003)


def septum(ax, y, z):
    """Bony nasal septum (perpendicular plate of the ethmoid + vomer), 2 mm, with a slight deviation-free midline."""
    d = ax - 0.0010
    d = smax(d, -0.081 - y, 0.002)                 # the cartilaginous septum in front is not bone
    d = smax(d, y - CHOANA_Y, 0.002)               # free posterior edge of the vomer at the choanae
    d = smax(d, z - 0.0235, 0.002)                 # up to the cribriform plate (crista galli is in the base skull)
    return smax(d, NASAL_FLOOR - 0.001 - z, 0.001)


# turbinates: (centre, radii) of the scroll's ellipsoid, lateral wall x it hangs from
TURBINATES = [((0.0102, -0.0560, -0.0215), (0.0034, 0.0215, 0.0058), 0.0140),    # inferior
              ((0.0078, -0.0540, -0.0050), (0.0028, 0.0175, 0.0055), 0.0115),    # middle
              ((0.0055, -0.0455, 0.0100), (0.0020, 0.0095, 0.0035), 0.0070)]     # superior


def turbinates(ax, y, z):
    """Three bony scrolls per side on the lateral nasal wall: a 1.1 mm curled plate (the ellipsoid's shell, open
    on its lateral-inferior quadrant = the meatus under it) plus the attachment lamina up to the lateral wall."""
    d = np.full(np.shape(ax), 1.0)
    for c, r, wall_x in TURBINATES:
        e = ell(ax, y, z, c, r)
        shell = np.abs(e + 0.0004) - 0.00055
        meatus = np.maximum(ax - c[0] - 0.0004, (c[2] - 0.35 * r[2]) - z)     # lateral AND below the axis
        shell = np.maximum(shell, -meatus)
        lamina = np.maximum(np.abs(z - (c[2] + 0.75 * r[2])) - 0.0005,
                            np.maximum(np.abs(y - c[1]) - 0.85 * r[1], np.maximum(c[0] - ax, ax - wall_x - 0.001)))
        d = np.minimum(d, np.minimum(shell, lamina))
    return d


MAX_SINUS = ((0.0310, -0.0590, -0.0135), (0.0175, 0.0180, 0.0165))      # maxillary sinus (centre, radii)
SPHENOID = ((0.0, -0.0240, -0.0085), (0.0135, 0.0125, 0.0095))
ETHMOID = ((0.0072, -0.0600, 0.0120), (0.0045, 0.0200, 0.0125))
MASTOID = ((0.0500, 0.0130, -0.0200), (0.0110, 0.0130, 0.0170))
MEATUS = ((0.0730, 0.0000, 0.0000), (0.0480, 0.0040, -0.0015), 0.0035)   # outer, inner end, radius
TYMPANUM = ((0.0430, 0.0040, -0.0005), (0.0035, 0.0070, 0.0075))
INFRATEMPORAL = ((0.0215, -0.0450, -0.0800), (0.0900, -0.0020, -0.0010))  # lo, hi (|x|, y, z), 11 mm rounding
ZYG_ARCH = [(0.0560, -0.0540, -0.0005), (0.0615, -0.0360, 0.0000), (0.0640, -0.0200, 0.0005),
            (0.0600, -0.0090, 0.0010)]
ARCH_R = (0.0030, 0.0028)       # half height, half thickness of the arch (a 5-6 mm bar)


def zygomatic_arch(ax, y, z):
    """The zygomatic arch as a free bar (6 x 5.5 mm) from the zygomatic body to the articular tubercle."""
    d = np.full(np.shape(ax), 1.0)
    for a, b in zip(ZYG_ARCH[:-1], ZYG_ARCH[1:]):
        d = np.minimum(d, capsule(ax, y, z * (ARCH_R[1] / ARCH_R[0]), (a[0], a[1], a[2] * ARCH_R[1] / ARCH_R[0]),
                                  (b[0], b[1], b[2] * ARCH_R[1] / ARCH_R[0]), ARCH_R[1]))
    return d


def pterygoid_plates(ax, y, z):
    """Lateral and medial pterygoid plates hanging from the sphenoid behind the maxilla (2 mm plates)."""
    lat = np.maximum(np.abs(ax - (0.0200 + 0.10 * (y + 0.030))) - 0.0010,
                     np.maximum(np.abs(y + 0.0300) - 0.0085, np.maximum(-0.0470 - z, z + 0.0080)))
    med = np.maximum(np.abs(ax - 0.0120) - 0.0009,
                     np.maximum(np.abs(y + 0.0290) - 0.0050, np.maximum(-0.0440 - z, z + 0.0100)))
    return smin(lat, med, 0.002)


def piriform_aperture(ax, y, z):
    """Pear-shaped piriform aperture (~24 mm wide low, ~9 mm under the nasal bones, 36 mm tall, rounded
    bottom at the anterior nasal spine level), extruded backward into the nasal cavity."""
    w = 0.0045 + 0.0078 * sstep(0.015, -0.013, z)
    zb = -0.0270 + 0.0060 * (ax / 0.0125) ** 2                     # rounded floor of the aperture
    d = smax(ax - w, zb - z, 0.004)
    d = smax(d, z - 0.0165, 0.004)
    return smax(d, -0.095 - y, 0.003)


def palate(ax, y, z):
    """Hard palate: a 4-6 mm plate between the nasal floor and the oral mucosa (the vault rises in the midline)."""
    A = _A()
    top = NASAL_FLOOR + 0.0005
    d = z - top
    d = smax(d, (NASAL_FLOOR - 0.0110) - z, 0.002)                      # never thicker than ~11 mm
    d = smax(d, y - CHOANA_Y, 0.002)
    # only inside the dental arch (lingual to the tooth line; the alveolar ridge and root sheaths close it)
    ca = A._cerv(True)
    s, q = ca.arch.project(ax, y)
    _zc, D, _pap = ca.props(s)
    d = smax(d, q + 0.5 * D + 0.0008, 0.003)
    d = smax(d, ax - 0.030, 0.004)
    # oral side: 1.5 mm of palatal mucosa over the bone
    return np.maximum(d, -(A.oral_void(ax, y, z) - 0.0015))


TMJ_ZONE = ((0.0330, -0.0360, -0.0300), (0.0700, 0.0210, 0.0070))      # lo, hi (|x|, y, z)


def cranial_cavity_body(ax, y, z):
    """The head's cranial cavity with its middle fossa floor raised over the TMJ and the ear (head frame, |x|).

    ``gore_head.anatomy.cranial_floor`` puts the lateral middle fossa at z -0.010, 12 mm BELOW the mandibular
    condyle (-0.002) and the external acoustic meatus (0.0): the glenoid fossa and the ear canal opened into the
    brain case and the temporal lobe sat where the coronoid process and the condylar neck belong.  Here the floor is
    at z +0.007 laterally (the level of the zygomatic arch's upper border, the infratemporal crest), so the tegmen
    and the articular fossa roof keep 4-5 mm of bone.  GB_Brain (neuro) is clamped to this cavity."""
    A = _A()
    lo, hi = TMJ_ZONE
    zone = rbox(ax, y, z, (lo[0], lo[1], -0.200), hi, 0.008)
    return smax(A.cranial_cavity(ax, y, z), -zone, 0.006)


def middle_fossa_roof(ax, y, z):
    """Bone of the raised middle fossa floor over the TMJ / ear (the region the body cavity gave up): the roof of
    the glenoid fossa and the articular eminence (z -0.006 .. +0.007), the tympanic plate / postglenoid process
    behind the condyle reaching down to -0.013, the petrous bone medially.  Rounded, never a box face outside."""
    roof = rbox(ax, y, z, (0.0330, -0.0330, -0.0060), (0.0680, 0.0200, 0.0070), 0.0045)
    tymp = rbox(ax, y, z, (0.0330, -0.0040, -0.0140), (0.0660, 0.0200, 0.0030), 0.0045)
    petrous = rbox(ax, y, z, (0.0200, -0.0300, -0.0250), (0.0420, 0.0200, 0.0070), 0.0060)
    return smin(smin(roof, tymp, 0.004), petrous, 0.006)


def face_skull(x, y, z, base, clamps):
    """Refine a skull SDF ``base`` (head frame) - see the module docstring.  ``clamps(ax, y, z, d)`` applies the
    caller's soft-tissue clearances (skin, eyes, atlas, ...) to the facial additions."""
    A = _A()
    ax = np.abs(x)
    env = A.skull_envelope(ax, y, z)
    cav = cranial_cavity_body(ax, y, z)
    orbit = A._orbit(ax, y, z)
    # --- midface refill: the envelope's face block below the anterior cranial fossa, in front of the pterygoids,
    # minus the orbits and the piriform aperture (the head carved round holes into it; we carve anew)
    fill = smax(env, y + 0.022, 0.004)
    fill = smax(fill, -0.050 - z, 0.004)
    fill = smax(fill, z - 0.034, 0.004)
    fill = smax(fill, ax - 0.056, 0.004)
    fill = smax(fill, -(orbit - 0.0002), 0.002)
    fill = smax(fill, -(cav - 0.0010), 0.002)
    aperture = piriform_aperture(ax, y, z)
    fill = smax(fill, -aperture, 0.002)
    fill = clamps(ax, y, z, fill, 0.0040)
    d = smin(base, fill, 0.002)
    # below the nasal floor level the face is only alveolar process, palate, sinus floor and the zygomatic
    # buttress: the head's facial block ended in a flat 12 cm wide shelf over the upper teeth (a 'visor')
    keep = smin(maxilla_flare(x, y, z), root_sheaths(x, y, z, True) - 0.0005, 0.003)
    keep = np.minimum(keep, palate(ax, y, z) - 0.0005)
    keep = smin(keep, ell(ax, y, z, MAX_SINUS[0], np.asarray(MAX_SINUS[1]) + 0.0019), 0.004)
    keep = smin(keep, capsule(ax, y, z, (0.0380, -0.0560, -0.0400), (0.0500, -0.0540, -0.0100), 0.0048, 0.0060), 0.006)
    keep = np.minimum(keep, pterygoid_plates(ax, y, z) - 0.0003)
    lowface = smax(z + 0.0110, -keep, 0.004)
    lowface = smax(lowface, y + 0.022, 0.004)                      # (the skull base behind is not face)
    d = smax(d, -lowface, 0.003)
    d = smax(d, -aperture, 0.002)
    # --- additions that face the mouth: palate, alveolar process (root sheaths), the bony plates
    pal = palate(ax, y, z)
    alv = smin(root_sheaths(x, y, z, True), alveolar_ridge(x, y, z, True), 0.003)
    # 1.2 mm of mucosa between the bone and the mouth's air, except under the gum band (0.7 mm of gingiva there)
    gum = gum_sdf(x, y, z, True)
    alv = np.maximum(alv, -np.maximum(A.oral_void(ax, y, z) - 0.0012, -(gum - 0.0007)))
    add = smin(pal, alv, 0.004)
    add = smin(add, pterygoid_plates(ax, y, z), 0.002)
    add = smin(add, smax(smax(middle_fossa_roof(ax, y, z), -(cav - 0.0010), 0.001), env, 0.002), 0.003)
    add = clamps(ax, y, z, add, 0.0030, mouth=False)
    d = smin(d, add, 0.002)
    d = np.minimum(d, clamps(ax, y, z, turbinates(ax, y, z), 0.0030, mouth=False))
    d = np.minimum(d, clamps(ax, y, z, septum(ax, y, z), 0.0030, mouth=False))
    # --- air spaces (walls 1.5-2 mm to the outer surfaces), the bony septum and turbinates stay
    nas = nasal_cavity(ax, y, z)
    nas = smax(nas, -(septum(ax, y, z) + 0.0), 0.0006)
    nas = smax(nas, -turbinates(ax, y, z), 0.0004)
    sin = ell(ax, y, z, *MAX_SINUS)
    sin = smax(sin, env + 0.0017, 0.002)                          # facial / posterior walls 1.7 mm
    sin = smax(sin, -(orbit - 0.0012), 0.002)                     # orbital floor 1.2 mm
    sin = smax(sin, -(nasal_cavity(ax, y, z) - 0.0016), 0.002)    # medial wall 1.6 mm
    sin = smax(sin, -(root_sheaths(x, y, z, True, wall=0.0028) - 0.0), 0.002)   # floor over the roots
    sin = smax(sin, NASAL_FLOOR + 0.001 - z, 0.003)
    eth = ell(ax, y, z, *ETHMOID)
    eth = smax(eth, -(orbit - 0.0007), 0.001)                     # lamina papyracea 0.7 mm
    eth = smax(eth, -(nasal_cavity(ax, y, z) - 0.0008), 0.001)
    eth = smax(eth, -(cav - 0.0012), 0.001)
    eth = smax(eth, 0.0012 - cell_walls(x, y, z, 0.0055, 11), 0.0003)
    sph = ell(ax, y, z, *SPHENOID)
    sph = smax(sph, -(cav - 0.0015), 0.002)
    sph = smax(sph, -(nasal_cavity(ax, y, z) - 0.0015), 0.002)
    sph = smax(sph, env + 0.0015, 0.002)
    sph = smax(sph, 0.0005 - ax, 0.0003)                          # intersinus septum
    sph = smax(sph, 0.0008 - cell_walls(x, y, z, 0.0090, 13), 0.0004)
    mas = ell(ax, y, z, *MASTOID)
    mas = smax(mas, -(cav - 0.0014), 0.001)
    mas = smax(mas, env + 0.0011, 0.001)
    mas = smax(mas, 0.0009 - cell_walls(x, y, z, 0.0042, 17), 0.0003)
    canal = capsule(ax, y, z, MEATUS[0], MEATUS[1], MEATUS[2], 0.0032)
    canal = smin(canal, ell(ax, y, z, *TYMPANUM), 0.002)
    air = np.minimum(np.minimum(nas, sin), np.minimum(eth, sph))
    air = np.minimum(air, np.minimum(mas, canal))
    d = smax(d, -air, 0.0006)
    # --- soft-tissue spaces: infratemporal / temporal fossa (temporalis, pterygoids, masseter) lateral to the
    # pterygoid plates, behind the maxilla and medial to the zygomatic arch and the ramus
    lo, hi = INFRATEMPORAL
    itf = rbox(ax, y, z, lo, hi, 0.011)
    itf = smax(itf, -(cav - 0.0030), 0.003)                       # >= 3 mm of skull base above it
    itf = smax(itf, -(pterygoid_plates(ax, y, z) + 0.0), 0.001)
    itf = smax(itf, -(ell(ax, y, z, *MAX_SINUS) + 0.0005), 0.003)   # maxillary tuberosity (posterior wall)
    d = smax(d, -itf, 0.002)
    d = smin(d, clamps(ax, y, z, zygomatic_arch(ax, y, z), 0.0030, mouth=False), 0.002)
    # --- sockets of the upper teeth
    return smax(d, -socket_sdf(x, y, z, True), 0.0003)


# ===========================================================================
# Mandible: swept profile along the lower dental arch + ramus
# ===========================================================================
# body arch (plan view, head frame): the line under the lower teeth, from the symphysis back to the ramus
_MARCH = None


def _mand_arch():
    """Arch polyline (|x|, y) under the lower tooth necks, continued back to the ramus (gonion region)."""
    global _MARCH
    if _MARCH is None:
        A = _A()
        fr = tooth_frames_long(False)
        pts = [(0.0, fr[0][3][1] - 0.0010)] + [(o[0] + 0.0006, o[1]) for (_f, _k, _d, o, _X, _Y, _Z) in fr]
        pts += [(0.0330, -0.0330), (0.0420, -0.0210)]
        _MARCH = A.Arch(pts)
    return _MARCH


# (arc fraction, top z (crest level between the teeth), bottom z (inferior border), labial-lingual half
#  thickness, lingual offset of the section centre): symphysis 31.7 mm tall, M2 ~25 mm, 10-14 mm thick; the
#  inferior border rises ~23 deg toward the gonion (mandibular plane) [C]
MAND_PROFILE = [(0.00, -0.0668, -0.0985, 0.0068, 0.0020), (0.10, -0.0670, -0.0982, 0.0066, 0.0016),
                (0.25, -0.0665, -0.0962, 0.0060, 0.0010), (0.45, -0.0640, -0.0928, 0.0062, 0.0008),
                (0.62, -0.0630, -0.0895, 0.0066, 0.0006), (0.76, -0.0632, -0.0862, 0.0064, 0.0005),
                (0.88, -0.0645, -0.0810, 0.0050, 0.0003), (1.00, -0.0670, -0.0745, 0.0038, 0.0000)]


def _mand_body(ax, y, z):
    """Body: at each arc position a rounded, slightly teardrop section (thicker at the base)."""
    arch = _mand_arch()
    s, q = arch.project(ax, y)
    t = np.clip(s / arch.s[-1], 0.0, 1.0)
    P = np.asarray(MAND_PROFILE)
    top = np.interp(t, P[:, 0], P[:, 1])
    bot = np.interp(t, P[:, 0], P[:, 2])
    th = np.interp(t, P[:, 0], P[:, 3])
    off = np.interp(t, P[:, 0], P[:, 4])
    zm, hh = 0.5 * (top + bot), 0.5 * (top - bot)
    th = th * (1.0 + 0.22 * sstep(zm, bot, z))                     # thicker base (the inferior border)
    A = _A()
    sec = A.ellipse2(q + off, (z - zm) / hh * th, th, th)          # section: ellipse in (q, scaled z)
    body = np.maximum(sec, np.abs(z - zm) - hh)
    body = smax(body, np.maximum(np.abs(q + off) - th, np.abs(z - zm) - hh), 0.004)
    # the body ends where the ramus takes over (no infinite extrusion beyond the arch end)
    return smax(body, y + 0.018, 0.006)


# ramus outline in its own plane (y, z), head frame: condyle in the glenoid fossa (y -0.0115, z -0.002), bone
# gonion (y -0.0175, z -0.0715; RB gonion skin (0.052, -0.025, -0.070) head frame), posterior border leaning ~8 deg
# back going up, the lower border continuing the mandibular plane -> gonial angle ~121 deg; coronoid tip under the
# zygomatic arch, sigmoid notch ~14 mm deep, ramus ~30 mm wide at its narrowest
RAMUS_POLY = [(-0.0175, -0.0715), (-0.0150, -0.0600), (-0.0125, -0.0400), (-0.0100, -0.0200),       # posterior border
              (-0.0082, -0.0080), (-0.0150, -0.0070), (-0.0195, -0.0140),                          # condylar neck
              (-0.0245, -0.0190), (-0.0305, -0.0140),                                             # sigmoid notch
              (-0.0350, -0.0050), (-0.0385, -0.0075),                                             # coronoid tip
              (-0.0410, -0.0300), (-0.0445, -0.0560), (-0.0480, -0.0700),                         # anterior border
              (-0.0400, -0.0790), (-0.0280, -0.0765)]                                             # inferior border


def _ramus_x(z, y):
    """Lateral position of the ramus mid-plane: flares outward at the angle (masseteric tuberosity) and at the
    condyle; the coronoid leans in a little."""
    return 0.0455 + 0.0030 * sstep(-0.050, -0.072, z) + 0.0020 * sstep(-0.012, -0.002, z) * sstep(-0.018, -0.010, y) \
        - 0.0022 * sstep(-0.028, -0.036, y) * sstep(-0.022, -0.006, z)


def _poly2d(u, v, P):
    """Signed distance to a closed polygon (u, v) (negative inside; winding-agnostic)."""
    P = np.asarray(P, float)
    d = None
    sgn = np.ones(np.shape(u))
    for i in range(len(P)):
        a, b = P[i], P[(i + 1) % len(P)]
        e = b - a
        wu, wv = u - a[0], v - a[1]
        h = np.clip((wu * e[0] + wv * e[1]) / (e @ e), 0.0, 1.0)
        di = np.hypot(wu - e[0] * h, wv - e[1] * h)
        d = di if d is None else np.minimum(d, di)
        c1 = v >= a[1]
        c2 = v < b[1]
        c3 = e[0] * wv > e[1] * wu
        flip = (c1 & c2 & c3) | (~c1 & ~c2 & ~c3)
        sgn = np.where(flip, -sgn, sgn)
    return sgn * d


_RAMUS_SMOOTH = None


def _ramus_outline():
    """RAMUS_POLY smoothed (closed centripetal Catmull-Rom, 8 samples per edge): concave anterior border,
    S-shaped posterior border, rounded gonial angle, coronoid and condyle."""
    global _RAMUS_SMOOTH
    if _RAMUS_SMOOTH is None:
        P = np.asarray(RAMUS_POLY, float)
        n = len(P)
        out = []
        for i in range(n):
            p0, p1, p2, p3 = P[(i - 1) % n], P[i], P[(i + 1) % n], P[(i + 2) % n]
            t0 = 0.0
            t1 = t0 + max(np.linalg.norm(p1 - p0), 1e-9) ** 0.5
            t2 = t1 + max(np.linalg.norm(p2 - p1), 1e-9) ** 0.5
            t3 = t2 + max(np.linalg.norm(p3 - p2), 1e-9) ** 0.5
            for k in range(8):
                t = t1 + (t2 - t1) * k / 8
                a1 = (t1 - t) / (t1 - t0) * p0 + (t - t0) / (t1 - t0) * p1
                a2 = (t2 - t) / (t2 - t1) * p1 + (t - t1) / (t2 - t1) * p2
                a3 = (t3 - t) / (t3 - t2) * p2 + (t - t2) / (t3 - t2) * p3
                b1 = (t2 - t) / (t2 - t0) * a1 + (t - t0) / (t2 - t0) * a2
                b2 = (t3 - t) / (t3 - t1) * a2 + (t - t1) / (t3 - t1) * a3
                out.append((t2 - t) / (t2 - t1) * b1 + (t - t1) / (t2 - t1) * b2)
        _RAMUS_SMOOTH = np.asarray(out)
    return _RAMUS_SMOOTH


def _mand_ramus(ax, y, z):
    """Ramus plate (5-6 mm, thicker at the borders), coronoid process, condylar neck and head."""
    out = _poly2d(y, z, _ramus_outline())
    # round the outline (2 mm) and give the plate its thickness about the flaring mid-plane
    thick = 0.0026 + 0.0012 * sstep(-0.004, 0.004, np.abs(out)) + 0.0010 * sstep(-0.050, -0.076, z)
    plate = np.maximum(out + 0.0015, np.abs(ax - _ramus_x(z, y)) - thick)
    plate = smax(plate, out + 0.0015, 0.0015)
    cond = ell(ax, y, z, (0.0500, -0.0115, -0.0020), (0.0085, 0.0048, 0.0050))
    neck = capsule(ax, y, z, (0.0480, -0.0120, -0.0130), (0.0495, -0.0115, -0.0045), 0.0036, 0.0040)
    return smin(smin(plate, cond, 0.003), neck, 0.003)


def mandible_raw(x, y, z):
    """Unclamped mandible (head frame, signed x): body + ramus + chin + lower alveolar process with sockets."""
    ax = np.abs(x)
    body = _mand_body(ax, y, z)
    ram = _mand_ramus(ax, y, z)
    d = smin(body, ram, 0.010)
    # mental protuberance and tubercles (a triangular chin), mental foramen region stays smooth
    d = smin(d, ell(ax, y, z, (0.0, -0.0835, -0.0915), (0.0150, 0.0050, 0.0075)), 0.006)
    d = smin(d, ell(ax, y, z, (0.0110, -0.0810, -0.0955), (0.0060, 0.0045, 0.0040)), 0.004)
    # alveolar process: continuous ridge + root sheaths (juga) of the lower teeth
    d = smin(d, smin(root_sheaths(x, y, z, False), alveolar_ridge(x, y, z, False, height=0.020), 0.003), 0.0035)
    # digastric fossa / genial tubercles on the lingual symphysis (subtle)
    d = smax(d, -ell(ax, y, z, (0.0080, -0.0700, -0.0985), (0.0060, 0.0040, 0.0030)), 0.002)
    return smax(d, -socket_sdf(x, y, z, False), 0.0003)


# ===========================================================================
# Air-space table for bones.json (G3 renders these volumes as air when a wound opens them)
# ===========================================================================
AIR_SPACES = [
    dict(name="nasal_cavity", shape="aabb", c=(0.0, -0.058, -0.004), size=(0.030, 0.054, 0.052)),
    dict(name="maxillary_sinus_L", shape="ellipsoid", c=MAX_SINUS[0], radii=MAX_SINUS[1]),
    dict(name="maxillary_sinus_R", shape="ellipsoid", c=(-MAX_SINUS[0][0],) + MAX_SINUS[0][1:], radii=MAX_SINUS[1]),
    dict(name="sphenoid_sinus", shape="ellipsoid", c=SPHENOID[0], radii=SPHENOID[1]),
    dict(name="ethmoid_cells_L", shape="ellipsoid", c=ETHMOID[0], radii=ETHMOID[1], porous=True),
    dict(name="ethmoid_cells_R", shape="ellipsoid", c=(-ETHMOID[0][0],) + ETHMOID[0][1:], radii=ETHMOID[1],
         porous=True),
    dict(name="mastoid_cells_L", shape="ellipsoid", c=MASTOID[0], radii=MASTOID[1], porous=True),
    dict(name="mastoid_cells_R", shape="ellipsoid", c=(-MASTOID[0][0],) + MASTOID[0][1:], radii=MASTOID[1],
         porous=True),
    dict(name="ear_canal_L", shape="capsule", a=MEATUS[0], b=MEATUS[1], radius=MEATUS[2]),
    dict(name="ear_canal_R", shape="capsule", a=(-MEATUS[0][0],) + MEATUS[0][1:], b=(-MEATUS[1][0],) + MEATUS[1][1:],
         radius=MEATUS[2]),
]


def air_spaces_body():
    """AIR_SPACES in the body frame (authoring): centres / end points moved by HEAD_OFFSET."""
    out = []
    for a in AIR_SPACES:
        r = dict(a)
        for k in ("c", "a", "b"):
            if k in r:
                r[k] = [round(float(v), 5) for v in gbc.head_to_body(np.asarray(r[k], float))]
        for k in ("size", "radii"):
            if k in r:
                r[k] = [round(float(v), 5) for v in r[k]]
        out.append(r)
    return out
