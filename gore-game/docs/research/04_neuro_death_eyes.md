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
- **Independent fact-check pass (2026-09-26), see §18.** Web access was again unavailable: WebSearch budget exhausted, and WebFetch `EGRESS_BLOCKED` on 14 domains. So the fact-checker could not open any source. Engineering derivations were recomputed and are marked **✓ verified (arithmetic)**. Values that match the fact-checker's independent recall are marked **≈ recall-consistent (not web-verified)**. Errors are marked **corrected: was X**.
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
- **Pressures** are in mmHg (1 mmHg = 133.3 Pa). A 1 cm column of blood (ρ ≈ 1,060 kg/m³) = **0.78 mmHg** `[E]`. ✓ verified (arithmetic: 1,060 × 9.81 × 0.01 = 104 Pa = 0.780 mmHg).
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
| Blood volume | 70 (male), 65 (female) | mL/kg | ≈ 7% of body weight. Reference body: **5,250 mL**. ≈ recall-consistent (not web-verified). ATLS gives only the "~7% of body weight" figure; 65 mL/kg for women is a general textbook value | [C1] [K] (H) |
| Cardiac output at rest | 5 (4–6) | L/min | HR 60–80 × SV ~70 mL | [K] (H) |
| Normal BP / MAP | 120/80 / 93 | mmHg | MAP ≈ DBP + (SBP − DBP)/3 | [K] (H) |
| Intrinsic (denervated) heart rate | 118.1 − 0.57 × age | bpm | ≈ 101 bpm at 30 y. The rate the heart keeps after the medulla is destroyed, until hypoxia slows it. ≈ recall-consistent (Jose & Collison formula); ✓ verified (arithmetic): 118.1 − 17.1 = 101 | [C36] (M) |
| Brain mass | 1,300–1,400 | g | | [K] (H) |
| Cerebral blood flow (CBF) | 50 | mL/100 g/min | ≈ 700–750 mL/min, ~15% of cardiac output | [K] (H) |
| Brain O₂ consumption | 3.3–3.5 | mL O₂/100 g/min | ≈ 45–50 mL/min, ~20% of whole-body O₂ | [K] (H) |
| CBF at which function fails | < 20 | mL/100 g/min | EEG slows, then goes silent. Membrane failure and infarction below ~10 | [K] (H) |
| Autoregulation lower limit | MAP 50–60 (up to 70) | mmHg | Below this, CBF follows MAP passively | [K] (M) |
| Time to unconsciousness after complete stop of brain blood flow | 5–10 (mean ~6.8) | s | Neck-cuff occlusion experiments. ≈ recall-consistent. The ESC syncope guideline (recall) similarly gives 6–10 s of cerebral flow cessation for complete loss of consciousness | [C9] (H) |
| "Functional buffer" (G-LOC) | ~5–6 | s | Oxygen reserve after cerebral flow stops | [C10] (M) |
| Voluntary action possible after the heart is destroyed | 10–15 | s | Classic FBI wound-ballistics figure. ≈ recall-consistent. It is doctrine (an upper envelope), not a measured series; the physiology in [C9] supports ~5–10 s once cerebral flow is truly zero | [C7] [C8] (M–H) |
| EEG isoelectric after circulatory arrest | 10–40 (typ. ~20) | s | ≈ recall-consistent | [K] (M) |
| Onset of irreversible neuronal injury, normothermic arrest | 4–6 | min | Cortex first; brainstem more tolerant. ≈ recall-consistent | [K] (H) |
| Intracranial pressure (ICP), normal | 5–15 | mmHg | Supine adult. Default 10. ≈ recall-consistent (7–15 is also commonly quoted) | [K] (H) |
| ICP treatment threshold (TBI guidelines) | > 22 | mmHg | ≈ recall-consistent (BTF 4th ed.) | [C28] (H) |
| Cerebral perfusion pressure | CPP = MAP − ICP. Normal 60–80. Ischaemia < 50 | mmHg | If ICP ≥ MAP, cerebral circulation stops | [K] (H) |
| Pressure–volume index (PVI) | 25 (20–30) | mL | Volume that raises ICP ten-fold on the steep part of the curve | [C30] (M) |
| CSF production | 0.35 | mL/min | ≈ 500 mL/day. CSF volume ~150 mL | [K] (H) |
| Resting respiration | RR 12–20/min, tidal volume ~500 mL, VO₂ ~250 mL/min | — | | [K] (H) |
| O₂ stores breathing room air | ~1.5 | L | Lungs ~0.4–0.5 L, blood ~0.8–0.9 L | [K] (M) |
| Apnoea on room air: SpO₂ < 90% | 60–90 (faster when struggling) | s | | [K] (M) |
| Apnoea: hypoxic loss of consciousness | 1.5–3 | min | Circulation intact | [K] (M) |
| Apnoea: cardiac arrest | 4–10 (default 6) | min | Hypoxic bradycardia → PEA/asystole | [K] (M) |
| Central cyanosis visible | deoxy-Hb ≥ ~5 g/dL | — | **Needs enough haemoglobin.** An exsanguinated body turns grey-white, not blue | [K] (H) |
| Mean systemic filling pressure after arrest | ~7 (classic) to ~13 (human ICU measurements) | mmHg | Pressure that arteries and veins equalise to within about a minute of arrest. ≈ recall-consistent: Guyton's ~7 mmHg comes from animal work; human post-mortem measurements are ~10–15 mmHg. Not web-verified | [C51] [C52] (M) |
| Arterial jet exit speed | v = √(2ΔP/ρ): 120 mmHg → **5.5 m/s** | m/s | Ideal jet height 1.54 m. Real jets **0.3–1.5 m** after friction, wound shape and vessel spasm. ✓ verified (arithmetic): 120 mmHg = 15,996 Pa; √(2 × 15,996 / 1,060) = 5.49 m/s; 15,996 / (1,060 × 9.81) = 1.54 m. The 0.3–1.5 m real range is unverified | [E] |

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
| `medulla_apnoea` | immediate, no gasps | — | Pontine-only hit: apneustic/ataxic breathing for 0–5 min, then apnoea. ≈ recall-consistent: the respiratory rhythm and gasp generators (pre-Bötzinger complex) are medullary | [K] (M) |
| `bs_catecholamine_surge` | p = 0.5. HR 120–160, SBP +20–60 for 10–60 s | — | Optional flourish | [C27] [K] (L) |
| `map_after_vasomotor_loss` | 40–60 (default 50) | mmHg | Medullary destruction. Plausible (hypotension after brain death is common), but no source was retrieved; not web-verified | [K] (M) |
| `hr_after_medulla_loss` | 118.1 − 0.57 × age | bpm | Until hypoxic bradycardia | [C36] (M) |
| `apnoea_to_cyanosis` | 60–120 | s | Only if Hb is adequate (see §1) | [K] (M) |
| `apnoea_to_bradycardia` | 180–300 | s | HR < 40–50 | [K] (M) |
| `apnoea_to_arrest` | 240–600 (default 360) | s | PEA, then asystole. Not web-verified; plausible order of magnitude | [K] (M) |
| `pupil_midbrain_hit` | 4–6, fixed, often unequal | mm | Immediate. ≈ recall-consistent. Plum & Posner distinguish nuclear midbrain lesions (mid-position, ~4–5 mm, fixed, often irregular) from pretectal lesions (slightly larger, ~5–6 mm, fixed, may show hippus) | [C19] [C17] (H) |
| `pupil_pontine_hit` | 1–2 | mm | Pinpoint. Dilate later with hypoxia. ≈ recall-consistent | [C19] (H) |
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
- **LOC** is immediate. After sports knockouts it usually lasts **seconds to about 1 min**. Loss of consciousness **> 30 min** means at least moderate TBI `[K] (H)`. *corrected: was "(GCS 9–12 by definition)". In the usual severity schemes (e.g. VA/DoD), LOC > 30 min and GCS 9–12 are separate, parallel criteria for "moderate"; one does not define the other (recall, not web-verified).*
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
| `fencing_prob_on_KO` | 0.66 | p | ≈ recall-consistent ("two-thirds of knockouts") | [C20] (M) |
| `fencing_duration` | 2–10 (max 20) | s | Arm on the face side extended, other arm flexed. The source says "several seconds". The 20 s maximum is [G] | [C20] (L–M), [G] |
| `concussive_convulsion_prob` | 0.014 | p | ~1 in 70. ≈ recall-consistent | [C21] (M) |
| `concussive_convulsion_phases` | tonic ≤ 20 s, then clonic ≤ 150 s | s | Begins within 2 s. ≈ recall-consistent (tonic phase up to ~20 s; jerks up to ~2–3 min) | [C21] (L–M) |
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

---

## 5. Raised intracranial pressure, herniation, Cushing's triad, breathing patterns

### 5.1 The volume model (Monro–Kellie)
- Skull contents: brain ~1,400 mL (~80%), blood ~150 mL (~10%), CSF ~150 mL (~10%). A new mass (haematoma, swelling) is first **compensated** by pushing CSF into the spinal sac and squeezing venous blood out. After that, ICP rises **exponentially** `[K] (H)` [C30].
- **Suggested game model** `[E]`/`[G]`:
  - `ΔV ≤ V_c`: ICP rises linearly from 10 to ~20 mmHg. `V_c` = **30–60 mL** (default 40; smaller in young brains).
  - `ΔV > V_c`: `ICP = 20 × 10^((ΔV − V_c) / PVI)`, with `PVI` = 25 mL [C30].
  - Worked example (V_c = 40): ΔV = 50 mL gives ICP ≈ 50 mmHg. ΔV = 60 mL gives ICP ≈ 126 mmHg, which exceeds MAP, so **cerebral circulation stops and the brainstem dies**. ✓ verified (arithmetic): 20 × 10^(10/25) = 50.2; 20 × 10^(20/25) = 126.2.
  - CSF absorption offsets growth by ≤ 0.35 mL/min.
- **Surgical thresholds** (they show which volumes matter clinically) [C29] `(H)`:
  - Epidural haematoma (EDH) **> 30 mL** is evacuated whatever the GCS. ≈ recall-consistent.
    - Also from [C29] (recall): an EDH < 30 mL, < 15 mm thick, with < 5 mm midline shift, GCS > 8 and no focal deficit can be observed without surgery.
  - Acute subdural **> 10 mm thick, or midline shift > 5 mm**, is evacuated. ≈ recall-consistent.
- **Haematoma growth rates** `[G]` (clinically plausible, no single source):
  - Arterial EDH (middle meningeal artery, from a temporal hammer blow): **0.3–2 mL/min**.
  - Bleeding along a bullet track in the brain: 10–50 mL over the first 5–30 min.
  - Acute subdural: 0.2–1 mL/min, usually with an immediate coma from the underlying brain injury.

### 5.2 Herniation syndromes (sequence the state machine should play)

| Syndrome | Cause | Sequence of signs | Source |
|---|---|---|---|
| **Uncal (lateral)** | Temporal or lateral mass (EDH, temporal contusion) | 1. **Ipsilateral pupil enlarges**, sluggish then fixed ("blown", 6–9 mm), ptosis; eye drifts **down and out**. 2. Consciousness falls. 3. Contralateral hemiparesis (or ipsilateral via Kernohan's notch, a false-localising sign). 4. Decerebrate posturing. 5. Both pupils fixed. 6. Breathing: Cheyne–Stokes → hyperventilation → ataxic → apnoea | [C19] (H) |
| **Central (transtentorial)** | Diffuse swelling or midline mass | Diencephalic stage: small reactive pupils, Cheyne–Stokes, decorticate. Midbrain stage: **mid-position fixed pupils**, decerebrate, central hyperventilation. Pontine and medullary stages: flaccid, ataxic breathing, apnoea | [C19] (H) |
| **Tonsillar (foramen magnum)** | Posterior-fossa mass or bleed | **Sudden apnoea and cardiovascular collapse, sometimes with little warning.** Neck stiffness, head tilt | [C19] (H) |
| Subfalcine | Frontal or parietal mass | Leg weakness (anterior cerebral artery compression). Often precedes the others | [K] (M) |

### 5.3 Cushing's triad
- **Hypertension with a widening pulse pressure** (SBP rising to 160–220+ mmHg), **bradycardia** (HR 40–60, sometimes lower) and **irregular breathing** [C31] `(H)`.
- **Mechanism**: as CPP collapses, brainstem ischaemia triggers a sympathetic surge that raises the BP to force blood into the brain. The baroreflex (plus direct brainstem compression) slows the heart.
- It is a **late, pre-terminal sign** of imminent herniation. The complete triad is seen in only a minority, roughly a third, of patients with critical ICP `[K] (L)`.
- **Game**: show the triad for **5–30 min real** (1–3 min at 10×) before bilateral fixed pupils and apnoea `[G]`.

### 5.4 Epidural haematoma: the "talk and die" timeline (hammer to the temple)

| t_real | Event | t_game (15×) | Source |
|---|---|---|---|
| 0 | Blow. Brief knockout (seconds–minutes), or no knockout | 1× for the first 60 s | [K] (H) |
| 1 min – several h | **Lucid interval** in ~20–50% of EDH: awake, headache, vomiting, may walk and talk | 0–15 min | [K] (M) |
| + 15–60 min | Drowsy and confused. Ipsilateral pupil enlarges. Contralateral weakness | 1–4 min | [C19] (H) sequence, [K] timing (L) |
| + 5–30 min | Coma. Decerebrate posturing. **Cushing's triad**. Irregular breathing | 20 s – 2 min | [C19] [C31] |
| + 5–20 min | Bilateral fixed dilated pupils. Apnoea. Hypoxic arrest 4–10 min later | 20 s – 1.5 min | [K] (M) |

Typical real total from the blow to death if untreated: **1–6 h** (default 2 h), shown in about 8–12 min of game time `[K] (L–M)`, `[G]`.

### 5.5 Breathing patterns by level (for audio and chest animation)

| Pattern | Level | Rate / rhythm | Look and sound | Source |
|---|---|---|---|---|
| Normal | — | 12–20/min, regular | Quiet | [K] (H) |
| **Cheyne–Stokes** | Both hemispheres or diencephalon; early herniation | Crescendo–decrescendo cycles, **period ~40–90 s**, with an apnoeic pause of 10–30 s | Breaths build to deep sighs, fade, then silence | [C19] (M) |
| **Central neurogenic hyperventilation** | Midbrain / upper pons | **25–40+/min**, deep, regular | Machine-like panting | [C19] (M) |
| **Apneustic** | Mid/lower pons | Long **inspiratory hold of 2–3 s** at full inspiration | Gasp in, hold, release | [C19] (M) |
| Cluster | Lower pons / upper medulla | Irregular clusters of breaths with pauses | Uneven | [C19] (M) |
| **Ataxic (Biot)** | Medulla | Random depth and timing, often slow (4–12/min) | Chaotic, **pre-terminal** | [C19] (M) |
| **Agonal gasping** | Medullary gasp centre, with the cortex off | 2–10/min, abrupt, deep, with **neck extension and jaw opening** | Snort, snore, gurgle. See §10 | [C12] [C13] (M) |
| Apnoea | Medulla destroyed or failed | 0 | Silence | [K] (H) |
| Stertor | Unconscious, airway partly obstructed by the tongue | Any | Loud snoring | [K] (H) |

### 5.6 Simulation parameters: ICP and herniation

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `icp0` | 10 (5–15) | mmHg | | [K] (H) |
| `icp_compensated_volume` | 30–60 (default 40) | mL | Linear to ~20 mmHg | [G]/[E] |
| `pvi` | 25 (20–30) | mL | Exponential phase. ≈ recall-consistent (normal adult PVI ~25–30 mL) | [C30] (M) |
| `csf_absorption_max` | 0.35 | mL/min | Offsets growth | [K] (H) |
| `edh_growth` | 0.3–2 (default 0.6) | mL/min | Arterial EDH. Stop growth at 150 mL | [G] |
| `edh_lucid_interval_prob` | 0.2–0.5 | p | | [K] (M) |
| `herniation_start_icp` | ≥ 30–40, or CPP < 50 | mmHg | Start the uncal or central sequence | [K]/[G] |
| `blown_pupil` | 6–9, fixed | mm | Ipsilateral first; the other follows within minutes to an hour | [C19] (H), timing [K] (L) |
| `cushing_sbp` / `cushing_hr` | 160–220 / 40–60 | mmHg / bpm | Late, ~5–30 min before apnoea. The triad and "late sign" are ≈ recall-consistent. The numeric SBP/HR bands are illustrative and not from a guideline | [C31] (H), numbers and timing [K]/[G] (L) |
| `cushing_full_triad_prob` | ~0.33 | p | ≈ recall-consistent ("about one-third"); not web-verified | [K] (L) |
| `cheyne_stokes_period` | 40–90 | s | Apnoea 10–30 s | [C19] (M) |
| `cnh_rr` | 25–40 | /min | | [C19] (M) |
| `apneustic_hold` | 2–3 | s | | [C19] (M) |
| `ataxic_rr` | 4–12, random | /min | | [C19] (L) |
| `cerebral_circ_arrest` | ICP ≥ MAP | — | Brainstem death, then hypoxic cardiac arrest in 4–10 min | [K] (H) |
| Game time | 10–30× in the lucid and deterioration phases. 1× in the final 60 s | — | | [G] |

### Visual/behavioural checklist: raised ICP
- After a temple blow, the character may get up, talk and seem fine. Then it vomits, complains of headache, becomes drowsy, and one pupil grows larger than the other.
- It stops responding. One eye drifts down and out with a drooping lid. The arms go into decorticate and then decerebrate spasms. Breathing becomes irregular: waxing and waning, then fast panting, then chaotic, then stops.
- Just before the end: a bounding, **slow** pulse (40–50 bpm) with high BP, flushed face, both pupils wide and fixed.
- Audio: vomiting, moaning, then Cheyne–Stokes sighs with silent gaps, then silence.

---

## 6. Spinal cord injury by level

### 6.1 Anatomy and mapping

| Quantity | Value | Notes | Source |
|---|---|---|---|
| Cord length | 42–45 cm (male), ~43 cm (female) | From the foramen magnum to the conus | [C50] [K] (M) |
| Cord end (conus medullaris) | **L1–L2** disc (adult range T12–L3) | Below this only the cauda equina (nerve roots). ≈ recall-consistent | [K] (H) |
| Cord cross-section | Cervical enlargement (C4–T1) ~13–14 mm wide × 7–9 mm AP. Thoracic ~8–10 × 6–8 mm | For hit volumes | [C50] [K] (M) |
| Spinal canal AP diameter | Cervical ~14–20 (mean ~17). Thoracic ~13–16. Lumbar 15–25 | mm | [K] (M) |
| Vertebra → cord segment | Cervical: segment ≈ vertebra + 1. Upper thoracic: + 2. T7–T9: + 3. T10–T12 vertebrae hold the lumbar and upper sacral segments. L1 vertebra holds the conus | So a bullet through the T12 vertebra injures the L-segments or conus | [K] (M) |
| Phrenic nerve | **C3, C4, C5** ("C3, 4, 5 keeps the diaphragm alive"). C4 is the main root | Diaphragm. ≈ recall-consistent | [K] (H) |
| Sympathetic outflow | T1–L2. Cardiac accelerator fibres T1–T4 | Above T6: neurogenic shock likely | [K] (H) |

### 6.2 Complete injury by level

| Level | Breathing (acute VC, % predicted) | Voice / cough | Arms and hands | Trunk and legs | Autonomic | What the player sees in the first minutes | Without help | Source |
|---|---|---|---|---|---|---|---|---|
| **C1–C3** | **Apnoea** (C3: at most a trace of diaphragm). VC 0–10% | **No voice** (no airflow). Can mouth words. No cough | None. Weak shrug and head turn (CN XI: SCM, trapezius) | None | Neurogenic shock (bradycardia, hypotension) | Instant flaccid collapse. **Awake if the brain is intact**: eyes open, darting, face contorted, jaw and neck straining in silent gasps. Lips blue by 1–2 min. Unconscious at 1.5–3 min | **Death in 4–10 min** | [C32] [K] (H) |
| **C4** | Diaphragm partly working. VC ~20–30% | Weak voice, short phrases. Cough ineffective | Shrug only | None | Neurogenic shock likely | **Paradoxical ("see-saw") breathing**: the belly rises while the upper chest sinks. Fast shallow breaths. Anxious | Respiratory fatigue over hours. Cord swelling can climb 1–2 levels over 24–72 h | [K] (M) |
| **C5** | Diaphragm intact. Intercostals and abdominals lost. VC ~25–40% | Soft voice, weak cough | Deltoid and biceps: shoulder abduction and **elbow flexion only**. Wrists and hands limp | None | Neurogenic shock common | Collapses. Can bend the elbows and lift the shoulders. Attempted movement gives flexed elbows with supinated, limp hands | Survives acutely | [C32] [K] (H) |
| **C6** | As C5. VC ~30–50% | Soft | + **wrist extension** (tenodesis: passive finger curl as the wrist extends), supination | None | As above | Can lift the wrists | Survives | [C32] (H) |
| **C7** | VC ~40–60% | Fair | + **triceps** (elbow extension), finger extension | None | As above | Can push up weakly on the arms | Survives | [C32] (H) |
| **C8** | As C7 | Fair | + **finger flexion (grip)** | None | Neurogenic shock less often | Can grasp. Hand fine movements weak | Survives | [C32] (H) |
| **T1** | VC ~50–70% | Normal voice, weak cough | Full arms and hands | No trunk or leg function | | Arms normal, legs flaccid, no trunk balance | Survives | [C32] (H) |
| **T2–T6** | Intercostals partly lost. VC ~50–75% | Weak cough | Full | Poor trunk control. Legs flaccid | **At or above T6: neurogenic shock possible** | Falls, then props up on the arms. Cannot sit unsupported | Survives | [K] (M) |
| **T7–T12** | Abdominals partly lost. VC ~70–90% | Near normal | Full | Better trunk control. Legs flaccid | Mild | **Drags itself with the arms, legs trailing** | Survives | [K] (M) |
| **L1–L2 (conus)** | Normal | Normal | Full | Hip flexors weak or absent. Legs flaccid. Bladder and bowel paralysed | | As T12. Legs limp | Survives | [C32] (H) |
| **L3–S1 (cauda equina)** | Normal | Normal | Full | **Partial**: quadriceps (L3), ankle dorsiflexion (L4), big-toe extension (L5), plantar flexion (S1) as roots allow. Lower-motor-neuron, permanently flaccid. Foot drop. Saddle anaesthesia | | Limps and stumbles. Foot slaps. One leg may be worse than the other | Survives | [C32] [K] (H) |

- **Key muscles** (ISNCSCI) [C32] `(H)`. ≈ recall-consistent (standard ISNCSCI list; not web-verified):
  - C5 elbow flexors; C6 wrist extensors; C7 elbow extensors; C8 finger flexors (distal phalanx of the middle finger); T1 little-finger abductors.
  - L2 hip flexors; L3 knee extensors; L4 ankle dorsiflexors; L5 long toe extensors; S1 ankle plantar flexors.
- **Dermatome landmarks** for "no reaction below here" [C32] [K] `(H)`:
  - C4: top of the shoulder / clavicle.
  - C6: thumb. C7: middle finger. C8: little finger.
  - T4: nipple line. T6: xiphoid. T10: umbilicus. T12: groin.
  - L4: medial ankle. L5: top of the foot. S1: lateral foot and heel. S4–5: perianal.
- The **acute VC percentages** are order-of-magnitude values from the clinical literature, recalled `[K] (L–M)`. Use them only to scale breathing effort and voice.

### 6.3 Incomplete injury syndromes (useful for knife wounds)

| Syndrome | Typical cause | What is lost | Game picture | Source |
|---|---|---|---|---|
| **Brown-Séquard (hemisection)** | **Stab wound to the back or neck** (classic), bullet fragment | **Same side**: motor (paralysis), proprioception and vibration below the lesion. **Opposite side**: pain and temperature, starting 1–2 segments below | One leg (or arm and leg, if cervical) paralysed on the stabbed side. The other leg moves but does not react to pain or burns | [K] (H) |
| Central cord | Neck hyperextension in older people; blunt | **Arms much weaker than legs**, hands worst | Can stand or walk, but hands and arms are weak and burning | [K] (H) |
| Anterior cord | Anterior spinal artery injury; flexion | Motor, pain and temperature. **Proprioception kept** | Paralysed, but feels touch and position | [K] (H) |
| Cauda equina | Lumbar or sacral wound | Asymmetric flaccid legs, saddle anaesthesia, sphincters | See L3–S1 row | [K] (H) |
| Spinal cord concussion (transient neurapraxia) | Blunt blow to the neck (hammer, fall) | Complete paralysis that **resolves within minutes to 48 h**, usually within 10–15 min | Collapses, limp, then recovers | [K] (L–M) |

### 6.4 Spinal shock (what the paralysed limbs do over time)
Four-phase model [C33] `(H)`. ≈ recall-consistent (phase boundaries 0–1 day, 1–3 days, 1–4 weeks, 1–12 months):
1. **0–24 h**: areflexia or hyporeflexia. **Limbs completely flaccid, no tendon reflexes, no withdrawal.** The delayed plantar response and some cutaneous reflexes may be the first to return.
2. **1–3 days**: initial return of reflexes (bulbocavernosus and other polysynaptic reflexes).
3. **1–4 weeks**: early hyperreflexia.
4. **1–12 months**: spasticity.

**Within the game's time window only phase 1 matters.** Everything below the level stays limp and does not react to damage.

### 6.5 Neurogenic shock (loss of sympathetic tone)
- **Signs**: **hypotension** (SBP 70–90 mmHg) with **bradycardia** (HR 40–60, occasionally < 40 or pauses, especially on airway stimulation) and **warm, dry, pink skin** below the lesion (vasodilation, no sweating). Poikilothermia: body temperature drifts toward ambient `[K] (H)`.
- **Incidence** in isolated spinal cord injury in the emergency department: **~19% cervical, ~7% thoracic, ~3% lumbar** [C34] `(M)`. ≈ recall-consistent.
  - Added in the fact-check (recall, not web-verified): that study defined neurogenic shock as **SBP < 100 mmHg with HR < 80 bpm**. Use this as the game's trigger definition.
- **Severe (complete) cervical injuries**: bradycardia in essentially **all** patients, hypotension needing pressors in **~⅔**, primary cardiac arrest in **~16%**. Bradycardia peaks around days 3–5 and resolves over 2–6 weeks [C35] `(M)`. ≈ recall-consistent.
- **Contrast with haemorrhagic shock**:

| | Haemorrhagic | Neurogenic |
|---|---|---|
| HR | High | Low or normal |
| Skin | Pale, cold, clammy | Warm, pink, dry |

  Combined, the neurogenic lesion **blunts the compensation** for blood loss. HR cannot rise and vessels cannot constrict, so the victim decompensates and loses consciousness **earlier** for the same blood loss `[K] (H)`.

### 6.6 What paralysis looks like at the moment of injury
- **Standing victim, cervical cord**: instant flaccid collapse like a brainstem hit (§2.3), with **no protective arm reaction**. If the brain is intact: **conscious**, eyes and face working, can speak if C4 or below, cannot move the limbs, and does not flinch below the lesion `[K] (H)`.
- **Standing victim, thoracic or lumbar cord**: the **legs fold instantly**. The upper body keeps control, so the arms reach out and break the fall. The victim then props up, tries to rise, and the legs do not respond. They drag the body with the arms, legs trailing and slightly externally rotated `[K] (H)`.
- **Limbs**: floppy, and fall under gravity when lifted and dropped. No reflex withdrawal, no tone, the feet flop into plantar flexion and outward rotation `[K] (H)`.
- **Breathing** (C4–C8): the belly moves and the upper chest sinks on inspiration; shallow, rapid breaths `[K] (H)`.
- Priapism: omitted by design.

### 6.7 Simulation parameters: spinal cord

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `cord_level` | C1…S5 | enum | Map from the vertebra hit using the offsets in §6.1 | [K] (M) |
| `cord_complete_prob` (bullet through the canal) | 0.7–0.9. Fragment or cavitation only: 0.3–0.5 | p | | [G] |
| `resp_capacity_by_level` | C1–C3: 0–0.1; C4: 0.25; C5: 0.3; C6: 0.4; C7–C8: 0.5; T1–T6: 0.6; T7–T12: 0.8; L+: 1.0 | fraction of VC | Scales tidal volume, voice and cough | [K] (L–M) |
| `apnoea_awake_LOC` (C1–C3) | 90–180 | s | Faster if struggling. Not web-verified. Consistent with room-air O₂ stores (§1) | [K] (M) |
| `apnoea_arrest` (C1–C3) | 240–600 (default 360) | s | | [K] (M) |
| `neurogenic_shock_prob` | cervical complete 0.7–1.0; cervical any 0.19; thoracic 0.07; lumbar 0.03 | p | | [C34] [C35] (M) |
| `neurogenic_hr` / `neurogenic_sbp` | 40–60 / 70–90 | bpm / mmHg | Warm pink skin below the level | [C35] [K] (M) |
| `neurogenic_comp_cap` | HR response ≤ +10 bpm. Vasoconstriction ≤ 40% of normal | — | For lesions at T6 or higher | [G] on [K] |
| `spinal_shock_phase1` | 0–24 | h | Flaccid, areflexic | [C33] (H) |
| `brown_sequard_on_stab_prob` | 0.3–0.5 of knife cord injuries | p | | [G] on [K] |
| `cord_concussion_recovery` | 2 min – 48 h (default 10 min) | — | Hammer or fist to the neck, no structural lesion | [K] (L) |
| `poikilothermia_drift` | toward ambient at 0.3–1 | °C/h | Cervical and high thoracic | [K] (L) |
| Colour: neurogenic flush below the lesion | `#E7A897` tint at 20–30% | sRGB | Warm pink | [G] |
| Game time | 1× for the first 60 s. C1–C3 death at 1× to loss of consciousness, then 4× | — | | [G] |

### Visual/behavioural checklist: spinal cord
- A neck shot or stab at C1–C3: the body drops like a puppet, **but the eyes stay alive**. The eyes widen and dart, the mouth opens and closes silently, and the neck strains. The chest does not move. Over 1–2 min the lips go blue, the eyes lose focus, and the lids droop.
- C4–C5: the character lies limp but talks in short, breathy phrases. The belly pumps while the chest sinks. The skin looks pink and warm, and the pulse is slow.
- Mid-back shot: the legs fold, the arms catch the fall, and the character drags itself on its elbows with the legs trailing. **Hitting or burning the legs gets no reaction at all**. There is no flinch, even reflexively.
- Knife in the side of the back: one leg is dead. The other leg moves but ignores the torch.
- Audio: breathy whisper voice (C4–C6), weak ineffective cough, no pain vocalisation for injuries below the level.

---

## 7. Death from exsanguination (bleeding out)

### 7.1 ATLS classes (reference 70–75 kg adult; total blood volume ~5 L)

| | Class I | Class II | Class III | Class IV |
|---|---|---|---|---|
| Blood loss, % of blood volume | < 15 | 15–30 | 30–40 | > 40 |
| Blood loss, mL (70 kg) | < 750 | 750–1,500 | 1,500–2,000 | > 2,000 |
| Blood loss, mL (reference 75 kg, 5,250 mL) [E] | < 790 | 790–1,575 | 1,575–2,100 | > 2,100 |
| Heart rate (bpm) | < 100 | 100–120 | 120–140 | > 140 |
| Systolic BP | Normal | Normal | Decreased | Decreased |
| Pulse pressure | Normal or ↑ | ↓ | ↓ | ↓ |
| Respiratory rate (/min) | 14–20 | 20–30 | 30–40 | > 35 |
| Urine (mL/h) | > 30 | 20–30 | 5–15 | Negligible |
| Mental state | Slightly anxious | Mildly anxious | **Anxious, confused** | **Confused, lethargic** |

Source: ATLS 9th edition numeric table [C1] `(H as published)`. ≈ recall-consistent: every cell matches the fact-checker's independent recall of the 9th-edition table. Not web-verified. ✓ verified (arithmetic): the 75 kg row is 15 / 30 / 40% of 5,250 mL = 788 / 1,575 / 2,100 mL.
- The **10th edition** replaced the fixed numbers with arrows and added **base deficit**: Class I 0 to −2; II −2 to −6; III −6 to −10; IV below −10 mmol/L [C1] `(M)`.
- **Real patients often show less tachycardia and hypotension than the table predicts** [C2] [C3] `(M)`.
- **Game use**: the numeric table drives visible signs. Randomise HR ±15% and let the paradoxical bradycardia of §7.3 happen.

### 7.2 What the player sees, stage by stage

| Stage (loss) | Mind and behaviour | Skin and face | Eyes | Breathing | Pulse / BP | Voice / audio | t_game guidance |
|---|---|---|---|---|---|---|---|
| **0–15%** | Normal. Maybe slightly anxious | Normal | Normal | Normal | HR ≤ 100 | Normal | Real time or 4× |
| **15–30%** | Anxious, restless, **thirsty**. Dizzy if upright; **may faint if standing** | **Pale**, cool hands, sweat beginning | Normal, blinks more | 20–30/min | HR 100–120. Narrow pulse pressure | Complains, may plead | 4× |
| **30–40%** | **Confused, agitated or oddly quiet**, air hunger, nausea, "sense of doom", fumbling | **Pale-grey, cold, clammy**, mottled knees, **pale lips** | **Sunken, dull, unfocused.** Conjunctivae pale. Pupils normal to large, sluggish | 30–40/min, sighing | HR 120–140. Weak "thready" radial pulse. SBP ~70–90 | Weak, slurred; repeats itself | 4× |
| **40–50%** | **Lethargic, then unresponsive.** Loss of consciousness when supine at ~40–50% | **Waxy white-grey.** Lips grey-lilac, **not blue** | **Lids half-closed or fixed open**, gaze vacant, pupils dilating | Shallow and fast, then slowing and irregular | HR > 140, *or paradoxically slowing*. SBP < 70. Radial pulse absent | Moans, then silence | 4× |
| **50–60%** | Unconscious, agonal | White. No capillary refill | Pupils wide and fixed. No blink | **Agonal gasps** 2–10/min (§10) | **PEA** (organised rhythm, no pulse), then asystole | Gasps, gurgles | 1× for the last 60 s |

Sources: [C1] for class signs `(H)`. Behaviour, eyes and audio are `[K] (M)`. Loss-of-consciousness and death thresholds are in §7.4.

### 7.3 Two important non-linearities
- **Paradoxical (relative) bradycardia**: in severe, rapid haemorrhage the HR can **fall** instead of rise. This is a vagally mediated, Bezold–Jarisch-type reflex from an empty, vigorously contracting ventricle, and it produces sudden collapse.
  - Documented in trauma series: roughly **a third of hypotensive trauma patients** have HR < 90–100 [C4] [C5] `(L–M)`.
    - *Fact-check note: uncertain. The fact-checker's recall is that the prevalence of relative bradycardia (HR ≤ 90 with SBP ≤ 90) in trauma registries may be higher, roughly 30–45%, depending on the HR cut-off. Not web-verified. Treat "one third" as a lower-middle estimate. The game's `paradoxical_brady_prob` is a separate [G] roll for sudden fainting and is unaffected.*
  - Volunteer studies (lower-body negative pressure) show that compensation holds until a **sudden decompensation**: BP drops, HR often drops, and the subject goes presyncopal. This occurs at an equivalent central hypovolaemia of **~1,000–2,000 mL**, with wide individual variation [C6] `(M)`.
    - *Fact-check note: ≈ recall-consistent. Cooke 2004 maps LBNP of −10 to −20 mmHg to ~400–550 mL of blood loss, −20 to −40 mmHg to ~550–1,000 mL, and beyond −40 mmHg to > 1,000 mL. Most subjects decompensate at about −60 to −100 mmHg. Not web-verified.*
  - **Game**: at 25–40% loss, 10–30% of characters suddenly faint (HR drops to 50–70) before the table predicts `[G]`.
- **Posture**: an **upright** bleeding person faints much earlier (from ~20–30% loss) than a supine one, because venous return falls when standing `[K] (M)`. After the fall, lying flat can bring brief partial recovery. This gives "gets back up, then collapses again".

### 7.4 Thresholds (defaults)

| Event | Blood loss (fraction of BV) | Also triggered by | Source |
|---|---|---|---|
| Orthostatic faint (standing) | 0.20–0.30 | MAP < 60 while upright | [K] (M) |
| Confusion | 0.30–0.40 | MAP < 65, or CPP < 50 | [C1] (H) |
| Loss of consciousness (supine) | **0.40–0.50 (default 0.45)** | **MAP < 40–45 (SBP < 60) for > 5–8 s** | [C1] [K] (M) |
| PEA | **0.50–0.60 (default 0.55)** | MAP < 20–25 | [K] (L–M) |
| Asystole | 2–10 min after PEA | | [K] (M) |
| Irreversible brain injury | 4–6 min after cerebral perfusion stops | | [K] (H) |

- **Fact-check note on the loss-of-consciousness and PEA thresholds** (uncertain, recall only, not web-verified). Two textbook statements bracket the defaults:
  - **ATLS 9th ed. text on Class IV**: loss of **more than 50%** of blood volume produces loss of consciousness with a weak pulse and low BP.
  - **Guyton & Hall (circulatory shock chapter)**: when blood is removed over about 30 min, cardiac output and arterial pressure **both fall to zero at about 40–45%** of blood volume. This is based on animal data.
  - So pulselessness can arrive at or below 50% loss, and the 0.55 PEA default sits at the late edge. **Recommendation**: keep LOC at 0.45. Make PEA rate-dependent: **0.45–0.50 for rapid bleeds (> 500 mL/min)**, and 0.55 for slow bleeds where compensation has time to act.
  - The MAP trigger (MAP < 40–45, SBP < 60, for > 5–8 s) agrees with the ESC syncope guideline (recall): loss of consciousness at SBP ~50–60 mmHg at heart level (≈ 30–45 mmHg at brain level when upright).
- A **slow** bleed allows compensation: fluid shifts from tissues into vessels (transcapillary refill, roughly **50–150 mL/h** early on `[K] (L)`) plus clotting. So slow deaths occur at a higher cumulative loss, or not at all.
- **Coagulopathy**: after ~30–40% loss, or with core temperature below ~35 °C, clotting weakens and **every wound oozes more** `[K] (M)`.

### 7.5 Bleeding-rate model (hand-off to the vascular system)

**Pressure-driven flow** `[E]`:
```
Q_wound = Q_ref × max(0, P_drive − P_ext) / (P_ref − P_ext)
```
- Artery: `P_drive` = instantaneous arterial pressure. It oscillates between DBP and SBP at the heart rate, which is what produces spurts.
- Vein: `P_drive` = CVP (0–8 mmHg) + ρgh, where h is the height below the heart, at 0.78 mmHg/cm. **A neck vein above the heart can go negative and suck in air** [D02:R13].
- `P_ext`: tamponade from haematoma or a closed compartment (0–30 mmHg). It rises in closed spaces such as the pericardium.

| Vessel | Physiological flow at rest | Suggested wound bleed rate at normal BP | Character | Source |
|---|---|---|---|---|
| Thoracic aorta, heart chamber | 3–5 L/min | 2–5 L/min, mostly **internal** (pleura or pericardium) | Loss of consciousness in 10–30 s; arrest in 1–3 min | [K] (M), rates [E] |
| Common carotid (each) | ~300–400 mL/min | 0.5–1.5 L/min (both ends) | Bright jet 0.5–1.5 m. See §7.6 | [K] (M), [E] (L) |
| Internal jugular | ~300–500 mL/min | 0.1–0.5 L/min | Dark, steady, **air embolism risk upright**. Frothy | [D02:R13] [K] (L) |
| Subclavian | ~300–500 mL/min | 0.5–1.5 L/min | Cannot be compressed | [E] (L) |
| Common femoral | ~300–400 mL/min | 0.5–1.5 L/min | Loss of consciousness in 2–5 min, death in 3–10 min | [K] (M), [E] (L) |
| Brachial | ~100–150 mL/min | 150–400 mL/min | Pulsatile | [E] (L) |
| Radial / ulnar | ~20–40 mL/min | 20–80 mL/min | Often self-limits by spasm | [E] (L) |
| Scalp laceration 5–10 cm | — | 20–100 mL/min | Does **not** self-limit (vessels tethered) | [D02:R15] |
| Lung parenchyma | Low pressure (PA 25/10) | 20–100 mL/min | Often self-limits | [K] (L) |

- **Transected vs lacerated** `[K] (M)`:
  - A **completely transected** small or medium artery retracts and constricts, so bleeding can fall to 20–50% of its initial rate within 1–5 min `[G]` numbers.
  - A **partially lacerated** artery is held open and keeps bleeding.
  - Large arteries (carotid, femoral, aorta) do not self-seal at normal BP.
- **Clotting**: capillary and small-vessel bleeding stops in **1–9 min** [D02:R21] (normal skin bleeding time). Arteries over ~2–3 mm diameter do not stop by themselves at normal pressure `[K] (M)`.

**Example timelines** `[E]` (BV 5,250 mL; loss of consciousness at 45%, PEA at 55%):
- The **lower bound** assumes constant flow.
- The **upper bound** lets flow fall in proportion to MAP.

| Initial bleed rate | Loss of consciousness | PEA | t_game (default scale) |
|---|---|---|---|
| 5 L/min (aorta, heart) | 10–30 s (brain perfusion fails before the volume threshold) | **35–50 s** (corrected: was 40–90 s) | 1× |
| 1 L/min (carotid, femoral) | **2.4–2.8 min** (corrected: was 2.5–4 min) | **2.9–4.0 min** (corrected: was 3.5–7 min) | 1× then 4×, last 60 s at 1×: **~2–2.5 min** (corrected: was ~1.5–2.5 min) |
| 300 mL/min (brachial, several wounds) | **7.9–9.3 min** (corrected: was 8–15 min) | **9.6–13 min** (corrected: was 10–25 min) | 4×: **~4–5 min** (corrected: was 3–6 min) |
| 100 mL/min (large scalp wound plus others) | **24–28 min** (corrected: was 25–50 min) | **29–40 min** (corrected: was 35–80 min) | 10×: **~5–6 min** (corrected: was 3–8 min) |
| 30 mL/min (oozing wounds) | **1.3–1.6 h**, or never if clotting wins (corrected: was 1.5–4 h) | **1.6–2.2 h** (corrected: was 2–6 h) | 30×: **~5–6.5 min** (corrected: was 3–12 min) |

✓ verified (arithmetic) after correction. The fact-checker recomputed every row with the method stated above.
- **LOC** at 45% loss = 2,362 mL. **PEA** at 55% = 2,888 mL.
- **Lower bound**: constant flow, t = V / Q.
- **Upper bound**: flow proportional to MAP, using the document's own `map_by_loss` curve (§7.8) integrated piecewise: t = ∫ dV / (Q₀ × MAP(V) / 93). This gives flow-equivalent volumes of **2,800 mL to LOC** and **3,962 mL to PEA**.
- The original upper bounds were 1.5–2× longer than this method gives.
- Transcapillary refill (50–150 mL/h) and clotting extend only the slow rows, by roughly 5–20 min at 30 mL/min.
- If PEA is moved to 0.50 for rapid bleeds (§7.4 note), use 2,625 mL / 3,302 mL instead. At 1 L/min that puts PEA at 2.6–3.3 min.

### 7.6 Arterial jets and when they stop
- **Ideal jet height** `h = P / (ρ g)`: SBP 120 → 1.54 m; SBP 80 → 1.03 m; SBP 60 → 0.77 m `[E]`. ✓ verified (arithmetic).
- **Gap added by the fact-check** `[E]`: `P` must be the **local** arterial pressure at the wound, not the aortic pressure.
  - Formula: `P_local = P_aortic − 0.78 mmHg/cm × (wound height above the heart)`.
  - Standing adult: a neck wound ~30 cm above the heart loses ~23 mmHg (SBP 120 → ~97 at the carotid). An ankle wound ~120 cm below the heart gains ~94 mmHg.
  - Lying flat: the correction is near zero.
  - So standing neck jets are shorter, and leg jets taller, than the aortic figure suggests. Apply the same term that §7.5 applies to veins. Real jets reach **20–90%** of that because of friction, the shape of the wound, overlying tissue and vessel spasm. Use `h_real = η × h_ideal` with η 0.2–0.9 (default 0.5) `[G]`.
- **Exit speed** v = √(2P/ρ): 5.5 m/s at 120 mmHg, 3.9 m/s at 60 mmHg `[E]`.
- The jet **pulses at the heart rate**: tall during systole, a dribble during diastole. As shock deepens, jets **shorten and become rapid and weak** (HR up, pulse pressure down) `[K] (H)`.
- Below SBP ~50–60 mmHg a jet turns into a **welling pulse** `[E]`.
- **At cardiac arrest, pulsatile flow stops with the last effective beat.** Within ~30–90 s, arterial pressure falls to the mean systemic filling pressure (~7–13 mmHg). After that the wound only **drains by gravity** (§12.2) `[K] (H)` [C51] [C52]. ≈ recall-consistent. Recalled human data from induced VF during defibrillator testing show that arterial and venous pressures have **not** fully equalised 10–15 s after arrest, which is compatible with the 30–90 s figure. Not web-verified.

### 7.7 Colour progression (light-to-medium skin)

| Region | Normal | 15–30% loss | 30–40% | > 40% / dead from bleeding | Source |
|---|---|---|---|---|---|
| Face skin | base | Desaturate 20% | Desaturate 40%, grey shift `#D9D2CC` | Waxy `#E3DCD3` | [G] on [K] |
| Lips | `#B35E62` | `#BF8583` | `#C9A09E` | Grey-lilac `#A99AA4` (not blue) | [G] |
| Palpebral conjunctiva | `#D98C87` | `#E2AAA5` | `#EBCFCB` | `#EFDCD8` | [G] |
| Nail beds | `#E2A9A6` | | Refill > 3 s | White `#EEE0DC` | [G] |
| Knees and thighs (mottling) | — | — | Lacy `#8C5A70` at 20–40% | Fades to pallor | [G] on [K] |
| Forehead | — | Sweat: specular up | Cold sweat beads | Dry | [G] |

### 7.8 Simulation parameters: exsanguination

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `bv_per_kg` | 70 (M) / 65 (F) | mL/kg | | [C1] (H) |
| `hr_by_loss` | 0–15%: 80–100; 15–30%: 100–120; 30–40%: 120–140; > 40%: 140–160, then falls terminally | bpm | ±15% randomness | [C1] (H) |
| `paradoxical_brady_prob` | 0.10–0.30 at 25–40% loss | p | HR → 50–70, sudden faint | [C4] [C5] [C6] (L–M), [G] |
| `map_by_loss` | 0: 93; 0.15: 90; 0.30: 80; 0.40: 60; 0.50: 45; 0.55: 30 | mmHg | Piecewise linear | [E] on [C1] |
| `rr_by_loss` | 16 → 25 → 35 → 40, then gasping | /min | | [C1] (H) |
| `cap_refill` | < 2 → 2–3 → > 3 → > 5 | s | | [K] (M) |
| `loc_supine_loss` | 0.40–0.50 (default 0.45) | fraction | Also MAP < 40–45 for > 5–8 s. Uncertain; bracketed by ATLS (> 50%) and Guyton (40–45%) per §7.4 note | [C1] [K] (M) |
| `faint_upright_loss` | 0.20–0.30 | fraction | Not web-verified | [K] (M) |
| `pea_loss` | 0.50–0.60 (default 0.55) | fraction | Fact-check recommendation: rapid bleeds (> 500 mL/min) 0.45–0.50; slow bleeds 0.55. See §7.4 | [K] (L–M) |
| `pea_to_asystole` | 2–10 | min | | [K] (M) |
| `transcapillary_refill` | 50–150 | mL/h | Early phase | [K] (L) |
| `coagulopathy_onset` | loss > 0.35, or core < 35 °C | — | Wound ooze ×1.5–2 | [K] (M), [G] |
| `artery_selfseal_factor` | complete transection: ×0.2–0.5 after 1–5 min (vessel < 4 mm). Partial: ×1 | — | | [K] (M), [G] |
| `jet_eta` | 0.2–0.9 (default 0.5) | — | h_real = η × P / (ρg) | [G]/[E] |
| `jet_stop` | at arrest (last beat) | — | | [K] (H) |
| Game time | 1× for 5 L/min bleeds. 4× for 0.3–1 L/min. 10–30× for slow bleeds. The last 60 s always at 1× | — | | [G] |

### Visual/behavioural checklist: exsanguination
- Early: spurting wound, rapid breathing, the character grows restless and thirsty, pleads, and keeps trying to stand. It gets dizzy upright and may faint, then partly recovers lying down.
- Middle: grey-white face, beaded cold sweat, pale lips, blotchy knees. Eyes sunken and dull. Speech slurred and repetitive. Hands fumble. The jet becomes shorter, faster and weaker.
- Late: eyes half-closed and vacant, breathing shallow and fast then slowing, no response to voice. The wound now just wells.
- End: a few slow, deep gasps with the jaw dropping open. The wound stops pulsing. The skin is waxy white, **not blue**.
- Audio: fast breathing, moans, sighs, then gasps, then silence. Blood patter sounds slow down with the pulse rate.

---

## 8. Heart wounds and the brain's oxygen reserve

### 8.1 The 10–15 second rule
- **"Even if the heart is instantly destroyed, there is sufficient oxygen within the brain to support full and complete voluntary action for 10–15 seconds."** This is FBI wound-ballistics doctrine [C7] (quoted from memory), echoed in the wound-ballistics literature [C8] `(M–H)`. ≈ recall-consistent: the fact-checker independently recalls the same sentence in Patrick (1989), worded "...sufficient oxygen **in** the brain...". Not web-verified.
- **Physiology** agrees:
  - Complete neck-cuff occlusion of cerebral flow causes unconsciousness in **5–10 s (mean ~6.8 s)** [C9] `(H)`.
  - G-induced loss of consciousness shows a **~5–6 s functional buffer**, then incapacitation lasting about 12 s (absolute) plus a longer relative period. **Brief myoclonic jerks are common** [C10] `(M)`. ≈ recall-consistent. The fact-checker recalls that the same series gives a mean relative-incapacitation period of ~15 s and myoclonic "flailing" in roughly 70% of episodes (low confidence, not web-verified).
  - A destroyed heart still leaves a few seconds of residual arterial pressure, which is how 5–10 s becomes 10–15 s `[E]`.
- **Syncope video analysis** (56 episodes, induced in healthy volunteers) [C11] `(M)`:
  - **myoclonic jerks in ~90%**;
  - **eyes open throughout**, with **upward eye deviation** in most episodes;
  - head turns, oral automatisms, and attempts to right the body.
  - The unconscious period lasted about **12 s** on average.

  This is the best evidence for what the eyes do during cerebral hypoperfusion. ≈ recall-consistent (56 induced syncopes; myoclonus ~90%; eyes open; upward deviation mainly early in the episode; hallucinations reported in ~60%). Not web-verified.

### 8.2 Sequence after the heart is destroyed (pistol, rifle, or shotgun to the ventricles)

| t_real | What happens | Eyes | t_game | Source |
|---|---|---|---|---|
| 0–5 s | Normal voluntary action. Can run, shout, fight, shoot back | Wide, pupils may dilate (fear), fixating | 1× | [C7] (M–H) |
| 5–10 s | Grey-out and tunnel vision, legs weaken, stumbles | Unfocused, "blank stare" | 1× | [C10] [K] (M) |
| 8–15 s | **Loss of consciousness and collapse.** A brief protective reaction is possible just before, as awareness fades | **Stay open**. Upward (or lateral) deviation for a few seconds. Blinking stops | 1× | [C9] [C11] (M) |
| 10–30 s | Myoclonic jerks (1–10 s). Limbs then flaccid | Return toward midline. Lids droop to half-open | 1× | [C11] (M) |
| 15–40 s | EEG goes flat | Pupils start to dilate (~30–45 s) | 1× | [K] (M) |
| 20 s – 5 min | **Agonal gasps** in ~⅓–½ (medulla intact), 2–10/min, stopping within ~1–5 min | Pupils wide and fixed by 1–2 min. Corneal reflex gone | 1× for the first minute, then 4× | [C12] [C13] (M) |
| 4–6 min | Irreversible brain injury begins | Tear film dried; gloss fading | 4× | [K] (H) |

### 8.3 Stab or small wounds of the heart: tamponade
- **Tamponade from blood in the pericardium**: the pericardium normally holds 15–50 mL of fluid, but **100–200 mL of acute blood** is enough to compress the heart because the sac cannot stretch quickly `[K] (H)`.
- **Signs**:
  - Beck's triad: hypotension, **distended neck veins** and muffled heart sounds.
  - Pulsus paradoxus: the SBP falls more than 10 mmHg on inspiration.
  - Rising distress, then PEA arrest `[K] (H)`.
- **Timeline**: minutes to hours. A small wound in the right ventricle can partly seal, and tamponade can **slow** external or pleural bleeding, which paradoxically helps survival `[K] (M)`.
- **Outcome**: most cardiac **gunshot** victims die before reaching hospital. Among those who arrive alive, survival is roughly **15–20% for gunshot and 50–65% for stab wounds** [C38] `(L–M)`.
- **Commotio cordis** (for the fist and hammer): a blunt blow to the front of the chest during a **~10–30 ms window on the upstroke of the T wave** can trigger **ventricular fibrillation** in a structurally normal heart. The victim collapses within seconds, without a pulse, often with agonal gasps `[K] (M)`.
  - The window is roughly 2–4% of the cardiac cycle `[E]`.
  - Game: p ≈ 0.01–0.03 per hard precordial blow `[G]`.
  - ✓ verified (arithmetic): a 20 ms window is 2% of a 1,000 ms cycle (60 bpm) and 4% of a 500 ms cycle (120 bpm).

### 8.4 Simulation parameters: heart

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `heart_destroyed_action_window` | 10–15 (default 12) | s | Full voluntary action, then fading | [C7] [C8] (M–H) |
| `cerebral_arrest_LOC` | 5–10 (mean 6.8) | s | Counted from zero brain perfusion | [C9] (H) |
| `syncope_myoclonus_prob` | 0.9 | p | 1–10 s of irregular jerks | [C11] (M) |
| `syncope_eye_upward_prob` | 0.6–0.8 | p | 2–10 s, 10–30° up, conjugate | [C11] (M), degrees [G] |
| `pupil_dilate_start` / `pupil_dilate_max` | 30–45 / 60–120 | s after circulatory arrest | To 6–8+ mm | [K] (M) |
| `agonal_gasp_prob` | 0.3–0.5 (medulla intact) | p | Falls with time since arrest | [C12] [C13] (M) |
| `tamponade_volume` | 100–200 | mL | Acute | [K] (H) |
| `tamponade_time_to_arrest` | 5 min – 2 h (default 20 min) | — | Stab wound | [K] (L), [G] |
| `commotio_prob_per_hard_chest_blow` | 0.01–0.03 | p | Instant VF | [G] on [K] |
| Game time | 1× for the first 60 s. Tamponade at 4× | — | | [G] |

### Visual/behavioural checklist: heart
- A heart shot does **not** drop the character instantly. For about 10 s it can move, scream or act. Then it stumbles and collapses with the eyes still open, often rolled up for a moment, with a few jerks of the arms.
- The small entrance wound bleeds surprisingly little outside. Blood fills the chest instead. A larger exit or shotgun wound in the back leaks heavily when the body lies on it.
- About a third of victims give a few slow, snoring gasps over the next minutes; the rest are silent.
- A stab to the heart: the victim walks, talks and sweats, with bulging neck veins. It becomes breathless and grey over minutes, then collapses.
- A hard punch or hammer blow to the chest, rarely: instant collapse without a pulse (commotio cordis).

---

## 9. Lung and chest wounds

### 9.1 Haemothorax
- Each hemithorax can hold **~40% of the blood volume (2–3 L)**, so a person can bleed to death **into the chest with little visible external blood** [C1] `(M)`. ≈ recall-consistent: the "40% of circulating blood volume per hemithorax" phrasing is standard in haemothorax reviews such as StatPearls. Not web-verified. ✓ verified (arithmetic): 40% × 5,250 mL = 2,100 mL.
- **Massive haemothorax** = **≥ 1,500 mL** immediately (or ≥ one-third of blood volume), or **> 200 mL/h for 2–4 h** [C1] `(H)`. ≈ recall-consistent.
- **Sources**:
  - Peripheral lung tissue is low-pressure (pulmonary artery ~25/10 mmHg) and often slows or stops by itself.
  - Intercostal and internal mammary arteries (systemic pressure) keep bleeding.
  - The hilum, great vessels and heart cause rapid exsanguination `[K] (H)`.
- **Signs**: breathlessness, dullness on the injured side, reduced chest movement on that side, and shock signs as in §7 `[K] (H)`.

### 9.2 Pneumothorax: simple, open, tension
- **Open ("sucking") chest wound**: if the chest-wall defect is **more than about ⅔ of the tracheal diameter**, air enters preferentially through the wound. That is about **> 10–13 mm** for a 15–20 mm trachea `[E]`, well within shotgun and rifle exit wounds [C1] `(H)`. ≈ recall-consistent (the ATLS "two-thirds of the tracheal diameter" rule). ✓ verified (arithmetic): ⅔ × 15–20 mm = 10–13 mm. Adult tracheal diameter varies (roughly 13–25 mm in men), so the threshold spans ~9–17 mm. Air **sucks and bubbles** at the wound with each breath.
- **Tension pneumothorax**: a one-way air leak inflates the pleural space, collapses the lung, pushes the mediastinum across, and kinks venous return.
  - In **spontaneously breathing** patients it usually develops **over minutes to hours**. It is faster with ventilation, which does not apply in this game [C37] `(M)`.
  - **Respiratory distress and tachycardia** are nearly universal, with falling oxygen saturation.
  - **Hypotension is a late sign, and tracheal deviation is late and uncommon** [C37] `(M)`. ≈ recall-consistent: the review reports that in awake patients distress and tachycardia are common, while hypotension and tracheal deviation are each seen in a minority. Not web-verified.
  - Distended neck veins appear unless the person is also hypovolaemic.
  - The affected side is hyperexpanded and moves little.
  - It ends in cyanosis, confusion, loss of consciousness and **PEA arrest** `[K] (H)`.

### 9.3 Haemoptysis and frothy blood
- A bullet or blade through the lung usually produces **coughing of bright red, frothy blood** within **seconds to a minute**. Blood mixes with air in the airways and makes a pink-red foam at the mouth and nose. Breathing sounds **wet**: gurgling and crackling `[K] (H)`.
- **Volumes**: streaks up to tens of mL per coughing episode. "Massive" haemoptysis is clinically ≥ 200–600 mL per 24 h. A hilar or major-vessel hit can flood the airways (the victim **drowns in blood** within minutes, with asphyxia before exsanguination) `[K] (M)`.
- **Expired blood spatter** (coughed or breathed out) is fine, may be diluted pink by saliva, and contains **small air bubbles or vacuoles and "bubble ring" stains**. These are recognised bloodstain-pattern features `[K] (M)`.
- **Subcutaneous emphysema**: air tracks into the tissues of the chest wall, neck and face. The skin looks **puffy** and **crackles** under pressure (crepitus), and it spreads over minutes to hours `[K] (H)`.
- **Air embolism**: lung injury can open a path from the airways into the pulmonary veins, sending air to the coronary and cerebral arteries. The result is sudden collapse, seizure or arrest. It is rare in a spontaneously breathing victim `[K] (M)`. For the venous route (neck veins), a rapidly entrained **~3–5 mL/kg (200–300 mL)** of air can be lethal `[K] (M)`.

### 9.4 Timeline: gunshot through one lung, no hilar injury

| t_real | Event | t_game | Source |
|---|---|---|---|
| 0–5 s | Hit. Gasp, pain, may stay standing | 1× | [K] (H) |
| 5–60 s | Cough, **bright frothy blood** from the mouth. Rapid breathing. With an open wound: **sucking and bubbling** at the hole | 1× | [K] (H) |
| 1–15 min | Haemothorax of 0.5–1.5 L. RR 30–40, HR 110–140, pale, anxious, sits up or leans forward to breathe | 4×: 15 s – 4 min | [K] (M) |
| 5–60 min | Tension develops (if a valve-like leak): increasing distress, neck veins bulge, lips blue, confusion | 4–10× | [C37] (M) |
| + 2–10 min | Hypotension, loss of consciousness, gasps, PEA | 1× for the last 60 s | [C37] [K] (M) |

### 9.5 Simulation parameters: lung and chest

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hemithorax_capacity` | 2,000–3,000 | mL | ~40% of BV | [C1] (M) |
| `massive_haemothorax` | ≥ 1,500 immediate, or > 200 mL/h | mL | | [C1] (H) |
| `lung_parenchyma_bleed` | 20–100, decaying with τ ≈ 10–30 min | mL/min | Self-limiting | [K] (L), [G] |
| `open_pneumo_threshold` | wound Ø > 10–13 | mm | ⅔ of tracheal Ø | [C1] (H) rule, [E] size |
| `tension_onset` | 5 min – several h (default 20 min for a large leak) | — | | [C37] (L–M) |
| `tension_signs` | RR > 30, HR > 120, SpO₂ falling. Hypotension late. Tracheal shift rare | — | | [C37] (M) |
| `haemoptysis_onset` | 5–60 | s | | [K] (M) |
| `haemoptysis_per_cough` | 2–30 (hilar: 100+) | mL | | [K] (L), [G] |
| `airway_flood_asphyxia` | 1–5 | min | Hilar or major-vessel lung hit | [K] (L) |
| `subcut_emphysema_spread` | 1–5 | cm/min | Visual swelling and crackle | [G] |
| `venous_air_lethal` | 3–5 | mL/kg | Rapid entrainment | [K] (M) |
| Colour: frothy blood | `#E04A56` with foam highlights `#F4C9CC` | sRGB | Pink-red, bubbly | [G] |
| Colour: coughed blood diluted with saliva | `#D9606A` | sRGB | | [G] |
| Game time | 1× for the first 60 s; then 4–10× | — | | [G] |

### Visual/behavioural checklist: chest
- A chest shot: the character gasps, coughs, and brings up **bright pink-red foam** that runs from the mouth and nostrils. Each breath gurgles.
- A big exit wound in the chest wall **sucks and bubbles** with each breath: a hissing, slurping sound, and frothy blood welling from the hole.
- Over minutes it sits up and leans forward, fighting for air. The neck veins bulge, the lips turn blue and the eyes become frightened, then vacant.
- The skin over the chest and neck puffs up and crackles when pressed.
- Blood from the mouth keeps leaking when the dead body is rolled or moved (passive drainage), and may carry bubbles.

---

## 10. The agonal phase and the transition to death

### 10.1 Definitions the state machine should use
- **Circulatory arrest ("clinical death")**: no effective cardiac output. The victim is pulseless, apnoeic or gasping, and unresponsive. **The post-mortem clock (§12) starts here** `[K] (H)`.
- **Irreversibility**: brain injury begins after **~4–6 min** without circulation at normal temperature `[K] (H)`.
  - Observation studies of dying patients show that **transient resumption of cardiac activity** after it has stopped (autoresuscitation) happens in a minority (~14%) and **within ~5 min**. That is why clinical protocols wait about 5 min before declaring circulatory death [C14] `(M)`. ≈ recall-consistent: the fact-checker recalls that in [C14] the longest pause before resumption was about 4 min 20 s, and that no patient regained consciousness or a sustained circulation. Not web-verified.
  - **Game**: declare `dead = true` at arrest + 5 min, but run the post-mortem clock from arrest.
- **Death by neurologic criteria (brain death)** [C17] [C18] `(H)`:
  - coma;
  - absent brainstem reflexes: pupils fixed at 4–9 mm, no corneal, oculocephalic, vestibulo-ocular, gag or cough reflex;
  - apnoea.

  ≈ recall-consistent: the 2010 guideline says pupils are "usually fixed in a midsize or dilated position (4–9 mm)". Not web-verified.
  - **Gap added by the fact-check** (recall):
    - A newer US consensus guideline replaces the 2010 one: Greer DM, et al. *Pediatric and adult brain death/death by neurologic criteria determination: consensus guideline*. Neurology 2023.
    - Its core clinical criteria are unchanged.
    - The apnoea test is positive when **PaCO₂ ≥ 60 mmHg and ≥ 20 mmHg above baseline** (the 2023 text also cites arterial pH ≤ 7.30) with no respiratory effort.
    - Game use: a brain-dead character makes **no breathing movement even as CO₂ rises**.

  In the game this is the state after brainstem destruction or herniation. The heart then stops within minutes from hypoxia, because no one ventilates.

### 10.2 Agonal breathing
- Occurs in **~30–40% or more of witnessed cardiac arrests**. It is **most frequent in the first minutes** and declines with time since collapse [C12] [C13] `(M)`. ≈ recall-consistent: Clark 1992 reports ~40% of arrests; Bobrow 2008 reports ~⅓ overall, higher when EMS arrive early. The 2–10/min rate and 1–5 min duration below are not from these papers and remain `[K]`. Not web-verified.
- **Character** `[K] (M)`:
  - sudden, short, deep inspiratory efforts;
  - **the head and neck extend and the jaw drops open**;
  - rate about 2–10/min, irregular.
- **Sounds**: snorting, snoring, gurgling, sometimes a moan as air passes the vocal cords.
- **Duration**: typically **one to several minutes**, fading `[K] (M)`.
- Gasps need a working **medulla**. They are **absent after medullary destruction** `[K] (M)`.
- They move almost no air. Do not animate them as effective breathing.

### 10.3 Terminal heart rhythms
- **Haemorrhage**: sinus tachycardia, then slowing, then **PEA** (organised complexes, no palpable pulse; the heart may still twitch weakly: "pseudo-PEA"), then a slow wide-complex rhythm, then **asystole** over **2–10 min** `[K] (M)`.
- **Hypoxia** (apnoea: brainstem, C1–C3, airway flooding): progressive **bradycardia** as SpO₂ falls below ~50–60%, then PEA or asystole at **4–10 min** `[K] (M)`.
- **Direct cardiac injury, commotio cordis, massive catecholamine surge**: **VF**. No output, and it degrades to asystole within ~10–20 min `[K] (M)`.
- **Pulses** (old ATLS teaching): a palpable radial pulse means SBP ≥ 80, femoral ≥ 70, carotid ≥ 60 mmHg. **This overestimates BP**: pulses persist to lower pressures than taught [C39] `(M)`. For the game: the radial pulse disappears at ~50–70, femoral at ~40–60, carotid at ~30–50 mmHg SBP `[G]`.

### 10.4 The brain in the last minutes
- **EEG silence** comes 10–40 s after cerebral perfusion stops `[K] (M)`.
- In human cortex recordings during dying, a **terminal spreading depolarisation** (the "wave of death") follows **within minutes** of circulatory failure. It marks the start of the injury cascade, which is still partly reversible if circulation is restored soon after [C15] `(M)`.
- **Spinal reflex movements** can occur after the brain is dead, because the cord survives longer. In brain-dead patients they include finger flexion, arm raising (the "Lazarus sign"), trunk flexion and toe movements, reported in **roughly 40%** of patients [C16] `(M)`.
  - **Game**: after brainstem destruction, allow rare (p ≈ 0.1–0.2) slow reflex movements of a hand, arm or foot during the first 1–10 min `[G]`.

### 10.5 The last moments
- **The final exhalation**: when respiratory muscles relax at or after the last gasp, the chest recoils and pushes out a passive breath, often with a sigh or rattle `[K] (M)`.
- **"Death rattle"**: gurgling from pooled secretions in the throat. It is a feature of **slow deaths lasting hours**, not of sudden violent death `[K] (H)`.
- **Tone**: all muscles go slack (primary flaccidity, §12.1). The jaw drops, the lids stay where they are (§11), and the sphincters may relax.
- **Fasciculations and twitches**: small, irregular twitches in individual muscles for minutes after death are plausible `[K] (L)`.

### 10.6 Simulation parameters: agonal phase

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `arrest_to_dead_flag` | 300 | s | Autoresuscitation window | [C14] (M) |
| `autoresuscitation_prob` | 0.1 | p | A brief return of a few beats in the first 5 min, then gone | [C14] (M), [G] |
| `agonal_gasp_prob` | 0.3–0.5 (0 if the medulla is destroyed) | p | | [C12] [C13] (M) |
| `agonal_gasp_rate` | 2–10, declining | /min | | [K] (M) |
| `agonal_gasp_duration` | 60–300 | s | | [K] (M) |
| `pea_to_asystole` | 2–10 | min | | [K] (M) |
| `vf_to_asystole` | 10–20 | min | | [K] (L–M) |
| `pulse_loss_sbp` (radial / femoral / carotid) | 50–70 / 40–60 / 30–50 | mmHg | For a "check pulse" interaction | [C39] (M), [G] |
| `lazarus_prob` (brain destroyed, heart beating) | 0.1–0.2 | p | Within 1–10 min | [C16] (M), [G] |
| `final_exhalation` | at the last gasp, or 5–30 s after arrest if there are no gasps | — | Audio: sigh or rattle | [K] (M), [G] |
| Game time | 1× until 60 s after arrest, then 4× until the dead flag, then the post-mortem scale | — | | [G] |

### Visual/behavioural checklist: agonal phase
- After collapse the character lies still. Then, some seconds to a minute later, it takes a sudden deep **snorting gasp**: head tipping back, jaw opening. Then nothing. Another gasp 10–30 s later. They grow weaker and further apart over a few minutes and stop.
- One final passive sigh or rattle as the chest settles.
- Occasional small twitches in a hand or the face in the first minutes. Very rarely, after brainstem destruction, a slow reflex arm movement.
- No death rattle in fast deaths. Only in deaths that take hours (slow bleed, raised ICP).

---

## 11. The eyes: unconsciousness, dying, death and after

### 11.1 Reference geometry and normal behaviour (living, awake)

| Quantity | Value | Unit | Source |
|---|---|---|---|
| Globe diameter / axial length | ~24 / 23–24 | mm | [K] (H) |
| Globe volume / vitreous volume | 6.5–7 / ~4 | mL | [K] (M) |
| Cornea diameter (horizontal × vertical) | 11.5–12 × 10.5–11 | mm | [K] (H) |
| Central corneal thickness | 0.50–0.55 | mm | [K] (H) |
| Pupil diameter | 2–4 in bright light, 4–8 in the dark | mm | [K] (H) |
| Palpebral fissure (height × width) | 9–10 (8–11) × 28–30 | mm | [K] (H) |
| Upper lid position | Covers the top 1–2 mm of the cornea. The lower lid sits at the lower limbus | mm | [K] (H) |
| Intraocular pressure (IOP) | 10–21 (mean ~15–16) | mmHg | [K] (H) |
| Blink rate | 12–20/min at rest. Up to ~25 in conversation. 3–8 when concentrating | /min | [K] (M–H) |
| Blink duration | 250–400 total (closure ~70–100 ms, reopening slower) | ms | [K] (M) |
| Tear-film break-up time without blinking | > 10 (10–35) | s | [K] (M) |
| Saccades / fixations | Peak 400–700 °/s, 20–80 ms. Fixations 200–400 ms | — | [K] (H) |
| Pupil light reflex | Latency ~200–250 ms, constriction ~1 s | — | [K] (M) |
| Bell's phenomenon | Eyes roll **up and slightly out** when the lids close (most people) | — | [K] (M) |
| Colours | Sclera `#F1ECE2` (warm white). Palpebral conjunctiva `#D98C87`. Bulbar vessels fine `#B8424A` | sRGB | [G] |

### 11.2 Eye state table (drives the eye system)

| State | Lids | Gaze | Pupils | Reflexes | Blink | Surface | Source |
|---|---|---|---|---|---|---|---|
| Alert | Aperture 9–10 mm | Fixations and saccades on targets | 3–4 mm, reactive | Corneal +. Oculocephalic suppressed by fixation | 12–20/min | Glossy | [K] (H) |
| Pain / fear (sympathetic surge) | **Lid retraction**: 11–12 mm, white showing above the iris | Rapid scanning, then fixed on the threat | +1–2 mm within 0.5–2 s | + | Burst of blinks, then staring | Glossy, tearing | [K] (M) |
| Haemorrhagic shock III–IV | Heavy lids, 5–8 mm. Eyes look **sunken** (periorbital hollowing) | Vacant, slow saccades, poor tracking | Normal to large, **sluggish** | + | 5–10/min | Normal. **Pale conjunctiva** | [K] (M) |
| Syncope / heart destroyed / sudden loss of brain perfusion | **Stay open** | **Conjugate upward deviation (10–30°) for 2–10 s** or lateral, then drift to midline | Dilating | Lost within tens of seconds | **Stops** | Glossy at first | [C11] (M) |
| Knockout / concussion | Open or closed (≈50/50 `[G]`) | Vacant, may briefly roll up | Equal, reactive | + | Absent while unconscious | Glossy | [K] (M) |
| Generalised seizure | **Open (~90%+)**, lids may flutter | Deviated up or to one side (**away** from a cortical focus). Nystagmoid jerks | **Dilated, unreactive** during the seizure | Absent during | None | Tearing | [C24] [C19] (M) |
| Postictal | Half-closed | Roving, slightly divergent | Sluggish | Returning | Rare | — | [K] (M) |
| Coma, brainstem intact | Closed or partly open. **A lifted lid closes again slowly** (1–2 s) | **Slightly divergent**. Slow **roving** horizontal movements. **Doll's eyes present** (eyes counter-rotate when the head turns) | Small to normal, **reactive** | Corneal + | Rare | Glossy | [C19] (H) |
| Destructive hemisphere lesion | Any | **Conjugate deviation toward the lesion** | Normal | + | — | — | [C19] (H) |
| Thalamus / diencephalon | Any | **Down and in** | Small, reactive | + | — | — | [C19] (M) |
| Pons | Any | No horizontal movement. **Ocular bobbing** (fast down, slow up). Skew. "Wrong-way" deviation (away from the lesion) | **Pinpoint 1–2 mm** | Corneal lost | None | — | [C19] (H) |
| Midbrain | Any. Ptosis with a third-nerve lesion | Dysconjugate. **Down and out** (CN III). Vertical gaze lost. Skew | **Mid-position 4–6 mm, fixed** | Lost | None | — | [C19] (H) |
| Uncal herniation | Ipsilateral ptosis | Ipsilateral eye down and out | **Ipsilateral blown (6–9 mm) fixed**, then both | Lost progressively | — | — | [C19] (H) |
| Locked-in (ventral pons) | Open | **Only vertical movement and blinking** (voluntary) | Normal | + | Voluntary | Glossy | [C19] (H) |
| C1–C3 cord, awake, apnoeic | Normal, wide | Normal, darting, terrified | Normal, then dilate as SpO₂ falls | + until loss of consciousness | Normal until loss of consciousness | Glossy | [K] (H) |
| **Brain death / death** | **Stay where they were at the moment tone was lost.** Usually part-open (§11.3) | **Neutral or slightly divergent. No movement. Moves rigidly with the head (doll's eyes absent)** | **4–9 mm, fixed** (§11.5) | **All absent** (corneal, light, oculocephalic) | **None** | Gloss fades over minutes to hours (§11.6) | [C17] [C18] (H) |

### 11.3 Eyelids at death: open, half-open or closed?
- **Mechanics** `[K] (M)`:
  - Opening the eye is **active**. The levator palpebrae (CN III) does most of the work, and the sympathetic Müller's muscle adds ~2 mm.
  - Closing it is **also active**, by the orbicularis oculi (CN VII).
  - At death both lose tone. The lid then rests wherever passive forces leave it. For an eye that was open, the lid **drops a few mm** (loss of Müller's tone alone gives ~1–2 mm of ptosis, as in Horner's syndrome), and the eye usually ends up **partly open**.
  - An eye that was **closed** tends to stay closed, or to part slightly.
- **Clinical evidence**: in a prospective study of dying cancer patients, **"inability to close the eyelids"** was one of a handful of highly specific bedside signs that death was expected **within 3 days** [C41] `(M)`. Lid closure fails before death.
  - *corrected: was cited to "[C40] [C41]".* The fact-checker recalls that the eyelid sign comes from the 2015 *Cancer* paper [C41]. Its eight highly specific signs were: nonreactive pupils, decreased response to verbal stimuli, decreased response to visual stimuli, **inability to close the eyelids**, drooping of the nasolabial fold, neck hyperextension, grunting of the vocal cords, and upper GI bleeding.
  - The 2014 *Oncologist* paper [C40] studied ten other signs: Cheyne–Stokes breathing, death rattle, apnoea periods, respiration with mandibular movement, peripheral cyanosis, radial pulselessness, and others.
  - Recall, not web-verified.
- **Funeral practice**: the eyes of the dead commonly **do not stay closed by themselves**. Morticians routinely set eye caps or adhesive under the lids `[K] (H)`.
- **Forensic observation**: bodies from sudden violent deaths of awake people are frequently found with the eyes **open or partly open** `[K] (M)`. **No prevalence study was located in this session.** The distribution below is therefore a game-design choice. *Fact-check: the fact-checker also knows of no prevalence study. The distribution stays [G]. The mechanics are plausible but unverified (L–M).*
- **Suggested distribution** `[G]`:

| Death type | Open (aperture 6–10 mm) | Half-open (2–6 mm) | Closed (0–2 mm) | Reason |
|---|---|---|---|---|
| Sudden, awake victim (brainstem hit, heart shot, high cord) | 0.55 | 0.35 | 0.10 | Eyes were open when tone vanished |
| Slow death through lethargy and coma (bleeding out, raised ICP) | 0.20 | 0.45 | 0.35 | Lids were drooping or closed before death |
| After a seizure or knockout that progressed to death | 0.30 | 0.45 | 0.25 | |

- **Lid behaviour at the moment of death**: an open lid **drops 2–4 mm over 1–3 s** as levator and Müller tone fail. It **never blinks shut** `[K] (L–M)`, `[G]`.
- **Player interaction**:
  - Closing a dead character's eyes by hand: before rigor, the lids **creep back open 1–3 mm** over 1–5 min in about half the cases `[G]` on `[K]` (funeral practice).
  - After rigor (≥ 2–4 h), the lids stay where they are placed.
  - A living unconscious character's lifted lid slowly closes again. A dead character's lid stays up.
- **Swelling overrides everything**: orbital haematoma or raccoon eyes can **push the lids shut** in the living (§11.8).

### 11.4 Gaze at death: do the eyes roll up?
- **Mostly no.**
  - The dramatic upward roll ("whites of the eyes") belongs to **transient unconsciousness**: syncope [C11], seizures, and Bell's phenomenon when the lids close.
  - Once all tone is lost, the globes settle near the **anatomical position of rest**: close to straight ahead, with **slight divergence** (each eye a few degrees outward) and sometimes slight elevation `[K] (L–M)`.
- **Dysconjugate** resting positions (one eye skewed or turned out) are common after **brainstem** injury or third-nerve damage `[C19] (M)`.
- **In the transition**: if the character lost consciousness with an upward or sideways deviation, animate a **drift back toward the rest position over 10–60 s** as tone disappears `[G]`.
- **Doll's eyes are absent after death.** When the head is turned, the eyes turn with it, as if glued to the skull [C17] `(H)`. This is a cheap, convincing tell for the player.
- **No micro-movements, no saccades, no nystagmus** after death `[K] (H)`.

### 11.5 Pupils: dilation, fixation, and after death
- **Global ischaemia** (heart destroyed, exsanguination to arrest, asphyxia): pupils begin to **dilate ~30–45 s** after cerebral circulation stops and are **widely dilated (6–8+ mm) and unreactive by ~1–2 min** `[K] (M)`. ≈ recall-consistent: resuscitation texts teach "dilation begins within ~45 s, full dilation by 1–2 min". Not web-verified. No primary measurement series was identified.
- **At brain death**, guidelines describe pupils **fixed at mid-size to dilated, 4–9 mm**. **Pinpoint pupils are not consistent with brain death alone** (think drugs or a pontine lesion) [C17] `(H)`.
- **After death** `[K] (M)` [C42] [C43]:
  - Pupil size is **variable and unreliable**, typically **mid-dilated (≈ 4–6 mm, range 3–8)**.
  - As rigor affects the iris muscles over hours, the pupils can **constrict somewhat and become unequal** (anisocoria ≤ 1–2 mm) or slightly irregular.
  - **Game**: at arrest + 2 min, pupils are at 6–8 mm. Over the next 2–6 h they relax to 4–6 mm with random anisocoria up to 1 mm.
- **Pupil colour**: black (`#0A0A0A`) until the cornea clouds. After clouding, the pupil reads as **grey** (`#6E7274`) `[G]`.
- **Supravital pupil response to eye drops**: the iris can still react to drugs for many hours after death. This is forensic-mode material only `[C43] (L)`.

### 11.6 The surface of the eye after death

| Change | Onset: eyes open | Onset: eyes closed | Appearance | Colour / shader target | Source |
|---|---|---|---|---|---|
| **Blink and corneal reflex lost** | At loss of brainstem function (seconds) | — | No blink | — | [C17] (H) |
| **Tear film breaks up** | **10–30 s** after the last blink | — | Tiny dry spots. The corneal highlight becomes irregular | `gloss` 1.0 → 0.8 | [K] (M) |
| **Loss of lustre ("glazed eye")** | **Minutes to ~1 h** | Slower | Cornea dull, highlight blurred | `gloss` → 0.4 by 1 h | [K] (M) |
| **Corneal clouding (turbidity)** | Begins **~1–2 h**, obvious at **3–6 h**, opaque at **12–24 h** | Begins **~12 h**, obvious at **~24 h** | Grey-white haze. The iris and pupil fade from view | `corneal_opacity` 0 → 0.3 (6 h) → 0.7 (24 h). Tint `#C9CFCF` | [K] [C42] [C43] (M). ≈ recall-consistent (teaching: ~2 h open vs ~24 h closed). Not web-verified |
| **Scleral drying → *tache noire*** | Yellowish parchment triangles at **~1–3 h**, then **brown-black at ~3–6 h** (range 1–12 h; faster when warm, dry or windy) | Absent (only the exposed strip dries) | **Horizontal triangles or bands in the exposed white of the eye**, one each side of the cornea, base toward the cornea. The dark colour is the choroid seen through the thinned, dried sclera | `dry_band` → `#CDB48C`, then `tache_noire` `#5B3F2E` → `#30231B` | [K] [C42] (M). ≈ recall-consistent ("within a few hours, from ~3 h, with the eyes open"). Timing depends strongly on the environment. Not web-verified |
| **Loss of intraocular pressure** | IOP falls steeply in the first 1–2 h. **Globe soft by ~2–4 h** | Same | The eye dents under a fingertip. The cornea may **wrinkle** | `iop` 15 → < 5 mmHg by 2 h | [K] (L–M) |
| **Ripault's sign** | From ~30 min | Same | Squeezing the eye makes the pupil **oval, and it stays oval** (in life it springs back) | Interaction hook | [K] (L) |
| **Sunken globes** | Visible at 12–24 h | Later | Eyes recede into the orbits (drying, loss of pressure) | Push the globe back 1–3 mm | [K] (L) |
| **Retinal vessel segmentation ("boxcarring")** | **Minutes** after arrest; lasts ~1–2 h | Same | Only with an ophthalmoscope: blood in the retinal vessels breaks into segments | Forensic-mode close-up | [C47] (L–M) |
| **Vitreous potassium rise** | Linear, ~**0.19 mmol/L per hour** | Same | Lab value: **PMI (h) ≈ 5.26 × [K⁺] − 30.9** | Forensic-mode readout. ≈ recall-consistent. ✓ verified (arithmetic): 1 / 0.19 = 5.26, and the intercept implies K⁺ ≈ 5.9 mmol/L at death. **Gap**: the 95% limits of this formula are roughly **± 20 h** (recall), so it cannot resolve the first hours. Older formulas give different slopes (e.g. Sturner ~0.14 mmol/L/h). Show the readout with its error band | [C46] (M) |

### 11.7 Brainstem eye signs (for injured but living characters)

| Sign | Lesion | Look | Rule / magnitude | Source |
|---|---|---|---|---|
| **Skew deviation** | Anywhere in the posterior fossa (brainstem, cerebellum) | **Vertical misalignment**: one eye sits higher than the other | **Low (medullary) lesions: the eye on the lesion side is lower. Pontine and midbrain lesions: the eye on the opposite side is lower.** Magnitude 2–10° `[G]` | [C19] [K] (M) |
| Horizontal gaze palsy, "wrong-way eyes" | Pons (PPRF / CN VI nucleus) | Cannot look toward the lesion side. Eyes rest **away from the lesion** (toward the paralysed side) | Opposite of a hemisphere lesion | [C19] (H) |
| **Ocular bobbing** | Pons | Both eyes **jerk down fast, then drift slowly back** | A few to ~10 per minute | [C19] (M), rate [K] (L) |
| **Pinpoint pupils** | Pons (loss of sympathetic dilation) | 1–2 mm, reactive only under magnification | | [C19] (H) |
| Third-nerve palsy | Midbrain or uncal herniation | Eye **down and out**, **ptosis**, **dilated fixed pupil** | Ipsilateral | [C19] (H) |
| Internuclear ophthalmoplegia | MLF (pons/midbrain) | On sideways gaze, one eye fails to turn in. The other eye jerks (nystagmus) | | [K] (H) |
| Horner's syndrome | Lateral medulla, cervical cord (≥ T1), carotid injury | **Ptosis 1–2 mm, pupil ~0.5–1 mm smaller** on that side (more obvious in dim light) (corrected: was "pupil 1–2 mm smaller"; typical Horner anisocoria is ≤ 1 mm, recall) | Anhidrosis of the face | [K] (H) |
| Doll's eyes (oculocephalic reflex) | Tests the pons and midbrain | **Present**: eyes counter-rotate, staying pointed in space when the head turns (unconscious, brainstem intact). **Absent**: eyes move with the head (brainstem dead) | Counter-rotation gain ≈ 1 when present, 0 when absent | [C17] [C19] (H) |
| Roving eye movements | Light coma, brainstem intact | Slow, smooth, conjugate side-to-side drift | Seconds per sweep | [C19] (M) |
| Nystagmus | Cerebellum or vestibular system | Rhythmic jerks | | [K] (H) |

### 11.8 Haemorrhagic and other signs in and around the eye

| Sign | Cause in this game | Onset and look | Colour | Source |
|---|---|---|---|---|
| **Petechial haemorrhages** | Raised head venous pressure plus hypoxia: neck or chest compression (traumatic asphyxia from crushing weight), violent coughing or vomiting, seizures, some cardiac deaths. **Not** from bleeding out | **0.1–2 mm** pinpoint red dots on the palpebral conjunctiva first, then the bulbar conjunctiva, eyelids, and facial skin above the compression. Seconds to minutes of venous obstruction | `#8E1520` | [K] [C42] (M) |
| Traumatic asphyxia (Perthes) | Heavy chest compression | Face and neck **deep blue-purple**, dense petechiae, subconjunctival haemorrhages | Face `#5B3A6B` tint | [K] (M) |
| **Subconjunctival haemorrhage**: direct trauma | Punch, hammer, fragment | Bright red, flat, **sharply bordered**, with a visible posterior edge. Does not resolve after death | `#B3121C` [D01], `#C0141E` [D02:R54] | [D02:R54] (H) |
| **Subconjunctival haemorrhage from a skull-base or orbital-roof fracture** | Penetrating head GSW, heavy blows | Spreads forward from the orbit. **No visible posterior border** | Same | [K] (M) |
| **Orbital (retrobulbar) haematoma** | Orbital or skull-base fracture | **Proptosis 2–10 mm**, tense globe, lids swollen shut, chemosis. If pressure is high the pupil dilates and fixes (orbital compartment syndrome; vision lost if untreated for more than ~1–2 h) | Lids `#7A2E4A` → `#4B2F63` | [D01:S24] [K] (M) |
| **Raccoon eyes** (bilateral periorbital ecchymosis, sparing the tarsal plate) | Anterior skull-base fracture | Clinically 1–3 days after blunt fracture [D02:R51] [D02:R52]. With a penetrating GSW and orbital-roof fracture, **faint in 5–30 min and clear by 1–6 h while the heart beats** [D01:S24] (tagged there as [G] timing). **No progression after death** except slow gravitational seepage | as above | [D01:S24] [D02:R51] [D02:R52] |
| Hyphaema | Blunt blow to the eye | Blood in the front chamber that **settles into a level at the bottom** of the iris | `#9E1A22` | [K] (H) |
| Pale conjunctiva | Exsanguination | Pull the lower lid down: pale pink to white | `#EBCFCB` → `#EFDCD8` | [K] (H) |
| Conjunctival hypostasis (post-mortem) | Body face-down or head-down for hours | Congested, purple conjunctivae, with post-mortem dots (Tardieu-like) after several hours. **Do not confuse with antemortem petechiae** | `#6E2D4E` | [K] [C42] (M) |

### 11.9 Eye choreography by death type (real time; the first 60 s always at 1×)

**A. Brainstem (medulla/pons) gunshot**
- 0 s: lids flinch (startle), then **stay open**. The eyes jolt, then stop.
- 0–1 s: blinking ceases forever. Pupils pinpoint (pons) or mid-fixed (midbrain), or normal (pure medulla).
- 1–3 s: the upper lid drops 2–4 mm. The eyes rest **slightly divergent or skewed**.
- 60–180 s: pupils dilate with hypoxia (unless the midbrain was hit, in which case they are already fixed).
- Minutes: the gloss fades.

**B. Heart destroyed**
- 0–5 s: wide eyes, pupils dilate with fear, gaze on the wound or the attacker.
- 5–10 s: unfocused, blank stare.
- 8–15 s: loss of consciousness. **Eyes open, rolled up 10–30° for 2–10 s**, possibly with lid flutter during myoclonic jerks.
- 15–60 s: drift back to near straight ahead, slightly divergent. Lids half-open.
- 30–120 s: pupils widen to 6–8 mm and fix. Corneal reflex gone.
- If agonal gasps occur, the head moves with each gasp and **the eyes move with the head** (no counter-rotation).

**C. Slow exsanguination**
- Minutes: eyes sunken and dull, conjunctivae paling, blinking slower, gaze wandering. Lids grow heavy and **close in lethargy** (they may blink shut and struggle open).
- Loss of consciousness: lids half-closed.
- Terminal: pupils dilate and fix during the final gasps.
- The eyes are **less likely to be wide open** than in sudden deaths.

**D. C1–C3 cord (awake apnoea)**
- 0–60 s: eyes wide, darting and pleading. Blinking **normal or rapid**. Tears.
- 60–120 s: lips blue, gaze slows, pupils begin to widen.
- 90–180 s: loss of consciousness. Eyes stay open and drift slightly up or out, and blinking stops.
- Then as in B from the pupil stage.

**E. Herniation (raised ICP)**
- Hours: one pupil enlarges. The same-side lid droops and the eye drifts down and out.
- Coma: the other pupil fixes. The eyes are dysconjugate and doll's eyes are lost.
- At apnoea: both pupils wide and fixed, lids partly open.

### 11.10 Simulation parameters: eyes

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `lid_aperture_alert` | 9–10 | mm | | [K] (H) |
| `lid_aperture_fear` | 11–12 | mm | | [K] (M) |
| `lid_aperture_shock` | 5–8 | mm | | [K] (M), [G] |
| `lid_drop_at_death` | 2–4 over 1–3 s | mm | From the pre-death position | [K] (L–M), [G] |
| `lid_state_at_death_dist` | see §11.3 table | p | | [G] |
| `lid_reopen_after_manual_close` | p = 0.5, 1–3 mm over 1–5 min, only before rigor | — | | [G] on [K] |
| `blink_rate` alert / shock / unconscious / dead | 12–20 / 5–10 / 0–2 / 0 | /min | | [K] (M) |
| `gaze_rest_dead` | each eye 3–10° abducted, 0–5° elevated | ° | | [K] (L–M) |
| `syncope_upgaze` | 10–30° for 2–10 s (p 0.6–0.8) | ° / s | | [C11] (M), [G] |
| `gaze_drift_to_rest` | 10–60 | s | After loss of tone | [G] |
| `doll_gain` | 1.0 (brainstem intact, unconscious), 0 (dead or brainstem destroyed) | — | Head-turn counter-rotation | [C17] [C19] (H) |
| `pupil_alert` | 3–4 | mm | | [K] (H) |
| `pupil_hypoxic_dilation` | start 30–45 s, max 6–8+ mm at 60–120 s | — | | [K] (M) |
| `pupil_brain_death` | 4–9, fixed | mm | | [C17] (H) |
| `pupil_postmortem_relax` | to 4–6 over 2–6 h, anisocoria ≤ 1 mm | mm | | [K] [C42] (L–M) |
| `tear_breakup` | 10–30 | s after the last blink | | [K] (M) |
| `gloss_curve` (open) | 1.0 → 0.8 (1 min) → 0.4 (1 h) → 0.15 (6 h) | — | Closed eyes ×0.25 rate | [G] on [K] |
| `corneal_opacity` (open) | 0 (0–1 h) → 0.3 (6 h) → 0.7 (24 h) | — | Closed eyes: start at ~12 h | [K] (M), [G] |
| `tache_noire` | onset 3–6 h (1–12), 0 → 1 by 12 h. Open eyes only; exposed strip only | — | ×1.5 speed if warm and dry | [K] [C42] (M) |
| `iop_postmortem` | 15 → < 5 by 2 h | mmHg | Softness and wrinkling | [K] (L–M) |
| `vitreous_K_slope` | 0.19 | mmol/L/h | PMI = 5.26 × K − 30.9. Show a ± 20 h (95%) error band in the forensic readout (fact-check gap) | [C46] (M) |
| `petechia_size` | 0.1–2 | mm | Compression or asphyxia triggers only | [K] (H) |
| `proptosis_orbital_haematoma` | 2–10 | mm | Living only | [K] (M) |
| `skew_deviation` | 2–10 | ° vertical | Brainstem injury, living | [G] on [C19] |
| Colours | sclera `#F1ECE2`, pale conjunctiva `#EBCFCB`, dried band `#CDB48C`, tache noire `#5B3F2E` → `#30231B`, corneal haze `#C9CFCF`, clouded pupil `#6E7274`, petechiae `#8E1520` | sRGB | | [G] |
| Game time | Dying: 1×. Post-mortem surface changes on the post-mortem scale (§12.8) | — | | [G] |

### Visual/behavioural checklist: eyes
- **At death, the eyes do not close and do not roll back to show the whites.** They stay open or half-open, looking roughly straight ahead or slightly outward, and they stop moving entirely. They look "through" the player. Nothing tracks, nothing blinks.
- Seconds before loss of consciousness in a sudden death, the eyes may roll up briefly, then settle back.
- The pupils go wide and black within a minute or two. Hours later they are mid-sized, sometimes unequal.
- Turn a dead character's head: the eyes turn with it, rigidly. Turn an unconscious living character's head: the eyes lag and stay pointed at the same spot (doll's eyes).
- The shine of the eye dulls within the first hour. Over 3–6 h the corneas haze grey, and the exposed whites develop brown-black triangles on each side of the iris. By a day the corneas are milky.
- Press a dead eye after ~30 min: it is soft, and the pupil stays squashed oval.
- In the living, only after heavy trauma: bright red patches on the whites, a bulging purple-lidded eye, or a blood level in front of the iris.
- Brainstem injury in a living character: eyes pointing in different directions (one higher, one turned out), pinpoint or mid-fixed pupils, occasional sudden downward jerks.

---

## 12. The first 48 hours after death

### 12.1 The first minutes: primary flaccidity
- **All skeletal muscle goes limp** at death. This **primary flaccidity** lasts until rigor begins, typically **1–3 h** (range ~0.5–7 h) `[K] (M)` [C44].
- **Jaw**: masseter and temporalis tone ceases, and the **mandible drops open** under gravity. With the body supine and the head neutral or tipped back, the mouth opens to about **10–30 mm between the incisors** within seconds. With the face down or turned sideways, the mouth opens less `[K] (M)`, `[G]` magnitude. Rigor later **fixes the jaw in whatever position it has reached** (§12.6).
- **Tongue**: falls back in a supine body. It does not protrude unless there was neck compression `[K] (M)`.
- **Lids**: see §11.3.
- **Sphincters**: may relax. A small release of urine is possible (game p ≈ 0.2–0.3, 50–200 mL over 1–5 min, only if the bladder is not empty) `[G]` on `[K]`.
- **Body settling**: flaccid limbs fall to the lowest position. A supine head rolls to one side. Moving or pressing the chest of a dead body can push air past the vocal cords and produce a **groan or sigh** `[K] (M)`. It is a real and unsettling effect, and good for audio.

### 12.2 Blood after the heart stops
- **Spurting stops at the last effective heartbeat.** Arterial pressure falls to the **mean systemic filling pressure (~7–13 mmHg)** within **~30–90 s**, and arteries empty into veins `[K] (H)` [C51] [C52].
- After that, a wound bleeds **only by gravity**. Wounds **below** the main blood pool **drain** at the hydrostatic pressure (0.78 mmHg per cm of height difference). Wounds **above** it stop `[E]`/`[K] (H)`.
  - Scalp and face wounds on a face-down or head-down body can keep draining for a long time.
  - Suggested dependent-wound drainage `[G]`: 50–500 mL over 30–120 min, decaying exponentially (τ ≈ 20–40 min).
- In **sudden deaths**, blood often **stays liquid** for hours (post-mortem fibrinolysis), which lets drainage continue. In **slow deaths**, soft post-mortem clots ("currant jelly", "chicken fat") form in the vessels `[K] (M)` [C42] [C49].
- Wounds inflicted after death show no active bleeding, gape less, and have no vital reaction (see doc 02 §2.8) [D02:R22].
- **Drying**: exposed wound edges, abrasions and the lips dry into **brown parchment** over hours (lips `#6E2E2E`, parchment `#8A5A3C`) `[K] (M)`, `[G]` colours.

### 12.3 Pallor mortis
- The skin **pales within minutes to ~30 min** as capillaries empty. It is most obvious in the face, lips and nail beds `[K] (M)`.
- In light skin, use a desaturation and lightening of 20–40% over 15–30 min, **then** livor appears in the dependent areas `[G]`.
- After death from bleeding, the pallor is already present at death and is extreme.

### 12.4 Livor mortis (hypostasis)
Blood settles by gravity into the dependent capillaries and venules.

| Stage | Mean (range) | Source |
|---|---|---|
| First patches visible | **~0.75 h (0.25–3 h)** | [C44] [C43] (M) |
| Patches merge (confluence) | **~2.5 h (1–4 h)** | [C44] (M) |
| Maximum intensity | **~9.5 h (3–16 h)** | [C44] (M) |
| Blanches **completely** under thumb pressure until | **~5.5 h (1–20 h)** | [C44] (M) |
| Blanches **incompletely** (strong pressure) until | **~17 h (10–30 h)** | [C44] (M) |
| **Shifts completely** to the new lowest side if the body is turned, until | **~3.75 h (2–6 h)** | [C44] (M) |
| **Shifts partly** (old and new patterns both visible), until | **~11 h (4–24 h)** | [C44] (M) |
| Common teaching summary | "Appears in 20–30 min to 2 h, fixed at 8–12 h" | [K] [C42] (M) |

≈ recall-consistent: every Mallach mean and range in this table matches the fact-checker's independent recall of the Henssge & Madea 2004 tabulation. Not web-verified. "Faint livor after exsanguination" is also standard teaching.

- **Pattern**:
  - **Contact pallor**: pale areas where the body presses on the ground. In a supine body these are the shoulder blades, buttocks, calves and back of the head. Clothing folds and straps leave pale lines.
  - Face-down bodies show **facial and conjunctival congestion**, and after hours small dark haemorrhagic dots (Tardieu spots) `[K] (H)` [C42].
- **Colour**:
  - Normally dusky **red-purple**.
  - Pinker in cold bodies (or with carbon monoxide or cyanide; not modelled).
  - **Faint, patchy and late after death from bleeding** (little blood left) `[K] (H)`.

| Livor stage | Colour (sRGB, opacity over skin) |
|---|---|
| Early | `#CC8A8F` at 20–30% |
| Established | `#9A4E6B` at 50–70% |
| Intense / fixed | `#6E2D4E` at 70–85% |
| Tardieu spots | `#3E1330` dots, 0.5–2 mm |

  Colours are `[G]`. Multiply the opacity by `(1 − loss_frac × 1.5)` for exsanguinated bodies `[G]`.

### 12.5 Algor mortis (cooling)
- **Henssge's double-exponential model** (rectal temperature), from which the Henssge nomogram is built [C45] [C43] `(M–H)`:
  - For ambient temperature Ta ≤ 23.2 °C:
    `Q = (Tr − Ta) / (37.2 − Ta) = 1.25·exp(B·t) − 0.25·exp(5·B·t)`
  - For Ta > 23.2 °C:
    `Q = 1.11·exp(B·t) − 0.11·exp(10·B·t)`
  - `B = −1.2815 · (c·m)^(−0.625) + 0.0284` (per hour). Here m is body mass in kg, and c is the corrective factor: 1.0 for naked, dry, still air; about 1.1–1.4 for clothed or covered; below 1 for wet or moving air or water.
- **Worked values** `[E]` for the reference body (m = 75 kg, c = 1, Ta = 20 °C, so B = −0.0579 /h):

| t (h) | 1 | 2 | 4 | 6 | 8 | 12 | 18 | 24 | 36 | 48 |
|---|---|---|---|---|---|---|---|---|---|---|
| Rectal temp (°C) | 37.1 | 36.7 | 35.7 | 34.4 | 33.1 | 30.6 | 27.6 | 25.4 | 22.7 | 21.3 |

  ✓ verified (arithmetic).
  - The fact-checker recomputed B = −1.2815 × 75^−0.625 + 0.0284 = −0.0579 /h, then every column of the table. All values match to 0.1 °C. Examples: t = 6 h gives Q = 0.839, so 34.4 °C; t = 24 h gives Q = 0.311, so 25.4 °C.
  - The formula constants themselves (1.25 / 0.25 / 5; 1.11 / 0.11 / 10; −1.2815, −0.625, 0.0284; the 23.2 °C switch; 37.2 °C at death) match the fact-checker's recall of Henssge 1988. They are ≈ recall-consistent, not web-verified.
  - **Gap added by the fact-check** (recall, M): the nomogram's 95% error limits are about **± 2.8 h** under standard conditions, widening to ± 4.5 h and ± 7 h at longer intervals or when corrective factors are applied. A forensic-mode readout should show this band.
  - The model also assumes 37.2 °C at death. A victim who was hypothermic from blood loss, or hyperthermic after a struggle, shifts the whole curve. Allow `T_death` as a state input.

  Note the **initial plateau** (~0.1–0.5 °C in the first 2 h), then ~0.6–0.7 °C/h. That is consistent with the rule of thumb of "~1 °C/h after a plateau" for smaller or lightly clothed bodies `[K] (M)`.
- **The surface cools faster than the core** `[K] (M)`:
  - hands, feet and face feel cool within **1–2 h**;
  - the trunk stays warm to touch for several hours;
  - the armpits stay warm longest.
- **Game use**: drive a `skin_warmth` value for touch and interaction, and (optionally) a thermal-view shader, from these curves.

### 12.6 Rigor mortis
- **Mechanism**: ATP depletion locks actin–myosin cross-bridges. It resolves as proteins break down. It is **faster** with heat and with **heavy muscular activity just before death** (struggling, seizures, running), and **slower** in the cold `[K] (H)`.
- **Timings** (Mallach's data as tabulated by Henssge & Madea) [C44] [C43] `(M)`:

| Stage | Mean (range) |
|---|---|
| Onset (detectable) | **~3 h (0.5–7 h)** |
| Re-establishes after being broken by force, if broken before | **~8 h (2–8 h)** |
| Fully developed | **~8 h (2–20 h)** |
| Persists | **~57 h (24–96 h)** |
| Resolved | **~76 h (24–192 h)** |
| Teaching shorthand | "**12 h to develop, 12 h fixed, 12 h to resolve**" in temperate conditions [K] [C42] (M) |

≈ recall-consistent: onset 3 h (0.5–7), full 8 h (2–20), persistence 57 h (24–96), resolution 76 h (24–192), and re-establishment up to ~8 h all match the fact-checker's recall of the Mallach data. So does Nysten's order (lids/jaw first, legs last). Not web-verified.

- **Order** (Nysten's rule, the order in which stiffness becomes detectable): **eyelids and jaw → face and neck → arms → trunk → legs**. It resolves in about the same order `[K] (M)`. The **heart** stiffens early, within ~1 h `[K] (L)`.
- **Breaking rigor**: forcing a stiff joint breaks the rigor there. If this happens early (before ~8 h), it can **partly re-form**. Later it stays broken `[C44] (M)`.
- **Cadaveric spasm** (instant rigor that freezes the last grip) is rare and disputed. **Do not use it by default**. Allow a hand to stay clenched on an object in ≤ 1% of deaths with intense activity at the moment of death `[K] (M)`, `[G]`.
- **Implementation** `[G]`:
  - Keep a per-joint-group stiffness `s(t)` in [0, 1]. Groups: lids, jaw, neck, upper limbs, trunk, lower limbs. Each starts at its onset time (offset by Nysten order: jaw +0 h, neck +0.5 h, arms +1 h, trunk +1.5 h, legs +2 h).
  - Ramp `s` to 1 at "full".
  - Map `s` to joint angular damping and to limits clamped around the current pose.
  - On an external torque above `τ_break × s`, set that group's `s` to 0.2 and allow re-growth to 0.6 if t < 8 h.

### 12.7 Supravital reactions (optional "forensic mode")
Tissues that are still alive respond for hours after death. These are forensic-mode details only. **Check Madea [C43] before using any of these numbers** `(L)`:
- **Mechanical excitability of muscle**: striking the biceps produces a visible contraction and local bulge ("idiomuscular swelling") for ~1.5–2.5 h. A persistent local bulge can be raised for up to ~4–5 h or longer `[C43] (L)`.
- **Electrical excitability of facial muscles** (eyelid): strong reactions spreading over the face last for several hours, up to roughly 5–8 h. **Weak, local reactions of the upper eyelid can persist much longer, up to ~13–22 h** `[C43] (L)`. *corrected: was "up to roughly 5–8 h" with no long tail. The fact-checker recalls Madea's graded scale, in which the weakest grade (local upper-eyelid twitch) is reported up to ~22 h. Low confidence, not web-verified.*
- **Pupil response to eye drops**: lasts for many hours `[C43] (L)`.

### 12.8 Post-mortem master timeline (real vs game)

| t_real after arrest | What changes | At 120× (default) | At 720× (fast-forward) |
|---|---|---|---|
| 0–1 min | Spurting stops. Last gasp or sigh. Jaw drops. Lids settle. Pupils dilating | Real time (1×) | 1× |
| 1–5 min | Pupils wide and fixed. Tear film broken. Fine twitches may occur. Gravity drainage from dependent wounds | 1× → 4× | 4× |
| 5–30 min | Pallor mortis. Eye gloss fading. Blood pooling around dependent wounds | 5–15 s | 1–3 s |
| 30–60 min | First livor patches (from ~20–45 min). Hands and face cool to touch. Ripault's sign present | 15–30 s | 3–5 s |
| 1–3 h | Livor confluent. Rigor starts in the jaw and eyelids. Globe soft. Corneal haze begins (open eyes). Yellow dried bands in the exposed sclera | 0.5–1.5 min | 5–15 s |
| 3–6 h | **Tache noire** darkening. Rigor in the neck and arms. Livor still shifts if the body is turned. Rectal temp **~36–34 °C** (corrected: was ~35–34 °C; the §12.5 model gives 36.3 °C at 3 h and 34.4 °C at 6 h for the reference body at 20 °C) | 1.5–3 min | 15–30 s |
| 6–12 h | Rigor complete. Livor maximal and becoming fixed. Corneas clearly cloudy (open eyes). Temp ~34–31 °C | 3–6 min | 30–60 s |
| 12–24 h | Livor fixed. Cornea opaque by 24 h (open). Closed eyes begin to cloud. Globes sunken. Temp ~31–25 °C | 6–12 min | 1–2 min |
| 24–48 h | Rigor persists, then begins resolving (from ~24–36 h in warm conditions). Temp approaching ambient. First decomposition signs, such as greenish discolouration of the right lower abdomen from ~24–36 h (out of scope) | 12–24 min | 2–4 min |

### 12.9 Simulation parameters: post-mortem

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `pm_clock_start` | circulatory arrest | — | | [K] (H) |
| `jaw_drop` | 10–30 within 5–30 s | mm | Supine; less if prone or on the side | [K] (M), [G] |
| `mean_filling_pressure` | 7–13 within 30–90 s | mmHg | Arterial jets end at the last beat | [C51] [C52] (M) |
| `pm_drainage` | 50–500 mL, τ 20–40 min, dependent wounds only | — | Hydrostatic head 0.78 mmHg/cm | [E]/[G] |
| `pallor_mortis` | 15–30 | min | Desaturate and lighten 20–40% | [K] (M), [G] |
| `livor_onset` / `livor_confluent` / `livor_max` | 0.75 (0.25–3) / 2.5 (1–4) / 9.5 (3–16) | h | | [C44] (M) |
| `livor_blanch_complete_until` / `incomplete_until` | 5.5 (1–20) / 17 (10–30) | h | Thumb-press interaction | [C44] (M) |
| `livor_shift_complete_until` / `partial_until` | 3.75 (2–6) / 11 (4–24) | h | On turning the body | [C44] (M) |
| `livor_opacity_exsanguinated` | × (1 − 1.5 × loss_frac), min 0.1 | — | | [G] on [K] |
| `algor_model` | Henssge (§12.5) | — | c = 1.0 naked, 1.1–1.4 clothed | [C45] (M–H) |
| `rigor_onset` / `rigor_full` / `rigor_persist` / `rigor_resolved` | 3 (0.5–7) / 8 (2–20) / 57 (24–96) / 76 (24–192) | h | Scale × 0.5 if hot or after intense activity; × 1.5–2 if cold | [C44] (M), scaling [K]/[G] |
| `rigor_reestablish_window` | 8 (2–8) | h | | [C44] (M) |
| `rigor_order_offsets` | jaw/lids 0, neck +0.5, arms +1, trunk +1.5, legs +2 | h | | [K] (M), [G] |
| `cadaveric_spasm_prob` | ≤ 0.01 | p | Intense activity at death only | [G] |
| `urine_release_prob` | 0.2–0.3 | p | 50–200 mL | [G] |
| `postmortem_groan_on_chest_press` | p = 0.3 per heavy press, first 12 h | — | Audio only | [G] on [K] |
| Game time | See §12.8 | — | | [G] |

### Visual/behavioural checklist: post-mortem
- The instant of death: the jet stops mid-rhythm. The wound turns to a slow drip or stops. The body goes completely slack, the jaw sags open, the lids settle half-open.
- Minutes: the face drains to a waxy pallor, and the eye shine dulls.
- Within the hour: faint pink-purple blotches appear on the down-side of the body, except where it presses on the floor. Hands feel cool.
- Hours: the blotches merge into a deep purple band. The jaw and neck stiffen, then the arms, then the legs. Try to bend an arm at 8 h: it resists, and if forced it gives way suddenly (no bone sound) and then stays loose.
- The corneas cloud milky-grey. Brown-black triangles appear on the exposed whites. The eyes feel soft and sink slightly.
- Moving the body can squeeze a groan out of it, and makes blood and froth leak from the mouth and dependent wounds.
- A bled-out body has barely any livor and looks white overall.

---

## 13. Physiology state machine: proposal for engineers

### 13.1 State vector (per character)
- **Circulation**:
  - `bv_mL`, `loss_frac`, `hr`, `sbp`, `dbp`, `map`, `cvp`.
  - `rhythm` ∈ {sinus, tachy, brady, VF, PEA, asystole}.
  - `pump_fraction` (0–1, cardiac damage), `tamponade_mL`, `neurogenic` (bool), `t_arrest`.
- **Respiration**:
  - `resp_drive` ∈ {normal, cheyne_stokes, cnh, apneustic, ataxic, gasping, none}.
  - `resp_capacity` (from the cord level, §6.7).
  - `airway` ∈ {open, stertor, blood_flooded, obstructed}.
  - Per lung: `{ok, pneumo, open_pneumo, tension}` plus `haemothorax_mL`.
  - `spo2`.
- **Brain**:
  - `cerebral_o2_s`: the brain oxygen reserve in seconds (below).
  - `icp`, `cpp`, `haematoma_mL`.
  - Damage 0–1 for: `hemi_L`, `hemi_R`, `diencephalon`, `midbrain`, `pons_teg`, `pons_basis`, `medulla`.
  - `seizure` ∈ {none, tonic, clonic, postictal}.
  - `gcs_e/v/m`.
- **Cord**: `cord_level`, `cord_complete`, `cord_syndrome`.
- **Motor per limb** ∈ {voluntary, weak, flaccid, decorticate, decerebrate, fencing, tonic, clonic, rigor}.
- **Eyes, per eye**: `lid_mm`, `yaw`, `pitch`, `pupil_mm`, `pupil_reactive`, `corneal_reflex`, `doll_gain`, `blink_on`, `gloss`, `opacity`, `dry_band`, `tache`, `iop`, `subconj`, `petechiae`, `proptosis_mm`.
- **Post-mortem**: `pm_h`, `core_temp`, `livor_intensity`, `livor_fixation`, `rigor_s[group]`, `pallor`.

### 13.2 Consciousness resolver (evaluate every tick, first match wins) `[G]` on the sources above
1. `medulla > 0.5`, `pons_teg > 0.5`, `midbrain > 0.5`, `diencephalon > 0.5`, or `(hemi_L > 0.6 and hemi_R > 0.6)` → **coma**. Choose GCS M by the lowest level destroyed (§4.1).
2. `cerebral_o2_s ≤ 0` → **unconscious** (syncope or anoxia). Choose the syncope eye and myoclonus pattern if it is the first entry.
3. `seizure ≠ none` → unconscious.
4. `ko_timer > 0` → unconscious (knockout; fencing response on entry, p = 0.66).
5. `cpp < 30` or `spo2 < 0.6` → coma. `cpp < 50` or `loss_frac > 0.3` → confused.
6. Otherwise conscious. Apply focal deficits from the damaged hemisphere (§3.3).

**Brain-oxygen reserve model** `[E]`/`[G]`:
- `perf = clamp((map − 20) / 40, 0, 1) × (cpp_ok ? 1 : cpp / 50) × spo2_factor`
- If `perf < 0.5`: `cerebral_o2_s -= (1 − perf) × dt`.
- Else: `cerebral_o2_s = min(8, cerebral_o2_s + dt)`.

Start at 8 s. With a destroyed heart, add ~4 s of residual pressure decay. That reproduces the 10–15 s action window [C7] and the 5–10 s loss of consciousness after cerebral arrest [C9].

### 13.3 Main transitions

| From | To | Condition | Duration / notes | Source |
|---|---|---|---|---|
| Alert | Shock stages | `loss_frac` crosses 0.15 / 0.30 / 0.40 | Drive HR, RR, colour and eyes (§7) | [C1] |
| Any | Syncope (unconscious) | reserve exhausted; or upright with loss 0.20–0.30; or paradoxical bradycardia roll | Eyes up 2–10 s, myoclonus 0.9 | [C11] [C4] |
| Any | Knockout | Blunt head impact above threshold (doc 02 energies) | 5–60 s. Fencing 0.66 | [C20] |
| Any | Seizure | Head injury roll (§4.3) | Tonic 10–20 s, then clonic 30–60 s, then postictal | [C22] [C23] |
| Conscious | Apnoea-awake | Cord C1–C3 complete | LOC 90–180 s, arrest 4–10 min | [K] |
| Any | Apnoea | Medulla destroyed; or herniation end-stage; or impact apnoea | Arrest 4–10 min | [K] [C26] |
| Any | Posturing | Lesion level (§4.1); or herniation stage | Episodic | [C19] |
| Herniating | Cushing | ICP within 10–20 mmHg of MAP | 5–30 min, then apnoea | [C31] |
| Circulating | PEA | `loss_frac ≥ 0.55` (fact-check: 0.45–0.50 for rapid bleeds > 500 mL/min, §7.4); or MAP < 20–25; or tension/tamponade end-stage; or hypoxic brady end-stage | | [K] |
| Circulating | VF | Direct cardiac hit (p 0.3 [G]); commotio cordis (p 0.01–0.03) | | [K] |
| PEA / VF | Asystole | 2–10 / 10–20 min | | [K] |
| Arrest | Agonal gasping | Medulla intact, p 0.3–0.5, start 10–60 s | 1–5 min | [C12] [C13] |
| Arrest | Dead flag | +5 min | Post-mortem clock already running | [C14] |
| Dead | Post-mortem stages | `pm_h` | §12 | [C44] [C45] |

### 13.4 Canonical deaths: summary (real vs game)

| Scenario | Loss of consciousness (real) | Arrest (real) | Signature visuals | Game length (suggested) |
|---|---|---|---|---|
| A. Medulla / pons gunshot | 0 s | 4–10 min (hypoxic) | Cut-strings drop, no breathing, eyes fixed open, pinpoint or mid pupils | ~2–3 min |
| B. Heart destroyed | 8–15 s | 0 s (no output) | 10 s of action, collapse, eyes up, jerks, gasps | ~1.5–2 min to dead flag |
| C. Stab to heart (tamponade) | 5–60 min | 5 min – 2 h | Bulging neck veins, grey, breathless | 3–8 min |
| D. Lung gunshot + tension / haemothorax | 10–60 min | 15–90 min | Frothy haemoptysis, sucking wound, blue lips | 4–8 min |
| E. Carotid or femoral transection | 2–4 min | 3–7 min | Tall pulsing jet that shrinks, grey pallor | 2–3 min |
| F. Slow multi-wound bleed (~100 mL/min) | 24–28 min (corrected: was 25–50 min) | 29–40 min (corrected: was 35–80 min; see the recomputed §7.5 table) | Full stage progression, thirst, confusion | ~5–6 min (corrected: was 4–8 min) |
| G. C1–C3 cord | 1.5–3 min (awake until then) | 4–10 min | Awake, silent, eyes pleading, blue lips | ~3 min |
| H. C5 cord | None | None acutely | Belly breathing, slow pulse, warm pink skin, flexed elbows | Persistent |
| I. T8 cord | None | None | Drags with arms, legs flaccid, no pain reaction | Persistent |
| J. Unilateral frontal .22 | 0–60 s (often transient) | Hours, or none | Staggers, talks confusedly, hemiparesis if motor | Persistent or slow |
| K. Hammer to temple (epidural haematoma) | Brief, then lucid interval | 1–6 h | Talk and die, blown pupil, Cushing's triad | 8–12 min |
| L. Punch knockout | 0 s, recover in 5–60 s | None | Fencing arms, snoring, dazed recovery | Real time |

### 13.5 Tick order (20 Hz alive, 2–5 Hz dead) `[E]`
1. Apply new injuries: update damage fields, wounds, `cord_level`, lungs, `tamponade`.
2. Circulation: bleeding (§7.5), then `bv`, then MAP/HR from `loss_frac`, neurogenic caps, `pump_fraction`, then rhythm.
3. Respiration: drive × capacity × airway × lungs, then `spo2`.
4. Brain: `icp`, `cpp`, then the oxygen reserve, then the consciousness resolver, then seizure and posturing timers.
5. Motor: per-limb control, then ragdoll drive targets and strengths.
6. Eyes: derive outputs from the state (§11.2, §11.10), then set material uniforms and bones.
7. Skin: pallor, cyanosis (only if Hb is adequate), mottling, flush. Mask updates at ≤ 1 Hz.
8. Post-mortem (if dead): `pm_h += dt × pm_scale`. Update the livor mask, rigor per group, temperature, and eye surface.

---

## 14. Common realism mistakes in games and films (with the fix)

| Mistake | Reality | Fix |
|---|---|---|
| Eyes close peacefully at death | Lids usually stay open or half-open. Closing is an active movement | §11.3 distribution. Lids drop 2–4 mm, never shut |
| Eyes roll back to the whites at death | Upward roll is a feature of syncope and seizures, and is transient | Brief upgaze only in the syncope phase, then near-neutral, slightly divergent |
| Pinpoint pupils in the dead | Dead pupils are mid-to-wide (4–9 mm). Pinpoint means a pontine lesion or drugs | §11.5 |
| Heart shot = instant drop | 10–15 s of possible action | §8 |
| Bullets throw bodies backward | Knock-back 0.01–0.18 m/s | Fall along the existing lean [D01:S30] |
| Any head shot = instant death | Brainstem = instant. Hemisphere wounds may leave the victim conscious and acting | §2, §3 |
| Blood keeps spurting after death | Jets stop at the last beat. Only gravity drainage remains | §7.6, §12.2 |
| Instantly stiff corpse | Primary flaccidity for hours. Rigor starts ~3 h and is full at ~8 h | §12.6 |
| Paralysed limbs twitch and withdraw | Spinal shock: flaccid and areflexic for the first day | §6.4 |
| Bled-out corpse turns blue | Too little haemoglobin for cyanosis. White-grey | §1, §7.7 |
| Death rattle in every death | Only slow deaths (hours) | §10.5 |
| Livor at the moment of death | First patches at ~20–45 min, strong after hours | §12.4 |
| Corneas cloud immediately | Hours (open eyes) to a day (closed) | §11.6 |
| Tension pneumothorax shown by tracheal deviation | Late and uncommon. Distress, tachycardia and falling saturation come first | §9.2 |
| Every KO victim lies still | Fencing posture in ~⅔; rare concussive convulsions | §3.6 |

---

## 15. Load-bearing numbers to verify first (QA list)

Status after the fact-check pass of 2026-09-26 (§18). No source could be opened, so "≈" means the value matches the fact-checker's independent recall. It still needs a source check before it is hard-coded.

1. Blood volume **70 mL/kg (M) / 65 (F)**. ATLS classes **< 15 / 15–30 / 30–40 / > 40%** with HR **< 100 / 100–120 / 120–140 / > 140** [C1]. **≈ recall-consistent**. ✓ verified (arithmetic) for the mL conversions.
2. Loss of consciousness (supine) at **~40–50%** loss, PEA at **~50–60%**. Upright faint from **20–30%** [C1] [K]. **Uncertain**: ATLS (> 50% → LOC) and Guyton (output → 0 at 40–45%) bracket these values. Rate-dependent PEA recommended (§7.4). The example timelines were **corrected** (§7.5).
3. Paradoxical bradycardia in severe haemorrhage (~⅓ of hypotensive trauma patients) [C4] [C5]. Sudden decompensation at **~1–2 L** equivalent (LBNP) [C6]. **Uncertain**: the prevalence may be ~30–45% depending on the cut-off. The LBNP part is ≈ recall-consistent.
4. **10–15 s** of voluntary action after destruction of the heart [C7] [C8]. **≈ recall-consistent** (the quote exists; it is doctrine, not data).
5. Unconsciousness **5–10 s (mean 6.8 s)** after complete cerebral circulatory arrest [C9]. **≈ recall-consistent**.
6. Syncope: myoclonus ~90%, eyes open, upward deviation common, mean ~12 s [C11]. **≈ recall-consistent**.
7. Agonal gasping in **~30–40%+** of witnessed arrests, declining with time [C12] [C13]. **≈ recall-consistent** for prevalence. The rate and duration remain [K].
8. Brain death: pupils **fixed 4–9 mm**, all brainstem reflexes absent, apnoea [C17] [C18]. **≈ recall-consistent**. The 2023 guideline update was added (§10.1).
9. Autoresuscitation within **~5 min** in a minority (~14%) [C14]. **≈ recall-consistent**.
10. Neurogenic shock incidence **19% cervical / 7% thoracic / 3% lumbar** [C34]. Bradycardia in essentially all severe cervical injuries, arrest ~16% [C35]. **≈ recall-consistent**. The trigger definition was added (§6.5).
11. Spinal shock four phases: **0–24 h** areflexia [C33]. **≈ recall-consistent**.
12. ISNCSCI key muscles and dermatomes [C32]. **≈ recall-consistent** (high-confidence textbook content).
13. Fencing response in **~66%** of knockouts, lasting seconds [C20]. Concussive convulsions **~1/70** [C21]. **≈ recall-consistent**.
14. GTC seizure: tonic 10–20 s, clonic 30–60 s, total ~1 min. Eyes open in ≥ 90% [C22] [C23] [C24]. **Not re-checked** in the fact-check pass (outside its claim list).
15. Lid behaviour at death (open or half-open common; "inability to close eyelids" before death) [C41]. **No prevalence study located. The distribution is [G].** **Citation corrected**: was [C40] [C41] (§11.3).
16. Tache noire **3–6 h**, corneal clouding **hours (open) vs ~24 h (closed)** [K] [C42] [C43]. **≈ recall-consistent**.
17. Vitreous K⁺ **0.19 mmol/L/h**; **PMI = 5.26 × K⁺ − 30.9** [C46]. **≈ recall-consistent**. ✓ verified (arithmetic): internally consistent. The ± 20 h error band was added.
18. Livor (Mallach): onset 0.75 h, confluence 2.5 h, maximum 9.5 h, complete blanching until 5.5 h, complete shift until 3.75 h [C44]. **≈ recall-consistent**.
19. Rigor (Mallach): onset 3 h, full 8 h, re-establishes if broken before 8 h, persists 57 h, resolves 76 h [C44]. **≈ recall-consistent**.
20. Henssge cooling formula and constants (1.25 / 0.25 / 5; 1.11 / 0.11 / 10; B = −1.2815 (cm)^−0.625 + 0.0284) [C45]. Constants **≈ recall-consistent**. Worked values **✓ verified (arithmetic)**. The error limits were added.
21. EDH > 30 mL surgical; PVI ~25 mL; ICP threshold 22 mmHg [C28] [C29] [C30]. **≈ recall-consistent**.
22. Open pneumothorax when the wound is > ⅔ of the tracheal diameter; massive haemothorax ≥ 1,500 mL [C1]. Tension signs: hypotension and tracheal deviation are late [C37]. **≈ recall-consistent**. ✓ verified (arithmetic) for the mm and mL conversions.

---

## 16. Sources

**Status**: none of these were opened in this session (see §0.1). Bibliographic details are given from memory, complete enough to locate each item. The `[D01]`/`[D02]` items were located by web search in the sibling documents' sessions, and their URLs are copied from those documents. URLs marked "from memory" were not opened. Verify all of them.

**Trauma, shock and haemorrhage**
- **[C1]** American College of Surgeons Committee on Trauma. *Advanced Trauma Life Support (ATLS) Student Course Manual*, 9th ed. (2012) and 10th ed. (2018). Chicago: ACS. (Hemorrhage classes, haemothorax, open pneumothorax rule, pulse/BP teaching.)
- **[C2]** Mutschler M, Nienaber U, Brockamp T, et al. A critical reappraisal of the ATLS classification of hypovolaemic shock: does it really reflect clinical reality? *Resuscitation*. 2013;84(3):309–313.
- **[C3]** Guly HR, Bouamra O, Little R, et al. Testing the validity of the ATLS classification of hypovolaemic shock. *Resuscitation*. 2010;81(9):1142–1147.
- **[C4]** Demetriades D, Chan LS, Bhasin P, et al. Relative bradycardia in patients with traumatic hypotension. *J Trauma*. 1998;45(3):534–539.
- **[C5]** Barriot P, Riou B. Hemorrhagic shock with paradoxical bradycardia. *Intensive Care Med*. 1987;13(3):203–207.
- **[C6]** Cooke WH, Ryan KL, Convertino VA. Lower body negative pressure as a model to study progression to acute hemorrhagic shock in humans. *J Appl Physiol*. 2004;96(4):1249–1261.
- **[C37]** Leigh-Smith S, Harris T. Tension pneumothorax — time for a re-think? *Emerg Med J*. 2005;22(1):8–16.
- **[C38]** Asensio JA, Murray J, Demetriades D, et al. Penetrating cardiac injuries: a prospective study of variables predicting outcomes. *J Am Coll Surg*. 1998;186(1):24–34.
- **[C39]** Deakin CD, Low JL. Accuracy of the advanced trauma life support guidelines for predicting systolic blood pressure using carotid, femoral, and radial pulses: observational study. *BMJ*. 2000;321(7262):673–674.

**Incapacitation, cerebral ischaemia, syncope**
- **[C7]** Patrick UW. *Handgun Wounding Factors and Effectiveness*. FBI Academy Firearms Training Unit, Quantico, VA; 1989.
- **[C8]** Newgard K. The physiological effects of handgun bullets: the mechanisms of wounding and incapacitation. *Wound Ballistics Review*. 1992;1(3):12–17.
- **[C9]** Rossen R, Kabat H, Anderson JP. Acute arrest of cerebral circulation in man. *Arch Neurol Psychiatry*. 1943;50(5):510–528.
- **[C10]** Whinnery JE, Whinnery AM. Acceleration-induced loss of consciousness: a review of 500 episodes. *Arch Neurol*. 1990;47(7):764–776.
- **[C11]** Lempert T, Bauer M, Schmidt D. Syncope: a videometric analysis of 56 episodes of transient cerebral hypoxia. *Ann Neurol*. 1994;36(2):233–237.

**Cardiac arrest, dying, death determination**
- **[C12]** Clark JJ, Larsen MP, Culley LL, Graves JR, Eisenberg MS. Incidence of agonal respirations in sudden cardiac arrest. *Ann Emerg Med*. 1992;21(12):1464–1467.
- **[C13]** Bobrow BJ, Zuercher M, Ewy GA, et al. Gasping during cardiac arrest in humans is frequent and associated with improved survival. *Circulation*. 2008;118(24):2550–2554.
- **[C14]** Dhanani S, Hornby L, van Beinum A, et al. Resumption of cardiac activity after withdrawal of life-sustaining measures. *N Engl J Med*. 2021;384(4):345–352.
- **[C15]** Dreier JP, Major S, Foreman B, et al. Terminal spreading depolarization and electrical silence in death of human cerebral cortex. *Ann Neurol*. 2018;83(2):295–310.
- **[C16]** Saposnik G, Bueri JA, Mauriño J, Saizar R, Garretto NS. Spontaneous and reflex movements in brain death. *Neurology*. 2000;54(1):221–223.
- **[C17]** Wijdicks EFM, Varelas PN, Gronseth GS, Greer DM. Evidence-based guideline update: determining brain death in adults. *Neurology*. 2010;74(23):1911–1918.
- **[C18]** Greer DM, Shemie SD, Lewis A, et al. Determination of brain death/death by neurologic criteria: the World Brain Death Project. *JAMA*. 2020;324(11):1078–1097.
- **[C53]** (added by the fact-check, from recall, not opened) Greer DM, Kirschen MP, Lewis A, et al. Pediatric and adult brain death/death by neurologic criteria determination: an update of the 2010 AAN, AAP, CNS and SCCM guidelines (consensus guideline). *Neurology*. 2023;101(24):1112–1132.
- **[C54]** (added by the fact-check, from recall, not opened) Brignole M, Moya A, de Lange FJ, et al. 2018 ESC Guidelines for the diagnosis and management of syncope. *Eur Heart J*. 2018;39(21):1883–1948. (Cerebral flow cessation of 6–10 s and SBP 50–60 mmHg at heart level cause loss of consciousness.)
- **[C36]** Jose AD, Collison D. The normal range and determinants of the intrinsic heart rate in man. *Cardiovasc Res*. 1970;4(2):160–167.
- **[C40]** Hui D, dos Santos R, Chisholm G, et al. Clinical signs of impending death in cancer patients. *Oncologist*. 2014;19(6):681–687. (Fact-check: this paper covers ten other signs. The eyelid sign is in [C41].)
- **[C41]** Hui D, dos Santos R, Chisholm G, et al. Bedside clinical signs associated with impending death in patients with advanced cancer: preliminary findings of a prospective, longitudinal cohort study. *Cancer*. 2015;121(6):960–967.

**Neurology, TBI, ICP, seizures**
- **[C19]** Posner JB, Saper CB, Schiff ND, Claassen J. *Plum and Posner's Diagnosis and Treatment of Stupor and Coma*. 5th ed. Oxford University Press; 2019.
- **[C20]** Hosseini AH, Lifshitz J. Brain injury forces of moderate magnitude elicit the fencing response. *Med Sci Sports Exerc*. 2009;41(9):1687–1697.
- **[C21]** McCrory PR, Bladin PF, Berkovic SF. Retrospective study of concussive convulsions in elite Australian rules and rugby league footballers: phenomenology, aetiology, and outcome. *BMJ*. 1997;314(7075):171–174.
- **[C22]** Theodore WH, Porter RJ, Albert P, et al. The secondarily generalized tonic-clonic seizure: a videotape analysis. *Neurology*. 1994;44(8):1403–1407.
- **[C23]** Jenssen S, Gracely EJ, Sperling MR. How long do most seizures last? A systematic comparison of seizures recorded in the epilepsy monitoring unit. *Epilepsia*. 2006;47(9):1499–1503.
- **[C24]** Chung SS, Gerber P, Kirlin KA. Ictal eye closure is a reliable indicator for psychogenic nonepileptic seizures. *Neurology*. 2006;66(11):1730–1731.
- **[C25]** Temkin NR. Risk factors for posttraumatic seizures in adults. *Epilepsia*. 2003;44(s10):18–20.
- **[C26]** Wilson MH, Hinds J, Grier G, et al. Impact brain apnoea — a forgotten cause of cardiovascular collapse in trauma. *Resuscitation*. 2016;105:52–58.
- **[C27]** Atkinson JLD. The neglected prehospital phase of head injury: apnea and catecholamine surge. *Mayo Clin Proc*. 2000;75(1):37–47.
- **[C28]** Carney N, Totten AM, O'Reilly C, et al. Guidelines for the management of severe traumatic brain injury, fourth edition. *Neurosurgery*. 2017;80(1):6–15.
- **[C29]** Bullock MR, Chesnut R, Ghajar J, et al. Surgical management of acute epidural hematomas. *Neurosurgery*. 2006;58(3 Suppl):S7–S15. (And the companion chapter on acute subdural hematomas, S16–S24.)
- **[C30]** Marmarou A, Shulman K, LaMorgese J. Compartmental analysis of compliance and outflow resistance of the cerebrospinal fluid system. *J Neurosurg*. 1975;43(5):523–534.
- **[C31]** Dinallo S, Waseem M. Cushing reflex. *StatPearls* (NCBI Bookshelf). URL from memory, not opened: https://www.ncbi.nlm.nih.gov/books/NBK549801/

**Spinal cord**
- **[C32]** Kirshblum SC, Burns SP, Biering-Sorensen F, et al. International standards for neurological classification of spinal cord injury (revised 2011). *J Spinal Cord Med*. 2011;34(6):535–546.
- **[C33]** Ditunno JF, Little JW, Tessler A, Burns AS. Spinal shock revisited: a four-phase model. *Spinal Cord*. 2004;42(7):383–395.
- **[C34]** Guly HR, Bouamra O, Lecky FE. The incidence of neurogenic shock in patients with isolated spinal cord injury in the emergency department. *Resuscitation*. 2008;76(1):57–62.
- **[C35]** Lehmann KG, Lane JG, Piepmeier JM, Batsford WP. Cardiovascular abnormalities accompanying acute spinal cord injury in humans: incidence, time course and severity. *J Am Coll Cardiol*. 1987;10(1):46–52.

**Forensic pathology, time since death, eyes**
- **[C42]** Saukko P, Knight B. *Knight's Forensic Pathology*. 4th ed. CRC Press; 2016. (Ch. 2, post-mortem changes; asphyxia and petechiae.)
- **[C43]** Madea B (ed.). *Estimation of the Time Since Death*. 3rd ed. CRC Press; 2016.
- **[C44]** Henssge C, Madea B. Estimation of the time since death in the early post-mortem period. *Forensic Sci Int*. 2004;144(2–3):167–175. (Tabulates Mallach's livor and rigor data.)
- **[C45]** Henssge C. Death time estimation in case work. I. The rectal temperature time of death nomogram. *Forensic Sci Int*. 1988;38(3–4):209–236.
- **[C46]** Madea B, Henssge C, Hönig W, Gerbracht A. References for determining the time of death by potassium in vitreous humor. *Forensic Sci Int*. 1989;40(3):231–243.
- **[C47]** Kevorkian J. The fundus oculi and the determination of death. *Am J Pathol*. 1956;32(6):1253–1269.
- **[C49]** DiMaio VJ, DiMaio D. *Forensic Pathology*. 2nd ed. CRC Press; 2001.

**Anatomy and physiology texts**
- **[C50]** Standring S (ed.). *Gray's Anatomy*. 42nd ed. Elsevier; 2020. (Brainstem, spinal cord, orbit.)
- **[C51]** Hall JE, Hall ME. *Guyton and Hall Textbook of Medical Physiology*. 14th ed. Elsevier; 2020. (Cerebral blood flow, mean systemic filling pressure, O₂ stores.)
- **[C52]** Repessé X, Charron C, Fink J, et al. Value and determinants of the mean systemic filling pressure in critically ill patients. *Am J Physiol Heart Circ Physiol*. 2015;309(5):H1003–H1007. (Low confidence in the exact citation details; the human post-mortem MSFP value ~10–15 mmHg is the point used.)

**Non-clinical**
- **[C48]** Plaster JL. *The Ultimate Sniper: An Advanced Training Manual for Military and Police Snipers*. Paladin Press; 1993. (Used only for the statement of targeting doctrine and slang.)

**Sibling-document sources (located by web search in earlier sessions)**
- **[D01:S24]** WikEM, Basilar skull fracture. https://wikem.org/wiki/Basilar_skull_fracture ; "Blind spots" in forensic autopsy: retrobulbar hemorrhage and orbital lesions by PMCT. https://pubmed.ncbi.nlm.nih.gov/25017308/
- **[D01:S25]** Oehmichen M, Meissner C, König HG. Brain injury after gunshot wounding: morphometric analysis of cell destruction caused by temporary cavitation. *J Neurotrauma*. 2000;17:155. https://journals.sagepub.com/doi/abs/10.1089/neu.2000.17.155 ; review (2004): https://pubmed.ncbi.nlm.nih.gov/15542271/
- **[D01:S26]** Karger B. Penetrating gunshots to the head and lack of immediate incapacitation. I. https://pubmed.ncbi.nlm.nih.gov/8547159/ ; II. https://pubmed.ncbi.nlm.nih.gov/8664147/
- **[D01:S30]** Karger B, et al. On the physics of momentum in ballistics: can the human body be displaced or knocked down by a small arms projectile? https://pubmed.ncbi.nlm.nih.gov/8956990/
- **[D01:S43]** Civilian gunshot wounds to the head: case report, clinical management, literature review. https://pmc.ncbi.nlm.nih.gov/articles/PMC7856761/ ; StatPearls, Penetrating Head Trauma. https://www.ncbi.nlm.nih.gov/books/NBK459254/
- **[D02:R13]** An autopsy study of 74 cases of cut throat injuries. https://www.sciencedirect.com/science/article/pii/S2090536X14000781
- **[D02:R15]** Scalp laceration: an obvious "occult" cause of shock. https://pubmed.ncbi.nlm.nih.gov/10728511/
- **[D02:R21]** Medscape, Bleeding time. https://emedicine.medscape.com/article/2085022-overview
- **[D02:R22]** EBSCO Research Starters, Antemortem injuries. https://www.ebsco.com/research-starters/applied-sciences/antemortem-injuries/
- **[D02:R51]** StatPearls, Basilar skull fractures. https://www.ncbi.nlm.nih.gov/sites/books/NBK470175/
- **[D02:R52]** StatPearls, Raccoon sign. https://www.ncbi.nlm.nih.gov/books/NBK542227/ ; WestJEM, Raccoon eyes. https://pmc.ncbi.nlm.nih.gov/articles/PMC2850869/
- **[D02:R54]** StatPearls, Subconjunctival hemorrhage. https://www.ncbi.nlm.nih.gov/sites/books/NBK551666/

---

## 17. Suspicious content

- **None encountered.** No web page, PDF or search result was retrieved in this session: every `WebSearch` call was refused (budget exhausted) and every `WebFetch` call was refused by the egress policy (`EGRESS_BLOCKED`). There was therefore no untrusted content that could carry instructions.
- The only other material read was the two sibling research documents in this repository (`01_gunshot_wounds.md`, `02_sharp_blunt_burn.md`). They were treated as data. They contained no instructions directed at the reader.
- Nothing was downloaded, installed or executed, and no code was copied from any external source. The formulas in §5.1, §7.5, §12.5 and §13.2 are standard published models (cited) or the author's own simple derivations.
- **Fact-check pass (2026-09-26)**: again **none encountered**.
  - WebSearch refused every query (session budget of 200 already used).
  - WebFetch returned `EGRESS_BLOCKED` for all 14 domains tried: pubmed.ncbi.nlm.nih.gov, www.ncbi.nlm.nih.gov, www.ebi.ac.uk, en.wikipedia.org, litfl.com, wikem.org, api.crossref.org, api.semanticscholar.org, radiopaedia.org, www.sciencedirect.com, www.merckmanuals.com, n.neurology.org, www.librepathology.org and www.bmj.com.
  - No external content was received, so none could carry instructions.
  - The fact-checker did not use Bash and did not try to work around the egress policy.

---

## 18. Fact-check (independent review, 2026-09-26)

### 18.1 What could and could not be done
- **Goal**: check the 22 load-bearing claims (§15), plus any other number that looked wrong, against sources the fact-checker found independently.
- **Blocker**: no source could be opened.
  - WebSearch refused every call (session budget exhausted).
  - WebFetch was `EGRESS_BLOCKED` on 14 domains (§17).
  - Per the security rules, no workaround was attempted.
- **Consequence**: the checks below rely on two methods only:
  - **Recomputing every engineering derivation**, marked ✓ verified (arithmetic).
  - **Comparing each sourced claim with the fact-checker's independent recall** of the same literature, marked ≈ recall-consistent (not web-verified), or corrected where recall contradicts the file.
- **Nothing in this document has been verified against a retrieved source.** The QA requirement in §0.1 still stands.

### 18.2 Changes made

| # | Location | Change | Basis |
|---|---|---|---|
| 1 | §7.5 example-timeline table | **Corrected** every LOC and PEA time, and the game times. The original upper bounds were 1.5–2× longer than the table's own stated method gives (flow ∝ MAP, integrated over the §7.8 `map_by_loss` curve). Example: 1 L/min gives LOC 2.4–2.8 min (was 2.5–4) and PEA 2.9–4.0 min (was 3.5–7) | ✓ arithmetic |
| 2 | §13.4 row F | Corrected to match: LOC 24–28 min (was 25–50), arrest 29–40 min (was 35–80), game ~5–6 min (was 4–8) | ✓ arithmetic |
| 3 | §12.8, 3–6 h row | Rectal temp ~36–34 °C (was ~35–34), from the document's own Henssge model | ✓ arithmetic |
| 4 | §11.3, §15 item 15, §16 | "Inability to close eyelids" is re-attributed to [C41] only (was [C40] [C41]). The eight specific signs from [C41] are listed | Recall (M) |
| 5 | §11.7 Horner row | Pupil 0.5–1 mm smaller (was 1–2 mm) | Recall (M) |
| 6 | §12.7 | Electrical excitability of the eyelid: weak local reactions up to ~13–22 h (was "up to 5–8 h" only) | Recall (L) |
| 7 | §3.6 | Removed "(GCS 9–12 by definition)". LOC > 30 min and GCS 9–12 are parallel criteria | Recall (M) |
| 8 | §7.4, §7.8, §13.3 | Added a note that ATLS (> 50% → LOC) and Guyton (output → 0 at 40–45%) bracket the thresholds. Recommended PEA at 0.45–0.50 for rapid bleeds. Defaults unchanged | Recall (M) |
| 9 | §7.3 | Flagged that relative-bradycardia prevalence may be ~30–45% rather than "a third". Added the LBNP-to-blood-loss mapping | Recall (L–M) |
| 10 | §7.6 | **Gap**: the arterial pressure at the wound must be hydrostatically corrected for wound height (−0.78 mmHg/cm above the heart). This changes jet heights by tens of cm when standing | ✓ arithmetic |
| 11 | §10.1 | **Gap**: the 2023 AAN/AAP/CNS/SCCM brain-death consensus update [C53]; apnoea-test thresholds (PaCO₂ ≥ 60 mmHg and ≥ 20 above baseline) | Recall (M) |
| 12 | §6.5 | **Gap**: the Guly 2008 definition of neurogenic shock (SBP < 100 with HR < 80) as the game trigger | Recall (M) |
| 13 | §11.6, §11.10 | **Gap**: vitreous K⁺ formula 95% limits ≈ ± 20 h; show an error band | Recall (M) |
| 14 | §12.5 | **Gap**: Henssge nomogram 95% limits ≈ ± 2.8 h (wider with corrective factors); make `T_death` a state input | Recall (M) |
| 15 | §1, §7.4, §16 | **Gap**: ESC syncope thresholds [C54] (6–10 s of cerebral flow cessation; SBP 50–60 mmHg at heart level) | Recall (M) |
| 16 | §8.1, §10.1, §10.2, §5.1 | Added context from recall: G-LOC relative incapacitation and myoclonus; autoresuscitation maximum ~4 min 20 s; gasping prevalence split by paper; EDH non-operative criteria | Recall (L–M) |
| 17 | Throughout | Added ✓ verified (arithmetic) or ≈ recall-consistent marks to the claims in §15 and to the rows they come from | — |

### 18.3 Arithmetic re-derived and found correct
- 0.78 mmHg/cm of blood.
- Jet exit speed 5.49 m/s and ideal height 1.54 m at 120 mmHg; 1.03 m at 80 mmHg; 0.77 m at 60 mmHg.
- ATLS mL conversions for 5,250 mL.
- Intrinsic HR 101 bpm at 30 y.
- ICP worked example: 50 and 126 mmHg.
- Every Henssge column in §12.5.
- Vitreous K⁺ slope and intercept consistency.
- Open-pneumothorax threshold of 10–13 mm.
- Hemithorax 40% = 2,100 mL.
- Commotio window of 2–4% of the cycle.
- Fall time 0.42 s.

### 18.4 Still open (for a session with web access)
1. Primary-source check of every "≈ recall-consistent" item, in the §15 order.
2. A real prevalence figure for eyelid position at death (none known).
3. The exact Demetriades 1998 relative-bradycardia percentage and HR cut-off.
4. The time course of pupil dilation after cardiac arrest from a primary measurement series.
5. Bibliographic details of [C52], [C53] and [C54].
