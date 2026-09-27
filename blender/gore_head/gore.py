"""Layered, live gore system for the procedural gore head (Blender 5.x).

Wounds are placed as empties in the `GH_Hits_*` collections (see CONTRACT.md:
location = impact, local -Z = direction into the head, local X = slash
direction, scale = (size, elongation, depth)). One shared geometry-nodes group
(`GH_Gore`) with a `Layer` setting runs as the last modifier on every
damageable layer. It reads the hit empties live through Collection Info nodes,
so dragging, rotating or scaling an empty updates the wound immediately;
nothing is baked from Python.

Per layer the group:
  1. reads the hits of every kind and ray-casts each one onto this layer,
  2. locally refines the mesh around the wounds (creased Catmull-Clark patch),
  3. evaluates the wound fields hit by hit (hole distance, displacement,
     wall direction, wound / edge / blood / bruise / burn / fracture),
  4. displaces, cuts the holes, snaps the rims onto the ragged outline and
     extrudes thick wound walls toward the next layer,
  5. adds extra geometry: blood rivulets on the skin (time-driven: blood
     only leaves a wound after its cavity has filled, from the lowest point
     of the rim) and blood welling up in the bed of bleeding cuts, clot blobs
     and tissue strands in the wounds, bone chips, knocked-out teeth, the
     broken-off mandible segment of a blast,
  6. writes the `gore_*` point attributes from the contract.

Typical use (after anatomy and materials):

    import gore
    gore.build_gore_system(objs, mats)       # modifiers + drivers + GH_Hits
    gore.add_hit("bullet", (0.01, -0.1, 0.07), depth=1.0)
    gore.add_hit("slash", (-0.06, -0.06, 0.0), elongation=2.5, roll=0.4)

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

KINDS = ("bullet", "exit", "slash", "blunt", "burn", "blast")
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
    # the mouth lining behind the lips and the tongue are soft tissue too: a
    # blow or shot through the mouth must open them as well, otherwise a hole
    # in the lips shows the untouched lining from behind
    "GH_MouthCavity": LAYER_MUSCLE,
    "GH_Tongue": LAYER_GUMS,
}
# layers whose wound walls use the object's own material
OWN_WALL_MATERIAL = ("GH_Tongue",)

# Global controls that drive the modifiers (materials drive the others).
DRIVEN_CONTROLS = ("damage", "bleed", "drip_time", "bruising", "swelling", "wound_age")

ATTRS = ("gore_wound", "gore_depth", "gore_edge", "gore_blood",
         "gore_bruise", "gore_burn", "gore_fracture", "gore_soot")


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
        """Group input socket `name` as F."""
        return F(self, self.gin.outputs[name])

    def result(self, name, val):
        """Connect `val` to group output `name`."""
        self.wire(self.gout, name, val)

    # -- math -----------------------------------------------------------------
    def math(self, op, a, b=None, c=None):
        """Float Math node."""
        n = self.node('ShaderNodeMath', operation=op)
        self.wire(n, 0, a)
        self.wire(n, 1, b)
        self.wire(n, 2, c)
        return F(self, n.outputs[0])

    def vmath(self, op, a, b=None, c=None, scale=None):
        """Vector Math node (DOT/LENGTH/DISTANCE return the float output)."""
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
        """Switch node: `true` where cond, else `false` (lazy for single values)."""
        n = self.node('GeometryNodeSwitch', {'Switch': cond, 'False': false, 'True': true}, input_type=itype)
        return F(self, n.outputs[0])

    def pick(self, index, values, dtype='FLOAT'):
        """Index Switch over a list of constants or sockets."""
        if all(isinstance(v, (int, float)) for v in values):
            key = ('pick', index.s.as_pointer(), tuple(values), dtype)
            if key in self._const_cache:
                return self._const_cache[key]
            self._const_cache[key] = None
            res = self._pick(index, values, dtype)
            self._const_cache[key] = res
            return res
        return self._pick(index, values, dtype)

    def _pick(self, index, values, dtype):
        n = self.node('GeometryNodeIndexSwitch', data_type=dtype)
        while len(n.index_switch_items) < len(values):
            n.index_switch_items.new()
        self.wire(n, 'Index', index)
        for i, v in enumerate(values):
            self.wire(n, f"Item_{i}", v)
        return F(self, n.outputs[0])

    # -- geometry helpers -----------------------------------------------------
    def _cached(self, key, make):
        if key not in self._const_cache:
            self._const_cache[key] = make()
        return self._const_cache[key]

    def pos(self):
        return self._cached('pos', lambda: F(self, self.node('GeometryNodeInputPosition').outputs[0]))

    def normal(self):
        return self._cached('normal', lambda: F(self, self.node('GeometryNodeInputNormal').outputs[0]))

    def index(self):
        return self._cached('index', lambda: F(self, self.node('GeometryNodeInputIndex').outputs[0]))

    def attr(self, name, dtype='FLOAT'):
        """Named attribute input (one node per name/type; fields are context free)."""
        return self._cached(('attr', name, dtype), lambda: F(self, self.node(
            'GeometryNodeInputNamedAttribute', {'Name': name}, data_type=dtype).outputs[0]))

    def store(self, geo, name, value, dtype='FLOAT', domain='POINT', sel=None):
        """Store Named Attribute; with `sel` only the selection is evaluated and written."""
        n = self.node('GeometryNodeStoreNamedAttribute', {'Geometry': geo, 'Selection': sel,
                                                          'Name': name, 'Value': value},
                      data_type=dtype, domain=domain)
        return F(self, n.outputs[0])

    def sample(self, geo, value, index, dtype='FLOAT', domain='POINT'):
        """Sample Index: `value` evaluated on `geo` at `index`."""
        n = self.node('GeometryNodeSampleIndex', {'Geometry': geo, 'Value': value, 'Index': index},
                      data_type=dtype, domain=domain)
        return F(self, n.outputs[0])

    def rand(self, lo, hi, id_=None, seed=0, dtype='FLOAT'):
        """Random Value (FLOAT, INT or FLOAT_VECTOR)."""
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
        """Voronoi Texture node (returns the node; pick outputs with out())."""
        n = self.node('ShaderNodeTexVoronoi', {'Vector': vec, 'Scale': scale, 'Randomness': rand, 'W': w},
                      feature=feature, voronoi_dimensions=dims)
        return n

    def group(self, tree, ins=None):
        """Group node instancing `tree` (NodeTree or node group) with inputs `ins`."""
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
LAYER_D1      = [0.75,    0.95,   1.0,    1.0,    1.0,    0.5,    1.0,    0.7]     # gore_depth at the bottom of a wall
LAYER_SURF_D  = [0.035,  0.6,    1.0,    1.0,    1.0,    0.3,    1.0,    0.6]     # gore_depth of exposed surface
LAYER_TOL_IN  = [0.012,  0.012,  0.016,  0.016,  0.035,  0.014,  0.05,   0.03]    # how far below the impact a layer is affected
LAYER_TOL_OUT = [0.016,  0.016,  0.010,  0.010,  0.010,  0.016,  0.03,   0.02]
LAYER_IS_BONE = [0, 0, 1, 1, 0, 0, 0, 0]
# depth (hit scale.z * damage) at which the layer is opened, and at which the
# layer above it is opened (so this layer's surface is exposed)
OPEN_AT       = [0.02,   0.35,   0.78,   0.78,   9.0,    0.05,   9.0,    0.3]
ABOVE_OPEN_AT = [9.0,    0.02,   0.35,   0.35,   0.78,   9.0,    9.0,    9.0]
# hole radius factors relative to the skin hole
BULLET_RF     = [1.0,    0.85,   0.8,    0.8,    1.0,    1.0,    1.0,    1.0]
EXIT_RF       = [1.0,    0.86,   0.74,   0.74,   1.0,    0.9,    1.0,    1.0]
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
    ("Tension", 'NodeSocketVector', None, None, None, "Skin tension line direction in the hit frame"),
    ("Normal", 'NodeSocketVector', None, None, None, "Surface normal at the impact in the hit frame"),
    ("Region", 'NodeSocketVector', None, None, None, "Region weights (scalp, face, neck) at the impact"),
    ("Age", 'NodeSocketFloat', 0.2, 0.0, 1.0, "Wound age (hours = 48 * age^2)"),
    ("Bone Depth", 'NodeSocketFloat', 0.008, None, None, "Soft tissue thickness over the bone here (m)"),
    ("Crush", 'NodeSocketFloat', 0.0, 0.0, 1.0,
     "Accumulated blunt energy of this hit and its neighbours (0 = single blow, 1 = crushed face)"),
    ("Axis W", 'NodeSocketFloat', 0.0, None, None,
     "Depth of this layer's impact below the hit empty along the hit axis (m, <= 0): Local.z + Axis W "
     "is the same point on every layer"),
    ("Pos", 'NodeSocketVector', None, None, None,
     "Vertex position in the layer's object space (head space for skin / skull; eye space for the "
     "eyes: origin at the eyeball's centre)"),
    ("Axis X", 'NodeSocketVector', None, None, None, "Hit frame X axis in object space"),
    ("Axis Y", 'NodeSocketVector', None, None, None, "Hit frame Y axis in object space"),
    ("Axis Z", 'NodeSocketVector', None, None, None, "Hit frame Z axis in object space (out of the head)"),
)
KIND_OUTPUTS = (
    ("Cut", 'NodeSocketFloat'),        # signed distance to the hole outline (m), > 0 inside the hole
    ("Disp", 'NodeSocketVector'),      # displacement in the hit frame
    ("Disp N", 'NodeSocketFloat'),     # displacement along the vertex normal
    ("Wall", 'NodeSocketVector'),      # full wall extrusion vector in the hit frame
    ("Center", 'NodeSocketVector'),    # vector to the wound's centre line (hit frame, tangent plane)
    ("Wound", 'NodeSocketFloat'),
    ("Edge", 'NodeSocketFloat'),
    ("Blood", 'NodeSocketFloat'),
    ("Bruise", 'NodeSocketFloat'),
    ("Burn", 'NodeSocketFloat'),
    ("Fracture", 'NodeSocketFloat'),
)

TAU = 2.0 * math.pi
EYE_R = 0.012                 # eyeball radius (anatomy.build_eye); trauma never enlarges it
NOSE_C = (0.0, -0.104, -0.012)  # middle of the external nose (head space), for blows that break it
NOSTRIL = (0.0072, -0.1012, -0.0248)  # left nostril opening (mirrored for the right)


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
        self.wT = self.w + t.inp("Axis W")            # depth below the hit empty (same on every layer)
        self.layer = t.inp("Layer")
        self.down = t.inp("Down")
        self.rho = (self.u * self.u + self.v * self.v).sqrt()
        self.theta = t.math('ARCTAN2', self.v, self.u)
        inv = 1.0 / self.rho.max(1e-6)
        self.radial = t.vec(self.u * inv, self.v * inv, 0.0)   # unit, away from the axis
        self.center = t.vec(-self.u, -self.v, 0.0)             # back to the axis
        self.P = t.inp("Pos")
        self.AX, self.AY, self.AZ = t.inp("Axis X"), t.inp("Axis Y"), t.inp("Axis Z")

    def to_hit(self, v):
        """Object-space vector -> hit frame."""
        return self.t.vec(v.dot(self.AX), v.dot(self.AY), v.dot(self.AZ))

    def impact_obj(self):
        """This layer's impact point in object space."""
        return self.P - (self.AX * self.u + self.AY * self.v + self.AZ * self.w)

    def eye_axis_dist(self):
        """Eye layer: distance (m) of the eyeball's centre from the hit axis.

        The eye objects have their origin at the globe's centre, so the centre
        seen from this vertex is -Pos; in the hit frame it lies at Local - Pos_h."""
        c = self.L - self.to_hit(self.P)
        return (c.x * c.x + c.y * c.y).sqrt()

    def eye_injury(self, rupture, hyph, subconj, tear_len=0.0065, tear_w=0.0011):
        """Injury of the eyeball (eye layer only), REFERENCE_NOTES §5.20.

        rupture 0..1: the globe DEFLATES -- it never swells: the side facing the
        blow caves in, the rest shrinks and wrinkles; a ragged tear opens through
        the impact point and dark uveal tissue and grey jelly (vitreous) bulge
        out through it (gore_edge on the eye = extruded tissue for the shader,
        gore_wound = collapsed, clouded globe).
        hyph 0..1: blood layered behind the cornea (gore_bruise on the eye = the
        level of the hyphaema; 1 = the whole front chamber, an "eight-ball" eye).
        subconj 0..1: subconjunctival haemorrhage (gore_blood on the eye: the
        white turns a flat, solid bright red).
        Returns dict(disp, cut, wall, edge, blood, bruise, wound); zero off the eye.
        """
        t = self.t
        on = self.is_layer(LAYER_EYE)
        ph = self.to_hit(self.P)                          # centre -> vertex, hit frame
        dh = ph / ph.length().max(1e-5)
        front = t.smooth(-0.35, 0.85, dh.z)               # the side facing the blow
        r = rupture * on
        # deflation with folds: a collapsed globe is a wrinkled, misshapen bag
        n1 = t.noise(self.P * 380.0 + t.vec(self.seed * 7.0, 0.0, 0.0), detail=2.0)
        n2 = t.noise(self.P * 1100.0 + t.vec(0.0, self.seed * 3.0, 0.0), detail=1.0)
        fold = 0.55 + 0.9 * n1.abs() + 0.25 * n2
        depth = r * EYE_R * (0.1 + 0.5 * front) * fold
        # ragged tear through the impact (limbus to equator), tapering at its ends
        uu = self.u / tear_len
        vw = self.v + t.noise(t.vec(self.u * 420.0, self.seed * 9.0, 1.0), detail=2.0) * 0.0006
        hw = tear_w * r * (1.0 - uu * uu).max(0.0) ** 0.6
        tear_cut = t.switch(t.bool('AND', front.gt(0.25), r.gt(0.3)), -1.0, hw - t.math('ABSOLUTE', vw))
        d_out = t.math('ABSOLUTE', vw) - hw
        # prolapse: uvea and vitreous pushed out through the tear, lumpy
        lump = 0.6 + 0.8 * t.noise(self.P * 900.0, detail=2.0, signed=False)
        pro = t.smooth(0.0032, 0.0, d_out) * t.smooth(1.25, 0.8, t.math('ABSOLUTE', uu)) * r * front
        disp = dh * (pro * 0.0019 * lump - depth)
        wall = dh * -0.0035
        extruded = (pro * 1.3).clamp()
        wound = (r * (0.35 + 0.65 * front)).clamp()
        return dict(disp=disp, cut=tear_cut, wall=wall, edge=extruded, blood=(subconj * on).clamp(),
                    bruise=(hyph * on).clamp(), wound=wound, on=on)

    def lc(self, values, dtype='FLOAT'):
        """Per-layer constant."""
        return self.t.pick(self.layer, values, dtype)

    def is_layer(self, layer_id):
        return self.t.switch(self.t.compare('EQUAL', self.layer, layer_id, 'INT'), 0.0, 1.0)

    def opened(self, at):
        return self.t.smooth(at, at + 0.02, self.D)

    def pool(self, q, radius, amount, stretch=3.2, drop=0.0):
        """Graded blood coverage around q = 0: a teardrop running down, broken into streaks.

        drop moves the pool down (along world -Z): blood leaves a wound over its
        lower rim, the upper margin stays readable.
        """
        if drop:
            q = q - self.down * drop
        n = self.t.group(_sub("pool"), {"Q": q, "Down": self.down, "Noise Pos": self.np, "Radius": radius,
                                         "Amount": amount, "Stretch": stretch})
        return self.t.out(n, "Coverage")

    def hash(self, k):
        """Deterministic pseudo-random 0..1 from the hit seed (k selects the stream)."""
        return _hash(self.t, self.seed, k)

    def tears(self, n, first=0, width=(0.12, 0.3), length=(0.4, 1.0), sharp=1.5, wobble=0.0, widen=1.0,
              with_angle=False):
        """Tapered tears at random angles: max over n spikes of length*(1-|dθ|/w)^sharp.

        widen > 1 returns the same tears fattened (used for their bruised margins).
        with_angle=True also returns the direction angle of the dominant tear.
        """
        t = self.t
        theta = self.theta
        if wobble:
            # tear lines are not straight radial rays
            theta = theta + t.noise(self.np * 260.0, detail=2.0) * wobble
        best = best_phi = None
        for k in range(first, first + n):
            sn = t.group(_sub("spike"), {"Theta": theta, "Seed": self.seed, "K": float(k),
                                         "Width Min": width[0], "Width Max": width[1],
                                         "Length Min": length[0], "Length Max": length[1],
                                         "Sharp": sharp, "Widen": widen})
            sp, phi = t.out(sn, "Value"), t.out(sn, "Phi")
            if best is None:
                best, best_phi = sp, phi
            else:
                if with_angle:
                    best_phi = t.switch(sp.gt(best), best_phi, phi)
                best = best.max(sp)
        best = best.max(0.0)
        return (best, best_phi) if with_angle else best

    def cracks(self, R, n_around=7.0, width=0.0005):
        """Polar Voronoi crack network around the axis.

        Returns (line, plate): line = 1 on crack lines (width in meters),
        plate = random 0..1 per bone plate between the cracks.
        """
        n = self.t.group(_sub("cracks"), {"Theta": self.theta, "Rho": self.rho, "Radius": R, "Seed": self.seed,
                                           "Noise Pos": self.np, "Around": n_around, "Width": width})
        return self.t.out(n, "Line"), self.t.out(n, "Plate")


def _hash(t, seed, k):
    """fract(sin(seed * a_k + b_k) * 43758.5453): cheap per-hit random stream k."""
    return t.math('FRACT', t.math('SINE', seed * (12.9898 + 3.71 * k) + 0.618 * k) * 43758.5453)


def _build_sub_spike():
    """One tapered tear at a random angle (by seed and index K)."""
    f = 'NodeSocketFloat'
    t = NodeTree("GH_Gore_Spike", (("Theta", f), ("Seed", f), ("K", f), ("Width Min", f, 0.1), ("Width Max", f, 0.3),
                                   ("Length Min", f, 0.3), ("Length Max", f, 1.0), ("Sharp", f, 1.5), ("Widen", f, 1.0)),
                 (("Value", f), ("Phi", f)), description="One tapered tear: profile over the angle")
    seed, k3 = t.inp("Seed"), t.inp("K") * 3.0

    def hk(off):
        kk = k3 + off
        return t.math('FRACT', t.math('SINE', seed * (12.9898 + kk * 3.71) + kk * 0.618) * 43758.5453)
    phi = hk(0.0) * TAU
    ln = t.inp("Length Min") + (t.inp("Length Max") - t.inp("Length Min")) * hk(1.0)
    wa = (t.inp("Width Min") + (t.inp("Width Max") - t.inp("Width Min")) * hk(2.0)) * t.inp("Widen")
    d = t.inp("Theta") - phi
    ad = t.math('ABSOLUTE', t.math('ARCTAN2', d.sin(), d.cos()))
    # soft falloff past the tip keeps the argmax over spikes defined everywhere
    t.result("Value", ln * ((1.0 - ad / wa).max(0.0) ** t.inp("Sharp")) - ad * 0.001)
    t.result("Phi", phi)
    t.layout()
    return t


def _build_sub_pool():
    """Blood pool: teardrop that runs down world -Z, broken up into streaks."""
    f, v = 'NodeSocketFloat', 'NodeSocketVector'
    t = NodeTree("GH_Gore_Pool", (("Q", v), ("Down", v), ("Noise Pos", v), ("Radius", f, 0.005),
                                  ("Amount", f, 1.0), ("Stretch", f, 3.2)),
                 (("Coverage", f),), description="Graded blood coverage running downward")
    q, down, npos = t.inp("Q"), t.inp("Down"), t.inp("Noise Pos")
    dz = q.dot(down)                                    # > 0 below the source
    lat = (q - down * dz).length()
    along = dz.max(0.0) / t.inp("Stretch") + (-dz).max(0.0) * 1.4
    td = (lat * lat + along * along).sqrt() / t.inp("Radius")
    n1 = t.noise(npos * 170.0, detail=3.0)
    n0 = t.noise(npos * 55.0, detail=2.0)              # broad lobes: no smooth blob outline
    # noise stretched along world Z -> vertical runs of thicker blood
    streak = t.noise(t.vec(npos.x * 520.0, npos.y * 520.0, npos.z * 70.0), detail=2.0)
    # one continuous sheet with a lobed edge (thicker runs inside it), not
    # scattered blotches
    cov = t.smooth(1.05, 0.25, td + n1 * 0.12 + n0 * 0.35)
    t.result("Coverage", cov * (0.72 + 0.28 * t.smooth(-0.25, 0.45, streak)) * t.inp("Amount"))
    t.layout()
    return t


def _build_sub_cracks():
    """Polar Voronoi crack network (radiating fractures and bone plates)."""
    f = 'NodeSocketFloat'
    t = NodeTree("GH_Gore_Cracks", (("Theta", f), ("Rho", f), ("Radius", f, 0.01), ("Seed", f),
                                    ("Noise Pos", 'NodeSocketVector'), ("Around", f, 7.0), ("Width", f, 0.0005)),
                 (("Line", f), ("Plate", f)), description="Radiating fracture lines around the axis")
    rho, n_around = t.inp("Rho"), t.inp("Around")
    lr = t.math('LOGARITHM', rho.max(1e-5) / t.inp("Radius"), math.e)
    pc = t.vec(t.inp("Theta") * n_around / TAU, lr * 0.75, t.inp("Seed") * 9.1)
    # jagged cracks: wobble the lookup
    pc = pc + t.noise(t.inp("Noise Pos") * 350.0, detail=2.0, color=True) * 0.12
    edge = t.out(t.voronoi(pc, 1.0, 'DISTANCE_TO_EDGE', 0.9), 'Distance')
    cell = t.out(t.voronoi(pc, 1.0, 'F1', 0.9), 'Color')
    # the world width in polar units (the angular cell width grows with rho)
    wpolar = t.inp("Width") / (rho.max(1e-4) * TAU / n_around)
    t.result("Line", t.smooth(wpolar, wpolar * 0.3, edge))
    t.result("Plate", t.sep(t.vmath('ADD', cell, (0, 0, 0)))[0])
    t.layout()
    return t


def _build_sub_tear():
    """One straight-ish tear of a blunt split: a tapered wedge from the centre."""
    f, v = 'NodeSocketFloat', 'NodeSocketVector'
    t = NodeTree("GH_Gore_Tear", (("U", f), ("V", f), ("Seed", f), ("K", f), ("Size", f, 0.01),
                                  ("Core", f, 0.002), ("Noise Pos", v), ("Gape", f, 1.0),
                                  ("Phi", f, 0.0), ("Phi Mix", f, 0.0), ("Length", f, 1.0)),
                 (("Cut", f), ("Line", v)), description="Perpendicular distance field of one tear")
    seed, k3 = t.inp("Seed"), t.inp("K") * 3.0 + 40.0
    size, rc = t.inp("Size"), t.inp("Core")
    u, v_ = t.inp("U"), t.inp("V")

    def hk(off):
        kk = k3 + off
        return t.math('FRACT', t.math('SINE', seed * (12.9898 + kk * 3.71) + kk * 0.618) * 43758.5453)
    phi = t.mix(hk(0.0) * TAU, t.inp("Phi") + (hk(0.0) - 0.5) * 0.5, t.inp("Phi Mix"))
    length = size * 0.0125 * (0.25 + 0.95 * hk(1.0)) * t.inp("Length")
    w0 = size * 0.0012 * (0.7 + 0.7 * hk(2.0)) * t.inp("Gape")
    dx, dy = phi.cos(), phi.sin()
    a = u * dx + v_ * dy
    # tears wander and tear raggedly
    b = (v_ * dx - u * dy) + size * 0.0007 * t.noise(t.vec(a * 260.0, t.inp("K") * 3.7, seed * 13.0), detail=2.0)
    hw = w0 * ((1.0 - a.max(0.0) / length).max(0.0) ** 0.75) * t.smooth(-rc, 0.0, a)
    hw = hw * (1.0 + 0.3 * t.noise(t.inp("Noise Pos") * 900.0 + t.vec(t.inp("K") * 1.3, 0.0, 0.0)))
    # distance to the tear segment (not its infinite line)
    da = a - t.clamp(a, 0.0, length)
    t.result("Cut", hw - (b * b + da * da).sqrt())
    t.result("Line", t.vec(dx * a.max(0.0), dy * a.max(0.0), 0.0) - t.vec(u, v_, 0.0))
    t.layout()
    return t


_SUBGROUPS = {}
_SUB_BUILDERS = {"spike": _build_sub_spike, "pool": _build_sub_pool, "cracks": _build_sub_cracks,
                 "tear": _build_sub_tear}


def _sub(name):
    """Small shared helper groups, built once per build_gore_node_group()."""
    if name not in _SUBGROUPS:
        _SUBGROUPS[name] = _SUB_BUILDERS[name]()
    return _SUBGROUPS[name]


def _kind_tree(name, desc):
    return NodeTree(name, KIND_INPUTS, KIND_OUTPUTS, description=desc)


def _finish_kind(t, cut, disp=None, dispn=0.0, wall=None, center=None, wound=0.0, edge=0.0,
                 blood=0.0, bruise=0.0, burn=0.0, fracture=0.0):
    t.result("Cut", cut)
    t.result("Disp", disp if disp is not None else (0.0, 0.0, 0.0))
    t.result("Disp N", dispn)
    t.result("Wall", wall if wall is not None else (0.0, 0.0, 0.0))
    t.result("Center", center if center is not None else (0.0, 0.0, 0.0))
    for k, v in (("Wound", wound), ("Edge", edge), ("Blood", blood), ("Bruise", bruise),
                 ("Burn", burn), ("Fracture", fracture)):
        t.result(k, v)
    t.layout()


def _build_bullet():
    """Entry wound (9 mm FMJ): small hole, abrasion collar, bevelled bone, brain track.

    Research 01 / REALISM_BIBLE rows 1-6: the skin hole is SMALLER than the
    bullet (skin recoils): scalp ~7.5 mm, face ~7 mm, neck ~5 mm; a crisp
    red-brown abrasion collar 1.6-2.4 mm wide, concentric for a square hit and
    widest toward the shooter for an oblique one (the hit plane makes oblique
    holes elliptical by itself). The skull hole is LARGER than the skin hole
    (outer table 1.0-1.2 x calibre) and bevels inward (inner table 1.3-2 x).
    The skin wall runs down to the bone (per-vertex bone depth). Range of fire
    (hit scale.y = muzzle distance in metres, default 1 m = distant): soot
    within ~30 cm, stippling to ~90 cm, a stellate contact tear over bone.
    """
    t = _kind_tree("GH_Gore_Bullet", "Bullet entry wound fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_bone = c.lc(LAYER_IS_BONE)
    is_skin = c.is_layer(LAYER_SKIN)
    is_brain = c.is_layer(LAYER_BRAIN)
    opened = c.opened(c.lc(OPEN_AT))
    rng = c.e                                          # muzzle distance (m)
    reg = t.inp("Region")
    k_hole = reg.x * 0.83 + reg.y * 0.78 + reg.z * 0.52
    r0 = s * 0.0045 * k_hole
    # mean-preserving, fine irregular margin (no saw teeth: an entrance margin
    # is abraded and slightly inverted, not torn paper)
    rag = t.noise(c.np * 520.0, detail=2.0)
    # contact shot over bone: gas under the skin tears it into a star
    bd = t.inp("Bone Depth")
    contact = t.smooth(0.03, 0.004, rng) * is_skin * t.smooth(0.014, 0.008, bd)
    star = c.tears(4, width=(0.25, 0.5), length=(0.35, 1.0), sharp=1.3, wobble=0.15)
    # (never a punched disc: slightly oval, with a few small notches where the
    # stretched skin split at the margin -- refs/20, gsw sheet)
    ell = 1.0 + 0.16 * c.hash(44) * (t.math('COSINE', (c.theta - c.hash(45) * TAU) * 2.0))
    notch = c.tears(5, first=30, width=(0.07, 0.2), length=(0.2, 0.75), sharp=1.5, wobble=0.25)
    rag = rag + t.noise(t.vec(c.theta.cos() * 1.4, c.theta.sin() * 1.4, c.seed * 4.0), detail=2.0) * 1.6
    r_soft = r0 * (1.0 + rag * 0.07 + notch * 0.35) * ell * c.lc([1.0, 1.2, 0.0, 0.0, 1.0, 1.0, 1.0, 1.0]) \
        + contact * star * s * 0.011
    # bone: sized from the calibre, inward bevel (inner table 1.3-2x the outer)
    r_outer = s * 0.0045 * (1.0 + 0.2 * c.hash(4))
    ratio = 1.3 + 0.7 * c.hash(5)
    slope = (ratio - 1.0) * r_outer / 0.0065
    r_bone = r_outer * (1.0 + t.noise(c.np * 1800.0, detail=1.0) * 0.06) + (-c.w).max(0.0) * slope
    r = t.mix(r_soft, r_bone, is_bone)
    cut = t.switch(opened.gt(0.5), -1.0, r - c.rho)
    # abrasion collar: concentric at 90 degrees, widest toward the shooter
    # when oblique (leading width = w / sin(incidence))
    N = t.inp("Normal")
    nz = N.z.max(0.15)
    phi_s = t.math('ARCTAN2', -N.y, -N.x)
    ecc = (1.0 / nz - 1.0).min(7.0)
    toward = t.math('COSINE', c.theta - phi_s).max(0.0) ** 1.5
    # (the width wanders +-30 % around the hole in 4-6 lobes: a real collar is
    # never a machined ring)
    lobe_dir = t.vec(c.theta.cos() * 0.8, c.theta.sin() * 0.8, c.seed * 9.0)
    lobe2 = t.vec(c.theta.cos() * 2.2, c.theta.sin() * 2.2, c.seed * 5.0 + 3.0)
    w_c = s * 0.002 * (1.0 + 0.5 * t.noise(lobe_dir, detail=1.0) + 0.25 * t.noise(lobe2, detail=1.0)
                       + 0.12 * t.noise(c.np * 900.0)).max(0.35) \
        * (1.0 + ecc * toward)
    # crisp outer edge (~0.2-0.3 mm of falloff, the mesh is ~0.45 mm): no soft
    # brown halo beyond it -- a blurred ring reads as a coffee stain
    # (the collar begins AT the hole margin: no band of clean skin between)
    # (an uneven, scalloped outer border and a patchy, dried surface: an even
    # band reads as a ring decal)
    collar = t.smooth(r + w_c * 1.05 + 0.00015, r + w_c * 1.05 - 0.00015,
                      c.rho + t.noise(c.np * 380.0) * w_c * 0.2 + t.noise(c.np * 1100.0) * w_c * 0.1) \
        * (0.45 + 0.55 * t.smooth(-0.35, 0.3, t.noise(c.np * 650.0, detail=2.0)))
    edge = collar * is_skin * (1.0 - contact) + t.smooth(r + 0.0009, r, c.rho) * (1.0 - is_skin)
    # range of fire: stippling (burnt powder grains, abrasions that do not
    # wipe off) and soot (grey-black, wipes off) around close shots
    st_amt = t.smooth(0.95, 0.35, rng) * t.smooth(0.004, 0.02, rng)
    r_st = 0.006 + 0.12 * rng
    vd = t.voronoi(c.np, 2600.0, 'F1', 1.0)
    dcell = t.sep(t.vmath('ADD', t.out(vd, 'Color'), (0, 0, 0)))[0]
    dens = st_amt * t.smooth(r_st, r_st * 0.15, c.rho - r) * 0.55
    dots = t.smooth(0.32, 0.12, t.out(vd, 'Distance')) * dcell.lt(dens).max(0.0)
    edge = edge.max(dots * is_skin * opened)
    soot_amt = t.smooth(0.32, 0.03, rng) * (1.0 - contact * 0.4)
    r_soot = 0.004 + 0.06 * rng
    soot = soot_amt * t.smooth(r + r_soot * 1.6, r, c.rho + t.noise(c.np * 150.0, detail=2.0) * r_soot * 0.5) \
        * (0.55 + 0.45 * t.noise(c.np * 700.0, detail=2.0, signed=False)) * is_skin * opened
    # contact: seared blackened margin and the muzzle imprint around it
    imprint = contact * t.smooth(0.0006, 0.0, t.math('ABSOLUTE', c.rho - s * 0.0065)) * 0.8
    edge = edge.max(imprint)
    sear = contact * t.smooth(r + 0.0025, r, c.rho)
    edge = edge * opened
    # inverted margin: the abraded collar is pushed slightly inward (0.1-0.3 mm),
    # never raised into a dome
    dent = t.smooth(r + w_c * 1.6, r, c.rho) * opened * is_skin * s * -0.00028
    # tissue exposed under the hole of the layer above
    r_above = s * 0.0045 * 1.25
    exposed = t.smooth(r_above * 1.2, r_above * 0.8, c.rho) * c.opened(c.lc(ABOVE_OPEN_AT))
    # (on the skin the raw margin is the wall itself: the collar reaches the hole)
    wound = (t.smooth(r + 0.0005, r, c.rho) * opened * (1.0 - is_skin)).max(exposed)
    # blood: none is painted on the skin around the hole (it only gets there by
    # the traced runs that overflow the wound, see _build_blood); only the
    # tissue exposed inside the wound is bloody
    blood = exposed * 0.9
    # brain: permanent track ~11 mm across, haemorrhagic tissue out to r = 18 mm
    crat = t.smooth(0.88, 0.97, D) * is_brain
    rc = s * 0.0055
    x = (c.rho / rc).min(1.0)
    prof = (1.0 - x * x) ** 1.5
    lump = 1.0 + t.noise(c.np * 500.0) * 0.35
    crater_z = crat * prof * lump * (0.012 + 0.012 * s) * -1.0
    brain_w = t.smooth(rc * 1.3, rc * 0.8, c.rho + t.noise(c.np * 300.0) * 0.0015) * crat
    haem = t.smooth(0.018, 0.005, c.rho + t.noise(c.np * 200.0, detail=2.0) * 0.004) * crat \
        * (0.35 + 0.4 * t.smooth(-0.2, 0.4, t.noise(c.np * 260.0, detail=2.0)))
    wound = wound.max(brain_w).max(haem * 0.6)
    blood = blood.max(brain_w).max(haem)
    # eye: a bullet through the globe destroys it (it deflates and collapses
    # around the torn track); one passing through the orbit beside it bursts
    # vessels (subconjunctival haemorrhage, blood in the front chamber)
    d_eye = c.eye_axis_dist()
    thru_eye = t.smooth(EYE_R + 0.004, EYE_R - 0.002, d_eye) * t.smooth(0.25, 0.4, D)
    near_eye = t.smooth(0.03, 0.014, d_eye) * t.smooth(0.8, 0.95, D)
    eye = c.eye_injury(thru_eye, (thru_eye * 0.9 + near_eye * 0.3).clamp(),
                       (thru_eye * 0.7 + near_eye * 0.75).clamp(), tear_len=0.008, tear_w=0.0017)
    blood = blood.max(eye["blood"])
    wound = wound.max(eye["wound"])
    edge = edge.max(eye["edge"])
    cut = cut.max(eye["cut"])
    disp = t.vec(0.0, 0.0, dent + crater_z) + eye["disp"]
    # walls: the skin tube runs down to the bone (so no gap shows between the
    # layers); bone flares outward (inward bevel)
    tw = c.lc(LAYER_WALL)
    wl = t.mix(tw, bd.max(0.002) + 0.0004, is_skin)
    wall = c.radial * (is_bone * slope * tw - (1.0 - is_bone) * r * 0.1) + t.vec(0.0, 0.0, -wl)
    wall = t.switch(eye["on"].gt(0.5), wall, eye["wall"], 'VECTOR')
    _finish_kind(t, cut, disp=disp, wall=wall, center=c.center, wound=wound, edge=edge, blood=blood,
                 bruise=eye["bruise"], burn=sear * 0.75, fracture=soot)
    return t


def _build_exit():
    """Exit wound (9 mm FMJ through the head): 10-30 mm, torn outward, no collar.

    Shape class by weighted chance (research 01 / REALISM_BIBLE row 7):
    circular 25 %, stellate 33 %, irregular 30 %, slit 9 %, crescent 3 %.
    The margins are everted by at most ~4 mm, frayed; the bone is bevelled
    outward with jagged edges; brain tissue herniates through the defect.
    """
    t = _kind_tree("GH_Gore_Exit", "Exit wound fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_bone = c.lc(LAYER_IS_BONE)
    is_skin = c.is_layer(LAYER_SKIN)
    is_brain = c.is_layer(LAYER_BRAIN)
    evert_amt = c.lc([1.0, 0.55, 0.35, 0.35, 0.0, 0.0, 0.0, 0.3])
    opened = c.opened(c.lc(OPEN_AT))
    # half span, capped at 15 mm (30 mm across)
    R = (s * 0.0105 * (0.8 + 0.45 * c.hash(7))).min(0.015) * c.lc(EXIT_RF)
    theta = c.theta
    ring = t.vec(theta.cos() * 1.1, theta.sin() * 1.1, c.seed * 11.0)
    lf = t.noise(ring, detail=2.0, signed=False)
    lf2 = t.noise(ring * 1.7 + t.vec(3.3, 1.1, 0.0), detail=3.0, signed=False)
    # 3-6 tapered splits radiate from every exit (refs/20, gsw sheet: star /
    # slit tears with long rays that taper to fine points); the class decides
    # how long they run and how big the torn core is. Even a "circular" exit
    # is a ragged hole with short splits, never a punched disc.
    star, tear_phi = c.tears(7, width=(0.07, 0.26), length=(0.2, 1.0), sharp=1.25, wobble=0.3, with_angle=True)
    phi0 = c.hash(8) * TAU
    dphi = theta - phi0
    # lobes and bites of 3-6 mm along the torn margin (a second, faster
    # harmonic around the ring): no exit class is a disc or a rounded square
    ring3 = t.vec(theta.cos() * 2.6, theta.sin() * 2.6, c.seed * 7.0 + 2.0)
    lobe = t.noise(ring3, detail=2.0)
    r_circ = R * (0.44 + 0.3 * lf + 0.1 * lobe + 0.34 * star)
    r_star = R * (0.28 + 0.2 * lf + 0.07 * lobe + 0.72 * star)
    r_irr = R * (0.3 + 0.55 * lf2 + 0.14 * lobe + 0.36 * star)
    a_, b_ = R * 0.95, R * 0.2
    r_slit = a_ * b_ / ((b_ * dphi.cos()) ** 2.0 + (a_ * dphi.sin()) ** 2.0).sqrt().max(1e-7) + R * 0.25 * star
    r_cres = R * (0.3 + 0.62 * t.smooth(-0.3, 0.7, dphi.cos())) * (0.85 + 0.2 * lf) + R * 0.2 * star
    h = c.hash(6)
    cls = h.gt(0.25).max(0.0) + h.gt(0.58).max(0.0) + h.gt(0.88).max(0.0) + h.gt(0.97).max(0.0)
    r = t.pick(t.math('FLOOR', cls + 0.5), [r_circ, r_star, r_irr, r_slit, r_cres])
    is_star = t.compare('EQUAL', t.math('FLOOR', cls + 0.5), 1.0)
    # torn tissue: frayed margins (skin), sharp small teeth (bone)
    rag = t.noise(c.np * 650.0, detail=2.0) * 0.0009 + t.noise(c.np * 2300.0, detail=1.0) * 0.00035 \
        + t.noise(c.np * 220.0, detail=2.0) * 0.0012
    jag = t.noise(c.np * 2200.0, detail=1.0)
    r = r + s * rag * (1.0 - is_bone) + is_bone * R * 0.12 * jag
    # outward bevel on bone: the outer table is blown out wider
    r = r + is_bone * (c.w + c.lc(LAYER_WALL)).max(0.0) * 0.6
    cut = t.switch(opened.gt(0.5), -1.0, r - c.rho)
    d_out = c.rho - r
    # everted flaps: lifted <= ~4 mm right at the margin, fading within ~R/2
    # (thin torn skin flaps turned outward, not a swollen ring: the lift dies
    # out within ~R/4 of the margin and varies flap by flap -- some sectors
    # stand up 2-4 mm, others lie flat -- REFERENCE_NOTES §5.16 / §5.19.2)
    flap = t.smooth(R * 0.28, 0.0, d_out) * opened
    tip = t.switch(is_star, 0.6, 1.0 - star.min(1.0))
    sector = t.smooth(0.35, 0.75, t.noise(ring * 2.3 + t.vec(0.0, 0.0, 5.0), detail=1.0, signed=False))
    curl = (0.25 + 0.95 * sector) * (0.85 + t.noise(c.np * 110.0, detail=1.0) * 0.3)
    lift = flap ** 2.5 * s.min(1.3) * 0.0026 * (0.5 + 0.5 * tip) * curl * evert_amt
    disp_evert = t.vec(0.0, 0.0, lift) + c.radial * (lift * 0.45)
    edge_lift = s.min(1.3) * 0.0026 * (0.5 + 0.5 * tip) * curl * evert_amt * opened
    # brain: pulped tissue herniating out toward the skull defect, a torn
    # track in the middle
    # (2-30 mL of pulped brain is extruded, mostly at the exit: a lumpy,
    # bloody mass pushes out through the skull defect to the skin surface)
    crat = t.smooth(0.84, 0.95, D) * is_brain
    rc = R * 0.62
    x = (c.rho / rc).min(1.0)
    pulp = t.noise(c.np * 380.0, detail=3.0)
    lumps = t.noise(c.np * 900.0, detail=2.0)
    track = t.smooth(0.25, 0.05, x)
    crater_z = crat * (((1.0 - x * x) ** 1.2) * s * (0.0135 + pulp * 0.004 + lumps * 0.0015) - track * s * 0.004)
    brain_w = t.smooth(1.2, 0.75, c.rho / rc + pulp * 0.1) * crat * t.smooth(-0.35, 0.25, pulp).max(track)
    brain_blood = brain_w * (0.25 + 0.5 * t.smooth(-0.1, 0.45, t.noise(c.np * 240.0, detail=2.0))) \
        + track * crat * 0.7
    disp = disp_evert + t.vec(0.0, 0.0, crater_z)
    # tissue exposure, torn edge (no abrasion collar at an exit), fracture
    r_above = R * 0.75
    exposed = t.smooth(r_above * 1.25, r_above * 0.7, c.rho) * c.opened(c.lc(ABOVE_OPEN_AT))
    # (no abrasion at an exit: the skin margin is torn, wet and dark red)
    edge = t.smooth(0.0012, 0.0, d_out) * opened * (1.0 - is_skin)
    wound = (t.smooth(s * 0.0014, 0.0, d_out + t.noise(c.np * 700.0) * 0.0006) * opened) \
        .max(exposed * (1.0 - is_brain * 0.65)).max(brain_w)
    lines, _plate = c.cracks(R, n_around=8.0, width=0.00045)
    frac = lines * t.smooth(R * 3.0, R * 1.1, c.rho) * is_bone * opened
    frac = frac.max(t.smooth(s * 0.004, 0.0, d_out) * is_bone * opened)
    # (no painted pool, film or blotches on the scalp around the exit: blood
    # only reaches the skin by the runs that overflow the wound; the torn
    # margin itself is raw, wet tissue -- at most ~1 mm of it)
    margin = t.smooth(0.0012, 0.0, d_out + t.noise(c.np * 700.0) * 0.0004) * opened * is_skin * 0.7
    blood = (exposed * (1.0 - is_brain * 0.6)).max(brain_blood).max(margin)
    tw = c.lc(LAYER_WALL)
    # walls: the core narrows toward the axis, the narrow tears of a stellate
    # exit close in a V toward their own line (their two sides never cross)
    tdx, tdy = tear_phi.cos(), tear_phi.sin()
    ta = (c.u * tdx + c.v * tdy).max(0.0)
    to_line = t.vec(tdx * ta, tdy * ta, 0.0) - t.vec(c.u, c.v, 0.0)
    in_tear = t.bool('AND', t.bool('AND', star.gt(0.12), c.rho.gt(R * 0.42)), is_star)
    center = t.switch(in_tear, c.center, to_line, 'VECTOR')
    conv = t.switch(in_tear, 0.2, 0.8) * (1.0 - is_bone)
    wall = t.vec(0.0, 0.0, -(tw + edge_lift * 0.25)) + center * conv - c.radial * (is_bone * tw * 0.6)
    # an exit through the orbit bursts the globe
    d_eye = c.eye_axis_dist()
    thru_eye = t.smooth(EYE_R + 0.008, EYE_R, d_eye) * t.smooth(0.25, 0.4, D)
    near_eye = t.smooth(0.035, 0.016, d_eye) * t.smooth(0.8, 0.95, D)
    eye = c.eye_injury(thru_eye, (thru_eye + near_eye * 0.3).clamp(), (thru_eye * 0.7 + near_eye * 0.75).clamp(),
                       tear_len=0.009, tear_w=0.002)
    cut = cut.max(eye["cut"])
    disp = disp + eye["disp"]
    wall = t.switch(eye["on"].gt(0.5), wall, eye["wall"], 'VECTOR')
    _finish_kind(t, cut, disp=disp, wall=wall, center=center, wound=wound.max(eye["wound"]),
                 edge=edge.max(eye["edge"]), blood=blood.max(eye["blood"]), bruise=eye["bruise"], fracture=frac)
    return t


def _slash_params(t, s, e, D, tx, ty, scalp, neck=None):
    """Length and gape of an incised cut.

    Gape (total opening at the widest point) = L * G(theta) * f_depth * f_region
    (research 02 / REALISM_BIBLE row 12): G ~ 0.21 L across the skin tension
    lines, ~0.035 L along them; a cut must pass the dermis to gape; scalp cuts
    through the galea gape wider. (tx, ty) = tension direction in the hit frame
    (the cut runs along local X). Returns (half_len, gape).
    """
    half_len = s * 0.012 * e
    sin2 = ty * ty / (tx * tx + ty * ty).max(1e-8)
    # (a cut through the muscle gapes more: the muscle retracts as well)
    G = 0.035 + 0.175 * sin2 + 0.045 * t.smooth(0.6, 0.9, D)
    f_depth = t.smooth(0.1, 0.5, D)
    # (a deep throat cut divides the platysma and strap muscles: they retract
    # and the wound gapes widely even along the neck's skin lines)
    f_reg = 1.0 + scalp * t.smooth(0.45, 0.6, D) * 0.45
    if neck is not None:
        f_reg = f_reg + neck * t.smooth(0.55, 0.8, D) * 1.6
    gape = (half_len * 2.0 * G * f_depth * f_reg).min(0.016)
    return half_len, gape


# lens(tt) = K (1 + tt)^A (1 - tt)^B: widest a quarter of the way in (where the
# blade went in deep), a short blunt-ish start and a long pointed tail; both
# ends come to an angle (exponents >= 0.9), never a rounded "mouth corner"
_LENS_A, _LENS_B = 0.9, 1.6
_LENS_K = 1.0 / ((1.0 + (_LENS_A - _LENS_B) / (_LENS_A + _LENS_B)) ** _LENS_A
                 * (1.0 - (_LENS_A - _LENS_B) / (_LENS_A + _LENS_B)) ** _LENS_B)


def _slash_lens(t, tt):
    """Opening profile along the cut (tt = -1 stroke start .. +1 stroke end), 0..1."""
    if isinstance(tt, (int, float)):
        x = min(max(tt, -1.0), 1.0)
        return _LENS_K * (1.0 + x) ** _LENS_A * (1.0 - x) ** _LENS_B
    x = t.clamp(tt, -1.0, 1.0)
    return _LENS_K * ((1.0 + x) ** _LENS_A) * ((1.0 - x) ** _LENS_B)


def _build_slash():
    """Incised cut along local X: the skin itself is cut and the lips gape.

    The knife line is a narrow hole; the gape comes from the two lips of skin
    being pulled apart (displaced sideways, fading out over ~1-2 cm), so the
    opening is a real gap between two raised, slightly swollen skin lips. The
    skin's own walls run down in a V to the depth of the cut (dermis -> fat ->
    muscle), so no deeper layer is opened (a knife never cuts the skull: bone
    only gets a score mark). Irregular outline, a deep start and a shallow
    scratch tail at the end of the stroke.
    """
    t = _kind_tree("GH_Gore_Slash", "Incised cut fields")
    c = _KindCtx(t)
    s, D, u, v = c.s, c.D, c.u, c.v
    is_skin = c.is_layer(LAYER_SKIN)
    is_bone = c.lc(LAYER_IS_BONE)
    tens = t.inp("Tension")
    half_len, gape = _slash_params(t, s, c.e, D, tens.x, tens.y, t.inp("Region").x, t.inp("Region").z)
    tt = u / half_len
    # the cut line bows and wanders a little
    bow = (c.hash(1) - 0.5) * 0.16
    vc = v - half_len * bow * (1.0 - tt * tt).max(0.0) \
        - s * 0.0004 * t.noise(t.vec(u * 70.0, c.seed * 5.0, 0.0), detail=2.0)
    av = t.math('ABSOLUTE', vc)
    sgn = t.math('SIGN', vc)
    lens = _slash_lens(t, tt)
    # each lip has its own irregular outline: 3-5 lobes of +-25-40 % per lip
    # at the 5-15 mm scale, smaller 2-6 mm wobbles, and only a faint
    # micro-roughness (strong fine notches read as a zip fastener)
    lobes = 1.0 + 0.36 * t.noise(t.vec(u * 70.0, c.seed * 3.1 + sgn * 2.3, 0.0), detail=1.0) \
        + 0.16 * t.noise(t.vec(u * 260.0, c.seed * 1.7 - sgn * 4.1, 0.0), detail=1.0)
    wide = t.smooth(0.002, 0.008, gape)
    micro = t.noise(c.np * 1400.0, detail=1.0) * (0.00002 + 0.00004 * wide) \
        + t.noise(c.np * 600.0, detail=1.0) * (0.00005 + 0.00007 * wide)
    hw = (0.00055 + gape * 0.15 * lobes) * lens + micro * t.smooth(0.0, 0.25, lens)
    d_rim = gape * 0.35 * lens * lobes                       # how far each lip is pulled back
    opened = is_skin * D.gt(0.04)
    # (where the opening would be thinner than ~0.3 mm the blade only scored
    # the skin: no hole, the scratch tail takes over -- a hairline hole with a
    # noisy outline would open and close in a saw-tooth)
    # (the test uses the smooth opening width, so lobes cannot pinch the cut
    # into separate islands with skin slivers between them)
    hw0 = (0.00055 + gape * 0.15) * lens
    cut = t.switch(opened.gt(0.5), -1.0, (hw.max(0.00032) - av).min(hw0 - 0.0003))
    d_out = av - hw                                           # distance outside the knife line
    # gaping: the lips retract, the pull fades over W (never folds: slope < 1)
    W = (d_rim * 2.6).max(0.006)
    fall = t.smooth(W, 0.0, d_out)
    gap_v = sgn * d_rim * fall * opened
    # swollen, slightly everted lips; a broad low swelling around the cut
    # (at most ~0.4 mm, varying +-50 % along the lip at 3-8 mm: the cut edge
    # shows its thin dermis line and sits flush or slightly everted, never a
    # rolled, sausage-like lip)
    lipn = t.noise(t.vec(u * 190.0, c.seed * 2.9 + sgn * 1.7, 0.0), detail=2.0)
    raise_ = ((0.00012 + 0.00022 * D) * t.smooth(0.0028, 0.0, d_out) * (1.0 + 0.5 * lipn)
              + 0.00012 * t.smooth(0.009, 0.0, d_out)) * (lens ** 0.5) * opened
    # superficial scratch tail past the end of the stroke (5-30 mm)
    tail_len = s * (0.005 + 0.02 * c.hash(3))
    ut = u - half_len * 0.72
    tail_f = t.smooth(-0.001, 0.001, ut) * t.smooth(tail_len, tail_len * 0.3, ut)
    tail_w = 0.00035 * (1.0 - (ut / tail_len).clamp())
    scratch = tail_f * t.smooth(tail_w + 0.0003, tail_w * 0.3, av + t.noise(c.np * 1800.0) * 0.00012) * is_skin
    groove = scratch * -0.00012
    # V walls: the skin wall runs from the retracted lip down to the centre
    # line at the depth of the cut (deep start, shallower toward the tail)
    along_d = t.smooth(-1.05, -0.6, tt) * (1.0 - 0.55 * t.smooth(-0.2, 1.0, tt))
    # (the neck has no bone close under the skin: a deep throat cut goes
    # 15-25 mm into the neck; the depth also wanders along the cut)
    neck = t.inp("Region").z
    vd = (0.0015 + D * 0.0115 * (1.0 + 1.1 * neck)) * (0.3 + 0.7 * along_d) \
        * (1.0 + 0.18 * t.noise(t.vec(u * 150.0, c.seed * 2.3, 0.0), detail=1.0))
    # a knife stops at the bone: the bed of a deep cut over the skull or the
    # cheekbone is the periosteum (the wall must not pierce the bone)
    # (the neck has no bone in front: a deep throat cut opens the strap
    # muscles down onto the larynx / trachea, ~15-20 mm)
    vd = vd.min((t.inp("Bone Depth").max(neck * 0.019) - 0.0004).max(0.0012))
    open_hw = hw + d_rim
    # near the two ends the walls also lean in along the cut, so the V closes
    # at the tips too (walls that only move sideways leave a slot at each end)
    end_u = -(u - t.clamp(u, -half_len * 0.8, half_len * 0.8))
    wall = t.vec(end_u, -sgn * open_hw, -vd)
    center = t.vec(end_u, -sgn * (av + d_rim * fall), 0.0)
    # bone under a deep cut is only scored (<= 1 mm), never opened
    zl = c.lc(LAYER_Z)
    reach = t.smooth(0.5, 0.65, D)
    score = reach * is_bone * t.smooth(open_hw * 0.7, open_hw * 0.15, av) * t.smooth(1.0, 0.8, t.math('ABSOLUTE', tt))
    # soft tissue under the trench is exposed (seen at the bottom of the V)
    under = (1.0 - is_skin) * (1.0 - is_bone) * zl.lt(vd).max(0.0)
    exposed = under * t.smooth(open_hw * 1.1, open_hw * 0.5, av) * lens.gt(0.02) * D.gt(0.04)
    disp = t.vec(0.0, gap_v, raise_ - score * 0.0008) + t.vec(0.0, 0.0, groove)
    # the cut skin margin itself: raw dermis only right at the edge
    wound = (t.smooth(0.00035, 0.0, d_out) * opened * lens.gt(0.01)).max(exposed).max(score).max(scratch * 0.35)
    # blood: the bed fills (the blood-fill sheet, see _build_cut) and overflows
    # the LOWEST point of the lower lip into the traced runs (_build_blood).
    # Nothing is painted on the skin beside the cut; the cut dermis edge itself
    # is wet (<= ~1 mm) and the scratch tail beads a little.
    bleed = t.inp("Bleed")
    lip_wet = t.smooth(0.0009, 0.0, d_out) * lens.gt(0.02) * opened * bleed \
        * (0.5 + 0.5 * t.smooth(-0.4, 0.3, t.noise(c.np * 260.0, detail=1.0)))
    # bone reached by the cut lies in a pool of blood (periosteum, not white bone)
    bone_bed = reach * is_bone * t.smooth(open_hw * 1.3, open_hw * 0.6, av) * lens.gt(0.02)
    blood = lip_wet.max(exposed * 0.9).max(bone_bed).max(scratch * 0.3 * bleed)
    _finish_kind(t, cut, disp=disp, wall=wall, center=center, wound=wound, edge=scratch, blood=blood)
    return t


def _build_blunt():
    """Blunt trauma: swelling, bruise, split (laceration) over bone, depressed fracture.

    Research 02 / REALISM_BIBLE rows 15-17: blunt lacerations split the skin
    against the bone: a linear or Y-shaped split along the skin's lines
    (through the vermilion on a lip), crushed and ragged margins with a
    2-4 mm abraded rim, tissue bridges spanning the floor, walls down to the
    bone, blood welling in the bed. Swelling (up to a 4-10 mm goose egg) and
    the bruise develop with the wound age: redness at once, a bruise over
    30-60 min, the full deep bruise after hours.
    """
    t = _kind_tree("GH_Gore_Blunt", "Blunt trauma fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_skin = c.is_layer(LAYER_SKIN)
    is_muscle = c.is_layer(LAYER_MUSCLE)
    is_bone = c.lc(LAYER_IS_BONE)
    is_brain = c.is_layer(LAYER_BRAIN)
    # (the eyeball never swells: a blow deflates it, see eye_injury)
    soft = c.lc([1.0, 0.35, 0.0, 0.0, 0.0, 0.0, 0.0, 0.6])
    nl = t.noise(c.np * 120.0, detail=3.0)
    hours = t.inp("Age") * t.inp("Age") * 48.0
    # swelling: some at once, most within the first hours (peak ~24 h)
    # (a goose egg of 5-10 mm is visible within the first hours)
    f_sw = 0.35 + 0.65 * t.smooth(0.02, 3.0, hours)
    # a broad goose egg: radius ~25 mm, 8-12 mm high at full swelling, with
    # a soft falloff (reads from the front as a changed contour)
    rsw = s * 0.025
    # (the face swells less than the scalp's goose egg: lips and cheeks 3-6 mm)
    swell = t.inp("Swelling") * (0.007 + 0.009 * s.min(1.3)) * f_sw * (1.0 - 0.45 * t.inp("Region").y) \
        * t.math('EXPONENT', -(c.rho / rsw) ** 2.0) * (1.0 + nl * 0.25) * soft
    # accumulated blows (several hits on one area, see _build_hit_points):
    # the facial skeleton breaks into pieces and the contour caves in
    cr = t.inp("Crush")
    # bruise: immediate redness only, a bruise over 30-60 min, deep after hours
    f_br = 0.18 + 0.47 * t.smooth(0.05, 1.0, hours) + 0.35 * t.smooth(3.0, 24.0, hours)
    # (a blow that splits the scalp or a lip bruises 3-6 cm around it; the
    # bruise is densest at the margin and fades out in irregular lobes)
    rb = s * 0.03 * (0.8 + 0.3 * t.smooth(0.2, 24.0, hours))
    bruise = t.smooth(1.25, 0.2, c.rho / rb + nl * 0.4) * (0.72 + 0.28 * t.noise(c.np * 420.0))
    bruise = (bruise * t.inp("Bruising") * f_br * 1.5).min(1.0) * c.lc([1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    # the split: 2 arms (linear) or 3 (Y) along the skin's lines, around a
    # small crushed centre; each arm is a thin wedge whose walls close in a V
    split_on = t.smooth(0.25, 0.45, D) * is_skin + t.smooth(0.55, 0.7, D) * is_muscle * 0.45
    crush0 = t.smooth(0.8, 1.0, D)
    k_sz = s * t.switch(is_muscle.gt(0.5), 1.0, 0.55 + 0.4 * crush0)
    crush = crush0 * (is_skin + is_muscle * 1.1)
    rc = k_sz * 0.0018 * (1.0 + 0.45 * nl) + crush * s * 0.0032 * (1.0 + 0.5 * nl)
    tens = t.inp("Tension")
    phi0 = t.math('ARCTAN2', tens.y, tens.x)
    y_shape = c.hash(9).gt(0.5).max(0.0)
    arms = ((phi0, 1.0, 1.1), (phi0 + math.pi, 1.0, 0.85), (phi0 + 1.9, y_shape, 0.7),
            (phi0 - 1.2, crush, 0.6))
    cut_arm = to_line = None
    for k, (phi, on, ln) in enumerate(arms):
        tn = t.group(_sub("tear"), {"U": c.u, "V": c.v, "Seed": c.seed, "K": float(k),
                                    "Size": k_sz * (1.0 + 0.35 * crush), "Core": rc, "Noise Pos": c.np,
                                    "Gape": (1.0 + crush * 2.2) * 1.15, "Phi": phi, "Phi Mix": 1.0,
                                    "Length": on * ln * 1.25})
        ck, line_k = t.out(tn, "Cut"), t.out(tn, "Line")
        if isinstance(on, float) and on < 1.0:
            ck = ck - 1.0 + 1.0 * on
        elif not isinstance(on, float):
            ck = ck - (1.0 - on) * 0.01
        if cut_arm is None:
            cut_arm, to_line = ck, line_k
        else:
            to_line = t.switch(ck.gt(cut_arm), to_line, line_k, 'VECTOR')
            cut_arm = cut_arm.max(ck)
    cut_centre = rc - c.rho + s * 0.0003 * t.noise(c.np * 1300.0) \
        + crush * s * 0.0014 * t.noise(c.np * 330.0, detail=2.0)
    # crushed, ragged margins (not a clean cut)
    # (irregular lobes and notches at 2-6 mm; only a little fine fraying -- a
    # strong high-frequency term reads as a saw-toothed paper edge)
    ragged = t.noise(c.np * 1500.0, detail=1.0) * 0.00018 + t.noise(c.np * 450.0, detail=2.0) * 0.0007 \
        + t.noise(c.np * 180.0, detail=2.0) * 0.0011 + t.noise(c.np * 800.0, detail=2.0) * 0.0004
    cut_split = cut_centre.max(cut_arm) + ragged
    in_arm = cut_arm.gt(cut_centre)
    # tissue bridges: thin strands of nerves / vessels / fibrous tissue that
    # were not torn, spanning the split
    # (a few, irregular: 1-3 per split, not a row of evenly spaced rungs)
    br_n = t.noise(c.np * 380.0 + t.vec(c.seed * 3.0, 0.0, 0.0), detail=2.0, signed=False)
    bridge = t.smooth(0.032, 0.01, t.math('ABSOLUTE', br_n - 0.5)) \
        * t.smooth(0.56, 0.7, t.noise(c.np * 90.0 + t.vec(0.0, c.seed * 5.0, 0.0), detail=1.0, signed=False)) \
        * (1.0 - crush)
    cut_split = cut_split - bridge * is_skin * 0.004
    cut_soft = t.switch(split_on.gt(0.05), -1.0, cut_split)
    # crushed face: the skin is torn away over a large ragged area (flaps
    # around it), the muscle under it is pulped open as well
    soft_cr = c.lc([1.0, 0.92, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    ring_c = t.vec(c.theta.cos() * 1.2, c.theta.sin() * 1.2, c.seed * 3.7)
    lf_c = t.noise(ring_c, detail=3.0, signed=False)
    tears_c = c.tears(6, first=10, width=(0.12, 0.35), length=(0.3, 1.0), sharp=1.4, wobble=0.25)
    R_cr = s * (0.004 + 0.02 * cr) * soft_cr
    r_cr = R_cr * (0.5 + 0.75 * lf_c + 0.3 * tears_c) \
        + t.noise(c.np * 150.0, detail=2.0) * 0.0015 + t.noise(c.np * 420.0, detail=1.0) * 0.0004
    cut_cr = t.switch(t.bool('AND', cr.gt(0.08), soft_cr.gt(0.5)), -1.0, r_cr - c.rho)
    cut_soft = cut_soft.max(cut_cr)
    d_cr = c.rho - r_cr                                   # distance outside the crushed opening
    # depressed skull fracture with radiating cracks
    dep_on = t.smooth(0.62, 0.85, D) * is_bone
    rd = s * 0.015
    lines, plate = c.cracks(rd, n_around=7.0, width=0.0005)
    # the ring fracture is an irregular loop, not a circle
    ring_dir = t.vec(c.theta.cos() * 0.9, c.theta.sin() * 0.9, c.seed * 5.0)
    rd_th = rd * (0.8 + 0.45 * t.noise(ring_dir, detail=2.0, signed=False)) + nl * 0.0015
    inside = t.smooth(rd_th * 1.04, rd_th * 0.94, c.rho)
    depress = dep_on * s * 0.0048 * inside * (0.4 + 0.6 * plate) * t.smooth(rd * 1.1, rd * 0.2, c.rho).max(0.35)
    ring_crack = t.smooth(0.0007, 0.0002, t.math('ABSOLUTE', c.rho - rd_th))
    frac = (lines * t.smooth(rd * 2.8, rd * 0.9, c.rho)).max(ring_crack) * dep_on
    breach = (t.smooth(0.94, 0.99, D).max(t.smooth(0.25, 0.45, cr))) * is_bone
    # (crushed: the bone breaks into a large hole of loose plates; its edge
    # follows the crack network, so it is jagged, not round)
    r_bb = s * (0.0045 + 0.017 * cr) * (1.0 + nl * 0.3 + 0.25 * cr * (plate - 0.5)) \
        + cr * s * 0.004 * lines
    cut_bone = t.switch(breach.gt(0.5), -1.0, r_bb - c.rho)
    cut = cut_soft.max(cut_bone)
    # contour collapse: skin, muscle and bone cave in 5-15 mm under crushing
    # blows; the loose plates at the edge of the bone hole are pushed in
    # (broad: the whole mid-face flattens, so the silhouette changes -- §5.18 D)
    cave = cr * s * 0.015 * t.math('EXPONENT', -(c.rho / (s * 0.042)) ** 2.0) \
        * c.lc([1.0, 1.0, 0.8, 0.8, 0.5, 0.0, 0.0, 1.0]) * (1.0 + 0.3 * nl)
    depress = depress * (1.0 + 1.5 * cr)
    # everted flaps around the torn-away skin: lifted and curled outward so
    # their pale fatty undersides show
    flap_cr = t.smooth(R_cr * 0.6 + 0.004, 0.0, d_cr) * cr * soft_cr
    curl_c = 0.6 + 0.6 * t.noise(c.np * 90.0, detail=1.0, signed=False)
    lift_cr = flap_cr * flap_cr * s * 0.0035 * curl_c
    # the eye sinks into the broken orbit (the globe moves back along the hit)
    # (enophthalmos of a blow-out fracture: 2-5 mm in all; the blows of a
    # crushed face add up, so each one moves it only a little)
    sink_eye = c.is_layer(LAYER_EYE) * cr * s * 0.0017 * t.smooth(0.05, 0.025, c.rho)
    # (the flaps fold back outward over the face, fatty side up, rather than
    # standing up as petals)
    # fade the broad cave-in and the puffy ring out before the edge of the
    # refined patch (see _Hit.within): displacement still rising across the
    # patch seam shows as a pale crease arc on the forehead and cheek
    rad_p = s * 0.02 * (1.0 + 1.3 * cr) + 0.002
    fit = t.smooth(rad_p, rad_p * 0.6, c.rho)
    cave = cave * fit
    disp = t.vec(0.0, 0.0, -depress - frac * dep_on * 0.0005 - sink_eye + lift_cr * 0.35) + c.radial * (lift_cr * 1.3)
    # ---- the nose is part of the injury (REFERENCE_NOTES §5.20.1) -----------
    # a blow on or beside the nose (or a crushed mid-face) breaks the nasal
    # bones and cartilage: the nose is pushed flat and to the side, droops,
    # swells, splits over the tip / dorsum and bleeds from the nostrils
    P = c.P
    Io = c.impact_obj()
    near_nose = t.smooth(0.052, 0.022, (Io - NOSE_C).length())
    nose_hit = (near_nose * (t.smooth(0.78, 1.0, D) * 0.6 + cr * 1.2)).clamp()
    ax_ = t.math('ABSOLUTE', P.x)
    prot = t.smooth(-0.089, -0.106, P.y) * t.smooth(0.024, 0.011, ax_) \
        * t.smooth(-0.040, -0.030, P.z) * t.smooth(0.030, 0.016, P.z)
    nose_lay = c.lc([1.0, 1.0, 0.7, 0.0, 0.0, 0.0, 0.0, 0.0])
    nf = nose_hit * prot * nose_lay
    # deviated away from the side the blow came from (random when head-on)
    side_ = t.math('SIGN', Io.x + (c.hash(41) - 0.5) * 0.004) * -1.0
    nose_disp = t.vec(side_ * (0.0045 + 0.002 * c.hash(42)) * nf * prot,
                      (0.009 + 0.004 * c.hash(43)) * nf * prot,
                      -0.0018 * nf)
    # nasal laceration: the skin bursts over the broken dorsum and tip
    NA = t.vec(side_ * -0.0015, -0.1035, 0.004)
    NB = t.vec(side_ * 0.0015, -0.1112, -0.0125)
    ba = NB - NA
    pa = P - NA
    hq = (pa.dot(ba) / ba.dot(ba)).clamp()
    to_seg = NA + ba * hq - P
    d_seg = to_seg.length()
    nose_cut_amt = nose_hit * t.smooth(0.15, 0.45, cr + t.smooth(0.85, 1.0, D) * 0.5) \
        * c.lc([1.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
    hw_n = (0.0006 + 0.0011 * nose_cut_amt) * ((1.0 - (hq * 2.0 - 1.0) * (hq * 2.0 - 1.0)).max(0.0) ** 0.5) \
        * (1.0 + 0.35 * t.noise(c.np * 700.0, detail=2.0))
    cut_nose = t.switch(nose_cut_amt.gt(0.2), -1.0, hw_n - d_seg)
    disp = disp + c.to_hit(nose_disp)
    # (the broken nose swells moderately but never balloons into the round
    # goose egg of a blow over flat bone: that made the tip a pink ball)
    swell = swell * (1.0 - 0.85 * (prot * near_nose).clamp())
    # ---- swollen lids close over the eye (periorbital haematoma) ------------
    f_close = (t.smooth(0.7, 1.0, D) * 0.45 + cr) * t.inp("Swelling") * f_sw * is_skin \
        * t.smooth(s * 0.058, s * 0.042, c.rho)
    lid_disp = t.vec(0.0, 0.0, 0.0)
    for sx in (1.0, -1.0):
        ex, ey, ez = sx * 0.0315, -0.0675, 0.022
        near_e = t.smooth(0.058, 0.03, (Io - t.vec(ex, ey, ez)).length())
        dz_ = P.z - ez
        m_lid = t.smooth(0.021, 0.013, t.math('ABSOLUTE', P.x - ex)) * t.smooth(0.017, 0.010, t.math('ABSOLUTE', dz_)) \
            * t.smooth(-0.068, -0.077, P.y)
        cl = (near_e * f_close).clamp() * m_lid
        lid_disp = lid_disp + t.vec(0.0, -0.0035 * cl * t.smooth(0.017, 0.004, t.math('ABSOLUTE', dz_)),
                                    -dz_ * 0.72 * cl)
    disp = disp + c.to_hit(lid_disp)
    # ---- the eyeball: deflated / ruptured, hyphaema, haemorrhage ------------
    prox_e = t.smooth(0.036, 0.014, c.eye_axis_dist())
    rupt = prox_e * t.smooth(0.35, 0.8, cr + t.smooth(1.0, 1.2, D))
    eye = c.eye_injury(rupt, prox_e * (t.smooth(0.55, 0.95, D) * 0.3 + rupt * 0.7),
                       prox_e * (t.smooth(0.4, 0.85, D) * 0.85 + cr * 0.3))
    disp = disp + eye["disp"]
    # the margins are pushed apart a little and bulge (crushed, swollen lips)
    mg = t.smooth(0.003, 0.0, -cut_split) * split_on * is_skin
    swell = swell + mg * 0.0006 - cave
    # massive, tight swelling of the skin around a crushed area (a puffy ring
    # 5-9 mm high outside the torn opening: the face widens, the eye closes)
    ring_sw = t.smooth(0.0, R_cr * 0.5 + 0.003, d_cr) * t.smooth(s * 0.07, s * 0.02, c.rho)
    swell = swell + ring_sw * fit * cr * soft_cr * s * 0.0075 * (0.4 + 0.6 * t.inp("Swelling")) * (1.0 + 0.3 * nl)
    # pulped muscle exposed in the crushed area: lumpy, torn
    swell = swell + is_muscle * cr * t.smooth(R_cr * 1.6 + 0.004, R_cr * 0.5, c.rho) \
        * (t.noise(c.np * 200.0, detail=3.0, rough=0.6) * 0.0025 + t.noise(c.np * 600.0, detail=2.0) * 0.0008)
    # blood: from the split (via the fill and the runs, nothing painted on the
    # skin), hematoma under the skin, contusion on the brain
    bleed = t.inp("Bleed")
    hema = t.smooth(rsw * 1.1, rsw * 0.3, c.rho) * c.lc([0.0, 0.85, 0.35, 0.35, 0.0, 0.0, 0.0, 0.8])
    contusion = t.smooth(rd * 1.3, rd * 0.4, c.rho + nl * 0.002) * is_brain * t.smooth(0.5, 0.8, D)
    # blood from the split lip and torn gum coats the teeth behind it
    teeth_blood = t.smooth(s * 0.03, s * 0.008, c.rho + t.noise(c.np * 200.0) * 0.004) \
        * (c.is_layer(LAYER_TEETH) + c.is_layer(LAYER_GUMS)) * t.smooth(0.2, 0.4, D) * 0.75
    blood = (hema * t.smooth(0.2, 0.5, D)).max(contusion).max(teeth_blood)
    # (only the torn margin itself is wet, <= ~1.5 mm)
    blood = blood.max(t.smooth(0.0015, 0.0, -cut_split) * split_on * (0.55 + 0.45 * bleed))
    blood = blood.max(t.smooth(0.002, 0.0, d_cr) * cr * soft_cr * (0.6 + 0.4 * bleed))
    # the broken plates of a crushed area lie in blood and pulp
    # (R_cr is zero on the bone layers: use the soft-tissue opening's size)
    R_crs = s * (0.004 + 0.02 * cr)
    # (every broken plate of the crushed area lies in blood and pulp: clean
    # cream plates at the crater's edge read as paper / plaster)
    blood = blood.max(is_bone * cr * t.smooth(R_crs * 2.8 + 0.012, R_crs * 1.2, c.rho)
                      * (0.78 + 0.22 * t.smooth(-0.3, 0.3, t.noise(c.np * 180.0, detail=2.0))))
    # subconjunctival haemorrhage of the eye near the blow (eye_injury)
    blood = blood.max(eye["blood"])
    # the broken nose: the split over it is wet, the whole nose swells
    blood = blood.max(t.smooth(0.0015, 0.0, d_seg - hw_n) * nose_cut_amt * 0.8)
    swell = swell + nf * 0.0014 * (1.0 + 0.3 * nl)
    # abraded, crushed margins (2-4 mm, dry brown-red, patchy)
    en = t.noise(c.np * 800.0, detail=2.0)
    edge = t.smooth(s * 0.0035, 0.0, -cut_split + en * 0.0009) * split_on * is_skin
    # patchy abrasion where the striking surface scraped the skin
    scrape = t.smooth(-0.1, 0.35, t.noise(c.np * 210.0, detail=3.0)) * t.smooth(s * 0.013, s * 0.004, c.rho + nl * 0.003)
    edge = edge.max(scrape * t.smooth(0.2, 0.5, D) * is_skin * 0.75)
    wound = (t.smooth(s * 0.0009, 0.0, -cut_split) * split_on).max(contusion * 0.5).max(frac * 0.4)
    wound = wound.max(t.smooth(s * 0.006, s * 0.0045, c.rho) * breach)
    wound = wound.max(t.smooth(0.0015, 0.0, d_cr) * cr * soft_cr)
    wound = wound.max(t.smooth(0.0006, 0.0, d_seg - hw_n) * nose_cut_amt).max(eye["wound"])
    edge = edge.max(eye["edge"])
    bruise = bruise.max(cr * t.smooth(s * 0.07, s * 0.012, c.rho + nl * 0.004)
                        * c.lc([1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]))
    # the broken nose bruises dark purple all over; hyphaema level on the eye
    bruise = bruise.max(nf.clamp() * 0.95 * t.inp("Bruising") * f_br * c.lc([1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]))
    bruise = bruise.max(eye["bruise"])
    cut = cut.max(cut_nose).max(eye["cut"])
    tw = c.lc(LAYER_WALL)
    # skin walls run down to the bone (the floor of a blunt split is the
    # bruised periosteum); the arms close in a V toward their mid line
    bd = t.inp("Bone Depth")
    # (bone: a short wall, about the thickness of the broken table -- long
    # extruded bone walls hang into the orbit and sinuses as pale paper sheets)
    wl = t.mix(tw * t.mix(0.55, 1.0, crush) * (1.0 - 0.6 * cr * is_bone), (bd * 0.95).min(0.012).max(0.002), is_skin)
    center = t.switch(in_arm, c.center, to_line, 'VECTOR')
    wall = t.vec(0.0, 0.0, -wl) + center * t.switch(in_arm, 0.75 - 0.6 * crush, 0.9)
    # walls of the crushed opening drop steeply (a crater, not a V)
    in_cr = cut_cr.gt(cut_split)
    center = t.switch(in_cr, center, c.center, 'VECTOR')
    wall = t.switch(in_cr, wall, t.vec(0.0, 0.0, -wl * 0.55) + c.center * 0.4, 'VECTOR')
    # the nasal split closes in a V toward its own line and runs in toward the
    # broken cartilage; the eye's tear runs in toward the centre of the globe
    seg_h = c.to_hit(to_seg)
    in_nose = cut_nose.gt(cut_soft.max(cut_bone))
    center = t.switch(in_nose, center, t.vec(seg_h.x, seg_h.y, 0.0), 'VECTOR')
    wall = t.switch(in_nose, wall, seg_h * 0.8 + c.to_hit(t.vec(0.0, 0.0028, 0.0)), 'VECTOR')
    on_eye = eye["on"].gt(0.5)
    center = t.switch(on_eye, center, t.vec(0.0, -c.v, 0.0), 'VECTOR')
    wall = t.switch(on_eye, wall, eye["wall"], 'VECTOR')
    _finish_kind(t, cut, disp=disp, dispn=swell, wall=wall, center=center, wound=wound, edge=edge,
                 blood=blood, bruise=bruise, fracture=frac)
    return t


# blisters: Voronoi cells of this size (1/m)
BLISTER_SCALE = 42.0          # few, large bullae (5-30 mm)
BLISTER_KEEP = 0.55           # cells with a random value above this blister


def _build_burn():
    """Burn: zones of different depth from a smooth, lobed dose field.

    From the edge inward (research 02 / REALISM_BIBLE row 18): a band of red
    skin; partial thickness with real blister domes (appearing 30 s-5 min
    after the burn and filling over hours) and lifted, curled sheets of dead
    epidermis; full thickness: waxy white / tan leather, sunk ~0.5-1 mm and
    shrinking, pulling the skin around toward it; a charred core that splits
    open along real fissures showing red and yellow tissue. The dose is also
    written as gore_burn, which the skin material turns into the zone colours.
    """
    t = _kind_tree("GH_Gore_Burn", "Burn fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_skin = c.is_layer(LAYER_SKIN)
    R = s * 0.022
    hours = t.inp("Age") * t.inp("Age") * 48.0
    # relief heights follow the tissue, not the burn's extent
    sd = s.min(1.2)
    # (distance over the surface, not in the hit plane: the face curves away)
    # (the depth term is halved: on the side of the head, which is nearly a
    # vertical cylinder, a full 3D distance cuts the dose off along vertical
    # lines)
    rho_e = (c.u * c.u + (c.v / c.e) ** 2.0 + c.w * c.w * 0.35).sqrt()
    # smooth dose with a lobed, irregular boundary (no thresholded noise)
    ring = t.vec(c.theta.cos() * 1.3, c.theta.sin() * 1.3, c.seed * 7.0)
    lobes = t.noise(ring, detail=2.0)
    n2 = t.noise(c.np * 70.0, detail=3.0)
    n3 = t.noise(c.np * 28.0 + t.vec(c.seed, 0.0, 0.0), detail=2.0)
    # heat rises: the dose licks upward in tongues (anisotropic, asymmetric),
    # and strong low-frequency variation makes the zones interlock unevenly
    # instead of forming concentric rings
    dn_ = c.down
    up_ = -(c.u * dn_.x + c.v * dn_.y) / (dn_.x * dn_.x + dn_.y * dn_.y).sqrt().max(1e-4)
    # (the tongues are separate: each licks up at its own lateral position and
    # tapers -- a lick independent of the lateral offset gave the burn long,
    # straight vertical sides, like a pasted rectangle)
    lat_ = (c.u * dn_.y - c.v * dn_.x) / (dn_.x * dn_.x + dn_.y * dn_.y).sqrt().max(1e-4)
    tongue = t.smooth(-0.25, 0.55, t.noise(t.vec(lat_ * 70.0, c.seed * 2.0, 0.0), detail=2.0))
    lick = t.smooth(-0.2, 1.0, up_ / R) * tongue * t.smooth(R * 1.05, R * 0.25, t.math('ABSOLUTE', lat_))
    # the lateral edges wander strongly (irregular zones, never a straight line)
    edge_w = t.noise(t.vec(up_ * 55.0, c.seed * 3.0, 1.7), detail=3.0) * 0.35 \
        + t.noise(c.np * 160.0, detail=2.0) * 0.08
    n4 = t.noise(c.np * 16.0 + t.vec(0.0, c.seed * 4.0, 0.0), detail=2.0)
    rn = rho_e / R * (1.0 + 0.45 * lobes) + 0.12 * n2 + 0.3 * n3 + 0.4 * n4 - 0.45 * lick + edge_w
    # soft edge: a 5-15 mm band of red skin; the flame tongues fade out well
    # inside the hit's reach (or the evaluation bounds show as a straight edge)
    # (the outer clamp is lobed too: a clean ellipse here gave the burn long
    # straight sides where two hits overlap)
    b = t.smooth(1.02, 0.12, rn) * t.smooth(R * 1.5, R * 1.1, rho_e * (1.0 + 0.3 * lobes) + edge_w * R * 0.5
                                            + n3 * R * 0.25)
    dose = (b * (0.55 + 0.6 * D)).clamp()
    partial = t.smooth(0.2, 0.3, dose) * t.smooth(0.56, 0.48, dose)
    full = t.smooth(0.52, 0.62, dose)
    char = t.smooth(0.72, 0.86, dose)
    # full thickness shrinks and sinks; the surrounding skin is pulled toward it
    sink = -(full * (0.00045 + 0.0004 * D) + char * 0.0003) * sd
    pull = t.smooth(0.25, 0.7, dose) * 0.07 * sd
    shrink = t.vec(-c.u * pull, -c.v * pull, 0.0)
    # blisters: domes of fluid under lifted epidermis, only on partial thickness
    bv = t.voronoi(c.np, BLISTER_SCALE, 'F1', 1.0)
    vd = t.out(bv, 'Distance')
    vcol = t.sep(t.vmath('ADD', t.out(bv, 'Color'), (0, 0, 0)))
    keep = t.smooth(BLISTER_KEEP, BLISTER_KEEP + 0.04, vcol[0])
    brad = 0.26 + vcol[1] * 0.2
    grow = t.smooth(0.008, 0.08, hours) * (0.55 + 0.45 * t.smooth(0.1, 8.0, hours))
    dome = (1.0 - (vd / brad) ** 2.0).max(0.0).sqrt()
    # flattened domes (a tense bulla stands 1-3 mm), wrinkled roof
    wrinkle = 1.0 + 0.12 * t.noise(c.np * 1400.0, detail=2.0)
    blister = partial * keep * dome * grow * (brad / BLISTER_SCALE) * 0.22 * sd * wrinkle
    # sloughed epidermis: raw patches with lifted, curled rims
    # (a few patches, not a web of squiggles)
    pm = t.noise(c.np * 55.0 + t.vec(3.1, 1.7, 0.4), detail=2.0)
    peel = t.smooth(0.24, 0.3, pm) * partial
    peel_rim = t.smooth(0.17, 0.23, pm) * t.smooth(0.33, 0.25, pm) * partial
    dn = sink + blister + peel_rim * sd * 0.0006 - peel * sd * 0.00025
    dn = dn * is_skin
    # charred skin splits: real fissures 1-2 mm wide
    fv = t.voronoi(c.np, 140.0, 'DISTANCE_TO_EDGE', 1.0)
    fe = t.out(fv, 'Distance') / 140.0
    fw = (0.00045 + 0.0004 * t.noise(c.np * 300.0, detail=1.0)) * t.smooth(0.8, 0.95, dose)
    cut = t.switch(t.bool('AND', is_skin.gt(0.5), fw.gt(0.00005)), -1.0, fw - fe)
    burn = dose * c.lc([1.0, 0.0, 0.0, 0.0, 0.0, 1.0, 1.0, 1.0])
    burn = burn.max(dose * t.smooth(0.55, 0.8, D) * c.lc([0.0, 0.8, 0.6, 0.6, 0.0, 0.0, 0.0, 0.0]))
    wound = (peel * is_skin).max(t.smooth(0.0012, 0.0, fe - fw) * t.smooth(0.8, 0.95, dose) * is_skin)
    # (on burns the edge channel carries the blister fluid mask for the shader)
    edge = t.smooth(0.0, 0.5, dome) * partial * keep * t.smooth(0.004, 0.03, hours) * is_skin
    blood = peel * 0.3 * t.inp("Bleed") * is_skin
    bd = t.inp("Bone Depth")
    wall = t.vec(0.0, 0.0, -(bd * 0.6).min(0.0035).max(0.0015))
    disp = shrink * is_skin
    # heat-shrunk skin pulls the lids and lips away from their openings: the
    # lower lid is dragged down and turned out (ectropion, the red inner lid
    # shows), the upper lid retracts, the lips pull apart
    P = c.P
    contract = t.smooth(0.35, 0.7, dose) * is_skin * sd
    pull_o = t.vec(0.0, 0.0, 0.0)
    for sx in (1.0, -1.0):
        ex, ez = sx * 0.0315, 0.022
        dz_ = P.z - ez
        m_lid = t.smooth(0.02, 0.012, t.math('ABSOLUTE', P.x - ex)) * t.smooth(0.016, 0.004, t.math('ABSOLUTE', dz_)) \
            * t.smooth(-0.068, -0.076, P.y)
        pull_o = pull_o + t.vec(0.0, -0.0006, t.math('SIGN', dz_) * 0.0016) * m_lid
    dm = P.z + 0.055
    m_lip = t.smooth(0.03, 0.02, t.math('ABSOLUTE', P.x)) * t.smooth(0.012, 0.003, t.math('ABSOLUTE', dm)) \
        * t.smooth(-0.082, -0.09, P.y)
    pull_o = pull_o + t.vec(0.0, -0.0004, t.math('SIGN', dm) * 0.0012) * m_lip
    disp = disp + c.to_hit(pull_o * contract)
    _finish_kind(t, cut, disp=disp, dispn=dn, wall=wall, center=(0.0, 0.0, 0.0), wound=wound, edge=edge,
                 blood=blood, burn=burn)
    return t


# Blast (explosive in the mouth / contact shotgun, REFERENCE_NOTES §5.11):
# crater radius per size unit and the broken-off mandible segment. The segment
# is a block of the jaw between two vertical fracture lines and a horizontal
# one, hinged at its lower edge and swung outward and down, WITH the teeth in
# it (the same rigid transform is applied to the tooth islands).
BLAST_R = 0.028               # crater radius (m) per unit of size
BLAST_ANGLE = (0.6, 1.05)     # hinge rotation of the jaw segment (rad, ~35-60 deg)
BLAST_SLOT = 0.0011           # half width of the fracture gaps in the jaw (m)


def _blast_fragment(t, s, hk, u, v, wT):
    """Broken-off mandible segment of a blast, in the hit frame.

    s: hit size, hk(k): per-hit random stream, (u, v, wT): hit-frame position
    with wT measured from the hit empty (same on every layer).
    Returns (in_frag, moved, slot): 1 inside the segment, the rigidly moved
    position (u', v', wT') of the point, and the signed distance to the nearest
    fracture line (< 0 inside a fracture gap).
    """
    # (a segment of ~25-40 mm: the incisors, a canine and a premolar or two)
    u1 = s * (-0.013 - 0.006 * hk(21))
    u2 = s * (0.004 + 0.006 * hk(22))
    vp = s * (-0.024 - 0.006 * hk(23))          # hinge line (lower fracture)
    wp = -0.014
    a = BLAST_ANGLE[0] + (BLAST_ANGLE[1] - BLAST_ANGLE[0]) * hk(24)
    # the fracture lines are jagged, not ruler-straight
    jag = t.noise(t.vec(v * 300.0, hk(25) * 7.0, 0.0), detail=2.0) * 0.0012
    jag_h = t.noise(t.vec(u * 300.0, hk(26) * 7.0, 3.0), detail=2.0) * 0.001
    uu = u + jag
    vv = v + jag_h
    in_u = t.bool('AND', uu.gt(u1), uu.lt(u2))
    in_frag = t.switch(t.bool('AND', in_u, vv.gt(vp)), 0.0, 1.0)
    # distance to the three fracture lines (only along the segment's extent)
    d1 = t.math('ABSOLUTE', uu - u1) + (vp - vv).max(0.0) * 4.0
    d2 = t.math('ABSOLUTE', uu - u2) + (vp - vv).max(0.0) * 4.0
    d3 = t.math('ABSOLUTE', vv - vp) + (u1 - uu).max(0.0) * 4.0 + (uu - u2).max(0.0) * 4.0
    slot = d1.min(d2).min(d3) - BLAST_SLOT
    cos_a, sin_a = a.cos(), a.sin()
    dv, dw = v - vp, wT - wp
    v2 = vp + dv * cos_a - dw * sin_a - s * 0.004
    w2 = wp + dv * sin_a + dw * cos_a + s * 0.003
    # a slight twist about the jaw's vertical axis (one side hangs lower)
    twist = (hk(27) - 0.5) * 0.35
    u2_ = u + (w2 - wp) * twist * 0.3 + (u - (u1 + u2) * 0.5) * (-0.04)
    v2 = v2 + (u - (u1 + u2) * 0.5) * twist * 0.25
    return in_frag, (u2_, v2, w2), slot


def _build_blast():
    """Explosive in the mouth / contact shotgun blast (REFERENCE_NOTES §5.11, ref 13).

    The lower-mid face is blown open from the mouth outward: a large crater
    (radius ~BLAST_R * size) of shredded skin and muscle with torn, everted
    flaps, reaching further up toward the nose and one cheek; the maxilla is
    breached; the mandible breaks along jagged fracture lines and a segment
    WITH TEETH swings out and down, hanging in the wound (see _build_teeth for
    the teeth and the loose, missing ones); bone chips lie in the tissue. The
    surrounding skin is seared, soot-blackened, stippled and swollen.
    """
    t = _kind_tree("GH_Gore_Blast", "Blast crater fields")
    c = _KindCtx(t)
    s, D = c.s, c.D
    is_skin = c.is_layer(LAYER_SKIN)
    is_jaw = c.is_layer(LAYER_JAW)
    is_bone = c.lc(LAYER_IS_BONE)
    R = s * BLAST_R
    # per layer: crater scale (skin widest, the maxilla only locally, the jaw
    # through its fragment and a small blown-out part)
    #                 skin  muscle skull jaw   brain eye  teeth gums
    k_lay = c.lc([1.0, 0.93, 0.5, 0.36, 0.0, 0.0, 0.0, 1.0])
    ring = t.vec(c.theta.cos() * 1.3, c.theta.sin() * 1.3, c.seed * 13.0)
    lf = t.noise(ring, detail=3.0, signed=False)
    star = c.tears(7, first=20, width=(0.1, 0.3), length=(0.25, 1.0), sharp=1.3, wobble=0.3)
    # the blast tears further up (nose, one cheek) than down
    phi_up = math.pi * 0.5 + (c.hash(31) - 0.5) * 1.2
    up = t.smooth(-0.3, 1.0, (c.theta - phi_up).cos())
    r = R * (0.5 + 0.35 * lf + 0.35 * star + 0.35 * up) * k_lay
    # shredded margin: large lobes and fine tears
    r = r + (t.noise(c.np * 260.0, detail=2.0) * 0.0025 + t.noise(c.np * 900.0, detail=2.0) * 0.0008) \
        * (1.0 - is_bone * 0.5)
    on = t.smooth(0.3, 0.5, D) * k_lay.gt(0.05)
    cut_crater = t.switch(on.gt(0.5), -1.0, r - c.rho)
    # deep in the mouth (tongue, palate lining, floor of the mouth, more than
    # ~3 cm behind the lips) the blast shreds and perforates the tissue but
    # does not erase it: a hole there only looks into a black void, while the
    # references show torn, pulped, blood-soaked tissue everywhere (§5.15)
    soft_in = c.lc([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    # (the tongue is a solid organ in a closed mesh: a hole would show its
    # hollow inside; it is torn by deep ragged craters pushed into it instead)
    deep = t.smooth(-0.011, -0.019, c.wT) * soft_in
    lac = t.noise(c.np * 140.0 + t.vec(c.seed * 3.0, 0.0, 0.0), detail=3.0, signed=False)
    in_cr = t.smooth(R * 1.1, R * 0.6, c.rho) * on
    lac_dent = t.smooth(0.5, 0.72, lac) * in_cr * deep * 0.0045
    cut_crater = t.mix(cut_crater, -1.0, deep)
    # the mandible segment: fracture gaps separate it, it is moved rigidly
    in_frag, moved, slot = _blast_fragment(t, s, c.hash, c.u, c.v, c.wT)
    frag_on = is_jaw * t.smooth(0.5, 0.7, D)
    cut_slot = t.switch(frag_on.gt(0.5), -1.0, -slot)
    # (the jaw's own crater never eats the segment)
    cut_crater = t.switch(t.bool('AND', is_jaw.gt(0.5), in_frag.gt(0.5)), cut_crater, -1.0)
    cut = cut_crater.max(cut_slot)
    frag_disp = t.vec(moved[0] - c.u, moved[1] - c.v, moved[2] - c.wT) * (in_frag * frag_on)
    d_out = c.rho - r
    # torn, everted flaps curling outward (fatty undersides show), shredded
    flap = t.smooth(R * 0.4, 0.0, d_out) * on * c.lc([1.0, 0.6, 0.0, 0.0, 0.0, 0.0, 0.0, 0.5])
    curl = 0.5 + 0.8 * t.noise(c.np * 120.0, detail=2.0, signed=False)
    lift = flap * flap * s * 0.0042 * curl
    # surrounding tissue swollen, a ring 1-2 R out
    swell = is_skin * s * 0.0035 * t.smooth(R * 2.4, R * 1.1, c.rho) * t.smooth(0.0, R * 0.3, d_out) * on
    # the exposed soft tissue inside the crater (muscle, mouth lining, tongue,
    # gums) is pulped: lumpy, shredded, never a smooth lining
    pulp_on = c.lc([0.0, 1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 1.0]) * on * t.smooth(R * 1.15, R * 0.55, c.rho)
    pulp = (t.noise(c.np * 70.0, detail=2.0) * 0.003 + t.noise(c.np * 180.0, detail=3.0, rough=0.6) * 0.0028
            + t.noise(c.np * 520.0, detail=2.0) * 0.0009) * pulp_on * s.min(1.6)
    swell = swell + pulp - lac_dent
    disp = t.vec(0.0, 0.0, lift) + c.radial * (lift * 0.7) + frag_disp
    # soot, searing and powder stippling on the skin around the crater
    soot = is_skin * on * t.smooth(R * 2.2, R * 0.9, c.rho + t.noise(c.np * 80.0, detail=2.0) * R * 0.5) \
        * (0.45 + 0.55 * t.noise(c.np * 500.0, detail=2.0, signed=False))
    sear = is_skin * on * t.smooth(R * 0.3, 0.0, d_out + t.noise(c.np * 200.0) * 0.004) * 0.3 \
        * (0.4 + 0.6 * t.smooth(-0.3, 0.4, t.noise(c.np * 120.0, detail=2.0)))
    vd = t.voronoi(c.np, 2200.0, 'F1', 1.0)
    dcell = t.sep(t.vmath('ADD', t.out(vd, 'Color'), (0, 0, 0)))[0]
    dots = t.smooth(0.34, 0.12, t.out(vd, 'Distance')) * dcell.lt(0.35 * t.smooth(R * 1.9, R, c.rho)).max(0.0)
    edge = (dots * is_skin * on).max(t.smooth(0.0015, 0.0, d_out) * on * (1.0 - is_skin))
    # raw pulped tissue and blood in and at the crater
    exposed = t.smooth(R * 1.1, R * 0.5, c.rho) * on * c.lc([0.0, 1.0, 1.0, 0.0, 0.0, 0.0, 0.0, 1.0])
    wound = (t.smooth(0.0015, 0.0, d_out) * on).max(exposed).max(t.smooth(0.001, -0.0005, slot) * frag_on)
    blood = (t.smooth(0.0015, 0.0, d_out) * on * 0.85) \
        .max(exposed * (0.35 + 0.45 * t.smooth(-0.2, 0.4, t.noise(c.np * 90.0, detail=2.0)))) \
        .max(frag_on * t.smooth(0.004, 0.0, slot) * 0.8)
    # the broken-off segment and the bone around the crater are bloody (the
    # bone must still read in patches)
    bone_bl = is_bone * on * t.smooth(R * 1.2, R * 0.4, c.rho) \
        * (0.35 + 0.6 * t.smooth(-0.2, 0.4, t.noise(c.np * 150.0, detail=2.0)))
    blood = blood.max(bone_bl).max(in_frag * frag_on * (0.45 + 0.5 * t.smooth(-0.3, 0.3, t.noise(c.np * 200.0))))
    frac = (t.smooth(0.004, 0.0, slot) * frag_on).max(is_bone * on * t.smooth(0.004, 0.0, d_out))
    bruise = is_skin * on * t.smooth(R * 2.0, R * 0.8, c.rho) * 0.6 * t.inp("Bruising")
    # walls: the crater drops straight in; the fracture gaps close along their line
    tw = c.lc(LAYER_WALL)
    in_gap = t.bool('AND', frag_on.gt(0.5), (-slot).gt(cut_crater))
    crater_wall = t.vec(0.0, 0.0, -tw * 1.6) + c.center * 0.12
    gap_wall = t.vec(0.0, 0.0, -tw * 0.6)
    wall = t.switch(in_gap, crater_wall, gap_wall, 'VECTOR')
    center = c.center
    fr_ = soot * 0.9
    _finish_kind(t, cut, disp=disp, dispn=swell, wall=wall, center=center, wound=wound, edge=edge,
                 blood=blood, bruise=bruise, burn=sear, fracture=fr_.max(frac))
    return t


KIND_BUILDERS = {
    "bullet": _build_bullet,
    "exit": _build_exit,
    "slash": _build_slash,
    "blunt": _build_blunt,
    "burn": _build_burn,
    "blast": _build_blast,
}


# ---------------------------------------------------------------------------
# Reading the hit empties
# ---------------------------------------------------------------------------
def _tension_region(t, I, N):
    """Skin tension line direction (object space, tangent to the surface) and
    region weights at an impact point I with outward surface normal N.

    Relaxed skin tension lines (Borges / Langer): horizontal on the forehead,
    scalp and neck; on the cheek they run down and out, parallel to the
    nasolabial fold. Returns (tension vector, region vector (scalp, face, neck)).
    """
    ax = t.math('ABSOLUTE', I.x)
    sx = t.math('SIGN', I.x)
    horiz = t.vmath('CROSS_PRODUCT', (0.0, 0.0, 1.0), N)
    d = t.vec(ax - 0.044, I.y + 0.074, I.z + 0.036)
    w_cheek = t.math('EXPONENT', -(d.dot(d)) / (0.026 * 0.026))
    cheek = t.vec(sx * 0.30, 0.22, -1.0)
    # the two fields point either way along a line: align before blending
    flip = t.switch(horiz.dot(cheek).lt(0.0), 1.0, -1.0)
    tv = t.mix(horiz * flip, cheek, w_cheek)
    # around the lips the lines run radially (vertical through the vermilion)
    dm = t.vec(I.x / 0.024, (I.y + 0.092) / 0.02, (I.z + 0.056) / 0.016)
    w_mouth = t.math('EXPONENT', -(dm.dot(dm)))
    tv = t.mix(tv, (0.0, 0.0, 1.0), w_mouth)
    tv = (tv - N * tv.dot(N)).normalize()
    scalp = (t.smooth(0.042, 0.066, I.z) + t.smooth(-0.035, 0.0, I.y) * t.smooth(-0.06, -0.02, I.z)).clamp()
    neck = t.smooth(-0.095, -0.12, I.z)
    face = ((1.0 - scalp) * (1.0 - neck)).clamp()
    return tv, t.vec(scalp, face, neck)


def _build_hit_points():
    """Collection of hit empties -> point cloud with the hit frame per point.

    Uses Collection Info (Separate Children, relative transforms) so every
    empty becomes one instance whose transform is the empty's transform in
    the modified object's space. Each hit is ray-cast along its local -Z onto
    the target (this layer's own mesh) to find the impact point for this layer.
    Everything is evaluated on the instance domain (no matrix attributes, and
    no attribute reads, so an empty collection evaluates without warnings).
    Stray empties (zero size, or far from this layer's surface) are dropped.
    """
    t = NodeTree("GH_Gore_HitPoints",
                 inputs=(("Collection", 'NodeSocketCollection'),
                         ("Target", 'NodeSocketGeometry'),
                         ("Layer Z", 'NodeSocketFloat', 0.0),
                         ("Kind", 'NodeSocketInt', 0)),
                 outputs=(("Points", 'NodeSocketGeometry'), ("Count", 'NodeSocketInt')),
                 description="Hit empties of one collection as points with frame attributes")
    ci = t.node('GeometryNodeCollectionInfo', {'Collection': t.inp("Collection"),
                                               'Separate Children': True, 'Reset Children': False},
                transform_space='RELATIVE')
    st = t.node('FunctionNodeSeparateTransform', [t.out(t.node('GeometryNodeInstanceTransform'))])
    T, R, S = t.out(st, 'Translation'), t.out(st, 'Rotation'), t.out(st, 'Scale')

    def axis(a):
        return t.out(t.node('FunctionNodeRotateVector', {'Vector': a, 'Rotation': R}))
    X, Y, Z = axis((1.0, 0.0, 0.0)), axis((0.0, 1.0, 0.0)), axis((0.0, 0.0, 1.0))
    # ray from just outside the empty along its -Z onto this layer
    back = 0.012
    ray = t.node('GeometryNodeRaycast', {'Target Geometry': t.inp("Target"), 'Source Position': T + Z * back,
                                         'Ray Direction': -Z, 'Ray Length': back + 0.09})
    is_hit = t.out(ray, 'Is Hit')
    fallback = T - Z * t.inp("Layer Z")
    I = t.switch(is_hit, fallback, t.out(ray, 'Hit Position'), 'VECTOR')
    N = t.switch(is_hit, Z, t.out(ray, 'Hit Normal'), 'VECTOR').normalize()
    # (normals of a closed shell point outward; keep N on the side the hit comes from)
    N = t.switch(N.dot(Z).lt(0.0), N, -N, 'VECTOR')
    seed = t.rand(0.0, 1.0, t.index(), t.inp("Kind") * 31 + 5)
    # hit_ok: the ray really reached this layer (not the fallback point); extra
    # geometry such as bone chips is only made on layers that were hit
    ok = t.switch(is_hit, 0.0, 1.0)
    tension, region = _tension_region(t, I, N)
    inst = t.out(ci)
    # stray empties: zero size, or nowhere near this layer
    near = t.out(t.node('GeometryNodeProximity', {'Target': t.inp("Target"), 'Source Position': T},
                        target_element='FACES'), 'Distance')
    stray = t.bool('OR', S.x.lt(1e-3), near.gt(0.035 + t.inp("Layer Z") * 1.5))
    inst = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': inst, 'Selection': stray}, domain='INSTANCE'))
    for name, val, dt in (("hit_I", I, 'FLOAT_VECTOR'), ("hit_X", X, 'FLOAT_VECTOR'),
                          ("hit_Y", Y, 'FLOAT_VECTOR'), ("hit_Z", Z, 'FLOAT_VECTOR'),
                          ("hit_S", S, 'FLOAT_VECTOR'), ("hit_N", N, 'FLOAT_VECTOR'),
                          ("hit_T", tension, 'FLOAT_VECTOR'), ("hit_R", region, 'FLOAT_VECTOR'),
                          ("hit_seed", seed, 'FLOAT'), ("hit_ok", ok, 'FLOAT'),
                          ("hit_P", T, 'FLOAT_VECTOR'), ("hit_W", (I - T).dot(Z), 'FLOAT')):
        inst = t.store(inst, name, val, dt, 'INSTANCE')
    pts = t.out(t.node('GeometryNodeInstancesToPoints', {'Instances': inst}))
    count = t.out(t.node('GeometryNodeAttributeDomainSize', {'Geometry': pts}, component='POINTCLOUD'),
                  'Point Count')
    # accumulated energy: repeated blows on one area add up (REFERENCE_NOTES
    # §5.13). hit_E = sum over the hits of this collection of depth * falloff
    # (full within 20 mm, none beyond 45 mm), including the hit itself.
    pts = t.store(pts, "hit_E", 0.0)
    rin, rout, cur = _repeat(t, count, [("Geometry", 'GEOMETRY', pts)])
    j = F(t, rin.outputs['Iteration'])
    g = cur["Geometry"]
    pj = t.sample(g, t.attr("hit_P", 'FLOAT_VECTOR'), j, 'FLOAT_VECTOR')
    sj = t.sample(g, t.attr("hit_S", 'FLOAT_VECTOR'), j, 'FLOAT_VECTOR')
    contrib = sj.z * t.smooth(0.045, 0.02, (t.attr("hit_P", 'FLOAT_VECTOR') - pj).length())
    g = t.store(g, "hit_E", t.attr("hit_E") + contrib)
    pts = _end_repeat(t, rout, [("Geometry", g)])["Geometry"]
    t.result("Points", pts)
    t.result("Count", count)
    t.layout()
    return t


class _Hit:
    """Frame of hit `i` sampled from a hit point cloud (fields on the layer)."""

    def __init__(self, t, pts, i, damage, P=None):
        def smp(name, dt='FLOAT_VECTOR'):
            return t.sample(pts, t.attr(name, dt), i, dt)
        self.I = smp("hit_I")
        self.X, self.Y, self.Z = smp("hit_X"), smp("hit_Y"), smp("hit_Z")
        S = smp("hit_S")
        self.seed = smp("hit_seed", 'FLOAT')
        self.N, self.T, self.R = smp("hit_N"), smp("hit_T"), smp("hit_R")
        self.W = smp("hit_W", 'FLOAT')
        # damage grows the wounds; at damage 0 the whole system is bypassed
        self.s = S.x * (0.3 + 0.7 * damage)
        self.e = S.y.max(0.004)
        self.D = S.z * damage
        # crushing: summed depth of the blows on this area (a single blow of
        # depth <= 1 never crushes; three heavy blows on one spot do)
        self.crush = t.smooth(1.15, 2.3, smp("hit_E", 'FLOAT') * damage)
        P = P if P is not None else t.pos()
        d = P - self.I
        self.u, self.v, self.w = d.dot(self.X), d.dot(self.Y), d.dot(self.Z)
        self.rho = (self.u * self.u + self.v * self.v).sqrt()
        self.t = t

    def world(self, vl):
        """Hit-frame vector -> object space."""
        return self.X * vl.x + self.Y * vl.y + self.Z * vl.z

    def gate(self, layer, kind=None):
        """1 near this layer's impact surface, 0 on far-away surfaces (other side of the head).

        Burns are surface wounds that can cover half a face, so they follow the
        curved surface further in and out of the hit's tangent plane.
        """
        t = self.t
        tol_in = t.pick(layer, LAYER_TOL_IN) + self.rho * self.rho * 6.25
        tol_out = t.pick(layer, LAYER_TOL_OUT)
        if kind in ("burn", "blast"):
            # (the face curves away from the hit plane: nose, brow, jaw)
            tol_in = tol_in + 0.012 + self.rho * 0.9
            tol_out = tol_out + 0.02 + self.rho * 0.6
        if kind == "blast":
            # a blast destroys everything from the lips to ~6 cm deep: measured
            # from the hit empty, not from this layer's own impact (a ray into
            # the open mouth meets the mouth lining at the back of the throat,
            # so the lining around the teeth would lie "in front" of it)
            wT = self.w + self.W
            return t.smooth(-0.065, -0.06, wT) * t.smooth(0.03, 0.025, wT)
        return t.smooth(-tol_in - 0.003, -tol_in, self.w) * t.smooth(tol_out + 0.003, tol_out, self.w)

    def within(self, kind, reach=False, layer=None):
        """Cheap bounding test: where the wound needs refinement / has any effect."""
        t, s, e = self.t, self.s, self.e
        au, av = t.math('ABSOLUTE', self.u), t.math('ABSOLUTE', self.v)
        if kind == "slash":
            hl = s * 0.012 * e
            if reach:
                # (the lips' pull and the scratch tail reach well beyond the cut)
                return t.bool('AND', au.lt(hl + s * 0.03), av.lt(s * 0.024 + 0.004))
            return t.bool('AND', au.lt(hl * 1.04 + 0.002), av.lt(s * 0.0095 + 0.002))
        if kind == "burn":
            rr = (self.u * self.u + (self.v / e) ** 2.0 + self.w * self.w * 0.35).sqrt()
            if reach:
                # (beyond the dose field's lobed edge, so it never ends in a cut line)
                return rr.lt(s * 0.022 * 2.3 + 0.004)
            # only the skin blisters / peels, other layers keep their mesh
            return t.bool('AND', rr.lt(s * 0.026 + 0.002), t.compare('EQUAL', layer, LAYER_SKIN, 'INT'))
        if kind == "blast":
            if reach:
                # (soot, stippling and swelling reach ~2.4 crater radii)
                return self.rho.lt(s * BLAST_R * 2.6 + 0.004)
            return self.rho.lt(s * BLAST_R * 1.6 + 0.003)
        if kind == "blunt" and not reach:
            # skin/muscle only split near the centre, bone fractures further out
            # (a crushed area opens far wider)
            rad = s * t.pick(layer, [0.02, 0.018, 0.021, 0.021, 0.0, 0.03, 0.0, 0.012]) * (1.0 + 1.3 * self.crush)
            return self.rho.lt(rad + 0.002)
        if reach:
            # skin and muscle carry the long blood pools, bone only cracks, brain only craters
            #          skin   muscle skull  jaw    brain  eye    teeth  gums
            per = {"bullet": [0.034, 0.02, 0.014, 0.014, 0.012, 0.02, 0.03, 0.03],
                   "exit": [0.07, 0.04, 0.045, 0.045, 0.02, 0.03, 0.03, 0.03],
                   "blunt": [0.058, 0.04, 0.045, 0.045, 0.025, 0.04, 0.04, 0.04]}[kind]
            grow = (1.0 + 0.6 * self.crush) if kind == "blunt" else 1.0
            return self.rho.lt(s * t.pick(layer, per) * grow + 0.002)
        radius = {"bullet": 0.011, "exit": 0.035, "blunt": 0.021}[kind]
        return self.rho.lt(s * radius + 0.002)


def _repeat(t, iterations, items):
    """Create a repeat zone; items = [(name, socket_type, initial)]. Returns (rin, rout, dict)."""
    rin = t.nodes.new('GeometryNodeRepeatInput')
    rout = t.nodes.new('GeometryNodeRepeatOutput')
    rin.pair_with_output(rout)
    rout.repeat_items.clear()
    for name, stype, _ in items:
        rout.repeat_items.new(stype, name)
    t.wire(rin, 'Iterations', iterations)
    cur = {}
    for idx, (name, stype, init) in enumerate(items):
        t.wire(rin, rin.inputs[idx + 1].identifier, init)
        cur[name] = F(t, rin.outputs[idx + 1])
    return rin, rout, cur


def _end_repeat(t, rout, values):
    outs = {}
    for idx, (name, val) in enumerate(values):
        t.wire(rout, rout.inputs[idx].identifier, val)
        outs[name] = F(t, rout.outputs[idx])
    return outs


# ---------------------------------------------------------------------------
# Head vessel table: where the blood comes from
# ---------------------------------------------------------------------------
# Every bleeding wound takes its blood from the named vessels it cuts
# (REFERENCE_NOTES §5.19.3, REALISM_BIBLE §3.3-§3.7). The table lists the
# vessels of the head and upper neck in HEAD space (metres, origin between the
# ear canals, Z up, face -Y, character's LEFT = +X; "LR" rows are given for the
# left side and mirrored). Control points are approximate anatomical courses;
# build_vessels() snaps them onto this head: each point is projected onto the
# skin and pushed in to the vessel's depth (superficial vessels: fixed depth in
# the scalp / face, capped above the bone; intracranial ones: under the inner
# table of the skull, found by ray casting through the skull).
#
# Columns
#   id, name        stable id (the Godot game keys on it) and anatomical name
#   cls             artery | vein | deep_artery | sinus (see VESSEL_CLASSES)
#   side            "LR" (bilateral, left given) or "mid"
#   d_mm            lumen diameter
#   bleed_ml_min    initial external bleed when transected at normal BP (both
#                   cut ends of scalp/face vessels bleed: they are tethered and
#                   collateralised), untreated [RB §3.3, §3.7 C/E]
#   depth           mm below the skin, or "inner_table+N" = N mm inside the skull
#   pulsatile       arterial pressure: spurts / surges with the heartbeat
#   persist         0..1: how long it keeps pouring (scalp vessels are held open by
#                   the galea: 1; face vessels spasm and clot: ~0.4)
#   pts             control points (head frame, left side)
# Plexuses and beds without a named trunk (scalp venous plexus, facial dermis,
# diploic veins, brain) are area sources, handled per wound in _vessel_sources.
VESSEL_CLASSES = ("artery", "vein", "deep_artery", "sinus")
HEAD_VESSELS = (
    # --- scalp arteries (external carotid system), 3-6 mm deep in the dense
    # subcutaneous layer over the galea ---------------------------------------
    dict(id="HA01", name="superficial temporal artery", cls="artery", side="LR", d_mm=2.0, bleed_ml_min=40.0,
         depth=4.0, pulsatile=True, persist=1.0,
         pts=((0.064, -0.014, -0.034), (0.071, -0.012, -0.012), (0.074, -0.010, 0.012), (0.073, -0.008, 0.036))),
    dict(id="HA02", name="superficial temporal artery, frontal branch", cls="artery", side="LR", d_mm=1.5,
         bleed_ml_min=30.0, depth=3.5, pulsatile=True, persist=1.0,
         pts=((0.073, -0.008, 0.036), (0.068, -0.032, 0.056), (0.058, -0.058, 0.076), (0.042, -0.076, 0.094),
              (0.024, -0.082, 0.106))),
    dict(id="HA03", name="superficial temporal artery, parietal branch", cls="artery", side="LR", d_mm=1.5,
         bleed_ml_min=30.0, depth=3.5, pulsatile=True, persist=1.0,
         pts=((0.073, -0.008, 0.036), (0.074, 0.004, 0.066), (0.068, 0.016, 0.094), (0.054, 0.024, 0.114))),
    dict(id="HA04", name="occipital artery", cls="artery", side="LR", d_mm=2.0, bleed_ml_min=40.0, depth=4.5,
         pulsatile=True, persist=1.0,
         pts=((0.050, 0.052, -0.046), (0.040, 0.080, -0.010), (0.032, 0.094, 0.030), (0.026, 0.090, 0.070),
              (0.020, 0.070, 0.104))),
    dict(id="HA05", name="posterior auricular artery", cls="artery", side="LR", d_mm=1.2, bleed_ml_min=15.0,
         depth=3.5, pulsatile=True, persist=1.0,
         pts=((0.060, 0.016, -0.030), (0.066, 0.024, -0.004), (0.068, 0.030, 0.024), (0.064, 0.040, 0.050))),
    dict(id="HA06", name="supraorbital artery", cls="artery", side="LR", d_mm=1.0, bleed_ml_min=12.0, depth=3.0,
         pulsatile=True, persist=0.9,
         pts=((0.026, -0.086, 0.036), (0.028, -0.090, 0.058), (0.028, -0.084, 0.084), (0.024, -0.066, 0.108))),
    dict(id="HA07", name="supratrochlear artery", cls="artery", side="LR", d_mm=0.9, bleed_ml_min=10.0, depth=3.0,
         pulsatile=True, persist=0.9,
         pts=((0.012, -0.092, 0.036), (0.011, -0.095, 0.058), (0.010, -0.089, 0.084), (0.008, -0.072, 0.106))),
    # --- face arteries (5-10 mm deep, labial branches inside the lips) ---------
    dict(id="HA08", name="facial artery", cls="artery", side="LR", d_mm=2.5, bleed_ml_min=30.0, depth=7.0,
         pulsatile=True, persist=0.5,
         pts=((0.048, -0.030, -0.112), (0.046, -0.050, -0.092), (0.038, -0.072, -0.072), (0.030, -0.086, -0.056),
              (0.024, -0.094, -0.034), (0.019, -0.096, -0.012))),
    dict(id="HA09", name="angular artery", cls="artery", side="LR", d_mm=1.2, bleed_ml_min=10.0, depth=4.0,
         pulsatile=True, persist=0.5,
         pts=((0.019, -0.096, -0.012), (0.016, -0.094, 0.004), (0.014, -0.088, 0.018))),
    dict(id="HA10", name="superior labial artery", cls="artery", side="LR", d_mm=1.3, bleed_ml_min=15.0, depth=5.0,
         pulsatile=True, persist=0.45,
         pts=((0.027, -0.088, -0.052), (0.016, -0.097, -0.049), (0.0, -0.103, -0.047))),
    dict(id="HA11", name="inferior labial artery", cls="artery", side="LR", d_mm=1.1, bleed_ml_min=12.0, depth=5.0,
         pulsatile=True, persist=0.45,
         pts=((0.027, -0.088, -0.058), (0.016, -0.095, -0.063), (0.0, -0.099, -0.066))),
    dict(id="HA12", name="infraorbital artery", cls="artery", side="LR", d_mm=1.0, bleed_ml_min=6.0, depth=7.0,
         pulsatile=True, persist=0.4,
         pts=((0.027, -0.080, 0.002), (0.029, -0.086, -0.012), (0.030, -0.088, -0.026))),
    dict(id="HA13", name="transverse facial artery", cls="artery", side="LR", d_mm=1.0, bleed_ml_min=8.0, depth=6.0,
         pulsatile=True, persist=0.45,
         pts=((0.066, -0.020, -0.018), (0.058, -0.044, -0.022), (0.046, -0.066, -0.024))),
    dict(id="HA14", name="mental artery", cls="artery", side="LR", d_mm=0.8, bleed_ml_min=4.0, depth=5.0,
         pulsatile=True, persist=0.4,
         pts=((0.022, -0.084, -0.084), (0.014, -0.090, -0.090), (0.004, -0.092, -0.092))),
    # --- neck (below the jaw; a deep throat cut reaches them) ---------------------
    dict(id="HA15", name="common carotid / carotid bifurcation", cls="deep_artery", side="LR", d_mm=6.5,
         bleed_ml_min=600.0, depth=22.0, pulsatile=True, persist=1.0,
         pts=((0.024, -0.040, -0.196), (0.026, -0.034, -0.160), (0.030, -0.026, -0.128), (0.034, -0.018, -0.104))),
    # --- intracranial arteries (bleed out only through an opened skull) ---------
    dict(id="HA16", name="middle meningeal artery, frontal branch", cls="deep_artery", side="LR", d_mm=1.75,
         bleed_ml_min=8.0, depth="inner_table+1.0", pulsatile=True, persist=0.8,
         pts=((0.060, -0.012, -0.004), (0.064, -0.028, 0.020), (0.062, -0.040, 0.046), (0.054, -0.048, 0.074),
              (0.040, -0.050, 0.098))),
    dict(id="HA17", name="middle meningeal artery, parietal branch", cls="deep_artery", side="LR", d_mm=1.5,
         bleed_ml_min=6.0, depth="inner_table+1.0", pulsatile=True, persist=0.8,
         pts=((0.064, -0.008, 0.010), (0.070, 0.010, 0.030), (0.068, 0.034, 0.052), (0.058, 0.056, 0.074))),
    dict(id="HA18", name="ophthalmic / central retinal artery", cls="deep_artery", side="LR", d_mm=1.5,
         bleed_ml_min=5.0, depth=30.0, pulsatile=True, persist=0.6,
         pts=((0.016, -0.030, 0.014), (0.024, -0.046, 0.020), (0.030, -0.058, 0.023))),
    # --- veins (dark maroon, steady welling; valveless in the face) --------------
    dict(id="HV01", name="superficial temporal vein", cls="vein", side="LR", d_mm=2.0, bleed_ml_min=15.0, depth=4.5,
         pulsatile=False, persist=1.0,
         pts=((0.063, -0.006, -0.036), (0.070, -0.004, -0.010), (0.074, -0.002, 0.020), (0.074, 0.004, 0.050),
              (0.068, 0.012, 0.086), (0.056, 0.020, 0.110))),
    dict(id="HV02", name="occipital vein", cls="vein", side="LR", d_mm=2.0, bleed_ml_min=12.0, depth=5.0,
         pulsatile=False, persist=1.0,
         pts=((0.044, 0.060, -0.050), (0.036, 0.086, -0.012), (0.028, 0.096, 0.030), (0.022, 0.088, 0.074))),
    dict(id="HV03", name="supraorbital / supratrochlear veins", cls="vein", side="LR", d_mm=1.5, bleed_ml_min=8.0,
         depth=3.5, pulsatile=False, persist=0.9,
         pts=((0.016, -0.090, 0.024), (0.020, -0.094, 0.050), (0.020, -0.088, 0.080), (0.016, -0.072, 0.104))),
    dict(id="HV04", name="angular / facial vein", cls="vein", side="LR", d_mm=3.0, bleed_ml_min=20.0, depth=7.5,
         pulsatile=False, persist=0.5,
         pts=((0.016, -0.090, 0.020), (0.021, -0.093, -0.004), (0.030, -0.088, -0.030), (0.040, -0.074, -0.058),
              (0.050, -0.052, -0.090), (0.052, -0.034, -0.114))),
    dict(id="HV05", name="retromandibular vein", cls="vein", side="LR", d_mm=4.0, bleed_ml_min=40.0, depth=14.0,
         pulsatile=False, persist=0.6,
         pts=((0.062, -0.004, -0.030), (0.058, -0.004, -0.060), (0.054, -0.006, -0.090), (0.050, -0.008, -0.118))),
    dict(id="HV06", name="external jugular vein", cls="vein", side="LR", d_mm=5.0, bleed_ml_min=45.0, depth=4.0,
         pulsatile=False, persist=0.8,
         pts=((0.050, -0.008, -0.118), (0.048, -0.012, -0.150), (0.044, -0.018, -0.196))),
    dict(id="HV07", name="internal jugular vein", cls="sinus", side="LR", d_mm=14.0, bleed_ml_min=400.0, depth=24.0,
         pulsatile=False, persist=1.0,
         pts=((0.034, -0.012, -0.104), (0.032, -0.022, -0.140), (0.030, -0.030, -0.196))),
    # --- dural venous sinuses (rigid, do not collapse: heavy dark welling from an
    # open skull; air can be drawn in) -------------------------------------------
    dict(id="HV08", name="superior sagittal sinus", cls="sinus", side="mid", d_mm=9.0, bleed_ml_min=250.0,
         depth="inner_table+2.5", pulsatile=False, persist=1.0,
         pts=((0.0, -0.084, 0.060), (0.0, -0.066, 0.094), (0.0, -0.036, 0.116), (0.0, 0.002, 0.124),
              (0.0, 0.042, 0.116), (0.0, 0.074, 0.090), (0.0, 0.092, 0.050), (0.0, 0.094, 0.020))),
    dict(id="HV09", name="transverse / sigmoid sinus", cls="sinus", side="LR", d_mm=8.0, bleed_ml_min=200.0,
         depth="inner_table+2.5", pulsatile=False, persist=1.0,
         pts=((0.0, 0.094, 0.020), (0.026, 0.090, 0.014), (0.048, 0.072, 0.006), (0.060, 0.050, -0.002),
              (0.058, 0.036, -0.018), (0.050, 0.030, -0.030))),
)
# area sources: (mL/min at a typical wound, persist) [RB §3.7]
SCALP_SHEET = (20.0, 1.0)       # scalp laceration through the galea: 5-30, default 20; keeps pouring
FACE_DERMIS = (3.0, 0.35)       # dermal cut of the face without a named vessel: 1-5 per 3 cm, stops 5-15 min
DIPLOE_OOZE = (3.0, 0.8)        # cancellous skull bone: 0.3-1 per cm^2, clots poorly
BRAIN_OOZE = (6.0, 0.9)         # open skull / brain: 1-10 of blood, CSF and pulp
MUSCLE_OOZE = 0.5               # cut skeletal muscle: 0.2-1 mL/min per cm^2
# the same beds as table rows (machine-readable, exported with the vessels)
AREA_SOURCES = (
    dict(id="HB01", name="scalp venous plexus / scalp sheet (through the galea)", cls="plexus",
         region="scalp", bleed_ml_min=SCALP_SHEET[0], persist=SCALP_SHEET[1], pulsatile=False,
         note="per scalp laceration; vessels held open by the galea, keeps pouring"),
    dict(id="HB02", name="facial dermal capillaries", cls="capillary", region="face", bleed_ml_min=FACE_DERMIS[0],
         persist=FACE_DERMIS[1], pulsatile=False, note="per 3 cm of cut; clots in 5-15 min"),
    dict(id="HB03", name="diploic veins (cancellous skull)", cls="bone", region="skull", bleed_ml_min=DIPLOE_OOZE[0],
         persist=DIPLOE_OOZE[1], pulsatile=False, note="dark ooze from broken bone, clots poorly"),
    dict(id="HB04", name="brain / pia (blood, CSF and pulp)", cls="brain", region="brain", bleed_ml_min=BRAIN_OOZE[0],
         persist=BRAIN_OOZE[1], pulsatile=False, note="through an open skull, mixed with tissue"),
    dict(id="HB05", name="cut skeletal muscle", cls="muscle", region="any", bleed_ml_min=MUSCLE_OOZE,
         persist=0.5, pulsatile=False, note="mL/min per cm^2 of cut wall"),
)
VESSEL_OBJECT = "GH_Vessels"
DATA_COLLECTION = "GH_Data"
VESSEL_STEP = 0.0015            # resampling of the snapped courses (m)


def _catmull(pts, n_per):
    """Catmull-Rom through pts (list of Vector), n_per samples per segment."""
    if len(pts) < 2:
        return list(pts)
    ext = [pts[0] * 2.0 - pts[1]] + list(pts) + [pts[-1] * 2.0 - pts[-2]]
    out = []
    for i in range(1, len(ext) - 2):
        p0, p1, p2, p3 = ext[i - 1], ext[i], ext[i + 1], ext[i + 2]
        for k in range(n_per):
            u = k / n_per
            u2, u3 = u * u, u * u * u
            out.append(0.5 * ((2.0 * p1) + (-p0 + p2) * u + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * u2
                              + (-p0 + 3.0 * p1 - 3.0 * p2 + p3) * u3))
    out.append(pts[-1].copy())
    return out


def _resample(pts, step):
    """Polyline resampled at a fixed arc-length step (keeps both ends)."""
    if len(pts) < 2:
        return list(pts)
    seg = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]
    total = sum(seg)
    n = max(2, int(round(total / step)) + 1)
    out, i, acc = [], 0, 0.0
    for k in range(n):
        s = total * k / (n - 1)
        while i < len(seg) - 1 and acc + seg[i] < s:
            acc += seg[i]
            i += 1
        f = 0.0 if seg[i] < 1e-9 else min(1.0, (s - acc) / seg[i])
        out.append(pts[i].lerp(pts[i + 1], f))
    return out


def _mesh_bvh(names):
    """World-space BVH over the base meshes of the named objects (None if none exist)."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    obs = [bpy.data.objects.get(n) for n in names]
    obs = [o for o in obs if o is not None and o.type == 'MESH']
    if not obs:
        return None
    verts, polys = [], []
    for o in obs:
        me = o.data
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        mw = np.array(o.matrix_world)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        base = len(verts)
        verts.extend(map(Vector, co))
        polys.extend([base + i for i in p.vertices] for p in me.polygons)
    return BVHTree.FromPolygons(verts, polys)


def vessel_courses():
    """Snap every HEAD_VESSELS row onto this head.

    Returns a list of dicts (the table row plus "side_tag" L/R/M and "course":
    list of (x, y, z) in head space, resampled every VESSEL_STEP). Needs
    GH_Skin (and GH_Skull / GH_Jaw for the depth checks) in the scene.
    """
    skin = _mesh_bvh(("GH_Skin",))
    bone = _mesh_bvh(("GH_Skull", "GH_Jaw"))
    if skin is None:
        return []
    out = []
    for row in HEAD_VESSELS:
        sides = (("L", 1.0), ("R", -1.0)) if row["side"] == "LR" else (("M", 1.0),)
        for tag, sx in sides:
            course = []
            for p in row["pts"]:
                pw = Vector((p[0] * sx, p[1], p[2]))
                q, n, _i, _d = skin.find_nearest(pw)
                if q is None:
                    continue
                n = n.normalized()
                # (outward normal: away from the head's centre)
                if n.dot(q - Vector((0.0, -0.01, 0.0))) < 0.0:
                    n = -n
                depth = row["depth"]
                if isinstance(depth, str):
                    # under the inner table: through the outer and inner surface of the skull
                    extra = float(depth.split("+")[1]) * 0.001
                    d_in = None
                    if bone is not None:
                        o, travelled = q - n * 0.0005, 0.0005
                        hits = []
                        for _ in range(4):
                            loc, _nr, _ix, dist = bone.ray_cast(o, -n, 0.05)
                            if loc is None:
                                break
                            travelled += dist
                            hits.append(travelled)
                            o = loc - n * 1e-5
                        if len(hits) >= 2:
                            d_in = hits[1]
                    pos = q - n * ((d_in if d_in is not None else 0.013) + extra)
                else:
                    d = depth * 0.001
                    if bone is not None and p[2] > -0.105:
                        # superficial vessels lie above the bone (the ray stops there)
                        loc, _nr, _ix, dist = bone.ray_cast(q - n * 0.0005, -n, 0.03)
                        if loc is not None:
                            d = min(d, max(0.0015, dist - 0.001))
                    pos = q - n * d
                course.append(pos)
            if len(course) < 2:
                continue
            smooth = _catmull(course, 8)
            res = _resample(smooth, VESSEL_STEP)
            item = {k: v for k, v in row.items() if k != "pts"}
            item["side_tag"] = tag
            item["course"] = [tuple(round(c, 5) for c in v) for v in res]
            out.append(item)
    return out


def build_vessels():
    """(Re)build the hidden GH_Vessels data mesh the gore modifier reads.

    One vertex chain per snapped vessel course, with point attributes
    v_cls (index into VESSEL_CLASSES), v_flow (mL/min when transected),
    v_r (lumen radius, m), v_persist, v_id (row index) and v_pulse (1 = arterial).
    The object is never rendered. Returns the object (None without GH_Skin).
    """
    import numpy as np
    courses = vessel_courses()
    if not courses:
        return None
    verts, edges, cls, flow, rad, pers, vid, pulse = [], [], [], [], [], [], [], []
    ids = [r["id"] for r in HEAD_VESSELS]
    for c in courses:
        base = len(verts)
        for i, p in enumerate(c["course"]):
            verts.append(p)
            if i:
                edges.append((base + i - 1, base + i))
            cls.append(VESSEL_CLASSES.index(c["cls"]))
            flow.append(c["bleed_ml_min"])
            rad.append(c["d_mm"] * 0.0005)
            pers.append(c["persist"])
            vid.append(ids.index(c["id"]))
            pulse.append(1.0 if c["pulsatile"] else 0.0)
    me = bpy.data.meshes.get(VESSEL_OBJECT) or bpy.data.meshes.new(VESSEL_OBJECT)
    me.clear_geometry()
    me.from_pydata(verts, edges, [])
    for name, typ, vals in (("v_cls", 'INT', cls), ("v_flow", 'FLOAT', flow), ("v_r", 'FLOAT', rad),
                            ("v_persist", 'FLOAT', pers), ("v_id", 'INT', vid), ("v_pulse", 'FLOAT', pulse)):
        att = me.attributes.get(name) or me.attributes.new(name, typ, 'POINT')
        att.data.foreach_set("value", np.array(vals, dtype=np.int32 if typ == 'INT' else np.float32))
    me.update()
    ob = bpy.data.objects.get(VESSEL_OBJECT)
    if ob is None:
        ob = bpy.data.objects.new(VESSEL_OBJECT, me)
    ob.data = me
    col = bpy.data.collections.get(DATA_COLLECTION)
    if col is None:
        col = bpy.data.collections.new(DATA_COLLECTION)
        bpy.context.scene.collection.children.link(col)
    if ob.name not in col.objects:
        for c in list(ob.users_collection):
            c.objects.unlink(ob)
        col.objects.link(ob)
    ob.hide_render = True
    ob.display_type = 'WIRE'
    col.hide_render = True
    return ob


def export_vessel_table(path):
    """Write the snapped head vessel table as JSON (machine-readable for the Godot game).

    Head space (see CONTRACT.md); the body places the head at (0, 0.020, 1.647).
    """
    import json
    courses = vessel_courses()
    doc = {
        "frame": "gore_head space: metres, origin between the ear canals, Z up, face -Y, left +X",
        "body_offset": [0.0, 0.020, 1.647],
        "classes": list(VESSEL_CLASSES),
        "area_sources_ml_min": {"scalp_sheet": SCALP_SHEET[0], "face_dermis": FACE_DERMIS[0],
                                "diploe": DIPLOE_OOZE[0], "brain": BRAIN_OOZE[0]},
        "area_sources": [dict(a) for a in AREA_SOURCES],
        "colours": {"arterial_thin": "#C0141E", "venous_thin": "#8E1420", "pool": "#5E070C"},
        "vessels": [dict(c, id=f"{c['id']}_{c['side_tag']}") for c in courses],
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return path


# ---------------------------------------------------------------------------
# Blood: from the cut vessels, out of the wound, down the skin
# ---------------------------------------------------------------------------
# Sequence per wound (CLAUDE.md §8, REFERENCE_NOTES §5.9 / §5.17 / §5.19):
#   1. _vessel_sources: which named vessels (HEAD_VESSELS) and which beds
#      (scalp sheet, face dermis, diploe, brain) the wound cuts -> bleed rate Q
#      (mL/min), arterial share, tissue share, persistence;
#   2. _build_pools: the wound opening fills with ONE liquid body: a blood
#      surface welling up inside the hole (from the bottom of the track to the
#      rim) that spills over the LOW parts of the rim (the wet lip);
#   3. _drip_seeds + _walk: every run starts INSIDE that pool and walks down
#      the skin under gravity (the stream and the pool share the surface they
#      are flattened onto, so there is never skin between them), its front
#      advancing at 1-5 cm/s, widening with the volume, splitting into branches,
#      slowing in creases and hanging as drops where the skin faces down.
DRIP_STEPS = 48
BRANCH_STEPS = 26
WALK_RAMP = 6                   # the first steps of a run are 1/6 .. 1 of the full step (see _walk)
BLOOD_KINDS = ("bullet", "exit", "slash", "blunt", "blast")
POOL_KINDS = ("bullet", "exit", "blunt", "slash")
POOL_RES = 72
POOL_COLS = 24                  # slices across a cut with their own liquid level
# kind: (extra runs at full flow, spread of the extra runs' start across the
# hole (fraction of its radius), cavity volume in mL at size 1 (fill time = V / Q))
RUNS = {"bullet": (3.0, 0.9, 0.10), "exit": (7.0, 1.0, 0.9), "slash": (1.0, 0.0, 0.25),
        "blunt": (6.0, 1.0, 0.7), "blast": (12.0, 1.2, 2.5)}
FLOW_REF = 22.0                 # mL/min at which a wound reads as heavy: I = 1 - exp(-Q / FLOW_REF)
# front speed on skin (m/s): base + heavy flow + arterial (RB §3.11: 1-5 cm/s,
# 2-3.5 on vertical skin)
RUN_SPEED = (0.016, 0.014, 0.010)
RUN_MAX = 0.34                  # longest run (m): forehead to the cut of the neck
BEAT_S = 0.8                    # heart period (s) of the arterial surges
# half width (m) of a run: 0.8 mm trickle .. ~2.4 mm (rivulets 2-5 mm wide, RB §3.11, REFERENCE_NOTES §5.21)
RUN_W = (0.0013, 0.0018, 0.0006)
BRANCH_P = 0.07                # chance per trail step that a heavy run splits


def _nearest_normal(t, surface, pos):
    n = t.node('GeometryNodeSampleNearestSurface', {'Mesh': surface, 'Value': t.normal(),
                                                    'Sample Position': pos}, data_type='FLOAT_VECTOR')
    return t.out(n, 'Value').normalize()


def _nearest_point(t, surface, pos):
    n = t.node('GeometryNodeProximity', {'Target': surface, 'Source Position': pos}, target_element='FACES')
    return t.out(n, 'Position')


def _hit_fields(t, damage):
    """Common per-hit fields on a hit point cloud (see _build_hit_points)."""
    S = t.attr("hit_S", 'FLOAT_VECTOR')
    return dict(S=S, s=S.x * (0.3 + 0.7 * damage), e=S.y.max(0.004), D=S.z * damage,
                I=t.attr("hit_I", 'FLOAT_VECTOR'), X=t.attr("hit_X", 'FLOAT_VECTOR'),
                Y=t.attr("hit_Y", 'FLOAT_VECTOR'), Z=t.attr("hit_Z", 'FLOAT_VECTOR'),
                N=t.attr("hit_N", 'FLOAT_VECTOR'), R=t.attr("hit_R", 'FLOAT_VECTOR'),
                crush=t.smooth(1.15, 2.3, t.attr("hit_E") * damage), seed=t.attr("hit_seed"))


def _wound_extent(t, kind, h):
    """Characteristic radius of the opening in the skin (m) and the wound's reach for vessels."""
    s = h["s"]
    if kind == "bullet":
        return s * 0.0036, s * 0.004 + 0.0015
    if kind == "exit":
        R = (s * 0.0105 * 1.1).min(0.015)
        return R * 0.62, R * 0.55 + 0.001
    if kind == "slash":
        hl = s * 0.012 * h["e"]
        return hl, hl * 0.25 + 0.0012
    if kind == "blunt":
        rad = s * 0.02 * (1.0 + 1.3 * h["crush"])
        return rad * 0.45, rad * 0.4 + 0.001
    Rb = s * BLAST_R
    return Rb, Rb * 0.45


def _wound_samples(t, kind, h):
    """Points of the wound volume that are tested against the vessels, and the
    reach around each of them: ([(u, v, w, outflow weight)], reach) in the hit
    frame (w < 0 = into the head).

    The outflow weight is the share of a deep bleed that comes out of the
    wound instead of filling the tissue (RB §3.4 tissue_factor: 0.15-0.3 in a
    narrow track deeper than ~3 cm, 1 in a gaping wound)."""
    s, e, D = h["s"], h["e"], h["D"]
    # depth reached: skin and scalp by D 0.6 (~7 mm), through the skull and
    # into the brain from D 0.78
    thru = t.lin(D, 0.0, 0.6, 0.0015, 0.007) + t.lin(D, 0.78, 1.0, 0.0, 0.035)
    out = []
    _hole, reach = _wound_extent(t, kind, h)
    if kind in ("bullet", "exit"):
        deep_w = 0.25 if kind == "bullet" else 0.6
        for f in (0.0, 0.2, 0.45, 0.7, 1.0):
            w = -(thru * f).max(0.0015)
            out.append((0.0, 0.0, w, t.lin(-w, 0.012, 0.02, 1.0, deep_w)))
        if kind == "exit":
            R = (s * 0.0105 * 1.1).min(0.015) * 0.6
            for a in range(4):
                ang = a * TAU / 4.0 + 0.4
                out.append((R * math.cos(ang), R * math.sin(ang), -0.003, 1.0))
    elif kind == "slash":
        # along the cut at half its depth; a vessel crossing the cut plane lies
        # within sqrt((spacing/2)^2 + (depth/2)^2) of a sample
        hl = s * 0.012 * e
        # a throat cut reaches much deeper than a cut over the skull
        ds = D * (0.009 + 0.018 * h["R"].z)
        # (the samples follow the curve of the skin away from the hit's
        # tangent plane: radius ~5 cm on the neck, ~8 cm on the scalp)
        rc = 0.075 - 0.025 * h["R"].z
        for k in range(9):
            f = -0.95 + 1.9 * k / 8.0
            drop = (hl * f) ** 2.0 / (rc * 2.0)
            out.append((hl * f, 0.0, -(ds * 0.5).max(0.001) - drop, 1.0))
        reach = ((hl * 0.12) ** 2.0 + (ds * 0.5) ** 2.0).sqrt() + 0.0008
    elif kind == "blunt":
        rad = s * 0.02 * (1.0 + 1.3 * h["crush"])
        out += [(0.0, 0.0, -0.002, 1.0), (0.0, 0.0, -0.006, 1.0)]
        for a in range(4):
            ang = a * TAU / 4.0 + 0.3
            out.append((rad * 0.5 * math.cos(ang), rad * 0.5 * math.sin(ang), -0.003, 1.0))
    else:
        Rb = s * BLAST_R
        out += [(0.0, 0.0, -0.005, 1.0), (0.0, 0.0, -0.02, 1.0), (0.0, 0.0, -0.04, 0.7)]
        for a in range(6):
            ang = a * TAU / 6.0
            out.append((Rb * 0.7 * math.cos(ang), Rb * 0.7 * math.sin(ang), -0.006, 1.0))
    return out, reach


# per-class maxima and the dominant vessel, accumulated over the wound samples
_SRC_ATTRS = ("b_c0", "b_c1", "b_c2", "b_c3", "b_pw", "b_ws", "b_best", "b_src")


def _build_source_group(kind):
    """Subgroup: bleed sources of every hit of one kind, stored on the hit points.

    Vessels (GH_Vessels, split by class): a repeat zone runs over the wound's
    sample points; each finds the nearest vessel of every class, and a vessel
    within the wound's reach (plus its own radius) is cut and adds its
    transected bleed rate (the largest per class counts: a course is one
    line). Beds without a named trunk are added after (RB §3.7). Writes
    b_q (mL/min, scaled by the bleed control, 0.7 = normal pressure), b_fa
    (arterial share), b_tis (brain / bone admixture), b_pers (0..1
    persistence), b_src (HEAD_VESSELS row + 1 of the dominant named vessel,
    0 = none), b_hole (opening radius, m) and b_t0 (fill time, drip units).
    """
    f, g_ = 'NodeSocketFloat', 'NodeSocketGeometry'
    t = NodeTree(f"GH_Gore_Sources_{kind.capitalize()}",
                 (("Hits", g_), ("Damage", f, 1.0), ("Bleed", f, 0.7),
                  ("Artery", g_), ("Vein", g_), ("Deep Artery", g_), ("Sinus", g_)),
                 (("Hits", g_),), description=f"Vessels and beds cut by {kind} wounds -> bleed rate")
    damage, bleed = t.inp("Damage"), t.inp("Bleed")
    h = _hit_fields(t, damage)
    geos = [t.inp("Artery"), t.inp("Vein"), t.inp("Deep Artery"), t.inp("Sinus")]
    samples, reach = _wound_samples(t, kind, h)
    g = t.inp("Hits")
    for name in _SRC_ATTRS:
        g = t.store(g, name, 0.0)
    rin, rout, cur = _repeat(t, len(samples), [("Geometry", 'GEOMETRY', g)])
    k = F(t, rin.outputs['Iteration'])
    su = t.pick(k, [smp[0] for smp in samples])
    sv = t.pick(k, [smp[1] for smp in samples])
    sw = t.pick(k, [smp[2] for smp in samples])
    swt = t.pick(k, [smp[3] for smp in samples])
    pos = h["I"] + h["X"] * su + h["Y"] * sv + h["Z"] * sw
    g = cur["Geometry"]
    for ci, vg in enumerate(geos):
        prox = t.node('GeometryNodeProximity', {'Target': vg, 'Source Position': pos}, target_element='EDGES')
        dist, near = t.out(prox, 'Distance'), t.out(prox, 'Position')
        valid = t.switch(t.out(prox, 'Is Valid'), 0.0, 1.0)
        idx = t.out(t.node('GeometryNodeSampleNearest', {'Geometry': vg, 'Sample Position': near}))
        data = t.sample(vg, t.attr("v_data", 'FLOAT_VECTOR'), idx, 'FLOAT_VECTOR')
        vid = t.sample(vg, t.attr("v_id", 'INT'), idx, 'INT')
        cut = t.smooth(reach + data.y + 0.0005, reach * 0.35, dist) * valid
        qs = cut * data.x * swt
        g = t.store(g, f"b_c{ci}", t.attr(f"b_c{ci}").max(qs))
        g = t.store(g, "b_pw", t.attr("b_pw") + qs * data.z)
        g = t.store(g, "b_ws", t.attr("b_ws") + qs)
        better = t.bool('AND', qs.gt(t.attr("b_best")), cut.gt(0.05))
        g = t.store(g, "b_src", t.switch(better, t.attr("b_src"), t.math('ADD', vid, 1.0)))
        g = t.store(g, "b_best", t.attr("b_best").max(qs))
    g = _end_repeat(t, rout, [("Geometry", g)])["Geometry"]
    s, D, reg = h["s"], h["D"], h["R"]
    hole, _r = _wound_extent(t, kind, h)
    opened = t.smooth(0.03, 0.12, D)
    # beds without a named trunk (RB §3.7): scalp sheet (keeps pouring), face
    # dermis (clots within minutes), diploe (oozes), brain (blood, CSF, pulp)
    size = {"bullet": t.math('ADD', 0.12, 0.0), "exit": hole / 0.0075, "slash": hole * 2.0 / 0.07,
            "blunt": (hole / 0.009) * (1.0 + h["crush"]), "blast": t.math('ADD', 1.0, 0.0)}[kind]
    face_k = {"bullet": 0.5, "exit": 1.5, "slash": 1.0, "blunt": 1.5, "blast": 8.0}[kind]
    face_sz = size if kind in ("slash", "blunt") else 1.0
    scalp = SCALP_SHEET[0] * reg.x * size * opened
    face = FACE_DERMIS[0] * (reg.y + reg.z) * face_k * face_sz * opened
    bone_k = {"bullet": 0.4, "exit": 1.2, "slash": 0.0, "blunt": 1.0, "blast": 2.0}[kind]
    diploe = DIPLOE_OOZE[0] * bone_k * t.smooth(0.6, 0.8, D) * (1.0 + h["crush"])
    brain = BRAIN_OOZE[0] * {"bullet": 0.8, "exit": 1.3}.get(kind, 0.0) * t.smooth(0.88, 0.97, D)
    # cut muscle surface of a deep cut: 0.2-1 mL/min per cm^2 of wall (RB §3.7)
    muscle = 0.0
    if kind == "slash":
        wall_cm2 = hole * 2.0 * 100.0 * D * (0.9 + 1.8 * reg.z) * 2.0
        muscle = MUSCLE_OOZE * wall_cm2 * t.smooth(0.3, 0.6, D)
    # a blast in the mouth destroys the lining, gums and tongue: they pour
    mouth = opened * 25.0 if kind == "blast" else 0.0
    qa = t.attr("b_c0") + t.attr("b_c2")
    qv = t.attr("b_c1") + t.attr("b_c3")
    qo = scalp + face + diploe + brain + mouth + muscle
    q = qa + qv + qo
    if kind == "blunt":
        # a bruise without a split does not bleed out
        q = q * t.smooth(0.25, 0.35, D)
    pers = ((t.attr("b_pw") + scalp * SCALP_SHEET[1] + face * FACE_DERMIS[1] + (diploe + brain) * 0.85
             + mouth * 0.7 + muscle * 0.5) / (t.attr("b_ws") + qo).max(1e-4)).clamp()
    qs_ = q * bleed / 0.7
    g = t.store(g, "b_q", qs_)
    g = t.store(g, "b_fa", (qa / q.max(1e-4)).clamp())
    g = t.store(g, "b_tis", ((brain + diploe * 0.3) / q.max(1e-4)).clamp())
    g = t.store(g, "b_pers", pers)
    g = t.store(g, "b_hole", hole)
    # time to fill the cavity (drip_time units, 1 = 60 s): V / Q, 0.3-25 s
    vol = RUNS[kind][2] * (s * s).max(0.2)
    if kind == "blunt":
        vol = vol * (1.0 + 3.0 * h["crush"])
    t0 = (vol / (t.attr("b_q") / 60.0).max(1e-3)).clamp(0.3, 25.0) / 60.0
    g = t.store(g, "b_t0", t0)
    for name in _SRC_ATTRS[:-1]:
        g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Exact', 'Name': name}))
    t.result("Hits", g)
    t.layout()
    return t


def _drip_seeds(t, pts, kind, kind_id, damage, drip):
    """Duplicate each hit into the runs that leave it (seed points, d_* attributes).

    Every run starts INSIDE the wound: in the blood pool that fills the hole
    (bullet, exit, blunt), in the welling fill of a cut's bed (slash) or in
    the pulp of a blast crater, and walks out over the lowest rim (_walk).
    The first run is the main one; more runs spill over the rim as the flow
    goes on (more and sooner with a heavier bleed).
    """
    n_extra, spread, _vol = RUNS[kind]
    h = _hit_fields(t, damage)
    s, e, D = h["s"], h["e"], h["D"]
    q, fa = t.attr("b_q"), t.attr("b_fa")
    ib = 1.0 - t.math('EXPONENT', -q / FLOW_REF)
    if kind == "slash":
        n_extra = e * 0.7
    rr = _hash(t, h["seed"], 17.0)
    amount = t.math('FLOOR', 1.0 + n_extra * ib * (0.55 + 0.9 * rr) + 0.5) * q.gt(0.3)
    dup = t.node('GeometryNodeDuplicateElements', {'Geometry': pts, 'Amount': amount}, domain='POINT')
    g = t.out(dup, 'Geometry')
    first = t.compare('EQUAL', t.out(dup, 'Duplicate Index'), 0, 'INT')
    idx = t.index()
    r1 = t.rand(0.0, 1.0, idx, 101 + kind_id)
    r2 = t.rand(0.0, 1.0, idx, 202 + kind_id)
    r3 = t.rand(0.0, 1.0, idx, 303 + kind_id)
    I, X, Y, N = h["I"], h["X"], h["Y"], h["N"]
    grav = t.vec(0.0, 0.0, -1.0)
    # down and sideways in the skin's tangent plane at the impact
    dn_t = (grav - N * N.dot(grav))
    dn_t = t.switch(dn_t.length().lt(1e-4), dn_t.normalize(), X, 'VECTOR')
    side_t = N.cross(dn_t).normalize()
    hole = t.attr("b_hole")
    if kind == "slash":
        Tw = t.attr("hit_T", 'FLOAT_VECTOR')
        half_len, gape = _slash_params(t, s, e, D, Tw.dot(X), Tw.dot(Y), h["R"].x, h["R"].z)
        dx, dy = -X.z, -Y.z
        sy = t.math('SIGN', dy)

        def rim_h(tt):
            """Height (world z) of the lower lip at tt along the cut."""
            hwo = (0.00045 + gape * 0.5) * _slash_lens(t, tt)
            return X.z * (tt * half_len) + Y.z * sy * hwo
        # the lowest point of the lower lip (sampled along the cut)
        best_h = best_t = None
        for k in range(9):
            tk = -0.85 + 1.7 * k / 8.0
            hk = rim_h(tk)
            if best_h is None:
                best_h, best_t = hk, t.math('ADD', tk, 0.0)
            else:
                lower = hk.lt(best_h)
                best_t = t.switch(lower, best_t, tk)
                best_h = best_h.min(hk)
        tt = t.switch(first, t.mix(best_t, (r1 - 0.5) * 1.6, 0.35 + 0.4 * r3), best_t)
        hwo = (0.00045 + gape * 0.5) * _slash_lens(t, tt)
        # (inside the bed, in the welling fill: the run's top lies in the
        # blood that fills the cut and pours over the lower lip)
        p0 = I + X * (tt * half_len) + Y * (sy * (hwo * 0.3))
    elif kind == "blast":
        # in the pulp of the crater, below its centre
        p0 = I + dn_t * (hole * (0.35 + 0.25 * r3)) + side_t * ((r1 - 0.5) * hole * spread * t.switch(first, 1.0, 0.3))
    else:
        # in the pool that fills the hole: the main run leaves from the
        # centre, the others spread across the lower part of the opening
        p0 = I + dn_t * (hole * 0.15) + side_t * t.switch(first, (r1 - 0.5) * hole * spread, 0.0)
    # where the run leaves the wound is found on the real rim (_find_lips):
    # these are the search parameters. Round openings are searched along
    # rays from their centre fanning around "downhill"; a cut along its
    # length, marching across it toward the lower lip. The main run takes the
    # lowest rim point, later runs a random one of the low ones.
    if kind == "slash":
        ax = X
        acr = Y * sy
        hl_s = half_len
        r_lo, r_hi = 0.0, gape * 0.5 + 0.0045
        spill = t.math('ADD', 0.0011, gape * 0.08)
    else:
        ax = dn_t
        acr = dn_t
        hl_s = 0.0
        r_lo = hole * 0.15
        r_hi = hole * {"bullet": 2.6, "exit": 2.2, "blunt": 2.6, "blast": 1.9}[kind] + 0.002
        spill = hole * {"bullet": 0.55, "exit": 0.45, "blunt": 0.4, "blast": 0.3}[kind]
    tol = {"bullet": 0.5, "exit": 0.55, "slash": 0.3, "blunt": 0.6, "blast": 0.4}[kind]
    # timing: nothing leaves the wound before it has filled (b_t0); later runs
    # spill over as the flow goes on (4-34 s later, sooner with more flow)
    t0 = t.attr("b_t0") + t.switch(first, (0.07 + 0.5 * (1.0 - ib)) * r1, 0.0)
    x = ((drip - t0) * 60.0).max(0.0)                    # seconds since this run left the wound
    pers = t.attr("b_pers")
    tau = 8.0 + 140.0 * pers                              # oozes slow down, scalp / arterial runs keep going
    v = RUN_SPEED[0] + RUN_SPEED[1] * ib + RUN_SPEED[2] * fa
    dist = v * tau * (1.0 - t.math('EXPONENT', -x / tau))
    lfac = t.switch(first, 0.35 + 0.65 * r2, 1.0)
    d_len = (dist * lfac).min(RUN_MAX * (0.8 + 0.2 * r2)) * x.gt(0.0)
    w0 = RUN_W[0] + RUN_W[1] * ib + RUN_W[2] * fa
    # a thin first trickle that widens as the volume comes down (first ~6 s)
    d_w = w0 * t.switch(first, 0.5 + 0.5 * r3, 1.2) * (0.5 + 0.5 * t.smooth(0.0, 6.0, x))
    speed_now = v * t.math('EXPONENT', -x / tau)
    moving = t.bool('AND', x.gt(0.0), t.bool('AND', speed_now.gt(0.004), d_len.lt(RUN_MAX * 0.97)))
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Position': p0}))
    g = t.store(g, "d_len", d_len)
    g = t.store(g, "d_w", d_w)
    g = t.store(g, "d_mov", t.switch(moving, 0.0, 1.0))
    g = t.store(g, "d_art", fa)
    g = t.store(g, "d_tis", t.attr("b_tis"))
    g = t.store(g, "d_lam", v * BEAT_S)
    g = t.store(g, "d_ib", ib)
    g = t.store(g, "d_q", q)
    g = t.store(g, "d_src", t.attr("b_src"))
    g = t.store(g, "d_bias", (0.0, 0.0, 0.0), 'FLOAT_VECTOR')
    ctr, n_s, dn_s, sd_s = I, N, dn_t, side_t
    if kind == "blast":
        # a blast in the open mouth: the impact ray may pass the lips and meet
        # the throat, so the search starts from the mouth opening itself (the
        # empty, ~1 cm in) and fans out in the plane facing the shot
        Zo = h["Z"]
        ctr = t.attr("hit_P", 'FLOAT_VECTOR') - Zo * 0.01
        n_s = Zo
        dn_s = (grav - Zo * Zo.dot(grav)).normalize()
        sd_s = Zo.cross(dn_s).normalize()
        ax = acr = dn_s
    for name, val in (("lp_ctr", ctr), ("lp_dn", dn_s), ("lp_sd", sd_s), ("lp_ax", ax), ("lp_acr", acr),
                      ("lp_n", n_s)):
        g = t.store(g, name, val, 'FLOAT_VECTOR')
    g = t.store(g, "lp_shape", 1.0 if kind == "slash" else 0.0)
    g = t.store(g, "lp_hl", hl_s)
    g = t.store(g, "lp_r0", r_lo)
    g = t.store(g, "lp_r1", r_hi)
    # (score noise: 0 for the main run = the lowest rim point; the others pick
    # among the rim points within ~tol x the opening's size of the lowest)
    g = t.store(g, "lp_tol", t.switch(first, (hole * 2.0 * tol).max(0.0015), 0.0))
    g = t.store(g, "d_spill", spill.max(0.0006) if kind != "slash" else spill)
    return g


def _build_seed_group(kind, kind_id, name=None):
    """Subgroup: run seed points of one wound kind."""
    f = 'NodeSocketFloat'
    t = NodeTree(name or f"GH_Gore_DripSeeds_{kind.capitalize()}",
                 (("Hits", 'NodeSocketGeometry'), ("Damage", f, 1.0), ("Drip Time", f, 1.0)),
                 (("Seeds", 'NodeSocketGeometry'),), description=f"Run seeds in {kind} wounds")
    t.result("Seeds", _drip_seeds(t, t.inp("Hits"), kind, kind_id, t.inp("Damage"), t.inp("Drip Time")))
    t.layout()
    return t


def _build_pools(t, hits, surface, drip):
    """Blood surface filling each wound opening (bullet, exit, blunt): one grid per hit.

    The grid lies in the skin's tangent plane at the impact. A ray down each
    grid vertex finds what is there: outer skin (outside the opening) or a
    wound wall / nothing (inside). The liquid level is the mean height of the
    opening's own rim: it rises from 3 mm down in the track to just over the
    rim as the cavity fills (b_t0), so the LOW parts of the rim are covered
    (the wet lip the runs pour over) and the high parts stand out of it.
    Outside the opening the grid tucks under the skin, so its edge is exactly
    the ragged outline of the hole. Exits carry pulped brain in the pool.
    """
    grid = t.out(t.node('GeometryNodeMeshGrid', {'Size X': 2.0, 'Size Y': 2.0, 'Vertices X': POOL_RES,
                                                 'Vertices Y': POOL_RES}))
    grid = t.store(grid, "pl_uv", t.pos(), 'FLOAT_VECTOR')
    pts = t.store(hits, "pl_id", t.index(), 'INT')
    inst = t.node('GeometryNodeInstanceOnPoints', {'Points': pts, 'Instance': grid})
    g = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(inst)}))
    I, N, X = t.attr("hit_I", 'FLOAT_VECTOR'), t.attr("hit_N", 'FLOAT_VECTOR'), t.attr("hit_X", 'FLOAT_VECTOR')
    Z = t.attr("hit_Z", 'FLOAT_VECTOR')
    uv = t.attr("pl_uv", 'FLOAT_VECTOR')
    T1 = (X - N * X.dot(N)).normalize()
    T2 = N.cross(T1)
    # an oblique track opens an elongated hole: cover it (a cut's grid is
    # already long along the cut and narrow across it: pl_Ry < pl_R)
    stretch = 1.0 / t.math('ABSOLUTE', N.dot(Z)).max(0.45)
    stretch = t.mix(stretch, 1.0, t.attr("pl_col"))
    P0 = I + (T1 * (uv.x * t.attr("pl_R")) + T2 * (uv.y * t.attr("pl_Ry"))) * stretch
    ray = t.node('GeometryNodeRaycast', {'Target Geometry': surface, 'Attribute': t.attr("g_wk"),
                                         'Source Position': P0 + N * 0.008, 'Ray Direction': -N,
                                         'Ray Length': 0.05}, data_type='FLOAT')
    hit = t.out(ray, 'Is Hit')
    wk = t.out(ray, 'Attribute')
    hgt = (t.out(ray, 'Hit Position') - I).dot(N)
    # inside the opening: the ray meets a wound wall, or passes into the
    # track without meeting skin -- but a miss far out on a curved face (the
    # skin falls away from the tangent plane) is outside, never a pool
    # hanging in the air
    r_loc = (P0 - I).length()
    in_miss = t.switch(t.attr("pl_col").gt(0.5), r_loc.lt(t.attr("b_hole") * 1.15),
                       t.bool('AND', t.math('ABSOLUTE', uv.x).lt(0.92),
                              (t.math('ABSOLUTE', uv.y) * t.attr("pl_Ry")).lt(t.attr("pl_Ry") - 0.0026)), 'BOOLEAN')
    # (a long cut on a round neck: the tangent-plane grid lies ~3 cm off the
    # skin at the cut's ends; a miss there is air, not the opening -- those
    # vertices once floated as a flat collar around the neck)
    near_s = t.out(t.node('GeometryNodeProximity', {'Target': surface, 'Source Position': P0},
                          target_element='FACES'), 'Distance').lt(0.0035)
    in_miss = t.bool('AND', in_miss, near_s)
    inside = t.bool('OR', t.bool('AND', hit, wk.gt(0.25)), t.bool('AND', t.bool('NOT', hit), in_miss))
    # (the grid's own border is never inside the opening: no straight edges)
    inside = t.bool('AND', inside, t.math('MAXIMUM', t.math('ABSOLUTE', uv.x), t.math('ABSOLUTE', uv.y)).lt(0.93))
    outside = t.switch(inside, 1.0, 0.0)
    g = t.store(g, "pl_out", outside)
    g = t.store(g, "pl_h", t.switch(hit, -0.004, hgt))
    g = t.store(g, "pl_p0", P0, 'FLOAT_VECTOR')
    out_f = t.attr("pl_out")
    m_in = F(t, t.node('GeometryNodeBlurAttribute', {'Value': 1.0 - out_f, 'Iterations': 2, 'Weight': 1.0},
                       data_type='FLOAT').outputs[0])
    g = t.store(g, "pl_min", m_in)
    m_in = t.attr("pl_min")
    rim = out_f * m_in.gt(0.03).max(0.0)
    # the liquid level is set by the rim it can spill over: for a round hole
    # the whole rim; along a cut, the rim around each slice across it (a long
    # cut on a curved face would otherwise hang its surface in the air at one
    # end and sink it deep at the other)
    col = t.math('FLOOR', (uv.x + 1.0) * 0.5 * (POOL_COLS - 1) + 0.5) * t.attr("pl_col")
    pid = t.math('ADD', t.attr("pl_id", 'INT') * POOL_COLS, col)
    cnt = t.out(t.node('GeometryNodeAccumulateField', {'Value': rim, 'Group ID': pid}), 'Total')
    sum_h = t.out(t.node('GeometryNodeAccumulateField', {'Value': rim * t.attr("pl_h"), 'Group ID': pid}), 'Total')
    mean_h = sum_h / cnt.max(1.0)
    g = t.store(g, "pl_mean", mean_h)
    g = t.store(g, "pl_cnt", cnt)
    # the liquid stands at the LOWEST part of the rim (it runs out there):
    # soft minimum of the rim heights, min ~ mean - k ln(sum exp(-(h - mean) / k) / n)
    k_sm = 0.00022
    ex = rim * t.math('EXPONENT', ((t.attr("pl_mean") - t.attr("pl_h")) / k_sm).min(40.0))
    s_ex = t.out(t.node('GeometryNodeAccumulateField', {'Value': ex, 'Group ID': pid}), 'Total')
    low = t.attr("pl_mean") - k_sm * t.math('LOGARITHM', (s_ex / t.attr("pl_cnt").max(1.0)).max(1.0), math.e)
    # (a hit whose skin did not open has no rim: no pool)
    g = t.store(g, "pl_low", low)
    # (slices of a cut: blend the levels of neighbouring slices, no steps)
    lb = F(t, t.node('GeometryNodeBlurAttribute', {'Value': t.attr("pl_low"), 'Iterations': 10, 'Weight': 1.0},
                     data_type='FLOAT').outputs[0])
    g = t.store(g, "pl_low", t.mix(t.attr("pl_low"), lb, t.attr("pl_col")))
    fill = t.smooth(0.0, t.attr("b_t0").max(0.004), drip)
    # gravity: on a sloping face the liquid runs to the LOW side of the
    # opening -- it stands at the lowest rim there and lies deeper toward the
    # upper edge, so the upper wall of the wound shows above it
    grav = t.vec(0.0, 0.0, -1.0)
    g_t = grav - N * N.dot(grav)
    up_d = (t.attr("pl_p0", 'FLOAT_VECTOR') - I).dot(g_t) * -1.0
    # (surface tension holds the blood level across a small hole; in a wide
    # crater gravity wins and the surface is nearly horizontal)
    # (a crushed crater is wide and open: its blood lies in the lowest pits
    # and pockets between the pulp, never as one slab across the crater)
    k_tilt = t.mix(0.22 + 0.7 * t.smooth(0.004, 0.016, t.attr("b_hole")), 0.0, t.attr("pl_col")) \
        + 2.2 * t.attr("pl_cr")
    tilt = up_d.max(-0.02) * k_tilt * g_t.length()
    # a cut is a channel: the blood runs down its bed to the LOW end and
    # brims over the lower lip there; up the cut the level drops below the
    # rim, so its upper walls (dermis line, fat, muscle) stand out of the
    # blood, wet -- a cut flooded flush along its whole length reads as a
    # flat painted "second mouth"
    g = t.store(g, "pl_up", up_d)
    pid_h = t.attr("pl_id", 'INT')
    cnt_h = t.out(t.node('GeometryNodeAccumulateField', {'Value': rim, 'Group ID': pid_h}), 'Total')
    mean_up = t.out(t.node('GeometryNodeAccumulateField', {'Value': rim * t.attr("pl_up"), 'Group ID': pid_h}),
                    'Total') / cnt_h.max(1.0)
    g = t.store(g, "pl_mup", mean_up)
    k_up = 0.0012
    exu = rim * t.math('EXPONENT', ((t.attr("pl_mup") - t.attr("pl_up")) / k_up).min(40.0))
    s_exu = t.out(t.node('GeometryNodeAccumulateField', {'Value': exu, 'Group ID': pid_h}), 'Total')
    up_min = t.attr("pl_mup") - k_up * t.math('LOGARITHM', (s_exu / cnt_h.max(1.0)).max(1.0), math.e)
    g = t.store(g, "pl_upmin", up_min)
    recede = ((t.attr("pl_up") - t.attr("pl_upmin")) * 0.5 * g_t.length()).clamp(0.0, 0.012) \
        * (t.attr("pl_col") + t.attr("pl_spl")).clamp()
    # a gaping cut that lies ACROSS gravity (a throat cut on the upright
    # neck) is no cup: the blood runs out over its lower lip as fast as it
    # comes, so only the floor of the V holds liquid and the cut walls --
    # muscle, cartilage, vessel openings -- stand out of it (a trench flooded
    # flush read as one flat glossy slab, REFERENCE_NOTES §5.18 E)
    gh = g_t.normalize()
    across = (1.0 - t.math('ABSOLUTE', T1.dot(gh))) * g_t.length()
    sink_cut = t.attr("pl_col") * across * (t.attr("pl_Ry") * 0.55).min(0.0065) \
        * t.smooth(0.003, 0.007, t.attr("pl_Ry"))
    L = t.attr("pl_low") - 0.0032 * (1.0 - fill) + 0.0003 * fill - tilt.max(0.0) - recede - sink_cut
    hs = t.attr("pl_h")
    # just past the rim the liquid drapes onto the lip where the lip is lower
    # than the level (spilling); everywhere else it tucks under the skin
    adj = t.smooth(0.0, 0.35, t.attr("pl_min")) * fill.gt(0.9).max(0.0)
    h_out = t.mix(hs - 0.0012, L.min(hs + 0.00012), adj).min(L)
    # pulped brain in the pool of an exit (tissue share), bulging through the blood
    lump_n = t.noise(t.attr("pl_p0", 'FLOAT_VECTOR') * 380.0, detail=3.0, signed=False)
    lump_n2 = t.noise(t.attr("pl_p0", 'FLOAT_VECTOR') * 1300.0, detail=2.0)
    lump_n3 = t.noise(t.attr("pl_p0", 'FLOAT_VECTOR') * 150.0, detail=2.0, signed=False)
    pulp = (t.attr("pl_pulp") * (0.6 + 1.5 * t.attr("b_tis"))).clamp()
    lump = t.smooth(0.5, 0.68, lump_n * 0.7 + lump_n3 * 0.3) * pulp * fill * (1.0 - out_f)
    # the liquid surface is never a mirror-flat disc: a shallow meniscus
    # bulge and slow ripples; pulp (brain, torn tissue) stands out of it in lumps
    h_in = L + lump * (0.0012 + 0.0016 * lump_n3 + 0.0005 * lump_n2) + (1.0 - lump) * 0.00016 * lump_n2
    hfin = t.mix(h_in, h_out, out_f)
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g,
                                                 'Position': t.attr("pl_p0", 'FLOAT_VECTOR') + N * (hfin - (t.attr("pl_p0", 'FLOAT_VECTOR') - I).dot(N))}))
    g = t.store(g, "gore_tis", lump.clamp())
    # keep the pool and a margin of two grid cells under the skin
    far = F(t, t.node('GeometryNodeBlurAttribute', {'Value': 1.0 - t.attr("pl_out"), 'Iterations': 4,
                                                    'Weight': 1.0}, data_type='FLOAT').outputs[0])
    g = t.store(g, "pl_far", far)
    # (no bleeding, no pool: bleed 0 or a bruise that did not split)
    # (a crushed crater is not a cup: its blood lies in the pits between the
    # pulp and clot lumps (_mush, clot blobs) and runs out over its lowest
    # edge; a single liquid sheet across it read as a dark slab and, where
    # the rays missed the caved-in face, hung in the air beside the head)
    drop = t.bool('OR', t.bool('OR', t.attr("pl_far").lt(0.004), t.attr("pl_cnt").lt(3.0)),
                  t.bool('OR', t.attr("b_q").lt(0.3), t.attr("pl_cr").gt(0.3)))
    g = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': g, 'Selection': drop}, domain='POINT'))
    g = t.store(g, "gore_bthin", 0.0)
    g = t.store(g, "gore_art", t.attr("b_fa") * 0.35)
    g = t.store(g, "gore_bq", t.attr("b_q"))
    g = t.store(g, "gore_bsrc", t.attr("b_src"))
    return g


LIP_CANDS = 13                  # candidate spill points per run (fan of rays / points along a cut)
LIP_STEPS = 28                  # samples of each march from inside the wound across its rim
LIP_FAN = 1.25                  # half angle (rad, ~72 deg) of the fan around "downhill"


def _find_lips(t, seeds, surface):
    """Put every run seed on the rim point where the blood actually spills over.

    REFERENCE_NOTES §5.17 / §5.19.1 / §5.21: a run may only leave a wound at
    a point of the wound's OWN edge that is a low point under gravity. For
    each seed LIP_CANDS candidate marches start inside the opening (a fan of
    rays from the centre of a round hole, or points along a cut marching
    across it toward its lower lip); each march ray-casts down onto the
    wounded skin until it first meets intact outer skin (g_wk < 0.25) -- that
    sample is the rim. The main run takes the lowest rim point (world z);
    later runs take a random low one (score = z + random * lp_tol).

    Writes: position = the rim point (on the lip), d_in = a point inside the
    opening on the same march (the run's first curve point: its top lies in
    the blood that fills the wound), d_arc0 = distance between them. Seeds
    whose marches found no rim keep their position (d_in = position).
    """
    NC, NS = LIP_CANDS, LIP_STEPS
    g = t.store(seeds, "lp_best", 1e9)
    g = t.store(g, "lp_L", t.pos(), 'FLOAT_VECTOR')
    g = t.store(g, "lp_I", t.pos(), 'FLOAT_VECTOR')
    g = t.store(g, "lp_f", 0.0)
    rin, rout, cur = _repeat(t, NC * NS, [("Geometry", 'GEOMETRY', g)])
    it = F(t, rin.outputs['Iteration'])
    j = t.math('FLOOR', (it + 0.5) / float(NS))
    k = it - j * float(NS)
    fj = j * (2.0 / (NC - 1)) - 1.0                        # -1 .. 1
    ang = fj * LIP_FAN
    V = lambda n: t.attr(n, 'FLOAT_VECTOR')                 # noqa: E731
    shape = t.attr("lp_shape")
    m_round = V("lp_dn") * ang.cos() + V("lp_sd") * ang.sin()
    M = t.mix(m_round, V("lp_acr"), shape)
    C = V("lp_ctr") + V("lp_ax") * (fj * 0.85 * t.attr("lp_hl"))
    dr = (t.attr("lp_r1") - t.attr("lp_r0")) / float(NS - 1)
    r = t.attr("lp_r0") + dr * k
    P = C + M * r
    N = V("lp_n")
    g = cur["Geometry"]
    # new candidate: forget whether the previous march already found its rim
    g = t.store(g, "lp_f", 0.0, sel=k.lt(0.5))
    ray = t.node('GeometryNodeRaycast', {'Target Geometry': surface, 'Attribute': t.attr("g_wk"),
                                         'Source Position': P + N * (0.008 + r * 0.3), 'Ray Direction': -N,
                                         'Ray Length': 0.03 + r * 0.6}, data_type='FLOAT')
    outer = t.bool('AND', t.out(ray, 'Is Hit'), t.out(ray, 'Attribute').lt(0.25))
    g = t.store(g, "lp_ok", t.switch(t.bool('AND', outer, t.attr("lp_f").lt(0.5)), 0.0, 1.0))
    g = t.store(g, "lp_hp", t.out(ray, 'Hit Position'), 'FLOAT_VECTOR')
    rnd = t.rand(0.0, 1.0, t.attr("d_id", 'INT') * 41 + j, 7707)
    score = V("lp_hp").z + rnd * t.attr("lp_tol")
    better = t.bool('AND', t.attr("lp_ok").gt(0.5), score.lt(t.attr("lp_best")))
    # (the rim lies between the last inside sample and this one: half a step back)
    g = t.store(g, "lp_L", V("lp_hp") - M * (dr * 0.5), 'FLOAT_VECTOR', sel=better)
    g = t.store(g, "lp_I", C + M * ((r - dr * 0.5) * 0.3), 'FLOAT_VECTOR', sel=better)
    g = t.store(g, "lp_best", score, sel=better)
    g = t.store(g, "lp_f", 1.0, sel=t.attr("lp_ok").gt(0.5))
    g = _end_repeat(t, rout, [("Geometry", g)])["Geometry"]
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Position': V("lp_L")}))
    g = t.store(g, "d_in", V("lp_I"), 'FLOAT_VECTOR')
    # later runs fan out from where they left the rim (they came over a
    # different part of it), the main run just follows gravity
    off = (V("lp_L") - V("lp_ctr")).dot(V("lp_sd"))
    # (not for a cut: runs leaving along its lower lip already lie side by
    # side, a push would make them cross)
    fan = V("lp_sd") * (off / (t.attr("lp_r1") * 0.4).max(0.001)).clamp(-1.0, 1.0) * 0.45 \
        * (1.0 - t.attr("lp_shape"))
    g = t.store(g, "d_bias", t.switch(t.attr("lp_tol").gt(0.0), (0.0, 0.0, 0.0), fan, 'VECTOR'), 'FLOAT_VECTOR')
    g = t.store(g, "d_arc0", (V("lp_L") - V("lp_I")).length())
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Wildcard', 'Name': "lp_*"}))
    return g


def _walk(t, seeds, surface, steps, rest):
    """Walk every seed down the surface under gravity; returns (trail points, final tips).

    Each step goes along gravity projected onto the tangent plane (plus a
    little meander, and a sideways push for new branches), then snaps back
    onto the surface. Where the skin turns to face downward (under the chin,
    the nose tip, an earlobe) the run stops and hangs as a drop; on shallow
    slopes it slows and the blood gathers (d_slow widens the run there).
    """
    rin, rout, cur = _repeat(t, steps, [("Tips", 'GEOMETRY', seeds), ("Trail", 'GEOMETRY', seeds)])
    it = F(t, rin.outputs['Iteration'])
    p = t.pos()
    n = _nearest_normal(t, surface, p)
    grav = (0.0, 0.0, -1.0)
    gt = t.vmath('SUBTRACT', grav, n * n.dot(grav))
    gl = gt.length()
    wob = t.noise(p * 170.0 + t.vec(t.attr("d_id", 'INT') * 1.37, 0.0, 0.0), detail=2.0, color=True)
    wob = wob - n * wob.dot(n)
    bias = t.attr("d_bias", 'FLOAT_VECTOR')
    bias = bias - n * bias.dot(n)
    push = (1.0 - it / 14.0).max(0.0)
    # (two scales of meander: pinning on skin texture, wander over cm)
    wob2 = t.noise(p * 45.0 + t.vec(0.0, t.attr("d_id", 'INT') * 0.91, 0.0), detail=1.0, color=True)
    wob2 = wob2 - n * wob2.dot(n)
    # (never uphill: the meander only bends a run sideways)
    dirv = (gt / gl.max(1e-4) + wob * 0.4 + wob2 * 0.45 + bias * push * 1.6).normalize()
    slope = 0.2 + 0.8 * t.smooth(0.05, 0.45, gl)
    # (large-scale orientation from the intact skin: blood flows over the mm
    # bumps of a wound lip, it only hangs where the face itself turns down)
    # (heavy flows cling further round onto skin that turns downward --
    # under the jaw line toward the neck -- before they hang and drip)
    ibh = t.attr("d_ib") ** 2.0 * 0.45
    hang = t.smooth(-0.62 - ibh, -0.42 - ibh, _nearest_normal(t, rest, p).z)
    # (a heavy flow is not stopped by skin that turns under: it keeps
    # running along the underside of the chin / jaw onto the neck)
    fac = (slope * hang).max(t.attr("d_ib") ** 2.0 * 0.5)
    # short steps where the run leaves the lip (it must hug the rim and the
    # skin just below it, never bridge under the lip), longer further down:
    # step k takes min(k + 1, WALK_RAMP) shares of the run's length
    ramp = float(WALK_RAMP)
    shares = ramp * (ramp + 1.0) / 2.0 + ramp * (steps - ramp)
    step = t.attr("d_len") * ((it + 1.0).min(ramp) / shares) * fac
    p2 = p + dirv * step
    p3 = _nearest_point(t, surface, p2) + _nearest_normal(t, surface, p2) * (t.attr("d_w") * 0.2)
    tips = t.out(t.node('GeometryNodeSetPosition', {'Geometry': cur["Tips"], 'Position': p3}))
    tips = t.store(tips, "d_step", t.math('ADD', it, 1.0))
    tips = t.store(tips, "d_slow", 1.0 - fac)
    tips = t.store(tips, "d_mv", step)
    trail = _join(t, tips, cur["Trail"])
    res = _end_repeat(t, rout, [("Tips", tips), ("Trail", trail)])
    trail = res["Trail"]
    # a run that stopped leaves points piled on one spot: keep one of them
    stuck = t.bool('AND', t.attr("d_mv").lt(2e-5), t.attr("d_step").gt(0.5))
    trail = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': trail, 'Selection': stuck}, domain='POINT'))
    return trail, res["Tips"]


def _run_mesh(t, trail, surface, steps):
    """Trail points -> flattened blood ribbon mesh (+ the centre-line path)."""
    running = t.attr("d_len").gt(0.0008)
    trail_run = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': trail, 'Selection': t.bool('NOT', running)},
                             domain='POINT'))
    curves = t.out(t.node('GeometryNodePointsToCurves', {'Points': trail_run, 'Curve Group ID': t.attr("d_id", 'INT'),
                                                         'Weight': t.attr("d_step")}))
    curves = t.out(t.node('GeometryNodeCurveSplineType', {'Curve': curves}, spline_type='CATMULL_ROM'))
    curves = t.out(t.node('GeometryNodeSetSplineResolution', {'Geometry': curves, 'Resolution': 3}))
    sp = t.node('GeometryNodeSplineParameter')
    tt = t.out(sp, 'Factor')
    arc = t.out(sp, 'Length')
    dw = t.attr("d_w")
    rid = t.attr("d_id", 'INT')
    a0 = t.attr("d_arc0")
    # width: uneven along the run (necking and swelling at two scales, from
    # the run's own arc length: a rivulet pins and bulges, it is never a bar),
    # fuller where it slowed (creases, shallow slopes)
    n1 = t.noise(t.vec(arc * 95.0, rid * 1.37, 0.3), detail=2.0)
    n2 = t.noise(t.vec(arc * 330.0, rid * 0.71, 1.7), detail=1.0)
    rad = dw * (0.75 + 0.25 * t.smooth(0.0, 0.14, tt)) * (1.0 + 0.34 * n1 + 0.16 * n2) \
        * (1.0 + 0.5 * t.attr("d_slow"))
    # arterial surges: one bulge per heartbeat along the run (d_lam = front
    # speed x beat period), strength = arterial share
    ph = t.math('SINE', arc / t.attr("d_lam").max(0.004) * TAU + rid * 1.7)
    rad = rad * (1.0 + 0.5 * t.attr("d_art") * ph.max(0.0) ** 2.0)
    # a moving front is a little fuller (the bead is added in _drops)
    rad = rad + dw * 0.2 * t.smooth(0.85, 1.0, tt) * t.attr("d_mov")
    # a run that stopped thins to a tip and its thin tail breaks into beads
    # (a film too thin to flow gathers into drops left along the path)
    lam = 0.0055 + 0.004 * t.rand(0.0, 1.0, rid, 505)
    bead = t.math('SINE', arc / lam * TAU + rid * 2.3).max(0.0) ** 3.0
    tail = t.smooth(0.5, 0.92, tt) * (1.0 - t.attr("d_mov"))
    rad = rad * t.mix(1.0, 0.28 + 1.05 * bead, tail * 0.85)
    rad = rad * (0.15 + 0.85 * t.smooth(1.0, 0.86, tt).max(t.attr("d_mov")))
    # where it leaves the wound the run is only as wide as the part of the
    # rim it spills over (d_spill), widening further down as it spreads
    cap = t.attr("d_spill") * (0.65 + 0.35 * t.smooth(0.0, a0.max(1e-4), arc)) + (arc - a0).max(0.0) * 0.22
    rad = rad.min(cap)
    curves = t.out(t.node('GeometryNodeSetCurveRadius', {'Curve': curves, 'Radius': rad}))
    curves = t.store(curves, "d_rad", rad)
    # run id and position along it (0 = where it leaves the wound): lets tests
    # and the game follow a run from its source
    curves = t.store(curves, "gore_run", t.math('ADD', t.attr("d_id", 'INT'), 1.0))
    curves = t.store(curves, "gore_runf", tt)
    # crest height of the rivulet: 0.1-0.3 mm (thicker for a heavy flow and
    # where it slowed and gathered), REFERENCE_NOTES §5.21 / RB rivulet row
    curves = t.store(curves, "d_cap", (0.00011 + 0.00012 * t.attr("d_ib")) * (1.0 + 0.5 * t.attr("d_slow")))
    path = t.out(t.node('GeometryNodeCurveToMesh', {'Curve': curves}))
    return path


FILM_REACH = 0.0065             # skin within this of a run's centre line is re-meshed for the film (m)
FILM_FINE = 4.0e-7              # faces larger than this (m^2) are subdivided twice for the film outline


def _film(t, paths, surface):
    """The runs as ONE liquid layer lying on the skin (not tubes laid on it).

    The skin (and pools / wound walls) near the runs is copied, subdivided to
    ~0.3 mm, and every vertex gets the thickness of the rivulet over it: a
    meniscus profile h = crest * (1 - (d / half width)^2)^0.7 across the
    nearest run (half width d_rad, crest d_cap), with a slightly ragged edge.
    Where runs meet they merge into one sheet; the layer follows every bump
    and crease of the skin because it IS the skin, lifted by h. Faces with no
    thickness are dropped, so the outline is the rivulet's contact line.
    """
    sel = t.out(t.node('GeometryNodeProximity', {'Target': paths}, target_element='EDGES'), 'Distance').lt(FILM_REACH)
    sel = t.bool('AND', sel, t.attr("gore_clot").lt(0.5))
    near = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': surface, 'Selection': sel}, domain='FACE'),
                 'Selection')
    area = t.out(t.node('GeometryNodeInputMeshFaceArea'))
    big = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': near, 'Selection': area.gt(FILM_FINE)},
                       domain='FACE'), 'Selection')
    small = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': near, 'Selection': area.gt(FILM_FINE)},
                         domain='FACE'), 'Inverted')
    big = t.out(t.node('GeometryNodeSubdivideMesh', {'Mesh': big, 'Level': 2}))
    small = t.out(t.node('GeometryNodeSubdivideMesh', {'Mesh': small, 'Level': 1}))
    g = _join(t, big, small)
    prox = t.node('GeometryNodeProximity', {'Target': paths}, target_element='EDGES')
    d, q = t.out(prox, 'Distance'), t.out(prox, 'Position')
    ni = t.out(t.node('GeometryNodeSampleNearest', {'Geometry': paths, 'Sample Position': q}, domain='POINT'))
    for name, dt in (("d_rad", 'FLOAT'), ("d_cap", 'FLOAT'), ("d_art", 'FLOAT'), ("d_q", 'FLOAT'),
                     ("d_src", 'FLOAT'), ("gore_run", 'FLOAT'), ("gore_runf", 'FLOAT')):
        g = t.store(g, "f_" + name, t.sample(paths, t.attr(name, dt), ni, dt))
    p = t.pos()
    # ragged contact line: the edge pins on the skin's micro relief
    edge_n = t.noise(p * 1400.0, detail=1.0) * 0.08 + t.noise(p * 380.0, detail=2.0) * 0.12 \
        + t.noise(p * 110.0, detail=1.0) * 0.14
    rel = (d / t.attr("f_d_rad").max(0.00015)) * (1.0 + edge_n)
    # cross-section: a low meniscus, fullest in the middle and thinning to a
    # translucent film at the contact line; the crest varies along the run
    # (it gathers where the skin flattens, thins where it runs fast)
    u = (1.0 - rel * rel).max(0.0)
    crest = t.attr("f_d_cap") * (0.72 + 0.56 * t.noise(p * 170.0, detail=2.0, signed=False))
    h = crest * u ** 0.7
    g = t.store(g, "f_h", h)
    hb = F(t, t.node('GeometryNodeBlurAttribute', {'Value': t.attr("f_h"), 'Iterations': 4, 'Weight': 1.0},
                     data_type='FLOAT').outputs[0])
    g = t.store(g, "f_hb", hb)
    g = t.store(g, "f_h", t.attr("f_h").max(t.attr("f_hb")) * t.attr("f_h").gt(1e-6))
    wet = F(t, t.node('GeometryNodeFieldOnDomain', {'Value': t.switch(t.attr("f_h").gt(1e-6), 0.0, 1.0)},
                      domain='FACE', data_type='FLOAT').outputs[0])
    g = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': g, 'Selection': wet.lt(0.34)}, domain='FACE'))
    # the deleted faces leave a stair-step outline (the triangles of the
    # re-meshed skin) that renders as a jagged, pixel-cut paper edge: relax
    # the contact line along itself (only boundary neighbours are averaged,
    # so the film does not shrink) and let it pin on the skin again
    bnd = _edge_float(t, _is_boundary_edge(t)).gt(0.01)
    wb = t.switch(bnd, 0.0, 1.0)
    for _ in range(2):
        sm = F(t, t.node('GeometryNodeBlurAttribute', {'Value': t.pos(), 'Iterations': 4, 'Weight': wb},
                         data_type='FLOAT_VECTOR').outputs[0])
        g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Selection': bnd, 'Position': sm}))
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g,
                                                 'Offset': t.normal() * (t.attr("f_h") + 0.00003)}))
    # Beer-Lambert thickness for the shader: the edge is a thin translucent film
    # (a 0.1-0.3 mm rivulet is still a red film, only pools / thick heads
    # reach the near-black of thick blood)
    g = t.store(g, "gore_bthin", 1.0 - (t.attr("f_h") / 0.00038).clamp() ** 0.8)
    for src, dst in (("f_d_art", "gore_art"), ("f_d_q", "gore_bq"), ("f_d_src", "gore_bsrc"),
                     ("f_gore_run", "gore_run"), ("f_gore_runf", "gore_runf")):
        g = t.store(g, dst, t.attr(src))
    g = t.store(g, "gore_tis", 0.0)
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Wildcard', 'Name': "f_*"}))
    for pat in ("g_*", "gore_wound", "gore_depth", "gore_edge", "gore_bruise", "gore_burn", "gore_fracture",
                "gore_soot", "pl_*", "b_*"):
        g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Wildcard', 'Name': pat}))
    return g


def _drops(t, tips, rest):
    """The front of a running stream (a rounded lobe) and the drops hanging
    where a run reached skin that faces down (chin, nose tip, jaw line,
    earlobe), plus drops falling from them while the flow keeps coming."""
    ico = t.out(t.node('GeometryNodeMeshIcoSphere', {'Radius': 1.0, 'Subdivisions': 2}))
    dw = t.attr("d_w")
    n = _nearest_normal(t, rest, t.pos())
    runs = t.attr("d_len").gt(0.012)
    # moving front: a flat rounded lobe a little wider than the run (the
    # bead of the advancing front, <= 4.5 mm across, 0.3 mm high), stretched
    # downhill -- not a berry
    front = t.bool('AND', runs, t.attr("d_mov").gt(0.5))
    bead_s = (dw * 1.12 * (0.6 + 0.4 * t.smooth(0.012, 0.045, t.attr("d_len")))).min(0.00215)
    beads = t.node('GeometryNodeInstanceOnPoints', {'Points': tips, 'Selection': front,
                                                    'Instance': ico, 'Scale': t.vec(bead_s, bead_s, bead_s * 1.5)})
    beads = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(beads)}))
    beads = t.out(t.node('GeometryNodeSetPosition', {'Geometry': beads, 'Offset': t.vec(0.0, 0.0, -1.0) * (bead_s * 0.55)}))
    beads = t.store(beads, "d_flat", 0.3)
    beads = t.store(beads, "d_rad", bead_s * 1.15)
    beads = t.store(beads, "d_cap", 0.00030)
    # pendant drops where the skin faces down (chin, nose tip, jaw line,
    # earlobe): 30-60 uL = a bead 3-4.5 mm across, flattened against the skin
    # it hangs from, a little longer than wide (REFERENCE_NOTES §5.21)
    hang = t.bool('AND', runs, n.z.lt(-0.3))
    r = 0.0015 + 0.0007 * t.rand(0.0, 1.0, t.index(), 71)
    # (local Z along the skin normal: the drop is a flattened cap on the skin
    # that sags downward, ~2-3 mm proud of it, not a ball stuck on)
    rot = t.out(t.node('FunctionNodeAlignRotationToVector', {'Vector': n}, axis='Z'))
    pend = t.node('GeometryNodeInstanceOnPoints', {'Points': tips, 'Selection': hang, 'Instance': ico,
                                                   'Rotation': rot, 'Scale': t.vec(r, r * 1.15, r * 0.62)})
    pend = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(pend)}))
    pend = t.out(t.node('GeometryNodeSetPosition', {'Geometry': pend, 'Offset': t.vec(0.0, 0.0, -1.0) * (r * 0.35)}))
    # (no drops frozen in mid-air below it: in a still they read as blood
    # floating beside the head, with no path from the wound)
    # a heavy flow does not drip off a low point, it POURS: a thin rope of
    # blood falls from the drop (REFERENCE_NOTES §5.18 F, refs 7 / 21: it
    # falls in ropey strands and sheets), 1-3 mm thick, beading and thinning
    # as it falls, up to ~12 cm below the head in this still
    pour = t.bool('AND', t.bool('AND', hang, t.attr("d_mov").gt(0.5)), t.attr("d_ib").gt(0.55))
    rope_pts = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': tips, 'Selection': pour},
                            domain='POINT'), 'Selection')
    line = t.out(t.node('GeometryNodeCurvePrimitiveLine', {'Start': (0.0, 0.0, 0.0), 'End': (0.0, 0.0, -1.0)}))
    line = t.out(t.node('GeometryNodeResampleCurve', {'Curve': line, 'Count': 40}))
    rl = 0.05 + 0.07 * t.rand(0.0, 1.0, t.attr("d_id", 'INT'), 73)
    rope = t.node('GeometryNodeInstanceOnPoints', {'Points': rope_pts, 'Instance': line,
                                                   'Scale': t.vec(1.0, 1.0, rl)})
    rope = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(rope)}))
    fpar = t.out(t.node('GeometryNodeSplineParameter'), 'Factor')
    rid = t.attr("d_id", 'INT')
    lam = 0.08 + 0.05 * t.rand(0.0, 1.0, rid, 74)
    bead = t.math('SINE', fpar / lam * TAU + rid * 1.3).max(0.0) ** 4.0
    r_rope = (0.0006 + 0.0006 * t.attr("d_ib")) * (1.0 - 0.55 * fpar) * (0.75 + 0.9 * bead * t.smooth(0.15, 0.5, fpar))
    # (a slight sway: a falling stream is never a ruler-straight rod)
    sway = t.noise(t.vec(fpar * 3.0, rid * 0.7, 0.0), detail=1.0, color=True) * (0.004 * fpar)
    rope = t.out(t.node('GeometryNodeSetPosition', {'Geometry': rope, 'Offset': sway * t.vec(1.0, 1.0, 0.0)}))
    rope = t.out(t.node('GeometryNodeSetCurveRadius', {'Curve': rope, 'Radius': r_rope}))
    prof = t.out(t.node('GeometryNodeCurvePrimitiveCircle', {'Resolution': 8, 'Radius': 1.0}, mode='RADIUS'))
    rope = t.out(t.node('GeometryNodeCurveToMesh', {'Curve': rope, 'Profile Curve': prof,
                                                    'Scale': t.out(t.node('GeometryNodeInputRadius')),
                                                    'Fill Caps': True}))
    hung = _join(t, pend, rope)
    hung = t.store(hung, "d_free", 1.0)
    return beads, hung


def _build_blood():
    """Skin-only blood geometry: pools in the wounds, runs down the skin, drops; also the run paths."""
    g_ = 'NodeSocketGeometry'
    t = NodeTree("GH_Gore_Blood",
                 inputs=(("Surface", g_), ("Rest", g_),
                         ("Bullet", g_), ("Exit", g_), ("Slash", g_), ("Blunt", g_), ("Blast", g_),
                         ("Vessels", g_),
                         ("Damage", 'NodeSocketFloat', 1.0), ("Bleed", 'NodeSocketFloat', 0.7),
                         ("Drip Time", 'NodeSocketFloat', 1.0), ("Material", 'NodeSocketMaterial')),
                 outputs=(("Blood", g_), ("Trail", g_)),
                 description="Blood from the cut vessels: pools in the wounds, runs down the skin")
    surface, rest = t.inp("Surface"), t.inp("Rest")
    damage, bleed, drip = t.inp("Damage"), t.inp("Bleed"), t.inp("Drip Time")
    # the vessel data mesh, one geometry per class (packed flow / radius / persistence)
    vg = t.inp("Vessels")
    vg = t.store(vg, "v_data", t.vec(t.attr("v_flow"), t.attr("v_r"), t.attr("v_persist")), 'FLOAT_VECTOR')
    vclass = {}
    for ci, cls in enumerate(VESSEL_CLASSES):
        keep = t.compare('EQUAL', t.attr("v_cls", 'INT'), ci, 'INT')
        vclass[cls] = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': vg, 'Selection': keep},
                                   domain='POINT'), 'Selection')
    sources, seeds = {}, []
    for i, k in enumerate(BLOOD_KINDS):
        sg = t.group(_build_source_group(k), {"Hits": t.inp(k.capitalize()), "Damage": damage, "Bleed": bleed,
                                              "Artery": vclass["artery"], "Vein": vclass["vein"],
                                              "Deep Artery": vclass["deep_artery"], "Sinus": vclass["sinus"]})
        sources[k] = t.out(sg)
        seeds.append(t.out(t.group(_build_seed_group(k, i), {"Hits": sources[k], "Damage": damage,
                                                             "Drip Time": drip})))
    # a broken nose bleeds from the nostrils (epistaxis: torn mucosa of the
    # septum / Kiesselbach's plexus, 10-30 mL/min, arterial and venous): runs
    # leave each nostril, over the sill and down the upper lip
    nh = sources["blunt"]
    hb = _hit_fields(t, damage)
    near_n = t.smooth(0.052, 0.022, (hb["I"] - NOSE_C).length())
    n_amt = (near_n * (t.smooth(0.78, 1.0, hb["D"]) * 0.6 + hb["crush"] * 1.2)).clamp()
    nd = t.node('GeometryNodeDuplicateElements', {'Geometry': nh, 'Amount': n_amt.gt(0.35).max(0.0) * 2.0},
                domain='POINT')
    ng_ = t.out(nd, 'Geometry')
    side = t.switch(t.compare('EQUAL', t.out(nd, 'Duplicate Index'), 0, 'INT'), 1.0, -1.0)
    nN = (0.0, -0.55, -0.835)
    for nm, val in (("hit_I", t.vec(side * NOSTRIL[0], NOSTRIL[1], NOSTRIL[2])), ("hit_N", nN),
                    ("hit_X", (1.0, 0.0, 0.0)), ("hit_Y", (0.0, 0.835, -0.55)), ("hit_Z", nN),
                    ("hit_T", (1.0, 0.0, 0.0))):
        ng_ = t.store(ng_, nm, val, 'FLOAT_VECTOR')
    for nm, val in (("b_q", n_amt * (12.0 + 10.0 * _hash(t, hb["seed"], 51.0)) * bleed / 0.7), ("b_fa", 0.45),
                    ("b_hole", 0.0032), ("b_t0", 0.04), ("b_pers", 0.65), ("b_tis", 0.0), ("b_src", 0.0)):
        ng_ = t.store(ng_, nm, val)
    seeds.append(t.out(t.group(_build_seed_group("bullet", 7, "GH_Gore_DripSeeds_Nose"),
                               {"Hits": ng_, "Damage": damage, "Drip Time": drip})))
    # pools in the openings (grid radius per kind)
    pool_hits = []
    for k in POOL_KINDS:
        hk = sources[k]
        h = _hit_fields(t, damage)
        hole, _r = _wound_extent(t, k, h)
        if k == "slash":
            Tw = t.attr("hit_T", 'FLOAT_VECTOR')
            hl, gape = _slash_params(t, h["s"], h["e"], h["D"], Tw.dot(h["X"]), Tw.dot(h["Y"]), h["R"].x,
                                     h["R"].z)
            rp, rpy = hl * 1.08 + 0.0015, gape * 0.5 + 0.0028
            hk = t.store(hk, "pl_col", 1.0)
        else:
            # (the grid must reach well past the everted, torn margin: a
            # wound wider than the grid showed the pool's square border)
            rp = {"bullet": hole * 2.2 + 0.0012, "exit": hole * 3.2 + 0.004, "blunt": hole * 2.6 + 0.002}[k]
            rpy = rp
            hk = t.store(hk, "pl_col", 0.0)
        hk = t.store(hk, "pl_pulp", {"bullet": 0.0, "exit": 0.75, "blunt": 0.25, "slash": 0.0}[k] + 0.35 * h["crush"])
        hk = t.store(hk, "pl_cr", h["crush"] if k == "blunt" else 0.0)
        # (a blunt split is a channel like a cut: it brims over only at its low end)
        hk = t.store(hk, "pl_spl", 1.0 if k == "blunt" else 0.0)
        hk = t.store(hk, "pl_Ry", rpy)
        pool_hits.append(t.store(hk, "pl_R", rp))
    pool_pts = _join(t, *pool_hits)
    pools = _build_pools(t, pool_pts, surface, drip)
    for pat in ("pl_*", "b_*"):
        pools = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': pools, 'Pattern Mode': 'Wildcard', 'Name': pat}))
    surf2 = _join(t, surface, pools)

    seeds = _join(t, *seeds)
    seeds = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': seeds, 'Pattern Mode': 'Wildcard', 'Name': "hit_*"}))
    seeds = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': seeds, 'Pattern Mode': 'Wildcard', 'Name': "b_*"}))
    seeds = t.store(seeds, "d_id", t.index(), 'INT')
    seeds = t.store(seeds, "d_step", 0.0)
    seeds = t.store(seeds, "d_slow", 0.0)
    seeds = t.store(seeds, "d_mv", 1.0)
    # every run starts on the rim point it spills over, with its first curve
    # point inside the opening (the blood filling the wound)
    seeds = _find_lips(t, seeds, surface)
    p = t.pos()
    snapped = _nearest_point(t, surf2, p) + _nearest_normal(t, surf2, p) * (t.attr("d_w") * 0.2)
    seeds = t.out(t.node('GeometryNodeSetPosition', {'Geometry': seeds, 'Position': snapped}))
    trail1, tips1 = _walk(t, seeds, surf2, DRIP_STEPS, rest)
    pin = t.attr("d_in", 'FLOAT_VECTOR')
    inside = t.out(t.node('GeometryNodeSetPosition', {'Geometry': seeds,
                                                      'Position': _nearest_point(t, surf2, pin)}))
    inside = t.store(inside, "d_step", -1.0)
    trail1 = _join(t, trail1, inside)

    # branches: a heavy run splits where it crosses a bump or a crease; the
    # branch leaves sideways and then follows gravity on its own
    st = t.attr("d_step")
    br_rand = t.rand(0.0, 1.0, t.attr("d_id", 'INT') * 97 + t.math('FLOOR', st), 404)
    pick = t.bool('AND', t.bool('AND', st.gt(4.5), st.lt(DRIP_STEPS - 5.5)),
                  t.bool('AND', br_rand.lt(t.attr("d_ib") * BRANCH_P), t.attr("d_len").gt(0.03)))
    bseeds = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': trail1, 'Selection': pick}, domain='POINT'),
                   'Selection')
    br2 = t.rand(0.0, 1.0, t.attr("d_id", 'INT') * 97 + t.math('FLOOR', st), 405)
    nb = _nearest_normal(t, surf2, t.pos())
    side = nb.cross((0.0, 0.0, -1.0)).normalize() * t.switch(br2.gt(0.5), -1.0, 1.0)
    bseeds = t.store(bseeds, "d_len", t.attr("d_len") * (1.0 - st / float(DRIP_STEPS)) * (0.3 + 0.5 * br2))
    bseeds = t.store(bseeds, "d_w", t.attr("d_w") * (0.45 + 0.2 * br2))
    bseeds = t.store(bseeds, "d_bias", side, 'FLOAT_VECTOR')
    bseeds = t.store(bseeds, "d_id", t.attr("d_id", 'INT') * 64 + t.math('FLOOR', st) + 100000, 'INT')
    bseeds = t.store(bseeds, "d_step", 0.0)
    bseeds = t.store(bseeds, "d_mov", 0.0)
    bseeds = t.store(bseeds, "d_spill", 1.0)
    bseeds = t.store(bseeds, "d_arc0", 0.0)
    trail2, tips2 = _walk(t, bseeds, surf2, BRANCH_STEPS, rest)

    path1 = _run_mesh(t, trail1, surf2, DRIP_STEPS)
    path2 = _run_mesh(t, trail2, surf2, BRANCH_STEPS)
    paths = _join(t, path1, path2)
    film = _film(t, paths, surf2)
    beads, hung = _drops(t, _join(t, tips1, tips2), rest)
    blood = beads
    # flatten the front lobes onto the skin: a low dome thinning to nothing
    # at the edges (a sphere reads as a berry)
    p = t.pos()
    q = _nearest_point(t, surf2, p)
    n = _nearest_normal(t, surf2, p)
    d = p - q
    hn = d.dot(n)
    rel = (hn.max(0.0) / t.attr("d_rad").max(0.0002)).clamp()
    h_new = t.attr("d_cap") * rel ** 0.8
    # film thickness for the shader (Beer-Lambert colour): the edges of a run
    # are a thin translucent film, its middle and its head thick and dark
    blood = t.store(blood, "gore_bthin", 1.0 - (h_new / 0.00022).clamp() ** 0.7)
    flat = q + (d - n * hn) + n * (h_new + 0.00004)
    blood = t.out(t.node('GeometryNodeSetPosition', {'Geometry': blood, 'Position': flat}))
    hung = t.store(hung, "gore_bthin", 0.0)
    runs = _join(t, blood, hung)
    runs = t.store(runs, "gore_art", t.attr("d_art"))
    runs = t.store(runs, "gore_tis", 0.0)
    runs = t.store(runs, "gore_bq", t.attr("d_q"))
    runs = t.store(runs, "gore_bsrc", t.attr("d_src"))
    allb = _join(t, pools, film, runs)
    allb = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': allb, 'Material': t.inp("Material")}))
    allb = t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': allb, 'Shade Smooth': True}))
    t.result("Blood", allb)
    t.result("Trail", paths)
    t.layout()
    return t


# ---------------------------------------------------------------------------
# Bone fragments and teeth
# ---------------------------------------------------------------------------
def _build_fragments():
    """Bone chips: carried outward into the scalp at exits and crushed blunt
    hits, and a cone of inner-table chips driven into the brain behind a
    bullet entrance (REALISM_BIBLE rows 10, 21). Chips are 2-20 mm plates of
    both tables with spongy bone between (material shows the broken diploe)."""
    t = NodeTree("GH_Gore_Fragments",
                 inputs=(("Exit", 'NodeSocketGeometry'), ("Blunt", 'NodeSocketGeometry'),
                         ("Bullet", 'NodeSocketGeometry'), ("Blast", 'NodeSocketGeometry'),
                         ("Damage", 'NodeSocketFloat', 1.0), ("Material", 'NodeSocketMaterial'),
                         ("Is Jaw", 'NodeSocketFloat', 0.0)),
                 outputs=(("Geometry", 'NodeSocketGeometry'),),
                 description="Bone fragments around skull breaches")
    damage = t.inp("Damage")
    parts = []
    # (kind, count, ring radius, lift max, lift min, size min, size max)
    # exit chips stay inside the wound (lifted at most ~4 mm); entrance chips
    # lie 2-14 mm below the outer table, spreading in a cone
    # blast chips (maxilla / mandible) are thrown into the torn tissue of the
    # crater, 1-6 mm; a crushed face has many loose plates
    specs = (("Exit", 6.0, 0.0075, 0.003, 0.0, 0.001, 0.0045),
             ("Blunt", 6.0, 0.0045, -0.001, -0.0025, 0.0008, 0.003),
             ("Bullet", 7.0, 0.0, -0.016, -0.007, 0.0006, 0.0018),
             ("Blast", 18.0, BLAST_R * 0.8, 0.004, -0.012, 0.001, 0.005))
    for kid, (kind, count, rb, lift_max, lift_min, sz0, sz1) in enumerate(specs):
        S = t.attr("hit_S", 'FLOAT_VECTOR')
        s = S.x * (0.3 + 0.7 * damage)
        D = S.z * damage
        thr = {"Exit": 0.8, "Blunt": 0.95, "Bullet": 0.85, "Blast": 0.5}[kind]
        # only on the bone the hit actually reached (not skull AND jaw)
        amount = D.gt(thr) * count * t.attr("hit_ok")
        if kind == "Blast":
            # (made once, on the jaw layer: a shot into the mouth may miss
            # both bones along its axis, so hit_ok says nothing here)
            amount = D.gt(thr) * count * t.inp("Is Jaw")
        if kind == "Blunt":
            crush = t.smooth(1.15, 2.3, t.attr("hit_E") * damage)
            amount = (D.gt(thr).max(crush.gt(0.2)) * (count + 16.0 * crush)) * t.attr("hit_ok")
            rb_k = rb * (1.0 + 3.0 * crush)
        else:
            rb_k = rb
        dup = t.node('GeometryNodeDuplicateElements', {'Geometry': t.inp(kind), 'Amount': amount},
                     domain='POINT')
        g = t.out(dup, 'Geometry')
        idx = t.index()
        a = t.rand(0.0, TAU, idx, 11 + kid)
        rr = t.rand(0.0, 1.0, idx, 12 + kid)
        rl = t.rand(0.0, 1.0, idx, 13 + kid)
        rs = t.rand(0.0, 1.0, idx, 14 + kid)
        I = t.attr("hit_P" if kind == "Blast" else "hit_I", 'FLOAT_VECTOR')
        X, Y, Z = (t.attr(n, 'FLOAT_VECTOR') for n in ("hit_X", "hit_Y", "hit_Z"))
        if kind == "Bullet":
            lift = lift_min + (lift_max - lift_min) * rl
            r = 0.0015 + (-lift) * 0.35 * rr        # cone opening inward
        else:
            lift = lift_min + (lift_max - lift_min) * rl ** 4.0
            r = s * rb_k * (0.25 + 0.75 * rr)
        pos = I + (X * a.cos() + Y * a.sin()) * r + Z * lift
        g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Position': pos}))
        sz = s.sqrt() * (sz0 + (sz1 - sz0) * rs ** 2.5)
        rot = t.out(t.node('FunctionNodeEulerToRotation',
                           {'Euler': t.rand((0, 0, 0), (TAU, TAU, TAU), idx, 15 + kid, 'FLOAT_VECTOR')}))
        # a broken piece of bone is an angular slab: a 5-7 sided prism whose
        # two faces are the outer and inner tables and whose sides are the
        # broken edges showing the red-brown spongy diploe between them
        # (an ellipsoid chip read as a pebble / almond / bean, REFERENCE_NOTES
        # §5.18: bone = matte chalky chunks with thickness)
        # (split edges: every face keeps its own vertices, so the side faces
        # carry c_rim = 1 and the tables 0 without blending across the corner)
        chip = t.out(t.node('GeometryNodeMeshCylinder', {'Vertices': 5 + kid % 3, 'Side Segments': 1,
                                                         'Fill Segments': 1, 'Radius': 1.0, 'Depth': 1.0},
                            fill_type='NGON'))
        chip = t.out(t.node('GeometryNodeSplitEdges', {'Mesh': chip}))
        chip = t.store(chip, "c_rim", t.smooth(0.75, 0.35, t.math('ABSOLUTE', t.normal().z)))
        # chunks of the vault with its real thickness (both tables and the
        # diploe: 2-4 mm; the facial bones 1-2 mm), never paper-thin flakes
        thick = (sz * 0.75).max(0.0012).min(0.0034)
        inst = t.node('GeometryNodeInstanceOnPoints', {'Points': g, 'Instance': chip, 'Rotation': rot,
                                                       'Scale': t.vec(sz * 1.05, sz * (0.6 + 0.5 * rr), thick)})
        inst = t.out(inst)
        # size per chip, for the corner jitter below
        inst = t.store(inst, "c_sz", sz, 'FLOAT', 'INSTANCE')
        parts.append(inst)
    jn = t.node('GeometryNodeJoinGeometry')
    for p in parts:
        t.links.new(p.s, jn.inputs[0])
    g = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(jn)}))
    # irregular broken outlines: every corner of the prism moves by up to
    # ~35 % of the chip's size (noise at the chip's own scale, so the top
    # and bottom corners of one broken edge move together and the slab keeps
    # its thickness), plus a little fine roughness on the fracture faces
    csz = t.attr("c_sz")
    jit = t.noise(t.pos() * 380.0, detail=1.0, color=True) * (csz * 0.7) \
        + t.noise(t.pos() * 2200.0, detail=1.0, color=True) * 0.00015
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Offset': jit}))
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Exact', 'Name': "c_sz"}))
    # (angular broken chunks: flat facets catch the light like chalk, not
    # like a smooth pebble)
    g = t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': g, 'Shade Smooth': False}))
    g = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': g, 'Material': t.inp("Material")}))
    # chips are only partly blood-coated: matte ivory table surfaces, the broken
    # edges show the red-brown spongy diploe, blood in the cracks and pores
    # (fully red chips read as red gummies, clean ones as plaster)
    fn = t.noise(t.pos() * 700.0, detail=2.0, signed=False)
    rim = t.attr("c_rim")
    g = t.store(g, "g_a", t.vec(rim * 0.95, 0.0, (t.smooth(0.52, 0.68, fn) * 0.7).max(rim * 0.45)), 'FLOAT_VECTOR')
    # (a little crack density only: high values stain the whole chip with seeping blood)
    g = t.store(g, "g_b", (0.0, 0.0, 0.3), 'FLOAT_VECTOR')
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Exact', 'Name': "c_rim"}))
    # (g_wk 0: the chip keeps its own wound / blood mask; as a "wall" it would
    # be diploe all over)
    g = t.store(g, "g_wk", 0.0)
    t.result("Geometry", g)
    t.layout()
    return t


def _build_teeth():
    """Knock out / tilt teeth (mesh islands) near blunt hits."""
    t = NodeTree("GH_Gore_Teeth",
                 inputs=(("Geometry", 'NodeSocketGeometry'), ("Blunt", 'NodeSocketGeometry'),
                         ("Count", 'NodeSocketInt', 0), ("Damage", 'NodeSocketFloat', 1.0),
                         ("Tooth Root", 'NodeSocketFloat', 1.0), ("Bullet", 'NodeSocketGeometry'),
                         ("Bullet Count", 'NodeSocketInt', 0), ("Blast", 'NodeSocketGeometry'),
                         ("Blast Count", 'NodeSocketInt', 0)),
                 outputs=(("Geometry", 'NodeSocketGeometry'),),
                 description="Teeth near blunt hits are knocked out or pushed in and tilted")
    isl = t.out(t.node('GeometryNodeInputMeshIsland'), 'Island Index')
    tot = t.node('GeometryNodeAccumulateField', {'Value': t.pos(), 'Group ID': isl}, data_type='FLOAT_VECTOR')
    cnt = t.node('GeometryNodeAccumulateField', {'Value': 1.0, 'Group ID': isl}, data_type='FLOAT')
    cen = t.out(tot, 'Total') / t.out(cnt, 'Total').max(1.0)
    g = t.store(t.inp("Geometry"), "g_cen", cen, 'FLOAT_VECTOR')
    g = t.store(g, "g_isl", isl, 'INT')
    g = t.store(g, "g_kill", 0.0)
    g = t.store(g, "g_tb", 0.0)
    rin, rout, cur = _repeat(t, t.inp("Count"), [("Geometry", 'GEOMETRY', g)])
    i = F(t, rin.outputs['Iteration'])
    c = t.attr("g_cen", 'FLOAT_VECTOR')
    h = _Hit(t, t.inp("Blunt"), i, t.inp("Damage"), P=c)
    rt = h.s * 0.02
    f = t.smooth(rt, rt * 0.4, h.rho) * h.w.gt(-0.06) * t.smooth(0.25, 0.4, h.D)
    isl = t.attr("g_isl", 'INT')
    sd = t.math('MULTIPLY', h.seed, 997.0)
    r1 = t.rand(0.0, 1.0, isl, sd)
    r2 = t.rand(0.0, 1.0, isl, t.math('ADD', sd, 17.0))
    knock = t.bool('AND', r1.lt(0.5), f.gt(0.35))
    gg = t.store(cur["Geometry"], "g_kill", t.attr("g_kill").max(t.switch(knock, 0.0, 1.0)))
    root = t.vec(0.0, 0.0, t.inp("Tooth Root"))
    pivot = c + root * 0.0055
    axis = root.cross(-h.Z).normalize()
    ang = (0.35 + 0.6 * r2) * f
    rot = t.out(t.node('FunctionNodeAxisAngleToRotation', {'Axis': axis, 'Angle': ang}))
    p = t.pos()
    moved = pivot + t.out(t.node('FunctionNodeRotateVector', {'Vector': p - pivot, 'Rotation': rot})) - h.Z * (0.0016 * r2 * f)
    gg = t.out(t.node('GeometryNodeSetPosition', {'Geometry': gg, 'Selection': f.gt(0.01), 'Position': moved}))
    # loosened teeth bleed from the torn gum: blood at the neck of the tooth
    # and a few runs down the crown (a full coat would hide the enamel)
    toward_root = (p - c).dot(root)
    # a film collecting at the gum line and between the teeth, thinning toward the edge
    tb = t.smooth(-0.0035, 0.0008, toward_root) * (0.75 + 0.25 * t.noise(p * 600.0, detail=2.0, signed=False))
    gg = t.store(gg, "g_tb", t.attr("g_tb").max(t.smooth(0.0, 0.3, f) * tb))
    g = _end_repeat(t, rout, [("Geometry", gg)])["Geometry"]
    # a bullet through the mouth shatters the teeth in its path
    rin, rout, cur = _repeat(t, t.inp("Bullet Count"), [("Geometry", 'GEOMETRY', g)])
    i = F(t, rin.outputs['Iteration'])
    hb = _Hit(t, t.inp("Bullet"), i, t.inp("Damage"), P=c)
    in_path = t.bool('AND', hb.rho.lt(hb.s * 0.0085), t.bool('AND', hb.w.gt(-0.03), hb.w.lt(0.008)))
    shot = t.bool('AND', in_path, hb.D.gt(0.3))
    gg = t.store(cur["Geometry"], "g_kill", t.attr("g_kill").max(t.switch(shot, 0.0, 1.0)))
    # the neighbours of a shattered tooth are loosened and bloodied
    near = t.smooth(hb.s * 0.012, hb.s * 0.005, hb.rho) * hb.w.gt(-0.03) * hb.D.gt(0.3)
    gg = t.store(gg, "g_tb", t.attr("g_tb").max(near * t.smooth(-0.0035, 0.0008, (p - c).dot(root))))
    g = _end_repeat(t, rout, [("Geometry", gg)])["Geometry"]
    # a blast in the mouth: the lower teeth in the broken-off mandible segment
    # hang out with it (same rigid transform as the jaw layer), the others
    # near the crater are blown out or left loose, tilted and displaced
    rin, rout, cur = _repeat(t, t.inp("Blast Count"), [("Geometry", 'GEOMETRY', g)])
    i = F(t, rin.outputs['Iteration'])
    hx = _Hit(t, t.inp("Blast"), i, t.inp("Damage"), P=c)

    def hk(k):
        return _hash(t, hx.seed, k)
    on = hx.D.gt(0.5)
    in_frag_c = _blast_fragment(t, hx.s, hk, hx.u, hx.v, hx.w + hx.W)[0]
    lower = t.inp("Tooth Root").lt(0.0)
    frag = in_frag_c * lower * on
    dq = p - hx.I
    pu, pv, pw = dq.dot(hx.X), dq.dot(hx.Y), dq.dot(hx.Z)
    m = _blast_fragment(t, hx.s, hk, pu, pv, pw + hx.W)[1]
    moved_b = hx.I + hx.X * m[0] + hx.Y * m[1] + hx.Z * (m[2] - hx.W)
    Rb = hx.s * BLAST_R
    near_b = t.smooth(Rb * 0.8, Rb * 0.3, hx.rho) * hx.w.gt(-0.05) * on * (1.0 - frag)
    isl_b = t.attr("g_isl", 'INT')
    sdb = t.math('MULTIPLY', hx.seed, 577.0)
    q1 = t.rand(0.0, 1.0, isl_b, sdb)
    q2 = t.rand(0.0, 1.0, isl_b, t.math('ADD', sdb, 5.0))
    qax = t.rand((-1.0, -1.0, -1.0), (1.0, 1.0, 1.0), isl_b, t.math('ADD', sdb, 9.0), 'FLOAT_VECTOR').normalize()
    blown = t.bool('AND', q1.lt(0.55), near_b.gt(0.35))
    gg = t.store(cur["Geometry"], "g_kill", t.attr("g_kill").max(t.switch(blown, 0.0, 1.0)))
    rot_b = t.out(t.node('FunctionNodeAxisAngleToRotation', {'Axis': qax, 'Angle': (0.3 + 0.9 * q2) * near_b}))
    pivot_b = c + root * 0.0055
    loose = pivot_b + t.out(t.node('FunctionNodeRotateVector', {'Vector': p - pivot_b, 'Rotation': rot_b})) \
        + hx.Z * (0.005 * q2 * near_b) - root * (0.003 * q1 * near_b)
    gg = t.out(t.node('GeometryNodeSetPosition', {'Geometry': gg, 'Selection': frag.gt(0.5), 'Position': moved_b}))
    gg = t.out(t.node('GeometryNodeSetPosition', {'Geometry': gg, 'Selection': near_b.gt(0.01), 'Position': loose}))
    gg = t.store(gg, "g_tb", t.attr("g_tb").max(frag.max(near_b) * t.smooth(-0.004, 0.001, (p - c).dot(root))))
    g = _end_repeat(t, rout, [("Geometry", gg)])["Geometry"]
    g = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': g, 'Selection': t.attr("g_kill").gt(0.5)},
                     domain='POINT'))
    t.result("Geometry", g)
    t.layout()
    return t


# ---------------------------------------------------------------------------
# The shared main group
# ---------------------------------------------------------------------------
WALL_STEPS = 9
# cumulative share of the sideways wall movement reached after each ring
# (x^1.9: walls drop steeply at the lip and converge lower down)
WALL_PROFILE = tuple(round((k / WALL_STEPS) ** 1.9, 4) for k in range(1, WALL_STEPS + 1))
# V-shaped incised wounds: depth(v) = D (1 - |v|/hw)^0.8, i.e. the lateral share
# after each ring is (ring depth fraction)^1.25 -- straight-ish V walls that
# meet in a line, not a flat-bottomed U
V_PROFILE = tuple(round((k / WALL_STEPS) ** 1.25, 4) for k in range(1, WALL_STEPS + 1))
VSHAPE_KINDS = ("slash",)
# ring from which the blood fill of a bleeding wound spans the wound bed
FILL_RING = 4
# wall relaxation (Blur Attribute iterations on the wall vertices) and the
# lumpy relief pushed along the wall normal: (scale 1/m, amplitude m)
WALL_RELAX = 10
# wall ring the tissue strands start from (a third of the way down: bridges
# span the deep part of a wound, they do not hang from the lips)
STRAND_RING = 3
WALL_LUMPS = ((210.0, 0.00055), (650.0, 0.00018))
# kinds whose wound bed fills with blood (skin layer, when bleeding), and how
# far the fill reaches toward the centre line: a cut's bed is flooded; an
# entrance hole holds a ring of dark clot around a still-open track
# (bullet entrances have no fill sheet: converging strips read as a camera
# iris; clot blobs sit in the track instead)
# (< 1: the two lips' sheets must never cross -- two sheets crossing along a
# jagged line alternate which one is on top and the bed reads as a dashed strip)
# (blunt splits have no sheet: the ragged split outline made the strip sheet
# shade as a row of dark slats -- the refs/12 stripe artefact; their bed is
# packed with clot lumps instead, as in the references)
# (the incised cut's bed is now flooded by the same liquid surface as the
# other openings, _build_pools: the old strip sheet shaded as a row of slats,
# the refs/12 stripe artefact, and stood below the lips)
FILL_EXTENT = {}
# clot blobs per wall area (relative to CLOT_DENSITY) and the chance that a
# vertex of the first wall ring starts a tissue strand across the gap
CLOT_DENSITY = 30000.0        # blobs per m^2 of wall at factor 1
# (no loose blobs in an incised cut: its bed is under the welling fill, and in
# the narrow scratch tail they showed as a row of black dots)
CLOT_DENSITY_K = {"bullet": 2.5, "exit": 1.3, "slash": 0.0, "blunt": 3.0, "blast": 1.2}
# (none in incised cuts: a knife divides everything in its path -- tissue
# bridges are the forensic sign of a blunt laceration, not of a cut)
# (few and irregular: a dense row of parallel strands across a split reads as
# a comb; real bridges are 1-5 scattered fibres, some torn and hanging)
STRAND_P = {"blunt": 0.0014, "exit": 0.0018, "blast": 0.004}
# wet pulp lumps and torn shreds per wall area (lumps per m^2 at factor 1) and
# per kind: destroyed tissue is mush at three scales (REFERENCE_NOTES §5.18 A)
MUSH_DENSITY = 450000.0
MUSH_K = {"exit": 2.6, "blunt": 1.6, "blast": 1.3}
# extra blood on the wound walls per kind: a bullet track is a narrow tube
# lined with blood and clot (no clean yellow fat), an exit is soaked
WALL_BLOOD = {"bullet": 0.85, "exit": 0.6, "blast": 0.6}
FILL_KINDS = tuple(FILL_EXTENT)
MAIN_INPUTS = (
    ("Geometry", 'NodeSocketGeometry'),
    ("Layer", 'NodeSocketInt', 0, 0, 7, "0 skin, 1 muscle, 2 skull, 3 jaw, 4 brain, 5 eye, 6 teeth, 7 gums"),
    ("Damage", 'NodeSocketFloat', 1.0, 0.0, 1.0, "Wound progression; 0 = intact"),
    ("Bleed", 'NodeSocketFloat', 0.7, 0.0, 1.0, "Blood coverage and drips"),
    ("Drip Time", 'NodeSocketFloat', 1.0, 0.0, 1.0, "How far the drips have run"),
    ("Bruising", 'NodeSocketFloat', 0.6, 0.0, 1.0, "Bruise strength (blunt)"),
    ("Swelling", 'NodeSocketFloat', 0.5, 0.0, 1.0, "Swelling (blunt)"),
    ("Wound Age", 'NodeSocketFloat', 0.2, 0.0, 1.0, "Time since the injuries (hours = 48 * age^2)"),
    ("Bullet Hits", 'NodeSocketCollection'),
    ("Exit Hits", 'NodeSocketCollection'),
    ("Slash Hits", 'NodeSocketCollection'),
    ("Blunt Hits", 'NodeSocketCollection'),
    ("Burn Hits", 'NodeSocketCollection'),
    ("Blast Hits", 'NodeSocketCollection'),
    ("Wall Material", 'NodeSocketMaterial'),
    ("Blood Material", 'NodeSocketMaterial'),
    ("Bone Material", 'NodeSocketMaterial'),
    ("Strand Material", 'NodeSocketMaterial'),
    ("Pulp Material", 'NodeSocketMaterial'),
    ("Detail", 'NodeSocketInt', 2, 0, 4, "Subdivision level of the refined patch around wounds (render)"),
    ("Viewport Detail", 'NodeSocketInt', 1, 0, 4,
     "Refinement level in the viewport: lower = faster live dragging of the hit empties"),
    ("Tooth Root", 'NodeSocketFloat', 1.0, -1.0, 1.0, "+1 = roots point up (upper teeth), -1 = down"),
    ("Vessels", 'NodeSocketObject'),
)


def _edge_float(t, boolean_field):
    """Evaluate a boolean on edges, as a float (reads as 'any edge' on points)."""
    f = t.switch(boolean_field, 0.0, 1.0)
    return F(t, t.node('GeometryNodeFieldOnDomain', {'Value': f}, domain='EDGE', data_type='FLOAT').outputs[0])


def _is_boundary_edge(t):
    fc = t.out(t.node('GeometryNodeInputMeshEdgeNeighbors'), 'Face Count')
    return t.compare('EQUAL', fc, 1, 'INT')


def _join(t, *geos):
    jn = t.node('GeometryNodeJoinGeometry')
    for g in reversed(geos):
        t.links.new(g.s, jn.inputs[0])
    return t.out(jn)


# kind -> per-layer depth below which the wound gets a floor instead of an open wall
FLOOR_BELOW = {
    "bullet": [0.35, 0.78, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
    # (a crushing blow, depth >= 0.8, leaves the muscle open over the fracture)
    "blunt": [0.0, 0.8, 0.0, 0.0, 0.0, 0.0, 0.0, 9.0],
}

_STEP_INPUTS = (
    ("Geometry", 'NodeSocketGeometry'),
    ("Hits", 'NodeSocketGeometry'),
    ("Index", 'NodeSocketInt', 0),
    ("Layer", 'NodeSocketInt', 0),
    ("Damage", 'NodeSocketFloat', 1.0),
    ("Bleed", 'NodeSocketFloat', 0.7),
    ("Swelling", 'NodeSocketFloat', 0.5),
    ("Bruising", 'NodeSocketFloat', 0.6),
    ("Age", 'NodeSocketFloat', 0.2),
)


def _build_region_step(kind):
    """One hit: mark where the mesh must be refined (g_reg)."""
    t = NodeTree(f"GH_Gore_Region_{kind.capitalize()}", _STEP_INPUTS, (("Geometry", 'NodeSocketGeometry'),),
                 description=f"Refinement region of one {kind} hit")
    layer = t.inp("Layer")
    h = _Hit(t, t.inp("Hits"), t.inp("Index"), t.inp("Damage"))
    reg = t.switch(h.within(kind, layer=layer), 0.0, 1.0) * h.gate(layer, kind)
    t.result("Geometry", t.store(t.inp("Geometry"), "g_reg", t.attr("g_reg").max(reg)))
    t.layout()
    return t


def _build_wound_step(kind, kind_group):
    """One hit: evaluate the wound fields and merge them into the g_* attributes."""
    t = NodeTree(f"GH_Gore_Step_{kind.capitalize()}", _STEP_INPUTS, (("Geometry", 'NodeSocketGeometry'),),
                 description=f"Accumulate the fields of one {kind} hit")
    layer = t.inp("Layer")
    h = _Hit(t, t.inp("Hits"), t.inp("Index"), t.inp("Damage"))
    gate = h.gate(layer, kind)
    sel = t.bool('AND', h.within(kind, reach=True, layer=layer), gate.gt(0.0))
    noise_pos = t.pos() + t.vec(h.seed * 0.37, h.seed * 0.21, h.seed * 0.13)
    kn = t.group(kind_group, {"Local": t.vec(h.u, h.v, h.w), "Noise Pos": noise_pos, "Size": h.s,
                              "Elongation": h.e, "Depth": h.D, "Seed": h.seed, "Layer": layer,
                              "Down": t.vec(-h.X.z, -h.Y.z, -h.Z.z), "Swelling": t.inp("Swelling"),
                              "Bruising": t.inp("Bruising"), "Bleed": t.inp("Bleed"),
                              "Tension": t.vec(h.T.dot(h.X), h.T.dot(h.Y), h.T.dot(h.Z)),
                              "Normal": t.vec(h.N.dot(h.X), h.N.dot(h.Y), h.N.dot(h.Z)),
                              "Region": h.R, "Age": t.inp("Age"), "Crush": h.crush, "Axis W": h.W,
                              "Pos": t.pos(), "Axis X": h.X, "Axis Y": h.Y, "Axis Z": h.Z,
                              "Bone Depth": t.switch(t.attr("gh_bone_depth").gt(0.0005), 0.008,
                                                     t.attr("gh_bone_depth"))})

    def o(name):
        return t.out(kn, name)
    # Evaluate the (expensive) wound fields once: pack all 16 outputs into a
    # matrix attribute, then merge them into the g_* attributes cheaply.
    cut = t.switch(gate.gt(0.5), -1.0, o("Cut"))
    wall, out = h.world(o("Wall")), h.world(o("Center"))
    # displace along the pre-refinement normal: it is interpolated exactly like
    # the patch seam, so the refined patch and its neighbours cannot crack apart
    disp = (h.world(o("Disp")) + t.attr("g_n", 'FLOAT_VECTOR') * o("Disp N")) * gate
    vals = [cut, wall.x, wall.y, wall.z, out.x, out.y, out.z, disp.x, disp.y, disp.z,
            o("Wound") * gate, o("Edge") * gate, o("Blood") * gate,
            o("Bruise") * gate, o("Burn") * gate, o("Fracture") * gate]
    pack = t.node('FunctionNodeCombineMatrix')
    for i, v in enumerate(vals):
        t.wire(pack, i, v)
    g = t.store(t.inp("Geometry"), "g_pack", t.out(pack), 'FLOAT4X4', sel=sel)
    un = t.node('FunctionNodeSeparateMatrix', [t.attr("g_pack", 'FLOAT4X4')])
    p = [t.out(un, i) for i in range(16)]
    cut = p[0]
    old_cut = t.attr("g_cut")
    better = cut.gt(old_cut)
    # the hit whose hole outline is nearest decides the wall direction
    g = t.store(g, "g_wall", t.switch(better, t.attr("g_wall", 'FLOAT_VECTOR'), t.vec(p[1], p[2], p[3]), 'VECTOR'),
                'FLOAT_VECTOR', sel=sel)
    g = t.store(g, "g_ctr", t.switch(better, t.attr("g_ctr", 'FLOAT_VECTOR'), t.vec(p[4], p[5], p[6]), 'VECTOR'),
                'FLOAT_VECTOR', sel=sel)
    # shallow wounds get a floor (the wall closes toward the centre line)
    floor_below = FLOOR_BELOW.get(kind)
    floor = h.D.lt(t.pick(layer, floor_below)) if floor_below else 0.0
    g = t.store(g, "g_floor", t.switch(better, t.attr("g_floor"), floor), sel=sel)
    fill = 0.0
    if kind in FILL_KINDS:
        fill = t.switch(t.bool('AND', t.compare('EQUAL', layer, LAYER_SKIN, 'INT'), t.inp("Bleed").gt(0.05)),
                        0.0, FILL_EXTENT[kind])
    g = t.store(g, "g_fill", t.switch(better, t.attr("g_fill"), fill), sel=sel)
    # clot blobs on the walls and tissue strands across the gap (skin and
    # muscle walls of bleeding wounds; see _build_cut)
    soft = t.bool('OR', t.compare('EQUAL', layer, LAYER_SKIN, 'INT'), t.compare('EQUAL', layer, LAYER_MUSCLE, 'INT'))
    clot = t.switch(soft, 0.0, CLOT_DENSITY_K.get(kind, 0.0)) * t.smooth(0.02, 0.2, t.inp("Bleed"))
    strand = t.switch(soft, 0.0, STRAND_P.get(kind, 0.0))
    if kind == "blunt":
        # a crushed area is pulp: more clot, more strands
        clot = clot * (1.0 + h.crush)
        strand = strand * (1.0 + 1.5 * h.crush)
    g = t.store(g, "g_clot", t.switch(better, t.attr("g_clot"), clot), sel=sel)
    # wet pulp lumps / torn shreds in destroyed tissue (_mush): crushed blunt
    # areas, blasts, and the pulped brain pushed out through an exit
    mush = MUSH_K.get(kind, 0.0)
    if kind == "blunt":
        mush = t.smooth(0.2, 0.7, h.crush) * mush
    mush = t.switch(soft, 0.0, mush)
    g = t.store(g, "g_mush", t.switch(better, t.attr("g_mush"), mush), sel=sel)
    # g_mushk = brain (1) + 2 x bleeding + 4 x incised (see _mush)
    g = t.store(g, "g_mushk", t.switch(better, t.attr("g_mushk"), (1.0 if kind == "exit" else 0.0)
                                        + (4.0 if kind == "slash" else 0.0)
                                        + 2.0 * t.smooth(0.02, 0.2, t.inp("Bleed")).gt(0.5)), sel=sel)
    g = t.store(g, "g_wb", t.switch(better, t.attr("g_wb"), WALL_BLOOD.get(kind, 0.0)), sel=sel)
    g = t.store(g, "g_strand", t.switch(better, t.attr("g_strand"), strand), sel=sel)
    g = t.store(g, "g_vshape", t.switch(better, t.attr("g_vshape"), 1.0 if kind in VSHAPE_KINDS else 0.0), sel=sel)
    g = t.store(g, "g_disp", t.attr("g_disp", 'FLOAT_VECTOR') + t.vec(p[7], p[8], p[9]), 'FLOAT_VECTOR', sel=sel)
    g = t.store(g, "g_a", t.vmath('MAXIMUM', t.attr("g_a", 'FLOAT_VECTOR'), t.vec(p[10], p[11], p[12])),
                'FLOAT_VECTOR', sel=sel)
    g = t.store(g, "g_b", t.vmath('MAXIMUM', t.attr("g_b", 'FLOAT_VECTOR'), t.vec(p[13], p[14], p[15])),
                'FLOAT_VECTOR', sel=sel)
    g = t.store(g, "g_cut", old_cut.max(cut), sel=sel)
    # matrix attributes must not reach curve / extrude nodes (Blender 5.0 crash)
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Exact', 'Name': "g_pack"}))
    t.result("Geometry", g)
    t.layout()
    return t


# target edge length after refinement, per layer (m); 0 = never refine
REFINE_TARGET = [0.00045, 0.0006, 0.0006, 0.0006, 0.0, 0.0005, 0.0, 0.0]


def _build_refine():
    """Catmull-Clark the faces flagged in g_reg; creased seam so nothing cracks.

    The level is chosen from the patch's mean edge length so dense and coarse
    meshes both end up near REFINE_TARGET (capped by the Detail input).
    """
    t = NodeTree("GH_Gore_Refine", (("Geometry", 'NodeSocketGeometry'), ("Detail", 'NodeSocketInt', 2),
                                    ("Layer", 'NodeSocketInt', 0)),
                 (("Geometry", 'NodeSocketGeometry'),), description="Local refinement around wounds")
    g = t.inp("Geometry")
    target = t.pick(t.inp("Layer"), REFINE_TARGET)
    refine = t.bool('AND', t.attr("g_reg").gt(0.001), target.gt(0.0))
    sep = t.node('GeometryNodeSeparateGeometry', {'Geometry': g, 'Selection': refine}, domain='FACE')
    patch, rest = t.out(sep, 'Selection'), t.out(sep, 'Inverted')
    ev = t.node('GeometryNodeInputMeshEdgeVertices')
    elen = t.vmath('DISTANCE', t.out(ev, 'Position 1'), t.out(ev, 'Position 2'))
    stat = t.node('GeometryNodeAttributeStatistic', {'Geometry': patch, 'Attribute': elen},
                  domain='EDGE', data_type='FLOAT')
    ratio = t.out(stat, 'Mean') / target.max(1e-6)
    level = t.math('CEIL', t.math('LOGARITHM', ratio.max(1.0), 2.0) - 0.25)
    level = t.clamp(level, 0.0, t.inp("Detail"))
    bnd = _edge_float(t, _is_boundary_edge(t))
    sub = t.node('GeometryNodeSubdivisionSurface', {'Mesh': patch, 'Level': level,
                                                    'Edge Crease': _is_boundary_edge(t),
                                                    'Vertex Crease': bnd.gt(0.0),
                                                    'Limit Surface': True, 'Boundary Smooth': 'All'})
    g = _join(t, t.out(sub), rest)
    g = t.out(t.node('GeometryNodeMergeByDistance', {'Geometry': g, 'Selection': bnd.gt(0.0),
                                                     'Mode': 'All', 'Distance': 1e-6}))
    # every boundary that exists now (mesh openings, patch seams) never grows walls
    g = t.store(g, "g_nowall", _is_boundary_edge(t), 'BOOLEAN', 'EDGE')
    t.result("Geometry", g)
    t.layout()
    return t


def _clot_blobs(t, g, on_faces, factor):
    """Dark, glossy clot lumps scattered over the walls and floor of bleeding wounds.

    Flattened, noise-deformed ico spheres (0.7-3 mm) lying on the wall
    surface, density from g_clot (per wound kind). Real wound walls are
    clot-filled and lumpy, never a clean tissue sheet (refs 3, 4, 13, 15, 16).
    """
    sel = t.bool('AND', on_faces, t.attr("g_clot").gt(0.01))
    dist = t.node('GeometryNodeDistributePointsOnFaces', {'Mesh': g, 'Selection': sel,
                                                          'Density': t.attr("g_clot") * (CLOT_DENSITY * factor),
                                                          'Seed': 7},
                  distribute_method='RANDOM')
    pts, rot = t.out(dist, 'Points'), t.out(dist, 'Rotation')
    idx = t.index()
    r1, r2, r3 = (t.rand(0.0, 1.0, idx, 61 + k) for k in range(3))
    # three scales: grit, 1-2 mm lumps, a few 3-4 mm clots
    sz = 0.0004 + 0.0014 * r1 * r1 + 0.0022 * t.smooth(0.88, 1.0, r2)
    ico = t.out(t.node('GeometryNodeMeshIcoSphere', {'Radius': 1.0, 'Subdivisions': 2}))
    inst = t.node('GeometryNodeInstanceOnPoints', {'Points': pts, 'Instance': ico, 'Rotation': rot,
                                                   'Scale': t.vec(sz * (0.8 + 0.6 * r2), sz * (0.7 + 0.6 * r3),
                                                                  sz * 0.22)})
    blobs = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(inst)}))
    # lumpy, not beads
    jit = t.noise(t.pos() * 1300.0, detail=2.0, color=True) * 0.0003 \
        + t.noise(t.pos() * 3500.0, detail=1.0, color=True) * 0.00012
    blobs = t.out(t.node('GeometryNodeSetPosition', {'Geometry': blobs, 'Offset': jit}))
    # (the shader turns these into matte clot, not glossy beads)
    blobs = t.store(blobs, "gore_clot", 1.0)
    blobs = t.store(blobs, "g_wk", float(WALL_STEPS + 2))
    blobs = t.store(blobs, "g_side", 99.0, 'FLOAT', 'FACE')
    blobs = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': blobs, 'Material': t.inp("Blood Material")}))
    return t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': blobs, 'Shade Smooth': True}))


def _mush(t, g, on_faces):
    """Wet pulp in destroyed tissue: lumps and torn shreds at three scales.

    Scattered over the wound walls and floor where g_mush > 0 (crushed blunt
    areas, blast craters: torn muscle, fat lobules and dark clot; exits: pulped
    cream-grey brain pushed out through the opening, mixed with clot). Big
    folded flaps (4-9 mm), medium lumps (1.5-4 mm) and fine grit (< 1.2 mm),
    each lump a noise-deformed, flattened blob; no order, no pattern
    (REFERENCE_NOTES §5.18 A-C, refs 3, 13, 15, 16, 18).
    """
    sel = t.bool('AND', on_faces, t.attr("g_mush").gt(0.01))
    dist = t.node('GeometryNodeDistributePointsOnFaces', {'Mesh': g, 'Selection': sel,
                                                          'Density': t.attr("g_mush") * MUSH_DENSITY, 'Seed': 23},
                  distribute_method='RANDOM')
    pts, rot, nrm = t.out(dist, 'Points'), t.out(dist, 'Rotation'), t.out(dist, 'Normal')
    idx = t.index()
    r1, r2, r3, r4, r5 = (t.rand(0.0, 1.0, idx, 131 + k) for k in range(5))
    # g_mushk = brain (1) + 2 x bleeding + 4 x incised: no bleeding, no clot
    mk = t.math('FLOOR', t.attr("g_mushk") + 0.5)
    bleeding = t.math('FLOORED_MODULO', t.math('FLOOR', mk / 2.0), 2.0).gt(0.5)
    brain = t.math('FLOORED_MODULO', mk, 2.0).gt(0.5)
    # an incised cut divides tissue cleanly: no torn flaps and no clot, but
    # the cut fat bulges out of its wall as rounded yellow lobules and the
    # cut muscle as dark red bundles below it (the class follows the wall's
    # depth ring, g_wk: fat in the upper half, muscle in the lower)
    incised = mk.gt(3.5)
    upper = t.attr("g_wk").lt(float(WALL_STEPS) * 0.55)
    # three scales: 6 % big torn flaps, 36 % medium lumps, the rest grit
    big = r1.gt(0.98)
    med = t.bool('AND', r1.gt(0.58), t.bool('NOT', big))
    sz = t.switch(big, t.switch(med, 0.0003 + 0.0006 * r2, 0.0009 + 0.0013 * r2), 0.002 + 0.0018 * r2)
    sz = t.switch(brain, sz, sz.min(0.0022))
    sz = t.switch(incised, sz, (sz * 0.7).min(0.0015).max(0.0006))
    # (most pieces are torn shreds and sheets, only some are lumps: rounded
    # blobs read as berries / beads)
    # (pulped brain comes out as soft lumps, not sheets)
    # (the density is high so the lumps fuse into masses; keep the number of
    # separate torn sheets about the same)
    flap = t.bool('AND', t.bool('AND', t.bool('OR', big, r3.lt(0.2)), t.bool('NOT', brain)), t.bool('NOT', incised))
    # flaps: thin torn sheets (0.3-0.6 mm); lumps: flattened blobs
    sx = sz * t.switch(flap, 0.8 + 0.5 * r4, 1.1 + 0.6 * r4)
    sy = sz * t.switch(flap, 0.6 + 0.5 * r5, 0.7 + 0.5 * r3)
    sz_ = t.switch(flap, sz * (0.22 + 0.25 * r5), (sz * 0.12).max(0.0003).min(0.0006))
    # sit on the wall, poking into the wound; brain pulp is pushed OUT through
    # the opening (lifted along the wall's way out and toward the middle)
    wall = t.attr("g_wall", 'FLOAT_VECTOR')
    ctr = t.attr("g_ctr", 'FLOAT_VECTOR')
    cdir = ctr.normalize()
    out = (-(wall - cdir * wall.dot(cdir))).normalize()
    lift = t.switch(brain, (0.0, 0.0, 0.0), out * ((0.0015 + 0.004 * r4 * r4) * (0.4 + 0.6 * r5)) + ctr * (0.25 + 0.6 * r3),
                    'VECTOR')
    lift = t.switch(incised, lift, (0.0, 0.0, 0.0), 'VECTOR')
    pos = t.pos() + nrm * (sz_ * 0.3) + lift
    pts = t.out(t.node('GeometryNodeSetPosition', {'Geometry': pts, 'Position': pos}))
    # material class per lump: 0 muscle, 1 fat (tissue) / brain pulp (exit), 2 clot
    cls_b = t.switch(r4.lt(0.55), t.switch(r4.lt(0.9), 0.0, 2.0), 1.0)      # pulp 55 %, clot 35 %, muscle
    cls_t = t.switch(r4.lt(0.42), t.switch(r4.lt(0.62), 2.0, 1.0), 0.0)      # muscle 42 %, fat 20 %, clot
    cls = t.switch(brain, cls_t, cls_b)
    cls = t.switch(t.bool('AND', cls.gt(1.5), t.bool('NOT', bleeding)), cls, 0.0)
    cls = t.switch(incised, cls, t.switch(upper, 0.0, 1.0))
    pts = t.store(pts, "m_cls", cls)
    pts = t.store(pts, "m_flap", t.switch(flap, 0.0, 1.0))
    # (sizes are random per point index: keep them before the points are split)
    pts = t.store(pts, "m_sc", t.vec(sx, sy, sz_), 'FLOAT_VECTOR')
    pts = t.store(pts, "m_sz", sz)
    # ---- torn flaps: thin crumpled sheets (tissue only) ---------------------
    flap_pts = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': pts, 'Selection': flap}, domain='POINT'),
                     'Selection')
    ico = t.out(t.node('GeometryNodeMeshIcoSphere', {'Radius': 1.0, 'Subdivisions': 2}))
    inst = t.node('GeometryNodeInstanceOnPoints', {'Points': flap_pts, 'Instance': ico, 'Rotation': rot,
                                                   'Scale': t.attr("m_sc", 'FLOAT_VECTOR')})
    sheets = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(inst)}))
    # crumple: a low-frequency fold bends each sheet, finer noise tears it
    jit = t.noise(t.pos() * 350.0, detail=1.0, color=True) * 0.0009 \
        + t.noise(t.pos() * 900.0, detail=2.0, color=True) * 0.0004 \
        + t.noise(t.pos() * 2400.0, detail=1.0, color=True) * 0.00012
    sheets = t.out(t.node('GeometryNodeSetPosition', {'Geometry': sheets, 'Offset': jit}))
    # ---- lumps: ONE merged, torn mass per tissue class ----------------------
    # (separate smooth ellipsoids read as beans / pebbles / candy: the lumps
    # of a class are fused through a volume -- a union of 0.5-4 mm balls at
    # three scales -- and the surface is torn by noise, so pulp is a
    # continuous wet mush with lobes, pits and crevices, REFERENCE_NOTES
    # §5.18 A, refs 3, 4, 13, 15, 16)
    lump_pts = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': pts, 'Selection': flap}, domain='POINT'),
                     'Inverted')
    # ball radius: the lump size, pulp a little fuller; buried half in the wall
    # (small balls, 0.45-1.7 mm: their union is a lumpy aggregate; a few
    # big balls fused into round cherries / dough balls)
    rad = (t.attr("m_sz") * t.switch(brain, 0.55, 0.7)).max(0.00045).min(0.0017)
    lump_pts = t.out(t.node('GeometryNodeSetPosition', {'Geometry': lump_pts,
                                                        'Offset': nrm * (rad * -0.25)}))
    lump_pts = t.store(lump_pts, "m_r", rad)
    k = t.attr("m_cls")
    classes = (
        # (selection, material input, g_wk, gore_clot, blood amount)
        (t.bool('AND', k.lt(0.5), t.bool('NOT', brain)), "Strand Material", float(WALL_STEPS + 2), 0.0, 0.45),
        (t.bool('AND', t.bool('AND', k.gt(0.5), k.lt(1.5)), t.bool('NOT', brain)), "Wall Material",
         WALL_STEPS * 0.4, 0.0, 0.3),
        (t.bool('AND', k.lt(1.5), brain), "Pulp Material", float(WALL_STEPS + 2), 0.0, 0.7),
        # (clot: matte near-black jelly in the blood shader, gore_clot = 1)
        (k.gt(1.5), "Blood Material", float(WALL_STEPS + 2), 1.0, 1.0),
    )
    masses = []
    for ci, (sel_c, mat_in, wk, clot_v, bl_amt) in enumerate(classes):
        cp = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': lump_pts, 'Selection': sel_c},
                          domain='POINT'), 'Selection')
        vol = t.out(t.node('GeometryNodePointsToVolume', {'Points': cp, 'Density': 1.0, 'Resolution Mode': 'Size',
                                                          'Voxel Size': 0.00022, 'Radius': t.attr("m_r")}))
        mm = t.out(t.node('GeometryNodeVolumeToMesh', {'Volume': vol, 'Resolution Mode': 'Grid',
                                                       'Threshold': 0.3, 'Adaptivity': 0.0}))
        # tear the fused surface: folds, pits and crevices at three scales
        pn = t.pos()
        tear = t.noise(pn * 520.0 + t.vec(ci * 3.1, 0.0, 0.0), detail=2.0) * 0.00055 \
            + t.noise(pn * 1500.0, detail=2.0) * 0.0002 \
            + (t.noise(pn * 220.0, detail=1.0, signed=False) - 0.5).max(0.0) * -0.0022
        mm = t.out(t.node('GeometryNodeSetPosition', {'Geometry': mm, 'Offset': t.normal() * tear}))
        bl_ = t.noise(pn * 600.0 + t.vec(0.0, ci * 1.7, 0.0), detail=2.0, signed=False)
        mm = t.store(mm, "g_a", t.vec(1.0, 0.0, t.smooth(0.45, 0.8, bl_) * bl_amt), 'FLOAT_VECTOR')
        mm = t.store(mm, "g_own", 1.0)
        mm = t.store(mm, "gore_clot", clot_v)
        mm = t.store(mm, "g_wk", wk)
        mm = t.store(mm, "g_side", 99.0, 'FLOAT', 'FACE')
        mm = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': mm, 'Material': t.inp(mat_in)}))
        masses.append(mm)
    # sheets: their own blood streaks and material per class
    bl_ = t.noise(t.pos() * 600.0, detail=2.0, signed=False)
    sheets = t.store(sheets, "g_a", t.vec(1.0, 0.0, t.smooth(0.5, 0.8, bl_) * 0.45), 'FLOAT_VECTOR')
    sheets = t.store(sheets, "g_own", 1.0)
    ks = t.attr("m_cls")
    is_mus, is_mid, is_clot = ks.lt(0.5), t.bool('AND', ks.gt(0.5), ks.lt(1.5)), ks.gt(1.5)
    sheets = t.store(sheets, "gore_clot", t.switch(is_clot, 0.0, 1.0))
    # fat sheets take the upper wall's depth (yellow, the pale fatty underside
    # of a torn flap); the rest the deep wall
    sheets = t.store(sheets, "g_wk", t.switch(is_mid, float(WALL_STEPS + 2), WALL_STEPS * 0.4))
    sheets = t.store(sheets, "g_side", 99.0, 'FLOAT', 'FACE')
    sheets = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': sheets, 'Selection': is_mus,
                                                      'Material': t.inp("Strand Material")}))
    sheets = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': sheets, 'Selection': is_mid,
                                                      'Material': t.inp("Wall Material")}))
    sheets = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': sheets, 'Selection': is_clot,
                                                      'Material': t.inp("Blood Material")}))
    m = _join(t, sheets, *masses)
    for nm in ("m_cls", "m_flap", "m_r", "m_sc", "m_sz"):
        m = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': m, 'Pattern Mode': 'Exact', 'Name': nm}))
    return t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': m, 'Shade Smooth': True}))


def _tissue_strands(t, g, vshape):
    """Tissue bridges: sagging strands of fibrous tissue / vessels spanning the gap.

    Started from random vertices of the first wall ring (chance g_strand) and
    running across the wound's centre line to the opposite wall, sagging
    down into the wound. 0.25-0.6 mm thick, a little thinner in the middle.
    """
    ring1 = t.attr("g_ring1", 'BOOLEAN')
    pick = t.rand(0.0, 1.0, t.index(), 97).lt(t.attr("g_strand"))
    ctr = t.attr("g_ctr", 'FLOAT_VECTOR')
    wall = t.attr("g_wall", 'FLOAT_VECTOR')
    cdir = ctr.normalize()
    lat = cdir * wall.dot(cdir)
    dn = wall - lat
    cum1 = t.mix(WALL_PROFILE[STRAND_RING - 1], V_PROFILE[STRAND_RING - 1], vshape)
    span = (ctr - lat * cum1) * 2.0
    sl = span.length()
    ok = t.bool('AND', t.bool('AND', ring1, pick), t.bool('AND', sl.gt(0.0009), sl.lt(0.014)))
    pts = t.out(t.node('GeometryNodeMeshToPoints', {'Mesh': g, 'Selection': ok}, mode='VERTICES'))
    rr = t.rand(0.0, 1.0, t.index(), 98)
    r2 = t.rand(0.0, 1.0, t.index(), 96)
    r3 = t.rand(0.0, 1.0, t.index(), 95)
    # (never a comb of parallel bars: each strand runs at its own slant along
    # the wound, some are torn through and hang into the wound from one side)
    tang = cdir.cross(dn.normalize())
    span = span + tang * (sl * (r2 - 0.5) * 1.4)
    torn = r3.lt(0.35)
    span = span * t.switch(torn, 1.0, 0.35 + 0.3 * rr)
    sag = t.switch(torn, 0.04 + 0.16 * rr, 0.35 + 0.4 * rr)
    pts = t.store(pts, "s_a", t.pos(), 'FLOAT_VECTOR')
    pts = t.store(pts, "s_b", span, 'FLOAT_VECTOR')
    pts = t.store(pts, "s_c", dn * sag + span * ((rr - 0.5) * 0.25), 'FLOAT_VECTOR')
    pts = t.store(pts, "s_r", 0.00015 + 0.00045 * t.rand(0.0, 1.0, t.index(), 99) ** 2.0)
    pts = t.store(pts, "s_t", t.switch(torn, 0.0, 1.0))
    line = t.out(t.node('GeometryNodeCurvePrimitiveLine', {'Start': (0.0, 0.0, 0.0), 'End': (1.0, 0.0, 0.0)}))
    line = t.out(t.node('GeometryNodeResampleCurve', {'Curve': line, 'Count': 10}))
    inst = t.node('GeometryNodeInstanceOnPoints', {'Points': pts, 'Instance': line})
    cur = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(inst)}))
    f = t.out(t.node('GeometryNodeSplineParameter'), 'Factor')
    # an intact bridge sags in the middle; a torn one hangs down from its root
    bell = t.mix(f * (1.0 - f) * 4.0, f * f * 1.6, t.attr("s_t"))
    wob = t.noise(t.attr("s_a", 'FLOAT_VECTOR') * 900.0 + t.vec(f * 3.0, 0.0, 0.0), detail=1.0, color=True)
    pos = t.attr("s_a", 'FLOAT_VECTOR') + t.attr("s_b", 'FLOAT_VECTOR') * f \
        + t.attr("s_c", 'FLOAT_VECTOR') * bell + wob * (0.0003 * bell)
    cur = t.out(t.node('GeometryNodeSetPosition', {'Geometry': cur, 'Position': pos}))
    cur = t.out(t.node('GeometryNodeSetCurveRadius', {'Curve': cur, 'Radius': t.attr("s_r") * (1.0 - 0.4 * bell)}))
    prof = t.out(t.node('GeometryNodeCurvePrimitiveCircle', {'Resolution': 8, 'Radius': 1.0}, mode='RADIUS'))
    mesh = t.out(t.node('GeometryNodeCurveToMesh', {'Curve': cur, 'Profile Curve': prof,
                                                    'Scale': t.out(t.node('GeometryNodeInputRadius')),
                                                    'Fill Caps': True}))
    for name in ("s_a", "s_b", "s_c", "s_r", "s_t"):
        mesh = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': mesh, 'Pattern Mode': 'Exact', 'Name': name}))
    mesh = t.store(mesh, "g_wk", 3.0)
    mesh = t.store(mesh, "g_side", 99.0, 'FLOAT', 'FACE')
    return t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': mesh, 'Shade Smooth': True}))


def _build_cut():
    """Displace, delete the holes, snap the rims and extrude thick walls."""
    t = NodeTree("GH_Gore_Cut", (("Geometry", 'NodeSocketGeometry'), ("Layer", 'NodeSocketInt', 0),
                                 ("Wall Material", 'NodeSocketMaterial'), ("Blood Material", 'NodeSocketMaterial'),
                                 ("Strand Material", 'NodeSocketMaterial'), ("Drip Time", 'NodeSocketFloat', 1.0),
                                 ("Pulp Material", 'NodeSocketMaterial')),
                 (("Geometry", 'NodeSocketGeometry'),), description="Holes and wound walls")
    layer = t.inp("Layer")
    # gradient of the hole field from the edges around each vertex (before
    # anything moves): used to pull rim vertices exactly onto the outline
    ev = t.node('GeometryNodeInputMeshEdgeVertices')
    p1, p2 = t.out(ev, 'Position 1'), t.out(ev, 'Position 2')

    def cut_at(i):
        return t.out(t.node('GeometryNodeFieldAtIndex', {'Value': t.attr("g_cut"), 'Index': t.out(ev, i)},
                            domain='POINT', data_type='FLOAT'))
    dp = p2 - p1
    ge = dp * ((cut_at('Vertex Index 2') - cut_at('Vertex Index 1')) / dp.dot(dp).max(1e-14))
    grad = F(t, t.node('GeometryNodeFieldOnDomain', {'Value': ge}, domain='EDGE', data_type='FLOAT_VECTOR').outputs[0])
    g = t.store(t.inp("Geometry"), "g_grad", grad * 2.0, 'FLOAT_VECTOR')
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Offset': t.attr("g_disp", 'FLOAT_VECTOR')}))
    g = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': g, 'Selection': t.attr("g_cut").gt(0.0)},
                     domain='FACE', mode='ALL'))
    new_rim = t.bool('AND', _is_boundary_edge(t), t.bool('NOT', t.attr("g_nowall", 'BOOLEAN')))
    g = t.store(g, "g_rim", t.switch(new_rim, 0.0, 1.0), 'FLOAT', 'EDGE')
    # pull rim vertices onto the exact (noisy) outline so the edge is not stair-stepped
    # one Newton step of the hole field: p -= cut * grad / |grad|^2 (clamped)
    gr = t.attr("g_grad", 'FLOAT_VECTOR')
    step = gr * (-t.attr("g_cut") / gr.dot(gr).max(1e-6))
    snap = step * (0.0008 / step.length().max(0.0008))
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Selection': t.attr("g_rim").gt(0.0), 'Offset': snap}))
    # smooth the rim along itself (only rim vertices take part): the snap onto
    # the noisy outline leaves a vertex-scale zig-zag whose facets catch the
    # light one by one (a row of glints / saw teeth along the cut edge); the
    # lobes and notches of the outline (mm scale) are kept
    rim_v = F(t, t.node('GeometryNodeFieldOnDomain', {'Value': t.attr("g_rim")}, domain='POINT',
                        data_type='FLOAT').outputs[0]).gt(0.0)
    rim_w = t.switch(rim_v, 0.0, 1.0)
    rblur = t.node('GeometryNodeBlurAttribute', {'Value': t.pos(), 'Iterations': 4, 'Weight': rim_w},
                   data_type='FLOAT_VECTOR')
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Selection': rim_v, 'Position': t.out(rblur)}))
    for name in ("g_grad", "g_disp", "g_cut", "g_nowall"):
        g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Exact', 'Name': name}))
    g = t.store(g, "g_wk", 0.0)
    sel_e = t.attr("g_rim").gt(0.5)
    wall = t.attr("g_wall", 'FLOAT_VECTOR')
    # split the wall into its sideways part (toward the wound's centre) and the
    # rest; the sideways part follows WALL_PROFILE, so walls drop steeply at
    # the lip (the cut skin edge) and converge lower down, not as one ramp
    ctr = t.attr("g_ctr", 'FLOAT_VECTOR')
    cdir = ctr.normalize()
    lat = cdir * wall.dot(cdir)
    dn = wall - lat
    prev = 0.0
    vshape = t.attr("g_vshape")
    # (no per-ring random jitter: sideways jitter larger than the spacing of
    # the columns folds the wall like an accordion, and every fold shades as
    # a light/dark stripe -- the "fence plank" artefact of refs/12. The ring
    # spacing varies smoothly along the rim instead, and the relief is added
    # afterwards along the wall normal only.)
    for k in range(1, WALL_STEPS + 1):
        cum = t.mix(WALL_PROFILE[k - 1], V_PROFILE[k - 1], vshape)
        sp = t.noise(t.pos() * 150.0 + t.vec(1.3, 2.9, 0.7 + 0.37 * k), detail=1.0)
        ex = t.node('GeometryNodeExtrudeMesh', {'Mesh': g, 'Selection': sel_e,
                                                'Offset': dn * ((1.0 + 0.3 * sp) / WALL_STEPS) + lat * (cum - prev)},
                    mode='EDGES')
        prev = cum
        g, top, side = t.out(ex, 'Mesh'), t.out(ex, 'Top'), t.out(ex, 'Side')
        g = t.store(g, "g_wk", float(k), sel=top)
        g = t.store(g, "g_side", float(k), 'FLOAT', 'FACE', sel=side)
        if k == FILL_RING:
            g = t.store(g, "g_fring", top, 'BOOLEAN', 'EDGE')
        if k == STRAND_RING:
            g = t.store(g, "g_ring1", top, 'BOOLEAN', 'POINT')
        sel_e = top
    # floor: shallow wounds close toward their centre line, a bloody bed of tissue
    k = WALL_STEPS + 1
    fsel = t.bool('AND', sel_e, t.attr("g_floor").gt(0.5))
    ex = t.node('GeometryNodeExtrudeMesh', {'Mesh': g, 'Selection': fsel,
                                            'Offset': (ctr - lat) * 0.92}, mode='EDGES')
    g = t.store(t.out(ex, 'Mesh'), "g_wk", float(k), sel=t.out(ex, 'Top'))
    g = t.store(g, "g_side", float(k), 'FLOAT', 'FACE', sel=t.out(ex, 'Side'))
    # relax the wall: the rim outline is ragged (it follows the noisy hole
    # field), and without this every zig-zag of the rim would run straight
    # down the wall as a crease. The rim itself (g_wk = 0) stays put.
    wallv = t.attr("g_wk").gt(0.5)
    blur = t.node('GeometryNodeBlurAttribute', {'Value': t.pos(), 'Iterations': WALL_RELAX, 'Weight': 1.0},
                  data_type='FLOAT_VECTOR')
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Selection': wallv, 'Position': t.out(blur)}))
    # lumpy torn tissue: multi-octave 3D noise pushed along the wall normal
    # only (neighbouring columns move together, so nothing can fold), growing
    # with depth; no pattern repeats along the rim or down the wall
    p = t.pos()
    fr_w = (t.attr("g_wk") / float(WALL_STEPS)).clamp()
    lump = None
    for sc, amp in WALL_LUMPS:
        term = t.noise(p * sc + t.vec(0.7, 3.1, 1.9), detail=2.0, rough=0.55) * amp
        lump = term if lump is None else lump + term
    # torn (not incised) walls also bulge and pit at the ~5-15 mm scale
    lump = lump + t.noise(p * 75.0 + t.vec(2.3, 0.4, 5.1), detail=2.0) * 0.0011 * (1.0 - vshape)
    # an incised wall is a clean section, but never a smooth plane: the cut
    # subcutaneous fat bulges out as rounded yellow lobules (2-4 mm, domed,
    # with thin septa between them) and the cut muscle below shows its
    # bundles as low ridges (the colours come from GH_Fat by depth; this is
    # the relief, so the wall has real shape at the 1-4 mm scale)
    lv = t.voronoi(p + t.noise(p * 300.0, detail=1.0, color=True) * 0.0006, 380.0, 'F1', 1.0)
    ld = t.out(lv, 'Distance')
    dome = (1.0 - (ld / 0.72) ** 2.0).max(0.0).sqrt()
    fat_band = t.smooth(0.08, 0.2, fr_w) * t.smooth(0.8, 0.66, fr_w)
    mus_band = t.smooth(0.74, 0.86, fr_w)
    bund = t.noise(p * t.vec(160.0, 160.0, 900.0) + t.vec(1.3, 0.2, 0.7), detail=2.0)
    lump = lump + vshape * (fat_band * dome * 0.00042 + mus_band * bund * 0.00022)
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g, 'Selection': wallv,
                                                 'Offset': t.normal() * (lump * (0.35 + 0.65 * fr_w))}))
    # blood filling the bed of a bleeding cut: a separate liquid sheet spanning
    # the bed. It WELLS UP with time: at drip_time 0 it lies at the bottom of
    # the wound, within the first ~7 s (drip_time 0.12) it rises to its final
    # level about a third of the way down the wall, from where it overflows
    # the lowest point of the rim (the runs, see _build_blood).
    fill_t = t.smooth(0.0, 0.12, t.inp("Drip Time"))
    level = t.mix(0.42, -0.26, fill_t)
    rsel = t.bool('AND', t.attr("g_fring", 'BOOLEAN'), t.attr("g_fill").gt(0.05))
    fill = t.out(t.node('GeometryNodeDuplicateElements', {'Geometry': g, 'Selection': rsel}, domain='EDGE'),
                 'Geometry')
    # (duplicated edges come out loose: weld them back into one ring, or every
    # edge extrudes into its own glossy slat with its own normal)
    fill = t.out(t.node('GeometryNodeMergeByDistance', {'Geometry': fill, 'Distance': 1e-6}))
    remain = ctr - lat * t.mix(WALL_PROFILE[FILL_RING - 1], V_PROFILE[FILL_RING - 1], vshape)
    # start a little inside the wall so the liquid meets it without a gap
    # (moving the level up also moves the sheet's edge out with the wall)
    fill = t.out(t.node('GeometryNodeSetPosition', {'Geometry': fill,
                                                    'Offset': -remain * 0.06 + dn * (0.03 + level) + lat * level}))
    # (the two lips' sheets sag a little toward the centre line and cross in a
    # shallow V there: two coplanar overlapping sheets, or jittered strips,
    # catch the light as a row of glossy slats)
    ex = t.node('GeometryNodeExtrudeMesh', {'Mesh': fill, 'Offset': (remain - lat * level) * t.attr("g_fill")
                                            + dn * 0.2}, mode='EDGES')
    fill = t.out(ex, 'Mesh')
    # (the sheet is one long thin strip per rim edge: relax it along the ring,
    # or every strip gets its own normal and the bed shades as a row of slats;
    # its lumps and clots are separate blobs and shader detail, never values
    # stored on the strips' ends)
    fill = t.out(t.node('GeometryNodeSubdivideMesh', {'Mesh': fill, 'Level': 1}))
    fblur = t.node('GeometryNodeBlurAttribute', {'Value': t.pos(), 'Iterations': 6, 'Weight': 1.0},
                   data_type='FLOAT_VECTOR')
    fill = t.out(t.node('GeometryNodeSetPosition', {'Geometry': fill, 'Position': t.out(fblur)}))
    fill = t.store(fill, "g_wk", float(WALL_STEPS + 2))
    fill = t.store(fill, "g_side", 99.0, 'FLOAT', 'FACE')
    fill = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': fill, 'Material': t.inp("Blood Material")}))
    fill = t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': fill, 'Shade Smooth': True}))
    side = t.attr("g_side")
    # (on the lower half of the walls, the floor and the fill: a clot sitting
    # right at the lip reads as a pill stuck to the cut edge)
    clots = _join(t, _clot_blobs(t, g, t.bool('AND', side.gt(WALL_STEPS * 0.5 - 0.5), side.lt(WALL_STEPS + 1.5)),
                                 0.8),
                  _clot_blobs(t, fill, t.attr("g_fill").gt(0.05), 0.7))
    strands = _tissue_strands(t, g, vshape)
    # wet pulp and shreds over the walls and floor of destroyed tissue
    mush = _mush(t, g, t.bool('AND', side.gt(0.5), side.lt(WALL_STEPS + 1.5)))
    # every wall ring gets the wall material (it paints the thin dermis line at
    # its top itself): skin's random-walk subsurface on thin, folded wall
    # strips leaks light and shows as glowing white tabs
    wall_from = t.pick(layer, [1.0, 1.0, 1.0, 1.0, 99.0, 1.0, 99.0, 1.0])
    side_k = t.attr("g_side")
    g = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': g, 'Selection': t.bool('AND', side_k.gt(wall_from - 0.5),
                                                                                   side_k.lt(50.0)),
                                                 'Material': t.inp("Wall Material")}))
    g = t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': g, 'Selection': t.attr("g_side").gt(0.5),
                                                    'Shade Smooth': True}))
    # the cut skin edge (between the surface and the first wall ring) is a
    # crisp edge, not a smooth-shaded "pillow" rolling into the wound: the
    # face average of g_side is 0.5 exactly on those edges
    side_e = F(t, t.node('GeometryNodeFieldOnDomain', {'Value': t.attr("g_side")}, domain='EDGE',
                         data_type='FLOAT').outputs[0])
    g = t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': g, 'Selection': t.bool('AND', side_e.gt(0.3), side_e.lt(0.7)),
                                                    'Shade Smooth': False}, domain='EDGE'))
    strands = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': strands, 'Material': t.inp("Strand Material")}))
    t.result("Geometry", _join(t, g, fill, clots, strands, mush))
    t.layout()
    return t


def _build_attributes():
    """Write the contract's gore_* point attributes from the g_* work attributes."""
    t = NodeTree("GH_Gore_Attributes", (("Geometry", 'NodeSocketGeometry'), ("Layer", 'NodeSocketInt', 0)),
                 (("Geometry", 'NodeSocketGeometry'),), description="gore_* attributes for the shaders")
    layer = t.inp("Layer")
    wk = t.attr("g_wk")
    wallf = t.switch(wk.gt(0.0), 0.0, 1.0)
    fr = t.clamp(wk / float(WALL_STEPS))
    a, b = t.attr("g_a", 'FLOAT_VECTOR'), t.attr("g_b", 'FLOAT_VECTOR')
    d0, d1 = t.pick(layer, LAYER_D0), t.pick(layer, LAYER_D1)
    depth = t.mix(a.x.clamp() * t.pick(layer, LAYER_SURF_D), d0 + (d1 - d0) * fr, wallf)
    # wound walls inherit the attributes of the rim vertex they grew from, so
    # anything that varies along the rim would run down the wall in stripes:
    # blood on the walls comes from the wall's own depth and position instead
    p = t.pos()
    wn = t.noise(p * 330.0, detail=3.0, signed=False)
    wn2 = t.noise(p * 90.0, detail=2.0, signed=False)
    # patches of real blood (clear tissue between them), not a thin pink veil
    # over everything
    wall_blood = t.smooth(0.42, 0.62, t.pick(layer, [0.72, 0.7, 0.55, 0.55, 0.5, 0.7, 0.3, 0.6]) * (0.5 + 0.5 * fr)
                          + (wn - 0.5) * 0.9 + (wn2 - 0.5) * 0.5)
    # (pulp lumps and shreds carry their own blood mask, g_own)
    wall_blood = t.mix(wall_blood, a.z, t.attr("g_own"))
    vals = {
        "gore_wound": a.x.max(wallf).clamp(),
        "gore_depth": depth,
        "gore_edge": (a.y * (1.0 - wallf)).clamp(),
        # (surface blood on the surface, the wall's own blood on the walls)
        "gore_blood": t.mix(a.z.max(t.attr("g_tb")),
                            t.mix(wall_blood.max(a.z * 0.5).max(t.attr("g_wb") * (0.7 + 0.3 * wn)), a.z,
                                  t.attr("g_own")), wallf).clamp(),
        "gore_bruise": b.x.clamp(),
        "gore_burn": b.y.clamp(),
        # the last channel is bone fracture on bone, gunpowder soot on the skin
        "gore_fracture": (b.z * t.pick(layer, [0.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0])).clamp(),
        "gore_soot": (b.z * t.pick(layer, [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])).clamp(),
    }
    g = t.inp("Geometry")
    for name in ATTRS:
        g = t.store(g, name, vals[name])
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Wildcard', 'Name': "g_*"}))
    t.result("Geometry", g)
    t.layout()
    return t


def build_gore_node_group():
    """(Re)build the shared GH_Gore node group and all its subgroups. Returns the group."""
    _SUBGROUPS.clear()
    # Subgroups first: editing a tree that is already used by a parent is slow.
    kind_groups = {k: KIND_BUILDERS[k]() for k in KINDS}
    region_steps = {k: _build_region_step(k) for k in KINDS}
    wound_steps = {k: _build_wound_step(k, kind_groups[k]) for k in KINDS}
    hp = _build_hit_points()
    blood_g = _build_blood()
    frag_g = _build_fragments()
    teeth_g = _build_teeth()
    refine_g = _build_refine()
    cut_g = _build_cut()
    attr_g = _build_attributes()

    t = NodeTree(GROUP_NAME, MAIN_INPUTS, (("Geometry", 'NodeSocketGeometry'),), modifier=True,
                 description="Layered live gore: reads the GH_Hits_* empties")
    geo_in = t.inp("Geometry")
    layer = t.inp("Layer")
    damage = t.inp("Damage")
    bleed = t.inp("Bleed") * (damage * 2.0).min(1.0)
    step_ins = {"Layer": layer, "Damage": damage, "Bleed": bleed,
                "Swelling": t.inp("Swelling") * damage, "Bruising": t.inp("Bruising") * damage,
                "Age": t.inp("Wound Age")}

    hits = {}
    total = None
    for i, k in enumerate(KINDS):
        n = t.group(hp, {"Collection": t.inp(f"{k.capitalize()} Hits"), "Target": geo_in,
                         "Layer Z": t.pick(layer, LAYER_Z), "Kind": i})
        hits[k] = (t.out(n, 'Points'), t.out(n, 'Count'))
        total = hits[k][1] if total is None else t.imath('ADD', total, hits[k][1])
    active = t.bool('AND', damage.gt(1e-4), t.compare('GREATER_THAN', total, 0, 'INT'))

    def per_hit(g, steps):
        for k in KINDS:
            pts, cnt = hits[k]
            rin, rout, cur = _repeat(t, cnt, [("Geometry", 'GEOMETRY', g)])
            ins = dict(step_ins, Geometry=cur["Geometry"], Hits=pts, Index=F(t, rin.outputs['Iteration']))
            g = _end_repeat(t, rout, [("Geometry", t.out(t.group(steps[k], ins)))])["Geometry"]
        return g

    # teeth are knocked out / tilted before anything else
    is_teeth = t.compare('EQUAL', layer, LAYER_TEETH, 'INT')
    tn = t.group(teeth_g, {"Geometry": geo_in, "Blunt": hits["blunt"][0], "Count": hits["blunt"][1],
                           "Damage": damage, "Tooth Root": t.inp("Tooth Root"),
                           "Bullet": hits["bullet"][0], "Bullet Count": hits["bullet"][1],
                           "Blast": hits["blast"][0], "Blast Count": hits["blast"][1]})
    g = t.switch(is_teeth, geo_in, t.out(tn), 'GEOMETRY')
    # 1. refine where wounds need resolution
    g = t.store(g, "g_n", t.normal(), 'FLOAT_VECTOR')
    g = per_hit(t.store(g, "g_reg", 0.0), region_steps)
    is_vp = t.out(t.node('GeometryNodeIsViewport'))
    detail = t.switch(is_vp, t.inp("Detail"), t.inp("Detail").min(t.inp("Viewport Detail")), 'INT')
    g = t.out(t.group(refine_g, {"Geometry": g, "Detail": detail, "Layer": layer}))
    # 2. wound fields, hit by hit
    g = t.store(g, "g_cut", -1.0)
    g = t.store(g, "g_floor", 0.0)
    g = t.store(g, "g_fill", 0.0)
    g = t.store(g, "g_clot", 0.0)
    g = t.store(g, "g_mush", 0.0)
    g = t.store(g, "g_mushk", 0.0)
    g = t.store(g, "g_wb", 0.0)
    g = t.store(g, "g_strand", 0.0)
    g = t.store(g, "g_vshape", 0.0)
    for name in ("g_disp", "g_wall", "g_ctr", "g_a", "g_b"):
        g = t.store(g, name, (0.0, 0.0, 0.0), 'FLOAT_VECTOR')
    g = per_hit(g, wound_steps)
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Exact', 'Name': "g_reg"}))
    g = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': g, 'Pattern Mode': 'Exact', 'Name': "g_n"}))
    # 3. holes and walls
    g = t.out(t.group(cut_g, {"Geometry": g, "Layer": layer, "Wall Material": t.inp("Wall Material"),
                              "Blood Material": t.inp("Blood Material"),
                              "Strand Material": t.inp("Strand Material"), "Drip Time": t.inp("Drip Time"),
                              "Pulp Material": t.inp("Pulp Material")}))
    # 4. extra geometry: blood on the skin, bone chips on skull and jaw
    is_skin = t.compare('EQUAL', layer, LAYER_SKIN, 'INT')
    is_bone = t.bool('OR', t.compare('EQUAL', layer, LAYER_SKULL, 'INT'), t.compare('EQUAL', layer, LAYER_JAW, 'INT'))
    empty = t.out(t.node('GeometryNodeJoinGeometry'))
    # drips only need the skin near the wounds: crop it so the
    # surface lookups build small search trees
    all_hits = _join(t, *(hits[k][0] for k in KINDS))
    # (runs reach from the scalp to the cut of the neck: ~0.34 m)
    near_hits = t.out(t.node('GeometryNodeProximity', {'Target': all_hits}, target_element='POINTS'), 'Distance').lt(0.36)
    crop = t.out(t.node('GeometryNodeSeparateGeometry', {'Geometry': g, 'Selection': near_hits}, domain='FACE'))
    vessels = t.out(t.node('GeometryNodeObjectInfo', {'Object': t.inp("Vessels")}, transform_space='RELATIVE'),
                    'Geometry')
    bn = t.group(blood_g, {"Surface": crop, "Rest": geo_in, "Bullet": hits["bullet"][0], "Exit": hits["exit"][0],
                           "Slash": hits["slash"][0], "Blunt": hits["blunt"][0], "Blast": hits["blast"][0],
                           "Vessels": vessels, "Damage": damage,
                           "Bleed": bleed, "Drip Time": t.inp("Drip Time"), "Material": t.inp("Blood Material")})
    trail = t.out(bn, 'Trail')
    prox = t.node('GeometryNodeProximity', {'Target': trail}, target_element='EDGES')
    # the stain a run leaves behind it is as wide as the run itself (the
    # width of the nearest trail point), a thin translucent film that is only
    # where the blood actually travelled
    # (an empty trail reports distance 0 everywhere, hence Is Valid)
    ni = t.out(t.node('GeometryNodeSampleNearest', {'Geometry': trail, 'Sample Position': t.pos()}, domain='POINT'))
    dw_n = t.sample(trail, t.attr("d_rad"), ni).max(0.0005)
    # the thin translucent smear the blood leaves around and behind a run
    # (where the stream wandered, spread and drained), ~2-3x the run's width,
    # uneven and broken up at its margin; under the run itself the skin is wet
    pn = t.pos()
    dprox = t.out(prox, 'Distance') + t.noise(pn * 900.0) * dw_n * 0.45 + t.noise(pn * 140.0) * dw_n * 1.1
    smear = t.smooth(dw_n * (2.2 + 1.2 * t.noise(pn * 60.0, signed=False)), dw_n * 0.9, dprox)
    trail_cov = (smear * (0.16 + 0.12 * t.noise(pn * 220.0, signed=False)) + t.smooth(dw_n * 1.2, dw_n * 0.7, dprox) * 0.3) \
        * t.out(prox, 'Is Valid') * bleed.gt(0.02)
    a = t.attr("g_a", 'FLOAT_VECTOR')
    g_sk = t.store(g, "g_a", t.vec(a.x, a.y, a.z.max(trail_cov)), 'FLOAT_VECTOR', sel=near_hits)
    g = t.switch(is_skin, g, g_sk, 'GEOMETRY')
    fn = t.group(frag_g, {"Exit": hits["exit"][0], "Blunt": hits["blunt"][0], "Bullet": hits["bullet"][0],
                          "Blast": hits["blast"][0], "Damage": damage,
                          "Is Jaw": t.switch(t.compare('EQUAL', layer, LAYER_JAW, 'INT'), 0.0, 1.0),
                          "Material": t.inp("Bone Material")})
    g = _join(t, g, t.switch(is_bone, empty, t.out(fn), 'GEOMETRY'))
    # 5. contract attributes
    g = t.out(t.group(attr_g, {"Geometry": g, "Layer": layer}))
    blood_geo = t.switch(is_skin, empty, t.out(bn, 'Blood'), 'GEOMETRY')
    for pattern in ("d_*", "hit_*"):
        blood_geo = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': blood_geo, 'Pattern Mode': 'Wildcard',
                                                                 'Name': pattern}))
    for name in ATTRS:
        blood_geo = t.store(blood_geo, name, 1.0 if name == "gore_blood" else 0.0)
    g = _join(t, g, blood_geo)
    # 6. intact path: damage 0 or no hits -> input geometry, zeroed attributes
    intact = geo_in
    for name in ATTRS:
        intact = t.store(intact, name, 0.0)
    t.result("Geometry", t.switch(active, intact, g, 'GEOMETRY'))
    t.layout()
    return t.ng


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def ensure_hit_collections():
    """Create GH_Hits and its five per-kind child collections. Returns {kind: collection}."""
    root = ghc.get_collection(HITS_ROOT)
    return {k: ghc.get_collection(HIT_COLLECTIONS[k], root) for k in KINDS}


# outer surfaces a hit can land on (a shot into the eye or the open mouth)
SURFACE_OBJECTS = ("GH_Skin", "GH_Eye_L", "GH_Eye_R", "GH_Teeth_Upper", "GH_Teeth_Lower", "GH_Gums",
                   "GH_Tongue", "GH_MouthCavity")
_BVH_CACHE = {}


def _surface_bvh():
    """World-space BVH of the outer surfaces, built from the base meshes.

    GH_Gore is the only modifier on these objects, so the undeformed mesh
    data is the surface the wounds are placed on (existing holes never
    swallow a ray). Cached per mesh / vertex count / transform, so placing
    many hits costs one BVH build."""
    import numpy as np
    from mathutils.bvhtree import BVHTree
    obs = [bpy.data.objects.get(n) for n in SURFACE_OBJECTS]
    obs = [o for o in obs if o is not None and o.type == 'MESH']
    if not obs:
        return None
    key = tuple((o.data.as_pointer(), len(o.data.vertices), tuple(round(x, 6) for row in o.matrix_world for x in row))
                for o in obs)
    if _BVH_CACHE.get("key") == key:
        return _BVH_CACHE["bvh"]
    verts, polys = [], []
    for o in obs:
        me = o.data
        co = np.empty(len(me.vertices) * 3)
        me.vertices.foreach_get("co", co)
        mw = np.array(o.matrix_world)
        co = co.reshape(-1, 3) @ mw[:3, :3].T + mw[:3, 3]
        base = len(verts)
        verts.extend(map(Vector, co))
        polys.extend([base + i for i in p.vertices] for p in me.polygons)
    bvh = BVHTree.FromPolygons(verts, polys)
    _BVH_CACHE.clear()
    _BVH_CACHE.update(key=key, bvh=bvh)
    return bvh


def _first_front_hit(bvh, origin, d, length):
    """First surface along the ray that faces the ray (skips inside-facing hits)."""
    o = origin.copy()
    travelled = 0.0
    for _ in range(8):
        co, nrm, _i, dist = bvh.ray_cast(o, d, length - travelled)
        if co is None:
            return None
        travelled += dist
        if nrm.dot(d) < 0.0:
            return co, nrm, travelled
        o = co + d * 1e-5
    return None


def _snap(bvh, loc, d, radius=0.0045):
    """Impact point of a projectile of `radius` travelling along d toward loc.

    Casts the axis and a ring of rays offset by the radius from well outside
    the head; the nearest surface any of them meets (facing the shot) is the
    impact, projected back onto the axis. So a shot into the open mouth hits
    the lips and teeth instead of passing through the 7 mm gap."""
    start = loc - d * 0.25
    side = d.orthogonal().normalized()
    up = d.cross(side).normalized()
    best = None
    offsets = [Vector((0.0, 0.0, 0.0))] + [(side * math.cos(a) + up * math.sin(a)) * radius
                                            for a in (i * TAU / 6.0 for i in range(6))]
    for k, off in enumerate(offsets):
        h = _first_front_hit(bvh, start + off, d, 0.5)
        if h is None:
            continue
        # (the axis ray wins ties within 0.5 mm: it is where the bullet centre goes)
        dist = h[2] + (0.0 if k == 0 else 0.0005)
        if best is None or dist < best[2] - 1e-6:
            best = (h[0] - off, h[1], dist, k)
    return best


def add_hit(kind, location, direction=None, size=1.0, elongation=1.0, depth=0.6, name=None, roll=0.0,
            muzzle_distance=None):
    """Place a wound: an empty in GH_Hits_<Kind>, snapped onto the outer surface.

    kind: bullet | exit | slash | blunt | burn | blast.
    location: impact point (anywhere near the surface).
    direction: direction the damage travels into the head. None = straight in
        along the surface normal. For exits pass the bullet's travel direction
        or the inward direction; it is flipped so local -Z always points into
        the head. With a direction the hit lands on the first surface facing
        the shot along that line (a ring of rays the width of a bullet, so a
        shot into the open mouth hits lips and teeth).
    size, elongation, depth: stored as scale x, y, z (see CONTRACT.md).
    roll: extra rotation (radians) around the hit axis; turns a slash.
    muzzle_distance: bullets only, metres from the muzzle to the skin (stored
        as scale.y; default 1 m = no soot or stippling; < 0.3 m soot,
        < 0.9 m stippling, ~0 contact).
    The empty's local X is horizontal by default (slash direction).
    """
    kind = kind.lower()
    if kind not in KINDS:
        raise ValueError(f"unknown hit kind {kind!r}, expected one of {KINDS}")
    cols = ensure_hit_collections()
    loc = Vector(location)
    d = Vector(direction).normalized() if direction is not None else None
    bvh = _surface_bvh()
    if bvh is not None:
        hit = None
        if d is not None:
            # exits are given along the bullet's travel: find the surface on
            # the way out as well as on the way in, keep the nearer one
            cands = [c for c in (_snap(bvh, loc, d), _snap(bvh, loc, -d)) if c is not None]
            if cands:
                cands.sort(key=lambda c: (c[0] - loc).length)
                co, nrm, _dist, _k = cands[0]
                hit = (co, nrm)
        if hit is None:
            co, nrm, _i, _dist = bvh.find_nearest(loc)
            if co is not None:
                hit = (co, nrm)
        if hit is not None:
            loc = hit[0].copy()
            n_out = hit[1].normalized()
            if d is None:
                d = -n_out
            elif d.dot(n_out) > 0.0:
                d = -d
    if d is None:
        d = (-loc).normalized() if loc.length > 1e-6 else Vector((0.0, 0.0, -1.0))
    quat = (-d).to_track_quat('Z', 'Y')      # local +Z out of the head, local X horizontal
    if roll:
        from mathutils import Quaternion
        quat = quat @ Quaternion((0.0, 0.0, 1.0), roll)
    if kind == "bullet":
        elongation = max(0.005, muzzle_distance if muzzle_distance is not None else 1.0)
    empty = bpy.data.objects.new(name or f"GH_Hit_{kind.capitalize()}", None)
    empty.empty_display_type = 'ARROWS' if kind == "slash" else 'SINGLE_ARROW'
    empty.empty_display_size = 0.015
    empty.location = loc
    empty.rotation_euler = quat.to_euler()
    empty.scale = (size, elongation, depth)
    cols[kind].objects.link(empty)
    return empty


def add_hits(hits):
    """Place several hits at once: [(kind, location, {add_hit keyword args}), ...]. Returns the empties."""
    return [add_hit(kind, loc, **dict(kw or {})) for kind, loc, kw in hits]


def clear_hits():
    """Delete every hit empty in the GH_Hits_* collections."""
    for k in KINDS:
        col = bpy.data.collections.get(HIT_COLLECTIONS[k])
        if col is None:
            continue
        for ob in list(col.objects):
            bpy.data.objects.remove(ob, do_unlink=True)


def _standin_material(name, color, rough=0.5):
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
        if mat.node_tree is None:        # (5.x materials always have one)
            mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (*color, 1.0)
            bsdf.inputs["Roughness"].default_value = rough
        mat.diffuse_color = (*color, 1.0)
        mat["gh_gore_standin"] = True
    return mat


def _object_material(ob):
    if ob is not None and ob.type == 'MESH' and len(ob.data.materials) and ob.data.materials[0]:
        return ob.data.materials[0]
    return None


def _wall_materials(mats):
    """Wall / blood / bone materials per layer. Uses materials.py's if present."""
    mats = dict(mats or {})
    get = lambda n: mats.get(n) or bpy.data.materials.get(n)  # noqa: E731
    fat = get("GH_Fat") or _standin_material("GH_Fat", (0.78, 0.62, 0.30), 0.35)
    muscle = get("GH_Muscle") or _standin_material("GH_Muscle", (0.30, 0.03, 0.03), 0.4)
    bone = get("GH_Bone") or _standin_material("GH_Bone", (0.78, 0.72, 0.60), 0.55)
    blood = get("GH_Blood") or _standin_material("GH_Blood", (0.18, 0.005, 0.005), 0.1)
    walls = {
        LAYER_SKIN: fat, LAYER_MUSCLE: muscle, LAYER_SKULL: bone, LAYER_JAW: bone,
        LAYER_EYE: blood, LAYER_GUMS: get("GH_Gums") or muscle,
    }
    return walls, blood, bone


BONE_DEPTH_LAYERS = ("GH_Skin", "GH_Muscle", "GH_MouthCavity")


def bake_bone_depth(objs):
    """Store `gh_bone_depth` on the soft-tissue layers: the distance from each
    vertex straight in (along -normal) to the skull or jaw, in metres.

    Wound walls use it to reach exactly down to the bone (no gap between the
    layers, no wall poking through the bone). Computed from the base meshes,
    so it is static anatomy data. Vertices with no bone within 30 mm (the
    neck) get 12 mm.
    """
    import numpy as np
    from mathutils.bvhtree import BVHTree
    def tree(names):
        obs = [objs.get(n) or bpy.data.objects.get(n) for n in names]
        obs = [b for b in obs if b is not None and b.type == 'MESH']
        if not obs:
            return None
        verts, polys = [], []
        for b in obs:
            me = b.data
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            co = co.reshape(-1, 3) @ np.array(b.matrix_world.to_3x3()).T + np.array(b.matrix_world.translation)
            base = len(verts)
            verts.extend(map(Vector, co))
            polys.extend([base + i for i in p.vertices] for p in me.polygons)
        return BVHTree.FromPolygons(verts, polys)
    bone_tree = tree(("GH_Skull", "GH_Jaw"))
    if bone_tree is None:
        return
    # over the mouth the skin's walls must stop at the mouth lining (the cheek
    # and lips are only 10-15 mm thick; a cut must not show the teeth through
    # its wall)
    soft_tree = tree(("GH_Skull", "GH_Jaw", "GH_MouthCavity"))
    for name in BONE_DEPTH_LAYERS:
        ob = objs.get(name) or bpy.data.objects.get(name)
        if ob is None or ob.type != 'MESH':
            continue
        bvh = soft_tree if name in ("GH_Skin", "GH_Muscle") and soft_tree is not None else bone_tree
        me = ob.data
        n = len(me.vertices)
        co = np.empty(n * 3)
        me.vertices.foreach_get("co", co)
        nr = np.empty(n * 3)
        me.vertices.foreach_get("normal", nr)
        co, nr = co.reshape(-1, 3), nr.reshape(-1, 3)
        depth = np.full(n, 0.012, np.float32)
        ray = bvh.ray_cast
        for i in range(n):
            loc, _nrm, _idx, dist = ray(Vector(co[i]), Vector(-nr[i]), 0.03)
            if loc is not None:
                depth[i] = dist
        att = me.attributes.get("gh_bone_depth") or me.attributes.new("gh_bone_depth", 'FLOAT', 'POINT')
        att.data.foreach_set("value", depth)


def build_gore_system(objs=None, mats=None):
    """Add the live GH_Gore modifier to every damageable layer.

    objs: dict name -> object (as returned by anatomy.build_anatomy()); missing
          entries are looked up by name.
    mats: optional dict of materials (materials.build_materials()).
    Returns {"node_group", "modifiers": {name: modifier}, "collections", "controls"}.
    """
    objs = dict(objs or {})
    for name in LAYERS:
        if objs.get(name) is None and bpy.data.objects.get(name) is not None:
            objs[name] = bpy.data.objects[name]
    cols = ensure_hit_collections()
    ctrl = ghc.ensure_controls()
    t0 = time.time()
    vessels = build_vessels()
    print(f"[gore] head vessel table snapped in {time.time() - t0:.1f} s")
    t0 = time.time()
    bake_bone_depth(objs)
    print(f"[gore] bone depth baked in {time.time() - t0:.1f} s")
    ng = bpy.data.node_groups.get(GROUP_NAME)
    if ng is None or ng.get("gh_gore_version") != _GROUP_VERSION:
        ng = build_gore_node_group()
        ng["gh_gore_version"] = _GROUP_VERSION
    ident = {it.name: it.identifier for it in ng.interface.items_tree
             if it.item_type == 'SOCKET' and it.in_out == 'INPUT'}
    walls, blood, bone = _wall_materials(mats)
    strand = (mats or {}).get("GH_Muscle") or bpy.data.materials.get("GH_Muscle") or walls[LAYER_MUSCLE]
    pulp = (mats or {}).get("GH_Brain") or bpy.data.materials.get("GH_Brain") or strand
    mods = {}
    for name, layer in LAYERS.items():
        ob = objs.get(name)
        if ob is None or ob.type != 'MESH':
            continue
        mod = ob.modifiers.get(MOD_NAME)
        if mod is None:
            mod = ob.modifiers.new(MOD_NAME, 'NODES')
        mod.node_group = ng
        # the gore modifier must see the final anatomy: keep it last
        idx = list(ob.modifiers).index(mod)
        if idx != len(ob.modifiers) - 1:
            ob.modifiers.move(idx, len(ob.modifiers) - 1)
        mod[ident["Layer"]] = layer
        for k in KINDS:
            mod[ident[f"{k.capitalize()} Hits"]] = cols[k]
        if name in OWN_WALL_MATERIAL:
            wall = _object_material(ob) or walls.get(layer) or bone
        else:
            wall = walls.get(layer) or _object_material(ob) or bone
        mod[ident["Wall Material"]] = wall
        mod[ident["Blood Material"]] = blood
        mod[ident["Bone Material"]] = bone
        mod[ident["Strand Material"]] = strand
        mod[ident["Pulp Material"]] = pulp
        mod[ident["Tooth Root"]] = -1.0 if name.endswith("Lower") else 1.0
        mod[ident["Vessels"]] = vessels
        # (a rebuilt group renumbers its sockets: drop drivers of the old ones)
        if ob.animation_data is not None:
            for fc in list(ob.animation_data.drivers):
                if fc.data_path.startswith(f'modifiers["{MOD_NAME}"]'):
                    ob.animation_data.drivers.remove(fc)
        # drivers from the global controls
        for prop, sock in (("damage", "Damage"), ("bleed", "Bleed"), ("drip_time", "Drip Time"),
                           ("bruising", "Bruising"), ("swelling", "Swelling"), ("wound_age", "Wound Age")):
            ghc.drive(ob, f'modifiers["{MOD_NAME}"]["{ident[sock]}"]', prop)
        mods[name] = mod
    return {"node_group": ng, "modifiers": mods, "collections": cols, "controls": ctrl}


_GROUP_VERSION = 10


# ---------------------------------------------------------------------------
# Test harness: placeholder anatomy, preview shading, renders, verification
# ---------------------------------------------------------------------------
def _quad_sphere(name, radii, center, n=90, shape=None, flip=False):
    """Uniform quad sphere mapped onto an ellipsoid; `shape(p, dir)` may displace."""
    import bmesh
    from mathutils import noise  # noqa: F401  (used by shape callbacks)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=2.0)
    bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=n - 1, use_grid_fill=True)
    for v in bm.verts:
        d = v.co.normalized()
        p = Vector((d.x * radii[0], d.y * radii[1], d.z * radii[2])) + Vector(center)
        if shape is not None:
            p = shape(p, d)
        v.co = p
    if flip:
        for f in bm.faces:
            f.normal_flip()
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    ghc.get_collection("GoreHead").objects.link(ob)
    return ob


def _placeholder_anatomy():
    """Crude but dense stand-in layers so the gore system can be developed alone."""
    from mathutils import noise
    import bmesh
    c = (0.0, 0.004, 0.012)
    R = (0.074, 0.098, 0.113)

    def head(off):
        def shape(p, d):
            # nose ridge and brow so the front is not a perfect ellipsoid
            nose = math.exp(-((p.x / 0.011) ** 2 + ((p.z + 0.008) / 0.022) ** 2)) * max(-d.y, 0.0)
            return p + Vector((0.0, -0.018 * nose, 0.0)) - d * off
        return shape
    objs = {}
    objs["GH_Skin"] = _quad_sphere("GH_Skin", R, c, 100, head(0.0))
    objs["GH_Muscle"] = _quad_sphere("GH_Muscle", R, c, 80, head(0.0042))
    outer = _quad_sphere("GH_Skull", R, c, 80, head(0.0085))
    inner = _quad_sphere("GH_Skull_in", R, c, 64, head(0.0152), flip=True)
    # join inner table into the skull
    bm = bmesh.new()
    bm.from_mesh(outer.data)
    bm.from_mesh(inner.data)
    bm.to_mesh(outer.data)
    bm.free()
    bpy.data.objects.remove(inner)
    objs["GH_Skull"] = outer

    def brain(p, d):
        gy = noise.noise(p * 260.0) + 0.5 * noise.noise(p * 520.0)
        fiss = math.exp(-(p.x / 0.004) ** 2) * max(d.z, 0.0)
        return p - d * (0.019 + 0.0022 * abs(gy) + 0.008 * fiss)
    objs["GH_Brain"] = _quad_sphere("GH_Brain", R, c, 110, brain)
    for side, sx in (("L", 1.0), ("R", -1.0)):
        objs[f"GH_Eye_{side}"] = _quad_sphere(f"GH_Eye_{side}", (0.012,) * 3, (0.032 * sx, -0.07, 0.022), 16)
    # teeth: a row of small rounded blocks on an arc, gums as a bar
    for row, z0, root in (("Upper", -0.047, 1.0), ("Lower", -0.061, -1.0)):
        bm = bmesh.new()
        for i in range(14):
            a = math.radians(-78 + 12 * i)
            cx, cy = 0.026 * math.sin(a), -0.052 - 0.026 * math.cos(a) + 0.0
            m = bmesh.ops.create_cube(bm, size=1.0)
            for v in m["verts"]:
                v.co = Vector((v.co.x * 0.006, v.co.y * 0.005, v.co.z * 0.010))
                v.co.rotate(__import__("mathutils").Euler((0, 0, a)))
                v.co += Vector((cx, cy, z0 + root * 0.004))
        bmesh.ops.subdivide_edges(bm, edges=bm.edges[:], cuts=3, use_grid_fill=True)
        me = bpy.data.meshes.new(f"GH_Teeth_{row}")
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new(f"GH_Teeth_{row}", me)
        ghc.get_collection("GoreHead").objects.link(ob)
        objs[f"GH_Teeth_{row}"] = ob
    return objs


class _Shader:
    """Minimal helper for the preview shaders (only used without materials.py)."""

    def __init__(self, mat):
        if mat.node_tree is None:
            mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')
        self.bsdf = self.nt.nodes.new('ShaderNodeBsdfPrincipled')
        self.nt.links.new(self.bsdf.outputs[0], self.out.inputs[0])

    def _set(self, sock, val):
        if isinstance(val, bpy.types.NodeSocket):
            self.nt.links.new(val, sock)
        elif isinstance(val, (tuple, list)) and len(val) == 3 and sock.type == 'RGBA':
            sock.default_value = (*val, 1.0)
        elif isinstance(val, (int, float)) and sock.type == 'RGBA':
            sock.default_value = (val, val, val, 1.0)
        else:
            sock.default_value = val

    def attr(self, name):
        a = self.nt.nodes.new('ShaderNodeAttribute')
        a.attribute_name = name
        return a.outputs['Fac']

    def noise(self, scale, detail=4.0, vec=None):
        n = self.nt.nodes.new('ShaderNodeTexNoise')
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        if vec is not None:
            self.nt.links.new(vec, n.inputs['Vector'])
        return n.outputs['Fac']

    def mix(self, fac, a, b, blend='MIX'):
        m = self.nt.nodes.new('ShaderNodeMix')
        m.data_type = 'RGBA'
        m.blend_type = blend
        self._set(m.inputs['Factor'], fac)
        self._set(m.inputs['A'], a)
        self._set(m.inputs['B'], b)
        return m.outputs['Result']

    def ramp(self, fac, stops):
        r = self.nt.nodes.new('ShaderNodeValToRGB')
        self._set(r.inputs[0], fac)
        el = r.color_ramp.elements
        while len(el) < len(stops):
            el.new(0.5)
        for e, (p, col) in zip(el, stops):
            e.position = p
            e.color = (*col, 1.0) if len(col) == 3 else col
        return r.outputs[0]

    def fac(self, x, a, b, c=0.0, d=1.0):
        r = self.nt.nodes.new('ShaderNodeMapRange')
        self._set(r.inputs['Value'], x)
        r.inputs['From Min'].default_value = a
        r.inputs['From Max'].default_value = b
        r.inputs['To Min'].default_value = c
        r.inputs['To Max'].default_value = d
        return r.outputs[0]

    def bump(self, height, strength=0.3, dist=0.001):
        b = self.nt.nodes.new('ShaderNodeBump')
        b.inputs['Strength'].default_value = strength
        b.inputs['Distance'].default_value = dist
        self._set(b.inputs['Height'], height)
        self.nt.links.new(b.outputs[0], self.bsdf.inputs['Normal'])


def _preview_material(name, kind):
    """Attribute-driven stand-in shading, used only when materials.py is missing."""
    mat = bpy.data.materials.get(name) or bpy.data.materials.new(name)
    sh = _Shader(mat)
    b = sh.bsdf
    blood_col = (0.06, 0.003, 0.002)
    if kind == "blood":
        sh._set(b.inputs['Base Color'], sh.mix(sh.noise(400.0), (0.075, 0.003, 0.002), (0.045, 0.002, 0.001)))
        b.inputs['Roughness'].default_value = 0.07
        b.inputs['Coat Weight'].default_value = 0.8
        b.inputs['Coat Roughness'].default_value = 0.03
        b.inputs['Subsurface Weight'].default_value = 0.3
        b.inputs['Subsurface Radius'].default_value = (1.0, 0.1, 0.05)
        b.inputs['Subsurface Scale'].default_value = 0.001
        return mat
    if kind == "fat":
        fat = sh.ramp(sh.noise(1500.0, 3.0), [(0.35, (0.62, 0.42, 0.14)), (0.6, (0.45, 0.17, 0.07))])
        blood_f = sh.fac(sh.attr("gore_blood"), 0.05, 0.75)
        sh._set(b.inputs['Base Color'], sh.mix(blood_f, fat, blood_col))
        b.inputs['Roughness'].default_value = 0.5
        sh.bump(sh.noise(1500.0, 3.0), 0.4, 0.0004)
        return mat
    base = {"skin": ((0.30, 0.18, 0.13), (0.25, 0.145, 0.105)), "muscle": ((0.24, 0.025, 0.02), (0.14, 0.01, 0.01)),
            "bone": ((0.74, 0.68, 0.56), (0.62, 0.55, 0.42)), "brain": ((0.58, 0.40, 0.40), (0.45, 0.28, 0.30)),
            "eye": ((0.80, 0.78, 0.74), (0.7, 0.6, 0.58)), "teeth": ((0.82, 0.78, 0.66), (0.7, 0.64, 0.5))}[kind]
    col = sh.mix(sh.noise(250.0), *base)
    if kind == "eye":
        # iris and pupil around the local -Y axis
        tc = sh.nt.nodes.new('ShaderNodeTexCoord')
        nrm = sh.nt.nodes.new('ShaderNodeVectorMath')
        nrm.operation = 'NORMALIZE'
        sh.nt.links.new(tc.outputs['Object'], nrm.inputs[0])
        dot = sh.nt.nodes.new('ShaderNodeVectorMath')
        dot.operation = 'DOT_PRODUCT'
        sh.nt.links.new(nrm.outputs[0], dot.inputs[0])
        dot.inputs[1].default_value = (0.0, -1.0, 0.0)
        iris = sh.ramp(dot.outputs['Value'], [(0.0, (0.0, 0.0, 0.0)), (0.905, (0.0, 0.0, 0.0)),
                                              (0.915, (1.0, 1.0, 1.0)), (1.0, (1.0, 1.0, 1.0))])
        pupil = sh.ramp(dot.outputs['Value'], [(0.972, (0.0, 0.0, 0.0)), (0.978, (1.0, 1.0, 1.0))])
        col = sh.mix(iris, col, sh.mix(sh.noise(600.0), (0.20, 0.13, 0.06), (0.10, 0.07, 0.03)))
        col = sh.mix(pupil, col, (0.005, 0.005, 0.005))
        b.inputs['Coat Weight'].default_value = 1.0
        b.inputs['Coat Roughness'].default_value = 0.02
    rough = sh.mix(sh.fac(sh.attr("gore_burn"), 0.4, 0.8), sh.fac(sh.attr("gore_wound"), 0.0, 1.0, 0.5, 0.3), 0.85)
    if kind == "skin":
        tissue = sh.ramp(sh.attr("gore_depth"), [(0.0, (0.40, 0.07, 0.05)), (0.14, (0.48, 0.12, 0.08)),
                                                 (0.24, (0.78, 0.56, 0.22)), (0.46, (0.70, 0.46, 0.18)),
                                                 (0.58, (0.22, 0.02, 0.02)), (1.0, (0.16, 0.01, 0.01))])
        col = sh.mix(sh.attr("gore_wound"), col, tissue)
        col = sh.mix(sh.fac(sh.attr("gore_edge"), 0.0, 1.0, 0.0, 0.85), col, (0.24, 0.07, 0.045))
        bruise = sh.ramp(sh.noise(90.0, 3.0), [(0.3, (0.05, 0.012, 0.06)), (0.7, (0.14, 0.02, 0.05))])
        col = sh.mix(sh.fac(sh.attr("gore_bruise"), 0.0, 0.6, 0.0, 0.95), col, bruise)
        char = sh.ramp(sh.attr("gore_burn"), [(0.0, (0.5, 0.14, 0.09)), (0.35, (0.42, 0.10, 0.06)),
                                              (0.55, (0.12, 0.05, 0.03)), (0.75, (0.02, 0.016, 0.013))])
        col = sh.mix(sh.fac(sh.attr("gore_burn"), 0.0, 0.25), col, char)
        sh._set(b.inputs['Subsurface Weight'], 0.3)
        sh._set(b.inputs['Specular IOR Level'], sh.fac(sh.attr("gore_burn"), 0.5, 0.9, 0.5, 0.08))
        b.inputs['Subsurface Radius'].default_value = (1.0, 0.35, 0.2)
        b.inputs['Subsurface Scale'].default_value = 0.003
        sh.bump(sh.noise(2500.0, 2.0), 0.15, 0.0003)
    elif kind in ("bone", "teeth"):
        col = sh.mix(sh.attr("gore_fracture"), col, (0.05, 0.02, 0.015))
    else:
        col = sh.mix(sh.attr("gore_wound"), col, (0.20, 0.02, 0.02))
    blood_f = sh.fac(sh.attr("gore_blood"), 0.05, 0.75)
    col = sh.mix(blood_f, col, blood_col)
    sh._set(b.inputs['Base Color'], col)
    sh._set(b.inputs['Roughness'], sh.mix(blood_f, rough, 0.22))
    if kind != "skin":
        sh.bump(sh.noise(900.0, 3.0), 0.25, 0.0005)
    return mat


def _setup_materials(objs):
    """Real materials if materials.py works, otherwise preview materials."""
    try:
        import materials
        mats = materials.build_materials()
        materials.assign_materials(objs, mats)
        print("[gore] using materials.py")
        return mats, True
    except Exception as exc:  # noqa: BLE001  (materials are built in parallel)
        print(f"[gore] materials.py not usable ({exc!r}); using preview materials")
    kinds = {"GH_Skin": "skin", "GH_Muscle": "muscle", "GH_Skull": "bone", "GH_Jaw": "bone",
             "GH_Brain": "brain", "GH_Eye_L": "eye", "GH_Eye_R": "eye", "GH_Teeth_Upper": "teeth",
             "GH_Teeth_Lower": "teeth", "GH_Gums": "muscle", "GH_Tongue": "muscle", "GH_MouthCavity": "muscle"}
    shared = {}
    for name, ob in objs.items():
        if ob is None or ob.type != 'MESH' or name not in kinds:
            continue
        k = kinds[name]
        shared.setdefault(k, _preview_material(f"GHP_{k}", k))
        ob.data.materials.clear()
        ob.data.materials.append(shared[k])
    mats = {"GH_Fat": _preview_material("GH_Fat", "fat"), "GH_Blood": _preview_material("GH_Blood", "blood"),
            "GH_Muscle": shared.get("muscle") or _preview_material("GHP_muscle", "muscle"),
            "GH_Bone": shared.get("bone") or _preview_material("GHP_bone", "bone")}
    return mats, False


def _load_anatomy():
    """Real anatomy if anatomy.py is present, otherwise the placeholder layers.

    Only a missing anatomy module falls back to the placeholders; an error
    inside anatomy.build_anatomy() is a real regression and is raised."""
    try:
        import anatomy
    except ImportError:
        import traceback
        traceback.print_exc()
        print("[gore] anatomy.py not importable; using placeholder layers")
        return _placeholder_anatomy(), False
    objs = anatomy.build_anatomy()
    if objs and objs.get("GH_Skin") is not None:
        print("[gore] using anatomy.py")
        return objs, True
    raise RuntimeError("anatomy.build_anatomy() returned no GH_Skin")


def _closeup(name, hit, dist=0.12, lens=85.0, offset=(0.0, 0.0, 0.0), up_tilt=0.25):
    """Camera looking at a hit from outside along its normal, slightly from above."""
    loc = hit.location.copy()
    z = hit.matrix_world.to_3x3() @ Vector((0.0, 0.0, 1.0))
    z.normalize()
    view = (z + Vector((0.0, 0.0, up_tilt))).normalized()
    target = loc + Vector(offset)
    return ghc.add_camera(name, target + view * dist, target, lens)


# Test scenes: hits and a close-up framing (distance, upward tilt, target offset).
TEST_SCENES = {
    "bullet": dict(hits=[("bullet", (0.014, -0.1, 0.07), dict(depth=1.0))],
                   dist=0.085, tilt=0.12, offset=(0.0, 0.0, -0.012)),
    "exit": dict(hits=[("exit", (0.035, 0.088, 0.05), dict(depth=1.0, size=1.1))],
                 dist=0.13, tilt=0.15, offset=(0.0, 0.0, -0.01)),
    "slash": dict(hits=[("slash", (-0.058, -0.062, -0.005), dict(depth=0.6, elongation=2.2, roll=0.35))],
                  dist=0.13, tilt=0.05, offset=(0.0, 0.0, -0.01)),
    "blunt": dict(hits=[("blunt", (0.058, -0.058, 0.055), dict(depth=0.9)),
                        ("blunt", (0.012, -0.1, -0.05), dict(depth=0.6, size=0.9))],
                  dist=0.12, tilt=0.1, offset=(0.0, 0.0, -0.006)),
    "burn": dict(hits=[("burn", (-0.062, -0.04, 0.058), dict(depth=0.5, elongation=1.25))],
                 dist=0.13, tilt=0.08, offset=(0.0, 0.0, 0.0)),
    # explosive / contact blast in the open mouth (REFERENCE_NOTES §5.11)
    "blast": dict(hits=[("blast", (0.0, -0.12, -0.056), dict(direction=(0.0, 1.0, 0.0), size=1.5, depth=1.0))],
                  dist=0.24, tilt=0.05, offset=(0.0, 0.0, -0.01)),
}


def place_test_hits(kinds=KINDS):
    """Clear the hits and place the TEST_SCENES hits of the given kinds. Returns the empties."""
    clear_hits()
    placed = []
    for kind in kinds:
        for hk, loc, kw in TEST_SCENES[kind]["hits"]:
            placed.append(add_hit(hk, loc, name=f"GH_Hit_{hk.capitalize()}_{len(placed)}", **kw))
    return placed


def _test_renders(out_dir=None, samples=32, res=(640, 640), kinds=KINDS, all_view=True):
    """Close-up render per wound kind plus an overview with every wound."""
    out_dir = out_dir or ghc.RENDER_DIR
    ghc.setup_stage()
    paths = []
    for kind in kinds:
        sc = TEST_SCENES[kind]
        hit = place_test_hits([kind])[0]
        bpy.context.view_layer.update()
        cam = _closeup(f"GH_Cam_gore_{kind}", hit, sc["dist"], 85.0, sc["offset"], sc["tilt"])
        paths.append(ghc.render(os.path.join(out_dir, f"gore_{kind}.png"), cam, samples, res))
    if all_view:
        paths.append(_render_overview(os.path.join(out_dir, "gore_all.png"), samples, res))
    return paths


def _render_overview(path, samples=32, res=(640, 640)):
    """Every wound at once: front view and back three-quarter view side by side."""
    import numpy as np
    place_test_hits(KINDS)
    w, h = res[0] // 2, res[1]
    views = (("front", (-0.36, -0.66, 0.08), (0.0, -0.03, 0.0)),
             ("left", (0.72, 0.2, 0.1), (0.01, 0.0, 0.0)))
    panels = []
    tmp_dir = os.path.join(os.path.dirname(path), ".gore_tmp")
    for name, loc, tgt in views:
        cam = ghc.add_camera(f"GH_Cam_gore_all_{name}", loc, tgt, 62.0)
        p = ghc.render(os.path.join(tmp_dir, f"{name}.png"), cam, samples, (w, h))
        img = bpy.data.images.load(p)
        panels.append(np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4))
        bpy.data.images.remove(img)
        os.remove(p)
    try:
        os.rmdir(tmp_dir)
    except OSError:
        pass
    out = bpy.data.images.new("gore_all", w * 2, h, alpha=True)
    out.pixels[:] = np.concatenate(panels, axis=1).ravel()
    out.filepath_raw = os.path.abspath(path)
    out.file_format = 'PNG'
    out.save()
    bpy.data.images.remove(out)
    return path


def _mesh_signature(ob):
    """(vertex count, face count, position checksum, blood-material face count) of the evaluated mesh."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = [0.0] * (3 * n)
    me.vertices.foreach_get("co", co)
    chk = round(sum(co[0::3]) * 1.7 + sum(co[1::3]) * 3.1 + sum(co[2::3]) * 5.3, 6)
    blood_idx = [i for i, m in enumerate(me.materials) if m and m.name.startswith("GH_Blood")]
    nb = sum(1 for p in me.polygons if p.material_index in blood_idx)
    sig = (n, len(me.polygons), chk, nb)
    ev.to_mesh_clear()
    return sig


def _evaluate_all(objs):
    """Force a full re-evaluation of every layer; returns seconds."""
    for ob in objs.values():
        if ob is not None:
            ob.update_tag()
    t0 = time.time()
    dg = bpy.context.evaluated_depsgraph_get()
    dg.update()
    for ob in objs.values():
        if ob is not None and ob.type == 'MESH':
            ob.evaluated_get(dg)
    return time.time() - t0


def _set_control(name, value):
    ctrl = ghc.ensure_controls()
    ctrl[name] = value
    ctrl.update_tag()
    bpy.context.evaluated_depsgraph_get().update()


def _wall_fold_stats(ob, wall_mat_prefix="GH_Fat"):
    """Fold statistics of the evaluated wound walls (faces with the wall material).

    Returns (wall edges, edges folded > 60 degrees, fraction). Folded walls
    shade as light/dark stripes (the artefact of refs/12_our_render_wall_stripes).
    """
    import bmesh
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    idx = {i for i, m in enumerate(me.materials) if m and m.name.startswith(wall_mat_prefix)}
    bm = bmesh.new()
    bm.from_mesh(me)
    ev.to_mesh_clear()
    n = folded = 0
    for e in bm.edges:
        lf = e.link_faces
        if len(lf) != 2 or lf[0].material_index not in idx or lf[1].material_index not in idx:
            continue
        n += 1
        if lf[0].normal.angle(lf[1].normal, 0.0) > math.radians(60.0):
            folded += 1
    bm.free()
    return n, folded, folded / max(n, 1)


def _stray_blood(ob, reach=0.004):
    """Skin vertices carrying blood (gore_blood > 0.3) that are farther than
    `reach` from any wound vertex and not part of the blood geometry itself:
    blood that appeared on the skin without a path from a wound."""
    import numpy as np
    from mathutils.kdtree import KDTree
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)

    def att(name):
        a = me.attributes.get(name)
        v = np.zeros(n, np.float32)
        if a is not None and a.domain == 'POINT':
            a.data.foreach_get("value", v)
        return v
    blood, wound, depth = att("gore_blood"), att("gore_wound"), att("gore_depth")
    # vertices of blood-material faces (runs, fills, clots) are the blood itself
    bidx = {i for i, m in enumerate(me.materials) if m and m.name.startswith("GH_Blood")}
    on_blood = np.zeros(n, bool)
    for poly in me.polygons:
        if poly.material_index in bidx:
            on_blood[list(poly.vertices)] = True
    ev.to_mesh_clear()
    src = np.where((wound > 0.3) | (depth > 0.02))[0]
    cand = np.where((blood > 0.3) & ~on_blood & (wound < 0.05) & (depth < 0.01))[0]
    if len(cand) == 0:
        return 0
    if len(src) == 0:
        return len(cand)
    kd = KDTree(len(src))
    for k, i in enumerate(src):
        kd.insert(co[i], k)
    kd.balance()
    return sum(1 for i in cand if kd.find(co[i])[2] > reach)


def verify_gore(objs=None):
    """Self-test of the live gore system. Prints a report, returns True if all checks pass."""
    objs = dict(objs or {})
    objs = {n: objs.get(n) or bpy.data.objects.get(n) for n in LAYERS}
    objs = {k: v for k, v in objs.items() if v is not None and v.type == 'MESH' and v.modifiers.get(MOD_NAME)}
    skin = objs["GH_Skin"]
    ok = True
    lines = []

    def check(name, cond, info=""):
        nonlocal ok
        ok &= bool(cond)
        lines.append(f"  [{'PASS' if cond else 'FAIL'}] {name}{(': ' + info) if info else ''}")

    ctrl = ghc.ensure_controls()
    saved = {k: ctrl[k] for k in DRIVEN_CONTROLS}
    _set_control("damage", 1.0)
    _set_control("drip_time", 1.0)
    hits = place_test_hits(KINDS)
    lines.append(f"gore verification: {len(hits)} hits, layers: {', '.join(objs)}")
    secs = _evaluate_all(objs)
    # (information only: wall-clock time depends on what else shares the CPU,
    # so it never decides pass/fail; the functional checks below do)
    lines.append(f"  [INFO] evaluation time, all layers, {len(hits)} hits: {secs:.2f} s")
    # attributes on every evaluated layer
    dg = bpy.context.evaluated_depsgraph_get()
    missing = []
    for name, ob in objs.items():
        me = ob.evaluated_get(dg).to_mesh()
        have = {a.name for a in me.attributes}
        miss = [a for a in ATTRS if a not in have]
        if miss:
            missing.append(f"{name}:{miss}")
        ob.evaluated_get(dg).to_mesh_clear()
    check("gore_* attributes on all evaluated layers", not missing, ", ".join(missing))
    # wound attributes are actually used on the skin
    me = skin.evaluated_get(dg).to_mesh()
    stats = {}
    for a in ATTRS:
        vals = [0.0] * len(me.vertices)
        me.attributes[a].data.foreach_get("value", vals)
        # (a bruise at the default wound age of ~2 h is still light)
        lim = 0.2 if a == "gore_bruise" else 0.5
        stats[a] = sum(1 for v in vals if v > lim)
    skin.evaluated_get(dg).to_mesh_clear()
    check("skin attributes non-trivial", all(stats[a] > 0 for a in ATTRS if a not in ("gore_fracture", "gore_soot")),
          ", ".join(f"{k[5:]}>{0.5}:{v}" for k, v in stats.items()))
    wounded = {n: _mesh_signature(o) for n, o in objs.items()}
    # damage 0 == no hits
    _set_control("damage", 0.0)
    sig_d0 = {n: _mesh_signature(o) for n, o in objs.items()}
    _set_control("damage", 1.0)
    stash = [(h, list(h.users_collection)) for h in hits]
    for h, cols in stash:
        for c in cols:
            c.objects.unlink(h)
    bpy.context.evaluated_depsgraph_get().update()
    sig_none = {n: _mesh_signature(o) for n, o in objs.items()}
    for h, cols in stash:
        for c in cols:
            c.objects.link(h)
    bpy.context.evaluated_depsgraph_get().update()
    same = all(sig_d0[n][:3] == sig_none[n][:3] for n in objs)
    check("damage=0 identical to no hits", same,
          f"skin {sig_d0['GH_Skin'][:2]} vs {sig_none['GH_Skin'][:2]}; wounded skin {wounded['GH_Skin'][:2]}")
    # moving / rotating / scaling an empty changes the wound live
    b = next(h for h in hits if h.users_collection[0].name == HIT_COLLECTIONS["bullet"])
    before = _mesh_signature(skin)
    b.location.z -= 0.012
    bpy.context.evaluated_depsgraph_get().update()
    moved = _mesh_signature(skin)
    b.location.z += 0.012
    b.scale.x *= 1.8
    bpy.context.evaluated_depsgraph_get().update()
    scaled = _mesh_signature(skin)
    b.scale.x /= 1.8
    s = next(h for h in hits if h.users_collection[0].name == HIT_COLLECTIONS["slash"])
    s.rotation_euler.rotate_axis('Z', 0.8)
    bpy.context.evaluated_depsgraph_get().update()
    rotated = _mesh_signature(skin)
    s.rotation_euler.rotate_axis('Z', -0.8)
    bpy.context.evaluated_depsgraph_get().update()
    check("moving an empty changes the skin", moved != before, f"{before[:3]} -> {moved[:3]}")
    check("scaling an empty changes the skin", scaled != before, f"-> {scaled[:3]}")
    check("rotating an empty changes the skin", rotated != before, f"-> {rotated[:3]}")
    # drip_time animates the drips
    _set_control("drip_time", 0.0)
    d0 = _mesh_signature(skin)
    _set_control("drip_time", 1.0)
    d1 = _mesh_signature(skin)
    check("drip_time 0 vs 1 changes the drips", d0 != d1 and d1[3] > d0[3],
          f"blood faces {d0[3]} -> {d1[3]}, verts {d0[0]} -> {d1[0]}")
    # blood only where it physically got to: at drip_time 0 nothing has run
    # out of the wounds yet, so no skin away from a wound may carry blood
    _set_control("drip_time", 0.0)
    stray0 = _stray_blood(skin)
    _set_control("drip_time", 1.0)
    check("no blood on intact skin at drip_time 0 (blood comes from the wound)", stray0 == 0,
          f"{stray0} stray blood vertices farther than 4 mm from any wound")
    # the blood grows over time (monotonic: 0 -> 0.25 -> 1)
    counts = []
    for dt_ in (0.0, 0.25, 1.0):
        _set_control("drip_time", dt_)
        counts.append(_mesh_signature(skin)[3])
    _set_control("drip_time", 1.0)
    check("blood grows with drip_time", counts[0] <= counts[1] <= counts[2] and counts[2] > counts[0],
          f"blood faces at drip_time 0 / 0.25 / 1: {counts}")
    # wound walls are smooth enough not to fold into stripes
    nw, nf, frac = _wall_fold_stats(skin)
    check("wound walls have no accordion folds (< 5 % of wall edges > 60 deg)", nw > 0 and frac < 0.05,
          f"{nf} of {nw} wall edges folded ({frac * 100:.1f} %)")
    # bleed 0 removes the drips
    _set_control("bleed", 0.0)
    b0 = _mesh_signature(skin)
    _set_control("bleed", saved["bleed"])
    check("bleed 0 removes drips and blood fills", b0[3] == 0, f"blood faces {b0[3]}")
    # the eyeball keeps its true size under a crushing beating and deflates
    # when ruptured (REFERENCE_NOTES §5.20.2-3); the other eye stays pristine
    eye_r, eye_l = bpy.data.objects.get("GH_Eye_R"), bpy.data.objects.get("GH_Eye_L")
    if eye_r is not None and eye_r.modifiers.get(MOD_NAME) and eye_l is not None:
        clear_hits()
        for loc, sz in (((-0.036, -0.080, 0.012), 1.2), ((-0.030, -0.085, -0.002), 1.2),
                        ((-0.042, -0.074, 0.020), 1.1)):
            add_hit("blunt", loc, size=sz, depth=0.95)
        bpy.context.evaluated_depsgraph_get().update()

        def radii(ob):
            import numpy as np
            me = ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
            co = np.empty(len(me.vertices) * 3)
            me.vertices.foreach_get("co", co)
            ob.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
            co = co.reshape(-1, 3)
            # (size = half the largest extent: the globe may also sink back
            # into the broken orbit, which moves it without resizing it)
            ext = float((co.max(0) - co.min(0)).max()) * 0.5
            r = np.linalg.norm(co - (co.max(0) + co.min(0)) * 0.5, axis=1)
            return ext, float(np.percentile(r, 5))
        rmax, r5 = radii(eye_r)
        lmax, l5 = radii(eye_l)
        check("crushed orbit: the eye never grows and deflates when ruptured",
              rmax < EYE_R * 1.12 and r5 < EYE_R * 0.9 and lmax < EYE_R * 1.12 and l5 > EYE_R * 0.93,
              f"right eye half extent {rmax * 1000:.1f} mm / 5th pct radius {r5 * 1000:.1f} mm, "
              f"left (unhurt) {lmax * 1000:.1f} / {l5 * 1000:.1f} mm, true r {EYE_R * 1000:.1f} mm")
        place_test_hits(KINDS)
    for k, v in saved.items():
        ctrl[k] = v
    ctrl.update_tag()
    bpy.context.evaluated_depsgraph_get().update()
    lines.append("RESULT: " + ("all checks passed" if ok else "SOME CHECKS FAILED"))
    print("\n".join(lines))
    return ok


def main():
    """Standalone test: build layers (real or placeholder), gore, verify, render."""
    ghc.reset_scene()
    objs, real_anatomy = _load_anatomy()
    mats, real_mats = _setup_materials(objs)
    t0 = time.time()
    build_gore_system(objs, mats)
    print(f"[gore] node groups built in {time.time() - t0:.1f} s")
    ok = verify_gore(objs)
    if "--no-render" not in sys.argv:
        # setup_stage() is hot; use the exposure materials.py is calibrated for
        exposure = -1.0
        if real_mats:
            import materials
            exposure = getattr(materials, "STAGE_EXPOSURE", -1.5)
        bpy.context.scene.view_settings.exposure = exposure
        _test_renders(samples=28)
    if not ok:
        sys.exit(1)


if __name__ == "__main__":
    main()
