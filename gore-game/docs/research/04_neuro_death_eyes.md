# 04 — Neurological injury, the dying process, the eyes, and the first hours after death

Project: **Gore Head** (Godot 4.5, Forward+, GDScript, Jolt). Research input for the **physiology state machine**, the **eye system**, the **ragdoll/posture system**, and the **post-mortem system**.
Scope: brainstem, cerebral hemisphere and spinal cord injury; posturing, fencing response, seizures and raised intracranial pressure; death from exsanguination and from heart or lung wounds; what the eyes do during unconsciousness, dying and after death; the changes in the first 48 h after death. Every section gives real times and a suggested compressed **game time**.
Audience: simulation, animation, VFX, shader and audio engineers. Clinical tone. The subject is a fictional, procedurally generated adult.
Cross-references:
- `01_gunshot_wounds.md`: skull and brain wounding, raccoon eyes, incapacitation statistics. Its source IDs are written here as `[D01:Sx]`.
- `02_sharp_blunt_burn.md`: basal skull fracture signs, subconjunctival haemorrhage, bleeding rates by head region, and the antemortem vs postmortem wound rule. Its source IDs are written here as `[D02:Rx]`.

---

## 0. Read this first

### 0.1 Method and limits (important)

- **No web page could be read in this session.**
  - Every `WebSearch` call was refused because the session's search budget (200 calls) had already been used up by earlier research tasks.
  - Every `WebFetch` call returned `EGRESS_BLOCKED` from the network egress policy. Domains tried: ncbi.nlm.nih.gov, pmc.ncbi.nlm.nih.gov, en.wikipedia.org, librepathology.org, europepmc.org, radiopaedia.org, emedicine.medscape.com, teachmeanatomy.info.
  - Per the environment rules, no workaround was attempted.
- **Consequence: the numbers in this document come from the author's own knowledge of the standard literature.** That covers ATLS, Plum & Posner, Knight's Forensic Pathology, Madea/Henssge on time since death, and the neurology and trauma papers listed in §16. Everything is tagged so you can see exactly what that means.
  - A specific paper cited from memory is tagged `[Cn]`. The bibliographic details in §16 are complete enough to find each one. **None of them was re-opened in this session.**
  - Where a sibling document (01, 02) located a source by web search in an earlier session, it is cited as `[D01:Sx]` / `[D02:Rx]`. Its URL is repeated in §16.
- **Before any number becomes a hard-coded constant, QA should check it against the cited source.** The priority list is in §15.
- Where sources disagree or ranges are wide, each table gives the range, a **default**, and the reason for choosing it.

### 0.2 Tags and confidence

| Tag | Meaning |
|---|---|
| `[Cn]` | A specific published source (§16), cited from memory. Not re-read in this session. |
| `[D01:Sx]`, `[D02:Rx]` | A source found by web search in sibling document 01 or 02. The URL is listed there and in §16. |
| `[K]` | General textbook knowledge (Plum & Posner, Knight, ATLS, Gray's, Guyton). No specific source was retrieved. |
| `[E]` | Engineering derivation or estimate. The arithmetic or reasoning is shown. |
| `[G]` | Game-design choice: a value picked for readability or pacing within (or at the edge of) the real range. |
| **(H) / (M) / (L)** | Author's confidence that the real-world value lies in the stated range: high, medium, low. |

### 0.3 Conventions

- **Reference body**: male, 75 kg, 1.75 m, 30 years old. Scale blood volume and cooling by mass (§1, §12).
- **Pressures** are in mmHg (1 mmHg = 133.3 Pa). A 1 cm column of blood (ρ ≈ 1,060 kg/m³) = **0.78 mmHg** `[E]`.
- **Colours** are approximate sRGB hex values under D65 for light-to-medium skin, authored `[K]`/`[G]`. On dark skin, pallor, cyanosis and livor are harder to see. Show them in the lips, nail beds, conjunctivae and palms, as clinicians do `[K]`.
- **Blood palette** (from doc 02): arterial `#C4161C`, venous `#7A0A10`, fresh clot `#5A0A0E`, dried `#3B1512`.
- **Time**: `t_real` is the medically real time. `t_game` is the suggested on-screen time. The default global policy `[G]`:

| Band | Real duration | Default scale | Why |
|---|---|---|---|
| Acute | first 60 s after a critical event (hit, collapse, arrest) | **1×** | The collapse, the eyes and the last breaths are the drama. Never compress them |
| Minutes | 1–30 min | **3–6×** (default 4×) | Keeps the order of stages; avoids dead air |
| Long dying | 30 min – 6 h (slow bleed, epidural haematoma) | **10–30×** (default 15×) | Keeps stages readable in 5–15 min of play |
| Post-mortem | 0–48 h after death | **120×** default (1 h real = 30 s). Player fast-forward 720× (1 h = 5 s) | Forensic "time-lapse" of livor, rigor, corneal clouding |

  Put one `sim_time_scale` in the physiology system and have every rate in this document integrate in *sim* time. Visual blends (lid droop, pupil dilation) run in *sim* time as well, except the 1× acute band.

### 0.4 Performance note (the user's 60 fps requirement)

Nothing in this document needs much CPU or GPU `[E]`:

- **Physiology state**: about 60–120 floats and enums per character, integrated at a **fixed 20 Hz** (drop to 2–5 Hz once dead). That is a few hundred arithmetic operations per tick in GDScript, far below 0.1 ms per character per tick `[E]`. Keep the arrays pre-allocated. Do not allocate per tick.
- **Eyes**: one material per eye with about 8–10 uniforms: `pupil_mm`, `gloss`, `corneal_opacity`, `dry_band`, `tache_noire`, `bloodshot`, `petechiae`, `subconj_mask_strength`. Lid and gaze positions go through existing bones or blendshapes. No extra passes are needed.
- **Skin (pallor, cyanosis, mottling, livor)**: 3–5 scalar uniforms plus one low-resolution mask (vertex colour, or a 128–256 px texture). Recompute the mask **on events or at ≤ 1 Hz, never every frame**. Livor needs the gravity direction in body space only when the body comes to rest, and again only if it is moved.
- **Posture and paralysis**: drive the existing Jolt ragdoll (for example PhysicalBone3D under a PhysicalBoneSimulator3D) by changing joint drive targets and strengths per state. Flaccid means zero drive. Rigor means joint damping and stiffness ramping up over hours. This adds no bodies and no extra collision cost.
- **Audio**: agonal breaths, gurgles and coughs are one-shot samples scheduled by the state machine.
- The heavy costs in this game are blood particles, decals and mesh cutting (docs 01 and 02), not the physiology described here. Profile anyway.

---

## 1. Shared physiology constants (used by every later section)

| Quantity | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| Blood volume | 70 (male), 65 (female) | mL/kg | ≈ 7% of body weight. Reference body: **5,250 mL** | [C1] [K] (H) |
| Cardiac output at rest | 5 (4–6) | L/min | HR 60–80 × SV ~70 mL | [K] (H) |
| Normal BP / MAP | 120/80 / 93 | mmHg | MAP ≈ DBP + (SBP − DBP)/3 | [K] (H) |
| Intrinsic (denervated) heart rate | 118.1 − 0.57 × age | bpm | ≈ 101 bpm at 30 y. The rate the heart keeps after the medulla is destroyed, until hypoxia slows it | [C36] (M) |
| Brain mass | 1,300–1,400 | g | | [K] (H) |
| Cerebral blood flow (CBF) | 50 | mL/100 g/min | ≈ 700–750 mL/min, ~15% of cardiac output | [K] (H) |
| Brain O₂ consumption | 3.3–3.5 | mL O₂/100 g/min | ≈ 45–50 mL/min, ~20% of whole-body O₂ | [K] (H) |
| CBF at which function fails | < 20 | mL/100 g/min | EEG slows, then goes silent. Membrane failure and infarction below ~10 | [K] (H) |
| Autoregulation lower limit | MAP 50–60 (up to 70) | mmHg | Below this, CBF follows MAP passively | [K] (M) |
| Time to unconsciousness after complete stop of brain blood flow | 5–10 (mean ~6.8) | s | Neck-cuff occlusion experiments | [C9] (H) |
| "Functional buffer" (G-LOC) | ~5–6 | s | Oxygen reserve after cerebral flow stops | [C10] (M) |
| Voluntary action possible after the heart is destroyed | 10–15 | s | Classic FBI wound-ballistics figure | [C7] [C8] (M–H) |
| EEG isoelectric after circulatory arrest | 10–40 (typ. ~20) | s | | [K] (M) |
| Onset of irreversible neuronal injury, normothermic arrest | 4–6 | min | Cortex first; brainstem more tolerant | [K] (H) |
| Intracranial pressure (ICP), normal | 5–15 | mmHg | Supine adult. Default 10 | [K] (H) |
| ICP treatment threshold (TBI guidelines) | > 22 | mmHg | | [C28] (H) |
| Cerebral perfusion pressure | CPP = MAP − ICP. Normal 60–80. Ischaemia < 50 | mmHg | If ICP ≥ MAP, cerebral circulation stops | [K] (H) |
| Pressure–volume index (PVI) | 25 (20–30) | mL | Volume that raises ICP ten-fold on the steep part of the curve | [C30] (M) |
| CSF production | 0.35 | mL/min | ≈ 500 mL/day. CSF volume ~150 mL | [K] (H) |
| Resting respiration | RR 12–20/min, tidal volume ~500 mL, VO₂ ~250 mL/min | — | | [K] (H) |
| O₂ stores breathing room air | ~1.5 | L | Lungs ~0.4–0.5 L, blood ~0.8–0.9 L | [K] (M) |
| Apnoea on room air: SpO₂ < 90% | 60–90 (faster when struggling) | s | | [K] (M) |
| Apnoea: hypoxic loss of consciousness | 1.5–3 | min | Circulation intact | [K] (M) |
| Apnoea: cardiac arrest | 4–10 (default 6) | min | Hypoxic bradycardia → PEA/asystole | [K] (M) |
| Central cyanosis visible | deoxy-Hb ≥ ~5 g/dL | — | **Needs enough haemoglobin.** An exsanguinated body turns grey-white, not blue | [K] (H) |
| Mean systemic filling pressure after arrest | ~7 (classic) to ~13 (human ICU measurements) | mmHg | Pressure that arteries and veins equalise to within about a minute of arrest | [C51] [C52] (M) |
| Arterial jet exit speed | v = √(2ΔP/ρ): 120 mmHg → **5.5 m/s** | m/s | Ideal jet height 1.54 m. Real jets **0.3–1.5 m** after friction, wound shape and vessel spasm | [E] |

### Visual/behavioural checklist (shared)
- Blood loss is the clock for most deaths. Brain oxygen is the clock for the last 10–15 s of consciousness. Brain-cell survival is the clock for the 4–6 min after arrest.
- Exsanguinated people look **white-grey**. People who stop breathing with a full blood volume look **blue-grey (cyanotic)**. Do not tint a bled-out body blue.
- Arterial jets rise and fall with each heartbeat. They shrink as blood pressure falls and **stop at cardiac arrest**.

---

## 2. Brainstem injury (medulla, pons, midbrain)

### 2.1 Anatomy an engineer needs

| Part | Size (adult) | Key contents | Function lost when destroyed | Source |
|---|---|---|---|---|
| **Midbrain** | ~15–20 mm long, ~25–30 mm wide at the cerebral peduncles | Upper reticular activating system (RAS), CN III/IV nuclei, red nucleus, cerebral peduncles (corticospinal tracts), vertical gaze centres | Consciousness. Pupil control (mid-position fixed pupils). Vertical and adducting eye movements. Descending motor pathways | [C50] [C19] [K] (M) |
| **Pons** | ~25 mm long, ~35–40 mm wide | Rostral RAS (tegmentum), CN V–VIII nuclei, horizontal gaze centre (PPRF, CN VI), pontine respiratory group, corticospinal tracts (basis pontis) | Consciousness (tegmentum). Horizontal gaze. Corneal and blink reflexes. Pupil dilation (sympathetic path, so pinpoint pupils). Breathing rhythm modulation | [C50] [C19] [K] (M) |
| **Medulla oblongata** | ~30 mm long, ~20 mm wide, ~12–13 mm front to back | Respiratory rhythm generator (pre-Bötzinger complex; dorsal and ventral respiratory groups), vasomotor centre (rostral ventrolateral medulla), cardiac vagal nuclei, gasp generator, CN IX–XII (swallow, gag, cough, tongue), pyramidal decussation | **Breathing** (immediate apnoea). **Vascular tone** (BP falls). Gag, cough and swallow. Descending motor pathways | [C50] [C19] [K] (M) |
| Cervicomedullary junction | At the foramen magnum. With the head neutral it lies at roughly the plane of the hard palate / nasal floor | Medulla continues into the C1 cord | See §6 (C1–C2) | [K] (M) |

- The whole brainstem is ~70–80 mm long and ~25–30 g. It sits on the clivus, directly behind the nasopharynx and sphenoid, and in front of the cerebellum. It is supplied by the vertebrobasilar arteries `[K] (M)`.
- **Engineering note** `[G]`: author the brainstem and upper cervical cord as their own hit volumes inside the skull model. Label them `midbrain`, `pons_tegmentum`, `pons_basis`, `medulla` and `cord_C1_C2`, because the outcome depends on which one is hit (table below). Also give each a **concussive radius** (§2.2) so that near-misses count.

### 2.2 What happens when each level is destroyed

| Level destroyed | Consciousness | Breathing | Circulation | Motor | Eyes / pupils | How the body falls |
|---|---|---|---|---|---|---|
| **Midbrain** | Coma at once (upper RAS) | Continues at first (medulla intact). Central neurogenic hyperventilation possible (§5.5). Fails later | Maintained at first | **Decerebrate extension** possible (lesion below the red nucleus), otherwise flaccid | **Mid-position (4–6 mm), fixed**. Third-nerve palsy: eye down and out, ptosis. Vertical gaze lost. Dysconjugate | Stiff and extended ("falls like a log"), or crumples |
| **Pons (tegmentum)** | Coma | Apneustic, cluster or ataxic breathing, then apnoea within minutes | Maintained at first | Decerebrate or flaccid | **Pinpoint (1–2 mm)**, reactive only under magnification. Ocular bobbing. No horizontal eye movement. **Corneal reflex lost** | Crumples |
| **Pons (ventral basis only)**: rare, low-energy or partial | **Conscious ("locked-in")** | Preserved, may be irregular | Maintained | Quadriplegia and facial paralysis. **Only vertical eye movement and blinking remain** | Pupils normal. Vertical gaze preserved | Collapses fully awake |
| **Medulla** | Lost at once in ballistic injury (shock wave and cavitation spread into the pons and RAS). A purely medullary lesion could leave the person awake until hypoxia | **Immediate apnoea. No agonal gasps** (the gasp generator is in the medulla) | Loss of vasomotor tone: **MAP falls to 40–60 mmHg within ~30–60 s**. The heart keeps beating at its intrinsic rate (~100 bpm) and arrests 4–10 min later from hypoxia | **Flaccid (GCS motor 1)**. Gag, cough and swallow gone | Size normal at first, then **dilate over 1–3 min** as hypoxia develops. Horner's syndrome if the lateral medulla is hit | **"Puppet with cut strings"** |
| **Cervicomedullary junction / C1–C2 cord** | **Preserved if the brain is intact.** The person can be awake (§6) | Apnoea (phrenic nerves disconnected). Jaw, face and neck-accessory "gasps" without airflow | Neurogenic shock (§6.5) | Flaccid quadriplegia. Face, eyes, jaw and tongue still move. Weak shrug (CN XI) | Normal and reactive, then dilate with hypoxia | "Cut strings", but awake |

Sources: Plum & Posner [C19], brain-death physiology [C17] [C18], [K]. Confidence (M) for the table as a whole. The pattern (pinpoint = pons, mid-fixed = midbrain, apnoea = medulla) is (H).

### 2.3 The "cut strings" collapse

- **Tone disappears at once.** Postural muscle tone depends on descending reticulospinal and vestibulospinal drive from the brainstem. When that drive is cut, every antigravity muscle goes slack in well under a second `[K] (H)`.
- **Fall time** `[E]`: in a standing adult, the centre of mass is at ~0.95–1.0 m. Pure free fall of the centre of mass to ~0.15 m takes √(2 × 0.85 / 9.81) = **0.42 s**. Real collapses buckle at the knees and hips and then topple. Use **0.6–1.2 s from hit to ground**.
- **Direction**: the body falls the way it was already leaning or moving. Bullet momentum adds only **0.01–0.18 m/s** of knock-back [D01:S30]. No flying backwards.
- **No protective reflexes.** The arms do not reach out to break the fall. The head hits the ground unprotected (secondary occipital or facial impact). This is the clearest visual difference between a brainstem collapse and a conscious fall `[K] (H)`.
- **Grip**: the hand opens as flexor tone fails. A held weapon drops within ~0.1–0.5 s `[G]`. This is exactly why a destroyed brainstem is treated as the only "no reflexive trigger pull" hit (§2.5).
- **Exception**: when the midbrain or upper pons is hit but the medulla survives, the victim may go into **transient decerebrate extension**. The limbs stiffen, the arms extend and turn inward, and the jaw clenches, for seconds to a minute, and the body topples rigidly (§4) `[K] (M)`.
- **Twitches**: brief myoclonic jerks or small digit and limb movements in the first seconds are plausible. Rare spinal reflex movements can occur for minutes afterwards, because the spinal cord below is still alive (compare the movements seen in brain death [C16]) `[K]`/`[G]`.

### 2.4 Circulation and breathing after brainstem destruction (timeline)

| t_real | Event | t_game | Source |
|---|---|---|---|
| 0 s | Hit. Apnoea (medulla) or abnormal breathing (pons). Collapse within 0.6–1.2 s | 0 s (1×) | [K] (H) |
| 0–60 s | A brief catecholamine surge is possible: HR 120–160, SBP +20–60 mmHg for 10–60 s. Then vasomotor loss: MAP 40–60 mmHg. Wounds still bleed in pulses, now at lower pressure | 1× | [C27] [K] (L–M) |
| 60–120 s | Lips and tongue turn blue if the blood volume is intact. Pupils start to dilate | 1× → 4× | [K] (M) |
| 3–5 min | Hypoxic bradycardia (HR < 40–50). Pulses weaken | 45–75 s at 4× | [K] (M) |
| 4–10 min (default 6) | PEA, then asystole. Bleeding stops pulsing and turns to gravity drainage (§12.2) | 60–150 s at 4× | [K] (M) |

### 2.5 Why marksmen aim for the brainstem (the "T-zone")

- Police and hostage-rescue marksmanship doctrine singles out the brainstem (medulla oblongata and upper cervical cord). Its destruction is the one wound that reliably produces **instant, flaccid incapacitation with no voluntary or reflexive motor activity**, such as a trigger pull `[C48] [K] (M)`.
  - A heart shot does not do this: the target can keep acting for about 10–15 s [C7].
  - A cerebral-hemisphere shot does not reliably do this either (§3).
- **From the front**, the target is a "T". The horizontal bar runs through both eyes along the brow line. The vertical bar runs down the nose to the upper lip. Near-horizontal trajectories through this area pass through the midbrain, pons, medulla and upper cord, which lie in a vertical column along the clivus behind the nasal cavity and nasopharynx `[K] (M)`.
- **From behind**, the target is the midline skull base just below the external occipital protuberance, at the top of the neck `[K] (M)`.
- **From the side**, it lies roughly on the line joining the ear canals, slightly below and in front of it `[K] (L)`.
- "Apricot" is sniper slang for the medulla `[C48] (L)`.
- **Game rule** `[G]`: do not hard-code a T-zone. Resolve the actual bullet path against the brainstem hit volumes (§2.1).
  - Near-misses within ~10–20 mm (the handgun axonal-injury radius of ~18 mm [D01:S25]) should count as concussive brainstem injury: immediate loss of consciousness, impact apnoea (§3.5), and a high chance of apnoea.
  - A higher-energy rifle round disrupts the whole posterior fossa.

### 2.6 Simulation parameters: brainstem

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `midbrain_len` / `pons_len` / `medulla_len` | 15–20 / 25 / 30 | mm | Medulla ~20 wide × 12–13 AP | [C50] [K] (M) |
| `bs_concussive_radius_handgun` | 18 | mm | Near-miss counts as brainstem dysfunction | [D01:S25] (M) |
| `bs_hit_LOC_delay` | 0 | s | Any ballistic midbrain, pontine-tegmentum or medullary hit | [K] (H) |
| `collapse_time` | 0.6–1.2 (floor 0.42) | s | Centre-of-mass drop of 0.85 m | [E] |
| `protective_reflex_on_fall` | false | bool | For brainstem, high-cord and unconscious states | [K] (H) |
| `grip_release_delay` | 0.1–0.5 | s | Weapon drops | [G] |
| `medulla_apnoea` | immediate, no gasps | — | Pontine-only hit: apneustic/ataxic breathing for 0–5 min, then apnoea | [K] (M) |
| `bs_catecholamine_surge` | p = 0.5. HR 120–160, SBP +20–60 for 10–60 s | — | Optional flourish | [C27] [K] (L) |
| `map_after_vasomotor_loss` | 40–60 (default 50) | mmHg | Medullary destruction | [K] (M) |
| `hr_after_medulla_loss` | 118.1 − 0.57 × age | bpm | Until hypoxic bradycardia | [C36] (M) |
| `apnoea_to_cyanosis` | 60–120 | s | Only if Hb is adequate (see §1) | [K] (M) |
| `apnoea_to_bradycardia` | 180–300 | s | HR < 40–50 | [K] (M) |
| `apnoea_to_arrest` | 240–600 (default 360) | s | PEA, then asystole | [K] (M) |
| `pupil_midbrain_hit` | 4–6, fixed, often unequal | mm | Immediate | [C19] [C17] (H) |
| `pupil_pontine_hit` | 1–2 | mm | Pinpoint. Dilate later with hypoxia | [C19] (H) |
| `decerebrate_prob_midbrain_hit` | 0.3–0.6 | p | Episodes of 5–60 s | [G] on [K] |
| `spinal_twitch_prob_first_30s` | 0.2 | p | Small digit or limb jerks | [G] |
| `locked_in_prob_ventral_pons_lowenergy` | ≤ 0.05 | p | Awake, only vertical eyes and blinks | [G] on [C19] |
| Game time | 0–60 s at 1×, then 4× | — | Death shown in about 2–3 min of play | [G] |

### Visual/behavioural checklist: brainstem
- The body drops straight down and crumples at the knees and hips within about a second. The arms do not break the fall. The head bounces off the floor. A held weapon slips from the hand.
- No breathing movement at all after a medullary hit. No chest rise, no gasps, no sounds from the airway except air forced out passively on impact. With a pontine-only hit, show a few strange breaths (long held inspirations, irregular clusters) before they stop.
- Eyes: lids stay where they were (usually open) and droop slightly. Eyes look slightly divergent or skewed and do not move. The pupils are mid-sized and fixed (midbrain) or pinpoint (pons). No blinking, ever again.
- Wounds keep bleeding in pulses for a few minutes, getting weaker as BP falls. Lips turn dusky blue over 1–2 min unless the victim has also bled heavily.
- Rare variant: a stiff, arched extension (arms straight and turned in, legs straight, feet pointed) lasting seconds, then slackness.
- Audio: impact thud, possibly a short passive exhalation. No gasping after a medullary hit.

---

## 3. Cerebral hemisphere wounds vs brainstem, concussion and knockout

### 3.1 The core rule
- Consciousness needs the **ascending reticular activating system** (upper pons, midbrain, thalamus) **plus** working cortex in the hemispheres. **A lesion confined to one hemisphere does not by itself cause coma.** Coma follows only if the damage is bilateral or diencephalic, or if mass effect compresses the brainstem (herniation, §5) [C19] `(H)`.
- So a penetrating wound that stays in one hemisphere, especially the frontal lobe, **can leave the victim conscious, moving and even acting**. Collapse then comes from concussion, shock, blood loss or later swelling, not from the track itself.

### 3.2 Evidence
- **Retained capacity to act** after penetrating head shots: **53 documented cases**. **More than 70%** involved slow, light bullets (6.35 mm, .22 rimfire). Frontal tracks were common, protected by the anterior skull base, and the brainstem was spared [D01:S26] `(M)`.
- **Mortality**: 70–90% of penetrating head wounds die before reaching hospital, with overall mortality ~91%. **Wounds crossing both hemispheres carry ~82% mortality** and about four times the odds of death of single-hemisphere wounds [D01:S43] `(M)`.
- **Early respiratory arrest** after low-velocity head shots may come from remote axonal injury in the brainstem, even without a direct hit [D01:S25] `(M)`.
- Historical illustration: Phineas Gage (1848) survived an iron bar through the left frontal lobe and was talking within minutes `[K] (H)`.

### 3.3 What a person with a hemisphere wound looks like, by region

| Track through | Immediate picture if conscious | Motor | Eyes | Source |
|---|---|---|---|---|
| Prefrontal (one side) | Dazed, confused, may keep walking or talking. Personality and judgement abnormal. Vomiting possible | Little or none | Normal. **Bilateral blindness** if the track crosses both optic nerves or the chiasm (a temple-to-temple shot through the orbits) | [K] (M) |
| Motor strip or internal capsule | Aware. Falls **toward the paralysed side** | **Contralateral hemiplegia**, flaccid at first: arm hangs, leg gives way, lower face droops | **Gaze deviation toward the lesion** (away from the paralysed side) | [C19] (H) |
| Left (dominant) hemisphere | **Aphasia**: cannot speak, or speaks nonsense, or cannot understand. Right hemiplegia | Right side | Deviate left | [K] (H) |
| Right hemisphere | Ignores the left side (neglect). May deny the deficit. Left hemiplegia | Left side | Deviate right | [K] (H) |
| Occipital | Sudden blindness in the opposite visual field (or complete cortical blindness if bilateral). May not realise | None | Pupils still react to light (cortical blindness) | [K] (H) |
| Temporal | Aphasia if left-sided. **Seizure risk**. An expanding haematoma here leads to **uncal herniation** (§5) | Variable | Later: ipsilateral dilated pupil | [K] (H) |
| Cerebellum | Vertigo, vomiting, staggering, nystagmus | Ataxia on the same side | Nystagmus. Brainstem compression risk within minutes to hours | [K] (H) |
| Thalamus or deep midline (diencephalon) | **Coma is likely** | Variable | **Eyes deviated down and in** ("peering at the nose"). Small reactive pupils | [C19] (M) |
| Across the midline, transventricular, or posterior fossa | Coma, high mortality | Posturing or flaccid | Depends on brainstem involvement | [D01:S43] [K] (M) |

### 3.4 Loss of tone without a brainstem hit
Even a unilateral hemisphere wound usually causes **immediate collapse** from:
- **concussion**: the shock and cavitation pressure wave reach the brainstem;
- **impact brain apnoea** (§3.5);
- the startle and syncope response.

The victim may then **wake within seconds to minutes** with the focal deficits in the table above `[K] (M)`.

### 3.5 Impact brain apnoea (IBA)
- A head impact can cause **immediate apnoea** plus a **catecholamine surge** (brief hypertension and tachycardia), followed by hypotension. **If no one ventilates the victim, the apnoea alone can cause hypoxic cardiac arrest**, even when the brain injury itself would have been survivable [C26] [C27] `(M)`.
- Apnoea duration scales with impact energy: from seconds after a knockout to minutes after severe TBI `[K] (L)`.

### 3.6 Knockout and concussion (fist, hammer, falls)
- **LOC** is immediate. After sports knockouts it usually lasts **seconds to about 1 min**. Loss of consciousness **> 30 min** means at least moderate TBI (GCS 9–12 by definition) `[K] (H)`.
- **Fencing response**: at the moment of impact the forearms go into a **tonic, unnatural posture**. One arm is extended, often stiffly raised, and the other is flexed, like the asymmetric tonic neck reflex. It lasts **several seconds** while the person is unconscious and then releases. It was seen in **about two-thirds of analysed knockout videos**. It is attributed to brainstem (lateral vestibular nucleus) activation and marks moderate-force injury [C20] `(M)`.
  - Default duration 2–10 s, maximum ~20 s `[G]`.
- **Concussive convulsion**: about **1 in 70** sport concussions [C21] `(M)`.
  - Tonic stiffening starts **within ~2 s** of impact and can last up to ~20 s. Myoclonic or clonic jerks follow for up to **~2–3 min** [C21] `(L–M)`.
  - It is non-epileptic and benign.
- **Airway**: an unconscious person lying on their back snores (stertor) as the tongue falls back. They may vomit and aspirate `[K] (H)`.
- **Recovery**: eyes open first. Then a dazed stare, confusion, repeated questions, amnesia for the event, unsteadiness and nausea for **5–30 min** `[K] (M)`.

### 3.7 Simulation parameters: hemisphere, concussion, knockout

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hemi_conscious_after_prob` (unilateral, low-energy, not crossing the midline or the diencephalon) | 0.10–0.30 | p | Probability the character is awake at 10 s | [G] on [D01:S26] |
| `capacity_to_act_prob` (low-energy frontal) | 0.05–0.15. Otherwise ~0 | p | Can walk, talk, or use hands purposefully | [D01:S26] (qual.), [G] |
| `hemi_transient_LOC` | 5–120 | s | Concussive collapse, then wakes with deficits | [G] on [K] |
| `contralateral_hemiplegia` | flaccid from the moment of injury | — | If the track crosses the motor strip or internal capsule | [K] (H) |
| `gaze_deviation_hemi` | 15–40, toward the lesion | ° (both eyes, conjugate) | Head often turned the same way | [C19] (M) |
| `impact_apnoea_prob` | KO 0.1; moderate TBI 0.3; severe or penetrating 0.6 | p | Duration below | [G] on [C26] |
| `impact_apnoea_duration` | KO 5–30 s; severe 30 s – 5 min | s | Hypoxic arrest if longer than ~4–6 min | [C26] [K] (L) |
| `KO_LOC_duration` | 5–60 (tail to 300) | s | | [K] (M) |
| `fencing_prob_on_KO` | 0.66 | p | | [C20] (M) |
| `fencing_duration` | 2–10 (max 20) | s | Arm on the face side extended, other arm flexed | [C20] (L–M), [G] |
| `concussive_convulsion_prob` | 0.014 | p | ~1 in 70 | [C21] (M) |
| `concussive_convulsion_phases` | tonic ≤ 20 s, then clonic ≤ 150 s | s | Begins within 2 s | [C21] (L–M) |
| `post_KO_confusion` | 5–30 | min | Compress 4× in game | [K] (M) |
| Game time | Knockout and fencing at 1×. Confusion phase at 4× | — | | [G] |

### Visual/behavioural checklist: hemisphere and knockout
- A small-calibre shot to one side of the forehead sometimes does **not** drop the character. It may stagger, clutch its head, turn, speak confusedly, then sit or fall minutes later as bleeding and swelling progress.
- A hemisphere wound through motor areas: one arm hangs and the same-side leg buckles. The character falls toward that side and cannot get up on it. The mouth droops on that side. The **eyes and head turn toward the wounded side** of the brain.
- A left-sided wound: slurred or nonsense speech, or silence despite being awake.
- A punch knockout: an instant stiff fall with **one arm extended up and forward, the other bent** for a few seconds (fencing response), then slack. Snoring breaths. Eyes open within seconds to a minute, unfocused.
- Rarely, a punch knockout is followed by seconds of stiffening and then jerking (concussive convulsion), and the character recovers.

---

## 4. Posturing and seizures

### 4.1 Motor response by lesion level (GCS motor score)

| GCS motor | Response | Lesion level it indicates | Appearance | Source |
|---|---|---|---|---|
| M6 | Obeys commands | Conscious | — | [K] (H) |
| M5 | Localises pain | Cortex working | Hand moves to the stimulus | [K] (H) |
| M4 | Normal flexion (withdrawal) | | Limb pulls away | [K] (H) |
| **M3** | **Abnormal flexion: decorticate** | Above the red nucleus: cerebral hemispheres, internal capsule, thalamus | **Arms**: shoulders adducted, elbows, wrists and fingers flexed, fists on the chest. **Legs**: extended and internally rotated, feet plantar-flexed | [C19] [K] (H) |
| **M2** | **Extension: decerebrate** | Midbrain or upper pons: below the red nucleus, above the vestibular nuclei | **Arms**: extended at the elbows, adducted, **internally rotated/pronated**, wrists and fingers flexed. **Legs**: extended, feet plantar-flexed and inverted. Jaw clenched. Neck extended; opisthotonus (arched back) when severe | [C19] [K] (H) |
| **M1** | **None: flaccid** | Lower pons, medulla, or upper cervical cord | Limp | [C19] (H) |

- Posturing is often **episodic and triggered by stimuli** (pain, moving the patient, loud noise). It can be **asymmetric**, for example decorticate on one side and decerebrate on the other `[K] (H)`.
- As herniation progresses (§5), the pattern typically moves from **decorticate to decerebrate to flaccid**. Decerebrate carries a worse prognosis than decorticate `[K] (H)`.
- Posturing can appear **immediately** after severe TBI, or **minutes to hours later** as ICP rises `[K] (M)`.
- The **fencing response** (§3.6) is a separate, brief tonic posture at the moment of impact in otherwise moderate injuries.

### 4.2 Seizures after head injury
- **Impact seizures** occur within seconds of injury. **Early post-traumatic seizures** occur within 7 days: overall ~2–6% after TBI, **~10–15% after severe TBI, and higher after penetrating injury** [C25] `(M)`.
- **Generalised tonic-clonic seizure (GTC)** [C22] [C23] `(M)`:
  - **Tonic phase: ~10–20 s.** The body stiffens. The arms flex then extend, the legs extend and the back arches. A forced **"epileptic cry"** is pushed out through a closed glottis. Breathing stops, cyanosis follows, and the jaw clenches, often biting the side of the tongue.
  - **Clonic phase: ~30–60 s.** Rhythmic, symmetric jerks whose frequency slows and then stops.
  - **Total: typically ~1 min, usually under 2 min.** Over 5 min counts as status epilepticus `[K] (H)`.
  - During the seizure the **eyes are open in the great majority of epileptic seizures**. They are closed in most *psychogenic* episodes [C24] `(M)`. The eyes deviate up or to one side. Pupils are dilated and unreactive during the seizure `[K] (M)`.
  - **Autonomic**: HR 120–160, BP rises, sweating, salivation (bloody froth if the tongue is bitten), possible urinary incontinence `[K] (M)`.
  - **Postictal**: flaccid, deeply unresponsive, loud **stertorous breathing** (snoring, gurgling) for minutes. Confusion for 10–30 min `[K] (M)`.
- A seizure from a focal cortical wound often begins with **head and eye turning away from the injured hemisphere** (the opposite of the gaze deviation seen with a destructive lesion) `[C19] (M)`.

### 4.3 Simulation parameters: posturing and seizures

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `posture_decorticate_trigger` | bilateral hemisphere, thalamus or internal-capsule damage; or early herniation stage | — | GCS M3 | [C19] (H) |
| `posture_decerebrate_trigger` | midbrain or upper pons damage or compression | — | GCS M2 | [C19] (H) |
| `posture_flaccid_trigger` | medulla, lower pons, or high cord | — | GCS M1 | [C19] (H) |
| `posture_episode_duration` | 5–60 | s | Repeats every 30 s – 5 min, or on stimulus | [G] on [K] |
| `posture_onset` | immediate (severe TBI) to minutes–hours (rising ICP) | — | | [K] (M) |
| `posture_joint_targets_decerebrate` | elbow 0–10° flexion, forearm full pronation, wrist 60–80° flexion, knee 0°, ankle 30–45° plantar flexion, neck 10–30° extension | ° | Ragdoll drive targets, strength 60–80% | [G] on [K] |
| `posture_joint_targets_decorticate` | shoulder adducted, elbow 90–120° flexion, wrist 60–80° flexion, fist; legs as decerebrate | ° | | [G] on [K] |
| `early_PTS_prob` (severe blunt / penetrating) | 0.10–0.15 / 0.2 | p | "Immediate" impact seizure ≈ 0.02–0.05 | [C25] (M), [G] |
| `GTC_tonic` / `GTC_clonic` / `GTC_total` | 10–20 / 30–60 / ~60 (30–120) | s | | [C22] [C23] (M) |
| `GTC_clonic_freq` | 3–4 Hz falling to ~1 Hz | Hz | | [K] (L) |
| `status_threshold` | 5 | min | | [K] (H) |
| `postictal_unresponsive` | 2–20 | min | Stertorous breathing | [K] (M) |
| `GTC_eyes_open_prob` | ~0.9–0.97 | p | | [C24] (M) |
| `GTC_HR` | 120–160 | bpm | | [K] (M) |
| `tongue_bite_prob` / `urinary_incontinence_prob` | 0.2–0.4 / 0.2–0.4 | p | Side of the tongue | [K] (L–M) |
| Game time | 1× (seizures are short) | — | Postictal at 4× | [G] |

### Visual/behavioural checklist: posturing and seizures
- Decorticate: arms pulled up onto the chest with fists and flexed wrists, legs straight, toes pointed.
- Decerebrate: arms rigidly straight at the sides, turned inward (backs of the hands facing each other or forward), wrists bent, legs straight, jaw clenched, head pushed back. It comes in spasms when the body is touched or moved.
- A seizure: a guttural cry, then the whole body rigid and arched for 10–20 s with the eyes open and turned up or to one side. Then rhythmic jerking that slows and stops within about a minute. Pink froth at the lips, blue lips. Afterwards limp, with loud snoring breaths and eyes half-closed.
- Audio: epileptic cry (forced groan), jaw clacking, snoring and gurgling postictal breathing.

<!-- CHUNK2 -->
