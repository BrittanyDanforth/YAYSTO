"""Procedural texture generation in pure numpy (owner B7).  Plan §4.2, §8.2 B7.

Everything here is computed from code (no image files are read, nothing is
downloaded) and is deterministic: every random draw uses ``gb_common.rng``.

Building blocks
===============
* ``Lattice``: periodic gradient (Perlin) noise and jittered-grid Voronoi on an
  integer lattice.  Evaluated on tile coordinates ``u, v`` in [0, 1) with
  *integer* frequencies, every pattern repeats exactly at the tile edge, so the
  tileables are seamless by construction (the plan's 4-D torus mapping gives
  the same property in Cycles; in numpy the periodic lattice is exact and
  cheaper).
* ``fbm``, ``voronoi``, ``ridge``, ``smooth``, ``ramp``: small helpers in the
  style of the head project's ``materials.ShaderBuilder`` so colours and
  feature sizes can be carried over from ``gore_head/materials.py``.
* ``height_to_normal``: tangent-space normal map (OpenGL / Godot convention,
  +Y = +v) from a height field in millimetres, with wrap-around differences
  for tileables.

Texture families (called from ``bake.py``)
==========================================
* ``TILEABLES``: seamless 512^2 tissue tileables (muscle fibre, fat lobule,
  bone cut, diploe, blood crust, cloth weave) plus skin micro detail, bone
  surface and transverse muscle cut.  Each returns albedo (linear RGB),
  height (mm), roughness, AO and the tile's physical size.
* ``iris()`` and ``sclera(...)``: eye textures (iris disc albedo + height,
  sclera with conjunctival vessels in the eye atlas).
* ``decal_atlas()``: 64 procedural blood stains (drops, directional drops,
  spatter, runs, smears, pools, soaked stains, dried crust) in an 8 x 8 atlas.
* ``ROOM_TEXTURES``: tileables for the room and props (tile, grout, epoxy,
  rubber granulate, brushed stainless, galvanised steel, polymer stipple,
  walnut, hickory, G10, glove leather).

Colours are *linear* reflectances (they are sRGB-encoded when written).  Values
follow the bibles where they give one (``gb_data/tissue.CUT_COLOURS``,
RB §2.7 blood colours) and the head project's look-dev palette otherwise.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402

TILE_SIZE = 512


# ---------------------------------------------------------------------------
# Colour helpers
# ---------------------------------------------------------------------------
def srgb_to_linear(c):
    """sRGB (0-1) -> linear."""
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(c):
    """Linear (0-1) -> sRGB (0-1)."""
    c = np.clip(np.asarray(c, float), 0.0, 1.0)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * np.power(c, 1.0 / 2.4) - 0.055)


def hexlin(h):
    """'#RRGGBB' -> linear RGB tuple."""
    h = h.lstrip("#")
    return tuple(float(x) for x in srgb_to_linear([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]))


def luminance(rgb):
    """Rec. 709 luminance of linear RGB (..., 3)."""
    rgb = np.asarray(rgb, float)
    return rgb[..., 0] * 0.2126 + rgb[..., 1] * 0.7152 + rgb[..., 2] * 0.0722


def to_u8(x):
    """0-1 float -> uint8 with rounding."""
    return np.clip(np.rint(np.asarray(x, float) * 255.0), 0, 255).astype(np.uint8)


def smooth(x, e0, e1):
    """Smoothstep from e0 to e1 (like Blender's Map Range SMOOTHSTEP)."""
    t = np.clip((np.asarray(x, float) - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def mix(f, a, b):
    """Linear blend with a scalar/array factor; colours broadcast over the last axis."""
    f = np.asarray(f, float)
    a = np.asarray(a, float)
    b = np.asarray(b, float)
    if (a.ndim and a.shape[-1] == 3) or (b.ndim and b.shape[-1] == 3):
        f = f[..., None] if f.ndim else f
    return a + (b - a) * f


def ramp(x, stops):
    """Piecewise-linear colour ramp: stops = [(pos, (r, g, b)), ...] sorted by pos."""
    x = np.asarray(x, float)
    pos = np.array([s[0] for s in stops])
    col = np.array([s[1] for s in stops], float)
    out = np.empty(x.shape + (col.shape[1],))
    for c in range(col.shape[1]):
        out[..., c] = np.interp(x, pos, col[:, c])
    return out


def ridge(n, width):
    """1 at the 0.5 iso-line of a 0-1 noise, falling to 0 at ``width`` away (thin wavy lines)."""
    return 1.0 - smooth(np.abs(np.asarray(n) - 0.5), 0.0, width)


# ---------------------------------------------------------------------------
# Periodic lattice noise
# ---------------------------------------------------------------------------
class Lattice:
    """Gradient noise and Voronoi on a periodic integer lattice (deterministic).

    Lattice values come from an integer hash of (cell x, cell y, seed), so any
    integer period tiles exactly and there is no table size limit.  Non-tiling
    uses pass ``period=None``."""

    def __init__(self, seed_name, size=0, salt=0):
        self.seed = np.uint64((gbc.SEEDS[seed_name] * 1000003 + 7919 * salt) & 0xFFFFFFFFFFFF)

    def _h(self, ix, iy, k):
        """Hash of integer lattice coords -> float in [0, 1) (k selects an independent stream)."""
        with np.errstate(over="ignore"):
            x = np.asarray(ix).astype(np.int64).astype(np.uint64)
            y = np.asarray(iy).astype(np.int64).astype(np.uint64)
            h = x * np.uint64(0x9E3779B97F4A7C15) ^ (y * np.uint64(0xC2B2AE3D27D4EB4F)) \
                ^ (self.seed + np.uint64(k) * np.uint64(0x165667B19E3779F9))
            h ^= h >> np.uint64(31)
            h *= np.uint64(0xBF58476D1CE4E5B9)
            h ^= h >> np.uint64(29)
            h *= np.uint64(0x94D049BB133111EB)
            h ^= h >> np.uint64(32)
        return (h >> np.uint64(11)).astype(np.float64) / float(1 << 53)

    # -- gradient noise --------------------------------------------------
    def perlin(self, x, y, px=None, py=None):
        """Perlin noise in [-1, 1] (approx.) at lattice coordinates (x, y), periods px, py."""
        px = 1 << 40 if px is None else int(px)
        py = 1 << 40 if py is None else int(py)
        x = np.asarray(x, float)
        y = np.asarray(y, float)
        xi = np.floor(x)
        yi = np.floor(y)
        xf, yf = x - xi, y - yi
        xi = xi.astype(np.int64)
        yi = yi.astype(np.int64)
        x0, x1 = xi % px, (xi + 1) % px
        y0, y1 = yi % py, (yi + 1) % py

        def g(ix, iy, dx, dy):
            a = self._h(ix, iy, 0) * (2.0 * np.pi)
            return np.cos(a) * dx + np.sin(a) * dy
        u = xf * xf * xf * (xf * (xf * 6 - 15) + 10)
        v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
        n00 = g(x0, y0, xf, yf)
        n10 = g(x1, y0, xf - 1, yf)
        n01 = g(x0, y1, xf, yf - 1)
        n11 = g(x1, y1, xf - 1, yf - 1)
        a = n00 + (n10 - n00) * u
        b = n01 + (n11 - n01) * u
        return (a + (b - a) * v) * 1.414

    def fbm(self, u, v, fx, fy=None, octaves=4, gain=0.5, lac=2, offset=(0.0, 0.0), tile=True):
        """0-1 fractal noise on tile coords (u, v); integer base frequencies fx, fy per tile.

        With ``tile`` the pattern repeats exactly at u, v = 1.  ``lac`` must be an integer."""
        fy = fx if fy is None else fy
        tot = np.zeros(np.shape(u))
        amp, norm = 1.0, 0.0
        for k in range(octaves):
            mx, my = int(fx * lac ** k), int(fy * lac ** k)
            tot = tot + amp * self.perlin(np.asarray(u) * mx + offset[0] * (k + 1) * 17.3,
                                          np.asarray(v) * my + offset[1] * (k + 1) * 11.9,
                                          mx if tile else None, my if tile else None)
            norm += amp
            amp *= gain
        return np.clip(0.5 + 0.5 * tot / norm, 0.0, 1.0)

    # -- Voronoi -----------------------------------------------------------
    def voronoi(self, u, v, nx, ny=None, jitter=1.0, sx=1.0, sy=1.0, reach=None, tile=True):
        """Jittered-grid Voronoi on tile coords with nx x ny cells per tile.

        ``sx, sy`` weight the distance axes (sy < 1 stretches cells along v).
        Returns dict with F1, F2 (in cell units), ``edge`` = F2 - F1, ``id`` (0-1
        random per cell) and ``dx, dy`` (offset to the nearest feature point)."""
        ny = nx if ny is None else ny
        if reach is None:
            # F2 of a fully jittered grid needs a 5 x 5 search; anisotropic distances need more cells
            # along the compressed axis, or the result jumps at cell borders
            reach = (max(2, int(math.ceil(2.0 * sy / sx))), max(2, int(math.ceil(2.0 * sx / sy))))
        X = np.asarray(u, float) * nx
        Y = np.asarray(v, float) * ny
        cx = np.floor(X).astype(np.int64)
        cy = np.floor(Y).astype(np.int64)
        f1 = np.full(X.shape, 1e9)
        f2 = np.full(X.shape, 1e9)
        cid = np.zeros(X.shape)
        ddx = np.zeros(X.shape)
        ddy = np.zeros(X.shape)
        mx = nx if tile else 1 << 40
        my = ny if tile else 1 << 40
        for oy in range(-reach[1], reach[1] + 1):
            for ox in range(-reach[0], reach[0] + 1):
                gx_, gy_ = cx + ox, cy + oy
                ix, iy = gx_ % mx, gy_ % my
                fpx = gx_ + 0.5 + (self._h(ix, iy, 1) - 0.5) * jitter
                fpy = gy_ + 0.5 + (self._h(ix, iy, 2) - 0.5) * jitter
                dx, dy = fpx - X, fpy - Y
                d = np.sqrt((dx * sx) ** 2 + (dy * sy) ** 2)
                closer = d < f1
                f2 = np.where(closer, f1, np.minimum(f2, d))
                f1 = np.where(closer, d, f1)
                cid = np.where(closer, self._h(ix, iy, 3), cid)
                ddx = np.where(closer, dx, ddx)
                ddy = np.where(closer, dy, ddy)
        return {"F1": f1, "F2": f2, "edge": f2 - f1, "id": cid, "dx": ddx, "dy": ddy}


def grid(n=TILE_SIZE):
    """Tile coordinates of texel centres: (u, v) arrays with row 0 at the TOP (v near 1)."""
    c = (np.arange(n) + 0.5) / n
    u, v = np.meshgrid(c, c[::-1])
    return u, v


def warp(lat, u, v, f, amount, octaves=2, offset=(3.1, 7.7)):
    """Periodic domain warp: returns (u', v') displaced by up to ``amount`` tile units."""
    du = lat.fbm(u, v, f, octaves=octaves, offset=offset) - 0.5
    dv = lat.fbm(u, v, f, octaves=octaves, offset=(offset[1], offset[0])) - 0.5
    return u + du * 2.0 * amount, v + dv * 2.0 * amount


def blur_wrap(img, r):
    """Box blur with wrap-around (separable, ``r`` texels, repeated 3x ~ Gaussian)."""
    out = np.asarray(img, float)
    for _ in range(3):
        for ax in (0, 1):
            acc = np.zeros_like(out)
            for k in range(-r, r + 1):
                acc += np.roll(out, k, ax)
            out = acc / (2 * r + 1)
    return out


def height_to_normal(h_mm, texel_mm, wrap=True, strength=1.0):
    """Tangent-space normal (x right = +u, y up = +v, z out) from a height field in mm.

    Row 0 is the top of the image (v = 1), so +v is toward row 0."""
    h = np.asarray(h_mm, float)
    if wrap:
        dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2.0 * texel_mm)
        dy = (np.roll(h, 1, 0) - np.roll(h, -1, 0)) / (2.0 * texel_mm)
    else:
        dx = np.gradient(h, axis=1) / texel_mm
        dy = -np.gradient(h, axis=0) / texel_mm
    n = np.stack([-dx * strength, -dy * strength, np.ones_like(h)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True)


def cavity_ao(h_mm, texel_mm, radius_mm=0.6, depth_mm=0.15, wrap=True):
    """Cheap cavity occlusion (0-1, 1 = open) from how far a texel lies below its blurred neighbourhood."""
    r = max(1, int(round(radius_mm / texel_mm / 2.0)))
    if wrap:
        hb = blur_wrap(h_mm, r)
    else:
        hb = _blur_clamp(h_mm, r)
    return np.clip(1.0 - np.maximum(hb - h_mm, 0.0) / depth_mm * 0.5, 0.3, 1.0)


def _blur_clamp(img, r):
    out = np.asarray(img, float)
    for _ in range(3):
        for ax in (0, 1):
            pad = [(0, 0)] * out.ndim
            pad[ax] = (r, r)
            p = np.pad(out, pad, mode="edge")
            c = np.cumsum(p, axis=ax)
            c = np.concatenate([np.zeros_like(np.take(c, [0], axis=ax)), c], axis=ax)
            n = out.shape[ax]
            out = (np.take(c, np.arange(2 * r + 1, 2 * r + 1 + n), axis=ax)
                   - np.take(c, np.arange(0, n), axis=ax)) / (2 * r + 1)
    return out


def pack_set(albedo, height_mm, rough, ao, texel_mm, metal=0.0, extra_a=None, normal_strength=1.0, wrap=True):
    """Common texture set: dict of uint8 images (albedo RGB sRGB, normal RGB, ORM RGBA).

    ORM = R ambient occlusion, G roughness, B metallic, A = ``extra_a`` (height 0-1 by default)."""
    n = height_to_normal(height_mm, texel_mm, wrap=wrap, strength=normal_strength)
    hn = np.asarray(height_mm, float)
    if extra_a is None:
        lo, hi = np.percentile(hn, 0.5), np.percentile(hn, 99.5)
        extra_a = np.clip((hn - lo) / max(hi - lo, 1e-9), 0.0, 1.0)
    orm = np.stack([np.broadcast_to(ao, hn.shape), np.broadcast_to(rough, hn.shape),
                    np.broadcast_to(metal, hn.shape), np.broadcast_to(extra_a, hn.shape)], -1)
    return {"albedo": to_u8(linear_to_srgb(albedo)), "normal": to_u8(n * 0.5 + 0.5), "orm": to_u8(orm)}


# ---------------------------------------------------------------------------
# Tissue tileables (plan §4.2: 512^2 each, seamless)
# ---------------------------------------------------------------------------
# Physical size of one tile (m); the game scales UVs / triplanar by this.
TILE_M = {"muscle_fibre": 0.024, "fat_lobule": 0.032, "bone_cut": 0.016, "diploe": 0.016,
          "blood_crust": 0.048, "cloth_weave": 0.008, "skin_micro": 0.012, "bone_surface": 0.032,
          "muscle_cross": 0.024}

# GHS_Muscle ramp from gore_head/materials.py (linear), ending on the bible's cut colour
MUSCLE_RAMP = [(0.2, (0.045, 0.004, 0.006)), (0.45, (0.11, 0.011, 0.014)), (0.65, (0.19, 0.024, 0.026)),
               (0.85, (0.30, 0.05, 0.045))]
FAT_RAMP = [(0.15, (0.52, 0.30, 0.05)), (0.5, (0.72, 0.48, 0.11)), (0.85, (0.86, 0.66, 0.24))]
BONE_RAMP = [(0.3, (0.46, 0.37, 0.25)), (0.55, (0.61, 0.53, 0.39)), (0.8, (0.69, 0.62, 0.48))]


def _stripes(lat, x, k, jitter=0.7, salt=0):
    """1-D Voronoi along ``x`` (tile units, k cells per tile, periodic): (distance to the nearest
    border in cell units, cell id 0-1)."""
    X = np.asarray(x, float) * k
    c = np.floor(X).astype(np.int64)
    best = np.full(X.shape, 1e9)
    second = np.full(X.shape, 1e9)
    cid = np.zeros(X.shape)
    for o in (-2, -1, 0, 1, 2):
        g = c + o
        i = g % k
        fp = g + 0.5 + (lat._h(i, np.full_like(i, salt), 1) - 0.5) * jitter
        d = np.abs(fp - X)
        closer = d < best
        second = np.where(closer, best, np.minimum(second, d))
        best = np.where(closer, d, best)
        cid = np.where(closer, lat._h(i, np.full_like(i, salt), 3), cid)
    return (second - best) * 0.5, cid


def tile_muscle_fibre(n=TILE_SIZE):
    """Striated skeletal muscle cut along its fibres (fibres run along v).

    Long parallel fascicles (~1-3 mm wide) with slightly wavy borders, each a
    little different in tone, separated by thin glistening perimysium lines
    (a few carry fat marbling); fine fibre striation inside; deep red, wet."""
    lat = gbc_lat("tileables", 1)
    u, v = grid(n)
    tm = TILE_M["muscle_fibre"] * 1000.0 / n
    wob = (lat.fbm(u * 0.0, v, 1, 2, octaves=3) - 0.5) * 0.012 + (lat.fbm(u, v, 4, 2, octaves=3,
                                                                           offset=(4.4, 1.7)) - 0.5) * 0.035
    edge, fid = _stripes(lat, u + wob, 14, 0.8, 1)
    edge2, fid2 = _stripes(lat, u + wob * 1.3 + 0.013, 44, 0.9, 2)
    seam = 1.0 - smooth(edge, 0.0, 0.045)
    seam2 = (1.0 - smooth(edge2, 0.0, 0.06)) * 0.5
    body = smooth(edge, 0.0, 0.4)
    fib = lat.fbm(u + wob, v, 128, 3, octaves=3)
    fine = lat.fbm(u + wob, v, 384, 6, octaves=2, offset=(1.7, 0.3))
    along = lat.fbm(u, v, 6, 3, octaves=3, offset=(2.9, 6.1))
    val = 0.40 + (fid - 0.5) * 0.22 + (fid2 - 0.5) * 0.08 + (fib - 0.5) * 0.35 + (fine - 0.5) * 0.12 \
        + (along - 0.5) * 0.25
    col = ramp(val, MUSCLE_RAMP)
    col = col * (1.0 - seam2[..., None] * 0.25)
    col = mix(seam * 0.35, col, (0.30, 0.13, 0.11))                    # perimysium: thin, pale, translucent
    marb = seam * smooth(lat._h(np.floor((u + wob) * 14).astype(np.int64) % 14, np.zeros_like(u, np.int64), 5),
                         0.8, 0.85)
    col = mix(marb * 0.55, col, (0.45, 0.30, 0.13))                    # fat marbling along a few seams
    blotch = smooth(lat.fbm(u, v, 3, 3, octaves=3, offset=(2.2, 5.5)), 0.55, 0.8)
    col = mix(blotch * 0.35, col, col * np.array([0.72, 0.5, 0.58]))    # darker, deoxygenated patches
    h = body * 0.07 + (fib - 0.5) * 0.02 + (fine - 0.5) * 0.008 - seam * 0.04 - seam2 * 0.01
    rough = 0.32 + (fib - 0.5) * 0.10 + seam * 0.06 + marb * 0.05
    ao = cavity_ao(h, tm, 0.5, 0.04)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


def tile_muscle_cross(n=TILE_SIZE):
    """Muscle cut across its fibres: polygonal fascicles (1-3 mm) in pale perimysium, fibre stipple."""
    lat = gbc_lat("tileables", 2)
    u, v = grid(n)
    tm = TILE_M["muscle_cross"] * 1000.0 / n
    uw, vw = warp(lat, u, v, 4, 0.01)
    big = lat.voronoi(uw, vw, 10, 10, jitter=0.95)
    small = lat.voronoi(uw, vw, 90, 90, jitter=1.0)
    seam = 1.0 - smooth(big["edge"], 0.0, 0.07)
    endo = 1.0 - smooth(small["edge"], 0.0, 0.12)
    val = 0.08 + big["id"] * 0.35 + lat.fbm(u, v, 16, octaves=3) * 0.35 + small["id"] * 0.08
    col = ramp(val, MUSCLE_RAMP)
    col = mix(endo * 0.12, col, col * 0.7)
    seam = 1.0 - smooth(big["edge"], 0.0, 0.045)
    col = mix(seam * 0.45, col, (0.30, 0.14, 0.12))
    marb = seam * smooth(lat.fbm(u, v, 5, octaves=2, offset=(3.3, 1.1)), 0.6, 0.72)
    col = mix(marb * 0.7, col, (0.50, 0.36, 0.16))
    h = smooth(big["edge"], 0.0, 0.3) * 0.06 - endo * 0.01
    rough = 0.32 + seam * 0.15
    ao = cavity_ao(h, tm, 0.4, 0.03)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


def tile_fat_lobule(n=TILE_SIZE):
    """Subcutaneous fat: glossy cream-yellow lobules (~1.5-4 mm) with thin red septa and capillaries."""
    lat = gbc_lat("tileables", 3)
    u, v = grid(n)
    tm = TILE_M["fat_lobule"] * 1000.0 / n
    uw, vw = warp(lat, u, v, 4, 0.01)
    v1 = lat.voronoi(uw, vw, 11, 11, jitter=0.9)
    uw2, vw2 = warp(lat, uw, vw, 24, 0.003, offset=(5.5, 1.9))
    v2 = lat.voronoi(uw2, vw2, 30, 30, jitter=1.0)
    dome1 = np.sqrt(np.clip(1.0 - (v1["F1"] / 0.75) ** 2, 0.0, 1.0))
    dome2 = np.sqrt(np.clip(1.0 - (v2["F1"] / 0.75) ** 2, 0.0, 1.0))
    lob = dome1 * 0.6 + dome2 * 0.4
    sept = np.maximum(1.0 - smooth(v1["edge"], 0.0, 0.05), (1.0 - smooth(v2["edge"], 0.0, 0.07)) * 0.45)
    tone = v1["id"] * 0.6 + v2["id"] * 0.4
    nfine = lat.fbm(u, v, 64, octaves=2)
    col = ramp(lob * 0.35 + tone * 0.45 + nfine * 0.2, FAT_RAMP)
    cap = ridge(lat.fbm(uw2, vw2, 10, octaves=3, offset=(7.1, 2.4)), 0.010) \
        * smooth(lat.fbm(u, v, 3, octaves=2), 0.45, 0.62)
    col = mix(sept * 0.55, col, (0.55, 0.20, 0.10))                     # thin pink-red septa
    col = mix(cap * 0.8, col, (0.35, 0.02, 0.015))                       # capillaries
    blush = smooth(lat.fbm(u, v, 3, octaves=3, offset=(1.1, 8.8)), 0.6, 0.8) * 0.3
    col = mix(blush, col, col * np.array([0.95, 0.55, 0.45]))
    col = col * (0.8 + 0.2 * lob[..., None])
    h = dome1 * 0.45 + dome2 * 0.15 - sept * 0.08
    rough = 0.18 + sept * 0.14 + (nfine - 0.5) * 0.06
    ao = cavity_ao(h, tm, 0.8, 0.12)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


def tile_bone_cut(n=TILE_SIZE):
    """Cut or broken compact (cortical) bone: ivory, osteon rings with Haversian pores, lamellar grain,
    blood caught in the pores and saw/fracture roughness."""
    lat = gbc_lat("tileables", 4)
    u, v = grid(n)
    tm = TILE_M["bone_cut"] * 1000.0 / n
    n1 = lat.fbm(u, v, 4, octaves=4)
    ost = lat.voronoi(u, v, 64, 64, jitter=0.85)                 # osteons ~0.25 mm
    rings = 0.5 + 0.5 * np.cos(ost["F1"] * 2.0 * np.pi * 3.2)
    canal = 1.0 - smooth(ost["F1"], 0.06, 0.13)                 # Haversian canals ~50 um
    cement = 1.0 - smooth(ost["edge"], 0.0, 0.06)
    col = ramp(n1 * 0.7 + lat.fbm(u, v, 32, octaves=2) * 0.3, BONE_RAMP)
    col = col * (0.95 + 0.07 * rings[..., None]) * (1.0 - cement[..., None] * 0.06)
    col = mix(canal * 0.8, col, (0.22, 0.06, 0.045))                # blood in the canals
    grain = lat.fbm(u, v, 3, 48, octaves=3, offset=(2.2, 0.4))
    col = col * (0.9 + 0.2 * grain[..., None])
    stain = smooth(lat.fbm(u, v, 3, octaves=3, offset=(4.4, 1.1)), 0.55, 0.78)
    col = mix(stain * 0.45, col, col * np.array([0.72, 0.42, 0.36]))   # blood-tinged patches
    saw = lat.fbm(u, v, 2, 64, octaves=2, offset=(6.6, 6.6))           # tool / fracture striation
    h = -canal * 0.03 + (saw - 0.5) * 0.02 + (n1 - 0.5) * 0.03 - cement * 0.005
    rough = 0.52 + (n1 - 0.5) * 0.1 + canal * 0.1
    ao = cavity_ao(h, tm, 0.1, 0.02)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


def tile_diploe(n=TILE_SIZE):
    """Spongy (cancellous) bone as in the skull's diploe and vertebral bodies: a lattice of pale
    trabeculae around marrow spaces filled with dark red marrow and blood."""
    lat = gbc_lat("tileables", 5)
    u, v = grid(n)
    tm = TILE_M["diploe"] * 1000.0 / n
    uw, vw = warp(lat, u, v, 6, 0.008)
    a = lat.voronoi(uw, vw, 22, 22, jitter=1.0)                  # 0.5-1 mm spaces
    b = lat.voronoi(uw, vw, 48, 48, jitter=1.0)
    thick = 0.07 + 0.06 * lat.fbm(u, v, 6, octaves=2)
    trab = np.maximum(1.0 - smooth(a["edge"], thick * 0.4, thick), (1.0 - smooth(b["edge"], 0.03, 0.08)) * 0.45)
    cavity = 1.0 - trab
    depth = smooth(a["F1"], 0.1, 0.6)
    marrow = ramp(a["id"] * 0.6 + lat.fbm(u, v, 20, octaves=2) * 0.4,
                  [(0.2, (0.07, 0.006, 0.006)), (0.55, (0.20, 0.022, 0.018)), (0.9, (0.34, 0.06, 0.04))])
    marrow = marrow * (1.0 - depth[..., None] * 0.6)
    bone = ramp(lat.fbm(u, v, 12, octaves=3), [(0.3, (0.60, 0.50, 0.34)), (0.7, (0.74, 0.65, 0.48))])
    col = mix(trab, marrow, bone)
    col = mix((1.0 - smooth(a["edge"], thick * 0.4, thick * 1.6)) * (1.0 - trab) * 0.5, col, (0.40, 0.14, 0.09))
    h = trab * 0.25 - cavity * depth * 0.35
    rough = mix(trab, 0.25, 0.55)                                   # wet marrow glossy, bone matte
    ao = np.clip(1.0 - cavity * depth * 0.7, 0.2, 1.0)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


def tile_blood_crust(n=TILE_SIZE):
    """Dried blood crust: near-black red-brown, thick glossy-to-matte plates, crack network showing a
    thinner rust-brown film, curled flake edges (RB §2.7 blood colours, dried)."""
    lat = gbc_lat("tileables", 6)
    u, v = grid(n)
    tm = TILE_M["blood_crust"] * 1000.0 / n
    thick = lat.fbm(u, v, 3, octaves=4)
    uw, vw = warp(lat, u, v, 5, 0.015)
    cr = lat.voronoi(uw, vw, 9, 9, jitter=1.0)
    cr2 = lat.voronoi(uw, vw, 26, 26, jitter=1.0)
    crackw = 0.02 + 0.03 * smooth(thick, 0.5, 0.9)
    crack = (1.0 - smooth(cr["edge"], 0.0, crackw)) * smooth(thick, 0.35, 0.55)
    fine = (1.0 - smooth(cr2["edge"], 0.0, 0.035)) * smooth(thick, 0.55, 0.75) * 0.8
    curl = smooth(cr["edge"], crackw, crackw * 4.0)
    base_thin = (0.15, 0.022, 0.016)
    base_thick = (0.024, 0.005, 0.004)
    col = mix(smooth(thick, 0.15, 0.75), base_thin, base_thick)
    col = col * (0.85 + 0.3 * lat.fbm(u, v, 40, octaves=2)[..., None])
    col = mix(np.maximum(crack, fine), col, (0.11, 0.022, 0.016))
    h = thick * 0.3 * curl - crack * 0.25 - fine * 0.06 + (1.0 - curl) * 0.05 * smooth(thick, 0.5, 0.8)
    rough = mix(smooth(thick, 0.4, 0.8), 0.7, 0.38) + crack * 0.2
    ao = cavity_ao(h, tm, 1.0, 0.1)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


def tile_cloth_weave(n=TILE_SIZE):
    """Charcoal cotton-poly 2/1 twill (27 ends x 27 picks per 8 mm tile, ~34 threads/cm), heathered
    fibres with a slight twist, fuzz on the thread tops."""
    lat = gbc_lat("tileables", 7)
    u, v = grid(n)
    tm = TILE_M["cloth_weave"] * 1000.0 / n
    k = 27
    X, Y = u * k, v * k
    ix, iy = np.floor(X).astype(int), np.floor(Y).astype(int)
    fx, fy = X - ix, Y - iy
    warp_up = ((ix - iy) % 3) != 0                 # 2/1 twill: warp floats over two picks
    # thread cross profiles (rounded) and lengthwise bulge
    prof_x = np.sin(np.clip(fx, 0, 1) * np.pi) ** 0.7
    prof_y = np.sin(np.clip(fy, 0, 1) * np.pi) ** 0.7
    twist_w = lat.fbm(u, v, 216, 27, octaves=2)
    twist_f = lat.fbm(u, v, 27, 216, octaves=2, offset=(2.2, 9.1))
    h_warp = prof_x * (0.08 + 0.03 * (twist_w - 0.5))
    h_weft = prof_y * (0.08 + 0.03 * (twist_f - 0.5))
    h = np.where(warp_up, h_warp + 0.04, h_weft + 0.04)
    gap = np.where(warp_up, 1.0 - prof_x, 1.0 - prof_y)
    heather = lat.fbm(u, v, 108, 108, octaves=2, offset=(1.3, 4.4))
    fibre = np.where(warp_up, lat.fbm(u, v, 432, 54, octaves=1), lat.fbm(u, v, 54, 432, octaves=1, offset=(3, 3)))
    g = 0.030 + 0.020 * smooth(heather, 0.45, 0.8) + 0.012 * (fibre - 0.5)
    col = np.stack([g * 0.98, g * 0.99, g * 1.04], -1)
    col = col * (1.0 - gap[..., None] * 0.45)
    fuzz = smooth(lat.fbm(u, v, 64, octaves=3, offset=(8.8, 1.2)), 0.6, 0.85) * 0.25
    col = col + fuzz[..., None] * 0.012
    rough = 0.88 + gap * 0.08
    ao = np.clip(1.0 - gap * 0.55, 0.3, 1.0)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


def tile_skin_micro(n=TILE_SIZE):
    """Skin micro detail (detail map): pores (~80-150 um) and the micro-relief furrow network
    (0.3-1 mm polygons).  Albedo is a multiplier around mid grey (0.5 = unchanged)."""
    lat = gbc_lat("tileables", 8)
    u, v = grid(n)
    tm = TILE_M["skin_micro"] * 1000.0 / n
    uw, vw = warp(lat, u, v, 8, 0.01)
    furrow = lat.voronoi(uw, vw, 24, 22, jitter=1.0)
    furrow2 = lat.voronoi(uw, vw, 60, 56, jitter=1.0)
    pores = lat.voronoi(u, v, 40, 40, jitter=0.9)
    grooves = (1.0 - smooth(furrow["edge"], 0.0, 0.10)) * 0.8 + (1.0 - smooth(furrow2["edge"], 0.0, 0.10)) * 0.3
    pore = (1.0 - smooth(pores["F1"], 0.0, 0.16)) * smooth(pores["id"], 0.15, 0.3)
    h = -grooves * 0.025 - pore * 0.04 + (lat.fbm(u, v, 30, octaves=3) - 0.5) * 0.01
    detail = 0.5 - grooves * 0.035 - pore * 0.09
    col = np.stack([detail, detail, detail], -1)
    rough = 0.45 + grooves * 0.05 + pore * 0.08
    ao = cavity_ao(h, tm, 0.2, 0.02)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm, "albedo_is_detail": True}


def tile_bone_surface(n=TILE_SIZE):
    """Periosteal (outer) bone surface: ivory with nutrient foramina, fine pits, periosteal vessels
    and lamellar grain (GHS_Bone in the head project)."""
    lat = gbc_lat("tileables", 9)
    u, v = grid(n)
    tm = TILE_M["bone_surface"] * 1000.0 / n
    n1 = lat.fbm(u, v, 3, octaves=4)
    n2 = lat.fbm(u, v, 22, octaves=2)
    col = ramp(n1 * 0.7 + n2 * 0.3, BONE_RAMP)
    pits = lat.voronoi(u, v, 76, 76)
    pit = 1.0 - smooth(pits["F1"], 0.0, 0.22)
    col = mix(pit * 0.6, col, (0.26, 0.18, 0.12))
    fd = lat.voronoi(u, v, 8, 8)
    dot = (1.0 - smooth(fd["F1"], 0.0, 0.07)) * smooth(fd["id"], 0.8, 0.82)
    col = mix(dot * 0.85, col, (0.20, 0.09, 0.07))
    uw, vw = warp(lat, u, v, 2, 0.03)
    vessel = ridge(lat.fbm(uw, vw, 4, octaves=3, offset=(5.1, 2.9)), 0.012) * smooth(lat.fbm(u, v, 2), 0.5, 0.7)
    col = mix(vessel * 0.35, col, (0.45, 0.16, 0.12))
    grain = lat.fbm(u, v, 4, 16, octaves=4, offset=(1.2, 3.4))
    col = col * (0.88 + 0.24 * grain[..., None])
    stain = smooth(lat.fbm(u, v, 2, octaves=3, offset=(9.9, 9.9)), 0.6, 0.8) * 0.4
    col = mix(stain, col, (0.40, 0.27, 0.16))
    h = n2 * 0.02 - pit * 0.025 - dot * 0.08 + vessel * 0.01 + grain * 0.01
    rough = 0.58 + (n1 - 0.5) * 0.2 + pit * 0.1
    ao = cavity_ao(h, tm, 0.2, 0.02)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao, "texel_mm": tm}


TILEABLES = {
    "muscle_fibre": tile_muscle_fibre,
    "fat_lobule": tile_fat_lobule,
    "bone_cut": tile_bone_cut,
    "diploe": tile_diploe,
    "blood_crust": tile_blood_crust,
    "cloth_weave": tile_cloth_weave,
    "skin_micro": tile_skin_micro,
    "bone_surface": tile_bone_surface,
    "muscle_cross": tile_muscle_cross,
}
CORE_TILEABLES = ("muscle_fibre", "fat_lobule", "bone_cut", "diploe", "blood_crust", "cloth_weave")

_LATS = {}


def gbc_lat(name, salt=0, size=1024):
    """Cached ``Lattice`` for a registered seed name + salt."""
    key = (name, salt, size)
    if key not in _LATS:
        _LATS[key] = Lattice(name, size, salt)
    return _LATS[key]


def tile_edge_error(img):
    """Seam error of a tileable in 1/255 units (>= 0).

    The wrap-around line (last row -> first row, last column -> first column)
    must look like any interior line: error = mean |difference across the seam|
    minus the 99th percentile of the same statistic over all interior lines
    (a pattern with regular hard edges, e.g. a weave, has interior lines as
    sharp as the seam; a broken seam stands out above all of them)."""
    a = np.asarray(img, float)
    if img.dtype != np.uint8:
        a = a * 255.0
    a = a.reshape(a.shape[0], a.shape[1], -1)
    err = 0.0
    for ax in (0, 1):
        b = np.moveaxis(a, ax, 0)
        lines = np.abs(np.diff(b, axis=0)).mean(axis=(1, 2))
        seam = np.abs(b[0] - b[-1]).mean()
        err = max(err, seam - float(np.percentile(lines, 99)))
    return float(max(err, 0.0))


# ---------------------------------------------------------------------------
# Eyes
# ---------------------------------------------------------------------------
# From gore_head/materials.py (object space of the eye, metres)
IRIS_R = 0.0058
PUPIL_R = 0.0022
LIMBUS_R = 0.0059
IRIS_TEX_R = 0.0062          # the iris texture spans this radius at its edge (uv radius 0.5)


def iris(n=1024):
    """Iris disc texture (albedo linear RGB, height mm) centred in the image.

    Radius IRIS_TEX_R at the image edge.  Matches the head project's GH_Eye:
    blue-grey stroma with a brown collarette zone (central heterochromia),
    radial fibres, crypts, contraction furrows, pupillary ruff, dark limbal
    ring.  The pupil is drawn at PUPIL_R; the game remaps radius for dilation
    (radial coordinate r_n = (r - PUPIL_R) / (IRIS_R - PUPIL_R))."""
    lat = gbc_lat("lookdev", 11)
    c = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    X, Y = np.meshgrid(c, c[::-1])
    r = np.sqrt(X * X + Y * Y) * IRIS_TEX_R
    th = (np.arctan2(Y, X) / (2.0 * np.pi)) % 1.0
    rn = r / IRIS_R
    pr = PUPIL_R / IRIS_R
    t = np.clip((rn - pr) / (1.0 - pr), 0.0, 1.0)     # 0 pupil edge .. 1 iris root
    # radial stroma fibres: noise with many cycles around, few along the radius
    fib = lat.fbm(th, t * 0.999, 96, 2, octaves=4, gain=0.55, offset=(0.3, 0.0))
    fib2 = lat.fbm(th, t * 0.999, 240, 3, octaves=2, offset=(2.9, 0.0))
    wav = lat.fbm(th, np.zeros_like(th), 7, 1, octaves=2, offset=(5.5, 0.0))
    coll = 0.50 + (wav - 0.5) * 0.14                    # wavy collarette radius (in rn)
    inner = 1.0 - smooth(rn, coll - 0.05, coll + 0.04)
    outer_col = ramp(fib * 0.65 + fib2 * 0.35, [(0.25, (0.035, 0.065, 0.080)), (0.5, (0.10, 0.17, 0.20)),
                                                (0.72, (0.27, 0.37, 0.40)), (0.9, (0.45, 0.52, 0.52))])
    inner_col = ramp(fib * 0.6 + fib2 * 0.4, [(0.3, (0.09, 0.065, 0.035)), (0.6, (0.24, 0.16, 0.075)),
                                              (0.85, (0.42, 0.31, 0.16))])
    col = mix(inner * (0.45 + 0.55 * fib2), outer_col, inner_col)
    ring = np.exp(-((rn - coll) * 22.0) ** 2)
    col = mix(ring * 0.4 * fib, col, (0.52, 0.47, 0.38))
    cr = lat.voronoi(th, t * 0.999, 22, 3, jitter=0.9, sx=1.0, sy=1.6, tile=False)
    crypt = (1.0 - smooth(cr["F1"], 0.05, 0.32)) * smooth(cr["id"], 0.45, 0.6) * smooth(rn, 0.42, 0.55) \
        * (1.0 - smooth(rn, 0.8, 0.9))
    col = mix(crypt * 0.75, col, col * 0.25)
    furrow = sum(np.exp(-((rn - f0 - (wav - 0.5) * 0.03) * 90.0) ** 2) for f0 in (0.70, 0.78, 0.86)) \
        * smooth(lat.fbm(th, np.zeros_like(th), 16, 1, octaves=2, offset=(1.1, 0.0)), 0.35, 0.6)
    col = mix(furrow * 0.35, col, col * 0.45)
    col = mix(smooth(rn, 0.86, 1.0), col, (0.02, 0.025, 0.03))                 # limbal ring
    ruff = (1.0 - smooth(rn, pr + 0.015, pr + 0.06)) * smooth(rn, pr - 0.01, pr)
    ruff_bumps = lat.fbm(th, np.zeros_like(th), 64, 1, octaves=2, offset=(7.7, 0.0))
    col = mix(ruff * (0.6 + 0.4 * ruff_bumps), col, (0.05, 0.025, 0.012))
    pupil = 1.0 - smooth(rn, pr - 0.012, pr + 0.004)
    col = mix(pupil, col, (0.003, 0.003, 0.003))
    outside = smooth(rn, 1.0, 1.04)
    col = mix(outside, col, (0.02, 0.025, 0.03))
    # height (mm): stroma raised at the collarette, crypts deep, fibres ridged, pupil flat
    h = (fib - 0.5) * 0.05 + ring * 0.06 + inner * 0.03 - crypt * 0.08 - furrow * 0.03 \
        + ruff * ruff_bumps * 0.04
    h = h * (1.0 - pupil) * (1.0 - outside)
    rough = np.full(h.shape, 0.4)
    ao = np.clip(1.0 - crypt * 0.5 - furrow * 0.2, 0.2, 1.0)
    return {"albedo": col, "height": h, "rough": rough, "ao": ao,
            "texel_mm": IRIS_TEX_R * 2000.0 / n, "pupil_rn": pr, "radius_m": IRIS_TEX_R}


def sclera(p_local, n_img=None):
    """Sclera albedo for eye-local unit directions ``p_local`` (N, 3); -Y = gaze (front).

    White slightly yellow-grey sclera, pinkish toward the fornices, bluish near
    the limbus, tortuous conjunctival vessels running from the fornices toward
    the limbus and thinning, deeper blurred episcleral vessels, a faint
    pinguecula nasally and temporally.  Returns (col (N,3) linear, height (N,) mm,
    iris_mask (N,) 1 inside the cornea)."""
    lat = gbc_lat("lookdev", 12)
    p = np.asarray(p_local, float)
    p = p / np.maximum(np.linalg.norm(p, axis=1, keepdims=True), 1e-9)
    polar = np.arccos(np.clip(-p[:, 1], -1.0, 1.0))           # 0 at the cornea apex
    around = (np.arctan2(p[:, 2], p[:, 0]) / (2.0 * np.pi)) % 1.0
    limbus_ang = math.asin(LIMBUS_R / 0.012)                   # ~29.5 deg
    t = np.clip((polar - limbus_ang) / (math.radians(110.0) - limbus_ang), 0.0, 1.0)   # 0 limbus .. 1 back
    base = mix(lat.fbm(around, t, 8, 2, octaves=3), (0.62, 0.57, 0.52), (0.71, 0.67, 0.62))
    col = mix(smooth(t, 0.45, 0.95), base, (0.52, 0.34, 0.30))
    col = mix((1.0 - smooth(t, 0.0, 0.08)) * 0.55, col, (0.52, 0.53, 0.56))
    # conjunctival vessels: iso-lines of noise stretched radially (many cycles around the eye)
    wa, wt = around + (lat.fbm(around, t, 12, 3, octaves=2, offset=(1.1, 2.2)) - 0.5) * 0.02, t
    v1 = ridge(lat.fbm(wa, wt, 18, 1, octaves=3, gain=0.6, offset=(0.0, 0.0), tile=False), 0.010 + 0.022 * t)
    v2 = ridge(lat.fbm(wa, wt, 46, 2, octaves=2, gain=0.6, offset=(5.0, 1.0), tile=False), 0.006 + 0.014 * t)
    vmask = smooth(t, 0.04, 0.35) * (0.45 + 0.55 * smooth(lat.fbm(around, t, 5, 2, octaves=2,
                                                                  offset=(3.3, 3.3)), 0.4, 0.6))
    col = mix(v1 * vmask * 0.55, col, (0.52, 0.06, 0.05))
    col = mix(v2 * vmask * 0.35, col, (0.62, 0.16, 0.13))
    epi = smooth(lat.fbm(wa, wt, 10, 2, octaves=2, offset=(9.0, 4.0)), 0.55, 0.75) * smooth(t, 0.1, 0.5)
    col = mix(epi * 0.18, col, col * np.array([1.0, 0.72, 0.68]))
    ping = np.exp(-(((around - 0.0 + 0.5) % 1.0 - 0.5) / 0.05) ** 2) + np.exp(-(((around - 0.5 + 0.5) % 1.0 - 0.5)
                                                                                  / 0.05) ** 2)
    ping = ping * np.exp(-((t - 0.07) / 0.05) ** 2) * 0.25
    col = mix(ping, col, (0.62, 0.52, 0.34))
    iris_mask = 1.0 - smooth(polar, limbus_ang - 0.01, limbus_ang + 0.02)
    col = mix(iris_mask, col, (0.10, 0.12, 0.13))
    h = v1 * vmask * 0.02 + v2 * vmask * 0.01
    return col, h, iris_mask


# ---------------------------------------------------------------------------
# Blood decal atlas (plan §8.2 B7: 32-64 procedural drops and smears)
# ---------------------------------------------------------------------------
DECAL_KINDS = ("drop_round", "drop_angled", "spatter", "run", "smear", "pool", "soak", "crust")
DECAL_TILE_MM = {"drop_round": 24.0, "drop_angled": 40.0, "spatter": 120.0, "run": 160.0, "smear": 200.0,
                 "pool": 400.0, "soak": 150.0, "crust": 60.0}
BLOOD_THIN = (0.38, 0.030, 0.035)       # thin fresh film over a light surface (tinted, not black)
BLOOD_MID = hexlin("#8E1420")           # RB venous / film colour
BLOOD_THICK = hexlin("#5E070C")         # RB thick pools, near-black red
BLOOD_CLOT = (0.030, 0.003, 0.004)


def _disc_field(X, Y, cx, cy, r, lat, wob=0.12, f=6, off=0.0):
    """Signed-ish radial field (1 inside, 0 at the wobbly rim) for a blob at (cx, cy) radius r."""
    dx, dy = X - cx, Y - cy
    ang = (np.arctan2(dy, dx) / (2 * np.pi)) % 1.0
    rw = r * (1.0 + (lat.fbm(ang, np.full_like(ang, off), f, 1, octaves=2, offset=(off, off)) - 0.5) * 2 * wob)
    return 1.0 - np.sqrt(dx * dx + dy * dy) / np.maximum(rw, 1e-6)


def _decal(kind, idx, n, lat, rng):
    """One decal tile: (thickness 0-1, coverage 0-1, clot 0-1) arrays in tile space [-1, 1]^2 (row 0 = top)."""
    c = (np.arange(n) + 0.5) / n * 2.0 - 1.0
    X, Y = np.meshgrid(c, c[::-1])
    th = np.zeros((n, n))
    clot = np.zeros((n, n))
    off = float(idx) * 1.37
    if kind == "drop_round":
        r = rng.uniform(0.38, 0.6)
        f = _disc_field(X, Y, 0, 0, r, lat, 0.06, 9, off)
        spines = lat.fbm((np.arctan2(Y, X) / (2 * np.pi)) % 1.0, np.full_like(X, off), 40, 1, octaves=2)
        f = np.maximum(f, _disc_field(X, Y, 0, 0, r * (1.0 + 0.16 * smooth(spines, 0.5, 0.75)), lat, 0.02, 4, off)
                       * 0.6)
        th = smooth(f, 0.0, 0.25) * (0.55 + 0.35 * smooth(f, 0.3, 0.9))
        rim = smooth(f, 0.0, 0.05) * (1.0 - smooth(f, 0.05, 0.22))
        th = th + rim * 0.25                                  # drying ring (coffee-ring edge)
        for _ in range(int(rng.integers(3, 9))):              # satellite droplets
            a = rng.uniform(0, 2 * np.pi)
            d = r * rng.uniform(1.15, 1.7)
            rr = rng.uniform(0.012, 0.045)
            th = np.maximum(th, smooth(_disc_field(X, Y, d * np.cos(a), d * np.sin(a), rr, lat, 0.1, 3, off + 2),
                                       0.0, 0.4) * 0.6)
    elif kind == "drop_angled":
        # impact at 20-60 deg: ellipse (width/length = sin(angle)) travelling toward +v, with a tail
        ang = math.radians(rng.uniform(20, 60))
        w = rng.uniform(0.14, 0.24)
        L = w / math.sin(ang)
        cy = -0.35 + (0.4 - L) * 0.3
        f = 1.0 - np.sqrt((X / w) ** 2 + ((Y - cy) / L) ** 2)
        f = f + (lat.fbm(X * 0.5 + 0.5, Y * 0.5 + 0.5, 6, octaves=2, offset=(off, off), tile=False) - 0.5) * 0.15
        th = smooth(f, 0.0, 0.25) * 0.8
        tail_y = cy + L
        tl = np.clip((Y - tail_y) / (0.55 * (1.0 - math.sin(ang)) + 0.1), 0.0, 1.0)
        tail = (1.0 - np.abs(X) / (w * 0.35 * (1.0 - tl) + 0.004)) * (Y > tail_y - 0.02) * (tl < 1.0)
        th = np.maximum(th, smooth(tail, 0.0, 0.3) * 0.55 * (1.0 - tl * 0.6))
        tip = _disc_field(X, Y, 0, tail_y + 0.55 * (1.0 - math.sin(ang)) + 0.12, w * 0.22, lat, 0.1, 3, off)
        th = np.maximum(th, smooth(tip, 0.0, 0.3) * 0.6)
    elif kind == "spatter":
        # cone of fine drops (0.2-3 mm at a 120 mm tile), density falling off from the source at the bottom
        k = int(rng.integers(120, 320))
        for _ in range(k):
            yy = rng.uniform(-1, 0.95)
            spread = 0.35 + 0.55 * (yy + 1) / 2
            xx = rng.normal(0, spread * 0.5)
            if abs(xx) > 0.97:
                continue
            rr = rng.lognormal(math.log(0.012), 0.55)
            e = 1.0 + rng.uniform(0.0, 1.8) * (rr < 0.02)
            dx, dy = X - xx, Y - yy
            f = 1.0 - np.sqrt(dx * dx + (dy / e) ** 2) / rr
            th = np.maximum(th, smooth(f, 0.0, 0.5) * rng.uniform(0.45, 0.85))
    elif kind == "run":
        # vertical run flowing toward -v: width thins, beads, a pendant bulb at the end
        x0 = rng.uniform(-0.15, 0.15)
        y_end = rng.uniform(-0.8, -0.55)
        wavy = (lat.fbm(np.full_like(Y, off * 0.1), Y * 0.5 + 0.5, 1, 6, octaves=3, offset=(off, 0), tile=False)
                - 0.5) * 0.12
        width = 0.05 + 0.03 * smooth(Y, y_end, 0.9)
        f = 1.0 - np.abs(X - x0 - wavy) / width
        f = f * (Y > y_end) * (Y < 0.95)
        th = smooth(f, 0.0, 0.4) * 0.75
        bulb = _disc_field(X, Y, x0 + wavy[np.argmin(np.abs(c[::-1] - y_end)), 0], y_end, 0.085, lat, 0.08, 4, off)
        th = np.maximum(th, smooth(bulb, 0.0, 0.4) * 0.95)
        head = _disc_field(X, Y, x0, 0.9, 0.12, lat, 0.2, 5, off + 1)
        th = np.maximum(th, smooth(head, 0.0, 0.4) * 0.6)
    elif kind == "smear":
        # wipe along +u: streaks from a finger/cloth, feathered trailing edge
        ang = rng.uniform(-0.35, 0.35)
        Xr = X * math.cos(ang) + Y * math.sin(ang)
        Yr = -X * math.sin(ang) + Y * math.cos(ang)
        h = rng.uniform(0.3, 0.55)
        band = 1.0 - np.abs(Yr) / (h * (1.0 + (lat.fbm(Xr * 0.5 + 0.5, np.full_like(X, off), 3, 1, octaves=2,
                                                     tile=False) - 0.5) * 0.5))
        streak = lat.fbm(np.full_like(X, off), Yr * 0.5 + 0.5, 1, 40, octaves=2, tile=False)
        along = np.clip((Xr + 0.85) / 1.7, 0, 1)
        load = (1.0 - along) ** 0.8
        th = smooth(band, 0.0, 0.35) * (0.25 + 0.65 * load) * (0.65 + 0.5 * smooth(streak, 0.3, 0.75))
        th = th * smooth(along, 0.0, 0.05) * (1.0 - smooth(along, 0.85, 1.0) * smooth(streak, 0.5, 0.2))
    elif kind == "pool":
        f = _disc_field(X, Y, 0, 0, rng.uniform(0.6, 0.8), lat, 0.28, 4, off)
        for _ in range(3):
            a = rng.uniform(0, 2 * np.pi)
            f = np.maximum(f, _disc_field(X, Y, 0.4 * np.cos(a), 0.4 * np.sin(a), rng.uniform(0.2, 0.4), lat, 0.2,
                                          4, off + 3))
        th = smooth(f, 0.0, 0.18) * (0.7 + 0.3 * smooth(f, 0.1, 0.6))
        serum = smooth(f, -0.04, 0.0) * (1.0 - smooth(f, 0.0, 0.02))
        th = th + serum * 0.12
        cl = lat.voronoi(X * 0.5 + 0.5, Y * 0.5 + 0.5, 7, 7, tile=False)
        clot = (1.0 - smooth(cl["F1"], 0.1, 0.45)) * smooth(cl["id"], 0.4, 0.55) * smooth(f, 0.15, 0.4)
    elif kind == "soak":
        # blood soaked into cloth/porous surface: dark core, lighter wicking halo with a tide line
        f = _disc_field(X, Y, 0, 0, rng.uniform(0.45, 0.65), lat, 0.3, 5, off)
        halo = _disc_field(X, Y, 0, 0, 0.88, lat, 0.25, 6, off + 5)
        th = smooth(f, 0.0, 0.3) * 0.8 + smooth(halo, 0.0, 0.2) * 0.22
        tide = smooth(halo, 0.0, 0.03) * (1.0 - smooth(halo, 0.03, 0.08))
        th = th + tide * 0.12
    elif kind == "crust":
        f = _disc_field(X, Y, 0, 0, rng.uniform(0.55, 0.75), lat, 0.25, 5, off)
        cr = lat.voronoi(X * 0.5 + 0.5, Y * 0.5 + 0.5, 10, 10, tile=False)
        crack = 1.0 - smooth(cr["edge"], 0.0, 0.06)
        th = smooth(f, 0.0, 0.2) * (0.8 - crack * 0.55)
        clot = smooth(f, 0.2, 0.6) * (1.0 - crack) * 0.4
    cov = np.clip(th * 4.0, 0.0, 1.0)
    fade = 1.0 - smooth(np.maximum(np.abs(X), np.abs(Y)), 0.93, 0.995)    # nothing touches the tile edge
    return np.clip(th, 0, 1) * fade, cov * fade, np.clip(clot, 0, 1) * fade


def decal_atlas(tile=256, grid_n=8):
    """64 blood stains in a ``grid_n`` x ``grid_n`` atlas of ``tile``-px tiles (row 0 = top).

    Returns (albedo RGBA uint8 sRGB with coverage in A, normal RGB uint8, ORM RGBA uint8 with A =
    thickness, list of tile descriptors).  Kinds are in DECAL_KINDS order, one row per kind; each tile's
    physical size is DECAL_TILE_MM[kind] and its travel/flow direction is +v (up) where relevant."""
    lat = gbc_lat("bake", 21, 1024)
    rng = gbc.rng("bake")
    N = tile * grid_n
    alb = np.zeros((N, N, 4))
    nrm = np.zeros((N, N, 3))
    orm = np.zeros((N, N, 4))
    info = []
    for row, kind in enumerate(DECAL_KINDS[:grid_n]):
        for col in range(grid_n):
            idx = row * grid_n + col
            th, cov, clot = _decal(kind, idx, tile, lat, rng)
            fine = gbc_lat("bake", 22, 1024).fbm(*grid(tile), 16, octaves=3, offset=(idx * 0.7, idx * 1.3))
            colr = mix(smooth(th, 0.05, 0.5), BLOOD_THIN, BLOOD_MID)
            colr = mix(smooth(th, 0.45, 0.85), colr, BLOOD_THICK)
            colr = mix(clot * 0.85, colr, BLOOD_CLOT)
            colr = colr * (0.9 + 0.2 * fine[..., None])
            tile_mm = DECAL_TILE_MM[kind]
            height = th * (0.4 if kind in ("pool", "drop_round") else 0.25) + clot * 0.6
            n_ = height_to_normal(height, tile_mm / tile, wrap=False, strength=3.0)
            rough = mix(smooth(th, 0.1, 0.6), 0.25, 0.08) + clot * 0.45
            ao = np.clip(1.0 - clot * 0.3, 0, 1)
            y0, x0 = row * tile, col * tile
            alb[y0:y0 + tile, x0:x0 + tile, :3] = colr
            alb[y0:y0 + tile, x0:x0 + tile, 3] = cov
            nrm[y0:y0 + tile, x0:x0 + tile] = n_
            orm[y0:y0 + tile, x0:x0 + tile] = np.stack([ao, rough, np.zeros_like(ao), th], -1)
            info.append({"index": idx, "kind": kind, "rect_px": [x0, y0, tile, tile], "tile_mm": tile_mm,
                         "direction": "+v" if kind in ("drop_angled", "spatter") else
                         ("-v flow" if kind == "run" else ("+u wipe" if kind == "smear" else "none"))})
    alb_u8 = np.concatenate([to_u8(linear_to_srgb(alb[..., :3])), to_u8(alb[..., 3:])], -1)
    return alb_u8, to_u8(nrm * 0.5 + 0.5), to_u8(orm), info


# ---------------------------------------------------------------------------
# Room and prop tileables (plan §4.2 "Room: tile, grout, epoxy, rubber, steel"; B8 materials)
# ---------------------------------------------------------------------------
ROOM_TILE_M = {"room_tile": 0.15, "room_grout": 0.05, "room_epoxy": 0.5, "room_rubber": 0.25,
               "room_stainless": 0.2, "room_galvanised": 0.4, "prop_polymer_stipple": 0.04,
               "prop_walnut": 0.25, "prop_hickory": 0.25, "prop_g10": 0.05, "prop_glove": 0.06}


def room_tile(n=1024):
    """One glazed ceramic wall tile, 150 mm, white-grey with faint glaze waviness and pinholes.
    The glaze fills the whole texture (the tile's rounded edges are real geometry in room.glb)."""
    lat = gbc_lat("room", 1)
    u, v = grid(n)
    tm = ROOM_TILE_M["room_tile"] * 1000 / n
    w = lat.fbm(u, v, 2, octaves=4)
    col = np.stack([0.70 + 0.03 * w, 0.71 + 0.03 * w, 0.70 + 0.03 * w], -1)
    speck = lat.voronoi(u, v, 90, 90)
    pin = (1.0 - smooth(speck["F1"], 0.0, 0.06)) * smooth(speck["id"], 0.93, 0.95)
    col = mix(pin * 0.5, col, (0.35, 0.35, 0.34))
    h = (w - 0.5) * 0.06 - pin * 0.05
    rough = 0.06 + (lat.fbm(u, v, 8, octaves=2) - 0.5) * 0.04 + pin * 0.3
    return {"albedo": col, "height": h, "rough": rough, "ao": np.ones_like(h), "texel_mm": tm}


def room_grout(n=512):
    """Cement grout: grey, sandy, porous and matte (absorbent: blood soaks in and stains)."""
    lat = gbc_lat("room", 2)
    u, v = grid(n)
    tm = ROOM_TILE_M["room_grout"] * 1000 / n
    sand = lat.voronoi(u, v, 110, 110)
    g = lat.fbm(u, v, 6, octaves=4)
    col = ramp(g * 0.6 + sand["id"] * 0.4, [(0.2, (0.22, 0.215, 0.20)), (0.8, (0.36, 0.35, 0.33))])
    grit = 1.0 - smooth(sand["edge"], 0.0, 0.12)
    col = col * (1.0 - grit[..., None] * 0.15)
    h = (1.0 - smooth(sand["F1"], 0.0, 0.5)) * 0.15 + g * 0.1
    return {"albedo": col, "height": h, "rough": 0.9 + grit * 0.05, "ao": cavity_ao(h, tm, 0.5, 0.1),
            "texel_mm": tm}


def room_epoxy(n=1024):
    """Grey epoxy floor with a fine decorative quartz fleck, orange-peel roll texture, scuffs."""
    lat = gbc_lat("room", 3)
    u, v = grid(n)
    tm = ROOM_TILE_M["room_epoxy"] * 1000 / n
    base = lat.fbm(u, v, 3, octaves=4)
    col = np.stack([0.16 + 0.02 * base, 0.165 + 0.02 * base, 0.17 + 0.02 * base], -1)
    fl = lat.voronoi(u, v, 160, 160)
    fleck = (1.0 - smooth(fl["F1"], 0.0, 0.18)) * smooth(fl["id"], 0.7, 0.72)
    col = mix(fleck * np.where(fl["id"] > 0.86, 0.9, 0.6), col,
              np.where((fl["id"] > 0.86)[..., None], (0.45, 0.45, 0.44), (0.05, 0.05, 0.055)))
    peel = lat.fbm(u, v, 48, octaves=2)
    scuff = ridge(lat.fbm(u, v, 4, 24, octaves=2, offset=(1.1, 3.3)), 0.01) * smooth(lat.fbm(u, v, 3), 0.55, 0.7)
    col = mix(scuff * 0.4, col, col * 1.35)
    h = (peel - 0.5) * 0.04
    rough = 0.22 + scuff * 0.3 + (base - 0.5) * 0.06
    return {"albedo": col, "height": h, "rough": rough, "ao": np.ones_like(h), "texel_mm": tm}


def room_rubber(n=1024):
    """Recycled rubber granulate (bullet backstop): black EPDM crumbs 1-4 mm in a binder, a few
    grey and coloured flecks; very matte, deep crevices (absorbent)."""
    lat = gbc_lat("room", 4)
    u, v = grid(n)
    tm = ROOM_TILE_M["room_rubber"] * 1000 / n
    a = lat.voronoi(u, v, 110, 110, jitter=1.0)
    b = lat.voronoi(u, v, 230, 230, jitter=1.0)
    crumb = np.maximum(smooth(a["edge"], 0.02, 0.2), smooth(b["edge"], 0.02, 0.2) * 0.6)
    tone = a["id"]
    col = ramp(tone, [(0.0, (0.018, 0.018, 0.019)), (0.9, (0.032, 0.032, 0.033)), (0.95, (0.09, 0.09, 0.09)),
                      (1.0, (0.12, 0.05, 0.03))])
    col = col * (0.5 + 0.5 * crumb[..., None])
    h = crumb * 0.9 + (lat.fbm(u, v, 200, octaves=2) - 0.5) * 0.2
    return {"albedo": col, "height": h, "rough": 0.92 - crumb * 0.08, "ao": cavity_ao(h, tm, 2.0, 0.6),
            "texel_mm": tm}


def room_stainless(n=1024):
    """Brushed 304 stainless (table, trolley, drain, door plate): directional brushing along u,
    faint smudges.  Metallic 1, albedo is the F0 colour."""
    lat = gbc_lat("room", 5)
    u, v = grid(n)
    tm = ROOM_TILE_M["room_stainless"] * 1000 / n
    brush = lat.fbm(u, v, 2, 512, octaves=2)
    smudge = smooth(lat.fbm(u, v, 3, octaves=4, offset=(2.2, 1.1)), 0.55, 0.8)
    f0 = 0.56 + 0.05 * (brush - 0.5)
    col = np.stack([f0 * 0.99, f0 * 0.98, f0 * 0.97], -1) * (1.0 - smudge[..., None] * 0.08)
    h = (brush - 0.5) * 0.004
    rough = 0.28 + (brush - 0.5) * 0.12 + smudge * 0.12
    return {"albedo": col, "height": h, "rough": rough, "ao": np.ones_like(h), "texel_mm": tm, "metal": 1.0}


def room_galvanised(n=512):
    """Hot-dip galvanised steel (backstop frame): spangle crystals, dull grey, metallic."""
    lat = gbc_lat("room", 6)
    u, v = grid(n)
    tm = ROOM_TILE_M["room_galvanised"] * 1000 / n
    sp = lat.voronoi(u, v, 24, 24)
    fe = (np.arctan2(sp["dy"], sp["dx"]) / (2 * np.pi)) % 1.0
    feath = 0.5 + 0.5 * np.cos((fe * 12 + sp["id"] * 7) * 2 * np.pi) * smooth(sp["F1"], 0.05, 0.4)
    f0 = 0.42 + 0.08 * sp["id"] + 0.03 * feath
    col = np.stack([f0, f0 * 1.01, f0 * 1.02], -1)
    h = feath * 0.004
    rough = 0.35 + 0.2 * sp["id"]
    return {"albedo": col, "height": h, "rough": rough, "ao": np.ones_like(h), "texel_mm": tm, "metal": 1.0}


def prop_polymer_stipple(n=512):
    """Pistol grip stipple on black polymer: dense raised cones 0.4-0.8 mm."""
    lat = gbc_lat("props", 1)
    u, v = grid(n)
    tm = ROOM_TILE_M["prop_polymer_stipple"] * 1000 / n
    s = lat.voronoi(u, v, 64, 64, jitter=0.9)
    cone = 1.0 - smooth(s["F1"], 0.0, 0.5)
    col = np.full(u.shape + (3,), 0.022) * (0.9 + 0.2 * cone[..., None])
    h = cone * 0.25
    return {"albedo": col, "height": h, "rough": 0.7 - cone * 0.15, "ao": cavity_ao(h, tm, 0.4, 0.1),
            "texel_mm": tm}


def _wood(lat, u, v, light, dark, rings, fig, tm):
    uw, vw = warp(lat, u, v, 3, 0.03)
    ring = lat.fbm(uw, vw, 1, rings, octaves=1)
    grain = 0.5 + 0.5 * np.sin((vw * rings * 6.0 + ring * 4.0) * 2 * np.pi)
    pores = lat.fbm(u, v, 8, 512, octaves=2, offset=(3.3, 0.0))
    col = mix(smooth(grain, 0.3, 0.9) * 0.7 + smooth(pores, 0.62, 0.75) * 0.3, light, dark)
    col = col * (0.9 + 0.2 * lat.fbm(u, v, fig, octaves=3)[..., None])
    h = -smooth(pores, 0.62, 0.75) * 0.02 + grain * 0.005
    return col, h


def prop_walnut(n=512):
    """Oiled walnut (shotgun stock / forend): dark brown with black streaks, open pores."""
    lat = gbc_lat("props", 2)
    u, v = grid(n)
    tm = ROOM_TILE_M["prop_walnut"] * 1000 / n
    col, h = _wood(lat, u, v, (0.16, 0.075, 0.035), (0.045, 0.020, 0.010), 9, 3, tm)
    return {"albedo": col, "height": h, "rough": 0.38, "ao": np.ones_like(h), "texel_mm": tm}


def prop_hickory(n=512):
    """Lacquered hickory hammer handle: pale honey sapwood with brown heart streaks."""
    lat = gbc_lat("props", 3)
    u, v = grid(n)
    tm = ROOM_TILE_M["prop_hickory"] * 1000 / n
    col, h = _wood(lat, u, v, (0.52, 0.34, 0.16), (0.24, 0.12, 0.05), 11, 2, tm)
    return {"albedo": col, "height": h, "rough": 0.3, "ao": np.ones_like(h), "texel_mm": tm}


def prop_g10(n=512):
    """G10 knife scales: black glass-epoxy laminate with a fine milled texture."""
    lat = gbc_lat("props", 4)
    u, v = grid(n)
    tm = ROOM_TILE_M["prop_g10"] * 1000 / n
    mill = lat.voronoi(u, v, 40, 40)
    h = (1.0 - smooth(mill["F1"], 0.0, 0.6)) * 0.12
    col = np.full(u.shape + (3,), 0.018) * (0.85 + 0.3 * lat.fbm(u, v, 12, octaves=2)[..., None])
    return {"albedo": col, "height": h, "rough": 0.62, "ao": cavity_ao(h, tm, 0.4, 0.05), "texel_mm": tm}


def prop_glove(n=512):
    """Black synthetic-leather glove palm: fine pebble grain and creases."""
    lat = gbc_lat("props", 5)
    u, v = grid(n)
    tm = ROOM_TILE_M["prop_glove"] * 1000 / n
    peb = lat.voronoi(u, v, 70, 70)
    crease = ridge(lat.fbm(u, v, 3, octaves=3), 0.01)
    h = smooth(peb["edge"], 0.0, 0.3) * 0.05 - crease * 0.08
    col = np.full(u.shape + (3,), 0.02) * (0.9 + 0.2 * smooth(peb["edge"], 0.0, 0.3)[..., None])
    return {"albedo": col, "height": h, "rough": 0.55 + crease * 0.1, "ao": cavity_ao(h, tm, 0.4, 0.05),
            "texel_mm": tm}


ROOM_TEXTURES = {
    "room_tile": room_tile, "room_grout": room_grout, "room_epoxy": room_epoxy, "room_rubber": room_rubber,
    "room_stainless": room_stainless, "room_galvanised": room_galvanised,
    "prop_polymer_stipple": prop_polymer_stipple, "prop_walnut": prop_walnut, "prop_hickory": prop_hickory,
    "prop_g10": prop_g10, "prop_glove": prop_glove,
}

# B8 material name -> room/prop texture set (G7 applies them triplanar / in metres)
PROP_MATERIAL_TEXTURES = {
    "GBPM_room_tile": "room_tile", "GBPM_room_grout": "room_grout", "GBPM_room_epoxy": "room_epoxy",
    "GBPM_room_rubber": "room_rubber", "GBPM_room_stainless": "room_stainless",
    "GBPM_room_galv": "room_galvanised", "GBPM_polymer_grip": "prop_polymer_stipple",
    "GBPM_polymer": "prop_polymer_stipple", "GBPM_walnut": "prop_walnut", "GBPM_hickory": "prop_hickory",
    "GBPM_g10_black": "prop_g10", "GBPM_glove": "prop_glove", "GBPM_glove_pad": "prop_glove",
    "GBPM_steel_satin": "room_stainless", "GBPM_steel_polished": "room_stainless",
}


# ---------------------------------------------------------------------------
# PNG reading (checks; pure numpy + zlib, 8-bit grey/RGB/RGBA, all five filter types)
# ---------------------------------------------------------------------------
def png_size(path):
    """(width, height, channels) from a PNG header."""
    import struct
    with open(path, "rb") as fh:
        head = fh.read(33)
    w, h, _bd, ct = struct.unpack(">IIBB", head[16:26])
    return w, h, {0: 1, 2: 3, 4: 2, 6: 4}[ct]


def read_png(path):
    """Decode an 8-bit PNG into a uint8 (H, W, C) array (row 0 = top)."""
    import struct
    import zlib
    data = open(path, "rb").read()
    pos, idat = 8, []
    w = h = ct = None
    while pos < len(data):
        n, = struct.unpack(">I", data[pos:pos + 4])
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        pos += 12 + n
        if tag == b"IHDR":
            w, h, bd, ct = struct.unpack(">IIBB", body[:10])
            if bd != 8:
                raise ValueError("only 8-bit PNGs")
        elif tag == b"IDAT":
            idat.append(body)
    c = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    raw = np.frombuffer(zlib.decompress(b"".join(idat)), np.uint8).reshape(h, w * c + 1)
    out = np.zeros((h, w * c), np.uint8)
    prev = np.zeros(w * c, np.int32)
    for r in range(h):
        f = raw[r, 0]
        line = raw[r, 1:].astype(np.int32)
        if f == 0:
            cur = line
        elif f == 2:
            cur = (line + prev) & 255
        else:                                          # 1 sub, 3 average, 4 paeth: per-pixel loop
            cur = np.zeros_like(line)
            for i in range(w * c):
                a = cur[i - c] if i >= c else 0
                b = prev[i]
                cc = prev[i - c] if i >= c else 0
                if f == 1:
                    pred = a
                elif f == 3:
                    pred = (a + b) // 2
                else:
                    p = a + b - cc
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - cc)
                    pred = a if pa <= pb and pa <= pc else (b if pb <= pc else cc)
                cur[i] = (line[i] + pred) & 255
        out[r] = cur
        prev = cur
    return out.reshape(h, w, c)
