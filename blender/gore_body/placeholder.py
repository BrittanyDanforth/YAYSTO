"""Placeholder subject (owner B0): every contract object with its FINAL name, bones and materials.

Plan §5.2 / §8.2 B0.  ``build_placeholder()`` builds a complete, exportable
stand-in of the whole subject in about a minute so the Godot team can import,
rig and test from day one, and so every later work package can replace one
object at a time while the export keeps running end to end.

What is real and what is a stand-in
-----------------------------------
* **Head**: the head project's real head (``gore_head/anatomy.py``: skin with
  lids, lips, nose, ears; skull, jaw, brain, eyes, teeth, gums, tongue), re-imported
  read-only on every build and moved into the body frame by (0, 0.020, 1.647).
* **Body skin**: a smooth SDF mannequin built from the bible landmarks and
  girths [RB §7.1] (superellipse torso sections, tapered limb tubes, simple hands
  and feet), joined to the head on the canonical seam ring at z = 1.485 (the
  seam vertices of GB_Head and GB_Body are identical).  B1 replaces it.
* **Inner layers**: muscle shell (skin SDF offset by skin + fat per region
  [RB §7.6]), a simplified but complete skeleton (every bone piece id of
  ``gb_data.bones.BONE_PIECES``), organ primitives [RB §7.5], cord and cauda,
  vessel tubes from the RB §3.3 table, fracture variants as split copies.
* Codes (segment/region/dermatome, piece, organ, vessel, cord), UV maps,
  shape keys, armature, weights and key poses use the final contract.

Run alone: ``python3 placeholder.py [--quick] [--render]``.
"""
import math
import os
import sys
import time

import numpy as np

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
import gb_geom as gg  # noqa: E402
from gb_data import bones as BN  # noqa: E402
from gb_data import dermatomes as DM  # noqa: E402
from gb_data import landmarks as LM  # noqa: E402
from gb_data import organs as OR  # noqa: E402
from gb_data import ribs as RB_  # noqa: E402
from gb_data import rig_table as RT  # noqa: E402
from gb_data import segments as SG  # noqa: E402
from gb_data import tissue as TS  # noqa: E402
from gb_data import vertebrae as VT  # noqa: E402
from gb_data import vessels as VS  # noqa: E402
from gb_data import nerves as NV  # noqa: E402

# Mesh resolutions (m).  quick: < 2 min for the whole stage on 4 shared cores.
RES = {
    "quick": dict(head=0.0030, body=0.0065, muscle=0.0085, bone=0.0032, organ=0.0045, brain=0.0032,
                  mouth=0.0011, vessel_step=0.020),
    "full": dict(head=0.0018, body=0.0042, muscle=0.0060, bone=0.0022, organ=0.0030, brain=0.0022,
                 mouth=0.0008, vessel_step=0.019),
}

HEAD_OFFSET = gbc.HEAD_OFFSET
SEAM_Z = gbc.SEAM_Z
ARM_D = np.array(LM.ARM_DIRECTION_L)            # A-pose arm direction (left)
ARM_NM = np.array(LM.ARM_MEDIAL_NORMAL_L)       # palm-side (medial) normal
ARM_LAT = -ARM_NM


def _A():
    return gbc.import_head().anatomy


# ===========================================================================
# Body SDF (left side authored; every component takes ax = |x|)
# ===========================================================================
# Torso sections [RB §7.1 girth table, R05 §2.1]: z, half width, half depth, centre y, superellipse n
TORSO_SECTIONS = np.array([
    (0.815, 0.105, 0.070, 0.045, 2.2),
    (0.850, 0.148, 0.100, 0.036, 2.4),
    (0.885, 0.165, 0.1175, 0.028, 2.5),      # hips 97 cm: 33 x 23.5, front -0.090 / back +0.145
    (0.960, 0.160, 0.108, 0.012, 2.6),
    (1.075, 0.1475, 0.1025, -0.0155, 2.6),   # navel 84 cm: 29.5 x 20.5, front -0.118 / back +0.087
    (1.130, 0.140, 0.0975, -0.012, 2.7),     # natural waist 81 cm
    (1.220, 0.146, 0.106, -0.004, 2.9),
    (1.300, 0.1435, 0.115, 0.003, 3.2),      # chest 100 cm: 28.7 x 23, front -0.112 / back +0.118
    (1.380, 0.152, 0.108, 0.012, 3.0),
    (1.420, 0.140, 0.095, 0.018, 2.6),
    (1.455, 0.105, 0.078, 0.016, 2.2),
    (1.485, 0.072, 0.064, 0.012, 2.0),
    (1.515, 0.062, 0.060, 0.010, 2.0),
    (1.560, 0.060, 0.060, 0.012, 2.0),
])

# Arm tube (left, A-pose): point, radius  [RB §7.2 joints; R05 §2.1 arm girths]
_ELB = np.array((0.325, 0.020, 1.164))
_WRI = np.array((0.460, 0.020, 0.930))
_GH = np.array((0.180, 0.020, 1.415))
ARM_PTS = np.array([_GH, _GH + 0.5 * (_ELB - _GH), _ELB - 0.02 * ARM_D, _ELB + 0.05 * ARM_D,
                    _ELB + 0.14 * ARM_D, _WRI - 0.02 * ARM_D, _WRI])
ARM_R = np.array([0.050, 0.047, 0.041, 0.043, 0.036, 0.028, 0.027])

# Fingers (left): y of the MCP row, length (m), radius at base/tip, MCP set-back along d
FINGERS = [(-0.001, 0.080, 0.0095, 0.0080, 0.002), (0.020, 0.090, 0.0098, 0.0082, 0.0),
           (0.038, 0.084, 0.0092, 0.0078, 0.003), (0.054, 0.068, 0.0082, 0.0070, 0.010)]
_MCP3 = np.array((0.508, 0.020, 0.848))
CURL_DEG = (8.0, 18.0, 28.0)                    # cumulative curl toward the palm per phalanx (relaxed)
THUMB = (np.array((0.468, -0.005, 0.915)), np.array((0.482, -0.021, 0.878)), np.array((0.500, -0.030, 0.840)))

# Leg tube (left): point, radius [RB §7.1 thigh/knee/calf/ankle girths and centres]
LEG_PTS = np.array([(0.093, 0.010, 0.930), (0.093, 0.020, 0.790), (0.093, 0.015, 0.700),
                    (0.092, 0.012, 0.560), (0.091, 0.010, 0.495), (0.093, 0.040, 0.425),
                    (0.094, 0.066, 0.360), (0.094, 0.060, 0.250), (0.095, 0.055, 0.120),
                    (0.095, 0.050, 0.075)])
LEG_R = np.array([0.088, 0.087, 0.080, 0.066, 0.058, 0.056, 0.058, 0.047, 0.035, 0.033])
FOOT_PTS = np.array([(0.095, 0.083, 0.036), (0.099, 0.030, 0.038), (0.108, -0.030, 0.034),
                     (0.117, -0.080, 0.020), (0.124, -0.132, 0.013)])
FOOT_R = np.array([0.036, 0.037, 0.034, 0.021, 0.011])

# per-component offset of the muscle shell = skin + subcutaneous fat [RB §7.6] (m)
SKIN_FAT = {"torso_front_abdomen": 0.017, "torso_chest": 0.009, "torso_back": 0.011, "buttock": 0.022,
            "neck": 0.006, "shoulder": 0.008, "arm": 0.008, "forearm": 0.006, "hand": 0.004,
            "thigh": 0.011, "shank": 0.006, "foot": 0.004}


def _finger_polyline(y0, length, setback):
    """MCP -> PIP -> DIP -> tip for a left finger in the relaxed A-pose curl."""
    base = _MCP3 - setback * ARM_D + np.array([0.0, y0 - _MCP3[1], 0.0])
    seg = np.array([0.45, 0.30, 0.25]) * length
    pts = [base]
    for s, ang in zip(seg, CURL_DEG):
        a = math.radians(ang)
        d = math.cos(a) * ARM_D + math.sin(a) * ARM_NM
        pts.append(pts[-1] + s * d)
    return np.array(pts)


def _torso(ax, y, z):
    T = TORSO_SECTIONS
    a = np.interp(z, T[:, 0], T[:, 1])
    b = np.interp(z, T[:, 0], T[:, 2])
    cy = np.interp(z, T[:, 0], T[:, 3])
    n = np.interp(z, T[:, 0], T[:, 4])
    d = gg.superellipse2(ax, y - cy, a, b, n)
    return np.maximum(d, np.maximum(T[0, 0] - z, z - T[-1, 0]))


def _torso_extras(ax, y, z):
    """Gluteals, scapular muscles, clavicles, acromion, trapezius, deltoids and the larynx on top of the sections."""
    A = _A()
    back = A.sd_ellipsoid(ax, y, z, (0.080, 0.064, 1.405), (0.080, 0.040, 0.085))      # scapular muscles
    acro = A.sd_ellipsoid(ax, y, z, (0.168, 0.022, 1.440), (0.045, 0.060, 0.034))
    clav = A.sd_polyline(ax, y, z, np.array(BN.CLAVICLE_WAYPOINTS), [0.018, 0.016, 0.016, 0.018])[0]
    glut = A.sd_ellipsoid(ax, y, z, (0.075, 0.075, 0.905), (0.080, 0.068, 0.095))
    trap = A.sd_capsule(ax, y, z, (0.035, 0.030, 1.480), (0.165, 0.028, 1.440), 0.034, 0.030)
    delt = gg.sd_oellipsoid(ax, y, z, (0.196, 0.014, 1.400), (0.050, 0.062, 0.082),
                            gg.orthonormal(ARM_LAT, (0, 1, 0)))
    lar = A.sd_ellipsoid(ax, y, z, (0.0, -0.047, 1.527), (0.015, 0.015, 0.026))
    d = glut
    d = A.smin(d, back, 0.02)
    d = A.smin(d, clav, 0.015)
    d = A.smin(d, acro, 0.02)
    d = A.smin(d, trap, 0.01)
    d = A.smin(d, delt, 0.01)
    return A.smin(d, lar, 0.005)


def _arm(ax, y, z):
    return _A().sd_polyline(ax, y, z, ARM_PTS, ARM_R)[0]


def _hand(ax, y, z):
    A = _A()
    axes = (ARM_D, np.array([0.0, 1.0, 0.0]), ARM_NM)
    palm = gg.sd_obox(ax, y, z, _WRI + 0.052 * ARM_D + np.array([0.0, 0.0, 0.0]),
                      (0.047, 0.040, 0.0140), axes, rnd=0.0135)
    d = palm
    for y0, L, r0, r1, sb in FINGERS:
        P = _finger_polyline(y0, L, sb)
        f = A.sd_polyline(ax, y, z, P, [r0, r0 * 0.95, r1 * 1.02, r1])[0]
        d = A.smin(d, f, 0.004)
    th = A.sd_polyline(ax, y, z, np.array(THUMB), [0.013, 0.011, 0.0092])[0]
    return A.smin(d, th, 0.010)


def _leg(ax, y, z):
    return _A().sd_polyline(ax, y, z, LEG_PTS, LEG_R)[0]


def _foot(ax, y, z):
    A = _A()
    d = A.sd_polyline(ax, y, z, FOOT_PTS, FOOT_R)[0]
    fax = gg.orthonormal((0.993, 0.122, 0.0), (-0.122, 0.993, 0.0))
    fore = gg.sd_oellipsoid(ax, y, z, (0.121, -0.066, 0.026), (0.051, 0.040, 0.025), fax)
    toes = gg.sd_oellipsoid(ax, y, z, (0.119, -0.116, 0.015), (0.044, 0.032, 0.015), fax)
    d = A.smin(A.smin(d, fore, 0.012), toes, 0.012)
    mall = A.smin(A.sd_sphere(ax, y, z, (0.130, 0.060, 0.060), 0.0125),
                  A.sd_sphere(ax, y, z, (0.067, 0.045, 0.072), 0.0115), 0.01)       # malleoli [RB §7.3]
    d = A.smin(d, mall, 0.015)
    return np.maximum(d, -z)                      # flat sole on the floor


def _neck(ax, y, z):
    return _A().sd_capsule(ax, y, z, (0.0, 0.010, 1.430), (0.0, 0.022, 1.600), 0.062, 0.052)


def body_parts(x, y, z):
    """Component SDFs of the body (no head) as a dict (all share the same points)."""
    ax = np.abs(x)
    return {"torso": _torso(ax, y, z), "extras": _torso_extras(ax, y, z), "neck": _neck(ax, y, z),
            "arm": _arm(ax, y, z), "hand": _hand(ax, y, z), "leg": _leg(ax, y, z), "foot": _foot(ax, y, z)}


def _union(parts, off=None):
    """Blend the components (optionally each shrunk by its own offset array/scalar)."""
    A = _A()
    o = off or {}
    g = {k: v + o.get(k, 0.0) for k, v in parts.items()}
    trunk = A.smin(g["torso"], g["extras"], 0.02)
    trunk = A.smin(trunk, g["neck"], 0.03)
    arm = A.smin(g["arm"], g["hand"], 0.020)
    leg = A.smin(g["leg"], g["foot"], 0.018)
    d = A.smin(trunk, arm, 0.018)
    return A.smin(d, leg, 0.030)


def body_sdf(x, y, z):
    """Placeholder body skin SDF (no head), body frame."""
    return _union(body_parts(x, y, z))


def _head_eval(fn, x, y, z, fill=0.5):
    """Evaluate a head-frame SDF only inside the head's box (body frame input)."""
    out = np.full(x.shape, fill)
    m = (z > 1.43) & (np.abs(x) < 0.12) & (y > -0.115) & (y < 0.145)
    if m.any():
        out[m] = fn(x[m], y[m] - HEAD_OFFSET[1], z[m] - HEAD_OFFSET[2])
    return out


NECK_BLEND = (1.500, 1.600)      # z band where the body neck hands over to the head project's head


def _blend_head(h, body, y, z, k=0.016):
    """Body below NECK_BLEND, smooth union with the head above, linear SDF blend in between
    (no crease where the head project's own neck column meets the bible-placed neck)."""
    A = _A()
    u = A.smin(h, body, k)
    w = A.smoothstep(NECK_BLEND[0], NECK_BLEND[1], z)
    face = A.smoothstep(-0.015, -0.040, y) * A.smoothstep(1.520, 1.540, z)   # chin/jaw keep the full union
    w = np.maximum(w, face)
    return (1.0 - w) * body + w * u


def skin_sdf(x, y, z):
    """Head-project skin blended into the placeholder body over NECK_BLEND."""
    A = _A()
    return _blend_head(_head_eval(A.skin_sdf, x, y, z), body_sdf(x, y, z), y, z)


def _shell_offsets(x, y, z):
    """Skin + fat thickness per component (arrays), used to inset the muscle shell."""
    F = SKIN_FAT
    cy = np.interp(z, TORSO_SECTIONS[:, 0], TORSO_SECTIONS[:, 3])
    front = y < cy
    abd = front & (z > 0.95) & (z < 1.24)
    torso = np.where(abd, F["torso_front_abdomen"], np.where(front, F["torso_chest"], F["torso_back"]))
    torso = np.where((z < 0.99) & ~front, F["buttock"], torso)
    t_arm = (np.abs(x) - 0.18) * ARM_D[0] + (z - 1.415) * ARM_D[2]
    arm = np.where(t_arm > 0.29, F["forearm"], F["arm"])
    leg = np.where(z < 0.49, F["shank"], F["thigh"])
    return {"torso": torso, "extras": np.where(z > 1.38, F["shoulder"], torso), "neck": F["neck"],
            "arm": arm, "hand": F["hand"], "leg": leg, "foot": F["foot"]}


def muscle_sdf(x, y, z):
    """Muscle shell: body components inset by skin + fat; the head part is the head project's muscle."""
    A = _A()
    d = _union(body_parts(x, y, z), _shell_offsets(x, y, z))
    return _blend_head(_head_eval(A.muscle_sdf, x, y, z), d, y, z, 0.02)


def shorts_sdf(x, y, z):
    """Inflated pelvis + thighs for the loose shorts (plan D2: 4-8 mm at the seat -> 15 mm at the hem)."""
    A = _A()
    ax = np.abs(x)
    off = np.interp(z, [0.68, 0.80, 0.95, 1.05], [0.015, 0.011, 0.006, 0.004])
    t = _torso(ax, y, z)
    g = _torso_extras(ax, y, z)
    trunk = A.smin(t, np.where(z < 1.0, g, 1.0), 0.02)
    leg = _leg(ax, y, z)
    return A.smin(trunk, leg, 0.035) - off


# ===========================================================================
# Small helpers
# ===========================================================================
def _faces_of(me):
    return [list(p.vertices) for p in me.polygons]


def _obj_to_arrays(obj):
    me = obj.data
    m = obj.matrix_basis                  # matrix_world is stale until the depsgraph updates
    v = gbc.get_verts(me) @ np.array(m.to_3x3()).T + np.array(m.translation)
    return v, _faces_of(me)


def _remove(obj):
    me = obj.data
    bpy.data.objects.remove(obj, do_unlink=True)
    if me is not None and me.users == 0:
        bpy.data.meshes.remove(me)


def _new_mesh_obj(name, verts, faces):
    me = gbc.mesh_from_arrays(name, verts, faces)
    return gbc.new_object(name, me)


def dominant_bone(points):
    """Index into ``RT.BONE_NAMES`` of the strongest analytic weight per point."""
    import rig
    idx, w = rig.weights_at(points)
    return idx[np.arange(len(idx)), np.argmax(w, axis=1)]


def segment_names_for(points, force=None):
    """Skin segment name per point (from the dominant bone), e.g. 'arm_L'."""
    if force is not None:
        return np.array([force] * len(points))
    b = dominant_bone(points)
    return np.array([SG.BONE_SEGMENT[RT.BONE_NAMES[i]] for i in b])


def skin_regions(points, seg_names):
    """Region code per point [RB §2.0] (plan §5.5): scalp, face, eyelid/lip, neck, trunk, limb, palm/sole."""
    A = _A()
    p = np.asarray(points, float)
    hp = p - HEAD_OFFSET
    out = np.full(len(p), SG.REGION_ID["limb"])
    head = seg_names == "head_neck"
    torso = np.isin(seg_names, ["torso", "shorts"])
    # head: face in front of the ears below the brow line, scalp above/behind, neck below the jaw
    hx, hy, hz = np.abs(hp[:, 0]), hp[:, 1], hp[:, 2]
    face = (hy < -0.035 + 0.25 * np.maximum(hz, 0)) & (hz < 0.050) & (hz > -0.115)
    scalp = ~face & (hz > -0.03)
    neck = ~face & ~scalp
    neck |= (hz < -0.10) & ~(hy < -0.06)
    lip_u, lip_l = A.lips_sdf(hx, hy, hz)
    eye_d = np.sqrt((hx - 0.032) ** 2 + (hy + 0.070) ** 2 + (hz - 0.022) ** 2)
    lidlip = (np.minimum(lip_u, lip_l) < 0.002) | ((eye_d < 0.0185) & (hy < -0.074))
    r = np.where(lidlip, SG.REGION_ID["eyelid_lip"],
                 np.where(face, SG.REGION_ID["face"],
                          np.where(scalp, SG.REGION_ID["scalp"], SG.REGION_ID["neck"])))
    out[head] = r[head]
    out[head & (p[:, 2] < 1.52)] = SG.REGION_ID["neck"]
    cy = np.interp(p[:, 2], TORSO_SECTIONS[:, 0], TORSO_SECTIONS[:, 3])
    trunk_r = np.where(p[:, 1] < cy, SG.REGION_ID["trunk_front"], SG.REGION_ID["trunk_back"])
    out[torso] = trunk_r[torso]
    out[torso & (p[:, 2] > 1.47) & (np.abs(p[:, 0]) < 0.08)] = SG.REGION_ID["neck"]
    hand = np.isin(seg_names, ["hand_L", "hand_R"])
    ax = np.abs(p[:, 0])
    rel = np.stack([ax - _WRI[0], p[:, 1] - _WRI[1], p[:, 2] - _WRI[2]], axis=1)
    palm = hand & ((rel @ ARM_NM) > 0.004)
    out[palm] = SG.REGION_ID["palm_sole"]
    foot = np.isin(seg_names, ["foot_L", "foot_R"])
    out[foot & (p[:, 2] < 0.010)] = SG.REGION_ID["palm_sole"]
    return out


def set_skin_codes(obj, code_segment=None, body_segment=None):
    """Write gb_seg/gb_region/gb_derm and the gb_codes UV map for a skin-like mesh (plan §5.5).

    ``code_segment`` forces the segment written into the codes (e.g. 'shorts');
    ``body_segment`` forces the underlying anatomical segment used for regions
    and dermatomes (e.g. 'head_neck' for the whole head mesh).  Returns the
    per-vertex anatomical segment names."""
    v = gbc.get_verts(obj.data)
    under = segment_names_for(v, body_segment)
    names = np.array([code_segment] * len(v)) if code_segment else under
    region = skin_regions(v, under)
    derm = DM.dermatome_v0(v, under)
    seg = np.array([SG.SEGMENT_ID[n] for n in names])
    gbc.point_attr(obj, "gb_seg", seg, 'INT')
    gbc.point_attr(obj, "gb_region", region, 'INT')
    gbc.point_attr(obj, "gb_derm", derm, 'INT')
    gbc.set_codes_uv(obj, seg + SG.REGION_STRIDE * region, derm)
    return under


def face_slots_by_segment(obj, slot_names, seg_to_slot):
    """Per-face material index from the per-vertex segment of the face's vertices (majority)."""
    me = obj.data
    seg = gbc.read_point_attr(obj, "gb_seg", 'INT')
    names = [SG.SEGMENTS[int(s)] for s in seg]
    vslot = np.array([slot_names.index(seg_to_slot(n)) for n in names])
    fs = np.empty(len(me.polygons), dtype=np.int32)
    for i, poly in enumerate(me.polygons):
        vals = vslot[list(poly.vertices)]
        fs[i] = np.bincount(vals).argmax()
    me.polygons.foreach_set("material_index", fs)
    me.update()


def atlas_uv(obj, quick=False):
    """Placeholder atlas UV (Smart UV Project); B1/B2 replace it with planned seams."""
    gg.smart_uv(obj, margin=0.003 if quick else 0.004)


def finish_uvs(obj):
    """Make sure ``atlas`` is UV 0 and ``gb_codes`` UV 1 (create empty codes if missing)."""
    me = obj.data
    if "atlas" not in me.uv_layers:
        me.uv_layers.new(name="atlas")
    if "gb_codes" not in me.uv_layers:
        gbc.set_codes_uv(obj, np.zeros(len(me.vertices)), np.zeros(len(me.vertices)))
    names = [l.name for l in me.uv_layers]
    if names[:2] != ["atlas", "gb_codes"]:
        # rebuild in the right order (UV layers cannot be reordered in place)
        data = {}
        for l in me.uv_layers:
            a = np.empty(len(me.loops) * 2, dtype=np.float32)
            l.data.foreach_get("uv", a)
            data[l.name] = a
        while me.uv_layers:
            me.uv_layers.remove(me.uv_layers[0])
        for n in ["atlas", "gb_codes"] + [n for n in names if n not in ("atlas", "gb_codes")]:
            me.uv_layers.new(name=n).data.foreach_set("uv", data[n])
    gbc.ensure_uv_order(obj)


def tag(obj, layer=None):
    """Custom props exported as glTF extras (plan §5.5)."""
    obj["gb_layer"] = layer or gbc.LAYER_OF.get(obj.name, "other")
    obj["gb_schema"] = 1
    obj["gb_status"] = "placeholder"


# ===========================================================================
# Outer layer: GB_Head + GB_Body on one seam ring, shorts, LOD1
# ===========================================================================
def seam_ring(n=gbc.SEAM_RING_N):
    """Canonical seam ring of the placeholder skin (B2 owns the final ``seam_ring``)."""
    return gg.seam_ring_from_sdf(skin_sdf, SEAM_Z, n, centre_xy=NECK_AXIS_XY, r_max=0.12)


NECK_AXIS_XY = (0.0, 0.012)


def _sdf_object(name, fn, lo, hi, h, project=2):
    me = gg.sdf_mesh(name, fn, lo, hi, h, project=project, remesh=True)
    return gbc.new_object(name, me)


def build_head_body(r, quick=False):
    """GB_Head (above the seam) and GB_Body (below) zipped to the same analytic seam ring."""
    A = _A()
    ring = seam_ring()
    hh, hb = r["head"], r["body"]
    head = _sdf_object("GB_Head", skin_sdf, (-0.118, -0.120, SEAM_Z - 3 * hh), (0.118, 0.150, 1.795), hh)
    gg.decimate_to(head, 29800)
    gg.cut_plane(head.data, SEAM_Z + 0.45 * hh, keep="above")
    gg.zip_to_ring(head, ring, NECK_AXIS_XY, "above")
    body = _sdf_object("GB_Body", skin_sdf, (-0.60, -0.20, -0.004), (0.60, 0.20, SEAM_Z + 3 * hb), hb)
    gg.decimate_to(body, 43700)
    gg.cut_plane(body.data, SEAM_Z - 0.45 * hb, keep="below")
    gg.zip_to_ring(body, ring, NECK_AXIS_XY, "below")
    for o in (head, body):
        o.data.shade_smooth()
    # head: mouth lining faces (inside the closed-mouth surface, in the mouth region) -> slot 1
    c = gbc.face_centres(head.data) - HEAD_OFFSET
    closed = A.skin_sdf(c[:, 0].copy(), c[:, 1].copy(), c[:, 2].copy(), mouth_cavity=False)
    in_mouth = (np.abs(c[:, 0]) < 0.034) & (c[:, 1] > -0.105) & (c[:, 1] < -0.01) & (c[:, 2] > -0.09) & (c[:, 2] < -0.02)
    set_skin_codes(head, body_segment="head_neck")
    gbc.set_material_slots(head, ((closed < -0.0006) & in_mouth).astype(np.int32))
    set_skin_codes(body)
    gbc.set_material_slots(body)
    surf = {"head_neck": "torso", "torso": "torso", "shorts": "torso"}
    face_slots_by_segment(body, list(gbc.MATERIAL_SLOTS["GB_Body"]),
                          lambda n: "GBM_skin_" + surf.get(n, SG.SEGMENT_SURFACE[n]))
    return head, body, ring


def build_shorts(r):
    """GB_Shorts: loose mid-thigh athletic shorts, 1.2 mm solidified cloth (plan D2, §1.2)."""
    h = r["body"]
    obj = _sdf_object("GB_Shorts", shorts_sdf, (-0.26, -0.19, 0.64), (0.26, 0.215, 1.10), h)
    gg.cut_plane(obj.data, 1.045, keep="below")          # waistband top (1.02-1.05)
    gg.cut_plane(obj.data, 0.680, keep="above")          # hem at mid-thigh
    gg.decimate_to(obj, 1900)
    mod = obj.modifiers.new("gb_solidify", 'SOLIDIFY')
    mod.thickness = 0.0012
    mod.offset = -1.0
    mod.use_even_offset = True
    gg.apply_modifier(obj, mod)
    obj.data.shade_smooth()
    set_skin_codes(obj, code_segment="shorts")
    gbc.set_material_slots(obj)
    return obj


def build_muscle_shell(r):
    """GB_MuscleShell: closed shell at skin + fat depth [RB §7.6]; 6 surfaces by segment."""
    obj = _sdf_object("GB_MuscleShell", muscle_sdf, (-0.60, -0.20, 0.0), (0.60, 0.20, 1.79), r["muscle"])
    gg.decimate_to(obj, 23800)
    set_skin_codes(obj)
    gbc.set_material_slots(obj)
    surf = {"head_neck": "head", "shorts": "torso"}
    face_slots_by_segment(obj, list(gbc.MATERIAL_SLOTS["GB_MuscleShell"]),
                          lambda n: "GBM_muscle_" + surf.get(n, SG.SEGMENT_SURFACE[n]))
    return obj


# ===========================================================================
# Eyes, eye FX, mouth, brow/lash cards (head project parts, body frame)
# ===========================================================================
def _rigid(n, bone):
    return np.full(n, RT.BONE_INDEX[bone], dtype=np.int32)


def build_eyes():
    """GB_Eye_L/R: the head project's eyeballs (cornea bulge), rigid to eye_L/R."""
    A = _A()
    out = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        name = f"GB_Eye_{side}"
        gbc.remove_object(name)
        c = gbc.head_to_body(A.EYE_C * np.array([sx, 1.0, 1.0]))
        tmp = A.build_eye("_gb_eye_tmp", tuple(c), bpy.context.scene.collection)
        v, f = _obj_to_arrays(tmp)
        _remove(tmp)
        n = len(v)
        obj = gg.object_from_parts(name, [gg.part(v, f, 0, gb_rigid_bone=_rigid(n, "eye_" + side))])
        gg.decimate_to(obj, 1900)                  # plan §4.1: eyes + eye FX 5,000 tris in total
        n = len(obj.data.vertices)
        gbc.set_codes_uv(obj, np.full(n, SG.REGION_STRIDE * SG.REGION_ID["eyelid_lip"]), np.zeros(n))
        out[name] = obj
    return out


def _eye_dir(u, v, sx):
    """Unit direction from the eye centre for horizontal angle u (lateral +) and elevation v."""
    return np.stack([sx * np.cos(v) * np.sin(u), -np.cos(v) * np.cos(u), np.sin(v)], axis=-1)


def build_eye_fx():
    """GB_EyeFX_L/R: tearline strip along the lower lid margin (slot 0) and an occlusion shell (slot 1)."""
    A = _A()
    out = {}
    for side, sx in (("L", 1.0), ("R", -1.0)):
        c = gbc.head_to_body(A.EYE_C * np.array([sx, 1.0, 1.0]))
        # tearline: 24 x 2 strip between the lid margin (r 12.9 mm) and the globe (r 12.15 mm)
        u = np.linspace(A.LID_UM + 0.08, A.LID_UL - 0.08, 24)
        _t, _st, up, lo = A._lid_curves(u)
        d = _eye_dir(u, lo + 0.03, sx)
        tv = np.concatenate([c + 0.0129 * d, c + 0.01215 * d])
        n = len(u)
        tf = [[i, i + 1, n + i + 1, n + i] for i in range(n - 1)]
        # occlusion: shell cap r 12.4 mm around the gaze, 50 deg half-angle (12 x 24 grid)
        th = np.radians(np.linspace(0.0, 50.0, 12))[1:]
        ph = np.linspace(0.0, 2 * np.pi, 24, endpoint=False)
        T, PH = np.meshgrid(th, ph, indexing="ij")
        dirs = np.stack([np.sin(T) * np.cos(PH), -np.cos(T), np.sin(T) * np.sin(PH)], axis=-1).reshape(-1, 3)
        ov = np.vstack([c + np.array([0.0, -0.0124, 0.0])[None] * 1.0, c + 0.0124 * dirs])
        # the cap bulges over the cornea: push the centre part out to clear the cornea (5.82 + 7.5 mm)
        dist = np.linalg.norm(ov - c, axis=1)
        dd = (ov - c) / dist[:, None]
        corn = np.clip((dd @ np.array([0.0, -1.0, 0.0]) - np.cos(np.radians(30))) / (1 - np.cos(np.radians(30))), 0, 1)
        ov = c + dd * (0.0124 + 0.0016 * corn)[:, None]
        m = len(ph)
        of = [[0, 1 + (k + 1) % m, 1 + k] for k in range(m)]
        for i in range(len(th) - 1):
            for k in range(m):
                a0, a1 = 1 + i * m + k, 1 + i * m + (k + 1) % m
                of.append([a0, a1, a1 + m, a0 + m])
        n_o = len(ov)
        parts = [gg.part(tv, tf, 0, gb_rigid_bone=_rigid(len(tv), "head")),
                 gg.part(ov, of, 1, gb_rigid_bone=_rigid(n_o, "eye_" + side))]
        name = f"GB_EyeFX_{side}"
        obj = gg.object_from_parts(name, parts)
        nv = len(obj.data.vertices)
        gbc.set_codes_uv(obj, np.full(nv, SG.REGION_STRIDE * SG.REGION_ID["eyelid_lip"]), np.zeros(nv))
        out[name] = obj
    return out


def build_mouth(r):
    """GB_Mouth: the head project's teeth (slot 0), gums (1) and tongue (2) in the body frame."""
    A = _A()
    col = bpy.context.scene.collection
    parts = []
    for upper in (True, False):
        tmp = A.build_teeth("_gb_teeth_tmp", upper, col, h=r["mouth"])
        v, f = _obj_to_arrays(tmp)
        _remove(tmp)
        parts.append(gg.part(v + HEAD_OFFSET, f, 0, gb_rigid_bone=_rigid(len(v), "head" if upper else "jaw")))
    gh = max(r["mouth"] * 1.4, 0.0011)
    for upper in (True, False):
        v, q = gg.sdf_arrays(lambda x, y, z, u=upper: A.gum_sdf(x, y, z, u), (-0.036, -0.098, -0.084),
                             (0.036, -0.024, -0.030), gh)
        parts.append(gg.part(v + HEAD_OFFSET, q, 1, gb_rigid_bone=_rigid(len(v), "head" if upper else "jaw")))
    v, q = gg.sdf_arrays(A.tongue_sdf, (-0.030, -0.095, -0.080), (0.030, -0.010, -0.045), gh)
    parts.append(gg.part(v + HEAD_OFFSET, q, 2, gb_rigid_bone=_rigid(len(v), "tongue")))
    obj = gg.object_from_parts("GB_Mouth", parts)
    gg.decimate_to(obj, 8400)
    nv = len(obj.data.vertices)
    gbc.set_codes_uv(obj, np.full(nv, SG.REGION_STRIDE * SG.REGION_ID["eyelid_lip"]), np.zeros(nv))
    return obj


def _skin_point_front(x, z, y0=-0.13, y1=-0.02):
    """Head-frame y where the skin surface is met travelling +y at (x, z) (bisection)."""
    A = _A()
    lo, hi = np.full(len(x), y0), np.full(len(x), y1)
    for _ in range(30):
        mid = 0.5 * (lo + hi)
        inside = A.skin_sdf(x.copy(), mid.copy(), z.copy()) < 0
        hi = np.where(inside, mid, hi)
        lo = np.where(inside, lo, mid)
    return 0.5 * (lo + hi)


def build_brow_lash():
    """GB_BrowLash: alpha-card strips for the brows and the upper/lower lashes (B2 converts the
    head project's hair curves into the final cards)."""
    A = _A()
    parts = []
    for sx in (1.0, -1.0):
        # brows: 14 x 2 strip lying on the skin, 4 mm tall, 0.4 mm off the surface
        xs = np.linspace(0.008, 0.052, 14)
        zs = np.array([A.BROW_Z(q) for q in xs]) - 0.001
        ys = _skin_point_front(xs, zs) - 0.0004
        base = np.stack([sx * xs, ys, zs], axis=1)
        top = base + np.array([0.0, -0.0012, 0.0036])
        v = np.vstack([base, top]) + HEAD_OFFSET
        n = len(xs)
        f = [[i, i + 1, n + i + 1, n + i] if sx > 0 else [i, n + i, n + i + 1, i + 1] for i in range(n - 1)]
        parts.append(gg.part(v, f, 0, gb_rigid_bone=_rigid(len(v), "head")))
        # lashes along the lid margins, tilted out and up (upper 9 mm, lower 5 mm)
        eye = A.EYE_C * np.array([sx, 1.0, 1.0])
        u = np.linspace(A.LID_UM + 0.15, A.LID_UL - 0.10, 16)
        _t, _st, up, lo = A._lid_curves(u)
        for vv, length, lift, bone in ((up, 0.0075, 0.7, "lid_upper_"), (lo, 0.0040, -0.5, "lid_lower_")):
            d = _eye_dir(u, vv, sx)
            b = eye + (A.LID_R + 0.0003) * d
            tipdir = d + np.array([0.0, 0.0, lift])
            tipdir /= np.linalg.norm(tipdir, axis=1, keepdims=True)
            t = b + length * tipdir
            v = np.vstack([b, t]) + HEAD_OFFSET
            n = len(u)
            f = [[i, i + 1, n + i + 1, n + i] if sx > 0 else [i, n + i, n + i + 1, i + 1] for i in range(n - 1)]
            side = "L" if sx > 0 else "R"
            parts.append(gg.part(v, f, 0, gb_rigid_bone=_rigid(len(v), bone + side)))
    obj = gg.object_from_parts("GB_BrowLash", parts)
    nv = len(obj.data.vertices)
    gbc.set_codes_uv(obj, np.full(nv, SG.REGION_STRIDE * SG.REGION_ID["face"]), np.zeros(nv))
    return obj


# ===========================================================================
# Skeleton (simplified but complete: every piece id of gb_data.bones.BONE_PIECES)
# ===========================================================================
def _vert_bone(z):
    """Rigid bone of a spine piece at height z (matches the rig's trunk segmentation)."""
    for zz, b in ((1.490, "neck"), (1.353, "upper_chest"), (1.212, "chest"), (1.027, "spine")):
        if z >= zz:
            return b
    return "hips"


def _vertebra_sdf(row):
    """Vertebral body + neural arch + spinous and transverse processes from the RB §7.3 row."""
    A = _A()
    lvl = row["level"]
    y, z = row["y"], row["z"]
    h, w, dp = row["body_h_mm"] / 1000, row["body_w_mm"] / 1000, row["body_d_mm"] / 1000
    cap, cw = row["canal_ap_mm"] / 1000, row["canal_w_mm"] / 1000
    yc = max(row["cord_y"], y + 0.5 * dp + 0.5 * cap - 0.001)
    sp = row["spinous_dy_mm"] / 1000
    region = lvl[0]
    drop = {"C": 0.006, "T": 0.028, "L": 0.004}[region]
    tp_len = {"C": 0.010, "T": 0.020, "L": 0.024}[region]
    arch_h = min(0.35 * h, 0.0055) if lvl != "C1" else 0.005

    def fn(x, yy, zz):
        ax = np.abs(x)
        if lvl == "C1":                                      # atlas: a ring (no body)
            ring = np.maximum(A.ellipse2(ax, yy - yc, 0.5 * w - 0.004, 0.5 * dp),
                              -A.ellipse2(ax, yy - yc, 0.5 * cw, 0.5 * cap))
            d = A.extrude(ring, zz - z, 0.5 * h, 0.002)
        else:
            d = A.extrude(A.ellipse2(ax, yy - y, 0.5 * w, 0.5 * dp), zz - z, 0.5 * h, 0.0025)
            ring = np.maximum(A.ellipse2(ax, yy - yc, 0.5 * cw + 0.0042, 0.5 * cap + 0.0045),
                              -A.ellipse2(ax, yy - yc, 0.5 * cw, 0.5 * cap))
            ring = np.maximum(ring, (y + 0.5 * dp - 0.002) - yy)       # arch only behind the body
            d = A.smin(d, A.extrude(ring, zz - z, arch_h, 0.0015), 0.002)
        if sp > 0:
            spin = A.sd_capsule(ax, yy, zz, (0.0, yc + 0.5 * cap + 0.002, z), (0.0, y + sp - 0.004, z - drop),
                                0.0042, 0.0032)
            d = A.smin(d, spin, 0.003)
        tp = A.sd_capsule(ax, yy, zz, (0.5 * cw, yc, z), (0.5 * cw + 0.004 + tp_len, yc + 0.006, z + 0.002),
                          0.0035, 0.003)
        return A.smin(d, tp, 0.003)
    half = max(0.5 * w, 0.5 * cw + 0.005 + tp_len) + 0.01
    lo = (-half, y - 0.5 * dp - 0.01, z - 0.5 * h - drop - 0.012)
    hi = (half, y + sp + 0.01, z + 0.5 * h + 0.012)
    return fn, lo, hi


def _disc_sdf(a, b):
    """Intervertebral disc between the bodies of rows a (above) and b (below)."""
    A = _A()
    za = a["z"] - 0.5 * a["body_h_mm"] / 1000
    zb = b["z"] + 0.5 * b["body_h_mm"] / 1000
    zc, half = 0.5 * (za + zb), max(0.5 * (za - zb) + 0.0004, 0.0012)
    yc = 0.5 * (a["y"] + b["y"])
    w = 0.5 * (a["body_w_mm"] + b["body_w_mm"]) / 1000 * 0.96
    dp = 0.5 * (a["body_d_mm"] + b["body_d_mm"]) / 1000 * 0.96

    def fn(x, y, z):
        return A.extrude(A.ellipse2(np.abs(x), y - yc, 0.5 * w, 0.5 * dp), z - zc, half, 0.001)
    return fn, (-0.5 * w - 0.006, yc - 0.5 * dp - 0.006, zc - half - 0.006), \
        (0.5 * w + 0.006, yc + 0.5 * dp + 0.006, zc + half + 0.006)


def _sacrum_sdf():
    A = _A()
    top, tip = np.array(VT.SACRUM["top_c"]), np.array(VT.SACRUM["tip"])
    axis = tip - top
    L = np.linalg.norm(axis)
    U = axis / L
    Wd = np.cross(np.array([1.0, 0.0, 0.0]), U)          # depth direction (toward the back)

    def fn(x, y, z):
        px, py, pz = x - top[0], y - top[1], z - top[2]
        s = px * U[0] + py * U[1] + pz * U[2]
        dep = px * Wd[0] + py * Wd[1] + pz * Wd[2]
        t = np.clip(s / L, 0.0, 1.0)
        hw = 0.052 * (1.0 - 0.72 * t)
        hd = 0.017 * (1.0 - 0.55 * t)
        dep = dep - 0.010 * np.sin(np.pi * t)            # concave front (sacral curve)
        d2 = gg.superellipse2(np.abs(px), dep, hw, hd, 2.6)
        return np.maximum(d2, np.maximum(-s, s - L))
    coccyx = [tip, np.array((0.0, 0.048, 0.915)), np.array(VT.COCCYX_TIP)]

    def fn2(x, y, z):
        return A.smin(fn(x, y, z), A.sd_polyline(x, y, z, coccyx, [0.007, 0.005, 0.003])[0], 0.003)
    return fn, fn2


def _ribcage_parts(h):
    """Ribs 1-12 and costal cartilages 1-10 (left), swept through the RB §7.3 rib table."""
    parts = []
    for n in range(1, 13):
        pts = np.array(RB_.rib_points(n))
        hmm, tmm = RB_.RIB_SECTION_MM.get(n, RB_.RIB_SECTION_MM["default"])
        radii = np.array([[0.5 * tmm / 1000, 0.5 * hmm / 1000]] * len(pts))
        radii[0] *= 0.8
        out_fn = lambda P: np.stack([P[:, 0], P[:, 1] - 0.02, np.zeros(len(P))], axis=1)
        v, f, _t = gg.sweep(pts, radii, sides=8, step=max(0.006, 2.5 * h), normal_fn=out_fn)
        parts.append(("rib%d" % n, v, f, 0, "upper_chest" if n <= 4 else "chest"))
        cp = RB_.cartilage_points(n)
        if cp and n <= 10:
            cmm = RB_.CARTILAGE_SECTION_MM
            v, f, _t = gg.sweep(np.array(cp), [[0.5 * cmm[1] / 1000, 0.5 * cmm[0] / 1000]] * 2, sides=8,
                                step=0.006, smooth=False, normal_fn=out_fn)
            parts.append(("costal_cartilage%d" % n, v, f, 1, "upper_chest" if n <= 4 else "chest"))
    return parts


def _sternum_sdf():
    A = _A()
    segs = []
    for key, thick_back in (("manubrium", 0.015), ("body", 0.011), ("xiphoid", 0.0045)):
        s = RB_.STERNUM[key]
        a, b = np.array(s["top"]), np.array(s["bottom"])
        U, V, W = gg.orthonormal(b - a, (1.0, 0.0, 0.0))
        wmax = max(s["width_cm"]) / 100
        c = 0.5 * (a + b) - W * 0.0 + np.array([0.0, 0.5 * thick_back, 0.0])
        segs.append((c, (0.5 * np.linalg.norm(b - a), 0.5 * wmax, 0.5 * thick_back), (U, V, W)))

    def fn(x, y, z):
        d = None
        for c, half, axes in segs:
            e = gg.sd_obox(x, y, z, c, half, axes, rnd=min(half) * 0.8)
            d = e if d is None else A.smin(d, e, 0.004)
        return d
    return fn


def _long_bone_sdfs():
    """Left limb and girdle bones as SDFs: name -> (fn, lo, hi, rigid bone)."""
    A = _A()
    S, H, F, K, FT, P = BN.SCAPULA, BN.HUMERUS, BN.FEMUR, BN.KNEE_LEG, BN.FOOT_BONES, BN.PELVIS
    out = {}

    def clav(x, y, z):
        return A.sd_polyline(x, y, z, BN.CLAVICLE_WAYPOINTS, [0.0105, 0.0068, 0.0062, 0.0085])[0]
    out["clavicle"] = (clav, (0.0, -0.075, 1.425), (0.19, 0.03, 1.49), "clavicle_L")

    def scap(x, y, z):
        plate = gg.sd_plate(x, y, z, [S["superior_angle"], S["inferior_angle"], (0.140, 0.040, 1.405)],
                            0.0035, rim=0.0015)
        spine = A.sd_polyline(x, y, z, [S["spine_root"], S["acromion_posterior_angle"], S["acromion_tip"]],
                              [0.004, 0.006, 0.0065])[0]
        glen = gg.sd_oellipsoid(x, y, z, S["glenoid_centre"], (0.008, 0.014, 0.019),
                                gg.orthonormal((0.94, -0.34, 0.0), (0.0, 0.0, 1.0)))
        cor = A.sd_capsule(x, y, z, (0.140, 0.012, 1.428), S["coracoid_tip"], 0.006, 0.005)
        lat = A.sd_capsule(x, y, z, (0.145, 0.035, 1.395), S["inferior_angle"], 0.005, 0.004)
        d = A.smin(plate, spine, 0.006)
        d = A.smin(d, glen, 0.006)
        d = A.smin(d, lat, 0.004)
        return A.smin(d, cor, 0.004)
    out["scapula"] = (scap, (0.05, -0.04, 1.30), (0.23, 0.13, 1.50), "clavicle_L")

    elb = np.array(H["elbow_centre"])

    def hum(x, y, z):
        head_ = A.sd_sphere(x, y, z, H["head_centre"], 0.024)
        shaft = A.sd_polyline(x, y, z, [(0.195, 0.020, 1.388), (0.255, 0.020, 1.285), (0.318, 0.020, 1.180)],
                              [0.0135, 0.0105, 0.0120])[0]
        dist = gg.sd_oellipsoid(x, y, z, elb + np.array([0.0, 0.0, 0.004]), (0.0315, 0.013, 0.014),
                                gg.orthonormal(ARM_LAT, (0.0, 1.0, 0.0)))
        return A.smin(A.smin(head_, shaft, 0.012), dist, 0.012)
    out["humerus"] = (hum, (0.14, -0.03, 1.13), (0.37, 0.07, 1.45), "upper_arm_L")

    def radius(x, y, z):
        return A.sd_polyline(x, y, z, [(0.330, 0.008, 1.150), (0.395, 0.008, 1.040), (0.457, 0.006, 0.940)],
                             [0.0095, 0.0070, 0.0125])[0]
    out["radius"] = (radius, (0.30, -0.02, 0.91), (0.49, 0.04, 1.18), "forearm_L")

    def ulna(x, y, z):
        return A.sd_polyline(x, y, z, [(0.315, 0.032, 1.190), (0.330, 0.030, 1.160), (0.400, 0.032, 1.040),
                                       (0.459, 0.034, 0.938)], [0.0105, 0.0095, 0.0068, 0.0070])[0]
    out["ulna"] = (ulna, (0.29, 0.0, 0.91), (0.49, 0.06, 1.22), "forearm_L")

    def hand(x, y, z):
        HB = BN.HAND_BONES
        axes = (ARM_D, np.array([0.0, 1.0, 0.0]), ARM_NM)
        d = gg.sd_obox(x, y, z, HB["carpal_centre"], (0.013, 0.025, 0.009), axes, rnd=0.006)
        for i, (y0, L, r0, r1, sb) in enumerate(FINGERS):
            P = _finger_polyline(y0, L, sb)
            mc0 = np.array(HB["carpal_centre"]) + 0.012 * ARM_D + np.array([0.0, (y0 - 0.02) * 0.6, 0.0])
            d = A.smin(d, A.sd_capsule(x, y, z, mc0, P[0], 0.0045, 0.005), 0.003)
            d = A.smin(d, A.sd_polyline(x, y, z, P, [0.0052, 0.0045, 0.0040, 0.0034])[0], 0.002)
        d = A.smin(d, A.sd_polyline(x, y, z, np.array(THUMB), [0.006, 0.0048, 0.0036])[0], 0.003)
        return d
    out["hand"] = (hand, (0.43, -0.05, 0.74), (0.58, 0.08, 0.95), "hand_L")

    def hip(x, y, z):
        wing1 = gg.sd_plate(x, y, z, [P["asis"], P["iliac_crest_top"], P["psis"]], 0.004, rim=0.002)
        wing2 = gg.sd_plate(x, y, z, [P["asis"], P["psis"], (0.080, 0.010, 0.950)], 0.006, rim=0.002)
        crest = A.sd_polyline(x, y, z, [P["asis"], P["iliac_tubercle"], P["iliac_crest_top"],
                                        (0.095, 0.060, 1.058), P["psis"]], [0.006, 0.008, 0.007, 0.007, 0.007])[0]
        ac = np.array(P["acetabulum_centre"])
        cup = np.maximum(A.sd_sphere(x, y, z, ac, 0.031), -A.sd_sphere(x, y, z, ac, 0.0258))
        cup = np.maximum(cup, (x - ac[0]) * 0.8 + (ac[1] - y) * 0.2 - 0.004)       # open laterally
        pubis = A.sd_polyline(x, y, z, [(0.070, -0.035, 0.905), P["pubic_tubercle"], P["symphysis_centre"]],
                              [0.010, 0.008, 0.009])[0]
        isch = A.sd_polyline(x, y, z, [(0.068, 0.012, 0.895), P["ischial_spine"], P["ischial_tuberosity"],
                                       (0.030, -0.030, 0.850), P["symphysis_lower"]],
                             [0.011, 0.008, 0.012, 0.006, 0.006])[0]
        d = A.smin(wing1, wing2, 0.01)
        d = A.smin(d, crest, 0.006)
        d = A.smin(d, cup, 0.008)
        d = A.smin(d, pubis, 0.006)
        return A.smin(d, isch, 0.006)
    out["hip_bone"] = (hip, (-0.01, -0.09, 0.82), (0.17, 0.11, 1.09), "hips")

    def femur(x, y, z):
        d = A.sd_sphere(x, y, z, F["head_centre"], 0.0245)
        d = A.smin(d, A.sd_capsule(x, y, z, F["head_centre"], (0.130, -0.004, 0.900), 0.016, 0.017), 0.008)
        d = A.smin(d, A.sd_ellipsoid(x, y, z, (0.140, 0.004, 0.905), (0.017, 0.020, 0.026)), 0.008)
        d = A.smin(d, A.sd_ellipsoid(x, y, z, F["lesser_trochanter"], (0.009, 0.009, 0.012)), 0.006)
        d = A.smin(d, A.sd_polyline(x, y, z, [(0.130, 0.002, 0.890), (0.108, 0.012, 0.700), (0.093, 0.018, 0.540)],
                                    [0.0150, 0.0138, 0.0170])[0], 0.010)
        for dx in (-0.021, 0.021):
            d = A.smin(d, A.sd_ellipsoid(x, y, z, (0.092 + dx, 0.024, 0.506), (0.019, 0.030, 0.024)), 0.010)
        return d
    out["femur"] = (femur, (0.04, -0.05, 0.46), (0.18, 0.07, 0.95), "thigh_L")

    def patella(x, y, z):
        return A.sd_ellipsoid(x, y, z, K["patella_centre"], (0.0255, 0.0115, 0.0250))
    out["patella"] = (patella, (0.055, -0.055, 0.46), (0.125, -0.015, 0.535), "shin_L")

    def tibia(x, y, z):
        d = A.sd_ellipsoid(x, y, z, (0.092, 0.028, 0.466), (0.039, 0.026, 0.017))
        d = A.smin(d, A.sd_ellipsoid(x, y, z, K["tibial_tuberosity"] + np.array([0.0, 0.010, 0.0]),
                                     (0.012, 0.012, 0.018)), 0.008)
        d = A.smin(d, A.sd_polyline(x, y, z, [(0.092, 0.026, 0.450), (0.093, 0.030, 0.300), (0.092, 0.044, 0.110)],
                                    [0.0165, 0.0125, 0.0135])[0], 0.012)
        d = A.smin(d, A.sd_ellipsoid(x, y, z, (0.088, 0.046, 0.100), (0.022, 0.019, 0.014)), 0.008)
        return A.smin(d, A.sd_capsule(x, y, z, (0.075, 0.045, 0.100), K["medial_malleolus_tip"], 0.0075, 0.0055),
                      0.005)
    out["tibia"] = (tibia, (0.04, -0.03, 0.05), (0.14, 0.08, 0.50), "shin_L")

    def fibula(x, y, z):
        return A.sd_polyline(x, y, z, [K["fibular_head"], (0.126, 0.048, 0.300), (0.130, 0.058, 0.110),
                                       K["lateral_malleolus_tip"]], [0.0095, 0.0060, 0.0070, 0.0065])[0]
    out["fibula"] = (fibula, (0.10, 0.01, 0.035), (0.155, 0.08, 0.47), "shin_L")

    def foot(x, y, z):
        d = A.sd_ellipsoid(x, y, z, (0.095, 0.052, 0.078), (0.018, 0.026, 0.015))
        d = A.smin(d, gg.sd_oellipsoid(x, y, z, (0.096, 0.066, 0.040), (0.036, 0.020, 0.021),
                                       gg.orthonormal(FT["axis"], (1.0, 0.0, 0.0))), 0.008)
        d = A.smin(d, A.sd_ellipsoid(x, y, z, FT["midfoot_centre"], (0.030, 0.028, 0.015)), 0.008)
        mt1, mt5 = np.array(FT["mtp1"]), np.array(FT["mtp5"])
        tip2 = np.array(FT["toe2_tip"])
        for k in range(5):
            t = k / 4.0
            head_ = mt1 + t * (mt5 - mt1)
            base = np.array((0.090 + 0.045 * t, -0.022 + 0.012 * t, 0.042))
            d = A.smin(d, A.sd_capsule(x, y, z, base, head_, 0.0055, 0.0052), 0.003)
            tip = head_ + np.array(FT["axis"]) * (0.062 - 0.026 * t)          # toes point along the foot axis
            tip[2] = 0.010
            d = A.smin(d, A.sd_capsule(x, y, z, head_, tip, 0.0055 if k == 0 else 0.0042, 0.0035), 0.002)
        return d
    out["foot"] = (foot, (0.05, -0.17, -0.005), (0.19, 0.12, 0.11), "foot_L")
    return out


def _piece_part(name, v, f, slot, rigid):
    """A skeleton part with its piece id / bone class codes and rigid bone."""
    pid = BN.BONE_PIECE_ID[name]
    cls = BN.BONE_PIECE_CLASS[name]
    n = len(v)
    rig_arr = rigid if isinstance(rigid, np.ndarray) else _rigid(n, rigid)
    return gg.part(v, f, slot, gb_piece=np.full(n, pid), gb_class=np.full(n, cls), gb_rigid_bone=rig_arr)


def _mirror_bone_name(b):
    return b[:-2] + "_R" if b.endswith("_L") else b


def skeleton_parts(r):
    """All skeleton parts (list of part dicts) - also the source of the fracture variants."""
    A = _A()
    h = r["bone"]
    parts = []
    # skull and mandible: the head project's bones
    v, q = gg.sdf_arrays(A.skull_sdf, *A.SKULL_BOX, max(h, 0.0024))
    parts.append(_piece_part("skull", v + HEAD_OFFSET, q, 0, "head"))
    v, q = gg.sdf_arrays(A.jaw_sdf, *A.JAW_BOX, max(0.6 * h, 0.0016))
    parts.append(_piece_part("mandible", v + HEAD_OFFSET, q, 0, "jaw"))
    # spine
    rows = VT.VERTEBRAE
    for row in rows:
        if row["level"] == "S1":
            continue
        fn, lo, hi = _vertebra_sdf(row)
        v, q = gg.sdf_arrays(fn, lo, hi, min(h, 0.0022))
        parts.append(_piece_part(row["level"].lower(), v, q, 0, _vert_bone(row["z"])))
    for a, b in zip(rows[1:-1], rows[2:]):
        fn, lo, hi = _disc_sdf(a, b)
        v, q = gg.sdf_arrays(fn, lo, hi, min(h, 0.0016))
        parts.append(_piece_part(f"disc_{a['level'].lower()}_{b['level'].lower()}", v, q, 1,
                                 _vert_bone(0.5 * (a["z"] + b["z"]))))
    sac, sac_cox = _sacrum_sdf()
    v, q = gg.sdf_arrays(sac, (-0.06, -0.01, 0.90), (0.06, 0.08, 1.03), h)
    parts.append(_piece_part("sacrum", v, q, 0, "hips"))

    def cox(x, y, z):
        return A.sd_polyline(x, y, z, [np.array(VT.SACRUM["tip"]), (0.0, 0.048, 0.915), VT.COCCYX_TIP],
                             [0.0065, 0.0050, 0.0030])[0]
    v, q = gg.sdf_arrays(cox, (-0.015, 0.025, 0.895), (0.015, 0.065, 0.935), min(h, 0.0016))
    parts.append(_piece_part("coccyx", v, q, 0, "hips"))
    v, q = gg.sdf_arrays(_sternum_sdf(), (-0.04, -0.12, 1.25), (0.04, -0.03, 1.47), min(h, 0.002))
    parts.append(_piece_part("sternum", v, q, 0, "upper_chest"))
    # ribs and cartilages, limb bones: left, then mirrored
    left = []
    for name, v, f, slot, bone in _ribcage_parts(h):
        left.append((name, v, f, slot, bone))
    for name, (fn, lo, hi, bone) in _long_bone_sdfs().items():
        v, q = gg.sdf_arrays(fn, lo, hi, h)
        if name == "hand":                                   # phalanges follow the finger/thumb bones
            rb = np.full(len(v), RT.BONE_INDEX["hand_L"], dtype=np.int32)
            rel = v - _WRI
            along = rel @ ARM_D
            rb[along > 0.085] = RT.BONE_INDEX["fingers_L"]
            th = np.linalg.norm(v - THUMB[1], axis=1) < 0.028
            rb[th & (v[:, 1] < 0.0)] = RT.BONE_INDEX["thumb_L"]
            left.append((name, v, q, 0, rb))
        elif name == "foot":
            rb = np.full(len(v), RT.BONE_INDEX["foot_L"], dtype=np.int32)
            rb[(v[:, 1] < -0.080)] = RT.BONE_INDEX["toes_L"]
            left.append((name, v, q, 0, rb))
        else:
            left.append((name, v, q, 0, bone))
    for name, v, f, slot, bone in left:
        pl = _piece_part(f"{name}_L", v, f, slot, bone)
        parts.append(pl)
        pr = gg.mirror_part(pl)
        pr["attrs"]["gb_piece"] = ("INT", np.full(len(v), BN.BONE_PIECE_ID[f"{name}_R"]))
        rb = pl["attrs"]["gb_rigid_bone"][1]
        pr["attrs"]["gb_rigid_bone"] = ("INT", np.array([RT.BONE_INDEX[_mirror_bone_name(RT.BONE_NAMES[i])]
                                                          for i in rb], dtype=np.int32))
        parts.append(pr)
    return parts


def _codes_from_attrs(obj, u_attr, v_attr):
    u = gbc.read_point_attr(obj, u_attr, 'INT')
    v = gbc.read_point_attr(obj, v_attr, 'INT')
    gbc.set_codes_uv(obj, u, v)


def build_skeleton(r):
    """GB_Skeleton: every bone piece (piece id in UV2.x, class in UV2.y), rigid per piece."""
    parts = skeleton_parts(r)
    obj = gg.object_from_parts("GB_Skeleton", parts)
    gg.decimate_to(obj, 35500)
    _codes_from_attrs(obj, "gb_piece", "gb_class")
    return obj, parts


def build_fracture_variants(parts):
    """GB_Frac_*: split copies of the intact pieces (fragments are loose islands).  B3 replaces
    them with Voronoi variants (skull 20-80 fragments, long bones simple/comminuted)."""
    out = {}
    by_piece = {}
    inv = {v: k for k, v in BN.BONE_PIECE_ID.items()}
    for p in parts:
        pid = int(p["attrs"]["gb_piece"][1][0])
        by_piece[inv[pid]] = p
    rng = gbc.rng("placeholder")
    specs = [("GB_Frac_Skull_L", "skull", (1.0, 0.0, 0.3)), ("GB_Frac_Skull_R", "skull", (-1.0, 0.0, 0.3)),
             ("GB_Frac_Skull_T", "skull", (0.0, 0.0, 1.0))]
    for bone, pieces in (("Humerus", ("humerus",)), ("RadUlna", ("radius", "ulna")), ("Femur", ("femur",)),
                         ("Tibia", ("tibia",))):
        for side in ("L", "R"):
            for kind in ("simple", "comminuted"):
                specs.append((f"GB_Frac_{bone}_{side}_{kind}", tuple(f"{p}_{side}" for p in pieces), kind))
    for name, src, how in specs:
        srcs = (src,) if isinstance(src, str) else src
        fparts = []
        for s in srcs:
            p = by_piece[s]
            v = np.asarray(p["verts"])
            faces = np.array([f for f in p["faces"]], dtype=object)
            fc = np.array([v[f].mean(axis=0) for f in p["faces"]])
            if s == "skull":
                # 24 Voronoi cells, seeds biased toward the exit direction
                d = np.array(how, float) / np.linalg.norm(how)
                c = v.mean(axis=0)
                seeds = c + rng.normal(0.0, 0.045, (24, 3)) + 0.05 * d
                cell = np.argmin(((fc[:, None, :] - seeds[None]) ** 2).sum(-1), axis=1)
            else:
                lo, hi = v[:, 2].min(), v[:, 2].max()
                if how == "simple":
                    cut = lo + 0.5 * (hi - lo)
                    cell = (fc[:, 2] > cut + 0.25 * (fc[:, 0] - fc[:, 0].mean())).astype(int)
                else:
                    zc = lo + 0.5 * (hi - lo)
                    seeds = np.column_stack([np.full(10, v[:, 0].mean()), np.full(10, v[:, 1].mean()),
                                             zc + rng.uniform(-0.04, 0.04, 10)]) + rng.normal(0, 0.008, (10, 3))
                    cell = np.argmin(((fc[:, None, :] - seeds[None]) ** 2).sum(-1), axis=1)
                    cell = np.where(np.abs(fc[:, 2] - zc) > 0.06, np.where(fc[:, 2] > zc, 100, 101), cell)
            q = dict(p)
            q["attrs"] = dict(p["attrs"])
            q["face_cell"] = cell
            fparts.append(q)
        obj = gg.object_from_parts(name, fparts)
        cells = np.concatenate([q["face_cell"] + 1000 * i for i, q in enumerate(fparts)])
        gg.split_pieces(obj.data, cells)
        gg.decimate_to(obj, 2400 if "Skull" not in name else 6400)   # plan §4.1: <= 60k in total
        _codes_from_attrs(obj, "gb_piece", "gb_class")
        tag(obj)
        out[name] = obj
    return out


# ===========================================================================
# Brain, organs, cord, vessels
# ===========================================================================
def build_brain(r):
    """GB_Brain: the head project's brain (gyri, cerebellum, stem); UV2 = (region id, sulcus depth)."""
    import neuro
    A = _A()
    v, q = gg.sdf_arrays(A.brain_sdf, *A.BRAIN_BOX, r["brain"])
    obj = gg.object_from_parts("GB_Brain", [gg.part(v + HEAD_OFFSET, q, 0, gb_rigid_bone=_rigid(len(v), "head"))])
    gg.decimate_to(obj, 13900)
    pv = gbc.get_verts(obj.data)
    hp = pv - HEAD_OFFSET
    s = A.gyri_field(np.abs(hp[:, 0]), hp[:, 1], hp[:, 2])
    depth = np.exp(-(s / 0.0016) ** 2)
    region = neuro.brain_region_at(pv)
    gbc.point_attr(obj, "gb_region", region, 'INT')
    gbc.set_codes_uv(obj, region, depth)
    return obj


def _organ_axes(p):
    return gg.orthonormal(p["u"], p["v"])


def _prim_sdf(name, inflate=0.0):
    """SDF of an RB §7.5 primitive (obb/aabb -> superellipsoid, ellipsoid, sphere, capsule)."""
    A = _A()
    p = OR.PRIMITIVES[name]
    c, size, axes = np.array(p["c"]), np.array(p["size"]), _organ_axes(p)
    half = 0.5 * size + inflate
    if p["shape"] in ("obb", "aabb"):
        return lambda x, y, z: gg.sd_superellipsoid(x, y, z, c, half, axes, n=2.6), c, half
    if p["shape"] in ("ellipsoid",):
        return lambda x, y, z: gg.sd_oellipsoid(x, y, z, c, half, axes), c, half
    if p["shape"] == "sphere":
        return lambda x, y, z: A.sd_sphere(x, y, z, c, half[0]), c, half
    if p["shape"] == "capsule":
        a = c - axes[0] * (half[0] - half[1])
        b = c + axes[0] * (half[0] - half[1])
        return lambda x, y, z: A.sd_capsule(x, y, z, a, b, half[1]), c, half
    raise ValueError(p["shape"])


def _lung_sdf(side):
    """Lung: box-ish superellipsoid tapering to the apex, hollowed by the heart (cardiac notch)."""
    A = _A()
    p = OR.PRIMITIVES["lung_" + side]
    c, half = np.array(p["c"]), 0.5 * np.array(p["size"])
    heart, _hc, _hh = _prim_sdf("heart", inflate=0.010)
    top, bot = c[2] + half[2], c[2] - half[2]

    def fn(x, y, z):
        t = np.clip((top - z) / (top - bot), 0.0, 1.0)
        s = 0.30 + 0.70 * np.sqrt(t)                        # narrow apex, broad base
        cx = c[0] - np.sign(c[0]) * 0.022 * (1.0 - t)       # the apex leans toward the midline
        d = gg.superellipse2(x - cx, y - c[1], half[0] * s, half[1] * s, 2.4)
        dome = (bot + 0.02 + 0.015 * np.abs((x - c[0]) / half[0])) - z   # concave diaphragmatic base
        d = np.maximum(d, np.maximum(z - top, dome))
        return A.smax(d, -heart(x, y, z), 0.01)
    return fn


def _diaphragm_sdf():
    """Diaphragm: 5 mm dome sheet (right dome 1.320, left 1.300, central tendon 1.310) in the cage."""
    A = _A()
    D = OR.DIAPHRAGM

    def height(x, y):
        right = D["dome_R_z"] - 0.07 * ((x + 0.060) / 0.10) ** 2 - 0.05 * (y / 0.10) ** 2
        left = D["dome_L_z"] - 0.07 * ((x - 0.060) / 0.10) ** 2 - 0.05 * (y / 0.10) ** 2
        return np.maximum(np.maximum(right, left), D["central_tendon_z"] - 0.01 - 0.3 * x * x)

    def fn(x, y, z):
        sheet = np.abs(z - height(x, y)) - 0.0025
        rim = A.ellipse2(x, y - 0.010, 0.135, 0.095)
        return np.maximum(sheet, rim)
    return fn


def _stomach_sdf():
    A = _A()
    fund = A.sd_ellipsoid
    return lambda x, y, z: A.smin(A.smin(fund(x, y, z, (0.060, 0.000, 1.250), (0.042, 0.045, 0.050)),
                                         A.sd_capsule(x, y, z, (0.055, -0.020, 1.215), (0.030, -0.045, 1.150),
                                                      0.045, 0.032), 0.02),
                                  A.sd_capsule(x, y, z, (0.030, -0.045, 1.150), (-0.015, -0.050, 1.145),
                                               0.030, 0.014), 0.015)


def organ_parts(r):
    """(organ id, sub-id array or 0, part) list for the placeholder organs."""
    A = _A()
    h = r["organ"]
    parts = []

    def add(oid, fn, c, half, sub=None, slot=0):
        pad = np.max(half) + 0.012
        lo, hi = np.array(c) - pad, np.array(c) + pad
        v, q = gg.sdf_arrays(fn, lo, hi, h)
        if len(v) == 0:
            return
        sid = np.zeros(len(v), dtype=np.int32) if sub is None else sub(v)
        parts.append(gg.part(v, q, slot, gb_organ=np.full(len(v), OR.ORGAN_BY_ID[oid]["organ_id"]), gb_sub=sid))

    # heart: ellipsoid of the RB OBB, sub-id = nearest chamber
    hf, hc, hh = _prim_sdf("heart")
    subs = OR.organ_sub_primitives(OR.ORGAN_BY_ID["heart"])

    def heart_sub(v):
        best = np.full(len(v), 1e9)
        out = np.zeros(len(v), dtype=np.int32)
        for s in subs:
            f, _c, _h = _prim_sdf(s["id"])
            d = f(v[:, 0], v[:, 1], v[:, 2])
            m = d < best
            best = np.where(m, d, best)
            out = np.where(m, s["sub_id"], out)
        return out
    heart_fn = lambda x, y, z: gg.sd_oellipsoid(x, y, z, hc, hh * np.array([1.0, 0.95, 0.95]),
                                               _organ_axes(OR.PRIMITIVES["heart"]))
    add("heart", heart_fn, hc, hh, heart_sub)
    peri = lambda x, y, z: heart_fn(x, y, z) - 0.003
    add("pericardium", peri, hc, hh + 0.003)
    for side in ("L", "R"):
        p = OR.PRIMITIVES["lung_" + side]
        add("lung_" + side, _lung_sdf(side), p["c"], 0.5 * np.array(p["size"]))
    lv = OR.organ_sub_primitives(OR.ORGAN_BY_ID["liver"])
    lfs = [_prim_sdf(s["id"]) for s in lv]
    liver = lambda x, y, z: A.smin(A.smin(lfs[0][0](x, y, z), lfs[1][0](x, y, z), 0.03), lfs[2][0](x, y, z), 0.01)
    pl = OR.PRIMITIVES["liver"]
    add("liver", liver, pl["c"], 0.5 * np.array(pl["size"]))
    for oid in ("gallbladder", "spleen", "kidney_L", "kidney_R", "adrenal_L", "adrenal_R", "bladder", "larynx"):
        prim = OR.ORGAN_BY_ID[oid]["hit"][0]
        f, c, hf_ = _prim_sdf(prim)
        add(oid, f, c, hf_)
    thy = [_prim_sdf(n) for n in OR.ORGAN_BY_ID["thyroid"]["hit"]]
    add("thyroid", lambda x, y, z: A.smin(A.smin(thy[0][0](x, y, z), thy[1][0](x, y, z), 0.004), thy[2][0](x, y, z),
                                          0.004), (0.0, -0.030, 1.500), (0.04, 0.02, 0.03))
    add("stomach", _stomach_sdf(), (0.035, -0.025, 1.200), (0.08, 0.07, 0.11))
    om = OR.PRIMITIVES["omentum"]

    def omf(x, y, z):
        T = TORSO_SECTIONS
        a, b = np.interp(z, T[:, 0], T[:, 1]) - 0.032, np.interp(z, T[:, 0], T[:, 2]) - 0.032
        cy = np.interp(z, T[:, 0], T[:, 3])
        sheet = np.abs(gg.superellipse2(x, y - cy, a, b, 2.6)) - 0.0035
        clip = np.maximum(np.maximum(0.950 - z, z - 1.120), np.maximum(np.abs(x) - 0.115, (y - cy) + 0.035))
        return np.maximum(sheet, clip)
    add("omentum", omf, om["c"], (0.14, 0.02, 0.09))
    add("diaphragm", _diaphragm_sdf(), (0.0, 0.010, 1.27), (0.14, 0.10, 0.07))
    # tubes: trachea, bronchi, oesophagus, pancreas (swept)
    for oid in ("trachea", "bronchus_L", "bronchus_R", "oesophagus", "pancreas"):
        t = OR.TUBES[OR.ORGAN_BY_ID[oid]["tube"]]
        v, f, _t = gg.sweep(t["points"], t["radius"], sides=12, step=max(0.006, 2 * h))
        parts.append(gg.part(v, f, 0, gb_organ=np.full(len(v), OR.ORGAN_BY_ID[oid]["organ_id"]),
                             gb_sub=np.zeros(len(v), dtype=np.int32)))
    return parts


def _organ_shape_keys(obj):
    """heart_systole, lung_inhale_L/R, lung_collapse_L/R, diaphragm_inhale (placeholder magnitudes [RB §7.5])."""
    v = gbc.get_verts(obj.data)
    org = gbc.read_point_attr(obj, "gb_organ", 'INT')
    keys = {}
    hid = OR.ORGAN_BY_ID["heart"]["organ_id"]
    hc = np.array(OR.PRIMITIVES["heart"]["c"])
    m = org == hid
    d = np.zeros_like(v)
    d[m] = (v[m] - hc) * (0.935 - 1.0)                 # -18 % volume (systole -15..-20 %)
    keys["heart_systole"] = d
    for side in ("L", "R"):
        oid = OR.ORGAN_BY_ID["lung_" + side]["organ_id"]
        m = org == oid
        c = np.array(OR.PRIMITIVES["lung_" + side]["c"])
        d = np.zeros_like(v)
        low = np.clip((c[2] - v[m, 2]) / 0.11 + 0.5, 0.0, 1.0)
        d[m] = (v[m] - c) * 0.031
        d[m, 2] -= 0.017 * low                         # diaphragm excursion 1.5-2 cm
        keys["lung_inhale_" + side] = d
        hilum = np.array(OR.TUBES["bronchus_" + side]["points"][-1])
        d = np.zeros_like(v)
        d[m] = (hilum - v[m]) * (1.0 - 0.67)            # -70 % volume toward the hilum
        keys["lung_collapse_" + side] = d
    m = org == OR.ORGAN_BY_ID["diaphragm"]["organ_id"]
    d = np.zeros_like(v)
    d[m, 2] = -0.017
    keys["diaphragm_inhale"] = d
    return keys


def build_organs(r):
    """GB_Organs: organ primitives (UV2 = organ id, sub id) with the 6 organ shape keys."""
    obj = gg.object_from_parts("GB_Organs", organ_parts(r))
    gg.decimate_to(obj, 21800)
    _codes_from_attrs(obj, "gb_organ", "gb_sub")
    return obj


def build_cord(r):
    """GB_Cord: cord C1 -> conus from the RB §7.3 cord ellipses, cauda equina; UV2 = (cord segment, t)."""
    prof = VT._cord_profile()
    pts = np.column_stack([np.zeros(len(prof)), prof[:, 1], prof[:, 0]])
    radii = np.column_stack([prof[:, 2], prof[:, 3]])
    v1, f1, t1 = gg.sweep(pts, radii, sides=12, step=0.006, normal_fn=lambda P: np.tile([1.0, 0.0, 0.0], (len(P), 1)))
    v2, f2, t2 = gg.sweep(VT.CAUDA_CHAIN, VT.CAUDA_RADIUS, sides=10, step=0.008)
    segs = VT.cord_segments()
    ztop = np.array([s["z_top"] for s in segs])

    def seg_of(v):
        return np.clip(np.searchsorted(-ztop, -v[:, 2], side="right") - 1, 0, 29)
    parts = [gg.part(v1, f1, 0, gb_piece=seg_of(v1), gb_tt=t1),
             gg.part(v2, f2, 0, gb_piece=np.full(len(v2), 30), gb_tt=t2)]
    obj = gg.object_from_parts("GB_Cord", parts)
    gg.decimate_to(obj, 2900)
    u = gbc.read_point_attr(obj, "gb_piece", 'INT')
    t = gbc.read_point_attr(obj, "gb_tt", 'FLOAT')
    gbc.set_codes_uv(obj, u, t)
    return obj


def build_vessels(r):
    """GB_Vessels_Art/_Ven: tubes of every RB §3.3 segment >= 1.5 mm; UV2 = (vessel index, t)."""
    import vascular
    parts = {"GB_Vessels_Art": [], "GB_Vessels_Ven": []}
    for s in VS.vessel_segments():
        mesh = vascular.mesh_for(s)
        if mesh is None:
            continue
        d0 = s["d_mm"] / 1000
        d1 = (s["d_end_mm"] or s["d_mm"]) / 1000
        n = len(s["points"])
        radii = 0.5 * (d0 + (d1 - d0) * np.linspace(0.0, 1.0, n))
        step = max(r["vessel_step"], 3.0 * d0)
        v, f, t = gg.sweep(s["points"], radii, sides=VS.tube_sides(s["d_mm"]), step=step, smooth=n > 2)
        parts[mesh].append(gg.part(v, f, 0, gb_vidx=np.full(len(v), float(s["vessel_index"])), gb_tt=t))
    out = {}
    for name, pl in parts.items():
        obj = gg.object_from_parts(name, pl)
        gbc.set_codes_uv(obj, gbc.read_point_attr(obj, "gb_vidx"), gbc.read_point_attr(obj, "gb_tt"))
        out[name] = obj
    return out


# ===========================================================================
# Data objects (GB_Data; JSON only, never in the glb)
# ===========================================================================
def _curve(name, pts, radius=None):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (p[0], p[1], p[2], 1.0)
        if radius is not None:
            sp.points[i].radius = float(radius[i] if np.ndim(radius) else radius)
    return gbc.new_object(name, cu, "GB_Data")


def build_data_objects():
    """GBL_ landmark empties, GBH_ organ hit empties, GBV_/GBN_ curves and the GBC_cord curve."""
    import vascular
    out = {}
    for name, p in LM.all_landmarks().items():
        o = gbc.new_object("GBL_" + name, None, "GB_Data")
        o.location = p
        o.empty_display_type = 'SPHERE'
        o.empty_display_size = 0.006
        out[o.name] = o
    for org in OR.ORGANS:
        for i, prim in enumerate(OR.organ_hit_primitives(org)):
            o = gbc.new_object(f"GBH_{org['id']}_{i}", None, "GB_Data")
            U, V, W = gg.orthonormal(prim["u"], prim["v"])
            from mathutils import Matrix
            m = Matrix(((U[0], V[0], W[0], prim["c"][0]), (U[1], V[1], W[1], prim["c"][1]),
                        (U[2], V[2], W[2], prim["c"][2]), (0, 0, 0, 1)))
            o.matrix_world = m
            o.scale = [0.5 * s for s in prim["size"]]
            o.empty_display_type = 'SPHERE' if prim["shape"] in ("ellipsoid", "sphere") else 'CUBE'
            o["gb_shape"] = prim["shape"]
            out[o.name] = o
    for s in VS.vessel_segments():
        P, rr, _t = vascular.centreline(s)
        out["GBV_" + s["id"]] = _curve("GBV_" + s["id"], P, rr)
    for nid, n in NV.NERVES.items():
        for side, sx in (("L", 1.0), ("R", -1.0)):
            pts = [(sx * p[0], p[1], p[2]) for p in n["points"]]
            out[f"GBN_{nid}_{side}"] = _curve(f"GBN_{nid}_{side}", pts, n["radius"])
    prof = VT._cord_profile()
    out["GBC_cord"] = _curve("GBC_cord", [(0.0, q[1], q[0]) for q in prof], prof[:, 2])
    return out


# ===========================================================================
# Shape keys (placeholder analytic fields; B2 / B1 / B4 own the final ones)
# ===========================================================================
# AU: (head-frame centre of the LEFT side, radius, displacement mm (lateral, y, z))
FACE_FIELDS = {
    "AU01": ((0.015, -0.093, 0.040), 0.015, (0.0, 0.0, 4.0)),
    "AU02": ((0.040, -0.085, 0.040), 0.015, (0.0, 0.0, 4.0)),
    "AU04": ((0.018, -0.094, 0.036), 0.015, (-2.0, 0.0, -3.0)),
    "AU06": ((0.035, -0.090, 0.000), 0.018, (0.0, -1.5, 3.0)),
    "AU07": ((0.032, -0.082, 0.012), 0.008, (0.0, 0.0, 1.5)),
    "AU09": ((0.010, -0.100, 0.005), 0.010, (0.0, -1.0, 2.0)),
    "AU10": ((0.012, -0.097, -0.042), 0.012, (0.0, 0.0, 3.0)),
    "AU12": ((0.024, -0.085, -0.055), 0.014, (4.0, 2.0, 4.0)),
    "AU15": ((0.024, -0.085, -0.055), 0.014, (0.0, 0.0, -4.0)),
    "AU20": ((0.024, -0.085, -0.055), 0.014, (5.0, 0.0, 0.0)),
    "mouth_slack": ((0.015, -0.090, -0.065), 0.020, (0.0, 0.0, -3.0)),
    "swell_periorbital": ((0.032, -0.082, 0.022), 0.018, (0.0, -3.0, 0.0)),
}


def face_shape_fields(v_body):
    """{key: displacement (N,3)} for the 24 face keys on body-frame vertices (placeholder fields)."""
    hp = np.asarray(v_body) - HEAD_OFFSET
    out = {}
    for au, (c, rad, disp) in FACE_FIELDS.items():
        for side, sx in (("L", 1.0), ("R", -1.0)):
            cc = np.array([sx * c[0], c[1], c[2]])
            d = np.linalg.norm(hp - cc, axis=1)
            w = np.clip(1.0 - (d / rad) ** 2, 0.0, 1.0) ** 2
            w *= (hp[:, 0] * sx > -0.004)                   # never cross the midline
            vec = np.array([sx * disp[0], disp[1], disp[2]]) / 1000.0
            out[f"{au}_{side}"] = w[:, None] * vec[None, :]
    return out


def body_shape_fields(v):
    """chest_inhale, belly_distension, thigh_swell_L/R on GB_Body vertices."""
    v = np.asarray(v)
    x, y, z = v[:, 0], v[:, 1], v[:, 2]
    cy = np.interp(z, TORSO_SECTIONS[:, 0], TORSO_SECTIONS[:, 3])
    trunk = (np.abs(x) < 0.17)
    out = {}
    w = trunk * np.clip(1 - ((z - 1.33) / 0.12) ** 2, 0, 1)
    rad = np.stack([x, y - cy, np.zeros_like(x)], 1)
    rad /= np.maximum(np.linalg.norm(rad, axis=1, keepdims=True), 1e-6)
    out["chest_inhale"] = (0.007 * w)[:, None] * rad
    w = trunk * (y < cy) * np.clip(1 - ((z - 1.09) / 0.11) ** 2, 0, 1) * np.clip(1 - (x / 0.14) ** 2, 0, 1)
    out["belly_distension"] = (0.025 * w)[:, None] * np.array([[0.0, -1.0, 0.0]])
    for side, sx in (("L", 1.0), ("R", -1.0)):
        ax = LEG_PTS[1] * np.array([sx, 1, 1])
        rel = np.stack([x - ax[0], y - ax[1], np.zeros_like(x)], 1)
        dist = np.linalg.norm(rel, axis=1)
        w = (x * sx > 0.02) * (dist < 0.12) * np.clip(1 - ((z - 0.70) / 0.16) ** 2, 0, 1)
        out["thigh_swell_" + side] = (0.008 * w / np.maximum(dist, 1e-6))[:, None] * rel
    return out


def add_shape_keys(obj, fields, order):
    """Basis + one key per name in ``order`` from per-vertex displacement fields."""
    if obj.data.shape_keys is None:
        obj.shape_key_add(name="Basis", from_mix=False)
    base = gbc.get_verts(obj.data)
    for name in order:
        kb = obj.shape_key_add(name=name, from_mix=False)
        kb.data.foreach_set("co", (base + fields[name]).ravel())
        kb.value = 0.0
    return obj


# ===========================================================================
# Orchestration
# ===========================================================================
def build_lod1(objs):
    """GB_Head_LOD1 / GB_Body_LOD1: 50 % collapse copies (plan D18 fallback)."""
    out = {}
    for src in ("GB_Head", "GB_Body"):
        o = objs[src]
        me = o.data.copy()
        lod = gbc.new_object(src + "_LOD1", me)
        gg.decimate_to(lod, gbc.tri_count(me) // 2)
        set_skin_codes(lod, body_segment="head_neck" if src == "GB_Head" else None)   # codes never interpolate
        out[lod.name] = lod
    return out


def build_placeholder(quick=False, uv=True):
    """Build the whole placeholder subject; returns ``{contract name: object}`` (plan §5.2).

    Every object carries its final name, collection, material slots, UV maps
    (``atlas``, ``gb_codes``), identity transform, parent ``GB_Armature`` and one
    ARMATURE modifier; shape keys and key-pose actions exist with final names."""
    import rig
    r = RES["quick" if quick else "full"]
    gbc.collections()
    objs = {}
    T = gbc.Timer
    with T("placeholder: armature + poses"):
        arm = rig.build_armature()
        rig.build_poses(arm)
    with T("placeholder: head + body skin (seam ring)"):
        head, body, _ring = build_head_body(r, quick)
        objs.update({"GB_Head": head, "GB_Body": body})
    with T("placeholder: shorts + muscle shell"):
        objs["GB_Shorts"] = build_shorts(r)
        objs["GB_MuscleShell"] = build_muscle_shell(r)
    with T("placeholder: eyes, eye FX, mouth, brow/lash"):
        objs.update(build_eyes())
        objs.update(build_eye_fx())
        objs["GB_Mouth"] = build_mouth(r)
        objs["GB_BrowLash"] = build_brow_lash()
    with T("placeholder: skeleton + fracture variants"):
        skel, parts = build_skeleton(r)
        objs["GB_Skeleton"] = skel
        objs.update(build_fracture_variants(parts))
    with T("placeholder: brain, organs, cord, vessels"):
        objs["GB_Brain"] = build_brain(r)
        objs["GB_Organs"] = build_organs(r)
        objs["GB_Cord"] = build_cord(r)
        objs.update(build_vessels(r))
    if uv:
        with T("placeholder: atlas UVs"):
            for name, o in objs.items():
                atlas_uv(o, quick)
    with T("placeholder: LOD1 + shape keys"):
        objs.update(build_lod1(objs))
        add_shape_keys(objs["GB_Head"], face_shape_fields(gbc.get_verts(objs["GB_Head"].data)),
                       gbc.SHAPE_KEYS["GB_Head"])
        add_shape_keys(objs["GB_Body"], body_shape_fields(gbc.get_verts(objs["GB_Body"].data)),
                       gbc.SHAPE_KEYS["GB_Body"])
        add_shape_keys(objs["GB_Organs"], _organ_shape_keys(objs["GB_Organs"]), gbc.SHAPE_KEYS["GB_Organs"])
    for name, o in objs.items():
        finish_uvs(o)
        tag(o)
        o.data.shade_smooth()
    with T("placeholder: GB_Data objects"):
        build_data_objects()
    with T("placeholder: skin weights"):
        rig.skin_all(objs)
    objs[gbc.ARMATURE] = arm
    return objs


if __name__ == "__main__":
    args = gbc.script_args()
    t0 = time.time()
    gbc.reset_scene()
    objs = build_placeholder(quick="--quick" in args)
    gbc.log(f"placeholder built: {len(objs)} objects in {time.time() - t0:.1f} s")
    if "--render" in args:
        gbc.render_views("placeholder", samples=24)
