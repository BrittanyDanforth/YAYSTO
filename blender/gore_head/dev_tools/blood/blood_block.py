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
DRIP_STEPS = 40
BRANCH_STEPS = 22
BLOOD_KINDS = ("bullet", "exit", "slash", "blunt", "blast")
POOL_KINDS = ("bullet", "exit", "blunt")
POOL_RES = 72
# kind: (extra runs at full flow, spread of the extra runs' start across the
# hole (fraction of its radius), cavity volume in mL at size 1 (fill time = V / Q))
RUNS = {"bullet": (2.0, 0.9, 0.10), "exit": (5.0, 1.0, 0.9), "slash": (1.0, 0.0, 0.25),
        "blunt": (4.0, 1.0, 0.7), "blast": (8.0, 1.2, 2.5)}
FLOW_REF = 22.0                 # mL/min at which a wound reads as heavy: I = 1 - exp(-Q / FLOW_REF)
# front speed on skin (m/s): base + heavy flow + arterial (RB §3.11: 1-5 cm/s,
# 2-3.5 on vertical skin)
RUN_SPEED = (0.016, 0.014, 0.010)
RUN_MAX = 0.34                  # longest run (m): forehead to the cut of the neck
BEAT_S = 0.8                    # heart period (s) of the arterial surges
# half width (m) of a run: 1.1 mm trickle .. ~3.5 mm (rivulets 2-5 mm, RB §3.11)
RUN_W = (0.0011, 0.0019, 0.0006)
BRANCH_P = 0.045                # chance per trail step that a heavy run splits


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
    """Points of the wound volume that are tested against the vessels:
    [(u, v, w, outflow weight)] in the hit frame (w < 0 = into the head).

    The outflow weight is the share of a deep bleed that comes out of the
    wound instead of filling the tissue (RB §3.4 tissue_factor: 0.15-0.3 in a
    narrow track deeper than ~3 cm, 1 in a gaping wound)."""
    s, e, D = h["s"], h["e"], h["D"]
    # depth reached: skin and scalp by D 0.6 (~7 mm), through the skull and
    # into the brain from D 0.78
    thru = t.lin(D, 0.0, 0.6, 0.0015, 0.007) + t.lin(D, 0.78, 1.0, 0.0, 0.035)
    out = []
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
        hl = s * 0.012 * e
        # a throat cut reaches much deeper than a cut over the skull
        ds = D * (0.009 + 0.018 * h["R"].z)
        for f in (-0.9, -0.45, 0.0, 0.45, 0.9):
            for dw in (0.45, 1.0):
                out.append((hl * f, 0.0, -(ds * dw).max(0.0015), 1.0))
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
    return out


def _vessel_sources(t, kind, h, vessels):
    """Bleed sources of one wound, as fields on its hit point.

    vessels: {class name: geometry of that class (GH_Vessels)}. Each wound
    sample finds the nearest vessel of every class; a vessel within the
    wound's reach (plus its own radius) is cut and adds its transected bleed
    rate (the largest per class counts: the courses are single lines).
    Area sources add the beds without a named trunk. Returns a dict of fields:
    q (mL/min at normal pressure), fa (arterial share), tis (brain / bone
    admixture), pers (0..1 persistence), src (row index + 1 of the dominant
    named vessel, 0 = none).
    """
    samples = _wound_samples(t, kind, h)
    _hole, reach = _wound_extent(t, kind, h)
    I, X, Y, Z = h["I"], h["X"], h["Y"], h["Z"]
    q_cls, pers_acc, pers_w = {}, None, None
    best_q, best_src = None, None
    for cls in VESSEL_CLASSES:
        g = vessels[cls]
        q = None
        for (u, v, w, wt) in samples:
            pos = I + X * u + Y * v + Z * w
            prox = t.node('GeometryNodeProximity', {'Target': g, 'Source Position': pos}, target_element='EDGES')
            dist, near = t.out(prox, 'Distance'), t.out(prox, 'Position')
            valid = t.switch(t.out(prox, 'Is Valid'), 0.0, 1.0)
            idx = t.out(t.node('GeometryNodeSampleNearest', {'Geometry': g, 'Sample Position': near}))
            data = t.sample(g, t.attr("v_data", 'FLOAT_VECTOR'), idx, 'FLOAT_VECTOR')
            vid = t.sample(g, t.attr("v_id", 'INT'), idx, 'INT')
            flow, r, pers = data.x, data.y, data.z
            cut = t.smooth(reach + r + 0.0005, reach * 0.35, dist) * valid
            qs = cut * flow * wt
            if q is None:
                q = qs
            else:
                q = q.max(qs)
            pa = qs * pers
            pers_acc = pa if pers_acc is None else pers_acc + pa
            pers_w = qs if pers_w is None else pers_w + qs
            if best_q is None:
                best_q, best_src = qs, t.math('ADD', vid, 1.0) * cut.gt(0.05)
            else:
                better = qs.gt(best_q)
                best_src = t.switch(better, best_src, t.math('ADD', vid, 1.0))
                best_q = best_q.max(qs)
        q_cls[cls] = q
    s, D, reg = h["s"], h["D"], h["R"]
    hole, _r = _wound_extent(t, kind, h)
    opened = t.smooth(0.03, 0.12, D)
    # beds without a named trunk (RB §3.7)
    size = {"bullet": 0.12 + 0.0 * s, "exit": hole / 0.0075, "slash": hole * 2.0 / 0.07,
            "blunt": (hole / 0.009) * (1.0 + h["crush"]), "blast": 1.0 + 0.0 * s}[kind]
    face_k = {"bullet": 0.5, "exit": 1.5, "slash": 1.0, "blunt": 1.5, "blast": 8.0}[kind]
    face_sz = size if kind in ("slash", "blunt") else 1.0
    scalp = SCALP_SHEET[0] * reg.x * size * opened
    face = FACE_DERMIS[0] * (reg.y + reg.z) * face_k * face_sz * opened
    bone_k = {"bullet": 0.4, "exit": 1.2, "slash": 0.0, "blunt": 1.0, "blast": 2.0}[kind]
    diploe = DIPLOE_OOZE[0] * bone_k * t.smooth(0.6, 0.8, D) * (1.0 + h["crush"])
    brain_k = {"bullet": 0.35, "exit": 1.3}.get(kind, 0.0)
    brain = BRAIN_OOZE[0] * brain_k * t.smooth(0.88, 0.97, D)
    # a blast in the mouth destroys the lining, gums and tongue: they pour
    mouth = 25.0 * opened if kind == "blast" else 0.0
    qa = q_cls["artery"] + q_cls["deep_artery"]
    qv = q_cls["vein"] + q_cls["sinus"]
    qo = scalp + face + diploe + brain + mouth
    q = qa + qv + qo
    if kind == "blunt":
        # a bruise without a split does not bleed out
        q = q * t.smooth(0.25, 0.35, D)
    pers = (pers_acc + scalp * SCALP_SHEET[1] + face * FACE_DERMIS[1] + (diploe + brain) * 0.85 + mouth * 0.7) \
        / (pers_w + qo).max(1e-4)
    return dict(q=q, fa=(qa / q.max(1e-4)).clamp(), tis=((brain + diploe * 0.3) / q.max(1e-4)).clamp(),
                pers=pers.clamp(), src=best_src)


def _build_source_group(kind):
    """Subgroup: bleed sources of every hit of one kind, stored on the hit points (b_*)."""
    f, g = 'NodeSocketFloat', 'NodeSocketGeometry'
    t = NodeTree(f"GH_Gore_Sources_{kind.capitalize()}",
                 (("Hits", g), ("Damage", f, 1.0), ("Bleed", f, 0.7),
                  ("Artery", g), ("Vein", g), ("Deep Artery", g), ("Sinus", g)),
                 (("Hits", g),), description=f"Vessels and beds cut by {kind} wounds -> bleed rate")
    damage, bleed = t.inp("Damage"), t.inp("Bleed")
    h = _hit_fields(t, damage)
    vessels = {"artery": t.inp("Artery"), "vein": t.inp("Vein"), "deep_artery": t.inp("Deep Artery"),
               "sinus": t.inp("Sinus")}
    src = _vessel_sources(t, kind, h, vessels)
    # the bleed control scales the physiological rate (0.7 = normal pressure)
    q = src["q"] * bleed / 0.7
    g = t.inp("Hits")
    g = t.store(g, "b_q", q)
    g = t.store(g, "b_fa", src["fa"])
    g = t.store(g, "b_tis", src["tis"])
    g = t.store(g, "b_pers", src["pers"])
    g = t.store(g, "b_src", src["src"])
    hole, _reach = _wound_extent(t, kind, h)
    g = t.store(g, "b_hole", hole)
    # time to fill the cavity (drip_time units, 1 = 60 s): V / Q, 0.3-25 s
    vol = RUNS[kind][2] * (h["s"] * h["s"]).max(0.2)
    if kind == "blunt":
        vol = vol * (1.0 + 3.0 * h["crush"])
    t0 = (vol / (q / 60.0).max(1e-3)).clamp(0.3, 25.0) / 60.0
    g = t.store(g, "b_t0", t0)
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
        n_extra = e * 0.4
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
        Tw = h["T"] if "T" in h else t.attr("hit_T", 'FLOAT_VECTOR')
        half_len, gape = _slash_params(t, s, e, D, Tw.dot(X), Tw.dot(Y), h["R"].x)
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
    return g


def _build_seed_group(kind, kind_id):
    """Subgroup: run seed points of one wound kind."""
    f = 'NodeSocketFloat'
    t = NodeTree(f"GH_Gore_DripSeeds_{kind.capitalize()}",
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
    # an oblique track opens an elongated hole: cover it
    stretch = 1.0 / t.math('ABSOLUTE', N.dot(Z)).max(0.45)
    Rp = t.attr("pl_R") * stretch
    P0 = I + (T1 * uv.x + T2 * uv.y) * Rp
    ray = t.node('GeometryNodeRaycast', {'Target Geometry': surface, 'Attribute': t.attr("g_wk"),
                                         'Source Position': P0 + N * 0.008, 'Ray Direction': -N,
                                         'Ray Length': 0.03}, data_type='FLOAT')
    hit = t.out(ray, 'Is Hit')
    wk = t.out(ray, 'Attribute')
    hgt = (t.out(ray, 'Hit Position') - I).dot(N)
    outside = t.switch(t.bool('AND', hit, wk.lt(0.5)), 0.0, 1.0)
    g = t.store(g, "pl_out", outside)
    g = t.store(g, "pl_h", t.switch(hit, -0.004, hgt))
    g = t.store(g, "pl_p0", P0, 'FLOAT_VECTOR')
    out_f = t.attr("pl_out")
    m_in = F(t, t.node('GeometryNodeBlurAttribute', {'Value': 1.0 - out_f, 'Iterations': 2, 'Weight': 1.0},
                       data_type='FLOAT').outputs[0])
    g = t.store(g, "pl_min", m_in)
    m_in = t.attr("pl_min")
    rim = out_f * m_in.gt(0.03).max(0.0)
    pid = t.attr("pl_id", 'INT')
    cnt = t.out(t.node('GeometryNodeAccumulateField', {'Value': rim, 'Group ID': pid}), 'Total')
    sum_h = t.out(t.node('GeometryNodeAccumulateField', {'Value': rim * t.attr("pl_h"), 'Group ID': pid}), 'Total')
    mean_h = sum_h / cnt.max(1.0)
    # (a hit whose skin did not open has no rim: no pool)
    g = t.store(g, "pl_mean", mean_h)
    g = t.store(g, "pl_cnt", cnt)
    fill = t.smooth(0.0, t.attr("b_t0").max(0.004), drip)
    L = t.attr("pl_mean") - 0.0032 * (1.0 - fill) + 0.00028 * fill
    hs = t.attr("pl_h")
    # just past the rim the liquid drapes onto the lip where the lip is lower
    # than the level (spilling); everywhere else it tucks under the skin
    adj = t.smooth(0.0, 0.35, t.attr("pl_min")) * fill.gt(0.9).max(0.0)
    h_out = t.mix(hs - 0.0012, L.min(hs + 0.00012), adj).min(L)
    # pulped brain in the pool of an exit (tissue share), bulging through the blood
    lump_n = t.noise(t.attr("pl_p0", 'FLOAT_VECTOR') * 380.0, detail=3.0, signed=False)
    lump_n2 = t.noise(t.attr("pl_p0", 'FLOAT_VECTOR') * 1300.0, detail=2.0)
    lump = t.smooth(0.52, 0.72, lump_n) * t.attr("b_tis").min(0.6) * 2.0 * fill * (1.0 - out_f)
    h_in = L + lump * (0.0016 + 0.0004 * lump_n2) + (1.0 - lump) * 0.00012 * lump_n2
    hfin = t.mix(h_in, h_out, out_f)
    g = t.out(t.node('GeometryNodeSetPosition', {'Geometry': g,
                                                 'Position': t.attr("pl_p0", 'FLOAT_VECTOR') + N * (hfin - (t.attr("pl_p0", 'FLOAT_VECTOR') - I).dot(N))}))
    g = t.store(g, "gore_tis", lump.clamp())
    # keep the pool and a margin of two grid cells under the skin
    far = F(t, t.node('GeometryNodeBlurAttribute', {'Value': 1.0 - t.attr("pl_out"), 'Iterations': 4,
                                                    'Weight': 1.0}, data_type='FLOAT').outputs[0])
    g = t.store(g, "pl_far", far)
    drop = t.bool('OR', t.attr("pl_far").lt(0.004), t.attr("pl_cnt").lt(3.0))
    g = t.out(t.node('GeometryNodeDeleteGeometry', {'Geometry': g, 'Selection': drop}, domain='POINT'))
    g = t.store(g, "gore_bthin", 0.0)
    g = t.store(g, "gore_art", t.attr("b_fa") * 0.35)
    g = t.store(g, "gore_bq", t.attr("b_q"))
    g = t.store(g, "gore_bsrc", t.attr("b_src"))
    return g


def _walk(t, seeds, surface, steps):
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
    push = (1.0 - it / 7.0).max(0.0)
    dirv = (gt / gl.max(1e-4) + wob * 0.7 + bias * push * 1.6).normalize()
    slope = 0.2 + 0.8 * t.smooth(0.05, 0.45, gl)
    hang = t.smooth(-0.62, -0.4, n.z)
    fac = slope * hang
    step = t.attr("d_len") / float(steps) * fac
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
    tt = t.attr("d_step") / float(steps)
    dw = t.attr("d_w")
    pp = t.pos()
    # width: narrow where it leaves the lip (never wider than the part of the
    # rim it pours over), widening down the run, uneven, fuller where it
    # slowed (creases, shallow slopes), a fuller head
    rad = dw * (0.6 + 0.4 * t.smooth(0.0, 0.14, tt)) \
        * (1.0 + 0.3 * t.noise(pp * 170.0, detail=1.0) + 0.12 * t.noise(pp * 520.0)) \
        * (1.0 + 0.55 * t.attr("d_slow"))
    # arterial surges: one bulge per heartbeat along the run (d_lam = front
    # speed x beat period), strength = arterial share
    arc = t.attr("d_len") * tt
    ph = t.math('SINE', arc / t.attr("d_lam").max(0.004) * TAU + t.attr("d_id", 'INT') * 1.7)
    rad = rad * (1.0 + 0.5 * t.attr("d_art") * ph.max(0.0) ** 2.0)
    rad = rad + dw * 0.3 * t.smooth(0.85, 1.0, tt) * t.attr("d_mov")
    # a run that stopped thins to a rounded tip
    rad = rad * (0.1 + 0.9 * t.smooth(1.0, 0.8, tt).max(t.attr("d_mov")))
    curves = t.out(t.node('GeometryNodeSetCurveRadius', {'Curve': curves, 'Radius': rad}))
    curves = t.store(curves, "d_rad", rad)
    profile = t.out(t.node('GeometryNodeCurvePrimitiveCircle', {'Resolution': 10, 'Radius': 1.0}, mode='RADIUS'))
    radius = t.out(t.node('GeometryNodeInputRadius'))
    tubes = t.out(t.node('GeometryNodeCurveToMesh', {'Curve': curves, 'Profile Curve': profile,
                                                     'Scale': radius, 'Fill Caps': True}))
    tubes = t.store(tubes, "d_flat", 0.24)
    tubes = t.store(tubes, "d_cap", 0.00016 + 0.00012 * t.attr("d_ib"))
    path = t.out(t.node('GeometryNodeCurveToMesh', {'Curve': curves}))
    return tubes, path


def _drops(t, tips, surface):
    """The front of a running stream (a rounded lobe) and the drops hanging
    where a run reached skin that faces down (chin, nose tip, jaw line,
    earlobe), plus drops falling from them while the flow keeps coming."""
    ico = t.out(t.node('GeometryNodeMeshIcoSphere', {'Radius': 1.0, 'Subdivisions': 2}))
    dw = t.attr("d_w")
    n = _nearest_normal(t, surface, t.pos())
    runs = t.attr("d_len").gt(0.012)
    # moving front: flat teardrop lobe 1.3x the run's width, stretched downward
    front = t.bool('AND', runs, t.attr("d_mov").gt(0.5))
    bead_s = dw * 1.3
    beads = t.node('GeometryNodeInstanceOnPoints', {'Points': tips, 'Selection': front,
                                                    'Instance': ico, 'Scale': t.vec(bead_s, bead_s, bead_s * 1.8)})
    beads = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(beads)}))
    beads = t.out(t.node('GeometryNodeSetPosition', {'Geometry': beads, 'Offset': t.vec(0.0, 0.0, -1.0) * (dw * 0.8)}))
    beads = t.store(beads, "d_flat", 0.3)
    beads = t.store(beads, "d_rad", bead_s * 1.2)
    beads = t.store(beads, "d_cap", 0.00034)
    # pendant drops (30-60 uL, r ~2.0-2.4 mm) where the skin faces down
    hang = t.bool('AND', runs, n.z.lt(-0.3))
    r = 0.0019 + 0.0005 * t.rand(0.0, 1.0, t.index(), 71)
    pend = t.node('GeometryNodeInstanceOnPoints', {'Points': tips, 'Selection': hang, 'Instance': ico,
                                                   'Scale': t.vec(r, r, r * 1.45)})
    pend = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(pend)}))
    pend = t.out(t.node('GeometryNodeSetPosition', {'Geometry': pend, 'Offset': t.vec(0.0, 0.0, -1.0) * r}))
    # falling drops below a hanging one while it keeps being fed (d_mov)
    fall_sel = t.bool('AND', hang, t.attr("d_mov").gt(0.5))
    fr = t.rand(0.0, 1.0, t.index(), 72)
    fall = t.node('GeometryNodeInstanceOnPoints', {'Points': tips, 'Selection': fall_sel, 'Instance': ico,
                                                   'Scale': t.vec(r * 0.9, r * 0.9, r * 1.25)})
    fall = t.out(t.node('GeometryNodeRealizeInstances', {'Geometry': t.out(fall)}))
    fall = t.out(t.node('GeometryNodeSetPosition', {'Geometry': fall,
                                                    'Offset': t.vec(0.0, 0.0, -1.0) * (0.012 + 0.03 * fr)}))
    hung = _join(t, pend, fall)
    hung = t.store(hung, "d_free", 1.0)
    return beads, hung


def _build_blood():
    """Skin-only blood geometry: pools in the wounds, runs down the skin, drops; also the run paths."""
    g_ = 'NodeSocketGeometry'
    t = NodeTree("GH_Gore_Blood",
                 inputs=(("Surface", g_),
                         ("Bullet", g_), ("Exit", g_), ("Slash", g_), ("Blunt", g_), ("Blast", g_),
                         ("Vessels", g_),
                         ("Damage", 'NodeSocketFloat', 1.0), ("Bleed", 'NodeSocketFloat', 0.7),
                         ("Drip Time", 'NodeSocketFloat', 1.0), ("Material", 'NodeSocketMaterial')),
                 outputs=(("Blood", g_), ("Trail", g_)),
                 description="Blood from the cut vessels: pools in the wounds, runs down the skin")
    surface = t.inp("Surface")
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
    # pools in the openings (grid radius per kind)
    pool_hits = []
    for k in POOL_KINDS:
        hk = sources[k]
        h = _hit_fields(t, damage)
        hole, _r = _wound_extent(t, k, h)
        rp = {"bullet": hole * 2.2 + 0.0012, "exit": hole * 2.2 + 0.0015, "blunt": hole * 2.6 + 0.002}[k]
        pool_hits.append(t.store(hk, "pl_R", rp))
    pool_pts = _join(t, *pool_hits)
    pools = _build_pools(t, pool_pts, surface, drip)
    pools = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': pools, 'Pattern Mode': 'Wildcard', 'Name': "pl_*"}))
    surf2 = _join(t, surface, pools)

    seeds = _join(t, *seeds)
    seeds = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': seeds, 'Pattern Mode': 'Wildcard', 'Name': "hit_*"}))
    seeds = t.out(t.node('GeometryNodeRemoveAttribute', {'Geometry': seeds, 'Pattern Mode': 'Wildcard', 'Name': "b_*"}))
    seeds = t.store(seeds, "d_id", t.index(), 'INT')
    seeds = t.store(seeds, "d_step", 0.0)
    seeds = t.store(seeds, "d_slow", 0.0)
    seeds = t.store(seeds, "d_mv", 1.0)
    p = t.pos()
    snapped = _nearest_point(t, surf2, p) + _nearest_normal(t, surf2, p) * (t.attr("d_w") * 0.2)
    seeds = t.out(t.node('GeometryNodeSetPosition', {'Geometry': seeds, 'Position': snapped}))
    trail1, tips1 = _walk(t, seeds, surf2, DRIP_STEPS)

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
    trail2, tips2 = _walk(t, bseeds, surf2, BRANCH_STEPS)

    tubes1, path1 = _run_mesh(t, trail1, surf2, DRIP_STEPS)
    tubes2, path2 = _run_mesh(t, trail2, surf2, BRANCH_STEPS)
    beads, hung = _drops(t, _join(t, tips1, tips2), surf2)
    blood = _join(t, tubes1, tubes2, beads)
    # flatten the runs onto the skin: blood runs as a flat film 0.1-0.4 mm
    # thick with rounded sides (a round tube reads as a glass rod); cross
    # section = a low dome thinning to nothing at the edges
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
    allb = _join(t, pools, runs)
    allb = t.out(t.node('GeometryNodeSetMaterial', {'Geometry': allb, 'Material': t.inp("Material")}))
    allb = t.out(t.node('GeometryNodeSetShadeSmooth', {'Mesh': allb, 'Shade Smooth': True}))
    t.result("Blood", allb)
    t.result("Trail", _join(t, path1, path2))
    t.layout()
    return t


