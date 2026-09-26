"""Shared helpers for the procedural full body (`blender/gore_body`, Blender 5.x).

Everything in this project is generated from code: no downloaded meshes,
textures, HDRIs or add-ons.  Works both as the ``bpy`` Python module
(``python3 build.py``) and inside Blender (``blender -b --python build.py -- ...``).

This module owns the pieces every work package shares (plan §5):

* paths (``HERE``, ``GAME_OUT`` ...) - always relative to this folder;
* the body frame (metres, +Z up, face -Y, character's left +X, origin on the
  floor between the feet) and its conversions ``head_to_body`` / ``b2g``;
* the contract names: collections, objects, material slots, shape keys,
  actions (plan §5.3-5.6), so no module hard-codes a name twice;
* deterministic RNG seeds (``SEEDS`` / ``rng``);
* ``write_json`` with the schema envelope of plan §5.8;
* ``stage_cache`` (content-hash cache of a stage's objects in a .blend);
* small mesh / material / UV / render helpers;
* read-only access to the head project (``import_head``).

Stubs owned by later packages: ``weights_at`` (B6, lives in ``rig.py``) and
``seam_ring`` (B2, lives in ``head_integration.py``) are thin delegates here so
every module can call them through ``gb_common``.
"""
import hashlib
import json
import math
import os
import sys
import time

import numpy as np

import bpy
from mathutils import Vector

# ---------------------------------------------------------------------------
# Paths (plan §5.1: only relative to HERE)
# ---------------------------------------------------------------------------
HERE = os.path.dirname(os.path.abspath(__file__))
HEAD_DIR = os.path.normpath(os.path.join(HERE, "..", "gore_head"))
GAME_DIR = os.path.normpath(os.path.join(HERE, "..", "..", "gore-game"))
GAME_OUT = os.path.join(GAME_DIR, "assets", "generated")
SUBJECT_OUT = os.path.join(GAME_OUT, "subject")
PROPS_OUT = os.path.join(GAME_OUT, "props")
RENDER_DIR = os.path.join(HERE, "renders")
CACHE_DIR = os.path.join(HERE, ".cache")
BLEND_PATH = os.path.join(HERE, "gore_body.blend")

# ---------------------------------------------------------------------------
# Frames (plan §2.5, RB §1.2)
# ---------------------------------------------------------------------------
FRAME = "body_zup_m"
GODOT_MAPPING = "(x, z, -y)"
GENERATOR = "blender/gore_body/build.py"
HEAD_OFFSET = np.array([0.0, 0.020, 1.647])   # p_body = p_head + HEAD_OFFSET  [RB §1.2] V
SEAM_Z = 1.485                                 # canonical neck seam plane (plan D19)
SEAM_RING_N = 160                              # vertices on the seam ring (plan §5.8 params)
JSON_DECIMALS = 5                              # 1e-5 m = 10 µm (plan §5.8)

# ---------------------------------------------------------------------------
# Deterministic RNG (plan §5.1): every random draw uses rng(<name>)
# ---------------------------------------------------------------------------
SEEDS = {
    "placeholder": 26_0926_00,
    "body_skin": 26_0926_01,
    "shorts": 26_0926_02,
    "muscle_shell": 26_0926_03,
    "head": 26_0926_04,
    "face_shapes": 26_0926_05,
    "hair_cards": 26_0926_06,
    "skeleton": 26_0926_07,
    "fracture_skull": 26_0926_08,
    "fracture_long": 26_0926_09,
    "viscera": 26_0926_10,
    "neuro": 26_0926_11,
    "brain_labels": 26_0926_12,
    "vascular": 26_0926_13,
    "rig": 26_0926_14,
    "uv": 26_0926_15,
    "lookdev": 26_0926_16,
    "bake": 26_0926_17,
    "tileables": 26_0926_18,
    "props": 26_0926_19,
    "room": 26_0926_20,
    "export": 26_0926_21,
    "verify": 26_0926_22,
}


def rng(name):
    """Return a fresh ``numpy.random.Generator`` for the named consumer.

    Raises KeyError for unknown names so that every consumer is registered in
    ``SEEDS`` (one place to audit determinism)."""
    return np.random.default_rng(SEEDS[name])


# ---------------------------------------------------------------------------
# Contract names (plan §5.3-5.6).  Every module uses these constants.
# ---------------------------------------------------------------------------
ROOT_COLLECTION = "GoreBody"
SUB_COLLECTIONS = ("GB_Rig", "GB_Outer", "GB_Inner", "GB_Variants", "GB_LOD1",
                   "GB_Data", "GB_HighRes", "Stage")

ARMATURE = "GB_Armature"
OUTER_OBJECTS = ("GB_Head", "GB_Body", "GB_Shorts", "GB_Eye_L", "GB_Eye_R",
                 "GB_EyeFX_L", "GB_EyeFX_R", "GB_Mouth", "GB_BrowLash")
INNER_OBJECTS = ("GB_MuscleShell", "GB_Skeleton", "GB_Brain", "GB_Organs", "GB_Cord",
                 "GB_Vessels_Art", "GB_Vessels_Ven")
FRACTURE_BONES = ("Humerus", "RadUlna", "Femur", "Tibia")
VARIANT_OBJECTS = tuple(["GB_Frac_Skull_L", "GB_Frac_Skull_R", "GB_Frac_Skull_T"] +
                        [f"GB_Frac_{b}_{s}_{k}" for b in FRACTURE_BONES for s in ("L", "R")
                         for k in ("simple", "comminuted")])
LOD1_OBJECTS = ("GB_Head_LOD1", "GB_Body_LOD1")
HIGHRES_OBJECTS = ("GB_Head_HR", "GB_Body_HR", "GB_Skeleton_HR", "GB_Organs_HR", "GB_Brain_HR")

# object -> collection it must live in
OBJECT_COLLECTION = {ARMATURE: "GB_Rig"}
OBJECT_COLLECTION.update({n: "GB_Outer" for n in OUTER_OBJECTS})
OBJECT_COLLECTION.update({n: "GB_Inner" for n in INNER_OBJECTS})
OBJECT_COLLECTION.update({n: "GB_Variants" for n in VARIANT_OBJECTS})
OBJECT_COLLECTION.update({n: "GB_LOD1" for n in LOD1_OBJECTS})
OBJECT_COLLECTION.update({n: "GB_HighRes" for n in HIGHRES_OBJECTS})

# prefixes of data-only objects in GB_Data (curves / empties, never exported to the glb)
DATA_PREFIXES = {"GBV_": "vessel curve", "GBN_": "nerve curve", "GBL_": "landmark empty",
                 "GBH_": "organ hit-primitive empty", "GBC_": "cord curve"}

# material slots per object, in slot order (plan §5.6)
MATERIAL_SLOTS = {
    "GB_Head": ("GBM_skin_head", "GBM_mouth_lining"),
    "GB_Body": ("GBM_skin_torso", "GBM_skin_arm_L", "GBM_skin_arm_R", "GBM_skin_leg_L", "GBM_skin_leg_R"),
    "GB_Shorts": ("GBM_cloth",),
    "GB_Eye_L": ("GBM_eye",), "GB_Eye_R": ("GBM_eye",),
    "GB_EyeFX_L": ("GBM_tearline", "GBM_eye_occlusion"),
    "GB_EyeFX_R": ("GBM_tearline", "GBM_eye_occlusion"),
    "GB_Mouth": ("GBM_teeth", "GBM_gums", "GBM_tongue"),
    "GB_BrowLash": ("GBM_hair_card",),
    "GB_MuscleShell": ("GBM_muscle_head", "GBM_muscle_torso", "GBM_muscle_arm_L", "GBM_muscle_arm_R",
                       "GBM_muscle_leg_L", "GBM_muscle_leg_R"),
    "GB_Skeleton": ("GBM_bone", "GBM_cartilage"),
    "GB_Brain": ("GBM_brain",),
    "GB_Organs": ("GBM_organ",),
    "GB_Cord": ("GBM_cord",),
    "GB_Vessels_Art": ("GBM_vessel_art",),
    "GB_Vessels_Ven": ("GBM_vessel_ven",),
    "GB_Head_LOD1": ("GBM_skin_head", "GBM_mouth_lining"),
    "GB_Body_LOD1": ("GBM_skin_torso", "GBM_skin_arm_L", "GBM_skin_arm_R", "GBM_skin_leg_L", "GBM_skin_leg_R"),
}
MATERIAL_SLOTS.update({n: ("GBM_bone", "GBM_cartilage") for n in VARIANT_OBJECTS})

# placeholder colours (sRGB) so the glb reads sensibly before Godot swaps materials
MATERIAL_COLOURS = {
    "GBM_skin_head": "#C99A82", "GBM_skin_torso": "#C99A82", "GBM_skin_arm_L": "#C99A82",
    "GBM_skin_arm_R": "#C99A82", "GBM_skin_leg_L": "#C99A82", "GBM_skin_leg_R": "#C99A82",
    "GBM_mouth_lining": "#A4474A", "GBM_cloth": "#2E3033", "GBM_eye": "#E8E4DC",
    "GBM_tearline": "#D8D8D8", "GBM_eye_occlusion": "#202020", "GBM_teeth": "#E6DDC8",
    "GBM_gums": "#C0605E", "GBM_tongue": "#B85A5E", "GBM_hair_card": "#2A2018",
    "GBM_muscle_head": "#9B2F2B", "GBM_muscle_torso": "#9B2F2B", "GBM_muscle_arm_L": "#9B2F2B",
    "GBM_muscle_arm_R": "#9B2F2B", "GBM_muscle_leg_L": "#9B2F2B", "GBM_muscle_leg_R": "#9B2F2B",
    "GBM_bone": "#E9DFCC", "GBM_cartilage": "#CBD5D8", "GBM_brain": "#B79C94", "GBM_organ": "#7A2E23",
    "GBM_cord": "#EEE5D6", "GBM_vessel_art": "#B0202A", "GBM_vessel_ven": "#3C2A5A",
}
MATERIAL_ROUGHNESS = {"GBM_cloth": 0.85, "GBM_eye": 0.05, "GBM_tearline": 0.05, "GBM_teeth": 0.3,
                      "GBM_bone": 0.55, "GBM_cartilage": 0.35, "GBM_brain": 0.35, "GBM_organ": 0.3,
                      "GBM_cord": 0.4, "GBM_vessel_art": 0.3, "GBM_vessel_ven": 0.3}

# shape keys (plan §5.6)
FACE_SHAPE_KEYS = tuple(f"{au}_{s}" for au in ("AU01", "AU02", "AU04", "AU06", "AU07", "AU09", "AU10",
                                                "AU12", "AU15", "AU20", "mouth_slack", "swell_periorbital")
                        for s in ("L", "R"))
SHAPE_KEYS = {
    "GB_Head": FACE_SHAPE_KEYS,
    "GB_Body": ("chest_inhale", "belly_distension", "thigh_swell_L", "thigh_swell_R"),
    "GB_Organs": ("heart_systole", "lung_inhale_L", "lung_inhale_R", "lung_collapse_L", "lung_collapse_R",
                  "diaphragm_inhale"),
}
POSE_ACTIONS = ("pose_idle", "pose_guard", "pose_cower", "pose_brace")

# "gb_layer" custom property (exported as glTF extras) per object
LAYER_OF = {"GB_Head": "skin", "GB_Body": "skin", "GB_Shorts": "cloth", "GB_Eye_L": "eye", "GB_Eye_R": "eye",
            "GB_EyeFX_L": "eye_fx", "GB_EyeFX_R": "eye_fx", "GB_Mouth": "mouth", "GB_BrowLash": "hair",
            "GB_MuscleShell": "muscle", "GB_Skeleton": "bone", "GB_Brain": "brain", "GB_Organs": "organ",
            "GB_Cord": "cord", "GB_Vessels_Art": "vessel_art", "GB_Vessels_Ven": "vessel_ven",
            "GB_Head_LOD1": "skin", "GB_Body_LOD1": "skin"}
LAYER_OF.update({n: "bone_variant" for n in VARIANT_OBJECTS})

# JSON schemas: name -> required keys of the "data" block (plan §5.7-5.8)
SCHEMAS = {
    "gb.manifest/1": ("build", "files", "meshes", "rest_bounds", "wound_grid", "segment_origins",
                      "textures", "budgets", "pending"),
    "gb.rig/1": ("bones", "bodies", "face"),
    "gb.landmarks/1": ("landmarks", "head", "girths", "eyes"),
    "gb.organs/1": ("organs", "tubes"),
    "gb.vessels/1": ("segments", "beds", "nerves"),
    "gb.spine/1": ("vertebrae", "cord_segments", "conus_tip", "thecal_end", "brainstem"),
    "gb.codes/1": ("segment", "region", "dermatome", "bone_class", "cord_segment", "uv2"),
    "gb.brain_labels/1": ("origin", "voxel_size", "dims", "atlas", "regions"),
}


class NotBuiltYet(NotImplementedError):
    """Raised by a builder whose work package has not implemented it yet.

    ``build.py`` catches it per stage, reports ``pending (<owner>)`` and keeps
    the placeholder objects of the same contract names, so the export always
    runs end to end."""

    def __init__(self, owner, what):
        super().__init__(f"{what} is not implemented yet (owner {owner}); the placeholder stands in")
        self.owner = owner
        self.what = what


def not_built(owner, what):
    """Raise ``NotBuiltYet`` (used by stubs as their whole body)."""
    raise NotBuiltYet(owner, what)


# ---------------------------------------------------------------------------
# Command line (works for `python3 x.py --a` and `blender -b --python x.py -- --a`)
# ---------------------------------------------------------------------------
def script_args(argv=None):
    """Return the script's own arguments: everything after ``--`` if present
    (Blender binary), else ``sys.argv[1:]`` (bpy module)."""
    argv = list(sys.argv if argv is None else argv)
    if "--" in argv:
        return argv[argv.index("--") + 1:]
    return argv[1:] if argv and not argv[0].startswith("-") else argv


# ---------------------------------------------------------------------------
# Frames and conversions
# ---------------------------------------------------------------------------
def head_to_body(p):
    """Head-project frame -> body frame: ``p_body = p_head + (0, 0.020, 1.647)`` [RB §1.2].

    Accepts one point (sequence of 3) or an (N, 3) array; returns the same shape."""
    a = np.asarray(p, dtype=float)
    return a + HEAD_OFFSET


def body_to_head(p):
    """Body frame -> head-project frame (inverse of ``head_to_body``)."""
    return np.asarray(p, dtype=float) - HEAD_OFFSET


def b2g(v):
    """Body frame (Z up) -> Godot model space (Y up): ``(x, z, -y)`` [T10 zup2yup]."""
    a = np.asarray(v, dtype=float)
    return np.stack([a[..., 0], a[..., 2], -a[..., 1]], axis=-1)


def g2b(v):
    """Godot model space -> body frame: ``(x, -z, y)``."""
    a = np.asarray(v, dtype=float)
    return np.stack([a[..., 0], -a[..., 2], a[..., 1]], axis=-1)


def mirror_x(p):
    """Mirror a left-side point (or (N,3) array) to the right side (negate x)."""
    a = np.array(p, dtype=float)
    a[..., 0] *= -1.0
    return a


def mirror_axis(a):
    """Mirror a rotation axis (an axial vector) across the x = 0 plane: (ax, -ay, -az).

    A rotation that bends the left elbow forward about ``a`` bends the right
    elbow forward about ``mirror_axis(a)``."""
    v = np.array(a, dtype=float)
    return np.array([v[0], -v[1], -v[2]])


# ---------------------------------------------------------------------------
# Head project (read-only import, plan §5.1 / §7)
# ---------------------------------------------------------------------------
class _HeadModules:
    """Namespace returned by ``import_head``: ``anatomy``, ``materials``, ``gh_common``."""

    def __init__(self, anatomy, materials, gh_common):
        self.anatomy = anatomy
        self.materials = materials
        self.gh_common = gh_common


_HEAD = None


def import_head():
    """Import the head project's modules read-only and return them.

    ``blender/gore_head`` is appended to ``sys.path`` (never inserted first, so
    its ``build.py`` cannot shadow ours) and re-imported fresh on every build
    process, so improvements made by the head team flow in automatically.
    Nothing in that folder is ever written."""
    global _HEAD
    if _HEAD is None:
        if not os.path.isdir(HEAD_DIR):
            raise FileNotFoundError(f"head project not found at {HEAD_DIR}")
        if HEAD_DIR not in sys.path:
            sys.path.append(HEAD_DIR)
        import anatomy as gh_anatomy          # noqa: E402  (head project)
        import materials as gh_materials      # noqa: E402
        import gh_common as ghc               # noqa: E402
        for mod in (gh_anatomy, gh_materials, ghc):
            if not os.path.abspath(mod.__file__).startswith(HEAD_DIR):
                raise ImportError(f"{mod.__name__} resolved to {mod.__file__}, not the head project")
        _HEAD = _HeadModules(gh_anatomy, gh_materials, ghc)
    return _HEAD


def head_source_files():
    """The head-project files the body build depends on (for cache keys and manifest hashes)."""
    return [os.path.join(HEAD_DIR, f) for f in ("anatomy.py", "materials.py", "gh_common.py")]


# ---------------------------------------------------------------------------
# Scene, collections, objects
# ---------------------------------------------------------------------------
def reset_scene():
    """Start from an empty file with metric units (metres)."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.scale_length = 1.0
    scene.frame_start, scene.frame_end, scene.frame_current = 1, 1, 1
    return scene


def collections():
    """Create (or return) the contract collection tree of plan §5.3.

    Returns ``{name: bpy.types.Collection}`` for ``GoreBody`` and every child."""
    scene_col = bpy.context.scene.collection
    root = bpy.data.collections.get(ROOT_COLLECTION)
    if root is None:
        root = bpy.data.collections.new(ROOT_COLLECTION)
    if root.name not in scene_col.children:
        scene_col.children.link(root)
    out = {ROOT_COLLECTION: root}
    for name in SUB_COLLECTIONS:
        col = bpy.data.collections.get(name)
        if col is None:
            col = bpy.data.collections.new(name)
        if col.name not in root.children:
            root.children.link(col)
        out[name] = col
    # data-only and bake-source collections are hidden in renders by default
    for name in ("GB_Data", "GB_HighRes", "GB_Variants", "GB_LOD1"):
        out[name].hide_render = True
    return out


def link(obj, col):
    """Move ``obj`` into collection ``col`` (a Collection or its name), unlinking it elsewhere."""
    if isinstance(col, str):
        col = collections()[col] if col in SUB_COLLECTIONS or col == ROOT_COLLECTION else bpy.data.collections[col]
    for c in list(obj.users_collection):
        if c != col:
            c.objects.unlink(obj)
    if obj.name not in col.objects:
        col.objects.link(obj)
    return obj


def remove_object(name):
    """Delete the object called ``name`` (and its now-unused mesh/curve data) if it exists."""
    obj = bpy.data.objects.get(name)
    if obj is None:
        return False
    data = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if data is not None and data.users == 0:
        for coll in (bpy.data.meshes, bpy.data.curves, bpy.data.armatures):
            if data.name in coll and coll[data.name] == data:
                coll.remove(data)
                break
    return True


def new_object(name, data, col=None):
    """Create object ``name`` with ``data`` and link it to its contract collection.

    An existing object of the same name (typically the placeholder) is removed
    first, so a real builder simply *replaces* the stand-in and keeps the exact
    contract name.  ``col`` overrides the collection (default:
    ``OBJECT_COLLECTION`` for contract names, else ``GB_Data``)."""
    remove_object(name)
    if data is not None and hasattr(data, "name"):
        data.name = name
    obj = bpy.data.objects.new(name, data)
    if obj.name != name:
        raise RuntimeError(f"could not claim object name {name!r} (got {obj.name!r})")
    link(obj, col or OBJECT_COLLECTION.get(name, "GB_Data"))
    return obj


def contract_objects(include_data=False):
    """Return ``{name: object}`` for every contract object present in the file."""
    out = {n: bpy.data.objects[n] for n in OBJECT_COLLECTION if n in bpy.data.objects}
    if include_data:
        for o in bpy.data.objects:
            if any(o.name.startswith(p) for p in DATA_PREFIXES):
                out[o.name] = o
    return out


def exported_mesh_names(lod=0):
    """Contract mesh objects that go into ``GB_Subject.glb`` (lod 0) or ``_LOD1.glb`` (lod 1)."""
    if lod == 1:
        return list(LOD1_OBJECTS)
    return list(OUTER_OBJECTS) + list(INNER_OBJECTS) + list(VARIANT_OBJECTS)


# ---------------------------------------------------------------------------
# Mesh helpers (numpy <-> Blender)
# ---------------------------------------------------------------------------
def mesh_from_arrays(name, verts, faces, smooth=True):
    """Build a mesh datablock from an (N,3) vertex array and a list/array of faces."""
    me = bpy.data.meshes.new(name)
    verts = np.asarray(verts, dtype=float)
    faces = [list(map(int, f)) for f in faces]
    me.from_pydata(verts.tolist(), [], faces)
    me.validate(clean_customdata=False)
    me.update()
    if smooth and len(me.polygons):
        me.shade_smooth()
    return me


def get_verts(me):
    """Vertex positions of a mesh as an (N, 3) float64 array."""
    v = np.empty(len(me.vertices) * 3, dtype=np.float64)
    me.vertices.foreach_get("co", v)
    return v.reshape(-1, 3)


def set_verts(me, v):
    """Write an (N, 3) array back into the mesh vertices."""
    me.vertices.foreach_set("co", np.asarray(v, dtype=np.float64).ravel())
    me.update()


def mesh_arrays(me):
    """Return ``(verts[N,3], tris[M,3])`` after triangulating loop triangles."""
    me.calc_loop_triangles()
    t = np.empty(len(me.loop_triangles) * 3, dtype=np.int64)
    me.loop_triangles.foreach_get("vertices", t)
    return get_verts(me), t.reshape(-1, 3)


def face_centres(me):
    """(F, 3) array of polygon centres."""
    c = np.empty(len(me.polygons) * 3, dtype=np.float64)
    me.polygons.foreach_get("center", c)
    return c.reshape(-1, 3)


def tri_count(me):
    """Number of triangles the mesh exports as."""
    me.calc_loop_triangles()
    return len(me.loop_triangles)


def apply_transform(obj):
    """Bake the object's matrix into its mesh and reset it to identity (plan §5.4)."""
    if obj.type == 'MESH':
        obj.data.transform(obj.matrix_basis)
    obj.matrix_basis.identity()


def point_attr(obj, name, values, kind='FLOAT'):
    """Create or overwrite a POINT attribute (FLOAT or INT)."""
    me = obj.data
    att = me.attributes.get(name)
    if att is not None and att.data_type != kind:
        me.attributes.remove(att)
        att = None
    if att is None:
        att = me.attributes.new(name, kind, 'POINT')
    arr = np.asarray(values, dtype=np.float32 if kind == 'FLOAT' else np.int32)
    att.data.foreach_set("value", arr)
    return att


def read_point_attr(obj, name, kind='FLOAT'):
    """Read a POINT attribute into a numpy array (None if missing)."""
    att = obj.data.attributes.get(name)
    if att is None:
        return None
    arr = np.empty(len(obj.data.vertices), dtype=np.float32 if kind == 'FLOAT' else np.int32)
    att.data.foreach_get("value", arr)
    return arr


def set_uv_from_vertex(obj, name, uv_per_vertex, index=None):
    """Create/overwrite UV map ``name`` from per-vertex UVs (shared across loops)."""
    me = obj.data
    layer = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    loops = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", loops)
    uv = np.asarray(uv_per_vertex, dtype=np.float32)[loops]
    layer.data.foreach_set("uv", uv.ravel())
    return layer


def set_uv_from_loops(obj, name, uv_per_loop):
    """Create/overwrite UV map ``name`` from per-loop UVs (allows seams)."""
    me = obj.data
    layer = me.uv_layers.get(name) or me.uv_layers.new(name=name)
    layer.data.foreach_set("uv", np.asarray(uv_per_loop, dtype=np.float32).ravel())
    return layer


def set_codes_uv(obj, code_u, code_v):
    """Write the integer code UV map ``gb_codes`` (plan §5.5).

    The glTF exporter flips V (``v_gltf = 1 - v``), so Blender stores
    ``1 - code_v``; Godot then reads ``UV2 = (code_u, code_v)`` exactly."""
    u = np.asarray(code_u, dtype=np.float64)
    v = np.asarray(code_v, dtype=np.float64)
    set_uv_from_vertex(obj, "gb_codes", np.stack([u, 1.0 - v], axis=1))


def read_codes_uv(obj):
    """Inverse of ``set_codes_uv``: per-vertex (code_u, code_v) as int arrays."""
    me = obj.data
    layer = me.uv_layers.get("gb_codes")
    if layer is None:
        return None, None
    uv = np.empty(len(me.loops) * 2, dtype=np.float32)
    layer.data.foreach_get("uv", uv)
    uv = uv.reshape(-1, 2)
    loops = np.empty(len(me.loops), dtype=np.int64)
    me.loops.foreach_get("vertex_index", loops)
    per_v = np.zeros((len(me.vertices), 2), dtype=np.float64)
    per_v[loops] = uv
    return np.rint(per_v[:, 0]).astype(int), np.rint(1.0 - per_v[:, 1]).astype(int)


def ensure_uv_order(obj):
    """Make sure ``atlas`` is UV map 0 and ``gb_codes`` UV map 1 (glTF TEXCOORD_0/1)."""
    me = obj.data
    names = [l.name for l in me.uv_layers]
    if names[:2] != ["atlas", "gb_codes"]:
        raise ValueError(f"{obj.name}: UV maps must be ['atlas', 'gb_codes', ...], got {names}")
    me.uv_layers.active_index = 0
    me.uv_layers["atlas"].active_render = True


# ---------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------
def hex_to_linear(hexstr):
    """sRGB hex '#RRGGBB' -> linear RGBA tuple (for Principled base colour)."""
    h = hexstr.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return (lin[0], lin[1], lin[2], 1.0)


def placeholder_material(name):
    """Named plain Principled material (plan §5.6: Godot swaps it by name)."""
    mat = bpy.data.materials.get(name)
    if mat is None:
        mat = bpy.data.materials.new(name)
    col = hex_to_linear(MATERIAL_COLOURS.get(name, "#808080"))
    mat.diffuse_color = col
    nt = mat.node_tree
    if nt is not None:
        bsdf = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = col
            bsdf.inputs["Roughness"].default_value = MATERIAL_ROUGHNESS.get(name, 0.5)
    return mat


def set_material_slots(obj, face_slot=None, names=None):
    """Assign the contract material slots of ``obj`` (plan §5.6).

    ``face_slot``: optional per-polygon slot index array."""
    names = names or MATERIAL_SLOTS[obj.name]
    me = obj.data
    me.materials.clear()
    for n in names:
        me.materials.append(placeholder_material(n))
    if face_slot is not None and len(me.polygons):
        me.polygons.foreach_set("material_index", np.asarray(face_slot, dtype=np.int32))
    me.update()


# ---------------------------------------------------------------------------
# JSON with the schema envelope (plan §5.8)
# ---------------------------------------------------------------------------
def _clean(x, nd=JSON_DECIMALS):
    """Recursively convert numpy types and round floats to ``nd`` decimals (no -0.0)."""
    if isinstance(x, dict):
        return {str(k): _clean(v, nd) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_clean(v, nd) for v in x]
    if isinstance(x, np.ndarray):
        return [_clean(v, nd) for v in x.tolist()]
    if isinstance(x, (bool, np.bool_)):
        return bool(x)
    if isinstance(x, (int, np.integer)):
        return int(x)
    if isinstance(x, (float, np.floating)):
        if not math.isfinite(float(x)):
            raise ValueError(f"non-finite value {x} in JSON data")
        r = round(float(x), nd)
        return 0.0 if r == 0 else r
    if x is None or isinstance(x, str):
        return x
    raise TypeError(f"cannot serialise {type(x).__name__}: {x!r}")


def validate_schema(data, schema):
    """Check the schema name and that every required top-level key exists.

    Returns a list of problems (empty = valid)."""
    if schema not in SCHEMAS:
        return [f"unknown schema {schema!r}"]
    missing = [k for k in SCHEMAS[schema] if k not in data]
    return [f"{schema}: missing key {k!r}" for k in missing]


def envelope(data, schema, build=None):
    """Wrap ``data`` in the plan §5.8 envelope."""
    return {"schema": schema, "frame": FRAME, "godot_mapping": GODOT_MAPPING,
            "generator": GENERATOR, "build_id": build or build_id(), "data": data}


def write_json(path, data, schema, build=None):
    """Write ``data`` wrapped in the schema envelope; floats rounded to 1e-5.

    Output is deterministic (insertion order kept, fixed separators, trailing
    newline), so an unchanged build reproduces byte-identical files.  Raises
    ValueError if ``data`` misses a key the schema requires."""
    problems = validate_schema(data, schema)
    if problems:
        raise ValueError("; ".join(problems))
    doc = _clean(envelope(data, schema, build))
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    text = json.dumps(doc, indent=1, ensure_ascii=False, allow_nan=False)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text + "\n")
    return path


def read_json(path):
    """Read an enveloped JSON file; returns the whole document (``doc['data']`` is the payload)."""
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Hashing, build id, stage cache
# ---------------------------------------------------------------------------
def file_hash(path, algo="sha256"):
    """Hex digest of a file's bytes."""
    h = hashlib.new(algo)
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def input_hash(paths, extra=""):
    """Stable hash over the contents (not mtimes) of ``paths`` plus ``extra`` text."""
    h = hashlib.sha256()
    for p in sorted(set(os.path.abspath(p) for p in paths)):
        h.update(os.path.relpath(p, HERE).replace(os.sep, "/").encode())
        h.update(file_hash(p).encode() if os.path.exists(p) else b"<missing>")
    h.update(extra.encode())
    return h.hexdigest()


def source_files():
    """Every Python source of this module plus the head files it imports."""
    out = []
    for root, _dirs, files in os.walk(HERE):
        if os.sep + "." in root or "__pycache__" in root or os.sep + "renders" in root:
            continue
        out += [os.path.join(root, f) for f in files if f.endswith(".py")]
    return sorted(out) + head_source_files()


_BUILD_ID = None


def build_id():
    """Deterministic build id ``gb-<12 hex>`` = hash of all generator sources.

    (The plan's example adds a timestamp; it is left out on purpose so that an
    unchanged build reproduces byte-identical JSON; see CONTRACT.md.)"""
    global _BUILD_ID
    if _BUILD_ID is None:
        _BUILD_ID = "gb-" + input_hash(source_files(), bpy.app.version_string)[:12]
    return _BUILD_ID


class StageCache:
    """Content-hash cache of one stage's objects, stored as a .blend library.

    Usage in a stage::

        cache = gb_common.stage_cache("skin", [HERE + "/body_skin.py", ...])
        if cache.hit:
            objs = cache.load()
        else:
            objs = build_body_skin()
            cache.save(objs.values())

    The key covers the listed input files, ``gb_common.py``, all ``gb_data``
    tables and the Blender version.  Files live in ``HERE/.cache`` (not
    committed)."""

    def __init__(self, name, input_paths, extra=""):
        data_dir = os.path.join(HERE, "gb_data")
        deps = list(input_paths) + [os.path.join(HERE, "gb_common.py")]
        deps += [os.path.join(data_dir, f) for f in sorted(os.listdir(data_dir)) if f.endswith(".py")]
        self.name = name
        self.key = input_hash(deps, extra + "|" + bpy.app.version_string)[:16]
        self.path = os.path.join(CACHE_DIR, f"{name}-{self.key}.blend")

    @property
    def hit(self):
        """True if a cache file for exactly these inputs exists."""
        return os.path.exists(self.path)

    def save(self, objects):
        """Write the objects (with their meshes, materials, attributes) to the cache."""
        os.makedirs(CACHE_DIR, exist_ok=True)
        for old in os.listdir(CACHE_DIR):
            if old.startswith(self.name + "-") and old.endswith(".blend"):
                os.remove(os.path.join(CACHE_DIR, old))
        bpy.data.libraries.write(self.path, set(objects), fake_user=True, compress=True)
        return self.path

    def load(self):
        """Append the cached objects, replacing same-named objects, into their collections."""
        with bpy.data.libraries.load(self.path, link=False) as (src, _dst):
            names = list(src.objects)
        for n in names:
            remove_object(n)
        with bpy.data.libraries.load(self.path, link=False) as (_src, dst):
            dst.objects = names
        out = {}
        for obj in dst.objects:
            if obj is None:
                continue
            obj.use_fake_user = False
            link(obj, OBJECT_COLLECTION.get(obj.name, "GB_Data"))
            out[obj.name] = obj
        return out


def stage_cache(name, input_paths, extra=""):
    """Return a ``StageCache`` for stage ``name`` keyed on ``input_paths`` (see class)."""
    return StageCache(name, input_paths, extra)


# ---------------------------------------------------------------------------
# Delegating stubs owned by later work packages
# ---------------------------------------------------------------------------
def weights_at(points, layer="skin"):
    """Shared analytic skin weights (owner B6, implemented in ``rig.weights_at``).

    Returns ``(idx[N,4] int, w[N,4] float)`` where ``idx`` indexes
    ``gb_data.rig_table.BONE_NAMES``; rows sum to 1.  Every layer must use this
    one function (plan D8)."""
    import rig  # local import: rig imports gb_common
    return rig.weights_at(points, layer=layer)


def seam_ring(n=SEAM_RING_N):
    """Canonical neck seam ring (owner B2, implemented in ``head_integration.seam_ring``).

    Returns an (n, 3) array of ring vertices in the body frame at z ~= SEAM_Z."""
    import head_integration  # local import
    return head_integration.seam_ring(n)


# ---------------------------------------------------------------------------
# Timing and logging
# ---------------------------------------------------------------------------
class Timer:
    """Context manager that prints and records the duration of a block."""

    records = {}

    def __init__(self, label, quiet=False):
        self.label = label
        self.quiet = quiet

    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *exc):
        self.dt = time.perf_counter() - self.t0
        Timer.records[self.label] = round(self.dt, 2)
        if not self.quiet:
            print(f"  [{self.dt:6.1f} s] {self.label}")
        return False


def log(msg):
    """Uniform console output for build scripts."""
    print(f"[gore_body] {msg}", flush=True)


# ---------------------------------------------------------------------------
# Test renders (plan §5.1: <= 640 px, <= 48 samples, denoised)
# ---------------------------------------------------------------------------
BODY_VIEWS = {
    # name: (camera location, look-at target, lens mm)
    "front": ((0.0, -4.6, 1.00), (0.0, 0.0, 0.93), 50.0),
    "three_q": ((-2.9, -3.5, 1.25), (0.0, 0.0, 0.93), 50.0),
    "side": ((-4.6, 0.02, 1.00), (0.0, 0.0, 0.93), 50.0),
    "back": ((0.0, 4.6, 1.05), (0.0, 0.0, 0.93), 50.0),
    "head_front": ((0.0, -0.95, 1.62), (0.0, 0.0, 1.60), 85.0),
    "head_three_q": ((-0.60, -0.72, 1.66), (0.0, 0.0, 1.60), 85.0),
    "torso_front": ((0.0, -2.2, 1.28), (0.0, 0.0, 1.22), 70.0),
    "torso_side": ((-2.2, 0.0, 1.28), (0.0, 0.0, 1.22), 70.0),
}


def look_at(obj, target):
    """Point an object's -Z axis at ``target`` (Y up)."""
    d = Vector(target) - obj.location
    obj.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def add_camera(name, location, target, lens=50.0):
    """Create or move a camera in the ``Stage`` collection."""
    cam_data = bpy.data.cameras.get(name) or bpy.data.cameras.new(name)
    cam = bpy.data.objects.get(name) or bpy.data.objects.new(name, cam_data)
    link(cam, "Stage")
    cam.location = location
    cam.data.lens = lens
    cam.data.clip_start = 0.02
    cam.data.clip_end = 50.0
    look_at(cam, target)
    return cam


def _area_light(name, location, target, energy, size, color=(1, 1, 1)):
    data = bpy.data.lights.get(name) or bpy.data.lights.new(name, 'AREA')
    data.energy, data.size, data.color = energy, size, color
    obj = bpy.data.objects.get(name) or bpy.data.objects.new(name, data)
    link(obj, "Stage")
    obj.location = location
    look_at(obj, target)
    return obj


def setup_stage(floor=True):
    """Neutral studio for full-body test renders: key/fill/rim area lights, grey floor, AgX."""
    scene = bpy.context.scene
    _area_light("GB_Key", (-2.2, -3.0, 3.0), (0, 0, 1.1), 1400.0, 2.0, (1.0, 0.96, 0.9))
    _area_light("GB_Fill", (3.0, -2.4, 1.4), (0, 0, 1.0), 450.0, 2.5, (0.85, 0.9, 1.0))
    _area_light("GB_Rim", (1.2, 3.2, 2.6), (0, 0, 1.2), 1100.0, 1.5, (1.0, 0.97, 0.95))
    if floor and "GB_StageFloor" not in bpy.data.objects:
        me = mesh_from_arrays("GB_StageFloor", [(-6, -6, 0), (6, -6, 0), (6, 6, 0), (-6, 6, 0)], [(0, 1, 2, 3)])
        fl = bpy.data.objects.new("GB_StageFloor", me)
        mat = bpy.data.materials.get("GB_StageFloorMat") or bpy.data.materials.new("GB_StageFloorMat")
        mat.diffuse_color = (0.18, 0.18, 0.19, 1.0)
        bsdf = next((n for n in mat.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bsdf is not None:
            bsdf.inputs["Base Color"].default_value = (0.18, 0.18, 0.19, 1.0)
            bsdf.inputs["Roughness"].default_value = 0.8
        me.materials.append(mat)
        link(fl, "Stage")
    world = bpy.data.worlds.get("GB_World") or bpy.data.worlds.new("GB_World")
    scene.world = world
    bg = world.node_tree.nodes.get("Background")
    if bg is not None:
        bg.inputs[0].default_value = (0.03, 0.032, 0.036, 1.0)
        bg.inputs[1].default_value = 1.0
    scene.view_settings.view_transform = 'AgX'
    try:
        scene.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    return scene


def configure_render(samples=32, res=(480, 640), engine='CYCLES'):
    """CPU Cycles with OIDN denoising, PNG output (small, shared machine)."""
    scene = bpy.context.scene
    scene.render.engine = engine
    if engine == 'CYCLES':
        scene.cycles.device = 'CPU'
        scene.cycles.samples = min(int(samples), 48)
        scene.cycles.use_adaptive_sampling = True
        scene.cycles.max_bounces = 6
        try:
            scene.cycles.use_denoising = True
            scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        except (AttributeError, TypeError):
            pass
    scene.render.resolution_x = min(int(res[0]), 640)
    scene.render.resolution_y = min(int(res[1]), 640)
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = 'PNG'
    return scene


def render(path, camera, samples=32, res=(480, 640)):
    """Render a still to ``path`` (absolute or relative to HERE). Returns the absolute path."""
    scene = configure_render(samples, res)
    scene.camera = camera
    path = path if os.path.isabs(path) else os.path.join(HERE, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def render_views(prefix, views=("front", "three_q", "side", "back"), out_dir=RENDER_DIR,
                 samples=32, res=(480, 640)):
    """Render several ``BODY_VIEWS`` as ``<out_dir>/<prefix>_<view>.png``; returns the paths."""
    setup_stage()
    paths = []
    for v in views:
        loc, tgt, lens = BODY_VIEWS[v]
        cam = add_camera(f"GB_Cam_{v}", loc, tgt, lens)
        paths.append(render(os.path.join(out_dir, f"{prefix}_{v}.png"), cam, samples, res))
    return paths
