# 06 — Gore Technology: AAA Techniques and a Godot 4.5 (Forward+) Implementation at 60 fps

Project: Gore Head (Godot 4.5, Forward+, GDScript + Godot shaders, Jolt physics, procedural assets from Blender).
Audience: rendering, VFX, physics, animation, tools and performance engineers.
Status: research reference v1, 2026-09-26. The subject is a fictional, procedurally generated adult only.

Companion documents in this folder:
- **01** Gunshot wound morphology and head-shot spatter.
- **02** Sharp, blunt and thermal injury, plus the skin colour palette.
- **03** Bleeding physiology, the vessel network and blood on surfaces.
- **04** Neurological injury, the death sequence, the eyes, and the physiology state machine.

This document is the engine-side design those documents point to (03 §12 says "see the tech doc"). The physiology numbers come from 01–04. This document decides how to render and simulate them in Godot at 60 fps.

---

## 0. Read this first

### 0.1 Evidence tags

| Tag | Meaning |
|---|---|
| **[S#]** | Read during this session. Section 18.1 gives the URL. Most of these are Godot engine source, the official Godot documentation source, or other GitHub-hosted primary material. |
| **[K-H] / [K-M] / [K-L]** | My own knowledge. H means high confidence (standard and widely repeated). M means medium (right in substance, but details may differ). L means low (plausible, weak basis). **[K-x Rn]** names a reference (Section 18.2) that I believe supports the claim. **I did not open Rn this session.** |
| **[D]** | Derived by arithmetic from other values. The working is shown. |
| **[E]** | Engineering estimate, such as a frame-time cost. **Profile it on the target hardware before relying on it.** |
| **[G]** | Game-design choice: a tuned value, with the reason given. |

### 0.2 Research method and limitations (important)

- **WebSearch was unavailable.** The first call returned "used its web search budget (200 of 200)". Other agents in this workflow had used the budget before this one started, so this agent made zero searches.
- **WebFetch reached only GitHub.** The egress proxy returned `EGRESS_BLOCKED` for every other domain I tried:
  - docs.godotengine.org and godotengine.org
  - en.wikipedia.org
  - gdcvault.com
  - 80.lv
  - cdn.akamai.steamstatic.com (Valve's papers)
  - advances.realtimerendering.com
  - gpuopen.com
  - developer.nvidia.com
  - arxiv.org
  - store.steampowered.com
  - jrouwe.github.io
  - web.archive.org
- **github.com and raw.githubusercontent.com worked.** I therefore verified the Godot facts against primary material:
  - the engine source (`godotengine/godot`), both `master` and the **`4.5-stable` tag** where the version mattered;
  - the official manual source (`godotengine/godot-docs`), which is what docs.godotengine.org renders;
  - the website data, including release dates (`godotengine/godot-website`);
  - the official demo projects.

  I also read:
  - the Jolt Physics documentation;
  - Raven Software's released GHOUL2 gore code (OpenJK);
  - the NetImmerse/Gamebryo format definitions (niftools), for Bethesda's dismemberment partitions;
  - several open-source gore, decal, slicing and ragdoll projects.
- **Consequences:**
  - The **Godot claims are well sourced ([S])**.
  - The descriptions of Dead Island 2, Sniper Elite, Mortal Kombat, The Last of Us Part II, RDR2/Euphoria and Dead Space come from my knowledge of public talks, interviews and play observation **[K-\*]**. Treat their implementation details as indicative only.
  - **All frame-time numbers are [E].**
- I cross-checked against the **4.5-stable** tag where master and 4.5 differ, for these items:
  - skinning compute shader
  - stencil mode names
  - BoneConstraint3D and LookAtModifier3D (present)
  - TwoBoneIK3D (absent)
  - SMAA
  - Jolt defaults

### 0.3 Targets and conventions

- **60 fps = 16.67 ms per frame.** Budget targets on the minimum-spec PC:
  - GPU ≤ 13.5 ms.
  - Main-thread CPU ≤ 12 ms.
  - The remaining ~3 ms is headroom for spikes. Gore is spiky: one shotgun blast triggers raycasts, paint, particles, decals and possibly a mesh swap in the same frame.
- **Minimum-spec GPU: GTX 1660** (6 GB GDDR5, 192 GB/s, ~5.0 FP32 TFLOPS). **Recommended: RTX 3060** (12 GB, 360 GB/s, ~12.7 TFLOPS) [K-H R23]. In rasterised games the RTX 3060 is roughly 1.7–2.0× faster than the GTX 1660 [K-M].
- **CPU reference:** 6-core desktop part (Ryzen 5 3600 / Core i5-10400 class) [G].
- **Resolution:** 1920×1080 native. Fallback: FSR 2.2 at 0.77 render scale on the 1660 (Godot offers FSR 1.0, FSR 2.2 and MetalFX) [S46].
- **Rest space:** the model space of the character mesh in its **bind (rest) pose**. All wound volumes, vessels, organs and paint brushes are stored in rest space so they stay attached to the correct tissue whatever the pose.
- Engine units are metres. Tables use mm where marked. Colours are approximate sRGB under D65. Shader maths is in linear space.

### 0.4 Executive summary (the decisions)

1. **Store wounds as data in rest space, not as decals.** Each wound is a signed-distance volume (capsule, round cone, ellipsoid or slab) plus paint events and physiology events. Godot skins meshes in a **compute pre-pass**, so `VERTEX` in `vertex()` is already skinned [S2, S3]. Bake the rest-pose position into `CUSTOM0` at import so shaders can evaluate wounds in rest space.
2. **Render damage in three tiers:**
   - **(a) UV-space damage atlases**, painted by compute shaders: blood film, clot, bruise, burn, soot, abrasion and wetness.
   - **(b) Wound SDFs evaluated in the skin shader:**
     - wound margins and abrasion collars;
     - analytic "cavity" shading for small holes (≤ ~12 mm);
     - `discard` for large holes.
   - **(c) Real geometry, enabled on demand:**
     - a muscle shell, the skeleton, the skull, the brain and the organs;
     - pre-fractured bone variants;
     - authored cut caps.
3. **Do not use Godot `Decal` nodes on the character for anything persistent.**
   - Decals are re-projected every frame from the current view-space position through the decal box [S25]. They therefore slide on deforming skin and project straight through a limb.
   - Keep `Decal` for walls and floors, and for short-lived impact flashes parented to a bone.
4. **Dismember with pre-split zones and authored caps** (the Fallout pattern [S61]). Allow runtime slicing only for knife incisions, in C++ on a worker thread. **With a pistol, shotgun, knife, fist, hammer and torch, real limb amputation is rare.** Prioritise open wounds, fractures and avulsions (tissue torn away) over full severing.
5. **Blood is driven by the vessel graph (doc 03).** Each wound's flow rate picks the VFX:
   - **ooze:** paint only;
   - **drip:** surface agents plus drops;
   - **stream:** a trail;
   - **arterial jet:** a pulsed ribbon plus breakup drops.

   Rendering duties:
   - **Fine mist:** GPU-only.
   - **Drops that leave stains:** simulated on the CPU with raycasts, then written as decals or into a floor "splat map".
   - **Pools:** a cellular spread on the floor splat map.
6. **Ragdolls:** `PhysicalBoneSimulator3D` with 17–19 `PhysicalBone3D` bodies on Jolt. Physiology drives the ragdoll's muscle tone through PD (proportional-derivative, i.e. spring-damper) torques applied in `_integrate_forces`. Godot 4.5 does not let scripts reach the PhysicalBone3D joint motors; `get_joint_rid()` is slated for 4.8 [S48]. Partial ragdolls use `influence` blending [S4, S11].
7. **X-ray kill cam** (Sniper Elite style): the skin writes the stencil, and the transparent inner-anatomy materials read it. Godot 4.5 supports stencil, but reads are allowed **only in the transparent pass** [S1, S44].
8. **Budget:**
   - ≤ 20k live GPU particles on the 1660.
   - ≤ 6 jets.
   - ≤ 32 surface-flow agents.
   - ≤ 200 visible decals. The cluster limit is 512 elements per view, shared with lights [S6].
   - ≤ 48 active rigid debris bodies; asleep ones are frozen into MultiMesh.
   - One hero victim with full gore.

   A runtime governor scales these from measured GPU time.
9. **Languages:** use GDScript for glue. Use a C++ GDExtension (or C#) for the hit pipeline, the surface-flow agents, mesh slicing and the vessel-graph solve.

---

## 1. How AAA games implement gore (survey)

### 1.1 Taxonomy of techniques

| Technique | Canonical examples | How it works | Strengths | Weaknesses | Fit in Godot 4.5 |
|---|---|---|---|---|---|
| Hit zones plus authored damage swaps | Soldier of Fortune (GHOUL), Doom Eternal, RE2 remake | Body split into zones. Damage at a zone swaps in or reveals pre-made damaged geometry and textures | Art-directed, cheap | Repetitive, fixed locations | Easy: visibility toggles, surface swaps |
| Projected gore marks on the posed mesh | GHOUL2 (Jedi Academy) [S59, S60] | At hit time, gore UVs are computed for the existing triangles around the hit. An extra "gore surface" is drawn on top and deforms with the skeleton | Sticks to skin. Cheap | Flat (no depth). Stretches on grazing surfaces | Possible, but UV-atlas painting is better (tier a) |
| Shader clip volumes plus interior meshes | Left 4 Dead 2 [K-M R1] | Pixel shader discards inside a bone-relative ellipsoid. A pre-made wound-interior mesh fills the hole | Real holes and silhouettes with no mesh edits | Few wounds per character. Interior is generic | Good: `discard` plus inner meshes (tier b/c) |
| Pre-split partitions plus caps | Fallout 3/NV/4, Skyrim [S61, K-H R14], Dead Space | Triangles pre-partitioned per body part. Severing hides partitions, shows authored section caps and spawns the limb | Robust, cheap, looks authored | Cuts only at fixed places | Good: vertex-shader collapse or modular surfaces |
| Layered anatomy ("onion") | Dead Island 2 FLESH, Dead Space remake, RE2, TLOU2 [K-M] | Skin, fat, muscle, bone and organ layers, revealed progressively by damage masks or geometry | Believable depth. Supports damage types | Asset-heavy | Good: tiers a–c |
| X-ray inner-anatomy view | Sniper Elite, Mortal Kombat [K-H R10, R11] | A presentation mode: the body goes translucent and skeleton/organs render with authored fracture/rupture states | Spectacular, readable, forensic-looking | Cinematic only | Good: stencil (4.5) plus inner meshes |
| Texture-space (UV) damage painting | Rockstar RAGE ped damage [K-M], Unity SkinnedMeshDecals [S62] | Decals rendered into a per-character texture in UV space, so they deform with the mesh | Persistent, sticks to skin, unlimited count | Needs non-overlapping UVs. Seams need dilation. VRAM | Good: compute plus Texture2DRD (tier a) |
| Active (powered) ragdoll | Euphoria in GTA IV/V, RDR, RDR2 [K-H R7] | Physics body with simulated muscles tracking goals (balance, clutch wound, writhe) | Unique, physical death behaviour | Hard to tune. Middleware | Partial: PD-driven PhysicalBone3D (Section 10) |
| Runtime mesh slicing | Metal Gear Rising: Revengeance [K-H], EzySlice/godot-slicer [S63, S64] | Split triangles by a plane, triangulate the cross-section cap | Any cut anywhere | CPU cost. Convex-only in simple libraries. Skinning attributes are hard | Only in C++. Limit to knife incisions |

### 1.2 Soldier of Fortune (GHOUL) and GHOUL2 gore marks

- **Soldier of Fortune (Raven, 2000)** used the GHOUL model system. Its characters were divided into **26 "gore zones"** that could show authored wounds or lose parts [K-M R9]. Soldier of Fortune II (2002, GHOUL2) is usually quoted with 36 zones [K-L R9].
- **GHOUL2 as released in the OpenJK code base** shows how Raven put persistent gore on animated models [S59, S60]:
  - **Placement.** At hit time the code builds an orthonormal basis (s, t axes) around the shot ray. For every vertex of the **posed** mesh it computes `s = dot(v − rayStart, s_axis) + 0.5` and the same for t. These become gore texture coordinates.
  - **Triangle selection.** Triangles with every vertex outside [0, 1] are dropped. An optional front- or back-face filter uses the sign of `dot(ray, triangle normal)`. "Radius" traces add a third axis along the ray to limit depth.
  - **The gore is a new surface** that reuses the mesh's own triangle indices with the new UVs, drawn with a gore shader. It deforms with the skeleton for free.
  - **Limits and lifetime:**
    - `MAX_GORE_RECORDS 500`, `MAX_GORE_VERTS 3000` and `MAX_GORE_INDECIES 6000` per operation.
    - Each record has a delete time, a fade time, a fade-RGB flag and growth parameters (grow start and end time, grow factor, start-scale fraction).
    - UVs are stored per level of detail (`MAX_LODS 8`).
- **Lesson.** Projecting onto the posed mesh and keeping the result in mesh space (not world space) is the key to wounds that stay on deforming skin. Our rest-space design generalises this.

### 1.3 Left 4 Dead 2 wounds [K-M R1]

- Vlachos (Valve, GDC 2010), "Rendering Wounds in Left 4 Dead 2":
  - Each infected can carry a small number of wounds (I recall two).
  - A wound is an **ellipsoid in a bone's local space**.
  - The body pixel shader **discards** fragments inside the ellipsoid.
  - A **pre-authored wound mesh** (flesh interior, ribs and so on) is drawn in the cavity, so the silhouette really has a hole.
  - Colour and texture variation keep it from looking repetitive.
- **Lesson.** Signed-distance clipping plus authored interior geometry gives real holes without changing the mesh. We generalise this to many SDFs per character and to layered interior meshes.

### 1.4 Bethesda: VATS and dismemberment [K-H R14], [S61]

- **VATS** (Fallout 3, New Vegas, 4) pauses or slows time and offers per-part targeting (head, torso, arms, legs) with a hit chance for each. Each limb has its own health and becomes "crippled" at zero. Kill shots may sever or explode parts.
- **Data.** The niftools format definition has an enum `BSDismemberBodyPartType`, described as **"Biped bodypart data used for visibility control of triangles"** [S61]. It lists:
  - body sections: `BP_TORSO`, `BP_HEAD`, `BP_HEAD2`, `BP_LEFTARM/2`, `BP_RIGHTARM/2`, `BP_LEFTLEG/2/3`, `BP_RIGHTLEG/2/3`, `BP_BRAIN`;
  - **section caps** `BP_SECTIONCAP_*` (values 101–113);
  - **torso caps** `BP_TORSOCAP_*` (201–213);
  - torso sections `BP_TORSOSECTION_*` (1000–9000).

  So each skinned mesh is pre-partitioned. Severing hides a partition, shows the matching caps on the body and on the severed piece, and spawns the limb.
- **Lesson.** Pre-split partitions with caps are cheap, predictable and artist-controlled. Our dismemberment copies this (Section 9).

### 1.5 Sniper Elite X-ray kill cam [K-M R10]

- **Sniper Elite V2 (2012)** introduced the slow-motion bullet camera and X-ray kill cam:
  - At impact, the body becomes translucent to show the skeleton.
  - Bones break using pre-fractured variants and fragments.
- **Sniper Elite 3 (2014)** added internal organs (heart, lungs, liver, kidneys, stomach and others).
- **Later titles** (4 in 2017, 5 in 2022, Resistance in 2025) added detail, including muscle layers [K-L for per-title specifics].
- **Presentation:**
  - It is cinematic: one victim at a time, a replaced body render, and damage states picked from the bullet path.
  - Time is slowed to a small fraction and the camera tracks the bullet.
  - The X-ray lasts ~1–3 s before returning to normal speed [K-M].
- **Lesson.** X-ray is a presentation mode that can reuse our inner anatomy meshes and pre-fractured bones. It is cheap with the stencil support added in 4.5 (Section 11).

### 1.6 Mortal Kombat X-ray [K-H R11]

- Mortal Kombat (2011) introduced "X-Ray" special moves. Mortal Kombat X (2015) kept them. Mortal Kombat 11 (2019) replaced them with Fatal Blows and added X-ray inserts to Krushing Blows.
- They are fully authored cinematics: separate skeleton and organ models, camera cuts, slow motion and exaggerated fractures.
- **Lesson.** A visual reference only. Its forensic realism is poor; for example, it shows skulls shattering from single punches.

### 1.7 Dead Island 2 FLESH [K-M R8]

- **FLESH** stands for "Fully Locational Evisceration System for Humanoids" (Dambuster Studios, Unreal Engine 4, 2023). Developer material and interviews describe:
  - procedural, location-specific wounds;
  - anatomical layers (skin, fat, muscle, organs, bone);
  - damage-type effects:
    - blunt weapons bruise and break bones, with visible limb deformity;
    - sharp weapons cut;
    - caustic damage dissolves flesh down to bone;
    - fire chars;
    - electricity burns;
  - dismemberment of limbs, head and jaw;
  - damage that persists on the body.
- **Implementation details are not public in any source I could open.** My understanding [K-L]:
  - layered meshes with shader-driven, per-region damage masks;
  - dismemberment from pre-split pieces;
  - procedurally varied "meat" materials.
- **Lesson.** The AAA benchmark for "realistic gore" is a layered-anatomy plus damage-mask design. It does not rely on runtime geometry cutting.

### 1.8 Dead Space (2023), Resident Evil 2 (2019), Doom Eternal (2020) [K-M R15, R16, R24]

- **Dead Space remake (Motive, Frostbite):** a "peeling" system. Enemies have skin, flesh and bone layers that weapons strip progressively. Strategic dismemberment remains the core mechanic.
- **Resident Evil 2 (RE Engine):** zombies accumulate damage by location. Chunks of flesh are removed to expose bone. Limbs sever after damage thresholds.
- **Doom Eternal (id Tech 7):** "destructible demons". Authored, progressive damage states per body region expose skeleton and armour.
- **Lesson.** The industry pattern is authored layers, per-region damage accumulation and pre-split dismemberment.

### 1.9 The Last of Us Part II (2020) [K-L R12]

- It shows detailed, persistent gunshot damage:
  - shotgun blasts remove chunks of flesh, limbs, and parts of the face and jaw;
  - wound marks, bleeding and blood pools;
  - dying NPCs with gasping and animated reactions.
- Technical details are not public in sources I could open. I believe it combines authored per-region damage meshes, dynamic wound marks and pooling. This is the benchmark for **believable dying behaviour and sound**, not for simulation.

### 1.10 Red Dead Redemption 2 and Euphoria [K-M R7, R13], [S67]

- **Euphoria** (NaturalMotion "Dynamic Motion Synthesis") has been used in GTA IV (2008), Red Dead Redemption, GTA V and RDR2. It simulates the body and a motor controller in real time, with behaviours such as balance, stagger, catching a fall, writhing and clutching a wound.
- The GTA V scripting library (ScriptHookVDotNet) exposes Euphoria message helpers [S67], including:
  - `ActivePose`, `ApplyImpulse`, `ApplyBulletImpulse`;
  - `BodyRelax`, documented as "Set the amount of relaxation across the whole body; used to collapse the character into a rag-doll-like state";
  - `ConfigureBalance` and `ConfigureBullets`.

  Other behaviour names documented by modders include Shot, ShotConfigureArms (wound reaching and clutching), BodyWrithe, InjuredOnGround, StaggerFall, CatchFall, HighFall and Electrocute [K-M].
- **Observed RDR2 behaviour** [K-M]:
  - wound marks persist on skin and clothing;
  - blood pools grow under bodies;
  - leg wounds cause limping; arm wounds make NPCs drop weapons;
  - wounded NPCs crawl, writhe and plead;
  - bleeding causes delayed deaths;
  - bodies decompose over in-game days.
- **Lesson.** Death behaviour must be physical and tone-driven, not a canned animation. Our analogue is the physiology-driven powered ragdoll (Section 10).

### 1.11 Gore Box, Kick the Buddy, Hitman, Metal Gear Rising [K-L R19–R21], [K-H]

- **Gore Box** (sandbox): ragdolls, dismemberment and blood decals with many weapons. Realism is modest.
- **Kick the Buddy** (mobile): a cartoon ragdoll. Not a realism reference.
- **Hitman** (Glacier engine): convincing ragdolls, blood pools under bodies, blood on clothing and cloth simulation. Forensic detail is low.
- **Metal Gear Rising: Revengeance (2013) "Blade Mode"**: real-time planar slicing of enemies and objects. It is the classic proof that runtime slicing works **when the whole game is designed around it** [K-H].

### 1.12 Design lessons for Gore Head

1. Every successful AAA gore system is **mostly authored layers plus data-driven masks**, not general-purpose simulation. Put the simulation budget into physiology (docs 03/04) and tissue placement, and use authored assets for the look.
2. Wounds must live in **mesh (rest) space**. Anything projected in world space slides.
3. Real holes need **clip volumes plus interior geometry**. Painting alone looks flat.
4. Dismemberment is best done with **pre-split zones and caps**.
5. Death behaviour depends on **muscle-tone control** of a physical body.
6. Forensic realism differs from the AAA norm. Real gunshot entrances are small (01 §2). External bleeding is often modest (03 §4.5). Limbs rarely come off with these weapons (Section 9.1). **The realism budget should go into small, correct detail, not volume.**

### Simulation parameters (survey-derived defaults)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `gore_zone_count` | 16–26 (hit/damage regions) | zones | SoF used 26. Our ragdoll has 17–19 bodies. Map several zones per body where needed (face vs scalp) | [K-M R9], [G] |
| `max_gore_records_per_char` | 500 (reference) | records | GHOUL2 limit. We use UV painting, so the limit applies to SDF wounds only (64 per character, Section 4) | [S60] |
| `projected_mark_max_verts` | 3,000 (reference) | vertices | GHOUL2 per-operation cap | [S60] |
| `wound_grow_time` | 0.2–2.0 | s | GHOUL2 supports growth. Use it for bleeding margins and bruise bloom (doc 02) | [S59], [G] |
| `xray_duration` | 1.5–3.0 | s (real time) | Sniper Elite style | [K-M R10], [G] |
| `dismember_zones` | 12–16 per body side (Section 9) | zones | Fallout-style partitions and caps | [S61], [G] |

### Visual/behavioural checklist (survey)
- Wounds stay exactly where they were made, however the body moves or bends.
- Large wounds are real holes with depth and layered interior tissue. Small ones are small and precise.
- The body reacts physically and differently every time. No canned death animation plays twice.
- The player can examine a wound closely. Nothing looks like a sticker (flat, sliding or projected through the limb).

---

## 2. Godot 4.5 engine facts that shape the design (verified)

### 2.1 Versions (as of 2026-09-26)

| Version | Stable date | Relevant content | Source |
|---|---|---|---|
| 4.4 | 3 Mar 2025 | Jolt added as a built-in alternative 3D physics engine | [S21], [S5] |
| **4.5** | **15 Sep 2025** (4.5.1: 15 Oct 2025; 4.5.2: 19 Mar 2026) | **Stencil buffer support** in spatial shaders and BaseMaterial3D; SMAA; BoneConstraint3D; LookAtModifier3D (present) | [S21], [S24], [S44], [S45], [S46] |
| 4.6 | 26 Jan 2026 | **Jolt becomes the default for new 3D projects**. New IK system: IKModifier3D, TwoBoneIK3D, SplineIK3D, FABRIK3D, CCDIK3D, JacobianIK3D. SSR overhaul (full- and half-resolution modes) | [S21], [S22] |
| 4.7 | 18 Jun 2026 (4.7.2: 18 Aug 2026) | AreaLight3D, HDR output, clearcoat fixes, per-pass uniform pools for speed, particle scale/rotation improvements | [S21], [S23] |
| 4.8 | in development | `PhysicalBone3D.get_joint_rid()` (PR 112002). Jolt 6DOF spring max force/torque exposed (PR 119332) | [S48], [S47] |

**Recommendation:**
- Build on 4.5 as requested.
- **In 4.5, select Jolt explicitly** under Project Settings > Physics > 3D > Physics Engine. It became the default for new projects only in 4.6 [S22] [K-M for the menu path].
- Keep the code free of 4.6+ APIs. Plan a move to 4.6 or later if built-in IK (wound clutching) or the new SSR (blood pools) is wanted.

### 2.2 Skinning happens before your vertex shader: `VERTEX` is post-skin

- In the RenderingDevice renderers (Forward+ and Mobile), `servers/rendering/renderer_rd/shaders/skeleton.glsl` is a **compute shader** (`#[compute]`, local size 64) [S2, S3]:
  - It applies blend shapes, then weighted bone matrices (up to **8 bones per vertex**).
  - It writes positions plus octahedral-encoded normals and tangents into a **destination vertex buffer (`dst_vertices`)**.
  - This is identical in `4.5-stable` [S3].
- The spatial `vertex()` function therefore receives **already-skinned** `VERTEX`, `NORMAL` and `TANGENT` in model space [S1, S2]. `BONE_INDICES`, `BONE_WEIGHTS` and `CUSTOM0–3` are read-only vertex built-ins [S1, S44].
- **Consequences:**
  - A spatial shader has no built-in access to bone matrices and no built-in rest position [K-M].
  - To evaluate wounds in rest space, **store the rest position per vertex in `CUSTOM0`** (RGBA float) at import. Use `CUSTOM0.w` for a segment ID (Section 9), then pass it to `fragment()` as a varying.
  - Do this in an `EditorScenePostImport` script that copies `ARRAY_VERTEX` into `ARRAY_CUSTOM0`. It can also be done through extra UV sets from Blender (`CUSTOM0.xy = UV3`, `CUSTOM0.zw = UV4` [S1]), but Blender's glTF exporter flips V, so that path needs a correction [K-M].
- `MeshInstance3D.bake_mesh_from_current_skeleton_pose()` exists but "Mesh data needs to be received from the GPU, stalling the RenderingServer" [S34]. Use it only rarely, for example once to freeze a severed part, and never per frame.

### 2.3 Getting wound data into shaders

| Mechanism | Limits | Use for | Source |
|---|---|---|---|
| Material uniform arrays (`uniform vec4 w[192]`) | Uniform buffer up to **65,536 bytes (4,096 vec4)** on desktop. Arrays are allowed; structs are not | Per-character wound list (64 wounds × 3 vec4 = 3 KB). Requires a **unique ShaderMaterial per character**, which is fine for 1–3 characters | [S8] |
| Per-instance uniforms (`instance uniform`) | **Practical maximum 16 per shader. Scalars and vectors only: no arrays, no textures.** Set with `set_instance_shader_parameter()` | Per-body scalars: pallor, cyanosis, wetness, segment-visibility bits, eye state (pupil mm, corneal opacity) | [S8] |
| Data textures (Image → ImageTexture, or Texture2DRD) | Any size. Update cost is proportional to upload size | >64 wounds; a 3D wound-lookup grid; vessel/organ lookup | [S37], [K-H] |
| Global uniforms (Project Settings > Shader Globals; `global_shader_parameter_set`) | Project-wide | Arena blood splat map and bounds, `time_minutes`, X-ray amount | [S8]; sampler support [K-M] |
| `Texture2DRD` written by compute on the **main** RenderingDevice | Must run through `RenderingServer.call_on_render_thread()`. A local RenderingDevice "cannot draw to the screen nor share data with the global RenderingDevice" | Damage atlases, floor splat map, flow | [S37], [S38], [S39] |

### 2.4 Stencil (new in 4.5)

- 4.5-stable defines spatial stencil modes [S44]:
  - `read`, `write`, `write_depth_fail`;
  - `compare_{always, less, equal, less_or_equal, greater, not_equal, greater_or_equal}`.

  The current master manual spells the depth-fail mode `write_if_depth_fail` [S1]. **Use the 4.5 spelling.**
- **"You can only read from the stencil buffer in the transparent pass. Any attempt to read in the opaque pass will fail."** [S1] The manual names outlines, **X-ray** and portals as intended uses [S1].
- BaseMaterial3D also exposes a stencil mode; the official ragdoll demo draws outlines with it [S52].
- **Consequences:**
  - Stencil is ideal for the X-ray kill cam (Section 11).
  - It **cannot** build opaque "portal" wound holes (for example, "draw the inside only where the skin was cut") in the opaque pass. Holes use `discard` instead (Section 5).

### 2.5 Decals

- **Forward+ renders decals with clustering.** The default limit is **512 clustered elements per camera view**, shared by omni, spot and area lights, decals and reflection probes [S6]. The setting is `rendering/limits/cluster_builder/max_clustered_elements` [K-M for the name].
- **Screen coverage matters more than decal count** for performance. Use distance fade [S6]. Defaults are `distance_fade_begin` 40 m and `distance_fade_length` 10 m [S12].
- **Decals are projected every frame.** The fragment shader transforms the current view-space position by the decal's matrix and tests it against the box [S25]:
  - On a skinned character, a decal therefore **does not follow skin deformation**. Parenting it to a `BoneAttachment3D` gives only rigid following.
  - A decal also **projects through the whole box**, onto the far side of a limb. `normal_fade` (0–1) and `upper_fade`/`lower_fade` (default 0.3) reduce this [S12, S25].
- **Decals cannot run custom shaders.** They affect albedo, normal, ORM and emission only [S6]. They **cannot affect transparency**, so they cannot cut holes [S12].
- Decal textures live in a shared atlas (sRGB for albedo and emission, linear for normal and ORM) [S25].
  - Adding a new unique texture at runtime marks the atlas dirty and rebuilds it [K-M]. **Preload every blood decal texture during loading.**
  - Changing `modulate`, size or rotation is free.

### 2.6 GPU particles

- Collision shapes are box, sphere, heightfield and SDF [S7]:
  - **The SDF must be baked in the editor.** "No runtime baking method exists for exported projects" [S16]. Resolution runs 16³ to 512³ [S16], and SDF has "larger" overhead than a heightfield [S7].
  - **The heightfield updates at runtime** ("When Moved" or "Always"), at resolution 256² to 8,192² (default 1,024²). It can follow the camera and filters meshes by layer mask [S17, S19].
- **The engine caps collision shapes and attractors at 32 each per particle system** (`MAX_COLLIDERS = 32`, `MAX_ATTRACTORS = 32`) [S19].
- Particles collide **only** with `GPUParticlesCollision3D` nodes, not with physics bodies or skinned meshes [S15]. `COLLISION_RIGID` supports bounce and friction (0–1). `COLLISION_HIDE_ON_CONTACT` is also available [S18].
- **Sub-emitters** have modes constant, at start, at end and at collision [S18]:
  - They can chain [S41].
  - The total number of live sub-particles is **capped by the sub-emitter's `amount`** [S41].
  - Explosiveness has no effect on a sub-emitter [S41].
- **Changing `amount` restarts the system.** Vary the count with `amount_ratio` instead [S14]. CPU-controlled spawning uses `emit_particle()` with emit flags [S14].
- **Trails** use "a mesh skinning system" with RibbonTrailMesh or TubeTrailMesh (`trail_enabled`, `trail_lifetime`) [S14].
- **There is no GPU → CPU event channel.** A particle landing cannot spawn a `Decal` node or a physics event [K-H]. Section 8.4 gives the workarounds.

### 2.7 Compute shaders and render-to-texture

- Compute shaders run only on the RenderingDevice renderers (Forward+ and Mobile) [S9].
- **Sharing a texture with materials:**
  1. Create it on the global device from `RenderingServer.get_rendering_device()`.
  2. Do the work inside `RenderingServer.call_on_render_thread()`.
  3. Wrap it in a `Texture2DRD`.

  The official `compute/texture` demo does exactly this: a water-ripple simulation in three ping-pong textures sampled by a material [S37, S38, S39].
- **Avoid `sync()` on a local device.** It stalls the CPU; wait 2–3 frames instead [S9]. Very long dispatches risk a Windows TDR (driver timeout reset) [S9].
- **SubViewport painting** is the no-compute alternative:
  - Use `render_target_clear_mode = CLEAR_MODE_NEVER` to accumulate.
  - Use `render_target_update_mode = UPDATE_ONCE` to render only when painting [S36].
- **CompositorEffect** (Forward+/Mobile) injects custom rendering passes and runs on the render thread [S40].

### 2.8 Subsurface scattering (skin, flesh, brain)

- SSS is available **only in Forward+** [S29].
- It is a **screen-space separable blur** with horizontal and vertical passes, 8×8 workgroups, and **11, 17 or 25 taps** by quality. It has a dedicated **skin kernel** in the style of Jimenez's separable SSS, and a depth-scaled radius [S33, K-H R5].
- Material built-ins: `SSS_STRENGTH`, `SSS_TRANSMITTANCE_COLOR`, `SSS_TRANSMITTANCE_DEPTH` and `SSS_TRANSMITTANCE_BOOST`. The render mode `sss_mode_skin` selects the skin profile. `BACKLIGHT` is the "cheaper approximation" [S1].
- Transparent materials do not receive screen-space SSS [K-M].

### 2.9 Physics: Jolt, PhysicalBone3D and joints

- **Ragdoll workflow:**
  1. Run "Create Physical Skeleton" on the `Skeleton3D`. This creates `PhysicalBone3D` nodes under a `PhysicalBoneSimulator3D`.
  2. Remove unneeded bones such as fingers ("for each PhysicalBone3D the engine needs to simulate, there is a performance cost").
  3. Start with `physical_bones_start_simulation()`. It optionally takes a list of bone names for a **partial ragdoll**.
  4. Blend with the simulator's `influence` [S4, S10].
- **Joint advice from the manual** [S4]:
  - Hinge for elbows and knees.
  - Cone for shoulders, hips and neck, with **swing span 20–90° and twist span 20–45°**.
  - **Not** the default pin joint, which causes crumpling.
- **SkeletonModifier3D:**
  - It runs **after** the AnimationMixer and blends by `influence` [S11].
  - `Skeleton3D.modifier_callback_mode_process` chooses physics-rate, idle-rate or manual processing [S35].
  - The `skeleton_updated` signal fires after all modifiers [S35].
- **PhysicalBone3D:**
  - It has `_integrate_forces(state)`, `custom_integrator`, `apply_impulse()` and `apply_central_impulse()` [S13].
  - It is **kinematic when not simulating** [S28].
  - Its 6DOF joint data exposes per-axis `angular_spring_enabled/stiffness/damping/equilibrium_point` and linear equivalents. Cone joint data exposes swing and twist spans [S28].
  - **The internal joint RID, and so motors, is not reachable from script before 4.8** [S48].
- **Godot's Jolt module:**
  - Maps 6DOF springs to Jolt motors in Position mode, using stiffness/damping or **frequency/damping**. Motors are velocity motors [S26].
  - Cone-twist maps to Jolt's `SwingTwistConstraint`, with swing and twist motors [S27].
  - **Unsupported properties are ignored with a warning** [S5, S26, S27]:
    - PinJoint3D: bias, damping, impulse clamp.
    - HingeJoint3D: bias, softness, relaxation.
    - ConeTwistJoint3D: bias, softness, relaxation.
    - Generic6DOFJoint3D: limit softness, restitution, damping, ERP.
    - SliderJoint3D: its angular properties and limit softness/restitution/damping.
- **Jolt project defaults** [S20]:
  - Velocity steps 10; position steps 2.
  - Sleep below 0.03 m/s for 0.5 s.
  - CCD movement threshold 0.75; CCD max penetration 0.25.
  - Penetration slop 0.02 m; speculative contact distance 0.02 m; Baumgarte 0.2.
  - Max bodies 10,240; max body pairs 65,536; max contact constraints 20,480.
  - Max linear velocity 500 m/s; max angular velocity 2,700°/s.
- **Queries and threading:**
  - Ray-cast `face_index` is **−1 by default**. Enable "Physics > Jolt Physics 3D > Queries > Enable Ray Cast Face Index", which costs "about 25 %" more memory for `ConcavePolygonShape3D` [S5].
  - The module supports "Run On Separate Thread", though it "has not been tested very thoroughly" [S5].
- **Jolt itself:**
  - Its motors apply `stiffness·(target − current) + damping·(target_vel − current_vel)`, with a frequency/damping spring mode [S54].
  - Its native ragdolls support hard keying, soft keying and motor driving [S55].
  - Its ragdoll benchmark scene has **16 piles × 10 ragdolls (3,680 bodies) with motors active** [S56, S58].
  - It is used by Horizon Forbidden West and Death Stranding 2 [S55, S57].
  - Godot does not expose Jolt's native `Ragdoll` class. PhysicalBone3D bodies and joints are separate objects [K-M].

### 2.10 LOD, culling, MultiMesh, AA

- **Auto LOD** (meshoptimizer, 1 px threshold) "may occasionally introduce rendering issues (especially in skinned meshes)". It can be disabled per mesh [S30].
- **Occlusion culling** rasterises occluders on the CPU with Embree. It gains less in Forward+, which already has a depth prepass, and works best indoors [S31].
- **MultiMesh** has **no per-instance frustum culling**, so chunk it by area. Allocate the maximum count and vary `visible_instance_count` [S43].
- **Skinning is "very expensive on some platforms"**, so reduce the polycount of animated models [S32].
- **Alpha-blended materials** are "significantly slower, especially if they overlap". They cast no shadows and sort per object [S29, S42].
- **AA and upscaling:** FXAA, **SMAA (4.5)**, TAA, MSAA, FSR 1.0 and FSR 2.2 [S46]. **Physics interpolation** is optional and off by default [S51].

### 2.11 What Godot cannot do easily, and the workaround

| Limitation | Evidence | Workaround |
|---|---|---|
| Persistent decals on skinned meshes (they slide and project through limbs) | [S25] | UV-space damage atlas painted by compute (Section 6). Bone-parented `Decal` only for ≤ 1 s impact flashes |
| Rest-pose position or bone matrices inside a spatial shader | [S2], [S1] | Bake rest position into `CUSTOM0` at import |
| Stencil read in the opaque pass | [S1] | `discard` holes plus interior meshes. Stencil only for the transparent X-ray view |
| Runtime SDF bake for particle collision | [S16] | Bake the static arena SDF in the editor. Runtime heightfield for dynamic floor objects. Box/sphere colliders on bones (≤ 32 per system) |
| Particle collision with skinned bodies | [S15] | `GPUParticlesCollisionSphere3D`/`Box3D` attached to 4–8 bones. Top-down heightfield including the body layer |
| GPU particle landing → decal or CPU event | [K-H] | GPU "stain particles" that freeze on collision. CPU-simulated "hero drops" for stains that matter (Section 8.4) |
| Arrays or textures in instance uniforms; > 16 instance uniforms | [S8] | Unique ShaderMaterial per character, or a data texture indexed by one instance-uniform ID |
| Script access to PhysicalBone3D joint motors (4.5) | [S48] | PD torques in `_integrate_forces`, or 6DOF angular springs through `joint_constraints/*` properties |
| Jolt joint softness, bias or restitution | [S5] | Emulate compliance with springs (frequency/damping) and body damping |
| Runtime skinned-mesh slicing | none built in; libraries are convex-only [S63, S64] | Pre-split zones plus caps. C++ GDExtension slicer on a worker thread for incisions only |
| Fluid simulation or screen-space fluid rendering | not in engine [K-H] | Trails and ribbons for streams. Particles plus stain quads. Floor splat map with cellular flow. Optional SSFR (screen-space fluid rendering) through CompositorEffect later |
| Texture-space skin diffusion or wetness simulation | not in engine | Screen-space SSS plus custom damage atlases |
| Reading the posed mesh on the CPU cheaply | [S34] | Hit rays go to a rest-space proxy (Section 4.2). Never read back GPU skinning |
| Adding decal textures at runtime without a hitch | [K-M] | Preload a fixed decal texture set |
| Clustered element budget (512 per view) | [S6] | Cap visible decals at ~200. Merge floor stains into the splat map |
| MultiMesh per-instance culling | [S43] | Chunk frozen debris per ~2 m cell |
| Mesh LOD glitches on skinned meshes | [S30] | Author body LODs manually, or disable auto LOD on the body |

### Simulation parameters (engine constraints)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `godot_version` | 4.5.x (4.5.2) | — | Select Jolt explicitly | [S21], [S22] |
| `skin_weights_per_vertex_max` | 8 | bones | Import with 4 unless the face needs 8 | [S2] |
| `uniform_buffer_max` | 65,536 | bytes | Desktop | [S8] |
| `instance_uniforms_max` | 16 | per shader | No arrays or textures | [S8] |
| `clustered_elements_max` | 512 (default) | per view | Lights + decals + probes | [S6] |
| `particle_colliders_max` | 32 | per system | Also 32 attractors | [S19] |
| `particle_sdf_resolution` | 64³–128³ for a 6–10 m room | voxels | 16³–512³ allowed. Editor bake only | [S16], [G] |
| `particle_heightfield_resolution` | 512² over 4×4 m around the victim (7.8 mm/texel) | texels | 256²–8,192² allowed. Default 1,024² | [S17], [S19], [G] |
| `sss_taps` | 17 (1660) / 25 (3060) | taps | 11/17/25 available | [S33], [G] |
| `jolt_velocity_steps` | 10 (default) → 12–16 for stacked ragdoll contact | iterations | Raise only if joints stretch | [S20], [G] |
| `jolt_position_steps` | 2 (default) → 3–4 | iterations | Same | [S20], [G] |
| `jolt_raycast_face_index` | enabled | bool | +~25 % memory on concave shapes | [S5] |
| `physics_ticks_per_second` | 60 | Hz | Enable physics interpolation | [S51], [G] |

### Visual/behavioural checklist (engine constraints)
- Nothing on the character slides when a joint bends. Test this with an elbow and a knee flexing through their full range.
- No wound "shows through" onto the far side of a limb.
- The first blood or the first gore mesh never causes a hitch. All gore materials, particle systems and decal textures are warmed up during loading. Godot compiles pipelines when a material is first drawn [K-M].

---

## 3. Recommended architecture (overview)

### 3.1 Data flow

```
Weapon event (ray/pellets/blade sweep/hammer contact/torch cone)
   │
   ▼
HIT PIPELINE  (C++ GDExtension, main thread, ≤0.5 ms per shot)
   1. Jolt ray vs PhysicalBone3D hitbox shapes → bone b, world hit
   2. Transform ray into REST space via bone b:  M = Rest(b) · Pose(b)^-1
   3. Exact ray vs rest-pose trimesh (separate physics space, face_index on)
      → rest-space point, normal, triangle, barycentrics, UV
   4. March the ray through anatomy SDFs: skin/fat/muscle depth maps,
      bone capsules, organ volumes, vessel capsules, spinal cord
   │
   ├──► WOUND STORE (per character)      ──► PHYSIOLOGY (docs 03/04, 20 Hz)
   │      rest-space SDF wound records          flows per wound, MAP, HR,
   │      paint events, fracture events         tone per limb, eyes, skin
   │                                              │
   ▼                                              ▼
 GPU wound buffer   DAMAGE PAINTER          VFX DIRECTOR (60 Hz, interpolates)
 (data texture +    (compute on main RD,     ooze / drip / stream / jet
  3D lookup grid)    Texture2DRD atlases)    particle pools, trails, decals,
   │                  │   ▲                  hero drops, floor splat + flow
   │                  │   └── RIVULET AGENTS (C++, 30 Hz, on rest mesh)
   ▼                  ▼
 SKIN / FLESH / ORGAN SHADERS  ◄── GEOMETRY MANAGER (inner layers on demand,
                                    caps, sever, pre-fractured bone swaps)
                                   MOTOR CONTROLLER (powered ragdoll, 60 Hz)
```

### 3.2 Scene layout (per victim)

```
Victim (Node3D)
├── Skeleton3D                      modifier_callback_mode_process = PHYSICS
│   ├── Body (MeshInstance3D)       modular surfaces per dismember segment, skin shader
│   ├── Head (MeshInstance3D)       face/scalp, teeth, tongue; eyes (separate material)
│   ├── Inner/ (MeshInstance3D ×N)  hidden until needed: muscle shell, skeleton,
│   │                               skull, brain, spinal cord, heart, lungs, liver,
│   │                               spleen, kidneys, great vessels
│   ├── Caps/ (MeshInstance3D ×Z)   hidden stump caps per zone
│   ├── PhysicalBoneSimulator3D
│   │   └── PhysicalBone3D ×17–19
│   ├── MotorController              SkeletonModifier3D or Node; PD torques via bones
│   └── BoneAttachment3D ×k          emitters, wound plugs, impact-flash decals
├── AnimationTree
├── WoundStore + PhysiologyBridge    GDExtension
└── RestProxy                        ConcavePolygonShape3D of the rest mesh in a
                                     private PhysicsServer3D space (never rendered)
```

### 3.3 Rates and threads

| System | Rate | Thread | Notes | Source |
|---|---|---|---|---|
| Jolt physics (ragdolls, debris) | 60 Hz | Physics (optionally separate) | Physics interpolation on | [S5], [S51], [G] |
| Physiology plus vessel graph | 20 Hz alive, 2–5 Hz dead | Worker | ~150 unknowns, < 0.1 ms per tick | doc 03 §11.6, doc 04 §13.5 |
| VFX director | 60 Hz | Main | Interpolates physiology outputs | [G] |
| Rivulet agents | 30 Hz | Worker (C++) | ≤ 32 agents | [G] |
| Damage painting | Event-driven, ≤ 8 dispatches per frame | Render thread | `call_on_render_thread` | [S37], [G] |
| Floor blood spread | 10–20 Hz | Render thread (compute) | 256² active window | [G] |
| Skin physiology masks (pallor and similar) | ≤ 1 Hz | Main → material | doc 04 §13.5 | doc 04 |

### 3.4 Language split

- **GDScript:**
  - game flow and weapons;
  - UI;
  - emitter and decal pooling;
  - setting material parameters.
- **C++ GDExtension** (or C#). These are the hot loops:
  - hit pipeline;
  - anatomy ray-march;
  - vessel-graph solve;
  - rivulet agents;
  - slicer;
  - bulk array building.

  GDScript is one to two orders of magnitude slower than C++ in tight numeric loops [K-M].

### Simulation parameters (architecture)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hit_pipeline_budget` | ≤ 0.5 (C++) | ms per shot | Shotgun = 9–12 rays (00 buck has 8–9 pellets) | [E], [K-M] |
| `physiology_tick` | 20 / 2–5 | Hz | Alive / dead | doc 04 §13.5 |
| `vfx_director_tick` | 60 | Hz | | [G] |
| `agent_tick` | 30 | Hz | | [G] |
| `paint_dispatches_per_frame_max` | 8 | — | Merge further events into the next frame | [G] |
| `gpu_frame_target_1660` | ≤ 13.5 | ms | ≥ 3 ms headroom | [G] |
| `cpu_main_target` | ≤ 12 | ms | | [G] |

### Visual/behavioural checklist (architecture)
- A shot's visual result (hole, spatter, first blood) appears **on the impact frame**. Paint, particles and decals are all issued in the same frame.
- Bleeding changes smoothly between physiology ticks. There is no visible 20 Hz stepping in jet height or drip rate.
- Heavy scenes degrade gracefully: fewer mist particles and fewer distant decals. They never drop frames or stop wounds from appearing.

---

## 4. Anatomy data and the hit pipeline (rest space)

### 4.1 Rest-space assets (authored in Blender, verified in Godot)

| Asset | Representation | Size / resolution | Used by | Source |
|---|---|---|---|---|
| Rest position per vertex | `CUSTOM0.xyz` (float); `CUSTOM0.w` = segment ID | per vertex | Skin/inner shaders (wound SDF), dismemberment | [S1], [S2], [G] |
| Position map (UV → rest position) | RGBA16F texture, rasterised in UV space | 1,024² body / 1,024² head (bilinear) | Painter (3D brushes) | [G] |
| Normal/tangent map (UV → rest normal) | RGBA8 | as above | Painter (brush orientation), agents | [G] |
| Tissue depth maps (UV → skin, fat, muscle thickness) | RGBA8 in mm, scaled | 512² | Anatomy march, cap and cavity shading | [G]; thicknesses [K-M] |
| Bone capsules/meshes | Capsule chain plus mesh for exact tests | 206 bones collapsed to ~60 capsules | Fractures, X-ray, hit test | [G] |
| Organ volumes | Low-resolution SDF 3D textures (32³–64³) or convex hulls | per organ | Hit test, organ damage | [G] |
| Vessel graph | Capsule segments (Ø, length, depth, parent), from doc 03 §11 | 60–80 arterial + 40–60 venous segments | Hit test, bleeding | doc 03 §11.6 |
| Spinal cord | Capsule chain per vertebral level, Ø ~10 mm (cervical wider) | 31 segments | Cord level (doc 04 §6) | doc 04, [K-M] |
| Rest-pose collision proxy | `ConcavePolygonShape3D` of the rest mesh in a private physics space | full body 30–60k triangles | Exact hit point | [S5], [G] |

**Surface-area arithmetic [D].**
- Body surface area (DuBois) for 178 cm and 75 kg = 0.007184 × 75^0.425 × 178^0.725 ≈ **1.93 m²**.
- A 2,048² atlas at ~70 % UV use holds 2.94 M texels → **~0.66 mm² per texel, i.e. ~0.8 mm texels** over the whole body.
- The head and neck are ~9 % of body surface area (rule of nines) ≈ 0.17 m². A separate 2,048² head atlas therefore gives **~0.24 mm texels**. That is enough for stippling (doc 01 §3) and abrasion collars (1–2 mm).

### 4.2 Exact hit on a deforming body

1. **Coarse hit.** Raycast against the `PhysicalBone3D` collision shapes (capsules and boxes) with Jolt. The result gives bone `b` and an approximate world point.
2. **Transform to rest space.** Compute `M_b = RestGlobal(b) · PoseGlobal(b)⁻¹` and apply it to both the ray origin and the direction. Near joints, the error from blended skinning is a few mm; the exact test in step 3 absorbs it [D].
3. **Exact hit.** Intersect the transformed ray with the rest-pose trimesh in a private `PhysicsServer3D` space. Enable face index [S5]. The result gives the triangle index, then barycentrics, UV, rest normal and exact rest point.

   **Do not** read skinned vertices back from the GPU [S34].
4. **Exit and second surfaces.** Continue the ray from the entry point to find the exit on the far side. Keep the entry → exit segment as the **wound track** in rest space.
5. **Pellets and blades.**
   - Shotgun: repeat steps 1–4 per pellet.
   - Knife: sweep 3–5 rays per frame along the blade edge while it is in contact.
   - Hammer and fist: sphere or box overlap, then contact point and normal.
   - Torch: a cone query over the position map, handled by the painter (Section 6).

### 4.3 Anatomy traversal along the track (rest space)

- March the track in 1–2 mm steps (C++, ~100–300 steps per shot):
  - Classify tissue by the depth maps: skin, then fat, then muscle.
  - Test bone capsules, organ SDFs, vessel capsules and the cord.
- **Emit one event per structure crossed:**
  - `SkinBreach`: entrance or exit, with angle and range class (doc 01).
  - `BoneHit`: bone, location and fracture pattern (doc 01 §5, doc 02 §4/5).
  - `OrganHit`: organ, entry/exit and cavity size.
  - `VesselHit`: segment, side laceration or transection by overlap fraction (doc 03 §4.4).
  - `CordHit`: level and completeness (doc 04 §6).
- **Vessel overlap rule [G]:** let `d` = distance from the track axis to the vessel axis.
  - If `d < r_vessel + r_track`, the vessel is injured.
  - If `d < r_track − 0.5·r_vessel`, it is a transection; otherwise a side laceration.
  - The permanent-track radius comes from doc 01 (~bullet diameter).
  - The temporary cavity can tear vessels without the bullet touching them. Roll against the cavity radius with a lower probability [K-M].

### 4.4 Wound record (CPU and GPU)

| Field | Type | GPU packing | Notes |
|---|---|---|---|
| `shape` | enum {round_cone, capsule, ellipsoid, slab, sphere_cluster} | vec4[2].w (low bits) | Round cone for bullet tracks (entry r ≠ exit r) |
| `p0, r0` | rest-space vec3, radius (m) | vec4[0] | Entry centre and radius |
| `p1, r1` | vec3, radius | vec4[1] | Exit or far end |
| `axis_u, len/width` | vec3, floats | vec4[2].xyz | Slab orientation (knife) |
| `open` | bool | flag | true → `discard`; false → shading only |
| `rim_mm, margin_type` | floats | packed | Abrasion collar, soot, stippling radius (doc 01 §2–3) |
| `t_created` | minutes | packed | Ageing, drying, clot (doc 03 §10.4) |
| `vessel_id, bleed_handle` | ints | CPU only | Links to physiology and VFX |

- **Storage:**
  - up to **64 SDF wounds** per character in a 3 × 64 RGBA32F data texture (3 KB);
  - plus a **3D lookup grid** (RGBA8, 4 wound indices per cell), 32 × 16 × 80 cells over the 0.8 × 0.4 × 2.0 m rest bounds (2.5 cm cells, 164 KB).

  Each fragment tests only the ≤ 4 wounds in its cell [D, G].
- **Beyond 64 wounds:** retire the oldest closed (non-open) wounds into the paint atlas, where their marks stay, and keep open wounds as SDFs [G].

### Simulation parameters (anatomy and hits)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `bsa_default` | 1.93 | m² | DuBois, 178 cm / 75 kg | [D] |
| `atlas_body` | 2,048² (4,096² on ≥ 8 GB VRAM) | texels | ~0.8 mm texels | [D], [G] |
| `atlas_head` | 2,048² | texels | ~0.24 mm texels | [D], [G] |
| `rest_proxy_tris` | 30–60k | triangles | Decimated rest mesh, error ≤ 1 mm | [G] |
| `march_step` | 1–2 | mm | Anatomy traversal | [G] |
| `sdf_wounds_max` | 64 | per character | Retire oldest closed ones to paint | [G] |
| `wound_grid` | 32×16×80, 2.5 cm cells, 4 indices per cell | cells | RGBA8 Texture3D | [D], [G] |
| `vessel_hit_rule` | d < r_v + r_t injured; d < r_t − 0.5 r_v transected | — | Cavity tears with probability | [G], [K-M] |
| `skin_thickness` | 1–4 (face 1–2, back 3–4, eyelid ~0.5) | mm | Depth map default | [K-M] |
| `subcut_fat` | lean 5–15, average 10–30, obese 30–80 (abdomen) | mm | Procedural body parameter | [K-M] |

### Visual/behavioural checklist (anatomy and hits)
- A shot to the same body point gives the same wound in any pose: standing, curled or ragdolled.
- Through-and-through shots have an entrance and an exit that line up with the bullet path through the anatomy.
- Arterial bleeding happens only when the track actually crosses the vessel's known course (doc 03 §11). Players who know anatomy can predict it.

---

## 5. Layered wound rendering on skinned meshes

### 5.1 Options compared

| Option | What the player sees | Cost | Fails when | Use in Gore Head |
|---|---|---|---|---|
| UV paint only (tier a) | Colour, blood film, bruise, burn, soot | Near zero at render time | Wound needs depth | Always, for all surface marks |
| Analytic cavity in the skin shader | Convincing hole ≤ ~12 mm with depth and layered walls; silhouette intact | ALU only, inside the wound radius | Hole large enough to see through, or at the silhouette | Pistol entrances and exits, stab wounds, small lacerations |
| Discard plus interior meshes (L4D2 style) | Real hole; the next tissue layer is visible; correct shadows | `discard` in prepass/shadow; hidden meshes cost only skinning and culling | Interior meshes missing or misaligned | Shotgun wounds, contact head wounds, large exits, avulsions, burns through |
| Back-face "flesh" fallback | Inside of the body shell rendered as dark wet tissue | `cull_disabled` on the skin | Looks hollow if relied on | Safety net behind every discard |
| Wound "plug" meshes on a BoneAttachment3D | Authored cavity (tube or crater) aligned to the track | Tiny meshes | Plug is rigid, so it can misalign near joints | Head, chest and pelvis (rigid regions) |
| Runtime geometry (CSG or slicing) | Arbitrary cuts | CPU milliseconds; complex | Skinned meshes | Knife incisions only (Section 9.3) |

### 5.2 Skin shader: SDF evaluation (tiers a and b)

**Vertex stage.**
- Pass `rest_pos = CUSTOM0.xyz` and `segment = CUSTOM0.w` as varyings.
- Collapse the vertices of hidden segments (Section 9.1).

**Fragment stage** (outline, own code):
```
cell   = texelFetch(wound_grid, ivec3((rest_pos - grid_min) / cell_size), 0)
d_min  = +inf ; k = -1
for j in 0..3: if cell[j] != 0: i = cell[j]-1; d = sdf(wound[i], rest_pos); if d < d_min {d_min = d; k = i}
if k >= 0:
    if wound[k].open and d_min < 0:             discard            // large hole (tier c shows through)
    if !wound[k].open and d_min < wound[k].r0:  cavity_shade(k)    // small hole, analytic depth
    rim = 1 - smoothstep(0, rim_width[k], d_min)                  // abrasion collar / margin
    ALBEDO = mix(ALBEDO, margin_colour(k, d_min), rim)
paint = texture(damage_atlas, UV)                                 // tier a (Section 6)
```

- **Round-cone SDF** for bullet tracks. The entry radius comes from calibre (doc 01 §2.1: entrance ≈ bullet diameter or slightly smaller). The exit radius is larger and irregular: add 3D noise to the SDF of amplitude 0.2–0.4 × r [G].
- **Knife slab SDF:**
  - length = cut length;
  - depth = cut depth;
  - thickness 0.3–1.0 mm.

  The gape increases with time and with skin tension lines (doc 02). **Gape angle** is animated through `r1` over 0.5–2 s [G].
- **Cavity shading** (closed, small holes):
  - Intersect the view ray (tangent space) analytically with a cylinder or cone of radius `r(depth)` down to depth `D` (20–40 mm).
  - Shade the wall by depth band from the tissue depth maps:
    - skin 1–4 mm;
    - fat (yellow);
    - muscle (dark red);
    - blood fill level at the bottom.
  - Add a dark centre (occlusion ∝ depth).

  No ray-march loop and no `discard`, so the depth prepass stays early-Z friendly. The idea resembles interior mapping and parallax occlusion mapping [K-H R26].
- **Budget.** ≤ 4 SDF evaluations per fragment (the grid) plus 1 cavity intersection inside wound radii. At a close-up covering 40 % of 1080p (0.83 Mpx), this is ~0.1–0.2 ms on a 1660 [E].

### 5.3 Large holes: discard plus interior layers (tier c)

- **Discard behaviour.** Opaque materials that `discard` also apply it in the depth prepass and shadow passes, so the hole appears in shadows [K-M]. `discard` "has a performance cost" [S8]. Keep it only in the skin and inner-layer shaders, and only branch into it inside wound cells.
- **Interior stack.** All layers are skinned to the same skeleton and are hidden until a wound with `open = true` lies within 5–10 cm of their bounds [G]:
  1. **Muscle shell.** The body mesh offset inward by (skin + fat) from the depth maps, then decimated to 30–50 % of the body triangle count. It is authored in Blender with shrinkwrap/displace plus weight transfer. It evaluates the same wound SDFs, so the hole continues through it with a slightly smaller radius (tracks narrow in muscle, doc 01).
  2. **Skeleton / ribs / skull.** Authored meshes with pre-fractured variants (5.5).
  3. **Organs.** Heart, lungs, liver, spleen, kidneys, brain, spinal cord and great vessels, with their own damage SDFs, masks and blend shapes (5.6).
  4. **Back-face fallback.** The skin uses `cull_disabled`. Where `FRONT_FACING == false`, it shades as dark, wet tissue (`#3A0A0C`, roughness 0.25), so a hole never shows the "empty inside of a balloon" [G].
- **Wound plugs.** For the head, chest and pelvis (rigid bones), spawn an authored cavity mesh on a `BoneAttachment3D`:
  - tube or crater, 100–300 triangles;
  - aligned to the track;
  - scaled to r0/r1 and the track length.

  This gives the walls of a through-and-through track real geometry [G].

### 5.4 Cross-section and cavity-wall colours (clinical reference, approximate)

| Tissue | Fresh, wet (sRGB) | Roughness | Notes | Source |
|---|---|---|---|---|
| Dermis (cut edge) | `#E3B7A6` | 0.45 | Pale pink-white band 1–4 mm | [K-M], [G] |
| Subcutaneous fat | `#EBD27E` → `#F2DF9C` | 0.35 | Lobulated yellow, glistening | [K-M] |
| Fascia | `#E6DFD4` | 0.3 | Thin white sheet | [K-M] |
| Skeletal muscle | `#8E2A2A` (fresh) → `#6E1E1F` (cyanotic or older) | 0.25–0.35 wet | Fibre direction visible | [K-M] |
| Cortical bone (cut) | `#E7DCC6` | 0.5 | Ring 2–8 mm (long-bone shaft) | [K-M] |
| Red marrow / cancellous bone | `#8C2A24` | 0.4 | Vertebrae, pelvis, ends of long bones | [K-M] |
| Yellow marrow | `#D7B45F` | 0.35 | Adult long-bone shafts | [K-M] |
| Brain, grey-matter surface | `#C9A79E` with a vessel net | 0.25 | Pink-grey. Soft, moist | [K-M] |
| Brain, white matter | `#EDE3D8` | 0.3 | Visible in cut tracks | [K-M] |
| Dura mater | `#D9CBBB` | 0.35 | Tough, whitish, fibrous | [K-M] |
| Artery wall (section) | `#DCC0B6` ring, lumen dark red | 0.3 | Thick wall keeps its round shape | [K-M] |
| Vein (section) | Thin wall, collapsed, `#3E0509` content | 0.25 | Flattened | [K-M], doc 03 §9.3 |
| Blood colours | see doc 03 §9.3 | — | Use doc 03 values | doc 03 |

### 5.5 Bone fracture and skull damage

- **Assets:** pre-fractured variants per long bone and per skull region, made in Blender (Cell Fracture or Voronoi):
  - 8–20 fragments;
  - shaft patterns: transverse, oblique, spiral, butterfly, comminuted;
  - skull: bevelled entry and exit holes, radiating and concentric fractures (doc 01 §5, doc 02 §5).
- **Runtime swap:**
  1. Hide the intact bone segment.
  2. Show the fracture variant whose pattern best matches the event.
  3. Fragments are children of the bone and move kinematically, offset 1–5 mm along the fracture normals [G].
  4. Comminuted pieces ≥ 20 mm become rigid debris (Section 9.4). Smaller chips are particles.
- **Skull and brain are rigid with the head bone**, so head wounds can use exact authored geometry and plugs. The brain wound track uses a discard SDF, a cavity plug and a haemorrhage tint painted into a 1,024² brain atlas.

### 5.6 Organ damage (heart, lungs, liver, kidneys, spleen, brain, cord)

| Organ | Rendering state | Driven by | Notes |
|---|---|---|---|
| Heart | Blend shapes: systole/diastole at HR. Fibrillation (random 4–8 Hz noise); still in asystole. Wound SDF with discard | doc 04 rhythm; doc 03 §11.5 | Visible through large chest wounds and in X-ray |
| Lungs | Blend shapes: breathing at RR × tidal volume; collapse (pneumothorax). Frothy blood particles at wounds | doc 04 §9 | Sucking chest wound: bubbles in sync with breathing |
| Liver, spleen, kidneys | Discard SDF lacerations, ooze paint, capsule-tear mask | doc 03 §8 | Mostly internal: drives physiology and X-ray |
| Brain | Track SDF, contusion mask, herniation (brain-stem shift is not visible) | doc 01 §6, doc 04 | Brain-matter ejection (Section 9.4) |
| Spinal cord | Transection or contusion mask. Level feeds doc 04 | doc 04 §6 | Visible only in open wounds or X-ray |

### Simulation parameters (wound rendering)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `cavity_max_radius` | 6 (≤ 12 mm diameter) | mm | Above this use discard | [G] |
| `cavity_depth` | 20–40 | mm | Analytic wall shading | [G] |
| `rim_width` | 1–2 (abrasion collar), 5–30 (stippling) | mm | doc 01 §2–3 | doc 01 |
| `exit_noise_amp` | 0.2–0.4 × r | — | Irregular exits | [G] |
| `stab_gape_time` | 0.5–2 | s | Knife slab r1 animation | [G] |
| `layer_reveal_radius` | 5–10 | cm | Enable inner meshes near open wounds | [G] |
| `backface_flesh_colour` | `#3A0A0C`, roughness 0.25 | sRGB | Hole safety net | [G] |
| `fracture_fragments` | 8–20 | per variant | Authored | [G] |
| `fragment_offset` | 1–5 | mm | Kinematic displacement | [G] |
| `wound_shader_cost` | ~0.1–0.2 at 0.83 Mpx | ms (1660) | ≤ 4 SDF evaluations per fragment | [E] |

### Visual/behavioural checklist (wound rendering)
- A pistol entrance is a small, round, dark hole with a thin abrasion collar. The player can see a short way in, and the walls change colour with depth. No large crater appears.
- Shotgun wounds at close range are ragged real holes. Through them the player sees muscle, and then rib or bone. The hole throws a correct shadow.
- A skull wound shows bevelling of the bone edge and fracture lines. Brain tissue is visible in the track.
- A hole never shows an empty, see-through body shell.
- Organs visible through large wounds move: the heart beats at the simulated heart rate and the lungs move with breathing. Both stop at death.

---

## 6. Texture-space damage painting (blood film, bruises, burns, soot, wetness)

### 6.1 Atlas layout and memory

| Texture | Format | Size | Memory | Channels | Source |
|---|---|---|---|---|---|
| `blood_state` (body) | RGBA16F | 2,048² | 33.6 MB (no mips) | R film thickness (mm), G deposit time (min), B dilution/serum, A crust/dried fraction | [D], [G] |
| `tissue_state` (body) | RGBA8 | 2,048² | 16.8 MB | R bruise (0–1, with age in `blood_state.G` or a paired map), G burn degree (0–3), B soot/stipple, A abrasion | [D], [G] |
| `blood_state` and `tissue_state` (head) | as above | 2,048² each | 50.4 MB | Face and scalp detail | [D], [G] |
| Position map and normal map | RGBA16F / RGBA8 | 1,024² each | 8.4 + 4.2 MB | Paint lookups only | [D], [G] |
| **Total per hero character** | | | **~113 MB** | Fits in 6 GB alongside the scene | [D] |

- **Mips.** Regenerate mips only for the dirty rectangle after painting, or sample with `textureLod` at a distance-based LOD. Otherwise distant bodies alias [K-M].
- **UVs.** Use a non-overlapping, uniform-density unwrap (the atlas UV set, separate from tiling detail UVs) with **≥ 8 px gutters at 2,048²** [K-M].

### 6.2 Seam-free 3D brushes via the position map

- Each paint event is a **3D brush in rest space**:
  - sphere, ellipsoid, oriented splat, stroke capsule or cone (torch);
  - plus a profile (Gaussian, hard, noise-edged) and a blend op (add thickness, max, set time).
- **Per texel:** read the rest position and normal, evaluate the brush, and write the result. Texels on both sides of a UV seam share a 3D position, so they get **identical** paint. Seams disappear without special handling. Dilation (6.5) covers only the gutter bleed.
- **Dispatch area.**
  - Compute the brush's UV-space bounding rectangles from a per-chart lookup, or conservatively from the triangles within the brush radius.
  - Dispatch over those rectangles only: typically 64²–256² texels, microseconds per dispatch [E].
  - A full 2,048² dispatch is ~0.1–0.2 ms on a 1660 [E]. Allow it only for global events such as burns or immersion.
- **Brushes by weapon and effect** (radii from docs 01–03):
  - Stippling: many ≤ 1 mm dots in a 1–30 cm pattern (doc 01 §3).
  - Soot: smooth grey-black ellipse.
  - Abrasion: a scraped band in the direction of travel.
  - Contusion: a blurred ellipse that blooms over minutes (doc 02 §3).
  - Burn: cone from the torch position, degree by temperature and dwell time (doc 02 §6).
  - Blood film: thickness added by bleeding agents and spatter.

### 6.3 Implementation in Godot 4.5

- **Compute path (recommended):**
  1. Create the atlases on the **global** RenderingDevice.
  2. Wrap them in `Texture2DRD` for the skin materials.
  3. Queue paint jobs from the main thread.
  4. Run all queued dispatches in one `RenderingServer.call_on_render_thread()` callback per frame [S37, S38, S39].
  5. Ping-pong only where a job reads and writes the same texel region, such as flow; brush writes can be in-place storage-image writes [K-M].
- **SubViewport path (prototype or fallback):**
  - Render the mesh unwrapped: the vertex shader writes `POSITION = vec4(UV * 2.0 - 1.0, 0.0, 1.0)` [K-H].
  - Use an unshaded, blend-add brush material in a `SubViewport` with `CLEAR_MODE_NEVER` and `UPDATE_ONCE` per paint [S36].
  - **Caveats:**
    - viewport output is 8-bit unless configured otherwise, and post-processing must be disabled in its own `World3D` [K-M];
    - float data (thickness, timestamps) is awkward.

    Move to compute for production.

### 6.4 Store timestamps, not ages

- Write the **deposit time** (minutes since level start, fp16) into the atlas.
  - The shader computes `age = time_minutes − deposit` and derives the doc 03 §10.4 colour ramp, roughness (wet → matte) and crust.
  - **No per-frame atlas updates are needed for drying** [G].
- **fp16 precision** is ±0.5 min at 1,000 min, which is adequate. Rebase the clock on scene reset [D].
- **Clot and dry thresholds.**
  - Skin smears go touch-dry in 1–3 min and fully dry in 5–10 min.
  - Thick rivulets are touch-dry in 10–20 min.

  Scale the time by thickness: thinner stains move along the ramp faster (doc 03 §10.4).

### 6.5 Seams, dilation, filtering

- After each paint job, dilate the affected rectangle by 2–4 texels into the gutters: copy the nearest valid texel into empty gutter texels, using a baked "valid texel" mask [K-M].
- Blood-film normals come from the thickness gradient (a height map), evaluated in the skin shader with 3–4 taps [G].

### 6.6 Blood-film optics on skin (from doc 03 §9)

- **Transmittance of a film** of thickness `h` (mm), with light passing through it twice: `T = exp(−2·μa·h)`.
  - Use μa per mm (R, G, B) = **(0.4, 28, 34) arterial** and **(3.0, 26, 50) deoxygenated**. Lerp by saturation (doc 03 §9.2).
- **Shaded albedo** = `skin_albedo · T + (1 − T) · blood_body_colour`, with the body colour from doc 03 §9.3.
  - Example at h = 0.05 mm, arterial: T ≈ (0.96, 0.06, 0.03).
  - Skin albedo (0.8, 0.6, 0.5) becomes ≈ (0.77, 0.04, 0.02) plus the body term: saturated scarlet [D].
- **Specular:**
  - Wet blood has F0 ≈ 0.02–0.025 (refractive index ~1.35–1.40) and roughness 0.05–0.15.
  - Tacky blood: 0.3–0.45. Dried crust: 0.6–0.8 [K-M].
- **Serum rim** (thick deposits after 30 min – 2 h): a pale translucent edge (`#E6D08A`, doc 03).

### Simulation parameters (painting)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `atlas_body_blood` | RGBA16F 2,048² | — | 33.6 MB | [D], [G] |
| `atlas_body_tissue` | RGBA8 2,048² | — | 16.8 MB | [D], [G] |
| `atlas_gutter` | ≥ 8 | px at 2,048² | Dilate 2–4 px after paint | [K-M], [G] |
| `paint_rect_typical` | 64²–256² | texels | Microseconds per dispatch | [E] |
| `paint_full_atlas` | 0.1–0.2 | ms (1660) | Rare | [E] |
| `time_units` | minutes, fp16 | — | Deposit timestamp | [G] |
| `mu_a_arterial_rgb` | (0.4, 28, 34) | 1/mm | | doc 03 §9.2 |
| `mu_a_deoxy_rgb` | (3.0, 26, 50) | 1/mm | | doc 03 §9.2 |
| `blood_F0` | 0.02–0.025 | — | n ≈ 1.35–1.40 | [K-M] |
| `rough_wet / tacky / dry` | 0.05–0.15 / 0.3–0.45 / 0.6–0.8 | — | Driven by age × thickness | [K-M], [G] |
| `dry_time_skin_smear` | 5–10 | min | doc 03 §10.4 | doc 03 |

### Visual/behavioural checklist (painting)
- Blood on skin is **scarlet and glossy in thin films** and darker where thick. Over a few minutes it loses its gloss and turns matte red-brown at the thin edges first.
- Paint crosses UV seams invisibly. Check the neck/head seam and the inner-arm seam.
- Soot and stippling around contact and close-range wounds sit exactly at the pattern radius given in doc 01. Stippling does not wipe off; soot smears.
- Bruises bloom over minutes rather than appearing instantly (doc 02).
- Torch burns spread as a gradient from the flame's aim point. Blistering and charring follow doc 02 §6.

---

## 7. Blood that runs down skin and surfaces

### 7.1 Rivulet agents on the rest mesh (skin)

**Agent state:** triangle ID, barycentric position, volume (µL), width (mm), speed (cm/s), pinned timer.

**Each step (30 Hz):**
1. **Gravity in rest space.** For the agent's dominant bone: `g_rest = R_b⁻¹ · g_world`, where `R_b` is the rotation from rest to current pose. Project `g_rest` onto the triangle plane.
2. **Speed.**
   - Thin-film formula `u = ρ·g·sinθ·h² / (3μ)`: h = 0.2 mm on a vertical surface gives ~2 cm/s.
   - Clamp to 0.5–10 cm/s (doc 03 §10.2).
   - **Stop–go pinning:** with probability 0.1–0.3 per step, pin for 0.2–1.5 s. This reproduces the jerky advance of the contact line [G].
3. **Move** across triangle edges using a prebuilt adjacency table (C++).
4. **Deposit residue** of 5–15 µL per cm of path (doc 03) as a painted capsule stroke 2–5 mm wide (blood-film thickness plus deposit time).
5. **Stop** when the volume drops below 5 µL.
6. **Pendant drops.** Where gravity points away from the surface or the agent reaches a local low point (chin, nose tip, earlobe, elbow, fingertips when standing; occiput and ears when supine), accumulate volume. **Release a drop at 30–60 µL** as a CPU "hero drop" (Section 8.4) and play a drip sound [doc 03].

**Spawning.**
- Each bleeding wound in the drip or stream regime spawns agents at `Q / V_agent` with V_agent 50–200 µL.
- Cap at **32 live agents** per character.
- The painted trails persist, so **old trails keep their original direction** after the body is moved. This is a forensic clue (doc 03 §10.2).

**Hair.** Hair cards take a wetness/blood parameter from rest-space distance to scalp wounds. Hair looks darker, clumped and glossy while wet. Drips fall from hair tips at 10–20 µL (doc 03) [G].

### 7.2 Streams on skin

- Above ~15–30 mL/min (doc 03 stream threshold), switch from agents to a **stream**: a painted continuous film along the agent path, plus a **trail ribbon** where the stream leaves the body.
- The ribbon is a GPUParticles3D trail, or a CPU-updated ImmediateMesh strip of 10–30 segments.

### 7.3 Blood running down walls and objects

- **GPU particles with collision** against the baked room SDF:
  - bounce 0;
  - friction 0.3–0.6;
  - gravity.

  They slide down vertical surfaces [S18].
- A **constant-mode sub-emitter** leaves a "stain" particle every 5–10 mm of path [S18, S41]. Stain particles freeze and live 10–30 min (Section 8.4).
- **Alternative:** a short sequence of preloaded drip decal textures. Switch the texture frame on a `Decal` every 0.5–2 s; no atlas rebuild is triggered, because all frames are preloaded [S6, K-M].

### 7.4 Floor pools: arena splat map with cellular spread

- **Splat map:** RG16F, 2,048² over an 8 × 8 m arena (3.9 mm texels), 16.8 MB:
  - R = thickness (mm);
  - G = deposit time (min).

  Bound as a **global uniform** so every floor material samples it [S8]. Walls use decals.
- **Spread rule** (10–20 Hz, compute over a 256² window around active pools) [G]:
  - Cells above the equilibrium thickness (2.5 mm, range 1.6–3.3 per doc 03 §10.3) pass their excess to lower neighbours, weighted by the height difference of (floor height + blood).
  - Limit movement to ≤ 1–3 cells per tick.
  - This conserves volume and gives area ≈ V/h: 500 mL ≈ 50 cm diameter, 1 L ≈ 71 cm.
  - Under a continuous source the radius grows as `R = √(Q·t/(π·h))` (doc 03).
- A full thin-film PDE is **not** used. At h = 2.5 mm its explicit stability limit on 4 mm cells is ~0.3 ms per step, which is impractical, and surface tension already pins real pools at the capillary thickness [D].
- **Gel.** After 5–15 min (doc 03), set cell mobility to 0. New blood flows over or around the gel, giving layered, lobed outlines.
- **Absorbent floor material flag:** spread area 2–4× and duller colour (doc 03).
- **Pool shading:**
  - thickness drives parallax height and normals;
  - wet roughness 0.03–0.08, rising with age;
  - near-black red body with colour visible only at thin edges (doc 03 §9);
  - a reflection probe for the room. SSR is optional on the 3060; the 4.6+ SSR is cheaper [S22].

### Simulation parameters (surface flow)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `agent_tick` | 30 | Hz | | [G] |
| `agents_max` | 32 per character | — | | [G] |
| `agent_speed` | 1–5 (clamp 0.5–10) | cm/s | Thin-film law | doc 03 §10.2 |
| `agent_pin_prob / pin_time` | 0.1–0.3 per step / 0.2–1.5 s | — | Stop–go | [G] |
| `agent_residue` | 5–15 | µL/cm | | doc 03 |
| `rivulet_width` | 2–5 | mm | | doc 03 |
| `drip_release` | 30–60 (hair 10–20) | µL | | doc 03 |
| `stream_threshold` | 15–30 | mL/min | Agents → stream | doc 03 |
| `wall_particle_friction` | 0.3–0.6, bounce 0 | — | Slide on the SDF | [S18], [G] |
| `floor_splat` | RG16F 2,048² over 8×8 m | — | 3.9 mm texels | [D], [G] |
| `pool_eq_thickness` | 2.5 (1.6–3.3) | mm | | doc 03 §10.3 |
| `pool_spread_tick` | 10–20 Hz, ≤ 1–3 cells per tick | — | Cellular automaton | [G] |
| `pool_gel_time` | 5–15 | min | Mobility → 0 | doc 03 |

### Visual/behavioural checklist (surface flow)
- Blood from a scalp or face wound runs in **narrow lines along creases**. It pauses, then jerks forward, and collects at the chin, nose tip or earlobe before dripping.
- **Drips are heard.** A soft tick on skin or cloth and a sharper patter on a hard floor. The rate matches the drip rate (1 mL/min ≈ 20 drops/min, doc 03).
- If the body is turned over, old dried trails point the "wrong" way and new ones run at an angle.
- The floor pool grows as a thin sheet with a sharp edge. It follows floor slope and grout lines, stops growing after ~10 min, and later goes dull at the edges.
- Blood on walls runs down in thin streaks that slow and stop, leaving a line of stain.

---

## 8. Bleeding VFX driven by the vessel graph; spatter; particles; decals

### 8.1 Flow regime → VFX

| Regime | Condition (per wound, from physiology) | VFX | Audio | Source |
|---|---|---|---|---|
| None / internal | Track fully inside tissue or cavity (`tissue_factor` ≈ 0) | None externally. Drives pallor and physiology | — | doc 03 §4.5, §8 |
| Ooze | Q < 1 mL/min | Paint only: film thickness grows, beads at the wound | — | doc 03, [G] |
| Drip | 1–15 mL/min | Agents (Section 7) plus pendant drops | Drip ticks | doc 03 §10.2 |
| Stream | 15–300 mL/min | Painted film plus trail ribbon to the ground | Continuous trickle and splash | doc 03, [G] |
| Jet (arterial) | Arterial, `tissue_factor` > 0.5, Q > ~300 mL/min | Pulsed ribbon or tube trail on a ballistic path, plus 30–80 breakup drops per s | Rhythmic spurting and splatter at heart rate | doc 03 §12 |
| Frothy (lung) | Lung or airway wound | Pink foam particles, bubbles in sync with breathing | Gurgling, sucking | doc 03 §9.3, doc 04 §9 |

**Jet dynamics** (doc 03 §4, §12):
- Launch speed `v0 = √(2·g·h_jet)`. The real jet height is 0.35–0.65 × the ideal pressure head, i.e. **0.55–1.0 m vertical at normal blood pressure**, which gives v0 ≈ 3.3–4.4 m/s [D].
- Height scales with instantaneous pressure. It pulses at HR with modulation depth 0.5–0.8 (arterial) and **shrinks as MAP falls**.
- The jet stops below the critical closing pressure for small arteries (20–40 mmHg).

**Caps:** ≤ 6 jets and ≤ 20 drips/streams (doc 03 §12). The physiology still accounts for the volume of every wound, including ones whose VFX is culled.

### 8.2 Spatter from impacts (numbers from doc 01 §7)

- **Back-spatter per head shot:**
  - 30–320 macro droplets (> 0.5 mm);
  - v0 13–61 m/s (mean ~24);
  - cone half-angle ~57°;
  - macro range 0.7–1.2 m, micro ≤ 0.7 m.
- **Forward spatter:**
  - v0 ~47 m/s;
  - half-angle ~27°;
  - 2–5 × the back-spatter count.
- **Render as:**
  - One **burst** GPUParticles3D per event from a pool, with `amount` fixed at 1,024 and the count set by `amount_ratio`. Changing `amount` would restart the system [S14].
  - 2–4 soft mist sprites.
  - One projected speckle for the micro-mist.
  - **30–60 CPU hero drops** for the largest droplets that must leave correct stains (8.4).
- **Droplets:**
  - small alpha-scissor quads or icospheres rendered opaque, so they need no sorting and are cheap to overdraw;
  - velocity-stretched by `transform_align` to velocity [S14];
  - mist is the only alpha-blended part.

### 8.3 Pellets, knife and blunt events

- **Shotgun:** 8–12 pellets per shot. Run the pipeline per pellet, but merge the spatter bursts into one or two emitters per shot [G].
- **Knife:** cast-off follows the blade arc on the backswing (1–4 mm drops). The blade itself gets a painted blood film.
- **Blunt:** cast-off from the hammer head (drops along the swing arc). Impact spatter is small in count and larger in drop size than gunshot spatter (medium-velocity legacy class, 1–4 mm, doc 03 §10.1).

### 8.4 From particles to stains: GPU-only versus CPU "hero drops"

| Path | What | How | Budget | Source |
|---|---|---|---|---|
| GPU stain particles | Mist and fine spatter (< 1 mm) | Custom particle process shader: on collision, zero velocity, orient to the collision normal, extend lifetime to 10–30 min, switch to a stain sprite. Or an at-collision sub-emitter that spawns stain particles (the sub-emitter's amount caps the total) | ≤ 8,000 persistent stain particles | [S18], [S41], [K-M] |
| CPU hero drops | Drops ≥ 1 mm and drips | C++ ballistic step with drag at 60 Hz plus a Jolt raycast per step. On hit, place a `Decal` (walls, props) or add volume and time to the floor splat map, with the stain size and ellipse from doc 03 (spread 3–5 × drop diameter; L/W = 1/sin α) | ≤ 200 in flight; each raycast ~µs in C++ | doc 03 §10.1, [E] |
| Victim's own body | Drops landing on the victim | Paint into the victim atlas when the drop's ray hits a PhysicalBone3D shape (Section 4.2 path) | ≤ 60 per s | [G] |

**Decal pool:**
- 128–256 `Decal` nodes, recycled oldest-first.
- `normal_fade` 0.3–0.5.
- Distance fade from 15 m with 10 m length [S12].
- A fixed preloaded set of 32–64 spatter/drip/smear textures (albedo + normal + ORM) [S6].
- **Floor stains go into the splat map, not decals,** to protect the 512-element cluster budget.

### 8.5 Particle budgets

| System | Max live (1660) | Max live (3060) | Collision | Notes |
|---|---|---|---|---|
| Spatter bursts (pool of 8 × 1,024) | 8,192 | 16,384 | SDF + heightfield + 4–8 bone spheres | Opaque droplets |
| Mist sprites | 64 | 128 | none | **Only alpha-blended system. Cap screen coverage** |
| Stain particles | 8,000 | 16,000 | on first hit | Frozen, flat, alpha-scissor |
| Jet breakup drops | 6 × 256 | 6 × 512 | yes | Sub-emitters for splash |
| Jet ribbons (trails) | 6 | 6 | — | Tube/ribbon trail meshes [S14] |
| Debris chips (bone < 20 mm, tissue) | 1,000 | 2,000 | yes | Mesh draw pass |
| **Total live** | **~20k** | **~40k** | | Scale with `amount_ratio` |

### Simulation parameters (bleeding VFX)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `regime_ooze_max` | 1 | mL/min | | [G] |
| `regime_drip_max` | 15 | mL/min | | doc 03 |
| `regime_stream_max` | 300 | mL/min | | [G] |
| `jet_height_normal_bp` | 0.55–1.0 | m | 0.35–0.65 × ideal | doc 03 |
| `jet_v0` | 3.3–4.4 | m/s | √(2gh) | [D] |
| `jet_pulse_depth` | 0.5–0.8 | × mean | At HR | [G] |
| `jets_max / drips_max` | 6 / 20 | — | | doc 03 §12 |
| `jet_breakup_drops` | 30–80 | per s per jet | | doc 03 §12 |
| `backspatter_count` | 30–320 | per head shot | | doc 01 §7 |
| `backspatter_v0 / cone` | 13–61 (24) m/s / 57° | — | | doc 01 §7 |
| `forward_v0 / cone` | 47 m/s / 27° | — | | doc 01 §7 |
| `hero_drops_per_event` | 30–60 | drops | CPU ballistic | [G] |
| `hero_drops_in_flight_max` | 200 | — | | [G] |
| `decal_pool` | 128–256, visible ≤ 200 | — | Cluster budget 512 | [S6], [G] |
| `stain_particles_max` | 8,000 (1660) | — | | [G] |
| `live_particles_max` | 20k (1660) / 40k (3060) | — | | [E], [G] |

### Visual/behavioural checklist (bleeding VFX)
- An exposed arterial wound spurts **in time with the pulse**. Each spurt is visibly lower as blood pressure falls, then the jet dwindles to a pulsing well and a trickle.
- Venous bleeding **wells and flows** darker, with no spurting. Straining or screaming causes brief dark surges (doc 03 §4.7).
- Head-shot spatter is sparse and fine on the shooter's side and denser and narrower on the exit side, with larger drops and tissue further out (doc 01 §7).
- Every visible drop that lands leaves a stain of the right size and shape: round when it hits head-on, elongated with a tail on a slant.
- The patter of spatter landing is heard 30–300 ms after the shot (doc 01 §7).

---

## 9. Dismemberment, cutting and debris

### 9.1 Realism scope first

With a pistol, shotgun, knife, fist, hammer and torch:
- **Pistol:** does not amputate limbs. It can shatter fingers [K-M].
- **Shotgun at contact or close range:**
  - can amputate fingers, a hand or a wrist;
  - can destroy much of the face, jaw or skull (doc 01 §9);
  - arm or leg amputation is uncommon.
- **Knife:** cuts soft tissue to the bone and can disarticulate small joints with effort. It **cannot** sever a long bone.
- **Hammer and fist:** fracture and lacerate; they do not sever.
- **Torch:** does not sever.

So the dismemberment system mainly serves **fingers, hand/wrist, jaw/face avulsion and skull disruption**. Full limb severing should be rare and gated by the weapon and range [K-M, G].

### 9.2 Pre-split zones, segment IDs and caps (Fallout pattern [S61])

- **Zones** (per side where paired):
  - fingers (phalanges);
  - hand/wrist;
  - mid-forearm; elbow; mid-upper arm; shoulder;
  - foot/ankle; mid-shank; knee; mid-thigh;
  - jaw (mandible);
  - face (mid-face avulsion);
  - skull vault (calvarium);
  - neck.

  That is 12–16 zones in total [G].
- **Authoring in Blender:**
  - Put edge loops at each cut position, with matched vertex rings.
  - Write the segment ID into `CUSTOM0.w`.
  - Author a **proximal cap** (stump) and a **distal cap** (severed piece) per zone.
  - **Cap cross-sections must place the vessels, nerves and bones where the vessel graph says** (doc 03 §11). Jets then start from the correct lumen.
- **Hiding segments without new geometry:**
  - An instance uniform `hidden_segments` (int bitmask; instance uniforms allow scalars [S8]) is read in `vertex()`.
  - Vertices whose segment is hidden are collapsed (for example `VERTEX = vec3(0)`), producing zero-area triangles that are not rasterised [K-H].
  - This avoids `discard` and costs nothing in the pixel shader.
- **Modular alternative:**
  - Author each segment as its own surface or mesh, so a severed piece carries only its own vertices. This is the approach of the Unreal SkeletalMeshDestruction plugin, which hides bones and spawns pre-made pieces [S65].
  - It avoids skinning the full mesh twice.
  - The price is ~10–16 extra draw calls per character and careful seam normals.
  - **Recommended** for the arms, hands and head/jaw.

### 9.3 The sever event

1. **Body.** Set the segment bits in `hidden_segments` and show the proximal cap (skinned to the proximal bone).
2. **Severed piece.**
   - Instance a prepared scene for that zone: the modular segment mesh(es) plus the distal cap, on a **copy of the distal bone chain** (a new Skeleton3D) with PhysicalBone3D bodies.
   - Initialise its poses from the body skeleton's current global poses.
   - Give it the bone's velocity plus the event impulse.
   - Disable collisions between the piece and the body for 0.1–0.3 s so it does not explode out of the stump. The UE plugin uses a similar "physical avoidance" phase [S65].
3. **Physiology.**
   - Every vessel crossing the zone becomes a transection at the cap position (doc 03 §4.4: retraction, spasm).
   - The distal piece drains only its own contained blood, by gravity, with no pressure.
4. **VFX.**
   - Jets or streams start from the cap lumens.
   - Paint heavy film on the cap and neighbouring skin.
   - Spawn debris chips for bone.

### 9.4 Runtime slicing (knife incisions only)

- **When:** a knife stroke deeper than the fat layer that runs longer than ~8–10 cm, where the player will inspect the cut edge [G]. Shallow cuts are SDF slabs (Section 5).
- **Algorithm** (C++ GDExtension, worker thread, rest pose):
  1. Select the triangles within the stroke's swept volume (by bone weights and bounds).
  2. Split them by the cut surface (a plane per stroke segment). Interpolate UV, normal, tangent and **bone weights**, then renormalise the top 4 or 8 weights.
  3. Build the cut-wall polygons (the incision is open, not a full sever) and triangulate them. Use ear clipping for simple polygons and constrained Delaunay for polygons with holes.
  4. Build a new `ArrayMesh` surface.
  5. Swap it in on the next frame.
- **Libraries.** EzySlice and godot-slicer handle **convex meshes only**, using monotone-chain triangulation of the section [S63, S64]. godot-slicer targets Godot 3.2 [S63]. Neither handles skinned meshes. **Write our own, and do not copy their code.**
- **Cost:** 1–4 ms on a worker for a 20k-triangle region in C++ [E]; 50–300 ms in GDScript [E]. Cap at one slice job in flight.

### 9.5 Gibs and debris (bone, skull, brain matter)

| Class | Size | Representation | Physics | Budget |
|---|---|---|---|---|
| Skull plates, jaw, large bone | ≥ 20 mm | RigidBody3D with a convex hull, CCD on | Jolt, mass by volume × 1.9 g/cm³ (bone) [K-M] | ≤ 48 active; asleep → MultiMesh |
| Brain clumps | 3–40 mm (doc 01 §7) | RigidBody3D if ≥ 20 mm; otherwise particles | On contact: stick with p 0.5–0.8, then slide down walls at 0.2–2 cm/s | as above |
| Bone chips, tooth fragments | 2–20 mm | GPU particles with a mesh draw pass | Particle collision | ≤ 1,000–2,000 |
| Tissue shreds | 5–30 mm | GPU particles or RigidBody3D | — | — |

- **Freezing.** When a debris body sleeps (Jolt: < 0.03 m/s for 0.5 s [S20]), delete it and add an instance to a **chunked MultiMesh** (per 2 m cell, since there is no per-instance culling [S43]) with the same transform and custom data (colour, wetness, age).
- **Soft brain matter** never bounces: bounce 0, friction 0.9 [G]. Leave a painted smear on the surface at the contact point.

### Simulation parameters (dismemberment and debris)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `dismember_zones` | 12–16 | — | Fingers, hand, forearm, elbow, arm, shoulder, foot, shank, knee, thigh, jaw, face, vault, neck | [G] |
| `sever_gate` | shotgun ≤ 1 m for hand/fingers/face; knife disarticulation of fingers only | — | Realism | [K-M], [G] |
| `sever_nocollide_time` | 0.1–0.3 | s | Piece vs body | [S65], [G] |
| `slice_trigger` | depth > fat layer, length > 8–10 cm | — | Knife only | [G] |
| `slice_cost` | 1–4 (C++ worker) | ms | GDScript is unusable | [E] |
| `debris_active_max` | 48 | bodies | CCD on | [G] |
| `debris_frozen_max` | 2,000 | instances | MultiMesh per 2 m cell | [S43], [G] |
| `bone_density` | 1.8–2.0 | g/cm³ | Cortical bone | [K-M] |
| `brain_density` | ~1.04 | g/cm³ | | [K-M] |
| `brain_stick_prob` | 0.5–0.8 | — | Walls and ceiling | [G] |

### Visual/behavioural checklist (dismemberment and debris)
- A close shotgun blast to the hand leaves a ragged stump. Bone ends and tendons are visible in the cap, and the stump bleeds from the correct vessels (radial and ulnar at the wrist).
- A knife cut deep enough shows gaping skin, yellow fat and red muscle in the walls of the cut. Long bones are never cut through.
- Skull fragments fly, clatter and settle realistically. Brain matter lands soft and wet and sticks, and it never bounces.
- Debris never disappears while in view. Frozen pieces look identical to the live ones.

---

## 10. Ragdolls, powered ragdolls and dying behaviour

### 10.1 Physical skeleton

**Bodies (17 minimum, 19 with clavicles):**
- pelvis, abdomen (lumbar), thorax;
- neck, head;
- per side: clavicle (optional), upper arm, forearm, hand, thigh, shank, foot.

**Masses for 75 kg (Winter/Dempster segment fractions) [K-H R17]:**

| Segment | Fraction of body mass | Mass (75 kg) | Notes |
|---|---|---|---|
| Head + neck | 0.081 | 6.1 kg | Split ~5.0 head + 1.1 neck. Keep the neck ≥ 1–1.5 kg for solver stability [K-M] |
| Thorax | 0.216 | 16.2 kg | |
| Abdomen | 0.139 | 10.4 kg | |
| Pelvis | 0.142 | 10.7 kg | |
| Upper arm | 0.028 | 2.1 kg each | |
| Forearm | 0.016 | 1.2 kg each | |
| Hand | 0.006 | 0.45 kg each | |
| Thigh | 0.100 | 7.5 kg each | |
| Shank | 0.0465 | 3.5 kg each | |
| Foot | 0.0145 | 1.1 kg each | |

**Joint limits** (active range from AAOS norms [K-H R18]; add ~10 % for passive limits in a dead body [G]):

| Joint | Godot joint type | Limits |
|---|---|---|
| Neck (C-spine) | 6DOF or cone | Flexion 45–50°, extension 45–60°, lateral flexion 45°, rotation 60–80° |
| Lumbar and thoracic | 6DOF | Flexion 80–90°, extension 20–30°, lateral 25–35°, rotation 30–45° (split across two joints) |
| Shoulder | Cone | Swing ≤ 90–110° (the manual suggests 20–90° [S4]); twist ±70° |
| Elbow | Hinge | 0–145° (hyperextension ≤ 5°) |
| Forearm twist | Folded into the wrist | ±80° |
| Wrist | 6DOF | Flexion 70–80°, extension 60–70°, radial/ulnar 20°/30° |
| Hip | Cone | Flexion 120°, extension 20–30°, abduction 45°, rotation ±45° |
| Knee | Hinge | 0–135° |
| Ankle | 6DOF | Dorsiflexion 20°, plantarflexion 45–50°, inversion/eversion 30°/20° |

**Surface parameters [G]:** friction 0.6–0.9 (skin or cloth on floor), bounce 0.0–0.05, angular damping 0.5–2, linear damping 0.05–0.1.

### 10.2 Jolt settings for ragdolls

- Keep the defaults first: 10 velocity steps, 2 position steps [S20].
- If joints stretch under stacked contact (a body folded over furniture), raise them to 12–16 and 3–4 [G].
- Avoid mass ratios above ~10:1 across one joint [K-M]. This is why the neck mass is raised in 10.1.
- **Sleep:** the default 0.03 m/s for 0.5 s [S20] lets corpses sleep within about a second of settling.
- **Performance:**
  - Jolt's benchmark runs 160 motor-driven ragdolls (3,680 bodies) [S56].
  - A single 19-body ragdoll in Godot costs ~0.05–0.15 ms per physics step, including node sync [E].
  - "Create Physical Skeleton" also creates finger bodies. Remove them [S4].

### 10.3 Hit reactions and partial ragdoll

- **Momentum is small [D].**
  - 9 mm (7.45 g at 360 m/s): p = **2.7 N·s**. .45 ACP (14.9 g at 255 m/s): 3.8 N·s. 12-gauge 00 buck (9 × 3.5 g at 400 m/s): **12.6 N·s**.
  - A 75 kg body gains only **0.04 m/s** from a pistol and **0.17 m/s** from a shotgun.
  - A 5 kg head that fully absorbs a pistol bullet gains ≤ 0.5 m/s.
  - **Realistic reactions come from the nervous system, not bullet momentum:** flinch, withdrawal, collapse.

  So apply the true impulse with `apply_impulse()` [S13] and drive the visible reaction through tone changes.
- **Partial ragdoll flinch:**
  1. `physical_bones_start_simulation([bones near the hit + 1 parent])` [S10].
  2. Set simulator `influence` to 0.3–0.6.
  3. Apply the impulse.
  4. Ramp influence to 0 over 0.2–0.5 s.
  5. Stop simulation [S4, S11].
- **Hammer blow** (0.5–1 kg head at 5–10 m/s; the effective mass including the arm is higher): **~3–10 N·s** [K-M]. This is enough to snap the head visibly. Punches are in the same order [K-L]; see doc 02 for energies.

### 10.4 Powered ragdoll (Euphoria-like tone control)

- **Controller:** a PD torque on each simulated body, toward the local rotation of the animation (or a procedural target), computed in `PhysicalBone3D._integrate_forces(state)` [S13]:
  - `τ = kp·θ_err − kd·ω_rel`, applied to the child body, with the equal and opposite torque on the parent.
  - `kp = I_eff·ω_n²` and `kd = 2·ζ·I_eff·ω_n`, where `ω_n = 2π·f` [D].
- **Alternative:** 6DOF angular springs with `angular_equilibrium_point` updated each physics tick through the `joint_constraints/*` properties [S28]. Jolt implements them as position motors [S26]. This is cheaper, but in 4.5 there is **no torque cap** (the 4.8 proposal adds one [S47]), so strong targets can yank limbs. **Prefer script PD with explicit torque caps.**

**Effective inertia and torque caps (75 kg) [D; torque maxima K-M]:**

| Joint | I_eff about the joint (distal chain) | kp at f = 4 Hz | Torque cap (strong adult) |
|---|---|---|---|
| Neck | ~0.08 kg·m² | ~50 N·m/rad | 20–40 N·m |
| Lumbar (upper body) | ~4–5 | ~2,800 | 200–300 |
| Shoulder (whole arm) | ~0.25 | ~160 | 60–100 |
| Elbow (forearm + hand) | ~0.06 | ~38 | 50–80 |
| Wrist | ~0.004 | ~2.5 | 8–15 |
| Hip (whole leg) | ~2.6 | ~1,640 | 200–300 |
| Knee (shank + foot) | ~0.4 | ~250 | 200–250 |
| Ankle | ~0.01 | ~6 | 100–150 |

Worked example, elbow [D]: forearm + hand 1.65 kg, CoM 0.18 m from the joint, gives I ≈ 0.06 kg·m². At 4 Hz, kp ≈ 38 N·m/rad and kd (ζ = 0.9) ≈ 2.7 N·m·s/rad. A 30° error gives 20 N·m, well under the cap. Gravity torque with the forearm horizontal is 2.9 N·m.

**Tone map from the doc 04 motor states [G]:**

| Doc 04 limb state | f (Hz) | ζ | Torque cap × | Target pose |
|---|---|---|---|---|
| voluntary | 4–6 | 0.8–1.0 | 1.0 | Animation (AnimationTree) |
| weak | 1.5–3 | 1.0 | 0.3–0.5 | Animation, with gravity sag |
| flaccid | 0 | — | 0 | None: passive damping only ("cut strings") |
| decorticate | 3–5 | 0.9 | 0.6 | Elbows flexed 90–120°, wrists and fingers flexed, legs extended |
| decerebrate | 5–8 | 0.9 | 0.8 | Arms extended and pronated, legs extended, neck extended |
| fencing | 3–5 | 0.9 | 0.6 | Arm on the face side extended, the other flexed (doc 04) |
| tonic | 8–10 | 0.7 | 1.0 | Extension rigidity |
| clonic | 3–5 Hz oscillation ±10–25° about the tonic pose | 0.5 | 0.8 | Rhythmic jerks |
| rigor | kinematic lock | — | — | Freeze the current pose as rigor sets in (doc 04 §12) |

- **Collapse timing [D, K-L]:**
  - Free fall of the centre of mass (~1.0 m) takes 0.45 s.
  - A "cut strings" collapse (buckling at knees and hips) reaches trunk-ground contact in **~0.6–1.2 s**.
  - A stiff "plank" topple from standing takes **~1.5–2 s**. It is **wrong** for sudden flaccid collapse.
- **Balance.** Do not attempt Euphoria-style balance in v1. Stand with animation plus a partial ragdoll. When doc 04 reports loss of consciousness or leg paralysis, blend into the full powered ragdoll [G].

### 10.5 Behaviours

| Behaviour | Trigger (doc 04) | Implementation |
|---|---|---|
| Collapse | LOC, cord C-level lesion, medulla/pons destruction | All limbs → flaccid (or the doc 04 posture). Full ragdoll |
| Clutch wound | Conscious and wounded; hand not paralysed | Hand target = wound point (rest → world through the current pose). **4.5: LookAtModifier3D and BoneConstraint3D exist, TwoBoneIK3D does not** [S45]. Write a small two-bone IK as a SkeletonModifier3D, or upgrade to 4.6 IK [S22]. Clutching reduces flow 30–70 % (doc 03 §4.5) |
| Writhing / crawling | Conscious, severe pain, legs functional or not | Procedural low-frequency targets (0.3–1 Hz) on trunk and legs at "weak" tone. Arms drag the body if the legs are paralysed (doc 04 T-level) |
| Agonal gasping | Arrest with intact medulla (doc 04) | Periodic jaw and neck extension, 1 gasp every 5–20 s for 1–5 min, with torque on the jaw and thorax |
| Seizure | doc 04 §4.3 | Tonic phase then clonic phase at 3–5 Hz; post-ictal flaccid |
| Death | doc 04 §10 | Tone → 0. Eyes per doc 04 §11. Rigor later locks the pose |

### 10.6 Eyes and face while dying (engine mapping for doc 04 §11)

- **Instance uniforms** (≤ 16 [S8]): `pupil_mm`, `pupil_reactive`, `gloss`, `corneal_opacity`, `dry_band`, `tache_noire`, `subconj_haem`, `petechiae`.
- **Bones:**
  - lids driven by `lid_mm`;
  - gaze through LookAtModifier3D (4.5) with influence → 0 when fixation is lost, and yaw/pitch offsets for divergence.
- **No blinking after death.** A corneal dry band appears over hours (doc 04).
- **Sound:** no rhythmic breathing after arrest except agonal gasps.

### Simulation parameters (ragdoll and behaviour)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `ragdoll_bodies` | 17–19 | — | Remove fingers | [S4], [G] |
| `segment_mass_fractions` | table 10.1 | — | Winter/Dempster | [K-H R17] |
| `joint_limits` | table 10.1 | ° | AAOS +10 % passive | [K-H R18], [G] |
| `ragdoll_friction / bounce` | 0.6–0.9 / 0–0.05 | — | | [G] |
| `ragdoll_ang_damp` | 0.5–2 | 1/s | | [G] |
| `impulse_9mm / 45acp / 00buck` | 2.7 / 3.8 / 12.6 | N·s | Apply the true value | [D] |
| `flinch_influence` | 0.3–0.6 → 0 over 0.2–0.5 s | — | Partial ragdoll | [S4], [S11], [G] |
| `pd_kp / kd` | I·ω² / 2ζIω | — | f and ζ per tone state | [D], [G] |
| `tone_table` | table 10.4 | — | From doc 04 motor states | [G] |
| `collapse_time` | 0.6–1.2 | s | Flaccid collapse to trunk contact | [D], [K-L] |
| `clutch_flow_reduction` | 0.3–0.7 | × | | doc 03 §4.5 |
| `agonal_gasp_interval` | 5–20 s for 1–5 min | — | | doc 04 |
| `ragdoll_step_cost` | 0.05–0.15 | ms per ragdoll | | [E] |

### Visual/behavioural checklist (ragdoll and behaviour)
- A pistol hit does **not** throw the body backward. The body flinches or buckles, and a hit to the head or cord drops it like "cut strings" in under a second.
- Conscious victims reach for and press on their wounds. Bleeding under the hand visibly slows.
- Limbs fall with correct weight: the arms flop, the head lolls within its real range of motion, and no joint bends backward.
- Posturing (flexed or extended arms), seizures and agonal gasps look distinct from one another and appear only when doc 04 conditions hold.
- **Audio:** breathing sounds match the respiratory state (gurgling with blood in the airway, stridor, gasps). Body falls sound heavy and soft, and falls with gear sound hard.

---

## 11. X-ray kill cam (Sniper Elite style)

### 11.1 Stencil approach in Godot 4.5

1. **Skin material, opaque pass:** stencil `write`, `compare_always`, reference 1. Writing in the opaque pass is allowed; only reading is restricted [S1, S44].
2. **X-ray materials** (skeleton, organs, bullet track, fracture fragments): **transparent pass**, `depth_test_disabled`, stencil `read`, `compare_equal`, reference 1 [S1, S44]. They draw only inside the body's silhouette.
3. **Skin during the X-ray:**
   - swap to a transparent variant (Fresnel rim, alpha 0.1–0.25);
   - or keep it opaque and draw the inner anatomy over it with alpha 0.6–0.9.
4. **Bones:** emissive-tinted pale grey-blue (`#C8D4E0`), with fracture lines brighter. **Organs:** semi-opaque, with rupture states.

Alpha-blended, overlapping layers are "significantly slower" [S29]. The kill cam shows one character, so this is acceptable.

### 11.2 Time scale and cameras

- **Timing:**
  - `Engine.time_scale` 0.05–0.1 for bullet travel.
  - A 1.5–3 s real-time X-ray window.
  - Return over 0.3–0.5 s.
- **Enable 3D physics interpolation** so the ragdoll and debris stay smooth at low time scale [S51]. Confirm how physics tick counts behave under `time_scale` in 4.5 before tuning [K-L].
- **Camera:** attach it to a proxy that follows the bullet ray, then orbit the victim. Keep the X-ray camera's near plane at ≥ 5 cm to protect depth precision [S42].

### 11.3 Assets

- Reuse the tier-c inner meshes (Section 5.3) and the pre-fractured bones (Section 5.5).
- **Organ rupture:** blend-shape swell/burst plus discard SDF plus a burst of blood particles.
- The bullet track is drawn as a thin glowing tube or capsule along the rest-space track, transformed to the current pose.
- **Forensic accuracy:** show only fractures consistent with the doc 01 and doc 02 patterns. No over-shattering.

### Simulation parameters (X-ray)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `xray_time_scale` | 0.05–0.1 | × | Bullet travel | [K-M R10], [G] |
| `xray_duration` | 1.5–3 | s real | | [K-M R10], [G] |
| `xray_stencil_ref` | 1 | — | Skin writes, X-ray reads (transparent pass) | [S1], [S44] |
| `xray_skin_alpha` | 0.1–0.25 | — | Fresnel rim | [G] |
| `xray_bone_colour` | `#C8D4E0` | sRGB | Emissive tint | [G] |
| `xray_cost` | 0.5–1.5 | ms (1660) | One character, blended layers | [E] |

### Visual/behavioural checklist (X-ray)
- Time slows and the bullet is followed in. On entry, the skin fades to a ghostly outline and the skeleton and organs appear only inside the body's outline.
- Bone breaks match the real patterns: bevelled skull holes, radiating fractures, rib fractures along the track.
- **Audio:** a muffled low-pass "inside the body" sound, a distinct bone crack at fracture, then a snap back to normal speed and sound.

---

## 12. Materials, SSS and screen-space effects for wet tissue

### 12.1 Material parameters

| Material | Albedo (sRGB) | Roughness | F0 | SSS / transmittance | Notes | Source |
|---|---|---|---|---|---|---|
| Skin | doc 02 §7 palette | 0.40–0.55 dry, 0.25 sweaty | 0.028 | `sss_mode_skin`, strength 0.3–0.6. Ears/nose transmittance depth 0.1–0.3, colour `#C0402A` | Pallor and cyanosis from doc 03/04 masks (≤ 1 Hz) | [S1], [K-M], [G] |
| Fresh blood film | Beer–Lambert (Section 6.6) | 0.05–0.15 | 0.02–0.025 | none | | doc 03, [K-M] |
| Dried blood | doc 03 §10.4 ramp | 0.6–0.8 | 0.02 | none | Cracks on thick deposits | doc 03 |
| Muscle (exposed) | `#8E2A2A` | 0.25–0.35 | 0.02 | strength 0.2–0.4 | Wet sheen | [K-M], [G] |
| Fat | `#EBD27E` | 0.3–0.4 | 0.02 | strength 0.3–0.5 (translucent) | | [K-M], [G] |
| Bone (exposed) | `#E7DCC6` | 0.45–0.6 | 0.03 | 0 | Dulls as it dries | [K-M] |
| Brain | `#C9A79E` | 0.2–0.3 | 0.02 | strength 0.3–0.5 | Vessel-net detail map | [K-M], [G] |
| Pooled blood | near-black red, colour at thin edges | 0.03–0.08 | 0.02 | none | Reflection probe; SSR optional | doc 03, [G] |

### 12.2 Screen-space settings by GPU tier

| Effect | GTX 1660 | RTX 3060 | Notes | Source |
|---|---|---|---|---|
| SSS | 17 taps | 25 taps | Forward+ only | [S29], [S33] |
| SSAO | Half-res, medium | Full-res, high | Grounds pools and debris | [K-M] |
| SSIL | Off | Optional | | [G] |
| SSR | Off (reflection probe) | On for pools; the 4.6+ SSR is cheaper | 4.6 overhaul | [S22], [G] |
| AA | SMAA (4.5) or FXAA | TAA or SMAA | TAA can ghost fast particles, so check spatter [K-L] | [S46] |
| Upscaling | FSR 2.2 at 0.77 if needed | Native | | [S46] |
| Volumetric fog | Off / low | Low | Mist looks better as sprites | [G] |
| Glow | Low | Medium | Wet highlights only | [G] |

### Visual/behavioural checklist (materials)
- Exposed tissue looks **wet** (tight highlights) at first and dulls over minutes. Bone goes from glistening to chalky.
- Skin looks translucent at the ears and nose in back-light. It turns grey-pale with blood loss and waxy after death (doc 04).
- Pools are mirror-dark with red only at the edges. Spatter dots on a pool's surface ring outward (sub-emitter crowns at collision).

---

## 13. Performance: budgets, LOD, culling and scalability

### 13.1 Hardware reference [K-H R23]

| GPU | FP32 | Memory | Bandwidth | Relative raster speed |
|---|---|---|---|---|
| GTX 1660 | ~5.0 TFLOPS | 6 GB GDDR5 | 192 GB/s | 1.0 |
| GTX 1660 Super | ~5.0 TFLOPS | 6 GB GDDR6 | 336 GB/s | ~1.1–1.15 [K-M] |
| RTX 3060 (12 GB) | ~12.7 TFLOPS | 12 GB GDDR6 | 360 GB/s | ~1.7–2.0 [K-M] |

### 13.2 "Heavy gore" reference scene (what the budget must survive)

- **Arena:**
  - one room, 150–300k visible triangles;
  - one directional light (2 cascades at 2,048) and 2–4 shadowed spot/omni lights at 1,024.
- **Hero victim:**
  - 100–150k triangles LOD0;
  - 40 wounds (8 open holes);
  - muscle shell, skull, brain and 2 organs visible;
  - 2 jets, 10 drips/streams, 24 rivulet agents.
- **Particles and stains:**
  - 15k live GPU particles;
  - 200 visible decals;
  - a 1.5 L floor pool.
- **Bodies:**
  - 40 active rigid debris plus 800 frozen MultiMesh fragments;
  - one powered ragdoll plus one sleeping ragdoll.

### 13.3 GPU frame budget at 1080p [E]

| Pass | GTX 1660 (ms) | RTX 3060 (ms) | Gore-specific notes |
|---|---|---|---|
| Skinning compute (≤ 300k skinned vertices incl. visible inner meshes) | 0.1–0.2 | 0.05–0.1 | Hide inner meshes until needed |
| Particle simulation (≤ 20k, collision) | 0.1–0.3 | 0.05–0.15 | 32-collider cap [S19] |
| Paint and flow compute | 0.05–0.2 | 0.03–0.1 | ≤ 8 dispatches per frame |
| Shadow maps | 1.5–2.5 | 0.8–1.3 | Inner meshes: shadows off |
| Depth prepass (incl. discard shaders) | 0.6–1.0 | 0.3–0.5 | Discard only in wound cells |
| SSAO | 0.5–0.8 | 0.3–0.5 | |
| Opaque pass (clustered lights, ≤ 200 decals, skin and wound shader) | 3.0–4.5 | 1.5–2.5 | Decal cost scales with coverage [S6] |
| SSS | 0.3–0.6 | 0.2–0.4 | 17 / 25 taps |
| Sky, fog | 0.1–0.3 | 0.05–0.15 | |
| Transparent (mist, jets, X-ray) | 0.5–1.5 | 0.3–0.8 | **Main risk: overdraw of mist near the camera** |
| Post (tonemap, glow, SMAA/TAA) | 0.6–1.0 | 0.3–0.6 | |
| UI | ~0.1 | ~0.05 | |
| **Total** | **7.5–13.5** | **4–7** | Target ≤ 13.5 on the 1660 |

**Overdraw arithmetic [D].** One mist sprite covering half the 1080p screen blends ~1.04 Mpx. Ten stacked sprites blend ~10 Mpx per frame, i.e. ~0.6 Gpx/s of blending at 60 fps. Blended RGBA16F traffic at that rate is a real fraction of the 1660's 192 GB/s. Hence **cap mist screen coverage at ~15–20 % of the screen and ≤ 4 layers**.

### 13.4 CPU budget (main thread, 6-core reference) [E]

| Work | ms | Notes |
|---|---|---|
| Jolt physics (60 Hz): 2 ragdolls, 48 debris, arena | 0.3–1.0 | Can run on a separate thread [S5] |
| Physiology and vessel graph (20 Hz) | < 0.1 per tick | doc 03 §12 |
| Hit pipeline | 0.1–0.5 per shot (C++) | 1–5 ms per shot in GDScript |
| Rivulet agents (worker) | 0.05–0.2 | |
| Hero drops (≤ 200) | 0.1–0.3 | Raycasts |
| Animation and skeleton modifiers (2 characters) | 0.2–0.6 | |
| Game logic (GDScript) | 1–3 | |
| Render CPU (culling, ~1,000–2,000 draws) | 2–4 | |
| **Total** | **~4–9** | Target ≤ 12 |

### 13.5 LOD, culling, visibility

- **Hero body:**
  - hand-authored LODs;
  - auto LOD disabled if it glitches on skinned meshes [S30].
- **Hidden inner meshes** stay hidden (invisible) until needed. Whether a hidden skinned instance is still skinned by the compute pass is not documented; measure it [K-L].
- **Occlusion culling:** use it for multi-room levels only [S31].
- **Visibility ranges:** particle systems and decals fade beyond 15–25 m.
- **MultiMesh:** chunk debris per 2 m cell [S43].

### 13.6 Measuring

- Use the Godot Visual Profiler (GPU time per pass) and `Performance` monitors.
- `RenderingServer.viewport_set_measure_render_time()` with the viewport CPU and GPU readouts, and `get_frame_setup_time_cpu()` [S38].
- Automated test: run the heavy scene with scripted shots for 60 s and log the 1 %-low frame time. **Pass criterion: 1 % low ≥ 55 fps on the 1660** [G].

### 13.7 Dynamic scalability governor

If measured GPU time > 14 ms over a 0.5 s window, degrade in this order [G]:
1. Mist sprite count and size.
2. `amount_ratio` of spatter bursts (down to 50 %).
3. Stain-particle lifetime (convert old stains into the splat map).
4. Decal distance fade (25 → 12 m).
5. SSS taps (25 → 17 → 11).
6. SSAO to half resolution.
7. Enable FSR 2.2 at 0.77.

Restore in reverse when time < 11 ms for 3 s. **Never degrade the wounds, the physiology, or the stains on the victim.**

### Simulation parameters (performance)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `gpu_budget_1660` | ≤ 13.5 | ms | 1080p | [G] |
| `gpu_budget_3060` | ≤ 8 | ms | Headroom for SSR/SSIL | [G] |
| `cpu_main_budget` | ≤ 12 | ms | | [G] |
| `mist_screen_coverage_max` | 15–20 %, ≤ 4 layers | — | Overdraw | [D], [G] |
| `hero_tris_lod0` | 100–150k (body + head) | triangles | | [G] |
| `inner_mesh_tris` | skeleton 30–50k; brain 40–80k; organs 5–30k each | triangles | Visible only on demand | [G] |
| `governor_high / low` | 14 / 11 | ms | Hysteresis | [G] |
| `pass_criterion` | 1 % low ≥ 55 fps | — | 1660, heavy scene | [G] |

### Visual/behavioural checklist (performance)
- Frame pacing stays smooth during a shotgun volley at point-blank range.
- When the governor acts, only mist density and distant stains change. The victim looks identical.

---

## 14. Final architecture decisions and trade-offs

| Decision | Chosen | Alternatives rejected | Why | Risk and mitigation |
|---|---|---|---|---|
| Wound space | Rest space, `CUSTOM0` rest position | World-space decals; bone-local only | Skinning is a compute pre-pass [S2]; decals slide [S25] | Import-script correctness. Unit-test with poses |
| Surface damage | Compute-painted UV atlases (Texture2DRD) | Decals on characters; SubViewport | Persistent, seam-free with position maps, float data | Needs a clean, uniform-density UV set |
| Holes | SDF in the skin shader: cavity (small) / discard (large) plus interior meshes | CSG; runtime remeshing | L4D2-proven [K-M R1]; cheap; correct shadows | Interior alignment. Back-face fallback |
| Dismemberment | Pre-split zones plus caps, modular segments | Runtime slicing everywhere | Fallout-proven [S61]; realism makes severing rare | Asset work per zone |
| Incisions | C++ slicer on a worker (rare) | GDScript; none | Close inspection needs real cut walls | Cost 1–4 ms; one job at a time |
| Bleeding | Vessel graph → regime VFX | Particle-only blood | Physiologically correct, budgetable | Tuning jets to pressure |
| Stains | GPU stain particles for mist; CPU hero drops for decals and the splat map | GPU collision → decals (impossible) | No GPU → CPU event path | Hero-drop count cap |
| Pools | Floor splat map plus cellular spread | Fluid sim; mesh blobs | Volume-true area V/h; cheap | Uneven floors: use a floor height map |
| Ragdoll | PhysicalBoneSimulator3D + Jolt + PD tone | Animation-only deaths; Jolt native Ragdoll (not exposed) | Physical, physiology-driven dying | PD tuning; 4.8 adds joint RID [S48] |
| X-ray | Stencil (4.5) | Second viewport composite | Built-in, cheap, reads in the transparent pass [S1] | 4.5 stencil syntax differs from master docs [S44] |
| Language | GDScript glue + C++ GDExtension hot paths | All GDScript | Hot loops | Build pipeline complexity |

### 14.1 Phased plan

1. **Phase A (head, current scope):**
   - rest-space pipeline;
   - head atlas;
   - skull and brain inner meshes with pre-fractured skull;
   - spatter (doc 01), rivulets, floor pool;
   - X-ray prototype.
2. **Phase B (full body):**
   - body atlas and muscle shell;
   - vessel-graph VFX regimes;
   - organ meshes (heart, lungs);
   - ragdoll with the tone map;
   - wound clutching (custom two-bone IK).
3. **Phase C:**
   - dismemberment zones (hand, fingers, jaw, face);
   - debris MultiMesh freezing;
   - knife incision slicer.
4. **Phase D:**
   - governor;
   - performance pass on the 1660;
   - optional move to Godot 4.6+ (IK nodes, SSR).

---

## 15. Cross-document notes and corrections

- **Doc 01 §7 checklist** says "a GPUParticles3D system with collision to decals". **GPU particle collisions cannot create `Decal` nodes**; there is no GPU → CPU event path. Use frozen stain particles for fine spatter and CPU hero drops for stains that matter (Section 8.4 here).
- **Doc 03 §12 is consistent with this document.** Ribbons for jets, a floor pool from V/h, a UV-space wetness mask for rivulets, and the caps of 6 jets and 20 drips are implemented in Sections 7–8.
- **Doc 04 §13.5 step 5** ("ragdoll drive targets and strengths") and **step 6** ("set material uniforms and bones") map to Section 10.4 (tone table) and Section 10.6 (eye uniforms) here.

---

## 16. Load-bearing claims (quick reference)

| # | Claim | Value | Source |
|---|---|---|---|
| 1 | Godot RD renderers skin in a compute pre-pass; `VERTEX` in `vertex()` is post-skin, model space | up to 8 weights per vertex | [S2], [S3], [S1] |
| 2 | Rest position must be supplied per vertex (e.g. `CUSTOM0`) for rest-space wounds | — | [D] from [S1], [S2] |
| 3 | Decals are projected per frame from view-space position through the decal box, so they slide on skin and project through limbs | — | [S25], [S12] |
| 4 | Forward+ clustered elements (lights + decals + probes) default limit per view | 512 | [S6] |
| 5 | Decals: no custom shaders; albedo/normal/ORM/emission only; cannot affect transparency | — | [S6], [S12] |
| 6 | Stencil in 4.5: read only in the transparent pass; modes read/write/write_depth_fail/compare_* | — | [S1], [S44] |
| 7 | Instance uniforms: max 16 per shader, no arrays or textures; uniform buffer 64 KB on desktop | 16; 65,536 B | [S8] |
| 8 | GPU particle collision shapes and attractors per system | 32 / 32 | [S19] |
| 9 | Particle SDF collision bakes in the editor only; heightfield updates at runtime (256²–8,192²) | — | [S16], [S17] |
| 10 | Changing `GPUParticles3D.amount` restarts the system; use `amount_ratio` | — | [S14] |
| 11 | Compute results reach materials only via the global RenderingDevice + `call_on_render_thread` + `Texture2DRD`; a local device cannot share | — | [S37], [S38], [S39] |
| 12 | SSS is Forward+-only, separable screen-space, 11/17/25 taps with a skin kernel | — | [S29], [S33] |
| 13 | Jolt defaults: velocity steps 10, position steps 2; sleep 0.03 m/s for 0.5 s; max bodies 10,240 | — | [S20] |
| 14 | Jolt ray `face_index` is −1 unless enabled (+~25 % concave-shape memory) | — | [S5] |
| 15 | PhysicalBone3D joint RID (motors) not script-accessible until 4.8; 4.5 offers 6DOF springs and `_integrate_forces` | — | [S48], [S28], [S13] |
| 16 | Jolt is the default engine for new projects only from 4.6; select it in 4.5. 4.5 released 15 Sep 2025 | — | [S21], [S22] |
| 17 | Segment masses (Winter): head+neck 8.1 %, trunk 49.7 %, thigh 10 %, shank 4.65 %, foot 1.45 %, upper arm 2.8 %, forearm 1.6 %, hand 0.6 % | — | [K-H R17] |
| 18 | Bullet momentum is small: 9 mm 2.7 N·s, 00 buck 12.6 N·s, giving 0.04–0.17 m/s to a 75 kg body | — | [D] |
| 19 | Atlas texel size: 2,048² gives ~0.8 mm over a 1.93 m² body and ~0.24 mm for the head | — | [D] |
| 20 | GPU budget at 1080p for the heavy scene: 7.5–13.5 ms on a GTX 1660; 4–7 ms on an RTX 3060 | — | [E] |

---

## 17. Suspicious content

- **No prompt-injection attempts were found** in the fetched material. No fetched page asked me to run, download, install, change files, visit other URLs or reveal information.
- **A GitHub topic listing** (`github.com/topics/dismemberment`) included a repository presented as a "**leaked build**" of an unreleased game ("ILL-Leaked-Build-2026", 0 stars). Repositories advertising leaked game builds are a common malware lure. **I did not open it, and it is not linked or referenced anywhere in this document.**
- **Several README files contained package-install instructions**, for example a Unity Package Manager Git URL in SkinnedMeshDecals. These are normal README content, not instructions to me. I did not follow them and have not reproduced them.
- **Data-quality note:** one fetch summary misreported Godot 4.5's release year as 2024. The authoritative website data gives **15 September 2025** [S21], and that is the date used here.
- **Bash was not used.** Nothing was downloaded, installed or executed. No code was copied from the web into the project. The shader and pseudo-code outlines in this document were written for it.

---

## 18. Sources

### 18.1 Read this session ([S#])

**Godot engine: manual source** (`godotengine/godot-docs`, which renders docs.godotengine.org):

| # | Source |
|---|---|
| S1 | Spatial shader reference: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/shaders/shader_reference/spatial_shader.rst (the 4.5 branch copy was also checked; its page has no stencil section) |
| S4 | Ragdoll system: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/physics/ragdoll_system.rst |
| S5 | Using Jolt Physics: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/physics/using_jolt_physics.rst |
| S6 | Using decals: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/3d/using_decals.rst |
| S7 | Particle collision: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/3d/particles/collision.rst |
| S8 | Shading language: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/shaders/shader_reference/shading_language.rst |
| S9 | Compute shaders: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/shaders/compute_shaders.rst |
| S29 | StandardMaterial3D: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/3d/standard_material_3d.rst |
| S30 | Mesh LOD: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/3d/mesh_lod.rst |
| S31 | Occlusion culling: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/3d/occlusion_culling.rst |
| S32 | Optimizing 3D performance: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/performance/optimizing_3d_performance.rst |
| S40 | Compositor: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/rendering/compositor.rst |
| S41 | Particle sub-emitters: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/3d/particles/subemitters.rst |
| S42 | 3D rendering limitations: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/3d/3d_rendering_limitations.rst |
| S43 | Using MultiMesh: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/performance/using_multimesh.rst |
| S51 | Physics interpolation introduction: https://raw.githubusercontent.com/godotengine/godot-docs/master/tutorials/physics/interpolation/physics_interpolation_introduction.rst |

**Godot engine: source code and class reference** (`godotengine/godot`):

| # | Source |
|---|---|
| S2 | Skinning compute shader (master): https://raw.githubusercontent.com/godotengine/godot/master/servers/rendering/renderer_rd/shaders/skeleton.glsl |
| S3 | Same file at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/servers/rendering/renderer_rd/shaders/skeleton.glsl |
| S10 | PhysicalBoneSimulator3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/PhysicalBoneSimulator3D.xml |
| S11 | SkeletonModifier3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/SkeletonModifier3D.xml |
| S12 | Decal: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/Decal.xml |
| S13 | PhysicalBone3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/PhysicalBone3D.xml |
| S14 | GPUParticles3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/GPUParticles3D.xml |
| S15 | GPUParticlesCollision3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/GPUParticlesCollision3D.xml |
| S16 | GPUParticlesCollisionSDF3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/GPUParticlesCollisionSDF3D.xml |
| S17 | GPUParticlesCollisionHeightField3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/GPUParticlesCollisionHeightField3D.xml |
| S18 | ParticleProcessMaterial: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/ParticleProcessMaterial.xml |
| S19 | Particle storage limits (MAX_COLLIDERS, MAX_ATTRACTORS): https://raw.githubusercontent.com/godotengine/godot/master/servers/rendering/renderer_rd/storage_rd/particles_storage.h |
| S20 | Jolt project settings: https://raw.githubusercontent.com/godotengine/godot/master/modules/jolt_physics/jolt_project_settings.cpp, also at 4.5-stable (…/4.5-stable/modules/jolt_physics/jolt_project_settings.cpp) |
| S25 | Forward+ scene shader (decal projection, SSS output): https://raw.githubusercontent.com/godotengine/godot/master/servers/rendering/renderer_rd/shaders/forward_clustered/scene_forward_clustered.glsl |
| S26 | Jolt 6DOF joint mapping: https://raw.githubusercontent.com/godotengine/godot/master/modules/jolt_physics/joints/jolt_generic_6dof_joint_3d.cpp |
| S27 | Jolt cone-twist joint mapping: https://raw.githubusercontent.com/godotengine/godot/master/modules/jolt_physics/joints/jolt_cone_twist_joint_3d.cpp |
| S28 | PhysicalBone3D implementation: https://raw.githubusercontent.com/godotengine/godot/master/scene/3d/physics/physical_bone_3d.cpp |
| S33 | Screen-space SSS shader: https://raw.githubusercontent.com/godotengine/godot/master/servers/rendering/renderer_rd/shaders/effects/subsurface_scattering.glsl |
| S34 | MeshInstance3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/MeshInstance3D.xml |
| S35 | Skeleton3D: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/Skeleton3D.xml |
| S36 | SubViewport: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/SubViewport.xml |
| S37 | Texture2DRD: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/Texture2DRD.xml |
| S38 | RenderingServer: https://raw.githubusercontent.com/godotengine/godot/master/doc/classes/RenderingServer.xml |
| S44 | Shader modes at 4.5-stable (stencil): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/servers/rendering/shader_types.cpp |
| S45 | Class presence at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/BoneConstraint3D.xml and …/LookAtModifier3D.xml (present); …/TwoBoneIK3D.xml (HTTP 404 at 4.5-stable) |
| S46 | Viewport at 4.5-stable (SMAA, FSR 2.2): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/Viewport.xml |

**Godot: website data, proposals, issues and demos:**

| # | Source |
|---|---|
| S21 | Release dates: https://raw.githubusercontent.com/godotengine/godot-website/master/_data/versions.yml |
| S22 | 4.6 features: https://raw.githubusercontent.com/godotengine/godot-website/master/_data/release_4_6/features.yml |
| S23 | 4.7 features: https://raw.githubusercontent.com/godotengine/godot-website/master/_data/release_4_7/features.yml |
| S24 | 4.5 release page (stencil buffer highlight): https://raw.githubusercontent.com/godotengine/godot-website/master/pages/releases/4.5.html |
| S39 | Compute texture demo: https://github.com/godotengine/godot-demo-projects/tree/master/compute/texture |
| S47 | Proposal 14745 (expose Jolt 6DOF spring max force/torque; milestone 4.8; PR 119332): https://github.com/godotengine/godot-proposals/issues/14745 |
| S48 | Proposal 13392 (PhysicalBone3D `get_joint_rid()`; milestone 4.8; PR 112002): https://github.com/godotengine/godot-proposals/issues/13392 |
| S49 | Proposal search "active ragdoll" (includes 15426, 14845, 10015, 8008): https://github.com/godotengine/godot-proposals/issues?q=is%3Aissue+active+ragdoll |
| S50 | Issue search "PhysicalBone3D Jolt" (issue 102638, milestone 4.4): https://github.com/godotengine/godot/issues?q=is%3Aissue+PhysicalBone3D+Jolt |
| S52 | Ragdoll physics demo (stencil outline via BaseMaterial3D): https://github.com/godotengine/godot-demo-projects/tree/master/3d/ragdoll_physics |
| S53 | Decals demo: https://github.com/godotengine/godot-demo-projects/tree/master/3d/decals |

**Jolt Physics** (`jrouwe/JoltPhysics`):

| # | Source |
|---|---|
| S54 | Architecture (motors, spring modes, ragdoll filtering): https://raw.githubusercontent.com/jrouwe/JoltPhysics/master/Docs/Architecture.md |
| S55 | README (features, animated ragdolls, users): https://raw.githubusercontent.com/jrouwe/JoltPhysics/master/README.md |
| S56 | Performance test (ragdoll scene 16 × 10, 3,680 bodies): https://raw.githubusercontent.com/jrouwe/JoltPhysics/master/Docs/PerformanceTest.md |
| S57 | Projects using Jolt: https://raw.githubusercontent.com/jrouwe/JoltPhysics/master/Docs/ProjectsUsingJolt.md |
| S58 | Ragdoll benchmark scene (`DriveToPoseUsingMotors`): https://raw.githubusercontent.com/jrouwe/JoltPhysics/master/PerformanceTest/RagdollScene.h |

**Game-engine gore primary material and open-source references:**

| # | Source |
|---|---|
| S59 | OpenJK GHOUL2 gore structures (Raven Software code release): https://raw.githubusercontent.com/JACoders/OpenJK/master/codemp/ghoul2/G2_gore.h (and G2_gore.cpp) |
| S60 | OpenJK gore placement algorithm and limits: https://raw.githubusercontent.com/JACoders/OpenJK/master/codemp/rd-vanilla/G2_misc.cpp |
| S61 | niftools format definition (BSDismemberBodyPartType, section and torso caps): https://raw.githubusercontent.com/niftools/nifxml/develop/nif.xml |
| S62 | SkinnedMeshDecals (texture-space decals on skinned meshes, VRAM budget): https://github.com/naelstrof/SkinnedMeshDecals |
| S63 | godot-slicer (Godot 3.2 port of EzySlice, convex only): https://github.com/cj-dimaggio/godot-slicer |
| S64 | EzySlice (monotone-chain cap triangulation, convex): https://github.com/DavidArayan/ezy-slice |
| S65 | SkeletalMeshDestruction (UE: hide bones plus pre-made pieces, avoidance phase): https://github.com/Lim-Young/SkeletalMeshDestruction |
| S66 | ActiveRagdoll (PID controllers following an animator): https://github.com/ashleve/ActiveRagdoll |
| S67 | ScriptHookVDotNet Euphoria helpers: https://github.com/scripthookvdotnet/scripthookvdotnet/tree/main/source/scripting_v3/GTA.NaturalMotion (EuphoriaHelpers.cs was read only in part, because the fetch was truncated) |
| S68 | GitHub topic listings: https://github.com/topics/dismemberment and https://github.com/topics/active-ragdoll |

In total, 68 sources (S1–S68) were read this session. All are on github.com or raw.githubusercontent.com, the only domains the proxy allowed.

### 18.2 Not opened (knowledge references; verify before relying on them)

- **R1** Vlachos A. "Rendering Wounds in Left 4 Dead 2." GDC 2010, Valve (Valve publications page).
- **R2** Vlachos A. "Water Flow in Portal 2." SIGGRAPH 2010 Advances course. (Flowmaps.)
- **R3** Green S. "Screen Space Fluid Rendering for Games." GDC 2010, NVIDIA.
- **R4** van der Laan W., Green S., Sainz M. "Screen Space Fluid Rendering with Curvature Flow." I3D 2009.
- **R5** Jimenez J. et al. "Separable Subsurface Scattering." Computer Graphics Forum 2015.
- **R6** d'Eon E., Luebke D. "Advanced Techniques for Realistic Real-Time Skin Rendering." GPU Gems 3, ch. 14, 2007.
- **R7** NaturalMotion Euphoria / Dynamic Motion Synthesis product material; GTA IV (2008), Red Dead Redemption (2010), GTA V (2013), RDR2 (2018).
- **R8** Dambuster Studios / Deep Silver. Dead Island 2 (2023) FLESH developer interviews and trailers.
- **R9** Raven Software. Soldier of Fortune (2000, GHOUL) and Soldier of Fortune II (2002, GHOUL2) marketing and reviews.
- **R10** Rebellion. Sniper Elite V2 (2012), 3 (2014), 4 (2017), 5 (2022), Resistance (2025).
- **R11** NetherRealm. Mortal Kombat (2011), Mortal Kombat X (2015), Mortal Kombat 11 (2019).
- **R12** Naughty Dog. The Last of Us Part II (2020).
- **R13** Rockstar Games. Red Dead Redemption 2 (2018).
- **R14** Bethesda. Fallout 3 (2008), New Vegas (2010), Fallout 4 (2015): VATS and dismemberment.
- **R15** Motive / EA. Dead Space (2023), "peeling" system developer material.
- **R16** id Software. Doom Eternal (2020), "destructible demons".
- **R17** Winter D.A. *Biomechanics and Motor Control of Human Movement*, 4th ed. Wiley, 2009, Table 4.1 (after Dempster 1955).
- **R18** Greene W.B., Heckman J.D. (eds.). *The Clinical Measurement of Joint Motion*. AAOS, 1994.
- **R19** Gore Box (sandbox, Steam).
- **R20** IO Interactive. Hitman series (Glacier engine).
- **R21** Playgendary. Kick the Buddy.
- **R23** NVIDIA product specifications: GeForce GTX 1660 / 1660 Super, GeForce RTX 3060.
- **R24** Capcom. Resident Evil 2 (2019), RE Engine.
- **R26** Tatarchuk N. "Practical Parallax Occlusion Mapping." GDC/I3D 2006; van Dongen J. "Interior Mapping." CGI 2008.
- Companion documents 01–04 in this folder (their own sources apply to all physiology numbers quoted here).
