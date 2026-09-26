# Gore Head — Realism Bible (implementation reference)

> **Reference photos:** real forensic reference photos are in the git-ignored folder `refs/` at the repo root (1-8). LOOK at them with the image viewer whenever you build or judge anything wound-, blood-, tissue-, bone-, skull-, brain- or death-related, and compare your renders side by side. Use injury/blood/tissue properties only; never faces or identities. Per-image notes: `gore-game/docs/REFERENCE_NOTES.md` §5.

> Audio removed by the user; the game has no sound. Audio sections below were deleted or reworded to visuals.
> **Visual reference notes:** also apply `gore-game/docs/REFERENCE_NOTES.md` (generic properties of real wounds and blood from forensic reference photos: far more blood coverage, soaked cloth, big dark lumpy pools, shredded irregular wet tissue with clots and strands, varied colours). A clean, dry, uniform or blood-sparse wound fails review like a sticker does.


Project: **Gore Head** — Godot 4.5 (Forward+, GDScript + Godot shaders, Jolt), procedural assets from Blender. The subject is a fictional, procedurally generated adult. No real person is modelled.
Audience: simulation, physiology, VFX, shader, animation and performance engineers.
Status: v1.0, 2026-09-26. Synthesised from the fact-checked research in `docs/research/` (01–06) and, where it adds detail, `docs/research2/` (round 2). Corrected values from the fact-check passes are used throughout. Conflicts between documents are resolved explicitly (marked **Resolved:**).

This is the single document engineers implement from. Every section ends with a **Simulation parameters** table and a **Visual/behavioural checklist**. Section 9 is the acceptance test list reviewers will test the game against.

---

## 0. How to use this document

### 0.1 Evidence status tags

| Tag | Meaning | How to treat it |
|---|---|---|
| **V** | Verified: confirmed by a research fact-check against a source that was actually read (textbook copy, dataset, engine source), or recomputed arithmetic/physics | Hard-code |
| **C** | Consistent: from the cited literature via search snippets or standard textbook teaching, agreed by an independent fact-checker's recall, **not re-read from the source** | Use as default; QA re-check before it is shown to the player as a measurement |
| **E** | Engineering derivation or estimate (arithmetic shown in the research doc) | Tune in engine |
| **G** | Game-design choice inside (or at the edge of) the real range, reason given | Tune freely inside the stated range |

Source keys (all links relative to `docs/`):
- **R01** [research/01_gunshot_wounds.md](research/01_gunshot_wounds.md) — wound ballistics, range of fire, skull, spatter, shotgun.
- **R02** [research/02_sharp_blunt_burn.md](research/02_sharp_blunt_burn.md) — knife, fist, hammer, torch, bruises, facial fractures.
- **R03** [research/03_bleeding_vessels.md](research/03_bleeding_vessels.md) — blood, haemodynamics, shock, wound-flow model, vessels, stains.
- **R04** [research/04_neuro_death_eyes.md](research/04_neuro_death_eyes.md) — brainstem, hemispheres, cord, dying, eyes, post-mortem, state machine.
- **R05** [research/05_body_anatomy_reference.md](research/05_body_anatomy_reference.md) — body frame, landmarks, bones, organs, vessel positions.
- **R06** [research/06_game_gore_tech.md](research/06_game_gore_tech.md) — Godot 4.5 architecture and budgets.
- **R2-01…R2-06** [research2/](research2/) — brain deficits, reactions, falls/ragdoll, agonal movement, severe trauma morphology, sounds/face.
- Primary sources are cited inline as short links (PubMed IDs, StatPearls) where the research docs give them. Full reference lists live in the research docs.

### 0.2 Limits of this synthesis

- All research agents and this synthesis pass had **no working web access for primary medical sources**: the shared WebSearch budget (200 calls) was exhausted and WebFetch to PubMed/PMC/StatPearls was egress-blocked (re-tested in this pass: `pubmed.ncbi.nlm.nih.gov` → `EGRESS_BLOCKED`). Verified (**V**) rows were checked against engine source, GitHub-hosted textbook copies and datasets (HuBMAP vessel table, Prahl haemoglobin table, ANSUR II raw data, Godot 4.5-stable source) as recorded in R03, R05 and R06.
- Per-vessel bleed-out times, eye-lid distributions at death, and most wound-size distributions are **tuning targets** (C/E/G), not measured facts. The QA re-check list is §10.1.

### 0.3 Global conventions

- Colours are sRGB hex under D65 for light-to-medium skin (Fitzpatrick II–III). On dark skin, show pallor, cyanosis and livor mainly in lips, nail beds, conjunctivae and palms [R04 §0.3].
- "Loss" always means **fraction of the victim's own blood volume BV0**, never a fixed mL figure.
- Tables give **range (default)**. Where no default is written, use the midpoint.
- **No sound**: the game has no audio. Speech, cries, moans, grunts and screams are shown only as mouth, jaw, chest and face movement; airway problems are shown by the chest, jaw, lips and froth.

---

## 1. Units, frames and timing

### 1.1 Units

| Quantity | Unit in data and code | Notes |
|---|---|---|
| Length | metres (engine), mm in wound/tissue tables | Convert once at load |
| Volume | mL | Blood, compartments, air |
| Flow | mL/min in tables; mL/s inside the solver | 1 mL/min = 0.01667 mL/s |
| Pressure | mmHg | 1 mmHg = 133.3 Pa = **12.8 mm of blood column**; **0.78 mmHg per cm** of height [R03 §2.2, V] |
| Heart and breathing rate | bpm, breaths/min | |
| Energy / impulse / force | J, N·s, N | |
| Heat flux | kW/m² | Torch |
| Time | s real, s sim, h sim | See §1.3 |
| Angles | degrees in data, radians in code | Incidence θ_inc is measured from the **skin surface** (90° = perpendicular) |

### 1.2 Coordinate frames

**Body frame** (all anatomy data; = Blender convention) [R05 §0.4, V]:
- +Z up, body **faces −Y**, character's **left = +X**. Metres.
- Origin (0, 0, 0): on the floor, midway between the feet, on the standing line of gravity (≈ 5 cm in front of the ankle-joint centres).
- Reference body: male, 1.78 m, 75 kg, ~15 % fat, relaxed A-pose (arms 30° from vertical, palms facing the thighs, thumbs forward).
- Bilateral structures are listed for the **left** side; negate x for the right.

**Head frame** (the existing Blender head, `blender/gore_head/CONTRACT.md`): origin midway between the ear canals, same axis convention.
- **Placement:** `p_body = p_head + (0, +0.020, +1.647)` [R05 §0.4, corrected value 1.647 from ANSUR II tragion–top-of-head 131–134 mm, V].
- The existing head has vertex–ear-canal = 0.125 m (ANSUR II median 0.131–0.134). **Resolved:** do **not** rescale the head. With the origin at 1.647 the vertex sits at 1.772 m (8 mm low-vaulted head, within normal variation). Ear-canal height relative to the shoulders is what the body fit depends on, and it is correct at 1.647. An optional later pass may stretch the vault above the ear line by ×1.064.
- The head's **own geometry is authoritative for head-internal positions** (eyes, teeth, brain). The R05 facial landmark fit differs from the contract head by 6–12 mm in places; use the contract values for anything inside the head and R05 for the neck and body.

| Contract landmark (head frame) | Head frame (m) | Body frame (m) |
|---|---|---|
| Vertex | (0, 0.005, 0.125) | (0, 0.025, 1.772) |
| Glabella | (0, −0.093, 0.035) | (0, −0.073, 1.682) |
| Eyeball centres (r = 0.012) | (±0.032, −0.070, 0.022) | (±0.032, −0.050, 1.669) |
| Nose tip | (0, −0.111, −0.014) | (0, −0.091, 1.633) |
| Mouth centre | (0, −0.094, −0.055) | (0, −0.074, 1.592) |
| Chin bottom (menton) | (0, −0.080, −0.103) | (0, −0.060, 1.544) |
| Ear canals | (±0.072, 0, 0) | (±0.072, 0.020, 1.647) |
| Neck cut plane | z = −0.200 | z = 1.447 (8 mm below the jugular notch at 1.455): **blend head neck into body neck over z 1.47–1.52** [G] |

**Godot frame** [R05 §0.4, R06 §2.2, V]: glTF export maps `(x, y, z)_Godot = (x, z, −y)_body`. The imported character faces +Z (`Vector3.MODEL_FRONT`), left on +X. Head origin in Godot: (0, 1.647, −0.020). When generating geometry in GDScript use `Vector3(x, z, -y)`.

**Rest space** [R06 §0.3, §2.2, V]: the model space of the skinned mesh in its bind pose. All wounds, vessels, organs, paint brushes and SDF volumes are stored in rest space so they stay on the tissue in any pose. Godot skins in a compute pre-pass, so shaders only see posed vertices; the rest position must be baked per vertex into `CUSTOM0.xyz` as **32-bit float** (`ARRAY_CUSTOM_RGBA_FLOAT`; half floats quantise to ~1 mm at 1–2 m from the origin) with `CUSTOM0.w` = dismemberment segment ID.

### 1.3 Real time versus simulated time

Real haemorrhage, herniation and post-mortem processes take minutes to days. The game runs one global **`sim_time_scale`** that multiplies the integration step of the **slow physiological state only**.

**What `sim_time_scale` affects** (integrated with `dt_sim = dt_real × sim_time_scale`): blood volume and all bleed/refill/clot integrators, ICP and haematoma growth, O₂ stores during slow phases, bruise/scab/blister ageing, stain drying (via timestamps in sim minutes), post-mortem clocks (livor, rigor, algor, cornea).

**What it never affects** (always real time): Jolt physics, ragdoll and debris, particles and jets' ballistic motion, and every **cosmetic oscillator** — the heartbeat phase that pulses jets, breathing motion, blinking, saccades, gasps. The heart visibly beats at the *current simulated HR in beats per real second*. At 4× the pool therefore grows faster than the jet suggests; this mismatch is accepted [G].

**Time bands** [R04 §0.3, G]:

| Band | Real phase it covers | Scale (default) | Why |
|---|---|---|---|
| ACUTE | First 60 s after any critical event (hit, collapse, arrest, seizure) and the last 60 s before predicted arrest | **1×** (fixed) | Collapse, eyes and last breaths are the drama; never compress |
| MINUTES | Predicted time to arrest ≤ 30 min sim | **4×** (3–6×) — the default **bleed-out multiplier** | Keeps stage order, removes dead air |
| LONG | Predicted time to arrest 30 min – 6 h sim (slow bleed, epidural haematoma, tamponade) | **15×** (10–30×) | Stages readable in 5–15 min of play |
| POSTMORTEM | After circulatory arrest + 60 s | **120×** (1 h = 30 s); player fast-forward **720×** (1 h = 5 s) | Forensic time-lapse |

**Band selector** (evaluated at 1 Hz) [G]:
```
q_net  = max(Q_loss_total - Q_refill, 1e-3)                  # mL per sim second
t_pred = min(V - V_loc, V - V_pea) / q_net                    # sim seconds to the next of LOC or PEA (ignore passed ones)
if seconds_since_last_critical_event_real < 60 or t_pred/scale_current < 60: band = ACUTE
elif dead_flag or seconds_since_arrest_real > 60:                           band = POSTMORTEM
elif t_pred <= 1800:                                                         band = MINUTES
else:                                                                        band = LONG
sim_time_scale += (target(band) - sim_time_scale) * (1 - exp(-dt_real / 2.0))   # 2 s ease
```
Player options: **Realtime** (1× everywhere), **Standard** (auto, default), **Forensic** (auto + 720× post-mortem, and a scrub bar for post-mortem hours).

**Tick rates** [R06 §3.3, R04 §13.5]: physiology + vessel graph 20 Hz alive, 2–5 Hz dead (worker thread); VFX director 60 Hz interpolating physiology outputs; Jolt 60 Hz (120 Hz optional for close-ups); rivulet agents 30 Hz; floor blood spread 10–20 Hz; skin physiology masks ≤ 1 Hz.

### Simulation parameters (units, frames, timing)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `head_origin_body` | (0, +0.020, 1.647) | m | Midway between ear canals | [R05 §0.4] V |
| `head_origin_godot` | (0, 1.647, −0.020) | m | glTF mapping | [R05 §0.4] V |
| `body_to_godot` | (x, z, −y) | — | Single conversion at export/generation | [R05 §0.4] V |
| `rest_pos_attribute` | CUSTOM0.xyz, RGBA32F; CUSTOM0.w = segment ID | — | Half float gives ~1 mm steps | [R06 §2.2] V |
| `hydro_mmHg_per_cm` | 0.78 | mmHg/cm | Hydrostatic correction for every wound | [R03 §2.2] V |
| `scale_acute / minutes / long / postmortem` | 1 / 4 (3–6) / 15 (10–30) / 120 (FF 720) | × | Band table above | [R04 §0.3] G |
| `band_ease_tau` | 2 | s real | Smooth scale changes | G |
| `physio_tick_alive / dead` | 20 / 2–5 | Hz | Worker thread | [R04 §13.5], [R06 §3.3] |
| `vfx_tick` | 60 | Hz | Interpolates physiology | [R06 §3.3] G |

### Visual/behavioural checklist (timing)
- The first minute after any hit and the last minute before cardiac arrest always play in real time.
- Heartbeat, breathing, blinking and gasps never speed up when the game compresses time; only slow state (blood volume, colour ageing, livor) does.
- Switching bands never pops: pallor, jet height and breathing rate change smoothly over ~2 s.

---

## 2. Wound morphology per weapon

### 2.0 Common rules for all weapons

**Wound record** (CPU, rest space) [R06 §4.4]: `weapon, kind, p_entry, dir, θ_inc, muzzle_distance, region {scalp, face, eyelid/lip, neck, trunk_front, trunk_back, limb, palm/sole}, projectile_d, E_impact, seed, t_created_sim_min, antemortem (bool), per-layer radii, shape_class, collar_w, collar_ecc, soot/stipple radii, fracture set, vessel hits, organ hits, cord hit`. GPU gets the packed subset (≤ 64 SDF wounds per character, 3 × vec4 each).

**Anatomy traversal** [R06 §4.3]: march the rest-space track in 1–2 mm steps and emit one event per structure: `SkinBreach`, `BoneHit`, `OrganHit`, `VesselHit`, `CordHit`. Vessel injury rule: with `d` = distance between track axis and vessel axis, the vessel is injured if `d < r_vessel + r_track`; transected if `d < r_track − 0.5·r_vessel`, otherwise side-lacerated. The temporary cavity can tear a vessel without contact: roll p = 0.1–0.3 for vessels within the cavity radius [G].

**Variation — no two wounds identical** [G]:
- Every range in this section is sampled per wound from a truncated normal: mean = default (or midpoint), σ = (hi − lo)/4, clamped to [lo, hi].
- Shape noise: 2–3-octave 3D noise seeded by `seed`, amplitude as stated (typically 0–15 % of radius), mean-preserving.
- Categorical shapes use the weighted tables given.
- Per character: bone-strength factor ×(0.75–1.25), skin laxity ×(0.8–1.2), subcutaneous fat from body build (R05 §12), bruisability ×(0.7–1.3).
- Rotation of every radial feature (tears, fracture rays) is random; ray counts and lengths are sampled independently.

**Ante- vs post-mortem** [R02 §2.8, R03 §6.3, C]: wounds made after circulatory arrest do not bleed actively (gravity drainage only), gape ×0.5, show no vital reaction (no bruise, no swelling, no red collar colour: collars dry to parchment brown `#6E3A22`, stipples grey-yellow `#B8AE8A`). A blow above ~3× the living bruise threshold can leave a small (≤ 25 % of living size), non-ageing dark red-purple mark.

---

### 2.1 Pistol (default 9 mm Luger 115 gr FMJ)

**Projectile** [R01 §1, V calc]: Ø 9.0 mm, 7.45 g, 360 m/s (350–380), E ≈ 483 J, impulse 2.7 N·s. Body knock-back ≤ 0.04 m/s (75 kg) — **bodies are never thrown**; the visible reaction comes from the nervous system (flinch, collapse). A 5 kg head that absorbs the whole bullet gains ≤ 0.55 m/s [R06 §10.3, V].

#### 2.1.1 Range of fire (muzzle-to-skin distance d)

| Class | d | What appears | Source |
|---|---|---|---|
| Hard contact | 0 (collider penetration ≥ 0, angle to normal < 15°) | Soot inside the track and on bone under lifted periosteum; seared blackened margin 1–3 mm; **muzzle imprint** (stamp of the weapon's front face, 0.5–1 mm abraded lines, bruise `#6A3F5A`); cherry-red CO tissue `#D03A45` within 5–30 mm of the track. **Over bone (scalp, sternum): stellate/cruciate tear 3–6 rays, 5–20 mm each (9 mm)**. Over soft areas (neck, abdomen): round hole with sooty seared rim, no stellate tear. Contact head entrance is **often larger than the exit** | [R01 §3.5] C |
| Angled/loose contact | 0 with gap | Soot fan/pear shape extending **down-range** (where the barrel points); searing heaviest on the shooter side where the muzzle touched | [R01 §3.5] C, E |
| Near contact | < 1 cm | Seared zone with baked-in soot; clumps of unburned powder on the edge; no visible stippling | [R01 §3.1] C |
| Close (soot) | 1–25 cm (max 30) | Dense black inner soot Ø = 1 cm + 0.25·d (d ≤ 10 cm), opacity 0.95 → 0.4; grey outer haze Ø = 3 cm + 0.6·d (d ≤ 25 cm), opacity 0.35 → 0; **soot wipes off**; stippling also present | [R01 §3] C, E |
| Intermediate (stippling) | 1–60 cm (flake powder); ball powder default 90 cm, sparse tail to 120 cm | Red-orange punctate abrasions `#A8432A`–`#C85A33`, 0.2–1.5 mm, **do not wipe off**; pattern Ø D = k·d, k per load 0.19–0.59 (5.7–17.7 cm at 30 cm), D ≥ 16.5 cm at ≥ 61 cm; count ~300–600 at 5 cm, 150–300 at 15 cm, 50–150 at 30 cm, 10–40 near max; Poisson-disc, denser centrally | [R01 §3.1–3.2] C (PMID-level sources S16, S46) |
| Distant | > max stipple range | Hole + abrasion collar only | [R01 §2] C |

Oblique shots: soot and stipple patterns become ellipses, dense and sharp on the gun side, fanning down-range. A shot into a dead body: stipples moist grey-yellow `#B8AE8A`.

#### 2.1.2 Entrance and exit by layer (9 mm FMJ)

| Layer | Entrance | Exit | Shape/other | Source |
|---|---|---|---|---|
| Skin, trunk | **0.37–0.62 × Ø = 3.3–5.6 mm (default 4.5)**; back skin lower end, belly upper end; noise envelope 0.24–0.69 × Ø | 0.5–2.0 × Ø = **5–18 mm**, may be a slit smaller than the entrance | Round; shape noise 0–15 % | [R01 §2.1, §4] C (porcine 5.61 ± 0.57 / 3.33 ± 1.17 mm, [PMID 36006518](https://pubmed.ncbi.nlm.nih.gov/36006518/)) |
| Scalp (over bone) | **0.7–1.0 × Ø = 6.3–9.0 mm (default 7.5)** | Head exit **10–30 mm**, stellate/irregular with bone chips, hair and brain dragged out | | [R01 §2.1, §4.2] C, K |
| Face (lips, cheek) | 0.6–1.0 × Ø = 5.4–9.0 mm; eyelid holes slit-like | Ragged with flaps | Lax tissue | [R01 §2] C |
| Abrasion collar (entrance only) | **1.6–2.4 mm (default 2.0)**, red-brown `#B4533F` fresh, parchment brown `#6E3A22` 1–4 h after death | None | Concentric at 90°; oblique: leading-edge width = w / sin θ_inc (clamp 8w), trailing = w; **widest on the side the bullet came from**; θ < 15° → comet-tail/graze decal | [R01 §2.2] C, E |
| Bullet wipe | Grey-black ring `#3A3A3A` α 0.3–0.6 on the inner margin, optional | — | | [R01 §2.2] K |
| Hole ellipse (oblique) | major = d / sin θ_inc (clamp 4d), minor = d | — | θ < 10° → graze gutter | [R01 §2.2] E |
| Exit shape weights | — | Trunk: circular 0.32, stellate 0.28, irregular 0.24, slit 0.12, crescent 0.04. **Head: circular 0.25, stellate 0.33, irregular 0.30, slit 0.09, crescent 0.03** | Everted edges 1–4 mm; **no collar, soot, stippling or searing, ever** (except shored exits: irregular abrasion 2–10 mm when skin was against a wall/floor) | [R01 §4] C (n = 98) |
| Subcutaneous fat | Track ≈ 1.0 × Ø; fat lobules `#F2D16B` extruded at the exit | | | [R01] K |
| Muscle | Permanent track 1.0–1.5 × Ø (9–13.5 mm); haemorrhagic contusion halo 5–20 mm around it (temporary cavity ≤ 10 cm in gel does not tear elastic muscle) | | Muscle `#8E2A2A` | [R01 §6.1], [R2-05 §11] C, E |
| Skull outer table (entrance) | **1.0–1.2 × Ø = 9.0–10.8 mm** (≥ the skin hole: bone does not recoil) | Exit outer table **1.3–2.5 × inner** (outward bevel) and larger than the entrance | Thin bone (temporal squama 2–5 mm, orbit, maxilla) shows little bevel | [R01 §2.1, §5.2] C |
| Skull inner table (entrance) | **1.3–2.0 × outer = 12–22 mm** (inward cone) | Inner table ≈ bullet Ø at exit | Inner-table fragments driven **into** the brain as a cone along the first few cm; exit fragments carried **outward** into the scalp | [R01 §5.2, §5.4] C, K |
| Brain | Permanent track **1.0–1.5 × Ø = 9–13.5 mm (default 11)**; non-functional destruction zone **radius 18 mm** (axonal injury to 18 mm); temporary cavity 4–10 cm (capped at the 12–13.5 cm endocranial width) resolved instantly (lifetime 5–10 ms) | Extrusion of pulped brain + blood **2–30 mL**, mostly at the exit, oozing over 10–120 s | Grey matter `#B79C94`, white `#E6DACA`, pulp `#9E5A55` | [R01 §6] C (Oehmichen, [PMID 15542271](https://pubmed.ncbi.nlm.nih.gov/15542271/)) |
| Thin flat bone (scapula blade, iliac wing) | Clean round hole ≈ 1.0–1.2 × Ø with bevel on the exit side and radiating cracks | | | [R05 §8.5] C |
| Long bone | Diaphysis: comminuted/butterfly, 3–10 fragments, fissures 2–10 cm, exit enlarged to 2–5 cm with bone chips; metaphysis: **drill hole ≈ Ø**, few cracks (p 0.8 at bone ends) | | Yellow marrow in shafts, fat globules on the blood | [R2-05 §8.4] C, E |
| Heart | Entrance 5–10 mm ragged; exit 10–20 mm; often 2 chambers or septum | Pericardium holed → blood to pleura | | [R2-05 §10.3] C |
| Lung | Track 5–15 mm with dark haemorrhagic rim 5–20 mm; pink froth at openings | | Elastic: little cavitation damage | [R2-05 §11.2] C |
| Liver / spleen / kidney | Liver: round track 1–2 cm, rim 0.5–1 cm, **short stellate fissures 1–3 cm** (AAST III); spleen III–V; kidney radial splits toward the hilum (III–IV) | | Inelastic organs crack | [R2-05 §12] C |

#### 2.1.3 Skull fractures, retention, spatter (9 mm head shot)

| Feature | Value | Source |
|---|---|---|
| Radial fractures from entrance and exit | 0–4 rays, 0–80 mm; cracks outrun the bullet (present before the exit forms) | [R01 §5.4] C |
| Puppe's rule | A new crack stops at an existing crack with p = 0.95 | [R01 §5.4] C/G |
| Heaving (outward-displaced plates) | 1–5 mm, only with intracranial overpressure (contact) | [R01 §5.4] C |
| Vault burst | **Never** from a distant 9 mm (deposited energy 70–230 J; burst needs ≥ 500–700 J); contact adds only +50–150 J | [R2-05 §2.1] E |
| Keyhole defect | θ_inc < 15–20° on skull without full penetration: round head ≈ 1 × Ø (inner bevel) + triangular tail 1–3 × Ø (outer bevel) pointing down-range | [R01 §5.3] C |
| Ricochet/graze threshold on skull | θ_inc < 10–20° | [R01 §8] K |
| Exit probability (head) | 0.6–0.8; if the far table is perforated but no exit: bullet under the scalp p 0.3–0.5 (lump, bruise if alive) | [R01 §8] K |
| Energy loss per skull table | 15–40 % of remaining E | [R01 §8] K |
| Anterior skull-base (orbital roof) fracture in any penetrating head GSW | p = 0.82 | [R01 §5.6] C (n = 147) |
| Raccoon eyes (only while the heart beats) | faint 5–30 min, clear 1–6 h; retrobulbar blood 0.1–2.4 mL, proptosis 0–5 mm; blood from nose/ears | [R01 §5.6] C/G |
| Back-spatter (toward shooter) | **30–320** macro drops (> 0.5 mm) per head shot; v₀ 13–61 m/s (mean ~24); cone half-angle ~57°; bulk within 0.5 m, max 0.7–1.2 m; emitted 0.7–4 ms after impact (same frame); micro-mist ≤ 0.7 m; gun and hand stained only when muzzle ≤ 40 cm | [R01 §7.1] C |
| Forward spatter (exit side) | v₀ ~47 m/s (42–52); half-angle ~27° (18–36); **2–5 × the back-spatter count**; fine spray 0.05–2 m, coarse drops and tissue 1–4 m | [R01 §7.2] C (foam targets) |
| Droplet sizes | mist < 0.1 mm 30–60 %, 0.1–1 mm 35–60 %, 1–4 mm 2–10 %; stain L/W = 1/sin α, tail points in travel direction | [R01 §7.3], [R03 §10.1] V |
| Brain/bone ejecta | Bone chips 2–20 mm; brain clumps 3–40 mm (clumps > 20 mm only with contact) | [R01 §7] K |

**Trunk shots:** small distant trunk entrances bleed little externally; the bleeding is internal (§3). Exits and scalp wounds bleed freely [R01 §7.4, R03 §4.5].

#### Simulation parameters (pistol)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `bullet_d / mass / v0` | 9.0 / 7.45 / 360 (350–380) | mm / g / m/s | 115 gr FMJ | [R01 §1] V calc |
| `impulse` | 2.7 | N·s | `apply_impulse` true value | [R06 §10.3] V |
| `k_hole_trunk / scalp / face` | 0.37–0.62 (0.5) / 0.7–1.0 (0.83) / 0.6–1.0 (0.8) | × Ø | Skin entrance diameter | [R01 §2] C |
| `hole_shape_noise` | 0–15 | % radius | Never a perfect circle | [R01 §2] K/G |
| `collar_w` | 1.6–2.4 (2.0) | mm | Concentric at 90° | [R01 §2.2] C |
| `collar_leading(θ)` | w / sin θ_inc, clamp 8w | mm | Widest toward the shooter | [R01 §2.2] E |
| `hole_major(θ)` | d / sin θ_inc, clamp 4d | mm | Graze gutter < 10° | [R01 §2.2] E |
| `d_contact / near / soot_dense / soot_max / stipple_max` | 0 / 1 / 10 / 25 (15–30) / 60 flake, 90 ball (tail 120) | cm | Range classes | [R01 §3] C |
| `soot_inner_d(d)` / `soot_outer_d(d)` | 1 + 0.25d / 3 + 0.6d | cm | d in cm | [R01 §3] E |
| `stipple_D(d)` | k·d, k 0.19–0.59; ≥ 16.5 at d ≥ 61 | cm | | [R01 §3] E |
| `stipple_dot` | 0.2–1.5 | mm | | [R01 §3.2] K |
| `stellate_rays / length` (contact over bone) | 3–6 / 5–20 | — / mm | 9 mm | [R01 §3.5] K |
| `exit_size_head / trunk` | 10–30 / 5–18 | mm | FMJ | [R01 §4] K |
| `exit_shape_weights_head` | circ 0.25, stell 0.33, irreg 0.30, slit 0.09, cresc 0.03 | p | Renormalised | [R01 §4] C |
| `exit_eversion` | 1–4 | mm | | [R01 §4] K |
| `skull_outer_entry` | 1.0–1.2 | × Ø | | [R01 §5] C |
| `inner_bevel_ratio / outer_bevel_ratio` | 1.3–2.0 / 1.3–2.5 | × | Skip bevel on bone < 4 mm | [R01 §5.2] K |
| `brain_track_d / destruction_r` | 1.0–1.5 × Ø (11 mm) / 18 | mm | Destruction zone = non-functional tissue | [R01 §6] C |
| `brain_extrusion` | 2–30 over 10–120 s | mL | Mostly exit | [R01 §6.2] K |
| `radial_fracture_count / length` | 0–4 / 0–80 | — / mm | | [R01 §5] K |
| `puppe_termination_p` | 0.95 | p | | [R01 §5] G |
| `p_exit_head` | 0.6–0.8 | p | | [R01 §8] K |
| `backspatter_count / v0 / half_angle` | 30–320 / 13–61 (24) / 57 | — / m/s / ° | | [R01 §7] C |
| `forward_count_mult / v0 / half_angle` | 2–5 / 47 / 27 | × / m/s / ° | | [R01 §7] C |
| `skin_perforation_v_min` | 50–75 (60) | m/s | Slower fragments/pellets only bruise | [R01 §2] K |

#### Visual/behavioural checklist (pistol)
- A distant 9 mm entrance on the chest is a ~4–6 mm round hole with a thin red-brown rim — smaller than a pencil, never a coin-sized crater.
- Every entrance changes with muzzle distance: contact = black-rimmed hole (a torn star over bone) with a muzzle stamp; a few cm = soot halo; up to ~60–90 cm = red-brown peppering that does not wipe off; beyond = hole and rim only.
- Oblique shots give an oval hole and a rim widest toward the shooter.
- Head exits are ragged stars or tears 1–3 cm across, edges pushed outward, bone chips and brain dragged out, no dark rim.
- A handgun never explodes the head. Peel the scalp: neat outer-table hole, wider inward cone behind it, 0–4 cracks.
- Back-spatter is a sparse fan of fine dots within ~0.5 m on the gun side; the wall behind the exit gets a denser, narrower cone.

---

### 2.2 Shotgun (12 gauge: 00 buckshot default, #7.5 birdshot alternative)

**Loads** [R01 §1, V calc]: 00 buck = 9 pellets × 8.4 mm × 3.49 g (31.4 g), ~400 m/s, ~2,560 J total (~280 J/pellet), impulse 12.6 N·s (body ≤ 0.17 m/s). #7.5 bird (1 oz) = ~350 pellets × 2.4 mm × 0.083 g (28 g), ~365 m/s, ~1,900 J total (~5.4 J/pellet).

#### 2.2.1 Pattern versus range (cylinder / improved cylinder)

| Range | Skin appearance | Source |
|---|---|---|
| Contact, head | Vault burst (p = 1.0); see 2.2.3 | [R01 §9], [R2-05 §2] C/E |
| Contact / ≤ 0.3 m, body | Single round hole **≈ bore size 20–25 mm**, smooth edge, soot/searing as §2.1.1, wad inside | [R01 §9] C/K |
| 0.3–1 m | Single hole growing linearly to **30–40 mm at 1 m**; wad inside; **4-petal wad abrasion (Maltese cross) at 0.3–1.5 m** | [R01 §9] C |
| 1–2 m | Single hole with **scalloped (crenated)** margin | [R01 §9] C |
| 2–4 m | Central hole + satellite pellet holes | [R01 §9] C |
| > 4–5 m (cylinder), > 6–8 m (tight choke / shot cup) | Separate pellet holes only; wad strikes separately as a 1–3 cm round/oval abrasion out to ~6 m | [R01 §9] C |
| Pattern diameter beyond 1 m | D = 2.5 cm + (1.5–2.8 cm) × (r − 1 m) | [R01 §9] C/G |
| Soot / stippling | As §2.1.1; stippling to ~90 cm | [R01 §9] K |

Pellet holes: use the §2.1.2 skin factors × pellet Ø — 00 buck **3.4–5.2 mm trunk, 5.9–8.4 mm scalp** with a collar; #7.5 bird 1.5–2.5 mm with a tiny collar [R01 §9; **Resolved:** R01's 4–7 mm and R2-05's 6–9 mm reconcile as region-dependent].
Penetration: buck 25–53 cm (perforates the head); birdshot at range 5–15 cm — beyond ~5 m birdshot enters the cranium only through the orbits and thin temporal/occipital squama (≤ 4 mm); eyes are highly vulnerable.

#### 2.2.2 Body at close range
- Trunk ≤ 1 m: single 2–4 cm entrance, massive internal destruction along one wide track; lung/liver/heart hydraulic bursting when the column crosses them (heart: ragged stellate ruptures 3–8 cm, massive haemothorax 1–3 L) [R2-05 §10.3].
- Hand/fingers/wrist amputation possible at ≤ 1 m; whole-limb amputation uncommon; forearm/lower leg near-amputation only at contact [R06 §9.1, R2-05 §8.4].
- Long bone at close range: massive comminution with soft-tissue loss.

#### 2.2.3 Head at contact to ~1 m (burst model) [R2-05 §2, E]
- Deposited energy `E_dep = E_impact × f_dep` (buck ≤ 1 m f 0.5–0.8; bird ≤ 1 m f 0.6–0.9) + contact gas bonus 400–800 J. Thresholds: **E_dep ≥ 500–700 J → vault burst; ≥ 1,000 J → 30–70 % of the brain ejected; ≥ 1,500 J → 50–100 % ejected, Krönlein roll (one or both hemispheres leave largely intact) p 0.3–0.6.**
- Vault fragments 20–80 (median 15–25 mm, largest plates 40–100 mm); 20–60 % leave the head, the rest stay in the scalp "bag" (head collapses, grates when moved).
- Scalp: 3–8 radial flaps, 50–150 mm, everted; entrance 3–5 cm stellate with soot and muzzle imprint (contact).
- Main defect on the far side: crater 8–20 cm or whole upper vault missing; orbital-roof burst → eye proptosis or rupture p 0.3–0.6 per eye.
- Ejecta: fine droplets 20–60 m/s, clumps (5–50 g) 10–40 m/s, plates/masses 5–20 m/s in a 20–40° cone down-range plus a slow 60–90° component; indoor range fine 0.5–3 m, clumps 1–5 m, plates 1–8 m; ceiling deposits with upward angles; fallout 0.2–1.5 s, ceiling drips 1–60 s.
- Behaviour: instant flaccid collapse; a single jerk or extensor stiffening in 0–2 s; irregular twitches ≤ 5–20 s; heart continues 1–10 min pumping blood out of the defect in pulses; breathing absent if the brainstem is destroyed. **Exception:** submental/face-only trajectories can leave the victim conscious (p 0.7–0.9).
- 1–3 m buckshot to the head: 9 pellets in a 3–8 cm group, separate/confluent holes, radial cracks linking them, 0–30 % brain ejected, partial burst possible only at the near end.

#### Simulation parameters (shotgun)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `buck00` | 9 × 8.4 mm, 3.49 g, 400 m/s | — | 31.4 g total | [R01 §1] V calc |
| `bird75` | 350 × 2.4 mm, 0.083 g, 365 m/s | — | 1 oz; 395 for 1⅛ oz | [R01 §1] V calc |
| `single_hole_d(r)` | 20–25 at ≤ 0.3 m → 30–40 at 1 m | mm | Linear | [R01 §9] C/K |
| `scallop / satellite / pellets_only range` | 1.0 / 2.0 / 4–5 (choke 6–8) | m | | [R01 §9] C |
| `pattern_D(r > 1 m)` | 2.5 + (1.5–2.8)(r − 1) | cm | 2.8 cylinder, 1.5 choke/shot cup | [R01 §9] C/G |
| `wad_inside / petals / separate` | ≤ 1.5 / 0.3–1.5 (4 petals) / 1.5–6 | m | | [R01 §9] C |
| `buck_penetration / bird_penetration` | 25–53 / 5–15 | cm | | [R01 §9] C (low-quality sources) |
| `head_burst_E_dep / partial_evisc / full_evisc` | 600 (500–700) / 1,000 / 1,500 | J | Continuous rule | [R2-05 §2.1] E |
| `contact_gas_bonus` | pistol 50–150; shotgun 400–800 | J | Contact/near contact only | [R2-05 §2.1] E |
| `vault_fragments` | 20–80 (contact), 3–20 (buck 1–3 m) | count | Median 15–25 mm | [R2-05 §2.4] E |
| `fragment_leave_frac` | 0.2–0.6 | — | Rest stay in scalp | [R2-05] E |
| `scalp_flaps` | 3–8 × 50–150 mm | — | | [R2-05] E |
| `ejecta_v fine / clump / mass` | 20–60 / 10–40 / 5–20 | m/s | Cone 20–40° + wide slow part | [R2-05] E |
| `post_burst_heart_duration` | 1–10 | min | Pulsatile bleeding from defect | [R04 §2.4] C |
| `sever_gate` | hand/fingers/face only at ≤ 1 m | — | Limb amputation rare | [R06 §9.1] G |

#### Visual/behavioural checklist (shotgun)
- Point-blank to 1 m: one round hole (≈ 2 cm at contact, ~4 cm at 1 m), soot if close, wad in the wound, a four-armed petal bruise at 0.3–1.5 m.
- 1–2 m: scalloped edge; 2–4 m: central hole plus a ring of pellet holes; far: a spray of small holes only.
- Contact to the head splits it: far-side crater, radial scalp flaps, a spray cone of blood, brain and bone down-range; the body drops limp; the heart keeps pumping blood out of the head for minutes; the head is soft and misshapen afterwards.
- Birdshot at range peppers the face with shallow pits and perforates eyes and eyelids; it does not enter the skull except through orbits and thin temporal bone.

---

### 2.3 Knife (default: single-edged, blade 25 mm wide, 120 mm long, sharp tip) [G]

#### 2.3.1 Incised wound (slash: edge drawn along the skin; longer than deep)
- **Margins** clean, straight, not abraded, not bruised; every layer divided at the same level; **no tissue bridges** (vessels, nerves cleanly severed); hairs cut, not crushed [R02 §2.2, C].
- **Tail**: the wound starts deeper and ends in a shallow tail 5–30 mm long; **the tail marks the stroke direction** (at the end). Both ends acute (V). Several passes → several tails or skin tags at one end [R02 §2.2].
- **Gape** (appears in < 1 s by elastic recoil; antemortem edges then swell slightly over minutes–hours) [R02 §2.3, E]:
```
gape_max_mm = L_mm * G(θ) * f_depth * f_region                 (lens-shaped: max at midpoint, 0 at ends)
G(θ)        = G_par + (G_perp - G_par) * sin²(θ)                θ = angle between cut and local tension line
G_par = 0.03–0.05 ; G_perp = 0.15–0.25
f_depth     : epidermis 0 ; partial dermis 0.3 ; full dermis 1.0 ; through galea/platysma/muscle across fibres 1.3–1.6
f_region    : face 1.0 ; forehead 1.0 ; scalp galea cut transversely 1.5 ; scalp galea intact 0.4 ;
              neck 1.2 (×1.5 head extended) ; lips/eyelids 0.7
clamp       : 25 mm face/scalp, 40 mm neck
```
  Tension map: bake Borges relaxed-skin-tension lines (RSTL) for face and neck and Langer's lines for scalp and body as a 2D vector field on the atlas UVs (horizontal on the forehead, radiating around eyes and mouth, near-vertical on the cheek sides, circumferential on the neck). Worked examples: 40 mm dermal cut across the lines gapes 6–10 mm, along them 1–2 mm; 60 mm coronal scalp cut through the galea 12–20 mm; transverse throat cut through platysma 10–25 mm.
- **Depth tiers per stroke** (normal force; scale by sharpness and angle) [R02 §2.4, E]:

| Tier | Depth | Face / forehead | Scalp | Neck |
|---|---|---|---|---|
| Scratch | 0.2–1 mm | Red line, beads of blood | Same | Same |
| Light cut | 1–3 mm | Full dermis; yellow fat in the gape | Dermis | Dermis |
| Moderate | 3–8 mm | Fat and mimetic muscle; facial/labial artery branches | Galea (gapes); periosteum scored | Platysma, **external jugular** (dark steady flow) |
| Hard | 8–25 mm | Cheek full-thickness into the mouth at 15–25 mm; parotid; facial nerve | **Stops at bone**: outer table scored ≤ 1 mm | IJV (< 20 mm deep), then larynx/trachea, then carotid (deeper, medial) |

- **Bone rule** [R02 §2.4, R06 §9.1, C]: a knife never cuts through adult calvaria or a long bone. A forceful **stab** can penetrate the temporal squama (2–5 mm) or the orbital roof/medial wall; it can disarticulate finger joints with effort; costal cartilage cuts easily.
- **Skin resistance**: skin is the most resistant layer; once breached little force is needed [R02 §2.4, C]. Penetration force 10–55 N (default 30 N ± 50 % per knife); blunt tips (screwdriver) ×3; skin tents 0.2–2 mm (mean 1 mm) before puncture.

#### 2.3.2 Stab wound (point driven in; deeper than long)
- **Shape** [R02 §2.5, C]: single-edged blade → one acute end + one squared-off or split "fish-tail" end; double-edged → both acute (spindle). 20–30 % of shallow single-edged stabs render spindle-shaped (only the tapered tip entered). **Twisting in the wound → L-, V- or Y-shaped notch** (not a fish-tail).
- **Length** = blade width − 0 to 2 mm (elastic recoil); longer if the blade is rocked or withdrawn at an angle.
- **Gape**: across tension lines an ellipse with width 20–40 % of length; along them a slit (5–10 %).
- **Track** can exceed blade length by up to +50 % where the wall compresses (abdomen, anterior chest); face 0–10 %.
- **Guard mark**: full-depth thrust leaves a patterned abrasion/bruise from the guard next to the wound.
- **Heart stab chamber weights** (ray-cast first; use as fallback): RV 0.40, LV 0.35, RA 0.15, LA 0.05, multiple 0.05. Slit ≈ blade width 10–30 mm; pericardial slit 1–3 cm often plugged by clot/fat → tamponade [R2-05 §10].
- **Cord**: knife wounds to the back/neck produce Brown-Séquard hemisection in 0.3–0.5 of cord injuries (§4.6). Easiest canal access: lower cervical (C5–C7) and lumbar, between spinous processes; thoracic laminae shield the cord unless the blade angles upward [R05 §9.6].

#### 2.3.3 Knife bleeding character and throat cuts
- Clean-cut vessels are not crushed, so **incised wounds bleed more than lacerations of the same size** (lacerations × 0.3–0.6, except scalp ×1.0) [R02 §2.6].
- Throat cut (fatal series n = 74): skin, platysma and EJV in 100 %; larynx/trachea/carotid/IJV in 91.9 %. Causes of death: exsanguination ~50 %, **aspiration of blood 36.5 %**, venous air embolism ~13.5 % (only with the head above the heart). Self-inflicted-style cuts with the head extended often spare the carotids; a single deep horizontal slash reaches the carotid more readily [R02 §2.4, C].
- Cut trachea below the vocal cords → **aphonia** (the victim mouths words; no air reaches the mouth), bubbling and aspiration-cough spray from the wound [R2-06 §17, R2-05 §18].
- Repeated light strokes render as clustered, parallel, superficial cuts (hesitation-mark morphology) [R02 §2.7].

#### Simulation parameters (knife)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `blade_width / length` | 25 / 120 | mm | Default knife | G |
| `gape_G_perp / G_par` | 0.15–0.25 / 0.03–0.05 | mm per mm | Direction ✓, magnitudes E | [R02 §2.3] E |
| `gape_onset` | < 1 | s | | [R02 §2.3] K |
| `tail_length` | 5–30 | mm | At stroke end | [R02 §2.2] C/K |
| `stab_len_minus_width` | 0 to −2 | mm | | [R02 §2.5] C |
| `stab_ellipse_width_perp / par` | 0.2–0.4 / 0.05–0.1 | × length | | [R02 §2.5] E |
| `stab_overshoot_compressible` | ≤ +50 (face ≤ 10) | % blade | | [R02 §2.5] C/E |
| `skin_penetration_force` | 10–55 (30 ± 50 %) | N | | [R02 §2.5] C |
| `bone_cut_through` | never (score ≤ 1 mm) | — | Stab penetrates temporal squama/orbit only | [R02 §2.4] C |
| `incised_vs_laceration_bleed` | 1 : 0.3–0.6 (scalp 1 : 1) | × | | [R02 §3.6] E |
| `throat_air_embolism_p` | 0.10–0.15 of fatal throat cuts, head above heart only | p | | [R02 §2.4] C/G |
| `stab_chamber_weights` | RV .40 LV .35 RA .15 LA .05 multi .05 | p | | [R2-05 §10] C |
| `postmortem_gape_mult` | 0.5 | × | | [R02 §2.8] E |

#### Visual/behavioural checklist (knife)
- A slash opens instantly into a lens: wide across tension lines, a thin line along them. Edges are razor-straight and clean; the floor shows white-pink dermis, then lobulated yellow fat `#F2D16B`, then red muscle or white galea/periosteum.
- Blood wells along the whole length within 1–3 s, beads, then runs downhill; cut arteries spurt in time with the pulse; neck veins pour dark blood and may bubble and froth on inspiration.
- The stroke ends in a shallow tail. A stab is a slit with one sharp and one square end; twisting adds a notch.
- A knife never cuts through the skull or a long bone; it scratches bone.
- On a dead body new cuts do not bleed or spurt, only drip under gravity.

---

### 2.4 Fist (bare knuckle)

**Forces** [R02 §3.5, C]: untrained adult 500–2,500 N (default 1,200 N; effective mass 1–2 kg at 5–8 m/s → 15–60 J); trained amateur 2,500–3,700 N; Olympic boxers 3,427 ± 811 N at 9.14 ± 2.06 m/s, effective mass 2.9 ± 2.0 kg, head acceleration 58 ± 13 g, 6,343 ± 1,789 rad/s² (Walilko, Viano & Bir 2005, *Br J Sports Med* 39:710, as cited in R02 §3.5; C). Contact duration 8–12 ms [R2-06 §17, E]. Momentum 26–32 kg·m/s (larger than any bullet's).

**Fracture thresholds** [R02 §4.1, C]:

| Structure | Threshold | Default |
|---|---|---|
| Nasal bones | 111–334 N | 220 N (lowest in the face) |
| Mandible lateral (body/angle) / chin | 600–1,500 N / 1.9–3.1 kN | 900 N / 2.5 kN |
| Zygoma | 900–2,000 N | 1,400 N |
| Maxilla | 660–1,780 N | 1,200 N |
| Frontal bone | 3.6–7.1 kN (50 % risk 1.9–2.4 kN flat impactor) | 2.2 kN (50 %) — bare fists essentially never fracture it |
| Orbital floor blow-out | 1.2–1.5 J to the globe | 1.3 J |

**Per-punch damage model** (bare knuckle, adult; × 0.05–0.1 for gloves) [R02 §3.5, E]:

| Target | Punch 1 | Punches 2–5, same spot | Beyond 5–10 |
|---|---|---|---|
| Any face skin | Knuckle-shaped erythema `#E07A6E` at once (fades 10–30 min if no bruise); swelling onset 1–5 min | Bruise visible in 15–60 min, row of knuckle ovals | Confluent bruising, tight shiny swelling |
| Eyebrow (anvil) | Split p 0.02–0.10 untrained / 0.10–0.25 trained | p × 1.5 per prior hit | 2–4 cm linear/crescentic split bleeding into the eye |
| Nose | Epistaxis p 0.6–0.9; fracture p 0.2–0.5 (untrained) | Deviation, crepitus | Septal haematoma (cherry-purple bulge `#6E2A4A`) |
| Lips | Inner-lip laceration against the incisors p 0.2–0.4 | Swelling ×1.5–2, through-and-through possible | Tooth luxation |
| Zygoma | Bruise | ZMC fracture p 0.05–0.2 per hard trained punch | Flat cheek, orbital-rim step, subconjunctival haemorrhage |
| Jaw side | Fracture p 0.05–0.15 per hard hook | Angle fracture typical in assault; 2nd (contralateral) fracture p 0.5 | Malocclusion, step, sublingual haematoma |
| Orbit | Black eye in 12–48 h | Blow-out 5–15 % per direct hit | Enophthalmos masked by swelling |

**Knockout** [R04 §3.6, R2-02 §15, C]: rotational acceleration ≥ ~4,500 rad/s² (25 % concussion risk; hook mean 9,306 rad/s²); jaw strikes cause 54 % of knockouts; tone lost within ≤ 100 ms; LOC 5–60 s (tail 300 s); **fencing response p 0.66, 2–10 s** (max 20 s); concussive convulsion p 0.014 (tonic ≤ 20 s then clonic ≤ 150 s, benign); impact apnoea p 0.1 for 5–30 s; post-KO confusion 5–30 min. The falling head hits the floor at 2.0–7.4 m/s (secondary occipital injury).
**Chest**: commotio cordis (VF) p 0.01–0.03 per hard precordial blow [R04 §8.3, G].

#### Simulation parameters (fist)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `punch_force_untrained / trained / elite` | 500–2,500 (1,200) / 2,500–3,700 / 3,427 ± 811 | N | | [R02 §3.5] C/V |
| `punch_contact_time` | 8–12 | ms | | [R2-06] E |
| `frac_nasal / mandible_lat / chin / zygoma / maxilla` | 111–334 / 600–1,500 / 1,900–3,100 / 900–2,000 / 660–1,780 | N | Defaults in text | [R02 §4.1] C |
| `ko_rot_accel` | ~4,500 (25 % risk) | rad/s² | | [R2-02] C |
| `ko_loc` | 5–60 (tail 300) | s | | [R04 §3.7] C |
| `fencing_p / duration` | 0.66 / 2–10 (max 20) | — / s | | [R04 §3.6] C |
| `concussive_convulsion_p` | 0.014 | p | | [R04 §3.6] C |
| `erythema_fade` | 10–30 | min | | [R02 §3.5] E |
| `bruise_visible_superficial / deep` | 0–30 min / 12–48 h | — | | [R02 §3.2] C |
| `commotio_p` | 0.01–0.03 | per hard chest blow | | [R04 §8.3] G |

#### Visual/behavioural checklist (fist)
- A punch leaves an instant knuckle-shaped red flush; swelling starts within minutes; real bruise colour needs 15 min to hours; deep bruises surface the next day, lower than the blow.
- Skin splits only over bone "anvils": eyebrow first, then cheekbone, nasal bridge, chin, and the inner lip against the teeth.
- A broken nose bleeds at once from both nostrils, deviates and shifts further on the next hit; swelling hides the deformity within an hour.
- A knockout drops the character instantly; two in three show one arm stiffly extended and the other flexed for a few seconds, then slack, with slack-jawed obstructed breathing.
- Punches never fracture the forehead.

---

### 2.5 Hammer (default claw hammer: 0.45–0.7 kg head, round face Ø 25–32 mm, 0.3 m handle) [R02 §5, C/E]

**Energy and force**: committed swing 30–120 J (default 60 J); contact force 2.97–4.68 kN; contact time 1–3 ms; impulse ~3–10 N·s (snaps the head visibly).

**Skull fracture probability** (logistic, per blow; × per-character bone factor 0.75–1.25) [R02 §5.1, R2-05 §7, E]:
- 50 % at **temporal 15 J** (range 10–15; clamp ≥ 10 J), **frontal 23 J**, parietal 30 J, occipital 40 J; logistic slope so that 10 %–90 % spans ×0.6–×1.6 of the 50 % energy [G].
- General skull fracture energy 14–69 J; 50 % fracture force 1.8–12.5 kN.
- So one hard committed blow can fracture the skull, the temple most easily.

**Depressed fracture morphology** [R02 §5.3, C]:
- Outer-table defect **reproduces the hammer face** (round Ø 25–32 mm, or square 35–45 mm for a club hammer) with **sharp, regular** edges; inner table **larger, irregular, bevelled** (a cone of fragments pushed in).
- Oblique blow → **concentrically terraced** depression (stepped arcs, deepest where the face bit first).
- Claw end → **two parallel wounds** or two in line.
- Higher energy adds radiating linear fractures from the rim; broad flat surfaces give radiating/concentric fractures rather than a punched-out hole.
- No pond ("ping-pong") fracture in adults.
- Surgical significance: depression > calvarial thickness (6–8 mm) or > 10 mm links to the dura/brain system.

**Repeated blows at one site** [R2-05 §7.2, E]:

| Blows | Scalp | Bone | Dura / brain | Spatter |
|---|---|---|---|---|
| 1 | Crescentic (angled face edge) or stellate (heavy) laceration 10–40 mm, or circular/square abrasion ring (flat strike); bruise, goose egg | Fracture p per the logistic rule; punched-out face-shaped defect or linear | Contusion under the site | Almost none (no exposed blood yet) |
| 2–3 | Lacerations join, flaps | Depressed 25–40 mm, 5–15 mm deep; 2–6 inner fragments driven in | Dural tear p 0.3–0.6; cortex lacerated | Impact spatter starts; first cast-off trails |
| 4–8 | Ragged defect 40–80 mm with hair and chips | Comminuted mosaic 40–80 mm, 10–30 fragments 5–25 mm; concentric rings; radial lines 50–150 mm | Fragments 10–30 mm deep; brain pulped and extruding | Heavy, with brain particles |
| > 8 | 60–120 mm | Cavity; loss of vault shape; skull-base fractures | Brain exposed and extruding | Very heavy |

- Depression per blow after the first fracture 3–10 mm; 2–6 fragments per blow.
- **Many weak blows** can produce multiple scalp lacerations with **no** fracture and kill by scalp haemorrhage [R02 §5.2, C].

**Scalp lacerations and haematomas** [R02 §3.4, §5.4, C]:
- Laceration only where skin is crushed against bone; force threshold human game value 1.5–3 kN (edged/small face) or 2.5–4 kN (flat); porcine upper anchor 4 kN.
- Laceration morphology: ragged, **abraded and bruised margins**, undermined edges, **tissue bridges** in the floor (pathognomonic), intact hairs crossing.
- Goose egg (subcutaneous): visible in 1–5 min, peaks at 24 h, 2–6 cm dome 0.5–2.5 cm high. Subgaleal: boggy, fluctuant, crosses sutures, can hold hundreds of mL, drains into both eyelids over 24–48 h.

**Temple blow → epidural haematoma** (middle meningeal artery under the pterion): growth 0.3–2 mL/min (default 0.6), lucid interval p 0.2–0.5, evacuation threshold 30 mL; full course §4.7.
**Basal skull signs** [R02 §5.5, C]: haemotympanum 1–6 h (earliest); CSF leak 0–72 h; raccoon eyes (spare the tarsal plate) 24–72 h (p 0.1 at 6–24 h); Battle's sign ≥ 24 h. A direct black eye appears within 24 h and crosses the tarsal plate.
**Limbs**: hammer force (3–4.7 kN) exceeds tibia (2.5–4 kN) and ulna/radius (1–1.5 kN) bending strength on their subcutaneous faces → transverse or butterfly fracture; the muscle-padded femur does not break [R2-05 §8.1].

#### Simulation parameters (hammer)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `hammer_energy` | 30–120 (60) | J | | [R02 §5.2] E |
| `hammer_contact_force / time` | 2.97–4.68 kN / 1–3 ms | — | Jolt contact impulses are estimates; use relative velocity × mass as well | [R02 §5.2] C, [R06 §2.9] V |
| `hammer_face_d` | 25–32 | mm | Round claw hammer | [R02 §5.3] K |
| `skull_frac_E50 temporal / frontal / parietal / occipital` | 15 (≥ 10) / 23 / 30 / 40 | J | Logistic | [R02 §5.1], [R2-05 §7] C/E |
| `depressed_depth_per_blow` | 3–10 | mm | After first fracture | [R2-05 §7] E |
| `fragments_per_blow` | 2–6 | count | | [R2-05 §7] E |
| `mosaic_d` | 40–80 (4–8 blows), 60–120 (> 8) | mm | | [R2-05 §7] E |
| `laceration_force_edged / flat` | 1.5–3 / 2.5–4 | kN | Anvil sites only | [R02 §3.4] E |
| `goose_egg_onset / peak` | 1–5 min / 24 h | — | | [R02 §5.6] C |
| `edh_growth` | 0.3–2 (0.6), stop 150 | mL/min, mL | | [R04 §5.6] G |
| `raccoon_eyes_delay / battle_sign_delay / haemotympanum` | 24–72 h (p .1 at 6–24 h) / ≥ 24 h / 1–6 h | — | Living only | [R02 §5.5] C |

#### Visual/behavioural checklist (hammer)
- First light blows raise goose eggs within minutes and crescentic or star-shaped scalp splits that bleed heavily into the hair; strands of tissue bridge the floor of each split.
- A committed blow leaves a punched-out hole the shape of the hammer face, wider and ragged on the inside; angled blows leave stepped arcs; the claw leaves paired wounds.
- Each further blow worsens the site step by step (depression → mosaic → brain extruding) with more spatter and cast-off each time.

---

### 2.6 Torch (handheld propane/butane)

**Source** [R02 §6.2, C/E]: propane-air flame 1,100–1,250 °C (max ~2,000); butane torch ~1,430 °C; local heat flux inside the visible flame (3–10 cm from the nozzle) **100–250 kW/m² (default 150)**, falling ∝ 1/d² beyond the flame tip.

**Dose model** (per atlas texel) [R02 §6.2, E; four points match the Stoll criterion, V]:
```
t2(q) = 10 s * (q / 10 kW/m²)^(-1.33)        # time to 2nd-degree (blister-level) burn; alt. Stoll form (q/50.2)^(-1.416)
D    += dt / t2(q_local)                      # accumulate while exposed; after-burn: +30 % of the last second's dose over 1–3 s
D ≥ 0.2 erythema | ≥ 1 superficial partial (blisters) | ≥ 2 deep partial | ≥ 3 full thickness | ≥ 10 char | ≥ 40 4th degree
```
At 150 kW/m², t2 ≈ 0.27 s. Pain from skin temperature 43–45 °C; damage accumulates from 44 °C (rate ≈ ×2 per °C to ~51 °C).

**Timeline at one spot, 150 kW/m²** [R02 §6.3, E]:

| Exposure | Tissue | Look | Smell |
|---|---|---|---|
| 0–0.1 s | Hair burns (~233 °C) | Hairs curl, bead into black knobs, white wisps | Sulfurous burnt hair |
| 0.1–0.3 s | Erythema | Red flush around the spot | — |
| 0.3–0.8 s | 2nd degree | Epidermis matte grey-white, wrinkles, lifts | — |
| 0.8–1.5 s | Deep partial → full | Waxy white centre, pale tan, red hyperaemic ring | — |
| 1.5–4 s | Full thickness | Tan-brown leathery eschar `#9B6B43`; skin tightens and puckers | Seared meat |
| 3–8 s | Char | Black `#1A1614`, fine cracks, curled edges, greasy yellow-grey smoke | — |
| 8–20 s | 4th degree | Fat melts, bubbles and spits, small yellow flames; heat fissures along muscle grain (1–5 mm × 1–10 cm, bloodless) | Pork-fat smell |
| > 20 s | Muscle cooked `#5A2A1E` → black; bone on thin sites | Bone ivory → brown (~300 °C) → black (~400 °C) → blue-grey (525–645 °C) → white calcined (> 650 °C) | — |

**Evolution** [R02 §6.4–6.7, C/E]: blister domes (roof translucent, fluid `#F4E7B0`, 3 mm – several cm) start **30 s–5 min** after a D ≈ 1–2 texel forms, 50 % size at ~30 min, full at 2–24 h; **full-thickness burns never blister and are painless**; flame burns often peel at once (grey-white epidermal sheets over moist pink dermis `#E8737A`); burned patches contract 15–35 % along the tension direction (lips retract to show teeth; lid ectropion); Jackson zones: coagulation (dead), stasis (dies over 24–72 h), hyperaemia red rim. **Burned tissue does not bleed.** Torch seals vessels ≤ 1–2 mm at D ≥ 2; arteries and large veins keep bleeding through the char. Pugilistic posture only for sustained whole-body fire; a torch on the forearm can curl the fingers when > 30 % of the flexor compartment reaches D ≥ 40.

#### Simulation parameters (torch)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `torch_flux_in_flame` | 100–250 (150) | kW/m² | Extrapolated beyond 84 kW/m² test data | [R02 §6.2] E |
| `t2(q)` | 10·(q/10)^−1.33 | s | Matches 4.5/6.4/10/16 kW/m² → 30/18/10/5 s | [R02 §6.2] V (Stoll) |
| `dose_thresholds` | 0.2 / 1 / 2 / 3 / 10 / 40 | D | erythema/SPT/DPT/FT/char/4th | [R02 §6.2] E |
| `afterburn` | +30 % over 1–3 s | — | | [R02 §6.2] E |
| `pain_threshold_skin` | 43–45 | °C | | [R02 §6.8] C |
| `blister_onset / half / full` | 0.5–5 min / 30 min / 2–24 h | — | | [R02 §6.4] E |
| `burn_contraction` | 15–35 | % area | Along tension lines | [R02 §6.5] G |
| `cautery_max_vessel` | 1–2 | mm | | [R02 §6.7] K |
| `bone_colour_T` | 300 brown / 400 black / 525–645 blue-grey / > 650 white | °C | Shipman 1984 | [R02 §6.7] C |

#### Visual/behavioural checklist (torch)
- Hair goes first; skin reddens, turns matte grey-white and wrinkles; the epidermis peels in grey sheets; held longer it goes waxy white, tan leathery, then black and cracked; fat bubbles and flares; fissures open along the muscle grain without bleeding.
- Blisters grow over the following minutes, never on full-thickness areas; full-thickness areas give no pain reaction.
- A moving torch leaves a graded trail: char centre, white/tan, blistered margin, red rim.
- The torch stops oozing from small cuts; an arterial jet keeps spurting through the char.

---

### 2.7 Current head implementation versus reality (`blender/gore_head/gore.py`, CONTRACT.md, renders)

Values read from `gore.py` (size s = 1, damage = 1). Fix targets use §2.1–2.6.

| # | Feature | Current implementation | Real (source) | Fix |
|---|---|---|---|---|
| 1 | Bullet entrance, skin hole | `r0 = s·4.5 mm` → **Ø 9.0 mm** ± 16 % ragged noise (up to ~10.4 mm), same on every region | Scalp 6.3–9.0 mm (default 7.5); trunk 3.3–5.6 (4.5); face 5.4–9.0 [R01 §2.1] | `r0 = 0.5·k_hole(region)·Ø`; scalp default **3.75 mm radius**; noise 0–15 % mean-preserving; expose `bullet_d` per weapon |
| 2 | Skull hole vs skin hole | Skull = 0.8 × skin radius (Ø 7.2 mm) | Outer table 1.0–1.2 × Ø = 9.0–10.8 mm, i.e. **larger** than the scalp hole (skin recoils, bone does not) [R01 §2.1] | Size bone from bullet Ø, not from the skin hole: `r_outer = 0.5·Ø·U(1.0,1.2)` |
| 3 | Inward bevel | +0.8 mm radius per mm of depth → inner/outer ≈ 2.5 for 7 mm bone | Inner table 1.3–2.0 × outer [R01 §5.2] | Slope = (ratio − 1)·r_outer / thickness, ratio 1.3–2.0 (≈ 0.2–0.7 mm/mm); no bevel where bone < 4 mm |
| 4 | Abrasion collar | Width 2.2 mm × eccentricity (1 ± 0.45) in a **random direction** → 1.2–3.2 mm, always eccentric | 1.6–2.4 mm, concentric at 90°; eccentric only when oblique, widest toward the shooter [R01 §2.2] | Compute θ_inc from the hit direction vs surface normal; `leading = w/sinθ` (clamp 8w) on the side facing the shooter |
| 5 | Oblique shots | Hole always circular | Ellipse major d/sinθ (≤ 4d); keyhole on skull < 15–20°; graze < 10° [R01 §2.2, §5.3] | Add ellipse, keyhole and graze variants driven by θ_inc |
| 6 | Range of fire | Not modelled (no soot, stippling, searing, stellate contact tear, muzzle imprint, CO colour) | §2.1.1 range classes | Add `muzzle_distance` to hit empties; implement contact/near/close/intermediate/distant looks |
| 7 | Exit shape and size | Always a 6-ray star; core radius 4.8–7 mm plus tears to ~18 mm (span up to ~36 mm); eversion lift up to ~7 mm | Head FMJ exit 10–30 mm; shape circ 0.25 / stellate 0.33 / irregular 0.30 / slit 0.09 / crescent 0.03; eversion 1–4 mm [R01 §4] | Weighted shape classes; cap span at 30 mm for 9 mm FMJ; clamp eversion ≤ 4 mm |
| 8 | Exit spatter | 34 droplets placed on the victim's own scalp 19–68 mm around the exit | Forward spatter leaves the head at ~47 m/s in a 27° cone and lands on the environment (2–5 × back-spatter count) [R01 §7.2] | Move exit spatter to world particles/hero drops; keep only runoff (not spatter) on the skin |
| 9 | Entry spatter | 6 droplets on the skin 6.5–22 mm around the entrance | Back-spatter travels toward the shooter (30–320 drops, bulk < 0.5 m); the skin around an entrance shows soot/stippling at close range, not blood spatter [R01 §7.1] | Remove own-skin spatter at the entrance; emit world back-spatter |
| 10 | Brain | Entry crater Ø 13.6 mm, 8–22 mm deep; exit hernia | Permanent track Ø 9–13.5 mm (default 11) **through the whole brain** to the exit; destruction zone radius 18 mm; 2–30 mL extruded, mostly at the exit; inner-table fragments driven in as a cone [R01 §5.4, §6] | Track tube (entry → exit) with a haemorrhagic tint to r = 18 mm; bone-fragment cone at the entrance |
| 11 | Skull fractures from a bullet | Entrance: none; exit: 8-ray Voronoi crack net to 3 R | Handgun 0–4 radial fractures, 0–80 mm, from entrance **and** exit; Puppe termination p 0.95; frequent orbital-roof fractures (p 0.82) [R01 §5] | Sample 0–4 rays at both holes; later cracks stop at earlier ones; add orbital-roof flag → raccoon eyes over time |
| 12 | Slash gape | Half-width 2.4 mm × (0.55 + 0.8 D) × lens profile, independent of orientation | Gape = L·G(θ)·f_depth·f_region; 0.15–0.25 L across tension lines, 0.03–0.05 L along [R02 §2.3] | Bake an RSTL/Langer vector map on the head UVs; compute θ per cut |
| 13 | Slash tail | Symmetric lens | Deeper start, 5–30 mm shallow tail at the stroke end [R02 §2.2] | Asymmetric depth profile along local X |
| 14 | Knife through bone | Skull opens when depth > 0.88–0.92 ("very deep chops") | A knife never cuts through adult calvaria; it scores ≤ 1 mm; only a stab penetrates temporal squama/orbit [R02 §2.4] | Never open the skull layer for `slash`; add a `stab` kind with the temporal/orbital exception |
| 15 | Blunt split shape | Always a crushed centre + 5 tapered tears once depth > 0.25 | Shape by impactor/angle: crescent (hammer edge, angled), ring abrasion (flat face), stellate (rounded/heavy), Y/irregular (flat surface); only over bone; tissue bridges in the floor; abraded bruised margins [R02 §3.4, §5.3] | Add `impactor` (fist, hammer_face, hammer_claw, flat) and angle inputs; add bridging strands to the split floor |
| 16 | Bruise timing | Full purple bruise (r ≈ 28 mm) and swelling at once | Immediate erythema only; superficial bruise 0–30 min, deep 12–48 h; never yellow < 18 h; swelling onset 1–5 min, peak 24 h [R02 §3.2–3.3] | Drive bruise/swelling by `age_h` (sim time) using the §2.4/§3.10 ramps |
| 17 | Depressed fracture | Irregular noisy ring Ø ~30 mm, 4.8 mm deep, always 7 radial cracks | Outer edge sharp and geometric = hammer face (Ø 25–32 mm or square); inner larger, irregular; terraced when oblique; radial lines only at higher energy [R02 §5.3] | Stamp the face silhouette; add terraced variant; gate radial cracks by energy |
| 18 | Burn | Char, blisters and peeling present instantly, patchy by noise | Dose-driven (D thresholds); blisters appear 30 s–5 min after and grow for hours; full thickness never blisters; char needs D ≥ 10 [R02 §6] | Replace the static field with the per-texel dose accumulator and `age` |
| 19 | Blood drips | Tubes ~0.8–1.4 mm wide, up to 60–90 mm long, random lengths | Rivulets 2–5 mm wide, 0.1–0.4 mm thick; a 50 µL drop runs 3–10 cm and stops; a ≥ 1–10 mL/min trickle keeps it alive; pendant drops release at 30–60 µL (Ø ~4.6 mm) at low points [R03 §10.2] | Width ×2–3, flatter; length from volume; pendant bead at chin/nose/earlobe |
| 20 | Blood colour | One "fresh" colour with red subsurface; pools render saturated scarlet | Thin arterial film scarlet `#C0141E`; venous maroon `#8E1420`; pools ≥ 2 mm near-black red `#5E070C` with colour only at thin edges; Beer–Lambert by thickness and saturation [R03 §9] | Film-thickness-driven Beer–Lambert (μa arterial (0.4, 28, 34)/mm, deoxy (3.0, 26, 50)/mm) and SvO₂ input |
| 21 | Bone chips | Exit: 11 chips ≤ ~3.7 mm, lifted ≤ 5 mm | Chips 2–20 mm carried outward into the scalp at the exit; inner-table chips driven into the brain at the entrance [R01 §5.4, §7] | Enlarge the size range; add the inward cone at the entrance |
| 22 | Layer depths | Muscle at 4 mm, skull at 8 mm, brain at 17 mm below skin | Scalp to bone 5–8 mm (default 6); vault 5.4–8 mm (frontal 7, parietal 6, temporal 2–5, occipital 8–8.6) [R02 §1.1] | Skull top at 6 mm; per-region thickness map (temporal thin) |
| 23 | Contact head entrance | Not possible | Stellate 5–20 mm (9 mm), often **larger than the exit** [R01 §3.5] | Covered by fix 6 |
| 24 | Wound evolution | Static (no ageing, clotting, drying, post-mortem state) | Clot 5–15 min, collar drying, bruise colours, raccoon eyes only while the heart beats [R01 §5.6, R03 §7] | Add `t_created` per hit and the sim clock (§1.3) |
| 25 | Head proportions | Vertex–ear 125 mm; ear canals ±72 mm | ANSUR II 131–134 mm; bitragion 145 mm [R05 §0.4] | Keep; place origin at body z 1.647 (§1.2) |

What the current head gets right: layered wounds with correct order (skin → muscle → skull → brain), thick wound walls showing the layers, outward eversion at exits, inward bevel direction, hammer-face-sized depressed fracture, scalp and face wounds that bleed and run downhill, knocked-out teeth for blunt hits to the mouth.

---

## 3. Circulatory model

### 3.1 Blood volume and blood as a material

- **BV0 (procedural)**: Nadler formula [R03 §1.1, V]: men `BV = 0.3669·H³ + 0.03219·W + 0.6041` L; women `0.3561·H³ + 0.03308·W + 0.1833` L (H in m, W in kg). Reference male (1.78 m, 75 kg) → **5.09 L** (68 mL/kg). Obese bodies: 50–60 mL/kg of actual weight.
  - **Resolved:** R03 used 5.0 L and R04 5.25 L (70 mL/kg) for convenience; both are within Nadler ± 5 %. All thresholds are fractions of BV0, so the choice does not change behaviour.
- Distribution: systemic veins ~64 %, arteries ~13 %, capillaries ~7 %, pulmonary ~9 %, heart ~7 %; stressed volume 25–30 % [R03 §1.2, C].
- Material constants [R03 §1.3]: density 1,060 kg/m³; viscosity 3.5 mPa·s (jets), 4–10 mPa·s (films, pools, low shear, cooling); surface tension 0.056 N/m; capillary length 2.3 mm; haematocrit 41–50 % (M). Hb/Hct do **not** fall for 8–12 h after acute bleeding (keep baseline during a session) [R03 §3.2, V].

### 3.2 Haemodynamic core

**Baseline** [R03 §2, C/V]: HR 70 bpm, BP 120/80 (MAP 93), CO 5.0 L/min, CVP 4 mmHg, RR 14/min, SaO₂ 0.97–0.99, SvO₂ 0.70–0.75, ICP 10 mmHg, core 37.0 °C.

**Compensated shock table** (supine, loss over minutes; interpolate linearly on `loss = 1 − V/BV0`) [R03 §3.3, G fitted to ATLS classes (V, Marino) and shock-index classes]:

| Loss | HR | SBP/DBP | MAP | PP | CO (L/min) | CVP | RR | Cap refill (s) | Skin perfusion × | Mental state | ATLS class |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 0.00 | 70 | 120/80 | 93 | 40 | 5.0 | 4 | 14 | 1.5 | 1.00 | Normal | — |
| 0.10 | 80 | 121/82 | 95 | 39 | 4.7 | 4 | 16 | 1.8 | 0.90 | Normal / slightly anxious | I |
| 0.15 | 92 | 119/84 | 96 | 35 | 4.4 | 3 | 18 | 2.0 | 0.80 | Anxious | I/II |
| 0.20 | 104 | 116/85 | 95 | 31 | 4.1 | 3 | 21 | 2.5 | 0.65 | Anxious, restless, thirsty | II |
| 0.25 | 114 | 110/83 | 92 | 27 | 3.8 | 2 | 24 | 3.0 | 0.55 | Restless, thirsty, nauseated | II |
| 0.30 | 122 | 99/76 | 84 | 23 | 3.4 | 2 | 28 | 3.5 | 0.45 | Anxious → confused | II/III |
| 0.35 | 130 | 88/68 | 75 | 20 | 3.0 | 1 | 32 | 4.0 | 0.35 | Confused, agitated or apathetic | III |
| 0.40 | 138 | 75/57 | 63 | 18 | 2.5 | 1 | 36 | 5.0 | 0.25 | Lethargic, slurred | III/IV |
| 0.45 | 146 | 60/45 | 50 | 15 | 1.9 | 0 | 38, irregular | absent | 0.20 | Obtunded (unconscious if upright) | IV |
| 0.50 | agonal, slowing | 45/32 | 36 | 13 | 1.2 | 0 | gasping 4–10 | absent | 0.10 | Unconscious | IV |
| 0.55 | PEA, slowing | 30/20 | 23 | 10 | 0.6 | 0 | agonal gasps | absent | 0.05 | Unconscious, pre-arrest | IV |
| ≥ 0.60 | arrest | — | < 15 | — | ~0 | — | apnoea | — | 0 | Cardiac arrest | — |

**Realism modifiers** [R03 §3.2, R04 §7.3]:
- `hr_response_scale` 0.8 (0.6–1.0): HR = 70 + 0.8·(HR_table − 70) ± 15 % per victim (real patients are less tachycardic than ATLS) [C].
- **Resolved (bradycardia):** R03 (corrected from a 1,194-patient series: pulse < 100 in 35 % with SBP < 100 and 46 % with SBP < 90, [R03 V2]) and R04 (0.10–0.30 "sudden faint") describe two different things. Implement both: `relative_brady_p = 0.40` — a per-victim trait: HR capped at 90–100 during hypotension; and `sudden_faint_p = 0.20` — one event between 20 % and 35 % loss: HR → 50–70 and MAP −20–30 mmHg for 30–120 s (LOC if upright), then partial recovery.
- Posture: brain-level pressure is ~23 mmHg lower upright (head ~30 cm above the heart); an upright victim faints at **20–30 % loss**; lying flat gives brief partial recovery ("gets up, collapses again") [R03 §3.2, E].
- Slow bleeds (> 60 min for the loss) shift every row by +5 % loss (compensation, refill) [R03 §3.4, G].
- The sight of blood or pain can trigger a vasovagal faint at 0 % loss (p 0.02–0.05 per major wound seen, G) [R03 §3.2 V3].
- SBP stays near normal until ~30 % loss; narrowing pulse pressure and rising HR come first.

**Compensation dynamics** [R03 §3.4, C/G]: table values are targets; state follows with first-order lags — HR τ 3 s (baroreflex onset 1–5 s), SVR τ 15 s, venoconstriction τ 30 s (mobilises 10–15 % of BV). **Stress surge** at injury: SBP +20 (10–30), HR +30 (20–40), decaying τ 120 s — early spurts are stronger. **Transcapillary refill**: 0 at 0 % loss → 4–8 mL/min at ≥ 20 % loss, decaying τ 60 min, cumulative cap **1,000 mL** (**Resolved:** R03/Marino 250–500 mL in the first hour, V, preferred over R04's 50–150 mL/h).

**Arterial-wound shunt solve** (one closed-form step per tick) [R03 §4.1, §5.1, V arithmetic]:
```
CO_avail = CO_table(loss) * pump_fraction * tamponade_mult * tension_mult
G_sys    = CO_table(loss) / MAP_table(loss)                     # systemic conductance (L/min per mmHg)
K        = Σ_arterial_wounds k_i ,  k_i = 0.01805 * A_eff_i[mm²] * tissue_factor_i    # L/min per √mmHg
x        = (-K + sqrt(K² + 4*G_sys*CO_avail)) / (2*G_sys)       # x = √MAP
MAP      = x²  ;  SBP = MAP + PP·2/3 ;  DBP = MAP − PP/3        # PP from the table, scaled by MAP/MAP_table
```
Example (V): 7 mm carotid hole, tissue factor 0.5 → MAP ≈ 48 mmHg and wound flow ≈ 2.4 L/min at once; tissue factor 0.2 → MAP ≈ 71, 1.2 L/min. This single effect produces the near-instant collapse of aortic and carotid wounds.

**Special states that override the table**:

| State | Effect | Source |
|---|---|---|
| Heart destroyed | CO_avail = 0 at once; arterial pressure decays (τ ≈ 2–4 s) | [R04 §8] C |
| Myocardial damage | `pump_fraction` 0–1 by destroyed wall fraction | G |
| Tamponade | CO × 1 below V_t, linear to 0 at 250 mL; V_t = 150 mL (100–200), ×0.5–0.7 when loss > 20 %; CVP = 4 + P_peri (neck veins distend unless hypovolaemic) | [R03 §8.2] V |
| Tension pneumothorax | CO × (1 − 0.6·severity); CVP up; hypotension late | [R04 §9.2] C |
| Neurogenic shock (complete cord ≥ T6; trigger SBP < 100 with HR < 80) | HR 40–60, SBP 70–90, warm pink skin below the level; compensation capped (HR ≤ +10, vasoconstriction ≤ 40 %) → decompensates earlier | [R04 §6.5] C |
| Medulla destroyed (vasomotor loss) | MAP → 40–60 within 30–60 s; HR = intrinsic 118.1 − 0.57·age (≈ 101 bpm at 30 y) until hypoxic bradycardia | [R04 §2.4] C |
| Catecholamine surge after brainstem/head hit | p 0.5: HR 120–160, SBP +20–60 for 10–60 s | [R04 §2.6] L/G |
| Cushing reflex (ICP within 10–20 of MAP) | SBP 160–220, HR 40–60, irregular breathing for 5–30 min before apnoea | [R04 §5.3] C/G |
| Hypoxia | SpO₂ < 0.5 → HR falls toward 30 over 120 s; SpO₂ < 0.4 for > 150 s → PEA | [R04 §1], E (calibrated to apnoea → arrest ≈ 6 min) |
| Circulatory arrest | Arterial pressure decays to mean systemic filling pressure **10 mmHg (7–20)** with τ ≈ 20 s (0–5 mmHg if exsanguinated); only hydrostatic drainage afterwards | [R03 §1.2, §6.3] V/C |

### 3.3 Vessel graph

**Topology** [R03 §11.6]: Tier 1 (default) = one global arterial pressure (above) + one CVP; each vessel segment is a labelled capsule (Ø, parent, waypoints, depth, kind) used for hit tests, flow caps, distal ischaemia and VFX. Tier 2 (optional) = ~60–80 arterial + 40–60 venous Poiseuille conduits and ~20 capillary beds solved at 10–20 Hz (sparse, ~150 unknowns, microseconds).

**Scaling**: Ø × (H/1.78)^0.5 and × 0.9 for female bodies [R03 §11, G]. Waypoints are **body frame, metres, left side** unless ±x or R is given; mirror x for the right. Kind: **E** elastic artery (little spasm, never self-seals), **M** muscular artery (spasm, can self-seal ≤ 3–4 mm), **V** vein. Waypoints are from R05 §10.4/§7.2 where listed; limb and head waypoints marked (E) are this document's fit to R03/R05 landmarks (±10–20 mm).

**Central and neck**

| ID | Vessel | Kind | Ø mm | Rest flow mL/min | Parent | Waypoints (body frame, m) | Landmarks / depth | Initial bleed at normal BP (mL/min) → LOC / death untreated, supine | Self-stop · compress |
|---|---|---|---|---|---|---|---|---|---|
| A01 | Ascending aorta | E | 32 (28–36) V | 5,000 | LV | (0.008,−0.038,1.360) → (−0.008,−0.048,1.405) | Behind left sternal half, 3rd ICS; inside pericardium; 4–6 cm deep | 3,000–6,000 → 5–15 s / 1–3 min | No · no |
| A02 | Aortic arch | E | 27 (25–30) V | 5,000→3,600 | A01 | (−0.008,−0.048,1.405) → (0,−0.020,1.428) → (0.022,0.030,1.418) | Top 2–3 cm below the jugular notch; ends at T4 | as A01 | No · no |
| A03 | Brachiocephalic trunk | E | 12 V | 650–800 | A02 | (−0.002,−0.035,1.430) → (−0.025,−0.030,1.455) | Splits behind the right SC joint | 1,000–2,500 → 30–90 s | No · no |
| A04 | Common carotid L (R from A03, mirrored) | E | 6.5 (6–8; F 6.1) V | 350–450 | A02 / A03 | (0.010,−0.025,1.432) → (0.028,−0.018,1.515) → bifurcation (0.030,−0.012,1.558) | Beside trachea/larynx under the SCM anterior border, IJV lateral; bifurcation at upper thyroid cartilage (C3–C4); 1.5–4 cm deep | **1,000–2,500 (+100–300 distal backflow) → LOC 20–90 s / death 2–5 min** | No · partly (finger) |
| A05 | Internal carotid (cervical) | E→M | 4.8 (4–5.5) V | 220–300 | A04 | (0.030,−0.012,1.558) → (0.024,0.012,1.625) (E) | No neck branches; enters the carotid canal in front of the jugular foramen; 2–4 cm | 500–1,000 → 1–3 min / 3–8 min | No · partly |
| A06 | External carotid | M | 4 (3.5–5) | 100–150 | A04 | (0.030,−0.012,1.558) → (0.050,0.000,1.630) (E) | Ends in the parotid behind the mandibular neck | 200–600 → 3–10 min / 5–20 min | Rarely · yes |
| A07 | Superficial temporal | M | 2.0 (1.5–2.5); branches 1.2–1.8 | 10–30 (per branch 16–18 V) | A06 | (0.050,0.000,1.630) → (0.068,0.002,1.650) → split (0.070,0.000,1.680) → frontal br. (0.055,−0.060,1.720); parietal br. (0.065,0.030,1.740) (E) | ~1 cm in front of the tragus over the zygomatic root (palpable); 3–6 mm deep in scalp connective tissue | 20–60 (both ends), pulsatile jet → scalp-wound course | Poorly (tethered) · yes |
| A08 | Facial | M | 2.5 → 1.5 | 20–40 | A06 | (0.035,−0.012,1.570) → mandible at masseter front edge (0.046,−0.032,1.565) → mouth angle +1.5 cm (0.035,−0.078,1.592) → angular at medial canthus (0.016,−0.072,1.662) (E) | Palpable notch 2.5–3 cm in front of the jaw angle; 5–10 mm deep; labial branches 1–1.5 mm inside the lips | 10–40 (facial/labial, into mouth too) | Partially · yes |
| A09 | Occipital | M | 2.0 | 10–20 | A06 | → (0.032,0.105,1.650) → (0.030,0.105,1.700) (E) | Pierces fascia 2.5–4 cm lateral to the inion at the superior nuchal line; 4–8 mm | 20–60 (scalp) | Poorly · yes |
| A10 | Vertebral | M | 3.5 (3–4) | 70–120 | A14 (subclavian 1st part) | (0.030,−0.008,1.440) → C6 transverse foramen (0.015,0.004,1.518) → foramina up to C1 → loop (0.028,0.035,1.622) → foramen magnum (0.008,0.030,1.630) | In bone canal; 4–7 cm deep | 100–400 → 5–20 min (often contained) | Often contained · no |
| A11 | Basilar | M | 3.5 | ~150–200 | A10 ×2 | (0,−0.004,1.645) → (0,−0.004,1.690) | Front of the pons on the clivus | Intracranial (§3.9) | — |
| A12 | Middle meningeal | M | 1.5–2 | — | Maxillary | → under the pterion (0.058,−0.008,1.682) (E) | Pterion ~3.5 cm above the midpoint of the zygomatic arch; inside the skull | Epidural haematoma 0.3–2 mL/min (§4.7) | — |
| A13 | Coronaries: left main → LAD, circumflex; RCA | M | LM 4.5, LAD 3.5, RCA 3.8 | 225–250 total | Aortic sinuses | LM (0.010,−0.035,1.365) → LAD toward apex (0.082,−0.068,1.285); RCA along right AV groove (−0.035,−0.045,1.330) (E) | Epicardium | Spurts in systole **and** diastole; downstream muscle turns dusky and stops contracting in 1–5 min | No |
| A14 | Subclavian L (R from A03) | E | 8.5 (7–10) | 200–350 | A02 | (0.020,−0.008,1.430) → over 1st rib behind mid-clavicle (0.065,−0.015,1.462) → (0.090,−0.015,1.450) | 1.5–2 cm above mid-clavicle; behind anterior scalene; 3–5 cm deep | 1,000–2,000 → 1–3 min / 3–10 min | No · poor |
| A15 | Internal thoracic | M | 2.5 (2–3) | 20–50 | A14 | (0.030,−0.060,1.440) → (0.030,−0.060,1.290) (E) | 1–2 cm lateral to the sternal edge behind the cartilages | 50–150 into pleura, systemic pressure → LOC 20–60 min | No · no |
| A16 | Intercostals (×11 per side) | M | 1.5–2.5 | 5–15 each | Aorta / A15 | Along the lower inner border of each rib (§7.4 rib table) | Costal groove (vein–artery–nerve top to bottom) | 50–150 → hours | No · no |
| V01 | Internal jugular L (R larger) | V | 14 (10–20) V | 300–700 | → V03 | jugular foramen (0.030,0.030,1.625) → lateral to CCA at C6 (0.040,−0.018,1.515) → behind SC joint (0.028,−0.030,1.448) | Line earlobe → medial clavicle; < 20 mm deep; **collapses when upright; tethered at the root → air entry** | Supine 200–1,000 → 5–20 min / 10–40 min | No · yes |
| V02 | External jugular | V | 5 (4–7) | 20–60 | → V04 | below jaw angle (0.050,0.000,1.570) → across SCM → (0.085,−0.020,1.485) → (0.075,−0.020,1.455) (E) | 3–6 mm under the skin (platysma); visible when distended | 50–200 dark steady; air risk | Sometimes · yes |
| V03 | Brachiocephalic veins | V | 14 (12–16) | — | → V05 | L (0.028,−0.030,1.448) → (−0.020,−0.035,1.440); R (−0.028,−0.030,1.448) → (−0.028,−0.035,1.438) | Behind the manubrium | into mediastinum | No |
| V04 | Subclavian vein | V | 10 (7–12) V | 150–300 | → V03 | (0.090,−0.025,1.450) → (0.028,−0.030,1.448) | In front of anterior scalene; ~5 mm above the apical pleura; held open → air | 200–800 (+ air) → 5–20 min | No · poor |
| V05 | SVC | V | 20 (18–22) V | 1,300–1,700 | → RA | (−0.028,−0.035,1.438) → (−0.028,−0.028,1.378) | Right sternal border; lower half intrapericardial | 500–2,000 → tamponade or mediastinum, 1–5 min | No · no |
| P01 | Pulmonary trunk; L/R pulmonary arteries | E (low P) | 27; 18–22 | 5,000 | RV | (0.022,−0.058,1.378) → (0.012,−0.030,1.405); RPA → (−0.060,0.005,1.385); LPA → (0.055,0.015,1.395) | Mean pressure 15 mmHg | Hilar hit 1,000–4,000 → 30 s–2 min | No |
| P02 | Pulmonary veins ×4 | V | 10–15 | 5,000 total | → LA (0.008,−0.008,1.365) | Hila (±0.050, 0.020–0.025, 1.380–1.388) → LA | | as P01 | No |

**Trunk, abdomen, pelvis**

| ID | Vessel | Kind | Ø mm | Rest flow | Parent | Waypoints (m) | Landmarks / depth | Initial bleed → LOC / death | Self-stop · compress |
|---|---|---|---|---|---|---|---|---|---|
| A20 | Descending thoracic aorta | E | 24 (20–26) V | 3,600 | A02 | (0.022,0.030,1.418) → (0.020,0.030,1.329) → hiatus T12 (0.006,−0.012,1.227) | Left front of vertebral bodies; isthmus = blunt-rupture site | 2,000–5,000 into left pleura → 10–30 s / 1–5 min | No |
| A21 | Abdominal aorta | E | 21 → 18 (F 16.7) V | 3,600 → 1,000 | A20 | (0.006,−0.012,1.227) → renal level (0.008,−0.030,1.180) → bifurcation L4 (0.010,−0.045,1.085) | Just left of midline on the vertebral bodies; bifurcation 1–2 cm below-left of the navel; ~7–8 cm under navel skin (lean ~6) | Free: 1,500–4,000 → 20–60 s / 2–10 min; contained retroperitoneal 100–500 → 5–30 min / hours | No |
| A22 | Coeliac trunk → splenic, common hepatic | M | 7; splenic 4–6; hepatic 4–5 | 800–1,100 | A21 (T12) | (0.006,−0.020,1.215) → splenic along pancreas to hilum (0.095,0.030,1.225); hepatic → porta (−0.030,−0.020,1.230) (E) | Deep | 300–1,000 intraperitoneal | No |
| A23 | Superior mesenteric | M | 7 | 500–700 | A21 (L1) | (0.008,−0.030,1.195) → (0.010,−0.060,1.120) (E) | Behind pancreatic neck | 300–1,000 | No |
| A24 | Renal L / R | M | 5.5 (4–7) | 500–600 each | A21 (L1/L2) | → hila (0.048,0.010,1.180) / (−0.048,0.010,1.160) | Right passes behind IVC | 300–1,000 retroperitoneal (Gerota may contain) → 5–20 min | Partly |
| A25 | Common iliac | E | 10 (8.8–9.9 V) | 350–500 | A21 | (0.010,−0.045,1.085) → (±0.040,−0.030,1.035) | To the SI joint (L5/S1) | 1,000–2,500 retroperitoneal → 2–6 min / 5–15 min | No |
| A26 | Internal iliac | M | 6 (5–7) | 100–150 | A25 | (0.040,−0.030,1.035) → (0.050,0.020,0.980) (E) | Pelvis, gluteal | pelvic | No |
| A27 | External iliac | M | 8 (7–9) | 250–350 | A25 | (0.040,−0.030,1.035) → mid-inguinal point (0.065,−0.068,0.940) | Along the pelvic brim, medial to psoas | 1,000–2,500 | No |
| A28 | Common femoral | M | 9.0 M / 8.2 F V | 250–400 | A27 | (0.065,−0.068,0.940) → profunda origin (0.068,−0.060,0.895) | Mid-inguinal point (midway ASIS–pubic symphysis); NAV lateral→medial; pulse palpable; 2–4 cm deep | **800–2,000 → LOC 2–5 min / death 3–10 min** | No · poor–moderate (junctional) |
| A29 | Profunda femoris | M | 5.5 (5–6) | 100–150 | A28 | (0.068,−0.060,0.895) → (0.090,−0.010,0.800) → (0.095,0.010,0.700) (E) | Posterolateral, deep (4–8 cm) | 400–1,000 → 4–10 min / 8–20 min | Rarely · yes (proximal) |
| A30 | Superficial femoral | M | 6 (5–7) | 150–250 | A28 | (0.068,−0.060,0.895) → under sartorius (0.075,−0.030,0.760) → adductor hiatus (0.080,0.030,0.610) | Anteromedial thigh; 3–6 cm deep | 400–1,000 | Rarely · yes |
| A31 | Popliteal | M | 5.5 (5–7) | 80–150 | A30 | (0.080,0.030,0.610) → (0.092,0.055,0.497) → (0.092,0.055,0.440) | Deepest in the popliteal fossa, on the capsule; 3–5 cm | 300–800 → 5–12 min / 10–30 min | Rarely · yes |
| A32 | Anterior tibial → dorsalis pedis | M | 3 (2.5–3.5) → 2–3 | 30–50 | A31 | (0.092,0.055,0.440) → (0.105,0.020,0.420) → (0.100,−0.005,0.250) → front of ankle (0.097,0.012,0.080) → dorsum (0.105,−0.030,0.050) (E) | DP pulse lateral to the EHL tendon; ankle ~5 mm deep | 50–200 → 20–60+ min / 1–3 h | Often · yes |
| A33 | Posterior tibial | M | 3 (2.5–3.5) | 30–50 | A31 | (0.092,0.055,0.440) → (0.088,0.060,0.250) → between medial malleolus and Achilles (0.075,0.075,0.080) (E) | ~1 cm deep at the ankle | 50–200 | Often · yes |
| A34 | Peroneal | M | 2.5 | 20–40 | A33 | (0.095,0.060,0.420) → (0.120,0.055,0.200) (E) | Along the fibula, deep | 50–150 | Often |
| V10 | IVC | V | 17 (13–21) V | 3,000–3,500 | → RA | L5 (−0.020,−0.035,1.050) → retrohepatic (−0.022,−0.015,1.260) → T8 hiatus (−0.022,−0.010,1.325) → RA (−0.025,−0.015,1.315) | Right of the aorta; retrohepatic part embedded in liver | Infrarenal 500–2,000 (50–200 tamponaded); retrohepatic/hepatic veins 1,000–3,000 → 1–5 min | Partly / no |
| V11 | Hepatic veins ×3 | V | 8–12 | ~1,350 | → V10 | into IVC ~(−0.022,−0.012,1.300) | Just below the diaphragm | 1,000–3,000 | No |
| V12 | Renal veins | V | L 9, R 7 | ~550 each | → V10 | L (0.048,0.010,1.180) → in front of aorta (0.008,−0.045,1.178) → IVC (−0.020,−0.030,1.175); R (−0.048,0.010,1.160) → (−0.022,−0.025,1.165) (E) | Left crosses in front of the aorta below the SMA | retroperitoneal | Partly |
| V13 | Portal vein | V | 11 (10–13) | 1,000–1,200 | SMV + splenic | (−0.005,−0.045,1.175) → porta hepatis (−0.030,−0.020,1.235) (E) | Hepatoduodenal ligament | 500–1,500 → 5–15 min / 10–40 min | No |
| V14 | Common iliac veins | V | 14 (12–16) | ~500 each | → V10 | (−0.020,−0.035,1.050) → (±0.045,−0.020,1.030) (E) | Behind and right of the arteries | pelvic | No |
| V15 | Common femoral vein | V | 12 (10–14) V | 250–400 | → V14 | (0.045,−0.020,1.030) → medial to CFA (0.055,−0.066,0.940) → (0.060,−0.058,0.895) (E) | Medial to the artery, 2–4 cm deep; ~80–90 mmHg at the foot when standing still | 200–600 (more if the leg hangs) → 10–30 min | Sometimes · yes |
| V16 | Femoral / popliteal veins | V | 8–12 / 6–10 | — | → V15 | Alongside A30 / A31 | Deep veins | 100–400 | Sometimes · yes |
| V17 | Great saphenous | V | 4 (3–5; 6–8 at junction) | — | → V15 | in front of medial malleolus (0.060,0.030,0.085) → behind medial femoral condyle (0.060,0.050,0.500) → anteromedial thigh → SFJ 3–4 cm below-lateral pubic tubercle (0.050,−0.065,0.885) (E) | Just under the skin | 20–100 | Yes · yes |

**Upper limb** (A-pose; limb direction d = (0.5, 0, −0.866); medial (palm-side) normal n_m = (−0.866, 0, −0.5); radial side = −Y) (E):

| ID | Vessel | Kind | Ø mm | Rest flow | Parent | Waypoints (m) | Landmarks / depth | Initial bleed → course | Self-stop · compress |
|---|---|---|---|---|---|---|---|---|---|
| A40 | Axillary | M | 6.5 (5–8) | 100–200 | A14 | (0.090,−0.015,1.450) → (0.140,0.000,1.410) → (0.188,0.015,1.350) | Behind pectoralis minor, among plexus cords; 3–5 cm | 600–1,500 → 2–5 min / 5–15 min | No · poor (junctional) |
| A41 | Brachial | M | 4.2 (3.5–5) V | 50–120 | A40 | (0.188,0.015,1.350) → medial bicipital groove (0.231,0.015,1.277) → cubital fossa (0.328,0.005,1.148) | With the median nerve; 1–2 cm deep mid-arm, ~1 cm at the elbow; divides 1–2 cm below the elbow crease | Side laceration ~400 → Class II 3 min, LOC 10–15 min, arrest 15–30 min; transected 200–600 | Sometimes (spasm) · yes |
| A42 | Radial | M | 2.5 (2.2–3.0) | 20–40 | A41 | (0.328,0.005,1.148) → (0.385,0.005,1.043) → wrist (0.447,0.005,0.923) | At the wrist between the FCR tendon and radial styloid, **3–7 mm deep** | 100–300 first min → 20–60 after spasm; stops in 5–20 min after 200–500 mL | **Usually** · yes |
| A43 | Ulnar | M | 2.4 (2.0–3.0) | 20–40 | A41 | → wrist (0.450,0.035,0.924) (E) | Lateral to the FCU tendon/pisiform; 5–10 mm | as radial | Usually · yes |
| A44 | Palmar arches, digital | M | arch 1.5–2; digital 0.8–1.6 | 1–5 per digit | A42/A43 | superficial arch ~(0.475,0.020,0.881) (E) | Arch at the distal border of the extended thumb | 5–30 | Yes · yes |
| V20 | Cephalic / basilic / median cubital | V | 2–5 / 3–6 / 2–5 | — | → axillary | Lateral arm (deltopectoral groove) / medial arm / cubital fossa | Visible; **flatten and vanish in shock** | 5–30 | Yes · yes |

**Capillary beds** (Tier 2 resistance targets: `R_bed = (P_art − P_ven) / Q_rest`) [R03 §2.3, C]: brain 750, coronary 225–250, kidneys 1,100–1,250, liver 1,350 (portal ~1,050 + arterial ~300), skeletal muscle 750–1,000, skin 250–450 (drops 70–90 % in shock), bone 250, spleen 150–300, scalp ~50–100 mL/min.

**Collaterals for distal-stump backflow** (stump pressure 0.3–0.8 × MAP; high for radial/ulnar/carotid, low for end arteries) [R03 §4.4, §11.6]: palmar arches (radial ↔ ulnar); circle of Willis (complete in only 20–50 %: unilateral carotid tolerance varies); external ↔ internal carotid via facial/angular and STA/supraorbital; geniculate network; profunda ↔ popliteal. Scalp and face arteries bleed from **both** cut ends.

**Distal ischaemia**: a bed downstream of a transected artery without collaterals → flow 0; limb pale, cold, pulseless over minutes; irreversible muscle damage at 4–6 h warm ischaemia [R03 §11.6, C].

### 3.4 Bleeding-rate formula for a damaged vessel

Per wound on vessel segment s (Tier 1) [R03 §4, V arithmetic, G factors]:
```
# local pressure
P_art(t)   = DBP + (SBP − DBP) * pulse_wave(phase(t − delay_s))        # §3.5; arteries only
P_local    = arterial: P_art(t) − 0.78 * Δh_cm                         # Δh = wound height above right atrium
             venous:   CVP + 0.78 * (−Δh_cm) + resp_mod(t) + valsalva(t)
             distal stump: stump_frac(s) * MAP − 0.78 * Δh_cm
P_ext      = 0 if open to air, else compartment pressure (haematoma, pericardium, pleura: 0–30 mmHg)
ΔP         = max(P_local − P_ext, 0)
# effective hole
A0         = side laceration: π/4 * hole_d²  (hole_d ≈ min(track_d, 1.2·vessel_d))
             transection:     π/4 * vessel_d²   (both ends; distal end uses stump pressure)
spasm      → target: muscular transected 0.4–0.6 (τ 1–3 min); side laceration 1.1–1.3 (spasm pulls the hole open);
             elastic 0.9; scalp/face tethered 1.0 (fixed)
A_eff      = A0 * spasm * (1 − clot) * (1 − compress)
# three limits; the smallest wins
Q_orif     = 0.6 * A_eff[mm²] * 0.5015 * sqrt(ΔP) * 60                 # mL/min   (v = √(2ΔP·133.3/1060) m/s)
Q_supply   = (MAP − P_hole) / R_upstream                               # Poiseuille, R = 8μL/(πr⁴); matters for Ø ≤ 3 mm
Q          = min(Q_orif * tissue_factor, Q_supply)                     # cardiac limit enforced by the shunt solve (§3.2)
# arrest
if circulatory_arrest: Q = passive_drain(Δh) only (§3.8, §6)
```
- **tissue_factor** [R03 §4.8, G]: 1.0 gaping incised wound exposing the vessel; 0.4–0.6 incised wound under muscle; 0.15–0.3 narrow stab/bullet track > 3 cm deep (blood fills tissue: **expanding pulsatile haematoma**, or drains into a cavity); 0.05–0.1 victim lying on the wound.
- **compress**: reflex clutching 0.3–0.7; firm direct pressure 0.8–0.95 on compressible sites; tourniquet 1.0 (limbs); 0 on non-compressible (trunk, junctional partial 0.3–0.6) [R03 §4.5, G].
- **Pressure dependence**: holes > ~3 mm are orifice-limited (Q ∝ √ΔP); small vessels and ooze are resistance-limited (Q ∝ ΔP). **Critical closing pressure 20–40 mmHg**: small arteries stop in deep shock and **rebleed** when MAP recovers above ~60–65 mmHg (SBP 90–95) [R03 §4.6, C].
- **Heart beating vs not**: pulsatile P_art only while the rhythm produces output; PEA/VF/asystole → arterial pressure decays to MSFP within ~30–90 s, then gravity drainage only.
- **Partial lacerations bleed more than complete transections** of the same muscular artery (no retraction, spasm widens the hole) [R03 §4.4, C].
- Worked example (V): radial 2.5 mm, fully transected, 20 cm feed → orifice pressure ~40 mmHg, ~550 mL/min theoretical; spasm and tissue bring it to 100–300 mL/min in minute 1 and 20–60 mL/min after a few minutes.

**Validation scenarios the model must reproduce** (supine, untreated) [R03 §5.1, R04 §7.5 corrected, E]:

| Scenario | Expected course |
|---|---|
| A. One radial artery cut clean | 100–300 mL/min for ~1 min → spasm → 20–60 mL/min → clot by 10–20 min; total 200–500 mL (Class I); survives |
| B. Brachial side laceration | ~400 mL/min declining; Class II ~3 min, Class III ~5–7 min, LOC 10–15 min, arrest 15–30 min |
| C. Common femoral transection, standing | ~1.2 L/min; Class III ~1.5 min; collapse ~2 min; arrest 4–8 min |
| D. Unilateral carotid, open neck | MAP 50–70 at once (shunt); LOC 20–60 s; arrest 2–5 min |
| E. Many small wounds 30–50 mL/min | Class II 15–30 min; Class III 35–50 min; LOC 60–90 min |
| F. Scalp laceration 20 mL/min | Class II after 40–60 min; Class III possible after ~1.5 h |
| G. Heart stab with tamponade | A few mL externally; rising HR, distended neck veins, falling BP over 5–30 min; PEA |
| H. 1 L/min constant-source check | LOC 2.4–2.8 min, PEA 2.9–4.0 min (R04 corrected, V arithmetic) |
| I. 100 mL/min | LOC 24–28 min, PEA 29–40 min (R04 corrected, V arithmetic) |

### 3.5 Pulsatile arterial spurting

- **Jet exists** only if: vessel kind E/M (or LV/coronary), wound open to air (tissue_factor ≥ 0.5 and skin gap ≥ vessel Ø), and **P_local ≥ 25–30 mmHg**. Spurting is gated by **pressure, not flow**: a small cut artery (digital, radial after spasm, STA) still spurts visibly [R06 §8.1, V/C].
- **Exit speed** `v = Cv · √(2·P·133.3/1060) = 0.351·√P m/s` with Cv = 0.7 (0.6–0.8). **Height** `h = Cv²·P·0.01282 m` (ideal 1.54 m at 120 mmHg; real 0.35–0.65 × ideal) [R03 §6.2, V arithmetic; Cv is a tuning value, no measured human jets exist].

| Local BP (sys/dia) | Vertical jet at systole | At diastole | Horizontal throw from 1.4 m (standing neck) | Look |
|---|---|---|---|---|
| 140/90 (stress surge) | 0.65–1.15 m | 0.4–0.7 m | 1.9–2.5 m | Strong throbbing |
| 120/80 | 0.55–1.0 m (default 0.75) | 0.35–0.65 m | 1.8–2.3 m | Throbbing, never fully stops between beats |
| 100/70 | 0.45–0.8 m | 0.3–0.55 m | 1.6–2.1 m | Faster pulses, lower |
| 80/55 | 0.35–0.65 m | 0.25–0.45 m | 1.4–1.9 m | Clearly weaker |
| 60/40 | 0.25–0.5 m | 0.15–0.3 m | 1.2–1.7 m | Arcs, dribbling between beats |
| 45/30 | 0.15–0.35 m | 0.1–0.2 m | 1.1–1.4 m | Pumping surges, 5–20 cm |
| MAP < 25–30 | — | — | — | No jet: welling with faint pulsation |
| Arrest | — | — | — | Stops within 1–2 beats; gravity drainage only |

- **Local pressure**: apply the hydrostatic term. Standing, a neck wound (~30 cm above the heart) sees SBP ~97 (jet ~0.6 m); an ankle wound gains ~94 mmHg.
- **Waveform per beat** [R03 §6.2, C]: upstroke ~0.1 s, peak at ~0.15 s after pulse arrival, dicrotic notch at 0.30–0.35 s, exponential diastolic decay to the next beat; modulation depth 0.5–0.8 × mean. LV wall wounds jet in **systole only** (0.1–0.35 s after R; 20–60 cm through an open chest); RV/atria well dark blood (RA double swell per beat) [R2-05 §10.2].
- **Pulse delay** after the ECG R-wave: pre-ejection 60–100 ms + path/PWV (aorta 6 m/s, peripheral 9 m/s): carotid 90–140 ms, femoral 150–220 ms, radial 170–250 ms, dorsalis pedis 220–300 ms [R03 §2.4, E].
- **Breakup**: the column breaks into drops ~1.9 × jet Ø (typically 4–6 mm, 35–110 µL) within 5–20 cm; pulsing bunches drops into one cluster per beat; stains on walls form a zig-zag, one peak per beat [R03 §6.2].
- As shock deepens the pulses get **faster and weaker at the same time** — the most readable bleed-out cue.

### 3.6 Venous flow and air embolism

- **Look**: dark maroon `#8E1420`, steady, non-pulsatile dome over the wound: height 12.8 cm per 10 mmHg × 0.25–0.5 (3–6 cm at 10 mmHg) [R03 §6.1, E].
- **Posture**: + 0.78 mmHg per cm below the right atrium. Limb venous bleeding increases strongly when the limb hangs and nearly stops when raised above the heart; arterial jets barely change (−8 mmHg per 10 cm).
- **Neck veins**: pulse with respiration (inspiration lowers pressure; upright neck veins ≤ 0 mmHg and collapse); **expiration, coughing, screaming, straining (+20–40 mmHg Valsalva) cause dark surges** [R03 §4.7, C].
- **Air embolism** [R03 §5, V; R02 §2.4, C/G]: condition = an open tethered vein (IJV root, subclavian, dural sinus with open skull) ≥ ~5 cm above the right atrium with P_local < 0. Roll `air_path_open` p = 0.15 per qualifying wound (fits ~10–15 % of fatal throat cuts). If open: entrainment **20–100 mL/s during inspiration** (≥ 100 mL/s possible through a large tear); lethal when **3–5 mL/kg (200–300 mL) enters within seconds** → sudden collapse (CO → 0 "air lock"), gasp, frothy blood, bubbling and sucking at the wound.

### 3.7 Capillary and tissue ooze (wounds without a named vessel)

Rates at MAP 93; scale by `clamp((MAP − 20)/73, 0, 1)` (resistance-limited, stops below critical closing pressure); clot per §3.8.

| Tissue / wound | Initial rate | Clot τ / course | Source |
|---|---|---|---|
| Abrasion (epidermis–papillary dermis) | 0.01–0.1 mL/min per cm²; pinpoint beads in 10–60 s, serum glaze 5–30 min | Stops 2–10 min (bleeding time 1–9 min) | [R02 §2.6], [R03 §6] C |
| Dermal cut, face (no named vessel) | 1–5 mL/min per 3 cm (0.3–1.7 per cm) | Mostly stops 5–15 min | [R02 §2.6] E |
| **Scalp laceration 5–10 cm through the galea** | **5–30 mL/min** sheet ooze + small branches (default 20); **+20–60 per named artery cut (STA/occipital)** → up to 100 | Poor: vessels tethered, spasm fixed 1.0, clot τ × 3–5; 500–1,500 mL over 30–60 min possible; rebleeds as BP recovers | [R02 §2.6], [R03 §5] **Resolved** C/E |
| Subcutaneous fat | 0.02–0.1 mL/min per cm² | 3–10 min | G |
| Skeletal muscle cut surface | 0.2–1 mL/min per cm² (10 cm² → 2–10 mL/min) | τ 5–10 min | G (no measured source) |
| Cancellous bone / red marrow cut (sternum, vertebra, pelvis, rib, skull diploë) | 0.3–1 mL/min per cm², clots poorly | τ 10–20 min | G, [R05 §8.5] C (keeps oozing) |
| Liver laceration | Moderate (1–3 cm deep) 20–100 total; severe 200–1,000 | Moderate often slows; severe does not | [R03 §5] C/E |
| Spleen | Moderate 20–100; shattered/hilar 200–800 | Delayed rupture possible | [R03 §5] C/E |
| Kidney parenchyma | 5–50 (contained in Gerota's fascia) | Usually survives | [R03 §5] C/E |
| Lung parenchyma | Peripheral 5–50; handgun through-track 20–100 | Decays τ 10–30 min (low pulmonary pressure) | [R03 §5], [R04 §9.5] **Resolved** C/E |
| Brain surface / open skull | 1–10 mL/min of blood, CSF and pulp; surges × 2–5 on Valsalva | Continues while ICP high | [R2-05 §7.4] E |
| Nose (anterior epistaxis) | 2–10 mL/min, from both nostrils after nasal fracture | Stops 5–15 min | G |
| Tooth socket | 0.5–2 mL/min | Clot 5–15 min; ooze ~60 min; clot can dislodge | [R02 §4.7] C/G |
| Burned (D ≥ 2) tissue | 0 | Vessels ≤ 1–2 mm cauterised | [R02 §6.7] K |

### 3.8 Haemostasis (clotting over time)

| Parameter | Value | Source |
|---|---|---|
| Vascular spasm | seconds; lasts 20–30 min; strongest in muscular arteries | [R03 §7.1] C |
| Platelet plug | seconds to 1–3 min (capillaries, tiny vessels) | [R03 §7.1] C |
| Skin bleeding time | Ivy 2–7 min (upper 8–9) | [R03 §7.1] C |
| Whole-blood (pool/container) clotting | **5–15 min** (Lee-White) | [R03 §7.1] V |
| Clot update | `clot += dt_sim / τ_eff`, `τ_eff = τ · (1 + (P_local/30)²)` | [R03 §7] G |
| τ: capillary / vessel < 1 mm / 2–3 mm artery | 2–5 / 3–10 / 10–20 min (only after spasm reduces flow) | [R03 §7] C/G |
| Clot ceiling | Arteries > 3–4 mm: clot ≤ 0.5 unless MAP < 50 | [R03 §7] G |
| Scalp/face | τ × 3–5, spasm fixed 1.0 | [R03 §7.3] C/G |
| Coagulopathy | τ × 1.5–3 when core < 35 °C, pH < 7.2 or loss > 0.30–0.35 (every wound oozes more) | [R03 §7.4] C |
| Rebleed | MAP rises > 20–30 mmHg above the value at clot formation, or > 60–65, or wound manipulated → clot × 0–0.5 | [R03 §7] C/G |
| Serum separation | starts 30–60 min (yellow rim `#E6D08A`), largely complete 12–24 h | [R03 §7.1] C |
| Post-mortem blood | stays liquid after sudden death (fibrinolysis); soft "currant jelly"/"chicken fat" clots in slow deaths; no active clotting in wounds | [R03 §6.3] C |

### 3.9 Internal bleeding compartments

| Compartment | Normal | Critical / effects | Capacity | Source |
|---|---|---|---|---|
| **Pericardium** | 15–50 mL fluid | J-shaped P–V: P ≈ 0 to 50 mL, ~15 mmHg at 150, ≥ 25 at 200+. **Tamponade at 100–200 mL acute (default 150)**; CO × 1 → 0 by ~250 mL; ×0.5–0.7 V_t in hypovolaemia (low-pressure tamponade, neck veins may stay flat). Beck's triad (hypotension, distended neck veins, muffled heart sounds), pulsus paradoxus > 10 mmHg, dusky face. Draining 20–50 mL restores pressure transiently | ~200–250 acute before arrest; autopsy 150–450 | [R03 §8], [R2-05 §10] V/C |
| **Pleura (each)** | 10–20 mL | Haemothorax: that lung's ventilation × (1 − V/2,000); RR up, SpO₂ down; massive ≥ 1,500 mL (or ≥ ⅓ BV) or > 200–250 mL/h × 2–4 h; mediastinal shift > 1,500 mL; blood partly defibrinated (stays liquid) | 2,500–3,000 mL (~40 % BV) | [R03 §8], [R04 §9] V/C |
| **Peritoneum** | < 50 mL | Little external sign; FAST-detectable from ~200–250 mL; visible distension only > 1,500–2,000 mL (belly blend shape starts there); Kehr's sign (left shoulder pain) with spleen; Cullen/Grey Turner bruising at 24–72 h | > 5,000 (never limiting) | [R03 §8] C |
| **Retroperitoneum / pelvis** | — | Self-tamponade slows bleeding (Gerota's fascia, retroperitoneal IVC); pelvic fracture 1.5–4 L | Several L | [R03 §8] C |
| Thigh (femur fracture) | — | 1,000–1,500 mL; thigh swells +2–3 cm girth per litre | 1.5–2 L | [R03 §8], [R2-05 §8.5] C/E |
| Tibia / humerus fracture | — | 500–750 mL; each rib ~100–125 mL | — | [R03 §8] C |
| **Cranial vault** | Brain ~1,400 mL, CSF ~150, blood ~150 | Monro–Kellie: compensated for ΔV ≤ V_c = 30–60 mL (default 40): ICP 10 → 20 linearly; beyond: `ICP = 20·10^((ΔV − V_c)/25)` (PVI 25 mL); ICP ≥ MAP → cerebral circulatory arrest. EDH > 30 mL is surgical; posterior fossa tolerates much less. CSF absorption offsets ≤ 0.35 mL/min | V_c + ~20 mL to lethal | [R04 §5.1] C, V arithmetic |
| Subgaleal space | — | Boggy spreading scalp swelling; drains into both eyelids over 24–48 h | Hundreds of mL | [R02 §5.4] C |
| Orbit (retrobulbar) | — | 0.1–2.4 mL → proptosis 0–5 mm; high pressure → fixed dilated pupil, lids swollen shut | small | [R01 §5.6] C |

Rule of thumb for external loss display: a clot the size of a clenched adult fist ≈ 400–500 mL [R03 §8.1].

### 3.10 Blood colour by oxygenation

- Deoxyhaemoglobin absorbs ~5–10× more red light (600–700 nm) than oxyhaemoglobin; the difference is obvious in thin films, subtle in thick pools [R03 §9, V against Prahl's table].
- Shader absorption μa per mm (R, G, B): **arterial (0.4, 28, 34)**, **deoxygenated (3.0, 26, 50)**; lerp by saturation. Film transmittance `T = exp(−2·μa·h)`; shaded albedo = skin·T + (1 − T)·blood body colour [R06 §6.6, E].
- Saturation: arterial 0.97–0.99; venous 0.70–0.75, falling to 0.40–0.50 in Class IV (lerp by loss) — late in shock every wound bleeds darker and more purple.

| Material / state | Hex | Source |
|---|---|---|
| Arterial thin film (≤ 0.2 mm) | `#C0141E` | [R03 §9.3] |
| Arterial 1 mm layer / pool ≥ 2 mm | `#8C0A12` / `#5E070C` + strong wet specular | [R03 §9.3] |
| Venous thin film / pool | `#8E1420` / `#3E0509` | [R03 §9.3] |
| Deeply deoxygenated (shock, post-mortem) film / pool | `#6A1026` / `#2C040A` | [R03 §9.3] |
| Capillary beads | `#B01820` | [R03 §9.3] |
| Fresh clot | `#4A060C` glossy | [R03 §7.6] |
| Frothy lung blood | `#D8404C`–`#E04A56` with white/pink foam `#F4C9CC` | [R03 §9.3], [R04 §9.5] |
| Diluted 1:10 / 1:100 | `#D04858` / `#F0B0B4` | [R03 §9.3] |
| Specular | wet F0 0.02–0.025, roughness 0.05–0.15; tacky 0.3–0.45; dry 0.6–0.8 | [R06 §6.6] |

### 3.11 Blood on surfaces: drops, rivulets, pools, drying

| Item | Value | Source |
|---|---|---|
| Free-falling drip | ~50 µL (13–160), Ø 4.6 mm; hair tips / sharp edges 10–20 µL | [R03 §10.1] V/C |
| Terminal velocity | 8 m/s (7.5–9); ~4.1–4.3 m/s after 1 m of fall | [R03 §10.1] corrected |
| Stain size | 3–5.5 × drop Ø (4.6 mm drop from 1 m → 15–22 mm); L/W = 1/sin α | [R03 §10.1] V |
| Drip rate | Q / 50 µL (1 mL/min ≈ 20 drops/min); continuous thin stream above 15–30 mL/min | [R03 §10.2] E |
| Rivulets on skin | 2–5 mm wide, 0.1–0.4 mm thick; 1–5 cm/s (2–3.5 on vertical skin), stop–go pinning (p 0.1–0.3 per step, 0.2–1.5 s); residue 5–15 µL/cm (a 50 µL drop runs 3–10 cm); a 1–10 mL/min trickle keeps a rivulet alive; pendant drops release at 30–60 µL at low points (standing: chin, nose tip, earlobe, elbow, fingertips; supine: occiput, ears, neck sides) | [R03 §10.2], [R06 §7.1] E |
| Old trails | Keep their original direction when the body is moved (forensic clue) | [R03 §10.2] C |
| Pool thickness | **2.5 mm** (1.6–3.3); area = V/h: 100 mL → Ø 23 cm, 500 mL → 50 cm, 1 L → 71 cm, 2 L → 1.0 m; continuous source radius R = √(Q·t/(π·h)) | [R03 §10.3] V |
| Pool gel | Spreading stops at **5–15 min**; new blood flows over/around, lobed layered outline; serum rim from 30 min–2 h; clot retracts to ~50 % in 1–2 h | [R03 §10.3], [R2-05] C |
| Absorbent surfaces | Stain area 2–4 × pool area, duller, browner | [R03 §10.3] G |

**Drying and colour timeline** (thin stains move along the ramp faster than thick ones; warm skin ×2 evaporation; airflow ×2–4) [R03 §10.4; chemistry oxyHb → metHb → hemichrome V, timings C/E]:

| Deposit | Tacky | Touch-dry | Fully dry |
|---|---|---|---|
| Smear on skin (< 0.05 mm) | 30–60 s | 1–3 min | 5–10 min |
| Rivulet on skin (0.1–0.3 mm) | 2–5 min | 10–20 min | 30–60 min |
| Spatter on steel (1–4 mm stains) | ~1 min (edge ring ~50 s) | 5–15 min | 15–30 min |
| Drip stain (50 µL) on tile | 5–15 min | 20–60 min | 1–2 h |
| Pool 100 mL–2 L | Gels 5–15 min | Surface skin 1–2 h; edges 2–6 h | 24–72 h, mud-crack plates |

| Age | Thin stain | Thick stain / pool |
|---|---|---|
| 0 | `#C0141E` arterial / `#8E1420` venous | `#5E070C` glossy |
| 10–30 min | `#9A1418` | `#4A060C` gel |
| 1–2 h | `#7A2016` red-brown | `#3A0808` |
| 6–24 h | `#5C2414` | `#2A0C0A` near-black, dull |
| Days | `#4A2618` brown | `#24100C` |
| Weeks | `#33201A` dark brown-black, flaking | black-brown |

Store the **deposit timestamp** (sim minutes, fp16) per texel/stain, not an age; the shader derives colour, roughness and crust [R06 §6.4].

### Simulation parameters (circulation)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `bv0` | Nadler(H, W, sex); ref 5.09 L | mL | Thresholds are fractions | [R03 §1.1] V |
| `shock_table` | §3.2 | — | Interpolate on loss | [R03 §3.3] G/V |
| `hr_response_scale` | 0.8 (0.6–1.0), ±15 % per victim | × | | [R03 §3.2] C |
| `relative_brady_p / sudden_faint_p` | 0.40 / 0.20 | p | Resolved split | [R03 V2], [R04 §7.3] C/G |
| `upright_brain_offset` | −23 | mmHg | | [R03 §3.2] E |
| `hr_tau / svr_tau / veno_tau` | 3 / 15 / 30 | s | | [R03 §3.4] G |
| `stress_surge` | SBP +20, HR +30, τ 120 s | — | At injury | [R03 §3.4] G |
| `refill` | 4–8 mL/min at ≥ 20 % loss, τ 60 min, cap 1,000 mL | — | Resolved | [R03 §3.4] V |
| `k_orifice` | 0.01805 · A[mm²] · tf | L/min per √mmHg | Shunt solve | [R03 §4] V |
| `cd_orifice / cv_jet` | 0.6 / 0.7 (0.6–0.8) | — | | [R03 §4, §6] V/G |
| `tissue_factor` | 1.0 / 0.4–0.6 / 0.15–0.3 / 0.05–0.1 | — | Gaping / under muscle / deep track / lying on wound | [R03 §4.8] G |
| `spasm_target` | muscular transected 0.4–0.6 (τ 1–3 min); side lac 1.1–1.3; elastic 0.9; scalp 1.0 | × area | | [R03 §4.8] G |
| `compress` | clutch 0.3–0.7; firm pressure 0.8–0.95; tourniquet 1.0 | — | | [R03 §4.5] G |
| `critical_closing_p / rebleed_map` | 20–40 / 60–65 | mmHg | | [R03 §4.6] C |
| `jet_min_p` | 25–30 | mmHg | Pressure-gated | [R03 §6.2], [R06 §8.1] |
| `jet_pulse_depth` | 0.5–0.8 | × mean | | [R06 §8.1] G |
| `pwv_aorta / peripheral / pre_ejection` | 6 / 9 / 60–100 ms | m/s | Spurt delay | [R03 §2.4] E |
| `msfp / msfp_exsanguinated / decay_tau` | 10 (7–20) / 0–5 / 20 s | mmHg | After arrest | [R03 §1.2] V/C |
| `air_path_open_p / entrain / lethal` | 0.15 / 20–100 mL/s inspiratory / 3–5 mL/kg in seconds | — | Tethered open vein above heart | [R03 §5] V, G |
| `valsalva_surge` | +20–40 | mmHg | Venous | [R03 §4.7] C |
| `pericardium_tamponade_v` | 150 (100–200), ×0.5–0.7 hypovolaemic; CO → 0 at 250 | mL | | [R03 §8] V |
| `pleura_capacity / massive` | 2,500–3,000 / ≥ 1,500 or > 200–250 mL/h | mL | | [R03 §8] V/C |
| `icp_vc / pvi` | 40 (30–60) / 25 | mL | | [R04 §5.1] C |
| `mu_a_arterial / deoxy` | (0.4, 28, 34) / (3.0, 26, 50) | 1/mm | | [R03 §9.2] V |
| `pool_thickness / gel_time` | 2.5 / 5–15 min | mm | | [R03 §10.3] V |
| `drop_volume / terminal_v` | 50 µL / 8 m/s | — | | [R03 §10.1] |

### Visual/behavioural checklist (circulation)
- An exposed cut artery spurts bright scarlet in time with the pulse, a fraction of a second after each heartbeat; the jet never fully stops between beats while BP is normal, gets faster and lower as shock deepens, becomes a pulsing well below MAP ~25–30 and stops within a beat or two of cardiac arrest.
- Venous bleeding is dark maroon, domed and steady, surging when the victim screams or strains; raising a bleeding limb above the heart nearly stops venous bleeding but not an arterial jet.
- Small trunk bullet wounds barely bleed outside while the victim goes pale, breathes faster and becomes confused (internal bleeding).
- Scalp wounds keep bleeding long after small cuts elsewhere have clotted; hair mats and drips from the tips.
- A floor pool spreads as a 2.5 mm sheet (1 L ≈ 70 cm across), stops spreading after ~10 min, later shows a yellow serum rim and darkens from the edges.
- Late in shock all wounds bleed darker and more purple.

---

## 4. Physiology state machine

### 4.1 State variables (per character)

| Group | Variable | Unit / type | Initial | Notes |
|---|---|---|---|---|
| Circulation | `V` (blood volume), `loss = 1 − V/BV0` | mL, fraction | BV0 | §3.1 |
| | `hr`, `sbp`, `dbp`, `map`, `cvp`, `co` | bpm, mmHg, L/min | 70, 120, 80, 93, 4, 5.0 | §3.2 |
| | `rhythm` | enum {sinus, tachy, brady, VF, PEA, asystole} | sinus | |
| | `pump_fraction`, `tamponade_mL`, `neurogenic`, `vasomotor_ok` | 0–1, mL, bool, bool | 1, 0, false, true | |
| | `stress_surge`, `refill_total` | 0–1, mL | 0, 0 | |
| | `t_arrest` | sim s | none | Post-mortem clock start |
| Respiration | `resp_drive` | enum {normal, tachypnoea, cheyne_stokes, cnh, apneustic, cluster, ataxic, gasping, none} | normal | §4.2 |
| | `resp_capacity` | 0–1 | 1 | From cord level (§4.6) |
| | `airway` | enum {open, stertor, blood_flooded, obstructed} | open | |
| | per lung: `state` {ok, pneumo, open_pneumo, tension}, `haemothorax_mL`, `collapse` | —, mL, 0–1 | ok, 0, 0 | |
| | `rr`, `o2_lung`, `o2_blood`, `spo2` | /min, mL, mL, 0–1 | 14, 400, 0.98·cap, 0.98 | §4.2 |
| Brain | `brain_o2_reserve` | s (real) | 8 | §4.2 |
| | `icp`, `cpp`, `haematoma_mL` | mmHg, mmHg, mL | 10, 83, 0 | §3.9 |
| | damage 0–1: `frontal_L/R`, `motor_L/R`, `parietal_L/R`, `temporal_L/R`, `occipital_L/R`, `capsule_L/R`, `thalamus`, `cerebellum_L/R`, `vermis`, `midbrain`, `pons_teg`, `pons_basis`, `medulla` | fraction destroyed | 0 | Include concussive radius (18 mm handgun) as partial damage |
| | `concussion_timer`, `ko_timer`, `seizure` {none, tonic, clonic, postictal}, `herniation_stage` {0, uncal/central 1–4} | s, s, enum, enum | 0 | |
| | `consciousness` {alert, confused, stupor, unconscious}, `gcs_e/v/m` | enum, 1–6 | alert, 4/5/6 | §4.3 |
| Cord | `cord_level` (C1…S5 or none), `cord_complete`, `cord_syndrome` {complete, brown_sequard_L/R, central, anterior, cauda, concussion} | enum, bool | none | §4.6 |
| Sensation / stress | `pain`, `stress`, `fear` | 0–1 | 0 | §4.2 |
| Motor | per limb/body: `tone` {voluntary, weak, flaccid, decorticate, decerebrate, fencing, tonic, clonic, rigor} | enum | voluntary | §4.10 |
| Metabolic | `core_temp`, `vo2_mult` | °C, × | 37.0, 1.0 | Struggling 1.5–2 |
| Eyes (per eye) | `lid_mm, yaw, pitch, pupil_mm, pupil_reactive, corneal_reflex, doll_gain, blink_on, gloss, corneal_opacity, dry_band, tache_noire, iop, subconj, petechiae, proptosis_mm` | mm, °, bool, 0–1 | §5 | |
| Skin | `pallor`, `cyanosis`, `mottling`, `sweat`, `flush_below_level` | 0–1 | 0 | ≤ 1 Hz mask update |
| Post-mortem | `pm_h`, `livor_intensity`, `livor_fixation`, `rigor_s[group]`, `rectal_temp` | h, 0–1, °C | 0 | §6 |

### 4.2 Update order and rules (20 Hz alive, 2–5 Hz dead) [R04 §13.5]

```
1  apply_new_injuries()       # wound records → vessel/organ/cord/brain damage, lung states, tamponade flags
2  circulation(dt_sim)        # §3: bleeding per wound (pressure from previous tick), V, refill, shock table targets,
                              #     lags, stress surge, special states, shunt solve → MAP/SBP/DBP/HR, rhythm & arrest rules
3  respiration(dt_sim)        # drive × capacity × airway × lungs → E_vent; O2 stores → SpO2; RR target
4  brain(dt_real for reserve, dt_sim for ICP)   # ICP/CPP, brain O2 reserve, consciousness resolver, seizure/posture timers
5  sensation_stress(dt_sim)   # pain, stress, analgesia
6  motor()                    # tone per body from cord map, lesion level, consciousness, posture → ragdoll PD targets (§4.10)
7  eyes()                     # §5 → material uniforms + bones (cosmetic oscillators in real time)
8  skin(≤ 1 Hz)               # pallor, cyanosis, mottling, sweat, neurogenic flush
9  postmortem(dt_sim)         # if arrested: livor, rigor, algor, eye surface (§6)
```

**Respiration and SpO₂ proxy** [R04 §1, E; calibrated: apnoea at rest → SpO₂ < 90 % at ~1.9 min, hypoxic LOC ~3 min, arrest ~6 min]:
```
E_vent  = drive_eff * resp_capacity * airway_f * lung_f            # 0–1
          drive_eff: normal/tachypnoea/cnh 1.0; cheyne_stokes 0.6 (cycle-averaged); apneustic 0.5; cluster 0.4;
                     ataxic 0.3; gasping 0.05 (moves almost no air); none 0
          airway_f:  open 1.0; stertor 0.8; blood_flooded 0.2–0.6; obstructed 0
          lung_f:    mean over lungs of (1 − collapse) × (1 − haemothorax_mL/2000); open_pneumo side 0.1; tension side 0
cap_b   = 850 mL * (V/BV0)                                          # blood O2 store shrinks with blood loss
VO2     = 250 mL/min * vo2_mult (rest 1.0; struggling/seizure/shivering 1.5–2.0; unconscious 0.8)
supply  = E_vent * 350 mL/min
o2_lung = clamp(o2_lung + (supply − draw)·dt, 0, 400);  draw = min(VO2, o2_lung/dt + supply)
o2_blood = clamp(o2_blood − (VO2 − draw)·dt, 0, cap_b)
if E_vent ≥ 0.6 and o2_lung > 360: o2_blood → 0.98·cap_b with τ 10 s (0.95 if one lung is down)
spo2    = o2_blood / cap_b
RR      = shock_table_RR(loss) + 4–8·stress + hypoxic drive (+10 when spo2 < 0.9), overridden by resp_drive patterns
```
Cyanosis (render): `cyanosis = skin_perfusion × clamp((deoxyHb − 3)/4, 0, 1)`, deoxyHb = 15 g/dL × (1 − spo2). **An exsanguinated body turns white-grey, not blue** (skin perfusion → 0); an apnoeic body with full volume turns blue-grey in 60–120 s. Lips lag arterial desaturation by 5–15 s, fingers by 15–30 s [R04 §1, R2-06 §17, C].

**Brain oxygen reserve** (integrated in **real** seconds; inputs from sim state) [R04 §13.2, E]:
```
map_brain = MAP − 0.78 × (head height above heart, cm)          # upright ≈ −23 mmHg
cpp       = map_brain − ICP
perf      = clamp((map_brain − 20)/40, 0, 1) × clamp(cpp/50, 0, 1) × clamp((spo2 − 0.5)/0.3, 0, 1)
if perf < 0.5: reserve −= (1 − perf)·dt   else: reserve = min(8, reserve + dt)
reserve ≤ 0 → loss of consciousness (syncope pattern on first entry)
```
Starts at 8 s; a destroyed heart adds ~4 s of residual pressure decay → reproduces **10–15 s of possible action** and **LOC 5–10 s after complete cerebral flow arrest** [R04 §8, C]. The band selector (§1.3) must also enter ACUTE when predicted LOC is < 60 s away.

**Orthostatic faint**: if upright and `loss ≥ faint_upright_loss` (per victim 0.20–0.30): MAP −25 for 20–60 s → reserve drains → collapse; once supine, partial recovery (can try to rise again) [R04 §7.3, C/G].

**Consciousness resolver** (every tick, first match wins) [R04 §13.2, extended with GCS]:

| # | Condition | Result | GCS (E/V/M) |
|---|---|---|---|
| 1 | `medulla, pons_teg, midbrain or thalamus > 0.5`, or both hemispheres > 0.6 | Coma; motor by lowest level destroyed: medulla/lower pons → flaccid (M1); midbrain/upper pons → decerebrate episodes (M2); thalamus/bilateral hemispheres → decorticate (M3) | 1/1/1–3 |
| 2 | `brain_o2_reserve ≤ 0` | Unconscious (syncope/anoxia); first entry: eyes up 10–30° for 2–10 s, myoclonus p 0.9 (1–10 irregular jerks < 15 s) | 1/1/1–2 |
| 3 | `seizure ≠ none` | Unconscious | 1/1/1 |
| 4 | `ko_timer > 0` | Unconscious; fencing p 0.66 on entry | 1/1/1–4 |
| 5 | `cpp < 30` or `spo2 < 0.6` or `loss > 0.45` (supine) | Coma | 1/1/2–4 |
| 6 | `loss > 0.40` or `cpp < 40` or herniation stage ≥ 2 | Stupor (responds to pain only) | 2/2/4–5 |
| 7 | `loss > 0.30` or `cpp < 50` or `spo2 < 0.8` or concussion_timer > 0 | Confused | 3–4/4/6 |
| 8 | else | Alert, with focal deficits (§4.5) | 4/5/6 |

**Pain and stress** [G, anchored to R02 §6, R2-02]:
```
pain_raw  = Σ_wounds w_type × severity × sensory_intact(site)
            sensory_intact = 0 below a complete cord level; 0 for full-thickness burn texels; ×0.5 in hemisensory loss
            w_type: superficial-partial burn 1.0 per 1 % BSA (very painful); fracture 0.6; incised 0.3; laceration 0.4;
                    gunshot track 0.3–0.5; bruise 0.1; full-thickness burn 0
pain      = clamp(pain_raw, 0, 1) × analgesia ;  analgesia 0.3–0.7 during the first 5–15 min under high stress
stress    = clamp(0.5·pain + 0.4·fear + 0.4·loss/0.3, 0, 1)
effects   : HR +30·stress and SBP +20·stress (inside the surge), pupils +1–2 mm, lid retraction to 11–12 mm (fear),
            RR +4–8, vocal effort, clutching/withdrawal
```
Withdrawal reflex ~100 ms; heat withdrawal 190–280 ms (fast fibres) and 1.2–1.5 s (slow second pain); whole-body startle flinch within 200 ms of a gunshot (blink 30 ms, SCM 62 ms, biceps 85–100 ms, legs 100–140 ms); the first startle is the largest and habituates [R2-02 §15, C]. Stress-induced analgesia is real: only 32 % of severely wounded soldiers at Anzio asked for narcotics [R2-02 §15, C].

### 4.3 Thresholds

| Event | Trigger | Source |
|---|---|---|
| Upright faint | loss 0.20–0.30 (per victim) while upright | [R04 §7.4] C |
| Confusion | loss 0.30–0.40, or MAP < 65, or CPP < 50 | [R04 §7.4] C |
| **LOC supine** | **loss 0.45 (0.40–0.50)**, or MAP < 40–45 (SBP < 60) for > 5–8 s | [R04 §7.4] C (ATLS > 50 %, Guyton 40–45 % bracket it) |
| **PEA** | **loss 0.45–0.50 if total bleed > 500 mL/min, else 0.55**; or MAP < 20 for > 30 s; or (DBP − CVP) < 15 for > 60 s; or tamponade/tension end-stage; or SpO₂ < 0.4 for > 150 s | [R04 §7.4], [R03 §3.5] C/G |
| VF | direct ventricular hit p 0.3; commotio p 0.01–0.03 | [R04 §13.3] G |
| PEA → asystole / VF → asystole | 2–10 min / 10–20 min | [R04 §10.3] C |
| EEG silent | 10–40 s after cerebral perfusion stops | [R04 §1] C |
| Irreversible brain injury | perf < 0.2 accumulated 4–6 min (normothermic) | [R04 §1] C |
| Herniation start | ICP ≥ 30–40 or CPP < 50 | [R04 §5.6] C/G |
| Cerebral circulatory arrest | ICP ≥ MAP | [R04 §5.1] C |
| Apnoea → arrest | 4–10 min (default 6) | [R04 §1] C |

### 4.4 Organ-hit effects

| Organ / structure | Hit type | Physiology effect | Time course (untreated) | Visible | Source |
|---|---|---|---|---|---|
| **Heart destroyed** | Shotgun ≤ 1 m, large exit, burst | CO = 0 | Action 10–15 s; LOC 8–15 s; agonal gasps p 0.3–0.5; dead flag +5 min | Collapse with eyes open and up, jerks; small external bleeding, chest fills | [R04 §8] C |
| LV perforation | Bullet, pericardium torn | 1,000–4,000 mL/min into pleura; pump_fraction 0.3–0.7; VF p 0.3 | LOC 10–60 s; death 1–5 min | Systole-only jets if exposed | [R03 §5], [R2-05 §10] C |
| RV / atrium perforation | Pericardium open | 500–2,000 mL/min | LOC 30 s–3 min; death 2–10 min | Dark welling | [R03 §5] C |
| Heart stab, pericardium intact | Knife | 100–200 mL into the sac → tamponade; self-seal p: LV < 1 cm 0.3–0.5, RV 0.2–0.4, atria 0.05–0.1 | LOC 5–60 min; arrest 5 min–2 h (default 20 min) | Distended neck veins, dusky face | [R03 §8.2], [R2-05 §10] C/E |
| Coronary artery | Any | Downstream myocardium stops in 1–5 min (pump_fraction −) | | Dusky patch | [R2-05 §10] C |
| Commotio cordis | Hard blow to the precordium | VF (p 0.01–0.03) | Collapse within seconds, pulseless, agonal gasps | | [R04 §8.3] G |
| **Lung parenchyma** | Any penetration | 20–100 mL/min (τ 10–30 min) into pleura; haemoptysis onset 5–60 s (2–30 mL per cough) | Usually survivable | Bright frothy pink blood from mouth and nose, froth bubbling with each breath | [R04 §9] C |
| Chest wall defect > 10–13 mm | Shotgun, big exit, big knife wound | Open pneumothorax: that lung → collapse in 2–10 s; air in/out through the wound | | Sucking on inspiration, bubbling pink froth on expiration | [R04 §9.2], [R2-06 §17] C |
| Valve-like lung wound | p 0.1–0.3 of lung wounds [G] | Tension: onset 5 min–hours (default 20 min); RR > 30, HR > 120, SpO₂ falling; hypotension and tracheal deviation late | → PEA | Hyperexpanded side that stops moving, neck veins distend, lips blue | [R04 §9.2] C |
| Lung hilum / pulmonary artery | Bullet | 1,000–4,000 mL/min; airway flooding asphyxia 1–5 min | LOC 30 s–2 min | Drowning in blood | [R03 §5] C |
| **Liver** | Moderate / severe / retrohepatic IVC | 20–100 / 200–1,000 / 1,000–3,000 mL/min intraperitoneal | Hours / LOC 10–30 min / 1–5 min | Little external blood, progressive pallor; knife: clean oozing cut; handgun: 1–2 cm track + 1–3 cm stellate fissures | [R03 §5], [R2-05 §12] C |
| **Spleen** | Moderate / shattered or hilar | 20–100 / 200–800 mL/min | Hours / LOC 10–40 min; delayed rupture 30 min–48 h (p 0.02–0.1 after blunt grade I–III) | Kehr's sign (left shoulder pain) | [R03 §5], [R2-05 §12.4] C/E |
| **Kidney** | Parenchyma / hilum | 5–50 contained / 300–1,000 retroperitoneal | Survives / LOC 5–20 min | Haematuria | [R03 §5] C |
| Stomach, bowel | Penetration | Minor bleeding; spillage | Peritonitis outside the game window | Sour gastric content; bowel through wounds ≥ 50–80 mm | [R2-05 §12.5] C |
| Great vessels | Any | §3.3 table | §3.3 table | | [R03 §5] |
| Trachea below cords | Cut or shot | Aphonia (mouths words without airflow); aspiration (airway blood_flooded) | Aspiration killed 36.5 % of cut-throat victims | Bubbling at the wound, cough spray | [R02 §2.4] C |

### 4.5 Brain regions

**Core rule** [R04 §3.1, C]: consciousness needs the brainstem reticular system plus working cortex; **a lesion confined to one hemisphere does not by itself cause coma**. It usually causes an immediate concussive collapse (impact apnoea p 0.3–0.6, transient LOC 5–120 s) from which the victim may wake with focal deficits. Probability of being awake 10 s after a unilateral low-energy wound not crossing the midline: 0.10–0.30; purposeful capacity to act after a low-energy frontal track: 0.05–0.15 (retained-capacity cases: > 70 % slow light bullets) [R04 §3.7, R01 §6.3].

| Region (damage = fraction destroyed; "visible / full" = deficit onset / complete) | Deficit | Side | What the player sees | Source |
|---|---|---|---|---|
| Prefrontal | Planning, inhibition, drive (unilateral 0.30/0.90; bilateral 0.20/0.60) | Bilateral effects | Blank stare, slowed or absent responses, perseveration, grasping; may keep walking/talking; vomiting possible | [R2-01 §1], [R04 §3.3] C/E |
| Motor strip / internal capsule (capsule 0.05/0.30: a 10 mm lesion gives dense hemiplegia) | Contralateral hemiplegia, flaccid at first (face, arm, leg) | Contra | Arm hangs, leg buckles, **falls toward the paralysed side**, mouth droops; **eyes and head deviate 15–40° toward the lesion** | [R2-01 §1], [R04 §3.3] C |
| Frontal eye field (0.30/0.70) | Voluntary gaze to the opposite side | Eyes toward lesion | Eyes and head turned toward the wound | [R2-01 §1] C |
| Left (dominant) language areas (Broca/Wernicke 0.20/0.70) | Aphasia | — | Broca: grunts, single effortful words (10–50 words/min, 1–5 s pauses); Wernicke: fluent nonsense, ignores commands | [R2-01 §1], [R2-06 §17] C |
| Right parietal | Left neglect | Contra | Ignores the left side, no reaction to hits on the left | [R2-01 §1] C |
| Occipital | Contralateral field loss; bilateral → cortical blindness | Contra field | Bumps into things; bilateral: eyes open, pupils react, no tracking | [R2-01 §1] C |
| Temporal | Memory, comprehension (left); seizures; expanding haematoma → uncal herniation | — | Repetitive questions, confusion; later ipsilateral blown pupil | [R04 §3.3] C |
| Thalamus / diencephalon (unilateral 0.10/0.50; bilateral paramedian 0.10/0.30) | Coma likely | — | Eyes deviated down and in, small reactive pupils | [R04 §3.3], [R2-01] C |
| **Cerebellar hemisphere** (0.10/0.50) | Ipsilateral limb ataxia, intention tremor 3–5 Hz (1–5 cm at the fingertip, rising in the last 10–20 cm of a reach), dysmetria overshoot 3–10 cm | **Ipsi** | Staggers and falls **toward the lesion** (60–80 % of falls), wide steps 15–30 cm, nystagmus p 0.75, vomiting p 0.6–0.8 in the first hour, cannot walk p 0.7 if severity > 0.3, scanning speech | [R2-01 §12] C/E |
| Vermis (0.10/0.50) | Truncal ataxia | Midline | Cannot sit or stand unsupported; titubation 2–4 Hz, 1–3 cm | [R2-01 §12] C/E |
| Cerebellar track with bleeding | Posterior-fossa haematoma compresses the 4th ventricle/medulla | — | Talking → sudden apnoea within minutes–48 h (not the 3-day oedema clock) | [R2-01 §12.1] C |
| **Midbrain** (0.02/0.20) | Coma at once; CN III | — | Mid-position fixed pupils 4–6 mm; eye down-and-out with ptosis; vertical gaze lost; decerebrate episodes p 0.3–0.6 (5–60 s); may topple stiffly | [R04 §2.2] C |
| **Pons, tegmentum** | Coma; horizontal gaze lost | — | **Pinpoint 1–2 mm pupils**, ocular bobbing, corneal reflex lost; apneustic/cluster/ataxic breathing then apnoea within 0–5 min | [R04 §2.2] C |
| Pons, ventral basis only (low energy, p ≤ 0.05) | Locked-in | — | Awake; quadriplegic; only vertical eye movements and blinks | [R04 §2.2] G |
| **Medulla** (0.02/0.15) | Breathing and vasomotor centres | — | **Immediate apnoea, no gasps**; MAP 40–60 within 30–60 s; flaccid; heart continues ~100 bpm, hypoxic arrest 4–10 min | [R04 §2.2] C |
| Near-miss within 10–20 mm of the brainstem (handgun) | Concussive brainstem dysfunction | — | Immediate LOC, impact apnoea, high apnoea chance | [R04 §2.5] C/G |

**Herniation sequences** [R04 §5.2, C]: *Uncal* (temporal mass, e.g. EDH): ipsilateral pupil enlarges, sluggish then fixed 6–9 mm, ptosis, eye down-and-out → consciousness falls → contralateral hemiparesis → decerebrate → both pupils fixed → breathing Cheyne–Stokes → hyperventilation → ataxic → apnoea. *Central*: small reactive pupils, Cheyne–Stokes, decorticate → mid-fixed pupils, decerebrate, central hyperventilation → flaccid, ataxic, apnoea. *Tonsillar* (posterior fossa): sudden apnoea and collapse with little warning.
**Breathing patterns**: Cheyne–Stokes period 40–90 s with 10–30 s apnoea; central neurogenic hyperventilation 25–40/min; apneustic 2–3 s inspiratory hold; ataxic 4–12/min random; agonal 2–10/min [R04 §5.5].
**Seizures** [R04 §4.2, R2-04 §14, C]: early post-traumatic seizure p 0.10–0.15 severe blunt, 0.2 penetrating (impact seizure 0.02–0.05). GTC: tonic 10–20 s (epileptic cry, apnoea, jaw clench), clonic 30–60 s slowing from 3–4 Hz to ~1 Hz, total ~62 s; eyes open 90–97 %; lateral tongue bite 0.2–0.35; HR 120–160; postictal 2–20 min of heavy obstructed breathing, confusion 10–30 min.

### 4.6 Spinal cord level → paralysis map

**Vertebra → cord segment**: cervical +1, upper thoracic +2, lower thoracic +3; T10 → T11–L1; T11 → L1–L3; **T12 → L3–S1**; **L1 → conus S2–S5** (bladder/bowel); L2–S2 = cauda equina roots (lower motor neuron, patchy, asymmetric). Conus tip at the L1/L2 disc, body frame (0, +0.017, 1.180) [R05 §9, V level]. Complete-injury probability for a bullet through the canal 0.7–0.9; fragment or cavitation only 0.3–0.5 [R04 §6.7, G].

| Level (complete) | Resp. capacity (fraction of VC) | Ragdoll bodies with voluntary tone | Flaccid bodies | Autonomic | What the player sees | Without help |
|---|---|---|---|---|---|---|
| **C1–C3** | 0–0.1 (apnoea) | Head/neck weak (CN XI shrug/turn), face, eyes, jaw | All limbs, trunk | Neurogenic shock | Instant flaccid collapse **but awake**: eyes wide and darting, mouth opening without airflow, neck straining, chest still; lips blue by 1–2 min; LOC 90–180 s | Arrest 4–10 min (default 6) |
| C4 | 0.25 | + shoulder shrug | Arms, trunk, legs | Neurogenic shock likely | Paradoxical "see-saw" breathing (belly rises, upper chest sinks), short breathy phrases | Fatigue over hours |
| C5 | 0.3 | upper_arm (abduction), forearm flexion only | hands, trunk, legs | Neurogenic shock common | Elbows flex with limp supinated hands; slow pulse 40–60, warm pink skin | Survives acutely |
| C6 | 0.4 | + wrist extension (tenodesis finger curl) | fingers, trunk, legs | | Can lift the wrists | Survives |
| C7 | 0.5 | + elbow and finger extension | intrinsic hand, trunk, legs | | Pushes up weakly | Survives |
| C8 | 0.5 | + grip | hand intrinsics, trunk, legs | Less often shock | Grasps | Survives |
| T1 | 0.6 | Arms fully | Trunk, legs | Horner's (ptosis 1–2 mm, pupil 0.5–1 mm smaller) | No trunk balance | Survives |
| T2–T6 | 0.6 | Arms | Poor trunk, legs | **≤ T6: neurogenic shock possible** | Falls, props up on the arms, cannot sit unsupported | Survives |
| T7–T12 | 0.8 | Arms, better trunk | Legs | Mild | **Legs fold instantly, arms break the fall, drags itself on the elbows**, legs trailing and externally rotated | Survives |
| L1–L2 (conus) | 1.0 | Upper body | Legs (hip flexors weak/absent), bladder/bowel | | As T12 | Survives |
| L3–S1 (cauda) | 1.0 | Partial legs by root: L3 quads, L4 dorsiflexion, L5 big-toe extension, S1 plantarflexion | Patchy, asymmetric, permanently flaccid; foot drop | | Limps, foot slaps, one leg worse | Survives |

- **Incomplete syndromes** [R04 §6.3, C]: *Brown-Séquard* (knife to the side of the back/neck; 0.3–0.5 of knife cord injuries): same-side paralysis and loss of position sense; opposite side loses pain/temperature from 1–2 segments below — one leg paralysed, the other moves but ignores the torch. *Central cord*: arms much weaker than legs. *Anterior cord*: paralysis and pain loss with position sense kept. *Cord concussion* (hammer/fist to the neck): complete paralysis resolving in 2 min–48 h (default 10 min).
- **Spinal shock** (0–24 h, the whole game window): everything below the level is flaccid, areflexic, with **no withdrawal** and no flinch to cutting or burning [R04 §6.4, C].
- **Neurogenic shock** incidence in isolated cord injury: cervical 0.19, thoracic 0.07, lumbar 0.03; complete cervical 0.7–1.0 (bradycardia essentially always; primary arrest ~16 %) [R04 §6.5, C]. Poikilothermia: core drifts toward ambient at 0.3–1 °C/h.

### 4.7 Time to incapacitation (canonical injuries, supine unless stated)

| Injury | LOC / incapacitation (real) | Arrest (real) | Signature | Game length (auto bands) | Source |
|---|---|---|---|---|---|
| Medulla / pons gunshot | 0 s (collapse 0.6–1.2 s) | 4–10 min (hypoxic) | Cut-strings drop, no breathing, eyes fixed open, pinpoint or mid pupils | ~2–3 min | [R04 §13.4] C |
| Heart destroyed | 8–15 s (action possible 10–15 s) | 0 s | Brief action, collapse, eyes up, jerks, gasps | ~1.5–2 min to dead flag | [R04 §8] C |
| Heart stab (tamponade) | 5–60 min | 5 min–2 h (20 min default) | Distended neck veins, grey, breathless; purposeful activity for minutes common (4/7 cardiac-stab suicides active 2–10 min) | 3–8 min | [R04 §8.3], [R2-02 §15] C |
| Ascending aorta / arch | 5–15 s | 1–3 min | | ~1.5 min | [R03 §5] C |
| Throat cut (both carotids + jugulars) | 5–20 s | 1–3 min | Aspiration, air bubbling at the wound | ~1.5 min | [R03 §5] C |
| Unilateral carotid (open) | 20–90 s | 2–5 min | Tall pulsing jet, hand to the neck | ~2 min | [R03 §5] C |
| Common femoral transection | 2–5 min (standing collapse ~2 min) | 3–10 min | Fast-growing pool | 2–3 min | [R03 §5] C |
| Brachial | 10–15 min | 15–30 min | | 4–6 min | [R03 §5] C |
| Lung + haemothorax/tension | 10–60 min | 15–90 min | Frothy haemoptysis, sucking wound, blue lips | 4–8 min | [R04 §13.4] C |
| Liver severe / spleen shattered | 10–30 / 10–40 min | 20–90 / 30–120 min | Little external blood | 4–8 min | [R03 §5] C |
| Slow multi-wound bleed 100 mL/min | 24–28 min | 29–40 min | Full stage progression | ~5–6 min | [R04 §7.5] V arithmetic |
| C1–C3 cord | 1.5–3 min (awake until then) | 4–10 min | Awake, eyes pleading, blue lips | ~3 min | [R04 §13.4] C |
| C5 cord / T8 cord | none | none | Belly breathing; dragging with arms | Persistent | [R04 §13.4] C |
| Unilateral frontal low-energy | 0–60 s (often transient) | Hours or none | Staggers, talks confusedly | Persistent/slow | [R04 §3] C |
| Temporal hammer blow → EDH | Brief, then lucid (p 0.2–0.5) | 1–6 h (default 2 h) | Talk and die: blown pupil, Cushing | 8–12 min | [R04 §5.4] C |
| Punch knockout | 0 s; recovers in 5–60 s | none | Fencing arms, obstructed breathing | Real time | [R04 §3.6] C |
| Contact shotgun to the head | 0 s | 1–10 min (heart continues) | Burst head, pulsatile bleeding from the defect | ~2 min | [R2-05 §2.5] C/E |
| Handgun body hits (stopping) | ~2 hits to stop on average; 47 % stop after the first 9 mm hit; 13–17 % never stop; "psychological stops" cannot be counted on | — | | — | [R2-02 §15] C |

### 4.8 Death criteria

1. **Circulatory arrest** = rhythm ∈ {VF, PEA, asystole} or effective CO < 0.3 L/min. Sets `t_arrest`; **the post-mortem clock starts here**. Pulsatile flow ends with the last effective beat.
2. **Dead flag** = arrest + 300 s (autoresuscitation window: p 0.1 of a brief return of a few beats in the first 5 min, never with consciousness) [R04 §10.1, C].
3. **Irreversible brain injury** begins after perf < 0.2 for 4–6 min (normothermic); cortex first, brainstem more tolerant.
4. **Death by neurologic criteria** (brainstem destroyed or herniation complete): coma, pupils fixed 4–9 mm (mean 5.0 ± 0.85), no corneal/oculocephalic/gag/cough reflexes, **no breathing effort even as CO₂ rises**; the heart then stops 4–10 min later from hypoxia [R04 §10.1, R2-04 §14, C].
5. After the dead flag, only post-mortem processes run (§6); spinal reflex movements are possible only while the cord is still perfused (p 0.1–0.2 after brainstem destruction, 1–10 min; full "Lazarus" arm raise rare) [R04 §10.4, R2-04 §14].

### 4.9 What the player sees, stage by stage

**Haemorrhage progression** [R04 §7.2, R03 §3.6, C]:

| Stage (loss) | Behaviour | Face / skin | Eyes (§5) | Breathing | Pulse / jets |
|---|---|---|---|---|---|
| 0–0.15 | Normal, maybe anxious | Normal | Normal, blinks 12–20/min | 14–18/min, calm | HR ≤ 100; strong jets |
| 0.15–0.30 | Anxious, restless, **thirsty**, dizzy upright (may faint), pleads | Pale (desaturate 20 %), cool hands, sweat beginning; hand and forearm veins flatten | Blinks more | 20–30/min; speech anxious but coherent | HR 100–120, narrow pulse pressure; jets faster |
| 0.30–0.40 | Confused, agitated **or** oddly quiet, air hunger, nausea, sense of doom, fumbling, complains of cold and "going dark"; yawning, sighing, shivering | Grey-white `#D9D2CC`, cold clammy sweat beads, **pale lips** `#C9A09E`, mottled knees `#8C5A70` (after ≥ 10–20 min of shock) | Sunken, dull, unfocused; pale conjunctivae `#EBCFCB`; pupils normal–large, sluggish; blinks 5–10/min, slow 300–500 ms | 30–40/min, sighing; speech weak, slurred, repetitive | HR 120–140, thready radial pulse; SBP 70–90; jets clearly lower |
| 0.40–0.50 | Lethargic → unresponsive (LOC ~0.45) | **Waxy white-grey** `#E3DCD3`; lips grey-lilac `#A99AA4`, **not blue** | Lids half-closed or fixed open, vacant, pupils dilating | Shallow and fast → slowing, irregular; moans, then no vocal effort | HR > 140 or paradoxically slowing; radial pulse gone; jets become welling surges |
| 0.50–0.60 | Unconscious, agonal | White, no capillary refill | Pupils wide and fixed, no blink | **Agonal gasps** 2–10/min (p 0.3–0.5), froth bubbling at the lips | PEA → asystole; jets stop |
| Arrest | — | Pallor extreme; livor faint/late | §5.4 | Final passive exhalation (sigh) at the last gasp or 5–30 s after arrest | Gravity drainage only |

**Breathing and airway catalogue** [R04 §5.5, §10, R2-04 §14, R2-06 §17, C/E]:

| State | Look |
|---|---|
| Normal | Belly then chest rise, 12–20/min |
| Pain / fear | Fast, gasping inhalations, breath holding; panting, moaning, screaming faces |
| Air hunger (Class III) | Deep, fast, suprasternal and intercostal tugging; sighs, yawns |
| Unconscious, supine | Tongue falls back: partial obstruction (slack jaw, chest and belly heaving); head tilt changes it |
| Blood in the airway | Coughing, spraying fine pink droplets; bubble-ring stains; froth bubbling at the lips on each breath |
| Upper-airway narrowing | Tugging |
| Chest-wall hole > 10–13 mm | Suck in / froth out, in time with RR |
| C1–C3 awake apnoea | Mouth and neck strain, chest still (no airflow) |
| C4–C6 | Paradoxical belly breathing; weak ineffective cough |
| Cheyne–Stokes | Crescendo–decrescendo cycles 40–90 s; sighs, then 10–30 s without breathing |
| Agonal gasping | 0.2–0.6 s inspiration with **neck extension and jaw opening**, 1–3 s passive expiration; intervals grow from ~10 s to ~1 min; lasts 1–5 min; absent after medullary destruction |
| Terminal secretions | Pooled secretions bubbling at the lips with each breath. **Only in deaths lasting hours** (median 16–23 h onset-to-death); never in fast violent deaths |
| After death | Chest still |

**Death-type choreography** (first 60 s always 1×) [R04 §8.2, §2, R2-04]:
- **Brainstem hit**: 0–1.2 s cut-strings collapse (no protective arm reaction, head strikes the floor, weapon drops in 0.1–0.5 s); no breathing (medulla) or a few strange breaths (pons); brief myoclonic twitches possible in the first seconds (p 0.2); rare transient decerebrate stiffening (midbrain); wounds keep pulsing for minutes, weakening; lips dusky blue over 1–2 min unless exsanguinated.
- **Heart destroyed**: 0–5 s normal action (can run, shout); 5–10 s grey-out, stumbles; 8–15 s collapse with eyes open, upgaze 2–10 s, myoclonic jerks (p 0.9, 1–10 irregular jerks); 15–40 s EEG flat, pupils start dilating at 30–45 s, fixed wide by 1–2 min; agonal gasps (p 0.3–0.5).
- **Anoxic sequence with a beating heart** (C1–C3, airway obstruction): LOC ~10–15 s after brain O₂ runs out, convulsive jerks ~15 s, extension ~20 s, flexion ~40 s, loss of tone ~1–1.5 min, last respiratory movement ~1–2 min, last isolated muscle movement up to ~4–7 min [R2-04 §14, L–M].
- **Destructive head wound**: instant flaccid collapse, a single jerk or extensor stiffening in 0–2 s, irregular twitches ≤ 5–20 s, no coordinated movement.
- **Post-arrest twitches**: fine fasciculations in the first ~15 min only; supravital contraction only when a muscle is struck (≤ 1.5–2.5 h).

### 4.10 Motor tone → powered ragdoll (Jolt)

PD torque per `PhysicalBone3D` in `_integrate_forces`: `τ = kp·θ_err − kd·ω_rel`, `kp = I·ω²`, `kd = 2ζ·I·ω`, equal and opposite torque on the parent; explicit torque caps (Godot 4.5 exposes no joint motors; 6DOF springs are uncapped) [R06 §10.4, R2-03 §11, V/E].

| Tone state | ω (rad/s) | ζ | Cap × | Target pose | Source |
|---|---|---|---|---|---|
| Voluntary | 10–12 (arms 6–8) | 0.8–1.0 | 1.0 | Animation | [R2-03 §11] E |
| Dazed | 5–8 | 1.0 | 0.6 | Animation with sag | [R2-03] E |
| Weak (Class III, hemiparesis) | 2–4 | 1.0 | 0.3–0.5 | Animation with gravity sag | [R2-03] E |
| Flaccid | 0 | — | 0 | None ("cut strings") | [R04 §2.3] C |
| Decorticate | 8–12 | 0.9 | 0.6 | Shoulders adducted, elbows 90–120° flexed, wrists 60–80° flexed, fists; legs extended, ankles 30–45° plantarflexed | [R04 §4.3] C/G |
| Decerebrate | 10–14 | 0.9 | 0.8 | Elbows 0–10°, forearms fully pronated, wrists 60–80° flexed; knees 0°, ankles 30–45° plantarflexed and inverted; neck 10–30° extended; jaw clenched; episodes 5–60 s, repeating every 30 s–5 min or on stimulus | [R04 §4.3] C/G |
| Fencing | 8–12 | 0.9 | 0.6 | Arm on the face side extended (often raised), other flexed; 2–10 s | [R04 §3.6] C |
| Tonic (seizure) | 12–15 | 0.7 | 1.0 | Extension rigidity, back arched | [R04 §4.2] G |
| Clonic | Oscillate ±10–25° about the tonic pose at 3–4 Hz slowing to ~1 Hz | 0.5 | 0.8 | Rhythmic jerks, gaps lengthening | [R2-04 §14] C |
| Rigor | Kinematic lock ramp (§6) | — | — | Current pose | [R04 §12.6] C |

- Stability: ω·Δt ≤ 0.5 (ω ≤ 30 rad/s at 60 Hz physics; use 120 Hz for close-ups); adjacent mass ratio ≤ 10:1 (neck ≥ 1–1.5 kg) [R2-03 §11, R06 §10.2].
- Torque caps (strong adult): neck 20–40 N·m, lumbar 200–300, shoulder 60–100, elbow 50–80, wrist 8–15, hip 200–300, knee 200–250, ankle 100–150 [R06 §10.4, C].
- **Tone loss speed**: ≤ 100 ms for off-switch injuries (brainstem, high cord, knockout); 0.5–2 s for faints and bleeding [R2-03 §11].
- **Collapse timing** [R04 §2.3, R2-03 §11, E]: centre-of-mass free fall ≥ 0.41 s; cut-strings collapse (knees and hips buckle) → first contact 0.35–0.55 s, head contact 0.7–1.2 s at 3–5 m/s; a rigid plank topple takes 1.0–1.6 s and is **wrong** for flaccid collapse. Falls follow the existing lean; unconscious falls have **no protective arm reaction**; conscious falls do (arm burst ~100 ms; hands land in 74 % of real falls, the head still hits in 37 %) [R2-02 §15].
- **Behaviours**: clutch wound (conscious, hand not paralysed; flow × 0.3–0.7); writhing (0.3–1 Hz procedural targets at weak tone); crawling/dragging with paralysed legs; agonal gasp (jaw and neck extension torque each gasp); partial-ragdoll flinch on every hit (influence 0.3–0.6 → 0 over 0.2–0.5 s) [R06 §10.3–10.5].
- Joint limits (living active ROM, add ~10 % passive when dead): neck flexion 45–50°, extension 45–60°, rotation 60–80°; elbow 0–145°; knee 0–135°; hip flexion 120°; dead key limits neck flex 70 / ext 85 / rot 90, knee −10 → 158, elbow −10 → 155 [R06 §10.1, R2-03 §11, C].
- Surface: friction 0.6–0.9 (skin/cloth on floor), **0.1–0.25 on wet blood**; restitution 0.1–0.3 (bounce setting 0) [R2-03 §11].

### Simulation parameters (physiology)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `o2_lung_max / cap_blood` | 400 / 850·(V/BV0) | mL | O₂ stores | [R04 §1] E |
| `vo2` | 250 × (0.8–2.0) | mL/min | | [R04 §1] C |
| `vent_supply_max` | 350 | mL/min O₂ | × E_vent | E |
| `brain_o2_reserve_max` | 8 (5–10) | s | Real time | [R04 §13.2] E |
| `loc_supine_loss / pea_loss` | 0.45 / 0.45–0.50 fast, 0.55 slow | fraction | | [R04 §7.4] C |
| `faint_upright_loss` | 0.20–0.30 | fraction | Per victim | [R04 §7.4] C |
| `hypoxic_arrest` | SpO₂ < 0.4 for > 150 s | — | Apnoea → arrest ≈ 6 min | E |
| `arrest_to_dead_flag / autoresus_p` | 300 s / 0.1 | — | | [R04 §10.6] C |
| `pea_to_asystole / vf_to_asystole` | 2–10 / 10–20 | min | | [R04 §10.3] C |
| `brain_irreversible` | perf < 0.2 for 4–6 min | — | | [R04 §1] C |
| `hemi_conscious_p / capacity_to_act_p` | 0.10–0.30 / 0.05–0.15 | p | Low-energy unilateral / frontal | [R04 §3.7] G |
| `impact_apnoea_p` | KO 0.1; moderate 0.3; severe/penetrating 0.6 | p | 5–30 s KO; 30 s–5 min severe | [R04 §3.7] G |
| `gaze_deviation_hemi` | 15–40 toward lesion | ° | | [R04 §3.7] C |
| `cord_complete_p` | 0.7–0.9 bullet through canal; 0.3–0.5 fragment | p | | [R04 §6.7] G |
| `resp_capacity_by_level` | C1–3 0–0.1; C4 .25; C5 .3; C6 .4; C7–8 .5; T1–6 .6; T7–12 .8; L+ 1.0 | fraction | | [R04 §6.7] C/L |
| `neurogenic_p` | cervical complete 0.7–1.0; cervical 0.19; thoracic 0.07; lumbar 0.03 | p | Trigger SBP < 100 & HR < 80 | [R04 §6.5] C |
| `seizure_early_p` | severe blunt 0.10–0.15; penetrating 0.2 | p | GTC ~62 s | [R04 §4.3] C |
| `posture_episode` | 5–60 s, every 30 s–5 min or on stimulus | — | | [R04 §4.3] G |
| `pd_omega` | voluntary 10–12 (arms 6–8), dazed 5–8, weak 2–4, flaccid 0 | rad/s | ω·Δt ≤ 0.5 | [R2-03 §11] E |
| `tone_loss_time` | ≤ 0.1 off-switch; 0.5–2 faint/bleed | s | | [R2-03 §11] C |
| `collapse_first_contact / head_contact` | 0.35–0.55 / 0.7–1.2 | s | Cut strings | [R2-03 §11] E |

### Visual/behavioural checklist (physiology)
- Bleeding victims progress visibly: restless and thirsty → grey, sweaty, confused, fast-breathing → lethargic with vacant half-open eyes → unconscious with gasps → still. A standing victim may faint at 20–30 % loss, recover briefly lying down, then collapse again.
- A brainstem or high-cord hit drops the body like a puppet in under a second, no arm reaction; a high-cord victim stays awake and unable to breathe.
- A heart shot never drops the target instantly: ~10 s of possible action, then collapse with eyes open and briefly rolled up, a few jerks.
- Unilateral brain wounds can leave the character awake with a paralysed side, eyes and head turned toward the wound.
- Paralysed limbs below a cord lesion never flinch, withdraw or react to cutting or burning.
- Posturing, seizures, knockouts and agonal gasps look distinct and only appear under their conditions.
- No terminal-secretion bubbling at the lips in fast deaths; no breathing at all after a medullary hit.

---

## 5. Eyes and face

### 5.1 Reference geometry [R04 §11.1, C/H]

| Quantity | Value |
|---|---|
| Globe diameter / axial length | ~24 / 23–24 mm (contract head: radius 0.012 m ✓) |
| Cornea (H × V), central thickness | 11.5–12 × 10.5–11 mm, 0.50–0.55 mm |
| Palpebral fissure (height × width) | 9–10 (8–11) × 28–30 mm; upper lid covers the top 1–2 mm of the cornea; lower lid at the lower limbus |
| Intraocular pressure | 10–21 mmHg (mean 15–16) |
| Colours | Sclera `#F1ECE2`, palpebral conjunctiva `#D98C87`, fine bulbar vessels `#B8424A`, pupil `#0A0A0A` |

### 5.2 Living eye behaviour (models)

**Blinks** [R04 §11.1, R2-06 §17, C/G]:
- Rate (Poisson, minimum interval 1 s [G]): alert 12–20/min (conversation up to 25; concentration 3–8); shock 5–10/min; unconscious 0–2; dead 0.
- Duration 250–400 ms: closing 70–100 ms, closed 0–50 ms, reopening 150–250 ms [K]; in shock slow blinks 300–500 ms (lids may shut and struggle open in lethargy).
- Bell's phenomenon: eyes roll up and slightly out behind closing lids.
- Stress: a burst of blinks, then staring with lid retraction.

**Gaze** [R2-06 §17, K]:
- Saccade duration **21 ms + 2.2 ms/°** (10° ≈ 43 ms); peak velocity 400–700 °/s; typical amplitude 2–15°, head joins shifts > ~20°.
- Fixations 200–400 ms; microsaccades < 1° about 1–2 per second [K]; smooth pursuit ≤ ~30 °/s [K].
- Upper lid tracks vertical gaze (gain ≈ 1 in rotation) [K].
- Targets while conscious: the attacker/weapon (fear), the own wound (pain), scanning (stress).
- Doll's eyes (vestibulo-ocular counter-rotation) gain 1.0 while the brainstem is intact — suppressed by fixation when awake, obvious when unconscious.

**Pupils** [R04 §11.1, §11.2, C/K]:
- Normal room light 3–4 mm; bright 2–4; dark 4–8.
- Light reflex: latency 200–250 ms, constriction ~1 s, redilation 2–4 s [K]; consensual (both eyes).
- Hippus ±0.2–0.5 mm at 0.2–0.5 Hz [K].
- Pain/fear: +1–2 mm within 0.5–2 s.
- Tears: basal 1–2 µL/min; the sac overflows beyond ~25–30 µL; a blow to the nose makes the eyes water within seconds [R2-06 §17].

### 5.3 Eye state table (drives the eye system) [R04 §11.2]

| State | Lid aperture | Gaze | Pupils | Reflexes | Blink | Surface |
|---|---|---|---|---|---|---|
| Alert | 9–10 mm | Fixations and saccades on targets | 3–4 mm, reactive | Corneal + | 12–20/min | Glossy |
| Pain / fear | **11–12 mm** (white above the iris) in fear; eyes squeezed shut in pain (AU43) | Rapid scanning, then fixed on the threat | +1–2 mm | + | Burst, then staring | Glossy, tearing |
| Shock III–IV | Heavy, 5–8 mm; eyes **sunken** | Vacant, slow saccades, poor tracking | Normal to large, **sluggish** | + | 5–10/min, slow | Pale conjunctiva `#EBCFCB` |
| Syncope / heart destroyed / sudden loss of brain perfusion | **Stay open** | **Conjugate upward deviation 10–30° for 2–10 s** (p 0.6–0.8), then drift to midline over 10–60 s | Dilating | Lost within tens of seconds | Stops | Glossy at first |
| Knockout | Open or closed (≈ 50/50) | Vacant, may briefly roll up | Equal, reactive | + | Absent while out | Glossy |
| Generalised seizure | Open (90–97 %), flutter | Deviated up or **away** from a cortical focus; nystagmoid jerks | Dilated, unreactive | Absent | None | Tearing |
| Postictal | Half-closed | Roving, slightly divergent | Sluggish | Returning | Rare | — |
| Coma, brainstem intact | Closed or part-open; a lifted lid closes again over 1–2 s | Slightly divergent, slow roving; **doll's eyes present** | Small–normal, reactive | Corneal + | Rare | Glossy |
| Destructive hemisphere lesion | Any | **Conjugate deviation toward the lesion** 15–40° | Normal | + | — | — |
| Thalamus | Any | Down and in | Small, reactive | + | — | — |
| Pons | Any | No horizontal movement; **ocular bobbing** (fast down, slow up, a few–10/min); skew; "wrong-way" deviation | **Pinpoint 1–2 mm** | Corneal lost | None | — |
| Midbrain | Any; ptosis with CN III | Dysconjugate, down-and-out, vertical gaze lost | **Mid-position 4–6 mm, fixed** | Lost | None | — |
| Uncal herniation | Ipsilateral ptosis | Ipsilateral eye down-and-out | **Ipsilateral blown 6–9 mm, fixed**, then both | Lost progressively | — | — |
| Locked-in | Open | Only vertical movements and blinks | Normal | + | Voluntary | Glossy |
| C1–C3 cord, awake apnoea | Wide | Darting, pleading | Normal, then dilate as SpO₂ falls | + until LOC | Normal/rapid, tears | Glossy |
| Brain death / death | **Stay where they were when tone was lost** (§5.4) | Neutral or slightly divergent; **no movement; move rigidly with the head (doll's eyes absent)** | **4–9 mm fixed** (mean 5.0 ± 0.85) | All absent | **None** | Gloss fades (§5.5) |

Brainstem signs in the living [R04 §11.7]: skew deviation 2–10° (medullary lesion: lesion-side eye lower; pontine/midbrain: opposite eye lower); Horner's (lateral medulla, T1 cord, carotid injury): ptosis 1–2 mm, pupil 0.5–1 mm smaller; internuclear ophthalmoplegia; nystagmus (cerebellar, vestibular).

### 5.4 Dying and death

**Lids at death** [R04 §11.3; no prevalence study exists — distribution G]:

| Death type | Open (aperture 6–10 mm) | Half-open (2–6 mm) | Closed (0–2 mm) |
|---|---|---|---|
| Sudden, awake victim (brainstem, heart, high cord) | 0.55 | 0.35 | 0.10 |
| Slow death through lethargy/coma (bleeding out, raised ICP) | 0.20 | 0.45 | 0.35 |
| After seizure or knockout progressing to death | 0.30 | 0.45 | 0.25 |

- At the moment tone fails an open lid **drops 2–4 mm over 1–3 s** (levator and Müller's tone lost); it **never blinks shut**. Closing is an active movement; "inability to close the eyelids" is a sign of death within days in palliative series [R04 §11.3, C].
- Manually closed lids of a dead character creep back open 1–3 mm over 1–5 min in ~50 % of cases before rigor; after rigor (≥ 2–4 h) they stay put. A living unconscious lid lifted by the player slowly closes again; a dead one stays up.
- Swelling overrides everything: orbital haematoma or raccoon eyes can push the lids shut in the living.

**Gaze** [R04 §11.4]: the dramatic upward roll belongs to syncope and seizures, not to death. After tone is lost, drift over 10–60 s to rest: **each eye 3–10° abducted, 0–5° elevated**; dysconjugate rest (one eye skewed or out) common after brainstem or CN III injury. No saccades, micro-movements or nystagmus after death. Turning a dead head: eyes move with it (doll gain 0).

**Pupils** [R04 §11.5, C]: global ischaemia → dilation begins 30–45 s after cerebral flow stops, **6–8+ mm and fixed by 1–2 min**; over 2–6 h after death they relax to **4–6 mm** with random anisocoria ≤ 1 mm and slight irregularity (iris rigor). Pinpoint pupils in a dead body only after a pontine lesion (or drugs). Pupil reads black until the cornea clouds, then grey `#6E7274`. Ripault's sign from ~30 min: squeezing the globe makes the pupil oval and it stays oval.

**Choreography by death type** (real time) [R04 §11.9]:
- *Brainstem gunshot*: lids flinch then stay open; blinking stops forever; pupils pinpoint (pons) / mid-fixed (midbrain) / normal (pure medulla); lids drop 2–4 mm in 1–3 s; eyes slightly divergent or skewed; pupils dilate with hypoxia at 60–180 s (unless midbrain-fixed); gloss fades over minutes.
- *Heart destroyed*: 0–5 s wide eyes, pupils dilating with fear, fixed on the wound or attacker; 5–10 s blank stare; 8–15 s LOC, eyes open and up 10–30° for 2–10 s with lid flutter during jerks; 15–60 s drift to near straight ahead, lids half-open; 30–120 s pupils 6–8 mm, fixed; agonal gasps move the head and the eyes move with it.
- *Slow exsanguination*: sunken, dull, pale conjunctivae, slow blinks, wandering gaze; lids close in lethargy; half-closed at LOC; pupils dilate and fix during the final gasps.
- *C1–C3*: wide, darting, pleading eyes with tears for 0–60 s; gaze slows, pupils widen at 60–120 s; LOC at 90–180 s, eyes stay open and drift up/out; then as heart-destroyed from the pupil stage.
- *Herniation*: one pupil enlarges, same-side ptosis and down-and-out eye; then the other pupil fixes; dysconjugate, doll's eyes lost; both wide and fixed at apnoea, lids part-open.

### 5.5 Post-mortem eye surface (sim time; open eyes unless stated) [R04 §11.6, C]

| Change | Onset | Appearance / shader target |
|---|---|---|
| Blink and corneal reflex lost | At brainstem failure | — |
| Tear film breaks up | 10–30 s after the last blink | `gloss` 1.0 → 0.8; corneal highlight irregular |
| Loss of lustre | minutes → 1 h | `gloss` 0.4 at 1 h, 0.15 at 6 h (closed eyes ×0.25 rate) |
| Corneal clouding | Begins 1–2 h, obvious 3–6 h, opaque 12–24 h; **closed eyes begin ~12 h, obvious ~24 h** | `corneal_opacity` 0.3 at 6 h, 0.7 at 24 h; tint `#C9CFCF`; iris and pupil fade |
| Scleral drying → *tache noire* | Yellow parchment triangles 1–3 h, **brown-black at 3–6 h** (range 1–12 h; ×1.5 faster warm/dry); exposed strip only, horizontal triangles each side of the cornea, base toward the cornea | `dry_band` `#CDB48C` → `tache_noire` `#5B3F2E` → `#30231B` |
| Loss of IOP | Steep in 1–2 h; globe soft by 2–4 h; cornea may wrinkle | `iop` 15 → < 5 mmHg by 2 h |
| Sunken globes | 12–24 h | Push the globe back 1–3 mm |
| Retinal "boxcarring" | Minutes, lasting 1–2 h | Forensic close-up only |
| Vitreous K⁺ (forensic readout) | +0.19 mmol/L/h; PMI (h) ≈ 5.26·K⁺ − 30.9 | Show ± 20 h (95 %) error band |

Haemorrhagic signs [R04 §11.8]: petechiae 0.1–2 mm `#8E1520` only from neck/chest compression, violent coughing or seizures, never from bleeding out; direct-trauma subconjunctival haemorrhage `#C0141E` bright, flat, sharply bordered, persists after death, resolves 7–14 d in the living; skull-base subconjunctival haemorrhage has no posterior border; hyphaema settles into a level; orbital haematoma proptosis 2–10 mm (living); conjunctival hypostasis (face-down bodies, hours) `#6E2D4E` with Tardieu dots.

### 5.6 Face behaviour

| State | Face | Source |
|---|---|---|
| Pain | Brow lowered (AU4), orbital tightening (AU6/7), nose wrinkle/upper lip raise (AU9/10), **eyes closed (AU43)**; grimace intensity with pain | [R2-06 §17] C |
| Fear | AU1+2+4+5+7+20+26: brows up and together, **eyes wide**, lips stretched, jaw drop | [R2-06 §17] C |
| Shock | Slack, grey-white, sweaty, sunken eyes, pale lips; nasolabial folds flatten late | [R04 §7.2] C |
| Hemisphere lesion (central facial palsy) | Contralateral lower-face droop; **forehead and eye closure spared**; emotional smile may be spared | [R2-06 §17] C |
| Temporal-bone fracture (peripheral palsy) | Whole half-face flaccid, incomplete eye closure with Bell's phenomenon | [R2-06 §17] C |
| Unconscious, supine | Jaw slack, mouth slightly open, tongue fallen back | [R04 §3.6] C |
| Near death (hours) | Drooping nasolabial folds, neck hyperextension, inability to close the lids | [R2-04 §14] C |
| Dead | **Jaw drops 10–30 mm within 5–30 s** (supine; less prone or on the side); expression relaxes — **the face does not keep its last expression** (cadaveric spasm is rare and affects the hands); tongue falls back; lips dry to brown parchment `#6E2E2E` over hours | [R04 §12.1], [R2-06 §17] C |

**Skin colour progression** (light–medium skin; lerp by loss) [R04 §7.7, G]:

| Region | Normal | 15–30 % | 30–40 % | > 40 % / dead from bleeding |
|---|---|---|---|---|
| Face | base | desaturate 20 % | desaturate 40 %, grey `#D9D2CC` | waxy `#E3DCD3` |
| Lips | `#B35E62` | `#BF8583` | `#C9A09E` | grey-lilac `#A99AA4` (not blue) |
| Palpebral conjunctiva | `#D98C87` | `#E2AAA5` | `#EBCFCB` | `#EFDCD8` |
| Nail beds | `#E2A9A6` | — | refill > 3 s | white `#EEE0DC` |
| Knees/thighs | — | — | lacy mottling `#8C5A70` 20–40 % | fades to pallor |
| Cyanosis (apnoea, full volume) | — | lips blue-grey in 60–120 s | — | — |
| Neurogenic flush below the lesion | warm pink `#E7A897` at 20–30 % | | | |

### Simulation parameters (eyes and face)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `lid_aperture` alert / fear / shock | 9–10 / 11–12 / 5–8 | mm | | [R04 §11.10] C/G |
| `blink_rate` alert / shock / unconscious / dead | 12–20 / 5–10 / 0–2 / 0 | /min | Poisson, min interval 1 s | [R04 §11.10] C |
| `blink_duration` normal / shock | 250–400 / 300–500 | ms | | [R04 §11.1], [R2-06] C |
| `saccade_duration` | 21 + 2.2·amplitude(°) | ms | Peak 400–700 °/s | [R2-06 §17] C |
| `fixation` | 200–400 | ms | | [R04 §11.1] C |
| `pupil_alert / light_latency / constrict_time` | 3–4 mm / 200–250 ms / ~1 s | — | | [R04 §11.1] C |
| `pupil_stress_delta` | +1–2 within 0.5–2 s | mm | | [R04 §11.2] C |
| `pupil_hypoxic_dilation` | start 30–45 s, 6–8+ mm by 60–120 s | — | | [R04 §11.5] C |
| `pupil_pontine / midbrain / blown` | 1–2 / 4–6 fixed / 6–9 fixed | mm | | [R04 §2.6, §5.6] C |
| `pupil_brain_death` | 4–9 (mean 5.0 ± 0.85) | mm | | [R04 §11.5], [R2-04 §14] C |
| `pupil_postmortem_relax` | → 4–6 over 2–6 h, anisocoria ≤ 1 | mm | | [R04 §11.5] C/L |
| `syncope_upgaze` | 10–30° for 2–10 s, p 0.6–0.8 | — | | [R04 §11.10] C |
| `gaze_drift_to_rest / rest_dead` | 10–60 s / 3–10° abducted, 0–5° up | — | | [R04 §11.4] G/C |
| `lid_drop_at_death` | 2–4 over 1–3 s | mm | | [R04 §11.3] G |
| `lid_state_at_death` | §5.4 table | p | | G |
| `doll_gain` | 1 (brainstem intact, unconscious) / 0 (dead, brainstem destroyed) | — | | [R04 §11.7] C |
| `gloss_curve` | 1.0 → 0.8 (1 min) → 0.4 (1 h) → 0.15 (6 h) | — | Closed ×0.25 | [R04 §11.10] G |
| `corneal_opacity` | 0 → 0.3 (6 h) → 0.7 (24 h); closed from 12 h | — | | [R04 §11.6] C |
| `tache_noire_onset` | 3–6 h (1–12), open eyes only | — | | [R04 §11.6] C |
| `jaw_drop` | 10–30 within 5–30 s | mm | Supine | [R04 §12.1] C/G |
| Instance uniforms (≤ 16/shader) | pupil_mm, pupil_reactive, gloss, corneal_opacity, dry_band, tache_noire, subconj_haem, petechiae | — | Lids and gaze through bones/LookAtModifier3D | [R06 §10.6] V |

### Visual/behavioural checklist (eyes and face)
- Living eyes blink 12–20 times a minute, dart in fast saccades, fixate on the attacker or the wound, and the pupils narrow within a quarter-second when a light hits them.
- At death the eyes do **not** close and do **not** roll back: they stay open or half-open, look roughly straight ahead or slightly outward, and never move again; they look "through" the player.
- Seconds before a sudden loss of consciousness the eyes may roll up briefly, then settle.
- Pupils go wide and black within a minute or two of arrest; hours later mid-sized, sometimes unequal; never pinpoint unless the pons was hit.
- Turn a dead head and the eyes turn with it; turn an unconscious living head and the eyes lag behind.
- Over hours the shine goes, the corneas haze grey, brown-black triangles form on the exposed whites, the globes soften and sink.
- A pained face squeezes the eyes shut; a frightened face opens them wide; a dead face relaxes and the jaw sags open.

---

## 6. Post-mortem changes (compressed timings)

All clocks start at circulatory arrest (`t_arrest`) and run in sim time (§1.3). Defaults are Mallach's data as tabulated by Henssge & Madea (mean, range) [R04 §12, C — every mean recall-consistent in the fact-check].

### 6.1 Primary flaccidity, jaw, settling
- All skeletal muscle goes limp at death until rigor (typically 1–3 h, range 0.5–7 h). Tone → 0 in ≤ 0.1–2 s depending on the death type (§4.10).
- Jaw drops 10–30 mm (supine) within 5–30 s; tongue falls back; lids per §5.4; sphincters may relax (urine release p 0.2–0.3, 50–200 mL over 1–5 min).
- Flaccid limbs settle to the lowest position; a supine head rolls to one side.

### 6.2 Blood after the heart stops
- Spurting stops at the last effective beat; arterial pressure → MSFP (~10 mmHg) within ~30–90 s; afterwards **gravity drainage only**, from wounds below the blood column: 50–500 mL total per dependent wound, decaying τ 20–40 min (more from a dependent large-vein wound, e.g. neck wound with the head down).
- Sudden deaths: blood often stays liquid for hours (drainage continues). Slow deaths: soft post-mortem clots.
- Moving the body squeezes blood and froth from the mouth and dependent wounds.
- Exposed wound edges, abrasions and lips dry to brown parchment over hours (`#8A5A3C`, lips `#6E2E2E`).

### 6.3 Pallor mortis
Skin pales within minutes to ~30 min as capillaries empty: desaturate and lighten 20–40 % over 15–30 min (face, lips, nail beds first); already extreme after exsanguination.

### 6.4 Livor mortis (hypostasis)

| Stage | Mean (range) |
|---|---|
| First patches | **0.75 h (0.25–3)** |
| Confluent | 2.5 h (1–4) |
| Maximum | 9.5 h (3–16) |
| Blanches completely under thumb pressure until | 5.5 h (1–20) |
| Blanches incompletely until | 17 h (10–30) |
| Shifts completely to the new lowest side if turned, until | 3.75 h (2–6) |
| Shifts partly (old and new both visible), until | 11 h (4–24) |

- Pattern: dependent areas relative to gravity when the body came to rest, with **contact pallor** where the body presses on the floor (supine: shoulder blades, buttocks, calves, back of the head) and pale lines from clothing folds/straps. Face-down bodies: facial and conjunctival congestion, Tardieu spots (0.5–2 mm `#3E1330`) after hours.
- Colour ramp: early `#CC8A8F` at 20–30 % opacity → established `#9A4E6B` 50–70 % → intense/fixed `#6E2D4E` 70–85 %. Exsanguinated bodies: opacity × (1 − 1.5·loss), minimum 0.1 (faint, patchy, late).
- Recompute the livor mask only when the body comes to rest and when it is moved; ≤ 1 Hz.

### 6.5 Algor mortis (Henssge double exponential, rectal temperature)
```
Ta ≤ 23.2 °C:  Q = (Tr − Ta)/(37.2 − Ta) = 1.25·exp(B·t) − 0.25·exp(5·B·t)
Ta > 23.2 °C:  Q = 1.11·exp(B·t) − 0.11·exp(10·B·t)
B = −1.2815·(c·m)^(−0.625) + 0.0284  (per h); c = 1.0 naked/still air, 1.1–1.4 clothed/covered, < 1 wet or moving air
```
Reference (75 kg, c = 1, 20 °C; B = −0.0579/h) [R04 §12.5, V arithmetic]: 1 h 37.1 °C · 2 h 36.7 · 4 h 35.7 · 6 h 34.4 · 8 h 33.1 · 12 h 30.6 · 18 h 27.6 · 24 h 25.4 · 36 h 22.7 · 48 h 21.3. Plateau of 0.1–0.5 °C in the first 2 h, then 0.6–0.7 °C/h. `T_death` is a state input (hypothermia from blood loss, hyperthermia from struggle). Forensic readout error ± 2.8 h (wider at long intervals). Hands, feet and face feel cool within 1–2 h; the trunk stays warm for hours; armpits longest.

### 6.6 Rigor mortis (optional feature)

| Stage | Mean (range) |
|---|---|
| Onset | **3 h (0.5–7)** |
| Fully developed | **8 h (2–20)** |
| Re-establishes after being broken, if broken before | 8 h (2–8) |
| Persists | 57 h (24–96) |
| Resolved | 76 h (24–192) |

- Order (Nysten): eyelids and jaw → face and neck → arms → trunk → legs (offsets 0, +0.5, +1, +1.5, +2 h); resolves in the same order. Faster with heat and with intense activity just before death (× 0.5), slower in cold (× 1.5–2).
- Implementation: per joint group `s(t)` 0 → 1 between onset and full; map to angular damping and to joint limits clamped around the current pose; an external torque above `τ_break·s` sets that group's `s` to 0.2 (re-grows to 0.6 if t < 8 h). Breaking rigor gives way suddenly, then stays loose.
- Cadaveric spasm (instant grip freeze): ≤ 1 % of deaths with intense activity; hands only.

### 6.7 Supravital reactions (forensic mode only, low confidence) [R04 §12.7]
Striking the biceps produces a visible contraction/idiomuscular bulge for ~1.5–2.5 h (a local bulge up to ~4–5 h); electrical eyelid reactions for several hours (weak local twitches up to ~13–22 h); pupils respond to eye drops for hours.

### 6.8 Master timeline (real time after arrest → game time)

| t_real after arrest | What changes | At 120× | At 720× |
|---|---|---|---|
| 0–1 min | Spurting stops; last gasp/sigh; jaw drops; lids settle; pupils dilating | 1× (real) | 1× |
| 1–5 min | Pupils wide and fixed; tear film broken; fine twitches; gravity drainage; dead flag at 5 min | 1× → 4× | 4× |
| 5–30 min | Pallor mortis; eye gloss fading; blood pooling at dependent wounds; pools gel | 5–15 s | 1–3 s |
| 30–60 min | First livor patches; hands/face cool; Ripault's sign | 15–30 s | 3–5 s |
| 1–3 h | Livor confluent; rigor begins in jaw and lids; globe soft; corneal haze begins (open); yellow dried scleral bands | 0.5–1.5 min | 5–15 s |
| 3–6 h | Tache noire darkens; rigor in neck and arms; livor still shifts if turned; rectal 36.3 → 34.4 °C | 1.5–3 min | 15–30 s |
| 6–12 h | Rigor complete; livor maximal and fixing; corneas clearly cloudy (open eyes); 34–31 °C | 3–6 min | 30–60 s |
| 12–24 h | Livor fixed; open corneas opaque by 24 h, closed ones begin to cloud; globes sunken; 31–25 °C | 6–12 min | 1–2 min |
| 24–48 h | Rigor persists then begins resolving; near ambient temperature; first decomposition (greenish right lower abdomen from ~24–36 h, out of scope) | 12–24 min | 2–4 min |

### Simulation parameters (post-mortem)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `pm_clock_start` | circulatory arrest | — | | [R04 §12.9] C |
| `pm_scale / ff_scale` | 120 / 720 | × | | G |
| `pm_drainage` | 50–500, τ 20–40 min, dependent wounds only | mL | 0.78 mmHg/cm | [R04 §12.2] E/G |
| `pallor_mortis` | 15–30 min, −20–40 % saturation/lightness | — | | [R04 §12.3] C/G |
| `livor_onset / confluent / max` | 0.75 (0.25–3) / 2.5 (1–4) / 9.5 (3–16) | h | | [R04 §12.4] C |
| `livor_blanch_complete / incomplete` | 5.5 (1–20) / 17 (10–30) | h | Thumb-press interaction | [R04 §12.4] C |
| `livor_shift_complete / partial` | 3.75 (2–6) / 11 (4–24) | h | Turning the body | [R04 §12.4] C |
| `livor_opacity_exsanguinated` | × (1 − 1.5·loss), min 0.1 | — | | [R04 §12.4] G |
| `algor` | Henssge; c 1.0 naked, 1.1–1.4 clothed | — | ± 2.8 h readout | [R04 §12.5] C/V |
| `rigor_onset / full / persist / resolved` | 3 (0.5–7) / 8 (2–20) / 57 (24–96) / 76 (24–192) | h | × 0.5 hot/active, × 1.5–2 cold | [R04 §12.6] C |
| `rigor_order_offsets` | jaw/lids 0, neck 0.5, arms 1, trunk 1.5, legs 2 | h | | [R04 §12.6] C/G |
| `rigor_reestablish_window` | 8 | h | | [R04 §12.6] C |
| `urine_release_p` | 0.2–0.3 (50–200 mL) | p | | [R04 §12.1] G |

### Visual/behavioural checklist (post-mortem)
- At the instant of death the jet stops mid-rhythm, the body goes completely slack, the jaw sags open and the lids settle half-open.
- Within half an hour the face drains to a waxy pallor and the eye shine dulls.
- Within the hour faint pink-purple blotches appear on the down-side of the body, except where it presses on the floor; hands feel cool.
- Over hours the blotches merge into a deep purple band; jaw and neck stiffen, then arms, then legs; a forced joint gives way suddenly and stays loose.
- A bled-out body has barely any livor and looks white overall.
- Moving the body squeezes blood/froth from the mouth and dependent wounds.

---

## 7. Body anatomy summary (body frame, metres, Z up, face −Y, left +X, origin on the floor between the feet)

Reference body: male, 1.78 m, 75 kg, ~15 % fat, A-pose (§1.2). Accuracy: ±5–10 mm surface landmarks, ±10–20 mm deep structures, ±2–5 mm dimensions [R05 §0.1]. All heights scale with k = H/1.78 (§7.8). Head-internal positions use the contract head placed at `p_body = p_head + (0, 0.020, 1.647)`.

### 7.1 Landmarks (code-ready CSV; corrected values from the R05 fact-check, head rows already lowered 8 mm) [R05 §13.1]

```csv
# name,x,y,z,kind   (kind: skin | bone | joint); left side, mirror x for right
# head rows: the existing contract head overrides these inside the head (vertex 1.772, ear canal x 0.072, chin (0,-0.060,1.544)); see §1.2
vertex,0.000,0.020,1.780,skin
head_origin_mid_ear_canals,0.000,0.020,1.647,joint
ear_canal_L,0.068,0.020,1.647,skin
mastoid_tip_L,0.055,0.030,1.612,bone
inion,0.000,0.112,1.654,skin
basion,0.000,0.018,1.626,bone
atlanto_occipital_pivot,0.000,0.015,1.622,joint
menton,0.000,-0.068,1.550,skin
gonion_L,0.052,-0.005,1.577,skin
hyoid_body,0.000,-0.030,1.556,bone
laryngeal_prominence,0.000,-0.062,1.537,skin
cricoid,0.000,-0.055,1.515,skin
c7_spinous_cervicale,0.000,0.075,1.532,skin
jugular_notch,0.000,-0.048,1.455,skin
sc_joint_L,0.025,-0.040,1.450,joint
ac_joint_L,0.165,0.010,1.462,joint
acromion_L,0.200,0.015,1.458,bone
gh_joint_L,0.180,0.020,1.415,joint
sternal_angle,0.000,-0.075,1.405,skin
nipple_L,0.100,-0.112,1.300,skin
xiphisternal_joint,0.000,-0.110,1.305,skin
xiphoid_tip,0.000,-0.094,1.273,bone
scapula_inferior_angle_L,0.085,0.105,1.325,bone
costal_margin_lowest_L,0.112,-0.050,1.125,bone
navel,0.000,-0.108,1.075,skin
iliac_crest_top_L,0.140,0.025,1.070,bone
asis_L,0.122,-0.062,0.992,bone
psis_L,0.045,0.090,1.010,bone
pubic_symphysis_top,0.000,-0.068,0.911,bone
mid_inguinal_point_L,0.065,-0.068,0.940,skin
hip_joint_centre_L,0.087,-0.015,0.918,joint
greater_trochanter_L,0.158,0.000,0.913,bone
ischial_tuberosity_L,0.055,0.020,0.841,bone
crotch,0.000,0.005,0.860,skin
elbow_centre_L_apose,0.325,0.020,1.164,joint
wrist_centre_L_apose,0.460,0.020,0.930,joint
mcp3_L_apose,0.508,0.020,0.848,joint
fingertip3_L_apose,0.553,0.020,0.770,skin
knee_centre_L,0.092,0.020,0.492,joint
patella_centre_L,0.090,-0.035,0.497,bone
tibial_tuberosity_L,0.090,-0.025,0.434,bone
fibular_head_L,0.130,0.035,0.452,bone
ankle_centre_L,0.095,0.050,0.075,joint
lateral_malleolus_L,0.132,0.060,0.055,bone
medial_malleolus_L,0.065,0.045,0.068,bone
heel_L,0.095,0.115,0.030,skin
toe2_tip_L,0.128,-0.151,0.010,skin
```
ANSUR II checks (14 men 1.77–1.79 m / 71–79 kg; V): cervicale 1.532, suprasternale 1.454, acromion 1.449, nipple 1.305, omphalion 1.072, iliocristale 1.071, trochanterion 0.920, crotch 0.860, lateral femoral epicondyle 0.490, tibiale 0.480, stylion 0.848, lateral malleolus 0.073. Girths (cm): head 57.5, neck 38, chest 100 (breadth 28.7 × depth 23), waist at navel 84, hips 97, upper thigh 58, calf 37.5; biacromial 42, bideltoid 49 [R05 §2.1]. Model torso rings as superellipses (n ≈ 3.5 chest, 2.8 waist, 2.5 limbs) with section centres offset in y (buttocks +0.028, calf 7 cm behind the shin) [R05 §2.1].

### 7.2 Rig, segment masses, joint pivots [R05 §2.2–2.3, V (Dempster/Winter table)]

| Bone | Parent | Head (x, y, z) | Tail (x, y, z) | Length | Mass (kg, 75 kg body) | COM from head |
|---|---|---|---|---|---|---|
| `hips` | root | (0, −0.005, 0.965) | (0, 0.006, 1.027) | 0.063 | pelvis 10.65 | — |
| `spine` (lumbar) | hips | (0, 0.006, 1.027) | (0, 0.002, 1.212) | 0.185 | abdomen 10.4 | 0.44 |
| `chest` | spine | (0, 0.002, 1.212) | (0, 0.049, 1.353) | 0.149 | thorax 16.2 (chest + upper_chest) | 0.82 |
| `upper_chest` | chest | (0, 0.049, 1.353) | (0, 0.015, 1.490) | 0.141 | | |
| `neck` | upper_chest | (0, 0.015, 1.490) | (0, 0.015, 1.622) | 0.132 | head + neck 6.08 (split ~5.0 + 1.1; neck ≥ 1–1.5 kg) | COM ≈ ear canal |
| `head` | neck | (0, 0.015, 1.622) | (0, 0.020, 1.780) | 0.158 | | Existing head origin at (0, 0.020, 1.647) |
| `clavicle.L` | upper_chest | (0.025, −0.040, 1.450) | (0.165, 0.010, 1.462) | 0.149 | — | |
| `upper_arm.L` | clavicle.L | (0.180, 0.020, 1.415) | (0.325, 0.020, 1.164) | 0.290 | 2.10 | 0.436 |
| `forearm.L` | upper_arm.L | (0.325, 0.020, 1.164) | (0.460, 0.020, 0.930) | 0.270 | 1.20 | 0.430 |
| `hand.L` | forearm.L | (0.460, 0.020, 0.930) | (0.508, 0.020, 0.848) | 0.095 | 0.45 | 0.506 |
| `thigh.L` | hips | (0.087, −0.015, 0.918) | (0.092, 0.020, 0.492) | 0.428 | 7.50 (de Leva 10.6 alternative) | 0.433 |
| `shin.L` | thigh.L | (0.092, 0.020, 0.492) | (0.095, 0.050, 0.075) | 0.418 | 3.49 | 0.433 |
| `foot.L` | shin.L | (0.095, 0.050, 0.075) | (0.119, −0.079, 0.025) | 0.140 | 1.09 | 0.50 |
| `toes.L` | foot.L | (0.119, −0.079, 0.025) | (0.128, −0.151, 0.010) | 0.074 | — | |

Head pivots: nodding at the atlanto-occipital joint (0, 0.015, 1.622); ~50 % of neck rotation at C1–C2 about a vertical axis through (0, 0.008, 1.60). Whole-body standing COM ≈ 0.96 m [R2-03 §11]. **Resolved (segment table):** keep Winter/Dempster (verified) as default; switch to de Leva (thigh ~10.6 kg, lower and heavier-legged falls) if falls look top-heavy [R06 §10.1, R2-03].

### 7.3 Skeleton

**Vertebrae** (x = 0; body centres; cord centre y; L2–S1 have no cord, only cauda equina) [R05 §13.4]:
```csv
# level,y,z,body_h_mm,body_w_mm,body_d_mm,disc_below_mm,canal_ap_mm,canal_w_mm,spinous_dy_mm,cord_y,cord_w_mm,cord_ap_mm
C1,0.020,1.610,10,78,45,0,30,28,30,0.024,11.5,8.5
C2,0.012,1.590,23,17,15.5,5,16,24,43,0.027,11.9,7.9
C3,0.007,1.570,14,16.5,15.5,5,14.5,23,40,0.023,12.5,8.0
C4,0.004,1.553,14,17.5,15.5,5,14,24,40,0.020,13.0,7.8
C5,0.003,1.536,13.5,18.5,16,5,14,24,42,0.019,13.5,7.7
C6,0.004,1.518,13.5,20,16.5,5,14,24,45,0.020,13.0,7.5
C7,0.010,1.500,15,22,16.5,5,14,23,57,0.026,12.0,7.5
T1,0.019,1.481,16,26,16.5,4.5,14,19,60,0.035,10.5,7.0
T2,0.028,1.461,17,27,17.5,4.5,14,17,60,0.044,9.0,6.5
T3,0.036,1.441,17.5,27,18.5,4.5,14,16,61,0.053,8.8,6.5
T4,0.042,1.420,18,27.5,20,5,13.5,15.5,62,0.060,8.5,6.5
T5,0.046,1.398,18.5,28.5,22,5,13.5,15.5,63,0.065,8.5,6.4
T6,0.049,1.376,19,30,24,5,13.5,15.5,64,0.069,8.3,6.4
T7,0.049,1.353,19.5,31,26,5,13.5,15.5,64,0.069,8.0,6.3
T8,0.046,1.329,20,32.5,27.5,5.5,14,16,63,0.067,8.0,6.3
T9,0.040,1.305,21,34,28.5,6,14,16,62,0.061,8.3,6.5
T10,0.031,1.280,22,37,29.5,6.5,14.5,17,62,0.053,8.5,7.0
T11,0.020,1.254,23,40,31,7,15,18,58,0.043,9.5,7.5
T12,0.008,1.227,24,42,32,8,16,21,58,0.031,10.0,8.0
L1,-0.004,1.197,25.5,43,33,10,17,22,68,0.021,8.0,7.0
L2,-0.013,1.161,26.5,45,34,11,17,23,70,0.013,0,0
L3,-0.018,1.124,27,48,35,12,16,23,70,0.008,0,0
L4,-0.016,1.087,27,50,35,12,16,24,70,0.011,0,0
L5,-0.005,1.050,26.5,52,35,11,17,26,65,0.022,0,0
S1,0.014,1.012,30,50,30,0,15,30,0,0.035,0,0
```
Known fit conflict: the ANSUR II cervicale skin bump (1.532) sits ~3 cm above the C7 body centre (1.500); expect ±2–3 cm in C4–T3 until a refit [R05 §4.6]. Surface levels: jugular notch T2/T3, sternal angle T4/T5, xiphisternum T9, subcostal plane L3, iliac crests L4/L5 (V), navel L3/4–L4. Thoracic spinous tips lie one level below their body (T5–T8). Curvatures: cervical lordosis ~30°, thoracic kyphosis ~36°, lumbar lordosis ~60°, pelvic incidence 53° [R05 §4.2, V ranges].

**Ribs** (left; head at the spine, CCJ = costochondral junction, cartilage end at the sternum or the cartilage above) [R05 §5.2, E]:

| Rib | Head | Lateral (≈ MAL) | CCJ | Cartilage end | Arc / cartilage (mm) |
|---|---|---|---|---|---|
| 1 | (0.018, 0.030, 1.481) | (0.055, −0.005, 1.462) | (0.035, −0.030, 1.440) | manubrium (0.020, −0.042, 1.440) | 80 / 25 |
| 2 | (0.020, 0.038, 1.469) | (0.085, 0.015, 1.440) | (0.045, −0.052, 1.405) | sternal angle (0.016, −0.062, 1.405) | 150 / 30 |
| 3 | (0.020, 0.046, 1.449) | (0.105, 0.022, 1.414) | (0.058, −0.066, 1.372) | (0.015, −0.071, 1.380) | 195 / 35 |
| 4 | (0.020, 0.052, 1.428) | (0.118, 0.025, 1.388) | (0.070, −0.075, 1.340) | (0.016, −0.079, 1.355) | 225 / 45 |
| 5 | (0.021, 0.056, 1.406) | (0.127, 0.025, 1.362) | (0.082, −0.080, 1.308) | (0.017, −0.086, 1.332) | 245 / 55 |
| 6 | (0.021, 0.059, 1.384) | (0.133, 0.022, 1.336) | (0.092, −0.080, 1.275) | (0.015, −0.094, 1.312) | 260 / 75 |
| 7 | (0.022, 0.059, 1.361) | (0.137, 0.018, 1.308) | (0.100, −0.075, 1.240) | xiphisternal (0.010, −0.098, 1.302) | 270 / 110 |
| 8 | (0.022, 0.056, 1.337) | (0.139, 0.015, 1.280) | (0.110, −0.062, 1.205) | → 7th cartilage (0.060, −0.090, 1.245) | 270 / 90 |
| 9 | (0.023, 0.050, 1.313) | (0.139, 0.015, 1.250) | (0.118, −0.048, 1.175) | → 8th (0.085, −0.078, 1.200) | 260 / 70 |
| 10 | (0.024, 0.041, 1.280) | (0.136, 0.018, 1.212) | (0.125, −0.030, 1.150) | → 9th (0.100, −0.065, 1.150) | 240 / 55 |
| 11 | (0.025, 0.030, 1.254) | (0.130, 0.030, 1.185) | free tip (0.125, 0.010, 1.160) | cap | 190 / 10 |
| 12 | (0.025, 0.018, 1.227) | — | free tip (0.085, 0.060, 1.180) | cap | 120 / 5 |

Sweep a rounded section 12–15 × 5–7 mm (rib 1: 25–30 × 5) through head → posterior angle → lateral → CCJ; costal groove on the lower inner edge (intercostal vein, artery, nerve). Rib cortex ~1 mm; intercostal spaces 15–25 mm front, 8–12 mm back. Sternum inclined 20° (lower end forward): manubrium 50 mm, body 105 mm, xiphoid 35 mm; soft tissue in front only 5–12 mm; the RV lies 25–35 mm behind the lower sternal skin [R05 §5].

**Bones: dimensions, cortex, marrow** [R05 §6–8, C; cortex values M/L]:

| Bone | Length (cm) | Mid-shaft Ø (mm) | Cortex (mm) | Interior / cut colour |
|---|---|---|---|---|
| Femur | 47 (47–48.5) | 28 (29 × 27) | 7 (6–8) | Yellow marrow shaft `#E4C36A`; red in neck/head |
| Tibia | 41 | 32 × 23 triangular | 6 (5–7) | Anteromedial face subcutaneous (3–6 mm) |
| Fibula | 39.5 | 14–16 | 2.5–3.5 | |
| Humerus | 33.5–34.5 | 21 (22 × 20) | 5 (4–6) | Radial nerve in the spiral groove (wrist drop with shaft fractures) |
| Radius / ulna | 26.0 / 27.5 | 13–14 | 2.5–3.5 | Ulna border subcutaneous |
| Clavicle | 14.8 | 12 | 2–3 | Subclavian vessels and plexus under its middle third |
| Scapula blade | 15.5 × 10.5 | — | 1–3 total (fossae translucent) | Clean bullet hole + cracks |
| Ribs | §7.3 | 13 × 6 | ~1 | Red marrow `#B5524A`, oozes |
| Vertebral body | CSV | — | shell 0.3–0.6 | Red marrow; crushes |
| Iliac wing | — | 2–4 thin centre, 10–15 crest | 1–2 | Bullets perforate it cleanly |
| Skull vault | frontal 7 (5.8–8), parietal 6 (5.4–7), temporal squama 2–5, occipital 8–8.6, orbital roof/floor 0.25–1 | — | tables 1.5–2 each | Diploë `#A4574A` bleeds |

Materials: cortical bone 1.9 g/cm³, E 17–20 GPa, ultimate tension/compression/shear ~130/190/70 MPa; trabecular (vertebral) 1–7 MPa; three-point bending failure femur 3–5 kN, tibia 2.5–4, humerus 1.5–2.5, radius/ulna 1–1.5 each [R05 §8.2, R2-05 §8.1, C/L]. Colours: cortical cut `#E9DFCC`, periosteum `#E6CFC4`, articular cartilage `#DDE3E6`, costal cartilage `#CBD5D8`, disc annulus/nucleus `#E3E0D6`/`#D8DDD2`, dura `#D9D6CE`.

### 7.4 Spinal cord and brainstem [R05 §9, C; C2/C5/T8 sizes V]

- Cord 45 cm (foramen magnum → conus); conus tip L1/L2 (0, 0.017, 1.180); thecal sac ends at S2 (0, 0.035, 0.995); cauda equina chain L1/L2 → S2, radius 7 mm.
- Cord centreline = CSV `cord_y` at each body-centre z; ellipse radii = half the width/AP (C2 5.95 × 3.95 mm; C5 6.75 × 3.85; T7 4.0 × 3.15). Add a canal chain (radius = canal AP/2) for near-miss concussion. Depth from back skin: C5 ~45 mm, T7 ~53 mm, conus ~60 mm.
- Cord colour: white `#EEE5D6` with a grey butterfly `#B9A89E`, silvery dural tube, clear CSF (leaks watery, blood-tinged from canal wounds).

**Brainstem nodes** (relative to the head origin — use with the contract head; body = rel + (0, 0.020, 1.647)) [R05 §9.4]:

| Structure | Centre rel. head origin (m) | Size (length × width × AP, mm) | Notes |
|---|---|---|---|
| Midbrain | (0, −0.010, +0.035) | 15–20 × 30 × 25 | Tentorial notch; CN III |
| Pons | (0, −0.006, +0.012) | 25–27 × 35–38 × 25 | Basis front at y_rel ≈ −0.019 on the clivus |
| **Pontomedullary junction** | **(0, 0.000, 0.000)** | — | At the head origin (CN VII/VIII exit) |
| Medulla | (0, +0.005, −0.014) | 30 × 20 → 12 × 12–13 | Respiratory/vasomotor centres |
| Cervicomedullary junction | (0, +0.010, −0.028) | 11 × 9 | At the foramen magnum |
| Cerebellum | (0, +0.045, −0.005), hemispheres x ±0.045 | 100 × 50 × 55 | 140–150 g |
| Capsule chain `brainstem` (body) | (0,0.030,1.619) → (0,0.025,1.633) → (0,0.020,1.647) → (0,0.014,1.659) → (0,0.010,1.682), r 11 mm | | Long axis tilted 15–25° top-forward |

Label hit volumes `midbrain`, `pons_tegmentum`, `pons_basis`, `medulla`, `cord_C1_C2` separately and give each a concussive radius (18 mm handgun) [R04 §2.1]. From the front the brainstem column lies behind the brow-line/nose "T"; from behind, just below the external occipital protuberance; from the side, on the ear-canal line and 0–2 cm in front of it.

### 7.5 Organs and hit volumes [R05 §13.2–13.3, §10–11]

```csv
# name,shape,cx,cy,cz,size_u,size_v,size_w,ux,uy,uz,vx,vy,vz,mass_g   (full lengths; aabb: u=+X, v=+Y)
heart,obb,0.035,-0.036,1.325,0.125,0.090,0.065,0.632,-0.498,-0.593,0.466,-0.367,0.805,320
heart_RA,ellipsoid,-0.030,-0.018,1.335,0.045,0.050,0.045,1,0,0,0,1,0,0
heart_RV,ellipsoid,0.012,-0.060,1.312,0.070,0.030,0.060,1,0,0,0,1,0,0
heart_LA,ellipsoid,0.008,-0.008,1.365,0.050,0.038,0.040,1,0,0,0,1,0,0
heart_LV,ellipsoid,0.045,-0.035,1.305,0.090,0.055,0.055,0.632,-0.498,-0.593,0.466,-0.367,0.805,0
lung_R,aabb,-0.075,0.006,1.383,0.130,0.168,0.225,1,0,0,0,1,0,550
lung_L,aabb,0.075,0.008,1.380,0.130,0.165,0.230,1,0,0,0,1,0,480
liver,aabb,-0.033,-0.008,1.235,0.225,0.155,0.160,1,0,0,0,1,0,1550
liver_right_lobe,ellipsoid,-0.075,0.000,1.235,0.140,0.150,0.160,1,0,0,0,1,0,0
liver_left_lobe,ellipsoid,0.035,-0.045,1.270,0.090,0.070,0.060,1,0,0,0,1,0,0
liver_caudate,ellipsoid,-0.010,0.030,1.255,0.030,0.030,0.060,1,0,0,0,1,0,0
gallbladder,capsule,-0.060,-0.043,1.208,0.080,0.035,0.035,0.466,0.699,0.543,0.832,-0.555,0,40
spleen,obb,0.105,0.040,1.228,0.120,0.070,0.030,0.390,-0.547,-0.742,0.445,-0.594,0.672,150
kidney_L,obb,0.070,0.024,1.180,0.115,0.060,0.040,0.258,-0.198,-0.946,-0.804,-0.586,-0.097,150
adrenal_L,ellipsoid,0.042,0.025,1.230,0.030,0.010,0.050,1,0,0,0,1,0,5
stomach,aabb,0.038,-0.025,1.200,0.145,0.120,0.210,1,0,0,0,1,0,150
bladder_empty,sphere,0.000,-0.030,0.898,0.050,0.050,0.050,1,0,0,0,1,0,50
bladder_full,sphere,0.000,-0.035,0.943,0.100,0.100,0.100,1,0,0,0,1,0,50
thyroid_lobe_L,ellipsoid,0.022,-0.028,1.505,0.020,0.018,0.050,1,0,0,0,1,0,9
thyroid_isthmus,ellipsoid,0.000,-0.042,1.492,0.020,0.005,0.020,1,0,0,0,1,0,2
bowel_filler,aabb,0.000,-0.040,1.040,0.240,0.120,0.280,1,0,0,0,1,0,2200
# right side: kidney_R (-0.070,0.024,1.160) u(-0.258,-0.198,-0.946) v(0.804,-0.586,-0.097); adrenal_R (-0.040,0.030,1.235)
# bowel_filler has the lowest hit priority (intestines are not modelled; mass/volume filler only)
```
```csv
# tube structures: name,radius,x1,y1,z1,x2,y2,z2,...
trachea,0.010,0.000,-0.030,1.508,0.000,-0.018,1.455,-0.003,0.008,1.402
bronchus_R,0.0075,-0.003,0.008,1.402,-0.028,0.012,1.380
bronchus_L,0.006,-0.003,0.008,1.402,0.042,0.020,1.380
oesophagus,0.009,0.000,-0.012,1.508,0.004,0.012,1.450,0.000,0.022,1.415,0.002,0.024,1.355,0.012,0.012,1.310,0.022,-0.008,1.280,0.030,-0.018,1.255
pancreas,0.012,-0.035,-0.035,1.160,-0.005,-0.050,1.180,0.025,-0.045,1.195,0.090,0.015,1.215
brainstem,0.011,0.000,0.030,1.619,0.000,0.025,1.633,0.000,0.020,1.647,0.000,0.014,1.659,0.000,0.010,1.682
cauda_equina,0.007,0.000,0.017,1.180,0.000,0.013,1.161,0.000,0.008,1.124,0.000,0.011,1.087,0.000,0.022,1.050,0.000,0.035,0.995
# great vessels: see §3.3 waypoints
```

Key organ facts [R05 §10–11, V/C]:
- **Heart** 320 g (250–380), 12.5 × 9 × 6.5 cm, axis base (0, −0.005, 1.360) → apex (0.082, −0.068, 1.285) (left, forward, down); apex beat 5th left ICS, MCL (~9 cm from midline). Walls: LV 9 mm (echo 6–10; cut post-mortem 12–14), RV 3–5, atria 2–3. Valves: pulmonary (0.022, −0.058, 1.378), aortic (0.008, −0.038, 1.360), mitral (0.030, −0.030, 1.340), tricuspid (−0.008, −0.048, 1.325). Myocardium `#7B2626`, epicardial fat `#E6C45A`.
- **Lungs**: apex 2.5–3 cm above the medial clavicle (z 1.495); lower lung border 6th rib MCL / 8th MAL / 10th back (z ≈ 1.27–1.28); pleura 8th / 10th / 12th (z ≈ 1.21–1.23 — a stab there crosses pleura and diaphragm into liver or spleen). TLC 7.1 L, FRC 3.35, tidal 0.5 (V). Pink `#E0A0A0` with anthracotic speckles `#3A3A3A`; dependent post-mortem `#A04A55`.
- **Diaphragm** domes R z 1.320, L 1.300, central tendon 1.310 (standing, end-expiration); excursion 1.5–2 cm quiet, 6–10 cm deep; openings IVC T8, oesophagus T10, aorta T12 (V).
- **Liver** 1,550 g (970–1,860 V); lower edge along the right costal margin, crosses the midline ~halfway xiphoid–navel; red-brown `#7A2E23`. **Spleen** 150 g, 12 × 7 × 3 cm under left ribs 9–11 (V), purple `#5E2433`. **Kidneys** 150 g each, T12–L3, right ~2 cm lower (V), 5–7 cm from the back skin, in yellow perirenal fat. Pancreas crushed against L1 by upper-abdominal blows. Bladder behind the symphysis unless full (ruptures under a kick when full).
- Posture: supine organs sit 2–4 cm higher than standing (cosmetic, post-mortem pose only) [R05 §14.1].

### 7.6 Tissue layers and depth to structures [R05 §12.2, C/M]

| Region (point) | Skin / fat / muscle (mm) | Depth to key structure |
|---|---|---|
| Scalp | 3.5–5.5 skin, 5–8 total to bone | Outer table at ~6 mm |
| Neck, anterior midline (cricoid) | 1.5 / 2–5 / 3–4 | Trachea 8–12 mm; thyroid isthmus ~10 mm |
| Neck, over the carotid (C4–C6) | 1.5 / 3–6 / platysma 1–2 + SCM 8–12 | **CCA/IJV 20–30 mm** |
| Neck, posterior midline C4 | 3 / 3–8 / 25–35 | Lamina ~35 mm; **cord 45–55 mm** |
| Over the sternum | 1.5–2 / 3–8 / — | Bone 5–12 mm; **RV 25–35 mm** |
| Anterior chest 2nd ICS MCL | 2 / 5–10 / 15–35 | **Pleura ~42 mm** (20–80) |
| Lateral chest 5th ICS MAL | 2 / 5–15 / 10–22 | **Pleura ~32–34 mm** |
| Upper back T4–T7, 4–5 cm lateral | 3–4 / 5–10 / 30–50 | Rib 40–60 mm; over spinous tips 8–12 mm |
| Abdomen paramedian at the navel | 2 / 12–20 / rectus 10–12 | Peritoneum 25–40 mm; aorta ~75 mm |
| Flank MAL L2 | 2 / 10–25 / 15–20 | Peritoneum 30–45; kidney edge 60–80 |
| Lower back L3, 4–5 cm lateral | 3–4 / 8–20 / 40–55 | **Kidney 50–70 mm**; canal ~70 mm midline |
| Groin | 1.5 / 8–15 / — | **Femoral artery 15–30 mm** |
| Upper arm anterior | 1.5 / 4–7 / 30–40 | Humerus 40–45; brachial artery medially 10–20 |
| Wrist volar | 1.0 / 2–3 / tendons | **Radial artery 2–5 mm**, ulnar 4–7 |
| Thigh anterior mid | 1.5–2 / 6–12 / 45–55 | Femur 55–70 mm |
| Shin anteromedial | 1.5–2 / 1–3 / — | **Tibia 3–6 mm** |
| Knee / malleoli / heel | — | Patella 4–8; malleoli 2–4; calcaneus 18–24 |

Skin thickness: eyelid 0.5–0.7, face 1.5–2.0, trunk front 1.5–2.5, **back 2.5–4.0**, limbs 1.0–2.0, palm/sole 1.5–4. Subcutaneous fat map (mm, × body fat % / 15): chest 6, abdomen 15, flank 15, back 8, buttock 20, thigh 9, arm 6, forearm 4, calf 6, shin 2, hands/feet 2. Cut-surface colours: dermis `#EAD2C8`, fat `#F2D16B`, fascia `#E8E6DF`, muscle `#9B2F2B` → `#6E2020` deoxygenated.

### 7.7 Vessels
Waypoints, diameters and flows: §3.3. Cap cross-sections at dismemberment zones must place the lumens where §3.3 says, so jets start from the right place [R06 §9.2].

### 7.8 Scaling to other generated bodies [R05 §14.3, E]
Heights, bone lengths and all coordinates × k = H/1.78; girths/breadths/depths × √(W/75)/√k, distributed mostly into subcutaneous fat (waist ×2 of the average change; hands, feet, head ×0.3); organ masses scale with BSA (W^0.425·H^0.725); vessel Ø × √k (× 0.9 female). Female bodies are a separate parameter set (pelvis, shoulders, heart ~250 g), not a scale factor.

### Simulation parameters (anatomy)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `stature / mass / bsa` | 1.78 / 75 / 1.93 | m / kg / m² | DuBois BSA | [R05 §0.3] V calc |
| `landmarks_csv` | §7.1 | m | Left side | [R05 §13.1] |
| `rig_joints` | §7.2 | m | | [R05 §2.3] |
| `segment_mass_fractions` | head+neck .081, thorax .216, abdomen .139, pelvis .142, upper arm .028, forearm .016, hand .006, thigh .100, shank .0465, foot .0145 | — | Sum 1.000 | [R05 §2.2] V |
| `vertebrae_csv` | §7.3 | m, mm | | [R05 §13.4] |
| `cord_segment_offset` | cervical +1, upper thoracic +2, lower thoracic +3; T12 → L3–S1; L1 → S2–S5 | levels | ±1 segment between sources at T10–T12 | [R05 §9.3] C |
| `brainstem_nodes_rel_head` | §7.4 | m | | [R05 §9.4] C |
| `organ_csv / tubes_csv` | §7.5 | m | Hit primitives in bone-local space | [R05 §13.2–13.3] |
| `organ_parent_bones` | heart, lungs, trachea, oesophagus → chest/upper_chest; liver, spleen, stomach, kidneys, pancreas → spine; bladder → hips | — | Organs are not rigid bodies | [R05 §15] G |
| `tissue_maps` | §7.6 | mm | Painted texture channels | [R05 §12] C |
| `scale_k` | H/1.78 | — | | [R05 §14.3] E |

### Visual/behavioural checklist (anatomy)
- In profile the ear canal, shoulder joint, greater trochanter and a point just in front of the ankle line up vertically.
- Nipples sit ~15.5 cm below the jugular notch and 20 cm apart; the navel ~20 cm below the xiphoid tip; A-pose fingertips reach mid-thigh (z ≈ 0.77).
- The spine lies in the back third of the trunk: a front-to-back torso wound meets heart, liver or aorta long before bone; in the lumbar region the aorta and IVC lie directly on the vertebral bodies.
- Lean areas (shin, sternum, back of hand, ulna border, spinous processes) show bone right under the dermis; abdomen and buttocks show 1.5–3 cm of yellow fat first.
- Chest wounds reach the pleura within 2.5–4.5 cm almost everywhere.

---

## 8. Technical architecture for Godot 4.5 (60 fps at 1080p with heavy gore)

### 8.1 Decisions [R06 §0.4, §14]

| Decision | Chosen | Rejected | Why |
|---|---|---|---|
| Wound space | **Rest space**; rest position baked into `CUSTOM0` (32-bit float) at import | World-space decals | Skinning is a compute pre-pass, so shaders see only posed vertices; decals slide on deforming skin and project through limbs (V: 4.5-stable source) |
| Surface damage | **Compute-painted UV atlases** (`Texture2DRD` on the global RenderingDevice, dispatched in `RenderingServer.call_on_render_thread()`), 3D brushes evaluated from a position map (seam-free) | `Decal` nodes on characters; SubViewport painting (prototype only) | Persistent, float data, unlimited count |
| Holes | **SDF wounds in the skin shader**: analytic cavity shading for holes ≤ 12 mm; `discard` + interior meshes for larger holes; back-face "flesh" fallback `#3A0A0C` | CSG, runtime remeshing | Left 4 Dead 2 pattern; cheap; correct shadows |
| Discard cost | **Two skin-shader variants** (with/without `discard`); switch a body surface to the discard variant only when it gets its first open wound | Branching around `discard` | The mere presence of `discard` disables the depth-prepass benefit for that shader (V: 4.5 manual) |
| Interior | Muscle shell, skeleton/skull (pre-fractured variants, 8–20 fragments), brain, cord, heart, lungs, liver, spleen, kidneys, great vessels — hidden until an open wound is within 5–10 cm | Volumetric flesh | Authored layers are the AAA norm (Dead Island 2 FLESH, Dead Space, RE2) |
| Dismemberment | Pre-split zones + authored caps (Fallout partition pattern), 12–16 zones (fingers, hand/wrist, forearm, elbow, arm, shoulder, foot, shank, knee, thigh, jaw, face, vault, neck); **realism gate: severing is rare with these weapons** | Runtime slicing everywhere | Predictable, cheap |
| Knife incisions | C++ GDExtension slicer on a worker (1–4 ms, one job in flight) only for cuts deeper than fat and longer than 8–10 cm; shallow cuts are SDF slabs | GDScript slicing (50–300 ms) | Close inspection needs real walls |
| Bleeding VFX | **Vessel graph → flow regime** (ooze / drip / stream / jet / froth), jets pressure-gated (§3.5) | Particle-only blood | Physiologically correct and budgetable |
| Stains | GPU stain particles (freeze on collision) for mist/fine spatter; **CPU "hero drops"** (≤ 200 in flight, Jolt raycasts) for stains that matter; floor stains into a **splat map** with cellular spread | GPU collision → Decal (impossible: no GPU→CPU event path) | |
| Ragdoll | `PhysicalBoneSimulator3D` + 17–19 `PhysicalBone3D` on Jolt; physiology-driven PD tone in `_integrate_forces` with torque caps | Canned death animations; Jolt native Ragdoll (not exposed) | Physical, never the same twice |
| X-ray cam (optional) | Stencil (new in 4.5): skin writes in the opaque pass; inner anatomy **reads only in the transparent pass** (`read`, `compare_equal`) | Second viewport | Built-in; one character |
| Languages | GDScript glue; **C++ GDExtension** for hit pipeline, anatomy march, vessel solve, rivulet agents, slicer | All GDScript | Hot loops are 1–2 orders faster in C++ |
| Physics engine | **Select Jolt explicitly** (Project Settings > Physics > 3D > Physics Engine); Godot Physics is still the 4.5 default | — | V: 4.5 manual |

### 8.2 Godot 4.5 constraints to respect [R06 §2, V unless noted]
- Skinning compute shader, up to 8 weights/vertex; `VERTEX` in `vertex()` is post-skin model space; no bone matrices in spatial shaders.
- Uniform buffers ≤ 65,536 B (desktop); **≤ 16 instance uniforms per shader, scalars/vectors only** (use a data texture indexed by one instance ID for more).
- Forward+ clustered elements: **512 per view** shared by omni/spot lights, decals and reflection probes (no area lights in 4.5). Cap visible decals at ~200. Remove the victim's visual layer from every world decal's `cull_mask`.
- GPU particles: collision only with `GPUParticlesCollision3D` (box, sphere, heightfield, SDF); **SDF baked in the editor only**; heightfield updates at runtime (`UPDATE_MODE_ALWAYS` if it must see the moving body); ≤ 32 colliders and ≤ 32 attractors per system; changing `amount` restarts a system — vary `amount_ratio`; no GPU→CPU event channel.
- SSS only in Forward+ (screen-space separable, 11/17/25 taps); **project default is Low (11)** — set explicitly.
- `PhysicalBone3D` joint motors are not reachable from script before 4.8 (`get_joint_rid()` merged for 4.8); 6DOF springs map to uncapped Jolt position motors in 4.5 → use script PD with caps.
- Jolt defaults: 10 velocity / 2 position steps (raise to 12–16 / 3–4 only if joints stretch), sleep 0.03 m/s for 0.5 s; contact impulses are **estimates** (drive fracture thresholds from relative velocity × mass as well); enable "Enable Ray Cast Face Index" (+~25 % memory on concave shapes).
- `Engine.time_scale` does not change `physics_ticks_per_second` (slow motion stays smooth).
- Pipeline hitches: 4.4+ compiles ubershaders at load and specialises in the background; 4.5 adds the shader baker. Still instance every gore material, particle system and inner mesh once off-screen at load; `RENDERING_INFO_PIPELINE_COMPILATIONS_DRAW` must stay 0 during a scripted gore test.
- Keep the code free of 4.6+ APIs (TwoBoneIK3D, new SSR); write a small two-bone IK SkeletonModifier3D for wound clutching.

### 8.3 Data flow and rates

```
Weapon event (ray / 9 pellet rays / blade sweep 3–5 rays per frame / hammer & fist overlap / torch cone)
  └► HIT PIPELINE (C++, main thread, ≤ 0.5 ms per shot)
       1 Jolt ray vs PhysicalBone3D shapes → bone b      2 ray → rest space via Rest(b)·Pose(b)⁻¹
       3 exact hit vs rest-pose trimesh (private physics space, face index on) → point, normal, UV
       4 march 1–2 mm through tissue maps, bone capsules, organ SDFs, vessel capsules, cord → events
  ├► WOUND STORE (≤ 64 SDF wounds, 3×vec4 each; 3D lookup grid 2.5 cm cells, 4 indices/cell, A-pose 60×16×80)
  ├► PHYSIOLOGY (worker, 20 Hz alive / 2–5 Hz dead; §3–§4)
  ├► DAMAGE PAINTER (render thread, ≤ 8 dispatches/frame, 64²–256² texel rects)
  └► VFX DIRECTOR (60 Hz, interpolates physiology) → jets, drips, rivulet agents (30 Hz, ≤ 32), hero drops, splat map
       MOTOR CONTROLLER (60 Hz PD) · EYE/SKIN UNIFORMS (eyes per frame, skin masks ≤ 1 Hz)
```

Atlases per hero character [R06 §6.1, V arithmetic]: body 2,048² (~0.8 mm texels) and head 2,048² (~0.24 mm texels — enough for stippling and 1–2 mm collars): `blood_state` RGBA16F (film thickness mm, deposit time min, dilution/serum, crust) + `tissue_state` RGBA8 (bruise, burn degree, soot/stipple, abrasion) + position/normal maps; **~126 MB per hero** (fits 6 GB). Store timestamps (sim minutes), never ages: drying needs no per-frame writes.

### 8.4 Frame budget (1080p, "heavy gore" reference scene) [R06 §13, E — profile on hardware]

Target hardware: **mid-range = RTX 3060 12 GB + 6-core CPU (Ryzen 5 3600 / i5-10400 class)**; minimum = GTX 1660 6 GB (RTX 3060 ≈ 1.57× a GTX 1660 in raster games, V). 60 fps = 16.67 ms; targets GPU ≤ 13.5 ms (1660) / ≤ 8 ms (3060), main-thread CPU ≤ 12 ms, ~3 ms headroom for gore spikes.

**Heavy gore reference scene**: one room (150–300k visible triangles, 1 directional light with 2 cascades at 2,048, 2–4 shadowed spot/omni at 1,024); hero victim 100–150k triangles with **40 wounds (8 open holes)**, muscle shell, skull, brain and 2 organs visible, **2 jets, 10 drips/streams, 24 rivulet agents**; 15k live GPU particles; 200 visible decals; a 1.5 L floor pool; 40 active debris bodies + 800 frozen MultiMesh fragments; one powered ragdoll + one sleeping ragdoll.

| GPU pass | GTX 1660 (ms) | RTX 3060 (ms) | How it stays inside |
|---|---|---|---|
| Skinning compute (≤ 300k skinned verts incl. visible inner meshes) | 0.1–0.2 | 0.05–0.1 | Inner meshes hidden until needed; hand-authored body LODs |
| Particle simulation (≤ 20k, collision) | 0.1–0.3 | 0.05–0.15 | ≤ 32 colliders; bone spheres on 4–8 bones; `amount_ratio` scaling |
| Paint + floor flow compute | 0.05–0.2 | 0.03–0.1 | ≤ 8 dispatches/frame; dirty-rect only; 256² active floor window |
| Shadow maps | 1.5–2.5 | 0.8–1.3 | Inner meshes cast no shadows |
| Depth prepass (incl. discard variant) | 0.6–1.0 | 0.3–0.5 | Discard variant only on surfaces with open wounds |
| SSAO | 0.5–0.8 | 0.3–0.5 | Half-res on 1660 |
| Opaque (clustered lights, ≤ 200 decals, skin + wound shader) | 3.0–4.5 | 1.5–2.5 | ≤ 4 SDF evals per fragment via the grid (~0.1–0.2 ms at 40 % screen); decals cost by coverage; floor stains in the splat map |
| SSS | 0.3–0.6 | 0.2–0.4 | 17 taps (1660) / 25 (3060) |
| Sky, fog | 0.1–0.3 | 0.05–0.15 | Volumetric fog off/low |
| Transparent (mist, jet ribbons, optional X-ray) | 0.5–1.5 | 0.3–0.8 | **Main risk**: mist overdraw — unshaded mist, ≤ 15–20 % of the screen, ≤ 4 layers; droplets opaque alpha-scissor |
| Post (tonemap, glow, SMAA/TAA) | 0.6–1.0 | 0.3–0.6 | SMAA (4.5); check TAA ghosting on spatter |
| UI | ~0.1 | ~0.05 | |
| **Total** | **7.5–13.0** | **4.7–8.3** (1660 × 1/1.57) | Profile first; SSR/SSIL may not fit the 3060 worst case |

| CPU work (main thread unless noted) | ms | How it stays inside |
|---|---|---|
| Jolt (2 ragdolls, 48 debris, arena), 60 Hz | 0.3–1.0 | Remove finger bodies; debris sleeps → MultiMesh (2 m chunks); optional physics thread (experimental) |
| Physiology + vessel graph, 20 Hz (worker) | < 0.1 per tick | ~150 unknowns, closed-form shunt solve |
| Hit pipeline | 0.1–0.5 per shot (C++) | Shotgun: 9 pellet rays, merged spatter emitters; co-located pellet tracks at ≤ 1 m merged into one wound |
| Rivulet agents (worker, 30 Hz) | 0.05–0.2 | ≤ 32 per character |
| Hero drops | 0.1–0.3 | ≤ 200 in flight; 30–60 per spatter event |
| Animation + skeleton modifiers | 0.2–0.6 | |
| Game logic (GDScript) | 1–3 | No per-tick allocation |
| Render CPU (culling, 1,000–2,000 draws) | 2–4 | Modular body surfaces only where needed |
| **Total** | **~4–10** | Target ≤ 12 |

**Caps** [R06 §8.5, §0.4]: ≤ 20k live GPU particles (1660; 40k on 3060) — spatter pool 8 × 1,024 via `amount_ratio`, mist sprites ≤ 64, stain particles ≤ 8,000, jet breakup 6 × 256, debris chips ≤ 1,000; **≤ 6 jets, ≤ 20 drips/streams**, ≤ 32 rivulet agents per character, ≤ 200 visible decals (pool 128–256, preloaded 32–64 textures), ≤ 48 active debris bodies, ≤ 2,000 frozen instances, ≤ 64 SDF wounds per character (oldest closed wounds retire into the paint atlas). **The physiology always accounts for every wound's volume, even when its VFX is culled.**

**Scalability governor** (GPU time > 14 ms over 0.5 s → degrade in order; restore when < 11 ms for 3 s) [R06 §13.7, G]: 1 mist count/size → 2 spatter `amount_ratio` down to 50 % → 3 stain-particle lifetime (bake old stains into the splat map) → 4 decal fade distance 25 → 12 m → 5 SSS taps 25 → 17 → 11 → 6 SSAO half-res → 7 FSR 2.2 at 0.77. **Never degrade wounds, physiology, or stains on the victim.**

**Pass criterion**: scripted 60 s heavy-scene run with shots — **1 % low ≥ 55 fps on the GTX 1660; average ≥ 60 fps and 1 % low ≥ 58 fps on the RTX 3060** [R06 §13.6, G]; zero draw-time pipeline compilations.

### 8.5 Phased plan [R06 §14.1]
1. **Head** (current): rest-space pipeline, head atlas, skull/brain inner meshes with pre-fractured skull, fixes from §2.7, range-of-fire looks, spatter, rivulets, floor pool.
2. **Full body**: body atlas and muscle shell, vessel graph + VFX regimes, heart/lung meshes, physiology state machine (§3–4), eyes (§5), ragdoll tone map, wound clutching.
3. **Post-mortem and dismemberment**: §6 clocks, hand/finger/jaw/face zones, debris freezing, knife slicer.
4. **Performance**: governor, 1660 pass, optional move to 4.6+ (IK nodes, SSR).

### Simulation parameters (tech)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `godot_version / physics` | 4.5.x (4.5.2) / Jolt selected explicitly | — | | [R06 §2.1] V |
| `gpu_budget_1660 / 3060` | ≤ 13.5 / ≤ 8 | ms | 1080p | [R06 §13] G |
| `cpu_main_budget` | ≤ 12 | ms | | [R06 §13] G |
| `hit_pipeline_budget` | ≤ 0.5 | ms/shot | C++ | [R06 §3] E |
| `sdf_wounds_max / wound_grid` | 64 / 60×16×80 cells at 2.5 cm (A-pose bind) | — | ~0.3 MB | [R06 §4.4] V calc |
| `atlas_body / head` | 2,048² (4,096² ≥ 8 GB VRAM) / 2,048² | texels | 0.81 / 0.24 mm | [R06 §4.1] V calc |
| `cavity_max_radius` | 6 (holes ≤ 12 mm) | mm | Above: discard + interior | [R06 §5] G |
| `layer_reveal_radius` | 5–10 | cm | Show inner meshes | [R06 §5.3] G |
| `live_particles_max` | 20k (1660) / 40k (3060) | — | | [R06 §8.5] E |
| `jets_max / drips_max / agents_max` | 6 / 20 / 32 | — | | [R03 §12], [R06] G |
| `decals_visible_max` | 200 (cluster limit 512) | — | | [R06 §2.5] V/G |
| `debris_active_max / frozen_max` | 48 / 2,000 | — | | [R06 §9.5] G |
| `mist_screen_coverage_max` | 15–20 %, ≤ 4 layers, unshaded | — | | [R06 §13.3] E |
| `sss_taps` | 17 (1660) / 25 (3060) | — | Default is 11: set it | [R06 §2.8] V |
| `governor_high / low` | 14 / 11 | ms | Hysteresis | [R06 §13.7] G |
| `pass_criterion` | 1 % low ≥ 55 fps (1660) | — | Heavy scene | [R06 §13.6] G |

### Visual/behavioural checklist (tech)
- Wounds stay exactly where they were made in any pose; nothing slides when an elbow or knee flexes through its full range; nothing projects through a limb.
- The first blood, first open hole and first inner mesh of a session cause no hitch.
- A point-blank shotgun volley keeps frame pacing smooth; when the governor acts only mist density and distant stains change — the victim looks identical.
- Large holes show real depth (muscle, then bone) and cast correct shadows; a hole never shows an empty body shell.

---

## 9. Realism checklist (acceptance tests)

Each statement is testable in-game (debug overlay showing wound sizes, physiology values and sim time). "sim" = simulated time. Tolerances are the stated ranges; over ≥ 20 repetitions the distribution must fall inside them.

| # | Statement | Test | Source |
|---|---|---|---|
| 1 | A 9 mm FMJ distant entrance in trunk skin is a round hole **3.3–5.6 mm** (mean ~4.5) with a **1.6–2.4 mm** red-brown abrasion collar; never ≥ 10 mm | Shoot the chest at 3 m, measure | [R01 §2] C |
| 2 | A 9 mm entrance in the scalp is **6.3–9.0 mm** with a concentric collar at 90° incidence | Head shot at 3 m, perpendicular | [R01 §2] C |
| 3 | At 45° incidence the entrance is an ellipse (major/minor ≈ 1.4) and the collar is widest on the side facing the shooter | Angled shot | [R01 §2.2] C/E |
| 4 | Exits never show soot, stippling, searing or an abrasion collar (except a shored exit against a surface) | Inspect 20 exits | [R01 §4] C |
| 5 | At 5–10 cm muzzle distance a dense black soot zone (~2.3–3.5 cm Ø) surrounds the entrance and wipes off; red-brown stippling (0.2–1.5 mm dots) does not wipe off | Shoot at 5/10 cm, apply wipe | [R01 §3] C |
| 6 | Stippling appears up to 60 cm (flake) / 90 cm (ball powder) and is absent at 150 cm; at 30 cm its pattern is 5.7–17.7 cm across | Shoot at 30/60/90/150 cm | [R01 §3] C |
| 7 | A contact 9 mm shot to the scalp over bone gives a stellate tear (3–6 rays, 5–20 mm) with a blackened seared rim, soot in the wound and a muzzle imprint; the entrance may exceed the exit | Contact head shot | [R01 §3.5] C |
| 8 | 9 mm FMJ head exits are 10–30 mm with everted edges; over ≥ 100 exits ~25 % circular, ~33 % stellate, ~30 % irregular, ~9 % slit, ~3 % crescent | Batch test | [R01 §4] C |
| 9 | The skull entrance has a 9.0–10.8 mm outer-table hole and a 1.3–2.0× larger inner cone; the exit is bevelled outward; a handgun never bursts the vault | Peel scalp in debug view | [R01 §5], [R2-05 §2] C/E |
| 10 | A handgun head wound shows 0–4 radial fractures ≤ 80 mm; later fractures stop at earlier ones in ≥ 90 % of cases | Two shots, inspect skull | [R01 §5.4] C |
| 11 | Back-spatter from a head shot is 30–320 visible drops, mostly within 0.5 m on the shooter side (max ~1.2 m); forward spatter is 2–5× denser in a ~27° cone | Scripted shot at a wall-backed head | [R01 §7] C |
| 12 | No shot moves the body backward by more than 0.2 m/s (9 mm ≤ 0.04 m/s; buckshot ≤ 0.17 m/s) | Measure pelvis velocity | [R01 §1] V |
| 13 | 12 ga: a single hole ~2–2.5 cm at ≤ 0.3 m, 3–4 cm at 1 m, scalloped at 1–2 m, central hole + satellites at 2–4 m, separate pellet holes beyond 4–5 m; the wad is in the wound at ≤ 1.5 m | Range series on the torso | [R01 §9] C |
| 14 | A contact shotgun shot to the head bursts the vault (far-side crater, radial scalp flaps, brain partly ejected down-range) and the heart keeps pumping blood from the defect for 1–10 min | Contact shot | [R2-05 §2] C/E |
| 15 | A 40 mm knife cut across the skin tension lines gapes 6–10 mm within 1 s; the same cut along them gapes 1–2 mm; edges are straight, unabraded, without tissue bridges, and the stroke end tapers into a 5–30 mm tail | Two cuts on the forehead | [R02 §2] C/E |
| 16 | A single-edged stab is a slit with one sharp and one square/fish-tailed end, length = blade width − 0–2 mm; the knife never cuts through the skull or a long bone | Stab tests | [R02 §2.5] C |
| 17 | A hammer blow lacerates only over bone, with ragged, abraded, bruised margins and tissue bridges; a committed blow (≥ 23 J frontal, ≥ 15 J temporal on average) leaves a depressed defect matching the 25–32 mm face, wider and irregular on the inner table | Blows at increasing energy | [R02 §3.4, §5] C/E |
| 18 | A bruise never shows yellow before 18 h (sim); a fist bruise becomes visible within 15–60 min; a deep bruise may surface only after 12–48 h and lower than the impact | Time-lapse | [R02 §3.2] V/C |
| 19 | A bare punch can break the nose (≥ 111–334 N) but never fractures the frontal bone; ~66 % of knockouts show a fencing posture lasting 2–10 s | Punch batch | [R02 §4.1], [R04 §3.6] C |
| 20 | Torch at close range: grey-white epidermis within ~0.3–0.8 s, leathery tan at 1.5–4 s, char at 3–8 s; blisters appear 30 s–5 min later only on partial-thickness areas; burned tissue does not bleed and full-thickness areas cause no pain reaction | Torch dwell series | [R02 §6] E/V |
| 21 | An exposed, transected carotid spurts bright red in time with the heartbeat (pulses lag the heartbeat by ~0.1 s), initial jet 0.55–1.0 m high at 120/80 supine; LOC at 20–90 s; arrest at 2–5 min untreated | Neck cut, overlay | [R03 §5, §6] C/E |
| 22 | As shock deepens the jet pulses get faster and weaker; below MAP ~25–30 mmHg there is no jet, only welling; it stops within 1–2 beats of cardiac arrest | Observe a femoral bleed-out | [R03 §6.2] C |
| 23 | Venous bleeding is dark maroon and non-pulsatile, surges when the victim screams, and nearly stops when the limb is raised above the heart | Cut a forearm vein, raise the arm | [R03 §6] C |
| 24 | A single clean radial-artery cut bleeds 100–300 mL/min at first, falls to 20–60 mL/min after spasm and stops within 5–20 min after 200–500 mL; the victim survives | Scenario A | [R03 §5.1] E |
| 25 | A common femoral transection in a standing victim causes collapse at ~2 min and arrest at 4–8 min; a 1 L floor pool is ~70 cm across and ~2.5 mm thick and stops spreading after 5–15 min | Scenario C | [R03 §5.1, §10.3] V/E |
| 26 | A 5–10 cm scalp laceration keeps bleeding (5–30 mL/min, more with a cut STA) long after small cuts elsewhere have clotted, soaking and dripping from the hair | Hammer/knife to the scalp | [R02 §2.6], [R03 §7.3] C |
| 27 | A small trunk bullet wound drips little externally while the victim becomes pale, tachypnoeic and confused from internal bleeding | Liver/spleen shot | [R03 §4.5] C |
| 28 | Shock signs follow blood loss: HR < 100 below 15 % loss, 100–120 at 15–30 %, systolic BP falls only after ~30 %, yet ≈ 40 % of hypotensive victims keep HR < 100 (relative bradycardia); supine LOC at ~45 %; arrest at 45–55 % | Overlay during a slow bleed | [R03 §3] V/C |
| 29 | An exsanguinated victim is waxy white-grey with grey-lilac lips, never blue, and shows faint or no livor after death | Bleed-out to death | [R04 §7.7, §12.4] C |
| 30 | A heart stab with an intact pericardium produces few mL of external blood, distended neck veins, a dusky face and falling BP over 5–30 min, then PEA | Stab the RV | [R03 §8.2] V/C |
| 31 | A lung hit produces bright frothy pink-red blood at the mouth within 5–60 s; a chest-wall hole > 10–13 mm sucks on inspiration and bubbles froth on expiration | Chest shots | [R04 §9] C |
| 32 | A medulla/pons hit collapses the body in 0.6–1.2 s with no protective arm reaction; after a medullary hit there is no breathing movement and no gasping; the heart continues ~100 bpm and arrests at 4–10 min | Brainstem shot | [R04 §2] C |
| 33 | After destruction of the heart the character can act for 10–15 s, loses consciousness at 8–15 s with eyes open and briefly rolled up 10–30° and (p ~0.9) irregular jerks | Heart destroyed | [R04 §8] C |
| 34 | A low-energy unilateral frontal track leaves the character conscious 10 s later in 10–30 % of trials | Batch | [R04 §3] G |
| 35 | A motor-strip/internal-capsule track gives contralateral flaccid hemiplegia with eyes and head deviated 15–40° toward the wounded side; the character falls toward the paralysed side | Targeted shot | [R04 §3.3] C |
| 36 | A complete C1–C3 lesion gives instant flaccid quadriplegia and apnoea with the character awake (eyes darting, mouth moving without airflow) until LOC at 90–180 s; arrest at 4–10 min | Neck shot through the canal | [R04 §6] C |
| 37 | A complete T8 lesion: legs fold, arms break the fall, the character drags itself; cutting or burning the legs produces no flinch at all | Back shot | [R04 §6.6] C |
| 38 | A knife hemisection (Brown-Séquard) paralyses the leg on the stabbed side while the other leg moves but ignores the torch | Stab beside the spine | [R04 §6.3] C |
| 39 | A temporal hammer blow can produce a lucid interval (20–50 %), then a unilateral pupil 6–9 mm, contralateral weakness, Cushing's triad (SBP 160–220, HR 40–60) and apnoea; death 1–6 h real (8–12 min of play) | EDH scenario | [R04 §5.4] C/G |
| 40 | Agonal gasps occur in 30–50 % of arrests with an intact medulla: 2–10/min, with neck extension and jaw opening, stopping within 1–5 min; no terminal-secretion bubbling in any death faster than hours | Observe 20 deaths | [R04 §10], [R2-04 §14] C |
| 41 | A living alert character blinks 12–20 times/min (250–400 ms each), makes saccades of duration ≈ 21 + 2.2 ms/°, and pupils (3–4 mm) constrict within 0.2–0.25 s of a light | Eye debug | [R04 §11], [R2-06] C |
| 42 | Eyes stay open or half-open after death (sudden death: open ~55 %, half-open ~35 %, closed ~10 %); the lids drop 2–4 mm over 1–3 s and never blink shut; gaze settles 3–10° outward with no further movement | Observe 20 sudden deaths | [R04 §11.3] G |
| 43 | Dead pupils are 6–8 mm and fixed by 2 min after arrest, relax to 4–6 mm (anisocoria ≤ 1 mm) over 2–6 h, and are never pinpoint unless the pons was destroyed | Pupil overlay | [R04 §11.5] C |
| 44 | Turning a dead head moves the eyes rigidly with it; turning an unconscious living head (brainstem intact) makes the eyes counter-rotate | Head-turn test | [R04 §11.4] C |
| 45 | Open dead eyes lose their gloss within ~1 h, haze from 1–2 h (obvious at 3–6 h), show brown-black tache noire at 3–6 h; closed eyes cloud only from ~12 h | Forensic fast-forward | [R04 §11.6] C |
| 46 | The jaw drops 10–30 mm within 30 s of death in a supine body; the face relaxes (no frozen expression); the body is flaccid until rigor | Death observation | [R04 §12.1] C |
| 47 | Livor: first patches at ~0.75 h (0.25–3), confluent ~2.5 h, maximal ~9.5 h; blanches fully under pressure until ~5.5 h; shifts completely if the body is turned before ~3.75 h; pressure points stay pale | Fast-forward + turning | [R04 §12.4] C |
| 48 | Rigor starts in the jaw/eyelids at ~3 h, is complete at ~8 h, in the order jaw → neck → arms → trunk → legs; a forced joint gives way and stays loose | Fast-forward | [R04 §12.6] C |
| 49 | Rectal temperature of the reference body (75 kg, naked, 20 °C) reads ~34.4 °C at 6 h and ~25.4 °C at 24 h after arrest | Forensic readout | [R04 §12.5] V |
| 50 | The heavy-gore reference scene holds 1 % low ≥ 55 fps on a GTX 1660 and ≥ 60 fps average on an RTX 3060 at 1080p, with zero draw-time pipeline compilations | Automated perf run | [R06 §13] G |

---

## 10. Open issues, verification queue, suspicious content, sources

### 10.1 QA re-check list (open the primary source before exposing as a measured value)
1. Entrance hole sizes and collar ratios (Geisenberger 2022 [PMID 36006518](https://pubmed.ncbi.nlm.nih.gov/36006518/); contusion-ring study [PMID 1811497](https://pubmed.ncbi.nlm.nih.gov/1811497/)).
2. Stippling ranges and pattern sizes (DiMaio 1976; Dana & DiMaio 2003; ETSU thesis) and ball-powder 90 vs 120 cm.
3. Brain destruction zone "3.6 cm" diameter vs radius (Oehmichen 2000/2004, [PMID 15542271](https://pubmed.ncbi.nlm.nih.gov/15542271/)); this bible uses radius 18 mm.
4. Back/forward spatter (Karger [PMID 8912050](https://pubmed.ncbi.nlm.nih.gov/8912050/); Comiskey/Attinger — foam targets, not heads).
5. Per-vessel bleed-out times (§3.3) — tuning targets; no per-vessel human series exists in the reviewed sources.
6. LOC/PEA loss thresholds (ATLS > 50 % vs Guyton 40–45 %) and Rossen 1943 (LOC 5–10 s).
7. Lid position at death — no prevalence study exists; distribution is a game choice.
8. Mallach livor/rigor tables (Henssge & Madea 2004) and Henssge 1988 constants (recall-consistent only).
9. Fist/hammer force and skull fracture energies (temporal 5–15 J source; 2025 blow-energy study).
10. Heat-flux/porcine burn depth values (Stoll curve verified; porcine 600 °C depths unverified).
11. Skull/bone cortex thicknesses and vertebral positions in C4–T3 (cervicale conflict).
12. Every timing in the drying/colour ramps (chemistry verified; times estimated).

### 10.2 Conflicts resolved in this bible
| Topic | Documents | Resolution |
|---|---|---|
| BV0 | R03 5.0 L, R04 5.25 L | Nadler per body (5.09 L reference); thresholds as fractions |
| Bradycardia in haemorrhage | R03 0.35–0.45 (corrected, trauma series), R04 0.10–0.30 | Split into `relative_brady_p` 0.40 (trait) and `sudden_faint_p` 0.20 (event) |
| Transcapillary refill | R03 250–500 mL first hour (Marino, V), R04 50–150 mL/h | R03 value |
| Scalp laceration rate | R02 20–100, R03 5–30 (50–100 with a named artery) | 5–30 base + 20–60 per named artery |
| Lung parenchyma rate | R03 5–50, R04 20–100 | Peripheral 5–50; handgun through-track 20–100 |
| Buckshot pellet holes | R01 4–7 mm, R2-05 6–9 mm | Region factor × 8.4 mm (trunk 3.4–5.2, scalp 5.9–8.4) |
| Temporal fracture energy | R02 5–15 J (clamped ≥ 10), R2-05 50 % at 10 J | 50 % at 15 J (range 10–15) |
| Ragdoll gains | R06 f 4–6 Hz, R2-03 ω 10–12 rad/s with ω·Δt ≤ 0.5 | R2-03 values (stability-checked) |
| Segment masses | Dempster/Winter vs de Leva | Dempster default (verified), de Leva optional |
| Head origin height | R05 1.655 → corrected 1.647; contract head vertex 0.125 m | Origin at 1.647; do not rescale the head |
| Arterial jet gate | R06 flow > 300 mL/min | Pressure gate (P_local ≥ 25–30 mmHg), flow sets thickness only |

### 10.3 Suspicious content
- **None encountered in this synthesis pass.** The only material read was the project's own research documents (`docs/research/`, `docs/research2/`), `blender/gore_head/CONTRACT.md`, `gore.py`, `build.py`, `materials.py` and the head renders; all were treated as data, and none contained instructions directed at the reader.
- One WebSearch was refused (session budget 200/200 exhausted) and one WebFetch to pubmed.ncbi.nlm.nih.gov returned `EGRESS_BLOCKED`; no external content was received. No shell commands were run, nothing was downloaded, installed or executed, and no code was copied from the web.
- The research documents' own suspicious-content sections report no prompt-injection attempts in any search result or fetched page (R01 §14, R02 §10, R03 §14, R04 §17, R05 §17, R06 §17, R2-02 §16, R2-05 §19).

### 10.4 Sources
- Project research: [R01](research/01_gunshot_wounds.md) · [R02](research/02_sharp_blunt_burn.md) · [R03](research/03_bleeding_vessels.md) · [R04](research/04_neuro_death_eyes.md) · [R05](research/05_body_anatomy_reference.md) · [R06](research/06_game_gore_tech.md) · [R2-01](research2/01_brain_injury_deficits.md) · [R2-02](research2/02_reactions_to_being_shot_and_hit.md) · [R2-03](research2/03_falling_ragdoll_biomechanics.md) · [R2-04](research2/04_agonal_involuntary_movement.md) · [R2-05](research2/05_severe_trauma_morphology.md) · [R2-06](research2/06_sounds_voice_face.md). Each contains its full reference list with URLs and verification status.
- Current head: [`blender/gore_head/CONTRACT.md`](../../blender/gore_head/CONTRACT.md), [`gore.py`](../../blender/gore_head/gore.py), renders in `blender/gore_head/renders/`.
- Key primary sources cited through the research docs (not re-opened in this pass): ATLS 9th/10th ed. (shock classes); Marino, *The ICU Book* (blood volume, refill, air embolism — read via text copy in R03); Nadler 1962 (blood volume); HuBMAP HRA-VCCF vessel table (diameters, read in R03); Prahl 1999 haemoglobin extinction (read in R03); ANSUR II raw data (read in R05); Dempster/Winter segment table (read in R05/R06); Godot 4.5-stable engine source and manual (read in R06); Plum & Posner (coma, eyes); Henssge & Madea 2004 (livor, rigor); Henssge 1988 (cooling); Lempert 1994 (syncope); Rossen 1943 (cerebral arrest); Wijdicks 2010 / Greer 2023 (brain death); DiMaio *Gunshot Wounds*; Saukko & Knight *Knight's Forensic Pathology*; Karger (incapacitation, spatter); Oehmichen (brain cavitation); Stoll & Chianta (burn criterion); Moritz & Henriques (scald times).

