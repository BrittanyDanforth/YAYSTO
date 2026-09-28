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
        "colours": {"arterial_thin": "#C0141E", "venous_thin": "#8E1420", "pool": "#5E070C"},
        "vessels": [dict(c, id=f"{c['id']}_{c['side_tag']}") for c in courses],
    }
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    return path


