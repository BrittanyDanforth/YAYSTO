# Gore Head — Behaviour Bible (implementation spec for everything the body does)

Project: **Gore Head**. Godot 4.5 (Forward+, GDScript + Godot shaders, built-in Jolt), Skeleton3D + PhysicalBone3D ragdoll, procedurally generated full adult body. The subject is fictional and procedurally generated. No real person is modelled.
Status: v1.0, 2026-09-26.
Audience: simulation, animation/ragdoll, AI/behaviour, eye/face, shader/VFX and audio engineers, plus the reviewers who test the game against §9.

**Scope.** This document specifies what the body **does**:
- the neuro model and its deficits (§1);
- the eyes and face (§2);
- reactions to being hit (§3);
- falls and the ragdoll (§4);
- involuntary movement (§5);
- the look of severe trauma (§6);
- sound (§7);
- eight second-by-second scenario scripts (§8);
- a reviewer test list (§9).

`docs/REALISM_BIBLE.md` (RB) remains the specification for wounds, blood and circulation, the physiology state machine, post-mortem changes and anatomy. This document **reads** the physiology state of RB §4 and turns it into motion, eyes, face and sound. Where the two documents give different values, Appendix A records the conflict and the value chosen.

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
  - RB anatomy uses 1.78 m. Scale lengths by stature / 1.75 and masses by segment fractions (§4.1).
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
  - Per-character traits are rolled at spawn: language dominance (left 0.90), mindset, expressivity, pain-face type, speaking F0, vocal-tract length, and a per-region severity factor of 0.85–1.15.

### 0.4 System map

```
RB §4 physiology (20 Hz)          ──► NeuroResolver (§1) ── channels ──┐
 V, MAP, CPP, ICP, SpO2, brain O2                                        │
 reserve, cord level, pain, stress                                       ▼
 airway, lungs, t_arr, t_dead      ──► ReactionSelector (§3) ──► MotorMixer (§4) ──► PhysicalBone3D PD torques
                                   ──► InvoluntaryGen (§5)   ──┘        │
                                   ──► EyeFaceController (§2) ──► eye/lid/jaw bones, blendshapes, shader uniforms
                                   ──► AudioGen (§7)          ──► AudioStreamPlayer3D (mouth, wound, landing points)
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
   - A brainstem lesion gives **crossed signs**: cranial-nerve deficits (eye, face, tongue, voice) on the lesion side, limb weakness on the other side.
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
| `medulla_lateral` | ~2 | (6, 7, −8) | `horner`, `dysphagia`, `hoarse`, `ataxia_limb` ipsi, `lateropulsion`, `hiccup` | Wallenberg syndrome. Both sides or the centre → **apnoea**, vasomotor collapse | Ipsi (crossed sensory) | 0 s | 0.02 / 0.15 | Signs rolled independently (§1.5) | `[S R2-01:S58,S59]` (M) |
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
| `str_tongue` | 0–1 | M1_bulbar, medulla medial | Protrusion deviates toward the weak side (cortex) or toward the lesion (medulla); dysarthria | §7 `[K] (H)` |
| `ataxia_limb_{side}` | 0–1 | cb_hemi (ipsi), red nucleus (contra), lateral medulla (ipsi) | Reach overshoot 3–10 cm; intention tremor 3–5 Hz, 1–5 cm at the fingertip in the last 10–20 cm of a reach | §3, §5 `[S R2-01:S44]` |
| `ataxia_trunk` | 0–1 | vermis | Gait table §1.5.3; titubation; cannot sit unsupported at sev > 0.7 `[E]` | §4 |
| `lateropulsion` | vector | lateral medulla (toward the lesion, 5–15 % body weight), thalamic astasia (backward or contra), pusher (toward the paretic side) | Constant lateral force in the balance controller | §4.8 `[E] R2-01 §13.5` |
| `gaze_bias` | ° yaw | FEF, putamen, PPC neglect (toward), seizure (away), pons (away) | Resting gaze and head yaw offset | §2 |
| `eye_overlay_{L,R}` | struct | CN III, IV, VI, INO, skew, Parinaud, Horner, thalamus | Per-eye offsets, lid and pupil overrides | §2.4 |
| `vision_mask_{eye}` | 4 quadrants + centre | V1, optic radiation, optic nerve, chiasm | Perception culling for the AI; head compensation 10–25° toward the blind side | §3 `[E] R2-01 §7.2` |
| `vocal_state` | enum | Broca, Wernicke, global, M1_bulbar, cerebellum, medulla, GCS V | Speech generator (§7.5) | §7 |
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

| State | Cause | What is heard | Obeys commands | Tag |
|---|---|---|---|---|
| `NORMAL` | — | Normal speech (articulation rate 4–6 syll/s) | Yes | `[K] (H)` |
| `DYSARTHRIC_UMN` | M1 face/tongue, capsule genu | Slurred, slow (3–5 syll/s), words intact | Yes | `[K] (H)` |
| `DYSARTHRIC_CEREBELLAR` | Cerebellum | Scanning: equal, excess stress; explosive loudness ±6–10 dB per syllable; 3–4 syll/s | Yes | `[S R2-01:S16]` (H) |
| `DYSARTHRIC_BULBAR` | Pons/medulla (CN VII, IX, X, XII) | Nasal, breathy, hoarse, wet; weak cough; 3–5 syllables per breath | Yes | `[K] (M)` |
| `NONFLUENT` | Broca + surroundings | 10–50 words/min, 1–5 s groping pauses; automatic phrases and **swearing preserved** | p 0.7 | `[S R2-01:S12,S13]` |
| `JARGON` | Wernicke | Fluent, normal prosody, neologisms; unaware of the errors | p 0.1 | `[S R2-01:S12]` |
| `GLOBAL` | Large dominant MCA territory | Mute, or one recurring 1–3-syllable utterance | 0 | `[K] (H)` |
| `MUTE_AKINETIC` | Bilateral medial frontal/cingulate; left SMA | Silence; rarely a whispered monosyllable after 5–30 s | Variable | `[S R2-01:S4,S9]` |
| `CONFUSED` (GCS V4) | Concussion, hypoxia, class III, frontal | Repeats questions every 30–120 s; response latency 1–5 s | Partly | `[K] R2-06 §7.1` |
| `MOAN_ONLY` (V2) | Stupor | Moans and groans, especially to pain | No | `[S R2-01:S93]` |
| `SILENT` (V1) | Coma, apnoea, locked-in, airway below the cords | Nothing (locked-in: nothing despite full awareness) | Locked-in: yes (eyes) | `[S R2-01:S56]` |

- **Pain vocalisation survives aphasia** (it is brainstem and limbic): a left-hemisphere wound removes words, not screaming `[K] (H) R2-01 §5.2`.
- The *capacity* to scream is not a *tendency* to scream. Silence, a grunt or "I'm hit" are common after gunshots and stabs; §3.6 and §7.4 gate vocalisation.

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

| GCS | Category | Eyes (E) | Voice (V) | Motor (M) | Behaviour the player sees |
|---|---|---|---|---|---|
| 15 | Alert | Spontaneous | Oriented | Obeys | Normal, with focal deficits |
| 13–14 | Mild | Spontaneous | Confused (V4) | Obeys or localises | Awake, repeats questions, unsteady walking |
| 9–12 | Moderate | To voice or pain | Words / moans | Localises or withdraws | Eyes flutter open when shouted at; pushes the player's hand away; cannot stand |
| 6–8 | Severe | To pain or none | Moans or none | Withdraws or postures | Eyes shut; groans when hurt; stiffens; snoring or gurgling airway |
| 3–5 | Deepest | None | None | Posturing or flaccid | Nothing except stiffening spasms; snoring or gurgling if breathing |

- E follows arousal and lid control. Lid swelling from periorbital haematoma blocks eye opening (clinically "not testable") `[E]`.
- V follows `vocal_state`. **Aphasia lowers V without lowering consciousness.**
- M is the best response the character can produce (§1.8 posturing, §3.5 withdrawal).
- **Locked-in** scores E4 V1 M1 with full awareness: vertical eye movements and blinks answer questions `[K] (H)`.

### 1.6 Spinal cord levels (engine data file `cord_levels.csv`)

Vertebra-to-segment mapping, complete-injury probabilities and incomplete syndromes: RB §4.6. The behaviour columns are added here `[K] (H)` patterns, `[E]` drive values, R2-03 §4.5.

| Level (complete) | Breathing capacity (fraction of vital capacity) | Voluntary groups (tone 1) | Flaccid groups (tone 0, no withdrawal) | Resting / falling picture | Voice |
|---|---|---|---|---|---|
| C1–C3 | 0–0.1 (apnoea) | Face, eyes, jaw, weak neck turn and shrug (CN XI) | Everything below | **Cut strings but awake**: eyes wide and darting, mouth opening silently 10–30 times/min, neck straining, chest still; lips blue by 1–2 min; LOC at 90–180 s | Aphonic |
| C4 | 0.25 | + shoulder shrug | Arms, trunk, legs | Paradoxical belly breathing | Breathy, 1–3 words |
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

#### 1.7.4 Breathing pattern by level (feeds §5.2 and §7)

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
| `p_seizure_penetrating_1h` / `blunt_1h` | 0.05–0.10 (×1.5 motor/temporal) / 0.02–0.04 | p | | `[E]` on `[S R2-01:S103]` |
| `concussive_convulsion_p` | 0.014 | p | On knockout | `[S R2-01:S100]` |
| `posture_episode` | ramp 0.5–2 s, hold 5–60 s, release 1–3 s; refractory 5–20 s | s | | `[E] R2-01 §18.2, R2-04 §5.6` |
| `fencing_p` / `duration` | 0.66 / 2–10 (≤ 20) | p / s | | `[S R2-01:S99]` ✓ |

### Visual/behavioural checklist (neuro model)
- The same bullet produces a different character depending on its track: a limp arm with a sagging mouth corner; a drunk-looking lurch toward the wound; a silent staring statue; a violently flinging arm; crossed eyes with a pinpoint-pupil coma.
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

**AU mixing:** sources combine by **maximum per AU**, never by sum. Mouth AUs from the voice and breathing generators override the expression mouth `[E] R2-06 §8.4`.

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
| Blink | Close 70–100 ms, reopen 150–250 ms, total 100–400 ms | `[K] (H) R2-06 §12.2` |
| Pupil light reflex | Latency 200–300 ms; constriction ~1 s; redilation 2–4 s; consensual | `[K] (H)` |
| Hippus | ±0.2–0.5 mm at 0.2–0.5 Hz (living, awake) | `[K] RB §5.2` |
| Pathological pupil change | 0.5–1 mm/s for acute changes; minutes for herniation stages | `[E] R2-01 §14.9` |
| Tears | Basal 1–2 µL/min; reflex 10–100 µL/min; overflow beyond ~25–30 µL in the sac | `[K] R2-06 §12.4` ✓ |

### 2.3 Base states

`GCS` = Glasgow Coma Scale; `PSPI` = Prkachin–Solomon pain score (0–16) = AU4 + max(AU6, AU7) + max(AU9, AU10) + AU43, where AU43 is **binary**; game mapping PSPI ≈ 1.6 × pain (0–10) `[S R2-02:S39]` ✓.

| State | Entry condition | Upper lid (mm) | Gaze | Pupil (mm) / reactivity | Blinks | Saccades / slow movements | Face tone and droop | Jaw (mm) | FACS / PSPI | Tag |
|---|---|---|---|---|---|---|---|---|---|---|
| `ALERT` | GCS 15, stress < 0.3 | 9–10 | Fixations on targets | base 3–4, brisk; hippus | 15–20 /min (10–25), 100–400 ms | ~2–3 saccades/s, 2–15° | Tone 1; micro-motion 0.02–0.05 weight at 0.3–2 Hz; swallow every 30–120 s | 0–2 | none | `[K] R2-06 §8.4, §12` |
| `FEAR` (threat seen) | stress ≥ 0.3 and threat present | **11–12** (white above the iris) | Hypervigilant scanning 2–4 saccades/s among attacker, weapon and exits; weapon focus | base +0.5–1.5 (4–7), brisk | Suppressed (< 5 /min), then bursts | Fast | Tone 1; nostrils flare with breaths when RR > 25 | 5–10 (AU26B) | 1C 2C 4B **5D** 7B **20C** 26B 38B | `[K] (H) R2-06 §8.2` ✓ |
| `PAIN` (acute) | pain ≥ 2 | Mild 7–9; moderate squeezed 3–6; severe **shut at each burst apex** | Fixed on the wound, or shut | Pain spike +0.3–1.0 within 0.3–0.6 s, peak 1–2 s, decays over 3–10 s; stays reactive | Replaced by squeezes of 0.3–3 s | Few | Tone 1 | Clenched between cries; opens with vocalisation | Mild 4B, 6B/7B, 10A (PSPI ~3–5); moderate 4C 6C 7C 9B 10C 43B 20B 25 (PSPI ~8–11); severe 4D–E 6D 7D 9D 10D **43** 20C 25 31 21C (PSPI 13–16) | `[S R2-02:S39]` `[K⚠] R2-06 §12.1` |
| `PAIN_SUPPRESSED` (fighter, stoic) | pain ≥ 2 and mindset = trained or enraged | 6–8 | On the threat | +0.3–1.0 | Normal | Normal | Tone 1 | Set (AU31C) | 4B 7B **24C** 17B 31C; full pain face leaks for 0.3–1 s | `[K] (M) R2-06 §8.2` |
| `DAZED` / concussed / rocked | concussion timer > 0, GCS 13–14 | 7–9 | **Blank, vacant stare**; slow drift | Normal, reactive | Slow, 5–10 /min | 0.5–1 /s at peak velocity ×0.6–0.8; horizontal nystagmus p 0.3 (1–3 Hz, 2–5°); poor convergence (exophoria 2–5°) | Tone 0.6–0.8 | 2–5 | Near neutral, 26A; 1B + 4B when addressed | `[S R2-01:S97,S102]` `[E] R2-02 §6.4` |
| `SHOCK_III` | blood loss 0.30–0.40 or MAP < 65 | 5–8, heavy; eyes look **sunken** (shader 0.5–1 mm) | Vacant; poor tracking | Normal to large, **sluggish** (latency × 1.5) | 5–10 /min, slow (300–500 ms) | 0.5–1 /s | Expression AUs ≤ A; 41–42 | Open 10–20, dry lips | Grimace only when moved (× 0.3–0.6) | `[K] RB §4.9, R2-06 §8.2` |
| `STUPOR` (GCS 9–12, class IV before LOC) | loss > 0.40, CPP < 40, or herniation stage ≥ U1/C1 | 2–6; drop shut and struggle open | Roving, drifting | Variable | 0–5 /min | Roving | Tone 0.3–0.5; nasolabial folds flatten | Slack, 5–15 | Grimace to pain only | `[K] R2-04 §7.1` |
| `CORTICAL_BLIND` (overlay on alert states) | both V1 sev > 0.8 | Normal | Conjugate, **slow wander 5–20 °/s, no fixation, no tracking** | **Normal and reactive** | Normal; **no menace blink** | No target saccades | Tone 1; puzzled 1B 4B | Normal | Per emotion | `[S R2-01:S22]` (H) |
| `SYNCOPE` / anoxic LOC (transient programme; §2.5) | brain O₂ reserve ≤ 0 | **Open** (p ≥ 0.9), 6–10 | **Up 10–30° for 2–10 s** (p 0.6–0.9); downbeat nystagmus first in ~0.4 of those; back to the midline over 10–60 s | Dilating | None | Lid flutter with jerks | Tone → 0 over 0.5–2 s | Slack; chewing and lip smacking (p 0.5–0.8) | — | `[S R2-02:S26,S27]` ✓ |
| `KNOCKOUT` | α-model LOC (§3.7) | Open p 0.8, glassy (conflict C-04) | Tonic upgaze in 0.5 of open eyes, 2–10 s; then neutral or slightly divergent 5–15° | Equal, reactive | None | Doll's eyes present | Tone 0 within ≤ 100 ms | Slack; snoring when supine | — | `[E] R2-02 §6.3` |
| `SEIZURE_TONIC` | seizure (§5.4) | **Wide**, 10–12 (open p 0.9–0.97) | Forced 30–45° away from the focus, or up | **6–8, unreactive** within 1–3 s | None | Fixed | Congested; blue from 10–20 s | **Clenched** (AU31) | Grimace, 20D | `[K] R2-04 §4.1` |
| `SEIZURE_CLONIC` | seizure | Lids jerk with each beat | Deviated, jerky; epileptic nystagmus beating away from the focus | Dilated, unreactive | Eyelid clonus | — | Rhythmic grimace | **Snaps shut with each jerk** | Froth at the lips | `[S R2-01:S71]` |
| `POSTICTAL` | seizure ended | Half-closed 2–5 (closed p ~0.5) | Roving or still deviated, slightly divergent | Large, sluggish → normal over 0.5–5 min | Rare | Roving | Tone 0 → returning | Slack; stertor | — | `[K] R2-04 §4.3` |
| `COMA` (brainstem intact, GCS 3–8) | resolver coma, pons and midbrain working | Closed, or a 1–5 mm gap (lagophthalmos p 0.3–0.7); **a lifted lid closes again over 1–2 s** | Resting divergence 5–15°; **roving** 10–30° at 5–20 °/s; or ping-pong (bilateral hemispheric) cycle 3–7 s; periodic alternating gaze reverses every ~2 min (metabolic) | 2–5, reactive (diencephalic stage 1–3) | None; corneal reflex **present** | **Doll's eyes gain 1.0** | Tone 0; hemiplegic cheek puffs 3–10 mm with each breath out | 5–20 open when supine | Grimace to pain on the working side only | `[S R2-01:S66,S67]` |
| `COMA_PONTINE` | pons_teg sev > 0.5 | As `COMA` | No horizontal movement; **ocular bobbing**: fast down 5–20° at 80–200 °/s, pause ~0.5 s, slow return 1–3 s, 2–15 /min irregular | **1.0–1.5, pinpoint** (reactive only under magnification) | None; corneal **absent** | Doll's eyes absent horizontally | Tone 0 | Slack | — | `[S R2-01:S54,S57]` |
| `COMA_MIDBRAIN` | midbrain sev > 0.5 | As `COMA`; ptosis with CN III | Dysconjugate; vertical gaze lost; CN III eye down and out | **4–6 mid-position, fixed**, often irregular | None | Doll's eyes weak | Tone 0 (decerebrate episodes) | Clenched during episodes | — | `[K] R1-04 §2.2` |
| `LOCKED_IN` | both ventral pons halves destroyed, tegmentum spared | Open; **voluntary blinks** | **Only vertical movements** (0–30° up/down) answer the player; horizontal absent | Normal, reactive | Voluntary | Vertical only | **Whole face flaccid** | Slack | None (silent) | `[S R2-01:S56]` |
| `C1C3_AWAKE_APNOEA` | cord C1–C3 complete, brain intact | **Wide 11–12**, tears | Darting 2–4 saccades/s, "pleading" | Normal → dilate from 60–120 s | Normal or rapid | Fast | Terror face 1+2+5+20; mouth gapes silently 10–30 /min | Gaping 15–30 | Terror | `[E] R2-04 §2.2, RB §5.4` |
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
| Supine | Opens 10–30 mm (5–20 mm while alive and unconscious) | Slide 3–10 mm toward the ears | Stay; drop 2–4 mm | Falls back (snoring while alive) |
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
| `blink_duration` normal / shock | 100–400 / 300–500 | ms | | `[K]` |
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
  | **E0** | Near miss, sound only |
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
| `FREEZE` | L4 | Threat or first hit | 0.3–0.5 s | 0.5–3 s | Fixed stare, reduced sway. Tonic immobility p 0.02–0.1 (seconds to hours: stiff, eyes open, silent) | `[S R2-02:S44]` `[E]` |
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
| 8 | Lower face avulsion (E3) | Airway threatened when supine | **Often conscious** (p 0.7–0.9 if the track is in front of the skull base): leans forward, gurgling grunts, spits teeth and blood, fights to sit up if pushed onto the back | 0.3 | 0.5 | `[K] R2-05 §4.4` |
| 9 | Neck vessels | Arterial jet or venous pour | `HOLD_NECK` 0.3–0.8 s; panic; flees or fights. Carotid with poor collaterals (p 0.2–0.3): contra weakness, face droop, aphasia (left carotid), eyes toward the cut side at 5–30 s | Controlled descent as MAP falls (RB §4.7) | 0.5 | `[E] R2-04 §10.3` |
| 10 | Larynx / trachea | Air leak | Coughs spraying blood; bubbling and whistling; voice hoarse or lost (aphonic below the cords); subcutaneous emphysema over minutes | 0.2–0.4 | 0.3 | `[K] R2-02 §3` |
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
| 21 | Femoral shaft | **Loaded: gives way within the stance, 0.1–0.3 s**; mid-thigh angulation 10–30°; shortening 2–5 cm; foot turned out 45–90° | Grabs the thigh with both hands; every movement brings a pain spike (vocal mix §7.4); later drags the leg | 0.85–0.95 loaded (D); unloaded at the next step | 0.3 | `[S R2-02:S48]` `[K]` |
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
| 29 | Solar plexus ("winded") | Diaphragm spasm | Bent over; silent failed gasps 5–30 s (up to 120), then a whooping inhalation; panic | 0.3 | 0.3 | `[S R2-02:S55]` (L) |
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
| Aphasia | Speech replaced by moans, jargon or silence; swearing kept | Vocal set §1.5.4 | `[K]` |
| Frontal / diffuse / concussion | Late, inappropriate, perseverative reactions | `rt_mult` 1.3–3.0; inappropriate p 0.1–0.4; perseveration p 0.2–0.5 per decision | `[E] R2-02 §10` |
| Cerebellar | Reaching for the wound overshoots 3–10 cm with a 3–5 Hz tremor; ataxic stagger; vomiting | §1.5.3 | `[S R2-01:S44]` |
| Diplopia / one eye blind | Reach error +2–5 cm; head tilt; closes one eye | — | `[E]` |
| Cortical blindness / hemianopia | No reaction to threats in the blind field; startle to sound still present | Vision mask | `[S R2-01:S22]` |
| Cord level | Below the level: no withdrawal, no pain behaviour, no protection | Spinal shock 0–24 h | `[S R2-02:S46]` |
| Seizure / posturing | Replaces all protective behaviour; stimuli trigger posturing | §1.8, §5.4 | `[K]` |
| Shock class III / IV | Wound check slow; controlled descent; voice capped (§7.4) | Strength 0.4–0.6 / 0.1–0.3 | `[E] R2-03 §5.5` |

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

**Vocal gating** (full model in §7.4) `[E] R2-06 §6.3`:
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
| Knockout phenomenology | Tone lost ≤ 100 ms (the knees go before the head recoils); fencing p 0.66; collapse limp 0.3 / fencing crumple 0.5 / plank 0.2; eyes per §2.3; snoring when supine; LOC 5–60 s (tail 300); concussive convulsion p 0.014 | `[S R2-02:S33,S35]` `[S R2-01:S100]` |
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
| 6 | Everyone screams when shot or stabbed | Silence, a grunt, a gasp or "I'm hit" are common; the cry comes at discovery | Vocal gating | `[K] R2-02 §14 row 15` |
| 7 | Unconscious bodies brace their fall | "No protective action – floppy" | Tone 0, no IK within ≤ 100 ms | `[S R2-02:S36]` |
| 8 | Conscious falls look like ragdolls | Arms react in ~100–200 ms; hands land first in ~74 % | CatchFall | `[S R2-02:S25]` |
| 9 | Knockouts drift down slowly | Tone lost ≤ 100 ms; plank or crumple | Tone ramp | `[S R2-02:S33]` |
| 10 | The eyes roll back at death | Upgaze belongs to the first seconds of LOC; the dead rest near straight ahead or slightly divergent | `assert_no_upgaze_in_dead` | `[K] (H) R2-04 §12` |
| 11 | Head-shot or headless bodies run or thrash | Flaccid collapse; at most a jerk and 5–20 s of twitches | Release table §5.5 | `[K] R2-05 §2.5` |
| 12 | A dead body jerks when shot | Mechanical motion only, plus a rare local muscle bulge | Row 38 | `[K] R2-04 §5.5` |
| 13 | A faint looks like death | Eyes open and turned up, 1–10 jerks, awake in ~12 s | Syncope programme | `[S R2-02:S26]` ✓ |
| 14 | Every stab is noticed | Often felt as a punch; noticed later | Awareness model | `[S R2-02:S16]` |
| 15 | Punches pop eyes out | The orbital rim (~35 × 40 mm) stops the fist; a hammer face or thumb does reach the globe | Globe-rupture risk by impactor width | `[K] (H) R2-05 §5` |
| 16 | A cut windpipe lets the victim scream | No voice below the cords; air hisses and bubbles at the neck | `aphonic_if` rule | `[K] (H) R2-05 §14.2` |
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
- A clean hook to the jaw: the head whips round in about a tenth of a second and the legs go before the head comes back; no hands break the fall; the body lies snoring with one arm stuck up for a few seconds.
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
| Long-bone fracture (virtual joint) | Bend / twist | — | — | ±30–90 / ±20–60 at stiffness 0.05–0.2 × intact, heavy damping | Crepitus audio (§7) |

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
| Forearm | Neutral to 45° pronation | **Full pronation 80–90°** (palms turned outward and backward) | Neutral | Pronated / neutral |
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

**Physics floor** `[E]` ✓: free fall of the CM (0.84 m) takes 0.41 s; no collapse from standing reaches the ground faster. Energy dissipated ≈ 620 J (used for impact loudness).

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

  Set `friction` directly on each `PhysicalBone3D`; it has no PhysicsMaterial slot.
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

<!-- CONTINUE: section 5 -->
