"""glTF export, JSON sidecars and manifest (owner B6; first working draft by B0).

Plan §3.3.3, §4.3, §5.7-5.9, §8.2 B6.

Final entry points
------------------
``export_subject(objs, out)``  -> writes GB_Subject.glb, GB_Subject_LOD1.glb and every JSON sidecar
                                  (rig, landmarks, organs, vessels, spine, codes, brain_labels) to ``out``
``export_props(out)``          -> weapons.glb, room.glb, props.json, room.json (delegates to props.py, B8)
``write_manifest(out, ...)``   -> manifest.json (schema/generator versions, build id, input hashes,
                                  per-mesh counts, surfaces, bounds, wound grid, segment origins,
                                  textures, budget checks, pending stages)

The glTF options are exactly plan §5.9 (verified in the bundled exporter 5.0.21).
Only the armature and the contract meshes are exported (``use_selection``);
GB_Data curves/empties, stage lights and cameras never reach the glb.
"""
import os
import sys

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
# plan §3.3.3 wound lookup grid: 2.5 cm cells over the measured A-pose rest bounds + 1 cell margin
WOUND_CELL_M = 0.025


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


def codes_table():
    """codes.json 'data': every integer code carried in UV2 / CUSTOM0.w (plan §5.5)."""
    return {
        "segment": {str(k): v for k, v in SG.SEGMENTS.items()},
        "region": {str(k): v for k, v in SG.REGIONS.items()},
        "dermatome": {str(k): v for k, v in DM.DERMATOMES.items()},
        "bone_class": {str(k): v for k, v in BN.BONE_CLASS.items()},
        "bone_piece": {str(v): k for k, v in BN.BONE_PIECE_ID.items()},
        "organ": {str(o["organ_id"]): o["id"] for o in OR.ORGANS},
        "brain_region": {str(k): v[0] for k, v in BR.BRAIN_REGIONS.items()},
        "cord_segment": {str(i): s for i, s in enumerate(MYO.CORD_SEGMENTS)} | {"30": "cauda_equina"},
        "region_stride": SG.REGION_STRIDE,
        "uv2": {
            "GB_Head, GB_Body, GB_Shorts, GB_MuscleShell, GB_*_LOD1": "x = segment + 32 * region, y = dermatome",
            "GB_Eye_*, GB_EyeFX_*, GB_Mouth": "x = 0 + 32 * region(eyelid_lip) = 64, y = 0",
            "GB_BrowLash": "x = 32 (face), y = 0",
            "GB_Skeleton, GB_Frac_*": "x = bone piece id, y = bone class (fracture fragments = loose islands)",
            "GB_Organs": "x = organ id, y = sub-part id (heart chambers 1 RA, 2 RV, 3 LA, 4 LV)",
            "GB_Vessels_Art, GB_Vessels_Ven": "x = vessel_index (vessels.json), y = t along the segment 0..1",
            "GB_Brain": "x = brain region id, y = sulcus depth 0..1",
            "GB_Cord": "x = cord segment index (C1 = 0 ... S5 = 29, cauda 30), y = t",
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
            "uv_maps": [l.name for l in me.uv_layers]}


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
    """Plan §4.1 triangle budgets and §4.3 file limits (placeholder meshes are expected to pass too)."""
    res = {}
    for key, budget in gbc.TRI_BUDGET.items():
        names = gbc.TRI_BUDGET_GROUPS.get(key, (key,))
        tris = sum(meshes[n]["triangles"] for n in names if n in meshes)
        res[key] = {"triangles": tris, "budget": budget, "ok": tris <= budget * 1.10}
    return res


def write_manifest(out, glb_paths=(), sidecars=None, pending=None, timings=None, quick=False):
    """manifest.json (plan §5.7).  Returns the manifest data dict."""
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
    try:
        import io_scene_gltf2
        exporter = ".".join(str(x) for x in io_scene_gltf2.bl_info["version"])
    except Exception:                                                # pragma: no cover
        exporter = "unknown"
    arm = bpy.data.objects.get(gbc.ARMATURE)
    data = {
        "build": {"build_id": gbc.build_id(), "blender": bpy.app.version_string, "gltf_exporter": exporter,
                  "quick": bool(quick), "timings_s": timings or {},
                  "input_hashes": {os.path.relpath(p, gbc.HERE).replace(os.sep, "/"): gbc.file_hash(p)[:16]
                                   for p in gbc.source_files() if os.path.exists(p)},
                  "schemas": {k: k for k in gbc.SCHEMAS}},
        "files": files,
        "meshes": meshes,
        "armature": {"bones": [b.name for b in arm.data.bones] if arm else [],
                     "actions": list(gbc.POSE_ACTIONS)},
        "rest_bounds": {"body_frame": {"min": lo.tolist(), "max": hi.tolist()},
                        "godot_rest": {"min": np.minimum(gbc.b2g(lo), gbc.b2g(hi)).tolist(),
                                       "max": np.maximum(gbc.b2g(lo), gbc.b2g(hi)).tolist()}},
        "wound_grid": wound_grid(lo, hi),
        "segment_origins": segment_origins(),
        "textures": [],
        "texture_note": "no baked textures yet (B7); materials are named placeholders swapped in Godot",
        "budgets": budget_checks(meshes),
        "pending": pending or {},
        "import_hints": {"import_script": "res://pipeline/import/subject_post_import.gd",
                         "inner_meshes_hidden": list(gbc.INNER_OBJECTS) + list(gbc.VARIANT_OBJECTS),
                         "uv2": "codes (see codes.json)", "custom0": "rest position + segment (G0)"},
    }
    gbc.write_json(os.path.join(out, "manifest.json"), data, "gb.manifest/1")
    return data


def export_subject(objs=None, out=gbc.SUBJECT_OUT, pending=None, timings=None, quick=False):
    """Export GB_Subject.glb (+ LOD1), every sidecar and the manifest into ``out``."""
    os.makedirs(out, exist_ok=True)
    lod0 = [n for n in gbc.exported_mesh_names(0) if n in bpy.data.objects]
    lod1 = [n for n in gbc.exported_mesh_names(1) if n in bpy.data.objects]
    glbs = [export_glb(os.path.join(out, SUBJECT_GLB), lod0)[0]]
    if lod1:
        glbs.append(export_glb(os.path.join(out, LOD1_GLB), lod1)[0])
    side = write_sidecars(out)
    man = write_manifest(out, glbs, side, pending, timings, quick)
    return {"glb": glbs, "sidecars": side, "manifest": os.path.join(out, "manifest.json"), "data": man}


def export_props(out=gbc.PROPS_OUT):
    """weapons.glb, room.glb, props.json and room.json from props.py (B8 builds and exports them)."""
    import props
    return props.export_props(out)
