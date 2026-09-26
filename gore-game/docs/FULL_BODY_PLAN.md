# Gore Head — Full-Body Build Plan (technical direction)

> Audio removed by the user; the game has no sound. Audio sections below were deleted or reworded to visuals.
> **Visual reference notes:** also apply `gore-game/docs/REFERENCE_NOTES.md` (generic properties of real wounds and blood from forensic reference photos: far more blood coverage, soaked cloth, big dark lumpy pools, shredded irregular wet tissue with clots and strands, varied colours). A clean, dry, uniform or blood-sparse wound fails review like a sticker does.


Project: **Gore Head**, a native Godot 4.5 PC game (Forward+, GDScript + Godot shaders, built-in Jolt physics) with every asset generated procedurally in Blender 5.0 (`bpy`). The subject is a fictional, procedurally generated adult. No real person is modelled.
Audience: the engineers who build the full-body version, one work package each.
Status: v1.0, 2026-09-26. **Numbers about the body, wounds, bleeding, physiology, eyes and death come from [`REALISM_BIBLE.md`](REALISM_BIBLE.md) (cited as `[RB §x]`). This document says how to build them.** Where this plan changes a bible decision it says so in §0.3.

---

## 0. Read this first

### 0.1 Evidence tags and sources

Tags as in the bible: **V** verified (source read, or recomputed), **C** consistent with cited literature, **E** engineering estimate (tune), **G** game choice, **K** this author's knowledge, not re-verified in this pass (QA re-check before relying on it).
Technical sources read for this plan are listed in §12.3 as `[T1]…[T12]`. Medical sources are the bible's.

### 0.2 Decisions at a glance

| # | Topic | Decision | Why | Rejected |
|---|---|---|---|---|
| D1 | Scene | The subject stands on a floor mark in a 6 × 6 × 3 m tiled **forensic test room**, 1.3 m in front of a rubber-granulate bullet backstop. The player is first-person, 3 m away. When incapacitated the subject **collapses into a powered Jolt ragdoll** and stays down (no get-up in v1) | Pale tile shows spatter and runs; box geometry makes particle collision and drop landing cheap and exact; one light rig keeps the budget | Open or furnished environments; restraint rigs (extra constraint physics, prevents a free collapse) |
| D2 | Modesty | Loose mid-thigh **athletic shorts** (charcoal cotton jersey). The skin under them is smooth and featureless (no genital geometry). Shorts cannot be removed; they take holes, blood soak and char, never disappear | The body is not nude; nothing explicit exists to reveal | Underwear briefs (too little coverage for shotgun wounds to the pelvis) |
| D3 | Subject | One reference adult male, 1.78 m, 75 kg, ~15 % fat, A-pose bind [RB §7]. v1 variation: skin tone, iris colour, per-victim physiological traits, wound seeds. Geometric build variants are v2 | All anatomy tables are for this body; variants multiply build, bake and validation work | Runtime morph of body build (breaks the vessel/organ fit) |
| D4 | Hands and feet | **Simplified** (user request): four fingers and thumb as smooth capsules in a relaxed curl, no nails or knuckle geometry (texture only); toes merged into the foot. Kinematic `fingers_*`, `thumb_*`, `toes_*` bones only | Cuts ~30 bones, ~20k triangles and 10 physics bodies | Articulated fingers |
| D5 | Skeleton | Full skeleton as render meshes (carpals/tarsals as blocks), skull and mandible from the head project, ~60 hit capsules, pre-fractured variants for the vault and long bones | Needed for bullet tracks, fractures, X-ray | Bones as capsules only (no X-ray, no visible fractures) |
| D6 | Organs | Heart (4 chambers, pericardium), lungs, diaphragm, liver + gallbladder, spleen, kidneys (+ adrenal hit volumes), stomach, pancreas, bladder, larynx/trachea/bronchi, oesophagus, thyroid, **greater-omentum apron instead of intestines**, brain (from the head), brainstem + cerebellum, spinal cord C1–S5 + cauda equina | User scope; the omentum is what an opened abdomen shows first anyway | Intestines (explicitly out of scope) |
| D7 | Vessels | ~140 named segments with left/right expanded (bible §3.3 plus limb veins, intracranial arteries, dural sinuses), ~20 capillary beds, main nerves as data curves. Authored as Blender curves → tube meshes + `vessels.json` | Bleeding is decided by where the track crosses a real vessel [RB §2.0, §3.3] | Region-only bleeding |
| D8 | Rig | 39 bones (§3.1.1), A-pose bind, 4 influences, **one analytic weight function shared by every layer** (skin, muscle, bones, organs, vessels) | Layers deform together, so vessels stay inside the body | Blender bone-heat weights (per-mesh, inconsistent between layers) |
| D9 | Ragdoll | 20 `PhysicalBone3D` under `PhysicalBoneSimulator3D` on Jolt; script PD torques with **separate flexor and extensor caps per joint axis**, fed by a myotome map (§3.2) | Paralysis by cord level becomes a data table; asymmetric caps create the real postures | 6DOF springs (uncapped in 4.5 [RB §8.2]); canned death animations |
| D10 | Gore on skinned meshes | Rest position in `CUSTOM0` (RGBA32F) injected at import; ≤ 64 SDF wounds per subject + 3D lookup grid; two skin-shader variants; analytic cavity ≤ 12 mm; `discard` + **runtime-generated skinned wound-wall meshes** + inner layers for larger wounds; compute-painted atlases [RB §8.1] | Proven in the bible research; wall meshes give real depth without CSG | World decals on skin; runtime remeshing |
| D11 | Languages | **GDScript + Godot shaders only** (GLSL compute through RenderingDevice counts as Godot shaders). No C++/GDExtension, no C# | The user forbids downloaded add-ons; godot-cpp and a C++ toolchain would be downloads | GDExtension (bible §8.1; see §0.3) |
| D12 | Physiology | Pure GDScript `RefCounted` model, main thread, fixed 20 Hz (every 3rd physics tick), deterministic seed, headless unit tests | Cost is < 0.3 ms per tick in GDScript (E); determinism makes scenario tests possible | Worker thread (harder to test, no benefit at this cost) |
| D13 | Reveal and X-ray | Inner meshes hidden per segment/organ until an open wound lies within 5–10 cm; back faces of every closed inner mesh shade as that tissue's cut interior; X-ray by 4.5 stencil [RB §8.1] | Cheap, and holes never look hollow | Always-on inner meshes |
| D14 | Eyes | Refracted-iris eye shader with pupil, gloss, clouding and tache noire as instance uniforms; lids and gaze on bones driven by an `EyeModifier` (`SkeletonModifier3D`); tearline + occlusion meshes | Bible §5 behaviour needs per-frame control of 8–14 values | Texture-swap eyes |
| D15 | Asset hand-off | One subject `.glb` (meshes, skin, blend shapes, placeholder-named materials, no images) + JSON sidecars + baked PNG/EXR textures. All game materials are Godot `ShaderMaterial`s assigned by the import script | Godot cannot run Cycles node trees; keeping images out of the glb lets Godot import each texture with the right settings | Embedded textures |
| D16 | Audio | **None** (user decision): the game has no sound | Removed by the user | Any audio system |
| D17 | Performance | **Design by budget** (§4); automated gates on counts and CPU ms under lavapipe; GPU ms measured on real GTX 1660 / RTX 3060 hardware at milestones M2 and M4 | Lavapipe GPU timings are meaningless for the target | fps checks on this machine |
| D18 | LOD | Single LOD0 for the subject in v1 (the room is ≤ 6 m deep, the subject is always ≥ 15 % of screen height); LOD1 (50 %) built and kept as a fallback | Skinned auto-LOD can glitch [RB §8.2]; distances are short | Auto LOD on skinned meshes |
| D19 | Neck seam | Head mesh (head atlas, 0.24 mm texels) and body mesh (body atlas, 0.84 mm) meet on a **canonical seam ring** at z ≈ 1.485 m (body frame); both meshes are zipped to identical ring vertices | Keeps the existing high-resolution head unchanged; the seam is invisible in position and normal | Rebuilding the head at body resolution (loses lids, lips, ears) |

### 0.3 Deviations from the bible (and why)

| Bible item | Change | Reason |
|---|---|---|
| §8.1 "C++ GDExtension for hit pipeline, anatomy march, vessel solve, rivulets, slicer" | GDScript, with the heavy parts moved into **native engine calls**: Jolt shape and ray queries in a private rest-space physics space (anatomy march, §3.7), GPU compute (painting, floor flow), analytic hero-drop landing (no per-frame ray casts). Budget per pistol shot raised from 0.5 ms to **≤ 2 ms** (spread over two frames if needed) | D11. The vessel solve is closed-form and cheap in any language |
| §8.1 runtime knife slicer | **Dropped.** Deep knife cuts use slab SDF + `discard` + generated wound-wall meshes | 50–300 ms in GDScript [RB §8.1]; the wall mesh shows the same layers |
| §8.3 wound record "3 × vec4" | **5 texels (vec4) per wound** (§3.3.3) | Per-layer radii and packed flags do not fit in 3 |
| §8.3 wound grid 60×16×80 | Grid sized from the measured A-pose bounds: 50 × 75 × 16 cells of 2.5 cm (≈ 240 KB RGBA8) | Measured, not assumed |
| §8.4 "Physiology on a worker thread" | Main thread, fixed 20 Hz | D12 |
| §7.2 bone names `upper_arm.L` | `upper_arm_L` (underscore suffix) | Node-name safety in Godot; matches the head contract's `_L/_R` |
| §7.5 anatomy tables | Exported JSON keeps the **body frame** (Z up); the game converts once with `B2G(v) = Vector3(v.x, v.z, -v.y)` | Engineers can compare JSON numbers directly with the bible |

### 0.4 Limits of this pass

The shared WebSearch budget was already exhausted (200/200) when this plan was written, and medical sites (NCBI, Wikipedia, Radiopaedia, Physiopedia, ASIA) are egress-blocked. Technical facts were verified by reading Godot 4.5-stable class references and docs, the Blender 5.0.0 source and the glTF exporter bundled with the local `bpy` 5.0.1 (§12.3). Neuro-anatomy used for the myotome map comes from the project's R04 §6 (ISNCSCI key muscles, recall-consistent) plus this author's knowledge (**K**), flagged in §3.2.

---

## 1. Product scope for the full body

### 1.1 In and out of scope (v1)

| In | Out (v1) |
|---|---|
| Full body with skin, fat and muscle layers, real skeleton, heart and vital organs, brain, brainstem, spinal cord, arteries and veins, simplified hands and feet | Intestines, genitals, detailed hands/feet, scalp hair geometry (buzz cut as texture), female or other body builds (v2) |
| Pistol, shotgun, knife, fist, hammer, torch; examine tools (grab/drag, press, wipe, lift lid, penlight, ruler, thermometer) | Other weapons; restraints |
| Wounds per bible §2 on any body region; fractures; vessel-driven bleeding; internal bleeding compartments | Runtime knife slicing; limb amputation (only skull burst in v1; hand/finger avulsion v2 per [RB §8.1] realism gate) |
| Physiology §3–4 (bleed-out with time bands, shock, consciousness, brainstem and cord paralysis), eyes and face §5, post-mortem §6 | Treatment (tourniquets exist only as the physiology's `compress` input for tests) |
| Standing → flinch/clutch → collapse → conscious or unconscious down states → death → forensic time-lapse | Getting up again after a collapse (partial recovery shows as pushing up on the arms) |
| X-ray view, injury case log, vitals overlay, time controls | Multiple simultaneous subjects (the architecture allows 2, the budget assumes 1 live + 1 sleeping) |

### 1.2 The subject

- **Body**: reference male per [RB §7.1] (landmarks, girths: chest 100, waist 84, hips 97, upper thigh 58, calf 37.5, neck 38 cm; biacromial 42, bideltoid 49 cm), A-pose bind (arms 30° from vertical, palms to thighs, thumbs forward).
- **Head**: the existing `gore_head` head, placed with `p_body = p_head + (0, 0.020, 1.647)` [RB §1.2]; not rescaled.
- **Hair**: 3 mm buzz cut painted into the head albedo/roughness (stubble), eyebrows and eyelashes as alpha-scissor cards converted from the head project's hair curves. Blood mats the scalp by darkening and gloss.
- **Hands**: length 19.2 cm, breadth 8.7 cm (R05, ANSUR II); fingers relaxed 15–25° per joint, fused webbing, nails and creases in texture only. **Feet**: length 26.8 cm, breadth 10.2 cm (R05, ANSUR II), toes merged, barefoot.
- **Shorts**: waistband z 1.02–1.05 m (35 mm elastic band), hem at mid-thigh z 0.68 m, 4–8 mm off the skin at the seat, flaring to 15 mm at the hem, 1.2 mm solidified cloth, albedo `#2E3033`, roughness 0.85, no print or logo.
- **Per-subject variation (v1)**: `skin_tone` 0–1 (Fitzpatrick I–VI ramp from the head materials), iris hue, all per-victim traits from the bible (bone strength ×0.75–1.25, skin laxity, bruisability, `relative_brady`, `faint_upright_loss`, `hr_response_scale`), and the wound seed stream.

### 1.3 Scene: the forensic test room

Godot frame (metres, Y up); the subject stands at the origin facing **+Z**.

| Element | Specification | Why |
|---|---|---|
| Room | Interior x −3…+3, z −1.6…+4.4, y 0…3.0 | Fits the 8 × 8 m floor splat map [RB §8.3] |
| Floor | Anti-slip grey epoxy `#8E9194`, roughness 0.55 dry; **1 % fall toward a Ø 150 mm drain at (0, 0, +1.0)** | Pools follow the slope and reach the drain (pool checklist [RB §3.11]) |
| Walls | White glazed tile 150 × 150 mm `#E8E6E1` (roughness 0.15, non-absorbent), grout 2 mm `#9C9A94` (roughness 0.8, absorbent: blood wicks into grout) | Spatter and wall runs read clearly |
| Backstop | Rubber-granulate panel 2.4 × 2.2 × 0.3 m on the rear wall, front face at z = −1.3, `#2A2A2A`, roughness 0.9, absorbent | Exit wounds' forward spatter lands 1.3 m behind the subject (1–4 m range [RB §2.1.3]) |
| Ceiling | 3.0 m, `#DCDCD8`; two 1.2 × 0.6 m LED panels | Ceiling deposits from shotgun bursts [RB §2.2.3] |
| Lights | 2 × SpotLight3D (panel, 100° cone, shadow 1,024) + 1 key SpotLight3D in front-above the subject (shadow 2,048), 5,000 K (`#FFE4CE`), ambient from a single ReflectionProbe (update once) | 3 shadowed lights ≤ the bible's 2–4 [RB §8.4]; no SDFGI/VoxelGI |
| Props | Floor mark (yellow tape cross `#D8B31E`) at the origin; 1 m forensic scale bar (10/100 mm ticks) on the side wall; stainless mortuary table 2.0 × 0.8 m at x = +2.4 (`#B8BBBD`, metallic 1, roughness 0.3); instrument trolley with the examine tools | Size reference for wound judgement; table for post-mortem work |
| Player | CharacterBody3D, eye height 1.65 m standing / 0.9 m kneeling, spawn (0, 0, +3.0) facing −Z, walk 1.4 m/s | Contact shots need walking up to the subject |
| Particle collision | 6 room boxes + backstop + table + trolley (9 `GPUParticlesCollisionBox3D`) + 4–8 bone spheres + 1 heightfield (512² over 4 × 4 m around the subject, `UPDATE_MODE_ALWAYS`) | ≤ 32 colliders per system [RB §8.2]; no editor-only SDF bake needed |

### 1.4 Interaction loop and subject states

```
STANDING_IDLE ──hit──► REACTING (flinch 0.2–0.5 s partial ragdoll, guard, clutch IK) ──► STANDING_IDLE
      │                     │
      │ LOC / cord lesion above L2 / brainstem / leg failure / faint   hemiparesis or ataxia:
      ▼                     ▼                                          STAGGER (falls toward the weak / lesion side)
 COLLAPSING (tone → targets, 0.35–0.55 s to first contact [RB §4.10]) ◄───────────┘
      ▼
 DOWN_CONSCIOUS (writhe 0.3–1 Hz, clutch, prop up, drag with arms)  ⇄  DOWN_UNCONSCIOUS (flaccid, posturing, seizure, agonal)
      ▼ circulatory arrest
 DEAD (flaccid; eyes/jaw §5.4, §6.1; rigor lock later) ──► FORENSIC (post-mortem clocks at 120×/720× [RB §1.3])
```
The physiology owns every transition trigger (consciousness resolver, motor output, arrest flag). The motor layer only executes them.

### Simulation parameters (scope and scene)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `subject_ref` | 1.78 / 75 / 15 | m / kg / % fat | A-pose bind | [RB §7] V |
| `head_offset_body` | (0, 0.020, 1.647) | m | Head frame → body frame | [RB §1.2] V |
| `room_interior` | 6 × 6 × 3 | m | x × z × y | G |
| `floor_fall` | 1 % toward drain at (0, 0, 1.0) | — | Feeds the splat-map spread height | G |
| `backstop_distance` | 1.3 | m | Behind the subject | G |
| `player_spawn_distance` | 3.0 | m | Distant range class for 9 mm (> 1.2 m) [RB §2.1.1] | G |
| `shorts_band / hem` | 1.02–1.05 / 0.68 | m (z) | Mid-thigh | G |
| `shorts_offset` | 4–8 (seat) → 15 (hem) | mm | Loose fit | G |
| `shadowed_lights` | 3 (1 × 2,048, 2 × 1,024) | — | | [RB §8.4] G |

### Visual/behavioural checklist (scope and scene)
- The subject stands relaxed on the yellow mark, breathes, blinks and watches the player; the backstop and tiled walls behind him catch exit spatter.
- The body is covered from waist to mid-thigh at all times; wounds in that area show through holes in the shorts, and the cloth darkens and spreads the stain wider than on skin.
- A collapse always ends on the floor near the mark; blood pools run slowly toward the drain.
- Hands and feet read as normal at game distance but have no nails or knuckle geometry up close.

---

## 2. Architecture overview

### 2.1 Build and runtime flow

```
BLENDER 5.0 (bpy, 4 cores, offline)                          GODOT 4.5 (runtime)
blender/gore_head (existing: SDF toolkit, head layers,        res://pipeline/import/subject_post_import.gd
                   materials, GN gore reference)                 CUSTOM0 = rest pos (RGBA32F), materials,
        │ import (read-only)                                     layers, visibility, uncompressed
        ▼                                                                │
blender/gore_body  build.py --stage all                                  ▼
  gb_data/ (bible tables) ─► body_skin, head_integration,       Subject scene (res://subject/subject.tscn)
  skeleton, viscera, neuro, vascular, rig, uv, bake, export       Skeleton3D + meshes + PhysicalBoneSimulator3D
        │                                                        ├ AnatomyQuery (private Jolt space, rest pose)
        ▼ writes                                                  ├ WoundStore (CPU records → GPU data tex + grid)
gore-game/assets/generated/subject/                               ├ Physiology (20 Hz, deterministic)
  GB_Subject.glb, *.json, textures/*.png|*.exr                    ├ DamagePainter (compute, Texture2DRD atlases)
gore-game/assets/generated/props/  weapons.glb, room.glb          ├ VfxDirector (60 Hz) + blood FX pools
                                                                  ├ MotorController (PD, 60 Hz) + behaviours
                                                                  ├ EyeModifier / FaceController / SkinState
                                                                  └ RevealManager, FractureManager, XRay
```

### 2.2 Runtime scene tree (one subject)

```
Subject (Node3D, subject.gd)                      facade: apply_hit(), vitals, signals
├── Model (instance of GB_Subject.glb)
│   └── GB_Armature (Skeleton3D)                  modifier_callback_mode_process = PHYSICS
│       ├── GB_Head, GB_Body, GB_Shorts, GB_Eye_L/R, GB_EyeFX_L/R, GB_Mouth, GB_BrowLash   (outer, layer 2)
│       ├── GB_MuscleShell, GB_Skeleton, GB_Brain, GB_Organs, GB_Cord,
│       │   GB_Vessels_Art, GB_Vessels_Ven         (inner, hidden, no shadows, layer 3)
│       ├── GB_Frac_* (fracture variants, hidden)
│       ├── PhysicalBoneSimulator3D (built at _ready from rig.json)
│       │   └── PhysicalBone3D × 20
│       ├── ClutchIK (SkeletonModifier3D)          two-bone IK, standing only
│       ├── BreathModifier (SkeletonModifier3D)    chest/shoulder motion at RR, jaw on gasps
│       └── EyeModifier (SkeletonModifier3D)       eyes, lids, doll's-eye, jaw drop at death
├── AnimationTree                                  idle/guard/cower poses from the glb
├── Anatomy (anatomy_query.gd)  Wounds (wound_store.gd)  Physiology (physiology_node.gd)
├── Painter (damage_painter.gd)  Vfx (vfx_director.gd)  Motor (motor_controller.gd)
├── Face (face_controller.gd)  Skin (skin_state.gd)  Reveal (reveal_manager.gd)  Fractures (fracture_manager.gd)
└── WoundWalls (Node3D, generated skinned MeshInstance3D children)
```

### 2.3 What happens on one pistol shot (budget ≤ 2 ms CPU, visual result on the impact frame)

1. `Pistol.fire()` builds a `HitEvent` (origin, direction, muzzle distance, projectile) → `Subject.apply_hit()`.
2. **Coarse hit**: Jolt ray vs the 20 ragdoll shapes → bone `b` [RB §8.3].
3. **Rest mapping**: `M_b = RestGlobal(b) · PoseGlobal(b)⁻¹` applied to the ray.
4. **Exact skin hit**: ray vs the rest-pose skin trimesh (LOD0 render meshes, face index on) in the private rest space → triangle, barycentrics, UV, segment/region/dermatome codes, entry normal, θ_inc.
5. **Track**: continue to the exit surface (or stop by energy rules [RB §2.1]).
6. **Anatomy query** (§3.7): one `intersect_shape` with a capsule of the cavity radius along the track in the anatomy space → candidate bones, organs, vessels, cord segments, brain label grid → exact classification in GDScript → `AnatomyEvent[]`.
7. **Morphology** (`morph_gunshot.gd`): wound record with per-layer radii, collar, range-of-fire marks, fracture set, exit shape [RB §2.1].
8. **Dispatch**: WoundStore.add → GPU buffers; Painter.queue (soot/stipple/collar/blood); Physiology.inject (bleed sites, organ, cord, brain); Vfx.spatter (back/forward, hero drops); Fractures; Reveal; case-log entry.

### 2.4 Rates and threads

| System | Rate | Thread | Budget (main thread unless noted) | Source |
|---|---|---|---|---|
| Jolt (ragdoll, debris) | 60 Hz | Physics | 0.3–1.0 ms | [RB §8.4] |
| MotorController PD (20 bodies) | 60 Hz | Physics (`_integrate_forces`) | ≤ 0.4 ms | E |
| Physiology + vessel graph | 20 Hz alive / 4 Hz dead | Main (fixed step) | ≤ 0.3 ms per tick | E, D12 |
| VfxDirector | 60 Hz | Main | ≤ 0.5 ms | E |
| Rivulet agents (≤ 24 live) | 30 Hz | `WorkerThreadPool` task | ≤ 0.3 ms per tick off-main | E |
| Hero drops (≤ 150 in flight) | 60 Hz | Main (analytic flight, no per-frame rays) | ≤ 0.2 ms | §3.4.4 |
| Damage painting | Event-driven, ≤ 8 dispatches/frame | Render thread | GPU ≤ 0.2 ms | [RB §8.3] |
| Floor splat spread | 15 Hz | Render thread (compute) | GPU ≤ 0.1 ms | [RB §8.3] |
| Skin masks, livor atlas | ≤ 1 Hz | Main → render | ≤ 0.1 ms | [RB §1.3] |
| Eye/face modifiers | per frame | Main | ≤ 0.1 ms | E |

### 2.5 Frames and spaces

| Space | Definition | Where used |
|---|---|---|
| **Body frame** | Blender: metres, +Z up, face −Y, character's left +X, origin on the floor between the feet [RB §1.2] | All Blender code, all exported JSON |
| Head frame | Origin between the ear canals, same axes; `p_body = p_head + (0, 0.020, 1.647)` | `blender/gore_head` only |
| **Godot model / rest space** | `(x, y, z)_godot = (x, z, −y)_body` (the glTF exporter's `zup2yup`, verified in [T10] `primitive_extract.py` lines 85–88); the subject faces +Z | All runtime anatomy, wounds, paint brushes, SDF grid, CUSTOM0 |
| World | Godot scene world | Physics, VFX, player |

`res://core/frames.gd` owns `B2G()`, `G2B()`, `head_to_body()` and the unit test "heart centre (0.035, −0.036, 1.325) body → (0.035, 1.325, 0.036) Godot".

### Simulation parameters (architecture)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `physics_ticks_per_second` | 60 | Hz | 120 optional for close-ups | [RB §1.3] |
| `physio_tick_alive / dead` | 20 / 4 | Hz | Every 3rd / 15th physics tick | [RB §1.3], D12 |
| `hit_budget_pistol / shotgun` | ≤ 2 / ≤ 4 | ms CPU | Pellet tracks ≤ 1 m merged | §0.3 E |
| `paint_dispatch_max` | 8 | per frame | | [RB §8.3] |
| `agents_max` | 24 (cap 32) | per subject | | [RB §8.4] G |
| `hero_drops_max` | 150 (cap 200) | in flight | Analytic landing | [RB §8.4] G |
| `b2g` | (x, z, −y) | — | Single conversion | [T10] V |

### Visual/behavioural checklist (architecture)
- Hole, first blood and spatter all appear on the impact frame; nothing waits for a physiology tick.
- Bleeding, jet height and pallor never step visibly at 20 Hz (VFX interpolates).
- A shot to the same body point produces the same wound whether the subject stands, lies curled or is mid-fall.

---

## 3. Key technical designs

### 3.1 Rig and ragdoll

#### 3.1.1 Bones (39 deform bones, A-pose bind)

Positions are the bible's [RB §7.2] unless marked; names are `snake_case` with `_L/_R`. Right side mirrors x.

| Bone | Parent | Head → tail (body frame, m) | Notes |
|---|---|---|---|
| `root` | — | (0, 0, 0) → (0, 0, 0.10) | Never simulated |
| `hips` | root | (0, −0.005, 0.965) → (0, 0.006, 1.027) | Ragdoll root |
| `spine` | hips | (0, 0.006, 1.027) → (0, 0.002, 1.212) | Lumbar |
| `chest` | spine | (0, 0.002, 1.212) → (0, 0.049, 1.353) | Lower thorax |
| `upper_chest` | chest | (0, 0.049, 1.353) → (0, 0.015, 1.490) | |
| `neck` | upper_chest | (0, 0.015, 1.490) → (0, 0.015, 1.622) | |
| `head` | neck | (0, 0.015, 1.622) → (0, 0.020, 1.780) | Nodding pivot = atlanto-occipital (0, 0.015, 1.622) |
| `jaw` | head | TMJ axis centre (0, 0.000, 1.640) → menton (0, −0.060, 1.544) | E: fit to `GH_Jaw` condyles |
| `tongue` | jaw | (0, −0.030, 1.585) → (0, −0.075, 1.590) | E; falls back at death |
| `eye_L` | head | (0.032, −0.050, 1.669) → +12 mm along −Y | Eyeball centre [RB §1.2] |
| `lid_upper_L`, `lid_lower_L` | head | At the eyeball centre, tail +15 mm up / down | Rotate about the eye's X axis |
| `clavicle_L` | upper_chest | (0.025, −0.040, 1.450) → (0.165, 0.010, 1.462) | |
| `upper_arm_L` | clavicle_L | (0.180, 0.020, 1.415) → (0.325, 0.020, 1.164) | |
| `upper_arm_twist_L` | upper_arm_L | mid-arm → elbow | Kinematic; 50 % of shoulder twist |
| `forearm_L` | upper_arm_L | (0.325, 0.020, 1.164) → (0.460, 0.020, 0.930) | |
| `forearm_twist_L` | forearm_L | mid-forearm → wrist | Kinematic; carries pronation |
| `hand_L` | forearm_L | (0.460, 0.020, 0.930) → (0.508, 0.020, 0.848) | |
| `fingers_L` | hand_L | MCP3 (0.508, 0.020, 0.848) → tip (0.553, 0.020, 0.770) | Kinematic curl (grip, tenodesis, cadaveric spasm) |
| `thumb_L` | hand_L | CMC ≈ (0.468, −0.005, 0.915) → tip (0.500, −0.030, 0.840) | E, kinematic |
| `thigh_L` | hips | (0.087, −0.015, 0.918) → (0.092, 0.020, 0.492) | |
| `shin_L` | thigh_L | (0.092, 0.020, 0.492) → (0.095, 0.050, 0.075) | |
| `foot_L` | shin_L | (0.095, 0.050, 0.075) → (0.119, −0.079, 0.025) | |
| `toes_L` | foot_L | (0.119, −0.079, 0.025) → (0.128, −0.151, 0.010) | Kinematic |

**Joint axes are exported as world vectors** (flexion axis, sign, abduction axis, twist axis at rest) in `rig.json`; the Godot ragdoll builder converts them into each `PhysicalBone3D` joint frame. Nobody hand-codes bone roll assumptions.

#### 3.1.2 Physical bodies (20) and joints

Masses are Winter/Dempster fractions of 75 kg [RB §7.2]; the thorax is split, and clavicles take 0.75 kg each from `upper_chest` to keep adjacent mass ratios ≤ 10:1 [RB §4.10].

| Body | Mass (kg) | Shape (E) | Joint to parent | Live limits (°) | Dead limits (°) | Torque cap (N·m) |
|---|---|---|---|---|---|---|
| `hips` | 10.65 | box 0.33 × 0.20 × 0.16 | — | — | — | — |
| `spine` | 10.4 | box 0.30 × 0.20 × 0.18 | 6DOF | flex 40, ext 15, lat 15, rot 15 | +10 % | 200–300 |
| `chest` | 8.6 | box 0.32 × 0.22 × 0.15 | 6DOF | flex 30, ext 10, lat 15, rot 20 | +10 % | 150 (E) |
| `upper_chest` | 6.1 | box 0.34 × 0.20 × 0.14 | 6DOF | flex 15, ext 10, lat 10, rot 10 | +10 % | 100 (E) |
| `neck` | 1.1 | capsule r 0.055, h 0.13 | 6DOF | 60 % of neck ROM: flex 28, ext 33, lat 27, rot 35 | flex 42, ext 51, rot 45 | 20–40 |
| `head` | 5.0 | capsule r 0.080, h 0.22 | 6DOF | 40 % of ROM (rot 50 %): flex 19, ext 22, lat 18, rot 35 | flex 28, ext 34, rot 45 | 20–40 |
| `clavicle_L/R` | 0.75 | capsule r 0.025, h 0.15 | 6DOF | elev 30, depr 10, protr/retr 15 | +10 % | 40 (E) |
| `upper_arm_L/R` | 2.1 | capsule r 0.045, h 0.29 | cone (swing 100, twist ±70) | | swing 110 | 60–100 |
| `forearm_L/R` | 1.2 | capsule r 0.038, h 0.27 | hinge | 0–145 (−5) | −10…155 | 50–80 |
| `hand_L/R` | 0.45 | box 0.087 × 0.03 × 0.19 | 6DOF | flex 75, ext 65, rad 20, uln 30, twist ±80 (forearm rotation folded in) | +10 % | 8–15 |
| `thigh_L/R` | 7.5 | capsule r 0.075, h 0.43 | 6DOF (asymmetric) | flex 120, ext 25, abd 45, add 30, rot ±45 | +10 % | 200–300 |
| `shin_L/R` | 3.49 | capsule r 0.050, h 0.42 | hinge | 0–135 | −10…158 | 200–250 |
| `foot_L/R` | 1.09 | box 0.10 × 0.07 × 0.26 | 6DOF | dorsi 20, plantar 50, inv 30, ev 20 | +10 % | 100–150 |

Neck ROM totals flex 45–50, ext 45–60, rot 60–80 (dead 70/85/90) split across the two joints [RB §4.10]. Friction 0.6–0.9 skin/cloth, 0.1–0.25 on wet blood (material swap on the floor splat), restitution 0.1–0.3 [RB §4.10].

#### 3.1.3 Control modes

| Mode | Skeleton driving | Physical bones |
|---|---|---|
| Standing | AnimationTree (idle/guard/cower poses) + ClutchIK + BreathModifier + EyeModifier | Not simulating (kinematic follow; hitboxes valid) |
| Flinch | as Standing | `physical_bones_start_simulation([hit bone, parent, children])` [T3], simulator `influence` 0.3–0.6 → 0 over 0.2–0.5 s, then stop [RB §4.10] |
| Collapse / down / dead | Simulator influence 1.0; PD targets from behaviours | All 20 simulating; velocities initialised from the last two animated poses (finite difference) so the fall inherits motion |
| Rigor | as dead | Per joint group, joint limits clamp around the current pose as `s(t)` rises [RB §6.6] |

PD per body in `_integrate_forces(state)` [T4]: `τ = clamp_dir(kp·θ_err − kd·ω_rel)` with `kp = I·ω²`, `kd = 2ζIω` and ω/ζ per tone state [RB §4.10]; **the clamp is separate for the positive and negative direction of each joint axis** (flexor cap vs extensor cap, §3.2). The controller computes all torques once per tick in `_physics_process` into a `PackedVector3Array`; each body applies its own torque minus its children's reactions. Stability: ω·Δt ≤ 0.5.

### 3.2 Paralysis: spinal level, brainstem and hemisphere → which joints go limp

**Level convention.** The hit gives a *lesioned cord segment* X (vertebra → segment offsets [RB §4.6]: cervical +1, upper thoracic +2, lower thoracic +3, T12 → L3–S1, L1 → conus S2–S5, L2–S2 → cauda equina roots). The **neurological level** (the bible's "Level (complete)" rows) is the lowest intact segment = X − 1. Complete lesion → every segment ≥ X loses voluntary control and, in spinal shock, all tone and reflexes (flaccid, no withdrawal) [RB §4.6].

**Myotome map** (joint axis direction → innervating segments with weights). ISNCSCI key muscles (in bold) from R04 §6.2 [C32]; the remaining assignments are standard neuro-anatomy, **K** (QA re-check).

| Body / joint | Direction | Main muscles | Segment weights |
|---|---|---|---|
| neck + head | flexion | SCM, longus colli/capitis | XI 0.4, C1–C3 0.4, C4–C6 0.2 |
| | extension | trapezius, splenius, semispinalis | XI 0.3, C1–C4 0.4, C5–C8 0.3 |
| | rotation, lateral flexion | SCM, splenius, scalenes | XI 0.4, C1–C4 0.4, C5–C8 0.2 |
| clavicle | elevation (shrug) | trapezius, levator scapulae | XI 0.5, C3–C5 0.5 |
| | protraction / depression | serratus anterior, pectoralis minor | C5–C7 0.6, C8–T1 0.4 |
| upper_arm (shoulder) | abduction, flexion | deltoid, supraspinatus, clavicular pectoralis | C5 0.6, C6 0.4 |
| | extension, adduction | latissimus, sternal pectoralis, teres major | C6 0.3, C7 0.4, C8 0.3 |
| | rotation | rotator cuff | C5 0.5, C6 0.5 |
| forearm (elbow) | flexion | **biceps/brachialis (C5 key)**, brachioradialis | C5 0.6, C6 0.4 |
| | extension | **triceps (C7 key)** | C6 0.2, C7 0.6, C8 0.2 |
| forearm_twist (kinematic) | supination / pronation | supinator, biceps / pronator teres | C6 / C6–C7 |
| hand (wrist) | extension | **ECRL/ECRB (C6 key)** | C6 0.7, C7 0.3 |
| | flexion | FCR, FCU | C7 0.6, C8 0.4 |
| fingers, thumb (kinematic) | grip | **FDP (C8 key)**, intrinsics (**T1 key**) | C8 0.7, T1 0.3 |
| | extension | EDC | C7 |
| upper_chest ↔ chest ↔ spine | flexion | intercostals T1–T11, rectus abdominis T7–T12, obliques T7–L1 | upper_chest T1–T6; chest T6–T12; spine T10–L1 (equal weights) |
| | extension | erector spinae (dorsal rami, each level) | upper_chest T1–T8; chest T6–L2; spine T10–L5 |
| | lateral, rotation | obliques, quadratus lumborum | chest T7–L1; spine T12–L3 |
| thigh (hip) | flexion | **iliopsoas (L2 key)**, rectus femoris | L1 0.2, L2 0.5, L3 0.3 |
| | extension | gluteus maximus, hamstrings | L5 0.3, S1 0.5, S2 0.2 |
| | abduction, internal rotation | gluteus medius/minimus | L4 0.3, L5 0.5, S1 0.2 |
| | adduction | adductors | L2 0.3, L3 0.5, L4 0.2 |
| | external rotation | piriformis, obturators | L5 0.3, S1 0.5, S2 0.2 |
| shin (knee) | extension | **quadriceps (L3 key)** | L2 0.2, L3 0.5, L4 0.3 |
| | flexion | hamstrings | L5 0.3, S1 0.5, S2 0.2 |
| foot (ankle) | dorsiflexion | **tibialis anterior (L4 key)** | L4 0.7, L5 0.3 |
| | plantarflexion | **gastrocnemius/soleus (S1 key)** | S1 0.7, S2 0.3 |
| | inversion / eversion | tibialis posterior / peronei | L4–L5 / L5–S1 |
| toes (kinematic) | extension | **EHL (L5 key)** | L5 |
| Breathing | diaphragm C3–C5 (C4 main), intercostals T1–T11, abdominals T6–L1 | — | → `resp_capacity` table [RB §4.6] |

`XI` is the accessory nerve (cranial): it survives any cord lesion and is lost only with medullary damage, which is why a C1–C3 victim can still shrug and strain the neck weakly [RB §4.6].

**Per-axis strength** each physiology tick:
```
seg_ok[s]      = cord map: 1 above the lesion, 0 at/below (complete); syndrome rules for incomplete:
                 Brown-Séquard: ipsilateral motor 0 below; contralateral motor 1 (pain loss contralateral, §sensation)
                 central cord: C5–T1 × 0.2–0.4, L1–S2 × 0.7–0.9 ; anterior cord: motor 0 below ; cauda: per root, asymmetric
                 cord concussion: all 0, restore at t_recover (2 min–48 h, default 10 min) [RB §4.6]
brain_ok[side] = contralateral motor strip/capsule damage (visible/full thresholds [RB §4.5]) → arm, leg, lower face
strength(axis, dir) = Σ w_s · seg_ok[s] · brain_ok[side of limb]            (0–1)
cap(axis, dir)      = cap_joint · tone_cap_mult(tone_state) · strength(axis, dir)
```
Consequences the table produces without special cases: C5 → elbows flex, hands limp (flexors present, triceps absent); C6 → + wrist extension; T8 → legs fold, arms brace and drag; L4 root → foot drop; right motor-strip lesion → left arm/leg flaccid, falls to the left [RB §4.5].

**Brainstem and consciousness override** [RB §4.2 resolver]: medulla/lower pons destroyed → all tone 0 at ≤ 0.1 s (cut strings); midbrain → decerebrate episodes; bilateral hemisphere/thalamus → decorticate; ventral pons only (p ≤ 0.05) → locked-in (all limbs 0, eyes vertical + blink only). **Sensation** uses the per-vertex dermatome code (§5.5): below a complete level `sensory_intact = 0` → no pain, no withdrawal, no flinch [RB §4.2].

### Simulation parameters (rig, ragdoll, paralysis)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `deform_bones` | 39 | — | §3.1.1 | G |
| `ragdoll_bodies` | 20 | — | §3.1.2 | [RB §8.1] G |
| `influences_per_vertex` | 4 | — | `export_influence_nb` | [T10] V |
| `pd_omega / zeta` | per tone state (voluntary 10–12, arms 6–8 …) | rad/s / — | ω·Δt ≤ 0.5 | [RB §4.10] E |
| `torque_caps` | table §3.1.2 | N·m | Split flexor/extensor | [RB §4.10] C |
| `flinch_influence` | 0.3–0.6 → 0 over 0.2–0.5 s | — | Partial ragdoll | [RB §4.10] |
| `mass_ratio_max` | 10:1 | — | Clavicles 0.75 kg | [RB §4.10] |
| `myotome_map` | table §3.2 | weights | ISNCSCI keys C; rest K | R04 §6.2, K |
| `cord_offset` | C +1, upper T +2, lower T +3, T12 → L3–S1, L1 → S2–S5 | segments | Lesioned segment X, neurological level X − 1 | [RB §4.6] C |
| `tone_loss_time` | ≤ 0.1 off-switch; 0.5–2 faint/bleed | s | | [RB §4.10] |

### Visual/behavioural checklist (rig, ragdoll, paralysis)
- C1–C3: instant flaccid collapse of everything below the head; head and neck strain weakly; eyes alive [RB §4.6].
- C5: arms fold at the elbows with limp hands; T8: legs fold instantly, arms break the fall, the subject drags itself on the elbows; L4 root: one foot slaps [RB §4.6].
- Right hemisphere motor wound: the left arm hangs, the left leg buckles, the subject falls to the left, eyes and head turn right [RB §4.5].
- No joint ever bends past its dead limit; the neck never exceeds 70° flexion / 85° extension / 90° rotation even when dead.
- Paralysed limbs never flinch when cut or burned.

---

### 3.3 Layered gore on skinned meshes

#### 3.3.1 Principle

Godot skins in a compute pre-pass, so a spatial shader sees only posed vertices [RB §1.2]. Every layer therefore carries its **bind-pose position** in `CUSTOM0.xyz` (float32) and its segment ID in `CUSTOM0.w`; all wounds, brushes, cracks and reveal tests live in that rest space. Because every layer is skinned by the same analytic weight function (D8), a rest-space wound volume cuts skin, fat wall, muscle shell, bone and organ consistently in any pose.

#### 3.3.2 Pipeline

| Step | Owner | What |
|---|---|---|
| 1 | Blender (B6) | Every mesh exported in the A-pose bind with identity object transforms, parented to `GB_Armature`, placeholder materials named per §5.6 |
| 2 | Import (G0) | `subject_post_import.gd`: for every mesh surface, `CUSTOM0 = (ARRAY_VERTEX.xyz, segment)` as `Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT` [T5]; attributes uncompressed (compressed positions are RGBA16UNORM [T5]); materials swapped by name; inner meshes hidden, `cast_shadow = OFF`, visual layer 3. **Runtime fallback**: the same routine runs once in `_ready` if the imported mesh lacks CUSTOM0 (≤ 40 ms total, E) |
| 3 | WoundStore (G3) | Packs records into a `RGBA32F` data texture (5 texels per wound, §3.3.3) and a `Texture3D` lookup grid (RGBA8, 4 indices per cell); one set per subject, shared by all its ShaderMaterials |
| 4 | Shaders (G3) | All subject shaders include `wound_sdf.gdshaderinc` with a `LAYER` constant (skin, cloth, fat wall, muscle, bone, organ, brain) that selects the per-layer radius |
| 5 | Open wound (G3) | When a wound needs a real hole (§3.3.4), its surface switches to the discard variant, a skinned **wound-wall mesh** is generated, and RevealManager shows the inner layers within 5–10 cm |
| 6 | Inner meshes (G3) | Closed inner meshes render back faces (`cull_disabled`, `FRONT_FACING == false`) as cut interior tissue (§3.3.6) |
| 7 | Painter (G3) | Compute brushes write blood film, bruise, burn dose, soot/stipple, abrasion into the head, body and shorts atlases [RB §8.3] |

#### 3.3.3 GPU wound record (5 × vec4 per wound, RGBA32F, 320 × 1 texels for 64 wounds)

| Texel | x | y | z | w |
|---|---|---|---|---|
| T0 | p0.x | p0.y | p0.z | r0 (skin radius at entry, m) |
| T1 | p1.x | p1.y | p1.z | r1 (far-end radius) |
| T2 | u.x | u.y | u.z (unit: slab long axis, or shooter-side direction for collar eccentricity) | aux (slab gape half-width, or ellipse major/minor) |
| T3 | r_muscle (m) | r_bone_outer (m) | bone inner-cone ratio (1.3–2.0) | r_organ (m) |
| T4 | `floatBitsToUint` flags: bits 0–3 shape {round_cone, capsule, ellipsoid, slab, stellate, burst}, 4 open, 5–8 margin {none, collar, contact soot/sear, lacerated/abraded, incised, burn}, 9–15 layer mask, 16–31 seed | collar width (m) | t_created (sim minutes) | exit/ray params (count + rotation packed) |

All radii are sampled on the CPU from the bible's per-weapon ranges [RB §2]; the shader never invents sizes. The GPU noise used for ragged outlines is an integer hash with a matching GDScript implementation in `wound_math.gd` (the wall-mesh generator must reproduce the same outline).

**Lookup grid**: A-pose rest bounds (Godot) x −0.60…+0.60 (fingertips at |x| 0.553), y −0.02…+1.82, z −0.17…+0.17 (toe tips +0.151, back −0.14), plus one cell of margin → 50 × 75 × 16 cells of 2.5 cm, RGBA8 (index + 1, 0 = empty), ≈ 240 KB; B6 writes the measured bounds into `manifest.json`. A cell keeps the 4 largest wounds; co-located pellet tracks at ≤ 1 m merge before insertion [RB §8.3]. Beyond 64 wounds the oldest closed ones retire into the paint atlas.

#### 3.3.4 Three rendering tiers

| Tier | When | How | Cost |
|---|---|---|---|
| a. Paint | Every mark (blood film, soot, stippling, collar tint, bruise, burn, abrasion) | Atlas sample in every skin/cloth shader; Beer–Lambert blood film with μa arterial (0.4, 28, 34)/mm and deoxygenated (3.0, 26, 50)/mm [RB §3.10] | ~0 |
| b. Analytic cavity | Closed holes ≤ 12 mm Ø: 9 mm entrances, stab slits, pellet holes, narrow slashes | No `discard`; view ray vs cone/slab of depth 20–40 mm in tangent space; wall banded by the tissue-depth map (dermis `#EAD2C8`, fat `#F2D16B`, muscle `#9B2F2B`, bone `#E9DFCC`), dark blood fill at the bottom [RB §7.6] | ≤ 4 SDF + 1 intersection per fragment in wound cells, ~0.1–0.2 ms at 40 % screen on a 1660 [RB §8.1] |
| c. Real hole | r > 6 mm open wounds, exits (10–30 mm head), gaping slashes wider than 12 mm, shotgun ≤ 1 m, bursts, burned-through tissue | Surface switches to the **discard variant**; wound-wall mesh; inner layers revealed; back-face flesh `#3A0A0C` safety net [RB §8.1] | `discard` disables depth-prepass benefit for that surface only [RB §8.2], hence per-surface switching |

**Wound-wall mesh** (G3, GDScript, ≤ 2 ms per wound, max 16 live per subject): 32–48 outline points sampled from the same SDF outline (hash noise) in the tangent plane at the entry, projected onto the rest skin with rays against the rest proxy; rings at the skin surface, dermis/fat boundary, fat/muscle boundary and the muscle-shell depth (from the tissue-depth map), then along the track to r_muscle. Vertices take the bone indices/weights of the nearest skin vertex (outer ring) blending to the dominant bone of the track (inner rings); `CUSTOM0` = rest position; UV.y = depth for tissue banding; exit walls evert 1–4 mm [RB §2.1.2]. ~400 triangles per wound. Slash walls follow the lens outline from `gape_max = L·G(θ)·f_depth·f_region` with the tension map (bible §2.3.1) baked as a tangent-space vector attribute in the atlas (B1).

#### 3.3.5 Bones, skull and fractures

- **Holes in bone** use the same SDF on the bone shell (outer + inner surfaces): a round cone with `r_bone_outer = 0.5·Ø·U(1.0, 1.2)` and inner ratio 1.3–2.0 produces the inward bevel automatically at the entrance and the outward bevel at the exit; the gap between tables shows diploë `#A4574A` through the back-face rule [RB §2.1.2, §7.3]. No bevel where bone < 4 mm.
- **Linear fractures**: 0–4 radial rays of 0–80 mm per handgun hole (Puppe termination p 0.95 computed on the CPU when rays are generated), stored as rest-space segments in a 128 × 2 `RGBA32F` crack buffer; the bone shader draws them as dark lines with a groove normal; paint adds haemorrhage along them [RB §2.1.3].
- **Depressed fractures** (hammer): stamped face-shaped SDF (round 25–32 mm or square) with terraced variant; fragments driven in 3–10 mm per blow [RB §2.5].
- **Pre-fractured variants** (Blender B3): skull vault burst ×3 (left, right, top exit direction; 20–80 Voronoi fragments), femur/tibia/humerus/radius-ulna per side as `simple` (one break; transverse or oblique by rotating the break plane at swap time) and `comminuted` (butterfly plus 8–20 fragments); ribs break as crack lines plus a 1–3 mm kink of the rib piece (no variant). At runtime the intact piece is hidden (vertex collapse by piece ID) and the variant shown; fragments ≥ 20 mm that leave become Jolt debris (≤ 48 active) and freeze into MultiMesh when asleep [RB §8.4].
- **Shotgun head burst** (E_dep ≥ 500–700 J [RB §2.2.3]): choose the variant nearest the exit direction, eject 20–60 % of fragments, discard the scalp inside a stellate burst SDF with 3–8 radial flaps (v1: flap walls as wound-wall rings everted 50–150 mm), discard brain inside the ejected fraction, spawn brain clumps; the heart keeps pumping from the defect for 1–10 min.

#### 3.3.6 Organs, brain and cut interiors

- Every closed inner mesh draws its back faces as its **interior**: myocardium `#7B2626` with dark chamber blood, lung `#A04A55` with froth sparkle, liver `#7A2E23`, spleen `#5E2433`, kidney cortex-over-medulla gradient, brain white matter `#E6DACA` under grey `#B79C94`, bone marrow red `#B5524A` (flat bones) or yellow `#E4C36A` (shafts) [RB §7.3–7.5]. A discard hole in an organ therefore reads as a solid cut surface.
- **Organ states** by blend shapes (`heart_systole` at the simulated HR, `lung_inhale_L/R` at RR × tidal volume, `lung_collapse_L/R` for pneumothorax, `diaphragm_inhale`) and instance uniforms (VF shiver 4–8 Hz noise, ischaemic dusky patch, haemorrhagic rim around tracks 5–20 mm) [RB §4.4, §8.1].
- **Brain regions**: a 64³ label grid over the brain bounds (≈ 2.9 mm voxels, R = region ID) exported as a lossless PNG slice atlas; the anatomy query counts voxels within the destruction radius (18 mm handgun) along the track → `damage = destroyed voxels / region voxels` for each of the bible's regions [RB §4.1].

#### 3.3.7 Painting on three atlases

| Atlas | Size | Texel | Channels | Memory |
|---|---|---|---|---|
| Head `blood_state` / `tissue_state` | 2,048² RGBA16F / RGBA8 | 0.24 mm | film mm, deposit min, dilution/serum, crust / bruise, burn dose (log-encoded), soot/stipple, abrasion | 33.6 + 16.8 MB |
| Body `blood_state` / `tissue_state` | 2,048² RGBA16F / RGBA8 | 0.84 mm | same | 33.6 + 16.8 MB |
| Shorts `blood_state` / `tissue_state` | 1,024² | ~1.2 mm | film (wicked ×2–4 area), deposit, char/hole, — | 8.4 + 4.2 MB |
| Livor | 512² RG8 per body/head | — | mobile livor, fixed livor (≤ 1 Hz compute, uses the dominant-bone map) | 1 MB |

Brushes are 3D in rest space and read the **position maps** baked by Blender (segment-relative half-float EXR; the segment origin table is in `manifest.json`, giving ≤ 0.25–0.5 mm quantisation, cf. [RB §1.2] precision rule) and normal maps. Timestamps, not ages, are stored [RB §3.11].

### Simulation parameters (layered gore)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `custom0_format` | RGBA32F; w = segment | — | Half float gives ~1 mm steps | [RB §1.2] V, [T5] V |
| `wound_texels` | 5 per wound, 64 wounds | — | §3.3.3 | G |
| `wound_grid` | 50 × 75 × 16 @ 2.5 cm, RGBA8 | cells | ~240 KB | E |
| `cavity_max_d` | 12 | mm | Tier b ↔ c | [RB §8.4] G |
| `layer_reveal_radius` | 5–10 | cm | | [RB §8.4] G |
| `wall_points / rings / tris` | 32–48 / 4–6 / ~400 | — | Per open wound | E |
| `wound_walls_max` | 16 | per subject | Oldest merged into paint | G |
| `crack_buffer` | 128 segments | — | Skull and bones | G |
| `brain_label_grid` | 64³ | voxels | ~2.9 mm | E |
| `backface_flesh` | `#3A0A0C`, roughness 0.25 | — | Safety net | [RB §8.1] G |
| `atlas_head / body / shorts` | 2,048² / 2,048² / 1,024² | texels | | [RB §8.3] |

### Visual/behavioural checklist (layered gore)
- A distant 9 mm chest entrance is a 3.3–5.6 mm hole with a 1.6–2.4 mm collar; the player sees a short way in; walls go pink-white, yellow, dark red with depth [RB §9 #1].
- A shotgun wound at 1 m is a real 3–4 cm hole showing muscle and rib, casting a correct shadow; never an empty shell.
- A skull entrance shows a neat outer-table hole and a wider inner cone; exits bevel outward; 0–4 cracks [RB §9 #9–10].
- An opened organ looks solid and wet inside; the heart beats at the simulated rate and stops at death; a collapsed lung is visibly smaller.
- Flexing an elbow or knee through its full range never moves a wound, a wall mesh or a paint mark relative to the tissue.

---

### 3.4 Vessel network: authoring, export and bleeding

#### 3.4.1 Authoring in Blender (B5)

1. `gb_data/vessels.py` holds one row per vessel from [RB §3.3] (ID, name, kind E/M/V, Ø default and range, rest flow, parent, waypoints (left side), landmarks/depth text, initial bleed, LOC/death, self-stop, compressibility) plus **additions (K, QA re-check)**: intracranial ICA (4 mm), MCA M1 (3), ACA A1 (2), PCA (2); superior sagittal sinus (8–10, triangular), transverse (8) and sigmoid (7) sinuses; superior/inferior epigastric (2.5); lateral thoracic (2); subscapular (4); profunda brachii (2.5); superior (5) and inferior (4) gluteal; lumbar arteries (2–3, 4 pairs); axillary vein (10–12); brachial veins (paired 3–5); small saphenous (3); popliteal and tibial veins (4–8); facial (3), retromandibular (4) and superficial temporal (2) veins; azygos (8–10); splenic (8) and superior mesenteric (10) veins. Main nerves as data-only curves: brachial plexus cords, median, ulnar, radial (spiral groove), femoral, sciatic (→ deficits, v1 data only).
2. `vascular.py`: per segment and side — Catmull-Rom through the waypoints (`gore_head.anatomy.catmull`, 8 samples per span), arc-length resampling at `min(10 mm, 2·Ø)`, radius tapering between listed diameters (e.g. A21 21 → 18 mm), mirrored for the right side (`side: "L"|"R"|"mid"`; SVC, IVC, azygos, brachiocephalic trunk and right-only branches are explicit rows).
3. Tube meshes: 12 sides for Ø ≥ 15 mm, 8 for 6–15, 6 for 3–6, 4 for 1.5–3, none below 1.5 mm (data only). End caps. Merged into `GB_Vessels_Art` and `GB_Vessels_Ven`; UV2 = (vessel index, t along the segment).
4. Weights from the shared weight function; validation: every centreline point inside the skin by at least 0.5 × its listed depth, inside bone canals where the bible says so (vertebral artery), and no arterial tube intersecting a bone mesh except in canals.
5. Capillary beds (brain, coronary, kidneys, liver, skeletal muscle by limb, skin by region, bone, spleen, scalp) with R_bed targets [RB §3.3] go into `vessels.json` `beds`.

#### 3.4.2 Runtime (G1 + G4)

- `VesselGraph` loads `vessels.json`; each polyline piece becomes a `CapsuleShape3D` in the anatomy space (layer VESSEL). The hit rule is the bible's: injured if `d < r_v + r_track`, transected if `d < r_track − 0.5·r_v`, else side laceration; cavity tear roll p 0.1–0.3 [RB §2.0].
- A `BleedSite` is created per injured vessel (and per tissue bed for ooze): `{site_id, wound_id, vessel_id|bed, type, A0, spasm, clot, compress, tissue_factor, outlet, p_rest, bone}`. `outlet` = `external` (the track reaches skin) or a compartment (pericardium, pleura L/R, peritoneum, retroperitoneum, cranium, thigh L/R, subgaleal, orbit); an external leak fraction applies for narrow tracks (tissue_factor 0.15–0.3) [RB §3.4].
- Each tick: Δh from the **current pose** (site rest position → world through its bone; right atrium through `chest`) with 0.78 mmHg/cm; the bible's orifice/supply limits, spasm, clot, critical closing pressure, shunt solve, stump pressure for distal ends [RB §3.2, §3.4].
- Output per site `FlowState {q_ml_min, p_local_mmHg, pulsatile, jet_ok, sat, regime}` → VfxDirector: regime ooze < 1, drip 1–15, stream 15–300 mL/min (venous), **jet when arterial, open to air and P_local ≥ 25–30 mmHg** [RB §3.5]; jets pulse at the simulated HR with the per-vessel pulse delay (carotid 90–140 ms, femoral 150–220, radial 170–250) [RB §3.5].

#### 3.4.3 Surface blood and pools (G4)

Rivulet agents on the rest mesh [RB §3.11]: adjacency built at load from the LOD0 arrays; agents in a `WorkerThreadPool` task at 30 Hz; residue painted as capsule strokes. Floor: 2,048² RG16F splat map over 8 × 8 m with cellular spread toward the analytic floor height (1 % fall), gel after 5–15 min [RB §3.11].

#### 3.4.4 Hero drops without per-frame ray casts

The room is a set of known planes and boxes. At launch each hero drop solves its flight in closed form with a linear-drag model (`v(t) = v_T + (v0 − v_T)·e^(−t/τ)`, τ = v_term/g ≈ 0.8 s for the bible's 8 m/s terminal velocity [RB §3.11]) and finds the first room-plane crossing with 3–4 Newton steps; it then casts **one ray** along the launch → landing chord (a second chord for arcs longer than 1 m) against dynamic objects (subject, debris, props). The earliest hit gives the landing time and point; the drop is drawn along the analytic path and lands exactly then: wall → decal (stain 3–5.5 × drop Ø, L/W = 1/sin α), floor → splat map, subject → paint [RB §3.11]. Cost: ~10–20 µs per drop at launch (≤ 1 ms for a 60-drop spatter event), zero per frame.

### Simulation parameters (vessels and bleeding)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `vessel_segments` | ~140 (L/R expanded) | — | Bible + additions (K) | [RB §3.3], K |
| `tube_sides` | 12 / 8 / 6 / 4 / 0 | — | Ø ≥ 15 / 6–15 / 3–6 / 1.5–3 / < 1.5 mm | G |
| `resample_step` | min(10 mm, 2·Ø) | mm | Centreline | G |
| `hit_rule` | d < r_v + r_t injured; d < r_t − 0.5 r_v transected | — | | [RB §2.0] G |
| `cavity_tear_p` | 0.1–0.3 | p | Within cavity radius | [RB §2.0] G |
| `hydrostatic` | 0.78 | mmHg/cm | From current pose | [RB §1.1] V |
| `jet_gate` | arterial, open, P_local ≥ 25–30 | mmHg | Pressure-gated | [RB §3.5] |
| `regime_edges` | 1 / 15 / 300 | mL/min | Ooze/drip/stream (venous) | [RB §3.5], R06 |
| `pool_thickness / gel` | 2.5 / 5–15 min | mm | | [RB §3.11] V |
| `hero_drop_rays` | 1 (2 for arcs > 1 m) | per drop | At launch only | E |
| `hero_drop_tau` | 0.8 | s | v_term / g, linear drag | [RB §3.11] E |

### Visual/behavioural checklist (vessels and bleeding)
- A track that misses every named vessel bleeds only as tissue ooze; a track through the femoral triangle jets. Players who know anatomy can predict it [RB §8.3].
- The jet starts from the lumen position, pulses a fraction of a second after each heartbeat, weakens and quickens as shock deepens, and stops within 1–2 beats of arrest [RB §9 #21–22].
- Raising a bleeding forearm above the heart nearly stops venous flow; a hanging limb bleeds more [RB §9 #23].
- Small trunk wounds bleed little outside while the chest or abdomen fills [RB §9 #27].

---

### 3.5 Reveal and X-ray

- **RevealManager** keeps, per inner mesh piece (muscle-shell surface, bone piece ID, organ ID, vessel class, brain, cord), the rest-space AABB. A piece becomes visible when any **open** wound SDF lies within `layer_reveal_radius` of it; pieces inside one mesh are shown or hidden by an instance-uniform bitmask that collapses hidden vertices in `vertex()` [RB §8.1] (no discard cost). Inner meshes never cast shadows.
- **X-ray mode** (player toggle or kill-cam): skin/cloth write stencil ref 1 in the opaque pass; X-ray variants of skeleton, organs, vessels, cord and the rest-space bullet track (glowing capsule) draw in the transparent pass with `depth_test_disabled`, stencil `read`, `compare_equal` (4.5 spellings) [RB §8.2]; bones emissive `#C8D4E0`, fractures brighter, severed vessels red; skin swaps to a Fresnel rim (α 0.1–0.25). Time scale 0.05–0.1 for the bullet, 1.5–3 s window [RB §8.1, R06 §11].

### Simulation parameters (reveal and X-ray)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `reveal_radius` | 5–10 | cm | Open wounds only | [RB §8.4] G |
| `xray_stencil_ref` | 1 | — | Write opaque, read transparent | [RB §8.2] V |
| `xray_skin_alpha` | 0.1–0.25 | — | Fresnel rim | R06 §11 G |
| `xray_time_scale / duration` | 0.05–0.1 / 1.5–3 s | — | | R06 §11 G |
| `xray_cost` | 0.5–1.5 | ms (1660) | One subject | R06 §11 E |

### Visual/behavioural checklist (reveal and X-ray)
- Through a shotgun wound to the chest the player sees muscle, then ribs, then lung; through a skull exit, bone edge and brain. Nothing is visible through intact skin.
- In X-ray the skeleton and organs appear only inside the body outline; the track is a thin bright line; fractures match the bible patterns (no over-shattering).

---

### 3.6 Eyes and face

| Part | Implementation | Driven by |
|---|---|---|
| Eyeball | Head project's eye mesh (r 12 mm, cornea bulge); `eye.gdshader`: refract the view ray through the cornea sphere (IOR 1.376) onto the iris plane (y_local −0.0101), polar iris lookup from a baked iris texture with pupil remap, limbal darkening, sclera vein texture, clearcoat for the tear film | `pupil_mm`, `gloss`, `corneal_opacity`, `dry_band`, `tache_noire`, `subconj`, `petechiae`, `hyphaema`, `conj_pallor`, `lid_up_deg`, `lid_lo_deg`, `iop_soft` (≤ 16 instance uniforms [RB §5]) |
| Lids | `lid_upper_*`, `lid_lower_*` bones rotating about the eye centre; aperture mm ↔ angle table measured in B2 | EyeModifier: blink model (Poisson 12–20/min, 250–400 ms), fear 11–12 mm, shock 5–8 mm, death drop 2–4 mm over 1–3 s, never blinks shut [RB §5] |
| Gaze | `eye_*` bone rotations set directly (not LookAtModifier3D) so saccade timing is exact: 21 + 2.2 ms/°, fixations 200–400 ms, microsaccades; doll's-eye counter-rotation gain 1 (unconscious, brainstem intact) or 0 (dead) | EyeModifier |
| Tearline, occlusion | Thin wet strip along the lower lid margin; transparent occlusion shell darkening the eyeball near the lids | `tear_amount`, lid angles |
| Face | 24 head blend shapes (`AU01/02/04/06/07/09/10/12/15/20_L/R`, `mouth_slack_L/R`, `swell_periorbital_L/R`) + `jaw` and `tongue` bones | FaceController: pain AU4+6/7+9/10+43, fear AU1+2+4+5+7+20+26, central palsy (lower face only), peripheral palsy, jaw drop 10–30 mm within 5–30 s at death [RB §5.6] |
| Skin state | Instance uniforms `pallor`, `cyanosis`, `mottling`, `sweat`, `flush_level` (dermatome index below which neurogenic flush shows), plus the livor atlas | SkinState ≤ 1 Hz from physiology [RB §5.6, §6.4] |
| Pupil light reflex | Illuminance at each eye from the scene lights (point-to-light attenuation + ambient) and the penlight tool | latency 200–250 ms, constrict ~1 s, redilate 2–4 s [RB §5.2] |

### Simulation parameters (eyes and face)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `eye_instance_uniforms` | 12 of 16 | — | Room for 4 more | [RB §5] V |
| `iris_plane_y / cornea_ior` | −0.0101 / 1.376 | m / — | Head materials constants | `materials.py` |
| `face_blend_shapes` | 24 | — | Head mesh only | G |
| `blink / saccade / lid tables` | [RB §5] | — | | [RB §5] C |
| `jaw_drop` | 10–30 within 5–30 s | mm | Supine | [RB §5.6] C |

### Visual/behavioural checklist (eyes and face)
- Alive: blinks, saccades toward the player or the wound, pupils 3–4 mm narrowing within a quarter second of the penlight [RB §9 #41].
- At death the eyes stay open or half-open (sudden death 55/35/10 %), lids sag 2–4 mm, gaze settles 3–10° outward and never moves again [RB §9 #42].
- Turning a dead head moves the eyes with it; turning an unconscious living head leaves them lagging [RB §9 #44].
- Over forensic hours: gloss gone within ~1 h, haze from 1–2 h, tache noire at 3–6 h [RB §9 #45].

---

### 3.7 Hit pipeline and anatomy query without C++

| Stage | Engine call | GDScript work | Estimate (E) |
|---|---|---|---|
| Coarse bone hit | `PhysicsDirectSpaceState3D.intersect_ray` vs ragdoll shapes | — | 10–20 µs |
| Rest mapping | `Skeleton3D.get_bone_global_pose` / rest | 2 transforms | < 5 µs |
| Exact skin hit, exit search | `intersect_ray` in the private rest space (skin trimesh, face index enabled [RB §8.2]) × 2–4 | barycentrics, UV, codes from cached arrays | 30–80 µs |
| Anatomy candidates | **one** `intersect_shape` with a `CapsuleShape3D` (r = cavity radius) along the track, max 64 results | — | 20–60 µs |
| Exact classification | per candidate: analytic segment–capsule distance (vessels, cord), `intersect_ray` against that body only for bones/organ meshes, voxel walk in the brain grid | ≤ 64 candidates × ~10 µs | 0.3–0.7 ms |
| Morphology + records | tables and RNG | ~200 lines | 0.2–0.4 ms |
| Paint/VFX queueing | — | small | 0.1 ms |
| **Total pistol shot** | | | **≈ 0.7–1.4 ms (budget 2)** |

The private rest space is created with `PhysicsServer3D.space_create()` and made active; static bodies hold: skin/shorts trimeshes (LOD0 render geometry, rest pose), bone meshes (decimated, concave, ≤ 20k tris total), organ meshes, vessel and cord capsules, brainstem capsules; collision layers separate classes. **Spike in G0**: confirm that Jolt queries see bodies in a private space one physics frame after creation, and measure the costs above.

### Simulation parameters (hit pipeline)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hit_candidates_max` | 64 | — | `intersect_shape` max_results | E |
| `rest_space_tris` | skin+shorts ~78k, bones ≤ 20k | tris | Face index +~25 % memory | [RB §8.2] |

### Visual/behavioural checklist (hit pipeline)
- A shotgun volley at close range never hitches the frame (pellet tracks merged, work spread over ≤ 2 frames).

---

## 4. Budgets

### 4.1 Triangles and vertices (LOD0, subject)

| Mesh | Triangles | Visible | Notes |
|---|---|---|---|
| `GB_Head` (head + neck to the seam, lids, ears, lips, mouth lining) | 30,000 | always | Decimated from the 1.2 mm head; 24 blend shapes |
| `GB_Body` (5 surfaces: torso, arm_L, arm_R, leg_L, leg_R) | 44,000 | always | Hands 2k and feet 1.5k each included; 4 blend shapes |
| `GB_Shorts` | 4,000 | always | Solidified 1.2 mm |
| `GB_Eye_L/R` + `GB_EyeFX_L/R` (tearline, occlusion) | 5,000 | always | |
| `GB_Mouth` (teeth, gums, tongue) | 8,500 | always | |
| `GB_BrowLash` cards | 2,000 | always | Alpha scissor |
| **Outer total** | **93,500** | | ~52k skinned vertices |
| `GB_MuscleShell` (6 surfaces) | 24,000 | on reveal | |
| `GB_Skeleton` (intact) | 36,000 | on reveal / X-ray | Skull 12k, spine 6.5k, ribs 5k, pelvis 3k, limbs 8k, rest 1.5k |
| `GB_Brain` | 14,000 | on reveal / X-ray | Gyri in the normal map |
| `GB_Organs` | 22,000 | on reveal / X-ray | 6 blend shapes |
| `GB_Cord` | 3,000 | on reveal / X-ray | Cord, dura, cauda, roots |
| `GB_Vessels_Art` + `_Ven` | 14,000 | on reveal / X-ray | |
| Fracture variants | ≤ 60,000 | swapped in | Loaded, not drawn until used |
| Wound walls | ≤ 16 × 400 | generated | |
| **Worst visible subject** | **≈ 135,000** | | Bible reference 100–150k [RB §8.4] |

### 4.2 Textures (static, baked by Blender)

| Set | Maps | Size | Import | VRAM (with mips) |
|---|---|---|---|---|
| Head skin | albedo, normal, ORM + SSS mask | 2,048² each | BC7 sRGB / RGTC normal / BC7 linear | ~17 MB |
| Body skin | same | 2,048² | same | ~17 MB |
| Shorts | albedo, normal, ORM | 1,024² | same | ~4 MB |
| Eyes | iris (albedo + height), sclera veins | 512² / 1,024² | | ~2 MB |
| Mouth | teeth/gums/tongue | 1,024² | | ~4 MB |
| Skeleton | albedo, normal, ORM | 2,048² | | ~17 MB |
| Organs + brain | albedo, normal, ORM | 2,048² + 1,024² | | ~21 MB |
| Tileables | muscle fibre, fat lobule, bone cut, diploë, blood crust, cloth weave | 512² each (seamless) | | ~4 MB |
| Painter inputs | position map (EXR half, segment-relative), rest normal map, valid mask, tissue-depth map, tension map, dominant-bone map | 1,024² / 512² | **uncompressed / lossless** | ~30 MB |
| Room | tile, grout, epoxy, rubber, steel | 1,024²–2,048² | | ~20 MB |
| **Static total** | | | | **~136 MB** |
| Runtime atlases (§3.3.7) + floor splat 16.8 MB + particles/decals ~20 MB | | | | **~150 MB** |

### 4.3 Files and build

| Artifact | Budget | Notes |
|---|---|---|
| `GB_Subject.glb` | ≤ 40 MB | No images; morph targets dominate (head 24 × ~16k vertices ≈ 9 MB with normals) |
| Each 2,048² PNG | ≤ 12 MB | 8-bit; EXR only for position maps |
| `assets/generated/` total | ≤ 250 MB | Git-ignored except `manifest.json` (§5.7) |
| Full Blender build | ≤ 60 min on 4 cores (bakes dominate); incremental stages ≤ 10 min | Content-hash caching per stage |
| Exported game `.pck` | ≤ 1 GB | |

### 4.4 Frame budgets (target hardware; heavy-gore reference scene [RB §8.4])

| Item | Budget | Gate under lavapipe (automated) |
|---|---|---|
| GPU total | ≤ 13.5 ms GTX 1660 / ≤ 8 ms RTX 3060 at 1080p | Not gated here; real-hardware run at M2 and M4 |
| Draw calls (frame, incl. shadows) | ≤ 1,500; subject ≤ 60 | `RENDER_TOTAL_DRAW_CALLS_IN_FRAME` [T6] |
| Primitives per frame | ≤ 1.5 M | `RENDER_TOTAL_PRIMITIVES_IN_FRAME` [T6] |
| Visible subject triangles | ≤ 150k | custom monitor |
| Live GPU particles | ≤ 20k (1660) / 40k (3060) | custom monitor |
| Visible decals | ≤ 200 | custom monitor |
| Jets / drips+streams / agents | ≤ 6 / ≤ 20 / ≤ 24 | custom monitor |
| Debris active / frozen | ≤ 48 / ≤ 2,000 | `PHYSICS_3D_ACTIVE_OBJECTS` [T6] |
| Pipeline compilations while drawing | 0 during the scripted run | `PIPELINE_COMPILATIONS_DRAW` [T6] |
| Main-thread script time | ≤ 6 ms average, ≤ 10 ms worst frame (this machine) | `Time.get_ticks_usec` spans per system |
| Physics step | ≤ 1.5 ms | `TIME_PHYSICS_PROCESS` [T6] |
| Texture memory | ≤ 700 MB | `RENDER_TEXTURE_MEM_USED` [T6] |

### Simulation parameters (budgets)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `subject_tris_visible_max` | 150,000 | tris | | [RB §8.4] |
| `draw_calls_frame_max / subject_max` | 1,500 / 60 | — | | [RB §8.4] E |
| `gpu_budget_1660 / 3060` | 13.5 / 8 | ms | | [RB §8.4] G |
| `static_texture_vram` | ~136 | MB | | E |
| `runtime_atlas_vram` | ~115 | MB | Head + body + shorts + livor | E |
| `glb_max` | 40 | MB | | G |

### Visual/behavioural checklist (budgets)
- The heavy-gore reference scene keeps every count gate green on every CI run; a failing gate blocks the merge.
- On the GTX 1660, the governor only ever touches mist, spatter density, stain lifetime, decal distance, SSS taps, SSAO resolution and render scale — the subject looks identical.

---

## 5. Blender module contract: `blender/gore_body/`

### 5.1 Rules

- **Everything is generated by code.** Only `bpy` and numpy (both already installed for the head project). No downloaded meshes, images, HDRIs, add-ons or pip packages.
- Runs as `python3 build.py [--stage …]` (bpy 5.0.1) and `blender -b --python build.py -- [--stage …]` (5.x). Paths only relative to `gb_common.HERE`; the game output root is `gb_common.GAME_OUT = HERE/../../gore-game/assets/generated`.
- `blender/gore_head` is **imported read-only** (`sys.path` + `import anatomy as gh_anatomy`, `import materials as gh_materials`, `import gh_common as ghc`). A change there goes through its own `CONTRACT.md` and must keep its renders working.
- Deterministic: every random draw uses `numpy.random.default_rng(gb_common.SEEDS[name])`.
- Each module runs alone (`python3 skeleton.py`), accepts `--quick` (placeholder inputs, coarse resolution) and writes test renders `renders/<module>_*.png` (≤ 640 px, ≤ 48 samples, denoised; 4 cores are shared).
- Metres, body frame, left side authored and mirrored unless a row says `mid` or `R`.
- The build ends only with an **ARMATURE modifier** on each mesh: every other modifier is applied inside the build, because the glTF exporter's `export_apply` "prevents exporting shape keys" ([T10] `__init__.py` line 648–652).

### 5.2 Files and entry points

| File | Owner | Entry points | Produces |
|---|---|---|---|
| `CONTRACT.md` | B0 | — | This section, kept current |
| `gb_common.py` | B0 | `HERE`, `GAME_OUT`, `SEEDS`, `head_to_body(p)`, `b2g(v)`, `collections()`, `link(obj, col)`, `write_json(path, data, schema)`, `stage_cache(name, input_paths)`; stubs for `weights_at` (B6) and `seam_ring` (B2) | Shared helpers |
| `gb_data/landmarks.py, rig_table.py, vertebrae.py, ribs.py, organs.py, vessels.py, nerves.py, myotomes.py, dermatomes.py, tissue.py, segments.py` | B0 transcribes from the bible; B5 extends vessels/nerves | Python tables | Single source of anatomical numbers |
| `placeholder.py` | B0 | `build_placeholder() -> dict[str, Object]` | Capsule mannequin with **final** object, bone and material names (M0) |
| `body_skin.py` | B1 | `body_sdf(x, y, z)`, `skin_sdf(x, y, z)` (head ∪ body), `build_body_skin()`, `build_shorts(skin)`, `build_muscle_shell(skin)`, `paint_codes(obj)` | `GB_Body`, `GB_Body_HR`, `GB_Shorts`, `GB_MuscleShell` |
| `head_integration.py` | B2 | `seam_ring(n=160)`, `zip_to_ring(obj, ring)`, `build_head()`, `build_face_shapes(head)`, `build_eye_fx()`, `build_hair_cards()` | `GB_Head`, `GB_Head_HR`, `GB_Eye_L/R`, `GB_EyeFX_L/R`, `GB_Mouth`, `GB_BrowLash`; head skull/jaw/brain handed to B3/B4 |
| `skeleton.py` | B3 | `build_skeleton()`, `build_fracture_variants()`, `bone_capsules()` | `GB_Skeleton`, `GB_Frac_*`, capsule list |
| `viscera.py` | B4 | `build_organs()`, `organ_table()` | `GB_Organs`, organ data |
| `neuro.py` | B4 | `build_cord()`, `spine_table()`, `brain_labels()` | `GB_Cord`, `GB_Brain` (from the head), label grid |
| `vascular.py` | B5 | `build_vessels()`, `vessel_table()` | `GB_Vessels_Art/_Ven`, `GBV_*` curves, vessel data |
| `rig.py` | B6 | `build_armature()`, `weights_at(points) -> (idx[N,4], w[N,4])`, `skin_all(objs)`, `build_poses()`, `rig_table()` | `GB_Armature`, weights, actions |
| `uv.py` | B1 (body), B2 (head) | `mark_seams(obj, rules)`, `unwrap(obj, method='MINIMUM_STRETCH')`, `pack(obj, size, margin_px)` | UV maps |
| `lookdev.py`, `bake.py` | B7 | `build_materials()`, `bake_all(objs, out)`, `bake_tileables(out)`, `bake_painter_inputs(objs, out)` | Textures |
| `props.py` | B8 | `build_weapons()`, `build_room()` | Props |
| `export.py` | B6 | `export_subject(objs, out)`, `export_props(out)`, `write_manifest(out)` | glb, JSON |
| `verify.py` | B0 frame, every WP adds checks | `verify_all() -> dict`, non-zero exit on failure | Report on stdout |
| `build.py` | B0 | `--stage placeholder\|skin\|head\|skeleton\|viscera\|neuro\|vascular\|rig\|bake\|export\|props\|all`, `--quick`, `--no-bake`, `--render` | Orchestration |

UV unwrap methods verified in the Blender 5.0.0 source: `ANGLE_BASED`, `CONFORMAL`, `MINIMUM_STRETCH`; packing shape methods `CONCAVE/CONVEX/AABB`, margin methods `SCALED/ADD/FRACTION` [T12].

### 5.3 Collections and object names

```
GoreBody
├── GB_Rig        GB_Armature
├── GB_Outer      GB_Head, GB_Body, GB_Shorts, GB_Eye_L, GB_Eye_R, GB_EyeFX_L, GB_EyeFX_R, GB_Mouth, GB_BrowLash
├── GB_Inner      GB_MuscleShell, GB_Skeleton, GB_Brain, GB_Organs, GB_Cord, GB_Vessels_Art, GB_Vessels_Ven
├── GB_Variants   GB_Frac_Skull_L, GB_Frac_Skull_R, GB_Frac_Skull_T,
│                 GB_Frac_{Humerus,RadUlna,Femur,Tibia}_{L,R}_{simple,comminuted}
├── GB_LOD1       GB_Head_LOD1, GB_Body_LOD1               (fallback, D18)
├── GB_Data       GBV_<vessel>_<side> curves, GBN_<nerve>_<side> curves, GBL_<landmark> empties,
│                 GBH_<organ>_<n> hit-primitive empties, GBC_cord curve          (JSON only, not in the glb)
├── GB_HighRes    GB_Head_HR, GB_Body_HR, GB_Skeleton_HR, GB_Organs_HR, GB_Brain_HR   (bake sources only)
└── Stage         cameras and lights for test renders
```
Eyes and eye FX are one object per side because per-eye state is set through per-instance uniforms in Godot.

### 5.4 Space, bind pose, transforms

Body frame (§2.5); A-pose bind; `GB_Armature` at the origin with identity transform; every exported mesh has an identity transform, parent `GB_Armature` (parent type OBJECT) and one ARMATURE modifier. Head-project objects are moved by `(0, 0.020, 1.647)` and their transforms applied.

### 5.5 Per-vertex data

| Data | Blender name | Type | Meaning | Godot |
|---|---|---|---|---|
| UV map 0 | `atlas` | UV | Non-overlapping atlas, 16 px margin at 2,048² (`margin_method='FRACTION'`, 0.0078) | `UV` |
| UV map 1 | `gb_codes` | UV | Integer codes as floats (table below). **The exporter flips V (`v_gltf = 1 − v`)** [T10 `primitive_extract.py` 1419–1423], so Blender stores `1 − code_v` | `UV2` = (code_u, code_v) |
| Point attr | `gb_seg`, `gb_region`, `gb_derm`, `gb_piece` | INT | Source of the codes (kept in the .blend for checks) | — |
| Shape keys | §5.6 | — | | Blend shapes |
| Object custom props | `gb_layer` (str), `gb_schema` (int) | — | Exported with `export_extras=True` | Node meta `"extras"` [T9] |

| Mesh | UV2.x | UV2.y |
|---|---|---|
| Skin (`GB_Head`, `GB_Body`), `GB_Shorts`, `GB_MuscleShell` | `segment + 32 × region` | dermatome id |
| `GB_Skeleton`, `GB_Frac_*` | bone piece id | bone class (0 long-bone cortex, 1 flat, 2 vertebra, 3 skull, 4 cartilage, 5 tooth) |
| `GB_Organs` | organ id | sub-part id (chamber, lobe) |
| `GB_Vessels_*` | vessel index | t along the segment (0–1) |
| `GB_Brain` | surface region id | sulcus depth (0–1) |
| `GB_Cord` | cord segment index (C1 = 0 … S5 = 29, cauda 30) | t |

Code tables (in `codes.json`):
- **segment**: 0 head/neck, 1 torso, 2 arm_L, 3 arm_R, 4 leg_L, 5 leg_R, 6 hand_L, 7 hand_R, 8 foot_L, 9 foot_R, 10 shorts.
- **region** [RB §2.0]: 0 scalp, 1 face, 2 eyelid/lip, 3 neck, 4 trunk_front, 5 trunk_back, 6 limb, 7 palm/sole.
- **dermatome**: 0 cranial (CN V), 1 C2 … 7 C8, 8 T1 … 19 T12, 20 L1 … 24 L5, 25 S1, 26 S2, 27 S3, 28 S4–5. Anchors from R04 §6.2 (C4 shoulder top, C6 thumb, C7 middle finger, C8 little finger, T4 nipple line, T6 xiphoid, T10 umbilicus, T12 groin, L4 medial ankle, L5 dorsum of the foot, S1 lateral foot and heel, S4–5 perianal); boundaries between anchors interpolated (**K**).

### 5.6 Materials (placeholder names that become Godot surfaces)

| Object | Slots |
|---|---|
| `GB_Head` | `GBM_skin_head`, `GBM_mouth_lining` |
| `GB_Body` | `GBM_skin_torso`, `GBM_skin_arm_L`, `GBM_skin_arm_R`, `GBM_skin_leg_L`, `GBM_skin_leg_R` |
| `GB_Shorts` | `GBM_cloth` |
| `GB_Eye_*`, `GB_EyeFX_*` | `GBM_eye`; `GBM_tearline`, `GBM_eye_occlusion` |
| `GB_Mouth`, `GB_BrowLash` | `GBM_teeth`, `GBM_gums`, `GBM_tongue`; `GBM_hair_card` |
| `GB_MuscleShell` | `GBM_muscle_head`, `GBM_muscle_torso`, `GBM_muscle_arm_L`, `GBM_muscle_arm_R`, `GBM_muscle_leg_L`, `GBM_muscle_leg_R` |
| `GB_Skeleton`, `GB_Frac_*` | `GBM_bone`, `GBM_cartilage` |
| `GB_Brain`, `GB_Organs`, `GB_Cord` | `GBM_brain`, `GBM_organ`, `GBM_cord` |
| `GB_Vessels_Art/_Ven` | `GBM_vessel_art`, `GBM_vessel_ven` |

Materials are exported as named plain Principled placeholders (`export_materials='EXPORT'`, `export_image_format='NONE'` [T10]); Godot's import script replaces them by name. (`PLACEHOLDER` mode was rejected: it keeps slots but not names [T10 line 497–499].)

**Shape keys**: `GB_Head` 24 (`AU01_L/R, AU02_L/R, AU04_L/R, AU06_L/R, AU07_L/R, AU09_L/R, AU10_L/R, AU12_L/R, AU15_L/R, AU20_L/R, mouth_slack_L/R, swell_periorbital_L/R`; AU05, AU26 and AU43 are bone-driven: lids and jaw); `GB_Body` 4 (`chest_inhale`, `belly_distension`, `thigh_swell_L/R`); `GB_Organs` 6 (`heart_systole`, `lung_inhale_L/R`, `lung_collapse_L/R`, `diaphragm_inhale`).

**Bones**: §3.1.1 (39). **Actions**: `pose_idle`, `pose_guard`, `pose_cower`, `pose_brace` (single-frame key poses; procedural motion is added in Godot).

### 5.7 Exported files

`gore-game/assets/generated/subject/`:

| File | Content |
|---|---|
| `GB_Subject.glb` | Armature, all `GB_Outer`, `GB_Inner`, `GB_Variants` meshes, blend shapes, actions |
| `GB_Subject_LOD1.glb` | Fallback LOD |
| `manifest.json` | Schema versions, generator versions (`bpy` 5.0.1, exporter 5.0.21), build id, input hashes, per-mesh/surface vertex and triangle counts, rest bounds, wound-grid bounds, **segment origin table** (for the position maps), texture list with import hints, budget check results |
| `rig.json`, `landmarks.json`, `organs.json`, `vessels.json`, `spine.json`, `codes.json` | §5.8 |
| `brain_labels.png` + `brain_labels.json` | 64³ labels as an 8 × 8 tile atlas of 64² slices (512²), R = region id, lossless; JSON: origin, voxel size, id → name |
| `textures/*.png`, `textures/*.exr` | §4.2 |

`gore-game/assets/generated/props/`: `weapons.glb`, `room.glb` with marker empties `GBP_muzzle`, `GBP_blade_edge_0…7`, `GBP_hammer_face`, `GBP_claw`, `GBP_torch_nozzle`, `GBP_room_*` (they import as `Node3D` markers; no JSON needed).
`gore-game/assets/generated/` is git-ignored except `manifest.json` files (reproducible build outputs, §4.3).

### 5.8 JSON formats

Envelope (every file):
```json
{ "schema": "gb.vessels/1", "frame": "body_zup_m", "godot_mapping": "(x, z, -y)",
  "generator": "blender/gore_body/build.py", "build_id": "2026-09-26T10:00:00Z-3f2a9c", "data": { } }
```
Metres rounded to 1e-5, degrees, kg, mL/min, mmHg; `snake_case` keys; left and right entries both present.

`rig.json` (one bone and one body shown; the left elbow flexion axis in A-pose is (−0.866, 0, −0.5), which rotates the forearm toward −Y = anterior):
```json
{ "bones": [ { "name": "forearm_L", "parent": "upper_arm_L", "head": [0.325, 0.020, 1.164],
               "tail": [0.460, 0.020, 0.930], "deform": true, "physical": true } ],
  "bodies": [ { "bone": "forearm_L", "mass_kg": 1.2, "com_from_head": 0.430,
                "shape": { "type": "capsule", "radius": 0.038, "height": 0.27 },
                "joint": { "type": "hinge",
                           "axes": { "flex": { "world": [-0.866, 0.0, -0.5], "sign": 1 } },
                           "limits_live_deg": { "flex": [-5, 145] }, "limits_dead_deg": { "flex": [-10, 155] },
                           "torque_cap_nm": { "flex": 65, "ext": 65 },
                           "myotomes": { "flex": { "C5": 0.6, "C6": 0.4 },
                                         "ext": { "C6": 0.2, "C7": 0.6, "C8": 0.2 } } } } ],
  "face": { "lid_aperture_mm_to_deg": [[0, -38.0], [9.5, 0.0], [12, 7.5]], "blend_shapes": ["AU01_L", "…"] } }
```
(The lid table values above are placeholders for the format; B2 measures them.)

`organs.json`:
```json
{ "organs": [ { "id": "heart", "organ_id": 1, "mesh": "GB_Organs", "parent_bones": { "chest": 1.0 },
                "mass_g": 320, "compartment": "pericardium", "hit_priority": 10, "interior_colour": "#7B2626",
                "hit": [ { "shape": "obb", "c": [0.035, -0.036, 1.325], "size": [0.125, 0.090, 0.065],
                           "u": [0.632, -0.498, -0.593], "v": [0.466, -0.367, 0.805] } ],
                "sub": [ { "id": "heart_LV", "sub_id": 3, "shape": "ellipsoid", "c": [0.045, -0.035, 1.305],
                           "size": [0.090, 0.055, 0.055], "u": [0.632, -0.498, -0.593], "v": [0.466, -0.367, 0.805] } ],
                "blend_shapes": ["heart_systole"] } ],
  "tubes": [ { "id": "trachea", "radius": 0.010,
               "points": [[0.0, -0.030, 1.508], [0.0, -0.018, 1.455], [-0.003, 0.008, 1.402]] } ] }
```

`vessels.json`:
```json
{ "segments": [ { "id": "A04_L", "vessel": "A04", "name": "common carotid", "side": "L", "kind": "E",
                  "d_mm": 6.5, "d_range_mm": [6.0, 8.0], "rest_flow_ml_min": [350, 450],
                  "parent": "A02", "children": ["A05_L", "A06_L"],
                  "points": [[0.010, -0.025, 1.432, 0.00325], [0.028, -0.018, 1.515, 0.00325], [0.030, -0.012, 1.558, 0.00325]],
                  "bones": ["upper_chest", "neck", "neck"], "depth_mm": [15, 40],
                  "compressible": "partial", "self_stop": "no", "stump_frac": 0.6, "collaterals": ["A06_L"],
                  "bleed_ref": { "initial_ml_min": [1000, 2500], "loc_s": [20, 90], "death_min": [2, 5] },
                  "mesh": "GB_Vessels_Art", "vessel_index": 17, "source": "RB 3.3" } ],
  "beds": [ { "id": "brain", "q_rest_ml_min": 750, "compartment": "cranium" } ],
  "nerves": [ { "id": "radial_L", "roots": ["C5", "C6", "C7", "C8", "T1"], "points": [[0.18, 0.02, 1.40]] } ] }
```
(Points are `[x, y, z, radius]`; the example points are the waypoints; the real file holds the resampled centreline.)

`spine.json`:
```json
{ "vertebrae": [ { "level": "C5", "c": [0.0, 0.003, 1.536], "body_hwd_mm": [13.5, 18.5, 16.0], "disc_below_mm": 5,
                   "canal_ap_w_mm": [14, 24], "spinous_dy_mm": 42,
                   "cord": { "c": [0.0, 0.019, 1.536], "w_mm": 13.5, "ap_mm": 7.7 } } ],
  "cord_segments": [ { "id": "C6", "index": 5, "z_top": 1.545, "z_bottom": 1.527, "vertebra": "C5" } ],
  "conus_tip": [0.0, 0.017, 1.180], "thecal_end": [0.0, 0.035, 0.995],
  "brainstem": [ { "id": "medulla", "a": [0.0, 0.030, 1.619], "b": [0.0, 0.025, 1.633], "r": 0.008, "concussive_r_mm": 18 } ] }
```
Cord segment z ranges are computed from the vertebra centres and the offsets in [RB §4.6] (the example numbers show the format).

### Simulation parameters (Blender contract)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `seam_ring_n` | 160 | vertices | z ≈ 1.485 (1.47–1.50), single loop with abs(x) ≤ 0.075 | G |
| `uv_margin` | 16 at 2,048² | px | `FRACTION` 0.0078 | [RB §8.3] ≥ 8 px |
| `body_sdf_h / head_sdf_h` | 2.5 / 1.2 | mm | Master meshes | E / `anatomy.RES` |
| `json_precision` | 1e-5 | m | 10 µm | G |
| `gltf_influences` | 4 | — | `export_influence_nb` | [T10] V |
| `gltf_flags` | yup, tangents, extras, skins, morph + morph normals, def bones, rest-position armature, materials EXPORT, images NONE, vertex colour NONE, apply **off** | — | §5.9 | [T10] V |

### 5.9 glTF export call (options verified in the bundled exporter 5.0.21 [T10])

```python
bpy.ops.export_scene.gltf(
    filepath=out_path, export_format='GLB', use_selection=True,
    export_yup=True, export_apply=False,                      # modifiers already applied; keeps shape keys
    export_texcoords=True, export_normals=True, export_tangents=True,
    export_materials='EXPORT', export_image_format='NONE', export_vertex_color='NONE',
    export_attributes=False, export_extras=True,
    export_skins=True, export_influence_nb=4, export_all_influences=False,
    export_def_bones=True, export_rest_position_armature=True, export_leaf_bone=False,
    export_morph=True, export_morph_normal=True, export_morph_tangent=False,
    export_animations=True, export_animation_mode='ACTIONS')
```

### Visual/behavioural checklist (Blender contract)
- `python3 build.py --stage all` on a clean checkout reproduces byte-identical JSON and identical vertex counts (deterministic seeds).
- Opening the saved `.blend` shows every object in its collection with the contract name; `verify.py` prints zero failures.

---

## 6. Game module contract: `gore-game/`

### 6.1 Folder layout

```
gore-game/
├── project.godot, export_presets.cfg (M4), .gitignore, main.tscn
├── docs/                         (existing research + this plan)
├── tools/  (.gdignore)           jpeg_encode.py (existing)
├── assets/generated/             Blender outputs (git-ignored except manifests)
├── assets/authored/              ShaderMaterial .tres per surface, particle process materials, decal set, UI theme
├── core/                         frames.gd, events.gd, sim_clock.gd, settings.gd, registry.gd, perf_governor.gd, rng.gd, json_util.gd
├── pipeline/import/              subject_post_import.gd, props_post_import.gd, mesh_prep.gd, material_map.gd
├── subject/
│   ├── subject.tscn, subject.gd
│   ├── anatomy/                  anatomy_db.gd, anatomy_query.gd, rest_mapper.gd, brain_grid.gd, codes.gd
│   ├── wounds/                   hit_event.gd, contact_event.gd, anatomy_event.gd, wound_record.gd, wound_store.gd,
│   │                             wound_math.gd, morph_gunshot.gd, morph_shotgun.gd, morph_sharp.gd, morph_blunt.gd,
│   │                             morph_burn.gd, fracture_manager.gd, wound_wall_builder.gd, reveal_manager.gd, damage_map.gd, case_report.gd
│   ├── physiology/               physiology_node.gd, physio_model.gd, physio_state.gd, circulation.gd, vessel_graph.gd,
│   │                             bleed_site.gd, compartments.gd, respiration.gd, brain.gd, cord.gd, consciousness.gd,
│   │                             sensation.gd, motor_output.gd, eye_output.gd, skin_output.gd, voice_output.gd,
│   │                             postmortem.gd, params/*.json
│   ├── motor/                    ragdoll_builder.gd, motor_controller.gd, pd_bone.gd, tone_map.gd, paralysis_map.gd,
│   │                             clutch_ik.gd, breath_modifier.gd, rigor.gd, pose_snapshot.gd, behaviours/*.gd
│   └── face/                     eye_modifier.gd, face_controller.gd, skin_state.gd, pupil_light.gd
├── gore/
│   ├── shaders/                  skin, skin_discard, cloth, cloth_discard, muscle, bone, organ, brain, cord, vessel,
│   │                             wound_wall, eye, tearline, eye_occlusion, hair_card, teeth, xray_*, floor, wall_tile (.gdshader)
│   ├── shaders/include/          wound_sdf, blood_film, tissue, hash_noise, skin_state (.gdshaderinc)
│   ├── compute/                  paint_brush.glsl, dilate.glsl, livor.glsl, floor_flow.glsl
│   └── painter/                  damage_painter.gd, atlas_set.gd, brush.gd
├── fx/blood/                     vfx_director.gd, jet.gd/.tscn, stream.gd, drip.gd, rivulets.gd, hero_drops.gd,
│                                 spatter_pool.gd, mist.gd, froth.gd, decal_pool.gd, floor_splat.gd
├── fx/debris/                    debris_manager.gd
├── weapons/                      tool_base.gd, pistol.gd, shotgun.gd, knife.gd, fist.gd, hammer.gd, torch.gd, examine.gd, *.tscn, data/*.json
├── player/                       player.tscn, player.gd, tool_holder.gd
├── world/                        forensic_room.tscn, room.gd
├── ui/                           hud.tscn, hud.gd, tool_bar.gd, vitals_panel.gd, case_log.gd, time_controls.gd, ruler.gd,
│                                 examine_readout.gd, dev_scenarios.gd, theme.tres
├── xray/                         xray_mode.gd, killcam.gd
└── tests/                        run_tests.gd, unit/, scenarios/, visual/, perf/heavy_gore.tscn, perf/perf_gate.gd, out/ (ignored)
```

### 6.2 Project settings (G0)

| Setting | Value | Source |
|---|---|---|
| Physics > 3D > Physics Engine | Jolt Physics (not the 4.5 default) | [RB §8.2] V |
| Physics ticks per second | 60 | [RB §1.3] |
| Jolt Physics 3D > Queries > Enable Ray Cast Face Index | on | [RB §8.2] V |
| Renderer | Forward+ | — |
| Subsurface scattering quality | Medium (17 taps) default, High (25) on the 3060 tier (project default is Low = 11) | [RB §8.2] V |
| Screen-space AA | SMAA | [RB §8.4] |
| Tonemap (Environment) | AgX, to match the Blender look-dev (**K**: available since 4.4) | K |
| Shader globals | `gb_time_min` (float), `gb_splat` (sampler2D), `gb_splat_bounds` (vec4), `gb_xray` (float) | [RB §8.3] |
| Visual layers | 1 world, 2 subject outer, 3 subject inner, 4 debris, 5 viewmodel, 6 X-ray; world decals' `cull_mask` excludes 2–4 | [RB §8.2] |
| Physics layers (world) | 1 world, 2 ragdoll, 3 debris, 4 player | — |
| Private rest-space layers | 1 skin, 2 shorts, 3 bone, 4 organ, 5 vessel, 6 cord/brainstem, 7 nerve | §3.7 |
| Autoloads | `Events`, `SimClock`, `Settings`, `Registry`, `Perf` | §6.3 |

### 6.3 Autoloads

| Autoload | Responsibility | Key API |
|---|---|---|
| `Events` | Signal bus | `wound_created(subject, id)`, `hit_resolved(subject, report)`, `subject_state(subject, state)`, `spatter(event)`, `xray(on)` |
| `SimClock` | Time bands [RB §1.3], sim time, player mode | `tick(dt_real) -> float dt_sim`, `report_prediction(t_pred_s, critical: bool)`, `set_mode(REALTIME\|STANDARD\|FORENSIC)`, `fast_forward(scale)`, `t_minutes` (→ `gb_time_min`) |
| `Settings` | Quality tier, gore options, time mode | `tier`, `apply()` |
| `Registry` | Loads `manifest/rig/organs/vessels/spine/codes/brain_labels` once, converts to Godot frame | `rig()`, `organs()`, `vessels()`, `spine()`, `codes()`, `brain_grid()` |
| `Perf` | Custom monitors, spans, governor [RB §8.4] | `begin(span)`, `end(span)`, `level` |

### 6.4 Subsystem responsibilities and interfaces

All classes are typed GDScript; data carriers are `RefCounted` with typed fields. Interfaces below are **frozen at M0**; changes need an edit to this section and a schema bump.

| Subsystem (owner) | Files | Responsibility | Interface |
|---|---|---|---|
| Subject facade (G2) | `subject.gd` | Entry point for tools; owns child systems | `apply_hit(hit: HitEvent) -> int`, `apply_contact(c: ContactEvent) -> void`, `vitals() -> Dictionary`, `rest_to_world(p: Vector3, bone: int) -> Vector3`, `world_to_rest(p, bone)`; signal `hit_resolved(report: Dictionary)` |
| Hit events (G2) | `hit_event.gd`, `contact_event.gd` | Weapon → subject data | `HitEvent {weapon, kind (bullet/pellet/stab/slash/blunt/burn), origin, dir, muzzle_distance_m, projectile_d_mm, mass_g, speed_mps, energy_j, impactor, seed}`; `ContactEvent {points, normal, force_n, energy_j, contact_ms, edge_a, edge_b, flux_kw_m2, dt}` |
| Anatomy (G2) | `anatomy_query.gd`, `rest_mapper.gd`, `brain_grid.gd` | Private rest space, exact hits, track classification | `skin_hit(o_rest, d_rest) -> SkinHit {tri, bary, uv, codes, normal, p}`, `trace(track: Track) -> Array[AnatomyEvent]`; `AnatomyEvent {type: SKIN_BREACH\|BONE_HIT\|ORGAN_HIT\|VESSEL_HIT\|CORD_HIT\|BRAIN_HIT\|AIRWAY_HIT\|LUNG_HIT\|NERVE_HIT, id, p_in, p_out, overlap_d, detail}` |
| Morphology (G2) | `morph_*.gd`, `wound_math.gd` | Bible §2 sizes, shapes, marks, fractures, per-victim factors, ante/post-mortem | `build(hit, skin_hit, events, victim) -> WoundRecord` |
| Wound store (G3, written by G2) | `wound_store.gd`, `wound_record.gd` | CPU records ↔ GPU textures (§3.3.3), grid, retirement | `add(w) -> int`, `update(id)`, `get(id) -> WoundRecord`, `open_near(p_rest, r) -> PackedInt32Array`, `data_texture: ImageTexture` (RGBA32F 320 × 1), `grid_texture: ImageTexture3D`; signal `wounds_changed(ids)` |
| Wound walls, reveal, fractures (G3/G2) | `wound_wall_builder.gd`, `reveal_manager.gd`, `fracture_manager.gd` | §3.3.4–3.3.5, §3.5 | `build_wall(id) -> MeshInstance3D`, `refresh()`, `apply_fracture(bone_piece, pattern, event)` |
| Damage painter (G3) | `damage_painter.gd`, `compute/*.glsl` | Atlas brushes on the render thread | `queue(brush: Brush)`; `Brush {atlases, shape, p_rest, axis, radius_m, profile, op, values, t_min}` |
| Physiology (G1) | `physiology_node.gd` (Node) wraps `physio_model.gd` (pure) | Bible §3–4, §6 | `inject(wound_id, events, mech)`, `set_compress(site_id, v)`, `set_pose(snap: PoseSnapshot)`, `vitals() -> Vitals`, `sites() -> Array[BleedSite]`, `flow(site_id) -> FlowState {q_ml_min, p_local, pulsatile, jet_ok, sat, regime, outlet}`, `motor() -> MotorOutput`, `eyes() -> EyeOutput`, `skin() -> SkinOutput`, `voice() -> VoiceOutput`; signals `consciousness_changed(old, new)`, `arrest(t_sim)`, `dead_flag()`, `seizure(phase)` |
| Motor (G5) | `motor_controller.gd`, `pd_bone.gd`, behaviours | §3.1–3.2 | `set_mode(mode)`, `apply(out: MotorOutput)`, `flinch(bone, impulse, at)`, `pose_snapshot() -> PoseSnapshot`, `grab(bone, target)` |
| Eyes, face, skin (G6) | `eye_modifier.gd`, `face_controller.gd`, `skin_state.gd` | §3.6 | `apply(out: EyeOutput)`, `apply(out: SkinOutput)`, `lift_lid(side)`, `penlight(on, pos)` |
| Blood FX (G4) | `vfx_director.gd` and friends | §3.4 | reads `sites()`/`flow()` each frame; `spatter(e: SpatterEvent)`, `emit_drop(p, v, vol_ul)`, `floor_add(p, vol_ml, t_min)` |
| Tools (G7) | `tool_base.gd` and weapons | Player actions → events | `primary()`, `secondary()`, `muzzle_distance_to(subject) -> float`, `hud_info() -> Dictionary` |
| UI (G7) | `ui/*` | HUD, vitals, case log, time controls, ruler, examine readouts, dev scenarios | `CaseLog.add(report)`, `VitalsPanel.bind(subject)` |
| X-ray (G3 shaders, G7 UX) | `xray_mode.gd`, `killcam.gd` | Stencil X-ray, kill-cam timing | `enter(subject, track)`, `exit()` |

### 6.5 Import pipeline (G0)

`GB_Subject.glb.import`: `import_script/path = "res://pipeline/import/subject_post_import.gd"`, ensure tangents on, generate LODs off, shadow meshes off, named skins on, animation import on. `_post_import(scene)` must return the scene [T8]. The script:
1. For every `MeshInstance3D`: rebuild each surface with `CUSTOM0` = rest position + segment (from UV2.x for skin, piece id otherwise) as `ARRAY_CUSTOM_RGBA_FLOAT` [T5], keeping blend shapes, uncompressed.
2. Map material names (§5.6) to `res://assets/authored/materials/*.tres`.
3. Set layers, `cast_shadow` off and `visible = false` for inner meshes and variants.
4. Store `extras` meta (`gb_layer`) for the runtime systems [T9].
If step 1 cannot run at import (open question Q1), `mesh_prep.gd` performs it once at load.

### 6.6 Test and performance harness (G0, Q1)

| Kind | Command (engineers run it; nothing is installed) | Covers |
|---|---|---|
| Import | `godot --headless --path gore-game --import` ("starts the editor, waits for imports, quits" [T1]) | Asset pipeline; then `tests/unit/test_import.gd` checks CUSTOM0 on every surface (FB-11) |
| Unit and scenario | `godot --headless --path gore-game --script res://tests/run_tests.gd` [T1] | Physiology scenarios A–I, thresholds, frames, codes, myotome map, morphology distributions (≥ 20 samples), JSON schemas, determinism |
| Visual | `xvfb-run -a godot --path gore-game --rendering-driver vulkan --write-movie tests/out/<name>.png --fixed-fps 30 --quit-after 120 res://tests/visual/<scene>.tscn` [T1] | Anything needing a RenderingDevice: `RenderingServer.get_rendering_device()` returns null in headless mode [T7], so painter/compute tests are visual tests; headless tests use a `NullPainter` |
| Performance | Same as visual with `res://tests/perf/heavy_gore.tscn`; writes `tests/out/perf.csv` | [T6] monitors + `Performance.add_custom_monitor` spans + `viewport_get_measured_render_time_cpu/gpu` [T7]; `perf_gate.gd` fails on any §4.4 breach |
| Hardware | Same scene on a GTX 1660 and an RTX 3060 PC with `--gpu-profile` [T1] | RB §9 #50 at M2 and M4 |

### Simulation parameters (game contract)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `wound_data_tex` | RGBA32F 320 × 1 | texels | 64 wounds × 5 | §3.3.3 |
| `physio_step` | 0.05 | s real | Fixed | D12 |
| `interfaces_frozen_at` | M0 | — | Schema bump on change | G |
| `perf_run_length` | 60 | s | Scripted shots | [RB §8.4] |
| `visual_capture` | 30 fps, 120 frames, 960 × 540 | — | Lavapipe | G |

### Visual/behavioural checklist (game contract)
- A fresh clone plus `--import` plus `run_tests.gd` passes without any network access.
- Every subject surface in the imported scene carries CUSTOM0; no import step depends on the editor UI.

---

## 7. What to keep from the head project

| Item | Decision | How it is used |
|---|---|---|
| `gore_head/anatomy.py` SDF toolkit (`smin/smax`, `sd_*`, `sample_grid`, `surface_nets`, `project_to_surface`, `remesh_object`, `remove_small_islands`, `mesh_sdf`, `catmull`, `Curve1D`) | **Keep, import** | B1/B3/B4 build every organic mesh with it; B5 uses `catmull` |
| Head layer SDFs and builders (`skin_sdf`, `skull_sdf`, `jaw_sdf`, `brain_sdf`, `muscle_sdf`, teeth, gums, tongue, `build_eye`) | **Keep, import** | B2 rebuilds the head skin with the combined SDF; all other head layers are translated by (0, 0.020, 1.647) |
| Head contract landmarks | Keep (authoritative inside the head) | [RB §1.2] |
| `materials.py` (`GHS_BloodFilm`, `GHS_Muscle`, `GHS_Fat`, `GHS_Bone`, eye constants) | Keep as Cycles look-dev and **bake source** | B7 bakes from it; G3 ports blood-film and tissue banding into `.gdshaderinc` with bible numbers |
| `gore.py` geometry-nodes gore | Keep as the offline **reference renderer**; not shipped | Q1 renders the same hit in Blender and Godot side by side; the bible §2.7 fixes apply only if it is used as a reference |
| `build.py` presets and hair-curve growth | Keep; hair becomes cards | B2 converts brows/lashes to alpha cards |
| `gh_common.py` stage and render helpers | Keep | Test renders |
| `renders/` | Keep as look-dev references | — |
| `gore-game/index.html` (three.js prototype; its `src/` is missing; it loads CDN scripts) | **Retire** | Keep only its case-file visual language ("CASE 26-0926", "Injury log") for the Godot UI |
| `gore-game/tools/jpeg_encode.py` | Keep, unused by Godot (`tools/.gdignore`) | Docs thumbnails |
| `docs/research*`, `REALISM_BIBLE.md` | Authoritative | Cited everywhere as `[RB §x]` |

### Simulation parameters (reuse)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `head_res` | skin 1.2, muscle 1.9, skull 1.4, jaw 1.0, brain 0.95, gums/tongue 0.7 | mm | Master meshes before decimation | `anatomy.RES` |
| `eye_constants` | r 12 mm, cornea r 7.5 mm at 5.82 mm, limbus 5.9 mm, IOR 1.376 | — | Shared by B2, G6 | `materials.py` |

### Visual/behavioural checklist (reuse)
- The full-body head is the head-project head: same face, eyes, teeth and brain; only the neck changed.
- Blender reference renders and Godot renders of the same wound agree in size and layer order.

---

## 8. Work packages

### 8.1 Overview

| ID | Package | Hard dependencies | Soft (late) dependencies | Main outputs | Days |
|---|---|---|---|---|---|
| **B0** | Blender infra, data tables, placeholder | — | — | `gore_body` scaffold, `gb_data`, placeholder export | 5 |
| **B1** | Body skin, shorts, muscle shell, codes, body UVs | B0 | B2 seam ring | `GB_Body`, `GB_Shorts`, `GB_MuscleShell`, tissue/tension maps | 15 |
| **B2** | Head integration, neck seam, face rig data, eye FX, hair cards | B0 | B1 `skin_sdf` | `GB_Head`, eyes, mouth, shape keys | 15 |
| **B3** | Skeleton, fracture variants, bone capsules | B0 | B1 (depth checks) | `GB_Skeleton`, `GB_Frac_*` | 12 |
| **B4** | Organs, cord, brainstem, brain labels | B0 | B1 (fit), B3 (ribcage fit) | `GB_Organs`, `GB_Cord`, `GB_Brain`, `organs.json`, `spine.json`, labels | 12 |
| **B5** | Vessel network and nerves | B0 | B1, B3 (depth/canal checks) | `GB_Vessels_*`, `vessels.json` | 10 |
| **B6** | Rig, weights, poses, export, manifest, LOD1 | B0 | B1–B5 (final export) | `GB_Subject.glb`, `rig.json`, manifest | 15 |
| **B7** | Look-dev and bakes | B0 (tileables, iris) | B1–B4 UVs (final bakes) | Textures §4.2 | 12 |
| **B8** | Props and room | B0 | — | `weapons.glb`, `room.glb` | 8 |
| **G0** | Godot scaffold, import, harness, governor | B6 placeholder (day 3) | — | Project, import script, tests, perf gates | 10 |
| **G1** | Physiology | — (bible) | B5 `vessels.json`, B4 `spine.json` | `subject/physiology/*` | 20 |
| **G2** | Hit pipeline, anatomy query, morphology, case report | G0 | B3–B5 JSON | `subject/anatomy/*`, `subject/wounds/*` (CPU) | 18 |
| **G3** | Gore rendering, painter, reveal, X-ray shaders | G0, G2 record schema (M0) | B7 textures | `gore/*`, wound store GPU, walls | 25 |
| **G4** | Blood FX, pools, debris | G0, G1 FlowState stub, G3 painter stub | — | `fx/*` | 20 |
| **G5** | Ragdoll and motor | G0, B6 `rig.json` (placeholder) | G1 MotorOutput | `subject/motor/*` | 20 |
| **G6** | Eyes, face, skin state | G0, G1 EyeOutput stub | B2 face rig | `subject/face/*`, eye shaders | 12 |
| **G7** | Tools, player, UI, X-ray UX, main scene | G0, G2 API | B8 props | `weapons/*`, `player/*`, `ui/*`, `xray/*` | 15 |
| **Q1** | QA and performance | G0 | everything | Acceptance runner, perf gates, hardware runs | 10 + continuous |

Total ≈ 254 engineer-days (Blender 104, Godot 140, QA 10; the 12 days of the removed audio package G8 are subtracted); with 10 engineers the calendar is ~12 weeks because of the dependency chain and integration (§9).

**Interface owners** (writer / reader): WoundRecord G2 / G3; FlowState, Vitals G1 / G4, G7; MotorOutput G1 / G5; EyeOutput, SkinOutput G1 / G6; VoiceOutput G1 / G5, G6 (VoiceOutput drives only the visible mouth, jaw and breathing animation; there is no sound); `rig.json` B6 / G5; `vessels.json` B5 / G1, G2; `organs.json`, `spine.json` B4 / G1, G2; `codes.json` B1 / G2, G3; `manifest.json` B6 / G0.

**Full-body acceptance tests** (FB, in addition to the bible's §9 numbers):

| # | Test |
|---|---|
| FB-1 | Neck seam: identical ring vertices (gap 0), normal difference < 1°, no lighting seam in front/three-quarter/side renders (Blender and Godot) |
| FB-2 | Wounds, walls and paint stay on the tissue through elbow 0–145°, knee 0–135°, shoulder abduction 0–90°, hip flexion 0–110° |
| FB-3 | Girths within ±2 cm (calf, neck ±1.5) and landmark heights within ±5 mm of [RB §7.1] |
| FB-4 | Nesting: bones inside the muscle shell inside the skin; organs inside the ribcage/abdominal wall by ≥ 2 mm; no organ–organ overlap > 1 mm |
| FB-5 | Vessel depths: CCA/IJV 20–30 mm at C4–C6, femoral artery 15–30 mm at the groin, radial artery 2–5 mm at the wrist, brachial 10–20 mm mid-arm [RB §7.6] |
| FB-6 | Paralysis postures for complete C5, C6, C7, T1, T8, an L4 root, Brown-Séquard (left, T10) and a right motor-strip lesion match [RB §4.5–4.6] |
| FB-7 | Cut-strings collapse: first ground contact 0.35–0.55 s, head contact 0.7–1.2 s; conscious falls show an arm reaction, unconscious falls none [RB §4.10] |
| FB-8 | A 1 m shotgun chest wound reveals muscle, rib and lung in the same frame; nothing inner is visible elsewhere |
| FB-9 | X-ray: no inner anatomy outside the body silhouette; the track is visible |
| FB-10 | Shorts: holes at wound sites, stain area 2–4 × the skin stain for the same blood volume, never removed |
| FB-11 | Import: every subject surface has CUSTOM0 RGBA32F; `PIPELINE_COMPILATIONS_DRAW` = 0 in the scripted scene |
| FB-12 | Determinism: same seed and inputs → identical wound records and identical physiology state hash every second for 10 min |
| FB-13 | Pose invariance: the same body point shot in 3 poses gives the same wound record (±0.5 mm) |
| FB-14 | Heart and lungs move at the simulated HR/RR and stop at arrest |
| FB-15 | Code decoding: navel vertex → T10, nipple → T4, thumb → C6, heel → S1, palm → region palm/sole |

### 8.2 Package details

**B0 — Blender infra, data tables, placeholder (5 days).**
Inputs: RB §1.2, §3.3, §4.6, §7; `gore_head`. Tasks: scaffold every file of §5.2 with stubs and final signatures; transcribe the bible tables into `gb_data` (landmarks, rig, vertebrae, ribs, organs, tubes, vessels, tissue, segment masses, myotomes §3.2, dermatome anchors); `write_json` with schema envelope; `verify.py` framework; `placeholder.py` (capsule mannequin from landmarks with final names, 39-bone armature, simple weights, the head-project eyes) and its export by day 3 (using B6's `export.py` draft). Acceptance: `--stage placeholder --quick` < 2 min; placeholder imports in Godot (G0); table checks (25 vertebra rows incl. S1, segment mass fractions sum 1.000, every vessel has a parent except roots).

**B1 — Body skin, shorts, muscle shell, codes, body UVs (15 days).**
Tasks: `body_sdf` from landmarks and girths (superellipse torso sections n 3.5 chest / 2.8 waist / 2.5 limbs, y offsets [RB §7.1]); limbs as tapered swept sections with muscle masses (deltoid, biceps, forearm flexor mass, gluteal, quadriceps, calf); subtle bony landmarks at lean sites (clavicles, sternum, patella, tibial face, malleoli, olecranon, spinous processes, iliac crests, scapular inferior angles); nipples 15.5 cm below the jugular notch and 20 cm apart, navel [RB §7 checklist]; simplified hands and feet (D4); combined `skin_sdf` with smooth union in the neck; master mesh at h 2.5 mm; cut and zip at the seam ring (B2 function); LOD0 by Decimate (collapse) to 44k with the ring re-zipped after decimation; seams on planned lines (inner arm, inner leg, lateral torso, shoulder ring, palm/dorsum, sole/dorsum), lower-neck island scaled ×2 to soften the texel jump at the seam; unwrap `MINIMUM_STRETCH`, pack 16 px; codes (segment, region, dermatome); tension map (Langer/RSTL directions, bible §2.3.1) and tissue-depth map (skin by region, fat map × fat%/15, muscle depth [RB §7.6]) baked to 512²; shorts (D2, §1.2); muscle shell (skin SDF offset inward by skin + fat, 24k, 6 surfaces). Acceptance: FB-3, FB-15; RB §7 checklist (profile line ear canal–shoulder–trochanter–front of ankle within ±15 mm; fingertips at z ≈ 0.77); manifold, watertight; texel density 0.84 mm ± 20 %; shorts ≥ 1 mm off the skin in the bind pose and at 90° hip flexion (checked after B6 skinning); triangle counts ±10 % of §4.1.

**B2 — Head integration, neck seam, face rig data, eye FX, hair cards (15 days).**
Tasks: `seam_ring(n=160)` (analytic: rays in the seam plane from the neck axis, bisection on `skin_sdf`); head skin rebuilt with the combined SDF at 1.2 mm (repeat `build_anatomy`'s mouth-lining split and `gh_lip` mask), zipped to the ring; decimate to 30k with vertex-group protection of lids, lips, nostrils and ears (≥ 1 mm edges there); translate all other head layers; hand skull/jaw to B3 and brain to B4; eye FX meshes; brow/lash cards from the head project's curves; face bone positions and the lid aperture ↔ angle table (0–12 mm); 24 face shape keys as analytic displacement fields around landmarks (e.g. AU04: brow −3 mm z and −2 mm medial, falloff radius 15 mm; amplitudes 2–8 mm); head UV (scalp seam along the back midline, ears as islands, mouth interior island). Acceptance: head landmarks in body frame equal the [RB §1.2] table (eyeball centres (±0.032, −0.050, 1.669), ear canals z 1.647); FB-1; lids close to 0 mm without touching the eyeball (gap ≥ 0.2 mm) and open to 12 mm; no self-intersection at any single shape key at 1.0; cards stay attached; head texel 0.24 mm ± 20 %.

**B3 — Skeleton, fracture variants, bone capsules (12 days).**
Tasks: vertebrae C1–L5, sacrum, coccyx at the [RB §7.3] CSV (body sizes, canal, spinous offsets); ribs 1–12 swept 12–15 × 5–7 mm through the rib table points, costal cartilages, sternum (50 + 105 + 35 mm, 20° incline); clavicles, scapulae, pelvis (acetabula at the hip centres), long bones at bible lengths and shaft diameters as **double shells** (periosteal outer + endosteal inner surface, cortex 6–8 mm femur, 5 humerus, etc.) so cut surfaces show a cortex ring and marrow; hand and foot bone blocks; skull and mandible from the head (6–7 mm vault with tables); bone capsules (~60) and decimated exact-hit meshes (≤ 20k); fracture variants by numpy Voronoi splitting (skull bursts L/R/T with 20–80 fragments, median 15–25 mm [RB §2.2.3]; long bones `simple` and `comminuted`, 8–20 fragments) with piece ids. Acceptance: femur 47 ± 1, tibia 41, fibula 39.5, humerus 34, radius 26, ulna 27.5, clavicle 14.8 cm; vertebra centres ±2 mm; lean-site depths under the skin: tibial face 3–6 mm, patella 4–8, malleoli 2–4, sternum 5–12 [RB §7.6]; intercostal spaces 15–25 mm front; triangle counts.

**B4 — Organs, spinal cord, brainstem, brain labels (12 days).**
Tasks: organs from the [RB §7.5] primitives refined into anatomical shapes: heart (4 chambers as inner cavities, axis base → apex (0, −0.005, 1.360) → (0.082, −0.068, 1.285), walls LV 9 / RV 3–5 / atria 2–3 mm, pericardium 2–3 mm off), lungs filling the pleural space to the 6th/8th/10th-rib borders with hila, diaphragm domes (R 1.320, L 1.300), liver lobes and gallbladder, spleen, kidneys, adrenal hit volumes, stomach, pancreas, bladder, larynx (thyroid and cricoid cartilage), trachea with rings, bronchi, oesophagus, thyroid; greater omentum apron (`#E8C766`, 5–10 mm thick, from z ≈ 1.12 to 0.95) over a dark peritoneal backing shell; blend shapes (`heart_systole` −15–20 % ventricular volume, `lung_inhale` +10 % volume with the diaphragm −1.5–2 cm, `lung_collapse` −70 %); cord C1–S5 with CSV ellipses, dura tube, cauda equina, root stubs; brainstem capsules and cerebellum labels; brain label grid 64³ (lobes cut by the head's `CENTRAL_SULCUS` and `LATERAL_FISSURE` curves plus planes; internal capsule, thalamus, brainstem parts, cerebellar hemispheres, vermis as ellipsoids). Acceptance: organ centres ±5 mm and sizes ±10 %; masses (volume × 1.05 g/cm³) ±15 % of the bible; FB-4; lung borders at the three reference lines ±15 mm; conus tip (0, 0.017, 1.180) ±3 mm; cord sizes at C2, C5, T7 ±0.5 mm [RB §7.4].

**B5 — Vessel network and nerves (10 days).**
Tasks: §3.4.1. Acceptance: centrelines within 2 mm of every [RB §3.3] waypoint; diameters ±5 %; FB-5; arterial tree rooted at A01 plus the pulmonary tree at P01, venous trees ending at the right atrium; left/right completeness; no arterial tube inside bone except in canals (vertebral foramina); ~14k triangles; `vessels.json` passes the schema check and the G1 loader.

**B6 — Rig, weights, poses, export, manifest, LOD1 (15 days).**
Tasks: armature (§3.1.1); `weights_at(p)`: analytic smooth weights from distance to bone segments with joint blend zones scaled by the local limb radius, twist bones sharing along their length, face bones by angular regions around the eyes and under the mouth line; the same function for every layer; normalise, ≤ 4 influences; key poses; `rig.json` with world joint axes, limits, masses, shapes, caps, myotomes; export (§5.9), LOD1, manifest; round-trip check (re-import the glb in Blender, compare counts and bone names). Acceptance: joint positions ±2 mm of [RB §7.2]; weight sums 1 ± 1e-4; deformation tests at elbow 0–145°, knee 0–135°, shoulder abduction 90°, hip flexion 110°: volume loss < 15 % in the joint region and no inner-layer vertex > 3 mm outside the skin up to 90 % of live ROM; FB-11 (with G0); files within §4.3.

**B7 — Look-dev and bakes (12 days).**
Tasks: Cycles materials reusing `gore_head/materials.py` (regional skin: lighter palms/soles, darker knees/elbows, nipples, subtle dorsal hand/forearm veins, scalp stubble); bakes at 2,048²: albedo (emission of the colour), normal (high → LOD0, cage 3 mm, MikkTSpace), ORM with SSS mask; skeleton, organ and brain sets; seamless 512² tileables (muscle fibre, fat lobule, bone cut, diploë, blood crust, cloth weave) with 4D noise on a torus mapping (Noise/Voronoi `W` input); iris 1,024² + height; sclera veins; painter inputs (segment-relative half-float position maps, rest normals, valid masks, dominant-bone map), 8 px dilation; decal stain set (32–64 procedural drops and smears, albedo + normal + ORM); room and prop textures. Acceptance: no empty texels inside islands; tileable edge error < 2/255; skin albedo luminance within the head palette per `skin_tone`; Godot vs Cycles renders of the reference stage reviewed side by side.

**B8 — Props and room (8 days).**
Tasks: pistol (9 mm bore, `GBP_muzzle`), shotgun (12 gauge ~18.5 mm bore), knife (single-edged 25 × 120 mm [RB §2.3], 8 edge markers), claw hammer (0.45–0.7 kg head, round face Ø 28 mm, claw marker [RB §2.5]), propane torch (nozzle marker, visible flame ~8 cm), fist glove, ruler, penlight, thermometer; room per §1.3 with exact axis-aligned planes. Acceptance: critical dimensions ±1 mm; markers present; room constants equal `room.gd`.

**G0 — Godot scaffold, import pipeline, harness, governor (10 days).**
Tasks: §6.1–6.6; autoload stubs with final signatures; `.gitignore`; import script and `mesh_prep.gd`; material map; warm-up routine that draws every material/particle/inner-mesh variant once off-screen at load [RB §8.2]; perf CSV, gates, custom monitors; `PerfGovernor` (§10.2 order); spikes for open questions Q1–Q5 (§12.1) in week 1. Acceptance: headless import + tests green; FB-11; perf CSV produced from the placeholder scene; spike answers recorded in §12.1.

**G1 — Physiology (20 days).**
Tasks: transcribe [RB §3–6] into `params/*.json`; `PhysioModel` with the [RB §4.2] update order; vessel graph Tier 1, BleedSites, compartments; `SimClock` bands; consciousness, brain regions (from the label grid damage), cord segments and syndromes, spinal and neurogenic shock, respiration and O₂, sensation by dermatome, motor output (tone states + §3.2 strengths), eye output ([RB §5.3–5.5]), skin output, voice output, post-mortem clocks; deterministic RNG; state serialisation; overlay data. Acceptance: [RB §3.4] scenarios A–I in range; [RB §9] #21 timings, #24, #25 timings, #26–#30, #32–#40, #47–#49 numeric parts; Nadler BV0 5.09 L; shunt example (7 mm carotid, tissue factor 0.5 → MAP ≈ 48 mmHg, ~2.4 L/min) [RB §3.2]; FB-12; ≤ 0.3 ms per tick.

**G2 — Hit pipeline, anatomy query, morphology, case report (18 days).**
Tasks: `RestMapper`; private rest space (§3.7); `AnatomyQuery`; morphology per weapon [RB §2.1–2.6] (range classes, collar eccentricity, oblique ellipse, keyhole and graze, exit-shape weights, skull tables, radial fractures with Puppe termination, shotgun pattern vs range, wad, burst model, knife slash/stab and gape with the tension map, fist and hammer thresholds with the fracture logistic and repeated-blow table, torch dose via painter texels), per-victim factors, ante/post-mortem rules; `DamageMap`; case-log reports (clinical wording with measured sizes); pellet merging. Acceptance: [RB §9] #1–#8, #10, #12, #13, #15–#17, #19, #20 (numeric, ≥ 20 samples each); FB-13; ≤ 2 ms pistol, ≤ 4 ms shotgun.

**G3 — Gore rendering, painter, reveal, X-ray shaders (25 days).**
Tasks: §3.3 and §3.5: GPU wound store, shader includes, all subject shaders with discard variants and per-surface switching, analytic cavity, wound walls, back-face interiors, bone holes/bevels/cracks, variant swaps, brain track tint, organ uniforms and blend shapes, compute painter (brushes, dilation, timestamps, blood-film optics, bruise and burn ageing), livor compute, reveal manager, X-ray stencil shaders, warm-up list, SSS settings. Acceptance: [RB §9] #1–#3, #5–#7, #9, #10, #15–#18, #20 (visual); bible tech checklist; FB-1 (lighting), FB-2, FB-8, FB-9, FB-10; GPU counters inside §4.4.

**G4 — Blood FX, pools, debris (20 days).**
Tasks: §3.4.2–3.4.4: regimes, jets (ribbon/tube trail + breakup drops, pulse waveform and per-vessel delays), streams, drips and pendant drops, rivulet agents, back/forward spatter [RB §2.1.3], mist, froth, hero drops, decal pool, floor splat compute with gel, serum rim and drying ramps, blood on weapons, debris (bone chips, brain clumps that stick with p 0.5–0.8, MultiMesh freezing). Acceptance: [RB §9] #11, #21–#27, #31; 1 L pool ≈ 70 cm; caps honoured; director ≤ 0.5 ms.

**G5 — Ragdoll and motor (20 days).**
Tasks: §3.1–3.2: builder from `rig.json`, PD with directional caps, tone states, paralysis map, behaviours (flinch, guard, standing clutch IK, down clutch by PD, stagger toward the weak side, cut-strings and faint collapses, writhe, prop up, drag with the arms, decorticate/decerebrate, fencing, tonic-clonic seizure, agonal gasp torques with G6's jaw), rigor lock, wet-floor friction, grab/drag support, `PoseSnapshot`. Acceptance: [RB §9] #12, #32, #33 (collapse), #35–#38, #46, #48; FB-6, FB-7; 10 min of continuous ragdoll plus grabbing without instability (no body > 10 m/s without an impulse).

**G6 — Eyes, face, skin state (12 days).**
Tasks: §3.6. Acceptance: [RB §9] #29 (colours), #33 (eyes), #41–#46; bible §5 checklist.

**G7 — Tools, player, UI, X-ray UX, main scene (15 days).**
Tasks: player; tools with bible parameters (pistol 9 mm FMJ; shotgun 00 buck / #7.5 selectable; knife stab and slash from the mouse gesture with 3–5 edge rays per frame; fist force from swing speed; hammer energy from swing; torch flux cone); dev range presets (contact, 5 cm, 30 cm, 1 m, 3 m); examine tool (grab/drag/turn the body, press for livor blanching, wipe soot, lift lid, turn head, penlight, ruler in mm, thermometer); HUD, vitals, case log, time controls (Realtime / Standard / Forensic, 720× fast-forward, post-mortem scrub), X-ray toggle and kill-cam UX, dev scenario menu ([RB §3.4] A–I, [RB §4.7] canonical injuries), new subject by seed, quality tier. Acceptance: [RB §9] #5 (wipe), ruler ±0.5 mm on a 10 mm test sphere, #44, #47 (turning and pressing); sim time and band always visible in the forensic overlay.

**Q1 — QA and performance (10 days + continuous).**
Tasks: acceptance runner covering every [RB §9] test and FB-1…15 (automated where numeric, scripted camera shots where visual); heavy-gore scene; CI gates; hardware sessions (GTX 1660, RTX 3060) at M2 and M4; governor tuning; Blender/Godot side-by-side renders with `gore.py`. Acceptance: [RB §9] #50; all gates green at M4.

### Simulation parameters (work packages)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `work_packages` | 18 (B0–B8, G0–G7, Q1) | — | §8.1; audio package G8 removed | G |
| `effort_blender / godot / qa` | 104 / 140 / 10 | engineer-days | Godot total without G8 (−12) | E |
| `first_isolated_demo` | day 5 | — | Placeholder subject + stubs | G |
| `interface_freeze` | M0 (end of week 1) | — | §6.4 | G |

### Visual/behavioural checklist (work packages)
- Every package can demo its output in isolation on day 5 using the placeholder subject and stubs.
- Nothing merges that breaks the headless test run or a perf gate.

---

## 9. Dependencies and milestones

### 9.1 Dependency graph

```
day 1:  B0 ──┬──► B1 ──┐                                 G1 (from the bible, stubs out)
             ├──► B2 ──┤ seam ring shared
             ├──► B3 ──┤                                 B7 (tileables, iris) ; B8
             ├──► B4 ──┼──► B6 final export ──► B7 final bakes
             ├──► B5 ──┘        ▲ (week 4, again week 7)
             └──► B6 placeholder export (day 3) ──► G0 ──┬──► G2 ──► G3 ──┬──► G4
                                                          ├──► G5          ├──► G7 (+ B8)
                                                          └──► G6          └──► Q1 (continuous)
Critical path: B0 → B1/B2 → B6 final → G3 inner layers + G5 final rig → Q1 hardware pass.
```

### 9.2 Milestones (10 engineers)

| Milestone | End of week | Content | Must pass |
|---|---|---|---|
| **M0 Walking skeleton** | 1 | Placeholder subject with final names and rig exported; imported with CUSTOM0; ragdoll falls; pistol ray → wound record → SDF dot on the skin; physiology unit tests run; perf CSV produced; interfaces frozen | FB-11, FB-12 (physiology only), scenario H [RB §3.4] |
| **M1 Real body** | 4 | B1, B2, B3, B6 v1; skin shaders tiers a–c with walls; pistol and knife morphology; circulation, shock, consciousness, time bands; tone and flaccid collapse; blink, gaze, pupils | [RB §9] #1–#3, #15, #16, #21, #28, #32; FB-1–4, FB-7, FB-13 |
| **M2 Inside** | 7 | B4, B5, B7 bakes; all bleeding regimes, pools, hero drops; paralysis map and behaviours; all six weapons; inner layers, fractures, X-ray; death choreography; **first hardware perf run** | [RB §9] #4–#14, #17, #20, #22–#27, #30–#38, #41–#44; FB-5, FB-6, FB-8, FB-9, FB-14 |
| **M3 Forensic** | 9 | Post-mortem (livor atlas, rigor, algor, eye surface), examine tools, case log, time controls, shotgun head burst, brain-region deficits | [RB §9] #18, #19, #29, #39, #40, #45–#49; FB-10, FB-15 |
| **M4 Ship quality** | 12 | Governor tuned; [RB §9] #50 on GTX 1660 and RTX 3060; full acceptance run; Windows/Linux export presets with the 4.5 shader baker (templates: §12.1 Q9) | All [RB §9] and FB tests |

### Simulation parameters (schedule)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `team_size` | 10 | engineers | 9 Blender/Godot + 1 QA | G |
| `effort_total` | ~254 | engineer-days | §8.1 (G8 audio, 12 days, removed) | E |
| `calendar` | 12 | weeks | M0–M4 | E |
| `hardware_runs` | M2, M4 | — | 1660 + 3060 | D17 |

### Visual/behavioural checklist (milestones)
- M0 already looks like the product loop (shot → mark → fall), even with capsules.
- From M2 on, every weekly build runs the heavy-gore scene and publishes the perf CSV.

---

## 10. Risks, fallbacks and the performance cut order

### 10.1 Risk register

| # | Risk | Early signal | Mitigation | Fallback |
|---|---|---|---|---|
| R1 | GDScript hot paths too slow (hit > 2 ms, rivulets, PD callbacks) | `Perf` spans in the heavy scene | Native Jolt queries, worker task for agents, caps | Hit work split over 2 frames; agents 24 → 12; rivulets moved to a compute shader; 6DOF springs for hands/feet/clavicles |
| R2 | Private-space Jolt queries behave unexpectedly (bodies not queryable before a step, result limits) | G0 spike Q4 | Activate the space, wait one physics frame, collision layers | Analytic GDScript broad phase (AABB per primitive, ~400 primitives filtered by bone), ~1–2 ms |
| R3 | Import script cannot rewrite meshes | G0 spike Q1 | — | `mesh_prep.gd` at load (≤ 40 ms once) |
| R4 | Hidden inner meshes still cost skinning | G0 spike Q3 | Measure with inner meshes hidden vs removed | Keep inner meshes out of the tree until first reveal; merge inner meshes into fewer instances |
| R5 | `discard` variant cost on large surfaces | GPU time on hardware (M2) | Per-surface switching (5 body surfaces) | Split torso front/back; cap open wounds per surface; more cavity shading |
| R6 | Wound-wall generation fails in concave regions (axilla, groin, neck folds) | FB-2 visual tests | Ray fallbacks, ring smoothing | Cavity shading + back-face flesh for that wound only |
| R7 | UV quality on SDF meshes (stretch, islands) | B1/B2 texel-density check | Planned seams, `MINIMUM_STRETCH` [T12] | Smart UV Project for hard regions; painting stays seam-free via position maps |
| R8 | Neck seam artefacts after decimation | FB-1 renders | Re-zip after decimation | Keep the ring band un-decimated (≈ +600 tris) |
| R9 | Linear-blend skinning collapse at shoulder, forearm twist, hip | B6 deformation tests | Twist bones | 2–4 corrective blend shapes driven by joint angles; limit standing animation ROM |
| R10 | Ragdoll instability under PD (jitter, explosions) | G5 soak test | Caps, ω·Δt ≤ 0.5, mass ratios ≤ 10:1 | Jolt 12–16 velocity / 3–4 position steps [RB §8.2]; lower ω; springs for non-key joints |
| R11 | GPU cost unknown until hardware runs | Count gates only | Conservative defaults (Medium SSS, half-res SSAO on the 1660 tier) | Governor + structural cuts (§10.2) |
| R12 | Blender build time or memory (1.2 mm head, 2.5 mm body) | Stage timings in `manifest.json` | Stage caching, chunked SDF evaluation, 1–4 bake samples | Body at h 3 mm; bakes at 1,024² for inner sets |
| R13 | Physiology interaction bugs and tuning time | Scenario tests drift | Deterministic replays, per-subsystem unit tests | Disable Tier-2 vessel solve and optional special states |
| R14 | *Removed (was a synthetic-voice risk; the user removed audio from the game)* | — | — | — |
| R15 | Eye realism below AAA | Side-by-side with Cycles | Refraction + parallax iris, occlusion and tearline meshes | More B7 iris detail, extra look-dev time |
| R16 | Windows/Linux export templates are an official download | M4 | Run from the editor binary until then | User decides (§12.1 Q9) |
| R17 | Shader-compile hitches (first discard variant, first X-ray, first organ) | `PIPELINE_COMPILATIONS_DRAW` > 0 | Warm-up at load; 4.5 shader baker at export | Pre-switch all surfaces to discard variants for one frame at load |
| R18 | Anatomical K-values (myotome weights, added vessels) wrong | QA re-check | Tagged K in data tables | Correct the tables; formats unchanged |

### 10.2 What to cut first if a scene drops below 60 fps

**Runtime governor** (automatic, reversible; GPU > 14 ms over 0.5 s → step down, < 11 ms for 3 s → step up) [RB §8.4]:
1. Mist sprite count and size.
2. Spatter `amount_ratio` down to 50 %.
3. Stain-particle lifetime (bake old stains into the splat map).
4. Decal fade distance 25 → 12 m.
5. SSS taps 25 → 17 → 11.
6. SSAO half resolution.
7. FSR 2.2 at 0.77 render scale.

**Structural cuts** (settings or build changes, in this order, each re-measured):
8. Hero drops in flight 150 → 60 and rivulet agents 24 → 12 (stains are still painted, only fewer drops fly).
9. Key-light shadow 2,048 → 1,024; panel-light shadows off.
10. Reveal radius 10 → 5 cm; organs and vessels drawn only in X-ray or when within 5 cm of an open wound.
11. Wound walls 16 → 8 (older walls fall back to cavity shading).
12. Jet VFX 6 → 3 (physiology unchanged).
13. Floor splat 2,048² → 1,024² (7.8 mm texels).
14. Subject LOD1 beyond 3.5 m.

**Never cut**: wound sizes and shapes, physiology, paint on the subject, eye behaviour, the first-minute real-time rule [RB §1.3].

### Simulation parameters (risks and scalability)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `governor_high / low` | 14 / 11 | ms GPU | 0.5 s / 3 s windows | [RB §8.4] G |
| `fallback_agents / drops` | 12 / 60 | — | Cut 8 | G |
| `fallback_reveal_radius` | 5 | cm | Cut 10 | G |
| `fallback_walls` | 8 | per subject | Cut 11 | G |

### Visual/behavioural checklist (risks and scalability)
- When the governor acts, only mist density, far stains and screen sharpness change; the subject looks identical.
- Every fallback keeps the physiology and every wound record exactly as before.

---

## 11. Verification strategy in one page

- **Numbers first**: every bible statement with a number is tested on the data (wound records, physiology state, JSON geometry), not on pixels. These tests are headless and run on every change.
- **Pictures second**: fixed camera shots under xvfb (`--write-movie`, 30 fps) for look, seams, layers and choreography, reviewed against Blender reference renders from `gore.py` and `lookdev.py`.
- **Budgets always**: the heavy-gore scene runs weekly from M2 with count gates here and GPU timings on the two target PCs at M2 and M4.
- **Determinism**: every subject has a seed; any failing test prints the seed and the event list so it can be replayed exactly.

### Simulation parameters (verification)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `distribution_samples` | ≥ 20 (exit shapes ≥ 100) | trials | Bible §9 rule | [RB §9] |
| `state_hash_interval` | 1 | s sim | FB-12 | G |

### Visual/behavioural checklist (verification)
- Every [RB §9] line and every FB test has an owner package and a runner entry by M1.

---

## 12. Open questions, suspicious content, sources

### 12.1 Verification queue (answer in the named package; record the answer here)

| # | Question | Owner | By |
|---|---|---|---|
| Q1 | Does `_post_import(scene)` receive `MeshInstance3D` with `ArrayMesh` surfaces for a skinned glb, so CUSTOM0 can be injected at import? | G0 | M0 |
| Q2 | Does the 4.5 scene import panel expose "Force Disable Compression" for meshes (the 4.5 docs page read for this plan does not mention it [T8])? Otherwise rebuild surfaces uncompressed in the import script | G0 | M0 |
| Q3 | Does Godot skip the skinning compute for hidden `MeshInstance3D`s? | G0 | M0 |
| Q4 | Private Jolt space: are static bodies queryable immediately or after one step; any `intersect_shape` result limits? | G0/G2 | M0 |
| Q5 | Half-float EXR import stays uncompressed and exact; `RenderingServer.texture_get_rd_texture` works for the painter inputs (**K**) | G3 | M1 |
| Q6 | Myotome weights beyond the ISNCSCI key muscles (**K**) | Q1 | M2 |
| Q7 | Diameters of the added vessels (**K**) | Q1 | M2 |
| Q8 | AgX tonemapper present in 4.5 (**K**: added in 4.4) | G0 | M0 |
| Q9 | Windows/Linux export templates are official downloads: user approval needed before M4 | Lead | M3 |
| Q10 | Cost of 24 head blend shapes when most weights are 0 | G6 | M1 |

### 12.2 Suspicious content

- **None encountered.** Fetched material was limited to raw files on `raw.githubusercontent.com` (Godot 4.5-stable class XML and docs source, Godot `gltf_document.cpp`, Blender 5.0.0 `uvedit_unwrap_ops.cc`, the upstream glTF-Blender-IO `__init__.py`) and local files (the project's docs and code, the glTF exporter bundled with the local `bpy`). All were treated as data; none contained instructions directed at the reader.
- WebSearch was unavailable (session budget already 200/200). WebFetch to `docs.blender.org`, `www.ncbi.nlm.nih.gov`, `en.wikipedia.org`, `radiopaedia.org`, `www.physio-pedia.com` and `asia-spinalinjury.org` returned `EGRESS_BLOCKED`; no content was received from them.
- No shell commands were run, nothing was downloaded, installed or executed, and no code was copied from the web into the project. This document contains no install commands and no links to executables.

### 12.3 Sources

Technical (read for this plan):
- [T1] Godot 4.5 command-line reference (`--headless`, `--import`, `--script`, `--write-movie`, `--fixed-fps`, `--quit-after`, `--gpu-profile`, `--rendering-driver`): https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/editor/command_line_tutorial.rst
- [T2] `SkeletonModifier3D` 4.5-stable (`_process_modification_with_delta(delta)`; `_process_modification` deprecated): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/SkeletonModifier3D.xml
- [T3] `PhysicalBoneSimulator3D` 4.5-stable (inherits SkeletonModifier3D; `physical_bones_start_simulation(bones)`): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/PhysicalBoneSimulator3D.xml
- [T4] `PhysicalBone3D` 4.5-stable (`_integrate_forces`, `custom_integrator`, joint types, `body_offset`, `joint_offset`): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/PhysicalBone3D.xml
- [T5] `Mesh` 4.5-stable (`ARRAY_CUSTOM_RGBA_FLOAT`, `ARRAY_FORMAT_CUSTOM0_SHIFT`, `ARRAY_FLAG_COMPRESS_ATTRIBUTES` = RGBA16UNORM positions, 8-bone flag): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/Mesh.xml
- [T6] `Performance` 4.5-stable (render, physics and pipeline-compilation monitors; `add_custom_monitor`): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/Performance.xml
- [T7] `RenderingServer` 4.5-stable (`viewport_set_measure_render_time`, `viewport_get_measured_render_time_cpu/gpu`, `call_on_render_thread`, `get_rendering_device` null in headless): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/RenderingServer.xml
- [T8] Godot 4.5 scene import configuration (`_post_import(scene)` must return the scene; tangents, LODs, shadow meshes, named skins): https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/assets_pipeline/importing_3d_scenes/import_configuration.rst
- [T9] Godot 4.5-stable glTF importer (`extras` stored as `set_meta("extras", …)` on nodes and resources): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/modules/gltf/gltf_document.cpp
- [T10] glTF exporter bundled with the local `bpy` 5.0.1 (add-on version 5.0.21): `/usr/local/lib/python3.11/dist-packages/bpy/5.0/scripts/addons_core/io_scene_gltf2/__init__.py` (option names; `export_apply` "prevents exporting shape keys") and `blender/exp/primitive_extract.py` (lines 85–88 `x,y,z -> x,z,-y`; lines 1419–1423 `u,v -> u,1-v`)
- [T11] Upstream glTF-Blender-IO exporter options (main branch, 5.3.32; same option names): https://raw.githubusercontent.com/KhronosGroup/glTF-Blender-IO/main/addons/io_scene_gltf2/__init__.py
- [T12] Blender 5.0.0 UV operators (`ANGLE_BASED`, `CONFORMAL`, `MINIMUM_STRETCH`; pack shape and margin methods): https://raw.githubusercontent.com/blender/blender/v5.0.0/source/blender/editors/uvedit/uvedit_unwrap_ops.cc

Project documents: [`REALISM_BIBLE.md`](REALISM_BIBLE.md) (all medical, forensic and physiological numbers, cited `[RB §x]`), [`research/06_game_gore_tech.md`](research/06_game_gore_tech.md) (R06: engine facts, budgets), [`research/05_body_anatomy_reference.md`](research/05_body_anatomy_reference.md) (R05: ANSUR II hand and foot sizes), [`research/04_neuro_death_eyes.md`](research/04_neuro_death_eyes.md) (R04 §6: ISNCSCI key muscles, dermatome anchors, cord levels), and the head project [`blender/gore_head/CONTRACT.md`](../../blender/gore_head/CONTRACT.md), `anatomy.py`, `materials.py`, `gore.py`, `build.py`, `gh_common.py`.
