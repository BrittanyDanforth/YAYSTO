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

- An impact force pulse of duration `τc` (roughly a half-sine) has a flat spectrum up to about `1/τc`, a first spectral zero at **`1.5/τc`**, and falls at ≥ 12 dB/octave above that `[K] (H)`.
- **Soft contacts are long, so they sound low and dull. Hard contacts are short, so they sound bright and "cracky".** This single rule explains why a punch thuds and a hammer on a shin cracks.
- Contact duration of a mass `m` on an effective stiffness `k`: `τc = π √(m / k)` `[K] (H)`.

| Contact | Effective mass | Typical `τc` | Force-spectrum first zero (1.5/τc) | What is heard | Tag |
|---|---|---|---|---|---|
| Bare fist to face (Olympic-boxer data: effective mass 2.9 kg, fist 9.1 m/s, peak force ~3.4 kN) | 2.9 kg | **~12 ms** (from `τc = π·p / (2·F)` with p = 26.5 kg·m/s) | ~125 Hz | A dull thud; the audible "smack" comes from skin slap and air, not from the force pulse | [S14] numbers, [E] derivation |
| Head (occiput) on concrete, 5 m/s | 4.5 kg | 2–8 ms (5 ms default) | 190–750 Hz | A "knock" or "crack" with a skull resonance near 1 kHz | `[R2-03 §6]` [E] |
| Steel hammer on scalp over skull | 0.5–0.7 kg head | 1–3 ms | 0.5–1.5 kHz, plus skull modes | Hard "tock"; crack on fracture | [E] (L–M) |
| Steel on bone under thin skin (shin, knuckle, teeth) | — | 0.2–1 ms | 1.5–7.5 kHz | Sharp "click/crack" | [E] (L–M) |
| Hip or trunk on floor | 15–40 kg | 20–80 ms | 20–75 Hz | Heavy "thump", more felt than heard; clothing and air make the audible part | [K; M21] (M), [E] |
| Knuckle-to-skin sliding or palm slap | — | < 1–3 ms (air squeezed out between surfaces) | > 1 kHz | "Slap" | [K] (M) |

Worked stiffness values for the `τc` formula `[E]`: head–concrete `k ≈ 1.8 × 10⁶ N/m` (gives 5 ms and ~320 g at 5 m/s, consistent with `[R2-03 §6.2]`); trunk–concrete `k ≈ 1.2 × 10⁵ N/m` (50 ms for 30 kg).

### 1.2 What rings and what does not

- **Soft tissue does not ring.** Skin, fat and muscle are highly damped viscoelastic materials. Flesh impacts have no audible resonance; their "wet" character comes from fluid films breaking, air pockets collapsing and skin slapping `[K] (H)`.
- **Bone rings briefly.** Cortical bone is stiff and low-loss, but in the body it is wrapped in soft tissue. The intact living skull has resonances from about **0.8–1.5 kHz upward**, with damping ratios of a few per cent to ~10 % `[K; M1] (M)`. Long bones have lowest bending modes of a few hundred Hz in vivo `[K; M33] (L)`. The ring therefore lasts only **3–20 ms**.
- **Hard floors and objects ring.** Tile laid over voids, wooden floors, metal grates, dropped weapons and keys ring for tens to hundreds of ms and are often the loudest part of a fall `[K] (H)`.
- **Clinical percussion is a good analogy for body regions** `[K] (H)`: over air-filled lung the note is **resonant** (lower, longer); over gas-filled stomach it is **tympanic** (drum-like); over liver, thigh and heart it is **dull** (short, damped); over a chest full of blood (haemothorax) it is **stony dull**. Use the same three characters for blows and bullet strikes to thorax, stomach and solid regions.

### 1.3 Level references

| Source | Level at 1 m | Tag |
|---|---|---|
| Quiet nasal breathing | 15–25 dBA | [E] (M) |
| Normal speech / raised / loud / shouted | **62 / 68 / 75 / 82 dB SPL** (average speech levels) | [K; M2] (H) |
| Maximal adult scream | 90–105 dB SPL (default 98) | [K] (L–M), [E] |
| Handgun muzzle blast (unsuppressed, at the shooter) | 150–165 dB peak | [K; M32] (M) |
| Suppressed handgun or rifle | still ~125–140 dB peak | [K; M32] (L–M) |

- The **gunshot report is 60–90 dB louder than a bullet striking flesh.** Near the gun the impact is masked. It becomes audible when the impact is far enough away that its sound arrives clearly **after** the report (§2.2), or when the listener is near the target and far from the gun `[K] (M)`.
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
| `impact_band_limit` | `LP` at `1.5/τc`, 12 dB/oct | Hz | Applied to the "force" layer of every impact | [K] (H) |
| `skull_mode1` / `zeta` | 0.8–1.5 kHz (default 1.0) / 0.03–0.10 (default 0.06) | Hz / — | Intact, living | [K; M1] (M) |
| `long_bone_mode1` | 200–1,000 | Hz | Tibia/femur lower; ribs, clavicle, facial bones higher (1–4 kHz) | [K; M33] (L), [E] |
| `soft_tissue_ring` | none | — | No resonant modes on flesh layers | [K] (H) |
| `muzzle_vs_impact` | 60–90 | dB | Duck nothing; rely on arrival-time separation (§2.2) | [K] (M) |

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

**Arrival time of the impact sound at the shooter** `[K] (H)` (physics; speed of sound `c = 343 m/s` at 20 °C): `t = d / v_bullet + d / c`.

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
| Victim's forced grunt | Chest compression, startle | 60–150 ms (startle SCM 62 ms `[R2-02 §1]`) | 100–300 ms | Voice (§6) | Variable | [R2-02] [E] |

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
| `impact_delay_at_shooter` | `d/v_bullet + d/343` | s | Makes the "whop" audible beyond ~20 m | [K] (H) |
| `bone_crack_spl_1m` | 75–95 | dB peak | +6–10 dB over the flesh layer | [E] (L) |
| `crunch_grains` | 3–10 in 5–30 ms | — | Nasal, orbital, comminuted, repeat blows | [E] |
| `skin_puncture_force` | 10–50 (sharp knife) | N | Tick at the give; clothing adds 10–50 % | [K] (L–M) |
| `skin_puncture_spl_0.5m` | 35–55 | dB peak | Near-silent in practice | [E] |
| `punch_contact_time` | ~12 (8–20) | ms | From [S14] impulse and force | [S14] [E] |
| `punch_face_spl_1m` | 70–85 | dB peak | | [E] (L) |
| `skull_modes_intact` | 1.0, 1.7, 2.8, 4.2 kHz; ζ 0.06–0.10 | Hz | ×0.6–0.8 and ζ ×2–3 once cracked | [K; M1] (M), [E] |
| `hammer_ring` | 2–6 kHz, 10–40 ms, −15 to −25 dB | — | Only on bone contact | [E] (L) |
| `crepitus_rate` | 10–60 × joint angular speed (rad/s) | clicks/s | 35–50 dBA; mostly felt | [K] (H) quality, [E] rate |

### Visual/behavioural checklist (impacts)
- A shot at 30 m: the report, then about a tenth of a second later a separate dull "whop" from the target.
- A rib or limb hit adds a sharp crack at the same instant; the victim's grunt follows ~0.1 s later.
- Knife attacks are quiet: fabric, a soft tick, the victim's gasp. The loud part is the victim.
- Hammer on a head: first blows knock hollowly; the fracturing blow cracks; later blows crunch and squelch without any ring.
- A broken nose crunches on the blow and again, fainter, when touched.
- Burning: hiss and sizzle build over the first second of contact, with irregular fat pops.

---

## 3. Blood sounds

### 3.1 The physics that decides whether blood makes a sound

- **Blood jets never hiss.** The exit speed of a liquid jet is at most `√(2P/ρ)`. At 120 mmHg (16 kPa) and ρ = 1,060 kg/m³ that is **≤ 5.5 m/s**; real arterial jets leave at **3.3–4.4 m/s** `[R1-06 §8.1]`. A liquid jet this slow produces no audible flow noise `[K] (H)`. **The sound of arterial bleeding comes from where the jet lands** (spatter patter on surfaces, splashing into a pool, soaking into cloth), not from the wound. Where round one says "hiss" `[R1-03 §6.4]`, read it as spray patter at the landing point.
- **Bubbles make the "plink".** A drop falling into deep liquid can trap an air bubble. The bubble rings at the **Minnaert frequency** `f0 = (1 / 2πa) √(3γp₀/ρ)` `[K; M3] (H)`. In blood this is **`f0 ≈ 3.2 / a`** (a = radius in m): a 0.5 mm bubble rings at ~6.4 kHz, 1 mm at ~3.2 kHz, 2 mm at ~1.6 kHz, 5 mm at ~640 Hz. The frequency rises slightly as the bubble rises (a short upward chirp), and the dripping-tap "plink" is this bubble oscillation driving the surface `[K; M3] (M)`. Thermal and radiation damping dominate at these sizes; blood's higher viscosity (3–4 mPa·s) adds little, so blood bubbles ring much like water bubbles `[K] (M)`.
- **Floor pools are too shallow to plink.** Blood pools spread to **~2.5 mm** `[R1-03 §10]`. A 3.9–4.9 mm drop (30–60 µL `[R1-06 §7]`) falling into a 2.5 mm film hits the floor through it and cannot trap a freely ringing bubble. **Drips into a floor pool make a wet "pat", not a "plink"** `[K] (M)`, `[E]`. Plinks occur only where blood collects deeper than ~1–2 cm (a basin, bath, bucket, hollow).
- **Once the pool gels (5–15 min `[R1-03 §10]`)** drops land on a gel: an even duller, softer "pat".

### 3.2 Event catalogue

| Event | Conditions | Heard | Recipe `[E]` | Level at 1 m `[E]` (L) |
|---|---|---|---|---|
| **Drip on hard dry floor** | 1–15 mL/min; rate = `Q / 50 µL` (20 drops/min per mL/min) `[R1-03 §6.4]`; drops hit at ~3–5 m/s from wound heights 0.5–1.5 m | "Tick"/"tap" | `GRAIN(1–3 ms, BP 1.5–5 kHz)` + a tiny splash `CLOUD(λ 2,000/s, T 5 ms)` | 30–45 dB peak |
| **Drip into a floor pool** | As above, on a fresh pool | Wet "pat" | `GRAIN(2–5 ms, BP 500–2,000 Hz)` + satellite ticks (1–4 mm drops, `[R1-03 §10]`) at −12 dB, 5–30 ms later | 30–45 dB peak |
| Drip onto gelled pool | Pool older than 5–15 min | Soft "pat" | As above, `LP(1.2 kHz)`, −6 dB | 25–40 dB |
| **Drip into deep liquid** | ≥ 1–2 cm deep | "Plink" | Impact `GRAIN(1 ms)` + `BUBBLE(a 0.5–2 mm, τ 3–15 ms, σ +0.1–0.3)` with p(bubble) 0.1–0.5 per drop | 35–50 dB peak |
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
| `minnaert_blood` | `f0 = 3.2 / a` | Hz (a in m) | 1 mm → 3.2 kHz | [K; M3] (H) |
| `plink_min_depth` | 10–20 | mm | Floor pools (2.5 mm) never plink | [K] (M), [E] |
| `bubble_p_per_drop` | 0.1–0.5 | p | Deep liquid only | [E] |
| `bubble_tau` / `chirp` | 3–15 / +10–30 % | ms / — | | [K; M3] (M), [E] |
| `jet_orifice_noise` | none | — | Jet speed ≤ 5.5 m/s | [K] (H) |
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

- **Breath noise is turbulence** at the glottis, pharynx, nose and lips. Its power rises steeply with flow: tracheal sound power grows roughly with **flow^1.75–2** (about +10–12 dB per doubling of flow) `[K; M4] (M)`. Quiet breathing is nearly silent at 1 m; panting is clearly audible.
- **Spectrum**: tracheal breath sound spans ~100–1,500 Hz with energy to ~2 kHz `[K; M4] (M)`. What a listener at 1 m hears is shaped by the exit route:
  - **nose**: a narrower, higher hiss (1–4 kHz), quiet;
  - **open mouth**: noise shaped by the vocal tract, with broad peaks at the open-vowel formants (F1 ~600–900 Hz, F2 ~1,100–1,500 Hz), louder.
- **Route rule** `[K] (M)`, `[E]`: nose at rest; mouth when tidal volume > ~1 L, RR > ~25/min, in pain or panic, when the nose is blocked (blood, fracture) or when unconscious with the jaw open.
- **Standard names and definitions of adventitious sounds** (CORSA) `[K; M5] (H)` unless marked:

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

`[R1-04 §9]`: air enters preferentially through a chest-wall defect larger than about two-thirds of the tracheal diameter (≳ 10–13 mm). The **sound depends on the size of the hole** because the air speed through it does `[K] (H)` physics, `[E]` values:

| Defect | Air speed through it | Heard on inspiration | Heard on expiration | Level at 1 m |
|---|---|---|---|---|
| **Small or slit-like, flap acting as a valve** (≲ 5–8 mm) | High: pleural pressure stays strongly negative (−10 to −40 cmH₂O in distress), giving **~20–50 m/s** | **Hiss or whistle**: broadband peak 1–5 kHz; a tonal whistle when the edge is sharp (`f ≈ 0.2 × v / d`: 30 m/s through 5 mm → ~1.2 kHz) | Bubbling as air and blood are pushed back out; fine froth | 40–60 dBA |
| **Large** (≳ 10–15 mm; shotgun, rifle exit) | Low: ~5–10 m/s, pressure equalises | Little turbulence; the sound is **sucking and slurping** of blood and air: bubble grains (a 2–8 mm) 400–1,600 Hz | Wet bubbling, blood spray, froth welling from the hole | 35–55 dBA |
| Sealed by a hand or dressing | — | Sound stops; a partial seal can squeak or flutter on expiration | — | — |

- Breath rate 30–40/min, shallow, grunting; the victim can say 1–4 words per breath (§6.6).
- `Recipe SUCKING_WOUND` `[E]`: inspiration noise `NOISE → BP(1–5 kHz)` with gain ∝ (v / 30 m/s)^3 (turbulence power grows steeply with speed), optional whistle `MODE`-free sine at `0.2 v / d` with ±5 % flutter; plus `CLOUD` of bubbles ∝ blood in the wound; expiration: bubble cloud + film pops.

### 5.5 Open airway in the neck (cut throat, laryngeal or tracheal wound)

- **All the tidal air passes through the wound**: 0.5–2 L/s through 1–5 cm² gives **2–30 m/s**, heard as a **rushing or hissing** 0.5–3 kHz on both phases `[K] (H)` physics, `[E]` values.
- Blood is always present: loud **bubbling and sucking**, frothy pink blood sprayed from the wound with each cough or forced expiration (0.5–1.5 m) `[R2-04 §2.5]`.
- **Voice** (§7.2): a wound below the vocal cords makes the victim **aphonic** (mouths words; air bubbles and hisses at the neck instead). A wound above the cords (through the thyrohyoid membrane or pharynx) lets a weak, wet, bubbly voice out through the wound.
- Aspiration of blood killed **36.5 %** of the cut-throat victims in one 74-case autopsy series (exsanguination ~50 %) `[S8]`. Expect gurgling and wet coughing from the first breaths.

### Simulation parameters (breathing sounds)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `breath_gain_exp` | 1.0 (0.9–1.0) | exponent on flow (amplitude) | Power ∝ flow^1.75–2 | [K; M4] (M) |
| `breath_ref_level` | nose 20; mouth 25 at 0.5 L/s | dBA at 1 m | | [E] (M) |
| `route_mouth_when` | tidal > 1 L OR RR > 25 OR pain OR nose blocked OR unconscious with jaw open | rule | | [K] (M), [E] |
| `F1_from_jaw` | `300 + 17 × jaw_mm` (250–1,000) | Hz | Also used by VoiceSynth | [E] |
| `snore_f0` | 30–120 | Hz | Palatal; tongue-base adds 0.5–2 kHz noise | [K] (M–L) |
| `stridor_f` | 250–1,000, ×(0.8–1.2) with flow | Hz | 3–6 harmonics | [K] (M–L), [E] |
| `gurgle_lambda` | `40 × flow × min(fluid/20 mL, 1)` | bubbles/s | Audible from 5–10 mL | [E] |
| `gurgle_bubble_radius` | 1–5 (rattle 3–8) | mm | | [E] |
| `crackle_2cd` | fine < 10; coarse > 10 | ms | | [K; M5] (H) |
| `splint_cutoff` | 40–70 % of planned volume; catch 50–150 ms | — | Rib or abdominal pain | [E] |
| `sob_hitches` | 3–6 at 4–8/s, 60–150 ms each | — | | [K] (M), [E] |
| `sucking_small_v` / `large_v` | 20–50 / 5–10 | m/s | Hiss/whistle vs slurp/bubble | [K] (H), [E] |
| `whistle_f` | `0.2 × v / d` | Hz | Strouhal ~0.2 | [K] (H) |
| `neck_airway_v` | 2–30 | m/s | Rushing 0.5–3 kHz + bubbling | [E] |
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
| F0 vs subglottal pressure | +2–6 Hz per cmH₂O | Loud voice is higher-pitched | [K; M7] (M) |
| **Subglottal pressure `Ps`** | Threshold ~3; soft 3–5; conversational 5–10; loud 10–20; shouting 20–40; screaming 30–60 cmH₂O | Limited by respiratory muscle power, lung injury and perfusion (§6.5) | [K; M7] (M) |
| **SPL vs `Ps`** | **+8–9 dB per doubling of `Ps`** | — | [K; M7] (M) |
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
- **roughness**: fast amplitude modulation at **30–150 Hz**, the acoustic signature that makes screams alarming (normal speech modulates at 4–5 Hz) `[S2]`.

NLP become more frequent as **emotional intensity** rises (rather than with negative valence as such) `[K; M15] (M)`; in pain vocalisations, F0, F0 range, loudness and NLP all rise with pain intensity `[S3]`. A person's pitch is individual and is preserved from speech through screams, roars and pain cries `[S3]`.

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
| P(vocalise) per pain spike | `clamp(0.15 × (p − 2), 0, 0.95) × x` | × 0.5 in "fighter" mode; × 0.5 at shock class III; × 0.2 at class IV; 0 when winded or apnoeic |
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
| `spl_per_ps_doubling` | 8–9 | dB | | [K; M7] (M) |
| `f0_per_cmH2O` | 2–6 | Hz | | [K; M7] (M) |
| `ps_by_effort` | soft 3–5; talk 5–10; loud 10–20; shout 20–40; scream 30–60 | cmH₂O | | [K; M7] (M) |
| `scream_f0_male` / `female` | 500–1,000+ / 800–2,000 peak | Hz | Derived from own F0 | `[R2-02 §9.2]` [S3] [E] |
| `scream_roughness` | 30–150 | Hz AM | | [S2] |
| `scream_spl_1m` | 90–105 (default 98) | dB | | [K] (L–M) |
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

States as in `[R2-01 §5.2]`. Normal speech runs at **4–6 syllables/s** (≈ 150–190 words/min) with phrase pauses of 0.2–0.8 s `[K] (H)`.

| Vocal state | Rate | Pauses | Prosody | Articulation | Voice | Other | Tag |
|---|---|---|---|---|---|---|---|
| `DYSARTHRIC_UMN` (unilateral, mild) | 3–5 syll/s | Normal | Normal | Mildly imprecise consonants | Normal | With contralateral lower-face weakness (§9) | [K] (M) |
| `DYSARTHRIC_UMN` (bilateral, spastic) | 2–3 | Short phrases | **Monopitch, low pitch** (F0 range ×0.4) | Imprecise | **Strained-strangled** (pressed, low HNR); hypernasal | — | [K; M9] (H) |
| `DYSARTHRIC_CEREBELLAR` (ataxic) | 3–4 | Irregular | **Scanning: excess and equal stress** on every syllable | **Irregular articulatory breakdowns** | **Explosive loudness** (±6–10 dB syllable to syllable) | Vowels prolonged | [S10] [K; M9] (H) |
| `DYSARTHRIC_BULBAR` (flaccid) | 3–4 | Frequent breaths | Reduced | Weak consonants; **audible nasal air escape** on /p b s/ | **Breathy** (HNR < 10 dB), hypernasal, wet | Weak cough; 3–5 syllables per breath | [K; M9] (H) |
| `NONFLUENT` (Broca) | **0.5–2 syll/s** (≈ 10–50 words/min) | **Long, 1–5 s**, with groping ("uh… m-m…") | Flattened | Phonetic distortions, effortful | Normal | **Telegraphic**; automatic phrases (swearing, "yes", "no") at normal speed | [S12] [K] (H) |
| `JARGON` (Wernicke) | 4–6+ (can be pressured) | Normal | **Normal intonation** | Fluent; neologisms and paraphasias | Normal | Does not stop or self-correct; does not follow commands | [S11] (H) |
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
| **Tracheal or laryngotracheal wound below the cords** | Air escapes before the cords | Everything | **Aphonic**: mouths words | Hiss and bubbling at the wound with each attempt; covering the hole restores a weak voice | [K] (H) |
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
| `speech_rate_normal` | 4–6 | syll/s | | [K] (H) |
| `speech_rate_broca` | 0.5–2 | syll/s | Pauses 1–5 s | [K] (H), [S12] |
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

<!-- CONTINUE-2 -->
