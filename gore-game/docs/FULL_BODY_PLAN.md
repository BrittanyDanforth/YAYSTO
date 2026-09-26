# Gore Head — Full-Body Build Plan (technical direction)

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
| D16 | Audio | Offline synthesis in Python + numpy (already installed for `bpy`) → WAV banks; runtime `AudioDirector` | No downloaded sounds; real-time GDScript synthesis is too slow | AudioStreamGenerator voices |
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
| Room | Interior x −3…+3, z −1.8…+4.2, y 0…3.0 | Fits the 8 × 8 m floor splat map [RB §8.3] |
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
      │ LOC / cord ≥ T1 lesion / brainstem / leg failure / faint       hemiparesis or ataxia:
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
gore-game/assets/generated/audio/  *.wav (tools/audio_gen)        ├ MotorController (PD, 60 Hz) + behaviours
                                                                  ├ EyeModifier / FaceController / SkinState
                                                                  └ RevealManager, FractureManager, XRay
```

### 2.2 Runtime scene tree (one subject)

```
Subject (Node3D, subject.gd)                      facade: apply_hit(), vitals, signals
├── Model (instance of GB_Subject.glb)
│   └── GB_Armature (Skeleton3D)                  modifier_callback_mode_process = PHYSICS
│       ├── GB_Head, GB_Body, GB_Shorts, GB_Eyes, GB_EyeFX, GB_Mouth, GB_BrowLash   (outer, layer 2)
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
7. **Morphology** (`gunshot_morph.gd`): wound record with per-layer radii, collar, range-of-fire marks, fracture set, exit shape [RB §2.1].
8. **Dispatch**: WoundStore.add → GPU buffers; Painter.queue (soot/stipple/collar/blood); Physiology.inject (bleed sites, organ, cord, brain); Vfx.spatter (back/forward, hero drops); Fractures; Reveal; Audio cue; case-log entry.

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
| Audio director | per frame | Main | ≤ 0.1 ms | E |

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
- Hole, first blood, spatter and sound all appear on the impact frame; nothing waits for a physiology tick.
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
- **Pre-fractured variants** (Blender B3): skull vault burst ×3 (left, right, top exit direction; 20–80 Voronoi fragments), femur/tibia/humerus/radius-ulna shaft patterns (transverse, oblique, butterfly, comminuted; 8–20 fragments), rib segment breaks. At runtime the intact piece is hidden (vertex collapse by piece ID) and the variant shown; fragments ≥ 20 mm that leave become Jolt debris (≤ 48 active) and freeze into MultiMesh when asleep [RB §8.4].
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

The room is a set of known planes and boxes. At launch each hero drop solves its ballistic flight (drag-free parabola with the bible's terminal-velocity clamp) against the room planes in closed form, then casts **one** Jolt shape-cast along 4 chords of the arc against dynamic objects (subject, debris, props). The earliest hit gives the landing time and point; the drop is drawn along the analytic path and lands exactly then: wall → decal (stain 3–5.5 × drop Ø, L/W = 1/sin α), floor → splat map, subject → paint [RB §3.11]. Cost: ~5 µs per drop at launch, zero per frame.

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
| `hero_drop_chords` | 4 | per drop | One shape-cast at launch | E |

### Visual/behavioural checklist (vessels and bleeding)
- A track that misses every named vessel bleeds only as tissue ooze; a track through the femoral triangle jets. Players who know anatomy can predict it [RB §8.3].
- The jet starts from the lumen position, pulses a fraction of a second after each heartbeat, weakens and quickens as shock deepens, and stops within 1–2 beats of arrest [RB §9 #21–22].
- Raising a bleeding forearm above the heart nearly stops venous flow; a hanging limb bleeds more [RB §9 #23].
- Small trunk wounds bleed little outside while the chest or abdomen fills [RB §9 #27].

---

### 3.5 Reveal and X-ray

- **RevealManager** keeps, per inner mesh piece (muscle-shell surface, bone piece ID, organ ID, vessel class, brain, cord), the rest-space AABB. A piece becomes visible when any **open** wound SDF lies within `layer_reveal_radius` of it; pieces inside one mesh are shown or hidden by an instance-uniform bitmask that collapses hidden vertices in `vertex()` [RB §8.1] (no discard cost). Inner meshes never cast shadows.
- **X-ray mode** (player toggle or kill-cam): skin/cloth write stencil ref 1 in the opaque pass; X-ray variants of skeleton, organs, vessels, cord and the rest-space bullet track (glowing capsule) draw in the transparent pass with `depth_test_disabled`, stencil `read`, `compare_equal` (4.5 spellings) [RB §8.2]; bones emissive `#C8D4E0`, fractures brighter, severed vessels red; skin swaps to a Fresnel rim (α 0.1–0.25). Time scale 0.05–0.1 for the bullet, 1.5–3 s window, `AudioServer.playback_speed_scale` matched [RB §8.1, R06 §11].

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
| Face | 20 head blend shapes (`AU01/02/04/06/07/09/10/12/15/20_L/R`, `mouth_slack_L/R`, `swell_periorbital_L/R`) + `jaw` and `tongue` bones | FaceController: pain AU4+6/7+9/10+43, fear AU1+2+4+5+7+20+26, central palsy (lower face only), peripheral palsy, jaw drop 10–30 mm within 5–30 s at death [RB §5.6] |
| Skin state | Instance uniforms `pallor`, `cyanosis`, `mottling`, `sweat`, `flush_level` (dermatome index below which neurogenic flush shows), plus the livor atlas | SkinState ≤ 1 Hz from physiology [RB §5.6, §6.4] |
| Pupil light reflex | Illuminance at each eye from the scene lights (point-to-light attenuation + ambient) and the penlight tool | latency 200–250 ms, constrict ~1 s, redilate 2–4 s [RB §5.2] |

### Simulation parameters (eyes and face)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `eye_instance_uniforms` | 12 of 16 | — | Room for 4 more | [RB §5] V |
| `iris_plane_y / cornea_ior` | −0.0101 / 1.376 | m / — | Head materials constants | `materials.py` |
| `face_blend_shapes` | 20 | — | Head mesh only | G |
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
| Paint/VFX/audio queueing | — | small | 0.1 ms |
| **Total pistol shot** | | | **≈ 0.7–1.4 ms (budget 2)** |

The private rest space is created with `PhysicsServer3D.space_create()` and made active; static bodies hold: skin/shorts trimeshes (LOD0 render geometry, rest pose), bone meshes (decimated, concave, ≤ 20k tris total), organ meshes, vessel and cord capsules, brainstem capsules; collision layers separate classes. **Spike in G0**: confirm that Jolt queries see bodies in a private space one physics frame after creation, and measure the costs above.

### 3.8 Audio from code

Offline generator `gore-game/tools/audio_gen/` (python3 + numpy + the standard-library `wave` module; nothing installed): gunshots (N-wave crack + muzzle blast + early reflections and a tail from an image-source impulse response of the 6 × 6 × 3 m tiled room), impacts (filtered noise + modal resonators for bone crack/snap/crunch), wet sounds (noise bursts with Minnaert bubble tones), torch (hiss loop, sizzle, fat spit), blood (drip on skin/cloth/tile/pool, patter, pour, spurt), body (falls, limb flops, head knock on tile), breathing and voice by source–filter synthesis (glottal pulse + noise through formant filters): normal/panting/gasp/agonal/stertor/gurgle/stridor/wheeze/hiss/suck/bubble, moan/groan/whimper/scream/cough/wet cough. 4–8 variations each, 44.1 kHz 16-bit mono WAV + `audio_manifest.json` (cue → files, gain dB, pitch range, bus). Levels from [RB §4.9] (screams 90–105 dB at 1 m, speech 62, shout 82).

### Simulation parameters (hit pipeline and audio)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hit_candidates_max` | 64 | — | `intersect_shape` max_results | E |
| `rest_space_tris` | skin+shorts ~78k, bones ≤ 20k | tris | Face index +~25 % memory | [RB §8.2] |
| `audio_format` | WAV 44.1 kHz 16-bit mono | — | Godot imports/compresses | G |
| `audio_variations` | 4–8 | per cue | | G |
| `scream_level` | 90–105 | dB @ 1 m | | [RB §4.9] C |

### Visual/behavioural checklist (hit pipeline and audio)
- A shotgun volley at close range never hitches the frame (pellet tracks merged, work spread over ≤ 2 frames).
- Every gunshot sounds like the tiled room (short bright reflections, ~0.4–0.6 s tail); the patter of spatter follows 30–300 ms later (R06 §8).
- Breathing sounds always match the respiratory state on screen; no death rattle in fast deaths [RB §4.9].

---

## 4. Budgets

### 4.1 Triangles and vertices (LOD0, subject)

| Mesh | Triangles | Visible | Notes |
|---|---|---|---|
| `GB_Head` (head + neck to the seam, lids, ears, lips, mouth lining) | 30,000 | always | Decimated from the 1.2 mm head; 20 blend shapes |
| `GB_Body` (5 surfaces: torso, arm_L, arm_R, leg_L, leg_R) | 44,000 | always | Hands 2k and feet 1.5k each included; 4 blend shapes |
| `GB_Shorts` | 4,000 | always | Solidified 1.2 mm |
| `GB_Eyes` + `GB_EyeFX` (tearline, occlusion) | 5,000 | always | |
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
| `GB_Subject.glb` | ≤ 40 MB | No images; morph targets dominate (head 20 × ~16k vertices) |
| Each 2,048² PNG | ≤ 12 MB | 8-bit; EXR only for position maps |
| `assets/generated/` total | ≤ 250 MB | Git-ignored except `manifest.json` (§5.7) |
| Audio banks | ≤ 40 MB WAV | ~300 files |
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

<!-- PART B -->
