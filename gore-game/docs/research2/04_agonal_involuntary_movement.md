# 04 (round 2) — Agonal and involuntary movement: dying, unconscious and newly dead bodies

Project: gore simulator (Godot 4.5, Forward+, GDScript + Godot shaders, built-in Jolt, Skeleton3D + PhysicalBone3D ragdolls). Research round 2.
Purpose: input for a **"still alive / dying" behaviour layer**. It covers everything a body does *without* voluntary control: in the last conscious minutes, while unconscious, while dying, and in the first minutes after death.
Audience: physiology, animation/ragdoll, eye/shader, VFX (fluids) and audio engineers. Clinical, factual tone. The subject is a fictional, procedurally generated adult.

**Round-one and round-two material this document builds on (not repeated here):**

| File | Already covers | Cited as |
|---|---|---|
| `docs/research/04_neuro_death_eyes.md` | Brainstem "cut strings" collapse (§2.3); posturing and GTC basics (§4); breathing patterns by level (§5.5); 10–15 s heart rule and syncope basics (§8.1–8.2); haemoptysis (§9.3); agonal-phase basics (§10); eyes when dying and dead (§11); first 48 h post-mortem (§12); physiology state machine (§13) | `[R1-04 §x]` |
| `docs/research/03_bleeding_vessels.md` | Shock classes, exsanguination sequence, bleed rates | `[R1-03 §x]` |
| `docs/research/02_sharp_blunt_burn.md` | Cut-throat autopsy series, neck-vein air entry | `[R1-02 §x]` |
| `docs/research2/01_brain_injury_deficits.md` | Eye signs master table (§14), seizure incidence, focal seizures, involuntary-movement catalogue (§17), posturing joint targets (§18) | `[R2-01 §x]` |
| `docs/research2/02_reactions_to_being_shot_and_hit.md` | Reflex layer, falls and fall archetypes A–G (§5), syncope as a collapse proxy (§5.6), pain behaviour and vocalisation (§9) | `[R2-02 §x]` |

**What this document adds:**
- the "generator rule": which tissue must still be alive for each sign to appear (§1);
- breathing, airway sounds and airway fluids in the unconscious and dying: gasping in detail, pre-terminal patterns, death rattle, blood, froth, vomit (§2);
- convulsive syncope and the second-by-second anoxic sequence (§3);
- a second-by-second seizure schedule (§4);
- twitching, myoclonus, spinal ("Lazarus") reflexes and movement after death (§5);
- tremor, shivering, teeth chattering (§6);
- face, eyes, jaw, tongue and hands per state (§7);
- skin and autonomic signs in the last minutes (§8);
- the generic last-minutes sequence (§9);
- five injury-to-death timelines (§10);
- an implementation plan for the layer in Godot 4.5 / Jolt (§11).

---

## 0. Read this first

### 0.1 Method and limits (important)

- **No web page or search result could be read in this session.**
  - Every `WebSearch` call was refused: the session's shared search budget (200 of 200 calls) had already been used by earlier research tasks.
  - `WebFetch` was not used. The brief states that the network policy blocks it, and round one confirmed `EGRESS_BLOCKED`.
- **Consequences:**
  - `[S#]` values come from sources that **sibling documents located by web search in earlier sessions**. The URLs are copied from those documents (§16.1). Those sessions read them only through search summaries, and they were not re-read here.
  - Most values are `[K]`: the author's knowledge of the clinical and forensic literature. Where a specific paper is recalled, it is named with a key `[K; M#]`. The list is in §16.2. **None of the `M#` items was opened in this session.**
  - `[E]` values are engineering estimates. The reasoning is shown.
- **Before any `[K]` or `[E]` number becomes a hard-coded constant, QA should check it.** The priority list is in §15.
- **An independent fact-check was made after writing (§18).** Marks in the text: **✓ verified** (matches the checker's knowledge at (H)/(M), or arithmetic re-derived); **⚠ not re-verified** (plausible, no independent confirmation possible); **corrected: was X** (value, attribution or wording changed). The fact-check also had no web access (search budget exhausted; `WebFetch` egress-blocked).
- Where sources or memory disagree, the range is given with a **game default** and the reason for choosing it.

### 0.2 Tags

| Tag | Meaning |
|---|---|
| `[S#]` | Sourced. URL in §16.1. Located by web search in a sibling session; read then through search summaries only |
| `[K]` | Author's own medical/forensic knowledge (standard texts). Not verified in this session |
| `[K; M#]` | Author's knowledge of a specific recalled paper or book, listed in §16.2. Not opened in this session |
| `[E]` | Engineering estimate or game mapping. Reasoning given |
| `[R1-0x §y]` / `[R2-0x §y]` | Sibling document and section |
| (H) / (M) / (L) | Confidence that the real value lies in the stated range: high, medium, low |

### 0.3 Conventions

- **Time origins** (all in real seconds unless stated):

  | Symbol | Meaning |
  |---|---|
  | `t_inj` | Moment of the injury |
  | `t_LOC` | Loss of consciousness |
  | `t_apn` | Onset of apnoea (no effective breathing) |
  | `t_arr` | Circulatory arrest: the last effective heartbeat (no cardiac output; pulsatile bleeding stops) |
  | `t_dead` | Game "dead" flag = `t_arr` + 300 s (autoresuscitation window, `[R1-04 §10.1]`) |

- **Game time scale**: as `[R1-04 §0.3]`. 1× for the first 60 s after any critical event **and for the 60 s either side of `t_arr`**. 4× for minutes. 10–30× for hours.
- **Reference body**: male, 75 kg, 1.75 m, blood volume 5,250 mL, segment masses from de Leva (1996) as listed in `[R2-02 §0.3]`.
- **Probabilities** are per character per episode unless stated. Roll them once when the character enters the relevant state, using a per-character seed.
- **Frames**: 60 fps = 16.7 ms per frame. Physics tick ≥ 60 Hz.

### 0.4 Where the layer sits

```
Physiology state (R1-04 §13)  ──►  DYING BEHAVIOUR LAYER (this document)  ──►  ragdoll drives, additive
 (consciousness, brain-level           generators:                               animation, eye/lid/jaw
  function, perfusion, SpO2,             BreathGen, MotorEventGen,                bones, skin/eye shader
  core temperature, airway fluid)        EyeLidJawGen, FluidGen, SkinGen,         uniforms, particles,
                                         AudioGen                                  one-shot audio
```

- The layer never decides whether the character lives or dies. It reads the physiology state and decides **what the body visibly and audibly does**.
- Every generator is gated by the tissue it needs (§1). That single rule removes most realism errors, for example gasps after a medullary hit, or shivering in a brain-dead body.

### Simulation parameters (conventions)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `dead_flag_delay` | 300 | s after `t_arr` | Post-mortem clock starts at `t_arr` | [R1-04 §10.1] |
| `acute_band` | first 60 s after an event; 60 s either side of `t_arr` | s | Always 1× | [R1-04 §0.3] [E] |
| `layer_tick` | 20 (alive), 5 (dead < 30 min), 1 (later) | Hz | Event scheduling. Motion runs on the physics/animation tick | [E] |
| `rng_seed` | per character | — | All probability rolls reproducible | [E] |

### Visual/behavioural checklist (conventions)
- A dying body is **not** still. Between the collapse and death there are jerks, gasps, twitches, sounds and fluid movement, each within a real time window.
- Nothing in this layer looks voluntary. Movements are stereotyped, repetitive, asymmetric or pointless, and they do not respond to the player the way a conscious person would.

---

## 1. The generator rule: which tissue must be alive for each sign

Every involuntary sign has a generator in the nervous system (or in muscle). If the generator is destroyed or dead, the sign cannot occur. If it is alive, the sign can occur even when everything above it is gone.

| Sign | Generator | Needs alive / working | Abolished by | Window relative to death | Tag |
|---|---|---|---|---|---|
| Purposeful movement, protective reactions, speech | Cortex + brainstem + cord | Consciousness | LOC (L2–L4 off within ~100 ms, `[R2-02 §0.4]`) | Until `t_LOC` | [K] (H) |
| Pain moan, groan, scream | Brainstem/limbic vocal circuits, larynx, airflow | Medulla, breathing | Apnoea, medullary destruction, GCS V1 | Until coma deepens | [K] (H) |
| Enhanced physiological (fear) tremor | Muscle activation + sympathetic drive | Consciousness and posture-holding muscle | LOC (limp limbs do not tremor) | Conscious phase only | [K] (M) |
| Shivering, teeth chattering | Hypothalamus → brainstem → cord → muscle | All of these, and core > ~30–32 °C | Hypothalamic or brainstem injury, deep coma, severe hypoxia or shock, cord lesion (below the level) | Stops before or at `t_LOC` in most deaths | [K] (M) |
| Syncopal / anoxic myoclonic jerks | Brainstem reticular release during transient cortical hypoxia | Brainstem still alive; cortex failing | Brainstem destruction | `t_LOC` to about `t_LOC` + 30 s | [S1] [K] (M) |
| Anoxic tonic spasm | Brainstem (vestibulospinal/reticulospinal release) | Brainstem alive | Medullary destruction | ~10–40 s after complete cerebral ischaemia | [K; M5] (L–M) |
| Epileptic seizure (tonic–clonic) | Cortex (with thalamocortical circuits) | **Perfused cortex** | EEG-flat cortex (after ~15–30 s of total ischaemia), cortical destruction | Not after ~30 s of no cerebral flow | [K] (H) |
| Decorticate / decerebrate posturing | Brainstem below the lesion (red nucleus, vestibular nuclei) + cord | Lower pons/medulla and cord | Medullary/lower-pontine failure (becomes flaccid, GCS M1) | Hours of coma until medullary failure | [S10] [K] (H) |
| Agonal gasping | Medullary gasp generator (pre-Bötzinger complex in "gasping mode") + phrenic nerves C3–C5 + diaphragm | **Medulla** and C3–C5 | Medullary destruction, C1–C3 cord section (face/neck "gasps" only, no airflow) | Mostly 10 s – 5 min after `t_arr`; also terminal hypoxia with a beating heart | [K; M1, M2] (M) |
| Snoring (stertor) | Airflow past a slack tongue/soft palate | Spontaneous breathing | Apnoea; lateral/prone posture reduces it | While breathing and unconscious | [K] (H) |
| Cough | Medulla + vagal afferents | Medulla, some airway reflex | Deep coma (reflex depressed), brain death | Living | [K] (H) |
| Active vomiting (retching) | Medullary emetic centre (area postrema, nucleus tractus solitarius) + abdominal muscles | Medulla | Brain death, deep brainstem failure | Living | [K] (M) |
| Passive regurgitation | None (gravity, abdominal pressure) | Nothing | — | Living, dying **and dead** (when the body is moved) | [K; M19] (M) |
| Hiccup | Medullary/phrenic/vagal reflex arc | Medulla, phrenic | Apnoea, medullary destruction | Living | [K] (M) |
| Spinal reflex movements (toe flexion wave, triple flexion, "Lazarus" arm raising) | Spinal cord segments | **Perfused and (at least partly) oxygenated cord** with the brain dead | Cord ischaemia after `t_arr`; cord transection above the segment isolates but does not abolish | From brainstem death until ~1–3 min after `t_arr` | [S11] [K; M11, M12] (M) |
| Fasciculations, fine twitches | Hyperexcitable motor axons/terminals (hypoxia, potassium rise) | Living motor axon and muscle | Axonal failure (tens of minutes after `t_arr`) | Living, and sparse to ~10–20 min after `t_arr` | [K] (L) |
| Idiomuscular contraction when struck | Muscle fibre (supravital) | Muscle only | Muscle death | Visible contraction to ~1.5–2.5 h after death; local bulge longer | [R1-04 §12.7] [K; M20] (L) |
| Roving eye movements | Brainstem gaze centres with depressed cortex | Pons + midbrain | Brainstem failure | Coma with intact brainstem | [S16] (M) |
| Doll's-eye counter-rotation | Vestibular nuclei → PPRF/MLF → CN III/VI | Pons + midbrain | Brainstem death | Coma only | [S17] (H) |
| Pupil constriction to light | Midbrain (Edinger–Westphal) + CN III | Midbrain | Midbrain destruction, global anoxia (> ~30–60 s) | Living | [K] (H) |
| Blink, corneal reflex | Pons (CN V → VII) | Pons | Pontine failure | Living | [K] (H) |
| Lid and jaw tone | CN III, VII, V motor nuclei + sympathetic | Brainstem | Coma deepening, death | Tone fades in deep coma; zero at death | [K] (H) |
| Sweating | Hypothalamus → sympathetic chain (T1–L2) → glands | Hypothalamus/brainstem + cord + perfusion | Circulatory arrest; high cord lesion (no sweating below) | Stops at `t_arr` | [K] (M) |
| Goosebumps | Sympathetic → arrector pili (living); **rigor** of arrector pili (dead) | — | — | Living (cold, fear); again post-mortem at hours (rigor) | [K; M19] (M) |

### Simulation parameters (generator gating)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `gate_gasp` | medulla function > 0.5 AND phrenic C3–C5 intact | bool | Otherwise no airflow gasps (C1–C3: mouth/neck "gasps" without air) | [K] (H) |
| `gate_posturing` | medulla function > 0.5 AND cord intact below | bool | Level of the highest lesion selects decorticate vs decerebrate `[R2-01 §18]` | [S10] (H) |
| `gate_seizure` | cortical perfusion `perf` > 0.3 for the last 10 s | bool | No new seizure after the EEG goes flat | [K] (H) |
| `gate_spinal_reflex` | brainstem dead AND (`t` < `t_arr` + 60–180 s) | bool | The cord needs some circulation | [K; M11] (M) |
| `gate_shiver` | conscious or GCS ≥ 9, core 30–36 °C, `perf` > 0.5, hypothalamus/brainstem intact | bool | Absent below a cord lesion | [K] (M) |
| `gate_fear_tremor` | conscious | bool | | [K] (M) |
| `gate_fasciculation` | living, or `t` < `t_arr` + 600–1,200 s | bool | Rate decays after `t_arr` (§5.5) | [E] on [K] (L) |

### Visual/behavioural checklist (generator gating)
- A medullary hit: no gasps, no cough, no vomiting reflex, no posturing. The body can still show spinal twitches or a slow arm movement while the heart beats.
- A destroyed or failed brainstem: the eyes move only with the head; the pupils never react; there is no blink.
- A body that has been dead for minutes may still twitch faintly, but it never shivers, trembles, gasps rhythmically, or postures.

---

## 2. Breathing, airway sounds and airway fluids in the unconscious and dying

### 2.1 The unconscious airway: posture decides the sound

When consciousness is lost, pharyngeal and tongue tone falls. The base of the tongue and the soft palate sag toward the back of the throat under gravity `[K] (H)`.

| Posture of the unconscious body | Airway result | Sound | P(partial obstruction) / P(complete obstruction) | Fluid behaviour | Tag |
|---|---|---|---|---|---|
| Supine, head neutral | Tongue falls back | **Snoring (stertor)** on inspiration; paradoxical chest–abdomen movement if obstructed | 0.6–0.8 / 0.1–0.2 | Blood, saliva and vomit **pool in the pharynx**: gurgling, aspiration | [K] (M), [E] |
| Supine, head extended (tipped back over an edge or object) | Airway opened | Quieter breathing | 0.2–0.3 / < 0.05 | Pooling | [K] (H) |
| Sitting slumped, chin on chest | Neck flexion kinks the airway | Snoring, or silent obstruction | 0.5–0.7 / 0.2–0.3 | Fluid runs out of the mouth onto the chest | [K] (M), [E] |
| Lateral (on the side) | Tongue falls forward | Quiet or light snoring | 0.1–0.2 / < 0.05 | **Drains from the lower mouth corner and nostril** | [K] (H) |
| Prone, face down | Airway open unless the face is buried in a soft surface | Muffled; bubbling into any pool under the face | 0.1–0.2 / 0.05–0.1 (soft surface: higher) | Drains out; blood and froth pool under the face | [K] (M), [E] |

- **Complete obstruction** looks like effort without air: the chest sinks while the abdomen rises (see-saw), the space above the collarbones and between the ribs sucks in, the trachea tugs downward, and there is no sound. With a normal haemoglobin the lips go blue in **60–120 s** and the heart slows and stops in **4–8 min** `[K] (M)`, `[R1-04 §1]`.
- **Stridor** (high-pitched crowing) means narrowing at the larynx (laryngeal wound, swelling, laryngospasm from aspirated fluid). It differs from low-pitched snoring `[K] (H)`.
- **Gurgling** means liquid in the pharynx or larynx. It is heard on both inspiration and expiration and produces bubbles at the lips or nostrils `[K] (H)`.
- Snoring sound: low-pitched, fundamental ~30–300 Hz with harmonics; 45–70 dBA at 1 m, louder when the airway is narrower `[K] (L–M)`.

### 2.2 Agonal gasping in detail

**What it is.** Gasping is a brainstem reflex. When the medulla becomes severely hypoxic or ischaemic, the respiratory rhythm generator switches into a "gasping mode": brief, maximal, decrementing inspiratory bursts with long pauses. It is **not** breathing controlled by the brain above the medulla, and it does not mean the person is conscious or recovering `[K] (H)`.

**When it happens:**
- after circulatory arrest (VF, destroyed heart, exsanguination to PEA), while the medulla still has some oxygen;
- at the end of a hypoxic death with the heart still beating (airway flooding, airway obstruction, apnoea from a pontine lesion with the medulla spared): classic sequence of fast breathing, then a **primary apnoea** of ~30–90 s, then **gasping** for several minutes, then **terminal apnoea** `[K; M22] (M)`.

**Incidence:**

| Setting | Share with gasping | Tag |
|---|---|---|
| Out-of-hospital cardiac arrest, reported at the time of the call | ~40 % ✓ verified [K] (M) | [K; M1] (M) |
| Out-of-hospital cardiac arrest, observed by paramedics | ~33 % overall; higher (~40–55 %) when witnessed and reached early; falls steeply with minutes since collapse (< ~10–20 % by ~8–10 min) ✓ verified (overall ~33 % and the decline with time) [K] (M); ⚠ the exact early/late percentages not re-verified | [K; M2] (M–L) |
| Witnessed arrests with gasping survive roughly three times as often (a marker of recent collapse and a working medulla) | — ✓ verified (direction and approximate size) [K] (M) | [K; M2] (L) |
| Medulla destroyed; brain death; C1–C3 cord section | 0 (true airflow gasps impossible) ✓ verified: the gasp generator is in the medulla (pre-Bötzinger region); gasping survives a pontomedullary transection in animals but not removal of the medulla [K] (H) | [K] (H) |

**Timing and rhythm** (heart stopped; composite `[K] (M)` with game schedule `[E]`):

| Quantity | Real range | Game default | Tag |
|---|---|---|---|
| First gasp after `t_arr` | 5–120 s (median ~20–40 s). Normal-looking breaths may continue for the first 10–20 s after arrest, then turn into gasps | 30 s | [K] (L–M), [E] |
| Initial interval between gasps | 6–20 s (3–10 per minute) | 10 s | [K] (M) |
| Interval growth | Each interval ×1.15–1.5 of the previous one | ×1.3 | [E] |
| Number of gasps | 3–30 | 8 | [E] on [K] |
| Duration of the gasping phase | 1–5 min typical; up to ~10 min rarely | 3–4 min | [K] (M) |
| Amplitude decay | Each gasp ~0.8–0.9 of the previous one | ×0.85 | [E] |
| "False last breath" (one or two more gasps after an apparently final one, following a 30–120 s silence) | Common in bedside descriptions | p = 0.3 | [K] (M), [E] |

With the default schedule (first gasp at 30 s, then intervals 10, 13, 17, 22, 29, 37, 48 s), the eighth gasp falls at ~3.4 min after arrest `[E]` (corrected: was "intervals … 62 s, eight gasps span about 4 min"; see the note below).

Fact-check note on this schedule: **⚠ not re-verified** as a whole. It is an engineering schedule with no single human source. Arithmetic re-derived: 10 × 1.3ⁿ gives intervals 10, 13, 16.9, 22.0, 28.6, 37.1, 48.3 (then 62.7) s. Eight gasps starting at 30 s fall at 30, 40, 53, 70, 92, 120, 158 and **206 s (~3.4 min)**; the 62 s interval only follows the eighth gasp. Corrected: was "eight gasps span about 4 min"; the eight-gasp default ends at ~3.4 min, and the false last breath (if rolled) lands at ~5–6.5 min in the §11.2 pseudocode. Qualitatively consistent with the resuscitation literature `[K]` (M): gasping often starts within the first minute (bystanders frequently see it immediately after the collapse), the rate is low (a few per minute), and it fades over minutes. The false-last-breath p 0.3 is a pure `[E]`.

**What one gasp looks like** `[K] (M)`, magnitudes `[E]`:
- **Inspiration is short and violent: 0.2–0.6 s** (a normal breath takes 1–1.5 s).
- **Head and neck extend 5–30°**; in a sitting slump the chin lifts off the chest.
- **The jaw drops 15–35 mm** (mouth opening wide), the lips pull back, the nostrils flare.
- Shoulders lift 5–15 mm (sternocleidomastoid and trapezius). The neck muscles stand out.
- The upper abdomen pushes out 10–30 mm (diaphragm) if the airway is open. If it is obstructed, the chest sinks and the abdomen rises (see-saw).
- Some early gasps come with a **small arm, hand or shoulder jerk** (p 0.2–0.4 per gasp in the first minute).
- **Expiration is passive: 1–3 s**, the jaw half-closes, the head settles back.
- Between gasps the body is completely limp and silent.

**Sound** `[K] (M)`, `[E]`:
- a short **snort, snore or "huh"** (0.3–0.8 s), guttural when the tongue is back;
- a **gurgle or bubbling** when fluid is in the airway (blood, vomit, froth sprays or bubbles at the lips);
- sometimes a **moan or groan** on the passive expiration as air passes the vocal cords;
- 50–70 dBA at 1 m `[E]`.

**Air moved:** variable. Early gasps with an open airway can move a substantial volume (animal studies suggest up to near-normal tidal volumes), and later gasps move little. **Without circulation, no gasp keeps the brain alive** `[K; M3] (L–M)`. Do not animate gasps as recovery.

**Eyes during gasps:** they do not move relative to the skull. When the head jerks back, the eyes go with it (no doll's-eye counter-rotation once the brainstem is failing). Pupils keep dilating on their own clock `[R1-04 §11.9]`.

**The "pseudo-gasp" of brain death** `[K; M11, M12] (M)`: after brainstem death with the heart still beating, the spinal cord can produce **respiratory-like movements**: shoulders elevate and adduct, the back arches, and the intercostal spaces pull in, with **no meaningful airflow and no sound**. Use this only in the spinal-reflex window (§5.4).

**C1–C3 cord section, awake** `[R1-04 §6.2]`: the brain is intact but the diaphragm is disconnected. The face and neck make **silent gasping attempts** (mouth opening, neck muscles straining, shoulder shrugs through CN XI) at ~10–30 attempts per minute while awake and panicking, slowing as hypoxia sets in, then stopping at loss of consciousness (1.5–3 min) `[E]` on `[K]`.

### 2.3 Breathing in slow deaths (hours) and the final breaths

Slow dying (raised intracranial pressure, slow bleeding with compensation, tamponade over hours) passes through recognisable breathing changes. The best observational data come from palliative care. They are the only large prospective data on what people look like in their final hours, but the underlying diseases differ from trauma. Use them only for deaths that last hours.

| Sign | Look and sound | Typical time before death (median) | Tag |
|---|---|---|---|
| Death rattle | §2.4 | ~16–23 h | [K; M13, M15] (L–M) |
| **Respiration with mandibular movement** ("jaw breathing") | The jaw drops **5–20 mm with every inspiration**; the head is often extended; shallow breaths | ~2–3 h | [K; M13] (L–M) |
| Peripheral cyanosis, cold mottled extremities | §8 | ~1 h | [K; M13] (L–M) |
| Loss of the radial pulse | For a "check pulse" interaction | ~1 h | [K; M13] (L–M) |
| Periods of apnoea, Cheyne–Stokes breathing | Pauses of 10–60 s that lengthen | Hours | [K; M14] (M), `[R1-04 §5.5]` |
| Highly specific signs of death within ~3 days | **Pupils not reacting to light; reduced response to voice and to visual stimuli; inability to close the eyelids; drooping of the nasolabial folds; hyperextension of the neck; grunting of the vocal cords on expiration; upper-GI bleeding** ✓ verified: these are the eight bedside signs of Hui et al. 2015 (*Cancer*), each with specificity > 95 % for death within 3 days; individually they have low sensitivity (most dying patients show only some of them) `[K]` (H) | Days to hours | [K; M14] (M) |

- Typical order: death rattle → mandibular breathing → cyanosis of the extremities → loss of the radial pulse → death `[K; M13] (L–M)`.
- **The final breaths**: shallow, widely spaced (30–120 s apart), often with the jaw movement above. They may end with one or two gasps. The "false last breath" (§2.2) is common `[K] (M)`.
- For trauma deaths lasting tens of minutes (slow limb bleed, §10.4), compress the sequence: fast shallow breathing (30–40/min), sighing, then slower irregular breaths, then gasps at PEA `[R1-04 §7.2]`.

### 2.4 Death rattle

- **Mechanism**: saliva and bronchial secretions pool in the hypopharynx and upper airway of a person who can no longer swallow or cough. They oscillate with each breath `[K] (H)`.
- **Prevalence**: 23–92 % of dying patients across studies, typically ~35–50 % `[K; M15] (M)`. ✓ verified: the 23–92 % range is the one quoted in the death-rattle reviews (including the Cochrane review of Wee & Hillier) `[K]` (M–H).
- **Time from onset to death**: median ~16–23 h; most die within ~48 h of onset `[K; M13, M15] (L–M)`. ✓ verified (order of magnitude: many hours, not minutes) `[K]` (M); ⚠ the exact medians (16 h in Wildiers & Menten, 23 h in Morita) were not re-opened.
- **Conditions**: reduced consciousness **plus** loss of swallowing **plus** enough time for secretions to accumulate. Unstimulated saliva flow is **~0.3–0.5 mL/min** `[K] (H)`, so 30–60 min without swallowing puts **10–30 mL** in the pharynx, enough to be audible `[E]`.
- **Sound**: a coarse, wet rattle or gurgle on inspiration and expiration, in time with breathing, **audible across a room (3–5 m)** `[K] (M)`; 40–60 dBA at 1 m `[E]`.
- **In the game**: no death rattle in deaths faster than ~30 min. Blood, froth and vomit produce a similar gurgle immediately (§2.5–2.7), and that is a different sound source.
- Lying on the side makes it quieter (secretions drain) `[K] (M)`.

### 2.5 Blood in the airway: gurgling, coughing, spitting, frothy pink blood

**Sources and what each does:**

| Source | How blood reaches the airway | Onset | Rate | Typical picture | Tag |
|---|---|---|---|---|---|
| Nose, midface, posterior nasal bleeding | Runs down the back of the throat | Seconds | 20–150 mL/min (face) | Swallowed (later vomited dark), spat, or aspirated when unconscious | `[R1-03 §5]` [K] (M) |
| Mandible fractured on both sides ("flail" front jaw) | Tongue loses its anterior anchor and falls back | Immediate | — | **Airway obstruction when supine**; the conscious victim holds the jaw forward and leans forward | [K] (H) |
| Skull-base fracture | Blood (± CSF) into the nasopharynx | Seconds–minutes | Low–moderate | Blood from the nose and down the throat; gurgling in the unconscious | [K] (M) |
| Larynx / trachea wound | Blood directly into the airway | Immediate | High | **Coughing, spraying blood, bubbling at the wound, hoarse or absent voice**; subcutaneous emphysema | `[R2-02 §3]` [K] (H) |
| Cut throat (fatal cases) | Open airway + vessels | Immediate | High | Causes of death in a 74-case autopsy series: **exsanguination ~50 %, aspiration of blood 36.5 %**, air embolism in a minority (~13.5 %, the remainder) ⚠ not re-verified (source not reachable). Arithmetic consistent: 27/74 = 36.5 %, 37/74 = 50 %. A fatal-case series over-represents deep cuts through the airway | [S19] (M) |
| Lung wound | Haemoptysis | 5–60 s | Streaks to tens of mL per cough; hilar injury 100+ mL | **Bright red frothy blood**, wet breathing `[R1-04 §9.3]` | [K] (H) |
| Tongue, mouth | Direct | Immediate | Low–moderate | Mouthfuls of blood, drooling | [K] (H) |

**The conscious victim with blood in the airway** `[K] (H)`:
- **sits up and leans forward** (chin forward, mouth open, drooling) and **refuses to lie back**;
- spits repeatedly (every 5–30 s);
- coughs in bouts;
- wipes the mouth with the back of the hand and looks at it;
- swallows some blood, which is often vomited 10–60 min later as dark red clots or "coffee grounds" `[K] (L–M)`.

**Cough mechanics** `[K; M35] (L–M)`, `[E]`:

| Phase | Duration | Visible / audible |
|---|---|---|
| Inspiration | 0.5–1.5 s | Deep breath in, shoulders lift |
| Compression (glottis closed) | ~0.2 s | Brief pause, abdomen tightens, face strains |
| Expulsion | 0.2–0.5 s; peak flow ~3–9 L/s within ~50 ms | Explosive sound; mouth-exit air speed ~5–20 m/s (typical ~10) |
| Bout | 1–5 coughs, bouts every 10–60 s early | Head and trunk jerk forward 5–15° with each cough `[E]` |

- **Coughed blood spatter** `[E]` on `[K]`: a fine mist (0.1–1 mm droplets) plus larger drops (1–4 mm). Most lands within **0.5–1.5 m**. Stains may contain small bubbles or vacuoles ("expirated" bloodstain features) `[R1-04 §9.3]`.
- **Spitting** `[E]`: a 1–10 mL bolus at 2–5 m/s, travelling 0.5–2 m.

**The unconscious victim** `[K] (M)`, thresholds `[E]` (L):
- Supine: blood pools in the pharynx and produces **gurgling with every breath**, **bubbles at the lips and nostrils**, and **aspiration**.
- Cough reflex: present but weak if the brainstem is intact (GCS 4–8); absent in deep coma and brain death.
- **Aspirated volume effects**: ~1–3 mL/kg (75–225 mL) impairs oxygenation noticeably; ~10 mL/kg (~750 mL), or a large clot at the larynx, gives asphyxia within minutes. These thresholds are borrowed from drowning physiology and are `[E]` (L).
- Lateral or prone: blood drains out of the lower mouth corner and nostril, pooling under the face. Gurgling is reduced.

**Frothy pink blood**: blood mixed with air in the airways forms a foam of fine bubbles (0.1–1 mm) that is stable for minutes, pink to bright red, and reforms at the lips with each breath `[K] (H)`. Colours are in `[R1-04 §9.5]`.

**Forensic note** (for an autopsy or forensic mode): **aspirated blood in the lungs and swallowed blood in the stomach prove that the victim breathed and swallowed after the injury**. Aspirated blood gives a speckled red lobular pattern on the lung surface `[K; M19] (H)`.

### 2.6 Froth from the lungs without a chest wound: neurogenic pulmonary oedema

- Severe brain injury can cause a sympathetic storm that floods the lungs with protein-rich fluid (**neurogenic pulmonary oedema**) `[K; M31] (M)`.
- **Look**: **white-to-pink froth at the nostrils and mouth**, fine bubbles, wet crackling breathing, falling oxygen saturation. After wiping, it **reforms within minutes** `[K] (M)`.
- **Onset**: minutes to hours after the injury (an early form within ~0.5–4 h; a delayed form at 12–72 h) `[K; M31] (L–M)`.
- **Frequency**: common in fatal head injuries. It is reported in roughly a third of people dying at the scene and about half of those dying within days in one autopsy series, and in a smaller share of severe head injuries seen clinically `[K; M31] (L)`. ✓ verified (M): the checker independently recalls the Rogers 1995 autopsy figures as ~32 % (died at the scene) and ~50 % (died within ~96 h). Clinical series of severe TBI report NPE in roughly 20 % or more `[K]` (L–M).
- **Important distinction (fact-check addition)**: the autopsy figures measure **lung oedema** (heavy, wet lungs), not **visible froth at the lips**. Froth appears only when the oedema is severe enough to fill the airways and the body keeps breathing or is moved. So the game's p is the chance of *visible* froth, and it must stay **below** the autopsy rate `[K]` (M).
- **Game value** `[E]`: p = 0.2–0.3 for a massive head injury that survives > 15 min; onset 15 min – 4 h (default 45 min); visible foam 5–50 mL. ⚠ not re-verified (no source measures visible froth). Kept as the upper end; a default of **0.2** is recommended so that visible froth stays well under the 32–50 % autopsy oedema rate. Onset ✓ consistent with the "early form" (minutes to a few hours) in the NPE reviews `[K]` (M).
- Other causes of froth (for the pattern library): seizures (saliva, §4), drowning (a white "foam cone"), lung wounds (§2.5) `[K] (H)`.

### 2.7 Vomiting, regurgitation and aspiration

**Probability of vomiting:**

| Situation | P(vomits) | Window | Tag |
|---|---|---|---|
| Adult head injury seen in hospital (mostly minor) (corrected: was "Adult concussion") | ~0.07; ~0.28 with a skull fracture. ⚠ not re-verified: the paper behind the search summary was never identified. Plausible `[K]` (L–M): vomiting appears in roughly 5–10 % of adults in the large minor-head-injury rule-derivation cohorts, and it is associated with fracture and intracranial lesions | Minutes to hours | [S15] (L) |
| Acute cerebellar injury | 0.6–0.8 in the first hour, repeated | Minutes | `[R2-01 §12]` (M) |
| Abdominal, groin or head injury (conscious) | 0.2–0.4 | 1–10 min | `[R2-02 §9.5]` [K] |
| Raised ICP (EDH, swelling) | Repeated vomiting is a warning sign | Lucid interval | [S15] `[R2-01 §15]` (M) |
| Massive head injury, comatose | 0.2–0.35 in the first 30–60 min (active vomiting or regurgitation) | 0–60 min | [E] on [K] |
| Swallowed blood ≥ 100–200 mL | Blood is emetic; p 0.3–0.5 | 10–60 min | [K] (L), [E] |
| Vasovagal prodrome, severe haemorrhage (class III) | 0.1–0.2 (nausea is much commoner) | Minutes | [K] (L) |

**The vomiting sequence (conscious or lightly unconscious)** `[K] (M)`, durations `[E]`:
1. **Nausea** (10–120 s): pallor, sweating, **excess saliva and repeated swallowing**, yawning, stillness, "I'm going to be sick".
2. **Retching**: 2–10 cycles at ~1 per second. The glottis is closed; the diaphragm and abdominal wall contract together; the trunk heaves forward; a dry "heave" sound.
3. **Expulsion**: 0.5–2 s. A forceful jet (projectile up to 0.5–1.5 m when upright or kneeling), 50–500 mL on a normal stomach.
4. **Recovery**: a gasp, coughing, spitting, and wiping. The next episode follows in 1–10 min if the cause persists.

**In the unconscious**:
- **Active vomiting** needs a working medulla: visible abdominal spasms and heaving, then vomit welling from the mouth and nose.
- **Passive regurgitation** needs nothing. Stomach contents flow up and out when the lower-oesophageal tone is gone, especially with abdominal pressure (a knee on the abdomen, being dragged), head-down tilt, or when the body is moved `[K] (M)`.
- **Aspiration** `[E]` on `[K]`: supine p 0.5–0.8 per vomiting episode; lateral 0.1–0.2. Signs are a sudden **gurgling or rattling**, bubbling vomit in the mouth, cough (only if the reflex remains), cyanosis, and a slowing heart.
  - Large particulate aspiration obstructs the airway: asphyxial arrest in **4–8 min**, as for complete obstruction (§2.1) `[K] (M)`.
  - Chemical pneumonitis develops over hours (out of scope).

**After death**: gastric contents are found in the airways in a substantial share of all autopsies (on the order of 20–25 %). Many of these are **agonal or post-mortem** (regurgitation during dying, moving the body, resuscitation) `[K; M19] (M)`. So a dead body that is rolled or lifted can leak vomit from the mouth and nose: p 0.05–0.15 per rough movement if the stomach was not empty `[E]`.

**Colours** `[E]` (tune under game lighting):

| Content | sRGB | Notes |
|---|---|---|
| Fresh swallowed blood with clots | `#7A0E14`, clots `#4A0A0E` | 10–30 min after swallowing |
| "Coffee grounds" (acid-altered blood) | `#3B2A20` granules in `#6B5A3E` fluid | ≥ 30–60 min in the stomach |
| Food vomit | `#B59A6A` base, variable chunks | Sour smell (flavour only) |
| Bile (after repeated vomiting) | `#9AA63A` → `#6E7A2A` | Thin, yellow-green |
| Blood + froth from the airway (for contrast) | `#E04A56`, foam `#F4C9CC` | `[R1-04 §9.5]` |

### 2.8 Other respiratory automatisms

| Automatism | Cause in this game | Look and sound | Rate / duration | Tag |
|---|---|---|---|---|
| **Sigh** (a breath of 2× normal volume) | Anxiety, haemorrhage (air hunger), presyncope | Deep audible inhalation, slow exhalation | Normally ~1 per 5 min; 1–4 per min in distress | [K] (M), [E] |
| **Yawn** | Vasovagal prodrome, haemorrhage class II–III, early herniation (diencephalic stage) | Wide jaw opening 3–6 s, eyes squeeze, head tilts back | 1–3 per min in the prodrome | [K] (L–M) `[R2-01 §15.6]` |
| **Hiccup** | Medullary lesion, swallowed blood or air (gastric distension), diaphragm irritation (haemoperitoneum) | A sudden diaphragm jerk (abdomen and shoulders twitch), glottis snaps shut ~35 ms later: "hic" | 4–60 per min in bouts of minutes | [K] (M) `[R2-01 §13.3]` |
| **Moan / groan** | Stupor (GCS V2), pain in a lightly unconscious person, passive expiration past the cords | Low, wordless, on expiration | With breaths, or to stimuli | `[R2-01 §5.2]` [K] (H) |
| **Grunting of the vocal cords** | Dying (hours) | Short expiratory grunt with each breath | Every breath | [K; M14] (M) |
| **Epileptic cry** | GTC onset | §4 | Once, 0.5–3 s | [K] (M) |
| **Post-mortem groan** | Pressing the chest or moving a dead body | Passive air past the cords | On movement | `[R1-04 §12.1]` |

### Simulation parameters (breathing and airway)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `stertor_p_supine` / `obstruct_p_supine` | 0.6–0.8 / 0.1–0.2 | p | Unconscious, head neutral. Lateral 0.1–0.2 / < 0.05 | [K] (M), [E] |
| `obstruct_to_cyanosis` / `obstruct_to_arrest` | 60–120 / 240–480 | s | Complete obstruction, normal Hb | [K] (M) |
| `gasp_p` | VF / destroyed heart 0.45; exsanguination to PEA 0.4; asphyxia with a beating heart 0.7; medulla destroyed 0 | p | Multiply by `exp(−t_onset / 300 s)` if the roll happens late. ✓ verified: base rates sit in the 33–40 % (early-witnessed higher) literature band; medulla = 0 ✓ (H). Asphyxia 0.7 is `[E]`; filmed hangings showed respiratory movements in essentially every case `[K; M10]`, so 0.7–0.9 is defensible | [K; M1, M2] (M), [E] |
| `gasp_first` | 5–120 (default 30) | s after `t_arr` | ⚠ not re-verified (`[E]` on `[K]`); a default of 15–30 s is equally defensible, since bystanders often see gasping right after the collapse | [K] (L–M) |
| `gasp_interval0` / `gasp_interval_growth` | 6–20 (default 10) / ×1.15–1.5 (default 1.3) | s / × | ⚠ not re-verified; engineering schedule | [K] (M), [E] |
| `gasp_count` / `gasp_phase_max` | 3–30 (default 8) / 60–300 (tail 600) | — / s | Stop at whichever comes first. Default 8 gasps end at ~206 s (arithmetic re-derived) | [K] (M), [E] |
| `gasp_amp_decay` | 0.85 | × per gasp | | [E] |
| `gasp_insp_time` / `gasp_exp_time` | 0.2–0.6 / 1–3 | s | | [K] (M) |
| `gasp_neck_ext` / `gasp_jaw_open` / `gasp_shoulder_lift` | 5–30° / 15–35 mm / 5–15 mm | ° / mm | Additive pose on each gasp | [E] |
| `gasp_limb_jerk_p` | 0.2–0.4 per gasp in the first minute, then 0.05 | p | Small arm or shoulder jerk | [E] |
| `false_last_breath_p` | 0.3 | p | 1–2 extra gasps after a 30–120 s pause | [K] (M), [E] |
| `c1c3_silent_gasp_rate` | 10–30 falling to 0 at LOC (90–180 s) | /min | No airflow, no sound | [E] on [K] |
| `death_rattle_p` | 0 if unconscious < 30 min; 0.3–0.5 if unconscious and not swallowing > 60 min | p | Loudness ×0.5 when lateral | [K; M15] (M), [E] |
| `saliva_flow` | 0.3–0.5 | mL/min | Pharyngeal pooling when swallowing is lost | [K] (H) |
| `rmm_jaw_drop` | 5–20 | mm per breath | Deaths lasting hours only | [K; M13] (L–M), [E] |
| `cough_bout` / `cough_interval` | 1–5 coughs / 10–60 s | — / s | Lung or airway blood, conscious or GCS ≥ 9 | [K] (M), [E] |
| `cough_exit_speed` / `cough_spatter_range` | 5–20 (default 10) / 0.5–1.5 | m/s / m | | [K; M35] (L), [E] |
| `spit_interval` / `spit_volume` | 5–30 / 1–10 | s / mL | Conscious with oral blood | [E] |
| `aspiration_hypoxia_vol` / `aspiration_asphyxia_vol` | 1–3 / ~10 | mL/kg | Drowning-derived analogy | [E] (L) |
| `npe_p` / `npe_onset` | 0.2–0.3 (default 0.2) / 15–240 (default 45) | p / min | Massive head injury surviving > 15 min. p = *visible* froth, which must stay below the autopsy oedema rate (32–50 %) ⚠ | [K; M31] (L), [E] |
| `vomit_p` | see §2.7 table | p | | [S15] [K] [E] |
| `retch_cycles` / `retch_rate` / `expulsion_time` / `vomit_volume` | 2–10 / ~1 per s / 0.5–2 s / 50–500 mL | — | | [K] (M), [E] |
| `aspiration_p_per_vomit` | supine 0.5–0.8; lateral 0.1–0.2 | p | Unconscious | [E] on [K] |
| `pm_regurg_p_per_move` | 0.05–0.15 | p | Dead body moved roughly, stomach not empty | [K; M19] (M), [E] |
| `hiccup_rate` | 4–60 | /min | Bouts of minutes | [K] (M) |

### Visual/behavioural checklist (breathing and airway)
- An unconscious body on its back **snores**. Rolled onto its side, it goes quiet and drools blood or saliva from the lower mouth corner.
- After the heart stops, about four in ten bodies take **sudden, deep, snorting gasps**: the head jerks back, the mouth gapes, the shoulders lift, then everything goes slack. The gaps grow from about 10 s to a minute. They stop within a few minutes, sometimes with one more gasp after a long silence.
- With blood in the throat, every breath **gurgles** and **bubbles form at the lips and nostrils**. A conscious victim sits bent forward, spitting and coughing blood spray; it will not lie down.
- Bright pink froth means a lung or airway injury. White-to-pink froth reforming at the nose of an unconscious head-injury victim means fluid in the lungs from the brain injury.
- Vomiting goes pale → salivating and swallowing → rhythmic heaving → the jet. An unconscious body on its back that vomits gurgles, turns blue and may stop breathing.
- **No death rattle in a fast death.** The rattle belongs to someone who has been unconscious for hours.
- Audio library: snore loop (rate-synced), gasp one-shots (snort, huh, gurgle variants), gurgle layer scaled by airway fluid volume, cough bouts, retch and vomit, spit, hiccup, sigh, yawn, grunt, rattle loop.

---

## 3. Transient loss of consciousness with movement: convulsive syncope and the anoxic sequence

### 3.1 Convulsive syncope (a faint)

The best human video data come from healthy volunteers made to faint (`[S1]`, 56 episodes; `[S2]`, eye movements). The same picture appears at the end of the heart-shot window, at the moment of haemorrhagic collapse, and in orthostatic faints, **except that dying people do not wake up** `[R2-02 §5.6]`.

| Feature | Value | Tag |
|---|---|---|
| Study population (fact-check addition) | 59 healthy young volunteers; faints induced by hyperventilation + orthostasis + Valsalva; 56 episodes, of which **42 were complete syncopes** (the percentages below refer to these). An induced faint in a young healthy person is a model; spontaneous and haemorrhagic faints may differ | [S1] `[K]` (M) |
| Duration of unconsciousness (faint that recovers) | **12.1 ± 4.4 s** ✓ verified `[K]` (H) | [S1] (M–H) |
| Myoclonic jerks | **~90 %** of induced syncopes. Multifocal, arrhythmic, proximal and distal, sometimes generalised ✓ verified `[K]` (H) | [S1] (M) |
| Myoclonus in tilt-table (reflex) syncope | Seen in a smaller share (roughly half) in another video-EEG series. ⚠ not re-verified | [K; M7] (L) |
| Other movements: head turning, oral automatisms (lip smacking, chewing), righting movements (trying to sit up) | **79 %** ✓ verified `[K]` (M) | [S1] (M) |
| Eyes | **Open** throughout ✓ verified `[K]` (H). Early **tonic upward deviation**: 7 of 14; downbeat nystagmus then upward deviation: 6 of 14; primary position: 1 of 14. ⚠ counts not re-verified; the qualitative result (upward deviation predominates, sometimes after a few beats of downbeat nystagmus; transient) ✓ `[K]` (M) | [S1] [S2] (M) |
| Experiences reported afterwards (fact-check addition) | Visual and/or auditory hallucinations (grey haze, lights, dream-like scenes, roaring noise) in roughly 60 % of the induced faints. Useful for survivor dialogue ("I saw…/heard…") | [S1] `[K]` (M) |
| Snoring breathing | In the deepest part of the faint (flat EEG phase) | [K; M7] (L) |
| Number of jerks | Usually **1–10** (median ~3–5), rarely up to ~20. No rhythm and **no slowing pattern**. ✓ verified (M): consistent with Shmuely et al. 2018 (video analysis of tilt-induced syncope vs convulsive seizures: syncope has few irregular jerks, seizures have many jerks with progressively lengthening intervals). Attribution corrected: was `[K; M8, M9]`; Sheldon 2002 [M9] is a questionnaire study of historical criteria and contains no jerk counts | [K; M8] (L–M) |
| Duration of jerking | Usually < 10–15 s; not > 30 s | [K; M8] (L–M) |
| Brief tonic stiffening (opisthotonus, arms extended) | p ~0.1–0.2, 1–5 s, usually with longer asystole | [K; M5] (L) |
| Moaning or groaning | p ~0.2–0.4 | [K] (L) |
| Urinary incontinence | p ~0.1–0.25 (does not distinguish syncope from seizure) | [K] (L–M) |
| Tongue biting | Rare (p < 0.05); the **tip** rather than the side ✓ verified `[K]` (M) | [K; M26] (M) |
| Prodrome (vasovagal or orthostatic) | 10–60 s: light-headedness, warmth, nausea, sweating, **pallor**, greying/tunnelling vision, muffled hearing, yawning | `[R2-02 §2.3]` [K] (M) |
| Prodrome (cardiac: arrhythmia, destroyed heart) | None, or 3–7 s of greying before the collapse | [K] (M) |
| Recovery when lying flat | Oriented within ~30 s, no prolonged confusion. Pale, sweaty, nauseated, tired. Flushing if the heart restarts after asystole | [K] (M) |
| G-force loss of consciousness (pilots) | Absolute incapacitation ~12 s, then ~12 s of relative incapacitation (confused). Brief myoclonic convulsions in ~70 %, a few seconds long. ✓ consistent with the checker's recall of Whinnery & Whinnery 1990 (absolute ~12 s, relative ~15 s, convulsions in ~70 % lasting ~4 s) `[K]` (M) | [K; M36] (L–M) |

**The fall**: flaccid crumple (archetype A, `[R2-02 §5.1]`), or a brief stiff topple if a tonic spasm comes first. No protective arms `[S20]`. Cardiac collapse is "crashing", with no self-protection; exertional collapse is a slower crumple `[S21]`.

### 3.2 Complete circulatory arrest: second by second (heart destroyed, VF, asystole)

Composite of neck-cuff experiments (`[K; M4]`), induced asystole and VF (`[K; M5, M6]`), G-LOC (`[K; M36]`) and syncope video (`[S1]` `[S2]`). Timing from `t_arr`. For a destroyed heart, add **2–5 s** of residual arterial pressure, which shifts LOC to **8–15 s** `[R1-04 §8]`.

Fact-check notes on this timing:
- ✓ verified `[K]` (H): Rossen, Kabat & Anderson (1943) stopped cerebral flow with a neck cuff at ~600 mmHg; consciousness was lost after **~5–10 s, mean ~6.8 s**. Some secondary summaries give the upper end as ~11 s.
- ✓ consistent `[K]` (M): after a sudden cardiac standstill, arterial pressure decays over several seconds rather than instantly, so LOC comes a little later than with the cuff. Tilt-table and device-testing observations put it at roughly 6–12 s for asystole or VF. The 8–15 s window for a destroyed heart is a reasonable game range (and matches the FBI "10–15 s" doctrine, §10.2).
- **Gap added: posture** `[K]` (M). Upright, the brain sits ~25–35 cm above the heart and loses that hydrostatic head of pressure first, so LOC comes at the **short** end (6–10 s). Supine, the same arrest is tolerated a few seconds longer (**10–15 s**, occasionally up to ~20 s). Game rule `[E]`: `loc_time × 0.85` upright, `× 1.2` supine or already fallen.
- EEG silence: `[R1-04]` gives 10–40 s (typically ~20 s); the 15–30 s used below lies inside that band ✓ consistent.

| t after `t_arr` | What happens | Eyes | Breathing / sound | P and notes | Tag |
|---|---|---|---|---|---|
| 0–4 s | Nothing visible (oxygen reserve) | Normal | Normal | — | [K] (H) |
| 3–7 s | Vision greys and tunnels (retina first), light-headed. Voluntary action continues | Unfocused | May gasp "I…" | Conscious | [K] (M) |
| **5–10 s (mean ~7)** | **Loss of consciousness** when flow stops completely. **Destroyed heart: 8–15 s** ✓ verified (cuff 5–10 s, mean 6.8 s; heart 8–15 s consistent) | Fixed stare, **open** | Breathing continues | Tone gone within ~0.1 s; fall 0.6–1.2 s. Posture: upright short end, supine long end | [K; M4] (H), [S22] |
| LOC + 0–3 s | Collapse | **Upward deviation 10–30°** begins (p 0.6–0.9); downbeat nystagmus first in ~40 % of those. **Transient**: this is the "eyes rolled up" of the collapse, not of death | Air forced out on impact | | [S2] (M) |
| LOC + 1–15 s | **Myoclonic jerks** (p 0.6–0.9): 1–10 irregular jerks of arms, legs, face and head. Head turning, lip smacking, chewing (p ~0.5–0.8) | Up, then drifting back to the midline over 10–60 s | Snoring possible | | [S1] (M) |
| 15–30 s | **Anoxic tonic spasm** (p 0.15–0.3): arms extended and turned in, legs extended, back and neck arched, jaw clenched, 5–20 s. Then limp. EEG flat by ~15–30 s | Mid-position, lids start to droop | Breathing turns irregular, then stops or becomes gasping | Incontinence p 0.1–0.2 | [K; M5, M6] (L–M) |
| 20–60 s | **First agonal gasp** (p ~0.45) | No movement relative to the head | Snort / gurgle | §2.2 | [K; M1, M2] (M) |
| 30–45 s | Pupils begin to dilate | | | | `[R1-04 §11.5]` (M) |
| 60–120 s | Pupils wide and fixed (6–8+ mm). Face pale-grey, lips dusky (full blood volume) or waxy white (exsanguinated) | Fixed, slightly divergent | Gasps every 10–30 s | | `[R1-04 §11]` [K] (M) |
| 1–5 min | Gasps weaken and stop. Occasional fine twitches of fingers, face or calves | Lids settle half-open | Silence after the last gasp; a passive sigh | Fasciculation p 0.2–0.4 (§5.5) | [K] (M), [E] |
| 4–6 min | Irreversible cortical injury begins | Gloss fading | — | | [K] (H) |
| 5 min | `t_dead` flag | | | | [R1-04 §10.1] |

### 3.3 Anoxic-ischaemic sequence with the heart still beating

When blood flow to the brain stops but the heart keeps beating (neck compression, near-complete cerebral ischaemia), the sequence is longer and more dramatic, because the spinal cord and parts of the brainstem stay perfused. The only human video-timed data come from forensic analyses of filmed neck-compression deaths `[K; M10] (L–M)`. Rounded means:

| Event | Time after onset of cerebral ischaemia | Tag |
|---|---|---|
| Loss of consciousness | ~10–15 s (checker's recall of the 8-case paper: 13 ± 3 s) ✓ | [K; M10] (M) |
| Generalised convulsions (jerking) | ~15 s (recall: 14 ± 3 s) ✓ | [K; M10] (M) |
| Decerebrate rigidity (extension) | ~20 s (recall: 19 ± 5 s) ✓ | [K; M10] (M) |
| Deep rhythmic abdominal respiratory movements | Start ~15–20 s; seen in essentially every case ✓ | [K; M10] (L–M) |
| Decorticate rigidity (flexion) | ~40 s (recall: 38 ± 15 s) ✓ | [K; M10] (M) |
| Loss of muscle tone | ~1–1.5 min (recall: 1 min 17 s ± 25 s) ✓ | [K; M10] (M) |
| Last respiratory movement | ~1–2 min (recall: range 1 min 02 s – 2 min 05 s) ✓ | [K; M10] (M) |
| Last isolated muscle movements (twitches) | **~2 to ~7.5 min** (default 4 min). Corrected: was "up to ~4–7 min"; the checker recalls a range of ~1 min 52 s to ~7 min 31 s in the 8-case series | [K; M10] (M) |

Fact-check notes `[K]` (M): ✓ verified from the checker's independent recall of the Sauvageau 2010 abstract (not re-opened; web access unavailable). Caveats: (1) times run from the **start of suspension**, not from a measured stop of cerebral flow; (2) hanging combines carotid (and often vertebral) occlusion with venous congestion and sometimes airway closure, so it is not a pure ischaemia model; (3) the 2011 14-case paper reports the same order, with **longer and more variable** times when suspension was incomplete or interrupted ("ischaemic habituation") or the person was intoxicated with alcohol. Confidence raised from (L–M) to (M) for the order and the rounded times.

- **Use this table as the template for any "brain cut off, heart beating" death**: brainstem compression at the end of herniation, bilateral carotid occlusion, and C1–C3 deaths once the victim is unconscious (hypoxic rather than ischaemic, so stretch the times 5–10× before LOC).
- Order to reproduce: **jerks → extension → flexion → limp**, with breathing movements running from ~15 s to ~1–2 min and sparse twitches for several more minutes `[E]`.

### 3.4 Syncope vs seizure vs anoxic spasm vs knockout: telling them apart (for animators)

| Feature | Convulsive syncope / anoxic jerks | Generalised tonic–clonic seizure | Anoxic tonic spasm | Knockout (fencing) | Tag |
|---|---|---|---|---|---|
| What comes first | Fall, then jerks | Stiffening (often with a cry), then the fall | Stiffening 10–30 s after flow stops | Instant tonic arm posture at impact | [S1] [S3] [S13] [K] |
| Jerks | **1–10, irregular, multifocal**, no pattern | **Dozens, rhythmic, synchronous**, slowing 3–4 Hz → ~1 Hz | None (tonic) or a few | None (tonic) | [K; M8] [S4] |
| Duration | 5–20 s | ~60 s (30–120) | 5–20 s | 2–10 s (max ~20) | [S1] [S3] [S13] |
| Eyes | Open, up, briefly | Open, deviated up or sideways for the whole seizure | Open | Open, fixed or rolled up | [S2] [K] |
| Colour | **Pale** | **Dusky, blue**, face congested | Pale-grey | Normal | [K] (M) |
| Afterwards | Awake in < 30 s (if circulation returns) | Stertorous breathing, confused 5–30 min | Limp; follows the underlying process | Wakes within seconds to minutes, dazed | [K] (M) |
| Tongue | Tip, rarely | Side, p 0.2–0.35 ✓ verified | — | — | [K; M26] (M) |

### Simulation parameters (transient LOC and the anoxic sequence)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `syncope_loc` | 12.1 ± 4.4 | s | Faint that recovers. ✓ verified | [S1] |
| `anoxic_myoclonus_p` | 0.6–0.9 (default 0.8 for sudden cardiac/haemorrhagic LOC; 0.5 for slow-onset LOC) | p | | [S1] [K; M7] (M), [E] |
| `anoxic_jerk_count` | 1–10 (median 4), rarely to 20 | jerks | Poisson, spread over 5–15 s | [K; M8] (L–M), [E] |
| `anoxic_jerk_window` | LOC + 1 s to LOC + 15 s | s | | [S1] (M) |
| `syncope_automatism_p` | 0.5–0.8 | p | Head turn, lip smack, chewing, attempt to sit up | [S1] (M) |
| `syncope_upgaze` | p 0.6–0.9; 10–30°; 2–10 s; downbeat nystagmus first in 0.4 of those | — | | [S2] (M), [E] |
| `anoxic_tonic_p` / `anoxic_tonic_duration` | 0.15–0.3 / 5–20 | p / s | Starts 15–30 s after `t_arr` | [K; M5] (L–M), [E] |
| `syncope_moan_p` / `syncope_incontinence_p` | 0.2–0.4 / 0.1–0.25 | p | | [K] (L) |
| `cerebral_arrest_loc` | 5–10 (mean 6.8); destroyed heart 8–15 | s | ✓ verified. Multiply by ~0.85 upright, ~1.2 supine (fact-check addition, `[E]` on `[K]`) | [K; M4] (H), [R1-04 §8] |
| `eeg_flat` | 15–30 | s after `t_arr` | No new seizure after this. ✓ inside the `[R1-04]` band of 10–40 s (typ. ~20) | [K] (M) |
| `ischaemic_beating_heart_seq` | LOC 10–15 s; jerks 15 s; extension 20 s; flexion 40 s; limp 60–90 s; last breathing movement 60–120 s; last twitch 110–450 s (default 240) | s | §3.3. ✓ verified (M). Corrected: last twitch was "≤ 240–450 s" | [K; M10] (M) |
| `glc_myoclonus_p` | ~0.7, a few seconds long | p | Cross-check for the anoxic jerk model | [K; M36] (L–M) |

### Visual/behavioural checklist (transient LOC)
- A faint: pale, sweaty, yawning, "I don't feel well", a slump to the ground with the eyes **open and turned up**, **a handful of irregular jerks** of the arms and face, lip smacking, then eyes back to the front and awake within about 15–30 s.
- The heart-shot collapse looks the same for the first 20 s, but the victim does not wake. It may stiffen and arch briefly, then goes limp, then starts gasping.
- A seizure is different: stiff first with a cry, then rhythmic jerking that slows down over a minute, with a blue face.
- A brain cut off while the heart still beats: jerks, then stiff extension, then flexion, then limp at about a minute, breathing heaves until about 1–2 min, then twitches for several minutes.

---

## 4. Seizures second by second

Incidence of post-traumatic seizures is in `[R2-01 §17.1]` and `[S14]`. This section is the **motion schedule** for a generalised tonic–clonic seizure (GTC), the post-ictal state, and seizures in the dying brain.

### 4.1 GTC master schedule (from the start of generalisation, t = 0)

Mean GTC duration **62 s** in a video analysis of 120 secondarily generalised seizures, with widely varying phase durations; only 27 % showed all phases `[S3]`. Phase detail `[K] (M)`; timings `[E]` within `[S3]` `[S4]` `[S5]` `[R1-04 §4.2]`.

Fact-check note: ✓ verified (M) — 62 s mean and 27 % consistent with the sibling search summary (`[R2-01 §17.2]`) and with other video-EEG series that put the convulsive part of a GTC at ~1–2 min `[K]`. **Gap added**: Theodore's five phases were *onset of generalisation → pre-tonic clonic → tonic → tremulousness (the vibratory phase) → clonic*. The table below omits the **pre-tonic clonic** phase: a few bilateral, irregular jerks (usually 1–5 s) before the body stiffens. Game `[E]`: p 0.2–0.3, 2–6 jerks at 1–3 Hz, amplitude as the clonic jerks. Also: > 5 min of continuous convulsion = status epilepticus (ILAE t1 for convulsive status) `[K]` (H).

| Phase | t (s) | Body | Eyes / face | Jaw / tongue | Breathing / sound | Skin / autonomic |
|---|---|---|---|---|---|---|
| Focal onset (wound-related, optional) | −10 to 0 | Contralateral hand/face clonic jerks 1–3 Hz; **head turns away from the wounded hemisphere** 30–90°; activity stops | Eyes forced away from the focus | Mouth pulled to one side | — | — |
| Onset | 0–1 | Sudden LOC; stiff topple (archetype B) or crumple | **Eyes open wide** (p 0.9–0.97), deviate up or sideways | Mouth opens | **Epileptic cry** (p ~0.3–0.5): a forced groan through closed vocal cords, 0.5–3 s, 70–90 dBA `[E]` | Pupils dilate within 1–3 s to 6–8 mm, unreactive |
| Tonic flexion | 0–3 (up to 5) | Shoulders elevate and abduct, elbows semi-flex, **arms rise**, trunk flexes slightly | Eyes up | Mouth may open, then clamp | Air pushed out | HR rising |
| Tonic extension | 3–15 (tonic total 10–20; range 2–40) | **Back and neck arch**, legs extend and adduct, feet plantar-flex; arms extend (and turn in) or stay flexed; fists or flexed wrists; **figure-of-4** possible after a focal onset (extended elbow opposite the focus) `[S5]` | Open, deviated; face contorted | **Jaw clenched**: lateral tongue bite risk | **Apnoea** (chest muscles locked); grunt | **Cyanosis from ~10–20 s** (lips, face congested blue-purple); HR 120–160+; bladder may void |
| Vibratory (tremulous) transition | 15–20 (2–5 s) | Fine, fast quiver of the rigid body, ~8–12 Hz, low amplitude | — | — | — | — |
| Clonic | 20–60 (30–60 s; up to ~90) | **Bilateral synchronous flexor jerks** of elbows, hips, knees and trunk, each ~100–250 ms of contraction followed by relaxation. **Frequency falls from ~3–4 Hz to ~1 Hz**; the relaxation gaps lengthen; jerks become slower and larger `[S4]` | Eyelids jerk with each beat; eyes jerky (nystagmoid) | **Jaw snaps shut with each jerk** (peak tongue-bite phase); saliva whipped into **froth** (pink if the tongue bleeds) | A grunt or snort forced out with each jerk; irregular breaths between | Cyanosis peaks, then eases as breathing resumes between jerks |
| End | ~60 (30–120) | Last jerks 1–3 s apart; sometimes a final brief tonic spasm; then **completely limp** | Eyes drift, lids partly close | Jaw slack | A deep sighing breath | Sweaty |

**Clonic frequency schedule** `[E]` on `[S4]` `[R2-01 §17.2]` (✓ verified qualitatively (M): the classic description, going back to Gastaut, is a tonic contraction broken up by a ~8 Hz vibratory phase that slows into clonic jerks, whose silent intervals lengthen progressively until the last jerk; the start and end frequencies below are `[E]` within that picture `[K]`):
`f(t) = f_end + (f_start − f_end) · exp(−(t − t_c0) / τ)`, with `f_start` 3–4 Hz, `f_end` 0.5–1 Hz, τ = 10–20 s. Stop when the next interval would exceed 2–3 s. With `f_start` 3.5 Hz, `f_end` 0.8 Hz and τ = 15 s over 40 s, the clonic phase contains about **60–70 jerks** `[E]`.

### 4.2 Signs with probabilities (GTC)

| Sign | P | Notes | Tag |
|---|---|---|---|
| Eyes open during the seizure | 0.9–0.97 | Closed eyes suggest a non-epileptic event | `[R1-04 §4.2]` [K; M29] (M) |
| Epileptic cry | 0.3–0.5 | At onset | [K] (L) |
| Lateral tongue bite | 0.2–0.35 | Very specific for GTC (specificity ~0.96–1.0). Bite marks and bleeding at the side of the tongue. ✓ verified `[K]` (M–H): Benbadis 1995 recalled as sensitivity ~24 %, specificity ~99 %; Brigo 2012 pooled sensitivity ~33 %, specificity ~96 % (seizure vs syncope), and lateral biting ~100 % specific vs psychogenic events | [K; M26, M27] (M) |
| Froth at the mouth | 0.2–0.4 | Pink if the tongue is bitten | [K] (L) |
| Cyanosis | 0.6–0.9 | Tonic and early clonic phases | [K] (M) |
| Urinary incontinence | 0.2–0.4 | Also occurs in syncope | `[R1-04 §4.3]` [K] (M) |
| Faecal incontinence | 0.02–0.05 | | [K] (L) |
| Vomiting after the seizure | 0.05–0.1 | Aspiration risk while supine (§2.7) | [K] (L) |
| Petechiae of the face and conjunctivae | 0.05–0.15 | From straining; see `[R1-04 §11.8]` | [K] (L) |
| Status epilepticus (> 5 min) | Rare, except with severe brain injury | Repeated seizures without recovery | `[R1-04 §4.3]` (H) |

### 4.3 The post-ictal state, minute by minute

| t after the last jerk | Body | Eyes | Breathing / sound | Response | Tag |
|---|---|---|---|---|---|
| 0–30 s | **Totally limp** (atonic), where it fell | Half-closed (2–5 mm) or open, gaze roving or still deviated; pupils large, sluggish | Brief pause (5–20 s), then **deep, loud, snoring (stertorous) breaths**, 20–30/min, saliva gurgling, froth at the lips | None | [K] (M) |
| 0.5–5 min | Limp; bilateral Babinski; possible Todd's paresis of the seizing side (mean 173 s, 11 s – 22 min) `[S9]` | Pupils returning to normal and reactive | Stertor fading over 1–5 min; colour returns from blue to pale | Withdraws or moans to pain | [S9] [K] (M) |
| 5–15 min | Stirs, rolls, pulls at clothes; may be agitated or combative when restrained | Opens eyes to voice | Normal | Confused words; does not know where it is | [K] (M) |
| 15–60 min | Sits up; headache, sore muscles, sleepy | Normal | Normal | Oriented by ~30–60 min | [K] (M) |

### 4.4 Focal motor seizures (kinematics added to `[R2-01 §17.3]`)

| Type | Amplitude and rhythm | Duration | Consciousness | Tag |
|---|---|---|---|---|
| Focal clonic (hand, face) | Finger/wrist flexion 10–40° per jerk; mouth corner pulled 3–8 mm; eyelid closure; 1–4 Hz, regular | 10 s – 2 min | Often preserved | [S7] [K], [E] |
| Versive (head and eye turning) | Head turns 30–90° away from the focus over 1–3 s; eyes 20–40° | 5–30 s | Usually lost at the end | [S5] [K], [E] |
| Jacksonian march | Clonic jerks spread along the body on one side in homunculus order, 5–30 s per segment | 10 s – 2 min | Preserved until it generalises | [S7] `[R2-01 §17.3]` |
| Epilepsia partialis continua | Small regular jerks of one part, 0.5–3 Hz | > 1 h | Preserved | [S8] |
| Frontal / SMA seizure | Abrupt asymmetric tonic posture (fencing-like arm, leg "bicycling"), loud vocalisation | 10–40 s | Variable, quick recovery | [S6] `[R2-01 §17.3]` |

### 4.5 Seizures in the dying and severely injured brain

- **Seizures need a perfused cortex.** They cannot start once cerebral flow has stopped and the EEG is flat (15–30 s after arrest). **Anoxic jerks and tonic spasms at collapse are not seizures** (§3) `[K] (H)`.
- **Immediate post-traumatic seizures**: see `[R2-01 §17.1]` (game p 0.05–0.10 for penetrating cortical tracks; 0.02–0.04 for blunt contusion). Concussive convulsions: ~1 in 70 sport concussions `[S12]`.
- **Subtle status epilepticus in coma** `[K] (M)`: after prolonged seizures or with severe injury, the motor signs can shrink to **small rhythmic twitches of the eyelids, mouth corner, fingers or toes (0.5–3 Hz, 1–5 mm)** and **nystagmoid eye jerks**, in a deeply comatose body, for minutes to hours. Game p 0.05–0.1 in a massive head injury that survives > 30 min `[E]`.
- **Seizure during raised ICP**: a seizure raises ICP further and can trigger herniation or apnoea. Treat a seizure in a herniating character as an accelerator of the ICP model `[K] (M)`.

### Simulation parameters (seizures)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `gtc_total` | 62 mean (30–120) | s | ✓ verified (M) | [S3] (H) |
| `gtc_pretonic_clonic_p` | 0.2–0.3; 2–6 jerks at 1–3 Hz over 1–5 s | p | Fact-check addition: Theodore's pre-tonic clonic phase | [S3] [E] |
| `gtc_tonic_flexion` / `gtc_tonic_extension` | 2–5 / 8–15 (tonic total 10–20, range 2–40) | s | | [K] (M), [E] |
| `gtc_vibratory` | 2–5 at 8–12 Hz, 0.5–2° joint amplitude | s | Additive animation, not physics | [K] (L), [E] |
| `gtc_clonic_f_start` / `f_end` / `tau` | 3–4 / 0.5–1 / 10–20 | Hz / Hz / s | Stop when the interval exceeds 2–3 s | [S4] [K] (M), [E] |
| `gtc_clonic_contraction` | 100–250 | ms | Per jerk | [K] (M) |
| `gtc_clonic_amp` | elbow 20–50°, knee 10–30°, trunk 5–15°, jaw 5–15 mm | ° / mm | Bilateral, synchronous | [E] |
| `gtc_tonic_targets` | `[R2-01 §18.2]` figure-of-4 or decerebrate-like targets at 70–90 % drive | — | | [R2-01 §18.2] |
| `gtc_eyes_open_p` | 0.9–0.97 | p | | [K; M29] (M) |
| `gtc_cry_p` / `tongue_bite_p` / `froth_p` / `cyanosis_p` / `urine_p` | 0.3–0.5 / 0.2–0.35 / 0.2–0.4 / 0.6–0.9 / 0.2–0.4 | p | | [K; M26] (L–M) |
| `postictal_stertor` | 1–5 | min | RR 20–30 | [K] (M) |
| `postictal_unresponsive` / `postictal_confused` | 2–10 / 10–60 | min | 4× game scale after the first 60 s | [K] (M) |
| `todd_duration` | 173 (11–1,320) | s | | [S9] (M) |
| `subtle_status_p` | 0.05–0.1 | p | Massive head injury > 30 min; twitch 0.5–3 Hz, 1–5 mm | [E] on [K] |
| `seizure_icp_bump` | +10–20 | mmHg during the seizure | Feeds the ICP model | [K] (L), [E] |

### Visual/behavioural checklist (seizures)
- Eyes snap open and turn; a strangled cry; the whole body goes rigid, back arched, fists clenched, jaw locked, face turning blue. After 10–20 s a fine quiver, then rhythmic jerks that **slow down** and get further apart, with a grunt and a jaw snap on each jerk and froth building at the lips. About a minute in, the last jerks come seconds apart, then the body is utterly limp.
- Then loud, deep snoring breaths, a slowly pinking face, pupils shrinking back, a bitten tongue bleeding into the froth, maybe a wet patch.
- In a comatose, badly head-injured body: tiny rhythmic twitches of an eyelid or mouth corner and jerking eyes, with no other movement.

---

## 5. Twitches, myoclonus and reflex movements: coma, brain death and after death

### 5.1 Fasciculations and myokymia (living)

- **Fasciculation**: the spontaneous discharge of a single motor unit. A **brief flicker under the skin** (contraction ~30–100 ms), usually with no joint movement; occasionally a finger or toe twitches 1–5 mm `[K] (M)`.
- Rate: irregular, ~0.1–2 per second per site when active `[K] (L)`.
- Sites: calves, thighs, deltoids, face, eyelids `[K] (M)`.
- **Myokymia**: rippling, worm-like undulation of a muscle strip (eyelid myokymia: bursts of 10–30 s) `[K] (M)`.
- Triggers in this game: exhaustion, cold, adrenaline, hypoxia, electrolyte shift in shock `[K] (L)`.

### 5.2 Hypoxic myoclonus

| Type | When | Look | P / duration | Tag |
|---|---|---|---|---|
| **Agonal (anoxic) myoclonus** | At LOC from circulatory failure | §3.1–3.2: 1–10 irregular jerks | p 0.6–0.9; 5–15 s | [S1] (M) |
| Gasp-associated jerks | With early agonal gasps | Small arm or shoulder jerk timed with the gasp | p 0.2–0.4 per gasp in the first minute | [E] on [K] |
| **Post-anoxic myoclonic status** | Circulation **returns** after prolonged hypoxia or arrest (autoresuscitation, impact apnoea that ends late), coma persists | Repetitive, often synchronous jerks of the face, eyelids, trunk and limbs, **often triggered by touch, noise or movement**; eyes may open and deviate upward with eyelid jerks | Seen in roughly a fifth to a third of comatose survivors of cardiac arrest; onset within 24 h (usually the first 6–12 h); lasts hours–days | [K; M25] (M) |
| Lance–Adams (action myoclonus) | Days–weeks later in survivors | Jerks when the person tries to move | Out of scope | [K; M24] (H) |

Game use for post-anoxic myoclonic status `[E]`: p 0.2 for a character whose brain was hypoxic > 5 min but whose circulation continues or returns. Stimulus-sensitive jerks when the player touches or moves the body, 0.5–2 bursts per second, amplitude as the syncope jerks.

### 5.3 Immediate "release" movements after destructive brain or brainstem injury (first 60 s)

When the brain above a level is destroyed instantly, the structures below are suddenly released from control. Humans have no controlled data, so the closest analogue is **penetrating captive-bolt or gunshot stunning of cattle and pigs**: typically an immediate collapse, a **tonic phase of ~10–20 s** (legs rigidly extended or flexed, back arched, no breathing), then a **clonic phase of involuntary kicking or paddling** lasting tens of seconds, then relaxation `[K; M32] (L–M)`.

Human game mapping `[E]` (L), consistent with `[R1-04 §2.6]`:

| Lesion | Tonic extension (decerebrate-like) | Leg kicking / paddling bursts | Small twitches (fingers, face) | Tag |
|---|---|---|---|---|
| Midbrain / upper pons destroyed, lower brainstem intact | p 0.3–0.6; 5–30 s | p 0.1–0.2; 10–60 s | p 0.3 | [E] on [K; M32] and `[R1-04 §2.6]` |
| Medulla / cervicomedullary junction destroyed | ~0 (flaccid at once) | p 0.05–0.15 (spinal only) | p 0.2 | [E] on [K] |
| Massive bihemispheric destruction, brainstem intact | Posturing (decorticate/decerebrate) p 0.3–0.5 | p 0.05 | p 0.2 | [E] on [K] |

- Humans have weaker spinal stepping circuits than quadrupeds. So **human leg "kicking" should be rarer, shorter and smaller** than in animal footage: 2–8 irregular bursts of hip/knee flexion–extension of 10–40° `[E]` (L).
- None of this is purposeful. Nothing orients to the player.

### 5.4 Spinal reflex movements after brainstem death (the "Lazarus" family)

After the brain and brainstem are dead, the spinal cord can still generate reflexes and short movement sequences **as long as it is perfused**. In intensive care this is seen in ventilated brain-dead patients. In this game (nobody ventilates), the window runs from brainstem death until the cord fails, roughly **1–3 min after `t_arr`**. Hypoxia of the cord is itself a trigger: arm-raising has been reported during apnoea testing and just after ventilator disconnection `[K; M11] (M)`.

**Frequency**: reported in **13–79 %** of brain-dead patients across series `[S11]` `[K; M12]`. About 40 % in the most-cited prospective series `[K; M12] (M)`; 13–22 % in another frequency study `[S11] (M)`. The full arm-raising sequence is **rare** (a few percent) `[K] (M)`.

Fact-check note: ✓ verified (M). Saposnik 2000 is recalled as 15 of 38 patients (39 %) `[K]` (M–H); Ropper 1984 described the arm-raising sequence in a handful of 60 brain-dead patients, during apnoea testing or right after disconnection from the ventilator `[K]` (M). Attribution clarified: the `[S11]` frequency paper supports only the **low end** (13–22 %); the "13–79 %" spread is the range quoted in reviews of brain-death reflexes `[K]` (M), not a value from `[S11]`. The game p 0.2–0.4 sits inside the range and is kept. The movements need a perfused, still-oxygenated cord ✓ (H).

| Movement | Look | Trigger | Duration | Share (of patients with any movement) | Tag |
|---|---|---|---|---|---|
| **Undulating toe flexion** | Toes flex one after another (2 → 5) in a wave, repeatedly | Spontaneous or plantar stimulus | 1–3 s per wave, repeating | Common | [S11] [K; M12] (M) |
| **Triple flexion** | Hip and knee flex, ankle dorsiflexes | Pinching the foot or leg | 1–5 s | Common | [K; M12] (M) |
| Plantar or finger flexion jerks | Brief flexion of toes or fingers | Stimulus, spontaneous | < 1 s | Common | [K] (M) |
| **Pronation–extension reflex** | Arm extends and pronates, sometimes both arms | Neck flexion, stimulus | 1–5 s | Less common | [K; M12] (M) |
| **Lazarus sign** | **Both arms flex at the elbows, shoulders adduct, hands rise to the chest, neck or chin, sometimes crossing; fingers flex; the trunk may flex 10–40° as if starting to sit up.** Goosebumps and sweating may accompany it | Hypoxia (apnoea), neck flexion, moving the body | Rises over 2–5 s, holds 3–10 s, falls back over 5–15 s | Rare | [K; M11] (M) |
| Respiratory-like movements | Shoulders elevate and adduct, back arches, intercostals pull in; **no airflow, no sound** | Hypoxia | Seconds, repeated | Occasional | [K; M11, M12] (M) |
| Facial myokymia | Rippling of facial muscles | Spontaneous | Seconds | Occasional | [K; M12] (L) |

**Game rule** `[E]` (consistent with `[R1-04 §10.6]`):
- Any spinal reflex movement during the hypoxic window after brainstem destruction: p 0.2–0.4.
- A full Lazarus arm-raise: p 0.03–0.05.
- None after `t_arr` + 180 s.
- **Stimulus-triggered versions** (the player moves the head, flexes the neck, stamps on a foot) have p 0.3–0.5 per stimulus while the window is open.

### 5.5 After circulatory arrest: what still moves

| t after `t_arr` | Movement | Visible? | Rate / amount | Tag |
|---|---|---|---|---|
| 0–60 s | Anoxic jerks, tonic spasm, gasps | Yes | §3.2 | [S1] [K] |
| 1–3 min | Spinal reflexes (if the brain died first), gasp-associated jerks | Yes | §5.4 | [K] (M) |
| 1–15 min | **Fine twitches (fasciculations)** of fingers, eyelids, lips, calves, as hypoxic motor axons fire | Faint | p 0.2–0.4 per body; 0.5–5 events/min, decaying (τ ≈ 3–5 min); none after ~15–20 min | [E] on [K] (L) |
| 0–30 min | **Settling under gravity**: the jaw drops, the head rolls to the side, limbs slide off supports, the chest sinks | Yes | Seconds to minutes | `[R1-04 §12.1]` (H) |
| 0–48 h | **Passive fluid movement**: blood drains from dependent wounds, froth and vomit leak when the body is moved, air is squeezed out as a groan | Yes | `[R1-04 §12.2]` | [K] (H) |
| Up to ~1.5–2.5 h | **Idiomuscular contraction**: striking a muscle (biceps) makes a local contraction and a bulge | Only when provoked | Forensic mode | `[R1-04 §12.7]` [K; M20] (L) |
| 1–12 h | **Rigor mortis**: stiffening in Nysten order; can pull fingers and toes into slight extra flexion | Slight | `[R1-04 §12.6]` | [K] (L–M) |
| Hours | **Goosebumps (cutis anserina)** from rigor of the arrector pili muscles | Yes, close-up | | [K; M19] (M) |
| Days–months | Decomposition-related movement (out of scope) | — | — | [K] |

**A dead body never does**: shiver, tremble, breathe rhythmically, posture, blink, track, or flinch at a sound. Supravital responses happen **only** when a muscle is directly struck or electrically stimulated `[K] (H)`.

**Shooting, stabbing or hitting a body that is already dead or brain-dead (fact-check addition)** `[K]` (M), `[E]`:
- There is **no convulsion, flinch or "death throe"** in response. What moves is purely mechanical: the segment that is hit takes the projectile's momentum (a 9 mm bullet carries ~2.9 N·s, enough to give the whole 75 kg body only ~0.04 m/s, but a forearm-plus-hand (1.68 kg) at most ~1.7 m/s if the bullet stops in it, and ~0.6–1.2 m/s once its attachment to the rest of the arm is counted; see `[R2-02 §1.3]`), and loose limbs, head and jaw swing and settle under gravity.
- Within the supravital window (to ~1.5–2.5 h), a hit squarely on a muscle belly can produce a **brief local contraction or bulge** at the impact site (idiomuscular response, §5.5). It is small, local and never a coordinated movement. Game `[E]`: p 0.1–0.3 per direct muscle hit, 5–20 mm local bulge, no joint movement larger than ~5°.
- Blood leaks from new wounds only by gravity (no pulsing), and air may be pushed out through the mouth as a groan if the chest is compressed `[R1-04 §12]`.

**Cadaveric spasm** (a grip frozen at the moment of death) is rare and disputed. Keep it at ≤ 0.01, only after intense activity at death `[R1-04 §12.6]`.

### 5.6 Posturing episodes triggered by stimulation (timing added to `[R2-01 §18]`)

| Quantity | Value | Tag |
|---|---|---|
| Latency from a noxious stimulus (pain, moving the body, loud noise, pressure on the chest) to the start of posturing | 0.2–1 s | [K] (L–M), [E] |
| Build-up to full posture | 0.5–2 s | `[R2-01 §18.2]` [E] |
| Hold | For the stimulus duration + 2–10 s; spontaneous episodes 5–60 s | [E] on [K] |
| Release | 1–3 s | `[R2-01 §18.2]` |
| Refractory period before the next triggered episode | 5–20 s | [E] |
| Spontaneous episodes with ICP plateau waves | Episodes accompany plateau waves that last ~5–20 min `[S26]`; posturing bursts every 30 s – 5 min during them | [S26] (M), [E] |
| Progression during herniation | Decorticate → decerebrate → flaccid; posturing **stops** when the medulla fails, which is a bad sign, not an improvement | [S10] `[R1-04 §4.1]` (H) |
| Vocal and autonomic accompaniment | Moan or grunt at onset (GCS V2), jaw clenching (decerebrate), sweating, rise in HR and BP | [K] (M) |

### Simulation parameters (twitches and reflexes)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `fasc_rate_living` | 0.1–2 per site when active | Hz | Shader ripple (§11.3) | [K] (L), [E] |
| `fasc_pm_p` / `fasc_pm_rate0` / `fasc_pm_tau` / `fasc_pm_end` | 0.2–0.4 / 0.5–5 per min / 3–5 min / 15–20 min | — | After `t_arr` | [E] on [K] (L) |
| `release_tonic_p` (midbrain/upper pons) | 0.3–0.6; 5–30 s | p / s | | [E] on [K; M32] |
| `release_kick_p` | 0.1–0.2 (midbrain), 0.05–0.15 (medulla); 2–8 bursts over 10–60 s, 10–40° | p | | [E] (L) |
| `spinal_reflex_p` / `lazarus_p` | 0.2–0.4 / 0.03–0.05 | p | Hypoxic window only. ✓ verified (inside the 13–79 % literature range; ~39 % Saposnik) | [S11] [K; M11, M12] (M), [E] |
| `pm_hit_idiomuscular_p` | 0.1–0.3 per direct muscle hit, ≤ ~2 h after `t_arr`; 5–20 mm local bulge | p | Fact-check addition: a dead body that is shot or struck shows only mechanical motion plus this local twitch | [K] (M), [E] |
| `spinal_reflex_stim_p` | 0.3–0.5 per stimulus | p | Neck flexion, foot stimulus | [E] |
| `lazarus_timing` | rise 2–5 s, hold 3–10 s, fall 5–15 s | s | | [K; M11] (L–M), [E] |
| `lazarus_targets` | shoulder adduction 10–30°, shoulder flexion 20–60°, elbow flexion 90–130°, fingers flexed, trunk flexion 10–40°, drive 30–50 % | ° | Slow, not a jerk | [E] on [K; M11] |
| `spinal_window_end` | `t_arr` + 60–180 | s | | [K] (L–M), [E] |
| `pams_p` (post-anoxic myoclonic status) | 0.2 | p | Only if circulation continues after > 5 min brain hypoxia | [K; M25] (M), [E] |
| `posture_trigger_latency` / `refractory` | 0.2–1 / 5–20 | s | | [E] on [K] |
| `cadaveric_spasm_p` | ≤ 0.01 | p | | [R1-04 §12.6] |

### Visual/behavioural checklist (twitches and reflexes)
- Right after a shot through the upper brainstem: the body may lock rigid with arms and legs straight for a few seconds, then a few aimless leg kicks, then nothing.
- Minutes after a brainstem shot, while the heart is still beating: the toes curl one after another; rarely, both arms slowly bend and the hands rise to the chest as if to grab the throat, then sink back.
- In the first 10–15 min after death: occasional faint twitches of an eyelid, a finger, a calf. They get rarer and stop.
- Touching or moving a deeply comatose head-injured body sets off stiffening spasms with a moan, which fade after a few seconds.
- A body dead for hours never moves on its own, except for slow sagging and leaking when it is moved.

---

## 6. Tremor, shivering, teeth chattering and gooseflesh

### 6.1 Fear, pain and adrenaline tremor

- **Enhanced physiological tremor**: normal tremor at **8–12 Hz** becomes visible under adrenaline (fear, pain, after violent exertion), cold, fatigue or blood loss `[K] (M)`.
- Visible fingertip amplitude **0.5–3 mm**, up to 5–10 mm in severe shaking `[E]` on `[K]`.
- Seen in outstretched or gripping hands, the jaw and lips, the voice (a shaky voice), and the legs when standing or kneeling. A fatigued leg under load can shake at a lower **~4–8 Hz** `[K] (L–M)`.
- **Onset** during or right after the violent event; lasts **5–30 min** after the threat ends ("adrenaline shakes") `[K] (M)`.
- **Stops at loss of consciousness**: limp limbs do not tremor `[K] (M)`.

### 6.2 Shivering

| Quantity | Value | Tag |
|---|---|---|
| Core temperature at which shivering starts | ~35.5–36.0 °C (higher threshold when the skin is cold; about a fifth of the drive comes from skin temperature) ✓ verified (Sessler: shivering threshold ~1 °C below the vasoconstriction threshold of ~36.5 °C; core ≈ 80 %, skin ≈ 20 % of the drive) `[K]` (M–H) | [K] (M) |
| Maximal shivering | Core ~34–35 °C ✓ consistent `[K]` (M) | [K] (M) |
| Shivering fades / stops | Below ~32–33 °C it weakens; absent below ~30–32 °C (corrected: was ~30–31 °C). ✓ verified with a widened stop: clinical hypothermia staging (Swiss system) puts the loss of shivering in the 32–28 °C stage, many texts at "< 32 °C" and others at ~30–31 °C, so use **30–32 °C** (default 31) | [K] (M) |
| Heat production | 2–5× resting metabolism; O₂ consumption +100–400 % | [K] (M) |
| Temporal pattern | Bursts that wax and wane **4–8 times per minute**, each made of a fast tremor (~8–12 Hz in large muscles; visible as a coarse 5–10 Hz shake at the hands). ✓ verified (M): the 4–8 cycles/min grouping of shivering EMG bursts is the Israel & Pozos finding `[K]` | [K; M16] (L–M) |
| Where it starts | Jaw (chattering), neck, chest and shoulders, then arms, then trunk and legs | [K; M17] (M) |
| Bedside grading (BSAS) | 0 none; **1 mild**: neck and chest only; **2 moderate**: gross movement of the arms plus neck and chest; **3 severe**: gross movement of the trunk and all four limbs. ✓ verified `[K]` (H) | [K; M17] (M) |
| Suppressed by | Severe hypoxia, hypoglycaemia, deep shock, alcohol, opioids, exhaustion, hypothalamic or brainstem injury, deep coma; **absent below a spinal cord lesion** ✓ verified (hypoxia lowers the shivering threshold and gain) `[K]` (M) | [K] (M) |

**In a bleeding casualty**:
- Haemorrhage and exposure cool the body. Vasoconstricted, cold skin makes the person **feel cold and shiver even before the core temperature falls much** ("I'm so cold") `[K] (M)`.
- Core cooling on cold ground: roughly 0.5–2 °C/h, depending on clothing, wind and wetness `[K] (L)`.
- Game onset `[E]`: shivering starts **10–40 min** after a major bleed in a conscious casualty (class II–III). It grows to BSAS 2–3, then **weakens and stops as the casualty becomes obtunded (class IV)**, even though the body keeps cooling.
- Behaviour while shivering (if conscious) `[K] (H)`: hunched, arms folded, hands tucked into the armpits, knees drawn up, teeth clenched or chattering, a broken, stuttering voice.

### 6.3 Teeth chattering

- A fast rhythmic oscillation of the jaw from shivering of the jaw muscles (or from fear): **jaw opening 1–5 mm at ~5–12 Hz**, producing an audible clicking train `[E]` (L).
- It is often the **first visible sign of shivering** and can come in bursts that match the shivering waves (4–8 per minute) `[K; M16] (L)`.
- A conscious person can partly stop it by clenching `[K] (M)`.

### 6.4 Gooseflesh (piloerection)

- **Living**: cold or a sympathetic surge (fear, the moment of injury, some seizures). Onset in 10–60 s. Bumps 0.5–1 mm on the forearms, thighs and shoulders. Hair stands up. Lasts minutes `[K] (M)`.
- **Dead**: can appear hours after death from rigor of the arrector pili muscles `[K; M19] (M)`.

### 6.5 When they stop in the dying

| Sign | Stops at | Tag |
|---|---|---|
| Fear tremor | LOC | [K] (M) |
| Shivering, chattering | Obtundation, deep shock (class IV), severe hypoxia, or LOC in most cases | [K] (M) |
| Living gooseflesh | Circulatory arrest (sympathetic output gone) | [K] (M) |

### Simulation parameters (tremor, shivering, chattering)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `fear_tremor_hz` / `fear_tremor_amp` | 8–12 / 0.5–3 mm fingertip (0.2–1.5° at wrist and fingers); severe 5–10 mm | Hz / mm | Additive, post-physics | [K] (M), [E] |
| `fear_tremor_duration` | 5–30 | min after the threat | Decays | [K] (M) |
| `leg_shake_hz` | 4–8 | Hz | Standing or kneeling while injured or exhausted | [K] (L–M) |
| `shiver_core_start` / `max` / `stop` | 35.5–36.0 / 34–35 / 30–32 (default 31) | °C | Skin-temperature bias: start at core ≤ 36.5 if skin < 30 °C. ✓ verified; corrected: stop was 30–31 | [K] (M), [E] |
| `shiver_burst_rate` | 4–8 | per min | Waxing and waning envelope | [K; M16] (L–M) |
| `shiver_hz` / `shiver_amp` | 5–10 visible / shoulders 0.5–2°, hands 5–20 mm at BSAS 3 | Hz / ° / mm | | [E] |
| `shiver_bsas_progression` | 1 (jaw, neck, chest) → 2 (+ arms) → 3 (+ trunk, legs) | grade | | [K; M17] (M) |
| `bleed_shiver_onset` | 10–40 | min | Conscious, class II–III | [E] on [K] |
| `shiver_suppress` | class IV shock, SpO₂ < 80 %, GCS ≤ 8, hypothalamic/brainstem damage, below a cord lesion | — | | [K] (M) |
| `chatter_hz` / `chatter_jaw` | 5–12 / 1–5 mm | Hz / mm | Click train audio | [E] (L) |
| `goosebump_onset` | 10–60 s (living); hours (post-mortem) | — | Normal-map layer | [K] (M) |

### Visual/behavioural checklist (tremor and cold)
- After a fight or a shot, a conscious survivor's hands, jaw and voice shake finely for many minutes.
- A bleeding casualty lying on the ground becomes grey and sweaty, says it is cold, and starts shivering: jaw first (chattering teeth), then shoulders and arms, then the whole body in waves every 10–15 s. Later, as it drifts off, the shivering fades although the body is colder.
- No tremor, shivering or chattering in the unconscious-and-dying or the dead.

---

## 7. Face, eyes, jaw, tongue and hands by state

Eye choreography by death type and post-mortem eye changes are in `[R1-04 §11]`; lesion-specific eye signs in `[R2-01 §14]`. This table is the per-state lookup for the layer.

### 7.1 Master state table

| State | Lids (aperture; P open) | Gaze | Pupils (mm) | Blink | Jaw / mouth | Tongue | Hands | Face | Tag |
|---|---|---|---|---|---|---|---|---|---|
| Conscious, injured, in pain or fear | 9–12 mm (fear: white above the iris); squeezed 3–6 mm in pain grimace | Scanning, then fixed on the threat or wound | 4–7 (sympathetic) | Bursts, then staring | Clenched, or open and panting | Normal | Clutching the wound, fists, gripping | Pain face `[R2-02 §9.1]` | [K] (M) |
| Shock class III (confused) | 5–8 mm; eyes look **sunken** | Slow, vacant, poor tracking | Normal to large, sluggish | 5–10/min | Open-mouth breathing; dry pale lips | Dry | **Fumbling, picking at clothes, weak grip** | Grey, sweaty | `[R1-04 §7.2]` [K] (M) |
| Stupor (class IV, rising ICP) | 2–6 mm; lids drop shut and struggle open | Roving, drifting | Variable | 0–5/min | Slack, 5–15 mm open | Drops back when supine | Limp; occasional plucking | Expressionless; nasolabial folds flatten | [K] (M) |
| Presyncope | Normal, then drooping | Unfocused | Dilating 1–2 mm | Yawning | Yawning | — | Reach for support | Pallor, sweat | [K] (M) |
| Syncope, anoxic LOC | **Open** (P ≥ 0.9), 6–10 mm | **Up 10–30° for 2–10 s**, then back to the midline | Dilating | None | Slack; chewing or lip smacking (automatisms) | Tip bite rare | 1–10 jerks | Pale | [S1] [S2] (M) |
| GTC tonic | Open (0.9–0.97), wide | Deviated up or sideways, fixed | 6–8, unreactive | None | **Clenched** | Side at risk | Fists or flexed wrists; arms raised then extended | Congested, blue | [K] (M) |
| GTC clonic | Lids jerk with each beat | Jerky, deviated | Dilated | Eyelid clonus | **Snapping rhythmically** | Bitten; froth | Rhythmic flexion jerks | Blue, grimacing | [S4] [K] (M) |
| Post-ictal | Half-closed 2–5 mm (P closed ~0.5) | Roving or still deviated, slightly divergent | Large, sluggish → normal | Rare | Slack, snoring | May protrude, bitten | Limp | Pale-dusky, sweaty, froth | [K] (M) |
| Coma, brainstem intact (GCS 3–8) | Closed, or **incompletely closed 1–5 mm** (P 0.3–0.7); a lifted lid closes slowly over 1–2 s | Slightly divergent, **roving** 10–30° at 5–20°/s; doll's eyes present | 2–5, reactive | None; corneal reflex present | Open 5–20 mm when supine; snoring | Falls back | Flaccid, or posturing on stimulation | Slack | `[R2-01 §14.2]` [K; M34] (M) |
| Posturing episode | May open during the episode | Dysconjugate or deviated, per lesion | Per lesion | — | **Clenched** in decerebrate | — | Decorticate fists on chest; decerebrate pronated arms with flexed wrists | Grimace | [S10] `[R2-01 §18]` |
| Brainstem dead, heart beating | **Where they were at the loss of tone**; open lids drop 2–4 mm over 1–3 s | **Fixed**; midline, slightly divergent or skewed; **doll's eyes absent** ✓ verified (absent oculocephalic reflex is a brain-death criterion) | 4–9, fixed (mean 5.0 ± 0.85; ⚠ mean not re-verified; the 4–9 mm "mid-size to dilated" range matches the AAN brain-death criteria ✓) | None | Slack; mouth open 10–30 mm when supine | Falls back | Flaccid; spinal reflexes possible (§5.4) | Dusky blue if Hb normal | [S17] [S18] `[R1-04 §11]` |
| Agonal (after `t_arr`, gasping) | Half-open 2–6 mm | Fixed near the midline | 6–8 by 1–2 min | None | Slack; **gapes 15–35 mm with each gasp** | — | Limp; small jerks with early gasps | Grey or dusky; white if exsanguinated | §2.2 [K] (M) |
| Newly dead (0–30 min) | Sudden death: open 0.55 / half 0.35 / closed 0.10 (`[R1-04 §11.3]` distribution) | Fixed, slightly divergent | 6–8 | None | Open 10–30 mm (supine) | Tip may show between the teeth | Flaccid, fingers in a loose curl | Pallor mortis | `[R1-04 §11–12]` |

### 7.2 Eyelids: numbers

- **Alert** 9–10 mm; **fear** 11–12 mm; **shock** 5–8 mm `[R1-04 §11.10]`.
- **Comatose patients often cannot close their eyes fully** (lagophthalmos). Incomplete closure is found in roughly a third to three quarters of sedated or comatose intensive-care patients, and exposure damage to the cornea in about a fifth to two fifths `[K; M34] (M)`. Typical gap 1–5 mm, with the lower white of the eye visible `[E]`.
- **At death** the lid stays near where it was and drops 2–4 mm; it never blinks shut `[R1-04 §11.3]`. Typical final aperture in a half-open eye: **3–6 mm**, showing the lower part of the iris and the white below it `[E]`.
- "Inability to close the eyelids" is one of the specific signs that death is expected within days in slow dying `[K; M14] (M)`.

### 7.3 Jaw and mouth

| State | Mouth | Tag |
|---|---|---|
| Conscious in pain | Clenched, or open and panting; lips pulled back in the pain face | `[R2-02 §9.1]` |
| Air hunger | Open 10–30 mm, lips pursed or gaping, nostrils flaring | [K] (H) |
| Unconscious, supine | **Opens 5–20 mm** as jaw tone falls; wider (10–30 mm) with the head tipped back | [K] (M), `[R1-04 §12.1]` |
| Unconscious, slumped forward | Closed or slightly open; chin on chest | [K] (M) |
| Gasping | Gapes 15–35 mm with each gasp, half-closes after | §2.2 |
| Mandibular breathing (hours) | Drops 5–20 mm with each breath | §2.3 |
| Tonic seizure, decerebrate posturing | Clenched (trismus) | [S10] [K] |
| Clonic seizure | Snaps shut with each jerk | [K] (M) |
| Dead | Slack; opens under gravity 10–30 mm (supine) within 5–30 s; **rigor fixes the jaw** from ~1–3 h in whatever position it has reached | `[R1-04 §12.1, §12.6]` |

### 7.4 Tongue

| State | Tongue | Tag |
|---|---|---|
| Unconscious, supine | Falls back; tip behind the lower teeth; causes snoring or obstruction | [K] (H) |
| Unconscious, prone or lateral | May slip forward; the tip can lie 0–10 mm between the teeth | [K] (M), [E] |
| After a seizure | Lateral bite marks, bleeding, swelling; may protrude slightly | [K; M26] (M) |
| Neck compression | Protrudes and swells, dark (forensic: tongue protrusion) | [K; M19] (M) |
| Dying over hours, mouth breathing | **Dry**, furred, cracked lips | [K] (M) |
| Dead | A protruding tip **dries brown-black** over hours (like the exposed sclera) | [K; M19] (M) |

### 7.5 Hands

| State | Hand posture | Tag |
|---|---|---|
| Conscious, wounded | Clutching or pressing the wound; fists; gripping a person, object or the ground; **clawing at the ground** when crawling | `[R2-02 §3, §9]` [K] (H) |
| Air hunger, choking, blood in the airway | **Hands to the throat**; pulling at a collar or clothing over the chest; tearing at anything around the neck | [K] (H) |
| Confusion, hypoxia, slow dying ("terminal restlessness") | **Picking or plucking** at clothes, bedding or the air; fumbling | [K] (M) |
| Frontal-lobe injury | **Grasp reflex**: closes on whatever touches the palm | `[R2-01 §4.3]` |
| Syncope | Brief jerks; sometimes a groping or reaching automatism | [S1] (M) |
| Tonic seizure / decorticate | Fists, thumb inside | [K] (M) `[R2-01 §18.2]` |
| Decerebrate | Wrists flexed 30–70°, fingers flexed, forearms fully pronated | `[R2-01 §18.2]` |
| Flaccid (unconscious, dying, newly dead) | **Resting cascade**: fingers loosely flexed, more toward the little finger. Index MCP 20–30°, little finger MCP 40–60°; PIP 30–70°; DIP 10–20°; thumb half-adducted. A hand hanging over an edge with the wrist flexed opens (tenodesis); a hand resting on its back curls more | [K] (M), [E] |
| Dead, rigor | Fixed in the flaccid posture; may curl slightly further | [K] (L) |

### Simulation parameters (face and extremities)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `lid_aperture_by_state` | table §7.1 | mm | Drives the lid bones/blendshapes | [K] (M), [E] |
| `coma_lagophthalmos_p` / `gap` | 0.3–0.7 / 1–5 | p / mm | | [K; M34] (M), [E] |
| `lid_close_after_lift_coma` | 1–2 | s | Dead: the lid stays up | `[R1-04 §11.3]` |
| `jaw_open_by_state` | table §7.3 | mm | Gravity-driven once tone < 0.2 | [K] (M), [E] |
| `jaw_tone_loss_time` | 0.5–5 | s after LOC | Supine; slower when slumped forward | [E] |
| `tongue_protrude_p` | prone/lateral 0.2–0.3; after a seizure 0.3 | p | 0–10 mm | [E] |
| `hand_rest_cascade` | MCP 20–60°, PIP 30–70°, DIP 10–20° (index → little finger) | ° | Flaccid pose targets at 5–10 % drive, or pure passive joint limits | [K] (M), [E] |
| `hand_to_throat_p` | 0.7–0.9 | p | Conscious with airway blood, obstruction or air hunger | [K] (M), [E] |
| `plucking_p` | class III–IV shock 0.2–0.4; hypoxic confusion 0.3 | p | 1–3 s picking bouts every 10–60 s | [K] (L–M), [E] |

### Visual/behavioural checklist (face and extremities)
- Syncope and seizures: eyes open and turned. Deep coma: lids nearly closed but often a sliver of white showing, eyes drifting slowly side to side. Brainstem death: lids where they were, eyes fixed, no counter-rotation when the head turns.
- The unconscious jaw hangs open when the body lies on its back; each agonal gasp opens it wide.
- Hands of the conscious dying: pressing the wound, then clawing at the collar or throat when breathing fails, then plucking at clothing as confusion sets in, then lying open and loosely curled.
- A seizure leaves a bitten, bleeding tongue edge; a dead mouth leaves a dried dark tongue tip.

---

## 8. Skin and autonomic signs in the last minutes

### 8.1 Pallor and sweating

| Sign | Onset | Where first | Magnitude | Tag |
|---|---|---|---|---|
| Pallor (vasoconstriction) | Vasovagal: 10–30 s before the faint. Haemorrhage: from ~15 % loss. Pain or fear: seconds | Lips, face, conjunctivae, nail beds | Desaturate/lighten 20–40 % (`[R1-04 §7.7]` colours) | [K] (M), `[R1-04 §7.7]` |
| **Cold sweat** | Vasovagal prodrome; haemorrhage class II–III (≈15–30 % loss); severe pain; after a seizure; hypoxia | **Forehead, upper lip, temples**, then neck, chest, palms | Beads 0.5–3 mm; spreads over 1–3 min | [K] (M), [E] |
| Sweating stops | At `t_arr`; the skin then dries and dulls over 30–60 min | — | Specular falls | [K] (M), [E] |
| Hand and forearm veins flatten | From ~15–30 % loss | Backs of hands | Veins vanish | `[R1-03 §3.6]` |

### 8.2 Cyanosis

- **Visible central cyanosis** needs enough **deoxygenated** haemoglobin. Classic threshold: ~5 g/dL in capillary blood `[K; M21] (H)`. In arterial terms, cyanosis is visible when `Hb × (1 − SaO₂)` ≥ ~2.5–3 g/dL (corrected: was ~1.5–3); game default **2.5 g/dL** `[K] (M)`, `[E]`.
- Fact-check ✓ verified (M): capillary deoxyhaemoglobin ≈ arterial deoxyhaemoglobin + half the arteriovenous difference (~1.9 g/dL for an O₂ extraction of 5 mL/dL), so 5 g/dL capillary ≈ **~3 g/dL arterial** (SaO₂ ~79–80 % at Hb 15). Observer studies (Comroe & Botelho 1947) found that some observers see cyanosis at SaO₂ ~85 % while others miss it until ~75 %. The game's 2.5 g/dL (SaO₂ 83 % at Hb 15) is inside that spread; **2.5–3.0** is the defensible band, and 1.5 g/dL is too sensitive (1.5 g/dL is the classic figure for *methaemoglobin*, not deoxyhaemoglobin). Table arithmetic re-derived ✓: 1 − 2.5/15 = 83 %, 1 − 2.5/9 = 72 %, 1 − 2.5/6 = 58 %.

  | Hb (g/dL) | SaO₂ at which lips turn visibly blue `[E]` |
  |---|---|
  | 15 (normal) | ~83 % |
  | 9 (about 35–40 % blood loss after refill) | ~72 % |
  | 6 | ~58 % |
  | < 5 | Never clearly blue: grey-white |

- **Peripheral (acro-)cyanosis**: slow flow in cold, vasoconstricted fingers, toes, nail beds and lips gives a dusky blue-grey tint even when arterial oxygen is normal. It appears in shock and cold `[K] (M)`.
- **Timelines**:

  | Situation | Lips visibly blue | Tag |
  |---|---|---|
  | Apnoea or complete obstruction, normal Hb | 60–120 s | `[R1-04 §1]` [K] (M) |
  | Tonic seizure | 10–30 s (apnoea plus high oxygen use) | [K] (M) |
  | Circulatory arrest with a full blood volume | Face and lips grey-blue/livid within ~1–3 min | [K] (M) |
  | Exsanguination | Waxy white-grey, lips grey-lilac, **not blue** | `[R1-04 §7.7]` |

### 8.3 Mottling

- A lacy, violet, net-like pattern from patchy skin perfusion. **It starts around the knees** and spreads up the thighs (and to the feet and hands) `[K; M18] (M)`.
- **Mottling score** (knee-centred) `[K; M18] (M)` — ✓ verified: the six grades below match the checker's recall of Ait-Oufella et al. 2011 `[K]` (H). The score was validated in **septic** shock; its use for haemorrhagic shock is an analogy:

  | Score | Extent |
  |---|---|
  | 0 | None |
  | 1 | Small, coin-sized area at the centre of the knee |
  | 2 | Not beyond the upper edge of the kneecap |
  | 3 | Not beyond the middle of the thigh |
  | 4 | Not beyond the groin fold |
  | 5 | Beyond the groin fold |

- **Timing**: needs sustained severe hypoperfusion. It does **not** appear in deaths under ~10 min. Game onset `[E]`: after ≥ 10–20 min at ≥ 30 % loss (or sustained MAP < 60); +1 score per 5–20 min as shock deepens. ⚠ not re-verified: no source gives a minimum shock duration for mottling; the ≥ 10–20 min rule is an engineering choice. Keep it separate from **livor mortis** (post-mortem, dependent, starts ~20–30 min after arrest), which players often confuse with mottling.
- In slow dying: mottled knees and feet hours to days before death `[K; M14] (M)`.
- **After death**: mottling fades into pallor, then livor forms in dependent areas `[R1-04 §12.3–12.4]`.
- Colour `[E]`: `#7B4A6A` lace over the pale base, 20–50 % opacity.

### 8.4 Flushing, congestion and petechiae

- **Congested, dusky-purple face**: seizure tonic phase, straining, asphyxia with venous obstruction, tamponade (neck veins bulge), traumatic asphyxia `[R1-04 §11.8]` `[K] (M)`.
- **Flushed face with a slow bounding pulse**: Cushing phase of raised ICP `[S25]` `[R1-04 §5.3]`.
- **Petechiae**: only with raised venous pressure plus hypoxia; never from bleeding out `[R1-04 §11.8]`.

### 8.5 Sphincters

| Event | Urine | Faeces | Tag |
|---|---|---|---|
| Syncope | 0.1–0.25 | < 0.02 | [K] (L) |
| GTC seizure | 0.2–0.4 | 0.02–0.05 | [K] (M) |
| Death | 0.2–0.3 (50–200 mL over 1–5 min) | 0.02–0.05 | `[R1-04 §12.1]` [K] (L) |

### Simulation parameters (skin)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `pallor_onset` | vasovagal 10–30 s before LOC; haemorrhage from 15 % loss | — | | [K] (M) |
| `sweat_onset` / `bead_size` / `spread_time` | class II–III or prodrome / 0.5–3 mm / 1–3 min | — | Forehead → lip → neck → palms | [K] (M), [E] |
| `sweat_dry_after_arrest` | 30–60 | min | | [E] |
| `cyanosis_threshold_deoxyHb_arterial` | 2.5 (2.5–3.0) | g/dL | Visible if `Hb·(1 − SaO₂)` ≥ threshold. ✓ verified; corrected: range was 1.5–3 (1.5 g/dL is the methaemoglobin figure) | [K; M21] (M), [E] |
| `acrocyanosis` | cold skin < 30 °C or class III–IV | — | Nail beds and lips dusky | [K] (M) |
| `mottling_onset` / `mottling_rate` | ≥ 10–20 min at ≥ 30 % loss / +1 score per 5–20 min | — | Score 0–5 mask around the knees | [K; M18] (M), [E] |
| `mottling_colour` | `#7B4A6A`, 20–50 % | sRGB | | [E] |
| Sphincter probabilities | table §8.5 | p | | [K] (L–M) |

### Visual/behavioural checklist (skin)
- Minutes before a collapse from bleeding: pale lips, cold sweat beading on the forehead and upper lip, grey face, flat hand veins.
- A slow bleed over tens of minutes: blotchy purple lace spreading from the knees up the thighs.
- Blue lips only when breathing fails or the airway is blocked **with blood still in the body**. A bled-out body is white.
- After the heart stops, the sweat stops and the skin loses its shine.

---

## 9. The last minutes: behaviour and the typical sequence

### 9.1 Sequence by speed of death

| Speed | Examples | Sequence the player should see | Tag |
|---|---|---|---|
| **Seconds** (< 1 min) | Brainstem, destroyed heart, throat cut through both carotids | Brainstem: instant limp drop, then nothing voluntary. Heart/throat: 5–15 s of action → grey-out, stagger → collapse with eyes up and a few jerks → (stiffening) → limp → gasps (≈45 %) → stillness. **No time for sweat, mottling, shivering or rattle** | [S22] `[R1-04 §8]` [S1] [K] |
| **Minutes** (1–10 min) | Single carotid, femoral, aorta partial | Pale and sweating within 30–120 s → anxious, fast breathing → faint if upright (convulsive) or controlled sit-down → confused → unconscious (snoring or gurgling) → gasps at PEA → stillness | `[R1-04 §7]` [K] (M) |
| **Tens of minutes** | Brachial or multiple limb wounds, partly tamponaded wounds | Full shock ladder: anxious → restless and thirsty → cold, shivering, nauseated → air hunger, sighing, yawning → confused, plucking → lethargic, lids heavy → mottled knees → unresponsive → slow irregular breaths → gasps → stillness | `[R1-03 §3.6]` [K] (M) |
| **Hours** | Raised ICP, slow tamponade, tension pneumothorax, head trauma in coma | Coma with posturing spasms, Cushing phase, breathing patterns changing by level; death rattle; mandibular breathing; mottling; pupils fixed; apnoea → hypoxic arrest | [S25] [S26] [S27] `[R1-04 §5]` [K; M13, M14] |

### 9.2 Behaviour markers in the conscious dying (haemorrhage and hypoxia)

| Marker | When | Look | Tag |
|---|---|---|---|
| Restlessness, attempts to get up | Class II–III; hypoxia | Tries to stand or roll every 10–60 s; pushes helpers away; pulls at clothes or bandages | [K] (M), [E] |
| Air hunger | Class III; lung, airway or tension | RR 30–40, mouth open, nostrils flare, neck muscles working, sits or leans forward (tripod), "I can't breathe" | `[R1-04 §9]` [K] (H) |
| Thirst, cold, nausea | Class II–III | "Water", "I'm cold", retching | `[R1-03 §3.6]` [K] (H) |
| Sense of impending doom | Class III; tamponade; massive bleeding | "I'm going to die", panic, calling for family or help | [K] (M) |
| Combative agitation | Hypoxia, head injury | Lashes out, cannot be calmed | [K] (M) |
| Speech degradation | Class III → IV | Sentences → phrases → single words → moans → silence (GCS V5 → V1) | `[R2-01 §5.2]` [K] (M) |
| Yawning, sighing | Presyncope, class II–III | §2.8 | [K] (M) |
| Crawling toward an exit or cover | Legs weak but arms work | Drags itself, leaving a blood trail; stops and rests every few metres | `[R2-02 §3]` [K] (M) |

### 9.3 The final 60 s and the moment of death

- **Before `t_arr` (slow death)**: pulse fast and thready, or slowing; breaths slower, shallower and irregular; lids half-closed; eyes drifting then still; jaw slack; perhaps a last moan `[K] (M)`.
- **At `t_arr`** (invisible except through its effects) `[K] (H)`:
  - arterial jets stop pulsing at the last beat `[R1-04 §7.6]`;
  - breathing may continue for a few breaths, then turns into gasping or stops;
  - a full-blooded face darkens to livid grey-blue over 1–3 min; an exsanguinated face stays white;
  - pupils start to widen at 30–45 s.
- **"The last breath"** is usually a gasp or a passive sigh. It can be followed by one or two more after a long pause (§2.2) `[K] (M)`.
- **Stillness**: after the last gasp there is no more movement except faint twitches (§5.5), gravity settling and fluid leakage.

### Simulation parameters (last minutes)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `restless_attempt_interval` | 10–60 | s | Class II–III, hypoxia | [E] on [K] |
| `air_hunger_rr` | 30–40 | /min | | [K] (H) |
| `speech_ladder` | V5 → V4 at 30 % loss → V3 at 35–40 % → V2 at 40–45 % → V1 at LOC | GCS V | Class-driven | [K] (M), [E] |
| `doom_line_p` | 0.3–0.5 | p | Conscious, class III, or tamponade | [E] |
| `crawl_rest_interval` | 2–5 m, rest 5–20 s | — | | [E] |

### Visual/behavioural checklist (last minutes)
- Fast deaths skip straight from action to collapse: no sweat, no mottling, no rattle.
- Slow deaths show a clear ladder: restless and talking → cold, shaking, sick → breathless and confused → quiet, drowsy, eyes half-shut → unconscious → a few irregular breaths → gasps → stillness.
- The moment of death is not a dramatic exhale. The jets stop, the gasps start or stop, the colour changes, the pupils widen.

---

## 10. Timelines from injury to death

All times are real (`t_real`), from `t_inj`. Game compression per §0.3. P values are defaults for the game; sources and ranges are in the earlier sections.

### 10.1 Brainstem shot

Variants: **(a) medulla / cervicomedullary junction destroyed** (default); (b) pons destroyed, medulla spared; (c) midbrain destroyed. Base physiology in `[R1-04 §2]`.

| t_real | Consciousness / behaviour | Breathing / airway | Involuntary movement | Eyes / lids / pupils | Skin | Sound | Tag |
|---|---|---|---|---|---|---|---|
| 0–0.1 s | Gone; tone lost ≤ 100 ms | (a) apnoea at once; (b) abnormal; (c) continues | (c) tonic extension p 0.3–0.6 | Lids stay where they were; no blink ever again | — | Impact | `[R1-04 §2.2–2.3]` |
| 0.1–1.2 s | Collapse (archetype A, or B if tonic); no protective arms; held object drops in 0.1–0.5 s | Air pushed out on impact | — | Lids drop 2–4 mm over 1–3 s | — | Thud; passive exhalation | `[R2-02 §5]` |
| 1–60 s | Coma | (a) **no chest movement at all**; (b) apneustic or cluster breaths; (c) fast deep breathing possible | Small twitches p 0.2–0.3; (c) extension 5–30 s then leg-kicking bursts p 0.1–0.2 | (a) pupils normal at first; (b) **pinpoint 1–2 mm**, ocular bobbing; (c) **mid-position 4–6 mm fixed**; eyes slightly divergent/skewed | Normal colour; catecholamine surge p 0.5 (HR 120–160) | Silence (a); odd breaths (b, c) | `[R1-04 §2]` [E] |
| 1–2 min | Coma | (a) apnoea | — | Pupils (a) begin to dilate | **Lips and face turn dusky blue** (Hb normal) from 60–120 s | Silence; blood may drain from nose or mouth passively | `[R1-04 §2.4]` [K] |
| 2–8 min | Coma | (b) terminal gasps p 0.3–0.5 as the medulla becomes hypoxic; (a) none | **Spinal reflex movements p 0.2–0.4** (toe waves, finger flexion); **Lazarus arm-raise p 0.03–0.05**; respiratory-like shoulder heaves without air | Pupils widening to 6–8 | Deep cyanosis; HR slows < 40–50 from 3–5 min | Silence (a) | §5.4 [K; M11] |
| 4–10 min (default 6) | — | — | Movements stop within 1–3 min of arrest | Fixed, dilated | Jets stop pulsing; livid face | — | `[R1-04 §2.4]` |
| `t_arr` + 1–15 min | Dead flag at `t_arr` + 5 min | — | Faint twitches p 0.2–0.4, decaying | Gloss fading | Pallor mortis begins | — | §5.5 |

### 10.2 Heart shot (ventricles destroyed; no brainstem injury)

| t_real | Consciousness / behaviour | Breathing / airway | Involuntary movement | Eyes | Skin | Sound | Tag |
|---|---|---|---|---|---|---|---|
| 0–0.3 s | Startle, flinch (damped by arousal) | Sharp inhalation | — | Blink | — | Grunt, "huh" | `[R2-02 §1]` |
| 0–5 s | **Full voluntary action** possible: run, fight, shout | Fast | — | Wide, fixed on the threat | Normal | Speech possible | [S22] `[R2-02 §2.5]` |
| 5–10 s | Grey-out, tunnel vision, legs weaken; stagger, reach for support; may sit or kneel. **Purposeful action (running, shooting, stabbing back) can continue through this phase until LOC** (fact-check note: FBI 1989 gives up to 10–15 s of "full and complete voluntary action" ✓ verified; the grey-out degrades accuracy and balance, it does not switch action off) | Gasping for air | — | Unfocused, blank | Pallor | Speech slurs or stops | [K] (M), [S22] |
| 8–15 s | **LOC**; crumple (A) or stiff topple | Breathing continues briefly | **Myoclonic jerks p 0.8** (1–10 over 5–15 s), lip smacking, head turning | **Open, up 10–30° for 2–10 s** (p 0.6–0.9) | Pale | Moan p 0.2–0.4 | [S1] [S2] |
| 15–30 s | Coma | Irregular, then stops or turns to gasps | **Anoxic tonic spasm p 0.15–0.3**: arms straight, back arched, 5–20 s; incontinence p 0.1–0.2 | Drift back to the midline; lids droop to half-open | Pale-grey | Snore | §3.2 |
| 20–60 s | — | **First gasp** (p 0.45) | Gasp-associated jerks p 0.2–0.4 | Pupils begin to dilate (30–45 s) | Face greying; blood froth at the mouth if the track crossed a lung (p 0.3–0.5) | Snort, gurgle | §2.2 |
| 1–4 min | — | Gasps every 10–30 s, weakening | Fine twitches | Wide and fixed by 1–2 min | Grey; lips dusky (blood is lost into the chest but not out of the body; not as white as an external bleed-out) | Gasps, then a final sigh | §2.2 [E] |
| 3–5 min | — | Last gasp; "false last breath" p 0.3 | — | Glossy, unmoving | — | Silence | §2.2 |
| 5 min | Dead flag | — | Faint twitches to ~15 min (p 0.2–0.4) | Gloss fading | Pallor mortis | — | §5.5 |

Variant, **stab wound to the heart with tamponade**: 4 of 7 witnessed cardiac stab suicides stayed active for 2–10 min, 2 of 7 for about 10 s, 1 of 7 was incapacitated immediately `[S23]`. Use the slow-bleed ladder (§10.4) compressed into minutes, with bulging neck veins and a grey, sweating, breathless victim `[R1-04 §8.3]`.

### 10.3 Carotid bleed (one common carotid completely transected; standing, conscious)

Flow 0.5–1.5 L/min (default 1.0 L/min) without compression `[R1-04 §7.5]`. Own-hand compression reduces flow ×0.4–0.7 while conscious `[E]`.

| t_real | Consciousness / behaviour | Breathing / airway | Involuntary movement | Eyes | Skin | Sound / blood | Tag |
|---|---|---|---|---|---|---|---|
| 0–1 s | Startle | Gasp | — | Blink, then wide | — | **Pulsing bright jet 0.5–1.5 m** | `[R1-04 §7.6]` |
| 0.3–0.8 s | **Both hands clamp the neck**; blood between the fingers | — | — | Fear: lids 11–12 mm | — | — | `[R2-02 §3]` |
| 1–30 s | Panic; flees or fights; may call out. If the larynx or trachea is cut: coughing, spraying blood, hoarse or no voice | Fast; if airway cut: **gurgling, bubbling at the wound**, aspiration (36.5 % of cut-throat deaths die of aspiration) | Fear tremor | Scanning | — | Airway intact: a shout or scream is possible but not the rule (p 0.3–0.5 `[E]`); silence, gasping and "help" are common. **Airway cut below the vocal cords: no scream at all**, only hissing, wet gurgling and bubbling at the wound (corrected: was "Screams, gurgling") | [S19] [K] `[R2-02 §14]` |
| 5–30 s | If collaterals are poor (p 0.2–0.3): **weakness of the opposite arm and leg, face droop, aphasia (left carotid), eyes toward the cut side**; falls toward the weak side | — | — | Conjugate deviation toward the lesion | — | Slurred | [K] (L), `[R2-01 §2]` |
| 30–90 s (10–20 % loss) | Anxious, dizzy | 20–30/min | — | Blinking more | **Pale, sweat on forehead and lip** | Jet shorter and faster | `[R1-04 §7.2]` |
| 60–120 s (20–30 %, upright) | **Faint if still standing** (convulsive: eyes up, a few jerks), or controlled descent to knees and sitting | — | Myoclonus p 0.8 if fainting | Up, then half-open | Grey | Hands fall from the neck at LOC: flow rises again | §3.1 |
| 2.5–4 min (40–50 %) | **Unconscious** (if not already) | Snoring; gurgling if the airway is involved | — | Half-open, roving then still | Waxy grey-white, lips grey-lilac | Jet becomes a welling pulse | `[R1-04 §7.4]` |
| 3.5–7 min (50–55 %) | **PEA** | Gasps p 0.4, 1–4 min | Twitches | Pupils wide by 1–2 min after arrest | White | Welling stops pulsing; gravity drainage | `[R1-04 §7]` |
| `t_arr` + 5 min | Dead flag | — | — | — | Minimal livor later | — | `[R1-04 §12.4]` |

Variant, **throat cut through both carotids and jugulars**: LOC 5–20 s, arrest 1–3 min `[R1-03 §5]`; neck-vein air entry (hissing, frothy dark blood) in a minority `[R1-02 §2]` `[S19]`.

### 10.4 Slow bleed from a limb (e.g. partial brachial artery, or several limb wounds)

Default: 200 mL/min initially, falling in proportion to MAP, with partial clotting. `[R1-04 §7.5]` brackets: 300 mL/min → LOC 8–15 min, PEA 10–25 min; 100 mL/min → LOC 25–50 min, PEA 35–80 min. Default below: **LOC ~20 min, PEA ~28 min** `[E]`. P(bleeding stops on its own and the character survives) 0.1–0.3 for radial, ulnar or partial brachial wounds `[R1-04 §7.5]` `[E]`.

| t_real | Loss | Consciousness / behaviour | Breathing | Involuntary / autonomic | Eyes | Skin | Sound | Tag |
|---|---|---|---|---|---|---|---|---|
| 0–1 min | < 5 % | Pain, flinch, wound check, presses the wound | Fast from fear | Fear tremor | Wide | — | Pulsing jet 0.3–0.8 m | `[R2-02 §2.4]` |
| 1–5 min | 5–15 % | Anxious, calls for help, holds the limb up or presses | 20/min | Tremor | Normal | Pale lips | Talking | `[R1-04 §7.2]` |
| 5–10 min | 15–30 % | **Restless, thirsty**; tries to stand, gets dizzy, sits back; nausea (vomit p 0.1–0.2); yawning, sighing | 20–30/min | **Cold sweat**; **shivering may start** | Blinking more | Pale, cold hands, flat veins | "I'm cold", "water" | `[R1-03 §3.6]` §6.2 |
| ~8 min | ~25 % | If upright: **faint** (p 0.3–0.5): convulsive syncope, recovers in 10–30 s lying down; paradoxical bradycardia faint p 0.1–0.3 | — | Jerks p 0.8 | Up during LOC | Grey | — | §3.1 `[R1-04 §7.3]` |
| 10–18 min | 30–40 % | **Confused, agitated or oddly quiet**; repetitive speech; **plucking at clothes**; cannot sit up | **30–40/min, air hunger, sighing** | Shivering and teeth chattering p 0.3–0.5 (BSAS 1–3) | **Sunken, dull**; pupils normal to large, sluggish | **Grey, clammy; mottled knees from ~15 min** (score 1–2) | Weak, slurred | `[R1-04 §7.2]` §8.3 |
| 18–22 min | 40–45 % | **Lethargic**, eyes closing and struggling open; responds only to pain (moan, withdrawal) | Shallow, fast, then slowing | Shivering fades | Lids 2–6 mm, roving | Waxy grey-white; lips grey-lilac; radial pulse gone | Moans | §7.1 |
| ~20 min | ~45 % | **LOC** | Snoring (supine) | Brief jerks p 0.5 (slow-onset LOC) | Half-open | Mottling score 2–3 | Snore | §3.1 [E] |
| 20–28 min | 45–55 % | Coma | Slow (6–10/min), shallow, irregular, sighs | — | Pupils dilating | Mottling fading into pallor | Irregular breaths | [K] (M) |
| ~28 min | ~55 % | **PEA** | **Gasps p 0.4**, 1–5 min | Gasp jerks | Wide, fixed | **White** | Gasps, final sigh | §2.2 |
| ~33 min | — | Dead flag | — | Faint twitches to ~45 min | Gloss fading | Faint, late livor | — | §5.5 |

Game time: 4× until ~5 min before PEA; 1× from 60 s before `t_arr` to 60 s after; then post-mortem scale. Total ≈ 8–10 min of play `[E]`.

### 10.5 Massive head trauma without brainstem damage

Default: **bihemispheric penetrating wound** (for example temple to temple above the tentorium) or **severe blunt injury** with contusions and an acute subdural haematoma. The brainstem is initially intact. Overall mortality of bihemispheric gunshot wounds is high (~80–90 %), much of it before hospital `[S33]` `[R1-04 §3.2]`.

**Outcome branches** `[E]` on `[S33]` `[K]`:

| Branch | P | Mechanism | Death |
|---|---|---|---|
| A. Early hypoxic death | 0.35–0.45 | Impact apnoea > 4–6 min and/or airway flooding with blood or vomit | Arrest at 5–15 min |
| B. Herniation death | 0.35–0.45 | Rising ICP → brainstem compression → apnoea | 30 min – 6 h (default 90 min) |
| C. Survives the game horizon in coma | 0.1–0.2 | Swelling stabilises | — |

| t_real | Consciousness / behaviour | Breathing / airway | Involuntary movement | Eyes / pupils | Skin / autonomic | Sound / fluids | Tag |
|---|---|---|---|---|---|---|---|
| 0 s | **Immediate LOC** (p ≥ 0.9 bihemispheric); collapse | **Impact apnoea** p 0.6 (30 s – 5 min) | **Immediate tonic posturing** (decorticate/decerebrate) p 0.3–0.5 for 5–60 s; impact seizure p 0.05–0.1 | Open or half; may be unequal | **Catecholamine surge**: HR 120–160, SBP 160–200 for 10–60 s | Wound bleeding; blood from nose/ears if the skull base is fractured | `[R1-04 §3.5]` [K; M30] |
| 1–5 min | Coma (GCS 3–6) | Breathing resumes (if apnoea ends): **stertorous, irregular, 8–30/min**; **gurgling** from blood in the nasopharynx; weak or absent cough | **Posturing spasms when moved or hurt** p 0.4–0.6 (5–60 s each) | Roving or midline; doll's eyes present; pupils reactive | Sweating | Snoring, gurgling, bubbling at the nostrils; moans with spasms | §2.1 §5.6 |
| 5–30 min | Coma | **Vomiting or regurgitation** p 0.2–0.35 → aspiration (supine p 0.5–0.8) → gurgle, cyanosis | Subtle status twitches p 0.05–0.1 | One pupil may start to enlarge (uncal) | Lips blue if aspiration or apnoea | Vomit at mouth and nose | §2.7 §4.5 |
| 15 min – 4 h | Coma deepening | **Pink-white froth at the nostrils (NPE)** p 0.2–0.3 | Posturing progresses decorticate → decerebrate | **Blown pupil 6–9 mm on the side of the mass**, then both | **Cushing phase** (p ~0.33 full triad): SBP 160–220, HR 40–60, flushed | Froth reforming | §2.6 [S25] `[R1-04 §5]` |
| Late (branch B) | — | Cheyne–Stokes → fast deep breathing → **ataxic** → **apnoea** (tonsillar: sudden) | **Posturing stops (flaccid)** | Both pupils fixed mid-to-wide; eyes fixed | BP falls after the apnoea | Death rattle if unconscious > 1–2 h (p 0.3–0.5) | [S27] `[R2-01 §15]` |
| Apnoea + 0–8 min | Brainstem dead, heart beating | None; no gasps (the medulla failed first; p of terminal gasps ≤ 0.1) | **Spinal reflexes p 0.2–0.4; Lazarus p 0.03–0.05** | Doll's eyes absent | Deepening cyanosis; HR slows | Silence | §5.4 |
| 4–10 min after apnoea | **Hypoxic arrest** | — | Stop within 1–3 min | Fixed | Livid | — | `[R1-04 §2.4]` |
| `t_arr` + 5 min | Dead flag | — | Faint twitches (p 0.2–0.4) | — | — | Froth and blood leak when moved | §5.5 |

Game time: 1× for the first 60 s; 4× to 30 min; 10–15× in the hours phase; 1× around `t_arr`.

### 10.6 Comparison summary (defaults)

| Scenario | LOC (real) | `t_arr` (real) | Gasps P | Anoxic myoclonus P | Tonic spasm / posturing P | Spinal reflex P | Post-mortem twitch P | Vomit P | Froth P | Death rattle P | Eyes at death (open / half / closed) | Game length to dead flag |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Brainstem (medulla) | 0 s | 4–10 min (6) | 0 | 0 | 0 (midbrain: 0.3–0.6) | 0.2–0.4 | 0.2–0.4 | 0 | 0 | 0 | 0.55 / 0.35 / 0.10 | ~3 min |
| Heart destroyed | 8–15 s | 0 s | 0.45 | 0.8 | 0.15–0.3 | 0 | 0.2–0.4 | < 0.05 | 0.3–0.5 (lung crossed) | 0 | 0.55 / 0.35 / 0.10 | ~2 min |
| Carotid (one) | 2.5–4 min (faint earlier if upright) | 3.5–7 min | 0.4 | 0.8 (at the faint) | 0.1 | 0 | 0.2–0.4 | 0.05–0.1 | 0.2 if airway cut | 0 | 0.40 / 0.40 / 0.20 | ~3 min |
| Slow limb bleed | ~20 min (13–35) | ~28 min (18–60) | 0.4 | 0.5 | < 0.05 | 0 | 0.2–0.4 | 0.1–0.2 | 0 | 0 (< 30 min unconscious) | 0.20 / 0.45 / 0.35 | ~8–10 min |
| Massive head trauma, brainstem spared | 0 s | Branch A: 5–15 min; B: 0.5–6 h | A: 0.3–0.5; B: ≤ 0.1 | 0 | 0.3–0.5 early; progressive | B: 0.2–0.4 | 0.2–0.4 | 0.2–0.35 | NPE 0.2–0.3 | B: 0.3–0.5 if > 1–2 h | 0.30 / 0.45 / 0.25 | A: ~4 min; B: 8–15 min |

Eye distributions from `[R1-04 §11.3]` (game-design values `[E]`), with the carotid row interpolated.

### Simulation parameters (timelines)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `scenario_defaults` | table §10.6 | — | Starting values; the physiology model produces the actual times | [E] |
| `carotid_self_compression` | ×0.4–0.7 flow while conscious and both hands on the neck | × | Released at LOC | [E] |
| `carotid_hemispheric_deficit_p` | 0.2–0.3; onset 5–30 s | p / s | Poor collaterals | [K] (L), [E] |
| `carotid_scream_p` | airway intact 0.3–0.5; airway cut below the vocal cords 0 | p | Fact-check addition; silence, gasping and short calls for help are common | [E] on [K] |
| `slow_bleed_self_stop_p` | 0.1–0.3 | p | Radial, ulnar, partial brachial | `[R1-04 §7.5]` [E] |
| `head_branch_p` | A 0.35–0.45 / B 0.35–0.45 / C 0.1–0.2 | p | Bihemispheric or severe blunt | [E] on [S33] |
| `head_herniation_death` | 30 min – 6 h (default 90 min) | — | Branch B | [K] (L–M), [E] |

### Visual/behavioural checklist (timelines)
- Brainstem: an instant limp drop, then a silent, motionless body whose lips turn blue over a minute or two, perhaps a slow curl of the toes or a rare slow arm rise, then nothing.
- Heart: seconds of action, a stagger, a collapse with eyes turned up **for a few seconds only** and a few jerks, sometimes a brief rigid arch, then snorting gasps for a few minutes. By the time the body is dead the eyes are back near straight ahead, half-open and fixed.
- Carotid: a tall pulsing jet clamped by both hands, panic, pallor and sweat within a minute, a faint or a slide to the ground, snoring or gurgling unconsciousness, gasps, a white body.
- Slow limb bleed: the full ladder over tens of minutes, including shivering, confusion, plucking at clothes and mottled knees.
- Massive head trauma: instant coma with stiffening spasms, snoring and gurgling, blood from the nose, vomiting, sometimes pink froth, then over an hour or more a blown pupil, a slow pounding pulse, changing breathing, and finally silence.

---

## 11. Implementation: the dying behaviour layer in Godot 4.5 / Jolt

### 11.1 States

`[E]` design, driven by the physiology state of `[R1-04 §13]`:

| Layer state | Entered when | Main generators active |
|---|---|---|
| `CONSCIOUS_DISTRESS` | Conscious and injured | Fear tremor, shivering, sweating, cough/spit, vomiting, restlessness, speech ladder |
| `PRESYNCOPE` | Brain O₂ reserve draining, or vasovagal roll | Pallor, yawning, sweat, greying, controlled descent |
| `TRANSIENT_LOC` | Reserve exhausted (syncope) | Anoxic jerks, upgaze, automatisms, snoring |
| `SEIZURE` / `POSTICTAL` | Seizure roll with `gate_seizure` | §4 schedule |
| `COMA_BREATHING` | Unconscious with breathing | Airway sound by posture, gurgle, rattle timer, posturing on stimulus, subtle twitches, roving eyes, vomit/regurgitation |
| `BRAINSTEM_DEAD_HEART_BEATING` | Medulla/pons destroyed or herniated | Spinal reflex window, cyanosis, no breathing (or pontine patterns) |
| `AGONAL` | `t_arr` reached | Gasp schedule, anoxic spasm, gasp jerks, pupils, colour change |
| `DEAD_SUPRAVITAL` | `t_arr` + 300 s, up to ~2 h | Fasciculation decay, gravity settling, passive fluids, idiomuscular response on strike |
| `DEAD` | Later | Post-mortem system `[R1-04 §12]` |

### 11.2 Scheduling events

- Use **Poisson** scheduling for irregular events (anoxic jerks, twitches, spits, coughs): the next event comes after `−ln(u) / rate` seconds `[E]`.
- Use **explicit schedules** for structured sequences (gasps §2.2, clonic frequency §4.1, Lazarus §5.4, shivering bursts §6.2).
- Roll every probability **once on state entry**. Store the outcome so that reloading or re-evaluating does not re-roll.
- Illustrative pseudocode (written for this document):

```
# on entering AGONAL
if gate_gasp and rng.randf() < gasp_p:
    var t = gasp_first            # s after t_arr
    var dt = gasp_interval0
    var amp = 1.0
    for i in gasp_count:
        schedule(t, "gasp", amp)
        t += dt; dt *= gasp_interval_growth; amp *= 0.85
        if t > gasp_phase_max: break
    if rng.randf() < false_last_breath_p:
        schedule(t + rng.randf_range(30, 120), "gasp", amp)
```

### 11.3 Mapping events to the body

**Jerks and kicks (physics).** Drive them through the joint drives (brief target offset of 10–30° for 80–200 ms at high stiffness) or through short off-centre impulses on the `PhysicalBone3D` (an angular impulse `J` is approximated by a linear impulse `J / r` applied at distance `r` from the joint). Check the exact Godot 4.5 API (`PhysicalBoneSimulator3D`, `PhysicalBone3D` joint and impulse methods) against the engine documentation before implementing.

Approximate moments of inertia about the proximal joint (75 kg body, de Leva segment data, `I = m (r_g² + d²) L²`) `[E]`:

| Segment (about) | Mass (kg) | I (kg·m²) | Target peak ω for a myoclonic jerk (rad/s) | Angular impulse J = I·ω (N·m·s) |
|---|---|---|---|---|
| Hand (wrist) | 0.46 | 0.0035 | 3–8 | 0.01–0.03 |
| Forearm + hand (elbow) | 1.68 | ~0.08 | 2–5 | 0.16–0.4 |
| Whole arm, extended (shoulder) | 3.71 | ~0.45 | 1–3 | 0.45–1.35 |
| Shank + foot (knee) | 4.28 | ~0.40 | 1–3 | 0.4–1.2 |
| Thigh alone (hip) | 10.6 | ~0.52 | 0.5–2 | 0.26–1.04 |
| Whole leg, extended (hip) | 14.9 | ~2.6 | 0.5–2 | 1.3–5.2 |
| Head (atlanto-occipital to C7 range) | 5.2 | 0.03–0.10 | 1–4 | 0.03–0.4 |

Arithmetic `[E]`: de Leva lengths (upper arm 0.282 m, forearm 0.269 m, hand 0.086 m, thigh 0.422 m, shank 0.434 m), centre-of-mass fractions and sagittal radii of gyration; distal segments added with the parallel-axis theorem. Values are for straight limbs; a flexed limb has a smaller moment about the proximal joint.

- Peak angular velocities of 1–8 rad/s (60–460°/s) are the `[E]` range for visible involuntary jerks. **Real myoclonic jerks are fast but small**: aim for 5–30° excursions.
- Clonic seizure jerks: synchronous bilateral offsets at the §4.1 frequency.
- Tonic phases and posturing: joint targets from `[R2-01 §18.2]` with ramp, hold and release.
- The Lazarus sequence: a slow target change (§5.4), never an impulse.

**Tremor, shivering, chattering, clonic vibration (visual only).** Oscillations at 5–12 Hz are poorly sampled by a 60 Hz physics tick and are too small to matter physically. Apply them as **additive bone-rotation offsets after the physics step** (0.2–2° amplitude, band-limited noise at the target frequency, burst envelopes as in §6.2) `[E]`.

**Fasciculations (shader).** A per-character array of up to 4 active "twitch spots" (position on the mesh, radius 10–30 mm, normal displacement 0.3–1.5 mm, rise 20–40 ms, decay 60–150 ms) evaluated in the vertex shader or as a normal-map perturbation `[E]`.

**Gasps and breathing.** An additive pose on chest/abdomen blendshapes (or spine bones), neck extension, jaw opening and nostril flare, with amplitudes from §2.2. When the ragdoll is fully limp, apply the neck and jaw parts as low-strength motor targets (20–40 %) so gravity still wins between gasps `[E]`.

**Fluids.** Froth, vomit and airway blood are emitters at the mouth and nostril sockets. Their rate is taken from the airway fluid volume and the breath or cough events. Direction: along the face normal, plus gravity; pools form on the dependent side `[E]`.

**Eyes, lids, jaw.** Use the targets in §7. Lid and jaw tone go to zero at death, and gravity sets the jaw.

**Audio.** One-shot and loop samples triggered by events: gasp variants, snore loop (rate-synced), gurgle layer (gain ∝ airway fluid), cough, spit, retch, vomit, hiccup, sigh, yawn, epileptic cry, clonic grunts, chattering click train, rattle loop, post-mortem groan on chest compression.

### 11.4 Performance budget

- Event generators: a few dozen floats and one small event queue per character, ticked at 20 Hz (5 Hz when dead). Well under 0.05 ms per character in GDScript `[E]`.
- Physics: no extra bodies. Jerks reuse the existing ragdoll.
- Visual-only oscillations are a handful of bone offsets per frame.
- Fasciculation spots: 4 × vec4 uniforms.
- The real costs remain particles (blood, froth, vomit) and decals; cap emitters per character and pool particles `[E]`.

### Simulation parameters (implementation)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `jerk_target_offset` / `jerk_duration` | 10–30 / 80–200 | ° / ms | Joint-drive method | [E] |
| `jerk_peak_omega` | 1–8 | rad/s | Per segment (table §11.3) | [E] |
| `visual_osc_amp` | 0.2–2 | ° | Tremor, shiver, vibratory phase | [E] |
| `fasc_spot` | radius 10–30 mm; depth 0.3–1.5 mm; rise 20–40 ms; decay 60–150 ms; max 4 active | — | Vertex/normal shader | [E] |
| `gasp_neck_jaw_drive` | 20–40 % | × max | Gravity wins between gasps | [E] |
| `layer_cpu_budget` | < 0.05 | ms per character per tick | GDScript | [E] |

### Visual/behavioural checklist (implementation)
- Jerks look fast but small; nothing flails across the room.
- Tremor and shivering never make the ragdoll jitter or slide; they are visual only.
- Every probability is rolled once per episode, so a replay of the same death looks the same.

---

## 12. Common realism mistakes (with the fix)

| # | Mistake | Reality | Fix | Source |
|---|---|---|---|---|
| 1 | The body lies perfectly still after it falls | Jerks at collapse (≈90 % of anoxic faints), gasps after arrest (≈40 %), twitches | §3, §2.2, §5.5 | [S1] [K; M1, M2] |
| 2 | Gasps after a medullary (brainstem) shot | The gasp generator is in the medulla | `gate_gasp` | [K] (H) |
| 3 | Gasping shown as the character recovering | Gasps are a dying reflex, mostly with no pulse | §2.2 | [K] (H) |
| 4 | Death happens on a single dramatic exhale | The heart stops first (or the brain), gasps continue for minutes, and "false last breaths" occur | §2.2, §9.3 | [K] (M) |
| 5 | A faint is a still, limp body with closed eyes | Eyes open and turned up, a few irregular jerks, automatisms, awake in ~12 s | §3.1 | [S1] [S2] |
| 6 | Seizures are random flailing | Stiff first (cry, arched, blue), then rhythmic jerks that slow down over ~1 min, then snoring stupor | §4.1 | [S3] [S4] |
| 7 | Death rattle in every death | Only after hours of unconsciousness | §2.4 | [K; M15] |
| 8 | Foam at the mouth in every death | Only lung/airway injury, seizures, neurogenic pulmonary oedema, drowning | §2.5–2.6 | [K] (H) |
| 9 | Corpses twitch strongly or sit up | Only faint twitches in the first ~15 min; large movements (Lazarus) need a beating heart and a dead brain, and are rare | §5.4–5.5 | [S11] [K; M11] |
| 10 | Shivering or trembling in an unconscious dying body | Shivering fades with obtundation and deep shock; tremor needs consciousness | §6 | [K] (M) |
| 11 | Posturing held continuously | Episodic, stimulus-triggered, 5–60 s | §5.6 | [S10] |
| 12 | Everyone vomits | P 0.07–0.35 depending on the injury | §2.7 | [S15] [K] |
| 13 | A bled-out body turns blue | Too little haemoglobin: white-grey | §8.2 | [K; M21] |
| 14 | Mottled skin in a 1-minute death | Mottling needs ≥ 10–20 min of shock | §8.3 | [K; M18] |
| 15 | Unconscious bodies breathe silently on their backs | Snoring in most; gurgling with fluid; lateral position quiets it | §2.1 | [K] (M) |
| 16 | The eyes "roll back" at the moment of death (fact-check addition) | Upward deviation belongs to the **moment of collapse** (syncope, anoxic LOC, knockout, seizure) and lasts seconds. At death and after it the eyes rest near straight ahead or slightly divergent, lids open or half-open, pupils wide and fixed | Blend upgaze back to neutral within 10–60 s of LOC; never keep it into `DEAD` | [S1] [S2] `[R1-04 §11]` `[R2-02 §5.6]` |
| 17 | The bullet throws the body backwards or off its feet (fact-check addition) | A handgun bullet gives a 75 kg body ~0.04 m/s; even buckshot < 0.2 m/s. The shooter feels the same momentum as recoil. Falls come from the victim's own muscles failing or reacting, and their direction follows posture and motion (§3.1 falls; `[R2-02 §5]`) | Small segment impulses only; the fall is driven by the tone model | `[R2-02 §1.3]` [K] (H) |
| 18 | "Hydrostatic shock" drops anyone hit in the torso (fact-check addition) | No reliable instant incapacitation from a pressure wave at handgun velocities (FBI 1987–1989 wound-ballistics position). Remote neural effects from high-velocity rifle hits are reported in animal work and remain contested; they are never a dependable off-switch. An instant drop needs a brain, brainstem or upper-cord hit, loss of skeletal support (pelvis, femur, spine), or a psychological or vasovagal collapse | Instant collapse only through those routes; otherwise use the physiological clock | [S22] `[R2-02 §14]` [K] (M–H) |
| 19 | Everyone screams when shot or cut (fact-check addition) | Silence, a grunt, "I'm hit", or gasping are common; screams follow fractures, burns, and seeing the wound. A cut airway below the cords makes any voice impossible | Vocalisation by the pain/voice model; gate by airway state | `[R2-02 §9, §14]` [K] (M) |
| 20 | A dying body thrashes violently for a long time ("death throes") (fact-check addition) | Circulatory collapse gives **a handful of small, irregular jerks for ~5–15 s** and sometimes a brief stiffening; big rhythmic convulsions lasting about a minute are a seizure (needs a perfused cortex) or a hanging-type ischaemia with a beating heart | §3, §4 | [S1] [S3] [K; M10] |
| 21 | Shooting a corpse makes it jerk or convulse (fact-check addition) | Only passive momentum and gravity, plus an occasional small local muscle bulge in the first ~2 h | §5.5 | [K] (M) |

### Simulation parameters (mistake guards)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `assert_no_gasp_if_medulla_dead` | true | bool | Debug assertion on the event queue | [K] (H) |
| `assert_no_rattle_before` | 30 | min unconscious | | [K; M15] (M) |
| `assert_no_mottling_before` | 10 | min of shock | | [K; M18] (M) |
| `assert_no_cyanosis_if_hb_below` | 5 | g/dL | Tint grey-white instead | [K; M21] (M) |
| `assert_no_spontaneous_motion_after` | `t_arr` + 20 min | — | Except gravity, fluids, provoked supravital responses | [K] (M), [E] |
| `assert_no_upgaze_in_dead` | true | bool | Fact-check addition: upward gaze must have blended back to neutral/slight divergence before `DEAD_SUPRAVITAL` | [S2] [K] (H) |
| `assert_no_instant_drop_without_cns_or_support_loss` | true | bool | Fact-check addition: "hydrostatic shock" guard. Psychological or vasovagal collapse is allowed through its own path and latency `[R2-02]` | [S22] [K] (M–H) |

### Visual/behavioural checklist (mistake guards)
- QA pass: watch each of the five §10 deaths at 1× around `t_arr` and tick off every row of the table above.
- (Fact-check additions) No body is thrown backwards by a bullet; a torso hit never switches a character off instantly unless the brain, brainstem, upper cord or skeletal support is hit (or the character faints); the eyes are turned up only for seconds at the collapse, never in the dead; a character with a cut windpipe makes no scream; shooting a corpse moves it only mechanically.

---

## 13. Probability summary (for tuning)

| Event | Default P | Condition |
|---|---|---|
| Agonal gasps | 0.45 / 0.4 / 0.7 / 0 | VF or destroyed heart / exsanguination to PEA / asphyxia with a beating heart / medulla destroyed |
| Anoxic myoclonus at LOC | 0.8 (sudden) / 0.5 (slow onset) | Circulatory LOC |
| Upgaze at LOC | 0.6–0.9 | Circulatory LOC |
| Anoxic tonic spasm | 0.15–0.3 | Circulatory arrest ≥ 15 s |
| Epileptic cry / tongue bite / froth / incontinence | 0.3–0.5 / 0.2–0.35 / 0.2–0.4 / 0.2–0.4 | GTC |
| Tonic release extension / leg kicking | 0.3–0.6 / 0.1–0.2 | Midbrain/upper pons destroyed |
| Spinal reflex movement / Lazarus | 0.2–0.4 / 0.03–0.05 | Brainstem dead, heart beating |
| Post-mortem fine twitches | 0.2–0.4 | First 15–20 min after `t_arr` |
| Vomiting | 0.07 / 0.28 / 0.2–0.35 / 0.2–0.4 | Head injury seen in hospital, mostly minor (corrected: was "Concussion") / skull fracture / comatose massive head injury / abdominal or groin |
| Pre-tonic clonic jerks in a GTC | 0.2–0.3 | Fact-check addition (§4.1) |
| Local muscle bulge when a dead body is hit | 0.1–0.3 per direct muscle hit | ≤ ~2 h after `t_arr` (fact-check addition, §5.5) |
| Aspiration per vomit (unconscious) | 0.5–0.8 supine / 0.1–0.2 lateral | |
| Neurogenic pulmonary oedema froth | 0.2–0.3 (default 0.2) | Massive head injury surviving > 15 min; visible froth only (fact-check: must stay below the 32–50 % autopsy oedema rate) |
| Death rattle | 0.3–0.5 | Unconscious > 60 min |
| Shivering | 0.3–0.5 | Conscious, class II–III, 10–40 min |
| Urine at death | 0.2–0.3 | |
| False last breath | 0.3 | If gasping |

All values are defaults collected from §2–§10 (tags there). The table above is the simulation-parameter table for this section.

### Visual/behavioural checklist (probability summary)
- Over many deaths of the same kind, the variety should match these rates: most heart-shot collapses jerk, fewer than half gasp, a minority stiffen; most slow bleeds never vomit; only long comas rattle.

---

## 14. Load-bearing claims (quick reference)

1. **Syncope**: unconsciousness **12.1 ± 4.4 s**; myoclonic jerks in **~90 %**; eyes **open** with early **upward deviation** (13 of 14 in an eye-movement study; 6 with downbeat nystagmus first); head turns, oral automatisms and righting movements in **79 %** [S1] [S2]. **✓ verified** (1994 values, 42 complete induced syncopes); ⚠ 1996 eye counts not re-verified.
2. **Complete cerebral circulatory arrest**: LOC in **5–10 s** (mean ~6.8 s); **8–15 s** with a destroyed heart (residual pressure); EEG flat at ~15–30 s; pupils start to dilate at 30–45 s and are fixed and wide by 1–2 min [K; M4] `[R1-04 §8, §11.5]`. **✓ verified**; upright → short end, supine → long end (added).
3. **Agonal gasping** occurs in roughly **a third to a half** of cardiac arrests (≈40 % at the time of the call), most often early, and declines with minutes since collapse. Gasps need a working **medulla**; they are absent after medullary destruction [K; M1, M2]. **✓ verified** (M; medulla H).
4. **Gasp kinematics**: a 0.2–0.6 s inspiration with neck extension and jaw opening, then 1–3 s passive expiration; intervals grow from ~10 s to about a minute; the phase lasts **1–5 min** [K] [E]. **⚠ not re-verified** (engineering schedule); default 8 gasps end at ~3.4 min (arithmetic corrected).
5. **GTC seizure**: mean duration **62 s**; tonic ~10–20 s; clonic jerks **slow from ~3–4 Hz to ~1 Hz** with lengthening gaps; eyes open in ~90–97 % [S3] [S4] `[R1-04 §4.2]`. **✓ verified** (M); pre-tonic clonic phase added.
6. **Lateral tongue biting** is highly specific for a GTC (seen in ~20–35 %); syncope bites are rare and at the tip [K; M26, M27]. **✓ verified** (M–H).
7. **Convulsive syncope vs seizure**: syncope jerks are few (**1–10**), irregular, with no slowing pattern, and last < 15 s; seizure jerks are dozens, rhythmic and slowing [K; M8] (attribution corrected: was [K; M8, M9]). **✓ verified** (M).
8. **Spinal reflex movements after brain death**: reported in **13–79 %** of brain-dead patients (≈40 % in the most-cited series); the full **Lazarus** arm-raise is rare; they require a perfused cord [S11] [K; M11, M12]. **✓ verified** (M); [S11] supports the low end only.
9. **Anoxic-ischaemic sequence with a beating heart**: LOC ~10–15 s, convulsions ~15 s, extension ~20 s, flexion ~40 s, loss of tone ~1–1.5 min, last respiratory movement ~1–2 min, last isolated muscle movement **~2–7.5 min** (corrected: was "up to ~4–7 min") [K; M10] (M). **✓ verified** from recall of the filmed-hanging series; times run from the start of suspension.
10. **Cut-throat deaths**: aspiration of blood caused **36.5 %** of deaths in a 74-case autopsy series (exsanguination ~50 %) [S19]. **⚠ not re-verified** (arithmetic consistent with n = 74).
11. **Vomiting after head injury**: ~**7 %** of adults with (mostly minor) head injury seen in hospital (corrected: was "adult concussions"), ~**28 %** with a skull fracture [S15] (L). **⚠ not re-verified**; plausible.
12. **Death rattle**: in 23–92 % of dying patients; median ~16–23 h from onset to death; so **never in fast violent deaths** [K; M13, M15]. **✓ verified** (M).
13. **Palliative signs of death within days**: non-reactive pupils, reduced response to voice and to visual stimuli, **inability to close the eyelids**, drooping nasolabial folds, **hyperextension of the neck**, **grunting of the vocal cords**, upper-GI bleeding [K; M14]. **✓ verified** (H; Hui 2015, eight signs, specificity > 95 %).
14. **Cyanosis** is visible only when deoxygenated haemoglobin is high enough (classic ~5 g/dL capillary). An exsanguinated body turns white, not blue [K; M21]. **✓ verified**; arterial band corrected to 2.5–3.0 g/dL (was 1.5–3).
15. **Mottling** starts at the knees (score 0–5 up to beyond the groin) and needs sustained shock (≥ 10–20 min) [K; M18]. **✓ verified** (score); ⚠ the duration rule is `[E]`.
16. **Shivering** starts at core ~35.5–36 °C, peaks at ~34–35 °C and stops below ~30–32 °C (corrected: was 30–31); it comes in bursts 4–8 times per minute; it is suppressed by deep shock, hypoxia and coma [K; M16, M17]. **✓ verified** (M).
17. **After circulatory arrest**, only faint twitches (first ~15 min), gravity settling and passive fluid movement occur spontaneously; supravital muscle contraction appears only when a muscle is struck (to ~1.5–2.5 h) [K] `[R1-04 §12.7]`. ✓ consistent (M).
18. **Brain death pupils**: fixed, mean **5.0 ± 0.85 mm**; eyes move with the head (doll's eyes absent) [S17] [S18]. **✓ verified** (doll's eyes, 4–9 mm range); ⚠ the mean not re-verified.
19. **Neurogenic pulmonary oedema froth**: lung oedema at autopsy in ~32 % (scene deaths) to ~50 % (deaths within days) of fatal head injuries; visible froth is rarer; game p 0.2–0.3 (default 0.2) [K; M31] [E]. **⚠ not re-verified** (visible-froth p is `[E]`).
20. **Full voluntary action for 10–15 s after the heart is destroyed** (FBI 1989 doctrine) [S22]. **✓ verified** (quote exists; doctrine, not measured data).

---

## 15. QA priority list (open the source and confirm before hard-coding)

1. Gasping incidence and its decline with time; gasp onset, rate and duration [M1] [M2] [M3].
2. The anoxic-ischaemic sequence timings with a beating heart [M10]. Treat as (L–M) until checked.
3. Syncope jerk counts and the syncope-vs-seizure discrimination [M7] [M8] (fact-check: [M9] removed; it has no jerk counts), and the myoclonus share in tilt-table syncope (conflicts with [S1]'s 90 %; the game uses 0.5–0.9 by onset speed).
15. (Fact-check) Lempert & von Brevern 1996 eye-movement counts (7/6/1 of 14) [S2]; Rogers 1995 NPE autopsy rates [M31]; the [S15] vomiting paper (never identified); the [S18] brain-death pupil mean; the Sauvageau 2010/2011 timings [M10], especially the last-muscle-movement range.
4. Asystole/VF anoxic tonic spasm frequency and timing [M5] [M6].
5. Tongue-bite, cry and froth probabilities in GTC [M26] [M27].
6. Spinal reflex frequencies by type, and Lazarus timing and kinematics [S11] [M11] [M12].
7. Death-rattle prevalence and onset-to-death interval; mandibular breathing timing [M13] [M15]; Hui's signs [M14].
8. Neurogenic pulmonary oedema frequency and onset after head injury [M31].
9. Shivering burst frequency and tremor frequency [M16]; BSAS wording [M17]; teeth-chattering frequency (author estimate only).
10. Mottling score wording [M18]; cyanosis threshold formula [M21].
11. Post-anoxic myoclonic status incidence [M25]; lagophthalmos incidence in ICU patients [M34].
12. Cough exit velocities and spatter ranges [M35].
13. Captive-bolt tonic/clonic phase durations used as the human "release" analogue [M32] (analogy is weak; keep (L)).
14. All `[E]` impulse and inertia numbers in §11.3: tune in engine.

---

## 16. References

### 16.1 Sources located by web search in sibling sessions (`[S#]`)

These were found by web search in earlier sessions of this project and are listed in the sibling documents named in brackets. They were read then through search summaries only, and **were not re-read in this session**.

- **[S1]** Lempert T, Bauer M, Schmidt D. Syncope: a videometric analysis of 56 episodes of transient cerebral hypoxia. *Ann Neurol* 1994. https://onlinelibrary.wiley.com/doi/abs/10.1002/ana.410360217 (R2-02 [S26]; R2-01 [S70])
- **[S2]** Lempert T, von Brevern M. The eye movements of syncope. *Neurology* 1996. https://pubmed.ncbi.nlm.nih.gov/8780096/ (R2-02 [S27])
- **[S3]** Theodore WH et al. The secondarily generalized tonic-clonic seizure: a videotape analysis. *Neurology* 1994. https://pubmed.ncbi.nlm.nih.gov/8058138/ (R2-01 [S104])
- **[S4]** Tonic clonic seizure (ScienceDirect Topics; clonic intervals lengthen, jerks slow). https://www.sciencedirect.com/topics/pharmacology-toxicology-and-pharmaceutical-science/tonic-clonic-seizure (R2-01 [S105])
- **[S5]** Focal to bilateral tonic-clonic seizures (MedLink). https://www.medlink.com/articles/focal-to-bilateral-tonic-clonic-seizures ; Semiology of focal- vs generalized-onset bilateral tonic-clonic seizures: systematic review. https://pubmed.ncbi.nlm.nih.gov/33556863/ (R2-01 [S106])
- **[S6]** ILAE seizure descriptions: motor seizure https://www.epilepsydiagnosis.org/seizure/motor-overview.html ; frontal lobe seizure https://www.epilepsydiagnosis.org/seizure/frontal-lobe-overview.html (R2-01 [S107])
- **[S7]** Jacksonian seizures (MedLink). https://www.medlink.com/articles/jacksonian-seizures ; Focal clonic seizures (MedLink). https://www.medlink.com/articles/focal-clonic-seizures (R2-01 [S108])
- **[S8]** Epilepsia partialis continua (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK532275/ (R2-01 [S109])
- **[S9]** Gallmetzer P et al. Postictal paresis in focal epilepsies. *Neurology* 2004. https://www.neurology.org/doi/abs/10.1212/WNL.62.12.2160 ; Frequency and pathophysiology of post-seizure Todd's paralysis. https://pmc.ncbi.nlm.nih.gov/articles/PMC7075081/ (R2-01 [S110])
- **[S10]** Decerebrate and decorticate posturing (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK559135/ (R2-01 [S111])
- **[S11]** Frequency of spinal reflex movements in brain-dead patients. https://www.sciencedirect.com/science/article/abs/pii/S0041134503012752 ; Spittler JF et al. Phenomenological diversity of spinal reflexes in brain death. https://onlinelibrary.wiley.com/doi/10.1046/j.1468-1331.2000.00062.x (R2-01 [S113])
- **[S12]** McCrory PR et al. Concussive convulsions: incidence in sport and treatment recommendations. https://pubmed.ncbi.nlm.nih.gov/9519401/ ; Video analysis of acute motor and convulsive manifestations in sport-related concussion. https://www.neurology.org/doi/10.1212/WNL.54.7.1488 (R2-01 [S100])
- **[S13]** Hosseini AH, Lifshitz J. Brain injury forces of moderate magnitude elicit the fencing response. https://pmc.ncbi.nlm.nih.gov/articles/PMC11421656/ (R2-01 [S99])
- **[S14]** Post-traumatic seizure (ScienceDirect Topics). https://www.sciencedirect.com/topics/medicine-and-dentistry/post-traumatic-seizure ; Annegers JF et al. A population-based study of seizures after traumatic brain injuries. *NEJM* 1998. https://www.nejm.org/doi/full/10.1056/NEJM199801013380104 (R2-01 [S103])
- **[S15]** Post-traumatic vomiting incidence (search summary; exact paper not identified; candidate URLs): https://pmc.ncbi.nlm.nih.gov/articles/PMC1736317 ; https://pubmed.ncbi.nlm.nih.gov/29599113/ (R2-01 [S101])
- **[S16]** Eye movements in coma (LITFL). https://litfl.com/eye-movements-in-coma/ ; Neuro-ophthalmic findings in coma (EyeWiki). https://eyewiki.org/Neuro-ophthalmic_Findings_in_Coma (R2-01 [S66])
- **[S17]** Doll's eyes (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK551716/ (R2-01 [S68])
- **[S18]** Pupillometry in brain death: differences in pupillary diameter between paediatric and adult subjects. https://pubmed.ncbi.nlm.nih.gov/26184095/ (R2-01 [S73])
- **[S19]** An autopsy study of 74 cases of cut throat injuries. https://www.sciencedirect.com/science/article/pii/S2090536X14000781 (R1-02 [R13])
- **[S20]** Davis GA et al. International consensus definitions of video signs of concussion in professional sports. *Br J Sports Med* 2019. https://pubmed.ncbi.nlm.nih.gov/30954947/ (R2-02 [S36])
- **[S21]** UT Southwestern, collapse during exercise (crumple vs crash). https://utswmed.org/medblog/syncope-cardiac-arrest-exercise/ (R2-02 [S53])
- **[S22]** Patrick UW. *Handgun Wounding Factors and Effectiveness*. FBI, 1989. https://archive.org/details/fbi-handgun-wounding-factors-and-effectiveness (R2-02 [S5])
- **[S23]** Karger B et al. Physical activity following fatal injury from sharp pointed weapons. *Int J Legal Med* 1999. https://pubmed.ncbi.nlm.nih.gov/10335884/ (R2-02 [S13])
- **[S24]** Engel GL. Psychologic stress, vasodepressor (vasovagal) syncope, and sudden death. *Ann Intern Med* 1978. https://doi.org/10.7326/0003-4819-89-3-403 (R2-02 [S63]) — background for the vasovagal prodrome; not cited for a number.
- **[S25]** Cushing reflex (StatPearls). https://www.ncbi.nlm.nih.gov/books/NBK549801/ (R2-01 [S85])
- **[S26]** Intracranial pressure (LITFL Part One). https://partone.litfl.com/intracranial_pressure.html ; Intracranial pressure waveform (IntechOpen). https://www.intechopen.com/chapters/73580 (R2-01 [S86])
- **[S27]** Respiratory rate and pattern disturbances in acute brain stem infarction. *Stroke* 1976. https://www.ahajournals.org/doi/pdf/10.1161/01.str.7.4.382 ; Disordered breathing in severe cerebral illness. https://www.sciencedirect.com/science/article/pii/S1569904822000283 (R2-01 [S96])
- **[S33]** Predictors of outcome in civilians with gunshot wounds to the head upon presentation. *J Neurosurg* 2014. https://pubmed.ncbi.nlm.nih.gov/24995781/ ; Analysis of ballistic trajectories and clinical outcomes in civilian penetrating brain injury. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11599325/ (R2-01 [S95])

(IDs S28–S32 are unused.)

### 16.2 Literature recalled from memory (`[K; M#]`; not opened in this session; verify)

- **[M1]** Clark JJ, Larsen MP, Culley LL, Graves JR, Eisenberg MS. Incidence of agonal respirations in sudden cardiac arrest. *Ann Emerg Med* 1992;21(12):1464–1467.
- **[M2]** Bobrow BJ, Zuercher M, Ewy GA, et al. Gasping during cardiac arrest in humans is frequent and associated with improved survival. *Circulation* 2008;118(24):2550–2554.
- **[M3]** Porcine ventricular-fibrillation gasping studies from the University of Arizona resuscitation group (Ewy, Zuercher and colleagues, 2000s). Exact titles not recalled reliably.
- **[M4]** Rossen R, Kabat H, Anderson JP. Acute arrest of cerebral circulation in man. *Arch Neurol Psychiatry* 1943;50(5):510–528.
- **[M5]** Gastaut H, Fischer-Williams M. Electro-encephalographic study of syncope: its differentiation from epilepsy. *Lancet* 1957;273(7004):1018–1025.
- **[M6]** Aminoff MJ, Scheinman MM, Griffin JC, Herre JM. Electrocerebral accompaniments of syncope associated with malignant ventricular arrhythmias. *Ann Intern Med* 1988;108(6):791–796.
- **[M7]** van Dijk JG, Thijs RD, van Zwet E, et al. The semiology of tilt-induced reflex syncope in relation to electroencephalographic changes. *Brain* 2014;137(2):576–585.
- **[M8]** Shmuely S, Bauer PR, van Zwet EW, van Dijk JG, Thijs RD. Differentiating motor phenomena in tilt-induced syncope and convulsive seizures. *Neurology* 2018;90(15):e1339–e1346.
- **[M9]** Sheldon R, Rose S, Ritchie D, et al. Historical criteria that distinguish syncope from seizures. *J Am Coll Cardiol* 2002;40(1):142–148. (Fact-check: a questionnaire-based diagnostic score; it supports "waking with a cut tongue", head turning and prolonged confusion as seizure markers, but it has **no jerk counts**. Removed as a source for §3.1 jerk numbers.)
- **[M10]** Sauvageau A, LaHarpe R, Geberth VJ. Agonal sequences in eight filmed hangings: analysis of respiratory and movement responses to asphyxia by hanging. *J Forensic Sci* 2010;55(5):1278–1281; and Sauvageau A et al. Agonal sequences in 14 filmed hangings with comments on the role of the type of suspension, ischemic habituation, and ethanol intoxication on the timing of agonal responses. *Am J Forensic Med Pathol* 2011;32(2):104–107. (Used only for the timing of motor and respiratory responses to cerebral ischaemia.)
- **[M11]** Ropper AH. Unusual spontaneous movements in brain-dead patients. *Neurology* 1984;34(8):1089–1092.
- **[M12]** Saposnik G, Bueri JA, Mauriño J, Saizar R, Garretto NS. Spontaneous and reflex movements in brain death. *Neurology* 2000;54(1):221–223.
- **[M13]** Morita T, Ichiki T, Tsunoda J, Inoue S, Chihara S. A prospective study on the dying process in terminally ill cancer patients. *Am J Hosp Palliat Care* 1998;15(4):217–222.
- **[M14]** Hui D, dos Santos R, Chisholm G, et al. Clinical signs of impending death in cancer patients. *Oncologist* 2014;19(6):681–687; and Bedside clinical signs associated with impending death in patients with advanced cancer. *Cancer* 2015;121(6):960–967.
- **[M15]** Wildiers H, Menten J. Death rattle: prevalence, prevention and treatment. *J Pain Symptom Manage* 2002;23(4):310–317.
- **[M16]** Israel DJ, Pozos RS. Synchronized slow-amplitude modulations in the electromyograms of shivering muscles. *J Appl Physiol* 1989;66(5):2358–2363.
- **[M17]** Badjatia N, Strongilis E, Gordon E, et al. Metabolic impact of shivering during therapeutic temperature modulation: the Bedside Shivering Assessment Scale. *Stroke* 2008;39(12):3242–3247.
- **[M18]** Ait-Oufella H, Lemoinne S, Boelle PY, et al. Mottling score predicts survival in septic shock. *Intensive Care Med* 2011;37(5):801–807.
- **[M19]** Saukko P, Knight B. *Knight's Forensic Pathology*. 4th ed. CRC Press; 2016. (Agonal and post-mortem regurgitation, aspirated blood as a vital sign, tongue drying, cutis anserina, cadaveric spasm.)
- **[M20]** Madea B (ed.). *Estimation of the Time Since Death*. 3rd ed. CRC Press; 2016. (Supravital muscle excitability.)
- **[M21]** Lundsgaard C, Van Slyke DD. Cyanosis. *Medicine* 1923;2(1):1–76.
- **[M22]** Dawes GS. *Foetal and Neonatal Physiology*. Year Book Medical Publishers; 1968. (Primary apnoea, gasping, terminal apnoea in asphyxia.)
- **[M24]** Lance JW, Adams RD. The syndrome of intention or action myoclonus as a sequel to hypoxic encephalopathy. *Brain* 1963;86:111–136.
- **[M25]** Wijdicks EFM, Parisi JE, Sharbrough FW. Prognostic value of myoclonus status in comatose survivors of cardiac arrest. *Ann Neurol* 1994;35(2):239–243.
- **[M26]** Benbadis SR, Wolgamuth BR, Goren H, Brener S, Fouad-Tarazi F. Value of tongue biting in the diagnosis of seizures. *Arch Intern Med* 1995;155(21):2346–2349.
- **[M27]** Brigo F, Nardone R, Bongiovanni LG. Value of tongue biting in the differential diagnosis between epileptic seizures and syncope. *Seizure* 2012;21(8):568–572.
- **[M29]** Chung SS, Gerber P, Kirlin KA. Ictal eye closure is a reliable indicator for psychogenic nonepileptic seizures. *Neurology* 2006;66(11):1730–1731.
- **[M30]** Wilson MH, Hinds J, Grier G, et al. Impact brain apnoea. *Resuscitation* 2016;105:52–58; Atkinson JLD. The neglected prehospital phase of head injury: apnea and catecholamine surge. *Mayo Clin Proc* 2000;75(1):37–47.
- **[M31]** Davison DL, Terek M, Chawla LS. Neurogenic pulmonary edema. *Crit Care* 2012;16(2):212; and Rogers FB, Shackford SR, Trevisani GT, et al. Neurogenic pulmonary edema in fatal and nonfatal head injuries. *J Trauma* 1995;39(5):860–866.
- **[M32]** Gregory NG. *Animal Welfare and Meat Production*. 2nd ed. CABI; 2007; and EFSA Scientific Opinion on welfare aspects of the main systems of stunning and killing (2004). (Tonic and clonic phases after penetrating stunning; analogy only.)
- **[M34]** Grixti A, Sadri M, Edgar J, Datta AV. Common ocular surface disorders in patients in intensive care units. *Ocul Surf* 2012;10(1):26–42.
- **[M35]** Gupta JK, Lin CH, Chen Q. Flow dynamics and characterization of a cough. *Indoor Air* 2009;19(6):517–525.
- **[M36]** Whinnery JE, Whinnery AM. Acceleration-induced loss of consciousness: a review of 500 episodes. *Arch Neurol* 1990;47(7):764–776.

(IDs M23, M28 and M33 are unused; see `[R1-04 §16]` for brain-death guidelines, seizure-duration data and autoresuscitation.)

---

## 17. Suspicious content

- **None encountered.** No web content was retrieved in this session: every `WebSearch` call was refused (search budget exhausted, 200 of 200 calls), and `WebFetch` was not used. There were therefore no pages, snippets or code that could carry injected instructions.
- The only material read was the sibling research documents in this repository (`docs/research/01–04`, `docs/research2/01–02`). They were treated as data. They contained no instructions directed at the reader.
- Nothing was downloaded, installed or executed. No commands were run. No code was copied from any external source; the pseudocode in §11.2 was written for this document. No install commands or links to executables appear in this document.
- **Fact-check pass (§18)**: again **none encountered**. The checker's `WebSearch` calls were refused (budget 200/200 used) and its one `WebFetch` to a PubMed abstract was refused by the egress proxy (`EGRESS_BLOCKED`), so no web text reached the checker. Only local sibling documents were read, as data. No instructions were found in them.

---

## 18. Fact-check (independent review, 2026-09-26)

### 18.1 Method and limits of this check

- **No fresh web evidence could be obtained.** Both `WebSearch` calls were refused because the session's shared search budget was exhausted (200/200). One `WebFetch` to the PubMed abstract of `[S2]` was refused by the egress proxy (`EGRESS_BLOCKED`).
- The check therefore rests on:
  1. the checker's own knowledge of the primary literature `[K]`, with a confidence grade;
  2. **re-derivation** of every computed number (gasp schedule, cyanosis thresholds, momentum, arithmetic of the cut-throat series);
  3. consistency with round one (`[R1-02]`, `[R1-03]`, `[R1-04]`) and with the fact-checked round-two files `[R2-01]` and `[R2-02]`. Those files draw on the same search summaries, so they are **not independent confirmation** of the `[S#]` numbers; they only show what the earlier searches returned.
- Process note: before starting, the checker ran one read-only local directory listing (file names and a line count) in the shell. Nothing else was executed, downloaded or installed, and no other file was changed.
- Marks used in the text: **✓ verified**, **⚠ not re-verified**, **corrected: was X** (see §0.1).

### 18.2 Per-claim verdicts

| # | Claim | Verdict | Value to use | Basis |
|---|---|---|---|---|
| 1 | Syncope: LOC 12.1 ± 4.4 s; jerks ~90 %; automatisms 79 %; eyes open | ✓ verified | Unchanged. Context added: 59 volunteers, 56 episodes, 42 complete induced syncopes | `[K]` (H): standard, widely reproduced abstract values of Lempert 1994 |
| 2 | Eye movements 7/14 up, 6/14 downbeat then up, 1/14 primary | ⚠ counts not re-verified; qualitative ✓ | Unchanged; upgaze transient | `[K]` (M): upward deviation predominates, sometimes preceded by downbeat nystagmus |
| 3 | Cerebral flow stop → LOC 5–10 s (mean 6.8); destroyed heart 8–15 s | ✓ verified | Unchanged; **posture factor added** (upright ×0.85, supine ×1.2) | Rossen 1943 `[K]` (H); asystole/VF LOC ~6–12 s `[K]` (M) |
| 4 | 10–15 s of full voluntary action after the heart is destroyed | ✓ verified | Unchanged; §10.2 now states action can continue through the grey-out until LOC | FBI 1989 (Patrick) wording `[K]` (H); doctrine, not measured data |
| 5 | Gasping in ~33–40 % of arrests; declines with time; needs the medulla | ✓ verified | Unchanged | Clark 1992 (~40 % at the call), Bobrow 2008 (~33 %, decline with time, ~3× survival) `[K]` (M); medullary generator `[K]` (H) |
| 6 | Gasp schedule 5–120 s / 6–20 s × 1.15–1.5 / 3–30 gasps / false last breath 0.3 | ⚠ not re-verified (engineering) | Unchanged; **arithmetic corrected**: the default 8 gasps end at ~3.4 min, not ~4 min | Re-derived 10 × 1.3ⁿ series |
| 7 | GTC mean 62 s; only 27 % show all phases | ✓ verified (M) | Unchanged; **pre-tonic clonic phase added** (p 0.2–0.3) | Theodore 1994 via `[R2-01]` summary; other video-EEG series ~1–2 min `[K]` |
| 8 | Clonic jerks slow (~3–4 Hz → ~1 Hz) with lengthening gaps | ✓ verified (qualitative, M); frequencies `[E]` | Unchanged | Classic Gastaut description `[K]` |
| 9 | Lateral tongue bite highly specific; sensitivity ~20–35 %; syncope bites rare, at the tip | ✓ verified (M–H) | Unchanged | Benbadis 1995 (~24 % / ~99 %); Brigo 2012 (~33 % / ~96 %) `[K]` |
| 10 | Syncope jerks 1–10, irregular, no slowing, < 15 s; seizures dozens, rhythmic, slowing | ✓ verified (M); **attribution corrected** | Unchanged; source is [M8] only (was [M8, M9]) | Shmuely 2018 `[K]` (M); Sheldon 2002 has no jerk counts |
| 11 | Spinal reflexes in 13–79 % (~40 % most-cited); Lazarus rare; needs perfused cord | ✓ verified (M); attribution clarified | Unchanged (p 0.2–0.4; Lazarus 0.03–0.05) | Saposnik 2000 15/38 = 39 % `[K]` (M–H); [S11] supports only the low end |
| 12 | Hanging-type ischaemia: LOC 10–15 s … last twitch 4–7 min | ✓ verified (M); **one value corrected** | Last isolated movement **~2–7.5 min** (was "up to ~4–7 min"); other times unchanged; timed from the start of suspension | Recall of Sauvageau 2010: 13, 14, 19, 38 s; 1:17 min; last breath 1:02–2:05; last movement 1:52–7:31 `[K]` (M) |
| 13 | Cut throat (74 cases): ~50 % exsanguination, 36.5 % aspiration | ⚠ not re-verified | Unchanged | Arithmetic consistent (27/74, 37/74); the paper itself could not be opened |
| 14 | Vomiting ~7 % of adult concussions, ~28 % with skull fracture | ⚠ not re-verified; **wording corrected** | 0.07 / 0.28, relabelled "adult head injury seen in hospital (mostly minor)" | Source paper never identified; magnitude plausible `[K]` (L–M) |
| 15 | Death rattle 23–92 %; median ~16–23 h; not in fast deaths | ✓ verified (M) | Unchanged | Range quoted in the Cochrane and other reviews `[K]` (M–H); exact medians not re-opened |
| 16 | Hui signs of death within days | ✓ verified (H) | Unchanged | Hui 2015: eight bedside signs, specificity > 95 % `[K]` |
| 17 | Cyanosis ~5 g/dL capillary; arterial game rule ≥ 2.5 g/dL; bled-out body white-grey | ✓ verified; **range corrected** | Default 2.5; band **2.5–3.0** (was 1.5–3) | Capillary ≈ arterial + ~1.9 g/dL; Comroe & Botelho observer data `[K]` (M); 1.5 g/dL is the methaemoglobin figure |
| 18 | Mottling from the knees, score 0–5; needs ≥ 10–20 min of shock | ✓ score (H); ⚠ timing `[E]` | Unchanged; note that the score comes from septic shock | Ait-Oufella 2011 `[K]` |
| 19 | Shivering: start 35.5–36 °C, peak 34–35 °C, stop < 30–31 °C; bursts 4–8/min; suppressed by shock, hypoxia, coma | ✓ verified (M); **stop widened** | Stop **30–32 °C** (default 31; was 30–31) | Sessler thresholds; Swiss hypothermia staging; Israel & Pozos 4–8 cycles/min `[K]` |
| 20 | Brain-death pupils 5.0 ± 0.85 mm; doll's eyes absent | ✓ doll's eyes and 4–9 mm range; ⚠ mean | Unchanged | AAN brain-death criteria `[K]` (H); mean from the `[R2-01]` search summary only |
| 21 | NPE froth common in fatal head injury; game p 0.2–0.3, onset 15 min – 4 h | ⚠ not re-verified (game p); autopsy rates ✓ (M) | p 0.2–0.3 kept, **default 0.2**; p is *visible* froth, below the 32–50 % autopsy oedema rate | Rogers 1995 recalled as ~32 % (scene) / ~50 % (≤ 96 h) `[K]` (M) |

### 18.3 Other changes made in the text

- §2.2: default gasp-schedule arithmetic corrected (the eighth gasp is at ~206 s); ✓/⚠ marks on incidence rows and gasp parameters.
- §2.5: cut-throat row marked ⚠, with the arithmetic check and the fatal-series bias noted.
- §2.6: autopsy oedema separated from visible froth; `npe_p` default 0.2.
- §2.7 and §13: "adult concussion" relabelled.
- §3.1: study population, a hallucination row (~60 % of induced faints reported visual or auditory experiences, `[K]` (M)) and ✓/⚠ marks added; [M9] removed as a jerk-count source.
- §3.2: Rossen, posture and EEG notes; upgaze row marked transient.
- §3.3 and §3 parameters: hanging-series times refined; last twitch 110–450 s (default 240).
- §4.1–4.2: pre-tonic clonic phase and `gtc_pretonic_clonic_p` added; tongue-bite statistics added.
- §5.4: frequency sources clarified. §5.5: **what a dead body does when shot, stabbed or struck** added, with `pm_hit_idiomuscular_p`.
- §6.2: shivering rows marked; stop threshold widened.
- §7.1: brain-death pupil and doll's-eye marks.
- §8.2–8.3: cyanosis derivation and corrected band; mottling vs livor mortis note.
- §10.2: action can continue until LOC. §10.3: "Screams" corrected (no voice when the airway is cut below the cords). §10 checklist: upgaze only for seconds.
- §12: myth rows 16–21 and two new assertions; checklist additions. §14: verdict marks and two new items (19–20). §15: new QA item 15. §16.2: note on [M9]. §17: fact-check pass logged.

### 18.4 Myth audit (this document)

| Myth | Status |
|---|---|
| Bullets knock people backwards | **Gap filled**: §12 row 17 (the document was silent; `[R2-02 §1.3]` has the arithmetic, which the checker re-derived for §5.5: 9 mm ≈ 2.9 N·s → whole body ~0.04 m/s) |
| Eyes "roll back" at the moment of death | **Gap filled**: §12 row 16, `assert_no_upgaze_in_dead`, §3.2 and §10 wording. The document already had upgaze correctly transient in §3.2; the §10 checklist said "eyes rolled up" without the time limit |
| "Hydrostatic shock" drops people from torso hits | **Gap filled**: §12 row 18 and an assertion |
| Everyone screams when shot | **Corrected**: §10.3 carotid row ("Screams" → conditional; none with a cut airway); §12 row 19 |
| Heart shot = instant drop | ✓ Correctly rejected (§10.2, [S22]); strengthened |
| Long violent "death throes" | **Gap filled**: §12 row 20 |
| A corpse jerks when shot | **Gap filled**: §5.5 and §12 row 21 |
| Death rattle in every death; foam in every death; blue bled-out body; mottling in a 1-min death | ✓ Correctly rejected in the original (§12 rows 7, 8, 13, 14) |

### 18.5 Gaps added

1. **Posture changes time to LOC** after circulatory arrest (upright faster, supine slower) (§3.2).
2. **Pre-tonic clonic phase** of a GTC (§4.1).
3. **Response of a dead body to being shot, stabbed or struck**: mechanical only, plus a small local idiomuscular bulge within ~2 h (§5.5).
4. **Visible froth vs autopsy lung oedema** distinction (§2.6).
5. **Mottling vs livor mortis** distinction (§8.3).
6. **Post-faint experiences** (~60 % in induced faints) for survivor dialogue (§3.1).
7. **Screaming gated by airway state** (§10.3).
8. Myth rows 16–21 and two assertions (§12).

### 18.6 Simulation parameters changed or added by the fact-check

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `cerebral_arrest_loc` posture factor | ×0.85 upright, ×1.2 supine | × | New | [E] on [K] (M) |
| `ischaemic_beating_heart_seq` last twitch | 110–450 (default 240) | s | Was "≤ 240–450" | [K; M10] (M) |
| `gtc_pretonic_clonic_p` | 0.2–0.3; 2–6 jerks at 1–3 Hz over 1–5 s | p | New | [S3] [E] |
| `npe_p` | 0.2–0.3, default 0.2 | p | Visible froth only | [K; M31] [E] |
| `cyanosis_threshold_deoxyHb_arterial` | 2.5 (band 2.5–3.0) | g/dL | Band was 1.5–3 | [K; M21] (M) |
| `shiver_core_stop` | 30–32 (default 31) | °C | Was 30–31 | [K] (M) |
| `pm_hit_idiomuscular_p` | 0.1–0.3 per direct muscle hit; ≤ ~2 h after `t_arr`; 5–20 mm bulge | p | New | [K] (M), [E] |
| `assert_no_upgaze_in_dead` / `assert_no_instant_drop_without_cns_or_support_loss` | true / true | bool | New | [S2] [S22] [K] |
| `carotid_scream_p` | airway intact 0.3–0.5; airway cut below the cords 0 | p | New | [E] on [K] |

### 18.7 Visual/behavioural checklist (fact-check additions)

- A faint or cardiac collapse: eyes up for a few seconds, then back to the front; in the dead, the eyes look straight ahead or slightly outward, never rolled up to the whites.
- A standing victim goes down a little faster than one already lying down when the heart stops.
- Some seizures open with a few scattered jerks before the body goes rigid.
- A corpse that is shot jolts only as much as the bullet's momentum allows, then settles; it never convulses.
- A victim whose windpipe is cut can make no scream; the sound is hissing, bubbling and gurgling.
- Pink-white froth appears in only a minority of head-injury deaths, even though wet lungs are common at autopsy.

### 18.8 Checker's bibliography (`[K]`; cited from memory, **not accessed** in this session, so no URLs)

- Comroe JH, Botelho S. The unreliability of cyanosis in the recognition of arterial anoxemia. *Am J Med Sci* 1947;214:1–6.
- Sessler DI. Temperature monitoring and perioperative thermoregulation. *Anesthesiology* 2008;109:318–338.
- Brown DJA, Brugger H, Boyd J, Paal P. Accidental hypothermia. *N Engl J Med* 2012;367:1930–1938. (Swiss staging.)
- Hui D, et al. Bedside clinical signs associated with impending death in patients with advanced cancer. *Cancer* 2015;121:960–967 (= [M14]).
- Wee B, Hillier R. Interventions for noisy breathing in patients near to death. *Cochrane Database Syst Rev* 2008. (Death-rattle prevalence range.)
- Wijdicks EFM, Varelas PN, Gronseth GS, Greer DM. Evidence-based guideline update: determining brain death in adults. Report of the Quality Standards Subcommittee of the American Academy of Neurology. *Neurology* 2010;74:1911–1918. (Pupils mid-size to dilated; oculocephalic reflex absent.)
- Gastaut H, Broughton R. *Epileptic Seizures*. Springfield: Thomas; 1972. (Tonic, vibratory and clonic phases.)
