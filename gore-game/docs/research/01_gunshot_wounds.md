# 01 — Gunshot Wound Morphology and Wound Ballistics (with emphasis on the head)

Project: Gore Head (Godot 4.5, Forward+, Jolt). Audience: simulation, VFX, decal, audio and animation engineers.
Status: research reference v1. Clinical/forensic tone. Fictional procedurally generated adult only.

---

## 0. How to read this document

### 0.1 Evidence tags

Every non-obvious number carries a tag:

| Tag | Meaning |
|---|---|
| **[S#]** | Taken from a published source listed in Section 13 (peer-reviewed paper, textbook-derived review, StatPearls, forensic teaching site). |
| **[S#, derived]** | Computed by me from a sourced number (the arithmetic is shown). |
| **[K]** | My own domain knowledge (standard forensic pathology / wound ballistics teaching, e.g. DiMaio *Gunshot Wounds*, Fackler, Kneubuehl, Saukko & Knight). I could not verify it with a source during this session. Treat as a reasonable default, not as a measured value. |
| **[G]** | Game-design choice: a value picked for gameplay/readability within (or slightly beyond) the real range, with the reason given. |

### 0.2 Research method and limitations (important)

- All `WebFetch` calls failed. The network egress proxy blocked every domain tried (pmc.ncbi.nlm.nih.gov, ncbi.nlm.nih.gov, pubmed, librepathology.org, medscape, pathologyoutlines, wikipedia, springer, pennds.org). All sourced numbers below therefore come from **search-engine result summaries of the cited pages** (abstracts, snippets), not from reading the full texts. Numbers that look like abstract-level results (sample sizes, means ± SD) are reliable. Anything more detailed was not available to me, so I tagged it **[K]**.
- The session's web-search budget (200 calls) ran out during the research. Some details I had planned to verify, such as exact abrasion collar widths in mm from a primary textbook and exact Fackler wound-profile numbers, are therefore **[K]**.
- Before this data drives anything the player can measure, e.g. a "forensic inspection" mode that shows wound sizes, a human should re-check the load-bearing numbers (Section 12) against the full papers.

### 0.3 Coordinate and unit conventions used in the tables

- Distances: muzzle-to-skin distance `d_muzzle` in cm. Shotgun ranges in m.
- Angles: `θ_inc` = angle between the bullet path and the **skin surface**. 90° = perpendicular, 0° = grazing.
- Sizes are diameters unless stated. Colours are sRGB hex approximations under neutral daylight (D65). Engineers should tune them under the game's own lighting.

---

## 1. Ammunition reference data (inputs to every other section)

| Round (game key) | Bullet Ø (mm) | Bullet mass (g) | Muzzle velocity (m/s) | Muzzle energy (J) | Construction notes | Source |
|---|---|---|---|---|---|---|
| `.22LR` 40 gr solid | 5.7 | 2.6 | 330–370 | 140–178 | Unjacketed lead, round nose; deforms; ricochets easily | [S44] for 370 m/s / 178 J; rest [K] |
| `9mm` 115–124 gr FMJ | 9.0 | 7.5–8.0 | 350–380 | 470–570 | Round-nose FMJ, non-expanding | [K] |
| `9mm_JHP` 124 gr | 9.0 → ~13–17 expanded | 8.0 | 350–370 | ~500 | Expands to ~1.5–1.9× Ø | [K] |
| `.45ACP` 230 gr FMJ | 11.5 | 14.9 | 250–260 | 470–500 | Round-nose FMJ | [K] |
| `.45ACP_JHP` 230 gr | 11.5 → ~17–19 expanded | 14.9 | 260–270 | ~520 | Gel-tested expansion ~0.67–0.75 in (17–19 mm) | [S48] (low-quality source), [K] |
| `5.56_M193` 55 gr | 5.7 | 3.6 | ~990 (20 in barrel) | ~1,750 | FMJ spitzer. Yaws then fragments at the cannelure | [K] |
| `5.56_M855` 62 gr | 5.7 | 4.0 | ~940 | ~1,770 | FMJ with steel penetrator. Fragments less than M193 | [K] |
| `7.62x39` 123 gr | 7.9 | 8.0 | ~715 | ~2,000 | FMJ, steel core. Travels ~26 cm point-forward in tissue before yawing | [S41] for 26 cm, rest [K] |
| `7.62x51_M80` 147 gr | 7.8 | 9.5 | ~840 | ~3,350 | FMJ | [K] |
| `12ga_00buck` | 9 × 8.4 mm pellets | 9 × 3.5 = ~31.5 | ~400 | ~2,500 total (~280 per pellet) | Lead balls, often in plastic shot cup | pellet count and Ø [S39], rest [K] |
| `12ga_bird_7.5` | ~350 × 2.4 mm pellets | ~32 total | ~365 | ~2,100 total (~6 per pellet) | Behaves as one mass at close range | pellet count [S39], rest [K] |

Definitions: high-velocity projectile (HVP) means muzzle velocity > 600 m/s fired from assault rifles [S10]. Handguns and "low-velocity" rifles in the forensic head-wound literature have muzzle energy E₀ < 550 J [S25].

**Momentum sanity check.** Even large rifles and a 12-gauge shotgun give an 80 kg body only **0.01–0.18 m/s** of backward velocity. That is negligible compared with walking speed (1–2 m/s), and balance reflexes cancel it [S30]. **Bodies must not be thrown backwards by bullets.**

### Simulation parameters (ammunition)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `bullet_diameter` | see table | mm | Base for every wound-size formula | [K] |
| `impact_velocity` | muzzle v minus ~0–3 % per 10 m (handgun) | m/s | Range drop is negligible at game distances (< 25 m) | [K] |
| `E_threshold_highvel` | 600 | m/s | Above this, switch to "rifle" wound recipes (large temporary cavity, bursting fractures) | [S10] |
| `E_lowvel_head_max` | 550 | J | Head-wound data from the forensic literature (handgun) applies below this | [S25] |
| `body_knockback_velocity` | 0.01–0.18 | m/s | Apply as a tiny impulse only. Falls are neuromuscular (collapse), not ballistic | [S30] |
| `jhp_expansion_factor` | 1.5–1.9 | × Ø | Apply after 1–3 cm tissue depth. The entrance looks like FMJ | [K] |
| `m193_yaw_depth` | ~12 (fragmentation onset ~12–15) | cm | Head width is ~14–16 cm, so M193 often yaws and fragments inside the head | [K] |
| `7.62x39_yaw_depth` | ~26 (full 90° at ~30) | cm | Through the head the track is narrow unless bone deflects it | [S41] |

### Visual/behavioural checklist (ammunition)
- The shot does not push the body back. Any reaction comes from the CNS (collapse, reflex flexion or extension, no movement at all), from pain or from the startle reflex.
- Rifle rounds differ from handgun rounds mainly by what happens **inside** (cavity, fragmentation, bursting), not by entrance size. A 5.56 entrance is often *smaller* than a 9 mm entrance.

---

## 2. Entrance wounds (distant range, i.e. no soot and no stippling)

### 2.1 Size versus calibre

- The size of the skin entrance hole **bears no reliable relation to calibre**. On elastic skin it is usually **smaller than the bullet**. The skin is stretched radially while the bullet passes, then partly recoils [S1, S13, S15].
- Measured example: 9 mm Luger FMJ fired at 1.6 m into porcine skin. Mean hole diameter was **5.61 ± 0.57 mm on belly skin** and **3.33 ± 1.17 mm on back skin**. The thick dorsal dermis recoils more [S1]. That is **62 % and 37 % of the 9.0 mm bullet diameter** [S1, derived].
- 5.56 × 45 mm (M16) autopsy series, Bangkok 2010, 32 shots: **23/32 (72 %) entrance wounds were round and smaller than the bullet diameter**. Most had **micro-tears and no abrasion collar**, because of the small streamlined spitzer tip and full metal jacket [S9].
- Bullet shape matters (.38 Special in pig skin). Round-nose bullets made the **largest abrasion rings and the smallest holes**. Wadcutters made the **smallest rings and the largest holes**, because the sharp shoulder punches out a disc [S2].
- Scalp over bone: the scalp is thick (≈5–7 mm, [K]) and backed by the skull, so scalp entrance holes are round and closer to calibre than trunk holes [K].
- Skull (bone) entrance defects are **generally slightly larger than calibre, sometimes smaller**. They vary from circular to oval or irregular [S5]. .38 defects are significantly larger than .22 and .25 defects, but .22 and .25 cannot be told apart [S5, S6]. Deforming bullets and denser bone (higher bone mineral density) produce larger bone defects [S7].

### 2.2 Abrasion collar (marginal abrasion, contusion ring)

- A ring of abraded epidermis around the hole. The bullet presses the skin inward and the epithelium is scraped off by friction and stretching as the bullet passes [S13, S15]. Present on almost all entrances. Exceptions: palms and soles, where it may be absent or subtle [S15], and high-velocity pointed FMJ rifle bullets (often absent, [S9]).
- Ring area compared with hole area: **3 : 1 for .22 LR** and **2.45 : 1 for 9 mm Parabellum**. Rings are smaller for .22 than for 9 mm [S3].
  - Derived geometry: if hole radius = r_h, then ring outer radius r_o = √(1 + ratio) · r_h. For .22 LR, r_o = 2.0 r_h, so collar width = 1.0 r_h. For 9 mm, r_o = 1.86 r_h, so collar width = 0.86 r_h. With a 9 mm hole of 5.6 mm (r_h 2.8 mm) the collar is **≈2.4 mm wide** [S3 + S1, derived].
- Typical width **1–4 mm** at distant range [S15-level summary]. My default: 1–2 mm for handguns [K].
- **Width versus velocity is non-monotonic.** At a fixed diameter, the collar is widest at intermediate velocities and narrower at very low and very high velocity. It scales with bullet diameter at a fixed velocity [S4]. For game purposes: rifle collars are narrow or absent, handgun collars are clearly visible.
- **Angled shots:** the hole becomes oval and the collar becomes **eccentric, widest on the side the bullet came from**. At shallow angles the collar is semilunar ("half-moon") or comet-tailed, with the broad part pointing toward the shooter [S13, S15, abrasion-collar literature].
- Appearance: fresh collars are red-brown to pink-red and moist. After death they dry to a dark brown, parchment-like band over hours [K]. The bullet may also leave a grey-black "bullet wipe" of lead, lubricant or soot (usually on clothing, sometimes on skin) [K].

### 2.3 Tumbling, ricochet and intermediate-target entrances
- A yawing or tumbling bullet (after a ricochet or after passing through glass, a door, etc.) makes an **elongated or irregular "keyhole-shaped" entrance** with a wide, irregular abrasion. It may carry stippling-like "pseudo-stippling" from fragments [K].
- Fragments of plated bullets can mimic powder stippling ("pseudo-gunpowder stippling") [K; title seen in search results].

### Simulation parameters (distant entrance)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `k_hole_trunk` | 0.37–0.62 (mean 0.5) | × bullet Ø | Multiply by bullet Ø. Use lower values on the back and higher on the belly and chest | [S1] |
| `k_hole_scalp` | 0.7–1.0 | × bullet Ø | Scalp backed by bone | [K] |
| `k_hole_face` (lips, eyelids, cheek) | 0.6–1.0 | × bullet Ø | Lax tissue. Eyelid holes may be slit-like | [K] |
| `hole_shape_noise` | 0–15 | % radius | Slight irregularity. Never a perfect circle | [K] |
| `collar_width_handgun_RN` | 1.5–2.5 | mm | Round-nose handgun | [S3, derived] |
| `collar_width_22LR` | ~1.0 × hole radius (≈1.5–2) | mm | | [S3, derived] |
| `collar_width_rifle_spitzer` | 0–0.5 (often absent, micro-tears instead) | mm | Add 3–8 micro-tears of 0.5–2 mm radiating from the edge | [S9] |
| `collar_width_wadcutter` | 0.5–1 | mm | Hole is closer to 1.0 × Ø | [S2], [K] |
| `collar_eccentricity(θ_inc)` | leading-edge width ≈ w / sin θ_inc, trailing edge ≈ w | mm | Clamp at 8 × w. Below ~15° switch to a "comet-tail" or graze decal | [K] (geometric model) |
| `hole_ellipse(θ_inc)` | major = d / sin θ_inc, minor = d | mm | Clamp major ≤ 4 d. At θ < ~10° use a graze gutter | [K] |
| `bone_defect_outer` | 1.0–1.2 × bullet Ø (sometimes < 1) | × Ø | Outer-table hole at entrance | [S5] |
| `bone_defect_outer_deforming` | +10–30 % vs non-deforming | × Ø | JHP, soft lead | [S7] direction, magnitude [K] |
| Colour: fresh collar | red-brown `#B4533F` | sRGB | Moist sheen | [K] |
| Colour: dried collar | brown parchment `#6E3A22` | sRGB | Blend in over 1–4 h after death | [K] |
| Colour: hole lumen | `#3B0A0A` | sRGB | Near-black red | [K] |
| Colour: bullet wipe | grey-black `#3A3A3A`, alpha 0.3–0.6 | sRGB | Thin ring on the inner edge. Optional | [K] |

### Visual/behavioural checklist (distant entrance)
- A 9 mm distant entrance on the chest is a **~4–6 mm round hole with a 1–3 mm red-brown rim**. Smaller than a pencil. **Never** a coin-sized crater.
- A 5.56 rifle entrance is often **smaller** than a 9 mm entrance, with no clear rim and tiny radial splits.
- Angled shots give an oval hole and a rim that is wide on the side facing the shooter.
- Little external bleeding from a small trunk entrance (see §7.4). Scalp entrances bleed freely.

---

## 3. Range of fire: soot, stippling, searing, contact wounds

### 3.1 Range classes

| Class | Muzzle–skin distance | Key findings | Source |
|---|---|---|---|
| **Hard contact** | 0 (muzzle pressed) | Soot mainly *inside* the wound. Seared, blackened margin. Muzzle imprint. Over bone: stellate or cruciate tears. Cherry-red CO-haemoglobin in the track. Soot on the bone and under the lifted periosteum | [S13, S15, S19, S37] |
| **Loose / angled / incomplete contact** | 0 with a small gap (mm) | Soot escapes through the gap and forms a ring or an eccentric fan around the hole | [S17] |
| **Near contact** | < ~1 cm | Seared zone (burned skin) with soot baked into it. Clumps of unburned powder piled on the wound edge. Stippling not yet visible (grains land too densely, or are hidden under the soot) | [S17] |
| **Close range (soot range)** | ~1 cm to ~20–30 cm (handgun) | Black, dense inner soot halo plus a larger grey outer halo. Both widen and fade with distance. Soot wipes off | [S15, S17] |
| **Intermediate (stippling range)** | ~1 cm to ~60 cm (flake powder), up to 90 cm (flattened ball) and 120 cm (ball powder), for a .38 handgun | Powder-tattoo (stipple) punctate abrasions. Do not wipe off | [S16] |
| **Distant** | beyond stippling range (> ~60–120 cm) | Hole plus abrasion collar only | [S13, S15] |

Supporting numbers:
- Soot: visible from contact to about **30 cm (1 ft)**, absent at 274 cm [S15]. Most handguns deposit soot from **20–30 cm**. Soot diameter shrinks and fades until it is absent at **~40 cm** [search summary of forensic sources; S15]. A UK teaching source gives soot up to **~15 cm** and tattooing up to **30–45 cm**, and says these distances **can be doubled for rifles** [S15 forensicmed].
- Stippling (.38): flake powder disappears at **45–60 cm** (18–24 in), flattened ball powder reaches **90 cm** (36 in), ball powder reaches **120 cm** (48 in) [S16]. Flake powder ≤ 60 cm, ball powder ≤ 90 cm (Dana & DiMaio 2003, cited in [S16 ScienceDirect topic]).
- Stippling has been seen from **~1.3 cm (0.5 in) to ~120 cm (48 in)** [S45].
- Rifles: tattooing up to **60–100 cm** [S15-level summary].
- Stipple pattern diameter (handgun test firings): at **30 cm (12 in), 5.7–17.6 cm** (2.25–6.94 in). At **61 cm (24 in), ≥ 16.5 cm** (6.5 in) [S46].
- Closer means a smaller and denser pattern. Farther means a larger and sparser pattern [S46].

### 3.2 Stippling appearance
- **Red to orange or red-brown punctate abrasions** around the entrance. Each dot is a small abrasion where a powder grain struck the skin. They **cannot be wiped away** [S45].
- **Ante-mortem vs post-mortem:** if the victim was already dead, stipples are **moist grey or yellow** rather than red-brown, and fewer [S45]. (Useful if the player shoots a corpse.)
- Dot size ~0.2–1.5 mm, irregular [K]. Some unburned grains may remain embedded: flake powder appears as dark grey-green specks, ball powder as black spheres [K].
- At 5 cm the stippling is a dense cluster. By 15 cm it thins out [search summary].

### 3.3 Soot appearance
- Two zones. The **inner zone** is dense, black and clearly demarcated. The **outer zone** is a larger, grey, barely visible "cloud" [S17].
- The inner zone becomes wider and less dense as distance increases. In angled shots it becomes **eccentric and elliptical** [S17].
- Engineering interpretation of the angled case [K, geometric]: the gas cone meets the skin as an ellipse. The **dense, sharply edged part lies on the shooter/muzzle side of the hole**, and a fainter fan extends **down-range** (the direction the barrel points).
- Soot is removable. A "wipe/wash" interaction should clear soot but leave stippling, the collar and searing.

### 3.4 Searing and singeing
- Flame and hot gas sear the skin margin (brown-black, leathery) only at contact or near contact with handguns. Handgun "scorching distance" is **a few cm**, but it may reach **up to ~1 m with rifles and muskets** (black-powder era) [S49].
- Singed hair is uncommon because the gas blast pushes hair aside [S49]. Where present, hairs are clubbed, curled and brittle [K].

### 3.5 Contact wounds, especially the head

- **Mechanism.** With the muzzle pressed on skin over bone, the propellant gas follows the bullet into the wound and spreads **between the scalp and the skull**. The scalp balloons outward, slams against the muzzle (making the **muzzle imprint**), then tears when stretched beyond its elasticity. The result is a **stellate or cruciate laceration** [S19, S15, S18]. High-speed video in the skin–skull–brain model shows the bulge, the pressing against the muzzle, and the splitting in that order [S18].
- **Gas volume governs tear size.**
  - A .22 short contact to the temple leaves a **small hole with seared, blackened edges and only tiny triangular tears**. True stellate wounds are the exception with .22 LR contact to the head [S54].
  - A **.357 Magnum** contact to the forehead makes a **large gaping stellate defect** [S54].
  - .22 Magnum is more destructive than other .22s, and cruciform tears are more frequent [S54].
- **Cherry-red colour** of the track and muscle, from carbon monoxide forming carboxyhaemoglobin and carboxymyoglobin [S15 forensicmed].
- **Soot on the outer table of the skull** around the bone hole, and **periosteum lifted and folded back with soot on its underside** [S37 / 2025 review].
- **Rifle contact to the head:** massive destruction of skin, skull and brain, with heterogeneous entrance and exit patterns [S10].
- **Shotgun contact to the head:** see §9.
- **Muzzle imprint** is a patterned abrasion or contusion reproducing the muzzle face: slide front, recoil spring guide, front sight, revolver ejector-rod housing. It can consist of intradermal bleeding [S18 / muzzle imprint study]. Engineers: stamp the actual weapon mesh's front-face silhouette.
- **Contact wounds on soft areas** (abdomen, neck) are round with a seared, sooty rim. They usually **don't tear stellately**, because the gas can expand into soft tissue [K].

### Simulation parameters (range of fire)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `d_contact` | 0 | cm | Hard contact if the muzzle collider penetrates skin by ≥ 0 mm and the angle to the normal is < ~15° | [G] |
| `d_near_contact_max` | 1 | cm | | [S17] |
| `d_soot_dense_max_handgun` | 10 | cm | Dense black inner halo visible | [K] from [S15, S17] |
| `d_soot_max_handgun` | 25 (range 15–30) | cm | Faint grey halo, absent beyond | [S15] |
| `d_soot_max_rifle` | 50 (range 30–60) | cm | "Double for rifles" | [S15 forensicmed] |
| `d_stipple_max_handgun` | 60 (flake). Ball-powder variant 90–120 | cm | Choose per-ammo `powder_type` | [S16] |
| `d_stipple_max_rifle` | 100 (range 60–100+) | cm | | [S15-level] |
| `d_stipple_max_shotgun` | 90 | cm | | [K] |
| `soot_inner_diameter(d)` | ≈ 1 cm + 0.25 · d (d ≤ 10 cm) | cm | Opacity 0.95 → 0.4 across 0–10 cm | [K] synthesized |
| `soot_outer_diameter(d)` | ≈ 3 cm + 0.6 · d (d ≤ 25 cm) | cm | Opacity 0.35 → 0 by `d_soot_max` | [K] synthesized |
| `stipple_pattern_diameter(d)` | ≈ 0.35–0.55 · d + 1 cm | cm | Matches 5.7–17.6 cm at 30 cm and ≥ 16.5 cm at 61 cm | [S46, derived] |
| `stipple_count(d)` | ~300–600 at 5 cm, ~150–300 at 15 cm, ~50–150 at 30 cm, 10–40 near max | dots | Poisson-disc scatter, density falls toward the edge | [K] |
| `stipple_dot_size` | 0.2–1.5 | mm | Irregular, slightly raised | [K] |
| `sear_margin_width` | 1–3 (contact/near contact only) | mm | Dark brown-black leathery ring | [K] |
| `stellate_tear_count` (contact over bone) | 3–6 rays | count | | [K] |
| `stellate_ray_length` | .22LR: 0–3 mm. 9 mm/.45: 5–20 mm. .357 Mag / rifle: 20–60 mm. 12 ga: 40–100+ mm, or gross destruction | mm | Scaled by propellant gas volume | [S54] direction, magnitudes [K] |
| `muzzle_imprint_depth_visual` | abrasion 0.5–1 mm wide lines matching the muzzle face | mm | Only at hard contact over bone. Faint on soft areas | [S18], [K] |
| `CO_tissue_tint_radius` | 5–30 | mm | Around the track at contact range | [K] |
| Colour: dense soot | `#1A1A1A` | sRGB | | [K] |
| Colour: outer soot haze | `#7D7A76` at alpha 0.1–0.35 | sRGB | | [K] |
| Colour: seared margin | `#3A2418` | sRGB | | [K] |
| Colour: stipple (living) | `#A8432A` to `#C85A33` | sRGB | Red to orange-red | [S45], hex [K] |
| Colour: stipple (post-mortem shot) | `#B8AE8A` | sRGB | Grey-yellow, moist | [S45], hex [K] |
| Colour: CO cherry-red tissue | `#D03A45` | sRGB | Brighter than normal muscle `#8E2A2A` | [K] |
| Colour: muzzle imprint | abrasion `#A2463F`, bruise `#6A3F5A` | sRGB | | [K] |

### Visual/behavioural checklist (range of fire)
- The wound decal must **depend on muzzle distance**. Contact wounds have a black-rimmed hole (and a star-tear on the head). Close-range wounds have a soot halo. Intermediate-range wounds have a peppering of red-brown dots. Distant wounds have just a hole with a rim.
- Soot wipes off with a cloth or water. Stippling does not.
- Contact head wound with a 9 mm pistol: a torn star-shaped hole about 1–3 cm across, with black soot in and around the edges and a faint rectangular pistol-muzzle stamp. Contact with a .22: a small hole with a black rim and at most tiny notches.
- Angled close shots: an oval soot or stipple pattern, dense on the gun side, fanning down-range.
- Shooting a corpse at intermediate range gives yellow-grey stipples, not red.

---

## 4. Exit wounds

### 4.1 General features
- Usually **larger and more irregular** than the entrance. Shapes are variable: stellate, slit, crescent, irregular or round. **Edges are everted**, with tissue tags turned outward. **No abrasion collar, no soot, no stippling, no searing** [S13, S15, S12].
- Shape frequencies in one autopsy series: **circular 31.6 %, stellate 27.6 %, irregular 24.5 %, slit-like 12.2 %, crescent 4.1 %**. **Head exits are more likely stellate or irregular** than circular [S12].
- Exit size alone is a poor discriminator of entrance versus exit [S12 summary]. Low-energy FMJ handgun exits can be **small slits of a few mm**, even smaller than the entrance [K].
- **Shored exits** occur when the skin is pressed against a wall, floor, belt, chair back or armour as the bullet exits. They show an **irregular, often broad abrasion rim** that can mimic an entrance collar [S15, S56].

### 4.2 Exit size by bullet type
- **FMJ handgun** (9 mm, .45): exit about the size of the entrance or somewhat larger. Round, slit or stellate. In the head, often stellate or irregular with external bevelling of the bone [K, S12].
- **Hollow point**: if it exits at all, the exit is larger because the expanded bullet (≈ 13–19 mm) leaves. JHPs exit the head less often than FMJ [K].
- **Rifle FMJ (5.56, 7.62)**: exit size is decided by **where the temporary cavity is when the bullet leaves**. An exit plane inside the cavity gives a **very large skin lesion**. The hole is small at the moment of exit, then enlarges secondarily as the cavity expands (high-speed imaging) [S11]. Yaw, fragmentation and bone fragments acting as secondary missiles all enlarge the exit [S10, S11]. Rifle exits are significantly larger than handgun exits [S10].
- **Skull exits**: in bone, the exit is larger than the entrance in 16 of 17 cases, and always more irregular [S8].

### Simulation parameters (exit)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `exit_shape_weights` | circular 0.32, stellate 0.28, irregular 0.24, slit 0.12, crescent 0.04 | probability | Shift +0.15 to stellate and irregular on the head | [S12] |
| `exit_size_FMJ_handgun_trunk` | 0.5–2.0 × bullet Ø (5–18 mm) | mm | Slit length for slit type | [K] |
| `exit_size_FMJ_handgun_head` | 10–30 | mm | Stellate/irregular, bone chips visible | [K] |
| `exit_size_JHP_head` | 15–40 | mm | If it exits at all | [K] |
| `exit_size_rifle` | 10–100+ | mm | Scale with temporary-cavity radius at the exit plane: `r_exit ≈ r_cavity(depth_at_exit) · 0.5–0.8` | [S11] concept, factor [G] |
| `exit_size_rifle_head` | 40–120 (plus calvarial burst) | mm | | [K], [S10] |
| `exit_edge_eversion` | 1–4 | mm | Normal-map lip turned outward, tissue tags | [K] |
| `shored_exit_abrasion_width` | 2–10, irregular | mm | Only if an exit-side collider is in contact with the skin | [S15], width [K] |
| `exit_soot` | 0 | — | Never | [S13] |

### Visual/behavioural checklist (exit)
- An exit on the head looks like a torn star or ragged split, with edges pushed outward. Bone fragments, brain tissue or hair are dragged out, and there is no dark rim.
- Exit wounds bleed more visibly than distant-range entrances on the trunk.
- A body lying against a wall or floor when shot shows abraded, rimmed exits.
- Rifle exits vary enormously, from a small tear to a fist-sized crater. Randomize by where the cavity peaks relative to the exit.

---

## 5. Skull: bevelling, keyholes, fractures

### 5.1 Anatomy inputs
- Mean CT thickness in one study: **frontal 8.0 ± 2.0 mm, parietal 7.0 ± 1.4 mm, temporal 4.7 ± 1.3 mm, occipital 8.0 ± 2.5 mm** [S31]. Another CT study found frontal ~8–9 mm, parietal ~10 mm, temporal ~6 mm, occipital ~10 mm [S31].
- Regional extremes run from **2.1 mm (temporal squama) to 19.2 mm (petrous bone)** [S31].
- Orbital roofs and the cribriform area are paper-thin, roughly 0.5–1 mm in places [K].
- Three layers: outer table, **diploë** (red, marrow-containing cancellous bone), inner table [K].

### 5.2 Bevelling
- **Entrance: inward (internal) bevelling.** The inner-table defect is larger than the outer one, making a cone opening into the skull [S15]. Seen in all but one of 17 cases [S8].
- **Exit: outward (external) bevelling.** The outer-table defect is larger. It was seen on most vault bones but **not on the orbit, maxilla, greater wing of sphenoid, temporal or thin occipital areas**. Thin bones don't bevel clearly [S8].
- External bevelling of an entrance is possible with tangential or keyhole shots and some contact shots [S22].

### 5.3 Keyhole lesion (tangential strike)
- A round part with **inner-table bevelling** (entrance), continuous with a **triangular part with outer-table bevelling** (exit side), made by a bullet striking the vault tangentially [S22]. Exit keyholes also exist. Do not always treat a keyhole as an entrance [S22].
- Engineering: when θ_inc < ~15–20° on the skull and the bullet does not fully penetrate, generate a keyhole defect ≈ 1 × Ø round head plus a 1–3 × Ø triangular tail pointing in the direction of travel [K].

### 5.4 Fracture lines and their sequence
- **Radial (linear) fractures** radiate from the entrance (and from the exit). **Concentric fractures** run perpendicular to them, giving a spider-web look [S20].
- **Speed:** bursting fractures from the entrance run through the skull **faster than the bullet**. They can cross the skull before the bullet exits [S21]. Crack propagation speed in bone is on the order of several hundred to a few thousand m/s. Sound speed in cortical bone is ~3,000–4,000 m/s [K].
- **Hydraulic mechanism.** The temporary cavity pressurizes the closed skull, and the skull bursts to relieve the pressure. Radial burst fractures result. Even handgun bullets generate enough pressure to crack the thin orbital plates [S20 summary / S23].
- **Heaving (concentric) fractures.** Bone segments between radial fractures are pushed **outward**, so they sit **above** the skull plane. This distinguishes them from blunt trauma, where segments are pushed inward [S20 summary].
- **Sequence rule (Puppe).** A fracture stops when it meets an existing fracture. Radials from a second shot, or from the exit, **terminate at** earlier radials. This is used to order multiple shots [S20].

### 5.5 High-velocity bursting and brain evisceration
- High-velocity rifle bullets can **fragment the vault into many pieces**. In a surrogate study, **7.62 mm rifle shots fractured all skull plates and fragmented most completely** [search summary of a surrogate-skull study].
- **Krönlein shot**: close-range high-velocity bullet, or a shotgun slug (for example a Brenneke), opens the skull widely, tears the dura and ejects the brain (sometimes a complete hemisphere, or both hemispheres nearly intact) out of the skull. Immediately fatal in all reported cases [S35].
- High-velocity soft-point hunting bullets leave a **"lead snowstorm"**: dozens to hundreds of dust-like to large metal fragments along the track, cone-shaped with its apex at the entrance or fracture. This is **not** seen with handgun bullets and only rarely with FMJ rifle bullets [S36].

### 5.6 Skull-base fractures, orbital roofs and "raccoon eyes"
- In **147 lethal head shots from handguns and low-velocity small-calibre rifles**, **82 % had fractures of the anterior skull base**. They also occurred with low-energy guns [S23].
- Mechanism: hydraulic overpressure and contre-coup loading of the thin orbital roofs. An isolated orbital-roof "blow-in" fracture can occur even from an occipital entry [S23-context, orbital case reports].
- **Periorbital ecchymosis (raccoon eyes):** blood from fractured orbital roofs tracks along tissue planes into the upper and lower eyelids [S24].
  - Clinically it often becomes obvious **1–3 days** after blunt skull-base fractures. It **can appear within ~1 hour** [S24].
  - In gunshot deaths with orbital-roof fractures, periorbital haemorrhage is a frequent autopsy finding even with short survival, because the orbit fills directly from the fracture [K].
  - Retrobulbar haemorrhage volumes of **0.1–2.4 mL** were measured on post-mortem CT and correlated with visible ecchymosis [S24].
- Related signs [K]:
  - **Battle's sign** (mastoid bruising, usually delayed).
  - Blood from nose and ears.
  - CSF leak (clear or blood-tinged fluid).
  - Subconjunctival haemorrhage.
  - Proptosis (the eye pushed forward).

### Simulation parameters (skull)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `skull_thickness_frontal` | 8 (6–10) | mm | | [S31] |
| `skull_thickness_parietal` | 7–10 | mm | | [S31] |
| `skull_thickness_temporal_squama` | 2–6 (mean ~4.7) | mm | Easiest to penetrate. Poor bevelling | [S31] |
| `skull_thickness_occipital` | 8–10 | mm | | [S31] |
| `orbital_roof_thickness` | 0.5–1 | mm | Indirect fractures | [K] |
| `inner_bevel_ratio` (entrance) | inner-table defect 1.3–2.0 × outer | × | Cone opening inward | [K]. Direction [S8, S15] |
| `outer_bevel_ratio` (exit) | outer-table defect 1.3–2.5 × inner | × | Skip on thin bones (orbit, temporal, maxilla) | [K]. Direction [S8] |
| `radial_fracture_count` | handgun 0–4. Rifle 4–10+ | count | Radiate from entrance and exit | [K] |
| `radial_fracture_length` | handgun 0–80. Rifle to full vault | mm | | [K] |
| `fracture_speed` | ≥ bullet speed (use "instantaneous" within the frame) | m/s | Entrance radials exist before the exit forms | [S21] |
| `puppe_termination` | true | bool | A new crack stops at any existing crack | [S20] |
| `heaving_segments` | outward displacement 1–5 mm | mm | Only with intracranial overpressure (rifle, contact, large handgun) | [S20], magnitude [K] |
| `burst_threshold` | v_impact > 600 m/s, or contact shot with gas volume ≥ magnum/shotgun | — | Vault fragments into 5–30 pieces | [S10], [S35], counts [K] |
| `kronlein_probability` | rifle contact or ≤ 1 m: 0.2–0.5. Shotgun contact: 0.3–0.6 | prob. | Ejects part or all of the brain | [S35] (qualitative), probabilities [G] |
| `anterior_base_fracture_probability` (any penetrating head GSW) | 0.8 | prob. | Drives raccoon eyes | [S23] |
| `raccoon_eye_onset` | 5–30 min faint. 1–6 h clear. Clinically up to 1–3 days | time | Only while circulation continues. After death: limited, slow gravitational spread | [S24], game timing [G] |
| `retrobulbar_blood` | 0.1–2.4 | mL | Proptosis 0–5 mm | [S24], proptosis [K] |
| Colour: outer table | `#E8DEC8` ivory | sRGB | | [K] |
| Colour: diploë (fresh) | `#A4574A` | sRGB | Red marrow | [K] |
| Colour: early periorbital bruise | `#7A2E4A` → `#4B2F63` | sRGB | Red-purple to blue-purple | [K] |
| Colour: subconjunctival bleed | `#B3121C` | sRGB | Bright, flat red on the white of the eye | [K] |

### Visual/behavioural checklist (skull)
- Peel back the scalp at an entrance: a neat round hole on the outer table, with a wider cone (bevelled crater) inside. At the exit it is the reverse, with a wide crater on the outside.
- Handgun head shots: a few cracks radiating from the holes, and cracks from the exit stopping where they meet entrance cracks.
- Rifle head shots: the skull cracks into many plates. Plates lift outward, the scalp splits over them, and brain may be expelled (Krönlein).
- Minutes after a penetrating head shot with continued heartbeat, both eyelids darken purple (raccoon eyes). Blood may run from the nose and one or both ears, and the eye may bulge.
- Sounds: sharp bone crack co-timed with the shot. On rifle bursts, a wet, hollow "pop" with bone fragments pattering.

---

## 6. Brain wound track, cavitation and tissue ejection

### 6.1 Permanent versus temporary cavity
- Two mechanisms act on tissue [S26]:
  - **Crush**, which forms the permanent track.
  - **Temporary cavitation**, a radial stretch-and-shear that lasts about **5–10 ms** [search summary, penetrating head injury sources].
- The brain is **inelastic and effectively incompressible** and sits in a rigid box, so cavitation damages it far more than muscle [S26].
- Low-energy handguns (E₀ < 550 J), human autopsy morphometry: a **destruction zone of ≈ 3.6 cm around the permanent track** corresponding to the temporary cavity. **Axonal damage extends to ~18 mm** from the track [S25]. Remote axonal injury may explain the **very early respiratory arrest** after low-velocity head shots [S25].
- Zones outward from the track, in concentric cylinders [S25-context]:
  - Permanent defect.
  - Glial, vessel and fibre necrosis.
  - Haemorrhage.
  - Outer zone of neuronal and axonal degeneration.
- Gelatin reference sizes:
  - Handgun temporary cavities are **usually < 10 cm** in diameter. 9 mm FMJ reaches a max of ~10 cm [S42].
  - A 5.56 NATO cavity reached **17.1 cm** in one gelatin-plus-bone study [S42].
  - High-velocity cavities range ~17–30 × bullet diameter [S42 summary].
  - In a skull-brain simulant, a 9 mm made a temporary cavity **~1.5 ×** that of a .25 [S50].
  - Pressure spikes of up to ~30 atm have been reported in brain simulants [search summary, lower confidence].
- Brain mass ~1,300–1,400 g. The cranial cavity is ~14–16 cm wide [K]. A 17 cm rifle cavity therefore cannot fit, which is why rifles burst the skull.

### 6.2 What exits the head
- Destroyed brain is either **ejected through the entrance or exit** or packed against the track walls [search summary, penetrating head injury].
- Oozing **CSF, blood and brain parenchyma** from the wound is a recognized finding [same].
- Air ejected from the collapsing temporary cavity has been visualized in simulants. It is a proposed driver of backspatter [S52].
- Handgun through-and-through: typically **a few mL to tens of mL** of pulped brain and blood extruded, most at the exit [K].
- Rifle or Krönlein: **hundreds of g of brain** can leave the skull [S35] (qualitative), [K].

### 6.3 Incapacitation (behaviour hook for the physiology team)
- Most penetrating head shots cause immediate incapacitation. There are documented cases of **retained capacity to act**: 53 case reports, **> 70 % involved slow lightweight bullets** (6.35 mm, .22 rimfire). Frontal tracks shielded by the anterior skull base and sella spare the **brainstem** [S26].
- Outcome statistics:
  - **70–90 % die before reaching hospital**. Overall mortality is **~91 %** [S43].
  - **Bihemispheric** wounds carry **~82 % mortality in adults** and ~4× the odds of death of single-hemisphere wounds [S43].
  - Penetrating brain injuries are 1.5 % of TBIs but **42 % of TBI deaths** [S43].

### Simulation parameters (brain)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `perm_track_diameter_FMJ_handgun` | 1.0–1.5 × bullet Ø | × Ø | Pulped channel | [K] |
| `perm_track_diameter_JHP` | 1.5–2.0 × Ø after 1–3 cm | × Ø | | [K] |
| `destruction_radius_handgun` | 18 (i.e. ~3.6 cm zone) | mm | Mark as "non-functional tissue" for the physiology system | [S25] |
| `temp_cavity_max_diameter_handgun` | 4–10 | cm | Inside the skull, cap at the intracranial width | [S42], [K] |
| `temp_cavity_max_diameter_rifle` | 12–17+ | cm | Exceeds skull width, triggers burst | [S42] |
| `temp_cavity_lifetime` | 5–10 | ms | Sub-frame at 60 fps (16.7 ms). Resolve instantly | [search summary] |
| `brain_extrusion_volume_handgun` | 2–30 | mL | Mostly at the exit. Oozes over 10–120 s | [K] |
| `brain_extrusion_volume_rifle` | 50–1,300 | mL | Krönlein at the upper end | [S35], [K] |
| `respiratory_arrest_early_prob` | high for brainstem, medulla or bihemispheric tracks | — | Hand off to the physiology document | [S25], [S43] |
| `retained_capacity_to_act_prob` | low-energy (.22/.25) frontal track: 0.05–0.15. Otherwise ~0 | prob. | | [S26] qualitative, numbers [G] |
| Colour: grey matter | `#B79C94` | sRGB | Pinkish grey | [K] |
| Colour: white matter | `#E6DACA` | sRGB | Cream | [K] |
| Colour: pulped brain + blood | `#9E5A55` | sRGB | Glistening, semi-fluid | [K] |

### Visual/behavioural checklist (brain)
- A handgun head wound leaks a slow ooze of blood mixed with **pink-grey semi-fluid brain** from the exit, and sometimes from the entrance. It is not a spray of chunks.
- Rifle head wounds eject large volumes of brain and bone at once, sometimes a hemisphere-sized mass landing nearby.
- Instant collapse is typical. Very rarely, a small-calibre frontal shot leaves the character able to move for seconds or minutes.

---

## 7. Blood and tissue spatter from head shots

### 7.1 Back-spatter (from the entrance, toward the shooter)
- Calf-head experiments, 9 mm Parabellum at 0–10 cm [S27, I]:
  - **31–324 macro-stains (> 0.5 mm) per shot**, independent of range.
  - **Maximum distance 72–119 cm**, with **most droplets within 0–50 cm**.
  - Large droplets left **0.7–4 ms** after impact, at a **minimum initial velocity of 13–61 m/s**.
- **Micro-back-spatter** (stains < 0.5 mm) [S27, II]:
  - Maximum distance **69 cm**, most within **0–40 cm**.
  - Contact and 2 cm shots produce a fine spray plus elongated "exclamation-mark" stains.
  - Micro-back-spatter was found on the **weapon and shooting hand at ranges up to 40 cm** [S27 II, S29].
- Back-spatter droplet velocity is about **24 ± 8 m/s**, emitted in a cone of upper angle **57 ± 7°**. Forward spatter produces **more droplets** [S28].
- Blood can enter the **barrel** in contact shots, though some contact shots with heavy external back-spatter left the rear barrel clean [S53].

### 7.2 Forward spatter (from the exit)
- Maximum velocity **47 ± 5 m/s**, about twice the back-spatter velocity. Cone upper angle **27 ± 9°**, much narrower than back-spatter. **More droplets** than back-spatter [S28] (9 mm FMJ experiments).
- Forward spatter includes **mist-like droplets < 0.1 mm** [S28-context BPA sources]. Misting and micro-spatter have been recorded over 5–60 cm [search summary].
- Game default for forward travel: the fine spray settles mostly within 1–2 m. Larger droplets and tissue reach 2–4 m with handguns. Rifles throw bone and brain fragments several metres [K].

### 7.3 Droplet sizes and stain shapes (BPA conventions)
- Gunshot spatter is dominated by **sub-millimetre droplets**. Mist is < 0.1 mm, fine spatter 0.1–1 mm, occasional 1–4 mm drops [K, consistent with S27, S28].
- Stain shape follows impact angle: `width / length ≈ sin(α_impact)`. Round at 90°, elongated with a tail at low angles. The tail points in the direction of travel [K, standard bloodstain pattern analysis].

### 7.4 Bleeding after the impact (hand-off to the circulation and physiology document)
- **Scalp and face are highly vascular** and bleed freely even from small wounds [K].
- **Small distant trunk entrances often bleed little externally.** The skin hole recoils and bleeding is mostly internal [K].
- Blood from nose, mouth and ears after skull-base fractures [K].
- Blood colour [K]:
  - Arterial: bright red.
  - Venous: dark red.
  - Clotting: gelatinous.
  - Drying: red-brown to brown-black at the edges within minutes, pools over hours.
- Surface clot formation starts after ~5–15 min in still pools [K].

### Simulation parameters (spatter)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `backspatter_macro_count` | 30–320 | droplets | Per head shot. Visible droplets > 0.5 mm | [S27] |
| `backspatter_micro_count` | 200–2,000 (render as 2–4 mist sprites plus a speckle decal) | droplets | Not individually simulated | [K], [G] (performance) |
| `backspatter_v0` | 13–61 (mean ~24) | m/s | | [S27], [S28] |
| `backspatter_cone_half_angle` | 50–64 (use 57) | ° | Around the reversed bullet axis | [S28] |
| `backspatter_emit_delay` | 0.7–4 | ms | Same frame as impact | [S27] |
| `backspatter_max_range` | macro 0.7–1.2 m. Micro ≤ 0.7 m. Bulk ≤ 0.5 m | m | Tune drag to match | [S27] |
| `backspatter_on_weapon_max_range` | 40 | cm | Stain the gun and hand only within this | [S27], [S29] |
| `forward_v0` | 42–52 (use 47) | m/s | | [S28] |
| `forward_cone_half_angle` | 18–36 (use 27) | ° | Around the bullet exit vector | [S28] |
| `forward_count_multiplier` | 2–5 × backspatter count | × | "More droplets forward" | [S28] direction, factor [K] |
| `forward_range` | fine 0.05–2 m. Coarse and tissue 1–4 m (handgun). Tissue 2–6 m (rifle) | m | | [K] |
| `droplet_diameter_distribution` | mist < 0.1 (30–60 %), 0.1–1 mm (35–60 %), 1–4 mm (2–10 %) | mm | Log-normal | [K] |
| `tissue_fragment_size` | bone chips 2–20 mm. Brain clumps 3–40 mm. Hair tufts | mm | Rifle and contact shotgun only for > 20 mm | [K] |
| `stain_elongation` | L/W = 1/sin α | — | Tail in the travel direction | [K] |
| `spatter_sound_delay` | 30–300 | ms | Patter as droplets land (0.5–2 m at 20–50 m/s with drag) | [S28] speeds, timing [K] |
| Colour: fresh arterial | `#C8102E` | sRGB | | [K] |
| Colour: fresh venous | `#6D0A0E` | sRGB | | [K] |
| Colour: clotting / dark pool | `#4A0507` | sRGB | | [K] |
| Colour: dried stain | `#3B1A12` | sRGB | Edges dry first | [K] |

### Visual/behavioural checklist (spatter)
- Back-spatter is **sparse and fine**: tens to a few hundred small red dots, mostly within half a metre of the head on the gun side, with a faint mist. It is **not** a big red cloud.
- Exit-side (forward) spatter is **denser, faster and narrower** in angle. It paints the wall or floor behind the head in a cone of fine droplets, with larger drops and tissue further out.
- With the gun at ≤ 40 cm, the gun muzzle, slide and shooting hand get peppered with micro-spatter.
- Stains are round where they hit surfaces head-on and elongated with tails on oblique surfaces.
- Blood keeps flowing after the shot, under gravity, and pools. Colour darkens and edges dry over minutes to hours.
- **Performance note (Godot, 60 fps):** realistic counts are modest. A few hundred macro droplets per shot fit comfortably in a GPUParticles3D system with collision to decals. Treat mist as 2–4 soft sprites plus a projected speckle decal instead of thousands of particles.

---

## 8. Through-and-through vs retained bullets, ricochet inside the skull

- **Retention.** Low-velocity, small-calibre, round-nose lead or lead-core jacketed bullets (.22 LR, .25 ACP) are the ones that ricochet and stay inside [search summary, intracranial ricochet review]. Example: a .22 LR suicide with 13 scalp entrances, most bullets remaining along the skull vault [search summary].
- **Internal ricochet.** A bullet can strike the inner table and **travel along the inner curvature of the vault**, coming to rest on the opposite inner side without crossing the brain. It can also ricochet back into the brain along a new path [search summary, intracranial ricochet literature].
- **Bullet under the scalp at the "exit".** The bullet penetrates the far skull but not the tough, elastic scalp. It is palpable under a bulge [K].
- **Migration.** Retained intracranial bullets can migrate (rare) [search summary].
- **Deformation on bone.** Soft lead and JHP bullets deform or fragment on the skull. Jacketed rifle bullets may fragment [K].

### Simulation parameters (retention and ricochet)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `p_exit_head_22LR` | 0.15–0.35 | prob. | | [K] |
| `p_exit_head_9mm_FMJ` | 0.6–0.8 | prob. | | [K] |
| `p_exit_head_9mm_JHP` | 0.3–0.5 | prob. | | [K] |
| `p_exit_head_45_FMJ` | 0.55–0.75 | prob. | | [K] |
| `p_exit_head_rifle` | 0.95–1.0 | prob. | Fragments may remain | [K] |
| `p_internal_ricochet` (.22/.25, when not exiting) | 0.2–0.4 | prob. | Follows the inner table 2–10 cm | [K] |
| `p_retained_under_scalp` (given the far table is perforated but no exit) | 0.3–0.5 | prob. | Visible lump. Bruise forms if alive | [K] |
| `ricochet_angle_threshold_skull` | θ_inc < 10–20° | ° | Glancing strike leads to a graze or keyhole instead of penetration | [K] |
| `energy_loss_per_table` | handgun 15–40 % of remaining E per table | % | Tune so .22 often fails at the second table | [K] |

### Visual/behavioural checklist (retention)
- Many small-calibre head shots have **no exit**. The bullet is found under the opposite scalp, or it slid along the inside of the skull.
- A retained bullet under the scalp may show as a small bulge with a bruise (if the heart is still beating).

---

## 9. Shotgun wounds

### 9.1 Pattern versus range (12-gauge, typical cylinder or improved-cylinder)

| Range | Skin appearance | Source |
|---|---|---|
| Contact (head) | Gross destruction. Stellate or bursting scalp, calvarial burst, brain partly ejected (Krönlein-like with slugs). Muzzle imprint. Soot inside. Wad inside the wound | [S35], [S37] |
| Up to ~1 m | **Single round hole ~2.5–4 cm**, smooth edges, wad often inside | [S37 forensicmed] |
| ~1–2 m | Single hole with **scalloped ("crenated") edges** as the outer pellets separate | [S37] |
| ~2–4 m | **Central hole with satellite pellet holes** | [S37 WikEM / AMBOSS summary] |
| Beyond ~4–5 m (varies with choke) | **Individual pellet holes, no central defect** | [S37] |

- Spread rule of thumb: **~1 inch per yard (≈2.8 cm per m)** for a cylinder bore. Modern shot-cup wads and chokes give **tighter** patterns. At 1 yd the charge is still ~1 inch (2.5 cm) wide, ~2 in (5 cm) at 3 yd, ~3 in (7.5 cm) at 5 yd with defensive buckshot [S38].
- **Wad**: at close range (single hole) the wad is found **inside the body** [S47]. Beyond **~1.5–1.8 m** the wad separates from the shot and strikes the skin separately, leaving its own abrasion [S47]. Plastic-wad **"petal" marks** give a Maltese-cross abrasion: **4 petals for 12/16/20 gauge, 3 for .410** [S47]. Wad marks have been seen out to **~4.5 m (filler wads) and ~6 m (plastic wads)** [S47].
- **Soot and stippling** as for rifled arms (§3). Shotgun powder tattooing extends to roughly 0.9 m [K].

### 9.2 Buckshot versus birdshot
- **00 buckshot**: **9 pellets of 8.4 mm** per 2¾-in shell [S39]. Each pellet makes its own entrance, with a round hole about 4–7 mm and an abrasion collar [K]. Deep penetration: **~25–53 cm** in gelatin, most pellets > 40 cm [S40]. Pellets can perforate the head [K].
- **#7.5 birdshot**: **~350 pellets of ~2.4 mm** [S39]. At close range it acts as a single mass and makes a very destructive hole. At range, pellets penetrate shallowly, **~5–15 cm** in gelatin [S40]. Each distant pellet hole is ~1.5–2.5 mm with a tiny collar [K].
- **Skull and eye** [search summary, pellet head injuries]:
  - Distant birdshot enters the cranium mainly through **thin bone (temporal and occipital squama) and the orbits**. The **orbit is the most common path into the brain**.
  - Eyes are highly vulnerable.
  - Severity depends on the effective range.

### Simulation parameters (shotgun)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `shot_column_diameter_0_1m` | 2.5–4 | cm | Single hole | [S37] |
| `pattern_diameter(r)` (r > 1 m) | 2.5 cm + (1.5–2.8) cm × (r − 1 m)/m | cm | 2.8 for cylinder bore. 1.5 for shot cup or choke | [S38], [G] |
| `scallop_onset_range` | 1.0 | m | | [S37] |
| `satellite_onset_range` | 2.0 | m | | [S37] |
| `no_central_hole_range` | 4–5 (cylinder). 6–8 (tight choke or shot cup) | m | | [S37], choke values [K] |
| `wad_inside_wound_max_range` | 1.5 | m | Wad mesh placed in the track | [S47] |
| `wad_petal_mark_range` | 0.3–1.5 | m | 4 petals (12 ga) | [S47], lower bound [K] |
| `wad_separate_abrasion_range` | 1.5–6 | m | Separate 1–3 cm round or oval abrasion | [S47] |
| `buck_00_pellets` | 9 × 8.4 mm | — | | [S39] |
| `bird_7_5_pellets` | ~350 × 2.4 mm | — | Render the distant pattern as an instanced decal atlas | [S39] |
| `buck_penetration_tissue` | 25–53 | cm | | [S40] |
| `bird_penetration_tissue` | 5–15 | cm | At range. Tunes skull-entry rules | [S40] |
| `bird_skull_entry_rule` | penetrates only orbit, temporal squama (≤ 4 mm) or open fontanelle-equivalent thin bone beyond ~5 m | — | | [search summary], [K] |
| `pellet_hole_size` | buck 4–7 mm. Bird 1.5–2.5 mm | mm | | [K] |
| `contact_shotgun_head_outcome` | calvarial burst 1.0. Brain partially ejected 0.5–0.9 | prob. | | [S35], [K] |

### Visual/behavioural checklist (shotgun)
- **Point-blank to ~1 m**: one big round hole (golf-ball to ping-pong-ball size), plus soot or stipple if close. The plastic wad may be inside.
- **1–2 m**: a big hole with a scalloped edge.
- **2–4 m**: a central hole plus a ring of separate pellet holes.
- **Far**: a spray of small holes, no big hole. With birdshot, many shallow pits on the face, and eyes and eyelids perforated.
- Petal-shaped bruise marks (4 arms) around the hole at close-intermediate range.
- Contact shotgun to the head: a massively destroyed head. Scalp split in flaps, skull shattered, brain partly ejected, heavy forward spray and tissue.

---

## 10. Facial and jaw shots

- In a 7-year series of **578 patients** with head, neck or facial gunshot wounds, **204 survived with facial fractures**. The most fractured bones were the **maxilla 62 %, orbit 55 % and mandible 51 %**. Mandible fractures had the **highest operative rate (76 %)** [S32]. Another series lists the orbit as the second most common fracture site (20.5 %), after the zygoma (13.7 %) and nasal bone (12.2 %) [search summary, facial projectile series].
- **High-velocity face wounds** show highly comminuted facial-skeleton fractures and **avulsion of facial and intra-oral soft tissue** along the track, with secondary distant fractures [S34].
- **Teeth and bone fragments act as secondary projectiles**, causing damage away from the track [S34].
- When a high-velocity bullet strikes the **mandible**, the result is a severely comminuted mandible surrounded by non-viable soft tissue, with embedded foreign bodies [S34].
- **Intra-oral contact shots**:
  - Entrance in the **hard palate or posterior pharynx**, with the muzzle usually pointed upward [S33].
  - **Lip lacerations** result when the **lower incisors are driven forward** as the alveolar process fractures under the sharp rise in intra-oral pressure [S33].
  - Broken incisors, damage down to **C1** (upper spinal cord) [S33].
  - Soot on the tongue and palate, and CO-coloured tissue [K].
- **Submental (under-chin) upward shots** can travel face → skull and eviscerate the brain (atypical Krönlein) [S35].
- Soft-tissue behaviour [K]:
  - Lips and cheeks are lax: entrances may be slit-like, exits ragged with large flaps.
  - Tongue lacerations bleed heavily (lingual artery).
  - Blood pours into the airway.

### Simulation parameters (face and jaw)

| Parameter | Value / range | Unit | Notes | Source |
|---|---|---|---|---|
| `p_fracture_maxilla / orbit / mandible` given a facial GSW with fracture | 0.62 / 0.55 / 0.51 | prob. | Not exclusive | [S32] |
| `mandible_comminution_fragments` | handgun 2–6. Rifle 6–20+ | count | | [K] |
| `teeth_fractured_per_hit` | handgun 1–4. Rifle or contact 4–12 | count | Fragments become secondary projectiles (1–5 mm, 5–30 m/s) | [S34] qualitative, numbers [K] |
| `lip_cheek_tissue_loss_rifle` | 10–60 | cm² | Avulsed flaps | [K] |
| `intraoral_contact_lip_split` | 0.5–1.0 | prob. | Split lower lip. Displaced incisors | [S33] |
| `facial_bleeding_rate` | 5–30 (up to 100+ with facial or lingual artery transection, while BP is maintained) | mL/min | Hand to the physiology doc | [K] |
| `airway_blood_aspiration` | on | bool | Gurgling breaths. Blood from mouth and nose | [K] |

### Visual/behavioural checklist (face and jaw)
- A handgun shot through the cheek: small entrance, ragged exit on the other cheek, broken teeth, blood pouring from the mouth.
- A rifle shot to the jaw: the mandible shattered with a sagging lower face, lips and cheek torn into flaps, and tooth fragments embedded in the tongue and cheek.
- An intra-oral contact shot: little visible on the outside except a split lip, broken front teeth and blood from the mouth and nose. Soot inside the mouth. Devastating damage behind the palate.
- Gurgling and bubbling breaths while alive (airway blood).

---

## 11. Common realism mistakes in games and films (with the fix)

| # | Mistake | Reality | Fix | Source |
|---|---|---|---|---|
| 1 | Entrance holes larger than the bullet (coin or crater decals) | Trunk entrances are ~40–60 % of bullet Ø (9 mm gives ~4–6 mm). Rifle entrances are often *smaller* than handgun entrances | `k_hole_trunk` 0.37–0.62 | [S1], [S9] |
| 2 | Same decal at every range | Contact, near, close, intermediate and distant look completely different | §3 range model | [S13], [S15], [S16] |
| 3 | Soot or burn on exit wounds | Exits never show soot, stippling or searing | Exit decals have no residue channel | [S13] |
| 4 | Exit identical to entrance, or missing | Exits are everted, irregular, stellate or slit, often larger. Head exits are mostly stellate or irregular | §4 | [S12] |
| 5 | Stellate star-tears everywhere | Only contact shots over bone (head, sternum). Distant shots are round | §3.5 | [S19], [S54] |
| 6 | Bodies thrown back by bullets | Momentum gives 0.01–0.18 m/s. People collapse, or keep going | §1 | [S30] |
| 7 | Every handgun headshot explodes the head | Handgun: small holes, a few cracks, some ooze. Bursting needs a rifle, a shotgun contact or a large-gas contact | §5.5 | [S10], [S35] |
| 8 | Huge red blood cloud on every hit | Back-spatter is sparse (30–320 macro drops), fine and short-ranged (< 0.5 m bulk). Forward spatter is denser and narrower | §7 | [S27], [S28] |
| 9 | Uniform, instant, static blood | Blood varies: bright arterial or dark venous, dripping, pooling, clotting, drying brown. Small entrances may barely bleed. Scalp bleeds freely | §7.4 | [K] |
| 10 | Shotgun at 10 m = one big hole | One hole only up to ~1 m (2.5–4 cm). Scalloped at 1–2 m. Satellites at 2–4 m. Pellet spray beyond | §9 | [S37] |
| 11 | Wounds don't evolve | Collars dry brown after death. Raccoon eyes and bruising develop only while circulation continues. Clots form | §5.6, §2.2 | [S24], [K] |
| 12 | Circular decals regardless of angle | Oblique shots give an oval hole, eccentric collar and elliptical soot or stipple | §2.2, §3.3 | [S13], [S17] |
| 13 | Headshot = instant death for everyone, always | Usually immediate incapacitation, but rare retained function with low-energy frontal tracks | §6.3 | [S26] |
| 14 | Back of the head blown out by any pistol | Many .22 and .25 head shots don't exit. Bullets lodge under the far scalp or ricochet around the inner skull | §8 | [search summary], [K] |
| 15 | Muzzle-flash burns at distance | Searing only at contact or a few cm with handguns | §3.4 | [S49] |

---

## 12. Load-bearing numbers (quick reference)

1. Entrance hole in trunk skin, 9 mm at 1.6 m: **5.61 ± 0.57 mm (belly), 3.33 ± 1.17 mm (back)**, i.e. **~0.4–0.6 × bullet Ø** [S1].
2. **72 %** of 5.56 entrances were smaller than the bullet, with micro-tears and **no abrasion collar** [S9].
3. Abrasion-ring area : hole area = **3 : 1 (.22 LR)**, **2.45 : 1 (9 mm)**. That gives a collar width of ~1.0 × and ~0.86 × hole radius (≈ 2–2.5 mm for 9 mm) [S3, derived].
4. Collar is eccentric, widest on the side the bullet came from, in angled shots [S13].
5. Soot to **~20–30 cm** (handgun), absent by ~40 cm. "Double for rifles" [S15].
6. Stippling (.38) to **45–60 cm (flake), 90 cm (flattened ball), 120 cm (ball)** [S16]. Stipple pattern **5.7–17.6 cm at 30 cm** and **≥ 16.5 cm at 61 cm** [S46].
7. Living-victim stipples are red-orange or red-brown. Post-mortem stipples are grey-yellow [S45].
8. Contact over bone gives a stellate tear from gas under the scalp, a muzzle imprint, and CO cherry-red tissue. .22 LR rarely makes true stellate tears. .357 Magnum makes large ones [S19], [S54].
9. Exit shapes: circular 31.6 %, stellate 27.6 %, irregular 24.5 %, slit 12.2 %, crescent 4.1 %. **Head exits skew stellate or irregular** [S12].
10. Skull: **internal bevel at entrance, external at exit**. Exits larger in 16/17 cases. No bevel on thin bones [S8].
11. Radial fractures outrun the bullet. Later fractures stop at earlier ones (**Puppe**) [S20], [S21].
12. **82 %** of lethal handgun or low-velocity head shots had anterior skull-base fractures [S23]. Raccoon eyes can appear within ~1 h, and clinically over 1–3 days [S24].
13. Low-energy (< 550 J) brain wounds: a **~3.6 cm destruction zone** around the track, axonal injury to **18 mm** [S25].
14. Back-spatter: **31–324** macro-droplets, max **72–119 cm**, bulk within **50 cm**, **13–61 m/s**, emitted 0.7–4 ms after impact. Micro max **69 cm** [S27].
15. Forward spatter **47 ± 5 m/s**, cone **27 ± 9°**. Back-spatter **24 ± 8 m/s**, cone **57 ± 7°**. More droplets forward [S28].
16. Body knock-back from any small arm: **0.01–0.18 m/s** [S30].
17. Shotgun: single **2.5–4 cm** hole to ~1 m, scalloped 1–2 m, satellites 2–4 m. Wad inside the wound < ~1.5 m. Petal marks (4 petals for 12 ga). Wad marks to ~6 m [S37], [S47].
18. 00 buck = **9 × 8.4 mm**. #7.5 bird = **~350 × 2.4 mm** [S39].
19. Facial GSW fractures: **maxilla 62 %, orbit 55 %, mandible 51 %** [S32]. Teeth and bone act as secondary missiles [S34].
20. Prehospital death **70–90 %**. Overall mortality ~91 %. Bihemispheric ~82 % [S43].

---

## 13. Sources

All URLs were found and read through web-search result summaries only (see §0.2). Full texts were not accessible in this session.

- **[S1]** Geisenberger D. et al. (2022). Differing sizes of bullet entrance holes in skin of the anterior and posterior trunk. *Int J Legal Med*. https://pubmed.ncbi.nlm.nih.gov/36006518/ ; https://www.ncbi.nlm.nih.gov/pmc/articles/PMC9576652/
- **[S2]** Pircher R., Preiß D., Pollak S. et al. (2017). The influence of the bullet shape on the width of abrasion collars and the size of gunshot entrance holes. *Int J Legal Med*. https://pubmed.ncbi.nlm.nih.gov/27909866
- **[S3]** Morphologic and morphometric aspects of the contusion ring ("abrasion seam") of gunshot wounds (.22 LR vs 9 mm). https://pubmed.ncbi.nlm.nih.gov/1811497/
- **[S4]** Randall B., Jaqua R. (1991). Gunshot entrance wound abrasion ring width as a function of projectile diameter and velocity. *J Forensic Sci* 36(1):138. https://pubmed.ncbi.nlm.nih.gov/2007864/
- **[S5]** Berryman H.E., Smith O.C., Symes S.A. (1995). Diameter of cranial gunshot wounds as a function of bullet caliber. *J Forensic Sci* 40(5):751–4. https://pubmed.ncbi.nlm.nih.gov/7595316/
- **[S6]** Ross A.H. (1996). Caliber estimation from cranial entrance defect measurements. https://pubmed.ncbi.nlm.nih.gov/8754573/
- **[S7]** Relationship between bullet diameter and bullet defect diameter in human calvariums (2020). *Int J Legal Med*. https://pubmed.ncbi.nlm.nih.gov/31734727/
- **[S8]** Quatrehomme G., İşcan M.Y. (1998). Gunshot wounds to the skull: comparison of entries and exits. *Forensic Sci Int*. https://pubmed.ncbi.nlm.nih.gov/9670492/ ; also Characteristics of gunshot wounds in the skull (1999) https://pubmed.ncbi.nlm.nih.gov/10408112/
- **[S9]** Entrance and exit wounds of high velocity bullet: an autopsy analysis, Bangkok, May 2010 (5.56 × 45 mm). https://pubmed.ncbi.nlm.nih.gov/27890096/
- **[S10]** The wounding potential of assault rifles: dimensions of entrance and exit wounds vs conventional handguns, a multicentric study (2024). *Forensic Sci Med Pathol*. https://pubmed.ncbi.nlm.nih.gov/38146043/
- **[S11]** The varying size of exit wounds from center-fire rifles as a consequence of the temporary cavity (2013). *Int J Legal Med* 127(5):931–936. https://pubmed.ncbi.nlm.nih.gov/23700297/
- **[S12]** Pipatchotitham T., Tangsermkijsakul A. The prevalence of exit gunshot wound shapes and the relationship of the shape to the location of exit wounds. *Asian Med J Alt Med*. https://asianmedjam.researchcommons.org/amjam/vol22/iss1/4/
- **[S13]** Shrestha R., Kanchan T., Krishan K. Gunshot Wounds Forensic Pathology. *StatPearls*. https://www.ncbi.nlm.nih.gov/books/NBK556119/
- **[S14]** Denton J.S., Segovia A., Filkins J.A. (2006). Practical pathology of gunshot wounds. *Arch Pathol Lab Med* 130(9):1283–9. https://pubmed.ncbi.nlm.nih.gov/16948512/
- **[S15]** Forensic teaching sources on range of fire and entrance/exit features: PathologyOutlines, Gunshot wounds https://www.pathologyoutlines.com/topic/forensicsgunshotwounds.html ; Medscape, Forensic Pathology of Firearm Wounds https://emedicine.medscape.com/article/1975428-overview ; forensicmed.co.uk, Gunshot wounds, rifled weapons https://www.forensicmed.co.uk/wounds/firearms/gunshot-wounds-rifled-weapons/ ; Libre Pathology https://librepathology.org/wiki/Gunshot_wounds ; Discordance of gross and histologic findings in estimating range of fire https://pubmed.ncbi.nlm.nih.gov/30897211/
- **[S16]** DiMaio V.J.M. (1976). An experimental study of powder tattooing of the skin. *J Forensic Sci* 21(2):367. https://asmedigitalcollection.asme.org/forensicsciences/article/21/2/367/1180585/ ; ScienceDirect Topics, Gunpowder (cites Dana & DiMaio 2003) https://www.sciencedirect.com/topics/pharmacology-toxicology-and-pharmaceutical-science/gunpowder
- **[S17]** Gunshot residue patterns on skin in angled contact and near contact gunshot wounds (2003). *Forensic Sci Int*. https://pubmed.ncbi.nlm.nih.gov/14642721/
- **[S18]** The dynamic development of the muzzle imprint by contact gunshot: high-speed documentation utilizing the "skin–skull–brain model". https://www.sciencedirect.com/science/article/abs/pii/S0379073802001172 ; Muzzle imprint mark study https://www.sciencedirect.com/science/article/abs/pii/S0379073814003569
- **[S19]** ACEP Now: The clinical forensic evaluation of gunshot wounds in the ED. https://www.acepnow.com/article/the-clinical-forensic-evaluation-of-gunshot-wounds-in-the-ed/
- **[S20]** Puppe's rule literature: Exception to Puppe's rule reloaded (2024) https://pubmed.ncbi.nlm.nih.gov/38733466/ ; Puppe's rule, a literature review https://pubmed.ncbi.nlm.nih.gov/22448468/ ; Intersecting fractures of the skull and gunshot wounds https://link.springer.com/article/10.1007/s12024-008-9062-8
- **[S21]** Observations of the propagation velocity and formation mechanism of burst fractures caused by gunshot. https://pubmed.ncbi.nlm.nih.gov/2818487/
- **[S22]** Dixon D.S. (1984). Exit keyhole lesion and direction of fire in a gunshot wound of the skull. https://pubmed.ncbi.nlm.nih.gov/6699601/ ; The mechanism of the keyhole lesion reassessed https://www.sciencedirect.com/science/article/abs/pii/S1752928X15001870
- **[S23]** Fractures at the base of the skull in gunshots to the head (1997). *Forensic Sci Int*. https://pubmed.ncbi.nlm.nih.gov/9180024/
- **[S24]** WikEM, Basilar skull fracture https://wikem.org/wiki/Basilar_skull_fracture ; "Blind spots" in forensic autopsy: retrobulbar hemorrhage and orbital lesions by PMCT https://pubmed.ncbi.nlm.nih.gov/25017308/ ; Raccoon eyes as a sign of skull base fracture https://www.sciencedirect.com/science/article/abs/pii/S0020138301001449
- **[S25]** Oehmichen M., Meissner C., König H.G. (2000). Brain injury after gunshot wounding: morphometric analysis of cell destruction caused by temporary cavitation. *J Neurotrauma* 17:155. https://journals.sagepub.com/doi/abs/10.1089/neu.2000.17.155 ; Oehmichen et al. (2004). Gunshot injuries to the head and brain caused by low-velocity handguns and rifles: a review. https://pubmed.ncbi.nlm.nih.gov/15542271/ ; imaging and biometry (2003) https://pubmed.ncbi.nlm.nih.gov/12664319/
- **[S26]** Karger B. Penetrating gunshots to the head and lack of immediate incapacitation. I. https://pubmed.ncbi.nlm.nih.gov/8547159/ ; II. https://pubmed.ncbi.nlm.nih.gov/8664147/
- **[S27]** Karger B. et al. Backspatter from experimental close-range shots to the head. I. Macrobackspatter https://pubmed.ncbi.nlm.nih.gov/8912050/ ; II. Microbackspatter https://pubmed.ncbi.nlm.nih.gov/9081237/
- **[S28]** Comiskey P., Yarin A., Attinger D. High-speed video analysis of forward and backward spattered blood droplets https://www.sciencedirect.com/science/article/abs/pii/S0379073817301536 ; Theoretical and experimental investigation of forward spatter of blood from a gunshot, *Phys Rev Fluids* 3:063901 https://journals.aps.org/prfluids/abstract/10.1103/PhysRevFluids.3.063901 ; Prediction of blood back spatter https://link.aps.org/pdf/10.1103/PhysRevFluids.1.043201
- **[S29]** Kunz S.N. et al. (2015). Characteristics of backspatter on the firearm and shooting hand. *J Forensic Sci*. https://onlinelibrary.wiley.com/doi/abs/10.1111/1556-4029.12572
- **[S30]** Karger B. et al. On the physics of momentum in ballistics: can the human body be displaced or knocked down by a small arms projectile? https://pubmed.ncbi.nlm.nih.gov/8956990/
- **[S31]** Morphometric measurement of cranial vault thickness (CT). https://pmc.ncbi.nlm.nih.gov/articles/PMC8827567/ ; Average thickness of the bones of the human neurocranium https://link.springer.com/article/10.1007/s00414-022-02824-y
- **[S32]** Fracture patterns in craniofacial gunshot wounds: a seven-year experience. https://pubmed.ncbi.nlm.nih.gov/40276519
- **[S33]** Intra- and perioral shooting fatalities https://www.sciencedirect.com/science/article/abs/pii/S0379073899000328 ; Suicidal intra-oral gunshot with labial laceration https://austinpublishinggroup.com/forensicscience-criminology/fulltext/ajfsc-v4-id1064.php
- **[S34]** Treatment protocol for high velocity/high energy gunshot injuries to the face. https://pmc.ncbi.nlm.nih.gov/articles/PMC3348750/
- **[S35]** Krönlein shot literature: An autopsy case of the decomposed body with Krönlein's shot https://pmc.ncbi.nlm.nih.gov/articles/PMC8848563/ ; A typical Krönlein shot? Submental-facio-cranial trajectory https://www.researchgate.net/publication/282448368
- **[S36]** Hollerman et al. Gunshot injuries: what does a radiologist need to know? *RadioGraphics* 19(5) https://pubs.rsna.org/doi/abs/10.1148/radiographics.19.5.g99se171358 ; lead snowstorm from buckshot https://pubmed.ncbi.nlm.nih.gov/21817870/
- **[S37]** Shotgun wound morphology: forensicmed.co.uk, smooth-bore weapons https://www.forensicmed.co.uk/wounds/firearms/gunshot-wounds-smooth-bore-weapons/ ; Lablogatory, Introduction to shotgun wounds https://labmedicineblog.com/2024/03/21/introduction-to-shotgun-wounds/ ; WikEM, Gun shot wounds https://wikem.org/wiki/Gun_shot_wounds ; AMBOSS forensic ballistics https://www.amboss.com/us/knowledge/forensic-ballistics ; Fackler M.L. Shotgun wound ballistics, *J Trauma* 1988 https://journals.lww.com/jtrauma/abstract/1988/05000/shotgun_wound_ballistics.11.aspx
- **[S38]** Shotgun pattern spread (non-clinical, firearms press): https://www.thefirearmblog.com/blog/2014/07/04/myth-busting-1-per-yard-shotgun-pattern-spreads/ ; https://www.shootingillustrated.com/content/the-beginner-s-guide-to-shotgun-chokes/
- **[S39]** Pellet counts: https://www.shotgunlife.com/briefs/unpacking-the-pellet-count-in-12-gauge-shotgun-shells.html ; https://fiocchi.com/en/blog/post/how-many-pellets-in-a-cartridge/
- **[S40]** Gelatin penetration of birdshot and buckshot (non-clinical test reports, lower quality): https://www.thetruthaboutguns.com/shotgun-penetration-with-various-rounds/ ; https://trueshotammo.com/academy/buckshot-vs-birdshot/
- **[S41]** Fackler M.L. Wounding patterns of military rifle bullets. https://ia903201.us.archive.org/7/items/wounding_patterns_military_rifles/wounding_patterns_military_rifles_text.pdf ; Terminal ballistics of 7.62 mm NATO bullets: experiments in ordnance gelatin https://pubmed.ncbi.nlm.nih.gov/8547160/
- **[S42]** Temporary cavity sizes: Comparing terminal performance of .357 SIG and 9 mm bullets in ballistic gelatin (arXiv) https://arxiv.org/pdf/1508.05843 ; Experimental wound ballistic study of various bullets and firearms (2025) https://link.springer.com/article/10.1007/s12024-025-01132-2 (the source of the 17.1 cm 5.56 value per the search summary; I could not verify the exact paper)
- **[S43]** Civilian gunshot wounds to the head: case report, clinical management, literature review https://pmc.ncbi.nlm.nih.gov/articles/PMC7856761/ ; Penetrating Head Trauma, *StatPearls* https://www.ncbi.nlm.nih.gov/books/NBK459254/
- **[S44]** .22 Long Rifle cartridge data. https://en.wikipedia.org/wiki/.22_long_rifle
- **[S45]** Stippling appearance, ante- vs post-mortem: PathologyOutlines (above) ; https://www.medicalalgorithms.com/stippling-and-tattooing-in-a-gunshot-wound
- **[S46]** Forensic gunshot residue distance determination testing (ETSU thesis). https://dc.etsu.edu/cgi/viewcontent.cgi?article=3267&context=etd
- **[S47]** Wad marks and ranges: forensicmed.co.uk smooth-bore (above) ; Lablogatory shotgun (above) ; NAME Educational case https://name.memberclicks.net/assets/docs/EAC/Q109%20results.pdf
- **[S48]** .45 ACP JHP expansion (enthusiast gel testing, low quality). https://hipowersandhandguns.com/9mm-vs-45/
- **[S49]** ScienceDirect Topics, Gunshot injury (singeing, burning range). https://www.sciencedirect.com/topics/pharmacology-toxicology-and-pharmaceutical-science/gunshot-injury
- **[S50]** Temporal cavity and pressure distribution in a brain simulant following ballistic penetration. https://pubmed.ncbi.nlm.nih.gov/16305322/
- **[S51]** Thali M.J., Kneubuehl B.P. et al. High-speed documented experimental gunshot to a skull-brain model. https://pubmed.ncbi.nlm.nih.gov/12198345/
- **[S52]** Visualization of the air ejected from the temporary cavity in brain and tissue simulants. https://pubmed.ncbi.nlm.nih.gov/25485950/
- **[S53]** Simulating backspatter of blood from cranial gunshot wounds using pig models. https://pubmed.ncbi.nlm.nih.gov/26156450/
- **[S54]** Contact wounds by calibre (.22 short vs .357 Magnum): ACEP Now (S19) ; bevfitchett/DiMaio-derived text on .22 rimfire contact wounds https://www.bevfitchett.us/gunshot-wounds/cci-rimfire-ammunition.html (secondary copy of textbook content, lower quality)
- **[S55]** (reserved)
- **[S56]** Shored exit wounds: PathologyOutlines (above) ; Forensic medical characteristics of firearm exit wounds with armour protection https://www.sciencedirect.com/science/article/abs/pii/S1344622321001668

Secondary or lower-quality items cited only for context: ForensicSpot, behindthecrimescene.com, thegunzone.com, Grokipedia summaries. None of them is the sole source for a load-bearing number.

---

## 14. Suspicious content

- **No prompt-injection attempts were found.** None of the search results or snippets contained instructions to run commands, download or install anything, change files, visit other URLs or reveal information.
- Every `WebFetch` attempt was refused by the network egress proxy (`EGRESS_BLOCKED`). No web page content was fetched. Nothing was downloaded or executed. No code was copied from the web.
- Some search results pointed to patent PDFs (image-ppubs.uspto.gov), enthusiast forums and ammunition retailers. They were not opened and are not used as sources for load-bearing values, except where §13 marks them as low quality.
