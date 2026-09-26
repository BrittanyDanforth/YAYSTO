# Gore Head — Realism Bible (implementation reference)

Project: **Gore Head** — Godot 4.5 (Forward+, GDScript + Godot shaders, Jolt), procedural assets from Blender. The subject is a fictional, procedurally generated adult. No real person is modelled.
Audience: simulation, physiology, VFX, shader, animation, audio and performance engineers.
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

**What it never affects** (always real time): Jolt physics, ragdoll and debris, particles and jets' ballistic motion, audio, and every **cosmetic oscillator** — the heartbeat phase that pulses jets, breathing motion, blinking, saccades, gasps. The heart visibly beats at the *current simulated HR in beats per real second*. At 4× the pool therefore grows faster than the jet suggests; this mismatch is accepted [G].

**Time bands** [R04 §0.3, G]:

| Band | Real phase it covers | Scale (default) | Why |
|---|---|---|---|
| ACUTE | First 60 s after any critical event (hit, collapse, arrest, seizure) and the last 60 s before predicted arrest | **1×** (fixed) | Collapse, eyes and last breaths are the drama; never compress |
| MINUTES | Predicted time to arrest ≤ 30 min sim | **4×** (3–6×) — the default **bleed-out multiplier** | Keeps stage order, removes dead air |
| LONG | Predicted time to arrest 30 min – 6 h sim (slow bleed, epidural haematoma, tamponade) | **15×** (10–30×) | Stages readable in 5–15 min of play |
| POSTMORTEM | After circulatory arrest + 60 s | **120×** (1 h = 30 s); player fast-forward **720×** (1 h = 5 s) | Forensic time-lapse |

**Band selector** (evaluated at 1 Hz) [G]:
```
t_pred = (V - V_pea) / max(Q_loss_total - Q_refill, 1e-3)     # sim seconds to PEA by volume
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
- Cut trachea below the vocal cords → **aphonia**, bubbling and aspiration-cough spray from the wound [R2-06 §17, R2-05 §18].
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
- Blood wells along the whole length within 1–3 s, beads, then runs downhill; cut arteries spurt in time with the pulse; neck veins pour dark blood and may hiss, gurgle and froth on inspiration.
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
- A broken nose bleeds at once from both nostrils, deviates and crunches on the next hit; swelling hides the deformity within an hour.
- A knockout drops the character instantly; two in three show one arm stiffly extended and the other flexed for a few seconds, then slack, snoring breaths.
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
- Sounds: dull thud on scalp, sharp crack at first fracture, wet crunching on later blows.

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

| Exposure | Tissue | Look | Sound / smell |
|---|---|---|---|
| 0–0.1 s | Hair burns (~233 °C) | Hairs curl, bead into black knobs, white wisps | Faint crackle; sulfurous burnt hair |
| 0.1–0.3 s | Erythema | Red flush around the spot | — |
| 0.3–0.8 s | 2nd degree | Epidermis matte grey-white, wrinkles, lifts | Soft hiss (steam) |
| 0.8–1.5 s | Deep partial → full | Waxy white centre, pale tan, red hyperaemic ring | Hiss, faint sizzle |
| 1.5–4 s | Full thickness | Tan-brown leathery eschar `#9B6B43`; skin tightens and puckers | Sizzle; seared meat |
| 3–8 s | Char | Black `#1A1614`, fine cracks, curled edges, greasy yellow-grey smoke | Crackling, popping |
| 8–20 s | 4th degree | Fat melts, bubbles, small yellow flames; heat fissures along muscle grain (1–5 mm × 1–10 cm, bloodless) | Fat spitting; pork-fat smell |
| > 20 s | Muscle cooked `#5A2A1E` → black; bone on thin sites | Bone ivory → brown (~300 °C) → black (~400 °C) → blue-grey (525–645 °C) → white calcined (> 650 °C) | Bone crackle |

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
- **Pulse delay** after the ECG R-wave / heart-sound "lub" (S1 at 20–60 ms): pre-ejection 60–100 ms + path/PWV (aorta 6 m/s, peripheral 9 m/s): carotid 90–140 ms, femoral 150–220 ms, radial 170–250 ms, dorsalis pedis 220–300 ms [R03 §2.4, E].
- **Breakup**: the column breaks into drops ~1.9 × jet Ø (typically 4–6 mm, 35–110 µL) within 5–20 cm; pulsing bunches drops into one cluster per beat; stains on walls form a zig-zag, one peak per beat [R03 §6.2].
- As shock deepens the pulses get **faster and weaker at the same time** — the most readable bleed-out cue.

### 3.6 Venous flow and air embolism

- **Look**: dark maroon `#8E1420`, steady, non-pulsatile dome over the wound: height 12.8 cm per 10 mmHg × 0.25–0.5 (3–6 cm at 10 mmHg) [R03 §6.1, E].
- **Posture**: + 0.78 mmHg per cm below the right atrium. Limb venous bleeding increases strongly when the limb hangs and nearly stops when raised above the heart; arterial jets barely change (−8 mmHg per 10 cm).
- **Neck veins**: pulse with respiration (inspiration lowers pressure; upright neck veins ≤ 0 mmHg and collapse); **expiration, coughing, screaming, straining (+20–40 mmHg Valsalva) cause dark surges** [R03 §4.7, C].
- **Air embolism** [R03 §5, V; R02 §2.4, C/G]: condition = an open tethered vein (IJV root, subclavian, dural sinus with open skull) ≥ ~5 cm above the right atrium with P_local < 0. Roll `air_path_open` p = 0.15 per qualifying wound (fits ~10–15 % of fatal throat cuts). If open: entrainment **20–100 mL/s during inspiration** (≥ 100 mL/s possible through a large tear); lethal when **3–5 mL/kg (200–300 mL) enters within seconds** → sudden collapse (CO → 0 "air lock"), gasp, frothy blood, audible hiss/gurgle/sucking at the wound.

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
- An exposed cut artery spurts bright scarlet in time with the pulse, a fraction of a second after the heartbeat sound; the jet never fully stops between beats while BP is normal, gets faster and lower as shock deepens, becomes a pulsing well below MAP ~25–30 and stops within a beat or two of cardiac arrest.
- Venous bleeding is dark maroon, domed and steady, surging when the victim screams or strains; raising a bleeding limb above the heart nearly stops venous bleeding but not an arterial jet.
- Small trunk bullet wounds barely bleed outside while the victim goes pale, breathes faster and becomes confused (internal bleeding).
- Scalp wounds keep bleeding long after small cuts elsewhere have clotted; hair mats and drips from the tips.
- A floor pool spreads as a 2.5 mm sheet (1 L ≈ 70 cm across), stops spreading after ~10 min, later shows a yellow serum rim and darkens from the edges.
- Late in shock all wounds bleed darker and more purple.

<!-- CONTINUE-4 -->
