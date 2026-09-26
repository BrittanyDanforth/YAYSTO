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

- About 75 `WebSearch` queries were run for this document (the session's shared search budget then ran out). `WebFetch` is blocked by network policy, so **no page was opened in full**. Values tagged [S#] come from search-result summaries of the listed pages. Before a number becomes a hard constant, QA should open the source (priority list in §21).
- Numbers not found in search results come from the author's knowledge of standard texts (Plum & Posner's *Diagnosis of Stupor and Coma*, Adams & Victor, Leigh & Zee *The Neurology of Eye Movements*, Blumenfeld *Neuroanatomy through Clinical Cases*, ATLS, Brain Trauma Foundation guidelines).
- Where a search summary contained an error that conflicts with standard neurology, it is noted in the text and corrected (for example §13.1 Weber syndrome, §17.1 seizure incidence).

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

1. **Crossing.** Everything above the pyramidal decussation (cortex, internal capsule, basal ganglia, thalamus, midbrain, pons) controls the **opposite** half of the body. The **cerebellum** controls the **same** side. A **brainstem** lesion gives **crossed signs**: cranial-nerve deficits (eye, face, tongue, swallowing) on the **same** side as the lesion, limb weakness on the **opposite** side `[K]` [S47][S53][S60].
2. **Consciousness** needs the brainstem reticular activating system plus thalami plus at least one working hemisphere. A one-sided hemisphere lesion does not by itself cause coma; bilateral hemisphere, bilateral thalamic or upper-brainstem damage does, and so does mass effect (herniation) [R1-04 §3.1] [S28].
3. **Destroyed tissue fails at once; the rest follows a clock.** Direct destruction = deficit in the same frame. Concussive/penumbral dysfunction around a track = seconds to minutes, partly recovers. Bleeding and swelling = minutes to days (§15).
4. **Destructive vs irritative lesions push the eyes opposite ways.** A destroyed hemisphere lets the eyes drift **toward** the lesion. A seizure focus drives them **away** from it. A destroyed pons makes them look **away** from the lesion (toward the paralysed limbs) (§14) [S63][S65] `[K]`.
5. **The flaccid phase is what the player sees.** Paralysis from a new brain lesion is limp for hours to weeks; spasticity appears 1–6 weeks later (§2.3) [S1][S2]. Posturing (§18) is a separate brainstem-release phenomenon and can appear within seconds.

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
- **Hand knob**: an omega-shaped bend of the precentral gyrus; ~3.5 cm from the midline and 1.5–2 cm deep into the central sulcus [S34]; ~31 mm horizontally from the Cz scalp point [S34]. Electrostimulation MNI coordinates: wrist (27, −25, 70), finger extension (30, −26, 69), thumb/finger flexion (34–36, −11 to −22, 65–66) [S35].
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
- **Face**: a cortical or capsular lesion weakens the **lower** face on the opposite side; the forehead and eye closure are largely spared because the upper face gets input from both hemispheres [S36]. In severe acute strokes upper-face weakness is also common, but milder [S36]. Emotional smiling may still move the weak side [S36].
- **Tongue**: pushed out, it deviates toward the weak side (contralateral to the lesion) `[K] (M)`.
- Severity scales with how much of the corticospinal output is destroyed: in stroke, motor outcome is inversely related to the fraction of the corticospinal tract hit by the lesion ("lesion load") [S32]; above ~7 cc of weighted tract lesion load, all patients had poor arm function at 3 months [S32].

### 2.3 Timing: flaccid first, spastic later

| Phase | Real time | Signs | Source |
|---|---|---|---|
| Destruction | 0 s | Loss of voluntary force in the same frame | `[K] (H)` |
| Flaccid ("cerebral shock") | Hours to 1–3 weeks | Limb limp, no resistance to passive movement, reflexes reduced or normal; Babinski sign may appear within hours | [S3] `[K] (M)` |
| Rising tone | Days to weeks | Hyperreflexia; spasticity in 24.5% within 2 weeks; spasticity usually appears between 1 and 6 weeks | [S1][S2] |
| Spastic peak | 1–3 months | Flexed arm, extended leg ("Wernicke-Mann" posture), clonus | [S1] |

- Overall spasticity after a first stroke with paresis: 39.5% [S1]. A lesion of the internal capsule or brainstem, severe weakness or early hyperreflexia predicts it [S1].
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
| `hand_knob_lateral` | 35 (30–40) | mm from midline | 15–20 mm deep | [S34] (H) |
| `m1_visible_at` / `m1_full_at` | 0.10 / 0.60 | fraction of segment destroyed | smoothstep between | [E] |
| `mrc_from_severity` | 5 − 5·sev (round down) | MRC | sev 0.5 → MRC 3 | [E] |
| `joint_drive_scale` | (1 − sev)^1.5 | × max drive | Applied to the affected side's PhysicalBone3D motor targets | [E] |
| `ipsi_proximal_sparing` | 0.3 | fraction of proximal/axial strength kept at sev = 1 | Shoulder shrug, hip still partly work | [E] on [K] |
| `upper_face_sparing` | 0.7 | fraction of forehead/eyelid strength kept | Severe cases lower it to 0.4 | [S36] (M), [E] |
| `arm_drift_time` | 3–10 | s | For sev 0.4–0.8 | [S37] [E] |
| `weapon_drop_threshold` | hand sev > 0.7 | — | Drop delay 0.1–0.5 s | [E] |
| `leg_buckle_threshold` | leg sev > 0.6 | — | Buckle 0.2–0.6 s after load | [E] |
| `flaccid_duration` | 1–3 weeks (never shorter in game) | — | Tone stays zero on the affected side | [S3] (M) |
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

- Destruction lets the eyes (and often the head) deviate **toward the lesion**, because the intact FEF pushes them over [S64]. The eyes can still be moved by reflex (doll's-eye manoeuvre) because the brainstem is intact `[K] (H)`.
- The deviation lasts **days to about a week** and then fades as other pathways take over; afterwards saccades toward the opposite side stay slow and hypometric [S64].
- In stroke series, forced conjugate eye deviation was found in 26.7% and partial in 6% of 116 patients [S63]; another series found 43% with conjugate deviation plus 33% with a lone abducting eye [S63]. An average deviation > 14–15° is associated with large middle-cerebral-territory infarcts [S63].
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
- In the confused period after a coma (post-traumatic amnesia), disinhibition and agitation are extreme regardless of lesion site [S11 search summary] `[K] (M)`.

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
<!-- PART2 -->
