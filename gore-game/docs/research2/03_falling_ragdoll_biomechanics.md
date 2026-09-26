# 03 (round 2) — Falling, landing and ragdoll biomechanics

Project: gore simulator (Godot 4.5, Forward+, GDScript + Godot shaders, built-in Jolt, Skeleton3D + PhysicalBone3D ragdolls). Research round 2.
Audience: ragdoll/physics, animation, AI/behaviour and audio engineers. Clinical, factual tone. The subject is a fictional, procedurally generated adult.

Scope: the physical body used by the ragdoll and the active-ragdoll controller. The document covers:
- segment masses, centres of mass and moments of inertia;
- joint ranges of motion (active, passive, limp/dead, structural failure);
- joint torque capacity, passive stiffness and damping;
- how muscle-tone states map to drive gains;
- how each kind of collapse unfolds, frame by frame;
- how the body lands, bounces, slides, settles and rests;
- active-ragdoll control (PD, balance, Euphoria-style behaviour layering);
- concrete Godot 4.5 / Jolt setup;
- a numeric validation suite that makes the body read as heavy and real rather than floaty.

This document builds on the earlier files and does not repeat them:

| File | What it already covers | Cited here as |
|---|---|---|
| `docs/research/01_gunshot_wounds.md` | Ammunition data; whole-body knock-back 0.01–0.18 m/s | `[R1-01]` |
| `docs/research/03_bleeding_vessels.md` | Shock classes and the exsanguination sequence | `[R1-03]` |
| `docs/research/04_neuro_death_eyes.md` | Brainstem "cut strings" collapse (§2.3), fencing response, posturing, primary flaccidity, rigor mortis timing (§12.6) | `[R1-04 §x]` |
| `docs/research2/01_brain_injury_deficits.md` | Posturing joint targets (§18.2), hemiplegia, seizures, gait deficits | `[R2-01 §x]` |
| `docs/research2/02_reactions_to_being_shot_and_hit.md` | Reflex latencies, stagger model, seven fall archetypes A–G, protective-arm data, fall direction, syncope video data, brief Godot notes (§13) | `[R2-02 §x]` |

---

## 0. Read this first

### 0.1 Method and limits (important)

- **No new web content was read in this session.** The round-two sessions share a web-search budget of 200 calls, and it was already used up. The first three queries (de Leva table, Dempster/Winter table, trunk sub-segments) came back with a budget notice only. `WebFetch` was not used because the brief says the network policy blocks it.
- Values tagged `[S#]` therefore come **only from sources the round-two document 02 session had already found** through search summaries (URLs in §14). They are re-cited here and were not re-read.
- **Most numbers in this document are `[K]`.** They come from the standard literature of biomechanics, rehabilitation, forensic pathology and physics-based animation: de Leva / Zatsiorsky, Dempster / Winter, AAOS range-of-motion norms, Norkin & White, Riener & Edrich, Loram & Lakie, Hof, SIMBICON, DeepMimic, Tan–Liu–Turk stable PD, and the Mertz & Patrick neck tolerances. The work is named wherever possible so the team can check it.
- **The de Leva table was reproduced from memory.** It passes two internal checks:
  - the male mass fractions sum to 100.0 %;
  - the head and trunk centre-of-mass (CM) positions and radii of gyration agree to < 0.1 mm between de Leva's two alternative endpoint definitions.
  It is still marked (M) until someone opens `[S1]`.
- **Godot and Jolt API names and defaults are `[K]`** (knowledge up to 2025). Verify them against the Godot 4.5 documentation and Project Settings before hard-coding. §12 lists the checks in priority order.
- Every derivation marked `[E]` shows its arithmetic, so it can be redone with other inputs.
- **Independent fact-check (§15).** A second session re-derived every `[E]` number in §1, §3.4, §5.1 and §6, compared the `[K]` tables with the checker's own recall of the literature and with the fact-checked round-two document 02, and edited the file in place. Corrections are marked "corrected: was X"; confirmed rows are marked "✓ verified". The fact-check session also had **no web access** (its searches returned the same budget notice), so "✓ verified" means arithmetic or independent recall, not a re-read source.

### 0.2 Tags

| Tag | Meaning |
|---|---|
| `[S#]` | Sourced. URL in §14. Found by an earlier round-two session through search summaries; not re-read here. |
| `[K]` | Author's knowledge of the standard literature (named where possible). Not verified in this session. |
| `[E]` | Engineering estimate or derivation for the game. Arithmetic shown. |
| `[R1-0x §y]` / `[R2-0x §y]` | Earlier project documents. |
| (H) / (M) / (L) | Confidence that the real value lies in the stated range. |

### 0.3 Conventions

- **Reference body**: adult male, **75 kg, 1.75 m**, the same body as all earlier documents. Procedural variation is covered in §1.5.
- **Angles** are measured from anatomical neutral: standing, arms at the sides, palms facing the thighs. Flexion is positive, extension negative. Hyperextension is extension past neutral. "Rotation" of a limb means rotation about its long axis.
- **Units**: SI. Torque in N·m (Nm); stiffness in Nm/rad; damping in Nm·s/rad; moment of inertia (MOI) in kg·m².
- **Godot axes**: +Y is up and −Z is forward. Bone-local axes depend on the rig; map them once in the joint table (§8.2).
- **Physics tick**: the baseline is 60 Hz. §8.3 recommends 120 Hz for ragdolls the player sees up close.
- **Segment names** follow de Leva `[S1]`. The **upper trunk** runs from the suprasternal notch to the xiphoid, the **middle trunk** from the xiphoid to the navel (omphalion), and the **lower trunk** from the navel to the hip-joint level (the pelvis). The **head** runs from the vertex to cervicale (C7), neck included.

### Simulation parameters (conventions)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `body_mass` | 75 | kg | Reference body | [R2-02] |
| `stature` | 1.75 | m | | [R2-02] |
| `gravity` | 9.81 | m/s² | Do not scale gravity to fake weight (§8.6) | [K] |
| `physics_hz` | 60 (crowd) / 120 (hero) | Hz | §8.3 | [E] |

### Visual/behavioural checklist (conventions)
- One metre in the engine is one metre in the world. Every number in this document assumes SI units and a real 75 kg body.

---

## 1. Body segment inertial parameters

### 1.1 Which table to use: Dempster or de Leva

| Dataset | Subjects | Method | Known bias | Use in game |
|---|---|---|---|---|
| **Dempster 1955**, via Winter's textbook tables | 8 male cadavers, aged ~52–83 (mean ~69), lean (~60 kg) | Segmented cadavers; pendulum MOI | **Thigh 10.0 %, trunk 49.7 %** ✓ verified [K] (H). **Corrected (reason): was "elderly and lean: thigh too light, trunk too heavy".** The gap comes mostly from **different segment boundaries** (where the thigh–trunk and head–trunk cuts are made, and Dempster's trunk runs from the greater trochanter to the glenohumeral joint), and only partly from the elderly, lean cadaver sample and post-mortem fluid loss | Cross-check only |
| **Zatsiorsky–Seluyanov**, adjusted by **de Leva 1996** `[S1]` | 100 young living men (mean ~24 y, ~73 kg) and 15 women | Gamma-ray mass scanning; de Leva moved the endpoints to joint centres | Athletic young adults | **Primary table** |

Where the tables disagree, **use de Leva** `[K] (H)`. It comes from living, young, normal-weight adults, its endpoints are joint centres (which matches a skeleton rig), and it splits the trunk into three parts, which a three-body spine needs. The largest disagreements are the thigh (10.0 vs 14.16 %), the trunk (49.7 vs 43.46 %) and the head+neck (8.1 vs 6.94 %). Those gaps shift the standing CM by ~2–3 cm ✓ (fact-check `[E]`: moving ~6 kg of thigh mass up to trunk level raises the CM ~3–4 cm; Dempster's heavier shanks and feet take back ~0.5–1 cm).

**Corrected: was "and change leg-swing inertia by ~40 %".** Recomputed `[E]` with the §1.3 lengths:
- the **thigh's own** MOI about the hip differs by ~35 % (Dempster 0.39 vs de Leva 0.53 kg·m²);
- but the **whole-leg swing inertia about the hip is almost identical, ≈ 2.67 kg·m² with either table**, because Dempster's heavier shank (4.65 vs 4.33 %) and foot (1.45 vs 1.37 %) sit far from the hip and compensate.
- The table choice therefore matters for where the mass sits in the trunk and thigh (CM height, trunk inertia, how a hit thigh moves), not for leg-swing timing. de Leva stays the primary table because its endpoints are joint centres.

### 1.2 de Leva (1996) adult male: relative values `[S1]` (M, reproduced from memory; see §0.1) — ✓ verified (fact-check)

Fact-check `[K]` / `[E]`: every length, mass %, CM % and radius below matches the checker's independent recall of de Leva's Table 4 (male), including the sub-trunk rows. An extra consistency test that a mis-remembered row would break: the three sub-trunk CMs recombine to **241.6 mm** below suprasternale (15.96 × 51.2 + 16.33 × 267.7 + 11.17 × 475.3, divided by 43.46), against **238.6 mm** for the whole trunk (44.86 % × 531.9). They differ by 3 mm. The source population is 100 men (mean ~24 y, 1.741 m, 73.0 kg) and 15 women (~19 y, 1.735 m, 61.9 kg) ✓ [K] (M). The PDF was still not opened, so confidence is raised from M to M–H, not to H.

CM position is given as a percentage of segment length from the first-named (proximal or cranial) endpoint. Radii of gyration are percentages of segment length about three axes through the segment CM:
- **r_AP**: about the anteroposterior axis (frontal-plane motion: lateral bending, abduction);
- **r_ML**: about the mediolateral axis (sagittal-plane motion: flexion–extension);
- **r_long**: about the long axis (twist).

| Segment | Endpoints | Mean length (mm) | Mass % | CM % | r_AP % | r_ML % | r_long % |
|---|---|---|---|---|---|---|---|
| Head + neck | Vertex → C7 (cervicale) | 242.9 | 6.94 | 50.02 | 30.3 | 31.5 | 26.1 |
| Trunk (whole) | C7 → mid-hip-joint | 603.3 | 43.46 | 51.38 | 32.8 | 30.6 | 16.9 |
| Upper trunk | Suprasternale → xiphoid | 170.7 | 15.96 | 29.99 | 71.6 | 45.4 | 65.9 |
| Middle trunk | Xiphoid → omphalion | 215.5 | 16.33 | 45.02 | 48.2 | 38.3 | 46.8 |
| Lower trunk | Omphalion → mid-hip-joint | 145.7 | 11.17 | 61.15 | 61.5 | 55.1 | 58.7 |
| Upper arm | Shoulder joint centre → elbow joint centre | 281.7 | 2.71 | 57.72 | 28.5 | 26.9 | 15.8 |
| Forearm | Elbow → wrist joint centre | 268.9 | 1.62 | 45.74 | 27.6 | 26.5 | 12.1 |
| Hand | Wrist → 3rd metacarpal head | 86.2 | 0.61 | 79.00 | 62.8 | 51.3 | 40.1 |
| Thigh | Hip → knee joint centre | 422.2 | 14.16 | 40.95 | 32.9 | 32.9 | 14.9 |
| Shank | Knee → lateral malleolus | 434.0 | 4.33 | 44.59 | 25.5 | 24.9 | 10.3 |
| Foot | Heel → tip of longest toe | 258.1 | 1.37 | 44.15 | 25.7 | 24.5 | 12.4 |

**Checks** `[E]`:
- Masses: 6.94 + 43.46 + 2 × (2.71 + 1.62 + 0.61 + 14.16 + 4.33 + 1.37) = **100.00 %**.
- Upper + middle + lower trunk = 43.46 % = the whole trunk.
- The sub-trunk lengths sum to 531.9 mm, which equals suprasternale → mid-hip. C7 sits 71.4 mm above suprasternale.
- The trunk CM computed from C7 (51.38 % × 603.3 = 310 mm) and from suprasternale (44.86 % × 531.9 + 71.4 = 310 mm) agree.

**Female values** (mass %, for procedural bodies) `[S1]` (M): head 6.68, trunk 42.57, upper arm 2.55, forearm 1.38, hand 0.56, thigh 14.78, shank 4.81, foot 1.29. They sum to 100.0 % ✓ verified (sum 99.99 %; values match the checker's recall; sub-trunk split 15.45 / 14.65 / 12.47 % `[K]` (M)).

### 1.3 Absolute values for the 75 kg, 1.75 m reference body `[E]` from §1.2 — ✓ verified (every mass and MOI recomputed; all within rounding)

Lengths are scaled by 1.75 / 1.741 = 1.005. MOI = m × (r × L)², about the segment CM.

| Segment | Mass (kg) | Length (m) | CM from proximal end (m) | I_AP (kg·m²) | I_ML (kg·m²) | I_long (kg·m²) |
|---|---|---|---|---|---|---|
| Head + neck | 5.21 | 0.244 | 0.122 below vertex | 0.0285 | 0.0308 | 0.0211 |
| Upper trunk | 11.97 | 0.172 | 0.052 below suprasternale | 0.181 | 0.073 | 0.153 |
| Middle trunk | 12.25 | 0.217 | 0.098 below xiphoid | 0.134 | 0.084 | 0.126 |
| Lower trunk (pelvis) | 8.38 | 0.146 | 0.090 below navel | 0.068 | 0.055 | 0.062 |
| Trunk (single body) | 32.60 | 0.606 | 0.311 below C7 | 1.288 | 1.121 | 0.342 |
| Upper arm (each) | 2.03 | 0.283 | 0.163 | 0.0132 | 0.0118 | 0.0041 |
| Forearm (each) | 1.22 | 0.270 | 0.124 | 0.0068 | 0.0062 | 0.0013 |
| Hand (each) | 0.46 | 0.087 (to knuckle) | 0.068 | 0.0014 | 0.0009 | 0.0006 |
| Thigh (each) | 10.62 | 0.424 | 0.174 | 0.207 | 0.207 | 0.042 |
| Shank (each) | 3.25 | 0.436 | 0.195 | 0.040 | 0.038 | 0.0065 |
| Foot (each) | 1.03 | 0.259 | 0.115 from heel | 0.0046 | 0.0042 | 0.0011 |
| **Sum** | **75.0** | | | | | |

### 1.4 Dempster / Winter values for comparison `[K] (H)`

| Segment | Mass fraction | CM from proximal (fraction of length) | Radius of gyration about CM (fraction of length) |
|---|---|---|---|
| Hand | 0.006 | 0.506 | 0.297 |
| Forearm | 0.016 | 0.430 | 0.303 |
| Upper arm | 0.028 | 0.436 | 0.322 |
| Foot | 0.0145 | 0.50 | 0.475 |
| Shank | 0.0465 | 0.433 | 0.302 |
| Thigh | 0.100 | 0.433 | 0.323 |
| Head + neck | 0.081 | 1.000 (C7–T1 to ear canal) | 0.495 |
| Thorax / abdomen / pelvis | 0.216 / 0.139 / 0.142 | 0.82 / 0.44 / 0.105 | — |
| Trunk | 0.497 | 0.50 | — |

For the 75 kg body the thigh moves from 7.5 kg (Dempster) to 10.6 kg (de Leva). In Dempster the arms are 5.0 % of body mass per side against 4.94 % in de Leva, so the arms agree well.

### 1.5 Head and neck split, clavicles, procedural variation

- **Head vs neck.** de Leva gives head + neck together as 5.21 kg. Split them for a rig with separate neck and head bones `[K] (M)`:
  - **head 4.4 kg**, CM ~3.5 cm above and ~1–1.5 cm in front of the occipital condyles, pitch MOI ≈ 0.022 kg·m²;
  - **neck 0.8 kg**.
  - For reference, the Hybrid III 50th-percentile male crash-dummy head is 4.54 kg with a pitch MOI of ~0.022 kg·m² `[K] (M)`.
- **Clavicle and scapula** are inside the upper trunk mass. If the rig simulates clavicle bodies, give each **0.3–0.5 kg** taken from the upper trunk `[E]`, or better, do not simulate them (§8.1).
- **Procedural bodies** `[E]`:
  - Scale lengths with stature.
  - Scale masses with body mass, but move mass toward the trunk for higher body fat: +1 % trunk share per +5 kg/m² BMI above 23, taken proportionally from the limbs `[E] (L)`.
  - Use the female fractions (§1.2) for female bodies.
  - Recompute the MOIs from the new masses and lengths with the §1.2 radii.

### 1.6 Whole-body values and landmark heights (1.75 m male) `[K] (M)` (Drillis–Contini proportions, rounded)

| Landmark | Height (m) | Fraction of stature |
|---|---|---|
| Vertex | 1.75 | 1.000 |
| Eye | 1.63 | 0.936 |
| C7 / shoulder joint | 1.50 / 1.43 | 0.86 / 0.818 |
| Xiphoid / navel | ~1.26 / ~1.05 | 0.72 / 0.60 |
| Hip joint centre | ~0.90 | 0.51–0.53 |
| Knee joint | 0.50 | 0.285 |
| Ankle | 0.07–0.08 | 0.039–0.045 |
| Elbow / wrist / fingertip (arm hanging) | 1.10 / 0.84 / 0.66 | 0.63 / 0.48 / 0.38 |
| **Whole-body CM, standing** | **0.96** (0.95–0.98) | 0.55–0.56 |
| CM lying supine or prone | 0.10–0.12 | — |

**Whole-body MOI** `[E]` (summed from §1.3 in the standing pose; agrees with published whole-body values of 11–13 kg·m² `[K]`):

| Axis | kg·m² | Use |
|---|---|---|
| Mediolateral axis through the CM (pitch) | **≈ 11.8** ✓ verified (re-summed segment by segment with de Leva CM heights: 12.1) | Forward and backward toppling |
| About the ankles (pitch) | **≈ 69.5** ✓ verified (69.5–72 depending on whether the feet are included) | Rigid topple: ω = √(m·g·h / I) = √(72.9 × 9.81 × 0.89 / 69.5) = **3.0 s⁻¹** ✓ verified (3.03; 3.04 with the de Leva CM height) |
| Long axis (twist, arms at the sides) | **≈ 1.1** ✓ (re-summed: ~1.0) | Spin from off-centre hits and hook punches |

### 1.7 Collider dimensions (1.75 m male) `[K] (M)` anthropometry, `[E]` shapes

Set every collider **0.5–1.0 cm inside the skin mesh**. The visible flesh then touches the floor and can be squashed in the shader (§6.5). A collider larger than the mesh leaves the body hovering 1–3 cm above the floor, which reads as weightless.

| Body | Shape | Size | Notes |
|---|---|---|---|
| Head | Convex hull of 12–20 points, or capsule r 0.08 m × 0.24 m tall | Head length 0.195–0.20, breadth 0.15–0.155, vertex–chin 0.23–0.24 m | A sphere rolls forever. A hull settles onto the occiput or cheek (§6.5) |
| Neck | Capsule | r 0.05, length 0.10–0.12 | Neck circumference 0.38–0.40 m |
| Upper trunk (C7 to xiphoid, with the shoulder girdle) | Box (rounded) or convex hull | w 0.32–0.34 × d 0.22–0.24 × h 0.24 | Biacromial breadth 0.40 m |
| Middle trunk | Box or capsule | w 0.30 × d 0.21 × h 0.22 | |
| Lower trunk (pelvis) | Box or hull | w 0.34–0.36 × d 0.22 × h 0.20 | Hip breadth 0.35–0.37 m; include the buttocks |
| Upper arm | Capsule | r 0.042–0.045, length 0.28 | Circumference 0.30–0.33 m |
| Forearm | Capsule | r 0.035–0.038, length 0.27 | |
| Hand (to fingertips) | Box | 0.09 × 0.03 × 0.19 | |
| Thigh | Capsule | r 0.075–0.08, length 0.42 | Circumference 0.55–0.60 m |
| Shank | Capsule | r 0.050–0.052, length 0.43 | Calf circumference 0.37–0.39 m |
| Foot | Box | 0.10 × 0.08 × 0.26 | Heel ~0.05 m behind the ankle axis |

### 1.8 Chain inertias and gravity loads about each joint `[E]`

- **I_eff** is the MOI of everything distal to the joint (the "child subtree"), about the joint's flexion axis, in the reference pose.
- **Gravity stiffness** k_g = m_sub × g × d_sub, where d_sub is the distance from the joint to the subtree CM. It is the stiffness gravity adds (hanging) or removes (inverted, as for the stance leg, spine and neck).
- **The drive gains in §4 are computed from these two numbers.**

| Joint | Subtree | Mass (kg) | I_eff (kg·m²) | k_g (Nm/rad) | Configuration |
|---|---|---|---|---|---|
| Head (occiput–C2) | head | 4.4 | 0.027 | 1.5 (plus a static forward moment of ~0.6 Nm) | Inverted: the head falls forward when tone is lost |
| Neck (C2–T1) | head + neck | 5.2 | 0.11 | 6.3 | Inverted |
| Spine upper (T10, xiphoid level) | upper trunk + arms + head | 24.6 | 1.4 | 35 | Inverted |
| Spine lower (L3/L4, navel level) | + middle trunk | 36.9 | 4.3 | 101 | Inverted |
| Hip (stance) | head, arms and trunk (HAT) | 45.2 (both hips) | **~7.4** (corrected: was ~6.6) | **149 both / 75 per hip** (corrected: was 159 / 79) | Inverted. Recomputed from §1.3: HAT CM 1.230 m, 0.336 m above the hip joints. Both old values were within ~10 % |
| Hip (swing, straight leg) | leg | 14.9 | 2.67 | 47 | Hanging |
| Knee (stance) | everything above the knee | 66.4 (both) | — | 358 both / **179 per knee** | Inverted |
| Knee (swing) | shank + foot | 4.28 | 0.41 | 11 | Hanging |
| Ankle (stance) | everything above the ankle | 72.9 (both) | 69.5 (whole body) | 636 both / **318 per ankle** | Inverted |
| Ankle (swing) | foot | 1.03 | 0.009 | ~0.6 | Hanging |
| Shoulder | whole arm | 3.70 | 0.45 | 10.9 | Hanging |
| Elbow | forearm + hand | 1.67 | 0.078 | 3.0 | Hanging |
| Wrist | hand | 0.46 | 0.0035 | 0.31 | Hanging |

Working (examples):
- Arm about the shoulder: upper arm 0.0132 + 2.03 × 0.163² = 0.067; forearm 0.0068 + 1.22 × 0.406² = 0.207; hand 0.0014 + 0.46 × 0.621² = 0.178. **Total 0.452 kg·m².** The arm CM lies 0.30 m from the shoulder.
- Leg about the hip (straight): thigh 0.207 + 10.62 × 0.174² = 0.53; shank 0.040 + 3.25 × 0.618² = 1.28; foot 0.0046 + 1.03 × 0.91² = 0.86. **Total 2.67 kg·m².** The leg CM lies 0.32 m from the hip.
- Fact-check `[E]` (all recomputed): leg about the hip 2.67 ✓; arm about the shoulder 0.452 ✓ (0.455); shank + foot about the knee 0.41 ✓; forearm + hand about the elbow 0.078 ✓; head + neck about C7 0.108 ✓. Stance gravity stiffness: ankle 318 ✓ (329 with the de Leva CM height of 0.97 m); knee 179 ✓ (185–195, depending on whether the knee sits at 0.50 m as in §1.6 or at 0.47 m as the de Leva thigh length implies); hip corrected to 75 per side (row above).
- Known small inconsistency `[E]`: the de Leva thigh + shank lengths (0.424 + 0.436 m) put the lateral malleolus ~3 cm lower than the §1.6 landmark heights do. Keep the de Leva lengths for the bodies and let the foot collider absorb the difference.

### Simulation parameters (segments)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `seg_mass` | table §1.3 (head 4.4 + neck 0.8 if split) | kg | Set explicitly on each PhysicalBone3D; do not rely on density | [S1] (M) [E] |
| `seg_com_offset` | table §1.3 | m | Use to place `body_offset` / collider centre | [S1] (M) |
| `seg_inertia` | table §1.3 | kg·m² | If the engine derives inertia from shapes, check it lands within ±30 % | [E] |
| `mass_ratio_adjacent_max` | ≤ 10 : 1 (neck 0.8 kg next to a 12 kg upper trunk is 15 : 1: raise the neck to ≥ 1.2 kg or merge it into the head) | — | Chains with large mass ratios wobble and stretch | [K] (M) |
| `com_height_standing` | 0.96 | m | | [K] |
| `I_body_pitch_com` / `I_body_ankle` / `I_body_long` | 11.8 / 69.5 / 1.1 | kg·m² | ✓ verified (re-summed 12.1 / 69.5–72 / ~1.0) | [E] |
| `k_grav_stance_per_side` | ankle 318, knee 179, hip 75 (corrected: was 79) | Nm/rad | §1.8 | [E] |
| `collider_inset` | 0.5–1.0 | cm | Collider smaller than the skin | [E] |
| `female_mass_frac` | head 6.68, trunk 42.57, upper arm 2.55, forearm 1.38, hand 0.56, thigh 14.78, shank 4.81, foot 1.29 | % | | [S1] (M) |

### Visual/behavioural checklist (segments)
- Legs are heavy: a swinging leg carries about 3× the momentum of an arm at the same speed. A kicked or shot leg moves little; a shot hand flicks.
- The head is heavy for its size. When the neck goes limp, the head drops and lolls; it does not float.
- Lying bodies touch the floor with flesh, not with an invisible shell 2 cm above it.

---

## 2. Joint ranges of motion

### 2.1 Four limits per joint

| Limit | Meaning | Use in game |
|---|---|---|
| **Active ROM** | What the person can reach with their own muscles | Target clamp for the animation and the controller |
| **Passive ROM (alive)** | What an examiner can push to in a relaxed person; typically **5–15° beyond active** `[K] (H)` | Hard joint limit while alive; external forces can reach it |
| **Limp/dead ROM** | Relaxed or anaesthetised, with no muscle guarding: ligaments, capsule, bone contact and stretched passive muscle limit the joint. **About passive + 0–10°** `[K] (M)` | Hard joint limit when unconscious or dead |
| **Failure** | The ligament ruptures, the joint dislocates or bone fractures | Gore event: raise the damage, remove or relax the limit, add deformity (§2.7) |

Where textbooks disagree (for example AAOS gives cervical extension 45° while other sources give 60–75°), the tables give the range and the game value. AAOS values are conservative clinical norms. The game uses the mid-range of healthy young adults because the reference body is a healthy adult.

### 2.2 Spine and neck `[K] (M)`

Range for the whole region; left and right values are each side.

| Region | Motion | Active (typical) | AAOS norm | Passive alive | Limp/dead | Notes |
|---|---|---|---|---|---|---|
| Cervical total (occiput–C7) | Flexion | 50–60 | 45 | 60–70 | **70** (chin on sternum) | |
| | Extension | 60–75 | 45 | 75–85 | **85** | Head hanging back over an edge |
| | Lateral flexion | 40–45 | 45 | 45–50 | **50** | |
| | Rotation | 70–80 | 60 | 80–90 | **90** | ~50 % of it happens at C1–C2 |
| Upper cervical (occiput–C1–C2) | Flex / ext | 10–15 / 15–25 | | | | Nodding |
| | Rotation | 35–45 | | | | Atlanto-axial |
| Thoracic (T1–T12) | Flex / ext | 30–40 / 20–25 | | | | Limited by the rib cage |
| | Lateral / rotation | 25–30 / 30–35 | | | | **Most trunk rotation is thoracic** |
| Lumbar (L1–S1) | Flex / ext | 40–60 / 20–35 | | | | L4–L5 and L5–S1 carry the most |
| | Lateral / rotation | 20–30 / **5–15** | | | | ~2–3° rotation per level |
| Thoracolumbar total | Flex / ext / lateral / rotation | 80–90 / 25–40 / 35–45 / 40–45 | 80 / 25 / 35 / 45 | +10 | **105 / 50 / 50 / 55** | Limp: can fold over a rail or slump onto the thighs |

**Mapping to a rig with three trunk bodies plus neck and head** `[E]`. de Leva's boundaries fall at the xiphoid (~T9–T10) and the navel (~L3–L4). Rotation of T1–T9 is lumped into the upper spine joint.

| Rig joint | Anatomy it stands for | Flex / ext (alive) | Flex / ext (dead) | Lateral (alive / dead) | Rotation (alive / dead) |
|---|---|---|---|---|---|
| `spine_lower` (lower ↔ middle trunk, L3/L4) | L3–S1 | 30 / 15 | 38 / 20 | 12 / 15 | 4 / 6 |
| `spine_upper` (middle ↔ upper trunk, T10) | T10–L3 + lumped thoracic | 45 / 20 | 60 / 28 | 22 / 30 | 35 / 45 |
| `neck` (upper trunk ↔ neck, C7/T1) | C2–C7 | 40 / 50 | 50 / 60 | 32 / 40 | 35 / 45 |
| `head` (neck ↔ head) | Occiput–C2 | 15 / 20 | 20 / 25 | 8 / 10 | 40 / 45 |
| **Totals** | | spine 75 / 35; neck + head 55 / 70 | spine 98 / 48; neck + head 70 / 85 | | neck + head 75 / 90 |

### 2.3 Upper limb `[K] (M)`

| Joint | Motion | Active | AAOS | Passive alive | Limp/dead | Failure (gore) |
|---|---|---|---|---|---|---|
| Shoulder complex (glenohumeral + scapula lumped) | Flexion | 165–180 | 180 | 180 | 180 | — |
| | Extension | 50–60 | 60 | 60–70 | 70 | — |
| | Abduction | 170–180 | 180 | 180 | 180 | Abduction + external rotation past ~100–110° → **anterior dislocation** `[K] (M)` |
| | Horizontal adduction (arm across the chest) | 130–140 | 135 | 140 | 145 | — |
| | Internal rotation | 70–90 | 70 | 80–95 | 95 (hand behind the back) | Flexion + adduction + internal rotation under force → **posterior dislocation**, classically from seizures or electrocution `[K] (H)` |
| | External rotation | 60–90 | 90 | 90–100 | 100 | See abduction |
| Clavicle (sternoclavicular joint), if simulated | Elevation / depression | 30–45 / 5–10 | | | | Clavicle fracture: shoulder drops forward and down |
| | Protraction / retraction | 15–20 / 15–25 | | | | |
| Elbow | Flexion | 140–150 | 150 | 150–160 (soft-tissue contact) | 155 | — |
| | Hyperextension | 0–10 | 0 | 5–10 | 5–10 | > 20–30° → posterior dislocation or olecranon fracture `[K] (M)` |
| Forearm | Pronation / supination | 75–85 / 80–90 | 80 / 80 | +5–10 | 90 / 95 | Forced rotation past ~110–120° → fracture or dislocation `[E] (L)` |
| Wrist | Flexion / extension | 75–85 / 70–75 | 80 / 70 | 85–90 / 80–90 | 90 / 90 (weight on the back of the hand) | Fall on an outstretched hand → distal radius fracture (force threshold in `[R1-02]`) |
| | Radial / ulnar deviation | 15–20 / 30–35 | 20 / 30 | 25 / 40 | 25 / 45 | |
| Fingers | Knuckle (MCP) / middle joint (PIP) / fingertip joint (DIP) flexion | 90 / 100–110 / 80–90 | | | Limp rest: §2.6 | Hammer: phalanx fractures, angulated fingers |

### 2.4 Lower limb `[K] (M)`

| Joint | Motion | Active | AAOS | Passive alive | Limp/dead | Failure (gore) |
|---|---|---|---|---|---|---|
| Hip | Flexion, knee bent | 115–125 | 120 | 130–140 | 140 (thigh on abdomen) | Flexed + adducted + axial load → posterior dislocation (leg short, internally rotated, adducted) `[K] (H)` |
| | Flexion, knee straight (straight-leg raise) | 70–90 (hamstrings limit it) | | 80–100 | 100 | |
| | Extension | 10–20 | 30 | 20–30 | 30 | |
| | Abduction / adduction | 40–45 / 20–30 | 45 / 30 | 45–55 / 30–35 | 55 / 35 | |
| | Internal / external rotation | 30–45 / 40–50 | 45 / 45 | 40–50 / 50–60 | 50 / 70 | **Femoral-neck fracture: the limb lies short and externally rotated 45–90°** `[K] (H)` |
| Knee | Flexion | 135–145 (hip flexed), 120–130 (hip extended) | 135 | 150–160 | 155–160 (heel meets buttock) | — |
| | Hyperextension | 0–5 | 0 | 5–10 | 5–10 | > 15–30° → cruciate ligament and posterior capsule rupture, possible dislocation (vessel injury) `[K] (M)` |
| | Tibial rotation at 90° flexion | internal 20–30 / external 30–40 | | | | Valgus > 10–15° under load → medial ligament / ACL tear `[K] (M)` |
| Ankle + subtalar | Dorsiflexion | 10–15 (knee straight), 20–25 (knee bent) | 20 | 20–30 | 25–30 | Forced dorsiflexion under axial load → fracture |
| | Plantarflexion | 40–55 | 50 | 55–65 | 60–65 | — |
| | Inversion / eversion | 25–35 / 15–20 | 35 / 15 | +5 | 40 / 20 | Inversion > 35–45° with plantarflexion → lateral ligament tear; the "rolled ankle" of a stumble `[K] (M)` |
| Toes (MTP) | Extension / flexion | 70–90 / 30–40 | | | | |

### 2.5 Two-joint muscles, coupled limits and tenodesis

Several limits depend on the angle of a neighbouring joint. A ragdoll with independent limits looks wrong in exactly these poses `[K] (H)`:
- **Hamstrings.** Hip flexion is limited to 80–100° when the knee is straight, but reaches 130–140° when the knee is bent.
  - A limp body folded at the hips therefore **bends the knees**, or stops folding.
  - Implement it as a coupling torque: τ_hip_ext = k_h × max(0, θ_hip − (90° − 0.6 × θ_knee)), with k_h ≈ 30–60 Nm/rad `[E]`.
- **Rectus femoris.** Knee flexion is limited to ~120–130° when the hip is extended, which matters in a prone body with the heel moving toward the buttock.
- **Gastrocnemius.** Ankle dorsiflexion is ~10° less when the knee is straight.
- **Tenodesis of the hand.** In a limp hand the finger flexors act like tendons with no motor:
  - wrist extension curls the fingers;
  - wrist flexion opens them.
  - Rule `[E]`: finger curl (0–1) = 0.35 + 0.4 × (wrist extension / 70°) − 0.3 × (wrist flexion / 80°), clamped to 0–1.
  - This single rule gives every dead hand a believable shape.
- **Neck extension and the jaw.** With the head tipped back, the limp jaw falls open 10–30 mm `[R1-04 §12]`.

### 2.6 Flaccid resting angles (where a limp body settles) `[K] (M)` values, `[E]` probabilities

| Posture | Region | Typical resting value |
|---|---|---|
| **Supine** | Head | Rotated **20–60°** to one side (p ≈ 0.8) or midline (p ≈ 0.2). Neck 0–15° extension. Jaw open 10–30 mm |
| | Shoulders / elbows | Abducted 10–40° (or flung 60–90° after a backward fall); elbows 10–40° flexed |
| | Forearms / wrists / hands | Pronated 30–80° or neutral; wrists 0–30° flexed; fingers MCP 20–40°, PIP 30–60°, DIP 10–30°; thumb adducted |
| | Hips | 0–10° flexion, **30–60° external rotation (feet splay; 60–120° between the feet)**, 5–15° abduction |
| | Knees / ankles | Knees 0–15° flexed; **ankles 20–40° plantarflexed** (foot drop) |
| **Prone** | Head | **Rotated 60–90°, lying on the cheek** (p ≈ 0.85). Face straight down (forehead and nose) p ≈ 0.15. Neck 10–30° extension |
| | Arms | Along the sides, **palms up** (shoulder extended and internally rotated) after a forward crumple; or abducted 60–90° with elbows 60–90° flexed |
| | Hips / knees | 0°, knees 0–10° |
| | Feet | Plantarflexed **40–60°, backs of the feet flat on the floor**; less often toes tucked under (ankle 0–10° dorsiflexion) |
| **Side-lying** | Down side | Shoulder protracted; the lower arm is trapped under the body or thrust forward |
| | Up side | Hip 20–60° and knee 20–60° flexed; the top knee rests on the floor in front of the bottom leg |
| | Head | Lateral flexion toward the floor 10–30° |
| **Slumped sitting** (against a wall or seat) | Trunk | 30–60° total flexion, or sideways lean of 20–45° |
| | Head | 40–60° flexed (chin on chest) or dropped sideways onto the shoulder |
| | Arms | Palms up on the lap or on the floor beside the body |
| | Legs | Straight, or knees bent and falling outward ("frog": hips 30–60° externally rotated and abducted) |
| **Kneeling crumple** | Legs / trunk | Knees 150–160° (sitting on the heels), ankles 50–60° plantarflexed; trunk folded onto the thighs or rolled to one side. Unstable: rolls within 0.5–3 s in ~70 % of cases `[E] (L)` |

### 2.7 Structural failure limits (gore events) `[K] (M–L)`

| Joint | Failure criterion | Value | Result in game |
|---|---|---|---|
| Neck (occipital-condyle moment, adult male) | **Flexion**: pain / ligament damage | **~59 / ~190 Nm** (Mertz & Patrick) `[K] (M)` ✓ verified [K] (M–H): 59.4 / 189.8 Nm (44 / 140 ft·lb) | Past the ligament threshold: fracture-dislocation. Head angulates; limits widen 20–40° |
| | **Extension**: pain / ligament damage | **~47 / ~57 Nm** `[K] (M)` ✓ verified [K] (M–H): 47.5 / 56.7 Nm (35 / 42 ft·lb). The 190 / 57 Nm pair became the Hybrid III neck-moment limits | Extension is far weaker than flexion: backward whips (occipital falls, blows to the face) are the dangerous direction. Caveat: pain values come from volunteers, ligament values were scaled from cadaver tests, and all are quasi-static equivalent moments at the occipital condyles |
| Knee | Hyperextension or valgus moment to ligament failure | ~100–300 Nm (cadaver range) `[K] (L)` | Knee bends backward or sideways; limit removed on that axis |
| Elbow | Hyperextension moment to dislocation | ~50–100 Nm `[E] (L)` | Forearm displaced backward; elbow limit 0 → −40° |
| Shoulder | Anterior dislocation | Abduction ~90° + external rotation > ~100° with ~30–60 Nm `[E] (L)` | Arm fixed in slight abduction and external rotation; squared-off shoulder |
| Long bones | Mid-shaft fracture (from the hammer or a bullet, `[R1-02]`) | — | Needs a virtual joint at the fracture site (§8.2): passive only, ±30–60° free, heavy damping, crepitus audio |

### Simulation parameters (ROM)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `rom_alive_limit` | passive column, §2.2–2.4 | ° | Hard limits while alive | [K] (M) |
| `rom_dead_limit` | limp/dead column | ° | Switch at loss of consciousness (tone < 0.2) | [K] (M) |
| `rom_soft_zone` | last 5–15° before the hard stop | ° | Exponential passive torque (§3.3) | [E] |
| `rom_spine_rig` | table §2.2 | ° | Three trunk bodies + neck + head | [E] |
| `hamstring_coupling_k` | 30–60 | Nm/rad | §2.5 | [E] |
| `tenodesis_rule` | curl = 0.35 + 0.4·ext/70 − 0.3·flex/80 | — | Limp hand | [E] |
| `rest_head_rot_prone` | 60–90 (p 0.85) | ° | | [K] [E] |
| `rest_hip_er_supine` | 30–60 | ° | Feet splay | [K] (M) |
| `rest_ankle_pf_supine` / `_prone` | 20–40 / 40–60 | ° | | [K] (M) |
| `neck_flex_failure` / `neck_ext_failure` | 190 / 57 | Nm | Ligament-damage thresholds ✓ verified [K] (Mertz & Patrick 1971) | [K] (M–H) |

### Visual/behavioural checklist (ROM)
- A living person never uses the ends of their range at rest. A limp or dead body **lives at the ends of its range**: feet flat and pointed, wrists fully bent, head turned 90° on the cheek, arms twisted palm-up behind the hips.
- A limp body folded at the hips bends its knees. Straight-legged folding past 100° is anatomically impossible.
- Broken joints show as angles that no intact joint allows: a knee bent sideways, a forearm displaced behind the elbow, a head tilted past the shoulder.

---

## 3. Joint mechanics: torque capacity, passive stiffness, damping

### 3.1 Maximum voluntary isometric torque (young adult male) `[K] (M)`

These values are the **torque caps** for the PD drive (§7.1). Strength modifiers (blood loss, pain inhibition, hemiparesis, fatigue) scale the caps, not the gains.

| Joint | Motion: torque (Nm) |
|---|---|
| Neck | Flexion 15–30; **extension 30–50**; lateral 20–35; rotation 10–20 |
| Trunk (lumbar) | Extension 200–300; flexion 150–250; lateral 120–200; rotation 60–120 |
| Shoulder | Flexion 60–100; extension 80–120; abduction 60–90; internal rotation 50–80; external rotation 30–50 |
| Elbow | Flexion 60–90; extension 40–60 |
| Wrist | Flexion 10–20; extension 8–15. **Grip force 400–550 N** |
| Hip | Extension 200–300; flexion 150–250; abduction and adduction 100–150 |
| Knee | Extension 200–300; flexion 100–150 |
| Ankle | Plantarflexion 150–250; dorsiflexion 40–60 |

Maximum voluntary joint speeds `[K] (M)`: 10–25 rad/s for most joints (up to ~100 rad/s for internal rotation of the shoulder while throwing). Clamp the drive's target velocity at 15–20 rad/s.

### 3.2 Demand vs capacity: why weakened people sink `[E]`

The knee-extensor torque needed to hold the body up is roughly body weight × horizontal distance between the knee and the line of gravity, shared between two legs or carried by one:

| Stance | Knee flexion | Demand per knee |
|---|---|---|
| Two legs | 20° | 25–40 Nm |
| Two legs | 45° | 60–100 Nm |
| **One leg** | 20° | **50–70 Nm** |
| **One leg** | 45° | **120–160 Nm** |

- A healthy knee (200–300 Nm) holds all of these.
- With pain inhibition (capacity −30–70 % `[K] (M)`), a thigh wound, or blood-loss weakness (§5.5), capacity drops below the demand of a bent single-leg stance first. That is why an injured person **stands straight-kneed on the good leg, then sinks as soon as the knee bends**.
- Buckling runs away: more flexion means more demand.
- Rule: if demand > strength × cap for more than 100 ms, the joint yields at the rate set by the torque deficit. A knee yielding this way reaches 90° in 0.3–0.6 s.

### 3.3 Passive elastic moment (relaxed muscle, ligament, capsule) `[K] (L–M)` values, `[E]` model

- **Model**: a double exponential plus viscous damping, following the Riener & Edrich 1999 form:

  τ_pass(θ, θ̇) = −k_mid·(θ − θ_rest) − A_hi·(e^((θ − θ_hi)/s) − 1)·[θ > θ_hi] + A_lo·(e^((θ_lo − θ)/s) − 1)·[θ < θ_lo] − B·θ̇

  - θ_hi and θ_lo are where the soft zone starts, 5–15° before the hard limit.
  - s is the e-fold angle: the torque grows by a factor e every s degrees.
  - A is the torque scale, chosen so that τ at the hard limit equals the "end torque" column below.

| Joint | k_mid (Nm/rad) | s (°) | End torque at the limit (Nm) | B (Nm·s/rad) |
|---|---|---|---|---|
| Head (occiput–C2) | 0.5–1 | 4–6 | 3–8 | 0.05–0.15 |
| Neck (C2–C7) | 1–3 | 5–8 | 5–15 | 0.1–0.3 |
| Spine (each joint) | 20–60 (discs and ligaments) | 5–10 | 50–100 (flexion–relaxation: at full flexion passive tissue carries ~100 Nm) | 2–5 |
| Shoulder | 1–3 | 8–12 | 10–25 | 0.2–0.5 |
| Elbow | 0.5–1.5 | 5–8 | 5–10 | 0.05–0.2 |
| Wrist | 0.1–0.3 | 5–10 | 1–3 | 0.01–0.05 |
| Hip | 5–15 | 8–12 | 20–50 | 0.5–2 |
| Knee | 2–5 | 6–10 | 15–30 | 0.2–0.5 |
| Ankle | 3–10 | 5–10 | 15–30 | 0.2–0.5 |

- **These terms are always on**, alive or dead. The active drive adds on top.
- The soft zone gives the "end feel" of real joints: **a dead limb decelerates into its limit instead of clanking off it.**
- Hard limits alone (§8.5) make the joint bounce elastically. That is one of the main reasons ragdolls look like rubber toys.

### 3.4 Pendulum behaviour: the validation numbers `[E]` (from §1.8), `[K]` for the clinical tests

| Test | Physics | Expected |
|---|---|---|
| **Limp arm dropped from horizontal** (shoulder flexed 90°, body upright) | Compound pendulum. Equivalent length I/(m·d) = 0.452 / (3.70 × 0.30) = 0.41 m. Small-amplitude period 2π√(0.41 / 9.81) = 1.28 s. Quarter swing from 90°: 0.32 s × 1.18 (large-amplitude correction, 2K(sin 45°)/π = 1.180) | **Passes the vertical, at its highest speed, after 0.36–0.40 s** ✓ verified (0.378 s). Corrected wording: was "hangs vertical". Swings on 2–4 times with period ~1.3 s; still after 2–4 s |
| **Seated leg pendulum** (Wartenberg test: shank released from full knee extension) | Equivalent length 0.405 / (4.28 × 0.263) = 0.36 m; period 1.20 s from gravity alone, **1.12 s once the §3.3 knee k_mid is added** (fact-check); horizontal to vertical 0.35 s | Period **1.0–1.3 s** (corrected: was implied 1.1–1.3 s). Normal: **4–6 oscillations, still after 4–6 s** `[K] (M)`. Flaccid (hypotonic): more and larger oscillations. Spastic: 1–3 oscillations, first swing cut short by a "catch" `[K] (M)` |
| **Head drop, seated, neck tone lost** | Inverted pendulum ω = √(6.3 / 0.11) = 7.6 s⁻¹. From 5° to 60°: t = acosh(12) / 7.6 = 0.42 s ✓ verified | **Chin to chest in 0.3–0.6 s** |
| **Trunk slump, seated** | HAT about the hips (both hips): ω = √(149 / 7.4) ≈ 4.5 s⁻¹ (corrected: was √(159 / 6.6) ≈ 4.9, see §1.8). From 5° to 60°: acosh(12) / 4.5 ≈ 0.71 s (was 0.65 s) | **Folds onto the thighs in 0.7–1.0 s**, or tips sideways in 0.8–1.2 s (unchanged) |
| **Hand-drop test** (unconscious) | Arm lifted over the face and released | Falls onto the face. A feigning or conscious person avoids the face `[K] (H)`. A dead or unconscious ragdoll must hit its own face |

Damping check `[E]`: for the knee pendulum, B = 0.3 Nm·s/rad gives ζ = B / (2√((k_g + k_mid) × I)) = 0.3 / (2√(13 × 0.41)) ≈ 0.065. Using B ≥ 1 kills the swing in one cycle and **looks like the limb is moving through syrup**.
- Fact-check `[E]`: corrected: was "that matches ~5 visible oscillations". ζ = 0.065 gives an amplitude ratio of e^(−2πζ) ≈ 0.66 per cycle, which is **~7 cycles** before the swing drops below 5°.
- For the 4–6 visible oscillations of a normal Wartenberg test, use ζ ≈ 0.075–0.11, i.e. **B ≈ 0.35–0.5 Nm·s/rad**, still inside the §3.3 knee range. The "B ≥ 1 looks like syrup" conclusion stands.

### Simulation parameters (joint mechanics)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `tau_max[joint][dir]` | table §3.1 | Nm | Drive caps | [K] (M) |
| `strength_scale` | 0–1 | — | Blood loss (§5.5), pain (0.3–0.7), hemiparesis (0–0.3 on the affected side), fatigue | [K] [E] |
| `joint_speed_max` | 15–20 | rad/s | Drive target-velocity clamp | [K] (M) |
| `passive_k_mid`, `passive_s`, `passive_end_tau`, `passive_B` | table §3.3 | various | Always on | [K] (L–M) [E] |
| `soft_zone_width` | 5–15 | ° | Before the hard limit | [E] |
| `arm_drop_time_90` | 0.36–0.40 | s | Validation: time for the limp arm to **pass** the vertical from horizontal. ✓ verified (0.378 s) | [E] |
| `leg_pendulum_period` | 1.0–1.3 (corrected: was 1.1–1.3) | s | Validation. The passive knee stiffness shortens the gravity-only 1.20 s | [E] |
| `leg_pendulum_damping_B` | 0.35–0.5 | Nm·s/rad | Gives the normal 4–6 visible oscillations (fact-check addition) | [E] |
| `head_drop_time` | 0.3–0.6 | s | Validation ✓ verified (0.42 s) | [E] |
| `yield_rule` | demand > strength × cap for > 100 ms → yield | — | §3.2 | [E] |

### Visual/behavioural checklist (joint mechanics)
- A dead arm hanging off a bed or a ledge swings a few times and stops. It does not freeze mid-swing and does not keep swinging.
- Limbs hitting their limit slow in the last few degrees, with no clank or rebound.
- An injured person with one bad leg keeps the good knee locked straight. When it bends, they go down.

---

## 4. Muscle tone states → drive parameters

### 4.1 Gain design `[E]` (standard control theory; the same idea underlies Euphoria's stiffness/damping pair and Jolt's frequency/damping motor springs `[K] (M)`)

- Set gains **by natural frequency ω (rad/s) and damping ratio ζ**, not by raw numbers:

  **kp = I_eff · ω²**, **kd = 2 · ζ · I_eff · ω**

  - I_eff comes from §1.8.
  - One ω then gives a consistent "muscle feel" from the neck to the wrist.
  - It also keeps small bodies (hand, foot) stable automatically.
- **Load joints need a gravity term.**
  - The stance ankles, knees and hips, the spine and the neck hold up mass above them, so child-subtree inertia underestimates what they need.
  - Use **kp = max(I_eff·ω², γ·k_g)** with γ = 1.2–2.0, or better, add gravity compensation (§7.3) and keep kp low.
  - **Corrected: was "human quiet-standing ankle stiffness is ~0.9–1.3 × m·g·h (Loram & Lakie; Casadio et al.)".** Those papers found the opposite of what the old line implied. The *intrinsic* ankle stiffness in quiet standing is **below** the gravitational toppling stiffness m·g·h: ~91 ± 23 % (Loram & Lakie, *J Physiol* 2002) and ~64 ± 8 % (Casadio, Morasso & Sanguineti, *Gait Posture* 2005) `[K] (M–H)`.
  - Both conclude that passive stiffness cannot hold a person up. The nervous system adds active, intermittent corrections on top.
  - For the game, γ > 1 is a stand-in for that active control. Remove it together with tone, and the stance joints must fall, as a real body does.
- **Tone scaling.** Physiology outputs `tone` from 0 to 1 per joint group:
  - kp_final = kp × tone
  - kd_final = kd × √tone (keeps ζ roughly constant)
  - τ_cap_final = τ_max × strength
- **Stability.** With explicit torques, keep ω·Δt ≤ 0.5: ω ≤ 30 rad/s at 60 Hz, ≤ 60 rad/s at 120 Hz. Everything in §4.2 except rigor stays below this.
  - ✓ verified (fact-check `[K]` (H)): kp = I·ω² and kd = 2ζ·I·ω are the standard second-order forms. For a semi-implicit (symplectic) Euler step the hard stability limit of an undamped spring is ω·Δt < 2, so ≤ 0.5 is a conservative rule that also keeps the motion accurate. Caveat: I_eff must be the inertia the torque actually drives. For a light child on a heavy parent (hand on forearm) that is the child's own inertia about the joint, which §1.8 uses.

### 4.2 Tone state table `[E]` (anchors: Euphoria stiffness scale 6–16 `[S12]` names, semantics `[K] (M)`; tone-loss timing `[S7]`)

| State | When | ω (rad/s) | ζ | Gravity compensation | Torque cap × max | Onset ramp |
|---|---|---|---|---|---|---|
| **Braced / fighting** | Alert, anticipating a blow | 14–16 | 1.0 | 1.0 | 1.0 | 100–200 ms |
| **Normal standing (relaxed)** | Default alive | Legs and trunk 10–12; neck 10; arms 6–8 | 0.8–1.0 | 1.0 | 1.0 | — |
| **Hit compliance** (local) | 0.1–0.3 s after a hit, on the hit chain ±2 joints | ×0.45–0.65 of current ω (kp × 0.2–0.4) | 0.7 | 0.7 | 1.0 | Instant; restore over 0.2–0.5 s |
| **Reduced tone / dazed** | Rocked, concussion, class III blood loss, pain shock | 5–8 | 0.6–0.8 | 0.5–0.8 | 0.4–0.7 | 0.3–1 s |
| **Very weak** | Class IV blood loss, pre-syncope | 2–4 | 0.8–1.0 | 0.2–0.4 | 0.1–0.3 | 1–3 s |
| **Flaccid** | Unconscious; brainstem death; spinal shock below the lesion; dead before rigor | **0 (active off)**; passive terms only (§3.3) | — | 0 | 0 | **≤ 100 ms** (off switch, knockout); 0.5–2 s (hypoperfusion) |
| **Tonic** | Fencing response, tonic seizure phase | 12–16 toward the posture target | 1.0–1.5 | 0.5 | 0.7–0.9 | 50–200 ms |
| **Posturing** (decorticate / decerebrate) | Coma with midbrain or upper-pons, or hemispheric, damage | 8–12 toward the `[R2-01 §18.2]` targets | **1.2–2.0 (slow, lead-pipe)** | 0.5 | 0.5–0.8 | 0.5–2 s |
| **Clonic jerks** | Seizure clonic phase; syncope myoclonus | Pulses: 12–16 on the pulse (40–120 ms), 3–5 between | 0.7 | 0 | 0.5–0.9 | Pulse rate 1–4 Hz, slowing |
| **Spastic** (days later; hemiplegia or cord injury after spinal shock) | Out of acute game time | Base 3–6; **stretch "catch" ×2–4** when joint speed > 60–120°/s for 100–300 ms | 0.7 | 0.3 | 0.5 | — |
| **Rigor mortis** (hours) | `[R1-04 §12.6]` timing | Implement as **limits clamped around the current pose** + break torque (§4.5), not as gains | — | 0 | — | Hours |

### 4.3 Per-joint gains for the 75 kg body `[E]` (from §1.8 and §4.1)

| Joint | I_eff (kg·m²) | k_g (Nm/rad) | kp at ω = 6 | kp at ω = 12 | kp at ω = 16 | kd at ω = 12, ζ = 1 | Stance kp (γ = 1.5, if no gravity compensation) |
|---|---|---|---|---|---|---|---|
| Head (occiput–C2) | 0.027 | 1.5 | 1.0 | 3.9 | 6.9 | 0.65 | — |
| Neck | 0.11 | 6.3 | 4.0 | 15.8 | 28 | 2.6 | 9.5 minimum |
| Spine upper (T10) | 1.4 | 35 | 50 | 202 | 358 | 34 | 53 |
| Spine lower (L3/L4) | 4.3 | 101 | 155 | 619 | 1101 | 103 | 152 |
| Hip | 2.67 (swing) | 47 swing / 75 stance (corrected: was 79) | 96 | 385 | 683 | 64 | 112 per hip (was 120) + swing term |
| Knee | 0.41 (swing) | 11 swing / 179 stance | 15 | 59 | 105 | 9.8 | **270 per knee** |
| Ankle | 0.009 (swing) | 0.6 swing / 318 stance | 0.3 | 1.3 | 2.3 | 0.22 | **480 per ankle** |
| Shoulder | 0.45 | 10.9 | 16 | 65 | 115 | 10.8 | — |
| Elbow | 0.078 | 3.0 | 2.8 | 11.2 | 20 | 1.9 | — |
| Wrist | 0.0035 | 0.31 | 0.13 | 0.50 | 0.90 | 0.084 | — |

**Comparison with research gains** `[K] (M)`:
- DeepMimic's humanoid uses chest 1000 / 100, hip and knee 500 / 50, shoulder 400 / 40 and elbow 300 / 30 (kp / kd, i.e. kd/kp = 0.1 s).
- For the arms that is 3–30× stiffer than the ω = 12 values above, i.e. ω ≈ 30–60 rad/s. It is tuned for tracking motion capture under reinforcement learning, not for looking hit.
- **Use ω 10–12 for "alive"**. Under impacts, stiffer gains look robotic: limbs shrug off hits like a statue.

### 4.4 Tone transitions: speed and order

| Transition | Duration | Order of loss or gain | Tag |
|---|---|---|---|
| **CNS off switch** (brainstem, high cord, deep knockout) | 50–100 ms linear to 0. Fact-check: ⚠ the ≤ 100 ms figure of [S7] was not re-verified. Neural drive stops at once, but muscle force decays with the muscle's relaxation time: half-relaxation ~50–100 ms, ~90 % gone by ~150–250 ms `[K] (M)`. **An exponential decay with τ ≈ 60–100 ms is the more physiological curve**; on screen it looks almost the same | **All groups at once**. Grip opens 0.1–0.5 s | [S7] [R1-04 §2.3] |
| **Knockout with fencing** | Legs and trunk to 0 in ≤ 100 ms; arms go tonic at the same moment for 2–10 s (the duration is `[E]`; [S14] gives the 66 % rate, not a duration range), then 0 over 0.5–1 s | Arms tonic, the rest limp | [S14] [R1-04 §3.6] |
| **Syncope / hypoperfusion** | 0.5–2 s, graded | **Legs → trunk → neck → arms.** Fact-check: this order is `[E]` (L), not a sourced sequence. §5.3 itself says the head *or* the knees may go first, so pick the first group at random between neck (p ≈ 0.4) and legs (p ≈ 0.6) `[E]`. Optional brief tonic stiffening (1–5 s) in ~10–20 % `[K] (L)` | [S5] [E] |
| **Cardiac arrest (sudden)** | Loss of consciousness 5–15 s after flow stops; final tone loss fast (0.2–0.5 s): a "crash", not a crumple | Whole body; anoxic jerks possible in the first 5–20 s | [S11] [R2-02 §2.5] |
| **Spinal cord transection** | ≤ 100 ms below the level | Flaccid below; normal above | [S19] [K] (H) |
| **Death** | Flaccid from arrest to rigor onset (~3 h, range 0.5–7 h) | — | [R1-04 §12.6] |
| **Recovery from knockout** (5–60 s) | Tone returns over 1–5 s | **Neck and arms first** (head lifts, hands push); legs last and ataxic: knees wobble at 1.5–3 Hz for 10–60 s | [K] (M) [E] |

### 4.5 Special tone maps

**Spinal cord level (acute; spinal shock = flaccid below)** `[K] (H)` for the patterns, `[E]` for the drive values:

| Level | What still works | Resting and falling picture |
|---|---|---|
| C1–C3 | Face, eyes, some neck rotation (accessory nerve). **No breathing** | Cut strings but awake; no arm protection `[R1-04 §2.2]` |
| C4 | Shrug; partial diaphragm | As above; paradoxical abdominal breathing |
| **C5** | Deltoid, biceps | **"Arms up" posture: shoulders abducted 45–90°, elbows flexed 90–120°, forearms supinated, wrists and hands limp** (unopposed deltoid and biceps). Drive: shoulder abduction and elbow flexion ω 6–10; triceps, wrist and hand flaccid |
| C6 | + wrist extensors | As C5 plus wrists extended 20–40°; tenodesis curl (§2.5) |
| C7–T1 | + triceps, then the hand | Arms usable, grip weak (C8–T1) |
| T1–T6 | Arms normal; trunk control poor | Falls sideways even when sitting; arms catch |
| T6–T12 | Better trunk | Legs flaccid; sits down hard (archetype E) |
| L1–L2 and below | Hip flexion partly kept (L1–L2) | Legs fold; sits down |
| Hemisection (Brown-Séquard) | Opposite leg strong | Leg on the side of the cut is flaccid; falls toward it |

**Hemiplegia** (acute cerebral lesion) `[R2-01 §2]`: the opposite side is flaccid at first, with the arm tone lower than the leg tone.
- Arm tone 0–0.2, leg tone 0.2–0.4, face drooping.
- The body falls toward the paralysed side.
- Spasticity follows only after days.

**Rigor mortis implementation** `[E]` (timing from `[R1-04 §12.6]`):
- For each group, `s(t)` runs from 0 to 1 with the Nysten order offsets.
- Clamp each joint's limits to **current pose ± lerp(full range, 2°, s)**.
- Raise passive B to lerp(passive, 50–200 Nm·s/rad, s).
- **Break torque** τ_break = s × τ_break_max (table below). When an external torque exceeds it, the rigor in that joint breaks:
  - s → 0.2–0.3 if post-mortem time < 8 h (it partly re-forms);
  - s → 0 otherwise.

| Group | τ_break_max (Nm) `[E] (L)` |
|---|---|
| Jaw | 5–15 |
| Fingers (each) | 0.5–2 |
| Wrist | 3–8 |
| Elbow | 15–40 |
| Shoulder | 20–50 |
| Neck | 15–40 |
| Trunk joints | 50–150 |
| Hip | 40–120 |
| Knee | 30–100 |
| Ankle | 15–40 |

Lead-pipe (decerebrate) rigidity resistance for comparison: ~5–20 Nm at the elbow `[E] (L)`.

### Simulation parameters (tone)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `gain_rule` | kp = I_eff·ω²·tone; kd = 2ζ·I_eff·ω·√tone | — | Per joint | [E] |
| `omega_braced` / `omega_normal` / `omega_dazed` / `omega_weak` | 14–16 / 10–12 (arms 6–8) / 5–8 / 2–4 | rad/s | | [E] [S12] (M) |
| `zeta_default` / `zeta_posturing` | 0.8–1.0 / 1.2–2.0 | — | | [E] |
| `hit_compliance` | kp × 0.2–0.4 for 0.1–0.3 s, restore over 0.2–0.5 s | — | Hit chain ±2 joints | [S13] (method) [E] (values) |
| `tone_loss_offswitch` | 50–100 (or exponential, τ 60–100) | ms | All groups at once. ⚠ [S7] figure not re-verified; muscle relaxation physiology gives ~90 % force loss by 150–250 ms | [S7] [K] (M) |
| `tone_loss_hypoperfusion` | 0.5–2 | s | Legs → trunk → neck → arms, or neck first (p ≈ 0.4). Order is `[E]` (L) | [E] |
| `fencing_arm_tone` | ω 12–16 for 2–10 s | — | p 0.66 of knockouts ✓ verified [K]; duration `[E]` | [S14] [E] |
| `stance_gamma` | 1.2–2.0 × k_g | — | Without gravity compensation | [K] (M) |
| `omega_dt_max` | 0.5 | — | Explicit-torque stability | [E] |
| `rigor_limit_band` | lerp(full, 2°, s) | ° | Around the current pose | [E] |
| `rigor_break_tau` | table §4.5 | Nm | | [E] (L) |
| `c5_posture` | shoulders abducted 45–90°, elbows 90–120°, forearms supinated | ° | Cord injury at C5 | [K] (H) pattern |

### Visual/behavioural checklist (tone)
- Alive: limbs yield to a hit and come back within about half a second. Never statue-stiff, never noodle-soft.
- Dazed: knees soften, the head nods, the arms hang. The body looks heavy on its legs.
- Unconscious: everything goes at once for off-switch causes, or legs first for fainting and bleeding. Nothing is held in the air any more.
- Fencing: one arm locked up and out, the other bent, while the rest of the body is limp.
- Cord injury at C5: the person lies with the arms bent up beside the head and cannot straighten them.

---

## 5. How different collapses unfold

### 5.1 Physics bounds `[E]`

| Quantity | Formula | Values |
|---|---|---|
| Free-fall time | t = √(2h/g) | h 0.45 m: 0.30 s · 0.84 m (standing CM to lying CM): **0.41 s** · 0.90 m: 0.43 s |
| Free-fall impact speed | v = √(2gh) | 0.45 m: 3.0 m/s · 0.84 m: 4.1 m/s · 0.90 m: 4.2 m/s · 1.60 m: 5.6 m/s |
| Rigid topple about the ankles | ω₀ = √(m·g·h / I) = 3.0 s⁻¹ (body); 2.9 s⁻¹ (uniform rod, `[R2-02 §5.2]`) | Ground time 1.0 s (start 10° lean), 1.2–1.3 s (5°), 1.5–1.6 s (2°). Head impact **6.2–6.7 m/s** (§6.2). ✓ verified (fact-check: the cosh phase plus the energy phase give ~0.95 / 1.2 / 1.5 s; round-two document 02 re-derived 1.00 / 1.25 / 1.57 s for the rod). Upper-bound case: real "timber" falls rarely keep the knees fully locked and run 10–30 % faster, with head speeds nearer 5–6 m/s |
| Rigid fall from kneeling (trunk pivoting at the knees, L ≈ 0.95 m) | ω_end = √(3g/L) = 5.6 rad/s; head at ~0.85 m | Head **≈ 4.7 m/s**; 3–4.5 m/s if the hips fold |
| Energy to dissipate at collapse | m·g·Δh_CM = 75 × 9.81 × 0.84 | **≈ 620 J** in 1–2 s (use for impact-sound loudness) |

**Feet during a rigid topple** `[E]`. For a rigid rod pivoting on the floor, the friction needed at the feet peaks at ~0.37 × the normal force, at ~35° of tilt:
- F/N = 3·sinθ·(3cosθ − 2) / (1 − 3cosθ)²
- Past ~48° the required friction reverses.
- The normal force reaches zero at ~70°.
- ✓ verified (fact-check `[K]` (H), classic falling-rod result): N = m·g·(3cosθ − 1)²/4 and F = ¾·m·g·sinθ·(3cosθ − 2). F/N = 0.371 at 35°; the sign change is at cosθ = ⅔ (48.2°); N = 0 at cosθ = ⅓ (70.5°).

So with shoe friction ≥ 0.4, **the feet stay planted until ~50°, then slide or lift in the direction of the fall**, and the body lands flatter than a hinged pole would. Do not pin the feet.

### 5.2 CNS off switch (brainstem hit, high cord, "cut strings"): archetype A of `[R2-02 §5.1]`

Anchors:
- The standing fall after a tone-abolishing hit takes **⅔ s to ≥ 1 s** `[S2]`. Fact-check: ⚠ source not re-verified (no web access in either session; round-two document 02 marks it the same way). ✓ physically consistent `[E]`: free fall of the CM (0.41 s) is the floor, and knee folding plus toppling stretch it to 0.6–1.2 s.
- Tone is lost in ≤ 100 ms `[S7]` (⚠ see §4.4: force decays over ~150–250 ms).
- 0.6–1.2 s from hit to ground `[R1-04 §2.3]`.

Phase detail `[E]`, from a stationary relaxed stance (knees 0–5° flexed, CM ~2–4° ahead of the ankles `[K] (M)`):

| t (s) | What happens | Joint angles (typical) | CM height (m) |
|---|---|---|---|
| 0 | Hit | Knees 0–5°, hips 0–5° | 0.96 |
| 0–0.10 | Tone ramps to 0. **Almost nothing visible (≤ 1–2 cm sag).** Eyelids stay put; the jaw starts to drop | — | 0.95 |
| 0.10–0.25 | Buckling starts slowly: knees go forward, hips flex, ankles dorsiflex. The head lags (neck flexes 10–20°, or extends if leaning back). The grip opens | Knees 20–50°, hips 10–30°, ankles 10–20° dorsiflexion | 0.85–0.90 |
| 0.25–0.45 | Near-vertical rapid drop. The **arms lag and seem to float up** relative to the shoulders; elbows flex passively. The knees often splay (hip external rotation 10–30°) | Knees 80–130°, hips 50–90°, trunk tilt 10–30° along the lean | 0.50–0.60 |
| **0.35–0.55** | **First contact**: knees (lean forward or neutral) at 2–3 m/s, or buttocks onto the heels or floor (lean back) at 2.5–3.5 m/s. ✓ plausible (fact-check `[E]`): the CM falls ~0.45–0.5 m by knee contact, which takes 0.30–0.32 s in free fall and 2.9–3.1 m/s; the slow start from near-straight legs adds 0.05–0.2 s. If tone decays exponentially (§4.4), use the later half of the window | — | ~0.45 |
| 0.5–1.2 | The trunk topples along the residual lean or velocity; the trunk goes through 60–90° in 0.3–0.6 s. **Head impact at 0.7–1.2 s, 3–5 m/s.** The arms land 50–150 ms after the trunk and slap down | — | 0.12–0.20 |
| 1.0–2.0 | Head rebounds 1–5 cm; the legs slide out or stay folded under; limbs flop to their limits | — | 0.10–0.15 |
| 2–10 | Still. Agonal breathing only if the medulla was spared; possible small spinal twitches (p ≈ 0.2) `[R1-04 §2.6]` | — | — |

Final poses `[E] (L)`:
- Folded or kneeling slump that rolls to one side: 40 %.
- Prone: 25 %.
- Supine: 20 %.
- Legs folded under the body, trunk twisted: 15 %.

### 5.3 Syncope (faint): vasovagal or orthostatic

Anchors (Lempert video data, 42 complete syncopes) `[S5]`:
- Loss of consciousness **12.1 ± 4.4 s** ✓ verified [K] (H).
- Myoclonic jerks **90 %** ✓ verified [K] (H).
- Eyes **open**, with early upward deviation (13/14) `[S6]` ✓ consistent (round-two document 02 gives 7 tonic upward deviation + 6 downbeat nystagmus followed by upward deviation + 1 primary position; counts ⚠ not re-verified).
- Collapse is slower than in cardiac arrest ("crumple" vs "crash") `[S11]`.
- Fact-check context `[K]`: these were faints *induced* in 59 healthy young volunteers (hyperventilation, orthostasis, Valsalva), 56 episodes, 42 complete. Spontaneous faints in the field look the same but vary more in duration.
- **Myth guard (eyes)**: the upward deviation is **transient** (seconds) and belongs to the moment consciousness is lost. It is **not** the resting eye position of the dead; the eyes of a dead body rest near straight ahead or slightly divergent, lids open or half-open (`[R2-02 §5.6]`, `[R1-04]`). Do not "roll the eyes back" at death.

| Phase | Duration | Kinematics `[K] (M)` / `[E]` |
|---|---|---|
| Prodrome (warning) | 5–60 s (can be absent) | Pale, sweating, yawning. Postural sway grows 2–3×, feet widen, the hand looks for a support, attempts to sit down |
| Grey-out | Last 3–7 s | Vision fades, hearing muffled, staring, slowed replies |
| Tone loss | **0.5–2 s, graded** | The head droops first or the knees soften first. **Legs buckle over 0.5–1.5 s**; the body folds at hips and knees and sags down and slightly back or sideways. Against a wall it slides down. Brief tonic extension (1–5 s) possible |
| Ground contact | **1–2.5 s after the first visible buckle** | Buttocks or hips first at 1.5–2.5 m/s. **Head 2–4 m/s** (lower than the off switch, because the descent is partly controlled by residual tone). Stiff backward falls do occur and give an occipital impact |
| On the ground | 5–20 s | **Jerks in 90 %**: multifocal, arrhythmic, low amplitude, proximal and distal, often in clusters of 1–10 over 3–15 s. Eyes open and turned up. Head turns, lip-smacking and righting movements in 79 % `[S5]` |
| Recovery (true faint only) | Within ~12 s of lying flat | Eyes refocus; oriented within < 30 s. Pale and clammy. Sits up too soon and may faint again (p 0.1–0.2 `[E] (L)`) |

- **If propped upright** (slumped in a chair, pinned against a wall), cerebral flow does not recover. Loss of consciousness and jerking last longer (≥ 20–30 s) `[K] (M)`.
- **Bleeding out or a cardiac wound**: the same picture at the end of the consciousness window, with **no recovery** `[R2-02 §5.6]`.

### 5.4 Knockout: limp or stiff

Anchors:
- Tone lost immediately (≤ 100 ms) `[S7]`.
- Fencing response in **~66 %** of analysed knockout videos `[S14]` `[R1-04 §3.6]` ✓ verified [K] (M–H) (Hosseini & Lifshitz report it in about two-thirds of the knockouts they reviewed). The duration of **2–10 s** is `[E]`: the source and `[R1-04]` only say it lasts "several seconds" while the person is unconscious (round-two document 01 also tags the duration `[E]`).
- "No protective action – floppy" is an agreed video sign of concussion `[S8]`.

| Variant | Probability `[E] (L)` | Legs | Arms | Fall | Head impact |
|---|---|---|---|---|---|
| **Limp crumple** | 0.30 | Flaccid | Flaccid | Archetype A (§5.2); a hook punch adds a ¼–½ turn following the head rotation `[R2-02 §5.5]` | 3–5 m/s |
| **Crumple with fencing arms** | 0.50 | Flaccid | Tonic: one arm raised forward and up with the elbow nearly straight, the other flexed `[R2-01 §18.2]` | Crumple; the raised arm stays up after landing for 2–10 s, then drops | 3–5 m/s |
| **Rigid plank** | 0.20 | Tonic extension, **knees locked** | Tonic or fencing | Topples about the ankles in 1.0–1.6 s | **5–7 m/s**; the hardest head impact of all |

- Locked knees favour the plank. If knee flexion is < 3° at the moment of tone loss (knees locked or hyperextended), raise the plank probability to 0.4–0.6 `[E] (L)`. A locked knee in slight hyperextension is held by the posterior capsule, not by muscle, so it does not buckle.
- **"Rocked" or rubber legs** (no loss of consciousness) `[K] (M)` / `[E]` (anchored on the motor-incoordination video sign `[S8]`):
  - knee tone oscillates as tone = 0.35–0.6 ± 0.2–0.3 × sin(2π·f·t), f = 1.5–3 Hz, for 1–5 s;
  - 2–6 stumbling steps with a wide base;
  - reaches for support;
  - falls with p 0.4–0.7, usually to the knees or hands, with arms working.

### 5.5 Sag from blood loss (exhaustion): archetypes C → G of `[R2-02 §5.1]`

Strength and tone versus blood loss `[E]` (classes from `[R1-03 §3.1]`):

| Loss of blood volume | `strength_scale` | Tone ω | Behaviour |
|---|---|---|---|
| < 15 % | 1.0 | Normal | — |
| 15–30 % | 0.8 | 10 | Anxious, restless; stands |
| 30–40 % (class III) | 0.4–0.6 | 5–8 | Legs tremble; leans; **sits down deliberately** |
| > 40 % (class IV) | 0.1–0.3 | 2–4 | Slumps; loses consciousness |
| At loss of consciousness | 0 | 0 | Hypoperfusion collapse (graded, §5.3 without recovery) |

Typical sequence (physical) `[K] (M)` / `[E]`:
1. **Lean.** One hand, then the shoulder, against a wall or object. Base widened. Sway 2–3× normal.
2. **Slide down the wall** with the back or shoulder in contact:
   - vertical speed 0.1–0.4 m/s, 1–3 s;
   - knees flex progressively to 60–100°, hips to 70–90°.
   - Visual hook: a back wound leaves a **vertical smear 0.5–1.0 m long** on the wall.
3. **Seated.** Over 1–5 s the heels slide forward and the knees extend to 10–30°. The trunk flexes or leans sideways along the wall at 20–60° over 5–30 s.
4. **Head nods.** The head drops, lifts again, and drops again in cycles of 1–3 s as neck tone fluctuates. The hands fall palm-up beside the hips.
5. **Topple.** When the trunk passes ~25–30° sideways from vertical, it tips over in 0.8–1.2 s onto the shoulder. Head impact is low (1–3 m/s).
6. **Final.** Side-lying or slumped sitting. Agonal breathing and arrest follow `[R1-03 §3.6]` `[R1-04]`.

Without a wall: the person sinks to the knees (controlled, 2–10 s), puts the hands on the floor, lowers onto one hip, then onto the side. Once consciousness goes, the last part is uncontrolled.

### 5.6 Stumble and fall after a leg hit: archetypes D and F of `[R2-02 §5.1]`

| Injury | Mechanical effect | Time to failure under load | Picture |
|---|---|---|---|
| Femoral shaft or neck fracture; hip-joint or pelvic fracture | Structural: support is lost immediately | **0.1–0.3 s** into stance | Drops toward the injured side. The limb lies short and externally rotated (§2.4) `[K] (H)` `[R2-02 §3]` |
| Knee (joint hit, patella) | Knee cannot hold extension | 0.1–0.3 s | Collapses onto the injured knee |
| Thigh muscle wound, no fracture | Pain inhibition: capacity −30–70 % | Often walks; buckles when the knee bends (§3.2) | Limps, then possibly sinks |
| Shank, ankle or foot | No push-off; cannot load the forefoot | Step fails | Hops or falls forward and sideways |
| Sciatic or femoral nerve | Foot drop / knee buckling | Immediate on loading | Trips on the toe (foot drop); knee gives way (femoral) |

Kinematic sequence `[E]` (conscious victim; protective data from `[S3b]` `[S4]`; corrected: was `[S3]`):
1. **0–0.1 s**: the hit leg is loaded; the flinch starts `[R2-02 §1]`.
2. **0.1–0.3 s**: the stance knee flexes 30–60° out of control. The pelvis drops 5–15° on the injured side. The trunk rotates toward the injured side.
3. **0.24 ± 0.03 s**: the other leg tries a rescue step `[S17]`. It is often short or crosses over `[S18]`. A **hop** on the good leg (1–3 hops, 0.3–0.5 s each) happens with p 0.3–0.5 `[E] (L)`.
4. **~0.1 s after balance is lost**: an arm burst; the arms reach toward the ground in < 200 ms (91 % of young adults) `[S4]`. Fact-check: ✓ the ~100 ms burst is consistent with known upper-limb balance-reaction latencies (~80–140 ms) `[K]`. ⚠ The 91 % was not re-verified, and round-two document 02 reports it as "91 % of evoked falls" (trials), not 91 % of people.
5. **0.6–1.4 s**: contact. Hands first in ~74 % of real falls `[S3b]`, then the knee or hip of the injured side, then the shoulder. The body rolls onto the injured side or back. The head strikes the ground in ~37 % `[S3b]`. **Corrected (attribution): was `[S3]` Robinovitch, *Lancet* 2013.** The 74 % / 37 % figures come from the companion paper Schonnop et al., *CMAJ* 2013, on the same video set of 227 falls ✓ verified [K] (M–H). In that study hand impact did **not** reduce the chance of head impact. These are **frail older adults in long-term care**. Treat 37 % as an upper bound for alert young adults, and as a floor for dazed or intoxicated ones.
6. **After landing**: the hand goes to the wound (0.3–1 s); the hips and knees flex (guarding the injured leg); writhing (§7.6).

### 5.7 Spinal cord hits

- **Thoracic or lumbar** (archetype E):
  - the legs vanish within ≤ 100 ms;
  - the body **sits down hard** (buttocks impact 2–3 m/s) or pitches forward over the legs;
  - the arms work and catch the fall.
  - The legs then lie wherever they landed, often externally rotated and crossed.
- **Cervical**: as §4.5. No catch below C5–C7. At C1–C3 it looks like the off switch, **but the person is awake**.

### 5.8 Slipping in blood `[K] (L–M)` / `[E]`

- Blood on a smooth floor gives an available friction coefficient of ~0.1–0.25 while wet `[E] (L)`. It becomes tacky (0.6–0.9) as it dries over 3–10 min, depending on film thickness `[E] (L)`. Fact-check: ⚠ no measurement found or recalled; the wet value, lower than water's, is reasonable because whole blood is ~3–5× as viscous as water, and a more viscous film lubricates better (thicker squeeze film under the heel, as with oil). Both numbers remain estimates.
- **Walking needs a friction coefficient of ~0.17–0.22 at heel strike**; turning or running needs 0.3–0.5 `[K] (M)`. ✓ consistent (fact-check `[K]` (M–H): required-friction studies of level walking give peaks of ~0.17–0.22).
- Heel-strike slip:
  - the heel shoots forward;
  - a slip distance > 10–15 cm or a slip speed > ~0.8–1.0 m/s usually means a fall `[K] (L–M)`;
  - the body falls **backward** in 0.6–0.8 s;
  - contacts: buttock or hip (first), hand and elbow, back;
  - occipital impact in ~20–40 % `[E] (L)`.

### 5.9 Direction

Use `[R2-02 §5.5]`: the fall follows the CM velocity at tone loss, else the lean. For the off switch from quiet stance, the CM is ~2–4° ahead of the ankles `[K] (M)`, which is why **forward-down** is the modal outcome.

### Simulation parameters (collapses)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `offswitch_first_contact` | 0.35–0.55 | s | Knees 2–3 m/s or buttocks 2.5–3.5 m/s | [E] |
| `offswitch_head_impact_t` / `_v` | 0.7–1.2 / 3–5 | s / m/s | | [S2] [R1-04] [E] |
| `syncope_tone_ramp` | 0.5–2 | s | Graded | [K] [E] |
| `syncope_contact_after_buckle` | 1–2.5 | s | | [E] |
| `syncope_head_v` | 2–4 | m/s | | [E] |
| `syncope_jerks` | p 0.9; 1–10 jerks over 3–15 s | — | | [S5] |
| `ko_variant_p` | limp 0.3 / fencing crumple 0.5 / plank 0.2 (plank 0.4–0.6 if knees locked) | p | | [S14] (fencing) [E] |
| `plank_time` / `plank_head_v` | 1.0–1.6 / 5–7 | s / m/s | | [E] [S9] |
| `rubber_legs` | f 1.5–3 Hz, tone 0.35–0.6 ± 0.2–0.3, 1–5 s; fall p 0.4–0.7 | — | | [E] (L) |
| `bleed_strength_curve` | 1 / 0.8 / 0.4–0.6 / 0.1–0.3 by class | — | | [E] on [R1-03] |
| `wall_slide_speed` | 0.1–0.4 | m/s | | [E] |
| `seated_topple_angle` | 25–30 | ° | Then 0.8–1.2 s to the ground | [E] |
| `leg_failure_time` | 0.1–0.3 | s | Fracture or joint under load | [R2-02] [E] |
| `hop_p` | 0.3–0.5 (1–3 hops, 0.3–0.5 s each) | p | Conscious, one leg unusable | [E] (L) |
| `blood_mu_wet` / `blood_mu_tacky` | 0.1–0.25 / 0.6–0.9 | — | Tacky after 3–10 min | [E] (L) |
| `heel_slip_fall` | slip > 10–15 cm or > 0.8–1.0 m/s | — | Backward fall 0.6–0.8 s | [K] (L–M) |

### Visual/behavioural checklist (collapses)
- **Off switch**: an instant of nothing, then the body drops almost straight down; knees forward and apart, arms floating up then flopping, face or back of the head last. All in about a second.
- **Faint**: seconds of warning (pale, swaying, grabbing), then a soft fold and slump. On the floor, eyes open and turned up, a handful of irregular jerks, then (if a true faint) waking within ~15 s.
- **Knockout**: instant. Either a limp heap, a limp heap with one arm stuck up in the air, or a stiff plank tipping over with the feet sliding at the end.
- **Bleeding out**: slow. Lean, slide down the wall, sit, nod, tip over. The wall smear marks the path.
- **Leg hit**: the leg folds in a fraction of a second; the body twists toward it; a hop or a crossing step; hands to the floor; roll; the hand to the wound.
- **Blood slip**: the foot shoots out forward and the body lands on its backside, elbows and back.

---

## 6. Landing, resting and dead weight

### 6.1 Contact order and impact speeds `[E]` (anchors: head impact 2.0–7.4 m/s in standing-height falls of test dummies `[S9]`; hands 74 % / head 37 % `[S3b]`, corrected attribution: was `[S3]`; older adults, see §5.6)

| Fall | 1st contact (t, v) | 2nd | 3rd / head | Arms |
|---|---|---|---|---|
| Crumple forward | Knees (0.35–0.5 s, 2–3 m/s) | Thighs and pelvis, or chest and abdomen | **Face or forehead (0.7–1.1 s), 3–5 m/s** | Trail; land beside the body palms up, or trapped under the chest |
| Crumple backward | Buttocks or sacrum (0.4–0.6 s, 2.5–3.5 m/s) | Lower back, then upper back | **Occiput last with a whip, 3.5–5 m/s** | Flung out, abducted 30–90° |
| Crumple sideways | Lateral knee or hip (0.4–0.6 s, 2–3 m/s) | Shoulder (2–4 m/s) | Temporo-parietal region, 2.5–4 m/s (the neck flexes sideways over the shoulder) | Lower arm trapped under the body |
| Plank forward | Toes pivot; chest, abdomen and face almost together | — | **Forehead or face, 5–7 m/s** | In the posture (fencing or extended) |
| Plank backward | Heels pivot; buttocks and upper back almost together | — | **Occiput 5–7 m/s**, the worst case | In the posture |
| Conscious stumble | Hands (74 %), 2–3 m/s | Knee, hip or shoulder | Head in 37 % (older adults; lower for alert young adults, higher when dazed), 1–4 m/s | Braced, elbows yielding 20–60° |
| Sit-down (paraplegia) | Buttocks, 2–3 m/s | Hands and back | Occiput if it goes backward, 2–4 m/s | Catch |
| Heel slip | Buttocks or hip, 2.5–3.5 m/s | Elbow and hand | Occiput in 20–40 %, 3–5 m/s | Reach backward |
| Syncope sag | Buttocks, knees or hip, 1.5–2.5 m/s | Side or back | Head 2–4 m/s | Limp |
| Seated topple (bled out) | Shoulder, 1–2 m/s | — | Head 1–3 m/s | Limp |

### 6.2 Head whip and impact severity `[E]` / `[K] (M)`

- **Why the head hits hardest.** When the trunk strikes the floor and stops, the limp head keeps its speed. It rotates about the neck until it hits the floor or the neck limit. Its speed at impact is **1.0–1.3 × the upper trunk's speed**. Nothing slows it: no neck-muscle braking, no chin tuck.
- A conscious person tucks the chin in backward falls and turns the face away in forward falls `[R2-02 §5.3]`.
- **Rigid backward topple**: ω_end = √(2 × 72.9 × 9.81 × 0.79 / 69.5) = 4.0 rad/s. Head centre 1.55 m from the pivot, so **v ≈ 6.2 m/s**; top of the head ≈ 6.7 m/s. This matches the upper tail of `[S9]`. ✓ verified (arithmetic: 4.03 rad/s, 6.25 and 6.75 m/s).
- **Energy**: effective mass (head plus some neck) 4.5–6 kg:
  - at 6.5 m/s: 95–127 J;
  - at 4 m/s (crumple): 36–48 J.
- **Deceleration on concrete** `[E]`: with 5–10 mm of scalp and soft-tissue compression, a 5 m/s impact averages v²/(2s) ≈ 1,250–2,500 m/s² (130–255 g); the peak is ~1.5–2× that (≈ 200–500 g).
  - Contact duration: 3–8 ms on concrete, 8–15 ms on wood or carpet `[K] (L)`.
  - Skull-fracture thresholds are in `[R1-02]`.
- Forensic context: in one-punch deaths, the fall onto the ground is a major part of the injury `[S10]`.

### 6.3 Bounce and restitution `[K] (M)` / `[E]`

- The coefficient of restitution of body segments on hard floors is **~0.1–0.3** (soft tissue absorbs); the bony head is ~0.2–0.4.
- Rebound heights `[R2-02 §5.4]` `[E]`: head 1–5 cm, trunk ≤ 1–2 cm, limbs 1–3 cm.
- Bodies do not bounce off the floor. Set `bounce` = 0 on all body parts and let the head collider's hull shape produce its small rebound. If using a restitution value, keep it at or below 0.1.
- The Jolt default bounce-velocity threshold is 1 m/s `[K] (M)`: impacts slower than that never bounce. ✓ consistent (fact-check `[K]`: Jolt's own `PhysicsSettings` default for the minimum restitution velocity is 1.0 m/s).
- Fact-check `[K]` (M): the restitution range 0.1–0.3 is plausible but **no source was read** for it, so it stays (M). The design rule (bounce 0) is correct regardless.
- **Gap (fact-check) `[K]` (M): Godot adds the two bounce values of a contact** (clamped to 0–1; this is why `PhysicsMaterial.absorbent` exists, to subtract instead). A body part with bounce 0 still bounces off a floor whose material has bounce 0.3. **Set bounce 0 on every floor, wall and prop the bodies can land on as well.** Check that the Jolt backend in 4.5 keeps this rule (it was written to match Godot Physics).

### 6.4 Friction and sliding `[K] (M)` values, `[E]` game values

| Pair | μ (static / kinetic) | Game value |
|---|---|---|
| Cotton or denim clothing on concrete | 0.5–0.7 / 0.4–0.6 | 0.55 ✓ consistent (fact-check `[K]` (M): pedestrian-sliding values on road surfaces used in accident reconstruction are ~0.45–0.7) |
| Clothing on polished wood or vinyl | 0.3–0.5 / 0.25–0.4 | 0.4 |
| Synthetic (nylon, polyester) on smooth floor | 0.25–0.4 | 0.3 |
| Bare dry skin on floor | 0.4–0.8 (rises with slight moisture) | 0.6 |
| Wet with water | 0.2–0.4 | 0.3 |
| Wet blood / tacky blood | 0.1–0.25 / 0.6–0.9 | 0.18 / 0.75 `[E] (L)` |
| Shoe on dry floor / wet tile | 0.5–0.9 / 0.1–0.3 | 0.7 / 0.2 |
| Body on grass / soil | 0.3–0.6 | 0.45 |

- **Slide distance** after the body lands moving: d = v²/(2μg). At 5 m/s and μ = 0.5: **2.5 m** ✓ verified (2.55 m).
  - **Gap (fact-check) `[E]`**: 5 m/s is a *horizontal* speed that only running, a vehicle or a stairway fall gives. In a collapse from standing, the impact speed is mostly vertical, and the CM's horizontal speed at contact is ~0.5–2 m/s. The body then slides **0.03–0.4 m**, and most of the energy goes into the impact. A body that slides a metre after a standing collapse is a bug (too little friction or too much bounce).
- **Dragging force** for a 75 kg body: μ·m·g = 0.4–0.6 × 736 N = **300–440 N** on concrete and 140–220 N on smooth wet floors ✓ verified (arithmetic: 294–442 N). Pulling up at an angle lifts part of the weight and lowers this by 10–25 %. A single person drags a body in short heaves, not smoothly `[E]`.
- **Rolling.** Capsules and spheres are perfect rollers. Real flesh has a flat contact patch and **does not roll on its own**, so dead limbs roll unrealistically on slopes as small as 2–3°. Fix it with **contact-dependent angular damping** (§6.5, §8.6) and hull shapes for the head and trunk.

### 6.5 Settling sequence `[E]` (qualitative basis `[K] (M)`)

| t after last major impact | What happens |
|---|---|
| 0–0.3 s | Rebounds; limbs flop to their limits; the arms slap down |
| 0.3–1.0 s | Secondary rolls: a bent top knee falls sideways; the head rolls 20–60° off the midline onto the side of the occiput; an arm slides off the chest |
| 1–2 s | Soft-tissue flattening (shader): cheek, chest, abdomen and buttocks spread 1–2 cm at the contacts; clothing drapes; air forced out (audible exhale on the first chest impact) |
| 2–5 s | Micro-settling stops. Total kinetic energy < 0.5 J. Sleep allowed |
| Minutes–hours | Jaw drops further; livor and rigor timelines `[R1-04 §12]` |

Settling controller:
- When a body is unconscious or dead, touching the ground, and its total kinetic energy has stayed below 2 J for 0.5 s, **ramp angular damping from 0.1 to 3–8 over 0.5 s** and linear damping from 0 to 0.5–1.
- On any external hit, reset both to the moving values (0.1 / 0).
- This mimics tissue-contact friction and removes creeping and rolling.
- Never raise damping before the body has settled: that is the "falling through syrup" look.

### 6.6 Final resting poses, and why they look "wrong"

Probabilities `[E] (L)` (no dataset was available):

| Fall | Prone | Side | Supine | Other |
|---|---|---|---|---|
| Forward | 0.55–0.65 | 0.25–0.35 | 0.05–0.10 | |
| Backward | 0.05 | 0.25 | 0.70 | |
| Vertical crumple | 0.25 | 0.40 | 0.20 | Folded or kneeling: 0.15 |

Why a dead or unconscious body looks wrong, and why each is correct `[K] (M)`:
1. **Nothing is held up.** Every segment rests on the floor or on another segment. Living people always hold something up: the head, a hand, a knee.
2. **Joints sit at the ends of their range** (§2.6):
   - the backs of the hands and feet lie flat on the floor;
   - wrists are bent 60–90°;
   - the head is turned 70–90° on the cheek;
   - feet splay out at 45–60° each.
3. **Limbs are trapped under the body**: an arm under the chest, palm up, the shoulder rolled inward. No awake person tolerates the load, so it never appears in living poses.
4. **Twist between regions**: the pelvis faces one way and the shoulders 30–45° another. Legs are folded under while the trunk lies sideways.
5. **No protective arrangement**: no hand under the face, no knee drawn up for comfort. It is unlike the recovery position that living sleepers adopt.
6. **Limp hands**: fingers half-curled, following the wrist through tenodesis; thumb tucked against the index finger.
7. **Face**: mouth open 10–30 mm; eyelids part-open `[R1-04]`. The face is pressed and distorted where it touches the floor.
8. **Complete stillness**: no postural sway, no breathing.
   - A living unconscious person breathes 12–20 /min with 5–10 mm of chest and abdominal motion `[K] (M)`.
   - **The absence of this micro-motion is the strongest cue of death**, stronger than any pose.

Ragdoll errors that look wrong in the *bad* way. These are bugs, not realism:
- jitter at rest;
- interpenetration of limbs;
- rotations beyond the limp ROM (a head turned 180°, a knee bent sideways without a fracture);
- hovering above the floor;
- perpetual rolling;
- limbs frozen in mid-air (premature sleep);
- a stiff T-pose snap at death;
- rubber-band stretching of joints under load.

### 6.7 Handling dead weight (player interactions) `[E]`

- **Lifting the shoulders** of a supine body: needs **~0.35–0.45 × body weight (260–330 N)** at the start of the lift. **Corrected: was ~0.5–0.6 × body weight (360–440 N).** Fact-check `[E]`: with the hips as the pivot, HAT weight 443 N acts 0.34 m from the hip, and the hands lift at the upper back or armpits 0.45–0.53 m from the hip: 443 × 0.34 / (0.45–0.53) = 285–335 N. For a vertical pull both lever arms shrink together as the trunk rises, so the force stays roughly constant until the head flops forward past the hips. The head falls back to the neck-extension limit (60–85°) and the arms hang and swing. Trying to stand the body up makes the knees fold.
- **Dragging by one wrist**: 300–440 N on concrete (§6.4).
  - The shoulder elevates to 150–180° of abduction.
  - The head rolls away from the pulled arm and scrapes.
  - The free arm trails, palm up. The legs pull straight and the heels drag, leaving two lines in blood.
- **Kicking the trunk**: a strong kick delivers ~20–40 N·s. The trunk region (~30 kg effective) moves at 0.7–1.3 m/s and slides 5–15 cm (μ 0.5). Limbs flop with a lag of 50–150 ms.
- **Shooting a body.** The whole-body effect is negligible (`[R1-01]`, Karger `[S20]`), but **light segments visibly jump**, because the impulse first acts on the struck segment. Apply the true impulse at the hit point, never multiplied. ✓ verified (fact-check: momenta recomputed from standard loads, e.g. 8.0 g × 360 m/s = 2.9 N·s; 9 × 3.5 g × 400 m/s = 12.6 N·s; whole body 12.6 / 75 = 0.17 m/s). **Myth guard**: no small-arms round throws a person backward or off their feet. What looks like knock-back in real footage is the person's own movement: a startle, a stumble, legs giving way, or a deliberate dive (§7.6).

  | Round | Momentum (N·s) `[K] (M)` |
  |---|---|
  | 9 mm | 2.9 |
  | .45 ACP | 3.9 |
  | 5.56 mm | 3.8 |
  | 7.62×39 | 5.7 |
  | 7.62×51 | 8.0 |
  | 12-gauge 00 buckshot (9 pellets) | 12.6 |
  | 12-gauge slug | 13.4 |

  The transferred fraction is 100 % if the bullet stays in the body and 10–50 % if it passes through `[E]`. Resulting segment Δv `[E]`:

  | Case | Δv (m/s) |
  |---|---|
  | Limp head (4.4 kg), retained 9 mm | 0.66 |
  | Limp head, rifle round passing through (30 %) | 0.2–0.4 |
  | Limp head, buckshot | **≈ 2–3** (a visible snap). Fact-check `[E]`: upper bound, all nine pellets hitting the head and staying in it (12.6 / 4.4 = 2.9 m/s). With spread, or pellets exiting, use 0.5–2 m/s. The neck adds effective mass within 20–50 ms, and a head resting on the floor is stopped by it |
  | Hand, 9 mm passing through (10–20 %) | 0.6–1.3 (a flick) |
  | Upper trunk (12 kg), buckshot | ~1 locally, dispersing through the joints within 20–50 ms |
  | Whole body, buckshot | ~0.17 `[R1-01]` |

### Simulation parameters (landing and rest)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `impact_v_table` | §6.1 | m/s | Validation targets | [E] [S9] [S3b] |
| `head_whip_factor` | 1.0–1.3 × upper-trunk speed | — | Limp neck | [E] |
| `head_peak_g_concrete_5ms` | 200–500 | g | For damage and audio | [E] |
| `head_contact_duration` | 3–8 (concrete) / 8–15 (wood, carpet) | ms | | [K] (L) |
| `body_bounce` | 0 (≤ 0.1) | — | | [K] (M) |
| `rebound_head` / `rebound_trunk` | 1–5 / ≤ 1–2 | cm | | [E] |
| `mu_table` | §6.4 | — | Per surface | [K] (M) [E] |
| `drag_force_75kg` | 300–440 | N | Concrete ✓ verified (arithmetic) | [E] |
| `lift_shoulders_force` | 260–330 (0.35–0.45 × body weight) | N | Supine body, hips as pivot. Corrected: was 360–440 N in §6.7 | [E] |
| `floor_bounce` | 0 | — | Godot adds the two bounce values; floors must be 0 too (fact-check addition) | [K] (M) |
| `standing_collapse_slide` | 0.03–0.4 | m | Horizontal CM speed at contact 0.5–2 m/s (fact-check addition) | [E] |
| `settle_trigger` | KE < 2 J for 0.5 s, unconscious, grounded | — | | [E] |
| `settle_damping` | angular 3–8, linear 0.5–1 (ramp 0.5 s) | 1/s | Reset on any hit | [E] |
| `sleep_after` | 2–5 | s | Total KE < 0.5 J | [E] |
| `rest_pose_p` | §6.6 | p | | [E] (L) |
| `bullet_momentum` | 9 mm 2.9 … slug 13.4 | N·s | Transfer 1.0 retained / 0.1–0.5 through-and-through | [K] (M) [E] |
| `kick_impulse` | 20–40 | N·s | | [E] |
| `breathing_motion_alive` | 12–20 /min, 5–10 mm | — | Absent when dead | [K] (M) |

### Visual/behavioural checklist (landing and rest)
- Unconscious impact order: body parts first, then the head last and hardest, with a small bounce. The arms slap down a beat after the trunk.
- The body stops sliding quickly and never rolls on its own on a nearly flat floor.
- Within ~2 s everything is still. Flesh is flattened where it touches, the head lies turned, the feet splay, the hands are half-curled.
- Living but unconscious: the chest rises and falls. Dead: nothing moves.
- Dragging a body: the head lolls back and scrapes, the heels drag, the free arm trails. It takes effort and comes in jerks.
- Shooting a corpse: the body does not move; the hit part twitches (a hand flicks, the head snaps a little under a shotgun).

---

## 7. Active ragdoll control

### 7.1 PD on quaternions `[K] (H)` method, `[E]` values

For each simulated joint j (child c, parent p), in the parent frame:
1. q_err = q_target × conj(q_current). Take the shortest path (negate if w < 0) and convert to an axis–angle pair (â, φ).
2. ω_rel = ω_c − ω_p (world, rotated into the parent frame).
3. τ = kp · φ · â − kd · ω_rel + τ_gravity_comp (§7.3) + τ_passive (§3.3).
4. Clamp per axis to ± τ_cap × strength (§3.1). The clamp is what makes weakness look like weakness: the target is still wanted, but the muscle cannot achieve it.
5. Apply +τ to the child body and **−τ to the parent body**. Muscles are internal forces. Skipping the reaction adds net angular momentum from nowhere ("hand of God" spins, levitation). ✓ verified (fact-check `[K]` (H): Newton's third law; internal torques cannot change the body's total angular momentum; only contacts with the ground or other objects can).

Stability:
- keep ω·Δt ≤ 0.5 (§4.1);
- clamp the target angular velocity to 15–20 rad/s;
- compute gains from I_eff once at spawn (reference pose) and rescale if a segment is severed.

**Stable PD** (Tan, Liu & Turk 2011) `[K] (M)` predicts the next-step state and allows ~5–10× stiffer gains at the same Δt. It is optional here, because the target ω ≤ 16 rad/s already fits at 60 Hz.

### 7.2 Gains in the literature `[K] (L–M)` unless tagged

| System | Gains | Notes |
|---|---|---|
| NaturalMotion Euphoria (GTA IV/V) | "Stiffness" ~6 (weak) to ~16 (strong); "damping" ~1 (critical) | Behaviour names in `[S12]`. Stiffness acts like a natural frequency in rad/s and damping like a damping ratio `[K] (M)`. Fact-check: ⚠ not re-verified. The 6–16 range matches the checker's recall of the published NM message parameters (e.g. body and arm stiffness with default ~11); the rad/s interpretation is inferred, not documented |
| Jolt motors | Spring frequency in Hz + damping ratio, plus torque limits | Frequency-based, like §4.1 |
| DeepMimic (Peng et al. 2018) | kp 100–1000, kd = 0.1 × kp | Stiff tracking controller |
| SIMBICON (Yin, Loken, van de Panne 2007) | kp ~300–1000 Nm/rad, kd ~0.1 × kp; balance feedback c_d 0–0.5 rad/m, c_v 0.2–0.5 rad·s/m | Walking controller |
| Zordan & Hodgins 2002 `[S13]` | Gains scaled by chain inertia; lowered on impact, then restored | The basis of §4.2 "hit compliance" |
| Zordan et al. 2005 `[S13]` | Simulate on impact, then blend into a matching motion-capture reaction | Reaction clips optional |
| Ha, Ye & Liu 2012 `[S13]` | Falling controller: airborne phase + landing (rolling) phase limiting joint stress | Conscious-fall reference |

### 7.3 Gravity compensation and stance support `[K] (H)` method

- **Gravity compensation** lets low, realistic gains hold posture: the body looks soft to hits but does not sag. For each joint j:

  τ_g(j) = −Σ_(b ∈ subtree(j)) (r_b,CM − r_j) × (m_b · **g**)

  Apply the fraction g_comp (§4.2) × tone × strength. **It must be exactly 0 once unconscious.**
- **Stance legs** (closed chain). Compensate with a virtual force F = −m_body·**g**·support_fraction at the pelvis, mapped to the stance-leg joints by the Jacobian transpose: τ = Jᵀ·F (Coros et al. 2010 style `[K] (M)`). Split the fraction between the legs by CM position. An injured leg takes a share ≤ its strength.
- **Assist forces** (non-physical, standing only) `[E]`: a pelvis upright torque τ = −k_u·θ_tilt − d_u·ω, with k_u = (0.5–1.5)·m·g·h_CM × balance_capacity.
  - Keep ≤ 0.3 × body weight of vertical assist.
  - **Hard rule: zero assist when falling, unconscious, or once the fall archetype has started.** Otherwise the fall looks guided. ✓ verified (design rule; fact-check agrees: any leftover assist lengthens the §9 T2 timings and is detectable there).

### 7.4 Balance and stepping `[K] (H)` method (Hof extrapolated CM), numbers from `[R2-02 §4]`

- XcoM = x_CM + v_CM / ω₀, with ω₀ = 3.20 s⁻¹. Margin b = the distance from XcoM to the edge of the support polygon.
- When b < 0.02 m: **step**.
  - Target = XcoM + 0.02–0.05 m along the CM velocity.
  - Swing time 0.25–0.4 s; toe-off at 0.24 ± 0.03 s `[S17]`.
  - Maximum step length = (0.3–0.8 m) × leg_capacity.
  - If the required step exceeds the maximum, or leg_capacity < 0.3, go to a fall archetype `[R2-02 §4.2]`.
- **Hip strategy** during hits: counter-rotate the trunk and windmill the arms (§7.6).
- Swing-hip feedback (SIMBICON form): θ_swing = θ₀ + c_d·d + c_v·v, with c_d 0–0.5 rad/m and c_v 0.2–0.5 rad·s/m `[K] (M)`.
- Lateral: a crossover step in ~50 % of multi-step responses when weak `[S18]`.
- Single-step lean limit: 23.5° + 8.7° × leg_capacity (32.2° young and healthy) `[S15]`.

### 7.5 Hit response (Zordan–Hodgins style) `[S13]` method, `[E]` values

1. Apply the physical impulse at the hit point (tiny for bullets, §6.7; ~26–32 N·s for a punch, `[R2-02 §1.3]`).
2. Hit compliance: on the hit chain (the struck segment ± 2 joints), kp × 0.2–0.4 for 0.1–0.3 s, then restore over 0.2–0.5 s.
3. Add the flinch overlay `[R2-02 §1.1]` as additive target offsets on top.
4. If XcoM leaves the support polygon, start stepping (§7.4). If stepping cannot recover, start stagger or fall.
5. If the physiology state changes (loss of consciousness, a limb disabled), the new tone overrides immediately.

### 7.6 Behaviour library (Euphoria-like) `[S12]` names where listed, `[K] (M)` others, `[E]` parameters

| Behaviour | Purpose | Effectors | Parameters | Start / stop | Conscious only? |
|---|---|---|---|---|---|
| **ConfigureBalance / StayUpright** `[S12]` | Stand and step (§7.4) | Legs, pelvis | Leg ω 10–12; step 0.25–0.4 s; give-up time 0.5–3 s × capacity | While capacity > 0.3 | Yes |
| **Shot** `[S12]` | Umbrella reaction to a gunshot | All | Spine ω 10 → 6–8 for 0.3 s; "snap" burst 40–120 ms of 20–60 Nm on the spine **in the startle-flexion direction** (trunk flexion 3–10°, head flexion 5–15°, shoulders up; `[R2-02 §1.1]`), **independent of the bullet's direction**. For a hit limb, add a withdrawal away from the stimulus. **Corrected: was "along the hit direction"**, which reproduces the knock-back myth: a frontal hit would bend the spine backward. Then reach and stagger | On the hit | **Yes. Corrected: was "Partly (the snap also acts on the unconscious as a physical twitch)".** An unconscious or dead body has no startle; only the true physical impulse (§6.7) acts on it (`startle_when_unconscious` = 0 in `[R2-02]`) |
| **ShotFallToKnees** `[S12]` | Legs give out, conscious | Legs | Knee target 90–120°, knee ω 4–6; then fold forward or sideways | Leg capacity < 0.4 | Yes |
| **StaggerFall** `[S12]` | Losing race to the CM | Legs, arms | 3–6 steps, leg ω decaying 10 → 4, heading noise ±20–40° | After a failed recovery | Yes |
| **ArmsWindmill** `[S12]` | Hip-strategy balance | Arms | Shoulder circles at 1–2 Hz, amplitude 60–120°, 0.5–1.5 s | Backward balance loss | Yes |
| **CatchFall** `[S12]` | Arms to the predicted ground contact | Arms, head | Onset burst ~100 ms, oriented < 200 ms `[S4]`; shoulder flexion 60–100°, elbows 10–30°, wrists extended 60–90°; **on contact, elbow ω drops to 4–6 so the elbow yields 20–60°**; head turned 30–60° away | Fall predicted | Yes |
| **ProtectHead** `[K]` | Shield the head from blows or a backward fall | Arms, neck | Forearms around the head, elbows 120–140°, shoulders 90–120° flexed; chin tuck 20–40° at neck ω 15 | Threat or backward fall | Yes |
| **ReachForWound** (part of Shot) `[K]` | Hand to the wound, apply pressure | Nearest working arm | IK in 0.3–1.0 s; contact force 5–20 N; elbow ω 8. Reachability: face, neck, chest, abdomen, thighs, opposite arm, lumbar region; **the interscapular back is unreachable** | Wound noticed | Yes |
| **BodyWrithe** `[S12]` | Pain on the ground | All | Smooth noise on joint targets at 0.2–1.0 Hz: hips and knees 20–60°, spine 10–30°, arms reaching; ω 5–8; bursts on pain spikes; breath-hold pauses of 1–5 s | Conscious, grounded, pain > threshold | Yes |
| **RollUp / Foetal** `[K]` | Curl to protect | All | Hips 90–120°, knees 110–140°, spine flexion 30–60°, arms around the head or abdomen | Repeated blows, abdominal pain | Yes |
| **HeadLook** `[K]` | Look at the threat or wound | Neck, eyes | Neck ω 10; eyes lead the head by 50–150 ms `[R2-01 §14]` | Always, if conscious | Yes |
| **InjuredOnGround** `[K]` | Try to rise or crawl | All | Push-up attempts; roll to the side; crawl at 0.1–0.3 m/s | Conscious, able | Yes |
| **BodyRelax** `[S12]` | Release all tone | All | ω → 0 over the tone-loss ramp (§4.4) | Loss of consciousness, death | — |
| **Posture / Seizure** `[R2-01]` | Physiology-driven motor programmes | Per the table in `[R2-01 §17–18]` | §4.2 tonic, posturing and clonic rows | Physiology | — (these are unconscious behaviours) |

### 7.7 Layering and arbitration `[E]` (layers from `[R2-02 §0.4]`)

Every behaviour writes, for each effector (joint) it drives, the tuple (target, ω, ζ, weight, priority). The mixer:
1. **Physiology gate first.** For each joint group, tone ∈ [0, 1] and strength ∈ [0, 1] come from consciousness, the spinal level, hemiparesis and blood loss. If tone = 0, no behaviour can drive that joint.
2. **Priority order (highest first)**:
   1. physiology motor programmes (posturing, seizure, fencing);
   2. reflex (flinch, withdrawal);
   3. protective (CatchFall, ProtectHead);
   4. balance and stepping;
   5. ReachForWound;
   6. Writhe / HeadLook / idle.
3. A higher priority claims an effector with weight w. Lower priorities fill the remaining weight (1 − w). Blend targets with quaternion slerp by weight; blend ω and ζ linearly.
4. **Blend times** `[R2-02 §13]`: behaviour switches 50–300 ms; tone loss ≤ 100 ms; reflex onsets on the physics tick.
5. **Unconscious**: only physiology programmes and passive terms remain. Everything else is removed within ≤ 100 ms.

### 7.8 Controller skeleton (pseudocode written for this document; not taken from any source)

```
each physics tick (dt):
  phys = physiology.sample()            # per joint group: tone, strength, program
  for joint in joints:
    cmd = mixer.resolve(joint, behaviours, phys)  # target, omega, zeta, weight
    t   = phys.tone[joint.group]
    kp  = joint.I_eff * cmd.omega^2 * t
    kd  = 2 * cmd.zeta * joint.I_eff * cmd.omega * sqrt(t)
    err = shortest_axis_angle(cmd.target * conj(joint.q_local))
    w   = joint.child.ang_vel - joint.parent.ang_vel
    tau = kp*err - kd*w
    tau += phys.gcomp[joint.group] * t * joint.gravity_comp_torque()
    tau += joint.passive_torque()        # always on (section 3.3)
    tau  = clamp_per_axis(tau, joint.tau_max * phys.strength[joint.group])
    apply_torque(joint.child,  +tau)
    apply_torque(joint.parent, -tau)
```

### Simulation parameters (active control)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `pd_form` | quaternion error, axis–angle | — | Plus reaction torque on the parent | [K] (H) |
| `target_vel_clamp` | 15–20 | rad/s | | [K] (M) |
| `gcomp_fraction` | 1 alive / 0.5–0.8 dazed / 0 unconscious | — | | [E] |
| `assist_upright_k` | 0.5–1.5 × m·g·h_CM × capacity | Nm/rad | Standing only; 0 when falling | [E] |
| `assist_vertical_max` | 0.3 × body weight | N | | [E] |
| `xcom_step_margin` | 0.02–0.05 | m | | [K] [E] |
| `simbicon_cd` / `simbicon_cv` | 0–0.5 / 0.2–0.5 | rad/m / rad·s/m | | [K] (M) |
| `catchfall_elbow_yield` | ω 4–6 on contact; 20–60° yield | — | | [E] |
| `reach_wound_time` / `force` | 0.3–1.0 / 5–20 | s / N | | [R2-02] [E] |
| `writhe_freq` / `amp` | 0.2–1.0 / hips and knees 20–60°, spine 10–30° | Hz / ° | | [E] |
| `windmill` | 1–2 Hz, 60–120°, 0.5–1.5 s | — | | [E] |
| `shot_snap` | 40–120 ms, 20–60 Nm, spine, **startle-flexion direction** (corrected: was "along the hit direction"); 0 when unconscious | — | Never a push in the bullet's direction | [E] [R2-02] |
| `priority_order` | physiology > reflex > protective > balance > reach > writhe/idle | — | | [E] |

### Visual/behavioural checklist (active control)
- A conscious hit body gives at the hit point, recovers in ~0.5 s, and steps if it has to. Its arms react to falling within ~0.1–0.2 s.
- Weakness looks like effort failing: the knee tries to straighten and cannot, the arm reaches and falls short.
- When consciousness goes, every voluntary behaviour disappears within 100 ms. No guided falls, no residual balancing.
- Behaviours stack: a flinch on top of a stagger on top of a hand pressing the wound.

---

## 8. Godot 4.5 + Jolt setup

All API names, paths and defaults here are `[K] (M)` (Godot 4.3–4.4 and the godot-jolt integration). **Verify in 4.5** (§12). The search planned in `[R2-02 §0.1]` for these details was also refused.

Fact-check `[K]` (M), no documentation re-read:
- ✓ The §8.3 Jolt defaults (10 velocity steps, 2 position steps, 0.03 m/s and 0.5 s sleep, 1.0 m/s restitution threshold, 0.02 m speculative distance, Baumgarte 0.2) match Jolt's own `PhysicsSettings` defaults, which the Godot module exposes.
- ✓ The Godot "Using Jolt Physics" notes list the soft-limit joint properties (`bias`, `softness`, `relaxation` on hinge and cone-twist joints; limit softness, restitution and damping on 6DOF) as unsupported by the Jolt backend.
- ✓ `PhysicalBoneSimulator3D` has been a `SkeletonModifier3D` since 4.3 and carries `physical_bones_start_simulation()` / `physical_bones_stop_simulation()` and `influence`.
- In 4.5 the default 3D engine for new projects is still GodotPhysics3D, so Jolt must be selected by hand. Later versions may change the default; check the project setting, do not assume it.
- **Gap**: `PhysicalBone3D` exposes `mass`, `friction`, `bounce`, damping and damp modes, `gravity_scale` and `can_sleep` directly. It has **no `physics_material_override`** (so no `rough` / `absorbent`), and no inertia or continuous-collision-detection properties. Set those through `PhysicsServer3D` on the bone's RID (`body_set_param(rid, BODY_PARAM_INERTIA, …)`, `body_set_enable_continuous_collision_detection(rid, true)`), then check that they survive the simulator starting and stopping.

### 8.1 Node structure and body list

- `Skeleton3D` → `PhysicalBoneSimulator3D` (a `SkeletonModifier3D` since 4.3) → `PhysicalBone3D` × N.
  - Control: `physical_bones_start_simulation(bones)` / `physical_bones_stop_simulation()`.
  - `influence` (0–1) blends the whole simulation with the animated pose.
  - Partial ragdoll: pass a list of bone names to simulate only those.
- **Core bodies (17)**:
  - pelvis (lower trunk), spine (middle trunk), chest (upper trunk);
  - neck, head;
  - upper arm, forearm and hand ×2;
  - thigh, shank and foot ×2.
- Do **not** simulate clavicles, fingers or toes. Drive fingers procedurally from tone plus tenodesis (§2.5).
- Optional: a jaw (for the dropping jaw) as an animated bone, not a physical body.
- Fracture joints (§2.7): represent a mid-shaft fracture as a flag that widens the neighbouring joint's limits and adds a visual bend in the skinning, unless the rig already has twist or roll bones that can act as a hinge. Splitting bodies at runtime needs verification in 4.5.

### 8.2 Joint type and limits per bone `[E]` (values from §2 alive/dead)

| Body (joint to parent) | Joint type | Limits: alive / dead | Notes |
|---|---|---|---|
| Spine (to pelvis) | 6DOF | Flex 30/38, ext 15/20, lateral ±12/15, twist ±4/6 | `spine_lower` |
| Chest (to spine) | 6DOF | Flex 45/60, ext 20/28, lateral ±22/30, twist ±35/45 | `spine_upper` |
| Neck (to chest) | 6DOF | Flex 40/50, ext 50/60, lateral ±32/40, twist ±35/45 | |
| Head (to neck) | 6DOF | Flex 15/20, ext 20/25, lateral ±8/10, twist ±40/45 | |
| Upper arm (to chest) | **Cone with offset axis**, or 6DOF | Cone centred at ~60–70° flexion and ~40–45° abduction, half-angle 95–105°; twist −80 / +90 (internal / external) | The symmetric cone approximates an asymmetric shoulder |
| Forearm (to upper arm) | Hinge | −5 → 145 / −10 → 155 | Pronation lives in the wrist twist |
| Hand (to forearm) | 6DOF, or cone + twist | Flex 85/90, ext 80/90, radial 25, ulnar 40/45; twist ±80/90 (pronation and supination) | |
| Thigh (to pelvis) | **Cone with offset axis**, or 6DOF | Cone centred at ~50° flexion and ~10° abduction; half-angles ~75° sagittal, ~40° frontal (elliptical if supported, else ~60°); twist −45/−50 → +55/+70 (internal → external) | Add the hamstring coupling torque (§2.5) |
| Shank (to thigh) | Hinge | −5 → 150 / −10 → 158 | Negative = hyperextension |
| Foot (to shank) | 6DOF, or cone + twist | Dorsiflexion 25/30, plantarflexion 55/65, inversion 35/40, eversion 20; twist ±10 | |

**Offset-cone trick** `[E]`: rotate the joint frame (`joint_rotation`) so the symmetric cone's axis points at the centre of the real, asymmetric range. Then set the half-angle to half of the range's span. Verify it with a sweep test (§9, T13).

**6DOF caution**: per-axis Euler limits interact near 90° on the middle axis (gimbal). For the shoulder and hip, prefer the cone with an offset axis.

**Soft end-feel**: Jolt's limits are hard. `bias`, `softness` and `relaxation` on Godot's cone and hinge joints were **not supported** in the Jolt integration `[K] (M)`. Implement the soft zone (§3.3) with script torques.

### 8.3 Project and Jolt settings

| Setting (path to verify) | Default `[K]` | Recommended | Reason |
|---|---|---|---|
| `physics/3d/physics_engine` | GodotPhysics3D (Jolt is an option since 4.4) | **Jolt Physics** | Brief |
| `physics/common/physics_ticks_per_second` | 60 | 60 for crowds / **120** for ragdolls the player examines | Contact quality, PD stability |
| `physics/common/physics_interpolation` | off | **on** | Smooth rendering between ticks |
| `physics/3d/default_gravity` | 9.8 | 9.81 | |
| `physics/3d/default_linear_damp` / `default_angular_damp` | 0.1 / 0.1 | Override per body (mode Replace): linear 0–0.05, angular 0.05–0.3 while moving | Air-drag look = floaty |
| `physics/jolt_physics_3d/simulation/velocity_steps` | 10 | **12–16** | Long joint chains with contacts |
| `physics/jolt_physics_3d/simulation/position_steps` | 2 | **3–4** | Less joint stretch and drift |
| `.../simulation/sleep_velocity_threshold` | 0.03 m/s | 0.03–0.05 | |
| `.../simulation/sleep_time_threshold` | 0.5 s | 0.5–1.0 s + the settle controller (§6.5) | Avoid limbs freezing mid-swing |
| `.../simulation/bounce_velocity_threshold` | 1.0 m/s | 1.0 | |
| `.../simulation/speculative_contact_distance` | 0.02 m | 0.02 | |
| `.../simulation/baumgarte_stabilization_factor` | 0.2 | 0.2 | |
| `.../simulation/use_enhanced_internal_edge_removal` | on | on | Limbs sliding over triangle-mesh floors without snagging |

### 8.4 Materials, collision filtering, CCD

- **PhysicsMaterial**:
  - body parts: friction 0.55–0.6, bounce 0, `absorbent` on. **Corrected (fact-check `[K]` (M)): `PhysicalBone3D` has no PhysicsMaterial slot.** Set its own `friction` (0.55–0.6) and `bounce` (0) properties; `absorbent` and `rough` are not available on bones. Put the zero bounce on the floor materials instead (§6.3: Godot adds the two bounce values);
  - floors: from §6.4;
  - blood-pool zones: override the floor friction to 0.18 (wet) → 0.75 (tacky) over 3–10 min.
- **Friction combine**: GodotPhysics uses the minimum of the two frictions unless `rough` is set (then the rough body's own friction; corrected wording: was "then the maximum") `[K] (M)`. Verify the Jolt backend's rule in 4.5. If in doubt, give body parts friction ≥ the highest floor friction, so the floor value governs.
- **Collision**:
  - exclude parent–child pairs;
  - **keep non-adjacent self-collision on** (arm vs trunk, leg vs leg, hand vs head). Without it, limbs pass through the body and the hand-drop test (§3.4) fails;
  - put ragdoll bodies on their own layer and let them collide with the world, props and other ragdolls.
- **Continuous collision detection** for the head, hands and feet if `PhysicalBone3D` exposes it (verify). Otherwise keep floor colliders ≥ 0.2 m thick. A limb moving at 10 m/s travels 0.17 m per 60 Hz tick.
- **Inertia**: if `PhysicalBone3D` computes inertia only from the shape, check the hand, foot and neck against §1.3. If needed, fatten the collider slightly or raise the neck mass (mass-ratio rule, §1).

### 8.5 How to drive the joints

| Option | How | Pros | Cons |
|---|---|---|---|
| **A. Script torques** (recommended first) | In `_physics_process`, compute §7.8 and call `PhysicsServer3D.body_apply_torque(rid, τ)` on the child and −τ on the parent (or `state.apply_torque` in `_integrate_forces`) | Full control: quaternion error, gravity compensation, caps, soft limits | Explicit, so respect ω·Δt ≤ 0.5 |
| B. 6DOF angular springs | Per axis: stiffness = kp, damping = kd, equilibrium = target angle, updated each tick | Solver-side, possibly implicit (more stable) | Euler axes; gimbal near 90°; verify support in the Jolt backend |
| C. Velocity motors | Motor target velocity = ω_n × error (clamped), force limit = τ_cap | Implicit damping; very stable | Verify that `PhysicalBone3D` exposes motors; less direct control of stiffness |

- **Animation targets**: sample the `AnimationTree` pose into a buffer *before* the simulator modifier overrides the skeleton. SkeletonModifier3D processing order matters; verify in 4.5.
- **Partial ragdoll**: bones that are not simulated stay animated. Blend a simulated chain into the animation with per-chain weights (a limp arm on a staggering body `[R2-02 §13]`).

### 8.6 "Heavy, not floaty": rules

1. **Real scale, real masses, g = 9.81.** Do not raise gravity to fake weight; it breaks every timing in §9.
2. **Near-zero linear damping.** Keep angular damping low while moving. Damping is the main cause of the slow-motion look.
3. **Tone loss in ≤ 100 ms** for off-switch causes. A multi-second fade to limp looks like a puppet being lowered.
4. **No assist forces during a fall.** No hidden upright torques or vertical support.
5. **Soft limits with damping, hard stops behind them.** No elastic clanks at the joint limits.
6. **Bounce 0.** Head rebound only from the collision geometry.
7. **Colliders inside the skin**, with shader flattening at the contacts.
8. **Correct impact audio**: loudness scaled by impact speed and effective mass (a head at 5 m/s is a sharp crack; a trunk at 2 m/s is a deep thud), plus air forced out of the chest on the first trunk impact.
9. **Settle, then sleep.** Everything is still within 2–5 s.
10. **Check the timings** (§9): if the crumple takes 2 s, something is damped or assisted.

### 8.7 Performance `[E]`

- 17 bodies and 16 joints per character. The PD loop is ~16 × ~60 floating-point operations per tick: negligible. The Jolt solve dominates.
- Budget ~0.05–0.1 ms per active ragdoll per tick on a desktop CPU `[E] (L)`. Measure it.
- Sleeping bodies cost almost nothing.
- For many corpses: after 30–60 s asleep, bake the pose into a static mesh with simplified colliders. Re-create the ragdoll when it is hit.

### Simulation parameters (Godot/Jolt)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `ragdoll_bodies` | 17 | count | §8.1 | [E] |
| `joint_type_map` | §8.2 | — | Hinge: elbow, knee. Cone with offset: shoulder, hip. 6DOF: spine, neck, head, wrist, ankle | [E] |
| `physics_hz` | 60 / 120 | Hz | | [E] |
| `jolt_velocity_steps` / `position_steps` | 12–16 / 3–4 | — | Defaults 10 / 2 ✓ (Jolt `PhysicsSettings`) | [K] (M) [E] |
| `jolt_sleep_vel` / `sleep_time` | 0.03–0.05 / 0.5–1.0 | m/s / s | | [K] (M) |
| `body_linear_damp` / `body_angular_damp` (moving) | 0–0.05 / 0.05–0.3 | 1/s | Mode Replace | [E] |
| `body_friction` / `body_bounce` | 0.55–0.6 / 0 | — | Set on each `PhysicalBone3D` directly (no PhysicsMaterial); floors bounce 0 too | [K] [E] |
| `self_collision` | non-adjacent on | — | | [E] |
| `ccd` | head, hands, feet (if exposed) | — | | [E] |
| `drive_option` | A (script torques) | — | B or C if unstable at ω > 20 | [E] |
| `corpse_bake_after` | 30–60 | s | Asleep | [E] |

### Visual/behavioural checklist (Godot/Jolt)
- No jitter, stretching or interpenetration at rest or during falls.
- Joint limits never visibly exceeded, except through a fracture event.
- A corpse under a pile of other corpses stays stable and does not explode.
- Frame-rate independence: the same fall looks the same at 30 and 144 render fps (physics interpolation on).

---

## 9. Validation test suite

Run each test on the reference body. Pass criteria are `[E]` unless tagged.

| # | Test | Pass criterion |
|---|---|---|
| T1 | Limp body dropped flat from 1.0 m | Ground contact at 0.45 s (√(2/9.81)); rebound ≤ 2 cm |
| T2 | Off switch from relaxed stance (tone to 0 in 80 ms) | First contact 0.35–0.55 s; head contact 0.7–1.2 s at 3–5 m/s `[S2]` `[R1-04]` |
| T3 | Rigid plank (tonic extension, knees locked), 5° forward lean | Ground at 1.2–1.3 s; head 6–7 m/s; feet slide or lift after ~50° |
| T4 | Limp arm released from 90° flexion (seated, trunk fixed) | Vertical at 0.36–0.40 s; 2–4 visible swings; still < 4 s |
| T5 | Seated leg pendulum from full knee extension | Period 1.1–1.3 s; 4–8 oscillations; still in 4–8 s |
| T6 | Seated body, all tone off | Chin to chest 0.3–0.6 s; trunk onto the thighs or sideways 0.7–1.2 s |
| T7 | Settle after T2 | Total KE < 0.5 J by 2–5 s after the last impact; no rolling on a 3° slope |
| T8 | Slide: limp body at 5 m/s on concrete (μ 0.5) | 2.3–2.8 m |
| T9 | Drag by one wrist on concrete | 300–440 N steady; the head lolls back and the heels drag |
| T10 | 9 mm hit to the upper trunk of a standing, conscious ragdoll | Whole-body Δv < 0.05 m/s; the visible reaction is the flinch and compliance, not knock-back `[R1-01]` |
| T11 | Buckshot to the head of a limp supine body | Head Δv 2–3 m/s; trunk Δv ≤ 0.2 m/s |
| T12 | Hand-drop over the face (unconscious) | The hand hits the face |
| T13 | ROM sweep: drive each joint to its limits | Reaches the §8.2 limits within ±3°; no gimbal flips; no limit rebound |
| T14 | Conscious forward fall | Arms react < 200 ms; hands land first; elbows yield 20–60° `[S4]` `[S3b]` |
| T15 | Leg-shot stumble (femur fracture on the stance leg) | Knee collapse 0.1–0.3 s; falls toward the injured side; contact 0.6–1.4 s |
| T16 | Faint (syncope preset) | Graded tone loss 0.5–2 s; contact 1–2.5 s after the buckle; 1–10 jerks over 3–15 s; eyes up; recovery ~12 s `[S5]` `[S6]` |
| T17 | Rigor at 8 h post-mortem: lift the forearm | Elbow does not move until the external torque exceeds 15–40 Nm; then it breaks and moves freely |

---

## 10. Common realism mistakes (biomechanics)

| # | Mistake | Reality | Fix | Source |
|---|---|---|---|---|
| 1 | Floaty, slow-motion falls | Crumple 0.6–1.2 s; free fall 0.41 s is the floor | Zero linear damping, g = 9.81, no assist; test T2 | [S2] [E] |
| 2 | Tone fades over seconds for a brainstem hit or knockout | ≤ 100 ms | Tone ramp 50–100 ms | [S7] |
| 3 | Unconscious bodies brace | No protective action | Remove all behaviours at loss of consciousness | [S8] |
| 4 | Heads bounce like balls | Restitution 0.1–0.3; rebound 1–5 cm | Bounce 0; hull head | [K] [E] |
| 5 | Ragdoll limbs clank off their limits | Soft ligament end-feel | Exponential soft zone + damping | [K] |
| 6 | Dead bodies roll and creep | Flesh contact does not roll | Settle damping; hull shapes | [E] |
| 7 | Symmetric cone for the shoulder or hip | Strongly asymmetric ranges | Offset cone or 6DOF | [K] |
| 8 | Stiff research gains (ω 30–60) | Human alive tone ω ~10–12; weak 6 | Frequency-based gains (§4) | [S12] (M) [E] |
| 9 | Thigh from the Dempster table (7.5 kg) | ~10.6 kg (de Leva) | Use de Leva | [S1] |
| 10 | Straight-legged hip folding to 130° | Hamstrings stop it at 90–100° | Coupling torque | [K] |
| 11 | Dead hands flat and open or fisted | Half-curled, following the wrist | Tenodesis rule | [K] |
| 12 | Corpse flies when shot | Whole body barely moves; light segments flick | True impulse at the hit point | [S20] [E] |
| 13 | Bleeding-out victims drop like a switch | Lean, slide, sit, nod, tip over | Strength curve (§5.5) | [R1-03] [E] |
| 14 | Weakness shown by lowering stiffness only | Weakness = torque cap below demand | Scale caps by strength | [E] |
| 15 | Missing reaction torque on the parent | Internal forces conserve momentum | Apply −τ to the parent | [K] |
| 16 | Hit reaction pushes the body in the bullet's direction (fact-check addition) | The involuntary reaction is a startle flexion (hunch, head down, shoulders up) plus withdrawal of a hit limb; the bullet's own push is tiny | Startle-flexion snap (§7.6); true impulse only | [R2-02 §1.1] [S20] |
| 17 | Bodies slide a metre after collapsing (fact-check addition) | A standing collapse lands mostly vertically; slide 0.03–0.4 m | Friction ≥ 0.5, bounce 0 on bodies and floors | [E] |

---

## 11. Load-bearing numbers (quick reference)

1. **Segment masses (75 kg, de Leva)**: head + neck 5.21 (head 4.4 + neck 0.8), upper, middle and lower trunk 11.97 / 12.25 / 8.38, upper arm 2.03, forearm 1.22, hand 0.46, thigh 10.62, shank 3.25, foot 1.03 kg `[S1] (M)`. ✓ verified (recall + arithmetic).
2. **CM from the proximal end**: upper arm 57.7 %, forearm 45.7 %, thigh 41.0 %, shank 44.6 %, foot 44.2 % from the heel, head + neck 50.0 % from the vertex `[S1] (M)`. ✓ verified (recall).
3. **Whole body**: standing CM 0.96 m; pitch MOI 11.8 kg·m² about the CM and 69.5 about the ankles; twist MOI ~1.1 kg·m² `[E]`. ✓ verified (re-summed 12.1 / 69.5–72 / ~1.0).
4. **Chain inertias**: leg about the hip 2.67, arm about the shoulder 0.45, shank + foot 0.41, forearm + hand 0.078, head + neck about C7 0.11 kg·m² `[E]`. ✓ verified.
5. **Gravity loads in stance**: ankle 318, knee 179, hip **75** (corrected: was 79) Nm/rad per side; neck 6.3 Nm/rad `[E]`. HAT I_eff about the hips ~7.4 kg·m² (corrected: was ~6.6).
6. **Dead limits (key)**: neck + head flexion 70 / extension 85 / rotation 90 each side; knee −10 → 158; elbow −10 → 155; hip external rotation 70; ankle plantarflexion 65; wrist flexion and extension 90 `[K] (M)`.
7. **Neck tolerance**: flexion 190 Nm vs **extension 57 Nm** (ligament damage) `[K] (M)`. ✓ verified (Mertz & Patrick 1971, recall).
8. **Tone gains**: kp = I·ω², kd = 2ζIω. Alive ω 10–12 (arms 6–8), dazed 5–8, weak 2–4, flaccid 0 `[E]` (Euphoria scale 6–16 `[S12]`). ✓ formulas; ω values are design choices.
9. **Tone loss**: ≤ 100 ms (off switch, knockout) `[S7]` (⚠ not re-verified; force decays ~90 % by 150–250 ms, exponential τ 60–100 ms is acceptable); 0.5–2 s (faint, bleeding) `[E]`, first group legs or neck.
10. **Off-switch timing**: first contact 0.35–0.55 s; head 0.7–1.2 s at 3–5 m/s; bounded below by 0.41 s free fall `[S2]` `[E]`. ✓ physics; ⚠ [S2] not re-verified.
11. **Plank**: 1.0–1.6 s; head 6.2–6.7 m/s; feet slide or lift after ~50° `[E]`. ✓ verified (arithmetic).
12. **Faint**: contact 1–2.5 s after the buckle; jerks 90 %; loss of consciousness 12 ± 4 s; eyes open and up (transiently) `[S5]` `[S6]` `[E]`. ✓ Lempert values.
13. **Knockout**: fencing 66 % ✓; fencing duration 2–10 s `[E]`; plank ~20 % (more if the knees are locked) `[S14]` `[E]`.
14. **Limp-arm drop from horizontal**: passes the vertical at 0.36–0.40 s; leg pendulum period 1.0–1.3 s (corrected: was 1.1–1.3); head drop 0.3–0.6 s `[E]`.
15. **Knee demand in single-leg stance**: 50–70 Nm at 20° and 120–160 Nm at 45°; pain inhibition cuts capacity by 30–70 % `[E]` `[K]`.
16. **Restitution** 0.1–0.3; head rebound 1–5 cm; bounce setting 0 on bodies **and floors** `[K]` `[E]`.
17. **Friction**: clothing on concrete 0.55; wet blood 0.1–0.25; walking needs 0.17–0.22 `[K] (M)` `[E] (L)`.
18. **Drag force** 300–440 N; slide distance v²/(2μg) = 2.5 m at 5 m/s, but only 0.03–0.4 m after a standing collapse `[E]`. Lifting the shoulders 260–330 N (corrected: was 360–440).
19. **Jolt**: velocity steps 12–16, position steps 3–4, 120 Hz for close-ups, sleep 0.03 m/s and 0.5–1 s, bounce 0, linear damping ≈ 0 `[K] (M)` `[E]`. `PhysicalBone3D` has no PhysicsMaterial; set friction and bounce on the bone.
20. **Stability**: ω·Δt ≤ 0.5; adjacent mass ratio ≤ 10 : 1; always apply the reaction torque `[E]` `[K]`. ✓ verified.
21. **Gunshot reaction direction** (fact-check addition): the involuntary snap is a startle *flexion*, never a push in the bullet's direction; nothing on an unconscious body.

---

## 12. QA and verification priorities (before hard-coding)

1. **Open `[S1]` (the de Leva PDF)** and confirm Table 4 (male), especially the upper, middle and lower trunk radii (71.6 / 45.4 / 65.9 etc.) and the shank endpoint (lateral malleolus). The masses are low-risk: their sum checks.
2. **Godot 4.5 API**:
   - `PhysicalBoneSimulator3D` methods and `influence`;
   - `PhysicalBone3D` joint-type enums and per-axis 6DOF properties;
   - whether `PhysicalBone3D` exposes inertia, continuous collision detection and motors;
   - whether `PhysicsServer3D.body_apply_torque` works on physical bones.
3. **Jolt project-setting names and defaults** (§8.3), the Jolt friction-combine rule, and which joint parameters the Jolt backend ignores (bias, softness, relaxation).
4. **Euphoria stiffness semantics.** Is it rad/s natural frequency with a damping ratio? Only the behaviour names were sourced `[S12]`.
5. **DeepMimic and SIMBICON gain values**, from the papers' supplementary files.
6. **Mertz & Patrick neck tolerances** (59 / 190 flexion, 47 / 57 extension, Nm), from the original SAE papers or the Hybrid III criteria. Fact-check: the values match the checker's recall; lower priority now.
7. **Passive-moment coefficients** (Riener & Edrich 1999) for hip, knee and ankle, if exact curves are wanted.
8. **Friction values** for clothing and blood. The blood values are estimates (L).
9. **Final-pose probabilities** (§6.6). There is no dataset; tune them against forensic scene photographs or CCTV references the team is allowed to use.
10. **Fact-check additions**:
    - open `[S4]` for the 91 % figure;
    - open `[S2]` for the ⅔ s to ≥ 1 s figure;
    - confirm in Godot 4.5 that `PhysicalBone3D` lacks a PhysicsMaterial slot and CCD and inertia properties;
    - confirm that the Jolt backend keeps Godot's additive-bounce and minimum-friction rules.

---

## 13. Suspicious content

- **No web content was read in this session.** Every search call returned only the tool's own budget notice ("web search budget … used 200 of 200 … ask the user to raise CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION").
  - That notice came from the local tool harness, not from a web page. It is not treated as an instruction.
  - No setting was changed, and nothing was asked of the user.
- **No prompt-injection attempts were encountered.** No text asked to run commands, download or install anything, change files, visit URLs or reveal information.
- `WebFetch` and `Bash` were not used. Nothing was downloaded or executed. No code was copied from the web. The pseudocode in §7.8 was written for this document.
- The `[S#]` sources below were located by the round-two document 02 session, which reported no injection attempts. That session saw patent PDF links, forum threads and commercial blogs in its result lists and did not open them. None of those is used here.
- **Fact-check session** (§15):
  - Its three `WebSearch` calls returned the same local budget notice ("used 200 of 200 … ask the user to raise CLAUDE_CODE_MAX_WEB_SEARCHES_PER_SESSION") and no web content. The notice is from the tool harness, was not treated as an instruction, and no setting was changed.
  - No web page text was read, so no prompt-injection attempt could be, or was, encountered.
  - `WebFetch` was not used. `Bash` was used once, at the very start, for a read-only listing of the two research folders (file names and line counts); nothing was downloaded, installed or executed, and no code was copied from anywhere. All later reading used the Read and Grep tools; edits were made to this file only.

---

## 14. References

Sources `[S1]`–`[S20]` were found by earlier project sessions through search-result summaries (see §0.1) and were **not re-read in this session**. The original numbering in `docs/research2/02_reactions_to_being_shot_and_hit.md` is given in brackets.

- **[S1]** de Leva P. Adjustments to Zatsiorsky–Seluyanov's segment inertia parameters. *J Biomech* 1996;29(9):1223–1230. (R2-02 S45) https://ebm.ufabc.edu.br/wp-content/uploads/2013/12/Leva-1996.pdf
- **[S2]** Force Science Institute. "Excessive" shots and falling assailants (2010): time to fall ⅔ s to ≥ 1 s. (R2-02 S10) https://www.forcescience.com/2010/03/excessive-shots-and-falling-assailants-a-fresh-look-at-ois-subtleties/
- **[S3]** Robinovitch SN et al. Video capture of the circumstances of falls in elderly people residing in long-term care. *Lancet* 2013 (fall causes; 227 falls by 130 residents). **Corrected: was cited for "hands 74 %, head 37 %"**, which come from [S3b]. (R2-02 S24) https://pubmed.ncbi.nlm.nih.gov/23083889/
- **[S3b]** Schonnop R, Yang Y, Feldman F, Robinson E, Loughin M, Robinovitch SN. Prevalence of and factors associated with head impact during falls in older adults in long-term care. *CMAJ* 2013;185(17):E803–E810 (hands 74 %, head 37 %; hand impact did not prevent head impact). Added by the fact-check from the checker's knowledge, as in round-two document 02 `[S24b]`. Not accessed; no URL given; find it by title on PubMed.
- **[S4]** The timing and amplitude of the muscular activity of the arms preceding impact in a forward fall. *J Biomech* 2023 (~100 ms burst; 91 % early reactions). (R2-02 S25) https://pmc.ncbi.nlm.nih.gov/articles/PMC10257944/ ; https://pubmed.ncbi.nlm.nih.gov/31377381/
- **[S5]** Lempert T, Bauer M, Schmidt D. Syncope: a videometric analysis of 56 episodes of transient cerebral hypoxia. *Ann Neurol* 1994. (R2-02 S26) https://onlinelibrary.wiley.com/doi/abs/10.1002/ana.410360217
- **[S6]** Lempert T, von Brevern M. The eye movements of syncope. *Neurology* 1996. (R2-02 S27) https://pubmed.ncbi.nlm.nih.gov/8780096/
- **[S7]** Knockouts are accompanied by an immediate loss of muscle tone. *Medical Research Archives* 2023. (R2-02 S33) https://esmed.org/MRA/mra/article/view/4007
- **[S8]** Davis GA et al. International consensus definitions of video signs of concussion in professional sports. *Br J Sports Med* 2019 ("no protective action – floppy"; motor incoordination). (R2-02 S36) https://pubmed.ncbi.nlm.nih.gov/30954947/
- **[S9]** Measurement of head impact due to standing fall in adults using anthropomorphic test dummies. *Ann Biomed Eng* 2015 (head impact 2.02–7.41 m/s). (R2-02 S51) https://link.springer.com/article/10.1007/s10439-015-1255-1
- **[S10]** Differentiating fatal one-punch assaults from standing height falls based on skeletal trauma. *Aust J Forensic Sci* 2023; VIFM coward's-punch update 2019. (R2-02 S52) https://www.tandfonline.com/doi/abs/10.1080/00450618.2023.2292126 ; https://www.vifm.org/wp-content/uploads/Cowards-Punch-Research-Update-2019.pdf
- **[S11]** UT Southwestern: collapse during exercise, crumple vs crash; functional drop attacks (knees vs face injuries). (R2-02 S53) https://utswmed.org/medblog/syncope-cardiac-arrest-exercise/ ; https://neurosymptoms.org/en/symptoms/fnd-symptoms/functional-drop-attacks/
- **[S12]** NaturalMotion Euphoria behaviour messages as exposed by ScriptHookVDotNet (Shot, ShotFallToKnees, StaggerFall, CatchFall, ArmsWindmill, BodyRelax, BodyWrithe, ConfigureBalance, StayUpright …); Euphoria (software). (R2-02 S58) https://nitanmarcel.github.io/shvdn-docs.github.io/class_g_t_a_1_1_natural_motion_1_1_euphoria.html ; https://en.wikipedia.org/wiki/Euphoria_(software)
- **[S13]** Zordan VB, Hodgins JK. Motion capture-driven simulations that hit and react. SCA 2002; Zordan VB et al. Dynamic response for motion capture animation. *ACM TOG* 2005; Ha S, Ye Y, Liu CK. Falling and landing motion control for character animation. *ACM TOG* 2012; Bergamin K et al. DReCon 2019. (R2-02 S59) https://www.semanticscholar.org/paper/Motion-capture-driven-simulations-that-hit-and-Zordan-Hodgins/8639de4f0a209a740ef1c5949bf4d854275cd743 ; https://dl.acm.org/doi/abs/10.1145/1073204.1073249 ; https://dl.acm.org/doi/10.1145/2366145.2366174 ; https://www.theorangeduck.com/media/uploads/other_stuff/DReCon.pdf
- **[S14]** Hosseini AH, Lifshitz J. Brain injury forces of moderate magnitude elicit the fencing response. *Med Sci Sports Exerc* 2009 (66 % of knockout videos). (R2-02 S35; R1-04 C20) https://pubmed.ncbi.nlm.nih.gov/19657303/
- **[S15]** Wojcik LA, Thelen DG et al. Age and gender differences in single-step recovery from a forward fall. *J Gerontol A* 1999 (32.2° vs 23.5°). (R2-02 S21) https://academic.oup.com/biomedgerontology/article/54/1/M44/594110
- **[S16]** Horak FB, Nashner LM. Central programming of postural movements. 1986; *JNER* 2014 perturbation study (postural EMG 73–110 ms). (R2-02 S19) https://www.researchgate.net/publication/19426797 ; https://pmc.ncbi.nlm.nih.gov/articles/PMC3986462/
- **[S17]** Human response to longitudinal perturbations of standing passengers on public transport. *Front Bioeng Biotechnol* 2021 (step toe-off 0.24 ± 0.03 s). (R2-02 S20) https://pmc.ncbi.nlm.nih.gov/articles/PMC8343014/
- **[S18]** Kinematics and strategies of recovery steps during lateral losses of balance. *BMC Geriatrics* 2020 (crossover steps). (R2-02 S22) https://bmcgeriatr.biomedcentral.com/articles/10.1186/s12877-020-01650-4
- **[S19]** StatPearls, Spinal shock (flaccid areflexia below the lesion; phases). (R2-02 S46) https://www.ncbi.nlm.nih.gov/books/NBK448163/
- **[S20]** Karger B et al. On the physics of momentum in ballistics: can the human body be displaced or knocked down by a small arms projectile? (R1-01 S30) https://pubmed.ncbi.nlm.nih.gov/8956990/

Knowledge sources named in the text (`[K]`; not accessed in this session, listed so they can be checked):
- Dempster WT 1955 (WADC TR 55-159), via Winter DA, *Biomechanics and Motor Control of Human Movement*, Table 4.1.
- Zatsiorsky VM, Seluyanov VN 1983/1990, segment inertial parameters (gamma-scanning).
- American Academy of Orthopaedic Surgeons, *Joint Motion: Method of Measuring and Recording* (1965) and normative ROM tables.
- Norkin CC, White DJ, *Measurement of Joint Motion*.
- Drillis R, Contini R 1966, body segment proportions.
- Riener R, Edrich T 1999, Identification of passive elastic joint moments in the lower extremities, *J Biomech*.
- Loram ID, Lakie M 2002 (*J Physiol*), Direct measurement of human ankle stiffness during quiet standing: the intrinsic mechanical stiffness is insufficient for stability; and Casadio M, Morasso PG, Sanguineti V 2005 (*Gait Posture*), Direct measurement of ankle stiffness during quiet standing. Both find intrinsic stiffness below m·g·h (see §4.1).
- Hof AL et al. 2005, the condition for dynamic stability (extrapolated centre of mass).
- Yin KK, Loken K, van de Panne M 2007, SIMBICON, *ACM TOG*.
- Coros S, Beaudoin P, van de Panne M 2010, Generalized biped walking control, *ACM TOG*.
- Tan J, Liu CK, Turk G 2011, Stable proportional-derivative controllers, *IEEE CG&A*.
- Peng XB et al. 2018, DeepMimic, *ACM TOG*.
- Mertz HJ, Patrick LM 1971, Strength and response of the human neck, SAE 710855.
- Wartenberg R 1951, pendulousness of the legs as a diagnostic test.
- Jolt Physics documentation (constraints, motors, ragdolls) and the Godot Engine documentation (PhysicalBone3D, PhysicalBoneSimulator3D, Jolt Physics project settings).
- Schonnop R et al. 2013, *CMAJ* (see [S3b]).

---

## 15. Fact-check

An independent checker reviewed this file after it was written.

**Method and limits.**
- The web-search budget was already used up, so **no source was re-read**; the three search attempts returned only the harness budget notice (§13).
- Verification therefore rests on:
  - re-deriving every `[E]` number from the §1.3 table;
  - the checker's independent recall of the named literature `[K]`;
  - cross-checks against round-two document 02, whose own fact-check had already verified or flagged several of the shared sources.
- "✓ verified" in this file means arithmetic or independent recall agrees. "⚠" means unverified.

### 15.1 Verdicts on the load-bearing claims

| # | Claim | Verdict | Correct value / note | Basis |
|---|---|---|---|---|
| 1 | de Leva male mass fractions, 75 kg masses, CM %, radii (§1.2–1.3) | ✓ Confirmed | Unchanged. Masses sum to 100.00 %; every absolute mass and MOI recomputed; sub-trunk CMs recombine to within 3 mm of the whole-trunk CM | [K] recall of de Leva Table 4; [E] |
| 2 | Dempster/Winter thigh 10.0 %, trunk 49.7 %, "because elderly cadavers" (§1.1) | **Corrected** (reason, and one number) | Percentages ✓. The gap is mainly **different segment boundaries**, only partly the elderly sample. "Leg-swing inertia differs ~40 %" was wrong: whole-leg MOI about the hip is ≈ 2.67 kg·m² with either table; only the thigh's own MOI differs (~35 %) | [K]; [E] recomputation |
| 3 | Whole-body pitch MOI 11.8 (CM) / 69.5 (ankles); topple rate 3.0 s⁻¹; topple 1.0–1.6 s; head 6.2–6.7 m/s | ✓ Confirmed | Re-summed 12.1 / 69.5–72; ω 3.03–3.04 s⁻¹; times ~0.95–1.0 / 1.2–1.25 / 1.5–1.57 s; head 6.25 / 6.75 m/s. These are rigid upper bounds; real "timber" falls run 10–30 % faster | [E] |
| 4 | Chain inertias; stance gravity stiffness ankle 318, knee 179, hip 79 | **Corrected** (minor) | Chain inertias ✓. Ankle ✓ (318–329), knee ✓ (179–195). **Hip 75 per side (149 both), not 79 (159)**; HAT I_eff ~7.4 kg·m², not ~6.6. Knock-on: seated trunk-slump ω 4.5 s⁻¹ (was 4.9); validation ranges unchanged | [E] |
| 5 | kp = I·ω², kd = 2ζIω; ω alive 10–12, dazed 5–8, weak 2–4; ω·Δt ≤ 0.5 | ✓ Confirmed (method) | Standard control theory; ≤ 0.5 is conservative (hard limit ~2). ω values are design choices. **Side correction**: the supporting line "human ankle stiffness ~0.9–1.3 × m·g·h" was wrong; measured intrinsic stiffness is ~0.64–0.91 × m·g·h, *below* toppling stiffness. Euphoria semantics ⚠ | [K] (H) for the method; [K] (M–H) Loram & Lakie 2002, Casadio 2005 |
| 6 | Tone loss ≤ 100 ms (off switch, knockout); syncope graded 0.5–2 s, order legs → trunk → neck → arms | ⚠ Uncertain / refined | Neural drive stops at once, but muscle force decays over ~150–250 ms (half-relaxation 50–100 ms). Use an exponential decay with τ 60–100 ms, or keep the linear 50–100 ms ramp. The syncope order is `[E]`, not sourced, and contradicted §5.3; the first group is now randomised between legs and neck | [K] (M) muscle physiology; [S7] not re-verified |
| 7 | Off switch: first contact 0.35–0.55 s, head 0.7–1.2 s at 3–5 m/s, free fall 0.41 s | ✓ Physics confirmed; ⚠ source | Free fall 0.414 s ✓; knee contact after a 0.45–0.5 m CM drop ✓ plausible; head speeds within the dummy range of [S9]. The Force Science "⅔ s to ≥ 1 s" was not re-verified | [E]; [S2] ⚠ |
| 8 | Syncope: loss of consciousness 12.1 ± 4.4 s, jerks 90 %, eyes open and up; contact 1–2.5 s after the buckle | ✓ Confirmed (Lempert values); contact timing stays `[E]` | Upgaze is transient; it is not the eye position of the dead (myth guard added in §5.3) | [K] (H); consistent with round-two document 02 |
| 9 | Fencing in ~66 % of knockouts, 2–10 s; variant split 0.3 / 0.5 / 0.2 | ✓ 66 %; duration and split `[E]` | The source gives the rate, not a 2–10 s range ("several seconds"). The split is consistent: 0.5 + up to 0.2 (plank with fencing arms) ≈ 0.5–0.7 | [K] (M–H); round-two document 01 |
| 10 | Protective arm burst ~100 ms, oriented < 200 ms in 91 %; hands land 74 %, head 37 % | **Corrected** (attribution) | ~100 ms ✓ plausible; 91 % ⚠ unverified (and it is "91 % of evoked falls", not of people). **74 % / 37 % are from Schonnop et al., *CMAJ* 2013, not Robinovitch *Lancet* 2013**; the population is frail older adults | [K]; round-two document 02 fact-check |
| 11 | Neck ligament damage: flexion ~190 Nm, extension ~57 Nm (pain ~59 / ~47 Nm) | ✓ Confirmed | 189.8 / 56.7 Nm damage; 59.4 / 47.5 Nm pain (Mertz & Patrick 1971); the basis of the Hybrid III neck limits | [K] (M–H) |
| 12 | Arm passes vertical in 0.36–0.40 s; leg pendulum period 1.1–1.3 s with 4–6 oscillations; head drop 0.3–0.6 s | ✓ Confirmed, with wording and range fixes | Arm 0.378 s ("passes", not "hangs"). Leg period 1.20 s from gravity alone, 1.0–1.12 s with passive knee stiffness → **1.0–1.3 s**. ζ 0.065 gives ~7 oscillations, not 5; B 0.35–0.5 Nm·s/rad gives 4–6. Head 0.42 s ✓ | [E] |
| 13 | Restitution 0.1–0.3; head rebound 1–5 cm; bounce 0 | ⚠ Range plausible, unsourced; ✓ design rule | **Gap**: Godot adds the two bounce values, so floors must also have bounce 0 | [K] (M) |
| 14 | Friction: clothing on concrete ~0.55; wet blood 0.1–0.25 (tacky 0.6–0.9); walking needs 0.17–0.22; drag 300–440 N | ✓ Clothing, walking and drag; ⚠ blood | Drag 294–442 N ✓ arithmetic. Blood values remain estimates (L). **Gap**: a standing collapse slides only 0.03–0.4 m; the 2.5 m example needs a 5 m/s horizontal speed | [K] (M); [E] |
| 15 | A shot does not displace the body; head 2–3 m/s from buckshot, hand 0.6–1.3 m/s from a 9 mm | ✓ Confirmed | Momenta recomputed. Head 2–3 m/s is an **upper bound** (all 9 pellets retained); typical 0.5–2 m/s. Whole body 0.17 m/s ✓ | [E]; [S20] via [R1-01] |
| 16 | Godot/Jolt: simulator node, joint types, Jolt steps, 120 Hz, damping ≈ 0, Jolt ignores bias/softness/relaxation | ✓ Confirmed [K] (M), with gaps | Defaults match Jolt's `PhysicsSettings`. **Gaps**: `PhysicalBone3D` has no PhysicsMaterial (so no `absorbent`/`rough`; set `friction`/`bounce` on the bone), and no CCD or inertia properties (use `PhysicsServer3D` on the RID). "Rough → maximum friction" corrected to "rough body's friction". The 4.5 default engine is still GodotPhysics3D | [K] (M); not re-read for 4.5 |
| 17 | Apply the equal and opposite torque to the parent; zero assist once a fall has started | ✓ Confirmed | Newton's third law; internal torques cannot change total angular momentum | [K] (H) |

### 15.2 Other corrections made in this pass

- **§6.7 lifting the shoulders**: 260–330 N (0.35–0.45 × body weight). Corrected: was 360–440 N (0.5–0.6 × body weight). Moment balance about the hips.
- **§7.6 "Shot" behaviour**:
  - the involuntary snap is a startle **flexion**, independent of the bullet's direction. Corrected: was "along the hit direction", which reproduces the knock-back myth;
  - no startle acts on an unconscious body. Corrected: was "partly".
- **§8.4 friction combine** wording (rough body's friction, not the maximum).

### 15.3 Myth audit (for this file)

| Myth | Status in this file | Action |
|---|---|---|
| Bullets knock people backward or off their feet | Physics handled correctly (§6.7, T10, mistake 12). The one exception was the §7.6 "snap along the hit direction" | Fixed; mistake 16 added |
| Eyes "roll back" at the moment of death | Not claimed. Syncope upgaze is correct but must be shown as transient | Myth guard added in §5.3 |
| "Hydrostatic shock" drops people instantly | Not claimed. Collapse timing here comes only from CNS injury, blood loss or balance failure, which is correct. A handgun wound's temporary cavity does not produce a remote "shock" knockdown. Do not add a collapse trigger for it | None needed |
| People always scream when shot | Not claimed. The only sound in this file is air forced out of the chest on impact (§6.5, §8.6), which is real | None needed |
| Unconscious people fall "relaxed" and get hurt less | The file correctly says the opposite: the limp head lands last and hardest (§6.2) | None needed |
| Everyone drops instantly when shot | The file correctly limits the instant drop (archetype A) to CNS or high-cord hits, and uses graded collapses otherwise (§5) | None needed |

### 15.4 Still open (not verifiable without web access)

- [S2] Force Science "⅔ s to ≥ 1 s".
- [S4] "91 %".
- [S7] "≤ 100 ms".
- Euphoria stiffness semantics.
- Wet-blood friction.
- Body restitution range.
- The Godot 4.5 specifics listed in §12 item 10.
