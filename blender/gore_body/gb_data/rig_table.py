"""Rig table: 39 deform bones (plan §3.1.1) and 20 physical bodies (plan §3.1.2).

Positions are [RB §7.2] (V) unless marked E.  Bones are ``snake_case`` with
``_L/_R`` suffixes (plan §0.3); right-side rows are mirrored from the left.

Joint axes are defined anatomically and resolved numerically into world
vectors (``resolve_axes``): for every axis we give an approximate direction,
a probe point on the child and the world direction that probe must move in for
a *positive* rotation (right-hand rule).  The resolver orthogonalises the axis
against the bone and flips it if needed, so ``rig.json`` carries world axes
whose sign is proven, never assumed from bone roll (plan §3.1.1).
"""
import numpy as np

from . import myotomes as _myo

# ---------------------------------------------------------------------------
# Bones.  name: (parent, head, tail, roll_align, kinematic, note)
# roll_align: a world vector the bone's local +Z axis is aligned toward (deterministic roll).
# Left-side rows only for bilateral bones; mirrored by ``bones()``.
# ---------------------------------------------------------------------------
_FWD = (0.0, -1.0, 0.0)
_UP = (0.0, 0.0, 1.0)

_EYE_L = (0.032, -0.050, 1.669)                     # eyeball centre [RB §1.2] (head eye + offset)

BONES_MID = [
    ("root", None, (0.0, 0.0, 0.0), (0.0, 0.0, 0.10), _FWD, True, "Never simulated"),
    ("hips", "root", (0.0, -0.005, 0.965), (0.0, 0.006, 1.027), _FWD, False, "Ragdoll root"),
    ("spine", "hips", (0.0, 0.006, 1.027), (0.0, 0.002, 1.212), _FWD, False, "Lumbar"),
    ("chest", "spine", (0.0, 0.002, 1.212), (0.0, 0.049, 1.353), _FWD, False, "Lower thorax"),
    ("upper_chest", "chest", (0.0, 0.049, 1.353), (0.0, 0.015, 1.490), _FWD, False, ""),
    ("neck", "upper_chest", (0.0, 0.015, 1.490), (0.0, 0.015, 1.622), _FWD, False, ""),
    ("head", "neck", (0.0, 0.015, 1.622), (0.0, 0.020, 1.780), _FWD, False,
     "Nodding pivot = atlanto-occipital (0, 0.015, 1.622)"),
    ("jaw", "head", (0.0, 0.000, 1.640), (0.0, -0.060, 1.544), _UP, True, "E: TMJ axis centre -> menton; fit to GH_Jaw condyles (B2)"),
    ("tongue", "jaw", (0.0, -0.030, 1.585), (0.0, -0.075, 1.590), _UP, True, "E; falls back at death"),
]
BONES_LEFT = [
    ("eye_L", "head", _EYE_L, (_EYE_L[0], _EYE_L[1] - 0.012, _EYE_L[2]), _UP, True,
     "Eyeball centre [RB §1.2]; tail +12 mm along -Y (gaze)"),
    ("lid_upper_L", "head", _EYE_L, (_EYE_L[0], _EYE_L[1], _EYE_L[2] + 0.015), _FWD, True,
     "Rotates about the eye's X axis"),
    ("lid_lower_L", "head", _EYE_L, (_EYE_L[0], _EYE_L[1], _EYE_L[2] - 0.015), _FWD, True,
     "Rotates about the eye's X axis"),
    ("clavicle_L", "upper_chest", (0.025, -0.040, 1.450), (0.165, 0.010, 1.462), _FWD, False, "SC -> AC"),
    ("upper_arm_L", "clavicle_L", (0.180, 0.020, 1.415), (0.325, 0.020, 1.164), _FWD, False, "A-pose 30 deg"),
    ("upper_arm_twist_L", "upper_arm_L", (0.2525, 0.020, 1.2895), (0.325, 0.020, 1.164), _FWD, True,
     "Mid-arm -> elbow; 50 % of shoulder twist"),
    ("forearm_L", "upper_arm_L", (0.325, 0.020, 1.164), (0.460, 0.020, 0.930), _FWD, False, ""),
    ("forearm_twist_L", "forearm_L", (0.3925, 0.020, 1.047), (0.460, 0.020, 0.930), _FWD, True,
     "Mid-forearm -> wrist; carries pronation"),
    ("hand_L", "forearm_L", (0.460, 0.020, 0.930), (0.508, 0.020, 0.848), _FWD, False, "Wrist -> MCP3"),
    ("fingers_L", "hand_L", (0.508, 0.020, 0.848), (0.553, 0.020, 0.770), _FWD, True,
     "MCP3 -> tip; kinematic curl (grip, tenodesis, cadaveric spasm)"),
    ("thumb_L", "hand_L", (0.468, -0.005, 0.915), (0.500, -0.030, 0.840), _FWD, True, "E: CMC -> tip, kinematic"),
    ("thigh_L", "hips", (0.087, -0.015, 0.918), (0.092, 0.020, 0.492), _FWD, False, ""),
    ("shin_L", "thigh_L", (0.092, 0.020, 0.492), (0.095, 0.050, 0.075), _FWD, False, ""),
    ("foot_L", "shin_L", (0.095, 0.050, 0.075), (0.119, -0.079, 0.025), _UP, False, "Ankle -> 2nd MT head"),
    ("toes_L", "foot_L", (0.119, -0.079, 0.025), (0.128, -0.151, 0.010), _UP, True, "Kinematic"),
]


def _mirror_name(name):
    return name[:-2] + "_R" if name.endswith("_L") else name


def _mirror_p(p):
    return (-p[0], p[1], p[2])


def bones():
    """Ordered list of bone dicts (parents before children): 39 rows."""
    rows = []
    for (n, par, h, t, roll, kin, note) in BONES_MID:
        rows.append(dict(name=n, parent=par, head=h, tail=t, roll_align=roll, kinematic=kin, note=note))
    left = [dict(name=n, parent=par, head=h, tail=t, roll_align=roll, kinematic=kin, note=note)
            for (n, par, h, t, roll, kin, note) in BONES_LEFT]
    right = [dict(name=_mirror_name(b["name"]), parent=_mirror_name(b["parent"]), head=_mirror_p(b["head"]),
                  tail=_mirror_p(b["tail"]), roll_align=b["roll_align"], kinematic=b["kinematic"],
                  note=b["note"]) for b in left]
    # interleave so every parent precedes its child
    for l, r in zip(left, right):
        rows += [l, r]
    order, placed = [], set()
    pending = list(rows)
    while pending:
        progressed = False
        for b in list(pending):
            if b["parent"] is None or b["parent"] in placed:
                order.append(b)
                placed.add(b["name"])
                pending.remove(b)
                progressed = True
        if not progressed:
            raise ValueError(f"bone hierarchy has a cycle or missing parent: {[b['name'] for b in pending]}")
    return order


BONE_NAMES = tuple(b["name"] for b in bones())
BONE_INDEX = {n: i for i, n in enumerate(BONE_NAMES)}

# ---------------------------------------------------------------------------
# Joint axis templates (left side; resolved by resolve_axes).
# axis: (approx world vector | "bone" | "-bone", probe, toward, pos key, neg key)
# probe: "tail" (child bone tail) or an offset from the pivot (child bone head).
# ---------------------------------------------------------------------------
_TRUNK = {
    "flex": ((1, 0, 0), "tail", (0, -1, 0), "flex", "ext"),
    "lat": ((0, 1, 0), "tail", (1, 0, 0), "lat_L", "lat_R"),
    "twist": ("bone", (0, -0.1, 0), (1, 0, 0), "rot_L", "rot_R"),
}
_CLAVICLE = {
    "elev": ((0, -1, 0), "tail", (0, 0, 1), "elev", "depr"),
    "protr": ((0, 0, -1), "tail", (0, -1, 0), "protr", "retr"),
    "twist": ("bone", (0, 0, 0.05), (0, -1, 0), "roll_fwd", "roll_back"),
}
_ARM_LAT = (0.8660254, 0.0, 0.5)          # lateral normal of the A-pose arm
_ARM_MED = (-0.8660254, 0.0, -0.5)        # palm-side (medial) normal n_m
_SHOULDER = {
    "flex": (_ARM_MED, "tail", (0, -1, 0), "flex", "ext"),
    "abd": ((0, -1, 0), "tail", _ARM_LAT, "abd", "add"),
    "twist": ("bone", (0, -0.05, 0), _ARM_LAT, "rot_ext", "rot_int"),
}
_ELBOW = {"flex": (_ARM_MED, "tail", (0, -1, 0), "flex", "ext")}
_WRIST = {
    "flex": ((0, 1, 0), "tail", _ARM_MED, "flex", "ext"),
    "dev": (_ARM_MED, "tail", (0, -1, 0), "rad", "uln"),
    "twist": ("bone", tuple(0.03 * np.array(_ARM_MED)), (0, -1, 0), "sup", "pron"),
}
_HIP = {
    "flex": ((-1, 0, 0), "tail", (0, -1, 0), "flex", "ext"),
    "abd": ((0, -1, 0), "tail", (1, 0, 0), "abd", "add"),
    "twist": ("bone", (0, -0.1, 0), (1, 0, 0), "rot_ext", "rot_int"),
}
_KNEE = {"flex": ((1, 0, 0), "tail", (0, 1, 0), "flex", "ext")}
_ANKLE = {
    "flex": ((-1, 0, 0), "tail", (0, 0, 1), "dorsi", "plantar"),
    "twist": ("bone", (0, 0, -0.05), (-1, 0, 0), "inv", "ev"),
    "abd": ((0, 0, 1), "tail", (1, 0, 0), "abd", "add"),
}


def _plus10(lim):
    """Dead limits default: live +10 % (plan §3.1.2)."""
    return {k: [round(v[0] * 1.1, 1), round(v[1] * 1.1, 1)] for k, v in lim.items()}


# ---------------------------------------------------------------------------
# Physical bodies (plan §3.1.2).  Masses: Winter/Dempster fractions of 75 kg
# [RB §7.2] V; the thorax is split and the clavicles take 0.75 kg each from
# upper_chest (adjacent mass ratio <= 10:1 [RB §4.10]).  Shapes, COM fractions of
# split bodies, torque caps (mid of the plan's range) and dead lat limits are E.
# limits: {axis: [min_deg, max_deg]} of rotation about the axis' world vector
# (positive = the axis' "pos" direction).  Upper arm: cone swing + twist.
# ---------------------------------------------------------------------------
BODIES_MID = [
    dict(bone="hips", mass_kg=10.65, com_from_head=0.5, com_tag="E",
         shape=dict(type="box", size=(0.33, 0.20, 0.16), center=(0.0, 0.005, 0.955), x=(1, 0, 0), z="bone"),
         joint=None),
    dict(bone="spine", mass_kg=10.4, com_from_head=0.56, com_tag="V (Winter abdomen 0.44 from T12/L1)",
         shape=dict(type="box", size=(0.30, 0.20, 0.18), center="mid", x=(1, 0, 0), z="bone"),
         joint=dict(type="6dof", axes=_TRUNK, cap_nm=250.0, cap_range=(200, 300),
                    live={"flex": [-15, 40], "lat": [-15, 15], "twist": [-15, 15]})),
    dict(bone="chest", mass_kg=8.6, com_from_head=0.5, com_tag="E",
         shape=dict(type="box", size=(0.32, 0.22, 0.15), center="mid", x=(1, 0, 0), z="bone"),
         joint=dict(type="6dof", axes=_TRUNK, cap_nm=150.0, cap_range=(150, 150),
                    live={"flex": [-10, 30], "lat": [-15, 15], "twist": [-20, 20]})),
    dict(bone="upper_chest", mass_kg=6.1, com_from_head=0.5, com_tag="E",
         shape=dict(type="box", size=(0.34, 0.20, 0.14), center="mid", x=(1, 0, 0), z="bone"),
         joint=dict(type="6dof", axes=_TRUNK, cap_nm=100.0, cap_range=(100, 100),
                    live={"flex": [-10, 15], "lat": [-10, 10], "twist": [-10, 10]})),
    dict(bone="neck", mass_kg=1.1, com_from_head=0.5, com_tag="E",
         shape=dict(type="capsule", radius=0.055, height=0.13, center="mid", axis="bone"),
         joint=dict(type="6dof", axes=_TRUNK, cap_nm=30.0, cap_range=(20, 40),
                    live={"flex": [-33, 28], "lat": [-27, 27], "twist": [-35, 35]},
                    dead={"flex": [-51, 42], "lat": [-30, 30], "twist": [-45, 45]})),
    dict(bone="head", mass_kg=5.0, com_from_head=0.158, com_tag="V (head+neck COM at the ear canal)",
         shape=dict(type="capsule", radius=0.080, height=0.22, center=(0.0, 0.000, 1.667), axis=(0, 0, 1)),
         joint=dict(type="6dof", axes=_TRUNK, cap_nm=30.0, cap_range=(20, 40),
                    live={"flex": [-22, 19], "lat": [-18, 18], "twist": [-35, 35]},
                    dead={"flex": [-34, 28], "lat": [-20, 20], "twist": [-45, 45]})),
]
BODIES_LEFT = [
    dict(bone="clavicle_L", mass_kg=0.75, com_from_head=0.5, com_tag="E",
         shape=dict(type="capsule", radius=0.025, height=0.15, center="mid", axis="bone"),
         joint=dict(type="6dof", axes=_CLAVICLE, cap_nm=40.0, cap_range=(40, 40),
                    live={"elev": [-10, 30], "protr": [-15, 15], "twist": [0, 0]})),
    dict(bone="upper_arm_L", mass_kg=2.1, com_from_head=0.436, com_tag="V",
         shape=dict(type="capsule", radius=0.045, height=0.29, center="mid", axis="bone"),
         joint=dict(type="cone", axes=_SHOULDER, cap_nm=80.0, cap_range=(60, 100),
                    live={"swing": [0, 100], "twist": [-70, 70]},
                    dead={"swing": [0, 110], "twist": [-77, 77]})),
    dict(bone="forearm_L", mass_kg=1.2, com_from_head=0.430, com_tag="V",
         shape=dict(type="capsule", radius=0.038, height=0.27, center="mid", axis="bone"),
         joint=dict(type="hinge", axes=_ELBOW, cap_nm=65.0, cap_range=(50, 80),
                    live={"flex": [-5, 145]}, dead={"flex": [-10, 155]})),
    dict(bone="hand_L", mass_kg=0.45, com_from_head=0.506, com_tag="V",
         shape=dict(type="box", size=(0.03, 0.087, 0.19), center=(0.5075, 0.020, 0.8477), x=_ARM_MED, z="bone"),
         joint=dict(type="6dof", axes=_WRIST, cap_nm=11.5, cap_range=(8, 15),
                    live={"flex": [-65, 75], "dev": [-30, 20], "twist": [-80, 80]})),
    dict(bone="thigh_L", mass_kg=7.5, com_from_head=0.433, com_tag="V",
         shape=dict(type="capsule", radius=0.075, height=0.43, center="mid", axis="bone"),
         joint=dict(type="6dof", axes=_HIP, cap_nm=250.0, cap_range=(200, 300),
                    live={"flex": [-25, 120], "abd": [-30, 45], "twist": [-45, 45]})),
    dict(bone="shin_L", mass_kg=3.49, com_from_head=0.433, com_tag="V",
         shape=dict(type="capsule", radius=0.050, height=0.42, center="mid", axis="bone"),
         joint=dict(type="hinge", axes=_KNEE, cap_nm=225.0, cap_range=(200, 250),
                    live={"flex": [0, 135]}, dead={"flex": [-10, 158]})),
    dict(bone="foot_L", mass_kg=1.09, com_from_head=0.50, com_tag="V",
         shape=dict(type="box", size=(0.10, 0.07, 0.26), center=(0.110, -0.018, 0.040), x=(1, 0, 0),
                    z=(0.122, -0.993, 0.0)),
         joint=dict(type="6dof", axes=_ANKLE, cap_nm=125.0, cap_range=(100, 150),
                    live={"flex": [-50, 20], "twist": [-20, 30], "abd": [0, 0]})),
]
SHAPE_TAG = "E (plan §3.1.2 shapes)"
FRICTION = dict(skin_cloth=(0.6, 0.9), wet_blood=(0.1, 0.25), restitution=(0.1, 0.3))   # [RB §4.10]


def _bone_map():
    return {b["name"]: b for b in bones()}


def _unit(v):
    v = np.asarray(v, dtype=float)
    n = np.linalg.norm(v)
    if n < 1e-12:
        raise ValueError("zero-length vector")
    return v / n


def resolve_axes(bone_name, template):
    """Turn an axis template into world axes with proven signs.

    Returns ``{axis: {"world": [x,y,z], "sign": 1, "pos": key, "neg": key}}``:
    a positive right-handed rotation about ``world`` moves the probe toward the
    template's ``toward`` direction (i.e. performs the ``pos`` motion)."""
    b = _bone_map()[bone_name]
    head, tail = np.array(b["head"], float), np.array(b["tail"], float)
    t = _unit(tail - head)
    right = bone_name.endswith("_R")
    out, used = {}, []
    for name, (approx, probe, toward, pos, neg) in template.items():
        toward = np.array(toward, float)
        if right:
            toward = toward * np.array([-1.0, 1.0, 1.0])
        if isinstance(approx, str):
            a = t.copy() if approx == "bone" else -t
        else:
            a = np.array(approx, float)
            if right:
                a = a * np.array([-1.0, 1.0, 1.0])     # approx given as a polar direction; sign fixed below
            a = a - (a @ t) * t
            for u in used:                             # keep the non-twist axes orthogonal
                a = a - (a @ u) * u
            a = _unit(a)
            used.append(a)
        if isinstance(probe, str):
            p = tail
        else:
            off = np.array(probe, float)
            if right:
                off = off * np.array([-1.0, 1.0, 1.0])
            p = head + off
        vel = np.cross(a, p - head)
        if vel @ toward < 0:
            a = -a
        out[name] = {"world": [float(x) for x in a], "sign": 1, "pos": pos, "neg": neg}
    return out


def _mirror_body(d):
    m = dict(d)
    m["bone"] = _mirror_name(d["bone"])
    shape = dict(d["shape"])
    for k in ("center", "x", "z", "axis"):
        if isinstance(shape.get(k), tuple) and k == "center":
            shape[k] = _mirror_p(shape[k])
        elif isinstance(shape.get(k), tuple):
            shape[k] = _mirror_p(shape[k])       # direction vectors mirror as polar vectors
    m["shape"] = shape
    return m


def bodies():
    """The 20 physical bodies with resolved world data (plan §3.1.2, rig.json 'bodies')."""
    bm = _bone_map()
    rows = list(BODIES_MID)
    for l in BODIES_LEFT:
        rows += [l, _mirror_body(l)]
    out = []
    for d in rows:
        bone = bm[d["bone"]]
        head, tail = np.array(bone["head"]), np.array(bone["tail"])
        t = _unit(tail - head)
        sh = d["shape"]
        centre = (head + tail) / 2 if sh.get("center") == "mid" else np.array(sh["center"], float)
        shape = {"type": sh["type"], "center_world": centre.tolist(), "tag": SHAPE_TAG}
        if sh["type"] == "capsule":
            axis = t if sh["axis"] == "bone" else _unit(sh["axis"])
            shape.update(radius=sh["radius"], height=sh["height"], axis_world=axis.tolist(),
                         height_is="total incl. caps (Godot CapsuleShape3D.height)")
        else:
            z = t if sh["z"] == "bone" else _unit(sh["z"])
            x = np.array(sh["x"], float)
            x = _unit(x - (x @ z) * z)
            y = np.cross(z, x)
            shape.update(size=list(sh["size"]), basis_world={"x": x.tolist(), "y": y.tolist(), "z": z.tolist()},
                         size_is="full lengths along basis x, y, z")
        com = head + d["com_from_head"] * (tail - head)
        row = {"bone": d["bone"], "mass_kg": d["mass_kg"], "com_from_head": d["com_from_head"],
               "com_world": com.tolist(), "com_tag": d["com_tag"], "shape": shape}
        j = d["joint"]
        if j is None:
            row["joint"] = None
        else:
            axes = resolve_axes(d["bone"], j["axes"])
            live = {k: list(v) for k, v in j["live"].items()}
            dead = {k: list(v) for k, v in j.get("dead", _plus10(live)).items()}
            dirs = [ax["pos"] for ax in axes.values()] + [ax["neg"] for ax in axes.values()]
            caps = {k: j["cap_nm"] for k in dirs}
            myo = _myo.myotomes_for(d["bone"])
            row["joint"] = {
                "type": j["type"], "parent": bone["parent"], "pivot_world": list(bone["head"]),
                "axes": axes, "limits_live_deg": live, "limits_dead_deg": dead,
                "torque_cap_nm": caps, "torque_cap_range_nm": list(j["cap_range"]),
                "myotomes": {k: v for k, v in myo.items() if k in dirs},
            }
        out.append(row)
    return out


def total_mass():
    """Sum of body masses (kg); should be 75.0 +- 0.05."""
    return sum(b["mass_kg"] for b in BODIES_MID) + 2 * sum(b["mass_kg"] for b in BODIES_LEFT)


# kinematic bones driven procedurally (not physical bodies)
KINEMATIC_MYOTOMES = {n: _myo.myotomes_for(n) for n in ("forearm_twist_L", "fingers_L", "thumb_L", "toes_L")}

# Face data (plan §5.8 rig.json "face"); B2 measures the lid table on the head mesh.
LID_APERTURE_MM_TO_DEG_PLACEHOLDER = [[0.0, -38.0], [9.5, 0.0], [12.0, 7.5]]
