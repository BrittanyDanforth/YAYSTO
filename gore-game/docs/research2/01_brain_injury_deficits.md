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
| **Hemispatial neglect** | Contra space; right lesions far more often | Acute: 43% of right-hemisphere vs 20% of left-hemisphere strokes; at 3 months 17% vs 5% | Ignores everything on the left: people, threats, sounds, its own left limbs; head and eyes turned right | [S17][S18] |
| **Anosognosia for hemiplegia** | Right hemisphere | ~32% very acute; 18% in the first week; 5% at 6 months | Denies or ignores the paralysis; tries to stand on a paralysed leg | [S19] |
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
| Hippocampus / medial temporal | **Anterograde amnesia** (cannot form new memories), repetitive questioning; severe only if bilateral | Global | [S83 search summary] `[K]` (H) |
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

- The **posterior limb** carries the corticospinal and corticobulbar fibres for the whole opposite half of the body, packed into a band ~10–15 mm wide `[K] (M)`. A lacune of **2–20 mm** here causes **pure motor hemiparesis/hemiplegia affecting face, arm and leg about equally** [S31]. Pure motor stroke is the commonest lacunar syndrome (33–50%) [S31].
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
| `ic_face_arm_leg_ratio` | 1 : 1 : 1 | — | Unlike cortex | [S31] (H) |
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
- Nystagmus in 75% of cerebellar infarcts (horizontal ipsilateral-beating 47%, contralateral 5%, bilateral 11%, vertical 11%) [S41].
- 90% show localising signs (truncal/limb ataxia, nystagmus, dysarthria); **71% of those with "only vertigo" cannot walk** [S41].
- Cerebellar tremor is low frequency, **< 5 Hz** (typically 3–5 Hz), without a rest component; Holmes (rubral/midbrain) tremor is < 4.5 Hz (2–4.5 Hz) and combines rest, postural and intention components [S44].
- Gait: reduced speed, cadence and step length; **increased step width, double-support time and especially stride-to-stride variability**, the core feature [S42]. Numbers below are author values (the retrieved summaries gave no means).
- Deterioration after cerebellar haemorrhage (brainstem compression or hydrocephalus): mean 5 days, range 10 h – 10 days, median and mode 3 days; the first sign is falling consciousness [S40]. A vermian haemorrhage, absent corneal reflexes, impaired oculocephalic responses or early hydrocephalus predict deterioration [S40].

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
| `cb_swelling_deterioration` | median 3 days (10 h–10 d) | — | Haematoma-driven compression faster (§15) | [S40] (M) |
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
| Trochlear (CN IV) | Weak depression in adduction; vertical double vision; head tilted **away** from the lesion side. Closed head trauma is its commonest cause | — | `[K]` (H) |
| Bilateral tegmentum | Coma, fixed mid-position pupils, decerebrate [R1-04 §2.2] | | [R1-04] |
| Late (weeks–months) | **Holmes (rubral) tremor**, < 4.5 Hz, rest + posture + intention | Contra | [S44] |

Corrections to search summaries: one summary described the CN III pupil as an "afferent pupillary defect"; it is an **efferent** defect (the pupil does not constrict whichever eye is lit) `[K] (H)`. Another listed hemiparesis in Claude syndrome; the classic description is contralateral ataxia without hemiparesis `[K] (M)`.

Numbers for the CN III eye:
- Horizontal exodeviation in primary position: mean 40–44 PD in one series, 66 ± 29 PD in another, up to 84 ± 15 PD in very large cases [S50]. That is **~22–33°** outward, up to ~40° `[E]`.
- Vertical (hypotropia): mean ~14 PD, **~8° down** [S50].
- Ptosis: complete, the upper lid covers the pupil `[K] (H)`. Pupil: 6–9 mm, fixed `[K] (M)`.

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
- **Ocular bobbing** (pontine coma): fast conjugate **downward** jerk (~17.5° at ~129°/s peak), sometimes a ~0.5 s pause, then **slow drift back** to mid-position; recurs irregularly **2–15 times per minute** [S54]. **Ocular dipping** (inverse bobbing, more often diffuse/anoxic damage): slow downward drift over ~2 s, held 2–10 s, fast return, sometimes with a blink; next cycle 10–30 s later [S55]. **Reverse bobbing**: fast up, slow return [S55].
- Massive pontine haemorrhage: invariably fatal but not instantaneous; death usually **24–48 h** after onset, 7–10 days not rare; overall pontine-haemorrhage mortality 30–60% [S57].

### 13.3 Medulla

| Lesion | Same side (ipsi) | Opposite side (contra) | Source |
|---|---|---|---|
| **Lateral medulla (Wallenberg)** | Face pain/temperature loss, **Horner** (small pupil, droopy lid), **dysphagia**, **hoarseness**, weak gag, limb ataxia, **lateropulsion** (pulled toward the lesion side) | Body pain/temperature loss | [S58][S59] |
| **Medial medulla (Dejerine)** | **Tongue paralysis**: protruded tongue deviates **toward the lesion** | **Hemiparesis sparing the face**, position-sense loss | [S60] |
| Bilateral medial medulla | Bilateral tongue paralysis | Quadriplegia; **respiratory failure** and death common | [S60] |
| Bilateral / central medulla | **Apnoea**, vasomotor collapse [R1-04 §2.2] | | [R1-04] |

Wallenberg symptom frequencies (130 consecutive patients): sensory symptoms 96%; **vertigo/dizziness 88%, gait ataxia 88%, Horner 88%**; nystagmus 71%; **nausea/vomiting 65%; dysphagia 62%; hoarseness 41%** [S58]. Rostral lesions give dysphagia, facial weakness and dysarthria more often; caudal lesions give more severe gait ataxia and headache [S58]. **Intractable, violent hiccups** are characteristic [S59]. A smaller series reported vocal-cord paresis in all patients and a weak cough in 80% [S59 search summary] (L).

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
| `tongue_dev_side` | toward lesion (medial medulla); toward weak side (cortex/capsule) | — | | [S60] `[K]` (H) |

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
| **Conjugate gaze deviation, destructive hemispheric** | FEF, large MCA territory, putamen/capsule | **Toward the lesion** (away from the paralysed side) | 15–40°; > 14–15° typical of large infarcts; head often turned too | Immediate; days (≈1 week) | Both eyes and head turned to the wounded side; doll's eyes can still move them | [S63][S64][S27] |
| **Seizure (irritative) deviation, "versive"** | Frontal (or other) seizure focus | **Away from the focus** (>90% of patients) | Forced, extreme 30–45°; head turns with it | Seconds, during the seizure; may reverse when focal destructive deficit dominates after the seizure | Head and eyes wrench to one side, often the first sign of the fit | [S65][S71] |
| **Pontine gaze palsy** | PPRF / CN VI nucleus | **Away from the lesion** (toward the paralysed side) | 10–30° at rest | Immediate, persistent | Eyes look at the paralysed limbs; doll's eyes fail | [S52][S53] `[K]` |
| **Thalamic eyes** | Thalamic haemorrhage/track | **Down and in**; occasionally **wrong-way** (away from lesion) | 10–25° down, 5–15° in | Immediate | "Peering at the tip of the nose"; small pupils | [S27][S29] |
| **Upgaze palsy / setting sun** | Dorsal midbrain; hydrocephalus pressing it | Eyes cannot go up; with hydrocephalus tonically **down**, sclera visible above the iris | Up-range 0–10° | Minutes–hours with hydrocephalus | Lids retracted, eyes pushed down | [S48] `[K]` |
| **Skew deviation / ocular tilt reaction** | Otolith pathway: vestibular nucleus to midbrain (INC) | Vertical misalignment. Pontomedullary lesion: **ipsilateral eye lower**; midbrain lesion: contralateral eye lower. Head tilts toward the lower eye | 2–10° vertical `[E]` | Immediate; weeks | One eye higher than the other; head tilted | [S61] `[K]` |
| **INO / WEBINO** | MLF | Adduction failure of the eye on the lesion side; bilateral with exotropia | Adduction 0–50% | Immediate | Eyes drift outward ("wall-eyed"); one eye lags when looking sideways | [S62] |
| **One-and-a-half** | PPRF/CN VI nucleus + MLF | Ipsi eye fixed horizontally; other eye only abducts | — | Immediate | | [S52] |
| **CN III palsy** | Midbrain, CN III nerve, uncal herniation | Ipsi eye **down and out** | 22–33° out, ~8° down; complete ptosis | Immediate (track) or minutes–hours (herniation) | See §13.1 | [S49][S50] |
| **CN VI palsy** | Pons, petrous apex, raised ICP | Ipsi eye **in** | 6–22° in | Immediate or with ICP | "Crossed eyes" | [S51] |
| **CN IV palsy** | Dorsal midbrain / nerve (blunt trauma) | Ipsi eye slightly **up**; head tilts away | 2–8° `[E]` | Immediate | Subtle | `[K]` |
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

Hutchinson sequence during uncal herniation [S74]: (1) brief **ipsilateral constriction** (irritation of the parasympathetic fibres on the outside of CN III); (2) **ipsilateral dilation**, often with brief contralateral constriction; (3) **bilateral fixed dilation**. The parasympathetic fibres lie on the surface of the nerve and are compressed first, which is why the pupil goes before eye movement [S74].

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
| **Syncope** (drop in brain blood flow, including faint from pain or blood loss) | Open in most; **initial upward deviation** common; some have brief **downbeat nystagmus** first, then upward deviation | LOC **12.1 ± 4.4 s**; **multifocal arrhythmic myoclonic jerks in 90%**; head turns, lip-smacking, righting movements in 79% | [S70] |
| **Knockout** | Open, fixed unfocused stare, or rolled up | "Flash" KO < 3 s vs KO ≥ 3 s; tone lost completely at once; wake within seconds to a few minutes | [S98] `[K]` |
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
| Midline shift from a lateral mass | ≈ 0.15 mm per mL (30 mL → 4.5 mm; 60 mL → 9 mm) | [E] |
| Consciousness vs horizontal pineal shift (Ropper) | 0–3 mm alert; 3–4 mm drowsy; 6–8.5 mm stupor; 8–13 mm coma | [S84] (M) |
| Cushing response | Appears when CPP falls below ~15 mmHg (seen in almost every case below that) | [S85] (M) |
| Plateau (Lundberg A) waves | ICP rises from near normal to **50–100 mmHg**, holds **5–20 min**, falls sharply; during them headache, nausea, stupor, **tonic posturing**; at the peak apnoea and decerebration | [S86] (M) |
| Haematoma volume vs outcome (spontaneous intracerebral bleed, as a dose example) | ≥ 60 cm³ with GCS ≤ 8: 91% 30-day mortality; < 30 cm³ with GCS ≥ 9: 19% | [S94] (H) |

### 15.2 Epidural (extradural) haematoma, EDH

- Usually a skull fracture tears the **middle meningeal artery**; ~75% of adult EDHs are temporal [S78].
- **Lucid interval**: estimates range 20–50% of EDH patients; the textbook sequence (knocked out → wakes and talks → deteriorates) is seen in fewer than 20% [S76]. The interval lasts **minutes to hours**; deterioration, if it happens, is usually within 24 h [S76]. Progressive EDHs developed between 2 h and 7 days after injury, average 23 h [S77].
- Treated outcome: not comatose → mortality 0–5%; comatose (GCS ≤ 8) → 11–41% [S78]. Guidelines evacuate any EDH > 30 cm³; < 30 cm³, < 15 mm thick and < 5 mm shift in an alert patient can be observed [S79]. The game has no neurosurgeon: **an untreated expanding EDH kills** `[K] (H)`.

Default "classic" EDH timeline for the game (arterial source, untreated) `[E]` on [S76][S77][S78][S84][S85]:

| Stage | Real time from impact (default, range) | Mass (mL) | What the player sees | t_game |
|---|---|---|---|---|
| Impact | 0 | 0 | Brief knockout 5 s – 5 min (p ≈ 0.6), or dazed only | 1× |
| Lucid interval | 5 min – 1 h (15 min – 6 h) | 5 → 50 | Awake, talking, walking; worsening headache, 1–3 vomits, irritability | 4× → 15× |
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
- Penetrating wounds: haematomas along the track, intraventricular bleeding and acute hydrocephalus cause secondary deterioration [S118]. In civilian series all deaths had admission GCS 3–8 [S118]; **non-reactive pupils, bihemispheric (non-bifrontal) tracks, posterior-fossa involvement and age > 35** predicted death [S95]; diencephalic, transventricular and posterior-fossa tracks had **100% mortality** in one series [S95]. Rare survivors of bihemispheric tracks exist [S121].

### 15.5 Cushing response

- Stage 1: sympathetic surge, **hypertension and tachycardia**; stage 2: hypertension persists and the heart rate **slows** (baroreflex) [S85]. Widened pulse pressure and irregular breathing complete the triad [S85].
- Simultaneous hypertension and tachycardia is an earlier warning than waiting for bradycardia [S85]. The full triad is a late sign that appears just before herniation and may never appear [S85].
- Author values for display `[K]` (M): SBP 160–240 mmHg, pulse pressure 80–120 mmHg, HR 40–60 bpm (can fall to 30), breathing slow and irregular (§15.6 table).

### 15.6 Herniation syndromes

**Uncal (lateral transtentorial)** — temporal or lateral masses (EDH, ASDH, temporal contusion):
- The medial temporal lobe (uncus) slides over the tentorial edge and compresses the **ipsilateral CN III** and midbrain [S90].
- Sequence: ipsilateral pupil (Hutchinson stages, §14.4) → falling consciousness → **contralateral** hemiparesis (cerebral peduncle) → decerebrate → bilateral fixed pupils → brainstem failure `[K]` [S90][S74].
- **Kernohan notch** (false localising): the opposite cerebral peduncle is pushed against the tentorium, producing hemiparesis on the **same** side as the mass and the blown pupil [S88]. Game probability 0.1–0.2 `[E]`.
- Posterior cerebral artery compression can add an occipital infarct (hemianopia) in survivors `[K] (M)`.
- Prognosis: survival 46% with a unilateral fixed dilated pupil versus 13% with bilateral [S89]; mortality 16% with both pupils reactive, 38% with one, 59% with none [S92]. In one surgical series the median time from pupil change to surgery was 133 min (30–900 min), showing the window lasts hours, not seconds [S89].

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
| `mls_per_ml` | 0.15 | mm/mL | Lateral masses | [E] |
| `loc_from_mls` | 0–3 alert, 3–4 drowsy, 6–8.5 stupor, 8–13 coma | mm | Interpolate | [S84] (M) |
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
| `mortality_by_pupils` | 0.16 / 0.38 / 0.59 | p | Both / one / neither reactive (for survival-based outcomes) | [S92] (H) |

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
| **Immediate post-traumatic seizure** | < 24 h | 1–4% of TBI | [S103] |
| **Early** | 1–7 days | 4–25% of TBI (untreated) | [S103] |
| **Late (epilepsy)** | > 7 days | 9–42%; up to ~50% after dural penetration and in military penetrating series | [S103] |

- One search summary stated that ~50% of penetrating head injuries have **immediate** seizures. This conflicts with the other figures and with the classification in the same source; it most likely refers to late epilepsy after penetrating injury. **Game value**: p(immediate seizure within the first hour) = 0.05–0.10 for a penetrating cortical track, 0.02–0.04 for blunt cortical contusion `[E]`.
- Seizures arise from **cortex**. Pure cerebellar, brainstem or deep white-matter lesions do not cause epileptic seizures `[K] (H)`; motor-strip, frontal and temporal cortex hits are the most epileptogenic `[K] (M)`.

### 17.2 Generalised and focal-to-bilateral tonic–clonic seizures

- In 120 video-EEG-recorded secondarily generalised seizures, mean duration was **62 s**; phases were onset of generalisation, pre-tonic clonic, tonic, **tremulousness**, clonic; only 27% showed all five, and phase durations varied widely [S104].
- In the clonic phase, the atonic gaps between jerks **lengthen** until the jerks stop; jerks become slower and larger [S105].
- Focal onset shows as **head/eye version** (away from the focus), unilateral face jerking, mouth deviation, automatisms first; the **figure-of-4** posture (one elbow extended, the other flexed across the chest) lateralises with PPV ~90%, the **extended elbow is contralateral to the focus**; the clonic phase and the ending are often asymmetric [S106].

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
- **Todd's paralysis** (postictal weakness of the seizing side): mean **173 s** (range 11 s – 22 min) in a video-EEG study of focal epilepsies; case reports up to 36–48 h [S110].

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
| Spinal reflex movements after brain death | Spinal cord | Slow, stereotyped (toe undulation, arm flexion/"Lazarus") | Limbs | Minutes–hours after brain death; 13–22% of brain-dead patients | [S113] |

### 17.5 Simulation parameters: seizures and movements

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `p_immediate_seizure_penetrating_cortex` | 0.05–0.10 | p in first hour | ×1.5 for motor/temporal cortex | [E] on [S103] |
| `p_immediate_seizure_blunt_contusion` | 0.02–0.04 | p | | [S103] (M), [E] |
| `p_seizure_noncortical` | 0 | p | Brainstem, cerebellum, deep white matter only | [K] (H) |
| `gtc_mean_duration` | 62 (30–120) | s | Phases variable; not all present (27% all five) | [S104] (H) |
| `version_direction` | away from focus | — | | [S65][S106] (H) |
| `figure4_prob` | 0.3–0.5 of focal-to-bilateral seizures | p | Extended elbow contralateral to focus | [S106] (M), [E] |
| `frontal_seizure_duration` | 10–40 | s | | [S107] (M) |
| `jackson_segment_time` | 5–30 | s per segment | Rare full march (p 0.1 of focal motor seizures) | [E] on [S108] |
| `todd_duration` | 173 (11–1320) | s | Tail to 36 h | [S110] (M) |
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
| Fencing | At the moment of a knockout blow, consciousness lost | 2–10 s (max ~20 s), once | Asymmetric: one extended up/forward, one flexed | Seen in 66% of 35 analysed knockout videos, regardless of the side of impact [S99] |
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
| `fencing_prob_ko` / `duration` | 0.66 / 2–10 (≤ 20) | p / s | | [S99] (M) |
| `psh_onset` | ~6 days | — | Time skips only | [S112] (M) |

### Visual/behavioural checklist: posturing
- Decorticate: fists pulled up to the chest, legs stiff and straight, toes pointed; comes and goes when the body is moved.
- Decerebrate: arms rigid at the sides, rolled inward so the backs of the hands turn out, wrists bent, head pushed back, jaw clamped; spasms when touched.
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
| 3 | Deepest | Flaccid, eyes closed or fixed open, no sound | Mortality 51% at GCS 3 in pooled IMPACT/CRASH data; **74% at GCS-P 1** (GCS 3 with both pupils unreactive) | [S92] (H) |

- **GCS-P** = GCS minus pupil reactivity score (2 = both unreactive, 1 = one unreactive, 0 = both react); range 1–15; mortality falls continuously from 79% at the bottom to 14% at the top [S92].
- The ICH example: bleed ≥ 60 cm³ with GCS ≤ 8 → 91% 30-day mortality [S94].

### 19.3 Simulation parameters: GCS

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `gcs_e/v/m` | computed per tick at 2–5 Hz | — | Store best-response values | [E] |
| `gcs_p` | GCS − PRS | 1–15 | | [S92] (H) |
| `survival_from_gcsp` | 0.21 at GCS-P 1 rising to 0.86 at 15 | p | Only if the game resolves "would survive" outcomes | [S92] (M) |

### Visual/behavioural checklist: GCS
- GCS 13–14: talking nonsense-adjacent, asking again and again, walking like a drunk.
- GCS 9–12: eyes flutter open when shouted at or hurt, mumbles a word or moans, pushes the player's hand away.
- GCS 6–8: eyes shut, groans when hurt, pulls a limb away or stiffens.
- GCS 3–5: nothing except spasms of stiffening; snoring or gurgling breathing, if any.

---
<!-- PART5 -->
