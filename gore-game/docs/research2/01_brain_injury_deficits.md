# 01 (round 2) — Brain injury to functional deficit: a region-by-region map

Project: **Gore Head** (Godot 4.5, Forward+, GDScript, Jolt). Research input for the **lesion resolver** (wound track to brain regions to deficits), the **motor/ragdoll drive system**, the **eye system**, the **vocal system** and the **physiology state machine**.
Audience: simulation, animation, eye/shader and audio engineers. Clinical tone. The subject is a fictional, procedurally generated adult.

Round-one cross-references (read these first; this document does not repeat them):
- `docs/research/04_neuro_death_eyes.md` = **[R1-04]**. Already covers: brainstem destruction outcomes by level (§2.2), the "cut strings" collapse (§2.3), hemisphere-vs-brainstem consciousness rule and a short per-lobe table (§3.1–3.3), impact brain apnoea (§3.5), knockout, fencing response and concussive convulsion basics (§3.6), GCS motor 1–6 and basic decorticate/decerebrate (§4.1), GTC seizure basics (§4.2), shared physiology constants (§1), the game time-scale policy (§0.3).
- `docs/research/01_gunshot_wounds.md` = **[R1-01]**. Brain wound track, cavitation, the ~18 mm axonal-injury radius around low-energy tracks, retained capacity to act, bihemispheric mortality.

This document goes deeper: **what each region does when destroyed, which side, how fast, how much tissue it takes, and what it looks like from outside**, plus a full eye-sign table, TBI progression over minutes to hours, seizures and involuntary movements, posturing joint targets and GCS behaviour.

---

## 0. Read this first

### 0.1 Method and limits

- About 115 `WebSearch` queries were run for this document (the session's shared search budget then ran out). `WebFetch` is blocked by network policy, so **no page was opened in full**. Values tagged [S#] come from search-result summaries of the listed pages. Before a number becomes a hard constant, QA should open the source (priority list in §21).
- Numbers not found in search results come from the author's knowledge of standard texts (Plum & Posner's *Diagnosis of Stupor and Coma*, Adams & Victor, Leigh & Zee *The Neurology of Eye Movements*, Blumenfeld *Neuroanatomy through Clinical Cases*, ATLS, Brain Trauma Foundation guidelines).
- Where a search summary contained an error that conflicts with standard neurology, it is noted in the text and corrected (for example §13.1 Weber syndrome, §17.1 seizure incidence).
- **Independent fact-check pass (see §24).** Markers added in the text: **✓ verified** = consistent with standard references known to the reviewer; **? not re-verified** = could not be confirmed and keeps its (M)/(L) rating; **corrected: was X** = value changed. The shared web-search budget was already exhausted when the fact-check ran, so no fresh searches were possible; the checks rely on reviewer knowledge `[K]` and internal consistency.

### 0.2 Tags

| Tag | Meaning |
|---|---|
| `[S#]` | Sourced from a web search result; URL in §22 |
| `[K]` | Author's own medical knowledge (standard textbooks); not re-checked in this session |
| `[E]` | Engineering estimate or game mapping, reasoning given |
| `[R1-04 §x]` | Round-one document, section x |
| (H)/(M)/(L) | Confidence that the real value lies in the stated range |

### 0.3 Conventions

- **Side words always refer to the character's own body.** "Ipsilateral" = same side as the lesion; "contralateral" = opposite side.
- **Eye angles**: horizontal positive = toward the lesion side; vertical positive = up. Squint sizes in the literature are in prism dioptres (PD): angle = atan(PD/100). 20 PD ≈ 11°, 40 PD ≈ 22°, 66 PD ≈ 33° `[E]`.
- **Strength** uses the MRC scale 0–5 (5 normal, 3 = can lift against gravity only, 0 = no contraction) `[K]`.
- **Time**: all real-world times are real. Game compression follows [R1-04 §0.3] (1× for the first 60 s, 4× for minutes, 15× for long dying).
- **Reference body**: 75 kg adult male, brain 1,300–1,400 g [R1-04 §1].

### 0.4 The five rules the resolver must obey (H)

1. **Crossing.** Everything above the pyramidal decussation (cortex, internal capsule, basal ganglia, thalamus, midbrain, pons) controls the **opposite** half of the body. The **cerebellum** controls the **same** side. A **brainstem** lesion gives **crossed signs**: cranial-nerve deficits (eye, face, tongue, swallowing) on the **same** side as the lesion, limb weakness on the **opposite** side `[K]` [S47][S53][S60]. **✓ verified** (fact-check §24). Exceptions the resolver must encode `[K] (H)`, added by fact-check: (a) **CN IV nucleus/fascicle** (midbrain, before the nerve crosses in the anterior medullary velum) weakens the **contralateral** superior oblique; (b) **CN III nucleus**: the superior-rectus subnucleus supplies the **contralateral** eye and the single levator subnucleus gives **bilateral** ptosis; (c) cerebellar outflow crosses in the lower midbrain (decussation of the superior cerebellar peduncles), so a **midbrain** lesion of that pathway (red nucleus region, Claude/Benedikt) gives **contralateral** ataxia, while a cerebellar-hemisphere lesion gives ipsilateral ataxia; (d) below the pyramidal decussation (caudal medulla/upper cervical cord) the corticospinal deficit is **ipsilateral** (hemicord / Brown-Séquard pattern); (e) lateral medulla gives crossed **sensory** loss (ipsilateral face, contralateral body), not crossed weakness.
2. **Consciousness** needs the brainstem reticular activating system plus thalami plus at least one working hemisphere. A one-sided hemisphere lesion does not by itself cause coma; bilateral hemisphere, bilateral thalamic or upper-brainstem damage does, and so does mass effect (herniation) [R1-04 §3.1] [S28].
3. **Destroyed tissue fails at once; the rest follows a clock.** Direct destruction = deficit in the same frame. Concussive/penumbral dysfunction around a track = seconds to minutes, partly recovers. Bleeding and swelling = minutes to days (§15).
4. **Destructive vs irritative lesions push the eyes opposite ways.** A destroyed hemisphere lets the eyes drift **toward** the lesion. A seizure focus drives them **away** from it. A destroyed pons makes them look **away** from the lesion (toward the paralysed limbs) (§14) [S63][S65] `[K]`.
5. **The flaccid phase is what the player sees.** Paralysis from a new brain lesion is limp for hours to weeks; spasticity appears 1–6 weeks later (§2.3) [S1][S2]. Posturing (§18) is a separate brainstem-release phenomenon and can appear within seconds. **✓ verified** (fact-check §24), with one precision: "flaccid" means **no active (voluntary or reflex) muscle drive**; passive tissue stiffness, joint-capsule limits and damping remain, so the ragdoll limb should not become frictionless `[K] (H)`.

---

## 1. Master map (summary; details in §2–§13)

"Visible at" = fraction of the region destroyed (volume) at which the deficit becomes obvious to a player; "full at" = fraction giving the complete deficit. These thresholds are `[E]` mappings of the clinical facts cited in each section.

| Region | Main loss | Body side | Onset | Visible at / full at | What the player sees |
|---|---|---|---|---|---|
| Primary motor cortex (M1) | Strength of the mapped body part (homunculus) | Contra | Immediate | 0.10 / 0.60 of a segment | Limp arm or hand, leg buckles, lower-face droop, dropped weapon |
| Premotor / SMA | Initiation of movement, bimanual/axial control, speech start (left) | Contra (SMA: global, worse contra) | Immediate | 0.20 / 0.70 | Freezes, stops using one side although not paralysed, mute or near-mute |
| Frontal eye field | Voluntary gaze to the opposite side | Eyes go toward lesion | Immediate, lasts days | 0.30 / 0.70 | Eyes and head turned toward the wounded side |
| Prefrontal (dorsolateral, orbital, medial) | Planning, inhibition, drive | Bilateral effects; unilateral subtle | Immediate | Unilateral 0.30 / 0.90; bilateral 0.20 / 0.60 | Blank stare, slowed or absent responses, perseveration, disinhibition, grasping |
| Anterior cingulate (bilateral) | Drive to move and speak | Global | Immediate | 0.30 each / 0.70 | Akinetic mutism: awake, eyes follow, no speech, no movement |
| Broca (left in ~90–95%) | Speech output | Speech; often right face/arm too | Immediate | 0.20 / 0.70 | Grunts, single words, effortful speech, moans |
| Wernicke (left) | Comprehension; fluent nonsense | Speech/comprehension | Immediate | 0.20 / 0.70 | Talks fluent nonsense, ignores commands, agitated |
| Parietal | Sensation, spatial attention, reaching | Contra (neglect mostly after right lesions) | Immediate | 0.20 / 0.70 | Ignores left space, no reaction to hits on the left, misreaches |
| Occipital (V1) | Vision in opposite half-field; both sides = blind | Contra visual field | Immediate | Field loss ∝ fraction destroyed | Bumps into things on one side; bilateral: eyes open, pupils react, no tracking |
| Temporal | Memory (medial), comprehension (left), hearing (bilateral only), upper-quadrant vision | Contra field; memory global | Immediate; seizures early; herniation minutes–hours | 0.30 / 0.80 | Repetitive questions, confusion; high seizure and herniation risk |
| Caudate / putamen / pallidum | Drive (caudate), tone/posture (lentiform) | Contra | Immediate (drive), months (dystonia) | 0.20 / 0.60 | Apathy; putaminal bleed = hemiplegia + gaze toward lesion |
| Subthalamic nucleus | Braking of proximal movement | Contra | Immediate to 48 h | 0.30 / 0.60 | Hemiballismus: violent flinging of one arm and leg |
| Thalamus | Sensation; alertness (paramedian); posture | Contra; bilateral paramedian = coma | Immediate | Unilateral 0.10 / 0.50; bilateral paramedian 0.10 / 0.30 | Drowsy/unrousable, eyes down-and-in, falls backward or to opposite side |
| Internal capsule, posterior limb | All descending motor fibres to one side | Contra, face = arm = leg | Immediate | 0.05 / 0.30 | Dense hemiplegia from a 10 mm lesion |
| Cerebellar hemisphere | Coordination | **Ipsi** | Immediate; swelling hours–days | 0.10 / 0.50 | Staggers and falls toward lesion side, overshoot, intention tremor, nystagmus |
| Vermis | Trunk balance, gait | Midline | Immediate | 0.10 / 0.50 | Cannot sit or stand unsupported, wide-based lurching, head/trunk bobbing |
| Midbrain | Eye movement (CN III, vertical gaze), consciousness, motor tracts | Crossed | Immediate | 0.02 / 0.20 | Eye down-and-out, ptosis, blown pupil + opposite hemiplegia; bilateral = coma, decerebrate |
| Pons | Horizontal gaze (CN VI, PPRF, MLF), face, motor tracts, consciousness | Crossed | Immediate | 0.02 / 0.20 | Crossed eyes, pinpoint pupils, ocular bobbing, locked-in |
| Medulla | Breathing, BP, swallowing, voice, tongue | Crossed; bilateral = apnoea | Immediate | 0.02 / 0.15 | Gurgling, choking, hoarse voice, hiccups, ipsilateral Horner; apnoea [R1-04 §2] |

Visual/behavioural summary for the whole map:
- One-sided cerebral damage: the body fails on the **other** side, the eyes turn **toward** the wound (unless seizing).
- Cerebellar damage: the body fails on the **same** side; the character lurches toward the wound.
- Brainstem damage: eye and face problems on the wound side, limb paralysis on the other side, or everything at once.

---

## 2. Primary motor cortex (M1, precentral gyrus)

### 2.1 Anatomy and the homunculus map

- M1 is the precentral gyrus, a strip ~10–15 mm wide (front to back) running from the top of the medial surface (paracentral lobule) down the lateral convexity to the Sylvian fissure `[K] (H)`.
- Somatotopy runs from medial to lateral: foot, lower leg, knee, thigh, hip, trunk, shoulder, arm, elbow, wrist, fingers, thumb, neck, brow, eyelid, face, lips, jaw, tongue, pharynx [S35]. Representations overlap considerably (gradual progression, not sharp borders) [S35].
- **Hand knob**: an omega-shaped bend of the precentral gyrus; ~3.5 cm from the midline and 1.5–2 cm deep into the central sulcus [S34]; ~31 mm horizontally from the Cz scalp point [S34]. Electrostimulation MNI coordinates: wrist (27, −25, 70), finger extension (30, −26, 69), thumb/finger flexion (34–36, −11 to −22, 65–66) [S35]. **Fact-check: the omega shape and the medial-to-lateral somatotopy are ✓ verified; the individual numbers (3.5 cm, 1.5–2 cm, 31 mm, MNI triplets) could not be re-searched and stay (M).** Cross-check `[K] (M)`: meta-analytic fMRI centres of the M1 hand area lie near MNI x = ±35–40, y ≈ −20, z ≈ 55–60, i.e. slightly lower and more lateral than the electrostimulation wrist point; both are within the 30–40 mm lateral band used below. The "31 mm from Cz" is a horizontal (not along-scalp) distance; the TMS hand hotspot on the scalp is usually ~4–6 cm lateral to Cz.
- Face lies below the hand, tongue and larynx lowest near the Sylvian fissure; leg and foot mostly on the medial surface facing the other hemisphere `[K] (H)`. Blood supply matches: the **middle cerebral artery** territory holds face and arm; the **anterior cerebral artery** territory holds the leg [S6].

**Game mapping** `[E]`: parameterise the strip by `s` = 0 at the midline (top of the head) to 1 at the Sylvian fissure (measured along the cortical surface). Put the medial-surface part (foot, leg) at `s` < 0.

| Segment | `s` range | Notes |
|---|---|---|
| Foot, toes | −0.30 to −0.05 | On the medial surface; a parasagittal track or a midline (sagittal-sinus) blow hits both legs |
| Leg, hip | −0.05 to 0.15 | |
| Trunk | 0.15 to 0.25 | Trunk muscles are bilaterally represented: one-sided loss is mild `[K]` |
| Shoulder, arm | 0.25 to 0.40 | |
| Hand, fingers, thumb | 0.40 to 0.62 | Hand knob; largest segment |
| Neck, brow, eyelid | 0.62 to 0.68 | Upper face is bilaterally represented: little visible loss |
| Lower face, lips, jaw | 0.68 to 0.85 | |
| Tongue, pharynx, larynx | 0.85 to 1.00 | Bilateral representation: one side = mild dysarthria only |

### 2.2 What is lost

- **Contralateral weakness of the mapped part.** Destruction of a whole segment gives paralysis (MRC 0–1) of that part; a partial lesion gives weakness (MRC 2–4) `[K] (H)`.
- Distal (hand, fingers) is affected more than proximal (shoulder), because proximal and axial muscles also receive ipsilateral and brainstem (reticulospinal) control `[K] (H)`.
- A small cortical lesion can cause an isolated hand paralysis that looks like a nerve injury ("pseudoperipheral palsy"); this is < 1% of hospitalised ischaemic strokes and reflexes are often normal [S33].
- **Face**: a cortical or capsular lesion weakens the **lower** face on the opposite side; the forehead and eye closure are largely spared because the upper face gets input from both hemispheres [S36]. In severe acute strokes upper-face weakness is also common, but milder [S36]. Emotional smiling may still move the weak side [S36]. **✓ verified** (standard upper-motor-neuron facial pattern `[K] (H)`).
- **Tongue**: pushed out, it deviates toward the weak side (contralateral to the lesion) `[K] (M)`.
- Severity scales with how much of the corticospinal output is destroyed: in stroke, motor outcome is inversely related to the fraction of the corticospinal tract hit by the lesion ("lesion load") [S32]; above ~7 cc of weighted tract lesion load, all patients had poor arm function at 3 months [S32].

### 2.3 Timing: flaccid first, spastic later

| Phase | Real time | Signs | Source |
|---|---|---|---|
| Destruction | 0 s | Loss of voluntary force in the same frame | `[K] (H)` |
| Flaccid ("cerebral shock") | Hours to 1–3 weeks | Limb limp, no resistance to passive movement, reflexes reduced or normal; Babinski sign may appear within hours | [S3] `[K] (M)` |
| Rising tone | Days to weeks | Hyperreflexia; spasticity in 24.5% within 2 weeks; spasticity usually appears between 1 and 6 weeks | [S1][S2] ✓ verified |
| Spastic peak | 1–3 months | Flexed arm, extended leg ("Wernicke-Mann" posture), clonus | [S1] |

- Overall spasticity after a first stroke with paresis: 39.5% [S1]. A lesion of the internal capsule or brainstem, severe weakness or early hyperreflexia predicts it [S1]. **✓ verified** against the reviewer's knowledge of the primary studies `[K] (M)`: the 24.5% figure matches Wissel et al. 2010 (*J Neurol*, prospective, first-ever stroke; measured at about 6 ± 3 days, then 26.7% at 6 weeks and 21.7% at 16 weeks), 39.5% matches the pooled prevalence in patients **with paresis** in Zeng et al. 2021 (*Front Neurol* meta-analysis; 25.3% in all stroke patients), and Sommerfeld 2004 [S2] found 19% at 3 months. Note that a minority show measurably raised tone within the **first week**, so "flaccid for 1–3 weeks" is the typical, not universal, course.
- **Game rule** `[E]`: within any playable time frame (minutes to a few hours) a motor-cortex or capsule lesion is **flaccid**. Spastic posture should only appear if the game offers a "days later" time skip.

### 2.4 What it looks like from outside

- **Arm**: segment severity > 0.8 → the arm drops as dead weight within 0.1–0.3 s and swings passively with body movement. Severity 0.4–0.8 → the character can lift the arm but it drifts down and the palm turns downward (pronator drift) within 3–10 s; clinicians hold the arm out for 10 s (NIHSS) and a drift within 20 s is abnormal [S37] `[K]`.
- **Hand**: hand-segment severity > 0.7 → fingers open, **held weapon drops** within 0.1–0.5 s `[E]`. At 0.3–0.7 the grip weakens and fine movements (trigger, fumbling) fail.
- **Leg**: leg severity > 0.6 → the knee buckles as soon as weight comes onto it (0.2–0.6 s after the hit if standing) and the character falls **toward the paralysed side** `[K]`/`[E]`. The non-paralysed arm reaches out to break the fall if the character is conscious.
- **Face**: the mouth corner on the weak side sags 2–6 mm, the nasolabial fold flattens, saliva runs from that corner, the cheek puffs out on expiration; the eye still closes and the forehead still wrinkles `[K]`/`[E]` [S36].
- **Speech**: slurred (dysarthria) if the face/tongue segment is hit; true language loss only with left-hemisphere language areas (§5).
- A parasagittal track (near the top of the head, both hemispheres) hits both leg areas: **both legs give way** while the arms still work `[K] (M)`.

### 2.5 Simulation parameters: M1

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `m1_strip_width` | 10–15 | mm | Anteroposterior thickness of precentral gyrus hit volume | [K] (M) |
| `m1_segment_s_ranges` | table §2.1 | — | Medial surface negative `s` | [E] on [S34][S35] |
| `hand_knob_lateral` | 35 (30–40) | mm from midline | 15–20 mm deep | [S34] (M) — fact-check: confidence lowered from (H); numbers not re-verified, band consistent with fMRI hand-area x ≈ 35–40 mm `[K]` |
| `m1_visible_at` / `m1_full_at` | 0.10 / 0.60 | fraction of segment destroyed | smoothstep between | [E] |
| `mrc_from_severity` | 5 − 5·sev (round down) | MRC | sev 0.5 → MRC 3 | [E] |
| `joint_drive_scale` | (1 − sev)^1.5 | × max drive | Applied to the affected side's PhysicalBone3D motor targets | [E] |
| `ipsi_proximal_sparing` | 0.3 | fraction of proximal/axial strength kept at sev = 1 | Shoulder shrug, hip still partly work | [E] on [K] |
| `upper_face_sparing` | 0.7 | fraction of forehead/eyelid strength kept | Severe cases lower it to 0.4 | [S36] (M), [E] |
| `arm_drift_time` | 3–10 | s | For sev 0.4–0.8 | [S37] [E] |
| `weapon_drop_threshold` | hand sev > 0.7 | — | Drop delay 0.1–0.5 s | [E] |
| `leg_buckle_threshold` | leg sev > 0.6 | — | Buckle 0.2–0.6 s after load | [E] |
| `flaccid_duration` | 1–3 weeks (never shorter in game) | — | Active drive (voluntary + reflex tone) stays zero on the affected side; **keep passive joint stiffness/damping and joint limits** (fact-check: flaccid ≠ frictionless) ✓ verified | [S3] (M) |
| `flaccid_passive_damping` | 0.6–0.9 × the damping of a relaxed (not actively held) healthy limb; 0 active drive | — | Added by fact-check; hypotonia lowers resistance only modestly below a relaxed limb; avoids "rubber-hose" limbs | [E] |
| `spasticity_onset` | 1–6 weeks; 24.5% by 2 weeks | — | Only for time skips | [S1][S2] (M) |

### Visual/behavioural checklist: M1
- One arm drops like a dead weight or slowly sinks and turns palm-down; the hand opens and the weapon falls.
- The leg on the same side folds at the knee and the character goes down toward that side, catching itself with the good arm.
- The lower face on that side hangs; drool runs from that mouth corner; the forehead and blink are normal.
- A hit high near the top midline takes out one or both legs while the arms keep working.
- Audio: slurred speech if the face area is hit; otherwise speech is normal (motor cortex is not language).

---

## 3. Premotor cortex, supplementary motor area (SMA), frontal eye field (FEF)

### 3.1 Supplementary motor area (medial frontal, in front of the leg area)

- **SMA syndrome**: global **akinesia** (poverty of movement) worse on the opposite side, with normal or reduced reflexes and normal tone; **strength can be preserved** [S4]. With a left (dominant) lesion, **mutism** or near-mutism; also apraxia and neglect of the contralateral limbs [S4][S5].
- Severity depends on location more than volume; lesions closer to premotor cortex give worse akinesia; cingulate involvement gives mutism [S4].
- Recovery pattern: **speech first, then leg, then arm** [S4]. About 90% recover fully in 1 week to 6 months; most within 2 months [S4][S5].
- Onset in surgical series ranges from immediate to a few days after the lesion [S4]; for a destructive wound use immediate `[E]`.
- Acute SMA infarction can cause isolated **astasia** (inability to stand) without weakness [S116] (title-level evidence; L).

### 3.2 Premotor cortex (lateral, in front of the arm/face strip)

- Mild weakness of **proximal** muscles (shoulder, hip) on the opposite side, clumsy "limb-kinetic" apraxia (movements coarse, poorly sequenced), grasp reflex with medial involvement `[K] (M)`.
- The left inferior premotor/Broca region overlaps with speech output (§5) `[K]`.

### 3.3 Frontal eye field (caudal middle frontal gyrus, just in front of the precentral sulcus)

- Location note (fact-check `[K] (M)`): in human functional imaging the FEF sits in the **precentral sulcus at its junction with the superior frontal sulcus** (classic texts: caudal middle frontal gyrus, Brodmann 8); for the hit-volume use the precentral-sulcus/SFS junction, ~2–4 cm³ per side.
- Destruction lets the eyes (and often the head) deviate **toward the lesion**, because the intact FEF pushes them over [S64]. The eyes can still be moved by reflex (doll's-eye manoeuvre) because the brainstem is intact `[K] (H)`. **✓ verified** (direction).
- The deviation lasts **days to about a week** and then fades as other pathways take over; afterwards saccades toward the opposite side stay slow and hypometric [S64]. **✓ verified** as typical course `[K] (M)`; large right-hemisphere lesions with neglect can keep a rightward gaze/head bias for weeks.
- In stroke series, forced conjugate eye deviation was found in 26.7% and partial in 6% of 116 patients [S63]; another series found 43% with conjugate deviation plus 33% with a lone abducting eye [S63]. An average deviation > 14–15° is associated with large middle-cerebral-territory infarcts [S63]. **? not re-verified by fact-check** (no search available); the overall incidence (~20–35% of acute hemispheric strokes) is consistent with the reviewer's knowledge `[K] (M)`; keep the exact percentages and the 14–15° cut-off at (M).
- Exception: a frontal haemorrhage can sometimes push the eyes the "wrong way" (away from the lesion) [S64].

### 3.4 Simulation parameters: SMA, premotor, FEF

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `sma_akinesia_contra` | 0.5–0.9 × voluntary movement rate | — | Strength kept; movement initiation drops | [S4] (M), [E] |
| `sma_akinesia_ipsi` | 0.1–0.3 | — | Global, milder on same side | [S4] (M), [E] |
| `sma_mutism_prob_left` | 0.6 | p | If left SMA or cingulate involved | [S4] (M), [E] |
| `sma_recovery` | days to weeks | — | Speech first, then leg, then arm | [S4] (H) |
| `premotor_proximal_weakness` | MRC 4 | — | Contra shoulder and hip | [K] (M) |
| `fef_gaze_bias` | 15–40 toward lesion (default 25) | ° | Head turns with it, 10–30° | [S63] (M), [E] |
| `fef_bias_duration` | 2–7 | days | Game: constant | [S64] (M) |
| `fef_oculocephalic_override` | true | bool | Doll's eyes still move the eyes past midline | [K] (H) |

### Visual/behavioural checklist: SMA, premotor, FEF
- The character stops moving one side although it is not paralysed; if provoked strongly (pain) that side moves normally.
- It may stand frozen, unable to start walking, or go silent while clearly awake.
- Eyes and head turn toward the wounded side of the brain and stay there; the character does not look toward the other side on its own.

---

## 4. Prefrontal cortex (dorsolateral, orbitofrontal, medial) and anterior cingulate

### 4.1 What is lost

| Sub-region | Loss | Source |
|---|---|---|
| Dorsolateral | Planning, working memory, set-shifting; **perseveration** (repeats the same action or word), impersistence, slowed responses | [S7][S8] |
| Orbitofrontal / ventromedial | **Disinhibition**, impulsivity, socially inappropriate behaviour, emotional lability, euphoria (right side more) | [S11][S7] |
| Medial frontal / anterior cingulate | **Apathy, abulia** (loss of will), reduced spontaneous speech and movement; bilateral lesions give **akinetic mutism** | [S7][S9] |
| Frontal base | Loss of smell (olfactory tracts) on the wounded side(s) | `[K] (H)` |

- The same patient can show apathy and inertia together with distractibility, **utilization behaviour** (picks up and uses objects that are within reach, even when inappropriate), **imitation** of the examiner's gestures, echolalia and a **grasp reflex** [S7][S8]. Other "frontal release" reflexes: snout, sucking, rooting, palmomental, glabellar tap [S8].
- **Akinetic mutism**: the patient is awake, eyes open and **may follow the examiner**, but makes no speech, no voluntary movement and no emotional response; incontinent. It usually follows bilateral anterior cingulate/medial frontal damage (bilateral ACA territory, masses, trauma) [S9].
- Caudate damage (the "frontal" part of the basal ganglia) gives abulia in 28% and disinhibition in 11% of focal lesions [S10].
- **A unilateral prefrontal wound may cause no visible deficit** apart from concussion; retained capacity to act after low-energy frontal shots is documented [R1-01 §6] [R1-04 §3.2]. Bihemispheric frontal tracks carry lower mortality than other bihemispheric tracks (bifrontal is excluded from the bihemispheric risk factor) [S95].
- In the confused period after a coma (post-traumatic amnesia), disinhibition and agitation are marked regardless of lesion site `[K] (M)`.

### 4.2 Onset

- Immediate after destruction. In blunt injury the frontal and temporal poles are the usual contusion sites whatever the impact side (the brain strikes the anterior and middle cranial fossae; an occipital blow gives frontal/temporal **contrecoup** contusions) `[K] (H)`. Contusions expand over 12–24 h (§15.4).

### 4.3 Simulation parameters: prefrontal / cingulate

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `pfc_unilateral_visible_at` | 0.30 | fraction | Below this, no visible change except concussion | [E] |
| `pfc_bilateral_visible_at` | 0.20 each side | fraction | | [E] |
| `response_latency_add` | 1–10 (sev-scaled) | s | Delay before reacting to player, sound or pain | [E] on [S7] |
| `perseveration_prob` | 0.2 + 0.5·sev | p per action choice | Repeat the last action or vocal line | [E] on [S7][S8] |
| `utilization_prob` | 0.1–0.4 | p | Picks up nearby objects and handles them | [E] on [S8] |
| `grasp_reflex` | true if medial frontal sev > 0.3 | bool | Hand closes on anything touching the palm, including the player's hand/weapon | [S8] (M), [E] |
| `disinhibition` | orbitofrontal sev | 0–1 | Laughs, swears, walks toward danger, ignores threat | [S11] (M), [E] |
| `akinetic_mutism` | bilateral ACA/medial frontal sev > 0.5 | bool | Eyes open, tracking; no voluntary speech or movement; withdrawal to pain may remain | [S9] (M) |
| `anosmia_side` | olfactory groove hit | L/R/both | No visible effect; flavour for smell-based AI | [K] |

### Visual/behavioural checklist: prefrontal
- Blank, "frozen" stare; long pauses before any response; eyes may still follow the player.
- Repeats the same movement (keeps trying the same door handle, keeps saying the same word).
- Grabs and holds whatever is put into its hand; fumbles with objects lying nearby.
- Inappropriate calm, laughter or crude remarks despite a horrific wound; no fear.
- Bilateral medial frontal: sits or lies awake, silent and motionless, eyes open, following movement.

---
## 5. Language areas and the vocal system

### 5.1 Anatomy and dominance

- **Broca's area**: pars opercularis and triangularis of the inferior frontal gyrus (Brodmann 44/45) of the dominant hemisphere [S14]. Real Broca's aphasia usually also involves the insula, underlying white matter and basal ganglia; damage to Broca's area alone gives milder, often transient deficits [S13] `[K]`.
- **Wernicke's area**: posterior third of the superior temporal gyrus (Brodmann 22) behind Heschl's gyrus, dominant hemisphere [S12][S14].
- **Dominance**: the left hemisphere is language-dominant in ~95% of right-handers and ~70% of left-handers [S14]. **Game default**: 90% of generated characters left-dominant `[E]`.
- Aphasia occurs in ~30% of ischaemic strokes [S13]. Non-fluent (Broca-type) aphasia is common after left-hemisphere **missile** wounds but rare after closed head injury [S15].

### 5.2 Vocal states for the game

| Vocal state | Cause | What is heard | Comprehension | Tag |
|---|---|---|---|---|
| `NORMAL` | — | Normal speech | Normal | — |
| `DYSARTHRIC_UMN` | M1 face/tongue, capsule genu | Slow, slurred, strained; words intact | Normal | [K] (H) |
| `DYSARTHRIC_CEREBELLAR` | Cerebellum | "Scanning": syllables separated, equal or excess stress, irregular loudness, jerky and explosive | Normal | [S16] (H) |
| `DYSARTHRIC_BULBAR` | Pons/medulla (CN VII, IX, X, XII) | Nasal, breathy, hoarse, weak; wet gurgle; cannot cough effectively | Normal | [S59][S58] `[K]` (M) |
| `NONFLUENT` | Broca + surroundings | Few effortful words, telegraphic, grunts; automatic phrases and swearing often preserved | Relatively preserved | [S12][S13] `[K]` (H) |
| `JARGON` | Wernicke | Fluent, normal rhythm, meaningless words and neologisms; does not realise it | Poor; does not obey | [S12] (H) |
| `GLOBAL` | Large left MCA territory | Mute or one repeated syllable/stereotypy | Nil | `[K]` (H) |
| `MUTE_AKINETIC` | Bilateral medial frontal/cingulate, SMA (left) | Silence; awake | Variable | [S4][S9] (M) |
| `MOAN_ONLY` | Stupor/coma (GCS V2) | Moans and groans only, especially to pain | Nil | [S93] (H) |
| `SILENT` | Coma GCS V1, apnoea, locked-in | Nothing (locked-in: nothing despite full awareness) | Locked-in: normal | [S56] (H) |

- **Pain vocalisation survives aphasia.** Screams, moans and cries are generated by brainstem and limbic circuits and are present in aphasic, frontal and even stuporous patients (that is what GCS V2 records) `[K] (H)`. A left-hemisphere wound therefore silences words, not screaming.
- **Myth guard (fact-check) `[K] (H)`:** "survives" means the *capacity* to vocalise is kept, not that a wounded person screams. Many people who are shot or stabbed make no sound, grunt, gasp, or say a short phrase ("I'm hit"); pain is often delayed or not felt in the first seconds to minutes; anyone knocked unconscious by a head wound is silent (GCS V1) apart from snoring, gurgling or agonal gasps. Drive screaming from a probability that depends on consciousness, airway and injury type (see `06_sounds_voice_face.md`), never as a default reaction.
- Persistent mutism after trauma is associated with bilateral hemisphere damage, especially frontal, or with upper-brainstem involvement; posterior fossa penetration can cause temporary mutism with intact cognition [S15 search summary] (M).

### 5.3 Simulation parameters: language

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `left_dominant_prob` | 0.90 | p | Per generated character | [S14] (H), [E] |
| `broca_visible_at` / `full_at` | 0.20 / 0.70 | fraction | Include insula and subjacent white matter in the region volume | [E] on [S13] |
| `wernicke_visible_at` / `full_at` | 0.20 / 0.70 | fraction | | [E] |
| `aphasia_obeys_commands` | Broca 0.7, Wernicke 0.1, global 0 | p | Affects surrender/compliance AI | [E] on [S12] |
| `automatic_speech_kept` | true for NONFLUENT | bool | Swear words, "no", "yes", counting | [K] (M) |
| `pain_vocal_kept` | true unless GCS V1, apnoea or locked-in | bool | | [K] (H) |

### Visual/behavioural checklist: language
- Left-side head wound: the character is awake and screaming in pain but cannot form words, or strings nonsense together and does not react to commands.
- The right side of the face droops and the right arm is weak in most non-fluent cases.
- Swearing or a single repeated word may be the only speech left.
- Brainstem wound: voice turns hoarse, nasal and wet; coughing is weak; gurgling.

---

## 6. Parietal lobe

### 6.1 What is lost

| Deficit | Side and lesion | Numbers | Appearance | Source |
|---|---|---|---|---|
| **Cortical sensory loss** (astereognosis, two-point, position sense) | Contra; postcentral gyrus/superior parietal | Dense hemianaesthesia points to thalamus rather than cortex | Cannot use the hand well without looking; drops things; weak response to touch | [S21] |
| **Hemispatial neglect** | Contra space; right lesions far more often | Acute: 43% of right-hemisphere vs 20% of left-hemisphere strokes; at 3 months 17% vs 5% | Ignores everything on the left: people, threats, sounds, its own left limbs; head and eyes turned right | [S17][S18] ✓ verified (Ringman 2004 figures) |
| **Anosognosia for hemiplegia** | Right hemisphere | ~32% very acute; 18% in the first week; 5% at 6 months | Denies or ignores the paralysis; tries to stand on a paralysed leg | [S19] ✓ verified; fact-check: these are rates **among right-hemisphere stroke patients**, from the longitudinal study of Vocat et al. 2010 (*Brain*), which [S19] draws on `[K] (M)` |
| **Somatoparaphrenia** | Right hemisphere; with neglect | Rare | Claims the paralysed arm belongs to someone else | [S19] |
| **Pusher syndrome** | Right > left (≈17% vs ≈10% of hemiparetic patients in one series); parietal, insula, thalamus | 10.4% of acute stroke with hemiparesis overall | Pushes with the good arm and leg **toward the paralysed side** and resists correction; falls that way | [S20] |
| **Optic ataxia** | Posterior parietal, contra hemifield/hand | — | Misreaches toward objects despite seeing them | [S21 search summary] |
| **Apraxia** (ideomotor) | Left parietal | — | Cannot perform learned gestures on command; automatic use may survive | `[K]` (H) |
| **Inferior quadrantanopia** | Contra lower visual quadrant (upper optic radiation) | — | Trips over things below and to one side | `[K]` (H) |
| **Balint syndrome** | Bilateral posterior parietal | — | Sees one object at a time, cannot direct gaze, misreaches | [S21 search summary] |

### 6.2 Simulation parameters: parietal

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `neglect_prob_right_lesion` | 0.43 (if right parietal sev > 0.3) | p | | [S17] (M) |
| `neglect_prob_left_lesion` | 0.20 | p | Milder form | [S17] (M) |
| `neglect_head_eye_bias` | 20–40 toward lesion side | ° | Head turned, gaze deviated | [E] on [K] |
| `neglect_stimulus_gain_contra` | 0.1–0.4 | × perception | Sounds, damage and visual targets on the neglected side | [E] |
| `anosognosia_prob_right` | 0.32 | p | Character keeps trying to use the paralysed side | [S19] (M) |
| `pusher_prob` | right 0.17, left 0.10 (if hemiparetic) | p | Active push toward paretic side | [S20] (L–M) |
| `cortical_sensory_loss` | contra, sev-scaled | 0–1 | Grip slips unless looking; flinch to touch on that side reduced | [S21] (M), [E] |
| `optic_ataxia_reach_error` | 5–20 | cm | Reaching error into contralateral field | [E] |

### Visual/behavioural checklist: parietal
- The character keeps its head and eyes turned to the right, does not react when shot or approached from the left, and does not look at its own left arm.
- It tries to stand and walk on a paralysed left leg as if nothing were wrong, and falls.
- A "pusher" shoves itself over toward its paralysed side with its good arm and leg.
- Reaching for a weapon or a handhold misses by a hand's width.

---

## 7. Occipital lobe

### 7.1 What is lost

- **Unilateral V1 or optic radiation**: **contralateral homonymous hemianopia** (the same half of the visual field is lost in both eyes). With occipital infarcts the centre (2–10° around fixation) is often spared ("macular sparing") because of dual blood supply to the occipital pole [S24]. The patient usually knows about it and compensates by turning the head [S24] `[K]`.
- Retinotopy for the game `[K] (H)`: the **occipital pole** holds central vision; the **anterior calcarine** cortex holds the periphery; **above** the calcarine fissure = lower visual field; **below** = upper field. A track through only the upper bank of the right calcarine cortex removes the lower-left quadrant.
- **Bilateral**: **cortical blindness**. Vision is lost but **pupil light reflexes are normal**, the fundus is normal and eye movements are preserved; the blink to a sudden threat (menace reflex) is lost [S22]. Some patients deny being blind and confabulate (Anton syndrome) [S22][S23]. Causes include PCA infarcts, trauma and hypoxia [S22].

### 7.2 Simulation parameters: occipital

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `vision_field_mask` | per quadrant, per eye | 0–1 | Derived from the retinotopic sub-regions hit | [K] (H), [E] |
| `macular_sparing_deg` | 2–10 (default 5) | ° radius | Only if the occipital pole is not hit | [S24] (M) |
| `hemianopia_head_comp` | 10–25 toward blind side | ° | Only when conscious and not neglecting | [E] on [K] |
| `cortical_blind_pupils` | normal, reactive | — | Eye shader keeps normal pupil response | [S22] (H) |
| `cortical_blind_menace_blink` | false | bool | No blink when something flies at the face | [S22] (H) |
| `cortical_blind_fixation` | false | bool | Eyes open, conjugate, slowly wandering, do not lock onto targets | [S22] `[K]` (M) |
| `anton_prob` | 0.1–0.2 | p | Acts as if sighted, walks into walls | [E] on [S22] |

### Visual/behavioural checklist: occipital
- One-sided: the character bumps into doorframes and objects on one side and turns its head to scan; it does not see the player coming from that side.
- Both sides: eyes open and moving, pupils constrict normally to a torch, but the eyes do not lock onto the player; no blink when something is thrust at the face; arms held out, groping; may insist it can see.

---

## 8. Temporal lobe

### 8.1 What is lost

| Sub-region | Loss | Side | Source |
|---|---|---|---|
| Lateral (superior temporal gyrus, left) | Comprehension, fluent jargon (§5) | Language | [S12] |
| Auditory cortex | One side: little hearing loss (both ears project to both sides). Both sides: cortical deafness | — | `[K]` (H) |
| Meyer's loop (optic radiation) | **Upper** quadrantanopia, contralateral ("pie in the sky") | Contra field | `[K]` (H) |
| Hippocampus / medial temporal | **Anterograde amnesia** (cannot form new memories), repetitive questioning; severe only if bilateral | Global | `[K]` (H) |
| Amygdala | Reduced fear and threat responses; bilateral: placidity, oral exploration (Klüver-Bucy), rare | Global | `[K]` (M) |
| Whole temporal lobe | Highest seizure risk of any site; temporal contusions and haematomas push the uncus into the tentorial gap → **uncal herniation** (§15.6) | — | [S90] `[K]` (H) |

- Temporal and frontal poles are the commonest contusion sites in blunt injury (§4.2) `[K] (H)`. Temporal squamous fractures tear the middle meningeal artery; about 75% of adult epidural haematomas are temporal [S78].

### 8.2 Simulation parameters: temporal

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `temporal_visible_at` / `full_at` | 0.30 / 0.80 | fraction | Unilateral non-dominant: few visible signs | [E] |
| `amnesia_bilateral_hippo` | sev > 0.5 both sides | bool | Repeats questions every 30–120 s | [E] on [K] |
| `upper_quadrant_loss` | Meyer's loop hit | mask | | [K] (H) |
| `temporal_immediate_seizure_mult` | 1.5 | × base cortical seizure p | | [E] on [K] |
| `uncal_herniation_driver` | temporal mass volume | mL | Feeds §15.6 | [E] |

### Visual/behavioural checklist: temporal
- Repeats the same question or phrase; does not remember what happened seconds ago.
- Right-sided temporal wound: often no visible deficit at first, then a seizure or a slowly dilating right pupil minutes to hours later.

---

## 9. Basal ganglia

### 9.1 Putamen / lentiform nucleus

- A putaminal haemorrhage (or a track through putamen and adjacent internal capsule) gives **rapidly progressing contralateral hemiplegia**, milder contralateral sensory loss, and **conjugate gaze deviation toward the side of the haematoma** [S27]. Dominant side: aphasia and visual field loss as well [S27].
- Lentiform lesions rarely cause abulia (10%) but commonly **dystonia** (49%; 63% if putamen involved) [S10]. Dystonia appears late: average **9.5 months** after the lesion, typically as the paresis resolves [S10 search summary] — out of game time.

### 9.2 Caudate

- Abulia 28%, sometimes alternating with disinhibition (11%) [S10]. Hemiballismus-like hyperkinesia is also reported with caudate strokes [S26 search summary].

### 9.3 Subthalamic nucleus (STN): hemiballismus

- STN destruction releases the motor thalamus and produces **hemiballismus**: abrupt, violent, **flinging, large-amplitude proximal movements of the contralateral arm and leg** (sometimes neck and trunk) [S25][S26]. Fully developed, the movements are nearly continuous: swinging, throwing, rolling, flailing [S26].
- EMG: irregular bursts of **200–1,000 ms**, synchronous in agonist and antagonist [S26].
- It can injure the patient and, untreated, can kill through exhaustion [S26]. Vascular cases are usually self-limiting over weeks (6–8 weeks) [S25].
- Infarcts of striatum, thalamus, cortex and subcortical white matter can also cause it [S25]. The STN is tiny (~10 × 6 × 4 mm, ~0.15–0.2 cm³) `[K] (M)`, so a direct ballistic hit usually destroys surrounding structures too (internal capsule, thalamus). **Game use**: rare flourish.

### 9.4 Simulation parameters: basal ganglia

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `putamen_hemiplegia` | via adjacent capsule involvement | — | Model putamen + capsule jointly | [S27] (H) |
| `putamen_gaze_toward_lesion` | 15–30 | ° | | [S27] (M), [E] |
| `caudate_abulia_prob` | 0.28 | p | | [S10] (M) |
| `stn_ballism_prob` | 0.3 if STN sev > 0.3 and capsule sev < 0.5 (paralysed limbs cannot fling) | p | | [E] on [S25] |
| `ballism_amplitude` | shoulder 40–120, hip 20–60 | ° per excursion | Proximal, rotatory, throwing | [E] on [S26] |
| `ballism_burst` | 0.2–1.0 | s | Irregular; 0.5–2 movements/s | [S26] (M), [E] |
| `ballism_onset` | 0 s – 48 h | — | Default: minutes after the lesion | [E] on [K] |
| `dystonia_onset` | ~9.5 months | — | Out of scope | [S10] (M) |

### Visual/behavioural checklist: basal ganglia
- Putamen/capsule: one-sided paralysis plus eyes turned toward the wounded side.
- STN (rare): one arm and leg thrash and fling violently and irregularly, hitting the floor and walls; this does not stop when the character lies down.
- Caudate: apathetic, slow to answer, may suddenly become inappropriate.

---

## 10. Thalamus

### 10.1 What is lost

| Lesion | Deficit | Eye signs | Source |
|---|---|---|---|
| Lateral (VPL/VPM, sensory relay) | **Dense contralateral hemisensory loss**; hemiparesis if the adjacent internal capsule is hit | — | [S21][S27] |
| Thalamic haemorrhage (any large) | Hemiplegia, hemisensory loss, decreased consciousness | **Down and in** ("peering at the nose"), small (miotic) pupils, occasional **wrong-way eyes** (gaze away from the lesion, a poor prognostic sign) | [S27][S29] |
| Superoposterolateral (VL/VPL, CM) | **Thalamic astasia**: alert, near-normal strength, but cannot stand and some cannot sit; **fall backward or toward the side opposite the lesion**; recovers in days to weeks | — | [S30] |
| Paramedian (one side) | Drowsiness, memory loss, vertical gaze weakness | Vertical gaze palsy | [S28] |
| **Bilateral paramedian** (artery of Percheron) | Triad: **stupor, hypersomnolence or coma**; **vertical gaze palsy**; memory/behaviour change. Can present as akinetic mutism | Vertical gaze palsy; pupil abnormalities if the midbrain is involved | [S28] |

- Deep midline tracks (third ventricle, diencephalon) carry very high mortality in civilian gunshot series (100% for diencephalic, transventricular and posterior-fossa tracks in one series) [S95].

### 10.2 Simulation parameters: thalamus

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `thal_volume` | 6–8 each | cm³ | Hit volume per side | [K] (M) |
| `thal_sensory_loss` | contra, sev-scaled | 0–1 | | [S21] (M) |
| `thal_astasia_prob` | 0.3 if lateral thalamus sev > 0.2 | p | Falls backward or contralateral | [S30] (M), [E] |
| `thal_eyes_down_in` | 10–25 down, 5–15 in (each eye) | ° | Large thalamic bleed or track | [S27] (M), [E] |
| `thal_pupil` | 2–3, reactive | mm | | [S27] (M), [K] |
| `wrong_way_prob` | 0.1–0.2 | p | Gaze 10–25° away from lesion | [S29] (L), [E] |
| `bilat_paramedian_LOC` | GCS 3–8 if both sides sev > 0.2 | — | Hypersomnolent: brief eye-opening to loud voice or pain, then back to sleep | [S28] (M), [E] |

### Visual/behavioural checklist: thalamus
- Eyes pointing down toward the tip of the nose, pupils small; the character is drowsy or cannot be woken.
- Or: awake and strong but unable to stand, repeatedly toppling backward or away from the wounded side.
- Both thalami: sleeps through anything but the strongest pain, then drifts off again; cannot look up or down.

---

## 11. Internal capsule and deep white matter

- The **posterior limb** carries the corticospinal and corticobulbar fibres for the whole opposite half of the body, packed into a band ~10–15 mm wide `[K] (M)`. A lacune of **2–20 mm** here causes **pure motor hemiparesis/hemiplegia affecting face, arm and leg about equally** [S31]. Pure motor stroke is the commonest lacunar syndrome (33–50%) [S31]. **✓ verified** `[K] (H)` (Fisher's classic description; Medscape gives the same 2–20 mm size and 33–50% share; clinical series of pure motor stroke put it at up to ~45–57% of lacunar syndromes, so 33–57% is the honest range). Fact-check nuance: incomplete forms (face + arm, or arm + leg) are common, and the same syndrome also comes from the **basis pontis** and corona radiata, so "face = arm = leg" is the typical, not the only, pattern.
- Genu: face and tongue (corticobulbar) fibres; anterior limb: frontothalamic fibres (abulia, confusion); retrolenticular part: optic radiation (hemianopia) `[K] (H)`.
- Corticospinal fibres move toward the posterior half of the posterior limb as they descend [S31].
- This is the most "tissue-efficient" place to paralyse half the body: a ~10 mm destruction gives dense hemiplegia, where the cortex needs a whole gyral strip `[E]` on [S31][S32].
- **Corpus callosum** (midline track above the ventricles): disconnection signs (the left hand cannot follow verbal commands; intermanual conflict, "alien hand") that are hard to show in a game; high association with transventricular tracks, which carry high mortality [S95] `[K] (M)`.
- **Diffuse axonal injury** (blunt rotational injury, and remote injury around high-energy tracks): loss of consciousness from the moment of injury lasting > 6 h; grade 3 (corpus callosum + brainstem) with coma and decerebrate posturing; ~60% of severe DAI die and ~20% remain vegetative [S114].

### Simulation parameters: capsule and white matter

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `ic_post_width` | 10–15 | mm | Hit volume | [K] (M) |
| `ic_post_visible_at` / `full_at` | 0.05 / 0.30 | fraction | 2–3 mm destroyed = weakness, ~10 mm = hemiplegia | [E] on [S31] |
| `ic_face_arm_leg_ratio` | 1 : 1 : 1 | — | Unlike cortex; ✓ verified as the typical pattern — fact-check: roll an incomplete variant (face + arm, or arm + leg) with p ≈ 0.3 | [S31] (H), [E] |
| `dai_grade3_LOC` | > 6 h, coma, posturing | — | | [S114] (M) |
| `dai_severe_mortality` | 0.6 | p | Vegetative 0.2 | [S114] (M) |

### Visual/behavioural checklist: capsule
- A small, deep track causes a whole half of the body (face, arm and leg) to go limp at once.
- The character falls toward that side; the mouth droops on that side; eyes may turn toward the wounded side.

---

## 12. Cerebellum

### 12.1 What is lost

| Lesion | Deficit | Side | Source |
|---|---|---|---|
| Hemisphere | **Limb ataxia**: dysmetria (overshoot/undershoot, "past-pointing"), **intention tremor** growing as the limb nears its target, dysdiadochokinesia, hypotonia; outstretched arm drifts up and hyperpronates (Riddoch's sign) | **Ipsi** | [S39] |
| Hemisphere | Unsteady gait **toward the side of the lesion**; ipsilateral lateropulsion | Ipsi | [S39][S41] |
| Vermis | **Truncal and gait ataxia**, limbs relatively spared; **titubation** (bobbing/swaying of head and trunk); severe: **cannot sit unsupported** | Midline | [S43] |
| Flocculonodular | Gaze-holding failure (gaze-evoked nystagmus), downbeat nystagmus, periodic alternating nystagmus (nodulus), vertigo | Eyes | [S45][S46] |
| Any acute large lesion | Vertigo, nausea, **vomiting**, occipital headache, dysarthria (scanning), inability to walk | — | [S40][S41] |

Numbers:
- Nystagmus in 75% of cerebellar infarcts (horizontal ipsilateral-beating 47%, contralateral 5%, bilateral 11%, vertical 11%) [S41]. **? not re-verified** (plausible; published cerebellar-stroke series range roughly 50–75%) `[K] (M)`.
- 90% show localising signs (truncal/limb ataxia, nystagmus, dysarthria); **71% of those with "only vertigo" cannot walk** [S41]. **? not re-verified**; the qualitative point (a patient with cerebellar stroke and "just vertigo" usually cannot walk unaided because of truncal ataxia) is ✓ verified `[K] (H)`.
- Cerebellar tremor is low frequency, **< 5 Hz** (typically 3–5 Hz), without a rest component; Holmes (rubral/midbrain) tremor is < 4.5 Hz (2–4.5 Hz) and combines rest, postural and intention components [S44]. **✓ verified** `[K] (H)` (Holmes tremor < 4.5 Hz is the movement-disorder-society consensus criterion).
- **Fall direction ✓ verified** `[K] (H)`: hemispheric lesions give ipsilateral limb ataxia and lateropulsion/falls **toward** the lesion side.
- Gait: reduced speed, cadence and step length; **increased step width, double-support time and especially stride-to-stride variability**, the core feature [S42]. Numbers below are author values (the retrieved summaries gave no means).
- Deterioration after cerebellar haemorrhage (brainstem compression or hydrocephalus): mean 5 days, range 10 h – 10 days, median and mode 3 days; the first sign is falling consciousness [S40]. A vermian haemorrhage, absent corneal reflexes, impaired oculocephalic responses or early hydrocephalus predict deterioration [S40]. **Fact-check (? not re-verified; timing re-scoped):** a median of ~3 days (range hours to ~10 days) is the classic figure for **oedema around infarcted or contused cerebellar tissue** (swelling peaks at days 2–4) `[K] (M)`. A **haematoma** in the posterior fossa (traumatic or spontaneous) usually deteriorates much earlier, often within the first **hours to 24–48 h**, and can go from talking to apnoea within minutes once the fourth ventricle or medulla is compressed `[K] (M)`. Game rule: a cerebellar **track with bleeding** uses the §15 haematoma clock (minutes–hours); only a bloodless contusion/infarct uses the 3-day clock.

### 12.2 Gait and movement numbers for animation

| Quantity | Healthy | Cerebellar ataxia | Tag |
|---|---|---|---|
| Step width (heel-to-heel, lateral) | 8–12 cm | 15–30 cm | [K] (M) / [E] |
| Walking speed | 1.2–1.4 m/s | 0.5–0.9 m/s | [K] (M) |
| Stride-time coefficient of variation | 2–3% | 6–15% | [K] (M) / [E] |
| Double-support fraction of the gait cycle | ~20% | 25–35% | [K] (M) |
| Foot-placement lateral error per step | < 2 cm | 5–15 cm | [E] |
| Trunk sway amplitude (standing, feet apart) | 1–2 cm | 5–15 cm, bursts toward lesion side | [E] |
| Titubation (head/trunk) | none | 2–4 Hz, 1–3 cm | [K] (L) / [E] |
| Intention tremor | none | 3–5 Hz, amplitude 1–5 cm at fingertip, rising within the last 10–20 cm of a reach | [S44] (M), [E] |
| Dysmetria overshoot | < 1 cm | 3–10 cm | [E] |

### 12.3 Simulation parameters: cerebellum

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `cb_volume` | ~130–150 total (~10% of brain) | cm³ | Two hemispheres + vermis | [S38] (M) |
| `cb_hemi_visible_at` / `full_at` | 0.10 / 0.50 | fraction | Ipsilateral limbs | [E] |
| `cb_fall_bias` | toward lesion side, 60–80% of falls | p | Vermis: any direction, often backward | [S39][S41] (M), [E] |
| `cb_nystagmus_prob` | 0.75 | p | Ipsilateral-beating 0.47 | [S41] (M) |
| `cb_cannot_walk_prob` | 0.7 if sev > 0.3 | p | | [S41] (M), [E] |
| `cb_vomit_prob_first_hour` | 0.6–0.8 | p | Repeated vomiting | [S40][S41] (M), [E] |
| `cb_swelling_deterioration` | median 3 days (10 h–10 d) | — | Haematoma-driven compression faster (§15): fact-check — for a bleeding track use minutes to 48 h, not days | [S40] (M), `[K]` |
| `intention_tremor_hz` | 3–5 (Holmes 2–4.5) | Hz | | [S44] (H) |
| `gait_params` | §12.2 | — | Drive procedural gait noise | [E] |

### Visual/behavioural checklist: cerebellum
- The character stays conscious but staggers like someone very drunk: feet wide apart, irregular steps, lurching and finally falling toward the wounded side; it grabs at walls.
- Reaching for something, its hand overshoots and shakes more and more as it gets closer.
- Head and trunk bob and sway; with a midline wound it cannot even sit upright.
- Eyes jerk (nystagmus), especially when looking toward the wounded side; it vomits repeatedly and holds its head still because moving makes the room spin.
- Speech breaks into separate, oddly stressed syllables.

---
## 13. Brainstem by level: partial and one-sided lesions

[R1-04 §2] covers **destruction** of each level (coma, apnoea, collapse). This section covers the **partial or one-sided** injuries that leave the character alive and often awake, with the crossed signs that make brainstem damage look different from anything else. Tracks that graze the brainstem, fragments, and blunt shear (Duret haemorrhage, §15.6) produce these.

### 13.1 Midbrain

| Lesion | Same side (ipsi) | Opposite side (contra) | Source |
|---|---|---|---|
| **Oculomotor (CN III) fascicle or nerve** | **Eye down and out**, **complete ptosis**, **dilated pupil unreactive to light**; cannot look up, down or inward | — | [S49][S50] |
| **Weber** (ventral: CN III fascicle + cerebral peduncle) | CN III palsy | **Hemiplegia including lower face** | [S47] |
| **Claude** (CN III + red nucleus / superior cerebellar peduncle) | CN III palsy | **Ataxia and tremor** (no hemiparesis in the classic form) | [S47] `[K]` |
| **Benedikt** (CN III + red nucleus ± peduncle) | CN III palsy | Tremor, involuntary choreoathetoid movements, ataxia ± weakness | [S47] |
| **Dorsal midbrain (Parinaud)** | Bilateral: **upgaze palsy** (87–100%), **convergence-retraction nystagmus** on attempted upgaze, **light-near dissociation** (pupils react to near but not light), **eyelid retraction** (Collier sign); full triad in 65% | — | [S48] |
| CN III **nucleus** | Ipsilateral CN III palsy, **both** lids droop (single central subnucleus), opposite eye cannot elevate | — | `[K]` (M) |
| Trochlear (CN IV) | **Nerve** lesion (after the crossing; the usual traumatic case, at the tentorial edge): weak depression in adduction of the **same-side** eye, which rides slightly high; vertical double vision; head tilted **away** from the affected eye. Closed head trauma is its commonest cause | **Nucleus/fascicle** lesion (midbrain, before the crossing): the **opposite** eye is affected, so the head tilts **toward** the lesion side. Corrected: was "head tilted away from the lesion side" for all CN IV lesions | `[K]` (H), fact-check |
| Bilateral tegmentum | Coma, fixed mid-position pupils, decerebrate [R1-04 §2.2] | | [R1-04] |
| Late (weeks–months) | **Holmes (rubral) tremor**, < 4.5 Hz, rest + posture + intention | Contra | [S44] |

Corrections to search summaries: one summary described the CN III pupil as an "afferent pupillary defect"; it is an **efferent** defect (the pupil does not constrict whichever eye is lit) `[K] (H)`. Another listed hemiparesis in Claude syndrome; the classic description is contralateral ataxia without hemiparesis `[K] (M)`.

Numbers for the CN III eye:
- Horizontal exodeviation in primary position: mean 40–44 PD in one series, 66 ± 29 PD in another, up to 84 ± 15 PD in very large cases [S50]. That is **~22–33°** outward, up to ~40° `[E]`.
- Vertical (hypotropia): mean ~14 PD, **~8° down** [S50].
- Ptosis: complete, the upper lid covers the pupil `[K] (H)`. Pupil: 6–9 mm, fixed `[K] (M)`.
- Fact-check: the picture (large exotropia, small hypotropia, complete ptosis, fixed dilated pupil) is **✓ verified** `[K] (H)`; PD-to-degree conversions re-computed and correct (atan 0.40 = 21.8°, atan 0.66 = 33.4°, atan 0.84 = 40.0°). The series means [S50] were not re-searched (M). Two nuances: the vertical component is small and variable (some complete palsies are nearly level vertically; the eye also intorts because the superior oblique is unopposed), and the pupil is spared in many **ischaemic** palsies but almost never in **compressive or traumatic** ones, which are the game's cases.

### 13.2 Pons

| Lesion | Same side (ipsi) | Opposite side (contra) | Source |
|---|---|---|---|
| **Abducens (CN VI) nerve / fascicle** | Eye cannot abduct: **esotropia (eye turned in)**, worse looking toward the lesion side | — | [S51] |
| **Abducens nucleus or PPRF** (horizontal gaze centre) | **Neither eye can look toward the lesion**; eyes rest deviated **away** from it (toward the paralysed limbs if the corticospinal tract is also hit). Doll's eyes cannot overcome it | — | [S52][S53] `[K]` |
| **MLF → internuclear ophthalmoplegia (INO)** | Ipsilateral eye fails to adduct (move toward the nose) on gaze to the other side; the other, abducting eye shows jerk nystagmus; convergence preserved. Often bilateral (MLFs lie next to the midline); bilateral + outward drift = **WEBINO** ("wall-eyed") | — | [S62] |
| **One-and-a-half syndrome** (PPRF/CN VI nucleus + MLF) | Ipsilateral eye **frozen horizontally**; the other eye can only **abduct** (with nystagmus); vertical movement and convergence preserved | — | [S52] |
| **Millard-Gubler** (ventral caudal pons) | CN VI palsy (eye turned in) + **CN VII palsy of the whole half-face** (forehead included, eye cannot close) | **Hemiplegia** | [S53] |
| **Foville** (dorsal caudal pons) | **Horizontal gaze palsy toward the lesion** + facial palsy | Hemiparesis sparing the face | [S53] |
| **Ventral pons, both sides** | **Locked-in**: fully awake, quadriplegic, mute; **only vertical eye movements and blinking** remain | Both | [S56] |
| **Large pontine haemorrhage / tegmentum** | Coma, decerebrate rigidity, quadriparesis, eyes central with absent doll's eyes, **pinpoint reactive pupils**, hyperthermia, hyperventilation; ocular bobbing | Both | [S57] |

- Traumatic CN VI palsy occurs in **1–2.7% of head injuries**; bilateral palsy is rare and usually comes with other intracranial or spinal injury [S51]. Raised ICP can stretch one or both sixth nerves over the petrous apex (a "false localising" sign) `[K] (H)`.
- A lower-motor-neuron **facial palsy** (CN VII nucleus/nerve) looks different from the cortical kind (§2.4): the whole half-face is flat including the forehead, the eye does not close and the eyeball rolls up behind the open lids when the character tries to blink (Bell's phenomenon, visible), tears run over the lid `[K] (H)` [S69].
- **Ocular bobbing** (pontine coma): fast conjugate **downward** jerk (~17.5° at ~129°/s peak), sometimes a ~0.5 s pause, then **slow drift back** to mid-position; recurs irregularly **2–15 times per minute** [S54]. Fact-check: the form (fast down, slow return, pontine, pinpoint pupils, absent horizontal movements in typical bobbing) is **✓ verified** `[K] (H)`. The 17.5° / 129°/s kinematics come from a **single-patient** recording [S54] and should be randomised (amplitude ~5–20°, peak velocity ~80–200°/s `[E]`); the rate was not re-verified (some texts give 2–12/min `[K] (L)`). **Ocular dipping** (inverse bobbing, more often diffuse/anoxic damage): slow downward drift over ~2 s, held 2–10 s, fast return, sometimes with a blink; next cycle 10–30 s later [S55]. **Reverse bobbing**: fast up, slow return [S55].
- Massive pontine haemorrhage: invariably fatal but not instantaneous; death usually **24–48 h** after onset, 7–10 days not rare; overall pontine-haemorrhage mortality 30–60% [S57]. **✓ verified** as the typical course `[K] (M)`; fact-check nuance: with a destructive **penetrating** pontine track (rather than a spontaneous bleed) apnoea and collapse are usually immediate, per [R1-04 §2.2]; the 24–48 h clock applies to bleeds that leave the medulla working. Published overall pontine-haemorrhage mortality ranges wider (~30–90% depending on size and series).

### 13.3 Medulla

| Lesion | Same side (ipsi) | Opposite side (contra) | Source |
|---|---|---|---|
| **Lateral medulla (Wallenberg)** | Face pain/temperature loss, **Horner** (small pupil, droopy lid), **dysphagia**, **hoarseness**, weak gag, limb ataxia, **lateropulsion** (pulled toward the lesion side) | Body pain/temperature loss | [S58][S59] |
| **Medial medulla (Dejerine)** | **Tongue paralysis**: protruded tongue deviates **toward the lesion** | **Hemiparesis sparing the face**, position-sense loss | [S60] |
| Bilateral medial medulla | Bilateral tongue paralysis | Quadriplegia; **respiratory failure** and death common | [S60] |
| Bilateral / central medulla | **Apnoea**, vasomotor collapse [R1-04 §2.2] | | [R1-04] |

Wallenberg symptom frequencies (130 consecutive patients): sensory symptoms 96%; **vertigo/dizziness 88%, gait ataxia 88%, Horner 88%**; nystagmus 71%; **nausea/vomiting 65%; dysphagia 62%; hoarseness 41%** [S58]. **? not re-verified by fact-check** (no search available). Sensory symptoms ~96% as the most common feature and Horner/ataxia/vertigo in the high-80s–90s are consistent with the reviewer's recollection of Kim 2003 `[K] (M)`; the hoarseness and dysphagia shares are the least certain (the reviewer recalls them as closer to each other, both ~50–65%) — QA should open the Brain paper before hard-coding them. For the game, rolling hoarseness at 0.4–0.6 and dysphagia at 0.5–0.65 covers both readings. Rostral lesions give dysphagia, facial weakness and dysarthria more often; caudal lesions give more severe gait ataxia and headache [S58]. **Intractable, violent hiccups** are characteristic [S59]. A smaller series reported vocal-cord paresis in all patients and a weak cough in 80% [S59 search summary] (L).

Other medullary signs `[K] (H)`: pooled saliva (cannot swallow) → **wet, gurgling breathing**, drooling, choking and coughing when anything enters the throat; nasal regurgitation; skew deviation with the **ipsilateral eye lower** and head tilted toward that side [S61]; upbeat nystagmus with paramedian lesions, downbeat with midline lower-medullary lesions [S46].

### 13.4 Crossed-sign lookup (for the resolver)

| Level | Ipsilateral cranial-nerve sign | Contralateral limb sign |
|---|---|---|
| Midbrain | CN III: eye down-and-out, ptosis, blown pupil; (CN IV: head tilt) | Hemiplegia with lower-face droop (peduncle), or ataxia/tremor (red nucleus) |
| Upper pons | Face numbness (CN V), jaw weakness | Hemiplegia |
| Lower pons | CN VI (eye in), CN VII (whole half-face), horizontal gaze palsy toward lesion, INO | Hemiplegia |
| Medulla | Tongue deviation (XII), hoarse voice and dysphagia (IX/X), Horner, face numbness | Hemiparesis sparing face (medial) or body pain loss (lateral) |

### 13.5 Simulation parameters: partial brainstem

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `bs_visible_at` / `full_at` | 0.02 / 0.20 | fraction of the level's volume | Tiny lesions matter | [E] |
| `cn3_exo_deg` | 22–33 (max 40) | ° outward | | [S50] (M), [E] |
| `cn3_hypo_deg` | 5–10 (default 8) | ° down | | [S50] (M), [E] |
| `cn3_ptosis` | complete (lid over pupil) | — | Nuclear lesion: bilateral | [S49] `[K]` (H) |
| `cn3_pupil_mm` | 6–9, fixed | mm | | [K] (M) |
| `cn6_eso_deg` | 6–22 (10–40 PD) | ° inward | Abduction stops at midline | [S51] (M), [E] |
| `cn6_trauma_prob` | 0.01–0.027 per significant head injury | p | Bilateral with high ICP | [S51] (M) |
| `pontine_gaze_palsy_rest` | 10–30 away from lesion | ° | Not overcome by doll's eyes | [K] (M), [E] |
| `ino_adduction_limit` | 0–50% of normal range | — | Abducting eye nystagmus 2–4 Hz, 2–5° | [S62] (M), [E] |
| `bobbing_down_amp` / `peak_vel` | 17.5 / 129 | ° / °/s | Pause 0.5 s; slow return 1–3 s | [S54] (M) |
| `bobbing_rate` | 2–15 | per min, irregular | | [S54] (M) |
| `dipping_cycle` | down 2 s, hold 2–10 s, fast up; repeat 10–30 s | s | | [S55] (M) |
| `pontine_pupil_mm` | 1.0–1.5 | mm | Reactive only under magnification | [S57] `[K]` (H) |
| `pontine_hge_death` | 24–48 h (tail 10 d) | — | Game: compress 15× | [S57] (M) |
| `wallenberg_signs` | table §13.3 frequencies | p | Roll each sign independently | [S58] (M) |
| `hiccup_rate` | 10–60 per min in bouts of minutes | — | Wallenberg flourish | [E] on [S59] |
| `lateropulsion_force` | 5–15% body weight sideways toward lesion | — | Feed balance controller | [E] |
| `tongue_dev_side` | toward lesion (medial medulla); toward weak side (cortex/capsule) | — | ✓ verified (fact-check) | [S60] `[K]` (H) |
| `cn4_side` | nerve lesion: ipsilateral eye; nucleus/fascicle lesion: contralateral eye | — | Added by fact-check; head tilts away from the affected eye | `[K]` (H) |

### Visual/behavioural checklist: brainstem (partial)
- One eye droops shut; lifting the lid shows the eye turned down and out with a huge black pupil; the opposite arm and leg are paralysed.
- One or both eyes turned in toward the nose (crossed eyes); the character cannot look to one side with either eye.
- On looking sideways, one eye stays in the middle while the other flicks out with jerky nystagmus.
- A whole half of the face hangs, including the forehead; that eye stays open and rolls upward when it tries to blink; tears spill over.
- Awake, breathing, eyes moving up and down purposefully, blinking in response, but nothing else moves (locked-in).
- Small droopy-lidded pupil on one side, hoarse wet voice, gurgling breaths, drooling, choking on its own saliva, violent hiccups, the body pulled sideways toward the wounded side when it tries to stand.
- Deep coma with pinpoint pupils and eyes that jerk down and drift back up every few seconds.

---

## 14. Eye signs: master table

### 14.1 Gaze direction and alignment

| Sign | Lesion | Direction | Magnitude | Timing | Appearance | Source |
|---|---|---|---|---|---|---|
| **Conjugate gaze deviation, destructive hemispheric** | FEF, large MCA territory, putamen/capsule | **Toward the lesion** (away from the paralysed side) ✓ verified | 15–40°; > 14–15° typical of large infarcts; head often turned too (magnitudes ? not re-verified) | Immediate; days (≈1 week) | Both eyes and head turned to the wounded side; doll's eyes can still move them | [S63][S64][S27] |
| **Seizure (irritative) deviation, "versive"** | Frontal (or other) seizure focus | **Away from the focus** (>90% of patients) ✓ verified, **for forced version only** | Forced, extreme 30–45°; head turns with it | Seconds, during the seizure; may reverse when focal destructive deficit dominates after the seizure | Head and eyes wrench to one side, often the first sign of the fit | [S65][S71] |
| **Pontine gaze palsy** | PPRF / CN VI nucleus | **Away from the lesion** (toward the paralysed side) ✓ verified | 10–30° at rest | Immediate, persistent | Eyes look at the paralysed limbs; doll's eyes fail | [S52][S53] `[K]` |

Fact-check note on versive seizures `[K] (H)`: Wyllie 1986 [S65] found that only **forced, sustained, unnatural** head/eye turning ("version") lateralises (contralateral to the focus in > 90%); mild, non-forced head turning early in a seizure has no lateralising value and is often **ipsilateral**. Game: early in a focal-onset seizure allow a mild head turn in either direction (p ≈ 0.5 each), then the forced contraversive wrench in the seconds before generalisation.
| **Thalamic eyes** | Thalamic haemorrhage/track | **Down and in**; occasionally **wrong-way** (away from lesion) | 10–25° down, 5–15° in | Immediate | "Peering at the tip of the nose"; small pupils | [S27][S29] |
| **Upgaze palsy / setting sun** | Dorsal midbrain; hydrocephalus pressing it | Eyes cannot go up; with hydrocephalus tonically **down**, sclera visible above the iris | Up-range 0–10° | Minutes–hours with hydrocephalus | Lids retracted, eyes pushed down | [S48] `[K]` |
| **Skew deviation / ocular tilt reaction** | Otolith pathway: vestibular nucleus to midbrain (INC) | Vertical misalignment. Pontomedullary lesion: **ipsilateral eye lower**; midbrain lesion: contralateral eye lower. Head tilts toward the lower eye | 2–10° vertical `[E]` | Immediate; weeks | One eye higher than the other; head tilted | [S61] `[K]` |
| **INO / WEBINO** | MLF | Adduction failure of the eye on the lesion side; bilateral with exotropia | Adduction 0–50% | Immediate | Eyes drift outward ("wall-eyed"); one eye lags when looking sideways | [S62] |
| **One-and-a-half** | PPRF/CN VI nucleus + MLF | Ipsi eye fixed horizontally; other eye only abducts | — | Immediate | | [S52] |
| **CN III palsy** | Midbrain, CN III nerve, uncal herniation | Ipsi eye **down and out** | 22–33° out, ~8° down; complete ptosis | Immediate (track) or minutes–hours (herniation) | See §13.1 | [S49][S50] |
| **CN VI palsy** | Pons, petrous apex, raised ICP | Ipsi eye **in** | 6–22° in | Immediate or with ICP | "Crossed eyes" | [S51] |
| **CN IV palsy** | Dorsal midbrain / nerve (blunt trauma) | Nerve lesion: ipsi eye slightly **up**, head tilts away from it. Nucleus/fascicle lesion: the **contralateral** eye is affected (corrected: was "Ipsi" for all lesion sites; fact-check) | 2–8° `[E]` | Immediate | Subtle | `[K]` |
| **Resting divergence in coma / death** | Loss of tonic convergence | Both eyes slightly **out** | 5–15° | With unconsciousness | Slightly "wall-eyed", unfocused | [R1-04] `[K]` |

### 14.2 Spontaneous eye movements in the unconscious

| Movement | Lesion it indicates | Kinematics | Source |
|---|---|---|---|
| **Roving eyes** | Cortex/hemispheres depressed, **brainstem intact** (metabolic, bilateral supranuclear) | Slow, conjugate (slight exophoria allowed), predominantly horizontal, random; like deep sleep. Author values: 10–30° excursions at 5–20°/s | [S66] `[E]` |
| **Ping-pong gaze** | Bilateral hemispheric dysfunction (structural or reversible) | Horizontal conjugate swings end-to-end; **cycle 1.5–8 s** (typically 3–7 s). Structural cases: death or vegetative state 67% | [S67] |
| **Periodic alternating gaze deviation** | Metabolic/hepatic, posterior fossa | Deviation reverses about every **2 min** | [S66] |
| **Ocular bobbing** | Pons | Fast down 17.5°, slow up; 2–15/min | [S54] |
| **Ocular dipping** | Diffuse/anoxic | Slow down (2 s), hold 2–10 s, fast up | [S55] |
| **Reverse bobbing / reverse dipping** | Non-localising | Up variants | [S55] |
| **No movement, eyes midline** | Deep coma, brainstem failure, brain death | Static | [R1-04] |

### 14.3 Nystagmus types

| Type | Lesion | Direction of fast phase | Characteristics | Source |
|---|---|---|---|---|
| **Gaze-evoked** | Cerebellum (flocculus), brainstem gaze-holding | **Toward the direction of gaze**; larger/slower toward the side of a floccular lesion | Appears only at eccentric gaze (> 20–30°); 1–3 Hz, 2–5° `[E]` | [S45] |
| **Bruns** | Cerebellopontine angle mass | Large, slow to the lesion side + small, fast to the other side | | [S45 search summary] `[K]` |
| **Downbeat** | Flocculonodular cerebellum; midline lower medulla | **Down**; worse on downgaze and lateral gaze | Commonest central vestibular nystagmus | [S45][S46] |
| **Upbeat** | Pontomesencephalic or pontomedullary junction, anterior vermis, paramedian medulla | **Up** | | [S46] |
| **Periodic alternating (PAN)** | Nodulus/uvula | Horizontal, **reverses every 90–120 s** with a brief null | | [S46] |
| **See-saw** | Parasellar/suprasellar, meso-diencephalic (INC) | One eye rises and intorts while the other falls and extorts, alternating (pendular) | | [S46] |
| **Convergence-retraction** | Dorsal midbrain (Parinaud) | On attempted upgaze the eyes jerk **inward** and the globes **retract** into the orbits | | [S48] |
| **Abducting nystagmus** | INO (MLF) | In the abducting eye only | | [S62] |
| **Peripheral vestibular** | Inner ear / temporal-bone fracture | **Away from the damaged ear**, horizontal-torsional, suppressed by fixation | | `[K]` (H) |
| **Epileptic** | Seizure focus (often temporo-parieto-occipital) | **Away from the focus**, with tonic deviation of eyes/head | Jerky, horizontal, conjugate | [S71] |

### 14.4 Pupils

| State | Size (mm) | Light reaction | Side / notes | Source |
|---|---|---|---|---|
| Normal | 2–4 in bright light, 4–8 in dark | Brisk: latency ~0.2–0.3 s, constriction ~0.5–1 s | Physiological anisocoria ≤ ~0.5–1 mm in a minority | `[K]` (H) |
| **Horner** (lateral medulla, cervical sympathetic chain) | Miosis; anisocoria 0.5–4.5 (mean 1.7) in dim light | Reacts; **dilation lag** (anisocoria greatest ~5 s after the light goes off) | Ipsi; ptosis < 2 mm; lower lid slightly raised ("upside-down ptosis") | [S72] |
| Diencephalic / early central herniation / thalamic | **1–3, small** | Reactive | Both | [S87][S27] |
| Pretectal / dorsal midbrain | 4–6 | **Poor to light, normal to near** (light-near dissociation) | Both | [S48] |
| Midbrain tegmentum (nuclear) | **4–6, mid-position** | **Fixed**, often irregular | Both | [R1-04] [S87] |
| **CN III compression (uncal herniation)** | 6–9 | Sluggish → fixed; may be oval as it dilates | **Ipsilateral to the mass** in most cases | [S74] `[K]` |
| **Pontine** | **1–1.5, pinpoint** | Reactive only under magnification | Both | [S57] |
| Brain death | 5.0 ± 0.85 (range ~3.7–7.3); < 2 mm argues against brain death | Fixed | Both | [S73] |
| During generalised seizure | Dilated | Unreactive | Both | [R1-04 §4.2] |
| Cortical blindness | Normal | **Normal** | Both | [S22] |
| Hypoxia / dying | Dilate over 1–3 min | Lost | Both | [R1-04 §2] |

Hutchinson sequence during uncal herniation [S74]: (1) brief **ipsilateral constriction** (irritation of the parasympathetic fibres on the outside of CN III); (2) **ipsilateral dilation**, often with brief contralateral constriction; (3) **bilateral fixed dilation**. The parasympathetic fibres lie on the surface of the nerve and are compressed first, which is why the pupil goes before eye movement [S74]. **✓ verified** `[K] (H)`. Fact-check additions `[K] (M)`: stage 1 is short and rarely witnessed clinically (make it 5–60 s and easy to miss); the first dilated pupil is on the side of the mass in roughly **85–90%** of cases, so a "false-side" pupil (p ≈ 0.1) is realistic; an **oval** or eccentric pupil is common during the transition.

### 14.5 Reflexes the player can trigger (by moving the head, touching the eye, flashing light, threatening the face)

| Reflex | Normal (awake) | Coma, brainstem intact | Brainstem damage / death | Source |
|---|---|---|---|---|
| **Oculocephalic (doll's eyes)** | Suppressed by fixation; eyes go with the head | Head turned → **eyes counter-rotate** and keep pointing at the same spot (gain ≈ 1, latency ~10 ms `[K]`) | **Absent**: eyes move with the head like painted eyes | [S68] |
| Cold caloric | Nystagmus, fast phase away from the cold ear | Slow tonic deviation **toward** the cold ear for minutes, no fast phase | Absent | `[K]` (H) |
| Corneal (touch the cornea) | Blink both eyes | Blink present | **Absent** with pontine (CN V/VII) failure | [R1-04] `[K]` |
| **Bell's phenomenon** | Eyes roll up and slightly out under closing lids (75–80% of people) | Strong corneal stimulus may trigger it = midbrain and pons working | Absent | [S69] |
| Menace blink | Blink to a sudden approaching object | Absent (no awareness) | Absent | [S22] |
| Pupil light | Constrict | Constrict (unless III/midbrain hit) | Fixed | §14.4 |

### 14.6 Eyes during transient loss of consciousness

| Event | Eyes | Other | Source |
|---|---|---|---|
| **Syncope** (drop in brain blood flow, including faint from pain or blood loss) | Open in most; **initial upward deviation** common; some have brief **downbeat nystagmus** first, then upward deviation | LOC **12.1 ± 4.4 s**; **multifocal arrhythmic myoclonic jerks in 90%**; head turns, lip-smacking, righting movements in 79% | [S70] ✓ verified `[K] (H)`. Fact-check: measured in **healthy young volunteers** (induced faints, supine recovery); a faint from haemorrhage with ongoing low pressure lasts longer and may not end |
| **Knockout** | Open, fixed unfocused stare, or rolled up | "Flash" KO < 3 s vs KO ≥ 3 s; tone lost completely at once; wake within seconds to a few minutes | [S98] `[K]` |
| **Death (myth guard, fact-check)** | **Not left rolled back.** When consciousness is lost from falling brain perfusion (bleeding out, heart wound) the eyes may deviate up 10–30° for 2–10 s [R1-04 §11], then settle near straight ahead or slightly divergent; after death they stay there, lids usually part-open (an open lid drops 2–4 mm over 1–3 s) and pupils mid-to-wide and fixed [R1-04 §11.3–11.5] | Sustained upward deviation belongs to living states (syncope, seizures, some knockouts); a corpse whose eyes stay rolled up to the whites is a film convention | [R1-04] `[K] (M–H)` |
| **Epileptic seizure** | Open (≈90–97%), forced deviation away from focus or upward; epileptic nystagmus possible; pupils dilated | §17 | [R1-04 §4.2][S65][S71] |

### 14.7 "Eyes crossing": all the ways the two eyes stop pointing at the same thing

1. **CN VI palsy** (one or both eyes turned in; with raised ICP both) (§13.2).
2. **Thalamic esodeviation** (both eyes down and in) (§10).
3. **Skew deviation** (one eye higher) (§14.1).
4. **INO / WEBINO** (eyes drifting out, one lagging) (§13.2).
5. **CN III palsy** (one eye out and down, lid shut) (§13.1).
6. **Coma or death** (both slightly out, unfocused) [R1-04].
7. **Concussion**: convergence insufficiency and blurred/double vision are the commonest ocular problems (up to ~3/4 of acute concussions show some oculomotor dysfunction), but they are subtle to an observer [S102].

### 14.8 Eye-rig reference numbers (author values)

| Quantity | Value | Tag |
|---|---|---|
| Rotation range | Horizontal ±45°, up +35°, down −45° | [K] (M) |
| Saccade peak velocity | 300–500°/s (10–20° saccades) | [K] (H) |
| Saccade duration | ≈ 2.2 ms × amplitude(°) + 21 ms (20° ≈ 65 ms) | [K] (M) |
| Saccade latency | 150–250 ms | [K] (H) |
| Smooth pursuit | Accurate to ~30°/s; breaks into catch-up saccades above | [K] (M) |
| Vestibulo-ocular reflex | Gain ≈ 1.0, latency ~10 ms | [K] (H) |
| Blink | 15–20/min awake; closure 100–150 ms, full blink 200–300 ms | [K] (M) |
| Lid position awake | Upper lid covers top 1–2 mm of the iris | [K] (M) |

### 14.9 Simulation parameters: eyes (summary)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `gaze_bias_hemi_destructive` | +15 to +40 (default +25) | ° toward lesion | Decays over days | [S63][S64] (M) |
| `gaze_bias_seizure` | −30 to −45 | ° (away from focus) | Only while seizing | [S65] (M), [E] |
| `gaze_bias_pontine` | −10 to −30 | ° | Persistent | [K] (M) |
| `pingpong_period` | 3–7 (1.5–8) | s per full cycle | | [S67] (M) |
| `roving_speed` | 5–20 | °/s | | [E] |
| `pag_period` | ~120 | s per direction | | [S66] (L) |
| `pan_period` | 90–120 | s per direction | | [S46] (M) |
| `nystagmus_freq` / `amp` | 1–4 / 2–10 | Hz / ° | Jerk form: slow drift + fast reset | [E] on [K] |
| `pupil_*` | table §14.4 | mm | Blend at 0.5–1 mm/s for pathological changes in the acute band | [E] |
| `anisocoria_significant` | > 1 | mm | Show as a warning sign; clinicians also track constriction velocity with pupillometers (a sluggish pupil precedes a fixed one) | [K] (H), [S75] |
| `dolls_eyes_gain` | 1.0 if brainstem intact and unconscious; 0 if brainstem failed | — | Awake: fixation overrides | [S68] (H) |

### Visual/behavioural checklist: eyes
- The side the eyes turn tells the player where the damage is: toward a destroyed hemisphere, away from a seizing one, away from a destroyed pons.
- In coma with a working brainstem the eyes drift slowly side to side, and when the head is turned they stay "looking at the ceiling". When the brainstem fails, they stop moving and follow the head like a doll's painted eyes.
- A single huge pupil on the side of a head wound, first sluggish then fixed, then the other pupil follows: the brain is herniating.
- Pinpoint pupils with downward bobbing eyes: pons. Small pupils with eyes looking at the nose: thalamus. Mid-sized fixed pupils: midbrain.
- A faint: eyes open, rolling up for about 12 s, with a few irregular jerks of the limbs.

---
## 15. Traumatic brain injury progression over minutes to hours

### 15.1 Pressure–volume model for the game

Constants from [R1-04 §1]: ICP normal 5–15 mmHg (default 10); pressure–volume index (PVI) 25 mL; CPP = MAP − ICP; treatment threshold ICP > 22 mmHg.

| Quantity | Value / rule | Tag |
|---|---|---|
| Compensatory reserve (CSF pushed into the spinal sac + venous blood squeezed out) before ICP climbs | 50–70 mL for an acutely growing mass (default 60) | [K] (M) / [E] |
| ICP beyond the reserve | ICP = ICP₀ × 10^((V_mass − V_reserve) / PVI) | [E] on [R1-04] |
| Midline shift from a lateral mass | ≈ 0.10 mm per mL (30 mL → 3 mm; 50 mL → 5 mm; 70 mL → 7 mm; 90 mL → 9 mm), chosen so the Ropper thresholds below line up with the EDH timeline in §15.2 | [E] |
| Consciousness vs horizontal pineal shift (Ropper) | 0–3 mm alert; 3–4 mm drowsy; 6–8.5 mm stupor; 8–13 mm coma | [S84] (M) ✓ verified `[K] (H)` (matches the NEJM 1986 abstract; derived from acute hemispheral masses; the 4–6 mm gap is interpolated) |
| Cushing response | Appears when CPP falls below ~15 mmHg (seen in almost every case below that) | [S85] (M); **? threshold not re-verified**; the two-stage sequence is ✓ verified `[K] (H)`; fact-check: the complete triad (hypertension + bradycardia + irregular breathing) is seen in only a minority (often quoted ~one third) of patients with raised ICP and is a late sign `[K] (L–M)` |
| Plateau (Lundberg A) waves | ICP rises from near normal to **50–100 mmHg**, holds **5–20 min**, falls sharply; during them headache, nausea, stupor, **tonic posturing**; at the peak apnoea and decerebration | [S86] (M) ✓ verified `[K] (H)` (Lundberg's definition) |
| Haematoma volume vs outcome (spontaneous intracerebral bleed, as a dose example) | ≥ 60 cm³ with GCS ≤ 8: 91% 30-day mortality; < 30 cm³ with GCS ≥ 9: 19% | [S94] (H) |

### 15.2 Epidural (extradural) haematoma, EDH

- Usually a skull fracture tears the **middle meningeal artery**; ~75% of adult EDHs are temporal [S78]. **✓ verified** `[K] (M)` (temporal/temporoparietal predominance and MMA source ~85% are textbook; in children the distribution is more even). Fact-check addition: roughly 10–15% of EDHs are **venous** (dural sinus, diploic veins; posterior-fossa EDH over the transverse sinus) and grow more slowly `[K] (M)`.
- **Lucid interval**: estimates range 20–50% of EDH patients; the textbook sequence (knocked out → wakes and talks → deteriorates) is seen in fewer than 20% [S76]. The interval lasts **minutes to hours**; deterioration, if it happens, is usually within 24 h [S76]. Progressive EDHs developed between 2 h and 7 days after injury, average 23 h [S77]. **✓ verified** for the 20–50% band and the minutes-to-hours interval `[K] (M)`; the 23 h mean ? not re-verified. Note: a substantial minority of EDH patients (reported shares vary widely, roughly one fifth to two fifths) are never unconscious at all and simply deteriorate later `[K] (L)`; the game's "p ≈ 0.6 initial knockout" below is consistent with this.
- Treated outcome: not comatose → mortality 0–5%; comatose (GCS ≤ 8) → 11–41% [S78]. **? not re-verified**; consistent with the reviewer's recollection (overall surgical mortality ~10%, near 0% in patients not in coma, ~20–40% in deep coma) `[K] (M)`. Guidelines evacuate any EDH > 30 cm³; < 30 cm³, < 15 mm thick and < 5 mm shift in an alert patient can be observed [S79]. The game has no neurosurgeon: **an untreated expanding EDH kills** `[K] (H)`.

Default "classic" EDH timeline for the game (arterial source, untreated) `[E]` on [S76][S77][S78][S84][S85]:

| Stage | Real time from impact (default, range) | Mass (mL) | What the player sees | t_game |
|---|---|---|---|---|
| Impact | 0 | 0 | Brief knockout 5 s – 5 min (p ≈ 0.6), or dazed only | 1× |
| Lucid interval | default 60 min (15 min – 6 h) | 5 → 50 | Awake, talking, walking; worsening headache, 1–3 vomits, irritability | 4× → 15× |
| Early decline | +10–30 min | 50 → 70 | Drowsy, slurred, confused (GCS 13 → 10); **contralateral** arm drift and weakness begins; ipsilateral pupil 1 mm larger and sluggish | 4× |
| Uncal herniation | +10–30 min | 70 → 90 | Stupor → coma (GCS ≤ 8); ipsilateral pupil 6–9 mm fixed; contralateral hemiplegia; decorticate then decerebrate spasms; Cushing (SBP 160–220, HR 40–60, irregular breathing); snoring/gurgling airway | 4× |
| Brainstem failure | +5–20 min | > 90 | Both pupils fixed dilated; flaccid; ataxic → cluster breathing → apnoea | 1× for the last 60 s |
| Death | +4–10 min after apnoea | — | Hypoxic cardiac arrest [R1-04 §2.4] | 1× → 4× |

`edh_bleed_rate`: default 1 mL/min (0.3–3) for arterial; 0.1–0.3 mL/min for venous-sinus EDH `[E]`. Total from first decline to death with the default rate: ~40–90 min real `[E]`.

### 15.3 Acute subdural haematoma, ASDH

- Torn bridging veins or cortical arteries, usually over a contused, swollen brain; a lucid interval is less common than with EDH `[K] (H)`.
- In comatose patients, surgery within 4 h gave 30% mortality versus 90% after 4 h [S80]. In a series of severely injured patients (GCS 3–7), ASDH mortality was 66%; GCS 3–4 and age > 65 predicted death [S81].
- **Game default**: coma from the start in severe blunt injury (p_lucid 0.1–0.2), mass growth 0.2–1 mL/min, with swelling of the underlying brain adding 20–50% to the effective volume over 1–6 h `[E]`.

### 15.4 Contusions, swelling and "talk and die"

- Contusions expand (haemorrhage + oedema) in ~50% of patients (up to 75% in some series); haemorrhagic progression mostly in the first **12–24 h**; pericontusional oedema then grows over **2–3 days** [S83].
- **"Talk and die"**: patients who speak after injury and later die. Incidence 2.4–7.8% of head injuries; 2.6% of head-injury deaths. **25% had no haematoma** at autopsy; the killers were swelling around contusions and ischaemic/hypoxic damage [S82].
- Penetrating wounds: haematomas along the track, intraventricular bleeding and acute hydrocephalus cause secondary deterioration [S118]. In civilian series all deaths had admission GCS 3–8 [S118]; **non-reactive pupils, bihemispheric (non-bifrontal) tracks, posterior-fossa involvement and age > 35** predicted death [S95]; diencephalic, transventricular and posterior-fossa tracks had **100% mortality** in one series [S95]. Rare survivors of bihemispheric tracks exist [S121]. Fact-check: the predictor list is **✓ verified** as consistent with the civilian GSW-head literature `[K] (M)` (low GCS/motor score, fixed pupils, bihemispheric or multilobar, transventricular and posterior-fossa tracks, suicide attempts and older age recur across series). The "100%" is **? not re-verified** and comes from small subgroups; use p(death) 0.9–1.0 for these tracks rather than a hard 1.0, which leaves room for the rare survivors seen in other series. Overall civilian GSW-head mortality is commonly ~70–90% including pre-hospital deaths `[K] (M)`.

### 15.5 Cushing response

- Stage 1: sympathetic surge, **hypertension and tachycardia**; stage 2: hypertension persists and the heart rate **slows** (baroreflex) [S85]. Widened pulse pressure and irregular breathing complete the triad [S85].
- Simultaneous hypertension and tachycardia is an earlier warning than waiting for bradycardia [S85]. The full triad is a late sign that appears just before herniation and may never appear [S85].
- Author values for display `[K]` (M): SBP 160–240 mmHg, pulse pressure 80–120 mmHg, HR 40–60 bpm (can fall to 30), breathing slow and irregular (§15.6 table).

### 15.6 Herniation syndromes

**Uncal (lateral transtentorial)** — temporal or lateral masses (EDH, ASDH, temporal contusion):
- The medial temporal lobe (uncus) slides over the tentorial edge and compresses the **ipsilateral CN III** and midbrain [S90].
- Sequence: ipsilateral pupil (Hutchinson stages, §14.4) → falling consciousness → **contralateral** hemiparesis (cerebral peduncle) → decerebrate → bilateral fixed pupils → brainstem failure `[K]` [S90][S74].
- **Kernohan notch** (false localising): the opposite cerebral peduncle is pushed against the tentorium, producing hemiparesis on the **same** side as the mass and the blown pupil [S88]. Game probability 0.1–0.2 `[E]`. **✓ verified** (mechanism and side) `[K] (H)`; the probability is an estimate (reported as uncommon; some series of herniating supratentorial masses report false-localising hemiparesis in the low tens of percent) `[K] (L)`.
- Posterior cerebral artery compression can add an occipital infarct (hemianopia) in survivors `[K] (M)`.
- Prognosis: survival 46% with a unilateral fixed dilated pupil versus 13% with bilateral [S89]; mortality 16% with both pupils reactive, 38% with one, 59% with none [S92]. In one surgical series the median time from pupil change to surgery was 133 min (30–900 min), showing the window lasts hours, not seconds [S89]. **Fact-check:** the gradient (both reactive < one < none, unilateral fixed pupil far better than bilateral) is **✓ verified** `[K] (H)`; the exact percentages are **? not re-verified** (the 16/38/59 split is plausible for pooled CRASH + IMPACT data, which include milder injuries; IMPACT-only severe-TBI cohorts give higher values). Survival figures in [S89] are for **operated** patients; untreated, a bilateral fixed dilated pupil from a mass is near-uniformly fatal `[K] (M)`.

**Central (rostrocaudal) herniation stages** (Plum & Posner) [S87] with author-added numbers `[K]`/`[E]`:

| Stage | Consciousness | Breathing | Pupils | Eye movements | Motor | Default stage duration (acute mass) |
|---|---|---|---|---|---|---|
| Early diencephalic | Drowsy, poor concentration, agitation | Sighs, yawns, pauses → **Cheyne-Stokes** (cycle 45–90 s) | **Small, 1–3 mm, reactive** | Roving; doll's eyes intact | Localises; bilateral Babinski; paratonia | 10–60 min (reversible) |
| Late diencephalic | Hard to rouse | Cheyne-Stokes | Small, reactive | Doll's eyes intact | Localising lost → **decorticate** | 10–30 min |
| Midbrain–upper pons | Coma | **Central neurogenic hyperventilation** (≥ 25/min, often 40–60) | **Mid-position 3–5 mm, fixed, irregular** | Doll's eyes weak, dysconjugate | **Decerebrate** | 5–30 min |
| Lower pons–upper medulla | Coma | Shallow, fast or **ataxic**, apneustic pauses | Mid-position, fixed | Doll's eyes and calorics absent | Flaccid; legs may withdraw from foot stimulation | 2–15 min |
| Medullary | Coma | **Slow irregular gasps → apnoea** | Dilate (hypoxia) | None | Flaccid | 1–5 min to apnoea |

**Tonsillar (foramen magnum)** — posterior fossa mass (cerebellar haematoma, occipital EDH) or end stage: the cerebellar tonsils compress the medulla against the clivus/odontoid: **coma and respiratory arrest**, usually rapidly fatal; fourth-ventricle outflow blocks, causing acute hydrocephalus [S90]. Warning signs `[K] (M)`: occipital headache, neck stiffness, head tilt, vomiting, then **sudden apnoea** with the heart still beating.

**Subfalcine** — the cingulate gyrus slides under the falx; the anterior cerebral artery can be compressed → **contralateral leg** weakness `[K] (M)`.

**Duret haemorrhages** — small linear or flame-shaped bleeds in midbrain and upper pons from stretching of basilar perforators during descending herniation; on emergency imaging in 41%, on delayed imaging in 56%; regarded as a terminal event (death or vegetative state) [S91].

### 15.7 Breathing patterns by level (for the audio/physiology system)

| Pattern | Level | Rhythm (author values unless sourced) | Tag |
|---|---|---|---|
| Cheyne-Stokes | Bilateral hemispheres / diencephalon | Crescendo–decrescendo hyperpnoea 30–40 s alternating with apnoea 10–30 s | [S96] `[K]` (M) |
| Central neurogenic hyperventilation | Midbrain / upper pons | Deep, regular, ≥ 25 breaths/min | [S96] (M) |
| Apneustic | Mid/lower pons | Deep inspiration, **held 2–3 s**, brief expiration | [S96] `[K]` (M) |
| Cluster | Lower pons / upper medulla | 3–5 irregular breaths, then apnoea 10–30 s | [S96] `[E]` (L) |
| Ataxic (Biot) | Medulla | Completely irregular rate and depth, random pauses; precedes apnoea | [S96] (M) |
| Gasping / apnoea | Medulla destroyed | [R1-04 §2] | [R1-04] |

### 15.8 Simulation parameters: TBI progression

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `icp_reserve_ml` | 60 (50–70) | mL | Then exponential with PVI 25 mL | [K]/[E] |
| `mls_per_ml` | 0.10 | mm/mL | Lateral masses | [E] |
| `loc_from_mls` | 0–3 alert, 3–4 drowsy, 6–8.5 stupor, 8–13 coma | mm | Interpolate; ✓ verified (fact-check) | [S84] (H) |
| `cushing_cpp` | < 15 | mmHg | Tachy + HTN first, then brady | [S85] (M) |
| `plateau_wave` | 50–100 mmHg for 5–20 min | — | Triggers posturing episodes | [S86] (M) |
| `edh_lucid_prob` | 0.2–0.5 (textbook form < 0.2) | p | | [S76] (M) |
| `edh_lucid_duration` | 60 (15–360) | min | | [S76][S77] (M), [E] |
| `edh_bleed_rate` | 1 (0.3–3) | mL/min | Venous 0.1–0.3 | [E] |
| `asdh_lucid_prob` | 0.1–0.2 | p | | [E] |
| `contusion_growth_window` | 12–24 h haemorrhage; oedema 2–3 days | — | Out of scope except in time skips | [S83] (M) |
| `talk_and_die_prob` | 0.03–0.08 of head-injured characters that talk | p | Includes non-haematoma swelling | [S82] (M) |
| `kernohan_prob` | 0.1–0.2 | p | Ipsilateral hemiparesis | [S88] (L), [E] |
| `herniation_stage_durations` | table §15.6 | min | Real time; game 4× | [E] on [S87] |
| `tonsillar_apnoea` | sudden | — | Heart continues 4–10 min [R1-04 §2.4] | [S90] (M) |
| `mortality_by_pupils` | 0.16 / 0.38 / 0.59 | p | Both / one / neither reactive (for survival-based outcomes); pooled mild-to-severe data — for untreated severe injury raise to ~0.3 / 0.6 / 0.9 `[E]` | [S92] (M) — fact-check: confidence lowered from (H); gradient ✓, exact values not re-verified |

### Visual/behavioural checklist: TBI progression
- A character hit on the side of the head goes down briefly, gets up, talks and complains of a headache, vomits; then over tens of minutes becomes sleepy and slurred, one arm weakens (opposite the wound), the pupil on the wounded side grows, and it slides into coma with stiffening spasms, a slow pounding pulse and irregular breathing, then both pupils go wide and breathing stops.
- A character with a crushing blunt blow is unconscious from the start and follows the same slide faster.
- Snoring and gurgling breath sounds, then sighing and yawning, then waxing–waning breathing, then fast deep breathing, then irregular gasps, then silence.
- A back-of-the-head (posterior fossa) injury: stiff neck, head held tilted, vomiting, then abrupt stop of breathing while the heart still beats.

---

## 16. Concussion: observable signs (additions to [R1-04 §3.6])

- Observable signs used in sport: **lying motionless**; **slow to get up**; **motor incoordination** (stumbling, falling back down, unable to walk heel-to-toe); **blank or vacant look**; dazed; **clutching the head**; confusion, repeated questions; brief loss of consciousness; **impact seizure** (rare); **tonic posturing** [S97]. In NFL video review, visible signs were present in about three quarters of diagnosed concussions; the commonest were being slow to get up and motor incoordination [S97].
- Knockout: flash knockout (< 3 s) versus knockout (≥ 3 s); consciousness usually returns within a few minutes; muscle tone is lost completely and at once [S98]. Rotational blows (hook to the jaw) are the classic cause [S98].
- Vomiting after head injury: ~7% of adults overall, ~28% of adults with a skull fracture [S101] (L; the exact paper behind the summary was not identified). Repeated vomiting is a warning sign of an expanding lesion [S101] `[K]`.
- Double or blurred vision from convergence insufficiency is the commonest eye problem [S102].
- A vagal (non-haemorrhagic) reflex response to injury can cause bradycardia, hypotension and fainting that mimic blood loss [S119].

Default real-time sequence for a moderate concussion without structural injury `[E]` on [S97][S98][R1-04 §3.6]:

| t (real) | Event |
|---|---|
| 0 | Impact; tone lost at once if knocked out |
| 0–2 s | Fencing response (p 0.66 on KO) or tonic posturing; rare impact convulsion (§17) |
| 3 s – 5 min (default 20 s) | Unconscious; snoring breaths; eyes open or rolled up |
| +0–60 s | Eyes open, **blank stare**, no answer; slow blinking |
| +10 s – 2 min | Tries to rise, **stumbles, falls back**, grabs at support; clutches head |
| +2–30 min | Confused, repeats questions, amnesic for the event; headache; nausea, sometimes one vomit; unsteady, wide-based walking |
| +30 min – hours | Headache, slowness; if it worsens instead of improving → §15 |

### Simulation parameters: concussion

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `flash_ko_threshold` | 3 | s | < 3 s = flash KO | [S98] (M) |
| `visible_sign_prob` | 0.75 | p | At least one observable sign in a diagnosed concussion | [S97] (M) |
| `slow_to_rise_delay` | 5–60 | s | After waking | [E] on [S97] |
| `refall_prob` | 0.3–0.6 | p | Falls back on first attempt to stand | [E] on [S97] |
| `vomit_prob_concussion` | 0.07 (0.28 with skull fracture) | p | | [S101] (L) |
| `head_clutch_prob` | 0.3–0.5 | p | Hand to head within 1–5 s of waking | [E] |

### Visual/behavioural checklist: concussion
- After the blow the character lies still, then stares blankly, then tries to get up and wobbles, stumbles or drops back down.
- It clutches its head, asks the same thing repeatedly, and does not remember being hit.
- Eyes may not converge well; it squints or closes one eye.

---

## 17. Seizures and other involuntary movements

### 17.1 How often and when

| Category | Timing | Incidence | Source |
|---|---|---|---|
| **Impact seizure / concussive convulsion** | Within 2 s of impact; tonic up to ~20 s then jerks up to 150 s | ~1 in 70 sport concussions; benign | [S100] [R1-04 §3.6] |
| **Immediate post-traumatic seizure** | < 24 h | 1–4% of TBI | [S103] (? not re-verified; plausible) |
| **Early** | 1–7 days | 4–25% of TBI (untreated) | [S103] ✓ verified `[K] (H)` (the "4–25% early, 9–42% late in untreated patients" ranges are the ones quoted by the Brain Trauma Foundation guidelines; they refer mainly to **moderate–severe** TBI; population-based rates across all severities, as in Annegers 1998, are far lower) |
| **Late (epilepsy)** | > 7 days | 9–42%; up to ~50% after dural penetration and in military penetrating series | [S103] ✓ verified `[K] (H)` (Vietnam Head Injury Study: ~50% late epilepsy after penetrating wounds) |

- One search summary stated that ~50% of penetrating head injuries have **immediate** seizures. This conflicts with the other figures and with the classification in the same source; it most likely refers to late epilepsy after penetrating injury. **Game value**: p(immediate seizure within the first hour) = 0.05–0.10 for a penetrating cortical track, 0.02–0.04 for blunt cortical contusion `[E]`.
- Seizures arise from **cortex**. Pure cerebellar, brainstem or deep white-matter lesions do not cause epileptic seizures `[K] (H)`; motor-strip, frontal and temporal cortex hits are the most epileptogenic `[K] (M)`.

### 17.2 Generalised and focal-to-bilateral tonic–clonic seizures

- In 120 video-EEG-recorded secondarily generalised seizures, mean duration was **62 s**; phases were onset of generalisation, pre-tonic clonic, tonic, **tremulousness**, clonic; only 27% showed all five, and phase durations varied widely [S104]. **✓ verified** `[K] (M)` (Theodore et al. 1994, *Neurology*; other video series also put the convulsive part of a GTC at ~1–2 min; > 5 min = status epilepticus).
- In the clonic phase, the atonic gaps between jerks **lengthen** until the jerks stop; jerks become slower and larger [S105].
- Focal onset shows as **head/eye version** (away from the focus), unilateral face jerking, mouth deviation, automatisms first; the **figure-of-4** posture (one elbow extended, the other flexed across the chest) lateralises with PPV ~90%, the **extended elbow is contralateral to the focus**; the clonic phase and the ending are often asymmetric [S106]. **✓ verified** `[K] (H)` (Kotagal et al. 2000, *Neurology*: extended elbow contralateral to the epileptogenic zone, PPV ≈ 90%). Version: see the forced-vs-non-forced note under §14.1.

Default game sequence `[E]` on [S104][S105][S106][R1-04 §4.2]:

| Phase | Duration | Body | Eyes / face / sound |
|---|---|---|---|
| Focal onset (if wound-related) | 2–10 s | Contralateral hand/face clonic jerks; head turns away from the wound | Eyes forced away from the wound |
| Tonic | 10–20 s | Stiff; arms flex then extend; figure-of-4 possible; legs extended; trunk arched | **Epileptic cry** (forced groan); jaw clenched; eyes open, deviated or up; pupils dilated; lips turning blue |
| Tremulousness | 2–5 s | Fine, fast vibration of the stiff limbs (8–12 Hz, low amplitude) `[K]` (L) | |
| Clonic | 30–60 s | Rhythmic whole-body jerks, 3–4 Hz slowing to ~1 Hz; gaps lengthen | Grunting on each jerk; frothy saliva, bloody if the tongue is bitten |
| End | — | Final jerk, then limp | Deep stertorous breath; postictal (R1-04 §4.2) |

### 17.3 Focal motor seizures, Jacksonian march, EPC, Todd's paralysis

- **Frontal seizures**: abrupt on/off, asymmetric tonic posturing, **10–40 s**, minimal confusion afterwards; can include loud vocalisation, bizarre movements, incontinence, head and eye deviation [S107].
- **SMA seizures**: fencing-like dystonic arm posture or leg "bicycling", **10–30 s** [S107].
- **Hemifacial clonic**: continuous or bursts of clonic contractions of one side of the face, **seconds to 1 min** [S108].
- **Jacksonian march**: clonic jerking spreads through **contiguous body parts on one side** in homunculus order: fingers → hand → arm → face, or foot → leg → arm → face; consciousness is usually preserved; the classic full march is **rare** [S108][S107]. March speed (not found in the retrieved sources): 5–30 s per homunculus segment `[E]`.
- **Epilepsia partialis continua**: clonic jerking confined to one body part (hand, face, leg) at fairly regular intervals for **> 1 h**, sometimes days; caused by motor-cortex lesions including trauma [S109].
- **Todd's paralysis** (postictal weakness of the seizing side): mean **173 s** (range 11 s – 22 min) in a video-EEG study of focal epilepsies; case reports up to 36–48 h [S110]. **✓ verified** `[K] (M)` (Gallmetzer et al. 2004; the figures match the reviewer's recollection). Fact-check context: those were chronic-epilepsy patients; after a seizure caused by a fresh structural wound, the postictal weakness adds to the lesion deficit and can look permanent.

### 17.4 Catalogue of involuntary movements for animation

| Movement | Cause | Rhythm | Amplitude / distribution | Onset → duration | Source |
|---|---|---|---|---|---|
| Focal clonic jerks | Cortical seizure (motor strip) | 1–5 Hz, regular | 5–30° at a joint; one hand/face side | Seconds–minutes | [S108] `[E]` |
| Jacksonian march | Seizure spreading along M1 | As above | Spreads segment to segment | 10 s – 2 min | [S108] `[E]` |
| EPC | Motor-cortex lesion | 0.5–3 Hz, regular | Small, one body part | > 1 h | [S109] `[E]` |
| GTC clonic | Generalised seizure | 3–4 → 1 Hz | Whole body | 30–60 s | [S105] [R1-04] |
| Syncopal myoclonus | Cerebral hypoperfusion (faint, blood loss) | Arrhythmic, multifocal | Small–moderate, proximal and distal | During 5–20 s of LOC | [S70] |
| Concussive convulsion | Impact | Tonic then myoclonic | Whole body | Starts < 2 s; ≤ 150 s | [S100] |
| Fencing response | Impact (brainstem) | Tonic, no jerks | One arm extended, other flexed | Onset at impact; 2–10 s | [S99] [R1-04] |
| Hemiballismus | STN (and other BG) | Irregular bursts 0.2–1 s | Violent proximal flinging, one side | Minutes–days → weeks | [S25][S26] |
| Intention tremor | Cerebellar hemisphere | 3–5 Hz | Grows near the target | While reaching | [S44] |
| Titubation | Vermis | 2–4 Hz `[K]` (L) | Head/trunk 1–3 cm | While sitting/standing | [S43] |
| Decerebrate / decorticate spasms | Brainstem release, plateau waves | Tonic episodes | §18 | 5–60 s, on stimulus | [S86] [R1-04] |
| Spinal reflex movements after brain death | Spinal cord | Slow, stereotyped (toe undulation, arm flexion/"Lazarus") | Limbs | Minutes–hours after brain death; 13–22% of brain-dead patients | [S113]; fact-check: other prospective series report higher rates (~40–55%) `[K] (M)`, so use p 0.2–0.5 |

### 17.5 Simulation parameters: seizures and movements

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `p_immediate_seizure_penetrating_cortex` | 0.05–0.10 | p in first hour | ×1.5 for motor/temporal cortex | [E] on [S103] |
| `p_immediate_seizure_blunt_contusion` | 0.02–0.04 | p | | [S103] (M), [E] |
| `p_seizure_noncortical` | 0 | p | Brainstem, cerebellum, deep white matter only | [K] (H) |
| `gtc_mean_duration` | 62 (30–120) | s | Phases variable; not all present (27% all five) | [S104] (H) |
| `version_direction` | away from focus (forced version); early non-forced turn either side (p 0.5) | — | Fact-check: only forced, sustained version lateralises | [S65][S106] (H) |
| `figure4_prob` | 0.3–0.5 of focal-to-bilateral seizures | p | Extended elbow contralateral to focus | [S106] (M), [E] |
| `frontal_seizure_duration` | 10–40 | s | | [S107] (M) |
| `jackson_segment_time` | 5–30 | s per segment | Rare full march (p 0.1 of focal motor seizures) | [E] on [S108] |
| `todd_duration` | 173 (11–1320) | s | Tail to 36 h; ✓ verified (fact-check) | [S110] (M) |
| `epc_min_duration` | 3600 | s | | [S109] (M) |

### Visual/behavioural checklist: seizures and movements
- A character shot through the side of the head may, seconds to minutes later, turn its head and eyes hard away from the wound, then its opposite hand and face start jerking, then the whole body stiffens with a groan and convulses for about a minute.
- After the fit, the side that jerked is limp for a few minutes.
- A fit's jerks get slower and farther apart before they stop; they never simply switch off at full speed.
- A faint from pain or bleeding shows a few irregular twitches for 5–15 s, not rhythmic jerking.
- A body declared brain-dead can still curl its toes or flex an arm when moved.

---

## 18. Posturing (joint targets and behaviour; extends [R1-04 §4])

### 18.1 Lesion levels

- **Decorticate** (abnormal flexion, GCS M3): lesion **above the red nucleus** (hemispheres, internal capsule, thalamus); rubrospinal flexion of the arms is unopposed [S111].
- **Decerebrate** (extension, GCS M2): lesion **at or below the red nucleus but above the vestibular nuclei** (midbrain, upper pons); vestibulospinal extensor drive is released [S111].
- **✓ verified** (descriptions and textbook lesion levels) `[K] (H)`. Fact-check nuance `[K] (M)`: the red-nucleus rule comes from animal work; in humans the correlation is loose (decerebrate posturing also occurs with large hemispheric masses, diffuse injury or metabolic coma, and the two can coexist or alternate in one patient). Use lesion level as the default driver but allow either posture with ICP/plateau-wave severity. A lesion **below the vestibular nuclei** (lower pons/medulla) gives **flaccidity**, not posturing.
- Both are often **episodic**, triggered by stimulation (pain, moving the body, noise, suctioning) and by ICP plateau waves [S86] `[K]`. They can be asymmetric (decorticate on one side, decerebrate on the other) [R1-04 §4.1].

### 18.2 Joint targets for the ragdoll drive

Angles from anatomical neutral. `[K]` descriptions per [S111]; numeric ranges `[E]`.

| Joint | Decorticate | Decerebrate | Fencing (arm on the extended side / other side) | Figure-of-4 (seizure) |
|---|---|---|---|---|
| Shoulder | Adducted 0–10° abduction; internal rotation 30–60°; flexion 0–30° (arm against chest) | Adducted 0–10°; **internal rotation 60–90°**; extension 0–20° | Flexion 60–120° (arm raised forward/up), abduction 0–30° / adducted | Extended arm: flexion 30–90°, abduction 20–45° / flexed arm across chest |
| Elbow | **Flexion 90–130°** | **0–10° (straight)** | 0–20° / 90–120° | **0–20°** / 90–130° |
| Forearm | Neutral to 45° pronation | **Full pronation 80–90°** (backs of hands face each other or forward) | Neutral / neutral | Pronated / neutral |
| Wrist | Flexion 45–80° | Flexion 30–70° | Neutral–30° flexion | Flexion 30–60° |
| Fingers / thumb | Fist, MCP 70–90°, thumb tucked | Flexed, fist | Flexed or loosely open | Fist |
| Hip | Extension 0–10°, adduction 10–20° (scissoring), internal rotation 10–30° | Same, stiffer | Varies | Extended |
| Knee | 0–10° | 0–5° | Varies | 0–20° |
| Ankle | Plantar flexion 20–45°, inversion 10–20° | **Plantar flexion 30–45°**, inversion | Varies | Plantar flexion |
| Neck | Neutral to 10° extension | **Extension 10–30°**; opisthotonus 40–60° with lumbar arching +20° | Often rotated toward the extended arm (asymmetric tonic neck reflex) `[K]` | Rotated away from the focus |
| Jaw | Neutral | Clenched (trismus) | Variable | Clenched |
| Drive strength | 50–70% of max | 60–80% of max | 40–70% | 70–90% |

Drive profile `[E]`: ramp-in 0.5–2 s, hold 5–60 s (plateau-wave episodes up to minutes), release 1–3 s; repeat every 30 s – 5 min or on stimulus [R1-04 §4.3]. Progression under herniation: decorticate → decerebrate → flaccid (§15.6).

### 18.3 Telling them apart (for animators)

| Posture | When | Duration | Arms | Distinguishing cue |
|---|---|---|---|---|
| Fencing | At the moment of a knockout blow, consciousness lost | 2–10 s (max ~20 s), once | Asymmetric: one extended up/forward, one flexed | Seen in 66% of 35 analysed knockout videos [S99] ✓ verified (≈ two thirds; same figure in [R1-04 §3.6]); "regardless of the side of impact" **? not re-verified** — fact-check: pick the extended arm from the direction the head is turned after impact (asymmetric-tonic-neck-reflex pattern: arm extends on the face side) and fall back to random if unknown `[K] (L)`; the duration is described only as "seconds" (2–10 s is `[E]`) |
| Figure-of-4 | Tonic phase of a focal-to-bilateral seizure | 10–20 s | One elbow straight, the other bent across the chest | Followed by clonic jerking |
| Decorticate | Coma from hemispheric/diencephalic damage | 5–60 s episodes, repeated | Both arms flexed onto the chest | Legs straight, triggered by touch |
| Decerebrate | Coma with midbrain/upper-pons damage | 5–60 s episodes, repeated | Both arms straight, turned in | Neck arched back, jaw clenched |

### 18.4 Later autonomic storms (paroxysmal sympathetic hyperactivity)

- Episodes of **hypertension, tachycardia, hyperthermia, fast breathing, sweating and extensor or flexor posturing**, first appearing around **day 6** after severe TBI (range: first week); 72% triggered by a stimulus (pain, full bladder, repositioning); episodes rarely last more than several hours [S112]. Associated with DAI and brainstem injury [S114 search summary]. Out of game time except in time skips.

### 18.5 Simulation parameters: posturing

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `posture_joint_targets` | table §18.2 | ° | | [S111] (H) desc., [E] numbers |
| `posture_drive_strength` | decorticate 0.5–0.7, decerebrate 0.6–0.8 | × max | | [E] |
| `posture_ramp` / `hold` / `release` | 0.5–2 / 5–60 / 1–3 | s | | [E] |
| `posture_trigger` | pain, movement, loud noise, plateau wave | — | | [S86] `[K]` (M) |
| `fencing_prob_ko` / `duration` | 0.66 / 2–10 (≤ 20) | p / s | Probability ✓ verified; duration `[E]` | [S99] (M) |
| `psh_onset` | ~6 days | — | Time skips only | [S112] (M) |

### Visual/behavioural checklist: posturing
- Decorticate: fists pulled up to the chest, legs stiff and straight, toes pointed; comes and goes when the body is moved.
- Decerebrate: arms rigid at the sides, rolled inward so the **palms turn outward and backward** (corrected: was "backs of the hands turn out"; internal rotation plus full pronation turns the palm away from the body), wrists and fingers bent, head pushed back, jaw clamped, feet pointed; spasms when touched.
- Fencing: at the instant of a knockout, one arm shoots up stiff, the other bends; it lasts a few seconds, then the body goes limp.

---

## 19. Glasgow Coma Scale: what each level looks like

### 19.1 Components (Teasdale structured approach [S93]) and game mapping

| Score | Eye opening (E) | Verbal (V) | Motor (M) |
|---|---|---|---|
| 6 | — | — | **Obeys** commands (two-step) |
| 5 | — | **Oriented** (name, place, date) | **Localises**: hand moves up to the painful stimulus at head/neck, crossing the midline or above the clavicle |
| 4 | **Spontaneous** | **Confused**: sentences, wrong content | **Normal flexion**: rapid withdrawal from pain |
| 3 | **To sound** | **Words**: intelligible single words | **Abnormal flexion**: slow, stereotyped, decorticate |
| 2 | **To pressure** (pain) | **Sounds**: moans/groans only | **Extension**: decerebrate |
| 1 | None | None | None (flaccid) |

Sources: [S93] for definitions (E/V wording per the 2014 structured approach); motor descriptions [S111][R1-04 §4.1] `[K]`.

Game mapping `[E]`: E from arousal level and lid control (and eyelid swelling from facial wounds, scored "NT" clinically); V from the vocal state (§5.2); M from the best motor response the character could make (§2, §18). Aphasia lowers V without lowering consciousness; locked-in scores E4 (vertical eye opening), V1, M1 despite full awareness `[K] (H)`.

### 19.2 GCS bands

| GCS | Category | What the player sees | Outcome data | Tag |
|---|---|---|---|---|
| 15 | Normal | Alert, oriented | — | [K] |
| 13–14 | Mild TBI | Awake, eyes open; confused, slow, repeats questions; can walk (unsteady) | — | [S97] `[K]` |
| 9–12 | Moderate | Drowsy or stuporous; opens eyes to voice or pain; words or moans; localises or withdraws; cannot stand | — | `[K]` |
| 6–8 | Severe (coma) | Eyes closed or open only to pain; moans or silent; withdraws or postures; snoring/gurgling airway | Severe-TBI (GCS 3–8) mortality ~20–40% across modern cohorts (6-month 19.5% in one validation cohort; hospital 32.8% and 6-month 40% in others) | `[K]`, [S122] (M) |
| 4–5 | Severe | No eye opening; silent or single moan; decorticate/decerebrate spasms | — | `[K]` |
| 3 | Deepest | Flaccid, eyes closed or fixed open, no sound | Mortality 51% at GCS 3 in pooled IMPACT/CRASH data; **74% at GCS-P 1** (GCS 3 with both pupils unreactive) | [S92] (M) — fact-check: GCS-P definition ✓ verified; percentages not re-verified |

- **GCS-P** = GCS minus pupil reactivity score (2 = both unreactive, 1 = one unreactive, 0 = both react); range 1–15 **✓ verified** `[K] (H)`; mortality falls continuously from the bottom to the top of the scale [S92]. **Corrected: was "from 79% at the bottom to 14% at the top"**, which contradicted the 74% at GCS-P 1 given in the row above (and the survival 0.21 in §19.3). Fact-check uses **74%** at GCS-P 1 throughout (the value in the table and in the claim list); the top-of-scale value is not re-verified and is omitted.
- The ICH example: bleed ≥ 60 cm³ with GCS ≤ 8 → 91% 30-day mortality [S94].

### 19.3 Simulation parameters: GCS

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `gcs_e/v/m` | computed per tick at 2–5 Hz | — | Store best-response values | [E] |
| `gcs_p` | GCS − PRS | 1–15 | | [S92] (H) |
| `survival_from_gcsp` | 0.26 at GCS-P 1 rising to ~0.85–0.95 at the top of the scale | p | Only if the game resolves "would survive" outcomes. **Corrected: was 0.21 at GCS-P 1 and 0.86 at 15** (0.21 contradicted the 74% mortality quoted in §19.2; top value not re-verified, range `[E]`). These are **treated** (hospital) outcomes; with no medical care in game, scale survival down | [S92] (M), [E] |

### Visual/behavioural checklist: GCS
- GCS 13–14: talking nonsense-adjacent, asking again and again, walking like a drunk.
- GCS 9–12: eyes flutter open when shouted at or hurt, mumbles a word or moans, pushes the player's hand away.
- GCS 6–8: eyes shut, groans when hurt, pulls a limb away or stiffens.
- GCS 3–5: nothing except spasms of stiffening; snoring or gurgling breathing, if any.

---
## 20. Putting it together: the lesion resolver

### 20.1 Region list and hit volumes

Approximate volumes for a 1,300–1,400 g adult brain. Lobe shares of cerebral cortex: frontal 41%, temporal 22%, parietal 19%, occipital 18% [S38]; cerebellum ~10% of brain volume [S38]. Everything else `[K]` (M) or `[E]`.

| Region ID (per side unless midline) | Volume (cm³) | Channel(s) it drives |
|---|---|---|
| `M1_leg`, `M1_trunk`, `M1_arm`, `M1_hand`, `M1_face`, `M1_bulbar` | 15–25 total strip | Contra strength per segment (§2) |
| `SMA`, `PMC`, `FEF` | 8–12, 10–15, 2–4 | Initiation, proximal strength, gaze bias (§3) |
| `PFC_dl`, `PFC_orb`, `ACC` | 40–60, 20–30, 5–8 | Response latency, perseveration, disinhibition, abulia (§4) |
| `Broca_ext` (with insula/WM), `Wernicke` | 5–10, 5–10 | Vocal state (§5), dominant side only |
| `S1`, `PPC` | 10–15, 30–50 | Sensation, neglect, reaching (§6) |
| `V1_upper`, `V1_lower`, `V1_pole`, `optic_radiation` | 5–8 each bank | Visual field mask (§7) |
| `temporal_lat`, `hippocampus`, `amygdala` | 60–80, 3.5–4, 1.5–2 | Language (left), memory, fear, seizure mult. (§8) |
| `caudate`, `putamen`, `GP`, `STN` | ~4, ~5, 1.5–2, 0.15–0.2 | Drive, hemiplegia (with capsule), ballism (§9) |
| `thal_lateral`, `thal_paramedian` | ~5, ~2 | Sensation, astasia, arousal, eyes down-in (§10) |
| `IC_ant`, `IC_genu`, `IC_post` | 1–2, 0.5–1, 2–4 | Dense hemiplegia (§11) |
| `corpus_callosum` (midline) | 15–20 | Disconnection; transventricular-track marker (§11) |
| `cb_hemi`, `vermis`, `flocculonodular` | 55–65, 10–15, 2–3 | Ipsi ataxia, trunk balance, nystagmus (§12) |
| `midbrain_ventral`, `midbrain_tegmentum`, `midbrain_tectum` | ~7 total | CN III, Weber/Parinaud, consciousness (§13.1) |
| `pons_basis`, `pons_tegmentum` | ~15 total | CN VI/VII, gaze, locked-in, consciousness (§13.2) |
| `medulla_lateral`, `medulla_medial` | ~6–7 total | Swallow, voice, Horner, tongue, breathing (§13.3) |
| `hypothalamus_pituitary` (midline) | ~4 | Temperature, water balance (§20.4) |
| `optic_nerve`, `chiasm`, `CN_III`, `CN_VI` (extra-axial) | small | Blindness of one eye, bitemporal loss, ocular palsies |

### 20.2 Resolver rules `[E]`

1. **Damage.** For each region r: `destroyed_r` = destroyed volume / region volume (0–1), from the wound track (permanent cavity) of [R1-01].
2. **Stun.** Add concussive dysfunction for regions inside the stun radius around the track (≥ 18 mm for low-energy handgun tracks [R1-01 §6]; larger for higher energy): `stun_r` = 0.5–1.0, decaying with a half-life of 30 s – 10 min to a residual 0–0.3. **Myth guard (fact-check) `[K] (M)`:** this radius applies to tracks **inside the skull**. Do not add brain stun for hits elsewhere on the body ("hydrostatic shock" / remote pressure-wave incapacitation): remote brain effects of torso hits are reported in animal experiments but are not an established cause of instant human incapacitation; torso hits cause collapse through blood loss, spinal-cord hits, pain/psychological response or syncope (§14.6), not remote brain injury.
3. **Ischaemia.** If the track cuts a named artery (MCA, ACA, PCA branch, basilar perforators), its territory gains `isch_r` rising to 1 over 10–20 s (brain function fails below ~20 mL/100 g/min [R1-04 §1]); in game time it never recovers.
4. **Compression.** From §15 (mass, midline shift, herniation stage) add `comp_r` to the diencephalon and brainstem regions and to CN III on the mass side.
5. **Dysfunction** `d_r(t) = clamp(destroyed_r + stun_r(t) + isch_r(t) + comp_r(t), 0, 1)`.
6. **Severity** `sev_r = smoothstep(visible_at_r, full_at_r, d_r)` using the thresholds in §1 and each section; multiply by a per-character factor 0.85–1.15.
7. **Side mapping.** Cortex, basal ganglia, thalamus, capsule, cerebral peduncle, corticospinal tracts in pons and upper medulla → contralateral body channels. Cerebellum → ipsilateral body. Cranial-nerve nuclei and nerves → ipsilateral eye/face/tongue/voice. Language regions → dominant side only (90% left). Fact-check exceptions (see §0.4 rule 1) `[K] (H)`: CN IV nucleus/fascicle → contralateral superior oblique; CN III nucleus → contralateral superior rectus + bilateral ptosis; midbrain cerebellar-outflow (red nucleus / decussated superior cerebellar peduncle) → contralateral ataxia; corticospinal tract **at or below** the pyramidal decussation (lowest medulla, cervical cord) → ipsilateral weakness.
8. **Combine** channels by taking the maximum severity of any region driving that channel (a leg paralysed by the capsule is not made "more paralysed" by M1 as well).
9. **Probabilistic signs** (neglect, anosognosia, pusher, ballism, seizure, Kernohan, wrong-way eyes) are rolled once, when the region's severity first crosses its threshold, with the probabilities given in the sections.
10. **Consciousness** is resolved last (rule 2 in §0.4, [R1-04 §3.1]) and overrides behaviour: an unconscious character shows only reflexes, posturing, eye signs and breathing patterns.
11. **Blunt force** (hammer, punch, fall) has no track: apply stun to the region under the impact (coup) and to the frontal and temporal poles, plus the opposite pole for occipital or lateral blows (contrecoup) `[K] (H)`; add EDH risk for temporal-squama fractures (§15.2) and DAI for rotational blows (§11). **Fact-check refinement `[K] (H)`:** which side bruises depends on whether the head was **moving** or **still**. A **moving head that stops** against the floor or a wall (fall, being thrown) gives the classic **contrecoup** pattern: contusions opposite the impact, worst in the frontal and temporal poles, typically larger than the coup lesion. A **still head struck by an object** (hammer, bat, punch to a braced head) gives mainly **coup** injury under the impact point (with a depressed fracture if the contact area is small) and little contrecoup. Scale coup and contrecoup weights by head velocity at impact vs object velocity.

### 20.3 How the body goes down, by deficit (for the fall controller)

| Deficit | Direction | Speed | Protective reaction | Notes | Tag |
|---|---|---|---|---|---|
| Loss of consciousness (concussion, brainstem) | Direction of existing lean/momentum | 0.6–1.2 s to the ground | None | [R1-04 §2.3] | [R1-04] |
| Acute hemiplegia (M1 leg, capsule) | **Toward the paralysed side** | Paralysed knee buckles 0.2–0.6 s after load; topple 0.8–1.5 s | Good arm reaches out if conscious | Head may still hit on the paralysed side | [K] / [E] |
| Pusher syndrome | Toward the paralysed side, actively pushed by the good limbs | 1–3 s | Resists being righted | Right-hemisphere lesions more often | [S20] |
| Cerebellar hemisphere | **Toward the lesion side** | Staggers 2–5 wide steps first | Grabs at walls and objects | Often recovers balance once or twice | [S39][S41] |
| Vermis | Any direction, often backward | Sways, then topples | Arms flail for balance | Cannot sit | [S43] |
| Thalamic astasia | **Backward or away from the lesion side** | Topples from standing or sitting | Present | Strength near normal | [S30] |
| Lateral medulla | Pulled sideways **toward the lesion** | Progressive lean | Present | Vertigo, vomiting | [S58][S59] |
| Seizure (tonic) | Stiff, "like a log", often backward | 0.5–1 s | None | Epileptic cry at onset | [R1-04 §4] `[K]` |
| Syncope | Crumples at knees and hips | 1–2 s | None | Eyes open, jerks | [S70] |
| Abulia / akinetic | Does not fall; stays frozen standing or sitting | — | — | May slowly sink into a chair | [S9] |

### 20.4 Other targets the resolver should know

- **Hypothalamus / pituitary stalk** (midline, above the sella): early **central diabetes insipidus** (large dilute urine output) usually in the first days, sometimes within hours; associated with high mortality when very early; central hyperthermia [S115]. Game: body temperature rising 0.5–1 °C/h and wet trousers (polyuria) over hours `[E]`.
- **Optic nerve** (orbit, optic canal): blindness of that eye with an afferent pupil defect (the pupil reacts to light shone in the other eye but not in this one) `[K] (H)`. **Chiasm**: loss of both outer half-fields `[K] (H)`. A temple-to-temple track through both orbits blinds both eyes [R1-04 §3.3].
- **Olfactory tracts** (frontal base): anosmia (§4.3).

### 20.5 Performance note

The resolver runs **on wound events only** (a few hundred operations per hit). Continuous processes (ICP/mass integration, herniation stage, seizure timer, nystagmus/roving/bobbing generators, posturing episodes) run in the 20 Hz physiology tick of [R1-04 §0.4] and cost a handful of floats each. Eye movement generators should be evaluated per rendered frame only for characters on screen `[E]`.

### Visual/behavioural checklist: integration
- The same bullet produces different characters depending on where it went: a limp arm and a sagging mouth; a drunk-looking stagger toward the wound; a staring, silent statue; a thrashing arm; crossed eyes and a pinpoint coma.
- Slow killers (haematoma, swelling) turn a talking, walking character into a posturing, blown-pupil coma over tens of minutes; the eyes and breathing tell the player it is happening before the body stops moving.

---

## 21. QA priority list (open the source and confirm before hard-coding)

1. Conjugate eye deviation magnitude and incidence [S63]; FEF deviation duration [S64].
2. Wallenberg sign frequencies [S58].
3. Ocular bobbing kinematics and rate [S54]; ocular dipping timing [S55].
4. Ropper midline-shift thresholds [S84].
5. EDH lucid-interval frequency and timing [S76][S77]; EDH/ASDH mortality [S78][S80][S81].
6. GCS-P and pupil-reactivity mortality [S92].
7. Post-traumatic seizure incidences and the conflicting "50% immediate" summary [S103].
8. Neglect and anosognosia percentages [S17][S19]; pusher incidence [S20].
9. CN III squint sizes [S50].
10. Author-only numbers most worth checking: gait metrics (§12.2), eye-rig numbers (§14.8), central-herniation stage durations (§15.6), EDH bleed rate (§15.2), Jacksonian march speed (§17.3), posture joint angles (§18.2).
11. Added by fact-check (items it could not re-verify without search): Wallenberg hoarseness/dysphagia shares [S58]; conjugate-deviation percentages and the 14–15° cut-off [S63]; cerebellar 75% nystagmus / 71% cannot-walk [S41]; pupil-reactivity and GCS-P percentages [S92][S89]; the "100% mortality" track subgroups [S95]; Cushing CPP < 15 mmHg threshold [S85]; fencing-response side [S99]; hand-knob numbers [S34][S35].

---

## 22. References

- **[S1]** Onset, time course and prediction of spasticity after stroke or traumatic brain injury. https://www.sciencedirect.com/science/article/pii/S1877065718300599
- **[S2]** Sommerfeld D.K. et al. Spasticity after stroke. *Stroke* 2004. https://www.ahajournals.org/doi/10.1161/01.str.0000105386.05173.5e
- **[S3]** Li S. Spasticity, motor recovery, and neural plasticity after stroke. *Front Neurol* 2017. https://www.frontiersin.org/journals/neurology/articles/10.3389/fneur.2017.00120/full
- **[S4]** Insights from the supplementary motor area syndrome in balancing movement initiation and inhibition. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4246659/
- **[S5]** Supplementary motor area syndrome after brain tumor surgery: a systematic review. https://www.sciencedirect.com/science/article/abs/pii/S1878875022008658
- **[S6]** Anterior cerebral artery stroke syndromes (MedLink). https://www.medlink.com/articles/anterior-cerebral-artery-stroke-syndromes
- **[S7]** Frontal lobe syndrome (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK532981/
- **[S8]** Frontal lobe motor syndromes (Handb Clin Neurol). https://pubmed.ncbi.nlm.nih.gov/37620084/
- **[S9]** On the pathophysiology and treatment of akinetic mutism. https://www.sciencedirect.com/science/article/pii/S0149763419301447 ; Akinetic mutism overview https://www.sciencedirect.com/topics/medicine-and-dentistry/akinetic-mutism
- **[S10]** Bhatia K.P., Marsden C.D. The behavioural and motor consequences of focal lesions of the basal ganglia in man. *Brain* 1994. https://pubmed.ncbi.nlm.nih.gov/7922471/ ; Movement disorders following cerebrovascular lesion in the basal ganglia circuit https://pmc.ncbi.nlm.nih.gov/articles/PMC4886205/
- **[S11]** Areas of brain damage underlying increased reports of behavioral disinhibition. https://psychiatryonline.org/doi/10.1176/appi.neuropsych.14060126
- **[S12]** Wernicke aphasia (StatPearls). https://www.ncbi.nlm.nih.gov/sites/books/NBK441951/
- **[S13]** Associations between lesion size, lesion location and aphasia in acute stroke. https://www.tandfonline.com/doi/full/10.1080/02687038.2020.1727838 ; The neuroanatomy of Broca's aphasia https://www.frontiersin.org/journals/language-sciences/articles/10.3389/flang.2025.1496209/full
- **[S14]** Neuroanatomy, Broca area (StatPearls). https://www.ncbi.nlm.nih.gov/sites/books/NBK526096/ ; Wernicke's area https://en.wikipedia.org/wiki/Wernicke%27s_area
- **[S15]** Variations in the presentation of aphasia in patients with closed head injuries. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC2831203/ ; Cerebellar mutism following head trauma https://surgicalneurologyint.com/surgicalint-articles/cerebellar-mutism-following-head-trauma-a-case-report-and-literature-review/
- **[S16]** Scanning dysarthria (GPnotebook). https://gpnotebook.com/pages/neurology/scanning-dysarthria
- **[S17]** Ringman J.M. et al. Frequency, risk factors, anatomy, and course of unilateral neglect in an acute stroke cohort. *Neurology* 2004. https://www.neurology.org/doi/10.1212/01.WNL.0000133011.10689.CE
- **[S18]** Unilateral spatial neglect due to stroke (NCBI Bookshelf). https://www.ncbi.nlm.nih.gov/books/NBK572008/
- **[S19]** Anosognosia for hemiplegia as a tripartite disconnection syndrome. *eLife* 2019. https://elifesciences.org/articles/46075
- **[S20]** Research progress in pusher syndrome after stroke. https://pmc.ncbi.nlm.nih.gov/articles/PMC12040677/ ; Prevalence and length of recovery of pusher syndrome by lesion side https://www.ahajournals.org/doi/10.1161/STROKEAHA.111.638379
- **[S21]** Astereognosis (StatPearls). https://www.ncbi.nlm.nih.gov/sites/books/NBK560773/ ; Parietal lobe overview https://www.sciencedirect.com/topics/neuroscience/parietal-lobe
- **[S22]** Cortical blindness (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK560626/
- **[S23]** Cortical blindness (MedLink). https://www.medlink.com/articles/cortical-blindness
- **[S24]** Hemianopsia (Moran CORE). https://morancore.utah.edu/basic-ophthalmology-review/hemianopsia/
- **[S25]** Hemiballism (MedLink). https://www.medlink.com/articles/hemiballism ; Hemiballismus: current concepts and review https://www.sciencedirect.com/science/article/abs/pii/S1353802011002690
- **[S26]** Hemiballismus (StatPearls). https://www.ncbi.nlm.nih.gov/sites/books/NBK559127/ ; Neurophysiological features of hemiballism https://pmc.ncbi.nlm.nih.gov/articles/PMC6353509/ ; Acute caudate nucleus stroke presenting as hemiballismus https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10693717/
- **[S27]** Basal ganglia hemorrhage (MedLink). https://www.medlink.com/articles/basal-ganglia-hemorrhage
- **[S28]** The syndrome of bilateral paramedian thalamic infarction. https://pubmed.ncbi.nlm.nih.gov/6682494/ ; Bilateral thalamic stroke from artery of Percheron occlusion https://www.ncbi.nlm.nih.gov/pmc/articles/PMC6059518/
- **[S29]** Wrong-way eyes with thalamic hemorrhage. *Neurology* 2003. https://www.neurology.org/doi/10.1212/01.WNL.0000065900.62880.4F
- **[S30]** Masdeu J.C., Gorelick P.B. Thalamic astasia: inability to stand after unilateral thalamic lesions. *Ann Neurol* 1988. https://pubmed.ncbi.nlm.nih.gov/2841901/
- **[S31]** Pure motor stroke as the most frequent lacunar syndrome: a clinical update. https://www.wjgnet.com/2218-6212/full/v3/i4/129.htm ; Lacunar stroke (Medscape) https://emedicine.medscape.com/article/322992-overview
- **[S32]** Zhu L.L. et al. Lesion load of the corticospinal tract predicts motor impairment in chronic stroke. *Stroke* 2010. https://www.ahajournals.org/doi/10.1161/strokeaha.109.577023 ; Feng W., Schlaug G. et al. Corticospinal tract lesion load: an imaging biomarker for stroke motor outcomes https://musicianbrain.com/papers/Feng_Schlaug_CorticospinalTractLesionLoad_AnImagingBiomarkerforStrokeMotorOutcome.pdf
- **[S33]** Cortical hand knob stroke: report of 25 cases. https://www.sciencedirect.com/science/article/abs/pii/S1052305718301071
- **[S34]** Yousry T.A. et al. Localization of the motor hand area to a knob on the precentral gyrus. *Brain* 1997. https://pubmed.ncbi.nlm.nih.gov/9055804/ ; Use of a brain navigator to identify the precentral knob https://pubmed.ncbi.nlm.nih.gov/35039469/
- **[S35]** Roux F.E. et al. Functional architecture of the motor homunculus detected by electrostimulation. *J Physiol* 2020. https://physoc.onlinelibrary.wiley.com/doi/abs/10.1113/JP280156 ; Modern coordinates for the motor homunculus https://pmc.ncbi.nlm.nih.gov/articles/PMC8033533/
- **[S36]** Analysis of upper facial weakness in central facial palsy following acute ischemic stroke. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11767383/
- **[S37]** Pronator drift (Neurosigns). https://www.neurosigns.org/pronator-drift.html ; Objective pronator drift test (PLOS One) https://journals.plos.org/plosone/article?id=10.1371%2Fjournal.pone.0041544
- **[S38]** Brain facts and figures (Kennedy et al. 1998 lobe volumes). https://faculty.washington.edu/chudler/facts.html
- **[S39]** Cerebellar neurological signs (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK556080/
- **[S40]** Cerebellar hemorrhage (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK541076/
- **[S41]** Diagnosis and management of acute cerebellar infarction. *Stroke* 2014. https://www.ahajournals.org/doi/10.1161/STROKEAHA.114.004474
- **[S42]** A systematic review of the gait characteristics associated with cerebellar ataxia. https://pubmed.ncbi.nlm.nih.gov/29220753/ ; Stolze H. et al. Typical features of cerebellar ataxic gait https://pubmed.ncbi.nlm.nih.gov/12185166/
- **[S43]** Evaluation of cerebellar ataxic patients. https://pmc.ncbi.nlm.nih.gov/articles/PMC10354692/ ; Truncal ataxia https://en.wikipedia.org/wiki/Truncal_ataxia
- **[S44]** Holmes tremor (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK562149/ ; Intention tremor https://en.wikipedia.org/wiki/Intention_tremor
- **[S45]** Nystagmus (EyeWiki). https://eyewiki.org/Nystagmus ; Incidence and anatomy of gaze-evoked nystagmus in patients with cerebellar lesions https://www.neurology.org/doi/10.1212/WNL.0b013e318208f4c3
- **[S46]** Nystagmus types (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK539711/ ; Upbeat nystagmus: clinicoanatomical correlations in 15 patients https://www.thejcn.com/DOIx.php?id=10.3988%2Fjcn.2006.2.1.58 ; Periodic alternating nystagmus in isolated nodular infarction https://pubmed.ncbi.nlm.nih.gov/17372136/ ; See-saw nystagmus in a sellar/suprasellar mass https://journals.lww.com/jneuro-ophthalmology/fulltext/2024/09000/see_saw_nystagmus_in_a_case_of_sellar_suprasellar.96.aspx
- **[S47]** Weber syndrome (StatPearls). https://www.ncbi.nlm.nih.gov/sites/books/NBK559158/ ; Benedikt syndrome https://en.wikipedia.org/wiki/Benedikt_syndrome
- **[S48]** Parinaud syndrome (EyeWiki). https://eyewiki.org/Parinaud_Syndrome
- **[S49]** Acquired oculomotor nerve palsy (EyeWiki). https://eyewiki.org/Acquired_Oculomotor_Nerve_Palsy ; Third cranial nerve disorders (Merck) https://www.merckmanuals.com/professional/neurologic-disorders/neuro-ophthalmologic-and-cranial-nerve-disorders/third-cranial-nerve-oculomotor-disorders
- **[S50]** Clinical features and outcomes of strabismus treatment in third cranial nerve palsy during a 10-year period. https://pmc.ncbi.nlm.nih.gov/articles/PMC4307654/ ; Long term outcomes of strabismus surgery for third nerve palsy https://www.sciencedirect.com/science/article/pii/S1888429618300992 ; Lateral rectus–medial rectus union https://pubmed.ncbi.nlm.nih.gov/30371913
- **[S51]** Abducens nerve palsy (EyeWiki). https://eyewiki.org/Abducens_Nerve_Palsy ; Transient bilateral sixth nerve palsy after head trauma https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7894221/
- **[S52]** One-and-a-half syndrome (EyeWiki). https://eyewiki.org/One_And_a_Half_Syndrome
- **[S53]** Millard-Gubler syndrome (EyeWiki). https://eyewiki.org/Millard-Gubler_Syndrome ; Foville syndrome (EyeWiki) https://eyewiki.org/Foville_Syndrome
- **[S54]** Pendular oscillation and ocular bobbing after pontine hemorrhage. *Cerebellum* 2019. https://link.springer.com/article/10.1007/s12311-019-01086-6 ; Ocular bobbing (MedLink media) https://www.medlink.com/media/85178490
- **[S55]** Other involuntary eye movements (Canadian Neuro-ophthalmology Group textbook). https://www.neuroophthalmology.ca/textbook/disorders-of-eye-movements/xii-other-involuntary-eye-movements
- **[S56]** Locked-in syndrome (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK559026/
- **[S57]** Brainstem hemorrhage (MedLink). https://www.medlink.com/articles/brainstem-hemorrhage ; Management of brainstem haemorrhages (Swiss Med Wkly) https://smw.ch/index.php/smw/article/download/2602/4110?inline=1
- **[S58]** Kim J.S. Pure lateral medullary infarction: clinical–radiological correlation of 130 acute, consecutive patients. *Brain* 2003. https://academic.oup.com/brain/article-pdf/126/8/1864/874738/awg169.pdf
- **[S59]** Lateral medullary syndrome (StatPearls). https://www.ncbi.nlm.nih.gov/sites/books/NBK551670/ ; Dysphagia caused by lateral medullary infarction https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3473978/
- **[S60]** Medial medullary syndrome: report of 18 new patients and a review of the literature. https://pubmed.ncbi.nlm.nih.gov/7660396/
- **[S61]** Skew deviation (EyeWiki). https://eyewiki.org/Skew_Deviation ; Brodsky M.C. et al. Skew deviation revisited https://www.surveyophthalmol.com/article/S0039-6257(05)00214-6/fulltext ; Ocular tilt reaction (EyeRounds) https://eyerounds.org/cases/200-OTR.htm
- **[S62]** Internuclear ophthalmoplegia (EyeWiki). https://eyewiki.org/Internuclear_Ophthalmoplegia ; Wall-eyed bilateral INO https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10147486/
- **[S63]** CT assessment of conjugate eye deviation in acute stroke. *Neurology* 2003. https://www.neurology.org/doi/10.1212/01.WNL.0000042086.98735.75 ; Conjugate eye deviation in acute stroke: incidence, hemispheric asymmetry, and lesion pattern. *Stroke* 2006 https://www.ahajournals.org/doi/10.1161/01.str.0000244809.67376.10
- **[S64]** Conjugate eye deviation with head version due to a cortical infarction of the frontal eye field. *Stroke* 2002. https://www.ahajournals.org/doi/10.1161/str.33.2.642 ; Contralateral gaze deviation after frontal lobe haemorrhage https://pmc.ncbi.nlm.nih.gov/articles/PMC1028190/
- **[S65]** Wyllie E. et al. The lateralizing significance of versive head and eye movements during epileptic seizures. *Neurology* 1986. https://pubmed.ncbi.nlm.nih.gov/3703259/ ; Lateralizing significance of head and eye deviation in secondary generalized tonic-clonic seizures https://www.neurology.org/doi/10.1212/WNL.43.7.1308
- **[S66]** Eye movements in coma (LITFL). https://litfl.com/eye-movements-in-coma/ ; Neuro-ophthalmic findings in coma (EyeWiki) https://eyewiki.org/Neuro-ophthalmic_Findings_in_Coma
- **[S67]** Ping-pong gaze: bouncing back from structural brain damage. *J Neuro-Ophthalmol* 2024. https://journals.lww.com/jneuro-ophthalmology/fulltext/2024/03000/ping_pong_gaze__bouncing_back_from_structural.87.aspx
- **[S68]** Doll's eyes (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK551716/
- **[S69]** Bell's phenomenon. https://en.wikipedia.org/wiki/Bell%27s_phenomenon ; Eye movements, coma and pseudocoma (LITFL) https://litfl.com/eye-movements-coma-and-pseudocoma/
- **[S70]** Lempert T. et al. Syncope: a videometric analysis of 56 episodes of transient cerebral hypoxia. *Ann Neurol* 1994. https://onlinelibrary.wiley.com/doi/10.1002/ana.410360217 ; The eye movements of syncope https://pubmed.ncbi.nlm.nih.gov/8780096/
- **[S71]** Epileptic nystagmus (Epileptic Disorders). http://www.jle.com/en/revues/epd/e-docs/epileptic_nystagmus_272124/article.phtml?tab=texte
- **[S72]** Horner syndrome (EyeWiki). https://eyewiki.org/Horner_Syndrome
- **[S73]** Pupillometry in brain death: differences in pupillary diameter between paediatric and adult subjects. https://pubmed.ncbi.nlm.nih.gov/26184095/
- **[S74]** Hutchinson's pupil. https://en.wikipedia.org/wiki/Hutchinson%27s_pupil ; Fixed and dilated: the history of a classic pupil abnormality https://pubmed.ncbi.nlm.nih.gov/25415062/
- **[S75]** Pupillometry and pupillary abnormalities (EMCrit IBCC). https://emcrit.org/ibcc/pupil/
- **[S76]** Lucid interval (ScienceDirect Topics). https://www.sciencedirect.com/topics/medicine-and-dentistry/lucid-interval
- **[S77]** Progressive epidural hematoma in patients with head trauma: incidence, outcome, and risk factors. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC3536037/
- **[S78]** Epidural hematoma (Medscape). https://emedicine.medscape.com/article/1137065-overview
- **[S79]** Bullock M.R. et al. Surgical management of acute epidural hematomas. *Neurosurgery* 2006. https://pubmed.ncbi.nlm.nih.gov/16710967/
- **[S80]** Seelig J.M. et al. Traumatic acute subdural hematoma: major mortality reduction in comatose patients treated within four hours. *NEJM* 1981. https://www.nejm.org/doi/full/10.1056/NEJM198106183042503
- **[S81]** Wilberger J.E. et al. Acute subdural hematoma: morbidity, mortality, and operative timing. *J Neurosurg* 1991. https://pubmed.ncbi.nlm.nih.gov/1988590/
- **[S82]** Reilly P.L. et al. Patients with head injury who talk and die. *Lancet* 1975. https://www.sciencedirect.com/science/article/abs/pii/S0140673675928937 ; The "talk and die" phenomenon in TBI: a meta-analysis https://www.sciencedirect.com/science/article/abs/pii/S0303846722001433
- **[S83]** Contusion progression following traumatic brain injury: a review. *Neurocrit Care* 2020. https://link.springer.com/article/10.1007/s12028-020-00994-4
- **[S84]** Ropper A.H. Lateral displacement of the brain and level of consciousness in patients with an acute hemispheral mass. *NEJM* 1986. https://doi.org/10.1056/nejm198604103141504
- **[S85]** Cushing reflex (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK549801/
- **[S86]** Intracranial pressure (LITFL Part One). https://partone.litfl.com/intracranial_pressure.html ; Intracranial pressure waveform (IntechOpen) https://www.intechopen.com/chapters/73580
- **[S87]** Rostrocaudal deterioration (Stroke Manual). https://www.stroke-manual.com/rostro-caudal-deterioration/ ; Brain herniation (Deranged Physiology) https://derangedphysiology.com/main/required-reading/neurological-intensive-care/Chapter-1162/brain-herniation
- **[S88]** Kernohan-Woltman notch phenomenon (LITFL). https://litfl.com/kernohan-woltman-notch-phenomenon/
- **[S89]** Clusmann H. et al. Fixed and dilated pupils after trauma, stroke, and previous intracranial surgery. *JNNP* 2001. https://neuroptics.com/wp-content/uploads/2017/02/Clusmann-H-Schaller-C-Schramm-J.-J-Neurol-Neurosurg-Psychiatry-2001.pdf ; Are bilaterally fixed and dilated pupils the kiss of death? https://www.sciencedirect.com/science/article/abs/pii/S187887502200571X ; The dilated pupil and brain herniation (ACNR) https://acnr.co.uk/articles/the-dilated-pupil-and-brain-herniation/
- **[S90]** Brain herniation (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK542246/ ; Tonsillar herniation (StatPearls) https://www.ncbi.nlm.nih.gov/books/NBK562170/
- **[S91]** Duret hemorrhages (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK560495/
- **[S92]** Brennan P.M. et al. Simplifying the use of prognostic information in traumatic brain injury. Part 1: the GCS-Pupils score. *J Neurosurg* 2018. https://pubmed.ncbi.nlm.nih.gov/29631516/
- **[S93]** The Glasgow structured approach to assessment of the Glasgow Coma Scale. https://www.glasgowcomascale.org/
- **[S94]** Broderick J.P. et al. Volume of intracerebral hemorrhage: a powerful and easy-to-use predictor of 30-day mortality. *Stroke* 1993. https://pubmed.ncbi.nlm.nih.gov/8322400/
- **[S95]** Predictors of outcome in civilians with gunshot wounds to the head upon presentation. *J Neurosurg* 2014. https://pubmed.ncbi.nlm.nih.gov/24995781/ ; Analysis of ballistic trajectories and clinical outcomes in civilian penetrating brain injury https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11599325/
- **[S96]** Respiratory rate and pattern disturbances in acute brain stem infarction. *Stroke* 1976. https://www.ahajournals.org/doi/pdf/10.1161/01.str.7.4.382 ; Disordered breathing in severe cerebral illness: towards a conceptual framework https://www.sciencedirect.com/science/article/pii/S1569904822000283
- **[S97]** Sport Concussion Assessment Tool 6 (Physiopedia). https://www.physio-pedia.com/Sport_Concussion_Assessment_Tool_6_(SCAT6) ; On-field motor incoordination and recovery after concussion https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7956999/
- **[S98]** How can a punch knock you out? https://pmc.ncbi.nlm.nih.gov/articles/PMC7649325/
- **[S99]** Hosseini A.H., Lifshitz J. Brain injury forces of moderate magnitude elicit the fencing response. *Med Sci Sports Exerc* 2009. https://pmc.ncbi.nlm.nih.gov/articles/PMC11421656/
- **[S100]** McCrory P.R. et al. Concussive convulsions: incidence in sport and treatment recommendations. https://pubmed.ncbi.nlm.nih.gov/9519401/ ; Video analysis of acute motor and convulsive manifestations in sport-related concussion https://www.neurology.org/doi/10.1212/WNL.54.7.1488
- **[S101]** Post-traumatic vomiting incidence (search summary; exact paper not identified; candidate URLs from the result list): https://pmc.ncbi.nlm.nih.gov/articles/PMC1736317 ; https://pubmed.ncbi.nlm.nih.gov/29599113/
- **[S102]** Vision and concussion: symptoms, signs, evaluation, and treatment (AAO 2022). https://www.aao.org/education/clinical-statement/vision-concussion-symptoms-signs-evaluation-treatm
- **[S103]** Post-traumatic seizure (ScienceDirect Topics). https://www.sciencedirect.com/topics/medicine-and-dentistry/post-traumatic-seizure ; Annegers J.F. et al. A population-based study of seizures after traumatic brain injuries. *NEJM* 1998 https://www.nejm.org/doi/full/10.1056/NEJM199801013380104
- **[S104]** Theodore W.H. et al. The secondarily generalized tonic-clonic seizure: a videotape analysis. *Neurology* 1994. https://pubmed.ncbi.nlm.nih.gov/8058138/
- **[S105]** Tonic clonic seizure (ScienceDirect Topics). https://www.sciencedirect.com/topics/pharmacology-toxicology-and-pharmaceutical-science/tonic-clonic-seizure
- **[S106]** Focal to bilateral tonic-clonic seizures (MedLink). https://www.medlink.com/articles/focal-to-bilateral-tonic-clonic-seizures ; Semiology of focal- vs generalized-onset bilateral tonic-clonic seizures: systematic review https://pubmed.ncbi.nlm.nih.gov/33556863/
- **[S107]** ILAE seizure descriptions: motor seizure https://www.epilepsydiagnosis.org/seizure/motor-overview.html ; frontal lobe seizure https://www.epilepsydiagnosis.org/seizure/frontal-lobe-overview.html
- **[S108]** Jacksonian seizures (MedLink). https://www.medlink.com/articles/jacksonian-seizures ; Focal clonic seizures (MedLink) https://www.medlink.com/articles/focal-clonic-seizures
- **[S109]** Epilepsia partialis continua (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK532275/
- **[S110]** Gallmetzer P. et al. Postictal paresis in focal epilepsies: incidence, duration, and causes. *Neurology* 2004. https://www.neurology.org/doi/abs/10.1212/WNL.62.12.2160 ; Frequency and pathophysiology of post-seizure Todd's paralysis https://pmc.ncbi.nlm.nih.gov/articles/PMC7075081/
- **[S111]** Decerebrate and decorticate posturing (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK559135/
- **[S112]** Paroxysmal sympathetic hyperactivity after traumatic brain injury: what is important to know? https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9161703/ ; Identification and management of PSH after TBI https://www.ncbi.nlm.nih.gov/pmc/articles/PMC7052349/
- **[S113]** Frequency of spinal reflex movements in brain-dead patients. https://www.sciencedirect.com/science/article/abs/pii/S0041134503012752 ; Spittler J.F. et al. Phenomenological diversity of spinal reflexes in brain death https://onlinelibrary.wiley.com/doi/10.1046/j.1468-1331.2000.00062.x
- **[S114]** Diffuse axonal injury (ScienceDirect Topics). https://www.sciencedirect.com/topics/neuroscience/diffuse-axonal-injury ; Diffuse axonal injury (StatPearls point of care) https://www.statpearls.com/point-of-care/20506 ; Post head injury autonomic complications (Medscape) https://emedicine.medscape.com/article/325994-overview
- **[S115]** Diabetes insipidus after traumatic brain injury. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC4519799/
- **[S116]** Isolated astasia in acute infarction of the supplementary-motor area (title-level only). https://pmc.ncbi.nlm.nih.gov/articles/PMC3029349/
- **[S118]** Craniocerebral gunshot injuries: a review of the current literature. https://pmc.ncbi.nlm.nih.gov/articles/PMC4897986/ ; Civilian gunshot wounds to the head: case report and review https://pmc.ncbi.nlm.nih.gov/articles/PMC7856761/
- **[S119]** The non-haemorrhagic vagal response to trauma: a review. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11599317/
- **[S121]** Neurologically intact survival after bihemispheric penetrating head trauma: a case report. https://www.sciencedirect.com/science/article/abs/pii/S0736467922008095
- **[S122]** Performance of the IMPACT and CRASH prognostic models in a contemporary cohort (TRACK-TBI). *J Neurosurg* 2024. https://pubmed.ncbi.nlm.nih.gov/38489823/ ; GCS-P and hospital mortality in severe TBI: 1,066 Brazilian patients https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10232027/ ; Comparative analysis of CRASH and IMPACT in 340 patients https://www.ncbi.nlm.nih.gov/pmc/articles/PMC10961482/

(IDs S117 and S120 are unused.)

---

## 23. Suspicious content

- No search result, snippet or summary contained instructions addressed to the agent (no requests to run commands, download or install anything, visit URLs, change files, reveal information, or ignore previous instructions).
- Some result lists included irrelevant US patent PDFs (image-ppubs.uspto.gov) and commercial rehabilitation or law-firm blog pages. They were ignored as sources.
- Content-quality issues, not injection: three search summaries contained medical errors or ambiguities that are corrected or flagged in the text: the CN III pupil called an "afferent" defect (§13.1), hemiparesis attributed to classic Claude syndrome (§13.1), and "~50% immediate seizures after penetrating injury" (§17.1).
- No code, commands or executable links were copied into this document.
- Fact-check pass: no web content was read (search budget exhausted), so no new untrusted text entered the document; nothing suspicious to report.

---

## 24. Fact-check (independent review of this document)

### 24.1 Method and limits

- Scope: the 20 load-bearing claims listed by the workflow, plus any other number that looked wrong or inconsistent, plus the common myths (bullets knocking people backward, eyes rolling back at death, "hydrostatic shock", everyone screaming).
- **No fresh web searches were possible**: the session's shared budget (200 WebSearch calls) was used up before this pass, and WebFetch is blocked. Verdicts therefore rest on the reviewer's knowledge of the primary papers and standard texts (Plum & Posner, Adams & Victor, Leigh & Zee, Brain Trauma Foundation guidelines) and on internal-consistency checks. Anything the reviewer could not confirm is marked **? not re-verified** in the text and keeps an (M) or (L) rating; QA items were added to §21 (item 11).
- Markers in the text: **✓ verified**, **? not re-verified**, **corrected: was X**.

### 24.2 Per-claim verdicts

| # | Claim (short) | Verdict | What changed in the text |
|---|---|---|---|
| 1 | Crossing: contralateral above the decussation, ipsilateral cerebellum, crossed brainstem signs | ✓ verified | Exceptions added to §0.4 rule 1 and §20.2 rule 7: CN IV nucleus → contralateral eye; CN III nucleus → contralateral superior rectus + bilateral ptosis; midbrain cerebellar outflow → contralateral ataxia; below the decussation → ipsilateral weakness; lateral medulla = crossed sensory loss |
| 2 | Flaccid first; spasticity 1–6 weeks; 24.5% by 2 weeks; 39.5% overall | ✓ verified | 24.5% matches Wissel 2010 (measured ~6 days); 39.5% matches Zeng 2021 (patients with paresis). Clarified "zero tone" = zero active drive, passive stiffness kept; `flaccid_passive_damping` added |
| 3 | Hand knob 3.5 cm lateral, 1.5–2 cm deep, MNI wrist (27, −25, 70); somatotopy; lower-face weakness | Partly: somatotopy and face ✓; numbers ? not re-verified | `hand_knob_lateral` confidence lowered (H → M); fMRI cross-check band added |
| 4 | 2–20 mm PLIC lacune → pure motor hemiplegia face = arm = leg; 33–50% of lacunar syndromes | ✓ verified | Range note (up to ~57% in some series); incomplete variants (p ≈ 0.3) and pontine origin added |
| 5 | Eyes toward destructive lesion, away from seizure focus, away from pontine lesion; 26.7% + 6%; > 14–15°; ~1 week | Directions ✓; numbers ? not re-verified | Added: only **forced** version lateralises (non-forced early turns often ipsilateral); `version_direction` updated |
| 6 | Neglect 43% vs 20% (17% vs 5% at 3 months); anosognosia 32/18/5% | ✓ verified | Anosognosia rates are among **right-hemisphere** stroke patients (Vocat 2010) |
| 7 | Cerebellar: ipsilateral ataxia, falls toward lesion, nystagmus 75%, 71% cannot walk, tremor < 5 Hz, deterioration median 3 days | Direction/tremor ✓; 75%/71% ? not re-verified; timing **re-scoped** | 3-day clock limited to oedema around infarct/contusion; bleeding posterior-fossa tracks use the minutes-to-48-h haematoma clock |
| 8 | CN III: exotropia 40–66 PD (up to 84), hypotropia ~14 PD, complete ptosis, fixed dilated pupil | ✓ verified (picture and PD→° maths) | Series means not re-checked; vertical component variable; traumatic/compressive palsies involve the pupil |
| 9 | Bobbing 17.5° at 129°/s, 0.5 s pause, 2–15/min; pontine pupils pinpoint; massive pontine bleed fatal in 24–48 h | Form, pupils, 24–48 h ✓; kinematics are **single-case**; rate ? | Randomise amplitude 5–20°, peak velocity 80–200°/s; penetrating pontine tracks cause immediate apnoea/collapse, not a 24–48 h course |
| 10 | Wallenberg frequencies (96/88/88/88/71/65/62/41%) | ? not re-verified | Hoarseness/dysphagia flagged as least certain; game ranges 0.4–0.6 / 0.5–0.65 given |
| 11 | Ropper: 0–3 mm alert, 3–4 drowsy, 6–8.5 stupor, 8–13 coma | ✓ verified | Confidence raised (M → H) |
| 12 | Cushing below CPP ~15 mmHg; tachycardia + HTN then bradycardia; Lundberg A 50–100 mmHg, 5–20 min | Sequence and Lundberg ✓; CPP threshold ? | Added: full triad appears only in a minority and late |
| 13 | EDH lucid interval 20–50% (classic < 20%), minutes–hours; progressive 2 h–7 d (mean 23 h); ~75% temporal; mortality 0–5% vs 11–41% | Main points ✓; mean 23 h and mortality ranges ? | Venous EDH (~10–15%, slower) and "never unconscious" minority added |
| 14 | Pupils 16/38/59%; GCS 3 = 51%; GCS-P 1 = 74%; survival 46% vs 13% | Gradient ✓; percentages ? ; **internal inconsistency corrected** | "79% at the bottom" and survival 0.21 contradicted 74% → harmonised to 74% (survival 0.26); confidence H → M; note that the survival figures are for operated patients |
| 15 | Hutchinson sequence; Kernohan notch → ipsilateral hemiparesis | ✓ verified | First dilated pupil on the mass side in ~85–90%; stage 1 brief and easily missed |
| 16 | PTS immediate 1–4%, early 4–25%, late 9–42% (~50% penetrating); GTC mean 62 s; figure-of-4 PPV ~90%; Todd 173 s (11 s–22 min) | ✓ verified (immediate 1–4% ? only) | Noted that 4–25% / 9–42% are moderate–severe TBI figures (BTF), and the ~50% penetrating figure matches the Vietnam Head Injury Study |
| 17 | Syncope LOC 12.1 ± 4.4 s, eyes open and up, myoclonus 90% | ✓ verified | Caveat: healthy volunteers; haemorrhagic syncope lasts longer and may not end |
| 18 | Fencing response 66% of 35 KO videos, regardless of side, seconds | 66% ✓; side ? not re-verified | Side choice rule (arm extends on the face side, else random) `[K] (L)`; duration marked `[E]` |
| 19 | Decorticate above red nucleus / decerebrate midbrain–upper pons; limb positions | ✓ verified | Human lesion-level correlation is loose; lesions below the vestibular nuclei → flaccid; checklist palm direction **corrected** |
| 20 | GSW head predictors; 100% mortality for diencephalic, transventricular, posterior-fossa tracks | Predictors ✓ (M); "100%" ? | Use p(death) 0.9–1.0 rather than a hard 1.0 |

### 24.3 Corrections (value changes)

1. §13.1 trochlear row — corrected: was "head tilted away from the lesion side" for every CN IV lesion; now nerve lesion (ipsilateral eye) vs nucleus/fascicle lesion (contralateral eye, head tilts toward the lesion side).
2. §14.1 CN IV row — corrected: was "Ipsi eye" for all lesion sites.
3. §19.2 GCS-P text — corrected: was "mortality falls from 79% at the bottom to 14% at the top" (contradicted the 74% in the same table).
4. §19.3 `survival_from_gcsp` — corrected: was 0.21 at GCS-P 1 and 0.86 at 15; now 0.26 and ~0.85–0.95 `[E]`.
5. §18.5 checklist, decerebrate — corrected: was "backs of the hands turn out"; internal rotation plus pronation turns the **palms** outward and backward.
6. Confidence changes: `hand_knob_lateral` H → M; `mortality_by_pupils` H → M; GCS 3 row H → M; `loc_from_mls` M → H.
7. §12.1 / §12.3 cerebellar deterioration timing re-scoped (infarct/contusion oedema days vs haematoma hours).
8. §20.2 rule 11 refined: coup vs contrecoup depends on head motion (moving head → contrecoup; still head struck → coup).

### 24.4 Myth check

| Myth | Status in this document | Fact `[K]` / computed `[E]` |
|---|---|---|
| Bullets knock people backward | Not claimed here ✓ | A 9 mm bullet (8 g at ~360 m/s) carries ~2.9 kg·m/s: fully absorbed by a 75 kg body that is ~0.04 m/s; fully stopped in a ~5 kg head, at most ~0.6 m/s, much less when it exits `[E]`. The shooter's hand takes the same momentum as recoil. Head-shot "snap" movements and falls come from loss of tone, reflexes and the character's own posture, not bullet push. |
| Eyes roll back at the moment of death | Guard added (§14.6 "Death" row) | A brief upward deviation (2–10 s) can occur at loss of consciousness from hypoperfusion [R1-04 §11]; the eyes then settle near straight ahead or slightly divergent and stay there after death. |
| "Hydrostatic shock" knocks people out from torso hits | Guard added (§20.2 rule 2) | Remote brain effects are described in animal experiments but are not an established cause of instant human incapacitation; do not apply brain stun to non-head hits. |
| Everyone screams when shot | Guard added (§5.2) | Capacity to vocalise survives aphasia, but many victims are silent, gasp, grunt or speak briefly; unconscious characters are silent apart from airway noises. |
| Any head shot drops the target instantly | Already handled ✓ (§4.1, [R1-01 §6]) | Immediate collapse needs brainstem/diencephalic destruction, massive hemispheric destruction or high-energy cavitation; low-energy unilateral frontal tracks can leave a person conscious and mobile. |
| Movement after brain death means the person is alive | Already handled ✓ (§17.4) | Spinal reflexes; the fact-check widened their frequency to p 0.2–0.5. |

### 24.5 Gaps

Written into the sections by this pass: crossing exceptions (§0.4, §20.2); flaccid ≠ frictionless (§0.4, §2.5); FEF location (§3.3); forced vs non-forced version (§14.1, §17.5); Hutchinson false-side pupil ~10–15% (§14.4); venous EDH (§15.2); spontaneous vs penetrating pontine lesions (§13.2); coup vs contrecoup (§20.2); the three myth guards (§5.2, §14.6, §20.2).

Recommended for a later pass (not written into the sections, because the numbers could not be checked):
- **Post-hypoxic myoclonus**: after strangulation, drowning or cardiac arrest with return of circulation, generalised or multifocal myoclonic jerks within the first 24 h (myoclonic status, a poor-prognosis sign); chronic action myoclonus (Lance-Adams) appears weeks later in survivors `[K] (M)`. Cross-reference `04_agonal_involuntary_movement.md`.
- **Visible signs of skull-base fracture** that accompany many of the deficits here (periorbital and mastoid bruising, which appear hours to days later; blood or CSF from the nose or ear): cross-reference `05_severe_trauma_morphology.md`.
- **Player-testable upper-motor-neuron signs** in the acute phase (Babinski sign, absent abdominal reflexes, early hyperreflexia) for a character that is examined up close `[K] (H)`.
- Primary-source opening for the §21 item 11 list before any of those numbers become hard constants.

### 24.6 Simulation parameters changed or added by the fact-check

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `flaccid_passive_damping` | 0.6–0.9 × relaxed healthy-limb damping; 0 active drive | — | New | [E] |
| `cn4_side` | nerve: ipsi eye; nucleus/fascicle: contra eye | — | New | `[K]` (H) |
| `version_direction` | forced: away from focus; early non-forced: either side, p 0.5 | — | Changed | [S65] `[K]` (H) |
| `hutchinson_false_side_prob` | 0.10–0.15 | p | New; first dilated pupil opposite the mass | `[K]` (M) |
| `survival_from_gcsp` | 0.26 at GCS-P 1 → ~0.85–0.95 at top | p | Corrected (was 0.21 → 0.86) | [S92] (M), [E] |
| `mortality_by_pupils` | 0.16 / 0.38 / 0.59 (untreated severe: ~0.3 / 0.6 / 0.9) | p | Confidence H → M | [S92] (M), [E] |
| `bobbing_down_amp` / `peak_vel` | 5–20 / 80–200 (single-case example 17.5 / 129) | ° / °/s | Randomise | [S54] (L), [E] |
| `ic_incomplete_variant_prob` | 0.3 | p | Face + arm or arm + leg only | [E] on [S31] |
| `penetrating_deep_track_death` | 0.9–1.0 | p | Diencephalic, transventricular, posterior-fossa tracks | [S95] (M), [E] |
| `spinal_reflex_after_brain_death` | 0.2–0.5 | p | Widened from 0.13–0.22 | [S113] `[K]` (M) |
| `coup_contrecoup_weight` | moving head: contrecoup ≥ coup; still head struck: coup ≫ contrecoup | — | New | `[K]` (H), [E] |
| `brain_stun_nonhead_hits` | 0 | — | Myth guard against "hydrostatic shock" | `[K]` (M) |

### 24.7 Visual/behavioural checklist (fact-check additions)

- A limp arm is heavy and swings, but still has the slight stiffness of a relaxed limb; it does not flop like rope.
- A seizure may start with a small head turn to either side; the violent, forced wrench of head and eyes is away from the wound, just before the whole body stiffens.
- After a fall onto the back of the head, the worst damage (and the late deterioration) comes from the front of the brain; after a hammer blow to a still head, the damage is under the blow.
- Shot characters are not thrown backward; they drop because their legs or consciousness fail.
- At death the eyes do not stay rolled up to the whites; they settle roughly forward, slightly apart, lids part-open.
- Many wounded characters stay quiet or only grunt; screaming is one possible reaction, not the default.
