"""Procedural materials for the gore head (Blender 5.x).

Every material is built from Blender's procedural shader nodes only (noise,
Voronoi, gradients, maths): no image textures, no downloads.  All textures are
driven by *object* coordinates in metres, so feature sizes are physical
(pores ~0.45 mm, muscle fibres ~0.4 mm, fat lobules ~1.5-4 mm) and nothing
needs UVs.

Public API (see CONTRACT.md):

* ``build_materials() -> dict[str, bpy.types.Material]`` builds (or rebuilds in
  place) GH_Skin, GH_Lips, GH_Muscle, GH_Fat, GH_Bone, GH_Brain, GH_Blood,
  GH_Eye, GH_Teeth, GH_Gums, GH_Tongue, GH_MouthInterior.
* ``assign_materials(objs, mats)`` puts them on the anatomy objects
  (OBJECT_MATERIALS); missing objects are skipped.

Shared building blocks are shader node groups, so a tissue looks the same
wherever it appears (skin wound rings, the muscle layer, the fat wall ...):

=================  =========================================================
``GHS_BloodFilm``  wet/dried blood over any base: semi-transparent thin films,
                   dark glossy pools with clots and darker rims, spatter, dried
                   cracks.  Used by every material.
``GHS_Muscle``     dark red muscle, fibres along object Z, fascia, marbling
``GHS_Fat``        yellow lobular fat with red septa and capillaries
``GHS_Bone``       ivory bone (pores, foramina, vessels) + spongy diploe
=================  =========================================================

Attributes read (Attribute node, type GEOMETRY; missing = 0 = intact):

=================  =========================================================
GH_Skin / GH_Lips  gore_wound + gore_depth (dermis 0-0.12, fat -0.55, muscle
                   -0.95, bone), gore_edge (abrasion), gore_bruise, gore_burn
                   (erythema, blisters, peeling, leather, char), gore_blood,
                   gh_lip (anatomy's vermilion mask)
GH_Fat             gore_depth (top of a skin wall = dermis), gore_blood
GH_Muscle          gore_depth (>0.96 bone showing), gore_bruise, gore_burn,
                   gore_blood
GH_Bone            gore_wound (broken spongy face), gore_fracture (crack
                   density: lines or zones both work), gore_blood
GH_Brain           gh_sulcus (anatomy), gore_wound (contusion), gore_blood
GH_Eye             gore_blood (bloodshot, hemorrhage, film), gore_wound
GH_Teeth           tooth_id (anatomy, per-tooth shade), gore_blood
Gums/Tongue/Mouth  gore_blood
GH_Blood           nothing (colour from blood_age / wetness only)
=================  =========================================================

Global controls: Value nodes named ``GH_wetness`` and ``GH_blood_age`` (every
material) and ``GH_skin_tone`` / ``GH_pallor`` (skin, lips), driven from the
``GH_Controls`` empty through ``gh_common.drive``.

Conventions the other modules rely on:

* Object space = the contract's head space (metres, face toward -Y); the skin,
  mouth and teeth shaders use landmark positions (FACE_REGIONS, OCCLUSAL_Z),
  so those objects must keep an identity transform.
* Eyes: origin at the eyeball centre, local -Y = gaze, radius EYE_R, limbus at
  |xz| = LIMBUS_R.  The iris is found by refracting the view ray through the
  cornea onto a plane at y = IRIS_PLANE_Y, so any rotation/scale is fine.
* Muscle fibres run along object Z.
* GH_Skin mixes a cheap healthy BSDF with the full damage BSDF by "any gore
  attribute > 0"; Cycles skips the damage branch on intact skin.
* setup_stage() is ~1.5 stops hot for these (physically based) albedos: render
  with ``scene.view_settings.exposure = STAGE_EXPOSURE`` (-1.5).

Run ``python3 materials.py`` for look-dev renders (``renders/materials_*.png``).
Options: ``--only lookdev,gore,dried,close,eye,head``, ``--no-head``,
``--samples N``, ``--res N``, ``--out DIR``.
"""
import math
import os
import sys

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_common as ghc  # noqa: E402

MATERIAL_NAMES = ("GH_Skin", "GH_Lips", "GH_Muscle", "GH_Fat", "GH_Bone", "GH_Brain", "GH_Blood",
                  "GH_Eye", "GH_Teeth", "GH_Gums", "GH_Tongue", "GH_MouthInterior")

# object name -> material name (assign_materials)
OBJECT_MATERIALS = {
    "GH_Skin": "GH_Skin", "GH_Muscle": "GH_Muscle", "GH_Skull": "GH_Bone", "GH_Jaw": "GH_Bone",
    "GH_Brain": "GH_Brain", "GH_Eye_L": "GH_Eye", "GH_Eye_R": "GH_Eye",
    "GH_Teeth_Upper": "GH_Teeth", "GH_Teeth_Lower": "GH_Teeth", "GH_Gums": "GH_Gums",
    "GH_Tongue": "GH_Tongue", "GH_MouthCavity": "GH_MouthInterior",
}

GORE_ATTRS = ("gore_wound", "gore_depth", "gore_edge", "gore_blood",
              "gore_bruise", "gore_burn", "gore_fracture")

# Eye convention (object space, metres): origin = eyeball centre, -Y = gaze.
EYE_R = 0.012             # sclera radius
CORNEA_R = 0.0075         # cornea sphere radius (anatomy.build_eye)
CORNEA_OFF = 0.00582      # cornea sphere centre at (0, -CORNEA_OFF, 0)
LIMBUS_R = 0.0059         # iris edge, measured perpendicular to the gaze axis
IRIS_R = 0.0058
PUPIL_R = 0.0022
IRIS_PLANE_Y = -0.0101    # the iris is a disc ~3 mm behind the cornea apex
CORNEA_IOR = 1.376

# Teeth: occlusal plane height at the incisors and its rise toward the molars
# (curve of Spee), used for the enamel -> cervical gradient.
OCCLUSAL_Z = -0.0556
OCCLUSAL_Y = -0.087
OCCLUSAL_SLOPE = 0.035    # dz / dy toward the back of the mouth

# Face landmarks (mirrored |x|) for regional skin colour, from CONTRACT.md.
FACE_REGIONS = {
    #             centre                     radius  (red, dark)
    "nose":      ((0.0, -0.104, -0.008),     0.016, (0.45, 0.0)),
    "cheek":     ((0.043, -0.079, -0.012),   0.021, (0.34, 0.0)),
    "ear":       ((0.074, 0.004, 0.000),     0.028, (0.50, 0.0)),
    "chin":      ((0.0, -0.090, -0.088),     0.014, (0.15, 0.0)),
    "under_eye": ((0.031, -0.081, 0.009),    0.010, (0.0, 0.45)),
    "lid":       ((0.032, -0.083, 0.030),    0.009, (0.10, 0.25)),
}


# ---------------------------------------------------------------------------
# Node building helpers
# ---------------------------------------------------------------------------
def _isvec(x):
    if isinstance(x, _S):
        return x.s.type in ('VECTOR', 'RGBA')
    return isinstance(x, (tuple, list))


class _S:
    """An output socket with arithmetic operators.

    Floats become Math nodes and vectors/colours Vector Math nodes, so shader
    formulas read like ordinary expressions (``a * 0.5 + b``).
    """
    __slots__ = ("t", "s")

    def __init__(self, tree, socket):
        self.t, self.s = tree, socket

    def __add__(self, o):
        return self.t.op('ADD', self, o)

    def __radd__(self, o):
        return self.t.op('ADD', o, self)

    def __sub__(self, o):
        return self.t.op('SUBTRACT', self, o)

    def __rsub__(self, o):
        return self.t.op('SUBTRACT', o, self)

    def __mul__(self, o):
        return self.t.op('MULTIPLY', self, o)

    def __rmul__(self, o):
        return self.t.op('MULTIPLY', o, self)

    def __truediv__(self, o):
        return self.t.op('DIVIDE', self, o)

    def __rtruediv__(self, o):
        return self.t.op('DIVIDE', o, self)

    def __neg__(self):
        return self.t.op('MULTIPLY', self, -1.0)

    def max(self, o):
        return self.t.op('MAXIMUM', self, o)

    def min(self, o):
        return self.t.op('MINIMUM', self, o)

    def abs(self):
        return self.t.op('ABSOLUTE', self)

    def pow(self, e):
        return self.t.math('POWER', self, e)

    def clamp(self):
        return self.t.math('ADD', self, 0.0, clamp=True)

    def smooth(self, e0, e1):
        """Smoothstep from e0 to e1 (e0 > e1 gives a falling edge)."""
        return self.t.smooth(self, e0, e1)

    def ramp(self, stops, interp='LINEAR'):
        return self.t.ramp(self, stops, interp)

    def length(self):
        return self.t.vmath('LENGTH', self)

    def normalize(self):
        return self.t.vmath('NORMALIZE', self)

    def dot(self, o):
        return self.t.vmath('DOT_PRODUCT', self, o)

    @property
    def x(self):
        return self.t.sep(self)[0]

    @property
    def y(self):
        return self.t.sep(self)[1]

    @property
    def z(self):
        return self.t.sep(self)[2]


class ShaderBuilder:
    """Builds shader nodes into a material or group node tree."""

    def __init__(self, nt):
        self.nt = nt
        self.nodes, self.links = nt.nodes, nt.links
        self._cache = {}

    # -- plumbing ----------------------------------------------------------
    def _set(self, sock, v):
        if v is None:
            return
        if isinstance(v, _S):
            self.links.new(v.s, sock)
        elif isinstance(v, bpy.types.NodeSocket):
            self.links.new(v, sock)
        else:
            if sock.type == 'RGBA':
                v = (v, v, v, 1.0) if isinstance(v, (int, float)) else (tuple(v) + (1.0,))[:4]
            elif sock.type == 'VECTOR':
                v = (v, v, v) if isinstance(v, (int, float)) else tuple(v)[:3]
            sock.default_value = v

    def node(self, idname, inputs=None, label=None, **props):
        """New node; ``inputs`` maps socket name/identifier/index to a value or socket."""
        n = self.nodes.new(idname)
        for k, v in props.items():
            setattr(n, k, v)
        for key, val in (inputs or {}).items():
            self._set(self._find(n.inputs, key), val)
        if label:
            n.label = label
        return n

    @staticmethod
    def _find(coll, key):
        if isinstance(key, int):
            return coll[key]
        for s in coll:
            if s.identifier == key:
                return s
        for s in coll:
            if s.name == key and getattr(s, "enabled", True):
                return s
        raise KeyError(key)

    def o(self, node, key=0):
        """Wrap an output socket of ``node``."""
        return _S(self, self._find(node.outputs, key))

    # -- maths -------------------------------------------------------------
    def math(self, op, a, b=None, c=None, clamp=False):
        n = self.nodes.new('ShaderNodeMath')
        n.operation, n.use_clamp = op, clamp
        for i, v in enumerate((a, b, c)):
            self._set(n.inputs[i], v)
        return _S(self, n.outputs[0])

    def vmath(self, op, a, b=None, c=None, scale=None):
        n = self.nodes.new('ShaderNodeVectorMath')
        n.operation = op
        for i, v in enumerate((a, b, c)):
            self._set(n.inputs[i], v)
        self._set(n.inputs[3], scale)
        out = 'Value' if op in ('DOT_PRODUCT', 'DISTANCE', 'LENGTH') else 'Vector'
        return _S(self, n.outputs[out])

    def _v3(self, x):
        if x is None or _isvec(x):
            return x
        if isinstance(x, _S):
            return self.vec(x, x, x)
        return (x, x, x)

    def op(self, op, a, b=None):
        """Binary operation choosing float or vector math from the operands."""
        if _isvec(a) or _isvec(b):
            if op in ('MULTIPLY', 'DIVIDE') and b is not None and not _isvec(b):
                if op == 'DIVIDE':
                    b = self.math('DIVIDE', 1.0, b) if isinstance(b, _S) else 1.0 / b
                return self.vmath('SCALE', a, scale=b)
            if op == 'MULTIPLY' and not _isvec(a):
                return self.vmath('SCALE', b, scale=a)
            return self.vmath(op, self._v3(a), self._v3(b))
        return self.math(op, a, b)

    def vec(self, x, y, z):
        return self.o(self.node('ShaderNodeCombineXYZ', {0: x, 1: y, 2: z}))

    def sep(self, v):
        key = ("sep", v.s.as_pointer())
        if key not in self._cache:
            n = self.node('ShaderNodeSeparateXYZ', {0: v})
            self._cache[key] = tuple(_S(self, n.outputs[i]) for i in range(3))
        return self._cache[key]

    def smooth(self, x, e0, e1):
        n = self.node('ShaderNodeMapRange', {'Value': x, 'From Min': e0, 'From Max': e1,
                                             'To Min': 0.0, 'To Max': 1.0},
                      interpolation_type='SMOOTHSTEP', clamp=True)
        return self.o(n, 'Result')

    def mix(self, f, a, b):
        """Linear blend a -> b by factor f (colour mix if a or b is a vector/colour)."""
        if _isvec(a) or _isvec(b):
            n = self.node('ShaderNodeMix', {'Factor_Float': f, 'A_Color': a, 'B_Color': b}, data_type='RGBA')
            return self.o(n, 'Result_Color')
        n = self.node('ShaderNodeMix', {'Factor_Float': f, 'A_Float': a, 'B_Float': b}, data_type='FLOAT')
        return self.o(n, 'Result_Float')

    def ramp(self, x, stops, interp='LINEAR'):
        """Colour ramp; ``stops`` = [(position, colour or grey value), ...]."""
        n = self.node('ShaderNodeValToRGB', {0: x})
        cr = n.color_ramp
        cr.interpolation = interp
        els = cr.elements
        while len(els) < len(stops):
            els.new(0.5)
        for el, (pos, col) in zip(els, stops):
            el.position = pos
            el.color = (col, col, col, 1.0) if isinstance(col, (int, float)) else (*col[:3], 1.0)
        return self.o(n, 'Color')

    def luminance(self, c):
        return self.vmath('DOT_PRODUCT', c, (0.2126, 0.7152, 0.0722))

    def gauss(self, p, centre, radius):
        """exp(-|p - centre|^2 / radius^2)."""
        d = p - tuple(centre)
        return self.math('EXPONENT', d.dot(d) * (-1.0 / (radius * radius)))

    def ridge(self, n, width):
        """Thin lines where a 0..1 noise crosses 0.5 (vein / crack networks)."""
        return 1.0 - (n - 0.5).abs().smooth(0.0, width)

    # -- inputs ------------------------------------------------------------
    def coord(self, kind='Object'):
        key = ("coord", kind)
        if key not in self._cache:
            self._cache[key] = self.o(self.node('ShaderNodeTexCoord'), kind)
        return self._cache[key]

    def geometry(self, out):
        key = ("geo",)
        if key not in self._cache:
            self._cache[key] = self.node('ShaderNodeNewGeometry')
        return self.o(self._cache[key], out)

    def attr(self, name):
        """Float point/face attribute of the evaluated geometry (0 when missing)."""
        key = ("attr", name)
        if key not in self._cache:
            n = self.node('ShaderNodeAttribute', attribute_type='GEOMETRY', attribute_name=name, label=name)
            self._cache[key] = self.o(n, 'Factor')
        return self._cache[key]

    def control(self, prop):
        """Value node ``GH_<prop>`` driven from GH_Controls[prop]."""
        key = ("ctrl", prop)
        if key not in self._cache:
            ctrl = ghc.ensure_controls()
            n = self.node('ShaderNodeValue', label=prop)
            n.name = f"GH_{prop}"
            n.outputs[0].default_value = float(ctrl.get(prop, ghc.CONTROL_PROPS[prop][0]))
            ghc.drive(self.nt, f'nodes["{n.name}"].outputs[0].default_value', prop)
            self._cache[key] = self.o(n)
        return self._cache[key]

    def value(self, name, v):
        """Named tweakable constant."""
        n = self.node('ShaderNodeValue', label=name)
        n.name = name
        n.outputs[0].default_value = v
        return self.o(n)

    # -- textures ----------------------------------------------------------
    def noise(self, p, scale, detail=2.0, rough=0.5, distortion=0.0, color=False, lac=2.0, ntype='FBM'):
        n = self.node('ShaderNodeTexNoise', {'Vector': p, 'Scale': scale, 'Detail': detail,
                                             'Roughness': rough, 'Lacunarity': lac,
                                             'Distortion': distortion}, noise_type=ntype)
        return self.o(n, 'Color' if color else 'Factor')

    def voronoi(self, p, scale, feature='F1', rand=1.0, smooth=0.5):
        """Voronoi node; returns (distance, cell colour, radius) sockets."""
        n = self.node('ShaderNodeTexVoronoi', {'Vector': p, 'Scale': scale, 'Randomness': rand,
                                               'Smoothness': smooth}, feature=feature)
        outs = {s.name: _S(self, s) for s in n.outputs}
        return outs['Distance'], outs['Color'], outs['Radius']

    def white(self, p):
        n = self.node('ShaderNodeTexWhiteNoise', {'Vector': p}, noise_dimensions='3D')
        return self.o(n, 'Value')

    def warp(self, p, scale, amount, detail=2.0):
        """Domain-warp a coordinate by a low frequency noise (metres)."""
        return p + (self.noise(p, scale, detail, color=True) - (0.5, 0.5, 0.5)) * amount

    # -- shading -------------------------------------------------------------
    def bump(self, height, distance, strength=1.0, normal=None):
        n = self.node('ShaderNodeBump', {'Height': height, 'Distance': distance,
                                         'Strength': strength, 'Normal': normal})
        return self.o(n, 'Normal')

    def principled(self, inputs, sss_method='RANDOM_WALK'):
        n = self.node('ShaderNodeBsdfPrincipled', inputs)
        n.distribution = 'MULTI_GGX'
        n.subsurface_method = sss_method
        return n

    def output(self, shader):
        out = self.node('ShaderNodeOutputMaterial')
        out.target = 'ALL'
        self._set(out.inputs['Surface'], shader if isinstance(shader, _S) else shader.outputs[0])
        return out

    # -- groups --------------------------------------------------------------
    def inp(self, name):
        key = ("ginp",)
        if key not in self._cache:
            self._cache[key] = self.node('NodeGroupInput')
        return self.o(self._cache[key], name)

    def result(self, name, value):
        key = ("gout",)
        if key not in self._cache:
            self._cache[key] = self.node('NodeGroupOutput')
        self._set(self._cache[key].inputs[name], value)

    def group(self, ng, inputs):
        """Instance a node group; returns {output name: socket}."""
        n = self.nodes.new('ShaderNodeGroup')
        n.node_tree = ng
        n.label = ng.name
        for k, v in inputs.items():
            self._set(n.inputs[k], v)
        return {s.name: _S(self, s) for s in n.outputs}

    def layout(self):
        """Arrange nodes in columns by distance from the output (readable in the editor)."""
        sinks = [n for n in self.nodes if n.bl_idname in ('ShaderNodeOutputMaterial', 'NodeGroupOutput')]
        depth = {n.name: 0 for n in sinks}
        links = [(lk.from_node.name, lk.to_node.name) for lk in self.links]
        for _ in range(len(self.nodes)):
            changed = False
            for a, b in links:
                if b in depth and depth.get(a, -1) < depth[b] + 1:
                    depth[a] = depth[b] + 1
                    changed = True
            if not changed:
                break
        top = max(depth.values(), default=0) + 1
        cols = {}
        for n in self.nodes:
            cols.setdefault(depth.get(n.name, top), []).append(n)
        for d, ns in cols.items():
            for i, n in enumerate(ns):
                n.location = (-d * 240.0, (len(ns) * 0.5 - i) * 180.0)


_SOCKET_TYPES = {'VALUE': 'NodeSocketFloat', 'RGBA': 'NodeSocketColor', 'VECTOR': 'NodeSocketVector'}


def _new_group(name, inputs, outputs, description=""):
    """Create (or rebuild) a shader node group. Sockets are (name, type, default)."""
    ng = bpy.data.node_groups.get(name)
    if ng is None or ng.bl_idname != 'ShaderNodeTree':
        ng = bpy.data.node_groups.new(name, 'ShaderNodeTree')
    ng.nodes.clear()
    ng.interface.clear()
    ng.description = description
    for spec in inputs:
        sname, stype, default = spec
        s = ng.interface.new_socket(name=sname, in_out='INPUT', socket_type=_SOCKET_TYPES[stype])
        if default is not None:
            s.default_value = (tuple(default) + (1.0,))[:4] if stype == 'RGBA' else default
    for sname, stype in outputs:
        ng.interface.new_socket(name=sname, in_out='OUTPUT', socket_type=_SOCKET_TYPES[stype])
    return ng, ShaderBuilder(ng)


def _new_material(name):
    """Get or create a material with an empty node tree (drivers cleared)."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    if mat.node_tree is None:
        mat.use_nodes = True
    if mat.node_tree.animation_data is not None:
        mat.node_tree.animation_data_clear()
    mat.node_tree.nodes.clear()
    if "gh_gore_standin" in mat:
        del mat["gh_gore_standin"]
    mat["gh_materials"] = True
    return mat, ShaderBuilder(mat.node_tree)


def _finish(mat, t, viewport_color, rough=0.5):
    t.layout()
    mat.diffuse_color = (*viewport_color, 1.0)
    mat.roughness = rough
    return mat


# ---------------------------------------------------------------------------
# Shared node groups
# ---------------------------------------------------------------------------
def _group_blood_film():
    """GHS_BloodFilm: blood layered over a base surface.

    Blood (0..1) is coverage *and* thickness: low values are thin smears that
    tint the surface underneath, high values are pooled, glossy, raised blood
    that hides it.  Age 0 = fresh saturated red with a wet coat, 1 = dark
    brown-black, matte, cracked.  Thin films dry (darken) before thick pools.
    """
    ng, t = _new_group("GHS_BloodFilm", [
        ("Color", 'RGBA', (0.6, 0.4, 0.3)), ("Roughness", 'VALUE', 0.4), ("Blood", 'VALUE', 0.0),
        ("Age", 'VALUE', 0.0), ("Wetness", 'VALUE', 0.8), ("Vector", 'VECTOR', None)],
        [("Color", 'RGBA'), ("Roughness", 'VALUE'), ("Coat", 'VALUE'), ("Coat Roughness", 'VALUE'),
         ("Coat Tint", 'RGBA'), ("Mask", 'VALUE'), ("Thickness", 'VALUE'), ("Height", 'VALUE'),
         ("Height Mask", 'VALUE'), ("SSS", 'VALUE')], "Wet or dried blood over a base surface")
    base, rough, blood = t.inp("Color"), t.inp("Roughness"), t.inp("Blood")
    age, wet, p = t.inp("Age"), t.inp("Wetness"), t.inp("Vector")

    n_big = t.noise(p, 70.0, 3.0, 0.6)
    n_mid = t.noise(p, 330.0, 2.0, 0.55)
    # coverage: blotchy edges; the noise only acts where there is blood at all
    cov = blood * (0.6 + 0.8 * n_big) + (n_mid - 0.5) * 0.4 * blood.smooth(0.0, 0.3)
    film = cov.smooth(0.10, 0.19)
    thick = cov.smooth(0.45, 1.0)
    # fine spatter droplets on the fringe of a bloody area
    sd, scol, _ = t.voronoi(t.warp(p, 900.0, 0.0004), 520.0)
    spk = (1.0 - sd.smooth(0.05, 0.17)) * t.sep(scol)[0].smooth(0.55, 0.6)
    spk = spk * blood.smooth(0.02, 0.12) * (1.0 - blood.smooth(0.3, 0.5))
    mask = film.max(spk)
    thick = thick.max(spk * 0.8)
    # thin films dry first, and drying is patchy
    a = (age + (1.0 - thick) * 0.35 * age + (n_mid - 0.5) * 0.5 * age * (1.0 - age)).clamp()

    # thin films are semi-transparent stains; opacity grows with the amount
    op = 0.6 + 0.4 * cov.smooth(0.15, 0.5)
    thin = t.mix(op, base, t.mix(n_mid, base * (0.45, 0.05, 0.056), base * (0.30, 0.022, 0.03)))
    fresh = t.mix(thick, thin, t.mix(n_mid, (0.035, 0.0038, 0.0045), (0.07, 0.0065, 0.0075)))
    # clots in pooled blood, and the darker rim where a film thins out at its edge
    clot = t.noise(p, 500.0, 3.0).smooth(0.58, 0.72) * thick
    fresh = t.mix(clot * 0.8, fresh, (0.022, 0.0025, 0.003))
    rim = film * (1.0 - cov.smooth(0.2, 0.34))
    fresh = t.mix(rim * 0.5, fresh, fresh * 0.55)
    old = t.mix(thick, base * (0.36, 0.16, 0.11), (0.026, 0.0085, 0.006))
    col = t.mix(a, fresh, old)
    # dried pools crack into flakes that show the surface underneath
    cd, _, _ = t.voronoi(p, 650.0, 'DISTANCE_TO_EDGE')
    crack = (1.0 - cd.smooth(0.0, 0.06)) * a.smooth(0.55, 0.95) * thick.smooth(0.35, 0.9)
    col = t.mix(crack * 0.75, col, base * 0.3)

    t.result("Color", t.mix(mask, base, col))
    r_blood = t.mix(a, t.mix(wet, 0.34, 0.05) + clot * 0.2, t.mix(thick, 0.64, 0.42))
    t.result("Roughness", t.mix(mask, rough, r_blood))
    t.result("Coat", mask * (0.35 + 0.65 * thick) * (1.0 - a * 0.9) * (0.25 + 0.75 * wet))
    t.result("Coat Roughness", 0.02 + (1.0 - wet) * 0.25 + a * 0.3)
    t.result("Coat Tint", t.mix(thick * (1.0 - a), (1.0, 1.0, 1.0), (0.92, 0.32, 0.27)))
    t.result("Mask", mask)
    t.result("Thickness", thick * mask)
    # relief from a cheap subset (a Bump node evaluates its height graph 3x)
    cov_h = blood * (0.7 + 0.6 * n_big)
    hmask = cov_h.smooth(0.10, 0.19)
    hthick = cov_h.smooth(0.45, 1.0)
    crack_h = (1.0 - cd.smooth(0.0, 0.06)) * age.smooth(0.55, 0.95) * hthick
    t.result("Height", hmask * (0.25 + 0.75 * hthick) - crack_h * 0.6)
    t.result("Height Mask", hmask * hthick.max(0.3))
    t.result("SSS", 1.0 - mask * (0.4 + 0.6 * thick))
    t.layout()
    return ng


def _group_muscle():
    """GHS_Muscle: dark red skeletal muscle.

    Fibres run along object Z.  Everything fibrous is noise stretched along Z
    (smooth isosurfaces stay long, wavy lines on curved surfaces, unlike
    Voronoi cells): fine myofibre streaks, fascicle tone, and thin dark
    perimysium seams where a stretched noise crosses 0.5.  Whitish fascia and a
    little fat marbling on top.
    """
    ng, t = _new_group("GHS_Muscle", [("Vector", 'VECTOR', None), ("Wetness", 'VALUE', 0.8)],
                       [("Color", 'RGBA'), ("Roughness", 'VALUE'), ("Coat", 'VALUE'), ("Height", 'VALUE')],
                       "Striated muscle: colour, gloss and height (fibres along Z)")
    p, wet = t.inp("Vector"), t.inp("Wetness")
    pw = t.warp(p, 30.0, 0.006)
    pf = pw * (1.0, 1.0, 0.05)                       # stretch along Z -> fibres
    fib = t.noise(pf, 2600.0, 3.0, 0.55)
    fine = t.noise(pf, 7500.0, 1.0, 0.5)
    bund = t.noise(pf, 450.0, 2.0, 0.45)
    seam = t.ridge(t.noise(pf + (3.3, 1.7, 0.0), 300.0, 2.0, 0.4), 0.035) \
        * t.noise(pf, 120.0).smooth(0.3, 0.55)
    v = fib * 0.5 + fine * 0.15 + bund * 0.35
    col = v.ramp([(0.2, (0.055, 0.005, 0.007)), (0.5, (0.13, 0.013, 0.016)), (0.8, (0.22, 0.028, 0.030))])
    col = t.mix(seam * 0.75, col, (0.05, 0.004, 0.004))
    # translucent whitish fascia sheets and a little fat along some seams
    fascia = t.noise(p, 45.0, 3.0, 0.6).smooth(0.64, 0.80) * 0.4
    col = t.mix(fascia * (0.5 + 0.5 * fib), col, (0.40, 0.29, 0.26))
    marb = seam * t.noise(pf, 140.0, 3.0).smooth(0.62, 0.72) * 0.8
    col = t.mix(marb, col, (0.50, 0.36, 0.16))
    t.result("Color", col)
    t.result("Roughness", t.mix(wet, 0.5, 0.2) + (fib - 0.5) * 0.12 + fascia * 0.1)
    t.result("Coat", wet * 0.3 * (1.0 - seam * 0.5))
    t.result("Height", fib * 0.7 + bund * 0.5)
    t.layout()
    return ng


def _group_fat():
    """GHS_Fat: yellow subcutaneous fat, glossy rounded lobules with thin red septa.

    Two lobule sizes (~4 mm and ~1.4 mm) are blended so the pattern never
    reads as a regular honeycomb.
    """
    ng, t = _new_group("GHS_Fat", [("Vector", 'VECTOR', None), ("Wetness", 'VALUE', 0.8)],
                       [("Color", 'RGBA'), ("Roughness", 'VALUE'), ("Coat", 'VALUE'), ("Height", 'VALUE')],
                       "Lobular fat: colour, gloss and height")
    p, wet = t.inp("Vector"), t.inp("Wetness")
    pw = t.warp(p, 40.0, 0.005)
    d1, c1, _ = t.voronoi(pw, 240.0, 'F1', rand=0.9)
    e1, _, _ = t.voronoi(pw, 240.0, 'DISTANCE_TO_EDGE', rand=0.9)
    d2, c2, _ = t.voronoi(t.warp(pw, 300.0, 0.0008), 700.0, 'F1', rand=1.0)
    e2, _, _ = t.voronoi(t.warp(pw, 300.0, 0.0008), 700.0, 'DISTANCE_TO_EDGE', rand=1.0)
    lob = (1.0 - d1.smooth(0.1, 0.85)) * 0.6 + (1.0 - d2.smooth(0.05, 0.8)) * 0.4
    sept = (1.0 - e1.smooth(0.0, 0.035)).max((1.0 - e2.smooth(0.0, 0.05)) * 0.45)
    tone = t.sep(c1)[0] * 0.6 + t.sep(c2)[1] * 0.4
    n = t.noise(p, 1400.0, 2.0)
    col = (lob * 0.45 + tone * 0.4 + n * 0.15).ramp([(0.15, (0.40, 0.21, 0.035)), (0.5, (0.57, 0.37, 0.085)),
                                                     (0.85, (0.66, 0.50, 0.17))])
    cap = t.ridge(t.noise(t.warp(p, 120.0, 0.002), 160.0, 3.0), 0.012) * t.noise(p, 45.0).smooth(0.4, 0.6)
    col = t.mix(sept * 0.6, col, (0.48, 0.17, 0.08))
    col = t.mix(cap * 0.75, col, (0.30, 0.025, 0.018))
    blush = t.noise(p, 60.0, 3.0).smooth(0.55, 0.75) * 0.35    # blood-tinged patches
    col = t.mix(blush, col, col * (0.9, 0.45, 0.35))
    t.result("Color", col)
    t.result("Roughness", t.mix(wet, 0.45, 0.2) + sept * 0.1)
    t.result("Coat", wet * 0.4)
    t.result("Height", (1.0 - d1.smooth(0.1, 0.85)) * 1.3)
    t.layout()
    return ng


def _group_bone():
    """GHS_Bone: ivory cortical bone (pores, foramina, periosteal vessels) + spongy diploe."""
    ng, t = _new_group("GHS_Bone", [("Vector", 'VECTOR', None), ("Wetness", 'VALUE', 0.8)],
                       [("Color", 'RGBA'), ("Roughness", 'VALUE'), ("Height", 'VALUE'),
                        ("Diploe Color", 'RGBA'), ("Diploe Height", 'VALUE')],
                       "Bone surface and broken spongy bone")
    p, wet = t.inp("Vector"), t.inp("Wetness")
    n1 = t.noise(p, 90.0, 3.0, 0.55)
    n2 = t.noise(p, 700.0, 2.0, 0.5)
    col = (n1 * 0.7 + n2 * 0.3).ramp([(0.3, (0.46, 0.37, 0.25)), (0.55, (0.61, 0.53, 0.39)),
                                      (0.8, (0.69, 0.62, 0.48))])
    pd, _, _ = t.voronoi(p, 2400.0)
    pit = 1.0 - pd.smooth(0.0, 0.22)
    col = t.mix(pit * 0.6, col, (0.26, 0.18, 0.12))
    fd, fcol, _ = t.voronoi(p, 260.0)
    dot = (1.0 - fd.smooth(0.0, 0.07)) * t.sep(fcol)[0].smooth(0.8, 0.82)
    col = t.mix(dot * 0.85, col, (0.20, 0.09, 0.07))
    vessel = t.ridge(t.noise(t.warp(p, 60.0, 0.004), 110.0, 3.0), 0.008) * t.noise(p, 40.0).smooth(0.55, 0.7)
    col = t.mix(vessel * 0.3, col, (0.45, 0.16, 0.12))
    grain = t.noise(p * (1.0, 1.0, 0.35), 350.0, 4.0, 0.6)    # lamellar grain
    col = col * (0.88 + 0.24 * grain)
    md, _, _ = t.voronoi(p, 900.0)
    mpit = (1.0 - md.smooth(0.0, 0.18)) * t.noise(p, 80.0).smooth(0.45, 0.6)
    col = t.mix(mpit * 0.6, col, (0.30, 0.20, 0.13))
    stain = t.noise(p, 30.0, 3.0).smooth(0.6, 0.8) * 0.4
    col = t.mix(stain, col, (0.40, 0.27, 0.16))
    t.result("Color", col)
    t.result("Roughness", t.mix(wet * 0.35, 0.58 + (n1 - 0.5) * 0.2 + pit * 0.1, 0.25))
    t.result("Height", n2 * 0.5 - pit * 0.7)
    # spongy bone between the tables: marrow-filled cavities
    sd, scol, _ = t.voronoi(p, 1100.0, 'F1')
    holes = (1.0 - sd.smooth(0.18, 0.34)) * t.noise(p, 300.0).smooth(0.3, 0.6)
    dbase = t.mix(n1, (0.52, 0.38, 0.28), (0.64, 0.52, 0.40))
    dcol = t.mix(holes, dbase, t.mix(t.sep(scol)[1], (0.14, 0.025, 0.018), (0.30, 0.08, 0.05)))
    t.result("Diploe Color", dcol)
    t.result("Diploe Height", -holes * 1.5)
    t.layout()
    return ng


def _build_groups():
    return {"blood": _group_blood_film(), "muscle": _group_muscle(), "fat": _group_fat(),
            "bone": _group_bone()}


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
def _blood_layer(t, g, base, rough, blood, p):
    """Apply GHS_BloodFilm with the material's own wetness / blood_age controls."""
    return t.group(g["blood"], {"Color": base, "Roughness": rough, "Blood": blood,
                                "Age": t.control("blood_age"), "Wetness": t.control("wetness"),
                                "Vector": p})


def _expression_lines(t, pm):
    """Fine wrinkles at the contract's landmarks: forehead lines, crow's feet,
    lines under the lower lids. ``pm`` = object position with |x|. Returns 0..1."""
    x, y, z = t.sep(pm)
    # forehead: arched horizontal lines, broken up along their length
    fmask = z.smooth(0.042, 0.056) * (1.0 - z.smooth(0.084, 0.098)) * (1.0 - x.smooth(0.035, 0.056)) \
        * (-y).smooth(0.055, 0.075)
    arch = z - x * x * 4.0
    fore = t.ridge(t.noise(t.vec(x * 0.06, y * 0.06, arch), 140.0, 2.0, 0.4), 0.035)
    fore = fore * fmask * t.noise(pm, 45.0).smooth(0.3, 0.55)
    # crow's feet: lines radiating from the outer eye corner
    d = pm - (0.047, -0.066, 0.021)
    dx, dy, dz = t.sep(d)
    side = t.vec(dx, dy, 0.0).length()
    ray = t.vec(side, dz, 0.0).normalize()
    rx, ry, _ = t.sep(ray)
    crow = t.ridge(t.noise(t.vec(rx * 6.0, ry * 6.0, d.length() * 60.0), 1.0, 2.0, 0.5), 0.03)
    crow = crow * t.gauss(pm, (0.055, -0.060, 0.020), 0.011) * dx.smooth(-0.002, 0.004)
    # under the lower lids: fine lines following the lid curve
    ue = t.gauss(pm, (0.032, -0.081, 0.006), 0.009)
    und = t.ridge(t.noise(t.vec(x * 0.08, y * 0.08, z + (x - 0.032) * (x - 0.032) * 12.0), 420.0, 2.0),
                  0.05) * ue
    return (fore + crow * 0.45 + und * 0.5).clamp()


def _skin_material(g, name="GH_Skin", lips=False):
    """GH_Skin: subsurface skin, pores, mottling, and every gore attribute.

    Reads gh_lip (vermilion), gore_wound + gore_depth (rings dermis -> fat ->
    muscle -> bone), gore_edge (abrasion), gore_bruise, gore_burn, gore_blood.

    Two BSDFs are mixed by "any gore here": Cycles skips a Mix Shader branch
    (and every node only it uses) when the factor is 0, so intact skin never
    pays for the wound / burn / blood layers.
    """
    mat, t = _new_material(name)
    p = t.coord()
    tone, pallor = t.control("skin_tone"), t.control("pallor")
    wet = t.control("wetness")
    wound, depth, edge = t.attr("gore_wound"), t.attr("gore_depth"), t.attr("gore_edge")
    blood, bruise, burn = t.attr("gore_blood"), t.attr("gore_bruise"), t.attr("gore_burn")
    lip = t.value("lip_force", 1.0) if lips else t.attr("gh_lip")

    # ---- healthy skin albedo ------------------------------------------------
    base = tone.ramp([(0.0, (0.61, 0.43, 0.35)), (0.25, (0.48, 0.30, 0.225)), (0.5, (0.30, 0.16, 0.10)),
                      (0.75, (0.13, 0.062, 0.038)), (1.0, (0.05, 0.026, 0.018))])
    pm = t.vec(p.x.abs(), p.y, p.z)                  # mirrored for symmetric face regions
    red_reg, dark_reg = 0.0, 0.0
    for c, r, (red, dark) in FACE_REGIONS.values():
        gz = t.gauss(pm, c, r)
        if red:
            red_reg = red_reg + gz * red
        if dark:
            dark_reg = dark_reg + gz * dark
    oily = t.gauss(pm, (0.0, -0.085, 0.07), 0.04).max(t.gauss(pm, (0.0, -0.104, -0.008), 0.018))

    m_low = t.noise(p, 22.0, 3.0, 0.55)
    m_red = t.noise(p + (7.3, 1.1, 3.7), 30.0, 3.0, 0.55)
    m_fine = t.noise(p, 190.0, 3.0, 0.6)
    redness = (m_red.smooth(0.5, 0.8) * 0.28 + red_reg + (m_fine - 0.5) * 0.22).clamp()
    redness = redness * (1.0 - pallor)
    col = t.mix(redness, base, base * (1.04, 0.64, 0.66))
    col = col * (0.82 + 0.34 * m_low)
    col = t.mix((m_fine - 0.5).abs() * 0.5, col, col * (1.0, 0.92, 0.80))     # sallow / olive patches
    # melanin freckles / spots in a fraction of cells
    fd, fcol, _ = t.voronoi(t.warp(p, 300.0, 0.0006), 380.0)
    frk = (1.0 - fd.smooth(0.0, 0.3)) * t.sep(fcol)[0].smooth(0.72, 0.9) * 0.4
    col = t.mix(frk, col, col * (0.70, 0.57, 0.47))
    # periorbital darkening, a little purple
    col = t.mix(dark_reg.clamp(), col, col * (0.72, 0.62, 0.70))
    # superficial veins, much more visible when pale
    vein = t.ridge(t.noise(t.warp(p, 20.0, 0.01), 38.0, 3.0), 0.022) * t.noise(p, 12.0).smooth(0.45, 0.62)
    col = t.mix(vein * (0.12 + 0.4 * pallor), col, col * (0.62, 0.74, 0.95))
    # lips: redder, darker vermilion (bluish-grey when pale)
    lip_tone = tone.ramp([(0.0, (0.50, 0.19, 0.19)), (0.25, (0.40, 0.13, 0.135)), (0.5, (0.25, 0.085, 0.08)),
                          (0.75, (0.11, 0.042, 0.042)), (1.0, (0.045, 0.019, 0.019))])
    lip_col = t.mix(pallor, lip_tone * (0.85 + 0.3 * m_fine), col * (0.72, 0.66, 0.82))
    col = t.mix(lip, col, lip_col)

    # ---- micro relief -------------------------------------------------------
    pd, _, _ = t.voronoi(p, 2200.0)
    big_pores = (t.gauss(pm, (0.0, -0.104, -0.010), 0.02) + t.gauss(pm, (0.04, -0.082, -0.006), 0.022)).clamp()
    pore = 1.0 - pd.smooth(0.0, 0.30 + 0.14 * big_pores)
    gd, _, _ = t.voronoi(p * (1.0, 1.0, 1.5), 1000.0, 'DISTANCE_TO_EDGE', rand=0.9)
    groove = (1.0 - gd.smooth(0.0, 0.12)) * m_fine.smooth(0.3, 0.7) * 0.45
    fine = t.noise(p, 6000.0, 2.0)
    lip_lines = t.ridge(t.noise(p * (1.0, 1.0, 0.1), 900.0, 2.0), 0.08) * lip
    col = col * (1.0 - pore * 0.10 * (1.0 - lip) - groove * 0.03 - lip_lines * 0.12)
    # pallor: desaturate toward a cool grey
    lum = t.luminance(col)
    skin_col = t.mix(pallor * 0.72, col, t.vec(lum, lum, lum) * (0.97, 1.0, 1.06) * 1.08)
    mid = t.noise(p, 160.0, 2.0)
    wrinkles = _expression_lines(t, pm)
    col = col * (1.0 - wrinkles * 0.08)
    h_skin = (-pore * 0.9 - groove * 0.4) * (1.0 - lip) + fine * 0.25 - lip_lines * 1.6 + mid * 0.5 \
        - wrinkles * 3.0
    h_lite = mid * 0.5 - pore * 0.6              # cheaper relief for the damage branch
    rough = 0.44 + (m_fine - 0.5) * 0.14 + (fine - 0.5) * 0.12 - oily * 0.1 - lip * 0.12 - wet * 0.04 \
        + pore * 0.1

    skin_sss = {'IOR': 1.4, 'Specular IOR Level': 0.5, 'Subsurface Radius': (1.0, 0.40, 0.22),
                'Subsurface Scale': 0.0035, 'Subsurface IOR': 1.4, 'Subsurface Anisotropy': 0.8,
                'Sheen Roughness': 0.35}
    n_skin = t.bump(h_skin, 0.0001)              # the oily coat follows the pores too
    healthy = t.principled(dict(skin_sss, **{
        'Base Color': skin_col, 'Roughness': rough, 'Subsurface Weight': 1.0,
        'Coat Weight': 0.10 + oily * 0.1 + lip * 0.15, 'Coat Roughness': 0.32 - lip * 0.1, 'Coat IOR': 1.45,
        'Coat Normal': n_skin, 'Sheen Weight': 0.06, 'Normal': n_skin}), sss_method='RANDOM_WALK_SKIN')

    # ==== damage (only evaluated where some gore attribute is non-zero) =======
    # ---- open wound: layered tissue by depth ---------------------------
    fat = t.group(g["fat"], {"Vector": p, "Wetness": wet})
    mus = t.group(g["muscle"], {"Vector": p, "Wetness": wet})
    bone = t.group(g["bone"], {"Vector": p, "Wetness": wet})
    dn = depth + (t.noise(p, 380.0, 3.0, 0.6) - 0.5) * 0.4
    f_fat, f_mus, f_bone = dn.smooth(0.10, 0.16), dn.smooth(0.50, 0.57), dn.smooth(0.92, 0.98)
    dermis = t.mix(t.noise(p, 900.0, 2.0), (0.46, 0.18, 0.14), (0.60, 0.36, 0.30))
    tis = t.mix(f_fat, dermis, fat["Color"])
    tis = t.mix(f_mus, tis, mus["Color"])
    fresh_bone = t.mix(t.noise(p, 250.0).smooth(0.35, 0.55), bone["Color"] * (0.85, 0.68, 0.62),
                       bone["Diploe Color"])
    tis = t.mix(f_bone, tis, fresh_bone)
    # exposed tissue is always blood-soaked, more so deeper down
    soak = t.noise(p, 140.0, 3.0).smooth(0.4, 0.75) * 0.35 + dn.smooth(0.55, 1.0) * 0.3
    tis = t.mix(soak * (1.0 - f_bone * 0.5), tis, tis * (0.62, 0.20, 0.17))
    h_tis = t.mix(f_fat, t.noise(p, 900.0) * 0.6, fat["Height"])
    h_tis = t.mix(f_mus, h_tis, mus["Height"])
    h_tis = t.mix(f_bone, h_tis, bone["Height"])
    wm = (wound + (t.noise(p, 400.0) - 0.5) * 0.3).smooth(0.35, 0.65)
    col = t.mix(wm, skin_col, tis)
    rgh = t.mix(wm, rough, t.mix(wet, 0.45, 0.14))
    height = t.mix(wm, h_lite, h_tis * 1.5)

    # ---- abraded / torn rim ----------------------------------------------
    en = t.noise(p, 220.0, 2.0)
    em = (edge * (0.55 + 0.9 * en)).clamp().smooth(0.15, 0.6) * (1.0 - wm)
    scr = t.noise(p * (1.0, 1.0, 0.18), 1400.0, 3.0)         # drag scratches
    ab = (t.noise(p, 900.0, 4.0) * 0.7 + scr * 0.3).ramp(
        [(0.25, (0.36, 0.07, 0.05)), (0.5, (0.19, 0.035, 0.025)), (0.75, (0.08, 0.02, 0.014))])
    ab = t.mix(edge.smooth(0.2, 0.9) * 0.5, ab, (0.09, 0.02, 0.015))
    col = t.mix(em, col, ab)
    rgh = t.mix(em, rgh, t.mix(wet, 0.62, 0.3))
    height = t.mix(em, height, en * 1.2 - 0.6)

    # ---- bruise (under the skin: multiplies the colour) ---------------------
    bz = (bruise * (0.5 + 1.0 * t.noise(p, 60.0, 4.0, 0.65))).clamp()
    tint = bz.ramp([(0.0, (1.0, 1.0, 1.0)), (0.1, (0.96, 0.95, 0.76)), (0.25, (0.84, 0.74, 0.56)),
                    (0.45, (0.64, 0.40, 0.45)), (0.7, (0.42, 0.24, 0.42)), (1.0, (0.24, 0.13, 0.30))])
    col = col * t.mix(wm, tint, (1.0, 1.0, 1.0))
    ptd, ptc, _ = t.voronoi(p, 1100.0)
    pete = (1.0 - ptd.smooth(0.05, 0.18)) * t.sep(ptc)[0].smooth(0.55, 0.6) * bz.smooth(0.35, 0.8)
    col = t.mix(pete * 0.8, col, col * (0.55, 0.12, 0.14))
    rgh = rgh - bz * 0.08

    # ---- burn: erythema -> weeping dermis + blisters -> waxy leather -> char ---
    bno = t.noise(p, 90.0, 3.0, 0.6)
    bnf = t.noise(p, 420.0, 2.0, 0.6)
    jit = ((bno - 0.5) * 0.75 + (bnf - 0.5) * 0.3) * burn.smooth(0.0, 0.3) * (1.0 - burn.smooth(0.92, 1.0) * 0.5)
    bn = (burn + jit).clamp()
    ery = bn.smooth(0.02, 0.22) * (0.6 + 0.4 * bnf)
    raw = bn.smooth(0.28, 0.42)
    leather = bn.smooth(0.55, 0.70)
    char = bn.smooth(0.70, 0.86)
    col = t.mix(ery, col, col * (1.10, 0.50, 0.46))
    # weeping dermis: mottled pink-red, pin-point bleeding, pale coagulated patches
    raw_col = t.noise(p, 500.0, 3.0, 0.6).ramp([(0.25, (0.22, 0.022, 0.022)), (0.5, (0.40, 0.075, 0.062)),
                                                (0.72, (0.48, 0.16, 0.12)), (0.9, (0.50, 0.31, 0.25))])
    col = t.mix(raw, col, raw_col)
    # blisters: domes of lifted, yellowish translucent epidermis
    bd, bcol, _ = t.voronoi(p, 190.0, 'F1')
    blister = (1.0 - bd.smooth(0.0, 0.42)) * t.sep(bcol)[0].smooth(0.5, 0.58)
    blister = blister * bn.smooth(0.16, 0.26) * (1.0 - bn.smooth(0.44, 0.54))
    bm = blister.smooth(0.02, 0.25)
    col = t.mix(bm * 0.7, col, t.mix(0.5, col, (0.52, 0.43, 0.30)))
    # sheets of dead epidermis peeling off: greyed skin colour, dark curled edges
    pe = t.noise(p, 150.0, 3.0, 0.6, distortion=0.4)
    band = bn.smooth(0.26, 0.36) * (1.0 - bn.smooth(0.58, 0.68))
    peel = pe.smooth(0.55, 0.585) * band
    peel_edge = (1.0 - (pe - 0.567).abs().smooth(0.0, 0.012)) * band
    lum_s = t.luminance(skin_col)
    peel_col = t.mix(0.55, skin_col, t.vec(lum_s, lum_s, lum_s) * (1.05, 0.97, 0.86))
    col = t.mix(peel * 0.9, col, peel_col * (0.85 + 0.3 * pe.smooth(0.6, 0.75)))
    col = t.mix(peel_edge * 0.8, col, (0.12, 0.07, 0.05))
    # full thickness: waxy white / tan / brown leather with thrombosed vessels
    lcol = t.noise(p, 260.0, 3.0, 0.6).ramp([(0.25, (0.12, 0.06, 0.03)), (0.5, (0.24, 0.14, 0.075)),
                                             (0.72, (0.36, 0.28, 0.20)), (0.88, (0.42, 0.38, 0.32))])
    thromb = t.ridge(t.noise(p, 120.0, 3.0), 0.015) * t.noise(p, 50.0).smooth(0.45, 0.6)
    lcol = t.mix(thromb * 0.8, lcol, (0.06, 0.02, 0.015))
    col = t.mix(leather, col, lcol)
    # char: black-brown crust with grey ash, fine fissures and deep cracks down to raw red
    kd, _, _ = t.voronoi(p, 300.0, 'DISTANCE_TO_EDGE', rand=0.9)
    kd2, _, _ = t.voronoi(p * (1.0, 1.0, 1.3), 900.0, 'DISTANCE_TO_EDGE', rand=1.0)
    crack = (1.0 - kd.smooth(0.0, 0.045)) * char * t.noise(p, 260.0, 2.0).smooth(0.45, 0.62)
    fissure = (1.0 - kd2.smooth(0.0, 0.06)) * char.smooth(0.3, 1.0) * 0.8
    cn = t.noise(p, 700.0, 3.0, 0.65)
    ccol = cn.ramp([(0.3, (0.007, 0.006, 0.005)), (0.55, (0.03, 0.02, 0.015)), (0.75, (0.06, 0.045, 0.035)),
                    (0.92, (0.15, 0.14, 0.13))])
    col = t.mix(char, col, ccol)
    col = t.mix(fissure, col, (0.003, 0.0025, 0.002))
    col = t.mix(crack, col, t.mix(kd.smooth(0.0, 0.015), (0.03, 0.005, 0.004), (0.13, 0.018, 0.012)))
    rgh = t.mix(ery, rgh, rgh - 0.05)
    rgh = t.mix(raw, rgh, t.mix(wet, 0.35, 0.1))
    rgh = t.mix(bm, rgh, 0.04)
    rgh = t.mix(peel, rgh, 0.5)
    rgh = t.mix(leather, rgh, 0.38)
    rgh = t.mix(char, rgh, 0.35 + cn.smooth(0.35, 0.7) * 0.55)       # glossy tarry spots
    height = t.mix(raw, height, height * 0.3)
    height = height + blister.smooth(0.0, 0.6) * 5.0 + peel * 1.5 - peel_edge * 0.5
    height = t.mix(char, height, bno * 2.0 + bnf * 1.2 + cn * 1.2 - crack * 3.0 - fissure * 0.8)

    # ---- blood on top -----------------------------------------------------
    bl = _blood_layer(t, g, col, rgh.clamp(), t.mix(wm, blood, blood * 0.65), p)
    height = t.mix(bl["Height Mask"], height, bl["Height"] * 3.0)
    sss = (1.0 - wm * 0.75) * (1.0 - leather) * bl["SSS"] + bm * 0.5
    # one bump only: a Bump node re-evaluates its whole height graph twice more
    n_fine = t.bump(height, 0.0001)
    damaged = t.principled(dict(skin_sss, **{
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'Subsurface Weight': sss.clamp(),
        'Coat Weight': (bl["Coat"] + (0.12 + oily * 0.1 + lip * 0.15) * (1.0 - bl["Mask"])
                        + (wm + raw + bm) * wet * 0.5).clamp(),
        'Coat Roughness': t.mix(bl["Mask"], 0.3 - lip * 0.1, bl["Coat Roughness"]),
        'Coat IOR': 1.45, 'Coat Tint': bl["Coat Tint"], 'Coat Normal': n_fine,
        'Sheen Weight': 0.06 * (1.0 - bl["Mask"]), 'Normal': n_fine}), sss_method='RANDOM_WALK_SKIN')

    any_gore = wound.max(edge).max(blood).max(bruise).max(burn).smooth(0.0, 0.01)
    mixn = t.node('ShaderNodeMixShader', {0: any_gore, 1: healthy.outputs[0], 2: damaged.outputs[0]})
    t.output(mixn)
    return _finish(mat, t, (0.47, 0.28, 0.19), 0.45)


def _fibre_tangent(t):
    """World-space tangent along the object's Z axis (muscle fibre direction)."""
    return t.o(t.node('ShaderNodeVectorTransform', {'Vector': (0.0, 0.0, 1.0)}, vector_type='VECTOR',
                      convert_from='OBJECT', convert_to='WORLD'))


def _muscle_material(g):
    """GH_Muscle: exposed muscle layer. Reads gore_blood, gore_burn, gore_bruise, gore_depth."""
    mat, t = _new_material("GH_Muscle")
    p, wet = t.coord(), t.control("wetness")
    m = t.group(g["muscle"], {"Vector": p, "Wetness": wet})
    col, rough = m["Color"], m["Roughness"]
    # deepest part of a wound wall: periosteum / bone showing through
    bone = t.group(g["bone"], {"Vector": p, "Wetness": wet})
    fb = (t.attr("gore_depth") + (t.noise(p, 300.0) - 0.5) * 0.06).smooth(0.96, 0.99)
    col = t.mix(fb, col, bone["Color"])
    # hematoma inside the muscle
    col = t.mix(t.attr("gore_bruise").smooth(0.1, 0.8) * 0.7, col, col * (0.45, 0.25, 0.35))
    # heat: cooked grey-brown, then charred
    bn = t.attr("gore_burn")
    col = t.mix(bn.smooth(0.2, 0.55), col, (0.30, 0.18, 0.12))
    col = t.mix(bn.smooth(0.7, 0.9), col, (0.02, 0.014, 0.012))
    rough = t.mix(bn.smooth(0.3, 0.8), rough, 0.7)
    bl = _blood_layer(t, g, col, rough, (t.attr("gore_blood") * 0.65).max(0.12), p)
    h = t.mix(bl["Height Mask"], m["Height"], bl["Height"] * 2.0)
    nrm = t.bump(h, 0.00015)
    bsdf = t.principled({
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'IOR': 1.4,
        'Anisotropic': 0.55 * (1.0 - bl["Mask"]), 'Tangent': _fibre_tangent(t),
        'Subsurface Weight': 0.35 * bl["SSS"], 'Subsurface Radius': (1.0, 0.25, 0.15),
        'Subsurface Scale': 0.002, 'Coat Weight': (m["Coat"] + bl["Coat"]).clamp(),
        'Coat Roughness': t.mix(bl["Mask"], 0.06 + (1.0 - wet) * 0.2, bl["Coat Roughness"]),
        'Coat Tint': bl["Coat Tint"], 'Coat Normal': nrm, 'Normal': nrm})
    t.output(bsdf)
    return _finish(mat, t, (0.30, 0.03, 0.03), 0.3)


def _fat_material(g):
    """GH_Fat: subcutaneous fat (skin wound walls). Reads gore_depth (dermis at the top), gore_blood."""
    mat, t = _new_material("GH_Fat")
    p, wet = t.coord(), t.control("wetness")
    f = t.group(g["fat"], {"Vector": p, "Wetness": wet})
    # the top of the wall is the dermis: dense, pale pink-white
    d = t.attr("gore_depth")
    dm = (1.0 - (d + (t.noise(p, 500.0) - 0.5) * 0.05).smooth(0.10, 0.16)) * d.smooth(0.0, 0.02)
    col = t.mix(dm, f["Color"], t.mix(t.noise(p, 900.0), (0.48, 0.22, 0.18), (0.60, 0.38, 0.32)))
    bl = _blood_layer(t, g, col, f["Roughness"], (t.attr("gore_blood") * 0.6).max(0.1), p)
    h = t.mix(bl["Height Mask"], f["Height"], bl["Height"] * 2.0)
    bsdf = t.principled({
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'IOR': 1.45,
        'Subsurface Weight': 0.7 * bl["SSS"], 'Subsurface Radius': (1.0, 0.7, 0.35),
        'Subsurface Scale': 0.002, 'Coat Weight': (f["Coat"] + bl["Coat"]).clamp(),
        'Coat Roughness': t.mix(bl["Mask"], 0.1, bl["Coat Roughness"]), 'Coat Tint': bl["Coat Tint"],
        'Normal': t.bump(h, 0.00025)})
    t.output(bsdf)
    return _finish(mat, t, (0.78, 0.58, 0.20), 0.25)


def _bone_material(g):
    """GH_Bone: skull and jaw. Reads gore_fracture, gore_wound (broken spongy bone), gore_blood.

    gore_fracture may be thin lines or broad zones (it is interpolated on a
    ~1.4 mm skull mesh either way), so it is used as a *crack density*: thin,
    jagged procedural crack lines (two scales) appear wherever it is high, with
    blood seeping out along them and a soft stain around.
    """
    mat, t = _new_material("GH_Bone")
    p, wet = t.coord(), t.control("wetness")
    b = t.group(g["bone"], {"Vector": p, "Wetness": wet})
    wound, frac = t.attr("gore_wound"), t.attr("gore_fracture")
    # broken faces show the spongy diploe
    wm = (wound + (t.noise(p, 500.0) - 0.5) * 0.3).smooth(0.45, 0.8)
    col = t.mix(wm, b["Color"], b["Diploe Color"])
    h = t.mix(wm, b["Height"], b["Diploe Height"])
    # crack network: main jagged cracks (~4 mm plates) + fine hairlines
    fz = (frac + (t.noise(p, 200.0, 2.0) - 0.5) * 0.3).clamp()
    cd1, _, _ = t.voronoi(t.warp(p, 700.0, 0.0006), 240.0, 'DISTANCE_TO_EDGE', rand=0.95)
    cd2, _, _ = t.voronoi(t.warp(p, 1500.0, 0.0003), 750.0, 'DISTANCE_TO_EDGE', rand=1.0)
    main = (1.0 - cd1.smooth(0.0, 0.028 + fz * 0.02)) * fz.smooth(0.2, 0.55)
    hair = (1.0 - cd2.smooth(0.0, 0.05)) * fz.smooth(0.35, 0.8) * t.noise(p, 400.0).smooth(0.35, 0.55)
    seep = (1.0 - cd1.smooth(0.0, 0.16)) * fz.smooth(0.2, 0.55)      # blood soaking out of the cracks
    stain = fz.smooth(0.05, 0.6) * t.noise(p, 260.0, 3.0).smooth(0.3, 0.65)
    col = t.mix(stain * 0.45, col, col * (0.62, 0.30, 0.24))
    col = t.mix(seep * 0.7, col, col * (0.45, 0.10, 0.08))
    col = t.mix(hair * 0.85, col, (0.10, 0.02, 0.014))
    col = t.mix(main, col, (0.025, 0.006, 0.005))
    h = h - main * 3.0 - hair * 1.2
    # wounds and fractures are bloody, but the bone must still read: patchy film
    blood = (t.attr("gore_blood") * 0.55).max(main * 0.7)
    bl = _blood_layer(t, g, col, b["Roughness"], blood, p)
    h = t.mix(bl["Height Mask"], h, bl["Height"] * 2.0 - main * 2.0)
    bsdf = t.principled({
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'IOR': 1.55,
        'Subsurface Weight': 0.2 * bl["SSS"], 'Subsurface Radius': (1.0, 0.75, 0.5),
        'Subsurface Scale': 0.0012, 'Coat Weight': (bl["Coat"] + wet * 0.15).clamp(),
        'Coat Roughness': t.mix(bl["Mask"], 0.25, bl["Coat Roughness"]), 'Coat Tint': bl["Coat Tint"],
        'Normal': t.bump(h, 0.00016)})
    t.output(bsdf)
    return _finish(mat, t, (0.78, 0.71, 0.57), 0.5)


def _brain_material(g):
    """GH_Brain: pinkish grey, glossy, vessels. Reads gh_sulcus, gore_wound (contusion), gore_blood."""
    mat, t = _new_material("GH_Brain")
    p, wet = t.coord(), t.control("wetness")
    sul = t.attr("gh_sulcus")
    n1 = t.noise(p, 80.0, 4.0, 0.55)
    col = n1.ramp([(0.3, (0.36, 0.235, 0.215)), (0.6, (0.45, 0.31, 0.28)), (0.85, (0.52, 0.38, 0.34))])
    blush = t.noise(p, 220.0, 3.0).smooth(0.5, 0.75)
    col = t.mix(blush * 0.4, col, col * (1.0, 0.62, 0.6))
    col = t.mix(sul * 0.85, col, col * (0.42, 0.18, 0.17))
    # pial vessels: big dark veins (mostly along the sulci), fine red arteries
    pv = t.warp(p, 40.0, 0.006)
    vmask = t.noise(p, 30.0).smooth(0.3, 0.55)
    veins = t.ridge(t.noise(pv, 70.0, 3.0), 0.022) * vmask
    veins = veins.max(sul.smooth(0.55, 0.9) * t.noise(pv, 150.0).smooth(0.4, 0.5) * 0.85)
    arts = t.ridge(t.noise(pv + (3.1, 7.7, 1.3), 260.0, 3.0), 0.025) * (0.4 + 0.6 * sul)
    caps = t.ridge(t.noise(pv + (1.3, 2.1, 5.3), 800.0, 2.0), 0.03) * 0.5
    col = t.mix(veins * 0.9, col, (0.10, 0.012, 0.028))
    col = t.mix(arts * 0.75, col, (0.34, 0.035, 0.035))
    col = t.mix(caps * 0.5, col, (0.42, 0.10, 0.09))
    # contused, pulped tissue in a wound
    wm = (t.attr("gore_wound") + (t.noise(p, 350.0) - 0.5) * 0.4).smooth(0.3, 0.7)
    pn = t.noise(p, 600.0, 3.0)
    pulp = pn.ramp([(0.2, (0.16, 0.025, 0.022)), (0.45, (0.36, 0.20, 0.18)), (0.75, (0.46, 0.33, 0.30)),
                    (0.95, (0.52, 0.40, 0.36))])
    col = t.mix(wm, col, pulp)
    h = veins * 1.2 + arts * 0.5 + t.noise(p, 900.0) * 0.3 + wm * t.noise(p, 500.0, 4.0) * 2.0
    rough = t.mix(wet, 0.45, 0.2) + wm * 0.1
    bl = _blood_layer(t, g, col, rough, t.attr("gore_blood") * 0.55, p)
    bsdf = t.principled({
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'IOR': 1.4,
        'Subsurface Weight': 0.7 * bl["SSS"], 'Subsurface Radius': (1.0, 0.45, 0.35),
        'Subsurface Scale': 0.003, 'Coat Weight': (wet * 0.55 + bl["Coat"]).clamp(),
        'Coat Roughness': t.mix(bl["Mask"], 0.04 + (1.0 - wet) * 0.2, bl["Coat Roughness"]),
        'Coat Tint': bl["Coat Tint"], 'Normal': t.bump(t.mix(bl["Height Mask"], h, bl["Height"]), 0.0001)})
    t.output(bsdf)
    return _finish(mat, t, (0.68, 0.49, 0.46), 0.2)


def _blood_material(g):
    """GH_Blood: drips, pools and the gore module's eye walls.

    Fresh: deep saturated red, translucent (red subsurface), glossy coat;
    blood_age -> clotted, then dark brown-black and matte. wetness -> gloss.
    """
    mat, t = _new_material("GH_Blood")
    p = t.coord()
    wet, age = t.control("wetness"), t.control("blood_age")
    n = t.noise(p, 300.0, 3.0)
    a = (age + (n - 0.5) * 0.4 * age * (1.0 - age)).clamp()
    clot = t.noise(p, 900.0, 4.0).smooth(0.5, 0.7) * (a * (1.0 - a) * 4.0).clamp()
    fresh = t.mix(n, (0.06, 0.005, 0.006), (0.10, 0.008, 0.009))
    old = t.mix(n, (0.022, 0.008, 0.006), (0.045, 0.014, 0.009))
    col = t.mix(a, fresh, old)
    col = t.mix(clot * 0.7, col, (0.07, 0.008, 0.006))
    rough = t.mix(a, t.mix(wet, 0.3, 0.04), 0.32 + n * 0.2) + clot * 0.1
    h = clot * 0.3 * (1.0 - a) + t.noise(p, 4000.0) * a * 0.3
    bsdf = t.principled({
        'Base Color': col, 'Roughness': rough, 'IOR': 1.36, 'Specular IOR Level': 0.5,
        'Subsurface Weight': (1.0 - a) * 0.45, 'Subsurface Radius': (1.0, 0.02, 0.02),
        'Subsurface Scale': 0.001, 'Subsurface IOR': 1.36,
        'Coat Weight': (1.0 - a * 0.85) * (0.3 + 0.7 * wet), 'Coat IOR': 1.36,
        'Coat Roughness': 0.015 + (1.0 - wet) * 0.2 + a * 0.3, 'Coat Tint': t.mix(a, (0.9, 0.4, 0.4), (1, 1, 1)),
        'Normal': t.bump(h, 0.0001)})
    t.output(bsdf)
    return _finish(mat, t, (0.25, 0.01, 0.01), 0.1)


def _eye_material(g):
    """GH_Eye: sclera with veins, refracted iris with radial fibres, pupil, wet cornea.

    Object coordinates of the eyeball: origin at its centre, -Y = gaze. The
    iris is looked up where the view ray, refracted by the cornea, meets the
    iris plane, so it sits ~3 mm under the glossy cornea with real parallax.
    Reads gore_blood (bloodshot + hemorrhage) and gore_wound (ruptured globe).
    """
    mat, t = _new_material("GH_Eye")
    p = t.coord()
    wet = t.control("wetness")
    blood, wound = t.attr("gore_blood"), t.attr("gore_wound")
    px, py, pz = t.sep(p)
    rs = t.vec(px, 0.0, pz).length()
    front = py.smooth(-0.004, -0.007)
    corn = (1.0 - rs.smooth(LIMBUS_R - 0.00022, LIMBUS_R + 0.00030)) * front

    # ---- refraction through the cornea onto the iris plane ------------------
    inc = t.o(t.node('ShaderNodeVectorTransform', {'Vector': t.geometry('Incoming')},
                     vector_type='VECTOR', convert_from='WORLD', convert_to='OBJECT'))
    ray = -inc.normalize()
    nrm = (p - (0.0, -CORNEA_OFF, 0.0)).normalize()
    ref = t.vmath('REFRACT', ray, nrm, scale=1.0 / CORNEA_IOR)
    ry = t.sep(ref)[1].max(0.05)
    dist = ((IRIS_PLANE_Y - py) / ry).clamp().min(0.006)
    hit = p + ref * dist
    hx, _, hz = t.sep(hit)
    hr = t.vec(hx, 0.0, hz).length()
    rn = hr / IRIS_R                                    # 0 centre .. 1 iris edge
    u = t.vec(hx, hz, 0.0) / hr.max(1e-6)               # direction around the pupil
    ux, uy, _ = t.sep(u)

    # ---- iris ---------------------------------------------------------------
    fib = t.noise(t.vec(ux, uy, rn * 0.16), 26.0, 4.0, 0.6, distortion=0.15)
    fib2 = t.noise(t.vec(ux, uy, rn * 0.3), 75.0, 2.0, 0.5)
    coll = 0.52 + (t.noise(t.vec(ux, uy, 0.0), 2.5) - 0.5) * 0.16   # wavy collarette radius
    inner = 1.0 - rn.smooth(coll - 0.05, coll + 0.04)
    outer_col = (fib * 0.65 + fib2 * 0.35).ramp([(0.25, (0.035, 0.065, 0.080)), (0.5, (0.10, 0.17, 0.20)),
                                                 (0.72, (0.27, 0.37, 0.40)), (0.9, (0.45, 0.52, 0.52))])
    inner_col = (fib * 0.6 + fib2 * 0.4).ramp([(0.3, (0.09, 0.065, 0.035)), (0.6, (0.24, 0.16, 0.075)),
                                               (0.85, (0.42, 0.31, 0.16))])
    iris = t.mix(inner * (0.45 + 0.55 * fib2), outer_col, inner_col)
    ring = t.math('EXPONENT', -((rn - coll) * 22.0).abs().pow(2.0))
    iris = t.mix(ring * 0.4 * fib, iris, (0.52, 0.47, 0.38))
    cd, ccol, _ = t.voronoi(t.vec(ux * 1.0, uy * 1.0, rn * 0.9), 7.0)
    crypt = (1.0 - cd.smooth(0.05, 0.3)) * t.sep(ccol)[0].smooth(0.5, 0.6) * rn.smooth(0.42, 0.55) \
        * (1.0 - rn.smooth(0.8, 0.9))
    iris = t.mix(crypt * 0.75, iris, iris * 0.25)
    furrow = t.ridge(t.noise(t.vec(rn * 3.0, 0.0, 0.0) + t.vec(ux, uy, 0.0) * 0.4, 6.0), 0.03) \
        * rn.smooth(0.6, 0.75)
    iris = t.mix(furrow * 0.35, iris, iris * 0.45)
    iris = t.mix(rn.smooth(0.80, 1.0), iris, (0.02, 0.025, 0.03))            # limbal ring
    pr = PUPIL_R / IRIS_R
    ruff = 1.0 - rn.smooth(pr + 0.02, pr + 0.07)
    iris = t.mix(ruff * 0.85, iris, (0.05, 0.025, 0.012))
    pupil = 1.0 - rn.smooth(pr - 0.015, pr + 0.01)
    iris = t.mix(pupil, iris, (0.003, 0.003, 0.003))

    # ---- sclera -------------------------------------------------------------
    pn = p.normalize()
    back = t.sep(pn)[1].smooth(-0.55, 0.3)
    scl = t.mix(t.noise(p, 400.0, 3.0), (0.62, 0.57, 0.52), (0.71, 0.67, 0.62))
    scl = t.mix(back, scl, (0.52, 0.34, 0.30))
    scl = t.mix((1.0 - rs.smooth(LIMBUS_R, LIMBUS_R + 0.0012)) * front * 0.55, scl, (0.52, 0.53, 0.56))
    shot = (blood * 1.5).clamp()
    away = rs.smooth(LIMBUS_R + 0.0006, 0.0105).max(1.0 - front)
    # meridian coordinates: direction around the gaze axis + angle from the front
    wp = t.warp(p, 300.0, 0.0008)
    wx, wy, wz = t.sep(wp)
    around = t.vec(wx, wz, 0.0).normalize()
    ax_, az_, _ = t.sep(around)
    polar = t.math('ARCCOSINE', (-wy / wp.length().max(1e-6)).clamp())
    v1 = t.ridge(t.noise(t.vec(ax_ * 4.0, az_ * 4.0, polar * 0.9), 3.0, 3.0, 0.6), 0.012 + 0.03 * away)
    v2 = t.ridge(t.noise(t.vec(ax_ * 11.0, az_ * 11.0, polar * 3.0) + (5.0, 1.0, 2.0), 3.0, 2.0, 0.6),
                 0.01 + 0.02 * away)
    vmask = away * (0.45 + 0.55 * t.noise(p, 90.0).smooth(0.4, 0.6))
    scl = t.mix(v1 * vmask * (0.5 + 0.5 * shot), scl, (0.52, 0.06, 0.05))
    scl = t.mix(v2 * vmask * (0.3 + 0.6 * shot), scl, (0.62, 0.16, 0.13))
    scl = t.mix(shot * 0.55 * away, scl, scl * (1.0, 0.58, 0.52))
    hem = (t.noise(p, 120.0, 3.0) + blood * 0.9).smooth(1.05, 1.2) * away
    scl = t.mix(hem, scl, (0.42, 0.018, 0.014))

    col = t.mix(corn, scl, iris)
    # ruptured globe: dark jelly and blood inside
    inside = 1.0 - p.length().smooth(EYE_R * 0.93, EYE_R * 0.975)
    col = t.mix(inside.max(wound * 0.8), col, t.mix(t.noise(p, 600.0), (0.10, 0.012, 0.01), (0.35, 0.26, 0.22)))
    rough = t.mix(corn, 0.28, 0.45)
    bl = _blood_layer(t, g, col, rough, blood * 0.6, p)
    h = v1 * vmask * 0.3 + t.noise(p, 1500.0) * 0.15 * (1.0 - corn)
    bsdf = t.principled({
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'IOR': 1.376,
        'Subsurface Weight': 0.25 * (1.0 - corn) * bl["SSS"], 'Subsurface Radius': (1.0, 0.55, 0.45),
        'Subsurface Scale': 0.0015, 'Coat Weight': 1.0, 'Coat IOR': CORNEA_IOR,
        'Coat Roughness': t.mix(bl["Mask"], 0.015 + (1.0 - wet) * 0.03, bl["Coat Roughness"]),
        'Coat Tint': bl["Coat Tint"], 'Normal': t.bump(h, 0.00005)})
    t.output(bsdf)
    return _finish(mat, t, (0.8, 0.75, 0.7), 0.1)


def _teeth_material(g):
    """GH_Teeth: translucent enamel, yellower toward the gum line. Reads tooth_id, gore_blood."""
    mat, t = _new_material("GH_Teeth")
    p, wet = t.coord(), t.control("wetness")
    _, py, pz = t.sep(p)
    z_occ = t.value("occlusal_z", OCCLUSAL_Z) + (py - OCCLUSAL_Y) * OCCLUSAL_SLOPE
    h = ((pz - z_occ).abs() - 0.0007) / 0.0085            # 0 biting edge .. 1 gum line
    rnd = t.white(t.vec(t.attr("tooth_id"), 0.37, 0.0))
    body = t.mix(h.smooth(0.15, 1.0), (0.68, 0.63, 0.51), (0.56, 0.44, 0.25))
    body = body * (0.92 + 0.12 * rnd)
    front = 1.0 - py.smooth(-0.075, -0.068)               # incisors and canines
    edge = (1.0 - h.smooth(0.0, 0.2)) * front
    col = t.mix(edge * 0.75, body, (0.42, 0.45, 0.48))
    col = t.mix(h.smooth(0.85, 1.1) * 0.6, col, (0.42, 0.29, 0.14))
    craze = t.ridge(t.noise(p * (1.0, 1.0, 0.08), 900.0, 2.0), 0.015) * 0.25
    col = t.mix(craze, col, col * 0.8)
    ao = t.o(t.node('ShaderNodeAmbientOcclusion', {'Distance': 0.0012}, only_local=True, samples=8), 'AO')
    col = t.mix((1.0 - ao) * 0.7, col, col * (0.62, 0.50, 0.35))
    peri = t.noise(p * (0.1, 0.1, 1.0), 2200.0, 2.0)          # growth lines around the crown
    bl = _blood_layer(t, g, col, t.mix(wet, 0.3, 0.12), t.attr("gore_blood"), p)
    nrm = t.bump(t.mix(bl["Height Mask"], peri * 0.3 + craze, bl["Height"]), 0.00004)
    bsdf = t.principled({
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'IOR': 1.62, 'Specular IOR Level': 0.6,
        'Subsurface Weight': 0.55 * bl["SSS"], 'Subsurface Radius': (1.0, 0.85, 0.6),
        'Subsurface Scale': 0.0012, 'Coat Weight': (wet * 0.55 + bl["Coat"]).clamp(),
        'Coat Roughness': t.mix(bl["Mask"], 0.05, bl["Coat Roughness"]), 'Coat Tint': bl["Coat Tint"],
        'Normal': nrm})
    t.output(bsdf)
    return _finish(mat, t, (0.86, 0.82, 0.71), 0.2)


def _wet_mucosa(g, name, base_lo, base_hi, extra=None, sss=0.8, view=(0.6, 0.2, 0.2)):
    """Shared wet pink-red mucosa (gums, tongue, mouth lining).

    ``extra(t, p, col, h)`` may return an adjusted (col, h, rough_add, coat_scale).
    The saliva coat uses the bumped normal so highlights break up on the
    surface texture instead of sitting on it like varnish.
    """
    mat, t = _new_material(name)
    p, wet = t.coord(), t.control("wetness")
    n1 = t.noise(p, 120.0, 3.0, 0.55)
    col = t.mix(n1, base_lo, base_hi)
    blot = t.noise(p + (2.0, 5.0, 1.0), 45.0, 3.0).smooth(0.45, 0.7)
    col = t.mix(blot * 0.5, col, col * (0.82, 0.62, 0.66))
    vess = t.ridge(t.noise(t.warp(p, 80.0, 0.003), 260.0, 3.0), 0.02) * t.noise(p, 50.0).smooth(0.45, 0.65)
    col = t.mix(vess * 0.55, col, (0.30, 0.025, 0.035))
    h = t.noise(p, 1500.0, 2.0) * 0.8 + n1 * 0.6 + vess * 0.5
    rough_add, coat_k = 0.0, 1.0
    if extra is not None:
        col, h, rough_add, coat_k = extra(t, p, col, h)
    bl = _blood_layer(t, g, col, t.mix(wet, 0.5, 0.2) + rough_add, t.attr("gore_blood"), p)
    nrm = t.bump(t.mix(bl["Height Mask"], h, bl["Height"]), 0.0001)
    bsdf = t.principled({
        'Base Color': bl["Color"], 'Roughness': bl["Roughness"], 'IOR': 1.4,
        'Subsurface Weight': sss * bl["SSS"], 'Subsurface Radius': (1.0, 0.33, 0.22),
        'Subsurface Scale': 0.0025, 'Coat Weight': (wet * 0.45 * coat_k + bl["Coat"]).clamp(),
        'Coat Roughness': t.mix(bl["Mask"], 0.06 + (1.0 - wet) * 0.2, bl["Coat Roughness"]),
        'Coat Tint': bl["Coat Tint"], 'Coat Normal': nrm, 'Normal': nrm}, sss_method='RANDOM_WALK')
    t.output(bsdf)
    return _finish(mat, t, view, 0.2)


def _gums_extra(t, p, col, h):
    """Attached gingiva: coral pink, orange-peel stippling, redder vascular patches."""
    sd, _, _ = t.voronoi(p, 2600.0)
    stip = 1.0 - sd.smooth(0.0, 0.35)                      # orange-peel stippling
    col = t.mix(t.noise(p, 60.0).smooth(0.5, 0.7) * 0.55, col, col * (0.78, 0.50, 0.52))
    col = col * (1.0 - stip * 0.08)
    return col, h - stip * 2.0, 0.05, 0.8


def _tongue_extra(t, p, col, h):
    """Dorsum: velvety filiform papillae with whitish tips, red fungiform dots,
    median groove, a light coating toward the back; smoother purplish underside."""
    px, py, _ = t.sep(p)
    fd, _, _ = t.voronoi(p, 2400.0)
    filiform = 1.0 - fd.smooth(0.0, 0.55)
    gd, gcol, _ = t.voronoi(p, 520.0)
    fung = (1.0 - gd.smooth(0.0, 0.2)) * t.sep(gcol)[0].smooth(0.72, 0.76)
    sulcus = t.math('EXPONENT', -(px / 0.0016).pow(2.0))
    nz = t.sep(t.coord('Normal'))[2]
    top = nz.smooth(0.0, 0.5)
    col = t.mix(filiform * top * 0.35, col, (0.60, 0.44, 0.42))
    coat = t.noise(p, 140.0, 3.0).smooth(0.45, 0.75) * py.smooth(-0.07, -0.04) * top * 0.45
    col = t.mix(coat, col, (0.60, 0.50, 0.46))
    col = t.mix(fung * top * 0.85, col, (0.44, 0.05, 0.065))
    col = t.mix(sulcus * top * 0.35, col, col * 0.65)
    col = t.mix(1.0 - top, col, col * (0.78, 0.60, 0.80))      # purplish, veiny underside
    h = h + (filiform * 3.0 + fung * 2.5) * top - sulcus * 6.0 * top
    return col, h, 0.25 * top, 1.0 - top * 0.6


def _mouth_extra(t, p, col, h):
    """Oral lining: darker toward the throat, transverse rugae on the palate."""
    px, py, pz = t.sep(p)
    deep = py.smooth(-0.085, -0.03)
    col = t.mix(deep * 0.85, col, (0.10, 0.012, 0.014))
    nz = t.sep(t.coord('Normal'))[2]
    roof = (-nz).smooth(0.2, 0.6)
    rugae = t.noise(t.vec(px * 0.3, py, pz * 0.3), 700.0, 2.0) * roof * (1.0 - deep)
    return col, h + rugae * 3.0, 0.0, 1.0


def build_materials():
    """Build (or rebuild in place) every GH_* material and the shared GHS_* groups.

    Returns {name: material} for the names in MATERIAL_NAMES. Safe to call
    repeatedly; materials already referenced by modifiers keep their identity.
    """
    ghc.ensure_controls()
    g = _build_groups()
    mats = {
        "GH_Skin": _skin_material(g),
        "GH_Lips": _skin_material(g, "GH_Lips", lips=True),
        "GH_Muscle": _muscle_material(g),
        "GH_Fat": _fat_material(g),
        "GH_Bone": _bone_material(g),
        "GH_Brain": _brain_material(g),
        "GH_Blood": _blood_material(g),
        "GH_Eye": _eye_material(g),
        "GH_Teeth": _teeth_material(g),
        "GH_Gums": _wet_mucosa(g, "GH_Gums", (0.36, 0.07, 0.08), (0.52, 0.17, 0.17), _gums_extra, 0.8,
                               (0.62, 0.24, 0.24)),
        "GH_Tongue": _wet_mucosa(g, "GH_Tongue", (0.38, 0.10, 0.10), (0.52, 0.19, 0.18), _tongue_extra, 0.7,
                                 (0.58, 0.22, 0.22)),
        "GH_MouthInterior": _wet_mucosa(g, "GH_MouthInterior", (0.20, 0.03, 0.03), (0.33, 0.07, 0.07),
                                        _mouth_extra, 0.6, (0.35, 0.07, 0.07)),
    }
    return mats


def assign_materials(objs, mats):
    """Put the right material on every anatomy object (missing objects are skipped).

    objs: {name: object} (e.g. anatomy.build_anatomy()); objects that are not
    in the dict are looked up by name.  mats: build_materials() result.
    """
    for obj_name, mat_name in OBJECT_MATERIALS.items():
        ob = (objs or {}).get(obj_name) or bpy.data.objects.get(obj_name)
        mat = (mats or {}).get(mat_name) or bpy.data.materials.get(mat_name)
        if ob is None or mat is None or ob.type != 'MESH':
            continue
        slots = ob.data.materials
        if len(slots) == 0:
            slots.append(mat)
        else:
            slots[0] = mat


# ---------------------------------------------------------------------------
# Test harness (python3 materials.py)
# ---------------------------------------------------------------------------
def _np():
    import numpy as np
    return np


def _mesh_object(name, bm, loc=(0.0, 0.0, 0.0), mat=None, collection="MatTest"):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    ob = bpy.data.objects.new(name, me)
    ob.location = loc
    ghc.get_collection(collection).objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    return ob


def _sphere(name, radius, loc=(0.0, 0.0, 0.0), subdiv=6, mat=None, offset=(0.0, 0.0, 0.0), squash=(1, 1, 1)):
    """Icosphere test object. ``offset`` moves the mesh in object space (and the
    object back by the same amount) so object-coordinate shaders see the
    region of the head they are meant for."""
    import bmesh
    from mathutils import Matrix, Vector
    bm = bmesh.new()
    bmesh.ops.create_icosphere(bm, subdivisions=subdiv, radius=radius)
    bmesh.ops.transform(bm, verts=bm.verts, matrix=Matrix.Diagonal((*squash, 1.0)))
    bmesh.ops.translate(bm, verts=bm.verts, vec=Vector(offset))
    return _mesh_object(name, bm, Vector(loc) - Vector(offset), mat)


def _verts(ob):
    np = _np()
    co = np.empty(len(ob.data.vertices) * 3, np.float32)
    ob.data.vertices.foreach_get("co", co)
    return co.reshape(-1, 3).astype(np.float64)


def _set_verts(ob, v):
    ob.data.vertices.foreach_set("co", v.astype(_np().float32).ravel())
    ob.data.update()


def _point_attr(ob, name, values):
    att = ob.data.attributes.get(name) or ob.data.attributes.new(name, 'FLOAT', 'POINT')
    att.data.foreach_set("value", _np().asarray(values, _np().float32))


def _wave_noise(p, freq, seed, octaves=3):
    """Cheap smooth 3D noise in [-1, 1]: sums of random plane waves."""
    np = _np()
    rng = np.random.default_rng(seed)
    out = np.zeros(len(p))
    amp, tot = 1.0, 0.0
    for _ in range(octaves):
        d = rng.normal(size=(9, 3))
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        ph = rng.uniform(0, 2 * math.pi, 9)
        out += amp * np.sin(p @ d.T * freq + ph).sum(1) / 3.0
        tot += amp
        amp *= 0.5
        freq *= 2.1
    return np.clip(out / tot, -1.0, 1.0)


def _smoothstep(e0, e1, x):
    np = _np()
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def _frame(c):
    """Unit vector c and two tangents (e1 horizontal, e2 'up' on the surface)."""
    np = _np()
    c = np.asarray(c, float)
    c = c / np.linalg.norm(c)
    e1 = np.cross((0.0, 0.0, 1.0), c)
    e1 /= np.linalg.norm(e1)
    return c, e1, np.cross(c, e1)


def _eye_mesh(name, loc, mat):
    """Eyeball like anatomy.build_eye: sphere r=EYE_R with the cornea bulge."""
    import bmesh
    from mathutils import Matrix, Vector
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=72, v_segments=48, radius=1.0)
    bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.radians(90), 3, 'X'))
    cc = Vector((0.0, -CORNEA_OFF, 0.0))
    for v in bm.verts:
        d = v.co.normalized()
        th = math.acos(max(-1.0, min(1.0, -d.y)))
        th2 = math.pi * (th / math.pi) ** 1.35
        hz = Vector((d.x, 0.0, d.z))
        hz = hz.normalized() if hz.length > 1e-9 else Vector((1.0, 0.0, 0.0))
        d = Vector((hz.x * math.sin(th2), -math.cos(th2), hz.z * math.sin(th2)))
        dc = d.dot(cc)
        tt = dc + math.sqrt(max(dc * dc - cc.dot(cc) + CORNEA_R ** 2, 0.0))
        k = 0.0004
        h = max(k - abs(tt - EYE_R), 0.0) / k
        v.co = d * (max(tt, EYE_R) + h * h * k * 0.25)
    return _mesh_object(name, bm, loc, mat)


def _label(text, loc, size=0.0075):
    cu = bpy.data.curves.new(f"LBL_{text}", 'FONT')
    cu.body = text
    cu.size = size
    cu.align_x = 'CENTER'
    ob = bpy.data.objects.new(f"LBL_{text}", cu)
    ob.location = loc
    ob.rotation_euler = (math.radians(90), 0.0, 0.0)
    m = bpy.data.materials.get("LBL_Text") or bpy.data.materials.new("LBL_Text")
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs[0].default_value = (0.55, 0.55, 0.55, 1.0)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs[0])
    cu.materials.append(m)
    ghc.get_collection("MatTest").objects.link(ob)
    return ob


def _brain_sample(name, radius, loc, mat):
    """The anatomy brain (scaled to the slot) or, without anatomy.py, a folded sphere.

    Both carry the gh_sulcus attribute that anatomy.py writes.
    """
    np = _np()
    try:
        import anatomy
        ob = anatomy.mesh_sdf(name, anatomy.brain_sdf, *anatomy.BRAIN_BOX, 0.0011, voxel=0.0011, project=1,
                              collection=ghc.get_collection("MatTest"))
        v = _verts(ob)
        s = anatomy.gyri_field(np.abs(v[:, 0]), v[:, 1], v[:, 2])
        _point_attr(ob, "gh_sulcus", np.exp(-(s / 0.0016) ** 2))
        ob.data.shade_smooth()
        ob.data.materials.append(mat)
        pivot = bpy.data.objects.new(name + "_Pivot", None)
        pivot.location = loc
        ghc.get_collection("MatTest").objects.link(pivot)
        ob.parent = pivot
        ob.location = (0.0, -0.005, -0.03)
        pivot.scale = (0.33, 0.33, 0.33)
        pivot.rotation_euler = (math.radians(20), 0.0, math.radians(-50))
        return ob
    except Exception as exc:  # noqa: BLE001
        print("brain sample fallback:", exc)
    ob = _sphere(name, radius, loc, 7, mat)
    v = _verts(ob)
    n = v / np.linalg.norm(v, axis=1, keepdims=True)
    f = _wave_noise(n * radius, 260.0, 11, 2) + 0.35 * _wave_noise(n * radius, 700.0, 12, 1)
    sul = np.exp(-(f / 0.12) ** 2)
    _set_verts(ob, v - n * (sul * 0.0028)[:, None])
    _point_attr(ob, "gh_sulcus", sul)
    return ob


def _clear_test_scene():
    ghc.reset_scene()
    ghc.ensure_controls()


# setup_stage() is about 1.5 stops hot: an 18% grey card in the key light
# renders at sRGB ~199.  -1.5 puts it at ~146 (a normal photographic exposure).
STAGE_EXPOSURE = -1.5
SAMPLES, RES = 48, 640       # test render quality (--samples / --res for quick iterations)


def _render(path, cam, samples=48, res=(640, 640)):
    bpy.context.scene.view_settings.exposure = STAGE_EXPOSURE
    bpy.context.view_layer.update()
    return ghc.render(path, cam, samples, res)


def scene_lookdev(out_dir):
    """Grid of material samples at real scale."""
    _clear_test_scene()
    mats = build_materials()
    ghc.setup_stage()
    s, r = 0.066, 0.026
    xs = [(-1.5 + i) * s for i in range(4)]
    zs = [s, 0.0, -s]
    slots = [(xs[i % 4], 0.0, zs[i // 4] + 0.006) for i in range(12)]
    names = ["GH_Skin", "GH_Lips", "GH_Muscle", "GH_Fat", "GH_Bone", "GH_Brain", "GH_Blood", "GH_Eye",
             "GH_Teeth", "GH_Gums", "GH_Tongue", "GH_MouthInterior"]
    for (x, y, z), nm in zip(slots, names):
        loc = (x, y, z)
        if nm == "GH_Brain":
            _brain_sample("S_Brain", r, loc, mats[nm])
        elif nm == "GH_Eye":
            eye = _eye_mesh("S_Eye", loc, mats[nm])
            eye.scale = (2.1, 2.1, 2.1)
            eye.rotation_euler = (math.radians(-8), 0.0, math.radians(-18))
        elif nm == "GH_Teeth":
            _teeth_sample(loc, mats[nm], r)
        elif nm == "GH_Tongue":
            _sphere("S_Tongue", r, loc, 6, mats[nm], offset=(0.0, -0.06, -0.06), squash=(1.0, 1.2, 0.55))
        elif nm == "GH_MouthInterior":
            _sphere("S_Mouth", r, loc, 6, mats[nm], offset=(0.0, -0.09, -0.06))
        elif nm == "GH_Blood":
            ob = _sphere("S_Blood", r, loc, 6, mats[nm])
            v = _verts(ob)
            np = _np()
            nn = v / np.linalg.norm(v, axis=1, keepdims=True)
            _set_verts(ob, v + nn * (0.0015 * _wave_noise(v, 90.0, 5, 2))[:, None])
        else:
            _sphere(f"S_{nm}", r, loc, 6, mats[nm])
        _label(nm[3:], (x, -0.03, z - r - 0.0105))
    cam = ghc.add_camera("MT_Cam", (0.0, -0.78, 0.02), (0.0, 0.0, 0.0), 85.0)
    return _render(os.path.join(out_dir, "materials_lookdev.png"), cam, SAMPLES, (RES, RES * 7 // 8))


def _teeth_sample(loc, mat, r):
    """Real tooth rows from anatomy.py when available, else a row of rounded boxes."""
    from mathutils import Vector
    try:
        import anatomy
        col = ghc.get_collection("MatTest")
        up = anatomy.build_teeth("S_TeethU", True, col)
        lo = anatomy.build_teeth("S_TeethL", False, col)
        centre = Vector((0.0, -0.066, -0.0556))
        for ob in (up, lo):
            ob.data.materials.append(mat)
            ob.location = Vector(loc) - centre
            ob.rotation_euler = (0.0, 0.0, 0.0)
        # look at the front teeth: rotate about the arch centre
        pivot = bpy.data.objects.new("S_TeethPivot", None)
        pivot.location = loc
        col.objects.link(pivot)
        for ob in (up, lo):
            ob.parent = pivot
            ob.location = -centre
        pivot.scale = (1.15, 1.15, 1.15)
        pivot.rotation_euler = (math.radians(12), 0.0, math.radians(-25))
    except Exception as exc:  # noqa: BLE001
        print("teeth sample fallback:", exc)
        for i in range(4):
            _sphere(f"S_Tooth{i}", r * 0.28, (loc[0] - r * 0.9 + i * r * 0.6, loc[1], loc[2]), 5, mat,
                    offset=(0.0, -0.087, -0.051), squash=(0.9, 0.7, 1.9))


def _streak_wiggle(along, k):
    """Sideways wander (m) of blood run k after running ``along`` metres down."""
    np = _np()
    return 0.0006 * np.sin(along * 110.0 + k * 1.7) + 0.00025 * np.sin(along * 330.0 + k * 2.9)


def _gore_head(mat, R=0.07, subdiv=8):
    """Head-sized sphere with synthetic gore_* attributes (see module docstring)."""
    np = _np()
    ob = _sphere("GT_Skin", R, (0.0, 0.0, 0.0), subdiv, mat)
    v = _verts(ob)
    n = v / np.linalg.norm(v, axis=1, keepdims=True)
    N = len(v)
    wound, depth, edge, blood, bruise, burn = (np.zeros(N) for _ in range(6))

    def geo(c):
        c = np.asarray(c, float) / np.linalg.norm(c)
        return R * np.arccos(np.clip(n @ c, -1.0, 1.0))

    # --- open wound: ragged disc, bowl-shaped crater, depth rings to the bone
    cw = np.array((-0.20, -1.0, 0.16))
    cw /= np.linalg.norm(cw)
    sw = geo(cw)
    rw = 0.0105 * (1.0 + 0.22 * _wave_noise(n, 7.0, 1, 2) + 0.09 * _wave_noise(n, 45.0, 9, 2))
    wound = _smoothstep(rw * 1.03, rw * 0.97, sw)
    q = np.clip(1.0 - sw / rw, 0.0, 1.0)
    depth = np.clip(q * 2.2 + 0.1 * _wave_noise(v, 300.0, 6), 0.0, 1.0) * (sw < rw)
    disp = 0.0095 * _smoothstep(0.0, 0.5, q) * (1.0 + 0.2 * _wave_noise(v, 250.0, 8)) \
        + 0.0012 * _smoothstep(0.0, 0.3, q) * _wave_noise(v, 900.0, 12, 2)
    rim = (sw - rw) / 0.0045
    edge = np.exp(-np.clip(rim, 0, None) ** 2) * (sw > rw * 0.92) * (0.65 + 0.35 * _wave_noise(v, 300.0, 2))
    lift = (0.0007 + 0.0005 * _wave_noise(v, 500.0, 13)) * np.exp(-(rim / 0.35) ** 2)   # torn rim rolls up
    el = np.arcsin(np.clip(n[:, 2], -1, 1))
    az = np.arctan2(n[:, 1], n[:, 0])
    el_w, az_w = math.asin(cw[2]), math.atan2(cw[1], cw[0])
    # blood welling over the lower rim and pooling in the lower half of the crater
    low = _smoothstep(0.2 * 0.0105, -0.5 * 0.0105, (el - el_w) * R)
    rim_pool = np.exp(-((sw - rw) / 0.0028) ** 2) * (0.12 + 0.8 * low) * (0.7 + 0.3 * _wave_noise(v, 200.0, 10))
    deep_low = _smoothstep(-0.2 * 0.0105, -0.6 * 0.0105, (el - el_w) * R)
    blood = np.maximum(rim_pool, wound * (0.3 + 0.1 * _wave_noise(v, 400.0, 11)
                                          + 0.6 * deep_low * _smoothstep(0.5, 0.8, q)))
    # --- blood runs straight down from the lower rim (meridians of the sphere)
    rng = np.random.default_rng(7)
    streaks = []
    for k, off in enumerate((-0.75, -0.42, -0.1, 0.22, 0.55, 0.8)):
        x = off * 0.0105
        el0 = el_w - math.sqrt(max(0.0105 ** 2 - x * x, 0.0)) * 0.92 / R
        length = rng.uniform(0.018, 0.05)
        streaks.append((x, el0, length, k))
        along = (el0 - el) * R
        tt = along / length
        lat = (az - az_w) * R * np.cos(el) - x - _streak_wiggle(along, k)
        width = 0.00115 * (1.0 - 0.45 * np.clip(tt, 0, 1)) + 0.0011 * np.exp(-((tt - 1.0) / 0.05) ** 2)
        m = _smoothstep(width, width * 0.45, np.abs(lat)) * (along > -0.002) * (tt < 1.04)
        blood = np.maximum(blood, m * (1.0 - 0.25 * np.clip(tt, 0, 1)))
    # spatter droplets around the wound
    for _ in range(70):
        d = cw + rng.normal(scale=0.28, size=3)
        d /= np.linalg.norm(d)
        rad = rng.uniform(0.0003, 0.0011)
        blood = np.maximum(blood, 0.85 * _smoothstep(rad, rad * 0.5, geo(d)))
    # --- bruise and burn patches
    sb = geo((0.46, -1.0, 0.46))
    bruise = np.clip(np.exp(-(sb / 0.017) ** 2) * (0.8 + 0.35 * _wave_noise(v, 60.0, 3)), 0, 1)
    sbn = geo((0.52, -1.0, -0.42)) * (1.0 + 0.3 * _wave_noise(v, 45.0, 4))
    burn = np.clip(_smoothstep(0.022, 0.0, sbn) ** 0.75 * 1.08, 0, 1)
    _set_verts(ob, v - n * (disp - lift * (sw > rw))[:, None])
    for nm, val in (("gore_wound", wound), ("gore_depth", depth), ("gore_edge", edge),
                    ("gore_blood", blood), ("gore_bruise", bruise), ("gore_burn", burn)):
        _point_attr(ob, nm, val)
    return ob, (cw, el_w, az_w, streaks, R)


def _drip_tubes(info, mat, which=(1, 3)):
    """Blood drips as real geometry along two of the streaks (GH_Blood)."""
    _, _, az_w, streaks, R = info
    for i in which:
        x, el0, length, k = streaks[i]
        cu = bpy.data.curves.new(f"GT_Drip{i}", 'CURVE')
        cu.dimensions = '3D'
        cu.bevel_depth = 0.001
        cu.bevel_resolution = 4
        cu.use_fill_caps = True
        sp = cu.splines.new('POLY')
        npt = 40
        sp.points.add(npt - 1)
        L = length * 0.93
        for j in range(npt):
            tt = j / (npt - 1)
            along = tt * L
            el = el0 - along / R
            az = az_w + (x + float(_streak_wiggle(along, k))) / (R * math.cos(el))
            rad = 0.00042 * (1.0 - 0.35 * tt) + 0.00075 * math.exp(-((tt - 1.0) / 0.07) ** 2)
            rr = R + rad * 0.55
            sp.points[j].co = (rr * math.cos(el) * math.cos(az), rr * math.cos(el) * math.sin(az),
                               rr * math.sin(el), 1.0)
            sp.points[j].radius = rad / 0.001
        ob = bpy.data.objects.new(f"GT_Drip{i}", cu)
        cu.materials.append(mat)
        ghc.get_collection("MatTest").objects.link(ob)


def _gore_bone(mat, loc, R=0.03, subdiv=7):
    """Bone sphere with a depressed fracture: radiating lines + ring, small breach."""
    np = _np()
    ob = _sphere("GT_Bone", R, loc, subdiv, mat)
    v = _verts(ob)
    n = v / np.linalg.norm(v, axis=1, keepdims=True)
    c, e1, e2 = _frame((-0.35, -1.0, 0.22))
    rho = R * np.arccos(np.clip(n @ c, -1.0, 1.0))
    th = np.arctan2(n @ e2, n @ e1)
    rng = np.random.default_rng(21)
    frac = np.zeros(len(v))
    for k in range(7):
        th_k = 2 * math.pi * k / 7 + rng.uniform(-0.25, 0.25)
        L = rng.uniform(0.012, 0.026)
        jag = 0.02 * np.sin(rho * 1400.0 + k * 1.3) + 0.012 * np.sin(rho * 3100.0 + k * 2.1)
        dth = np.angle(np.exp(1j * (th - th_k - jag)))
        dist = rho * np.abs(dth)
        frac = np.maximum(frac, np.exp(-(dist / 0.0012) ** 2) * _smoothstep(L, L * 0.7, rho) * (rho > 0.002))
    r_ring = 0.0065 + 0.0005 * np.sin(th * 5.0)
    frac = np.maximum(frac, np.exp(-((rho - r_ring) / 0.001) ** 2) * (np.sin(th * 3.0 + 1.0) > -0.6))
    frac = np.maximum(frac, _smoothstep(r_ring * 1.1, r_ring * 0.7, rho))       # comminuted centre
    breach = _smoothstep(0.0032, 0.0026, rho * (1.0 + 0.15 * np.sin(th * 7.0)))
    depress = 0.0016 * _smoothstep(r_ring, r_ring * 0.8, rho) + 0.004 * breach
    blood = np.clip(0.3 * np.exp(-(rho / 0.008) ** 2) * (0.6 + 0.4 * _wave_noise(v, 300.0, 22))
                    + 0.6 * breach + 0.25 * frac, 0, 1)
    _set_verts(ob, v - n * depress[:, None])
    _point_attr(ob, "gore_fracture", frac)
    _point_attr(ob, "gore_wound", breach)
    _point_attr(ob, "gore_blood", blood)
    return ob


def scene_gore(out_dir, dried=False, close=False):
    """Gore attribute test: wound rings, torn rim, streaks, bruise, burn, fractured bone."""
    _clear_test_scene()
    ctrl = ghc.ensure_controls()
    ctrl["blood_age"] = 0.0
    mats = build_materials()
    ctrl["blood_age"] = 1.0 if dried else 0.0       # after building: exercises the drivers
    ghc.setup_stage()
    _, info = _gore_head(mats["GH_Skin"])
    _drip_tubes(info, mats["GH_Blood"])
    _gore_bone(mats["GH_Bone"], (0.092, 0.03, -0.012))
    if close:
        cam = ghc.add_camera("MT_Cam", (-0.08, -0.30, 0.06), (-0.012, -0.06, 0.004), 85.0)
        name = "materials_gore_close.png"
    else:
        cam = ghc.add_camera("MT_Cam", (0.03, -0.52, 0.06), (0.03, 0.0, 0.0), 85.0)
        name = "materials_dried.png" if dried else "materials_gore_test.png"
    path = _render(os.path.join(out_dir, name), cam, SAMPLES, (RES, RES))
    ctrl["blood_age"] = 0.0
    return path


def scene_eye(out_dir):
    """Close-up of the eyeball: refracted iris under the cornea, veiny sclera."""
    _clear_test_scene()
    mats = build_materials()
    ghc.setup_stage()
    eye = _eye_mesh("S_Eye", (0.0, 0.0, 0.0), mats["GH_Eye"])
    eye.rotation_euler = (math.radians(4), 0.0, math.radians(-14))
    cam = ghc.add_camera("MT_Cam", (-0.030, -0.085, 0.018), (0.0, 0.0, 0.0), 85.0)
    return _render(os.path.join(out_dir, "materials_eye.png"), cam, SAMPLES, (RES, RES))


def scene_head(out_dir):
    """The real anatomy with these materials (skipped when anatomy.py is unusable)."""
    _clear_test_scene()
    try:
        import anatomy
        objs = anatomy.build_anatomy()
    except Exception as exc:  # noqa: BLE001
        print("[materials] anatomy.py not usable, head render skipped:", exc)
        return []
    mats = build_materials()
    assign_materials(objs, mats)
    ghc.setup_stage()
    loc, tgt = ghc.VIEWS["three_q"]
    cam = ghc.add_camera("MT_Cam_head", loc, tgt, 85.0)
    paths = [_render(os.path.join(out_dir, "materials_head.png"), cam, SAMPLES, (RES, RES))]
    cam = ghc.add_camera("MT_Cam_eye", (-0.075, -0.30, 0.05), (0.022, -0.075, 0.018), 85.0)
    paths.append(_render(os.path.join(out_dir, "materials_head_eye.png"), cam, SAMPLES, (RES, RES)))
    return paths


def _cli_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    only, out_dir, head = None, ghc.RENDER_DIR, True
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == "--only":
            only = set(argv[i + 1].split(","))
            i += 1
        elif a == "--out":
            out_dir = argv[i + 1]
            i += 1
        elif a == "--no-head":
            head = False
        elif a in ("--samples", "--res"):
            globals()["SAMPLES" if a == "--samples" else "RES"] = int(argv[i + 1])
            i += 1
        i += 1
    return only, out_dir, head


def main():
    only, out_dir, head = _cli_args()
    want = (lambda k: only is None or k in only)  # noqa: E731
    if want("lookdev"):
        print(scene_lookdev(out_dir))
    if want("gore"):
        print(scene_gore(out_dir))
    if want("dried"):
        print(scene_gore(out_dir, dried=True))
    if want("close"):
        print(scene_gore(out_dir, close=True))
    if want("eye"):
        print(scene_eye(out_dir))
    if head and want("head"):
        print(scene_head(out_dir))


if __name__ == "__main__":
    main()
