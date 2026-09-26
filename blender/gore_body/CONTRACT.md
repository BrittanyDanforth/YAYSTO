# gore_body module contract (plan §5, kept current)

Procedural full body for the Godot game, built with Blender 5.x from code only (no downloads).
The authoritative design is `gore-game/docs/FULL_BODY_PLAN.md` §5; this file records what the code
actually does today and the rules every work package follows. Status: **B0 done (placeholder,
data, infra, export draft)**. Every other package is a stub with its final signatures.

## Run

```
cd blender/gore_body
python3 build.py --stage placeholder --quick      # ~35 s: placeholder + rig + export + verify
python3 build.py --stage placeholder               # ~65 s: finer meshes
python3 build.py --stage skin head ... [--quick]   # build those stages, load the other stages from cache
python3 build.py --stage all [--no-bake]           # everything
python3 verify.py [--blend gore_body.blend]        # tables + exported files (+ scene checks)
python3 placeholder.py --quick | neuro.py | rig.py # each module also runs alone
blender -b --python build.py -- --stage placeholder --quick     # Blender binary (5.1): args after "--"
```

Options: `--quick` (coarse meshes), `--no-bake`, `--render` (renders/build_*.png), `--no-save`
(skip `gore_body.blend`), `--no-verify`. Exit code 1 when a `fail` check fails.

## Rules (plan §5.1)

- Only `bpy` + `numpy`. Paths only through `gb_common` (`HERE`, `GAME_OUT`, `SUBJECT_OUT`, ...).
- `blender/gore_head` is imported **read-only** with `gb_common.import_head()` (anatomy, materials,
  gh_common), re-imported on every build so the head team's fixes flow in. Never write there.
- Deterministic: every random draw uses `gb_common.rng("<name>")` (seeds registered in `SEEDS`).
- Body frame everywhere: metres, +Z up, face −Y, character's left +X, origin on the floor between the
  feet. `p_body = p_head + (0, 0.020, 1.647)` (`gb_common.head_to_body`). Godot = `(x, z, −y)` (`b2g`).
- Left side authored, right mirrored (`gb_common.mirror_x`, `mirror_axis` for rotation axes).
- Test renders ≤ 640 px, ≤ 48 samples, denoised (`gb_common.render_views`, `BODY_VIEWS`).
- The build ends with exactly one ARMATURE modifier per exported mesh; everything else is applied
  (the glTF exporter's `export_apply` would drop shape keys).
- **Never decimate after writing categorical data by hand without `gb_geom.decimate_to`**: it restores
  every `gb_*` point attribute and the `gb_codes` UV from the nearest original vertex (Blender's
  decimation averages INT attributes: bone index "fingers_L"/"thumb_L" would become another bone).

## Files and owners (plan §5.2)

| File | Owner | State | Final entry points |
|---|---|---|---|
| `gb_common.py` | B0 | done | paths, `SEEDS`/`rng`, `head_to_body`, `b2g`/`g2b`, `collections()`, `link()`, `new_object()`, contract name tables, `write_json`/`read_json`/`validate_schema`, `stage_cache()`, `write_png_u8`, `weights_at` (→ rig), `seam_ring` (→ head_integration), mesh/UV/material/render helpers, `NotBuiltYet`/`not_built` |
| `gb_geom.py` | B0 | done | `sdf_mesh`, `sdf_arrays`, `sweep`, `resample`, `cut_plane`, `seam_ring_from_sdf`, `zip_to_ring`, `decimate_to`, `apply_modifier`, `split_pieces`, `join_parts`/`part`/`mirror_part`/`object_from_parts`, oriented SDF primitives (`sd_oellipsoid`, `sd_obox`, `sd_superellipsoid`, `sd_plate`, `superellipse2`), `smart_uv`, `remove_loose` |
| `gb_data/*` | B0 (B5 extends vessels/nerves) | done | landmarks, rig_table, vertebrae, ribs, bones, organs, vessels, nerves, myotomes, dermatomes, tissue, segments, brain |
| `placeholder.py` | B0 | done | `build_placeholder(quick=False) -> {name: Object}`; also `body_sdf`, `skin_sdf`, `muscle_sdf`, `seam_ring`, `set_skin_codes`, `skin_regions`, `finish_uvs`, `tag` |
| `verify.py` | B0 frame, all add checks | done | `@check(group, owner, severity)`, `verify_all(groups) -> dict`, `failures(res)` |
| `build.py` | B0 | done | `--stage …`, `run(stages, opts)` |
| `export.py` | B6 (draft by B0) | working draft | `export_subject(objs, out)`, `export_props(out)`, `write_manifest(out, …)`, `landmarks_table()`, `codes_table()`, `GLTF_OPTIONS` (= plan §5.9) |
| `rig.py` | B6 (v0 by B0) | working v0 | `build_armature()`, `weights_at(points, layer)`, `skin_all(objs)`, `build_poses(arm)`, `rig_table()` |
| `body_skin.py` | B1 | stub (`body_sdf`/`skin_sdf`/`paint_codes` delegate to the placeholder) | `body_sdf`, `skin_sdf`, `build_body_skin()`, `build_shorts(skin)`, `build_muscle_shell(skin)`, `paint_codes(obj)` |
| `head_integration.py` | B2 | stub (`seam_ring`, `zip_to_ring` work) | `seam_ring(n=160)`, `zip_to_ring(obj, ring)`, `build_head()`, `build_face_shapes(head)`, `build_eye_fx()`, `build_hair_cards()` |
| `skeleton.py` | B3 | stub | `build_skeleton()`, `build_fracture_variants()`, `bone_capsules()` |
| `viscera.py` | B4 | stub (`organ_table` v0 works) | `build_organs()`, `organ_table()` |
| `neuro.py` | B4 | stub (`spine_table`, `brain_labels`, `brain_region_at` v0 work) | `build_cord()`, `spine_table()`, `brain_labels()` |
| `vascular.py` | B5 | stub (`vessel_table`, `centreline`, `mesh_for` v0 work) | `build_vessels()`, `vessel_table()` |
| `uv.py` | B1/B2 (v0 by B0) | working v0 | `mark_seams(obj, rules)`, `unwrap(obj, method)`, `pack(obj, size, margin_px)` |
| `lookdev.py`, `bake.py` | B7 | stub | `build_materials()`, `bake_all`, `bake_tileables`, `bake_painter_inputs` |
| `props.py` | B8 | stub | `build_weapons()`, `build_room()` |

### Stage builder contract (how a package replaces the placeholder)

`build.py` always builds the placeholder first, then calls the stage builders (`BUILDERS` in
`build.py`). A builder returns `{contract name: object}` and must:

1. create its objects with `gb_common.new_object(name, data)` (removes the placeholder of that name,
   links to the contract collection) — or `gb_geom.object_from_parts`;
2. give each mesh the contract material slots (`gb_common.set_material_slots`), UV maps
   `atlas` (UV0) and `gb_codes` (UV1, via `set_codes_uv`), identity transform, `gb_layer` /
   `gb_schema` custom props (`placeholder.tag`), and a `gb_rigid_bone` INT point attribute
   (bone index, −1 = analytic weights) wherever the part must not bend (bones, teeth, eyes);
3. not skin: the `rig` stage parents and weights every exported mesh (`rig.skin_all`);
4. raise `gb_common.NotBuiltYet` (via `not_built(owner, what)`) while unfinished: the placeholder stays.

Built stages are cached in `.cache/<stage>-<hash>.blend` (key: the stage's source files,
`gb_common.py`, every `gb_data` table, Blender version, quick/full) and loaded by later runs that do
not rebuild that stage. `.cache/` is git-ignored.

## Collections and objects (plan §5.3)

```
GoreBody
├── GB_Rig        GB_Armature
├── GB_Outer      GB_Head, GB_Body, GB_Shorts, GB_Eye_L, GB_Eye_R, GB_EyeFX_L, GB_EyeFX_R, GB_Mouth, GB_BrowLash
├── GB_Inner      GB_MuscleShell, GB_Skeleton, GB_Brain, GB_Organs, GB_Cord, GB_Vessels_Art, GB_Vessels_Ven
├── GB_Variants   GB_Frac_Skull_{L,R,T}, GB_Frac_{Humerus,RadUlna,Femur,Tibia}_{L,R}_{simple,comminuted}
├── GB_LOD1       GB_Head_LOD1, GB_Body_LOD1
├── GB_Data       GBL_<landmark> empties, GBH_<organ>_<n> hit empties, GBV_<segment> / GBN_<nerve>_<side> / GBC_cord curves
├── GB_HighRes    GB_Head_HR, GB_Body_HR, GB_Skeleton_HR, GB_Organs_HR, GB_Brain_HR   (bake sources; not built yet)
└── Stage         cameras, lights, floor for test renders
```

All names, slots, shape keys, budgets and layers live in `gb_common` (`OUTER_OBJECTS`,
`MATERIAL_SLOTS`, `SHAPE_KEYS`, `TRI_BUDGET`, `LAYER_OF`, ...). Nobody hard-codes a name twice.

## Per-vertex data (plan §5.5)

- UV0 `atlas` (placeholder: Smart UV Project; B1/B2 plan real seams, `FRACTION` margin 0.0078).
- UV1 `gb_codes` — integer codes as floats. **Blender stores `1 − v`** (the exporter flips V), so
  Godot's UV2 reads the codes exactly (checked in Godot: GB_Body UV2 = (129, 28) = torso + 32·trunk_front, S4-5).
- Point attributes kept in the .blend: `gb_seg`, `gb_region`, `gb_derm`, `gb_piece`, `gb_class`,
  `gb_organ`, `gb_sub`, `gb_rigid_bone` (INT), `gb_tt`, `gb_vidx` (FLOAT).

| Mesh | UV2.x | UV2.y |
|---|---|---|
| GB_Head, GB_Body, GB_Shorts, GB_MuscleShell, LOD1 | segment + 32 · region | dermatome |
| GB_Eye_*, GB_EyeFX_*, GB_Mouth | 64 (head/eyelid-lip) | 0 |
| GB_BrowLash | 32 (head/face) | 0 |
| GB_Skeleton, GB_Frac_* | bone piece id (`gb_data.bones.BONE_PIECE_ID`, append-only) | bone class |
| GB_Organs | organ id (`gb_data.organs.ORGANS`) | sub-part (heart 1 RA, 2 RV, 3 LA, 4 LV) |
| GB_Vessels_* | vessel_index (vessels.json) | t along the segment |
| GB_Brain | brain region id (`gb_data.brain`) | sulcus depth 0–1 |
| GB_Cord | cord segment (C1 = 0 … S5 = 29, cauda 30) | t |

Code tables: `codes.json` (segment 0–10, region 0–7, dermatome 0–28, bone class, bone piece,
organ, brain region, cord segment).

## Materials, shape keys, bones, actions (plan §5.6)

Named plain Principled placeholders (`gb_common.MATERIAL_SLOTS`, colours from the bible), exported
with `export_materials='EXPORT'`, no images; Godot swaps them by name. Shape keys: GB_Head 24 face
keys, GB_Body 4, GB_Organs 6 (placeholder analytic fields; B2/B1/B4 own the final ones).
39 deform bones (`gb_data.rig_table`, A-pose, RB §7.2 joint centres), 20 physical bodies with world
joint axes whose signs are proven numerically (`rig_table.resolve_axes`), actions `pose_idle`,
`pose_guard`, `pose_cower`, `pose_brace`.

## Exported files (plan §5.7–5.9) → `gore-game/assets/generated/subject/`

`GB_Subject.glb` (armature + outer + inner + variants, ~21 MB), `GB_Subject_LOD1.glb`, `manifest.json`,
`rig.json`, `landmarks.json`, `organs.json`, `vessels.json`, `spine.json`, `codes.json`,
`brain_labels.png` (8 × 8 tiles of 64² slices, R = region id, lossless) + `brain_labels.json`.
Every JSON has the envelope `{schema, frame: "body_zup_m", godot_mapping: "(x, z, -y)", generator,
build_id, data}`; floats rounded to 1e-5; `build_id` = hash of the generator sources (no timestamp, so
unchanged builds give byte-identical JSON — verified). Generated assets are **committed** (the user runs
the game from a clone); every file < 50 MB. Props (`../props/weapons.glb`, `room.glb`) are B8.

Manifest `data`: `build` (ids, versions, timings, input hashes), `files` (bytes, sha256), `meshes`
(vertices, triangles, surfaces, shape keys, layer, status), `armature`, `rest_bounds`, `wound_grid`
(Godot rest frame, 2.5 cm cells + margin), `segment_origins`, `textures` (empty until B7), `budgets`,
`pending` (which stages are still placeholders), `import_hints`.

## Verification (verify.py)

Groups `tables` (gb_data), `scene` (the built .blend), `files` (exports incl. parsing the GLB JSON:
nodes, 39 joints, materials, UV2/JOINTS on every primitive, no images, 4 actions, morph target names).
Add a check with `@check("scene", owner="B3")` returning `(ok, detail)`. Current B0 checks include:
25 vertebra rows, mass fractions = 1.000, 39 bones / 20 bodies / 75 kg, adjacent mass ratio ≤ 10,
joint heads at the RB landmarks ±2 mm, plan §5.8 elbow axis example, myotome key muscles, vessel graph
(every bible RB §3.3 id present, parents, L/R pairs), organ/code tables, ribs/cord, landmark checklist,
JSON determinism; scene: contract objects/collections, identity transforms + one ARMATURE modifier,
slot names, UV order, weights ≤ 4 and normalised, rigid parts 100 % on their bone, bone-piece sides,
shape keys, armature/poses, **seam ring shared by GB_Head and GB_Body (160 identical vertices)**, eye
centres (RB §1.2), codes inside their tables, nesting inside the skin (FB-4 style), vessels inside skin
(warn, B5), triangle budgets (warn).

## Known facts and findings for the other packages

- **Head neck vs bible (B2)**: `gore_head/anatomy._neck` is centred ~3 cm behind the RB §7.1 neck
  (front surface y ≈ −0.013 at z 1.49 vs −0.055; larynx at y −0.010 vs the prominence at −0.062). The
  placeholder uses a bible-placed neck below z 1.50, blends to the head's surface over z 1.50–1.60 and
  keeps the full head union in front of y −0.015 (chin/jaw).
- **Vessel waypoints (B5)**: RB §3.3 scalp/face vessels (A07 superficial temporal branches, A08 facial)
  lie 3–15 mm outside the head project's skin; limb superficial veins (V20 cephalic, V17 great
  saphenous, V02 external jugular) and A32 dorsalis pedis sit 10–30 mm outside the placeholder body.
  They must be projected to the final skin (FB-5 depths).
- Placeholder eyes use the head's 72 × 48 eyeball decimated to 1.9k tris (plan budget 5k for eyes + FX).
- Brain labels / spine / organ / vessel JSON are v0 transcriptions (status field says so); owners refine.
- Every foot/scapula/clavicle/hip placeholder bone is inside the placeholder skin (≤ 1 % sampled
  vertices outside); B1's real skin must keep lean-site depths (RB §7.6) so this stays true.
