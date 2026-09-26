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
| `viscera.py` | B4 | done | `build_organs()` -> GB_Organs (+ GB_Organs_HR), `organ_table()`, `render_organs()`; SDF toolkit: `mesh_sdf` (marching tetrahedra: watertight, keeps sealed cavities), `decimate_components`, `cage_sdf`/`dome_height`/`lung_border_z` (rib-table cage model) |
| `neuro.py` | B4 | done | `build_cord()` -> GB_Cord + GB_Brain + GB_Brain_HR (the whole neuro stage), `build_brain()`, `spine_table()`, `brain_labels()`, `brain_region_at()`, `render_neuro()` |
| `vascular.py` | B5 | stub (`vessel_table`, `centreline`, `mesh_for` v0 work) | `build_vessels()`, `vessel_table()` |
| `uv.py` | B1/B2 (v0 by B0) | working v0 | `mark_seams(obj, rules)`, `unwrap(obj, method)`, `pack(obj, size, margin_px)` |
| `lookdev.py`, `bake.py` | B7 | stub | `build_materials()`, `bake_all`, `bake_tileables`, `bake_painter_inputs` |
| `props.py` | B8 | done | `build_weapons(quick)`, `build_room(quick)`, `export_props(out)`, `measure_props()`, `spec_check()`, `floor_height(x, y)`, `room_bounds()`, `SPEC`, `ROOM`, `render_items()`, `render_room()` (details: "Props and room" below) |

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
| GB_Cord | cord segment (C1 = 0 … S5 = 29), 30 cauda equina, 31 dura, 40 + n root stub of segment n | t |

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
the game from a clone); every file < 50 MB. Props (`../props/weapons.glb`, `room.glb`) are B8 (below).

## Props and room (B8) → `gore-game/assets/generated/props/`

`python3 build.py --stage props` (≈10 s of the build) or `python3 props.py [--quick] [--render]
[--render-items a,b] [--render-room all|v1,v2] [--no-export]`. `export.export_props` delegates to
`props.export_props`. Scene: collection `GoreProps` (`GBP_Weapons`, `GBP_Room`, `GBP_Stage` = render-only
studio/room lights); it is excluded from the view layer after export so subject renders stay clear.

- `weapons.glb`: one root per item at the origin, root origin = grip / hand point: `GBP_Pistol`
  (9 mm, bore 9.0, barrel 114, slide 186, overall 196.5), `GBP_Shotgun` (12 ga pump, bore 18.5, barrel 470,
  overall 987), `GBP_Knife` (single edge, blade 120 × 25, spine 2.5), `GBP_Hammer` (face Ø 28, head
  0.48 kg measured from the mesh volume, overall 325), `GBP_Torch` (Ø 77.3 cylinder, Ø 16 tube, 80 mm flame
  `GBP_Torch_Flame` to toggle), `GBP_Fist` (gloved right fist), `GBP_Ruler` (ABFO-style L, 1 mm ticks),
  `GBP_Penlight`, `GBP_Thermometer`. Moving parts are separate meshes (slide, triggers, forend, flame).
- Item frame: authored +Y forward / +Z up → Godot −Z forward / +Y up. **Markers** (`Node3D` in Godot):
  local +Y (Godot −basis.z) = action direction, +Z = up; kind in `gbp_marker` extras. `GBP_muzzle_pistol`,
  `GBP_muzzle_shotgun` (plan's `GBP_muzzle`; unique names per file), `GBP_blade_edge_0…7` (edge outward
  normal, up = toward the tip), `GBP_blade_tip`, `GBP_hammer_face`, `GBP_claw`, `GBP_torch_nozzle`,
  `GBP_fist_knuckles`, `GBP_ruler_zero`, `GBP_penlight_beam`, `GBP_thermo_tip`, `GBP_thermo_display`, sights,
  ejection ports, `*_grip`.
- `room.glb`: body frame planes x ±3, y −4.4…1.6 (Godot z −1.6…4.4), ceiling 3.0; epoxy floor
  `h = 0.01·(|p − drain| − 1.0)` (1 % fall to the Ø 150 drain at Godot (0, 0, 1), zero at the subject mark)
  with a 40 mm coved skirting to 0.14 m; 150 mm glazed tiles as real cushion-edged pads (face exactly on the
  plane) over a grout plane 1.5 mm behind (2 mm real joints; UV0 = metres, UV1 `tile_id`); backstop 2.4 × 2.2
  × 0.3 m, front plane Godot z = −1.3; two LED panels; door; mortuary table; trolley; tape cross; 1 m scale bar.
  Markers `GBP_room_*` (subject mark, spawn, key/panel lights, probe, drain, backstop, table, trolley, door,
  scale-bar zero, `GBP_room_tool_<item>` = item root transforms resting on the trolley / table).
  Collision: `GBP_room_col_*-convcolonly` boxes and `GBP_room_col_floor-colonly` (Godot makes StaticBody3D;
  verified with a headless 4.5.1 import). Collision meshes are hidden in Blender renders.
- `props.json` (`gb.props/1`): spec vs measured critical dimensions, triangles, markers (Godot axes, relative to
  the item root), materials. `room.json` (`gb.room/1`): every room constant in Godot axes (`godot`), the
  floor formula, markers, materials (with `absorbent` for grout / rubber), collision boxes. **`world/room.gd`
  must take its constants from `room.json`**; verify compares them once the file exists.
- Materials `GBPM_*`: plain Principled factors exported (images NONE); Blender-only noise bump for renders.

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

### B4 (organs, cord, brain) — facts for the other packages

- **GB_Organs** (22k tris, 6 shape keys): every organ is a closed mesh; hollow organs keep an inner surface with
  normals into the lumen (heart: 4 chambers LV/RV/RA/LA with walls ~9/4/2.5 mm, papillary muscles, trabeculae;
  stomach 2.3 mm wall + rugae; bladder; trachea/bronchi with C-rings and a flat membranous back wall; larynx
  airway; oesophagus slit lumen). UV2.y sub-part ids per organ are listed in `organs.json` `sub_parts`
  (heart 5 = epicardial fat; kidney 3 = perirenal fat capsule, a container of sub 1-2; diaphragm 2 = central
  tendon; stomach/bladder 2 = mucosa). The pericardium is a closed sac around the heart (container).
  `organs.json` carries per organ the measured mesh volume, centroid, AABB and mass estimate (`measured`).
- `diaphragm_inhale` also moves the liver, gallbladder, spleen, stomach, kidneys, adrenals, pancreas down with
  the domes (R05 §14) and pushes the backing mass/omentum down and forward: drive it together with
  `lung_inhale_L/R`.
- Organs carve each other and the great vessels (bible waypoints of `gb_data.vessels`, +2 mm): **B5**, keep
  the thoracic/abdominal centrelines within ~2 mm of the bible waypoints or the carved grooves will not match.
- **Cage model**: the lungs/diaphragm fit a cage interpolated from `gb_data.ribs` (rib centreline radius
  - 4.5 mm - 2.2 mm). The whole right hemithorax above the dome holds only ~1.95 L, so the lungs reach
  1.29 / 1.20 L instead of the bible's FRC 1.80 / 1.55 L (verify warns).
- **GB_Brain** is the head project's brain; below z 1.623 its stem is replaced by a medulla following
  `neuro.CMJ_PATH` into the canal. The head's brainstem sits ~2 cm lower than RB §7.4 (pons centre z_rel
  -0.010 vs +0.012; its clivus occupies the bible's pons basis) — the head is authoritative inside the head,
  so brainstem labels and `spine.json` `brainstem` capsules follow the mesh (`brainstem_bible` kept).
- **B2/B3 (C0-C1)**: the head skull's basion lip (y 0.025-0.029, z 1.608-1.616) sits over the atlas canal,
  while the atlas posterior arch (y 0.035-0.045, z 1.600-1.606) sits under the foramen magnum: there is no
  straight channel for an 8.5 mm cord. The cord threads the gap (`CMJ_PATH`); please align FM and atlas.
- **B3**: the sacrum is solid at x = 0 from z 1.030 down (no sacral canal), so the lower thecal sac and cauda
  equina (to S2, RB §7.4) necessarily intersect bone there; please open the sacral canal (AP ~15 mm).
- **B3 canal size**: the built vertebral canal is smaller than the RB §7.3 table (L3 ~12 x 20 mm vs 16 x 23;
  C6 ~10 x 20 mm vs 14 x 24) and centred ~1-3 mm off the table's cord line in places. The cord proper
  (table sizes, verified +-0.5 mm) is clear of bone; the dural sac is sized to the table canal minus 3 mm.
- **B0/B6 codes**: `codes.json` `cord_segment` should add 31 = dura and 40 + n = root stub of segment n
  (documented in `spine.json` `cord_codes`).
- **build.py**: the neuro stage's cache key lists only `neuro.py`; it also depends on `viscera.py` (shared
  mesher) and the head project's `anatomy.py` (brain). The viscera stage also reads `body_skin.py` (abdominal
  wall stations). Please add them to `SOURCES` so edits invalidate the caches.

