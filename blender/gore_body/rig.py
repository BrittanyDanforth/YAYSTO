"""Rig, weights, poses and rig.json (owner B6; this is B0's working v0 draft).

Plan §3.1, §5.4, §8.2 B6.  Everything here is data-driven from
``gb_data.rig_table`` so B6 can refine the weight model without touching
names or interfaces.

Entry points (final signatures)
-------------------------------
``build_armature()``            -> the ``GB_Armature`` object (39 deform bones, A-pose bind)
``weights_at(points, layer)``   -> (idx[N,4], w[N,4]) - ONE analytic weight function for every layer (D8)
``skin_all(objs)``              -> parents + vertex groups + a single ARMATURE modifier on every mesh
``build_poses(arm)``            -> single-frame key-pose actions pose_idle/guard/cower/brace
``rig_table()``                 -> rig.json payload (bones, bodies, face)

v0 weight model (B0)
--------------------
For each candidate bone b, ``d_b`` is the distance from the point to the
bone's weight segment divided by the bone's nominal limb radius ``R_b`` (so a
wide trunk bone and a thin arm bone compete fairly); overshoot past a segment
end is weighted 1/AXIAL times more than the radial distance, which keeps the
blend zone about +-0.5 R around each joint.  Weights are
``exp(-((d_b - d_min) / TAU)^2)``, the best four are kept and normalised, then
snapped to a 1/4096 grid (exact sums).  Jaw influence is a smooth region below
the mouth line; eyes, lids, tongue and rigid parts are assigned through the
``gb_rigid_bone`` point attribute (bone index, -1 = use the analytic weights).
B6 replaces this with the plan's final model (joint blend zones scaled by the
local limb radius, twist sharing, face regions) and the deformation tests.
"""
import math
import os
import sys

import numpy as np

import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402
from gb_data import myotomes as MYO  # noqa: E402

BONE_NAMES = RT.BONE_NAMES
BONE_INDEX = RT.BONE_INDEX
TAU = 0.5            # normalised-distance blend width
AXIAL = 0.4          # overshoot beyond a bone end counts 1/AXIAL times more than radial distance
QUANT = 4096         # weight grid (exact float sums)

# Nominal limb radius per bone (m, from the girth table) and optional weight
# segments that differ from the bone (pelvis mass below the hips bone, heel
# behind the ankle).  E values; B6 tunes.
_R = {"hips": 0.15, "spine": 0.13, "chest": 0.14, "upper_chest": 0.13, "neck": 0.06, "head": 0.085,
      "clavicle": 0.05, "upper_arm": 0.048, "upper_arm_twist": 0.048, "forearm": 0.042, "forearm_twist": 0.042,
      "hand": 0.04, "fingers": 0.035, "thumb": 0.013, "thigh": 0.085, "shin": 0.055, "foot": 0.045,
      "toes": 0.035}
_WSEG = {"hips": ((0.0, 0.020, 0.880), (0.0, 0.000, 1.030)),
         "head": ((0.0, 0.015, 1.625), (0.0, 0.020, 1.780)),
         "foot_L": ((0.095, 0.085, 0.045), (0.119, -0.079, 0.025))}
_EXCLUDED = {"root", "jaw", "tongue", "eye_L", "eye_R", "lid_upper_L", "lid_lower_L", "lid_upper_R", "lid_lower_R"}


def _base(name):
    return name[:-2] if name.endswith(("_L", "_R")) else name


def _weight_segments():
    """(names, A[K,3], B[K,3], R[K]) for the generic candidate bones."""
    names, A, B, R = [], [], [], []
    for b in RT.bones():
        n = b["name"]
        if n in _EXCLUDED:
            continue
        seg = _WSEG.get(n)
        if seg is None and n.endswith("_R") and (n[:-2] + "_L") in _WSEG:
            l = _WSEG[n[:-2] + "_L"]
            seg = ((-l[0][0], l[0][1], l[0][2]), (-l[1][0], l[1][1], l[1][2]))
        if seg is None:
            seg = (b["head"], b["tail"])
        names.append(n)
        A.append(seg[0])
        B.append(seg[1])
        R.append(_R[_base(n)])
    return names, np.array(A, float), np.array(B, float), np.array(R, float)


_SEGS = _weight_segments()


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def jaw_region(points):
    """0..1 jaw influence: in front of the TMJ, below the mouth line, above the chin-neck line (v0, E)."""
    p = np.asarray(points, float)
    x, y, z = np.abs(p[:, 0]), p[:, 1], p[:, 2]
    return (_smooth(1.600, 1.588, z) * _smooth(1.528, 1.548, z) * _smooth(0.012, -0.004, y)
            * _smooth(0.068, 0.052, x))


def weights_at(points, layer="skin"):
    """Analytic skin weights for body-frame rest points (plan D8: every layer uses this).

    Returns ``(idx, w)`` with shapes (N, 4): bone indices into ``BONE_NAMES``
    and weights on a 1/4096 grid that sum exactly to 1.  ``layer`` is kept for
    B6's per-layer tweaks; v0 treats every layer alike except ``head_rigid``
    (brain, eye FX: 100 % head)."""
    p = np.asarray(points, dtype=float).reshape(-1, 3)
    n = len(p)
    idx = np.zeros((n, 4), dtype=np.int32)
    w = np.zeros((n, 4), dtype=np.float64)
    if n == 0:
        return idx, w
    if layer == "head_rigid":
        idx[:, 0] = BONE_INDEX["head"]
        w[:, 0] = 1.0
        return idx, w
    names, A, B, R = _SEGS
    out_i = np.empty((n, 4), dtype=np.int32)
    out_w = np.empty((n, 4), dtype=np.float64)
    chunk = 200000
    for s in range(0, n, chunk):
        q = p[s:s + chunk]
        ab = B - A                                        # (K,3)
        L = np.linalg.norm(ab, axis=1)                    # (K,)
        ap = q[:, None, :] - A[None, :, :]                # (n,K,3)
        t_raw = np.einsum("nkj,kj->nk", ap, ab) / (L * L)[None]
        radial = np.linalg.norm(ap - t_raw[..., None] * ab[None], axis=2)      # to the infinite axis
        overshoot = np.maximum(np.maximum(-t_raw, t_raw - 1.0), 0.0) * L[None]  # beyond the segment ends
        d = np.sqrt((overshoot / (AXIAL * R[None])) ** 2 + (radial / R[None]) ** 2)
        dmin = d.min(axis=1, keepdims=True)
        wt = np.exp(-((d - dmin) / TAU) ** 2)
        top = np.argsort(-wt, axis=1)[:, :4]
        tw = np.take_along_axis(wt, top, axis=1)
        tw /= tw.sum(axis=1, keepdims=True)
        out_i[s:s + chunk] = np.array([BONE_INDEX[names[k]] for k in range(len(names))])[top]
        out_w[s:s + chunk] = tw
    # jaw blend: the three strongest bones keep (1 - wj), the jaw takes slot 3 with wj
    wj = jaw_region(p)
    m = wj > 1e-4
    if m.any():
        keep = out_w[m, :3]
        keep = keep / keep.sum(axis=1, keepdims=True) * (1.0 - wj[m])[:, None]
        out_w[m, :3] = keep
        out_i[m, 3] = BONE_INDEX["jaw"]
        out_w[m, 3] = wj[m]
    return _quantise(out_i, out_w)


def _quantise(idx, w):
    """Snap weights to a 1/QUANT grid; the largest absorbs the remainder so rows sum exactly to 1."""
    w = np.clip(w, 0.0, None)
    w = w / np.maximum(w.sum(axis=1, keepdims=True), 1e-12)
    q = np.floor(w * QUANT + 0.5)
    big = np.argmax(w, axis=1)
    rows = np.arange(len(w))
    q[rows, big] = 0
    q[rows, big] = QUANT - q.sum(axis=1)
    return idx, q / QUANT


def rigid_weights(n, bone):
    """(idx, w) assigning all ``n`` points 100 % to ``bone``."""
    idx = np.zeros((n, 4), dtype=np.int32)
    w = np.zeros((n, 4), dtype=np.float64)
    idx[:, 0] = BONE_INDEX[bone]
    w[:, 0] = 1.0
    return idx, w


# ---------------------------------------------------------------------------
# Armature
# ---------------------------------------------------------------------------
def build_armature():
    """Create ``GB_Armature`` (identity transform, 39 deform bones, A-pose bind) in GB_Rig."""
    gbc.collections()
    arm_data = bpy.data.armatures.get(gbc.ARMATURE)
    if arm_data is not None and arm_data.users == 0:
        bpy.data.armatures.remove(arm_data)
    arm_data = bpy.data.armatures.new(gbc.ARMATURE)
    arm = gbc.new_object(gbc.ARMATURE, arm_data)
    arm.show_in_front = True
    arm_data.display_type = 'STICK'
    view_layer = bpy.context.view_layer
    view_layer.objects.active = arm
    arm.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    ebs = {}
    for b in RT.bones():
        eb = arm_data.edit_bones.new(b["name"])
        eb.head = Vector(b["head"])
        eb.tail = Vector(b["tail"])
        eb.use_deform = True
        eb.use_connect = False
        eb.align_roll(Vector(b["roll_align"]))
        if b["parent"]:
            eb.parent = ebs[b["parent"]]
        ebs[b["name"]] = eb
    bpy.ops.object.mode_set(mode='OBJECT')
    arm["gb_layer"] = "rig"
    arm["gb_schema"] = 1
    for pb in arm.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    return arm


def rest_basis(arm, name):
    """Armature-space 3x3 rest basis of a bone (columns = local x, y, z in the body frame)."""
    return arm.data.bones[name].matrix_local.to_3x3()


# ---------------------------------------------------------------------------
# Skinning
# ---------------------------------------------------------------------------
def assign_weights(obj, arm, idx, w):
    """Write (idx, w) into vertex groups of ``obj`` (one group per used bone)."""
    obj.vertex_groups.clear()
    n = len(obj.data.vertices)
    used = np.unique(idx[w > 0])
    groups = {int(b): obj.vertex_groups.new(name=BONE_NAMES[int(b)]) for b in used}
    for b, vg in groups.items():
        rows, cols = np.nonzero((idx == b) & (w > 0))
        vals = w[rows, cols]
        # bucket by identical value: one API call per distinct weight
        order = np.argsort(vals, kind="stable")
        vals_s, rows_s = vals[order], rows[order]
        cuts = np.flatnonzero(np.diff(vals_s)) + 1
        for grp_rows, grp_vals in zip(np.split(rows_s, cuts), np.split(vals_s, cuts)):
            if len(grp_rows):
                vg.add(grp_rows.tolist(), float(grp_vals[0]), 'REPLACE')
    _ = n


def skin_object(obj, arm, layer="skin"):
    """Parent to the armature (OBJECT), weight every vertex, add the single ARMATURE modifier."""
    v = gbc.get_verts(obj.data)
    idx, w = weights_at(v, layer=layer)
    rigid = gbc.read_point_attr(obj, "gb_rigid_bone", 'INT')
    if rigid is not None:
        m = rigid >= 0
        if m.any():
            idx[m] = 0
            w[m] = 0.0
            idx[m, 0] = rigid[m]
            w[m, 0] = 1.0
    assign_weights(obj, arm, idx, w)
    for mod in list(obj.modifiers):
        obj.modifiers.remove(mod)
    obj.parent = arm
    obj.parent_type = 'OBJECT'
    obj.matrix_parent_inverse.identity()
    mod = obj.modifiers.new("Armature", 'ARMATURE')
    mod.object = arm
    mod.use_vertex_groups = True
    mod.use_bone_envelopes = False
    return idx, w


# per-object weight layer (v0); rigid parts use the gb_rigid_bone attribute
SKIN_LAYER = {"GB_Brain": "head_rigid", "GB_EyeFX_L": "head_rigid", "GB_EyeFX_R": "head_rigid"}


def skin_all(objs):
    """Skin every exported mesh in ``objs`` (dict name -> object) to ``GB_Armature``."""
    arm = bpy.data.objects[gbc.ARMATURE]
    for name, obj in objs.items():
        if obj is None or obj.type != 'MESH':
            continue
        skin_object(obj, arm, SKIN_LAYER.get(name, gbc.LAYER_OF.get(name, "skin")))
    return arm


# ---------------------------------------------------------------------------
# Key poses (single-frame actions; G5 adds procedural motion in Godot)
# ---------------------------------------------------------------------------
# pose: {bone_base: [(axis name, degrees), ...]} applied about the joint's resolved world axes (E)
POSES = {
    "pose_idle": {"forearm": [("flex", 8.0)], "shin": [("flex", 3.0)], "fingers": [("flex", 15.0)]},
    "pose_guard": {"upper_arm": [("flex", 45.0), ("abd", -25.0)], "forearm": [("flex", 115.0)],
                   "hand": [("flex", 10.0)], "fingers": [("flex", 70.0)], "neck": [("flex", 8.0)],
                   "shin": [("flex", 12.0)], "thigh": [("flex", 8.0)]},
    "pose_cower": {"spine": [("flex", 18.0)], "chest": [("flex", 14.0)], "upper_chest": [("flex", 8.0)],
                   "neck": [("flex", 22.0)], "head": [("flex", 10.0)],
                   "upper_arm": [("flex", 75.0), ("abd", -30.0)], "forearm": [("flex", 130.0)],
                   "hand": [("flex", 20.0)], "fingers": [("flex", 50.0)],
                   "thigh": [("flex", 30.0)], "shin": [("flex", 40.0)], "foot": [("flex", 10.0)]},
    "pose_brace": {"upper_arm": [("flex", 80.0), ("abd", 10.0)], "forearm": [("flex", 20.0)],
                   "hand": [("flex", -45.0)], "spine": [("flex", -4.0)], "neck": [("flex", -8.0)],
                   "fingers": [("flex", -10.0)], "thigh": [("flex", 5.0)], "shin": [("flex", 10.0)]},
}
# kinematic bones without a physical joint: axes borrowed from a neighbour (E)
_KIN_AXES = {"fingers": "hand", "thumb": "hand", "toes": "foot"}


def _world_axes():
    """{bone: {axis: world vector}} for every jointed body plus kinematic borrowers."""
    out = {}
    for row in RT.bodies():
        if row["joint"]:
            out[row["bone"]] = {k: np.array(v["world"]) for k, v in row["joint"]["axes"].items()}
    for side in ("L", "R"):
        for kin, src in _KIN_AXES.items():
            out[f"{kin}_{side}"] = out[f"{src}_{side}"]
    return out


def _local_quat(arm, bone, world_axis, deg):
    """Pose-bone quaternion that rotates about a rest-pose world axis by ``deg``."""
    m = rest_basis(arm, bone)
    ax_local = m.inverted() @ Vector(world_axis)
    return Quaternion(ax_local.normalized(), math.radians(deg))


def build_poses(arm):
    """Create the single-frame key-pose actions (plan §5.6) on ``arm``; leaves the rest pose active."""
    axes = _world_axes()
    arm.animation_data_create()
    for name in gbc.POSE_ACTIONS:
        old = bpy.data.actions.get(name)
        if old is not None:
            bpy.data.actions.remove(old)
        act = bpy.data.actions.new(name)
        act.use_fake_user = True
        arm.animation_data.action = act
        spec = POSES[name]
        for pb in arm.pose.bones:
            pb.rotation_mode = 'QUATERNION'
            q = Quaternion()
            base = _base(pb.name)
            for axis, deg in spec.get(base, []):
                if pb.name in axes and axis in axes[pb.name]:
                    q = _local_quat(arm, pb.name, axes[pb.name][axis], deg) @ q
            pb.rotation_quaternion = q
            pb.keyframe_insert("rotation_quaternion", frame=1)
    arm.animation_data.action = None
    for pb in arm.pose.bones:
        pb.rotation_quaternion = Quaternion()
        pb.location = (0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    return [bpy.data.actions[n] for n in gbc.POSE_ACTIONS]


# ---------------------------------------------------------------------------
# rig.json payload (plan §5.8)
# ---------------------------------------------------------------------------
def rig_table():
    """rig.json 'data': bones (with Blender rest bases when the armature exists), bodies, face."""
    arm = bpy.data.objects.get(gbc.ARMATURE)
    physical = {b["bone"] for b in RT.bodies()}
    bones = []
    for b in RT.bones():
        row = {"name": b["name"], "parent": b["parent"], "head": list(b["head"]), "tail": list(b["tail"]),
               "deform": True, "physical": b["name"] in physical, "kinematic": b["kinematic"]}
        if arm is not None and b["name"] in arm.data.bones:
            m = rest_basis(arm, b["name"])
            row["rest_basis_world"] = {"x": list(m.col[0]), "y": list(m.col[1]), "z": list(m.col[2])}
        if b["note"]:
            row["note"] = b["note"]
        bones.append(row)
    kin = {}
    for n in ("forearm_twist", "fingers", "thumb", "toes"):
        kin[n] = {k: v for k, v in MYO.myotomes_for(n).items()}
    face = {
        "lid_aperture_mm_to_deg": RT.LID_APERTURE_MM_TO_DEG_PLACEHOLDER,
        "lid_table_status": "placeholder format values; B2 measures them on the head mesh",
        "blend_shapes": list(gbc.FACE_SHAPE_KEYS),
        "bone_driven": {"AU05": "lid_upper_*", "AU26": "jaw", "AU43": "lid_upper_*"},
        "eye_bones": {"eye_L": list(RT.bones()[BONE_INDEX["eye_L"]]["head"]),
                      "eye_R": list(RT.bones()[BONE_INDEX["eye_R"]]["head"])},
    }
    return {"bones": bones, "bodies": RT.bodies(), "face": face, "kinematic_myotomes": kin,
            "poses": list(gbc.POSE_ACTIONS), "friction": RT.FRICTION,
            "notes": {"limits": "degrees about axes[*].world; positive = axes[*].pos direction",
                      "torque_cap_nm": "per direction key, before tone/paralysis multipliers (plan §3.2)",
                      "b2g": "Godot = (x, z, -y) of every vector here"}}


if __name__ == "__main__":
    gbc.reset_scene()
    arm = build_armature()
    build_poses(arm)
    print(f"{len(arm.data.bones)} bones; actions: {[a.name for a in bpy.data.actions]}")
