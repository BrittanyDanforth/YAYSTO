# 03 — Bleeding Physiology and the Vascular System (for a vessel-network bleeding simulation)

Project: Gore Head (Godot 4.5, Forward+, Jolt). Audience: physiology-sim, VFX, decal, shader, audio and animation engineers.
Status: research reference v1.1 (v1 plus an independent fact-check; see Section 16). Clinical/forensic tone. The subject is a fictional, procedurally generated adult only.

---

## 0. How to read this document

### 0.1 Evidence tags

| Tag | Meaning |
|---|---|
| **[K-H] / [K-M] / [K-L]** | My own domain knowledge of the standard references: ATLS manual, Guyton & Hall physiology, Gray's/Moore anatomy, and the forensic pathology texts by DiMaio, Saukko & Knight, and Spitz. H means high confidence (textbook-standard, widely repeated). M means medium (right order of magnitude, exact figure may differ). L means low (plausible estimate, weak basis). |
| **[K-x Rn]** | Same as above, plus the reference **Rn** (Section 15) where I believe the value is stated. **I did not open Rn during this session.** |
| **[D]** | Derived by me from other values with physics or arithmetic. The working is shown. |
| **[G]** | Game-design choice: a tuned value inside, or deliberately at the edge of, the real range, with the reason given. |

No **[S#]** ("read in a source this session") tags appear anywhere in this document, for the reason given in 0.2.

### 0.2 Research method and limitations (read this first)

- **WebSearch was unavailable.** The first call returned "this session has used its web search budget (200 of 200 WebSearch calls)". Other research agents in this workflow had used the budget before this one started. This agent made **zero** successful searches.
- **WebFetch was blocked for every domain tried.** The egress proxy returned `EGRESS_BLOCKED` for www.ncbi.nlm.nih.gov (StatPearls/Bookshelf), pmc.ncbi.nlm.nih.gov, en.wikipedia.org, radiopaedia.org, teachmeanatomy.info, www.kenhub.com, emedicine.medscape.com and www.ebi.ac.uk (Europe PMC).
- **As a result, every number here is [K], [D] or [G].** Many are textbook-standard. Examples: ATLS shock classes, blood volume per kg, organ blood flows, vessel diameters, tamponade volumes and bloodstain drop volumes. I tagged those **[K-H]**. Time-to-death and per-vessel bleed-rate figures are much less certain. They come from a mix of forensic teaching, trauma teaching and orifice/Poiseuille physics that I calibrated myself (**[K-M]**/**[K-L]**/**[D]**/**[G]**).
- Before any number appears in a player-visible "forensic readout" (for example a displayed blood-loss figure or a vessel diameter), a human should check the load-bearing numbers in Section 13 against the Section 15 references.
- **Fact-check pass (v1.1):** an independent checker later re-tested the load-bearing claims. Verified values are marked **✓ verified** and changed values carry "corrected: was X". Sources are tagged **[V#]** and listed in Section 15.1. The method, its limits and a per-claim verdict table are in **Section 16**. Anything without a ✓ is still unverified.

### 0.3 Reference victim and conventions

- **Default victim (male):** 178 cm, 75 kg, blood volume **BV0 = 5.0 L**. Nadler gives 5.1 L and the 70 mL/kg rule gives 5.25 L. I picked 5.0 L so that every 10 % of loss is 500 mL. **Female variant:** 165 cm, 60 kg, BV0 = 3.8 L. Express all thresholds as a **fraction of BV0**, not in mL.
- Baseline vitals: HR 70 bpm, BP 120/80 mmHg (MAP 93), RR 14/min, cardiac output (CO) 5.0 L/min, core temperature 37.0 °C.
- Pressure: mmHg. 1 mmHg = 133.3 Pa = **12.8 mm of blood column** (density 1.06 g/mL) [D]. The hydrostatic reference level is the right atrium (4th intercostal space, mid-axillary line).
- Flow: mL/min unless stated. mL/s = mL/min ÷ 60.
- Colours: approximate sRGB hex under neutral daylight (D65). Tune them in-engine under the game's own lighting.

---

## 1. Blood as a material

### 1.1 Total blood volume

| Population | mL/kg | Typical total | Source |
|---|---|---|---|
| Adult male | 70–75 (range ~66–77) | 5.0–5.5 L at 70–75 kg | [K-H R1, R2]. ✓ verified: Marino gives 66 mL/kg (lean body weight) for males [V1]. BioGears uses BV = 65.6·W^1.02 mL (≈ 71 mL/kg at 75 kg) [V9] |
| Adult female | 60–65 | 3.6–4.2 L at 60 kg | [K-H R1, R2]. ✓ verified: Marino gives 60 mL/kg [V1] |
| Obese adult | 50–60 per kg *actual* weight (fat is poorly vascular) | — | [K-M] |
| ATLS teaching figure (adult) | 70 | 4.9 L for 70 kg | [K-H R1] |
| ICRP reference man / woman | — | 5.3 L / 3.9 L | [K-M R3] |

**Nadler formula** (height H in m, weight W in kg, result in L) [K-H R2]. **✓ verified:** the coefficients match several independent implementations, one of which cites "Nadler et al. Surgery 51:224, 1962" [V10]. The worked examples below were recomputed and are correct.
- Men: `BV = 0.3669·H³ + 0.03219·W + 0.6041`
- Women: `BV = 0.3561·H³ + 0.03308·W + 0.1833`
- Worked examples [D]: male 1.78 m, 75 kg gives 2.069 + 2.414 + 0.604 = **5.09 L** (68 mL/kg). Female 1.65 m, 60 kg gives 1.600 + 1.985 + 0.183 = **3.77 L** (63 mL/kg).

### 1.2 Where the blood is (resting, supine)

| Compartment | % of BV | mL (BV 5.0 L) | Notes | Source |
|---|---|---|---|---|
| Systemic veins and venules | ~64 | 3,200 | The main reservoir. Venoconstriction moves blood from here in haemorrhage | [K-H R4] |
| Systemic arteries | ~13 | 650 | High pressure, low volume | [K-H R4] |
| Systemic arterioles and capillaries | ~7 | 350 | | [K-H R4] |
| Pulmonary circulation | ~9 | 450 | | [K-H R4] |
| Heart chambers | ~7 | 350 | | [K-H R4] |
| "Stressed" volume (the part that generates pressure) | ~25–30 | 1,250–1,500 | The rest is "unstressed" volume, which fills vessels without raising pressure | [K-M R5] |
| Liver content | ~10–13 | 450–650 | Part of the splanchnic reservoir | [K-M R4] |

**Mean systemic filling pressure** (the pressure everywhere after the heart stops) is about **7 mmHg** in Guyton's classic measurements, which were made in animals. **Corrected: was "Human estimates run 7–15 mmHg".** Marino reports human values of **14–20 mmHg**, measured mostly in postoperative ICU patients, some on vasopressors [V1b]. The overall human range is therefore ~7–20 mmHg. After exsanguination it is lower, about 0–5 mmHg [D]. Marino also states that the venous system holds **~75 %** of the blood volume [V1b]. That is consistent with the 64 % systemic plus 9 % pulmonary veins in the table above.

### 1.3 Physical properties (for fluid, particle and decal systems)

| Property | Value | Unit | Notes | Source |
|---|---|---|---|---|
| Density, whole blood | 1.050–1.060 | g/mL | Plasma 1.025, red cells ~1.10 | [K-H R4] |
| Haematocrit | 41–50 (M), 36–44 (F) | % | Falls slowly after haemorrhage as tissue fluid moves into the vessels | [K-H] |
| Haemoglobin | 13.5–17.5 (M), 12.0–15.5 (F) | g/dL | | [K-H] |
| Water content | ~80–83 | % by mass | Controls drying time | [K-M] |
| Viscosity at 37 °C, high shear (>100 s⁻¹) | 3–4 | mPa·s | Flow in large vessels and jets | [K-H R6] |
| Viscosity, low shear (~1 s⁻¹) | 10–20+ | mPa·s | Shear-thinning (red cells stack into rouleaux at low shear). Relevant to slow rivulets and pools | [K-M R6] |
| Viscosity at room temperature (~22 °C), high shear | 5–6 | mPa·s | Blood cooling on skin or floor | [K-M] |
| Plasma viscosity | 1.1–1.35 | mPa·s | | [K-H R6] |
| Surface tension, whole blood | 52–61 (use 56) | mN/m | Water is 72 | [K-M R7, R8] |
| Capillary length √(γ/ρg) | 2.3 | mm | [D] from γ = 0.056 N/m and ρ = 1,060 kg/m³ | [D] |
| Arterial O₂ saturation (SaO₂) | 97–99 | % | Bright scarlet | [K-H] |
| Mixed venous O₂ saturation (SvO₂) | 65–80 (typ. 70–75) | % | Darker. Below 50 % in severe shock | [K-H] |
| Temperature | 37 | °C | Visibly steams at ambient temperatures below ~10 °C | [K-M] |

### Simulation parameters (blood material)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `bv_per_kg_male` | 70 (66–77) | mL/kg | Or use Nadler with the procedural height and weight | [K-H R1, R2] |
| `bv_per_kg_female` | 65 (60–70) | mL/kg | | [K-H R1] |
| `bv0_default` | 5,000 | mL | Default male. Every threshold is a fraction of this | [G] |
| `rho_blood` | 1,060 | kg/m³ | | [K-H] |
| `mu_blood_jet` | 3.5 | mPa·s | Jets, vessel flow | [K-H R6] |
| `mu_blood_film` | 6–10 | mPa·s | Rivulets and pools (low shear, cooling) | [K-M R6] |
| `gamma_blood` | 0.056 | N/m | | [K-M R7] |
| `unstressed_fraction` | 0.70–0.75 | — | Can be partly mobilised by venoconstriction | [K-M R5] |
| `msfp` | 10 (7–20) | mmHg | Pressure left after cardiac arrest, before blood loss. Corrected: was 7 (5–15). 7 is Guyton's animal value; human ICU measurements are 14–20 [V1b]. 10 is a compromise for an unstressed, non-ICU victim | [K-M R5], [V1b], [G] |

### Visual/behavioural checklist
- Blood is **not** water. It is about 3–6× more viscous, it is shear-thinning, and its surface tension is ~25 % lower. Rivulets move slower and stay narrower than water. Drops are ~4.5 mm, not raindrop-sized.
- In a cold environment, fresh blood steams faintly for the first few seconds to a minute.

---

## 2. Baseline haemodynamics

### 2.1 Pressures by site (supine, at heart level)

| Site | Systolic / diastolic (mean) | Unit | Notes | Source |
|---|---|---|---|---|
| Left ventricle | 120 / 5–12 | mmHg | | [K-H R4] |
| Aorta, large elastic arteries | 120 / 80 (MAP ~93) | mmHg | | [K-H R4] |
| Radial, dorsalis pedis | 125–140 / 75–80 (MAP 88–92) | mmHg | Systolic *amplification* toward the periphery | [K-M R4] |
| Arterioles (entry → exit) | ~85 → ~35 | mmHg | Most of the pressure drop happens here | [K-H R4] |
| Capillaries | 30–35 arterial end → 10–15 venous end | mmHg | | [K-H R4] |
| Venules, small veins | 10–15 | mmHg | | [K-H R4] |
| Large peripheral veins (arm, leg, supine) | 6–12 | mmHg | | [K-H R4] |
| Central venous / right atrium | 0–8 (typ. 3–5) | mmHg | Falls toward 0 in hypovolaemia | [K-H R4] |
| Right ventricle | 25 / 0–8 | mmHg | | [K-H R4] |
| Pulmonary artery | 25 / 10 (mean ~15) | mmHg | Low pressure. Lung wounds bleed slowly and often stop by themselves | [K-H R4] |
| Left atrium, pulmonary veins | 5–12 (mean ~8) | mmHg | | [K-H R4] |
| Intracranial pressure (ICP) | 5–15 | mmHg | Subtract from MAP to get cerebral perfusion pressure (CPP) | [K-H] |
| Portal vein | 5–10 | mmHg | | [K-H] |

### 2.2 Hydrostatics (posture changes everything for veins and for the brain)

- Every 10 cm of height relative to the right atrium changes local pressure by **7.8 mmHg** [D]. (ρgh = 1,060 × 9.81 × 0.10 = 1,040 Pa.)
- Standing: foot arteries have a MAP of ~170–180 mmHg and foot veins ~80–90 mmHg (motionless). Brain-level MAP is ~70 mmHg because the head is ~30 cm above the heart [D, K-H R4].
- Upright neck veins sit at about 0 mmHg or below and **collapse**. Dural venous sinuses cannot collapse and are *sub-atmospheric* (about −5 to −10 mmHg) when upright [K-M R4]. **Air embolism risk:** a large open vein above heart level (neck, subclavian, an open dural sinus) can suck in air.
- Consequences for the sim:
  - Venous bleeding from a limb increases strongly when the limb hangs down and nearly stops when it is raised above the heart.
  - Neck vein bleeding in an upright victim is weak and may whistle or suck air.
  - A standing victim faints at a smaller blood loss than a supine one, because brain-level pressure is ~23 mmHg lower.

### 2.3 Resting blood flow by organ (CO 5.0 L/min)

| Organ / bed | mL/min | % CO | Source |
|---|---|---|---|
| Brain | 750 | 14–15 | [K-H R4, R9] |
| Heart (coronary) | 225–250 | 4–5 | [K-H R4] |
| Kidneys (both) | 1,100–1,250 | 22–25 | [K-H R4] |
| Liver total: portal vein ~1,050 + hepatic artery ~300 | 1,350 | ~27 | [K-H R4] |
| Skeletal muscle (rest) | 750–1,000 | 15–20 | [K-H R4] |
| Skin (thermoneutral) | 250–450 | 5–9 | Drops by 70–90 % in shock (pallor) [K-M] |
| Bone | 250 | 5 | [K-H R4] |
| Spleen | 150–300 | 3–6 | [K-M R9] |
| Scalp (whole) | ~50–100 (estimate) | 1–2 | [K-L] |

### 2.4 Pulse timing (for syncing spurts to heartbeat audio)

| Event | Delay after the ECG R-wave | Source |
|---|---|---|
| Aortic valve opens (pre-ejection period) | 60–100 ms | [K-M] |
| Pulse arrives at carotid | +20–50 ms after ejection starts (≈ 90–140 ms after R) | [D] from aortic pulse wave velocity (PWV) 5–8 m/s, ~20 cm path |
| Pulse arrives at femoral | ≈ 150–220 ms after R | [D] PWV 6–9 m/s, ~60 cm path |
| Pulse arrives at radial | ≈ 170–250 ms after R | [D] PWV 8–10 m/s, ~75 cm path |
| Pulse arrives at dorsalis pedis | ≈ 220–300 ms after R | [D] |
| First heart sound S1 (audible "lub") | ≈ 20–60 ms after R | [K-M] |

PWV rises with age (roughly 5–6 m/s in the aorta in young adults, over 10 m/s in the elderly) [K-M].

### Simulation parameters (baseline haemodynamics)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hr0` | 70 (60–80) | bpm | | [K-H] |
| `sbp0 / dbp0 / map0` | 120 / 80 / 93 | mmHg | | [K-H] |
| `co0` | 5.0 (4.5–6) | L/min | | [K-H R4] |
| `cvp0` | 4 (2–8) | mmHg | | [K-H R4] |
| `svr0` | ≈ (93 − 4)/5 = 17.8 | mmHg·min/L | [D] | [D] |
| `hydro_mmHg_per_cm` | 0.78 | mmHg/cm | Add to every wound's local pressure: ρ·g·(h_heart − h_wound) | [D] |
| `pwv_aorta / pwv_peripheral` | 6 / 9 | m/s | Delay from heartbeat to spurt = path length / PWV + pre-ejection time | [K-M] |
| `peripheral_vein_p` | 8–12 (supine) | mmHg | Plus hydrostatic term | [K-H R4] |
| `pulm_art_mean` | 15 | mmHg | Lung parenchymal bleeding uses this, not systemic MAP | [K-H R4] |

### Visual/behavioural checklist
- A heartbeat sound and the spurt at the wound are **not simultaneous**. The spurt lags by ~0.1 s (neck) to ~0.25 s (foot). Players will not notice consciously, but it feels right.
- Raising a bleeding leg or arm above heart level visibly slows **venous** bleeding. It barely changes an **arterial** jet (about −8 mmHg per 10 cm).

---

## 3. Haemorrhagic shock physiology

### 3.1 ATLS classes (classic numeric table, 70 kg adult male)

The ATLS 10th edition (2018) replaced the fixed numbers with arrows (↔/↑/↓) and added base deficit. Games and most teaching still use the classic numbers, which I reproduce here [K-H R1, R10].

**✓ verified (secondary sources; the ATLS manual itself could not be reached).** The class boundaries match Marino's ICU Book: I < 15 % (< 10 mL/kg), II 15–30 % (10–20 mL/kg), III **31**–40 % (21–30 mL/kg), IV > 40 % (> 30 mL/kg). Marino describes Class IV as "profound hemorrhagic shock, which may be irreversible" [V1]. The HR, RR, urine-output and mental-status rows match independent teaching tables [V11]. The **mL/kg form is handy for procedural bodies** because it needs no BV estimate. Marino's mL/kg values assume 66 mL/kg.

| | Class I | Class II | Class III | Class IV |
|---|---|---|---|---|
| Blood loss (% BV) | ≤ 15 % | 15–30 % | 30–40 % | > 40 % |
| Blood loss (mL, 70 kg) | ≤ 750 | 750–1,500 | 1,500–2,000 | > 2,000 |
| Heart rate (bpm) | < 100 | 100–120 | 120–140 | > 140 |
| Systolic BP | Normal | Normal | Decreased | Markedly decreased |
| Pulse pressure | Normal or ↑ | ↓ | ↓ | ↓ (narrow) |
| Respiratory rate (/min) | 14–20 | 20–30 | 30–40 | > 35 |
| Urine output (mL/h) | > 30 | 20–30 | 5–15 | Negligible |
| Mental status | Slightly anxious | Mildly anxious | Anxious, confused | Confused, lethargic |
| Capillary refill | Normal (< 2 s) | Delayed | Delayed | Delayed / absent |
| Skin | Normal / pale | Pale, cool | Pale, cold, clammy | Grey/ashen, cold, mottled |
| Base deficit (10th ed.) (mEq/L) | 0 to −2 | −2 to −6 | −6 to −10 | ≤ −10 |

### 3.2 Realism caveats (important for "medically real")

1. **Real patients are less tachycardic than the table predicts.** Registry studies (Mutschler et al. 2013; Guly et al. 2011) found that most trauma patients do not fit the ATLS class rows. Heart rate in particular rose less than predicted [K-M R11, R12]. **Shock index** (SI = HR / SBP) tracks blood loss better. Mutschler's SI classes: < 0.6 no shock; 0.6–1.0 mild; 1.0–1.4 moderate; ≥ 1.4 severe [K-M R13]. (Fact-check: the citations for R11 and R13 were confirmed as *Resuscitation* 2013;84:309–13 and *Crit Care* 2013;17(4):R172 [V12]. The four SI cut-offs could not be read in the paper itself and are unverified. Normal SI is 0.5–0.7 [V12].)
2. **The response is biphasic.** At about 20–35 % acute loss, many people show a sudden *sympatho-inhibitory* phase: heart rate falls (relative bradycardia, sometimes 50–70 bpm), BP drops abruptly and they faint. This was described in posthaemorrhagic fainting experiments (Barcroft et al. 1944) and is seen in a sizeable minority of hypotensive trauma patients [K-M R14]. **✓ verified, with a corrected rate.** A 1990 *Ann Emerg Med* study reviewed 1,194 trauma patients (256 with isolated penetrating abdominal trauma and 938 with severe extremity trauma). **Pulse < 100 bpm was present in 35.2 % of patients with SBP < 100 mmHg and in 45.8 % of those with SBP < 90.** Relative bradycardia did not raise mortality [V2]. **Game:** give each victim a **35–45 %** chance of a "vasovagal collapse" event between 20 % and 35 % loss. Corrected: was 25–35 % [G from V2]. Separately, blood-injury cues alone (the sight of blood or a wound) can cause "an initial rise in heart rate followed by vasovagal bradycardia and, frequently, syncope" [V3]. That supports the faint at 0 % loss in item 4.
3. **Blood pressure holds until late.** Systolic BP usually stays near normal until about 30 % loss. A narrowing pulse pressure and rising heart rate are the early signs [K-H R1].
4. **Standing victims faint early.** An upright victim becomes syncopal at about 20–30 % loss, because brain-level pressure is ~23 mmHg lower [D]. The sight of blood or pain can trigger a vasovagal faint at 0 % loss [K-M].
5. **Slow loss is tolerated better than fast loss.** Loss over hours allows tissue fluid to move into the vessels (transcapillary refill) and allows full compensation. The same percentage lost in minutes is worse. Chronic slow bleeders can survive haemoglobin of 3–5 g/dL [K-M]. *Added in fact-check:* transcapillary refill "can add as much as one liter to the plasma volume". Haemoglobin and haematocrit therefore do **not** fall at once after acute bleeding. Marino says the fall "is not apparent for 8–12 hours" and takes days to become fully established [V1]. **Sim:** keep Hb/Hct at baseline during a game session unless many hours pass. Cap cumulative refill at ~1 L.
6. **Head injury does not cause haemorrhagic shock** in adults, except through scalp bleeding or as a terminal event. A raised ICP instead produces **Cushing's triad**: *hypertension*, *bradycardia*, irregular breathing. That is the opposite pattern to haemorrhage. If the sim combines brain injury and blood loss, the signs mix [K-H R1].

### 3.3 Continuous physiology lookup table (use this in the sim)

Assumptions: supine victim, acute loss over minutes, BV0 = 5.0 L, fully compensated steady state. The sim interpolates linearly between rows. [K-M R1, R4, R13] for the shape; exact values [G], fitted to the ATLS rows and the SI classes.

| Loss % | Loss mL | HR bpm | SBP/DBP | MAP | PP | CO L/min | CVP | RR /min | Cap refill s | SI | Skin perfusion × | Mental state |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0 | 0 | 70 | 120/80 | 93 | 40 | 5.0 | 4 | 14 | 1.5 | 0.58 | 1.00 | Normal |
| 10 | 500 | 80 | 121/82 | 95 | 39 | 4.7 | 4 | 16 | 1.8 | 0.66 | 0.90 | Normal / slightly anxious |
| 15 | 750 | 92 | 119/84 | 96 | 35 | 4.4 | 3 | 18 | 2.0 | 0.77 | 0.80 | Anxious |
| 20 | 1,000 | 104 | 116/85 | 95 | 31 | 4.1 | 3 | 21 | 2.5 | 0.90 | 0.65 | Anxious, restless, thirsty |
| 25 | 1,250 | 114 | 110/83 | 92 | 27 | 3.8 | 2 | 24 | 3.0 | 1.04 | 0.55 | Restless, thirsty, nauseated |
| 30 | 1,500 | 122 | 99/76 | 84 | 23 | 3.4 | 2 | 28 | 3.5 | 1.23 | 0.45 | Anxious → confused |
| 35 | 1,750 | 130 | 88/68 | 75 | 20 | 3.0 | 1 | 32 | 4.0 | 1.48 | 0.35 | Confused, agitated or apathetic |
| 40 | 2,000 | 138 | 75/57 | 63 | 18 | 2.5 | 1 | 36 | 5.0 | 1.84 | 0.25 | Lethargic, slow, slurred |
| 45 | 2,250 | 146 (or 50–60) | 60/45 | 50 | 15 | 1.9 | 0 | 38, irregular | absent | 2.4 | 0.20 | Obtunded. Unconscious if upright |
| 50 | 2,500 | agonal / slowing | 45/32 | 36 | 13 | 1.2 | 0 | gasping 4–10 | absent | — | 0.10 | Unconscious |
| 55 | 2,750 | PEA, slowing | 30/20 | 23 | 10 | 0.6 | 0 | agonal gasps | absent | — | 0.05 | Unconscious, pre-arrest |
| ≥ 60 | ≥ 3,000 | arrest | — | < 15 | — | ~0 | — | apnoea | — | — | 0 | Cardiac arrest |

(PEA: pulseless electrical activity. The heart still produces electrical activity but no palpable pulse.)

Palpable-pulse heuristic (legacy ATLS rule): radial pulse present when SBP ≥ ~80, femoral when ≥ ~70, carotid when ≥ ~60. Deakin & Low (2000) showed this **overestimates** SBP, meaning pulses remain palpable at lower pressures than the rule claims. Use it as a gameplay heuristic, not as a truth [K-M R15].

### 3.4 Compensation and time dynamics

| Mechanism | Onset | Magnitude | Source |
|---|---|---|---|
| Baroreflex (heart rate, contractility) | 1–5 s | HR +30–70 bpm. Gain roughly 1–2 bpm per mmHg fall in MAP | [K-M R4] |
| Arteriolar vasoconstriction (SVR ↑) | 5–30 s | SVR +30–80 % | [K-M R4] |
| Venoconstriction ("autotransfusion" from unstressed volume) | 10–60 s | Mobilises ≈ 10–15 % of BV into the effective circulation | [K-M R4, R5] |
| Adrenaline surge at injury (pain, fear) | 5–30 s | Transient SBP +10–30 mmHg, HR +20–40 bpm for 1–5 min. Spurts are *stronger* at first | [K-M] |
| Transcapillary refill (tissue fluid moving into plasma) | minutes to hours | ~250–500 mL in the first hour, then slower. Plasma volume fully restored in 24–72 h | [K-L R4] |
| Renal fluid retention, thirst | 30 min+ | Irrelevant on game timescales, apart from the *thirst* behaviour | [K-H] |

### 3.5 Thresholds: consciousness, cardiac arrest, brain injury

| Threshold | Value | Source |
|---|---|---|
| Normal cerebral blood flow (CBF) | ~50 mL/100 g/min (brain ~1.4 kg gives ~750 mL/min) | [K-H R4] |
| Lower limit of cerebral autoregulation | CPP ~50–60 mmHg. Below it, CBF falls with pressure | [K-H] |
| EEG slowing, confusion | CBF < ~25–30 mL/100 g/min (~50–60 % of normal) | [K-M R16] |
| Loss of consciousness, EEG failure | CBF < ~15–20 mL/100 g/min (~30–40 %) | [K-M R16] |
| Neuronal membrane failure, infarction risk | CBF < ~10 mL/100 g/min (~20 %) | [K-M R16] |
| Time to LOC after *complete* stop of cerebral flow | **5–10 s** (Rossen et al. 1943, neck-cuff experiments: ~6–7 s) | [K-H R17]. Fact-check: unverified. The paper and abstracts could not be reached; the value is consistent with standard teaching |
| Voluntary activity after the heart is destroyed | **10–15 s** (the brain's oxygen reserve) | [K-H R18]. Fact-check: unverified (DiMaio could not be reached) |
| EEG isoelectric after cardiac arrest | ~10–30 s | [K-M] |
| Pupils fully dilated after cerebral circulatory arrest | ~30–60 s to begin, fixed by ~1–2 min | [K-M] |
| Irreversible brain injury, normothermic no-flow | 4–6 min (longer if cold) | [K-H] |
| Coronary perfusion pressure (DBP − RAP) too low to sustain the heart | < ~15–20 mmHg | [K-M R19] |
| Acute loss usually fatal without treatment | ≥ 40–50 % BV. ✓ verified, with a caveat: Marino says loss "of as little as 30 % of the (limited) blood volume can be fatal", and Class IV (> 40 %) "may be irreversible" [V1]. Keep 40–50 % as the usual lethal range, and let fast or upright losses kill from ~30 % | [K-H R1, R18], [V1] |

### 3.6 Death sequence from exsanguination (what the player should see)

[K-M R18, R20] for the components. The order and timings are my synthesis [G].

1. **Early (Class I–II):** alert, anxious, restless. Breathing faster. Pale lips and face. Sweating (cold, clammy). Thirst. Nausea. Collapsed hand and arm veins (they flatten and disappear under the skin).
2. **Class III:** confusion, agitation *or* apathy. Voice weak (hypophonic). Rapid shallow breathing ("air hunger"). Yawning and sighing (presyncope). Complaints of cold and "going dark". Shivering. Vision greys or tunnels.
3. **Class IV / pre-arrest:** unresponsive to voice. Grey-white waxy skin with mottled knees. Lips blue-grey but *not strongly cyanotic*: visible cyanosis needs ~5 g/dL deoxygenated haemoglobin, which exsanguinated blood lacks [K-M].
4. **LOC:** if the fall in cerebral flow is abrupt, **brief myoclonic jerks** occur in most people (about 90 % in videometric syncope studies). The **eyes usually stay open**, often with upward gaze deviation. Some show head turning and oral automatisms. The jerks last seconds [K-M R21].
5. **Agonal phase:** irregular gasps (every 5–15 s) in about 40–60 % of arrests, lasting 1–5 min. Jaw drops. Sphincters may relax [K-M R20].
6. **Cardiac arrest:** in haemorrhage this is PEA or bradycardic, then asystole over 5–15 min [K-M].
7. **After death:** marked pallor. **Livor mortis faint or absent**, because little blood is left. Mucous membranes and conjunctivae white. Eyes half-open. Corneas lose their shine within minutes to hours as they dry. If the eyelids stay open, a brown-black band of scleral drying (*tache noire*) appears within ~3–4 h [K-M R18].

### 3.7 Definitions of "massive haemorrhage" (useful difficulty tiers)

Any one of the following [K-H R22]:
- ≥ 1 BV lost in 24 h
- ≥ 50 % BV in 3 h
- ≥ 150 mL/min
- ≥ 1.5 mL/kg/min for ≥ 20 min

### Simulation parameters (shock)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `shock_table` | Section 3.3 | — | Interpolate on `loss_frac = 1 − V/BV0` | [G] fitted to [K-H R1] |
| `hr_response_scale` | 0.6–1.0 (default 0.8) | × | Realism: real HR rises less than ATLS | [K-M R11, R12] |
| `vasovagal_chance` | 0.35–0.45 (default 0.4) | probability | Triggered once, between 20–35 % loss. HR → 50–70 and MAP −20–30 for 30–120 s. Corrected: was 0.25–0.35. Pulse < 100 in 35 % of trauma patients with SBP < 100 and in 46 % with SBP < 90 [V2] | [K-M R14], [V2], [G] |
| `refill_cap` | ~1,000 | mL | Added in fact-check. Maximum cumulative transcapillary refill. Hb/Hct do not visibly fall for 8–12 h [V1] | [V1] |
| `upright_brain_offset` | −23 | mmHg | CPP penalty when standing (~30 cm head above heart) | [D] |
| `cbf_fraction` | f = clamp((CPP − 20)/(50 − 20), 0, 1) | — | Autoregulated (f = 1) above CPP 50 | [G] from [K-M R16] |
| `brain_o2_reserve` | 8 (5–10) | s | Drains when f < 0.4 at rate (1 − f/0.4) per s. LOC at 0. Recovers at 1 s/s when f ≥ 0.5 | [G] from [K-H R17] |
| `loc_cpp` | ~30 | mmHg | Supine: reached near 45–50 % loss. Upright: near 35–40 % | [D] |
| `arrest_rule` | loss ≥ 0.60, OR MAP < 20 for > 30 s, OR (DBP − CVP) < 15 for > 60 s | — | Then PEA for 5–15 min, then asystole | [G] from [K-M R19] |
| `brain_death_timer` | f < 0.2 accumulated for 4–6 | min | Normothermic | [K-H] |
| `refill_rate` | 0 at 0 % loss → 5–8 at ≥ 20 % loss, decaying with τ ≈ 60 min | mL/min | Transcapillary refill. Also lowers haematocrit | [K-L R4], [G] |
| `stress_surge` | SBP +20, HR +30, decaying with τ ≈ 120 s | mmHg, bpm | Applied at the moment of injury | [K-M], [G] |
| `tolerance_slow_bleed` | Shift every table row by +5 % loss if the loss took > 60 min | % BV | | [K-M], [G] |

### Visual/behavioural checklist
- Pallor spreads from the lips, nail beds and conjunctivae outward. By Class III the face is grey-white and sweaty. Mottled lace-like patches appear on the knees in Class IV.
- Hand and forearm veins that were visible flatten and vanish as volume falls. Neck veins are **flat**, unless there is tamponade (Section 8).
- Breathing sound tracks RR: 14 → 20s → 30s/min, then shallow panting, then irregular gasps after LOC. Gasps continue for a minute or more after the victim looks dead.
- Voice (if any): anxious and coherent, then repeated questions and complaints of thirst or cold, then weak, slow and slurred, then silent.
- Collapse: a standing victim crumples when LOC comes (loss of tone, *not* thrown). Brief jerks of the arms and face for a few seconds. **Eyes open**, often rolled up, then staring.
- **No instant death from bleeding.** Even total destruction of the heart leaves 10–15 s of possible voluntary movement. Anything faster must come from CNS injury.

---

## 4. Wound flow model (how many mL/s leave a hole)

### 4.1 Principle

A bleeding wound is an **orifice** (the hole in the vessel wall). It is fed by the **vascular network** upstream and discharges into the **tissue path**, which is either open skin or a narrow track through muscle. Three limits apply, and the smallest wins [D]:

1. **Orifice limit:** `Q_orif = Cd · A_hole · √(2·ΔP/ρ)`, where ΔP = local intravascular pressure − external pressure. Use Cd ≈ 0.6 (sharp-edged hole). **✓ verified (arithmetic):** the fact-check recomputed every value in tables 4.2 and 4.3, the radial worked example (P_hole ≈ 40 mmHg, Q ≈ 0.56 L/min) and the parallel-shunt examples (P ≈ 48 mmHg / 2.4 L/min and P ≈ 71 mmHg / 1.2 L/min). All agree within ~1 %. The model is standard hydraulics. It has **not** been validated against measured human wound flows, and no such data could be found.
2. **Supply limit:** flow cannot exceed what the upstream conduits deliver at the pressure drop available. `Q ≤ (P_source − P_hole)/R_upstream`. This matters for small arteries (≤ 3 mm) with long feeding segments.
3. **Cardiac limit:** total flow out of all arterial wounds plus all tissue beds cannot exceed cardiac output. A large arterial wound works as a **low-resistance parallel shunt**: it lowers MAP *immediately*, before much volume has been lost. This one effect produces the near-instant collapse seen in aortic or cardiac wounds, and the rapid collapse in carotid and femoral wounds.

### 4.2 Orifice-limited flow (upper bound; no tissue in the way)

`v = √(2ΔP/ρ)`: 120 mmHg gives 5.49 m/s, 90 gives 4.76, 60 gives 3.88, 30 gives 2.75, 10 gives 1.59 m/s [D].
`Q (mL/s) = 0.6 · A (mm²) · v (m/s)` [D].

| Hole Ø | Area | Q at 120 mmHg | Q at 90 | Q at 60 | Q at 30 | Q at 10 (vein) |
|---|---|---|---|---|---|---|
| 1 mm | 0.79 mm² | 2.6 mL/s (155 mL/min) | 135 | 110 | 78 | 45 |
| 2 mm | 3.1 mm² | 10.3 mL/s (620) | 540 | 440 | 310 | 180 |
| 3 mm | 7.1 mm² | 23 mL/s (1,400) | 1,210 | 990 | 700 | 400 |
| 5 mm | 19.6 mm² | 65 mL/s (3,880) | 3,360 | 2,740 | 1,940 | 1,120 |
| 8 mm | 50.3 mm² | 166 mL/s (9,900) | 8,600 | 7,000 | 5,000 | 2,880 |

All values are mL/min unless marked mL/s. These are *upper bounds*. For any hole above ~3 mm in a major artery, the orifice limit exceeds cardiac output, so the **cardiac limit** (4.1, item 3) governs.

### 4.3 Supply limit: Poiseuille resistance of feeding vessels

`R = 8·μ·L / (π·r⁴)`, with μ = 3.5 mPa·s. To convert Pa·s/m³ to mmHg·min/L, multiply by 1.25 × 10⁻⁷ [D].

| Lumen Ø | R per 10 cm of vessel (mmHg·min/L) | Pressure lost per 10 cm at 500 mL/min | Comment |
|---|---|---|---|
| 25 mm (aorta) | 0.005 | ~0 | Negligible |
| 8 mm (femoral, subclavian) | 0.44 | 0.2 mmHg | Negligible |
| 4 mm (brachial) | 7.0 | 3.5 mmHg | Small |
| 2.5 mm (radial) | 46 | 23 mmHg | **Significant**: limits small-artery bleeding |
| 1 mm (digital, scalp branch) | 1,780 | — (flow cannot reach 500) | Dominant. ~100 mL/min max from a 5 cm branch at 90 mmHg |

Flows above Reynolds number ~2,000 are turbulent. Multiply R by 1.5–3 there [K-M]. Worked example, radial artery 2.5 mm, fully transected, 20 cm feeding length: solving orifice and upstream together gives an orifice pressure of ~40 mmHg and **~550 mL/min theoretical initial flow** [D]. Arterial spasm (radius −30 % gives R ×4) and overlying tissue bring real rates down to 100–300 mL/min in the first minute and 20–60 mL/min after a few minutes (Section 5) [D, K-M].

**Why cut arteries bleed more than their resting flow.** At rest, flow is set by downstream arteriolar resistance. Opening the artery bypasses that resistance, so flow is set only by the low upstream resistance. A brachial artery carrying 70 mL/min at rest can discharge 5–10× that when opened [D].

### 4.4 Partial vs complete transection, retraction and spasm

| Situation | Behaviour | Source |
|---|---|---|
| **Complete transection, muscular artery** (brachial, radial, ulnar, femoral branches, popliteal, tibial, coronary, scalp) | Both ends retract 1–3 cm into the sheath or tissue and go into spasm (lumen −30–60 % within 1–5 min). The intima curls inward and platelets plug it. Vessels ≤ ~3–4 mm can stop by themselves. Traumatic *avulsion* amputations (limb torn off, as in a blast) sometimes bleed surprisingly little at first; clean sharp amputations bleed more | [K-H R1, R18] |
| **Partial (side) laceration** | The wall is held open. Spasm *pulls the hole wider*. It cannot retract. **It keeps bleeding, often more than a complete cut.** | [K-H R1]. Fact-check: unverified (no source reachable). This is standard trauma and forensic teaching and was left unchanged |
| **Elastic arteries** (aorta, brachiocephalic, carotid, subclavian, iliac) | Little spasm. Do not stop by themselves | [K-M]. Fact-check: unverified |
| **Distal stump** | Bleeds backwards via collaterals at 30–80 % of MAP. High for the radial (palmar arch), ulnar and carotid (circle of Willis, external-carotid collaterals). Low for end-arteries | [K-M], [G] |
| **Veins** | Collapse when local pressure ≤ 0. They are held open (air entry risk) where fascia tethers them: subclavian, internal jugular at the root of the neck, dural sinuses | [K-H] |
| **Crushed or torn vessels** (hammer, fist, blast) | Bleed less per mm of opening than clean incised vessels, but cause more tissue haematoma | [K-M R18] |

### 4.5 Tissue path, tamponade, compression

- A deep stab or bullet track through more than ~3 cm of muscle does **not** let an arterial jet reach the skin cleanly. Blood wells out pulsatile, fills the tissue (an **expanding, pulsatile haematoma**, a "hard sign" of vascular injury) or drains into a body cavity [K-H R1].
- An entrance gunshot wound often bleeds little externally. Exits and gaping incised wounds bleed freely. Most gunshot bleeding into the torso is internal [K-M R18].
- A closed fascial compartment or the retroperitoneum fills and pressurises. This **self-tamponade** slows the bleed (the kidney inside Gerota's fascia, retroperitoneal IVC injuries) [K-M].
- Firm direct pressure stops most compressible bleeding. Tourniquets stop limb bleeding. The victim clutching the wound by reflex reduces flow by roughly 30–70 % [G].

### 4.6 Pressure dependence as BP falls

- Large holes (orifice-limited): Q ∝ √ΔP [D].
- Small vessels and capillary ooze (resistance-limited): Q ∝ ΔP [D].
- **Critical closing pressure:** small arteries and arterioles collapse when transmural pressure falls below ~20–40 mmHg, especially when vasoconstricted. Deep shock therefore *stops* small-vessel bleeding, and it restarts ("rebleeds") if pressure is restored [K-M R4]. Animal work suggests rebleeding from a clotted arterial injury at a MAP of about 60–65 mmHg, SBP about 90–95 (Sondeen 2003) [K-M R23].

### 4.7 Posture, breathing and straining
- Hydrostatic term: +0.78 mmHg per cm below the right atrium.
- Neck veins: inspiration lowers intrathoracic pressure. The internal jugular collapses or sucks air. Expiration, coughing, screaming or straining (Valsalva, venous pressure up to 30–40 mmHg or more) produces **surges of dark blood** [K-M].

### 4.8 Recommended per-wound state (design)

Each wound on a vessel segment stores:
`A0` (hole area), `kind` (side | transected), `muscular` (bool), `tissue_factor` ∈ [0,1], `spasm` ∈ [0.3,1.3], `clot` ∈ [0,1] and `compress` ∈ [0,1].

`A_eff = A0 · spasm · (1 − clot) · (1 − compress)`
`Q = min( Cd·A_eff·√(2·max(P_local − P_ext, 0)/ρ) · tissue_factor , supply_limit )`

Tissue factor [G]:
- 1.0: gaping incised wound exposing the vessel
- 0.4–0.6: incised wound under muscle
- 0.15–0.3: narrow stab or bullet track more than 3 cm deep
- 0.05–0.1: victim lying on the wound

Spasm [G]:
- Muscular artery, complete transection: → 0.4–0.6 with τ = 1–3 min
- Side laceration: → 1.1–1.3
- Elastic artery: → 0.9

Clot: see Section 7.

### Simulation parameters (wound flow)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `cd_orifice` | 0.6 (0.5–0.8) | — | Discharge coefficient | [K-H] (fluid mechanics) |
| `turbulence_R_mult` | 1.5–3 when Re > 2,000 | × | | [K-M] |
| `tissue_factor` | 0.05–1.0 | — | See 4.8 | [G] |
| `spasm_target_muscular_transected` | 0.4–0.6, τ 1–3 min | × area | | [K-M], [G] |
| `spasm_target_side_laceration` | 1.1–1.3 | × area | Hole pulled open | [K-H R1], [G] |
| `distal_stump_pressure` | 0.3–0.8 × MAP | — | Radial, ulnar, carotid high; end-arteries low | [K-M], [G] |
| `critical_closing_p` | 20–40 | mmHg | Small-artery bleeding → 0 below this | [K-M R4] |
| `rebleed_map` | 60–65 (SBP ~90–95) | mmHg | A clot formed at low pressure breaks above this | [K-M R23] |
| `valsalva_venous_surge` | +20–40 | mmHg | Screaming, straining, coughing | [K-M] |
| `self_compress_factor` | 0.3–0.7 | × flow | Reflex clutching of the wound | [G] |
| `physics_tick` | 10–20 | Hz | Physiology and flows. VFX interpolate between ticks | [G] |

---

## 5. Injury catalogue: bleed rates and time courses

**How to use:** the "Initial rate" column is what the Section 4 model should produce at normal BP with a typical tissue factor (~0.4–0.6). The time columns are what the full sim should roughly reproduce if the wound is left untreated and the victim is supine. All rows are **[K-M]/[K-L] plus [D]** unless stated. Forensic and trauma texts give time courses only as ranges ("seconds", "minutes", "hours"). The exact ranges here are my synthesis [R1, R18, R20, R24, R25].

"Stops alone?" = can it stop spontaneously. "Compress?" = is it compressible from outside.

**Fact-check status of this table: unverified.** The fact-check found no primary source with per-vessel bleed rates or times to incapacitation. The forensic survival-time literature it could reach (for example a 1988 Dade County series of gunshot and stab victims [V4]) gives no per-vessel numbers in its abstract. The rows *are* internally consistent with the Section 4 model and the Section 3.3 table. For example, femoral 0.8–2 L/min reaches the 40–50 % lethal range (2–2.5 L) in ~1.5–4 min, and flow falls as MAP falls, which matches "death 3–10 min". Treat every time here as a **tuning target, not a measured fact**.

| Injury | Vessel Ø | Initial rate (mL/min) | Blood goes to | LOC (supine) | Death if untreated | Stops alone? | Compress? |
|---|---|---|---|---|---|---|---|
| Ascending aorta or arch, large hole or transection | 25–32 mm | ≈ entire CO: 3,000–6,000 | Mediastinum, pericardium, pleura | **5–15 s** (as in cardiac arrest) | 1–3 min | No | No |
| Descending thoracic aorta (free rupture) | 20–26 | 2,000–5,000 | Pleural cavity (usually left) | 10–30 s | 1–5 min | No. Blunt injuries contained by adventitia: ~15 % reach hospital [K-H R26] | No |
| Abdominal aorta, free intraperitoneal | 15–20 | 1,500–4,000 | Peritoneum | 20–60 s | 2–10 min | No | No |
| Abdominal aorta, contained retroperitoneal | — | 100–500 | Retroperitoneum | 5–30 min | 30 min – hours | Partly (tamponade) | No |
| Heart destroyed (close-range shotgun, large calibre) | — | CO → 0 | Chest | **10–15 s** of possible activity | 1–3 min | No | No |
| LV perforation, pericardium open | wall 9–11 mm | 1,000–4,000 | Pleura | 10–60 s | 1–5 min | Small stab wounds may seal (thick muscle) | No |
| RV or atrium perforation, pericardium open | wall 2–5 mm | 500–2,000 | Pleura | 30 s – 3 min | 2–10 min | Rarely | No |
| Heart stab, pericardium intact | — | 100–200 mL into sac → tamponade | Pericardium | 2–20 min | 5 min – hours | Sometimes temporarily | No |
| Common carotid, unilateral, open neck | 6–8 | 1,000–2,500 (+100–300 distal backflow) | External | 20–90 s | 2–5 min | No | Partly (finger pressure) |
| Throat cut: both carotids + jugulars | — | 2,000–4,000 | External, air aspiration, airway | **5–20 s** | 1–3 min | No | No |
| Internal carotid (cervical) | 4–5.5 (corrected: was 4.5–5.5; see 11.1) | 500–1,000 | External / neck haematoma | 1–3 min | 3–8 min | No | Partly |
| External carotid trunk | 3.5–5 | 200–600 | External | 3–10 min | 5–20 min | Rarely | Yes (neck) |
| Vertebral artery | 3–4 | 100–400 | Deep neck (bony canal) | 5–20 min | 10–40 min | Often contained | No |
| Internal jugular, supine | 10–20 | 200–1,000 | External | 5–20 min | 10–40 min | No | Yes |
| Internal jugular, upright → **air embolism** | — | Air entry **≥ 100 mL/s**. Corrected: was "up to ~100 mL/s through a large opening". Marino: a gradient of only 5 mmHg across a 14 G catheter (1.8 mm ID) entrains ~100 mL/s, so a torn large vein can admit more [V1c] | Right heart | Seconds–1 min. ✓ verified: fatal "when air entry reaches 200–300 mL (3–5 mL/kg) over a few seconds" [V1c]. In dogs, 5 mL/kg over 30 s was the "lethal dose" [V5] | 1–5 min | — | — |
| External jugular | 4–7 | 50–200 | External | 20–60 min | 30 min – hours (air risk) | Sometimes | Yes |
| Subclavian artery | 8–10 | 1,000–2,000 | External or pleura | 1–3 min | 3–10 min | No | Poor (behind clavicle) |
| Subclavian vein | 7–12. Corrected: was 10–13 [V1c] | 200–800 (+ air) | External or pleura. The vein lies "only 5 mm above the apical pleura" at some points [V1c], so pleural involvement is common | 5–20 min | 10–30 min | No | Poor |
| Axillary artery | 6–8 | 600–1,500 | External | 2–5 min | 5–15 min | No | Poor (junctional) |
| Brachial artery | 3.5–5 | 200–600 | External | 5–15 min | 10–30 min | Sometimes (spasm) | Yes |
| Radial or ulnar artery (one) | 2–3 | 100–300 first minute → 20–60 after spasm | External | Rarely | Rare: hours if kept open (warm water, both wrists) | **Usually**, in 5–20 min, after 200–500 mL total | Yes |
| Common femoral artery (± vein) | 7.5–11 (corrected: was 7–10; see 11.2) | 800–2,000 | External | 2–5 min | **3–10 min** | No | Poor–moderate (groin, junctional) |
| Superficial femoral or profunda | 5–7 | 400–1,000 | External / thigh | 4–10 min | 8–20 min | Rarely | Yes (proximal pressure) |
| Common femoral vein alone | 10–14 | 200–600 (more if leg hangs down) | External | 10–30 min | 15–45 min | Sometimes | Yes |
| Popliteal artery | 5–7 | 300–800 | External / knee | 5–12 min | 10–30 min | Rarely | Yes |
| Tibial arteries | 2–3.5 | 50–200 | External | 20–60+ min | 1–3 h | Often | Yes |
| Common or external iliac artery | 7–11 | 1,000–2,500 | Retroperitoneum / pelvis | 2–6 min | 5–15 min | No | No |
| IVC, infrarenal | 13–21 (corrected: was 17–25; see 11.4) | 500–2,000 (50–200 if tamponaded) | Retroperitoneum | 3–15 min | 10–60 min | Partly | No |
| IVC retrohepatic or hepatic veins | 8–25 | 1,000–3,000 | Peritoneum | 1–5 min | 3–15 min | No | No |
| SVC | 18–22 | 500–2,000 | Pericardium (lower half is intrapericardial) → tamponade, or mediastinum | 1–5 min | 3–15 min | No | No |
| Portal vein | 10–13 | 500–1,500 | Peritoneum | 5–15 min | 10–40 min | No | No |
| Renal artery or hilar avulsion | 5–6 | 300–1,000 | Retroperitoneum (Gerota's fascia may contain) | 5–20 min | 15–60 min | Partly | No |
| Kidney parenchyma, minor–moderate | — | 5–50 | Contained perirenal | — | Usually survives | Yes | No |
| Liver laceration, moderate (1–3 cm deep) | — | 20–100 | Peritoneum | 30–120 min | Hours | Often slows | No |
| Liver, severe (deep, lobar disruption) | — | 200–1,000 | Peritoneum | 10–30 min | 20–90 min | No | No |
| Spleen, moderate | — | 20–100 | Peritoneum | 30 min – 3 h | Hours. Delayed rupture possible 2 days to weeks later | Sometimes | No |
| Spleen, shattered or hilar | — | 200–800 | Peritoneum | 10–40 min | 30–120 min | No | No |
| Lung parenchyma (peripheral) | — | 5–50 (low pulmonary pressure) | Pleura, airway | — | Usually survivable | Usually. ✓ Sugarbaker: most traumatic lung injuries are self-limiting and are managed with a chest tube alone [V6] | No |
| Lung hilum (pulmonary artery or vein) | 18–29 | 1,000–4,000 | Pleura | 30 s – 2 min | 2–10 min | No | No |
| Intercostal or internal thoracic artery | 1.5–3 | 50–150 | Pleura | 20–60 min | 1–3 h | **No** (systemic pressure, rigid wall) | No |
| Scalp laceration 5–10 cm | 1–2.5 (branches) | 5–30 (up to 50–100 if the superficial temporal or occipital artery is cut) | External | 30–90+ min | Hours. Can reach Class II–III over 30–90 min | **Poorly**: vessels held open | Yes |
| Face: facial artery, lip, nose | 1–3 | 20–150 | External + mouth/airway (swallowed or aspirated) | 30+ min | Hours. The airway is the bigger risk | Sometimes | Yes |
| Capillary abrasion (10 cm²) | — | 0.1–1 | External (ooze) | — | — | **Yes**, in 3–10 min | Yes |

Context:
- Blunt thoracic aortic injury: ~80–85 % die before reaching hospital (Parmley 1958) [K-H R26]. ✓ consistent: a 10-year community series ("Traumatic rupture of the aorta: still a lethal injury", *Am J Surg* 1986) reported **84 % overall mortality** for blunt aortic trauma [V4b]. (That figure is overall mortality, not prehospital deaths only, so the check is indirect.)
- Combat deaths judged "potentially survivable": ~91 % were haemorrhage. Of these, ~67 % were truncal, ~19 % junctional (groin, axilla, neck) and ~14 % extremity (Eastridge 2012) [K-M R24]. **Non-compressible truncal bleeding is the main killer.**
- In forensic series, victims with fatal stab wounds of the heart or great vessels often carried out purposeful activity (walking, running, fighting) for tens of seconds to minutes (Karger et al.) [K-M R25].

### 5.1 Validation scenarios (the sim should land roughly here)

| Scenario | Expected course | Source |
|---|---|---|
| A. One radial artery cut clean, arm resting | 100–300 mL/min for ~1 min → spasm → 20–60 mL/min → clot by 10–20 min. Total 200–500 mL (Class I). Survives | [D], [K-M] |
| B. Brachial artery side laceration | ~400 mL/min, slowly declining. Class II at ~3 min, Class III at ~5–7 min, LOC at ~10–15 min, arrest at ~15–30 min | [D], [G] |
| C. Common femoral transection (standing, then collapses) | ~1.2 L/min. Class III at ~1.5 min. Collapse at ~2 min (upright). Arrest at ~4–8 min | [D], [G] |
| D. Unilateral carotid, open neck wound | MAP falls to ~50–70 at once (shunt effect). LOC at 20–60 s. Arrest at 2–5 min | [D] (parallel-shunt solve, 4.1) |
| E. Many small wounds totalling 30–50 mL/min ("slow bleed-out") | Class II at 15–30 min, Class III at 35–50 min, LOC at 60–90 min | [D] |
| F. Isolated large scalp laceration, 20 mL/min, untreated | Class II after ~40–60 min. Class III possible after ~1.5 h | [D], [K-M] |
| G. Heart stab with tamponade | Few mL of external blood. Rising HR, distended neck veins, falling BP over 5–30 min. PEA arrest | [K-H R27] |

Parallel-shunt worked example for scenario D [D]:
- Wound constant: k = Q/√P. A 7 mm hole with tissue factor 0.5 gives k ≈ 0.35 L/min per √mmHg.
- Systemic conductance: G = 5.0/93 = 0.054 L/min per mmHg.
- Assume CO stays at 5 L/min. Solve `5 = 0.054·P + 0.35·√P`. This gives **P ≈ 48 mmHg** and wound flow ≈ **2.4 L/min**.
- With tissue factor 0.2 the result is P ≈ 71 mmHg and 1.2 L/min.

### Visual/behavioural checklist
- Carotid, aortic and cardiac wounds: the victim goes down in **seconds to about a minute**, not instantly. Small purposeful movements (hand to neck, a step or two) are realistic in that window.
- Femoral and subclavian wounds: the victim may stay conscious for 1–3 minutes, then collapses. The ground pool grows fast (Section 10).
- Radial cuts: brisk spurts at first that weaken within a minute or two, often stopping. They are rarely lethal alone.
- Torso wounds (liver, spleen, iliac, IVC): **little external blood** but steady deterioration: pale, fast breathing, confused. The abdomen fills slowly (Section 8).
- A deep narrow stab over a big artery: pulsating welling and a swelling haematoma, not a movie jet.

---

## 6. Appearance of external bleeding

### 6.1 Arterial vs venous vs capillary

| Feature | Arterial | Venous | Capillary |
|---|---|---|---|
| Colour (fresh, thin film) | Bright scarlet (≈ `#C0141E`) | Dark red / maroon (≈ `#8E1420`) | Bright red beads (≈ `#B01820`) |
| Flow pattern | **Pulsatile jet synchronised with the heartbeat, continuous between beats** (diastolic pressure ~80 keeps it flowing, only lower) | Steady welling or flowing. No pulsation, except neck veins (breathing and cardiac waves) | Ooze: many pinpoint beads that merge into a sheet within seconds |
| Driving pressure | 60–140 mmHg | 5–15 mmHg (supine limb). Up to ~90 in a hanging foot | 15–35 mmHg, tiny orifices |
| Jet / dome height | Vertical jet 0.4–1.0 m at normal BP (6.2) | Dome of blood a few mm to 2–6 cm above the wound, spilling over the edges | None |
| Stops by itself? | Large: no. Small (≤ 3 mm), transected: often | Small: yes. Large or neck: no | Yes, 3–10 min |
| Source | [K-H R1] | [K-H R1] | [K-H] |

Venous dome height = 12.8 cm per 10 mmHg × Cv² (Cv² ≈ 0.25–0.5), giving 3–6 cm at 10 mmHg [D].

### 6.2 Spurt physics (arterial jets)

- **Ideal jet height** equals the local pressure head: SBP 120 gives 1.54 m of blood, 80 gives 1.03 m, 60 gives 0.77 m, 40 gives 0.51 m, 20 gives 0.26 m [D]. **✓ verified (arithmetic):** 133.32 Pa ÷ (1,060 kg/m³ × 9.81 m/s²) = 12.82 mm per mmHg. Cv² for Cv 0.6–0.8 is 0.36–0.64. The horizontal-throw column (t = 0.534 s from 1.4 m) was also recomputed. No measured human arterial jet heights were found, so Cv remains a tuning value.
- **Real jet speed** `v = Cv·√(2P/ρ)` with velocity coefficient Cv ≈ 0.6–0.8. Losses come from the hole shape, tissue, and the pressure drop at the orifice. Height scales with Cv², so real vertical jets are **~0.35–0.65 × ideal** [D]:

| BP (sys/dia) | Vertical jet at systole | At diastole | Horizontal throw from 1.4 m (standing neck), jet horizontal | Look |
|---|---|---|---|---|
| 140/90 (stress surge) | 0.65–1.15 m | 0.4–0.7 m | 1.9–2.5 m | Strong throbbing jet |
| 120/80 (normal) | 0.55–1.0 m | 0.35–0.65 m | 1.8–2.3 m | Throbbing jet, never fully stops |
| 100/70 | 0.45–0.8 m | 0.3–0.55 m | 1.6–2.1 m | Pulses faster (HR ↑), a little lower |
| 80/55 | 0.35–0.65 m | 0.25–0.45 m | 1.4–1.9 m | Clearly weaker |
| 60/40 | 0.25–0.5 m | 0.15–0.3 m | 1.2–1.7 m | Arcs, dribbling between beats |
| 45/30 | 0.15–0.35 m | 0.1–0.2 m | 1.1–1.4 m | "Pumping" surges, a few cm to 20 cm high |
| MAP < 25–30 | — | — | — | No jet. Welling flow with faint pulsation, then gravity only |
| Cardiac arrest | — | — | — | Passive drainage from dependent wounds only (6.4) |

Horizontal throw = v·√(2h/g) at systolic v (Cv 0.6–0.8), with h = 1.4 m, which gives t = 0.53 s [D]. A jet aimed ~45° upward travels ~10–20 % further.

- **Jet breakup:** the jet column breaks into drops about 1.9× its diameter (Rayleigh–Plateau) within ~5–20 cm. A 2–3 mm jet gives drops of ~4–6 mm (35–110 µL). Pulsing velocity bunches drops into **clusters, one per heartbeat** [D, K-M R28].
- **Impact patterns:** arterial spurts on walls or floors leave large stains with downward flow lines, in a **wave/zig-zag sequence, one peak per beat**. The pattern moves as the victim moves [K-H R29].
- **Hole geometry:** a side hole throws a jet sideways from the vessel axis. Transected ends jet along the axis. A jet exiting through skin in front of the vessel spreads into a fan or a welling pool if tissue is in the way.

### 6.3 After cardiac arrest, and post-mortem wounds

- **Arterial pressure** decays to the mean systemic filling pressure (~7 mmHg; ~0–5 after exsanguination) within about 1 minute. Arteries empty into veins [K-M R5].
- **Post-mortem bleeding is passive.** It drains only from wounds below the level of the blood above them, driven by hydrostatic head (0.78 mmHg per cm). It is slow (a few to tens of mL/min, decaying over 10–60 min). The total is usually tens to a few hundred mL. It is more when a large-vein wound is dependent, for example a neck wound with the head hanging [K-M R18].
- **Blood may stay liquid** after sudden death (post-mortem fibrinolysis). Otherwise it forms soft, glossy, dark-red "currant jelly" clots and yellow "chicken fat" clots inside vessels. These are not attached to the vessel wall [K-H R18].
- **Post-mortem wounds** have little or no bleeding, pale margins that gape less, and **no bruising or tissue haemorrhage**. Antemortem wounds show haemorrhage into the margins and clot in the wound. This "vital reaction" distinction is classic forensic teaching [K-H R18].

### 6.4 Audio

| Event | Sound | Source |
|---|---|---|
| Arterial jet | Rhythmic hiss or spatter at HR. Loud patter when the jet hits a hard surface. Pitch and loudness fall as BP falls | [G] |
| Venous flow | Soft continuous trickle. Gurgle in a gaping neck wound. Gulping or sucking air on inspiration if a neck vein is open | [K-M], [G] |
| Drips | Discrete taps, rate = Q / 50 µL (1 mL/min ≈ 20 drops/min). A continuous thin stream above ~15–30 mL/min | [D] |
| Blood in the airway | Wet gurgling breaths, coughing, spraying of fine pink-red droplets | [K-H] |
| Pooling | Near-silent. A faint splash only when the drop rate is high | [G] |

### Simulation parameters (appearance)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `cv_jet` | 0.7 (0.6–0.8) | — | Jet height factor = Cv² | [D], [G] |
| `jet_v` | cv · √(2·P_local·133.3/1060) | m/s | P_local in mmHg | [D] |
| `jet_pulse_waveform` | Upstroke ~0.1 s, peak at 0.15 s, dicrotic notch at ~0.3–0.35 s, diastolic decay to next beat | — | Modulates jet v per beat | [K-M] |
| `jet_min_map` | 25–30 | mmHg | Below this, no ballistic jet: welling only | [D], [G] |
| `jet_drop_diameter` | ~1.9 × jet Ø (typ. 3–6) | mm | | [D] |
| `venous_dome_height` | 12.8 cm per 10 mmHg × 0.25–0.5 | cm | | [D] |
| `capillary_ooze_rate` | 0.01–0.1 per cm² | mL/min | Resistance-limited | [K-L], [G] |
| `postmortem_drain` | Hydrostatic head only, total ≤ 50–500 | mL | Only dependent wounds | [K-M R18] |
| `postmortem_vital_reaction` | false | bool | No bruising or margin haemorrhage for wounds made after arrest | [K-H R18] |

### Visual/behavioural checklist
- An arterial jet pulses at the **current** HR. As shock progresses the pulses get *faster and weaker* at the same time. This is the single most readable cue of a victim bleeding out.
- Between beats the jet shrinks but does not stop while DBP > ~40.
- Venous blood comes out darker and steadily, dome-shaped. Neck-vein bleeding varies with each breath.
- After arrest the jet stops within a beat or two. Only slow dripping from the lowest wounds remains.
- A wound made after death (for example, the player keeps cutting) shows no gush, no bruising and pale edges.

---

## 7. Haemostasis: vasoconstriction, clotting, special sites

### 7.1 Timeline

| Step | Timing | Value | Source |
|---|---|---|---|
| Vascular spasm | Seconds | Lasts ~20–30 min. Strongest in muscular arteries | [K-H R4] |
| Platelet plug | Seconds to ~1–3 min | Seals capillaries and very small vessels | [K-H R4] |
| Skin bleeding time (standard small incision) | Ivy method **2–7 min** (upper normal ~8–9). Duke (earlobe) 1–3 min | Standard for a **small wound** | [K-H]. Fact-check: unverified. The only abstract found notes that template bleeding time does not differ by sex and shortens with age; it gives no numbers [V4c] |
| Whole-blood clotting time (Lee-White, glass tube) | **5–15 min** | Pools and blood in a container gel in this time | [K-H]. ✓ verified: two independent teaching sources give 5–15 min [V13] (secondary sources only) |
| Plasma tests (for a medical HUD) | Prothrombin time (PT) 11–13.5 s. Activated partial thromboplastin time (aPTT) 25–35 s | Not visual | [K-H] |
| Clot retraction, serum expressed | Starts at ~30–60 min, largely complete at 12–24 h | Clear yellow serum rim appears | [K-M] |
| Crust or scab on skin | Surface dries in 10–30 min. Firm scab in hours | | [K-M] |

### 7.2 Which wounds stop on their own

| Wound | Spontaneous stop | Typical time | Source |
|---|---|---|---|
| Capillary abrasion, small cut < 1 cm | Yes | 2–10 min | [K-H] |
| Small artery ≤ 1 mm, transected | Yes | 3–10 min | [K-M] |
| Artery 2–3 mm (radial, ulnar), transected | Usually | 5–20 min | [K-M] |
| Artery 2–3 mm, side laceration | Less often. Rebleeds | 20+ min / never | [K-M R1] |
| Artery ≥ 4 mm | Rarely, only at MAP < ~50 in deep shock | — | [K-M] |
| Veins ≤ 3 mm | Yes | 5–15 min | [K-M] |
| Large veins (jugular, femoral, cava) | No | — | [K-M] |
| Scalp and face | **Poorly**: see 7.3 | 30 min to hours | [K-H R1] |
| Lung parenchyma | Usually (low pressure) | Minutes | [K-M] |

### 7.3 Scalp and face: why they keep bleeding

- The scalp layers are, from outside in: **S**kin, dense **C**onnective tissue, **A**poneurosis (galea), **L**oose areolar tissue, **P**ericranium. The arteries and veins run in the dense connective-tissue layer, where **fibrous septa hold them open**. They cannot retract or constrict effectively, so small arteries keep spurting and oozing [K-H R30]. (Fact-check: unverified; no anatomy text was reachable. This is standard anatomy teaching and was left unchanged.)
- The scalp is richly supplied, with extensive anastomoses from both sides (internal and external carotid systems). Both ends of a cut vessel bleed [K-H R30].
- A laceration through the galea **gapes** because the frontalis and occipitalis muscles pull on it, which increases bleeding [K-H R30].
- A neglected scalp laceration can cause hypovolaemic shock over an hour or more [K-M R1].
- The face is similar: rich collaterals from the facial, labial, angular and nasal vessels. Blood also runs into the mouth and nose, where it is swallowed and later vomited as dark "coffee grounds", or aspirated [K-M].

### 7.4 Coagulopathy ("lethal triad")

- About a quarter of severely injured trauma patients arrive already coagulopathic (Brohi 2003: 24 %) [K-M R31].
- Clotting worsens with **hypothermia** (< 35 °C, roughly 10 % slower enzyme activity per °C), **acidosis** (pH < 7.2) and dilution/consumption after large losses [K-H R1].

### 7.5 Thermal haemostasis (the torch)

| Temperature / process | Effect | Source |
|---|---|---|
| ~60–70 °C | Collagen and proteins denature. Blood coagulates and turns grey-brown and opaque | [K-M] |
| 100 °C | Water boils. Blood **sizzles and spits** on hot surfaces | [K-H] |
| > ~200–300 °C | Carbonisation. Blood and tissue char black. Burnt-protein smell | [K-M] |
| Vessel sealing | Surface heat seals capillaries and small vessels up to ~1–2 mm (monopolar electrocautery ~1–2 mm, bipolar ~3 mm, clinical vessel-sealing devices ≤ 7 mm). An open flame chars the surface but **larger vessels under the eschar bleed again if the eschar cracks** | [K-M R32] |
| Full-thickness burn | Dry, leathery, white/brown/black. **Bloodless when cut** (vessels thrombosed). No capillary refill | [K-H] |
| Partial-thickness burn | Red, blistering, moist. Blanches and refills | [K-H] |
| Hot steel above ~200 °C | Blood drops may skitter (Leidenfrost-like), then burn to a black crust | [K-L] |

### 7.6 Clot appearance

- **Fresh clot** (minutes): glossy dark-red jelly (`#4A060C`) with a wet specular highlight. It wobbles when touched and holds the shape of the wound or pool.
- **30–60 min:** darker. Straw-yellow translucent serum (`#E6D08A`) seeps out at the edges as the clot retracts.
- **Antemortem vs post-mortem clots** inside vessels: see 6.3.

### Simulation parameters (haemostasis)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `tau_clot_capillary` | 2–5 | min | Clot progress `clot += dt/τ_eff` | [K-H] (bleeding time) |
| `tau_clot_small_vessel` (< 1 mm) | 3–10 | min | | [K-M] |
| `tau_clot_2_3mm_artery` | 10–20 | min | Only after spasm lowers flow | [K-M], [G] |
| `tau_eff` | τ · (1 + (P_local / 30 mmHg)²) | min | High pressure and flow hinder clotting | [G] |
| `clot_max_vessel_d` | ~3–4 (arteries) | mm | Above this, clot never exceeds 0.5 unless MAP < 50 | [K-M], [G] |
| `scalp_tau_mult` | ×3–5, spasm fixed at 1.0 | — | Vessels held open | [K-H R30], [G] |
| `coagulopathy_mult` | ×1.5–3 on τ if T < 35 °C, pH < 7.2 or loss > 30 % | — | | [K-M R1, R31] |
| `rebleed_trigger` | MAP rises > 20–30 above the value at clot formation, or MAP > 60–65, or the wound is manipulated | — | clot ×0–0.5 | [K-M R23], [G] |
| `pool_gel_time` | 5–15 | min | Lee-White | [K-H] |
| `serum_separation_start` | 30–60 | min | Yellow rim | [K-M] |
| `thermal_seal_max_d` | 1–2 | mm | Torch contact seals vessels up to this size | [K-M R32] |

### Visual/behavioural checklist
- Small cuts, knuckle wounds and abrasions: oozing that visibly slows and glazes over with a glossy clot in a few minutes.
- **Scalp wounds keep running** long after other small wounds have stopped. Hair is soaked and matted and drips from the tips.
- The torch on a bleeding surface: sizzling, spitting, brown then black crust. Bleeding from small vessels stops. A charred full-thickness area, when cut, does not bleed.
- A stopped wound can restart if the body is moved, the wound is probed, or (in a medical mode) BP is raised.

---

## 8. Internal bleeding

### 8.1 Compartment capacities

| Compartment | Normal content | Critical / typical volumes | Capacity | Source |
|---|---|---|---|---|
| Pericardial sac | 15–50 mL fluid | **Acute tamponade at 100–200 mL** (sometimes 50–100 mL). Chronic effusions can reach 1–2 L without tamponade. **✓ verified:** "rapid accumulation of as little as 100 mL … (eg, after a penetrating cardiac wound) may … produce critical tamponade", while chronic effusions can exceed 1 L [V7]. The Oxford Handbook gives "rapid accumulations of < 150 mL" [V8] | ~200–250 mL acute before arrest (unverified) | [K-H R27, R33], [V7, V8] |
| Each pleural cavity (haemothorax) | ~10–20 mL fluid | Blunts the costophrenic angle on an upright chest X-ray at 200–300 mL. "Massive" > 1,500 mL on chest drain insertion or > 200 mL/h for 2–4 h. **✓ verified:** Sugarbaker gives "> 1500 mL upon initial chest tube insertion or more than one-third the patient's calculated blood volume" and "output greater than 250 mL an hour for a few hours" [V6]. A surgical residency handbook gives > 1,500 mL or > 200 mL/h × 4 h [V14]. Use 200–250 mL/h | **2.5–3 L per side** (~40 % of BV). Capacity unverified | [K-H R1, R34], [V6, V14] |
| Peritoneal cavity | < 50 mL | Ultrasound (FAST) detects from ~200–250 mL (mean ~600 mL in one study). Visible distension usually needs > 1.5–2 L | Several litres (more than the whole BV) | [K-M R1, R35] |
| Retroperitoneum / pelvis | — | Pelvic fracture bleeding 1.5–4 L | Several litres | [K-H R1]. Fact-check: unverified |
| Thigh (closed femur fracture) | — | 1,000–1,500 mL | ~1.5–2 L | [K-H R1]. Fact-check: unverified |
| Tibia or humerus fracture | — | ~500–750 mL | — | [K-H R1]. Fact-check: unverified (classic teaching values; no source reachable) |
| Each rib fracture | — | ~100–125 mL | — | [K-M] |
| Cranial vault | Brain ~1,200–1,400 mL, CSF ~150 mL, blood ~100–150 mL | Compensation limit ~100–150 mL. Beyond it ICP rises steeply (Monro–Kellie). An epidural haematoma > ~30 mL is surgical. In the posterior fossa much less is lethal | Small: see the head/brain docs | [K-H] |
| Subgaleal space (scalp) | — | Hammer blows give a boggy swelling. Subgaleal bleeding can spread across the whole scalp | Hundreds of mL | [K-M] |

Rule of thumb for external loss: **a clot the size of a clenched adult fist is ≈ 400–500 mL** [K-M R1].

### 8.2 Cardiac tamponade

- The pericardium's pressure–volume curve is J-shaped: flat for the first ~50–100 mL beyond normal, then steep. At ~100–200 mL of acute blood, pericardial pressure reaches right-atrial pressure (~5–15 mmHg). The heart cannot fill and cardiac output falls [K-H R33].
- **Signs:**
  - **Beck's triad:** hypotension, **distended neck veins** (unless also hypovolaemic), muffled heart sounds.
  - **Pulsus paradoxus:** systolic drop > 10 mmHg on inspiration.
  - Tachycardia.
  - **Electrical alternans** on ECG (beat-to-beat QRS amplitude alternation).
  - Face and upper body congested or dusky.

  [K-H R27, R33]
- **Course:** minutes to hours, ending in PEA. Removing 20–50 mL of blood from the sac can transiently restore pressure dramatically [K-H R27].
- **Low-pressure tamponade (added in fact-check):** in a **hypovolaemic** victim, a pericardial collection may cause no haemodynamic effect until volume is lost, and "venous filling pressures may be normal or mildly elevated" [V7]. **Sim:** when tamponade and haemorrhage coexist, scale neck-vein distension by the remaining volume, so a bled-out victim with tamponade can have flat neck veins. Pericardial pressure then equals the (low) right-atrial pressure at a smaller pericardial volume, so lower `pericardium_tamponade_v` by ~30–50 % when loss is > 20 % [G from V7].
- Stab wounds of the heart (the right ventricle is most often hit because it lies most anteriorly) commonly produce tamponade. Large or gunshot wounds more often tear the pericardium open and bleed into the pleura [K-M R18].

### 8.3 Haemothorax

- Signs: reduced chest movement and breath sounds on the affected side, dullness to percussion, rising RR, hypoxia. With > 1.5–2 L, mediastinal shift and tracheal deviation away from the side [K-H R1, R34].
- Blood in the pleural cavity is partly **defibrinated** by heart and lung motion, so much of it stays liquid [K-M].
- Chest wall systemic arteries (intercostal, internal thoracic) keep bleeding. Lung parenchyma usually stops (low pressure) [K-M].
- **Frothy, bright-red blood from the mouth** (air mixed in) means lung or airway injury [K-H].

### 8.4 Haemoperitoneum and solid organs

- Liver injury is the most common solid-organ bleed in penetrating trauma. Spleen injury is the most common in blunt trauma [K-M].
- **Kehr's sign:** left shoulder-tip pain from blood irritating the diaphragm (spleen) [K-H].
- Bruising around the umbilicus (**Cullen's sign**) or in the flanks (**Grey Turner's sign**) appears **24–72 h** after retroperitoneal or intraperitoneal bleeding. It is too slow for a game session, but correct for a "found days later" scene [K-H].
- Abdominal distension is a late and unreliable sign. The abdomen can hold litres before obvious swelling [K-H R1].
- A clot forms next to the bleeding organ (the radiological "sentinel clot"). Free blood away from it stays more liquid [K-M].

### 8.5 Bruises and haematomas (fist, hammer)

- Venule and capillary rupture bleeds into the subcutis. Swelling appears within minutes. Discolouration may be delayed by hours, especially in deep bruises [K-H R18].
- Colours over time are **unreliable for ageing**. Yellow is not seen before ~18 h (Langlois & Gresham 1991) [K-M R36]. Sequence: red-purple (`#6A2A55`) → blue-purple (`#4A3A6A`) over hours to days → green (`#6A7A40`) at ~4–7 days → yellow (`#C8B060`) → brown, then fading.
- Scalp haematoma ("goose egg") after a hammer blow: a firm lump 1–3 cm high within minutes (above the galea). Or a boggy spreading swelling if subgaleal.
- A black eye (periorbital haematoma) develops over hours. **"Raccoon eyes"** (bilateral periorbital bruising) and **Battle's sign** (bruising behind the ear) indicate a basal skull fracture. They take hours (periorbital) to 1–3 days (Battle's sign) to appear [K-H].

### Simulation parameters (internal bleeding)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `pericardium_tamponade_v` | 100–200 (default 150). ✓ verified | mL | Above this, CO multiplier falls linearly to 0 by ~250 mL. Reduce by 30–50 % in hypovolaemia (low-pressure tamponade) | [K-H R27, R33], [V7, V8], [G] |
| `pericardium_pv_curve` | P ≈ 0 up to 50 mL, ~15 mmHg at 150 mL, ≥ 25 mmHg at 200+ mL | mmHg | J-shaped | [K-M R33] |
| `pleura_capacity` | 2,500–3,000 per side | mL | Mediastinal shift > 1,500 | [K-H R1, R34] |
| `haemothorax_massive` | > 1,500 (or > ⅓ BV), or > 200–250 mL/h × 2–4 h. ✓ verified | mL | Difficulty and diagnosis tier | [K-H R1], [V6, V14] |
| `peritoneum_capacity` | > 5,000 (never the limiting factor) | mL | | [K-M] |
| `abdomen_visible_distension` | > 1,500–2,000 | mL | Belly swelling blend shape starts here | [K-M], [G] |
| `femur_fracture_loss` | 1,000–1,500 | mL | Into the thigh (swelling) | [K-H R1] |
| `pelvic_fracture_loss` | 1,500–4,000 | mL | Retroperitoneum | [K-H R1] |
| `cranial_reserve` | 100–150 | mL | Beyond this ICP ↑ → Cushing's triad | [K-H] |
| `neck_veins_state` | Flat in hypovolaemia. **Distended** in tamponade, tension pneumothorax, heart failure | enum | Neck blend shape | [K-H R27] |

### Visual/behavioural checklist
- Torso wounds: small external bleeding, big deterioration. The victim becomes pale and tachypnoeic, then confused, while the wound itself barely drips.
- Tamponade: distended neck veins **with** falling BP and a dusky face. This is the only shock state with full neck veins.
- Lung injury: coughing bright frothy blood. Wet gurgling breathing.
- Hammer to the scalp: the lump rises within a minute. Bruise colour stays red-purple for the whole session.

---

## 9. Blood colour and optics

### 9.1 Why arterial and venous blood look different

Oxy- and deoxyhaemoglobin absorb almost the same amount in blue and green. They differ strongly in **red (600–700 nm)**, where deoxyhaemoglobin absorbs ~5–10× more. Venous blood therefore returns less red light and looks darker and more maroon or purple. The difference is obvious in thin films and subtle in thick pools, where both look very dark [K-H R37].

### 9.2 Absorption coefficients (whole blood, Hb 150 g/L)

The conversion uses Prahl's molar extinction table: μa = 2.303 · ε · 150 / 64,500 [K-H R37, D].

**✓ verified:** the table was checked against a copy of Prahl's 1999 compilation (Gratzer/Kollias data) [V15]. The ε values (HbO₂ / Hb) are: 450 nm 62,816 / 103,292; 540 nm 53,236 / 46,592; 600 nm 3,200 / 14,677; 620 nm 942 / 6,510; 650 nm 368 / 3,750. The conversion formula is also correct. All μa values below were recomputed and agree. The deoxy/oxy ratio is 4.6× at 600 nm, 6.9× at 620, 10.2× at 650 and 6.2× at 700, which confirms "~5–10× more red absorption". Note that the blue band is not a single number: near the 415–430 nm Soret peaks μa exceeds 250 per mm. Any blood film thicker than ~0.05 mm is effectively opaque to blue, so the exact blue μa does not matter for rendering.

| Band | ε HbO₂ (cm⁻¹/M) | ε Hb | μa oxy (per mm) | μa deoxy (per mm) |
|---|---|---|---|---|
| Blue ~450 nm | ~62,800 | ~103,300 | ~34 | ~55 |
| Green ~540 nm | ~53,200 | ~46,600 | ~29 | ~25 |
| Orange ~600 nm | ~3,200 | ~14,700 | ~1.7 | ~7.9 |
| Red ~620 nm | ~940 | ~6,500 | ~0.5 | ~3.5 |
| Red ~650 nm | ~370 | ~3,750 | ~0.2 | ~2.0 |

For shaders:
- Use μa per mm roughly (R, G, B) = **(0.4, 28, 34) for arterial** and **(3.0, 26, 50) for deeply deoxygenated** blood. Lerp between them by O₂ saturation [D].
- A 0.5 mm film of arterial blood transmits ~80 % of red and ~0 % of green or blue: saturated scarlet. The same film of venous blood (SvO₂ ~70 %, μa red ≈ 1.4 per mm) transmits ~50 % of red, and fully deoxygenated blood ~17 %: dark maroon to purple-black [D].
- Reduced scattering μs′ ≈ 1–3 per mm (low confidence) [K-L].

### 9.3 Colour reference (sRGB, D65, approximate — tune under game lighting)

| Material / state | Hex | Notes | Source |
|---|---|---|---|
| Arterial, thin film (≤ 0.2 mm) on skin | `#C0141E` | Scarlet | [K-M], [G] |
| Arterial, 1 mm layer | `#8C0A12` | | [K-M], [G] |
| Arterial pool (≥ 2 mm) | `#5E070C` + strong wet specular | Looks near-black-red at grazing angles | [K-M], [G] |
| Venous, thin film | `#8E1420` | Maroon | [K-M], [G] |
| Venous pool | `#3E0509` | | [K-M], [G] |
| Deeply deoxygenated (shock, post-mortem) | film `#6A1026`, pool `#2C040A` | Purple cast | [K-M], [G] |
| Capillary ooze beads | `#B01820` | | [G] |
| Fresh clot | `#4A060C`, glossy | | [G] |
| Serum rim | `#E6D08A`, translucent | | [K-M], [G] |
| Frothy lung blood | `#D8404C` with white foam | | [K-M], [G] |
| Diluted 1:10 (water, sweat, rain) | `#D04858` | Pink-red | [G] |
| Diluted 1:100 | `#F0B0B4` | Pale pink | [G] |
| Surface re-oxygenation | The top surface of a dark venous pool brightens slightly within seconds to minutes in air | Subtle | [K-L] |

### Simulation parameters (optics)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `sat_arterial` | 0.97–0.99 | — | | [K-H] |
| `sat_venous` | 0.70–0.75 → 0.40–0.50 in Class IV | — | Lerp by `loss_frac` | [K-H], [G] |
| `mu_a_oxy_rgb` | (0.4, 28, 34) | 1/mm | | [D] from [R37] |
| `mu_a_deoxy_rgb` | (3.0, 26, 50) | 1/mm | | [D] from [R37] |
| `skin_blood_fraction_mult` | Section 3.3 "skin perfusion ×" | × | Drives pallor in the skin shader | [G] |
| `skin_blood_sat` | 0.8 normal → 0.5 in Class IV | — | Grey-blue lips. Weak cyanosis, because little haemoglobin is left | [K-M], [G] |

### Visual/behavioural checklist
- Fresh arterial jets and splashes are clearly **scarlet** in thin layers. Venous flow is visibly darker.
- Late in shock, blood from every wound becomes darker and more purple as extraction rises.
- Pools read as dark red-black with a strong wet highlight. Colour is seen mainly at the thin edges and in splashes.

---

## 10. Blood on surfaces: drops, rivulets, pools, drying

### 10.1 Drops

| Quantity | Value | Source |
|---|---|---|
| Typical free-falling drip volume | **~50 µL** (range ~13–160 depending on the source edge) | [K-H R29, R38] |
| Diameter of a 50 µL drop | **4.6 mm** (d = (6V/π)^⅓) | [D] |
| Drop from hair tips or a sharp edge | 10–20 µL (Tate's law with contact radius 0.5–1 mm) | [D] |
| Tate's law | `V ≈ 2π·r·γ·f / (ρ·g)`, f ≈ 0.6. Contact radius r = 3 mm gives ~60 µL | [D] |
| Terminal velocity (50 µL) | **~7.6 m/s**, reached after ~6–8 m of fall. At 1 m the drop moves at ~4.3 m/s | [K-H R29]. **Fact-check: uncertain.** 7.6 m/s (25.1 ft/s) is the classic bloodstain-textbook figure; its origin could not be checked. Scaled water-drop data give ~9 m/s for a 4.6 mm drop (a 4.6 mm water drop falls at ~9.0 m/s; blood is 6 % denser but deforms more because of its lower surface tension). Real blood drops probably fall at **~7.5–9 m/s**. Use 8 m/s in game. With a quadratic-drag model, the drop reaches ~4.1–4.3 m/s after 1 m and 95 % of terminal velocity after ~7–10 m [D] |
| Stain diameter on a smooth surface | Maximum spread ≈ 3–5.5 × drop Ø. Corrected: was 3–5 ×. A 4.6 mm drop from 1 m gives a ~15–22 mm stain. Grows with height, levelling off around ~2 m | [D] via Laan et al. [K-M R39]. The fact-check recomputed with the Laan correlation (A = 1.24, μ = 4 mPa·s, γ = 56 mN/m): spread factor ≈ 4.7 at 4.3 m/s (1 m fall), 5.2 at 6 m/s and ~5.6 at terminal velocity |
| Impact angle | sin α = width / length (elliptical stain; the tail points in the travel direction) | [K-H R29]. ✓ verified: "the width-length ratio of the ellipse is the sine of the impact angle" [V16] |
| Classic size classes (legacy BPA terms) | Drip/"low velocity" > 4 mm stains. Blunt blow/cast-off/"medium" 1–4 mm. Gunshot/"high velocity" < 1 mm mist | [K-H R29] |
| Expired/coughed blood | Small stains with **bubble rings**, often pinker (diluted by saliva/mucus) | [K-H R29] |
| Drip-into-blood | Satellite spatter around the drip pool, 1–4 mm drops, up to ~0.5–1 m away | [K-H R29] |

### 10.2 Drips and rivulets on skin

- **Film flow speed** (thin film on an incline): `u = ρ·g·sinθ·h² / (3μ)` [D].
  - h = 0.2 mm, μ = 6 mPa·s, vertical: **~2 cm/s**
  - h = 0.4 mm: ~9 cm/s
  - h = 0.1 mm: ~0.6 cm/s
- The contact line on skin *pins and slips*. Fronts advance in stop–go jerks along creases and hair lines [K-M].
- **Rivulet geometry:** 2–5 mm wide, 0.1–0.4 mm thick. It leaves a residual film of **~5–15 µL per cm of path**, so a single 50 µL drop runs ~3–10 cm and stops [D]. A steady trickle of 1–10 mL/min keeps a rivulet alive indefinitely. (Fact-check: ✓ arithmetic verified. The film formula is the standard Nusselt mean velocity ρgh²/3μ, and 2.3 / 9.2 / 0.58 cm/s were recomputed. The rivulet widths and residue values are unvalidated estimates. Contact-line pinning on real skin can make real speeds several times lower.)
- **Routing:** rivulets follow gravity in the body's *current* orientation, travelling along skin folds and down to local low points:
  - Standing: chin, nose tip, earlobe, elbow, fingertips
  - Supine: occiput, ears, sides of the neck

  Pendant drops form there and release at 30–60 µL [D].
- **Drip rate** = Q / V_drop. 1 mL/min ≈ 20 drops/min. 10 mL/min ≈ 3.3 drops/s. Above ~15–30 mL/min the drops merge into a thin continuous stream [D].
- **Dried trails keep their old direction.** If the body is moved, old rivulets point the "wrong" way and new ones start at an angle. This is a classic forensic clue that the body was moved [K-H R29].
- **Hair:** soaks, clumps and drips from the ends. Hair wicks blood away from the scalp (larger visible wet area).
- **Contact angle** of blood on skin and on steel is roughly 60–90°, with high hysteresis (low confidence) [K-L].

### 10.3 Pooling on flat surfaces

- On a non-absorbent horizontal floor, a puddle's thickness is set by surface tension and gravity: `h ≈ 2·l_c·sin(θ/2)`. With l_c = 2.3 mm and θ = 40–90°, **h ≈ 1.6–3.3 mm; use 2.5 mm** [D]. (Fact-check: ✓ arithmetic verified. l_c = √(0.056 / (1,060 × 9.81)) = 2.32 mm, and every area and diameter in the table below was recomputed. No measured blood-pool thicknesses were found. Blood's high contact-angle hysteresis means a spreading pool pins at its edge, so real pools on slightly rough floors may be thinner (~1.5–2 mm) and therefore larger.)
- **Area = V / h** [D]:

| Volume | Area at h = 2.5 mm | Equivalent circle Ø |
|---|---|---|
| 50 mL | 0.02 m² | 16 cm |
| 100 mL | 0.04 m² | 23 cm |
| 250 mL | 0.10 m² | 36 cm |
| 500 mL | 0.20 m² | 50 cm |
| 1,000 mL | 0.40 m² | 71 cm |
| 2,000 mL | 0.80 m² | 1.0 m |
| 3,000 mL | 1.20 m² | 1.24 m |

- **Spreading speed:** viscous gravity currents (Huppert 1982) reach the capillary-limited area within about a second for a dumped volume [D, K-M R40]. With a continuous source, the pool radius grows as `R = √(Q·t / (π·h))`. For example, 1 L/min gives R ≈ 36 cm at 1 min and ≈ 50 cm at 2 min with h = 2.5 mm [D].
- **Real floors** are not flat. Pools follow slope and grout lines, form fingers and stop at edges. Recompute on a heightfield.
- **Pool gel:** after **5–15 min** the pool gels and stops spreading. New blood flows over or around the gel, giving a layered, lobed outline. Serum separates at the rim after 30 min – 2 h [K-M].
- **Absorbent surfaces:** fabric, carpet and wood wick blood. The stain area is 2–4× the equivalent pool area and shallower. The colour is duller and browner as it dries [K-M], [G].

### 10.4 Drying and colour change

Drying time is controlled by water evaporation (~80 % of the mass). Indoor still air at 20–22 °C and 40–60 % RH evaporates roughly 0.05–0.1 mm of water per hour from a flat pool. Small drops dry much faster because of edge-enhanced evaporation. Warm skin (32–34 °C) roughly **doubles** the rate. Airflow speeds drying. High humidity slows it [K-M R41, D].

| Deposit | Thickness | Surface | Tacky | Touch-dry | Fully dry / hard | Notes | Source |
|---|---|---|---|---|---|---|---|
| Smear or wipe | < 0.05 mm | Skin (33 °C) | 30–60 s | 1–3 min | 5–10 min | Matte red-brown film. Cracks as skin moves | [K-M], [G] |
| Smear or wipe | < 0.05 mm | Steel (20 °C) | 1–2 min | 3–8 min | 10–20 min | Glossy, translucent amber-brown to red | [K-M], [G] |
| Small spatter (1–5 µL, 1–4 mm stains) | 0.1–0.3 mm | Steel | ~1 min (edge "skeletonises" first) | 5–15 min | 15–30 min | Dried edge ring forms in ~50 s | [K-M R29] |
| Drip stain (50 µL, 15–20 mm) | 0.2–0.5 mm | Steel / tile | 5–15 min | 20–60 min | 1–2 h | Radial cracks. Dark centre, lighter ring | [K-M R41], [G] |
| Rivulet on skin | 0.1–0.3 mm | Skin | 2–5 min | 10–20 min | 30–60 min | Crust. Flakes when rubbed | [K-M], [G] |
| Pool 100 mL – 2 L | 2–3 mm | Floor | Gels at 5–15 min | Surface skin at 1–2 h. Edges dry at 2–6 h | **24–72 h** | Serum rim. Dries into cracked plates ("mud-crack") | [D], [K-M] |

**Colour ramp over time** (apply per stain; thin stains move along it faster than thick ones) [K-M R42]:

| Age | Thin stain | Thick stain / pool | Chemistry |
|---|---|---|---|
| 0 min | `#C0141E` (arterial) / `#8E1420` (venous) | `#5E070C` glossy | Oxyhaemoglobin |
| 10–30 min | `#9A1418` | `#4A060C`, gel | Deoxygenation, clotting |
| 1–2 h | `#7A2016` red-brown | `#3A0808` | Methaemoglobin starts to form |
| 6–24 h | `#5C2414` reddish-brown | `#2A0C0A` near-black, dull | Mostly methaemoglobin |
| Days | `#4A2618` brown | `#24100C` | Hemichrome |
| Weeks+ | `#33201A` dark brown-black | black-brown, flaking | Hemichrome, degradation |

(Bremmer et al. used reflectance spectroscopy to track the oxyHb → metHb → hemichrome sequence [K-M R42].) **Fact-check:** the chemistry sequence is ✓ verified. Outside the body, oxyHb auto-oxidises to metHb, which is no longer reduced back, and metHb then denatures to hemichrome. This drives the change from bright red to dark brown [V16, citing Bremmer et al., *PLoS One* 2011;6(7):e21845]. The **timings** in the ramp and in the drying table above are **unverified** estimates.

**Steel-specific effects:**
- Blood on smooth steel dries as a glossy film. Thick deposits crack into plates ~1–3 mm across that **curl and flake off** at the edges within hours [K-M].
- On uncoated carbon steel, rust (orange-brown halo) develops over days [K-M].
- On hot steel (torch-heated or a gun barrel): instant sizzling, then a brown and black burnt crust (7.5).

### Simulation parameters (surfaces)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `drop_volume` | 50 (skin/fingers), 15 (hair tips), up to 100 (large flat edges) | µL | | [K-H R29], [D] |
| `drop_terminal_v` | 8 (7.5–9) | m/s | Corrected: was 7.6. The classic BPA value is 7.6; a physics estimate gives ~9. See 10.1 | [K-H R29], [D] |
| `stain_spread_factor` | 3–5.5 × drop Ø | — | Grows with impact velocity. Corrected: was 3–5. Laan correlation gives ~4.7 at 1 m and ~5.6 at terminal velocity | [D] via [R39] |
| `rivulet_width` | 2–5 | mm | | [K-M] |
| `rivulet_speed_vertical` | 1–5 (clamp 0.5–10) | cm/s | Lubrication-film formula, stop–go | [D] |
| `rivulet_residue` | 5–15 | µL/cm | Finite drop runs 3–10 cm | [D] |
| `drip_release_volume` | 30–60 | µL | Pendant drop at a low point | [D] |
| `stream_threshold` | 15–30 | mL/min | Drips merge into a continuous stream | [D] |
| `pool_thickness` | 2.5 (1.6–3.3) | mm | Area = V/h | [D] |
| `pool_gel_time` | 5–15 | min | Freeze spreading, then layer | [K-H] |
| `evap_rate_flat` | 0.05–0.1 (×2 on warm skin, ×2–4 with airflow or heat) | mm water/h | | [K-M], [D] |
| `dry_time_pool` | 24–72 | h | | [D] |
| `dry_time_drip_stain` | 1–2 | h | | [K-M] |
| `dry_time_skin_smear` | 5–10 | min | | [K-M], [G] |
| `colour_age_ramp` | Table in 10.4 | — | Index by (age × thinness factor) | [K-M R42], [G] |

### Visual/behavioural checklist
- Drips are ~4–5 mm beads that fall and leave round stains ~1.5–2 cm wide on the floor, with satellite droplets if they fall into existing blood.
- Rivulets run in narrow lines along creases, pause, then jerk forward. They collect at the chin, earlobe or fingertips and drip.
- The pool grows as a ~2.5 mm-thick sheet: 500 mL is about a 50 cm circle, 1 L about 70 cm, 2 L about a metre.
- After ~10 min the pool stops spreading and becomes gelatinous. A yellow rim appears later. Edges dry and darken first.
- Blood on skin loses its wet sheen within minutes and becomes a matte red-brown crust. Blood on steel stays glossy longer, then cracks and flakes.

---

## 11. Vessel anatomy for the network

Diameters are adult **lumen** diameters [K-H R43, R44] unless marked [K-M]. Specific diameter studies are cited where I recall them: coronary R45, carotid R46, femoral R47, radial R48, aorta R49.

Depth values assume a lean-to-average build. **Add subcutaneous fat for heavier procedural bodies** [K-M].

**Fact-check of diameters.** Most rows were checked against the HuBMAP Human Reference Atlas vasculature table (HRA-VCCF). That table compiles published measurements with citations [V17]. Other checks came from Framingham CT data quoted in Cohn [V7b], from Hurst [V18] and from Marino [V1c]. Rows marked ✓ agree with those sources. Rows without a mark (vertebral, subclavian and axillary arteries, the radial and forearm arteries, SFA, popliteal, tibial, and the scalp and face arteries) could **not** be checked. Their values are from memory of the standard references. Aortic diameters in men are on average **2–3 mm larger than in women** [V7b]. The 0.9× female scale factor in the sim parameters is consistent with the data (CCA 6.1 vs 6.5 mm; CFA 8.2 vs 9.8 mm; infrarenal aorta 16.7 vs 19.3 mm).

"Kind" in the tables below: elastic artery (E) or muscular artery (M).

### 11.1 Arterial tree: trunk, neck, upper limb

| Segment | Parent | Lumen Ø mm (default) | Length cm | Rest flow mL/min | Course and landmarks | Depth from skin | Kind |
|---|---|---|---|---|---|---|---|
| Aortic root / ascending aorta | LV | 28–36 (32). ✓ verified: Hurst gives "~3 cm". A CT series (n = 200) gives lumen 36.1 mm (M) / 31.7 mm (F) [V17, V18]. Use 33–35 for older procedural bodies | ~5 | 5,000 | From the aortic valve (behind the left sternal half at the 3rd intercostal space) upward to the level of the sternal angle (T4) | 4–6 cm behind the sternum surface | E |
| Aortic arch | Asc. aorta | 25–30 (27). ✓ verified: 26.1 ± 3.6 mm on CT, n = 534 [V17] | ~5 | 5,000 → 3,600 | Arches back and to the left behind the manubrium. Its top is ~2–3 cm below the suprasternal notch. Ends at T4 | 5–7 cm | E |
| Brachiocephalic trunk | Arch | 10–14 (12). ✓ verified: 11.1–11.6 mm on CT [V17] | 3.5–4.5 (4). Corrected: was 4–5. Cadaveric length 3.7 cm (F) / 3.9 cm (M) [V17] | 650–800 | Up and to the right. Divides behind the right sternoclavicular joint | 3–5 cm | E |
| R common carotid | Brachiocephalic | 6–8 (6.5; F ~6). ✓ verified: Krejza 2006 ultrasound lumen 6.52 ± 0.98 mm (M, n = 194) and 6.10 ± 0.80 mm (F, n = 306) [V17] | 9–10 | 350–450 | From behind the SC joint, up the neck **beside the trachea, then the larynx**, under the anterior border of the SCM in the carotid sheath (internal jugular lateral, vagus behind). Pulse at the anterior border of the SCM at thyroid-cartilage level. Surface line from the SC joint to midway between the mastoid and the angle of the mandible. **Bifurcates at the upper border of the thyroid cartilage (~C3–C4; range C2–C6)** | Lower neck 3–4 cm (under the SCM). Carotid triangle 1.5–2.5 cm | E |
| L common carotid | Arch | 6–8 (6.5) | 12–15 | 350–450 | Same course in the neck. Its first part is in the thorax | as right | E |
| Carotid bulb | CCA | 7–9 | 2 | — | Dilated bifurcation. Carries the baroreceptors | 1.5–2.5 cm | E |
| Internal carotid (cervical) | CCA | 4–5.5 (4.8). Corrected: was 4.5–5.5 (5). Lumen 4.8 ± 0.65 mm (M) and 4.7 ± 0.66 mm (F) [V17] | ~10 (+ ~8 intracranial) | 220–300 | Posterolateral at first, then straight up to the skull base with **no neck branches**. Enters the carotid canal (petrous temporal) just in front of the jugular foramen | 2–4 cm | E→M |
| External carotid | CCA | 3.5–5 (4) | 5–7 | 100–150 | Anteromedial. Ends in the parotid behind the neck of the mandible as the superficial temporal and maxillary arteries. Branches: superior thyroid, lingual, facial, occipital, posterior auricular, ascending pharyngeal | 1.5–3 cm | M |
| Vertebral | Subclavian (1st part) | 3–4 (3.5; left often dominant) | 18–20 | 70–120 each | Enters the C6 transverse foramen (~90 % of people), climbs through C6–C1, loops over the posterior arch of C1 (suboccipital triangle), passes the foramen magnum and joins its partner to form the basilar artery at the pontomedullary junction | 4–7 cm, in bone | M |
| R subclavian | Brachiocephalic | 7–10 (8.5) | 6–8 | 200–350 | Arches over the lung apex, behind the anterior scalene, over the 1st rib, ~1.5–2 cm above the middle of the clavicle. Becomes the axillary at the lateral border of the 1st rib | 3–5 cm, behind the clavicle | E |
| L subclavian | Arch | 7–10 (8.5) | 9–10 | 200–350 | Longer intrathoracic course | 3–5 cm | E |
| Internal thoracic | Subclavian | 2–3 | ~20 | 20–50 | Runs vertically ~1–2 cm lateral to the sternal edge, behind the costal cartilages | 1.5–3 cm | M |
| Intercostals | Aorta / int. thoracic | 1.5–2.5 | ribs | 5–15 each | In the costal groove along the lower border of each rib (vein, artery, nerve from top to bottom) | 1–4 cm | M |
| Axillary | Subclavian | 5–8 (6.5) | 10–12 | 100–200 | From the 1st rib to the lower border of teres major, behind pectoralis minor, surrounded by the brachial plexus cords. Surface line (arm abducted) from mid-clavicle to the medial arm at the axillary fold | 3–5 cm | M |
| Brachial | Axillary | 3.5–5 (4.2). ✓ verified: 4.36 ± 0.87 mm [V17] | 20–25 | 50–120 | In the medial bicipital groove with the median nerve. In the cubital fossa, medial to the biceps tendon, under the bicipital aponeurosis. Divides ~1–2 cm below the elbow crease (neck of the radius). High division occurs in ~10–15 % of people | Mid-arm 1–2 cm. Elbow ~1 cm | M |
| Radial | Brachial | 2.2–3.0 (2.5; F 2.2) | 20–25 | 20–40 | Down the lateral forearm under brachioradialis. **At the wrist it is superficial, between the flexor carpi radialis (FCR) tendon (medial) and the radial styloid**. Then into the anatomical snuffbox and the deep palmar arch | Wrist 3–7 mm | M |
| Ulnar | Brachial | 2.0–3.0 (2.4) | 22–25 | 20–40 | Medial forearm under flexor carpi ulnaris (FCU). At the wrist, lateral to the FCU tendon and pisiform, with the ulnar nerve on its medial side. Forms the superficial palmar arch | Wrist 5–10 mm | M |
| Palmar arches / digital | Radial, ulnar | Arch 1.5–2. Common digital 1.2–1.6. Proper digital 0.8–1.2 | — | 1–5 per digit | The superficial arch lies at the level of the distal border of the fully extended thumb. Digital arteries run along both sides of each finger | 2–5 mm | M |
| Coronary: left main | Aortic sinus | 4–5 (4.5) | 1–2.5 | 225–250 total | Splits into the LAD (anterior interventricular groove to the apex, 3.5–4 mm proximally) and the circumflex (left AV groove, 3–3.5 mm) | On the epicardium | M |
| Coronary: right (RCA) | Aortic sinus | 3.5–4 (3.8) | 12–14 | — | Right AV groove, down to the posterior interventricular groove | Epicardium | M |

### 11.2 Arterial tree: abdomen, pelvis, lower limb

| Segment | Parent | Lumen Ø mm (default) | Length cm | Rest flow mL/min | Course and landmarks | Depth | Kind |
|---|---|---|---|---|---|---|---|
| Descending thoracic aorta | Arch | 20–26 (24). ✓ verified: Framingham CT 25.8 mm (M) / 23.1 mm (F) [V7b]; 24.4 ± 3.9 mm (CT, n = 534) [V17]; Hurst gives 2–2.3 cm [V18] | ~20 | 3,600 | T4 to T12 (aortic hiatus), left anterolateral to the vertebral bodies. Its isthmus (just beyond the left subclavian) is the classic blunt-rupture site | 8–12 cm from the front | E |
| Abdominal aorta, suprarenal | Thoracic | 20–23 (21) | ~5 | 3,600 → 2,000 | Enters at T12 slightly left of midline | Lean: 5–8 cm from the front. Heavier: 10–15 cm | E |
| Celiac trunk | Aorta (T12) | 6–8 | 1–2 | 800–1,100 | Splits into the left gastric, common hepatic (4–5 mm) and splenic (4–6 mm, tortuous along the upper border of the pancreas) arteries | deep | M |
| Superior mesenteric (SMA) | Aorta (L1) | 6–8 | ~20 | 500–700 fasting | Behind the neck of the pancreas, into the mesentery | deep | M |
| Renal (each) | Aorta (L1–L2) | 5–6 (4–7) | 3–5 (right longer, passes behind the IVC) | 500–600 | To the renal hilum ~5 cm from midline at L1–L2 | 8–12 cm from the back | M |
| Abdominal aorta, infrarenal | Aorta | 15–20 (M 18, F 16). ✓ verified: Framingham CT 19.3 mm (M) / 16.7 mm (F) [V7b]; ultrasound lumen 18.4 ± 3.3 / 16.6 ± 3.0 mm [V17]; Hurst gives 1.7–1.9 cm [V18] | 8–10 | 800–1,000 | Bifurcates at **L4**, ~1–2 cm below and left of the umbilicus. **Aneurysm defined as ≥ 30 mm** | Lean 4–8 cm | E |
| Common iliac | Aorta | 8–12 (10). ✓ verified: 9.9 ± 1.6 mm (M) / 8.8 ± 1.2 mm (F) [V17] | 4–6 | 350–500 | To the sacroiliac joint (L5–S1). Surface: the upper third of a line from the aortic bifurcation to the mid-inguinal point | deep | E |
| Internal iliac | Common iliac | 5–7 | ~4 | 100–150 | Pelvic organs and gluteal region (superior gluteal artery exits above piriformis) | deep | M |
| External iliac | Common iliac | 7–9 (8) | ~10 | 250–350 | Along the pelvic brim, medial to psoas, to the **mid-inguinal point** under the inguinal ligament | deep | M |
| Common femoral | External iliac | 7.5–11 (M 9.0, F 8.2). Corrected: was 7–10 (8.5). Sandgren 1999 ultrasound means are 9.8 mm (M, n = 59) and 8.2 mm (F, n = 63); the cohort spans adulthood and diameter grows with age, so ~9 suits a young adult male [V17] | 3–5 (cadaveric mean 5.1 cm [V17]) | 250–400 | In the femoral triangle at the **mid-inguinal point** (midway between the anterior superior iliac spine and the pubic symphysis). Order from lateral to medial: **N**erve, **A**rtery, **V**ein ("NAV"). Pulse palpable | 2–4 cm (1–6 cm by build) | M |
| Profunda femoris | CFA (3.5–5 cm below the ligament) | 5–6 | 12+ | 100–150 | Posterolateral, deep. Perforating branches wind around the femur | 4–8 cm | M |
| Superficial femoral | CFA | 5–7 (6) | 25–30 | 150–250 | Anteromedial thigh under sartorius, through the adductor (Hunter's) canal. Becomes the popliteal at the adductor hiatus, at the junction of the middle and lower thirds of the thigh (~10 cm above the knee joint) | 3–6 cm | M |
| Popliteal | SFA | 5–7 (5.5) | 15–20 | 80–150 | Deepest structure of the popliteal fossa, directly on the joint capsule. From superficial to deep: nerve, vein, artery. Tethered at both ends, so it is vulnerable in knee dislocation. Divides at the lower border of popliteus | 3–5 cm | M |
| Anterior tibial | Popliteal | 2.5–3.5 | ~30 | 30–50 | Through the interosseous membrane, down the anterior compartment. Becomes the **dorsalis pedis** (2–3 mm) midway between the malleoli. Pulse on the dorsum of the foot, lateral to the extensor hallucis longus (EHL) tendon | Ankle ~5 mm | M |
| Posterior tibial | Tibioperoneal trunk | 2.5–3.5 | ~30 | 30–50 | Deep posterior compartment. Pulse midway between the medial malleolus and the Achilles tendon | Ankle ~1 cm | M |
| Peroneal (fibular) | Tibioperoneal trunk | 2–3 | ~25 | 20–40 | Deep, along the fibula | deep | M |

### 11.3 Head and face superficial vessels (for scalp and face wounds)

| Vessel | Ø mm (default) | Course and landmarks | Depth | Rest flow (estimate) | Source |
|---|---|---|---|---|---|
| Superficial temporal artery | 1.5–2.5 (2.0) | Emerges from the parotid and crosses the root of the zygomatic arch **~1 cm in front of the tragus** (palpable pulse). Divides 2–4 cm above the arch into frontal and parietal branches (1.2–1.8 mm), which are tortuous and visible under the skin in lean or elderly people | 3–6 mm (in the scalp's connective-tissue layer) | 10–30 mL/min | [K-H R43], flow [K-L] |
| Facial artery | 2–3 at the mandible (2.5), tapering to ~1.5 | Crosses the lower border of the mandible at the **anterior edge of masseter** (~2.5–3 cm in front of the angle, palpable notch). Winds ~1.5 cm lateral to the angle of the mouth, gives the superior and inferior labial arteries (1–1.5 mm, in the lips between muscle and mucosa), then runs up beside the nose as the angular artery to the medial canthus | 5–10 mm | 20–40 mL/min | [K-H R43], flow [K-L] |
| Occipital artery | 1.5–2.5 (2.0) | Deep to the mastoid. Pierces the fascia between the SCM and trapezius attachments ~2.5–4 cm lateral to the external occipital protuberance (inion), near the superior nuchal line. Climbs tortuously over the occiput with the greater occipital nerve | 4–8 mm | 10–20 mL/min | [K-H R43], flow [K-L] |
| Posterior auricular artery | 1–1.5 | Behind the ear, over the mastoid | 3–5 mm | 5–10 | [K-M] |
| Supraorbital / supratrochlear arteries (internal carotid system) | 0.8–1.2 | Exit the supraorbital notch (~2.5 cm from midline) and the supratrochlear notch (~1.5–2 cm from midline). Climb the forehead. They anastomose with the superficial temporal branches | 3–5 mm | 3–8 | [K-H R43] |
| Maxillary → middle meningeal artery | 2.5–3.5 → 1.5–2 | Deep (infratemporal fossa). The middle meningeal enters the skull through the foramen spinosum. Its anterior branch runs under the **pterion** (~3–4 cm above the midpoint of the zygomatic arch). Tearing it with a temporal fracture causes an **epidural haematoma** | Inside the skull | — | [K-H R43] |
| Sphenopalatine artery / Kiesselbach's plexus | < 1–2 | Kiesselbach's plexus on the anterior nasal septum is the source of ~90 % of nosebleeds. The posterior (sphenopalatine) source bleeds more heavily and drains into the throat | 1–2 mm under the mucosa | — | [K-H] |
| Scalp venous network | 1–3 | Accompanies the arteries (superficial temporal, occipital, posterior auricular and supraorbital veins). **Emissary veins** (parietal, mastoid, occipital) pass through the skull to the dural sinuses. Diploic veins run inside the skull bone. Open skull plus upright posture risks air entry through the sinuses | Connective-tissue layer | — | [K-H R43] |
| Scalp thickness overall | 5–7 mm (skin 3–5 mm) | Layers SCALP (7.3) | — | — | [K-M R30] |

### 11.4 Major veins

| Vein | Ø mm (default) | Course and landmarks | Pressure (supine) | Rest flow mL/min | Notes |
|---|---|---|---|---|---|
| Internal jugular (IJV) | 10–20 (14; right usually larger). Very position-dependent. ✓ verified: 15.5 ± 5.2 mm on CT, n = 190 [V17]. A 15° head-down tilt increases the diameter by 20–25 %, and the IJV lies "anterior and lateral to the carotid artery" [V1c] | From the jugular foramen down the neck in the carotid sheath, **lateral to the common carotid**, under the SCM. Its lower end lies in the small hollow between the sternal and clavicular heads of the SCM. Joins the subclavian behind the sternal end of the clavicle. Surface line: earlobe → medial clavicle | 3–8 mmHg. **≤ 0 when upright (collapses)** | 300–700 each supine | Air embolism risk [K-H] |
| External jugular (EJV) | 4–7 (5) | From just below the angle of the mandible, runs **superficially across the SCM** obliquely downward and backward. Pierces the fascia ~2–3 cm above the midpoint of the clavicle and drains into the subclavian. Visible when distended (straining, tamponade) | 3–8 | 20–60 | Just under the skin [K-H] |
| Anterior jugular | 2–4 | Near midline, lower neck | — | small | [K-M] |
| Subclavian vein | 7–12 (10). Corrected: was 10–13 (12). Marino: "3–4 cm in length, and the diameter is 7–12 mm in the supine position" [V1c] | Continuation of the axillary vein at the 1st rib. Passes **in front of** anterior scalene (the artery lies behind it), under the medial clavicle. Held open by fascia | 3–8 | 150–300 | Air embolism risk [K-H] |
| Brachiocephalic veins | 12–16 (14) | Left: ~6–7 cm, crosses obliquely behind the manubrium. Right: 2–3 cm, vertical | 2–6 | — | [K-M] |
| Superior vena cava (SVC) | 18–22 (20). ✓ verified: 19 ± 3.7 mm and 20.4 mm [V17] | Formed behind the right 1st costal cartilage. Runs down along the right sternal border. Enters the right atrium at the right 3rd costal cartilage. ~7 cm long. **Lower half is inside the pericardium** | 2–6 | 1,300–1,700 | [K-H R43] |
| Inferior vena cava (IVC) | 13–21 (17). Corrected: was 17–25 (21). Measured means are 16.4–17.4 mm [V17]; 21 mm is the conventional upper limit of normal, not a typical value (knowledge). Collapses > 50 % on inspiration when CVP is low. Flattens further in haemorrhage | Formed at **L5** from the common iliac veins. Rises to the right of the aorta, through a groove behind the liver (receiving the hepatic veins), through the diaphragm at **T8** and into the right atrium | 5–10 (infrarenal) | 3,000–3,500 | Retrohepatic injuries are catastrophic [K-H] |
| Hepatic veins (3) | 8–12 | Into the IVC just below the diaphragm | ~CVP | ~1,350 total | [K-H] |
| Renal veins | Left 8–10 (~7 cm, crosses **in front of** the aorta just below the SMA). Right 6–8 (~2–3 cm) | | 5–10 | ~550 each | [K-H] |
| Portal vein | 10–13 (11; > 13 abnormal). ✓ consistent: 12.1 mm (M) / 8.6 mm (F), single reference model [V17] | Formed behind the neck of the pancreas (L1–L2) from the superior mesenteric and splenic veins. ~7–8 cm up to the porta hepatis in the hepatoduodenal ligament | 5–10 | 1,000–1,200 | Note only: not part of the systemic loop [K-H] |
| Common iliac vein | 12–16 (14) | Behind and to the right of the arteries | 6–10 | ~500 each | [K-M] |
| Common femoral vein | 10–14 (12). ✓ consistent: cadaveric outer diameter ~14 mm, n = 12 [V17]. Marino puts it "just medial to the femoral artery … 2 to 4 cm from the skin". A 15° head-up tilt increases its cross-section by ~50 % [V1c] | **Medial to the femoral artery** in the femoral triangle. The great saphenous vein joins it ~3–4 cm below and lateral to the pubic tubercle | 8–12 (supine). ~80–90 standing still at foot level | 250–400 | Leg-hanging surge [K-H] |
| Femoral vein ("superficial femoral vein") | 8–12 | Alongside the superficial femoral artery (a deep vein despite the name) | — | — | [K-H] |
| Popliteal vein | 6–10 | Between the nerve and the artery in the fossa | — | — | [K-H] |
| Great saphenous vein | 3–5 (up to 6–8 at the junction) | **Constant position just in front of the medial malleolus**. Up the medial leg, behind the medial femoral condyle, anteromedial thigh to the saphenofemoral junction | — | — | Just under the skin [K-H] |
| Small saphenous vein | 2–4 | Behind the lateral malleolus, up the back of the calf to the popliteal vein | — | — | [K-H] |
| Arm superficial veins | Cephalic 2–5 (lateral, deltopectoral groove). Basilic 3–6 (medial). Median cubital 2–5 (cubital fossa) | Visible veins that flatten in shock | 6–10 | — | [K-H] |
| Venae comitantes | 1–3 (paired) | Accompany the brachial, radial, ulnar and tibial arteries | — | — | [K-H] |

### 11.5 Heart, great vessels, organs

| Structure | Key data | Source |
|---|---|---|
| Heart | 250–350 g (M), 230–280 g (F). ~12 × 8–9 × 6 cm. **Surface projection:** right border ~1–2 cm right of the sternum (3rd–6th costal cartilages). Apex at the left 5th intercostal space, mid-clavicular line (~8–9 cm from midline). Upper border at the 2nd–3rd costal cartilages | [K-H R43] |
| Chambers | LV: end-diastolic volume 120–150 mL, wall 8–11 mm, 120/8 mmHg. RV: end-diastolic volume 140–160 mL, wall 3–5 mm, 25/4. LA/RA: 50–80 mL, wall 2–3 mm, mean 8 / 4 mmHg. The **RV lies most anteriorly**, behind the sternum and left parasternal region, so it is the chamber most often hit by stab wounds. Then LV, then RA | [K-H], stab frequency [K-M] |
| Pericardium | Fibrous and non-distensible acutely. Normal fluid 15–50 mL | [K-H R33] |
| Pulmonary trunk | 25–29 mm (> 29 abnormal). Left and right pulmonary arteries 18–22 mm. Pulmonary veins 10–15 mm (×4) | [K-M] |
| Liver | 1.4–1.6 kg. Right upper quadrant. Its dome reaches the right 5th rib, the lower border follows the costal margin. Contains 450–650 mL of blood. Receives 1,350 mL/min | [K-H R4] |
| Spleen | 150–200 g, ~12 × 7 × 4 cm. Lies under the left 9th–11th ribs posterolaterally, long axis along the 10th rib. 150–300 mL/min | [K-H] |
| Kidneys | 120–170 g, ~11 × 6 × 3 cm. T12–L3, hilum at L1 ~5 cm from midline, right slightly lower. Enclosed in perirenal fat and Gerota's fascia | [K-H] |
| Brain | 1.2–1.4 kg, 750 mL/min. The circle of Willis is complete in only ~20–50 % of people, so tolerance of one-sided carotid loss varies | [K-M] |

### 11.6 Suggested graph topology for the sim

Tier 1 (recommended default, cheapest) [G]:
- One global arterial pressure P_a(t), from Section 3.3 plus the parallel-shunt correction (4.1). One global central venous pressure. Per-segment local pressure = global pressure − distal pressure drop (Poiseuille, table 4.3) + hydrostatic term.
- Vessel segments are just *labels with geometry* (Ø, length, depth, kind, parent) for wound placement, flow caps, distal-ischaemia flags and VFX.

Tier 2 (optional, still cheap):
- **Node count:** ~60–80 arterial segments, ~40–60 venous segments and ~20 capillary beds: brain; face and scalp (left/right); each arm (upper arm, forearm, hand); each leg (thigh, calf, foot); myocardium; lungs; liver; spleen; kidneys; gut; trunk wall.
- **Conduits:** Poiseuille resistance. Wounds are nonlinear orifice sinks.
- **Beds:** resistance tuned so each bed carries its resting flow at MAP 93: R_bed = (P_art − P_ven) / Q_rest.
- **Heart:** a pump with CO = HR × SV(preload).
- **Solving:** at 10–20 Hz (a sparse system of ~150 unknowns takes microseconds). Pulsatility is added analytically per beat for VFX, not solved.
- **Distal ischaemia:** a bed downstream of a transected or occluded artery with no collateral gets flow → 0. The limb turns pale, cold and pulseless over minutes. The "6 Ps": pain, pallor, pulselessness, paraesthesia, paralysis, poikilothermia (limb takes room temperature). Muscle is irreversibly damaged after ~4–6 h of warm ischaemia [K-H R1].
- **Collaterals** (for distal-stump backflow): palmar arches (radial ↔ ulnar), circle of Willis (left ↔ right internal carotids, basilar), external ↔ internal carotid via facial/angular and superficial temporal/supraorbital, geniculate network around the knee, profunda ↔ popliteal [K-H R43].

### Simulation parameters (anatomy)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `vessel_table` | Sections 11.1–11.4 (defaults in brackets) | mm, cm | Scale diameters × (height/178 cm)^0.5 and by sex (F ≈ ×0.9) | [K-H R43–R49], scaling [G] |
| `carotid_bifurcation_level` | Upper border of thyroid cartilage, C3–C4 (range C2–C6) | vertebra | | [K-H R43] |
| `aortic_bifurcation_level` | L4 (≈ umbilicus) | vertebra | | [K-H R43] |
| `ivc_origin / ivc_diaphragm` | L5 / T8 | vertebra | | [K-H R43] |
| `femoral_landmark` | Mid-inguinal point. NAV from lateral to medial | — | | [K-H R43] |
| `depth_fat_offset` | + subcutaneous fat thickness (1–6 cm, by BMI and site) | cm | | [K-M] |
| `ischaemia_irreversible` | 4–6 | h | Muscle, warm | [K-H R1] |
| `collateral_pairs` | See 11.6 | — | | [K-H R43] |

---

## 12. Engineering notes for 60 fps (brief; see the tech doc for detail)

The user's constraint is that Godot must hold 60 fps with blood, brain and gore. The physiology in this document is **not** the bottleneck [G]:

- **Physiology plus vessel network:** a Tier 2 solve at 10–20 Hz on the CPU costs well under 0.1 ms per tick for ~150 unknowns. Run it off the render thread and interpolate the values VFX reads.
- **Particles are the real budget.**
  - An arterial jet at 1 L/min is 16.7 mL/s. Represented as literal 50 µL drops, that would be ~330 drops/s.
  - Instead, draw the jet as a **ribbon or mesh stream** (height and velocity from Section 6.2, pulsed per beat) plus ~30–80 GPU particles/s for breakup drops. The drops can be larger (100 µL "super-drops" with 2× stain size).
- **Stains:** decals plus a floor pool rendered as a **heightfield or SDF blob** whose area comes from V / 2.5 mm, not from particle accumulation. Age each decal through the colour ramp in a shader (one float per decal: age × thinness).
- **Rivulets on skin:** paint into a per-character wetness/blood mask texture (UV space) with a gravity-advected brush at 1–10 cm/s. A skin shader samples it (wet specular while fresh, matte brown when dried).
- **Cap simultaneous emitters** (e.g., ≤ 6 jets, ≤ 20 drips). The sim still tracks all wounds for volume accounting even when their VFX is culled.

---

## 13. Load-bearing numbers (quick reference)

The "Fact-check" column was added in v1.1. Details are in Section 16.

| # | Claim | Value | Tag | Fact-check |
|---|---|---|---|---|
| 1 | Blood volume | Adult male 70 (66–77) mL/kg. Female 60–65 mL/kg. Default 5.0 L / 3.8 L. Nadler formula | [K-H R1, R2] | **✓ verified** [V1, V9, V10] |
| 2 | ATLS classes | I ≤ 15 %, II 15–30 %, III 30–40 %, IV > 40 %. HR < 100 / 100–120 / 120–140 / > 140. RR 14–20 / 20–30 / 30–40 / > 35. SBP normal until Class III | [K-H R1] | **✓ verified** from secondary sources [V1, V11]; ATLS manual not reached |
| 3 | Real HR response is weaker than ATLS; biphasic bradycardic faint at ~20–35 % loss; shock index ≥ 1.4 means severe | — | [K-M R11–R14] | **Corrected:** bradycardic-faint chance 35–45 % (was 25–35 %) [V2]. SI cut-offs unverified; citations verified [V12] |
| 4 | Acute loss ≥ 40–50 % BV usually fatal untreated | — | [K-H R1, R18] | **✓ verified**, with the caveat that ~30 % *can* be fatal [V1] |
| 5 | LOC 5–10 s after complete stop of cerebral flow. 10–15 s of possible voluntary activity after heart destruction | — | [K-H R17, R18] | Unverified (sources unreachable) |
| 6 | Irreversible brain injury after 4–6 min of no flow (normothermic) | — | [K-H] | Unverified |
| 7 | Orifice flow Q = 0.6·A·√(2ΔP/ρ). A 3 mm hole at 90 mmHg gives ~1.2 L/min upper bound. Large arterial wounds act as parallel shunts that collapse MAP | — | [D] | **✓ verified** (arithmetic recomputed) |
| 8 | Pressure head: 1 mmHg = 12.8 mm of blood. SBP 120 gives a 1.54 m ideal jet. Real jets 0.35–0.65 × ideal, i.e. 0.55–1.0 m vertical at normal BP | — | [D] | **✓ verified** (arithmetic). Cv is not validated against measurements |
| 9 | Bleed-out times, untreated. Aorta/heart: LOC 5–30 s, death 1–5 min. Carotid: LOC 20–90 s, death 2–5 min. Femoral: LOC 2–5 min, death 3–10 min. Brachial: 10–30 min. Radial: usually self-limiting | — | [K-M] + [D] | Unverified; internally consistent. Treat as tuning targets |
| 10 | Partial lacerations bleed more than complete transections (retraction and spasm) | — | [K-H R1] | Unverified (standard teaching) |
| 11 | Hydrostatic 0.78 mmHg per cm. Neck and dural veins go sub-atmospheric when upright (air embolism). 200–300 mL of air (3–5 mL/kg) rapidly is lethal. ~100 mL/s can enter a large opening | — | [D], [K-M R50] | **Corrected:** ≥ 100 mL/s. 100 mL/s passes even a 1.8 mm (14 G) opening at a 5 mmHg gradient (was "a large opening"). Lethal 200–300 mL **✓ verified** [V1c]. 0.78 mmHg/cm ✓ (arithmetic) |
| 12 | Tamponade at 100–200 mL of acute pericardial blood. Beck's triad with distended neck veins | — | [K-H R27, R33] | **✓ verified** [V7, V8]. Added: low-pressure tamponade in hypovolaemia (neck veins may not distend) |
| 13 | Haemothorax capacity 2.5–3 L per side. Massive > 1,500 mL or > 200 mL/h × 2–4 h | — | [K-H R1, R34] | Massive-haemothorax thresholds **✓ verified** (also > ⅓ BV; 200–250 mL/h) [V6, V14]. Capacity unverified |
| 14 | Fracture losses: femur 1–1.5 L, pelvis 1.5–4 L, tibia/humerus 0.5–0.75 L | — | [K-H R1] | Unverified |
| 15 | Bleeding time 2–7 min (small wounds). Whole-blood clotting 5–15 min. Serum separation 30–60 min+. Scalp vessels are held open and keep bleeding | — | [K-H], [K-H R30] | Lee-White 5–15 min **✓ verified** (secondary sources) [V13]. The rest is unverified |
| 16 | Drops ~50 µL, Ø 4.6 mm, terminal velocity ~7.6 m/s | — | [K-H R29], [D] | Ø ✓ (arithmetic). **Corrected:** terminal velocity 7.5–9 (use 8) m/s; stain spread 3–5.5× (was 3–5×) |
| 17 | Pool thickness ~2.5 mm (capillary length 2.3 mm): 500 mL ≈ 50 cm circle, 1 L ≈ 71 cm. Pool gels in 5–15 min | — | [D] | **✓ verified** (arithmetic; gel time matches Lee-White) |
| 18 | Drying: skin smear 5–10 min. Drip stain on steel 1–2 h. Pool 24–72 h. Colour red → red-brown (hours) → brown (1 day) → black-brown (weeks) | — | [K-M R41, R42], [D] | Chemistry sequence ✓ [V16]. Timings unverified |
| 19 | Venous blood looks darker because deoxyHb absorbs ~5–10× more red light. μa per mm at 620 nm: ~0.5 (oxy) vs ~3.5 (deoxy) | — | [K-H R37], [D] | **✓ verified** against Prahl's table [V15] |
| 20 | Key diameters. Aorta 25–32 → 15–20 mm infrarenal. CCA 6–8, ICA 5, ECA 4, vertebral 3.5, subclavian 8.5, brachial 4, radial 2.5, CFA 8.5, SFA 6, popliteal 5.5, superficial temporal/facial/occipital ~2. IJV 10–20, SVC 20, IVC 21, CFV 12 | — | [K-H R43–R49] | **Partly corrected:** ICA 4.8 (was 5), CFA M 9.0 / F 8.2 (was 8.5), IVC 17 (13–21; was 21), subclavian vein 7–12 (was 10–13). ✓ verified: aorta segments, CCA, brachial, common iliac, IJV, SVC, CFV [V7b, V17, V18, V1c]. ECA, vertebral, subclavian artery, radial, SFA, popliteal and scalp/face arteries unverified |

---

## 14. Suspicious content

None encountered. **No web content was retrieved in this session:** the search budget was exhausted before this agent ran, and the egress proxy blocked every fetch. There were therefore no pages, snippets or code that could carry injected instructions. No commands were run. Nothing was downloaded, installed or executed.

**Fact-check pass (v1.1):** this pass did read web content: GitHub pages, raw GitHub files and GitHub code-search results. All of it was treated as data. **No text in any of it tried to give instructions** (no requests to run commands, install software, visit URLs, change files or ignore instructions). One incidental observation: several GitHub-hosted "medical" files appear to be AI-generated study notes. They were used only as low-weight corroboration and never as a sole source. No commands were run. Nothing was downloaded, installed or executed. No code was copied into the project.

---

## 15. References (verification list — none were opened this session)

The URLs are from memory and were not opened. Verify them before relying on them.

- **R1** American College of Surgeons Committee on Trauma. *Advanced Trauma Life Support (ATLS) Student Course Manual*, 10th ed. Chicago: ACS; 2018. (Shock classes, haemothorax, fracture blood loss, scalp bleeding, vascular hard signs.)
- **R2** Nadler SB, Hidalgo JU, Bloch T. Prediction of blood volume in normal human adults. *Surgery* 1962;51(2):224–232.
- **R3** ICRP Publication 89. Basic anatomical and physiological data for use in radiological protection: reference values. *Ann ICRP* 2002;32(3–4).
- **R4** Hall JE, Hall ME. *Guyton and Hall Textbook of Medical Physiology*, 14th ed. Elsevier; 2021. (Volume distribution, pressures, organ flows, compensation.)
- **R5** Rothe CF. Mean circulatory filling pressure: its meaning and measurement. *J Appl Physiol* 1993;74(2):499–509.
- **R6** Baskurt OK, Meiselman HJ. Blood rheology and hemodynamics. *Semin Thromb Hemost* 2003;29(5):435–450.
- **R7** Hrnčíř E, Rosina J. Surface tension of blood. *Physiol Res* 1997;46(4):319–321.
- **R8** Raymond MA, Smith ER, Liesegang J. The physical properties of blood — forensic considerations. *Sci Justice* 1996;36(3):153–160.
- **R9** Williams LR, Leggett RW. Reference values for resting blood flow to organs of man. *Clin Phys Physiol Meas* 1989;10(3):187–217.
- **R10** Hooper N, Armstrong TJ. Hemorrhagic Shock. *StatPearls*. NCBI Bookshelf NBK470382 (ID from memory): https://www.ncbi.nlm.nih.gov/books/NBK470382/
- **R11** Mutschler M, et al. A critical reappraisal of the ATLS classification of hypovolaemic shock: does it really reflect clinical reality? *Resuscitation* 2013;84(3):309–313.
- **R12** Guly HR, et al. Testing the validity of the ATLS classification of hypovolaemic shock. *Resuscitation* 2011;82(5):556–559.
- **R13** Mutschler M, et al. The Shock Index revisited — a fast guide to transfusion requirement? A retrospective analysis on 21,853 patients derived from the TraumaRegister DGU. *Crit Care* 2013;17(4):R172.
- **R14** Barcroft H, Edholm OG, McMichael J, Sharpey-Schafer EP. Posthaemorrhagic fainting: study by cardiac output and forearm flow. *Lancet* 1944;243(6294):489–491.
- **R15** Deakin CD, Low JL. Accuracy of the advanced trauma life support guidelines for predicting systolic blood pressure using carotid, femoral, and radial pulses: observational study. *BMJ* 2000;321:673–674.
- **R16** Astrup J, Siesjö BK, Symon L. Thresholds in cerebral ischemia — the ischemic penumbra. *Stroke* 1981;12(6):723–725.
- **R17** Rossen R, Kabat H, Anderson JP. Acute arrest of cerebral circulation in man. *Arch Neurol Psychiatry* 1943;50(5):510–528.
- **R18** DiMaio VJ, DiMaio D. *Forensic Pathology*, 2nd ed. CRC Press; 2001. Also Saukko P, Knight B. *Knight's Forensic Pathology*, 4th ed. CRC Press; 2016. (Time to incapacitation, vital reaction, post-mortem clots, heart wounds, eyes after death.)
- **R19** Paradis NA, et al. Coronary perfusion pressure and the return of spontaneous circulation in human cardiopulmonary resuscitation. *JAMA* 1990;263(8):1106–1113.
- **R20** Clark JJ, et al. Incidence of agonal respirations in sudden cardiac arrest. *Ann Emerg Med* 1992;21(12):1464–1467.
- **R21** Lempert T, Bauer M, Schmidt D. Syncope: a videometric analysis of 56 episodes of transient cerebral hypoxia. *Ann Neurol* 1994;36(2):233–237.
- **R22** Massive-haemorrhage definitions as used in transfusion and trauma guidelines, e.g. the European guideline on management of major bleeding and coagulopathy following trauma (Spahn DR, Rossaint R, et al., *Crit Care*, serial editions 2007–2023).
- **R23** Sondeen JL, Coppes VG, Holcomb JB. Blood pressure at which rebleeding occurs after resuscitation in swine with aortic injury. *J Trauma* 2003;54(5 Suppl):S110–S117.
- **R24** Eastridge BJ, et al. Death on the battlefield (2001–2011): implications for the future of combat casualty care. *J Trauma Acute Care Surg* 2012;73(6 Suppl 5):S431–S437.
- **R25** Karger B, Niemeyer J, Brinkmann B. Physical activity following fatal injury from sharp pointed weapons. *Int J Legal Med* 1999;112(3):188–191.
- **R26** Parmley LF, Mattingly TW, Manion WC, Jahnke EJ. Nonpenetrating traumatic injury of the aorta. *Circulation* 1958;17(6):1086–1101.
- **R27** Stashko E, Meer JM. Cardiac Tamponade. *StatPearls*. NCBI Bookshelf NBK431090 (ID from memory).
- **R28** Attinger D, Moore C, Donaldson A, Jafari A, Stone HA. Fluid dynamics topics in bloodstain pattern analysis: comparative review and research opportunities. *Forensic Sci Int* 2013;231(1–3):375–396.
- **R29** Bevel T, Gardner RM. *Bloodstain Pattern Analysis*, 3rd ed. CRC Press; 2008. Also James SH, Kish PE, Sutton TP. *Principles of Bloodstain Pattern Analysis*. CRC Press; 2005.
- **R30** Scalp anatomy: Standring S (ed.). *Gray's Anatomy*, 42nd ed. Elsevier; 2020, chapter on the scalp.
- **R31** Brohi K, Singh J, Heron M, Coats T. Acute traumatic coagulopathy. *J Trauma* 2003;54(6):1127–1130.
- **R32** Electrosurgical and vessel-sealing capability: surgical-energy reviews and device labelling (bipolar vessel sealing cleared for vessels ≤ 7 mm).
- **R33** Spodick DH. Acute cardiac tamponade. *N Engl J Med* 2003;349(7):684–690.
- **R34** Hemothorax. *StatPearls*. NCBI Bookshelf (entry ID not verified).
- **R35** Branney SW, et al. Quantitative sensitivity of ultrasound in detecting free intraperitoneal fluid. *J Trauma* 1995;39(2):375–380.
- **R36** Langlois NEI, Gresham GA. The ageing of bruises: a review and study of the colour changes with time. *Forensic Sci Int* 1991;50(2):227–238.
- **R37** Prahl S. Optical absorption of hemoglobin. Oregon Medical Laser Center; 1999. https://omlc.org/spectra/hemoglobin/
- **R38** Hulse-Smith L, Mehdizadeh NZ, Chandra S. Deducing drop size and impact velocity from circular bloodstains. *J Forensic Sci* 2005;50(1):54–63.
- **R39** Laan N, de Bruin KG, Bartolo D, Josserand C, Bonn D. Maximum diameter of impacting liquid droplets. *Phys Rev Applied* 2014;2:044018.
- **R40** Huppert HE. The propagation of two-dimensional and axisymmetric viscous gravity currents over a rigid horizontal surface. *J Fluid Mech* 1982;121:43–58.
- **R41** Brutin D, Sobac B, Loquet B, Sampol J. Pattern formation in drying drops of blood. *J Fluid Mech* 2011;667:85–95.
- **R42** Bremmer RH, de Bruin KG, van Gemert MJC, van Leeuwen TG, Aalders MCG. Forensic quest for age determination of bloodstains. *Forensic Sci Int* 2012;216(1–3):1–11. Also Bremmer RH et al. Age estimation of blood stains by hemoglobin derivative determination using reflectance spectroscopy. *Forensic Sci Int* 2011;206:166–171.
- **R43** Moore KL, Dalley AF, Agur AMR. *Clinically Oriented Anatomy*, 8th ed. Wolters Kluwer; 2018. Also *Gray's Anatomy* 42nd ed. (Courses, landmarks, surface projections.)
- **R44** Radiopaedia and Kenhub/TeachMeAnatomy vessel articles (normal calibres). Blocked this session.
- **R45** Dodge JT Jr, Brown BG, Bolson EL, Dodge HT. Lumen diameter of normal human coronary arteries. *Circulation* 1992;86(1):232–246.
- **R46** Krejza J, et al. Carotid artery diameter in men and women and the relation to body and neck size. *Stroke* 2006;37(4):1103–1105.
- **R47** Sandgren T, Sonesson B, Ahlgren AR, Länne T. The diameter of the common femoral artery in healthy human: influence of sex, age, and body size. *J Vasc Surg* 1999;29(3):503–510.
- **R48** Yoo BS, et al. Anatomical consideration of the radial artery for transradial coronary procedures: arterial diameter, branching anomaly and vessel tortuosity. *Int J Cardiol* 2005;101(3):421–427.
- **R49** Wolak A, et al. Aortic size assessment by noncontrast cardiac computed tomography: normal limits by age, gender, and body surface area. *JACC Cardiovasc Imaging* 2008;1(2):200–209.
- **R50** Flanagan JP, Gradisar IA, Gross RJ, Kelly TR. Air embolus — a lethal complication of subclavian venipuncture. *N Engl J Med* 1969;281(9):488–489.

### 15.1 Sources actually read during the fact-check (v1.1)

Every source below was opened and read during the fact-check. Several are **third-party copies hosted on GitHub**, the only reachable host (see 16.1). When you cite them, cite the original book or paper, and check the number against the published edition before it goes into a player-visible readout.

- **V1** Marino PL. *The ICU Book*, chapter "Hemorrhagic shock" (chapter 15 in the copy read; edition not stated in the copy). Read via an unofficial text copy: github.com/StarleyBy/Starley-CS-Library, path `books/icu/marino/chapters/chapter-15/chapter-15.md`. Used for: blood volume 66 mL/kg (M, lean weight) and 60 mL/kg (F); classes in % and mL/kg; "as little as 30 % … can be fatal"; refill up to ~1 L; Hb/Hct fall not apparent for 8–12 h. Chapter 13 of the same copy defines massive blood loss as "loss equivalent to the blood volume within 24 hours".
- **V1b** Same book and copy, chapter 11 (`…/chapter-11/chapter-11.md`). Human mean systemic filling pressure 14–20 mmHg (ICU patients); veins hold 75 % of the blood volume.
- **V1c** Same book and copy, chapter 2 on central venous access (`…/chapter-02/chapter-02.md`). Air entrainment of 100 mL/s through a 14 G catheter at a 5 mmHg gradient; fatal at 200–300 mL (3–5 mL/kg) over a few seconds; subclavian vein 7–12 mm and 3–4 cm long, ~5 mm above the apical pleura; IJV diameter +20–25 % with a 15° head-down tilt; femoral vein medial to the artery at 2–4 cm depth, cross-section +50 % with a 15° head-up tilt.
- **V2** "Relative bradycardia in patients with isolated penetrating abdominal trauma and isolated extremity trauma." *Ann Emerg Med* 1990;19(3):268–75 (MEDLINE UI 90178769). Abstract read in the OHSUMED MEDLINE corpus copy at github.com/el-san59/Course_Work, `data/ohsu/ohsu741.json`.
- **V3** Blood-injury phobia review abstract, MEDLINE UI 88338785 (1988). Same corpus, `data/ohsu/ohsu392.json`. Blood/injury cues cause an initial HR rise, then vasovagal bradycardia and frequently syncope.
- **V4** "Survival time in gunshot and stab wound victims." *Am J Forensic Med Pathol* 1988;9(3):215–7 (UI 89023037). Same corpus, `ohsu607.json`. The abstract has no per-vessel numbers.
- **V4b** "Traumatic rupture of the aorta: still a lethal injury." *Am J Surg* 1986;152(6):660–3 (UI 87073973). Same corpus, `ohsu9.json`. Overall mortality 84 %.
- **V4c** Template bleeding-time abstract (UI 87155842). Same corpus, `ohsu41.json`. No normal range stated.
- **V5** "Bunegin-Albin catheter improves air retrieval and resuscitation from lethal venous air embolism in dogs." *Anesth Analg* 1987;66(10):991–4 (UI 87324205); and the upright-dog study, *Anesth Analg* 1989;68(3):298–301. Same corpus, `ohsu105.json` and `ohsu541.json`. A "lethal dose" of air of 5 mL/kg over 30 s.
- **V6** Sugarbaker DJ et al. *Adult Chest Surgery*, 2nd ed., chapter on thoracic trauma (chapter 6 in the copy; StarleyBy repo `books/thoracic-surgery/Sugarbaker2/chapters/chapter-06/chapter-06.md`). Thoracotomy for > 1,500 mL initial drainage or > ⅓ of blood volume, or > 250 mL/h for a few hours; most lung injuries are self-limiting.
- **V7** Cohn LH (ed.). *Cardiac Surgery in the Adult*, chapter 57 on pericardial disease (StarleyBy repo `books/cardiac-surgery/cohn/chapters/chapter-57/chapter-57.md`). Rapid accumulation of as little as 100 mL can cause critical tamponade; chronic effusions can exceed 1 L; low-pressure tamponade in hypovolaemia; Beck's triad.
- **V7b** Same book, chapter 49 on aortic aneurysm (`…/chapter-49/chapter-49.md`). Framingham CT mean diameters: descending thoracic 25.8 mm (M) / 23.1 mm (F); infrarenal 19.3 / 16.7 mm; lower abdominal 18.7 / 16.0 mm; men 2–3 mm larger; aneurysm ≥ 1.5 × normal.
- **V8** *Oxford Handbook of Critical Care*, cardiac tamponade section (StarleyBy repo `books/icu/oxford/chapters/chapter-06/chapter-06.md`). "Rapid accumulations of < 150 mL".
- **V9** BioGears Engine documentation, `PatientMethodology.md`: https://raw.githubusercontent.com/BioGearsEngine/core/master/share/doc/methodology/PatientMethodology.md. BV = 65.6·W^1.02 mL, citing Morgan et al. 2006.
- **V10** Nadler-formula implementations with identical coefficients: github.com/filip-jezek/FMIComparison `FMITest.mo` (comment cites "Nadler et al. Surgery 51:224, 1962"); github.com/jackwasey/physiology `R/bmi.R`; github.com/beards-lab/TriSeg-Digital-Twins `targetVals_HF.m`.
- **V11** Secondary ATLS teaching tables (low weight; probably AI-assisted notes): github.com/Open-Medica/open-medical-skills `skills/trauma-management-protocols/skill.py`; github.com/GOATnote-Inc/openem-corpus `corpus/tier1/conditions/hemorrhagic-shock.md`.
- **V12** Citation confirmations: openEHR GDL guideline github.com/gdl-lang/common-clinical-models `gdl2/Shock_Index.v1.gdl2.json` (cites Mutschler *Crit Care* 2013;17(4):R172; normal SI 0.5–0.7; > 0.8 is early shock). Published reference lists that give Mutschler *Resuscitation* 2013;84:309–13.
- **V13** Lee-White whole-blood clotting time 5–15 min, from teaching notes (low weight): github.com/tapendrashahi/magic-doc `normal.txt`; github.com/Sakilanwar9531/Nursingmock `src/blood_data.ts`.
- **V14** University of Arizona General Surgery residency handbook, `docs/Trauma/ATLS/Primary Survey.md` (github.com/bilalmirza96/University-of-Arizona-General-Suregry-Handbook). Massive haemothorax > 1,500 mL or > 200 mL/h × 4 h.
- **V15** Prahl S. *Tabulated molar extinction coefficient for hemoglobin in water* (OMLC, 1999; data by Gratzer and Kollias). Copy read at https://raw.githubusercontent.com/TimHarries/torusdata/master/prahl1999.dat. Identical rows appear in github.com/Nirstorm/nirstorm `bst_plugin/forward/nst_get_hb_extinctions.m`.
- **V16** Wikipedia, "Bloodstain pattern analysis" (text snapshot at github.com/ajb2969/MLInformationRetrieval `documents/6-1285.txt`). The oxyHb → metHb → hemichrome ageing chemistry, citing Bremmer RH et al., *PLoS One* 2011;6(7):e21845; and "the width-length ratio of the ellipse is the sine of the impact angle".
- **V17** HuBMAP Human Reference Atlas, vasculature table HRA-VCCF, `Geometry.csv`: https://raw.githubusercontent.com/hubmapconsortium/hra-vccf/main/Geometry.csv (curated vessel dimensions, each with its primary citation). Rows used: Krejza 2006 *Stroke* 37:1103 (CCA, ICA); Sandgren 1999 *J Vasc Surg* 29:503 (CFA); Tartière 2009 (IJV, CT); Pedersen 1993 (abdominal aorta, ultrasound); Qiu 2020 (arch and descending aorta, CT); Eliathamby 2021 (ascending aorta, CT); Panagouli 2020 and Kumar 2016 (brachiocephalic); Ba 2019 (CFA length, femoral vein, cadaveric); plus brachial, common iliac, SVC, IVC and portal-vein rows.
- **V18** *Hurst's The Heart*, chapter on aortic disease (StarleyBy repo `books/cardiology/Hurst/chapters/chapter-14/chapter-14-01.md`). Ascending aorta ~3 cm; descending 2–2.3 cm; abdominal 1.7–1.9 cm; abdominal aneurysm > 3 cm; aortic pressure-wave velocity ~5 m/s.

---

## 16. Fact-check (v1.1)

### 16.1 Method and limits

- **The checker's WebSearch budget was already exhausted** ("200 of 200"), so no web searches were possible.
- **Almost every medical domain was blocked** by the egress proxy: NCBI/PMC/PubMed, Europe PMC, Wikipedia, Radiopaedia, LITFL, MSD Manuals, OpenStax, Crossref, OpenAlex, Semantic Scholar, doi.org, arXiv, ScienceDirect, Hugging Face, CRAN, the Wayback Machine and OMLC.
- **github.com, raw.githubusercontent.com and pypi.org were reachable.** The checker therefore used GitHub code search (read-only) and fetched raw files. The usable sources found that way were:
  - a MEDLINE abstract corpus (OHSUMED, 1987–1991);
  - text copies of ICU, cardiac-surgery, thoracic-surgery and cardiology textbooks;
  - the HuBMAP vessel-geometry dataset;
  - Prahl's haemoglobin table;
  - open-source physiology engines (BioGears);
  - independent implementations of Nadler's formula.
- **Evidence weight:** textbooks, primary abstracts, HuBMAP and Prahl are *strong*. Residency handbooks are *moderate*. Unattributed teaching notes on GitHub are *weak*; they were used only for corroboration.
- **Items the checker could not reach:** the ATLS manual, the DiMaio/Knight forensic texts, Rossen 1943, Barcroft 1944, Paradis 1990, Lempert 1994, Eastridge 2012, Karger 1999, Gray's/Moore anatomy and the bloodstain-pattern-analysis textbooks. Claims that depend only on these remain **unverified**. They are not wrong, just unchecked.
- **Every [D] (derived) number in the claim list was recomputed by hand:** Nadler examples, orifice and Poiseuille tables, the radial and shunt worked examples, jet heights and throws, Rayleigh–Plateau drop size, Tate's law, pool areas, film-flow speeds, μa conversions, and the SI and MAP columns of table 3.3. No arithmetic errors were found.

### 16.2 Per-claim verdicts

| # | Claim | Verdict | What changed / evidence |
|---|---|---|---|
| 1 | Blood volume 70 mL/kg M (66–77), 60–65 F; BV0 5.0 / 3.8 L; Nadler | **Confirmed** | Marino 66 M / 60 F mL/kg [V1]; BioGears ≈ 71 mL/kg [V9]; Nadler coefficients and citation confirmed [V10]; worked examples recomputed (5.09 L, 3.77 L) |
| 2 | ATLS classes I–IV (HR, RR, SBP, PP, mental state) | **Confirmed** (secondary) | Marino % and mL/kg bands [V1]; teaching tables [V11]. Class III is written 31–40 % in Marino. The ATLS manual itself was not reached |
| 3 | HR response weaker than ATLS; SI ≥ 1.4 severe; 25–35 % biphasic faint | **Corrected** | Pulse < 100 in 35.2 % (SBP < 100) and 45.8 % (SBP < 90) of trauma patients [V2] → `vasovagal_chance` 0.35–0.45. Mutschler citations confirmed [V12]; SI cut-offs unverified |
| 4 | ≥ 40–50 % loss usually fatal; sim arrest rule | **Confirmed**, caveat added | Marino: > 40 % "may be irreversible", and "as little as 30 % … can be fatal" [V1]. Arrest thresholds are game rules [G]; Paradis not reached |
| 5 | LOC 5–10 s; 10–15 s after heart destroyed; 4–6 min brain | **Uncertain** | No source reachable. Consistent with standard teaching; left unchanged |
| 6 | Orifice/Poiseuille/cardiac-limit flow model | **Confirmed** (arithmetic) | All table values reproduced within ~1 %. Not validated against human wound-flow data (none found) |
| 7 | Per-vessel bleed-out times | **Uncertain** | No per-vessel source found [V4]. Internally consistent with Sections 3–4. Relabelled as tuning targets |
| 8 | Partial > complete laceration; elastic arteries do not stop | **Uncertain** | No source reachable. Standard teaching; unchanged |
| 9 | 0.78 mmHg/cm; sub-atmospheric neck/dural veins; 200–300 mL air lethal; ~100 mL/s | **Corrected** (nuance) | 200–300 mL (3–5 mL/kg) over seconds confirmed [V1c]; 5 mL/kg lethal in dogs [V5]. "~100 mL/s through a large opening" changed to "≥ 100 mL/s", because 100 mL/s passes even a 1.8 mm opening at 5 mmHg [V1c] |
| 10 | Jet height 12.8 mm/mmHg; 1.54 m ideal; 0.35–0.65× real | **Confirmed** (arithmetic) | Recomputed. Cv is a tuning value (no measured human jets found) |
| 11 | Bleeding time 2–7 min; clotting 5–15 min; serum 30–60 min; scalp septa | **Uncertain** (partly confirmed) | Lee-White 5–15 min confirmed by secondary sources [V13]. Ivy range, serum timing and scalp anatomy unverified |
| 12 | Tamponade 100–200 mL; Beck's triad | **Confirmed** | "As little as 100 mL" [V7]; "< 150 mL" [V8]. **Added:** low-pressure tamponade in hypovolaemia (neck veins may not distend) [V7] |
| 13 | Haemothorax 2.5–3 L/side; massive > 1,500 mL or > 200 mL/h × 2–4 h; fracture losses | **Uncertain** (thresholds confirmed) | Massive-haemothorax thresholds confirmed and widened (> ⅓ BV; 200–250 mL/h) [V6, V14]. Pleural capacity and fracture losses unverified |
| 14 | DeoxyHb 5–10× more red absorption; μa RGB | **Confirmed** | Extinction values match Prahl's table exactly [V15]; ratios 4.6× (600 nm) to 10.2× (650 nm) |
| 15 | Drop 50 µL, 4.6 mm, 7.6 m/s; stain 3–5× | **Corrected** | 4.6 mm correct. Terminal velocity 7.6 is the classic figure but unverified; a water-drop physics estimate gives ~9 → use 7.5–9 (8). Stain spread 3–5.5× (Laan correlation gives ~5.6 at terminal velocity). Impact-angle formula confirmed [V16] |
| 16 | Pool 2.5 mm; 500 mL = 50 cm, 1 L = 71 cm, 2 L = 1 m; gel 5–15 min | **Confirmed** (arithmetic) | l_c = 2.32 mm and all areas recomputed; gel time matches Lee-White [V13]. Caveat: real pools may be thinner (edge pinning) |
| 17 | Rivulets 2–5 mm, 1–5 cm/s, 5–15 µL/cm | **Confirmed** (arithmetic) | Nusselt film speed recomputed. Widths and residue are estimates; contact-line pinning may slow real rivulets |
| 18 | Drying times; red → brown → black colour ramp | **Uncertain** (chemistry confirmed) | OxyHb → metHb → hemichrome sequence confirmed [V16]. Timings unverified |
| 19 | Vessel diameters | **Corrected** (partly) | ICA 4.8 (was 5); CFA M 9.0 / F 8.2 (was 8.5); IVC 13–21 (17) (was 17–25 (21)); subclavian vein 7–12 (was 10–13); brachiocephalic length 3.5–4.5 cm (was 4–5). Confirmed: aorta segments, CCA, brachial, common iliac, IJV, SVC, CFV, portal vein [V1c, V7b, V17, V18]. Unverified: ECA, vertebral, subclavian and axillary arteries, radial, ulnar, SFA, popliteal, tibial, scalp and face arteries |

### 16.3 All edits made in this pass

- **Values changed:**
  - `msfp` 7 (5–15) → 10 (7–20) mmHg, with the human 14–20 mmHg data.
  - `vasovagal_chance` 0.25–0.35 → 0.35–0.45.
  - Air entry "~100 mL/s through a large opening" → "≥ 100 mL/s".
  - Subclavian vein 10–13 → 7–12 mm (Sections 5 and 11).
  - ICA 4.5–5.5 (5) → 4–5.5 (4.8).
  - CFA 7–10 (8.5) → 7.5–11 (M 9.0, F 8.2).
  - IVC 17–25 (21) → 13–21 (17) (Sections 5 and 11).
  - Brachiocephalic length 4–5 → 3.5–4.5 cm.
  - `drop_terminal_v` 7.6 → 8 (7.5–9) m/s.
  - `stain_spread_factor` 3–5 → 3–5.5×.
- **New parameters and notes (gaps filled):**
  - `refill_cap` ≈ 1 L, and the fact that Hb/Hct do not fall for 8–12 h [V1].
  - Class boundaries in mL/kg (< 10 / 10–20 / 21–30 / > 30) [V1].
  - Low-pressure tamponade and its effect on neck veins and `pericardium_tamponade_v` [V7].
  - Massive haemothorax also defined as > ⅓ BV [V6].
  - The sight of blood or a wound alone can cause vasovagal syncope [V3].
  - Posture changes vein size: IJV +20–25 % with a 15° head-down tilt; femoral vein +50 % cross-section with a 15° head-up tilt [V1c].
  - Subclavian vein ~5 mm above the pleura [V1c].
  - Sex differences in vessel size (men's aortas 2–3 mm larger) [V7b].
  - Blue-band caveat for the μa shader values.
  - Marino's point that ~30 % loss can already be fatal [V1].
- **Status marks:** "✓ verified" or "Fact-check: unverified" notes were added throughout, and Section 13 gained a Fact-check column.

### 16.4 Still to verify (priority order, for a human with library access)

1. The per-vessel bleed-out times in Section 5 (forensic series on incapacitation times, and Karger's work) — these drive gameplay pacing.
2. The Mutschler SI cut-offs (R13) and Barcroft's biphasic response (R14).
3. Time to LOC and to irreversible injury (Rossen, DiMaio). These are load-bearing for the "death animation" timing.
4. The fracture blood-loss table and pleural capacity (ATLS 10th ed.).
5. Diameters of the forearm, leg and scalp arteries (radial: Yoo 2005; vertebral; SFA; popliteal).
6. Bloodstain drying and colour timings (Bremmer; Brutin) and the drop terminal velocity (bloodstain-pattern-analysis primary literature).
