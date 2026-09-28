"""Weapons, examine tools and the forensic test room (owner B8).  Plan §1.3, §5.2, §5.7, §8.2 B8.

Everything is modelled from code (numpy + bmesh + Blender modifiers); no downloaded asset of any kind.

Entry points
------------
``build_weapons() -> {name: root empty}``
    pistol (9 mm), shotgun (12 ga pump), single-edged knife, claw hammer, propane torch (+ flame),
    gloved fist, ABFO-style L ruler, penlight, probe thermometer.  One root empty per item
    (``GBP_Pistol`` ...) at the origin; the item's grip / hand point is the root origin.
``build_room() -> {name: object}``
    6 x 6 x 3 m tiled forensic room (plan §1.3): epoxy floor with a 1 % fall to a Ø 150 mm drain,
    coved skirting, 150 mm glazed wall tiles with real 2 mm grout joints, ceiling with two LED panels,
    rubber-granulate bullet backstop, steel door, stainless mortuary table, instrument trolley,
    yellow tape floor mark, 1 m wall scale bar, light / probe / spawn markers and collision shapes.
``export_props(out) -> {path: ...}``
    ``weapons.glb``, ``room.glb``, ``props.json`` (measured critical dimensions, markers) and
    ``room.json`` (the room constants ``world/room.gd`` must equal).
``measure_props() -> dict``
    Critical dimensions measured on the built meshes (verify.py compares them to ``SPEC``).

Frames and marker convention
----------------------------
Blender body frame (metres, +Z up).  The glTF exporter converts to Godot ``(x, z, -y)``, so an item
authored pointing **+Y** points **-Z** in Godot (Node3D forward).  Every weapon is authored pointing
+Y (muzzle / blade / face / nozzle / knuckles), up +Z.  Every marker empty (``GBP_*``) has local **+Y =
its action direction** (bullet path, blade-edge outward normal, striking direction, flame axis, beam)
and local **+Z = up / reference**; in Godot that is ``-basis.z`` = action direction.  Marker kind is
stored in the custom property ``gbp_marker`` (exported as node extras).

Plan §5.7 lists ``GBP_muzzle``; two firearms share one file and Blender names are unique, so the
muzzles are ``GBP_muzzle_pistol`` and ``GBP_muzzle_shotgun`` (both with ``gbp_marker = "muzzle"``).

Run alone:  ``python3 props.py [--quick] [--render] [--render-items a,b] [--render-room all|v1,v2] [--no-export]``
"""
import math
import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402

import bmesh  # noqa: E402
import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

MM = 0.001
ROOT_COL = "GoreProps"
COL_WEAPONS = "GBP_Weapons"
COL_ROOM = "GBP_Room"
COL_STAGE = "GBP_Stage"
WEAPONS_GLB = "weapons.glb"
ROOM_GLB = "room.glb"
PROPS_JSON = "props.json"
ROOM_JSON = "room.json"

gbc.SCHEMAS.setdefault("gb.props/1", ("items", "markers", "materials", "conventions"))
gbc.SCHEMAS.setdefault("gb.room/1", ("godot", "body", "markers", "materials", "collision", "floor_height"))

# ---------------------------------------------------------------------------
# Specification: critical dimensions (mm unless stated).  verify.py checks the built meshes
# against these within +-1 mm (bores +-0.05 mm).  Sources: plan §8.2 B8, RB §2.3, §2.5, §2.6.
# ---------------------------------------------------------------------------
SPEC = {
    "pistol": {"bore_d": 9.0, "overall_length": 196.5, "height": 139.0, "slide_width": 25.4,
               "grip_width": 30.0, "barrel_length": 114.0},
    "shotgun": {"bore_d": 18.5, "barrel_length": 470.0, "overall_length": 987.0, "barrel_od_muzzle": 21.6},
    "knife": {"blade_length": 120.0, "blade_width": 25.0, "spine_thickness": 2.5, "overall_length": 236.0},
    "hammer": {"face_d": 28.0, "overall_length": 325.0, "head_length": 133.0,
               "head_mass_kg": (0.45, 0.70)},
    "torch": {"cylinder_d": 77.3, "tube_d": 16.0, "flame_length": 80.0, "overall_length": 440.0},
    "fist": {"knuckle_width": (80.0, 95.0)},
    "ruler": {"arm_length": 130.0, "arm_width": 25.0, "cm_tick_pitch": 10.0, "scale_length": 100.0},
    "penlight": {"diameter": 14.4, "length": 141.1},
    "thermometer": {"probe_d": 3.5, "probe_length": 123.0},
}

# Room constants (Godot frame in plan §1.3; converted to the Blender body frame with g2b).
ROOM = {
    "x": (-3.0, 3.0), "z": (-1.6, 4.4), "height": 3.0,           # Godot interior bounds (m)
    "floor_fall": 0.01, "drain_g": (0.0, 0.0, 1.0), "drain_d": 0.150,
    "tile": 0.150, "grout": 0.002, "tile_relief": 0.0015,
    "cove_r": 0.040, "cove_top": 0.140,
    "backstop_size": (2.4, 2.2, 0.3), "backstop_front_z": -1.3,
    "panel_size": (1.2, 0.6), "panel_z": (0.2, 2.4),
    "key_light_g": (0.0, 2.65, 1.7), "key_target_g": (0.0, 1.25, 0.0),
    "player_spawn_g": (0.0, 0.0, 3.0), "player_eye": (1.65, 0.9),
    "table_g": (2.4, 1.2), "table_size": (0.8, 2.0), "table_top": 0.86,
    "trolley_g": (-2.3, 2.3), "trolley_size": (0.6, 0.45), "trolley_top": 0.86,
    "scale_bar_g": (-3.0, 1.45, 0.0), "door_g": (-1.9, 0.0, 4.4), "door_size": (0.9, 2.1),
}

# ---------------------------------------------------------------------------
# Materials: named Principled placeholders with exact factors (exported by glTF; Godot's props
# import may replace them by name).  Procedural bump nodes are Blender-render only (the exporter
# drops them; base colour / metallic / roughness / emission factors are what the game receives).
# ---------------------------------------------------------------------------
MATS = {
    # name: (hex, metallic, roughness, extras)
    "GBPM_polymer": ("#1B1C1E", 0.0, 0.55, {"bump": (900.0, 0.15)}),
    "GBPM_polymer_grip": ("#1A1B1D", 0.0, 0.68, {"bump": (2600.0, 0.22)}),
    "GBPM_steel_nitride": ("#2B2C2F", 1.0, 0.40, {"bump": (1500.0, 0.05)}),
    "GBPM_steel_bore": ("#4C4944", 1.0, 0.30, {}),
    "GBPM_steel_barrel": ("#56585C", 1.0, 0.33, {"bump": (1500.0, 0.03)}),
    "GBPM_sight_white": ("#E9E6DA", 0.0, 0.45, {}),
    "GBPM_steel_blued": ("#23262B", 1.0, 0.32, {"bump": (1200.0, 0.04)}),
    "GBPM_alu_black": ("#1D1E21", 1.0, 0.45, {"bump": (1600.0, 0.06)}),
    "GBPM_walnut": ("#3A2315", 0.0, 0.42, {"bump": (220.0, 0.12)}),
    "GBPM_rubber_pad": ("#141414", 0.0, 0.85, {"bump": (1800.0, 0.3)}),
    "GBPM_brass": ("#B18E57", 1.0, 0.30, {}),
    "GBPM_steel_satin": ("#AEB2B6", 1.0, 0.26, {"bump": (2200.0, 0.03)}),
    "GBPM_steel_edge": ("#D4D7DA", 1.0, 0.14, {}),
    "GBPM_steel_ground": ("#C3C7CB", 1.0, 0.19, {"bump": (3000.0, 0.02)}),
    "GBPM_g10_black": ("#1A1B1C", 0.0, 0.62, {"bump": (1400.0, 0.35)}),
    "GBPM_steel_forged": ("#34373C", 1.0, 0.48, {"bump": (500.0, 0.10)}),
    "GBPM_steel_polished": ("#C6C9CC", 1.0, 0.16, {}),
    "GBPM_hickory": ("#A06A36", 0.0, 0.46, {"bump": (160.0, 0.10)}),
    "GBPM_paint_blue": ("#123A7A", 0.0, 0.34, {}),
    "GBPM_label": ("#E8E4D6", 0.0, 0.55, {}),
    "GBPM_print_red": ("#B3161B", 0.0, 0.5, {}),
    "GBPM_steel_stainless": ("#A9ADB1", 1.0, 0.30, {"bump": (1800.0, 0.03)}),
    "GBPM_plastic_black": ("#141517", 0.0, 0.50, {}),
    "GBPM_flame_core": ("#9CC3FF", 0.0, 0.5, {"emission": ("#8DB8FF", 18.0), "alpha": 0.85}),
    "GBPM_flame_outer": ("#4659FF", 0.0, 0.5, {"emission": ("#3E55FF", 4.0), "alpha": 0.22}),
    "GBPM_glove": ("#151516", 0.0, 0.58, {"bump": (900.0, 0.35)}),
    "GBPM_glove_pad": ("#232426", 0.0, 0.72, {"bump": (1500.0, 0.45)}),
    "GBPM_ruler_white": ("#ECEBE6", 0.0, 0.60, {}),
    "GBPM_print_black": ("#0C0C0C", 0.0, 0.55, {}),
    "GBPM_glass": ("#F4F7F8", 0.0, 0.03, {"alpha": 0.25, "transmission": 1.0}),
    "GBPM_led": ("#FFF3D2", 0.0, 0.3, {}),
    "GBPM_chrome": ("#DADCDE", 1.0, 0.06, {}),
    "GBPM_abs_grey": ("#C9CBC7", 0.0, 0.42, {"bump": (1300.0, 0.08)}),
    "GBPM_lcd": ("#27332A", 0.0, 0.08, {}),
    "GBPM_rubber_grey": ("#55585A", 0.0, 0.80, {}),
    # room (plan §1.3 colours / roughness; absorbent flags for the blood system)
    "GBPM_room_epoxy": ("#8E9194", 0.0, 0.55, {"bump": (900.0, 0.25), "absorbent": False}),
    "GBPM_room_tile": ("#E8E6E1", 0.0, 0.15, {"absorbent": False}),
    "GBPM_room_grout": ("#9C9A94", 0.0, 0.80, {"bump": (2500.0, 0.4), "absorbent": True}),
    "GBPM_room_rubber": ("#1F1F1F", 0.0, 0.92, {"bump": (520.0, 0.9), "absorbent": True}),
    "GBPM_room_ceiling": ("#DCDCD8", 0.0, 0.80, {}),
    "GBPM_room_led": ("#FFFFFF", 0.0, 0.40, {"emission": ("#FFE4CE", 6.0)}),
    "GBPM_room_stainless": ("#B8BBBD", 1.0, 0.30, {"bump": (2000.0, 0.03), "absorbent": False}),
    "GBPM_room_galv": ("#7C8084", 1.0, 0.50, {"bump": (180.0, 0.08)}),
    "GBPM_room_door": ("#C9CCCB", 0.0, 0.38, {}),
    "GBPM_room_tape": ("#D8B31E", 0.0, 0.45, {}),
    "GBPM_room_dark": ("#0D0D0E", 0.0, 0.90, {}),
    "GBPM_room_alu": ("#C4C6C8", 1.0, 0.35, {}),
    "GBPM_room_caster": ("#202124", 0.0, 0.70, {}),
}


def hex_lin(h):
    """sRGB hex -> linear RGBA."""
    return gbc.hex_to_linear(h)


def material(name):
    """Create (once) the named prop material from ``MATS``."""
    mat = bpy.data.materials.get(name)
    if mat is not None:
        return mat
    hexc, metal, rough, ex = MATS[name]
    mat = bpy.data.materials.new(name)
    if not mat.node_tree:
        mat.use_nodes = True
    nt = mat.node_tree
    bsdf = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    col = hex_lin(hexc)
    bsdf.inputs["Base Color"].default_value = col
    bsdf.inputs["Metallic"].default_value = metal
    bsdf.inputs["Roughness"].default_value = rough
    mat.diffuse_color = col
    mat.metallic = metal
    mat.roughness = rough
    if "emission" in ex:
        ehex, strength = ex["emission"]
        bsdf.inputs["Emission Color"].default_value = hex_lin(ehex)
        bsdf.inputs["Emission Strength"].default_value = strength
    if "alpha" in ex:
        bsdf.inputs["Alpha"].default_value = ex["alpha"]
        try:
            mat.surface_render_method = 'BLENDED'
        except (AttributeError, TypeError):
            pass
    if "transmission" in ex:
        bsdf.inputs["Transmission Weight"].default_value = ex["transmission"]
    if "bump" in ex:                                # Blender-only micro detail (not exported)
        scale, strength = ex["bump"]
        tex = nt.nodes.new("ShaderNodeTexNoise")
        tex.inputs["Scale"].default_value = scale
        tex.inputs["Detail"].default_value = 6.0
        coord = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord.outputs["Object"], tex.inputs["Vector"])
        bump = nt.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = strength
        bump.inputs["Distance"].default_value = 0.0004
        nt.links.new(tex.outputs["Fac"], bump.inputs["Height"])
        nt.links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    mat["gbp_absorbent"] = bool(ex.get("absorbent", False))
    return mat


# ---------------------------------------------------------------------------
# Collections
# ---------------------------------------------------------------------------
def prop_collections():
    """Create (or return) ``GoreProps`` with ``GBP_Weapons``, ``GBP_Room``, ``GBP_Stage``."""
    scene_col = bpy.context.scene.collection
    root = bpy.data.collections.get(ROOT_COL) or bpy.data.collections.new(ROOT_COL)
    if root.name not in scene_col.children:
        scene_col.children.link(root)
    out = {ROOT_COL: root}
    for n in (COL_WEAPONS, COL_ROOM, COL_STAGE):
        c = bpy.data.collections.get(n) or bpy.data.collections.new(n)
        if c.name not in root.children:
            root.children.link(c)
        out[n] = c
    return out


# ---------------------------------------------------------------------------
# 2D / 3D primitive generators (return numpy verts + face lists; units as given)
# ---------------------------------------------------------------------------
def signed_area(P):
    P = np.asarray(P, float)
    return 0.5 * float(np.sum(P[:, 0] * np.roll(P[:, 1], -1) - np.roll(P[:, 0], -1) * P[:, 1]))


AXES = {"yz": (1, 2, 0), "xz": (0, 2, 1), "xy": (0, 1, 2)}


def _uvw(u, v, w, axes):
    iu, iv, iw = AXES[axes]
    out = np.zeros((len(u), 3))
    out[:, iu], out[:, iv], out[:, iw] = u, v, w
    return out


def prism(poly, w0, w1, axes="yz"):
    """Extrude a 2D polygon (in the plane ``axes``) between ``w0`` and ``w1`` along the third axis."""
    P = np.asarray(poly, float)
    if signed_area(P) < 0:
        P = P[::-1]
    K = len(P)
    V = np.vstack([_uvw(P[:, 0], P[:, 1], np.full(K, w0), axes), _uvw(P[:, 0], P[:, 1], np.full(K, w1), axes)])
    F = [list(range(K))[::-1], list(range(K, 2 * K))]
    F += [[i, (i + 1) % K, K + (i + 1) % K, K + i] for i in range(K)]
    return V, F


def box(c, size):
    """Axis-aligned box centred at ``c`` with full ``size``."""
    c = np.asarray(c, float)
    h = np.asarray(size, float) / 2
    poly = [(c[0] - h[0], c[1] - h[1]), (c[0] + h[0], c[1] - h[1]), (c[0] + h[0], c[1] + h[1]),
            (c[0] - h[0], c[1] + h[1])]
    return prism(poly, c[2] - h[2], c[2] + h[2], "xy")


def box_mm(lo, hi):
    """Box from its min and max corners."""
    lo, hi = np.asarray(lo, float), np.asarray(hi, float)
    return box((lo + hi) / 2, hi - lo)


def rrect(hw, hh, r=(1.0, 1.0, 1.0, 1.0), seg=4, cx=0.0, cy=0.0):
    """Rounded rectangle, CCW, corner radii (bottom-left, bottom-right, top-right, top-left)."""
    if np.isscalar(r):
        r = (r, r, r, r)
    pts = []
    corners = [(-hw, -hh, 180.0), (hw, -hh, 270.0), (hw, hh, 0.0), (-hw, hh, 90.0)]
    for (x, y, a0), rad in zip(corners, r):
        rad = min(rad, hw * 0.999, hh * 0.999)
        ccx = x - np.sign(x) * rad
        ccy = y - np.sign(y) * rad
        if rad <= 1e-9:
            pts.append((x, y))
            continue
        for k in range(seg + 1):
            a = math.radians(a0 + 90.0 * k / seg)
            pts.append((ccx + rad * math.cos(a), ccy + rad * math.sin(a)))
    P = np.array(pts) + (cx, cy)
    keep = np.concatenate([[True], np.linalg.norm(np.diff(P, axis=0), axis=1) > 1e-9])
    return P[keep]


def superellipse(a, b, n=2.5, K=32, cx=0.0, cy=0.0, t0=0.0, t1=2 * math.pi, endpoint=False):
    """Superellipse points ``|x/a|^n + |y/b|^n = 1`` (CCW)."""
    t = np.linspace(t0, t1, K, endpoint=endpoint)
    c, s = np.cos(t), np.sin(t)
    x = a * np.sign(c) * np.abs(c) ** (2.0 / n)
    y = b * np.sign(s) * np.abs(s) ** (2.0 / n)
    return np.stack([x + cx, y + cy], axis=1)


def lathe(profile, seg=32, axis="y", centre=(0.0, 0.0, 0.0), loop=False, phase=0.0):
    """Surface of revolution of ``profile`` [(a, r), ...] around ``axis`` through ``centre``.

    Points with r == 0 become poles.  ``loop`` connects the last profile point to the first (tube
    walls, rings).  Ends with r > 0 and no loop are closed by n-gon caps."""
    prof = np.asarray(profile, float)
    ia = "xyz".index(axis)
    iu, iv = [i for i in range(3) if i != ia]
    if axis == "y":
        iu, iv = 2, 0            # right-handed (z, x, y)
    phi = np.linspace(0.0, 2 * math.pi, seg, endpoint=False) + phase
    verts, rings = [], []
    for a, r in prof:
        if r <= 1e-9:
            p = np.zeros(3)
            p[ia] = a
            rings.append([len(verts)])
            verts.append(p)
        else:
            idx = []
            for f in phi:
                p = np.zeros(3)
                p[ia], p[iu], p[iv] = a, r * math.cos(f), r * math.sin(f)
                idx.append(len(verts))
                verts.append(p)
            rings.append(idx)
    faces = []
    n = len(rings)
    pairs = [(i, i + 1) for i in range(n - 1)] + ([(n - 1, 0)] if loop else [])
    for i, j in pairs:
        A, B = rings[i], rings[j]
        if len(A) == 1 and len(B) == 1:
            continue
        if len(A) == 1:
            faces += [[A[0], B[(k + 1) % seg], B[k]] for k in range(seg)]
        elif len(B) == 1:
            faces += [[A[k], A[(k + 1) % seg], B[0]] for k in range(seg)]
        else:
            faces += [[A[k], A[(k + 1) % seg], B[(k + 1) % seg], B[k]] for k in range(seg)]
    if not loop:
        if len(rings[0]) > 1:
            faces.append(list(rings[0]))
        if len(rings[-1]) > 1:
            faces.append(list(rings[-1])[::-1])
    V = np.asarray(verts) + np.asarray(centre, float)
    return V, faces


def loft(sections, caps=True, closed=True):
    """Skin a list of equal-length 3D point rings (K, 3).  ``closed``: rings are closed loops."""
    S = [np.asarray(s, float) for s in sections]
    K = len(S[0])
    V = np.vstack(S)
    F = []
    m = K if closed else K - 1
    for i in range(len(S) - 1):
        a, b = i * K, (i + 1) * K
        F += [[a + k, a + (k + 1) % K, b + (k + 1) % K, b + k] for k in range(m)]
    if caps and closed:
        F.append(list(range(K))[::-1])
        F.append(list(range((len(S) - 1) * K, len(S) * K)))
    return V, F


def section_at(P2, origin, U, V):
    """Place 2D section points (u, v) in 3D: origin + u*U + v*V."""
    P2 = np.asarray(P2, float)
    return np.asarray(origin, float) + P2[:, :1] * np.asarray(U, float) + P2[:, 1:2] * np.asarray(V, float)


def path_frames(P, up=(0.0, 0.0, 1.0)):
    """Tangent / side / up frames along a 3D polyline (up projected, side = T x up)."""
    P = np.asarray(P, float)
    T = np.gradient(P, axis=0)
    T /= np.linalg.norm(T, axis=1, keepdims=True)
    upv = np.asarray(up, float)
    S = np.cross(T, upv)
    S /= np.linalg.norm(S, axis=1, keepdims=True)
    Uv = np.cross(S, T)
    return T, S, Uv


def merge(*parts):
    """Concatenate (V, F) parts into one (V, F)."""
    Vs, Fs, off = [], [], 0
    for V, F in parts:
        Vs.append(np.asarray(V, float))
        Fs += [[int(i) + off for i in f] for f in F]
        off += len(V)
    return np.vstack(Vs), Fs


def xform(part, R=None, t=(0.0, 0.0, 0.0)):
    """Rotate (3x3 matrix) then translate a (V, F) part."""
    V, F = part
    V = np.asarray(V, float)
    if R is not None:
        V = V @ np.asarray(R, float).T
    return V + np.asarray(t, float), F


def rot(axis, deg):
    """3x3 rotation matrix about 'x' | 'y' | 'z'."""
    return np.array(Matrix.Rotation(math.radians(deg), 3, axis.upper()))


# ---------------------------------------------------------------------------
# Object kit: objects of one item share a root empty and a millimetre frame with an origin shift
# ---------------------------------------------------------------------------
class Kit:
    """Builds the objects of one prop.  Geometry is authored in ``unit`` (mm by default) in the item's
    own frame; ``origin`` (same unit) becomes the root origin, so vertices are stored as
    ``(p - origin) * unit`` metres under an identity-transform root empty."""

    def __init__(self, root_name, col, origin=(0.0, 0.0, 0.0), unit=MM, kind="weapon"):
        self.col = col
        self.unit = unit
        self.origin = np.asarray(origin, float)
        remove_tree(root_name)
        self.root = bpy.data.objects.new(root_name, None)
        self.root.empty_display_type = 'PLAIN_AXES'
        self.root.empty_display_size = 0.05
        self.root["gbp_kind"] = kind
        col.objects.link(self.root)
        self.objects = {}
        self.markers = {}

    def to_m(self, V):
        return (np.asarray(V, float) - self.origin) * self.unit

    def obj(self, name, part, mats, face_mat=None, smooth=True, recalc=True, temp=False):
        """Create a mesh object from a (V, F) part in item units."""
        V, F = part
        me = bpy.data.meshes.new(name)
        me.from_pydata(self.to_m(V).tolist(), [], [list(map(int, f)) for f in F])
        me.validate(clean_customdata=False)
        me.update()
        ob = bpy.data.objects.new(name, me)
        self.col.objects.link(ob)
        if temp:
            return ob
        ob.parent = self.root
        if isinstance(mats, str):
            mats = [mats]
        for m in mats or []:
            me.materials.append(material(m))
        if face_mat is not None and len(me.polygons):
            me.polygons.foreach_set("material_index", np.asarray(face_mat, np.int32))
        if recalc:
            bm = bmesh.new()
            bm.from_mesh(me)
            bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            bm.to_mesh(me)
            bm.free()
        if smooth:
            me.shade_smooth()
        self.objects[name] = ob
        return ob

    def boolean(self, ob, part, op='DIFFERENCE'):
        """Apply an EXACT boolean with a temporary cutter built from ``part``."""
        cut = self.obj("_gbp_cutter", part, None, temp=True)
        bm = bmesh.new()                                   # cutters must be closed and outward-facing
        bm.from_mesh(cut.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        bm.to_mesh(cut.data)
        bm.free()
        m = ob.modifiers.new("gbp_bool", 'BOOLEAN')
        m.operation = op
        m.object = cut
        m.solver = 'EXACT'
        _apply(ob, m)
        me = cut.data
        bpy.data.objects.remove(cut, do_unlink=True)
        bpy.data.meshes.remove(me)
        return ob

    def bevel(self, ob, width, segments=2, angle=30.0, profile=0.5):
        """Rounded edges via the Bevel modifier (applied), limited by angle."""
        m = ob.modifiers.new("gbp_bevel", 'BEVEL')
        m.width = width * self.unit
        m.segments = segments
        m.limit_method = 'ANGLE'
        m.angle_limit = math.radians(angle)
        m.profile = profile
        m.use_clamp_overlap = True
        m.miter_outer = 'MITER_ARC'
        _apply(ob, m)
        return ob

    def marker(self, name, pos, fwd=(0, 1, 0), up=(0, 0, 1), kind=None, size=0.01):
        """Marker empty: local +Y = ``fwd``, local +Z = ``up`` (orthogonalised)."""
        remove_tree(name)
        e = bpy.data.objects.new(name, None)
        e.empty_display_type = 'ARROWS'
        e.empty_display_size = size
        self.col.objects.link(e)
        e.parent = self.root
        f = Vector(fwd).normalized()
        u = Vector(up)
        u = (u - f * u.dot(f)).normalized()
        x = f.cross(u)
        M = Matrix((x, f, u)).transposed().to_4x4()
        M.translation = Vector(self.to_m([pos])[0])
        e.matrix_world = M
        e["gbp_marker"] = kind or name.replace("GBP_", "")
        self.markers[name] = e
        return e

    def finish(self, sharp=32.0, uv=True):
        """Sharp edges by angle, UV atlas, custom props on every mesh of the item."""
        for ob in self.objects.values():
            finish_mesh(ob, sharp, uv)
        return self.root


def _apply(ob, mod):
    dg = bpy.context.evaluated_depsgraph_get()
    new = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    ob.modifiers.remove(mod)
    old = ob.data
    name = old.name
    ob.data = new
    if old.users == 0:
        bpy.data.meshes.remove(old)
    new.name = name


def finish_mesh(ob, sharp=32.0, uv=True):
    """Shade smooth with sharp edges above ``sharp`` degrees; Smart-UV ``atlas`` map."""
    me = ob.data
    bm = bmesh.new()                    # drop boolean slivers; n-gons -> triangles (MikkTSpace tangents)
    bm.from_mesh(me)
    bmesh.ops.dissolve_degenerate(bm, dist=1e-7, edges=bm.edges)
    ngons = [f for f in bm.faces if len(f.verts) > 4]
    if ngons:
        bmesh.ops.triangulate(bm, faces=ngons, quad_method='BEAUTY', ngon_method='BEAUTY')
    bm.to_mesh(me)
    bm.free()
    if sharp is not None:
        me.shade_smooth()
        me.set_sharp_from_angle(angle=math.radians(sharp))
        if ob.get("gbp_sharp_slots"):                  # finish boundaries (grind line) are crisp
            bm = bmesh.new()
            bm.from_mesh(me)
            for e in bm.edges:
                f = e.link_faces
                if len(f) == 2 and f[0].material_index != f[1].material_index:
                    e.smooth = False
            bm.to_mesh(me)
            bm.free()
    if uv and len(me.polygons):
        if "atlas" not in me.uv_layers:
            me.uv_layers.new(name="atlas")
        _smart_uv(ob)
    ob["gb_layer"] = "prop"


def _smart_uv(ob):
    vl = bpy.context.view_layer
    for o in list(bpy.context.selected_objects):
        o.select_set(False)
    vl.objects.active = ob
    ob.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.smart_project(angle_limit=math.radians(60.0), island_margin=0.004)
    bpy.ops.object.mode_set(mode='OBJECT')
    ob.select_set(False)


def remove_tree(name):
    """Delete object ``name`` and all its children (and orphaned meshes)."""
    ob = bpy.data.objects.get(name)
    if ob is None:
        return
    for c in list(ob.children_recursive):
        _remove(c)
    _remove(ob)


def _remove(ob):
    data = ob.data
    bpy.data.objects.remove(ob, do_unlink=True)
    if data is not None and getattr(data, "users", 1) == 0 and isinstance(data, bpy.types.Mesh):
        bpy.data.meshes.remove(data)


def text_part(s, size, align='CENTER', extrude=0.0):
    """Mesh of a text string (Blender's built-in font), in the XY plane, units = ``size`` units.

    Returns (V, F) with the text centred on (0, 0) horizontally and baseline-centred vertically."""
    cu = bpy.data.curves.new("_gbp_text", type='FONT')
    cu.body = s
    cu.size = 1.0
    cu.align_x = align
    cu.align_y = 'CENTER'
    cu.extrude = extrude
    cu.resolution_u = 3
    ob = bpy.data.objects.new("_gbp_text", cu)
    bpy.context.scene.collection.objects.link(ob)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    V = np.array([v.co[:] for v in me.vertices]) * size
    F = [list(p.vertices) for p in me.polygons]
    bpy.data.objects.remove(ob, do_unlink=True)
    bpy.data.curves.remove(cu)
    bpy.data.meshes.remove(me)
    return V, F


def flat_slab(poly, z0, z1):
    """Prism in the XY plane (print marks, tape) - alias of ``prism(..., 'xy')``."""
    return prism(poly, z0, z1, "xy")


# ===========================================================================
# WEAPONS  (all item geometry in millimetres, item frame: +Y forward, +Z up, +X right)
# ===========================================================================
def build_pistol(col):
    """Generic polymer-frame striker pistol, 9 mm (no real make or markings).

    Item frame: bore axis on z = 0 along +Y, slide rear face at y = 0.  Root origin = grip centre
    (0, 31.5, -70).  Slide, barrel, frame, trigger, sights and levers are separate objects so the game
    can cycle the slide and pull the trigger.  Critical: bore 9.0 mm, barrel 114 mm, overall 192 mm,
    height 139 mm, slide width 25.4 mm, grip width 30 mm."""
    k = Kit("GBP_Pistol", col, origin=(0.0, 31.5, -70.0))
    # ---- slide: lofted rounded section, chamfered nose, serrations, ejection port, bore + rod holes
    def slide_sec(y, hw, zb, zt, rt=4.2, rb=1.2):
        s = rrect(hw, (zt - zb) / 2, (rb, rb, rt, rt), seg=4, cy=(zt + zb) / 2)
        return section_at(s, (0, y, 0), (1, 0, 0), (0, 0, 1))
    secs = [slide_sec(0.0, 11.9, -14.2, 14.2, 3.4), slide_sec(0.9, 12.7, -15.0, 15.0),
            slide_sec(176.0, 12.7, -15.0, 15.0), slide_sec(183.5, 12.3, -14.8, 14.6, 4.6),
            slide_sec(186.0, 11.2, -14.2, 13.4, 4.4)]
    slide = k.obj("GBP_Pistol_Slide", loft(secs), "GBPM_steel_nitride")
    k.boolean(slide, lathe([(150, 6.3), (190, 6.3)], 40, "y"))                                 # barrel hole
    k.boolean(slide, lathe([(165, 3.7), (190, 3.7)], 24, "y", centre=(0, 0, -10.6)))           # guide rod
    k.boolean(slide, box_mm((-5.5, 70.0, 4.2), (20.0, 120.0, 20.0)))                          # ejection port
    k.boolean(slide, box_mm((-7.5, 3.5, 15.0 - 1.4), (7.5, 14.5, 16.0)))                       # sight dovetail seat
    cut = []
    for i in range(9):                                                                         # rear serrations
        y = 9.0 + 3.1 * i
        for sx in (1, -1):
            poly = [(y - 0.65, -12.8), (y + 0.65, -12.8), (y + 2.3, 11.8), (y + 1.0, 11.8)]
            p = prism(poly, sx * 11.85, sx * 14.0, "yz")
            cut.append(p)
    k.boolean(slide, merge(*cut))
    k.bevel(slide, 0.45, 2, 35.0)
    # ---- barrel: tube with recessed crown, chamber hood visible in the port
    barrel = k.obj("GBP_Pistol_Barrel", merge(
        lathe([(123.0, 0.0), (123.0, 6.0), (184.7, 6.0), (185.5, 5.4), (185.5, 4.95), (185.0, 4.5),
               (126.0, 4.5), (126.0, 0.0)], 48, "y"),
        box_mm((-6.3, 71.5, -6.5), (6.3, 123.5, 13.4))), ["GBPM_steel_barrel", "GBPM_steel_bore"])
    _mat_by(barrel, lambda c, n: 1 if (math.hypot(c[0], c[2]) < 5.0 and c[1] > 123.2) else 0, k)
    k.obj("GBP_Pistol_GuideRod", lathe([(160, 0), (160, 3.1), (184.4, 3.1), (185.0, 2.6), (185.0, 0)],
                                             24, "y", centre=(0, 0, -10.6)), "GBPM_steel_nitride")
    # ---- frame (upper frame + grip + trigger guard hole + rail slots + magazine plate)
    upper = [(2, -15), (170, -15), (172, -17), (172, -26), (168, -28), (116, -28), (112, -31), (110.5, -50),
             (106, -55.5), (96, -57.2), (76, -57.2), (68, -53.5), (63, -46), (10, -46), (-3, -30), (-5.5, -24),
             (-6.0, -19.5), (-4.0, -15.6)]
    frame = k.obj("GBP_Pistol_Frame", prism(upper, -10.6, 10.6, "yz"), ["GBPM_polymer", "GBPM_polymer_grip"])
    k.bevel(frame, 2.2, 3, 30.0)
    front = []                                   # front strap with three shallow finger grooves
    for t in np.linspace(0.0, 1.0, 25):
        z = -44.0 - 66.0 * t
        y = 68.5 - 27.0 * t + (1.6 * math.sin(math.pi * ((t - 0.10) / 0.28)) ** 2 if 0.10 < t < 0.94 else 0.0)
        front.append((y, z))
    grip_poly = [(70, -36)] + front + [(40.0, -112), (-8.0, -112), (-8.5, -110), (12.0, -52), (11.0, -44),
                                       (6.0, -36), (-2.0, -30.5), (-5.0, -28), (28.0, -30.0)]
    grip = k.obj("_grip", prism(grip_poly, -15.0, 15.0, "yz"), "GBPM_polymer_grip")
    k.bevel(grip, 6.5, 5, 25.0, 0.55)
    _union_into(k, frame, grip)
    k.boolean(frame, prism([(107.5, -30.5), (106.8, -49.2), (102.5, -52.8), (80.0, -52.8), (72.0, -49.8),
                            (68.2, -44.0), (66.5, -30.5)], -20, 20, "yz"))                     # trigger guard hole
    for y0 in (130.0, 144.0, 158.0):                                                           # accessory rail
        k.boolean(frame, box_mm((-12, y0, -29.0), (12, y0 + 5.0, -25.6)))
    k.boolean(frame, box_mm((-12, 120.0, -29.0), (12, 168.0, -27.3)))
    _mat_by(frame, lambda c, n: 1 if c[2] < -36.0 and c[1] < 64.0 + (c[2] + 36.0) * 0.42 else 0, k)
    base = k.obj("GBP_Pistol_MagBase", prism([(40.5, -111.5), (41.8, -115.5), (40.0, -118.0), (-9.6, -118.0),
                                              (-10.6, -115.0), (-8.6, -111.5)], -15.4, 15.4, "yz"), "GBPM_polymer")
    k.bevel(base, 1.2, 2, 30.0)
    # ---- trigger with the centre safety blade
    trig = k.obj("GBP_Pistol_Trigger", merge(
        prism([(90.5, -30.0), (92.2, -36), (92.4, -42), (90.8, -47.8), (87.8, -49.6), (86.4, -48.2),
               (87.6, -42), (87.2, -36), (85.8, -30.0)], -3.0, 3.0, "yz"),
        prism([(92.0, -36.5), (93.9, -42.0), (93.0, -46.8), (91.2, -46.8), (92.2, -42.0), (90.6, -36.5)],
              -0.9, 0.9, "yz")), "GBPM_polymer")
    k.bevel(trig, 0.6, 2, 30.0)
    # ---- sights (three white dots), slide stop, takedown, magazine release, extractor
    rear = k.obj("GBP_Pistol_RearSight", prism([(-7.5, 13.9), (7.5, 13.9), (7.5, 19.2), (6.5, 20.6), (1.9, 20.6),
                                                (1.6, 18.0), (-1.6, 18.0), (-1.9, 20.6), (-6.5, 20.6),
                                                (-7.5, 19.2)], 4.0, 14.0, "xz"), "GBPM_steel_nitride")
    k.bevel(rear, 0.35, 2, 30.0)
    front = k.obj("GBP_Pistol_FrontSight", prism([(171.0, 14.0), (179.5, 14.0), (179.5, 19.6), (178.0, 21.0),
                                                  (172.5, 21.0)], -1.9, 1.9, "yz"), "GBPM_steel_nitride")
    k.bevel(front, 0.3, 2, 30.0)
    dots = [xform(lathe([(0.0, 0.0), (0.0, 1.1), (0.35, 1.1), (0.35, 0.0)], 20, "y"), t=(0.0, 170.8, 18.8))]
    for sx in (-4.4, 4.4):
        dots.append(xform(lathe([(0.0, 0.0), (0.0, 1.0), (0.35, 1.0), (0.35, 0.0)], 20, "y"), t=(sx, 3.75, 18.4)))
    k.obj("GBP_Pistol_SightDots", merge(*dots), "GBPM_sight_white")
    small = [box_mm((-11.9, 74.0, -18.8), (-10.4, 94.0, -14.9)),         # slide stop lever (left)
             box_mm((-11.4, 104.0, -20.2), (11.4, 110.0, -16.8)),        # takedown lever
             box_mm((-15.9, 61.5, -49.0), (-14.2, 67.5, -42.0)),         # magazine release (left)
             box_mm((12.5, 64.0, 5.0), (13.2, 84.0, 9.0))]                # extractor (right)
    lev = k.obj("GBP_Pistol_Levers", merge(*small), "GBPM_steel_nitride")
    k.bevel(lev, 0.35, 2, 30.0)
    # ---- markers
    k.marker("GBP_muzzle_pistol", (0, 185.5, 0), kind="muzzle")
    k.marker("GBP_pistol_front_sight", (0, 175.0, 21.0), kind="front_sight")
    k.marker("GBP_pistol_rear_sight", (0, 9.0, 18.0), kind="rear_sight")
    k.marker("GBP_pistol_ejection", (8.0, 95.0, 11.0), fwd=(1, 0, 0.35), kind="ejection")
    k.marker("GBP_pistol_grip", (0, 31.5, -70.0), kind="grip")
    k.root["gbp_bore_mm"] = SPEC["pistol"]["bore_d"]
    k.root["gbp_projectile"] = "9mm_fmj"
    return k


def _mat_by(ob, fn, k=None):
    """Set per-face material index from ``fn(face_centre, normal) -> slot``.

    With a Kit ``k`` the face centre is given in the item frame and unit (mm), else in metres."""
    me = ob.data
    n = len(me.polygons)
    C = np.zeros(n * 3)
    N = np.zeros(n * 3)
    me.polygons.foreach_get("center", C)
    me.polygons.foreach_get("normal", N)
    C, N = C.reshape(-1, 3), N.reshape(-1, 3)
    if k is not None:
        C = C / k.unit + k.origin
    idx = np.array([fn(c, nn) for c, nn in zip(C, N)], np.int32)
    me.polygons.foreach_set("material_index", idx)
    me.update()


def _union_into(k, target, other):
    """Boolean-union object ``other`` into ``target`` and delete ``other``."""
    m = target.modifiers.new("gbp_union", 'BOOLEAN')
    m.operation = 'UNION'
    m.object = other
    m.solver = 'EXACT'
    _apply(target, m)
    me = other.data
    k.objects.pop(other.name, None)
    bpy.data.objects.remove(other, do_unlink=True)
    if me.users == 0:
        bpy.data.meshes.remove(me)


def _smooth_curve(xs, ys, x):
    """Monotone cubic (Catmull-Rom style) interpolation of control points (xs ascending)."""
    xs, ys = np.asarray(xs, float), np.asarray(ys, float)
    x = np.asarray(x, float)
    i = np.clip(np.searchsorted(xs, x) - 1, 0, len(xs) - 2)
    t = (x - xs[i]) / (xs[i + 1] - xs[i])
    m = np.gradient(ys, xs)
    h = xs[i + 1] - xs[i]
    t2, t3 = t * t, t * t * t
    return ((2 * t3 - 3 * t2 + 1) * ys[i] + (t3 - 2 * t2 + t) * h * m[i] + (-2 * t3 + 3 * t2) * ys[i + 1]
            + (t3 - t2) * h * m[i + 1])


def build_shotgun(col):
    """Pump-action 12 gauge, 18.5" (470 mm) cylinder-bore barrel, walnut furniture (generic).

    Item frame: bore axis z = 0 along +Y, receiver rear y = 0, muzzle y = 675.  Root origin = wrist
    grip (0, -55, -33).  The forend (pump) is its own object so the game can rack it (travel 90 mm).
    Critical: bore 18.5 mm, barrel 470 mm, overall 987 mm."""
    k = Kit("GBP_Shotgun", col, origin=(0.0, -55.0, -33.0))
    # ---- receiver (black anodised aluminium) with ejection and loading ports
    def rsec(y, hw, zb, zt, rt=10.0, rb=3.0):
        s = rrect(hw, (zt - zb) / 2, (rb, rb, rt, rt), seg=5, cy=(zt + zb) / 2)
        return section_at(s, (0, y, 0), (1, 0, 0), (0, 0, 1))
    rec = k.obj("GBP_Shotgun_Receiver", loft([rsec(0.0, 14.2, -41.2, 15.8), rsec(1.2, 15.0, -42.0, 17.0),
                                             rsec(203.8, 15.0, -42.0, 17.0), rsec(205.0, 14.2, -41.2, 16.0)]),
                ["GBPM_alu_black", "GBPM_steel_polished"])
    k.boolean(rec, box_mm((6.5, 72.0, -7.0), (20.0, 150.0, 12.0)))                  # ejection port (right)
    k.boolean(rec, box_mm((-11.0, 40.0, -50.0), (11.0, 176.0, -35.0)))              # loading port (bottom)
    k.boolean(rec, lathe([(190.0, 13.3), (210.0, 13.3)], 40, "y"))                 # barrel seat
    k.bevel(rec, 0.8, 2, 30.0)
    bolt = k.obj("GBP_Shotgun_Bolt", box_mm((-6.0, 73.0, -6.2), (8.2, 149.0, 11.0)), "GBPM_steel_polished")
    k.bevel(bolt, 0.8, 2, 30.0)
    k.obj("GBP_Shotgun_Carrier", box_mm((-10.5, 42.0, -37.5), (10.5, 174.0, -35.5)), "GBPM_steel_blued")
    # ---- trigger group, guard loop, trigger, cross-bolt safety
    tg = k.obj("GBP_Shotgun_TriggerGuard", prism([(22, -41.5), (150, -41.5), (148, -47.5), (112, -48.5),
                                                  (110, -56), (104, -70), (95, -79.5), (67, -79.5), (57, -72),
                                                  (50, -58), (47, -48.5), (24, -47.0)], -8.0, 8.0, "yz"),
               "GBPM_alu_black")
    k.boolean(tg, prism([(103.5, -48.5), (100.5, -66), (93.5, -73.8), (68.5, -73.8), (61.5, -67.5), (56.5, -56),
                         (54.0, -48.5)], -12, 12, "yz"))
    k.bevel(tg, 1.4, 2, 30.0)
    trig = k.obj("GBP_Shotgun_Trigger", prism([(80.5, -47.0), (83.0, -54), (83.2, -61), (81.0, -68.5), (78.0, -69.5),
                                               (77.2, -67.8), (79.0, -61), (78.6, -54), (76.4, -47.0)],
                                              -3.4, 3.4, "yz"), "GBPM_steel_blued")
    k.bevel(trig, 0.5, 2, 30.0)
    k.obj("GBP_Shotgun_Safety", lathe([(-9.6, 0), (-9.6, 2.8), (9.6, 2.8), (9.6, 0)], 20, "x",
                                      centre=(0, 107.0, -44.5)), "GBPM_steel_blued")
    # ---- barrel (bore 18.5), magazine tube, cap, barrel lug, brass bead
    bore_r = SPEC["shotgun"]["bore_d"] / 2
    od_r = SPEC["shotgun"]["barrel_od_muzzle"] / 2
    barrel = k.obj("GBP_Shotgun_Barrel", lathe(
        [(196.0, 0.0), (196.0, 13.0), (213.0, 13.0), (216.0, 11.6), (300.0, 11.2), (671.8, od_r),
         (675.0, od_r - 0.4), (675.0, bore_r + 0.45), (674.4, bore_r), (222.0, bore_r), (222.0, 0.0)],
        56, "y"), ["GBPM_steel_blued", "GBPM_steel_bore"])
    _mat_by(barrel, lambda c, n: 1 if math.hypot(c[0], c[2]) < bore_r + 0.2 else 0, k)
    zt = -22.6
    tube = [lathe([(205.0, 0), (205.0, 11.0), (604.0, 11.0), (604.0, 0)], 40, "y", centre=(0, 0, zt))]
    cap = [(604.0, 0.0), (604.0, 12.6)]
    for i in range(9):
        y = 606.0 + i * 2.6
        cap += [(y, 12.6), (y + 0.6, 12.1), (y + 1.4, 12.1), (y + 2.0, 12.6)]
    cap += [(630.0, 12.6), (632.0, 11.6), (633.0, 8.0), (633.0, 0.0)]
    tube.append(lathe(cap, 40, "y", centre=(0, 0, zt)))
    k.obj("GBP_Shotgun_MagTube", merge(*tube), "GBPM_steel_blued")
    lug = k.obj("GBP_Shotgun_BarrelLug", box_mm((-5.5, 588.0, -20.0), (5.5, 603.5, -9.0)), "GBPM_steel_blued")
    k.bevel(lug, 1.0, 2, 30.0)
    k.obj("GBP_Shotgun_Bead", lathe([(-1.9, 0.0)] + [(1.9 * math.sin(a), 1.9 * math.cos(a))
                                                     for a in np.linspace(-1.2, 1.5708, 8)],
                                    16, "z", centre=(0, 666.0, 11.9)), "GBPM_brass")
    # ---- forend (pump): lofted walnut with ring grooves, channel for the barrel
    ys = np.linspace(262.0, 472.0, 106)
    secs = []
    for y in ys:
        g = 0.0
        if 300.0 <= y <= 430.0:
            ph = ((y - 300.0) % 13.0) / 13.0
            g = max(0.0, 1.0 - abs(ph - 0.5) * 5.0)
        end = min(y - 262.0, 472.0 - y)
        taper = 1.0 - 0.06 * max(0.0, 1.0 - end / 8.0) ** 2
        s = (1.0 - 0.075 * g) * taper
        pts = superellipse(22.5 * s, 21.5 * s, 2.3, 40, cy=-24.0)
        pts[:, 1] = np.maximum(pts[:, 1], -24.0 - 21.5 * s)
        secs.append(section_at(pts, (0, y, 0), (1, 0, 0), (0, 0, 1)))
    fore = k.obj("GBP_Shotgun_Forend", loft(secs), "GBPM_walnut")
    k.boolean(fore, lathe([(250.0, 12.2), (480.0, 12.2)], 40, "y"))
    k.boolean(fore, box_mm((-8.0, 250.0, -8.0), (8.0, 480.0, 14.0)))
    k.bevel(fore, 1.2, 2, 35.0)
    # ---- stock: walnut, lofted along -Y, rubber recoil pad
    cy = [0.0, -12.0, -40.0, -80.0, -140.0, -200.0, -260.0, -291.0]
    top = [15.8, 12.0, 3.0, -2.5, -9.0, -15.5, -21.5, -25.0]
    bot = [-41.5, -46.0, -61.0, -79.0, -102.0, -125.0, -148.0, -161.0]
    hw = [14.6, 15.2, 15.6, 17.2, 19.4, 20.8, 21.4, 21.4]
    yy = np.linspace(0.0, -291.0, 60)
    xs = np.array(cy[::-1])
    T = _smooth_curve(xs, top[::-1], yy)
    B = _smooth_curve(xs, bot[::-1], yy)
    H = _smooth_curve(xs, hw[::-1], yy)
    secs = []
    for y, t, b, w in zip(yy, T, B, H):
        pts = superellipse(w, (t - b) / 2, 2.6, 44, cy=(t + b) / 2)
        secs.append(section_at(pts, (0, y, 0), (1, 0, 0), (0, 0, 1)))
    stock = k.obj("GBP_Shotgun_Stock", loft(secs), "GBPM_walnut")
    k.bevel(stock, 1.5, 2, 30.0)
    pad_secs = []
    for y, s, r in ((-290.5, 1.0, 0.0), (-293.0, 1.012, 0.0), (-309.5, 1.03, 0.0), (-311.5, 0.99, 0.0),
                    (-312.0, 0.94, 0.0)):
        pts = superellipse(21.4 * s, (T[-1] - B[-1]) / 2 * s, 2.6, 44, cy=(T[-1] + B[-1]) / 2)
        pad_secs.append(section_at(pts, (0, y, 0), (1, 0, 0), (0, 0, 1)))
    k.obj("GBP_Shotgun_RecoilPad", loft(pad_secs), "GBPM_rubber_pad")
    # ---- markers
    k.marker("GBP_muzzle_shotgun", (0, 675.0, 0), kind="muzzle")
    k.marker("GBP_shotgun_bead", (0, 666.0, 13.8), kind="front_sight")
    k.marker("GBP_shotgun_ejection", (16.0, 110.0, 3.0), fwd=(1, 0, 0.3), kind="ejection")
    k.marker("GBP_shotgun_grip", (0, -55.0, -33.0), kind="grip")
    k.marker("GBP_shotgun_pump", (0, 367.0, -24.0), kind="support_hand")
    k.root["gbp_bore_mm"] = SPEC["shotgun"]["bore_d"]
    k.root["gbp_pump_travel_mm"] = 90.0
    return k


# ===========================================================================
# Test renders (plan §5.1: <= 640 px, <= 48 samples, denoised)
# ===========================================================================
def _stage_col():
    return prop_collections()[COL_STAGE]


def _stage_light(name, loc, target, energy, size, color=(1.0, 1.0, 1.0), kind='AREA'):
    data = bpy.data.lights.get(name) or bpy.data.lights.new(name, kind)
    data.energy = energy
    data.color = color
    if kind == 'AREA':
        data.size = size
    ob = bpy.data.objects.get(name) or bpy.data.objects.new(name, data)
    if ob.name not in _stage_col().objects:
        _stage_col().objects.link(ob)
    ob.location = loc
    gbc.look_at(ob, target)
    return ob


def studio(on=True):
    """Product studio for item renders: seamless grey sweep + key / fill / rim area lights."""
    names = ("GBP_StudioKey", "GBP_StudioFill", "GBP_StudioRim", "GBP_StudioSweep")
    if not on:
        for n in names:
            ob = bpy.data.objects.get(n)
            if ob is not None:
                ob.hide_render = True
        return
    if "GBP_StudioSweep" not in bpy.data.objects:
        ang = np.linspace(0, math.pi / 2, 12)
        prof = [(-3.0, 0.0), (0.4, 0.0)] + [(0.4 + 0.6 * math.sin(a), 0.6 - 0.6 * math.cos(a)) for a in ang[1:]] + \
               [(1.0, 3.0)]
        V, F = [], []
        for i, (y, z) in enumerate(prof):
            V += [(-4.0, y, z), (4.0, y, z)]
            if i:
                a = 2 * (i - 1)
                F.append([a, a + 1, a + 3, a + 2])
        me = bpy.data.meshes.new("GBP_StudioSweep")
        me.from_pydata(V, [], F)
        me.shade_smooth()
        mat = bpy.data.materials.get("GBP_StudioMat") or bpy.data.materials.new("GBP_StudioMat")
        mat.use_nodes = True
        b = next(n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED')
        b.inputs["Base Color"].default_value = (0.18, 0.185, 0.19, 1.0)
        b.inputs["Roughness"].default_value = 0.7
        me.materials.append(mat)
        ob = bpy.data.objects.new("GBP_StudioSweep", me)
        _stage_col().objects.link(ob)
    for n in names:
        if n in bpy.data.objects:
            bpy.data.objects[n].hide_render = False
    scene = bpy.context.scene
    world = bpy.data.worlds.get("GBP_World") or bpy.data.worlds.new("GBP_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.052, 0.056, 1.0)
    scene.world = world
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass


def _bbox(objs):
    pts = []
    for o in objs:
        if o.type == 'MESH' and len(o.data.vertices):
            M = np.array(o.matrix_world)
            V = np.array([v.co[:] for v in o.data.vertices])
            pts.append(V @ M[:3, :3].T + M[:3, 3])
    P = np.vstack(pts)
    return P.min(0), P.max(0)


def render_item(root, path, view=(-0.55, 1.0, 0.35), res=(640, 400), samples=40, lens=85.0, fill=0.86,
                place=(0.0, 0.0, 0.6), rotate=None, focus=None, span=None):
    """Render one prop root: move it to ``place`` (optionally rotated), frame its bounding box from
    direction ``view`` (camera -> subject is -view), under the studio lights, then restore."""
    studio(True)
    old = root.matrix_world.copy()
    R = Matrix.Identity(4) if rotate is None else rotate.to_4x4()
    root.matrix_world = Matrix.Translation(Vector(place)) @ R
    bpy.context.view_layer.update()
    kids = [o for o in root.children_recursive if o.type == 'MESH']
    lo, hi = _bbox(kids)
    c = (lo + hi) / 2 if focus is None else np.asarray(focus, float) + np.asarray(place, float)
    rad = float(np.linalg.norm(hi - lo)) / 2 if focus is None else span / 2
    d = np.asarray(view, float)
    d /= np.linalg.norm(d)
    aspect = res[0] / res[1]
    fov = 2 * math.atan(18.0 / lens) if aspect >= 1 else 2 * math.atan(18.0 / lens * aspect)
    fov_short = fov if aspect < 1 else 2 * math.atan(math.tan(fov / 2) / aspect)
    dist = rad / math.tan(fov_short / 2) / fill if focus is None else rad / math.tan(fov / 2 if aspect >= 1 else
                                                                                  fov_short / 2)
    loc = c + d * dist
    cam = gbc.add_camera("GBP_Cam", tuple(loc), tuple(c), lens)
    gbc.link(cam, _stage_col())
    cam.data.clip_start = 0.005
    scene = gbc.configure_render(samples, res)
    if focus is None:                              # fit the projected bounding box (2 passes)
        from bpy_extras.object_utils import world_to_camera_view
        corners = [Vector((x, y, z)) for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])]
        for _ in range(3):
            bpy.context.view_layer.update()
            uv = np.array([world_to_camera_view(scene, cam, p)[:2] for p in corners])
            span = max((uv[:, 0].max() - uv[:, 0].min()), (uv[:, 1].max() - uv[:, 1].min()))
            mid = (uv.min(0) + uv.max(0)) / 2 - 0.5
            dist *= span / fill
            # re-centre: shift the look-at point by the projected offset
            right = np.array(cam.matrix_world.to_3x3().col[0])
            upv = np.array(cam.matrix_world.to_3x3().col[1])
            w = 2 * dist * math.tan(fov / 2) if aspect >= 1 else 2 * dist * math.tan(fov_short / 2) * aspect
            c = c + right * mid[0] * w + upv * mid[1] * w / aspect
            cam.location = tuple(c + d * dist)
            gbc.look_at(cam, tuple(c))
    sweep = bpy.data.objects["GBP_StudioSweep"]
    s = max(0.25, float(np.linalg.norm(hi - lo)) * 1.25)
    back = -np.array([d[0], d[1], 0.0])
    back /= max(np.linalg.norm(back), 1e-9)
    ang = math.atan2(-back[0], back[1])
    sweep.rotation_euler = (0.0, 0.0, ang)
    ctr = (lo + hi) / 2
    sweep.location = (ctr[0] + back[0] * 0.4 * s, ctr[1] + back[1] * 0.4 * s, lo[2] - 0.004)
    sweep.scale = (s, s, s)
    key = _stage_light("GBP_StudioKey", tuple(c + np.array([-1.2, -0.3, 1.4]) * rad * 3), tuple(c), 150 * rad ** 2 * 9,
                       rad * 2.0, (1.0, 0.97, 0.92))
    fill_l = _stage_light("GBP_StudioFill", tuple(c + np.array([1.4, 0.6, 0.5]) * rad * 3), tuple(c),
                          50 * rad ** 2 * 9, rad * 3.0, (0.9, 0.94, 1.0))
    rim = _stage_light("GBP_StudioRim", tuple(c + np.array([0.3, -1.6, 0.9]) * rad * 3), tuple(c),
                       160 * rad ** 2 * 9, rad * 1.5)
    for L in (key, fill_l, rim):
        L.hide_render = False
    out = gbc.render(path, cam, samples, res)
    root.matrix_world = old
    bpy.context.view_layer.update()
    return out


def _knife_lines(y):
    """Blade outline (item mm): spine top z and edge z at blade station y (0 = heel, 120 = tip)."""
    y = np.asarray(y, float)
    top = np.where(y <= 78.0, 10.0, 10.0 - 16.0 * (np.clip(y - 78.0, 0, None) / 42.0) ** 1.8)
    bot = np.where(y <= 55.0, -15.0, -15.0 + 9.0 * (np.clip(y - 55.0, 0, None) / 65.0) ** 2.2)
    bot = bot + (y < 6.0) * 2.4 * np.sin(np.pi * np.clip(y / 6.0, 0, 1))          # sharpening choil
    return top, bot


def build_knife(col):
    """Single-edged fixed-blade knife: blade 120 x 25 mm (RB §2.3), 2.5 mm spine, drop point, flat
    grind from 35 % of the height with a 1 mm secondary edge bevel, distal taper; steel bolster,
    full tang between black G10 scales with three rivets.

    Item frame: blade along +Y, edge down (-Z), heel of the blade y = 0.  Root origin = handle centre
    (0, -60, -1).  Markers ``GBP_blade_edge_0..7`` sit on the edge from heel to tip with +Y = the edge's
    outward normal (cutting direction) and +Z = toward the tip; ``GBP_blade_tip`` points along the blade."""
    k = Kit("GBP_Knife", col, origin=(0.0, -60.0, -1.0))
    ys = np.concatenate([np.linspace(0.0, 110.0, 111), np.linspace(110.5, 119.6, 12)])
    top, bot = _knife_lines(ys)
    vg0 = 0.35
    rings, edge_rows = [], []
    nv = 0
    for y, t, b in zip(ys, top, bot):
        H = t - b
        ts = 1.25 if y < 60.0 else 1.25 - 0.8 * (y - 60.0) / 60.0          # distal taper
        g = float(np.clip((y - 4.0) / 5.0, 0.0, 1.0))                        # no grind on the ricasso
        vg = vg0 + (0.95 - vg0) * (1.0 - g)
        ve = max(vg + 0.02, 1.0 - 1.0 / H)
        vs = [0.0, 0.035] + list(np.linspace(vg, ve, 10)) + [ve + 0.5 * (1.0 - ve), 1.0]
        te = 0.2 + 0.25 * (1.0 - g)
        hs = []
        for v in vs:
            if v <= 0.0:
                h = 0.82 * ts
            elif v <= vg:
                h = ts
            elif v <= ve:
                h = ts + (te - ts) * (v - vg) / (ve - vg)
            else:
                h = te * (1.0 - v) / (1.0 - ve)
            hs.append(h)
        R = [(h, y, t - v * H) for v, h in zip(vs, hs)]
        L = [(-h, y, t - v * H) for v, h in zip(vs, hs)][:-1][::-1]
        rings.append(np.array(R + L))
        nv = len(vs)
    V, F = loft(rings, caps=False)
    K = len(rings[0])
    F.append(list(range(K))[::-1])                                            # heel cap (inside bolster)
    tip = len(V)
    V = np.vstack([V, [(0.0, 120.0, float(_knife_lines(120.0)[0]))]])
    last = (len(rings) - 1) * K
    F += [[last + j, last + (j + 1) % K, tip] for j in range(K)]
    def vidx(p):
        return p if p < nv else 2 * nv - 2 - p
    slots = []
    for i in range(len(rings) - 1):
        for p in range(K):
            q = (p + 1) % K
            lo_v = min(vidx(p), vidx(q))
            slots.append(1 if lo_v >= nv - 3 and ys[i] > 7.0 else (2 if lo_v >= 2 and ys[i] > 7.0 else 0))
    slots += [0] + [0] * K
    blade = k.obj("GBP_Knife_Blade", (V, F), ["GBPM_steel_satin", "GBPM_steel_edge", "GBPM_steel_ground"],
                  face_mat=slots)
    blade["gbp_sharp_slots"] = True
    # bolster / finger guard
    gs = rrect(10.4, 16.8, (4.0, 4.0, 3.0, 3.0), 4, cy=-5.2)
    bol = k.obj("GBP_Knife_Bolster", prism(gs, -6.5, 0.4, "xz"), "GBPM_steel_satin")
    k.bevel(bol, 1.1, 3, 30.0)
    # handle: tang + two G10 scales (lofted half superellipses) + rivets
    yy = np.concatenate([np.linspace(-6.0, -113.2, 50), [-114.6, -115.6, -116.0]])
    ctrl_y = [-116.0, -108.0, -88.0, -55.0, -20.0, -6.0]
    bz = _smooth_curve(ctrl_y, [12.4, 12.7, 11.2, 12.4, 11.6, 11.1], np.clip(yy, -116, -6))
    ax = _smooth_curve(ctrl_y, [9.4, 9.8, 9.0, 9.9, 8.9, 8.3], np.clip(yy, -116, -6))
    zc = -2.5 * np.clip((-6.0 - yy) / 110.0, 0, 1) ** 1.5 - 1.0
    shrink = np.ones_like(yy)
    shrink[-3:] = (0.94, 0.8, 0.5)
    secs_r = []
    tang_top, tang_bot = [], []
    for y, a, b, z0, s in zip(yy, ax, bz, zc, shrink):
        pts = superellipse(a * s, b * s, 2.4, 25, t0=-math.pi / 2, t1=math.pi / 2, endpoint=True)
        pts[:, 0] = np.maximum(pts[:, 0], 1.25)
        secs_r.append(section_at(pts, (0, y, z0), (1, 0, 0), (0, 0, 1)))
        tang_top.append((y, z0 + b * s * 0.985))
        tang_bot.append((y, z0 - b * s * 0.985))
    sc_r = loft(secs_r)
    k.obj("GBP_Knife_Scales", merge(sc_r, (sc_r[0] * np.array([-1, 1, 1]), sc_r[1])), "GBPM_g10_black")
    tang_poly = [(0.2, 10.0)] + tang_top + tang_bot[::-1] + [(0.2, -10.0)]
    k.obj("GBP_Knife_Tang", prism(tang_poly, -1.26, 1.26, "yz"), "GBPM_steel_satin")
    rv = []
    for y in (-27.0, -62.0, -97.0):
        a = float(np.interp(-y, -yy, ax))
        z0 = float(np.interp(-y, -yy, zc))
        rv.append(lathe([(-(a + 0.35), 0), (-(a + 0.35), 2.5), (-(a + 0.05), 3.0), (a + 0.05, 3.0), (a + 0.35, 2.5),
                         (a + 0.35, 0)], 24, "x", centre=(0, y, z0)))
    k.obj("GBP_Knife_Rivets", merge(*rv), "GBPM_steel_polished")
    # markers along the edge (equal arc length, heel -> tip)
    ye = np.linspace(9.0, 116.0, 600)
    _, be = _knife_lines(ye)
    seg = np.hypot(np.diff(ye), np.diff(be))
    cum = np.concatenate([[0], np.cumsum(seg)])
    for i, s in enumerate(np.linspace(0, cum[-1], 8)):
        y = float(np.interp(s, cum, ye))
        z = float(np.interp(s, cum, be))
        dy, dz = 0.2, float(_knife_lines(y + 0.1)[1] - _knife_lines(y - 0.1)[1])
        t = np.array([dy, dz]) / math.hypot(dy, dz)
        n = (0.0, t[1], -t[0])
        k.marker(f"GBP_blade_edge_{i}", (0.0, y, z), fwd=n, up=(0.0, t[0], t[1]), kind="blade_edge")
    k.marker("GBP_blade_tip", (0.0, 120.0, float(_knife_lines(120.0)[0])), kind="blade_tip")
    k.marker("GBP_knife_grip", (0.0, -60.0, -1.0), kind="grip")
    k.root["gbp_blade_mm"] = [SPEC["knife"]["blade_length"], SPEC["knife"]["blade_width"]]
    k.root["gbp_edges"] = 1
    return k


HAMMER_ZH = 300.0                                          # head centreline height (item mm)
HAMMER_CLAW = [(-14.0, 302.0), (-28.0, 302.4), (-42.0, 299.4), (-54.5, 292.0), (-64.0, 282.5), (-70.5, 271.5),
               (-73.2, 263.5)]


def _hammer_handle_ctrl():
    # (z, half width x, half depth y) of the hickory handle; the eye holds a 6.4 x 12.4 mm section
    return [(-2.4, 7.0, 10.0), (-2.0, 10.0, 14.2), (-1.0, 11.8, 16.6), (0.5, 12.4, 17.6), (6.0, 12.6, 17.8),
            (20.0, 12.0, 17.0), (45.0, 11.2, 15.8), (120.0, 11.0, 15.6), (190.0, 9.8, 14.4), (248.0, 8.0, 13.2),
            (272.0, 6.6, 12.5), (282.0, 6.4, 12.4), (322.0, 6.4, 12.4)]


def build_hammer(col):
    """Claw hammer: forged steel head (round face Ø 28 mm, polished, slight crown; curved split claw),
    hickory handle 322 mm, steel wedge.  RB §2.5: head 0.45-0.7 kg, face Ø 25-32 mm.

    Item frame: handle along +Z (butt at z = 0), face toward +Y, head centreline z = 300.  Root origin =
    grip point (0, -2.5, 70).  ``GBP_hammer_face`` at the face centre (+Y = strike direction);
    ``GBP_claw`` between the claw tips (+Y = claw tangent at the tips)."""
    k = Kit("GBP_Hammer", col, origin=(0.0, -2.5, 70.0))
    zh = HAMMER_ZH
    fr = SPEC["hammer"]["face_d"] / 2
    face = k.obj("GBP_Hammer_Head", lathe(
        [(6.0, 0.0), (6.0, 14.6), (19.0, 11.4), (33.0, 10.9), (44.0, 12.2), (51.0, fr), (56.6, fr),
         (57.5, fr - 0.6), (58.1, fr - 2.4), (58.35, 7.0), (58.4, 0.0)], 56, "y", centre=(0, 0, zh)),
        ["GBPM_steel_forged", "GBPM_steel_polished"])
    eye = k.obj("_eye", prism([(-12.6, -13.2), (-8.8, -17.0), (8.8, -17.0), (12.6, -13.2), (12.6, 8.2), (8.8, 12.0),
                               (-8.8, 12.0), (-12.6, 8.2)], zh - 20.0, zh + 20.0, "xy"), "GBPM_steel_forged")
    k.bevel(eye, 2.2, 3, 30.0)
    # claw: loft along the curved path, tapering to thin tips, then the V slot
    P = np.array([(0.0, y, z) for y, z in HAMMER_CLAW])
    Pd = np.stack([np.interp(np.linspace(0, len(P) - 1, 40), np.arange(len(P)), P[:, i]) for i in range(3)], 1)
    T, S, U = path_frames(Pd, up=(0, 0, 1))
    secs = []
    for i, (p, s, u) in enumerate(zip(Pd, S, U)):
        t = i / (len(Pd) - 1)
        w = 12.6 - 0.9 * t
        th = 11.4 * (1 - t) ** 1.25 + 1.5
        secs.append(section_at(rrect(w, th, min(2.4, th * 0.6), 3), p, s, u))
    claw = k.obj("_claw", loft(secs), "GBPM_steel_forged")
    _union_into(k, face, eye)
    _union_into(k, face, claw)
    k.boolean(face, prism([(0.0, -29.0), (4.0, -84.0), (-4.0, -84.0)], zh - 60.0, zh + 30.0, "xy"))
    # eye hole through the head for the handle
    ctrl = _hammer_handle_ctrl()
    k.boolean(face, prism(superellipse(6.45, 12.45, 2.2, 40, cy=-2.5), zh - 30.0, zh + 30.0, "xy"))
    k.bevel(face, 0.5, 2, 40.0)
    _mat_by(face, lambda c, n: 1 if (c[1] > 50.0 and n[1] > 0.5) or (c[1] < -58.0 and c[2] < 285.0) else 0, k)
    # handle
    secs = [section_at(superellipse(a, b, 2.2, 40, cy=-2.5), (0, 0, z), (1, 0, 0), (0, 1, 0)) for z, a, b in ctrl]
    k.obj("GBP_Hammer_Handle", loft(secs), "GBPM_hickory")
    k.obj("GBP_Hammer_Wedge", box_mm((-6.0, -3.3, zh + 17.0), (6.0, -1.7, zh + 22.6)), "GBPM_steel_forged")
    k.marker("GBP_hammer_face", (0.0, 58.4, zh), kind="hammer_face")
    tdir = Pd[-1] - Pd[-2]
    k.marker("GBP_claw", tuple(Pd[-1]), fwd=tuple(tdir), up=(0, 1, 0), kind="claw")
    k.marker("GBP_hammer_grip", (0.0, -2.5, 70.0), kind="grip")
    k.root["gbp_face_d_mm"] = SPEC["hammer"]["face_d"]
    return k


def build_torch(col):
    """Hand propane torch: 400 g propane cylinder (Ø 77.3 mm, plain blue paint, label band), brass
    coupling nut and valve body, black control knob, stainless burner tube Ø 16 mm with four air
    inlets and an open stabiliser nozzle; separate ``GBP_Torch_Flame`` (core cone ~20 mm, visible
    envelope 80 mm, emissive, toggled by the game).

    Item frame: cylinder axis +Y (bottom y = 0), nozzle exit y = 440.  Root origin = grip (0, 120, 0).
    ``GBP_torch_nozzle`` at the nozzle exit, +Y = flame axis."""
    k = Kit("GBP_Torch", col, origin=(0.0, 120.0, 0.0))
    R = SPEC["torch"]["cylinder_d"] / 2
    k.obj("GBP_Torch_Cylinder", lathe(
        [(7.0, 0.0), (6.4, 14.0), (4.8, 24.0), (2.6, 31.0), (0.6, 34.0), (0.0, 35.6), (0.5, 37.3), (2.2, R - 0.3),
         (4.2, R), (222.0, R), (229.0, R - 0.8), (238.0, R - 4.5), (247.0, 30.0), (255.0, 22.0), (260.5, 16.5),
         (263.0, 15.2), (268.0, 15.2), (268.0, 0.0)], 72, "y"), "GBPM_paint_blue")
    k.obj("GBP_Torch_Label", lathe([(62.0, R + 0.15), (188.0, R + 0.15), (188.0, R - 0.5), (62.0, R - 0.5)], 72, "y",
                                   loop=True), "GBPM_label")
    # label print: "PROPANE" wrapped around the band (generic, no brand)
    tv, tf = text_part("PROPANE", 22.0, extrude=0.0)
    ang = tv[:, 0] / (R + 0.2)
    pv = np.stack([(R + 0.22) * np.sin(ang), 125.0 + tv[:, 1], -(R + 0.22) * np.cos(ang)], 1)
    k.obj("GBP_Torch_Print", (pv, tf), "GBPM_print_red", recalc=False)
    thr = [(266.0, 0.0), (266.0, 11.0)]
    for i in range(6):
        y = 267.0 + i * 1.8
        thr += [(y, 12.7), (y + 0.9, 11.6)]
    thr += [(278.0, 11.6), (278.0, 0.0)]
    k.obj("GBP_Torch_Thread", lathe(thr, 40, "y"), "GBPM_brass")
    hexv = [(17.0 * math.cos(a), 17.0 * math.sin(a)) for a in np.radians(np.arange(0, 360, 60) + 30)]
    nut = k.obj("GBP_Torch_Nut", prism(hexv, 270.0, 290.0, "xz"), "GBPM_brass")
    k.bevel(nut, 1.0, 2, 30.0)
    k.obj("GBP_Torch_Valve", merge(
        lathe([(289.0, 0), (289.0, 13.5), (300.0, 13.5), (304.0, 12.0), (314.0, 11.0), (318.0, 9.2), (318.0, 0)],
              40, "y"),
        box_mm((-10.5, 293.0, -10.5), (10.5, 311.0, 10.5))), "GBPM_brass")
    # control knob on the right side: ribbed black plastic
    ribs = []
    for x in np.linspace(12.0, 28.0, 12):
        r = 12.0 if x < 26.5 else 12.0 - (x - 26.5) * 1.2
        pts = [(r * (1.0 - 0.06 * (j % 2)) * math.cos(a), r * (1.0 - 0.06 * (j % 2)) * math.sin(a))
               for j, a in enumerate(np.linspace(0, 2 * math.pi, 48, endpoint=False))]
        ribs.append(section_at(np.array(pts), (x, 302.0, 0.0), (0, 1, 0), (0, 0, 1)))
    k.obj("GBP_Torch_Knob", merge(loft(ribs), lathe([(9.0, 0), (9.0, 4.0), (12.5, 4.0), (12.5, 0)], 24, "x",
                                                       centre=(0, 302.0, 0))), "GBPM_plastic_black")
    # burner tube with air inlets, stabiliser nozzle, inner orifice
    tube = k.obj("GBP_Torch_Tube", lathe(
        [(316.0, 8.0), (424.0, 8.0), (426.0, 9.3), (440.0, 9.3), (440.0, 8.5), (428.0, 7.3), (318.0, 7.3)],
        48, "y", loop=True), ["GBPM_steel_stainless", "GBPM_room_dark"])
    holes = [lathe([(-12, 2.3), (12, 2.3)], 20, ax, centre=(0, 326.0, 0)) for ax in ("x", "z")]
    k.boolean(tube, merge(*holes))
    _mat_by(tube, lambda c, n: 1 if math.hypot(c[0], c[2]) < 7.6 else 0, k)
    k.obj("GBP_Torch_Orifice", lathe([(333.0, 0), (333.0, 7.4), (336.0, 7.4), (336.0, 1.0), (338.0, 0.6), (338.0, 0)],
                                     24, "y"), "GBPM_brass")
    # flame: bright core cone + faint envelope, emissive (plan §8.2: visible flame ~8 cm)
    L = SPEC["torch"]["flame_length"]
    core = lathe([(440.2, 0.0), (440.2, 5.6), (446.0, 5.0), (452.0, 3.8), (457.0, 2.2), (460.0, 0.0)], 32, "y")
    outer = lathe([(440.2, 0.0), (440.2, 7.9), (452.0, 9.2), (470.0, 9.4), (490.0, 7.6), (505.0, 5.2),
                   (514.0, 2.8), (440.0 + L, 0.0)], 40, "y")
    k.obj("GBP_Torch_Flame", merge(core, outer), ["GBPM_flame_core", "GBPM_flame_outer"],
          face_mat=[0] * len(core[1]) + [1] * len(outer[1]))
    k.marker("GBP_torch_nozzle", (0.0, 440.0, 0.0), kind="torch_nozzle")
    k.marker("GBP_torch_grip", (0.0, 120.0, 0.0), kind="grip")
    k.root["gbp_flame_length_mm"] = L
    k.root["gbp_flux_kw_m2"] = 150.0
    return k


def _fist_sdf():
    """Signed distance (mm) of a gloved right fist, palm down, knuckles +Y, thumb on -X."""
    A = __import__("gb_geom").head()

    def cap(x, y, z, a, b, ra, rb):
        a, b = np.asarray(a, float), np.asarray(b, float)
        ab = b - a
        L2 = float(ab @ ab)
        px, py, pz = x - a[0], y - a[1], z - a[2]
        t = np.clip((px * ab[0] + py * ab[1] + pz * ab[2]) / L2, 0, 1)
        dx, dy, dz = px - t * ab[0], py - t * ab[1], pz - t * ab[2]
        return np.sqrt(dx * dx + dy * dy + dz * dz) - (ra + (rb - ra) * t)

    def smin(a, b, kk):
        h = np.clip(0.5 + 0.5 * (b - a) / kk, 0, 1)
        return b * (1 - h) + a * h - kk * h * (1 - h)

    def rbox(x, y, z, c, hsz, r):
        qx = np.abs(x - c[0]) - hsz[0] + r
        qy = np.abs(y - c[1]) - hsz[1] + r
        qz = np.abs(z - c[2]) - hsz[2] + r
        out = np.sqrt(np.maximum(qx, 0) ** 2 + np.maximum(qy, 0) ** 2 + np.maximum(qz, 0) ** 2)
        return out + np.minimum(np.maximum(np.maximum(qx, qy), qz), 0) - r

    fingers = [  # MCP centre, lengths (prox, mid, dist), radii (prox, mid, dist)
        ((-29.0, 0.0, 0.0), (40.0, 23.0, 18.0), (10.6, 9.6, 8.6)),
        ((-8.8, 2.0, 1.0), (44.0, 27.0, 19.0), (10.9, 9.9, 8.8)),
        ((11.0, 0.0, 0.0), (41.0, 25.0, 18.5), (10.3, 9.3, 8.4)),
        ((29.0, -5.0, -3.0), (32.0, 19.0, 16.0), (9.1, 8.3, 7.6))]

    def fn(x, y, z):
        x, y, z = x * 1000.0, y * 1000.0, z * 1000.0
        palm = rbox(x, y, z, (0.5, -40.0, -8.0), (35.0, 38.0, 14.5), 9.5)
        d = palm
        fd = None
        for (m, (lp, lm, ld), (rp, rm, rd)) in fingers:
            m = np.array(m)
            base = np.array((m[0] * 0.6, -74.0, -4.0))
            meta = cap(x, y, z, base, m, 9.5, rp + 0.8)
            d = smin(d, meta, 5.0)
            pdir = np.array((0.0, -0.05, -1.0)) / np.linalg.norm((0.0, -0.05, -1.0))
            pip = m + lp * pdir
            mdir = np.array((0.0, -1.0, -0.12)) / np.linalg.norm((0.0, -1.0, -0.12))
            dip = pip + lm * mdir
            ddir = np.array((0.0, 0.12, 1.0)) / np.linalg.norm((0.0, 0.12, 1.0))
            tip = dip + ld * ddir
            f = smin(smin(cap(x, y, z, m, pip, rp, rp * 0.9), cap(x, y, z, pip, dip, rm, rm * 0.9), 2.0),
                     cap(x, y, z, dip, tip, rd, rd * 0.85), 2.0)
            pipk = np.sqrt((x - pip[0]) ** 2 + (y - pip[1] - 1.5) ** 2 + (z - pip[2] + 1.0) ** 2) - rm * 1.02
            f = smin(f, pipk, 2.0)
            knuckle = np.sqrt((x - m[0]) ** 2 + (y - m[1] - 1.0) ** 2 + (z - m[2] - 1.5) ** 2) - (rp + 1.2)
            f = smin(f, knuckle, 2.5)
            fd = f if fd is None else np.minimum(fd, f)
        d = smin(d, fd, 3.2)
        fill = rbox(x, y, z, (0.5, -15.0, -29.0), (33.0, 12.0, 10.0), 7.0)      # flesh inside the curl
        d = smin(d, fill, 3.0)
        th = cap(x, y, z, (-30.0, -68.0, -14.0), (-42.0, -40.0, -30.0), 13.0, 11.0)
        th = smin(th, cap(x, y, z, (-42.0, -40.0, -30.0), (-27.0, -15.0, -50.0), 11.0, 10.0), 2.5)
        th = smin(th, cap(x, y, z, (-27.0, -15.0, -50.0), (-7.0, -11.0, -52.5), 10.0, 8.8), 2.5)
        web = cap(x, y, z, (-35.0, -52.0, -20.0), (-30.0, -24.0, -30.0), 9.0, 7.5)  # thumb web
        d = smin(d, web, 3.0)
        d = smin(d, th, 1.6)
        # padded knuckle guard: a 2.4 mm raised layer that follows the dorsum over the knuckles
        region = rbox(x, y, z, (0.5, -9.0, 14.0), (37.0, 14.0, 12.0), 6.0)
        pad = np.maximum(d - 2.4, region)
        d = smin(d, pad, 0.8)
        wrist = np.sqrt(((x - 1.0) / 31.0) ** 2 + ((z + 9.0) / 18.5) ** 2) * 18.5 - 18.5
        wrist = np.maximum(wrist, np.maximum(y + 74.0 - 40.0, -(y + 140.0)))
        d = smin(d, wrist, 8.0)
        flare = np.clip((-y - 100.0) / 40.0, 0, 1)
        cuff = np.sqrt(((x - 2.0) / (31.0 + 3.0 * flare)) ** 2 + ((z + 9.0) / (20.5 + 3.0 * flare)) ** 2) * 20.5 \
            - 20.5 - 1.2 * flare
        cuff = np.maximum(cuff, np.maximum(y + 100.0, -(y + 140.0)))
        strap = np.sqrt(((x - 2.0) / 33.0) ** 2 + ((z + 9.0) / 22.5) ** 2) * 22.5 - 22.9
        strap = np.maximum(strap, np.maximum(y + 106.0, -(y + 124.0)))
        d = smin(d, np.minimum(cuff, strap), 2.0)
        return d / 1000.0
    return fn, A


def build_fist(col):
    """Gloved right fist (black leather tactical glove with a padded knuckle guard and strap cuff),
    signed-distance modelled and polygonised: the player's fist tool.

    Item frame: knuckles +Y (punch direction), back of the hand +Z, thumb on -X.  Root origin = palm
    centre (0, -40, -8).  ``GBP_fist_knuckles`` on the 2nd/3rd knuckle striking face (+Y)."""
    import gb_geom as gg
    k = Kit("GBP_Fist", col, origin=(0.0, -40.0, -8.0))
    fn, _A = _fist_sdf()
    me = gg.sdf_mesh("_fist", fn, (-0.064, -0.146, -0.072), (0.056, 0.024, 0.034), 0.0011, project=2)
    V = np.array([v.co[:] for v in me.vertices]) * 1000.0
    F = [list(p.vertices) for p in me.polygons]
    bpy.data.meshes.remove(me)
    ob = k.obj("GBP_Fist_Glove", (V, F), ["GBPM_glove", "GBPM_glove_pad"])
    m = ob.modifiers.new("dec", 'DECIMATE')
    m.ratio = min(1.0, 14000.0 / max(1, len(ob.data.polygons)))
    _apply(ob, m)
    _mat_by(ob, lambda c, n: 1 if ((c[2] > 9.0 and -24.0 < c[1] < 6.0 and n[2] > 0.35) or (-124.5 < c[1] < -105.5)) else 0,
            k)
    # knuckle marker on the front surface between index and middle MCP (ray-march the SDF)
    y = -10.0
    for _ in range(80):
        dd = float(fn(np.array([-19.0e-3]), np.array([y * 1e-3]), np.array([-8.0e-3]))[0]) * 1000.0
        if dd > 0:
            break
        y += 0.5
    k.marker("GBP_fist_knuckles", (-19.0, y, -8.0), kind="fist_knuckles")
    k.marker("GBP_fist_grip", (0.0, -40.0, -8.0), kind="grip")
    return k


def build_ruler(col):
    """ABFO No. 2 style forensic L-scale: white matte 1.2 mm plastic, arms 130 x 25 mm, two 100 mm
    scales from the inner corner (1 mm ticks 3 mm, 5 mm ticks 5 mm, 10 mm ticks 7 mm, 0.2 mm wide),
    cm numerals and three reference circles (geometry printed 0.06 mm proud).

    Item frame: lies in the XY plane (top face +Z).  Root origin = the common zero at the inner
    corner (25, 25, 0).  ``GBP_ruler_zero``: +Y along the Y scale, +Z up (X scale runs along +X)."""
    k = Kit("GBP_Ruler", col, origin=(25.0, 25.0, 0.0))
    body = k.obj("GBP_Ruler_Body", prism([(0, 0), (130, 0), (130, 25), (25, 25), (25, 130), (0, 130)], 0.0, 1.2, "xy"),
                 "GBPM_ruler_white")
    k.bevel(body, 0.3, 2, 30.0)
    z0, z1 = 1.2, 1.26
    marks = []
    for i in range(101):
        L = 7.0 if i % 10 == 0 else (5.0 if i % 5 == 0 else 3.0)
        w = 0.1
        marks.append(flat_slab([(25.0 - L, 25.0 + i - w), (25.0, 25.0 + i - w), (25.0, 25.0 + i + w),
                                (25.0 - L, 25.0 + i + w)], z0, z1))              # Y scale
        marks.append(flat_slab([(25.0 + i - w, 25.0 - L), (25.0 + i + w, 25.0 - L), (25.0 + i + w, 25.0),
                                (25.0 + i - w, 25.0)], z0, z1))                  # X scale
    for c in range(1, 11):
        tv, tf = text_part(str(c), 3.4)
        marks.append((np.column_stack([tv[:, 0] + 25.0 + 10 * c, tv[:, 1] + 25.0 - 11.5, np.full(len(tv), z1)]), tf))
        marks.append((np.column_stack([-tv[:, 1] + 25.0 - 11.5, tv[:, 0] + 25.0 + 10 * c, np.full(len(tv), z1)]), tf))
    tv, tf = text_part("mm", 2.6)
    marks.append((np.column_stack([tv[:, 0] + 118.0, tv[:, 1] + 5.0, np.full(len(tv), z1)]), tf))
    for cx, cy in ((12.5, 12.5), (12.5, 122.0), (122.0, 12.5)):
        ring = []
        for rr in (4.0, 3.6):
            ring.append([(cx + rr * math.cos(a), cy + rr * math.sin(a)) for a in np.linspace(0, 2 * math.pi, 48,
                                                                                            endpoint=False)])
        V = np.array([(x, y, z1) for x, y in ring[0] + ring[1]])
        F = [[i, (i + 1) % 48, 48 + (i + 1) % 48, 48 + i] for i in range(48)]
        marks.append((V, F))
    k.obj("GBP_Ruler_Print", merge(*marks), "GBPM_print_black", recalc=False, smooth=False)
    k.marker("GBP_ruler_zero", (25.0, 25.0, z1), kind="ruler_zero")
    k.root["gbp_scale_mm"] = 100.0
    return k


def build_penlight(col):
    """Medical penlight: black anodised aluminium Ø 13 mm x 140 mm, knurled grip band, pocket clip,
    tail button, chrome reflector with LED behind a glass lens.  Item frame: beam +Y; root origin =
    grip (0, -15, 0); ``GBP_penlight_beam`` at the lens (+Y)."""
    k = Kit("GBP_Penlight", col, origin=(0.0, -15.0, 0.0))
    prof = [(-70.0, 0.0), (-70.0, 3.6), (-69.2, 5.9), (-68.0, 6.5), (-52.0, 6.5), (-51.5, 6.1), (-50.5, 6.1),
            (-50.0, 6.5)]
    for i in range(24):                                  # knurled grip band (ring grooves)
        y = -40.0 + i * 1.6
        prof += [(y, 6.5), (y + 0.5, 6.22), (y + 0.9, 6.22), (y + 1.4, 6.5)]
    prof += [(39.0, 6.5), (43.0, 7.2), (66.5, 7.2), (68.6, 7.0), (70.0, 6.3), (70.0, 5.5), (69.4, 5.5), (64.5, 2.2),
             (64.5, 0.0)]
    body = k.obj("GBP_Penlight_Body", lathe(prof, 40, "y"), ["GBPM_alu_black", "GBPM_chrome"])
    _mat_by(body, lambda c, n: 1 if c[1] > 64.0 and math.hypot(c[0], c[2]) < 5.4 and n[1] > -0.2 else 0, k)
    k.obj("GBP_Penlight_Button", lathe([(-70.0, 0.0), (-70.0, 3.4), (-70.6, 3.0), (-71.0, 1.8), (-71.1, 0.0)],
                                       24, "y"), "GBPM_rubber_grey")
    k.obj("GBP_Penlight_LED", box_mm((-1.1, 64.5, -1.1), (1.1, 65.4, 1.1)), "GBPM_led")
    k.obj("GBP_Penlight_Lens", lathe([(69.1, 0.0), (69.1, 5.5), (69.5, 5.5), (69.5, 0.0)], 32, "y"), "GBPM_glass")
    # pocket clip: steel strip along +Z side, attached near the tail
    path = [(0.0, -63.0, 6.5), (0.0, -61.0, 7.8), (0.0, -50.0, 8.0), (0.0, -20.0, 7.5), (0.0, -14.0, 6.9)]
    Pd = np.array(path)
    Pd = np.stack([np.interp(np.linspace(0, len(Pd) - 1, 24), np.arange(len(Pd)), Pd[:, i]) for i in range(3)], 1)
    T, S, U = path_frames(Pd, up=(0, 0, 1))
    secs = [section_at(rrect(2.6, 0.4, 0.2, 2), p, s, u) for p, s, u in zip(Pd, S, U)]
    k.obj("GBP_Penlight_Clip", merge(loft(secs), lathe([(-63.8, 6.45), (-60.0, 6.45), (-60.0, 6.95),
                                                               (-63.8, 6.95)], 40, "y", loop=True),
                                            xform(lathe([(0, 0), (0, 1.2), (0.9, 1.2), (1.4, 0)], 16, "z"),
                                                  t=(0.0, -14.5, 6.0))), "GBPM_steel_polished")
    k.marker("GBP_penlight_beam", (0.0, 69.5, 0.0), kind="penlight_beam")
    k.marker("GBP_penlight_grip", (0.0, -15.0, 0.0), kind="grip")
    return k


def build_thermometer(col):
    """Digital probe thermometer (core temperature): white ABS body 100 x 28 x 18 mm with a recessed
    LCD and two rubber buttons, stainless probe Ø 3.5 x 123 mm with a conical tip.  Item frame: probe
    +Y; root origin = grip (0, -30, 0); ``GBP_thermo_tip`` (+Y) and ``GBP_thermo_display`` (+Y = screen
    normal) markers."""
    k = Kit("GBP_Thermometer", col, origin=(0.0, -30.0, 0.0))
    secs = []
    for y, hw, hh in ((-70.0, 12.5, 7.6), (-69.0, 13.6, 8.6), (-67.5, 14.0, 9.0), (12.0, 14.0, 9.0), (22.0, 11.5, 8.2),
                      (30.0, 8.0, 6.6), (32.0, 7.0, 6.0)):
        secs.append(section_at(rrect(hw, hh, min(hw, hh) * 0.62, 5), (0, y, 0), (1, 0, 0), (0, 0, 1)))
    body = k.obj("GBP_Thermometer_Body", loft(secs), "GBPM_abs_grey")
    k.boolean(body, box_mm((-10.5, -41.0, 8.2), (10.5, -3.0, 12.0)))
    k.bevel(body, 0.5, 2, 30.0)
    k.obj("GBP_Thermometer_LCD", box_mm((-10.3, -40.8, 7.9), (10.3, -3.2, 8.45)), "GBPM_lcd")
    btn = [lathe([(0.0, 0.0), (0.0, 3.4), (0.9, 3.1), (1.5, 2.0), (1.7, 0.0)], 24, "z", centre=(sx, -56.0, 8.4))
           for sx in (-5.5, 5.5)]
    k.obj("GBP_Thermometer_Buttons", merge(*btn), "GBPM_rubber_grey")
    pl = SPEC["thermometer"]["probe_length"]
    pr = SPEC["thermometer"]["probe_d"] / 2
    k.obj("GBP_Thermometer_Probe", merge(
        lathe([(30.0, 0.0), (30.0, 6.2), (34.0, 5.4), (38.0, 3.0), (40.0, 2.4), (40.0, 0.0)], 32, "y"),
        lathe([(38.0, 0.0), (38.0, pr), (38.0 + pl - 6.0, pr), (38.0 + pl - 0.4, 0.25), (38.0 + pl, 0.0)], 24, "y")),
        ["GBPM_plastic_black"])
    probe = k.objects["GBP_Thermometer_Probe"]
    probe.data.materials.append(material("GBPM_steel_polished"))
    _mat_by(probe, lambda c, n: 1 if c[1] > 39.0 else 0, k)
    k.marker("GBP_thermo_tip", (0.0, 38.0 + pl, 0.0), kind="thermo_tip")
    k.marker("GBP_thermo_display", (0.0, -22.0, 8.45), fwd=(0, 0, 1), up=(0, 1, 0), kind="thermo_display")
    k.marker("GBP_thermometer_grip", (0.0, -30.0, 0.0), kind="grip")
    return k


WEAPON_BUILDERS = (("pistol", build_pistol), ("shotgun", build_shotgun), ("knife", build_knife),
                   ("hammer", build_hammer), ("torch", build_torch), ("fist", build_fist), ("ruler", build_ruler),
                   ("penlight", build_penlight), ("thermometer", build_thermometer))
KITS = {}


def build_weapons(quick=False):
    """Build every weapon and examine tool into ``GBP_Weapons``; returns ``{item: root empty}``."""
    cols = prop_collections()
    out = {}
    for name, fn in WEAPON_BUILDERS:
        t0 = time.perf_counter()
        kit = fn(cols[COL_WEAPONS])
        kit.finish()
        KITS[name] = kit
        out[name] = kit.root
        gbc.log(f"props: {name:12s} {len(kit.objects):2d} meshes {sum(len(o.data.polygons) for o in kit.objects.values()):6d} "
                f"faces {len(kit.markers):2d} markers  {time.perf_counter() - t0:5.1f} s")
    return out


# ===========================================================================
# ROOM  (plan §1.3; Blender body frame metres: x = Godot x, y = -Godot z, z = Godot y)
# ===========================================================================
def room_bounds():
    """Interior planes in the body frame: (x0, x1, y0, y1, z0, z1)."""
    x0, x1 = ROOM["x"]
    gz0, gz1 = ROOM["z"]
    return x0, x1, -gz1, -gz0, 0.0, ROOM["height"]


def drain_xy():
    g = ROOM["drain_g"]
    return np.array([g[0], -g[2]])


def floor_height(x, y):
    """Epoxy floor height (m): 1 % fall toward the drain, zero at the subject mark (origin).

    h = fall * (|p - drain| - |drain|) - identical formula in room.json for world/room.gd."""
    d = drain_xy()
    return ROOM["floor_fall"] * (np.hypot(np.asarray(x) - d[0], np.asarray(y) - d[1]) - float(np.hypot(*d)))


def _perimeter(x0, x1, y0, y1, step, extra=()):
    """CCW points on a rectangle incl. its corners (+ extra x or y breakpoints on the front side)."""
    pts = []
    sides = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    for si, (a, b) in enumerate(sides):
        a, b = np.array(a), np.array(b)
        L = float(np.linalg.norm(b - a))
        ts = list(np.linspace(0, 1, max(2, int(math.ceil(L / step)) + 1))[:-1])
        if si == 0:
            ts += [(e - x0) / (x1 - x0) for e in extra]
        for t in sorted(set(np.round(ts, 9))):
            pts.append(a + (b - a) * t)
    return np.array(pts)


def _door_rect():
    cx = ROOM["door_g"][0]
    w, h = ROOM["door_size"]
    return cx - w / 2 - 0.02, cx + w / 2 + 0.02, h + 0.02                # opening x0, x1, top z


def build_floor(k, quick=False):
    """Epoxy floor (cone falling 1 % to the drain) + coved skirting up to ``cove_top``."""
    x0, x1, y0, y1, _, _ = room_bounds()
    rc = ROOM["cove_r"]
    dx0, dx1, _ = _door_rect()
    b = _perimeter(x0 + rc, x1 - rc, y0 + rc, y1 - rc, 0.2 if quick else 0.08,
                   extra=(dx0 - 0.001, dx0 + 0.001, dx1 - 0.001, dx1 + 0.001))
    c = drain_xy()
    r0 = ROOM["drain_d"] / 2 + 0.008
    NJ = 14 if quick else 34
    ts = (np.arange(NJ + 1) / NJ) ** 1.7
    rings = []
    for t in ts:
        ring = []
        for p in b:
            v = p - c
            L = float(np.linalg.norm(v))
            q = c + v * (r0 / L + t * (1 - r0 / L))
            ring.append((q[0], q[1], float(floor_height(q[0], q[1]))))
        rings.append(ring)
    V, F = loft(rings, caps=False)
    # cove profile per boundary point (outward offset to the wall plane); flat through the door
    n_th = 7
    prof_rows = []
    for p in b:
        o = np.array([(x1 if p[0] > x1 - rc - 1e-6 else (x0 if p[0] < x0 + rc + 1e-6 else p[0])) - p[0],
                      (y1 if p[1] > y1 - rc - 1e-6 else (y0 if p[1] < y0 + rc + 1e-6 else p[1])) - p[1]])
        h = float(floor_height(p[0], p[1]))
        in_door = dx0 < p[0] < dx1 and p[1] < y0 + rc + 1e-6
        row = []
        if in_door:
            o = np.array([0.0, -(rc + 0.045)])
            for j in range(n_th + 2):
                s = (j + 1) / (n_th + 2)
                row.append((p[0] + o[0] * s, p[1] + o[1] * s, h))
        else:
            for j in range(1, n_th + 1):
                th = math.radians(90.0 * j / n_th)
                row.append((p[0] + o[0] * math.sin(th), p[1] + o[1] * math.sin(th), h + rc * (1 - math.cos(th))))
            w = p + o
            row.append((w[0], w[1], ROOM["cove_top"] - 0.004))
            row.append((w[0], w[1], ROOM["cove_top"]))
        prof_rows.append(row)
    nb = len(b)
    base = len(V)
    P = np.array(prof_rows)                                   # (nb, n_th + 2, 3)
    V = np.vstack([V, P.reshape(-1, 3)])
    outer = (len(rings) - 1) * nb
    m = P.shape[1]
    for i in range(nb):
        i2 = (i + 1) % nb
        F.append([outer + i, outer + i2, base + i2 * m, base + i * m])
        for j in range(m - 1):
            F.append([base + i * m + j, base + i2 * m + j, base + i2 * m + j + 1, base + i * m + j + 1])
    ob = k.obj("GBP_Room_Floor", (V, F), "GBPM_room_epoxy", recalc=False)
    _flip_if(ob, (0, 0, 1), lambda c: c[2] < 0.05)
    _metric_uv(ob, "xy")
    return ob


def _flip_if(ob, want, sel):
    """Make faces selected by ``sel(centre)`` face roughly toward ``want`` (open surfaces)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.faces.ensure_lookup_table()
    votes = [f.normal.dot(Vector(want)) for f in bm.faces if sel(f.calc_center_median())]
    if votes and np.mean(votes) < 0:
        bmesh.ops.reverse_faces(bm, faces=bm.faces)
    bm.to_mesh(ob.data)
    bm.free()


def _metric_uv(ob, plane="xy", name="atlas"):
    """UV = world metres in the given plane (tileable room textures)."""
    me = ob.data
    if name not in me.uv_layers:
        me.uv_layers.new(name=name)
    uv = me.uv_layers[name]
    ia, ib = {"xy": (0, 1), "xz": (0, 2), "yz": (1, 2)}[plane]
    co = np.array([v.co[:] for v in me.vertices])
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    data = np.stack([co[li, ia], co[li, ib]], 1).astype(np.float32)
    uv.data.foreach_set("uv", data.ravel())


def _wall_uv(ob):
    """Per-face wall-plane metric UVs (u along the wall, v = height)."""
    me = ob.data
    uv = me.uv_layers.get("atlas") or me.uv_layers.new(name="atlas")
    co = np.array([v.co[:] for v in me.vertices])
    out = np.zeros((len(me.loops), 2), np.float32)
    for p in me.polygons:
        n = p.normal
        use_x = abs(n.x) > abs(n.y)
        for li in p.loop_indices:
            v = co[me.loops[li].vertex_index]
            out[li] = (v[1] if use_x else v[0], v[2])
    uv.data.foreach_set("uv", out.ravel())


def _walls():
    """The four walls: (name, axis index of the plane, plane value, inward sign, u-axis index, u range)."""
    x0, x1, y0, y1, _, _ = room_bounds()
    return [("back", 1, y1, -1, 0, (x0, x1)), ("front", 1, y0, 1, 0, (x0, x1)),
            ("left", 0, x0, 1, 1, (y0, y1)), ("right", 0, x1, -1, 1, (y0, y1))]


def _rect_minus(r, hole):
    """Axis-aligned rectangle minus a hole -> list of rectangles (u0, u1, v0, v1)."""
    u0, u1, v0, v1 = r
    h0, h1, g0, g1 = hole
    if h1 <= u0 or h0 >= u1 or g1 <= v0 or g0 >= v1:
        return [r]
    out = []
    if u0 < h0:
        out.append((u0, h0, v0, v1))
    if h1 < u1:
        out.append((h1, u1, v0, v1))
    a0, a1 = max(u0, h0), min(u1, h1)
    if v0 < g0:
        out.append((a0, a1, v0, g0))
    if g1 < v1:
        out.append((a0, a1, g1, v1))
    return [q for q in out if q[1] - q[0] > 0.004 and q[3] - q[2] > 0.004]


def build_walls(k, quick=False):
    """Glazed 150 mm tiles as real cushion-edged pads (face exactly on the wall plane) over a grout
    backing 1.5 mm behind it; the grout joints are real 2 mm gaps.  Tiles run from the cove top to the
    ceiling, cut at corners, around the door and hidden behind the backstop."""
    tile, grout, relief = ROOM["tile"], ROOM["grout"], ROOM["tile_relief"]
    pitch = tile + grout
    x0, x1, y0, y1, z0, z1 = room_bounds()
    dx0, dx1, dtop = _door_rect()
    bw, bh, _bd = ROOM["backstop_size"]
    phis = np.radians([0.0, 45.0, 90.0]) if not quick else np.radians([0.0, 90.0])
    TV, TF, TID = [], [], []
    GV, GF = [], []
    vstart = ROOM["cove_top"] + grout / 2
    for wi, (wname, ax, plane, inward, uax, (ua, ub)) in enumerate(_walls()):
        uc = (ua + ub) / 2
        n_half = int(math.ceil((ub - ua) / 2 / pitch)) + 1
        rows = int(math.ceil((z1 - vstart) / pitch)) + 1
        # winding: (e_u x e_z) must point into the room (inward * e_ax), else reverse every face
        flip = (uax == 0 and inward == 1) or (uax == 1 and inward == -1)
        holes = []
        if wname == "front":
            holes.append((dx0 - 0.045, dx1 + 0.045, -1.0, dtop + 0.045))
        for i in range(-n_half, n_half):
            for j in range(rows):
                u0 = uc + grout / 2 + i * pitch
                v0 = vstart + grout / 2 + j * pitch
                r = (max(u0, ua + grout / 2), min(u0 + tile, ub - grout / 2), v0, min(v0 + tile, z1 - grout / 2))
                if r[1] - r[0] < 0.004 or r[3] - r[2] < 0.004:
                    continue
                if wname == "back" and r[0] > -bw / 2 + 0.03 and r[1] < bw / 2 - 0.03 and r[3] < bh - 0.03:
                    continue                                          # fully hidden behind the backstop
                pieces = [r]
                for hole in holes:
                    pieces = [q for p in pieces for q in _rect_minus(p, hole)]
                for (a0, a1, b0, b1) in pieces:
                    base = len(TV)
                    for phi in phis:
                        ins = 0.001 * (1 - math.sin(phi)) if len(phis) > 2 else (0.001 if phi == 0 else 0.0)
                        dep = relief * (1 - math.cos(phi))
                        w = plane - inward * dep
                        for (uu, vv) in ((a0 + ins, b0 + ins), (a1 - ins, b0 + ins), (a1 - ins, b1 - ins),
                                         (a0 + ins, b1 - ins)):
                            p = [0.0, 0.0, vv]
                            p[ax] = w
                            p[uax] = uu
                            TV.append(p)
                            TID.append((wi * 100 + i + n_half, j))
                    tf = [[base, base + 1, base + 2, base + 3]]
                    for rr in range(len(phis) - 1):
                        a, bq = base + 4 * rr, base + 4 * (rr + 1)
                        for e in range(4):
                            tf.append([a + e, bq + e, bq + (e + 1) % 4, a + (e + 1) % 4])
                    TF += [f[::-1] for f in tf] if flip else tf
        # grout backing plane (with the door opening cut out)
        w = plane - inward * relief
        u_lo, u_hi = ua - relief, ub + relief
        rects = [(u_lo, u_hi, ROOM["cove_top"] - 0.02, z1)]
        for hole in holes:
            rects = [q for p in rects for q in _rect_minus(p, (hole[0] + 0.04, hole[1] - 0.04, hole[2],
                                                              hole[3] - 0.04))]
        for (a0, a1, b0, b1) in rects:
            base = len(GV)
            for (uu, vv) in ((a0, b0), (a1, b0), (a1, b1), (a0, b1)):
                p = [0.0, 0.0, vv]
                p[ax] = w
                p[uax] = uu
                GV.append(p)
            GF.append([base + 3, base + 2, base + 1, base] if flip else [base, base + 1, base + 2, base + 3])
    TV = np.array(TV)
    tiles = k.obj("GBP_Room_Tiles", (TV, TF), "GBPM_room_tile", recalc=False)
    grout_ob = k.obj("GBP_Room_Grout", (np.array(GV), GF), "GBPM_room_grout", recalc=False)
    for ob in (tiles, grout_ob):
        _wall_uv(ob)
    me = tiles.data
    uv1 = me.uv_layers.new(name="tile_id")
    li = np.zeros(len(me.loops), np.int64)
    me.loops.foreach_get("vertex_index", li)
    uv1.data.foreach_set("uv", np.asarray(TID, np.float32)[li].ravel())
    return tiles, grout_ob


def build_ceiling(k):
    """Ceiling plane at 3.0 m with two recessed 1.2 x 0.6 m LED panels (aluminium frame + diffuser)."""
    x0, x1, y0, y1, _, z1 = room_bounds()
    pw, pd = ROOM["panel_size"]
    pys = [-g for g in ROOM["panel_z"]]
    xs = sorted({x0, x1, -pw / 2, pw / 2})
    ys = sorted({y0, y1} | {py - pd / 2 for py in pys} | {py + pd / 2 for py in pys})
    V, F = [], []
    for i in range(len(xs) - 1):
        for j in range(len(ys) - 1):
            cx, cy = (xs[i] + xs[i + 1]) / 2, (ys[j] + ys[j + 1]) / 2
            if any(abs(cx) < pw / 2 and abs(cy - py) < pd / 2 for py in pys):
                continue
            b = len(V)
            V += [(xs[i], ys[j], z1), (xs[i], ys[j + 1], z1), (xs[i + 1], ys[j + 1], z1), (xs[i + 1], ys[j], z1)]
            F.append([b, b + 1, b + 2, b + 3])                               # faces down
    ceil = k.obj("GBP_Room_Ceiling", (np.array(V), F), "GBPM_room_ceiling", recalc=False, smooth=False)
    _metric_uv(ceil, "xy")
    frames, diff = [], []
    for py in pys:
        outer = rrect(pw / 2, pd / 2, 0.0, 1, cy=py)
        inner = rrect(pw / 2 - 0.02, pd / 2 - 0.02, 0.0, 1, cy=py)
        Vf = [(x, y, z1 - 0.004) for x, y in outer] + [(x, y, z1 - 0.004) for x, y in inner] + \
             [(x, y, z1) for x, y in outer]
        Ff = [[i, 4 + i, 4 + (i + 1) % 4, (i + 1) % 4] for i in range(4)]
        Ff += [[8 + i, i, (i + 1) % 4, 8 + (i + 1) % 4] for i in range(4)]
        Vi = [(x, y, z1 - 0.004) for x, y in inner] + [(x, y, z1 - 0.008) for x, y in inner]
        Fi = [[4 + i, i, (i + 1) % 4, 4 + (i + 1) % 4] for i in range(4)]
        frames.append((np.array(Vf), Ff))
        frames.append((np.array(Vi), Fi))
        diff.append((np.array([(x, y, z1 - 0.008) for x, y in inner]), [[0, 1, 2, 3][::-1]]))
    fr = k.obj("GBP_Room_PanelFrames", merge(*frames), "GBPM_room_alu", recalc=False, smooth=False)
    df = k.obj("GBP_Room_LightPanels", merge(*diff), "GBPM_room_led", recalc=False, smooth=False)
    for ob in (ceil, df):
        _face_toward(ob, (0, 0, -1))
    _face_toward_center(fr)
    _metric_uv(df, "xy")
    return ceil, df


def _face_toward(ob, want):
    """Make every face of ``ob`` point toward ``want``."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if f.normal.dot(Vector(want)) < 0])
    bm.to_mesh(me)
    bm.free()


def _face_toward_center(ob, c=None):
    """Make faces point toward the room interior point ``c`` (default room centre)."""
    x0, x1, y0, y1, _, _ = room_bounds()
    c = Vector(c or ((x0 + x1) / 2, (y0 + y1) / 2, 1.5))
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.reverse_faces(bm, faces=[f for f in bm.faces if f.normal.dot(c - f.calc_center_median()) < 0])
    bm.to_mesh(me)
    bm.free()


def _blur2(a, n=2):
    """Separable [1 2 1]/4 blur, ``n`` passes, edge-clamped."""
    for _ in range(n):
        a = (np.pad(a, ((1, 1), (0, 0)), mode="edge")[:-2] + 2 * a + np.pad(a, ((1, 1), (0, 0)), mode="edge")[2:]) / 4
        a = (np.pad(a, ((0, 0), (1, 1)), mode="edge")[:, :-2] + 2 * a + np.pad(a, ((0, 0), (1, 1)), mode="edge")[:, 2:]) / 4
    return a


def build_backstop(k, quick=False):
    """Bullet backstop: galvanised steel frame 2.4 x 2.2 x 0.3 m against the rear wall, front plane
    exactly at Godot z = -1.3 (body y = +1.3), filled with 16 rubber-granulate blocks (lumpy faces,
    rounded edges, a scatter of old bullet pocks in the chest/head zone)."""
    bw, bh, bd = ROOM["backstop_size"]
    yf = -ROOM["backstop_front_z"]
    yb = yf + bd
    zb = 0.010
    fw = 0.06
    rng = gbc.rng("room")
    parts = []
    # frame: side posts, top cap, bottom kick plate (front faces on the front plane)
    for x in (-bw / 2, bw / 2 - fw):
        parts.append(box_mm((x, yf, zb), (x + fw, yb, zb + bh)))
    parts.append(box_mm((-bw / 2, yf, zb + bh - fw), (bw / 2, yb, zb + bh)))
    parts.append(box_mm((-bw / 2, yf, zb), (bw / 2, yb, zb + 0.10)))
    frame = k.obj("GBP_Room_BackstopFrame", merge(*parts), "GBPM_room_galv")
    # rubber blocks
    ix0, ix1 = -bw / 2 + fw, bw / 2 - fw
    iz0, iz1 = zb + 0.10, zb + bh - fw
    nc, nr = 4, 4
    gap = 0.004
    bwid = (ix1 - ix0 - gap * (nc - 1)) / nc
    bhei = (iz1 - iz0 - gap * (nr - 1)) / nr
    pocks = []
    for _ in range(0 if quick else 34):
        pocks.append((rng.normal(0.0, 0.16), rng.uniform(0.95, 1.75), rng.uniform(0.004, 0.009), rng.uniform(0.003, 0.009)))
    blocks = []
    for ci in range(nc):
        for ri in range(nr):
            bx0 = ix0 + ci * (bwid + gap)
            bz0 = iz0 + ri * (bhei + gap)
            central = ci in (1, 2) and ri in (1, 2, 3)
            step = 0.03 if quick else 0.02
            nu = max(3, int(round(bwid / step)))
            nv = max(3, int(round(bhei / step)))
            u = np.linspace(0, 1, nu + 1)
            v = np.linspace(0, 1, nv + 1)
            U, W = np.meshgrid(u, v, indexing="ij")
            X = bx0 + U * bwid
            Z = bz0 + W * bhei
            noise = _blur2(rng.normal(0, 1, X.shape), 2)
            noise = noise / max(1e-9, noise.std())
            depth = 0.004 + 0.0012 * noise                                  # behind the front plane
            ed = np.minimum(np.minimum(U * bwid, (1 - U) * bwid), np.minimum(W * bhei, (1 - W) * bhei))
            rr = 0.012
            depth += np.where(ed < rr, rr - np.sqrt(np.clip(rr * rr - (rr - ed) ** 2, 0, None)), 0.0)
            for (px, pz, pr, pdp) in pocks:
                d2 = (X - px) ** 2 + (Z - pz) ** 2
                depth += pdp * np.exp(-d2 / (pr * pr)) - 0.0012 * np.exp(-d2 / (2.2 * pr) ** 2)
            depth = np.clip(depth, 0.0005, 0.05)
            Y = yf + depth
            base = sum(len(b[0]) for b in blocks)
            Vb = np.stack([X, Y, Z], -1).reshape(-1, 3)
            Fb = []
            for i in range(nu):
                for j in range(nv):
                    a = i * (nv + 1) + j
                    Fb.append([a, a + nv + 1, a + nv + 2, a + 1])
            # skirt back to the rear so the gaps between blocks look solid
            ring = [i * (nv + 1) for i in range(nu + 1)] + [nu * (nv + 1) + j for j in range(1, nv + 1)] + \
                   [i * (nv + 1) + nv for i in range(nu - 1, -1, -1)] + [j for j in range(nv - 1, 0, -1)]
            back = len(Vb)
            Vb = np.vstack([Vb, Vb[ring] * np.array([1, 0, 1]) + np.array([0, yf + 0.06, 0])])
            for q in range(len(ring)):
                Fb.append([ring[q], ring[(q + 1) % len(ring)], back + (q + 1) % len(ring), back + q])
            blocks.append((Vb, Fb))
    rub = k.obj("GBP_Room_Backstop", merge(*blocks), "GBPM_room_rubber", recalc=False)
    _orient_by_center(rub, (0.0, yf + 0.03, 1.1), outward=True)
    k.obj("GBP_Room_BackstopBacking", box_mm((ix0, yf + 0.03, iz0), (ix1, yb, iz1)), "GBPM_room_dark")
    _metric_uv(rub, "xz")
    return frame, rub


def _orient_by_center(ob, c, outward=True):
    """Orient faces away from (outward) or toward a point."""
    me = ob.data
    bm = bmesh.new()
    bm.from_mesh(me)
    cv = Vector(c)
    bad = [f for f in bm.faces if (f.normal.dot(f.calc_center_median() - cv) < 0) == outward]
    bmesh.ops.reverse_faces(bm, faces=bad)
    bm.to_mesh(me)
    bm.free()


def build_drain(k):
    """Ø 150 mm stainless floor drain: flush frame ring, slotted grate 2 mm below the rim, dark sump."""
    c = drain_xy()
    r = ROOM["drain_d"] / 2
    h = float(floor_height(c[0] + r + 0.008, c[1]))                  # rim height = floor at the ring
    ring = lathe([(h - 0.012, r - 0.002), (h - 0.0005, r - 0.002), (h, r + 0.0005), (h, r + 0.008),
                  (h - 0.012, r + 0.008)], 64, "z", centre=(c[0], c[1], 0.0), loop=True)
    grate_t = 0.003
    grate = lathe([(h - 0.002 - grate_t, 0.0), (h - 0.002 - grate_t, r - 0.0025), (h - 0.002, r - 0.0025),
                   (h - 0.002, 0.0)], 64, "z", centre=(c[0], c[1], 0.0))
    sump = lathe([(h - 0.011, r - 0.002), (h - 0.09, r - 0.002), (h - 0.09, 0.0)], 48, "z", centre=(c[0], c[1], 0.0))
    ob = k.obj("GBP_Room_Drain", merge(ring, grate), "GBPM_room_stainless")
    slots = []
    for i in range(-4, 5):
        x = c[0] + i * 0.0145
        half = math.sqrt(max(0.0, (r - 0.012) ** 2 - (i * 0.0145) ** 2))
        slots.append(box_mm((x - 0.004, c[1] - half, h - 0.02), (x + 0.004, c[1] + half, h - 0.0015)))
    k.boolean(ob, merge(*slots))
    s = k.obj("GBP_Room_DrainSump", sump, "GBPM_room_dark", recalc=False)
    _orient_by_center(s, (c[0], c[1], h - 0.04), outward=False)
    return ob, h


def build_door(k):
    """Painted steel door (0.9 x 2.1 m) in a steel frame on the front wall (Godot +z), leaf 45 mm
    behind the wall plane, lever handle, three hinges, stainless kick plate and threshold."""
    x0, x1, y0, y1, _, _ = room_bounds()
    dx0, dx1, top = _door_rect()
    cx = (dx0 + dx1) / 2
    yw = y0
    zb = float(floor_height(cx, yw)) - 0.002
    parts = []
    a = 0.05                                          # architrave face width
    proud = 0.012
    for (u0, u1, v0, v1) in ((dx0 - a, dx0, zb, top + a), (dx1, dx1 + a, zb, top + a), (dx0 - a, dx1 + a, top, top + a)):
        parts.append(box_mm((u0, yw - 0.002, v0), (u1, yw + proud, v1)))
    for (u0, u1, v0, v1) in ((dx0, dx0 + 0.012, zb, top), (dx1 - 0.012, dx1, zb, top), (dx0, dx1, top - 0.012, top)):
        parts.append(box_mm((u0, yw - 0.06, v0), (u1, yw, v1)))           # jamb reveals
    frame = k.obj("GBP_Room_DoorFrame", merge(*parts), "GBPM_room_door")
    k.bevel(frame, 0.002, 2, 30.0)
    leaf_y = yw - 0.045
    leaf = k.obj("GBP_Room_DoorLeaf", box_mm((dx0 + 0.012, leaf_y - 0.045, zb + 0.008), (dx1 - 0.012, leaf_y,
                                                                                       top - 0.012)), "GBPM_room_door")
    k.bevel(leaf, 0.003, 2, 30.0)
    hw = []
    hx = dx1 - 0.075
    hw.append(lathe([(leaf_y, 0.0), (leaf_y, 0.026), (leaf_y + 0.008, 0.024), (leaf_y + 0.010, 0.0)], 32, "y",
                    centre=(hx, 0.0, 1.05)))
    path = [(hx, leaf_y + 0.010, 1.05), (hx, leaf_y + 0.055, 1.05), (hx - 0.02, leaf_y + 0.07, 1.05),
            (hx - 0.13, leaf_y + 0.07, 1.05)]
    import gb_geom as gg
    V, F, _t = gg.sweep(path, 0.0095, sides=16, step=0.006)
    hw.append((V, F))
    for z in (zb + 0.25, zb + 1.05, top - 0.25):
        hw.append(lathe([(z - 0.05, 0.0), (z - 0.05, 0.008), (z + 0.05, 0.008), (z + 0.05, 0.0)], 16, "z",
                        centre=(dx0 + 0.016, leaf_y - 0.004, 0.0)))
    k.obj("GBP_Room_DoorHardware", merge(*hw), "GBPM_room_stainless")
    k.obj("GBP_Room_DoorKick", box_mm((dx0 + 0.03, leaf_y, zb + 0.02), (dx1 - 0.03, leaf_y + 0.0015, zb + 0.30)),
                 "GBPM_room_stainless")
    thr = k.obj("GBP_Room_Threshold", box_mm((dx0, yw - 0.09, zb - 0.004), (dx1, yw + 0.045, zb + 0.004)),
                "GBPM_room_stainless")
    k.bevel(thr, 0.002, 2, 30.0)
    return leaf


def build_table(k):
    """Stainless mortuary table 2.0 x 0.8 m, rim at 0.86 m: rolled-rim tray with a 45 mm basin
    falling to a foot-end drain, drain sink, pedestal column and base plate (plan §1.3)."""
    gx, gz = ROOM["table_g"]
    cx, cy = gx, -gz
    w, L = ROOM["table_size"]
    top = ROOM["table_top"]
    tray = k.obj("GBP_Room_Table", box_mm((cx - w / 2, cy - L / 2, top - 0.06), (cx + w / 2, cy + L / 2, top)),
                 "GBPM_room_stainless")
    k.boolean(tray, box_mm((cx - w / 2 + 0.03, cy - L / 2 + 0.03, top - 0.045), (cx + w / 2 - 0.03, cy + L / 2 - 0.03,
                                                                                  top + 0.05)))
    k.boolean(tray, lathe([(top - 0.08, 0.022), (top, 0.022)], 32, "z", centre=(cx, cy - L / 2 + 0.10, 0.0)))
    k.bevel(tray, 0.004, 3, 30.0)
    zf = float(floor_height(cx, cy)) - 0.004
    parts = [box_mm((cx - 0.09, cy - 0.20, zf + 0.02), (cx + 0.09, cy + 0.20, top - 0.06)),
             box_mm((cx - 0.35, cy - 0.40, zf), (cx + 0.35, cy + 0.40, zf + 0.022)),
             box_mm((cx - 0.20, cy - L / 2 + 0.03, top - 0.20), (cx + 0.20, cy - L / 2 + 0.25, top - 0.06))]
    ped = k.obj("GBP_Room_TableBase", merge(*parts), "GBPM_room_stainless")
    k.bevel(ped, 0.004, 2, 30.0)
    sink = lathe([(top - 0.20, 0.0), (top - 0.20, 0.02), (top - 0.35, 0.02), (top - 0.35, 0.0)], 20, "z",
                 centre=(cx, cy - L / 2 + 0.14, 0.0))
    k.obj("GBP_Room_TablePipe", sink, "GBPM_room_stainless")
    return tray


def build_trolley(k):
    """Stainless instrument trolley 0.6 x 0.45 m, two lipped shelves (top 0.86 m), tube legs, casters
    and a push handle.  Returns (object, top-shelf surface z)."""
    gx, gz = ROOM["trolley_g"]
    cx, cy = gx, -gz
    w, d = ROOM["trolley_size"]
    top = ROOM["trolley_top"]
    shelves = []
    for zt in (top, 0.30):
        s = box_mm((cx - w / 2, cy - d / 2, zt - 0.03), (cx + w / 2, cy + d / 2, zt))
        shelves.append(s)
    ob = k.obj("GBP_Room_Trolley", shelves[0], "GBPM_room_stainless")
    k.boolean(ob, box_mm((cx - w / 2 + 0.012, cy - d / 2 + 0.012, top - 0.026), (cx + w / 2 - 0.012, cy + d / 2 - 0.012,
                                                                                  top + 0.05)))
    k.bevel(ob, 0.002, 2, 30.0)
    low = k.obj("GBP_Room_TrolleyShelf", shelves[1], "GBPM_room_stainless")
    k.boolean(low, box_mm((cx - w / 2 + 0.012, cy - d / 2 + 0.012, 0.30 - 0.026), (cx + w / 2 - 0.012, cy + d / 2 - 0.012,
                                                                                  0.35)))
    k.bevel(low, 0.002, 2, 30.0)
    zf = float(floor_height(cx, cy))
    legs, cast = [], []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx, ly = cx + sx * (w / 2 - 0.02), cy + sy * (d / 2 - 0.02)
            legs.append(lathe([(zf + 0.105, 0.0), (zf + 0.105, 0.0125), (top - 0.002, 0.0125), (top - 0.002, 0.0)], 20,
                              "z", centre=(lx, ly, 0.0)))
            cast.append(box_mm((lx - 0.018, ly - 0.022, zf + 0.055), (lx + 0.018, ly + 0.022, zf + 0.105)))
            cast.append(lathe([(-0.011, 0.0), (-0.011, 0.038), (0.011, 0.038), (0.011, 0.0)], 24, "x",
                              centre=(lx, ly, zf + 0.04)))
    k.obj("GBP_Room_TrolleyLegs", merge(*legs), "GBPM_room_stainless")
    k.obj("GBP_Room_TrolleyCasters", merge(*cast), "GBPM_room_caster")
    import gb_geom as gg
    hx = cx + w / 2 + 0.035
    path = [(cx + w / 2 - 0.02, cy - 0.17, top - 0.01), (hx, cy - 0.17, top + 0.06), (hx, cy + 0.17, top + 0.06),
            (cx + w / 2 - 0.02, cy + 0.17, top - 0.01)]
    V, F, _t = gg.sweep(path, 0.011, sides=16, step=0.01)
    k.obj("GBP_Room_TrolleyHandle", (V, F), "GBPM_room_stainless")
    return ob, top - 0.026


def build_floor_mark(k):
    """Yellow tape cross (50 mm tape, 600 mm arms) at the subject mark, following the floor."""
    parts = []
    tw, L = 0.05, 0.60
    for axis in (0, 1):
        us = np.linspace(-L / 2, L / 2, 25)
        vs = np.array([-tw / 2, tw / 2])
        V, F = [], []
        for i, u in enumerate(us):
            for v in vs:
                x, y = (u, v) if axis == 0 else (v, u)
                V.append((x, y, float(floor_height(x, y)) + 0.0004 + 0.0001 * axis))
        for i in range(len(us) - 1):
            F.append([2 * i, 2 * i + 2, 2 * i + 3, 2 * i + 1])
        parts.append((np.array(V), F))
    ob = k.obj("GBP_Room_FloorMark", merge(*parts), "GBPM_room_tape", recalc=False, smooth=False)
    _face_toward(ob, (0, 0, 1))
    return ob


def build_scale_bar(k):
    """1 m forensic scale bar on the left wall (Godot x = -3): white bar, black 10 / 50 / 100 mm ticks
    and cm numerals as printed geometry; zero at the left end seen from the room."""
    x0 = room_bounds()[0]
    g = ROOM["scale_bar_g"]
    zc, yc = g[1], -g[2]
    xb0, xb1 = x0 + 0.001, x0 + 0.004
    bar = k.obj("GBP_Room_ScaleBar", box_mm((xb0, yc - 0.52, zc - 0.03), (xb1, yc + 0.52, zc + 0.03)),
                "GBPM_ruler_white")
    k.bevel(bar, 0.0008, 2, 30.0)
    xp = xb1 + 0.00008
    marks = []
    for i in range(101):
        L = 0.018 if i % 10 == 0 else (0.012 if i % 5 == 0 else 0.008)
        y = yc - 0.5 + i * 0.01
        marks.append((np.array([(xp, y - 0.0005, zc + 0.03 - L), (xp, y + 0.0005, zc + 0.03 - L),
                                (xp, y + 0.0005, zc + 0.03), (xp, y - 0.0005, zc + 0.03)]), [[0, 1, 2, 3]]))
    for c in range(0, 11):
        tv, tf = text_part(str(c * 10), 0.012)
        marks.append((np.column_stack([np.full(len(tv), xp), yc - 0.5 + c * 0.1 + tv[:, 0], zc - 0.006 + tv[:, 1]]), tf))
    tv, tf = text_part("cm", 0.009)
    marks.append((np.column_stack([np.full(len(tv), xp), yc + 0.47 + tv[:, 0], zc - 0.021 + tv[:, 1]]), tf))
    pr = k.obj("GBP_Room_ScaleBarPrint", merge(*marks), "GBPM_print_black", recalc=False, smooth=False)
    _face_toward(pr, (1, 0, 0))
    return bar


def _rest_transform(kit, R):
    """Root transform that lays item ``kit`` on a surface: rotation ``R`` (3x3) and the offset that puts
    the rotated bounding box's lowest point at z = 0 and its footprint centre at (0, 0)."""
    pts = []
    for o in kit.objects.values():
        if o.name.endswith("_Flame"):
            continue
        V = np.array([v.co[:] for v in o.data.vertices])
        pts.append(V @ np.asarray(R).T)
    P = np.vstack(pts)
    lo, hi = P.min(0), P.max(0)
    return -np.array([(lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]])


def build_room_markers(k, drain_h, tray_z):
    """Markers for the game: subject mark, player spawn, lights, reflection probe, drain, backstop,
    table, trolley, door, scale-bar zero and resting spots for every tool (item root transforms)."""
    x0, x1, y0, y1, _, z1 = room_bounds()
    k.marker("GBP_room_subject_mark", (0, 0, 0), fwd=(0, -1, 0), kind="subject_mark")
    sp = ROOM["player_spawn_g"]
    k.marker("GBP_room_player_spawn", (sp[0], -sp[2], float(floor_height(sp[0], -sp[2]))), fwd=(0, 1, 0),
             kind="player_spawn")
    kl, kt = ROOM["key_light_g"], ROOM["key_target_g"]
    kpos = np.array([kl[0], -kl[2], kl[1]])
    ktgt = np.array([kt[0], -kt[2], kt[1]])
    k.marker("GBP_room_light_key", tuple(kpos), fwd=tuple(ktgt - kpos), up=(0, 1, 0), kind="light_key")
    for i, pz in enumerate(ROOM["panel_z"]):
        k.marker(f"GBP_room_light_panel_{i}", (0.0, -pz, z1 - 0.01), fwd=(0, 0, -1), up=(0, 1, 0), kind="light_panel")
    e = k.marker("GBP_room_probe", ((x0 + x1) / 2, (y0 + y1) / 2, z1 / 2), kind="reflection_probe")
    e["gbp_extents_godot"] = [x1 - x0, z1, y1 - y0]
    c = drain_xy()
    k.marker("GBP_room_drain", (c[0], c[1], drain_h), fwd=(0, 0, -1), up=(0, 1, 0), kind="drain")
    bw, bh, bd = ROOM["backstop_size"]
    e = k.marker("GBP_room_backstop", (0.0, -ROOM["backstop_front_z"], 0.01 + bh / 2), fwd=(0, -1, 0), kind="backstop")
    e["gbp_size_m"] = list(ROOM["backstop_size"])
    gx, gz = ROOM["table_g"]
    k.marker("GBP_room_table", (gx, -gz, ROOM["table_top"] - 0.045), kind="table")
    tx, tz = ROOM["trolley_g"]
    k.marker("GBP_room_trolley", (tx, -tz, tray_z), kind="trolley")
    dx0, dx1, _ = _door_rect()
    k.marker("GBP_room_door", ((dx0 + dx1) / 2, y0, 1.05), fwd=(0, 1, 0), kind="door")
    g = ROOM["scale_bar_g"]
    k.marker("GBP_room_scale_bar", (x0 + 0.0041, -g[2] - 0.5, g[1] + 0.03), fwd=(0, 1, 0), up=(1, 0, 0),
             kind="scale_bar_zero")
    # tool resting spots (root transform of each item lying on the trolley / table)
    low_z = 0.30 - 0.026
    side = rot("z", -90) @ rot("y", 90)            # length along +X, lying on its (right) side
    spots = {  # item: (surface centre x, y, z, R); small tools on the top shelf, long ones below
        "pistol": (tx - 0.155, -tz - 0.10, tray_z, side),
        "knife": (tx + 0.14, -tz - 0.15, tray_z, side),
        "thermometer": (tx + 0.13, -tz - 0.06, tray_z, rot("z", -90)),
        "penlight": (tx - 0.14, -tz + 0.05, tray_z, rot("z", -90)),
        "ruler": (tx + 0.17, -tz + 0.10, tray_z, np.eye(3)),
        "torch": (tx + 0.0, -tz - 0.09, low_z, rot("z", -90)),
        "hammer": (tx + 0.0, -tz + 0.11, low_z, rot("y", 90)),
        "shotgun": (gx - 0.18, -gz, ROOM["table_top"] - 0.045, rot("y", 90)),
        "fist": None,
    }
    for item, spec in spots.items():
        if spec is None or item not in KITS:
            continue
        sx, sy, sz, R = spec
        off = _rest_transform(KITS[item], R)
        pos = np.array([sx, sy, sz]) + off
        fwd = np.asarray(R) @ np.array([0.0, 1.0, 0.0])
        up = np.asarray(R) @ np.array([0.0, 0.0, 1.0])
        k.marker(f"GBP_room_tool_{item}", tuple(pos), fwd=tuple(fwd), up=tuple(up), kind="tool_spot")


def build_collision(k):
    """Collision-only meshes for Godot's glTF importer (``-colonly`` = trimesh static body,
    ``-convcolonly`` = convex).  Walls/ceiling are 0.2 m slabs outside the interior planes."""
    x0, x1, y0, y1, z0, z1 = room_bounds()
    t = 0.2
    boxes = {
        "GBP_room_col_wall_back-convcolonly": ((x0 - t, y1, -t), (x1 + t, y1 + t, z1 + t)),
        "GBP_room_col_wall_front-convcolonly": ((x0 - t, y0 - t, -t), (x1 + t, y0, z1 + t)),
        "GBP_room_col_wall_left-convcolonly": ((x0 - t, y0 - t, -t), (x0, y1 + t, z1 + t)),
        "GBP_room_col_wall_right-convcolonly": ((x1, y0 - t, -t), (x1 + t, y1 + t, z1 + t)),
        "GBP_room_col_ceiling-convcolonly": ((x0 - t, y0 - t, z1), (x1 + t, y1 + t, z1 + t)),
    }
    bw, bh, bd = ROOM["backstop_size"]
    yf = -ROOM["backstop_front_z"]
    boxes["GBP_room_col_backstop-convcolonly"] = ((-bw / 2, yf, 0.0), (bw / 2, yf + bd, 0.01 + bh))
    gx, gz = ROOM["table_g"]
    w, L = ROOM["table_size"]
    boxes["GBP_room_col_table-convcolonly"] = ((gx - w / 2, -gz - L / 2, ROOM["table_top"] - 0.06),
                                               (gx + w / 2, -gz + L / 2, ROOM["table_top"]))
    boxes["GBP_room_col_table_base-convcolonly"] = ((gx - 0.35, -gz - 0.40, 0.0), (gx + 0.35, -gz + 0.40,
                                                                                 ROOM["table_top"] - 0.06))
    tx, tz = ROOM["trolley_g"]
    tw, td = ROOM["trolley_size"]
    boxes["GBP_room_col_trolley-convcolonly"] = ((tx - tw / 2, -tz - td / 2, 0.0),
                                                 (tx + tw / 2 + 0.05, -tz + td / 2, ROOM["trolley_top"] + 0.07))
    out = []
    for name, (lo, hi) in boxes.items():
        ob = k.obj(name, box_mm(lo, hi), None, smooth=False)
        ob["gbp_collision"] = True
        ob.hide_render = True
        ob.display_type = 'WIRE'
        out.append(ob)
    # floor: coarse copy of the sloped floor surface (trimesh)
    b = _perimeter(x0, x1, y0, y1, 0.5)
    c = drain_xy()
    V = [(c[0], c[1], float(floor_height(*c)))]
    rings = []
    for t_ in (0.25, 0.5, 1.0):
        ring = []
        for p in b:
            q = c + (p - c) * t_
            ring.append(len(V))
            V.append((q[0], q[1], float(floor_height(q[0], q[1]))))
        rings.append(ring)
    F = [[0, rings[0][i], rings[0][(i + 1) % len(b)]] for i in range(len(b))]
    for r0, r1 in zip(rings[:-1], rings[1:]):
        F += [[r0[i], r1[i], r1[(i + 1) % len(b)], r0[(i + 1) % len(b)]] for i in range(len(b))]
    fl = k.obj("GBP_room_col_floor-colonly", (np.array(V), F), None, recalc=False, smooth=False)
    _face_toward(fl, (0, 0, 1))
    fl["gbp_collision"] = True
    fl.hide_render = True
    fl.display_type = 'WIRE'
    out.append(fl)
    return out


def build_room(quick=False):
    """Build the forensic room into ``GBP_Room``; returns ``{name: object}`` (root + meshes + markers)."""
    cols = prop_collections()
    t0 = time.perf_counter()
    k = Kit("GBP_Room", cols[COL_ROOM], origin=(0.0, 0.0, 0.0), unit=1.0, kind="room")
    build_floor(k, quick)
    _, drain_h = build_drain(k)
    build_walls(k, quick)
    build_ceiling(k)
    build_backstop(k, quick)
    build_door(k)
    build_table(k)
    _, tray_z = build_trolley(k)
    build_floor_mark(k)
    build_scale_bar(k)
    build_room_markers(k, drain_h, tray_z)
    cols_ = build_collision(k)
    cols_ = set(cols_)
    uv_done = {"GBP_Room_Floor", "GBP_Room_Tiles", "GBP_Room_Grout", "GBP_Room_Ceiling", "GBP_Room_LightPanels",
               "GBP_Room_Backstop"}
    for name, ob in k.objects.items():
        if ob in cols_:
            ob["gb_layer"] = "collision"
            continue
        finish_mesh(ob, sharp=20.0 if name == "GBP_Room_Tiles" else 35.0, uv=name not in uv_done)
    KITS["room"] = k
    gbc.log(f"props: room         {len(k.objects):2d} meshes {sum(len(o.data.polygons) for o in k.objects.values()):6d} "
            f"faces {len(k.markers):2d} markers  {time.perf_counter() - t0:5.1f} s")
    out = {"GBP_Room": k.root}
    out.update(k.objects)
    out.update(k.markers)
    return out


# ===========================================================================
# Measurements, JSON sidecars, export
# ===========================================================================
def item_verts(kit, names=None, skip_flame=True):
    """Vertices (item frame, item unit) of the kit's meshes (optionally only ``names``)."""
    pts = []
    for n, o in kit.objects.items():
        if names is not None and n not in names:
            continue
        if skip_flame and n.endswith("_Flame"):
            continue
        V = np.array([v.co[:] for v in o.data.vertices])
        if len(V):
            pts.append(V / kit.unit + kit.origin)
    return np.vstack(pts)


def _extent(P, i):
    return float(P[:, i].max() - P[:, i].min())


def mesh_volume(ob):
    """Closed-mesh volume in m^3 (bmesh signed volume)."""
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    v = abs(bm.calc_volume(signed=True))
    bm.free()
    return v


def measure_props():
    """Critical dimensions measured on the built meshes (mm, kg) - compared with ``SPEC`` by verify.py."""
    out = {}
    if "pistol" in KITS:
        k = KITS["pistol"]
        A = item_verts(k)
        B = item_verts(k, ["GBP_Pistol_Barrel"])
        r = np.hypot(B[:, 0], B[:, 2])
        bore = B[(B[:, 1] > 125.0) & (r < 4.7)]
        out["pistol"] = {"bore_d": 2 * float(np.hypot(bore[:, 0], bore[:, 2]).max()),
                         "overall_length": _extent(A, 1), "height": _extent(A, 2),
                         "slide_width": _extent(item_verts(k, ["GBP_Pistol_Slide"]), 0),
                         "grip_width": _extent(_below(item_verts(k, ["GBP_Pistol_Frame"]), -60.0), 0),
                         "barrel_length": _extent(B, 1)}
    if "shotgun" in KITS:
        k = KITS["shotgun"]
        A = item_verts(k)
        B = item_verts(k, ["GBP_Shotgun_Barrel"])
        r = np.hypot(B[:, 0], B[:, 2])
        R = item_verts(k, ["GBP_Shotgun_Receiver"])
        out["shotgun"] = {"bore_d": 2 * float(r[(B[:, 1] > 221.0) & (r < 9.5)].max()),
                          "barrel_length": float(B[:, 1].max() - R[:, 1].max()),
                          "overall_length": _extent(A, 1),
                          "barrel_od_muzzle": 2 * float(r[(B[:, 1] > 660.0) & (B[:, 1] < 672.0)].max())}
    if "knife" in KITS:
        k = KITS["knife"]
        Bl = item_verts(k, ["GBP_Knife_Blade"])
        widths = []
        for y in np.arange(1.0, 119.0, 1.0):
            sel = Bl[np.abs(Bl[:, 1] - y) < 0.51]
            if len(sel):
                widths.append(_extent(sel, 2))
        out["knife"] = {"blade_length": _extent(Bl, 1), "blade_width": float(max(widths)),
                        "spine_thickness": _extent(Bl, 0), "overall_length": _extent(item_verts(k), 1)}
    if "hammer" in KITS:
        k = KITS["hammer"]
        H = item_verts(k, ["GBP_Hammer_Head"])
        face = H[H[:, 1] > 50.0]
        out["hammer"] = {"face_d": 2 * float(np.hypot(face[:, 0], face[:, 2] - HAMMER_ZH).max()),
                         "overall_length": _extent(item_verts(k), 2), "head_length": _extent(H, 1),
                         "head_mass_kg": mesh_volume(k.objects["GBP_Hammer_Head"]) * 7850.0}
    if "torch" in KITS:
        k = KITS["torch"]
        C = item_verts(k, ["GBP_Torch_Cylinder"])
        T = item_verts(k, ["GBP_Torch_Tube"])
        Fl = item_verts(k, ["GBP_Torch_Flame"], skip_flame=False)
        out["torch"] = {"cylinder_d": 2 * float(np.hypot(C[:, 0], C[:, 2]).max()),
                        "tube_d": 2 * float(np.hypot(T[:, 0], T[:, 2])[(T[:, 1] > 300) & (T[:, 1] < 425)].max()),
                        "flame_length": _extent(Fl, 1), "overall_length": _extent(item_verts(k), 1)}
    if "fist" in KITS:
        G = item_verts(KITS["fist"])
        out["fist"] = {"knuckle_width": _extent(G[G[:, 1] > -12.0], 0)}
    if "ruler" in KITS:
        k = KITS["ruler"]
        Bd = item_verts(k, ["GBP_Ruler_Body"])
        Pr = item_verts(k, ["GBP_Ruler_Print"])
        long_ticks = Pr[(np.abs(Pr[:, 0] - 18.0) < 1e-4) & (Pr[:, 1] > 24.0)]
        ys = np.unique(np.round((long_ticks[:, 1]), 4))
        centres = np.array([(a + b) / 2 for a, b in zip(ys[0::2], ys[1::2])])
        out["ruler"] = {"arm_length": _extent(Bd, 0), "arm_width": float(Bd[Bd[:, 0] > 60.0][:, 1].max() - Bd[:, 1].min()),
                        "cm_tick_pitch": float(np.mean(np.diff(centres))) if len(centres) > 1 else 0.0,
                        "scale_length": float(centres[-1] - centres[0]) if len(centres) > 1 else 0.0}
    if "penlight" in KITS:
        k = KITS["penlight"]
        Bd = item_verts(k, ["GBP_Penlight_Body"])
        out["penlight"] = {"diameter": _extent(Bd, 0), "length": _extent(item_verts(k, ["GBP_Penlight_Body",
                                                                                         "GBP_Penlight_Button"]), 1)}
    if "thermometer" in KITS:
        k = KITS["thermometer"]
        P = item_verts(k, ["GBP_Thermometer_Probe"])
        pr = P[(np.hypot(P[:, 0], P[:, 2]) <= SPEC["thermometer"]["probe_d"] / 2 + 1e-3) & (P[:, 1] > 37.0)]
        out["thermometer"] = {"probe_d": 2 * float(np.hypot(pr[:, 0], pr[:, 2]).max()),
                              "probe_length": _extent(pr, 1)}
    return out


def _below(P, z):
    return P[P[:, 2] < z]


def spec_check(measured=None):
    """Compare ``measure_props()`` with ``SPEC``.  Returns (ok, list of problems, table)."""
    m = measured or measure_props()
    probs, table = [], {}
    for item, spec in SPEC.items():
        if item not in m:
            probs.append(f"{item} not built")
            continue
        for key, want in spec.items():
            got = m[item].get(key)
            if got is None:
                probs.append(f"{item}.{key} not measured")
                continue
            if isinstance(want, tuple):
                ok = want[0] <= got <= want[1]
            else:
                tol = 0.05 if key.endswith("bore_d") or key in ("probe_d", "cm_tick_pitch") else 1.0
                ok = abs(got - want) <= tol
            table[f"{item}.{key}"] = (round(got, 3), want, ok)
            if not ok:
                probs.append(f"{item}.{key} = {got:.3f} (spec {want})")
    return not probs, probs, table


def _g(v):
    return [float(a) for a in gbc.b2g(np.asarray(v, float))]


def marker_table(kit):
    """{marker: {kind, pos, fwd, up}} in Godot axes, relative to the item root (metres)."""
    out = {}
    for n, e in kit.markers.items():
        M = e.matrix_world
        out[n] = {"kind": e.get("gbp_marker", ""), "pos": _g(M.translation[:]),
                  "fwd": _g(M.to_3x3().col[1][:]), "up": _g(M.to_3x3().col[2][:])}
        for key in ("gbp_extents_godot", "gbp_size_m"):
            if key in e:
                out[n][key.replace("gbp_", "")] = list(e[key])
    return out


def materials_table(names):
    out = {}
    for n in sorted(names):
        hexc, metal, rough, ex = MATS[n]
        out[n] = {"base_color": hexc, "metallic": metal, "roughness": rough,
                  "absorbent": bool(ex.get("absorbent", False))}
        if "emission" in ex:
            out[n]["emission"] = list(ex["emission"])
        if "alpha" in ex:
            out[n]["alpha"] = ex["alpha"]
    return out


def _used_materials(kits):
    names = set()
    for k in kits:
        for o in k.objects.values():
            names |= {m.name for m in o.data.materials if m is not None}
    return names


def props_data(measured):
    items, markers = {}, {}
    for name, _fn in WEAPON_BUILDERS:
        k = KITS[name]
        items[name] = {"root": k.root.name, "meshes": sorted(k.objects), "spec": SPEC[name],
                       "measured": measured.get(name, {}),
                       "triangles": int(sum(sum(len(p.vertices) - 2 for p in o.data.polygons)
                                            for o in k.objects.values())),
                       "extras": {kk: (list(v) if hasattr(v, "__len__") and not isinstance(v, str) else v)
                                  for kk, v in k.root.items() if kk.startswith("gbp_")}}
        for mn, rec in marker_table(k).items():
            rec["item"] = name
            markers[mn] = rec
    conv = {"units": "metres; item root origin = grip / hand point",
            "axes": "Godot: item forward = -Z (authored +Y in Blender), up = +Y",
            "markers": "marker forward (-basis.z in Godot, 'fwd' here) = action direction: bullet path, "
                       "blade-edge outward normal, strike direction, flame axis, beam; 'up' = reference up",
            "muzzles": "GBP_muzzle_pistol / GBP_muzzle_shotgun (plan §5.7 'GBP_muzzle'; unique names per file)",
            "moving_parts": "GBP_Pistol_Slide/Trigger, GBP_Shotgun_Forend/Trigger, GBP_Torch_Flame (toggle)"}
    return {"items": items, "markers": markers, "materials": materials_table(_used_materials(
        [KITS[n] for n, _ in WEAPON_BUILDERS])), "conventions": conv}


def room_data():
    x0, x1, y0, y1, z0, z1 = room_bounds()
    k = KITS["room"]
    gx, gz = ROOM["table_g"]
    tx, tz = ROOM["trolley_g"]
    godot = {
        "interior": {"x": [x0, x1], "y": [0.0, z1], "z": list(ROOM["z"])},
        "wall_planes": {"x_min": x0, "x_max": x1, "z_min": ROOM["z"][0], "z_max": ROOM["z"][1], "ceiling_y": z1},
        "floor": {"fall": ROOM["floor_fall"], "drain": list(ROOM["drain_g"]), "drain_d": ROOM["drain_d"],
                  "material": "epoxy", "cove_r": ROOM["cove_r"], "cove_top": ROOM["cove_top"]},
        "tiles": {"size": ROOM["tile"], "grout": ROOM["grout"], "relief": ROOM["tile_relief"],
                  "pitch": ROOM["tile"] + ROOM["grout"], "first_row_y": ROOM["cove_top"] + ROOM["grout"]},
        "backstop": {"front_z": ROOM["backstop_front_z"], "size": list(ROOM["backstop_size"]),
                     "center": [0.0, 0.01 + ROOM["backstop_size"][1] / 2, ROOM["backstop_front_z"] -
                                ROOM["backstop_size"][2] / 2]},
        "panels": [{"center": [0.0, z1 - 0.008, pz], "size": list(ROOM["panel_size"])} for pz in ROOM["panel_z"]],
        "key_light": {"pos": list(ROOM["key_light_g"]), "target": list(ROOM["key_target_g"]),
                      "color": "#FFE4CE", "kelvin": 5000},
        "player": {"spawn": list(ROOM["player_spawn_g"]), "eye_standing": ROOM["player_eye"][0],
                   "eye_kneeling": ROOM["player_eye"][1], "facing": [0.0, 0.0, -1.0]},
        "table": {"center_xz": [gx, gz], "size_xz": list(ROOM["table_size"]), "top_y": ROOM["table_top"]},
        "trolley": {"center_xz": [tx, tz], "size_xz": list(ROOM["trolley_size"]), "top_y": ROOM["trolley_top"]},
        "door": {"center": list(ROOM["door_g"]), "size": list(ROOM["door_size"])},
        "scale_bar": {"zero": [x0 + 0.0041, ROOM["scale_bar_g"][1] + 0.03, ROOM["scale_bar_g"][2] - 0.5],
                      "direction": [0.0, 0.0, 1.0], "length": 1.0},
        "subject_mark": [0.0, 0.0, 0.0],
    }
    body = {"interior": [x0, x1, y0, y1, z0, z1], "drain_xy": [float(a) for a in drain_xy()],
            "backstop_front_y": -ROOM["backstop_front_z"]}
    col = {}
    for n, o in k.objects.items():
        if o.get("gbp_collision"):
            V = np.array([v.co[:] for v in o.data.vertices])
            G = np.array([gbc.b2g(v) for v in V])
            col[n] = {"min": [float(a) for a in G.min(0)], "max": [float(a) for a in G.max(0)],
                      "shape": "trimesh" if n.endswith("-colonly") else "convex"}
    return {"godot": godot, "body": body, "markers": marker_table(k),
            "materials": materials_table(_used_materials([k])), "collision": col,
            "floor_height": {"formula": "y = fall * (hypot(x - drain.x, z - drain.z) - hypot(drain.x, drain.z))",
                             "fall": ROOM["floor_fall"], "drain_xz": [ROOM["drain_g"][0], ROOM["drain_g"][2]],
                             "value_at_origin": 0.0}}


GLTF_PROPS = dict(export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
                  export_texcoords=True, export_normals=True, export_tangents=True,
                  export_materials='EXPORT', export_image_format='NONE', export_vertex_color='NONE',
                  export_attributes=False, export_extras=True, export_skins=False, export_morph=False,
                  export_animations=False, export_lights=False, export_cameras=False)


def _export_glb(path, objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.gltf(filepath=path, **GLTF_PROPS)
    for o in objs:
        o.select_set(False)
    return path


def export_props(out=gbc.PROPS_OUT, quick=False, hide_after=True):
    """Build (if needed) and export weapons.glb, room.glb, props.json and room.json into ``out``."""
    os.makedirs(out, exist_ok=True)
    if not all(n in KITS for n, _ in WEAPON_BUILDERS):
        build_weapons(quick)
    if "room" not in KITS:
        build_room(quick)
    cols = prop_collections()
    for c in (cols[COL_WEAPONS], cols[COL_ROOM]):
        _layer_col(c).exclude = False
    paths = {}
    with gbc.Timer("props: export weapons.glb", quiet=True):
        paths["weapons"] = _export_glb(os.path.join(out, WEAPONS_GLB), list(cols[COL_WEAPONS].objects))
    with gbc.Timer("props: export room.glb", quiet=True):
        paths["room"] = _export_glb(os.path.join(out, ROOM_GLB), list(cols[COL_ROOM].objects))
    measured = measure_props()
    paths["props_json"] = gbc.write_json(os.path.join(out, PROPS_JSON), props_data(measured), "gb.props/1")
    paths["room_json"] = gbc.write_json(os.path.join(out, ROOM_JSON), room_data(), "gb.room/1")
    ok, probs, _t = spec_check(measured)
    gbc.log(f"props: exported {', '.join(os.path.basename(p) for p in paths.values())}; "
            f"critical dimensions {'OK' if ok else 'FAIL ' + str(probs)}")
    if hide_after:                         # keep subject renders (outside the room) unobstructed
        _layer_col(cols[ROOT_COL]).exclude = True
    return paths


def _layer_col(col):
    def walk(lc):
        if lc.collection == col:
            return lc
        for ch in lc.children:
            r = walk(ch)
            if r is not None:
                return r
        return None
    return walk(bpy.context.view_layer.layer_collection)


def _room_lights(on=True):
    """Render-only lights matching plan §1.3: two panel area lights + the key spot (Godot uses its own)."""
    x0, x1, y0, y1, _, z1 = room_bounds()
    made = []
    for i, pz in enumerate(ROOM["panel_z"]):
        data = bpy.data.lights.get(f"GBP_RoomPanel_{i}") or bpy.data.lights.new(f"GBP_RoomPanel_{i}", 'AREA')
        data.shape = 'RECTANGLE'
        data.size, data.size_y = ROOM["panel_size"]
        data.energy = 170.0
        data.color = (1.0, 0.9, 0.82)
        ob = bpy.data.objects.get(data.name) or bpy.data.objects.new(data.name, data)
        if ob.name not in _stage_col().objects:
            _stage_col().objects.link(ob)
        ob.location = (0.0, -pz, z1 - 0.012)
        ob.rotation_euler = (0.0, 0.0, 0.0)
        made.append(ob)
    kl, kt = ROOM["key_light_g"], ROOM["key_target_g"]
    data = bpy.data.lights.get("GBP_RoomKey") or bpy.data.lights.new("GBP_RoomKey", 'SPOT')
    data.energy = 110.0
    data.spot_size = math.radians(70.0)
    data.spot_blend = 0.6
    data.shadow_soft_size = 0.08
    data.color = (1.0, 0.9, 0.82)
    ob = bpy.data.objects.get("GBP_RoomKey") or bpy.data.objects.new("GBP_RoomKey", data)
    if ob.name not in _stage_col().objects:
        _stage_col().objects.link(ob)
    ob.location = (kl[0], -kl[2], kl[1])
    gbc.look_at(ob, (kt[0], -kt[2], kt[1]))
    made.append(ob)
    for o in made:
        o.hide_render = not on
    scene = bpy.context.scene
    world = bpy.data.worlds.get("GBP_World") or bpy.data.worlds.new("GBP_World")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.01, 0.01, 0.01, 1.0)
    scene.world = world
    scene.view_settings.view_transform = 'AgX'
    return made


ROOM_VIEWS = {
    # name: (camera location, target, lens) in the body frame
    "player": ((0.0, -3.0, 1.65), (0.0, 0.0, 1.15), 24.0),
    "corner": ((-2.7, -4.1, 2.55), (0.4, 0.2, 0.9), 18.0),
    "backstop": ((0.55, -0.9, 1.25), (0.0, 1.3, 1.25), 40.0),
    "tiles_grazing": ((2.93, -0.2, 1.35), (2.99, 0.4, 1.33), 50.0),
    "drain": ((0.35, -1.45, 0.45), (0.0, -1.0, 0.0), 45.0),
    "trolley": ((-1.35, -1.45, 1.45), (-2.3, -2.3, 0.86), 35.0),
    "table": ((1.3, -2.9, 1.7), (2.4, -1.2, 0.85), 26.0),
    "door": ((0.4, -1.8, 1.4), (-1.9, -4.4, 1.05), 28.0),
    "scale_bar": ((-2.1, 0.0, 1.45), (-3.0, 0.0, 1.45), 35.0),
}


def place_tools(on=True):
    """Move every item root to its room resting spot (``GBP_room_tool_*``) or back to the origin."""
    for name, k in KITS.items():
        if name == "room":
            continue
        m = bpy.data.objects.get(f"GBP_room_tool_{name}")
        k.root.matrix_world = m.matrix_world.copy() if (on and m is not None) else Matrix.Identity(4)
        for o in k.objects.values():
            if o.name.endswith("_Flame") or m is None:
                o.hide_render = on
    bpy.context.view_layer.update()


def render_room(views=None, samples=32, res=(640, 400), out_dir=gbc.RENDER_DIR, prefix="props_room"):
    """Render the room from ``ROOM_VIEWS`` with the tools laid out; returns the paths."""
    cols = prop_collections()
    for c in (cols[ROOT_COL], cols[COL_WEAPONS], cols[COL_ROOM], cols[COL_STAGE]):
        _layer_col(c).exclude = False
    studio(False)
    _room_lights(True)
    place_tools(True)
    paths = []
    for v in views or ROOM_VIEWS:
        loc, tgt, lens = ROOM_VIEWS[v]
        cam = gbc.add_camera("GBP_RoomCam", loc, tgt, lens)
        gbc.link(cam, _stage_col())
        cam.data.clip_start = 0.01
        paths.append(gbc.render(os.path.join(out_dir, f"{prefix}_{v}.png"), cam, samples, res))
    place_tools(False)
    _room_lights(False)
    return paths


ITEM_VIEWS = {
    # item: [(view name, camera direction, optional (focus point in item mm, frame width in mm))]
    "pistol": [("side_r", (1.0, 0.0, 0.05)), ("side_l", (-1.0, 0.0, 0.08)), ("tq", (-0.8, 0.9, 0.45)),
               ("muzzle", (-0.35, 1.0, 0.2), ((0.0, 186.0, -4.0), 62.0)),
               ("port", (0.9, 0.25, 0.7), ((5.0, 95.0, 5.0), 90.0))],
    "shotgun": [("side_r", (1.0, 0.0, 0.05)), ("tq", (-0.8, 0.9, 0.45)),
                ("muzzle", (-0.35, 1.0, 0.25), ((0.0, 675.0, -10.0), 75.0)),
                ("action", (0.9, 0.3, 0.35), ((0.0, 110.0, -25.0), 280.0))],
    "knife": [("side", (1.0, 0.0, 0.05)), ("tq", (-0.8, 0.9, 0.45)),
              ("edge", (0.8, 0.5, 0.1), ((0.0, 92.0, -9.0), 60.0)),
              ("spine", (0.5, -0.3, 0.8), ((0.0, 30.0, 5.0), 70.0))],
    "hammer": [("side", (1.0, 0.0, 0.05)), ("tq", (-0.8, 0.9, 0.45)),
               ("face", (0.35, 1.0, 0.25), ((0.0, 50.0, 300.0), 75.0)),
               ("claw", (-0.7, -1.0, 0.45), ((0.0, -55.0, 285.0), 80.0))],
    "torch": [("side", (1.0, 0.0, 0.05)), ("tq", (-0.8, 0.9, 0.45)),
              ("nozzle", (-0.5, 1.0, 0.35), ((0.0, 445.0, 0.0), 120.0)),
              ("valve", (0.8, 0.4, 0.5), ((5.0, 300.0, 0.0), 110.0))],
    "fist": [("tq", (-0.8, 0.9, 0.45)), ("front", (-0.1, 1.0, 0.2)), ("side", (1.0, 0.0, 0.1)),
             ("thumb", (-1.0, 0.25, 0.05))],
    "ruler": [("top", (0.0, -0.2, 1.0)), ("tq", (-0.6, -0.8, 0.9)),
              ("scale", (0.1, -0.3, 1.0), ((25.0, 40.0, 1.2), 45.0))],
    "penlight": [("tq", (-0.8, 0.9, 0.45)), ("lens", (-0.3, 1.0, 0.2), ((0.0, 69.0, 0.0), 30.0))],
    "thermometer": [("tq", (-0.8, 0.9, 0.55)), ("top", (0.0, -0.05, 1.0))],
}


def render_items(samples=32, out_dir=gbc.RENDER_DIR, only=None):
    """Studio renders of every item (``renders/props_<item>_<view>.png``)."""
    cols = prop_collections()
    for c in (cols[ROOT_COL], cols[COL_WEAPONS], cols[COL_STAGE]):
        _layer_col(c).exclude = False
    _layer_col(cols[COL_ROOM]).exclude = True
    _room_lights(False)
    paths = []
    for name, views in ITEM_VIEWS.items():
        if name not in KITS or (only and name not in only):
            continue
        others = [KITS[n].root for n in KITS if n not in (name, "room")]
        for o in others:
            for c in [o] + list(o.children_recursive):
                c.hide_render = True
        k = KITS[name]
        for v in views:
            res = (640, 420) if name in ("shotgun", "pistol", "knife", "torch", "hammer") else (560, 480)
            focus = span = None
            if len(v) > 2:
                focus = (np.asarray(v[2][0], float) - k.origin) * k.unit
                span = v[2][1] * k.unit
                res = (560, 420)
            paths.append(render_item(k.root, os.path.join(out_dir, f"props_{name}_{v[0]}.png"), view=v[1],
                                     res=res, samples=samples, focus=focus, span=span))
        for o in others:
            for c in [o] + list(o.children_recursive):
                c.hide_render = False
    studio(False)
    return paths


def main():
    args = gbc.script_args()
    quick = "--quick" in args
    gbc.reset_scene()
    t0 = time.perf_counter()
    build_weapons(quick)
    build_room(quick)
    gbc.log(f"props built in {time.perf_counter() - t0:.1f} s")
    ok, probs, table = spec_check()
    for key, (got, want, good) in table.items():
        print(f"  {'OK ' if good else 'BAD'} {key:32s} {got:10.3f}  spec {want}")
    if "--no-export" not in args:
        export_props(gbc.PROPS_OUT, quick, hide_after=False)
    s = 16 if quick else 32
    if "--render" in args:
        render_items(s)
        render_room(samples=s)
    if "--render-items" in args:
        render_items(s, only=args[args.index("--render-items") + 1].split(","))
    if "--render-room" in args:
        v = args[args.index("--render-room") + 1]
        render_room(views=None if v == "all" else v.split(","), samples=s)
    if "--save" in args:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.join(os.path.dirname(gbc.BLEND_PATH), "props_test.blend"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
