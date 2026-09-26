# 02 — Reactions to being shot, stabbed, punched, struck and burned (second by second)

Project: gore simulator (Godot 4.5, Forward+, GDScript + Godot shaders, built-in Jolt, Skeleton3D + PhysicalBone3D ragdolls). Research round 2.
Audience: animation, ragdoll/physics, AI/behaviour, audio and physiology engineers. Clinical, factual tone. The subject is a fictional, procedurally generated adult.

Scope: what a real person's body and behaviour do in the first 0–60 s after a hit. Covers reflexes, momentum, the difference between psychological and physiological incapacitation, not noticing a hit, the mechanical effect of each hit location, staggering and balance recovery, how and when the body drops, protective behaviour (conscious vs unconscious), knockouts and "getting rocked", knife and burn reactions, pain behaviour and vocalisation, shock and dissociation, neurological deficits as reaction modifiers, and a reaction-selection table.

This document builds on round one and does not repeat it:

| Round-one file | What it already covers | Cited here as |
|---|---|---|
| `docs/research/01_gunshot_wounds.md` | Ammunition data. Body knock-back 0.01–0.18 m/s. Head-shot retained capacity (Karger) | `[R1-01 §x]` |
| `docs/research/02_sharp_blunt_burn.md` | Punch forces, facial fractures, defence-wound statistics, burn thermal dose and depth | `[R1-02 §x]` |
| `docs/research/03_bleeding_vessels.md` | Bleed rates, shock classes, exsanguination sequence | `[R1-03 §x]` |
| `docs/research/04_neuro_death_eyes.md` | Brainstem "cut strings" collapse, hemisphere deficits, knockout and fencing response, concussive convulsion, posturing, seizures, eyes, apnoea | `[R1-04 §x]` |

---

## 0. Read this first

### 0.1 Method and limits

- About 60 `WebSearch` queries were completed. The session's shared web-search budget (200 calls) then ran out. Three planned searches were refused: Godot 4 `PhysicalBoneSimulator3D` API details, the DReCon paper, and a NaturalMotion GDC talk.
- `WebFetch` was not used. The brief says the network policy blocks it.
- Every `[S#]` value therefore comes from **search-result summaries and abstract-level text, not full papers**. Sample sizes, means and percentages quoted from abstracts are reliable. Finer detail is tagged `[K]` or `[E]`.
- **Field data on real shootings is thin and partly non-peer-reviewed.** Examples are Ellifritz's 1,800-shooting compilation and Force Science Institute reports. They are the best available behavioural data, but the confidence is (M) or (L).
- **Survivor accounts are anecdotal.** They justify only qualitative behaviour, never a number.

### 0.2 Tags

| Tag | Meaning |
|---|---|
| `[S#]` | Sourced. The URL is in §17. Read through search summaries only. |
| `[K]` | Author's own knowledge of standard neurology, trauma surgery, forensic pathology, motor control and biomechanics. Not verified in this session. |
| `[E]` | Engineering estimate or derivation for the game. The arithmetic or anchoring is shown. |
| `[R1-0x §y]` | Round-one document and section. |
| (H) / (M) / (L) | Confidence that the real value lies in the stated range. |

### 0.3 Conventions

- **Reference body**: male, 75 kg, 1.75 m. This is the same body as round one.
- **Segment masses** (de Leva 1996 [S45]):

  | Segment | Share of body mass | Mass for 75 kg |
  |---|---|---|
  | Head + neck | 6.94 % | 5.2 kg |
  | Trunk | 43.46 % | 32.6 kg |
  | Upper arm | 2.71 % | 2.03 kg |
  | Forearm | 1.62 % | 1.22 kg |
  | Hand | 0.61 % | 0.46 kg |
  | Thigh | 14.16 % | 10.6 kg |
  | Shank | 4.33 % | 3.25 kg |
  | Foot | 1.37 % | 1.03 kg |

  Two sides plus head and trunk sum to 100 %.
- **Centre of mass (COM)**: standing COM height ≈ 0.55 × stature = **0.96 m** `[K]`. The inverted-pendulum constant is ω₀ = √(g/l) = √(9.81/0.96) = **3.20 s⁻¹** `[E]`.
- **t = 0** is the moment of contact: bullet entry, blade contact, fist or hammer contact, or flame contact.
- **Frames**: at 60 fps one frame is 16.7 ms.
  - Events under ~30 ms, such as bullet transit and cavitation, are instantaneous.
  - Reflex events (30–150 ms) span 2–9 frames. **Schedule them. Never skip or merge them.**
- **Time scale**: everything here runs in the **Acute band (1×)** of `[R1-04 §0.3]`. The exceptions are slow bleeding (§5.6) and long pain phases (§9.5).

### 0.4 The layered reaction model this document feeds

| Layer | What it is | Latency after t = 0 | Neural substrate | Present when unconscious? |
|---|---|---|---|---|
| **L0 Physics** | Momentum from the projectile or blow | 0 | none (Jolt impulse) | yes |
| **L1 Reflex** | Startle, blink, withdrawal, grip clench | EMG 20–150 ms; visible 50–250 ms | brainstem, spinal cord | Startle: no (suppressed). Spinal withdrawal: sometimes (§11, row 23) |
| **L2 Postural** | Ankle, hip and stepping balance recovery; righting | EMG 70–130 ms; step toe-off ~240 ms | brainstem, spinal cord, cerebellum | no |
| **L3 Protective** | Arms out to break a fall, shielding the head, hand to wound, turning away | 100–200 ms (arms in a fall) to 300–1,000 ms (hand to wound) | subcortical + cortical | no |
| **L4 Behavioural** | Stop, fight, flee, surrender, freeze; wound check; speech | 0.3–3 s | cortex, limbic system | no |
| **L5 Physiological clock** | CNS destruction (0 s), cerebral hypoperfusion (5–15 s after flow stops), exsanguination (minutes) | 0 s to minutes | physiology sim (`[R1-03]`, `[R1-04]`) | n/a |

**Master rule `[K]`**:
- L1–L4 require a functioning nervous system for the body part involved.
- When consciousness is lost, L2–L4 go to zero within ~100 ms, and any held posture collapses unless tonic posturing replaces it (`[R1-04 §4]`).
- Spinal L1 reflexes below an intact segment can persist.

### Simulation parameters (conventions)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `com_height_standing` | 0.96 | m | 0.55 × stature | [K] |
| `omega0` | 3.20 | s⁻¹ | √(g/COM height) | [E] |
| `seg_mass_frac` | head 0.0694, trunk 0.4346, upper arm 0.0271, forearm 0.0162, hand 0.0061, thigh 0.1416, shank 0.0433, foot 0.0137 | — | Use to set PhysicalBone3D masses | [S45] |
| `reaction_tick` | 60 (physics) / 20 (decision) | Hz | Reflexes are scheduled on the physics tick | [E] |
| `loc_to_zero_L2_L4` | ≤ 100 | ms | Protective and postural layers switch off | [K] |

### Visual/behavioural checklist (conventions)
- Every hit produces a visible reaction within 2–15 frames (startle or flinch) while the character is conscious. Nothing happens instantly on the impact frame except the tiny physical impulse and the wound.
- Reactions are layered. A flinch (L1) can play on top of a stagger (L2), which can play on top of a hand moving to the wound (L3).

---

## 1. The reflex layer: the first 300 ms

### 1.1 Startle (the shot's sound, a sudden impact, a sudden touch)

**EMG onset latencies** of the acoustic startle reflex:

| Muscle (movement) | EMG onset (ms) | Visible onset (ms) `[E]` | Visible peak (ms) `[E]` | Source |
|---|---|---|---|---|
| Orbicularis oculi (blink) | 20–50; pooled mean 30 ± 1 | lid starts 40–60; closed by 80–120 | lid stays closed 100–300 in total | [S1] [S2] |
| Masseter (jaw clench) | 55–85; 67 ± 2 | 80–110 | 150–250 | [S1] [S2] |
| Sternocleidomastoid (head "duck" / flexion) | 55–85; 62 ± 13 | 90–130 | 180–300 | [S1] [S2] |
| Biceps brachii (elbows flex, arms pull in) | 85–100 | 120–160 | 200–350 | [S1] |
| Trunk flexors | ~90–120 | 130–180 | 250–400 | [K] |
| Hamstrings / quadriceps (knees flex, crouch) | 100–125 | 140–200 | 250–450 | [S1] |
| Tibialis anterior | 130–140 | 170–220 | 300–450 | [S1] |

- **Visible onset** = EMG onset + electromechanical delay (~20–40 ms) + the time to move the segment far enough to see (20–80 ms) `[E]`.
- **Pattern**: a bilaterally synchronous flexion of the upper body into a defensive posture, spreading from the head downward. The sequence is `[S3]`:
  1. blink;
  2. facial grimace;
  3. head flexion;
  4. shoulder elevation and abduction;
  5. elbow flexion and forearm pronation;
  6. fist clench;
  7. trunk flexion;
  8. knee bend.
- Landis and Hunt (1939) filmed people startled by a **pistol shot** with high-speed cameras. They found stereotyped responses (wincing, lip stretching, head and trunk movement) **within 200 ms** `[S3]`.
- **First-trial effect**: the first unexpected stimulus gives the largest kinematic and EMG response. Amplitude falls significantly after the first exposure `[S4]`. So the first shot in an encounter produces a big flinch, and later shots produce smaller ones.
- **StartReact** `[K]`: a startling stimulus releases an action the person was already preparing (running, raising the hands) ~50–100 ms earlier than normal.
- **Grip clench** `[K]`: startle, sudden loss of balance and sudden effort in one limb can close the hand involuntarily. The police literature describes this as a cause of unintentional discharges.

**Startle amplitudes** (for the animation layer; the sources give the pattern, not the angles) `[E]`:
- lids fully closed;
- brow and eyes squeezed, lip corners stretched;
- head flexion 5–15° with slight retraction;
- shoulders elevated 10–25 mm;
- upper arms abducted 5–20°;
- elbow flexion increased by 10–30°;
- forearms pronated 10–20°;
- fists closed;
- trunk flexion 3–10°;
- knee flexion 5–15°;
- COM drop 10–30 mm.
- The posture releases over 300–800 ms if nothing else takes over.

### 1.2 The pain and withdrawal reflex arc

- **Nociceptive withdrawal reflex (RIII)**: latency **~100 ms**, consistent with Aδ-fibre conduction. It is closely tied to pain perception `[S37]`.
- **Conduction arithmetic** `[K]` `[E]`:
  - Aδ fibres conduct at 5–30 m/s and C fibres at 0.5–2 m/s.
  - Over ~0.8 m from the hand to the spinal cord, that is **27–160 ms** for Aδ ("first pain": sharp and well localised) and **0.4–1.6 s** for C ("second pain": burning and diffuse).
  - So pain arrives in two waves about 1 s apart. This is most obvious in the hands and feet.
- **Radiant heat** (laser) evokes withdrawal EMG in two windows: **~250 ms (mean 187–278 ms)** and **> 1,000 ms (mean 1,172–1,460 ms)**, from Aδ and C fibres respectively `[S37]`. The data are from people with spinal cord injury, the best human heat-withdrawal latencies found in this session.
- **Stress-induced analgesia** means the reflex (L1) fires even when the person does not consciously feel pain (L4):
  - "The effects of pain are often delayed due to survival patterns secondary to 'fight or flight'" `[S6]`.
  - In the FBI study *Violent Encounters*, many officers reported not feeling pain until the event had stabilised `[S17]`.
  - At Anzio, only **32 %** of severely wounded soldiers asked for narcotics, against **83 %** of civilians with comparable injuries `[S15]`.
- **Engine rule** `[E]`:
  - Keep `reflex_gain` (L1) independent of arousal.
  - Scale conscious-pain behaviour (L4) by `pain_gain = 1 − 0.7 × arousal`, clamped to 0.2–1.0.

### 1.3 Momentum: what the hit itself does mechanically

Momentum p = m·v. The velocity given to the whole body, or to one free segment, if all the momentum were retained is p / mass `[E]`. The round data come from `[R1-01 §1]` and the punch data from `[S28]` `[S29]`.

| Projectile / blow | Mass | Velocity (m/s) | p (kg·m/s) | Whole body, 75 kg (m/s) | Head, 5.2 kg (m/s) | Forearm, 1.22 kg (m/s) |
|---|---|---|---|---|---|---|
| .22 LR | 2.6 g | 350 | 0.91 | 0.012 | 0.18 | 0.75 |
| 9 mm | 8.0 g | 360 | 2.88 | 0.038 | 0.55 | 2.36 |
| .45 ACP | 14.9 g | 255 | 3.80 | 0.051 | 0.73 | 3.11 |
| 5.56 mm M855 | 4.0 g | 940 | 3.76 | 0.050 | 0.72 | 3.08 |
| 7.62×39 mm | 8.0 g | 715 | 5.72 | 0.076 | 1.10 | 4.69 |
| 7.62×51 mm | 9.5 g | 840 | 7.98 | 0.106 | 1.53 | 6.54 |
| 12-gauge 00 buck (all 9 pellets) | 31.5 g | 400 | 12.6 | 0.168 | 2.42 | 10.3 |
| Olympic boxer straight punch (effective mass 2.9 kg) | 2.9 kg | 9.14 | 26.5 | 0.35 | — | — |
| Hook punch (hand ΔV 11 m/s; 2.9 kg assumed) | 2.9 kg | 11.0 | ~32 | ~0.43 | — | — |

**What the table means** `[E]`:

1. **Whole body.**
   - Even full retention of a buckshot load gives 0.17 m/s. That matches round one's 0.01–0.18 m/s `[R1-01 §1]`.
   - The shooter's gun recoils with at least the same momentum as the bullet (bullet plus propellant gases) `[S57]`. If the bullet could throw the target, the gun would throw the shooter.
2. **Balance thresholds.** Apply the extrapolated-COM criterion (XcoM = x + v/ω₀). The person must step when XcoM leaves the base of support (BoS). Quiet stance margins are 0.12–0.16 m forward (to the toes), 0.04–0.07 m backward (to the heels) and 0.10–0.14 m sideways. The velocity thresholds (v = margin × ω₀) are:
   - **forward 0.38–0.51 m/s**;
   - **backward 0.13–0.22 m/s**;
   - **sideways 0.32–0.45 m/s**.
   - Hip strategy adds 20–30 %.
3. **Result for firearms and punches:**
   - Handgun bullets (0.01–0.05 m/s) never force a step.
   - A shotgun load to the chest (0.17 m/s backward) can, at most, provoke a small corrective backward step in a relaxed person standing on their heels.
   - **A boxer's punch carries ~9× the momentum of a 9 mm bullet** and exceeds the backward threshold. Punches knock people back a step. Bullets do not.
4. **Segments.** The hit segment is attached to the body (effective mass ×1.5–3) and most through-and-through bullets keep most of their momentum. Model it as: segment Δv = p × `f_ret` / (segment mass × `k_attach`).
   - Example: a 9 mm stopping in the forearm gives Δv ≈ 2.36 / 2 ≈ 1.2 m/s. That is a **visible 3–6 cm flick** of the limb within ~50 ms.
   - A retained 9 mm in the head gives ~0.35 m/s: a **1–3° nod**.
   - **A visible jerk of the hit limb is realistic. A whole-body throw is not.**

### Simulation parameters (reflex layer and momentum)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `startle_emg_onset` | blink 30, masseter 67, SCM 62, biceps 85–100, thigh 100–125, tibialis anterior 130–140 | ms | Schedule per bone group | [S1] [S2] |
| `startle_visible_offset` | +30–80 | ms | Add to EMG onset | [E] |
| `startle_peak` | 200–300 (head/arms), 300–450 (legs) | ms | | [S3] [E] |
| `startle_release` | 300–800 | ms | Blend back to the prior pose or next behaviour | [E] |
| `startle_amp_pose` | head flex 5–15°, shoulders up 10–25 mm, elbows +10–30°, trunk flex 3–10°, knees 5–15°, COM −10 to −30 mm | ° / mm | Additive pose | [E] |
| `startle_habituation` | 1.0, 0.6, 0.45, 0.35, then floor 0.25 (blink floor 0.5); recovery τ 20–60 s | × | Repeated stimuli within 10 s | [E] shaped on [S4] |
| `startle_when_unconscious` | 0 | × | | [K] |
| `startle_arousal_scale` | 1 − 0.5 × arousal | × | Fighters flinch less | [E] |
| `startreact_advance` | 50–100 | ms | Only for an action already queued | [K] |
| `involuntary_trigger_pull_p` | 0.05–0.2 | p | Armed, finger on trigger, on startle or sudden balance loss | [E] on [K] |
| `nwr_latency` | 90–130 (mean 100) | ms | Mechanical or electrical noxious stimulus | [S37] |
| `heat_withdrawal_emg` | 190–280 early; 1,170–1,460 late | ms | After the skin reaches the pain threshold | [S37] |
| `first_second_pain_gap` | 0.4–1.6 | s | Distance-dependent (hand/foot longest) | [E] |
| `pain_gain` | clamp(1 − 0.7 × arousal, 0.2, 1) | × | Scales L4 pain behaviour only | [E] on [S6] [S15] [S17] |
| `f_ret` (momentum retained) | stopped in body 1.0; through-and-through handgun in limb 0.1–0.3; rifle through-and-through 0.05–0.2; shotgun close range 0.8–1.0 | fraction | | [E] |
| `k_attach` | 1.5–3 | × | Effective mass multiplier for an attached segment | [E] |
| `step_threshold_v` | fwd 0.38–0.51; back 0.13–0.22; side 0.32–0.45 | m/s | XcoM, ω₀ = 3.2 | [E] |

### Visual/behavioural checklist (reflex layer)
- On the shot's sound, a nearby conscious person blinks (~2–3 frames after the report), ducks the head and hunches the shoulders. Hands come up and in, and the knees dip slightly. The flinch is over in about half a second.
- The first shot in a sequence gives the biggest flinch. Later ones give progressively smaller flinches, but the blink never disappears.
- A limb hit by a bullet makes a small, sharp flick. The body is never pushed back. A hard punch can push someone back one step.
- There is no startle on an unconscious body. The only movement is the passive impulse.
- Audio: the flinch often comes with a sharp inhalation or a short "huh" or grunt (§9.2).

---

## 2. Incapacitation: why people stop, and why many do not

### 2.1 The four ways a person stops

| Mechanism | Timing | Reliability | Source |
|---|---|---|---|
| **1. CNS disruption**: brainstem or upper cord; bilateral or deep brain; concussive loss of consciousness | 0 s (tone lost ≤ 100 ms) | The only reliably immediate stop | [S7] [S5] [R1-04 §2–3] |
| **2. Circulatory**: cerebral hypoperfusion from loss of blood pressure | 5–15 s after cardiac output stops; minutes for slower bleeds | Certain but delayed | [S5] [S9] [R1-04 §1] [R1-03] |
| **3. Mechanical/structural**: broken femur or pelvis, severed nerve or tendon | 0–0.3 s for the affected function only | Removes one function. The person stays conscious and can keep fighting with what remains | [K] [S47] [S48] |
| **4. Psychological**: decides to stop (fear, pain, seeing blood, expectation, surrender) or faints (vasovagal) | 0.3–3 s, or later when the wound is discovered | Common but can never be counted on | [S5] [S6] |

- The 1987 FBI Wound Ballistics Workshop concluded that a handgun bullet can produce rapid incapacitation in only two ways: **disruption of the CNS** or **massive blood loss causing unconsciousness** `[S7]`.
- The FBI's 1989 paper `[S5]`:
  - "Even if the heart is instantly destroyed, there is sufficient oxygen in the brain to support full and complete voluntary action for **10–15 seconds**."
  - Psychological factors are "probably the most important" in rapid incapacitation from torso wounds, but "can never be counted on".
  - The listed psychological drivers are awareness of the injury; fear of injury, death, blood or pain; intimidation by the weapon; **preconceived notions of what people do when they are shot**; and the simple desire to quit.
- The FBI's 2014 paper `[S6]`: "Those who do stop commonly do so because they decide to, not because they have to." If the psychological factors are absent, "incapacitation can be significantly delayed even with major, unsurvivable wounds".
- The US Army's casualty model assesses impairment at fixed times after wounding: **0 s, 30 s, 5 min, 1 h, 24 h and 3 days** `[S60]`. Incapacitation is time-dependent, not one instant. Use the same idea: evaluate capability on a clock, not only at the moment of the hit.
- Baseline voluntary reaction times for L4 behaviour `[S64]` `[K]`: simple auditory reaction ~150–280 ms, visual ~190–330 ms. Choice reactions and high stress are slower. Multiply by `rt_mult_cognitive` (§10).

### 2.2 Field data

| Metric | Value | Source |
|---|---|---|
| Average handgun hits needed to stop an assailant | ~2 (1.5–2.4 across calibres) | [S8] (M–L) |
| Stopped by the first torso or head hit, 9 mm | 47 % | [S8] |
| "One-shot stop" (stopped after being shot once), 9 mm | 34 % | [S8] |
| Never incapacitated, .38 / 9 mm / .40 / .45 | 13–17 % | [S8] |
| Shotgun: stopped by one hit / never stopped | 86 % / 12 % | [S8] |
| .25 ACP (68 people): never incapacitated / stopped by one hit | 35 % / 49 % | [S8] |
| People killed by police who were shot more than once | 79 %, mean 5.98 wounds (civilian-shooter homicides: 65 %, mean 3.94) | [S61] |
| Police hit rate | 18 % (NYPD gunfights) to 35 % (Dallas); FBI quotes 20–30 % | [S61] [S6] |
| Voluntary action after the heart is destroyed | 10–15 s | [S5] [S9] |
| Shots a determined attacker can fire in 1.06 s | 4 | [S9] |
| Time for a person to fall from standing after a hit that removes muscle tone | ⅔ s to ≥ 1 s | [S10] |
| Extra shots fired after a "stop" cue (lab) | mean 2.18; last shot mean 0.36 s after the cue | [S11] |
| Time for an assailant to turn 180° and show the back | mean 0.54 s (fastest 0.37 s); fastest 0.26 s in a later study; back of the head toward the shooter in < ⅓ s | [S12] |
| Miami 1986: attacker kept fighting | After a 9 mm hit through the arm (brachial artery) and right lung, stopping near the heart; described as non-survivable and early in the fight | [S62]. The duration of several minutes is [K] |

**Interpretation for the game** `[E]`:
- A handgun torso hit stops about **40–50 %** of committed attackers on the first hit, mostly for psychological reasons. Direct CNS hits are a minority of hits.
- About **1 in 6** keep going regardless and stop only when physiology forces them to.
- People who are shot are usually **shot again**, and the shooter keeps firing for ~0.3–0.5 s after the target starts to drop. So **most falling bodies take hits while falling** `[S10]` `[S11]`.
- Bullets entering the back or the back of the head are commonly a consequence of the target **turning away** within 0.26–0.54 s `[S12]`.

### 2.3 Psychological stop model

**Probability of a psychological stop** after a handgun torso hit that does not damage the CNS or the skeleton:

| Mindset (per character) | P(stop within 3 s of the first hit) | P(stop per later hit) | P(never stops until physiology fails) | Tag |
|---|---|---|---|---|
| Surprised non-combatant (unarmed bystander, victim) | 0.7–0.9 | 0.8 | ~0.02 | [E] |
| **Committed attacker (baseline; calibrated to Ellifritz)** | **0.35–0.45** | **0.25** | **0.13–0.17** | [E] on [S8] |
| Enraged, or intoxicated with stimulants | 0.10–0.20 | 0.10 | 0.4 | [E] on [S6] |
| Trained and motivated (soldier, police) | 0.10–0.20 | 0.10 | 0.5 | [E] on [S17] |

- **Multipliers** `[E]`:
  - ×1.5 if the person sees a lot of their own blood;
  - ×1.3 for a face or genital wound;
  - ×1.3 if a limb stops working;
  - ×0.5 if unaware of the hit (§2.4);
  - ×0.3 while actively grappling.
- **What "stop" looks like** for a non-combatant `[E]`:

  | Stop form | Share |
  |---|---|
  | Sits, kneels or lies down (controlled descent, §5.1 C) | 40 % |
  | Flees | 25 % |
  | Freezes (§9.4) | 15 % |
  | Surrenders (hands up, drops the weapon, pleads) | 10 % |
  | Deliberate "drop" as if felled (the preconceived-notion effect [S5]) | 10 % |

  For a committed attacker, shift weight toward fleeing and surrender.
- **Vasovagal faint** (psychological route to real unconsciousness) `[S26]` `[S63]` `[E]`:
  - P = 0.02–0.05 for non-combatants who see their own blood or wound.
  - Prodrome 10–60 s: pallor, sweat, yawning, nausea, "I feel sick", greying vision.
  - Then a flaccid fall and ~12 s of unconsciousness (§5.6). They recover once horizontal unless also bleeding.
  - In blood-injury phobia, heart rate first rises, then drops sharply `[S63]`.

### 2.4 Not noticing the hit

Evidence:
- **Perceptual narrowing**: in 157 officers interviewed after shootings, 84 % reported diminished sound, 79 % tunnel vision, 74 % acting "on automatic pilot" and 62 % slow motion `[S18]`. This was measured in shooters, not victims. Use it as the model for anyone in high arousal `[E]`.
- **Survivor accounts** `[S16]` (anecdotal):
  - Stabbing felt "like being punched" or "someone slapping me".
  - One victim stabbed 31 times "couldn't understand why he was punching me".
  - One man stabbed in the back realised it only at home.
  - Gunshot victims describe an impact, then warmth and wetness, then realisation. Many describe a burning sensation afterwards.
- **Delayed pain**: see the Anzio data and the FBI 2014 and *Violent Encounters* findings in §1.2 `[S15]` `[S6]` `[S17]`.

Model `[E]`:

| Situation | P(unaware for > 3 s) | Discovery latency | Discovery triggers |
|---|---|---|---|
| High arousal (fighting, fleeing), torso or limb hit, no bone, joint or nerve damage | 0.3–0.5 | lognormal, median 5 s, 90th percentile 60 s | Sees blood; warm wet feeling; loss of function; weakness or dizziness; someone says "you're bleeding"; arousal drops |
| Low arousal, same wound | 0.05–0.15 | median 2 s | same |
| Hit that breaks bone, enters a joint, hits the face or genitals, or causes loss of function | ≤ 0.05 | — | Notices the function loss even if pain is muted |
| Stab to the back or flank | 0.4–0.6 | median 10 s, up to minutes | Feels "a punch"; notices later |

**The "wound check" `[K]` `[E]`**: once aware, people almost always:
1. look down at the site (0.3–1.0 s);
2. touch it with the nearest free hand (0.4–1.2 s);
3. **look at the hand** for blood (1–2 s);
4. then react emotionally: exclaim, freeze, sit or flee.

This short sequence reads as very real and should be a first-class behaviour.

### 2.5 Heart and great-vessel hits: the "10–15 seconds"

**Timeline for a heart that is effectively destroyed** (large gunshot wound, conscious committed person) `[S5]` `[S9]` `[R1-04 §1]` `[E]`:

| t | What happens |
|---|---|
| 0–0.3 s | Startle and flinch, damped by arousal. Often no pain. Keeps doing what they were doing |
| 0–5 s | Full function. Blood pressure collapses within 2–4 beats, but the brain lives on its oxygen reserve. Can run, fight and shoot (up to 4 shots per ~1 s) |
| 5–10 s | Vision greys and narrows. Legs weaken. Stride shortens and weaves. Reaches for support. Speech slurs or stops |
| 8–15 s | Loss of consciousness. Legs buckle: hypoperfusion sag (§5.1 G), then limp. Eyes open and turned up. Possible brief myoclonic jerks |
| 15–60 s | Agonal gasps, pulseless. See `[R1-04 §2.4]` and `[R1-03 §3.6]` |

**Partial or tamponading cardiac wounds** (stabs, small bullets) `[S13]` `[S14]`:
- In 7 witnessed suicides by stab wound to the heart: **4 stayed active for 2–10 min**, **2 for ~10 s**, **1 was incapacitated immediately** `[S13]`.
- Wounds of the ulnar artery, great saphenous vein, and the edge of the lung or liver allowed activity for **several hours** `[S13]`.
- Case reports describe prolonged, methodical activity after an ultimately fatal gunshot wound to the heart `[S14]`.

**Distance covered** `[E]`:
- Walking (1.4 m/s) × 10 s = 14 m. Running (5 m/s) × 10 s = 50 m.
- Hit people usually slow down, so the realistic median is **5–20 m**, with a tail to ~50 m.

**Animal proxy** `[S50]` (L):
- Deer hit through the centre of the chest by arrows **almost always take 5–10 s to fall**.
- Deer heart-shot with handgun bullets covered mean distances of ~45 m and ~90 m (ranges 0–150 m), per a secondary summary.
- Incapacitation time scales with body mass. Humans fall inside the deer mass range.

### Simulation parameters (incapacitation)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `stop_mechanism` | CNS / circulatory / mechanical / psychological | enum | Evaluate all four every decision tick | [S7] [K] |
| `heart_destroyed_voluntary_window` | 10–15 (default 12) | s | Full function about the first 5 s | [S5] [S9] |
| `heart_destroyed_greyout_start` | 5–10 | s | Stride shortens, reaches for support | [E] on [R1-04 §1] |
| `cardiac_stab_activity` | 4/7: 120–600 s; 2/7: ~10 s; 1/7: 0 s | s | Sample one class | [S13] |
| `psych_stop_p` | see §2.3 table | p | Per mindset, with multipliers | [E] on [S8] |
| `never_stop_p_committed` | 0.13–0.17 | p | Until physiology fails | [S8] |
| `hits_to_stop_mean` | ~2 | hits | Validation target for handgun sims | [S8] |
| `vasovagal_p` | 0.02–0.05 | p | Non-combatant who sees their own blood; prodrome 10–60 s | [E] on [S26] [S63] |
| `unaware_p` | 0.3–0.5 (high arousal), 0.05–0.15 (low), 0.4–0.6 (stab to back or flank) | p | | [E] on [S16] [S18] |
| `discovery_latency` | lognormal, median 5 s, P90 60 s | s | | [E] |
| `wound_check_seq` | look 0.3–1.0 s, touch 0.4–1.2 s, look at hand 1–2 s | s | Needs a free, working hand | [K] [E] |
| `turn_away_180` | 0.26–0.54 | s | Explains back wounds | [S12] |
| `simple_rt_base` | auditory 150–280, visual 190–330 | ms | L4 decisions; ×`rt_mult_cognitive` | [S64] [K] |
| `capability_eval_times` | 0 s, 30 s, 5 min, 1 h (then continuous) | — | ORCA-style checkpoints for AI and debugging | [S60] [E] |
| `shooter_overrun` | 0.3–0.5 s; ~2 extra shots | s | For NPC shooters | [S11] |

### Visual/behavioural checklist (incapacitation)
- Most people who are shot **do something other than fall over at once**. They flinch, look at the wound, clutch it, turn away, run, sit down, or keep attacking.
- Some drop immediately **without any injury that forces it**. That is a psychological drop. They are conscious, still protect their fall, and may be moaning or talking.
- A heart-shot attacker can keep coming for several seconds, then slows, weaves, sags and collapses, with no protective reflexes once unconscious.
- Some people don't notice a stab or bullet until they see blood on their hand. Then the reaction starts.
- Audio: "I'm hit", "he shot me", swearing, or nothing at all. A gasp or grunt at the moment of the hit.

---

## 3. What each hit location does (mechanics and behaviour)

The head and brain are covered in `[R1-04 §2–4]`. Rows 1–2 below only route to it.

| # | Region / structure | 0–0.5 s mechanical or neurological effect | Typical reaction if conscious (0.3–5 s) | P(falls within 2 s) and how | What remains possible | Tag |
|---|---|---|---|---|---|---|
| 1 | Brainstem, C1–C2 | Tone lost ≤ 100 ms | none | 1.0; cut strings, no protection | nothing | [R1-04 §2] |
| 2 | Cerebral hemisphere (handgun) | Usually concussive loss of consciousness; if the track crosses the motor strip, contralateral hemiplegia | If awake: confused, hand to head, falls toward the paralysed side | 0.7–0.9 | 0.1–0.3 awake at 10 s | [R1-04 §3] |
| 3 | Scalp graze / tangential skull hit | Stun; brief loss of consciousness possible | Hand to head 0.3–0.8 s. Blood reaches the eyes in 5–30 s, so blinking and wiping follow | 0.3–0.6 | Most functions | [E] on [R1-04 §3.6] |
| 4a | Eye / orbit | Pain, loss of vision on that side | Both hands over the eye 0.2–0.5 s. Turns head away, bends forward, screams | 0.3–0.5 (psychological) | Mobility | [K] [E] |
| 4b | Nose | Reflex tearing, eyes shut | Hand to nose, head tilts forward or back, spits blood | 0.1–0.2 | All | [K] |
| 4c | Mandible / jaw | Mouth cannot close, sags open | Drools blood and saliva, speech lost, leans forward to drain, spits, hand under the jaw | 0.2–0.4 (higher if concussed) | Mobility | [K] [R1-01 §10] |
| 5a | Neck vessels (carotid / jugular) | Arterial jet or venous pour | **Both hands clamp the neck in 0.3–0.8 s**, blood between the fingers. Carotid: contralateral weakness can appear within 5–20 s if collaterals are poor | Controlled descent as blood pressure falls; see `[R1-03]` for timing | Arms are busy holding the neck | [K] [E] |
| 5b | Larynx / trachea | Air leak | Coughs and sprays blood, bubbling and whistling, voice lost or hoarse. Crackling under the skin (subcutaneous emphysema) over minutes | 0.2–0.4 | Mobility | [K] |
| 6 | Cervical cord C3–C7 | Quadriplegia below the level. Breathing is diaphragmatic if C3–C5 are intact | Awake, cannot move below the level. Arm function by level: C5 shoulder, C5–6 elbow flexion, C7 elbow extension, C8–T1 hand | 1.0; cut strings, awake | Face, voice, whatever arm function the level leaves | [K] [R1-04 §6] |
| 7 | Thoracic / lumbar cord (48–64 % of spinal gunshot wounds are thoracic) | **Legs flaccid within 100 ms** | Arms fling out to catch the fall. Cannot rise. Drags himself with the arms. "I can't feel my legs." Burning band of pain at the level | 1.0; paraplegic drop (§5.1 E) | Arms, trunk above the level; can still fight or shoot | [S46] [K] |
| 8 | Shoulder girdle / humerus | Arm cannot be held against gravity; drops to the side | Other hand grabs the wrist or forearm and holds it against the belly. Shoulder hunched, trunk leans toward the injured side. **Radial nerve palsy (wrist drop) in 26.5 % of ballistic humeral shaft fractures** | 0.1–0.3 | Legs, other arm | [S47] [K] |
| 9 | Forearm / hand | Hand flicks from the impulse. Grip fails with tendon, nerve or bone damage | Hand pulled against the chest, then stares at it. Shakes the hand, tucks it into the armpit | 0.05–0.15 | All but that hand | [K] [E] |
| 10 | Chest wall / lung (not heart) | Sharp pain on each breath | Breath-hold, then shallow fast breathing (25–40/min). Hand flat over the wound. Cough, maybe blood. Short phrases. Leans forward with hands on knees ("tripod"), then sits or kneels | 0.2–0.4 now; 0.6 sit/kneel within 60 s | Most. Voice limited. Tension pneumothorax over minutes | [S49] [K] [E] |
| 11 | Heart / great vessels | Blood pressure collapses | §2.5 | Delayed 8–15 s | Everything for ~5–10 s | [S5] [S13] |
| 12 | Upper abdomen (liver, spleen, stomach) | Abdominal wall reflexively rigid (guarding) | **Doubles over 20–60°**, hands to the wound 0.4–0.8 s, knees bend, turns away. Liver injury can refer pain to the right shoulder, spleen to the left | 0.3–0.6 kneel or sit | Moves slowly. Shock develops over minutes (`[R1-03]`) | [K] |
| 13 | Lower abdomen / bowel | Visceral pain, dull at first | May carry on for seconds to minutes, then guards, hunches, lies still with knees drawn up | 0.2–0.4 | Most, at first | [S42] [K] |
| 14 | Groin / genitals | Severe visceral pain | Knees together, both hands to the groin, **drops to the knees in 0.5–2 s**. Nausea or vomiting at 30–120 s. Femoral vessels: see `[R1-03]` | 0.6–0.9 | Little for 10–60 s | [K] [E] |
| 15 | Pelvis, hip joint, acetabulum, femoral head | Cannot bear weight on that side | Leg gives way. Falls toward the injured side | 0.8–0.95 | Arms; can crawl | [S48] [E] |
| 16 | Femoral shaft | If fractured while bearing weight, **gives way within that stance phase (0.1–0.3 s)**. Thigh angulates and shortens; foot turns out 45–90° | Screams. Grabs the thigh with both hands. Every movement hurts | 0.85–0.95 (loaded); next step if unloaded | Arms. Remote spiral fractures from the fall itself are recognised | [S48] [K] |
| 17 | Thigh muscle only | Pain, "dead leg" | Limps, may keep running, hand to the thigh | 0.1–0.3 | Most | [K] [E] |
| 18 | Knee joint | Buckles into flexion, cannot straighten | Falls onto that knee, holds it | 0.6–0.8 | Arms, crawling | [K] [E] |
| 19 | Tibia / fibula | Cannot bear weight; foot flops | Falls, holds the shin | 0.7–0.9 (loaded) | Arms | [K] [E] |
| 20 | Ankle / foot | Intense pain (dense innervation) | Hops on the good leg, limps | 0.3–0.5 | Most | [K] [E] |
| 21 | Buttock / back of thigh (sciatic nerve) | Foot drop, weak knee flexion | Partial collapse, drags the foot | 0.4–0.6 | Most | [K] |

**Weapon or grip loss** `[E]`:

| Hit | P(drops a held object) |
|---|---|
| Hand or forearm with bone, tendon or nerve damage | 0.6–0.9 |
| Humerus or shoulder fracture | 0.7–0.9 (gravity pulls the arm down) |
| Radial nerve palsy | 0.5 (wrist drop weakens the finger flexors) |
| Muscle-only arm wound | 0.1–0.3 |
| Loss of consciousness | 1.0, after 0.1–0.5 s `[R1-04 §2.3]` |

A startle can instead **tighten** the grip (§1.1).

### Simulation parameters (hit locations)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `fall_p_by_region` | column "P(falls within 2 s)" above | p | Before mindset multipliers | [E] |
| `loaded_leg_giveway_delay` | 0.1–0.3 | s | Femur, tibia, pelvis or knee with the leg loaded | [K] [E] |
| `unloaded_leg_giveway` | at the next stance phase, 0.2–0.5 | s | | [E] |
| `femur_deformity` | foot external rotation 45–90°, shortening 2–5 cm, visible mid-thigh angulation 10–30° | ° / cm | Pose targets when the fracture is simulated | [K] |
| `radial_palsy_p_ballistic_humerus` | 0.265 | p | Wrist drop: wrist and fingers hang in 40–70° flexion | [S47] |
| `neck_clamp_latency` | 0.3–0.8 | s | Both hands | [E] |
| `hand_to_wound_latency` | 0.4–0.8 (torso), 0.3–0.6 (face) | s | Nearest working hand | [E] |
| `double_over_angle` | hip/trunk flexion 20–60° | ° | Abdominal and groin hits | [K] [E] |
| `chest_resp_rate` | 25–40 | /min | Shallow, splinted | [K] |
| `groin_to_knees` | 0.5–2 | s | | [K] [E] |
| `cord_T_L_legs_tone` | 0 at ≤ 0.1 s | — | Areflexic for hours to days (spinal shock) | [S46] [K] |
| `weapon_drop_p` | see the grip table above | p | | [E] |

### Visual/behavioural checklist (hit locations)
- Thigh bone hit while standing on it: the leg folds sideways at mid-thigh, the person drops toward that side, screams, and grabs the thigh. The foot lies turned outward.
- Upper-arm hit: the arm swings down and hangs. The other hand catches it and holds it to the body. The pistol falls.
- Abdominal hit: a sudden hunch, hands pressed to the belly, a stagger, then kneeling or sitting with the head down.
- Neck hit: both hands clamped to the neck with blood welling between the fingers, eyes wide. The voice is gone or gurgling if the airway is hit.
- Spine hit (mid-back): the legs simply stop and the body folds down onto the hands. The upper body keeps working. The person tries to push up and nothing below the waist responds.
- Face or eye hit: hands to the face, body turning away and bending forward, blood running through the fingers.

---

## 4. Staggering, stumbling and balance recovery

### 4.1 Strategies and latencies

| Strategy | Used when | Latency | Kinematics | Source |
|---|---|---|---|---|
| **Ankle** | Small perturbation; COM well inside the base of support | EMG 73–110 ms. Ankle muscles fire first, then thigh, then trunk | Body sways as an inverted pendulum; sway ≲ 2–4° | [S19] |
| **Hip** | Larger or faster perturbation, or narrow support | Similar latency | Hips flex or extend against the COM motion; trunk counter-rotates; arms windmill | [S19] |
| **Step (change of support)** | XcoM leaves the base of support | EMG 90–130 ms; recovery-step toe-off **0.24 ± 0.03 s** | Step 0.3–0.8 m; balance regained within about 1 s for large perturbations | [S20] |
| **Reach / grasp** | Support nearby, or the step fails | Arm EMG ~100 ms; reach 200–400 ms | Grabs a wall, rail, person, or the attacker (clinch) | [S25] [K] |
| **Trip recovery (walking)** | Foot obstructed | Reflex 60–140 ms | Early swing: elevate the foot over the obstacle. Late swing: lower the foot and shorten the step | [S23] |

### 4.2 How far recovery can go, and how many steps

- **Single-step limit**: after a release from a forward lean, young adults can recover with one step from leans up to **32.2°**, older adults only **23.5°** `[S21]`. The smallest lean tested was ~14°.
  - **Use the lean limit as the strength-dependent capability** `[E]`: `max_single_step_lean = 23.5° + 8.7° × leg_capacity`, where `leg_capacity` runs from 0 to 1.
  - Injury, blood loss, concussion and intoxication reduce `leg_capacity`.
- **Sideways**: after large lateral perturbations, young adults mostly take **one sidestep**. Weaker (older) people take **multiple steps**, and about half of those multi-step responses use a **crossover step** (the far leg crosses in front or behind) `[S22]`. A crossover is less stabilising and is a typical "stumble" look.
- **Stagger model** `[E]`:

  | Balance loss (excess XcoM velocity) | Steps | Result |
  |---|---|---|
  | < 0.3 m/s | 1 | Recovers (P 0.9) |
  | 0.3–0.8 m/s | 2–3 | Recovers (P 0.6) |
  | > 0.8 m/s, or `leg_capacity` < 0.5 | 3–6 lurching steps | Falls (P 0.5–0.9) |

  - Step duration 0.25–0.40 s. Step length 0.3–0.7 m, decreasing with `leg_capacity`.
  - Heading follows the COM velocity with ±20–40° wander.
  - Arms abduct 30–70° ("windmill") during hip-strategy moments.
- **Injured stance leg**: if the leg that must support the body is injured, the other leg must step quickly and short. If the injured leg is the one that must step, the step is short (< 0.2 m) or fails, and the person falls `[E]`.
- **Concussed or ataxic stagger** `[K]` `[E]`:
  - base of support widened +50–100 %;
  - irregular step lengths (coefficient of variation 20–40 %);
  - trunk lurches;
  - hands out for balance;
  - repeated grabbing for support;
  - knees buckle intermittently (§6.4).

### 4.3 Running when hit

- If tone is lost at 5 m/s, the body travels about **2.5–3.5 m** during the 0.5–0.7 s fall, then slides or rolls a further 0.8–3 m. Slide distance is v²/(2µg) with µ 0.4–0.6 `[E]`.
- If the person stays conscious but a leg fails, they **sprawl forward** with the arms out, often rolling onto a shoulder `[K]`.
- A committed runner who is unaware of the hit keeps running. Their stride shortens as the injury bites.

### Simulation parameters (balance)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `apr_latency` | 73–110 | ms | Automatic postural response, ankle first | [S19] |
| `step_toe_off` | 0.24 ± 0.03 | s | After the perturbation | [S20] |
| `balance_regain_time` | ~1 | s | Large perturbations | [S20] |
| `max_single_step_lean` | 23.5 + 8.7 × `leg_capacity` | ° | Young healthy = 32.2 | [S21] [E] |
| `lateral_crossover_p` | 0.5 of multi-step responses | p | Weak or injured | [S22] |
| `trip_reflex_latency` | 60–140 | ms | Elevating or lowering strategy | [S23] |
| `stagger_steps` | 1 / 2–3 / 3–6 by severity | steps | Table above | [E] |
| `stagger_step_duration` | 0.25–0.40 | s | | [E] |
| `stagger_heading_noise` | ±20–40 | ° | | [E] |
| `ataxic_base_widen` | +50–100 | % | Concussion, cerebellar injury, blood loss | [K] [E] |
| `run_collapse_travel` | 2.5–3.5 airborne/folding + 0.8–3 slide | m | From 5 m/s | [E] |

### Visual/behavioural checklist (balance)
- A hit person who does not fall sways, then either plants the feet (small hip wiggle, arms flung out) or takes one quick step.
- A weakened person lurches through several short, uneven steps, sometimes crossing one foot over the other, reaching for a wall or for the attacker, and often ends on the knees.
- Staggering should look like losing a race against the COM: each step lands a bit too late and a bit too short.
- A runner who collapses keeps travelling forward several metres and skids.
- Audio: scuffing feet, hands slapping a wall, hard breathing.

---

## 5. How the body drops

### 5.1 Seven fall archetypes

| Archetype | Trigger | Tone change | Knees/hips reach the ground | Torso/head reach the ground | Motion | Protective arms | Head impact speed | Tag |
|---|---|---|---|---|---|---|---|---|
| **A. Cut-strings crumple** | Brainstem hit; cardiac arrest at the end of the 10–15 s window; deep syncope; knockout without posturing | ≤ 100 ms | 0.3–0.5 s | **0.6–1.2 s** | Knees and hips fold (concertina), trunk pitches along the lean, head whips last | **none** | 3–5 m/s | [R1-04 §2.3] [S10] [S33] [E] |
| **B. Rigid topple ("plank")** | Tonic posturing or fencing in a knockout; decerebrate posturing; knees locked | ≤ 100 ms (tonic) | feet stay planted | **1.0–1.6 s** (from 10° down to 2° initial lean) | Rotates about the ankles as one piece | none (arms fixed in the posture) | **5–7 m/s** (face or back of the head) | [E] §5.2 [S51] |
| **C. Controlled descent** | Conscious weakness, dizziness, breathlessness, pain, surrender | 0.5–3 s | 1–5 s | 2–10 s | Hand on a wall or knee, kneels, sits, lies down, often onto one side | yes, deliberate | < 1 m/s | [K] |
| **D. One-sided buckle** | Leg, pelvis or knee failure; hemiplegia | 0.1–0.3 s (stance phase) | 0.4–0.8 s | 0.8–1.4 s | Drops toward the injured side, rotating toward it; hops on the good leg | yes, arms out in 100–200 ms | 1–3 m/s; hands or shoulder usually land first | [S25] [E] |
| **E. Paraplegic drop** | Thoracic or lumbar cord | ≤ 100 ms (legs only) | 0.3–0.5 s (buttocks or knees) | 0.6–1.0 s | Legs fold; sits down hard or pitches along the motion | yes (arms work) | 1–3 m/s | [K] |
| **F. Stumble-fall** | Balance loss while moving; rocked | — | after 1–6 steps, 0.5–3 s | +0.3–0.6 s | Sprawls forward, knees and hands first, rolls | yes, if conscious | 1–4 m/s | [S24] [E] |
| **G. Hypoperfusion sag** | Heart, aorta or major bleed at the end of consciousness | 1–3 s of greying and staggering | 1–2 s | 2–4 s | Slows, sways, sags to the knees, slumps forward or sideways | fades from partial to none | 2–4 m/s | [S26] [E] |

**Check against data**:
- The time to fall from standing after a tone-abolishing hit is ⅔ s to ≥ 1 s `[S10]`.
- Unavoidable falls take 700–1,200 ms from balance loss to impact `[S25]`.
- Measured head impact velocities for standing-height falls with test dummies: 95 % prediction interval **2.02–7.41 m/s** `[S51]`.

### 5.2 Arithmetic for the rigid topple `[E]`

- Model the body as a uniform rod of length L = 1.75 m pivoting at the feet: θ̈ = (3g / 2L) sin θ, so ω² = 3 × 9.81 / 3.5 = 8.41 and **ω = 2.90 s⁻¹**.
- Small-angle phase: θ = θ₀ cosh(ωt), up to 0.5 rad.
  - From 5°: t = 0.84 s. From 10°: 0.59 s. From 2°: 1.16 s.
- Phase from 0.5 rad to horizontal, integrating by energy: 0.25 s + 0.17 s = **0.42 s**.
- **Total: 1.0 s (10° start), 1.26 s (5°), 1.58 s (2°).**
- Speed of the top of the head at impact: L × θ̇ = 1.75 × 4.09 ≈ **7.2 m/s**. The head centre (~1.6 m) moves at ~6.5 m/s. This matches the upper tail of `[S51]`.
- **Crumple (A)**: the COM drops ~0.7 m. Free fall alone takes 0.38 s. With the knees folding and then toppling, 0.6–1.0 s. The head falls from kneeling height (~0.9 m): √(2 × 9.81 × 0.9) ≈ 4.2 m/s.

### 5.3 Protective behaviour while conscious

- **Arms**: a startle-like burst in biceps and triceps ~**100 ms** after balance is lost, then the arms move quickly into a protective orientation `[S25]`. Young adults show early (< 200 ms) arm reactions in **91 %** of evoked falls `[S25]`. The drop took 601–816 ms in the lab, so there is time.
- **Posture for arrest** `[K]` `[E]`:
  - shoulders flexed 60–100°;
  - elbows 10–30° flexed, yielding on impact;
  - wrists extended (dorsiflexed) 60–90°;
  - fingers spread;
  - head turned aside (forward fall) or chin tucked (backward fall);
  - knees first when falling forward; hip and side landing when falling sideways; a roll if moving.
- **Hands do not guarantee head protection**. In 227 filmed real falls (older adults), hands hit the ground in **74 %** of falls and the head in **37 %**. Hand impact did **not** reduce the chance of head impact `[S24]`.
  - Causes in that study: incorrect weight shift 41 %, trip 21 %, hit or bump 11 %, loss of support 11 %, **collapse 11 %** `[S24]`.
- **Other conscious protective acts** `[K]`:
  - turning the face away from the attacker or ground;
  - raising the forearms in front of the face;
  - curling;
  - grabbing a support;
  - sitting down deliberately when faint.
  - People with non-organic "drop attacks" typically land on their **knees** (bruised knees). True loss of consciousness produces **face and head** injuries `[S53]`.

### 5.4 Unconscious falls

- There are **no protective reflexes**. "No protective action – floppy" is one of the six internationally agreed video signs of concussion `[S36]`.
- Cardiac arrest gives "a sudden, crashing collapse with no attempt at self-protection, the body behaving almost like a rag doll". Heat or exercise collapse is a slower crumple `[S53]`.
- The face or back of the head hits the ground. In one-punch assault deaths, the fall is a large part of the injury: falling because of the assault was associated with more injuries (odds ratio 2.87) `[S52]`.
- **Bounce** `[E]`: the head rebounds 1–5 cm after a hard-floor impact. Limbs flop and settle within 0.3–1.0 s. Nothing is braced.

### 5.5 Which way the body falls

1. **Along the COM velocity at the moment tone is lost.** If the body is roughly stationary, along the current lean `[E]`.
2. One leg fails: toward that leg, sideways and forward `[K]`.
3. Hemiplegia: toward the paralysed side `[R1-04 §3.3]`.
4. Running: forward (§4.3).
5. Hit while backing away or turning: backward or twisting `[K]`.
6. Hook-punch knockout: the body tends to follow the head's rotation, spinning a quarter to half turn, then falls sideways or forward `[K]`.
7. **Bullets do not choose the direction.** Their momentum is negligible (§1.3).

- **Default when perfectly upright and stationary** `[E]` (L; no human dataset found): forward 45 %, backward 25 %, sideways 30 %.
  - Bias the direction toward the side of a weakened limb and away from the direction of the attacker's push (punch only).

### 5.6 The hypoperfusion collapse sequence (syncope data as a proxy)

Healthy volunteers were made to faint on video (Lempert 1994, 42 complete syncopes) `[S26]`:

| Finding | Value |
|---|---|
| Duration of unconsciousness | **12.1 ± 4.4 s** |
| Myoclonic jerks (multifocal, arrhythmic, in proximal and distal muscles; generalised jerks common) | **90 %** |
| Other movements (head turns, oral automatisms, righting movements) | **79 %** |
| Eyes | **Open** throughout; early **upward deviation** common |

Eye movements in fainting (14 subjects) `[S27]`:
- 7: tonic upward deviation;
- 6: downbeat nystagmus, then upward deviation;
- 1: eyes stayed in the primary position.

Game use `[E]`:
- A victim bleeding out, or with a destroyed heart, passes through the same picture at the end of the consciousness window: eyes open and turned up, a few irregular jerks for 5–15 s, head turning, lip smacking.
- **Unlike a faint, they do not wake up.** Agonal breathing and arrest follow `[R1-04]`.
- Slower bleeds (limb arteries; minutes, see `[R1-03]`): anxious and restless, then "I need to sit down", controlled descent (C), then confused and drowsy, then unresponsive.

### Simulation parameters (falls)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `fall_archetype` | A–G | enum | Selected by §11 | [E] |
| `crumple_ground_time` | 0.6–1.2 | s | Archetype A | [S10] [R1-04] |
| `topple_ground_time` | 1.0–1.6 | s | Rigid; θ₀ 10° to 2° | [E] |
| `topple_head_v` | 5–7 | m/s | | [E] [S51] |
| `crumple_head_v` | 3–5 | m/s | | [E] |
| `protective_arm_onset` | ~100 (burst), < 200 (orientation) | ms | Conscious only | [S25] |
| `protective_arm_p_conscious` | 0.9 | p | Young, alert | [S25] |
| `hand_impact_p` / `head_impact_p` | 0.74 / 0.37 | p | Older-adult falls; use as a floor for impaired characters | [S24] |
| `arrest_pose` | shoulders 60–100° flexed, elbows 10–30°, wrists 60–90° extended | ° | IK targets to the ground contact point | [E] |
| `unconscious_protect` | 0 | — | "No protective action – floppy" | [S36] |
| `head_bounce` | 1–5 | cm | Hard floor | [E] |
| `fall_dir_default` | fwd 0.45 / back 0.25 / side 0.30 | p | Stationary upright only | [E] (L) |
| `syncope_loc` | 12.1 ± 4.4 | s | Faint, not bleeding | [S26] |
| `syncope_myoclonus_p` | 0.9 | p | Multifocal, arrhythmic, 5–15 s | [S26] |
| `syncope_eye_up_p` | 0.93 (13/14) | p | Some start with downbeat nystagmus | [S27] |

### Visual/behavioural checklist (falls)
- **Conscious** fall: arms shoot out, hands hit first, the head is turned aside, and the body rolls onto a hip or shoulder. The person immediately tries to move or get up.
- **Unconscious** fall: no arms, the face or back of the head smacks the floor with a small bounce, and the limbs flop into place. Eyes are open and staring or rolled up.
- **Stiff knockout**: the body tips over like a plank in about a second, arms locked in odd positions, and lands flat. It is the hardest head impact.
- **Faint or bleed-out**: legs wobble, knees go, the body slumps. Eyes turn up. A few twitches or jerks for several seconds.
- **Spine hit**: the legs vanish from under the body, which sits or drops onto the hands.
- Audio: impact thuds scaled to speed (a heavy crack for a topple, a dull thud for a crumple), exhaled air forced out on impact, clothing and gear sounds.

---

## 6. Blunt force: punches, kicks and the hammer

### 6.1 Punch mechanics (building on `[R1-02 §3.5]`)

| Punch | Hand velocity | Force | Head linear acceleration | Head rotational acceleration | Source |
|---|---|---|---|---|---|
| Olympic boxer, straight punch to the face | 9.14 ± 2.06 m/s | 3,427 ± 811 N (effective mass 2.9 kg) | 58 ± 13 g | 6,343 ± 1,789 rad/s² | [S28] |
| Hook | ΔV 11.0 ± 3.4 m/s | 4,405 ± 2,318 N (neck load 855 N) | 71.2 ± 32.2 g | 9,306 ± 4,485 rad/s² | [S29] |
| Punches that caused loss of consciousness vs those that did not (hooks to the side of the jaw) | — | — | 81.5 ± 39.8 g vs 47.9 ± 21.4 g | **5.9 ± 2.4 vs 3.5 ± 1.6 krad/s²** | [S31] |
| Proposed thresholds | concussion ~4,500 rad/s²; diffuse axonal injury / acute subdural haematoma ~10,000 rad/s² | | | | [S30] |
| Headgear effect (hook) | — | — | — | falls to ~1,740 rad/s² | [S30] |

- Boxing punches have a **65 mm** effective lever arm about the head's centre of gravity, against 34 mm in American football, so they are **rotation-heavy** `[S29]`.
- The rotational mechanism explains why the chin and jaw are "knockout buttons": about 90 % of brain shear strain is attributed to rotation `[S32]`.
- In MMA knockouts, **53.9 %** of the knockout strikes landed on the jaw region `[S34]`.
- **Game conversion** `[E]`: α_peak ≈ F × r_eff / I_eff, with r_eff = 0.065 m and I_eff = 0.035 kg·m² (head plus neck coupling).
  - Check: 3,427 × 0.065 / 0.035 = 6,364 rad/s² against 6,343 measured.
  - Location multipliers: side of the jaw 1.0; chin (uppercut) 0.9; temple 0.9; back of the head 0.6; straight to the forehead 0.5.
  - Untrained bare-knuckle punches (500–1,500 N, `[R1-02]`) give ~900–2,800 rad/s².
- **Head snap** `[E]`:
  - Angular velocity peak ω ≈ 0.64 × α_peak × T for a half-sine pulse of T = 8–15 ms. For α = 6,000 rad/s² and T = 10 ms, ω ≈ 38 rad/s.
  - Head excursion peaks **50–100 ms** after contact. A large head displacement occurs within 100 ms `[S33]`.
  - Amplitude 20–60°, limited by the neck's range of motion (rotation 70–80°, lateral flexion 35–45°, extension 60–75°, flexion 45–60° `[K]`). Recoil over 100–300 ms.

### 6.2 Outcome ladder per head blow `[E]` (anchored on [S30] [S31])

| α_peak (rad/s²) | Most likely outcome |
|---|---|
| < 1,500 | Pain, flinch, head turned. No neurological effect |
| 1,500–4,500 | Stunned 0.5–3 s: P(dazed) 0.2–0.5, P(loss of consciousness) < 0.1 |
| 4,500–7,000 | P(loss of consciousness) 0.2–0.6; otherwise "rocked" (§6.4) |
| 7,000–10,000 | P(loss of consciousness) 0.6–0.9 |
| > 10,000 | P(loss of consciousness) > 0.9; risk of diffuse axonal injury or acute subdural haematoma |

- **Logistic model**: P_LOC = 1 / (1 + exp(−(α − 6,000) / 1,200)). This gives 0.11 at 3,500, 0.22 at 4,500, 0.5 at 6,000 and 0.94 at 9,300.
- **Accumulation**: each head blow within 60 s lowers the midpoint by 5 %. A second head blow while already rocked lowers it by 20 %.

### 6.3 Knockout phenomenology

- **Tone is lost immediately**, at a speed rivalling or exceeding a voluntary movement `[S33]`.
- **Posture**: tonic "fencing" posturing in ~66 % of knockout videos (`[R1-04 §3.6]`, `[S35]`).
- **Body collapse pattern** `[E]`:
  - limp crumple (A) 55 %;
  - stiff topple (B) 30 %;
  - "delayed" stagger for 1–3 steps, then a fall (F with loss of consciousness) 15 %.
- **Eyes**: open, glassy, drifting up or apart, or "rolled back" (Bell's phenomenon, the upward roll with loss of consciousness, present in ~75 % of people) `[S54]`. Lids half-open.
- **Airway**: snoring or stertor if lying on the back `[R1-04 §3.6]`.
- **Duration**: 5–60 s, tail to 300 s `[R1-04 §3.7]`.
- **Waking**:
  1. eyes open first;
  2. blank stare;
  3. tries to rise and fails (motor incoordination);
  4. confused and repeats questions.
- **Blows after a knockout**: in MMA the mean time from the knockout strike to the referee stopping the fight is **3.5 s (range 0–20 s)** `[S34]`. So an unconscious body commonly takes several more blows.
  - Show these as **purely passive**: the head bounces, there is no guard and no flinch. Posturing is possible.
- **Flash knockdown**: down briefly with no, or only momentary, loss of consciousness. Gets up at once. Mild concussion `[S56]`.
- Of UFC matches reviewed (n = 503), 12 % ended in knockout and 24 % in technical knockout `[S34]`.

### 6.4 Getting "rocked"

- **Definition**: "motor incoordination" = unsteady on the feet, including losing balance, staggering or stumbling, struggling to get up, or falling `[S36]`.
- In the NFL, "slow to get up" was the most sensitive video sign (66 %). A blank or vacant look and an impact seizure were the most specific (100 %) `[S36]`.
- Frequencies among concussed athletes: slow to get up 65.9 %, motor incoordination 28.4 % `[S36]`.
- **Game model** `[E]`:
  - Severe phase 5–60 s, residual 5–30 min.
  - Postural sway ×2–3.
  - Reaction time +30–80 %.
  - P(knee buckle) 0.1–0.3 per second during the first 10 s. The knees dip 10–30° and recover, or the person goes down.
  - Hands seek support or clinch the attacker.
  - Blank stare P 0.05–0.3.
  - Horizontal nystagmus in the eyes P 0.3.
  - Guard drops. Delayed or absent defensive reactions to the next blow, so P(flinch) falls to 0.3–0.6.

### 6.5 Body blows

| Blow | Immediate | Delay | Behaviour | Duration | Tag |
|---|---|---|---|---|---|
| **Liver** (right lower ribs) | Severe pain, conscious | **Collapse 1–3 s after the blow** | Clutches the right side, drops to the knees, curls on the side, face contorted, cannot rise | 10 s to a few minutes | [S55] (L) [K] |
| **Solar plexus / epigastrium ("winded")** | Diaphragm spasm, cannot inhale or exhale | 0 | Bent over, hands on the belly or knees. Mouth open, **silent failed gasps**, then a whooping inhalation. Panic | 5–30 s typical; eases within 1–2 min | [S55] (L) [K] |
| **Ribs** | Sharp pain; a fracture hurts on every breath | 0 | Holds the side, shallow breaths, avoids twisting | minutes and longer | [K] |
| **Groin** | Visceral pain peaks over 0.5–2 s | 0.5–2 s | See §3, row 14 | 10–60 s incapacitated | [K] |
| **Kidney / flank** | Deep pain | 0.5–1 s | Arches away from the blow, hand to the back | seconds to minutes | [K] |

### 6.6 The hammer

- **Head**: the same outcome ladder as punches, but with much higher linear and local loads. Skull fracture and depressed fracture are covered in `[R1-02 §5]`. Expect knockout, or focal deficits (§10) from a depressed fracture over the motor strip.
- **Limbs** `[K]`:
  - Fracture gives immediate loss of function (§3).
  - A blow to the ulnar nerve at the elbow causes tingling and a weak hand for 5–30 s.
  - Kneecap: the knee buckles.
  - Fingers or hand: the hand is snatched back, shaken, then tucked under the armpit or held against the belly.
  - Shin: the person hops and holds the shin.

### Simulation parameters (blunt)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `punch_r_eff` / `head_I_eff` | 0.065 / 0.035 | m / kg·m² | α = F·r/I | [S29] [E] |
| `alpha_loc_mult` | jaw 1.0, chin 0.9, temple 0.9, occiput 0.6, forehead 0.5 | × | | [E] on [S31] [S34] |
| `P_LOC(α)` | 1/(1+exp(−(α−6000)/1200)) | p | Midpoint −5 % per head blow within 60 s | [E] on [S30] [S31] |
| `head_snap_peak_t` | 50–100 | ms | | [S33] [E] |
| `head_snap_amp` | 20–60, clamped to the neck range | ° | | [E] |
| `ko_tone_loss` | ≤ 100 | ms | | [S33] |
| `ko_collapse_mix` | crumple 0.55 / topple 0.30 / delayed 0.15 | p | | [E] |
| `ko_eyes` | open 0.8; rolled up (Bell's) 0.5 of those | p | | [S54] [K] |
| `post_ko_passive_strikes` | 3.5 (0–20) | s | Expected player behaviour | [S34] |
| `rocked_duration` | 5–60 (severe), 300–1,800 (residual) | s | | [E] |
| `rocked_knee_buckle_rate` | 0.1–0.3 | /s | First 10 s | [E] |
| `rocked_rt_mult` | 1.3–1.8 | × | | [E] |
| `liver_delay` | 1–3 | s | | [S55] (L) |
| `winded_apnoea` | 5–30 (up to 120) | s | | [S55] (L) [K] |

### Visual/behavioural checklist (blunt)
- A clean hook to the jaw: the head whips round in a tenth of a second, the eyes go blank, and the legs go before the head comes back. The body either folds or tips over stiff with arms locked. It hits the floor with no hands.
- A rocked person: knees dip and recover, feet wide, hands grabbing, eyes unfocused. They are slow to react to the next punch.
- A liver shot: a delay of a second or two, then the person folds to the knees holding the right side and cannot get up, conscious and grimacing.
- Winded: the mouth opens, nothing comes in for several seconds, then a loud whoop.
- Audio: impact slap or thud, forced "oof" from the chest, snoring breaths from an unconscious person on their back.

---

## 7. Sharp force: cuts and stabs

- **Perception**:
  - Stabs are often felt as a **punch, slap or scratch**, or as a hot line.
  - Realisation comes on seeing blood or feeling warmth `[S16]`.
  - Stabs to the torso may draw no reaction beyond a flinch, so an attacker can deliver several stabs before the victim realises.
- **Slash to the forearm** (timeline) `[S37]` `[E]`:

  | t | Event |
  |---|---|
  | 0–50 ms | Blade contact |
  | ~100 ms | Withdrawal reflex (RIII): elbow flexes, arm pulled toward the body |
  | 150–250 ms | Visible yank, with a startle on top |
  | 200–500 ms | Other hand grabs the cut forearm |
  | 0.5–2 s | Looks at the wound |
  | 1–3 s | Bleeding clearly visible (`[R1-02 §2]`, `[R1-03]`) |

  The limb travels 5–20 cm in 150–300 ms.
- **Defensive behaviour against a visible blade** `[K]`: forearms raised in front of the face and chest, palms out or crossed, head down and turned away, trunk turned sideways, stepping back. Sometimes the person grabs the blade or the attacker's wrist.
  - This behaviour produces the defence-wound pattern of `[R1-02 §2.7]`: present in 41–48 % of sharp-force homicide victims; of those, hands 80 %, forearms 65 %.
  - Head-avoidance movements to a looming object are faster than orienting movements `[S65]`.
- **Face cut** `[E]`: hands to the face in 0.2–0.5 s, eyes shut, turns away, bends forward. Blood from an eyebrow cut blinds that eye within seconds (`[R1-02]`).
- **Neck cut**: both hands clamp the neck (§3, row 5a).
- **Stab to the heart**: activity for 10 s to 10 min (§2.5) `[S13]`.
- **Stab to the abdomen**: may keep fighting. Guarding and hunching come later, as pain and blood loss progress `[K]`.

### Simulation parameters (sharp)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `cut_withdraw_emg` | ~100 | ms | | [S37] |
| `cut_withdraw_visible` | 150–250 | ms | | [E] |
| `cut_withdraw_distance` | 5–20 in 150–300 ms | cm | | [E] |
| `other_hand_grab` | 0.2–0.5 | s | | [E] |
| `stab_unaware_p` | 0.3–0.6 (torso), 0.4–0.6 (back) | p | | [E] on [S16] |
| `defensive_arms_p` | 0.5–0.8 | p | Blade visible, victim facing the attacker | [E] |
| `defensive_arms_latency` | 0.2–0.4 after the threat is seen | s | | [E] on [S65] |

### Visual/behavioural checklist (sharp)
- A slash makes the arm jerk away and the other hand grab it. The person then stares at the cut before the pain face arrives.
- Stabs to the body often look like punches. The victim may keep struggling for several more stabs, then suddenly look down.
- Against a knife held in view: forearms up and out, head tucked and turned, backing away, sometimes grabbing the blade.
- Audio: sharp inhalation, "ah!" or swearing when the cut is noticed. Often silence during stabbing, then a scream when blood is seen.

---

## 8. Burns: withdrawal and behaviour

- **Pain threshold**: ~**43–45 °C** at the skin (values of 43 °C and 44.6 °C are reported). Burn injury begins when the dermo-epidermal junction exceeds 44 °C `[S38]` `[R1-02 §6.2]`.
- **Reaction time used by standards**: ISO 13732-1 takes **0.5 s** as the minimum contact period for unintentional touching of a hot surface by healthy adults `[S38]`.
- **Real contact with hot metal above 70 °C** typically lasts **1–5 s** before release, because of grip, surprise and slow letting go `[S38]`.
- **Latency chain** `[E]`:
  1. time for the skin to reach the pain threshold (with a torch at the default flux of `[R1-02 §6.3]`, well under ~0.3 s);
  2. plus heat-withdrawal EMG of 190–280 ms (Aδ) `[S37]`;
  3. so the **visible withdrawal starts ~0.2–0.6 s after the flame touches the skin**.
  4. Second (C-fibre) pain follows about 1 s later and drives sustained behaviour.
- **Behaviour when free to move** `[K]` `[E]`:
  - **Hand**: snatched back (elbow flexion and shoulder extension, 20–40 cm in 200–300 ms). Then shaken, blown on, pressed into the armpit or against clothing, the wrist held by the other hand.
  - **Face**: eyes squeezed shut. The blink is the fastest component (`[S1]`). The head turns and pulls back within 100–250 ms, hands come up to shield it, and the body turns away.
  - **Burning clothing**: people tend to run and beat at the flames. Stopping, dropping and rolling is trained, not instinctive.
- **Behaviour when restrained**:
  - maximal struggling, arching and writhing;
  - screams in bursts, one per breath;
  - hyperventilation;
  - vasovagal fainting possible after 10–60 s of extreme pain `[E]`.
- **Over the following minutes** `[R1-02 §6.1]`: continuous burning pain. Partial-thickness areas hurt most. The centres of full-thickness areas are painless.

### Simulation parameters (burns)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `heat_pain_threshold` | 43–45 | °C | Skin / dermo-epidermal junction | [S38] |
| `burn_withdraw_onset` | t(threshold) + 0.19–0.28 | s | ≈ 0.2–0.6 s after flame contact | [S37] [E] |
| `burn_second_pain` | +1.2–1.5 | s | Sustained behaviour | [S37] |
| `unintentional_contact_min` | 0.5 | s | ISO reference | [S38] |
| `hot_metal_contact_real` | 1–5 | s | Grip or surprise | [S38] |
| `hand_snatch` | 20–40 in 200–300 ms | cm | | [E] |
| `face_turn_away` | 100–250 | ms | After the flash or heat | [E] |
| `restrained_scream_rate` | 1 per 1.5–4 | s | Breath-limited | [E] |

### Visual/behavioural checklist (burns)
- A flame on the hand: a brief delay (a fraction of a second), the hand snaps back, then shaking and blowing, the hand clamped under the armpit, pacing, swearing.
- A flame near the face: eyes slammed shut, head wrenched away, hands up, stumbling back.
- Restrained: violent struggling and arching, rhythmic screaming with gasps between, then exhaustion, trembling and moaning.

---

## 9. Pain behaviour, vocalisation, shock and dissociation

### 9.1 The pain face

- Four actions carry most of the information about pain `[S39]`:
  - brow lowering (AU4);
  - orbital tightening (AU6/AU7);
  - levator contraction, i.e. nose wrinkle and upper-lip raise (AU9/AU10);
  - eye closure (AU43).
- The Prkachin–Solomon Pain Intensity score (PSPI) = AU4 + max(AU6, AU7) + max(AU9, AU10) + AU43, on a 0–16 scale `[S39]`.
- Map to the game's pain level (0–10) as **PSPI ≈ 1.6 × pain** `[E]`. Add a lip stretch (AU20) and a clenched jaw at moderate pain, and an open mouth (AU25–27) during vocalisation `[K]`.
- **Timing** `[E]`:
  - onset 150–400 ms after the pain is perceived;
  - peak 0.5–1.5 s;
  - then sustained, with fluctuations every 1–3 s.
- Scale by `pain_gain` (§1.2). A fighter in high arousal may show a snarl or effort face instead.

### 9.2 Vocalisation

| Type | When | Acoustics | Duration | Tag |
|---|---|---|---|---|
| Impact grunt / "oof" | Blows to the torso, shots, landing from a fall | Forced expiration, noisy, low F0 | 100–300 ms | [K] |
| Startle cry / yelp | Unexpected hit, sudden pain | Brief jump in F0 | 150–400 ms | [K] |
| **Scream** | Severe acute pain, terror, burns | Loud, high F0, **amplitude modulated at 30–150 Hz ("roughness")**; normal speech modulates at 4–5 Hz | 0.5–3 s per breath | [S40] |
| Pain cry (intensity-graded) | Rising pain | Mean F0, F0 range, loudness and **non-linear phenomena (rough, chaotic voicing)** all rise with pain; cries get longer and less stable | 0.5–3 s | [S41] |
| Moan / groan | Sustained pain; semi-conscious (GCS verbal 2) | Low F0, voiced, on expiration | 0.5–2 s | [K] |
| Words | Conscious: "I'm shot", "help", "stop", names, prayer, swearing | — | — | [K] |
| Expiratory grunting breaths | Splinting for chest or abdominal pain | Short, voiced exhalations | every breath | [K] |
| Gurgling / wet cough | Blood in the airway | — | — | [R1-04] |
| **Silence** | Shock, low blood pressure, chest wound with no breath to spare, dissociation, a focused fighter | — | — | [K] |

- **F0 guide** `[K]` (L):
  - adult male speech 85–155 Hz;
  - pain moans 100–250 Hz;
  - screams 300–900+ Hz;
  - adult female: multiply by ~1.7–2.
- A person's voice pitch keeps its individual differences from speech through to screams and pain cries `[S41]`. Derive scream pitch from the character's speaking pitch.
- **Breathing limits the voice** `[E]`:
  - One scream uses one breath, so there is one scream per 1.5–4 s.
  - Chest wounds and pneumothorax cap bursts at 0.3–1 s and at lower loudness.
  - A winded person is silent (§6.5).
  - As blood pressure falls, loudness falls. Pre-arrest victims are silent.

### 9.3 Body posture in pain

| Behaviour | Typical cause | Detail | Tag |
|---|---|---|---|
| Guarding / splinting | Any wound | Muscles over the wound tense; limb held against the body | [K] |
| **Pressing or holding the wound** | Any reachable wound | Touch reduces pain through subcortical gating of nociceptive input (it even suppresses the nociceptive blink reflex) | [S43] |
| Doubling over | Abdomen, groin | Hip/trunk flexion 30–90° | [K] |
| Fetal curl on the ground | Abdominal or groin pain, fear | Hips 90–120°, knees 100–130°, arms wrapped around the body, head flexed | [K] [E] |
| **Writhing / rolling** | Colicky visceral pain, burns, extreme acute pain | Restless, tries position after position | [S42] |
| **Lying absolutely still** | Peritoneal irritation, fractures, chest wall pain, shock | Any movement hurts, or there is no energy; peritonitis: on the back with the knees drawn up | [S42] |
| Rocking, rubbing, shaking the limb | Limb pain, burns | | [K] |
| Crawling away | Legs useless, threat present | Pulls with the forearms | [K] |
| Rolling onto the side | Face or jaw wounds, vomiting | Drains blood and keeps the airway clear | [K] |

### 9.4 Freeze, tonic immobility and dissociation

- **Freeze**: angry faces reduce body sway and slow the heart (bradycardia) `[S44]`. In a violent encounter, show 0.5–3 s of stillness with a fixed stare after a threat or a first hit `[E]`.
- **Tonic immobility**: reversible physical immobility and muscular rigidity lasting **seconds to hours** `[S44]`. P = 0.02–0.1 for a non-combatant under an overwhelming attack `[E]`. The eyes are open and the body stiff, with little or no vocalisation.
- **Dissociation**: blank stare, delayed or absent responses, detached calm, perceptual narrowing (84 % reduced hearing, 79 % tunnel vision in shooting survivors `[S18]`).
- **Shock behaviour over minutes**: anxious and restless (class II), confused (class III), lethargic and unresponsive (class IV) `[R1-03 §3]`.

### 9.5 Pain over longer periods `[E]`

- 0–10 s: acute (scream, grimace, reflexes).
- 10–60 s: second pain and awareness (crying, calling out, trying to escape).
- 1–10 min: fatigue lowers loudness, moaning and whimpering, shivering and trembling.
- From then on: tracks shock class.
- Nausea and vomiting are common after abdominal, groin and head injury: P 0.2–0.4 within 1–10 min `[K]`.

### Simulation parameters (pain behaviour)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `pspi` | 1.6 × pain (0–16) | — | AU4, AU6/7, AU9/10, AU43 blendshape weights | [S39] [E] |
| `pain_face_onset` / `peak` | 150–400 / 500–1,500 | ms | | [E] |
| `scream_roughness_am` | 30–150 | Hz | Amplitude modulation for audio synthesis or selection | [S40] |
| `scream_f0` | 300–900+ (male), ×1.7–2 (female) | Hz | Derive from the speaking F0 | [K] (L) |
| `vocal_per_breath` | 1 | — | 1.5–4 s cycle | [E] |
| `chest_wound_vocal_cap` | 0.3–1 s bursts, −6 to −12 dB | s / dB | | [E] |
| `hold_wound_p` | 0.7–0.9 (torso, neck, face); 0.4–0.6 (limb) | p | Conscious, free working hand, not on the neglected side | [E] on [S43] |
| `writhe_vs_still` | writhe: colic-type visceral pain and burns; still: peritoneal, fracture, chest wall, shock | rule | | [S42] |
| `freeze_duration` | 0.5–3 | s | | [E] on [S44] |
| `tonic_immobility_p` | 0.02–0.1 | p | Seconds to hours | [S44] [E] |
| `vomit_p` | 0.2–0.4 in 1–10 min | p | Abdominal, groin or head injury | [K] |

### Visual/behavioural checklist (pain)
- Pain face: brows down, eyes squeezed, nose wrinkled, upper lip raised, teeth bared or mouth open. Build it over a second; don't snap it on.
- Screams are rough, grating and breathy, and are broken by gasps. Chest-wounded characters can only manage short, weak cries.
- Clutching and pressing the wound is near-universal in conscious people.
- Belly pain from a stab: stillness, knees up, hands on the belly, shallow breathing. Burns or colic-like pain: rolling and thrashing.
- A stunned victim may stand frozen and staring for a second or two before doing anything.
- Audio: sobbing, whimpering, pleading, hyperventilation. As blood pressure falls, sounds get weaker and then stop.

---

## 10. Neurological deficits as reaction modifiers

This table is how "real deficits" change reactions. Where the deficits come from is in `[R1-04 §3–4]`. Values are `[K]`, with game ranges `[E]`.

| Deficit | Effect on reactions | Parameters |
|---|---|---|
| **Hemiplegia (one side)** | No protective arm on the paralysed side; no hand-to-wound with that hand. Stepping on the paralysed leg fails, so falls go **toward** it. Face droops on that side. Eyes and head turn toward the lesion (away from the paralysed side) | `P(fall)` ×3 on perturbations toward the paralysed side; paralysed-side tone 0.1–0.3 at first (flaccid) |
| **Neglect (right-hemisphere lesion)** | Ignores wounds, threats and the limb on the **left**; does not look left; may deny the injury | `hold_wound_p` = 0 for left-sided wounds; left threats trigger no defence |
| **Aphasia (left-hemisphere lesion)** | Speech replaced by moans, jargon or silence. **Automatic phrases and swearing are often preserved** | Vocal set limited to moans, cries and 1–3 stock phrases |
| **Cognitive impairment / confusion (frontal, diffuse brain injury, concussion)** | Slow, inappropriate, perseverative reactions. Repeats the same question or action. Poor avoidance of the threat. Inappropriate calm, laughing or crying. Wanders aimlessly. Does not understand commands | Reaction time ×1.3 (mild) to ×3 (severe); P(inappropriate action) 0.1–0.4; P(perseverate) 0.2–0.5 per decision |
| **Cerebellar injury** | Ataxic stagger (§4.2); reaching for the wound overshoots (dysmetria); intention tremor **3–5 Hz**; nystagmus; vomiting | Base of support +50–100 %; reach error 3–10 cm |
| **Eye-movement nerve palsies ("eyes crossed")** | Sixth nerve: affected eye turned **in** (esotropia) 10–30°. Third nerve: eye turned **down and out**, eyelid drooping, pupil dilated. Brainstem or cerebellar lesion: vertical skew deviation 2–10°. Double vision leads to squinting, closing one eye, a head tilt, and misjudged reaches | `eye_offset` per eye; `reach_error` +2–5 cm |
| **Focal motor seizure ("arms twitch")** | Rhythmic clonic jerking of the hand, arm or face on the side **opposite** the lesion, at **~1–4 Hz**. May spread up the limb (Jacksonian march) over 10–60 s and may become generalised. Afterwards the limb is weak for hours (Todd's paresis, typically < 48 h) | Onset from seconds (impact seizure) to minutes; see `[R1-04 §4.2]` |
| **Myoclonus (hypoxic)** | Brief, shock-like jerks of limbs or trunk (10–100 ms), singly or in bursts; startle-sensitive | 0.2–2 jerks/s during hypoxic phases |
| **Posturing** (decorticate or decerebrate) | Replaces all protective behaviour; triggered by stimuli (being hit, moved or burned) | `[R1-04 §4.1]` |
| **Spinal cord level** | Below the level: no withdrawal, no pain behaviour, no protection (spinal shock phase 0–24 h). Above: normal | Spinal shock: phase 1 (0–1 d) areflexia; phase 2 (1–3 d) reflexes begin to return; phase 3 (4 d – 1 month) hyper-reflexia `[S46]` |
| **Reduced consciousness (GCS verbal / motor)** | Verbal: 4 confused speech; 3 inappropriate words; 2 moans; 1 silent. Motor: 5 localises (hand goes to the stimulus); 4 withdraws; 3–2 posturing; 1 flaccid | Map GCS directly to the vocal and motor response sets |

### Simulation parameters (neurological modifiers)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `rt_mult_cognitive` | 1.3 (mild) – 3.0 (severe) | × | All L3/L4 latencies | [K] [E] |
| `perseverate_p` | 0.2–0.5 | p per decision | Repeats the last behaviour | [E] |
| `inappropriate_action_p` | 0.1–0.4 | p | Laughs, wanders, ignores the threat | [E] |
| `esotropia_deg` (sixth nerve) | 10–30 | ° | Affected eye | [K] |
| `exotropia_hypotropia_deg` (third nerve) | 15–30 out, 5–15 down, ptosis 50–100 %, pupil 6–8 mm | ° / % / mm | | [K] |
| `skew_deg` | 2–10 | ° vertical | | [K] |
| `nystagmus` | 1–5 Hz, 2–10° | Hz / ° | Cerebellar, vestibular, concussion | [K] |
| `focal_clonic_freq` | 1–4 | Hz | Contralateral hand, arm or face | [K] |
| `jacksonian_march` | 10–60 | s | Hand, then forearm, arm, face | [K] |
| `todd_paresis` | 0.5–48 (typ. < 24) | h | Compress with the time scale | [K] |
| `intention_tremor` | 3–5 | Hz | During reaching | [K] |
| `myoclonic_jerk` | 10–100 ms each; 0.2–2 /s | ms / Hz | | [K] |

### Visual/behavioural checklist (neurological modifiers)
- A brain-injured character reacts late and wrongly. They may look at the attacker blankly, laugh, repeat "what happened?", or keep trying the same failed action.
- One eye drifts inward or down and out. The character squints, tilts the head, and misses when reaching.
- A hand starts twitching rhythmically, the twitching climbs the arm into the face, then the arm hangs weak afterwards.
- A character with a paralysed side falls onto that side without an arm to catch it, and grabs its wound only with the good hand.
- A left-brain-injured character can't form words but can still swear.

---

## 11. Reaction-selection table

### 11.1 Inputs

- **Hit**:
  - `region` and structure flags (bone, joint, major artery, nerve, cord level, organ);
  - `energy_class`: low (.22, untrained punch), medium (handgun, trained punch, hammer), high (rifle, shotgun);
  - hit direction.
- **State**:
  - `consciousness` (GCS-like, 3–15);
  - `arousal` (0–1);
  - `mindset` (§2.3);
  - `locomotion` (standing, walking, running), including which leg is loaded;
  - `armed` flag;
  - `aware_of_hit`.
- **Neurological**: hemiplegia side, neglect, aphasia, ataxia, `rt_mult_cognitive`, seizure state, cord level (§10).
- **Physiology**: MAP, cerebral oxygen-reserve timer, `leg_capacity` per leg (§4.2).

### 11.2 Table

In this table, a "fall" letter refers to the archetypes in §5.1.

| # | Condition (conscious at t = 0 unless stated) | Reaction chain | Timings | Probabilities | Tag |
|---|---|---|---|---|---|
| 1 | Any hit or nearby shot, conscious | Startle and flinch (§1.1) plus limb flick from momentum (§1.3) | 30–450 ms | 1.0 × habituation × (1 − 0.5·arousal) | [S1]–[S4] [E] |
| 2 | Brainstem / C1–C2 | Cut-strings crumple (fall A); weapon drops; no protection | Tone lost ≤ 0.1 s; ground at 0.6–1.2 s | 1.0; decerebrate topple (fall B) 0.3–0.6 for a midbrain hit | [R1-04 §2] |
| 3 | Cerebral hemisphere (handgun) | Concussive collapse, then may wake with deficits; else staggers with deficits (§10) | 0–120 s unconscious | P(awake at 10 s) 0.1–0.3 | [R1-04 §3] |
| 4 | Cervical cord C3–C7 | Cut strings, **awake**; arm function by level | ≤ 0.1 s | 1.0 | [K] |
| 5 | Thoracic / lumbar cord | Paraplegic drop (fall E); arms catch; tries to rise; crawls | Legs ≤ 0.1 s; ground 0.6–1.0 s | 1.0 | [S46] [K] |
| 6 | Heart / aorta destroyed | Continues per mindset, or stops psychologically; then hypoperfusion sag (fall G) and limp | Sag at 8–15 s | Psychological stop per §2.3; 1.0 unconscious by 15 s | [S5] [S9] |
| 7 | Partial cardiac wound | As row 6 but slower | 10 s – 10 min | 4/7 minutes; 2/7 ~10 s; 1/7 immediate | [S13] |
| 8 | Major limb or neck artery | Clamps or holds the wound (neck 0.3–0.8 s); continues; controlled descent (fall C) as MAP falls | Descent at 1–5 min (`[R1-03]`) | Hold P 0.7–0.9 | [E] |
| 9 | Lung / chest wall | Flinch, hand to chest, breathlessness; tripod stance, then sit or kneel | Sit or kneel within 10–60 s | 0.6 | [K] [E] |
| 10 | Abdomen | Guarding, doubling over, hand to wound; kneel or sit; curl | Hand 0.4–0.8 s; kneel 2–5 s | Per mindset (§2.3) | [K] |
| 11 | Groin | Knees together, hands to groin, drops to the knees; later vomits | 0.5–2 s | 0.6–0.9 | [K] |
| 12 | Pelvis / hip / femur fracture, leg loaded | One-sided buckle (fall D) toward the injured side; arms out; screams; grips the thigh | Give-way 0.1–0.3 s; ground 0.6–0.9 s | 0.85–0.95 | [S48] [E] |
| 13 | As row 12, leg unloaded | Falls when that leg next takes weight | 0.2–0.5 s | 0.9 | [E] |
| 14 | Thigh or calf, muscle only | Limp, "dead leg", continues | — | P(fall) 0.1–0.3 | [E] |
| 15 | Knee / tibia / ankle | Buckles (knee or tibia), hops (ankle) | 0.1–0.5 s | 0.3–0.9 (§3) | [E] |
| 16 | Arm or shoulder: fracture or nerve | Arm drops, weapon drops, other hand supports the arm | 0.2–1 s | Drop 0.5–0.9 | [S47] [E] |
| 17 | Hand | Hand flicks, drops the object, hand held to the chest, shaken | 0.1–0.5 s | Drop 0.6–0.9 | [E] |
| 18 | Face / eye / jaw | Hands to the face, turns away, bends forward; spits or drains blood | 0.2–0.5 s | P(fall) 0.2–0.5 | [E] |
| 19 | Punch to the head | Compute α (§6.1). Loss of consciousness: fall A/B (fencing 0.66). Otherwise rocked (§6.4) or flinch | Tone ≤ 0.1 s | P_LOC(α) | [S30] [S31] [S33] [E] |
| 20 | Punch to the liver / epigastrium | Delayed fold to the knees and curl / winded | 1–3 s / 0 s | Scale by force: P 0.2 at 1,500 N, 0.7 at 3,500 N | [S55] (L) [E] |
| 21 | Knife cut to a limb or the face | Withdrawal, other hand grabs, wound check; defensive arms if the blade is visible | 0.1–2 s | Unaware P per §2.4 | [S37] [E] |
| 22 | Knife stab to the torso | Minimal flinch; delayed realisation | 0–60 s | P(unaware) 0.3–0.6 | [S16] [E] |
| 23 | Hit while unconscious | Passive physics only. Possible **spinal withdrawal** of the struck limb in light coma (GCS motor 4); posturing at motor 2–3; nothing at motor 1 | Withdrawal 100–250 ms | Withdrawal 0.2–0.5 at GCS motor ≥ 4; posture burst 0.5 at motor 2–3 | [K] [R1-04 §4] |
| 24 | Near miss (no hit) | Startle; duck; turn away; flee or freeze | 0.03–0.6 s | Flee 0.4 / freeze 0.3 / duck-and-cover 0.3 (non-combatant) | [E] |
| 25 | Burn contact | Withdraw; shake, blow or press; scream; writhe if restrained | Withdrawal 0.2–0.6 s after contact | 1.0 if free and conscious | [S37] [S38] [E] |

### 11.3 Arbitration (per decision tick, 20 Hz) `[E]`

1. **Consciousness gate.** If unconscious, keep only L0, spinal reflexes (row 23), posturing and seizure states.
2. **Mechanical failures.** Leg, cord or arm failures immediately override posture and locomotion goals (rows 5, 12–17).
3. **Reflex overlays.** Startle and withdrawal are additive and short (≤ 0.8 s). They never block a fall.
4. **Balance.** If XcoM is outside the base of support, choose a step, a grab or a fall (§4). Protective arm targets are pre-armed whenever the fall probability is > 0.5.
5. **Behavioural choice.** Awareness, then wound check, then the psychological stop roll (§2.3), then an action (fight, flee, surrender, freeze, descend), all delayed by `rt_mult_cognitive`.
6. **Physiological clock.** When the cerebral oxygen-reserve timer or MAP crosses its threshold, force archetype G, then limp.

```text
# Pseudocode written for this document (not taken from any source)
on_hit(hit):
    apply_segment_impulse(hit.p * f_ret / (seg_mass * k_attach))       # L0
    if conscious:
        schedule_startle(amp = habituation * (1 - 0.5*arousal))       # L1, 30-450 ms
        schedule_local_withdrawal(hit.segment, delay = nwr_latency)   # L1
    mech = evaluate_structural_failure(hit)                           # §3
    if mech.leg_giveway: schedule_buckle(side, delay = 0.1..0.3 s)
    if mech.cns_immediate: set_tone(0, over = 0.05..0.1 s); archetype = A or B
    aware = conscious and not roll(unaware_p)                         # §2.4
    if aware: queue(wound_check, delay = 0.3..1.0 s * rt_mult)
    queue(psych_stop_roll, delay = 0.3..3 s * rt_mult)                # §2.3
```

### Simulation parameters (selection)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `decision_tick` | 20 | Hz | Reflexes on the physics tick | [E] |
| `reflex_overlay_max` | 0.8 | s | Additive, never blocks falls | [E] |
| `prearm_protect_threshold` | P(fall) > 0.5 | — | Arms begin to move toward the likely ground contact | [E] |
| `near_miss_choice` | flee 0.4 / freeze 0.3 / duck 0.3 | p | Non-combatant | [E] |
| `unconscious_withdraw_p` | 0.2–0.5 at GCS motor ≥ 4 | p | | [K] [E] |

### Visual/behavioural checklist (selection)
- The same bullet looks different on different people. A bystander drops or runs. An enraged attacker barely flinches. A drunk may not notice.
- Structural failures (a broken leg, a spine hit) happen **before** any emotional reaction. The body goes down, then the face shows fear and pain.
- A knocked-out body gets hit again and does nothing.

---

## 12. Second-by-second scenarios (validation targets)

**A. 9 mm to the upper abdomen (liver), surprised bystander, standing.**
- **0 ms**: entry. No visible push (0.04 m/s); a ripple of clothing.
- **30–60 ms**: blink (from the shot's report).
- **60–250 ms**: head ducks, shoulders rise, arms pull in, knees dip.
- **0.4–0.8 s**: a hand arrives on the belly. First pain (sharp). Gasp or "ah!".
- **0.5–1.5 s**: looks down, pain face builds.
- **1–2 s**: looks at a bloody hand.
- **1–3 s**: psychological stop (P 0.8). Doubles over, one or two steps, kneels or sits (2–5 s), curls on the side with knees up, moaning or crying out.
- **10–60 s**: burning second pain; calls for help; pale.
- **2–10 min**: shock progresses with the liver bleed (`[R1-03]`): restless, then confused, then drowsy.
- **Variant (P 0.1)**: unaware for 5–30 s and keeps walking.

**B. 9 mm through the heart, committed armed attacker running at the shooter.**
- **0–0.3 s**: small flinch (arousal-damped). Keeps running. May grunt.
- **0–5 s**: fully functional; can fire several shots.
- **5–10 s**: stride shortens and weaves; the gun sags.
- **8–12 s**: sag (fall G) into a forward crumple, carried 1–3 m by momentum. Partial or no arm protection.
- **12–25 s**: eyes open and up, irregular jerks, agonal gasps begin (`[R1-04]`).

**C. 7.62×39 mm through the right femur of a man walking (right leg in stance).**
- **0 ms**: femur shatters.
- **30–250 ms**: startle.
- **100–300 ms**: the right leg folds at mid-thigh.
- **100–200 ms**: arms thrown out.
- **0.6–0.9 s**: lands on the right hip and hands.
- **0.5–1 s**: screaming starts.
- **1–5 s**: rolls onto the back, both hands clamp the thigh, the foot lies turned out 60–90°. Every attempt to move draws a scream.
- If the femoral artery is cut, the minutes-long clock of `[R1-03]` applies.

**D. Bare-knuckle hook to the jaw, trained puncher, α ≈ 7,000 rad/s² (P_LOC ≈ 0.7).**
- **0–15 ms**: impulse.
- **50–100 ms**: head rotated 40–60°.
- **≤ 100 ms**: tone lost. Knees buckle, or the arms lock into a fencing posture (0.66).
- **0.5–1.2 s**: lands without protection. Head strikes the floor at 3–6 m/s.
- **1–20 s**: motionless, eyes open and glassy, snoring. P 0.014 of a concussive convulsion (`[R1-04]`).
- **5–60 s**: eyes focus, tries to rise, falls back, confused.
- **Without loss of consciousness (0.3)**: rocked. Two to four lurching steps, grabs the attacker, blank look, slow reactions for 5–60 s.

**E. Knife slash to the left forearm, then a stab to the left chest (heart).**
- **0.1 s**: arm yanked back.
- **0.2–0.5 s**: right hand grabs the left forearm.
- **0.5–2 s**: looks at it, pain face.
- **~2–3 s**: the stab, felt as a punch. P 0.4 that it goes unnoticed.
- **3–13 s** (short-term class): keeps struggling, then greys out and sags.
- **Or 2–10 min** (long-term class): walks, talks and seeks help, then collapses.

**F. Torch flame onto the right hand, arm restrained.**
- **< 0.3 s**: skin reaches the pain threshold.
- **0.2–0.6 s**: violent pull against the restraint, scream.
- **1.2–1.5 s**: second pain wave, maximal struggling and arching.
- **2–30 s**: breath-paced screams, hyperventilation.
- **10–60 s**: possible vasovagal faint (P 0.05–0.1).
- **After release**: shakes the hand, presses it to the body, whimpers. Blistering follows the timeline in `[R1-02 §6]`.

**G. 9 mm to the spine at T8 from behind, man walking away.**
- **≤ 100 ms**: legs flaccid.
- **30–250 ms**: upper-body startle.
- **0.3–0.5 s**: knees and hips fold.
- **0.6–0.9 s**: pitches forward onto the hands.
- **1–5 s**: tries to push up, legs do not respond, "I can't move my legs". Burning pain band at chest level.
- **10–60 s**: drags forward with the arms. The legs show no withdrawal when struck.

**H. .22 LR into the left frontal/motor region.**
- **0–0.3 s**: startle, then brief collapse (P 0.7) or stagger.
- **0.5–2 s**: the right arm hangs and the right leg buckles, so the body falls to the right. Eyes and head deviate **left**. The left hand goes to the head.
- **2–60 s**: awake but speech is jargon or absent (aphasia); swearing may be preserved. Confused, slow, repeats actions.
- **1–30 min**: P 0.1–0.2 of a focal seizure: right-sided face and hand twitching at 1–4 Hz, sometimes spreading.

**I. 12-gauge 00 buck to the chest at 5 m, bystander.**
- **0 ms**: nine pellets into the heart and lungs. 0.17 m/s: no throw. At most a half-step back if already leaning back.
- **30–250 ms**: startle.
- **0.3–2 s**: hand to chest, psychological drop likely.
- **5–15 s**: loss of consciousness if the heart is hit; otherwise a slower course.

### Visual/behavioural checklist (scenarios)
- Replay each scenario at 1× and check that the order of events matches:
  1. impulse;
  2. blink and flinch;
  3. mechanical failure;
  4. protective limbs;
  5. hand to wound;
  6. look;
  7. emotional reaction;
  8. physiological collapse.
- Check that **nothing is thrown by a bullet**, that **unconscious bodies never protect themselves**, and that **heart-shot characters remain capable for several seconds**.

---

## 13. Implementation notes for Godot 4.5 / Jolt (brief)

Engine API details are `[K]`. Verify them against the Godot 4.5 documentation; the planned search was refused.

- **Per-joint tone.** Drive PhysicalBone3D bodies toward animated targets with PD control (torque = kp·Δθ − kd·ω) applied in the physics step. Scale kp and kd by a per-joint `tone` value from 0 to 1.
  - Loss of consciousness: tone goes to 0 over **50–100 ms**, not in one frame.
  - Tonic posture (fencing, decerebrate): tone 1.0 toward posture targets with high kp.
- **Blend.** Blend physical and animated pose per bone chain. Recent Godot versions provide a physical-bone simulator node with a blend (influence) control. This allows partial ragdoll: for example, a limp arm while the legs still follow a stagger animation.
- **Reflex overlays** are additive pose offsets on top of the current target (the startle table in §1.1). Schedule them on the physics tick.
- **Balance.** Compute XcoM each physics step from the COM and its velocity. When it leaves the support polygon, trigger a step planner (target = XcoM plus a margin, clamped by `leg_capacity`) or a fall archetype.
- **Protective behaviours as IK targets**: hand to wound (nearest working hand); hands to the predicted ground contact point during a fall; forearms in front of the face when a threat is seen; head turned away.
- **Behaviour library for reference.** NaturalMotion Euphoria, used in GTA IV and V, exposes behaviours with names that match this document's reactions: `Shot`, `ShotFallToKnees`, `ShotSnap`, `StaggerFall`, `CatchFall`, `ArmsWindmill`, `BodyRelax`, `BodyWrithe`, `ConfigureBalance`, `StayUpright` `[S58]`.
- **Academic references for the control approach**:
  - Zordan & Hodgins 2002: trajectory tracking of motion capture plus a balance controller, for characters that hit and react `[S59]`.
  - Zordan et al. 2005: simulate on impact, then blend back into a matched motion-capture reaction clip `[S59]`. The method description is `[K]`.
  - Ha, Ye & Liu 2012: falling and landing controller with an airborne phase and a landing (rolling) phase that limits joint stress, without motion capture `[S59]`.
  - DReCon 2019: data-driven responsive control. Only the title was found `[S59]`.
- **Performance** `[E]`: the reaction logic is a few hundred operations per character per 20 Hz tick. The cost is in the ragdoll solve (~15–20 bodies per character). Keep PD gains in pre-allocated arrays and avoid per-tick allocation.

### Simulation parameters (implementation)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `tone_ramp_loc` | 50–100 | ms | Tone to 0 | [S33] [E] |
| `pd_kp_scale` | tone × base | — | Base tuned per joint | [E] |
| `xcom_check` | every physics tick | — | | [E] |
| `ik_hand_to_wound_blend` | 150–300 | ms | Motion time after onset | [E] |
| `ragdoll_bodies` | 15–20 | count | Per character | [E] |

### Visual/behavioural checklist (implementation)
- No reaction pops. Every transition blends in 50–300 ms, except tone loss (≤ 100 ms) and reflex onsets.
- Partial ragdoll is visible: a paralysed or broken limb swings passively while the rest of the body acts.

---

## 14. Common realism mistakes

| # | Mistake | Reality | Fix | Source |
|---|---|---|---|---|
| 1 | Bullets throw bodies back | Buckshot, the worst case, gives ≤ 0.17 m/s; a boxer's punch carries ~9× a 9 mm bullet's momentum | Tiny segment impulses only (§1.3) | [R1-01] [S57] [E] |
| 2 | Everyone falls when hit | Handgun: ~47 % stop on the first hit; 13–17 % never stop | Psychological stop model (§2.3) | [S8] |
| 3 | Heart shot = instant drop | 10–15 s of voluntary action; stabs 10 s to 10 min | Physiological clock (§2.5) | [S5] [S13] |
| 4 | Instant pain scream on every hit | Pain often delayed or absent under arousal; wound discovered later | Awareness and `pain_gain` (§1.2, §2.4) | [S6] [S15] [S16] |
| 5 | Unconscious bodies brace their fall | No protective action ("floppy") | Tone to 0; no IK (§5.4) | [S36] |
| 6 | Conscious falls look like ragdolls | Arms out in ~100–200 ms; hands land first in 74 % of falls | Protective IK (§5.3) | [S24] [S25] |
| 7 | Knockouts drift down slowly | Tone lost within ~100 ms; plank or crumple | §6.3 | [S33] |
| 8 | A shot leg is just a limp | A broken femur under load gives way in 0.1–0.3 s and the body falls to that side | §3 | [S48] [E] |
| 9 | Screams are clean tones | Screams are rough (30–150 Hz amplitude modulation), breath-limited, and weaker with chest wounds or low blood pressure | §9.2 | [S40] [S41] |
| 10 | Brain-injured characters behave normally until they die | Deficits: paralysed side, gaze deviation, aphasia, confusion, seizures | §10 | [R1-04] |
| 11 | Every stab is noticed | Often felt as a punch; noticed later | §2.4, §7 | [S16] |
| 12 | Faint = instant death pose | Syncope: eyes open and turned up, jerks in 90 %, ~12 s, then recovery | §5.6 | [S26] [S27] |

---

## 15. Load-bearing numbers (quick reference)

1. Startle EMG onsets: blink **30 ms**, sternocleidomastoid **62 ms**, masseter **67 ms**, biceps 85–100 ms, thigh 100–125 ms, tibialis anterior 130–140 ms. Stereotyped whole-body flinch within **200 ms** of a pistol shot [S1] [S2] [S3].
2. The first startle is the largest, and it habituates with repetition [S4].
3. Withdrawal reflex ~**100 ms**. Heat withdrawal **190–280 ms** (Aδ) and **1.2–1.5 s** (C) [S37].
4. Knock-back: 9 mm **0.038 m/s**, buckshot **0.17 m/s**; the backward step threshold is **0.13–0.22 m/s**. A punch carries ~26–32 kg·m/s (0.35–0.43 m/s) [R1-01] [S28] [S29] [E].
5. FBI: "sufficient oxygen in the brain to support full and complete voluntary action for **10–15 seconds**" after heart destruction. Psychological stops "can never be counted on" [S5].
6. "Those who do stop commonly do so because they decide to" [S6].
7. Handguns: **~2 hits** to stop; **47 %** stopped by the first hit (9 mm); **13–17 %** never stopped. Shotgun 86 % / 12 % [S8].
8. Cardiac stab suicides: **4/7 active 2–10 min, 2/7 ~10 s, 1/7 immediate** [S13].
9. Standing fall after a tone-abolishing hit: **⅔ s to ≥ 1 s**. Unavoidable falls **0.7–1.2 s** [S10] [S25].
10. Turn 180° in **0.26–0.54 s** (explains back wounds) [S12].
11. Single-step recovery limit **32.2°** (young) vs **23.5°** (older). Recovery-step toe-off **0.24 ± 0.03 s**. Postural EMG **73–110 ms** [S19] [S20] [S21].
12. Real falls: hands **74 %**, head **37 %**; hands did not prevent head impact. "Collapse" caused **11 %** [S24].
13. Protective arm burst **~100 ms**; early arm reaction in **91 %** of young adults' falls [S25].
14. Head impact velocities for standing falls: **2.0–7.4 m/s** [S51]. Rigid topple **1.0–1.6 s**, ~**6.5–7 m/s** head impact [E].
15. Syncope: **12.1 ± 4.4 s**, myoclonus **90 %**, eyes open and turned up [S26] [S27].
16. Knockouts: rotational acceleration **5.9 vs 3.5 krad/s²** with vs without loss of consciousness; threshold ~**4,500**; hook mean **9,306 rad/s²**; tone lost ≤ **100 ms** [S29] [S30] [S31] [S33].
17. MMA: **53.9 %** of knockouts from jaw strikes; **3.5 s** (0–20 s) of blows after the knockout before stoppage [S34].
18. Video signs: slow to get up (66 % sensitive); motor incoordination = staggering, stumbling, struggling to get up [S36].
19. Officers in shootings: reduced hearing **84 %**, tunnel vision **79 %**, autopilot **74 %**, slow motion **62 %** [S18].
20. Anzio: **32 %** of severely wounded soldiers vs **83 %** of civilians wanted narcotics [S15].
21. Screams: roughness **30–150 Hz**. Pain vocal F0, loudness and non-linear phenomena rise with intensity [S40] [S41].
22. Pain face: brow lowering, orbital tightening, levator contraction, eye closure (PSPI 0–16) [S39].
23. Radial nerve palsy in **26.5 %** of ballistic humeral shaft fractures. Thoracic cord **48–64 %** of spinal gunshot wounds [S46] [S47].

---

## 16. Suspicious content

- **No prompt-injection attempts were found.** No search result or snippet told the reader to run a command, download or install anything, change files, visit a URL, or reveal information.
- Several result lists included **patent PDF links** (image-ppubs.uspto.gov "downloadPdf"), **forum threads**, **commercial fitness and combat-sports blogs** and **YouTube videos**. None were opened. None is the sole source of a load-bearing number. Liver-shot and "winded" timings are marked (L) for this reason.
- A search for "Pinizzotto" also returned unrelated 2026 news about a Toronto police constable with that surname. It was ignored as irrelevant.
- `WebFetch` was not used. Nothing was downloaded or executed. No code was copied from the web. The pseudocode in §11.3 was written for this document.
- The shared web-search budget ran out at the end of the session. Three searches were refused (see §0.1).

---

## 17. References

All sources were read only through search-result summaries (see §0.1).

- **[S1]** ScienceDirect Topics, "Startle reflex" (EMG latencies by muscle; pontine reticular nucleus pathway). https://www.sciencedirect.com/topics/biochemistry-genetics-and-molecular-biology/startle-reflex
- **[S2]** Sinclair et al. The Laryngeal Auditory Startle Reflex (LASR). *Laryngoscope* 2026 (pooled onsets: orbicularis oculi 30 ± 1, SCM 62 ± 13, masseter 67 ± 2 ms). https://pmc.ncbi.nlm.nih.gov/articles/PMC13357233/ ; https://pubmed.ncbi.nlm.nih.gov/41910336/
- **[S3]** Landis C, Hunt WA. *The Startle Pattern*. 1939 (pistol-shot stimulus, high-speed film). https://books.google.com/books/about/The_Startle_Pattern.html?id=HRW0AAAAIAAJ ; ScienceDirect Topics (psychology), Startle reflex: https://www.sciencedirect.com/topics/psychology/startle-reflex ; pattern description: https://www.ccjm.org/content/ccjom/57/1_suppl_1/S-54.full.pdf
- **[S4]** First trial postural reactions to unexpected balance disturbances: a comparison with the acoustic startle reaction. *J Neurophysiol* 2010. https://journals.physiology.org/doi/full/10.1152/jn.01080.2009
- **[S5]** Patrick UW. *Handgun Wounding Factors and Effectiveness*. FBI Firearms Training Unit, 1989. https://archive.org/details/fbi-handgun-wounding-factors-and-effectiveness ; https://tirotactico.net/wp-content/uploads/2016/07/handgun-wounding-factors-and-effectivene-special-agent-urey-w-patrick.pdf
- **[S6]** FBI Training Division. 9 mm Luger justification ("white paper"), 2014. https://www.gunnuts.net/wp-content/uploads/2020/06/FBI-9mm-white-paper-2014.pdf
- **[S7]** 1987 FBI Wound Ballistics Workshop summary: American Rifleman, "Throwback Thursday: the FBI ammo tests". https://www.americanrifleman.org/articles/2015/4/16/throwback-thursday-the-fbi-ammo-tests/ ; Fackler ML, "What's wrong with the wound ballistics literature". https://www.rkba.org/research/fackler/wrong.html
- **[S8]** Ellifritz G. An alternate look at handgun stopping power (≈1,800 shootings; non-peer-reviewed). https://www.activeresponsetraining.net/an-alternate-look-at-handgun-stopping-power ; summaries: https://www.tierthreetactical.com/analyzing-1800-shootings-which-caliber-has-the-best-stopping-power/ ; https://www.buckeyefirearms.org/alternate-look-handgun-stopping-power
- **[S9]** Force Science Institute. Why shooting to wound doesn't make sense (2006). https://www.forcescience.com/2006/03/why-shooting-to-wound-doesnt-make-sense-scientifically-legally-or-tactically/
- **[S10]** Force Science Institute. "Excessive" shots and falling assailants (2010). https://www.forcescience.com/2010/03/excessive-shots-and-falling-assailants-a-fresh-look-at-ois-subtleties/
- **[S11]** Force Science Institute. Time to stop (2025). https://www.forcescience.com/2025/07/new-study-time-to-stop-why-even-the-most-disciplined-officers-cant-stop-faster-than-humanly-possible/
- **[S12]** Lewinski / Force Science turning studies: Police1, "Study reveals how suspects sometimes get shot in the back". https://www.police1.com/officer-shootings/articles/study-reveals-how-suspects-sometimes-get-shot-in-the-back-BLchKt2nDQHhrO0M/ ; Force Science validates legacy research findings, Part II (2023). https://www.forcescience.com/2023/02/force-science-validates-legacy-research-findings-part-ii/
- **[S13]** Karger B et al. Physical activity following fatal injury from sharp pointed weapons. *Int J Legal Med* 1999. https://pubmed.ncbi.nlm.nih.gov/10335884/
- **[S14]** Juvin B et al. Prolonged activity after an ultimately fatal gunshot wound to the heart. *Am J Forensic Med Pathol* 1999. https://pubmed.ncbi.nlm.nih.gov/10208328/ ; Karger B, Brinkmann B. Multiple gunshot suicides: potential for physical activity. https://link.springer.com/article/10.1007/s004140050065 ; Precise survival time and physical activity after fatal left ventricle injury (2016). https://pubmed.ncbi.nlm.nih.gov/26914799/ ; Levy V, Rao VJ. Survival time in gunshot and stab wound victims. 1988. https://pubmed.ncbi.nlm.nih.gov/3177349/
- **[S15]** Beecher HK. Pain in men wounded in battle (1946), as summarised by McGill OSS, "The legend of the wartime placebo". https://www.mcgill.ca/oss/article/critical-thinking-health-and-nutrition-history/legend-wartime-placebo ; https://www.researchgate.net/publication/305989143_Beecher_as_Clinical_Investigator_Pain_and_the_Placebo_Effect
- **[S16]** Survivor accounts (anecdotal, low quality): https://www.vice.com/en/article/survived-stabbed-stabbing-35-multiple-times/ ; https://americanshootingjournal.com/heres-what-it-feels-like-to-get-shot/ ; https://www.thedp.com/article/1990/10/90_grad_stabbed_in_back ; https://www.ranker.com/list/what-being-stabbed-is-like/kellen-perry
- **[S17]** Pinizzotto AJ, Davis EF, Miller CE. *Violent Encounters: A Study of Felonious Assaults on Our Nation's Law Enforcement Officers*. FBI, 2006 (40 incidents). https://www.ojp.gov/ncjrs/virtual-library/abstracts/violent-encounters-study-felonious-assaults-our-nations-law ; FBI Law Enforcement Bulletin, Jan 2007. https://www2.fbi.gov/publications/leb/2007/jan2007/jan2007leb.htm
- **[S18]** Artwohl A: perceptual distortions in 157 officers after shootings, cited in: A reasonable officer (PMC). https://pmc.ncbi.nlm.nih.gov/articles/PMC8803048/ ; Force Science 2005. https://www.forcescience.com/2005/08/new-findings-expand-understanding-of-tunnel-vision-auditory-blocking-lag-time/
- **[S19]** Horak FB, Nashner LM. Central programming of postural movements. 1986. https://www.researchgate.net/publication/19426797 ; Effects of the type and direction of support surface perturbation on postural responses. *JNER* 2014. https://pmc.ncbi.nlm.nih.gov/articles/PMC3986462/
- **[S20]** Human response to longitudinal perturbations of standing passengers on public transport. *Front Bioeng Biotechnol* 2021. https://pmc.ncbi.nlm.nih.gov/articles/PMC8343014/
- **[S21]** Wojcik LA, Thelen DG et al. Age and gender differences in single-step recovery from a forward fall. *J Gerontol A* 1999. https://academic.oup.com/biomedgerontology/article/54/1/M44/594110
- **[S22]** Kinematics and strategies of recovery steps during lateral losses of balance. *BMC Geriatrics* 2020. https://bmcgeriatr.biomedcentral.com/articles/10.1186/s12877-020-01650-4
- **[S23]** Eng JJ, Winter DA, Patla AE. Strategies for recovery from a trip in early and late swing. *Exp Brain Res* 1994. https://pubmed.ncbi.nlm.nih.gov/7705511/
- **[S24]** Robinovitch SN et al. Video capture of the circumstances of falls in elderly people residing in long-term care. *Lancet* 2013. https://pubmed.ncbi.nlm.nih.gov/23083889/
- **[S25]** The timing and amplitude of the muscular activity of the arms preceding impact in a forward fall. *J Biomech* 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC10257944/ ; Age-related changes in the capacity to select early-onset upper-limb reactions. https://pubmed.ncbi.nlm.nih.gov/31377381/
- **[S26]** Lempert T et al. Syncope: a videometric analysis of 56 episodes of transient cerebral hypoxia. *Ann Neurol* 1994. https://onlinelibrary.wiley.com/doi/abs/10.1002/ana.410360217
- **[S27]** Lempert T, von Brevern M. The eye movements of syncope. *Neurology* 1996. https://pubmed.ncbi.nlm.nih.gov/8780096/
- **[S28]** Walilko TJ, Viano DC, Bir CA. Biomechanics of the head for Olympic boxer punches to the face. *Br J Sports Med* 2005. https://pubmed.ncbi.nlm.nih.gov/16183766/
- **[S29]** Viano DC et al. Concussion in professional football: comparison with boxing head impacts, Part 10. *Neurosurgery* 2005. https://pubmed.ncbi.nlm.nih.gov/16331164/
- **[S30]** Rotational head acceleration and traumatic brain injury in combat sports: a systematic review. *Br Med Bull* 2022. https://academic.oup.com/bmb/article/141/1/33/6516223
- **[S31]** Head dynamic response and brain tissue deformation for boxing punches with and without loss of consciousness. *Clin Biomech* 2019. https://pubmed.ncbi.nlm.nih.gov/31082637/
- **[S32]** How can a punch knock you out? *Front Neurol* 2020. https://pmc.ncbi.nlm.nih.gov/articles/PMC7649325/
- **[S33]** Knockouts are accompanied by an immediate loss of muscle tone. *Medical Research Archives* 2023. https://esmed.org/MRA/mra/article/view/4007
- **[S34]** Hutchison MG et al. Head trauma in mixed martial arts. *Am J Sports Med* 2014. https://journals.sagepub.com/doi/abs/10.1177/0363546514526151 ; Comprehensive analysis of "knockouts" in MMA. https://www.researchgate.net/publication/270199104
- **[S35]** Hosseini AH, Lifshitz J. Brain injury forces of moderate magnitude elicit the fencing response. *Med Sci Sports Exerc* 2009. https://pubmed.ncbi.nlm.nih.gov/19657303/
- **[S36]** Davis GA et al. International consensus definitions of video signs of concussion in professional sports. *Br J Sports Med* 2019. https://pubmed.ncbi.nlm.nih.gov/30954947/ ; Sensitivity and specificity of on-field visible signs of concussion in the NFL. 2020. https://pubmed.ncbi.nlm.nih.gov/32294198/
- **[S37]** Nociceptive withdrawal reflex (RIII ~100 ms, Aδ): https://pmc.ncbi.nlm.nih.gov/articles/PMC6509112/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC7356211/ ; Noxious radiant heat evokes bi-component nociceptive withdrawal reflexes in spinal cord injured humans. 2023. https://pmc.ncbi.nlm.nih.gov/articles/PMC10185789/
- **[S38]** ISO 13732-1:2006, Hot surfaces (0.5 s minimum contact period). https://www.iso.org/standard/43558.html ; In Compliance Magazine, Contact burn injuries (1–5 s contact; 43–44.6 °C thresholds). https://incompliancemag.com/contact-burn-injuries-the-influence-of-object-thermal-mass/
- **[S39]** Prkachin KM; Prkachin & Solomon PSPI, as summarised in: Automatically detecting pain using facial actions. https://pmc.ncbi.nlm.nih.gov/articles/PMC3296481/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6942457/
- **[S40]** Arnal LH et al. Human screams occupy a privileged niche in the communication soundscape. *Curr Biol* 2015. https://www.cell.com/fulltext/S0960-9822(15)00737-X
- **[S41]** Vocal communication of simulated pain. *Bioacoustics* 2018. https://www.tandfonline.com/doi/abs/10.1080/09524622.2018.1463295 ; Vocal communication and perception of pain in childbirth vocalizations. 2025. https://pubmed.ncbi.nlm.nih.gov/40176506/ ; Individual differences in human voice pitch are preserved from speech to screams, roars and pain cries. *R Soc Open Sci* 2020. https://royalsocietypublishing.org/rsos/article/7/2/191642
- **[S42]** Merck Manual Professional, Acute abdominal pain. https://www.merckmanuals.com/professional/gastrointestinal-disorders/acute-abdomen-and-surgical-gastroenterology/acute-abdominal-pain ; GPonline, Renal colic clinical review. https://www.gponline.com/renal-colic-clinical-review/genito-urinary-system/genito-urinary-system/article/1188835
- **[S43]** Mancini F et al. Touch inhibits subcortical and cortical nociceptive responses. *Pain* 2015. https://journals.lww.com/pain/fulltext/10.1097/j.pain.0000000000000253
- **[S44]** Roelofs K, Hagenaars MA, Stins J. Facing freeze. *Psychol Sci* 2010. https://journals.sagepub.com/doi/abs/10.1177/0956797610384746 ; Tonic immobility and peritraumatic dissociation. https://www.psychiatrist.com/jcp/tonic-immobility-and-peritraumatic-dissociation-in-ptsd/
- **[S45]** de Leva P. Adjustments to Zatsiorsky–Seluyanov's segment inertia parameters. *J Biomech* 1996. https://ebm.ufabc.edu.br/wp-content/uploads/2013/12/Leva-1996.pdf
- **[S46]** Gunshot injuries in the spine. *Spinal Cord* 2014. https://www.nature.com/articles/sc201456 ; StatPearls, Spinal shock (Ditunno phases). https://www.ncbi.nlm.nih.gov/books/NBK448163/
- **[S47]** Ballistic humeral shaft fractures and radial nerve palsy (113 fractures, 30 with complete palsy): search-summary figure. The exact paper is not confirmed; candidates are https://www.sciencedirect.com/science/article/pii/S1058274621006054 and https://pmc.ncbi.nlm.nih.gov/articles/PMC13414398/ . Non-ballistic incidence 7–17 %: https://pmc.ncbi.nlm.nih.gov/articles/PMC7736027/
- **[S48]** Gunshot wound to the hip joint (inability to bear weight). https://www.healio.com/news/orthopedics/20250917/36yearold-man-with-gunshot-wound-to-the-hip-joint ; Management of civilian transpelvic gunshot fractures. *Injury* 2023. https://www.injuryjournal.com/article/S0020-1383(23)00790-8/fulltext ; Biomechanics of femur fractures secondary to gunshot wounds. *J Trauma* 1984. https://journals.lww.com/jtrauma/abstract/1984/11000/biomechanics_of_femur_fractures_secondary_to.8.aspx ; Femur fractures caused by gunshots. https://pubmed.ncbi.nlm.nih.gov/8315670/
- **[S49]** Merck Manual Professional, Tension pneumothorax. https://www.merckmanuals.com/professional/injuries-poisoning/thoracic-trauma/tension-pneumothorax
- **[S50]** Courtney M, Courtney A. A method for testing handgun bullets in deer. arXiv 2007. https://arxiv.org/abs/physics/0702107 ; Stokke S et al. Defining animal welfare standards in hunting. *Sci Rep* 2018. https://www.nature.com/articles/s41598-018-32102-0 ; secondary summary of deer flight distances: https://huntiq.org/blog/how-far-will-a-deer-run/
- **[S51]** Measurement of head impact due to standing fall in adults using anthropomorphic test dummies. *Ann Biomed Eng* 2015. https://link.springer.com/article/10.1007/s10439-015-1255-1
- **[S52]** Differentiating fatal one-punch assaults from standing height falls based on skeletal trauma. *Aust J Forensic Sci* 2023. https://www.tandfonline.com/doi/abs/10.1080/00450618.2023.2292126 ; VIFM, Australian deaths involving coward's punches (2019). https://www.vifm.org/wp-content/uploads/Cowards-Punch-Research-Update-2019.pdf
- **[S53]** UT Southwestern, collapse during exercise (crumple vs crash). https://utswmed.org/medblog/syncope-cardiac-arrest-exercise/ ; Functional drop attacks (knees vs face injuries). https://neurosymptoms.org/en/symptoms/fnd-symptoms/functional-drop-attacks/
- **[S54]** American Academy of Ophthalmology, why eyes roll back during a knockout. https://www.aao.org/eye-health/ask-ophthalmologist-q/boxers-eyes-rolling-back-in-head-after-knockout ; Bell's phenomenon. https://en.wikipedia.org/wiki/Bell%27s_phenomenon
- **[S55]** (Low quality) Liver shot. https://en.wikipedia.org/wiki/Liver_shot ; Getting the wind knocked out of you. https://en.wikipedia.org/wiki/Getting_the_wind_knocked_out_of_you
- **[S56]** Flash knockdowns. https://combatsportslaw.com/2020/09/18/do-flash-knockouts-happen-without-brain-trauma/ ; Knockout. https://en.wikipedia.org/wiki/Knockout
- **[S57]** Physics of firearms (recoil, momentum). https://en.wikipedia.org/wiki/Physics_of_firearms
- **[S58]** NaturalMotion Euphoria behaviour messages as exposed by ScriptHookVDotNet: https://nitanmarcel.github.io/shvdn-docs.github.io/class_g_t_a_1_1_natural_motion_1_1_euphoria.html ; Euphoria (software). https://en.wikipedia.org/wiki/Euphoria_(software)
- **[S59]** Zordan VB, Hodgins JK. Motion capture-driven simulations that hit and react. SCA 2002. https://www.semanticscholar.org/paper/Motion-capture-driven-simulations-that-hit-and-Zordan-Hodgins/8639de4f0a209a740ef1c5949bf4d854275cd743 ; Zordan VB et al. Dynamic response for motion capture animation. *ACM TOG* 2005. https://dl.acm.org/doi/abs/10.1145/1073204.1073249 ; Ha S, Ye Y, Liu CK. Falling and landing motion control for character animation. *ACM TOG* (SIGGRAPH Asia) 2012. https://dl.acm.org/doi/10.1145/2366145.2366174 ; Bergamin K et al. DReCon: data-driven responsive control of physics-based characters. 2019. https://www.theorangeduck.com/media/uploads/other_stuff/DReCon.pdf
- **[S60]** US Army ORCA casualty model (assessments at 0 s, 30 s, 5 min, 1 h, 24 h, 3 d). ARL-TR-7274. https://apps.dtic.mil/sti/pdfs/ADA620168.pdf ; Kokinakis W, Sperrazza J. Criteria for incapacitating soldiers with fragments and flechettes. 1965. https://apps.dtic.mil/sti/pdfs/AD0359774.pdf
- **[S61]** Firearm homicides by police in the United States: who is shot and how many times? *Am J Prev Med* 2025. https://pubmed.ncbi.nlm.nih.gov/40266156/ ; Dallas PD hit rate. https://daiglelawgroup.com/new-study-on-shooting-accuracy-how-does-your-agency-stack-up/ ; NYPD / RAND hit rates via PolitiFact. https://politifact.com/factchecks/2018/may/25/shannon-watts/do-more-7-10-police-bullets-miss-their-mark-gun-co/
- **[S62]** Police1, public misconceptions about officer-involved shootings (Miami 1986 case). https://www.police1.com/evergreen/articles/3-myths-about-officer-involved-shootings-Inn9w3PqOMbyGEYo/
- **[S63]** Engel GL. Psychologic stress, vasodepressor (vasovagal) syncope, and sudden death. *Ann Intern Med* 1978. https://doi.org/10.7326/0003-4819-89-3-403 ; blood-injury phobia heart-rate response. https://en.wikipedia.org/wiki/Fear_of_needles
- **[S64]** Comparison between auditory and visual simple reaction times. https://www.scirp.org/html/4-2400003_2689.htm
- **[S65]** King SM et al. Defensive head movements to looming visual stimuli in human adults. *Perception* 1992. https://doi.org/10.1068/p210245

Round-one sources (Karger momentum paper, Rossen neck-cuff experiments, fencing-response details, Plum & Posner) are listed in the round-one files and cited here through `[R1-0x]`.
