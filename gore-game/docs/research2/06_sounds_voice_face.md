# 06 (round 2) — Sounds, voice and face of injured and dying people: acoustics, synthesis recipes, FACS, palsy, colour

Project: gore simulator (Godot 4.5, Forward+, GDScript + Godot shaders, built-in Jolt, Skeleton3D + PhysicalBone3D ragdolls). Research round 2.
Purpose: input for the **AudioGen** (impacts, fluids, falls, breathing, voice) and **FaceGen** (expression, palsy, tone, skin colour, sweat, tears, pupils and lids) generators of the behaviour layer. The goal is sound and facial behaviour that a clinician, forensic pathologist or trauma medic would accept as real, and that can be synthesised or processed procedurally from the physiology state.
Audience: audio, facial-animation, shader and physiology engineers. Clinical, factual tone. The subject is a fictional, procedurally generated adult.

**Round-one and round-two material this document builds on (not repeated here):**

| File | Already covers | Cited as |
|---|---|---|
| `docs/research/01_gunshot_wounds.md` | Bullet data, skull fracture mechanics ("bone crack co-timed with the shot", §5), spatter and `spatter_sound_delay` (§7) | `[R1-01 §x]` |
| `docs/research/02_sharp_blunt_burn.md` | Stab "skin tick", skull "thud → crack → wet crunch" (§5), nasal crunch (§4), burn hiss/sizzle/pops (§6), neck-vein air entry (§2), skin palette (§7) | `[R1-02 §x]` |
| `docs/research/03_bleeding_vessels.md` | Blood-sound events (§6.4), drip rule `Q / 50 µL`, jet speeds and pulse waveform (§2.4, §6), pool thickness 2.5 mm and gelling at 5–15 min (§10) | `[R1-03 §x]` |
| `docs/research/04_neuro_death_eyes.md` | Haemorrhage colour progression of face, lips, conjunctiva and nail beds (§7.7); sucking chest wound threshold (§9); eyes when dying and dead (§11); post-mortem changes incl. passive "groan" (§12) | `[R1-04 §x]` |
| `docs/research/06_game_gore_tech.md` | Flow regime → VFX/audio table (§8.1), instance-uniform budget (≤ 16 per shader) | `[R1-06 §x]` |
| `docs/research2/01_brain_injury_deficits.md` | Vocal states and aphasia types (§5), central (lower-face) weakness (§2), eye signs (§14), GCS (§19) | `[R2-01 §x]` |
| `docs/research2/02_reactions_to_being_shot_and_hit.md` | Pain face core (PSPI) (§9.1), vocalisation types, scream roughness, F0 guide, "one scream per breath" (§9.2), winded (§6.5) | `[R2-02 §x]` |
| `docs/research2/03_falling_ragdoll_biomechanics.md` | Fall contact order, impact speeds, collapse energy ≈ 620 J, head 200–500 g at ~5 ms (§5–§6), impact-audio rule (§8.6) | `[R2-03 §x]` |
| `docs/research2/04_agonal_involuntary_movement.md` | **Physiology** of snoring, gasps, death rattle, gurgling, cough, vomiting, hiccup (§2); face/lid/jaw/tongue by state (§7); pallor, sweat, cyanosis threshold, mottling (§8) | `[R2-04 §x]` |

**What this document adds:**
- the acoustics of flesh, bone, skull, knife, fist and hammer impacts, with synthesis recipes (§1–§2);
- the physics of blood sounds, including why floor drips do not "plink" and why blood jets do not hiss (§3);
- body-fall sounds by body part and floor (§4);
- the acoustics of every breathing state, including stridor, gurgling, the sucking chest wound and the open airway in the neck (§5);
- a source–filter voice model, a quantitative vocalisation catalogue, and the rules that tie voice to pain, blood loss, breathing and consciousness (§6);
- speech after brain, jaw, lip, tongue, tooth, larynx, trachea and chest injury (§7);
- FACS recipes for pain, fear, terror, shock, daze, confusion, effort, air hunger, crying and nausea, and a FACS → blendshape mapping (§8);
- facial palsy: central vs peripheral, per-branch, per-AU (§9);
- colour ramps (hex) and timing for pallor, cyanosis, congestion and capillary refill, on light and dark skin (§10);
- sweat and skin sheen (§11); pupils, blinks, saccades and tears (§12);
- the loss of facial tone, the Hippocratic face and the "death mask" (§13);
- a Godot 4.5 implementation plan (§14) and a combined state table (§15).

---

## 0. Read this first

### 0.1 Method and limits (important)

- **No web page or search result could be read in this session.**
  - All three `WebSearch` calls were refused: the session's shared search budget (200 of 200 calls) had already been used by earlier research tasks.
  - One `WebFetch` attempt (pubmed.ncbi.nlm.nih.gov) returned `EGRESS_BLOCKED`, as the brief predicted. No further fetches were tried.
- **Consequences:**
  - `[S#]` values come only from sources that **sibling documents located by web search in earlier sessions** (URLs copied from those documents, §19.1). They were read then through search summaries and were not re-read here.
  - Most values are `[K]`: the author's knowledge of acoustics, phonetics, clinical medicine and forensic pathology. Where a specific paper is recalled it is tagged `[K; M#]` and listed in §19.2. **None of the `M#` items was opened in this session.**
  - Many acoustic values follow directly from physics (contact mechanics, bubble resonance, jet speed). They are tagged `[K]` with confidence (H) where the physics is textbook.
  - `[E]` values are engineering estimates for the game, with the reasoning shown.
- **Calibrated recordings of real injuries barely exist.** Nobody measures the sound pressure of a stabbing. The impact levels in §2–§4 are therefore `[E]` (L): derived from contact physics and forensic or clinical descriptions. **Before hard-coding any dB value, measure the game's own foley references** (meat, bone, gelatin, body-weight drops on the target floors) with a calibrated sound level meter at 1 m. The QA list is §18.
- Where sources or memory disagree, the range is given with a **game default** and the reason for choosing it.

### 0.2 Tags

| Tag | Meaning |
|---|---|
| `[S#]` | Sourced. URL in §19.1. Located by web search in a sibling session; read then through search summaries only |
| `[K]` | Author's own knowledge (acoustics, phonetics, medicine, forensic pathology). Not verified in this session |
| `[K; M#]` | Author's knowledge of a specific recalled paper, standard or book, listed in §19.2. Not opened in this session |
| `[E]` | Engineering estimate or game mapping. Reasoning given |
| `[R1-0x §y]` / `[R2-0x §y]` | Sibling document and section |
| (H) / (M) / (L) | Confidence that the real value lies in the stated range: high, medium, low |

### 0.3 Conventions

- **Audio units.**
  - Levels are **dB SPL at 1 m from the source**, free field, **unweighted peak** for impacts and **dBA (slow)** for breathing and voice, unless stated.
  - Distance: −6 dB per doubling of distance in the free field `[K] (H)`.
  - Sample rate 48 kHz, 32-bit float internally.
  - Time constants: `τ` is the 1/e amplitude decay time; `T60 = 6.91 τ` `[K] (H)`. Damping ratio `ζ` gives `τ = 1 / (2π f ζ)` `[K] (H)`.
  - Filters: `BP(fc, Q)` band-pass, `LP(fc, n)` / `HP(fc, n)` low/high-pass with slope `n` dB/octave, `Q = fc / bandwidth`.
- **Engine loudness mapping** `[E]`: author every one-shot peak-normalised, then set `volume_db = SPL_1m − 100` (a 100 dB SPL source plays at 0 dB). A master limiter and a "realism dynamic range" setting (§14.1) compress the real 30–165 dB span into something a player can listen to.
- **Colour**: sRGB hex, D65, light-to-medium skin baseline as in `[R1-04 §7.7]` (lips `#B35E62`, nail beds `#E2A9A6`, palpebral conjunctiva `#D98C87`). For dark skin, apply the same change to lips, gums, tongue, conjunctivae, nail beds and palms, and use a grey ("ashen") overlay on skin (§10.4).
- **FACS intensity** (A–E) → blendshape weight `[E]`: A 0.10, B 0.30, C 0.50, D 0.75, E 0.95.
- **Time origins** as `[R2-04 §0.3]`: `t_inj`, `t_LOC`, `t_apn`, `t_arr`, `t_dead`.
- **Reference body** as `[R2-04 §0.3]` (male, 75 kg, 1.75 m). **Per-character voice**: speaking F0 male 85–155 Hz (mean ~115), female 165–255 Hz (mean ~200); vocal-tract length male 16–18 cm, female 14–15 cm `[K] (H)`.

### 0.4 Where the generators sit

```
Physiology state (R1-04 §13)          DYING / REACTION LAYERS (R2-02, R2-04)
 pain, arousal, consciousness (GCS),   ──►  AudioGen ─┬─ ImpactSynth  (flesh, bone, skull, knife, fist, hammer, burn)
 RR, tidal volume, airway fluid,               │      ├─ FluidSynth   (drip, stream, spray patter, bubbling)
 airway narrowing, open chest/neck             │      ├─ FallSynth    (contacts from Jolt, floor material)
 wounds, SBP/MAP, blood loss %, SpO2,          │      ├─ BreathSynth  (flow-driven noise + adventitious layers)
 Hb, core temperature, facial nerve            │      └─ VoiceSynth   (glottal source + formants, or processed samples)
 and jaw/tongue/lip/larynx damage              └──► FaceGen ─┬─ AU mixer (expressions, pain, fear, effort ...)
                                                             ├─ palsy mask (per side, per branch)
                                                             ├─ tone / gravity sag layer
                                                             ├─ skin colour, sweat, capillary refill (shader uniforms)
                                                             └─ eyes: pupils, blinks, saccades, tears
```

- The generators never decide physiology. They read it and produce sound and face.
- Every sound and face generator is gated by the tissue it needs, exactly as in `[R2-04 §1]`: no voice without airflow through the larynx, no expression without a working facial nerve and brainstem, no sweating after `t_arr`.

### Simulation parameters (conventions)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `sample_rate` | 48,000 | Hz | Breath and rattle generators may run at 24,000 to halve cost | [E] |
| `spl_to_volume_db` | `SPL_1m − 100` | dB | Peak-normalised assets | [E] |
| `distance_law` | −6 | dB per doubling | Free field; rooms add reverb | [K] (H) |
| `facs_weight` | A 0.10 / B 0.30 / C 0.50 / D 0.75 / E 0.95 | — | | [E] |
| `f0_speech_male` / `female` | 85–155 (115) / 165–255 (200) | Hz | Normal distribution per character, σ ≈ 15 % | [K] (H) |

### Visual/behavioural checklist (conventions)
- Every sound has a physical cause the player can see: a contact, a wound, a breath, a mouth shape.
- Loudness follows physiology: a bleeding-out victim gets quieter, not louder.
- The living face never stops moving slightly; the dead face never moves on its own.

---

## 1. Acoustic foundations and synthesis primitives

### 1.1 Contact duration sets the bandwidth

- An impact force pulse of duration `τc` (roughly a half-sine) has a spectrum that stays within 3 dB of its low-frequency value up to **~0.6/τc**, is about **−9.5 dB at 1/τc**, has its first spectral zero at **`1.5/τc`**, and has an envelope falling at 12 dB/octave above that `[K] (H)`. ✓ verified (arithmetic): the half-sine transform is `|F(f)| ∝ |cos(π f τc) / (1 − 4 f² τc²)|`; the apparent zero at `f τc = 0.5` cancels (value π/4, −2.1 dB), so the first true zero is at `f τc = 1.5`. **Corrected: was "a flat spectrum up to about 1/τc"** (at 1/τc the level is already ~10 dB down).
- **Soft contacts are long, so they sound low and dull. Hard contacts are short, so they sound bright and "cracky".** This single rule explains why a punch thuds and a hammer on a shin cracks.
- Contact duration of a mass `m` on an effective stiffness `k`: `τc = π √(m / k)` `[K] (H)`. ✓ verified [K] (H): half the natural period of a linear mass–spring contact against a rigid surface. For two moving bodies use the reduced mass `m₁m₂/(m₁+m₂)`; a Hertzian (non-linear) contact gives a similar order of magnitude with a weak speed dependence (`τc ∝ v^−1/5`).

| Contact | Effective mass | Typical `τc` | Force-spectrum first zero (1.5/τc) | What is heard | Tag |
|---|---|---|---|---|---|
| Fist to face (Olympic-boxer data: **gloved** straight punches to a Hybrid III dummy face; effective mass 2.9 ± 2.0 kg, fist 9.14 ± 2.06 m/s, peak force 3,427 ± 811 N) | 2.9 kg | **~12 ms** gloved (from `τc = π·p / (2·F)` with p = 26.5 kg·m/s); **bare knuckle ~5–10 ms** `[E]` | ~125 Hz gloved; ~150–300 Hz bare | A dull thud; the audible "smack" comes from skin slap and air, not from the force pulse | [S14] numbers, [E] derivation. ✓ verified (arithmetic): π × 26.5 / (2 × 3,427) = 12.1 ms; the same cross-check is in `[R2-02 §1.3]`. **Corrected: was labelled "Bare fist"**: Walilko's boxers punched in competition gloves `[K] (M)`, which lengthen contact; a bare fist on the face is shorter and brighter, but still a thud |
| Head (occiput) on concrete, 5 m/s | 4.5 kg | 2–8 ms (5 ms default) | 190–750 Hz | A "knock" or "crack" with a skull resonance near 1 kHz | `[R2-03 §6]` [E] |
| Steel hammer on scalp over skull | 0.5–0.7 kg head | 1–3 ms | 0.5–1.5 kHz, plus skull modes | Hard "tock"; crack on fracture | [E] (L–M) |
| Steel on bone under thin skin (shin, knuckle, teeth) | — | 0.2–1 ms | 1.5–7.5 kHz | Sharp "click/crack" | [E] (L–M). ⚠ Plausible but narrow: 0.2–0.5 ms needs bare bone or enamel (teeth, exposed bone); with 2–5 mm of skin and periosteum over the shin or knuckle a 0.5 kg hammer head sees `k` ≈ 10⁶–10⁷ N/m, i.e. **~0.7–2 ms** (first zero ~0.75–2 kHz) `[E]`. Use 0.2–0.5 ms for teeth/exposed bone, 0.7–2 ms through skin |
| Hip or trunk on floor | 15–40 kg | 20–80 ms | 20–75 Hz | Heavy "thump", more felt than heard; clothing and air make the audible part | [K; M21] (M), [E] |
| Knuckle-to-skin sliding or palm slap | — | < 1–3 ms (air squeezed out between surfaces) | > 1 kHz | "Slap" | [K] (M) |

Worked stiffness values for the `τc` formula `[E]`: head–concrete `k ≈ 1.8 × 10⁶ N/m` (gives 5 ms and ~320 g at 5 m/s, consistent with `[R2-03 §6.2]`); trunk–concrete `k ≈ 1.2 × 10⁵ N/m` (50 ms for 30 kg). ✓ verified (arithmetic): π√(4.5/1.8 × 10⁶) = 4.97 ms; peak force v√(mk) = 14.2 kN → 322 g; π√(30/1.2 × 10⁵) = 49.7 ms.

### 1.2 What rings and what does not

- **Soft tissue does not ring.** Skin, fat and muscle are highly damped viscoelastic materials. Flesh impacts have no audible resonance; their "wet" character comes from fluid films breaking, air pockets collapsing and skin slapping `[K] (H)`. ✓ verified [K] (H). The only "tonal" body responses are the air-filled cavities heard in clinical percussion (lung, stomach, below), which are cavity resonances, not tissue resonances.
- **Bone rings briefly.** Cortical bone is stiff and low-loss, but in the body it is wrapped in soft tissue. The intact living skull has resonances from about **0.8–1.5 kHz upward**, with damping ratios of a few per cent to ~10 % `[K; M1] (M)`. ✓ consistent with the checker's recall of Håkansson et al. 1994 (first in-vivo resonance near ~1 kHz, several further modes up to several kHz) `[K]` (M); the paper was not re-opened. Long bones have lowest bending modes of a few hundred Hz in vivo `[K; M33] (L)`. With f = 0.8–1.5 kHz and ζ = 0.03–0.10, `τ = 1/(2π f ζ)` ≈ **1–7 ms** and **T60 ≈ 7–45 ms**, so the audible ring is roughly **10–40 ms** and is usually masked by the thud after ~20 ms. **Corrected: was "The ring therefore lasts only 3–20 ms"**, which matched neither τ nor T60 of the stated parameters (arithmetic).
- **Hard floors and objects ring.** Tile laid over voids, wooden floors, metal grates, dropped weapons and keys ring for tens to hundreds of ms and are often the loudest part of a fall `[K] (H)`.
- **Clinical percussion is a good analogy for body regions** `[K] (H)`: over air-filled lung the note is **resonant** (lower, longer); over gas-filled stomach it is **tympanic** (drum-like); over liver, thigh and heart it is **dull** (short, damped); over a chest full of blood (haemothorax) it is **stony dull**. Use the same three characters for blows and bullet strikes to thorax, stomach and solid regions.

### 1.3 Level references

| Source | Level at 1 m | Tag |
|---|---|---|
| Quiet nasal breathing | 15–25 dBA | [E] (M) |
| Normal speech / raised / loud / shouted | **62 / 68 / 75 / 82 dB SPL** (average speech levels) | [K; M2] (H). ✓ verified [K] (H): ANSI S3.5-1997 overall levels 62.35 / 68.34 / 74.85 / 82.30 dB SPL at 1 m in front of the talker |
| Maximal adult scream | 90–105 dB SPL (default 98) | [K] (L–M), [E]. ⚠ Plausible: maximal voice levels are usually measured at 30 cm (typically ~100–115 dB there, i.e. ~90–105 dB at 1 m after −10.5 dB); exceptional screamers exceed 110 dB at 1 m. Keep 98 as the default and allow up to 110 for rare characters |
| Handgun muzzle blast (unsuppressed, at the shooter) | 150–165 dB peak | [K; M32] (M) |
| Suppressed handgun or rifle | still ~125–140 dB peak | [K; M32] (L–M) |

- The **gunshot report is 60–90 dB louder than a bullet striking flesh.** Near the gun the impact is masked. It becomes audible when the impact is far enough away that its sound arrives clearly **after** the report (§2.2), or when the listener is near the target and far from the gun `[K] (M)`. ⚠ Plausible, not verified: compared at the same 1 m distance, the levels in this table and §2.2 (150–165 vs 75–95 dB) give **55–90 dB**; at the shooter, with the target 20 m away (−26 dB for the impact), the gap is **~80–115 dB**. The impact level itself is `[E]` (L), so this difference is only as good as that estimate.
- **Gap added (the shooter's own hearing)** `[K] (M)`: an unprotected indoor shot (150–165 dB peak) is followed by a temporary threshold shift (muffled hearing, especially above 2 kHz) and tinnitus lasting seconds to hours; the middle-ear reflex is too slow to protect against a single gunshot. Many people in shootings also report sounds as muted or absent ("auditory exclusion") because of attention under stress. An optional "realistic hearing" setting `[E]`: after an unsuppressed indoor shot near the listener, `LP` 2–4 kHz and −10 to −20 dB on all other sounds for 2–10 s, recovering over 10–60 s, plus a faint 4–8 kHz tone.
- Air absorption at 20 °C, 50 % RH is ~0.03 dB/m at 4 kHz and ~0.1 dB/m at 8 kHz `[K] (M)`, so it hardly matters below ~30 m.

### 1.4 Synthesis primitives used by every recipe

All written for this document `[E]`; none is copied from any source.

| Primitive | Definition |
|---|---|
| `NOISE(c)` | White, pink or brown noise |
| `ENV(A, H, τ)` | Linear attack `A`, hold `H`, exponential decay with time constant `τ` |
| `MODE(f, ζ, a)` | Exponentially decaying sine: amplitude `a·e^(−t/τ)`, `τ = 1/(2π f ζ)`; random start phase |
| `MODAL(bank)` | Sum of 2–8 `MODE`s excited by the same impulse or short noise burst |
| `GRAIN(d, spec)` | One windowed noise or sine burst of duration `d` (0.2–5 ms) with spectrum `spec` |
| `CLOUD(λ, grain, T)` | Poisson process of grains, rate `λ` per second, lasting `T`; each grain randomised ±30 % in level and ±20 % in centre frequency |
| `BUBBLE(a, τ, σ)` | Sine at the Minnaert frequency `f0 = 3.2 / a` (a = bubble radius in m; see §3.1), amplitude `e^(−t/τ)`, frequency rising by fraction `σ` over the ring |
| `GLOTTAL(F0(t), OQ, tilt)` | Glottal flow pulse train (Rosenberg or LF shape `[K; M24]`), open quotient `OQ`, spectral tilt |
| `FORMANTS(F1..F5, B1..B5)` | Cascade or parallel two-pole resonators `[K; M35]` |
| `AM(r, d)` | Amplitude modulation at rate `r` Hz, depth `d` |
| `PITCHDROP(ratio, T)` | Exponential glide of a mode frequency to `ratio × f` over `T` |
| `FLOW(t)` | Breath flow curve in L/s (§5) |

### Simulation parameters (acoustic foundations)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `contact_tau` | `π √(m/k)` | s | Per body part and surface (§4) | [K] (H) |
| `impact_band_limit` | `LP` at ~`0.6/τc` (−3 dB), 12 dB/oct, or a half-sine force pulse filtered directly | Hz | Applied to the "force" layer of every impact. **Corrected: was `LP` at `1.5/τc`** (that is the first spectral zero; a corner there leaves the band around 1/τc ~9 dB brighter than the real pulse; the −3 dB corner of a half-sine is ~0.6/τc) | [K] (H) ✓ verified (arithmetic) |
| `skull_mode1` / `zeta` | 0.8–1.5 kHz (default 1.0) / 0.03–0.10 (default 0.06) | Hz / — | Intact, living. At the defaults τ = 2.7 ms, T60 = 18 ms | [K; M1] (M) ✓ consistent with recall, not re-opened |
| `long_bone_mode1` | 200–1,000 | Hz | Tibia/femur lower; ribs, clavicle, facial bones higher (1–4 kHz) | [K; M33] (L), [E] |
| `soft_tissue_ring` | none | — | No resonant modes on flesh layers | [K] (H) |
| `muzzle_vs_impact` | 60–90 (55–90 at equal distance) | dB | Duck nothing; rely on arrival-time separation (§2.2) | [K] (M) ⚠ depends on the `[E]` (L) impact level |

### Visual/behavioural checklist (acoustic foundations)
- Fist, knee and body falls: dull, low, short. Only bone, teeth and hard floors add "crack" and "click".
- A blow to the chest sounds hollower than the same blow to the thigh; a blow to a blood-filled chest sounds dead.
- Nothing fleshy rings.

---

## 2. Impacts on flesh and bone

### 2.1 Real versus film

- **Real blows are quieter, shorter and duller than film foley** `[K] (H)`. Film and game punches are built from layered leather slaps, vegetable snaps (celery, cabbage, lettuce), raw meat and whooshes, then compressed and mixed loud. Real bare-knuckle blows mostly produce a thud, a small skin slap, a grunt and the sound of the victim's feet and clothing.
- **"Crack" only happens when something hard is struck or breaks**: bone under thin skin, teeth, the skull, a fracture `[K] (H)`.
- The user wants 1:1 realism, so the default is physical. Provide `impact_stylisation` (0 = physical, 1 = film-style layering) for players who want the convention `[E]`.

### 2.2 Gunshot impact on the body

**Arrival time of the impact sound at the shooter** `[K] (H)` (physics; speed of sound `c = 343 m/s` at 20 °C): `t = d / v_bullet + d / c`. ✓ verified (arithmetic): all eight cells below were recomputed (e.g. 20 m handgun: 57.1 + 58.3 = 115 ms). The table ignores bullet deceleration, which adds a few per cent for rifles at 100 m.

| Distance | Handgun (≈ 350 m/s) | Rifle (≈ 850 m/s mean) |
|---|---|---|
| 5 m | 29 ms | 20 ms |
| 20 m | 115 ms | 82 ms |
| 50 m | 289 ms | 205 ms |
| 100 m | 577 ms | 409 ms |

- From ~20 m on, the impact arrives as a **separate, delayed "whop" or "thwack"** after the report. Hunters commonly report hearing this "bullet strike" on large game at 100–300 m, and describe it as a hollow thump on the body and a sharper crack on bone `[K] (L)` (hunting lore; plausible physics).
- A listener standing near the victim hears the impact **first** and the report `d / c` later (plus the supersonic crack of a rifle bullet passing, if it misses).

**Components of the impact sound** (torso, handgun unless stated) `[E]` on the mechanisms `[K]`:

| Component | Cause | Onset | Duration | Band | Relative level | Tag |
|---|---|---|---|---|---|---|
| Cloth snap | Fabric tensioned and perforated | 0 | 1–3 ms | 2–10 kHz | −10 dB | [E] |
| **Slap / "thwack"** | Body wall displaced abruptly; skin surface wave | 0–1 ms | 3–10 ms | 150 Hz – 2 kHz, peak 300–800 Hz | 0 dB (reference; ≈ 75–95 dB peak at 1 m) | [E] (L) |
| **Cavity "whump"** | Temporary cavity expands and pulsates; lifetime 5–10 ms, 2–4 pulsations; large for rifles, small for handguns | 1–15 ms | 5–15 ms | 100–500 Hz | Handgun −10 dB; rifle 0 to +6 dB | [K; M22] (M) mechanism, [E] sound |
| Bone strike | Rib, spine, pelvis, long bone | 0–1 ms (co-timed with the shot `[R1-01 §5]`) | click 1–3 ms + ring 3–15 ms | 1–8 kHz + modes | +6 to +10 dB | [R1-01] [E] |
| Wet grains | Fluid films and air pockets disrupted | 0–40 ms | 15–40 ms | 1–4 kHz grains | −15 dB | [E] |
| Exit spray patter | Droplets and fragments landing 0.5–3 m away | 30–300 ms `[R1-01 §7]` | 10–200 ms | 2–8 kHz ticks | −20 to −30 dB | [R1-01] [E] |
| Victim's startle grunt or gasp (**optional**) | Startle or pain, **not** chest compression: a 9 mm bullet carries ~2.9 N·s, which moves a 75 kg body ~0.04 m/s `[R2-02 §1.3]` and cannot squeeze air out of the chest | 60–150 ms (startle SCM 62 ms `[R2-02 §1]`) | 100–300 ms | Voice (§6) | Variable; **often absent**: many people who are shot make no sound or only say "I'm hit", and pain is often delayed `[R2-02 §2.4, §14 row 15]` | [R2-02] [E]. **Corrected: was "Victim's forced grunt — chest compression, startle"** |

**Region modifiers** `[E]` on the percussion analogy (§1.2):

| Region | Character | Recipe change |
|---|---|---|
| Thorax (lung) | Hollow, resonant "whump" | Body mode ×0.8 in frequency, `τ` ×1.4, +3 dB at 150–300 Hz |
| Upper abdomen (stomach with gas) | Tympanic, drum-like | Add a mode at 200–400 Hz, ζ 0.05 |
| Liver, thigh, buttock | Dull, short | `τ` ×0.7, −3 dB below 200 Hz |
| Limb with bone hit | Thud + crack | Add `BONE_CRACK` (§2.3) |
| Blood-filled chest (haemothorax) | Stony dull | Remove resonance, `τ` ×0.5 |
| Head | See §2.6 | — |

**Head shots.** With a high-velocity rifle or a contact shot, the skull **bursts** (R1-01 §5–§6 fracture and ejection mechanics). The sound is the loudest impact in the game: a sharp crack co-timed with a wet burst (5–30 ms, broadband 200 Hz – 8 kHz), then fragment and droplet patter 30–300 ms later `[K] (M)` description, `[E]` sound. A low-energy handgun head shot sounds like a skull knock (§2.6) with a crack and little burst.

**Recipe `GSW_FLESH`** (handgun, torso) `[E]`:
1. `slap`: `NOISE(white) → BP(600–1,200 Hz, Q 0.8) → ENV(0.3 ms, 0, τ 4 ms)`; 0 dB.
2. `body`: `MODE(120–250 Hz, ζ 0.3)` with `PITCHDROP(0.7, 20 ms)`, plus `NOISE(brown) → LP(400 Hz, 12) → ENV(1 ms, 0, τ 15 ms)`; −3 dB.
3. `cavity`: 2–4 half-sine pulses of low-passed noise (`LP 500 Hz`), periods 2, 3, 4.5 ms, each ×0.5 of the previous; −10 dB (handgun), 0 dB (rifle; rifle periods ×1.5).
4. `wet`: `CLOUD(λ 300–1,000/s, GRAIN(0.3–1 ms, BP 1–4 kHz), T 20–40 ms)`; −15 dB.
5. `cloth` (if clothed): `NOISE(white) → HP(2 kHz, 12) → ENV(0.1 ms, 0, τ 1.5 ms)`; −10 dB.
6. Apply the region modifier; randomise mode frequencies ±15 % and level ±3 dB per hit.

### 2.3 Bone fracture, crunch and crepitus

- **Mechanism** `[K] (H)`: a fracture releases stored elastic energy almost instantly. Cracks run at hundreds to ~2,000 m/s `[R1-01 §5]`. The acoustic source is a **step release**: a broadband click (much of the acoustic emission is ultrasonic and inaudible), followed by the fragments ringing, heavily damped by muscle.
- People who break a long bone, and bystanders, commonly report an audible **"crack", "snap" or "pop"** `[K] (M)`.
- **Small, thin or multiple fragments** (nasal bones, orbital floor, comminuted fractures) give a **crunch**: a cluster of 3–10 small clicks within 5–30 ms `[K] (M)`, `[E]`.
- **Crepitus** `[K] (H)`: grating of bone ends when a fractured part is moved or pressed. It is **mostly felt, and only faintly heard** at close range. Subcutaneous emphysema (air in the tissues after chest or airway injury) crackles "like crushed tissue paper" under a pressing hand, audible only within ~0.3 m.

| Event | Recipe `[E]` | Level at 1 m `[E]` (L) |
|---|---|---|
| `BONE_CRACK` (long bone, rib, mandible) | Impulse (2–4 samples) → `HP(800 Hz, 12)`; `MODAL`: 3–5 modes at 0.3–1 kHz (long bone) or 1.2–4.5 kHz (rib, facial bone), ζ 0.05–0.15; 1–3 secondary micro-cracks at +2–15 ms, each −6 dB; plus the flesh `body` layer of the blow | 75–95 dB peak |
| `BONE_CRUNCH` (nasal, orbital, comminuted, repeat blow on a fractured bone) | `CLOUD(λ 200–600/s, GRAIN(0.2–0.8 ms, BP 1.5–6 kHz), T 5–30 ms)` + a low wet `body` layer; no ring | 65–85 dB peak |
| `TEETH_CLACK` (jaw snapped shut by an uppercut or fall) | Two to three clicks 2–10 ms apart, `BP 2–6 kHz, Q 3`, `τ` 1–3 ms | 65–80 dB peak |
| `TOOTH_BREAK` | One sharp click `BP 3–8 kHz`, `τ` 1 ms + tiny patter of fragments if they fall on a hard floor | 60–75 dB peak |
| `CREPITUS` (moving a fractured limb) | `CLOUD(λ 10–60/s × joint angular speed, GRAIN(0.3–1 ms, BP 1–5 kHz))` | 35–50 dBA |
| `EMPHYSEMA_CRACKLE` (pressing air-filled tissue) | `CLOUD(λ 100–400/s, GRAIN(0.1–0.5 ms, HP 2 kHz))` during the press | 25–40 dBA |

### 2.4 Knife: stab, slash, withdrawal

- **Knife injuries are acoustically near-silent** `[K] (M)`. Most of what is heard is clothing, the attacker's movement and the victim's voice and breathing.
- **Skin puncture** `[K] (M)`: skin is the most resistant soft tissue. It tents under the point, then gives suddenly. Typical sharp knives penetrate skin at roughly **10–50 N**; blunt tips need more; clothing adds resistance `[K] (L–M)`. Once through the skin the blade meets little resistance until cartilage or bone. The give is a soft **"tick" or "pop"** (`[R1-02 §2]`): `GRAIN(1 ms, BP 800–2,000 Hz)`, **35–55 dB at 0.5 m** `[E]`.
- **Through clothing**: fabric pierce "tick" + a short tear 20–100 ms (cotton quiet; denim and canvas louder; leather a dull "thock") `[E]`: `NOISE → BP(2–8 kHz)` with 100–300 Hz granular AM for the "zip" of a tear.
- **In tissue**: a faint wet "squelch" when the blade moves: `CLOUD(λ 100–400/s, GRAIN(0.5–2 ms, BP 300–1,500 Hz), T 50–300 ms)`, −30 dB relative to the puncture `[E]`.
- **Blade on bone or cartilage**: a dull "tock" `MODAL(1–4 kHz, ζ 0.1)` `τ` 3–8 ms; a blade dragged along a rib gives a grating scrape (stick–slip at 200–1,000 Hz, amplitude-modulated by blade speed) `[E]`.
- **Withdrawal**: usually silent. A deep wound in wet tissue may give a short suck ("slurp") as air enters. **A chest stab that opens the pleura hisses or bubbles on the next breaths** (§5.4) `[R1-04 §9]`.
- **Slash**: skin opens silently; heard: fabric rip, the victim's gasp or cry, then blood patter (§3). A deep neck slash that opens the airway adds air rushing and bubbling through the wound with each breath and a loss of voice (§5.5, §7.2).

### 2.5 Punch, kick, stamp and hammer

| Blow | Heard | Recipe `[E]` | Level at 1 m `[E]` (L) |
|---|---|---|---|
| Bare-knuckle punch to face | Dull smack; small skin slap; crunch if the nose breaks; teeth clack if the jaw snaps shut; victim's forced exhalation | `body`: `MODE(90–160 Hz, ζ 0.4)` + `LP(300 Hz)` noise, `τ` 8–15 ms; `slap`: `BP(1.5–4 kHz, Q 1)` `τ` 2–4 ms at −8 dB; optional `BONE_CRUNCH`, `TEETH_CLACK` | 70–85 dB peak |
| Punch to the body | Dull thud; clothing; if winded, a short "ugh" then silent breath-hold 3–15 s `[R2-02 §6.5]` | `body` `MODE(70–130 Hz)`, `τ` 12–25 ms; cloth `BP(1–5 kHz)` −12 dB | 65–80 dB peak |
| Kick (shoe) to torso | Heavier, lower thud; rib crack if ribs break | `body` ×1.3 level, `τ` ×1.2; shoe-sole slap `BP(1–3 kHz)` | 75–90 dB peak |
| Stamp on head on a hard floor | Two sounds: shoe on head, head on floor (skull knock, §2.6) | Two impacts 1–5 ms apart | 80–100 dB peak |
| Hammer on muscle | Short, dull thud; steel ring barely audible | `body` with `τ` 5–10 ms; hammer ring `MODAL(2–6 kHz)` at −25 dB, `τ` 10 ms | 70–85 dB peak |
| Hammer on bone under thin skin (shin, knuckles, clavicle, face) | Hard "tock"; crack on fracture | `MODAL(1–3 kHz, ζ 0.05)` `τ` 5–15 ms + `BONE_CRACK` on fracture; steel ring −15 dB | 80–95 dB peak |
| Hammer on skull | §2.6 | — | 80–100 dB peak |

- **Hammer head ring**: a free steel hammer head rings at several kHz for 100 ms or more, but while it is pressed against tissue the ring is damped. On rebound from bone, a short metallic ring of **10–40 ms at −15 to −25 dB** is plausible `[E]` (L).

### 2.6 The skull: intact, cracked, comminuted, open

The same blow sounds different as the skull fails. This progression is the most important sound cue for the hammer `[R1-02 §5]` `[K] (M)`, `[E]`.

| Skull state | Heard | Recipe `SKULL_KNOCK(state)` `[E]` |
|---|---|---|
| **Intact** (scalp 5–7 mm over bone) | Hollow knock ("coconut"); dull at the first contact because the scalp cushions it | Scalp thud `LP(400 Hz)` `τ` 5 ms; `MODAL`: 1.0 kHz (ζ 0.06), 1.7 kHz (ζ 0.07), 2.8 kHz (ζ 0.08), 4.2 kHz (ζ 0.10), relative 0, −4, −8, −14 dB; whole bank `LP(3 kHz)` while in contact |
| **Fracture on this blow** | Sharp crack on top of the knock | Add `BONE_CRACK` with 1.2–4.5 kHz modes, +6 dB |
| **Cracked** (linear fracture present) | Lower, buzzy, shorter knock | Modes ×0.6–0.8 in frequency, ζ ×2–3; add a buzz: `AM(40–120 Hz, 0.3)` on the ring (edges rattling) |
| **Depressed / comminuted** | "Crunch-squelch", no ring | `BONE_CRUNCH` + wet `CLOUD` (blood, CSF), `LP(1.5 kHz)` body; no modes |
| **Open** (fragments displaced, brain exposed) | Wet slaps on soft tissue; occasional click on fragment edges | `GSW_FLESH` wet/body layers only, `τ` 5–10 ms; 20 % chance of a fragment click |

- Head-to-floor impacts (§4) use the same states: a second fall of a fractured head sounds duller.

### 2.7 Burning (addition to `[R1-02 §6]`)

| Sound | Mechanism | Recipe `[E]` |
|---|---|---|
| Steam hiss | Water flashing off skin and tissue | `NOISE → HP(3 kHz) → BP(4–10 kHz)`, level ∝ heat flux; onset 0.3–0.8 s after flame contact `[R1-02 §6]` |
| Sizzle | Many tiny boiling and bursting droplets | `CLOUD(λ 50–400/s, GRAIN(0.1–0.5 ms, HP 2 kHz))`; λ rises with surface temperature |
| Fat pops | Fat droplets bursting | `CLOUD(λ 0.5–5/s, GRAIN(1–3 ms, BP 1–5 kHz))` at +10 dB over the sizzle |
| Char crackle | Carbonised surface fracturing | Low-rate clicks 2–20/s, `BP 2–6 kHz` |
| Torch roar | The torch itself; usually masks everything above | Broadband roar; the flesh layers are 10–20 dB below it |

### Simulation parameters (impacts)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `impact_stylisation` | 0 (physical) – 1 (film) | — | Default 0 | [E] |
| `gsw_impact_spl_1m` | handgun torso 75–95; rifle 85–105; rifle/contact head 95–110 | dB peak | Calibrate against gel/meat foley | [E] (L) |
| `gsw_cavity_life` / `pulses` | 5–10 / 2–4 | ms / — | Rifle cavity large; handgun small | [K; M22] (M) |
| `impact_delay_at_shooter` | `d/v_bullet + d/343` | s | Makes the "whop" audible beyond ~20 m | [K] (H) ✓ verified (arithmetic) |
| `bone_crack_spl_1m` | 75–95 | dB peak | +6–10 dB over the flesh layer | [E] (L) |
| `crunch_grains` | 3–10 in 5–30 ms | — | Nasal, orbital, comminuted, repeat blows | [E] |
| `skin_puncture_force` | 10–50 (sharp knife) | N | Tick at the give; clothing adds 10–50 % | [K] (L–M) |
| `skin_puncture_spl_0.5m` | 35–55 | dB peak | Near-silent in practice | [E] |
| `punch_contact_time` | gloved ~12 (8–20); **bare knuckle 5–10** | ms | From [S14] impulse and force (gloved punches). Corrected: was "~12 (8–20)" for all punches | [S14] [E] ✓ arithmetic |
| `punch_face_spl_1m` | 70–85 | dB peak | | [E] (L) |
| `skull_modes_intact` | 1.0, 1.7, 2.8, 4.2 kHz; ζ 0.06–0.10 | Hz | ×0.6–0.8 and ζ ×2–3 once cracked | [K; M1] (M), [E] |
| `hammer_ring` | 2–6 kHz, 10–40 ms, −15 to −25 dB | — | Only on bone contact | [E] (L) |
| `crepitus_rate` | 10–60 × joint angular speed (rad/s) | clicks/s | 35–50 dBA; mostly felt | [K] (H) quality, [E] rate |

### Visual/behavioural checklist (impacts)
- A shot at 30 m: the report, then **0.12 s (rifle) to 0.17 s (handgun)** later a separate dull "whop" from the target. Corrected: was "about a tenth of a second later" (arithmetic: 30/350 + 30/343 = 0.173 s; 30/850 + 30/343 = 0.123 s).
- A rib or limb hit adds a sharp crack at the same instant; a startle grunt, if there is one, follows ~0.1 s later. Silence is common.
- Knife attacks are quiet: fabric, a soft tick, the victim's gasp. The loud part is the victim.
- Hammer on a head: first blows knock hollowly; the fracturing blow cracks; later blows crunch and squelch without any ring.
- A broken nose crunches on the blow and again, fainter, when touched.
- Burning: hiss and sizzle build over the first second of contact, with irregular fat pops.

---

## 3. Blood sounds

### 3.1 The physics that decides whether blood makes a sound

- **Blood jets never hiss.** The exit speed of a liquid jet is at most `√(2P/ρ)`. At 120 mmHg (16 kPa) and ρ = 1,060 kg/m³ that is **≤ 5.5 m/s**; real arterial jets leave at **3.3–4.4 m/s** `[R1-06 §8.1]`. A liquid jet this slow produces no audible flow noise `[K] (H)`. **The sound of arterial bleeding comes from where the jet lands** (spatter patter on surfaces, splashing into a pool, soaking into cloth), not from the wound. Where round one says "hiss" `[R1-03 §6.4]`, read it as spray patter at the landing point.
  - ✓ verified (arithmetic): √(2 × 15,996 Pa / 1,060) = 5.49 m/s. **Corrected (upper bound)**: a frightened, injured person often has a systolic pressure of 140–180 mmHg in the first minutes, giving **≤ 5.9–6.7 m/s**; the conclusion (no orifice noise) is unchanged. The 3.3–4.4 m/s "typical" value is itself an estimate (velocity coefficient 0.6–0.8); no measured human jet speeds were found in round one `[R1-03 §6.2]`.
  - Exceptions `[K] (M)`: blood driven out **with air** (open airway, sucking chest wound, jugular air entry) bubbles and sputters at the wound (§3.2, §5.4–§5.5); a jet forced through a small hole in tight clothing can "spit" faintly.
- **Bubbles make the "plink".** A drop falling into deep liquid can trap an air bubble. The bubble rings at the **Minnaert frequency** `f0 = (1 / 2πa) √(3γp₀/ρ)` `[K; M3] (H)`. In blood this is **`f0 ≈ 3.2 / a`** (a = radius in m): a 0.5 mm bubble rings at ~6.4 kHz, 1 mm at ~3.2 kHz, 2 mm at ~1.6 kHz, 5 mm at ~640 Hz. ✓ verified (arithmetic): √(3 × 1.4 × 101,325 / 1,060) / 2π = 3.19 (water: 3.28); surface tension adds < 1 % above a = 0.1 mm. The frequency rises slightly as the bubble rises (a short upward chirp), and the dripping-tap "plink" is this bubble oscillation driving the surface `[K; M3] (M)`. Thermal and radiation damping dominate at these sizes; blood's higher viscosity (3–4 mPa·s) adds little, so blood bubbles ring much like water bubbles `[K] (M)`.
- **Floor pools are too shallow to plink.** Blood pools spread to **~2.5 mm** `[R1-03 §10]`. A 3.9–4.9 mm drop (30–60 µL `[R1-06 §7]`) falling into a 2.5 mm film hits the floor through it and cannot trap a freely ringing bubble. **Drips into a floor pool make a wet "pat", not a "plink"** `[K] (M)`, `[E]`. Plinks occur only where blood collects deeper than ~1–2 cm (a basin, bath, bucket, hollow).
  - ✓ consistent (physics, not tested): a sessile puddle's maximum height is `2√(σ/ρg)·sin(θ/2)`; with blood σ ≈ 0.055 N/m the capillary length is ~2.3 mm, giving **~2.3–3.3 mm** for contact angles 60–90°, which matches the 2.5 mm pool. The crater of a 4–5 mm drop at 3–5 m/s is deeper than that, so it bottoms out on the floor instead of pinching off a bubble. Even in deep liquid, large drops entrain a ringing bubble only in some impacts (hence `p(bubble)` < 1).
  - **Corrected (bubble ring time)**: a mm-sized bubble has a total damping constant δ ≈ 0.03–0.06 (radiation + thermal; viscosity negligible), i.e. Q ≈ 15–35, so the amplitude time constant is `τ = Q/(π f0)`: **~1 ms at a = 0.5 mm, ~2–3 ms at 1 mm, ~4–7 ms at 2 mm, ~15–20 ms at 5 mm** `[K]` (M). The recipes below used τ 3–15 ms for 0.5–2 mm bubbles, which rings 2–3× too long.
- **Once the pool gels (5–15 min `[R1-03 §10]`)** drops land on a gel: an even duller, softer "pat".

### 3.2 Event catalogue

| Event | Conditions | Heard | Recipe `[E]` | Level at 1 m `[E]` (L) |
|---|---|---|---|---|
| **Drip on hard dry floor** | 1–15 mL/min; rate = `Q / 50 µL` (20 drops/min per mL/min) `[R1-03 §6.4]`; drops hit at ~3–5 m/s from wound heights 0.5–1.5 m | "Tick"/"tap" | `GRAIN(1–3 ms, BP 1.5–5 kHz)` + a tiny splash `CLOUD(λ 2,000/s, T 5 ms)` | 30–45 dB peak |
| **Drip into a floor pool** | As above, on a fresh pool | Wet "pat" | `GRAIN(2–5 ms, BP 500–2,000 Hz)` + satellite ticks (1–4 mm drops, `[R1-03 §10]`) at −12 dB, 5–30 ms later | 30–45 dB peak |
| Drip onto gelled pool | Pool older than 5–15 min | Soft "pat" | As above, `LP(1.2 kHz)`, −6 dB | 25–40 dB |
| **Drip into deep liquid** | ≥ 1–2 cm deep | "Plink" | Impact `GRAIN(1 ms)` + `BUBBLE(a 0.5–2 mm, τ = Q/(π f0) ≈ 1–7 ms, σ +0.1–0.3)` with p(bubble) 0.1–0.5 per drop. Corrected: was τ 3–15 ms | 35–50 dB peak |
| Drip on cloth, skin, carpet | — | Nearly silent | `GRAIN(2 ms, LP 1 kHz)` at −20 dB | < 25 dB |
| **Stream** (15–300 mL/min) | Continuous thin stream to the floor | Trickle and splash | `NOISE(pink) → BP(300–4,000 Hz)`; level `∝ 10·log10(Q) + 20·log10(v_impact)`; slow random AM 2–8 Hz | 35–55 dBA |
| **Arterial spurting** | Pulsed jet at HR `[R1-03 §6]` | A patter burst per beat where the jet lands | Per beat: spray `CLOUD(λ 2,000–8,000/s, GRAIN(0.2–1 ms, BP 1.5–6 kHz))` whose rate and level follow the pressure waveform (upstroke 0.1 s, peak 0.15 s, decay) `[R1-03 §6]`. Spectral centroid ~3–5 kHz at MAP 90, ~1.5–2.5 kHz at MAP 40 as drops slow. Stops below `jet_min_map` 25–30 mmHg | 45–65 dBA at the landing point |
| Jet onto the victim's own clothes | — | Muffled pulsing "wet thud" | Above, `LP(1 kHz)`, −12 dB | 30–45 dBA |
| **Gurgling spurt** (blood forced through a clot or a narrow wound with air) | Deep wound with air in the track | "Glug" per beat | 1–3 `BUBBLE(a 2–6 mm, τ 5–15 ms)` per beat + low wet body | 40–55 dBA |
| **Venous pour** | Steady flow, varies with breathing at neck veins | Soft trickle | Stream recipe at −6 dB; 20–40 % AM at the respiratory rate for neck wounds | 30–45 dBA |
| **Neck-vein air entry** `[R1-02 §2]` | Open jugular above heart level, inspiration | Sucking hiss or gurgle on each inspiration, frothy dark blood | Inspiratory `NOISE → BP(1–4 kHz)` 0.3–1 s + `BUBBLE` cloud (a 1–3 mm) | 35–50 dBA |
| **Exit spray patter** (GSW) | Droplets 0.1–4 mm hitting walls and floor | Brief "shhk" | `CLOUD(λ 5,000–20,000/s, GRAIN(0.1–0.5 ms, HP 2 kHz), T 20–100 ms)`, delayed 30–300 ms `[R1-01 §7]` | 40–60 dB peak |
| **Bubbling at the lips/nostrils** | Blood or froth in the airway, each breath | Tiny pops and bubbling | Film-rupture pops `GRAIN(0.2–1 ms, BP 1–8 kHz)` λ 5–40/s during expiration + `BUBBLE` (a 1–3 mm) | 25–40 dBA |
| **Spitting blood** | Conscious, oral blood `[R2-04 §2.5]` | Plosive "ptuh" + splat | Lip burst `NOISE → BP(1–3 kHz)` 20–40 ms + splat on landing | 50–65 dB peak |
| **Stepping in blood** | Fresh pool | Wet slap on landing; sticky peel on lift once the pool is tacky | Slap: `GRAIN(3–8 ms, BP 300–2,000 Hz)`; peel: `CLOUD(λ 200–800/s, GRAIN(0.2 ms, BP 1–4 kHz), T 50–150 ms)` | 45–60 dB peak |
| **Dragging a body through blood** | — | Smeared slide | Friction noise `NOISE(pink) → BP(200–1,500 Hz)` ∝ speed + wet grains | 40–55 dBA |

### Simulation parameters (blood sounds)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `minnaert_blood` | `f0 = 3.2 / a` | Hz (a in m) | 1 mm → 3.2 kHz | [K; M3] (H) ✓ verified (arithmetic) |
| `plink_min_depth` | 10–20 | mm | Floor pools (2.5 mm) never plink | [K] (M), [E] ✓ consistent (capillary-length check) |
| `bubble_p_per_drop` | 0.1–0.5 | p | Deep liquid only | [E] |
| `bubble_tau` / `chirp` | `Q/(π f0)`, Q 15–35 (≈ 1 ms at 0.5 mm … 15–20 ms at 5 mm) / +10–30 % | ms / — | **Corrected: was 3–15 ms** for all sizes | [K] (M), [E] |
| `jet_orifice_noise` | none | — | Jet speed ≤ 5.5 m/s at 120 mmHg (≤ 6.7 m/s at 180 mmHg) | [K] (H) ✓ verified (arithmetic) |
| `spurt_centroid` | 3–5 kHz at MAP 90 → 1.5–2.5 kHz at MAP 40 | Hz | Follows droplet energy | [E] |
| `drip_rate` | `20 × Q` (Q in mL/min) | drops/min | Stream above 15–30 mL/min | `[R1-03 §6.4]` |
| `drip_spl_1m` | 30–45 | dB peak | | [E] (L) |
| `stream_spl_1m` | 35–55 | dBA | ∝ 10 log Q | [E] (L) |
| `pool_gel_time` | 5–15 | min | Drips then sound duller | `[R1-03 §10]` |

### Visual/behavioural checklist (blood sounds)
- An arterial wound is heard where the blood lands: a rhythmic patter on the floor or wall in time with the pulse, getting faster, softer and duller as the victim bleeds out, then stopping at the last effective beat.
- Drips on a bare floor tick; drips into the victim's own pool pat. Only blood collecting in a deep container plinks.
- Frothy lung blood crackles and bubbles faintly at the lips with each breath.
- Walking through a fresh pool slaps; a few minutes later it starts to peel and stick.

---

## 4. Body-fall and collapse sounds

### 4.1 Sequence

The contact order, impact speeds and collapse types come from `[R2-03 §5–§6]` and `[R2-02 §5]`. Each Jolt contact event above a speed threshold triggers `FALL_THUD(part, v_n, surface)`.

| Collapse type | Typical contact sequence | Span | Tag |
|---|---|---|---|
| "Cut strings" limp drop (brainstem, high cord) | Knees → buttocks/hip → trunk → head last (whip) → arms flop | 0.4–1.2 s; 3–6 distinct thuds | `[R2-03 §5.2, §6.1]` [E] |
| Rigid topple (tonic, decerebrate) | Trunk and head almost together; **head at ~6–7 m/s** | One heavy impact + crack | `[R2-03 §5]` |
| Forward fall with arms (conscious) | Palms slap → knees → chest → head (often protected) | 0.2–0.6 s | `[R2-02 §5]` |
| Sag / sit-down (syncope prodrome, blood loss) | Buttocks → back → head (low speed) | 1–3 s, soft | `[R2-03 §5.3, §5.5]` |
| Falling against a wall or furniture | Shoulder/head on the object, then the floor | Adds object sounds | [E] |

### 4.2 Components by body part `[E]` (speeds from `[R2-03 §6]` and `[S7]`)

| Part | Effective mass | Impact speed | `τc` on concrete | Band | Level at 1 m (peak) | Notes |
|---|---|---|---|---|---|---|
| **Head** | 4.5–5 kg | 2.0–7.4 m/s | 2–8 ms | Force < 200–750 Hz + skull modes ~1–4 kHz | **80–95 dB** | The defining sound: a hard "knock" or "crack". Use `SKULL_KNOCK(state)` (§2.6) scaled by speed |
| Trunk (back or chest) | 25–40 kg | 2–5 m/s | 30–80 ms | < 150 Hz | 75–90 dB | Heavy "thump" plus air forced from the chest (§4.4) and clothing flap |
| Hip / buttocks | 15–30 kg | 2–3.5 m/s | 30–60 ms | < 100 Hz | 70–85 dB | Mostly felt; floor-dependent |
| Knees | 5–10 kg | 1.5–3 m/s | 10–20 ms | 60–400 Hz + patella knock if bare | 70–85 dB | Often the first sound of a limp drop |
| Palms (slap) | 1–2 kg | 2–3 m/s | 3–10 ms (+ air squeeze) | 200 Hz – 4 kHz | 70–85 dB | Only when arms still work |
| Arms, legs flopping | 1–4 kg | 1–3 m/s | 10–30 ms | < 500 Hz | 55–70 dB | Staggered 50–400 ms after the trunk |
| Held weapon, keys, phone | — | 2–5 m/s | < 1 ms | 1–8 kHz, ringing, bounces | 70–95 dB | **Often the loudest part of a fall** |

- **Loudness scaling** `[E]`: `L_peak = L_ref + 20·log10(v / v_ref) + 10·log10(m / m_ref)`, with `L_ref` 88 dB for the head at 5 m/s and 82 dB for a 30 kg trunk at 3 m/s. Band-limit with `LP(1.5/τc)` from §1.1.

### 4.3 Floors

| Surface | Change to the body sounds `[E]` on `[K]` |
|---|---|
| Concrete (bare or sealed) | Reference. Dense and non-resonant: the sound is the body, the head knock, clothing and air |
| Ceramic tile on a solid bed | Brighter: +3 dB above 2 kHz on head and hand contacts; a small "click" on teeth, buttons, buckles |
| Tile over voids (poor bedding) | Hollow "clack" resonances 0.5–2 kHz, T60 30–80 ms |
| Wooden floor | Panel/joist "boom" 50–200 Hz, T60 100–300 ms; rattle of loose objects; +6 dB below 200 Hz |
| Carpet | −10 to −20 dB, `LP(800–1,200 Hz)`; head knock becomes a muffled thud |
| Grass, soil | −10 dB, `LP(500 Hz)`, a soft crunch of vegetation |
| Metal grating or plate | Ringing 0.3–3 kHz, T60 0.3–1 s |
| Water or deep puddle | Splash replaces the thud |

### 4.4 Air forced out of the chest

- A trunk impact compresses the chest by **10–30 mm** and pushes out **0.2–0.6 L of air in 50–150 ms** `[E]` (L).
- With an open glottis (unconscious or dead) this is a **voiceless "huff"** (`NOISE → BP(300–2,000 Hz)`, 100–250 ms). If the vocal folds are partly closed (a conscious person bracing, or a relaxed larynx) it becomes a short **voiced "uhh/ugh"** at F0 80–150 Hz (§6) `[E]`.
- The same mechanism produces the "post-mortem groan" when a dead body is moved or pressed `[R1-04 §12.1]`.
- `p(voiced)` `[E]`: conscious 0.6–0.8, unconscious 0.2–0.4, dead 0.1–0.3.

### 4.5 After landing

- Settling (`[R2-03 §6.5]`): limb slides, clothing rustle, a last roll of the head (skin or teeth tick), then silence.
- Then, if alive: snoring or gurgling (§5); if agonal: gasps (§5, `[R2-04 §2.2]`); if bleeding: patter or trickle (§3).

### Simulation parameters (falls)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `fall_contact_threshold` | 0.5 | m/s normal speed | Below: rustle only | [E] |
| `head_fall_spl_1m` | 80–95 at 2–7.4 m/s | dB peak | Uses `SKULL_KNOCK` | [E] (L), [S7] speeds |
| `trunk_fall_spl_1m` | 75–90 | dB peak | + chest "huff" | [E] (L) |
| `fall_L_ref` | head 88 dB @ 5 m/s; trunk 82 dB @ 3 m/s, 30 kg | dB | Scaling law §4.2 | [E] |
| `chest_huff_volume` / `duration` | 0.2–0.6 / 50–150 | L / ms | | [E] (L) |
| `chest_huff_voiced_p` | conscious 0.6–0.8; unconscious 0.2–0.4; dead 0.1–0.3 | p | | [E] |
| `limb_flop_delay` | 50–400 | ms after trunk | Staggered | [E] |
| `floor_profiles` | table §4.3 | — | Per physics material | [E] |

### Visual/behavioural checklist (falls)
- A limp drop is a short series of heavy, dull thuds (knees, hips, back) ending in the sharp knock of the head, then the softer flop of arms.
- Carpet swallows the thuds; a wooden floor booms and rattles; a dropped pistol clatters louder than the body.
- The chest hitting the floor forces out a breath: a voiceless huff from an unconscious body, a grunt from a conscious one.
- After the landing: silence, or snoring, gurgling or gasps.

---

## 5. Breathing sounds by state: acoustics and synthesis

The physiology (when each pattern happens, rates, probabilities, gasps, rattle, blood in the airway, cough mechanics, vomiting) is in `[R2-04 §2]` and `[R1-04 §5, §9]`. This section gives the **sound** of each state and a synthesis recipe.

### 5.1 Acoustic basis

- **Breath noise is turbulence** at the glottis, pharynx, nose and lips. Its power rises steeply with flow: tracheal sound power grows roughly with **flow^1.75–2** (about **+5–6 dB per doubling of flow**) `[K; M4] (M)`. **Corrected: was "about +10–12 dB per doubling of flow"**: a power law `P ∝ Q^n` gives `10·n·log10(2)` = 3.0·n dB per doubling, i.e. 5.3 dB (n = 1.75) to 6.0 dB (n = 2); +10–12 dB would need n ≈ 3.5–4. The exponent itself ✓ matches the checker's recall of the tracheal-sound literature (Gavriely & Cugell; exponents ~1.5–2 reported) `[K]` (M), not re-opened. The §5.3 recipe (amplitude ∝ flow, power ∝ flow²) was already consistent with the exponent. Quiet breathing is nearly silent at 1 m; panting is clearly audible (a 4–6× rise in flow is +12–16 dB).
- **Spectrum**: tracheal breath sound spans ~100–1,500 Hz with energy to ~2 kHz `[K; M4] (M)`. ✓ verified [K] (M): the usual textbook range for normal tracheal sounds is 100–1,500 Hz, with a steep fall above ~800–1,000 Hz; chest-wall (vesicular) sounds are narrower (100–1,000 Hz, power falling above ~200 Hz). What a listener at 1 m hears is shaped by the exit route:
  - **nose**: a narrower, higher hiss (1–4 kHz), quiet;
  - **open mouth**: noise shaped by the vocal tract, with broad peaks at the open-vowel formants (F1 ~600–900 Hz, F2 ~1,100–1,500 Hz), louder.
- **Route rule** `[K] (M)`, `[E]`: nose at rest; mouth when tidal volume > ~1 L, RR > ~25/min, in pain or panic, when the nose is blocked (blood, fracture) or when unconscious with the jaw open.
- **Standard names and definitions of adventitious sounds** (CORSA) `[K; M5] (H)` unless marked. ✓ verified [K] (H) for crackle (< 20 ms; fine 2CD < 10 ms, coarse 2CD > 10 ms), wheeze (continuous, musical, ≥ 100 ms, dominant frequency > 100 Hz) and rhonchus (low-pitched, ≤ ~200 Hz); CORSA not re-opened. Stridor site rule ✓ [K] (H): extrathoracic narrowing (larynx, upper trachea) → inspiratory; intrathoracic tracheal → expiratory; fixed or severe → biphasic. ⚠ Stridor frequency: many descriptions put the dominant frequency above ~500 Hz; keep 250–1,000 Hz but default to 500–800 Hz.

| Sound | Definition | Typical frequency | Game use |
|---|---|---|---|
| **Crackle** | Discontinuous, explosive, < 20 ms. **Fine**: two-cycle duration (2CD) < 10 ms; **coarse**: 2CD > 10 ms | Fine higher, coarse lower (coarse ~100–500 Hz) (M) | Fluid in small (fine) or larger (coarse) airways: aspirated blood, lung contusion, neurogenic pulmonary oedema |
| **Wheeze** | Continuous, musical, ≥ 100 ms | Dominant > 100 Hz, usually ≥ 400 Hz | Bronchospasm after aspiration or smoke; rare in this game |
| **Rhonchus** | Low-pitched wheeze | ≤ 200–300 Hz, snoring-like | Secretions or blood in large airways |
| **Stridor** | Loud, high-pitched, musical; inspiratory when the narrowing is above the thorax (larynx, upper trachea); biphasic when severe or tracheal | Fundamental ~250–1,000 Hz with harmonics (M–L) | Laryngeal fracture or haematoma, neck haematoma compressing the airway, strangulation, inhalation burns, bilateral recurrent laryngeal nerve injury |
| **Stertor (snoring)** | Low-pitched, rattling, inspiratory; flutter of the soft palate or tongue base | Palatal flutter ~20–150 Hz with harmonics; tongue-base more noise-like with peaks ~0.5–2 kHz (M–L) | Unconscious and supine `[R2-04 §2.1]` |
| **Gurgle** | Bubbling of liquid in the pharynx or larynx, both phases | Bubble grains ~300–1,500 Hz | Blood, saliva, vomit in the throat |

### 5.2 State table

Levels are dBA at 1 m `[E]` (L–M) unless tagged; rates and timings from the sibling documents.

| State | RR / flow | Phases heard | Character | Band / tonal features | Level | Source |
|---|---|---|---|---|---|---|
| Quiet, calm | 12–20/min; tidal 0.5 L; peak ~0.5 L/s | Both, faint | Nasal hiss | BP 1–4 kHz | 15–25 | [K] (M) |
| Aroused, frightened (not yet hurt) | 18–30; 1–2 L/s | Both | Audible mouth breathing | Open-mouth formant noise | 35–50 | [K] (M) |
| **Acute pain** | Irregular | Breath-hold 1–5 s, then forced exhalation | **Hiss through clenched teeth** (sibilant 3–8 kHz, 0.5–2 s) or through pursed lips (1–3 kHz); **catching inspirations**; groans or grunts on expiration | Voiced components §6 | 40–65 | `[R2-03 §7.6]` [K] (M) |
| Panic, hyperventilation | 30–50; 2–3 L/s | Both, loud | "Huh-huh" with voiced expirations | Formant noise + voicing at F0 150–300 Hz | 50–65 | [K] (M) |
| **Splinting** (rib fractures, chest wall, abdominal wound) | 25–35, shallow | Inspiration cut off with a catch at the pain point | Short "uh!" at the catch; expiratory grunt | Voiced grunt §6 | 35–55 | [K] (H) |
| **Shock class II–III** | 25–40; tidal 0.25–0.45 L | Both | Rapid, shallow, dry mouth breathing; **lip and tongue "clicks"** from a dry mouth; **sighs** every 15–60 s `[R2-04 §2.8]` | Open-mouth noise, `LP 3 kHz` | 35–50 | `[R1-03 §3]` [K] (M) |
| Shock class IV | 30–40 then slowing, irregular | Both, weak | Shallow, faint, irregular; occasional sigh or moan | — | 25–40 | `[R1-04 §7]` [K] (M) |
| **Air hunger** (lung or airway injury, tension, hypoxia) | 30–45; effortful | Loud inspirations 0.4–0.8 s | Deep, straining; voiced effort on inspiration; speech in 1–4-word bursts | Formant noise + low voicing | 50–65 | `[R1-04 §9]` [K] (H) |
| **Stertor** (unconscious, supine) | 10–25 | Inspiration | Rhythmic snore | Pulse train 30–120 Hz + harmonics, `LP 800 Hz` | 45–70 | `[R2-04 §2.1]` |
| **Stridor** | Any | Inspiration (biphasic if severe) | Crowing, whooping, musical | Harmonic tone 250–1,000 Hz, glides up with flow | 50–75; **becomes quieter as obstruction nears complete** | [K] (M) |
| Complete obstruction | Effort without air | — | **Silence**; a squeak at most; see-saw chest; hands to throat | — | < 30 | `[R2-04 §2.1]` [K] (H) |
| **Gurgling** (fluid in pharynx/larynx) | Any | Both | Wet bubbling; bubbles at lips and nostrils | Bubble grains 300–1,500 Hz, rate ∝ flow × fluid | 45–65 | `[R2-04 §2.5]` |
| Wet chest (aspiration, contusion, NPE) | 25–40 | Both | "Crackly" texture under the breath noise, audible at 1 m only with fluid in large airways | Coarse crackle grains (2CD > 10 ms) | 30–45 | [K; M5] (M) |
| **Death rattle** (unconscious for hours) | Slow | Both | Coarse, wet rattle in time with breathing | Grains 100–600 Hz + low bubbling | 40–60; −6 dB when lying on the side | `[R2-04 §2.4]` |
| **Agonal gasp** | 3–10/min, slowing | Short violent inspiration 0.2–0.6 s; passive expiration | Snort, "huh", snore, gurgle; sometimes a groan on expiration | Pharyngeal noise 200–1,500 Hz with **30–80 Hz flutter**; groan F0 70–110 Hz | 50–70 | `[R2-04 §2.2]` |
| Mandibular breathing (dying over hours) | Slow, shallow | Faint | Jaw drops with each breath; faint lip and tongue clicks | — | 20–35 | `[R2-04 §2.3]` |
| Cheyne–Stokes, ataxic, apneustic | Per `[R1-04 §5.5]` | — | Amplitude envelopes over the base breath noise; apnoeas silent | — | — | `[R1-04 §5.5]` |
| Expiratory grunting (dying; splinting) | Each breath | Expiration | Short voiced grunt 100–300 ms | F0 80–150 Hz | 35–55 | `[R2-04 §2.8]` |
| **Sob** | Crying | 3–6 inspiratory "hitches" at 4–8 per s, each 60–150 ms, then a voiced expiration | Glottal catches + wail or moan | §6 | 50–75 | [K] (M), [E] |
| Sniff (crying, nosebleed) | — | Short nasal inspiration 100–300 ms | Hiss `BP 1–4 kHz`; with blood a wet snort (bubbles) | — | 35–50 | [E] |
| Cough | `[R2-04 §2.5]` | Explosive phase 30–50 ms broadband (200 Hz – 6 kHz); noisy intermediate phase 100–300 ms; optional voiced end 50–200 ms | Wet cough adds crackle and bubble grains and spray | — | 65–85 peak | [K] (M), [E] |
| Hiccup | `[R2-04 §2.8]` | Glottal closure ~35 ms after the diaphragm jerk | "Hic": click + 30–80 ms voiced | — | 50–65 | `[R2-04 §2.8]` |
| Dead | — | None | Silence; passive huff or groan only when moved or pressed (§4.4) | — | — | `[R1-04 §12.1]` |

### 5.3 Recipe `BreathSynth` `[E]`

Per breath, generate a flow curve and derive every layer from it.

1. **Flow curve** `FLOW(t)` in L/s:
   - normal: inspiration a half-sine of duration `Ti`, expiration an exponential decay over `Te`; `Ti : Te` 1 : 2 at rest, 1 : 1–1.5 in distress;
   - gasp: rise in 50–100 ms to 1–5 L/s, fall over 150–500 ms; passive expiration 1–3 s `[R2-04 §2.2]`;
   - splinted: half-sine truncated at 40–70 % of its planned volume, followed by a 50–150 ms "catch" (glottal closure).
2. **Base noise**: `NOISE(pink)` → route filter (nose: `BP 1–4 kHz` + a 2.5 kHz peak; mouth: two resonators at F1 = `300 + 17 × jaw_mm` Hz, clamped 250–1,000 Hz, and F2 1,100–1,500 Hz, bandwidths ×2 of voiced values) → gain `g = (|FLOW| / 0.5 L/s)^1.0` in amplitude (≈ power ∝ flow²), referenced to 20 dBA (nose) or 25 dBA (mouth) at 0.5 L/s.
3. **Snore layer** (inspiration only, unconscious and supine, `stertor` roll true): pulse train at 30–120 Hz with ±15 % jitter, amplitude ∝ `max(0, FLOW − 0.2 L/s)`, through `LP(800 Hz)`; add ±20 % random amplitude per pulse for rattle.
4. **Stridor layer**: harmonic tone, `f = f_str × (0.8 + 0.4 × FLOW / FLOW_peak)`, `f_str` 250–1,000 Hz by the narrowing; 3–6 harmonics at −6 dB each; + band noise around `f`. Level ∝ narrowing × flow; when narrowing > 0.9, level falls toward zero (no flow).
5. **Gurgle layer**: `CLOUD(λ, BUBBLE(a 1–5 mm, τ 2–8 ms, σ 0.1–0.3), during |FLOW| > 0.1)`, with `λ = 40 × |FLOW| × min(fluid_mL / 20, 1)` per s; audible from ~5–10 mL of pharyngeal fluid. Confinement and viscous fluid pull the bubble resonances down into 300–1,500 Hz.
6. **Rattle layer** (death rattle): as gurgle, with a 10–25 Hz "rattling" AM and bubble radii 3–8 mm (lower, coarser).
7. **Crackle layer**: coarse crackles as `GRAIN(2CD 10–20 ms)` at 5–40 per breath late in inspiration; fine crackles `GRAIN(2CD 3–8 ms)`.
8. **Voice hook**: expiratory grunts, groans, whimpers and screams are requested from `VoiceSynth` (§6) and occupy the expiration of this breath.

### 5.4 Sucking chest wound

`[R1-04 §9]`: air enters preferentially through a chest-wall defect larger than about two-thirds of the tracheal diameter (≳ 10–13 mm). ✓ verified [K] (H): this is the standard ATLS teaching (a teaching rule of thumb, not a measured threshold). The **sound depends on the size of the hole** because the air speed through it does `[K] (H)` physics, `[E]` values. ⚠ The hiss/whistle-versus-slurp split is physics-derived; clinical descriptions mention "sucking", hissing and bubbling but no measured spectra were found:

| Defect | Air speed through it | Heard on inspiration | Heard on expiration | Level at 1 m |
|---|---|---|---|---|
| **Small or slit-like, flap acting as a valve** (≲ 5–8 mm) | High: the hole limits inflow, so a pressure difference of **~2–15 cmH₂O** builds across it, giving **~20–50 m/s** (Bernoulli `v = √(2ΔP/ρ_air)`: 2 cmH₂O → 18 m/s, 15 cmH₂O → 50 m/s). **Corrected: was "pleural pressure stays strongly negative (−10 to −40 cmH₂O in distress), giving ~20–50 m/s"**: −10 to −40 cmH₂O would give 40–80 m/s (internal inconsistency). Flow check: 0.5 L/s through 5 mm (19.6 mm²) ≈ 25 m/s | **Hiss or whistle**: broadband peak 1–5 kHz; a tonal whistle when the edge is sharp (`f ≈ 0.2 × v / d`: 30 m/s through 5 mm → ~1.2 kHz) | Bubbling as air and blood are pushed back out; fine froth | 40–60 dBA |
| **Large** (≳ 10–15 mm; shotgun, rifle exit) | Low: **~1–9 m/s**, falling with hole size (0.5–1 L/s through 12 mm ≈ 4–9 m/s, 15 mm ≈ 3–6 m/s, 25 mm ≈ 1–2 m/s; part of the flow still goes through the trachea); pressure equalises. **Corrected: was ~5–10 m/s** (arithmetic) | Little turbulence; the sound is **sucking and slurping** of blood and air: bubble grains (a 2–8 mm) 400–1,600 Hz | Wet bubbling, blood spray, froth welling from the hole | 35–55 dBA |
| Sealed by a hand or dressing | — | Sound stops; a partial seal can squeak or flutter on expiration | — | — |

- Breath rate 30–40/min, shallow, grunting; the victim can say 1–4 words per breath (§6.6).
- `Recipe SUCKING_WOUND` `[E]`: inspiration noise `NOISE → BP(1–5 kHz)` with gain ∝ (v / 30 m/s)^3 (turbulence power grows steeply with speed), optional whistle `MODE`-free sine at `0.2 v / d` with ±5 % flutter; plus `CLOUD` of bubbles ∝ blood in the wound; expiration: bubble cloud + film pops.

### 5.5 Open airway in the neck (cut throat, laryngeal or tracheal wound)

- **All the tidal air passes through the wound**: 0.5–2 L/s through 1–5 cm² gives **1–20 m/s**, heard as a **rushing or hissing** 0.5–3 kHz on both phases `[K] (H)` physics, `[E]` values. **Corrected: was 2–30 m/s** (arithmetic: 0.5 L/s ÷ 5 cm² = 1 m/s; 2 L/s ÷ 1 cm² = 20 m/s). A wide, gaping cut throat (≥ 3–5 cm²) therefore mostly bubbles and sucks rather than hisses; a narrow stab into the trachea hisses.
- Blood is always present: loud **bubbling and sucking**, frothy pink blood sprayed from the wound with each cough or forced expiration (0.5–1.5 m) `[R2-04 §2.5]`.
- **Voice** (§7.2): a wound below the vocal cords makes the victim **aphonic** (mouths words; air bubbles and hisses at the neck instead). A wound above the cords (through the thyrohyoid membrane or pharynx) lets a weak, wet, bubbly voice out through the wound. ✓ verified [K] (H) for an **open** (gaping) wound: the air leaves before it reaches the glottis, exactly as with an uncapped tracheostomy. Nuance added: a small or partly closed tracheal puncture leaks only part of the air and leaves a **weak, breathy voice** plus crackling surgical emphysema in the neck; occluding the hole (a hand, the chin flexed onto it, clot) restores a weak voice.
- Aspiration of blood killed **36.5 %** of the cut-throat victims in one 74-case autopsy series (exsanguination ~50 %) `[S8]`. Expect gurgling and wet coughing from the first breaths. ⚠ Not re-verified (paper unreachable in this session and in the R2-04 fact-check); arithmetic consistent (27/74 = 36.5 %, 37/74 = 50 %). A fatal autopsy series over-represents deep cuts through the airway, so do not read it as the risk for every neck cut.

### Simulation parameters (breathing sounds)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `breath_gain_exp` | 1.0 (0.9–1.0) | exponent on flow (amplitude) | Power ∝ flow^1.75–2 → **+5–6 dB per doubling of flow** | [K; M4] (M) ✓ consistent with recall |
| `breath_ref_level` | nose 20; mouth 25 at 0.5 L/s | dBA at 1 m | | [E] (M) |
| `route_mouth_when` | tidal > 1 L OR RR > 25 OR pain OR nose blocked OR unconscious with jaw open | rule | | [K] (M), [E] |
| `F1_from_jaw` | `300 + 17 × jaw_mm` (250–1,000) | Hz | Also used by VoiceSynth | [E] |
| `snore_f0` | 30–120 | Hz | Palatal; tongue-base adds 0.5–2 kHz noise | [K] (M–L) |
| `stridor_f` | 250–1,000 (default 500–800), ×(0.8–1.2) with flow | Hz | 3–6 harmonics. Default added by the fact-check | [K] (M–L), [E] |
| `gurgle_lambda` | `40 × flow × min(fluid/20 mL, 1)` | bubbles/s | Audible from 5–10 mL | [E] |
| `gurgle_bubble_radius` | 1–5 (rattle 3–8) | mm | | [E] |
| `crackle_2cd` | fine < 10; coarse > 10 | ms | | [K; M5] (H) ✓ verified [K] |
| `splint_cutoff` | 40–70 % of planned volume; catch 50–150 ms | — | Rib or abdominal pain | [E] |
| `sob_hitches` | 3–6 at 4–8/s, 60–150 ms each | — | | [K] (M), [E] |
| `sucking_small_v` / `large_v` | 20–50 / **1–9** | m/s | Hiss/whistle vs slurp/bubble. Corrected: large was 5–10 | [K] (H), [E] |
| `whistle_f` | `0.2 × v / d` | Hz | Strouhal ~0.2 | [K] (H) |
| `neck_airway_v` | **1–20** | m/s | Rushing 0.5–3 kHz + bubbling. Corrected: was 2–30 | [E] (arithmetic) |
| `cough_spl_1m` | 65–85 | dB peak | | [E] (L) |

### Visual/behavioural checklist (breathing sounds)
- The loudness of breathing tracks effort: silent at rest, audible panting in fear, faint rapid breathing in deep shock.
- Pain breathing: hold, then hiss out through the teeth; a catch and a grunt when a broken rib is moved.
- Supine and unconscious: snoring. Blood in the throat: every breath gurgles and bubbles form at the lips.
- A crowing noise on each breath in: the airway is narrowing at the larynx. If it goes quiet while the chest still heaves, the airway has closed.
- A small hole in the chest whistles or hisses when the victim breathes in; a big hole slurps, bubbles and spits pink froth.
- A cut throat through the windpipe: air roars and bubbles at the neck; the victim mouths words without a voice.
- Agonal gasps are snorts, not sighs. The death rattle belongs to hours-long dying only.

---

## 6. Voice: source, filter and the vocalisation catalogue

### 6.1 Source–filter model: parameters

| Parameter | Normal adult values | Change with pain, fear, exhaustion | Tag |
|---|---|---|---|
| **F0** | Male 85–155 Hz (mean ~115); female 165–255 Hz (mean ~200) | Rises with arousal and pain (screams 300–1,000+ Hz male; §6.3); falls and narrows with exhaustion | [K] (H), `[R2-02 §9.2]` |
| F0 vs subglottal pressure | +2–6 Hz per cmH₂O | Loud voice is higher-pitched | [K; M7] (M) ✓ consistent with recall |
| **Subglottal pressure `Ps`** | Threshold ~3; soft 3–5; conversational 5–10; loud 10–20; shouting 20–40; screaming 30–60 cmH₂O | Limited by respiratory muscle power, lung injury and perfusion (§6.5) | [K; M7] (M). ✓ plausible [K] (M): phonation threshold ~3 cmH₂O and conversational 5–10 cmH₂O are textbook; loud singing reaches 40–60 cmH₂O; no direct measurement of screaming was located. Note: healthy maximal expiratory pressure is ~100–200+ cmH₂O, so the 30–60 cmH₂O a scream needs is a small fraction of it |
| **SPL vs `Ps`** | **+8–9 dB per doubling of `Ps`** | — | [K; M7] (M) ✓ verified [K] (M–H): the Titze & Sundberg figure of roughly 8–9 dB per doubling (SPL ∝ Ps^~1.5 in pressure) is the standard value; not re-opened |
| Open quotient (OQ) | 0.5–0.7 (modal) | Breathy 0.7–0.8; pressed (effort, strain) 0.3–0.4 | [K] (M) |
| Source spectral tilt | ~−12 dB/oct (modal) | Breathy −15 to −18; loud or pressed −6 to −9 (loud voices are brighter) | [K] (M) |
| Jitter / shimmer | < 1 % / < 3–5 % | Up to 3–5 % / 10 % in pain, fear, fatigue, hoarseness | [K] (M) |
| HNR | > 20 dB | 10–15 breathy or rough; < 10 markedly abnormal; < 5 wet or whispery | [K] (M) |
| **Formants** (male averages; female ×1.15–1.2) | /ɑ/ 730, 1,090, 2,440; /i/ 270, 2,290, 3,010; /u/ 300, 870, 2,240; /ʌ/ 640, 1,190, 2,390; neutral ~500, 1,500, 2,500 Hz | Wide-open scream vowel: F1 900–1,200 Hz; F0 can exceed F1 | [K; M6] (H) |
| Formant spacing from vocal-tract length `L` | Uniform tube: `Fn ≈ (2n − 1) c / 4L` (L = 17.5 cm → ~490, 1,470, 2,450 Hz) | Lowered larynx in roars: formants −10–15 % | [K] (H) |
| Bandwidths | B1 60–100, B2 80–120, B3 100–180 Hz | ×1.5 with an open (breathy) glottis | [K] (M) |
| Nasal coupling | Off except nasals | Moans with closed lips: nasal pole ~250–300 Hz, zero ~0.8–1.5 kHz | [K] (M) |
| Maximum phonation time (one breath) | Male 25–35 s; female 15–25 s | 2–8 s in shock, chest injury, dyspnoea | [K] (M) |

**Nonlinear phenomena (NLP)** are what make pain and terror vocalisations sound unlike speech `[K] (M)`:
- **subharmonics / period doubling**: alternate glottal pulses differ; a rough "growl" at F0/2;
- **biphonation**: two independent pitches at once;
- **deterministic chaos**: voiced but irregular and noisy ("harsh", "rasping");
- **frequency jumps**: sudden F0 breaks by 20–50 %;
- **roughness**: fast amplitude modulation at **30–150 Hz**, the acoustic signature that makes screams alarming (normal speech modulates at 4–5 Hz) `[S2]`. ✓ verified [K] (H): Arnal et al. 2015 define the scream-specific "roughness" niche as temporal modulations of ~30–150 Hz (also used by alarm signals), versus the ~4–5 Hz syllabic modulation of speech; the same value was fact-checked in `[R2-02 §9.2]`.

NLP become more frequent as **emotional intensity** rises (rather than with negative valence as such) `[K; M15] (M)`; in pain vocalisations, F0, F0 range, loudness and NLP all rise with pain intensity `[S3]`. A person's pitch is individual and is preserved from speech through screams, roars and pain cries `[S3]`. ✓ verified [K] (M) (Raine, Pisanski, Simner & Reby, *Bioacoustics*; Pisanski, Raine & Reby, *R Soc Open Sci* 2020, whose title states the pitch-preservation finding). **Caveat added:** both studies used **acted (simulated)** pain vocalisations and screams by volunteers, and pitch is preserved as a **correlation across people** (a higher-voiced person tends to scream higher), not as a fixed ratio for each person. The childbirth study `[S3]` is the only real-pain sample among them.

### 6.2 Vocalisation catalogue

Male values; female F0 ×1.7–2 of her own speaking F0 (§6.3 formulas do this automatically); formants ×1.15–1.2. Levels dB SPL at 1 m `[E]` (L–M) anchored on the speech levels in §1.3.

| Vocalisation | Trigger | Duration | F0 contour (male) | Voice quality | Mouth / F1 | Level | Breath coupling | Tag |
|---|---|---|---|---|---|---|---|---|
| **Startle yelp** | Sudden unexpected hit or pain | 150–400 ms | 150 → 300–600 Hz in 30–80 ms, then falls | Tense; some NLP | Mid-open, F1 600–800 | 75–95 | Interrupts breathing | `[R2-02 §9.2]` [E] |
| **Impact grunt** ("uh", "oof") | Blow to the trunk, landing, being shot | 80–250 ms | 90–150 Hz, flat or falling; often creaky (fry pulses 30–70 Hz) | Abrupt glottal onset; HNR 5–12 dB | Half-closed, F1 400–550 | 65–85 | Forced expiration | [K] (M), [E] |
| **Effort/strain grunt** ("nnngh") | Pushing up, crawling, pulling, pressing a wound | 0.2–1.5 s | 100–200 Hz | Pressed (tilt −6 to −9 dB/oct); nasal if lips closed | Lips closed or teeth clenched, F1 300–450 | 55–75 | Breath-hold (Valsalva) then release | [K] (M) |
| **Hiss through teeth** | Moderate sharp pain (touching a wound, bone moved) | 0.3–2 s | Voiceless | Sibilant noise 3–8 kHz | Teeth clenched (AU31), lips drawn back | 45–65 | Expiration after a breath-hold | [K] (M) |
| **Pain cry / yell** ("aah!") | Severe acute pain | 0.5–2 s | 200–350 → 400–700 Hz, falling 30–50 % at the end | NLP 10–40 % of duration | Open, F1 700–1,000 | 85–100 | One per breath | `[S3]` [E] |
| **Scream** (pain or terror) | Extreme pain (burns, bone, eye), terror | 0.8–3 s | 300–500 → **500–1,000+ Hz**, sustained with fluctuation, then falling | **Roughness AM 30–150 Hz**; NLP 30–70 % | Jaw wide, F1 900–1,200; square mouth (§8) | 90–105 | One per breath; loud **inhalation gasp 0.3–0.8 s** between screams | `[S2]` `[S3]` [E] |
| **Roar / angry shout** (fighting back) | Aggression, defiance | 0.5–2 s | 180–350 Hz (lower than a scream) | Harsh (chaos 30–60 %); lowered larynx | Open, F1 700–900; formants −10–15 % | 85–100 | One per breath | [K] (M), [E] |
| **Wail** | Sustained severe pain, despair | 1–4 s | 250–450 Hz, slowly falling, fluctuating 4–7 Hz | Breathy, tremulous | Open-mid, F1 600–900 | 70–90 | With sobs | [K] (M) |
| **Moan / groan** | Sustained pain; stupor (GCS V2); passive in the lightly unconscious | 0.5–2.5 s | 90–180 Hz, flat, falling 10–30 % at the end; fry at the end | Breathy, HNR 5–15 dB | Closed "mmm" (nasal, F1 ~250–300) or half-open "uhh/ohh" (F1 400–550) | 45–70 | One per expiration, every 1–5 breaths | `[R2-01 §5.2]` [K] (H) |
| **Whimper** | Moderate sustained pain, fear, exhaustion | Bursts 0.1–0.5 s, 2–6 per breath | 250–600 Hz, rise–fall | Breathy, nasal, falsetto-like | Lips nearly closed | 35–60 | On both phases | [K] (M) |
| **Sob** | Crying | §5.2 | Wail or moan on expiration | — | — | 50–75 | Inspiratory hitches | [K] (M) |
| **Pleading, talking in distress** | Conscious, threat present | Speech | F0 +20–60 % over baseline, range ×1.5 | Tremor, voice breaks | Speech | 65–85 | Short breath groups (3–8 syllables) | [K] (M), [E] |
| **Gasping speech** (air hunger) | Lung, airway, tension, class III | 1–4 words per breath | Raised | Breathy | — | 55–75 | Each phrase ends with a gasp | [K] (H) |
| **Wet / gargled voice** | Any vocalisation with fluid in the larynx or pharynx | — | Unstable | HNR < 5 dB; bubbling AM | — | −3 to −6 dB | Stops to spit or cough every 5–30 s | `[R2-04 §2.5]` [K] (H) |
| **Epileptic cry** | GTC onset: tonic contraction forces air through closed cords | 0.5–3 s | 150–400 Hz | Strangled, harsh; not intentional | Clenched | 70–90 | Then apnoea | `[R2-04 §4]` |
| **Passive (agonal) groan** | Expiration past relaxed cords: unconscious, agonal, dead body pressed | 0.3–1.5 s | 70–110 Hz | Very breathy, fry | Slack open | 40–60 | Passive | `[R1-04 §12.1]` [K] (M) |
| Retch ("hurk") | Nausea `[R2-04 §2.7]` | 0.3–0.8 s per cycle | Strained, partly voiced | Gagging, glottal | Open | 60–80 | Closed glottis | [K] (M) |
| Hiccup | §5.2 | — | — | — | — | — | — | `[R2-04 §2.8]` |

### 6.3 Pain and arousal → vocal parameters `[E]` (anchored on `[S2]` `[S3]`)

With pain `p` on 0–10 (as `[R2-02]`), speaking F0 `F0s` and a per-character `expressivity` `x` (0.3–1.5, default 1):

| Output | Formula / rule | Notes |
|---|---|---|
| P(vocalise) per pain spike | `clamp(0.15 × (p − 2), 0, 0.95) × x` | × 0.5 in "fighter" mode; × 0.5 at shock class III; × 0.2 at class IV; 0 when winded or apnoeic. **Gap added (myth guard "everyone screams when shot")**: × 0 while the character is **unaware of the hit** (`unaware_p` 0.3–0.5 under high arousal for gunshots, 0.3–0.6 for stabs to the torso `[R2-02 §2.4]`), and the pain spike of a gunshot or stab is applied **when the wound is discovered**, not at impact. Many shot people are silent, grunt, or say "I'm hit"; screaming is most likely with fractures under load, burns, eye or genital wounds and after the wound is seen `[R2-02 §14 row 15]` |
| Type | p < 4: hiss, grunt, moan · 4–7: yell, cry, moan, whimper · ≥ 7 with high arousal: scream · ≥ 7 with low arousal (shock, exhaustion): moan, whimper · burns: prolonged screaming | Arousal from `[R2-02]` |
| Peak F0 | `F0s × (1.3 + 0.45 × p)`, cap ×9 | p = 10 → ×5.8 (male ~670 Hz) |
| NLP fraction | `0.05 + 0.06 × p` | p = 10 → 0.65 |
| Roughness | depth `0.6 × max(0, (p − 5) / 5)`, rate 30–150 Hz (default 70, per utterance) | `[S2]` |
| Level (before the budget) | `60 + 4.5 × p` dB SPL at 1 m | p = 10 → 105 |
| Duration | `0.3 + 0.2 × p` s, capped by the breath budget | p = 10 → 2.3 s |
| Repetition | One per breath; next after an inhalation gasp of 0.3–0.8 s | `[R2-02 §9.2]` |
| Pain face | Synchronised: the vocalisation opens the mouth (AU25–27) on top of the pain AUs (§8) | — |

### 6.4 Individual variation (per character, rolled once)

| Trait | Distribution | Effect | Tag |
|---|---|---|---|
| Speaking F0 | Male N(115, 17) Hz; female N(200, 25) Hz | All vocal F0s scale from it | [K] (H), [S3] |
| Vocal-tract length | Male 16–18 cm; female 14–15 cm | Formant scale ∝ 1/L | [K] (H) |
| Expressivity `x` | 0.3–1.5 (lognormal, median 1) | P(vocalise), level | [E] |
| Pain "vocabulary" | Preference weights: moaner, yeller, hisser, silent | Type selection | [E] |
| Baseline breathiness | HNR 15–25 dB | Voice quality | [K] (M) |
| Language and lines | From the game's line set | §7 processing | [E] |

### 6.5 Physiology limits: the voice budget `[E]` unless tagged

A voice needs airflow, pressure and a working larynx. The budget caps every vocalisation.

⚠ Fact-check note on the mechanism `[K]` (M): the class III–IV caps below are sound as game values, but the limit is **not mainly the subglottal pressure**. Even a shocked adult's expiratory muscles can briefly exceed the 30–60 cmH₂O a scream needs. What removes loud screaming in haemorrhage is falling consciousness and drive (class III anxious-confused, class IV lethargic), air hunger with short breath groups, and weakness from hypoperfusion. Keep the caps; gate them on consciousness and breath budget as well as blood loss.

| Condition | Max level (dB SPL at 1 m) | Max duration per breath | Other changes | Tag |
|---|---|---|---|---|
| Uninjured, aroused | 105 | 3 s | — | [E] |
| Blood loss 15–30 % (class II) | 100 | 2.5 s | F0 slightly raised; faster speech | `[R1-03 §3]` [E] |
| **Blood loss 30–40 % (class III)** | **85–90** | 1–1.5 s | HNR 10–15 dB; speech 2.5–4 syll/s; breath groups 4–8 syllables; slurred, repetitive `[R1-04 §7.2]`; F0 range ×0.5 | `[R1-04 §7.2]` [E] |
| **Blood loss > 40 % (class IV)** | **≤ 65** (moans, whispers) | 0.5–1 s | HNR 5–10 dB; single words then moans | `[R1-04 §7.2]` [E] |
| LOC, apnoea | 0 | — | Only passive groans | `[R2-04 §1]` |
| SpO₂ < 85 % / < 75 % | −10 / −20 dB | ×0.6 / ×0.4 | Slurred, slow (2–3.5 syll/s) | [E] (L) |
| Open pneumothorax, haemothorax, flail chest | −6 to −12 dB | 0.3–1 s | Grunting; 1–4 words per breath | `[R2-02 §9.2]` [E] |
| Diaphragm weak (C3–C5) | −10 to −20 dB | 1–3 words | — | `[R1-04 §6]` [E] |
| C1–C3 cord, tracheal wound below the cords | 0 (aphonic) | — | Mouths words | `[R1-04 §6]` [K] (H) |
| Winded (solar plexus) | 0 for 3–15 s | — | Then gasping speech | `[R2-02 §6.5]` |
| **Fatigue**: > 60–180 s of screaming within 10 min | −3 to −6 dB | — | Hoarse: jitter ×3, shimmer ×2, HNR −6 dB, F0 −10–20 %, voice breaks p 0.1–0.3 per utterance | [E] (L) |
| Shivering, cold | — | — | Voice trembles with the shiver bursts; teeth-chatter clicks between words `[R2-04 §6]` | [E] |
| Fear | — | — | F0 tremor 4–8 Hz, ±2–5 %; voice breaks | [E] (L) |

**GCS verbal score → vocal generator** `[R2-01 §19]` `[K] (H)`: V5 oriented speech (limited by the budget); V4 confused speech (§7.1 CONFUSED); V3 inappropriate words, often shouted; V2 moans and groans only; V1 nothing.

### 6.6 Recipe `VoiceSynth` and the recommended hybrid

**Procedural voice** (written for this document; approach as in parametric nonverbal-vocalisation synthesisers such as the one described in `[K; M15]`, and classic formant synthesis `[K; M35]`):
1. **Source**: glottal flow pulses (Rosenberg or LF shape `[K; M24]`) at `F0(t)` from a contour template (rise–plateau–fall for screams; flat–fall for moans; rise–fall for whimpers; falling for grunts). Add jitter and shimmer; aspiration noise gated to the open phase at a level set by HNR; OQ and tilt by voice quality.
2. **NLP injection** over the fraction of the utterance chosen in §6.3, in random 50–400 ms segments:
   - subharmonics: scale every second pulse by `1 − d` (d 0.2–0.5);
   - roughness: `AM(30–150 Hz, depth)`;
   - chaos: random walk on the pulse period (σ 5–15 % per period) plus extra aspiration noise;
   - frequency jumps: step F0 by ×1.2–1.5 or ×0.7 for 50–300 ms.
3. **Filter**: five cascade formants; F1 from jaw opening (§5.3 formula), F2 from lip and tongue shape, F3–F5 from vocal-tract length; bandwidths widened with breathiness; optional nasal branch for closed-mouth moans and whimpers.
4. **Radiation**: +6 dB/oct (first difference).
5. **Budget and coupling**: clip level and duration to §6.5; the utterance occupies the expiration of the current `BreathSynth` breath, and the next inhalation is a gasp when the previous utterance was ≥ 1 s at ≥ 85 dB.
6. **Damage processing**: §7.3.

**Recommended hybrid** `[E]`:
- Fully procedural synthesis is convincing for **grunts, moans, groans, whimpers, sobs, hisses, gasps, snoring and gurgling**, and it follows physiology perfectly.
- Procedurally synthesised **screams, crying and words** tend to sound artificial. Record a small library of **real nonverbal pain and fear vocalisations and pleading lines** per voice type (with actors, never from real incidents), then drive **procedural processing** from physiology: pitch shift (±3 semitones to the character's F0), formant shift (vocal-tract length), level and tilt (subglottal pressure), breathiness (aspiration noise + low-pass), roughness (AM 30–150 Hz), wetness (bubble layer), tremor, granular time-stretch (0.7–1.3×) and truncation by the breath budget with a following gasp.

### Simulation parameters (voice)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `spl_per_ps_doubling` | 8–9 | dB | | [K; M7] (M) ✓ verified [K] |
| `f0_per_cmH2O` | 2–6 | Hz | | [K; M7] (M) |
| `ps_by_effort` | soft 3–5; talk 5–10; loud 10–20; shout 20–40; scream 30–60 | cmH₂O | | [K; M7] (M) |
| `scream_f0_male` / `female` | 500–1,000+ / 800–2,000 peak | Hz | Derived from own F0 | `[R2-02 §9.2]` [S3] [E] |
| `scream_roughness` | 30–150 | Hz AM | | [S2] ✓ verified [K] (H) |
| `scream_spl_1m` | 90–105 (default 98; rare characters to 110) | dB | | [K] (L–M) ⚠ plausible |
| `moan_f0_male` / `spl` | 90–180 / 45–70 | Hz / dB | | [K] (M), [E] |
| `whimper_f0_male` / `spl` | 250–600 / 35–60 | Hz / dB | | [K] (M), [E] |
| `grunt_dur` / `f0` | 80–250 / 90–150 | ms / Hz | | [K] (M) |
| `inhale_gasp_between_screams` | 0.3–0.8 | s | | [K] (M) |
| `voice_budget_by_class` | I 105; II 100; III 85–90; IV ≤ 65; LOC 0 | dB SPL at 1 m | | [E] on `[R1-04 §7.2]` |
| `nlp_fraction` | `0.05 + 0.06 × pain` | — | | [E] on [S3] |
| `expressivity` | 0.3–1.5 | × | Per character | [E] |
| `hoarse_after_scream_s` | 60–180 | s cumulative in 10 min | | [E] (L) |
| `max_phonation_time` | normal 25–35 (M) / 15–25 (F); distressed 2–8 | s | | [K] (M) |

### Visual/behavioural checklist (voice)
- Screams are rough, grating and harsh, not sung; each lasts one breath and is followed by a ragged gasp.
- The same character's screams, moans and speech share an obviously related pitch.
- As blood is lost, the voice goes from shouting and pleading to short, breathy, slurred phrases, to moans, to silence.
- A chest-wounded victim can only manage short, weak cries and a few words per breath.
- Grunts on impacts; hisses through the teeth when a wound is touched; moans in the half-conscious.
- After minutes of screaming the voice cracks and turns hoarse.

---

## 7. Speech after brain, face, jaw, tongue, larynx and chest injury

### 7.1 Brain injury: acoustic profile per vocal state

States as in `[R2-01 §5.2]`. Normal speech runs at **4–6 syllables/s** (≈ 150–190 words/min) with phrase pauses of 0.2–0.8 s `[K] (H)`. ⚠ Clarified: 150–190 words/min at ~1.4 syllables per word is **~3.5–4.5 syll/s overall** (pauses included); 4–6 syll/s is the **articulation rate** within runs of speech. Use 4–6 for the synthesiser within phrases and the words/min figure for overall pacing.

| Vocal state | Rate | Pauses | Prosody | Articulation | Voice | Other | Tag |
|---|---|---|---|---|---|---|---|
| `DYSARTHRIC_UMN` (unilateral, mild) | 3–5 syll/s | Normal | Normal | Mildly imprecise consonants | Normal | With contralateral lower-face weakness (§9) | [K] (M) |
| `DYSARTHRIC_UMN` (bilateral, spastic) | 2–3 | Short phrases | **Monopitch, low pitch** (F0 range ×0.4) | Imprecise | **Strained-strangled** (pressed, low HNR); hypernasal | — | [K; M9] (H) |
| `DYSARTHRIC_CEREBELLAR` (ataxic) | 3–4 | Irregular | **Scanning: excess and equal stress** on every syllable | **Irregular articulatory breakdowns** | **Explosive loudness** (±6–10 dB syllable to syllable) | Vowels prolonged | [S10] [K; M9] (H). ✓ verified [K] (H): the Mayo (Darley, Aronson & Brown) ataxic cluster is articulatory inaccuracy, prosodic excess (excess and equal stress) and phonatory-prosodic insufficiency; "scanning" and "explosive" speech are the classic bedside terms. The ±6–10 dB figure is `[E]` |
| `DYSARTHRIC_BULBAR` (flaccid) | 3–4 | Frequent breaths | Reduced | Weak consonants; **audible nasal air escape** on /p b s/ | **Breathy** (HNR < 10 dB), hypernasal, wet | Weak cough; 3–5 syllables per breath | [K; M9] (H) |
| `NONFLUENT` (Broca) | **≈ 10–50 words/min overall (≈ 0.25–1.2 syll/s including pauses)**; within short runs ~1–3 syll/s | **Long, 1–5 s**, with groping ("uh… m-m…") | Flattened | Phonetic distortions, effortful | Normal | **Telegraphic**; automatic phrases (swearing, "yes", "no") at normal speed | [S12] [K] (H). ✓ verified [K] (H) for the words/min figure (the classic fluent/non-fluent boundary is < 50 words/min for non-fluent speech). **Corrected: was "0.5–2 syll/s (≈ 10–50 words/min)"**, which did not convert: 10–50 words/min × ~1.4 syll/word = 0.23–1.2 syll/s |
| `JARGON` (Wernicke) | 4–6+ (can be pressured) | Normal | **Normal intonation** | Fluent; neologisms and paraphasias | Normal | Does not stop or self-correct; does not follow commands | [S11] (H) ✓ verified [K] (H): fluent, normal prosody, paraphasias and neologisms, poor comprehension, often unaware of the errors |
| `GLOBAL` | — | — | Expressive intonation on a stereotypy | — | — | Mute, or one **recurring utterance** of 1–3 syllables | [K] (H) |
| `MUTE_AKINETIC` | — | — | — | — | — | Silent; rarely a whispered monosyllable after 5–30 s | [S16] [E] |
| `CONFUSED` (GCS V4: concussion, hypoxia, class III, frontal) | 3–5 | Slow responses, latency 1–5 s | Flat | Normal to mildly slurred | Normal to quiet | **Repetitive questions** every 30–120 s ("What happened?"); perseveration; wrong answers about place and time | [K] (H) |
| `INAPPROPRIATE` (V3) | Bursts | — | Exclamatory | Clear words | Often shouted | Random words; no exchange | [K] (H) |
| `SLURRED_SHOCK_HYPOXIC` | 2–3.5 | Longer | Reduced range | Slurred like intoxication | Quiet, breathy | — | [K] (M), [E] |
| Pseudobulbar affect (bilateral UMN) | — | — | — | — | — | Involuntary crying or laughing bursts of 5–60 s, unrelated to mood | [K] (M) |
| `MOAN_ONLY` (V2), `SILENT` (V1) | — | — | — | — | — | §6 | `[R2-01 §5.2]` |

- **Pain vocalisation survives aphasia** `[R2-01 §5.2]`: screams, moans and cries are brainstem and limbic; a left-hemisphere wound takes words, not screaming.

### 7.2 Structural injury: what cannot be said

| Injury | What changes | Sounds lost or distorted | Voice | Extra | Tag |
|---|---|---|---|---|---|
| **Unilateral mandible fracture** | Mouth opening limited by pain to **10–25 mm** (normal 40–55 mm interincisal) | F1 capped ~600 Hz; everything muffled; careful, slow | Normal | Drools blood; holds the jaw | [K] (M) |
| **Bilateral mandible fracture / flail front jaw** | Lips and teeth cannot close; tongue falls back | **/p b m f v/ weak or absent**; vowels centralised (F1/F2 range compressed 30–50 %) | Normal larynx, wet | **Airway risk when supine**; leans forward drooling `[R2-04 §2.5]` | [K] (H) |
| **Mandible shot away** | No lower jaw, lips or tongue tip support | Almost all consonants gone; vowels only, fixed open (F1 700–900 Hz) | Larynx intact: **can still moan and scream** | Massive bleeding and drooling; tongue may fall back or hang | [K] (H) |
| Lip loss or laceration | — | /p b m f v w/ lost; rounded vowels (/u o/) unrounded | Normal | Drooling | [K] (H) |
| **Tongue laceration or swelling** | Swelling peaks over 30–120 min | "**Hot-potato**" voice: F2 lowered and compressed, output low-passed ~2–2.5 kHz; /t d n l s z ʃ k g/ distorted | Muffled | Airway risk | [K] (M), [E] timing |
| Front teeth lost | — | **Lisp**: /s z/ peak moves from ~4–8 kHz to a broader ~2.5–5 kHz; /f v θ/ affected | Normal | Whistling /s/ possible | [K] (M) |
| Nasal fracture with blood or clot | Nose blocked | **Hyponasal**: /m n ŋ/ → /b d g/; nasal murmur gone | Normal | Mouth breathing, wet snorting | [K] (H) |
| Midface (Le Fort) or palate split | Mouth and nose connected | **Hypernasal** with nasal air escape on pressure consonants | Normal | Blood from nose and mouth | [K] (H) |
| Facial nerve palsy (peripheral) | Paralysed lip corner | Bilabials weak (air leaks at the corner); slight slur | Normal | Drools on that side (§9) | [K] (H) |
| **Larynx fracture or haematoma** | Cords swollen, displaced | — | **Hoarse → breathy → aphonic** (whisper only) as swelling grows over 10–60 min | **Stridor**; painful speech; haemoptysis; crackling emphysema in the neck | [K] (H), [E] timing |
| Unilateral recurrent laryngeal nerve cut (neck wound) | One cord paralysed | — | Breathy, hoarse, weak; **diplophonia** (two pitches) sometimes | Weak cough; aspiration | [K] (H) |
| Bilateral recurrent laryngeal nerve cut | Cords near midline | — | Near-normal but weak | **Inspiratory stridor**, air hunger | [K] (H) |
| **Tracheal or laryngotracheal wound below the cords** | Air escapes before the cords | Everything | **Aphonic**: mouths words (open wound); weak, breathy voice if the hole is small or partly closed | Hiss and bubbling at the wound with each attempt; covering the hole restores a weak voice | [K] (H) ✓ verified [K] (H), nuance added |
| Cut throat above the cords (thyrohyoid, pharynx) | Voice partly exits through the wound | Articulation bypassed | Weak, wet, bubbly | Gurgling, aspiration `[S8]` | [K] (M) |
| Open chest wound, haemothorax, flail chest | Breath limited | — | Short phrases of 1–4 words, −6 to −12 dB | Grunting | `[R2-02 §9.2]` [K] (H) |
| Blood in mouth or throat | — | — | Gargled, wet | Spits every 5–30 s | `[R2-04 §2.5]` |

### 7.3 Processing chains (for recorded lines or the procedural voice) `[E]`

| Effect | Chain |
|---|---|
| Slurred (UMN dysarthria, shock, hypoxia) | Time-stretch 1.2–2.0×; soften consonant bursts (−6 dB, `LP 3 kHz` on transients); move F2 20–40 % toward the neutral vowel; add breathiness |
| Strained-strangled | Tilt −6 dB/oct, HNR −6 dB, F0 range ×0.4, rate ×0.6 |
| Scanning (ataxic) | Equalise syllables to 250–400 ms each; random loudness ±6–10 dB per syllable; occasional consonant dropouts |
| Hypernasal / nasal air escape | Add nasal pole 250–300 Hz and zero 0.8–1.5 kHz; add `BP 2–5 kHz` noise bursts on plosives and fricatives |
| Hyponasal | Notch 250–300 Hz on nasal segments; replace /m n/ onsets with /b d/-like bursts |
| Hot potato | `LP 2–2.5 kHz`, F2 ×0.8, F1 +10 % |
| Jaw immobile / destroyed | Cap F1 at 600 Hz (immobile) or fix it at 700–900 Hz (destroyed); replace bilabial segments with glottal stops or silence |
| Lisp | Shift /s/ energy peak down ~40 % and broaden it |
| Breathy / hoarse | Aspiration noise at HNR 5–10 dB; jitter 2–5 %; shimmer 6–12 %; tilt −15 to −18 dB/oct |
| Aphonic | Replace the voiced source with noise (whisper), −20 dB; add the neck-wound hiss if relevant |
| Wet | Bubble cloud following the syllable envelope; F0 perturbation 5 %; spit or cough every 5–30 s |
| Non-fluent (Broca) | Drop function words; insert 1–5 s pauses with groping sounds; keep swear words and stock phrases intact and fluent |
| Jargon (Wernicke) | Replace 30–70 % of content words with pseudo-words following the language's syllable pattern; keep prosody and speed |
| Confused | Line selection: repeat the same question every 30–120 s; 1–5 s response latency |

### Simulation parameters (speech after injury)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `speech_rate_normal` | 4–6 articulation; ~3.5–4.5 overall | syll/s | | [K] (H) ✓ (clarified) |
| `speech_rate_broca` | **0.25–1.2 overall** (runs 1–3) | syll/s | Pauses 1–5 s; 10–50 words/min. Corrected: was 0.5–2 | [K] (H), [S12] |
| `speech_rate_spastic` / `ataxic` / `shock` | 2–3 / 3–4 / 2–3.5 | syll/s | | [K; M9] (M), [E] |
| `ataxic_loudness_jitter` | ±6–10 | dB per syllable | | [S10] [E] |
| `confused_repeat_interval` | 30–120 | s | | [E] on [K] |
| `mouth_opening_normal` / `fracture` | 40–55 / 10–25 | mm | Caps F1 | [K] (M) |
| `tongue_swelling_peak` | 30–120 | min | Hot-potato ramps up | [E] |
| `larynx_swelling_to_aphonia` | 10–60 | min | Stridor rises in parallel | [E] (L) |
| `aphonic_if` | tracheal wound below cords OR C1–C3 OR apnoea | rule | Mouths words | [K] (H) |

### Visual/behavioural checklist (speech after injury)
- A left-side head wound: screaming intact, words gone or replaced by fluent nonsense.
- A cerebellar wound: loud-soft-loud syllables of equal length, like someone badly drunk.
- A shattered jaw: the victim leans forward drooling blood and makes open vowel sounds but cannot form "p", "b" or "m".
- A broken nose: blocked, "cold-in-the-head" speech.
- A throat wound below the voice box: lips move, no voice, air bubbles at the neck.
- A punch to the larynx: hoarseness that turns to a whisper over minutes, with crowing breaths.

---

## 8. Facial expression: FACS recipes

The core pain face (PSPI) and its timing are in `[R2-02 §9.1]`; lids, jaw and tongue per physiological state are in `[R2-04 §7]`. This section gives the full action-unit (AU) recipes, the blending rules and a rig mapping.

### 8.1 Action units used, with a blendshape mapping

FACS AU names and muscles `[K; M11] (H)`. Blendshape names follow the common 52-shape (ARKit-style) convention `[K] (M)`; "custom" means the convention has no matching shape and one must be sculpted.

| AU | Name | Main muscle | Visible effect | Blendshape (per side where available) |
|---|---|---|---|---|
| 1 | Inner brow raiser | Frontalis, medial | Inner brows up; oblique "worried" brows with AU4 | `browInnerUp` (**split L/R for palsy**) |
| 2 | Outer brow raiser | Frontalis, lateral | Outer brows up | `browOuterUp_L/R` |
| 4 | Brow lowerer | Corrugator, depressor supercilii, procerus | Brows down and together; vertical glabellar furrows | `browDown_L/R` |
| 5 | Upper lid raiser | Levator palpebrae | Eyes wide; sclera visible above the iris | `eyeWide_L/R` |
| 6 | Cheek raiser | Orbicularis oculi, orbital part | Cheeks up, crow's feet, lower lid bulges | `cheekSquint_L/R` |
| 7 | Lid tightener | Orbicularis oculi, palpebral part | Lids tensed and narrowed | `eyeSquint_L/R` |
| 9 | Nose wrinkler | Levator labii superioris alaeque nasi | Nose wrinkled, upper lip up | `noseSneer_L/R` |
| 10 | Upper lip raiser | Levator labii superioris | Upper lip raised, upper teeth shown | `mouthUpperUp_L/R` |
| 11 | Nasolabial deepener | Zygomaticus minor | Deepened nasolabial fold | custom |
| 12 | Lip corner puller | Zygomaticus major | Corners up and back (also in pain grimaces) | `mouthSmile_L/R` |
| 14 | Dimpler | Buccinator | Corners tightened inward | `mouthDimple_L/R` |
| 15 | Lip corner depressor | Depressor anguli oris | Corners down | `mouthFrown_L/R` |
| 16 | Lower lip depressor | Depressor labii inferioris | Lower lip down, lower teeth shown | `mouthLowerDown_L/R` |
| 17 | Chin raiser | Mentalis | Chin boss wrinkled, lower lip pushed up | `mouthShrugLower` |
| 18 / 22 | Lip pucker / funneler | Orbicularis oris | Lips rounded | `mouthPucker` / `mouthFunnel` |
| 20 | Lip stretcher | Risorius, platysma | Lips stretched horizontally ("square mouth" with AU25–27) | `mouthStretch_L/R` |
| 21 | Neck tightener | Platysma | Neck cords | custom |
| 23 / 24 | Lip tightener / pressor | Orbicularis oris | Lips thinned or pressed together | `mouthPress_L/R` (+ `mouthRoll*`) |
| 25 | Lips part | — | Lips apart | small `jawOpen` + `mouthClose` inverse |
| 26 | Jaw drop | Masseter/temporalis relaxed | Jaw hangs open (to ~20 mm) | `jawOpen` 0.2–0.5 |
| 27 | Mouth stretch | Pterygoids, digastric | Jaw pulled wide open (> 25 mm) | `jawOpen` 0.6–1.0 (+ `mouthStretch`) |
| 31 | Jaw clencher | Masseter | Masseter bulge, jaw set | custom |
| 34 | Cheek puff | — | Cheeks puffed (also passive on the paralysed side, §9) | `cheekPuff` (**split L/R**) |
| 38 | Nostril dilator | Nasalis, dilator part | Nostrils flare | custom |
| 41 / 42 / 43 | Lid droop / slit / eyes closed | Levator relaxed; orbicularis | Heavy lids → closed | `eyeBlink_L/R` 0.3 / 0.6 / 1.0 |
| 45 | Blink | — | Blink (§12.2 timing) | `eyeBlink_L/R` pulse |
| 51–58 | Head turns, tilts, up/down | — | Head pose | Neck/head bones |
| 61–64 | Eyes left/right/up/down | — | Gaze | Eye bones |

### 8.2 Expression recipes

AU intensities as FACS letters (A trace … E maximum; weights in §0.3). Lid apertures from `[R2-04 §7.2]`. "Onset/hold" are for a single episode `[E]`.

| State | AUs (intensity) | Eyes and lids | Mouth and neck | Head | Onset / hold | Tag |
|---|---|---|---|---|---|---|
| **Pain, mild** (pain 2–4) | 4B, 6B or 7B, 10A; longer blinks | Narrowed 7–9 mm | Closed or slightly parted | Still | 150–400 ms / 0.5–1.5 s bursts | [S1] [E] |
| **Pain, moderate** (5–7) | 4C, 6C, 7C, 9B, 10C, 43B (brief squeezes), 20B, 25 | Squeezed 3–6 mm | Parted, teeth showing | Turns away or down | as above | [S1] [K; M10] [E] |
| **Pain, severe** (8–10) | 4D–E, 6D, 7D, 9D, 10D, **43 closed**, 20C, 25, 31 between cries, 21C | **Shut** | Teeth bared; jaw clenched between cries | Arched or curled | Bursts every 3–15 s | [S1] [E] |
| **Pain scream** | Severe pain set + **27D + 20D** (square mouth) | **Shut** (the key difference from a fear scream) | Wide square mouth; neck cords | Back or forward | With each scream | [S1] [E] |
| Suppressed pain (stoic, fighter) | 4B, 7B, **24C**, 17B, **31C** | Narrowed | Lips pressed, jaw set | Still | Leaks of full pain face 0.3–1 s | [K; M10] (M), [E] |
| **Fear** | 1C, 2C, 4B, **5D**, 7B, **20C**, 26B, 38B | **Wide 11–12 mm; white above the iris** | Lips stretched horizontally; jaw slightly dropped | Pulled back, chin down | 200–500 ms / sustained while the threat lasts | [K; M11] (H) ✓ verified [K] (H): the FACS Investigator's Guide prototype is 1+2+4+5+7+20+26 (variants 1+2+4+5+20+25/26/27 and 1+2+4+5+25/26/27); AU38 is an addition |
| **Terror scream** | 1D, 2D, 4C, **5E**, 20D, 27D, 21D, 38C | **Wide open**, fixed on the threat | Wide, stretched | Back | With each scream | [K; M11] [E] |
| Startle (first 0.3 s) | 45 (blink at ~30 ms), 4B, 7C, 20C, 21C | Blink then wide | Stretched | Head down, shoulders up | 30–300 ms | `[R2-02 §1]` [K] |
| Surprise (unhurt, e.g. a miss) | 1C, 2C, 5B, 26B | Wide | Dropped jaw | Back slightly | < 1 s | [K; M11] (H) |
| **Circulatory shock** (class III) | All expression AUs ≤ A; **41–42**; **25, 26B** (open-mouth breathing); 38B with air hunger | **5–8 mm, heavy; eyes look sunken**; slow blinks (300–500 ms) | Open, dry, pale lips | Lolling, poor head control | Sustained; pain grimace when moved at ×0.3–0.6 | `[R2-04 §7.1]` [K] (M) |
| **Dazed / concussed** | Near-neutral; 26A; occasionally 1B + 4A when addressed | "**Blank or vacant look**"; slow, few saccades | Slightly open | Slow, unsteady | Seconds to minutes | [S6] [K] (M) |
| **Confused** (hypoxia, delirium, head injury) | 1B + 4B (puzzled), 7A, 24A | Wandering gaze, 1–3 saccades/s | Slightly parted | Tilted 5–15° | Waxes and wanes | [K] (M), [E] |
| Anger, defiance | 4D, 5C, 7C, 23C or 24C | Glaring | Lips pressed or thinned | Forward | — | [K; M11] (H) |
| **Roar** (fighting back) | 4D, 5C, 7C, 9B, 10C, 25, 27C | Glaring, open | Wide, upper teeth bared | Forward | With the roar | [K] (M) |
| **Crying, despair** | 1C, 4C, 6C, 7B, 15C, 17C (+ 9B, 10B, 20B, 25/26 during sobs) | Squeezed, wet, reddening | Corners down, chin wrinkled | Down | Minutes | [K; M11] (H), [E] |
| Pleading | 1D + 4C (oblique brows), 15B, 20B, 25 | Wide-ish, fixed on the attacker | Parted | Tilted, forward | — | [E] |
| **Effort, straining** (pushing up, crawling, pressing a wound) | 4C, 6C, 7C, 9B, 10B, **24D or 31**, 21C | Squeezed | Lips pressed or teeth clenched | — | 0.5–3 s | [K] (M) |
| **Air hunger, choking** | 1C, 2C, **5C**, 25, **27C** (gaping), **38D**, **21D** | Wide, frightened | Gaping; nostrils flared; neck cords | **Extended**; hands to throat `[R2-04 §7.5]` | With each breath | [K] (H) |
| Nausea | 9B, 10B, 15B, 17B, 25A; swallowing every 10–30 s; yawns | Glazed | Lip-licking, swallowing | Still, head down | 10–120 s before vomiting `[R2-04 §2.7]` | [K] (M) |
| Disgust at the wound | 9C, 10C, 15B, 16B, 25 | Narrowed | Upper lip up, lower lip down | Back 5–10° | 0.5–2 s | [K; M11] (H) |
| Exhaustion, resignation (class III–IV, conscious) | 1A, 4A, 15A, 41C | Heavy lids, slow blinks | Slack | Drops | Sustained | [E] |

### 8.3 Pain face: extra detail

- **PSPI** = AU4 + max(AU6, AU7) + max(AU9, AU10) + AU43 (0–16) `[S1]`; game mapping PSPI ≈ 1.6 × pain `[R2-02 §9.1]`. ✓ verified [K] (H) (Prkachin & Solomon 2008): AU4, 6, 7, 9 and 10 are scored 0–5 and AU43 is **binary** (0/1), so the maximum is 5 + 5 + 5 + 1 = 16. AU5 (upper-lid raiser) is part of the FACS fear prototype and not of the pain core, so "pain closes, fear opens the eyes" ✓ holds `[K]` (M–H).
- **Other AUs often seen in pain**: jaw drop / mouth stretch (AU25–27), lip stretch (AU20) and a **lip-corner pull (AU12)** that makes a "pain smile" grimace; the AU12 in pain is not happiness `[K; M10] (M)`.
- **People have different pain faces.** A cluster analysis found a small number of recurring individual patterns, e.g. narrowed eyes with furrowed brows and wrinkled nose, or an opened mouth with narrowed eyes `[K; M10] (M–L)`. **Roll one pain-face type per character** (weights on the AU groups ±30 %) so that crowds do not grimace identically `[E]`.
- **Expressivity varies**: many people show little facial expression at moderate pain `[K; M10] (L–M)`. Game: `pain_face_gain` 0.3–1.3 per character, default distribution median 1.
- **Dynamics** `[E]`: onset 150–400 ms `[R2-02 §9.1]`; apex 0.5–1.5 s; in sustained pain, bursts of 1–3 s every 3–15 s with relaxation to 30–50 % between bursts; new pain spikes restart the burst.
- **Pain scream vs fear scream**: in pain the eyes are **squeezed shut** (AU6/7/43); in terror they are **wide open** (AU5). This single cue tells the player which one they are looking at `[K] (M)`.

### 8.4 Blending and living-face rules `[E]`

- **Combine sources by maximum per AU**, not by sum (pain, fear, effort, breathing, vocalisation).
- **Mouth AUs from the voice and breath generators override** the expression mouth (jaw opening from the F1 formula in §5.3; screams force AU27).
- **Asymmetry**: ±10–20 % random per side per episode; living faces are rarely symmetric. Palsy gains (§9) are applied after.
- **Micro-motion of the living face**: 0.02–0.05 weight noise at 0.3–2 Hz on brows, lids and lips; swallowing every 30–120 s when calm (every 5–30 s with nausea or blood in the mouth); nostril flare AU38 0.1–0.3 in time with inspiration when RR > 25. **The dead face gets none of this.**
- **Gates**: no voluntary or emotional AUs without a working facial nerve on that side (§9) and a working pons; swollen lids (periorbital haematoma) cap AU5 at 0.2 and hold the lids partly closed; a fractured mandible caps voluntary AU27 (gravity can still open the jaw, §13).

### 8.5 Timing reference

| Event | Value | Tag |
|---|---|---|
| Startle blink latency | ~30 ms | `[R2-02 §1]` |
| Expression onset / apex / offset | 150–500 ms / 0.5–2 s / 0.5–2 s | [K] (M), [E] |
| Micro-expression (leaked, suppressed) | 40–200 ms | [K] (M) |
| Pain-face onset after the pain is perceived | 150–400 ms | `[R2-02 §9.1]` |
| Swallow duration (larynx rise and fall) | 0.5–1 s | [K] (M) |

### Simulation parameters (expression)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `expr_recipes` | table §8.2 | AU weights | | [K; M11] [S1] [E] |
| `pain_face_type` | one of 3–4 clusters, ±30 % group weights | — | Per character | [K; M10] (M–L), [E] |
| `pain_face_gain` | 0.3–1.3 (median 1) | × | Per character | [E] |
| `pain_burst` | 1–3 s every 3–15 s; relax to 30–50 % | — | Sustained pain | [E] |
| `face_asymmetry` | ±10–20 % | per side | Per episode | [E] |
| `micro_motion` | 0.02–0.05 at 0.3–2 Hz | weight | Living only | [E] |
| `swallow_interval` | calm 30–120; nausea or oral blood 5–30 | s | | [K] (M), [E] |
| `nostril_flare` | AU38 0.1–0.3 per inspiration when RR > 25; 0.6–0.9 in air hunger | weight | | [K] (M), [E] |
| `lid_swelling_cap_AU5` | 0.2 | weight | Periorbital haematoma | [E] |

### Visual/behavioural checklist (expression)
- Pain: brows down, eyes squeezed, nose wrinkled, upper lip up, teeth bared; builds over half a second and comes in waves.
- A pain scream is screamed with the eyes shut; a terror scream with the eyes wide and white showing above the iris.
- Shock: a face that has stopped performing: heavy lids, open dry mouth, slow blinks, no expression until the body is moved.
- A dazed victim stares blankly and answers late.
- Air hunger: brows up, eyes wide, mouth gaping, nostrils flaring, neck cords standing out, head tipped back.
- No two characters grimace identically.

---

## 9. Facial palsy: central versus peripheral

### 9.1 The two patterns

| Feature | **Central** (upper motor neuron): face area of the motor cortex (lower precentral gyrus), corona radiata, internal-capsule genu | **Peripheral** (lower motor neuron): facial nucleus in the pons, the nerve in the temporal bone, its branches in the parotid and cheek | Tag |
|---|---|---|---|
| Side | **Opposite** to the lesion | **Same** side as the lesion | [K] (H) |
| Forehead (AU1, AU2) | **Largely spared** (upper face has input from both hemispheres); mild upper-face weakness is common in severe acute strokes | **Paralysed**: no wrinkling, brow lower | [S4] [K] (H) |
| Eye closure, blink (AU43, AU45) | Preserved or mildly weak | **Incomplete closure** (lagophthalmos); **Bell's phenomenon**: the eye rolls up and out on attempted closure, showing white | [S4] [S5] [K] (H) |
| Lower face (AU10, 12, 15, 20, 24) | Weak | Weak | [K] (H) |
| Emotional vs voluntary movement | **Emotional smiling may still move the weak side** (volitional–emotional dissociation) | Both lost | [S4] |
| Resting face | Mild: flat nasolabial fold, corner 1–3 mm lower | Marked (§9.3) | [K] (M), [E] |
| Associated signs | Opposite arm and hand weak; aphasia if dominant `[R2-01 §2, §5]` | Pons: crossed signs `[R2-01 §13]`. Temporal bone: hearing loss, blood or CSF from the ear, later Battle's sign `[R1-01 §5]` | [K] (H) |
| Onset in trauma | Immediate with the lesion | Immediate (nerve cut) or delayed by days (swelling in the canal) | [K] (H) |

### 9.2 Branch injuries (face wounds): which AUs are lost

| Branch (course) | AUs lost on that side | What the player sees | Tag |
|---|---|---|---|
| **Temporal (frontal)**: crosses the zygomatic arch | 1, 2 (part of 4) | Brow flat and lower; forehead smooth on that side | [K] (H) |
| **Zygomatic**: across the cheekbone to the eye | 6, 7, 43/45 weak (part of 12) | Incomplete eye closure; weak blink; eye waters | [K] (H) |
| **Buccal**: across the cheek, in front of the masseter | 9 (part), 10, 11, 12, 13, 14, upper 18/22/23, 34 | Upper lip droops; cheek billows; food and air pocket | [K] (H) |
| **Marginal mandibular**: along the lower border of the jaw | 15, 16, (17) | When grimacing or showing teeth, **the lower lip on the injured side stays up**: lopsided grimace | [K] (H) |
| **Cervical** | 21 | No neck cord on that side | [K] (M) |

- Cuts in front of a vertical line through the outer corner of the eye usually hit small terminal branches with overlapping supply, so visible palsy is less likely there `[K] (M)`.

### 9.3 Resting and moving asymmetry (peripheral palsy) `[E]` on `[K]`

| Feature | Magnitude |
|---|---|
| Brow ptosis | 2–5 mm lower than the other side |
| Palpebral fissure | Widened 1–3 mm (lower lid sags) |
| Incomplete closure on attempted blink or squeeze | Gap 2–10 mm, white showing as the eye rolls up (Bell's) |
| Nasolabial fold | Flattened (depth ×0.2–0.5) |
| Mouth corner at rest | 2–6 mm lower |
| Mouth midline at rest / on expression | Pulled 2–5 mm / **5–15 mm toward the healthy side** |
| Cheek on expiration | **Puffs out 3–10 mm with each expiration** (passive; very visible in the unconscious) |
| Fluids | Drool and blood leak from the paralysed corner; **tears spill** over the lower lid (it no longer pumps tears) |
| Over hours | The exposed eye reddens and dries (a dry band like `[R1-04 §11]` but in a living eye) |

- **Bell's phenomenon** (upward roll of the eye with lid closure) is present in most people `[S5] (M)`.
- **Cheek puffing on expiration on the paralysed side** is a classic sign of hemiplegia in a comatose patient, and it also occurs in central palsy because the lower face is weak `[K] (H)`.

### 9.4 Grading (House–Brackmann) → AU gain

| Grade | Description `[K; M12] (H)` | AU gain on the affected side `[E]` |
|---|---|---|
| I | Normal | 1.0 |
| II | Slight weakness on close inspection; complete eye closure with minimal effort | 0.8 |
| III | Obvious but not disfiguring asymmetry; complete eye closure with effort; some forehead movement | 0.6 |
| IV | Obvious, disfiguring asymmetry; **incomplete eye closure; no forehead movement** | 0.4 (forehead 0) |
| V | Barely perceptible movement; asymmetric at rest | 0.15 |
| VI | Total paralysis | 0 |

### 9.5 Causes in the game

| Cause | Palsy | Probability / notes | Tag |
|---|---|---|---|
| Lower precentral gyrus, corona radiata, capsule genu `[R2-01 §2, §11]` | Central, opposite side | Deterministic from the lesion map | `[R2-01]` |
| Pons (facial nucleus or fascicle) `[R2-01 §13]` | Peripheral, same side, with crossed limb weakness | Deterministic | `[R2-01]` |
| **Temporal bone fracture** (blunt or gunshot) | Peripheral, same side | ~7–10 % of all temporal bone fractures; **30–50 %** of fractures crossing the inner ear (transverse / otic-capsule-violating); gunshots through the temporal bone higher | [K; M23] (M–L) |
| Cheek, parotid or jaw-line cut or gunshot | Branch pattern §9.2 | Deterministic from the track vs branch course | [K] (H) |
| Both sides (bilateral temporal bone fractures, bilateral pontine injury) | **Facial diplegia**: expressionless, both eyes cannot close | Rare | [K] (M) |

### 9.6 Palsy in the unconscious

- Visible only through **tone**: the paralysed side is flatter, its mouth corner lower, its **cheek billows on expiration**, and its lid closes less `[K] (H)`.
- **Pain stimulus test** (the player presses a nail bed or the supraorbital notch): the grimace moves only the working side `[K] (H)`. Use it as the in-game way to discover a palsy.

### Simulation parameters (palsy)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `palsy_type` | none / central / peripheral / branch | enum per side | From the lesion resolver | [K] (H) |
| `central_upper_face_gain` | 0.8–1.0 | × | Upper face largely spared | [S4] |
| `central_emotional_smile_kept` | true (p 0.5–0.7) | bool | | [S4] [E] |
| `peripheral_gain_by_HB` | I 1.0 … VI 0 | × | §9.4 | [K; M12] [E] |
| `brow_ptosis` / `corner_droop` | 2–5 / 2–6 | mm | Peripheral, at rest | [E] on [K] |
| `midline_pull_expression` | 5–15 | mm | Toward the healthy side | [E] on [K] |
| `lagophthalmos_gap` | 2–10 | mm | Peripheral | [E] on [K] |
| `bells_p` | ~0.75–0.9 | p | Eye rolls up on attempted closure | [S5] (M) |
| `cheek_puff_expiration` | 3–10 | mm | Paralysed side; strongest in the unconscious | [K] (H), [E] |
| `temporal_bone_palsy_p` | all 0.07–0.10; transverse/otic 0.3–0.5 | p | | [K; M23] (M–L) |

### Visual/behavioural checklist (palsy)
- A brain wound: the opposite lower face sags and the mouth pulls to the healthy side when the victim grimaces or screams, but both brows still lift and both eyes still close.
- A temporal bone or pontine injury: the whole half of the face is dead, brow and all; the eye cannot close and rolls up, tears and drool run from that side.
- A cut along the jaw line: only the lower lip on that side fails to drop in a grimace.
- Unconscious hemiplegic: one cheek blows out with every breath out.

---

## 10. Colour: pallor, cyanosis, congestion, flushing and capillary refill

Haemorrhage colours (face, lips, conjunctiva, nail beds by blood-loss class) are in `[R1-04 §7.7]`; the cyanosis threshold and mottling are in `[R2-04 §8]`. This section adds cyanosis ramps, other colour states, dark skin, timing and capillary refill.

### 10.1 Model

- Visible colour depends on the **amount of haemoglobin in the skin's capillaries** (Hb concentration × local perfusion), its **oxygen saturation**, **venous congestion**, **temperature** and **melanin** `[K] (H)`.
- Recommended shader model: two chromophores (**melanin**, **haemoglobin**) plus the **oxy fraction**, as in practical dynamic facial-colour models, which also let expressions blanch compressed skin (forehead ridges in AU1/2, cheeks in AU6/12) and flush others `[K; M13] (M)`. The hex ramps below are the targets that such a model should reproduce under neutral lighting.
- **Central vs peripheral cyanosis** `[K] (H)`: central cyanosis (low arterial saturation) turns the **tongue and oral mucosa** blue as well as the lips; peripheral cyanosis (slow flow in cold or shut-down extremities) leaves the **tongue pink** while fingers, nail beds, ear lobes and lips go dusky.

### 10.2 Ramps (light-to-medium skin) `[E]` (tune under game lighting)

Steps map to arterial deoxy-Hb = `Hb × (1 − SaO₂)`: **trace 1.5–2.5, mild 2.5–3.5, moderate 3.5–5, severe > 5 g/dL** (threshold 2.5 g/dL per `[R2-04 §8.2]`).

| Region | Normal | Mild cyanosis | Moderate | Severe | Congested-cyanotic (asphyxia, strangulation, tonic seizure) | Exsanguinated (not blue) |
|---|---|---|---|---|---|---|
| Lips | `#B35E62` `[R1-04]` | `#9E6070` | `#8A5E7C` | `#6E587E` | `#5E3F66` | `#A99AA4` `[R1-04]` |
| Nail beds | `#E2A9A6` `[R1-04]` | `#C9A0B2` | `#A994B4` | `#8C86AE` | `#7E6A9A` | `#EEE0DC` `[R1-04]` |
| Tongue, gums, oral mucosa | `#C8646A` | `#A8637A` | `#8E5E82` | `#6F557E` | `#5A3F66` | `#D8B8BA` |
| Palpebral conjunctiva | `#D98C87` `[R1-04]` | `#C48A98` | `#AE889F` | `#967FA0` | `#8A5A7A` + petechiae | `#EFDCD8` `[R1-04]` |
| Face skin overlay (multiply) | — | `#7F86AE` 10 % | 20 % | 30–40 % | `#7A4A78` 30–60 % + petechiae `[R1-04 §11.8]` | Waxy `#E3DCD3` `[R1-04]` |
| Ear lobes, nose tip, fingertips | Skin | Nail-bed ramp at 50 % over skin | ″ | ″ | ″ | Pale |

**Other states** `[E]` on `[K]`:

| State | Where | Colour | Tag |
|---|---|---|---|
| Peripheral (acro-)cyanosis: cold, shock with normal SaO₂ | Nail beds, fingertips, ear lobes, lips (tongue pink) | Mild ramp at the periphery only; lips `#A77E8A` | [K] (M) |
| Livid face after circulatory arrest with a full blood volume | Face, lips | Overlay `#7E8196` 30–50 % within 1–3 min `[R2-04 §9.3]` | [E] |
| Vasovagal pallor ("grey-green") | Face | Desaturate 30 %, overlay `#C9CCB0` 10–20 % | [E] (L) |
| Fear or pain pallor | Face, lips | Desaturate 15–25 %; lips toward `#BF8583` | `[R1-04 §7.7]` [E] |
| Flush (anger, heat, Cushing phase, CO₂ retention) | Cheeks, forehead, neck | Overlay `#D9786E` 15–35 % | [K] (M), [E] |
| Straining (Valsalva, pushing up, tonic seizure start) | Whole face, congested | Overlay `#C0607A` 20–40 %; veins on forehead and neck | [K] (M), [E] |
| Blanched skin under pressure | Pressed area | Light skin `#F0E4DC`; nail bed `#F2E6E2` | [E] |

### 10.3 Dark skin (Fitzpatrick V–VI)

- Pallor and cyanosis are **hard to see in the skin** itself; clinicians look at **lips (inner surface), gums, tongue, conjunctivae, nail beds, palms and soles** `[K] (H)`.
- Game rule `[E]`: apply the full ramps of §10.2 to those regions; on facial skin use only a subtle **ashen grey** overlay: pallor `#8A8790` 10–25 %, cyanosis `#6C6F86` 10–20 %. The outer lip (vermilion) is often pigmented; drive the inner lip with the oral-mucosa ramp.

### 10.4 Timing

| Change | Onset | Full | Recovery | Tag |
|---|---|---|---|---|
| **Colour lag behind arterial saturation** | Lips and tongue **~5–15 s** (lung-to-tongue circulation); fingers and nail beds **~15–30 s**, longer in cold and shock | — | Same lags | [K; M27] (M) |
| Apnoea or complete obstruction at rest, room air, normal lungs | SpO₂ holds > 90 % for **~60–120 s**, then falls steeply | Lips visibly blue at ~70–150 s (Hb 15); keep the `[R2-04 §8.2]` default of 60–120 s | Pink within ~10–30 s of airflow + lag | [K; M28] (M), `[R2-04 §8.2]` |
| Same while struggling, seizing (oxygen use ×2) | ~30–60 s | Blue at ~40–80 s | as above | [K] (M), [E] |
| Fear or pain pallor | 2–10 s | 20–60 s | 1–5 min | [E] on [K] |
| Vasovagal pallor | 10–30 s before the faint | — | Minutes | `[R2-04 §8.1]` |
| Haemorrhagic pallor | Follows loss class `[R1-04 §7.7]`, vasoconstriction lag τ 30–60 s | — | — | [E] |
| Flush | 5–30 s | 30–60 s | 1–5 min | [K] (M), [E] |
| Circulatory arrest | Face livid 1–3 min (full blood) or stays white (exsanguinated) | — | — | `[R2-04 §9.3]` |
| Post-mortem | Pallor mortis minutes to ~30 min; livor from 20–30 min | — | — | `[R1-04 §12]` |

Implement each colour driver as a first-order lag toward its target: face and lips τ = 8 s, extremities τ = 20 s, both ×2 in shock `[E]`.

### 10.5 Capillary refill (player "press the skin" interaction)

| State | Refill time after 5 s of pressure | Tag |
|---|---|---|
| Normal | **≤ 2 s** | [K] (H) |
| Class II loss, cold ambient | 2–3 s (cold adds 1–2 s) | [K] (M) |
| Class III | 3–4 s | [K] (M) |
| Class IV | > 4–5 s | [K] (M) |
| Dead | No refill. Once livor has formed, it still blanches under pressure until it fixes (~8–12 h) `[R1-04 §12]` | [K] (H) |

Animate the blanched spot refilling from its edges inward, first-order with τ = refill time / 3 `[E]`.

### Simulation parameters (colour)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `cyan_steps` | trace 1.5–2.5; mild 2.5–3.5; moderate 3.5–5; severe > 5 | g/dL deoxy-Hb | Arterial | `[R2-04 §8.2]` (M), [E] |
| `ramps` | table §10.2 | sRGB | Tune under lighting | [E] |
| `central_vs_peripheral` | central: tongue blue; peripheral: tongue pink | rule | | [K] (H) |
| `colour_lag_face` / `extremity` | 8 (5–15) / 20 (15–30) | s | ×2 in shock | [K; M27] (M), [E] |
| `apnoea_spo2_hold` | 60–120 (rest); 30–60 (struggle) | s | Then steep fall | [K; M28] (M) |
| `fear_pallor` | onset 2–10 s; full 20–60 s; recovery 1–5 min | — | | [E] |
| `crt` | ≤ 2 / 2–3 / 3–4 / > 4–5 / none | s | Normal / II / III / IV / dead | [K] (H–M) |
| `dark_skin_overlay` | pallor `#8A8790` 10–25 %; cyanosis `#6C6F86` 10–20 % | sRGB | Mucosa and nail beds carry the signal | [E] on [K] |

### Visual/behavioural checklist (colour)
- Blue lips and a blue tongue: the victim is not getting oxygen. Blue fingers with a pink tongue: cold or shut-down circulation.
- An airway blocked at rest turns the lips blue in about one to two minutes; a struggling victim's in under a minute and a half.
- A bled-out victim goes white and grey-lilac, never blue.
- Strangled, seizing or crushed: a dusky purple, congested face with pinpoint haemorrhages.
- Pressing a nail bed: pink returns in under 2 s in the healthy, slowly in shock, never in the dead.
- On dark skin, look at the gums, tongue, inner lips, eyelid linings and nail beds.

---

## 11. Sweat, wetness and skin sheen

Onset and distribution of cold sweat are in `[R2-04 §8.1]` (forehead, upper lip, temples → neck, chest, palms; beads 0.5–3 mm; spreads over 1–3 min; stops at `t_arr`, dries over 30–60 min).

| Item | Value | Tag |
|---|---|---|
| Eccrine gland density | Forehead ~150–200 /cm²; palms and soles ~350–600 /cm²; back ~60–100 /cm² | [K; M30] (M) |
| Emotional ("psychogenic") sweating sites | Palms, soles, armpits, forehead, upper lip | [K] (H) |
| Sudomotor latency (skin conductance response) | 1–3 s after the stimulus | [K] (H) |
| Visible moisture | Palms 10–60 s after strong fear or pain; forehead beads 1–3 min `[R2-04 §8.1]` | [E] on [K] |
| **Cold, clammy skin** of shock | Sweat + vasoconstriction: pale, cool, wet | [K] (H) |
| Beads run | When a drop exceeds ~2–4 mm on vertical skin (contact-angle hysteresis) | [E] |
| Wet-skin shading | Roughness 0.45 → 0.15–0.25; specular up; albedo darkens 5–10 % | [E] on [K] |
| Sweat and blood | Sweat thins blood film at the hairline and brow: pinker, streaked runs | [E] |
| After death | No new sweat; film evaporates in 30–60 min; skin dulls `[R2-04 §8.1]` | `[R2-04]` |
| Below a spinal cord lesion | No sweating below the level | `[R2-04 §1]` |

### Simulation parameters (sweat)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `sweat_latency_palms` / `forehead_beads` | 10–60 s / 1–3 min | — | Fear, pain, class II–III, prodrome | [E] on [K] |
| `bead_run_size` | 2–4 | mm | | [E] |
| `wet_roughness` | 0.15–0.25 | — | From ~0.45 dry | [E] |
| `wet_albedo` | ×0.90–0.95 | — | | [E] |
| `sweat_stop` | `t_arr`; below a cord lesion | rule | | `[R2-04 §1]` |

### Visual/behavioural checklist (sweat)
- Fear: palms wet within a minute. Shock: beads on the forehead and upper lip within minutes, grey skin that shines.
- Sweat stops when the heart stops; the skin loses its sheen over the next hour.

---

## 12. Eyes: pupils, blinks, gaze and tears

Lesion-specific pupil and gaze signs are in `[R2-01 §14]`; eyes when dying and dead in `[R1-04 §11]`; lid apertures per state in `[R2-04 §7]`.

### 12.1 Pupils in pain, fear and shock

| Condition | Pupil behaviour | Tag |
|---|---|---|
| Light | 2–4 mm in bright light, 4–8 mm in darkness; light reflex latency ~200–300 ms, constriction over ~1 s | [K] (H) |
| **Pain (awake)**: pupillary dilation reflex | Dilates ~**0.3–1 mm** within **0.3–0.6 s**, peak at ~1–2 s, back over 3–10 s; larger with stronger stimuli (much larger, 2–4 mm, under anaesthesia) | [K; M14] (L–M) |
| Fear, arousal (sustained) | Baseline +0.5–1.5 mm (typical 4–7 mm in normal light) | `[R2-04 §7.1]` [E] |
| Shock class III | Normal to large, sluggish | `[R1-04 §7]` |
| Hypoxia, anoxia | Dilating; fixed and wide by 1–2 min after circulatory arrest | `[R1-04 §11]` `[R2-04 §14]` |
| Brain death | Fixed, mean ~5 mm | [S9] |

### 12.2 Blinks

| Condition | Rate | Duration | Tag |
|---|---|---|---|
| Calm | 15–20/min (10–25) | 100–400 ms (close 70–100 ms, reopen 150–250 ms) | [K] (H) |
| Talking, agitated | 20–30/min | Normal | [K] (M) |
| **Watching a threat** | Suppressed (< 5/min), then bursts | Normal | [K] (M) |
| Pain | Blinks replaced by squeezes (AU6/7/43) of 0.3–3 s | — | [S1] [E] |
| **Shock, exhaustion, drowsiness** | 5–10/min | **Slow: 300–500 ms**; lids reopen incompletely (heavy lids) | `[R2-04 §7.1]` [K] (M) |
| Stupor / coma / dead | 0–5/min / none / none | — | `[R2-04 §7.1]` |

### 12.3 Gaze

- **Saccade main sequence** `[K; M18] (H)`: duration ≈ **21 ms + 2.2 ms per degree**; peak velocity ~400 °/s at 10°, saturating near 500–700 °/s for large saccades.
- **Fear and threat**: hypervigilant scanning at 2–4 saccades/s between the attacker, the weapon and exits; fixation on the weapon ("weapon focus") `[K] (M)`.
- **Pain**: eyes shut or fixed on the wound.
- **Shock, daze**: fewer saccades (0.5–1/s), slower (peak velocity ×0.6–0.8), long fixations and drift; the "vacant", "thousand-yard" stare `[S6]` `[K] (M)`, `[E]` values.
- **Syncope and anoxic LOC**: eyes open and deviated upward for 2–10 s `[S15]` `[R2-04 §7.1]`.

### 12.4 Tears

| Item | Value | Tag |
|---|---|---|
| Basal tear secretion | ~1–2 µL/min | [K; M19] (H) |
| Tear film volume / conjunctival sac maximum before overflow | ~7 µL / ~25–30 µL | [K; M19] (M) |
| **Reflex tearing** (pain, eye or nose injury, smoke, irritants) | ~10–100 µL/min | [K] (L–M), [E] |
| **Nose struck (trigeminal reflex)** | Eyes **glisten within 1–5 s**; tears run down the cheeks within ~10–30 s | [K] (M), [E] timing |
| Emotional crying | Tears run within ~30–120 s of crying onset; nose runs (tears drain through the nasolacrimal duct): sniffing | [K] (M), [E] |
| A tear running down the cheek | 10–30 µL; 5–20 mm/s on a vertical cheek; slows in blood or sweat | [E] |
| Conjunctival redness after crying or rubbing | Sclera tints toward `#E8B4B0` over 1–5 min | [E] |
| Without blinking (coma, dead) | Tear film breaks up in ~10–20 s; the eye loses its glisten over minutes; dry band later `[R1-04 §11]` | [K] (M) |
| Paralysed lower lid (§9) | Tears spill over the lid on that side | [K] (H) |

### Simulation parameters (eyes)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `pdr_pain` | +0.3–1.0 mm; latency 0.3–0.6 s; peak 1–2 s; decay 3–10 s | — | Awake | [K; M14] (L–M) |
| `pupil_fear_offset` | +0.5–1.5 | mm | Sustained arousal | [E] |
| `blink_rate` | calm 15–20; threat < 5 then bursts; shock 5–10 | /min | | [K] (M–H) |
| `blink_duration` | normal 100–400; shock 300–500 | ms | | [K] (M) |
| `saccade_duration` | 21 + 2.2 × amplitude(°) | ms | | [K; M18] (H) |
| `saccade_rate` | fear 2–4; shock 0.5–1 | /s | | [K] (M), [E] |
| `tear_basal` / `reflex` | 1–2 / 10–100 | µL/min | | [K; M19] (H) / (L–M) |
| `tear_overflow_volume` | 20–25 | µL excess | Then a drop runs | [E] |
| `nose_hit_tear_time` | glisten 1–5 s; run 10–30 s | s | | [E] |

### Visual/behavioural checklist (eyes)
- Pain: pupils widen a little within a second; eyes squeeze shut.
- Fear: eyes wide, darting between the attacker, the weapon and the way out.
- Shock: slow heavy blinks, few eye movements, a fixed stare.
- A punch to the nose makes the eyes water at once, even in a tough character.
- Crying: tears, a running nose, sniffing, reddened eyes.
- An eye that cannot close (palsy, coma) loses its shine and reddens.

---

## 13. Loss of facial tone and the death mask

### 13.1 How fast the face goes slack

| Death type | Face | Tag |
|---|---|---|
| **Brainstem destroyed** | Tone lost within ~100 ms `[R2-02 §0.4]`: expression vanishes instantly; lids stay where they were (often open); the jaw drops as soon as the head moves or tilts back | `[R2-02]` `[R1-04 §2]` |
| **Circulatory arrest** (heart destroyed, exsanguination to PEA) | Expression lasts until LOC at 8–15 s; an **anoxic grimace or tonic spasm** may follow (10–40 s); flaccid by ~1–1.5 min; gasps open the jaw wide `[R2-04 §2.2, §3]` | `[R2-04]` |
| **Slow death** (hours) | Progressive: heavy lids → cannot close the lids fully → **drooping nasolabial folds** → mandibular breathing → slack | `[R2-04 §2.3]` (palliative signs, R2-04 M14) |
| Jaw tone after LOC | Supine jaw opens within 0.5–5 s `[R2-04 §7.3]` | `[R2-04]` |

### 13.2 What a face without tone does (gravity only) `[E]` on `[K]`

| Feature | Supine | Upright slumped | Prone |
|---|---|---|---|
| Jaw | Opens 10–30 mm `[R2-04 §7.3]` | Closed or slightly open; chin on chest | Pressed; mouth distorted against the floor |
| Lips | Parted; lower lip everts and sags 2–5 mm | Lower lip hangs 2–5 mm | Compressed, distorted |
| Cheeks and jowls | Slide toward the ears and back of the head **3–10 mm**: face looks flatter and wider | Sag down 3–8 mm: jowls, heavy lower face | Pushed up and sideways |
| Nasolabial folds | Flatten | Deepen by sag | Distorted |
| Lids | Where they were at the loss of tone; drop 2–4 mm over 1–3 s `[R2-04 §7.2]` | Drift down | Closed by pressure or open |
| Eyes | Fixed, slightly divergent `[R1-04 §11]` | Down | — |
| Tongue | Falls back; tip behind the lower teeth `[R2-04 §7.4]` | Forward | Tip may show between the teeth |

- The newly dead face looks **"emptier" and older** because all tone and micro-motion stop; this, not a dramatic pose, is the cue players read as death `[E]` on `[K]`.

### 13.3 No frozen expression

- **The pain or fear face does not persist after death.** It releases at loss of consciousness. The final facial "expression" is produced by gravity and posture `[K] (H)`.
- **Cadaveric spasm** (instant rigor fixing the last posture) is rare and almost always involves the **hands**, not the face `[K] (M)` (forensic texts, R2-04 M19). Do not fix a scream on the corpse.
- Rigor later fixes whatever gravity produced (jaw and lids first, from ~1–3 h) `[R1-04 §12]`.

### 13.4 The Hippocratic face (dying over hours to days)

Hippocrates' description (*Prognostic*) remains the classic picture of the moribund face `[K; M17] (H)`: **a sharp nose, hollow eyes, sunken temples, ears cold and drawn in with the lobes turned out, the skin of the forehead hard, stretched and dry, and the colour of the whole face green-yellow, black, livid or lead-coloured**. Game version `[E]`: temples hollow 2–4 mm, eyes sunken 1–3 mm, lips thin and dry, nose tip paler and sharper, skin tight and dull. **Use it only for deaths lasting hours** (slow bleeding with compensation, raised ICP); it does not develop in minutes.

### 13.5 Unconscious versus dead: the face tells

| Sign | Unconscious (alive) | Dead | Tag |
|---|---|---|---|
| Lids | Closed or open a slit (1–5 mm); **a lifted lid closes slowly over 1–2 s** | **Stays where it is put** | `[R2-04 §7.1]` `[R1-04 §11]` |
| Blink to touching the eyelashes or cornea | Present while the pons works | None | `[R2-04 §1]` |
| Micro-motion, swallowing, nostril movement with breaths | Present | None | [E] on [K] |
| Colour | Pink to pale; lips pink, blue or grey by physiology | Pallor mortis; livid if asphyxial | §10 |
| Eye surface | Moist, glistening | Glisten fades over minutes; dry band later | `[R1-04 §11]` |
| Mouth when supine | Open 5–20 mm, snoring | Open 10–30 mm, silent | `[R2-04 §7.3]` |
| Grimace to a pain stimulus | Present in stupor and light coma | None | `[R2-01 §19]` |

### 13.6 The death mask over the first hours

Details and times are in `[R1-04 §11–§12]`. For FaceGen, flag these per hour: pallor mortis (minutes–30 min); corneal dulling (minutes–hours with the eye open); dry scleral band (hours with the eye open); lips drying brown (hours); jaw and lid rigor (1–3 h); softening, "sunken" eyes as eye pressure falls (hours); livor of the face only if the face is dependent (prone).

### Simulation parameters (death mask)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `face_tone_loss` | brainstem ≤ 0.1; circulatory arrest 60–90 after LOC; slow death hours | s | Tone → 0 | `[R2-02]` `[R2-04]` |
| `cheek_gravity_shift` | supine 3–10 toward ears; upright 3–8 down | mm | Corrective sag shapes, weight = 1 − tone | [E] |
| `lower_lip_sag` | 2–5 | mm | | [E] |
| `frozen_expression` | never (face) | rule | Cadaveric spasm: hands only | [K] (H) |
| `hippocratic_face` | temples −2–4 mm; eyes −1–3 mm; dull tight skin | — | Deaths lasting hours only | [K; M17] (H), [E] |
| `lid_after_lift` | alive 1–2 s to close; dead stays | s | | `[R1-04 §11]` |

### Visual/behavioural checklist (death mask)
- At death the face does not hold its last expression; it goes slack: jaw hangs, lower lip sags, cheeks slide with gravity, lids stay part-open.
- A lifted eyelid on a dead face stays up; on an unconscious face it drifts shut.
- Over the next hours: paler, duller eyes, drying lips, a jaw that becomes fixed where it fell.
- Only those who die slowly get the hollow-eyed, sharp-nosed, lead-coloured face.

---

## 14. Implementation in Godot 4.5

Engine facts here are `[K] (M)` from the author's knowledge of Godot 4.x; they were not re-verified in this session. Check them against the 4.5 class reference before building.

### 14.1 Audio architecture

- **Per character** `[E]`:
  - `MouthEmitter`: an `AudioStreamPlayer3D` on a `BoneAttachment3D` at the mouth, playing an `AudioStreamGenerator` for `BreathSynth` + `VoiceSynth` (or an `AudioStreamPolyphonic` if voice is sample-based);
  - `AirwayWoundEmitter`: at a sucking chest wound or open neck airway, only while one exists;
  - fluid emitters: at the **landing point** of jets and drips, not at the wound (§3.1); capped at 4–6 per character, as the VFX caps in `[R1-06 §8]`.
- **Global pool**: 24–32 `AudioStreamPlayer3D` for impacts and falls, each with an `AudioStreamRandomizer` over baked variants.
- **Buses**: `Impacts`, `Fluids`, `Breath`, `Voice`, `World` → `Master` with a limiter. Room reverb through `Area3D` reverb-bus settings.
- **Realism dynamic range** `[E]`: map the SPL range [40, 110] dB to [−60, 0] dB by default (`realism_range_db` 60); a wider setting for headphone users.
- **Air absorption**: the `AudioStreamPlayer3D` distance filter defaults to a strong high cut (cutoff 5 kHz, −24 dB) `[K] (M)`. Real air absorption is small below ~30 m (§1.3); set the cutoff to 10–12 kHz and the attenuation to about −6 dB `[E]`.
- **Occlusion**: a ray from listener to source; if blocked, `LP 1–2 kHz` and −6 to −15 dB `[E]`.

### 14.2 How to make the sounds procedurally without killing the frame rate

- **Bake one-shots at load** `[E]`: render each impact, fall, drip and crunch recipe into 8–16 variants per material state and body region as `AudioStreamWAV` (16-bit, 48 kHz, mono), and play them through `AudioStreamRandomizer` (pitch ±3–8 %, level ±1–3 dB). Memory: 16 variants × 0.3 s × 48,000 × 2 bytes ≈ **460 KB per recipe** (arithmetic).
- **Real-time generators only for continuous, physiology-coupled sound**: breath (with snore, stridor, gurgle, rattle layers), moans, whimpers, grunts, spurting patter and streams. Use one `AudioStreamGenerator` per active character mouth; `mix_rate` 24 kHz while only breathing, 48 kHz while vocalising; `buffer_length` ~0.1 s; each frame, push as many frames as the playback reports available `[K] (M)`.
- **Cost** `[E]` (M): per-sample DSP in GDScript is slow. A five-formant voice needs roughly 50–100 operations per sample, i.e. millions per second per voice. Budget **1–2 real-time voices in GDScript**. For more, move the DSP into a GDExtension, or mix **pre-rendered grains** (bubbles, crackles, clicks, glottal-pulse periods) instead of computing every sample.
- **Audio LOD** `[E]`: beyond ~15 m, drop quiet breathing (keep gasps, stridor, screams); beyond ~30 m, keep only screams, shots, falls and clatter; dead characters have no generator (passive huffs are baked one-shots).

### 14.3 Physiology → audio and face inputs

| Physiology variable (R1-04 §13 state) | Drives | Mapping |
|---|---|---|
| `pain` (0–10), `arousal` | Vocal type, F0, NLP, roughness, level (§6.3); pain face (§8) | Formulas §6.3; PSPI ≈ 1.6 × pain |
| `gcs_v`, `consciousness` | Vocal generator state (§6.5, §7.1); voluntary AUs gate | V5…V1; LOC → only passive sounds |
| `rr`, `tidal_volume`, `route` | `FLOW(t)` and breath noise (§5.3) | Level ∝ flow |
| `airway_fluid_mL` | Gurgle, wet voice, rattle | λ formula §5.3; audible ≥ 5–10 mL |
| `airway_narrowing` (0–1) | Stridor frequency and level; aphonia | §5.3 step 4 |
| `open_chest_wound_mm`, `sealed` | Sucking-wound recipe | §5.4 |
| `neck_airway_open`, `level_vs_cords` | Neck hiss and bubbling; aphonia or wet voice | §5.5, §7.2 |
| `blood_loss_frac`, `map` | Voice budget; spurt patter rate, level and centroid; pallor | §6.5, §3.2, §10 |
| `spo2`, `hb` | Cyanosis ramp; voice budget | §10.2, §6.5 |
| `perf_face`, `perf_periph`, `skin_temp` | Pallor, acrocyanosis, capillary refill, sweat | §10–§11 |
| `jaw_state`, `lip_state`, `tongue_state`, `teeth_state`, `nose_state`, `larynx_state`, `rln_L/R` | Speech processing chains; AU caps | §7.2–§7.3 |
| `facial_nerve_L/R` (type, HB grade, branches) | Palsy gains | §9 |
| `tone` (0–1) | AU scaling, gravity sag, jaw drop | §13 |
| `core_temp`, `shivering` | Voice tremor, chattering | `[R2-04 §6]` |
| `scream_seconds_10min` | Hoarseness | §6.5 |
| `t_arr`, `t_dead` | Stop sweat, micro-motion, colour lags; post-mortem flags | §11, §13 |

### 14.4 Face rig and skin shader

- **Blendshapes**: the 52-shape set plus custom shapes for AU11, AU21, AU31, AU38, split `cheekPuff_L/R` and `browInnerUp_L/R`, and gravity correctives (`sag_supine`, `sag_upright`, `sag_prone`): about 60–64 shapes `[E]`.
- **Per-frame pipeline** `[E]`:
  1. collect AU targets from every active source (pain, fear, effort, breath, voice, reflexes such as the startle blink);
  2. combine by maximum per AU; add asymmetry and micro-motion (§8.4);
  3. multiply each AU by the palsy gain of its side and branch (§9);
  4. multiply by `tone` (and by the consciousness gate for voluntary AUs);
  5. add gravity correctives with weight `(1 − tone)` by body orientation (§13.2);
  6. write lids and gaze through the eye rig (`[R2-01 §14]`, `[R2-04 §7]`);
  7. write weights to the `MeshInstance3D` at 30–60 Hz.
- **Skin shader instance uniforms** (budget ≤ 16 per shader `[R1-06]`) `[E]`: `hb_rel`, `sat_art`, `perf_face`, `perf_periph`, `congestion`, `flush`, `pallor_green`, `wet`, `mottling` (`[R2-04 §8.3]`), `livor` (`[R1-04 §12]`): 10 uniforms. A static **region mask texture** (lips, oral mucosa, nail beds, conjunctiva, ear lobes/nose tip, cheeks) selects which ramp of §10.2 applies. Melanin is a per-character material constant. Capillary-refill blanching is painted into the damage/texture-space layer `[R1-06 §6]` and fades back with the §10.5 time constant.
- **Update rates**: AUs 30–60 Hz; pupils 30 Hz; colour drivers 5 Hz with the §10.4 lags; sweat and tears as particles or texture-space painting when their volume changes.

### 14.5 Pseudocode (written for this document; not taken from any source)

```
# VoiceSynth, one audio block (N samples)
func render_voice_block(N, st):            # st = current utterance state
    budget = voice_budget(physiology)      # §6.5: max_db, max_dur, hnr_cap, f0_range_scale
    if st.elapsed >= min(st.duration, budget.max_dur): end_utterance(st); request_gasp_if_loud(st)
    for i in N:
        f0 = st.contour.sample(st.t) * st.f0_scale * nlp_jump(st)      # §6.3
        pulse = glottal_pulse(st.phase, st.oq)                          # Rosenberg/LF shape
        pulse *= 1.0 + shimmer_noise() - subharmonic_dip(st)            # NLP
        pulse *= 1.0 + st.rough_depth * sin(TAU * st.rough_rate * st.t) # roughness AM 30–150 Hz
        src = pulse + aspiration_noise(st.phase) * breath_gain(st.hnr)  # breathiness
        y = formant_cascade(src, jaw_to_f1(st.jaw_mm), st.f2, st.vtl)   # §6.1
        y = radiate(y) * db_to_lin(min(st.level_db, budget.max_db) - 100)
        out[i] = apply_damage_chain(y, st.damage_flags)                 # §7.3
        advance(st, f0)
```

```
# FaceGen, one frame
targets = {}                                   # AU -> weight
for src in active_sources: for au in src.aus: targets[au] = max(targets.get(au, 0), src.weight(au))
for au in targets:
    side_gain = palsy_gain(au, side)           # §9
    targets[au] *= side_gain * tone * (consciousness_gate(au))
apply_gravity_sag(1.0 - tone, body_orientation)   # §13.2
write_blendshapes(targets)
```

### Simulation parameters (implementation)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `impact_pool` | 24–32 | players | Global | [E] |
| `fluid_emitters_per_char` | 4–6 | — | At landing points | [E] on `[R1-06 §8]` |
| `baked_variants` | 8–16 | per recipe × state | ≈ 460 KB per recipe at 16 | [E] |
| `generator_mix_rate` | 24,000 breathing; 48,000 vocalising | Hz | | [E] |
| `generator_buffer` | ~0.1 | s | | [E] |
| `realtime_voices_gdscript` | 1–2 | — | More needs GDExtension or grain mixing | [E] (M) |
| `realism_range_db` | 60 (40–80) | dB | SPL 40–110 → −60–0 dB | [E] |
| `attenuation_filter` | cutoff 10–12 kHz, −6 dB | — | Instead of the strong default | [E] |
| `audio_lod` | 15 m: no quiet breathing; 30 m: loud events only | m | | [E] |
| `face_update` / `colour_update` | 30–60 / 5 | Hz | | [E] |
| `skin_instance_uniforms` | 10 of 16 | — | Region mask selects ramps | [E] on `[R1-06]` |

### Visual/behavioural checklist (implementation)
- Blood sounds come from where the blood lands.
- Breathing and voice come from the mouth bone and move with the head; a sucking wound sounds at the wound.
- Distant characters stay audible only for loud events; nothing breathes after death except when moved.

---

## 15. Master state table: what the player hears and sees

| State | Breathing sound | Voice | Face (key AUs) | Eyes and lids | Skin | Other sounds |
|---|---|---|---|---|---|---|
| Alert, unhurt, threatened | Audible mouth breathing 35–50 dBA | Pleading, shouting, raised F0 | Fear set (1+2+4+5+7+20+26) | Wide, white above the iris; scanning 2–4 saccades/s; pupils +0.5–1.5 mm | Pallor within seconds; palms sweat | Footsteps, clothing |
| **First 0.3 s after a hit** | Breath catches | Startle yelp or impact grunt 60–150 ms after | Startle blink at ~30 ms, then 4+7+20+21 | Blink, then wide | — | Impact sound (§2) |
| **Acute severe pain (0–10 s)** | Hold, then hiss or catching breaths | Yell or scream per §6.3; one per breath with gasps | Pain set, eyes shut (PSPI 13–16) | Squeezed shut; pupil +0.3–1 mm | Pallor starts | Clutching, clothing |
| Terror | Panting | Terror screams | Terror set, eyes wide | Wide, fixed on the threat | Pale, sweating | — |
| Sustained pain (minutes) | Irregular, sighs | Moans, whimpers, crying, pleading | Pain bursts every 3–15 s | Wet, reddening, tears | Pale, sweaty | Sobs, sniffs |
| Shock class II | 20–30/min, audible | Anxious speech, "I'm cold", "water" | Fear/pain, reduced | Normal to wide | Pale, cool, sweat beads | Teeth chattering if shivering |
| **Shock class III** | 30–40/min, shallow, dry mouth clicks, sighs | Short breathy phrases, slurred, repetitive; ≤ 85–90 dB | Shock face; grimace only when moved | 5–8 mm, sunken, slow blinks | Grey, clammy; lips `#C9A09E` `[R1-04]`; CRT 3–4 s | Restless movements |
| **Shock class IV, pre-LOC** | Faint, irregular | Moans, single words, then silence | Slack | Half-closed, vacant | Waxy; lips grey-lilac | — |
| Stupor (GCS 9–12, V2–3) | Snoring if supine | Moans to pain | Grimace to pain only | Drooping, roving | Per physiology | — |
| Coma, brainstem intact | Snoring or gurgling | Passive groans | Slack; palsy cheek puff if hemiplegic | Slit open 1–5 mm; roving; doll's eyes | Per physiology | — |
| Seizure (tonic → clonic → post-ictal) | Apnoea → grunting jerks → loud snoring | Epileptic cry at onset | Clenched → rhythmic grimaces → slack | Open, deviated → half-closed | Blue-purple congested at 10–30 s → pale | Tongue-bite, froth bubbling |
| **Blood in the airway, conscious** | Gurgling, wet coughs | Wet, gargled; spits every 5–30 s | Effort, air hunger | Wide, frightened | Pale; blue if flooding | Coughing spray, spitting |
| Blood in the airway, unconscious supine | Loud gurgling, bubbles at lips and nostrils | — | Slack | — | Turning blue | — |
| **Sucking chest wound** | 30–40/min; hiss or whistle (small hole) or slurp and bubble (large hole) at the wound | 1–4 words per breath; grunting | Air hunger | Wide | Grey, then blue | Froth at the wound |
| **Throat cut through the windpipe** | Rushing and bubbling at the neck | Aphonic below the cords; wet bubbly voice above | Air hunger, terror | Wide | Pale; blue as blood is aspirated | Spray from the neck with coughs |
| Larynx crushed | Stridor rising, then silence if closed | Hoarse → whisper → none | Air hunger; hands to throat | Wide | Blue | — |
| **Agonal (after `t_arr`)** | Snorting gasps every 10–60 s for 1–5 min | Occasional passive groan | Jaw gapes with each gasp; otherwise slack | Half-open, fixed; pupils widening | Livid (full blood) or white (bled out) | Drip patter at the landing points |
| Dead 0–30 min | Silence | None (passive huff when moved) | Death mask (§13) | Lids where they were; glisten fading | Pallor mortis | Drips slowing, then stopping |
| Dead, hours | Silence | — | Rigor-fixed jaw | Dry band; sunken | Livor below; lips browning | — |

---

## 16. Common realism mistakes (with the fix)

| Mistake | Why it is wrong | Fix |
|---|---|---|
| Film-style "crack-smack" on every punch | Real blows are dull thuds; cracks need bone, teeth or a fracture (§2.1) | Physical recipes; `impact_stylisation` for players who want the convention |
| Hearing the bullet hit at the same instant as the shot | Impact sound travels back; from ~20 m it is a separate, delayed "whop" (§2.2) | Delay = d/v + d/343 |
| **Blood jets that hiss at the wound** | Jet speed ≤ 5.5 m/s is silent; the sound is at the landing point (§3.1) | Emit spurt patter where the jet lands |
| **Drips that "plink" on the floor** | Floor pools are 2.5 mm deep; no ringing bubble (§3.1) | "Pat" on pools; "plink" only in deep liquid |
| An audible heartbeat from the victim | A heartbeat cannot be heard at a distance | Use visible jets and pulse, never a heartbeat sound |
| Loud screaming while bled out | Class III–IV cannot generate the pressure (§6.5) | Voice budget by blood loss and SpO₂ |
| Screams that sound like singing or speech | Real screams are rough (30–150 Hz AM) and full of nonlinear phenomena `[S2]` `[S3]` | Roughness and NLP injection (§6.6) |
| Every character screams at the same pitch | Pitch is individual and preserved into screams `[S3]` | Derive vocal F0 from each character's speaking F0 |
| A clearly speaking victim with a shattered jaw or tracheal wound | Articulators or airflow are gone (§7.2) | Processing chains and aphonia rules |
| A left-hemisphere wound silences screaming | Pain vocalisation survives aphasia `[R2-01 §5.2]` | Remove words only |
| Pain face with eyes wide open | Pain closes the eyes; fear opens them (§8.3) | AU43/6/7 in pain; AU5 in fear |
| Identical grimaces on every NPC | Pain faces differ between people `[K; M10]` | Per-character pain-face type and gain |
| Waxy, motionless living face | Living faces swallow, blink, twitch and flare nostrils | Micro-motion layer (§8.4) |
| Dead face that keeps its last expression | Tone is lost; gravity shapes the face (§13.3) | Tone → 0, sag correctives |
| Dead eyes neatly closed | Lids stay where they were `[R1-04 §11]` | Distribution in `[R1-04 §11.3]` |
| Facial palsy that spares the forehead after a temporal bone fracture, or paralyses it after a cortical wound | Central spares the forehead; peripheral does not (§9.1) | Per-type AU gains |
| Blue lips on a bled-out body | Too little haemoglobin for cyanosis `[R2-04 §8.2]` | Grey-lilac lips, waxy skin |
| Instant colour changes | Colour lags saturation by 5–30 s; pallor builds over tens of seconds (§10.4) | First-order lags |
| Death rattle in a fast death | Needs hours of unconsciousness `[R2-04 §2.4]` | Gate on time unconscious |
| Silent sucking chest wound, or one that hisses with no breathing | The sound follows the victim's breaths (§5.4) | Drive from `FLOW(t)` |
| Body falls with no head knock and no breath forced out | Head impacts are the sharpest part of a fall; the chest expels air (§4) | `SKULL_KNOCK` + chest huff |
| Clean, silent tears only in "sad" scenes | Reflex tearing follows nose, eye and severe pain triggers within seconds (§12.4) | Tear generator driven by triggers |

---

## 17. Load-bearing claims (quick reference)

1. **Contact duration sets the sound**: spectrum flat to ~1/τc, first zero at 1.5/τc. Fist-to-face ~12 ms (from 26.5 kg·m/s and ~3.4 kN `[S14]`), head-to-concrete 2–8 ms, trunk-to-floor 20–80 ms, steel-on-bone 0.2–1 ms `[K] (H)` physics, `[E]` values.
2. **Soft tissue does not ring; bone rings for 3–20 ms**; the living skull's first resonances lie around ~1 kHz with damping of a few per cent to ~10 % `[K; M1] (M)`.
3. **Speech levels at 1 m**: normal 62, raised 68, loud 75, shouted 82 dB SPL `[K; M2] (H)`; maximal screams ~90–105 dB `[K] (L–M)`.
4. **Impact sound at the shooter arrives d/v_bullet + d/343 s after the shot** (≈115 ms at 20 m with a handgun) `[K] (H)`.
5. **Blood jets are silent at the wound** (exit ≤ 5.5 m/s); the sound is spray landing `[K] (H)` with `[R1-06 §8.1]`.
6. **Bubble ("plink") frequency in blood ≈ 3.2 / radius(m)** Hz; floor pools (2.5 mm) are too shallow to plink `[K; M3] (H)`, `[R1-03 §10]`.
7. **Breath-sound power rises ~flow^1.75–2**; tracheal sound 100–1,500 Hz `[K; M4] (M)`.
8. **CORSA**: crackles < 20 ms (fine 2CD < 10 ms, coarse > 10 ms); wheezes ≥ 100 ms and > 100 Hz; stridor is loud, high-pitched and inspiratory with upper-airway narrowing `[K; M5] (H)`.
9. **Small chest holes hiss or whistle (20–50 m/s), large ones slurp and bubble (5–10 m/s)** `[K] (H)` physics, `[E]` values, threshold from `[R1-04 §9]`.
10. **Tracheal wound below the cords → aphonia** `[K] (H)`; aspiration killed 36.5 % of cut-throat victims in a 74-case series `[S8]`.
11. **Screams: roughness AM 30–150 Hz** `[S2]`; pain vocal F0, loudness and nonlinear phenomena rise with pain `[S3]`; individual pitch is preserved into screams `[S3]`.
12. **SPL rises 8–9 dB per doubling of subglottal pressure**; screaming needs ~30–60 cmH₂O `[K; M7] (M)`, so the voice fades with shock.
13. **Pain face**: AU4 + AU6/7 + AU9/10 + AU43 (PSPI 0–16) `[S1]`; eyes shut in pain vs wide (AU5) in fear `[K] (M)`.
14. **Fear prototype**: AU1+2+4+5+7+20+26 `[K; M11] (H)`.
15. **Central facial palsy spares the forehead and eye closure and may spare emotional smiling; peripheral palsy takes the whole half-face with incomplete eye closure and Bell's phenomenon** `[S4]` `[S5]` `[K] (H)`.
16. **Cyanosis is central when the tongue is blue and peripheral when only the extremities are**; lips lag arterial saturation by ~5–15 s and fingers by ~15–30 s `[K; M27] (M)`.
17. **Capillary refill ≤ 2 s is normal**; > 3 s means poor perfusion `[K] (H)`.
18. **Apnoea at rest on room air: SpO₂ holds > 90 % for ~1–2 min, then falls steeply**; struggling halves this `[K; M28] (M)`.
19. **Broca speech ≈ 10–50 words/min with 1–5 s pauses vs 150–190 normal; Wernicke's jargon is fluent with normal prosody; ataxic speech is scanning with explosive loudness** `[S10]` `[S11]` `[S12]` `[K; M9] (H)`.
20. **The face does not keep its last expression after death**; cadaveric spasm is rare and affects the hands `[K] (H–M)`.
21. **Saccade duration ≈ 21 ms + 2.2 ms/°** `[K; M18] (H)`; blink rate 15–20/min at rest, slow (300–500 ms) blinks in shock `[K] (M)`.
22. **Basal tears 1–2 µL/min; the conjunctival sac overflows beyond ~25–30 µL**; a blow to the nose makes the eyes water within seconds `[K; M19] (M–H)`, `[E]`.

---

## 18. QA priority list (open the source and confirm before hard-coding)

1. **Measure the game's own foley at 1 m** (meat and bone slaps, ballistic gelatin strikes, 5 kg padded-ball drops on concrete, tile and wood) with a calibrated meter; replace the `[E]` (L) dB values of §2–§4.
2. Skull resonance frequencies and damping in vivo `[M1]`; long-bone modes `[M33]`.
3. Speech-level table `[M2]` `[M31]` and the scream level range.
4. Minnaert and drip-sound mechanism `[M3]`; check that blood drips into a 2–3 mm pool never produce a ringing bubble (a short test with animal blood or a blood simulant of matching viscosity and surface tension).
5. Breath-sound flow exponent and spectra `[M4]`; CORSA definitions `[M5]`; snoring and stridor frequency ranges.
6. Scream acoustics `[S2]` `[M8]` `[M34]` and pain-vocalisation findings `[S3]` `[M15]`: roughness band, F0 ranges, NLP fractions. The §6.3 formulas are `[E]` fits to these trends.
7. Subglottal pressure–SPL–F0 relations `[M7]`.
8. Formant values `[M6]` and vocal-tract scaling.
9. Dysarthria features `[M9]` `[S10]`; aphasia speech rates `[S11]` `[S12]`.
10. Pain-face clusters and expressivity shares `[M10]`; FACS prototypes `[M11]`.
11. Central palsy details `[S4]`; House–Brackmann wording `[M12]`; Bell's phenomenon prevalence `[S5]`; temporal-bone palsy rates `[M23]`.
12. Cyanosis ramps (render tests against clinical photographs under D65); colour lag `[M27]`; apnoea desaturation times `[M28]`.
13. Pupillary dilation to pain `[M14]`; tear volumes and rates `[M19]`.
14. Sweat gland densities `[M30]`.
15. Godot 4.5 class names and defaults used in §14 (generator, polyphonic, randomizer, 3D attenuation filter defaults, limiter effect, reverb areas).

---

## 19. References

### 19.1 Sources located by web search in sibling sessions (`[S#]`)

Found by web search in earlier sessions of this project and listed in the sibling documents named in brackets. They were read then through search summaries only and **were not re-read in this session**.

- **[S1]** Prkachin KM; Prkachin & Solomon Pain Intensity (PSPI), as summarised in: Automatically detecting pain using facial actions. https://pmc.ncbi.nlm.nih.gov/articles/PMC3296481/ ; https://pmc.ncbi.nlm.nih.gov/articles/PMC6942457/ (R2-02 [S39])
- **[S2]** Arnal LH, Flinker A, Kleinschmidt A, Giraud AL, Poeppel D. Human screams occupy a privileged niche in the communication soundscape. *Curr Biol* 2015. https://www.cell.com/fulltext/S0960-9822(15)00737-X (R2-02 [S40])
- **[S3]** Vocal communication of simulated pain. *Bioacoustics* 2018. https://www.tandfonline.com/doi/abs/10.1080/09524622.2018.1463295 ; Vocal communication and perception of pain in childbirth vocalizations. 2025. https://pubmed.ncbi.nlm.nih.gov/40176506/ ; Individual differences in human voice pitch are preserved from speech to screams, roars and pain cries. *R Soc Open Sci* 2020. https://royalsocietypublishing.org/rsos/article/7/2/191642 (R2-02 [S41])
- **[S4]** Analysis of upper facial weakness in central facial palsy following acute ischemic stroke. https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11767383/ (R2-01 [S36])
- **[S5]** Bell's phenomenon. https://en.wikipedia.org/wiki/Bell%27s_phenomenon ; American Academy of Ophthalmology, why eyes roll back during a knockout. https://www.aao.org/eye-health/ask-ophthalmologist-q/boxers-eyes-rolling-back-in-head-after-knockout (R2-02 [S54]; R2-01 [S69])
- **[S6]** Davis GA et al. International consensus definitions of video signs of concussion in professional sports (includes the "blank or vacant look" sign). *Br J Sports Med* 2019. https://pubmed.ncbi.nlm.nih.gov/30954947/ (R2-02 [S36])
- **[S7]** Measurement of head impact due to standing fall in adults using anthropomorphic test dummies (head impact 2.0–7.4 m/s). *Ann Biomed Eng* 2015. https://link.springer.com/article/10.1007/s10439-015-1255-1 (R2-02 [S51])
- **[S8]** An autopsy study of 74 cases of cut throat injuries. https://www.sciencedirect.com/science/article/pii/S2090536X14000781 (R2-04 [S19]; R1-02 [R13])
- **[S9]** Pupillometry in brain death: differences in pupillary diameter between paediatric and adult subjects. https://pubmed.ncbi.nlm.nih.gov/26184095/ (R2-04 [S18]; R2-01 [S73])
- **[S10]** Scanning dysarthria (GPnotebook). https://gpnotebook.com/pages/neurology/scanning-dysarthria (R2-01 [S16])
- **[S11]** Wernicke aphasia (StatPearls). https://www.ncbi.nlm.nih.gov/sites/books/NBK441951/ (R2-01 [S12])
- **[S12]** Associations between lesion size, lesion location and aphasia in acute stroke. https://www.tandfonline.com/doi/full/10.1080/02687038.2020.1727838 ; The neuroanatomy of Broca's aphasia. https://www.frontiersin.org/journals/language-sciences/articles/10.3389/flang.2025.1496209/full (R2-01 [S13])
- **[S14]** Walilko TJ, Viano DC, Bir CA. Biomechanics of the head for Olympic boxer punches to the face (effective mass, fist speed, force). *Br J Sports Med* 2005. https://pubmed.ncbi.nlm.nih.gov/16183766/ (R2-02 [S28])
- **[S15]** Lempert T, von Brevern M. The eye movements of syncope. *Neurology* 1996. https://pubmed.ncbi.nlm.nih.gov/8780096/ (R2-02 [S27]; R2-04 [S2])
- **[S16]** On the pathophysiology and treatment of akinetic mutism. https://www.sciencedirect.com/science/article/pii/S0149763419301447 (R2-01 [S9])

(ID S13 is unused.)

### 19.2 Literature and standards recalled from memory (`[K; M#]`; not opened in this session; verify)

- **[M1]** Håkansson B, Brandt A, Carlsson P, Tjellström A. Resonance frequencies of the human skull in vivo. *J Acoust Soc Am* 1994;95(3):1474–1481.
- **[M2]** ANSI S3.5-1997. Methods for calculation of the Speech Intelligibility Index (standard speech spectrum levels for normal, raised, loud and shouted speech).
- **[M3]** Minnaert M. On musical air-bubbles and the sounds of running water. *Phil Mag* 1933;16:235–248; Phillips S, Agarwal A, Jordan P. The sound produced by a dripping tap is driven by resonant oscillations of an entrapped air bubble. *Sci Rep* 2018;8:9515.
- **[M4]** Gavriely N, Cugell DW. *Breath Sounds Methodology*. CRC Press, 1995; Pasterkamp H, Kraman SS, Wodicka GR. Respiratory sounds: advances beyond the stethoscope. *Am J Respir Crit Care Med* 1997;156:974–987.
- **[M5]** Sovijärvi ARA, Dalmasso F, Vanderschoot J, et al. Definition of terms for applications of respiratory sounds (CORSA). *Eur Respir Rev* 2000;10(77):597–610.
- **[M6]** Peterson GE, Barney HL. Control methods used in a study of the vowels. *J Acoust Soc Am* 1952;24:175–184.
- **[M7]** Titze IR, Sundberg J. Vocal intensity in speakers and singers. *J Acoust Soc Am* 1992;91:2936–2946; Titze IR. *Principles of Voice Production*. 1994.
- **[M8]** Frühholz S, Dietziker J, Staib M, Trost W. Neurocognitive processing efficiency for discriminating human non-alarm rather than alarm scream calls. *PLoS Biol* 2021;19(4):e3000751.
- **[M9]** Darley FL, Aronson AE, Brown JR. Differential diagnostic patterns of dysarthria. *J Speech Hear Res* 1969;12:246–269; Duffy JR. *Motor Speech Disorders*. Elsevier.
- **[M10]** Prkachin KM. The consistency of facial expressions of pain: a comparison across modalities. *Pain* 1992;51:297–306; Kunz M, Lautenbacher S. The faces of pain: a cluster analysis of individual differences in facial activity patterns of pain. *Eur J Pain* 2014;18(6):813–823; Kunz M, Meixner D, Lautenbacher S. Facial muscle movements encoding pain — a systematic review. *Pain* 2019;160(3):535–549.
- **[M11]** Ekman P, Friesen WV, Hager JC. *Facial Action Coding System* (2nd ed.). 2002; EMFACS emotion prototypes.
- **[M12]** House JW, Brackmann DE. Facial nerve grading system. *Otolaryngol Head Neck Surg* 1985;93:146–147.
- **[M13]** Jimenez J, Scully T, Barbosa N, et al. A practical appearance model for dynamic facial color. *ACM Trans Graph* (SIGGRAPH Asia) 2010;29(6):141.
- **[M14]** Chapman CR, Oka S, Bradshaw DH, Jacobson RC, Donaldson GW. Phasic pupil dilation response to noxious stimulation in normal volunteers. *Psychophysiology* 1999;36:44–52; Larson MD and colleagues, pupillary dilation reflex under anaesthesia (1990s, *Anesthesiology*).
- **[M15]** Anikin A. Soundgen: an open-source tool for synthesizing nonverbal vocalizations. *Behav Res Methods* 2019;51:778–792; Anikin A, Pisanski K, Reby D. Do nonlinear vocal phenomena signal negative valence or high emotion intensity? *R Soc Open Sci* 2020;7:201306. (Method reference only; no code was used.)
- **[M17]** Hippocrates. *Prognostic* (the "facies Hippocratica").
- **[M18]** Bahill AT, Clark MR, Stark L. The main sequence, a tool for studying human eye movements. *Math Biosci* 1975;24:191–204.
- **[M19]** Mishima S, Gasset A, Klyce SD, Baum JL. Determination of tear volume and tear flow. *Invest Ophthalmol* 1966;5:264–276.
- **[M21]** Robinovitch SN, Hayes WC, McMahon TA. Prediction of femoral impact forces in falls on the hip. *J Biomech Eng* 1991;113:366–374.
- **[M22]** Fackler ML. Wound ballistics: a review of common misconceptions. *JAMA* 1988;259:2730–2736 (temporary-cavity timing from gelatin high-speed photography).
- **[M23]** Brodie HA, Thompson TC. Management of complications from 820 temporal bone fractures. *Am J Otol* 1997;18:188–197; and the otic-capsule-sparing vs violating classification literature.
- **[M24]** Fant G, Liljencrants J, Lin Q. A four-parameter model of glottal flow. *STL-QPSR* 1985;26(4):1–13; Rosenberg AE. Effect of glottal pulse shape on the quality of natural vowels. *J Acoust Soc Am* 1971;49:583–590.
- **[M27]** Hamber EA, Bailey PL, James SW, et al. Delays in the detection of hypoxemia due to site of pulse oximetry probe placement. *J Clin Anesth* 1999;11:113–118.
- **[M28]** Benumof JL, Dagg R, Benumof R. Critical hemoglobin desaturation will occur before return to an unparalyzed state following 1 mg/kg intravenous succinylcholine. *Anesthesiology* 1997;87:979–982 (apnoea desaturation curves).
- **[M30]** Taylor NAS, Machado-Moreira CA. Regional variations in transepidermal water loss, eccrine sweat gland density, sweat secretion rates and electrolyte composition in resting and exercising humans. *Extrem Physiol Med* 2013;2:4.
- **[M31]** Pearsons KS, Bennett RL, Fidell S. *Speech Levels in Various Noise Environments*. US EPA-600/1-77-025, 1977.
- **[M32]** Flamme GA, Wong A, Liebe K, Lynd J. Estimates of auditory risk from outdoor impulse noise II: civilian firearms. *Noise Health* 2009;11:231–242.
- **[M33]** Lowet G, Van Audekercke R, Van der Perre G, et al. The relation between resonant frequencies and torsional stiffness of long bones in vitro: validation of a simple beam model. *J Biomech* 1993;26:689–696. (Low confidence in exact title and figures.)
- **[M34]** Schwartz JW, Engelberg JWM, Gouzoules H. What is a scream? Acoustic characteristics of a human call type. *J Acoust Soc Am* 2019;145:1776–1790.
- **[M35]** Klatt DH. Software for a cascade/parallel formant synthesizer. *J Acoust Soc Am* 1980;67:971–995.

Also used as background (method only, no numbers): Farnell A. *Designing Sound*. MIT Press, 2010; Cook PR. *Real Sound Synthesis for Interactive Applications*. A K Peters, 2002; van den Doel K, Kry PG, Pai DK. FoleyAutomatic: physically-based sound effects for interactive simulation and animation. SIGGRAPH 2001. (IDs M16, M20, M25, M26 and M29 are unused.)

---

## 20. Suspicious content

- **None encountered.** No web content was retrieved in this session: all three `WebSearch` calls were refused (shared budget exhausted, 200 of 200), and the single `WebFetch` attempt was blocked by the egress proxy (`EGRESS_BLOCKED`). There were therefore no pages, snippets or code that could carry injected instructions.
- The only material read was the sibling research documents in this repository (`docs/research/01–06`, `docs/research2/01–04`). They were treated as data and contained no instructions directed at the reader.
- Nothing was downloaded, installed or executed. No shell commands were run. No code was copied from any external source; the recipes and pseudocode were written for this document. No install commands or links to executables appear here. Parametric-synthesis tools named in §19.2 are cited as method references only.

