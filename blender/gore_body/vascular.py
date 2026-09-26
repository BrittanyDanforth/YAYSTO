"""Vessel network and nerves (owner B5).  Plan §3.4.1, §5.2, §5.8 vessels.json, §8.2 B5.

Final entry points
------------------
``build_vessels()`` -> {"GB_Vessels_Art": obj, "GB_Vessels_Ven": obj, "GBV_<segment>": curve, "GBN_<nerve>_<side>": curve}
``vessel_table()``  -> vessels.json ``data``: segments (fitted centreline ``[x, y, z, r]`` per point, bones per
                       point, measured depths), beds, nerves, collaterals, pulse data, fit report

How the network is made
-----------------------
1. **Rows.**  ``gb_data.vessels`` holds one row per named vessel: every RB §3.3 row plus the B5 additions of
   plan §3.4.1 (circle of Willis, dural sinuses, face/scalp veins, axillary/brachial/forearm veins,
   epigastric, gluteal, lumbar, azygos system, portal tributaries, coronary sinus, calf veins) = 84 named
   vessels.  ``vessel_segments()`` expands them into 201 left/right/branch segments, proximal (heart side)
   first; ``d_mm`` is the proximal diameter, ``d_end_mm`` the distal one.
2. **Centrelines** (``centreline``).  Catmull-Rom through the waypoints (``gore_head.anatomy.catmull``),
   arc-length resampled per span at ``min(10 mm, 2 x diameter)`` so every waypoint stays a sample;
   radius tapered ``d_mm`` -> ``d_end_mm``; the facial and superficial temporal arteries get their
   typical tortuosity (``TORTUOUS``).
3. **Fit to the built body** (``fit_network``).  Waypoints are bible/E fits to landmark tables; the built
   skin (B1/B2), skeleton (B3), brain and heart (B4) are other surfaces, so every centreline is fitted in
   the built scene, parents before children (a branch origin stays on its parent's fitted centreline):

   * skin depth (centreline to nearest GB_Body/GB_Head surface; inside = first hit is a back face on 2 of
     3 rays): every point at least ``max(r + 1.3 mm, 0.5 x listed depth)`` deep (plan §3.4.1 step 4);
     subcutaneous vessels (``SUPERFICIAL_T``) held inside their listed band; ``ZONES`` hold FB-5 and a few
     other spot depths (CCA/IJV at C4-C6, femoral at the groin, brachial mid-arm, radial/ulnar at the
     wrist, ankle arteries);
   * bone (hard, wins over depth bands): no tube wall within 0.5 mm of ``GB_Skeleton`` except in canals
     and grooves (``BONE_CANAL``: vertebral foramina, carotid canal, jugular foramen, meningeal and sinus
     grooves); where the nearest-surface push oscillates (joint gaps, notches) the shortest free move
     along 26 directions is taken;
   * brain: nothing inside ``GB_Brain`` (0.3 mm); dural sinuses are snapped under the inner table and
     faired (sigma 12 mm); coronary arteries and sinus are laid on the B4 epicardium, half sunk in fat.

   Corrections are Gaussian-smoothed along the vessel, capped at 4 mm per iteration, then the moved
   stretches are faired (sigma 5 mm) and re-relaxed.  The fitted centreline is stored in the
   ``GBV_<segment>`` curve (point radius = vessel radius, measured depths as custom props);
   ``vessel_table()`` reads the curves, so ``vessels.json`` is exactly what the tubes show.
4. **Tubes** (``_tube_parts``).  Sides from the mean diameter: 12 for >= 15 mm, 8 for 6-15, 6 for 3-6, 4 for
   1.5-3, none below (data only); rings where the centreline bends (Douglas-Peucker, tolerance
   ``max(0.5 r, 2 mm)``, 0.8 mm on tortuous arteries) and at least every 50 mm; veins flattened 0.8
   against the skin, the sagittal sinus a rounded triangle; end caps.  Mesh by blood colour
   (``mesh_for``): ``GB_Vessels_Art`` = systemic arteries + pulmonary veins, ``GB_Vessels_Ven`` = systemic
   and portal veins + pulmonary arteries.  UV2 = (vessel index, t along the segment).
5. **Nerves.**  Data-only ``GBN_<nerve>_<side>`` curves fitted with the same skin/bone rules (the radial
   nerve may touch the humerus in the spiral groove).
6. **Checks** (``graph_report``, ``fb5_report``, ``bone_report``, ``tube_vertices_in_bone``,
   ``skin_report``, ``waypoint_report``) are called by ``verify.py``; ``render_sections`` and
   ``render_xray`` make the review images.

Run alone (loads the newest skin/head/skeleton/viscera/neuro stage caches, builds, reports, renders)::

    python3 vascular.py [--render] [--no-fit] [--views front,heart,... [--anat]]
"""
import glob
import math
import os
import re
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import nerves as NV  # noqa: E402
from gb_data import vertebrae as VT  # noqa: E402
from gb_data import vessels as VS  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402

MM = 1e-3
SKIN_FLOOR_MM = 1.3            # skin (dermis) under which a tube wall may lie [RB §7.6: limbs 1.0-2.0 mm]
BONE_CLEAR_MM = 0.5            # gap between a tube wall and bone
BRAIN_CLEAR_MM = 0.3           # gap between an intracranial tube wall and the brain surface
FIT_ITERS = 24
MAX_STEP = 0.004              # m, largest fit move per iteration
FAIR_SIGMA = 0.005            # m, final fairing of the fitted centreline
RING_MAX_STEP = 0.055          # m, longest straight run between two tube rings (skinning needs rings)
VEIN_FLATTEN = 0.8             # vein section: minor / major axis (short axis along the skin normal)
HEAD_CENTRE = np.array([0.0, 0.020, 1.680])   # cranial-cavity centre used for the under-skull snap

# C4-C6 band for the neck tests (vertebra centres, RB §7.3)
_C4Z, _C6Z = VT.VERTEBRA["C4"]["z"], VT.VERTEBRA["C6"]["z"]

# Depth zones (mm, centreline to nearest skin) that the fit holds; the FB-5 rows are the acceptance test
# [plan §8.1 FB-5, RB §7.6].  selector: ("z", lo, hi) body height, ("t", lo, hi) arc fraction from the
# proximal end, ("end", metres) the last metres of the segment (distal end).
ZONES = {
    "A04": [(("z", _C6Z, _C4Z), 21.0, 29.0, "FB-5 CCA 20-30 mm at C4-C6")],
    "V01": [(("z", _C6Z, _C4Z), 21.0, 29.0, "FB-5 IJV 20-30 mm at C4-C6")],
    "A28": [(("t", 0.0, 1.0), 17.0, 28.0, "FB-5 femoral artery 15-30 mm at the groin")],
    "A41": [(("t", 0.30, 0.70), 11.0, 19.0, "FB-5 brachial 10-20 mm mid-arm"),
            (("t", 0.85, 1.0), 8.0, 14.0, "brachial ~1 cm at the elbow [RB §3.3]")],
    "A42": [(("end", 0.030), 2.6, 4.6, "FB-5 radial 2-5 mm at the wrist")],
    "A43": [(("end", 0.030), 5.0, 9.0, "ulnar 4-10 mm at the wrist [RB §7.6]")],
    "A32": [(("z", 0.0, 0.095), 4.0, 9.0, "dorsalis pedis / front of the ankle ~5 mm"),
            (("z", 0.15, 0.40), 14.0, 45.0, "anterior tibial on the interosseous membrane")],
    "A33": [(("z", 0.0, 0.12), 8.0, 13.0, "posterior tibial ~1 cm behind the medial malleolus")],
    "V15": [(("z", 0.88, 0.95), 17.0, 32.0, "femoral vein 2-4 cm at the groin")],
    "A27": [(("end", 0.030), 17.0, 28.0, "external iliac reaching the mid-inguinal point 2-4 cm deep")],
}
# Vessels whose listed depth band [RB §3.3 / §7.6] describes the whole course (subcutaneous vessels), with the
# arc fraction (from the proximal end) over which it is held; every other listed depth is a spot value and is
# only used as the 0.5 x depth floor (plan §3.4.1 step 4) or through ZONES.
SUPERFICIAL_T = {"A07": (0.0, 1.0), "A08": (0.15, 1.0), "A09": (0.40, 1.0), "V02": (0.2, 1.0),
                 "V17": (0.08, 1.0), "V20_cephalic": (0.08, 1.0), "V20_basilic": (0.30, 1.0),
                 "V20_median_cubital": (0.0, 1.0), "V35": (0.0, 1.0), "V40": (0.12, 1.0), "V33": (0.2, 1.0)}
# Per-point bone-rule exemptions: vessels (or z bands of them) that run in bone canals
# (vertebral artery C6-C1 transverse foramina + foramen magnum; petrous carotid canal; middle meningeal groove
# of the inner table; occipital groove medial to the mastoid; jugular foramen at the top of the IJV; the
# dural sinuses lie in bony grooves the head project's skull does not carve; the vertebro-basilar junction
# at the foramen magnum sits on the modelled lower clivus)
BONE_CANAL = {"A10": (1.505, 1.628), "A11": (-1.0, 1.628), "A50": (-1.0, 9.0), "A12": (-1.0, 9.0), "A09": (1.600, 1.645),
              "V01": (1.600, 9.0), "V30": (-1.0, 9.0), "V31": (-1.0, 9.0), "V32": (-1.0, 9.0)}
CRANIAL = {"A11", "A50", "A51", "A52", "A53", "A54"}               # intracranial arteries (outside GB_Brain)
UNDER_SKULL = {"V30", "V31", "V32"}               # dural sinuses: snapped under the inner table, on the brain
ON_HEART = {"A13", "V45"}                          # coronary arteries / sinus: on the epicardium (B4 heart)
HEART_CENTRE = np.array([0.035, -0.036, 1.325])    # organs.json heart OBB centre
TRI_SECTION = {"V30"}                                               # triangular dural sinus section
# may touch bone: costal groove, meningeal groove, spiral groove; the basilar sits in a 3 mm prepontine gap
# between the head project's clivus and pons (a 3.5 mm artery cannot clear both)
BONE_CONTACT_OK = {"A16", "A12", "A11", "radial"}


# ===========================================================================
# Bible waypoints (for the 2 mm acceptance check) - parsed from RB §3.3 itself
# ===========================================================================
def bible_waypoints():
    """{vessel id: {"points": [(x, y, z), ...], "E": bool}} from the RB §3.3 tables (None if docs missing).

    ``E`` marks rows whose waypoint column says (E) (the bible's own ±10-20 mm fits)."""
    path = os.path.join(gbc.GAME_DIR, "docs", "REALISM_BIBLE.md")
    if not os.path.exists(path):
        return None
    text = open(path, encoding="utf-8").read()
    a = text.find("### 3.3")
    b = text.find("### 3.4", a)
    out = {}
    num = r"[-−±]?\d*\.\d+|[-−±]?\d+"
    section_e = False
    for line in text[a:b].splitlines():
        if line.startswith("**"):                         # table header, e.g. "**Upper limb** (A-pose ...) (E):"
            section_e = "(E)" in line
        m = re.match(r"^\| *([AVP]\d+) *\|", line)
        if not m:
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) < 8:
            continue
        wp = cols[7]
        pts = []
        for tup in re.findall(r"\(([^()]*)\)", wp):
            parts = [p.strip() for p in tup.split(",")]
            if len(parts) != 3 or not all(re.fullmatch(num, p) for p in parts):
                continue
            vals = [p.replace("−", "-") for p in parts]
            if vals[0].startswith("±"):
                x = float(vals[0][1:])
                pts += [(x, float(vals[1]), float(vals[2])), (-x, float(vals[1]), float(vals[2]))]
            else:
                pts.append(tuple(float(v) for v in vals))
        out[m.group(1)] = {"points": pts, "E": section_e or "(E)" in wp}
    return out


# ===========================================================================
# Centrelines
# ===========================================================================
OXYGENATED = ("systemic_art", "pulmonary_ven")      # bright arterial blood [RB §3.10]


def blood_of(seg):
    """'oxygenated' (systemic arteries, pulmonary veins) or 'deoxygenated' (systemic/portal veins, pulmonary
    arteries): the colour a cut vessel bleeds and the mesh it is drawn in (atlas convention)."""
    return "oxygenated" if seg["circuit"] in OXYGENATED else "deoxygenated"


def sides_for(seg):
    """Tube sides from the segment's mean diameter (plan §3.4.1 table; tapering vessels use the mean)."""
    return VS.tube_sides(0.5 * (seg["d_mm"] + (seg["d_end_mm"] or seg["d_mm"])))


def mesh_for(seg):
    """Mesh a segment belongs to, by blood colour: 'GB_Vessels_Art' (oxygenated: systemic arteries and the
    pulmonary veins) / 'GB_Vessels_Ven' (systemic and portal veins and the pulmonary arteries); None below
    1.5 mm (data only)."""
    if sides_for(seg) == 0:
        return None
    return "GB_Vessels_Art" if blood_of(seg) == "oxygenated" else "GB_Vessels_Ven"


def _arc(P):
    s = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
    return s


def resample_knots(points, step, n_dense=16):
    """Catmull-Rom through the waypoints, arc-length resampled per span so every waypoint stays a sample.

    Returns (P[M,3], t[M]) with t the normalised arc parameter (0..1)."""
    import gb_geom as gg
    p = np.asarray(points, float)
    if len(p) > 2:
        dense = gg.head().catmull(p, n=n_dense)
    else:
        dense = np.vstack([p[0] + (p[-1] - p[0]) * k / n_dense for k in range(n_dense)] + [p[-1]])
    out = [dense[0]]
    for k in range(len(p) - 1):
        span = dense[k * n_dense:(k + 1) * n_dense + 1]
        sa = _arc(span)
        m = max(1, int(math.ceil(sa[-1] / max(step, 1e-6))))
        tgt = np.linspace(0.0, sa[-1], m + 1)[1:]
        out += list(np.stack([np.interp(tgt, sa, span[:, i]) for i in range(3)], axis=1))
    P = np.array(out)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-9])
    P = P[keep]
    sa = _arc(P)
    return P, sa / max(sa[-1], 1e-12)


# Tortuous arteries (facial, superficial temporal; anatomy texts call both "tortuous" so they can follow
# the jaw and the scalp): lateral waviness (amplitude mm, wavelength mm) added to the raw centreline,
# deterministic, fading in over the first wavelength
TORTUOUS = {"A08": (2.0, 22.0), "A07": (1.3, 16.0)}


def _tortuosity(P, amp, wavelength):
    s = _arc(P)
    T = np.gradient(P, axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    side = np.cross(T, np.array([0.0, 0.0, 1.0]))
    bad = np.linalg.norm(side, axis=1) < 1e-3
    side[bad] = np.cross(T[bad], np.array([1.0, 0.0, 0.0]))
    side /= np.linalg.norm(side, axis=1, keepdims=True)
    fade = np.clip(s / (wavelength * MM), 0.0, 1.0) * np.clip((s[-1] - s) / (0.5 * wavelength * MM), 0.0, 1.0)
    return P + side * (amp * MM * np.sin(2.0 * np.pi * s / (wavelength * MM)) * fade)[:, None]


def centreline(seg):
    """Raw resampled centreline (P[M,3], r[M], t[M]) of a segment from its waypoints (plan §3.4.1 step 2)."""
    d0 = seg["d_mm"] * MM
    d1 = (seg["d_end_mm"] or seg["d_mm"]) * MM
    step = min(0.010, 2.0 * d0)
    P, t = resample_knots(seg["points"], step)
    if seg["vessel"] in TORTUOUS:
        P = _tortuosity(P, *TORTUOUS[seg["vessel"]])
    r = 0.5 * (d0 + (d1 - d0) * t)
    return P, r, t


def nerve_rows():
    """Left/right nerve rows: [{"id", "nerve", "side", "roots", "radius", "points", "deficit", "note"}]."""
    out = []
    for nid, n in NV.NERVES.items():
        for side, sx in (("L", 1.0), ("R", -1.0)):
            pts = [(sx * p[0], p[1], p[2]) for p in n["points"]]
            out.append({"id": f"{nid}_{side}", "nerve": nid, "side": side, "roots": n["roots"],
                        "radius": n["radius"], "points": pts, "deficit": n["deficit"], "note": n["note"]})
    return out


def nerve_centreline(nv):
    """Raw resampled nerve centreline (P, r, t) at 8 mm steps."""
    P, t = resample_knots(nv["points"], 0.008)
    return P, np.full(len(P), nv["radius"]), t


# ===========================================================================
# Scene probe: skin depth, bone and brain distance, skull inner table (BVH on the built meshes)
# ===========================================================================
class Probe:
    """Distance queries against the built scene (GB_Body + GB_Head skin, GB_Skeleton, GB_Brain)."""

    PARITY_DIRS = ((1.0, 0.0, 0.0), (0.0, 0.0, 1.0), (0.3, 0.9, 0.3))

    def __init__(self):
        import bpy
        self.bpy = bpy
        self.skin = self._bvh([n for n in ("GB_Body", "GB_Head") if n in bpy.data.objects])
        self.bone = self._bvh(["GB_Skeleton"] if "GB_Skeleton" in bpy.data.objects else [])
        self.brain = self._bvh(["GB_Brain"] if "GB_Brain" in bpy.data.objects else [])
        self.heart = self._organ_bvh(1)                   # gb_data.organs: heart = organ id 1
        self.sources = {n: bpy.data.objects[n].get("gb_status", "?") for n in
                        ("GB_Body", "GB_Head", "GB_Skeleton", "GB_Brain") if n in bpy.data.objects}

    def _bvh(self, names):
        from mathutils.bvhtree import BVHTree
        if not names:
            return None
        V, T, off = [], [], 0
        for n in names:
            v, t = gbc.mesh_arrays(self.bpy.data.objects[n].data)
            V.append(v)
            T.append(t + off)
            off += len(v)
        return BVHTree.FromPolygons(np.vstack(V).tolist(), np.vstack(T).tolist())

    def _organ_bvh(self, organ_id):
        """BVH of the GB_Organs faces of one organ (B4 writes the ``gb_organ`` point attribute)."""
        from mathutils.bvhtree import BVHTree
        o = self.bpy.data.objects.get("GB_Organs")
        if o is None or "gb_organ" not in o.data.attributes:
            return None
        v, t = gbc.mesh_arrays(o.data)
        org = gbc.read_point_attr(o, "gb_organ", 'INT')
        keep = (org[t] == organ_id).all(axis=1)
        if not keep.any():
            return None
        return BVHTree.FromPolygons(v.tolist(), t[keep].tolist())

    def epicardium(self, P, centre):
        """Outer heart surface point along the ray centre -> p (first heart hit coming from outside)."""
        from mathutils import Vector
        out = []
        for p in np.asarray(P, float):
            d = p - centre
            n = np.linalg.norm(d)
            if self.heart is None or n < 1e-6:
                out.append(None)
                continue
            d /= n
            o = centre + d * 0.15
            loc, _nrm, _i, _dist = self.heart.ray_cast(Vector(o), Vector(-d), 0.15)
            out.append(None if loc is None else (np.array(loc), d))
        return out

    def _inside(self, bvh, p):
        """Inside test that also works for double shells (bone cortex + marrow core) and open lips:
        along each of three rays the FIRST surface hit is a back face (we are leaving a solid)."""
        from mathutils import Vector
        votes = 0
        for d in self.PARITY_DIRS:
            d = Vector(d).normalized()
            loc, nrm, _i, _dist = bvh.ray_cast(Vector(p), d)
            if loc is not None and nrm.dot(d) > 0.0:
                votes += 1
        return votes >= 2

    def _signed(self, bvh, P, limit=None):
        """(signed distance[N] m, + outside; unit direction[N,3] that increases it) to a closed surface."""
        from mathutils import Vector
        P = np.asarray(P, float)
        sd = np.full(len(P), 1.0)
        nout = np.zeros((len(P), 3))
        nout[:, 2] = 1.0
        if bvh is None:
            return sd, nout
        for i, p in enumerate(P):
            q = Vector(p)
            loc, nrm, _i, dist = bvh.find_nearest(q, limit) if limit else bvh.find_nearest(q)
            if loc is None:
                continue
            inside = self._inside(bvh, p)
            v = np.asarray(q - loc)
            n = float(np.linalg.norm(v))
            u = v / n if n > 1e-9 else np.asarray(nrm)
            sd[i] = -dist if inside else dist
            nout[i] = -u if inside else u
        return sd, nout

    def skin_depth(self, P, parity=True):
        """(depth[N] m, positive inside; outward unit direction[N,3]) to the nearest skin surface."""
        if self.skin is None:
            P = np.asarray(P, float)
            return np.ones(len(P)), np.tile([0.0, 0.0, 1.0], (len(P), 1))
        sd, nout = self._signed(self.skin, P)
        return -sd, nout

    def bone_dist(self, P):
        return self._signed(self.bone, P, 0.04)

    _DIRS = None

    def bone_escape(self, p, sd, u, need):
        """Move that takes a centreline point to ``need`` metres clear of bone.

        The nearest-surface push is used when it works; in a joint gap or a notch (two bone surfaces
        close together, where the nearest surface flips every iteration) the shortest move along 26
        directions that ends clear of bone is used instead."""
        cand = (need - sd) * u
        q = p + cand
        sdq, _u = self._signed(self.bone, q[None], 0.04)
        if sdq[0] >= need - 0.2 * MM:
            return cand
        if Probe._DIRS is None:
            d = np.array([(i, j, k) for i in (-1, 0, 1) for j in (-1, 0, 1) for k in (-1, 0, 1)
                          if (i, j, k) != (0, 0, 0)], float)
            Probe._DIRS = d / np.linalg.norm(d, axis=1, keepdims=True)
        best = None
        for step in (0.5, 1.0, 2.0, 3.0, 4.5, 6.0, 8.0, 11.0):
            Q = p[None] + Probe._DIRS * (step * MM + max(0.0, need - max(sd, 0.0)))
            sdQ, _ = self._signed(self.bone, Q, 0.04)
            ok = np.where(sdQ >= need)[0]
            if len(ok):
                best = Q[ok[np.argmax(sdQ[ok])]] - p
                break
        return cand if best is None else best

    def brain_dist(self, P):
        return self._signed(self.brain, P, 0.05)

    def skull_inner(self, P):
        """For each point, the first skeleton hit on the ray HEAD_CENTRE -> point (inner table), or None."""
        from mathutils import Vector
        out = []
        for p in np.asarray(P, float):
            d = p - HEAD_CENTRE
            n = np.linalg.norm(d)
            if self.bone is None or n < 1e-6:
                out.append(None)
                continue
            d = d / n
            loc, _nrm, _i, _dist = self.bone.ray_cast(Vector(HEAD_CENTRE), Vector(d), 0.2)
            out.append(None if loc is None else (np.array(loc), d))
        return out


# ===========================================================================
# Fit (plan §3.4.1 step 4)
# ===========================================================================
def _gauss_smooth(D, s, sigma, anchor=None):
    """Smooth per-point vectors D[M,3] along arc length s with a Gaussian (sigma metres)."""
    if len(D) < 3 or sigma <= 0:
        return D
    w = np.exp(-0.5 * ((s[:, None] - s[None, :]) / sigma) ** 2)
    w /= w.sum(axis=1, keepdims=True)
    out = w @ D
    if anchor is not None:
        out *= anchor[:, None]
    return out


def _zone_mask(sel, P, s):
    kind = sel[0]
    if kind == "z":
        return (P[:, 2] >= sel[1]) & (P[:, 2] <= sel[2])
    if kind == "t":
        t = s / max(s[-1], 1e-9)
        return (t >= sel[1] - 1e-9) & (t <= sel[2] + 1e-9)
    if kind == "end":
        return s >= s[-1] - sel[1]
    raise ValueError(sel)


def depth_bands(seg, P, r, s):
    """Per-point (lo, hi) skin-depth band in metres and a label list, for a segment at points P."""
    vid = seg["vessel"]
    lo = np.maximum(r + SKIN_FLOOR_MM * MM, 0.0)
    hi = np.full(len(P), np.inf)
    dm = seg.get("depth_mm")
    if dm:
        lo = np.maximum(lo, 0.5 * dm[0] * MM)
        key = f"{vid}_{seg.get('branch')}" if seg.get("branch") else vid
        if key in SUPERFICIAL_T or vid in SUPERFICIAL_T:
            t = s / max(s[-1], 1e-9)
            t0, t1 = SUPERFICIAL_T.get(key, SUPERFICIAL_T.get(vid))
            m = (t >= t0) & (t <= t1)
            lo_b = np.maximum(dm[0] * MM, r + SKIN_FLOOR_MM * MM)
            hi_b = np.maximum(dm[1] * MM, lo_b + 1.0 * MM)
            lo = np.where(m, lo_b, lo)
            hi = np.where(m, hi_b, hi)
    for sel, zlo, zhi, _label in ZONES.get(vid, ()):
        m = _zone_mask(sel, P, s)
        lo = np.where(m, np.maximum(zlo * MM, r + SKIN_FLOOR_MM * MM), lo)
        hi = np.where(m, zhi * MM, hi)
    return lo, hi


def _bone_mask(vid, P):
    if vid in BONE_CANAL:
        z0, z1 = BONE_CANAL[vid]
        return ~((P[:, 2] >= z0) & (P[:, 2] <= z1))
    return np.ones(len(P), bool)


def fit_centreline(key, vid, P0, r, probe, anchor_disp=None, seg=None, cranial=False, under_skull=False,
                   bone_contact=False, iters=FIT_ITERS, root=False, on_heart=False):
    """Fit one centreline to the scene; returns (P, report dict).

    ``anchor_disp``: displacement of the parent at this segment's origin (the branch follows it and the
    origin is pinned to it)."""
    P = np.array(P0, float)
    P0_start = P.copy()                              # untouched stretches keep the exact waypoint curve
    s = _arc(P)
    L = s[-1]
    # a branch starts on its parent: carry the parent's displacement, fading over 30 mm
    if anchor_disp is not None:
        P += anchor_disp[None, :] * np.exp(-s / 0.030)[:, None]
    # the origin stays on its parent; a root may slide a little on its heart chamber
    if on_heart:
        anchor = np.clip(s / 0.020, 0.0, 1.0)          # coronary origins stay on the aortic sinuses
    else:
        anchor = np.clip(s / 0.012, 0.1 if anchor_disp is not None else (0.35 if root else 0.0), 1.0)
    sigma = float(np.clip(1.5 * np.mean(r), 0.005, 0.015))
    bone_mask = _bone_mask(vid, P)
    clear = (0.0 if bone_contact else BONE_CLEAR_MM * MM)
    if on_heart:
        hits = probe.epicardium(P, HEART_CENTRE)
        tgt = P.copy()
        for i, h in enumerate(hits):
            if h is not None:
                loc, d = h
                tgt[i] = loc + d * (0.5 * r[i])          # half sunk into the epicardial fat of its groove
        tgt = _gauss_smooth(tgt, s, 0.006)
        P = P + (tgt - P) * anchor[:, None]
        P0_start = P.copy()                           # fairing below acts only where bone then moves it
    if under_skull:
        hits = probe.skull_inner(P)
        tgt = P.copy()
        for i, h in enumerate(hits):
            if h is not None and np.linalg.norm(h[0] - P[i]) < 0.015:
                loc, d = h
                tgt[i] = loc - d * (r[i] * 0.85 + 0.6 * MM)
        # the modelled inner table is bumpy: snap, then fair the sinus along its course (sigma 12 mm)
        tgt = _gauss_smooth(tgt, s, 0.012)
        P = P + (tgt - P) * anchor[:, None]
    def relax(P, n_iter):
        for _it in range(n_iter):
            corr = np.zeros_like(P)
            hard = np.zeros(len(P), bool)                 # points a hard rule (bone, brain) is moving
            sd, bn = probe.brain_dist(P)                  # nothing may run inside the brain
            need = r + BRAIN_CLEAR_MM * MM
            bad = (sd < need) & (not under_skull)
            corr[bad] += bn[bad] * (need[bad] - sd[bad])[:, None]
            hard |= bad
            sd, bn = probe.bone_dist(P)
            need = r + clear
            bad = (sd < need) & bone_mask
            for i in np.where(bad)[0]:
                corr[i] += probe.bone_escape(P[i], sd[i], bn[i], need[i])
            hard |= bad
            if seg is not None:
                # skin bands are soft: where bone/brain push, a depth band may not push back into them
                lo, hi = depth_bands(seg, P, r, _arc(P))
                depth, nout = probe.skin_depth(P, parity=True)
                shallow = (depth < lo) & ~(hard & (depth > r + SKIN_FLOOR_MM * MM))
                deep = (depth > hi) & ~hard
                corr[shallow] -= nout[shallow] * (lo[shallow] - depth[shallow])[:, None]
                corr[deep] += nout[deep] * (depth[deep] - hi[deep])[:, None]
            if not np.any(np.linalg.norm(corr, axis=1) > 2e-5):
                break
            # over-relax a little (the Gaussian spreads an isolated correction over its neighbours), but
            # never move more than MAX_STEP per iteration so conflicting rules cannot throw a vessel
            # through a bone
            step = 1.4 * _gauss_smooth(corr, _arc(P), sigma, anchor)
            n = np.linalg.norm(step, axis=1, keepdims=True)
            P = P + step * np.minimum(1.0, MAX_STEP / np.maximum(n, 1e-12))
        return P
    P = relax(P, iters)
    # fairing: remove the jitter the rules leave (surface tessellation, rib edges), ends fixed, then re-relax
    sa = _arc(P)
    ends = np.clip(np.minimum(sa, sa[-1] - sa) / 0.010, 0.0, 1.0)
    moved = np.linalg.norm(P - P0_start, axis=1)
    w = _gauss_smooth(np.clip(moved / (2.0 * MM), 0.0, 1.0)[:, None].repeat(3, 1), sa, 0.010)[:, 0]
    P = P + (_gauss_smooth(P, sa, FAIR_SIGMA) - P) * (ends * np.clip(w, 0.0, 1.0))[:, None]
    P = relax(P, iters // 2)
    rep = measure(key, vid, P, r, probe, seg=seg, cranial=cranial or under_skull, bone_mask=bone_mask,
                  clear=clear)
    rep["moved_mm_max"] = round(float(np.linalg.norm(P - P0, axis=1).max() / MM), 2)
    rep["length_m"] = round(float(L), 4)
    return P, rep


def measure(key, vid, P, r, probe, seg=None, cranial=False, bone_mask=None, clear=0.0):
    """Depth / bone / band report of a fitted centreline."""
    depth, _n = probe.skin_depth(P, parity=True)
    sd, _bn = probe.bone_dist(P)
    bone_mask = _bone_mask(vid, P) if bone_mask is None else bone_mask
    in_bone = int(np.sum((sd < r) & bone_mask))               # tube wall intersecting bone
    rep = {"id": key, "depth_mm": [round(float(depth.min() / MM), 1), round(float(np.median(depth) / MM), 1),
                                   round(float(depth.max() / MM), 1)],
           "outside_skin_pts": int(np.sum(depth < r)), "bone_hits": in_bone}
    if seg is not None and not cranial:
        lo, hi = depth_bands(seg, P, r, _arc(P))
        tol = 0.5 * MM
        rep["band_viol"] = int(np.sum((depth < lo - tol) | (depth > hi + tol)))
    else:
        rep["band_viol"] = 0
    if cranial:
        bd, _ = probe.brain_dist(P)
        rep["in_brain_pts"] = int(np.sum(bd < 0.0))
    return rep


def polyline_distance(P, q):
    """Distance from point q to the polyline P (segments, not just vertices)."""
    P = np.asarray(P, float)
    q = np.asarray(q, float)
    if len(P) == 1:
        return float(np.linalg.norm(P[0] - q))
    a, b = P[:-1], P[1:]
    ab = b - a
    t = np.clip(((q - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-18), 0.0, 1.0)
    return float(np.min(np.linalg.norm(a + t[:, None] * ab - q, axis=1)))


def _nearest_on_polyline(P, q):
    """Closest point to q on the polyline P."""
    a, b = P[:-1], P[1:]
    ab = b - a
    t = np.clip(((q - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-18), 0.0, 1.0)
    c = a + t[:, None] * ab
    return c[int(np.argmin(np.linalg.norm(c - q, axis=1)))]


def _origin_disp(parent_raw, parent_fit, parent_r, p):
    """Displacement for a branch origin ``p``: the same place along the parent (arc parameter of the nearest
    raw parent point, so branch spacing along e.g. the aortic arch is kept) plus the raw offset from the
    parent centreline, clamped inside the parent tube (0.8 r) so the branch stays attached."""
    a, b = parent_raw[:-1], parent_raw[1:]
    ab = b - a
    t = np.clip(((p - a) * ab).sum(1) / np.maximum((ab * ab).sum(1), 1e-18), 0.0, 1.0)
    c = a + t[:, None] * ab
    k = int(np.argmin(np.linalg.norm(c - p, axis=1)))
    base_raw = c[k]
    base_fit = parent_fit[k] + (parent_fit[k + 1] - parent_fit[k]) * t[k]
    rp = parent_r[k] + (parent_r[k + 1] - parent_r[k]) * t[k]
    off = p - base_raw
    n = np.linalg.norm(off)
    if n > 0.8 * rp:
        off *= 0.8 * rp / n
    return base_fit + off - p


def _nearest_disp(parent_P0, parent_P, p):
    i = int(np.argmin(np.linalg.norm(parent_P0 - p, axis=1)))
    return parent_P[i] - parent_P0[i]


def fit_network(probe=None, log=True):
    """Fit every segment and nerve (parents first).  Returns {"segments": {id: (P, r, rep)},
    "nerves": {id: (P, r, rep)}, "sources": ...}."""
    probe = probe or Probe()
    segs = VS.vessel_segments()
    by_id = {s["id"]: s for s in segs}
    order, seen = [], set()

    def visit(s):
        if s["id"] in seen:
            return
        par = by_id.get(s["parent"])
        if par is not None:
            visit(par)
        seen.add(s["id"])
        order.append(s)
    for s in segs:
        visit(s)
    raw, fitted = {}, {}
    t0 = time.perf_counter()
    for s in order:
        P0, r, _t = centreline(s)
        raw[s["id"]] = P0
        disp = None
        par = by_id.get(s["parent"])
        if par is not None and par["id"] in fitted:
            disp = _origin_disp(raw[par["id"]], fitted[par["id"]][0], fitted[par["id"]][1], P0[0])
        vid = s["vessel"]
        P, rep = fit_centreline(s["id"], vid, P0, r, probe, anchor_disp=disp, seg=s,
                                cranial=vid in CRANIAL, under_skull=vid in UNDER_SKULL,
                                bone_contact=vid in BONE_CONTACT_OK, root=s["root"], on_heart=vid in ON_HEART)
        fitted[s["id"]] = (P, r, rep)
    # reconnect: a branch whose origin ended outside its parent's tube (rules pulled them apart) is bent
    # back onto the parent over its first 10 mm
    for sg in order:
        par = by_id.get(sg["parent"])
        if par is None or par["id"] not in fitted:
            continue
        P, r, rep = fitted[sg["id"]]
        Pp, rp, _ = fitted[par["id"]]
        q = _nearest_on_polyline(Pp, P[0])
        k = int(np.argmin(np.linalg.norm(Pp - q, axis=1)))
        gap = np.linalg.norm(P[0] - q)
        if gap > 0.8 * rp[k]:
            tgt = q + (P[0] - q) * (0.8 * rp[k] / gap)
            P = P + (tgt - P[0])[None, :] * np.exp(-_arc(P) / 0.010)[:, None]
            rep = dict(measure(sg["id"], sg["vessel"], P, r, probe, seg=sg,
                               cranial=sg["vessel"] in CRANIAL or sg["vessel"] in UNDER_SKULL),
                       moved_mm_max=rep["moved_mm_max"], length_m=rep["length_m"], reconnected_mm=round(gap / MM, 1))
            fitted[sg["id"]] = (P, r, rep)
    nerves = {}
    for nv in nerve_rows():
        P0, r, _t = nerve_centreline(nv)
        pseudo = {"vessel": nv["nerve"], "depth_mm": None}
        P, rep = fit_centreline(nv["id"], nv["nerve"], P0, r, probe, seg=pseudo,
                                bone_contact=nv["nerve"] in BONE_CONTACT_OK)
        nerves[nv["id"]] = (P, r, rep)
    if log:
        gbc.log(f"B5 vascular: fitted {len(fitted)} segments + {len(nerves)} nerves in "
                f"{time.perf_counter() - t0:.1f} s against {probe.sources}")
    return {"segments": fitted, "nerves": nerves, "sources": probe.sources}


# ===========================================================================
# Tubes
# ===========================================================================
def _stations(P, r, tol_frac=0.5, tol_min=0.0020, max_step=RING_MAX_STEP):
    """Indices of the ring stations: Douglas-Peucker on the dense centreline plus a maximum spacing."""
    keep = {0, len(P) - 1}

    def dp(i, j):
        if j <= i + 1:
            return
        a, b = P[i], P[j]
        ab = b - a
        L = np.linalg.norm(ab)
        seg = P[i + 1:j]
        if L < 1e-9:
            d = np.linalg.norm(seg - a, axis=1)
        else:
            d = np.linalg.norm(np.cross(seg - a, ab / L), axis=1)
        k = int(np.argmax(d))
        tol = max(tol_frac * float(r[i + 1 + k]), tol_min)
        if d[k] > tol:
            keep.add(i + 1 + k)
            dp(i, i + 1 + k)
            dp(i + 1 + k, j)
    dp(0, len(P) - 1)
    idx = sorted(keep)
    s = _arc(P)
    out = [idx[0]]
    for a, b in zip(idx[:-1], idx[1:]):
        n = int(math.ceil((s[b] - s[a]) / max_step))
        if n > 1:
            for k in range(1, n):
                target = s[a] + (s[b] - s[a]) * k / n
                out.append(int(np.argmin(np.abs(s - target))))
        out.append(b)
    return sorted(set(out))


def _frames(P, pref=None):
    """Parallel-transport frames; ``pref`` (optional [M,3]) = preferred N axis per station."""
    T = np.gradient(P, axis=0) if len(P) > 2 else np.repeat((P[1] - P[0])[None], len(P), axis=0)
    T /= np.maximum(np.linalg.norm(T, axis=1, keepdims=True), 1e-12)
    N = np.zeros_like(P)
    up = np.array([0.0, 0.0, 1.0]) if abs(T[0][2]) < 0.9 else np.array([1.0, 0.0, 0.0])
    n0 = up - (up @ T[0]) * T[0]
    N[0] = n0 / np.linalg.norm(n0)
    for i in range(1, len(P)):
        n = N[i - 1] - (N[i - 1] @ T[i]) * T[i]
        ln = np.linalg.norm(n)
        N[i] = n / ln if ln > 1e-9 else N[i - 1]
    if pref is not None:
        q = pref - (pref * T).sum(1, keepdims=True) * T
        ok = np.linalg.norm(q, axis=1) > 1e-6
        q[ok] /= np.linalg.norm(q[ok], axis=1, keepdims=True)
        N[ok] = q[ok]
    B = np.cross(T, N)
    return T, N, B


def tube(P, r, t, sides, section="round", pref=None):
    """Tube mesh arrays (verts[V,3], faces, t per vertex) through stations P with radii r.

    section: 'round', 'vein' (flattened VEIN_FLATTEN along N = ``pref``), 'tri' (rounded triangle whose
    flat side faces N = ``pref``)."""
    T, N, B = _frames(P, pref)
    phi = np.linspace(0.0, 2.0 * np.pi, sides, endpoint=False)
    if section == "tri":
        rad = 1.0 + 0.25 * np.cos(3.0 * (phi - np.pi))
        cn, cb = np.cos(phi) * rad, np.sin(phi) * rad
    elif section == "vein":
        cn, cb = np.cos(phi) * VEIN_FLATTEN, np.sin(phi) / math.sqrt(VEIN_FLATTEN)
    else:
        cn, cb = np.cos(phi), np.sin(phi)
    ring = (cn[None, :, None] * N[:, None, :] + cb[None, :, None] * B[:, None, :]) * r[:, None, None]
    V = (P[:, None, :] + ring).reshape(-1, 3)
    tv = np.repeat(t, sides)
    M = len(P)
    faces = []
    for i in range(M - 1):
        a0, b0 = i * sides, (i + 1) * sides
        for k in range(sides):
            k1 = (k + 1) % sides
            faces.append((a0 + k, a0 + k1, b0 + k1, b0 + k))
    c0 = len(V)
    V = np.vstack([V, P[0], P[-1]])
    tv = np.concatenate([tv, [t[0], t[-1]]])
    last = (M - 1) * sides
    for k in range(sides):
        k1 = (k + 1) % sides
        faces.append((c0, k1, k))
        faces.append((c0 + 1, last + k, last + k1))
    return V, faces, tv


def _tube_parts(fit, probe=None):
    """Join-parts lists for GB_Vessels_Art / _Ven from the fitted centrelines."""
    import gb_geom as gg
    parts = {"GB_Vessels_Art": [], "GB_Vessels_Ven": []}
    for s in VS.vessel_segments():
        mesh = mesh_for(s)
        if mesh is None or s["id"] not in fit:
            continue
        P, r, _rep = fit[s["id"]]
        sa = _arc(P)
        t = sa / max(sa[-1], 1e-9)
        idx = _stations(P, r, tol_min=0.0008) if s["vessel"] in TORTUOUS else _stations(P, r)
        Ps, rs, ts = P[idx], r[idx], t[idx]
        section, pref = "round", None
        if s["vessel"] in TRI_SECTION or s["kind"] == "V":
            section = "tri" if s["vessel"] in TRI_SECTION else "vein"
            if probe is not None:
                if s["vessel"] in TRI_SECTION:
                    pref = Ps - HEAD_CENTRE                     # flat side toward the skull
                else:
                    _d, pref = probe.skin_depth(Ps, parity=False)
        v, f, tv = tube(Ps, rs, ts, sides_for(s), section, pref)
        parts[mesh].append(gg.part(v, f, 0, gb_vidx=np.full(len(v), float(s["vessel_index"])), gb_tt=tv))
    return parts


# ===========================================================================
# Data curves (GB_Data)
# ===========================================================================
def _curve(name, pts, radius, props=None):
    import bpy
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (float(p[0]), float(p[1]), float(p[2]), 1.0)
        sp.points[i].radius = float(radius[i])
    obj = gbc.new_object(name, cu, "GB_Data")
    for k, v in (props or {}).items():
        obj[k] = v
    return obj


def _read_curve(name):
    """(P[M,3], r[M], props) of a fitted GBV_/GBN_ curve in the scene, or None."""
    try:
        import bpy
    except ImportError:
        return None
    obj = bpy.data.objects.get(name)
    if obj is None or obj.type != 'CURVE' or obj.get("gb_fit") != "B5":
        return None
    sp = obj.data.splines[0]
    P = np.array([tuple(p.co)[:3] for p in sp.points], float)
    r = np.array([p.radius for p in sp.points], float)
    props = {k: obj[k] for k in obj.keys() if k.startswith("gb_")}
    return P, r, props


def _rep_props(rep):
    return {"gb_fit": "B5", "gb_depth_mm": list(rep["depth_mm"]), "gb_moved_mm": rep.get("moved_mm_max", 0.0),
            "gb_bone_hits": rep["bone_hits"], "gb_band_viol": rep["band_viol"],
            "gb_outside_skin_pts": rep["outside_skin_pts"]}


# ===========================================================================
# Build
# ===========================================================================
_LAST_NET = {}


def build_vessels(fit=True):
    """Build GB_Vessels_Art/_Ven tubes and the fitted GBV_/GBN_ data curves (B5)."""
    import bpy
    import gb_geom as gg
    import placeholder as PH
    t0 = time.perf_counter()
    probe = Probe()
    if fit:
        net = fit_network(probe)
    else:
        net = {"segments": {}, "nerves": {}}
        for s in VS.vessel_segments():
            P, r, _t = centreline(s)
            net["segments"][s["id"]] = (P, r, measure(s["id"], s["vessel"], P, r, probe, seg=s))
        for nv in nerve_rows():
            P, r, _t = nerve_centreline(nv)
            net["nerves"][nv["id"]] = (P, r, measure(nv["id"], nv["nerve"], P, r, probe))
    _LAST_NET["net"] = net
    out = {}
    with gbc.Timer("B5 vascular: tubes"):
        parts = _tube_parts(net["segments"], probe)
        for name, pl in parts.items():
            obj = gg.object_from_parts(name, pl)
            gbc.set_codes_uv(obj, gbc.read_point_attr(obj, "gb_vidx"), gbc.read_point_attr(obj, "gb_tt"))
            gg.smart_uv(obj, margin=0.003)
            PH.finish_uvs(obj)
            obj.data.shade_smooth()
            obj["gb_layer"] = gbc.LAYER_OF[name]
            obj["gb_schema"] = 1
            obj["gb_status"] = "B5"
            out[name] = obj
    with gbc.Timer("B5 vascular: data curves"):
        keep = set()
        for sid, (P, r, rep) in net["segments"].items():
            nm = "GBV_" + sid
            out[nm] = _curve(nm, P, r, _rep_props(rep))
            keep.add(nm)
        for nid, (P, r, rep) in net["nerves"].items():
            nm = "GBN_" + nid
            out[nm] = _curve(nm, P, r, _rep_props(rep))
            keep.add(nm)
        for o in list(bpy.data.objects):                      # stale placeholder curves of renamed segments
            if o.name.startswith(("GBV_", "GBN_")) and o.name not in keep:
                gbc.remove_object(o.name)
    tris = {n: gbc.tri_count(out[n].data) for n in ("GB_Vessels_Art", "GB_Vessels_Ven")}
    gbc.log(f"B5 vascular: {len(net['segments'])} segments, {len(net['nerves'])} nerves, tubes {tris} "
            f"(total {sum(tris.values())}), {time.perf_counter() - t0:.1f} s")
    return out


# ===========================================================================
# vessels.json
# ===========================================================================
def _fitted_or_raw(seg):
    got = _read_curve("GBV_" + seg["id"])
    if got is not None:
        return got[0], got[1], got[2]
    P, r, _t = centreline(seg)
    return P, r, {}


def vessel_table():
    """vessels.json 'data' (plan §5.8): fitted centrelines when the B5 stage is in the scene."""
    import rig
    segs = VS.vessel_segments()
    out = []
    n_fit = 0
    for s in segs:
        P, r, props = _fitted_or_raw(s)
        n_fit += bool(props)
        sa = _arc(P)
        t = sa / max(sa[-1], 1e-9)
        idx, w = rig.weights_at(P)
        dom = idx[np.arange(len(idx)), np.argmax(w, axis=1)]
        rec = {k: s[k] for k in ("id", "vessel", "branch", "name", "side", "kind", "circuit", "d_mm", "d_end_mm",
                                 "d_range_mm", "rest_flow_ml_min", "parent", "extra_parents", "children", "root",
                                 "depth_mm", "compressible", "self_stop", "stump_frac", "collaterals",
                                 "outlet_default", "in_bone_canal", "air_entry", "pulse_delay_ms", "landmarks",
                                 "bleed_ref", "fit_points", "tag", "note", "source")}
        rec["waypoints"] = [list(p) for p in s["points"]]
        rec["points"] = np.column_stack([P, r]).tolist()
        rec["t"] = t.tolist()
        rec["length_m"] = float(sa[-1])
        rec["bones"] = [RT.BONE_NAMES[i] for i in dom]
        rec["mesh"] = mesh_for(s)
        rec["blood"] = blood_of(s)
        rec["vessel_index"] = s["vessel_index"]
        rec["tube_sides"] = sides_for(s)
        rec["depth_measured_mm"] = list(props.get("gb_depth_mm", [])) or None
        rec["fit_moved_mm"] = props.get("gb_moved_mm")
        out.append(rec)
    nerves = []
    for nv in nerve_rows():
        got = _read_curve("GBN_" + nv["id"])
        if got is not None:
            P, r = got[0], got[1]
        else:
            P, r, _t = nerve_centreline(nv)
        idx, w = rig.weights_at(P)
        dom = idx[np.arange(len(idx)), np.argmax(w, axis=1)]
        nerves.append({"id": nv["id"], "nerve": nv["nerve"], "side": nv["side"], "roots": nv["roots"],
                       "radius": nv["radius"], "points": [list(p) for p in P],
                       "bones": [RT.BONE_NAMES[i] for i in dom], "deficit": nv["deficit"],
                       "note": nv["note"], "tag": NV.TAG, "fitted": got is not None,
                       "depth_measured_mm": list(got[2].get("gb_depth_mm", [])) if got else None})
    status = ("B5: centrelines fitted to the built skin, skeleton and brain (vascular.fit_network)"
              if n_fit == len(segs) else f"B5 table; {n_fit}/{len(segs)} fitted (unfitted = raw waypoint "
                                         "centrelines: run the vascular stage)")
    return {"segments": out, "beds": VS.BEDS, "nerves": nerves, "collaterals": VS.COLLATERALS,
            "pulse": VS.PULSE, "colours": VS.COLOURS, "both_ends_bleed": list(VS.SCALP_FACE_BOTH_ENDS),
            "roots": [s["id"] for s in segs if s["root"]],
            "counts": {"segments": len(segs), "named_vessels": len(VS.vessel_ids()),
                       "tubes": sum(1 for s in segs if mesh_for(s)), "nerves": len(nerves)},
            "status": status}


# ===========================================================================
# Checks (called by verify.py and the standalone run)
# ===========================================================================
def graph_report(table=None):
    """Loader-style graph check of a vessels.json 'data' block: (ok, detail)."""
    d = table or vessel_table()
    segs = d["segments"]
    by = {s["id"]: s for s in segs}
    probs = []
    for s in segs:
        if not s["root"] and s["parent"] not in by:
            probs.append(f"{s['id']}: parent {s['parent']} missing")
        for c in s["children"]:
            if c not in by or by[c]["parent"] != s["id"]:
                probs.append(f"{s['id']}: child {c} inconsistent")
        pts = np.asarray(s["points"], float)
        if pts.ndim != 2 or pts.shape[1] != 4 or len(pts) < 2 or np.any(pts[:, 3] <= 0):
            probs.append(f"{s['id']}: points not [x,y,z,r]")
        if len(s["bones"]) != len(pts) or len(s["t"]) != len(pts):
            probs.append(f"{s['id']}: bones/t length")
        if s["bones"] and any(b not in RT.BONE_NAMES for b in s["bones"]):
            probs.append(f"{s['id']}: unknown bone")

    def root_of(s):
        k = 0
        while not s["root"] and k < 64:
            s = by[s["parent"]]
            k += 1
        return s["parent"]
    roots = {}
    for s in segs:
        if s["parent"] in by or s["root"]:
            roots.setdefault((s["circuit"], root_of(s)), 0)
            roots[(s["circuit"], root_of(s))] += 1
    want = {"systemic_art": "LV", "pulmonary_art": "RV", "systemic_ven": "RA", "portal": "RA",
            "pulmonary_ven": "LA"}
    for (circ, rt), n in roots.items():
        if want.get(circ) != rt:
            probs.append(f"{n} {circ} segments end at {rt}")
    art_roots = sorted({s["id"] for s in segs if s["root"] and s["kind"] != "V"})
    if art_roots != ["A01", "P01"]:
        probs.append(f"arterial roots {art_roots} (want A01, P01)")
    lr = [s["id"] for s in segs if s["side"] == "L" and s["id"].endswith("_L")
          and s["id"][:-2] + "_R" not in by]
    if lr:
        probs.append(f"left without right: {lr[:6]}")
    return not probs, (f"{len(segs)} segments; circuits->roots {sorted((k[0], k[1], v) for k, v in roots.items())}; "
                       f"problems {probs[:8]}")


def waypoint_report(tol_mm=2.0, tol_e_mm=20.0, probe=None):
    """Distance of every RB §3.3 waypoint to its vessel's fitted centreline, with the reason when it moved.

    A waypoint may leave its bible position only when the raw (unfitted) centreline breaks a hard rule
    within 25 mm of it (tube wall in bone / outside the skin / out of its depth band / inside the brain),
    when its segment starts on a parent that moved, or when it is listed in ``WAYPOINT_DEVIATIONS``.
    Strict rows must be within ``tol_mm`` otherwise; (E) rows (the bible's own ±10-20 mm fits) within
    ``tol_e_mm``.  Returns (ok, detail, rows[(vid, point, dist_mm, is_E, ok, cause)])."""
    bw = bible_waypoints()
    if bw is None:
        return True, "bible not found (skipped)", []
    probe = probe or Probe()
    segs = VS.vessel_segments()
    by_id = {s["id"]: s for s in segs}
    cl = {}
    for s in segs:
        P, r, _p = _fitted_or_raw(s)
        P0, r0, _t = centreline(s)
        cl.setdefault(s["vessel"], []).append((s, P, P0, r0))
    viol_cache = {}

    def raw_violations(s, P0, r0):
        if s["id"] not in viol_cache:
            depth, _ = probe.skin_depth(P0)
            lo, hi = depth_bands(s, P0, r0, _arc(P0))
            sd, _ = probe.bone_dist(P0)
            bd, _ = probe.brain_dist(P0)
            v = np.zeros(len(P0), dtype=object)
            v[:] = ""
            cran = s["vessel"] in CRANIAL or s["vessel"] in UNDER_SKULL
            if not cran:
                v[(depth < lo - 0.5 * MM) | (depth > hi + 0.5 * MM)] = "depth"
            v[(sd < r0) & _bone_mask(s["vessel"], P0)] = "bone"
            v[bd < r0] = "brain"
            if s["vessel"] in UNDER_SKULL:
                v[:] = "under-skull snap"
            if s["vessel"] in ON_HEART:
                v[:] = "epicardium snap"
            viol_cache[s["id"]] = v
        return viol_cache[s["id"]]
    rows, bad = [], []
    for vid, info in sorted(bw.items()):
        if vid not in cl:
            continue
        for p in info["points"]:
            p = np.asarray(p)
            best = min(cl[vid], key=lambda it: polyline_distance(it[1], p))
            s, P, P0, r0 = best
            d = polyline_distance(P, p) / MM
            tol = tol_e_mm if info["E"] else tol_mm
            cause = ""
            if d > tol:
                s0 = _arc(P0)
                i = int(np.argmin(np.linalg.norm(P0 - p, axis=1)))
                near = np.abs(s0 - s0[i]) <= 0.025
                v = raw_violations(s, P0, r0)
                causes = sorted({c for c in v[near] if c})
                par = by_id.get(s["parent"])
                if causes:
                    cause = "raw " + "/".join(causes)
                elif par is not None and s0[i] <= 0.030:
                    cause = f"origin follows parent {par['id']}"
                elif vid in WAYPOINT_DEVIATIONS:
                    cause = WAYPOINT_DEVIATIONS[vid]
            ok = d <= tol or bool(cause)
            rows.append((vid, tuple(float(c) for c in p), round(d, 1), info["E"], ok, cause))
            if not ok:
                bad.append(f"{vid}{'(E)' if info['E'] else ''} {tuple(round(c, 3) for c in p)} {d:.1f} mm")
    strict = [r for r in rows if not r[3]]
    n_in = sum(1 for r in strict if r[2] <= tol_mm)
    forced = sorted({r[0] for r in rows if r[5]})
    detail = (f"{len(rows)} bible waypoints; strict {n_in}/{len(strict)} within {tol_mm} mm, the rest moved by a "
              f"rule ({forced}); (E) within {tol_e_mm} mm unless moved by a rule; unexplained {bad[:10]}")
    return not bad, detail, rows


# RB §3.3 waypoints the network deliberately leaves although the raw centreline breaks no rule there
# (anatomy of the built meshes wins; see gb_data/vessels.py notes and the B5 report).
WAYPOINT_DEVIATIONS = {
    "A10": "end re-routed around the modelled medulla to the basilar origin",
    "A11": "basilar on the modelled pons front instead of the clivus line",
    "A32": "E waypoints in the tibia / 25 mm in front of the built shin, re-fitted to the membrane",
}


def fb5_report():
    """FB-5 depths measured on the built skin: [(test, measured [min, max] mm, band, ok)] and overall ok."""
    probe = Probe()
    tests = [("CCA at C4-C6", "A04", ("z", _C6Z, _C4Z), (20, 30)),
             ("IJV at C4-C6", "V01", ("z", _C6Z, _C4Z), (20, 30)),
             ("femoral artery at the groin", "A28", ("t", 0.0, 1.0), (15, 30)),
             ("radial artery at the wrist", "A42", ("end", 0.030), (2, 5)),
             ("brachial mid-arm", "A41", ("t", 0.30, 0.70), (10, 20))]
    rows = []
    for label, vid, sel, (lo, hi) in tests:
        for side in ("L", "R"):
            sid = f"{vid}_{side}"
            seg = next((s for s in VS.vessel_segments() if s["id"] == sid), None)
            if seg is None:
                continue
            P, _r, _p = _fitted_or_raw(seg)
            m = _zone_mask(sel, P, _arc(P))
            if not np.any(m):
                rows.append((f"{label} {side}", None, (lo, hi), False))
                continue
            d, _n = probe.skin_depth(P[m])
            mn, mx = float(d.min() / MM), float(d.max() / MM)
            rows.append((f"{label} {side}", (round(mn, 1), round(mx, 1)), (lo, hi), lo <= mn and mx <= hi))
    return all(r[3] for r in rows), rows


def bone_report():
    """Arterial/venous tubes intersecting GB_Skeleton outside bone canals: (ok, detail)."""
    probe = Probe()
    hits = []
    for s in VS.vessel_segments():
        if mesh_for(s) is None:
            continue
        P, r, _p = _fitted_or_raw(s)
        sd, _n = probe.bone_dist(P)
        m = (sd < r - 0.5 * MM) & _bone_mask(s["vessel"], P)          # 0.5 mm: mesh-level tolerance
        if s["vessel"] in BONE_CONTACT_OK:
            m = (sd < 0.0) & _bone_mask(s["vessel"], P)
        if np.any(m):
            k = int(np.argmin(np.where(m, sd - r, 9.0)))
            hits.append(f"{s['id']}({int(m.sum())} pts, wall {float((sd[k] - r[k]) / MM):.1f} mm at "
                        f"{tuple(round(float(c), 3) for c in P[k])})")
    art = [h for h in hits if h.startswith(("A", "P"))]
    return not art, f"tubes into bone outside canals: arteries {art[:12]}; veins {[h for h in hits if h not in art][:12]}"


def tube_vertices_in_bone(tol=0.5 * MM):
    """Fraction of GB_Vessels_Art vertices more than ``tol`` inside GB_Skeleton, outside bone canals and
    bone-contact vessels (mesh-level check of the tubes, not only the centrelines)."""
    import bpy
    o = bpy.data.objects.get("GB_Vessels_Art")
    if o is None:
        return 1.0
    probe = Probe()
    v = gbc.get_verts(o.data)
    vidx = np.round(gbc.read_point_attr(o, "gb_vidx")).astype(int)
    segs = VS.vessel_segments()
    vess = np.array([segs[i]["vessel"] for i in vidx])
    keep = np.ones(len(v), bool)
    for vid in set(vess):
        m = vess == vid
        if vid in BONE_CONTACT_OK:
            keep &= ~m
        elif vid in BONE_CANAL:
            z0, z1 = BONE_CANAL[vid]
            keep &= ~(m & (v[:, 2] >= z0 - 0.004) & (v[:, 2] <= z1 + 0.004))
    sd, _n = probe.bone_dist(v[keep])
    return float(np.mean(sd < -tol)) if keep.any() else 0.0


def skin_report():
    """Every tube inside the skin (centreline deeper than its radius): (ok, detail)."""
    probe = Probe()
    bad = []
    for s in VS.vessel_segments():
        if mesh_for(s) is None:
            continue
        P, r, _p = _fitted_or_raw(s)
        d, _n = probe.skin_depth(P)
        m = d < r + 0.3 * MM
        if np.any(m):
            bad.append(f"{s['id']}({int(m.sum())}, {float((d[m] - r[m]).min() / MM):.1f} mm)")
    return not bad, f"tube walls within 0.3 mm of / outside the skin: {bad[:12]}"


# ===========================================================================
# X-ray renders
# ===========================================================================
def _xray_material(name, rgb, strength, alpha):
    """Emission + transparency (reads like an angiogram over a ghosted body)."""
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (*rgb, 1.0)
    em.inputs["Strength"].default_value = strength
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    lw = nt.nodes.new("ShaderNodeLayerWeight")
    lw.inputs["Blend"].default_value = 0.35
    if alpha is None:                                     # facing-ratio ghost (edges glow, centre clear)
        nt.links.new(lw.outputs["Facing"], mix.inputs["Fac"])
    else:
        mix.inputs["Fac"].default_value = alpha
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(em.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    return mat


def _solid_material(name, rgb, rough=0.35, emit=0.0):
    import bpy
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
    b.inputs["Base Color"].default_value = (*rgb, 1.0)
    b.inputs["Roughness"].default_value = rough
    b.inputs["Coat Weight"].default_value = 0.4
    if emit > 0:
        b.inputs["Emission Color"].default_value = (*rgb, 1.0)
        b.inputs["Emission Strength"].default_value = emit
    return mat


XRAY_VIEWS = {
    "front": ((0.0, -3.3, 0.93), (0.0, 0.0, 0.91), 50.0, (480, 640)),
    "side": ((-3.3, 0.02, 0.93), (0.0, 0.02, 0.91), 50.0, (480, 640)),
    "three_q": ((-2.1, -2.5, 1.15), (0.0, 0.0, 0.91), 50.0, (480, 640)),
    "head_neck": ((-0.55, -0.62, 1.64), (0.0, 0.01, 1.58), 70.0, (560, 560)),
    "head_side": ((-0.85, 0.02, 1.64), (0.0, 0.02, 1.62), 85.0, (560, 560)),
    "thorax_abdomen": ((0.0, -1.55, 1.22), (0.0, 0.0, 1.20), 50.0, (560, 640)),
    "arm": ((0.55, -1.0, 1.12), (0.30, 0.0, 1.13), 55.0, (560, 560)),
    "leg": ((0.62, -1.35, 0.52), (0.09, 0.0, 0.50), 50.0, (480, 640)),
    "pelvis": ((0.0, -1.1, 0.98), (0.03, 0.0, 0.98), 55.0, (560, 560)),
    "heart": ((0.30, -0.80, 1.45), (0.02, -0.03, 1.36), 60.0, (560, 560)),
    "head_top": ((0.35, -0.25, 2.25), (0.0, 0.02, 1.66), 60.0, (560, 560)),
}


def render_xray(prefix="vascular", views=tuple(XRAY_VIEWS), samples=32, anatomical=False):
    """X-ray style renders: ghost skin, faint bones, arteries red, veins blue.  ``anatomical``: opaque
    vessels with the skin hidden (a dissection look) instead of the angiogram look."""
    import bpy
    gbc.collections()
    scene = bpy.context.scene
    world = bpy.data.worlds.get("GB_XRayWorld") or bpy.data.worlds.new("GB_XRayWorld")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    bg.inputs[0].default_value = (0.004, 0.005, 0.008, 1.0) if not anatomical else (0.02, 0.022, 0.026, 1.0)
    scene.view_settings.view_transform = 'AgX'
    mats = {
        "skin": _xray_material("XR_skin", (0.30, 0.45, 0.62), 0.35, None),
        "bone": _xray_material("XR_bone", (0.80, 0.80, 0.76), 0.35, 0.10),
        "organ": _xray_material("XR_organ", (0.7, 0.40, 0.36), 0.3, 0.06),
        "brain": _xray_material("XR_brain", (0.8, 0.7, 0.7), 0.3, 0.06),
        "art": (_solid_material("XR_art", (0.80, 0.03, 0.04), 0.3, 1.2 if not anatomical else 0.0)),
        "ven": (_solid_material("XR_ven", (0.08, 0.20, 0.85), 0.3, 1.2 if not anatomical else 0.0)),
    }
    show = {"GB_Body": "skin", "GB_Head": "skin", "GB_Skeleton": "bone", "GB_Organs": "organ",
            "GB_Brain": "brain", "GB_Vessels_Art": "art", "GB_Vessels_Ven": "ven"}
    if anatomical:
        show.pop("GB_Body")
        show.pop("GB_Head")
    saved = {}
    for o in scene.objects:
        saved[o.name] = (o.hide_render, [s.material for s in o.material_slots] if o.type == 'MESH' else None)
        o.hide_render = o.name not in show and o.type != 'CAMERA'
        if o.type == 'LIGHT':
            o.hide_render = not anatomical
    for n, key in show.items():
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        for s in o.material_slots:
            s.link = 'OBJECT'
            s.material = mats[key]
    if anatomical:
        gbc.setup_stage(floor=False)
        for n in ("GB_Key", "GB_Fill", "GB_Rim"):
            if n in bpy.data.objects:
                bpy.data.objects[n].hide_render = False
    paths = []
    try:
        for v in views:
            loc, tgt, lens, res = XRAY_VIEWS[v]
            cam = gbc.add_camera(f"XR_Cam_{v}", loc, tgt, lens)
            scene.cycles.transparent_max_bounces = 24
            paths.append(gbc.render(os.path.join(gbc.RENDER_DIR, f"{prefix}_{v}.png"), cam, samples, res))
    finally:
        for o in scene.objects:
            if o.name in saved:
                o.hide_render = saved[o.name][0]
        for n in show:
            o = bpy.data.objects.get(n)
            if o is not None:
                for s in o.material_slots:
                    s.link = 'DATA'
    return paths


# ===========================================================================
# Cross-section panels (numeric check made visible: skin, muscle shell, bone, vessels in one plane)
# ===========================================================================
SECTIONS = [
    # (label, plane axis, plane value, window centre (u, v), window size m); axis 2 = horizontal slice
    ("neck C5", 2, VT.VERTEBRA["C5"]["z"], (0.0, 0.0), 0.16),
    ("root of neck", 2, 1.45, (0.0, -0.01), 0.24),
    ("upper thorax T5", 2, 1.39, (0.0, 0.0), 0.36),
    ("abdomen L2", 2, 1.16, (0.0, -0.01), 0.36),
    ("groin", 2, 0.93, (0.06, -0.02), 0.22),
    ("mid thigh", 2, 0.72, (0.10, 0.0), 0.20),
    ("calf", 2, 0.30, (0.10, 0.03), 0.16),
    ("ankle", 2, 0.085, (0.10, 0.04), 0.14),
    ("mid upper arm", "arm", 0.46, None, 0.14),
    ("forearm", "arm", 0.80, None, 0.12),
    ("wrist", "arm", 0.975, None, 0.10),
    ("head, sagittal x = 3 mm", 0, 0.003, (0.02, 1.64), 0.26),
]
_ARM_S0 = np.array([0.18, 0.02, 1.415])                       # glenohumeral centre (left)
_ARM_S1 = np.array([0.46, 0.02, 0.93])                        # wrist centre (A-pose)


def _plane(axis, val):
    """(origin, normal, u axis, v axis) of a section plane."""
    if axis == "arm":
        d = _ARM_S1 - _ARM_S0
        o = _ARM_S0 + d * val
        n = d / np.linalg.norm(d)
        u = np.cross(n, [0.0, 1.0, 0.0])
        u /= np.linalg.norm(u)
        return o, n, u, np.cross(n, u)
    n = np.eye(3)[axis]
    u = np.eye(3)[(axis + 1) % 3] if axis != 2 else np.array([1.0, 0.0, 0.0])
    v = np.cross(n, u)
    if axis == 2:                                      # radiological axial view: anterior up, left on the right
        v = np.array([0.0, -1.0, 0.0])
    if axis == 0:                                      # sagittal, face to the left
        u, v = np.array([0.0, 1.0, 0.0]), np.array([0.0, 0.0, 1.0])
    o = n * val
    return o, n, u, v


def _mesh_section(obj, o, n):
    """Line segments (K, 2, 3) where the mesh cuts the plane."""
    v, t = gbc.mesh_arrays(obj.data)
    s = (v - o) @ n
    st = s[t]
    cut = (st.min(1) < 0) & (st.max(1) > 0)
    segs = []
    for tri, ss in zip(t[cut], st[cut]):
        pts = []
        for a, b in ((0, 1), (1, 2), (2, 0)):
            if (ss[a] < 0) != (ss[b] < 0):
                k = ss[a] / (ss[a] - ss[b])
                pts.append(v[tri[a]] + (v[tri[b]] - v[tri[a]]) * k)
        if len(pts) == 2:
            segs.append(pts)
    return np.array(segs).reshape(-1, 2, 3)


def render_sections(path=None, px=300, raw=True):
    """Write ``renders/vascular_sections.png``: one panel per ``SECTIONS`` row.

    grey = skin, dark red = muscle shell, white = bone, filled red/blue circles = fitted arteries/veins at
    their true radius, green dots = the raw waypoint centreline (before the fit), yellow = nerves."""
    import bpy
    path = path or os.path.join(gbc.RENDER_DIR, "vascular_sections.png")
    cols = 4
    rows = int(math.ceil(len(SECTIONS) / cols))
    img = np.zeros((rows * px, cols * px, 3), np.uint8)
    layers = [("GB_Body", (150, 150, 150)), ("GB_Head", (150, 150, 150)), ("GB_MuscleShell", (110, 40, 40)),
              ("GB_Skeleton", (235, 235, 225))]
    segs = VS.vessel_segments()
    for k, (label, axis, val, centre, size) in enumerate(SECTIONS):
        o, n, u, v = _plane(axis, val)
        if centre is not None:
            c2 = np.array(centre, float)
            if axis == 2:
                c2[1] = -c2[1]                            # centres are given as body (x, y)
        else:
            c2 = np.array([o @ u, o @ v])
        panel = np.zeros((px, px, 3), np.uint8) + np.array([12, 14, 20], np.uint8)
        scale = px / size

        def to_px(P):
            uv = np.stack([(P @ u) - c2[0], (P @ v) - c2[1]], axis=-1)
            return np.stack([px / 2 + uv[..., 0] * scale, px / 2 - uv[..., 1] * scale], axis=-1)

        def dot(x, y, rad, col):
            x0, x1 = int(max(0, x - rad - 1)), int(min(px, x + rad + 2))
            y0, y1 = int(max(0, y - rad - 1)), int(min(px, y + rad + 2))
            if x0 >= x1 or y0 >= y1:
                return
            yy, xx = np.mgrid[y0:y1, x0:x1]
            m = (xx - x) ** 2 + (yy - y) ** 2 <= rad * rad
            panel[y0:y1, x0:x1][m] = col
        for name, col in layers:
            obj = bpy.data.objects.get(name)
            if obj is None:
                continue
            for a, b in to_px(_mesh_section(obj, o, n)):
                m = int(max(2, np.linalg.norm(b - a)))
                for q in np.linspace(a, b, m):
                    if 0 <= q[0] < px and 0 <= q[1] < px:
                        panel[int(q[1]), int(q[0])] = col

        def crossings(P):
            s = (P - o) @ n
            out = []
            for i in range(len(P) - 1):
                if (s[i] < 0) != (s[i + 1] < 0):
                    f = s[i] / (s[i] - s[i + 1])
                    out.append((i, f, P[i] + (P[i + 1] - P[i]) * f))
            return out
        for sg in segs:
            P, r, _p = _fitted_or_raw(sg)
            col = (70, 110, 255) if blood_of(sg) == "deoxygenated" else (235, 40, 40)
            for i, f, q in crossings(P):
                rr = r[i] + (r[min(i + 1, len(r) - 1)] - r[i]) * f
                x, y = to_px(q)
                dot(x, y, max(1.5, rr * scale), col)
            if raw:
                P0, _r0, _t0 = centreline(sg)
                for _i, _f, q in crossings(P0):
                    x, y = to_px(q)
                    dot(x, y, 1.5, (60, 230, 60))
        for nv in nerve_rows():
            got = _read_curve("GBN_" + nv["id"])
            P = got[0] if got else nerve_centreline(nv)[0]
            for _i, _f, q in crossings(P):
                x, y = to_px(q)
                dot(x, y, max(1.5, nv["radius"] * scale), (240, 220, 60))
        panel[:, :1] = panel[:, -1:] = panel[:1] = panel[-1:] = 60
        # scale bar: 1 cm
        panel[px - 8:px - 6, 8:8 + int(0.01 * scale)] = 255
        rr_, cc_ = divmod(k, cols)
        img[rr_ * px:(rr_ + 1) * px, cc_ * px:(cc_ + 1) * px] = panel
    gbc.write_png_u8(path, img)
    return path


# ===========================================================================
# Standalone
# ===========================================================================
def load_stage_caches(stages=("skin", "head", "skeleton", "viscera", "neuro")):
    """Append the newest cached objects of each stage (standalone runs; build.py does this itself)."""
    import bpy
    loaded = {}
    for st in stages:
        files = glob.glob(os.path.join(gbc.CACHE_DIR, f"{st}-*.blend"))
        if not files:
            continue
        path = max(files, key=os.path.getmtime)
        with bpy.data.libraries.load(path, link=False) as (src, _dst):
            names = list(src.objects)
        for n in names:
            gbc.remove_object(n)
        with bpy.data.libraries.load(path, link=False) as (_src, dst):
            dst.objects = names
        for obj in dst.objects:
            if obj is None:
                continue
            obj.use_fake_user = False
            gbc.link(obj, gbc.OBJECT_COLLECTION.get(obj.name, "GB_Data"))
            loaded[obj.name] = st
    return loaded


def print_report(net=None):
    """Human-readable fit report."""
    ok, rows = fb5_report()
    print("FB-5 depths (centreline to nearest skin):")
    for label, meas, band, good in rows:
        print(f"   {'ok ' if good else 'BAD'} {label:32s} {meas} mm   band {band}")
    for fn in (graph_report, bone_report, skin_report):
        good, det = fn()
        print(f"{'ok ' if good else 'BAD'} {fn.__name__}: {det}")
    good, det, rows = waypoint_report()
    print(f"{'ok ' if good else 'BAD'} waypoint_report: {det}")
    far = sorted([r for r in rows if r[2] > 2.0], key=lambda r: -r[2])[:40]
    for vid, p, d, e, okk, cause in far:
        print(f"      {vid}{'(E)' if e else '   '} {tuple(round(c, 3) for c in p)}  {d} mm {cause} "
              f"{'' if okk else '<< UNEXPLAINED'}")
    if net is not None:
        mv = sorted(net["segments"].items(), key=lambda kv: -kv[1][2]["moved_mm_max"])[:30]
        print("largest fit moves: " + ", ".join(f"{k} {v[2]['moved_mm_max']}" for k, v in mv))
        viol = [(k, v[2]) for k, v in net["segments"].items() if v[2]["band_viol"] or v[2]["bone_hits"]
                or v[2]["outside_skin_pts"] or v[2].get("in_brain_pts")]
        print(f"segments with residual violations: {len(viol)}")
        for k, rep in viol[:40]:
            print(f"      {k}: {rep}")


if __name__ == "__main__":
    args = gbc.script_args()
    t_start = time.perf_counter()
    gbc.reset_scene()
    gbc.collections()
    got = load_stage_caches()
    gbc.log(f"loaded {len(got)} cached objects")
    objs = build_vessels(fit="--no-fit" not in args)
    print_report(_LAST_NET.get("net"))
    render_sections()
    if "--views" in args:
        render_xray("vascular", views=tuple(args[args.index("--views") + 1].split(",")),
                    anatomical="--anat" in args)
    elif "--render" in args:
        render_xray("vascular", views=("front", "side", "three_q", "head_neck", "head_side", "thorax_abdomen",
                                       "arm", "leg", "pelvis"))
        render_xray("vascular_anat", views=("front", "head_neck", "heart", "thorax_abdomen"), anatomical=True)
    gbc.log(f"vascular standalone {time.perf_counter() - t_start:.1f} s")
