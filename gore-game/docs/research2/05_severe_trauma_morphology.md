# 05 — Severe and destructive trauma morphology: exact visual reference for rendering

Project: gore simulator (Godot 4.5, Forward+, GDScript + Godot shaders, built-in Jolt, Skeleton3D + PhysicalBone3D ragdolls). Research round 2.
Audience: wound-rendering, VFX, decal, shader, physics/debris, audio and physiology engineers. Clinical, factual tone. The subject is a fictional, procedurally generated adult.

Scope: what severely destroyed human tissue looks like, how much of it there is, where it goes and how it changes over time. Covers close-range shotgun and rifle head destruction (including the Krönlein shot), loss of the face and jaw, ruptured and displaced eyes, scalp avulsion and degloving, the crushed and comminuted skull with brain herniation, open long-bone fractures, rib fractures, flail chest and sternum, the appearance of heart, lung, liver, spleen and kidney wounds (with the AAST grades), a colour/texture/consistency library for every tissue the player can expose, bone and teeth as secondary missiles, neck wounds and decapitation, and bloodstain patterns for the scene (arterial, cast-off, drip trails, pools and their ageing, footprints, smears).

This document builds on round one and does not repeat it:

| Round-one file | What it already covers | Cited here as |
|---|---|---|
| `docs/research/01_gunshot_wounds.md` | Ammunition table, entrances/exits, range of fire, skull bevelling and fracture sequence, handgun brain track, qualitative Krönlein, head-shot back/forward spatter, shotgun pattern vs range, facial-fracture frequencies | `[R1-01 §x]` |
| `docs/research/02_sharp_blunt_burn.md` | Knife wounds, blunt soft tissue, facial fractures, hammer depressed fracture, scalp haematomas, burns | `[R1-02 §x]` |
| `docs/research/03_bleeding_vessels.md` | Bleed rates per vessel, spurt physics, clotting timeline, internal bleeding volumes, blood optics and colours, drops, rivulets, pools, drying | `[R1-03 §x]` |
| `docs/research/04_neuro_death_eyes.md` | Brainstem collapse, 10–15 s heart rule, pneumothorax/haemothorax physiology, eye states in dying and death | `[R1-04 §x]` |
| `docs/research/05_body_anatomy_reference.md` | Landmarks, bone dimensions and cortex thickness, bone colours | `[R1-05 §x]` |
| `docs/research/06_game_gore_tech.md` | Rendering architecture, cross-section colours, fracture assets, gibs | `[R1-06 §x]` |
| `docs/research2/01–03` | Brain-injury deficits, reactions to being hit, falling and ragdoll biomechanics | `[R2-0x §y]` |

---

## 0. Read this first

### 0.1 Method and limits (important)

- **No web research was possible in this session.** The first `WebSearch` call returned "this session has used its web search budget (200 of 200 WebSearch calls)". The shared budget had been used up by earlier agents in this workflow. Zero searches succeeded.
- `WebFetch` was not attempted. The brief states that the network policy blocks it, and round one documented `EGRESS_BLOCKED` on every medical domain.
- **Consequence: this document contains no `[S#]` (sourced this session) values.** Every new value is `[K]` (my own knowledge of the standard forensic-pathology, trauma-surgery, ophthalmology, orthopaedic and bloodstain-pattern literature, with a confidence grade) or `[E]` (an engineering estimate or derivation, with the working shown). Where round one already sourced a value, I cite that round-one section instead of restating it.
- The references in §20 are the standard texts and papers the `[K]` values come from. **None were opened in this session.** Before any number is shown to the player as a measurement (for example a "forensic mode" readout), a human should check the §18 list against them.
- No web content was read, so there was no exposure to prompt injection. See §19.

### 0.2 Tags

| Tag | Meaning |
|---|---|
| `[K](H)` | Own knowledge, textbook-standard, repeated across many references. High confidence. |
| `[K](M)` | Own knowledge, right order of magnitude; the exact figure may differ by ±30–50 %. |
| `[K](L)` | Own knowledge, plausible, weak basis. Treat as a starting value for tuning. |
| `[E]` | Engineering estimate or derivation for the game. The arithmetic or anchor is shown. |
| `[R1-0x §y]` / `[R2-0x §y]` | Value taken from a round-one or round-two document; its own tag applies. |

### 0.3 Conventions

- **Reference body**: male, 75 kg, 1.75 m, blood volume 5.0 L, head mass 4.5–5.0 kg, intracranial volume 1,400–1,600 mL (brain 1,250–1,400 g, CSF ~150 mL, blood ~100–150 mL) `[K](H)`.
- **Colours**: approximate sRGB hex under neutral daylight (D65). They are starting values. Tune under the game's lighting and tonemapper. Light-to-medium skin unless stated.
- **Roughness**: Godot `StandardMaterial3D` / shader `ROUGHNESS` scale, 0 = mirror, 1 = fully matte. "Wet" means covered by a film of blood, plasma or tissue fluid.
- **SSS radius**: approximate visible light-diffusion distance for Godot's subsurface-scattering depth, in mm `[E]`.
- **t = 0**: the moment of injury. "Living" means the circulation is running; "dead" means cardiac arrest has occurred.
- **Probabilities** are per event unless stated. "Fragments" means pieces ≥ 2 mm unless stated.

### 0.4 What the player's weapons can actually produce (scope filter)

Not every morphology below can be produced by every weapon. Use this matrix to decide which recipes are reachable `[E]` from `[K](M)` wound-ballistics and forensic teaching.

| Morphology (section) | Handgun | Rifle | Shotgun (buck/bird/slug) | Knife | Fist / kick / stomp | Hammer | Fire |
|---|---|---|---|---|---|---|---|
| Head burst, brain evisceration (§2–3) | Contact magnum only, rare | Yes (energy-dependent) | Yes at ≤ 1–3 m; always at contact | No | No | No | No |
| Face / jaw avulsion (§4) | Rare (submental contact) | Yes | Yes | Only by prolonged cutting | No | No (comminution yes, avulsion no) | No |
| Globe rupture (§5) | Yes | Yes | Yes (pellets) | Yes (penetrating) | Rare (rim protects); thumb gouge yes | Yes (face fits the orbit) | Late (heat) |
| Globe luxation / enucleation (§5) | Rare | Yes (orbital burst) | Yes | By deliberate cutting | Thumb gouge (rare) | Rare | No |
| Scalp avulsion / degloving (§6) | No | Tangential only | Tangential, close range | Yes (flaps, scalping) | Shear stomp: closed degloving | Tangential blows: flaps | No |
| Comminuted / crushed skull (§7) | Rifle-like only at contact | Yes | Yes | No | Stomp against floor: yes | Yes (repeated blows) | No |
| Open long-bone fracture (§8) | Yes | Yes | Yes | No | Stomp/kick: tibia possible | Yes (tibia, forearm) | No |
| Rib fractures / flail / sternum (§9) | Single ribs | Yes | Yes | Rib notching only | Yes | Yes | No |
| Heart, lung, liver, spleen, kidney wounds (§10–12) | Yes | Yes | Yes | Yes | Blunt: spleen, liver, lung contusion, cardiac contusion | Blunt: as fist, stronger | No |
| Bone/teeth secondary missiles (§13) | Few | Many | Many | No | Teeth only (in mouth) | Skull chips into brain | No |
| Neck wounds, near-decapitation (§14) | Yes (partial) | Yes | Contact: near-decapitation | Yes (cut throat; decapitation only with prolonged work, through a disc space) | No | No | No |
| Scene bloodstain patterns (§15) | Yes | Yes | Yes | Yes (cast-off, arterial) | Impact spatter, expirated | Cast-off, impact spatter | No (heat alters stains) |

---

## 1. Exposed tissue library (colour, wetness, texture, consistency, ageing)

Every later section refers to this library. It extends `[R1-06 §5.4]` and `[R1-05 §8.3]` with time-dependent colours, roughness, SSS and texture notes, and adds organs, eye, mouth and airway tissues that round one did not cover.

### 1.1 Colour and surface table

Columns: fresh = first minutes of exposure while living. 30–60 min = exposed in a living body (still perfused, periodically re-wetted by ooze). Dead/drying = 2–6 h after death in room air, not re-wetted.

| Tissue | Fresh (hex) | Exposed 30–60 min, living | Dead, drying 2–6 h | Roughness wet → dry | SSS (mm) | Surface and texture notes | Tag |
|---|---|---|---|---|---|---|---|
| Dermis, cut edge | `#E3B7A6` | `#D9A796` | `#A8745E` (parchment brown) | 0.45 → 0.75 | 1.0 | Dense pink-white band. Thickness 1–2 mm on the face, 2–3 mm on the scalp and limbs, 3–4 mm on the back, 0.5 mm on eyelids | `[R1-06 §5.4]`; ageing `[K](M)` |
| Subcutaneous fat | `#EBD27E` | `#E2C56C` | `#CDAA55` | 0.30 → 0.55 | 3–5 | Lobules 3–10 mm in the superficial layer, 1–3 mm and flatter in the deep layer. Fine pink septa with capillaries. Greasy gloss. Lobules bulge 2–10 mm out of a fresh cut. Firms and turns more opaque as the body cools below ~30 °C | `[R1-06]`; texture `[K](M)` |
| Galea aponeurotica (scalp) | `#E0DAD2` | `#D8D0C4` | `#C2B39C` | 0.25 → 0.60 | 0.5 | Tough white fibrous sheet 1–2 mm thick under the scalp's fat layer. Undersurface of an avulsed scalp | `[K](M)` |
| Deep fascia | `#E4E2DC` | `#DAD6CC` | `#C8BCA2` (translucent yellow parchment) | 0.20 → 0.50 | 0.5 | Silvery sheet with a cross-hatched fibre sheen. 0.3–1 mm; fascia lata 1–2 mm; iliotibial tract 2–3 mm. Muscle bulges ("herniates") through tears | `[K](M)` |
| Skeletal muscle | `#8E2A2A` (deoxygenated myoglobin + blood) | `#A5362F` ("bloom": oxymyoglobin on the air-exposed surface) | `#6B3A2E` brown (metmyoglobin), crust `#4A2A22` | 0.25 → 0.60 | 1–2 | Grain depends on cut direction (§1.2). Epimysium gives a thin glossy film on intact bellies | `[R1-06]`; bloom/brown `[K](M)` (meat-science colour chemistry) |
| Tendon | `#ECE8DE` | `#E2DCCC` | `#C9B98E` translucent amber | 0.20 → 0.50, **anisotropic** along fibres | 0.5 | Silvery cords 2–10 mm wide. Collagen crimp gives a banded "watered silk" sheen that moves with the view angle. Firm, does not tear by hand | `[K](M)` |
| Ligament / joint capsule | `#E6E2D8` | `#DCD6C8` | `#C4B494` | 0.30 → 0.60 | 0.5 | Duller than tendon, less banding | `[K](M)` |
| Peripheral nerve | `#EDE6D2` | `#E3DAC2` | `#C8B894` | 0.35 → 0.60 | 1.0 | Cream-white cord with fine longitudinal striation and one thin red surface vessel (vasa nervorum). Cut end: fascicles "pout" 1–2 mm beyond the sheath | `[K](M)` |
| Artery wall (cut section) | `#E8D2C8` ring | same | `#C9A89A` | 0.30 | 0.5 | Round, firm, thick-walled (wall ≈ 10–15 % of outer Ø). Visibly pulsates while alive | `[R1-06]`, `[K](M)` |
| Vein (in situ) | `#4E3A5E` (dark blood seen through a thin wall) | same | `#3A2A3E` | 0.25 | — | Thin-walled, flat ribbon when empty, round and bulging on straining | `[K](M)` |
| Cortical bone | `#E9DFCC` | `#EFE7D6` (chalky) | `#F1EBDF` | 0.50 → 0.80 | 0.3 | Fracture face is matte and granular. Fresh sawn/cut face is smoother | `[R1-05 §8.3]`; drying `[K](M)` |
| Periosteum | `#E6CFC4` | `#DCC0B2` | `#B8987E` | 0.30 → 0.60 | 0.5 | Thin glossy sleeve; bleeds from pinpoints when stripped | `[R1-05]` |
| Cancellous bone, red marrow | `#B5524A` (range to `#8C2A24`) | `#9A3E36` | `#5E2A22` | 0.40 → 0.70 | 1.0 | Honeycomb; trabeculae 0.1–0.3 mm, pores 0.5–1.5 mm; oozes blood continuously while alive | `[R1-05]`, `[R1-06]` |
| Yellow marrow (long-bone shaft) | `#E4C36A` | `#D9B45A` | `#B8923E` | 0.35 → 0.55 | 3 | Greasy yellow fat plug, streaked red; sheds fat droplets that float on blood as bright yellow beads 0.5–3 mm | `[R1-05]`, `[K](M)` |
| Articular cartilage | `#DDE3E6` | `#D5DBDC` | `#C8C4B0` | 0.10 → 0.40 | 1.0 | Bluish-white, very smooth, glassy | `[R1-05]` |
| Costal cartilage | `#CBD5D8` | — | `#BDB8A4` | 0.20 → 0.45 | 1.5 | Translucent bluish; cuts cleanly, does not shatter; calcified flecks in older adults | `[R1-05]` |
| Brain surface (pia intact) | `#C9A79E` + vessel net | — | `#9E8078` | 0.20 → 0.50 | 2–3 | Gyri 8–12 mm wide, sulci 1–3 mm. Surface veins dark blue-purple `#4A3050`, arteries red `#B03030` | `[R1-06]`; vessels `[K](M)` |
| Grey matter, cut | `#B79C94` | — | `#8A6E66` | 0.20 → 0.50 | 2–3 | Cortical ribbon 2–4 mm; deep grey nuclei (basal ganglia, thalamus) as grey islands in white | `[R1-01]` |
| White matter, cut | `#E6DACA` – `#EDE3D8` | — | `#BFAE98` | 0.20 → 0.50 | 2–3 | Cream, faintly glossy; shows pinpoint red petechiae after impact | `[R1-01]`, `[R1-06]` |
| Pulped brain + blood | `#9E5A55` | — | `#6A3A34` crust | 0.15 → 0.55 | 2 | Semi-fluid paste; see §1.4 consistency | `[R1-01]` |
| Contused cortex | streaks `#6A1A1E` in `#B79C94` | darkens | `#4A1A1A` | — | — | Haemorrhagic streaks perpendicular to the surface, crest of gyri first | `[K](M)` |
| Subarachnoid blood | `#5A0A10` film | — | `#3A0A0C` | 0.15 | — | Thin dark film following the sulci | `[K](M)` |
| Dura mater | `#D9D6CE` | — | `#BDB19C` | 0.35 → 0.60 | 0.5 | Tough, 0.5–1 mm; inner surface glossy; middle meningeal vessels in grooves on the bone side | `[R1-05]` |
| CSF | colourless, IOR 1.335 | — | leaves no visible residue | 0.05 | — | Water-like, viscosity ~0.7–1 mPa·s at 37 °C. Mixed with blood: watery pink, does not clot (§1.4) | `[K](H)` |
| Liver, capsule surface | `#6E2C22` | `#62281F` | `#4E2219` | 0.15 → 0.45 | 0.5–1 | Mirror-smooth capsule. Faint 1–2 mm lobular stipple visible under it | `[K](M)` |
| Liver, cut / torn surface | `#5A231B` | `#4E1E17` | `#3E1A14` | 0.25 → 0.50 | 0.5 | Friable, granular. Portal triads as small pale-rimmed holes 1–5 mm. Bile staining in places (below) | `[K](M)` |
| Gallbladder bile / hepatic bile | `#4E5A1E` dark green / `#B8862A` golden | — | brown-green crust | 0.10 | — | Leaks as an oily green-gold fluid that does not clot and stains tissue yellow-green | `[K](M)` |
| Spleen, capsule | `#5E4A5C` slate purple-grey | `#56425A` | `#463444` | 0.20 → 0.45 | 0.5 | Thin; wrinkles when the organ empties | `[K](M)` |
| Spleen, pulp (cut / torn) | `#5A1624` | `#4E1220` | `#3E1018` | 0.30 → 0.55 | 0.5 | Very soft dark red pulp that scrapes off on a blade; grey dots ~0.5 mm (white pulp) | `[K](M)` |
| Kidney, surface | `#7B3B2E` | `#70362A` | `#5A2C22` | 0.20 → 0.45 | 0.5 | Smooth; the thin capsule peels easily | `[K](M)` |
| Kidney, cut | cortex `#8C4636`, medulla `#5E2426`, sinus fat `#E8C66A` | — | darker | 0.25 | 0.5 | Cortex 7–10 mm pale band; medulla as striated darker pyramids; white pelvis and calyces | `[K](M)` |
| Lung, aerated | `#D9A5A0` + anthracotic `#2B2626` lines | `#C8908C` | `#9A6A68` | 0.30 → 0.55 | 2 | Spongy, crepitant, light (floats in water). Black carbon pigment outlines 1–2 cm polygonal lobules in most urban adults. Cut surface exudes pink froth | `[K](M)` |
| Lung, collapsed (pneumothorax) | `#8A3A4A` dusky plum | — | `#6A2E3A` | 0.25 | 1 | Rubbery, shrunk toward the hilum, no crepitus | `[K](M)` |
| Lung, contused | `#5A1A2A` dark plum | darkens | `#3E141E` | 0.25 | 0.5 | Firm, heavy, airless, "liver-like"; sharply or vaguely demarcated from pink lung | `[K](M)` |
| Myocardium | `#7A2A28` (darker, browner than skeletal muscle) | `#6E2624` | `#5A2220` | 0.30 → 0.55 | 1 | Coarse interlacing spiral bundles; glossy epicardium over it | `[K](M)` |
| Epicardial fat | `#E8C868` | `#E0BE5C` | `#C8A24C` | 0.30 | 3 | Fills the atrioventricular and interventricular grooves; coronary arteries run in it as pale cords 2–4 mm | `[K](M)` |
| Pericardium (parietal) | `#D8D0C8`, alpha 0.5–0.7 | — | opaque `#C8BCA8` | 0.20 → 0.45 | 1 | Fibrous, 1–2 mm, semi-translucent: the heart or contained blood shows through | `[K](M)` |
| Trachea | rings `#DCE0DC`, mucosa `#D8908A` | — | mucosa `#A86A64` | 0.15 / 0.20 | 1 | 16–20 C-shaped rings; lumen 15–20 mm; glossy mucosa | `[K](M)` |
| Oesophagus | outer `#B0605A`, mucosa `#D8B0A8` | — | — | 0.20 | 1 | Collapsed muscular tube behind the trachea | `[K](M)` |
| Tongue | dorsum `#C8A0A0` (papillary), cut body `#9A3A40` | — | `#6A2A2E` | 0.30 / 0.25 | 1.5 | Interlacing muscle with no single fibre direction; papillae give a velvety matte dorsum | `[K](M)` |
| Tooth | enamel `#EFEBDD`, dentin `#E6D5A8`, pulp `#C05A5A` | — | pulp dries dark `#6A2A2A` | enamel 0.15 | enamel 0.5 | Enamel translucent at edges, fractures with glassy conchoidal faces | `[K](M)` |
| Eye tissues | sclera `#F2EEE6`, uvea `#3A2420`, lens `#F4E8C0`, retina `#D8B8B0`, vitreous clear gel IOR 1.336 | — | sclera dries to `#D8CFC0`; see `[R1-04 §11.6]` | sclera 0.15 | sclera 1.5 | See §5 | `[K](M)` |
| Blood clot / serum | `#4A060C` glossy / `#E6D08A` translucent | — | — | 0.10 | — | See `[R1-03 §7.6, §9.3]` for all blood colours | `[R1-03]` |
| Haematuria (bloody urine) | `#C04A4A` (diluted) | — | brown ring | 0.05 | — | Kidney/bladder injury; released at death (sphincter relaxation) | `[K](M)` |

### 1.2 Muscle: cut across fibres vs along fibres

| Property | Cut **across** fibres (transverse) | Cut **along** fibres (longitudinal) | Oblique | Tag |
|---|---|---|---|---|
| Surface look | "End grain": polygonal fascicles 1–3 mm across, outlined by a fine pale network of perimysium (`#C9A9A0`), slightly granular, each fascicle a darker red dot | "Wood grain": parallel streaks; fascicle bands 1–3 mm wide, fine fibre striation along them | Elongated polygons | `[K](M)` |
| Gape of a partial-depth cut | Wide. Gape width ≈ 0.5–1.0 × cut depth, because fibres retract away from the cut on both sides | Narrow. Gape ≈ 0.1–0.2 × depth; the edges stay close | Intermediate | `[E]` from `[K](M)` |
| Full transection of a belly | Ends retract; gap 20–40 % of the muscle's resting length in a living, toned muscle (e.g. biceps 3–8 cm); the proximal stump bunches into a bulge | — | — | `[E]` |
| Bleeding | Many small vessels cut: diffuse brisk ooze from the whole face | Fewer vessels cut: less bleeding | — | `[K](M)` |
| Motion (living) | Cut ends twitch and fasciculate for seconds; touching the blade to exposed muscle triggers local contraction | Same | — | `[K](M)` |
| Motion (dead) | A sharp tap raises a local "idiomuscular" ridge 1–2 cm long for a few seconds, for ~1–3 h after death (supravital reaction; see `[R1-04 §12.7]`) | Same | — | `[K](M)` |
| Texture authoring | Tri-planar noise with a Voronoi cell pattern (cell 1–3 mm) projected along the fibre axis | Anisotropic streak noise aligned to the fibre tangent | Blend by the angle between cut normal and fibre tangent | `[E]` |

Fibre direction matters for the shader: store a per-vertex (or per-voxel) fibre tangent for every muscle mesh in rest space. Use it to pick the texture, the gape factor and the anisotropic highlight direction `[E]`.

### 1.3 Identifying structures in an open wound (arteries, veins, nerves, tendons)

| Feature | Artery | Vein | Nerve | Tendon | Tag |
|---|---|---|---|---|---|
| Shape in situ | Round, firm tube; keeps its lumen when empty | Flat ribbon when empty; round only when full | Solid round/flat cord | Solid flat/round cord | `[K](H)` |
| Colour | Pale pink-white wall (`#E8D2C8`) | Blue-purple (`#4E3A5E`), contents show through | Cream-white, one fine red surface vessel | Silvery white, banded sheen | `[K](M)` |
| Motion (living) | Pulsates at the heart rate; diameter change 5–10 % per beat; a whole looping artery "writhes" slightly | Fills and empties with breathing; bulges on straining or screaming | None | Slides when the related joint or muscle moves (fingers move with it) | `[K](M)` |
| Cut end | Retracts 1–3 cm into the tissue, goes into spasm, lumen shrinks to a pinhole in muscular arteries (`[R1-03 §4.4]`); intima curls in | Collapses; end lies flat; may suck air at the neck | Fascicles pout 1–2 mm; no lumen; no bleeding except the small surface vessel | Retracts 1–4 cm (flexors most); frayed collagen "paintbrush" end if torn rather than cut | `[K](M)` |
| Bleeding | Bright red, pulsatile jet synchronised with the pulse | Dark red, steady welling | Almost none | None | `[R1-03 §6.1]` |
| Sizes in the limbs (outer Ø) | Femoral 8–10 mm, brachial 4–5, radial 2–3, carotid 6–8 | Femoral 10–14, cephalic/basilic 4–8 (superficial, under skin), jugular 10–20 | Sciatic 10–20 × 5 mm (flattened), median 4–6, ulnar 3–5, radial 3–4, vagus 2–4 | Achilles 5–7 mm thick × 12–15 wide, finger flexors 3–5 | `[K](M)`; vessels `[R1-03 §11]` |
| Clue for the player | "The thing that throbs and spurts" | "The dark blue flat thing that leaks steadily" | "The white string that doesn't bleed" | "The shiny white strap that moves the fingers" | `[E]` |

Neurovascular bundles travel together (artery + 1–2 veins + nerve in one sheath): brachial bundle along the medial arm, femoral in the groin, carotid sheath in the neck. A deep wound that cuts an artery at one of these sites usually also cuts the accompanying vein and often the nerve `[K](H)`. Distal loss of function (hand/foot drop, numbness) follows nerve section immediately; see `[R2-02]` for behaviour.

### 1.4 Mechanical consistency (for soft bodies, particles, tearing and "feel")

| Tissue | Density (g/mL) | Stiffness (small strain) | Failure / behaviour | Everyday analogue | Tag |
|---|---|---|---|---|---|
| Skin | 1.10 | Nonlinear: 0.1–1 MPa at low strain, 10–100 MPa near failure | Tensile strength 5–30 MPa, failure strain 30–70 %. The toughest soft tissue: often holds shattered bone together inside a "bag" | Thin leather | `[K](M)` |
| Subcutaneous fat | 0.90–0.92 | E ≈ 1–4 kPa | Smears and fractures between septa; lobules pop out | Soft butter / custard (cold body: firmer) | `[K](M)` |
| Skeletal muscle | 1.06 | Passive E ≈ 10–50 kPa along fibres (relaxed) | Tears between fascicles; tensile strength ~0.1–0.5 MPa | Raw steak | `[K](M)` |
| Tendon | 1.10–1.15 | E ≈ 1–1.5 GPa in tension | Tensile strength 50–100 MPa; cannot be torn by hand | Nylon strap | `[K](M)` |
| Brain | 1.04 | E ≈ 1–3 kPa (shear modulus ~0.3–1.5 kPa), strongly viscoelastic | Tears at very low stress; flows through small openings | Soft tofu / set custard | `[K](M)` |
| Pulped brain | 1.04 | Yield stress ~50–200 Pa `[E]` | Paste that holds a clump shape, smears, stretches into strings with blood | Thick yoghurt / porridge | `[E]` |
| Liver | 1.06 | E ≈ 4–6 kPa (clinical elastography normal < ~7 kPa) | Low tensile strength; tears in straight and stellate fissures; capsule strips | Firm jelly / raw liver | `[K](M)` |
| Spleen | 1.05 | Similar to liver, pulp softer | Pulp smears; capsule tears | Blood-soaked sponge cake | `[K](L)` |
| Kidney | 1.05 | E ≈ 5–10 kPa | Capsule tough; parenchyma splits radially toward the hilum | Firm raw liver | `[K](L)` |
| Lung (inflated) | 0.25–0.40 | Very compliant, elastic | Tolerates stretch; tears but does not burst | Foam sponge | `[K](M)` |
| Myocardium | 1.06 | Like muscle, stiffer in contraction | Thick LV wall closes small stab tracks | Dense raw steak | `[K](M)` |
| Cortical bone | 1.9 | 17–20 GPa | Brittle; sharp edges that can cut skin and gloves | Porcelain / hard plastic | `[R1-05 §8.2]` |
| Cancellous bone | 1.0–1.1 (marrow-filled) | 0.1–2 GPa (apparent) | Crushes; vertebral wedge collapse | Pumice soaked in jam | `[R1-05]`, `[K](M)` |
| Teeth (enamel) | 2.9 | ~80 GPa | Very brittle; glassy fragments | Glass | `[K](M)` |
| Clotted blood (fresh) | 1.06 | Soft gel, G ~ 10–100 Pa | Holds shape, wobbles, breaks into lumps | Blackcurrant jelly | `[K](M)` |
| CSF + blood mixture | 1.01–1.03 | Liquid, ~1 mPa·s | Does not clot at low blood fraction; spreads further and thinner than blood | Diluted cordial | `[K](M)` |

**Why solid organs burst but lungs and muscle do not.** Tissue damage from the temporary cavity depends on how far the tissue can stretch before failing. Lung, skeletal muscle, bowel wall and skin are elastic and survive large stretches, so a rifle cavity leaves a relatively narrow damaged zone. Liver, spleen, kidney and brain are inelastic, so the same cavity splits them into stellate fissures or pulp. The skull adds confinement (see §2–3) `[K](H)` (Fackler; Kneubuehl).

### 1.5 Ageing of exposed tissue (timeline)

| Time after exposure | Living body (perfused) | Dead body (room air, 20 °C, 50 % RH) | Tag |
|---|---|---|---|
| 0–2 min | All surfaces wet and glossy (roughness 0.1–0.3); fresh blood film | Same, but no new ooze | `[K](M)` |
| 2–10 min | Clot glazes small vessels; muscle surface starts to bloom brighter red | Surface film thins; specular falls | `[K](M)` |
| 10–30 min | Muscle bloomed (`#A5362F`); fat edges matte; exposed bone chalky at edges | Muscle surface tacky; fat matte; fascia and tendon lose shine; brain surface skin forms | `[K](M)` |
| 30–120 min | Serous exudate (yellow-pink) and fibrin film start to coat the wound (living only) | Muscle darkens to brown-red; bone ivory-white and dry; exposed dura and fascia parchment-like and translucent | `[K](M)` |
| 2–6 h | Swelling of wound margins (living only) | Exposed wound margins and abrasions dry to dark brown parchment; pulped brain forms a grey-brown crust | `[K](M)` |
| 6–24 h | — | Deep dark-brown leathery surfaces; cracking of thin layers; corneal and scleral changes per `[R1-04 §11.6]` | `[K](M)` |

### Simulation parameters (tissue library)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `tissue_palette` | §1.1 table | sRGB | One material per tissue ID; lerp fresh → 30–60 min → dead by exposure age | `[K](M)`, `[R1]` |
| `exposure_age_rate_living` | 0.3–0.5 × dead rate | × | Re-wetting by ooze slows drying | `[E]` |
| `muscle_bloom_time` | 10–30 | min | Lerp `#8E2A2A` → `#A5362F` on air-exposed muscle | `[K](M)` |
| `muscle_brown_time_dead` | 2–6 | h | → `#6B3A2E` | `[K](M)` |
| `muscle_gape_factor_across` | 0.5–1.0 | × depth | Width of gape for a cut across fibres | `[E]` |
| `muscle_gape_factor_along` | 0.1–0.2 | × depth | | `[E]` |
| `muscle_transection_retraction` | 0.2–0.4 | × rest length | Living, toned muscle; 0.05–0.1 when dead and flaccid | `[E]` |
| `tendon_retraction_cut` | 10–40 | mm | Flexors at the upper end | `[K](M)` |
| `artery_retraction_cut` | 10–30 | mm | Plus spasm per `[R1-03 §4.4]` | `[K](M)` |
| `nerve_fascicle_pout` | 1–2 | mm | Cut-end geometry | `[K](M)` |
| `fat_lobule_bulge` | 2–10 | mm | Displacement of fat lobules out of a fresh cut | `[K](M)` |
| `fat_droplet_on_blood` | 0.5–3 | mm | Yellow specular beads when yellow marrow or fat is disrupted | `[K](M)` |
| `brain_yield_stress_pulped` | 50–200 | Pa | For a particle/SPH paste or for a mesh "smear" threshold | `[E]` |
| `csf_blood_mix_clots` | false when blood fraction < ~30 % | bool | CSF-diluted blood spreads 1.5–2× the area of pure blood and dries paler | `[E]` |
| `sss_radius` | per §1.1 | mm | Fat and brain largest, liver/spleen smallest | `[E]` |

### Visual/behavioural checklist (tissue library)

- Every exposed tissue is identifiable at a glance by colour and texture: yellow lobulated fat, dark red grained muscle, silvery fascia and tendon, ivory bone with a red or yellow core, cream nerve without bleeding, pulsating pale artery, flat blue vein.
- Muscle cut across its fibres gapes wide and shows a stippled end-grain; muscle cut along its fibres stays narrow and streaky.
- Exposed muscle turns brighter red within half an hour in air, then brown after death over hours. Fat turns matte. Bone dries chalky white.
- Brain is visibly the softest thing in the body: it sags, smears, and extrudes like thick paste; CSF makes blood watery and pink.
- Solid organs (liver, spleen, kidney) crack and split; lungs and muscle stretch and tear.

---

## 2. Close-range shotgun wounds of the head

Round one gives the shotgun pattern versus range and a qualitative note that contact shots destroy the head `[R1-01 §9]`. This section quantifies the destruction.

### 2.1 Energy budget model for head bursting (shared by §2 and §3)

- The closed skull contains ~1.5 L of incompressible tissue and fluid. Any energy that the projectile deposits as a radial pressure pulse (temporary cavity) has nowhere to go, so above a threshold the vault bursts along fracture lines and sutures and the contents are ejected `[K](H)` (Kneubuehl; DiMaio).
- Typical deposited energies inside the head `[E]`, from round-one ammunition data `[R1-01 §1]`:

| Round | Impact energy (J) | Fraction deposited in a 15 cm head | Deposited (J) | Expected result |
|---|---|---|---|---|
| .22 LR | 140–180 | 50–100 % (often no exit) | 100–180 | Hole, retained bullet, no burst |
| 9 mm FMJ | 470–570 | 15–40 % | 70–230 | Holes, radial cracks, no burst |
| 9 mm JHP / .45 | 470–570 | 30–60 % | 150–340 | Larger track, more cracks, no burst |
| .357 Mag contact | ~750 + gas | 30–60 % + gas | 250–450 + gas | Stellate entrance, extensive cracks; rarely partial burst |
| 5.56 M193 | ~1,750 | 15–60 % (depends on yaw/fragmentation inside the head) | 250–1,050 | From a narrow perforation to a full burst |
| 7.62×39 | ~2,000 | 10–40 % | 200–800 | Often perforation with large exit; burst when it yaws or hits thick bone |
| 7.62×51 / .30-06 | 3,300–3,900 | 20–60 % | 650–2,300 | Burst common; Krönlein-type evisceration possible |
| 12 ga 00 buck, ≤ 1 m | ~2,500 | 50–80 % (shot column acts as one mass) | 1,250–2,000 | Burst certain |
| 12 ga birdshot, ≤ 1 m | 1,900–2,500 | 60–90 % (shot stays in the head) | 1,150–2,250 | Burst certain |
| 12 ga slug (28 g, ~480 m/s) | ~3,200 | 40–70 % | 1,300–2,250 | Burst certain; Krönlein-type evisceration common |

- **Game rule** `[E]`: `E_dep` = impact energy × deposit fraction, plus a contact-gas bonus. Thresholds: `E_dep ≥ 500–700 J` → vault burst; `≥ 1,000 J` → partial brain evisceration (30–70 %); `≥ 1,500 J` → evisceration of 50–100 % with a chance of one or both hemispheres leaving largely intact (Krönlein). This replaces the pure velocity switch in `[R1-01 §5 burst_threshold]` with a continuous rule that reproduces the same outcomes.
- **Contact gas** `[E]`: smokeless propellant yields roughly 0.8–1.0 L of gas per gram at standard conditions `[K](M)`. A 12-gauge shell carries ~1.6–2.3 g of powder (1.3–2.3 L of gas); a 9 mm cartridge ~0.3–0.4 g (0.25–0.4 L). At contact, the gas enters the wound and adds to the burst. Suggested bonus to `E_dep`: handgun +50–150 J, magnum +150–300 J, rifle +300–600 J, shotgun +400–800 J `[E]` (tuning device, not a measured quantity).
- **Sanity check** `[E]`: accelerating 1 kg of brain and bone to 30 m/s takes ½·1·30² = 450 J. So 1,000–2,000 J deposited is enough to eject most of the cranial contents at tens of m/s, and handgun deposits of 100–300 J are not.

### 2.2 Destruction patterns by site (12-gauge, contact to ~1 m)

| Site / angle | Entrance | Skull | Brain | Face and eyes | Main defect ("exit") | Tag |
|---|---|---|---|---|---|---|
| **Intraoral**, muzzle in the mouth, angled up/back | Inside the mouth (palate or oropharynx). Lips: intact, or radial splits at the corners of the mouth 1–5 cm from gas; cheeks may be torn or blown out | Palate and skull base shattered; vault burst into 20–60+ fragments; sutures sprung | 50–100 % ejected; remainder pulped | Facial skin often largely continuous but loose, hanging over shattered bones like a "mask"; eyes proptosed or ruptured from orbital-roof burst (30–60 %); blood from nose and ears | Vertex / parieto-occipital crater 10–20 cm, or the whole upper vault missing; scalp split into 3–8 radial flaps 5–15 cm long | `[K](M)`, `[E]` |
| **Submental** (under the chin), muzzle up and forward | Under-chin entrance 3–5 cm, soot, stellate tears | Mandible symphysis shattered; maxilla, nasal bones, orbital floors destroyed; frontal bone burst if the column enters the anterior fossa | 0–100 %: depends on whether the column enters the cranial cavity. Anterior trajectory: brain spared or only frontal lobes | Lower face, nose and often the eyes avulsed; open cavity from chin to forehead; tongue shredded | Forehead / frontal crater or the entire mid-face missing | `[K](M)` |
| **Temple** contact | 3–5 cm ragged, star-shaped tears 2–6 cm, soot, muzzle imprint (`[R1-01 §3.5]`) | Temporal/parietal burst; 10–40 fragments; opposite side of the vault missing | 30–80 % ejected, mostly from the far side | Both eyes often proptosed, periorbital haemorrhage in seconds if the heart still beats; ears torn | Contralateral parieto-temporal crater 8–15 cm, or larger | `[K](M)`, `[E]` |
| **Forehead** contact | 3–5 cm stellate | Frontal and vault burst; the top of the head may be removed as a "cap" of scalp and bone | 40–90 % ejected | Face distorted; orbital roofs shattered; eyes displaced, often ruptured | Parieto-occipital crater 10–20 cm | `[K](M)` |
| **Occiput** contact | 3–5 cm stellate | Occipital and vault burst; skull base cracked | 30–80 % ejected forward/upward; brainstem and cerebellum destroyed | Face may remain recognisable but swollen and misshapen; eyes proptosed | Frontal or facial defect | `[K](M)` |
| **Near contact to 1 m**, any site | Single round hole 2–4 cm (`[R1-01 §9]`), wad often inside | As contact, minus the gas-driven scalp tears at the entrance | As contact | As contact | As contact | `[R1-01 §9]`, `[K](M)` |
| **1–3 m, buckshot** | 9 pellets in a 3–8 cm group: separate 6–9 mm holes, some confluent | Multiple perforations; radial cracks link them; partial burst possible at the lower end of the range | Several separate tracks; 0–30 % ejected | Pellet holes in the face and eyes | Several exits or a combined defect | `[K](M)`, `[E]` |
| **Slug, ≤ 10 m** | 18–20 mm round hole | Krönlein-type burst | 50–100 % ejected; hemispheres may leave largely intact | Face distorted | Large crater | `[R1-01 §5.5]`, `[K](M)` |

### 2.3 What remains of the head

- **"The head collapses."** When most of the vault is fragmented, the tough scalp often keeps the fragments together. The head loses its rigid shape: it looks widened and flattened on the side it rests on, feels like a bag of gravel when moved, and grates (bone crepitus) `[K](M)`.
- **The face becomes a loose mask.** Without bony support the facial features sag and shift: the eyes sit at different heights, the nose flattens or deviates, the mouth hangs open and the jaw may be dislocated `[K](M)`.
- **Scalp flaps**: 3–8 radial flaps with irregular, torn (not abraded) margins, everted, hair matted with blood and brain `[E]` from `[K](M)`.
- **Residual brain**: the brainstem and cerebellum are often still present in the posterior fossa (except in occipital shots); the remaining cerebrum is pulped with bone chips and hair driven into it `[K](M)`.
- **Blood**: if the heart is still beating it pumps into the open cranium and out of the defect for 1–10 min (`[R1-04 §2.4]`); blood runs from the nose, mouth and ears; a large pool (§15.6) forms under the head.

### 2.4 Ejecta: fragments, brain, spatter

| Quantity | Value | Unit | Notes | Tag |
|---|---|---|---|---|
| Vault fragments (≥ 2 mm) | contact 12 ga: 20–80; slug: 15–50; buck 1–3 m: 3–20 | count | Size distribution log-normal, median 15–25 mm, largest plates 40–100 mm | `[E]` from `[K](M)` |
| Fraction of fragments that leave the head | 20–60 % | — | The rest stay inside the scalp bag | `[E]` |
| Brain ejected | see table §2.2 | % of ~1,350 g | Clumps 5–200 g; fine paste; occasionally a hemisphere-sized mass (400–600 g) with slugs/rifles | `[K](M)`, `[E]` |
| Launch speed, fine droplets and mist | 20–60 | m/s | Forward spray is faster than back-spray `[R1-01 §7]` | `[R1-01 §7]`, `[E]` |
| Launch speed, clumps 5–50 g | 10–40 | m/s | | `[E]` |
| Launch speed, large masses and plates > 50 g | 5–20 | m/s | | `[E]` |
| Ejecta range indoors | fine 0.5–3 m; clumps 1–5 m; plates 1–8 m | m | Limited by walls and ceiling; ceiling deposits common when the muzzle is angled up (intraoral, submental) | `[E]` from `[K](M)` |
| Ejecta range outdoors | up to 10–15 | m | Largest bone plates and brain masses | `[E](L)` |
| Hair and scalp pieces | 0–10 | pieces | Scalp tags 1–5 cm with hair | `[E]` |
| Back-spatter onto the shooter's hand/weapon | Heavy (contact) | — | Blood, brain particles and bone dust on the muzzle, hand and forearm | `[R1-01 §7.1]`, `[K](M)` |
| Wad (contact to ~1.5 m) | Inside the head or among the ejecta | — | `[R1-01 §9]` | `[R1-01]` |
| Time course | Burst 0–1 ms; ejection 1–10 ms; plume 10–100 ms; fallout 0.2–1.5 s; dripping from ceiling 1–60 s | — | Sub-frame events resolve on the impact frame at 60 fps | `[E]` |

### 2.5 Behaviour after a destructive head wound

- **Immediate total loss of motor control** ("cut strings" collapse `[R1-04 §2.3]`). No purposeful movement.
- **Brief motor phenomena** `[K](M)`: a single generalised jerk or extensor stiffening in the first 0–2 s; irregular twitches of the limbs or face for up to 5–20 s. No coordinated movement.
- **Breathing**: absent if the brainstem is destroyed. If the lower brainstem survives (typically submental/face-only trajectories), gasping may continue for minutes.
- **Heart**: continues for 1–10 min in most cases (`[R1-04 §2.4]`); blood pumps from the defect in time with the pulse and weakens progressively.
- **Face-only (submental, anterior) trajectories are the exception**: the victim may remain conscious, sit up, move, and survive for hours. See §4.

### Simulation parameters (shotgun to the head)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `E_dep_fraction` | per §2.1 table | — | Draw per shot within the range | `[E]` |
| `contact_gas_bonus` | handgun 50–150, magnum 150–300, rifle 300–600, shotgun 400–800 | J | Only at hard/near contact | `[E]` |
| `burst_E_dep` | 500–700 (default 600) | J | Vault burst | `[E]` |
| `partial_evisceration_E_dep` | 1,000 | J | 30–70 % of brain ejected | `[E]` |
| `full_evisceration_E_dep` | 1,500 | J | 50–100 %; Krönlein roll (§3) | `[E]` |
| `vault_fragment_count` | contact 12 ga 20–80; slug 15–50; buck at 1–3 m 3–20 | count | Log-normal size, median 15–25 mm, max 40–100 mm | `[E]` |
| `fragment_leave_fraction` | 0.2–0.6 | — | Others stay in the scalp bag (head collapses) | `[E]` |
| `scalp_flap_count` / `length` | 3–8 / 50–150 | count / mm | Radial from the burst centre | `[E]` |
| `lip_commissure_split` (intraoral) | p = 0.3–0.6, length 10–50 | — / mm | | `[K](M)`, `[E]` |
| `eye_proptosis_or_rupture` (vault burst) | 0.3–0.6 per eye | prob. | Orbital-roof burst | `[K](M)`, `[E]` |
| `ejecta_speed_fine / clump / mass` | 20–60 / 10–40 / 5–20 | m/s | Cone half-angle 20–40° about the exit direction; add a 60–90° wide low-speed component | `[E]` |
| `head_shape_collapse` | blend 0.3–0.8 toward a flattened shape when resting | — | Scale by fraction of vault fragmented | `[E]` |
| `post_burst_heart_duration` | 1–10 | min | Pulsatile bleeding from the defect | `[R1-04 §2.4]` |
| `terminal_twitch_window` | 0–20 | s | Irregular limb/face twitches, no purpose | `[K](M)` |

### Visual/behavioural checklist (shotgun to the head)

- At contact or within ~1 m the head does not "pop" uniformly; it splits. A large crater on the far side, radial scalp flaps, a spray cone of blood, brain and bone leaving mainly down-range, and heavy contamination of the muzzle and hand.
- The body drops instantly and limply. A single jerk or a few twitches may follow. The heart keeps pumping blood out of the head for minutes.
- Afterwards the head is misshapen and soft, the face sags like a mask, the eyes are at different heights or bulging, and bone fragments grate when the head is moved.
- Ceiling deposits and dripping from above after intraoral or submental shots.
- At 1–3 m with buckshot: several separate holes rather than one burst; less brain ejected.
- Sounds: the shot, a wet crack on the same frame, a patter of fragments and tissue landing over ~1 s, then dripping.

---

## 3. Rifle to the head: burst and the Krönlein shot

Round one gives the qualitative definition and a Krönlein probability `[R1-01 §5.5, kronlein_probability]`. This section gives the morphology.

### 3.1 Conditions

- **Definition**: a Krönlein shot is a head wound from a high-energy projectile (rifle, sometimes a shotgun slug) in which the vault is burst open and the brain is ejected **largely intact**, sometimes one or both hemispheres lying separately near the body `[K](M)` (Krönlein 1899; `[R1-01 §5.5, S35]`).
- **Energy, not range, decides.** Full-power rifle cartridges (7.62×51, .30-06, .308 hunting loads) retain > 2,000 J beyond 100 m and can produce it at ordinary engagement ranges; intermediate cartridges (5.56, 7.62×39) do it when the bullet yaws, fragments or strikes thick bone early `[K](M)`. Use the §2.1 `E_dep` rule.
- **Trajectory matters**: tangential and vertex tracks through the upper vault favour ejection of the hemispheres through a wide roof defect; tracks through the skull base favour destruction of the brainstem with less ejection `[K](L)`.

### 3.2 Morphology

| Feature | Description | Numbers | Tag |
|---|---|---|---|
| Entrance | Small (often 5–8 mm skin hole), with radial fractures from the bone entrance | `[R1-01 §2, §5]` | `[R1-01]` |
| Vault | Burst into 4–30 large plates, separated along fracture lines and **sprung sutures** (sagittal, coronal and lambdoid sutures gape 2–20 mm); heaving outward | Plates 30–120 mm | `[K](M)`, `[E]` |
| Scalp | Several "burst" lacerations over the fracture lines and vertex, torn (not cut) margins without abrasion, 30–150 mm; the scalp may split from front to back | 2–6 lacerations | `[K](M)`, `[E]` |
| Exit | Very large and irregular; bone fragments protrude | 40–120 mm plus the burst | `[R1-01 §4]` |
| Brain | Ejected as a large mass or as separate hemispheres with torn dura; the ejected brain shows the bullet track and surface lacerations but keeps gross shape (gyri recognisable) | 30–100 % ejected; hemisphere 400–600 g | `[K](M)` |
| Location of ejected brain | Near the body, down-range of the exit | 0.5–5 m | `[K](L)`, `[E]` |
| Residual cranial contents | Posterior fossa (cerebellum, brainstem) often remains, torn; bone chips, blood | — | `[K](M)` |
| Face | Distorted as in §2.3; eyes may protrude or rupture (orbital roof fractures, `[R1-01 §5.6]`) | — | `[K](M)` |
| "Lead snowstorm" | Soft-point hunting bullets leave dozens to hundreds of metal fragments along the track; not with handguns | `[R1-01 §5.5, S36]` | `[R1-01]` |

### 3.3 Behaviour

Identical to §2.5: immediate flaccid collapse, a brief jerk or twitches, apnoea, heart continuing for minutes with pulsatile bleeding from the open skull.

### Simulation parameters (rifle to the head)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `rifle_E_dep_fraction` | 5.56: 0.15–0.60; 7.62×39: 0.10–0.40; 7.62×51: 0.20–0.60 | — | Upper end if yaw/fragmentation happens inside the head (`[R1-01 §1]` yaw depths) | `[E]` |
| `kronlein_intact_hemisphere_prob` | 0.2–0.4 when `E_dep ≥ 1,500 J`; 0 below 1,000 J | prob. | Spawn one or two hemisphere meshes (400–600 g each) as rigid-soft debris | `[E]`, cf. `[R1-01 kronlein_probability]` |
| `vault_plate_count` | 4–30 | count | Split along authored suture curves first | `[E]` |
| `suture_diastasis` | 2–20 | mm | Gap along sprung sutures | `[E]` |
| `scalp_burst_lacerations` | 2–6 × 30–150 mm | — | Over fracture lines, vertex first | `[E]` |
| `ejected_brain_distance` | 0.5–5 | m | Hemisphere masses land down-range, slide 0.1–0.5 m on hard floors | `[E]` |

### Visual/behavioural checklist (rifle to the head)

- A small entrance and a massive exit; the vault splits into large plates along its sutures; the scalp tears open over the top of the head.
- With enough energy, brain leaves the skull as a large mass or as recognisable hemispheres that land a metre or more away.
- The body drops instantly and limply; the heart continues and blood pours from the open skull.
- A 5.56 head shot varies from a clean through-and-through to a full burst; do not make every rifle head shot identical.

---

## 4. Face and jaw shot off: mandible avulsion, tongue, teeth

Round one gives facial-fracture frequencies, intra-oral contact wounds and handgun/rifle jaw shots `[R1-01 §10]`. This section covers loss of the face and what the remaining structures look like and do.

### 4.1 Anatomy numbers

| Structure | Value | Tag |
|---|---|---|
| Mandible, fresh mass | 90–130 g | `[K](L)` |
| Mandibular body height (molars / symphysis) | 25–30 / 30–35 mm | `[K](M)` |
| Mandibular cortex | 2–4 mm (inferior border 3–5 mm) | `[K](M)` |
| Inferior alveolar artery and nerve (in the canal) | 2–3 mm bundle | `[K](M)` |
| Teeth | 32; incisors 21–24 mm long (crown 9–11 mm); molars ~20 mm; enamel 2–2.5 mm at cusps | `[K](H)` |
| Tongue | 60–80 g; ~9–10 cm long | `[K](M)` |
| Lingual arteries | 2–3 mm, one each side | `[K](M)` |
| Facial arteries | 2–3 mm, cross the lower border of the mandible in front of the masseter | `[K](H)` |
| Maxillary artery (deep face) | 3–4 mm | `[K](M)` |
| Labial arteries | 1–1.5 mm, run in the lips close to the inner surface | `[K](M)` |
| Tongue anchor | Genioglossus attaches to the genial tubercles on the back of the mandibular symphysis | `[K](H)` |

### 4.2 Injury patterns and their appearance

| Pattern | Typical cause | Appearance | Tag |
|---|---|---|---|
| **Lower-face avulsion** (symphysis and body of mandible lost) | Submental shotgun or rifle angled forward; close-range shotgun to the lower face | Lower lip and chin gone. The **tongue hangs out and down** 5–10 cm below the upper teeth when upright, dorsum visible, swelling within minutes. Floor of the mouth open into the upper neck; submandibular glands (lobulated, pale pink-tan `#D8B8A0`) and the hyoid region visible. Remaining rami hang on each side with a few teeth attached. Upper teeth and maxilla intact. Blood and saliva stream from the defect in ropes | `[K](M)` |
| **Mid-face avulsion** (nose, maxilla, palate) | Tangential rifle; close shotgun to the mid-face | Open nasal cavity: septum (cartilage `#CBD5D8` under red mucosa), **turbinates** as scroll-shaped, dark red, very vascular mucosa that bleeds heavily. Maxillary sinuses open (pale mucosa-lined cavities). Upper teeth lost. If the orbital floors are gone, the globes **sag 2–10 mm downward** and look sunken | `[K](M)` |
| **Transfacial through-and-through** (cheek to cheek) | Handgun or rifle across the face | Teeth visible through the cheek defect ("grin through the cheek"); tongue lacerated; one or both mandibular bodies fractured, with the front segment pulled down and back (open-bite deformity) | `[K](M)` |
| **Bilateral mandible fracture without avulsion** | Rifle, shotgun, hammer | "Flail" anterior mandible: chin segment drops and moves independently; mouth hangs open; tongue falls back when supine | `[K](H)` |
| **Intra-oral contact, low energy** | Handgun | Split lip, broken incisors, little external damage `[R1-01 §10]` | `[R1-01]` |

Bone fragment and tooth numbers: `[R1-01 §10]` (mandible 2–6 fragments handgun, 6–20+ rifle; 1–12 teeth fractured). Secondary-missile behaviour of teeth: §13.

### 4.3 Bleeding and airway

| Item | Value | Unit | Notes | Tag |
|---|---|---|---|---|
| Lower-face avulsion bleeding (both facial + both lingual + labial, BP maintained) | 100–300 initially, 30–100 after 5–10 min spasm | mL/min | `[R1-03 §5]` gives 20–150 per facial/lingual source | `[E]` |
| Mid-face (maxillary, sphenopalatine, turbinates) | 50–200 | mL/min | Largely posterior: runs into the throat | `[E]` |
| Swallowed blood that triggers vomiting | > 100–200 | mL | Vomiting of dark blood and clots 10–30 min later | `[K](M)` |
| Airway obstruction (supine, mandibular symphysis lost) | Tongue falls back within seconds | — | Genioglossus has lost its anchor | `[K](H)` |
| Time from complete obstruction to loss of consciousness | 1–3 | min | Faster with blood loss and exertion | `[K](M)` |

### 4.4 Behaviour

- **Consciousness is often preserved** when the track stays in front of the skull base and spine. These victims can stand, walk and fight, and many survive for hours `[K](M)`.
- **Posture**: conscious victims sit up and **lean forward with the head down** so that blood and saliva drain out of the defect. Laid supine, they choke, gurgle and struggle to sit up `[K](H)`.
- **Speech**: impossible for words needing lips, jaw or tongue. Grunts, groans, open vowel sounds; wet gurgling breath sounds `[K](M)`.
- **Hands**: go to the face and explore the defect; then press on it or hold the hanging tissue `[K](M)`.
- **Coughing and spitting**: sprays of blood, saliva, tooth fragments and bone chips (expirated spatter, §15.8) `[K](M)`.
- **Pain** may seem surprisingly limited in the first minutes (acute stress, `[R2-02]`); distress is dominated by air hunger and choking `[K](M)`.
- **Eyes**: intact unless the orbits are involved; watering; blood in the eyes if the forehead is damaged.

### Simulation parameters (face and jaw)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `mandible_avulsion_E_dep` | ≥ 400–700 in the lower face | J | Below: comminution; above: loss of the symphysis and body | `[E]` |
| `tongue_hang_length_upright` | 50–100 | mm | Below the upper incisal edge; soft-body or bone chain of 4–6 joints | `[E]` |
| `tongue_swelling` | +20–50 % volume over 10–60 min | — | Blend shape | `[K](M)`, `[E]` |
| `airway_obstruction_supine_no_symphysis` | true | bool | Triggers choking behaviour and hypoxia timer (1–3 min to LOC) | `[K](H)` |
| `lower_face_bleed_rate` | 100–300 → 30–100 after 5–10 min | mL/min | | `[E]` |
| `blood_vomit_threshold` | 150 (100–200) swallowed | mL | Vomit event 10–30 min later | `[K](M)` |
| `globe_sag_orbital_floor_loss` | 2–10 | mm | Downward displacement of the eye | `[K](M)` |
| `conscious_prob_face_only_track` | 0.7–0.9 | prob. | Track anterior to the skull base and spine | `[K](L)`, `[E]` |

### Visual/behavioural checklist (face and jaw)

- With the lower jaw gone, the tongue hangs forward and down out of a bloody cavity, the upper teeth are exposed, and blood and saliva pour out in strings.
- The victim is often awake: leans forward, holds the face, makes gurgling grunts, spits blood and teeth, and fights to sit up if pushed onto the back.
- Mid-face loss exposes the dark red scroll-shaped turbinates and the septum; bleeding runs backward into the throat and is coughed out.
- Swallowed blood comes back up as dark vomit after 10–30 min.

---

## 5. The eye: globe rupture, luxation and enucleation

Round one covers eyes in dying and death `[R1-04 §11]`, subconjunctival haemorrhage, raccoon eyes and birdshot entering through the orbit `[R1-01 §5.6, §9.2]`. This section covers the physically destroyed or displaced eye.

### 5.1 Reference numbers

| Item | Value | Tag |
|---|---|---|
| Axial length | 23.5–24 mm | `[K](H)` |
| Volume / mass | 6.5–7.2 mL / 7–7.5 g | `[K](H)` |
| Vitreous volume | ~4 mL (~80 % of the globe) | `[K](H)` |
| Aqueous volume / anterior chamber depth | ~0.25 mL / ~3 mm | `[K](H)` |
| Lens | 9–10 mm diameter, ~4 mm thick | `[K](H)` |
| Cornea thickness | 0.52–0.55 mm central, 0.65–0.7 mm peripheral | `[K](H)` |
| Sclera thickness | ~0.8 mm at the limbus; **~0.3 mm just behind the rectus insertions** (thinnest); 0.4–0.6 mm at the equator; ~1.0 mm near the optic nerve | `[K](H)` |
| Rectus insertions (distance from limbus) | medial 5.5, inferior 6.5, lateral 6.9, superior 7.7 mm (spiral of Tillaux) | `[K](H)` |
| Intraocular pressure | 10–21 mmHg | `[K](H)` |
| Globe rupture pressure (cadaver pressurisation) | roughly 0.3–1 MPa (≈ 2,000–7,500 mmHg); dynamic loading higher than static | `[K](L)` |
| Blunt-impact globe rupture risk | 50 % at a normalised energy (kinetic energy ÷ projectile cross-section) of ≈ 35,000 J/m² | `[K](M)` (Kennedy & Duma eye-injury risk functions) |
| Orbital opening | ~35 mm high × ~40 mm wide; objects wider than this are stopped by the bony rim | `[K](H)` |
| Orbit volume | ~30 mL | `[K](H)` |
| Optic nerve | 3–4 mm (4–6 mm with sheaths); intraorbital length 25–30 mm in an S-curve, ~18–20 mm from the back of the globe to the optic canal, leaving ~6–10 mm of slack | `[K](H)` |
| Ophthalmic artery | ~1–2 mm | `[K](M)` |

**Consequences for the player's weapons** `[E]`:
- **Fist**: the knuckles and hand are wider than the orbital opening, so the rim takes most of the load. Globe rupture from a punch is uncommon; orbital blow-out fractures and lid bruising are the usual result `[R1-02 §4.3]`.
- **Thumb gouge**: fits into the orbit; can luxate or rupture the globe.
- **Hammer face** (25–32 mm): fits into the orbit. 30–120 J over π·(0.0125–0.016 m)² = 4.9–8.0 × 10⁻⁴ m² gives 37,000–245,000 J/m², at or above the 50 % rupture value. A direct hammer strike to the eye ruptures the globe in most cases.
- **Knife**: penetrating injury; collapse without an explosive appearance.
- **Pellets and bullets**: perforate the globe easily. A lead pellet or BB perforates the eye above roughly 40–75 m/s `[K](M)`; birdshot at typical ranges exceeds this.

### 5.2 Blunt globe rupture: mechanism and sites

- The impact deforms the globe, intraocular pressure spikes, and the wall splits at its weakest points: **just behind the rectus insertions** (0.3 mm sclera), **at the limbus**, and at old surgical wounds. The split is often on the side opposite the impact or superonasal, because most blows come from below and the side `[K](M)`.
- Rupture sites behind the rectus insertions are hidden under the conjunctiva and haemorrhage; the eye looks swollen, dark red and soft rather than visibly torn `[K](M)`.
- Scleral split length: 5–20 mm, usually curved, parallel to the limbus `[K](M)`.

### 5.3 Appearance of a ruptured globe (what to render)

| Sign | Appearance | Numbers | Tag |
|---|---|---|---|
| Deflated globe | Soft, sunken, loses its round shape; the cornea wrinkles into folds; the sharp specular highlight breaks into irregular patches (the best single render cue) | Volume loss 20–80 % | `[K](M)`, `[E]` |
| 360° haemorrhagic chemosis | Conjunctiva ballooned with blood all round, dark red `#7A0A14`, glossy, may bulge between the lids | 2–6 mm thick | `[K](H)` |
| Peaked ("teardrop") pupil | Pupil drawn toward the rupture site | — | `[K](H)` |
| Uveal prolapse | Dark brown-black bead or knuckle `#3A2420` at the wound edge; often mistaken for clot | 1–5 mm | `[K](H)` |
| Vitreous extrusion | Clear jelly strands with egg-white consistency, blood-tinged pink, stretch from the wound and drape over the lid or cheek | 0.5–3 mL; strands 1–3 cm | `[K](M)` |
| Hyphema | Blood in the anterior chamber; settles into a horizontal fluid level when upright; a fully filled chamber looks black-red ("eight-ball") | ≤ 0.25 mL | `[K](H)` |
| Anterior chamber depth | Shallow or flat (anterior rupture) or abnormally deep (posterior rupture) | — | `[K](H)` |
| Lens | Dislocated, or extruded as a clear to yellowish disc; becomes opaque white over minutes to hours outside the eye | 9–10 mm | `[K](M)` |
| Retina | May extrude as a thin grey-white membrane | — | `[K](M)` |
| Iris tear at its root | D-shaped pupil, second dark gap at the iris edge | — | `[K](M)` |
| Lids | Swell within minutes; may close the eye within 10–60 min in the living | — | `[K](M)` |
| Tears | Blood-tinged watery discharge running down the cheek | — | `[K](M)` |

Penetrating wounds (knife, fragment): linear corneal or scleral cut about the width of the blade or fragment, clear aqueous dripping, uveal tissue plugging the wound, globe progressively soft `[K](M)`.
Bullet through or next to the orbit: the globe is burst by the temporary cavity; the orbital contents may be expelled with the fragments; the eyelids remain as torn flaps over an empty or blood-filled orbit `[K](M)`.

### 5.4 Luxation, hanging globe and enucleation

| State | Appearance | Numbers | Tag |
|---|---|---|---|
| **Luxation** (globe pushed in front of the lids) | Eye bulges far forward; lids spasm and lock behind the globe's equator; cornea may look normal; vision may persist briefly; double vision because the eyes no longer align | Globe 10–20 mm forward of normal | `[K](M)` |
| **Hanging globe** (muscles torn, nerve intact) | The eye hangs out of the orbit onto the cheek, attached by the optic nerve and remnants of muscle; white sclera with 1–4 red muscle stumps at the insertion distances in §5.1; white optic nerve cord 3–6 mm thick visible for 1–3 cm; orbital fat lobules protrude | Up to ~2–3 cm beyond the rim before the nerve is taut | `[K](M)`, `[E]` |
| **Enucleation** (globe detached) | Globe with a 5–20 mm optic nerve stump, muscle tags, conjunctival rags; **empty orbit**: dark red cavity, yellow fat lobules herniating, muscle stumps, bleeding that fills the socket and overflows; the lids sink inward | Globe 7–7.5 g; bleeding 10–50 mL/min (ophthalmic artery and branches, spasm reduces it within minutes) | `[K](M)`, `[E]` |
| Detached globe over time | Cornea clouds within 1–2 h; sclera dries yellow-brown; the globe slowly softens as fluid leaks | — | `[K](M)`, `[R1-04 §11.6]` |

### 5.5 Behaviour

- Severe pain, **blepharospasm** (the eye is squeezed shut), profuse tearing, hand pressed over the eye `[K](H)`. Pressing on a ruptured globe expels more contents.
- **Oculocardiac reflex**: pressure or traction on the globe slows the heart (drop ≥ 20 %) and causes nausea, sometimes vomiting and fainting `[K](H)`.
- Loss of vision in that eye; loss of depth perception: reaching and stepping errors `[K](M)`.
- The uninjured eye often closes reflexively too; the victim may be functionally blind for seconds to minutes `[K](M)`.
- A luxated eye that still sees gives double vision `[K](M)`.

### Simulation parameters (eye)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `globe_rupture_norm_energy_50` | 35,000 | J/m² | Logistic risk; slope so that 10 % ≈ 20,000 and 90 % ≈ 55,000 `[E]` | `[K](M)` |
| `orbit_aperture` | 35 × 40 | mm | Impactors wider than this load the rim, not the globe | `[K](H)` |
| `pellet_eye_perforation_v` | 40–75 | m/s | | `[K](M)` |
| `globe_volume_loss_on_rupture` | 0.2–0.8 | fraction | Drives the deflation blend shape and highlight break-up | `[E]` |
| `chemosis_thickness` | 2–6 | mm | Inflate the conjunctiva shell | `[K](H)` |
| `uveal_prolapse_size` | 1–5 | mm | Dark bead at the wound | `[K](H)` |
| `vitreous_strand_length` | 10–30 | mm | Clear gel strands, IOR 1.336, blood-tinged | `[K](M)` |
| `hyphema_volume` | 0–0.25 | mL | Fluid level follows gravity | `[K](H)` |
| `lid_swelling_close_time` | 10–60 | min | Living only | `[K](M)` |
| `luxation_forward_offset` | 10–20 | mm | Lids clamp behind the equator | `[K](M)` |
| `hanging_globe_max_offset` | 20–30 | mm | Beyond: optic nerve avulsion | `[E]` |
| `enucleation_orbit_bleed` | 10–50 → 5–15 after 5 min | mL/min | | `[E]` |
| `oculocardiac_hr_drop` | 20–40 | % | Triggered by pressure or traction on the globe | `[K](H)` |

### Visual/behavioural checklist (eye)

- A ruptured eye is not a neat hole: it is a soft, deflated, wrinkled globe surrounded by bulging dark red conjunctiva, with dark uveal tissue and clear-to-pink jelly at the wound.
- A hammer to the eye ruptures it; a punch usually does not (the bony rim takes the blow) and gives a black eye and swollen lids instead.
- A hanging eye shows white sclera with red muscle stumps and a white nerve cord; the empty orbit fills with blood and yellow fat bulges from it.
- The victim clamps the eye shut, clutches it, tears, may vomit or faint, and misjudges distances.

---

## 6. Scalp avulsion and degloving

### 6.1 Reference numbers

| Item | Value | Tag |
|---|---|---|
| Scalp thickness (skin + dense subcutaneous layer + galea) | 5–7 mm | `[R1-01 §2.1]`, `[K](M)` |
| Hair-bearing scalp area | ~550–700 cm² | `[E]` |
| Scalp hairs | ~100,000 | `[K](H)` |
| Single hair: pull-out or break force | ~0.4–1.0 N | `[K](M)` |
| Avulsion plane | Loose areolar (subgaleal) layer between galea and pericranium | `[K](H)` |
| Typical avulsion margins | Eyebrows / supraorbital ridge in front; temporal region above or including the ears; nuchal line behind | `[K](M)` |
| Main scalp arteries | Superficial temporal ~2 mm, occipital ~2 mm, posterior auricular ~1 mm, supraorbital and supratrochlear ~1 mm | `[K](M)` |

**Why the scalp comes off rather than the hair** `[E]` from `[K](M)`: when hair is gathered into a bundle and pulled or wound up, the load is shared by thousands of hair follicles anchored in the dense subcutaneous layer (thousands × 0.5 N = kN), while the subgaleal plane below is loose and weak. The scalp therefore separates through the subgaleal plane before the hairs pull out.

### 6.2 Appearance

| Feature | Appearance | Numbers | Tag |
|---|---|---|---|
| Avulsed flap, outer side | Hair matted with blood; skin intact apart from the torn margins | Flap 5–7 mm thick | `[K](M)` |
| Avulsed flap, underside | Glistening white-grey galea (`#E0DAD2`), relatively bloodless in the middle; bleeding vessel ends along the torn margins | — | `[K](M)` |
| Exposed skull, pericranium intact | Pink-white glistening membrane (`#E6CFC4`) with scattered pinpoint bleeding | — | `[K](M)` |
| Exposed skull, pericranium stripped | Ivory bone (`#E9DFCC`) with red pinpoints from emissary and diploic vessels; sutures visible as fine wavy lines | — | `[K](M)` |
| Flap margins | Irregular, torn, curled; skin edge retracts 5–10 mm | — | `[K](M)` |
| Partial avulsion | Flap hinged on a pedicle (often at the temple or occiput, carrying the superficial temporal or occipital vessels); hangs down over the face or neck | — | `[K](M)` |
| Sharp scalping (knife) | Round or oval defect 8–15 cm at the crown with incised margins, pericranium usually left on the bone | — | `[K](M)` |
| Bleeding | Vessels are held open by fibrous septa and cannot retract (`[R1-03 §7.3]`); streams from the margins, runs into the eyes and down the face and neck | Complete avulsion 100–300 mL/min initially; shock in 10–30 min untreated | `[E]` from `[R1-03 §5]` |

### 6.3 Degloving (limbs and trunk)

| Type | Mechanism | Appearance | Numbers | Tag |
|---|---|---|---|---|
| **Open degloving** | Shear: skin and fat torn off the deep fascia (wheel, machinery, heavy tangential blow, close tangential shotgun) | Skin sleeve peeled back like a glove or rolled-down sock; underside yellow fat with red **perforator vessel stumps** bleeding at intervals; exposed muscle covered by glistening white fascia; flap blanches (pale, no refill) then turns dusky purple over hours | Flap thickness 0.5–4 cm; perforator stumps every 2–4 cm | `[K](M)`, `[E]` |
| **Closed degloving** (Morel-Lavallée) | Same shear without a skin break (heavy stomp or crush with sliding) | Soft, fluctuant swelling that sloshes when pressed; skin abnormally mobile over the deep layer; overlying bruise; can be large | 50–500+ mL of blood, lymph and liquefied fat | `[K](M)` |
| **Ring avulsion** (finger) | Ring caught while the body moves | Skin of the finger pulled off like a glove, exposing tendons and bone | — | `[K](H)` |
| **Knife flaying** (flap raised with a blade) | Incision + undermining | Clean incised margins; underside fat with small bleeding vessels; flap thickness set by the cutting plane | — | `[K](M)` |

### 6.4 Behaviour

- Conscious. Blood runs into the eyes: repeated blinking, wiping, stumbling from impaired vision `[K](M)`.
- A scalp flap hanging over the face blocks vision; the victim pushes it back and holds it `[K](M)`.
- Scalp avulsion is intensely painful at the margins; the exposed bone itself is not sensitive `[K](M)`.
- Progressive signs of blood loss as in `[R1-03 §3.6]`.

### Simulation parameters (scalp and degloving)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `scalp_flap_thickness` | 5–7 | mm | Separates at the subgaleal plane | `[K](M)` |
| `scalp_avulsion_force_bundled` | 300–1,500 | N | Traction on bundled hair or a tangential blow grabbing the scalp | `[E]` |
| `scalp_margin_retraction` | 5–10 | mm | | `[K](M)` |
| `scalp_avulsion_bleed` | 100–300 initially | mL/min | Spasm factor fixed near 1.0 (vessels held open) | `[E]`, `[R1-03 §7]` |
| `degloving_flap_thickness` | 5–40 | mm | Skin + fat | `[K](M)` |
| `perforator_spacing` | 20–40 | mm | Bleeding points on the fascia and flap | `[E]` |
| `flap_colour_ramp` | pale (0–30 min) → dusky purple `#6A4A6A` (1–6 h, living) | — | Ischaemic, then venous congestion | `[K](M)` |
| `closed_degloving_volume` | 50–500 | mL | Fluctuant swelling blend shape | `[K](M)` |

### Visual/behavioural checklist (scalp and degloving)

- An avulsed scalp comes off as a thick hairy flap with a white glistening underside; underneath, the skull is either covered by pink membrane with pinpoint bleeding or is bare ivory bone.
- The margins bleed relentlessly, blood runs into the eyes and the victim keeps wiping and blinking.
- A degloved limb shows a sleeve of skin rolled back, yellow fat on its underside, and silvery fascia over the muscles, dotted with bleeding points.
- A closed degloving is a soft, sloshing swelling under intact, bruised, loose skin.

---

## 7. Crushed and comminuted skull, depressed fragments, brain herniation

Round one covers the single hammer blow (thresholds, depressed fracture shape, scalp haematoma) `[R1-02 §5]` and gunshot fractures `[R1-01 §5]`. This section covers repeated blows, stomping and crushing, and the brain coming out through the defect.

### 7.1 Energy sources available in the game

| Source | Energy / force per event | Relation to skull thresholds (14–68 J; frontal ~22–24 J, temporal ~5–15 J `[R1-02 §5.1]`) | Tag |
|---|---|---|---|
| Hammer blow | 30–120 J; 3–4.7 kN contact force | One committed blow can fracture; repeated blows comminute | `[R1-02 §5.2]` |
| Stomp with the head on a hard floor | ~50–200 J; peak 1.5–4 kN (heel, 75–90 kg attacker) | Can fracture, especially the temporal region; repeated stomps comminute and flatten | `[E]` (foot + leg effective mass 5–15 kg at 3–6 m/s = 22–270 J) |
| Head driven into a floor or wall | ~20–150 J | Can fracture at the contact point; contrecoup brain contusions opposite | `[E]` |
| Fist | 30–150 J (effective mass 2–5 kg at 5–10 m/s); broad knuckle contact, and the head moves away on the neck | Skull fracture rare; facial fractures common `[R1-02 §4]` | `[R1-02]`, `[E]` |
| Quasi-static crush (heavy object) | Skull failure somewhere in the ~5–15 kN range in lateral compression | Only for environmental hazards; not a player weapon | `[K](L)` |

### 7.2 Progression under repeated hammer blows at one site

| Blow count at one site | Scalp | Bone | Dura and brain | Spatter | Tag |
|---|---|---|---|---|---|
| 1 | Crescent or stellate laceration 10–40 mm; bruise and swelling | Fracture with probability 0.2–0.8 (energy and region); linear or a punched-out defect matching the hammer face | Contusion under the site | Almost none: no exposed blood yet | `[R1-02 §5]`, `[E]` |
| 2–3 | Lacerations join; flaps | Depressed fracture 25–40 mm, 5–15 mm deep; 2–6 inner-table fragments driven inward | Dural tear p ≈ 0.3–0.6; cortex lacerated | Impact spatter starts; first cast-off trails (§15) | `[E]` from `[K](M)` |
| 4–8 | Ragged defect 40–80 mm; hair and bone chips in the wound | **Comminuted "mosaic" zone** 40–80 mm: 10–30 fragments 5–25 mm; concentric fracture rings around it; radial lines to 50–150 mm | Fragments driven 10–30 mm into the brain; brain pulped under the site; pulped brain and chips extrude through the laceration | Heavy impact spatter; several cast-off trails; brain particles in the spatter | `[E]` from `[K](M)` |
| > 8 | Defect 60–120 mm | Cavity; neighbouring impact sites merge into one comminuted area; loss of vault shape; skull-base fractures | Brain exposed and extruding; massive loss of tissue | Very heavy | `[E]` |

Also `[K](M)`:
- **Terraced** depressions on oblique blows `[R1-02 §5.3]`.
- **Contrecoup contusions** (frontal and temporal poles, undersurfaces) when the moving head strikes a floor or wall, not when a stationary head is struck by a hammer.
- **Hinge fracture**: a transverse fracture across the middle cranial fossae and pituitary fossa that splits the skull base into front and back halves; from heavy side impacts or crushing. The head feels unstable; blood from both ears.
- **Ring fracture** around the foramen magnum: from vertical loading (falls onto the feet or buttocks, or heavy blows to the vertex).

### 7.3 Crush of the whole head (stomping, heavy object)

| Feature | Description | Numbers | Tag |
|---|---|---|---|
| Shape | Flattened perpendicular to the load; the vault widens | Height loss 20–60 % | `[K](M)`, `[E]` |
| Fractures | Multiple linear fractures radiating from both contact points, joining; "eggshell" comminution | 10–60 fragments | `[K](M)`, `[E]` |
| Scalp | **Bursting lacerations** where the scalp is stretched, typically along the sides at right angles to the load; torn margins with tissue bridges | 30–120 mm | `[K](M)` |
| Brain | Extruded through scalp lacerations, the ears, nose and orbits | — | `[K](M)` |
| Eyes | Pushed forward or extruded by the rise in orbital pressure | — | `[K](M)` |
| Face | Unrecognisable; nose and mouth bleeding; jaw dislocated | — | `[K](M)` |
| Feel and sound | Grating bone crepitus; wet crunching on further load | — | `[K](M)` |

### 7.4 Brain herniating through a skull defect (living victim)

| Feature | Description | Numbers | Tag |
|---|---|---|---|
| Protrusion | Brain bulges through the dural tear and bone defect as ICP rises and the brain swells | 5–30 mm above the bone edge, growing over minutes to hours | `[K](M)`, `[E]` |
| Pulsation | The protruding brain pulses visibly with the heartbeat and moves with breathing | Pulse 1–3 mm; respiration 0.5–2 mm | `[K](M)`, `[E]` |
| Colour | Surface purple-red and congested; a dark haemorrhagic "collar" where the bone edge strangles it (`#5A1A22`) | — | `[K](M)` |
| Discharge | Pulped brain, CSF and blood ooze out and surge on coughing, straining or screaming | 1–10 mL/min, surges ×2–5 | `[E]` |
| At death | Pulsation stops with the last effective beats; surface dulls within minutes | — | `[K](M)` |
| Through small openings | Pulped brain extrudes as a soft "worm" or ribbon through a 10–20 mm gap | — | `[K](M)` |

### 7.5 Behaviour (hand-off)

- Comminuted depressed fractures with brain injury: immediate loss of consciousness or confusion, focal deficits, posturing and seizures. See `[R2-01]` and `[R1-04 §3–5]`.
- Crushed head: immediate death with brief terminal twitches (`[R1-04 §2.3]`).

### Simulation parameters (crushed skull)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `stomp_energy` | 50–200 | J | Head on a rigid floor | `[E]` |
| `blow_fracture_prob(E, region)` | logistic, 50 % at frontal 23 J, temporal 10 J, parietal 30 J, occipital 40 J | prob. | Frontal and temporal anchored to `[R1-02 §5.1]`; parietal and occipital `[E]` | `[E]` |
| `depressed_depth_per_blow` | 3–10 after the first fracture | mm | Cumulative; > 10 mm links to the dura/brain system | `[E]` |
| `fragments_added_per_blow` | 2–6 | count | Once fractured | `[E]` |
| `mosaic_zone_diameter` | 40–80 (4–8 blows) → 60–120 (> 8) | mm | | `[E]` |
| `inner_fragment_drive_depth` | 10–30 | mm | Into the brain | `[E]` |
| `dural_tear_prob` | 0.3–0.6 at blows 2–3; 0.9 beyond | prob. | | `[E]` |
| `crush_height_loss` | 0.2–0.6 | fraction | Whole-head crush | `[E]` |
| `herniation_growth` | 5–30 mm over 10–120 min | mm | Living only; scales with ICP | `[E]` |
| `herniation_pulse_amp` | 1–3 | mm | At the current HR | `[E]` |
| `herniation_ooze` | 1–10 (surges ×2–5 on Valsalva) | mL/min | | `[E]` |

### Visual/behavioural checklist (crushed skull)

- Repeated hammer blows change the picture step by step: first a split scalp and a lump, then a punched-in depression, then a mosaic of loose pieces with brain and chips coming out, and more spatter with every blow.
- A stomped or crushed head is flattened and widened, the scalp bursts at the sides, the eyes bulge or come out, and brain appears at the ears and nose.
- In a living victim with an open skull, the exposed brain bulges, darkens at the edge and pulses with each heartbeat; it surges out when the victim coughs or screams.
- Sounds: dull thuds, then sharp cracks, then wet crunching as fragments grind.

---

## 8. Open fractures of long bones

Round one gives bone dimensions, cortex thickness, marrow types and colours `[R1-05 §8]`, fracture-asset tech `[R1-06 §5.5]` and closed-fracture blood loss `[R1-03 §8.1]`. This section gives fracture patterns, how bone comes through the skin, and what the player sees.

### 8.1 Bone reference for fracture rendering

| Bone | Mid-shaft outer Ø (mm) | Cortex (mm) | Medullary canal (mm) | Shaft marrow | Soft tissue over the bone at its thinnest | Tag |
|---|---|---|---|---|---|---|
| Femur | 26–30 | 5–7 | 12–16 | Yellow (red in the neck and proximal metaphysis) | 3–8 cm of muscle all round: open femur fractures need high energy | `[R1-05 §8.4]`, `[K](M)` |
| Tibia | 22–28 × 18–22 (triangular) | 4–6 | 10–14 | Yellow | **Anteromedial face: skin + thin fat, 3–8 mm**: the most common open fracture in adults | `[K](H)` |
| Fibula | 10–15 | 2–3 | 3–5 | Yellow | Peroneal muscles; head subcutaneous | `[K](M)` |
| Humerus | 20–24 | 3–5 | 10–13 | Yellow | 2–5 cm | `[K](M)` |
| Radius | 12–15 | 2–3 | 6–8 | Yellow | Distal third 5–15 mm | `[K](M)` |
| Ulna | 12–14 | 2–3 | 5–7 | Yellow | **Posterior border subcutaneous along its whole length** (5–10 mm) | `[K](H)` |
| Clavicle | 12–15 | 2–3 | small | Red | Subcutaneous, 3–8 mm | `[K](M)` |

Failure loads for tuning `[K](L)`: three-point bending of the shaft, roughly femur 3–5 kN, tibia 2.5–4 kN, humerus 1.5–2.5 kN, radius or ulna 1–1.5 kN each; torsion to failure, roughly femur 100–200 N·m, tibia 50–100 N·m. A hammer (3–4.7 kN contact force `[R1-02 §5.2]`) on the subcutaneous tibia or ulna can therefore break it; on the muscle-padded femur it cannot.

### 8.2 Fracture patterns (choose by mechanism)

| Pattern | Geometry | Fragment ends | Mechanism | Game sources | Tag |
|---|---|---|---|---|---|
| **Transverse** | Line ⟂ shaft (±10–15°) | Blunt, fine saw-tooth interlocking edges | Pure bending, three-point loading, direct blow | Hammer, kick or stomp on the shin or forearm | `[K](H)` |
| **Oblique** | 30–60° to the shaft | Sharp wedges | Bending + axial compression | Falls, jumping from height | `[K](H)` |
| **Spiral** | Helix ~40–45° to the axis, wraps 180–360° round the shaft; length 2–4 × shaft Ø (tibia 5–10 cm) | **Long, pointed, spear-like spikes** with a straight vertical "step" connecting the helix ends | Torsion (foot planted, body rotates; twisted limb) | Falls with rotation, limb twisted by an attacker, ragdoll falls with a fixed foot | `[K](H)` |
| **Butterfly (wedge)** | Two oblique lines isolating a triangular fragment on the compression side; fragment 1–2 × shaft Ø long | Sharp | Bending with compression | Hammer, kick; handgun bullets through the shaft | `[K](H)` |
| **Comminuted** | ≥ 3 fragments, often many | Mixed; small chips | High energy | Rifle, close shotgun, crushing stomp | `[K](H)` |
| **Segmental** | Two fracture levels with a free middle segment 5–15 cm | — | High-energy bending | Heavy blunt blows, vehicles | `[K](H)` |
| **Drill hole** | Round hole ≈ bullet Ø through cancellous metaphysis, few cracks | — | Low-velocity bullet in cancellous bone | Handgun near the knee, hip, shoulder, wrist | `[K](M)` |
| Greenstick / plastic bowing | Incomplete, bent | — | Children only | **Do not use for adults** | `[K](H)` |

### 8.3 How bone comes through the skin

| Mechanism | Wound | What is seen | Tag |
|---|---|---|---|
| **Inside-out** (spike of the proximal fragment pierces the skin at the apex of the angulation) | Small, 0.5–3 cm, often slit-like, clean edges | Bone spike protrudes 1–8 cm. The end: an **ivory cortical ring** 2–7 mm thick around a **yellow greasy marrow plug** (shaft) or a **red sponge** (metaphysis); torn periosteum as a ragged glossy collar; clinging red muscle fibres; fat globules shining on the blood. Bleeding dark and welling unless an artery is torn | `[K](M)` |
| Re-entry | — | When the limb straightens or the muscles relax, the bone end often **slips back under the skin**, leaving only a small bleeding wound (important: the "bone visible" state depends on the current pose) | `[K](H)` |
| **Outside-in** (projectile, crush, blow) | Larger, ragged, contaminated | Fragments visible in the wound bed; soft-tissue loss; periosteum stripped; muscle pulped | `[K](M)` |
| Near-amputation (close shotgun, rifle, heavy crush) | Circumferential tissue loss | Limb hangs on a bridge of skin and muscle; bone ends ragged; distal limb pale and cold if the artery is cut | `[K](M)` |

**Gustilo–Anderson grade** (use it as the severity key for the recipe) `[K](H)`:

| Type | Criteria |
|---|---|
| I | Wound < 1 cm, clean, low energy, simple fracture |
| II | Wound 1–10 cm, moderate soft-tissue damage, no extensive flaps or avulsion |
| IIIA | Extensive soft-tissue damage or high energy (includes high-velocity gunshot, segmental or severely comminuted fractures regardless of wound size), but bone can still be covered |
| IIIB | Extensive soft-tissue loss with **periosteal stripping and exposed bone** |
| IIIC | Any open fracture with an **arterial injury requiring repair** |

### 8.4 Gunshot fractures of long bones

| Weapon | Diaphysis (shaft) | Metaphysis (bone end) | Soft tissue and exit | Tag |
|---|---|---|---|---|
| Handgun | Comminuted, often butterfly; 3–10 fragments; radiating fissures 2–10 cm | Drill hole ≈ bullet Ø, few cracks | Exit enlarged to 2–5 cm with bone chips | `[K](M)`, `[E]` |
| Rifle | Severe comminution; **3–10 cm of shaft pulverised**; 20–100+ fragments driven 2–10 cm into the muscle | Extensive comminution into the joint | Exit 5–15 cm with bone protruding; see §13 | `[K](M)`, `[E]` |
| Shotgun, close range | Massive comminution with soft-tissue loss; near-amputation at contact on the forearm or lower leg | Same | Crater wound with wadding, pellets and bone | `[K](M)` |

### 8.5 Deformity and mechanics (ragdoll)

| Item | Value | Tag |
|---|---|---|
| Femoral shaft: shortening from muscle pull (fragments override) | 2–5 cm | `[K](M)` |
| Femoral shaft or neck, supine: external rotation of the foot | 45–90° | `[K](H)` |
| Tibial shaft: angulation after the fall | 10–45° | `[E]` |
| "New joint" at the fracture: range restrained only by soft tissue | ±30–90° bending; free rotation ±20–60° | `[E]` |
| Crepitus | Grating felt and heard when fragments move | `[K](H)` |
| Thigh swelling from closed bleeding | +2–3 cm circumference per litre (thigh 55 cm × 40 cm long gains 25 cm² cross-section per litre) | `[E]` |
| Blood loss | Femur 1–1.5 L, tibia or humerus 0.5–0.75 L closed; more when open | `[R1-03 §8.1]` |

### 8.6 Behaviour

- **Immediate loss of weight-bearing** on a broken femur or tibia: the leg buckles at the fracture and the victim falls toward the injured side `[K](H)`; see `[R2-03]` for the fall.
- **Guarding**: both hands grip the limb above the fracture; the victim avoids any movement; screams or groans at each movement, with a pain spike when fragments grind `[K](M)`.
- Crawling while dragging the broken leg, which rotates outward and bends at the fracture `[K](M)`.
- Sight of their own bone can trigger a vasovagal faint (`[R1-03 §3.2]`) `[K](M)`.
- Arm fractures: the arm hangs; the victim cradles it against the trunk with the other hand `[K](H)`.

### Simulation parameters (open fractures)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `fracture_pattern_weights` | direct blow: transverse 0.5, butterfly 0.35, comminuted 0.15; torsion fall: spiral 0.8, oblique 0.2; axial fall: oblique 0.5, comminuted 0.3, transverse 0.2; handgun: comminuted/butterfly 0.8, drill hole 0.2 (metaphysis 0.8); rifle: comminuted 1.0 | prob. | Select the authored fracture variant `[R1-06 §5.5]` | `[E]` from `[K](M)` |
| `open_fracture_prob` | tibia 0.25–0.4, ulna 0.15–0.3, radius 0.1–0.2, humerus 0.05–0.15, femur 0.05–0.1 (blunt); gunshot 1.0 | prob. | Given a fracture | `[E]` from `[K](M)` |
| `bone_spike_protrusion` | 10–80 | mm | Only while the limb is angulated beyond ~15–20° | `[E]` |
| `spiral_fracture_length` | 2–4 × shaft Ø | mm | | `[K](M)` |
| `butterfly_fragment_length` | 1–2 × shaft Ø | mm | | `[K](M)` |
| `rifle_diaphysis_pulverised_length` | 30–100 | mm | Remove authored segment; spawn secondary fragments §13 | `[E]` |
| `fracture_joint_limits` | bend ±30–90°, twist ±20–60°, stiffness 0.05–0.2 × intact | ° | Insert a soft joint in the PhysicalBone chain at the fracture | `[E]` |
| `femur_shortening` | 20–50 | mm | Override along the shaft | `[K](M)` |
| `foot_external_rotation_femur_fx` | 45–90 | ° | Supine rest pose | `[K](H)` |
| `fat_globules_in_wound` | true for shaft fractures | bool | Yellow specular beads on the blood | `[K](M)` |
| Sound: fracture | sharp crack (shaft), dull crunch (cancellous); crepitus grating on movement | — | | `[E]` |

### Visual/behavioural checklist (open fractures)

- A spiral tibial fracture ends in long spear-like points; one of them can come out through the thin skin of the shin as a white ring of bone with a yellow fatty core and a torn collar of membrane.
- The bone end can slip back inside when the leg is straightened, leaving just a small bleeding wound.
- Fat droplets glisten on the blood in the wound.
- The limb bends where there is no joint, the foot rolls outward, the thigh swells.
- The victim collapses onto the injured side, grips the limb, screams on every movement and drags it when crawling.
- A rifle bullet through a shaft leaves a gap of pulverised bone and a large exit with bone chips sticking out.

---

## 9. Rib fractures, flail chest and the sternum

### 9.1 Reference numbers

| Item | Value | Tag |
|---|---|---|
| Rib cross-section (mid-ribs) | ~10–15 × 5–8 mm; cortex ~1 mm; red marrow | `[R1-05 §8.4]`, `[K](M)` |
| Most commonly fractured | Ribs 4–9, at the lateral and posterolateral angles | `[K](M)` |
| Ribs 1–2 fractured | Implies high energy; associated with great-vessel and brachial-plexus injury | `[K](H)` |
| Ribs 10–12 fractured | Look for liver (right), spleen (left), kidney injury below | `[K](H)` |
| Chest compression (frontal blunt) at which rib fractures start | ~20 % of chest depth (~45 mm in a 23 cm chest) | `[K](M)` (Kroell; Viano) |
| Compression associated with multiple fractures / flail | ~35–40 % (~80–90 mm) | `[K](M)` |
| Blood per rib fracture | ~100–125 mL | `[R1-03 §8.1]` |

Game energy sources `[E]`: hammer blows (3–4.7 kN focal) fracture the struck rib in most full-force hits on the lateral chest; kicks and stomps (1.5–4 kN, larger area) fracture ribs, stomps on a supine chest can cause multiple bilateral fractures; punches fracture ribs occasionally, most often the lower ribs.

### 9.2 Rib fracture morphology

| Type | Appearance | Tag |
|---|---|---|
| Direct-blow fracture | At the point of impact; fragment ends **driven inward** toward the pleura and lung; can lacerate the lung and intercostal vessels | `[K](H)` |
| Indirect (compression) fracture | Away from the impact, at the lateral angles, where the rib bows outward; ends displaced outward or not at all | `[K](H)` |
| Buckle (incomplete) fracture | One cortex crumpled, the other intact; no displacement | `[K](M)` |
| Displaced fracture | Ends overlap or step by more than a cortical width; sharp spikes 5–15 mm | `[K](M)` |
| Costochondral separation | Rib torn from its cartilage; the cartilage end is translucent bluish and smooth | `[K](M)` |

### 9.3 Flail chest

- **Definition**: three or more adjacent ribs each fractured in two or more places, producing a free segment `[K](H)`. An **anterior (sternal) flail** occurs when the costal cartilages or ribs fracture on both sides of the sternum.
- **Paradoxical movement**: the free segment is sucked **in on inspiration** and pushed **out on expiration**, opposite to the rest of the chest `[K](H)`.
- **Magnitude** `[E]`: pleural pressure in quiet breathing is −5 to −10 cmH₂O, and −20 to −40 cmH₂O in laboured breathing. On a segment of ~150 cm² this is 7–60 N of inward pull, restrained only by intercostal soft tissue and muscle tone. Visible paradoxical excursion: **~0.5–1 cm in quiet breathing, 1–3 cm in laboured breathing, up to ~5 cm in severe distress**.
- **Muscle splinting masks it early**: in the first minutes to hours, reflex spasm of the chest-wall muscles can hold the segment; the paradox becomes obvious as the muscles tire or the victim breathes harder `[K](M)`.
- **Underlying lung contusion** is present in most flail chests and is the main cause of hypoxia `[K](H)`.
- **Breathing**: rapid (25–40/min) and shallow, a grunt or catch at the end of each inspiration, suppressed cough `[K](M)`.
- **Posture**: holds the injured side with the arm pressed against it, leans toward the injured side, avoids lying flat `[K](M)`.

### 9.4 Sternum

- Usually a **transverse fracture** of the body or at the manubriosternal joint, from direct frontal blows (stomp on a supine chest, kick, hammer) `[K](H)`.
- **Step deformity** of 5–15 mm palpable and sometimes visible; local bruising and swelling `[K](M)`.
- Associated **cardiac contusion** (arrhythmias: extra beats, runs of tachycardia) `[K](H)`.

### 9.5 Subcutaneous emphysema and traumatic asphyxia

- **Subcutaneous emphysema**: air from a lung or airway injury tracks under the skin. The skin swells and **crackles** under pressure like crisp rice or fresh snow. It spreads from the chest wall to the neck and face over minutes to hours; in severe cases the eyelids swell shut and the voice becomes nasal `[K](H)`.
- **Traumatic asphyxia**: sustained compression of the chest (someone kneeling or standing on it, pinned under weight) produces a **deep purple-blue congestion of the face, neck and upper chest** with pinpoint petechiae and **bilateral subconjunctival haemorrhages**, sharply cut off at the level of the compression `[K](H)`. Onset within minutes of sustained compression; persists after release.

### Simulation parameters (ribs, flail, sternum)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `rib_fracture_compression_onset` | 0.20 | fraction of chest depth | Frontal blunt; lateral similar `[E]` | `[K](M)` |
| `flail_compression` | 0.35–0.40 | fraction | | `[K](M)` |
| `hammer_rib_fracture_prob` | 0.5–0.8 (lateral chest), 0.3–0.5 (anterior, cartilage absorbs) | prob. | Per full-force blow | `[E]` |
| `punch_rib_fracture_prob` | 0.02–0.1 (ribs 9–11 highest) | prob. | Per punch | `[E]` |
| `flail_definition` | ≥ 3 adjacent ribs × ≥ 2 fractures each | — | | `[K](H)` |
| `flail_paradox_amplitude` | quiet 5–10, laboured 10–30, distress up to 50 | mm | Inward on inspiration | `[E]` |
| `flail_splint_mask_time` | 5–120 | min | Paradox scaled by (1 − splint), splint decays with fatigue | `[E]` |
| `flail_resp_rate` | 25–40 | /min | Shallow; grunt at end-inspiration | `[K](M)` |
| `sternal_step` | 5–15 | mm | | `[K](M)` |
| `subcut_emphysema_spread` | chest → neck 10–60 min, → face 30–180 min | — | Blend shapes + crackle audio on contact | `[K](M)` |
| `traumatic_asphyxia_onset` | 1–5 min of sustained compression ≥ ~ body weight | — | Face/neck purple `#5A3A6A` with petechiae | `[K](M)` |

### Visual/behavioural checklist (ribs, flail, sternum)

- A patch of the chest wall sinks in when the victim breathes in and bulges when they breathe out; it gets more obvious as they tire.
- The victim takes fast shallow breaths with a grunt, holds the side, leans toward it and refuses to lie flat.
- Crackling swelling spreads from the chest up to the neck and face.
- Someone pinned under weight turns deep purple from the chest up, with red-blotched eyes.
- Sounds: a muffled snap on the blow, then a soft grating with breathing.

---

## 10. Heart wounds: appearance and how they bleed

Round one covers the physiology: the 10–15 s rule, tamponade pressures and volumes, time courses `[R1-03 §8.2]`, `[R1-04 §8]`. This section covers what the heart and pericardium look like and how each part bleeds.

### 10.1 Reference numbers

| Item | Value | Tag |
|---|---|---|
| Heart mass / size | 280–350 g; ~12 × 8–9 × 6 cm | `[K](H)` |
| Wall thickness | LV 9–12 mm; RV 3–5 mm; atria 2–3 mm | `[K](H)` |
| Chamber hit in stab wounds of the heart | RV ~35–45 %, LV ~30–40 %, RA ~10–20 %, LA ~5 %; more than one chamber in ~20–30 % | `[K](M)` |
| Pericardium | Fibrous, 1–2 mm, semi-translucent; normally 15–50 mL of clear straw fluid | `[K](H)` |
| Blood in the pericardium at autopsy in fatal tamponade | ~150–450 mL (often 250–350), liquid plus clot | `[K](M)`; clinical tamponade volume `[R1-03 §8.1]` |

### 10.2 How each part of the heart bleeds

| Site | Pressure (sys/dia, mmHg) | Blood colour | When exposed (open chest or large defect) | Self-sealing | Tag |
|---|---|---|---|---|---|
| **Left ventricle** | 120 / 5–12 | Scarlet | **Systole-only jets** synchronised with the apex beat, 20–60 cm through an open wound, almost nothing in diastole | Small (< 1 cm), oblique stab tracks often close temporarily with muscle contraction and clot → tamponade | `[K](M)`, `[E]` |
| **Right ventricle** | 25 / 0–8 | Dark red (venous) | Low surges 5–30 cm in systole, welling between | Sometimes; low pressure helps | `[K](M)`, `[E]` |
| **Right atrium** | 0–8, with a and v waves | Dark red | Continuous dark welling with a double swell per heartbeat; sucks slightly in inspiration | Poor (thin wall) | `[K](M)` |
| **Left atrium** | 5–12 | Scarlet | Continuous welling | Poor; rarely reached from the front | `[K](M)` |
| **Coronary artery** | aortic | Scarlet | Continuous pulsatile spurting in both systole and diastole; the muscle it supplies turns dusky, pale and stops contracting within minutes | No | `[K](M)` |
| Aortic root, pulmonary artery | — | — | See `[R1-03 §5]` | — | `[R1-03]` |

### 10.3 Wound morphology

| Weapon | Heart | Pericardium | Tag |
|---|---|---|---|
| Knife | Slit wound ≈ blade width (10–30 mm), straight edges; gapes in the LV where it crosses the fibre direction; oblique track through the wall | Slit 1–3 cm, often plugged by clot or epicardial fat → tamponade | `[K](M)` |
| Handgun | Entrance 5–10 mm, ragged; exit 10–20 mm; through-and-through wounds of two chambers or the septum | Holes; usually leaks into the pleura → haemothorax | `[K](M)` |
| Rifle / close shotgun | **Hydraulic bursting** of the blood-filled chambers: ragged stellate ruptures 3–8 cm, septum and valves torn; the heart may be fragmented or pulped | Torn widely; massive left haemothorax (1–3 L) | `[K](M)` |
| Blunt (stomp, hammer to the sternum) | Contusion: dark red-purple patches under the epicardium (RV front first); rarely rupture (atria and RV) | Usually intact | `[K](M)` |

### 10.4 Tamponade appearance

- Pericardial sac **distended, tense and domed**, dark blue-purple because blood shows through the semi-translucent membrane (`#3A1A2E`) `[K](M)`.
- Heart motion inside is **damped**: small, fast, weak beats `[K](M)`.
- External signs: **distended neck veins**, dusky congested face, falling BP `[R1-03 §8.2]`.
- When the sac is opened (autopsy or surgery view): dark liquid blood gushes out, followed by a dark clot cast of the heart `[K](M)`.

### 10.5 The dying heart (render states)

| State | Appearance | Tag |
|---|---|---|
| Normal beating | Twisting contraction, apex moves toward the base; ~70–140 bpm in injury | `[K](H)` |
| Exsanguinated heart | Small, firmly contracted, empty, pale | `[K](M)` |
| Ventricular fibrillation | Surface shimmers and writhes ("bag of worms") at ~4–8 Hz, coarse at first then finer over minutes; no effective pumping | `[R1-06 §5.6]`, `[K](M)` |
| Agonal / PEA | Slow, weak, incomplete contractions | `[K](M)` |
| After death | Flaccid; later firm (myocardial rigor) | `[K](M)` |

### 10.6 Behaviour (hand-off)

- Destroyed heart: 10–15 s of possible voluntary action `[R1-04 §8.1]`.
- Knife wounds of the heart: purposeful activity for tens of seconds to minutes is common (`[R1-03 §5]`, Karger).
- Tamponade: progressive breathlessness, restlessness, pallor or dusky face, collapse over minutes.

### Simulation parameters (heart)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `stab_chamber_weights` | RV 0.40, LV 0.35, RA 0.15, LA 0.05, multiple 0.05 (adjust by entry point geometry) | prob. | Prefer ray-cast against the heart mesh | `[K](M)` |
| `lv_jet_phase` | systole only (0.1–0.35 s after R) | — | Diastolic flow ~5–10 % of systolic | `[K](M)`, `[E]` |
| `lv_jet_height_open` | 200–600 | mm | Through an open chest wall | `[E]` |
| `rv_jet_height_open` | 50–300 | mm | | `[E]` |
| `atrial_bleed_mode` | continuous welling, double swell per beat | — | Dark colour | `[K](M)` |
| `stab_self_seal_prob` | LV < 1 cm oblique 0.3–0.5; RV 0.2–0.4; atria 0.05–0.1 | prob. | Sealed wounds feed the pericardium (tamponade) | `[E]` from `[K](M)` |
| `pericardium_autopsy_volume` | 150–450 | mL | Fatal tamponade | `[K](M)` |
| `burst_heart_E_dep` | ≥ 500 | J | Rifle or close shotgun through the heart | `[E]` |
| `coronary_ischaemia_visual` | dusky/pale patch, contraction stops in 1–5 min | — | Downstream myocardium | `[K](M)` |
| `vf_visual_freq` | 4–8 | Hz | Amplitude decays over 2–10 min | `[K](M)` |

### Visual/behavioural checklist (heart)

- A left-ventricle wound squirts scarlet blood only when the heart contracts; a right-ventricle or atrial wound wells dark blood more steadily.
- A stabbed heart with the pericardium intact shows a tight, dark-blue bulging sac with a small, fast, feeble heart inside; the neck veins stand out.
- A rifle round bursts the heart into ragged pieces and floods the chest.
- A fibrillating heart quivers like a bag of worms and moves no blood.

---

## 11. Lung wounds: laceration, contusion, pneumothorax, haemothorax (appearance)

Round one covers the physiology and timelines `[R1-04 §9]` and bleeding `[R1-03 §8.3]`. This section covers appearance.

### 11.1 Reference numbers

| Item | Value | Tag |
|---|---|---|
| Lung mass | 400–600 g each (with blood) | `[K](M)` |
| Density (inflated) | 0.25–0.4 g/mL | `[K](M)` |
| Parenchymal bleeding pressure | Pulmonary artery mean ~15 mmHg | `[R1-03 §2.1]` |
| Tracheal lumen | 15–20 mm (adult male) | `[K](M)` |
| Open ("sucking") pneumothorax threshold | Chest-wall defect ≥ ~2/3 of the tracheal diameter (≈ 10–13 mm): air then enters through the wound in preference to the airway | `[K](H)` (ATLS) |

### 11.2 Appearance by injury

| Injury | Appearance | Numbers | Tag |
|---|---|---|---|
| Handgun track through the lung | Narrow permanent track, surrounding dark red haemorrhagic rim; pink froth at the openings | Track 5–15 mm; rim 5–20 mm | `[K](M)` |
| Rifle track | Wider haemorrhagic zone; lung elasticity limits the permanent damage | Zone 20–50 mm | `[K](M)` |
| **Laceration** (rib fragment, knife, blast) | Jagged tear; air bubbles and blood foam from the surface with each breath | 10–100 mm | `[K](M)` |
| **Contusion** | Dark plum, firm, heavy, airless areas; appear at impact, enlarge over hours as blood and fluid fill the alveoli | Clinical worsening over 4–24 h | `[K](H)` |
| **Collapsed lung** (pneumothorax) | Shrinks toward the hilum, dusky plum, rubbery; through a large chest wound it visibly shrinks within seconds of opening the chest | Collapse to 20–50 % volume | `[K](M)`, `[E]` |
| **Lung herniation** through a large chest-wall defect | Pink lung bulges out of the wound on coughing, straining or expiration against a closed glottis | Bulge 1–5 cm | `[K](M)` |
| **Haemothorax** | Dark liquid blood with soft clots in the pleural cavity; partly defibrinated, so much stays liquid | Volumes `[R1-03 §8.1]` | `[R1-03]` |
| Haemoptysis | Bright red frothy blood coughed from the mouth and nose; fine spray | — | `[R1-04 §9.3]` |

### 11.3 The sucking chest wound

- A chest-wall defect larger than ~10–13 mm (close shotgun, rifle exit, large knife wound) lets air in and out through the wound `[K](H)`.
- **Inspiration**: an audible suck or hiss; blood at the wound is drawn in; the edges pull inward `[K](M)`.
- **Expiration**: blood at the wound **froths and bubbles**; pink foam builds up around the hole; fine droplets spray `[K](M)`.
- A handgun entrance (4–6 mm) is below the threshold; it can still bubble a little if the lung is injured `[K](M)`.
- **Tension pneumothorax** (valve-like wound): over minutes the chest on that side stops moving and looks over-expanded, neck veins distend, the victim becomes agitated, grey-blue and collapses; tracheal shift is a late sign `[K](H)`; physiology `[R1-04 §9.2]`.

### Simulation parameters (lung)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `open_ptx_defect_threshold` | 10–13 | mm | ≥ 2/3 tracheal Ø | `[K](H)` |
| `lung_track_rim` | handgun 5–20; rifle 20–50 | mm | Haemorrhage tint around the track SDF | `[K](M)` |
| `contusion_growth` | ×1.5–3 area over 4–24 h | — | Living only | `[K](M)`, `[E]` |
| `lung_collapse_time_open_chest` | 2–10 | s | To 20–50 % volume | `[E]` |
| `lung_herniation_bulge` | 10–50 | mm | On cough or Valsalva through large defects | `[K](M)` |
| `sucking_wound_audio` | suck/hiss on inspiration, bubbling on expiration | — | At the current RR | `[K](M)` |
| `froth_bubble_size` | 0.1–1 (stable pink foam), 2–10 (large bubbles at the wound) | mm | | `[E]` |

### Visual/behavioural checklist (lung)

- A large chest wound sucks air on each breath in and blows pink froth on each breath out.
- Through a large chest wound, the lung shrinks into a dark rubbery mass; if the victim coughs, pink lung can bulge out of the hole.
- A bruised lung is dark plum and solid; the victim coughs frothy bright blood and becomes more breathless over time.

---

## 12. Liver, spleen and kidney (AAST grades and appearance), bowel evisceration

Round one covers bleed rates and time courses for these organs `[R1-03 §5, §8.4]`. This section covers the grading and the look.

### 12.1 Reference numbers

| Organ | Mass | Size | Position | Tag |
|---|---|---|---|---|
| Liver | 1.4–1.6 kg | ~25 × 15 × 15 cm (right lobe largest) | Right upper abdomen under ribs 7–11; lower edge at the right costal margin | `[K](H)` |
| Spleen | 150 g (100–250) | ~12 × 7 × 4 cm | Left, under ribs 9–11, posterolateral | `[K](H)` |
| Kidney | 130–150 g each | ~11 × 6 × 3 cm | Retroperitoneal, T12–L3, in Gerota's fascia and perirenal fat | `[K](H)` |

### 12.2 AAST organ injury scales (2018 revision)

Use the grade as the organ-damage state key. The grades below follow the 2018 AAST revision (Kozar et al.) as I recall it `[K](M)`; verify against the published table before exposing grades to the player.

**Liver**

| Grade | Criteria |
|---|---|
| I | Subcapsular haematoma < 10 % of surface area; parenchymal laceration < 1 cm deep |
| II | Subcapsular haematoma 10–50 %; intraparenchymal haematoma < 10 cm; laceration 1–3 cm deep and ≤ 10 cm long |
| III | Subcapsular haematoma > 50 % or ruptured; intraparenchymal haematoma > 10 cm; laceration > 3 cm deep; any vascular injury or active bleeding contained within the liver parenchyma |
| IV | Parenchymal disruption of 25–75 % of a hepatic lobe; active bleeding extending beyond the liver into the peritoneum |
| V | Parenchymal disruption > 75 % of a hepatic lobe; juxtahepatic venous injury (retrohepatic vena cava, central major hepatic veins) |

**Spleen**

| Grade | Criteria |
|---|---|
| I | Subcapsular haematoma < 10 %; laceration < 1 cm deep; capsular tear |
| II | Subcapsular haematoma 10–50 %; intraparenchymal haematoma < 5 cm; laceration 1–3 cm deep |
| III | Subcapsular haematoma > 50 % or ruptured; intraparenchymal haematoma ≥ 5 cm; laceration > 3 cm deep |
| IV | Vascular injury or active bleeding confined within the splenic capsule; laceration involving segmental or hilar vessels with > 25 % devascularisation |
| V | Shattered spleen; vascular injury with active bleeding extending beyond the spleen into the peritoneum |

**Kidney**

| Grade | Criteria |
|---|---|
| I | Parenchymal contusion or subcapsular haematoma without laceration |
| II | Perirenal haematoma confined to Gerota's fascia; laceration ≤ 1 cm deep without urinary extravasation |
| III | Laceration > 1 cm without collecting-system rupture; vascular injury or active bleeding contained within Gerota's fascia |
| IV | Laceration into the collecting system with urinary extravasation; renal pelvis laceration or ureteropelvic disruption; segmental artery or vein injury; active bleeding beyond Gerota's fascia; segmental or complete infarction from vessel thrombosis |
| V | Main renal artery or vein laceration or avulsion of the hilum; devascularised kidney with active bleeding; shattered kidney with loss of identifiable anatomy |

**Game mapping** `[E]` from `[K](M)`:

| Weapon | Liver | Spleen | Kidney |
|---|---|---|---|
| Knife stab | II–III (depth-dependent) | II–IV | II–IV |
| Handgun through the organ | III (track > 3 cm) with 1–3 cm stellate fissures; IV if hilar | III–V | III–IV |
| Rifle / close shotgun | IV–V: stellate bursting | V | IV–V |
| Kick, stomp, hammer (blunt) | I–III (IV with heavy stomps) | I–IV; **delayed rupture** possible | I–III |
| Fist | I–II (rarely III) | I–III | I–II |

### 12.3 Appearance

| Organ / injury | Appearance | Numbers | Tag |
|---|---|---|---|
| Liver, knife | Straight clean laceration through the glossy capsule into dark red-brown friable tissue; oozes steadily; bile-green staining if a duct is cut | Depth per blade | `[K](M)` |
| Liver, handgun | Round track 1–2 cm with a 0.5–1 cm haemorrhagic rim and **short stellate fissures** radiating 1–3 cm | — | `[K](M)` |
| Liver, rifle / close shotgun | **Stellate bursting**: fissures radiating 3–10+ cm from the track, 1–5 cm deep; loose fragments 1–10 cm floating in blood; whole segments pulped | 5–15 fissures | `[K](M)`, `[E]` |
| Subcapsular haematoma (liver, spleen) | Capsule lifted by a tense, dark blue-black, glossy blood blister; may rupture later | 1–10 cm | `[K](M)` |
| Spleen, laceration | Dark purple-red pulp welling through a capsular tear; soft, bleeds heavily | — | `[K](M)` |
| Spleen, shattered | Fragmented into several pieces within a large clot | 3–10 pieces | `[K](M)` |
| Kidney, laceration | Radial splits running from the surface toward the hilum through the pale cortex band into the darker medulla; perirenal haematoma spreading in the yellow fat inside Gerota's fascia; urine-tinged fluid | — | `[K](M)` |
| Kidney, shattered | Multiple fragments within the fascia; haematuria at any urination | — | `[K](M)` |
| Haemoperitoneum (abdomen opened) | Dark red liquid blood and clots between the bowel loops; a larger "sentinel" clot next to the injured organ | Volumes `[R1-03 §8.1]` | `[R1-03 §8.4]` |

### 12.4 Delayed splenic rupture

A subcapsular haematoma or contained injury can rupture hours to days later with sudden collapse `[K](H)`. For a session-length game: an optional event 30 min – 48 h after blunt left-flank trauma, with low probability (0.02–0.1 per grade I–III blunt splenic injury `[E]`).

### 12.5 Bowel and omentum through abdominal wounds (evisceration)

| Item | Appearance / value | Tag |
|---|---|---|
| Omentum | Yellow fatty apron (`#E8C870`) with fine vessels; usually the first thing to protrude through a 3–5 cm wound | `[K](M)` |
| Small bowel | Glistening pink-grey serosa (`#D9A8A0`), 2.5–3 cm diameter; slow peristaltic waves travel along it (visible writhing, ~8–12 contractions per minute) | `[K](M)` |
| Colon | Greyer, larger (4–7 cm), with longitudinal muscle bands and fat tags | `[K](M)` |
| Mesentery | Fatty fan carrying arcades of pulsating arteries and dark veins | `[K](M)` |
| Protrusion | Increases with coughing, straining, screaming; a 3–5 cm abdominal wound is enough for omentum; > 5–8 cm for bowel loops | `[K](M)`, `[E]` |
| Strangulated loop | Turns dusky purple over 30–120 min if trapped by the wound edges | `[K](M)` |
| Perforated bowel | Small bowel: yellow-green liquid content; colon: brown faecal content and smell | `[K](H)` |

### 12.6 Behaviour

- Abdominal wounds: guarding (tense abdominal wall), curling up with knees drawn up, shallow breathing to avoid moving the abdomen, nausea and vomiting `[K](H)`.
- Left shoulder-tip pain with splenic bleeding (Kehr's sign) `[R1-03 §8.4]`.
- Eviscerated bowel: the victim tries to hold it in with the hands and bends forward `[K](M)`.
- Progressive shock with little external blood: the wound drips while the victim turns pale and confused `[R1-03 §8]`.

### Simulation parameters (abdominal organs)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `organ_grade` | AAST I–V per §12.2 | enum | Drives bleed rate `[R1-03 §5]` and the render state | `[K](M)` |
| `liver_stellate_fissure_len` | handgun 10–30; rifle 30–100+ | mm | Radiating from the track | `[K](M)`, `[E]` |
| `liver_fragment_count_rifle` | 3–15 | count | Loose pieces 10–100 mm | `[E]` |
| `subcapsular_haematoma_size` | 10–100 | mm | Tense dome; rupture probability 0.05–0.2/h while BP is normal `[E]` | `[K](M)` |
| `delayed_splenic_rupture_prob` | 0.02–0.1 | per blunt grade I–III | 30 min – 48 h | `[E]` |
| `evisceration_wound_min` | omentum 30–50, bowel 50–80 | mm | Abdominal wall wound length | `[K](M)`, `[E]` |
| `peristalsis_rate` | 8–12 | /min | Wave speed 1–2 cm/s | `[K](M)` |
| `bowel_strangulation_time` | 30–120 | min | Colour → dusky `#6A3A5A` | `[K](M)` |

### Visual/behavioural checklist (abdominal organs)

- A liver hit by a rifle round is split into a star of deep cracks and loose chunks; by a knife, a clean cut that oozes dark blood.
- A burst spleen is a dark purple-black pulpy mass inside a big clot.
- A kidney cracks toward its centre; the urine turns red.
- Omentum or bowel bulges out of a long belly wound, glistening, slowly writhing, pushed out further when the victim coughs; the victim clutches it and bends forward.

---

## 13. Bone and teeth as secondary missiles

### 13.1 Mechanism

When a bullet strikes bone, bone fragments are accelerated and travel through the tissue as secondary projectiles, each making its own wound track; they enlarge the exit and can leave small separate "satellite" exits `[K](H)` (`[R1-01 §10, S34]` for teeth). Inner-table skull fragments are driven into the brain along the first centimetres of the track `[R1-01 §5.4]`. Fragments of vertebral laminae or bodies driven into the canal injure the spinal cord even when the bullet itself misses it `[K](H)`.

### 13.2 Numbers

| Situation | Fragments | Size | Velocity | Penetration | Spread | Tag |
|---|---|---|---|---|---|---|
| Handgun through the skull (entrance) | 3–15 inner-table chips | 1–10 mm | 30–150 m/s | 1–5 cm into the brain | Cone, half-angle 20–40° around the track | `[E]` from `[K](M)` |
| Rifle through the skull | See §3 plates plus 20–100 chips | 1–30 mm | 50–300 m/s | Throughout the cavity | 30–60° | `[E](L)` |
| Handgun through a long-bone shaft | 3–10 | 2–20 mm | 20–80 m/s | 1–3 cm | 20–40° down-range | `[E]` |
| Rifle through a long-bone shaft | 20–100+ | 1–30 mm ("bone snow" on X-ray) | 50–300 m/s | 2–10 cm | 20–45° down-range | `[E](L)` |
| Rib struck by a bullet | 2–10 | 2–15 mm | 20–100 m/s | 1–3 cm into the lung | 20–40° | `[E]` |
| Teeth (bullet or pellet through the mouth) | 1–12 teeth fractured; 2–30 pieces | 0.5–8 mm | 10–100 m/s | 5–30 mm into the tongue, cheek, floor of the mouth; occasionally the neck | Wide, 40–70° | `[R1-01 §10]`, `[E]` |
| Vertebra struck | 2–10 | 1–10 mm | 20–100 m/s | Into the canal | — | `[E]` |

Fragments leaving the body: only those above the skin-perforation threshold (~50–75 m/s `[R1-01 v_skin_perforation_min]`) exit; slower fragments stay under the skin as palpable lumps near the exit `[R1-01]`, `[E]`.

### Simulation parameters (secondary missiles)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `sec_frag_count(bone, weapon)` | §13.2 | count | Spawn as short ray-cast tracks, not rigid bodies | `[E]` |
| `sec_frag_speed` | handgun 20–150; rifle 50–300 | m/s | | `[E](L)` |
| `sec_frag_cone_half_angle` | 20–45 (teeth 40–70) | ° | Around the bullet's post-impact direction | `[E]` |
| `sec_frag_penetration` | handgun 10–50; rifle 20–100 | mm | Each track cuts tissue it crosses (vessels, lung) | `[E]` |
| `satellite_exit_prob` | 0.1–0.3 handgun; 0.3–0.7 rifle | prob. | 2–5 mm holes 1–5 cm from the main exit | `[E]` |
| `sub_skin_fragment_lump` | fragments < 50–75 m/s at the skin | — | Small bulge + bruise if alive | `[R1-01]`, `[E]` |

### Visual/behavioural checklist (secondary missiles)

- Bone chips stick out of rifle exits; small extra holes sit around a rifle exit where fragments came out separately.
- In the brain, a spray of bone chips lies along the first few centimetres of the track (X-ray or cut view).
- Tooth pieces are embedded in the tongue and cheeks after a mouth or jaw shot.
- A bullet near the spine can paralyse without touching the cord, because bone fragments do it.

---

## 14. Neck wounds, near-decapitation and decapitation

Round one covers bleed rates and times for carotid, jugular and throat-cut wounds, air embolism and neck-vein behaviour `[R1-03 §2.2, §5]`, and cord levels `[R1-04 §6]`. This section covers appearance and the extreme end.

### 14.1 Reference numbers

| Item | Value | Tag |
|---|---|---|
| Neck circumference (adult male) | 36–42 cm | `[K](M)` |
| Skin to trachea in front (at the cricoid) | 1–2 cm | `[K](M)` |
| Carotid sheath depth under the sternocleidomastoid | 2–4 cm | `[K](M)` |
| Trachea | Lumen 15–20 mm; 16–20 C-rings; 10–12 cm from the cricoid (C6) to the carina (T4–5) | `[K](H)` |
| Larynx | Thyroid cartilage (often partly ossified in adults: cut face shows bone islands); thyrohyoid membrane above, cricothyroid membrane below | `[K](H)` |
| Common carotid / internal jugular | 6–8 mm / 10–20 mm | `[R1-03 §5]` |
| Cervical vertebral body height / disc | ~15 mm / 4–6 mm | `[K](M)` |
| Cervical cord (transverse) | 10–13 mm | `[R1-05 §9.2]` |
| Osteoligamentous neck tensile failure | roughly 3–5 kN (whole neck with muscle and skin higher) | `[K](L)` |

### 14.2 Cut throat: what is exposed and what it does

| Depth reached | Appearance | Function and sound | Tag |
|---|---|---|---|
| Skin, platysma | Gaping 1–3 cm (the platysma and skin retract); fat; superficial veins (external jugular) bleed dark | Normal voice | `[K](M)` |
| Strap muscles, thyroid | Red muscle bands retract; thyroid gland (dark red-brown, lobulated, `#8A3A30`) bleeds briskly | Normal voice | `[K](M)` |
| **Larynx through the thyrohyoid membrane** | Common level in cut throats: the epiglottis becomes visible in the wound; the larynx gapes | Air escapes above the vocal cords: hoarse, breathy voice; bubbling | `[K](M)` |
| **Trachea / cricothyroid** | Cartilage rings (`#DCE0DC`) and the pink mucosa exposed; the lower tracheal segment retracts downward 1–3 cm; the wound gapes 3–5 cm with the head extended | **No voice** (air leaves below the cords); breath hisses in and out of the wound; exhaled air **bubbles through the blood** (bubbles 2–15 mm, pink foam); inspiration **sucks blood into the trachea** → violent coughing that sprays blood **out of the neck wound** | `[K](H)` |
| **Carotid sheath** | Carotid jets scarlet (`[R1-03 §6.2]` heights and throws); internal jugular pours dark blood, surges on expiration, sucks air on inspiration (air embolism risk `[R1-03 §5]`) | Rapid collapse `[R1-03 §5]` | `[R1-03]`, `[K](H)` |
| **Oesophagus** | Collapsed muscular tube behind the trachea; swallowed saliva and blood leak into the wound | — | `[K](M)` |
| **Prevertebral muscles and spine** | Knife stops on the vertebral bodies; notches on the bone | — | `[K](H)` |

Head position changes the wound: extension opens it widely; flexion (chin down) closes it and reduces bleeding and bubbling `[K](M)`.

### 14.3 Gunshot wounds of the neck

- Handgun: small entrance; if the trachea or larynx is hit, air and bubbling blood at the wounds, subcutaneous emphysema spreading over the neck and face (§9.5), hoarse or absent voice `[K](M)`.
- Cord hit at C1–C4: immediate flaccid quadriplegia and apnoea (`[R1-04 §6]`).
- Rifle: large exit; the transverse processes, vertebral arteries and cord are often involved `[K](M)`.
- **Close shotgun to the neck: near-decapitation**. The anterior or lateral neck is destroyed, the spine disrupted, and the head remains attached by a bridge of skin and posterior muscles `[K](M)`.

### 14.4 Near-decapitation (appearance)

| Feature | Description | Tag |
|---|---|---|
| Head | Hangs back or sideways under gravity, hinged on the remaining tissue bridge; moves loosely when the body is moved | `[K](M)` |
| Wound | Gapes 5–15 cm; cut or broken vertebra or disc visible; trachea and oesophagus open; carotid stumps jetting; jugulars collapsed | `[K](M)` |
| Cord | Transected: immediate loss of all movement and breathing below the level | `[R1-04 §6]` |

### 14.5 Complete decapitation

**Mechanism and feasibility** `[K](M)`:
- Soft tissues of the neck can be cut with a knife; the **vertebral column cannot be cut with an ordinary knife** except by finding a disc space and severing the ligaments. Heavy chopping blades separate the neck in one or several blows. Blast, vehicles and extreme hanging drops tear it off (tension of several kN, §14.1).
- Game implication: a knife decapitation is a long, multi-step process (dozens of strokes, 30–120 s), not a single action `[E]`.

**Body stump** `[K](M)`:

| Structure | Appearance |
|---|---|
| Skin | Retracts 1–3 cm; margins incised (blade) or torn with tissue bridges (tearing) |
| Muscles | Retract unevenly: sternocleidomastoid 2–4 cm, strap and posterior muscles less; red bands at different levels |
| Trachea | Open ring of cartilage retracting 1–3 cm into the root of the neck |
| Oesophagus | Collapsed tube behind it, retracting |
| Carotids | Round pale stumps jetting scarlet blood for several beats, then weakening as pressure collapses |
| Jugulars | Flat stumps; dark welling; may suck air |
| Spine | Cut or disarticulated end: white annulus fibrosus with a gel-like nucleus (`#D8DDD2`) at a disc level, or cancellous red bone |
| Cord | White cylinder 10–13 mm in its dural sheath, pouting slightly; cross-section shows a grey butterfly in white |

**Bleeding** `[E]` from `[R1-03 §5]`: both carotids and vertebrals open at once; MAP collapses within 5–15 s; jets start at 20–60 cm and fade to welling within 10–30 s; the heart continues to beat for minutes, but with no effective pressure. External loss from the body stump 500–1,500 mL over 1–3 min. The head loses 100–300 mL passively.

**The body** `[K](M)`: drops instantly and flaccidly (cord transection, spinal shock); brief jerks or tremor of the limbs in the first seconds are possible; no running or coordinated movement.

**The head** `[K](M)`:
- Cerebral perfusion stops instantly. Loss of consciousness is estimated at **~2–10 s** (brain oxygen reserve `[R1-03 §3.5]`). Rodent decapitation EEG studies show loss of cortical activity within a few seconds (van Rijn et al.) `[K](M)`.
- Visible for up to ~10–30 s: eyes open, facial twitches, grimacing, lip and jaw movements, and **gasp-like mouth opening** if the medulla remains with the head (hypoxic gasping from the respiratory centre) `[K](M)`.
- Pupils constrict briefly then dilate over 30–90 s `[K](M)`.
- Historical reports of guillotined heads responding to their names are anecdotal and unreliable `[K](L)`.

### Simulation parameters (neck and decapitation)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `neck_cut_gape` | skin 10–30; through the trachea 30–50 (head extended); × 0.3–0.5 when flexed | mm | | `[K](M)`, `[E]` |
| `trachea_retraction` | 10–30 | mm | Lower segment | `[K](M)` |
| `tracheal_bubble_size` | 2–15 (foam 0.1–1) | mm | One burst per exhalation | `[E]` |
| `voice_state` | normal (above larynx) / hoarse (thyrohyoid) / aphonic (at or below cords) | enum | | `[K](H)` |
| `aspiration_cough_spray` | 1–3 coughs per 10 s while blood enters the airway | — | Sprays out of the neck wound and mouth | `[K](M)`, `[E]` |
| `knife_decap_strokes` | 30–80 strokes, 30–120 s | — | Only through a disc space | `[E]` |
| `neck_tensile_failure` | 3–5 (osteoligamentous) | kN | Tearing, blast | `[K](L)` |
| `stump_jet_decay` | 20–60 cm → welling in 10–30 s | — | | `[E]` |
| `stump_external_loss` | 500–1,500 over 1–3 min | mL | | `[E]` |
| `severed_head_loc_time` | 2–10 (default 6) | s | | `[K](M)` |
| `severed_head_movement_window` | 10–30 | s | Twitches, jaw/lip movements, gasps | `[K](M)` |
| `severed_head_passive_loss` | 100–300 | mL | | `[E]` |

### Visual/behavioural checklist (neck and decapitation)

- A throat cut through the windpipe: no voice, air hissing in and out of the neck, blood bubbling with each breath out, and coughing that sprays blood from the wound itself.
- Carotid jets are scarlet and pulse; jugular blood is dark and surges when the victim breathes out or screams.
- Near-decapitation: the head flops back or sideways on a bridge of tissue.
- After decapitation the body collapses limply; the stump jets for a few seconds, then wells. The head's eyes stay open; the face may twitch and the mouth may open and close a few times in the first seconds.

---

## 15. Bloodstain patterns for the scene

Round one covers blood as a material, drop physics, rivulets, pools, drying and colour ageing `[R1-03 §1, §10]`, spurt heights `[R1-03 §6.2]`, and head-shot back/forward spatter `[R1-01 §7]`. This section adds the pattern types a forensic examiner would recognise, with the numbers needed to generate them. Terminology follows the SWGSTAIN / bloodstain-pattern-analysis conventions `[K](H)`.

### 15.1 Pattern taxonomy

| Class | Pattern | Mechanism | Key features | Typical stain size | Game source | Tag |
|---|---|---|---|---|---|---|
| Passive | Drip stain / drip trail | Gravity | Round to slightly elongated drops; satellites when falling into blood | 10–20 mm on hard floors | Any bleeding wound, moving or still | `[R1-03 §10.1]` |
| Passive | Flow | Gravity on surfaces | Rivulets following gravity; direction shows position at the time | — | Bodies, walls | `[R1-03 §10.2]` |
| Passive | Pool / saturation | Accumulation | Pool; soaked fabric | — | Collapse sites | §15.6 |
| Spatter | Impact spatter | Force applied to exposed blood | Radiating small stains | 0.5–4 mm | Hammer, fist, stomp, gunshot | §15.4, `[R1-01 §7]` |
| Spatter | Cast-off | Blood flung from a moving object | Linear or curved trails of elongated stains | 2–8 mm | Hammer, knife, bloody hands | §15.3 |
| Spatter | Cessation cast-off | Object stops abruptly | Drops thrown ahead of the impact site | 1–6 mm | Hammer, knife | §15.3 |
| Spatter | Projected (arterial) | Blood under arterial pressure | Large stains, flows, arcs or zigzags, one group per heartbeat | 5–30+ mm | Neck, groin, arm arteries | §15.2 |
| Spatter | Expirated | Blood blown from the airway | Small stains with air bubbles/vacuoles, often diluted | 0.1–4 mm | Face, lung, neck wounds | §15.8 |
| Altered | Clotted, diluted, skeletonised, sequenced, void | Time and disturbance | See §15.9 | — | Time passing, player actions | §15.9 |
| Transfer | Contact, swipe, wipe, pattern transfer (footwear, hand, hair, fabric, drag) | Contact with a bloody surface | Recognisable shapes; feathering shows direction | — | Walking, crawling, dragging, touching | §15.7 |

### 15.2 Projected (arterial) patterns

| Feature | Value / description | Tag |
|---|---|---|
| Blood per pulse from a carotid or femoral wound | 8–25 mL (1,000–2,500 mL/min at HR 100–140) | `[E]` from `[R1-03 §5]` |
| Stains | Large stains 5–30 mm with spines and satellites; gush deposits up to 50 mm | `[K](M)`, `[E]` |
| Arrangement | One cluster per heartbeat, arranged along an **arc, wave or zigzag** that traces the movement of the wound | `[K](H)` |
| Spacing between clusters | = wound speed × beat interval (e.g. head turning at 0.5 m/s, HR 120 → ~25 cm) | `[E]` |
| Flows on vertical surfaces | Stains from drops ≥ ~4–5 mm (≥ 30–60 µL) run downward 5–50 cm | `[E]` |
| Height on a wall from a standing neck wound | Mainly 1.2–1.8 m; up to the ceiling at the first systolic peaks in a 2.4 m room | `[E]` from `[R1-03 §6.2]` |
| Sequence | First clusters largest and highest; later clusters lower, smaller and closer to the victim as BP falls and HR rises | `[K](M)`, `[E]` |
| "Arterial rain" | Fine field of round 3–10 mm drops falling onto horizontal surfaces from high jets | `[K](M)` |
| On the victim | Heavy on the chest, shoulder and arm on the wound side; hands bloody from clutching | `[K](M)` |

### 15.3 Cast-off and cessation cast-off

- **Release physics** `[E]`: blood clinging to a moving object detaches when the centripetal acceleration overcomes adhesion. From Tate's law, the detaching drop volume scales as `V ≈ 50 µL × g / a`. A hammer head at 10 m/s on a 0.6 m swing radius (a ≈ 17 g) releases ~3 µL drops (~1.8 mm); a knife tip at 8 m/s on 0.7 m (a ≈ 9 g) releases ~5–6 µL (~2.2 mm); a bloody hand swung loosely (a ≈ 3–5 g) releases 10–15 µL (~3 mm).
- Resulting stains: **2–8 mm**, elongated; tails point in the direction of the swing; elongation increases along the trail where the drops strike more obliquely `[K](M)`, `[E]`.
- **Trail geometry**: a line or gentle curve 0.3–2 m long, about as wide as the weapon (1–5 cm), with **5–60 stains** `[E](L)`; mostly from the **backswing**, landing behind and above the attacker on the ceiling and walls, on the side of the swinging arm `[K](H)`.
- **No cast-off from the first blow**: the weapon is not yet bloody. Classic rule: minimum number of blows ≈ number of cast-off trails + 1 `[K](H)` (with caveats: not every swing throws blood).
- **Cessation cast-off**: when the weapon stops on impact, blood on it is thrown forward past the impact site as a short burst of 1–6 mm stains `[K](M)`.
- Repeated stabbing produces cast-off from the knife and from the bloody hand `[K](M)`.

### 15.4 Impact spatter from blows

| Feature | Value | Tag |
|---|---|---|
| Needs exposed blood | First blow on intact skin: almost none; spatter grows with later blows | `[K](H)` |
| Stain size | 0.5–4 mm, mostly 1–3 mm | `[K](M)` |
| Stains per blow (bloody wound) | 20–300 | `[E]` |
| Distribution | Radiating from the impact point; more in the direction the struck surface faces; reaches 0.5–1.5 m | `[K](M)`, `[E]` |
| On the attacker | Face, hands, forearms, chest and shoes peppered with 0.5–3 mm stains | `[K](H)` |
| Brain or bone in the spatter | Once the skull is open (§7.2): particles 1–10 mm mixed with blood | `[K](M)` |
| Punches | Spatter only after the face is already bleeding (nose, lips, brows): 1–3 mm stains on the fist, forearm and nearby surfaces | `[K](M)` |

### 15.5 Drip stains, drip trails, drip patterns

| Feature | Value | Tag |
|---|---|---|
| Drop / stain | 50 µL; 13–20 mm stain from 0.5–1 m on hard floors | `[R1-03 §10.1]` |
| Drip rate from a moderately bleeding hand or forearm wound | 1–5 drops/s; continuous stream above 15–30 mL/min | `[R1-03 §10.2]`, `[E]` |
| **Trail spacing** | = walking speed ÷ drip rate; 1.4 m/s at 1–3 drops/s → 0.5–1.4 m between stains; closer as bleeding increases | `[E]` |
| **Stain shape when walking** (hand at 0.8–1 m, 1.4 m/s) | Impact angle 70–73° → width/length 0.94–0.96: nearly round, with slightly scalloped edge and satellites toward the direction of travel | `[E]` (v_vertical = √(2gh) = 4.0–4.4 m/s) |
| **Running** (4 m/s) | Angle 45–48° → W/L 0.71–0.74: clearly elongated, spines and tail toward the direction of travel | `[E]` |
| Standing still (drip pattern) | Central pool with many satellite stains 1–4 mm radiating 0.3–1 m | `[R1-03 §10.1]` |
| Turning, stopping | Clusters of drops and a small pool where the victim paused | `[K](M)` |

### 15.6 Pools: edges, clotting, serum separation, drying

The pool size and spreading model is in `[R1-03 §10.3]`. The appearance over time:

| Time after deposition | Surface | Edge | Tag |
|---|---|---|---|
| 0–3 min | Liquid, mirror-glossy, uniform dark red; reflects the room; ripples when touched | Smooth raised meniscus 2–3 mm high; fingers along slopes and grout lines | `[R1-03]`, `[K](M)` |
| 3–15 min | **Gels**: stops spreading; a thin surface skin wrinkles when disturbed; a finger or foot leaves a **furrow that does not flow back** | Thin perimeter starts to darken | `[K](M)` |
| 15–60 min | Surface less glossy; darker | Outer 1–5 mm dries to a dark brown ring; clot retraction begins; beads of clear yellow serum appear at the edge and on top | `[K](M)` |
| 1–3 h | Clot pulls in from the edge (retracts to roughly half its volume within ~1–2 h) and becomes a dark maroon jelly island | **Serum ring** of clear straw-yellow fluid (`#E6D08A`, translucent) 2–20 mm wide on hard floors; a paler yellow halo 5–30 mm on absorbent surfaces | `[K](M)` |
| 3–12 h | Clot surface dull, near-black; serum ring dries to a shiny transparent varnish film | Film glossy, faintly yellow | `[K](M)` |
| 12–72 h | Dries to a dark crust that shrinks and cracks into plates ("mud-cracks") 2–20 mm; flakes at the edges | Serum film remains as a faint glossy outline | `[R1-03 §10.4]`, `[K](M)` |

Disturbing a pool after it has gelled leaves lumps, furrows and smears that do not level out, which dates the disturbance `[K](M)`. Blood mixed with CSF does not clot and spreads thinner and paler (§1.4).

### 15.7 Transfer patterns

| Pattern | Description | Numbers | Tag |
|---|---|---|---|
| **Footwear prints** | Stepping in blood loads the sole; the first 1–3 prints are heavy, smeared, sometimes with slip marks; the next prints show the tread best; the last show only heel and ball | Pick-up 2–10 mL; intensity falls to ~60–75 % per step; visible for ~5–15 steps | `[E]`, `[K](L)` |
| Step length | Walking 0.65–0.8 m; running 1.0–1.5 m | — | `[K](H)` |
| Bare footprints | Toe pads, ball, heel, outer edge; arch void; ridge detail in medium-intensity prints | — | `[K](H)` |
| **Hand prints** | Partial palm and finger outlines; the wounded victim leaning on walls leaves prints that **drag downward** as they slide down the wall | Slide marks 10–100 cm | `[K](M)` |
| **Swipe** | A bloody object moving across a clean surface: dense at the start, **feathered at the end** (feathering points in the direction of movement) | — | `[K](H)` |
| **Wipe** | An object moving through an existing wet stain: part of the stain removed, streaks and a displaced edge | — | `[K](H)` |
| **Drag trail** | A body dragged through blood: broad smear 20–50 cm wide with parallel striations from clothing and hair; drips and pools where it stopped; feathering and accumulation show direction | — | `[K](M)` |
| Hair swipe | Fine parallel curved lines 0.5–1 mm apart | — | `[K](M)` |
| Fabric | Weave pattern in contact stains | — | `[K](H)` |

### 15.8 Expirated patterns and mixtures

| Pattern | Description | Numbers | Tag |
|---|---|---|---|
| Expirated (coughed, sneezed, breathed) | Small stains, many with **air bubbles or vacuole rings**, lighter and pinker (diluted by saliva/mucus) | 0.1–4 mm; up to ~1–1.5 m | `[K](H)`, `[E]` |
| Blood + saliva | Stringy, bubbly, stretches | — | `[K](M)` |
| Blood + CSF | Watery pink; does not clot; on fabric a blood centre with a pale outer ring | — | `[K](M)` |
| Vomited blood | Dark red to brown clots, "coffee-ground" material if partly digested | — | `[R1-03 §7.3]`, `[K](M)` |
| Urine at death | Diluted pink-red if haematuria; spreads wide and thin | — | `[K](M)` |

### 15.9 Altered stains, voids and sequencing

- **Clotted drops**: blood from a clotting wound or a gelled pool leaves raised, gelatinous stains with dark centres `[K](M)`.
- **Diluted**: water, sweat or rain make pink, spread, paler stains (`[R1-03 §9.3]`) `[K](H)`.
- **Skeletonised**: the dried rim remains when the wet centre is wiped (rim dries in ~1 min for small drops) `[R1-03 §10.4]`.
- **Void**: a clean area with a sharp outline where a person or object blocked spatter; if the object is moved away the void remains and shows where it was `[K](H)`.
- **Sequencing**: later stains over dried earlier ones stay distinct; stains over wet ones merge; footprints through dried pools crack them `[K](M)`.
- **Moved body**: dried flows that point the "wrong" way `[R1-03 §10.2]`.

### 15.10 Event → pattern spawning table

| Event | Patterns to spawn | Tag |
|---|---|---|
| Gunshot, head | Back- and forward spatter `[R1-01 §7]`; bursting ejecta (§2.4); pool | `[R1-01]` |
| Gunshot, trunk or limb | Little external spatter at the entrance; forward spatter at the exit; drips and pool | `[R1-01]`, `[R1-03]` |
| Knife: first stab | Almost nothing external | `[K](M)` |
| Knife: repeated stabs | Backswing cast-off trails; cessation cast-off; hand and sleeve soaked; arterial pattern if an artery is cut | `[K](M)` |
| Neck cut | Projected arterial arcs; expirated spray from the neck and mouth; heavy flows on the victim's chest; large pool | `[K](M)` |
| Hammer: first blow | No spatter; scalp bleeds | `[K](H)` |
| Hammer: later blows | Impact spatter 20–300 stains per blow; cast-off trail per backswing; brain and bone particles once the skull is open | `[K](M)`, `[E]` |
| Punching a bleeding face | Small impact spatter on the fist, forearm, floor; drips from the nose and mouth; expirated spray when the victim coughs | `[K](M)` |
| Victim walking / crawling | Drip trail, hand prints and slide marks on walls, knee and hand smears on the floor | `[K](M)` |
| Victim collapses | Pool at the wound; saturation of clothing | `[K](M)` |
| Body dragged | Drag trail | `[K](M)` |
| Player steps in blood | Footwear prints fading over 5–15 steps | `[E]` |
| Time passes | Pool gel, serum ring, drying and colour ageing (§15.6, `[R1-03 §10.4]`) | `[K](M)` |

### Simulation parameters (bloodstain patterns)

| Parameter | Value / range | Unit | Notes | Tag |
|---|---|---|---|---|
| `arterial_volume_per_pulse` | 8–25 | mL | Carotid/femoral; scale with the wound flow | `[E]` |
| `arterial_stain_size` | 5–30 (gush ≤ 50) | mm | Spines and satellites | `[E]` |
| `vertical_run_threshold_drop` | 4–5 (30–60 µL) | mm | Larger stains on walls run 5–50 cm | `[E]` |
| `castoff_drop_volume` | 50 µL × g/a | µL | a = v²/r of the weapon point | `[E]` |
| `castoff_stain_size` | 2–8 | mm | | `[K](M)`, `[E]` |
| `castoff_stains_per_trail` | 5–60 | count | Requires blood on the weapon (≥ 1 prior bloody contact) | `[E](L)` |
| `castoff_trail_length` | 0.3–2 | m | Backswing plane | `[E]` |
| `impact_spatter_per_blow` | 20–300 | stains | Size 0.5–4 mm; only when blood is exposed at the site | `[E]` |
| `impact_spatter_range` | 0.5–1.5 | m | | `[K](M)` |
| `drip_trail_spacing` | v_walk / f_drip | m | | `[E]` |
| `drip_stain_WL` | sin(atan(√(2gh) / v_horizontal)) | — | h = drop height | `[E]` |
| `pool_gel_time` | 3–15 | min | Freeze spread; furrows persist | `[R1-03]`, `[K](M)` |
| `clot_retraction` | to ~50 % volume in 1–2 h | — | Island shrinks from the edge | `[K](M)` |
| `serum_ring_width` | 2–20 (hard), 5–30 (absorbent) | mm | Appears 30 min – 3 h | `[K](M)` |
| `footprint_pickup` | 2–10 | mL | | `[E]` |
| `footprint_decay_per_step` | 0.60–0.75 | × | Visible to ~5 % intensity (5–15 steps) | `[E]` |
| `expirated_stain_size` | 0.1–4 | mm | 30–60 % with vacuole rings; colour lightened 20–40 % | `[E]` |
| `void_mask` | per blocking collider at spawn time | — | Stamp before decals | `[E]` |

### Visual/behavioural checklist (bloodstain patterns)

- Arterial bleeding paints walls in arcs or zigzags of large drops with runs, one group per heartbeat, getting lower and smaller as the victim weakens.
- Hammer attacks leave fine spatter radiating from the head and lines of elongated drops on the ceiling behind the attacker, but none from the first blow.
- A walking victim leaves round drops at regular spacing; a running victim leaves elongated drops with tails pointing the way they went.
- Pools stop spreading and turn to jelly within about 10 minutes; after an hour or two a clear yellow ring of serum surrounds a shrunken dark clot; a day later the pool is a cracked dark crust.
- Bloody footprints fade over a dozen steps; handprints slide down walls where the victim leaned and slumped.
- Coughed blood leaves small pink stains with tiny bubble rings.
- Where a body or object blocked the spray there is a clean silhouette.

---

## 16. Common realism mistakes in games and films (with the fix)

| # | Mistake | Reality | Fix | Tag |
|---|---|---|---|---|
| 1 | Every head shot explodes the head | Bursting needs ~500–700 J deposited in the skull: rifles (variably), shotguns within ~1–3 m, slugs, contact magnums rarely. Handguns make holes and cracks | `E_dep` rule §2.1 | `[E]`, `[R1-01 §5.5]` |
| 2 | An exploding head is a uniform red cloud and a neck stump | The vault splits into plates and flaps; ejecta leave mostly down-range; the scalp often keeps many fragments in a soft bag; the face remains as a sagging mask | §2.3–2.4 | `[K](M)` |
| 3 | Headless or head-shot bodies run, crawl or thrash | Flaccid collapse; at most a jerk and a few seconds of twitching | §2.5, §14.5 | `[K](M)`, `[R1-04]` |
| 4 | Eyes pop out from punches | The orbital rim stops the fist; black eye and lid swelling instead. Hammers, thumbs, pellets and bullets do reach the globe | §5.1 | `[K](H)` |
| 5 | A ruptured eye is a neat hole or an empty black socket | Soft, deflated, wrinkled globe inside ballooned dark red conjunctiva, dark uveal bead and jelly-like vitreous at the wound | §5.3 | `[K](H)` |
| 6 | Losing the face or jaw is instant death | Often conscious and mobile; the threat is the airway; victims lean forward and choke when laid on their back | §4.4 | `[K](M)` |
| 7 | Broken bones look like snapped white sticks | Ivory cortical ring around a yellow greasy (shaft) or red spongy (bone-end) core, torn periosteum, fat droplets on the blood; spiral fractures end in long spikes | §8 | `[K](H)` |
| 8 | An open-fracture bone end is always sticking out | It often slips back under the skin when the limb straightens | §8.3 | `[K](H)` |
| 9 | Brain is grey chunks or solid lumps | Very soft pink-grey and cream paste that smears and strings; CSF makes it watery and pink | §1.4 | `[K](M)` |
| 10 | Everything inside the body is red | Yellow fat, silver fascia and tendon, cream nerves, ivory bone, purple spleen, red-brown liver, pink lung; muscle turns brighter red in air and brown after death | §1.1, §1.5 | `[K](M)` |
| 11 | Blood spatter is one generic splat decal | Arterial arcs and zigzags, cast-off lines on ceilings, radiating impact spatter, spaced drip trails, voids, footprints, smears | §15 | `[K](H)` |
| 12 | Blood pools stay glossy and liquid forever | Gel in 3–15 min, serum ring in 1–3 h, cracked crust after 1–3 days | §15.6 | `[K](M)` |
| 13 | The first hammer blow sprays blood | No exposed blood yet, so no spatter and no cast-off on the first blow | §15.3–15.4 | `[K](H)` |
| 14 | Chest wounds are silent | Large chest wounds suck and bubble with every breath | §11.3 | `[K](H)` |
| 15 | A victim with a cut windpipe screams | No voice below the vocal cords; air hisses from the neck; coughing sprays blood out of the wound | §14.2 | `[K](H)` |
| 16 | A heart wound drops the victim instantly | 10–15 s of possible action after destruction, tens of seconds to minutes after a stab | §10.6 | `[R1-04 §8]` |
| 17 | Liver and spleen hits look like muscle hits | Solid organs crack into stellate fissures and pulp; they bleed internally with little outside | §12 | `[K](H)` |
| 18 | Tamponade looks like ordinary blood loss | Distended neck veins and a dusky face with falling BP | §10.4 | `[R1-03 §8.2]` |
| 19 | A single knife swipe cuts the head off | The spine stops the blade; separation only through a disc space after many strokes, or with heavy chopping, blast or tearing forces | §14.5 | `[K](M)` |
| 20 | Bloody footprints stay perfect indefinitely | Heavy smeared first prints, then tread detail, then only heel and ball, fading over ~5–15 steps | §15.7 | `[E]` |

---

## 17. Cross-document notes

- **Burst rule.** `[R1-01 §5 burst_threshold]` uses a velocity switch (> 600 m/s). §2.1 here proposes an energy-deposit rule (`E_dep ≥ 500–700 J`) plus a contact-gas bonus. It reproduces the round-one outcomes (rifles burst, handguns do not, contact shotguns always) and also produces the observed variability of 5.56 head shots and the rare contact-magnum burst. Recommend adopting it and keeping `[R1-01]`'s `kronlein_probability` as the evisceration roll above 1,500 J.
- **Tamponade volume.** `[R1-03 §8.1]` gives 100–200 mL for acute clinical tamponade; §10.1 gives 150–450 mL found at autopsy. Both are correct: the autopsy volume includes blood that accumulated after the circulation failed. Use the clinical value to drive physiology and the autopsy value for the post-mortem (opened-chest) view.
- **Pool gel time.** `[R1-03 §10.3]` gives 5–15 min; §15.6 gives 3–15 min. Keep 5–15 min as the default; allow 3 min for thin films and warm surfaces.
- **Muscle colour.** `[R1-06 §5.4]` gives a single static muscle colour. §1.1 adds the air-exposure bloom and the post-mortem brown shift; use them as time-driven lerps on the same material.
- **Eyes.** `[R1-04 §11]` handles intact eyes during dying and after death. §5 here handles physically destroyed or displaced eyes. The eye system needs a mode switch: intact (R1-04) / ruptured / luxated / hanging / enucleated.

---

## 18. Load-bearing claims to verify first (QA list)

All values below are `[K]` or `[E]`; none was verified against a source in this session (§0.1). Check these first.

| # | Claim | Value | Tag | Verify against |
|---|---|---|---|---|
| 1 | Energy deposited in the skull decides bursting; threshold for vault burst | ~500–700 J; evisceration ≥ 1,000–1,500 J | `[E]` | DiMaio *Gunshot Wounds*; Kneubuehl *Wound Ballistics*; Krönlein-shot case literature |
| 2 | Contact 12-gauge head wounds always burst the vault; brain ejection fraction by site | 30–100 % ejected | `[K](M)`, `[E]` | DiMaio; Spitz & Fisher |
| 3 | Destroyed vault fragments often retained in the scalp ("bag"), head collapses | 20–60 % of fragments leave | `[E]` | Forensic autopsy descriptions of shotgun suicides |
| 4 | Submental/face-only trajectories often leave the victim conscious; airway obstruction when supine after loss of the mandibular symphysis | p(conscious) 0.7–0.9; LOC 1–3 min after complete obstruction | `[K](M)`, `[K](H)` | Maxillofacial gunshot series; ATLS airway chapter |
| 5 | Globe rupture risk: 50 % at a normalised energy of ~35,000 J/m²; the orbital rim (35 × 40 mm) protects from larger objects | — | `[K](M)`, `[K](H)` | Kennedy & Duma eye-injury risk functions; orbit anatomy |
| 6 | Blunt globe rupture occurs at the limbus or behind the rectus insertions (sclera ~0.3 mm) | Rectus insertion distances 5.5 / 6.5 / 6.9 / 7.7 mm | `[K](H)` | Ophthalmology texts (spiral of Tillaux) |
| 7 | Ruptured-globe signs: deflation, 360° haemorrhagic chemosis, peaked pupil, uveal prolapse, vitreous extrusion, hyphema | — | `[K](H)` | Ophthalmic trauma texts |
| 8 | Scalp avulsion occurs through the subgaleal plane; avulsion bleeding is not controlled by vessel retraction | 100–300 mL/min initially | `[K](H)` plane; `[E]` rate | Plastic-surgery reviews of scalp avulsion |
| 9 | Hammer comminution progression per blow (depth 3–10 mm/blow after fracture; 2–6 fragments/blow; mosaic zone 40–80 mm at 4–8 blows) | — | `[E]` | Forensic series of hammer homicides |
| 10 | Exposed brain herniating through a skull defect pulses with the heartbeat | 1–3 mm | `[K](M)`, `[E]` | Neurosurgical descriptions |
| 11 | Tibia (anteromedial, 3–8 mm cover) is the commonest open fracture; bone ends may re-enter the wound | — | `[K](H)` | Orthopaedic trauma texts; Gustilo–Anderson |
| 12 | Fracture pattern by mechanism (transverse/butterfly for direct blows, spiral for torsion, comminuted for high energy) | Spiral length 2–4 × Ø | `[K](H)` | Orthopaedic and forensic texts |
| 13 | Flail chest definition and paradoxical movement; excursion | ≥ 3 ribs × ≥ 2 places; 0.5–3 cm (up to 5) | `[K](H)` definition; `[E]` excursion | ATLS; thoracic trauma texts |
| 14 | Rib fractures begin at ~20 % chest compression; flail at ~35–40 % | — | `[K](M)` | Kroell; Viano blunt thoracic tolerance |
| 15 | LV wounds jet in systole only; RV and atrial wounds well dark blood; small LV stabs may self-seal → tamponade | — | `[K](M)` | Cardiac trauma surgery texts |
| 16 | Stab chamber distribution RV > LV > RA > LA | 40 / 35 / 15 / 5 % | `[K](M)` | Penetrating cardiac trauma series |
| 17 | Open pneumothorax when the chest-wall defect is ≥ 2/3 of the tracheal diameter | ~10–13 mm | `[K](H)` | ATLS |
| 18 | AAST 2018 grades for liver, spleen and kidney as tabulated | §12.2 | `[K](M)` | Kozar et al. 2018 |
| 19 | Liver/spleen/kidney (inelastic) burst into stellate fissures under rifle cavitation; lung and muscle (elastic) do not | Liver fissures 3–10+ cm | `[K](H)` mechanism, `[E]` numbers | Fackler; Kneubuehl |
| 20 | Cut trachea: aphonia, bubbling, aspiration-cough spray from the wound | — | `[K](H)` | Forensic cut-throat descriptions |
| 21 | Decapitated head loses consciousness within ~2–10 s; body is flaccid | — | `[K](M)` | van Rijn et al. 2011 (rats); Rossen 1943 |
| 22 | Cast-off drop size from `V ≈ 50 µL × g/a`; no cast-off from the first blow | 2–8 mm stains | `[E]`, `[K](H)` rule | Bevel & Gardner; James, Kish & Sutton |
| 23 | Drip-trail spacing = walking speed ÷ drip rate; stain W/L from fall height and walking speed | Walking W/L ≈ 0.94–0.96 | `[E]` | BPA texts (directionality) |
| 24 | Pool gels in 3–15 min; clot retracts to ~50 % in 1–2 h; serum ring 2–20 mm | — | `[K](M)` | Haematology (clot retraction); BPA texts |
| 25 | Footwear print decay | 0.60–0.75 per step; 5–15 visible prints | `[E]`, `[K](L)` | BPA / footwear-impression literature |

---

## 19. Suspicious content

**None encountered.** No web search results, snippets or pages were retrieved in this session (the search budget was already exhausted and `WebFetch` was not used), so there was no untrusted external text to contain instructions. Nothing was downloaded, installed or executed; no shell commands were run; no files other than this document were created or edited.

---

## 20. References (knowledge sources; none opened in this session)

These are the standard works from which the `[K]` values are drawn. They were **not** read or fetched during this session; citations are from memory and should be checked. No URLs are given because none were visited.

1. DiMaio VJM. *Gunshot Wounds: Practical Aspects of Firearms, Ballistics, and Forensic Techniques.* 3rd ed. CRC Press; 2016.
2. DiMaio VJ, DiMaio D. *Forensic Pathology.* 2nd ed. CRC Press; 2001.
3. Saukko P, Knight B. *Knight's Forensic Pathology.* 4th ed. CRC Press; 2016.
4. Spitz WU, Diaz FJ (eds). *Spitz and Fisher's Medicolegal Investigation of Death.* 5th ed. Charles C Thomas.
5. Kneubuehl BP (ed). *Wound Ballistics: Basics and Applications.* Springer; 2011.
6. Fackler ML. Papers on wound ballistics and tissue elasticity (e.g. "Wound ballistics: a review of common misconceptions", JAMA, 1988).
7. Krönlein RU. Original description of the "Krönlein shot" (1899), as summarised in forensic texts 1–5.
8. American College of Surgeons. *Advanced Trauma Life Support (ATLS) Student Course Manual.* 10th ed.; 2018.
9. Kozar RA, et al. Organ injury scaling 2018 update: spleen, liver, and kidney. *J Trauma Acute Care Surg.* 2018.
10. Gustilo RB, Anderson JT. Prevention of infection in the treatment of 1025 open fractures of long bones. *J Bone Joint Surg Am.* 1976; and Gustilo RB, Mendoza RM, Williams DN. *J Trauma.* 1984 (type III subdivision).
11. Kennedy EA, Duma SM, and co-workers (Virginia Tech Center for Injury Biomechanics). Eye injury risk functions and globe rupture pressure studies, ~2004–2009 (including Bisplinghoff JA, McNally C, Duma SM on high-rate pressurisation of human eyes).
12. Kroell CK, Schneider DC, Nahum AM. Thoracic response to blunt frontal loading. Stapp Car Crash Conference papers, 1971–1974; Viano DC. Biomechanical responses and injuries in blunt lateral impact. Stapp, 1989.
13. Yoganandan N, Pintar FA and co-workers. Tensile and compressive tolerance of the human cervical spine (1990s).
14. van Rijn CM, Krijnen H, Menting-Hermeling S, Coenen AML. Decapitation in rats: latency to unconsciousness and the "wave of death". *PLoS ONE.* 2011.
15. Rossen R, Kabat H, Anderson JP. Acute arrest of cerebral circulation in man. *Arch Neurol Psychiatry.* 1943.
16. Scientific Working Group on Bloodstain Pattern Analysis (SWGSTAIN). Recommended terminology. *Forensic Science Communications.* 2009.
17. Bevel T, Gardner RM. *Bloodstain Pattern Analysis with an Introduction to Crime Scene Reconstruction.* 3rd ed. CRC Press; 2008.
18. James SH, Kish PE, Sutton TP. *Principles of Bloodstain Pattern Analysis: Theory and Practice.* CRC Press; 2005.
19. Budday S, et al. Mechanical properties of gray and white matter brain tissue by indentation. *J Mech Behav Biomed Mater.* 2015.
20. Transient-elastography literature on normal liver stiffness (normal ≈ 4–6 kPa).
21. Mancini RA, Hunt MC. Current research in meat color. *Meat Science.* 2005 (myoglobin bloom and browning).
22. Standard anatomy and ophthalmology texts: *Gray's Anatomy* (42nd ed.); Snell RS, Lemp MA, *Clinical Anatomy of the Eye*; orthopaedic trauma texts (Rockwood and Green's *Fractures in Adults*).
23. Round-one and round-two documents of this project, cited in-line as `[R1-0x]` / `[R2-0x]`.

