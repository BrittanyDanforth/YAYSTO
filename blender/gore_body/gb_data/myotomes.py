"""Myotome map: joint direction -> innervating cord segments (plan §3.2).

ISNCSCI key muscles (C5 elbow flexors, C6 wrist extensors, C7 elbow extensors,
C8 finger flexors, T1 small-finger abductors, L2 hip flexors, L3 knee extensors,
L4 ankle dorsiflexors, L5 long toe extensors, S1 ankle plantar flexors) are C
(R04 §6.2); every other assignment is standard neuro-anatomy, K (QA re-check),
as flagged in the plan.  Rows marked ``fit="B0"`` fill directions the plan's
table does not list (tag K).

Groups like ``"C1-C3": 0.4`` spread their weight equally over the listed
segments; ``expand()`` returns per-segment weights that sum to 1.  ``XI`` is
the accessory nerve (cranial): it survives every cord lesion and is lost only
with medullary damage [RB §4.6].

Direction keys (used by ``rig.json`` torque caps, limits and myotomes):
``flex/ext`` (flexion/extension; ankle ``dorsi/plantar``), ``abd/add``,
``lat_L/lat_R`` (trunk/neck lateral bend toward the left/right),
``rot_L/rot_R`` (trunk/neck turn toward the left/right), ``rot_int/rot_ext``
(limb internal/external rotation), ``elev/depr/protr/retr`` (clavicle),
``rad/uln`` (wrist deviation), ``sup/pron`` (forearm), ``inv/ev`` (foot),
``grip/open`` (fingers, thumb).
"""

CORD_SEGMENTS = (["C%d" % i for i in range(1, 9)] + ["T%d" % i for i in range(1, 13)] +
                 ["L%d" % i for i in range(1, 6)] + ["S%d" % i for i in range(1, 6)])
CORD_INDEX = {s: i for i, s in enumerate(CORD_SEGMENTS)}      # C1 = 0 ... S5 = 29 (plan §5.5)


def _range(a, b):
    """Segments from ``a`` to ``b`` inclusive, e.g. ('T10', 'L1')."""
    i, j = CORD_INDEX[a], CORD_INDEX[b]
    return CORD_SEGMENTS[i:j + 1]


def expand(groups):
    """``{"C1-C3": 0.4, "XI": 0.4, ...}`` -> ``{"C1": 0.1333, ..., "XI": 0.4}`` (sums to 1)."""
    out = {}
    for key, w in groups.items():
        if "-" in key:
            a, b = key.split("-")
            segs = _range(a, b)
        else:
            segs = [key]
        for s in segs:
            out[s] = out.get(s, 0.0) + w / len(segs)
    total = sum(out.values())
    return {k: v / total for k, v in out.items()}


def _eq(a, b):
    return {f"{a}-{b}": 1.0}


# body (or kinematic bone base name) -> direction -> weight groups
MYOTOMES = {
    # neck and head share one table (plan §3.2)
    "neck": {
        "flex": {"XI": 0.4, "C1-C3": 0.4, "C4-C6": 0.2},
        "ext": {"XI": 0.3, "C1-C4": 0.4, "C5-C8": 0.3},
        "rot_L": {"XI": 0.4, "C1-C4": 0.4, "C5-C8": 0.2},
        "rot_R": {"XI": 0.4, "C1-C4": 0.4, "C5-C8": 0.2},
        "lat_L": {"XI": 0.4, "C1-C4": 0.4, "C5-C8": 0.2},
        "lat_R": {"XI": 0.4, "C1-C4": 0.4, "C5-C8": 0.2},
    },
    "clavicle": {
        "elev": {"XI": 0.5, "C3-C5": 0.5},
        "protr": {"C5-C7": 0.6, "C8-T1": 0.4},
        "depr": {"C5-C7": 0.6, "C8-T1": 0.4},
        "retr": {"XI": 0.4, "C4-C5": 0.6},                        # rhomboids, trapezius; fit="B0" K
    },
    "upper_arm": {
        "abd": {"C5": 0.6, "C6": 0.4},
        "flex": {"C5": 0.6, "C6": 0.4},
        "ext": {"C6": 0.3, "C7": 0.4, "C8": 0.3},
        "add": {"C6": 0.3, "C7": 0.4, "C8": 0.3},
        "rot_int": {"C5": 0.5, "C6": 0.5},
        "rot_ext": {"C5": 0.5, "C6": 0.5},
    },
    "forearm": {
        "flex": {"C5": 0.6, "C6": 0.4},                            # biceps/brachialis (C5 key)
        "ext": {"C6": 0.2, "C7": 0.6, "C8": 0.2},                  # triceps (C7 key)
    },
    "forearm_twist": {                                              # kinematic
        "sup": {"C6": 1.0},
        "pron": {"C6-C7": 1.0},
    },
    "hand": {
        "ext": {"C6": 0.7, "C7": 0.3},                             # ECRL/ECRB (C6 key)
        "flex": {"C7": 0.6, "C8": 0.4},
        "rad": {"C6": 0.5, "C7": 0.5},                             # ECRL + FCR; fit="B0" K
        "uln": {"C7": 0.5, "C8": 0.5},                             # ECU + FCU; fit="B0" K
        "sup": {"C6": 1.0},                                         # forearm rotation folded into the wrist body
        "pron": {"C6-C7": 1.0},
    },
    "fingers": {                                                    # kinematic
        "grip": {"C8": 0.7, "T1": 0.3},                            # FDP (C8 key), intrinsics (T1 key)
        "open": {"C7": 1.0},                                        # EDC
    },
    "thumb": {
        "grip": {"C8": 0.7, "T1": 0.3},
        "open": {"C7": 1.0},
    },
    "upper_chest": {
        "flex": _eq("T1", "T6"),
        "ext": _eq("T1", "T8"),
        "lat_L": _eq("T1", "T6"), "lat_R": _eq("T1", "T6"),         # not in the plan table; fit="B0" K
        "rot_L": _eq("T1", "T6"), "rot_R": _eq("T1", "T6"),
    },
    "chest": {
        "flex": _eq("T6", "T12"),
        "ext": _eq("T6", "L2"),
        "lat_L": _eq("T7", "L1"), "lat_R": _eq("T7", "L1"),
        "rot_L": _eq("T7", "L1"), "rot_R": _eq("T7", "L1"),
    },
    "spine": {
        "flex": _eq("T10", "L1"),
        "ext": _eq("T10", "L5"),
        "lat_L": _eq("T12", "L3"), "lat_R": _eq("T12", "L3"),
        "rot_L": _eq("T12", "L3"), "rot_R": _eq("T12", "L3"),
    },
    "thigh": {
        "flex": {"L1": 0.2, "L2": 0.5, "L3": 0.3},                 # iliopsoas (L2 key)
        "ext": {"L5": 0.3, "S1": 0.5, "S2": 0.2},
        "abd": {"L4": 0.3, "L5": 0.5, "S1": 0.2},
        "rot_int": {"L4": 0.3, "L5": 0.5, "S1": 0.2},
        "add": {"L2": 0.3, "L3": 0.5, "L4": 0.2},
        "rot_ext": {"L5": 0.3, "S1": 0.5, "S2": 0.2},
    },
    "shin": {
        "ext": {"L2": 0.2, "L3": 0.5, "L4": 0.3},                  # quadriceps (L3 key)
        "flex": {"L5": 0.3, "S1": 0.5, "S2": 0.2},
    },
    "foot": {
        "dorsi": {"L4": 0.7, "L5": 0.3},                           # tibialis anterior (L4 key)
        "plantar": {"S1": 0.7, "S2": 0.3},                         # gastrocnemius/soleus (S1 key)
        "inv": {"L4-L5": 1.0},
        "ev": {"L5-S1": 1.0},
    },
    "toes": {
        "ext": {"L5": 1.0},                                         # EHL (L5 key)
        "flex": {"S1-S2": 1.0},                                     # FHL/FDL; fit="B0" K
    },
}
# the head body uses the neck table (plan §3.2 "neck + head")
MYOTOMES["head"] = MYOTOMES["neck"]

# Breathing muscles (plan §3.2 last row) and respiratory capacity by complete level [RB §4.6]
BREATHING = {
    "diaphragm": {"C3": 0.3, "C4": 0.5, "C5": 0.2},               # C4 main
    "intercostals": _eq("T1", "T11"),
    "abdominals": _eq("T6", "L1"),
}
# fraction of vital capacity kept with a COMPLETE lesion at this neurological level (K, L-M)
RESP_CAPACITY = [
    ("C1", "C3", 0.05), ("C4", "C4", 0.25), ("C5", "C5", 0.30), ("C6", "C6", 0.40),
    ("C7", "C8", 0.50), ("T1", "T6", 0.60), ("T7", "T12", 0.80), ("L1", "S5", 1.00),
]

# vertebra -> lesioned cord segments (RB §4.6; ±1 segment between sources at T10-T12)
VERTEBRA_TO_SEGMENTS = {
    "C1": ("C1", "C1"), "C2": ("C2", "C3"), "C3": ("C3", "C4"), "C4": ("C4", "C5"),
    "C5": ("C5", "C6"), "C6": ("C6", "C7"), "C7": ("C7", "C8"), "T1": ("C8", "T2"),
    "T2": ("T3", "T4"), "T3": ("T4", "T5"), "T4": ("T5", "T6"), "T5": ("T6", "T7"),
    "T6": ("T8", "T9"), "T7": ("T9", "T10"), "T8": ("T10", "T11"), "T9": ("T11", "T12"),
    "T10": ("T11", "L1"), "T11": ("L1", "L3"), "T12": ("L3", "S1"), "L1": ("S2", "S5"),
}
# L2-S2: cauda equina roots only (lower motor neuron, patchy, asymmetric)
CAUDA_VERTEBRAE = ("L2", "L3", "L4", "L5", "S1")


def resp_capacity(level):
    """Vital-capacity fraction for a complete lesion whose neurological level is ``level``."""
    i = CORD_INDEX[level]
    for a, b, frac in RESP_CAPACITY:
        if CORD_INDEX[a] <= i <= CORD_INDEX[b]:
            return frac
    return 1.0


def myotomes_for(body):
    """Expanded ``{direction: {segment: weight}}`` for a body/bone base name (e.g. ``forearm``)."""
    base = body[:-2] if body.endswith(("_L", "_R")) else body
    table = MYOTOMES.get(base)
    if table is None:
        return {}
    return {d: expand(g) for d, g in table.items()}
