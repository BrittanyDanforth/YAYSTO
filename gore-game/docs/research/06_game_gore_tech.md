# 06 — Gore Technology: AAA Techniques and a Godot 4.5 (Forward+) Implementation at 60 fps

Project: Gore Head (Godot 4.5, Forward+, GDScript + Godot shaders, Jolt physics, procedural assets from Blender).
Audience: rendering, VFX, physics, animation, tools and performance engineers.
Status: research reference v1, 2026-09-26. Independently fact-checked on 2026-09-26: see **Section 19**; rows marked "✓ verified" or "corrected: was X". The subject is a fictional, procedurally generated adult only.

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
- **Minimum-spec GPU: GTX 1660** (6 GB GDDR5, 192 GB/s, ~5.0 FP32 TFLOPS). **Recommended: RTX 3060** (12 GB, 360 GB/s, ~12.7 TFLOPS) [K-H R23]. ✓ verified (specs, F21/F22). In rasterised games the RTX 3060 is roughly **1.6×** faster than the GTX 1660: TechPowerUp's aggregate relative-performance chart puts the RTX 3060 12 GB at 157 % of the GTX 1660 [F22]. *(corrected: was 1.7–2.0× [K-M])*
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
    - `MAX_GORE_VERTS 3000` and `MAX_GORE_INDECIES 6000` are the static scratch arrays for **one** gore operation. `MAX_GORE_RECORDS 500` is a **global** pool of stored gore records: when the map holds more than 500, the oldest tag group is erased first (`while (GoreRecords.size()>MAX_GORE_RECORDS)`). It is not a per-operation or per-character limit. ✓ verified (numbers) against OpenJK `code/`, `codemp/rd-vanilla` and `codemp/rd-rend2/G2_gore_r2.h` via GitHub code search [F17, F18]. *(corrected: was "all three per operation")*
    - The placement code uses the **transformed (posed) vertices** (`TS.TransformedVertsArray`), computes `s = DotProduct(delta, saxis) + 0.5f` (same for t), drops triangles whose three vertices all fall outside [0, 1], and optionally culls front or back faces by `DotProduct(rayEnd, n)` ✓ verified [F18].
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
  - **section caps** `BP_SECTIONCAP_*` (values 101–113) ✓ verified;
  - **torso caps** `BP_TORSOCAP_*` (201–213) ✓ verified;
  - torso sections `BP_TORSOSECTION_*` (1000–13000, in steps of 1000: HEAD = 1000 … RIGHTLEG3 = 12000, BRAIN = 13000). *(corrected: was 1000–9000)* Verified against the generated niflib enum [F19].
  - **Skyrim** uses the same enum with `SBP_*` values (30–61, 130–150, 230). These are mostly armour-slot partitions. The only dismemberment entries are decapitation (`SBP_50_DECAPITATEDHEAD`, `SBP_51_DECAPITATE`, `SBP_150_DECAPITATEDHEAD`, `SBP_230_HEAD`) [F19]. Skyrim therefore severs only heads; limb partitions plus caps are a Fallout 3/New Vegas feature. Fallout 4 uses a newer mesh format with its own segment data, which I did not check [K-M].

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
| `max_gore_records_per_char` | 500 (reference) | records | In GHOUL2 this is a **global** pool with oldest-first eviction, not a per-character cap *(corrected)*. We use UV painting, so a cap applies to SDF wounds only (64 per character, Section 4) | [S60], [F17] ✓ verified |
| `projected_mark_max_verts` | 3,000 (reference) | vertices | GHOUL2 per-operation cap (indices: 6,000) | [S60], [F17] ✓ verified |
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
| **4.5** | **15 Sep 2025** (4.5.1: 15 Oct 2025; 4.5.2: 19 Mar 2026) | **Stencil buffer support** in spatial shaders and BaseMaterial3D (PR 80710); SMAA; BoneConstraint3D (PR 100984); **shader baker** for export (PR 102552); LookAtModifier3D (present since 4.4, PR 98446) | [S21], [S24], [S44], [S45], [S46]; ✓ verified: 4.5-stable release tag dated 15 Sep, milestone "4.5" due 2025-09-15, 4.5.2 tag dated 19 Mar [F1, F2, F4, F5] |
| 4.6 | 26 Jan 2026 | **Jolt becomes the default for new 3D projects** (PR 105737, milestone 4.6). New IK system: IKModifier3D, TwoBoneIK3D, SplineIK3D, FABRIK3D, CCDIK3D, JacobianIK3D (PR 110120, milestone 4.6). SSR overhaul (full- and half-resolution modes). Direct3D 12 becomes the default RD driver for new Windows projects (PR 113213) | [S21], [S22]; ✓ verified: 4.6 milestone closed 2026-01-26, release tag dated 26 Jan [F3, F6, F7]. SSR detail not re-checked |
| 4.7 | 18 Jun 2026 (4.7.2: 18 Aug 2026) | AreaLight3D, HDR output, clearcoat fixes, per-pass uniform pools for speed, particle scale/rotation improvements | [S21], [S23]; release date ✓ verified (tag dated 18 Jun) [F8]. Feature list not re-checked |
| 4.8 | in development (milestone still open on 2026-09-26) | `PhysicalBone3D.get_joint_rid()` (PR 112002, **merged 22 Jun 2026**). Generic6DOFJoint3D angular/linear **drive** torque/force limits (PR 119332, **merged 26 Jun 2026**). That PR unifies the spring and motor limits into one "drive" limit and deprecates the separate motor-limit parameters, so the 4.8 API names will differ from the 4.5 ones | [S48], [S47]; ✓ verified [F9, F10] |

**Recommendation:**
- Build on 4.5 as requested.
- **In 4.5, select Jolt explicitly** under Project Settings > Physics > 3D > Physics Engine. It became the default for new projects only in 4.6 [S22] [K-M for the menu path]. ✓ verified: the 4.5 manual gives exactly this path ("Project Settings > Physics > 3D > Physics Engine", then "Save & Restart") and says Godot Physics is still the default in 4.5 [F43]; PR 105737 made Jolt the default in 4.6 [F6].
- Keep the code free of 4.6+ APIs. Plan a move to 4.6 or later if built-in IK (wound clutching) or the new SSR (blood pools) is wanted.

### 2.2 Skinning happens before your vertex shader: `VERTEX` is post-skin

- In the RenderingDevice renderers (Forward+ and Mobile), `servers/rendering/renderer_rd/shaders/skeleton.glsl` is a **compute shader** (`#[compute]`, local size 64) [S2, S3]:
  - It applies blend shapes, then weighted bone matrices (up to **8 bones per vertex**).
  - It writes positions plus octahedral-encoded normals and tangents into a **destination vertex buffer (`dst_vertices`)**.
  - This is identical in `4.5-stable` [S3]. ✓ verified independently at `4.5.1-stable`: `#[compute]`, `local_size_x = 64`, blend shapes added before the bone transform, `if (params.skin_weight_offset == 4) { //using 8 bones/weights`, output to `dst_vertices` with octahedral normals/tangents [F11].
- The spatial `vertex()` function therefore receives **already-skinned** `VERTEX`, `NORMAL` and `TANGENT` in model space [S1, S2]. `BONE_INDICES`, `BONE_WEIGHTS` and `CUSTOM0–3` are read-only vertex built-ins [S1, S44]. ✓ verified in the 4.5 manual branch: `in vec4 CUSTOM0` ("When using extra UVs, xy is UV3 and zw is UV4"), `in uvec4 BONE_INDICES`, `in vec4 BONE_WEIGHTS`; VERTEX/NORMAL/TANGENT "presented in model space" unless `world_vertex_coords` [F12].
- **Consequences:**
  - A spatial shader has no built-in access to bone matrices and no built-in rest position [K-M].
  - To evaluate wounds in rest space, **store the rest position per vertex in `CUSTOM0`** (RGBA float) at import. Use `CUSTOM0.w` for a segment ID (Section 9), then pass it to `fragment()` as a varying.
  - Do this in an `EditorScenePostImport` script that copies `ARRAY_VERTEX` into `ARRAY_CUSTOM0`. It can also be done through extra UV sets from Blender (`CUSTOM0.xy = UV3`, `CUSTOM0.zw = UV4` [S1]), but Blender's glTF exporter flips V, so that path needs a correction [K-M].
  - **Precision (added in the fact-check) [D].** Declare the channel as `Mesh.ARRAY_CUSTOM_RGBA_FLOAT` (32-bit) in the surface format flags (`ARRAY_FORMAT_CUSTOM0_SHIFT` [F13]), not `ARRAY_CUSTOM_RGBA_HALF`. A half float has 10 mantissa bits, so between 1 m and 2 m it steps in 2⁻¹⁰ m ≈ **0.98 mm**. With the rest-space origin at the feet, every head vertex (≈ 1.5–1.8 m) would be quantised to ~1 mm, which is coarser than the 1–2 mm abrasion collar and the ≤ 1 mm stippling this design wants to resolve. If half precision is needed for memory, store the position relative to a per-segment origin (for example, the head centre, |p| < 0.16 m gives ~0.12 mm steps). The same rule applies to the RGBA16F position map in Section 4.1.
- `MeshInstance3D.bake_mesh_from_current_skeleton_pose()` exists but "Mesh data needs to be received from the GPU, stalling the RenderingServer" [S34]. Use it only rarely, for example once to freeze a severed part, and never per frame.

### 2.3 Getting wound data into shaders

| Mechanism | Limits | Use for | Source |
|---|---|---|---|
| Material uniform arrays (`uniform vec4 w[192]`) | Uniform buffer up to **65,536 bytes (4,096 vec4)** on desktop (**16,384 bytes / 1,024 vec4 on mobile**). `vec2`/`vec3` uniforms are padded to `vec4`. Arrays are allowed; structs are not | Per-character wound list (64 wounds × 3 vec4 = 3 KB). Requires a **unique ShaderMaterial per character**, which is fine for 1–3 characters | [S8]; ✓ verified in the 4.5 manual branch [F14] |
| Per-instance uniforms (`instance uniform`) | **Practical maximum 16 per shader. Scalars and vectors only: no arrays, no textures.** Set with `set_instance_shader_parameter()` | Per-body scalars: pallor, cyanosis, wetness, segment-visibility bits, eye state (pupil mm, corneal opacity) | [S8]; ✓ verified: "There is a practical maximum limit of 16 instance uniforms per shader"; "Per-instance uniforms do not support textures or arrays, only regular scalar and vector types" [F14] |
| Data textures (Image → ImageTexture, or Texture2DRD) | Any size. Update cost is proportional to upload size | >64 wounds; a 3D wound-lookup grid; vessel/organ lookup | [S37], [K-H] |
| Global uniforms (Project Settings > Shader Globals; `global_shader_parameter_set`) | Project-wide | Arena blood splat map and bounds, `time_minutes`, X-ray amount | [S8]; sampler support [K-M] |
| `Texture2DRD` written by compute on the **main** RenderingDevice | Must run through `RenderingServer.call_on_render_thread()`. A local RenderingDevice "cannot draw to the screen nor share data with the global RenderingDevice" | Damage atlases, floor splat map, flow | [S37], [S38], [S39]; ✓ verified in the 4.5-stable class reference [F15]. Nuance: a local device's results *can* reach a material through a CPU readback into an `ImageTexture`, but that costs a GPU→CPU→GPU round trip and a stall, so it is unsuitable per frame |

### 2.4 Stencil (new in 4.5)

- 4.5-stable defines spatial stencil modes [S44]:
  - `read`, `write`, `write_depth_fail`;
  - `compare_{always, less, equal, less_or_equal, greater, not_equal, greater_or_equal}`.

  The current master manual spells the depth-fail mode `write_if_depth_fail` [S1]. **Use the 4.5 spelling.** ✓ verified: the 4.5-stable `scene_shader_forward_clustered.cpp` registers exactly `read`, `write`, `write_depth_fail` and `compare_{less, equal, less_or_equal, greater, not_equal, greater_or_equal, always}` [F16]. *Clarification (fact-check): the engine source on master still registers `write_depth_fail` (Forward+ and Mobile), so `write_if_depth_fail` in the master manual is a documentation error, not a renamed mode.* The stencil state is applied only in the colour pass (`use_stencil = stencil_enabled && version == PIPELINE_VERSION_COLOR_PASS`), not in the depth prepass [F16].
- **"You can only read from the stencil buffer in the transparent pass. Any attempt to read in the opaque pass will fail."** [S1] The manual names outlines, **X-ray** and portals as intended uses [S1]. ✓ verified independently: the PR that added stencil (godotengine/godot #80710, milestone 4.5) says the depth-prepass conflict "has been resolved by simply not supporting opaque-pass stencil-read materials", and lists Forward+, Mobile and Compatibility as supported [F4].
- BaseMaterial3D also exposes a stencil mode; the official ragdoll demo draws outlines with it [S52].
- **Consequences:**
  - Stencil is ideal for the X-ray kill cam (Section 11).
  - It **cannot** build opaque "portal" wound holes (for example, "draw the inside only where the skin was cut") in the opaque pass. Holes use `discard` instead (Section 5).

### 2.5 Decals

- **Forward+ renders decals with clustering.** The default limit is **512 clustered elements per camera view**, shared by omni lights, spot lights, decals and reflection probes. ✓ verified in the 4.5 manual: "a default limit of 512 *clustered elements* … A clustered element is an omni light, a spot light, a decal or a reflection probe", adjustable under Project Settings > Rendering > Limits > Cluster Builder > Max Clustered Elements [F20]. *(corrected: was "omni, spot and area lights": `AreaLight3D` does not exist in 4.5; it arrives in 4.7, where the master manual adds it.)*
- **Screen coverage matters more than decal count** for performance. Use distance fade [S6]. Defaults are `distance_fade_begin` 40 m and `distance_fade_length` 10 m [S12]. ✓ verified: "a few large decals that cover up most of the screen will be more expensive to render than many small decals" [F20]; defaults 40/10, `distance_fade_enabled` false, `normal_fade` 0.0, `upper_fade`/`lower_fade` 0.3 in 4.5-stable Decal.xml [F23].
- **Cull mask (added in the fact-check).** `Decal.cull_mask` defaults to all 20 layers (1048575) [F23]. Put the victim, its inner meshes and debris on their own visual layer and **remove that layer from every world decal's cull mask**. Otherwise a wall or floor splat whose box overlaps a lying body also projects onto the skin and slides as the body moves.
- **Renderer limits (added).** Decals are Forward+ and Mobile only (not Compatibility). On Mobile only 8 decals can affect one Mesh resource [F20, F23]. This does not affect the Forward+ PC target.
- **Decals are projected every frame.** The fragment shader transforms the current view-space position by the decal's matrix and tests it against the box [S25]. ✓ verified at 4.5-stable: `vec3 uv_local = (decals.data[decal_index].xform * vec4(vertex, 1.0)).xyz;` followed by the box test and the `upper_fade`/`lower_fade` power curve, with `vertex` in view space [F24]:
  - On a skinned character, a decal therefore **does not follow skin deformation**. Parenting it to a `BoneAttachment3D` gives only rigid following.
  - A decal also **projects through the whole box**, onto the far side of a limb. `normal_fade` (0–1) and `upper_fade`/`lower_fade` (default 0.3) reduce this [S12, S25].
- **Decals cannot run custom shaders.** They affect albedo, normal, ORM and emission only [S6]. They **cannot affect transparency**, so they cannot cut holes [S12]. ✓ verified: "decals use purely fixed rendering logic. This means decals cannot use custom shaders"; "Decals cannot affect material properties other than the ones listed above, such as height" [F20]; "Decals cannot affect an underlying material's transparency, regardless of its transparency mode" [F23].
- Decal textures live in a shared atlas (sRGB for albedo and emission, linear for normal and ORM) [S25].
  - Adding a new unique texture at runtime marks the atlas dirty and rebuilds it [K-M]. **Preload every blood decal texture during loading.**
  - Changing `modulate`, size or rotation is free.

### 2.6 GPU particles

- Collision shapes are box, sphere, heightfield and SDF [S7]:
  - **The SDF must be baked in the editor.** "No runtime baking method exists for exported projects" [S16]. Resolution runs 16³ to 512³ [S16], and SDF has "larger" overhead than a heightfield [S7]. ✓ verified at 4.5-stable: "Baking … is only possible within the editor, as there is no bake method exposed for use in exported projects"; resolutions 16³–512³, **default 64³** [F25].
  - **The heightfield updates at runtime** ("When Moved" or "Always"), at resolution 256² to 8,192² (default 1,024²). It can follow the camera and filters meshes by layer mask [S17, S19]. ✓ verified at 4.5-stable [F26]. **Caveat (added in the fact-check):** in the default `UPDATE_MODE_WHEN_MOVED` the heightmap is re-rendered only when the *heightfield node itself* moves, not when meshes inside it move [F27]. A heightfield that must include the moving or falling body (Section 2.11) therefore needs `UPDATE_MODE_ALWAYS`, which re-renders the top-down depth every frame. Keep that heightfield small (for example 512² over 4 × 4 m, Section 2 parameters) and budget it inside "Particle simulation" in Section 13.3.
- **The engine caps collision shapes and attractors at 32 each per particle system** (`MAX_COLLIDERS = 32`, `MAX_ATTRACTORS = 32`) [S19]. ✓ verified in 4.5-stable `particles_storage.h`, which also defines `MAX_3D_TEXTURES = 7` (the per-system limit on SDF/heightfield textures) [F28].
- Particles collide **only** with `GPUParticlesCollision3D` nodes, not with physics bodies or skinned meshes [S15]. `COLLISION_RIGID` supports bounce and friction (0–1). `COLLISION_HIDE_ON_CONTACT` is also available [S18]. ✓ verified: "GPU particles are processed entirely on the GPU, they don't have access to the game's physical world" [F27]; collision modes and 0–1 ranges in 4.5-stable ParticleProcessMaterial.xml [F29].
- **Sub-emitters** have modes constant, at start, at end and at collision [S18]:
  - They can chain [S41].
  - The total number of live sub-particles is **capped by the sub-emitter's `amount`** [S41].
  - Explosiveness has no effect on a sub-emitter [S41].
  - ✓ verified: `SUB_EMITTER_CONSTANT` 1, `AT_END` 2, `AT_COLLISION` 3, `AT_START` 4 exist in 4.5-stable [F29]; "the total number of active particles from the sub-emitter is always capped by the `Amount` property on the sub-emitter particle system"; chaining and "Explosiveness … has no effect" confirmed in the 4.5 manual [F30]. Also: "A particle system which is its own sub-emitter does not work" [F30].
- **Changing `amount` restarts the system.** Vary the count with `amount_ratio` instead [S14]. CPU-controlled spawning uses `emit_particle()` with emit flags [S14]. ✓ verified at 4.5-stable: "Changing this value will cause the particle system to restart"; changing `amount_ratio` "doesn't cause the particle system to restart" [F31]. Note that GPU memory is still allocated for the full `amount` whatever the ratio [F31].
- **Trails** use "a mesh skinning system" with RibbonTrailMesh or TubeTrailMesh (`trail_enabled`, `trail_lifetime`) [S14]. ✓ verified [F31].
- **There is no GPU → CPU event channel.** A particle landing cannot spawn a `Decal` node or a physics event [K-H]. Section 8.4 gives the workarounds. ✓ verified: GPUParticles3D at 4.5-stable has a single signal, `finished`, and no method that reports collisions or per-particle positions. The only readback is `capture_aabb()` [F31].

### 2.7 Compute shaders and render-to-texture

- Compute shaders run only on the RenderingDevice renderers (Forward+ and Mobile) [S9].
- **Sharing a texture with materials:**
  1. Create it on the global device from `RenderingServer.get_rendering_device()`.
  2. Do the work inside `RenderingServer.call_on_render_thread()`.
  3. Wrap it in a `Texture2DRD`.

  The official `compute/texture` demo does exactly this: a water-ripple simulation in three ping-pong textures sampled by a material [S37, S38, S39]. ✓ verified: `call_on_render_thread` exists so that code touching "RenderingDevice and similar RD classes" runs "on the render thread"; Texture2DRD uses "a 2D texture created directly on the RenderingDevice as a texture for materials" [F15].
- **Avoid `sync()` on a local device.** It stalls the CPU; wait 2–3 frames instead [S9]. Very long dispatches risk a Windows TDR (driver timeout reset) [S9]. ✓ verified in the 4.5 manual; the TDR timeout is "usually 5 to 10 seconds", far above any gore dispatch [F32].
- **SubViewport painting** is the no-compute alternative:
  - Use `render_target_clear_mode = CLEAR_MODE_NEVER` to accumulate.
  - Use `render_target_update_mode = UPDATE_ONCE` to render only when painting [S36].
- **CompositorEffect** (Forward+/Mobile) injects custom rendering passes and runs on the render thread [S40].

### 2.8 Subsurface scattering (skin, flesh, brain)

- SSS is available **only in Forward+** [S29]. ✓ verified in the 4.5 manual branch (not in Mobile or Compatibility) [F33].
- It is a **screen-space separable blur** with horizontal and vertical passes, 8×8 workgroups, and **11, 17 or 25 taps** by quality. It has a dedicated **skin kernel** in the style of Jimenez's separable SSS, and a depth-scaled radius [S33, K-H R5]. ✓ verified at 4.5-stable: `local_size_x = 8, local_size_y = 8`, `USE_11/17/25_SAMPLES`, `skin_kernel` arrays, `params.vertical` pass direction, `mix(params.scale, depth_scale, params.depth_scale)` [F34]. `ss_effects.cpp` registers the variants in the order 11, 17, 25, which maps to quality Low, Medium, High [F35].
- **Default quality (added in the fact-check):** `rendering/environment/subsurface_scattering/subsurface_scattering_quality` defaults to **1 = Low (11 taps)** [F35]. The 17-tap (Medium) and 25-tap (High) settings in Section 12.2 must be set explicitly, at runtime through `RenderingServer.sub_surface_scattering_set_quality()` [K-M for the method name] or in Project Settings. Other defaults: `subsurface_scattering_scale` 0.05 and `subsurface_scattering_depth_scale` 0.01 [F35].
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
  - ✓ verified, with a version caveat: this advice ("it's usually best to limit Swing Span between 20 and 90 degrees, and the Twist Span between 20 and 45 degrees"; PinJoint "Leads to 'crumpling'") is in the **current master** manual only. The **4.5** manual branch says only that PhysicalBones get "an unconstrained pin joint assigned by default" and gives no joint types per bone or numeric limits [F36]. The advice still applies to 4.5 because the joint types are unchanged, but these are generic starting values. Use the anatomical limits in Section 10.1 where they differ (for example shoulder swing 90–110°, hip flexion 120°).
- **SkeletonModifier3D:**
  - It runs **after** the AnimationMixer and blends by `influence` [S11].
  - `Skeleton3D.modifier_callback_mode_process` chooses physics-rate, idle-rate or manual processing [S35].
  - The `skeleton_updated` signal fires after all modifiers [S35].
- **PhysicalBone3D:**
  - It has `_integrate_forces(state)`, `custom_integrator`, `apply_impulse()` and `apply_central_impulse()` [S13].
  - It is **kinematic when not simulating** [S28].
  - Its 6DOF joint data exposes per-axis `angular_spring_enabled/stiffness/damping/equilibrium_point` and linear equivalents. Cone joint data exposes swing and twist spans [S28].
  - **The internal joint RID, and so motors, is not reachable from script before 4.8** [S48]. ✓ verified: the 4.5-stable class reference lists no `get_joint_rid` (methods: `_integrate_forces`, `apply_central_impulse`, `apply_impulse`, `get_bone_id`, `get_simulate_physics`, `is_simulating_physics`) [F37]. The 4.5-stable implementation exposes 6DOF `joint_constraints/{x,y,z}/…` limit and spring properties and cone `swing_span`/`twist_span`/`bias`/`softness`/`relaxation`, with **no motor properties**, and sets `BODY_MODE_KINEMATIC` when simulation stops [F38]. PR 112002 (`get_joint_rid()`) was merged on 22 Jun 2026 for 4.8 [F9].
- **Godot's Jolt module:**
  - Maps 6DOF springs to Jolt motors in Position mode, using stiffness/damping or **frequency/damping**. Motors are velocity motors [S26]. ✓ verified at 4.5-stable: springs call `SetMotorState(axis, EMotorState::Position)` with `ESpringMode::FrequencyAndDamping` or stiffness mode. A per-axis `spring_limit` is applied through `SetTorqueLimit`/`SetForceLimit`, but it is initialised to `FLT_MAX` and is not exposed through the node API in 4.5, so springs are effectively **uncapped** [F39, F40]. PR 119332 (4.8) exposes it as a unified "drive" limit [F10].
  - Cone-twist maps to Jolt's `SwingTwistConstraint`, with swing and twist motors [S27].
  - **Unsupported properties are ignored with a warning** [S5, S26, S27]:
    - PinJoint3D: bias, damping, impulse clamp.
    - HingeJoint3D: bias, softness, relaxation.
    - ConeTwistJoint3D: bias, softness, relaxation.
    - Generic6DOFJoint3D: limit softness, restitution, damping, ERP.
    - SliderJoint3D: its angular properties and limit softness/restitution/damping.
- **Jolt project defaults** [S20] (✓ all verified at `4.5.1-stable` `jolt_project_settings.cpp` and by GitHub code search of master [F41, F42]):
  - Velocity steps 10; position steps 2.
  - Sleep below 0.03 m/s for 0.5 s.
  - CCD movement threshold 0.75; CCD max penetration 0.25.
  - Penetration slop 0.02 m; speculative contact distance 0.02 m; Baumgarte 0.2.
  - Max bodies 10,240; max body pairs 65,536; max contact constraints 20,480.
  - Max linear velocity 500 m/s; max angular velocity 2,700°/s.
  - Also: bounce velocity threshold 1.0 m/s (below this, restitution is ignored), `enable_ray_cast_face_index` false, temporary memory buffer 32 MB [F41].
- **Queries and threading:**
  - Ray-cast `face_index` is **−1 by default**. Enable "Physics > Jolt Physics 3D > Queries > Enable Ray Cast Face Index", which costs "about 25 %" more memory for `ConcavePolygonShape3D` [S5]. ✓ verified in the 4.5 manual branch [F43].
  - The module supports "Run On Separate Thread", though it "has not been tested very thoroughly" [S5]. ✓ verified: "it should be considered experimental" [F43].
  - Other 4.5 differences worth knowing (added in the fact-check) [F43]: contact impulses reported by Jolt are **estimated**, not exact, so do not drive bone-fracture thresholds from `get_contact_impulse()` alone (use relative velocity × mass as well). Kinematic bodies do not report contacts with static or kinematic bodies by default. Area3D–SoftBody3D interaction is unsupported.
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
| Particle collision with skinned bodies | [S15] | `GPUParticlesCollisionSphere3D`/`Box3D` attached to 4–8 bones. Top-down heightfield including the body layer (needs `UPDATE_MODE_ALWAYS`, since "When Moved" ignores moving meshes [F27]) |
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
| `godot_version` | 4.5.x (4.5.2) | — | Select Jolt explicitly | [S21], [S22]; ✓ verified [F1–F3, F6] |
| `skin_weights_per_vertex_max` | 8 | bones | Import with 4 unless the face needs 8 | [S2]; ✓ verified [F11] |
| `uniform_buffer_max` | 65,536 | bytes | Desktop (16,384 on mobile) | [S8]; ✓ verified [F14] |
| `instance_uniforms_max` | 16 | per shader | No arrays or textures | [S8]; ✓ verified [F14] |
| `clustered_elements_max` | 512 (default) | per view | Omni + spot lights + decals + reflection probes (no area lights in 4.5) | [S6]; ✓ verified [F20] |
| `particle_colliders_max` | 32 | per system | Also 32 attractors; 7 SDF/heightfield textures | [S19]; ✓ verified [F28] |
| `particle_sdf_resolution` | 64³–128³ for a 6–10 m room | voxels | 16³–512³ allowed (default 64³). Editor bake only | [S16], [G]; ✓ verified [F25] |
| `particle_heightfield_resolution` | 512² over 4×4 m around the victim (7.8 mm/texel) | texels | 256²–8,192² allowed. Default 1,024². `UPDATE_MODE_ALWAYS` if it must see the moving body | [S17], [S19], [G]; ✓ verified [F26, F27] |
| `sss_taps` | 17 (1660) / 25 (3060) | taps | 11/17/25 available. **Project default is Low = 11**: set it explicitly | [S33], [G]; ✓ verified [F34, F35] |
| `jolt_velocity_steps` | 10 (default) → 12–16 for stacked ragdoll contact | iterations | Raise only if joints stretch | [S20], [G]; default ✓ verified [F41] |
| `jolt_position_steps` | 2 (default) → 3–4 | iterations | Same | [S20], [G]; default ✓ verified [F41] |
| `jolt_raycast_face_index` | enabled | bool | +~25 % memory on concave shapes | [S5]; ✓ verified [F43] |
| `physics_ticks_per_second` | 60 | Hz | Enable physics interpolation (for render rates above 60 Hz; it is **not** needed for slow motion, see Section 11.2) | [S51], [G] |

### Visual/behavioural checklist (engine constraints)
- Nothing on the character slides when a joint bends. Test this with an elbow and a knee flexing through their full range.
- No wound "shows through" onto the far side of a limb.
- The first blood or the first gore mesh never causes a hitch. All gore materials, particle systems and decal textures are warmed up during loading. Godot compiles pipelines when a material is first drawn [K-M]. *(Refined in the fact-check: since 4.4, Forward+ and Mobile compile **ubershader pipelines at load time**, when an ArrayMesh loads and when the surface cache is built, and compile specialised pipelines in the background (PR 90400). 4.5 adds a **shader baker** export option that precompiles shaders for the target API (PR 102552) [F44, F5]. Draw-time compilation can still happen for variants first seen mid-game, such as a new material/feature combination. So still instance every gore material, particle system and inner mesh once, off-screen, during loading. Then verify with the `RENDERING_INFO_PIPELINE_COMPILATIONS_DRAW` performance monitor, which should stay at 0 during a scripted gore test [F44].)*

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
- ✓ verified (fact-check, recomputed): 75^0.425 = 6.26 and 178^0.725 = 42.8, so BSA = 0.007184 × 6.26 × 42.8 = **1.93 m²**. 2,048² × 0.70 = 2.936 M texels; 1.93 × 10⁶ mm² / 2.936 M = 0.657 mm² per texel, and √0.657 = **0.81 mm**. Head: 0.09 × 1.93 = 0.174 m², giving 0.059 mm² per texel, √ = **0.24 mm** [D]. The Lund–Browder chart splits the adult head and neck as ~7 % + ~2 %, so 9 % is the right total [K-H].
- **Position-map caveats (added in the fact-check) [D]:**
  - The position map (1,024²) is half the atlas resolution (2,048²), so each position texel serves 2 × 2 atlas texels through bilinear filtering. Inside a UV chart this is harmless. At chart borders, bilinear taps mix in gutter texels, so **dilate the position and normal maps** by ≥ 2 texels, or bake them at the atlas resolution (a 2,048² RGBA16F map is 33.6 MB).
  - **RGBA16F precision:** positions between 1 m and 2 m from the origin quantise to ~0.98 mm steps. For the head atlas, store head-relative positions: ~0.12 mm steps within ±0.16 m. Otherwise use RGBA32F. See Section 2.2.

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
- **Grid bounds correction (fact-check) [D].** A 0.8 m-wide box contains the body only if the bind pose has the arms at the sides. Rigs are normally bound in a **T-pose** (fingertip span ≈ stature, ~1.78 m for a 178 cm adult [K-H]) or an **A-pose** (~1.3–1.5 m span at 45° [D]). For a T-pose use ~1.8 × 0.4 × 2.0 m: 72 × 16 × 80 = 92,160 cells × 4 B ≈ **369 KB**. For an A-pose use ~1.5 m: 60 × 16 × 80 ≈ **307 KB**. Alternatively keep one small grid per limb segment. *(corrected: was 0.8 m wide / 164 KB, which leaves the arms outside the grid)*
- **Cell overflow [G].** A close-range shotgun blast puts up to 9 pellet tracks inside one or two 2.5 cm cells, more than the 4 index slots. At ≤ 1 m the shot behaves as a single mass (doc 01), so merge co-located pellet tracks into one wound volume before insertion. Otherwise keep the 4 largest wounds per cell and paint the rest.
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
| `wound_grid` | 72×16×80 for a T-pose bind (60×16×80 for an A-pose), 2.5 cm cells, 4 indices per cell (~0.3–0.37 MB) | cells | RGBA8 Texture3D. *(corrected: was 32×16×80 over 0.8 m width, too narrow for T/A-pose arms)* | [D], [G] |
| `bsa_default` check | 1.93 m²; 0.81 mm (body) / 0.24 mm (head) texels | — | ✓ verified (arithmetic) | [D] |
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
  - **Correction (fact-check):** branching is not enough. The 4.5 manual says `discard` "will prevent the depth prepass from being effective on any surfaces using the shader" [F14]. The cost attaches to the **presence** of `discard` in the compiled shader, not to whether the branch is taken. So:
    - build **two variants of the skin shader**, one without `discard` (tier a + b only) and one with it;
    - switch a body surface to the discard variant only when its first `open = true` wound appears;
    - keep the analytic cavity shading (5.2) in the no-discard variant, which is why it was designed without `discard`.

    With modular surfaces (Section 9.2), only the surfaces that actually carry an open wound pay the cost.
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
| Position + normal map for the **head** atlas (Section 4.1 specifies one set per atlas) | RGBA16F / RGBA8 | 1,024² each | 8.4 + 4.2 MB | Missing from the original total (added in the fact-check) | [D] |
| **Total per hero character** | | | **~126 MB** (113 MB without the head position/normal maps; ~150–170 MB with full mip chains on the four atlases) | Fits in 6 GB alongside the scene | [D]; *(corrected: was ~113 MB)*. Arithmetic ✓ verified: RGBA16F 2,048² = 4,194,304 × 8 B = 33.55 MB (decimal), RGBA8 2,048² = 16.78 MB |

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
   - Thin-film formula `u = ρ·g·sinθ·h² / (3μ)`: h = 0.2 mm on a vertical surface gives ~2 cm/s. *(Fact-check [D]: with ρ = 1,060 kg/m³ and whole-blood viscosity 4 mPa·s (typical at the ~100–500 s⁻¹ shear rates of such a film [K-H]), u = 1,060 × 9.81 × (2×10⁻⁴)² / (3 × 0.004) ≈ **3.5 cm/s**. ~2 cm/s corresponds to μ ≈ 7 mPa·s (low shear or partly clotted). Use 2–3.5 cm/s; the value stays inside the clamp, so no parameter changes.)*
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
| `pool_eq_thickness` | 2.5 (1.6–3.3) | mm | Capillary length of blood √(γ/ρg) ≈ 2.3 mm; puddle height 2·l_c·sin(θ/2) gives 2.3–3.3 mm for contact angles 60–90° [D]. 500 mL → 0.2 m² → Ø 50 cm; 1 L → Ø 71 cm | doc 03 §10.3; ✓ verified (arithmetic, consistent with doc 03's own fact-check). Doc 03 warns that real pools can be thinner (edge pinning); the absorbent-floor flag covers that |
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
| Jet (arterial) | Arterial, `tissue_factor` > 0.5, Q > ~300 mL/min | Pulsed ribbon or tube trail on a ballistic path, plus 30–80 breakup drops per s | Rhythmic spurting and splatter at heart rate | doc 03 §12 (ribbon, 30–80 drops/s ✓ consistent). **Fact-check note:** the "Q > ~300 mL/min" gate is a [G] value from this document; it is not in doc 03. Spurting is driven by **pressure**, not by flow. A small cut artery (digital, radial after spasm at 20–60 mL/min, scalp arteries) still spurts visibly in pulses [K-H]. Recommended gate: arterial wound open to the skin AND local orifice pressure above the doc 03 jet cut-off (MAP ≳ 25–30 mmHg, doc 03 §6.2). Flow then sets only the jet **thickness** and breakup-drop count, and pressure sets the height |
| Frothy (lung) | Lung or airway wound | Pink foam particles, bubbles in sync with breathing | Gurgling, sucking | doc 03 §9.3, doc 04 §9 |

**Jet dynamics** (doc 03 §4, §12):
- Launch speed `v0 = √(2·g·h_jet)`. The real jet height is 0.35–0.65 × the ideal pressure head, i.e. **0.55–1.0 m vertical at normal blood pressure**, which gives v0 ≈ 3.3–4.4 m/s [D]. ✓ verified (arithmetic): 120 mmHg × 133.32 Pa / (1,060 × 9.81) = 1.54 m ideal; × 0.35–0.65 = 0.54–1.0 m; √(2 × 9.81 × 0.55) = 3.28 m/s and √(2 × 9.81 × 1.0) = 4.43 m/s. Consistent with doc 03 §6.2, whose own fact-check notes that no measured human jet heights were found (Cv is a tuning value).
- Height scales with instantaneous pressure. It pulses at HR with modulation depth 0.5–0.8 (arterial) and **shrinks as MAP falls**.
- The jet stops below the critical closing pressure for small arteries (20–40 mmHg). (Doc 03 §6.2 uses "MAP < 25–30 mmHg: no jet", which falls inside this range; use 25–30 for consistency.)

**Caps:** ≤ 6 jets and ≤ 20 drips/streams (doc 03 §12). The physiology still accounts for the volume of every wound, including ones whose VFX is culled. ✓ consistent with doc 03 §12 ("≤ 6 jets, ≤ 20 drips"). The 32 surface-flow agents and the 1 / 15 / 300 mL/min regime edges are [G] values of this document. The 15 mL/min drip → stream edge is the lower end of doc 03's "above ~15–30 mL/min" [D].

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
| CPU hero drops | Drops ≥ 1 mm and drips | C++ ballistic step with drag at 60 Hz plus a Jolt raycast per step. On hit, place a `Decal` (walls, props) or add volume and time to the floor splat map, with the stain size and ellipse from doc 03 (spread 3–5.5 × drop diameter *(corrected: was 3–5×, per the doc 03 fact-check)*; L/W = 1/sin α) | ≤ 200 in flight; each raycast ~µs in C++ | doc 03 §10.1, [E] |
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
| `regime_drip_max` | 15 | mL/min | Lower end of doc 03's 15–30 | doc 03; ✓ consistent |
| `regime_stream_max` | 300 | mL/min | Use it only for **venous/non-pulsatile** flow. Arterial wounds jet whenever the orifice pressure exceeds ~25–30 mmHg, whatever the flow (fact-check) | [G] |
| `jet_height_normal_bp` | 0.55–1.0 | m | 0.35–0.65 × ideal | doc 03; ✓ verified (arithmetic) |
| `jet_v0` | 3.3–4.4 | m/s | √(2gh) | [D]; ✓ verified (arithmetic) |
| `jet_cutoff_pressure` (added) | 25–30 | mmHg | Below this, no jet: welling flow only | doc 03 §6.2 |
| `jet_pulse_depth` | 0.5–0.8 | × mean | At HR | [G] |
| `jets_max / drips_max` | 6 / 20 | — | | doc 03 §12; ✓ consistent |
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

**Masses for 75 kg (Winter/Dempster segment fractions) [K-H R17]:** ✓ verified in the fact-check against the Winter (2009) / Dempster table reproduced in the BMClab Biomechanics and Motor Control notebooks: hand 0.0060, forearm 0.0160, upper arm 0.0280, foot 0.0145, leg (shank) 0.0465, thigh 0.1000, head and neck 0.0810, thorax 0.2160, abdomen 0.1390, pelvis 0.1420, trunk 0.4970 [F45]. The fractions sum to 1.000 [D].

**Alternative data set (added in the fact-check).** Dempster's fractions come from cadavers (8 elderly males [K-H]). The Zatsiorsky–Seluyanov values adjusted by de Leva (1996) come from scanning living young adults [F45] (gamma-ray scanning [K-H]), use joint centres as segment ends, and differ markedly for the thigh and trunk. The notebook's de Leva **female** values are head 6.68 %, trunk 42.57 %, upper arm 2.55 %, forearm 1.38 %, hand 0.56 %, thigh 14.78 %, shank 4.81 %, foot 1.29 % [F45]. The de Leva **male** values, from my knowledge and not re-verified, are head 6.94 %, trunk 43.46 %, upper arm 2.71 %, forearm 1.62 %, hand 0.61 %, thigh 14.16 %, shank 4.33 %, foot 1.37 % [K-H].
- **Which to use:** because our ragdoll bodies start at the hip joint centre, de Leva's thigh (~10.6 kg rather than 7.5 kg at 75 kg) better matches the capsule geometry, and it gives a lower, heavier-legged fall.
- **Either set is defensible [G].** Keep Winter/Dempster if matching published biomechanics tables matters more; switch to de Leva if leg-dominated falls look too "top-heavy".

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
| Shoulder | Cone | Swing ≤ 90–110° (the current master manual suggests 20–90° [S4]; the 4.5 manual gives no values [F36]); twist ±70° |
| Elbow | Hinge | 0–145° (hyperextension ≤ 5°) |
| Forearm twist | Folded into the wrist | ±80° |
| Wrist | 6DOF | Flexion 70–80°, extension 60–70°, radial/ulnar 20°/30° |
| Hip | Cone | Flexion 120°, extension 20–30°, abduction 45°, rotation ±45° |
| Knee | Hinge | 0–135° |
| Ankle | 6DOF | Dorsiflexion 20°, plantarflexion 45–50°, inversion/eversion 30°/20° |

**Surface parameters [G]:** friction 0.6–0.9 (skin or cloth on floor), bounce 0.0–0.05, angular damping 0.5–2, linear damping 0.05–0.1.

### 10.2 Jolt settings for ragdolls

- Keep the defaults first: 10 velocity steps, 2 position steps [S20]. ✓ verified [F41, F42].
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
  - A 5 kg head that fully absorbs a pistol bullet gains **~0.55 m/s (9 mm) to ~0.75 m/s (.45 ACP)**. *(corrected: was "≤ 0.5 m/s"; 2.7/5 = 0.54 and 3.8/5 = 0.76)*
  - ✓ verified (arithmetic, fact-check): 0.00745 × 360 = 2.68; 0.0149 × 255 = 3.80; 9 × 0.0035 × 400 = 12.6 N·s; 2.68/75 = 0.036 m/s; 12.6/75 = 0.168 m/s. The masses and velocities match doc 01 §1 (9 mm 7.5–8.0 g at 350–380 m/s; .45 ACP 14.9 g at 250–260 m/s; 00 buck 9 × 8.4 mm pellets, 31.4 g, ~400 m/s, pellet count sourced there). Across doc 01's velocity range, 9 mm gives 2.6–3.0 N·s. A through-and-through shot transfers only part of this momentum, so these are upper bounds.
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
| Shoulder (whole arm) | ~0.25 with the elbow flexed; **~0.5 with the arm straight** (fact-check [D]: upper arm 2.1 kg at 0.14 m, forearm 1.2 kg at 0.44 m, hand 0.45 kg at 0.69 m, plus segment self-inertia ≈ 0.5 kg·m²) | ~160 (flexed) to ~320 (straight) | 60–100 |
| Elbow (forearm + hand) | ~0.06 (0.06–0.08 with segment self-inertia [D]) | ~38 (38–50) | 50–80 |
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
| `segment_mass_fractions` | table 10.1 | — | Winter/Dempster (de Leva alternative in 10.1) | [K-H R17]; ✓ verified [F45] |
| `joint_limits` | table 10.1 | ° | AAOS +10 % passive | [K-H R18], [G] |
| `ragdoll_friction / bounce` | 0.6–0.9 / 0–0.05 | — | | [G] |
| `ragdoll_ang_damp` | 0.5–2 | 1/s | | [G] |
| `impulse_9mm / 45acp / 00buck` | 2.7 / 3.8 / 12.6 | N·s | Apply the true value (upper bound; less for through-and-through) | [D]; ✓ verified (arithmetic, doc 01 inputs) |
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

1. **Skin material, opaque pass:** stencil `write`, `compare_always`, reference 1. Writing in the opaque pass is allowed; only reading is restricted [S1, S44]. ✓ verified: PR 80710 drops only opaque-pass stencil *reads*, and its own "standard x-ray" preset uses the same write-then-read pattern [F4].
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
  - **Answered in the fact-check [F46]:** `Engine.time_scale` scales `delta` but "does not automatically adjust `physics_ticks_per_second`". At 0.05× the engine still runs 60 physics ticks per **real** second, each covering 0.83 ms of game time, so ragdolls and debris stay smooth **without** interpolation. Interpolation matters only when the render rate exceeds the tick rate. Two consequences:
    - PD gains computed from `state.step` in `_integrate_forces` remain valid.
    - Any per-tick logic written in "ticks" rather than seconds runs 20× more often per game second.
  - **Audio (added):** `time_scale` "does not affect audio playback speed". For the slowed "inside the body" sound, set `AudioServer.playback_speed_scale` to match (or use pitch-shift/low-pass effects) and restore it on exit [F46].
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
| SSS | 17 taps (Medium) | 25 taps (High) | Forward+ only. Project default is Low (11 taps): set explicitly | [S29], [S33]; ✓ verified [F33–F35] |
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
| GTX 1660 Super | ~5.0 TFLOPS | 6 GB GDDR6 | 336 GB/s | **~1.09** [F22] *(corrected: was ~1.1–1.15 [K-M])* |
| RTX 3060 (12 GB) | ~12.7 TFLOPS | 12 GB GDDR6 | 360 GB/s | **~1.57** [F22] *(corrected: was ~1.7–2.0 [K-M])* |

✓ verified (specs): 192 / 336 / 360 GB/s and 5.0 / 5.0 / 12.7 TFLOPS [F21]; GTX 1660 = TU116, 1,408 shaders, 48 ROPs, boost 1,785 MHz [F22]. The relative-speed column is TechPowerUp's aggregate game benchmark. Compute-heavy passes (particles, painting) may scale closer to the 2.5× FP32 ratio, and bandwidth-bound passes closer to the 1.9× bandwidth ratio [D].

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
| **Total** | **7.5–13.0** | **4–7** | Target ≤ 13.5 on the 1660 |

*Fact-check of the totals [D]:*
- The 1660 column sums to 7.45–13.0 ms. *(corrected: the upper total was 13.5, which is the target, not the sum)*
- The 3060 column sums to 3.9–7.2 ms, which implies a 1.8–1.9× speed-up. TechPowerUp's aggregate ratio is 1.57× [F22]. Scaling the 1660 column by that gives **~4.7–8.3 ms on the RTX 3060**, so the `gpu_budget_3060` target of ≤ 8 ms (Section 13) may be exceeded in the worst case.
- Treat both columns as [E] until profiled.

**Overdraw arithmetic [D].** One mist sprite covering half the 1080p screen blends ~1.04 Mpx. Ten stacked sprites blend ~10 Mpx per frame, i.e. ~0.6 Gpx/s of blending at 60 fps. Blended RGBA16F traffic at that rate is a real fraction of the 1660's 192 GB/s. Hence **cap mist screen coverage at ~15–20 % of the screen and ≤ 4 layers**.
- *Quantified in the fact-check [D]:*
  - **Bandwidth.** 10.4 Mpx × 16 B (8 B read + 8 B write for RGBA16F) ≈ 166 MB per frame. At 192 GB/s that is **~0.9 ms per frame** of raw blend traffic before any texture fetches, about 5 % of the bandwidth.
  - **ROPs.** Blend throughput is not the limit: 48 ROPs × 1.785 GHz ≈ 86 Gpx/s, roughly half that for 64-bit blending [F22, K-M], which is ~70× the 0.6 Gpx/s needed.
  - **Shading.** The larger risk is **per-fragment shading** if mist sprites are lit through the clustered lights with shadow sampling.
  - **Recommendation.** Make mist `unshaded` (or vertex-lit), and sample a low-resolution lighting term instead of computing it per pixel. The 15–20 % / 4-layer cap then leaves a large margin.

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
| **Total** | **~4–10** | Target ≤ 12. *(corrected: was ~4–9; the listed maxima sum to 9.7 ms, including the worker-thread rivulet agents)* |

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
| `gpu_budget_3060` | ≤ 8 | ms | Headroom for SSR/SSIL. The fact-check rescaling (1.57× [F22]) gives 4.7–8.3 ms for the heavy scene, so SSR/SSIL may not fit in the worst case: profile first | [G] |
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

| # | Claim | Value | Source | Fact-check (2026-09-26) |
|---|---|---|---|---|
| 1 | Godot RD renderers skin in a compute pre-pass; `VERTEX` in `vertex()` is post-skin, model space | up to 8 weights per vertex | [S2], [S3], [S1] | ✓ verified [F11, F12] |
| 2 | Rest position must be supplied per vertex (e.g. `CUSTOM0`) for rest-space wounds | — | [D] from [S1], [S2] | ✓ verified (no bone-matrix built-ins; CUSTOM0–3 are `in`) [F12]. Added: use a 32-bit float custom format (half gives ~1 mm steps at 1–2 m) |
| 3 | Decals are projected per frame from view-space position through the decal box, so they slide on skin and project through limbs | — | [S25], [S12] | ✓ verified [F24] |
| 4 | Forward+ clustered elements (omni + spot lights + decals + reflection probes) default limit per view | 512 | [S6] | ✓ verified [F20]. *(corrected: "area lights" removed for 4.5)* |
| 5 | Decals: no custom shaders; albedo/normal/ORM/emission only; cannot affect transparency | — | [S6], [S12] | ✓ verified [F20, F23] |
| 6 | Stencil in 4.5: read only in the transparent pass; modes read/write/write_depth_fail/compare_* | — | [S1], [S44] | ✓ verified [F4, F16] |
| 7 | Instance uniforms: max 16 per shader, no arrays or textures; uniform buffer 64 KB on desktop | 16; 65,536 B | [S8] | ✓ verified [F14] (16 KB on mobile) |
| 8 | GPU particle collision shapes and attractors per system | 32 / 32 | [S19] | ✓ verified [F28] |
| 9 | Particle SDF collision bakes in the editor only; heightfield updates at runtime (256²–8,192²) | — | [S16], [S17] | ✓ verified [F25–F27]. Caveat: "When Moved" ignores moving meshes |
| 10 | Changing `GPUParticles3D.amount` restarts the system; use `amount_ratio` | — | [S14] | ✓ verified [F31] |
| 11 | Compute results reach materials only via the global RenderingDevice + `call_on_render_thread` + `Texture2DRD`; a local device cannot share | — | [S37], [S38], [S39] | ✓ verified [F15] (a slow CPU-readback path also exists) |
| 12 | SSS is Forward+-only, separable screen-space, 11/17/25 taps with a skin kernel | — | [S29], [S33] | ✓ verified [F33–F35]. Default quality is Low (11) |
| 13 | Jolt defaults: velocity steps 10, position steps 2; sleep 0.03 m/s for 0.5 s; max bodies 10,240 | — | [S20] | ✓ verified [F41, F42] |
| 14 | Jolt ray `face_index` is −1 unless enabled (+~25 % concave-shape memory) | — | [S5] | ✓ verified [F43] |
| 15 | PhysicalBone3D joint RID (motors) not script-accessible until 4.8; 4.5 offers 6DOF springs and `_integrate_forces` | — | [S48], [S28], [S13] | ✓ verified [F9, F37, F38]; spring limit = FLT_MAX in 4.5 [F39, F40] |
| 16 | Jolt is the default engine for new projects only from 4.6; select it in 4.5. 4.5 released 15 Sep 2025 | — | [S21], [S22] | ✓ verified [F1–F3, F6, F7] |
| 17 | Segment masses (Winter): head+neck 8.1 %, trunk 49.7 %, thigh 10 %, shank 4.65 %, foot 1.45 %, upper arm 2.8 %, forearm 1.6 %, hand 0.6 % | — | [K-H R17] | ✓ verified [F45]. de Leva alternative added |
| 18 | Bullet momentum is small: 9 mm 2.7 N·s, 00 buck 12.6 N·s, giving 0.04–0.17 m/s to a 75 kg body | — | [D] | ✓ verified (arithmetic; inputs from doc 01). Head speed corrected to 0.55–0.75 m/s |
| 19 | Atlas texel size: 2,048² gives ~0.8 mm over a 1.93 m² body and ~0.24 mm for the head | — | [D] | ✓ verified (arithmetic). Memory corrected to ~126 MB |
| 20 | GPU budget at 1080p for the heavy scene: 7.5–13.0 ms on a GTX 1660; 4–7 ms (per-pass estimate) or 4.7–8.3 ms (scaled by the measured 1.57× ratio) on an RTX 3060 | — | [E] | *(corrected: 1660 upper total was 13.5; RTX 3060 range widened)*. Still [E]: must be profiled |

---

## 17. Suspicious content

- **No prompt-injection attempts were found** in the fetched material. No fetched page asked me to run, download, install, change files, visit other URLs or reveal information.
- **A GitHub topic listing** (`github.com/topics/dismemberment`) included a repository presented as a "**leaked build**" of an unreleased game ("ILL-Leaked-Build-2026", 0 stars). Repositories advertising leaked game builds are a common malware lure. **I did not open it, and it is not linked or referenced anywhere in this document.**
- **Several README files contained package-install instructions**, for example a Unity Package Manager Git URL in SkinnedMeshDecals. These are normal README content, not instructions to me. I did not follow them and have not reproduced them.
- **Data-quality note:** one fetch summary misreported Godot 4.5's release year as 2024. The authoritative website data gives **15 September 2025** [S21], and that is the date used here.
- **Bash was not used.** Nothing was downloaded, installed or executed. No code was copied from the web into the project. The shader and pseudo-code outlines in this document were written for it.
- **Fact-check pass (2026-09-26):**
  - No prompt-injection text was found in any page, source file, pull-request description or code-search result read during the fact-check.
  - Pull-request descriptions contained normal build/test instructions and links to demo projects (for example a stencil demo repository, and a shell command in a Metal shader-baker PR). These are ordinary PR content, not instructions to me. I did not follow, open or reproduce them.
  - A TechPowerUp page was read from a third-party GitHub mirror (a student project's HTML snapshot), because techpowerup.com itself was blocked. I treated it as data only, and its numbers agree with a second GitHub-hosted spec table [F21, F22].
  - One fetch summary gave Godot 4.6's release year as "2025". The 4.6 milestone closing date (2026-01-26) and the release sequence show that **26 Jan 2026** is correct, and that is the date used.
  - In the fact-check, Bash was used once, for a read-only line count of this file, and not afterwards. Nothing was downloaded or executed.

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

---

## 19. Fact-check (independent verification, 2026-09-26)

### 19.1 Method and limits

- **Scope.** An independent fact-checker re-verified the load-bearing claims of this document, plus other numbers that looked off. Every claim was treated as unverified until checked against material found separately from the author's citations.
- **WebSearch was unavailable.** The session's search budget was already exhausted.
- **WebFetch worked only for GitHub.** docs.godotengine.org and techpowerup.com were blocked by the egress proxy.
- **Independence strategy.** Where the author read `master` files, I read the **4.5 manual branch** (`godot-docs/4.5`) and the **`4.5-stable` / `4.5.1-stable` tags**. I also used GitHub code search, pull-request records and milestone dates, and release-tag pages. For non-Godot facts I used different artefacts from the author's:
  - OpenJK code search across `code/`, `codemp/rd-vanilla` and `codemp/rd-rend2`;
  - the generated **niflib** enum, not nif.xml;
  - a biomechanics teaching notebook for the segment masses;
  - a TechPowerUp snapshot plus an NVIDIA-sourced spec table for GPU data.
- **Arithmetic** was recomputed by hand.
- Markers used in the body: **✓ verified** for rows checked, and ***(corrected: was X)*** for changed values.

### 19.2 Per-claim verdicts (the 20 load-bearing claims)

| # | Claim | Verdict | Evidence / change |
|---|---|---|---|
| 1 | Compute skinning pre-pass, 8 weights, identical at 4.5, `VERTEX` post-skin model space | **Confirmed** | `4.5.1-stable` skeleton.glsl: `#[compute]`, local size 64, `skin_weight_offset == 4 //using 8 bones/weights`, blend shapes then bones, `dst_vertices` [F11]; 4.5 manual: model space [F12] |
| 2 | Rest position must be baked into CUSTOM0 (read-only); no bone matrices/bind pose in spatial shaders | **Confirmed** (+ gap) | 4.5 manual: `in vec4 CUSTOM0`, only BONE_INDICES/WEIGHTS as bone built-ins [F12]. Added: use `ARRAY_CUSTOM_RGBA_FLOAT`; half precision gives ~1 mm steps at 1–2 m [D] |
| 3 | Decals re-projected per frame; slide and project through; no custom shaders; albedo/normal/ORM/emission; no transparency | **Confirmed** | 4.5-stable shader `uv_local = (xform * vec4(vertex,1)).xyz` in view space [F24]; 4.5 manual [F20]; Decal.xml 4.5 [F23] |
| 4 | 512 clustered elements per view shared by lights, decals, probes; cost ∝ coverage | **Confirmed with correction** | 4.5 manual: omni, spot, decal, reflection probe [F20]. "Area lights" removed: AreaLight3D is 4.7+ |
| 5 | Stencil modes read/write/write_depth_fail/compare_*; read only in transparent pass; suits X-ray, not opaque holes | **Confirmed** | 4.5-stable forward_clustered registers exactly these modes [F16]; PR #80710: "not supporting opaque-pass stencil-read materials" [F4]. Clarified that master *source* still uses `write_depth_fail` (the manual's `write_if_depth_fail` is a docs typo) |
| 6 | Instance uniforms ≤ 16, scalars/vectors only; 65,536 B / 4,096 vec4 desktop | **Confirmed** | 4.5 manual quotes [F14]. Added the mobile limit of 16,384 B and vec4 padding |
| 7 | MAX_COLLIDERS/ATTRACTORS 32; SDF editor bake 16³–512³; heightfield 256²–8,192² (default 1,024²); collide only with collision nodes; no GPU→CPU event | **Confirmed** (+ caveat) | 4.5-stable particles_storage.h [F28]; SDF/heightfield XML [F25, F26]; manual [F27]; GPUParticles3D has only a `finished` signal [F31]. Added: heightfield "When Moved" does not track moving meshes, so use Always for the body |
| 8 | Changing `amount` restarts; use `amount_ratio`; sub-emitter capped by its own amount | **Confirmed** | GPUParticles3D.xml 4.5 [F31]; subemitters manual 4.5 [F30]; AT_START exists (value 4) [F29] |
| 9 | Compute → materials only via global RD + call_on_render_thread + Texture2DRD; local RD cannot share | **Confirmed (nuance)** | RenderingServer.xml 4.5: local device "Cannot draw to the screen nor share data with the global RenderingDevice" [F15]. A slow CPU-readback path exists but is unsuitable per frame |
| 10 | SSS Forward+ only; separable; 11/17/25 taps; skin kernel | **Confirmed** (+ gap) | 4.5 manual [F33]; 4.5-stable shader [F34]; `ss_effects.cpp` order 11/17/25 [F35]. Added: project default quality = Low (11 taps) [F35] |
| 11 | Jolt defaults (10/2 steps; sleep 0.03 m/s, 0.5 s; 10,240 bodies); face_index −1 (+~25 % memory); softness/bias/restitution ignored with warning | **Confirmed** | `4.5.1-stable` jolt_project_settings.cpp and master code search [F41, F42]; 4.5 manual [F43]; 6DOF warnings in 4.5-stable source [F39] |
| 12 | 4.5: no script access to PhysicalBone3D joint motors; get_joint_rid in 4.8 (PR 112002); use PD torques or 6DOF springs (uncapped until 4.8) | **Confirmed** | PhysicalBone3D.xml 4.5 has no `get_joint_rid` [F37]; physical_bone_3d.cpp 4.5 has no motor properties [F38]; PR 112002 merged 22 Jun 2026, milestone 4.8 [F9]; Jolt 6DOF `spring_limit = FLT_MAX`, not exposed [F39, F40]; PR 119332 merged 26 Jun 2026 as unified "drive" limits [F10] |
| 13 | 4.5 released 15 Sep 2025; Jolt default only from 4.6 (26 Jan 2026); TwoBoneIK3D absent in 4.5; LookAtModifier3D and BoneConstraint3D present | **Confirmed** | 4.5-stable tag 15 Sep, milestone due 2025-09-15 [F1, F2]; PR 105737 in milestone 4.6, closed 2026-01-26 [F6]; 4.6 tag 26 Jan [F3]; IKModifier3D/TwoBoneIK3D PR 110120 in 4.6 [F7]; LookAtModifier3D PR 98446 in 4.4; BoneConstraint3D PR 100984 in 4.5 [F5] |
| 14 | GHOUL2 projects onto posed mesh and stores per-vertex gore UVs on own triangles; MAX_GORE_RECORDS 500, VERTS 3000, INDECIES 6000 | **Confirmed with correction** | Numbers and algorithm confirmed [F17, F18]. Corrected: MAX_GORE_RECORDS is a **global** pool with oldest-first eviction, not per operation |
| 15 | Bethesda BSDismemberBodyPartType partitions; section caps 101–113; torso caps 201–213 | **Confirmed with correction** | niflib enum [F19]. Corrected: torso sections are 1000–13000 (was 1000–9000). Added: Skyrim uses the enum only for armour slots and decapitation |
| 16 | 2,048² over 1.93 m² at 70 % → ~0.8 mm; head ~0.24 mm; ~113 MB per hero | **Arithmetic confirmed; memory corrected** | Recomputed 1.93 m², 0.81 mm, 0.24 mm [D]. Total memory is ~126 MB once the head's position and normal maps (specified in 4.1) are counted; ~150–170 MB with mips. Added: half-float position precision issue |
| 17 | Momentum 2.7 / 3.8 / 12.6 N·s → 0.04–0.17 m/s; reactions from tone | **Confirmed** (minor fix) | Arithmetic confirmed; inputs match doc 01 §1. Corrected the 5 kg head from ≤ 0.5 to 0.55–0.75 m/s |
| 18 | Winter/Dempster masses; manual cone-joint swing 20–90°, twist 20–45°, not pin | **Confirmed (version caveat)** | All ten fractions match the BMClab Winter (2009) table [F45]. The joint advice is in the **master** manual; the 4.5 manual has no numeric joint advice [F36]. Added de Leva alternative (thigh 14 % vs 10 %) |
| 19 | Flow → VFX regimes; jets 0.55–1.0 m, v0 3.3–4.4 m/s; caps 6/20/32; pools 2.5 mm | **Mostly confirmed; one design correction** | Jet arithmetic, 6/20 caps and 2.5 mm pool match doc 03 §6.2, §10.3 and §12 [D]. The 32-agent cap and the regime edges are [G]. Corrected: "Q > 300 mL/min" for jets is not from doc 03, and arterial spurting is pressure-gated (small arteries spurt at low flow). Stain spread updated to 3–5.5× from the doc 03 fact-check |
| 20 | GPU 7.5–13.5 ms (1660), 4–7 ms (3060); mist overdraw main risk, cap 15–20 % / 4 layers | **Corrected / refined** | Pass maxima sum to **13.0**, not 13.5. The measured 3060/1660 ratio is **1.57×** (not 1.7–2.0×) [F22], giving ~4.7–8.3 ms. The overdraw arithmetic now quantifies ~0.9 ms/frame of blend traffic at 10 half-screen layers; per-fragment lighting is the bigger risk, so make mist unshaded. Still [E] |

### 19.3 Other corrections made in the body

- **Section 0.3 and 13.1:** RTX 3060 relative raster speed changed to ~1.57× (was 1.7–2.0×). GTX 1660 Super ~1.09× (was 1.1–1.15×) [F22].
- **Section 2.1:** 4.8 items marked as merged on 22 and 26 Jun 2026, in a milestone still open on 2026-09-26. PR 119332 renames the concept to "drive" limits.
- **Section 4.4:** the wound-grid rest bounds were 0.8 m wide, which excludes the arms of a T- or A-pose bind. Changed to ~1.5–1.8 m (~0.3–0.37 MB). Added a pellet-overflow rule.
- **Section 5.3:** `discard` defeats the depth prepass for every surface using the shader, whether or not the branch is taken [F14]. Added the two-variant skin-shader rule.
- **Section 7.1:** the thin-film speed for h = 0.2 mm is ~3.5 cm/s at μ = 4 mPa·s (was ~2 cm/s). The clamp is unchanged.
- **Section 10.4:** shoulder effective inertia is ~0.5 kg·m² with the arm straight (0.25 applies only with the elbow flexed). Elbow 0.06–0.08.
- **Section 11.2:** `time_scale` keeps 60 physics ticks per real second, so slow motion is smooth without interpolation. Audio needs `AudioServer.playback_speed_scale` [F46].
- **Section 13.4:** CPU total ~4–10 ms (was ~4–9).

### 19.4 Gaps filled

1. **Pipeline stutter (Section 2 checklist).** 4.4 ubershaders plus load-time pipeline compilation (PR 90400), and the 4.5 shader baker (PR 102552). Verify warm-up with `RENDERING_INFO_PIPELINE_COMPILATIONS_DRAW` = 0 [F44, F5].
2. **SSS default.** The project default is Low (11 taps), so the Medium/High settings must be set explicitly [F35].
3. **Decal cull mask.** It defaults to all layers. Exclude the victim's layer from world decals [F23].
4. **Heightfield update mode.** "When Moved" ignores moving meshes [F27].
5. **Discard cost** is per shader, not per branch [F14].
6. **Custom-attribute precision.** Use 32-bit CUSTOM0 and relative or 32-bit position maps [D].
7. **Head position/normal maps** were missing from the memory total [D].
8. **Jolt behaviour.** Contact impulses are estimates. Kinematic–static contacts are off by default. Run-on-thread is experimental [F43].
9. **Jolt 6DOF springs** carry an internal `FLT_MAX` torque limit in 4.5 [F40].
10. **de Leva (1996) segment fractions** as an alternative to Dempster [F45, K-H].
11. **Slow-motion audio** and physics-tick behaviour under `time_scale` [F46].
12. **Arterial jet gating** should use pressure, not flow (doc 03 §6.2).

### 19.5 Not verified (left as tagged)

- AAA game descriptions (Sections 1.3, 1.5–1.11).
- Frame-time estimates [E].
- The 4.6 SSR overhaul and the 4.7 feature list.
- The Jolt benchmark body count (S56).
- The "8 elderly male cadavers" detail of Dempster's sample.
- de Leva **male** values (only the female values were visible in [F45]).
- `RenderingServer.sub_surface_scattering_set_quality` method name.
- The MultiMesh, LOD and occlusion statements in 2.10.
- Tissue colours (5.4), which are [K-M].

### 19.6 Fact-check sources (read 2026-09-26)

| # | Source |
|---|---|
| F1 | Godot 4.5-stable release tag (dated 15 Sep): https://github.com/godotengine/godot/releases/tag/4.5-stable |
| F2 | Milestone "4.5" (due 2025-09-15, closed 2025-09-18): https://github.com/godotengine/godot/milestone/22 ; 4.5.2-stable tag (dated 19 Mar): https://github.com/godotengine/godot/releases/tag/4.5.2-stable |
| F3 | Godot 4.6-stable release tag (dated 26 Jan): https://github.com/godotengine/godot/releases/tag/4.6-stable ; milestone "4.6" closed 2026-01-26: https://github.com/godotengine/godot/milestone/23 |
| F4 | PR #80710 "Add stencil support to spatial materials" (milestone 4.5): https://github.com/godotengine/godot/pull/80710 |
| F5 | 4.5/4.4 feature PRs: #102552 shader baker (4.5) https://github.com/godotengine/godot/pull/102552 ; #100984 BoneConstraint3D (4.5) https://github.com/godotengine/godot/pull/100984 ; #109970 SMAA debanding (4.5, implies SMAA present) https://github.com/godotengine/godot/pull/109970 ; #98446 LookAtModifier3D (4.4) https://github.com/godotengine/godot/pull/98446 |
| F6 | PR #105737 "Use Jolt Physics by default in newly created projects" (milestone 4.6): https://github.com/godotengine/godot/pull/105737 |
| F7 | PR #110120 "Add SkeletonModifier3D IKs as IKModifier3D" (4.6): https://github.com/godotengine/godot/pull/110120 ; PR #113213 D3D12 default (4.6): https://github.com/godotengine/godot/pull/113213 |
| F8 | Godot 4.7-stable release tag (dated 18 Jun): https://github.com/godotengine/godot/releases/tag/4.7-stable |
| F9 | PR #112002 "Add get_joint_rid() to PhysicalBone3D" (merged 22 Jun 2026, milestone 4.8): https://github.com/godotengine/godot/pull/112002 |
| F10 | PR #119332 "Add angular spring max torque and linear max force to Generic6DOFJoint3D" (merged 26 Jun 2026, milestone 4.8): https://github.com/godotengine/godot/pull/119332 |
| F11 | skeleton.glsl at 4.5.1-stable: https://raw.githubusercontent.com/godotengine/godot/4.5.1-stable/servers/rendering/renderer_rd/shaders/skeleton.glsl |
| F12 | Spatial shader reference, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/shaders/shader_reference/spatial_shader.rst |
| F13 | ArrayMesh class reference at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/ArrayMesh.xml |
| F14 | Shading language, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/shaders/shader_reference/shading_language.rst |
| F15 | RenderingServer and Texture2DRD at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/RenderingServer.xml ; https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/Texture2DRD.xml |
| F16 | Forward+ shader actions at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/servers/rendering/renderer_rd/forward_clustered/scene_shader_forward_clustered.cpp ; master code search (`stencil_mode_values`, forward_clustered and forward_mobile) |
| F17 | GitHub code search, JACoders/OpenJK: `MAX_GORE_RECORDS (500)`, `MAX_GORE_VERTS (3000)`, `MAX_GORE_INDECIES (6000)`, `MAX_LODS (8)` in code/rd-vanilla/G2_misc.cpp, codemp/rd-vanilla/G2_misc.cpp, codemp/rd-rend2/G2_gore_r2.h |
| F18 | OpenJK G2_misc.cpp (blob view): https://github.com/JACoders/OpenJK/blob/master/codemp/rd-vanilla/G2_misc.cpp |
| F19 | niflib generated enums (BSDismemberBodyPartType): https://raw.githubusercontent.com/niftools/niflib/develop/include/gen/enums.h |
| F20 | Using decals, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/3d/using_decals.rst |
| F21 | GPU spec table citing NVIDIA product pages, file `gpu_onboard.py` in https://github.com/michael-borck/gpu-onboard (GTX 1660 192 GB/s, 5.0 TFLOPS; 1660 Super 336, 5.0; RTX 3060 360, 12.7) |
| F22 | TechPowerUp GTX 1660 page (HTML snapshot mirrored on GitHub): https://raw.githubusercontent.com/Mosh333/csca5622_final_project/HEAD/data/gpu/geforce-gtx-1660.c3365.html (48 ROPs, 1,785 MHz boost; relative performance RTX 3060 12 GB 157 %, 1660 Super 109 %) |
| F23 | Decal class reference at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/Decal.xml |
| F24 | Forward+ scene shader at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/servers/rendering/renderer_rd/shaders/forward_clustered/scene_forward_clustered.glsl |
| F25 | GPUParticlesCollisionSDF3D at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/GPUParticlesCollisionSDF3D.xml |
| F26 | GPUParticlesCollisionHeightField3D at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/GPUParticlesCollisionHeightField3D.xml |
| F27 | Particle collision, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/3d/particles/collision.rst |
| F28 | particles_storage.h at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/servers/rendering/renderer_rd/storage_rd/particles_storage.h |
| F29 | ParticleProcessMaterial at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/ParticleProcessMaterial.xml |
| F30 | Sub-emitters, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/3d/particles/subemitters.rst |
| F31 | GPUParticles3D at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/GPUParticles3D.xml |
| F32 | Compute shaders, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/shaders/compute_shaders.rst |
| F33 | StandardMaterial3D, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/3d/standard_material_3d.rst |
| F34 | Subsurface scattering shader at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/servers/rendering/renderer_rd/shaders/effects/subsurface_scattering.glsl |
| F35 | Master code search: servers/rendering/renderer_rd/effects/ss_effects.cpp (variant order 11/17/25) and servers/rendering/rendering_server.cpp (`subsurface_scattering_quality` default 1 = Low; scale 0.05; depth scale 0.01). Master, not the 4.5 tag [K-M that it is unchanged in 4.5] |
| F36 | Ragdoll system, 4.5 manual branch (no numeric joint advice): https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/physics/ragdoll_system.rst ; compared with master (S4) |
| F37 | PhysicalBone3D class reference at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/PhysicalBone3D.xml |
| F38 | physical_bone_3d.cpp at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/scene/3d/physics/physical_bone_3d.cpp |
| F39 | Jolt 6DOF joint at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/modules/jolt_physics/joints/jolt_generic_6dof_joint_3d.cpp |
| F40 | Jolt 6DOF joint header at 4.5-stable: https://raw.githubusercontent.com/godotengine/godot/4.5-stable/modules/jolt_physics/joints/jolt_generic_6dof_joint_3d.h |
| F41 | Jolt project settings at 4.5.1-stable: https://raw.githubusercontent.com/godotengine/godot/4.5.1-stable/modules/jolt_physics/jolt_project_settings.cpp |
| F42 | Master code search: modules/jolt_physics/jolt_project_settings.cpp (velocity_steps 10, position_steps 2) and spaces/jolt_space_3d.cpp |
| F43 | Using Jolt Physics, 4.5 manual branch: https://raw.githubusercontent.com/godotengine/godot-docs/4.5/tutorials/physics/using_jolt_physics.rst |
| F44 | PR #90400 "Ubershaders and pipeline pre-compilation" (milestone 4.4): https://github.com/godotengine/godot/pull/90400 |
| F45 | BMClab, Body Segment Parameters notebook (Winter 2009 / Dempster table; de Leva female table): https://github.com/BMClab/BMC/blob/master/notebooks/BodySegmentParameters.ipynb |
| F46 | Engine class reference at 4.5-stable (`time_scale`, `physics_ticks_per_second`): https://raw.githubusercontent.com/godotengine/godot/4.5-stable/doc/classes/Engine.xml |
| — | In-repo cross-checks: doc 01 §1 (projectile masses and velocities), doc 03 §6.2, §10.3, §12 and its fact-check (jet arithmetic, pool thickness, caps, stain spread) |
