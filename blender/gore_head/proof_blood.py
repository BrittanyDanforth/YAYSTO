"""Zero-gap proof: the blood comes OUT OF THE HOLE, never from skin beside it.

REFERENCE_NOTES §5.17 / §5.19.1 / §5.21 (user requirement): the blood inside a
wound, the wet lip it spills over and the stream below must be ONE continuous
liquid body, with no skin visible between them at any time and from any angle.

For every bleeding wound (entry, exit, slash, blunt, blast, crushed) and every
sequence time (0, 5, 10, 20, 40, 60 s after the injury) this script

1. evaluates the head and finds the wound's main run (the film vertices carry
   ``gore_run`` = run id + 1 and ``gore_runf`` = 0 inside the wound .. 1 at the
   front), and builds its axis: the run's centre line from INSIDE the opening,
   over the rim, to 5 mm below the rim (the rim = the first axis point over
   intact skin);
2. renders close-ups from straight on, at 45 deg and grazing across the rim
   (Cycles), plus an exact material-ID mask of the same frame (Workbench,
   flat colours: skin / wound wall / blood / other);
3. samples every pixel along the projected axis: a pixel whose mask is skin or
   wound wall AND whose rendered colour is skin-like (not blood-tinted) is a
   gap pixel. Any gap pixel = FAIL.

Before the wound has filled (t = 0 and the first seconds) there is no run:
the check is then that no blood lies on intact skin outside the wound.

Writes a contact sheet of the rim crops (axis drawn in, green bar = PASS,
red = FAIL) to renders/proof_rim_zero_gap.png and prints the numbers.

    python3 proof_blood.py [--res 240] [--samples 12] [--rebuild]
    blender -b --python proof_blood.py -- [options]
"""
import argparse
import tempfile
import math
import os
import sys
import time

import bpy
import numpy as np
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gh_common as ghc  # noqa: E402
import gore  # noqa: E402

TIMES = (0, 5, 10, 20, 40, 60)
VIEWS = ("straight", "45", "graze")
# label, preset, hit, camera distance (m)
WOUNDS = (
    ("entry", "gunshot", "GH_Hit_Entry", 0.045),
    ("exit", "gunshot", "GH_Hit_Exit", 0.06),
    ("slash", "slash", "GH_Hit_Slash_Cheek", 0.07),
    ("blunt", "blunt", "GH_Hit_Blunt_Cranium", 0.07),
    ("blast", "blast", "GH_Hit_Blast_Mouth", 0.11),
    ("crushed", "crushed", "GH_Hit_Crush_2", 0.09),
)
BELOW_RIM = 0.005                # the axis runs on 5 mm below the rim
MASK_COLORS = {"skin": (0.0, 1.0, 0.0), "wall": (1.0, 1.0, 0.0), "blood": (1.0, 0.0, 0.0),
               "other": (0.0, 0.0, 1.0)}


def _mask_class(mat_name):
    if mat_name is None:
        return "other"
    if mat_name.startswith("GH_Blood"):
        return "blood"
    if mat_name == "GH_Skin":
        return "skin"
    if mat_name in ("GH_Fat",):
        return "wall"
    return "other"


def _read_png(path):
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    px = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[..., :3]
    bpy.data.images.remove(im)
    return px


def _skin_like(rgb):
    """Rendered colour that reads as bare skin / pale tissue (not blood-tinted, not a highlight)."""
    r, g, b = rgb[..., 0], rgb[..., 1], rgb[..., 2]
    rr = np.maximum(r, 1e-4)
    highlight = (g / rr > 0.9) & (b / rr > 0.85) & (r > 0.85)
    return (r > 0.3) & (g / rr > 0.6) & (b / rr > 0.45) & ~highlight


def _cameras(hit, dist, target=None, side=False):
    """Straight / 45 deg / grazing close-up cameras around the rim point the
    main run leaves from (or the hit itself before anything has left it)."""
    m = hit.matrix_world.to_3x3().normalized()
    z = (m @ Vector((0.0, 0.0, 1.0))).normalized()
    tgt = Vector(target) if target is not None else hit.matrix_world.translation + Vector((0.0, 0.0, -0.004))
    horiz = Vector((0.0, 0.0, 1.0)).cross(z)
    horiz = horiz.normalized() if horiz.length > 1e-6 else Vector((1.0, 0.0, 0.0))
    down = Vector((0.0, 0.0, -1.0))
    dn_t = down - z * z.dot(down)
    dn_t = dn_t.normalized() if dn_t.length > 1e-4 else -horiz.cross(z).normalized()
    dirs = {"straight": z,
            "45": (z + horiz).normalized(),
            # ~68 deg off the normal, from below the wound looking up along
            # the stream at the lip it pours over (the skin falls away from
            # this camera, so the stream and the rim face it)
            "graze": (z * 0.37 + (horiz if side else dn_t) * 0.93).normalized()}
    return {v: ghc.add_camera(f"PROOF_{v}", tgt + d * dist, tgt, 85.0) for v, d in dirs.items()}


def _mesh_arrays(ob):
    """Evaluated mesh: vertex coords, per-vertex material class, run id/param, wound/depth."""
    dg = bpy.context.evaluated_depsgraph_get()
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    mw = np.array(ob.matrix_world)
    co = co @ mw[:3, :3].T + mw[:3, 3]

    def att(name):
        a = me.attributes.get(name)
        v = np.zeros(n, np.float32)
        if a is not None and a.domain == 'POINT' and a.data_type == 'FLOAT':
            a.data.foreach_get("value", v)
        return v
    run, runf, wound, depth, blood = att("gore_run"), att("gore_runf"), att("gore_wound"), att("gore_depth"), \
        att("gore_blood")
    mi = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("material_index", mi)
    lt = np.zeros(len(me.polygons), np.int32)
    me.polygons.foreach_get("loop_total", lt)
    lv = np.zeros(len(me.loops), np.int32)
    me.loops.foreach_get("vertex_index", lv)
    cls_names = [_mask_class(m.name if m else None) for m in me.materials]
    fcls = np.array([cls_names[i] if i < len(cls_names) else "other" for i in mi]) if len(mi) else np.array([])
    vcls = np.full(n, "", dtype=object)
    vcls[lv] = np.repeat(fcls, lt)
    ev.to_mesh_clear()
    return dict(co=co, run=run, runf=runf, wound=wound, depth=depth, blood=blood, vcls=vcls)


def _main_axis(m, centre, reach, skip=()):
    """Centre line of the wound's main run, from inside the opening to BELOW_RIM past the rim.

    Returns (axis points (k, 3), index of the rim point) or (None, None)."""
    film = (m["vcls"] == "blood") & (m["run"] > 0.5)
    if not film.any():
        return None, None
    ids = np.round(m["run"][film]).astype(int)
    co_f, rf = m["co"][film], m["runf"][film]
    best, best_n = None, 0
    for rid in np.unique(ids):
        sel = ids == rid
        start = co_f[sel][np.argmin(rf[sel])]
        if np.linalg.norm(start - centre) > reach or rid in skip:
            continue
        # the main run: the longest one leaving this wound
        if sel.sum() > best_n:
            best, best_n = rid, sel.sum()
    if best is None:
        return None, None
    sel = ids == best
    pts, f = co_f[sel], rf[sel]
    order = np.argsort(f)
    pts, f = pts[order], f[order]
    bins = np.linspace(0.0, f.max() + 1e-6, 90)
    axis = []
    for a, b in zip(bins[:-1], bins[1:]):
        k = (f >= a) & (f < b)
        if k.any():
            axis.append(pts[k].mean(axis=0))
    axis = np.array(axis)
    # rim: first axis point whose nearest skin vertex is intact skin
    skin = (m["vcls"] == "skin")
    sco = m["co"][skin]
    intact = (m["wound"][skin] < 0.05) & (m["depth"][skin] < 0.01)
    rim = None
    for i, p in enumerate(axis):
        d = np.linalg.norm(sco - p, axis=1)
        j = np.argmin(d)
        if intact[j] and d[j] < 0.0025:
            rim = i
            break
    if rim is None:
        return None, None
    _main_axis.last = best
    # extend to BELOW_RIM past the rim (arc length)
    arc = np.concatenate([[0.0], np.cumsum(np.linalg.norm(np.diff(axis, axis=0), axis=1))])
    end = np.searchsorted(arc, arc[rim] + BELOW_RIM)
    return axis[:max(end + 1, rim + 2)], rim


def _stray_outside(m, centre, reach):
    """Blood on intact skin farther than 4 mm from any wound vertex and from
    any blood geometry: blood that got there without a path (t = 0 check)."""
    from mathutils.kdtree import KDTree
    skin = (m["vcls"] == "skin") & (m["blood"] > 0.3) & (m["wound"] < 0.05) & (m["depth"] < 0.01)
    if not skin.any():
        return 0
    src = np.where((m["wound"] > 0.3) | (m["depth"] > 0.02) | (m["vcls"] == "blood") | (m["vcls"] == "wall"))[0]
    if len(src) == 0:
        return int(skin.sum())
    kd = KDTree(len(src))
    for k, i in enumerate(src):
        kd.insert(m["co"][i], k)
    kd.balance()
    return sum(1 for p in m["co"][skin] if kd.find(p)[2] > 0.004)


def _densify(axis, step=0.00015):
    out = [axis[0]]
    for a, b in zip(axis[:-1], axis[1:]):
        n = max(1, int(np.linalg.norm(b - a) / step))
        for k in range(1, n + 1):
            out.append(a + (b - a) * (k / n))
    return np.array(out)


def _visible(cam, pts):
    """Per point: not hidden behind other surfaces as seen from the camera."""
    dg = bpy.context.evaluated_depsgraph_get()
    sc = bpy.context.scene
    o = cam.matrix_world.translation
    vis = []
    for p in pts:
        p = Vector(p)
        d = p - o
        L = d.length
        hit, loc, _n, _i, _ob, _m = sc.ray_cast(dg, o, d.normalized(), distance=L + 0.001)
        vis.append((not hit) or (loc - o).length > L - 0.0012)
    return np.array(vis)


def _project(cam, pts, res):
    sc = bpy.context.scene
    uv = []
    for p in pts:
        c = world_to_camera_view(sc, cam, Vector(p))
        uv.append((c.x * res, c.y * res))       # y up (numpy rows from the bottom, like bpy pixels)
    return np.array(uv)


def _render_mask(cam, path, res):
    """Material-ID mask of the same frame: every material temporarily emits its
    class colour (Cycles, 1 sample, box filter: exact, no anti-aliasing)."""
    sc = bpy.context.scene
    patched = []
    for mat in bpy.data.materials:
        if not mat.use_nodes or mat.node_tree is None:
            continue
        nt = mat.node_tree
        outs = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL']
        if not outs:
            continue
        o = outs[0]
        old = [lk.from_socket for lk in o.inputs['Surface'].links]
        oldd = [lk.from_socket for lk in o.inputs['Displacement'].links]
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs['Color'].default_value = (*MASK_COLORS[_mask_class(mat.name)], 1.0)
        em.inputs['Strength'].default_value = 1.0
        nt.links.new(em.outputs[0], o.inputs['Surface'])
        for lk in list(o.inputs['Displacement'].links):
            nt.links.remove(lk)
        patched.append((nt, o, em, old, oldd))
    world = sc.world
    wstr = None
    if world is not None and world.use_nodes:
        bg = [n for n in world.node_tree.nodes if n.type == 'BACKGROUND']
        if bg:
            wstr = (bg[0], bg[0].inputs['Strength'].default_value)
            bg[0].inputs['Strength'].default_value = 0.0
    lights = [(ob, ob.hide_render) for ob in sc.objects if ob.type == 'LIGHT']
    for ob, _h in lights:
        ob.hide_render = True
    vt = sc.view_settings.view_transform
    sc.view_settings.view_transform = 'Standard'
    exp = sc.view_settings.exposure
    sc.view_settings.exposure = 0.0
    fw, den = sc.cycles.filter_width, sc.cycles.use_denoising
    sc.cycles.filter_width = 0.01
    ghc.configure_render(1, (res, res))
    sc.cycles.use_denoising = False
    sc.cycles.filter_width = 0.01
    sc.camera = cam
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    sc.cycles.filter_width, sc.cycles.use_denoising = fw, den
    sc.view_settings.view_transform = vt
    sc.view_settings.exposure = exp
    for ob, h in lights:
        ob.hide_render = h
    if wstr is not None:
        wstr[0].inputs['Strength'].default_value = wstr[1]
    for nt, o, em, old, oldd in patched:
        nt.nodes.remove(em)
        for s_ in old:
            nt.links.new(s_, o.inputs['Surface'])
        for s_ in oldd:
            nt.links.new(s_, o.inputs['Displacement'])
    return _read_png(path)


def _mask_label(px):
    """Mask pixels -> class names."""
    r, g, b = px[..., 0] > 0.5, px[..., 1] > 0.5, px[..., 2] > 0.5
    lab = np.full(px.shape[:2], "other", dtype=object)
    lab[g & ~r & ~b] = "skin"
    lab[r & g & ~b] = "wall"
    lab[r & ~g & ~b] = "blood"
    lab[~r & ~g & ~b] = "bg"
    return lab


# a tiny 3x5 bitmap font for the sheet labels
_FONT = {
    "0": "111101101101111", "1": "010110010010111", "2": "111001111100111", "3": "111001111001111",
    "4": "101101111001001", "5": "111100111001111", "6": "111100111101111", "7": "111001010010010",
    "8": "111101111101111", "9": "111101111001111", "A": "010101111101101", "B": "110101110101110",
    "C": "011100100100011", "D": "110101101101110", "E": "111100110100111", "F": "111100110100100",
    "G": "011100101101011", "H": "101101111101101", "I": "111010010010111", "K": "101101110101101",
    "L": "100100100100111", "N": "110101101101101", "O": "010101101101010", "P": "110101110100100",
    "R": "110101110101101", "S": "011100010001110", "T": "111010010010010", "U": "101101101101111",
    "X": "101101010101101", "Y": "101101010010010", "Z": "111001010100111", " ": "000000000000000",
    "/": "001001010100100", ":": "000010000010000", "-": "000000111000000", ".": "000000000000010",
}


def _text(img, x, y, s, col, scale=2):
    """Draw text into img (rows from the top) at pixel (x, y)."""
    for ch in s.upper():
        glyph = _FONT.get(ch, _FONT[" "])
        for i, bit in enumerate(glyph):
            if bit == "1":
                r, c = divmod(i, 3)
                img[y + r * scale:y + (r + 1) * scale, x + c * scale:x + (c + 1) * scale] = col
        x += 4 * scale


def _crop(img, uv, size):
    """Square crop (rows from the top) centred on the axis' bounding box."""
    h, w = img.shape[:2]
    cx, cy = uv[:, 0].mean(), uv[:, 1].mean()
    span = max(np.ptp(uv[:, 0]), np.ptp(uv[:, 1])) * 1.9 + 40
    x0, y0 = int(cx - span / 2), int(cy - span / 2)
    x0, y0 = max(0, min(w - 1, x0)), max(0, min(h - 1, y0))
    x1, y1 = min(w, x0 + int(span)), min(h, y0 + int(span))
    sub = img[y0:y1, x0:x1]
    if sub.size == 0:
        sub = img
        x0 = y0 = 0
    ys = (np.arange(size) * sub.shape[0] / size).astype(int)
    xs = (np.arange(size) * sub.shape[1] / size).astype(int)
    return sub[ys][:, xs], (x0, y0, sub.shape[1] / size, sub.shape[0] / size)


def run(args):
    ghc_path = os.path.join(ghc.HERE, "gore_head.blend")
    bpy.ops.wm.open_mainfile(filepath=args.blend or ghc_path)
    import build  # noqa: E402  (after loading: build imports the scene helpers)
    if args.rebuild:
        import materials  # noqa: E402
        mats = materials.build_materials()
        gore.build_gore_node_group()
        bpy.data.node_groups[gore.GROUP_NAME]["gh_gore_version"] = gore._GROUP_VERSION
        gore.build_gore_system(None, mats)
    build.setup_cameras()
    sc = bpy.context.scene
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = args.threads
    ctrl = ghc.ensure_controls()
    skin = bpy.data.objects["GH_Skin"]
    tmp = os.path.join(args.tmp, "proof")
    os.makedirs(tmp, exist_ok=True)
    tile = args.tile
    rows, results = [], []
    wounds = [w for w in WOUNDS if not args.only or w[0] in args.only]
    times = args.times or TIMES
    for label, preset, hit_name, dist in wounds:
        build.apply_preset(preset)
        hit = bpy.data.objects[hit_name]
        centre = np.array(hit.matrix_world.translation)
        reach = {"blast": 0.07, "slash": 0.05, "crushed": 0.05}.get(label, 0.03)
        row = {v: [] for v in VIEWS}
        for sec in times:
            ctrl["drip_time"] = sec / 60.0
            ctrl.update_tag()
            bpy.context.view_layer.update()
            m = _mesh_arrays(skin)
            # the main run = the longest one leaving this wound whose rim point
            # can be seen at all (in a caved-in crater a run may start and stay
            # deep inside, hidden by the crater's own edge from every side)
            skip = []
            for _try in range(6):
                axis, rim = _main_axis(m, centre, reach, skip)
                if axis is None:
                    break
                cams = _cameras(hit, dist, axis[rim] + np.array([0.0, 0.0, -0.002]))
                if any(_visible(c, axis[rim:rim + 1]).any() for c in cams.values()):
                    break
                skip.append(_main_axis.last)
            if axis is None:
                cams = _cameras(hit, dist)
            for v in VIEWS:
                cam = cams[v]
                base = os.path.join(tmp, f"{label}_{v}_{sec:02d}")
                t0 = time.time()
                ghc.render(base + ".png", cam, args.samples, (args.res, args.res))
                img = _read_png(base + ".png")
                if axis is None:
                    stray = _stray_outside(m, centre, reach)
                    ok = stray == 0
                    # nothing has left the wound yet: crop around the hit
                    uv = _project(cam, [centre + np.array([0.0, 0.0, -0.004]) + d
                                        for d in ((0.004, 0, 0), (-0.004, 0, 0), (0, 0, 0.004), (0, 0, -0.008))],
                                  args.res)
                    res_ = dict(wound=label, view=v, t=sec, samples=0, gap=0, stray=stray, ok=ok,
                                note="no run yet")
                else:
                    mask = _mask_label(_render_mask(cam, base + "_mask.png", args.res))
                    dense = _densify(axis)
                    uv = _project(cam, dense, args.res)
                    vis = _visible(cam, dense)
                    gap, n = 0, 0
                    bad = []
                    for (x, y), vv in zip(uv, vis):
                        xi, yi = int(x), int(y)
                        if not vv or not (0 <= xi < args.res and 0 <= yi < args.res):
                            continue
                        n += 1
                        lab = mask[yi, xi]
                        if lab in ("skin", "wall") and _skin_like(img[yi, xi]):
                            gap += 1
                            bad.append((xi, yi))
                    note = ""
                    if n == 0 and not args._retry:
                        # the chin, brow or nose hides the rim from this side: look across it from the side
                        args._retry = True
                        side = _cameras(hit, dist, axis[rim] + np.array([0.0, 0.0, -0.002]), side=True)["graze"]
                        cam = side
                        ghc.render(base + ".png", cam, args.samples, (args.res, args.res))
                        img = _read_png(base + ".png")
                        mask = _mask_label(_render_mask(cam, base + "_mask.png", args.res))
                        uv = _project(cam, dense, args.res)
                        vis = _visible(cam, dense)
                        for (x, y), vv in zip(uv, vis):
                            xi, yi = int(x), int(y)
                            if not vv or not (0 <= xi < args.res and 0 <= yi < args.res):
                                continue
                            n += 1
                            if mask[yi, xi] in ("skin", "wall") and _skin_like(img[yi, xi]):
                                gap += 1
                                bad.append((xi, yi))
                        note = "side view"
                    args._retry = False
                    res_ = dict(wound=label, view=v, t=sec, samples=n, gap=gap, stray=0, ok=(gap == 0 and n > 0),
                                note=note)
                results.append(res_)
                # crop (rows from the top) with the axis drawn in
                disp = np.clip(img[::-1], 0.0, 1.0) ** (1.0 / 1.0)
                uvt = uv.copy()
                uvt[:, 1] = args.res - 1 - uvt[:, 1]
                crop, (x0, y0, sx, sy) = _crop(disp, uvt, tile)
                for (x, y) in uvt[::4]:
                    cx, cy = int((x - x0) / sx), int((y - y0) / sy)
                    if 0 <= cx < tile and 0 <= cy < tile:
                        crop[cy, cx] = (0.1, 0.9, 1.0)
                if axis is not None:
                    ru = _project(cam, [axis[rim]], args.res)[0]
                    cx, cy = int((ru[0] - x0) / sx), int((args.res - 1 - ru[1] - y0) / sy)
                    for dd in range(-3, 4):
                        for (px_, py_) in ((cx + dd, cy), (cx, cy + dd)):
                            if 0 <= px_ < tile and 0 <= py_ < tile:
                                crop[py_, px_] = (1.0, 0.9, 0.0)
                if axis is not None and res_["gap"]:
                    for (x, y) in bad:
                        cx, cy = int((x - x0) / sx), int((args.res - 1 - y - y0) / sy)
                        if 0 <= cx < tile and 0 <= cy < tile:
                            crop[max(0, cy - 1):cy + 2, max(0, cx - 1):cx + 2] = (1.0, 0.0, 1.0)
                cell = np.zeros((tile + 16, tile, 3), np.float32)
                cell[:tile] = crop
                cell[tile:] = (0.1, 0.6, 0.15) if res_["ok"] else (0.75, 0.08, 0.08)
                _text(cell, 3, tile + 3, f"{sec}S {res_['gap']}/{res_['samples']}", (1, 1, 1))
                row[v].append(cell)
                print(f"[proof] {label:8s} {v:8s} t={sec:2d}s samples={res_['samples']:4d} gap_px={res_['gap']:3d} "
                      f"stray={res_['stray']} {'PASS' if res_['ok'] else 'FAIL'} {res_['note']} "
                      f"({time.time() - t0:.1f}s)", flush=True)
        for v in VIEWS:
            head = np.zeros((tile + 16, 150, 3), np.float32)
            _text(head, 4, 8, label, (1, 1, 1), 3)
            _text(head, 4, 34, v, (0.8, 0.8, 0.8), 2)
            rows.append(np.concatenate([head] + [np.concatenate([c, np.zeros((c.shape[0], 3, 3), np.float32)], 1)
                                                 for c in row[v]], 1))
    wmax = max(r.shape[1] for r in rows)
    sheet = np.concatenate([np.pad(r, ((0, 3), (0, wmax - r.shape[1]), (0, 0))) for r in rows], 0)
    title = np.zeros((30, wmax, 3), np.float32)
    npass = sum(r["ok"] for r in results)
    _text(title, 6, 6, f"ZERO GAP PROOF: {npass}/{len(results)} PASS  TIMES {' '.join(str(t) for t in times)} S",
          (1, 1, 1), 3)
    sheet = np.concatenate([title, sheet], 0)
    out = os.path.abspath(args.out)
    img = bpy.data.images.new("proof_sheet", sheet.shape[1], sheet.shape[0], alpha=True)
    rgba = np.concatenate([sheet[::-1], np.ones(sheet.shape[:2] + (1,), np.float32)], 2)
    img.pixels[:] = rgba.ravel()
    img.filepath_raw = out
    img.file_format = 'PNG'
    img.save()
    print(f"[proof] {npass}/{len(results)} PASS -> {out}")
    return results


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("--res", type=int, default=240)
    p.add_argument("--samples", type=int, default=12)
    p.add_argument("--threads", type=int, default=2)
    p.add_argument("--tile", type=int, default=120)
    p.add_argument("--times", type=int, nargs="*")
    p.add_argument("--only", nargs="*", help="subset of wound labels")
    p.add_argument("--blend", default=None, help="scene to load (default gore_head.blend)")
    p.add_argument("--rebuild", action="store_true",
                   help="rebuild the materials and the gore node group from the current code first")
    p.add_argument("--tmp", default=os.path.join(tempfile.gettempdir(), "gh_proof"))
    p.add_argument("--out", default=os.path.join(ghc.RENDER_DIR, "proof_rim_zero_gap.png"))
    args = p.parse_args(argv)
    args._retry = False
    run(args)


if __name__ == "__main__":
    main()
