"""Layered, live gore system for the procedural gore head (Blender 5.x).

Wounds are placed as empties in the `GH_Hits_*` collections. One shared
geometry-nodes group (`GH_Gore`) with a `Layer` setting runs as the last
modifier on every damageable layer. It reads the hit empties live through
Collection Info nodes, so dragging, rotating or scaling an empty updates the
wound immediately; nothing is baked from Python.

Per layer the group:
  1. reads the hits of every kind and ray-casts each one onto this layer,
  2. locally refines the mesh around the wounds (creased Catmull-Clark patch),
  3. evaluates the wound fields hit by hit (hole distance, displacement,
     wall direction, wound / edge / blood / bruise / burn / fracture),
  4. displaces, cuts the holes, snaps the rims onto the ragged outline and
     extrudes thick wound walls toward the next layer,
  5. adds extra geometry: blood drips and spatter on the skin, bone chips on
     the skull, knocked-out teeth,
  6. writes the `gore_*` point attributes from the contract.

Run `python3 gore.py` for the test renders and `verify_gore()`.
"""
import math
import os
import sys
import time

import bpy
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_common as ghc  # noqa: E402

KINDS = ("bullet", "exit", "slash", "blunt", "burn")
HITS_ROOT = "GH_Hits"
HIT_COLLECTIONS = {k: f"GH_Hits_{k.capitalize()}" for k in KINDS}
GROUP_NAME = "GH_Gore"
MOD_NAME = "GH_Gore"

# Layer ids used by the shared node group's "Layer" input.
LAYER_SKIN, LAYER_MUSCLE, LAYER_SKULL, LAYER_JAW, LAYER_BRAIN, LAYER_EYE, LAYER_TEETH, LAYER_GUMS = range(8)
LAYERS = {
    "GH_Skin": LAYER_SKIN,
    "GH_Muscle": LAYER_MUSCLE,
    "GH_Skull": LAYER_SKULL,
    "GH_Jaw": LAYER_JAW,
    "GH_Brain": LAYER_BRAIN,
    "GH_Eye_L": LAYER_EYE,
    "GH_Eye_R": LAYER_EYE,
    "GH_Teeth_Upper": LAYER_TEETH,
    "GH_Teeth_Lower": LAYER_TEETH,
    "GH_Gums": LAYER_GUMS,
}

# Global controls that drive the modifiers (materials drive the others).
DRIVEN_CONTROLS = ("damage", "bleed", "drip_time", "bruising", "swelling")

ATTRS = ("gore_wound", "gore_depth", "gore_edge", "gore_blood",
         "gore_bruise", "gore_burn", "gore_fracture")


# ---------------------------------------------------------------------------
# Tiny node-graph DSL
# ---------------------------------------------------------------------------
# Building a large node graph socket by socket is unreadable, so the gore
# groups are written with a small expression layer: `F` wraps an output socket
# and overloads arithmetic, `NodeTree` creates nodes and wires either sockets
# or constants into them.

_VEC_TYPES = {'VECTOR'}


def _is_vec(x):
    if isinstance(x, F):
        return x.s.type in _VEC_TYPES
    return isinstance(x, (tuple, list, Vector)) and len(x) == 3


class F:
    """A node output socket with operator overloading (float or vector)."""
    __slots__ = ("t", "s")

    def __init__(self, tree, sock):
        self.t = tree
        self.s = sock

    # arithmetic -----------------------------------------------------------
    def __add__(self, o): return self.t.op('ADD', self, o)
    def __radd__(self, o): return self.t.op('ADD', o, self)
    def __sub__(self, o): return self.t.op('SUBTRACT', self, o)
    def __rsub__(self, o): return self.t.op('SUBTRACT', o, self)
    def __mul__(self, o): return self.t.op('MULTIPLY', self, o)
    def __rmul__(self, o): return self.t.op('MULTIPLY', o, self)
    def __truediv__(self, o): return self.t.op('DIVIDE', self, o)
    def __rtruediv__(self, o): return self.t.op('DIVIDE', o, self)
    def __neg__(self): return self.t.op('MULTIPLY', self, -1.0)
    def __pow__(self, o): return self.t.math('POWER', self, o)

    # vector helpers ---------------------------------------------------------
    @property
    def x(self): return self.t.sep(self)[0]
    @property
    def y(self): return self.t.sep(self)[1]
    @property
    def z(self): return self.t.sep(self)[2]
    def dot(self, o): return self.t.vmath('DOT_PRODUCT', self, o)
    def cross(self, o): return self.t.vmath('CROSS_PRODUCT', self, o)
    def length(self): return self.t.vmath('LENGTH', self)
    def normalize(self): return self.t.vmath('NORMALIZE', self)

    # float helpers ----------------------------------------------------------
    def abs(self): return self.t.vmath('ABSOLUTE', self) if _is_vec(self) else self.t.math('ABSOLUTE', self)
    def sqrt(self): return self.t.math('SQRT', self)
    def max(self, o): return self.t.op('MAXIMUM', self, o)
    def min(self, o): return self.t.op('MINIMUM', self, o)
    def sin(self): return self.t.math('SINE', self)
    def cos(self): return self.t.math('COSINE', self)
    def clamp(self, lo=0.0, hi=1.0): return self.t.clamp(self, lo, hi)
    def lt(self, o): return self.t.compare('LESS_THAN', self, o)
    def gt(self, o): return self.t.compare('GREATER_THAN', self, o)


class NodeTree:
    """Creates (or rebuilds) a geometry node group and offers node helpers."""

    def __init__(self, name, inputs=(), outputs=(), modifier=False, description=""):
        ng = bpy.data.node_groups.get(name)
        if ng is None:
            ng = bpy.data.node_groups.new(name, 'GeometryNodeTree')
        ng.nodes.clear()
        ng.interface.clear()
        ng.is_modifier = modifier
        ng.description = description
        self.ng = ng
        self.nodes = ng.nodes
        self.links = ng.links
        self._sep_cache = {}
        self._const_cache = {}
        self.sockets = {}
        for spec in inputs:
            self._add_socket('INPUT', *spec)
        for spec in outputs:
            self._add_socket('OUTPUT', *spec)
        self.gin = self.nodes.new('NodeGroupInput')
        self.gout = self.nodes.new('NodeGroupOutput')

    def _add_socket(self, in_out, name, stype, default=None, lo=None, hi=None, desc=""):
        s = self.ng.interface.new_socket(name=name, in_out=in_out, socket_type=stype)
        if default is not None:
            s.default_value = default
        if lo is not None:
            s.min_value = lo
        if hi is not None:
            s.max_value = hi
        if desc:
            s.description = desc
        if in_out == 'INPUT':
            self.sockets[name] = s
        return s

    # -- wiring -------------------------------------------------------------
    @staticmethod
    def _find(sockets, key):
        if isinstance(key, int):
            return sockets[key]
        for s in sockets:
            if s.identifier == key:
                return s
        for s in sockets:
            if s.name == key and s.enabled:
                return s
        for s in sockets:
            if s.name == key:
                return s
        raise KeyError(key)

    def wire(self, node, key, val):
        """Connect `val` (F / socket / node / constant) to input `key` of `node`."""
        if val is None:
            return
        sock = self._find(node.inputs, key)
        if isinstance(val, F):
            val = val.s
        if isinstance(val, bpy.types.Node):
            val = val.outputs[0]
        if isinstance(val, bpy.types.NodeSocket):
            self.links.new(val, sock)
        else:
            if isinstance(val, (tuple, list, Vector)) and sock.type in ('VALUE', 'INT'):
                raise TypeError(f"vector constant into scalar socket {node.bl_idname}.{key}")
            if sock.type == 'VECTOR' and isinstance(val, (int, float)):
                val = (val, val, val)
            sock.default_value = val

    def node(self, idname, ins=None, **props):
        """Create a node, set properties, wire inputs. Returns the node."""
        n = self.nodes.new(idname)
        for k, v in props.items():
            setattr(n, k, v)
        if ins:
            for k, v in (ins.items() if isinstance(ins, dict) else enumerate(ins)):
                self.wire(n, k, v)
        return n

    def out(self, node, key=0):
        """Output socket of a node as F."""
        return F(self, self._find(node.outputs, key))

    # -- group interface ------------------------------------------------------
    def inp(self, name):
        return F(self, self.gin.outputs[name])

    def result(self, name, val):
        self.wire(self.gout, name, val)

    # -- math -----------------------------------------------------------------
    def math(self, op, a, b=None, c=None):
        n = self.node('ShaderNodeMath', operation=op)
        self.wire(n, 0, a)
        self.wire(n, 1, b)
        self.wire(n, 2, c)
        return F(self, n.outputs[0])

    def vmath(self, op, a, b=None, c=None, scale=None):
        n = self.node('ShaderNodeVectorMath', operation=op)
        self.wire(n, 0, a)
        self.wire(n, 1, b)
        self.wire(n, 2, c)
        self.wire(n, 'Scale', scale)
        if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE'):
            return F(self, n.outputs['Value'])
        return F(self, n.outputs['Vector'])

    def op(self, op, a, b):
        """Binary op on floats or vectors, promoting float*vector to SCALE."""
        va, vb = _is_vec(a), _is_vec(b)
        if not (va or vb):
            return self.math(op, a, b)
        if op == 'MULTIPLY' and va != vb:
            v, f = (a, b) if va else (b, a)
            return self.vmath('SCALE', v, scale=f)
        if op == 'DIVIDE' and va and not vb:
            inv = 1.0 / b if isinstance(b, (int, float)) else self.math('DIVIDE', 1.0, b)
            return self.vmath('SCALE', a, scale=inv)
        return self.vmath(op, a, b)

    def sep(self, v):
        key = v.s.as_pointer()
        if key not in self._sep_cache:
            n = self.node('ShaderNodeSeparateXYZ', [v])
            self._sep_cache[key] = tuple(F(self, o) for o in n.outputs)
        return self._sep_cache[key]

    def vec(self, x=0.0, y=0.0, z=0.0):
        n = self.node('ShaderNodeCombineXYZ', {'X': x, 'Y': y, 'Z': z})
        return F(self, n.outputs[0])

    def clamp(self, x, lo=0.0, hi=1.0):
        return F(self, self.node('ShaderNodeClamp', {'Value': x, 'Min': lo, 'Max': hi}).outputs[0])

    def smooth(self, e0, e1, x):
        """Smoothstep of x from e0 to e1 (0..1, clamped; e0 > e1 flips it)."""
        n = self.node('ShaderNodeMapRange', {'Value': x, 'From Min': e0, 'From Max': e1,
                                             'To Min': 0.0, 'To Max': 1.0},
                      interpolation_type='SMOOTHSTEP', clamp=True)
        return F(self, n.outputs['Result'])

    def lin(self, x, a, b, c=0.0, d=1.0, clamp=True):
        """Linear remap of x from [a, b] to [c, d]."""
        n = self.node('ShaderNodeMapRange', {'Value': x, 'From Min': a, 'From Max': b,
                                             'To Min': c, 'To Max': d}, clamp=clamp)
        return F(self, n.outputs['Result'])

    def mix(self, a, b, f):
        if _is_vec(a) or _is_vec(b):
            n = self.node('ShaderNodeMix', {'Factor_Float': f, 'A_Vector': a, 'B_Vector': b},
                          data_type='VECTOR', clamp_factor=True)
            return F(self, n.outputs[1])
        n = self.node('ShaderNodeMix', {'Factor_Float': f, 'A_Float': a, 'B_Float': b},
                      data_type='FLOAT', clamp_factor=True)
        return F(self, n.outputs[0])

    def compare(self, op, a, b, dtype='FLOAT'):
        if dtype == 'INT':
            n = self.node('FunctionNodeCompare', {'A_INT': a, 'B_INT': b}, data_type='INT', operation=op)
        else:
            n = self.node('FunctionNodeCompare', {'A': a, 'B': b}, data_type='FLOAT', operation=op)
        return F(self, n.outputs[0])

    def bool(self, op, a, b=None):
        n = self.node('FunctionNodeBooleanMath', operation=op)
        self.wire(n, 0, a)
        self.wire(n, 1, b)
        return F(self, n.outputs[0])

    def imath(self, op, a, b=None):
        n = self.node('FunctionNodeIntegerMath', operation=op)
        self.wire(n, 0, a)
        self.wire(n, 1, b)
        return F(self, n.outputs[0])

    def switch(self, cond, false, true, itype='FLOAT'):
        n = self.node('GeometryNodeSwitch', {'Switch': cond, 'False': false, 'True': true}, input_type=itype)
        return F(self, n.outputs[0])

    def pick(self, index, values, dtype='FLOAT'):
        """Index Switch over a list of constants or sockets."""
        n = self.node('GeometryNodeIndexSwitch', data_type=dtype)
        while len(n.index_switch_items) < len(values):
            n.index_switch_items.new()
        self.wire(n, 'Index', index)
        for i, v in enumerate(values):
            self.wire(n, f"Item_{i}", v)
        return F(self, n.outputs[0])

    # -- geometry helpers -----------------------------------------------------
    def pos(self):
        return F(self, self.node('GeometryNodeInputPosition').outputs[0])

    def normal(self):
        return F(self, self.node('GeometryNodeInputNormal').outputs[0])

    def index(self):
        return F(self, self.node('GeometryNodeInputIndex').outputs[0])

    def attr(self, name, dtype='FLOAT'):
        n = self.node('GeometryNodeInputNamedAttribute', {'Name': name}, data_type=dtype)
        return F(self, n.outputs[0])

    def store(self, geo, name, value, dtype='FLOAT', domain='POINT', sel=None):
        n = self.node('GeometryNodeStoreNamedAttribute', {'Geometry': geo, 'Selection': sel,
                                                          'Name': name, 'Value': value},
                      data_type=dtype, domain=domain)
        return F(self, n.outputs[0])

    def sample(self, geo, value, index, dtype='FLOAT', domain='POINT'):
        n = self.node('GeometryNodeSampleIndex', {'Geometry': geo, 'Value': value, 'Index': index},
                      data_type=dtype, domain=domain)
        return F(self, n.outputs[0])

    def rand(self, lo, hi, id_=None, seed=0, dtype='FLOAT'):
        if dtype == 'FLOAT':
            ins = {'Min_001': lo, 'Max_001': hi, 'ID': id_, 'Seed': seed}
            idx = 1
        elif dtype == 'INT':
            ins = {'Min_002': lo, 'Max_002': hi, 'ID': id_, 'Seed': seed}
            idx = 2
        else:
            ins = {'Min': lo, 'Max': hi, 'ID': id_, 'Seed': seed}
            idx = 0
        n = self.node('FunctionNodeRandomValue', ins, data_type=dtype)
        return F(self, n.outputs[idx])

    def noise(self, vec, scale=1.0, detail=2.0, rough=0.5, dist=0.0, signed=True, color=False):
        """3D noise; signed=True maps to roughly -1..1."""
        n = self.node('ShaderNodeTexNoise', {'Vector': vec, 'Scale': scale, 'Detail': detail,
                                             'Roughness': rough, 'Distortion': dist})
        if color:
            c = F(self, n.outputs['Color'])
            c = self.op('SUBTRACT', self._color_to_vec(c), (0.5, 0.5, 0.5)) * 2.0 if signed else c
            return c
        f = F(self, n.outputs['Factor'])
        return (f - 0.5) * 2.0 if signed else f

    def _color_to_vec(self, c):
        # a color socket linked into a vector math socket converts implicitly
        return self.vmath('ADD', c, (0.0, 0.0, 0.0))

    def voronoi(self, vec, scale=1.0, feature='F1', rand=1.0, dims='3D', w=None):
        n = self.node('ShaderNodeTexVoronoi', {'Vector': vec, 'Scale': scale, 'Randomness': rand, 'W': w},
                      feature=feature, voronoi_dimensions=dims)
        return n

    def group(self, tree, ins=None):
        n = self.node('GeometryNodeGroup')
        n.node_tree = tree.ng if isinstance(tree, NodeTree) else tree
        if ins:
            for k, v in ins.items():
                self.wire(n, k, v)
        return n

    # -- layout -----------------------------------------------------------------
    def layout(self):
        """Arrange nodes in columns by link depth so the graph is browsable."""
        depth = {n: 0 for n in self.nodes}
        incoming = {n: [] for n in self.nodes}
        for lk in self.links:
            incoming[lk.to_node].append(lk.from_node)
        for _ in range(60):
            changed = False
            for n in self.nodes:
                for src in incoming[n]:
                    if depth[src] + 1 > depth[n] and depth[src] < 400:
                        depth[n] = depth[src] + 1
                        changed = True
            if not changed:
                break
        cols = {}
        for n in self.nodes:
            cols.setdefault(depth[n], []).append(n)
        for d, ns in cols.items():
            for i, n in enumerate(ns):
                n.location = (d * 230.0, -i * 190.0)


# ---------------------------------------------------------------------------
# Per-layer constants (indexed by the Layer input)
# ---------------------------------------------------------------------------
#                 skin    muscle  skull   jaw     brain   eye     teeth   gums
LAYER_Z       = [0.0,    0.004,  0.008,  0.008,  0.017,  0.0,    0.010,  0.008]   # nominal depth below skin (m)
LAYER_WALL    = [0.0046, 0.0042, 0.0066, 0.0055, 0.0,    0.0030, 0.0,    0.0025]  # wall length toward next layer (m)
LAYER_D0      = [0.0,    0.6,    1.0,    1.0,    1.0,    0.3,    1.0,    0.6]     # gore_depth at the top of a wall
LAYER_D1      = [0.6,    0.95,   1.0,    1.0,    1.0,    0.5,    1.0,    0.7]     # gore_depth at the bottom of a wall
LAYER_SURF_D  = [0.12,   0.6,    1.0,    1.0,    1.0,    0.3,    1.0,    0.6]     # gore_depth of exposed surface
LAYER_TOL_IN  = [0.012,  0.012,  0.016,  0.016,  0.035,  0.014,  0.05,   0.03]    # how far below the impact a layer is affected
LAYER_TOL_OUT = [0.016,  0.016,  0.010,  0.010,  0.010,  0.016,  0.03,   0.02]
LAYER_IS_BONE = [0, 0, 1, 1, 0, 0, 0, 0]
LAYER_IS_SOFT = [1, 1, 0, 0, 0, 0, 0, 1]
# depth (hit scale.z * damage) at which the layer is opened, and at which the
# layer above it is opened (so this layer's surface is exposed)
OPEN_AT       = [0.02,   0.35,   0.78,   0.78,   9.0,    0.05,   9.0,    0.3]
ABOVE_OPEN_AT = [9.0,    0.02,   0.35,   0.35,   0.78,   9.0,    9.0,    9.0]
# hole radius factors relative to the skin hole
BULLET_RF     = [1.0,    0.85,   0.8,    0.8,    1.0,    1.0,    1.0,    1.0]
EXIT_RF       = [1.0,    0.8,    0.62,   0.62,   1.0,    0.9,    1.0,    1.0]
ABOVE_RF      = [1.0,    1.0,    0.85,   0.85,   0.8,    1.0,    1.0,    1.0]

KIND_INPUTS = (
    ("Local", 'NodeSocketVector', None, None, None, "Vertex position in the hit frame, relative to this layer's impact"),
    ("Noise Pos", 'NodeSocketVector', None, None, None, "Position used for noise (offset per hit)"),
    ("Size", 'NodeSocketFloat', 1.0),
    ("Elongation", 'NodeSocketFloat', 1.0),
    ("Depth", 'NodeSocketFloat', 0.6),
    ("Seed", 'NodeSocketFloat', 0.0),
    ("Layer", 'NodeSocketInt', 0),
    ("Down", 'NodeSocketVector', None, None, None, "World -Z expressed in the hit frame"),
    ("Swelling", 'NodeSocketFloat', 0.5),
    ("Bruising", 'NodeSocketFloat', 0.6),
    ("Bleed", 'NodeSocketFloat', 0.7),
)
KIND_OUTPUTS = (
    ("Cut", 'NodeSocketFloat'),        # signed distance to the hole outline (m), > 0 inside the hole
    ("Disp", 'NodeSocketVector'),      # displacement in the hit frame
    ("Disp N", 'NodeSocketFloat'),     # displacement along the vertex normal
    ("Wall", 'NodeSocketVector'),      # full wall extrusion vector in the hit frame
    ("Out", 'NodeSocketVector'),       # unit direction away from the hole (hit frame)
    ("Wound", 'NodeSocketFloat'),
    ("Edge", 'NodeSocketFloat'),
    ("Blood", 'NodeSocketFloat'),
    ("Bruise", 'NodeSocketFloat'),
    ("Burn", 'NodeSocketFloat'),
    ("Fracture", 'NodeSocketFloat'),
)

TAU = 2.0 * math.pi


class _KindCtx:
    """Shared inputs and helpers inside one wound-kind subgroup."""

    def __init__(self, t):
        self.t = t
        self.L = t.inp("Local")
        self.u, self.v, self.w = self.L.x, self.L.y, self.L.z
        self.np = t.inp("Noise Pos")
        self.s = t.inp("Size")
        self.e = t.inp("Elongation")
        self.D = t.inp("Depth")
        self.seed = t.inp("Seed")
        self.layer = t.inp("Layer")
        self.down = t.inp("Down")
        self.rho = (self.u * self.u + self.v * self.v).sqrt()
        self.theta = t.math('ARCTAN2', self.v, self.u)
        inv = 1.0 / self.rho.max(1e-6)
        self.radial = t.vec(self.u * inv, self.v * inv, 0.0)   # unit, away from the axis

    def lc(self, values, dtype='FLOAT'):
        """Per-layer constant."""
        return self.t.pick(self.layer, values, dtype)

    def is_layer(self, layer_id):
        return self.t.switch(self.t.compare('EQUAL', self.layer, layer_id, 'INT'), 0.0, 1.0)

    def opened(self, at):
        return self.t.smooth(at, at + 0.02, self.D)

    def teardrop(self, q, radius, stretch=3.2):
        """Normalized distance for a blood pool that runs downward (world -Z)."""
        t = self.t
        dz = q.dot(self.down)                       # > 0 below the source
        lat = (q - self.down * dz).length()
        along = dz.max(0.0) / stretch + (-dz).max(0.0) * 1.4
        return (lat * lat + along * along).sqrt() / radius

    def cracks(self, R, n_around=7.0, width=0.0005, rand=0.9):
        """Polar Voronoi crack network around the axis.

        Returns (line, plate): line = 1 on crack lines (width in meters),
        plate = random 0..1 per bone plate between the cracks.
        """
        t = self.t
        lr = t.math('LOGARITHM', self.rho.max(1e-5) / R, math.e)
        pc = t.vec(self.theta * (n_around / TAU), lr * 1.7, self.seed * 9.1)
        # jagged cracks: wobble the lookup
        pc = pc + t.noise(self.np * 350.0, detail=2.0, color=True) * 0.12
        edge = t.out(t.voronoi(pc, 1.0, 'DISTANCE_TO_EDGE', rand), 'Distance')
        cell = t.out(t.voronoi(pc, 1.0, 'F1', rand), 'Color')
        # convert the world width to polar units (angular cell width grows with rho)
        wpolar = width / (self.rho.max(1e-4) * (TAU / n_around))
        line = t.smooth(wpolar, wpolar * 0.3, edge)
        plate = t.sep(t.vmath('ADD', cell, (0, 0, 0)))[0]
        return line, plate


def _kind_tree(name, desc):
    return NodeTree(name, KIND_INPUTS, KIND_OUTPUTS, description=desc)


def _finish_kind(t, cut, disp=None, dispn=0.0, wall=None, out=None, wound=0.0, edge=0.0,
                 blood=0.0, bruise=0.0, burn=0.0, fracture=0.0):
    t.result("Cut", cut)
    t.result("Disp", disp if disp is not None else (0.0, 0.0, 0.0))
    t.result("Disp N", dispn)
    t.result("Wall", wall if wall is not None else (0.0, 0.0, 0.0))
    t.result("Out", out if out is not None else (1.0, 0.0, 0.0))
    for k, v in (("Wound", wound), ("Edge", edge), ("Blood", blood), ("Bruise", bruise),
                 ("Burn", burn), ("Fracture", fracture)):
        t.result(k, v)
    t.layout()


def _build_bullet():
    """Entry wound: small round hole, abrasion collar, bevelled bone, brain crater."""
    t = _kind_tree("GH_Gore_Bullet", "Bullet entry wound fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_bone = c.lc(LAYER_IS_BONE)
    is_skin = c.is_layer(LAYER_SKIN)
    is_brain = c.is_layer(LAYER_BRAIN)
    opened = c.opened(c.lc(OPEN_AT))
    r0 = s * 0.0045 * c.lc(BULLET_RF)
    rag = t.noise(c.np * 900.0, detail=2.0)
    # inward bevel: the inner table of the skull breaks out wider (cone)
    r = r0 * (1.0 + rag * 0.12) + is_bone * (-c.w).max(0.0) * 0.8
    cut = t.switch(opened.gt(0.5), -1.0, r - c.rho)
    # abrasion collar (skin) / torn rim (deeper layers)
    collar_w = s * 0.0026 * (1.0 + t.noise(c.np * 400.0) * 0.35)
    edge = t.smooth(r + collar_w, r, c.rho) * is_skin + t.smooth(r + 0.0012, r, c.rho) * (1.0 - is_skin)
    edge = edge * opened
    # inverted rim: entry wounds are pushed slightly inward
    dent = t.smooth(r * 2.6, r, c.rho) * opened * is_skin * s * -0.0007
    # tissue exposed under the hole of the layer above
    r_above = s * 0.0045 * c.lc(ABOVE_RF) * 1.1
    exposed = t.smooth(r_above * 1.2, r_above * 0.8, c.rho) * c.opened(c.lc(ABOVE_OPEN_AT))
    wound = (t.smooth(r + 0.0005, r, c.rho) * opened).max(exposed)
    # blood: small pool running down on the skin, the whole exposed area below
    bleed = t.inp("Bleed")
    pool_r = s * 0.0055 * (0.5 + bleed)
    pool = t.smooth(1.0, 0.45, c.teardrop(c.L, pool_r) + t.noise(c.np * 260.0) * 0.3) * bleed * opened
    blood = (pool * is_skin).max(exposed * 0.9).max(edge * 0.6 * bleed)
    # brain: deep crater / tunnel along the track
    crat = t.smooth(0.88, 0.97, D) * is_brain
    rc = s * 0.0068
    x = (c.rho / rc).min(1.0)
    prof = (1.0 - x * x) ** 2.0
    lump = 1.0 + t.noise(c.np * 500.0) * 0.35
    crater_z = crat * prof * lump * (0.008 + 0.014 * s) * -1.0
    brain_w = t.smooth(1.25, 0.8, c.rho / rc) * crat
    wound = wound.max(brain_w)
    blood = blood.max(brain_w)
    disp = t.vec(0.0, 0.0, dent + crater_z)
    # walls: straight down with a little convergence; bone flares outward (bevel)
    tw = c.lc(LAYER_WALL)
    wall = c.radial * (is_bone * tw * 0.8 - (1.0 - is_bone) * r * 0.12) + t.vec(0.0, 0.0, -tw)
    _finish_kind(t, cut, disp=disp, wall=wall, out=c.radial, wound=wound, edge=edge, blood=blood)
    return t


def _build_exit():
    """Exit wound: large star-shaped tear with everted flaps, jagged bone."""
    t = _kind_tree("GH_Gore_Exit", "Exit wound fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_bone = c.lc(LAYER_IS_BONE)
    is_skin = c.is_layer(LAYER_SKIN)
    is_brain = c.is_layer(LAYER_BRAIN)
    evert_amt = c.lc([1.0, 0.55, 0.35, 0.35, 0.0, 0.0, 0.0, 0.3])
    opened = c.opened(c.lc(OPEN_AT))
    R = s * 0.014 * c.lc(EXIT_RF)
    # star: 5-7 tears radiating out; each tear has its own length
    n_tears = t.math('FLOOR', c.seed * 2.99) + 5.0
    a = c.theta * n_tears * 0.5 + c.seed * 17.0
    star = t.math('ABSOLUTE', a.cos()) ** 3.0
    ring = t.vec(c.theta.cos() * 1.3, c.theta.sin() * 1.3, c.seed * 11.0)
    tear_len = 0.6 + t.noise(ring, detail=1.0, signed=False) * 0.9
    rag = t.noise(c.np * 1100.0, detail=2.0)
    jag = t.noise(c.np * 2200.0, detail=1.0)           # bone breaks with sharp small teeth
    r = R * (0.38 + 0.62 * star * tear_len) + s * 0.0009 * rag + is_bone * R * 0.16 * jag
    # outward bevel on bone: the outer table is blown out wider
    r = r + is_bone * (c.w + c.lc(LAYER_WALL)).max(0.0) * 0.6
    cut = t.switch(opened.gt(0.5), -1.0, r - c.rho)
    d_out = c.rho - r
    flap = t.smooth(R * 0.95, 0.0, d_out) * opened
    tip = 1.0 - star                                    # flaps sit between the tears
    curl = 0.75 + t.noise(c.np * 300.0) * 0.45
    lift = flap * flap * s * 0.0062 * (0.45 + 0.85 * tip) * curl * evert_amt
    disp_evert = t.vec(0.0, 0.0, lift) + c.radial * (lift * 0.55)
    edge_lift = s * 0.0062 * (0.45 + 0.85 * tip) * curl * evert_amt * opened
    # brain: pulped crater with lumps pushed out toward the hole
    crat = t.smooth(0.84, 0.95, D) * is_brain
    rc = s * 0.013
    x = (c.rho / rc).min(1.0)
    pulp = t.noise(c.np * 420.0, detail=3.0)
    crater_z = crat * ((1.0 - x * x) ** 2.0) * (s * -0.009 + pulp * 0.004)
    brain_w = t.smooth(1.2, 0.75, c.rho / rc + pulp * 0.1) * crat
    disp = disp_evert + t.vec(0.0, 0.0, crater_z)
    # tissue exposure, torn edge, fracture
    r_above = s * 0.014 * c.lc(ABOVE_RF) * 0.8
    exposed = t.smooth(r_above * 1.25, r_above * 0.7, c.rho) * c.opened(c.lc(ABOVE_OPEN_AT))
    edge = t.smooth(s * 0.0035, 0.0, d_out) * opened
    wound = (t.smooth(0.0006, 0.0, d_out) * opened).max(exposed).max(brain_w)
    lines, _plate = c.cracks(R, n_around=8.0, width=0.00045)
    frac = lines * t.smooth(R * 3.0, R * 1.1, c.rho) * is_bone * opened
    frac = frac.max(t.smooth(s * 0.004, 0.0, d_out) * is_bone * opened)
    bleed = t.inp("Bleed")
    pool = t.smooth(1.0, 0.4, c.teardrop(c.L, s * 0.017 * (0.5 + bleed)) + t.noise(c.np * 200.0) * 0.3)
    blood = (pool * bleed * opened * is_skin).max(flap * (0.5 + 0.5 * bleed)).max(exposed).max(brain_w)
    tw = c.lc(LAYER_WALL)
    wall = t.vec(0.0, 0.0, -(tw + edge_lift)) + c.radial * (-(1.0 - is_bone) * R * 0.18 - is_bone * tw * 0.6)
    _finish_kind(t, cut, disp=disp, wall=wall, out=c.radial, wound=wound, edge=edge,
                 blood=blood, fracture=frac)
    return t


def _build_slash():
    """Laceration along local X: lens-shaped gash with V walls and gaping lips."""
    t = _kind_tree("GH_Gore_Slash", "Slash / laceration fields")
    c = _KindCtx(t)
    s, D, u, v = c.s, c.D, c.u, c.v
    is_skin = c.is_layer(LAYER_SKIN)
    is_bone = c.lc(LAYER_IS_BONE)
    is_brain = c.is_layer(LAYER_BRAIN)
    half_len = s * 0.012 * c.e
    tt = u / half_len
    lens = (1.0 - tt * tt).max(0.0) ** 0.65
    wob = t.noise(c.np * 240.0, detail=2.0)
    # the cut line wanders a little, the lips are torn slightly
    vc = v - s * 0.00045 * t.noise(t.vec(u * 90.0, c.seed * 5.0, 0.0), detail=1.0)
    hw = s * 0.0017 * (0.55 + 0.8 * D) * lens * (1.0 + wob * 0.22) + s * 0.00012 * t.noise(c.np * 1500.0)
    v_depth = D * 0.0135 + 0.0005                        # V bottom (below skin), 0.6 -> bone
    zl = c.lc(LAYER_Z)
    frac_l = (1.0 - zl / v_depth).max(0.0)
    hwl = hw * frac_l
    bone_ok = 1.0 - is_bone * (1.0 - t.smooth(0.88, 0.92, D))   # bone is only split by very deep chops
    opened = t.switch(t.bool('AND', zl.lt(v_depth), (1.0 - is_brain).gt(0.5)), 0.0, 1.0) * bone_ok
    av = t.math('ABSOLUTE', vc)
    cut = t.switch(opened.gt(0.5), -1.0, hwl - av)
    sgn = t.math('SIGN', vc)
    # gaping lips (skin), swollen slightly
    along = t.smooth(1.15, 0.75, t.math('ABSOLUTE', tt))
    gape = t.smooth(s * 0.0045, 0.0, av - hwl) * along * opened
    gape_amt = c.lc([1.0, 0.4, 0.0, 0.0, 0.0, 0.3, 0.0, 0.3])
    disp = t.vec(0.0, sgn * gape * s * 0.0007 * (0.5 + D) * gape_amt, gape * s * 0.0003 * gape_amt)
    # V walls converge to the centre line at the bottom of the cut
    z_bot = v_depth.min(zl + c.lc(LAYER_WALL))
    hw_bot = hw * (1.0 - z_bot / v_depth).max(0.0)
    wall = t.vec(0.0, sgn * (hw_bot - hwl), zl - z_bot)
    out = t.vec(0.0, sgn, 0.0)
    edge = t.smooth(s * 0.0011, 0.0, av - hwl) * along * opened * is_skin
    # bone scored by the blade
    score = t.smooth(0.55, 0.65, D) * is_bone * t.smooth(s * 0.0014, s * 0.0003, av) * t.smooth(1.05, 0.9, t.math('ABSOLUTE', tt))
    disp = disp + t.vec(0.0, 0.0, score * -0.0007)
    hw_skin = hw * 1.1
    exposed = t.smooth(hw_skin * 1.3 + 0.0003, hw_skin * 0.7, av) * along * t.switch(zl.lt(v_depth), 0.0, 1.0) * (1.0 - is_skin)
    wound = (t.smooth(0.0005, 0.0, av - hwl) * opened * along).max(exposed).max(score)
    bleed = t.inp("Bleed")
    q = t.vec(u - t.clamp(u, -half_len * 0.8, half_len * 0.8), vc, c.w)
    pool = t.smooth(1.0, 0.45, c.teardrop(q, s * 0.0045 * (0.5 + bleed)) + t.noise(c.np * 260.0) * 0.3)
    blood = (pool * bleed * opened * is_skin).max(exposed).max(score).max(edge * 0.7 * bleed)
    _finish_kind(t, cut, disp=disp, wall=wall, out=out, wound=wound, edge=edge, blood=blood, fracture=score)
    return t


def _build_blunt():
    """Blunt trauma: swelling, bruise, stellate split, depressed skull fracture."""
    t = _kind_tree("GH_Gore_Blunt", "Blunt trauma fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_skin = c.is_layer(LAYER_SKIN)
    is_muscle = c.is_layer(LAYER_MUSCLE)
    is_bone = c.lc(LAYER_IS_BONE)
    is_brain = c.is_layer(LAYER_BRAIN)
    soft = c.lc([1.0, 0.35, 0.0, 0.0, 0.0, 0.25, 0.0, 0.6])
    nl = t.noise(c.np * 120.0, detail=3.0)
    rsw = s * 0.022
    swell = t.inp("Swelling") * s * 0.0058 * t.math('EXPONENT', -(c.rho / rsw) ** 2.0) * (1.0 + nl * 0.25) * soft
    rb = s * 0.028
    bruise = t.smooth(1.1, 0.3, c.rho / rb + nl * 0.32) * (0.72 + 0.28 * t.noise(c.np * 420.0))
    bruise = bruise * t.inp("Bruising") * c.lc([1.0, 1.0, 0.0, 0.0, 0.0, 0.6, 0.0, 1.0])
    # stellate split: 3-5 thin tears from the centre (skin), smaller in muscle
    arms = t.math('FLOOR', c.seed * 2.99) + 3.0
    star = t.math('ABSOLUTE', (c.theta * arms * 0.5 + c.seed * 23.0).cos()) ** 22.0
    ring = t.vec(c.theta.cos() * 1.4, c.theta.sin() * 1.4, c.seed * 7.0)
    arm_len = s * 0.0105 * (0.5 + t.noise(ring, detail=1.0, signed=False) * 0.9)
    split_on = t.smooth(0.25, 0.45, D) * is_skin + t.smooth(0.55, 0.7, D) * is_muscle * 0.45
    r_split = (s * 0.0011 + arm_len * star) * split_on + s * 0.00025 * t.noise(c.np * 1300.0)
    cut_soft = t.switch(split_on.gt(0.05), -1.0, r_split - c.rho)
    # depressed skull fracture with radiating cracks
    dep_on = t.smooth(0.62, 0.85, D) * is_bone
    rd = s * 0.015
    lines, plate = c.cracks(rd, n_around=7.0, width=0.0005)
    inside = t.smooth(rd * 1.04, rd * 0.94, c.rho + nl * 0.0012)
    depress = dep_on * s * 0.0048 * inside * (0.4 + 0.6 * plate) * t.smooth(rd * 1.1, rd * 0.2, c.rho).max(0.35)
    ring_crack = t.smooth(0.0007, 0.0002, t.math('ABSOLUTE', c.rho - rd + nl * 0.0012))
    frac = (lines * t.smooth(rd * 2.8, rd * 0.9, c.rho)).max(ring_crack) * dep_on
    breach = t.smooth(0.94, 0.99, D) * is_bone
    cut_bone = t.switch(breach.gt(0.5), -1.0, s * 0.0045 * (1.0 + nl * 0.3) - c.rho)
    cut = cut_soft.max(cut_bone)
    disp = t.vec(0.0, 0.0, -depress - frac * dep_on * 0.0005)
    # blood: from the split, hematoma under the skin, contusion on the brain
    bleed = t.inp("Bleed")
    pool = t.smooth(1.0, 0.45, c.teardrop(c.L, s * 0.005 * (0.5 + bleed)) + nl * 0.3) * bleed * t.smooth(0.25, 0.45, D)
    hema = t.smooth(rsw * 1.1, rsw * 0.3, c.rho) * c.lc([0.0, 0.85, 0.35, 0.35, 0.0, 0.7, 0.0, 0.8])
    contusion = t.smooth(rd * 1.3, rd * 0.4, c.rho + nl * 0.002) * is_brain * t.smooth(0.5, 0.8, D)
    teeth_blood = t.smooth(s * 0.03, s * 0.01, c.rho) * c.is_layer(LAYER_TEETH) * t.smooth(0.2, 0.4, D)
    blood = (pool * is_skin).max(hema * t.smooth(0.2, 0.5, D)).max(contusion).max(teeth_blood)
    blood = blood.max(t.smooth(0.0008, 0.0, c.rho - r_split) * split_on * 0.8)
    edge = t.smooth(s * 0.0022, 0.0, c.rho - r_split) * split_on * is_skin
    # patterned abrasion ring of the striking surface
    edge = edge.max(t.smooth(s * 0.0022, 0.0, t.math('ABSOLUTE', c.rho - s * 0.009 + nl * 0.002)) * t.smooth(0.2, 0.5, D) * is_skin * 0.6)
    wound = (t.smooth(0.0005, 0.0, c.rho - r_split) * split_on).max(contusion * 0.5).max(frac * 0.4)
    wound = wound.max(t.smooth(s * 0.006, s * 0.0045, c.rho) * breach)
    tw = c.lc(LAYER_WALL)
    wall = t.vec(0.0, 0.0, -tw) - c.radial * (s * 0.0006)
    _finish_kind(t, cut, disp=disp, dispn=swell, wall=wall, out=c.radial, wound=wound, edge=edge,
                 blood=blood, bruise=bruise, fracture=frac)
    return t


def _build_burn():
    """Burn: charred shrunken centre, blister ring, peeling epidermis."""
    t = _kind_tree("GH_Gore_Burn", "Burn fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_skin = c.is_layer(LAYER_SKIN)
    R = s * 0.022
    rho_e = (c.u * c.u + (c.v / c.e) ** 2.0).sqrt()
    nl = t.noise(c.np * 90.0, detail=3.0)
    nh = t.noise(c.np * 650.0, detail=2.0)
    b = t.smooth(1.0, 0.42, rho_e / R + nl * 0.3 + nh * 0.05)
    char = t.smooth(0.55, 0.95, b)
    # charred, shrunken crust with fine crackle
    crust = t.out(t.voronoi(c.np, 700.0, 'DISTANCE_TO_EDGE', 1.0), 'Distance')
    crackle = t.smooth(0.08, 0.0, crust) * char
    dn = char * s * -0.0011 * (0.5 + D) + nh * char * 0.00025 - crackle * 0.00025
    # blisters in the partial-thickness ring
    ringb = t.smooth(0.1, 0.32, b) * t.smooth(0.8, 0.5, b)
    vor = t.voronoi(c.np, 230.0, 'F1', 1.0)
    vd = t.out(vor, 'Distance')
    vcol = t.sep(t.vmath('ADD', t.out(vor, 'Color'), (0, 0, 0)))
    keep = t.smooth(0.3, 0.45, vcol[0])
    brad = 0.26 + vcol[1] * 0.16
    dome = (1.0 - (vd / brad) ** 2.0).max(0.0).sqrt()
    blister = ringb * keep * dome * s * 0.0013
    # peeling epidermis: sloughed patches with curled, lifted rims
    pm = t.noise(c.np * 150.0 + t.vec(3.1, 1.7, 0.4), detail=2.0)
    ringp = t.smooth(0.22, 0.45, b) * t.smooth(0.97, 0.75, b)
    peel = t.smooth(0.10, 0.16, pm) * ringp
    peel_rim = t.smooth(0.04, 0.10, pm) * t.smooth(0.2, 0.12, pm) * ringp
    dn = dn + blister + peel_rim * s * 0.0007 - peel * s * 0.0003
    dn = dn * is_skin
    burn = b * c.lc([1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
    burn = burn.max(b * t.smooth(0.55, 0.8, D) * c.lc([0.0, 0.8, 0.6, 0.6, 0.0, 0.0, 0.0, 0.0]))
    wound = peel * is_skin
    edge = peel_rim * is_skin
    blood = peel * 0.3 * t.inp("Bleed") * is_skin
    _finish_kind(t, -1.0, dispn=dn, out=c.radial, wound=wound, edge=edge, blood=blood, burn=burn)
    return t


KIND_BUILDERS = {
    "bullet": _build_bullet,
    "exit": _build_exit,
    "slash": _build_slash,
    "blunt": _build_blunt,
    "burn": _build_burn,
}
