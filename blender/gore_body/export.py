"""glTF export, JSON sidecars, manifest, LOD1 and the export checks (owner B6).

Plan §3.3.3, §4.3, §5.7-5.9, §8.2 B6.

Final entry points
------------------
``export_subject(objs, out)``  -> GB_Subject.glb, GB_Subject_LOD1.glb and every JSON sidecar (rig, landmarks,
                                  organs, vessels, spine, codes, brain_labels; bones.json from B3) in ``out``
``export_props(out)``          -> weapons.glb, room.glb, props.json, room.json (delegates to props.py, B8)
``write_manifest(out, ...)``   -> manifest.json: schema/generator versions, build id, input hashes, files
                                  (bytes + sha256), per-mesh counts/surfaces/keys, armature, rest bounds,
                                  wound grid, segment origins, the texture list with import hints, budget
                                  and file-size checks, rig/deformation/round-trip/Godot-import results
``round_trip(glb)``            -> re-imports a glb in a fresh Blender process and compares it with the scene
``godot_import_check(glb)``    -> imports the glb with Godot 4.5.1 headless in a temporary project and
                                  inspects the result (skeleton, skins, blend shapes, animations, CUSTOM0)

Before exporting, ``prepare_for_export`` re-applies B7's re-charted inner atlases (``bake.prepare_uvs``,
cached) so the exported UVs always match the baked textures, and refreshes the painter dominant-bone
maps (``bake.bake_painter_inputs``) whenever the weight model changed.

The glTF options are exactly plan §5.9 (verified in the bundled exporter 5.0.21).  Only the armature
and the contract meshes are exported (``use_selection``); GB_Data curves/empties, the high-res bake
sources, stage lights and cameras never reach the glb.
"""
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

import numpy as np

import bpy

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gb_common as gbc  # noqa: E402
from gb_data import bones as BN  # noqa: E402
from gb_data import brain as BR  # noqa: E402
from gb_data import dermatomes as DM  # noqa: E402
from gb_data import landmarks as LM  # noqa: E402
from gb_data import myotomes as MYO  # noqa: E402
from gb_data import organs as OR  # noqa: E402
from gb_data import segments as SG  # noqa: E402

GLTF_OPTIONS = dict(
    export_format='GLB', use_selection=True,
    export_yup=True, export_apply=False,
    export_texcoords=True, export_normals=True, export_tangents=True,
    export_materials='EXPORT', export_image_format='NONE', export_vertex_color='NONE',
    export_attributes=False, export_extras=True,
    export_skins=True, export_influence_nb=4, export_all_influences=False,
    export_def_bones=True, export_rest_position_armature=True, export_leaf_bone=False,
    export_morph=True, export_morph_normal=True, export_morph_tangent=False,
    export_animations=True, export_animation_mode='ACTIONS')

SUBJECT_GLB = "GB_Subject.glb"
LOD1_GLB = "GB_Subject_LOD1.glb"
# Godot 4.5.1 binary for the import check: $GODOT_BIN (e.g. the Windows .exe path on the user's PC), else the
# cloud container's install.  When missing the check is reported as skipped with a visible warning.
GODOT_BIN = os.environ.get("GODOT_BIN", "/opt/godot/Godot_v4.5.1-stable_linux.x86_64")
# plan §3.3.3 wound lookup grid: 2.5 cm cells over the measured A-pose rest bounds + 1 cell margin
WOUND_CELL_M = 0.025
# sidecars written by other stages (kept in the manifest file list when present)
FOREIGN_SIDECARS = ("bones.json",)
# results of the export checks run in this process (verify fills them; the final manifest reports them)
CHECKS = {}


def _select_only(objs):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.hide_set(False)
        o.hide_viewport = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]


def _collection_visibility(on=True):
    """Exclude nothing: variants/LOD collections must be in the view layer to be selectable."""
    for lc in bpy.context.view_layer.layer_collection.children:
        lc.exclude = False
        for c in lc.children:
            c.exclude = False


def export_glb(path, mesh_names):
    """Export the armature plus the named meshes (those that exist) with the plan §5.9 options."""
    arm = bpy.data.objects[gbc.ARMATURE]
    objs = [arm] + [bpy.data.objects[n] for n in mesh_names if n in bpy.data.objects]
    _collection_visibility()
    _select_only(objs)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=path, **GLTF_OPTIONS)
    return path, [o.name for o in objs]


# ---------------------------------------------------------------------------
# Pre-export: B7 atlases and painter bone maps must match what is exported
# ---------------------------------------------------------------------------
def weights_hash(names=("GB_Head", "GB_Body", "GB_Shorts")):
    """Fingerprint of the analytic weight function on the painter meshes (every 5th vertex)."""
    import rig
    h = hashlib.sha256()
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        v = gbc.get_verts(o.data)[::5]
        idx, w = rig.weights_at(v)
        h.update(n.encode())
        h.update(idx.astype(np.int32).tobytes())
        h.update(np.rint(w * rig.QUANT).astype(np.int32).tobytes())
    return h.hexdigest()[:16]


def _previous_manifest(out):
    path = os.path.join(out, "manifest.json")
    if not os.path.exists(path):
        return {}
    try:
        return gbc.read_json(path)["data"]
    except (ValueError, KeyError):
        return {}


def prepare_for_export(out=gbc.SUBJECT_OUT, refresh_painter=True):
    """Re-apply B7's inner-mesh atlases and refresh the painter bone maps if the weights changed."""
    res = {"uvs": "bake module unavailable", "painter": "unchanged"}
    try:
        import bake
    except Exception as exc:                                         # pragma: no cover - B7 missing
        res["uvs"] = f"bake import failed: {exc}"
        return res
    try:
        with gbc.Timer("export: B7 atlases (bake.prepare_uvs)"):
            res["uvs"] = {k: bool(v.get("cached", False)) for k, v in bake.prepare_uvs().items()}
    except Exception as exc:                                         # pragma: no cover
        res["uvs"] = f"prepare_uvs failed: {exc}"
    wh = weights_hash()
    res["weights_hash"] = wh
    prev = _previous_manifest(out).get("rig", {}).get("painter_weights_hash")
    tex = os.path.join(out, "textures")
    have = all(os.path.exists(os.path.join(tex, f"{s}_bone.png")) for s in ("head", "body", "shorts"))
    if refresh_painter and (prev != wh or not have):
        present = {n: bpy.data.objects[n] for n in ("GB_Head", "GB_Body", "GB_Shorts") if n in bpy.data.objects}
        with gbc.Timer("export: painter bone maps (bake.bake_painter_inputs)"):
            bake.bake_painter_inputs(present, tex)
        res["painter"] = "refreshed (weight model changed)"
    CHECKS["painter_weights_hash"] = wh
    CHECKS["prepare"] = res
    return res


# ---------------------------------------------------------------------------
# JSON payloads owned by B0 (landmarks, codes)
# ---------------------------------------------------------------------------
def landmarks_table():
    """landmarks.json 'data': body landmarks (L and mirrored R), head contract (body frame), girths, eyes."""
    head = {}
    try:
        A = gbc.import_head().anatomy
        for k, v in A.ANATOMY_LANDMARKS.items():
            if isinstance(v, tuple) and len(v) == 3:
                head[k] = gbc.head_to_body(v).tolist()
    except Exception as exc:                                         # pragma: no cover - reported, not fatal
        head["_error"] = str(exc)
    contract = {k: gbc.head_to_body(v).tolist() for k, v in LM.HEAD_CONTRACT.items()}
    return {
        "landmarks": {k: list(v) for k, v in LM.all_landmarks().items()},
        "landmark_tags": {k: v["tag"] for k, v in {**LM.LANDMARKS, **LM.LANDMARKS_EXTRA}.items()},
        "head": {"measured": head, "contract_rb_1_2": contract, "offset": gbc.HEAD_OFFSET.tolist(),
                 "seam_z": gbc.SEAM_Z},
        "girths": LM.GIRTHS, "arm_girths": LM.ARM_GIRTHS, "hand": LM.HAND, "foot": LM.FOOT,
        "eyes": {"L": gbc.head_to_body(np.array(LM.HEAD_CONTRACT["eye_L"])).tolist(),
                 "R": gbc.head_to_body(np.array(LM.HEAD_CONTRACT["eye_R"])).tolist(),
                 "constants": LM.EYE_CONSTANTS},
        "body": {"stature_m": LM.STATURE_M, "mass_kg": LM.MASS_KG, "body_fat_pct": LM.BODY_FAT_PCT,
                 "bsa_m2": LM.BSA_M2, "arm_direction_L": list(LM.ARM_DIRECTION_L),
                 "arm_medial_normal_L": list(LM.ARM_MEDIAL_NORMAL_L), "foot_axis_L": list(LM.FOOT_AXIS_L)},
        "segment_masses": {k: {"fraction": v[0], "mass_kg": v[0] * SG.BODY_MASS_KG, "com_from_proximal": v[1],
                               "radius_of_gyration": v[2], "definition": v[3]}
                           for k, v in SG.SEGMENT_MASS.items()},
    }


CORD_EXTRA = {"30": "cauda_equina", "31": "dura"}      # B4: 40 + n = root stub of cord segment n


def codes_table():
    """codes.json 'data': every integer code carried in UV2 / CUSTOM0.w (plan §5.5)."""
    cord = {str(i): s for i, s in enumerate(MYO.CORD_SEGMENTS)}
    cord.update(CORD_EXTRA)
    cord.update({str(40 + i): f"root_{s}" for i, s in enumerate(MYO.CORD_SEGMENTS)})
    return {
        "segment": {str(k): v for k, v in SG.SEGMENTS.items()},
        "region": {str(k): v for k, v in SG.REGIONS.items()},
        "dermatome": {str(k): v for k, v in DM.DERMATOMES.items()},
        "bone_class": {str(k): v for k, v in BN.BONE_CLASS.items()},
        "bone_piece": {str(v): k for k, v in BN.BONE_PIECE_ID.items()},
        "organ": {str(o["organ_id"]): o["id"] for o in OR.ORGANS},
        "brain_region": {str(k): v[0] for k, v in BR.BRAIN_REGIONS.items()},
        "cord_segment": cord,
        "region_stride": SG.REGION_STRIDE,
        "uv2": {
            "GB_Head, GB_Body, GB_Shorts, GB_MuscleShell, GB_*_LOD1": "x = segment + 32 * region, y = dermatome",
            "GB_Eye_*, GB_EyeFX_*": "x = 0 + 32 * region(eyelid_lip) = 64, y = 0",
            "GB_Mouth": "x = 64, y = FDI tooth number (0 = gums / tongue) (B2)",
            "GB_BrowLash": "x = 32 (face), y = 0",
            "GB_Skeleton, GB_Frac_*": "x = bone piece id, y = bone class (6 = marrow core; fracture fragments = "
                                      "loose islands, gb_frag index in bones.json)",
            "GB_Organs": "x = organ id, y = sub-part id (organs.json sub_parts; heart 1 RA, 2 RV, 3 LA, 4 LV)",
            "GB_Vessels_Art, GB_Vessels_Ven": "x = vessel_index (vessels.json), y = t along the segment 0..1",
            "GB_Brain": "x = brain region id, y = sulcus depth 0..1",
            "GB_Cord": "x = cord segment index (C1 = 0 ... S5 = 29), 30 cauda equina, 31 dura, 40 + n root stub of "
                       "segment n; y = t",
            "v_flip": "Blender stores 1 - v; the glTF exporter flips V, so Godot reads UV2 = (x, y) exactly",
        },
        "custom0_w": "segment code (plan §3.3.1) for skin-like meshes; piece/organ id otherwise (G0 import)",
    }


def write_sidecars(out):
    """Write every JSON sidecar and the brain label atlas; returns {file: path}."""
    import neuro
    import rig
    import vascular
    import viscera
    files = {}
    files["rig.json"] = gbc.write_json(os.path.join(out, "rig.json"), rig.rig_table(), "gb.rig/1")
    files["landmarks.json"] = gbc.write_json(os.path.join(out, "landmarks.json"), landmarks_table(),
                                             "gb.landmarks/1")
    files["organs.json"] = gbc.write_json(os.path.join(out, "organs.json"), viscera.organ_table(), "gb.organs/1")
    files["vessels.json"] = gbc.write_json(os.path.join(out, "vessels.json"), vascular.vessel_table(),
                                           "gb.vessels/1")
    files["spine.json"] = gbc.write_json(os.path.join(out, "spine.json"), neuro.spine_table(), "gb.spine/1")
    files["codes.json"] = gbc.write_json(os.path.join(out, "codes.json"), codes_table(), "gb.codes/1")
    labels, meta = neuro.brain_labels()
    files["brain_labels.png"] = gbc.write_png_u8(os.path.join(out, "brain_labels.png"), neuro.labels_atlas(labels))
    files["brain_labels.json"] = gbc.write_json(os.path.join(out, "brain_labels.json"), meta, "gb.brain_labels/1")
    for f in FOREIGN_SIDECARS:
        p = os.path.join(out, f)
        if os.path.exists(p):
            files[f] = p
    return files


# ---------------------------------------------------------------------------
# Manifest
# ---------------------------------------------------------------------------
def mesh_stats(obj):
    """Vertex/triangle counts, surfaces (used material slots) and shape keys of a mesh object."""
    me = obj.data
    me.calc_loop_triangles()
    mi = np.empty(len(me.loop_triangles), dtype=np.int32)
    me.loop_triangles.foreach_get("material_index", mi)
    surf = {}
    for i, m in enumerate(me.materials):
        n = int((mi == i).sum())
        if n:
            surf[m.name if m else f"slot{i}"] = n
    keys = [k.name for k in me.shape_keys.key_blocks[1:]] if me.shape_keys else []
    return {"vertices": len(me.vertices), "triangles": len(me.loop_triangles), "surfaces": surf,
            "shape_keys": keys, "layer": obj.get("gb_layer", ""), "status": obj.get("gb_status", "built"),
            "uv_maps": [l.name for l in me.uv_layers], "bones_used": len(obj.vertex_groups)}


def rest_bounds(names):
    """Axis-aligned rest bounds (body frame) of the named meshes."""
    lo, hi = np.full(3, np.inf), np.full(3, -np.inf)
    for n in names:
        o = bpy.data.objects.get(n)
        if o is None or o.type != 'MESH' or not len(o.data.vertices):
            continue
        v = gbc.get_verts(o.data)
        lo, hi = np.minimum(lo, v.min(0)), np.maximum(hi, v.max(0))
    return lo, hi


def wound_grid(lo, hi):
    """Wound lookup grid in the Godot rest frame (plan §3.3.3): 2.5 cm cells + 1 cell margin."""
    glo, ghi = gbc.b2g(lo), gbc.b2g(hi)
    g_lo, g_hi = np.minimum(glo, ghi) - WOUND_CELL_M, np.maximum(glo, ghi) + WOUND_CELL_M
    dims = np.ceil((g_hi - g_lo) / WOUND_CELL_M).astype(int)
    return {"frame": "godot_rest", "origin": g_lo.tolist(), "cell_m": WOUND_CELL_M, "dims": dims.tolist(),
            "format": "RGBA8 (index + 1, 0 = empty), 4 wounds per cell", "bytes": int(np.prod(dims) * 4)}


def segment_origins():
    """Per skin segment origin (min corner of its rest bounds) for the segment-relative position maps."""
    out = {}
    pts = {k: [] for k in SG.SEGMENTS}
    for n in ("GB_Head", "GB_Body", "GB_Shorts"):
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        seg = gbc.read_point_attr(o, "gb_seg", 'INT')
        if seg is None:
            continue
        v = gbc.get_verts(o.data)
        for k in np.unique(seg):
            pts[int(k)].append(v[seg == k])
    for k, lst in pts.items():
        if lst:
            v = np.vstack(lst)
            out[SG.SEGMENTS[k]] = {"code": k, "origin": v.min(0).tolist(), "extent": (v.max(0) - v.min(0)).tolist()}
    return out


def budget_checks(meshes):
    """Plan §4.1 triangle budgets: ``ok`` = tris <= budget; ``within_tolerance`` = tris <= budget + 10 %."""
    res = {}
    for key, budget in gbc.TRI_BUDGET.items():
        names = gbc.TRI_BUDGET_GROUPS.get(key, (key,))
        tris = sum(meshes[n]["triangles"] for n in names if n in meshes)
        res[key] = {"triangles": tris, "budget": budget, "ok": tris <= budget,
                    "within_tolerance": tris <= budget * 1.10}
    return res


def file_checks(out):
    """Every file under ``out`` < 50 MB, GB_Subject.glb <= 40 MB, 2048^2 PNG <= 12 MB (plan §4.3)."""
    bad, total, biggest = [], 0, ("", 0)
    for root, _d, files in os.walk(out):
        for f in files:
            p = os.path.join(root, f)
            b = os.path.getsize(p)
            total += b
            if b > biggest[1]:
                biggest = (os.path.relpath(p, out), b)
            if b > gbc.FILE_LIMITS_MB["any"] * 1e6 or (f == SUBJECT_GLB and b > gbc.FILE_LIMITS_MB[SUBJECT_GLB] * 1e6) \
                    or (f.endswith(".png") and b > 12e6):
                bad.append(f"{os.path.relpath(p, out)} {b / 1e6:.1f} MB")
    return {"ok": not bad, "over": bad, "total_mb": round(total / 1e6, 2),
            "largest": {"file": biggest[0], "mb": round(biggest[1] / 1e6, 2)},
            "limits_mb": {"any": gbc.FILE_LIMITS_MB["any"], SUBJECT_GLB: gbc.FILE_LIMITS_MB[SUBJECT_GLB],
                          "png": 12.0, "generated_total": 250.0}}


# import hints per texture role (plan §4.2); Godot's importer settings for G0
_TEX_HINT = {"albedo": "VRAM compressed (BC7), sRGB, mipmaps", "normal": "normal map (RGTC/BC5), linear, mipmaps",
             "orm": "VRAM compressed (BC7), linear, mipmaps", "height": "linear",
             "position": "lossless, uncompressed (half float EXR), no mipmaps, no filtering",
             "rest_normal": "lossless, no mipmaps", "valid": "lossless, no mipmaps, nearest",
             "bone": "lossless, no mipmaps, nearest (indices)", "tissue_depth": "lossless, linear",
             "tension": "lossless, linear", "hair": "VRAM compressed (BC7), sRGB, alpha scissor 0.35"}


def texture_list(out):
    """manifest 'textures': every texture set (B7 textures.json, B1 body_maps.json, B2 hair cards)."""
    tex_dir = os.path.join(out, "textures")
    res = {"sets": {}, "painter": {}, "extra": {}, "tileables": {}, "files": 0}
    tj = os.path.join(tex_dir, "textures.json")
    if os.path.exists(tj):
        d = gbc.read_json(tj)["data"]
        for name, s in d.get("sets", {}).items():
            res["sets"][name] = {"mesh": s.get("target"), "lod1": s.get("lod1", []), "size": s.get("size"),
                                 "surfaces": s.get("surfaces", []), "uv_hash": s.get("uv_hash"),
                                 "files": {k: {"file": f, "import": _TEX_HINT.get(k, "")}
                                           for k, f in s.get("files", {}).items()}}
        for name, s in d.get("painter", {}).items():
            res["painter"][name] = {"mesh": s.get("mesh"), "size": s.get("size"), "bone_size": s.get("bone_size"),
                                    "files": {k: {"file": f, "import": _TEX_HINT.get(k, "")}
                                              for k, f in s.get("files", {}).items()}}
        res["tileables"] = {k: {"tile_m": v.get("tile_m"), "files": v.get("files")}
                            for k, v in d.get("tileables", {}).items()}
        res["eyes"] = d.get("eyes", {})
        res["decals"] = {k: d.get("decals", {}).get(k) for k in ("files", "grid", "tile_px", "count")}
        res["room"] = {k: {"tile_m": v.get("tile_m"), "files": v.get("files")} for k, v in d.get("room", {}).items()}
        res["material_map"] = d.get("material_map", {})
        res["conventions"] = d.get("conventions", {})
        res["texture_manifest"] = "textures/textures.json"
    bm = os.path.join(tex_dir, "body_maps.json")
    if os.path.exists(bm):
        d = gbc.read_json(bm)["data"]
        res["extra"]["body_maps"] = {"mesh": d.get("mesh"), "manifest": "textures/body_maps.json",
                                     "files": {"tissue_depth": {"file": d["tissue_depth"]["file"],
                                                                "import": _TEX_HINT["tissue_depth"]},
                                               "tension": {"file": d["tension"]["file"],
                                                           "import": _TEX_HINT["tension"]}}}
    if os.path.exists(os.path.join(tex_dir, "hair_cards.png")):
        res["extra"]["hair_cards"] = {"mesh": "GB_BrowLash", "files": {"albedo": {"file": "hair_cards.png",
                                                                                  "import": _TEX_HINT["hair"]}}}
    if os.path.isdir(tex_dir):
        res["files"] = len([f for f in os.listdir(tex_dir) if f.endswith((".png", ".exr"))])
    return res


def rig_summary():
    """manifest 'rig': bone fits, weight fingerprint, deformation-test and round-trip results of this build."""
    import rig
    fits = {b["name"]: {"head": list(b["head"]), "tail": list(b["tail"]), "note": b["note"]}
            for b in rig.bone_rows() if b.get("fit")}
    out = {"bones": len(rig.BONE_NAMES), "bone_fits": fits, "influences": rig.MAX_INF, "weight_grid": rig.QUANT,
           "painter_weights_hash": CHECKS.get("painter_weights_hash"),
           "twist_drivers": [list(t) for t in rig.TWIST_DRIVERS]}
    for k in ("deformation", "roundtrip", "godot_import", "prepare"):
        if k in CHECKS:
            out[k] = CHECKS[k]
    return out


def deformation_summary(res):
    """Compact per-test deformation results for the manifest."""
    return {k: {"level": v["level"], "ok": v["ok"], "poke_mm": v["poke_mm"], "poke_over_3mm": v["poke_over"],
                "vol_loss": v["vol_loss"], "shorts_mm": v.get("shorts_mm")} for k, v in res.items()}


def _file_build_id(path):
    """The envelope build_id of a generated JSON file (None for binaries / other files)."""
    if not path.endswith(".json"):
        return None
    try:
        return gbc.read_json(path).get("build_id")
    except Exception:                                                # pragma: no cover
        return None


def write_manifest(out, glb_paths=(), sidecars=None, pending=None, timings=None, quick=False, stage_keys=None,
                   status=None):
    """manifest.json (plan §5.7).  Returns the manifest data dict.

    ``stage_keys`` (build.stage_key per geometry stage) and ``status`` (built / cached / placeholder per
    stage) are recorded so verify can prove the loaded caches match the current sources.  Every listed
    file carries its own envelope build_id, and the texture block says which build produced the baked
    sets when the bake was skipped and earlier textures are reused."""
    meshes = {}
    for n in gbc.exported_mesh_names(0) + gbc.exported_mesh_names(1):
        o = bpy.data.objects.get(n)
        if o is not None and o.type == 'MESH':
            meshes[n] = mesh_stats(o)
    lo, hi = rest_bounds(list(gbc.OUTER_OBJECTS))
    files = {}
    for p in list(glb_paths) + list((sidecars or {}).values()):
        if p and os.path.exists(p):
            files[os.path.basename(p)] = {"bytes": os.path.getsize(p), "sha256": gbc.file_hash(p),
                                          "mb": round(os.path.getsize(p) / 1e6, 3)}
            bid = _file_build_id(p)
            if bid is not None:
                files[os.path.basename(p)]["build_id"] = bid
    try:
        import io_scene_gltf2
        exporter = ".".join(str(x) for x in io_scene_gltf2.bl_info["version"])
    except Exception:                                                # pragma: no cover
        exporter = "unknown"
    arm = bpy.data.objects.get(gbc.ARMATURE)
    textures = texture_list(out)
    pending = dict(pending or {})
    tj = os.path.join(out, "textures", "textures.json")
    if os.path.exists(tj):
        textures["build_id"] = _file_build_id(tj)
        if str(pending.get("bake", "")).startswith("skipped"):
            pending["bake"] = f"skipped: reusing textures baked by {textures['build_id']}"
    data = {
        "build": {"build_id": gbc.build_id(), "blender": bpy.app.version_string, "gltf_exporter": exporter,
                  "quick": bool(quick), "timings_s": timings or {},
                  "input_hashes": {os.path.relpath(p, gbc.HERE).replace(os.sep, "/"): gbc.file_hash(p)[:16]
                                   for p in gbc.source_files() if os.path.exists(p)},
                  "schemas": {k: k for k in gbc.SCHEMAS},
                  "stage_keys": dict(stage_keys or {}), "stage_status": dict(status or {})},
        "files": files,
        "meshes": meshes,
        "armature": {"bones": [b.name for b in arm.data.bones] if arm else [],
                     "actions": list(gbc.POSE_ACTIONS)},
        "rest_bounds": {"body_frame": {"min": lo.tolist(), "max": hi.tolist()},
                        "godot_rest": {"min": np.minimum(gbc.b2g(lo), gbc.b2g(hi)).tolist(),
                                       "max": np.maximum(gbc.b2g(lo), gbc.b2g(hi)).tolist()}},
        "wound_grid": wound_grid(lo, hi),
        "segment_origins": segment_origins(),
        "textures": textures,
        "texture_note": ("baked sets are plain PNG/EXR files next to the glb (no images inside the glb); the "
                         "import script builds ShaderMaterials from them by material name (plan D15)"),
        "budgets": budget_checks(meshes),
        "file_limits": file_checks(out),
        "rig": rig_summary(),
        "lod": {"lod0": SUBJECT_GLB, "lod1": LOD1_GLB,
                "lod1_meshes": {n: {"triangles": meshes[n]["triangles"], "lod0": n.replace("_LOD1", ""),
                                    "ratio": round(meshes[n]["triangles"] /
                                                   max(meshes.get(n.replace("_LOD1", ""), {}).get("triangles", 1), 1),
                                                   3)}
                                for n in gbc.LOD1_OBJECTS if n in meshes},
                "note": "LOD1 = head + body skin at ~50 % (same armature, weights, UV atlases, codes and shape "
                        "keys); every other mesh has one LOD (plan D18)"},
        "pending": pending,
        "import_hints": {"import_script": "res://pipeline/import/subject_post_import.gd",
                         "inner_meshes_hidden": list(gbc.INNER_OBJECTS) + list(gbc.VARIANT_OBJECTS),
                         "uv2": "codes (see codes.json)", "custom0": "rest position + segment (G0)",
                         "materials": "replace GBM_* by name (plan §5.6); textures per manifest 'textures'",
                         "hair_cards": "alpha scissor 0.35, double sided (B2)",
                         "face": "rig.json face: lid bones rotate + scale per lid_table; blend shapes on GB_Head, "
                                 "GB_EyeFX_L/R, GB_BrowLash, GB_Head_LOD1 are driven together by name (B2)",
                         "twist_bones": "drive rig.json kinematic.*_twist_*.driver every frame",
                         "animations": "pose_idle/guard/cower/brace: single-frame key poses (hips translation keeps "
                                       "the feet planted)"},
    }
    gbc.write_json(os.path.join(out, "manifest.json"), data, "gb.manifest/1")
    return data


def export_subject(objs=None, out=gbc.SUBJECT_OUT, pending=None, timings=None, quick=False, stage_keys=None,
                   status=None):
    """Export GB_Subject.glb (+ LOD1), every sidecar and the manifest into ``out``."""
    os.makedirs(out, exist_ok=True)
    prepare_for_export(out)
    lod0 = [n for n in gbc.exported_mesh_names(0) if n in bpy.data.objects]
    lod1 = [n for n in gbc.exported_mesh_names(1) if n in bpy.data.objects]
    glbs = [export_glb(os.path.join(out, SUBJECT_GLB), lod0)[0]]
    if lod1:
        glbs.append(export_glb(os.path.join(out, LOD1_GLB), lod1)[0])
    side = write_sidecars(out)
    man = write_manifest(out, glbs, side, pending, timings, quick, stage_keys, status)
    return {"glb": glbs, "sidecars": side, "manifest": os.path.join(out, "manifest.json"), "data": man}


def export_props(out=gbc.PROPS_OUT):
    """weapons.glb, room.glb, props.json and room.json from props.py (B8 builds and exports them)."""
    import props
    return props.export_props(out)


# ===========================================================================
# Round trip: re-import the glb in a clean Blender process and compare with the scene
# ===========================================================================
def scene_summary(mesh_names):
    """What the glb should contain: per mesh triangles, shape keys, materials, bones; bones; actions."""
    arm = bpy.data.objects[gbc.ARMATURE]
    meshes = {}
    for n in mesh_names:
        o = bpy.data.objects.get(n)
        if o is None:
            continue
        me = o.data
        me.calc_loop_triangles()
        mi = np.empty(len(me.loop_triangles), np.int32)
        me.loop_triangles.foreach_get("material_index", mi)
        used = sorted({me.materials[i].name for i in np.unique(mi) if i < len(me.materials) and me.materials[i]})
        meshes[n] = {"triangles": len(me.loop_triangles),
                     "shape_keys": [k.name for k in me.shape_keys.key_blocks[1:]] if me.shape_keys else [],
                     "materials": used, "groups": sorted(g.name for g in o.vertex_groups)}
    return {"meshes": meshes, "bones": sorted(b.name for b in arm.data.bones),
            "actions": sorted(gbc.POSE_ACTIONS)}


def _import_summary(glb):
    """(Runs in the child process) import ``glb`` into an empty file and summarise it."""
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes, bones = {}, []
    for o in bpy.data.objects:
        if o.type == 'MESH':
            me = o.data
            me.calc_loop_triangles()
            groups = sorted(g.name for g in o.vertex_groups)
            # glTF splits a mesh per material into primitives but Blender re-joins them on import
            meshes[o.name] = {"triangles": len(me.loop_triangles),
                              "shape_keys": [k.name for k in me.shape_keys.key_blocks[1:]] if me.shape_keys else [],
                              "materials": sorted({m.name for m in me.materials if m}), "groups": groups,
                              "uv_layers": len(me.uv_layers),
                              "max_influences": int(max((sum(1 for g in v.groups if g.weight > 0)
                                                         for v in me.vertices), default=0))}
        elif o.type == 'ARMATURE':
            bones = sorted(b.name for b in o.data.bones)
    return {"meshes": meshes, "bones": bones, "actions": sorted(a.name for a in bpy.data.actions)}


def round_trip(glb, mesh_names=None):
    """Re-import ``glb`` in a fresh Blender process; compare names, triangle counts, shape keys, materials,
    vertex groups, bones and actions with the current scene.  Returns (ok, detail dict)."""
    mesh_names = mesh_names or [n for n in gbc.exported_mesh_names(0) if n in bpy.data.objects]
    want = scene_summary(mesh_names)
    here = os.path.abspath(__file__)
    binary = bpy.app.binary_path or ""
    if binary and os.path.basename(binary).lower().startswith("blender"):
        cmd = [binary, "-b", "--factory-startup", "--python", here, "--", "--roundtrip", glb]
    else:
        cmd = [sys.executable, here, "--roundtrip", glb]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=900)
    line = next((l for l in proc.stdout.splitlines() if l.startswith("ROUNDTRIP ")), None)
    if line is None:
        return False, {"error": "no summary", "stderr": proc.stderr[-2000:], "stdout": proc.stdout[-2000:]}
    got = json.loads(line[len("ROUNDTRIP "):])
    probs = []
    if got["bones"] != want["bones"]:
        probs.append(f"bones differ ({len(got['bones'])} vs {len(want['bones'])})")
    if [a for a in want["actions"] if a not in got["actions"]]:
        probs.append(f"actions missing: {[a for a in want['actions'] if a not in got['actions']]}")
    for n, w in want["meshes"].items():
        g = got["meshes"].get(n)
        if g is None:
            probs.append(f"{n} missing")
            continue
        if g["triangles"] != w["triangles"]:
            probs.append(f"{n} triangles {g['triangles']} vs {w['triangles']}")
        if g["shape_keys"] != w["shape_keys"]:
            probs.append(f"{n} shape keys differ")
        if g["materials"] != w["materials"]:
            probs.append(f"{n} materials {g['materials']} vs {w['materials']}")
        if not set(g["groups"]) <= set(want["bones"]) or not set(w["groups"]) <= set(g["groups"]):
            probs.append(f"{n} vertex groups differ")
        if g["max_influences"] > 4:
            probs.append(f"{n} {g['max_influences']} influences")
    detail = {"meshes": len(got["meshes"]), "bones": len(got["bones"]), "actions": got["actions"],
              "problems": probs}
    return not probs, detail


# ===========================================================================
# Godot 4.5.1 headless import check (temporary project; nothing is written into gore-game/)
# ===========================================================================
_GODOT_CHECK_GD = r'''extends SceneTree
# B6 export check: load the imported subject, report skeleton / meshes / skins / blend shapes /
# animations, test CUSTOM0 injection (plan §3.3.1, FB-11 precursor) on one skinned surface, then pose
# the skeleton with rig.json's world axes (poses.json) and write GB_Body skinned by Godot
# (bake_mesh_from_current_skeleton_pose) so Blender can compare it with its own skinning.
var subj: Node
var frame := 0

func _initialize() -> void:
	var ps: PackedScene = load("res://GB_Subject.glb")
	if ps == null:
		print("GODOTCHECK " + JSON.stringify({"error": "load failed"}))
		quit(1)
		return
	subj = ps.instantiate()
	get_root().add_child(subj)

var result := {}
var pose_names := []
var pose_data := {}
var pose_i := -1
var wait := 0

func _process(_delta: float) -> bool:
	# frame-stepped: inspect, then for every pose: set it, let the skeleton update for 2 frames, bake
	frame += 1
	if frame < 2:
		return false
	if frame == 2:
		result = _inspect()
		result["poses"] = {}
		if FileAccess.file_exists("res://poses.json"):
			pose_data = JSON.parse_string(FileAccess.get_file_as_string("res://poses.json"))
			pose_names = pose_data.keys()
		return false
	if wait > 0:
		wait -= 1
		return false
	if pose_i >= 0:
		result["poses"][pose_names[pose_i]] = _bake(pose_names[pose_i])
	pose_i += 1
	if pose_i >= pose_names.size():
		print("GODOTCHECK " + JSON.stringify(result))
		quit(0)
		return true
	_set_pose(pose_names[pose_i])
	wait = 2
	return false

func _inspect() -> Dictionary:
	var out := {}
	var skels := subj.find_children("*", "Skeleton3D", true, false)
	out["skeletons"] = skels.size()
	if skels.size() > 0:
		var sk: Skeleton3D = skels[0]
		var names := []
		for i in sk.get_bone_count():
			names.append(sk.get_bone_name(i))
		out["bones"] = names
	var meshes := {}
	for n in subj.find_children("*", "MeshInstance3D", true, false):
		var mi := n as MeshInstance3D
		var m := mi.mesh
		if m == null:
			continue
		var info := {"surfaces": m.get_surface_count(), "blend_shapes": 0, "skin": mi.skin != null,
			"materials": [], "uv2": true, "bones_per_vertex": 0, "compressed": false}
		if m is ArrayMesh:
			var am := m as ArrayMesh
			info["blend_shapes"] = am.get_blend_shape_count()
			for s in am.get_surface_count():
				var mat := am.surface_get_material(s)
				info["materials"].append(mat.resource_name if mat else "")
				var fmt := am.surface_get_format(s)
				if (fmt & Mesh.ARRAY_FORMAT_TEX_UV2) == 0:
					info["uv2"] = false
				if (fmt & Mesh.ARRAY_FLAG_USE_8_BONE_WEIGHTS) != 0:
					info["bones_per_vertex"] = 8
				elif (fmt & Mesh.ARRAY_FORMAT_BONES) != 0:
					info["bones_per_vertex"] = 4
				if (fmt & Mesh.ARRAY_FLAG_COMPRESS_ATTRIBUTES) != 0:
					info["compressed"] = true
		meshes[String(mi.name)] = info
	out["meshes"] = meshes
	var anims := []
	for n in subj.find_children("*", "AnimationPlayer", true, false):
		var ap := n as AnimationPlayer
		for a in ap.get_animation_list():
			anims.append(String(a))
	out["animations"] = anims
	var body := subj.find_child("GB_Body", true, false) as MeshInstance3D
	if body != null and body.mesh is ArrayMesh:
		var am := body.mesh as ArrayMesh
		var arrays := am.surface_get_arrays(0)
		var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var c0 := PackedFloat32Array()
		c0.resize(verts.size() * 4)
		for i in verts.size():
			c0[i * 4] = verts[i].x
			c0[i * 4 + 1] = verts[i].y
			c0[i * 4 + 2] = verts[i].z
			c0[i * 4 + 3] = 1.0
		arrays[Mesh.ARRAY_CUSTOM0] = c0
		var nm := ArrayMesh.new()
		var fmt := Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT
		nm.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, fmt)
		var f2 := nm.surface_get_format(0)
		out["custom0"] = {"vertices": verts.size(), "has_custom0": (f2 & Mesh.ARRAY_FORMAT_CUSTOM0) != 0,
			"rgba_float": ((f2 >> Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) & Mesh.ARRAY_FORMAT_CUSTOM_MASK) == Mesh.ARRAY_CUSTOM_RGBA_FLOAT,
			"bones_kept": (f2 & Mesh.ARRAY_FORMAT_BONES) != 0}
	return out

func _set_pose(pname: String) -> void:
	var sk: Skeleton3D = subj.find_children("*", "Skeleton3D", true, false)[0]
	for b in sk.get_bone_count():
		sk.reset_bone_pose(b)
	for item in pose_data[pname]:
		var bi := sk.find_bone(item[0])
		var grest: Transform3D = sk.get_bone_global_rest(bi)
		var ax := Vector3(item[1][0], item[1][1], item[1][2])
		var ax_local := (grest.basis.inverse() * ax).normalized()
		sk.set_bone_pose_rotation(bi, sk.get_bone_pose_rotation(bi) * Quaternion(ax_local, deg_to_rad(item[2])))
		if item.size() > 3:
			# bone translation given in world (Godot) axes, e.g. the TMJ glide of kinematic.jaw
			var t := Vector3(item[3][0], item[3][1], item[3][2])
			var par := sk.get_bone_parent(bi)
			var pbasis: Basis = sk.get_bone_global_rest(par).basis if par >= 0 else Basis()
			sk.set_bone_pose_position(bi, sk.get_bone_rest(bi).origin + pbasis.inverse() * t)

func _bake(pname: String) -> Dictionary:
	var info := {}
	for mn in ["GB_Body", "GB_MuscleShell", "GB_Skeleton"]:
		var mi := subj.find_child(mn, true, false) as MeshInstance3D
		if mi == null:
			continue
		var baked := mi.bake_mesh_from_current_skeleton_pose()
		if baked == null:
			continue
		var flat := PackedFloat32Array()
		for s in baked.get_surface_count():
			var v: PackedVector3Array = baked.surface_get_arrays(s)[Mesh.ARRAY_VERTEX]
			for p in v:
				flat.append(p.x)
				flat.append(p.y)
				flat.append(p.z)
		var f := FileAccess.open("res://baked_%s_%s.bin" % [pname, mn], FileAccess.WRITE)
		f.store_buffer(flat.to_byte_array())
		f.close()
		info[mn] = flat.size() / 3
	return info
'''


# poses Godot applies with rig.json world axes (converted to Godot axes) and bakes; Blender compares
GODOT_POSES = {"elbow_90": {"forearm_L": [("flex", 90.0)]}, "knee_110": {"shin_R": [("flex", 110.0)]},
               "shoulder_abd_60": {"upper_arm_L": [("abd", 60.0)]}, "hip_flex_90": {"thigh_R": [("flex", 90.0)]},
               "neck_rot_30": {"neck": [("twist", 30.0)]}, "jaw_open_15": {"jaw": [("open", 15.0)]}}


def _godot_poses():
    import rig
    axes = rig.world_axes()
    out = {}
    for name, pose in GODOT_POSES.items():
        rows = []
        for b, rots in pose.items():
            for ax, deg in rots:
                row = [b, [float(c) for c in gbc.b2g(np.asarray(axes[b][ax]))], float(deg)]
                if b == "jaw" and ax == "open":            # rig.json kinematic.jaw: hinge + TMJ glide
                    row.append([float(c) for c in gbc.b2g(np.asarray(rig.jaw_glide(deg)))])
                rows.append(row)
        out[name] = rows
    return out


def _compare_godot_poses(tmp, info):
    """Max / mean distance (mm) from every Godot-skinned vertex to the nearest Blender-skinned vertex."""
    import rig
    from mathutils.kdtree import KDTree
    res = {}
    arm = bpy.data.objects[gbc.ARMATURE]
    for pname, meshes in info.items():
        mats = rig.pose_matrices(arm, GODOT_POSES[pname])
        worst, mean_all, n_all = 0.0, 0.0, 0
        for mn, count in meshes.items():
            path = os.path.join(tmp, f"baked_{pname}_{mn}.bin")
            if not os.path.exists(path):
                continue
            G = np.fromfile(path, dtype=np.float32).reshape(-1, 3).astype(float)
            o = bpy.data.objects[mn]
            idx, w = rig.read_weights(o)
            P = rig.lbs(gbc.get_verts(o.data), idx, w, mats)
            B = np.stack([P[:, 0], P[:, 2], -P[:, 1]], 1)
            kd = KDTree(len(B))
            for i, p in enumerate(B):
                kd.insert(p.tolist(), i)
            kd.balance()
            d = np.array([kd.find(p.tolist())[2] for p in G])
            worst = max(worst, float(d.max()))
            mean_all += float(d.sum())
            n_all += len(d)
        rig.reset_pose(arm)
        res[pname] = {"max_mm": round(worst * 1000, 4), "mean_mm": round(mean_all / max(n_all, 1) * 1000, 5),
                      "vertices": n_all}
    return res


def godot_import_check(glb, godot=GODOT_BIN, timeout=900):
    """Import ``glb`` with Godot headless in a temporary project and inspect it.  Returns (ok, detail);
    ok is None when the Godot binary is not installed (the check is then skipped, not failed)."""
    if not os.path.exists(godot):
        gbc.log(f"WARNING: Godot import check SKIPPED: no Godot binary at {godot} (set GODOT_BIN)")
        return None, {"skipped": f"no Godot binary at {godot} (set the GODOT_BIN environment variable)"}
    tmp = tempfile.mkdtemp(prefix="gb_godot_check_")
    extra_glbs = []
    try:
        with open(os.path.join(tmp, "project.godot"), "w") as fh:
            fh.write('config_version=5\n\n[application]\nconfig/name="gb_b6_import_check"\n')
        shutil.copy(glb, os.path.join(tmp, "GB_Subject.glb"))
        # every other generated glb is imported in the same project (LOD1, weapons, room) so an importer
        # error in any of them fails the check
        for p in (os.path.join(os.path.dirname(glb), LOD1_GLB), os.path.join(gbc.PROPS_OUT, "weapons.glb"),
                  os.path.join(gbc.PROPS_OUT, "room.glb")):
            if os.path.exists(p):
                shutil.copy(p, os.path.join(tmp, os.path.basename(p)))
                extra_glbs.append(os.path.basename(p))
        with open(os.path.join(tmp, "check.gd"), "w") as fh:
            fh.write(_GODOT_CHECK_GD)
        with open(os.path.join(tmp, "poses.json"), "w") as fh:
            json.dump(_godot_poses(), fh)
        env = dict(os.environ)
        imp = subprocess.run([godot, "--headless", "--path", tmp, "--import"], capture_output=True, text=True,
                             timeout=timeout, env=env)
        import_errors = [ln.strip() for ln in (imp.stdout + "\n" + imp.stderr).splitlines()
                         if ln.strip().startswith(("ERROR:", "SCRIPT ERROR:", "WARNING:"))]
        imported = sorted(f[:-len(".import")] for f in os.listdir(tmp) if f.endswith(".glb.import"))
        # skins register with the skeleton only with a real renderer: run the check under a virtual X
        # display with the OpenGL (Mesa llvmpipe) driver when xvfb-run exists, else headless (no pose bakes)
        xvfb = shutil.which("xvfb-run")
        if xvfb:
            cmd = [xvfb, "-a", godot, "--path", tmp, "--rendering-driver", "opengl3", "--audio-driver", "Dummy",
                   "--script", "res://check.gd"]
        else:
            cmd = [godot, "--headless", "--path", tmp, "--audio-driver", "Dummy", "--script", "res://check.gd"]
        run = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
        line = next((l for l in run.stdout.splitlines() if l.startswith("GODOTCHECK ")), None)
        if line is None:
            return False, {"error": "no output", "import_rc": imp.returncode, "rc": run.returncode,
                           "stderr": (imp.stderr + run.stderr)[-3000:]}
        got = json.loads(line[len("GODOTCHECK "):])
        pose_cmp = _compare_godot_poses(tmp, got.get("poses", {}))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    import rig
    probs = []
    errs = [e for e in import_errors if e.startswith(("ERROR:", "SCRIPT ERROR:"))]
    if errs:
        probs.append(f"{len(errs)} importer ERROR lines: {errs[:6]}")
    not_imported = [g for g in ["GB_Subject.glb"] + extra_glbs if g not in imported]
    if not_imported:
        probs.append(f"not imported: {not_imported}")
    if got.get("skeletons") != 1:
        probs.append(f"{got.get('skeletons')} skeletons")
    if sorted(got.get("bones", [])) != sorted(rig.BONE_NAMES):
        probs.append("bone names differ from rig.json")
    order_same = got.get("bones") == list(rig.BONE_NAMES)
    want = [n for n in gbc.exported_mesh_names(0) if n in bpy.data.objects]
    meshes = got.get("meshes", {})
    for n in want:
        m = meshes.get(n)
        if m is None:
            probs.append(f"{n} missing")
            continue
        if not m["skin"]:
            probs.append(f"{n} not skinned")
        if not m["uv2"]:
            probs.append(f"{n} lacks UV2")
        if m["bones_per_vertex"] != 4:
            probs.append(f"{n} bones/vertex {m['bones_per_vertex']}")
        me = bpy.data.objects[n].data
        nk = len(me.shape_keys.key_blocks) - 1 if me.shape_keys else 0
        if m["blend_shapes"] != nk:
            probs.append(f"{n} blend shapes {m['blend_shapes']} (want {nk})")
        me.calc_loop_triangles()
        mi = np.empty(len(me.loop_triangles), np.int32)
        me.loop_triangles.foreach_get("material_index", mi)
        if m["surfaces"] != len(np.unique(mi)):
            probs.append(f"{n} surfaces {m['surfaces']} (want {len(np.unique(mi))})")
    missing_anims = [a for a in gbc.POSE_ACTIONS if a not in got.get("animations", [])]
    if missing_anims:
        probs.append(f"animations missing {missing_anims}")
    for pn, r in pose_cmp.items():
        if r.get("max_mm", 1e9) > 0.2:
            probs.append(f"pose {pn}: Godot vs Blender skinning differ by {r.get('max_mm')} mm")
    c0 = got.get("custom0", {})
    if not (c0.get("has_custom0") and c0.get("rgba_float") and c0.get("bones_kept")):
        probs.append(f"CUSTOM0 injection failed: {c0}")
    detail = {"meshes": len(meshes), "bones": len(got.get("bones", [])), "animations": got.get("animations", []),
              "bone_order": "same as rig.json" if order_same else "differs from rig.json: map bones by NAME "
                                                                 "(Skeleton3D.find_bone), never by index",
              "godot_bone_order": got.get("bones", []),
              "custom0": c0,
              "compressed_meshes": sorted(n for n, m in meshes.items() if m.get("compressed")),
              "skinning_vs_blender": pose_cmp,
              "imported_glbs": imported, "import_warnings": [e for e in import_errors if e.startswith("WARNING:")][:10],
              "problems": probs}
    return not probs, detail


if __name__ == "__main__":
    args = gbc.script_args()
    if "--roundtrip" in args:
        print("ROUNDTRIP " + json.dumps(_import_summary(args[args.index("--roundtrip") + 1])))
