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
        for k in range(9):
            f = -0.95 + 1.9 * k / 8.0
            out.append((hl * f, 0.0, -(ds * 0.5).max(0.001), 1.0))
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
    brain = BRAIN_OOZE[0] * {"bullet": 0.35, "exit": 1.3}.get(kind, 0.0) * t.smooth(0.88, 0.97, D)
    # a blast in the mouth destroys the lining, gums and tongue: they pour
    mouth = opened * 25.0 if kind == "blast" else 0.0
    qa = t.attr("b_c0") + t.attr("b_c2")
    qv = t.attr("b_c1") + t.attr("b_c3")
    qo = scalp + face + diploe + brain + mouth
    q = qa + qv + qo
    if kind == "blunt":
        # a bruise without a split does not bleed out
        q = q * t.smooth(0.25, 0.35, D)
    pers = ((t.attr("b_pw") + scalp * SCALP_SHEET[1] + face * FACE_DERMIS[1] + (diploe + brain) * 0.85
             + mouth * 0.7) / (t.attr("b_ws") + qo).max(1e-4)).clamp()
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


