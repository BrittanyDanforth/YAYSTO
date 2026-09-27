# gore_body module contract (plan §5, kept current)

Procedural full body for the Godot game, built with Blender 5.x from code only (no downloads).
The authoritative design is `gore-game/docs/FULL_BODY_PLAN.md` §5; this file records what the code
actually does today and the rules every work package follows. Status: **B0-B8 built; fix round 1
applied** (see "Fix round 1: changes and deviations" at the end). Remaining failures are listed there.

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

Options: `--quick` (coarse meshes; also skips the full bake and writes to `.cache/quick_out/` unless
`--force-export`), `--no-bake`, `--render` (renders/build_*.png), `--no-save` (skip `gore_body.blend`),
`--no-verify`, `--reproduce` (verify: rebuild into a scratch root and compare mesh hashes). Exit code 1
when a `fail` check fails. Environment: `GB_OUTPUT_ROOT` (write the exports + `.blend` to another root),
`GB_CACHE_DIR` (stage caches), `GODOT_BIN` (headless import check; skipped with a warning if unset/missing).

**Blender 5.1 (the user's local install)**: the code was developed on the bpy 5.0.1 module. Run
`blender -b --python build.py -- --stage placeholder --quick` once first (~1 min): it exercises every
bpy API the full build uses (mesh/attribute foreach, geometry ops, glTF export, Cycles setup) and fails
fast on a 5.0 -> 5.1 difference.

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
| `export.py` | B6 | done | `export_subject(objs, out)` (B7 atlases re-applied, painter bone maps refreshed when the weights change), `export_props(out)`, `write_manifest(out, …)`, `round_trip(glb)`, `godot_import_check(glb)`, `landmarks_table()`, `codes_table()`, `GLTF_OPTIONS` (= plan §5.9) |
| `rig.py`, `posetest.py` | B6 | done | `build_armature()`, `bone_rows()`, `weights_at(points, layer)`, `skin_all(objs)`, `build_poses(arm)`, `rig_table()`, `apply_pose`/`pose_matrices`/`lbs`; posetest: `run_tests()`, `render_poses()`, `render_key_poses()`, `render_weights()`, `section_png()` (details: "Rig, weights, export (B6)" below) |
| `body_skin.py` | B1 | built (fix rounds 1-2) | `body_sdf`, `skin_sdf`, `build_body_skin()`, `build_shorts(skin)`, `build_muscle_shell(skin)`, `paint_codes(obj)` |
| `head_integration.py` | B2 | built (fix rounds 1-2) | `seam_ring(n=160)`, `zip_to_ring(obj, ring)`, `build_head()`, `build_face_shapes(head)`, `build_eye_fx()`, `build_hair_cards()` |
| `skeleton.py` | B3 | built (fix rounds 1-2) | `build_skeleton()`, `build_fracture_variants()`, `bone_capsules()` |
| `viscera.py` | B4 | done | `build_organs()` -> GB_Organs (+ GB_Organs_HR), `organ_table()`, `render_organs()`; SDF toolkit: `mesh_sdf` (marching tetrahedra: watertight, keeps sealed cavities), `decimate_components`, `cage_sdf`/`dome_height`/`lung_border_z` (rib-table cage model) |
| `neuro.py` | B4 | done | `build_cord()` -> GB_Cord + GB_Brain + GB_Brain_HR (the whole neuro stage), `build_brain()`, `spine_table()`, `brain_labels()`, `brain_region_at()`, `render_neuro()` |
| `vascular.py` | B5 | built (fix rounds 1-2) | `build_vessels()`, `vessel_table()` |
| `uv.py` | B1/B2 (v0 by B0) | working v0 | `mark_seams(obj, rules)`, `unwrap(obj, method)`, `pack(obj, size, margin_px)` |
| `lookdev.py`, `bake.py`, `texgen.py` | B7 | built | `build_materials()`, `lookdev_on/off`, `prepare_attributes`; `prepare_uvs`, `bake_all`, `bake_tileables`, `bake_painter_inputs`, `write_texture_manifest`; numpy texture library (tileables, iris, sclera, decals, room/props) |
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
├── GB_HighRes    GB_Head_HR, GB_Body_HR, GB_Skeleton_HR, GB_Organs_HR, GB_Brain_HR   (bake sources)
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

## Look-dev and bakes (B7) → `gore-game/assets/generated/subject/textures/`

`python3 build.py --stage bake` (loads every geometry cache, then bakes) or standalone on the saved
build: `python3 bake.py [--only head,body] [--tiles] [--painter] [--quick] [--out DIR]`;
`python3 lookdev.py --render [--baked] [--views body,head,...]` for look-dev renders.

- **Look-dev materials** (`lookdev.build_materials()`, names `GBL_*`) reuse the head project's
  `materials.py` read-only (GH_Skin, GH_Bone, GH_Brain, GH_Eye, GH_Teeth/Gums/Tongue,
  GH_MouthInterior, GH_Muscle) with their Object coordinates shifted into the body frame; new:
  GBL_skin_body (same noise frame as the head skin → continuous across the seam, plus regional
  `lk_*` attributes: palms/soles, knees/elbows/knuckles/ankles, areola/nipple, sun exposure, covered
  skin, B5's superficial veins, dorsal venous networks, moles, body hair, sebaceous areas),
  GBL_organ (bible surface/interior colours per `gb_organ`/`gb_sub`, cavity linings via
  `lk_interior`), GBL_cartilage, GBL_cloth, eye FX, vessels, cord. They are swapped in only during
  bakes/renders (`lookdev_on/off`); the exported glb keeps the `GBM_*` placeholders.
- **Inner atlases re-charted** (`bake.prepare_uvs`): GB_Skeleton, GB_Organs and GB_Brain get
  normal-cone charts (≤ 60° from each chart's axis, planar-projected in metres → uniform texel
  density, no folds), marrow cores/cavities at reduced density, packed with a 3–6 px margin. Cached in
  `.cache/uv-<mesh hash>.npy`. **build.py must call `bake.prepare_uvs()` in every build that exports
  those meshes** (it runs only in the bake stage today), otherwise the exported UVs do not match the
  textures (`b7_textures_match_uvs` warns).
- **Sets** (albedo sRGB, normal tangent OpenGL +Y MikkTSpace on LOD0, ORM = AO / roughness /
  metallic / SSS mask): head 2048, body 2048, shorts 1024, mouth 1024, skeleton 2048, organs 2048,
  brain 1024. LOD1 meshes share their LOD0 atlas. Every map is dilated 8 px and push-pull filled.
- **Eyes**: `eye_iris_albedo.png` (1024², RGB + A height, radius 6.2 mm at the edge, pupil drawn at
  2.2 mm), `eye_iris_normal.png`, `eye_sclera_albedo.png` (GB_Eye atlas, A = 0 in the cornea window).
- **Tileables** 512² (`tile_<name>_{albedo,normal,orm}.png`, ORM.A = height): muscle_fibre,
  muscle_cross, fat_lobule, bone_cut, bone_surface, diploe, blood_crust, cloth_weave, skin_micro
  (detail map, albedo 0.5 = neutral); physical repeat size `tile_m` in textures.json.
- **Decals**: `decal_blood_{albedo,normal,orm}.png`, 8 × 8 tiles of 256² (one row per kind:
  round drops, angled drops, spatter, runs, smears, pools, soaked stains, crust), A = coverage,
  ORM.A = thickness; per-tile size and direction in textures.json.
- **Room/props**: `room_{tile,grout,epoxy,rubber,stainless,galvanised}`, `prop_{polymer_stipple,
  walnut,hickory,g10,glove}` tileables with `tile_m`, mapped to B8's GBPM_* names in `material_map`.
- **Painter inputs** (head, body, shorts): `<set>_position.exr` (1024², half float, RGB = rest position
  − segment origin from manifest `segment_origins`, A = segment code, −1 outside), `<set>_rest_normal.png`,
  `<set>_valid.png`, `<set>_bone.png` (512², R dominant bone, G second, B weight, A inside).
  Body tissue depth / tension maps are B1's.
- **Godot vs Cycles**: `lookdev_godot_ref/` is a tiny Godot project that loads the exported glb at runtime
  with the baked sets and renders the `lookdev.TURNTABLE["ref"]` cameras (command in its `main.gd`);
  `renders/lookdev_cycles_vs_godot.png` = Cycles (top) vs Godot 4.5.1 (bottom).
- `textures/textures.json` (schema `gb.textures/1`) lists every file with channels, sizes, uv_hash,
  bake statistics and timings; B6 should copy its `sets` into manifest `textures`.

## Rig, weights, export (B6) → `rig.json`, `GB_Subject.glb`, `GB_Subject_LOD1.glb`, `manifest.json`

`python3 build.py --stage rig` (placeholder + every geometry cache + weights + export + verify, ~3.5 min) or
`python3 posetest.py --reskin [--render] [--only a,b] [--detail]` on the saved build.

- **Armature**: 39 bones from `gb_data.rig_table` plus two documented B6 fits (`rig.bone_rows()`): `jaw` head
  = B2's measured TMJ hinge (0, 0.0085, 1.645); `thumb_*` = B1's thumb (CMC (±0.4608, 0, 0.9166) → tip). Every
  other joint equals RB §7.2 (0.00 mm). `skin_all` rebuilds a stale armature (`ensure_armature_fit`).
- **One weight function** `rig.weights_at(points)` for every layer (plan D8): territories (arm, leg, neck+head,
  shoulder girdle = clavicle + scapula + acromion + top of the shoulder, trunk) split by joint *gates*
  `smootherstep((x - o(phi)) / w(phi))` with sector-dependent offsets/widths (flexor / lateral / extensor /
  medial, 8 sectors on the trunk). Elbow and knee gates are **ray gates** (x = elevation angle seen from the
  joint centre) so skin, muscle shell and vessels on one ray keep identical weights and stay nested in deep
  flexion; the olecranon / patella skin moves 100 % with the forearm / shin. Jaw = Voronoi of the head project's
  mandible vs skull (+ skin within 12-22 mm of the mandible) plus the **throat sheet** (`rig.JAW_THROAT`: the front
  of the neck shares the jaw 0 → 1 from z 1.46 to the chin, columns = rays from the neck axis, fading toward the
  axis so spine/cord/deep vessels stay on the neck), so opening the mouth stretches the whole front of the neck
  instead of tearing a band under the chin; lids = B2 `face_weights` inside the same function;
  hand fingers / thumb from B1's MCP arc and thumb polyline; toes along the oblique MTP row. 4 influences,
  1/4096 grid, rows sum exactly to 1. Gate numbers are in `rig.json` `weights`.
- **Followers** (`GB_BrowLash`, `GB_EyeFX_L/R`): `weights_at` at each vertex's `gb_anchor_*` (their
  `gb_rigid_bone` tags are B2's fallback and are ignored; verify's rigid check skips them).
- **Rigid parts** (`gb_rigid_bone >= 0`): 100 % on their bone (skeleton pieces, variants, eyes, teeth, tongue).
- **Twist bones**: `upper_arm_twist_*` carries the proximal upper arm (driver: -0.5 × the shoulder twist, i.e.
  world 50 %), `forearm_twist_*` the mid/distal forearm (+0.5 × the hand's pronation). Drivers in
  `rig.json kinematic.*.driver` (swing-twist decomposition about the rest twist axis); `rig.apply_pose` applies
  them. Without drivers the twist bones carry 100 % (no candy-wrap relief, no harm).
- **Jaw opening** = rotation about +X through the TMJ hinge **plus the TMJ glide** `rig.jaw_glide(deg)` =
  (0, -0.45, -0.25) mm per degree of opening (condyle sliding down the eminence; `rig.json kinematic.jaw.rule`).
  Limit 26 deg (about 45 mm incisal opening). G6 must apply both; the weights assume it.
- **Key poses** `pose_idle/guard/cower/brace`: joint angles about the resolved world axes (`rig.POSES`), all inside
  the live limits; bent-knee poses key a hips translation that keeps both ankles within 0.4 mm of rest.
- **rig.json** adds to B0's table: `kinematic` (fingers/thumb/toes/twist/jaw/eye axes, limits, drivers), directional
  `torque_cap_nm` (strongest direction at the top of the plan range), `face` = B2's measured lid table
  (`head_face_rig.json`), `poses` (angles + hips translation), `weights` (gate table).
- **Export** (`export.export_subject`): re-applies B7's inner atlases (`bake.prepare_uvs`, cached) so UVs match
  the textures; re-bakes the painter `*_bone.png` maps when the weight fingerprint changes; GB_Subject.glb (21.5 MB)
  + LOD1 (head + body at 50 %) + sidecars (+ B3 `bones.json`) + manifest (files with sha256, texture sets with
  import hints, file limits, rig fits, deformation results, round trip, Godot import).
- **Checks** (verify `b6_*`): joint positions, one weight function (vertex groups == `weights_at`), seam-ring
  weights identical on head and body, followers, FB-2 deformation (`posetest.TESTS` level `fb2`: elbow 130.5,
  knee 121.5, shoulder abduction +60/+90 from the bind, hip flexion 108: no inner-layer vertex > 3 mm outside the
  posed skin by signed ray-crossing winding number or newly visible from outside through a tear / fold (26-ray
  exposure test); volume loss < 15 %), quality poses (warn), rest-pose nesting
  (warn, other owners' geometry), key poses, rig.json, manifest + file limits, **round trip** (re-import in a fresh
  Blender process), **Godot 4.5.1 import** (temporary project under xvfb/OpenGL: 39 bones, every mesh skinned with
  4 weights + UV2, blend shapes, 4 animations, CUSTOM0 RGBA32F injection, and Godot's own skinning of 6 poses set
  from rig.json world axes equals Blender's LBS within 0.02 mm on 74.5k vertices).
- **Godot notes**: the imported Skeleton3D orders bones depth-first (not rig.json's order): always map by name
  (`Skeleton3D.find_bone`); rig.json indices (and `gb_rigid_bone`, painter bone maps) index `rig.BONE_NAMES`.
  Skins register with the skeleton only with a real renderer (headless dummy: `bake_mesh_from_current_skeleton_pose`
  fails).

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
(fail, B5), triangle budgets (fail, strict plan §4.1 numbers), stage caches current, UV overlap (exact),
B6 rest-pose nesting and every deformation test (fail). A check returning `(None, detail)` is a SKIP
(bake-dependent checks when the bake stage was skipped on purpose).

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
- **build.py** (fixed in fix round 1): every stage's cache key is its whole import closure (`SOURCES`) plus
  `gb_geom.py`, the head project's sources and the upstream stages' keys, so any edit invalidates exactly the
  stages it can change; side files (maps, hair cards, bones.json) are cached and restored with the stage.


## Fix round 1: changes and deviations (kept current)

Deviations from the bible / plan that the code now makes on purpose (each also noted where it is coded):

| Item | Bible / plan | Now | Why |
|---|---|---|---|
| Laryngeal prominence | RB §7.1 (0, −0.058, 1.537) | (0, −0.061, 1.527) skin; B4 thyroid cartilage recedes 6 mm toward its lower border | 2.3 cm under the menton with a real cervicomental angle; the cricoid skin point (−0.055 at 1.515) stays consistent |
| Iliac crest top / tubercle | RB table | x 0.132 / 0.128 | inside the flank skin with 7-12 mm of cover |
| Patella centre / skin | RB table | (0.090, −0.0215, 0.500) / (0.090, −0.039, 0.499) | knee girth 37.4 cm with 5-6 mm pre-patellar cover |
| Scapula superior angle | (0.080, 0.085, 1.475) | z 1.468 (T2 level) | at 1.475 it sat 10 mm under the D19 seam plane and could not be covered by 5 mm of trapezius without the skin rising above the seam |
| Spleen centre | RB OBB centre | `viscera.SPLEEN_CENTROID` (0.0987, 0.0225, 1.2233) | the RB OBB centre lies on the rib cage wall; the lens sits 16 mm inward |
| Liver AABB | RB AABB | x tolerance 15 mm | the RB box is 2 cm wider than the right cage allows |
| Lung AABB | RB AABB | x 8 / y 6 mm tolerance; volumes below FRC (warn) | the lungs fit the rib cage model (ribs win) |
| Left adrenal | RB centre | ellipsoid 6 mm lower before the kidney carve | the kidney pole carves the lower crescent; the carved gland is centred |
| GB_Brain budget | plan 14k | 28k (`TRI_BUDGET`) | hero asset of every headshot / cutaway |
| Body atlas | 2k | 4096 px (brain 4096 since fix round 2) | body / brain texel density |
| Rib arcs | 4 table points | + 2 round arc mid-points per rib (`ribs.rib_points`) | ribs were polygonal between the table points |
| Neck girth | 38 cm at z 1.515 (horizontal) | measured as the anthropometric tape (`verify.neck_tape`: anchored at the cricoid point, perpendicular to the neck, smallest of 0-16 deg tilts): 39.1 cm | a horizontal cut at 1.515 runs below the C7 skin landmark (0.075, 1.532) through the trapezius (the neck *base*, 42.6 cm) |
| Vessel tube rings | 0.35-0.5 r Douglas-Peucker | 0.7 r / 3 mm, turn limit by tube size (18-60 deg), 75 mm max span + forced rings at every limb joint | the 14,000-triangle plan budget with no kinks at joints |
| Eye centres | RB §1.2 (±0.032, −0.050, 1.669) | follow the head project (±0.0315, −0.0475, 1.669) | the head team moved the eyes 2.5 mm back (head is authoritative) |
| Left lung | RB box | cardiac notch below z 1.345 medial of x 4.8 cm | the lingula tip reached the lower sternum over the heart |
| Epiglottis | - | behind the hyoid (0, −0.027, 1.555) | it sat in front of the hyoid under the submental skin |
| Cord roots / cauda | straight stubs to the table canal width | run down beside the cord and exit 1.2 mm inside B3's fitted canal; C1 exits between the skull base and the atlas | the stubs cut through pedicles and the condyles (8 % of GB_Cord vertices in bone) |
| Larynx / thyroid (fix round 2) | R05 prominence (0, −0.058, 1.537), cricoid 1.513; thyroid lobes 1.505 | larynx 12 mm lower (`viscera.LARYNX_DZ`), prominence 2 mm back, 28 mm laminae with a 1 cm V notch; thyroid 5 mm lower; skin prominence (0, −0.060, 1.515), cricoid skin 1.502 (authoring frame) | the head project's menton is at 1.544: at the bible height the thyroid cartilage filled the space under the chin (the 'pouch'); now a submental plane (`body_skin.SUBMENTAL_*`) and a cervicomental angle of ~110° exist |
| Bone pads (fix round 2) | - | pads sink smoothly into their bone over 18 mm beyond the site box (`PAD_FADE`, `PAD_SINK`); sternum / spinous pads blend over 20 / 11 mm | the old 3 m/m cut left straight shading lines across the chest (sternum box bottom), the lower back and beside the manubrium |
| Skin smooth steps (fix round 2) | - | `body_skin.sstep` is quintic (C2) | cubic steps printed curvature lines along every relief border in raking light |
| Body LOD0 density (fix round 2) | - | zoned collapse weights (`DEC_W_*`): torso edges ~9 mm (p95 14 mm) instead of 2-7 cm | long torso triangles showed as straight lines across the chest and back |
| Muscle shell under folds (fix round 2) | RB §7.6 fat | +2.5-6 mm extra shell depth under the axillary folds, perineum and plantar pad (`FOLD_FAT_SITES`) | LBS compresses the skin there more than the shell (FB-2 pokes 3-10 mm) |
| Inner atlases (fix round 2) | non-overlapping, 16 px margin | 9 px margin; folded normal-cone charts repaired per mesh (`bake.RECHART[...]['repair']`): skeleton / organs re-flattened with an angle-based unwrap (`unfold_charts`), brain split into planar sub-charts (`refine_folded`, no texel distortion) on a 4096 atlas; overlap < 0.1 % | isolating single faces made 4-8k islands and halved the texel density; the angle-based unwrap of gyri gave 2.5-stop texel distortion |

Rig / tests:
- Deep layers (bone, organs, vessels, nerves, cord, brain) take the head share of the 12-22 mm band around the
  mandible (they turn with the head) but the jaw share only within 2-6 mm of the bone; the throat sheet (jaw
  share of the submental skin) starts at z 1.528 (above the thyroid cartilage), so opening the mouth no longer
  drags the neck skin over the larynx.
- The mandible band does not reach below the jaw line (`body_skin.head_clip_z`): the submental skin over the hyoid
  and larynx is only stretched by the throat sheet; the back of the mouth floor (tongue base / vallecula) follows
  the jaw 30 %.
- The neck gate's radial containment was widened (68-112 mm) so neck rotation spreads over the trapezius base.
- GB_Body LOD0 is decimated with denser rings within 4 cm of every limb joint (`joint_weighted_decimate`).
- The shorts take the skin weights at their nearest skin point (smoothed over the cloth).
- `posetest`: a point counts as outside only if the global winding number AND the nearest posed face agree
  (a remote inside-out fold along a winding ray no longer flags rigidly-inside points); "exposed" needs two
  escaping rays; shorts in a closed skin crease (two facing skin sheets within 25 mm) are reported as pinched.

## Final body frame: neck lengthening (fix round 2, user feedback)

The RB frame put the menton only 9.1 cm from the sternal notch (chin pressed into the neck). All stages still
author and cache in that **authoring frame**; `build.py` then warps the whole scene once before the rig stage
(`gbc.set_scene_frame("final")`): `z_final = z + NECK_LIFT · smoothstep(1.455, 1.540, z)` with `NECK_LIFT = 0.015`.
Below the jugular notch nothing moves; above the jaw line everything (head, skull, brain, eyes, C1-C2) moves up
15 mm rigidly; the neck stretches. Final: menton-notch 10.6 cm, stature 1.795 m, head offset (0, 0.020, 1.662),
seam plane z 1.48929. The armature is built in the final frame; `rig.weights_at(p, layer, frame="final")` unwarps its
input; exported JSON points are final (`warp_json`, each payload has `frame_note`); `verify_all` runs B6/B7 checks
in the final frame and all others in the authoring frame. `gbc.authoring_json` reads an exported payload back.
