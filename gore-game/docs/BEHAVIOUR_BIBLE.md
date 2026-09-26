# Gore Head — Behaviour Bible (implementation spec for everything the body does)

> Audio removed by the user; the game has no sound. Audio sections below were deleted or reworded to visuals.
> **Visual reference notes:** also apply `gore-game/docs/REFERENCE_NOTES.md` (generic properties of real wounds and blood from forensic reference photos: far more blood coverage, soaked cloth, big dark lumpy pools, shredded irregular wet tissue with clots and strands, varied colours). A clean, dry, uniform or blood-sparse wound fails review like a sticker does.


Project: **Gore Head**. Godot 4.5 (Forward+, GDScript + Godot shaders, built-in Jolt), Skeleton3D + PhysicalBone3D ragdoll, procedurally generated full adult body. The subject is fictional and procedurally generated. No real person is modelled.
Status: v1.0, 2026-09-26.
Audience: simulation, animation/ragdoll, AI/behaviour, eye/face and shader/VFX engineers, plus the reviewers who test the game against §9.

**Scope.** This document specifies what the body **does**:
- the neuro model and its deficits (§1);
- the eyes and face (§2);
- reactions to being hit (§3);
- falls and the ragdoll (§4);
- involuntary movement (§5);
- the look of severe trauma (§6);
- §7 (sound) removed: the game has no sound;
- eight second-by-second scenario scripts (§8);
- a reviewer test list (§9);
- appendices: conflict register (A), key references (B), suspicious content (C).

`docs/REALISM_BIBLE.md` (RB) remains the specification for wounds, blood and circulation, the physiology state machine, post-mortem changes and anatomy. This document **reads** the physiology state of RB §4 and turns it into motion, eyes and face. Where the two documents give different values, Appendix A records the conflict and the value chosen.

---

## 0. How to use this document

### 0.1 Source keys and evidence tags

| Key | File |
|---|---|
| R1-01 … R1-06 | `docs/research/01_gunshot_wounds.md` … `06_game_gore_tech.md` |
| R2-01 | `docs/research2/01_brain_injury_deficits.md` |
| R2-02 | `docs/research2/02_reactions_to_being_shot_and_hit.md` |
| R2-03 | `docs/research2/03_falling_ragdoll_biomechanics.md` |
| R2-04 | `docs/research2/04_agonal_involuntary_movement.md` |
| R2-05 | `docs/research2/05_severe_trauma_morphology.md` |
| R2-06 | `docs/research2/06_sounds_voice_face.md` |
| RB | `docs/REALISM_BIBLE.md` |

Every value carries one of these tags:

| Tag | Meaning | How to treat it |
|---|---|---|
| `[S]` | Found by web search in a round-two research session (search-summary level). Written `[S R2-0x:S#]`. The URL is in that file's reference list; the load-bearing ones are repeated in Appendix B | Default value. QA opens the source before the number is shown to the player as a measurement |
| `[K]` | Standard clinical, physiological or physical knowledge, confirmed by the independent fact-check of the research file (✓ there) | Default value |
| `[K⚠]` | Knowledge the fact-check could not re-verify | Default value, tune, on the QA list |
| `[E]` | Engineering estimate or derivation; the arithmetic is in the cited file or here | Tune in engine |
| `[G]` | Game-design choice inside the real range | Tune freely inside the range |

Confidence (H)/(M)/(L) is added where it matters. `R2-0x §y` after a tag names the section the value comes from.

### 0.2 Method and limits

- **Inputs.** This synthesis read all six round-two files, round-one file R1-04 and RB (§1, §4, §5, §6, §7.2) in full or by section.
- **Web access.** One WebSearch was attempted in this pass (Godot 4.5 `PhysicalBoneSimulator3D` API). The harness refused it because the session's shared search budget (200/200) was already used. No WebFetch, no Bash, nothing downloaded or executed.
- **Consequence.** No value here is newly sourced. Each number is exactly as reliable as the fact-checked research file it comes from. The research fact-checks also had no web access, so "✓" means re-derived arithmetic or independent recall, not a re-read paper.
- **Engine API caveat.** Godot/Jolt API names are `[K]` from R2-03 §8 and RB §4.10 (RB checked them against the Godot 4.5-stable source). Where the two disagree, RB wins (Appendix A, C-12).

### 0.3 Conventions

- **Reference body**: male, 75 kg, 1.75 m (round two).
  - RB anatomy uses 1.78 m (C-14). Scale lengths by stature / 1.75 and masses by segment fractions (§4.1).
  - Standing centre of mass (CM) 0.96 m. Inverted-pendulum constant ω₀ = √(9.81 / 0.96) = **3.20 s⁻¹** `[E]`.
- **Frames**:
  - Body frame: +Z up, face −Y, character's left = +X (RB §1.2).
  - Head frame: origin midway between the ear canals, same axes.
  - Godot: `(x, z, −y)`.
- **Side words** always refer to the character's own body. Ipsilateral = same side as the lesion; contralateral = opposite side.
- **Eye angles**, per eye, in the head frame:
  - yaw positive toward the character's **left**, pitch positive **up**;
  - "toward the lesion" means yaw toward the lesion's side;
  - "in" (adduction) and "out" (abduction) are relative to that eye's nose side.
- **Pupils** in mm at room light (`pupil_base` 3–4 mm). Bright light 2–4 mm, dark 4–8 mm `[K]`. State values below are offsets from, or overrides of, `pupil_base`.
- **Time**:
  - t = 0 is contact (bullet entry, blade contact, fist or hammer contact, flame contact).
  - Times are real seconds unless marked "game".
  - Time bands follow RB §1.3: ACUTE 1× (60 s after any critical event and 60 s either side of cardiac arrest), MINUTES 4×, LONG 15×, POSTMORTEM 120×.
  - **Cosmetic oscillators never speed up**: breathing motion, blinks, saccades, tremor, jerks, gasps and jet pulsing always run in real time.
- **Ticks**:
  - physics 60 Hz (crowds) or 120 Hz (close-ups);
  - decision and physiology 20 Hz;
  - dead bodies 2–5 Hz;
  - eyes and face per rendered frame for on-screen characters.
  - Reflex events (30–150 ms) are scheduled on the physics tick, never skipped or merged `[E] R2-02 §0.3`.
- **Randomness**:
  - Every probability is rolled **once**, on entry to the state, with the per-character seed, so a replay looks identical `[G] R2-04 §0.3`.
  - Per-character traits are rolled at spawn: language dominance (left 0.90), mindset, expressivity, pain-face type, and a per-region severity factor of 0.85–1.15.
- **No sound**: the game has no audio. Vocal behaviour (words, cries, moans, groans, grunts, screams, coughs, gasps) exists only as the mouth, jaw, chest and face movement driven by `vocal_state` and the breathing generators (§2.1, §5.2). Airway problems are shown by the chest, jaw, lips and froth.

### 0.4 System map

```
RB §4 physiology (20 Hz)          ──► NeuroResolver (§1) ── channels ──┐
 V, MAP, CPP, ICP, SpO2, brain O2                                        │
 reserve, cord level, pain, stress                                       ▼
 airway, lungs, t_arr, t_dead      ──► ReactionSelector (§3) ──► MotorMixer (§4) ──► PhysicalBone3D PD torques
                                   ──► InvoluntaryGen (§5)   ──┘        │
                                   ──► EyeFaceController (§2) ──► eye/lid/jaw bones, blendshapes, shader uniforms
 wound records (RB §2)             ──► TraumaVisuals (§6)     ──► SDF wounds, meshes, particles, decals
```

- The behaviour layer **never decides** whether the character lives or dies. It only turns physiology into observable behaviour `[G] R2-04 §0.4`.
- Every generator is **gated by the tissue it needs** (§5.1). This single rule removes most realism errors.

### Simulation parameters (conventions)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `com_height_standing` | 0.96 | m | 0.55 × stature | `[K] R2-02 §0.3` |
| `omega0` | 3.20 | s⁻¹ | √(g / CM height) | `[E]` |
| `physics_hz` | 60 (crowd) / 120 (hero) | Hz | ω·Δt ≤ 0.5 for PD stability | `[E] R2-03 §4.1` |
| `decision_tick` | 20 | Hz | Reflexes run on the physics tick | `[E] R2-02 §11.3` |
| `left_dominant_p` | 0.90 | p | Language hemisphere | `[S R2-01:S14]` (H) |
| `region_severity_factor` | 0.85–1.15 | × | Per character, per region | `[E] R2-01 §20.2` |
| `roll_once_per_state` | true | bool | Seeded; replays identical | `[G]` |

### Visual/behavioural checklist (conventions)
- Nothing visible happens on the impact frame except the small physical impulse and the wound. Every other reaction starts 2–15 frames later.
- Breathing, blinks, saccades and jerks keep real-time speed when the game compresses time.
- Two identical hits on two characters produce visibly different behaviour (traits, mindset, rolls), but the same character replayed produces the same behaviour.

---

## 1. Neuro model

### 1.1 Rules the resolver obeys

1. **Crossing** `[K] (H) R2-01 §0.4 ✓`.
   - Everything above the pyramidal decussation (cortex, internal capsule, basal ganglia, thalamus, midbrain, pons) controls the **opposite** half of the body.
   - The cerebellum controls the **same** side.
   - A brainstem lesion gives **crossed signs**: cranial-nerve deficits (eye, face, tongue) on the lesion side, limb weakness on the other side.
   - Exceptions to encode:
     - a CN IV nucleus or fascicle lesion affects the opposite eye;
     - a CN III nucleus lesion weakens the opposite superior rectus and gives ptosis on both sides;
     - a red-nucleus lesion (midbrain cerebellar outflow) gives opposite-side ataxia;
     - lesions at or below the decussation (lowest medulla, cervical cord) give same-side weakness;
     - a lateral medullary lesion gives crossed **sensory** loss, not crossed weakness.
2. **Consciousness** needs the brainstem reticular activating system, the thalami and at least one working hemisphere `[K] (H) R1-04 §3.1`.
   - A one-sided hemisphere lesion **does not by itself cause coma**.
   - Coma needs bilateral hemispheric, bilateral thalamic or upper-brainstem damage, or mass effect (herniation).
3. **Destroyed tissue fails in the same frame; the rest follows a clock** `[K] R2-01 §0.4`.
   - Concussive (stun) dysfunction around a track lasts seconds to minutes and partly recovers.
   - Bleeding and swelling act over minutes to days (§1.7).
4. **Gaze direction tells the lesion type** `[K] (H) R2-01 §14.1 ✓`:
   - a destroyed hemisphere turns the eyes **toward** the lesion;
   - a seizure focus turns them **away** (forced version only);
   - a destroyed pons turns them **away** from the lesion, toward the paralysed limbs.
5. **Flaccid first** `[K] (H) R2-01 §2.3 ✓`.
   - A fresh central paralysis is limp for hours to weeks; spasticity appears after 1–6 weeks (time skips only).
   - "Flaccid" means **no active drive**. Passive tissue stiffness, joint limits and damping remain, so a paralysed limb never becomes a frictionless rope.
6. **No remote brain effects from body hits** `[K] (M) R2-01 §20.2, R2-02 §14 row 13`. The "hydrostatic shock" myth is excluded: brain stun applies only to tracks inside the skull and to head blows.
7. **Seizures need perfused cortex** `[K] (H) R2-01 §17.1, R2-04 §4.5`.
   - Pure cerebellar, brainstem or deep white-matter lesions never cause epileptic seizures.
   - No seizure starts once cerebral flow has stopped for about 15–30 s.
8. **Consciousness is resolved last** and overrides behaviour. An unconscious character shows only reflexes, posturing, eye signs, involuntary movement and breathing `[E] R2-01 §20.2`.

### 1.2 Region table (engine data file `neuro_regions.csv`)

**Column meanings:**
- `vol`: volume per side, cm³ `[K] (M) R2-01 §20.1`.
- `pos`: position hint in the **head frame**, in mm, for the **left** structure; negate x for the right one. Accuracy is ±10–15 mm `[E] (L)`.
  - Cortical and deep hints were re-mapped from standard atlas coordinates with x_h = −x, y_h = −10 − y, z_h = 38 + z + 0.165·y (a correction for the ~9° tilt of the AC–PC line against the Frankfurt plane).
  - Brainstem and cerebellum hints were placed from skull landmarks: the pontomedullary junction lies roughly in the coronal plane of the ear canals, and the foramen magnum ~20 mm below them.
  - **The authoritative volumes are the procedural brain's labelled sub-meshes.** Use the hints only to seed and validate them.
- `vis / full`: the fraction of the region destroyed or dysfunctional at which the deficit becomes visible, and at which it is complete.
- Severity: `sev = smoothstep(vis, full, d) × region_severity_factor` (§1.3).

| id | vol | pos (x, y, z) | Channel(s) driven | Deficit when destroyed | Body mapping | Onset | vis / full | Extra rolls | Tag |
|---|---|---|---|---|---|---|---|---|---|
| `M1_leg` | 4–6 | (5, 15, 104) | `str_leg`, `str_foot` | Leg and foot weakness to paralysis. A parasagittal or midline hit takes out **both** legs | Contra | 0 s | 0.10 / 0.60 | — | `[K] R2-01 §2` |
| `M1_trunk` | 2–3 | (15, 15, 106) | `str_trunk` × 0.3 | Mild (the trunk is represented on both sides) | Contra | 0 s | 0.10 / 0.60 | — | `[K]` |
| `M1_arm` | 3–5 | (25, 12, 102) | `str_arm` | Shoulder and elbow weakness | Contra | 0 s | 0.10 / 0.60 | — | `[K]` |
| `M1_hand` | 4–6 | (37, 12, 92) | `str_hand` | Hand and finger paralysis; held weapon drops when sev > 0.7 | Contra | 0 s | 0.10 / 0.60 | — | `[S R2-01:S34,S35]` (M) |
| `M1_face` | 2–3 | (55, 0, 66) | `str_face_lower` | Lower-face droop; forehead and eye closure spared (upper face gain 0.7) | Contra | 0 s | 0.10 / 0.60 | — | `[S R2-01:S36]` ✓ |
| `M1_bulbar` | 1–2 | (58, −5, 56) | `str_tongue`, `vocal: DYSARTHRIC_UMN` | Mild dysarthria; the tongue deviates toward the weak side | Contra | 0 s | 0.10 / 0.60 | — | `[K] (M)` |
| `SMA` | 8–12 | (5, −5, 97) | `initiation` | Akinesia: contra 0.5–0.9, ipsi 0.1–0.3; strength kept | Contra > ipsi | 0 s | 0.20 / 0.70 | Mutism p 0.6 if left SMA or cingulate is involved | `[S R2-01:S4]` (M) |
| `PMC` | 10–15 | (40, −10, 88) | `str_proximal` | Proximal weakness (MRC 4); clumsy limb-kinetic apraxia | Contra | 0 s | 0.20 / 0.70 | — | `[K] (M)` |
| `FEF` | 2–4 | (30, −7, 92) | `gaze_bias` | Eyes deviate **toward the lesion** 15–40° (default 25°); head 10–30° | Eyes | 0 s; lasts 2–7 d | 0.30 / 0.70 | — | `[S R2-01:S63,S64]` (M) |
| `PFC_dl` | 40–60 | (42, −40, 73) | `rt_add`, `persev_p` | Slowed, perseverative, impersistent | Bilateral effect | 0 s | unilateral 0.30 / 0.90; bilateral 0.20 / 0.60 | — | `[S R2-01:S7,S8]` |
| `PFC_orb` | 20–30 | (25, −45, 36) | `disinhib`, `anosmia` | Disinhibition, euphoria, no fear | Bilateral effect | 0 s | as `PFC_dl` | — | `[S R2-01:S11]` |
| `ACC` | 5–8 | (5, −35, 67) | `abulia` | Apathy. **Bilateral** sev > 0.5 → akinetic mutism | Global | 0 s | 0.30 / 0.70 | — | `[S R2-01:S9]` (M) |
| `Broca_ext` (dominant side; includes insula and white matter) | 5–10 | (48, −28, 51) | `vocal: NONFLUENT` | Few effortful words; swearing and stock phrases kept | Speech | 0 s | 0.20 / 0.70 | — | `[S R2-01:S12,S13]` |
| `Wernicke` (dominant side) | 5–10 | (55, 35, 43) | `vocal: JARGON`, `obeys_p` | Fluent nonsense; does not obey commands | Speech | 0 s | 0.20 / 0.70 | — | `[S R2-01:S12]` (H) |
| `S1` | 10–15 | (40, 20, 88) | `sens` | Cortical sensory loss; weaker flinch to touch on that side | Contra | 0 s | 0.20 / 0.70 | — | `[S R2-01:S21]` |
| `PPC` | 30–50 | (35, 50, 73) | `neglect`, `reach_err` | Hemispatial neglect; optic ataxia (reach error 5–20 cm) | Contra space | 0 s | 0.20 / 0.70 | Neglect p 0.43 (right lesion) / 0.20 (left); anosognosia 0.32 (right); pusher: right 0.17, left 0.10 if hemiparetic | `[S R2-01:S17,S19,S20]` |
| `V1_upper` / `V1_lower` / `V1_pole` / `optic_rad` | 5–8 each | (10, 78, 31) / (10, 78, 21) / (8, 88, 27) / (30, 30, 40) | `vision_mask` | Contra **lower** quadrant / **upper** quadrant / central field / hemifield | Contra field | 0 s | loss ∝ fraction | Macular sparing 2–10° unless the pole is hit | `[S R2-01:S22,S24]` |
| `temporal_lat` | 60–80 | (55, 10, 25) | `vocal` (dominant side), `vision_mask` (Meyer's loop), `seizure_mult` 1.5 | Comprehension loss (dominant side); upper quadrantanopia; high seizure and herniation risk | — | 0 s | 0.30 / 0.80 | — | `[K] (H)` |
| `hippocampus` | 3.5–4 | (28, 12, 20) | `amnesia` | Severe amnesia only if **both** sides > 0.5 (repeats questions every 30–120 s) | Global | 0 s | 0.50 / 0.80 | — | `[K] (H)` |
| `amygdala` | 1.5–2 | (23, −6, 17) | `fear_gain` | Reduced fear (both sides) | Global | 0 s | 0.30 / 0.80 | — | `[K] (M)` |
| `caudate` | ~4 | (13, −22, 50) | `abulia` | Apathy, slow answers | Contra | 0 s | 0.20 / 0.60 | Abulia p 0.28; disinhibition p 0.11 | `[S R2-01:S10]` (M) |
| `putamen` (+ adjacent capsule) | ~5 | (25, −12, 40) | via `IC_post`; `gaze_bias` 15–30° toward lesion | Hemiplegia (from the capsule) and gaze deviation | Contra | 0 s | 0.20 / 0.60 | — | `[S R2-01:S27]` |
| `STN` | 0.15–0.2 | (11, 0, 32) | `ballism` | Hemiballismus: violent proximal flinging of the arm and leg | Contra | 0 s – 48 h (default minutes) | 0.30 / 0.60 | p 0.3 if STN sev > 0.3 and capsule sev < 0.5 | `[S R2-01:S25,S26]` |
| `thal_lateral` | ~5 | (16, 5, 42) | `sens`, `astasia` | Dense contra sensory loss; cannot stand (falls backward or to the contra side) | Contra | 0 s | 0.10 / 0.50 | Astasia p 0.3 if sev > 0.2 | `[S R2-01:S30]` (M) |
| `thal_paramedian` | ~2 | (6, 0, 44) | `arousal`, `eye_down_in` | Drowsiness; **both sides** → GCS 3–8, vertical gaze palsy, eyes down and in, pupils 2–3 mm | Global | 0 s | both sides 0.10 / 0.30 | Wrong-way eyes p 0.1–0.2 | `[S R2-01:S27,S28,S29]` |
| `IC_post` | 2–4 | (22, 2, 44) | `str_*` (face = arm = leg) | Dense hemiplegia from a ~10 mm lesion | Contra | 0 s | 0.05 / 0.30 | Incomplete variant (face + arm, or arm + leg only) p 0.3 | `[S R2-01:S31]` ✓ |
| `IC_genu` / `IC_ant` | 0.5–1 / 1–2 | (18, −10, 46) / (16, −20, 48) | `str_face_lower`, `str_tongue` / `cog` | Face and tongue weakness / confusion and abulia | Contra | 0 s | 0.05 / 0.30 | — | `[K] (H)` |
| `corpus_callosum` | 15–20 (midline) | (0, −10, 60) | marker only | Disconnection (not shown). Marks a transventricular track: death p 0.9–1.0 | — | — | — | — | `[S R2-01:S95]` (M) |
| `cb_hemi` | 55–65 | (30, 40, −5) | `ataxia_limb` (ipsi), `nystagmus`, `vomit`, `vocal: DYSARTHRIC_CEREBELLAR` | Ipsi dysmetria, 3–5 Hz intention tremor; lurches and falls **toward the lesion** | **Ipsi** | 0 s | 0.10 / 0.50 | Nystagmus p 0.75; vomiting p 0.6–0.8 in the first hour; cannot walk p 0.7 if sev > 0.3 | `[S R2-01:S39,S41,S44]` |
| `vermis` | 10–15 (midline) | (0, 35, 0) | `ataxia_trunk` | Truncal ataxia; titubation 2–4 Hz; cannot sit unsupported | Midline | 0 s | 0.10 / 0.50 | — | `[S R2-01:S43]` |
| `flocculonodular` | 2–3 | (20, 22, −2) | `nystagmus` | Gaze-evoked, downbeat or periodic alternating nystagmus | Eyes | 0 s | 0.10 / 0.50 | — | `[S R2-01:S45,S46]` |
| `midbrain_ventral` (peduncle) | ~2 | (10, 0, 27) | `CN3` ipsi, `str_*` contra | Weber syndrome: ipsi CN III palsy + contra hemiplegia including the lower face | Crossed | 0 s | 0.02 / 0.20 | — | `[S R2-01:S47]` |
| `midbrain_teg` | ~3 (midline) | (0, 7, 28) | `arousal`, `CN3` nucleus, `red_nucleus` | Coma if both sides; mid-position fixed pupils 4–6 mm; decerebrate; contra ataxia and tremor (Claude/Benedikt) | Crossed | 0 s | 0.02 / 0.20 | Decerebrate p 0.3–0.6 | `[K] R1-04 §2.2` |
| `midbrain_tectum` | ~1.5 (midline) | (0, 15, 30) | Parinaud | Upgaze palsy (87–100 %), convergence-retraction nystagmus, light-near dissociation, lid retraction | Both eyes | 0 s | 0.02 / 0.20 | — | `[S R2-01:S48]` |
| `pons_basis` | ~8 (midline) | (0, −3, 12) | `str_*` both sides | Quadriparesis. Both ventral halves destroyed → **locked-in** | Both | 0 s | 0.02 / 0.20 | Locked-in p ≤ 0.05 (low-energy ventral only) | `[S R2-01:S56]` |
| `pons_teg` | ~7 | (0, 7, 12) | `arousal`, `PPRF`, `MLF`, `CN6`, `CN7`, `pupil_pinpoint` | Coma; gaze palsy toward the lesion; INO; peripheral facial palsy; pinpoint pupils; ocular bobbing; apneustic/cluster breathing | Crossed | 0 s | 0.02 / 0.20 | — | `[S R2-01:S52,S53,S54,S57]` |
| `medulla_medial` | ~3 (midline) | (0, 5, −8) | `tongue` ipsi, `str_*` contra (sparing the face) | Dejerine syndrome. Both sides → quadriplegia and respiratory failure | Crossed | 0 s | 0.02 / 0.15 | — | `[S R2-01:S60]` |
| `medulla_lateral` | ~2 | (6, 7, −8) | `horner`, `dysphagia`, `ataxia_limb` ipsi, `lateropulsion`, `hiccup` | Wallenberg syndrome. Both sides or the centre → **apnoea**, vasomotor collapse | Ipsi (crossed sensory) | 0 s | 0.02 / 0.15 | Signs rolled independently (§1.5) | `[S R2-01:S58,S59]` (M) |
| `hypothalamus` | ~4 (midline) | (0, −6, 27) | `temp`, `DI` | Hyperthermia 0.5–1 °C/h; polyuria (hours) | Global | hours | 0.20 / 0.60 | — | `[S R2-01:S115]` |
| `optic_nerve` | small | (22, −50, 23) | `vision_mask` (one eye), `rapd` | Blind eye; afferent pupil defect | That eye | 0 s | 0.10 / 0.50 | — | `[K] (H)` |
| `chiasm` | small (midline) | (0, −16, 26) | `vision_mask` | Loss of both outer half-fields | Both eyes | 0 s | 0.10 / 0.50 | — | `[K] (H)` |
| `CN3_nerve` (extra-axial; uncal compression target) | small | (12, −10, 22) | `CN3` | Eye down and out, complete ptosis, pupil 6–9 mm fixed | Ipsi eye | 0 s (track) or clock (herniation) | 0.10 / 0.60 | — | `[S R2-01:S49,S50]` |
| `CN6_nerve` | small | (12, −2, 8) | `CN6` | Eye turned in (esotropia 6–22°) | Ipsi eye | 0 s, or with raised ICP | 0.10 / 0.60 | Traumatic p 0.01–0.027 per significant head injury | `[S R2-01:S51]` |
| `CN7_temporal_bone` | small | (45, −2, 0) | `palsy: peripheral` | Whole half-face palsy | Ipsi face | 0 s, or delayed days | 0.10 / 0.60 | p 0.07–0.10 per temporal-bone fracture; 0.3–0.5 if the fracture crosses the otic capsule | `[K⚠] R2-06 §9.5` |

### 1.3 Resolver algorithm (runs on wound events, plus the 20 Hz clock for the time-dependent terms)

```text
# Pseudocode written for this document (not taken from any source)
for region r:
    destroyed[r] = destroyed_volume(r) / volume(r)               # permanent track, fragments (RB §2, R1-01 §6)
    stun[r]      = stun_from_tracks(r) + stun_from_blunt(r)      # 0.5–1.0 inside the stun radius; decays (half-life
                                                                 #   30 s – 10 min) to a residual 0–0.3
    isch[r]      = territory_ischaemia(r)                        # named artery cut: rises to 1 over 10–20 s; permanent
    comp[r]      = compression(r, mass_model)                    # §1.7: diencephalon, brainstem, CN III on the mass side
    d[r]         = clamp(destroyed + stun + isch + comp, 0, 1)
    sev[r]       = smoothstep(vis[r], full[r], d[r]) * trait_factor[r]
channels = side_map(sev)     # contra / ipsi / crossed per §1.1, dominance per character
channel[c] = max(sev of every region driving c)                 # never summed
roll_probabilistic_signs_on_first_crossing()                     # neglect, pusher, ballism, seizure, Kernohan, wrong-way eyes
consciousness = resolve_last()                                   # RB §4.2 resolver + §1.5.7
```

Constants and rules `[E] R2-01 §20.2` unless tagged:
- **Stun radius**:
  - ≥ 18 mm around a low-energy handgun track `[S R1-01]`;
  - scale with deposited energy: ×1.5 for 9 mm JHP / .45, ×2–3 for rifle tracks without a burst `[E]`.
  - A near-miss within 10–20 mm of the brainstem counts as concussive brainstem dysfunction: immediate LOC and impact apnoea `[K] R1-04 §2.5`.
- **Blunt force** (hammer, punch, fall) has no track `[K] (H) R2-01 §20.2 ✓`:
  - A **still head struck** by an object gets **coup** stun under the impact (0.5–1.0), plus the frontal and temporal poles at 0.2–0.4.
  - A **moving head that stops** (a fall onto the floor, being thrown) gets **contrecoup** contusions opposite the impact, largest at the frontal and temporal poles, larger than the coup lesion.
  - A depressed fracture adds `destroyed` for cortex under the fragment: 10–30 mm deep `[E] R2-05 §7.2`.
  - Rotational blows (hooks) add diffuse axonal injury (DAI) risk: `dai_p` = 0.02 × max(0, (α − 7,000)/1,000) per blow `[E]` on `[K] R2-02 §6.1`. DAI grade 3 → coma > 6 h with posturing `[S R2-01:S114]`.
- **Ischaemia**: an MCA, ACA, PCA branch or basilar perforator inside the track radius makes its territory fail over 10–20 s. A common or internal carotid cut with poor collaterals (p 0.2–0.3) gives hemispheric ischaemia with onset 5–30 s `[K⚠] (L) R2-04 §10.3`.
- **Probabilistic signs** are rolled once, when the region's severity first crosses `vis`.

### 1.4 Channels and what they do to the body

| Channel | Range | Driven by (max of) | Effect on the body | Consumer |
|---|---|---|---|---|
| `str_{arm,hand,leg,foot,trunk}_{L,R}` | 0–1 severity | M1 segment, IC_post, peduncle, pons basis, medulla medial, cord | Drive scale on PD targets `(1 − sev)^1.5`; torque cap × `(1 − sev)`; MRC = floor(5 − 5·sev); proximal/axial sparing 0.3 at sev 1 for cortical lesions | §4.4 `[E] R2-01 §2.5` |
| `tone_active_{limb}_{side}` | 0–1 | as `str` | Acute paralysis is flaccid: arm 0–0.2, leg 0.2–0.4 at sev 1; passive damping 0.6–0.9 × relaxed | §4.4 `[E] R2-03 §4.5` |
| `str_face_lower` / `str_face_upper` | 0–1 | M1_face, IC_genu, pons (CN VII), CN VII nerve | AU gains (§2.7). Central lesions spare the upper face (gain 0.8–1.0); peripheral lesions take the whole half-face | §2 `[S R2-06:S4]` |
| `str_tongue` | 0–1 | M1_bulbar, medulla medial | Protrusion deviates toward the weak side (cortex) or toward the lesion (medulla); dysarthria | §2 `[K] (H)` |
| `ataxia_limb_{side}` | 0–1 | cb_hemi (ipsi), red nucleus (contra), lateral medulla (ipsi) | Reach overshoot 3–10 cm; intention tremor 3–5 Hz, 1–5 cm at the fingertip in the last 10–20 cm of a reach | §3, §5 `[S R2-01:S44]` |
| `ataxia_trunk` | 0–1 | vermis | Gait table §1.5.3; titubation; cannot sit unsupported at sev > 0.7 `[E]` | §4 |
| `lateropulsion` | vector | lateral medulla (toward the lesion, 5–15 % body weight), thalamic astasia (backward or contra), pusher (toward the paretic side) | Constant lateral force in the balance controller | §4.8 `[E] R2-01 §13.5` |
| `gaze_bias` | ° yaw | FEF, putamen, PPC neglect (toward), seizure (away), pons (away) | Resting gaze and head yaw offset | §2 |
| `eye_overlay_{L,R}` | struct | CN III, IV, VI, INO, skew, Parinaud, Horner, thalamus | Per-eye offsets, lid and pupil overrides | §2.4 |
| `vision_mask_{eye}` | 4 quadrants + centre | V1, optic radiation, optic nerve, chiasm | Perception culling for the AI; head compensation 10–25° toward the blind side | §3 `[E] R2-01 §7.2` |
| `vocal_state` | enum | Broca, Wernicke, global, M1_bulbar, cerebellum, medulla, GCS V | Mouth and jaw movement of speech and vocalisation (§2.1) | §2 |
| `rt_mult` | 1–3 | PFC, diffuse injury, concussion, hypoxia | Multiplies every L3/L4 latency | §3 `[E] R2-02 §10` |
| `persev_p` / `inappropriate_p` | 0–1 | PFC_dl / PFC_orb | Repeats the last action or line / laughs, wanders, walks toward danger | §3 |
| `abulia` | 0–1 | ACC, caudate, SMA | Delays and suppresses spontaneous action; akinetic mutism at bilateral > 0.5 | §3 |
| `grasp_reflex` | bool | medial frontal sev > 0.3 | The hand closes on anything touching the palm, including the player's hand or weapon | §3 `[S R2-01:S8]` |
| `sens_{side}` / `neglect_{side}` | 0–1 | S1, thal_lateral / PPC | Hit-reaction gain on that side × (1 − sens) and × 0.1–0.4 under neglect | §3 |
| `arousal_cap` | GCS | RAS structures, thalami, bilateral hemispheres, ICP | Consciousness resolver | §1.5.7 |
| `seizure_foci` | list | cortex only | Seizure scheduler | §1.8 |

### 1.5 Deficit effects on the body

#### 1.5.1 Limb weakness and paralysis (per limb, per side)

| Severity | MRC | Drive scale | Arm | Hand | Leg | Tag |
|---|---|---|---|---|---|---|
| < `vis` | 5 | 1.0 | Normal | Normal | Normal | — |
| 0.1–0.4 | 4 | 0.95–0.46 | Slight drift; clumsy | Grip weakens; fine actions (trigger, fumbling) fail at 0.3+ | Limp; the toe catches | `[E] R2-01 §2.4` |
| 0.4–0.8 | 3–1 | 0.46–0.09 | **Pronator drift**: the raised arm sinks and turns palm-down within 3–10 s | Grip 0.3–0.7 of normal | Buckles under load above 0.6 | `[S R2-01:S37]` |
| > 0.8 | 0–1 | < 0.09 | **Drops as dead weight in 0.1–0.3 s**; swings passively with the body | Fingers open; **the weapon falls 0.1–0.5 s** after sev passes 0.7 | **The knee buckles 0.2–0.6 s after weight comes on**; the body falls **toward the paralysed side**; the good arm reaches out if conscious | `[E] R2-01 §2.4` |

- A parasagittal (vertex) track takes out both leg areas: both legs give way while the arms keep working `[K] (M)`.
- Hemiplegia doubles as a reaction modifier: no protective arm and no hand-to-wound on the paralysed side, and fall probability ×3 for perturbations toward it `[E] R2-02 §10`.

#### 1.5.2 Muscle tone per limb (acute game window)

| Cause | Active tone | Passive properties | Duration in game | After a time skip | Tag |
|---|---|---|---|---|---|
| Cortex or capsule, complete | Arm 0–0.2, leg 0.2–0.4 (reticulospinal sparing); face lower drooping | Damping 0.6–0.9 × a relaxed healthy limb; limits and soft zones unchanged | Flaccid for the whole session | Spastic 1–6 weeks (24.5 % by ~2 weeks): stretch "catch" ×2–4 at > 60–120 °/s; flexed arm, extended leg | `[S R2-01:S1,S2]` ✓, `[E] R2-03 §4.2` |
| Cord below the level (spinal shock) | 0, areflexic; **no withdrawal, no flinch** to cutting or burning | Passive only | 0–24 h (the whole game) | Reflexes return from 1–3 days; hyperreflexia from 4 days to 1 month | `[S R2-02:S46]`, RB §4.6 |
| Cerebellar hemisphere | Hypotonia ipsi (kp × 0.7–0.9) | Riddoch's sign: the outstretched arm drifts **up** and over-pronates | Session | — | `[E]` on `[S R2-01:S39]` |
| Unconscious (any cause) | 0 everywhere, except posturing and seizure programmes | Passive | While unconscious | — | `[K] R2-02 §0.4` |
| Posturing episode | 0.5–0.8 of max toward posture targets (§4.4) | ζ 1.2–2.0 ("lead-pipe") | 5–60 s episodes | — | `[E] R2-01 §18.2` |

#### 1.5.3 Balance and gait

| Condition | Step width | Speed | Stride-time variability (CV) | Sway | Falls toward | Signature | Tag |
|---|---|---|---|---|---|---|---|
| Healthy | 8–12 cm | 1.2–1.4 m/s | 2–3 % | 1–2 cm | — | — | `[K] R2-01 §12.2` |
| Concussed or "rocked" | +50–100 % | ×0.5–0.7 | step-length CV 20–40 % | ×2–3 | Along the motion | Knees dip 10–30° and recover; buckle rate 0.1–0.3 /s in the first 10 s; hands grab support or the attacker; rubber-leg knee tone 0.35–0.6 ± 0.2–0.3 at 1.5–3 Hz for 1–5 s | `[E] R2-02 §6.4, R2-03 §5.4` |
| Cerebellar hemisphere | 15–30 cm | 0.5–0.9 m/s | 6–15 % | 5–15 cm, bursts toward the lesion | The lesion side in 60–80 % of falls | Lateral foot-placement error 5–15 cm; 2–5 wide lurching steps before a fall; recovers once or twice; grabs walls | `[S R2-01:S39,S41,S42]` |
| Vermis | Very wide | Cannot walk unaided at sev > 0.3 (p 0.7) | High | Titubation 2–4 Hz, 1–3 cm | Any direction, often backward | Cannot sit unsupported | `[S R2-01:S43]` |
| Acute hemiparesis (leg sev 0.3–0.6) | Wide | 0.3–0.8 m/s | High | — | The paretic side | Stance on the paretic leg ×0.6–0.8; toe drag; knee gives way under load; hand on the wall. Leg sev > 0.6: cannot stand | `[E]` on `[K]` |
| Thalamic astasia | — | Cannot stand; some cannot sit | — | — | **Backward** or contra | Strength near normal | `[S R2-01:S30]` |
| Pusher syndrome | — | — | — | — | The paralysed side, **actively pushed** by the good limbs | Resists being righted | `[S R2-01:S20]` |
| Lateral medulla | Wide | Slow | — | Leans progressively | Pulled toward the lesion (5–15 % body weight) | Vertigo, vomiting, hiccups | `[S R2-01:S58]` |
| Hypovolaemia class III | +50–100 % | Slow | — | ×2–3 | Sag and descent | Sits down deliberately (§4.5 C, G) | `[E] R2-03 §5.5` |
| Hemianopia | — | — | — | — | — | Bumps doorframes on the blind side; head turned 10–25° toward it | `[E] R2-01 §7.2` |
| Cortical blindness | — | Slow | — | — | — | Arms out, groping; walks into walls if Anton (p 0.1–0.2) | `[S R2-01:S22]` |

#### 1.5.4 Speech and vocalisation states (`vocal_state`)

| State | Cause | Speech pattern (shown only as mouth and jaw movement) | Obeys commands | Tag |
|---|---|---|---|---|
| `NORMAL` | — | Normal speech (articulation rate 4–6 syll/s) | Yes | `[K] (H)` |
| `DYSARTHRIC_UMN` | M1 face/tongue, capsule genu | Slurred, slow (3–5 syll/s), words intact | Yes | `[K] (H)` |
| `DYSARTHRIC_CEREBELLAR` | Cerebellum | Scanning: equal, excess stress; 3–4 syll/s | Yes | `[S R2-01:S16]` (H) |
| `DYSARTHRIC_BULBAR` | Pons/medulla (CN VII, IX, X, XII) | Weak cough; 3–5 syllables per breath | Yes | `[K] (M)` |
| `NONFLUENT` | Broca + surroundings | 10–50 words/min, 1–5 s groping pauses; automatic phrases and **swearing preserved** | p 0.7 | `[S R2-01:S12,S13]` |
| `JARGON` | Wernicke | Fluent, normal prosody, neologisms; unaware of the errors | p 0.1 | `[S R2-01:S12]` |
| `GLOBAL` | Large dominant MCA territory | Mute, or one recurring 1–3-syllable utterance | 0 | `[K] (H)` |
| `MUTE_AKINETIC` | Bilateral medial frontal/cingulate; left SMA | No speech; rarely a whispered monosyllable after 5–30 s | Variable | `[S R2-01:S4,S9]` |
| `CONFUSED` (GCS V4) | Concussion, hypoxia, class III, frontal | Repeats questions every 30–120 s; response latency 1–5 s | Partly | `[K] R2-06 §7.1` |
| `MOAN_ONLY` (V2) | Stupor | Moans and groans, especially to pain | No | `[S R2-01:S93]` |
| `SILENT` (V1) | Coma, apnoea, locked-in, airway below the cords | Nothing (locked-in: nothing despite full awareness) | Locked-in: yes (eyes) | `[S R2-01:S56]` |

- **Pain vocalisation survives aphasia** (it is brainstem and limbic): a left-hemisphere wound removes words, not screaming `[K] (H) R2-01 §5.2`.
- The *capacity* to scream is not a *tendency* to scream. No vocal reaction, a grunt or "I'm hit" are common after gunshots and stabs; §3.6 gates vocalisation.

#### 1.5.5 Vision

| Deficit | Visible behaviour | Parameters | Tag |
|---|---|---|---|
| Hemianopia / quadrantanopia | Does not see a threat from the blind side; turns the head to scan | Mask per quadrant; macular sparing 2–10° (default 5°) unless the pole is hit; head compensation 10–25° | `[S R2-01:S24]` |
| Cortical blindness (both V1) | Eyes open and wandering slowly, **no fixation**, **no menace blink**; **pupils react normally**; arms out, groping; may insist it can see | `cortical_blind_fixation` false; Anton p 0.1–0.2 | `[S R2-01:S22]` (H) |
| Optic nerve | One blind eye; the pupil reacts only to light shone in the other eye (afferent defect) | Swinging-light test fails | `[K] (H)` |
| Diplopia (CN III/IV/VI, skew, INO) | Squints, closes one eye (p 0.3–0.6 per minute of activity `[G]`), tilts the head, misjudges reaches | Reach error +2–5 cm | `[E] R2-02 §10` |
| Blood in the eyes (scalp or brow wound) | Blinks, wipes, stumbles | Onset 5–30 s after a scalp wound | `[E] R2-02 §3` |

#### 1.5.6 Cognition and behaviour

| Deficit | Behaviour | Parameters | Tag |
|---|---|---|---|
| Frontal (dorsolateral) | Blank stare; long pauses; perseveration | `response_latency_add` 1–10 s × sev; `persev_p` = 0.2 + 0.5·sev per action choice | `[E]` on `[S R2-01:S7,S8]` |
| Orbitofrontal | Laughs, swears, walks toward danger, no fear | `disinhib` = sev | `[S R2-01:S11]` |
| Utilisation behaviour | Picks up and uses nearby objects | p 0.1–0.4 | `[S R2-01:S8]` |
| Akinetic mutism | Awake, eyes follow the player; no speech, no voluntary movement; withdrawal to pain may remain | Both-side medial frontal / ACC sev > 0.5 | `[S R2-01:S9]` |
| Amnesia | Repeats questions; no memory of the attack | Every 30–120 s | `[E]` on `[K]` |
| General cognitive slowing | All reactions late and wrong | `rt_mult` 1.3 (mild) – 3.0 (severe) | `[E] R2-02 §10` |

#### 1.5.7 Consciousness and GCS

Resolver: RB §4.2 (first match wins). This document adds the behaviour mapping and the component rules `[S R2-01:S93]`, `[E] R2-01 §19`.

| GCS | Category | Eyes (E) | Verbal (V) | Motor (M) | Behaviour the player sees |
|---|---|---|---|---|---|
| 15 | Alert | Spontaneous | Oriented | Obeys | Normal, with focal deficits |
| 13–14 | Mild | Spontaneous | Confused (V4) | Obeys or localises | Awake, repeats questions, unsteady walking |
| 9–12 | Moderate | To speech or pain | Words / moans | Localises or withdraws | Eyes flutter open when shaken or touched; pushes the player's hand away; cannot stand |
| 6–8 | Severe | To pain or none | Moans or none | Withdraws or postures | Eyes shut; groans when hurt; stiffens; obstructed breathing (slack jaw, heaving chest) or froth bubbling at the lips |
| 3–5 | Deepest | None | None | Posturing or flaccid | Nothing except stiffening spasms; obstructed breathing or froth bubbling at the lips if breathing |

- E follows arousal and lid control. Lid swelling from periorbital haematoma blocks eye opening (clinically "not testable") `[E]`.
- V follows `vocal_state`. **Aphasia lowers V without lowering consciousness.**
- M is the best response the character can produce (§1.8 posturing, §3.5 withdrawal).
- **Locked-in** scores E4 V1 M1 with full awareness: vertical eye movements and blinks answer questions `[K] (H)`.

### 1.6 Spinal cord levels (engine data file `cord_levels.csv`)

Vertebra-to-segment mapping, complete-injury probabilities and incomplete syndromes: RB §4.6. The behaviour columns are added here `[K] (H)` patterns, `[E]` drive values, R2-03 §4.5.

| Level (complete) | Breathing capacity (fraction of vital capacity) | Voluntary groups (tone 1) | Flaccid groups (tone 0, no withdrawal) | Resting / falling picture | Speech |
|---|---|---|---|---|---|
| C1–C3 | 0–0.1 (apnoea) | Face, eyes, jaw, weak neck turn and shrug (CN XI) | Everything below | **Cut strings but awake**: eyes wide and darting, mouth opening without airflow 10–30 times/min, neck straining, chest still; lips blue by 1–2 min; LOC at 90–180 s | Mouths words only (aphonic) |
| C4 | 0.25 | + shoulder shrug | Arms, trunk, legs | Paradoxical belly breathing | 1–3 words per breath |
| C5 | 0.3 | Deltoid, biceps (drive ω 6–10) | Triceps, wrists, hands, trunk, legs | **"Arms up"**: shoulders abducted 45–90°, elbows 90–120° flexed, forearms supinated, hands limp | Weak |
| C6 | 0.4 | + wrist extensors | Fingers, trunk, legs | As C5 plus wrists extended 20–40°; fingers curl through tenodesis | Weak |
| C7–C8 | 0.5 | + triceps (C7), grip (C8) | Hand intrinsics, trunk, legs | Pushes up weakly | Near normal |
| T1–T6 | 0.6 | Arms | Poor trunk, legs | Falls sideways even when sitting; props on the arms | Normal |
| T7–T12 | 0.8 | Arms, better trunk | Legs | **Legs vanish in ≤ 100 ms; sits down hard or pitches onto the hands**; drags itself on the elbows | Normal |
| L1–L2 | 1.0 | Upper body, weak hip flexion | Legs | As T12 | Normal |
| L3–S1 (cauda) | 1.0 | Partial legs by root | Patchy, asymmetric; foot drop | Limps; the foot slaps | Normal |

- **Brown-Séquard hemisection** (knife to the side of the back or neck; 0.3–0.5 of knife cord injuries) `[K] RB §4.6`:
  - the leg on the side of the cut is flaccid and has lost position sense; the body falls toward it;
  - the other leg moves but ignores pain and heat from 1–2 segments below the level.
- **Central cord**: arms much weaker than legs. **Anterior cord**: paralysis and pain loss with position sense kept. **Cord concussion** (hammer or fist to the neck): complete paralysis resolving in 2 min – 48 h (default 10 min).
- Below the level: no pain behaviour, no withdrawal, no sweating, no shivering `[K] R2-04 §1`.
- A bullet can paralyse without touching the cord when bone fragments are driven into the canal `[K] (H) R2-05 §13`.

### 1.7 Progression over time

#### 1.7.1 Intracranial mass and pressure model

| Quantity | Rule / value | Tag |
|---|---|---|
| Normal ICP | 10 mmHg (5–15) | `[K] R1-04 §1` |
| Compensatory reserve | 60 mL (50–70) of acutely added mass before ICP climbs | `[K] (M) R2-01 §15.1` |
| ICP above the reserve | `ICP = 10 × 10^((V_mass − V_reserve) / 25)` (pressure–volume index 25 mL). Examples: 70 mL → 25 mmHg; 85 mL → 100 mmHg | `[E]` |
| Midline shift (MLS) | 0.10 mm per mL of lateral mass | `[E] R2-01 §15.1` |
| Consciousness vs MLS (Ropper) | 0–3 mm alert; 3–4 drowsy; 6–8.5 stupor; 8–13 coma; interpolate 4–6 | `[S R2-01:S84]` ✓ (H) |
| Temporal / middle-fossa mass | Uncal signs (pupil) can appear before a large shift: effective volume × 1.3 for the herniation triggers only | `[E] (L)` on `[K]` |
| CPP | MAP − ICP; herniation starts at ICP ≥ 30–40 or CPP < 50 | RB §4.3 |
| Cushing response | CPP < ~15 mmHg `[K⚠]`: stage 1 hypertension + tachycardia, stage 2 hypertension + bradycardia (SBP 160–240, pulse pressure 80–120, HR 40–60, down to 30), irregular breathing; full triad in only ~⅓ | `[S R2-01:S85]` |
| Plateau (Lundberg A) waves | ICP 50–100 mmHg for 5–20 min, then a sharp fall. During a wave: tonic posturing bursts every 30 s – 5 min; apnoea and decerebration at the peak | `[S R2-01:S86]` ✓ |
| Seizure effect | +10–20 mmHg during the seizure; can trigger herniation | `[E] R2-04 §4.5` |

#### 1.7.2 Haematoma and swelling types

| Type | Source / growth | Initial picture | Lucid interval | Deterioration | Tag |
|---|---|---|---|---|---|
| Epidural (EDH), arterial | Middle meningeal artery under a temporal (~75 %) fracture; **1 mL/min** (0.3–3) | Knockout 5 s – 5 min (p 0.6) or dazed only | p 0.2–0.5 (classic < 0.2); 60 min default (15–360) | Headache, 1–3 vomits → drowsy and slurred → contra arm drift → ipsi pupil +1 mm and sluggish → coma, blown pupil, decerebrate, Cushing → apnoea. **An untreated expanding EDH kills** | `[S R2-01:S76,S77,S78]` |
| EDH, venous (10–15 %) | Sinus or diploic veins; 0.1–0.3 mL/min | Same | Longer | Slower | `[K⚠] (M)` |
| Acute subdural (ASDH) | Bridging veins over contused brain; 0.2–1 mL/min, plus swelling adding 20–50 % of effective volume over 1–6 h | Usually comatose from the start | p 0.1–0.2 | Faster slide | `[E] R2-01 §15.3` |
| Penetrating-track haematoma | Along the track; initial 5–20 mL; growth 0.2–1 mL/min × (1 − clot fraction); intraventricular blood → hydrocephalus (tectal compression: upgaze palsy, "setting sun" eyes) | Per region | Variable | Minutes to hours | `[E]` on `[S R2-01:S118]` |
| Cerebellar track with bleeding | Posterior-fossa haematoma | Ataxia, vomiting, occipital headache, stiff neck, head tilt | — | Minutes to 48 h, then **sudden apnoea with the heart still beating** (tonsillar herniation) | `[K] (M) R2-01 §12.1` |
| Contusion expansion | Haemorrhagic growth over 12–24 h; oedema over 2–3 days | — | — | Time skips only | `[S R2-01:S83]` |
| "Talk and die" | Includes swelling without a haematoma | Talks after the injury | — | Dies later | p 0.03–0.08 of head-injured characters who talk `[S R2-01:S82]` |

#### 1.7.3 Herniation stage machine

Stages advance when their ICP/MLS triggers are met. Durations are defaults if the mass keeps growing, in real time; the game plays them at 4× `[E] on [S R2-01:S87]`.

| Stage | Trigger | Consciousness | Breathing | Pupils | Eyes | Motor | Default duration |
|---|---|---|---|---|---|---|---|
| U1 early uncal | Temporal mass effective > 70 mL, or ICP > 25 | Confused → drowsy | Normal or sighing | **Ipsi pupil**: brief constriction 5–60 s (easily missed) → +1 mm, sluggish, oval during the change | Normal | Contra arm drift | 10–30 min |
| U2 uncal (CN III + peduncle) | ICP > 30–40 | Stupor → coma | Cheyne–Stokes | Ipsi **6–9 mm fixed**; ipsi ptosis; eye down and out | Doll's eyes weakening | **Contra hemiparesis** (Kernohan: ipsi, p 0.1–0.2); decorticate → decerebrate | 10–30 min |
| C1 early diencephalic | Central mass, bilateral swelling | Drowsy, agitated | Sighs, yawns → Cheyne–Stokes (cycle 45–90 s) | Small 1–3 mm, reactive | Roving; doll's eyes intact | Localises; paratonia | 10–60 min |
| C2 late diencephalic | — | Hard to rouse | Cheyne–Stokes | Small, reactive | Doll's eyes intact | Decorticate | 10–30 min |
| M midbrain–upper pons (both paths converge) | ICP ≥ 40–50 | Coma | Central neurogenic hyperventilation ≥ 25 /min (40–60) | Mid-position 3–5 mm, **fixed**, irregular; the uncal side stays larger | Doll's eyes weak and dysconjugate | **Decerebrate** | 5–30 min |
| P lower pons–upper medulla | — | Coma | Shallow and fast, or ataxic, with apneustic pauses | Mid-position, fixed | Doll's eyes and calorics absent | Flaccid; legs may withdraw from foot stimuli | 2–15 min |
| X medulla | ICP ≥ MAP | Coma | Slow irregular gasps → **apnoea** | Dilate (hypoxia) | None | Flaccid | 1–5 min to apnoea |
| T tonsillar (posterior fossa) | Posterior-fossa mass | Occipital headache, stiff neck, vomiting, then coma | **Sudden apnoea** | — | — | — | Minutes |

After apnoea: hypoxic arrest 4–10 min later (default 6) `[K] R1-04 §2.4`. Posturing **stops** when the medulla fails; that is a bad sign, not an improvement `[K] (H)`.

#### 1.7.4 Breathing pattern by level (feeds §5.2)

| Pattern | Level | Rhythm | Tag |
|---|---|---|---|
| Cheyne–Stokes | Bilateral hemispheres / diencephalon | Crescendo–decrescendo 30–40 s alternating with apnoea 10–30 s (cycle 40–90 s) | `[S R2-01:S96]` (M) |
| Central neurogenic hyperventilation | Midbrain / upper pons | Deep, regular, ≥ 25 /min | `[S R2-01:S96]` |
| Apneustic | Mid/lower pons | Deep inspiration **held 2–3 s**, brief expiration | `[S R2-01:S96]` |
| Cluster | Lower pons / upper medulla | 3–5 irregular breaths, then 10–30 s apnoea | `[E] (L)` |
| Ataxic (Biot) | Medulla | Random rate (4–12 /min) and depth, random pauses | `[S R2-01:S96]` |
| None | Medulla destroyed | Apnoea at once, **no gasps** | `[K] (H) R1-04 §2.2` |

### 1.8 Seizure and posturing triggers

**Seizure probabilities** (rolled once per injury event; gated by `gate_seizure`, i.e. cortical perfusion > 0.3 for the last 10 s):

| Situation | p | Onset distribution | Tag |
|---|---|---|---|
| Concussive (impact) convulsion on a knockout | 0.014 (≈ 1 in 70) | Tonic within 2 s, ≤ 20 s; then jerks ≤ 150 s; benign, not epileptic | `[S R2-01:S100]` (M) |
| Penetrating cortical track, first hour | 0.05–0.10; × 1.5 if motor strip or temporal cortex is involved | 30 % within 60 s, the rest log-uniform between 1 and 60 min `[G]` | `[E]` on `[S R2-01:S103]` |
| Blunt cortical contusion or depressed fracture, first hour | 0.02–0.04; × 2 if bone fragments penetrate the dura `[E]` | As above | `[S R2-01:S103]`, `[E]` |
| Early (1–7 days) | Moderate–severe TBI 0.04–0.25; penetrating ~0.2 | Time skips only | `[S R2-01:S103]` ✓ |
| Cerebellum, brainstem, deep white matter only | 0 | — | `[K] (H)` |

**Seizure type given a cortical focus** `[G]` shaped on `[S R2-01:S106,S107,S108]`:
- focal motor without spread 0.35;
- focal → bilateral tonic–clonic 0.55;
- non-motor (staring, automatisms) 0.10.
- A full Jacksonian march is rare: p 0.1 of focal motor seizures.
- Status epilepticus (> 5 min continuous) only with severe injury, p 0.02–0.05 per seizure `[G]`.
- A second seizure within 60 min, p 0.15–0.3 in severe injury `[G]`.

**Posturing triggers** `[K] (H) R2-01 §18, R1-04 §4.1`:

| Lesion or state | Posture (GCS M) | Mode |
|---|---|---|
| Bilateral hemispheres, thalamus, internal capsule, early central herniation | Decorticate (M3) | Episodes 5–60 s: on stimulus (latency 0.2–1 s, refractory 5–20 s), during plateau waves, or spontaneously every 30 s – 5 min |
| Midbrain / upper pons (damage or compression) | Decerebrate (M2) | Same; can alternate with decorticate or be asymmetric |
| Lower pons, medulla, high cord | Flaccid (M1) | None |
| Knockout (brainstem acceleration) | Fencing response | p 0.66 at impact, 2–10 s (max ~20 s), once |
| Midbrain destroyed by a track | Decerebrate topple | p 0.3–0.6, 5–30 s |

- The human lesion-level rule is loose. Allow either posture with ICP / plateau-wave severity; progression runs decorticate → decerebrate → flaccid `[K] (M) R2-01 §18.1`.

### Simulation parameters (neuro model)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `region_table` | §1.2 | — | CSV; volumes from the procedural brain | `[K]`/`[E]` |
| `severity_curve` | smoothstep(vis, full, d) × 0.85–1.15 | — | Per region | `[E] R2-01 §20.2` |
| `stun_radius_handgun` | 18 (×1.5 JHP/.45, ×2–3 rifle without burst) | mm | Decays with half-life 30 s – 10 min to 0–0.3 | `[S R1-01]`, `[E]` |
| `brain_stun_nonhead_hits` | 0 | — | "Hydrostatic shock" guard | `[K] (M)` |
| `drive_scale` | (1 − sev)^1.5 | × | PD targets; torque cap × (1 − sev) | `[E] R2-01 §2.5` |
| `proximal_sparing` | 0.3 | fraction at sev 1 | Cortical lesions | `[E]` |
| `flaccid_arm_tone` / `leg_tone` | 0–0.2 / 0.2–0.4 | × | Complete acute lesion | `[E] R2-03 §4.5` |
| `flaccid_passive_damping` | 0.6–0.9 | × relaxed | Never frictionless | `[E] R2-01 §24.6` |
| `arm_drift_time` | 3–10 | s | sev 0.4–0.8 | `[S R2-01:S37]` |
| `weapon_drop` | hand sev > 0.7, delay 0.1–0.5 | s | | `[E]` |
| `leg_buckle_after_load` | 0.2–0.6 | s | leg sev > 0.6 | `[E]` |
| `fef_gaze_bias` | 15–40 (25) toward the lesion; head 10–30 | ° | Lasts 2–7 d | `[S R2-01:S63,S64]` (M) |
| `neglect_p` right / left | 0.43 / 0.20 | p | PPC sev > 0.3 | `[S R2-01:S17]` ✓ |
| `cb_fall_bias_to_lesion` | 0.6–0.8 | p | | `[E]` on `[S R2-01:S39]` |
| `intention_tremor` | 3–5 Hz, 1–5 cm | — | Last 10–20 cm of a reach | `[S R2-01:S44]` ✓ |
| `icp_reserve` / `pvi` | 60 (50–70) / 25 | mL | | `[K]`/`[E]` |
| `mls_per_ml` | 0.10 | mm/mL | | `[E]` |
| `edh_rate` | arterial 1 (0.3–3); venous 0.1–0.3 | mL/min | | `[E]` |
| `edh_lucid_p` / `duration` | 0.2–0.5 / 60 (15–360) | p / min | | `[S R2-01:S76,S77]` |
| `herniation_stage_durations` | §1.7.3 | min | Real time; game 4× | `[E]` on `[S R2-01:S87]` |
| `kernohan_p` | 0.1–0.2 | p | Ipsi hemiparesis | `[S R2-01:S88]` (L) |
| `hutchinson_false_side_p` | 0.10–0.15 | p | First dilated pupil opposite the mass | `[K] (M)` |
| `p_seizure_penetrating_1h` / `blunt_1h` | 0.05–0.10 (×1.5 motor/temporal) / 0.02–0.04 | p | First hour only; RB's 0.2 / 0.10–0.15 cover the first week (C-02) | `[E]` on `[S R2-01:S103]` |
| `concussive_convulsion_p` | 0.014 | p | On knockout | `[S R2-01:S100]` |
| `posture_episode` | ramp 0.5–2 s, hold 5–60 s, release 1–3 s; refractory 5–20 s | s | | `[E] R2-01 §18.2, R2-04 §5.6` |
| `fencing_p` / `duration` | 0.66 / 2–10 (≤ 20) | p / s | | `[S R2-01:S99]` ✓ |

### Visual/behavioural checklist (neuro model)
- The same bullet produces a different character depending on its track: a limp arm with a sagging mouth corner; a drunk-looking lurch toward the wound; a speechless staring statue; a violently flinging arm; crossed eyes with a pinpoint-pupil coma.
- A one-sided brain wound leaves the character awake (after at most a short collapse), weak on the **opposite** side, eyes and head turned **toward** the wound.
- A cerebellar wound leaves the character strong but falling **toward** the wound side, overshooting every reach with a shaking hand, eyes jerking, vomiting.
- A brainstem wound mixes sides: an eye and the face on the wound side, the arm and leg on the other side.
- A slowly expanding haematoma turns a talking, walking character into a posturing coma with one blown pupil over tens of minutes. The eyes and the breathing announce it before the body stops moving.
- Paralysed limbs hang heavy but keep a slight resistance; they never flop like rope.

---

## 2. Eye and face controller

### 2.1 Architecture

**Per-eye outputs:**
- `yaw`, `pitch`, `torsion` (eye bones);
- upper-lid aperture (mm) and lower-lid offset (mm);
- `pupil_mm` and `pupil_gain` (0 = fixed, 1 = brisk) with its latency;
- `gloss`, `tear_volume`;
- globe mode {intact, ruptured, luxated, hanging, enucleated} (§6).

**Generators:**
- `SaccadeGen`: main sequence, target selection.
- `BlinkGen`: Poisson process, minimum interval 1 s.
- `VOR`/`Dolls`: counter-rotation against head motion, latency ~10 ms, gain 0–1.
- `NystagmusGen`: jerk waveform.
- `RovingGen`, `PingPongGen`, `BobbingGen`, `DippingGen`.
- `PupilGen`: light reflex, hippus, arousal and pain offsets, hypoxic dilation, lesion overrides.
- `TearGen`.

**Composition order**, evaluated per frame for on-screen characters `[E] R2-06 §14.4`:
1. The **base state** (§2.3) from consciousness, arousal and dying stage sets targets and generator parameters.
2. **Lesion overlays** (§2.4) add per-eye offsets and override lids, pupils and movement limits.
3. **Transient programmes** (§2.5): startle blink, pain squeeze, seizure, syncope upgaze.
4. **Physiology**: hypoxic pupil dilation, ambient light, tear film, colour lags.
5. **Clamps**: rotation range; lid-swelling caps (a periorbital haematoma caps AU5 at 0.2 and holds the lids partly closed).

**Priority when states compete:**
`DEAD` > `BRAINSTEM_DEAD` > `SEIZURE` > `SYNCOPE/ANOXIC` transient > `COMA` > lesion overlays > emotion/arousal.
Lesion overlays **persist through coma**: a CN III palsy stays down-and-out while unconscious.

**Face outputs:**
- AU weights (FACS, blendshapes; intensity A–E → weight 0.10 / 0.30 / 0.50 / 0.75 / 0.95);
- per-side palsy gains;
- `tone` (0–1) with gravity-sag correctives;
- jaw opening in mm;
- skin shader uniforms (pallor, cyanosis, flush, wetness).

**AU mixing:** sources combine by **maximum per AU**, never by sum. Mouth AUs from the vocal (`vocal_state`) and breathing generators override the expression mouth `[E] R2-06 §8.4`.

### 2.2 Rig reference numbers

| Quantity | Value | Tag |
|---|---|---|
| Rotation range | Horizontal ±45°; up +35°; down −45° | `[K] (M) R2-01 §14.8` |
| Saccade duration | 21 ms + 2.2 ms per degree (10° ≈ 43 ms; 20° ≈ 65 ms); peak 400–700 °/s | `[K] (H) R2-06 §12.3` ✓ |
| Saccade latency | 150–250 ms; the head joins gaze shifts > ~20° | `[K] (H)` |
| Fixation | 200–400 ms; microsaccades < 1°, 1–2 /s | `[K] RB §5.2` |
| Smooth pursuit | Accurate to ~30 °/s, then catch-up saccades | `[K] (M)` |
| VOR / doll's eyes | Gain ≈ 1.0, latency ~10 ms; suppressed by fixation when awake; obvious when unconscious | `[S R2-01:S68]` (H) |
| Normal lid aperture | 9–10 mm; the upper lid covers the top 1–2 mm of the iris; the lid follows vertical gaze (gain ≈ 1) | `[K] RB §5.1` |
| Blink | Close 70–100 ms, closed 0–50 ms, reopen 150–250 ms: a full spontaneous blink lasts **250–400 ms**. Reflex and incomplete blinks may be 100–250 ms (C-15) | `[K] (H) R2-06 §12.2, RB §5.2` |
| Pupil light reflex | Latency 200–300 ms; constriction ~1 s; redilation 2–4 s; consensual | `[K] (H)` |
| Hippus | ±0.2–0.5 mm at 0.2–0.5 Hz (living, awake) | `[K] RB §5.2` |
| Pathological pupil change | 0.5–1 mm/s for acute changes; minutes for herniation stages | `[E] R2-01 §14.9` |
| Tears | Basal 1–2 µL/min; reflex 10–100 µL/min; overflow beyond ~25–30 µL in the sac | `[K] R2-06 §12.4` ✓ |

### 2.3 Base states

`GCS` = Glasgow Coma Scale; `PSPI` = Prkachin–Solomon pain score (0–16) = AU4 + max(AU6, AU7) + max(AU9, AU10) + AU43, where AU43 is **binary**; game mapping PSPI ≈ 1.6 × pain (0–10) `[S R2-02:S39]` ✓.

| State | Entry condition | Upper lid (mm) | Gaze | Pupil (mm) / reactivity | Blinks | Saccades / slow movements | Face tone and droop | Jaw (mm) | FACS / PSPI | Tag |
|---|---|---|---|---|---|---|---|---|---|---|
| `ALERT` | GCS 15, stress < 0.3 | 9–10 | Fixations on targets | base 3–4, brisk; hippus | 15–20 /min (10–25), 250–400 ms | ~2–3 saccades/s, 2–15° | Tone 1; micro-motion 0.02–0.05 weight at 0.3–2 Hz; swallow every 30–120 s | 0–2 | none | `[K] R2-06 §8.4, §12` |
| `FEAR` (threat seen) | stress ≥ 0.3 and threat present | **11–12** (white above the iris) | Hypervigilant scanning 2–4 saccades/s among attacker, weapon and exits; weapon focus | base +0.5–1.5 (4–7), brisk | Suppressed (< 5 /min), then bursts | Fast | Tone 1; nostrils flare with breaths when RR > 25 | 5–10 (AU26B) | 1C 2C 4B **5D** 7B **20C** 26B 38B | `[K] (H) R2-06 §8.2` ✓ |
| `PAIN` (acute) | pain ≥ 2 | Mild 7–9; moderate squeezed 3–6; severe **shut at each burst apex** | Fixed on the wound, or shut | Pain spike +0.3–1.0 within 0.3–0.6 s, peak 1–2 s, decays over 3–10 s; stays reactive | Replaced by squeezes of 0.3–3 s | Few | Tone 1 | Clenched between cries; opens with vocalisation | Mild 4B, 6B/7B, 10A (PSPI ~3–5); moderate 4C 6C 7C 9B 10C 43B 20B 25 (PSPI ~8–11); severe 4D–E 6D 7D 9D 10D **43** 20C 25 31 21C (PSPI 13–16) | `[S R2-02:S39]` `[K⚠] R2-06 §12.1` |
| `PAIN_SUPPRESSED` (fighter, stoic) | pain ≥ 2 and mindset = trained or enraged | 6–8 | On the threat | +0.3–1.0 | Normal | Normal | Tone 1 | Set (AU31C) | 4B 7B **24C** 17B 31C; full pain face leaks for 0.3–1 s | `[K] (M) R2-06 §8.2` |
| `DAZED` / concussed / rocked | concussion timer > 0, GCS 13–14 | 7–9 | **Blank, vacant stare**; slow drift | Normal, reactive | Slow, 5–10 /min | 0.5–1 /s at peak velocity ×0.6–0.8; horizontal nystagmus p 0.3 (1–3 Hz, 2–5°); poor convergence (exophoria 2–5°) | Tone 0.6–0.8 | 2–5 | Near neutral, 26A; 1B + 4B when addressed | `[S R2-01:S97,S102]` `[E] R2-02 §6.4` |
| `SHOCK_III` | blood loss 0.30–0.40 or MAP < 65 | 5–8, heavy; eyes look **sunken** (shader 0.5–1 mm) | Vacant; poor tracking | Normal to large, **sluggish** (latency × 1.5) | 5–10 /min, slow (300–500 ms) | 0.5–1 /s | Expression AUs ≤ A; 41–42 | Open 10–20, dry lips | Grimace only when moved (× 0.3–0.6) | `[K] RB §4.9, R2-06 §8.2` |
| `STUPOR` (GCS 9–12, class IV before LOC) | loss > 0.40, CPP < 40, or herniation stage ≥ U1/C1 | 2–6; drop shut and struggle open | Roving, drifting | Variable | 0–5 /min | Roving | Tone 0.3–0.5; nasolabial folds flatten | Slack, 5–15 | Grimace to pain only | `[K] R2-04 §7.1` |
| `CORTICAL_BLIND` (overlay on alert states) | both V1 sev > 0.8 | Normal | Conjugate, **slow wander 5–20 °/s, no fixation, no tracking** | **Normal and reactive** | Normal; **no menace blink** | No target saccades | Tone 1; puzzled 1B 4B | Normal | Per emotion | `[S R2-01:S22]` (H) |
| `SYNCOPE` / anoxic LOC (transient programme; §2.5) | brain O₂ reserve ≤ 0 | **Open** (p ≥ 0.9), 6–10 | **Up 10–30° for 2–10 s** (p 0.6–0.9); downbeat nystagmus first in ~0.4 of those; back to the midline over 10–60 s | Dilating | None | Lid flutter with jerks | Tone → 0 over 0.5–2 s | Slack; chewing and lip smacking (p 0.5–0.8) | — | `[S R2-02:S26,S27]` ✓ |
| `KNOCKOUT` | α-model LOC (§3.7) | Open p 0.8, glassy (conflict C-04) | Tonic upgaze in 0.5 of open eyes, 2–10 s; then neutral or slightly divergent 5–15° | Equal, reactive | None | Doll's eyes present | Tone 0 within ≤ 100 ms | Slack; obstructed breathing when supine | — | `[E] R2-02 §6.3` |
| `SEIZURE_TONIC` | seizure (§5.4) | **Wide**, 10–12 (open p 0.9–0.97) | Forced 30–45° away from the focus, or up | **6–8, unreactive** within 1–3 s | None | Fixed | Congested; blue from 10–20 s | **Clenched** (AU31) | Grimace, 20D | `[K] R2-04 §4.1` |
| `SEIZURE_CLONIC` | seizure | Lids jerk with each beat | Deviated, jerky; epileptic nystagmus beating away from the focus | Dilated, unreactive | Eyelid clonus | — | Rhythmic grimace | **Snaps shut with each jerk** | Froth at the lips | `[S R2-01:S71]` |
| `POSTICTAL` | seizure ended | Half-closed 2–5 (closed p ~0.5) | Roving or still deviated, slightly divergent | Large, sluggish → normal over 0.5–5 min | Rare | Roving | Tone 0 → returning | Slack; obstructed breathing | — | `[K] R2-04 §4.3` |
| `COMA` (brainstem intact, GCS 3–8) | resolver coma, pons and midbrain working | Closed, or a 1–5 mm gap (lagophthalmos p 0.3–0.7); **a lifted lid closes again over 1–2 s** | Resting divergence 5–15°; **roving** 10–30° at 5–20 °/s; or ping-pong (bilateral hemispheric) cycle 3–7 s; periodic alternating gaze reverses every ~2 min (metabolic) | 2–5, reactive (diencephalic stage 1–3) | None; corneal reflex **present** | **Doll's eyes gain 1.0** | Tone 0; hemiplegic cheek puffs 3–10 mm with each breath out | 5–20 open when supine | Grimace to pain on the working side only | `[S R2-01:S66,S67]` |
| `COMA_PONTINE` | pons_teg sev > 0.5 | As `COMA` | No horizontal movement; **ocular bobbing**: fast down 5–20° at 80–200 °/s, pause ~0.5 s, slow return 1–3 s, 2–15 /min irregular | **1.0–1.5, pinpoint** (reactive only under magnification) | None; corneal **absent** | Doll's eyes absent horizontally | Tone 0 | Slack | — | `[S R2-01:S54,S57]` |
| `COMA_MIDBRAIN` | midbrain sev > 0.5 | As `COMA`; ptosis with CN III | Dysconjugate; vertical gaze lost; CN III eye down and out | **4–6 mid-position, fixed**, often irregular | None | Doll's eyes weak | Tone 0 (decerebrate episodes) | Clenched during episodes | — | `[K] R1-04 §2.2` |
| `LOCKED_IN` | both ventral pons halves destroyed, tegmentum spared | Open; **voluntary blinks** | **Only vertical movements** (0–30° up/down) answer the player; horizontal absent | Normal, reactive | Voluntary | Vertical only | **Whole face flaccid** | Slack | None | `[S R2-01:S56]` |
| `C1C3_AWAKE_APNOEA` | cord C1–C3 complete, brain intact | **Wide 11–12**, tears | Darting 2–4 saccades/s, "pleading" | Normal → dilate from 60–120 s | Normal or rapid | Fast | Terror face 1+2+5+20; mouth gapes without airflow 10–30 /min | Gaping 15–30 | Terror | `[E] R2-04 §2.2, RB §5.4` |
| `AGONAL` (after `t_arr`) | circulatory arrest | Half-open 2–6 | Fixed near the midline; moves only with the head | Start dilating at 30–45 s; **6–8 fixed by 60–120 s** | None | None; doll's eyes fading | Tone 0 | **Gapes 15–35 with each gasp**, half-closes after | — | `[K] R2-04 §3.2, §7.1` |
| `BRAINSTEM_DEAD` (heart beating) | medulla/pons destroyed or herniation stage X | **Where they were at the loss of tone**; open lids drop 2–4 mm over 1–3 s | Fixed near the midline, slightly divergent (3–10°) or skewed | **4–9, fixed** (mean 5.0 ± 0.85 `[K⚠]`) | None; corneal absent | **Doll's eyes absent**: the eyes move with the head like painted eyes | Tone 0 | Slack, 10–30 when supine | — | `[S R2-01:S73]` `[S R2-04:S17]` |
| `DEAD` | `t_dead` (arrest + 300 s), or earlier for the visuals | Distribution at death (RB §5.4): sudden death open 0.55 / half 0.35 / closed 0.10; slow death 0.20 / 0.45 / 0.35. A lifted lid **stays** | Each eye 3–10° abducted, 0–5° up; **never rolled up** | 6–8 fixed; relax to 4–6 over 2–6 h (anisocoria ≤ 1 mm) | None | None | Tone 0; **no micro-motion**; gravity sag | 10–30 within 5–30 s (supine) | None; the last expression is **not** kept | `[K] RB §5.4, R2-06 §13` |

### 2.4 Lesion overlays (per eye; composed on top of every living state)

| Overlay | Trigger | Eye(s) | Rotation offsets | Lids | Pupil | Movement limits | Head posture | Tag |
|---|---|---|---|---|---|---|---|---|
| `GAZE_DEV_DESTRUCTIVE` | FEF, large MCA territory, putamen/capsule | Both | **Toward the lesion** 15–40° (default 25°) | — | — | Doll's eyes **can** move the eyes past the midline; decays over days (constant in game) | Head turned 10–30° the same way | `[S R2-01:S63,S64]` ✓ direction |
| `GAZE_DEV_SEIZURE` | Cortical focus, while seizing | Both | **Away from the focus** 30–45° (forced version, seconds before generalisation); early non-forced turn to either side (p 0.5) | Wide | Dilated | — | Head wrenches with it | `[S R2-01:S65]` ✓ |
| `GAZE_PALSY_PONTINE` | PPRF / CN VI nucleus | Both | At rest 10–30° **away from the lesion** (toward the paralysed limbs) | — | — | Neither eye passes the midline toward the lesion, **even with doll's eyes** | — | `[K] (M) R2-01 §13.2` |
| `NEGLECT` | PPC neglect roll | Both | 20–40° toward the lesion | — | — | Saccade gain into the neglected field × 0.1–0.4 | Head turned toward the lesion | `[E] R2-01 §6.2` |
| `THALAMIC` | Thalamic sev > 0.5 | Both | **10–25° down, 5–15° in** ("peering at the nose"); wrong-way deviation (p 0.1–0.2): 10–25° away from the lesion | — | 2–3, reactive | Vertical gaze palsy when paramedian | — | `[S R2-01:S27,S29]` |
| `CN3_PALSY` | Midbrain fascicle, CN III nerve, uncal compression | Ipsi | **22–33° out (max 40°), 5–10° down (default 8°)**, slight intorsion | **Complete ptosis** (aperture 0–2 mm, lid covers the pupil); nuclear lesion: both lids | **6–9, fixed** (compressive and traumatic palsies involve the pupil) | Cannot adduct, elevate or depress | — | `[S R2-01:S49,S50]` ✓ |
| `CN6_PALSY` | Pons, petrous apex, raised ICP (often both sides) | Ipsi (both with ICP) | **6–22° in** (esotropia), worse looking toward the lesion side | — | — | Abduction stops at the midline | Face turned toward the palsied side | `[S R2-01:S51]` |
| `CN4_PALSY` | Blunt trauma (nerve), midbrain | Nerve lesion: ipsi eye; nucleus lesion: contra eye | 2–8° up, extorted | — | — | Weak depression in adduction | **Tilted away from the affected eye** | `[K] (H) R2-01 §13.1` |
| `SKEW` | Otolith pathway (vestibular nucleus → midbrain) | Both | 2–10° vertical misalignment. Pontomedullary lesion: **ipsi eye lower**; midbrain: contra eye lower | — | — | — | Tilted toward the lower eye | `[S R2-01:S61]` |
| `INO` / `WEBINO` | MLF | Ipsi (both if bilateral) | WEBINO: both eyes drift 10–20° out ("wall-eyed") | — | — | Ipsi adduction 0–50 % of normal; the abducting eye beats 2–4 Hz, 2–5°; convergence kept | — | `[S R2-01:S62]` |
| `ONE_AND_A_HALF` | PPRF/CN VI nucleus + MLF | Both | — | — | — | Ipsi eye frozen horizontally; the other eye can only abduct (with nystagmus); vertical kept | — | `[S R2-01:S52]` |
| `PARINAUD` | Tectum, hydrocephalus | Both | Hydrocephalus: tonic down 10–20° with sclera visible above the iris ("setting sun") | **Retraction** +2–3 mm (Collier sign) | 4–6: poor to light, normal to near | Upgaze range 0–10°; convergence-retraction jerks on attempted upgaze | — | `[S R2-01:S48]` |
| `HORNER` | Lateral medulla, cervical sympathetic chain, T1 cord, carotid wall | Ipsi | — | Ptosis 1–2 mm; lower lid 1 mm high ("upside-down ptosis") | **Smaller**: anisocoria 0.5–1 mm in light, up to 4.5 (mean 1.7) in dim light; dilation lag (largest ~5 s after the light goes off) | — | — | `[S R2-01:S72]` |
| `UNCAL` | Herniation U1–U2 (§1.7.3) | Ipsi, then both | Down and out as CN III fails | Ipsi ptosis | Brief constriction (5–60 s) → +1 mm, sluggish, oval → 6–9 fixed → the other pupil follows | Doll's eyes lost progressively | — | `[S R2-01:S74]` ✓ |
| `RAPD` (optic nerve) | Optic nerve sev > 0.5 | Ipsi | — | — | Equal at rest; the blind eye constricts only consensually | — | — | `[K] (H)` |
| `CN7_PERIPHERAL` | Pons (nucleus), temporal-bone fracture | Ipsi | Bell's phenomenon **visible**: the eye rolls 10–20° up and out on attempted closure (p 0.75–0.9) | **Incomplete closure, 2–10 mm gap**; lower lid sags (fissure +1–3 mm); tears spill over | — | — | — | `[K] (H) R2-06 §9.3` |
| `NYSTAGMUS` (generator) | Cerebellum (p 0.75), flocculus, vestibular, concussion (p 0.3), seizure | Both (the abducting eye only in INO) | Jerk waveform: slow drift + fast reset, 1–4 Hz, 2–10°. **Gaze-evoked**: only beyond 20–30° eccentric, fast phase toward the gaze. **Downbeat**: flocculonodular, lower medulla. **Upbeat**: pontomesencephalic. **Periodic alternating**: reverses every 90–120 s. **Peripheral vestibular** (temporal-bone fracture): fast phase **away from the damaged ear**, horizontal-torsional, damped by fixation. **Epileptic**: fast phase away from the focus. **See-saw**: parasellar | — | — | — | — | `[S R2-01:S45,S46,S71]` |

**All the ways the eyes can "cross" or misalign** `[K] R2-01 §14.7`:
1. CN VI palsy: one or both eyes turned in; both with raised ICP.
2. Thalamic lesion: both eyes down and in.
3. Skew deviation: one eye higher.
4. INO / WEBINO: eyes drift out, one lags.
5. CN III palsy: one eye out and down, lid shut.
6. Coma or death: both slightly out.
7. Concussion: poor convergence; subtle.

Behavioural consequences of misalignment (diplopia): squinting, closing one eye, head tilt, reach error +2–5 cm `[E] R2-02 §10`.

### 2.5 Transitions and timings

| Event | Onset | Build / hold | Release | Tag |
|---|---|---|---|---|
| Startle blink | EMG 20–50 ms; lid starts moving 40–60 ms; shut by 80–120 ms | Closed 100–300 ms | Then wide for 0.3–1 s; habituates: floor 0.5 × for the blink, 0.25 × for the rest | `[S R2-02:S1,S2]` ✓ ranges |
| Startle face | 60–150 ms | AU 4B 7C 20C 21C | 300–800 ms | `[E] R2-02 §1.1` |
| Fear face | 200–500 ms after the threat is seen | Sustained while the threat lasts | 0.5–2 s | `[K] R2-06 §8.2` |
| Pain face | 150–400 ms after the pain is **perceived** (not after impact when the character is unaware) | Apex 0.5–1.5 s; bursts of 1–3 s every 3–15 s; relaxes to 30–50 % between bursts | 0.5–2 s | `[E] R2-02 §9.1` |
| Pupil pain spike | 0.3–0.6 s | Peak 1–2 s | 3–10 s | `[K⚠] R2-06 §12.1` |
| Fear pupil offset | 0.5–2 s | Sustained | Minutes | `[E]` |
| Loss of consciousness, off-switch (brainstem, high cord, knockout) | ≤ 100 ms: all voluntary AUs and gaze control off | Lids stay; an open lid drops 2–4 mm over 1–3 s | — | `[K] RB §5.4` |
| Loss of consciousness, circulatory | At `reserve ≤ 0` | Upgaze 10–30° begins 0–3 s after LOC, holds 2–10 s | Drifts to near straight ahead over 10–60 s. **Never kept into `DEAD`** | `[S R2-02:S27]` ✓ |
| Hypoxic pupil dilation | 30–45 s after cerebral flow stops | 6–8 mm, fixed by 60–120 s | Relax to 4–6 over 2–6 h after death | `[K] RB §5.4` |
| Uncal pupil sequence | Stage U1 | +1 mm, sluggish over 5–15 min | Fixed 6–9 over 10–30 min; the other pupil follows at stage M | `[E] R2-01 §15.2` |
| Seizure onset | 0–1 s: eyes snap open and deviate | Pupils 6–8 within 1–3 s | Normal over 0.5–5 min after the seizure | `[K] R2-04 §4.1` |
| Waking from a knockout | Eyes open first, 5–60 s after the knockout (tail 300 s) | Blank stare 0–60 s; saccades return at ~0.5 /s; fixation on faces within 10–60 s `[E]` | Confused gaze for 5–30 min | `[K] R1-04 §3.6` |
| Tear film without blinking | Breaks up 10–30 s after the last blink | Gloss 1.0 → 0.8 in 1 min, 0.4 at 1 h | Post-mortem surface: RB §5.5 | `[K] RB §5.5` |
| Face at death | Expression releases at LOC (a tonic anoxic grimace can follow for 10–40 s) | Flaccid by ~1–1.5 min after circulatory LOC; gravity sag (cheeks 3–10 mm, lower lip 2–5 mm) | Rigor fixes it from 1–3 h | `[K] R2-06 §13` ✓ |
| Skin colour | Face and lips follow arterial SaO₂ with τ ≈ 8 s (5–15), extremities τ ≈ 20 s (15–30), both × 2 in shock | Pallor of fear 2–10 s onset, full at 20–60 s | 1–5 min | `[K] R2-06 §10.4` |

### 2.6 Face states (expression, palsy, tone, colour)

**Expression recipes** `[K] (H) R2-06 §8.2` (FACS prototypes ✓):

| State | AUs | Key cue |
|---|---|---|
| Pain scream | Severe-pain set + 27D + 20D (square mouth) | **Eyes shut** |
| Terror scream | 1D 2D 4C **5E** 20D 27D 21D 38C | **Eyes wide**, white above the iris |
| Effort (pushing up, crawling, pressing a wound) | 4C 6C 7C 9B 10B 24D or 31, 21C | Lips pressed or teeth clenched |
| Air hunger / choking | 1C 2C 5C 25 27C **38D 21D**; head extended; hands to the throat | Nostrils flared, neck cords |
| Nausea | 9B 10B 15B 17B 25A; swallows every 10–30 s; yawns | 10–120 s before vomiting |
| Crying | 1C 4C 6C 7B 15C 17C (+ 9B 10B 20B 25/26 during sobs) | Tears within 30–120 s |
| Pleading | 1D + 4C (oblique brows) 15B 20B 25 | Head tilted forward |
| Roar (fighting back) | 4D 5C 7C 9B 10C 25 27C | Upper teeth bared |
| Exhaustion (class III–IV, conscious) | 1A 4A 15A 41C | Heavy lids, slack |

- **Per-character variation** `[E] R2-06 §8.3`: one pain-face cluster per character (AU group weights ± 30 %); `pain_face_gain` 0.3–1.3; asymmetry ± 10–20 % per side per episode.

**Palsy** `[K] (H) R2-06 §9` ✓:

| Type | Side | Forehead / eye closure | Lower face | Emotional smile | At rest | Tag |
|---|---|---|---|---|---|---|
| Central (cortex, corona radiata, capsule genu) | Contra | Spared (gain 0.8–1.0) | Weak | May still move (p 0.5–0.7); thalamic/striatocapsular/medial frontal lesions show the reverse (p 0.3–0.5) | Corner 1–3 mm low; flat nasolabial fold | `[S R2-06:S4]` |
| Peripheral (pons, temporal bone) | Ipsi | Paralysed: brow 2–5 mm low; closure gap 2–10 mm with Bell's | Weak: corner 2–6 mm low; midline pulled 2–5 mm (rest) and **5–15 mm** (expression) toward the healthy side | Lost | Cheek puffs 3–10 mm on each breath out; drool and tears spill on that side | `[K] (H)` |
| Branch cut (face wound) | Ipsi | Temporal branch: AU1, AU2. Zygomatic: AU6, AU7, 43/45 weak | Buccal: 9–14, 34. Marginal mandibular: 15, 16 (the lower lip stays up in a grimace) | — | Lopsided grimace | `[K] (H)` |

- House–Brackmann grade → AU gain: I 1.0, II 0.8, III 0.6, IV 0.4 (forehead 0), V 0.15, VI 0 `[E] R2-06 §9.4`.
- **Unconscious palsy** shows only through tone: flatter side, lower mouth corner, cheek billows on expiration, less lid closure. A pain stimulus moves only the working side `[K] (H)`.

**Tone and gravity** `[E] R2-06 §13.2`:

| Orientation | Jaw | Cheeks | Lids | Tongue |
|---|---|---|---|---|
| Supine | Opens 10–30 mm (5–20 mm while alive and unconscious) | Slide 3–10 mm toward the ears | Stay; drop 2–4 mm | Falls back (obstructs the airway while alive) |
| Upright slumped | Closed or slightly open; chin on chest | Sag 3–8 mm | Drift down | Forward |
| Prone | Pressed, distorted | Pushed up and sideways | Pressure-closed or open | The tip may show between the teeth (p 0.2–0.3) |

**Colour** (driven by physiology; ramps in R2-06 §10.2 and RB §5.6):
- An exsanguinated body turns **white-grey with grey-lilac lips (#A99AA4), never blue** `[K] (H)`.
- Cyanosis becomes visible when Hb × (1 − SaO₂) ≥ 2.5–3.0 g/dL (arterial). **Central** cyanosis turns the tongue blue; **peripheral** cyanosis leaves it pink `[K] R2-04 §8.2` ✓.
- Congested purple face with petechiae: tonic seizure, strangulation, traumatic asphyxia.
- Flush: Cushing phase, anger, straining.

### 2.7 Player interactions with the eyes and face

| Interaction | Alert | Coma, brainstem intact | Brainstem failed / dead | Tag |
|---|---|---|---|---|
| Shine a light | Constricts in 200–300 ms, consensual | Constricts (unless CN III / midbrain is hit) | Fixed | `[K] (H)` |
| Lift a lid | Resists; blinks | **Closes again slowly over 1–2 s** | **Stays up** | `[K] RB §5.4` |
| Turn the head | Eyes follow the head (fixation suppresses VOR) | **Eyes counter-rotate** and keep "looking at the ceiling" | **Eyes move with the head** | `[S R2-01:S68]` (H) |
| Touch the cornea | Blink, both eyes | Blink (corneal reflex present); Bell's roll on forced closure | None | `[K] (H)` |
| Thrust an object at the face | Menace blink, head turns away in 100–250 ms | None | None | `[K] R2-02 §8` |
| Pain stimulus (nail bed, supraorbital notch) | Withdraws, grimaces, cries out | Grimace (working side only if palsied), moan (V2), withdrawal or posturing | Nothing | `[K] R2-06 §9.6` |
| Press a nail bed (capillary refill) | ≤ 2 s (men), 2.5–3 s (women), 3–4.5 s (elderly); +1–2 s in the cold | Per shock class: 3–4 s (class III), > 4–5 s (class IV) | No active refill; unfixed livor re-colours slowly and passively | `[K] (H) R2-06 §10.5` ✓ |

### Simulation parameters (eye and face controller)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `lid_aperture` alert / fear / shock / stupor / coma gap | 9–10 / 11–12 / 5–8 / 2–6 / 1–5 | mm | | `[K] RB §5.3, R2-04 §7` |
| `blink_rate` alert / threat / shock / coma / dead | 15–20 / < 5 then bursts / 5–10 / 0 / 0 | /min | Poisson, minimum interval 1 s | `[K] R2-06 §12.2` |
| `blink_duration` spontaneous / reflex or incomplete / shock | 250–400 / 100–250 / 300–500 | ms | C-15 | `[K] RB §5.2, R2-06 §12.2` |
| `saccade_duration` | 21 + 2.2 × amplitude | ms | Peak 400–700 °/s | `[K] (H)` ✓ |
| `saccade_rate` fear / dazed, shock | 2–4 / 0.5–1 | /s | | `[E] R2-06 §12.3` |
| `pupil_pain_spike` | +0.3–1.0; latency 0.3–0.6 s; peak 1–2 s; decay 3–10 s | mm | Conflict C-03 | `[K⚠] R2-06 §12.1` |
| `pupil_fear_offset` | +0.5–1.5 | mm | | `[E]` |
| `pupil_pontine` / `midbrain` / `blown` / `brain_death` | 1–1.5 / 4–6 fixed / 6–9 fixed / 4–9 fixed | mm | | `[K] R2-01 §14.4` |
| `pupil_hypoxic` | start 30–45 s; 6–8 by 60–120 s | — | | `[K] RB §5.4` |
| `syncope_upgaze` | p 0.6–0.9; 10–30°; 2–10 s; return over 10–60 s | — | Conflict C-05 (RB p 0.6–0.8) | `[S R2-02:S27]` |
| `ko_eyes_open_p` | 0.8 (RB: 0.5) | p | Conflict C-04 | `[E] R2-02 §6.3` |
| `gaze_bias_destructive` / `seizure` / `pontine` | +15–40 / −30–45 / −10–30 | ° (relative to the lesion) | | `[S R2-01:S63,S65]` |
| `cn3` / `cn6` / `cn4` / `skew` | out 22–33, down 5–10, ptosis 100 %, pupil 6–9 / in 6–22 / up 2–8 / vertical 2–10 | ° / mm | | `[S R2-01:S50,S51]` `[K]` |
| `bobbing` | down 5–20° at 80–200 °/s; pause 0.5 s; return 1–3 s; 2–15 /min | — | Single-case kinematics, randomise | `[S R2-01:S54]` (L) |
| `roving` / `pingpong_cycle` | 10–30° at 5–20 °/s / 3–7 s (1.5–8) | — | | `[S R2-01:S67]` |
| `nystagmus` | 1–4 Hz, 2–10° jerk | — | | `[E]` |
| `dolls_gain` | 1 (brainstem intact, unconscious); 0 (failed) | — | | `[S R2-01:S68]` (H) |
| `dead_eye_rest` | 3–10° abducted, 0–5° up | ° | | `[K] RB §5.4` |
| `lid_drop_at_tone_loss` | 2–4 over 1–3 s | mm | | `[K] RB §5.4` |
| `facs_weights` | A 0.10 / B 0.30 / C 0.50 / D 0.75 / E 0.95 | — | | `[E] R2-06 §0.3` |
| `pspi_from_pain` | 1.6 × pain; AU43 binary | — | | `[S R2-02:S39]` ✓ |
| `micro_motion_face` | 0.02–0.05 at 0.3–2 Hz; living only | weight | | `[E]` |
| `cheek_puff_paralysed` | 3–10 | mm per expiration | Strongest when unconscious | `[K] (H)` |
| `colour_lag_face` / `extremity` | 8 (5–15) / 20 (15–30), × 2 in shock | s | | `[K] R2-06 §10.4` |

### Visual/behavioural checklist (eye and face controller)
- A frightened character shows white above the iris and darts its eyes between attacker, weapon and exits. A hurt character squeezes its eyes shut at each wave of pain.
- A character with a destroyed right frontal eye field looks persistently to the right; turning its head moves the eyes past the midline. During a seizure from the same wound, the eyes and head wrench to the left.
- One droopy eyelid, lifted by the player, shows an eye turned down and out with a large fixed pupil.
- Deep coma with a working brainstem: when the head is turned the eyes keep pointing at the ceiling. After brainstem failure they turn with the head.
- A fainting or heart-shot character's eyes roll up for a few seconds at collapse, then settle. A dead character's eyes are never rolled up; they look roughly ahead and slightly outward, lids part-open, pupils wide.
- A lifted eyelid drifts shut on an unconscious living face and stays up on a dead one.
- A bled-out face is white with grey-lilac lips; a suffocating one turns blue, including the tongue.

---

## 3. Reaction system

### 3.1 Layers

| Layer | What it is | Latency after t = 0 | Present when unconscious? | Tag |
|---|---|---|---|---|
| **L0 Physics** | True impulse at the hit point (never multiplied) | 0 | Yes | `[E] R2-02 §1.3` |
| **L1 Reflex** | Startle, blink, nociceptive withdrawal, grip clench | EMG 20–150 ms; visible 50–250 ms | Startle: no. Spinal withdrawal: sometimes (light coma, cord intact below) | `[S R2-02:S1,S37]` |
| **L2 Postural** | Ankle, hip and stepping strategies | EMG 73–110 ms; recovery-step toe-off 0.22–0.35 s | No | `[S R2-02:S19,S20]` |
| **L3 Protective** | Arms to break a fall, shielding, hand to wound, turning away | 100–200 ms (arms in a fall) to 300–1,000 ms (hand to wound) | No | `[S R2-02:S25]` |
| **L4 Behavioural** | Stop, fight, flee, surrender, freeze, wound check, speech | 0.3–3 s × `rt_mult` | No | `[E] R2-02 §2` |
| **L5 Physiological clock** | CNS destruction (0 s), cerebral hypoperfusion (8–15 s after the heart is destroyed), exsanguination (minutes) | 0 s to hours | n/a | RB §4 |

**Master rule** `[K] R2-02 §0.4`:
- When consciousness is lost, L2–L4 go to zero within ≤ 100 ms. A held posture collapses unless posturing, fencing or a seizure replaces it.
- L1 spinal reflexes below an intact cord segment can persist.
- Reflex overlays are **additive** and never block a fall.

### 3.2 Inputs

- **Hit record** (RB §2.0): region; structure flags (bone, joint, artery, nerve, cord level, organ); weapon; direction; momentum `p`; deposited energy.
- **Energy class** `[G]` on R2-02 §11.1:

  | Class | Examples |
  |---|---|
  | **E0** | Near miss, no contact |
  | **E1** | .22 LR, untrained punch (< 1,500 N), light kick, knife slash |
  | **E2** | Handgun, trained punch, hammer, kick, knife stab |
  | **E3** | Rifle, shotgun ≤ 5 m, stomp on a head on the floor |

- **Conscious state**: GCS band (§1.5.7); `arousal` 0–1; `aware_of_hit`.
- **Mindset**: rolled at spawn (§3.6).
- **Deficit channels**: §1.4.
- **Locomotion**: standing, walking or running; which leg is loaded; armed; finger on the trigger.
- **Physiology**: MAP, brain O₂ reserve timer, per-leg `leg_capacity` (0–1), shock class.

### 3.3 Behaviour primitives

| Primitive | Layer | Trigger | Latency | Duration | Kinematics and parameters | Tag |
|---|---|---|---|---|---|---|
| `FLINCH` (startle) | L1 | Any hit, nearby shot, sudden touch or pain; conscious | Visible: blink 40–60 ms; head duck 90–130; arms 120–160; trunk 130–180; knees 140–200 ms | Peak 200–450 ms; release 300–800 ms | Head flexion 5–15°, shoulders up 10–25 mm, upper arms abducted 5–20°, elbows +10–30°, forearms pronated 10–20°, fists, trunk flexion 3–10°, knees 5–15°, CM −10 to −30 mm. Amplitude × habituation (1.0, 0.6, 0.45, 0.35, floor 0.25; blink floor 0.5; recovery τ 20–60 s) × (1 − 0.5·arousal). **Always a flexion, never in the bullet's direction** | `[S R2-02:S1,S2,S3,S4]` `[E]` |
| `GRIP_CLENCH` | L1 | Startle or sudden balance loss while armed with the finger on the trigger | 60–120 ms | — | Involuntary discharge p 0.05–0.2 | `[E] R2-02 §1.1` |
| `LIMB_FLICK` | L0 | Projectile or blow on a segment | 0 | 20–50 ms | Δv = p·f_ret / (m_seg·k_attach), k_attach 1.5–3. A 9 mm stopping in the forearm gives ~1.2 m/s, a 3–6 cm flick. A retained 9 mm in the head gives a 1–3° nod | `[E] R2-02 §1.3` ✓ |
| `WITHDRAW` | L1 | Cut, stab or burn of a limb | EMG ~100 ms (leg 90–130; arm 10–30 ms shorter); visible yank 150–250 ms. Heat: 0.2–0.6 s after flame contact | 150–300 ms | Cut: limb moves 5–20 cm. Burn: hand snatched 20–40 cm in 200–300 ms. Needs an intact cord segment; none during spinal shock | `[S R2-02:S37]` ✓ RIII |
| `WOUND_CHECK` | L4 | Hit noticed | Look down 0.3–1.0 s | Touch 0.4–1.2 s; look at the hand 1–2 s | Then the emotional reaction. Needs a free working hand | `[K] [E] R2-02 §2.4` |
| `CLUTCH` / `REACH_FOR_WOUND` | L3 | Wound noticed | Torso 0.4–0.8 s; face 0.3–0.6 s; **neck: both hands 0.3–0.8 s** | While conscious | IK reach 150–300 ms; press 5–20 N; nearest working hand; the interscapular back is unreachable. p 0.7–0.9 (torso, neck, face), 0.4–0.6 (limb); 0 on a neglected side. Own-hand pressure reduces flow × 0.3–0.7 (RB §4.10) | `[S R2-02:S43]` `[E]` |
| `SHIELD` | L3 | Visible blade or weapon, looming object, repeated blows | 0.2–0.4 s after the threat is seen; head avoidance 100–250 ms | While the threat lasts | Forearms up in front of the face and chest, palms out or crossed, head down and turned, trunk sideways, stepping back; sometimes grabs the blade or wrist. p 0.5–0.8 | `[S R2-02:S65]` `[E]` |
| `PROTECT_HEAD` | L3 | Blows to the head, backward fall | 100–200 ms | — | Forearms around the head, elbows 120–140°, shoulders 90–120° flexed, chin tuck 20–40° | `[K] R2-03 §7.6` |
| `TURN_AWAY` | L3/L4 | Threat, shot, heat or flash | Head 100–250 ms; body 180° in **0.26–0.54 s** | — | Explains wounds in the back and back of the head | `[S R2-02:S12]` (M) |
| `DOUBLE_OVER` | L3 | Abdomen, groin, winded | Hands to the wound 0.4–0.8 s | Seconds | Hip and trunk flexion 20–60° (up to 90°); knees bend | `[K] R2-02 §3` |
| `STAGGER(n)` | L2 | XcoM leaves the base of support | Toe-off 0.22–0.35 s (× 1/`leg_capacity` when injured) | Each step 0.25–0.40 s | n by excess XcoM velocity: < 0.3 m/s → 1 step, recover p 0.9; 0.3–0.8 m/s → 2–3 steps, recover p 0.6; > 0.8 m/s or `leg_capacity` < 0.5 → 3–6 lurching steps, fall p 0.5–0.9. Step length 0.3–0.7 m × capacity; heading noise ±20–40°; crossover in 0.5 of weak multi-step lateral responses; arms windmill 60–120° at 1–2 Hz. Single-step lean limit 23.5° + 8.7° × capacity | `[S R2-02:S19,S20,S21,S22]` `[E]` |
| `LEG_BUCKLE` | L0/L2 | Fracture of femur, tibia, pelvis or knee; femoral nerve; paralysed leg; knee demand > capacity | Loaded leg 0.1–0.3 s; unloaded: at the next stance, 0.2–0.5 s | Knee to 90° in 0.3–0.6 s | Falls toward the injured side; hop on the good leg p 0.3–0.5 (1–3 hops of 0.3–0.5 s) | `[E] R2-02 §3, R2-03 §3.2` |
| `DROP` | L0–L5 | See archetypes A–G (§4.5) | — | — | Conscious drops protect; unconscious drops do not | §4.5 |
| `KNOCKOUT` | L1/L5 | α model (§3.7) | Tone lost ≤ 100 ms | LOC 5–60 s (tail 300) | Variants: limp 0.3 / fencing crumple 0.5 / plank 0.2 (plank 0.4–0.6 if the knees are locked) | `[S R2-02:S33,S35]` `[E]` |
| `FENCING` | L1 (brainstem) | Knockout (p 0.66) | At impact | 2–10 s (≤ 20), then 0 over 0.5–1 s | Arm on the side the face turned: shoulder flexion 60–120°, elbow 0–20°. Other arm: elbow 90–120°. ω 12–16 rad/s | `[S R2-01:S99]` ✓ |
| `WRITHE` | L3/L4 | Conscious, on the ground; colic-type visceral pain, burns | 0.5–2 s | While the pain lasts | Smooth noise targets 0.2–1.0 Hz: hips and knees 20–60°, spine 10–30°, arms reaching; ω 5–8; bursts on pain spikes; breath-holds 1–5 s | `[S R2-02:S42]` ✓ `[E]` |
| `LIE_STILL` | L4 | Peritoneal irritation, fractures, chest-wall pain, shock | — | — | On the back with knees drawn up (peritonitis); any movement draws a pain spike | `[S R2-02:S42]` ✓ |
| `CURL` (foetal) | L3 | Repeated blows, abdominal or groin pain | 0.5–1.5 s | — | Hips 90–120°, knees 100–140°, spine flexion 30–60°, arms around the head or abdomen | `[K] R2-03 §7.6` |
| `CRAWL` | L4 | Legs useless, threat present or exit visible | 1–5 s after landing | Minutes | Pulls with the forearms, 0.1–0.3 m/s; rests 5–20 s every 2–5 m; a broken leg drags, rotated outward and bent at the fracture; blood trail | `[E] R2-04 §9.2, R2-05 §8.6` |
| `CONTROLLED_DESCENT` | L4 | Conscious weakness, dizziness, breathlessness, pain, surrender | 0.5–3 s | Kneel or sit 1–5 s; lie 2–10 s | Hand on a wall or knee; head impact < 1 m/s | `[K] R2-02 §5.1` |
| `FREEZE` | L4 | Threat or first hit | 0.3–0.5 s | 0.5–3 s | Fixed stare, reduced sway. Tonic immobility p 0.02–0.1 (seconds to hours: stiff, eyes open, not speaking) | `[S R2-02:S44]` `[E]` |
| `HOLD_NECK` | L3 | Neck wound | 0.3–0.8 s | Until LOC | Both hands clamp; blood wells between the fingers; the hands fall away at LOC and the flow rises again | `[E] R2-02 §3, R2-04 §10.3` |
| `HANDS_TO_FACE` | L3 | Eye, face cut, face burn | 0.2–0.5 s | Seconds | Eyes shut, turns away, bends forward | `[K] R2-02 §3` |
| `CRADLE_ARM` | L3 | Humerus or shoulder fracture, radial palsy | 0.2–1 s | While conscious | The other hand holds the wrist or forearm against the belly; shoulder hunched | `[K] R2-02 §3` |
| `TRIPOD` | L4 | Chest wall or lung wound, air hunger | 1–10 s | 10–60 s, then sits or kneels | Hands on the knees, leaning forward; RR 25–40 | `[K] R2-02 §3` |
| `DRAIN_FORWARD` | L4 | Blood in the mouth, jaw or face wound | 1–3 s | While conscious | Sits up and leans forward, refuses to lie back; spits every 5–30 s | `[K] (H) R2-04 §2.5` |
| `HAND_TO_THROAT` | L4 | Airway blood, obstruction, air hunger | 0.5–2 s | — | Pulls at the collar; p 0.7–0.9 | `[E] R2-04 §7.5` |
| `CATCH_FALL` | L3 | Fall predicted (pre-armed when P(fall) > 0.5) | Arm burst ~100 ms; oriented < 200 ms (p ~0.9, young and alert) | Until contact | Shoulders flexed 60–100°, elbows 10–30°, wrists extended 60–90°, fingers spread; elbows **yield 20–60°** on contact (ω 4–6); head turned 30–60° away (forward fall) or chin tucked (backward fall) | `[S R2-02:S25]` `[E]` |
| `GRAB_SUPPORT` / `CLINCH` | L2/L3 | Support within reach, or the attacker | Arm EMG ~100 ms; reach 200–400 ms | — | Wall, rail, person or attacker | `[K] R2-02 §4.1` |
| `PLUCK` | L5 | Confusion, hypoxia, class III–IV | — | 1–3 s bouts every 10–60 s | Fumbling, picking at clothes; p 0.2–0.4 | `[E] R2-04 §7.5` |

### 3.4 Reaction selection by hit location

Defaults are for a **conscious, alert, committed attacker** with **E2** energy. Modifiers follow in §3.5–§3.6. "Fall" is P(on the ground within 2 s) before mindset multipliers `[E] R2-02 §3`.

**Head and neck**

| # | Region / structure | 0–0.5 s effect | Reaction chain (latencies) | Fall (archetype) | Weapon drop p | Tag |
|---|---|---|---|---|---|---|
| 1 | Brainstem, C1–C2 | Tone lost ≤ 100 ms; grip opens 0.1–0.5 s | None | 1.0 (A; B p 0.3–0.6 for midbrain) | 1.0 | `[K] R1-04 §2` |
| 2 | Cerebral hemisphere (handgun) | Concussive collapse (awake at 10 s p 0.1–0.3; transient LOC 5–120 s); motor strip or capsule → contra hemiplegia | If awake: confused, hand to head 0.3–0.8 s, falls toward the paralysed side | 0.7–0.9 (A, or D toward the paralysed side) | From hand sev (§1.5.1) | `[K] R1-04 §3, RB §4.5` |
| 3 | Scalp graze / tangential skull | Stun; brief LOC possible | Hand to head 0.3–0.8 s; blood reaches the eyes in 5–30 s → blinking, wiping | 0.3–0.6 | 0.1–0.3 | `[E] R2-02 §3` |
| 4 | Head, blunt (fist, kick, hammer) | α model (§3.7) | Rocked, knocked out, or flinch and guard | P_LOC | 1.0 on LOC | `[E] R2-02 §6` |
| 5 | Eye / orbit | Pain, loss of vision on that side; blepharospasm; tearing | Both hands over the eye 0.2–0.5 s; turns away, bends forward; oculocardiac reflex (HR −20–40 %, nausea, faint possible) | 0.3–0.5 (psychological) | 0.3–0.5 | `[K] R2-02 §3, R2-05 §5.5` |
| 6 | Nose | Reflex tearing (eyes glisten in 1–5 s, tears run by 10–30 s); eyes shut | Hand to the nose; head tilts; spits blood | 0.1–0.2 | 0.1 | `[K] R2-06 §12.4` |
| 7 | Mandible | Mouth sags open. Bilateral fracture → flail front jaw, tongue falls back when supine | Drools blood, leans forward to drain, hand under the jaw, speech lost | 0.2–0.4 | 0.2 | `[K] R2-02 §3, R2-05 §4` |
| 8 | Lower face avulsion (E3) | Airway threatened when supine | **Often conscious** (p 0.7–0.9 if the track is in front of the skull base): leans forward, grunts with blood bubbling at the mouth, spits teeth and blood, fights to sit up if pushed onto the back | 0.3 | 0.5 | `[K] R2-05 §4.4` |
| 9 | Neck vessels | Arterial jet or venous pour | `HOLD_NECK` 0.3–0.8 s; panic; flees or fights. Carotid with poor collaterals (p 0.2–0.3): contra weakness, face droop, aphasia (left carotid), eyes toward the cut side at 5–30 s | Controlled descent as MAP falls (RB §4.7) | 0.5 | `[E] R2-04 §10.3` |
| 10 | Larynx / trachea | Air leak | Coughs spraying blood; bubbling at the wound; mouths words without airflow below the cords (aphonic); subcutaneous emphysema over minutes | 0.2–0.4 | 0.3 | `[K] R2-02 §3` |
| 11 | Cervical cord C3–C7 | Quadriplegia below the level | Awake; cannot move below the level; C5: "arms up" posture | 1.0 (A-like, awake, no catch below C5–C7) | 1.0 below C7 | `[K] R1-04 §6` |

**Trunk and spine**

| # | Region / structure | 0–0.5 s effect | Reaction chain (latencies) | Fall (archetype) | Weapon drop p | Tag |
|---|---|---|---|---|---|---|
| 12 | Thoracic / lumbar cord | Legs flaccid ≤ 100 ms | Arms fling out and catch; pushes up; "I can't feel my legs"; burning band of pain at the level; drags with the arms | 1.0 (E) | 0.1–0.3 | `[S R2-02:S46]` |
| 15 | Chest wall / lung | Sharp pain on every breath | Breath-hold, then RR 25–40 splinted; hand flat over the wound; cough (blood after 5–60 s); short phrases; `TRIPOD` → sits or kneels | 0.2–0.4 now; 0.6 within 60 s | 0.1–0.3 | `[S R2-02:S49]` `[K]` |
| 16 | Heart / great vessels | BP collapses in 2–4 beats | Continues per mindset; the §3.8 heart clock | Hypoperfusion sag (G) at 8–15 s | 1.0 at LOC | `[S R2-02:S5]` ✓ |
| 17 | Upper abdomen (liver, spleen, stomach) | Reflex guarding | `DOUBLE_OVER` 20–60°, hands 0.4–0.8 s, knees bend, turns away; right-shoulder (liver) or left-shoulder (spleen) pain | 0.3–0.6 (kneel or sit) | 0.2 | `[K] R2-02 §3` |
| 18 | Lower abdomen / bowel | Dull visceral pain | May carry on for seconds to minutes; then guards, hunches, `LIE_STILL` with knees up | 0.2–0.4 | 0.1 | `[K]` |
| 19 | Groin / genitals | Severe visceral pain peaking at 0.5–2 s | Knees together, both hands to the groin, **drops to the knees in 0.5–2 s**; nausea or vomiting at 30–120 s | 0.6–0.9 | 0.6 | `[K] [E]` |

**Limbs**

| # | Region / structure | 0–0.5 s effect | Reaction chain (latencies) | Fall (archetype) | Weapon drop p | Tag |
|---|---|---|---|---|---|---|
| 13 | Shoulder / humerus fracture | The arm cannot be held against gravity and drops | `CRADLE_ARM`; leans toward the injured side; wrist drop from radial palsy (p 0.2–0.3, wrist and fingers hanging at 40–70°) | 0.1–0.3 | 0.7–0.9 | `[S R2-02:S47]` (⚠ source) |
| 14 | Forearm / hand | Flick; grip fails with tendon, nerve or bone damage | Hand pulled to the chest; stares at it; shakes it; tucks it into the armpit | 0.05–0.15 | Bone, tendon or nerve 0.6–0.9; muscle only 0.1–0.3 | `[E] R2-02 §3` |
| 20 | Pelvis, hip joint | Cannot bear weight on that side | The leg gives way; falls toward the injured side; can crawl | 0.8–0.95 (D) | 0.3 | `[S R2-02:S48]` |
| 21 | Femoral shaft | **Loaded: gives way within the stance, 0.1–0.3 s**; mid-thigh angulation 10–30°; shortening 2–5 cm; foot turned out 45–90° | Grabs the thigh with both hands; every movement brings a pain spike (vocal gating §3.6); later drags the leg | 0.85–0.95 loaded (D); unloaded at the next step | 0.3 | `[S R2-02:S48]` `[K]` |
| 22 | Thigh muscle only | Pain, "dead leg" | Limps; may keep running; hand to the thigh | 0.1–0.3 | 0.05 | `[E]` |
| 23 | Knee joint | Buckles into flexion; cannot straighten | Falls onto that knee and holds it | 0.6–0.8 | 0.2 | `[E]` |
| 24 | Tibia / fibula | Cannot bear weight; the foot flops | Falls; holds the shin | 0.7–0.9 loaded | 0.2 | `[E]` |
| 25 | Ankle / foot | Intense pain | Hops on the good leg; limps | 0.3–0.5 | 0.05 | `[E]` |
| 26 | Sciatic nerve (buttock, back of thigh) | Foot drop, weak knee flexion | Partial collapse; drags the foot | 0.4–0.6 | 0.05 | `[K]` |
| 27 | Femoral nerve (groin, front of thigh) | Quadriceps paralysed | Knee buckles on the next loaded step; stands only with the knee locked back, a hand pushing on the thigh | 0.6–0.8 | 0.1 | `[K] (H) R2-02 §3` |

**Blunt body blows**

| # | Region / structure | 0–0.5 s effect | Reaction chain (latencies) | Fall (archetype) | Weapon drop p | Tag |
|---|---|---|---|---|---|---|
| 28 | Liver (punch or kick to the right lower ribs) | Severe pain; conscious | **Collapse 1–3 s after the blow**: clutches the right side, drops to the knees, curls on the side, cannot rise for 10 s to minutes | p 0.2 at 1,500 N → 0.7 at 3,500 N | 0.5 | `[S R2-02:S55]` (L) |
| 29 | Solar plexus ("winded") | Diaphragm spasm | Bent over; failed gasps without airflow 5–30 s (up to 120), then a sudden deep inhalation; panic | 0.3 | 0.3 | `[S R2-02:S55]` (L) |
| 30 | Ribs (blunt) | Sharp pain; a fracture hurts on every breath | Holds the side, shallow breaths, avoids twisting | 0.1 | 0.1 | `[K]` |
| 31 | Kidney / flank | Deep pain after 0.5–1 s | Arches away from the blow; hand to the back | 0.1–0.2 | 0.1 | `[K]` |

**Blades, burns and other cases**

| # | Region / structure | 0–0.5 s effect | Reaction chain (latencies) | Fall (archetype) | Weapon drop p | Tag |
|---|---|---|---|---|---|---|
| 32 | Knife slash, limb | Withdrawal EMG ~100 ms | Yank visible 150–250 ms; the other hand grabs 0.2–0.5 s; looks 0.5–2 s; pain face; `SHIELD` if the blade is visible | 0.05 | 0.3 (hand) | `[S R2-02:S37]` `[E]` |
| 33 | Knife slash, face | Eyes shut | `HANDS_TO_FACE` 0.2–0.5 s; turns away; bends forward; eyebrow blood blinds that eye within seconds | 0.1–0.2 | 0.2 | `[E]` |
| 34 | Knife stab, torso | Minimal flinch, felt as a punch | Unaware p 0.3–0.6 (back 0.4–0.6); discovery after a median 5–10 s; several stabs may land before the victim looks down | Per organ | 0.1 | `[S R2-02:S16]` (anecdotal) |
| 35 | Flame on skin | Pain threshold 43–45 °C | Withdrawal 0.2–0.6 s after contact; second pain +0.6–1.0 s (hand) or +0.2–0.5 s (face); hand shaken, blown on, tucked; face: eyes shut, head wrenched away in 100–250 ms, hands up. **Restrained**: violent struggle and arching, breath-paced screams (one per 1.5–4 s), vasovagal faint p 0.05–0.1 after 10–60 s | 0.1 | 0.5 | `[S R2-02:S37,S38]` |
| 36 | Near miss (E0) | Startle | Duck, turn, then flee 0.4 / freeze 0.3 / duck-and-cover 0.3 (non-combatant) | 0 | Grip clench | `[E]` |
| 37 | Any hit while **unconscious** | L0 only | Spinal withdrawal of the struck limb 100–250 ms, p 0.2–0.5 at GCS M ≥ 4; posturing burst p 0.5 at M2–M3 (latency 0.2–1 s); nothing at M1 | — | — | `[K] R2-02 §11` |
| 38 | Any hit on a **dead** body | L0 only | Nothing active. Local muscle bulge 5–20 mm p 0.1–0.3 per direct muscle hit up to ~2 h after arrest; loose limbs, head and jaw swing and settle | — | — | `[K] R2-04 §5.5` |

**Energy scaling** `[G]` on R2-02 §1.3 and R2-05 §8:
- **E1**: bone-failure rows (13, 20, 21, 24) × 0.5–0.7 (fewer fractures); psychological stop × 0.8.
- **E3**: bone rows 1.0 with comminution; near-amputation of the hand, forearm or lower leg at contact to 1 m (shotgun); the lung row gains a sucking wound when the defect is ≥ 10–13 mm.
- **Momentum never changes the reaction direction** (§3.9).

### 3.5 Modifiers from conscious state and deficits

| Modifier | Effect on the layers | Parameters | Tag |
|---|---|---|---|
| Unconscious (any cause) | L0 only; row 37; posturing and seizure programmes if active | Tone per §4.4 | `[K]` |
| Stupor (GCS 9–12) | No wound check, no speech; grimace, moan and withdrawal to pain; `PLUCK` | Latency × 2–3 | `[K] R2-01 §19` |
| Dazed / rocked | Flinch p 0.3–0.6; guard dropped; blank stare p 0.05–0.3; knee buckle 0.1–0.3 /s during the first 10 s | `rt_mult` 1.3–1.8; severe phase 5–60 s, residual 5–30 min | `[E] R2-02 §6.4` |
| High arousal (fight or flight) | Flinch × (1 − 0.5·arousal); conscious pain behaviour × `pain_gain` = clamp(1 − 0.7·arousal, 0.2, 1) | — | `[E]` on `[S R2-02:S6,S15,S17]` |
| Unaware of the hit | No L4 reaction until discovery; L1 still fires | §3.6 | `[E]` |
| Hemiplegia | No protective arm or hand-to-wound on the paralysed side; falls toward it (fall p × 3 for perturbations toward that side) | Paralysed side tone §1.5.2 | `[E] R2-02 §10` |
| Neglect (usually the left side) | Ignores wounds, threats and hits on the neglected side; does not look there | `hold_wound_p` 0 on that side; stimulus gain × 0.1–0.4 | `[S R2-01:S17]` `[E]` |
| Aphasia | Speech replaced by moans, jargon or no speech; swearing kept | Vocal set §1.5.4 | `[K]` |
| Frontal / diffuse / concussion | Late, inappropriate, perseverative reactions | `rt_mult` 1.3–3.0; inappropriate p 0.1–0.4; perseveration p 0.2–0.5 per decision | `[E] R2-02 §10` |
| Cerebellar | Reaching for the wound overshoots 3–10 cm with a 3–5 Hz tremor; ataxic stagger; vomiting | §1.5.3 | `[S R2-01:S44]` |
| Diplopia / one eye blind | Reach error +2–5 cm; head tilt; closes one eye | — | `[E]` |
| Cortical blindness / hemianopia | No reaction to threats in the blind field; startle to a nearby shot still present | Vision mask | `[S R2-01:S22]` |
| Cord level | Below the level: no withdrawal, no pain behaviour, no protection | Spinal shock 0–24 h | `[S R2-02:S46]` |
| Seizure / posturing | Replaces all protective behaviour; stimuli trigger posturing | §1.8, §5.4 | `[K]` |
| Shock class III / IV | Wound check slow; controlled descent; vocal effort capped | Strength 0.4–0.6 / 0.1–0.3 | `[E] R2-03 §5.5` |

### 3.6 Psychological stop, awareness and vocal gating

**Mindset** (rolled at spawn) `[E]` calibrated on `[S R2-02:S8]` (M):

| Mindset | P(stop within 3 s of the first handgun torso hit) | P(stop per later hit) | P(never stops until physiology fails) |
|---|---|---|---|
| Surprised non-combatant | 0.7–0.9 | 0.8 | ~0.02 |
| **Committed attacker (baseline)** | **0.35–0.45** | 0.25 | **0.13–0.17** |
| Enraged or stimulant-intoxicated | 0.10–0.20 | 0.10 | 0.4 |
| Trained and motivated | 0.10–0.20 | 0.10 | 0.5 |

- **Multipliers** `[E]`:
  - × 1.5 when the character sees a lot of its own blood;
  - × 1.3 for a face or genital wound;
  - × 1.3 when a limb stops working;
  - × 0.5 while unaware of the hit;
  - × 0.3 while grappling.
- **Validation target**: ~2 handgun hits to stop on average (1.4–2.5 by calibre); 47 % stopped by the first 9 mm hit; 13–17 % never stopped `[S R2-02:S8]` ✓ (M).
- **Stop forms (non-combatant)** `[E]`: sit, kneel or lie down 0.40; flee 0.25; freeze 0.15; surrender 0.10; deliberate "felled" drop 0.10. For committed attackers, shift weight toward flee and surrender.
- **Vasovagal faint** `[E]` on `[S R2-02:S26,S63]`:
  - p 0.02–0.05 for a non-combatant who sees its own blood or bone;
  - prodrome 10–60 s: pallor, sweat, yawning, "I feel sick", greying vision;
  - flaccid crumple, LOC 12.1 ± 4.4 s;
  - recovers once horizontal, unless also bleeding.

**Awareness** `[E]` on `[S R2-02:S16,S18]`:

| Situation | P(unaware for > 3 s) | Discovery latency | Discovery triggers |
|---|---|---|---|
| High arousal, torso or limb hit, no bone, joint or nerve damage | 0.3–0.5 | Lognormal, median 5 s, P90 60 s | Sees blood; warmth and wetness; loss of function; weakness; told "you're bleeding"; arousal falls |
| Low arousal, same wound | 0.05–0.15 | Median 2 s | Same |
| Bone, joint, face, genitals, or loss of function | ≤ 0.05 | — | Function loss |
| Stab to the back or flank | 0.4–0.6 | Median 10 s, up to minutes | Feels "a punch"; notices later |

**Vocal gating** `[E] R2-06 §6.3`:
- P(vocalise) per pain spike = clamp(0.15 × (pain − 2), 0, 0.95) × expressivity.
- × 0 while unaware. **A gunshot or stab pain spike fires at discovery, not at impact.**
- × 0.5 in fighter mode or class III; × 0.2 in class IV; 0 when winded, apnoeic or unconscious.

### 3.7 Blunt blows to the head: the α model

| Step | Rule | Tag |
|---|---|---|
| Rotational acceleration | α_peak = F × r_eff / I_eff, with r_eff 0.065 m and I_eff 0.035 kg·m² (calibrated on 3,427 N → 6,343 rad/s²) | `[S R2-02:S28,S29]` `[E]` |
| Location multiplier | Side of the jaw 1.0; chin (uppercut) 0.9; temple 0.9; back of the head 0.6; straight to the forehead 0.5 | `[E]` on `[S R2-02:S31,S34]` |
| Force reference | Untrained bare knuckle 500–1,500 N (α ≈ 900–2,800); trained 2,500–3,700 N; Olympic straight 3,427 ± 811 N; hook 4,405 ± 2,318 N (mean α 9,306) | `[S R2-02:S28,S29]` ✓ |
| P(LOC) | 1 / (1 + exp(−(α − 6,000) / 1,200)) for an unbraced, unaware target (0.11 at 3,500; 0.5 at 6,000; 0.94 at 9,300). Braced or aware: midpoint 7,500–8,000 | `[E]` ✓ arithmetic |
| Accumulation | Midpoint −5 % per head blow within 60 s; −20 % for a second blow while rocked | `[E]` |
| Outcome ladder | < 1,500: pain, flinch, head turned. 1,500–4,500: stunned 0.5–3 s (dazed p 0.2–0.5, LOC < 0.1). 4,500–7,000: LOC 0.2–0.6, otherwise rocked. 7,000–10,000: LOC 0.6–0.9. > 10,000: LOC > 0.9; DAI / acute subdural risk | `[E]` on `[S R2-02:S30,S31]` |
| Head snap | Peak excursion 50–100 ms after contact, 20–60° (clamped to the neck range); recoil 100–300 ms; ω_peak ≈ 0.64 × α × T (T = 8–15 ms) | `[S R2-02:S33]` `[E]` |
| Hammer | Same ladder for the rotational part, plus local failure: fracture p logistic, 50 % at frontal 23 J / temporal 10 J / parietal 30 J / occipital 40 J (blow energy 30–120 J). P(LOC) per full blow `[G]` (L): 0.1–0.3 without a fracture; 0.3–0.6 with a depressed fracture; +0.1 at the temple | `[E] R2-05 §7.5`, RB §2.5 |
| Knockout phenomenology | Tone lost ≤ 100 ms (the knees go before the head recoils); fencing p 0.66; collapse limp 0.3 / fencing crumple 0.5 / plank 0.2; eyes per §2.3; obstructed breathing when supine; LOC 5–60 s (tail 300); concussive convulsion p 0.014 | `[S R2-02:S33,S35]` `[S R2-01:S100]` |
| Waking | Eyes open first → blank stare → tries to rise and fails (p 0.3–0.6 falls back) → confused, repeats questions, amnesic | `[S R2-01:S97]` `[E]` |
| Blows after a knockout | Purely passive: the head bounces, no guard, no flinch. MMA reference: 3.5 s (0–20 s) of further strikes before stoppage | `[S R2-02:S34]` ✓ (M) |
| Flash knockdown | Down briefly with no, or momentary, LOC; gets up at once | `[S R2-02:S56]` |

### 3.8 The heart and great-vessel clock (for rows 9 and 16)

| t after the heart is destroyed | Capability | Tag |
|---|---|---|
| 0–0.3 s | Flinch damped by arousal; often no pain | `[S R2-02:S5]` |
| 0–5 s | **Full function**: can run, fight, shout, fire (4 shots in ~1 s) | `[S R2-02:S5,S9]` ✓ |
| 5–10 s | Vision greys, legs weaken, stride shortens and weaves, reaches for support; purposeful action can continue | `[K]` |
| **8–15 s** | LOC (× 0.85 upright, × 1.2 supine); hypoperfusion sag (G) | `[K] R2-04 §3.2` ✓ |
| Partial or tamponading wounds | 4 of 7 witnessed cardiac stab suicides stayed active 2–10 min, 2 for ~10 s, 1 was stopped at once (use as a shape only) | `[S R2-02:S13]` ⚠ |

### 3.9 Myths explicitly excluded (each has a debug assertion)

| # | Myth | Reality | Assertion | Tag |
|---|---|---|---|---|
| 1 | Bullets throw bodies back or spin them | Whole-body Δv: 9 mm 0.038 m/s; 00 buckshot 0.17 m/s. A boxer's punch carries ~9× the momentum of a 9 mm bullet. Spins and falls come from the victim's own movement | `assert_projectile_body_dv < 0.2 m/s`; fall direction from lean, motion, weak leg | `[E] R2-02 §1.3` ✓ |
| 2 | The involuntary "shot" snap follows the bullet's direction | The snap is a **startle flexion** (hunch, head down, shoulders up); a hit limb withdraws | `shot_snap_dir = startle_flexion` | `[K] R2-03 §7.6` ✓ |
| 3 | Everyone falls when hit | ~47 % stop after the first 9 mm hit; 13–17 % never stop | Psychological stop model | `[S R2-02:S8]` |
| 4 | Heart shot = instant drop | 10–15 s of possible action; stabs 10 s – 10 min | Physiological clock | `[S R2-02:S5]` |
| 5 | "Hydrostatic shock": a torso hit switches the brain off | No reliable remote incapacitation. Instant drops need CNS, high cord, skeletal-support loss, or psychological/vasovagal paths | `assert_no_instant_drop_without_cns_or_support_loss` | `[K] (M–H) R2-04 §12` |
| 6 | Everyone screams when shot or stabbed | No vocal reaction, a grunt, a gasp or "I'm hit" are common; the cry comes at discovery | Vocal gating | `[K] R2-02 §14 row 15` |
| 7 | Unconscious bodies brace their fall | "No protective action – floppy" | Tone 0, no IK within ≤ 100 ms | `[S R2-02:S36]` |
| 8 | Conscious falls look like ragdolls | Arms react in ~100–200 ms; hands land first in ~74 % | CatchFall | `[S R2-02:S25]` |
| 9 | Knockouts drift down slowly | Tone lost ≤ 100 ms; plank or crumple | Tone ramp | `[S R2-02:S33]` |
| 10 | The eyes roll back at death | Upgaze belongs to the first seconds of LOC; the dead rest near straight ahead or slightly divergent | `assert_no_upgaze_in_dead` | `[K] (H) R2-04 §12` |
| 11 | Head-shot or headless bodies run or thrash | Flaccid collapse; at most a jerk and 5–20 s of twitches | Release table §5.5 | `[K] R2-05 §2.5` |
| 12 | A dead body jerks when shot | Mechanical motion only, plus a rare local muscle bulge | Row 38 | `[K] R2-04 §5.5` |
| 13 | A faint looks like death | Eyes open and turned up, 1–10 jerks, awake in ~12 s | Syncope programme | `[S R2-02:S26]` ✓ |
| 14 | Every stab is noticed | Often felt as a punch; noticed later | Awareness model | `[S R2-02:S16]` |
| 15 | Punches pop eyes out | The orbital rim (~35 × 40 mm) stops the fist; a hammer face or thumb does reach the globe | Globe-rupture risk by impactor width | `[K] (H) R2-05 §5` |
| 16 | A cut windpipe lets the victim scream | No airflow reaches the mouth below the cords: the lips move while air bubbles at the neck | `aphonic_if` rule (tracheal wound below the cords, C1–C3 or apnoea) | `[K] (H) R2-05 §14.2` |
| 17 | Brain-injured characters act normally until they die | Paralysis, gaze deviation, aphasia, confusion, seizures | Neuro model | `[K] R2-02 §14 row 10` |

### 3.10 Arbitration (20 Hz decision tick; reflexes on the physics tick)

1. **Consciousness gate.** If unconscious, keep only L0, spinal reflexes, posturing and seizure states.
2. **Mechanical failures** (leg, cord or arm) immediately override posture and locomotion goals.
3. **Reflex overlays** are additive and short (≤ 0.8 s).
4. **Balance.** If XcoM is outside the base of support: step, grab or fall. Protective arm targets are pre-armed when P(fall) > 0.5.
5. **Behavioural choice**, all delayed by `rt_mult`: awareness → wound check → psychological stop roll → action (fight, flee, surrender, freeze, descend).
6. **Physiological clock.** When the brain O₂ reserve runs out or MAP crosses its threshold, force archetype G, then limp.

```text
# Pseudocode written for this document (not taken from any source)
on_hit(hit):
    apply_impulse(hit.point, hit.p * f_ret)                           # L0, true value
    if conscious:
        schedule_startle(amp = habituation * (1 - 0.5*arousal))       # L1, 30–450 ms
        if limb_hit and cord_intact_at(hit.segment): schedule_withdraw(nwr_latency)
    mech = structural_failure(hit)                                    # §3.4 rows
    if mech.leg: schedule_buckle(side, 0.1–0.3 s if loaded else next_stance)
    if mech.cns_offswitch: tone_to_zero(tau = 60–100 ms); pick_archetype(A or B)
    aware = conscious and not roll(unaware_p)
    if aware: queue(WOUND_CHECK, delay = 0.3–1.0 s * rt_mult); queue(pain_spike)
    queue(psych_stop_roll, delay = 0.3–3 s * rt_mult)
```

### Simulation parameters (reaction system)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `startle_visible` | blink 40–60; head 90–130; arms 120–160; legs 140–220 | ms | Schedule per bone group | `[S R2-02:S1,S2]` ✓ ranges |
| `startle_release` | 300–800 | ms | | `[E]` |
| `startle_habituation` | 1.0 / 0.6 / 0.45 / 0.35 / 0.25 (blink 0.5); τ 20–60 s | × | Within 10 s | `[E]` on `[S R2-02:S4]` |
| `nwr_latency` | 90–130 (arm −10–30) | ms | | `[S R2-02:S37]` ✓ |
| `heat_withdraw` | 0.2–0.6 s after contact; second pain hand +0.6–1.0, face +0.2–0.5 | s | | `[S R2-02:S37]` ⚠ `[E]` |
| `f_ret` / `k_attach` | retained 1.0; handgun through a limb 0.1–0.3; rifle through 0.05–0.2 / 1.5–3 | — | | `[E]` |
| `step_threshold_v` | forward 0.38–0.51; backward 0.13–0.22; sideways 0.32–0.45 | m/s | XcoM, ω₀ 3.2 | `[E]` ✓ |
| `toe_off` | 0.22–0.35 (× 1/capacity) | s | | `[S R2-02:S20]` ⚠ |
| `max_single_step_lean` | 23.5 + 8.7 × capacity | ° | | `[S R2-02:S21]` ✓ |
| `hand_to_wound` | torso 0.4–0.8; face 0.3–0.6; neck 0.3–0.8 | s | | `[E]` |
| `wound_check` | look 0.3–1.0; touch 0.4–1.2; look at hand 1–2 | s | | `[E]` |
| `turn_away_180` | 0.26–0.54 | s | | `[S R2-02:S12]` ⚠ |
| `psych_stop_p` | §3.6 | p | | `[E]` on `[S R2-02:S8]` |
| `unaware_p` / `discovery` | 0.3–0.5 high arousal; 0.4–0.6 back stab / lognormal median 5 s, P90 60 s | — | | `[E]` |
| `pain_gain` | clamp(1 − 0.7·arousal, 0.2, 1) | × | L4 pain behaviour only | `[E]` |
| `P_LOC(α)` | logistic, midpoint 6,000 (braced 7,500–8,000), width 1,200 | p | −5 %/blow within 60 s; −20 % when rocked | `[E]` |
| `alpha_loc_mult` | jaw 1.0; chin 0.9; temple 0.9; occiput 0.6; forehead 0.5 | × | | `[E]` |
| `ko_collapse_mix` | limp 0.3 / fencing 0.5 / plank 0.2 | p | Plank 0.4–0.6 if the knees are locked | `[E] R2-03 §5.4` |
| `rocked` | severe 5–60 s; residual 5–30 min; `rt_mult` 1.3–1.8; knee buckle 0.1–0.3 /s | — | | `[E]` |
| `liver_delay` / `winded_apnoea` | 1–3 / 5–30 (≤ 120) | s | | `[S R2-02:S55]` (L) |
| `weapon_drop_p` | §3.4 column | p | A startle can tighten the grip instead | `[E]` |
| `vasovagal_p` | 0.02–0.05 | p | Non-combatant sees its own blood | `[E]` |
| `tonic_immobility_p` | 0.02–0.1 | p | | `[S R2-02:S44]` |
| `near_miss_choice` | flee 0.4 / freeze 0.3 / duck 0.3 | p | Non-combatant | `[E]` |
| `unconscious_withdraw_p` | 0.2–0.5 at GCS M ≥ 4 | p | | `[K] [E]` |

### Visual/behavioural checklist (reaction system)
- Nobody is thrown by a bullet. A hand hit by a bullet flicks; the body hunches (startle) and then does something human: looks down, clutches, turns away, runs, sits, or keeps attacking.
- The first shot in an encounter produces the biggest flinch; later ones produce smaller flinches, but the blink never disappears.
- A thigh bone broken while standing on it folds the leg in a fraction of a second; the body goes down toward that side and the hands grab the thigh. **The fracture happens before any emotion.**
- A stabbed torso may look like it was punched; the victim keeps struggling, then looks down and sees blood.
- A clean hook to the jaw: the head whips round in about a tenth of a second and the legs go before the head comes back; no hands break the fall; the body lies slack-jawed with obstructed breathing and one arm stuck up for a few seconds.
- Hitting an unconscious body produces only passive motion (or a slow posturing spasm in deep coma); hitting a dead body produces only mechanics.
- A character with a paralysed side has no arm to catch itself on that side and clutches its wound only with the good hand.

---

## 4. Falls and ragdoll

### 4.1 Bodies and segment masses

17 simulated bodies. Clavicles, fingers and toes are **not** simulated; fingers are driven procedurally from tone and tenodesis (§4.3) `[E] R2-03 §8.1`.

Masses and inertias: de Leva (1996), scaled to 75 kg and 1.75 m `[S R2-03:S1]` (M–H; recall- and arithmetic-verified). This choice conflicts with RB §7.2, which keeps Dempster/Winter as its default (Appendix A, C-01).

| Body (RB bone) | Mass (kg) | Length (m) | CM from proximal end | I_AP / I_ML / I_long (kg·m²) | Notes |
|---|---|---|---|---|---|
| Head (`head`) | 4.0 (4.4 if the neck is merged) | 0.244 with the neck | ~3.5 cm above and 1–1.5 cm in front of the occipital condyles | pitch ≈ 0.022 | Convex hull of 12–20 points, not a sphere |
| Neck (`neck`) | **1.2** (anatomical 0.8, raised for the ≤ 10 : 1 mass-ratio rule) | 0.10–0.12 | mid | — | RB: neck ≥ 1–1.5 kg |
| Upper trunk (`chest` + `upper_chest`) | 11.97 | 0.172 | 0.052 below suprasternale | 0.181 / 0.073 / 0.153 | One body; `upper_chest` follows it |
| Middle trunk (`spine`) | 12.25 | 0.217 | 0.098 below xiphoid | 0.134 / 0.084 / 0.126 | |
| Lower trunk (`hips`) | 8.38 | 0.146 | 0.090 below navel | 0.068 / 0.055 / 0.062 | Include the buttocks in the collider |
| Upper arm (each) | 2.03 | 0.283 | 0.163 | 0.0132 / 0.0118 / 0.0041 | |
| Forearm (each) | 1.22 | 0.270 | 0.124 | 0.0068 / 0.0062 / 0.0013 | |
| Hand (each) | 0.46 | 0.087 | 0.068 | 0.0014 / 0.0009 / 0.0006 | Box collider to the fingertips |
| Thigh (each) | 10.62 | 0.424 | 0.174 | 0.207 / 0.207 / 0.042 | Dempster: 7.5 kg (C-01) |
| Shank (each) | 3.25 | 0.436 | 0.195 | 0.040 / 0.038 / 0.0065 | |
| Foot (each) | 1.03 | 0.259 | 0.115 from the heel | 0.0046 / 0.0042 / 0.0011 | |
| **Sum** | **75.0** | | | | Mass fractions sum to 100.00 % ✓ |

- **Whole body** `[E]` ✓: CM 0.96 m standing and 0.10–0.12 m lying. Pitch MOI 11.8 kg·m² about the CM, 69.5 about the ankles. Twist MOI ~1.1 kg·m².
- **Chain inertias** about each joint (for the gains in §4.4) `[E]` ✓:

  | Joint | I_eff (kg·m²) |
  |---|---|
  | Leg about the hip | 2.67 |
  | Arm about the shoulder | 0.45 |
  | Shank + foot about the knee | 0.41 |
  | Forearm + hand about the elbow | 0.078 |
  | Head + neck about C7 | 0.11 |

- **Gravity stiffness in stance, per side** `[E]`: ankle 318, knee 179, hip 75 Nm/rad.
- **Female bodies**: mass % head 6.68, trunk 42.57, upper arm 2.55, forearm 1.38, hand 0.56, thigh 14.78, shank 4.81, foot 1.29 `[S R2-03:S1]` (M).
- **Procedural bodies**: scale lengths with stature and masses with body mass; +1 % trunk share per +5 kg/m² of BMI above 23 `[E] (L)`. Recompute every MOI and gain from the §4.4 formulas.
- **Colliders** sit **0.5–1.0 cm inside the skin mesh**, so the flesh touches the floor and can be flattened in the shader. A collider larger than the skin makes the body hover and look weightless `[E] R2-03 §1.7`.

### 4.2 Joint limits

Angles are from anatomical neutral. The **alive hard limit** is the passive range (≈ active + 5–15°). Switch to the **dead/limp** limits when tone < 0.2 `[K] (M) R2-03 §2`.

| Rig joint (Jolt type) | Motion | Active | Alive hard limit | Dead / limp | Structural failure (gore event) |
|---|---|---|---|---|---|
| `spine_lower` (6DOF) | Flexion / extension / lateral / twist | 25 / 12 / 10 / 3 | 30 / 15 / 12 / 4 | 38 / 20 / 15 / 6 | Vertebral fracture only with a spine hit (RB §4.6) |
| `spine_upper` (6DOF) | Flexion / extension / lateral / twist | 40 / 18 / 20 / 30 | 45 / 20 / 22 / 35 | 60 / 28 / 30 / 45 | — |
| `neck` (6DOF) | Flexion / extension / lateral / twist | 35 / 45 / 30 / 32 | 40 / 50 / 32 / 35 | 50 / 60 / 40 / 45 | Occipital-condyle moment: flexion 59 Nm (pain) / 190 Nm (ligament); **extension 47 / 57 Nm**. Past it: fracture-dislocation; limits widen 20–40° |
| `head` (6DOF) | Flexion / extension / lateral / twist | 12 / 18 / 7 / 38 | 15 / 20 / 8 / 40 | 20 / 25 / 10 / 45 | Neck + head totals when dead: flexion 70 (chin on sternum), extension 85, rotation 90 |
| Shoulder (offset cone: axis ~60–70° flexion, 40–45° abduction; half-angle 95–105°) | Flexion / extension / abduction / horizontal adduction / internal rotation / external rotation | 165–180 / 50–60 / 170–180 / 130–140 / 70–90 / 60–90 | 180 / 60–70 / 180 / 140 / 80–95 / 90–100 | 180 / 70 / 180 / 145 / 95 / 100 | Abduction ~90° + external rotation > 100–110° at 30–60 Nm → anterior dislocation. Flexion + adduction + internal rotation under force → posterior dislocation (seizures) |
| Elbow (hinge) | Flexion / hyperextension | 140–150 / 0–10 | 150–160 / 5–10 | 155 / 10 | Hyperextension > 20–30° at ~50–100 Nm → posterior dislocation; the limit opens to −40° |
| Forearm (wrist twist) | Pronation / supination | 75–85 / 80–90 | +5–10 | 90 / 95 | Forced rotation > 110–120° → fracture |
| Wrist (6DOF) | Flexion / extension / radial / ulnar | 75–85 / 70–75 / 15–20 / 30–35 | 85–90 / 80–90 / 25 / 40 | 90 / 90 / 25 / 45 | Fall on an outstretched hand → distal radius fracture |
| Hip (offset cone: axis ~50° flexion, 10° abduction; half-angles ~75° sagittal, ~40° frontal) | Flexion with the knee bent / flexion with the knee straight / extension / abduction / adduction / internal rotation / external rotation | 115–125 / 70–90 / 10–20 / 40–45 / 20–30 / 30–45 / 40–50 | 130–140 / 80–100 / 20–30 / 45–55 / 30–35 / 40–50 / 50–60 | 140 / 100 / 30 / 55 / 35 / 50 / 70 | Flexed + adducted + axial load → posterior dislocation (short, internally rotated). Femoral-neck fracture → short, externally rotated 45–90° |
| Knee (hinge) | Flexion / hyperextension | 135–145 / 0–5 | 150–160 / 5–10 | 155–160 / 10 | Hyperextension > 15–30° or valgus > 10–15° under load (~100–300 Nm) → ligament rupture; the limit is removed on that axis |
| Ankle (6DOF) | Dorsiflexion / plantarflexion / inversion / eversion | 10–25 / 40–55 / 25–35 / 15–20 | 20–30 / 55–65 / +5 / +5 | 25–30 / 60–65 / 40 / 20 | Inversion > 35–45° with plantarflexion → sprain (the rolled ankle of a stumble) |
| Long-bone fracture (virtual joint) | Bend / twist | — | — | ±30–90 / ±20–60 at stiffness 0.05–0.2 × intact, heavy damping | — |

Sources: `[K] (M) R2-03 §2.2–2.7, §8.2`; neck tolerances `[K] (M–H)` (Mertz & Patrick); failure torques `[E] (L)`.

**Coupled limits** (a ragdoll with independent limits looks wrong exactly here) `[K] (H) R2-03 §2.5`:
- **Hamstrings.** Hip flexion ≤ 80–100° with the knee straight. Coupling torque τ = k_h × max(0, θ_hip − (90° − 0.6 × θ_knee)), k_h 30–60 Nm/rad. A limp body folded at the hips **bends its knees**.
- **Rectus femoris.** Knee flexion ≤ 120–130° with the hip extended (prone bodies).
- **Gastrocnemius.** Dorsiflexion is ~10° less with the knee straight.
- **Tenodesis.** For a limp hand, finger curl (0–1) = clamp(0.35 + 0.4 × wrist extension / 70° − 0.3 × wrist flexion / 80°, 0, 1).
- **Jaw.** With the head tipped back, a limp jaw falls open 10–30 mm.

### 4.3 Passive joint model (always on, alive or dead)

τ_pass = −k_mid·(θ − θ_rest) − A_hi·(e^((θ − θ_hi)/s) − 1)·[θ > θ_hi] + A_lo·(e^((θ_lo − θ)/s) − 1)·[θ < θ_lo] − B·θ̇

The soft zone starts 5–15° before the hard limit. A dead limb **decelerates into its limit** and never clanks off it `[K] (L–M)`, `[E] R2-03 §3.3`.

| Joint | k_mid (Nm/rad) | s (°) | End torque at the limit (Nm) | B (Nm·s/rad) |
|---|---|---|---|---|
| Head (occiput–C2) | 0.5–1 | 4–6 | 3–8 | 0.05–0.15 |
| Neck | 1–3 | 5–8 | 5–15 | 0.1–0.3 |
| Spine (each joint) | 20–60 | 5–10 | 50–100 | 2–5 |
| Shoulder | 1–3 | 8–12 | 10–25 | 0.2–0.5 |
| Elbow | 0.5–1.5 | 5–8 | 5–10 | 0.05–0.2 |
| Wrist | 0.1–0.3 | 5–10 | 1–3 | 0.01–0.05 |
| Hip | 5–15 | 8–12 | 20–50 | 0.5–2 |
| Knee | 2–5 | 6–10 | 15–30 | **0.35–0.5** (gives the normal 4–6 pendulum swings) |
| Ankle | 3–10 | 5–10 | 15–30 | 0.2–0.5 |

B ≥ 1 on the knee kills the swing in one cycle and looks like the limb is moving through syrup `[E] R2-03 §3.4` ✓.

### 4.4 Muscle tone → Jolt PhysicalBone3D drive

**Gains** `[K] (H)` method, `[E]` values, R2-03 §4, §7:
- kp = I_eff · ω² · tone
- kd = 2 · ζ · I_eff · ω · √tone
- τ_cap = τ_max · strength
- τ = kp·θ_err − kd·ω_rel + g_comp·tone·strength·τ_gravity + τ_passive

Rules:
- Clamp τ per axis to ± τ_cap. **Weakness is the cap, not the gain**: the target is still wanted, but the muscle cannot reach it.
- Apply +τ to the child body and **−τ to the parent body**. Skipping the reaction torque creates angular momentum from nothing.
- Stance joints: kp ≥ γ·k_g (γ 1.2–2.0), or gravity compensation. Remove it together with tone and the stance joints must fall.
- Stability: ω·Δt ≤ 0.5 (ω ≤ 30 rad/s at 60 Hz). Clamp the target angular velocity to 15–20 rad/s.
- **Godot 4.5 exposes no joint motors on PhysicalBone3D, and 6DOF springs are uncapped** (RB §4.10, checked against the engine source). Drive with **script torques** (`PhysicsServer3D.body_apply_torque` on the child and the parent) in the physics step (C-12).

**Tone states** `[E] R2-03 §4.2`:

| State | When | ω (rad/s) | ζ | Gravity compensation | Torque cap × max | Onset ramp |
|---|---|---|---|---|---|---|
| Braced | Alert, anticipating a blow | 14–16 | 1.0 | 1.0 | 1.0 | 100–200 ms |
| Normal (alive default) | — | Legs and trunk 10–12; neck 10; arms 6–8 | 0.8–1.0 | 1.0 | 1.0 | — |
| Hit compliance | The hit chain (± 2 joints) for 0.1–0.3 s after a hit | × 0.45–0.65 of current (kp × 0.2–0.4) | 0.7 | 0.7 | 1.0 | Instant; restore over 0.2–0.5 s |
| Dazed / reduced | Rocked, concussion, class III, pain shock | 5–8 | 0.6–0.8 | 0.5–0.8 | 0.4–0.7 | 0.3–1 s |
| Very weak | Class IV, presyncope | 2–4 | 0.8–1.0 | 0.2–0.4 | 0.1–0.3 | 1–3 s |
| **Flaccid** | Unconscious; brainstem death; below a cord lesion; dead before rigor | **0** (passive terms only) | — | **0** | 0 | **≤ 100 ms** off-switch; 0.5–2 s hypoperfusion |
| Tonic | Fencing arm, tonic seizure | 12–16 toward the posture | 1.0–1.5 | 0.5 | 0.7–0.9 | 50–200 ms |
| Posturing | Decorticate / decerebrate episode | 8–12 toward the posture | **1.2–2.0** (slow, "lead-pipe") | 0.5 | 0.5–0.8 | 0.5–2 s |
| Clonic | Seizure clonic phase, syncope myoclonus | Pulses: 12–16 for 40–120 ms, then 3–5 | 0.7 | 0 | 0.5–0.9 | Pulse rate 1–4 Hz, slowing |
| Spastic | Days later (time skip only) | Base 3–6; stretch "catch" × 2–4 when joint speed > 60–120 °/s for 100–300 ms | 0.7 | 0.3 | 0.5 | — |
| Rigor | Hours after death (RB §6.6) | Limits clamped around the current pose; break torque (RB table) | — | 0 | — | Hours |

Conflicts C-07 and C-08: RB §4.10 lists ζ 0.9 for posturing and fencing, ω 8–12 for fencing, and ζ 0.7 for tonic. This document uses the R2-03 values above.

**Per-joint gains for the 75 kg body** (reference pose) `[E] R2-03 §4.3`:

| Joint | I_eff | k_g | kp at ω 6 / 12 / 16 | kd at ω 12, ζ 1 | Stance kp (γ 1.5, no gravity compensation) |
|---|---|---|---|---|---|
| Head | 0.027 | 1.5 | 1.0 / 3.9 / 6.9 | 0.65 | — |
| Neck | 0.11 | 6.3 | 4.0 / 15.8 / 28 | 2.6 | ≥ 9.5 |
| Spine upper | 1.4 | 35 | 50 / 202 / 358 | 34 | 53 |
| Spine lower | 4.3 | 101 | 155 / 619 / 1,101 | 103 | 152 |
| Hip | 2.67 (swing) | 47 swing / 75 stance | 96 / 385 / 683 | 64 | 112 per hip |
| Knee | 0.41 | 11 / 179 | 15 / 59 / 105 | 9.8 | **270** per knee |
| Ankle | 0.009 | 0.6 / 318 | 0.3 / 1.3 / 2.3 | 0.22 | **480** per ankle |
| Shoulder | 0.45 | 10.9 | 16 / 65 / 115 | 10.8 | — |
| Elbow | 0.078 | 3.0 | 2.8 / 11.2 / 20 | 1.9 | — |
| Wrist | 0.0035 | 0.31 | 0.13 / 0.50 / 0.90 | 0.084 | — |

**Torque caps**, young adult male `[K] (M) R2-03 §3.1`:

| Joint | Cap (Nm) |
|---|---|
| Neck | Flexion 15–30; extension 30–50 |
| Trunk | Extension 200–300; flexion 150–250 |
| Shoulder | 60–120 |
| Elbow | Flexion 60–90; extension 40–60 |
| Wrist | 8–20 |
| Hip | Extension 200–300 |
| Knee | Extension 200–300 |
| Ankle | Plantarflexion 150–250 |

**Strength scale** (multiplies the cap): blood loss (1 / 0.8 / 0.4–0.6 / 0.1–0.3 by class), pain inhibition 0.3–0.7, hemiparesis (1 − sev), fatigue `[E]`.

**Why a weakened person sinks** `[E] R2-03 §3.2`:
- Knee demand per knee: 25–40 Nm at 20° on two legs; **50–70 Nm at 20° on one leg; 120–160 Nm at 45° on one leg**.
- If demand > strength × cap for > 100 ms, the knee yields; 90° is reached in 0.3–0.6 s.
- So injured people **stand straight-kneed on the good leg and go down as soon as the knee bends**.

**Tone-loss speed and order** `[E]` / `[K] (M) R2-03 §4.4`:

| Cause | Speed | Order | Tag |
|---|---|---|---|
| CNS off-switch (brainstem, high cord, deep knockout) | Linear to 0 in 50–100 ms, or exponential τ 60–100 ms (muscle force ~90 % gone by 150–250 ms) | All groups at once; grip opens 0.1–0.5 s | `[S R2-03:S7]` ⚠ |
| Knockout with fencing | Legs and trunk → 0 in ≤ 100 ms | Arms tonic for 2–10 s, then 0 over 0.5–1 s | `[S R2-03:S14]` |
| Syncope / hypoperfusion | Graded, 0.5–2 s | Legs first (p 0.6) or neck first (p 0.4), then trunk, then arms; brief tonic stiffening 1–5 s in 10–20 % | `[E] (L)` |
| Cardiac arrest (sudden) | LOC 8–15 s after the heart stops; final tone loss 0.2–0.5 s: a "crash", not a crumple | Whole body | `[S R2-03:S11]` |
| Cord transection | ≤ 100 ms below the level | — | `[K] (H)` |
| Recovery from a knockout | Over 1–5 s | Neck and arms first (the head lifts, the hands push); legs last and ataxic: knees wobble at 1.5–3 Hz for 10–60 s | `[K] (M)` `[E]` |

**Posture joint targets** (drive toward these with the "Posturing" or "Tonic" tone state) `[K]` descriptions `[S R2-01:S111]`, `[E]` angles, R2-01 §18.2:

| Joint | Decorticate | Decerebrate | Fencing (extended arm / other arm) | Figure-of-4 (seizure) |
|---|---|---|---|---|
| Shoulder | Adducted; internal rotation 30–60°; flexion 0–30° (arms on the chest) | Adducted; **internal rotation 60–90°**; extension 0–20° | Flexion 60–120°, abduction 0–30° / adducted | Extended arm: flexion 30–90°, abduction 20–45° / flexed arm across the chest |
| Elbow | **Flexion 90–130°** | **0–10°** | 0–20° / 90–120° | 0–20° / 90–130° |
| Forearm | Neutral to 45° pronation | **Full pronation 80–90°** (palms turned outward and backward; C-13) | Neutral | Pronated / neutral |
| Wrist | Flexion 45–80° | Flexion 30–70° | Neutral to 30° | Flexion 30–60° |
| Fingers | Fist, thumb tucked | Flexed | Flexed or loose | Fist |
| Hip | Extension 0–10°, adduction 10–20°, internal rotation 10–30° | Same, stiffer | Varies | Extended |
| Knee | 0–10° | 0–5° | Varies | 0–20° |
| Ankle | Plantarflexion 20–45°, inversion 10–20° | **Plantarflexion 30–45°**, inversion | Varies | Plantarflexion |
| Neck | 0–10° extension | **Extension 10–30°**; opisthotonus 40–60° + lumbar arch 20° when severe | Rotated toward the extended arm | Rotated away from the focus |
| Jaw | Neutral | Clenched | Variable | Clenched |
| Drive | 50–70 % | 60–80 % | 40–70 % | 70–90 % |

### 4.5 Collapse types

**Archetypes** `[E]` on `[S R2-02:S10,S25,S51]`, R2-02 §5.1, R2-03 §5:

| Archetype | Trigger | Tone change | Knees / hips reach the ground | Torso / head reach the ground | Motion | Protective arms | Head impact |
|---|---|---|---|---|---|---|---|
| **A. Cut-strings crumple** | Brainstem, cardiac arrest at the end of the window, deep syncope, knockout without posturing | ≤ 100 ms | 0.35–0.55 s | **0.7–1.2 s** | Knees go forward and apart, hips fold; the arms lag and "float up" relative to the shoulders; the trunk pitches along the lean; the head lands last with a whip | **None** | 3–5 m/s |
| **B. Rigid topple ("plank")** | Tonic posture (fencing, decerebrate), knees locked | ≤ 100 ms (tonic) | Feet planted until ~50° of tilt, then slide or lift | **1.0–1.6 s** from 10° to 2° of initial lean (0.8–1.6 s if the knees are not fully locked) | Rotates about the ankles as one piece | None (arms fixed in the posture) | **5–7 m/s**, the hardest head impact |
| **C. Controlled descent** | Conscious weakness, dizziness, breathlessness, surrender | 0.5–3 s | 1–5 s | 2–10 s | Hand on a wall or knee; kneels, sits, lies down, often onto one side | Deliberate | < 1 m/s |
| **D. One-sided buckle** | Leg, pelvis or knee failure; hemiplegia | 0.1–0.3 s (stance phase) | 0.4–0.8 s | 0.8–1.4 s | Drops toward the injured side, rotating toward it; hop or crossover step | Yes, in 100–200 ms | 1–3 m/s; hands or shoulder first |
| **E. Paraplegic drop** | Thoracic or lumbar cord | ≤ 100 ms (legs only) | 0.3–0.5 s (buttocks or knees) | 0.6–1.0 s | Sits down hard or pitches over the legs | Yes | 1–3 m/s |
| **F. Stumble-fall** | Balance loss while moving; rocked | — | After 1–6 steps, 0.5–3 s | +0.3–0.6 s | Sprawls forward, knees and hands first, rolls | Yes, if conscious | 1–4 m/s |
| **G. Hypoperfusion sag** | End of the consciousness window after a heart, aorta or major bleed | 1–3 s of greying and staggering, then 0.5–2 s graded | 1–2 s | 2–4 s | Slows, sways, sags to the knees, slumps forward or sideways | Fades from partial to none | 2–4 m/s |

**Off-switch (A), frame by frame**, from a relaxed stance (knees 0–5°, CM 2–4° ahead of the ankles) `[E] R2-03 §5.2`:

| t (s) | What happens | CM height (m) |
|---|---|---|
| 0–0.10 | Tone ramps to 0. Almost nothing visible (≤ 1–2 cm sag); lids stay; the jaw starts to drop | 0.95 |
| 0.10–0.25 | Knees go forward (20–50°), hips flex (10–30°), ankles dorsiflex (10–20°); the head lags (neck flexion 10–20°); the grip opens | 0.85–0.90 |
| 0.25–0.45 | Near-vertical drop; knees 80–130°, hips 50–90°; the arms lag; the knees splay (hip external rotation 10–30°) | 0.50–0.60 |
| **0.35–0.55** | **First contact**: knees at 2–3 m/s, or buttocks at 2.5–3.5 m/s | ~0.45 |
| 0.5–1.2 | The trunk topples 60–90° in 0.3–0.6 s. **Head impact at 0.7–1.2 s, 3–5 m/s.** The arms slap down 50–150 ms after the trunk | 0.12–0.20 |
| 1.0–2.0 | The head rebounds 1–5 cm; the legs slide out or stay folded; limbs flop to their limits | 0.10–0.15 |

Final poses `[E] (L)`: folded or kneeling slump rolling to one side 0.40; prone 0.25; supine 0.20; legs folded under with the trunk twisted 0.15.

**Physics floor** `[E]` ✓: free fall of the CM (0.84 m) takes 0.41 s; no collapse from standing reaches the ground faster. Energy dissipated ≈ 620 J.

**Other collapse scripts:**

| Collapse | Sequence | Tag |
|---|---|---|
| Syncope (faint) | Prodrome 5–60 s (pale, sweating, yawning, sway × 2–3, feet widen, hand seeks support); grey-out in the last 3–7 s; tone loss graded 0.5–2 s; ground contact 1–2.5 s after the first visible buckle (buttocks or hips at 1.5–2.5 m/s, head 2–4 m/s); on the ground: 1–10 irregular jerks over 3–15 s, eyes open and up; recovers ~12 s after lying flat; may faint again on sitting up too soon (p 0.1–0.2). Propped upright: LOC and jerking last ≥ 20–30 s | `[S R2-03:S5]` ✓ |
| Knockout variants | Limp crumple (A) 0.30, with a ¼–½ turn following the head's rotation after a hook; fencing crumple 0.50 (the raised arm stays up 2–10 s after landing, then drops); rigid plank (B) 0.20 (0.4–0.6 if the knees are locked or hyperextended) | `[E] R2-03 §5.4` |
| Rocked ("rubber legs") | Knee tone 0.35–0.6 ± 0.2–0.3 at 1.5–3 Hz for 1–5 s; 2–6 stumbling wide steps; reaches for support; falls with p 0.4–0.7, usually to the knees or hands, arms working | `[E] R2-03 §5.4` |
| Bleeding out (C → G) | Leans on a wall with sway × 2–3 → slides down it at 0.1–0.4 m/s over 1–3 s (knees to 60–100°; a back wound leaves a 0.5–1 m vertical smear) → seated, heels slide forward, trunk leans 20–60° over 5–30 s → head nods in 1–3 s cycles, hands fall palm-up → topples when the trunk passes 25–30° sideways (0.8–1.2 s, head 1–3 m/s). Without a wall: knees (2–10 s), hands, hip, side | `[E] R2-03 §5.5` |
| Leg failure (D) | 0–0.1 s the hit leg is loaded and the flinch starts → 0.1–0.3 s the stance knee flexes 30–60° uncontrolled, pelvis drops 5–15° on that side, trunk rotates toward it → rescue step at ~0.24 s, often short or crossing, or 1–3 hops (p 0.3–0.5) → arm burst ~0.1 s after balance loss → contact at 0.6–1.4 s, hands first (~74 %), then knee or hip, then shoulder; the head strikes in up to ~37 % (frail older adults: an upper bound for alert young adults, a floor for dazed ones) → hand to the wound 0.3–1 s after landing | `[S R2-03:S3b,S4,S17]` |
| Spinal cord (E) | Legs vanish ≤ 100 ms; sits down hard (buttocks 2–3 m/s) or pitches over the legs; arms catch; the legs lie where they landed, often externally rotated and crossed. Cervical: no catch below C5–C7; C1–C3 is cut strings **with the person awake** | `[K] R2-03 §5.7` |
| Heel slip in blood | Wet-blood friction 0.1–0.25 (tacky 0.6–0.9 after 3–10 min); walking needs 0.17–0.22. Slip > 10–15 cm or > 0.8–1.0 m/s → backward fall in 0.6–0.8 s; buttock or hip first, then hand and elbow, then back; occipital impact 20–40 % | `[E] (L) R2-03 §5.8` |
| Running collapse | Loss of tone at 5 m/s: the body travels 2.5–3.5 m during the 0.5–0.7 s fall, then slides or rolls 0.8–3 m | `[E] R2-02 §4.3` |

**Direction rules** `[E] R2-02 §5.5`:
1. The fall follows the CM velocity at the moment tone is lost; if the body is roughly still, it follows the current lean (quiet stance leans 2–4° forward, so forward-down is the most common result).
2. One leg fails: toward that leg, sideways and forward.
3. Hemiplegia: toward the paralysed side.
4. Running: forward.
5. Backing away or turning: backward or twisting.
6. Hook-punch knockout: follows the head's rotation.
7. **Bullets never choose the direction.**

Default when perfectly upright and still: forward 0.45, backward 0.25, sideways 0.30 `[E] (L)`.

### 4.6 Landing rules

**Contact order and impact speeds** `[E] R2-03 §6.1` (anchor: head impact 2.0–7.4 m/s in dummy standing falls `[S R2-03:S9]` ⚠):

| Fall | First contact | Then | Head | Arms |
|---|---|---|---|---|
| Crumple forward | Knees 0.35–0.5 s, 2–3 m/s | Thighs and pelvis, or chest and abdomen | **Face or forehead 0.7–1.1 s, 3–5 m/s** | Trail; palms up beside the body or trapped under the chest |
| Crumple backward | Buttocks 0.4–0.6 s, 2.5–3.5 m/s | Lower back, then upper back | **Occiput last, with a whip, 3.5–5 m/s** | Flung out, abducted 30–90° |
| Crumple sideways | Knee or hip 0.4–0.6 s | Shoulder 2–4 m/s | Temporo-parietal, 2.5–4 m/s | The lower arm trapped under the body |
| Plank forward / backward | Chest, abdomen and face almost together / buttocks and upper back almost together | — | **5–7 m/s** (backward to the occiput is the worst case) | In the posture |
| Conscious stumble | Hands 2–3 m/s | Knee, hip or shoulder | 1–4 m/s in a minority | Elbows yield 20–60° |
| Syncope sag | Buttocks, knees or hip, 1.5–2.5 m/s | Side or back | 2–4 m/s | Limp |
| Seated topple (bled out) | Shoulder 1–2 m/s | — | 1–3 m/s | Limp |

- **Head whip**: a limp head hits at **1.0–1.3 × the upper-trunk speed**. There is no neck-muscle braking or chin tuck. A conscious person tucks the chin in backward falls and turns the face away in forward falls `[E] R2-03 §6.2`.
- **Head deceleration on concrete** at 5 m/s with 5–10 mm of scalp compression: mean 130–255 g, peak ≈ 200–500 g; contact lasts 3–8 ms on concrete and 8–15 ms on wood or carpet. Hand the impact to the skull-fracture thresholds of RB §2.5 / R1-02 §5. **A rigid backward topple onto the occiput is the most dangerous fall in the game** `[E]` ✓.
- **Bounce**: set bounce = 0 on every body part **and on every floor, wall and prop**, because Godot adds the two bounce values. The head's small rebound (1–5 cm) comes from its hull shape. Trunk rebound ≤ 1–2 cm; limbs 1–3 cm `[K] (M) R2-03 §6.3`.
- **Friction** `[K] (M)`, `[E]`:

  | Pair | μ |
  |---|---|
  | Clothing on concrete | 0.55 |
  | Clothing on polished wood | 0.4 |
  | Synthetic fabric | 0.3 |
  | Bare skin | 0.6 |
  | Wet with water | 0.3 |
  | Wet blood / tacky blood | 0.18 / 0.75 |
  | Grass | 0.45 |

  Set `friction` directly on each `PhysicalBone3D`; it has no PhysicsMaterial slot. RB §4.10 gives 0.6–0.9 for skin or cloth on a floor (C-16).
- **Slide**: d = v² / (2μg). A standing collapse lands mostly vertically, with 0.5–2 m/s of horizontal CM speed at contact, so it slides only **0.03–0.4 m**. **A body that slides a metre after a standing collapse is a bug** `[E] R2-03 §6.4` ✓.
- **Rolling**: flesh has a flat contact patch and does not roll by itself. Capsules and spheres do, so use hull shapes for the head and trunk, plus contact-dependent angular damping (§4.7).

### 4.7 Settling and the final pose

**Settle controller** `[E] R2-03 §6.5`:
- When the body is unconscious or dead, grounded, and its kinetic energy has stayed below 2 J for 0.5 s, ramp angular damping from 0.1 to 3–8 and linear damping from 0 to 0.5–1 over 0.5 s.
- Reset both on any external hit.
- Sleep when KE < 0.5 J, within 2–5 s of the last impact.
- **Never raise damping before the body has settled** ("falling through syrup").

**Settling sequence:**

| t after the last impact | What happens |
|---|---|
| 0–0.3 s | Rebounds; limbs flop to their limits; the arms slap down |
| 0.3–1.0 s | Secondary rolls: a bent top knee falls sideways; the head rolls 20–60° off the midline; an arm slides off the chest |
| 1–2 s | Flesh flattens 1–2 cm at the contacts (shader); clothing drapes; air forced out on the first chest impact |
| 2–5 s | Still |

**Resting angles of a limp body** `[K] (M)` values, `[E] R2-03 §2.6`:

| Posture | Resting angles |
|---|---|
| Supine | Head rotated **20–60°** to one side (p 0.8) or midline (p 0.2); jaw open 10–30 mm; shoulders abducted 10–40° (60–90° after a backward fall); elbows 10–40°; forearms pronated 30–80°; fingers in a loose curl; hips externally rotated **30–60°** (feet 60–120° apart); ankles plantarflexed 20–40° |
| Prone | Head **rotated 60–90° onto the cheek** (p 0.85) or face down (p 0.15); arms along the sides palms up after a forward crumple, or abducted 60–90° with the elbows bent 60–90°; feet plantarflexed 40–60° with their backs flat on the floor |
| Side-lying | Lower arm trapped under the body or thrust forward; upper hip and knee 20–60° flexed, with the top knee on the floor in front |
| Slumped sitting | Trunk flexed 30–60° or leaning 20–45° sideways; chin on the chest or head on the shoulder; palms up on the lap; legs straight or "frog" (hips externally rotated 30–60°) |
| Kneeling crumple | Knees 150–160°; trunk folded onto the thighs; unstable, rolls within 0.5–3 s in ~70 % |

**Final pose probabilities** `[E] (L)`:

| Fall | Prone | Side | Supine | Folded / kneeling |
|---|---|---|---|---|
| Forward | 0.55–0.65 | 0.25–0.35 | 0.05–0.10 | — |
| Backward | 0.05 | 0.25 | 0.70 | — |
| Vertical crumple | 0.25 | 0.40 | 0.20 | 0.15 |

**Why a correct dead pose looks "wrong"** (keep all of these) `[K] (M) R2-03 §6.6`:
- nothing is held up;
- joints sit at the **ends** of their range (backs of the hands and feet flat, wrists bent 60–90°, head 70–90° on the cheek, feet splayed 45–60°);
- limbs are trapped under the body;
- the pelvis and shoulders are twisted 30–45° apart;
- there is no protective arrangement;
- the hands are half-curled;
- the mouth is open;
- **complete stillness.** A living unconscious body breathes 12–20 /min with 5–10 mm of chest and belly motion. **The absence of that micro-motion is the strongest cue of death.**

**Bugs that look wrong in the bad way**: jitter at rest, interpenetration, rotation beyond the limp range without a fracture, hovering, perpetual rolling, limbs frozen in mid-air (premature sleep), a T-pose snap at death, rubber-band joint stretching.

**Handling dead weight** `[E] R2-03 §6.7` ✓:

| Action | Force or impulse | What the body does |
|---|---|---|
| Drag by one wrist | 300–440 N on concrete; 140–220 N on a wet smooth floor | The shoulder abducts 150–180°; the head rolls away and scrapes; the free arm trails palm up; the heels drag and leave two lines in blood; the drag comes in heaves |
| Lift the shoulders of a supine body | 260–330 N | The head falls back to the neck-extension limit; the arms hang; trying to stand it up folds the knees |
| Kick the trunk | 20–40 N·s | The trunk moves 0.7–1.3 m/s and slides 5–15 cm; limbs flop 50–150 ms later |
| Shoot a limp body | True impulse only | Whole body ≤ 0.2 m/s. Head: 0.66 m/s (retained 9 mm); up to ~2–3 m/s from a full buckshot load (typically 0.5–2). Hand flick 0.6–1.3 m/s |

### 4.8 Active-ragdoll layering

Two controls per bone chain `[E]` on R2-02 §13, R2-03 §7–§8, RB §4.10:
- `w_phys`: the `PhysicalBoneSimulator3D` **influence** on that chain. 0 = the kinematic animation pose; 1 = the simulated pose.
- `tone`: the PD gain scale on the simulated chain, tracking the animation or behaviour target pose.

**Blend weights per state:**

| State | Legs | Trunk | Arms | Neck / head | Notes |
|---|---|---|---|---|---|
| Alert, idle or locomotion | w 0 | w 0 | w 0–0.2 (secondary motion) | w 0 | Animation-driven |
| Hit reaction, no balance loss | w 0 | Hit chain w 0.3–0.6 → 0 over 0.2–0.5 s; tone × 0.2–0.4 (compliance) | As trunk if hit | As trunk | Plus the flinch overlay |
| Balance lost, stepping or staggering | w 1, tone 0.6–1.0, targets from the step planner | w 1 | w 1 (windmill / CatchFall) | w 1 | Assist ≤ 0.3 × body weight vertical, upright torque (0.5–1.5)·m·g·h × capacity; **zero once a fall starts** |
| Conscious fall | w 1 per injury | w 1 | w 1, tone 1.0, CatchFall targets | w 1, head turned away | |
| Paralysed limb on a standing body | w 0 | w 0 | Paralysed chain w 1, tone 0 | w 0 | Partial ragdoll: the limb swings passively |
| Broken leg while standing | That leg w 1 with the fracture joint | w 1 as balance fails | w 1 | — | |
| Unconscious / cut strings | w 1 | w 1 | w 1 | w 1 | Tone → 0 in 50–100 ms |
| Posturing, tonic, fencing | w 1 | w 1 | w 1 | w 1 | Tone toward the posture targets (§4.4) |
| Seizure | w 1 | w 1 | w 1 | w 1 | Clonic pulses (§5.4) |
| Writhing, curling, crawling on the ground | w 1, tone 0.3–0.8 | w 1 | w 1 | w 1 | Noise or crawl targets |
| Dead | w 1, tone 0 | — | — | — | Settle controller; bake to a static mesh after 30–60 s asleep; re-create the ragdoll when hit |
| Getting up (waking or recovering) | Blend w 1 → 0 over 0.3–0.6 s to a matched get-up clip once KE < 2 J and the pose matches (Zordan-style) | | | | |

**Priority of behaviours** (a higher layer claims weight w; lower layers fill 1 − w; targets slerped by weight):
1. physiology programmes (posturing, seizure, fencing);
2. reflexes;
3. protective (CatchFall, ProtectHead);
4. balance and stepping;
5. ReachForWound;
6. writhe, HeadLook, idle.

**Blend times**: behaviour switches 50–300 ms; tone loss ≤ 100 ms; reflex onsets on the physics tick. **An unconscious body loses every voluntary behaviour within ≤ 100 ms** `[E]`.

**Godot 4.5 / Jolt setup** (`[K] (M)` R2-03 §8; RB §4.10 where verified; check against the 4.5 class reference):

| Setting | Value |
|---|---|
| Node structure | `Skeleton3D` → `PhysicalBoneSimulator3D` → 17 × `PhysicalBone3D` |
| Simulation control | `physical_bones_start_simulation(bones)` for partial ragdolls; `influence` for the blend |
| Animation targets | Sample the `AnimationTree` pose **before** the simulator modifier overrides the skeleton |
| Joint types | Hinge: elbow, knee. Cone with an offset axis: shoulder, hip. 6DOF: spine, neck, head, wrist, ankle |
| Soft limits | `bias`, `softness` and `relaxation` are ignored by Jolt; implement the §4.3 soft zone with script torques |
| Physics rate | 60 Hz (crowds) / 120 Hz (close-ups); interpolation on |
| Jolt solver steps | Velocity 12–16 (default 10); position 3–4 (default 2) |
| Sleep | 0.03–0.05 m/s for 0.5–1 s, plus the settle controller |
| Damping while moving | Linear 0–0.05; angular 0.05–0.3 |
| Gravity | 9.81 m/s²; **never raise gravity to fake weight** |
| Collisions | Non-adjacent self-collision on (the hand-drop test needs it) |
| CCD | On for the head, hands and feet via `PhysicsServer3D` on the bone's RID, if supported; otherwise keep floor colliders ≥ 0.2 m thick |
| Inertia | Set through `PhysicsServer3D` (`BODY_PARAM_INERTIA`) if the shape-derived value is off by more than ±30 %; check that it survives starting and stopping the simulation |

### 4.9 Validation tests (run on the reference body)

| # | Test | Pass criterion | Tag |
|---|---|---|---|
| T1 | Limp body dropped flat from 1.0 m | Contact at 0.45 s; rebound ≤ 2 cm | `[E]` |
| T2 | Off-switch from relaxed stance (tone → 0 in 80 ms) | First contact 0.35–0.55 s; head 0.7–1.2 s at 3–5 m/s | `[E]` |
| T3 | Rigid plank, 5° forward lean | Ground at 1.2–1.3 s; head 6–7 m/s; the feet slide or lift after ~50° | `[E]` ✓ |
| T4 | Limp arm released from 90° flexion (seated, trunk fixed) | **Passes the vertical at 0.36–0.40 s**; 2–4 visible swings; still within 4 s | `[E]` ✓ |
| T5 | Seated leg pendulum from full knee extension | Period 1.0–1.3 s; 4–6 oscillations | `[E]` ✓ |
| T6 | Seated body, all tone off | Chin to chest in 0.3–0.6 s; trunk onto the thighs or sideways in 0.7–1.2 s | `[E]` ✓ |
| T7 | Settle after T2 | KE < 0.5 J by 2–5 s; no rolling on a 3° slope | `[E]` |
| T8 | Limp body sliding at 5 m/s on concrete (μ 0.5) | 2.3–2.8 m | `[E]` ✓ |
| T9 | Drag by one wrist on concrete | 300–440 N; the head lolls back; the heels drag | `[E]` |
| T10 | 9 mm hit to the upper trunk of a standing, conscious ragdoll | Whole-body Δv < 0.05 m/s; the visible reaction is the flinch and compliance | `[E]` |
| T11 | Buckshot to the head of a limp supine body | Head Δv ≤ 2–3 m/s; trunk ≤ 0.2 m/s | `[E]` |
| T12 | Hand drop over the face (unconscious) | The hand hits the face | `[K] (H)` |
| T13 | ROM sweep of every joint | Reaches the §4.2 limits within ±3°; no gimbal flips; no rebound at the limit | `[E]` |
| T14 | Conscious forward fall | Arms react < 200 ms; hands land first; elbows yield 20–60° | `[S R2-03:S4]` |
| T15 | Femur fracture on the stance leg | Knee collapse 0.1–0.3 s; falls toward the injured side; contact 0.6–1.4 s | `[E]` |
| T16 | Syncope preset | Graded tone loss 0.5–2 s; contact 1–2.5 s after the buckle; 1–10 jerks over 3–15 s; eyes up; recovery ~12 s | `[S R2-03:S5]` ✓ |
| T17 | Rigor at 8 h: lift the forearm | Nothing moves until 15–40 Nm; then the joint breaks and stays loose | `[E]` |

### Simulation parameters (falls and ragdoll)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `seg_mass` | §4.1 (de Leva; neck ≥ 1.2) | kg | Set explicitly; C-01 | `[S R2-03:S1]` (M) |
| `mass_ratio_adjacent_max` | 10 : 1 | — | | `[K] (M)` |
| `rom_alive` / `rom_dead` | §4.2 | ° | Switch at tone < 0.2 | `[K] (M)` |
| `soft_zone` | last 5–15° | ° | Exponential | `[E]` |
| `hamstring_k` | 30–60 | Nm/rad | | `[E]` |
| `gain_rule` | kp = I·ω²·tone; kd = 2ζIω√tone | — | + reaction torque on the parent | `[K] (H)` |
| `omega` braced / normal / dazed / weak | 14–16 / 10–12 (arms 6–8) / 5–8 / 2–4 | rad/s | | `[E]` |
| `zeta` normal / posturing | 0.8–1.0 / 1.2–2.0 | — | C-07 | `[E]` |
| `hit_compliance` | kp × 0.2–0.4 for 0.1–0.3 s; restore 0.2–0.5 s | — | Hit chain ± 2 joints | `[E]` |
| `tone_loss_offswitch` | 50–100 (or τ 60–100) | ms | | `[S R2-03:S7]` ⚠ |
| `tone_loss_hypoperfusion` | 0.5–2 | s | Legs first p 0.6 / neck first p 0.4 | `[E] (L)` |
| `crumple_contact` / `head` | 0.35–0.55 / 0.7–1.2 s at 3–5 m/s | s | | `[E]` |
| `plank_time` / `head_v` | 1.0–1.6 (0.8–1.6 not rigid) / 5–7 | s / m/s | | `[E]` ✓ |
| `protective_arm_onset` / `p` | ~100 ms burst; oriented < 200 ms / 0.9 | — | Conscious only | `[S R2-02:S25]` |
| `body_bounce` / `floor_bounce` | 0 / 0 | — | Godot adds them | `[K] (M)` |
| `standing_collapse_slide` | 0.03–0.4 | m | | `[E]` |
| `settle_damping` | angular 3–8, linear 0.5–1, 0.5 s ramp | 1/s | After KE < 2 J for 0.5 s | `[E]` |
| `sleep_after` | 2–5 | s | KE < 0.5 J | `[E]` |
| `assist_vertical_max` | 0.3 × body weight | N | 0 once a fall starts | `[E]` |
| `blend_times` | 50–300 | ms | Tone loss ≤ 100 ms | `[E]` |
| `jolt_steps` | velocity 12–16, position 3–4 | — | | `[K] (M)` |
| `corpse_bake_after` | 30–60 | s | Asleep | `[E]` |

### Visual/behavioural checklist (falls and ragdoll)
- A brainstem or knockout collapse is an instant of nothing, then the body drops almost straight down in about a second: knees forward and apart, arms floating up then slapping down, head last and hardest with a small bounce, no hand reaching out.
- A stiff knockout tips over like a plank in about a second, arms locked, feet sliding at the end, and gives the hardest head impact in the game.
- A conscious fall has arms out within a fifth of a second, hands landing first, elbows bending, head turned away.
- A bleeding victim leans, slides down the wall, sits, nods, and tips over, leaving a smear.
- Within 2–5 s everything is still: head turned on the cheek, feet splayed, hands half-curled, flesh flattened at the contacts. Nothing rolls on a gentle slope and nothing jitters.
- A limp body folded at the hips bends its knees; a limp arm dropped over the face hits the face.
- A living unconscious body keeps breathing (chest moves 5–10 mm); a dead one is completely still.

---

## 5. Involuntary movement layer

Time origins as R2-04 §0.3:
- `t_inj`: the injury;
- `t_LOC`: loss of consciousness;
- `t_apn`: apnoea;
- `t_arr`: circulatory arrest (last effective beat);
- `t_dead` = `t_arr` + 300 s.

### 5.1 Generator gating (each sign needs living tissue)

| Sign | Needs working | Abolished by | Window | Tag |
|---|---|---|---|---|
| Purposeful movement, protection, speech | Consciousness | LOC (≤ 100 ms) | Until `t_LOC` | `[K] (H)` |
| Moan, groan, scream | Medulla + breathing | Apnoea, medullary destruction, GCS V1 | Until coma deepens | `[K] (H)` |
| Fear tremor | Consciousness | LOC | Conscious phase | `[K] (M)` |
| Shivering, teeth chattering | Hypothalamus, brainstem, cord, muscle; core > 30–32 °C; perfusion > 0.5 | Deep shock, hypoxia, coma, cord lesion (below it) | Stops before or at LOC | `[K] (M)` |
| Syncopal / anoxic jerks | Brainstem alive, cortex failing | Brainstem destruction | `t_LOC` → +30 s | `[S R2-04:S1]` |
| Anoxic tonic spasm | Brainstem | Medullary destruction | 10–40 s after flow stops | `[K⚠] (L–M)` |
| Epileptic seizure | **Perfused cortex** (perfusion > 0.3 for the last 10 s) | Flat EEG (15–30 s after flow stops); cortical destruction | Not after ~30 s of no flow | `[K] (H)` |
| Posturing | Lower pons/medulla + cord | Medullary failure (becomes flaccid) | Hours of coma | `[S R2-04:S10]` (H) |
| Agonal gasping | **Medulla** + phrenic nerves (C3–C5) | Medullary destruction; C1–C3 section (face and neck "gasps" without air) | Mostly 10 s – 5 min after `t_arr` | `[K] (M)` |
| Obstructed breathing, airway froth | Spontaneous breathing | Apnoea | Unconscious and breathing | `[K] (H)` |
| Cough, active vomiting, hiccup | Medulla | Deep coma, brain death | Living | `[K] (M)` |
| Passive regurgitation | Nothing | — | Living, dying and **dead** (when moved) | `[K] (M)` |
| Spinal reflexes ("Lazarus") | Perfused cord with the brain dead | Cord ischaemia | Brainstem death → `t_arr` + 60–180 s | `[S R2-04:S11]` |
| Fasciculations | Living motor axons | Axonal failure | Living, and sparse to 10–20 min after `t_arr` | `[K] (L)` |
| Idiomuscular bulge | Muscle fibre only | Muscle death | Visible to ~1.5–2.5 h after death, when struck | `[K] (L) RB §6.7` |
| Roving eyes, doll's eyes, pupil reflex, blink | Pons + midbrain | Brainstem failure | Coma with an intact brainstem | `[S R2-04:S16,S17]` |
| Sweating | Hypothalamus → sympathetic chain → perfusion | `t_arr`; below a cord lesion | Stops at `t_arr` | `[K] (M)` |

**Debug assertions** `[K] R2-04 §12`:
- `assert_no_gasp_if_medulla_dead`
- `assert_no_terminal_secretions_before` 30 min unconscious
- `assert_no_mottling_before` 10 min of shock
- `assert_no_cyanosis_if_hb_below` 5 g/dL
- `assert_no_spontaneous_motion_after` `t_arr` + 20 min
- `assert_no_upgaze_in_dead`

### 5.2 Breathing, airway obstruction and agonal gasps

**Unconscious airway by posture** `[K] (M)`, `[E] R2-04 §2.1`:

| Posture | P(partial obstruction) / P(complete obstruction) | Fluids |
|---|---|---|
| Supine, head neutral | 0.6–0.8 / 0.1–0.2 | Pool in the pharynx: froth bubbling at the lips, aspiration |
| Supine, head extended | 0.2–0.3 / < 0.05 | Pool |
| Slumped, chin on chest | 0.5–0.7 / 0.2–0.3 | Run out onto the chest |
| On the side | 0.1–0.2 / < 0.05 | **Drain from the lower mouth corner and nostril** |
| Prone | 0.1–0.2 / 0.05–0.1 (higher on soft surfaces) | Pool under the face; bubbling |

- **Partial obstruction**: slack jaw, tongue fallen back, chest and belly heaving with each breath.
- **Complete obstruction**: effort without air. See-saw chest and belly, suprasternal tugging, hands to the throat if conscious. Lips blue in 60–120 s; heart arrest in 4–8 min `[K] (M)`.

**Agonal gasping** `[K] (M)` / `[E] R2-04 §2.2`:

| Quantity | Value | Tag |
|---|---|---|
| P(gasps) | Destroyed heart / VF 0.45; exsanguination to PEA 0.4; asphyxia with a beating heart 0.7 (0.7–0.9); **medulla destroyed 0**; × exp(−t_onset / 300 s) for late rolls | `[K]` ✓ (33–40 % literature band) |
| First gasp | 5–120 s after `t_arr` (default 30; 15–30 equally defensible) | `[K⚠]` |
| Interval | Starts at 10 s (6–20), each × 1.3 (1.15–1.5) → 10, 13, 17, 22, 29, 37, 48 s | `[E]` |
| Count / phase | 8 (3–30) / 1–5 min; the eight defaults end at ~206 s | `[E]` ✓ arithmetic |
| Amplitude | × 0.85 per gasp | `[E]` |
| False last breath | p 0.3: 1–2 more gasps after a 30–120 s pause | `[E]` |
| One gasp | Inspiration **0.2–0.6 s**, short and violent: head and neck extend 5–30°; **jaw drops 15–35 mm**; lips pull back; nostrils flare; shoulders lift 5–15 mm; upper belly out 10–30 mm (see-saw if obstructed). Early gasps come with a small arm or shoulder jerk, p 0.2–0.4 per gasp in the first minute (then 0.05). Expiration passive 1–3 s; the jaw half-closes. Limp and still between gasps | `[K] (M)` `[E]` |
| Eyes during gasps | Move with the head (no counter-rotation); pupils keep dilating | `[K]` |
| Meaning | A brainstem reflex, **not recovery**; without circulation no gasp keeps the brain alive | `[K] (H)` |

- **C1–C3 section, awake**: gasping attempts (mouth opening, neck straining, shoulder shrugs) at 10–30 /min, slowing with hypoxia and stopping at LOC after 90–180 s. No airflow `[E]`.
- **Brain-death pseudo-gasps**: shoulders elevate and adduct, back arches, intercostals pull in. No airflow; only inside the spinal-reflex window `[K] (M)`.
- **Pontine and medullary patterns** (apneustic, cluster, ataxic): §1.7.4.
- **Slow deaths only (hours)** `[K] (L–M) R2-04 §2.3–2.4`:
  - **terminal secretions** (secretions pooled in the throat, bubbling at the lips with each breath): p 0 if unconscious < 30 min; 0.3–0.5 if unconscious and not swallowing > 60 min;
  - **mandibular breathing**: the jaw drops 5–20 mm with every breath, ~2–3 h before death;
  - final breaths shallow and 30–120 s apart, often ending with a gasp or a passive sigh.

**Airway fluids** `[K] R2-04 §2.5–2.7`:
- **Conscious with blood in the airway**: sits up, leans forward, refuses to lie back; spits every 5–30 s; coughs in bouts of 1–5 every 10–60 s (head and trunk jerk 5–15° forward per cough); swallowed blood is vomited 10–60 min later as dark clots.
- **Unconscious supine**: froth moving with every breath; bubbles at the lips and nostrils.
- **Aspiration**: ~1–3 mL/kg impairs oxygenation; ~10 mL/kg or a clot at the larynx asphyxiates within minutes `[E] (L)`.
- **Vomiting sequence** (conscious or lightly unconscious):
  1. nausea 10–120 s: pallor, sweat, salivation, repeated swallowing, yawning;
  2. retching: 2–10 heaves at ~1 /s;
  3. expulsion: 0.5–2 s, 50–500 mL, a jet up to 0.5–1.5 m when upright;
  4. recovery: gasp, cough, spit.

  Unconscious supine: aspiration p 0.5–0.8 per episode (on the side 0.1–0.2).
- **Neurogenic pulmonary oedema** (massive head injury surviving > 15 min): visible white-to-pink froth at the nose and mouth, p 0.2 (0.2–0.3); onset 15 min – 4 h (default 45 min); reforms within minutes when wiped `[E]`.
- **Dead body moved roughly**: regurgitation p 0.05–0.15 per movement.

### 5.3 Anoxic sequences

**Convulsive syncope and circulatory LOC** `[S R2-04:S1,S2]` ✓:

| Feature | Value |
|---|---|
| LOC (faint that recovers) | 12.1 ± 4.4 s |
| Myoclonic jerks | 90 % of induced faints (game: 0.8 for sudden cardiac or haemorrhagic LOC, 0.5 for slow onset) |
| Jerk count | 1–10 (median ~3–5, rarely ~20), irregular, multifocal, proximal and distal, **no slowing pattern**, over 5–15 s (never > 30 s) |
| Automatisms | Head turning, lip smacking, chewing, righting attempts: 79 % |
| Eyes | Open; transient upgaze (§2.3) |
| Brief tonic stiffening | p 0.1–0.2 for 1–5 s (opisthotonus, arms extended) |
| Moan | p 0.2–0.4 |
| Urine | p 0.1–0.25 |
| Tongue bite | Rare (< 0.05), at the **tip** |
| Colour | **Pale** |
| Recovery lying flat | Oriented within ~30 s; hallucinations reported afterwards in ~60 % ("I saw lights") |

**Complete circulatory arrest, second by second** (destroyed heart, VF, asystole) `[K] (H)` Rossen 1943 ✓, R2-04 §3.2:

| t after `t_arr` | Body | Eyes | Breathing |
|---|---|---|---|
| 0–4 s | Nothing visible | Normal | Normal |
| 3–7 s | Vision greys and tunnels; action continues | Unfocused | May gasp a word |
| **5–10 s (cuff); 8–15 s for a destroyed heart** (× 0.85 upright, × 1.2 supine) | **LOC**; tone gone; fall 0.6–1.2 s | Open, fixed stare | Air forced out on impact |
| LOC + 0–3 s | Collapse | Upgaze 10–30° begins (p 0.6–0.9) | — |
| LOC + 1–15 s | Jerks (p 0.6–0.9, 1–10); head turns; lip smacking | Up, then drifting back | Obstructed breathing possible |
| 15–30 s | Anoxic tonic spasm (p 0.15–0.3): arms extended and turned in, legs extended, back and neck arched, jaw clenched, 5–20 s, then limp; urine p 0.1–0.2; EEG flat | Mid-position; lids start to droop | Irregular, then stops or becomes gasping |
| 20–60 s | First gasp (p ~0.45) | No movement relative to the head | Gasping; froth may bubble at the lips |
| 30–45 s | — | Pupils start to dilate | — |
| 60–120 s | Face grey-blue with full blood volume; waxy white if exsanguinated | 6–8 mm, fixed, slightly divergent | Gasps every 10–30 s |
| 1–5 min | Gasps weaken and stop; faint twitches of fingers, face or calves | Lids half-open | A final passive sigh |
| 5 min | `t_dead` | — | — |

**Brain cut off while the heart still beats** (neck compression; brainstem compression at the end of herniation; C1–C3 after LOC, whose times stretch 5–10× before LOC because the insult is hypoxic, not ischaemic) `[K] (M) R2-04 §3.3` ✓ recall:

| Event | Time from the onset of cerebral ischaemia |
|---|---|
| LOC | ~10–15 s |
| Generalised convulsive jerks | ~15 s |
| Decerebrate extension | ~20 s |
| Rhythmic abdominal breathing movements | From ~15–20 s |
| Decorticate flexion | ~40 s |
| Loss of tone | ~1–1.5 min |
| Last respiratory movement | ~1–2 min |
| Last isolated twitches | ~2–7.5 min (default 4 min) |

**Order: jerks → extension → flexion → limp.**

### 5.4 Seizure sequence

**Generalised tonic–clonic seizure (GTC) master schedule**, t = 0 at generalisation. Mean total **62 s** (30–120); only 27 % of seizures show every phase `[S R2-04:S3]` ✓ (M).

| Phase | t (s) | Body | Eyes / face | Jaw / tongue | Breathing | Skin / autonomic |
|---|---|---|---|---|---|---|
| Focal onset (wound-related, optional) | −10 to 0 | Contra hand and face clonic jerks 1–3 Hz; head turns **away** from the wounded hemisphere 30–90° over 1–3 s | Eyes forced away from the focus | Mouth pulled to one side | — | — |
| Pre-tonic clonic (p 0.2–0.3) | 0–5 | 2–6 bilateral irregular jerks at 1–3 Hz | — | — | — | — |
| Onset | 0–1 | Sudden LOC; stiff topple (B) or crumple | **Eyes open wide** (p 0.9–0.97), deviate up or sideways | Mouth opens | **Epileptic cry** (p 0.3–0.5): a forced expiration through closed cords, 0.5–3 s | Pupils 6–8, unreactive within 1–3 s |
| Tonic flexion | 0–3 (≤ 5) | Shoulders up and abducted, elbows half-flexed, **arms rise**, trunk flexes slightly | Up | Opens, then clamps | Air pushed out | HR rising |
| Tonic extension | 3–15 (tonic total 10–20; range 2–40) | **Back and neck arch**; legs extend and adduct; feet plantarflex; arms extend and turn in, or stay flexed; **figure-of-4** after a focal onset (extended elbow contra to the focus, p 0.3–0.5) | Open, deviated; face contorted | **Clenched**: lateral tongue-bite risk | **Apnoea**; grunt | **Cyanosis from ~10–20 s**; HR 120–160+; bladder may void |
| Vibratory transition | 15–20 (2–5 s) | Fine fast quiver, 8–12 Hz, 0.5–2° (additive animation) | — | — | — | — |
| Clonic | 20–60 (30–60; ≤ 90) | **Bilateral synchronous flexor jerks** (elbow 20–50°, knee 10–30°, trunk 5–15°), each 100–250 ms of contraction. **Frequency falls from 3–4 Hz to 0.5–1 Hz; gaps lengthen**; ~60–70 jerks in total | Lids jerk with each beat; eyes nystagmoid | **Jaw snaps shut with each jerk** (5–15 mm); froth (pink if the tongue is bitten) | Grunt on each jerk | Cyanosis peaks, then eases |
| End | ~60 | Last jerks 1–3 s apart; sometimes a final tonic spasm; **completely limp** | Drift; lids partly close | Slack | Deep sighing breath | Sweaty |

- **Clonic frequency** `[E]` ✓ qualitatively: f(t) = f_end + (f_start − f_end)·exp(−(t − t_c0)/τ), with f_start 3–4 Hz, f_end 0.5–1 Hz, τ 10–20 s. Stop when the next interval would exceed 2–3 s.
- **Probabilities per GTC** `[K] (L–M) R2-04 §4.2`: eyes open 0.9–0.97; cry 0.3–0.5; **lateral** tongue bite 0.2–0.35 (specific for GTC); froth 0.2–0.4; cyanosis 0.6–0.9; urine 0.2–0.4; faeces 0.02–0.05; vomiting afterwards 0.05–0.1; facial petechiae 0.05–0.15.

**Post-ictal state** `[K] (M) R2-04 §4.3`:

| t after the last jerk | Body | Eyes | Breathing | Response |
|---|---|---|---|---|
| 0–30 s | Totally limp where it fell | Half-closed 2–5 mm or open; roving or still deviated; pupils large and sluggish | Pause 5–20 s, then **deep, laboured, obstructed breaths** 20–30 /min, bubbling saliva, froth | None |
| 0.5–5 min | Limp; Todd's paresis of the seizing side (mean 173 s, 11 s – 22 min) | Pupils return to normal and reactive | Obstructed breathing eases over 1–5 min; colour from blue to pale | Withdraws and moans to pain |
| 5–15 min | Stirs, rolls, pulls at clothes; combative if restrained | Opens when stimulated | Normal | Confused words |
| 15–60 min | Sits up; headache, sore muscles, sleepy | Normal | Normal | Oriented by 30–60 min |

**Focal and other seizures** `[S R2-01:S107,S108,S109]` `[E]`:

| Type | Rhythm and amplitude | Duration | Consciousness |
|---|---|---|---|
| Focal clonic (hand, face) | 1–4 Hz, regular; finger/wrist 10–40° per jerk; mouth corner 3–8 mm; eyelid closure | 10 s – 2 min | Often kept |
| Versive | Head 30–90° away from the focus over 1–3 s; eyes 20–40° | 5–30 s | Lost at the end |
| Jacksonian march | Spreads in homunculus order, hand → forearm → arm → face (or foot → leg → arm → face), **5–30 s per segment** | 10 s – 2 min | Kept until it generalises |
| Frontal / SMA | Abrupt, asymmetric tonic posture (fencing-like arm, leg "bicycling"), vocalisation | 10–40 s | Quick recovery |
| Epilepsia partialis continua | One part at 0.5–3 Hz | > 1 h | Kept |
| Subtle status in coma (massive head injury > 30 min, p 0.05–0.1) | Rhythmic twitches of an eyelid, mouth corner, finger or toe at 0.5–3 Hz, 1–5 mm; nystagmoid eye jerks | Minutes–hours | Coma |
| Todd's paralysis | Weakness of the seizing side after the seizure | Mean 173 s (11 s – 22 min; case reports to 36–48 h); adds to the lesion deficit | — |

**Telling the collapses apart** (for animators) `[K] R2-04 §3.4`:

| Feature | Convulsive syncope / anoxic | GTC seizure | Anoxic tonic spasm | Knockout (fencing) |
|---|---|---|---|---|
| First | Fall, then jerks | Stiffening (often a cry), then the fall | Stiffening 10–30 s after flow stops | Instant tonic arm posture at impact |
| Jerks | 1–10, irregular, multifocal | Dozens, rhythmic, synchronous, **slowing** 3–4 → ~1 Hz | None or a few | None |
| Duration | 5–20 s | ~60 s (30–120) | 5–20 s | 2–10 s (≤ 20) |
| Colour | **Pale** | **Blue, congested** | Pale-grey | Normal |
| Afterwards | Awake < 30 s (if circulation returns) | Stupor with obstructed breathing, confused 5–30 min | Follows the underlying process | Wakes within seconds to minutes, dazed |
| Tongue | Tip, rarely | **Side**, p 0.2–0.35 | — | — |

### 5.5 Twitches, release movements, spinal reflexes

| Movement | When | Look | Probability / rate | Tag |
|---|---|---|---|---|
| Fasciculations (living) | Exhaustion, cold, adrenaline, hypoxia, shock | A 30–100 ms flicker under the skin; a finger or toe twitches 1–5 mm; calves, thighs, deltoids, face, eyelids | 0.1–2 /s per active site | `[K] (L)` |
| Eyelid myokymia | Same | Rippling of the lid | Bursts of 10–30 s | `[K] (M)` |
| **Release after upper-brainstem destruction** (midbrain / upper pons, medulla spared) | 0–60 s after the hit | Tonic extension (decerebrate-like) 5–30 s; then 2–8 irregular bursts of hip/knee flexion–extension of 10–40° over 10–60 s (human kicking is rarer, shorter and smaller than in animal footage); finger or face twitches | Tonic p 0.3–0.6; kicking p 0.1–0.2; twitches p 0.3 | `[E] (L) R2-04 §5.3` |
| Release after medullary / cervicomedullary destruction | 0–60 s | Flaccid at once; spinal-only kicks | Kicks p 0.05–0.15; twitches p 0.2 | `[E] (L)` |
| Massive bihemispheric destruction, brainstem intact | 0–60 s | Posturing | p 0.3–0.5 | `[E]` |
| **Spinal reflexes after brainstem death** | Brainstem death → `t_arr` + 60–180 s (the cord still perfused) | Undulating toe flexion (toes 2 → 5, 1–3 s waves); triple flexion (hip, knee, ankle) to a foot pinch, 1–5 s; brief finger or toe flexion; pronation–extension of an arm on neck flexion; respiratory-like shoulder heaves without air | Any movement p 0.2–0.4; **stimulus-triggered** (player flexes the neck or stamps on a foot) p 0.3–0.5 per stimulus | `[S R2-04:S11]` `[K]` ✓ (13–79 % across series; ~39 % Saposnik) |
| **Lazarus sign** | Same window; triggered by hypoxia or moving the body | Both elbows flex 90–130°, shoulders adduct 10–30° and flex 20–60°, hands rise to the chest, neck or chin, sometimes crossing; fingers flex; trunk flexes 10–40° as if sitting up; drive 30–50 %. **A slow target change, never an impulse**: rise 2–5 s, hold 3–10 s, fall 5–15 s; gooseflesh and sweating may accompany it | p 0.03–0.05 | `[K] (M)` |
| Post-mortem fine twitches | 1–15 min after `t_arr` | Fingers, eyelids, lips, calves | p 0.2–0.4 per body; 0.5–5 /min decaying with τ 3–5 min; none after 15–20 min | `[E] (L)` |
| Post-anoxic myoclonic status | Circulation continues or returns after > 5 min of brain hypoxia | Repetitive jerks of face, eyelids, trunk and limbs, **triggered by touch, a nearby shot or movement**, 0.5–2 bursts/s; the eyes may open and deviate up | p 0.2; hours | `[K] (M) R2-04 §5.2` |
| Idiomuscular bulge | Dead ≤ ~2 h; a direct hit on a muscle belly | A 5–20 mm local bulge; no joint motion > 5° | p 0.1–0.3 per hit | `[K] (M)` |
| Hemiballismus | STN roll (§1.2) | Violent flinging of one arm and leg: shoulder 40–120°, hip 20–60° per excursion; irregular bursts of 0.2–1.0 s at 0.5–2 movements/s; continues when lying down | Minutes–weeks | `[S R2-01:S25,S26]` |
| Intention tremor | Cerebellar hemisphere | 3–5 Hz, 1–5 cm at the fingertip, rising in the last 10–20 cm of a reach | While reaching | `[S R2-01:S44]` ✓ |
| Titubation | Vermis | Head and trunk 2–4 Hz, 1–3 cm | Sitting or standing | `[K] (L)` |
| Holmes (rubral) tremor | Midbrain, weeks later | < 4.5 Hz; rest + posture + intention | Time skips only | `[S R2-01:S44]` ✓ |
| Cadaveric spasm | Death during intense activity | A grip frozen at the moment of death; **hands only, never the face** | ≤ 0.01 | `[K] RB §6.6` |

**A dead body never** shivers, trembles, breathes rhythmically, postures, blinks, tracks or flinches at a nearby shot `[K] (H) R2-04 §5.5`.

### 5.6 Tremor, shivering and chattering (visual only: additive bone offsets after physics)

| Type | Frequency | Amplitude | When | Stops | Tag |
|---|---|---|---|---|---|
| Fear / adrenaline tremor | 8–12 Hz | 0.5–3 mm at the fingertip (0.2–1.5° at wrist and fingers); severe 5–10 mm; jaw, lips | During and after a violent event; lasts **5–30 min** | At LOC | `[K] (M) R2-04 §6.1` |
| Injured or exhausted leg under load | 4–8 Hz | Visible knee shake | Standing or kneeling | When unloaded | `[K] (L–M)` |
| Shivering | Bursts 4–8 per minute, each a 5–10 Hz visible shake | BSAS 1: neck and chest; 2: + arms (hands 5–20 mm); 3: whole body (shoulders 0.5–2°) | Core 35.5–36 °C (earlier with cold skin); peaks at 34–35 °C. After a major bleed: onset 10–40 min in a conscious class II–III casualty, p 0.3–0.5 | Obtundation, class IV, SpO₂ < 80 %, GCS ≤ 8, core < 30–32 °C, below a cord lesion | `[K] (M) R2-04 §6.2` ✓ |
| Teeth chattering | 5–12 Hz | Jaw 1–5 mm | Often the first sign of shivering; follows the bursts | With shivering; clenching stops it | `[E] (L)` |
| Gooseflesh | — | Bumps 0.5–1 mm on forearms, thighs, shoulders (normal map) | Living: cold or fear, onset 10–60 s. **Dead: hours** (rigor of the arrector pili) | — | `[K] (M)` |

- Shivering behaviour when conscious: hunched, arms folded, hands in the armpits, knees drawn up, "I'm so cold" `[K] (H)`.

### 5.7 Posturing episodes (timing)

| Quantity | Value | Tag |
|---|---|---|
| Latency from a noxious stimulus (pain, being moved, a nearby shot, chest pressure) | 0.2–1 s | `[E]` on `[K]` |
| Build-up / hold / release | 0.5–2 s / stimulus duration + 2–10 s (spontaneous episodes 5–60 s) / 1–3 s | `[E] R2-01 §18.2` |
| Refractory period | 5–20 s | `[E]` |
| During plateau waves | Bursts every 30 s – 5 min for 5–20 min | `[S R2-01:S86]` |
| Accompaniment | Moan or grunt at onset (V2), jaw clenching (decerebrate), sweating, HR and BP rise | `[K] (M)` |
| Progression | Decorticate → decerebrate → flaccid. Stopping at medullary failure is a bad sign | `[K] (H)` |

### 5.8 Implementation mapping

| Movement class | How to drive it | Parameters | Tag |
|---|---|---|---|
| Myoclonic jerks, gasp jerks, release kicks | Brief target offset of 10–30° for 80–200 ms at high stiffness, or an off-centre linear impulse J / r at distance r from the joint | Peak ω 1–8 rad/s; excursion 5–30° (fast but small; nothing flails across the room) | `[E] R2-04 §11.3` |
| Clonic seizure jerks | Synchronous bilateral target offsets at f(t) (§5.4) | Clonic tone state (§4.4) | `[E]` |
| Tonic phases, posturing, Lazarus | Joint targets with ramp, hold and release | §4.4 posture table | `[E]` |
| Tremor, shivering, chattering, vibratory phase | **Additive bone rotation after the physics step** (the 60 Hz tick undersamples them) | 0.2–2°, band-limited noise, burst envelopes | `[E]` |
| Fasciculations | Shader "twitch spots" (≤ 4 active per character) | Radius 10–30 mm; displacement 0.3–1.5 mm; rise 20–40 ms; decay 60–150 ms | `[E]` |
| Breathing and gasps | Additive chest and belly blendshapes or spine bones; neck and jaw as 20–40 % drive targets when limp, so gravity wins between gasps | §5.2 | `[E]` |
| Irregular events (jerks, twitches, coughs, spits) | Poisson scheduling: next event after −ln(u) / rate | — | `[E]` |
| Structured sequences (gasps, clonic phase, Lazarus, shivering bursts) | Explicit schedules, rolled once on state entry | — | `[G]` |

**Angular impulses for visible jerks** `[E] R2-04 §11.3`:

| Segment (about) | I (kg·m²) | Peak ω (rad/s) | J = I·ω (N·m·s) |
|---|---|---|---|
| Hand (wrist) | 0.0035 | 3–8 | 0.01–0.03 |
| Forearm + hand (elbow) | ~0.08 | 2–5 | 0.16–0.4 |
| Whole arm (shoulder) | ~0.45 | 1–3 | 0.45–1.35 |
| Shank + foot (knee) | ~0.40 | 1–3 | 0.4–1.2 |
| Whole leg (hip) | ~2.6 | 0.5–2 | 1.3–5.2 |
| Head | 0.03–0.10 | 1–4 | 0.03–0.4 |

### 5.9 Probability summary (defaults for tuning)

| Event | Default p | Condition |
|---|---|---|
| Agonal gasps | 0.45 / 0.4 / 0.7 / **0** | Destroyed heart or VF / exsanguination to PEA / asphyxia with a beating heart / medulla destroyed |
| Anoxic myoclonus at LOC | 0.8 / 0.5 | Sudden / slow onset (C-11: RB uses 0.9 for a destroyed heart) |
| Upgaze at LOC | 0.6–0.9 | Circulatory LOC |
| Anoxic tonic spasm | 0.15–0.3 | Arrest ≥ 15 s |
| Release extension / kicking | 0.3–0.6 / 0.1–0.2 | Midbrain or upper pons destroyed |
| Spinal reflex / Lazarus | 0.2–0.4 / 0.03–0.05 | Brainstem dead, heart beating (C-09) |
| Post-mortem twitches | 0.2–0.4 | First 15–20 min after `t_arr` |
| GTC cry / lateral tongue bite / froth / urine | 0.3–0.5 / 0.2–0.35 / 0.2–0.4 / 0.2–0.4 | GTC |
| Vomiting | 0.07 / 0.28 / 0.2–0.35 / 0.2–0.4 | Minor head injury / skull fracture / comatose massive head injury / abdominal or groin wound |
| Visible neurogenic-oedema froth | 0.2 | Massive head injury surviving > 15 min |
| Terminal secretions (bubbling at the lips) | 0.3–0.5 | Unconscious > 60 min |
| Shivering | 0.3–0.5 | Conscious, class II–III, 10–40 min |
| Urine at death | 0.2–0.3 | — |
| False last breath | 0.3 | If gasping |

### Simulation parameters (involuntary movement)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `gate_*` | §5.1 | bool | Checked on every event | `[K] (H)` |
| `gasp_schedule` | first 30 s; interval 10 × 1.3ⁿ; 8 gasps; amplitude × 0.85 | s | False last breath p 0.3 | `[E]` |
| `gasp_pose` | neck extension 5–30°; jaw 15–35 mm; shoulders 5–15 mm; inspiration 0.2–0.6 s; expiration 1–3 s | — | | `[E]` |
| `syncope_jerks` | 1–10 over 5–15 s, irregular | — | | `[S R2-04:S1]` ✓ |
| `anoxic_tonic` | p 0.15–0.3; 5–20 s; starts 15–30 s after `t_arr` | — | | `[K⚠]` |
| `cerebral_arrest_loc` | 5–10 (cuff) / 8–15 (heart); × 0.85 upright, × 1.2 supine | s | | `[K] (H)` ✓ |
| `ischaemic_beating_heart_seq` | LOC 10–15; jerks 15; extension 20; flexion 40; limp 60–90; last breath 60–120; last twitch 110–450 (240) | s | C-06 | `[K] (M)` ✓ recall |
| `gtc_total` / `tonic` / `clonic` | 62 (30–120) / 10–20 / 30–60 | s | | `[S R2-04:S3]` ✓ |
| `gtc_clonic_f` | 3–4 → 0.5–1 Hz, τ 10–20 s | — | Stop when the interval exceeds 2–3 s | `[E]` |
| `vibratory` | 8–12 Hz, 0.5–2°, 2–5 s | — | Additive | `[K] (L)` |
| `postictal_obstruction` / `confused` | 1–5 / 10–60 | min | | `[K] (M)` |
| `todd_duration` | 173 (11–1,320) | s | | `[S R2-01:S110]` ✓ |
| `jackson_segment_time` | 5–30 | s | Full march p 0.1 | `[E]` |
| `release_tonic_p` / `kick_p` | 0.3–0.6 / 0.1–0.2 | p | Midbrain or upper pons | `[E] (L)` |
| `spinal_reflex_p` / `lazarus_p` / `stim_p` | 0.2–0.4 / 0.03–0.05 / 0.3–0.5 | p | Window `t_arr` + 60–180 s | `[S R2-04:S11]` `[K]` |
| `pm_twitch` | p 0.2–0.4; 0.5–5 /min; τ 3–5 min; none after 15–20 min | — | | `[E] (L)` |
| `fear_tremor` | 8–12 Hz; 0.5–3 mm; 5–30 min | — | | `[K] (M)` |
| `shiver` | bursts 4–8 /min; 5–10 Hz visible; onset 10–40 min after a major bleed | — | | `[K] (M)` |
| `posture_trigger_latency` / `refractory` | 0.2–1 / 5–20 | s | | `[E]` |

### Visual/behavioural checklist (involuntary movement)
- A heart-shot or bled-out body is not still after it falls: eyes up for a few seconds, a handful of irregular jerks, maybe a brief rigid arch, then gasps with the head jerking back and the mouth gaping, spaced further and further apart for a few minutes.
- A medullary (lower brainstem) hit: **no breathing movement at all**, no gasps, no cough. Lips turn blue over a minute or two while the heart still beats.
- A seizure starts stiff (with a cry, eyes open, face turning blue), then jerks rhythmically, **slowing down** over about a minute, then a stupor with heavy obstructed breathing and froth.
- A faint shows few, irregular jerks and a pale face, and the person wakes in about 12–30 s.
- Minutes after a brainstem shot the toes may curl in a wave; rarely both arms slowly rise to the chest and sink back.
- A frightened survivor's hands and jaw shake finely for many minutes; a cold bleeding casualty shivers in waves, jaw first, until it drifts toward unconsciousness.
- Nothing in this layer looks voluntary, and nothing responds to the player the way a conscious person would.

---

## 6. Severe trauma visuals addendum

Source: R2-05. Its values are `[K]`/`[E]`; no web source was reachable in that session. RB §2 already covers entrances, exits, ranges of fire, the burst energy rule (`E_dep`) and ordinary wounds. This section lists what each **destructive** injury looks like, which render layers it needs, and what the behaviour system does with it.

### 6.0 Layer codes

| Code | Layer | Notes |
|---|---|---|
| `SDF` | Rest-space wound SDFs in the skin and tissue shaders | ≤ 64 per character, 3 × vec4 each (RB §2.0) |
| `TEX` | Texture-space damage and paint layer | Bruise, soot, blood film, drying, blanching |
| `MESH` | Authored damage-state meshes or fracture variants | Burst vault, plates, destroyed jaw, bone ends |
| `CAP` | Cross-section cap shader | Layered skin / fat / muscle / bone at cut or torn surfaces |
| `BS` | Blendshapes | Swelling, globe deflation, head collapse, chemosis, tongue swelling, flail paradox |
| `SB` | Soft-body or short bone chains | Tongue, scalp flaps, hanging globe, bowel loops, skin sleeves |
| `RB` | Rigid debris | Bone plates and chips, teeth, hemisphere masses, fragments |
| `PART` | GPU particles | Mist, droplets, froth, bubbles, fat globules, brain clumps |
| `FLUID` | Blood emitters, rivulets, pools | RB §3.11 |
| `DEC` | World decals | Spatter, cast-off, pools, smears, prints, voids |
| `SH` | Tissue material by tissue ID with an ageing lerp | §6.1 |
| `JNT` | Fracture joint inserted in the ragdoll | §4.2 |
| `EYE` | Eye mode switch | intact / ruptured / luxated / hanging / enucleated |

### 6.1 Exposed tissue palette (condensed; full table R2-05 §1.1)

| Tissue | Fresh | Living 30–60 min | Dead, drying 2–6 h | Roughness (wet → dry) | SSS (mm) | Signature |
|---|---|---|---|---|---|---|
| Dermis, cut edge | `#E3B7A6` | `#D9A796` | `#A8745E` | 0.45 → 0.75 | 1.0 | Pink-white band 1–4 mm |
| Subcutaneous fat | `#EBD27E` | `#E2C56C` | `#CDAA55` | 0.30 → 0.55 | 3–5 | Lobules 3–10 mm bulging 2–10 mm from a fresh cut |
| Galea / fascia / tendon | `#E0DAD2` / `#E4E2DC` / `#ECE8DE` | — | Translucent amber `#C9B98E` | 0.20 → 0.50; tendon anisotropic | 0.5 | Silvery; tendon "watered silk" banding |
| Skeletal muscle | `#8E2A2A` | Weak bloom toward `#A5362F` (≤ 30–50 % in the living) | `#6B3A2E` (brown, drying) | 0.25 → 0.60 | 1–2 | Cut across fibres: stippled end-grain, wide gape. Along: streaks, narrow gape |
| Cortical bone | `#E9DFCC` | `#EFE7D6` (chalky) | `#F1EBDF` | 0.50 → 0.80 | 0.3 | Matte, granular fracture face |
| Red / yellow marrow | `#B5524A` / `#E4C36A` | — | `#5E2A22` / `#B8923E` | 0.40–0.70 | 1–3 | Yellow beads 0.5–3 mm float on the blood |
| Grey / white matter; pulped brain | `#B79C94` / `#E6DACA`; `#9E5A55` | — | `#8A6E66` / `#BFAE98`; crust `#6A3A34` | 0.15 → 0.55 | 2–3 | The softest tissue: sags, smears, strings; pulp yield stress 50–200 Pa |
| Liver / spleen / kidney | `#6E2C22` / `#5E4A5C` capsule, `#5A1624` pulp / `#7B3B2E` | darker | `#4E2219` / `#463444` / `#5A2C22` | 0.15 → 0.50 | 0.5–1 | Inelastic: stellate cracks and pulp |
| Lung (aerated / collapsed / contused) | `#D9A5A0` + black lines / `#8A3A4A` / `#5A1A2A` | — | `#9A6A68` | 0.30 → 0.55 | 1–2 | Spongy; exudes pink froth |
| Myocardium | `#7A2A28` | `#6E2624` | `#5A2220` | 0.30 → 0.55 | 1 | Coarse spiral bundles under a glossy epicardium |
| Artery / vein / nerve | Pale ring `#E8D2C8` / `#4E3A5E` / `#EDE6D2` | — | — | 0.25–0.35 | 0.5–1 | Artery pulsates 5–10 % per beat; the vein is a flat ribbon; the nerve is a white string that does not bleed |
| Sclera / uvea / vitreous | `#F2EEE6` / `#3A2420` / clear gel (IOR 1.336) | — | Sclera `#D8CFC0` | 0.15 | 1.5 | §6.2 row 13 |

**Ageing** `[K] (M) R2-05 §1.5`:

| Time | Living (perfused) | Dead |
|---|---|---|
| 0–2 min | Everything wet and glossy (roughness 0.1–0.3) | Same, no new ooze |
| 10–30 min | Fat edges go matte | Muscle blooms, then turns tacky |
| 30–120 min | Yellow-pink exudate and fibrin film | Muscle browns; bone chalks |
| 2–6 h | Margins swell | Parchment-brown edges; brain crust |
| 6–24 h | — | Dark leathery surfaces |

Living tissue ages at 0.3–0.5 × the dead rate.

### 6.2 Injury recipes

**Head (bursts, blunt destruction, scalp)**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 1 | **Contact or ≤ 1 m shotgun to the head** (vault burst) | `E_dep` ≥ 500–700 J (p 0.95–1.0 for 12-gauge at contact to 1 m); ejected fraction capped by site | Entrance 3–5 cm stellate with soot and muzzle stamp. Far-side crater 8–20 cm, or the upper vault missing. Scalp split into 3–8 radial flaps (50–150 mm) with torn, everted margins and matted hair. The **face stays as a loose sagging mask**: eyes at different heights, bulging or ruptured (p 0.3–0.6 per eye). Intraoral: lips split at the corners (p 0.3–0.6), cheeks torn; ceiling deposits. **The head collapses into a soft "bag"** (20–60 % of 20–80 fragments leave, the rest stay under the scalp) | Burst 0–1 ms; ejection 1–10 ms; plume 10–100 ms; fallout 0.2–1.5 s; ceiling drips 1–60 s. Ejecta: fine 20–60 m/s, clumps 10–40 m/s, plates 5–20 m/s, in a 20–40° cone plus a slow 60–90° component. The heart pumps blood out of the defect for 1–10 min | `MESH` (burst vault, flaps) `BS` (collapse 0.3–0.8 when resting) `RB` (plates, chips) `PART` `FLUID` `DEC` (cone, ceiling) `SH` | Instant flaccid collapse **where it stands** (no throw); a single jerk or extensor stiffening in 0–2 s; twitches ≤ 5–20 s; apnoea if the brainstem is destroyed |
| 2 | Buckshot to the head at 1–3 m | 9 pellets in a 3–8 cm group | Separate or confluent 6–9 mm holes; radial cracks linking them; 0–30 % of the brain ejected; partial burst only at the near end | — | `SDF` `MESH` (cracks) `PART` | As the track resolves (§1) |
| 3 | **Rifle burst / Krönlein shot** | `E_dep` ≥ 1,000 J partial; ≥ 1,500 J Krönlein (intact hemispheres p 0.2–0.4) | Small entrance (5–8 mm skin), massive exit (40–120 mm). The vault splits into 4–30 plates **along sprung sutures** (gaps 2–20 mm); 2–6 scalp burst lacerations (30–150 mm) over the vertex. The brain is ejected as a large mass or as recognisable hemispheres (400–600 g) lying 0.5–5 m down-range; the posterior fossa contents often remain. Soft-point bullets leave a "lead snowstorm" of fragments. 5.56 mm varies from a clean perforation to a full burst | As row 1 | `MESH` (suture-aware split) `RB` (hemisphere soft-rigid meshes that slide 0.1–0.5 m) `PART` `DEC` | As row 1 |
| 4 | **Hammer at one site, progression** | Blow energy 30–120 J; fracture logistic (frontal 23 J, temporal 10 J, parietal 30 J, occipital 40 J) | **Blow 1**: crescent or stellate laceration 10–40 mm, bump and bruise, **no spatter**. **Blows 2–3**: depressed fracture 25–40 mm across, 5–15 mm deep, 2–6 inner-table fragments driven in; dural tear p 0.3–0.6; impact spatter and cast-off start. **Blows 4–8**: ragged 40–80 mm defect; **comminuted mosaic** of 10–30 fragments (5–25 mm) with concentric rings and radial lines to 50–150 mm; fragments driven 10–30 mm into the brain; pulped brain and chips extrude. **> 8**: a 60–120 mm cavity; loss of vault shape; skull-base fractures | Per blow: +3–10 mm depression, +2–6 fragments. Oblique blows: terraced depressions. Exception: if the head is already bleeding, the first blow at a new site does spatter | `SDF` `MESH` (depression, mosaic) `BS` `RB` (chips) `PART` `DEC` (impact spatter 20–300 stains per blow; cast-off trails) | Coup stun under the site; M1/S1 deficits if over the strip; seizure risk (§1.8) |
| 5 | Crushed head (stomp on a hard floor, heavy object) | 50–200 J per stomp; repeated | Flattened perpendicular to the load (height −20–60 %) and widened; eggshell comminution (10–60 fragments); **bursting scalp lacerations** at the sides (30–120 mm) with tissue bridges; brain at the ears, nose and orbits; eyes pushed forward or out; jaw dislocated | Crepitus when moved | `MESH` `BS` (flatten) `RB` `PART` | Immediate death with brief terminal twitches |
| 6 | **Brain herniating through a skull defect** (living victim) | Open skull + rising ICP | The brain bulges 5–30 mm above the bone edge, growing over minutes to hours; surface purple-red and congested, with a dark haemorrhagic collar `#5A1A22` where the edge strangles it; **pulses 1–3 mm with each heartbeat** and 0.5–2 mm with breathing; pulp, CSF and blood ooze 1–10 mL/min, surging × 2–5 with coughs and screams; through a 10–20 mm gap it extrudes as a soft ribbon | Pulsation stops at the last effective beats; the surface dulls within minutes | `BS` (bulge) `SB` `SH` `FLUID` (CSF-diluted: pinker, spreads 1.5–2 × wider, does not clot) | ICP model §1.7 |
| 7 | **Scalp avulsion** | Traction on bundled hair; tangential blow; knife scalping | A thick hairy flap (5–7 mm) with a **glistening white-grey galea underside**, separating through the subgaleal plane. Underneath: pink membrane (`#E6CFC4`) with pinpoint bleeding, or bare ivory bone with red pinpoints and wavy sutures. Margins torn and curled, retracted 5–10 mm. Partial avulsion: a flap hinged at the temple or occiput hangs over the face or neck. Knife scalping: an oval 8–15 cm crown defect with incised edges | Bleeding **50–150 mL/min**, falling to 20–60 mL/min over 10–30 min (the vessels are held open); class III shock after 15–45 min | `MESH` / `SB` (flap) `CAP` `SH` `FLUID` | Conscious: blood in the eyes, blinks, wipes, pushes the flap back; exposed bone itself is not painful |

**Face and jaw**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 8 | **Lower-face / mandible avulsion** | `E_dep` ≥ 400–700 J in the lower face (submental rifle or shotgun) | Lower lip and chin gone; **the tongue hangs 5–10 cm below the upper teeth** (swells +20–50 % over 10–60 min); the floor of the mouth is open into the neck (pale submandibular glands `#D8B8A0`); the remaining rami hang with a few teeth; ropes of blood and saliva | Bleeding 100–300 → 30–100 mL/min after 5–10 min; swallowed blood (> 150 mL) is vomited dark 10–30 min later | `MESH` (destroyed jaw) `SB` (tongue, 4–6 joints) `BS` (swelling) `PART` `FLUID` | **Often conscious** (p 0.7–0.9 if the track stays in front of the skull base): leans forward, grunts with blood bubbling at the mouth, spits teeth; **supine → the tongue falls back → obstruction** (LOC 1–3 min). Can still moan and scream |
| 9 | Mid-face avulsion | Tangential rifle; close shotgun to the mid-face | Open nasal cavity: septum, dark red scroll-shaped **turbinates** (bleed heavily), pale-lined sinus cavities; upper teeth lost; globes sag 2–10 mm when the orbital floors are gone | Bleeding 50–200 mL/min, mostly backward into the throat | `MESH` `SH` `FLUID` | Coughs blood; airway risk |
| 10 | Transfacial (cheek to cheek) / bilateral mandible fracture | Handgun or rifle across the face; hammer | Teeth visible through the cheek defect; the front jaw segment pulled down and back ("flail"); the mouth hangs open | Tongue falls back when supine | `SDF` `JNT` (jaw) `BS` | Drools; the lips cannot meet; airway risk when supine |

**Eye**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 11 | **Ruptured globe** (blunt or penetrating) | Normalised energy ≥ 24,000–35,000 J/m² for 50 % risk (a hammer face gives 37,000–245,000; a fist is stopped by the rim; a thumb or pellet at 40–75 m/s reaches the globe) | **Soft, deflated, wrinkled globe** (volume −20–80 %); the corneal highlight breaks into patches; **360° dark red ballooned chemosis** (`#7A0A14`, 2–6 mm); peaked "teardrop" pupil; a dark uveal bead 1–5 mm at the wound; clear-to-pink vitreous strands 1–3 cm draping over the lid; hyphema ≤ 0.25 mL with a level ("eight-ball" when full); lens dislocated or extruded, clouding over minutes to hours; lids swell shut in 10–60 min | Blood-tinged tears | `EYE` (ruptured) `BS` (deflation, chemosis) `SB` (vitreous strands) `PART` `SH` | Blepharospasm, hand over the eye, tearing; oculocardiac reflex (HR −20–40 %, nausea, faint); misreaches (loss of depth perception) |
| 12 | Luxation / hanging globe / enucleation | Thumb gouge, orbital burst | **Luxated**: the globe 10–20 mm forward, lids locked behind its equator. **Hanging** (needs optic-nerve avulsion or orbital-wall destruction to reach the cheek; with the nerve intact, travel is only ~10–15 mm): white sclera with 1–4 red muscle stumps and a white nerve cord 3–6 mm thick. **Enucleated**: dark red socket, yellow fat herniating, lids sinking; the detached globe clouds in 1–2 h and dries yellow-brown | Socket bleeding 10–50 → 5–15 mL/min after 5 min | `EYE` `SB` (hanging chain) `RB` (detached globe) `SH` | Double vision if the luxated eye still sees |

**Neck**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 13 | **Cut throat through the trachea** | Knife depth reaches the airway | Gape 10–30 mm (skin), 30–50 mm through the trachea with the head extended (× 0.3–0.5 flexed); cartilage rings and pink mucosa; the lower trachea retracts 1–3 cm; exhaled air **bubbles through the blood** (2–15 mm bubbles, pink foam); inspiration sucks blood in and the cough **sprays out of the neck wound** (1–3 coughs per 10 s) | Aspiration caused 36.5 % of deaths in a 74-case autopsy series ⚠ | `SDF` `CAP` `PART` (bubbles, foam, spray) `FLUID` | **Aphonic below the cords** (mouths words without airflow); `HOLD_NECK` |
| 14 | Carotid / jugular cut | Track or blade reaches the carotid sheath | Scarlet pulsing jet 0.5–1.5 m from the carotid; dark welling from the jugular that surges on expiration and screaming and sucks air on inspiration (frothy dark blood) | Jet shortens as MAP falls; stops at `t_arr` | `FLUID` `DEC` (arterial arcs, one cluster per beat) | §8 scenario 5 |
| 15 | Near-decapitation (close shotgun to the neck) | Contact–1 m shotgun to the neck | Gape 5–15 cm; vertebra or disc visible; trachea and oesophagus open; carotid stumps jetting; **the head hangs back or sideways on a bridge of skin and posterior muscle** | Cord transected: immediate flaccid collapse and apnoea | `MESH` `JNT` (neck limits removed) `CAP` `FLUID` | Cut strings |
| 16 | Complete decapitation | Heavy chop or tearing force; **a knife only through a disc space after 30–80 strokes (30–180 s)** | Body stump: skin retracted 1–3 cm; muscles retracted unevenly (SCM 2–4 cm); open tracheal ring; carotid stumps jetting 20–60 cm and fading to welling in 10–30 s; flat jugular stumps; white disc annulus or red cancellous bone; the cord as a white 10–13 mm cylinder with a grey butterfly in section | Body stump external loss 500–1,500 mL over 1–3 min. Head: LOC **4–10 s (default 7)**; eyes open; facial twitches, jaw and lip movements, gasp-like mouth opening for 10–30 s; pupils dilate over 30–90 s; **eyes never rolled back** | `MESH` `CAP` `RB` (head) `FLUID` | The body drops flaccid; brief limb jerks in the first seconds; no running |

**Limbs**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 17 | **Open long-bone fracture** | Fracture + open probability (tibia 0.25–0.4; ulna 0.15–0.3; radius 0.1–0.2; humerus 0.05–0.15; femur 0.05–0.1 blunt; gunshot 1.0) | **Inside-out**: a 0.5–3 cm slit wound with a bone spike protruding 1–8 cm: an **ivory cortical ring 2–7 mm thick around a yellow greasy marrow plug** (shaft) or red sponge (bone end), a torn glossy periosteal collar, clinging muscle fibres, fat beads on the blood. The spike **slips back under the skin when the limb straightens** (visible only while angulated > 15–20°). Patterns: transverse (direct blow), butterfly, **spiral with long spear-like points** (torsion; 2–4 × shaft diameter), comminuted (high energy) | Femur: shortening 2–5 cm, foot turned out 45–90°; tibia angulation 10–45°; thigh swells +2–3 cm per litre of blood | `MESH` (fracture variant) `JNT` (±30–90° bend, ±20–60° twist, 0.05–0.2 × stiffness) `CAP` `SH` `PART` (fat beads) | §3.4 rows 13, 20–24; the sight of their own bone can trigger a faint (p 0.02–0.05) |
| 18 | Rifle through a long-bone shaft | Rifle | 3–10 cm of shaft pulverised; 20–100+ fragments driven 2–10 cm into the muscle; exit 5–15 cm with bone protruding; satellite exits (2–5 mm) 1–5 cm around it (p 0.3–0.7) | — | `MESH` `RB`/ray-cast secondary tracks `SDF` | Secondary fragments cut vessels they cross (§6.2 row 26) |
| 19 | Near-amputation | Close shotgun, rifle, heavy crush | The limb hangs on a bridge of skin and muscle; ragged bone ends; distal limb pale and cold if the artery is cut | — | `MESH` `JNT` `CAP` | Arm or leg fails completely |
| 20 | Degloving | Open: shear (close tangential shotgun, heavy tangential blow). Closed: stomp with sliding | **Open**: a skin sleeve rolled back like a sock; yellow fat on its underside with perforator stumps bleeding every 2–4 cm; silvery fascia over the muscle; the flap goes pale, then dusky purple `#6A4A6A` over hours. **Closed**: a soft sloshing swelling (50–500 mL) under loose, bruised, intact skin | — | `SB`/`MESH` (sleeve) `CAP` `BS` (fluctuant swelling) | Pain at the margins |

**Chest**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 21 | Rib fractures, **flail chest**, sternum | Compression ≥ 20–25 % of chest depth (fracture), 35–40 % (flail); hammer on the lateral chest p 0.5–0.8; punch 0.02–0.1 | Direct-blow ends driven inward; a flail segment (≥ 2 adjacent ribs × ≥ 2 breaks) **sinks on inspiration and bulges on expiration**: 5–10 mm quiet, 10–30 mm laboured, up to 50 mm in distress (half for 2-rib segments), masked by muscle splinting for 5–120 min; sternal step 5–15 mm | Paradox grows as the muscles tire | `BS` (paradox, driven by the breath flow) `MESH` | RR 25–40 shallow with a catch at the end of each inspiration; holds the side; leans toward it; refuses to lie flat |
| 22 | Subcutaneous emphysema / traumatic asphyxia | Lung or airway injury / sustained compression ≥ ~body weight for 1–5 min | Emphysema: puffy swelling spreading chest → neck (10–60 min) → face (30–180 min), eyelids swelling shut. Traumatic asphyxia: **deep purple-blue face, neck and upper chest `#5A3A6A` sharply cut off at the compression line**, with petechiae and bilateral subconjunctival haemorrhage | Persists after release | `BS` `TEX` `SH` | — |
| 23 | **Sucking chest wound** | Chest-wall defect ≥ 10–13 mm (≥ ⅔ of the tracheal diameter; a rule of thumb) | Inspiration: blood at the wound is drawn in, edges pull inward. Expiration: **pink froth bubbles and builds around the hole**, fine droplets spray. Through a large wound the lung shrinks into a dusky rubbery mass in 2–10 s; pink lung may bulge 1–5 cm out on a cough | A tension variant (valve-like wound, p 0.1–0.3 of lung wounds) evolves over minutes: that side stops moving, neck veins distend, grey-blue collapse | `SDF` `PART` (froth 0.1–1 mm, bubbles 2–10 mm) `BS` | Froth and sucking at the hole move with each breath (see the look column) |
| 24 | **Heart wounds** (open chest or large defect) | Track or blade into the heart | **LV**: scarlet jets in systole only, 20–60 cm through an open wound. **RV**: dark surges 5–30 cm. **Atria**: continuous dark welling with a double swell per beat. **Coronary**: continuous spurting; the downstream muscle turns dusky and stops within 1–5 min. **Tamponade**: a tense, domed, **dark blue-purple sac** (`#3A1A2E`) with a small, fast, feeble heart inside (autopsy volume 150–500 mL). **Rifle or close shotgun**: ragged stellate bursts 3–8 cm, a flooded chest. **VF**: surface shimmering "bag of worms" at 4–8 Hz, finer over minutes | Stab chamber: RV 0.42, LV 0.37, RA 0.16, LA 0.05; second chamber p 0.2–0.3. Self-seal p: LV < 1 cm oblique 0.3–0.5, RV 0.2–0.4, atria 0.05–0.1 | `MESH` (beating heart states) `FLUID` `SH` | §8 scenario 4 |

**Abdomen**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 25 | Liver / spleen / kidney (AAST 2018 grades) | Knife II–III; handgun III (+ 1–3 cm stellate fissures); rifle or close shotgun IV–V (**stellate bursting**, fissures 3–10+ cm, 3–15 loose fragments); blunt I–III (delayed splenic rupture p 0.02–0.1, 30 min – 48 h) | Liver: glossy capsule over dark red-brown friable tissue, green bile staining. Spleen: dark purple pulp welling, or shattered in a clot. Kidney: radial splits toward the hilum; red urine. Tense blue-black subcapsular haematomas (10–100 mm) | Drive bleeding from the vessels hit (RB §3), not from the grade alone | `MESH`/`SDF` (organ states) `SH` `FLUID` | Little external blood, progressive pallor; Kehr's sign (left shoulder pain) |
| 26 | Evisceration | Abdominal wall wound ≥ 30–50 mm (omentum) or ≥ 50–80 mm (bowel) | Yellow fatty omentum first; glistening pink-grey small bowel (2.5–3 cm) with **slow peristaltic waves** (8–12 /min, 1–2 cm/s); greyer colon; mesentery with pulsating arcades; protrusion grows with coughing and screaming; a trapped loop turns dusky `#6A3A5A` over 30–120 min | — | `SB` (bowel loops) `SH` | The victim holds the bowel in with the hands and bends forward |

**Secondary missiles and bloodstains**

| # | Injury | Trigger rule | What the player sees | Dynamics and timing | Layers | Behaviour hand-off |
|---|---|---|---|---|---|---|
| 27 | Bone and teeth as secondary missiles | A bullet striking bone | Handgun through the skull: 3–15 inner-table chips (1–10 mm) driven 1–5 cm into the brain in a 20–40° cone. Rifle through a long bone: 20–100+ fragments at 50–300 m/s. Teeth: 2–30 pieces embedded 5–30 mm in the tongue and cheeks. Fragments below 50–75 m/s at the skin stay as lumps | — | Ray-cast secondary tracks (not rigid bodies) `SDF` | A bullet near the spine can paralyse through fragments alone |
| 28 | Scene bloodstains | Every blood event | See §6.3 | RB §3.11 | `DEC` `FLUID` | — |

### 6.3 Bloodstain events → patterns (condensed from R2-05 §15)

| Event | Patterns to spawn | Key numbers |
|---|---|---|
| Gunshot, head | Back-spatter (30–320 drops within ~0.5 m on the gun side), denser forward cone (2–5 ×), burst ejecta, pool | RB §2.1.3 |
| Gunshot, trunk or limb | Little at the entrance; forward spatter at the exit; drips; pool | — |
| Knife, first stab / repeated stabs | Almost nothing / backswing cast-off trails (5–60 stains of 2–8 mm per trail, 0.3–2 m), cessation cast-off, soaked hand and sleeve | Cast-off needs blood already on the weapon |
| Neck cut | Arterial arcs and zigzags (6–25 mL per beat, 5–30 mm stains, one cluster per beat, lower and smaller as MAP falls); expirated spray; heavy flows down the chest; large pool | Stains from drops > 4–5 mm (30–60 µL) run on walls |
| Hammer, first blow / later blows | **None** / impact spatter 20–300 stains (0.5–4 mm, within 0.5–1.5 m) per blow, a cast-off line on the ceiling per backswing, brain and bone particles once the skull is open | — |
| Punching a bleeding face | Small impact spatter on fist, forearm and floor; nose and mouth drips; expirated spray on coughs | — |
| Victim walking or crawling | Drip trail (spacing = walking speed / drip rate; round drops when walking, elongated drops with tails when running), hand prints, slide marks on walls, knee and hand smears | — |
| Coughing blood | Small pink stains (0.1–4 mm) with vacuole rings in 30–60 % | — |
| Body dragged / stepped in | Drag trail / footprints fading over 6–13 steps (× 0.60–0.80 per step) | — |
| Time | Pool gels in 5–15 min (3 min for thin films); clot shrinks to ~50 % in 1–2 h; serum ring (2–20 mm) from 30 min – 3 h; cracked crust at 12–72 h | — |
| Objects in the spray | A clean silhouette (void) | — |

### Simulation parameters (severe trauma visuals)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `burst_E_dep` / `partial` / `kronlein` | 600 (500–700) / 1,000 / 1,500 | J | Contact-gas bonus: handgun 50–150, magnum 100–250, rifle 300–600, shotgun 400–800 | `[E] R2-05 §2.1` |
| `vault_fragments` / `leave_fraction` | contact 12-gauge 20–80; slug 15–50; buck at 1–3 m 3–20 / 0.2–0.6 | count / — | | `[E]` |
| `head_collapse_blend` | 0.3–0.8 | — | Scales with the fragmented fraction | `[E]` |
| `ejecta_v` fine / clump / mass | 20–60 / 10–40 / 5–20 | m/s | Cone 20–40° + slow 60–90° | `[E]` |
| `kronlein_hemisphere_p` | 0.2–0.4 above 1,500 J | p | | `[E]` |
| `hammer_per_blow` | +3–10 mm depression; +2–6 fragments; dural tear 0.3–0.6 (blows 2–3), 0.9 after | — | | `[E]` |
| `herniation_bulge` / `pulse` / `ooze` | 5–30 over 10–120 min / 1–3 / 1–10 (surges × 2–5) | mm / mm / mL/min | Living only | `[E]` |
| `scalp_avulsion_bleed` | 50–150 → 20–60 | mL/min | Corrected in R2-05 | `[E]` |
| `tongue_hang` / `swelling` | 50–100 / +20–50 % over 10–60 min | mm / — | | `[E]` |
| `globe_rupture_50` | 35,000 (24,000–35,000) | J/m² | Impactor width vs the 35 × 40 mm rim | `[K] (M)` |
| `hanging_globe_max` | 10–15 (nerve intact) | mm | | `[E]` |
| `open_fracture_p` | tibia 0.25–0.4 … femur 0.05–0.1; gunshot 1.0 | p | | `[E]` |
| `bone_spike_visible_if_angle_gt` | 15–20 | ° | | `[E]` |
| `flail_paradox` | 5–10 / 10–30 / ≤ 50 | mm | Quiet / laboured / distress | `[E]` |
| `open_ptx_threshold` | 10–13 | mm | Rule of thumb | `[K] (H)` |
| `lv_jet_height_open` / `rv` | 200–600 / 50–300 | mm | Systole only for the LV | `[E]` |
| `severed_head_loc` | 4–10 (7) | s | | `[K] (M)` |
| `peristalsis` | 8–12 /min, 1–2 cm/s | — | | `[K] (M)` |
| `impact_spatter_per_blow` | 20–300 stains, 0.5–4 mm | — | Only with exposed blood | `[E]` |

### Visual/behavioural checklist (severe trauma visuals)
- A close shotgun blast to the head **splits** it rather than popping it: a far-side crater, radial scalp flaps, a sagging face mask, a soft misshapen head that grates when moved; the body drops where it stood and the heart keeps pumping blood out of the head for minutes.
- A handgun never bursts a head. A 5.56 mm head shot is sometimes a clean hole and sometimes a burst.
- Hammer blows escalate visibly: split scalp and lump → punched-in depression → a mosaic of loose pieces with brain and chips coming out; no spatter from the first blow.
- A victim with the lower jaw gone is often awake, leaning forward, the tongue hanging, spitting teeth, fighting to sit up if laid back.
- A ruptured eye is a soft, wrinkled globe in ballooned dark red conjunctiva with jelly at the wound, not a neat hole.
- An open shin fracture shows an ivory ring of bone around a yellow greasy core that disappears back under the skin when the leg is straightened.
- A large chest wound sucks on inspiration and blows pink froth on expiration; a cut windpipe bubbles while the victim mouths words.
- Everything inside the body has its own colour: yellow fat, silvery fascia, ivory bone, purple spleen, red-brown liver, pink lung.

---

## 7. Audio design spec

Removed: the user removed audio from the game. Breathing, gasps, coughing and vocal effort are shown visually (chest, jaw, mouth, face) — see §2 and §5.

---

## 8. Timelines: eight scenarios, second by second

**How to read the scenarios:**
- Times are **real time** from t = 0 (contact). The game plays the first 60 s after any critical event, and the 60 s either side of cardiac arrest, at 1×; the rest runs at the RB §1.3 band scale ("game").
- Each scenario lists its **setup** and the **rolls** used (seeded; the main line is one legal outcome) and ends with its main **variants**.
- Every event cites the section that specifies it. Tags are in those sections.
- Reviewers replay each scenario at 1× and check the order and timing of events (§9).
- There is no sound (§0.3). *Breathing and mouth* is chest, jaw, mouth and face movement (quoted words are mouth movement only); *Other visible events* lists blood and fluid events off the body.

### 8.1 Brainstem shot

**Setup.**
- 9 mm FMJ from 3 m behind a standing, relaxed man holding a pistol in the right hand.
- Entrance at the midline of the skull base, just below the external occipital protuberance. The track runs forward and slightly upward through the vermis, **medulla** and lower pons, the clivus and the nasopharynx, and exits beside the nose.

**Rolls.**
- Medulla destroyed (variant a).
- Catecholamine surge: yes (p 0.5).
- Small twitches in the first 30 s: yes (p 0.2–0.3).
- Spinal reflex: yes (p 0.2–0.4).
- Lazarus: no (p 0.03–0.05).
- Post-mortem twitches: yes.
- Lids at death: open.

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0 ms | Head nods 1–3° forward (bullet exits, f_ret 0.1–0.3); **no startle** (the brainstem is destroyed) | Expression frozen; lids stay where they are | Breath stops (medulla) | — | Tone lost from 0 s (§3.4 row 1) |
| 1–10 ms | — | — | — | — | Forward spatter cone from the face exit (1–4 m); back-spatter ≤ 0.5 m toward the shooter; bone chips and a little brain at the exit |
| 0–100 ms | Tone ramps to 0 (τ 60–100 ms); ≤ 1–2 cm sag | — | — | — | §4.4 off-switch |
| 100–250 ms | Knees go forward, hips flex, head lags; the **grip opens** | Jaw starts to drop | — | — | §4.5 A |
| 0.3 s | The pistol leaves the hand | — | — | — | §3.4 row 1 |
| 0.35–0.50 s | Knees hit the floor at 2–3 m/s; the arms seem to float up | — | — | — | — |
| 0.8–1.0 s | The trunk pitches forward; **face and forehead strike the floor at 3–5 m/s with no hand in front**; the head rebounds 1–5 cm; the arms slap down 50–150 ms later | Lids drop 2–4 mm over 1–3 s; **no blink ever again** | Chest huff on trunk impact | — | §4.6: head last and hardest |
| 1–2 s | Settles prone; the head rolls onto its cheek (p 0.85); arms beside the body palms up; feet flat | Eyes slightly divergent / skewed and motionless; pupils normal size at first | **No chest movement at all** | — | — |
| 4 s, 11 s | A single finger twitch; a small foot twitch | — | — | — | §5.5 release after medullary destruction |
| 0–60 s | Still | Doll's eyes absent (pons involved) | No breathing, **no gasps, no cough** | Drips from the nose and exit wound fall into a spreading pool | Catecholamine surge: HR 120–160, SBP +20–60 for ~40 s; then vasomotor loss, MAP 40–60 by 30–60 s. Face and exit wounds bleed in pulses at falling pressure |
| 60–120 s | — | Pupils begin to dilate | — | Drip rate falls | **Lips and tongue turn dusky blue** (Hb intact) |
| 3:10 | **Toes of the right foot curl one after another (2 → 5)**, twice, over 6 s | — | — | — | Spinal reflex window (§5.5). Moving the body or flexing the neck retriggers it with p 0.3–0.5 |
| 3–5 min | Still | Pupils 5–7 mm | — | — | Hypoxic bradycardia < 40–50; bleeding weakens |
| **6:00** | — | — | — | Pulsing ooze stops | **`t_arr`** (PEA → asystole); gravity drainage only |
| 6–20 min | 3 faint twitches (an eyelid, the left calf, a finger) by 12 min, then none | Pupils 6–8 fixed; tear film gone; gloss fading | — | — | §5.5 post-mortem twitches |
| **11:00** | — | — | — | — | Dead flag (`t_arr` + 300 s); post-mortem clocks (RB §6) |

- **Game time**: 0–60 s at 1×; 1–5 min at 4×; 5–7 min at 1× around `t_arr`; then POSTMORTEM. About 3 min of play.
- **Variants**:
  - (b) Pons destroyed with the medulla spared: pinpoint pupils (1–1.5 mm), ocular bobbing, apneustic or cluster breaths for 0–5 min, then terminal gasps (p 0.3–0.5).
  - (c) Midbrain destroyed: mid-position fixed pupils 4–6 mm, CN III eye down and out; **decerebrate stiffening (p 0.3–0.6) makes it a plank topple (B)** with arms straight and turned in, head impact 5–7 m/s; breathing continues (central neurogenic hyperventilation) and then fails; 2–8 irregular leg kicks over 10–60 s (p 0.1–0.2).

### 8.2 Frontal-lobe pistol shot (dominant hemisphere, conscious survivor)

**Setup.**
- 9 mm FMJ from 5 m into a surprised, unarmed bystander facing the shooter.
- Entrance in the left forehead, 3 cm above the brow and 3 cm left of the midline. The track runs laterally and slightly downward through the left dorsolateral prefrontal cortex and the inferior frontal gyrus (`Broca_ext`) and exits at the left temple.
- Destroyed fraction: `PFC_dl_L` 0.45, `Broca_ext` 0.35, plus stun within 18 mm (0.7, decaying).

**Rolls.**
- Concussive collapse: yes (p 0.7–0.9).
- Impact apnoea: yes, 40 s (p 0.6).
- Seizure in the first hour: no (p 0.05–0.10).
- Orbital-roof fracture: yes (p 0.82).
- Vomiting: yes at ~4 min.
- Left-dominant: yes (p 0.90).

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0 ms | Head nods 1–2° back | — | — | — | Entrance ~7.5 mm with a 2 mm collar; exit 10–30 mm stellate at the temple with bone chips and brain; back-spatter ≤ 0.5 m toward the shooter; forward cone on the wall to the left |
| 40–60 ms | — | Startle blink begins | — | — | L1 fires before the concussive collapse |
| 100–200 ms | **Concussive LOC**: tone lost; the startle hunch had tipped the body forward | Lids stay part-open | — | — | Row 2 of §3.4 |
| 0.35–1.1 s | Forward crumple (A), a quarter-turn left; no hands; forehead and nose strike the floor at ~4 m/s | — | — | — | — |
| 1–2 s | Prone, head on the right cheek (wound side up) | Pupils equal and reactive; doll's eyes present | **Impact apnoea**: no breathing | — | Catecholamine surge: HR 140, SBP +40 for ~30 s |
| 5–40 s | Flaccid | Eyes slightly divergent, roving slowly | Apnoea continues | Blood from the exit drips into a pool; brain oozes from the exit (2–30 mL over 10–120 s) | Lips not yet blue (cyanosis needs 60–120 s) |
| 40 s | — | — | **Breathing resumes**: irregular, 8–30 /min, bubbling into the blood under the face | Bubbling | Impact apnoea ends |
| 40–75 s | A withdrawal of the left leg when the player steps on it (GCS M4) | Roving | Moans to pain (V2) | — | GCS ~7 → 9 |
| 75 s | **Wakes**: pushes up on both hands (arms are not paralysed), rolls onto the side, sits slumped | **Blank, vacant stare**; slow blinks; no gaze deviation (FEF spared) | Groans | — | Stun decaying (half-life 30 s – 10 min) |
| 1.5–3 min | Right hand goes to the forehead; looks at the bloody hand (wound check 1–2 s, delayed × `rt_mult` 2); tries to stand, sinks back, **tries again the same way** (perseveration p ~0.5) | Blood from the forehead runs into the left eye within 5–30 s of sitting up → blinking and wiping; mild pain face (PSPI ~5) | **Non-fluent aphasia**: "uh… m-m… no… no"; **swearing fluent and intact**; screaming possible but absent (low arousal after the collapse) | Sniffing; spitting | `vocal_state` NONFLUENT (sev ≈ 0.8 residual); obeys simple commands p 0.7 |
| 4 min | Retches 3 times, vomits 150 mL forward | Nausea face (9B 10B 15B) | Retches ×3, then a gasp and a cough | — | Vomit p 0.2–0.4 after head injury |
| 5–15 min | Stands with a hand on a wall; wide-based steps (+50–100 %), sway × 2–3; walks toward the exit, stops, turns back (perseveration); laughs once at nothing (disinhibition 0.3) | Response latency 3–6 s; follows the player with the eyes | 1–3-word utterances; repeats "no" | — | Stable GCS 13–14 |
| 10–30 min | Sits; holds cloth to the forehead | **Faint left periorbital purple (raccoon eye) appearing from ~10 min**; blood trickles from the left nostril | Headache moans | — | Anterior skull-base fracture (p 0.82); raccoon eyes clear at 1–6 h, beyond the scenario |
| 30–60 min | Unchanged; fatigue | Blinks 10–15 /min | Non-fluent speech persists | — | Track haematoma 10 mL + 0.3 mL/min = 28 mL at 60 min: below the 60 mL reserve, no herniation |

- **Game time**: 0–60 s at 1×; then 4× until the scenario is ended. About 8–10 min of play for the hour.
- **Variants**:
  - (A) No collapse (p 0.1–0.3): startle, stagger 1–2 steps, both hands to the forehead, wound check, a psychological stop (sits down), aphasia apparent at once.
  - (B) Seizure (p 0.05–0.10 in the first hour): the head and eyes wrench to the **right** (away from the left frontal focus) → GTC (§5.4) → Todd's paresis.
  - (C) Larger track bleed (1 mL/min): drowsy from ~45 min, right arm drift, left pupil changes, herniation (§1.7.3).
  - (D) The track crosses the precentral gyrus: right lower-face droop, right hand drop, right leg buckle, and the fall goes toward the right side.

### 8.3 Temporal shot with a blown pupil later (talk and die)

**Setup.**
- .22 LR from 4 m into the right temple of an unarmed man, alert, low arousal.
- The bullet is **retained** in the right temporal lobe (non-dominant): `temporal_lat_R` destroyed 0.35, contusion.
- Track haematoma 15 mL growing at 1.0 mL/min.
- Herniation triggers use effective volume × 1.3 (temporal mass).

**Rolls.**
- Concussive collapse: yes, 20 s.
- Seizure: no (p 0.075–0.15).
- Kernohan: no.
- Neurogenic pulmonary oedema: no.
- Gasps at the end: no (the medulla fails first).

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0–60 ms | Startle begins | Blink | — | — | Entrance 4–5.6 mm over bone; no exit |
| 0.1–1.0 s | Concussive collapse, crumpling forward-right, no hands | — | — | — | §3.4 row 2 |
| 1–20 s | Flaccid on its side, obstructed breathing | Open, then roving; pupils equal 3.5 mm | Partial obstruction (lateral p 0.1–0.2 → light) | — | GCS 7 → 12 |
| 20 s | Wakes, confused; the left hand goes to the right temple | Dazed stare; slow saccades | "What… what happened?" | — | GCS 13 |
| 1–5 min | Sits up; asks the same question every ~60 s; holds the head | Normal pupils; **does not notice objects in the upper left** (left upper quadrantanopia, Meyer's loop) | Talks; complains of headache | Sniffing | Amnesia for the event |
| ~6 min | Vomits once | Nausea face | Retching | — | Vomit roll |
| 5–25 min | **Lucid**: stands, walks with a hand on the wall, argues, refuses help | Normal | Normal speech, irritable | — | Mass 20 → 40 mL (effective 52); MLS 4 mm |
| 25–35 min | Lies down; yawns; second vomit; left arm drifts down and palm-down within 3–10 s when raised; left foot drags | Heavy lids (5–7 mm); slow blinks | Slurred, sleepy (GCS 13 → 11) | Sighing | Drowsy per Ropper (3–4 mm MLS) |
| ~35 min (U1) | Stuporous; opens the eyes only to pain | **Right pupil**: a brief constriction (missed), then **4.5 vs 3.5 mm, sluggish, slightly oval** | Moans; breathing waxing and waning (Cheyne–Stokes) | — | Uncal stage U1 |
| ~45 min (U2) | Coma (GCS 6–7); **left hemiparesis**; decorticate spasms when touched (5–60 s), then decerebrate | **Right pupil 7–8 mm fixed**; right lid drooping; right eye down and out | Obstructed breathing or froth bubbling on the back; a moan with each spasm | — | **Cushing**: SBP 190–220, HR 50–60, irregular breathing; flushed face |
| ~55 min (M) | Decerebrate spasms on any stimulus; jaw clenched | Both pupils mid-to-wide and fixed (right 7, left 5 mm); doll's eyes weak and dysconjugate | Central hyperventilation 30–40 /min | — | Stage M |
| ~65 min (P) | **Flaccid**; spasms stop | Doll's eyes absent; left pupil widening | Ataxic: irregular rate and depth with pauses | — | Posturing stopping is a bad sign |
| ~72 min (X) | — | Both 6–8 mm fixed | Slow irregular gasps → **apnoea** | — | Tonsillar compression |
| 72–78 min | Heart beating; brainstem dead | Fixed, slightly divergent; eyes move with the head | None | — | Lips blue from ~73–74 min; HR < 40–50 by ~76 min |
| **~78 min** | — | — | — | — | `t_arr` (6 min after apnoea); dead flag ~83 min |

- **Game time**: ACUTE for the first minute, MINUTES/LONG bands (4–15×) for the lucid interval and the decline, 1× around `t_arr`. About 8–12 min of play.
- **What the player learns**: the eyes and the breathing announce the herniation long before the body stops moving.
- **Variants**:
  - Seizure (p 0.075–0.15): versive to the left, then GTC; it raises ICP by +10–20 mmHg and speeds up the decline.
  - Kernohan (p 0.1–0.2): the hemiparesis is on the right (same side as the mass).
  - False-side pupil (p 0.10–0.15): the left pupil dilates first.
  - A left temple (dominant side) adds jargon or non-fluent aphasia and right hemiparesis.

### 8.4 Heart shot

**Setup.**
- 9 mm FMJ from 7 m into a **committed attacker** walking toward the shooter at 1.4 m/s with a knife raised.
- The bullet crosses the left lung, the right and left ventricles and the septum, and exits the back. The heart is effectively destroyed: `t_arr` ≈ 0.

**Rolls.**
- Arousal 0.8.
- Psychological stop: no (p 0.35–0.45).
- Aware at 1.5 s.
- LOC at 11 s (upright × 0.85).
- Anoxic myoclonus: yes, 5 jerks (p 0.8).
- Tonic spasm: yes (p 0.15–0.3).
- Gasps: yes (p 0.45).
- Lung froth: yes (p 0.3–0.5).
- False last breath: yes (p 0.3).

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0 ms | **No knock-back** (0.038 m/s); the shirt ripples | — | — | — | BP falls over 2–4 beats |
| 40–250 ms | A small hunch (startle × 0.6 for arousal) | Blink | — (startle grunt not rolled) | — | §3.3 `FLINCH` |
| 0.3–1.5 s | Keeps walking and raises the knife | Wide, fixed on the shooter; pupils +1 mm | Shouts | — | Unaware for 1.5 s |
| 1.5 s | Glances down at the chest for 0.5 s, then back up | Brief look | — | — | Committed: no wound check |
| 1.5–5 s | **Full function**: closes to ~3 m, still advancing | Fixed on the target | Shouting | — | Brain O₂ reserve 8 s + ~4 s residual pressure (§3.8) |
| 5–10 s | Stride shortens and weaves; knife arm sags; left hand reaches for a table edge | **Vacant, unfocused**; pupils dilating; face pales | Speech slurs; gasping breaths | — | Grey-out |
| **11.0 s** | **LOC**: hypoperfusion sag with a final "crash" (0.2–0.5 s) | Lids stay open | — | — | §4.5 G |
| 11.2–12.5 s | Knees buckle; slumps forward and sideways; the right hand opens (knife drops at ~11.3 s); **no protective arms**; head strikes the floor at 2–4 m/s at ~12.4 s | **Eyes roll up 20°** (starts 11.5 s, held ~6 s) | Chest huff | — | — |
| 12–22 s | **5 irregular myoclonic jerks** (right arm, face, left leg, both shoulders, right hand) spread over 10 s; head turns; lip smacking | Lid flutter with jerks; eyes drift back to near straight ahead by ~20–40 s | Obstructed breaths for a few seconds | — | Not a seizure: few, irregular, pale |
| 26–36 s | **Anoxic tonic spasm**: arms straighten and turn in, back arches, jaw clenches, 10 s; then limp | Mid-position | Breathing stops | — | EEG flat by 15–30 s |
| **30 s** | First **agonal gasp**: head jerks back 20°, jaw gapes 30 mm, shoulders lift, a small right-arm jerk | Eyes move with the head | Gasp with **pink froth** bubbling at the lips | — | Gasp schedule (§5.2): 30, 40, 53, 70, 92, 120, 158, 206 s |
| 30–45 s | Limp between gasps | **Pupils begin to dilate** | — | — | — |
| 60–120 s | — | Pupils **6–8 mm fixed**; lids settle half-open (4 mm) | Gasps weaker, 17–38 s apart | — | Face grey; lips dusky (the blood is in the chest, not outside) |
| 3.4 min | Last scheduled gasp | — | Weak gasp, passive sigh | — | — |
| **4.8 min** | **False last breath** after a 90 s pause | — | One more small gasp | — | p 0.3 |
| 5 min | — | Gloss fading | — | — | Dead flag |
| 5–15 min | 3 faint twitches (fingers, eyelid) | — | — | — | Post-mortem twitches |

- **Game time**: 1× for the first 60 s and around `t_arr` (here the whole first 2 min); then 4× to the dead flag. About 2 min of play.
- **External blood**: little. The 5–18 mm back exit soaks the clothes and pools under the back; there are no arterial jets outside.
- **Variants**:
  - Non-combatant (psychological stop p 0.7–0.9): at 0.4–0.8 s the hand goes to the chest, then kneels and sits (C), still conscious until the same ~11 s.
  - Supine at the time of the hit: LOC × 1.2.
  - Stab wound with tamponade: activity for minutes, distended neck veins, grey sweating breathlessness (RB §4.4).

### 8.5 Carotid cut

**Setup.**
- Knife slash across the **left** side of the neck of a standing, unarmed man.
- Transects the left common carotid and the internal jugular vein; the airway is intact.
- Uncompressed arterial flow 1.0 L/min; own-hand compression × 0.4–0.7.
- **Timing caveat (C-17)**: the clock below follows R2-04 §10.3 (1.0 L/min). RB §3.4 scenario D (supine, uncompressed, open neck) gives LOC at 20–60 s and arrest at 2–5 min. RB owns the bleeding solver: if its output is faster, keep the order of events below and compress the clock to match.

**Rolls.**
- Poor collaterals → left-hemisphere ischaemia: yes (p 0.2–0.3), onset 12 s.
- Scream: no, a shout instead (p 0.3–0.5).
- Myoclonus at LOC: yes (p 0.5, slow onset).
- Gasps: yes, 5 (p 0.4).

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0–50 ms | Blade contact | — | — | — | — |
| ~100 ms | Flinch away from the blade: head turns right, shoulders up | Blink | Sharp inhalation | — | Withdrawal / startle |
| 0.2–1 s | — | — | — | — | Wound gapes 10–30 mm in < 1 s; a **scarlet pulsing jet** of 0.5–1.5 m, one burst per beat (HR 110 → 130); dark welling from the jugular beneath |
| 0.3–0.8 s | **Both hands clamp the neck**; blood wells between the fingers | Eyes wide (11–12 mm), fear face | — | **Spurts land** on the wall and floor | Flow × 0.5 |
| 1–10 s | Backs away, turns toward the door | Scanning | Panting; a shouted "help!" | Spurts keep landing | Airway intact |
| **12 s** | **Right arm weakens**: the right hand slips from the neck and the arm sinks and pronates; right leg weakens | **Eyes and head turn 20° left** (toward the ischaemic hemisphere); **right lower face droops** 3–5 mm | Speech breaks down: "uh… uh… help… no" (non-fluent) | — | Left MCA territory ischaemia (§1.3); onset 5–30 s |
| 15 s | The right knee buckles under load; falls **toward the right** (D); the left arm catches, then returns to the neck | — | Grunt | — | Compression now × 0.7 (left hand only) |
| 15–60 s | Lying on the right side; left hand pressing; tries to push up with the left arm | Fear face lopsided (right side weak); pupils 5–6 mm | Fast breathing 25–30 /min; moans; single words | Spurt landings weaken | — |
| 30–90 s (10–20 % loss) | Restless | **Pale; sweat beads on the forehead and upper lip** | Sighs | Jet shorter, faster | Class I–II |
| 90–150 s (20–30 %) | Pushing attempts stop | Heavy lids; slow blinks | Moans | — | Confusion |
| **~3 min** (40–50 %) | **LOC**: the left hand falls away from the neck → the flow rises again | Eyes up briefly, then half-open | No vocal effort (lying on the side); blood drains from the neck | Jet becomes a **welling pulse** | Myoclonus: 3 jerks over 8 s |
| 3–5 min | Limp | Pupils dilating | Irregular shallow breaths | — | Waxy grey-white; **lips grey-lilac, not blue** |
| **~5 min** | — | — | — | Welling stops pulsing | **`t_arr`** (PEA) |
| 5–8 min | Small gasp jerks | Pupils wide and fixed by 1–2 min after arrest | **5 agonal gasps** | — | — |
| 10 min | — | — | — | — | Dead flag; very faint, late livor (exsanguinated) |

- **Game time**: the first 60 s at 1×; then 4×; 1× from 4 to 6 min. About 3 min of play.
- **Scene**: arterial arcs and zigzag clusters on the wall (one per beat, lower and smaller over time); flows down the chest; a large pool; hand smears on the floor.
- **Variants**:
  - Airway cut below the cords: **mouths words without airflow**; bubbling at the neck; coughs spray blood from the wound; aspiration (the cause of death in 36.5 % of a fatal series).
  - Good collaterals (p 0.7–0.8): no hemispheric signs; the clamp holds with both hands until LOC at 2.5–4 min.
  - Upright victim: faints at 20–30 % loss (60–120 s) with convulsive jerks.
  - Both carotids and jugulars cut: LOC 5–20 s, arrest 1–3 min.

### 8.6 Femur shot

**Setup.**
- 9 mm FMJ from 10 m through the **right mid-thigh** of a committed attacker walking toward the shooter, holding a pistol, with the right leg in stance.
- Femoral shaft fracture (comminuted with a butterfly fragment); femoral artery intact.

**Rolls.**
- Aware at once (a bone hit: unaware ≤ 0.05).
- Hop: no.
- Vocalisation on the fracture: a cry (pain 8).
- Psychological stop at 8 s: yes (committed 0.4 × 1.3 for the limb).
- Keeps the pistol for 3 s.

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0 ms | The thigh flicks slightly | — | — | — | Femur shatters; 3–10 fragments; exit 2–5 cm with bone chips |
| 30–250 ms | Startle | Blink | — | — | — |
| **100–300 ms** | **The right leg folds at mid-thigh** (10–30° angulation); pelvis drops 10° on the right; the trunk rotates right | Pain face begins (~300 ms) | — | — | §3.4 row 21, §4.5 D |
| 200 ms | **Arms thrown out** (burst ~100 ms after balance loss) | — | — | — | CatchFall pre-armed |
| 240 ms | Short rescue step with the left leg | — | — | — | Fails |
| **0.6–0.9 s** | Lands on the right hip and the heels of both hands; the pistol still in the right hand | Eyes squeezed | Air forced out | — | Hands first |
| 0.5–1.5 s | — | PSPI 13–16 at the apex | **Cry**, 1.2 s; gasping inhalation | — | Pain spike (aware at once) |
| 1–3 s | Rolls onto the back; the right thigh bends visibly mid-shaft; **the foot lies turned out 60–90°** | — | Breath drawn through clenched teeth | — | Shortening 2–5 cm |
| 3 s | Drops the pistol; **both hands clamp the thigh** above the fracture | Pupils +1 mm | Groans with each movement | — | Weapon drop |
| 8 s | **Psychological stop**: raises one hand toward the shooter | Pleading face (oblique brows) | "Don't— don't shoot, I'm done" in breath groups of 3–8 syllables | — | Surrender |
| 10–60 s | Any movement → pain spike (vocal mix: none 0.35, groan 0.35, cry 0.2, scream 0.1) | Tears | Panting 25 /min | — | — |
| 1–10 min | Tries to drag itself backward with the arms; the broken leg drags, rotating outward and bending at the fracture | Pale lips | Breathless speech | — | Closed blood loss 1–1.5 L into the thigh over tens of minutes; the thigh swells 2–3 cm per litre; fat beads glisten in the exit wound |
| 5–20 min | Fear tremor in the hands and jaw; hunched | Sweat on the forehead | "I'm cold" | Teeth chatter from ~15 min (shiver p 0.3–0.5) | Class II (15–30 %) |

- **Game time**: the first 60 s at 1×; then 4×. Survives the scenario window.
- **Variants**:
  - Femoral artery also transected (p from the track): a pulsing jet from the entrance and exit wounds, a fast-growing pool; LOC 2–5 min, arrest 3–10 min (RB §4.7); `HOLD_NECK`-like clamping of the groin with both hands.
  - Hop (p 0.3–0.5): 1–3 hops on the left leg before the fall.
  - Rifle (7.62×39): 3–10 cm of the shaft pulverised, near-amputation look, exit 5–15 cm with protruding bone.
  - Unloaded leg at the time of the hit: stays up until the next right stance (0.2–0.5 s), then the same fall.

### 8.7 Punches to knockout

**Setup.**
- An unarmed man, aware of the fight, guard up (braced) at the start.
- The attacker is a trained puncher (straights 2,800 N; hooks 3,500 N).

**Rolls.** Every P(LOC) is computed with §3.7.

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0.00 s | **Punch 1**: straight right to the nose (α ≈ 5,200 × 0.5 = 2,600; braced midpoint 7,750 → P(LOC) ≈ 0.01) | — | — | — | Nasal fracture (threshold 111–334 N) |
| 0.05–0.10 s | Head snaps back 20–30° | Blink, eyes squeeze | Forced exhalation | — | Head excursion peaks at 50–100 ms |
| 0.3–0.6 s | Left hand to the nose | **Eyes glisten within 1–5 s**; pain face (PSPI ~8) | Grunt; breath drawn through the teeth | — | Reflex tearing |
| 0.5–2 s | Steps back 1 step; guard re-forms | Tears run by ~10–30 s | Sniff | Blood drips from the nose | — |
| **2.00 s** | **Punch 2**: left hook to the right jaw (α ≈ 6,500; midpoint 7,750 × 0.95 = 7,360 → **P(LOC) 0.33 → no**) | — | — | — | — |
| 2.05–2.10 s | Head whips 40–60° to the left | — | — | — | — |
| 2.1–4 s | **Rocked**: knees dip 20° and recover; 3 wide lurching steps; the hands grab the attacker (clinch) | **Blank stare**; horizontal nystagmus (2 Hz, 4°) | Grunts | — | `rt_mult` 1.5; guard dropped; flinch p 0.3–0.6 |
| **4.20 s** | **Punch 3**: right hook to the left jaw while rocked (α 6,500; unbraced 6,000 × 0.95² × 0.8 = 4,330 → **P(LOC) 0.86 → yes**) | — | — | — | — |
| 4.25–4.30 s | Head rotates to the right; **tone lost** (≤ 100 ms) **before the head comes back** | Eyes glaze | — | — | — |
| 4.3 s | **Fencing**: the right arm (face side) shoots up and forward, stiff (shoulder flexion ~100°, elbow ~10°); the left arm flexes | Open (p 0.8); **tonic upgaze** 5 s | — | — | p 0.66; ω 12–16 |
| 4.3–5.2 s | Crumples with a quarter-turn to the right, following the head; **no protective hands**; lands on the right side and back | — | Huff (air forced out) | **Head strikes the floor at 3–5 m/s** | Fencing crumple (0.5 of the mix) |
| 5.2–6.0 s | **Two more punches land on the downed head**: purely passive bounces; no guard, no flinch | — | — | — | Post-knockout strikes |
| 4.3–9.5 s | The raised right arm stays up ~5 s, then drops over 0.8 s | Eyes back to near neutral, slightly divergent; pupils equal and reactive | — | — | — |
| 6–40 s | Limp on the back | Doll's eyes present | **Obstructed breathing**, then **froth bubbling** at the mouth as nose blood runs back into the throat | — | LOC; concussive convulsion not rolled (p 0.014) |
| **~40 s** | Wakes | **Eyes open first**; blank stare for 20 s | Groans | — | — |
| ~60 s | Tries to rise; **falls back** | Unfocused | — | — | Fall-back p 0.3–0.6 |
| ~90 s | Sits up; **hand to the head** | Slow saccades (0.5 /s) | "What happened? … What happened?" (repeats every 30–120 s) | Spitting blood | Amnesic for the event |
| 2–10 min | Stands unsteadily with feet wide; sways; sits again | Nose blocked; periorbital swelling beginning | Mouth breathing; sniffing | — | Confusion 5–30 min |

- **Game time**: 1× throughout the fight and the first minute after the knockout; then 4×.
- **Variants**:
  - Punch 3 lands with locked knees: **plank topple** (1.0–1.6 s), occipital impact 5–7 m/s; risk of a skull fracture and EDH → the §8.3 pattern.
  - Concussive convulsion (p 0.014): tonic stiffening within 2 s, lasting ≤ 20 s, then jerks up to 150 s; recovers.
  - Heavy blows while unconscious and supine: aspiration of nose blood → froth bubbling at the mouth, blue lips.

### 8.8 Hammer depressed fracture with a seizure

**Setup.**
- Claw hammer (0.6 kg head) striking the **left parietal** region of a standing, unarmed man, 3–4 cm left of the midline and ~2 cm behind the vertex, over the left hand and arm motor area.
- The victim is left-dominant (speech in the left hemisphere).

**Rolls.**
- Blow 1: no fracture; no LOC (0.1–0.3).
- Blow 2: depressed fracture and dural tear (0.3–0.6); no LOC (0.3–0.6).
- Seizure: yes (p 0.06–0.12: blunt with fragments through the dura × 2, motor cortex × 1.5), onset at 3:10, focal → bilateral.
- Figure-of-4: yes.
- Tongue bite: yes.
- Urine: yes.

| t (real) | Body / motor | Eyes and face | Breathing and mouth | Other visible events | Physiology / notes |
|---|---|---|---|---|---|
| 0.00 s | **Blow 1** (60 J) | — | — | — | Crescent scalp laceration 25 mm; bump; **no spatter** (no exposed blood yet) |
| 0.04–0.3 s | Startle; head ducks; stumbles one step | Blink; eyes squeeze | "Ah!" | — | Coup stun under the site 0.3–0.6: right hand weak (transient) |
| 0.4–1.2 s | Left hand to the back of the head; turns toward the attacker; **forearms up** (the right arm lags, weak) | Terror face, eyes wide | **Shout: "Stop!"** | — | `SHIELD` p 0.5–0.8 |
| **1.80 s** | **Blow 2** (70 J), same site, past the raised left forearm | — | — | — | **Depressed fracture** 30 mm across, 8 mm deep; 4 inner-table fragments driven in; dural tear; `M1_hand_L` / `M1_arm_L` destroyed 0.35 + stun; `M1_leg_L` stun 0.3 |
| 1.85–2.3 s | **The right arm drops as dead weight** and swings; the right hand is limp | Dazed | Scream (0.9 s) | Impact spatter begins (blood now exposed); cast-off on the backswing | Right hand and arm sev ≈ 1 / 0.8 |
| 2.3–2.8 s | The right knee buckles under load; **falls toward the right** (D); the left arm catches; lands on the right shoulder | — | Grunt | — | Leg sev ~0.4 (MRC 3) |
| 3–60 s | On the ground, conscious (GCS 13–14); tries to push up with the left arm only; the right arm lies where it fell | Mild right lower-face droop; blood from the scalp runs over the forehead into the eyes → blinking and wiping with the left hand | Screams in breath-paced bursts, then moans; speech slightly slurred (dysarthric), words intact | Drips fall | Pain spikes on each movement |
| 1–3 min | Sits against the wall; holds the head with the left hand | Pale; sweat | "My arm… I can't feel my arm" | — | Seizure clock running |
| **3:10** | **Focal seizure**: the paralysed **right fingers and wrist start jerking at ~2 Hz** (10–40° per jerk) | Stares at the hand; fear face | "No, no, no" (conscious) | — | Irritative cortex beside the destroyed tissue (§1.8) |
| 3:25 | **Jacksonian march**: the jerking spreads to the forearm and then the whole arm (~15 s per segment) | — | Panting | — | — |
| 3:40 | The **right face** joins: mouth corner pulled 3–8 mm, right eyelid twitching | Right hemiface clonic | Speech stops | — | — |
| 3:50 | **Head and eyes wrench to the right** (forced version 30–45°, away from the left focus) over 2 s | Eyes forced right | — | — | LOC |
| 3:52 | **Generalisation**: epileptic cry (1.5 s); tonic flexion 3 s (arms rise) | **Eyes open wide**, pupils 7 mm, unreactive | **Epileptic cry** | — | — |
| 3:55–4:07 | **Tonic extension** with a **figure-of-4**: right elbow straight (contra to the focus), left arm flexed across the chest; back arched; legs extended; feet pointed; slides from the wall onto the floor | Face congested, **turning blue from ~4:05** | **Apnoea**; strained grunt | — | Urine released; ICP +10–20 mmHg |
| 4:07–4:10 | Fine 10 Hz quiver of the rigid body | — | — | — | Vibratory transition |
| 4:10–4:55 | **Clonic**: bilateral synchronous flexor jerks at 3.5 Hz, **slowing to ~0.8 Hz** (~60 jerks); the gaps lengthen | Eyelids jerk with each beat; eyes nystagmoid | Grunt with each jerk; **jaw snaps**; **pink froth** (lateral tongue bite) | Limbs strike the floor | Cyanosis peaks, then eases |
| 4:55 | Last jerks 2 s apart; **completely limp** | Lids half-close | A deep sighing breath | — | — |
| 4:55–5:25 | Limp where it lies | Half-closed; pupils large and sluggish | 10 s pause, then **heavy obstructed breathing** 25 /min, bubbling froth | — | Colour returns from blue to pale over 1–5 min |
| 5–8 min | **Todd's paresis**: the right leg is now also flaccid (on top of the arm lesion); withdraws the left limbs and moans to pain | Pupils back to normal and reactive | Moans | — | GCS 8–9; Todd lasts 173 s here |
| 8–25 min | Stirs; rolls; pulls at clothes; combative when touched; the right leg recovers to MRC 3; **the right arm stays paralysed** (lesion) | Confused gaze | Confused, slurred words | — | Post-ictal confusion 10–60 min |
| 25–60 min | Sits; headache; nausea | Drowsy | Slurred but oriented by ~45 min | — | Watch for EDH (parietal fracture near the middle meningeal branches) |

- **Game time**: 1× for the attack and the first minute; 4× from 1–3 min; **1× again for the 60 s after the seizure starts** (a critical event); then 4×.
- **Variants**:
  - Status epilepticus (p 0.02–0.05): the convulsions continue or recur without recovery beyond 5 min.
  - EDH from a torn meningeal branch (1 mL/min): lucid for ~60 min, then the §8.3 decline with the **left** pupil blowing and a right hemiplegia.
  - More blows (4–8): comminuted mosaic, extruding brain, LOC, posturing (§6.2 row 4).
  - A blow over the left temple instead: aphasia (non-fluent or jargon) and a much higher EDH risk (thin temporal bone, fracture threshold ~10 J).

### Simulation parameters (scenario defaults)

| Parameter | Value | Unit | Notes | Tag |
|---|---|---|---|---|
| `scenario_brainstem_t_arr` | 6 (4–10) | min | Medulla variant | `[K] R1-04 §2.4` |
| `scenario_frontal_transient_loc` | 75 (5–120) | s | Impact apnoea 40 s | `[G]` on `[K]` |
| `scenario_temporal_mass` | 15 mL + 1.0 mL/min; herniation effective volume × 1.3 | — | Apnoea ~72 min, `t_arr` ~78 min | `[E]` |
| `scenario_heart_loc` | 11 (8–15 × 0.85 upright) | s | Gasps from 30 s | `[K]` `[E]` |
| `scenario_carotid_flow` | 1.0 uncompressed; × 0.5 two hands; × 0.7 one hand | L/min | LOC ~3 min; `t_arr` ~5 min; RB solver governs (C-17) | `[E] R2-04 §10.3` |
| `scenario_femur_giveway` | 0.1–0.3 | s | Contact 0.6–0.9 s | `[E]` |
| `scenario_ko_forces` | straight 2,800 N; hooks 3,500 N | N | §3.7 | `[S R2-02:S28,S29]` `[E]` |
| `scenario_hammer_energy` | 60 / 70 | J | Seizure onset 3:10 | `[E]` |

### Visual/behavioural checklist (scenarios)
- In every scenario the order is: impulse → blink and flinch (if the brainstem works) → mechanical failure → protective limbs (if conscious) → hand to the wound → looking → the emotional reaction → physiological collapse.
- Nothing is thrown by a bullet. Unconscious bodies never protect themselves. Heart-shot characters stay capable for several seconds.
- The brainstem victim never breathes again; the heart-shot victim gasps; the carotid victim goes white; the temporal victim talks for half an hour before one pupil blows; the knocked-out man wakes up asking the same question; the hammer victim's paralysed hand starts jerking before the whole body convulses.

---

## 9. Test checklist (reviewer acceptance tests)

This list complements RB §9, which covers wounds, blood, circulation, eyes after death and post-mortem changes (RB rows 1–50). Where a statement here overlaps an RB row, the RB row number is given. Each statement is observable in the game or its debug overlay, and each has a pass criterion.

### 9.1 How to run the tests

- **Test body**: the reference body (§0.3; 75 kg, 1.75 m), hero settings (physics 120 Hz). Q53 also runs at 60 Hz.
- **Debug overlay** (required fields):
  - sim time and band;
  - physiology (MAP, HR, SpO₂, brain O₂ reserve, ICP, blood-loss class, `t_LOC`, `t_arr`);
  - per-region neuro severity and the resolved channels;
  - tone and strength per joint group;
  - eye yaw and pitch per eye, pupil diameter, lid aperture;
  - active involuntary generators and their gate state (§5.1);
  - the RNG seed and every roll with its outcome.
- **Seeds**: batch tests use seeds 1…n. Scenario tests use the seeds stored with each §8 scenario plus seeds 1–10.
- **Pass rules**:
  - **Probabilities** (n runs): pass if the observed fraction lies inside [p_lo − 2σ, p_hi + 2σ], with σ = √(p̄(1 − p̄)/n) and p̄ the midpoint of the stated range.
  - **Timings and magnitudes**: at least 90 % of runs inside the stated range, and 100 % inside the range widened by 25 % of its width on each side.
  - **Absolute statements** ("never", "always", "0 events"): zero failures in n runs.
  - **Reflex latencies**: ±1 physics tick (8.3 ms at 120 Hz). **Eye angles**: ±2°. **Pupils**: ±0.2 mm. **Joint limits**: ±3°.
- A failed test produces the event log of the failing seed. The fix is made in the system named in the "Ref" column, not by special-casing the test.

### 9.2 Global rules

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q01 | The same seed replays identically; a different seed changes the rolls | Replay each §8 scenario twice with seed s and once with s + 1 | Logs for seed s identical (event type, tick, bone, value); at least one rolled event differs for s + 1 | §0.3 |
| Q02 | On the impact frame, only the physical impulse and the wound are visible | 50 hits, frame capture at 120 Hz | 0 non-L0 bone rotations > 0.5° on the contact frame; every L1 event starts 2–15 frames later | §0.3, §3.1 |
| Q03 | Cosmetic oscillators keep real-time speed under time compression | A breathing, shivering, gasping body run at 1×, 4× and 15× | Breath rate, blink rate, tremor and shiver frequency and gasp intervals, measured in real seconds, match across speeds within ±5 % | §0.3 |
| Q04 | Every involuntary sign respects its tissue gate | 500 random injuries; every generator event logged with its gate | 0 events with a failed gate; the six §5.1 debug assertions never fire | §5.1 |

### 9.3 Neuro model (§1)

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q05 | Body hits never switch the brain off ("hydrostatic shock" guard) | 200 handgun and rifle hits to soft tissue of the chest, abdomen and thigh (§3.4 rows 15, 17, 18, 22), with the heart, great vessels, cord and bone spared | Brain `stun` = 0 in 200/200; tone < 0.5 within 1 s in 0/200 | §1.3, §3.9 #5 |
| Q06 | A one-sided hemisphere wound weakens the opposite side and turns the eyes and head toward the wound | Track through the left FEF and left M1 (or internal capsule), severity ≥ 0.7, 20 seeds, standing | Right hand: drive scale ≤ 0.2 and torque cap ≤ 0.3 (§1.5), left side normal, in 20/20; eyes 15–40° and head 10–30° toward the left in ≥ 18/20; falls toward the right in ≥ 80 % of falls | §1.5, RB §9 #35 |
| Q07 | A seizure from the same focus turns the eyes and head away from the wound | Force a versive seizure in the Q06 bodies | Version 30–45° toward the right (away from the lesion) in ≥ 90 %; the destructive bias toward the left returns after the seizure | §1.8, §2.4 |
| Q08 | Brainstem lesions cross: face and eye on the wound side, arm and leg on the other | Right lateral pontine lesion, 20 seeds | 20/20: right peripheral facial palsy (brow 2–5 mm low, closure gap 2–10 mm), right eye turned in 6–22° (CN VI), left arm and leg weak | §1.2, §2.4, §2.6 |
| Q09 | Central and peripheral facial palsy differ at the forehead | Left M1 face-area lesion vs left pontine lesion, 10 seeds each | Cortical: right lower face weak, forehead gain ≥ 0.8. Pontine: whole left face weak, forehead gain ≤ 0.2 | §2.6 |
| Q10 | A cerebellar wound leaves the character strong but falling toward the wound and overshooting | Right cerebellar hemisphere, severity 0.7, 50 seeds, standing, then a reach task | Falls toward the right in 0.6–0.8 (±2σ); reach overshoot 3–10 cm with a 3–5 Hz tremor of 1–5 cm in the last 10–20 cm, right hand; strength ≥ 0.9 | §1.5, §5.5 |
| Q11 | A weak arm drifts | Both arms raised to 90°; contralateral arm severity 0.4–0.8 vs 0–0.2 | The weak arm drifts down and pronates within 3–10 s; the normal arm holds ≥ 20 s | §1.5 |
| Q12 | Aphasia follows language dominance | 100 characters with rolled dominance; left inferior frontal lesion, severity ≥ 0.6 | Non-fluent output only in left-dominant characters (0.90 of the batch, ±2σ); swearing intact; no aphasia in left-dominant characters after the mirror (right) lesion | §1.5, §0.3 |
| Q13 | Neglect occurs at the right rates and hides one side | 100 right and 100 left parietal (PPC) lesions, severity > 0.3 | Neglect 0.43 (right) and 0.20 (left), ±2σ. On the neglected side: no glance, no hand to a wound, no shielding | §1.5, §3.5 |
| Q14 | An expanding mass is silent while compensated, then declines in order | EDH at 1 mL/min from 15 mL, 20 seeds | No herniation sign while the volume is < 60 mL; midline shift 0.10 mm per mL ± 10 %; stages U1 → U2 → M → P → X in order in 20/20, never skipped or reversed | §1.7 |
| Q15 | The first blown pupil is on the side of the mass and the weakness on the other side, with rare exceptions | 100 temporal masses | First pupil ipsilateral in 0.85–0.90 (false side 0.10–0.15); ipsilateral hemiparesis (Kernohan) in 0.1–0.2 | §1.7 |
| Q16 | Posturing follows the herniation stage | Q14 runs | Decorticate → decerebrate → flaccid; no new posturing after medullary failure; posturing absent after stage X | §1.7, §5.7 |
| Q17 | The Cushing response appears at U2–M | Q14 runs plus 30 more | SBP rises and HR falls in every run; the full triad (SBP 160–240, HR 40–60, irregular breathing) in about ⅓ (0.2–0.47 at n = 50) | §1.7 |
| Q18 | Early seizures occur at first-hour rates | 1,000 penetrating hemisphere wounds, 1,000 blunt, 1,000 knockouts | 0.05–0.10 (× 1.5 with motor or temporal cortex), 0.02–0.04, and 0.014 (0.007–0.021) | §1.8, C-02 |

### 9.4 Eyes and face (§2)

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q19 | Saccades follow the main sequence | 200 saccades of 5–40° | Duration 21 + 2.2 × amplitude ms, ±10 %; peak velocity 400–700 °/s for amplitudes ≥ 10° | §2.2 |
| Q20 | Blinks match the state | 5 min per state | Alert: mean 12–20 /min, no interval < 1 s, full blink 250–400 ms. Shock: 5–10 /min, 300–500 ms. Coma and dead: 0 | §2.3, C-15, RB §9 #41 |
| Q21 | Pupils respond to light, pain and fear | Light test; pain spike; visible threat | Light: constriction starts 200–300 ms, consensual. Pain: +0.3–1.0 mm, onset 0.3–0.6 s, peak 1–2 s, back in 3–10 s. Fear: +0.5–1.5 mm while the threat lasts | §2.2, §2.3, C-03 |
| Q22 | Pupil size follows the lesion and the circulation | Pontine, midbrain and uncal lesions; circulatory arrest | Pons 1–1.5 mm; midbrain 4–6 mm fixed; uncal side 6–9 mm fixed. After arrest: dilation starts at 30–45 s and reaches 6–8 mm fixed by 60–120 s. A dead pupil is never < 4 mm unless the pons was destroyed | §2.3, RB §9 #43 |
| Q23 | Doll's eyes depend on the brainstem | Turn the head 30° in four states: alert, coma with an intact brainstem, brainstem failed, dead | Alert: the eyes stay on the target. Coma: counter-rotation gain 1.0 ± 0.1. Brainstem failed or dead: gain 0 ± 0.05 | §2.7, RB §9 #44 |
| Q24 | A lifted lid closes only in the living | Lift one lid 5 mm on a living coma body and on a dead body, 20 each | Living: closes over 1–2 s. Dead: stays up in 20/20 | §2.7 |
| Q25 | Upgaze belongs to the collapse, never to death | 50 circulatory LOCs (heart, syncope); 100 deaths of all causes | Upgaze 10–30° for 2–10 s in 0.6–0.9 (±2σ); neutral again within 10–60 s. In every `DEAD` state: pitch ≤ +5°, yaw 3–10° outward; `assert_no_upgaze_in_dead` never fires | §2.3, §3.9 #10, C-05 |
| Q26 | CN III palsy looks down and out with a blown pupil | Uncal stage U2 or midbrain lesion, 20 seeds | On the lesion side: ptosis 100 %, eye out 22–33° and down 5–10°, pupil 6–9 mm fixed | §2.4 |
| Q27 | Lids at death follow the distribution | 100 sudden and 100 slow deaths | Sudden: open 0.55 / half 0.35 / closed 0.10. Slow: 0.20 / 0.45 / 0.35 (±2σ). Lids drop 2–4 mm over 1–3 s; no blink after death | §2.3, RB §9 #42 |
| Q28 | A knocked-out character's eyes are open and glassy | 50 knockouts | Open or half-open in 0.8 (±2σ; C-04); tonic upgaze in about half of the open eyes for 2–10 s; pupils equal and reactive; doll's eyes present | §2.3 |
| Q29 | The pain face scales with pain | Pain swept 0–10 on 10 characters | PSPI ≈ 1.6 × pain ± 2; AU43 binary; eyes shut in pain screams, wide in terror screams | §2.3, §2.6 |
| Q30 | An unconscious palsied face shows the palsy through tone | Palsied comatose body, supine, pain stimulus | Only the working side grimaces; the paralysed cheek puffs out 3–10 mm on each expiration | §2.6 |
| Q31 | Colour follows the cause | A bleed-out death; apnoea with normal Hb | Exsanguinated: white-grey face, grey-lilac lips, never blue. Apnoea: lips and tongue blue within 60–120 s. Face colour lags physiology by 5–15 s (× 2 in shock) | §2.6, RB §9 #29 |

### 9.5 Reaction system (§3)

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q32 | Bullets never throw bodies | 500 projectile hits, all weapons, standing and supine | Pelvis Δv ≤ 0.2 m/s in 500/500 (9 mm ≤ 0.05; 00 buckshot ≤ 0.17); `assert_projectile_body_dv` never fires; fall direction not correlated with shot direction (abs(r) < 0.2) | §3.9 #1, T10, RB §9 #12 |
| Q33 | The involuntary "shot" snap is a startle flexion, whatever the shot direction | 50 shots from the front, 50 from behind | A hunch (head down, shoulders up) in ≥ 95 % of both sets; frontal shots produce no backward trunk rotation > 2° beyond L0 in the first 200 ms | §3.9 #2 |
| Q34 | Startle timing | 50 unexpected shots near a conscious character | Visible blink 40–60 ms, head 90–130, arms 120–160, legs 140–220 ms; no startle with a destroyed brainstem | §3.3 |
| Q35 | The startle habituates but the blink persists | 5 shots within 10 s, 20 seeds | Amplitudes 1.0 / 0.6 / 0.45 / 0.35 / 0.25 (±0.05); blink amplitude never below 0.5 | §3.3 |
| Q36 | Not everyone stops when shot | 200 committed attackers; first 9 mm hit to the torso, CNS, heart and bone spared | Stop within 3 s in 0.35–0.45; never stop in 0.13–0.17 (±2σ); over a multi-hit batch, mean hits to stop 1.4–2.5 | §3.6, §3.9 #3 |
| Q37 | A destroyed heart leaves seconds of capability | 50 committed attackers | Purposeful action continues ≥ 5 s in 50/50; LOC at 8–15 s (× 0.85 upright); hypoperfusion sag (G); no LOC before 5 s | §3.8, §3.9 #4, RB §9 #33 |
| Q38 | Pain vocalisation is gated; not everyone screams | 200 gunshot and stab pain spikes | Vocalisation rate = clamp(0.15 × (pain − 2), 0, 0.95) × expressivity, ±2σ; 0 while unaware, winded, apnoeic or unconscious; the first cry comes at discovery, not at impact | §3.6, §3.9 #6 |
| Q39 | Many wounds are not noticed at once | 200 high-arousal torso hits, 100 back stabs, 100 bone hits | Unaware for > 3 s: 0.3–0.5 / 0.4–0.6 / ≤ 0.05. Discovery median ~5 s (back stab ~10 s); P90 ≤ 60 s | §3.6, §3.9 #14 |
| Q40 | A broken femur folds before any emotion | 20 loaded femur hits | The thigh gives way at 0.1–0.3 s; falls toward the injured side in ≥ 17/20; hands first; foot turned out 45–90°; shortening 2–5 cm; wound check and pain face start only after the collapse has begun | §3.4 #21, T15 |
| Q41 | Knockout probability follows the α model | 200 blows at each of α 3,500 / 6,000 / 9,300 rad/s², unbraced | P(LOC) 0.11 / 0.50 / 0.94 (±2σ); braced midpoint 7,500–8,000 | §3.7 |
| Q42 | A knockout drops at once and never protects itself | 50 knockouts | Tone < 0.1 within 100 ms of contact, before the head returns from its peak excursion; no protective hand in 50/50; tonic arm (fencing crumple plus plank) in 0.66 ± 0.13; the raised arm stays 2–10 s (≤ 20), then falls over 0.5–1 s | §3.7, §3.9 #7, #9, RB §9 #19 |
| Q43 | Hits on the unconscious produce only reflexes | 50 hits at each of GCS M5–M4, M3–M2 and M1 | Withdrawal of the struck limb in 0.2–0.5 at M ≥ 4; posturing burst in 0.5 at M2–M3 (latency 0.2–1 s); nothing at M1; never a guard, a flinch or a blink | §3.4 #37 |
| Q44 | Hits on the dead produce only mechanics | 100 hits on bodies 0–2 h after arrest | Active torque 0 in 100/100; a local muscle bulge of 5–20 mm in 0.1–0.3 of direct muscle hits, with no joint motion > 5° from it | §3.4 #38, §3.9 #12 |
| Q45 | A paralysed side cannot protect | A hemiplegic character pushed toward each side, 20 pushes per side | No protective arm and no hand-to-wound on the paralysed side; falls after pushes toward the paralysed side are about 3 times as frequent | §3.5 |
| Q46 | A faint is short and recovers | 50 vasovagal faints | Graded tone loss over 0.5–2 s; 1–10 irregular jerks over 5–15 s; eyes open and up; LOC 12.1 ± 4.4 s; wakes once horizontal | §3.6, T16, §3.9 #13 |

### 9.6 Falls and ragdoll (§4)

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q47 | An off-switch collapse drops straight down, head last | T2, 20 runs | First contact 0.35–0.55 s; head last, at 0.7–1.2 s and 3–5 m/s; the arms float up and slap down 50–150 ms after the trunk; no hand reaches out | §4.5 A, T2, RB §9 #32 |
| Q48 | A rigid knockout topples like a plank | T3, 20 runs | Ground at 1.2–1.3 s from 5° of lean; head 6–7 m/s; feet planted until ~50°, then slide or lift | §4.5 B, T3 |
| Q49 | A conscious fall is caught by the hands | T14, 50 runs | Arm burst ~100 ms after balance loss, oriented < 200 ms; hands first in ≥ 0.74 (±2σ); elbows yield 20–60°; face turned away | §4.6, T14, §3.9 #8 |
| Q50 | Bodies neither slide nor bounce | 100 standing collapses; T8 | Slide 0.03–0.4 m, never > 1 m; T8 slide 2.3–2.8 m; rebound ≤ 2 cm (trunk), ≤ 5 cm (head), ≤ 3 cm (limbs) | §4.6 |
| Q51 | Bodies settle and stay still | 100 falls, some on a 3° slope | KE < 0.5 J by 2–5 s and asleep by 5 s; no rolling; no bone moving > 1 cm/s after sleep; damping not raised before KE < 2 J for 0.5 s | §4.7, T7 |
| Q52 | Limp limbs are heavy, not floaty | T4, T5, T6, T12 | T4 passes the vertical at 0.36–0.40 s, 2–4 swings, still by 4 s; T5 period 1.0–1.3 s; T6 chin to chest in 0.3–0.6 s; T12 the hand hits the face | §4.9 |
| Q53 | The ragdoll is stable and physically honest | 1,000 random falls at 60 Hz and at 120 Hz | 0 NaN; no bone > 20 m/s without an external impulse; joint limits held within ±3° (T13); in free flight with drives on, total angular momentum constant within 1 % over 2 s (reaction torque applied) | §4.3, §4.4, C-12 |
| Q54 | Rigor holds, then breaks | T17 | No motion below 15–40 Nm; then the joint gives way and stays loose | §4.9 |

### 9.7 Involuntary movement (§5)

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q55 | A destroyed medulla means no breathing movement of any kind | 50 medullary hits | 0 breaths, gasps, coughs and hiccups; lips blue by 60–120 s; `assert_no_gasp_if_medulla_dead` never fires | §5.1, RB §9 #32 |
| Q56 | Agonal gasps follow their schedule | 100 destroyed-heart deaths with an intact medulla | Gasps in 0.45 (±2σ); first at ~30 s; intervals 10 × 1.3ⁿ s; ≤ 8 gasps plus a false last breath (0.3); mean rate over the gasping period 2–10 /min; last gasp within 1–5 min; the eyes move with the head | §5.2, RB §9 #40 |
| Q57 | A generalised seizure has the right phases | 50 GTC seizures | Total 30–120 s (mean 62 ± 10); tonic 10–20 s with apnoea; clonic 30–60 s, falling from 3–4 Hz to 0.5–1 Hz and stopping when the gap exceeds 2–3 s; eyes open ≥ 0.9; cry 0.3–0.5; lateral tongue bite 0.2–0.35 | §5.4 |
| Q58 | A faint is distinguishable from a seizure | 50 syncopes vs 50 GTC seizures | Syncope: 1–10 irregular jerks within 15 s, pale face. GTC: rhythmic clonus that slows, cyanosis, heavy obstructed breathing afterwards | §5.3, §5.4 |
| Q59 | Post-mortem movement fades and stops | 100 bodies from `t_arr` to `t_arr` + 30 min | Twitches in 0.2–0.4 of bodies at 0.5–5 /min, decaying; 0 spontaneous movement after `t_arr` + 20 min | §5.5, C-06 |
| Q60 | Spinal reflexes and the Lazarus sign occur only in their window | 100 brainstem deaths with a beating heart | Any spinal movement in 0.2–0.4 (C-09); Lazarus in 0.03–0.05, a 2–5 s rise, never an impulse; no spinal movement outside brainstem death → `t_arr` + 60–180 s | §5.5 |
| Q61 | A dead body never shivers, trembles, breathes, postures, blinks, tracks or flinches | 100 bodies; a nearby shot, touch, light and a head turn applied to each | 0 events | §5.5 |
| Q62 | Tremor and shivering belong to the conscious | A frightened survivor; a class II–III bleed | Fear tremor 8–12 Hz, 0.5–3 mm; shivering bursts 4–8 /min starting 10–40 min after the bleed and stopping at or before LOC | §5.6 |
| Q63 | No terminal secretions in a fast death | 100 deaths within 30 min; 50 comas lasting > 60 min | Terminal-secretion bubbling at the lips 0/100 in the fast deaths (assertion); 0.3–0.5 in the long comas | §5.1, §5.9 |

### 9.8 Severe trauma visuals (§6)

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q64 | Handguns never burst heads; contact shotgun blasts split them | 100 handgun head shots; 20 contact 12-gauge head shots | Handgun: burst 0/100. Shotgun: far-side crater, radial scalp flaps and a sagging face in 20/20; with the heart intact, blood pumps from the defect for minutes | §6.2, RB §9 #9, #14 |
| Q65 | Hammer blows escalate visibly | 6 blows of 60–70 J, 10 seeds | Blow 1: no spatter. Once blood is exposed: 20–300 impact stains of 0.5–4 mm per blow; depression +3–10 mm and +2–6 fragments per blow | §6.2 |
| Q66 | Punches do not burst eyes | 100 fist blows to the orbit; 20 hammer-face and thumb impacts | Globe rupture 0/100 from fists; rupture only when the impactor fits inside the 35 × 40 mm rim and exceeds 24,000–35,000 J/m² | §6.2, §3.9 #15 |
| Q67 | Chest and neck wounds breathe | Chest-wall defects of 5, 10 and 15 mm; a tracheal cut | Sucking only at ≥ 10–13 mm, with pink froth on expiration. Tracheal cut below the cords: no airflow at the mouth in 100 %; the lips move; bubbling at the neck | §6.2, §3.9 #16 |

### 9.9 Audio (§7)

Removed: audio was removed from the game; tests Q68–Q73 were deleted.

### 9.10 Scenarios (§8)

| # | Statement | Method (n) | Pass criterion | Ref |
|---|---|---|---|---|
| Q74 | Events keep their causal order | All 8 scenarios, seeds 1–10 | No event precedes its predecessor in: impulse → blink and flinch → mechanical failure → protective limbs → hand to the wound → looking → emotional reaction → physiological collapse. Conditional steps may be absent | §8 |
| Q75 | Brainstem shot (§8.1) | 10 seeds | No blink and no startle at any time; the head is the last contact at 0.8–1.0 s and 3–5 m/s; no breath, gasp or cough; lips blue by 60–120 s; `t_arr` 4–10 min | §8.1, §3.9 #11 |
| Q76 | Temporal shot, talk and die (§8.3) | 10 seeds on the main line | Talks for ≥ 20 min; the right pupil changes before the left; U1 at ~35 min, apnoea at ~72 min, `t_arr` at ~78 min (±15 %) | §8.3, RB §9 #39 |
| Q77 | Heart shot (§8.4) | 10 seeds | Advances for ≥ 5 s; LOC at 7–13 s; eyes up at LOC; no external arterial jet | §8.4 |
| Q78 | Carotid cut (§8.5) | 10 seeds | Pulsing jet of 0.5–1.5 m, one burst per beat; lips grey-lilac, never blue; event order as §8.5; LOC and `t_arr` equal to the RB solver output for the scenario's compression (C-17) | §8.5 |
| Q79 | Punches to knockout (§8.7) | 10 seeds | Blows after the knockout are purely passive; obstructed breathing when supine; on waking, the eyes open first; the same question is repeated every 30–120 s | §8.7 |
| Q80 | Hammer with seizure (§8.8) | 10 seeds on the main line | Clonus starts in the paralysed right hand and marches at 5–30 s per segment; head and eyes turn right before generalisation; Todd's paresis lasts 11 s – 22 min | §8.8 |

### 9.11 Myth coverage

Every myth in §3.9 has at least one test.

| Myth (§3.9 #) | Tests |
|---|---|
| 1 Knock-back | Q32 |
| 2 Snap follows the bullet | Q33 |
| 3 Everyone falls | Q36 |
| 4 Heart shot = instant drop | Q37, Q77 |
| 5 Hydrostatic shock | Q05 |
| 6 Everyone screams | Q38 |
| 7 Unconscious bodies brace | Q42, Q47 |
| 8 Conscious falls look like ragdolls | Q49 |
| 9 Knockouts drift down | Q42 |
| 10 Eyes roll back at death | Q25 |
| 11 Head-shot bodies run or thrash | Q47, Q75 |
| 12 A dead body jerks when shot | Q44, Q61 |
| 13 A faint looks like death | Q46, Q58 |
| 14 Every stab is noticed | Q39 |
| 15 Punches pop eyes out | Q66 |
| 16 A cut windpipe lets the victim scream | Q67 |
| 17 Brain-injured characters act normally | Q06–Q13 |

### Simulation parameters (tests)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `test_body` | 75 / 1.75 | kg / m | Reference body; lengths scale by stature / 1.75 | `[K]` |
| `test_physics_hz` | 120 (Q53 also at 60) | Hz | | `[E]` |
| `prob_tolerance` | ±2σ, σ = √(p̄(1 − p̄)/n) | — | p̄ = midpoint of the stated range | `[G]` |
| `timing_pass` | ≥ 90 % inside; 100 % inside the range widened by 25 % of its width | — | | `[G]` |
| `latency_tolerance` | ±1 physics tick (8.3) | ms | Reflex events | `[E]` |
| `eye_angle_tolerance` / `pupil_tolerance` | ±2 / ±0.2 | ° / mm | | `[G]` |
| `joint_limit_tolerance` | ±3 | ° | T13 | `[E]` |
| `default_n` | 20 (timings); as stated (probabilities, ≥ 50) | runs | | `[G]` |
| `absolute_failures_allowed` | 0 | — | "never" / "always" statements | `[G]` |

### Visual/behavioural checklist (tests)
- Every Q test names the section that owns the behaviour, so a failure is fixed at its source.
- Batch tests run headless every night on fixed seeds; a failure attaches the event log of the failing seed.
- Before each release, a reviewer watches all eight §8 scenarios at 1× with the overlay on and signs off the order and timing of events.
- A test that depends on an open conflict (C-01, C-04, C-11, C-17) is re-baselined when that conflict is decided.

---

## Appendix A. Conflict register

"Chosen" is the value this document uses. "Open" means that a lead has to decide; until then the chosen value applies.

| ID | Topic | Source A | Source B | Chosen here | Status |
|---|---|---|---|---|---|
| C-01 | Segment masses | RB §7.2, §10.2: Dempster/Winter default (verified); de Leva optional "if falls look top-heavy" | R2-03 §1: de Leva 1996 (thigh 10.62 kg vs 7.5 kg Dempster) | de Leva for the ragdoll (§4.1); neck raised to 1.2 kg for the 10 : 1 mass-ratio rule | **Open** (ragdoll lead). T3–T6 and Q52 assume de Leva; if Dempster is kept, re-derive the pendulum targets. RB already allows de Leva as an option |
| C-02 | Early post-traumatic seizure probability | RB §4.5: 0.2 penetrating, 0.10–0.15 severe blunt, impact seizure 0.02–0.05 | This document §1.8: 0.05–0.10 penetrating and 0.02–0.04 blunt in the first hour; knockout 0.014 | Both kept: RB's values cover the first week (time skips); this document's cover the first hour of play | Resolved (different windows) |
| C-03 | Pupil dilation to pain | RB §5.2: pain or fear +1–2 mm within 0.5–2 s | R2-06 §12.1: pain +0.3–1.0 mm, onset 0.3–0.6 s, peak 1–2 s | Split: phasic pain spike +0.3–1.0 mm plus a tonic fear offset of +0.5–1.5 mm; together they reach RB's +1–2 mm | Resolved; R2-06 value `[K⚠]`, on the QA list |
| C-04 | Lids after a knockout | RB §5.3: open or closed about 50/50 | R2-02 §6.3: "open, glassy", lids half-open; this document p 0.8 | 0.8 open or half-open `[E]` | **Open** (low evidence on both sides; tune on video review) |
| C-05 | Syncope upgaze probability | RB §5 parameters: 0.6–0.8 | R2-02 S27 (Lempert 1996; 13 of 14 episodes): 0.6–0.9 | 0.6–0.9; RB's range lies inside it | Resolved |
| C-06 | Last movement after ischaemia with a beating heart | R1-04 (hanging-type series): last movement "up to ~4–7 min" | R2-04 fact-check correction: last twitch 110–450 s (default 240) | R2-04 corrected value | Resolved |
| C-07 | Damping during posturing | RB §4.10: ζ 0.9 | R2-03 §4.3: ζ 1.2–2.0 ("lead-pipe", slow) | R2-03 value | Resolved here; RB table to be aligned by its owner |
| C-08 | Fencing and tonic gains | RB §4.10: fencing ω 8–12, ζ 0.9; tonic ζ 0.7 | R2-03 §4.3: tonic ω 12–16, ζ 1.0–1.5, onset 50–200 ms | R2-03 values; fencing is driven as a tonic state | Resolved |
| C-09 | Spinal reflex probability after brainstem death | RB §4.8: p 0.1–0.2, 1–10 min | R2-04 §5.5 on S11: 0.2–0.4 (13–79 % across series; ~39 % in one series) | 0.2–0.4 when the heart keeps beating ≥ 60 s after brainstem death. RB's 0.1–0.2 fits as an unconditional per-death rate, since many brainstem deaths arrest early `[E]` | Resolved; QA check |
| C-10 | *Removed with §7 (voice loudness in shock; the game has no sound)* | — | — | — | Closed |
| C-11 | Myoclonus at LOC after a destroyed heart | RB §4.2, §4.9, RB §9 #33: p 0.9 | R2-04 §5.9: 0.8 (sudden onset), 0.5 (slow onset) | 0.8 default, tunable to 0.9; the RB #33 test tolerance must accept 0.8 | **Open** (minor) |
| C-12 | How to drive the joints | R2-03 §8.5: script torques first; 6DOF springs or velocity motors as alternatives to verify | RB §4.10, §8.2 (checked against the 4.5-stable source): no script-reachable joint motors before 4.8; 6DOF springs map to uncapped Jolt motors | Script torques with explicit caps and reaction torque (§4.4) | Resolved; revisit on Godot ≥ 4.8 |
| C-13 | Decerebrate hand orientation | R1-04 §4: arms "turned inward (backs of the hands facing each other or forward)", wrist flexion 60–80° | R2-01 §18.2: internal rotation 60–90°, full pronation 80–90°, wrist flexion 30–70° | Joint targets from R2-01 (§4.4). The R1-04 wording describes the same pose seen from the front; wrist 30–80° is acceptable | Resolved (wording) |
| C-14 | Reference stature | RB anatomy: 1.78 m | Round two: 1.75 m | Behaviour values are for 1.75 m; lengths scale by stature / 1.75 | Resolved |
| C-15 | Blink duration and rate | RB §5.2, RB §9 #41: full blink 250–400 ms; 12–20 /min | R2-06 §12.2: 100–400 ms; 15–20 /min | Spontaneous blink 250–400 ms; reflex or incomplete blinks 100–250 ms; default rate 15–20 /min, inside RB's 12–20 test band. §2.2, §2.3 and the §2 parameters were updated | Resolved |
| C-16 | Body friction | RB §4.10: skin or cloth on a floor 0.6–0.9; wet blood 0.1–0.25 | R2-03 §6.4: clothing on concrete 0.55; body bones 0.55–0.6 | Per-pair table (§4.6): bones 0.55–0.6, floors govern; RB's 0.6–0.9 applies to bare skin and rough floors | Resolved; verify the Jolt friction-combine rule |
| C-17 | Carotid bleed timing | RB §3.4 scenario D (supine, uncompressed, open neck): LOC 20–60 s, arrest 2–5 min; RB §9 #21: LOC 20–90 s | R2-04 §10.3 and §8.5: 1.0 L/min, LOC ~2.5–4 min with own-hand compression, `t_arr` ~5 min | RB's bleeding solver governs. §8.5 keeps its order of events and compresses its clock to match the solver | **Open**: run the solver on the §8.5 setup and update the times |

---

## Appendix B. Key references

Load-bearing `[S]` sources, copied from the reference lists of the research files (verification status is in those files). `[S]` values are at search-summary level. Open the source before a number is shown to the player as a measurement.

| Key | Reference | URL | Used for |
|---|---|---|---|
| R2-01:S14 | Neuroanatomy, Broca area (StatPearls) | https://www.ncbi.nlm.nih.gov/sites/books/NBK526096/ | Language dominance (§0.3, §1.5) |
| R2-01:S17 | Ringman J.M. et al. Unilateral neglect in an acute stroke cohort. *Neurology* 2004 | https://www.neurology.org/doi/10.1212/01.WNL.0000133011.10689.CE | Neglect rates (§1.5) |
| R2-01:S37 | Pronator drift (Neurosigns) | https://www.neurosigns.org/pronator-drift.html | Arm drift (§1.5) |
| R2-01:S39 | Cerebellar neurological signs (StatPearls) | https://www.ncbi.nlm.nih.gov/books/NBK556080/ | Cerebellar falls (§1.5) |
| R2-01:S44 | Holmes tremor (StatPearls) | https://www.ncbi.nlm.nih.gov/books/NBK562149/ | Tremors (§1.5, §5.5) |
| R2-01:S50 | Strabismus in third cranial nerve palsy (10-year series) | https://pmc.ncbi.nlm.nih.gov/articles/PMC4307654/ | CN III angles (§2.4) |
| R2-01:S54 | Pendular oscillation and ocular bobbing after pontine haemorrhage. *Cerebellum* 2019 | https://link.springer.com/article/10.1007/s12311-019-01086-6 | Bobbing (§2.3) |
| R2-01:S63 | CT assessment of conjugate eye deviation in acute stroke. *Neurology* 2003 | https://www.neurology.org/doi/10.1212/01.WNL.0000042086.98735.75 | Gaze deviation (§1.5, §2.4) |
| R2-01:S64 | Conjugate eye deviation with head version from a frontal eye field infarct. *Stroke* 2002 | https://www.ahajournals.org/doi/10.1161/str.33.2.642 | Gaze and head deviation (§1.5) |
| R2-01:S65 | Wyllie E. et al. Versive head and eye movements during seizures. *Neurology* 1986 | https://pubmed.ncbi.nlm.nih.gov/3703259/ | Versive seizures (§1.8, §2.4) |
| R2-01:S67 | Ping-pong gaze. *J Neuro-Ophthalmol* 2024 | https://journals.lww.com/jneuro-ophthalmology/fulltext/2024/03000/ping_pong_gaze__bouncing_back_from_structural.87.aspx | Roving and ping-pong gaze (§2.3) |
| R2-01:S68 | Doll's eyes (StatPearls) | https://www.ncbi.nlm.nih.gov/books/NBK551716/ | Oculocephalic reflex (§2.7) |
| R2-01:S76, S77 | Lucid interval (ScienceDirect Topics); Progressive epidural haematoma, incidence and risk factors | https://www.sciencedirect.com/topics/medicine-and-dentistry/lucid-interval ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3536037/ | EDH (§1.7) |
| R2-01:S87 | Rostrocaudal deterioration (Stroke Manual) | https://www.stroke-manual.com/rostro-caudal-deterioration/ | Herniation stages (§1.7) |
| R2-01:S88 | Kernohan–Woltman notch phenomenon (LITFL) | https://litfl.com/kernohan-woltman-notch-phenomenon/ | Kernohan (§1.7) |
| R2-01:S99 | Hosseini A.H., Lifshitz J. Brain injury forces of moderate magnitude elicit the fencing response. 2009 | https://pmc.ncbi.nlm.nih.gov/articles/PMC11421656/ | Fencing (§1.8, §3.7) |
| R2-01:S100 | McCrory P.R. et al. Concussive convulsions | https://pubmed.ncbi.nlm.nih.gov/9519401/ | Concussive convulsion rate (§1.8) |
| R2-01:S103 | Annegers J.F. et al. Seizures after traumatic brain injury. *NEJM* 1998 | https://www.nejm.org/doi/full/10.1056/NEJM199801013380104 | Post-traumatic seizures (§1.8) |
| R2-01:S110 | Gallmetzer P. et al. Postictal paresis in focal epilepsies. *Neurology* 2004 | https://www.neurology.org/doi/abs/10.1212/WNL.62.12.2160 | Todd's paresis (§5.4) |
| R2-01:S111 | Decerebrate and decorticate posturing (StatPearls) | https://www.ncbi.nlm.nih.gov/books/NBK559135/ | Posturing (§4.4, §5.7) |
| R2-02:S1, S2 | Startle reflex (ScienceDirect Topics); Laryngeal auditory startle reflex. *Laryngoscope* 2026 | https://www.sciencedirect.com/topics/biochemistry-genetics-and-molecular-biology/startle-reflex ; https://pmc.ncbi.nlm.nih.gov/articles/PMC13357233/ | Startle latencies (§3.3) |
| R2-02:S4 | First-trial postural reactions vs the acoustic startle. *J Neurophysiol* 2010 | https://journals.physiology.org/doi/full/10.1152/jn.01080.2009 | Habituation (§3.3) |
| R2-02:S5 | Patrick U.W. *Handgun Wounding Factors and Effectiveness*. FBI Firearms Training Unit, 1989 | https://archive.org/details/fbi-handgun-wounding-factors-and-effectiveness | Heart-shot capability (§3.8) |
| R2-02:S8 | Ellifritz G. An alternate look at handgun stopping power (non-peer-reviewed) | https://www.activeresponsetraining.net/an-alternate-look-at-handgun-stopping-power | Psychological stop calibration (§3.6) |
| R2-02:S12 | Force Science turning studies (2023 summary) | https://www.forcescience.com/2023/02/force-science-validates-legacy-research-findings-part-ii/ | Turn-away time (§3.3) |
| R2-02:S21 | Wojcik L.A., Thelen D.G. et al. Single-step recovery from a forward fall. *J Gerontol A* 1999 | https://academic.oup.com/biomedgerontology/article/54/1/M44/594110 | Step recovery (§3.3) |
| R2-02:S25 | Timing and amplitude of arm muscle activity before impact in a forward fall. *J Biomech* 2023 | https://pmc.ncbi.nlm.nih.gov/articles/PMC10257944/ | Protective arms (§4.6) |
| R2-02:S26 | Lempert T. et al. Syncope: a videometric analysis of 56 episodes. *Ann Neurol* 1994 | https://onlinelibrary.wiley.com/doi/abs/10.1002/ana.410360217 | Syncope, jerks (§3.6, §5.3) |
| R2-02:S27 | Lempert T., von Brevern M. The eye movements of syncope. *Neurology* 1996 | https://pubmed.ncbi.nlm.nih.gov/8780096/ | Upgaze at LOC (§2.3) |
| R2-02:S28, S29 | Walilko T.J. et al. Olympic boxer punches, *Br J Sports Med* 2005; Viano D.C. et al. Concussion in professional football, Part 10, *Neurosurgery* 2005 | https://pubmed.ncbi.nlm.nih.gov/16183766/ ; https://pubmed.ncbi.nlm.nih.gov/16331164/ | α model (§3.7) |
| R2-02:S33 | Knockouts are accompanied by an immediate loss of muscle tone. *Med Res Arch* 2023 | https://esmed.org/MRA/mra/article/view/4007 | Tone loss (§3.7, §4.4) |
| R2-02:S36 | Davis G.A. et al. Video signs of concussion. *Br J Sports Med* 2019 | https://pubmed.ncbi.nlm.nih.gov/30954947/ | "No protective action" (§3.9) |
| R2-02:S37 | Nociceptive withdrawal reflex | https://pmc.ncbi.nlm.nih.gov/articles/PMC6509112/ | Withdrawal latency (§3.3) |
| R2-02:S39 | PSPI pain score (automatic pain detection from facial actions) | https://pmc.ncbi.nlm.nih.gov/articles/PMC3296481/ | Pain face (§2.3) |
| R2-02:S44 | Roelofs K. et al. Facing freeze. *Psychol Sci* 2010 | https://journals.sagepub.com/doi/abs/10.1177/0956797610384746 | Tonic immobility (§3.6) |
| R2-02:S16, S55 | Survivor accounts (anecdotal); liver shot and winding (encyclopaedic) | See the R2-02 reference list | Awareness, liver and solar-plexus rows (L) |
| R2-03:S1 | de Leva P. Adjustments to Zatsiorsky–Seluyanov's segment inertia parameters. *J Biomech* 1996;29(9):1223–1230 | https://ebm.ufabc.edu.br/wp-content/uploads/2013/12/Leva-1996.pdf | Segment masses (§4.1) |
| R2-04:S3 | Theodore W.H. et al. The secondarily generalised tonic-clonic seizure: a videotape analysis. *Neurology* 1994 | https://pubmed.ncbi.nlm.nih.gov/8058138/ | GTC timing (§5.4) |
| R2-04:S11 | Frequency of spinal reflex movements in brain-dead patients | https://www.sciencedirect.com/science/article/abs/pii/S0041134503012752 | Spinal reflexes (§5.5) |
| R2-06:S2 | Arnal L.H. et al. Human screams occupy a privileged niche in the communication soundscape. *Curr Biol* 2015 | https://www.cell.com/fulltext/S0960-9822(15)00737-X | Scream roughness (was §7.4; audio removed, reference only) |
| R2-06:S3 | Voice pitch is preserved from speech to screams, roars and pain cries. *R Soc Open Sci* 2020 | https://royalsocietypublishing.org/rsos/article/7/2/191642 | F0 continuity (was §7.4; audio removed, reference only) |

Standard texts behind many `[K]` values (not re-opened in this pass): Plum and Posner (coma, pupils, breathing patterns); Wijdicks and Greer (brain death, spinal reflexes); Lempert 1994 (syncope); Rossen 1943 (cerebral arrest); Winter (biomechanics); the Godot 4.5-stable source and manual, as read for RB §4.10 and §8.2.

---

## Appendix C. Suspicious content

- **None encountered in this synthesis.** The only material read was the project's own documents: `docs/research/04_neuro_death_eyes.md`, `docs/research2/01`–`06` and `docs/REALISM_BIBLE.md`. They were treated as data, and none contained instructions addressed to the reader.
- One WebSearch was refused by the tool harness (session search budget 200/200 exhausted). That notice came from the local harness, not from a web page, and it was not treated as an instruction. No setting was changed in response.
- No WebFetch was made, no shell command was run, nothing was downloaded, installed or executed, no code was copied from the web, and no file other than this document was created or edited.
- The research files' own suspicious-content sections report no prompt-injection attempts. R2-01 §23 and R2-02 §16 note irrelevant patent-PDF links, forum threads and commercial blogs in result lists; none of these were opened, and none is the sole source of a load-bearing number. The other files report no web content (R2-03 §13, R2-04 §17, R2-05 §19, R2-06 §20).

*End of document.*
