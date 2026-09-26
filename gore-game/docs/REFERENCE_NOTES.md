# Visual reference notes (generic, from real forensic reference photos)

These notes record **generic visual properties** observed in real forensic reference photographs supplied by the user
for educational realism. No identity, face, tattoo, location or case detail is used or recorded, no specific person's
injuries are recreated, and the photos themselves are never stored in the repo. Everything here is a general property
of real wounds and blood that our procedural assets and shaders must reproduce. These notes complement (never
override) the sourced numbers in `REALISM_BIBLE.md` and `BEHAVIOUR_BIBLE.md`.

The one-line lesson: **real injuries are far wetter, bloodier, messier and more irregular than our renders.** Our
wounds are too clean, too smooth, too uniform in colour, and there is far too little blood around them.

---

## 1. How much blood there is, and where it goes

- **Coverage is large.** Heavy bleeding coats big areas: whole sides of the neck and shoulder, the arm down to the hand,
  the clothing, the furniture and the floor. A single serious wound routinely marks a zone of tens of centimetres to
  metres around the body. Our current renders show thin drips near the wound only; that reads as fake.
- **Blood on skin is never one even film.** It is:
  - smeared sheets (thin, translucent pink-red where wiped or spread, `#B8474C`–`#C75A5A`);
  - thick dark accumulations in creases, folds and the lowest points (`#4A0A0E`–`#6A0E14`);
  - rivulets that follow gravity **and** the body's contours (around the jaw line, down the neck, along the arm);
  - fine speckle of 0.5–3 mm droplets scattered over a wide area (tens of cm) around high-energy wounds, on skin and
    on nearby surfaces;
  - dried flecks and thin edges that turn darker brown-red and matte first, while thick areas stay glossy.
- **Clothing soaks, it does not stain like paint.** Cotton wicks fast: saturated zones go dark maroon to near-black
  (`#3A0A0E`–`#5A0E12`), with a lighter, pinkish diffuse halo 1–3 cm wide at the wicking front (`#8A2A30`), and the
  cloth gets heavier-looking and glossy only where oversaturated. Soaked fabric area is several times the skin area for
  the same blood (see FB-10: 2–4×). This applies to the subject's shorts.
- **Floor pools are big, dark and lumpy.**
  - Thick centres look near-black red (`#2A0508`–`#5E070C`), glossy, with sharp window/light reflections.
  - Bright red only at thin edges, splash rims and fresh drips landing (`#A0141C`).
  - Jelly-like clots sit in the pool as darker, slightly raised, matte-er lumps.
  - Pools collect in low points and along the edges of furniture and walls; satellite drops, drip trails, smears and
    drag marks surround them.
- **The environment gets spattered.** Nearby walls, furniture and objects carry arcs and streaks of elongated droplets
  with tails pointing in the direction of travel, plus runs where larger spots drip downward.

## 2. Torn tissue (high-energy, chopping, crushing and blunt wounds)

- **Never a smooth crater.** Real torn tissue is a chaotic, layered mass:
  - shredded sheets and flaps of skin and muscle, with rolled, ragged, irregular margins;
  - stringy fibrous strands and tissue bridges spanning gaps;
  - many small cavities and crevices, filled with dark clotted blood;
  - very irregular depth: ridges, pits and overhangs within a few centimetres.
- **Colour varies strongly within a few centimetres:** bright red fresh muscle (`#A01822`), dark maroon to black clots
  (`#2A0508`–`#4A0A0E`), pale pink to whitish fascia and connective tissue (`#D8A7A0`), yellowish fat globules
  (`#E8C766`), grey-white bone fragments. Avoid a single uniform "wound red".
- **Everything is wet.** Glossy surfaces with sharp, broken specular highlights all over the torn tissue; clots are a
  little less glossy than fresh surfaces.
- **Skin around torn wounds** is blood-stained, abraded and irregular; margins curl and roll outward or inward.
- **Massive crushing of the face/head** destroys normal contours: features collapse and lose their shape, and in the
  living the surrounding tissue swells heavily with purple-black bruising.

## 3. Clean transections (a blade or edge cutting straight through)

- The cut face shows **distinct muscle bundles** as dark red masses separated by paler lines of fascia and fat, **cut
  vessels** as small dark round openings (arteries with thicker pale walls), and bone (where cut) as a pale ring of
  cortex around darker marrow.
- The skin margin retracts slightly from the cut face; muscle bundles retract unevenly, so the face is not flat.
- The surroundings are heavily blood-soaked (see §1).

## 4. Skin colour after major blood loss

- Waxy pale, yellow-grey to grey-white skin that contrasts strongly with the red blood on it (consistent with
  `REALISM_BIBLE.md` checklist #29: never blue).

## 5. Injury types seen in the reference set (what each injury does to the body)

### 5.1 Heavy chopping / crushing blows to the head (pickaxe- or axe-type tool; the extreme end of our hammer and claw)
- **Normal facial anatomy is gone.** Repeated heavy blows turn the face into a mass of torn, folded sheets of skin and
  muscle; the nose, lips, cheeks and eye regions are no longer recognisable as features. Contours collapse because the
  facial skeleton underneath is broken into pieces.
- **Layering is visible everywhere:** flaps of skin with their pale underside and yellow fat, then dark red muscle
  sheets, then clot-filled pits, then pale fragments of bone and crushed tissue at the bottom. Flaps are folded back on
  themselves and overlap like torn cloth.
- **Clots fill every cavity:** dark maroon-black, glossy jelly in the pits, bright red only on freshly exposed surfaces.
- **Side view of a chop wound through the side of the head:** a deep, long, gaping defect with ragged overhanging
  edges, torn muscle hanging in strips, cavities packed with clot, and blood pooled under the head on the floor.
- **Around it:** the skin of the neck and shoulders is smeared with blood that dries brownish at thin edges; the neck
  shows dark purple-red congestion and bruising.
- **For our game:** a single hammer blow gives a depressed fracture and a laceration (RB §2.5); these images show what
  **many** heavy blows accumulate into. Repeated hammer/claw hits on the same area should progressively destroy the
  contour, open layered flaps, expose bone fragments and fill with clot — not just stack more round dents.

### 5.2 Complete transection of the neck by a heavy blade
- The cut face is a dense mosaic: large dark red muscle bundles, pale lines of fascia and fat between them, small dark
  round openings of cut vessels, the pale ring of the cut airway, and at the centre the vertebra with its canal.
- The cut surface is **not flat**: muscles retract by different amounts, so it is lumpy, with clot collecting in the
  gaps and blood running from the lowest edge.
- The skin of the face and head carries **dense fine speckle** (0.5–3 mm droplets) over wide areas — the spray from
  cut arteries and from the blade — plus heavier spatter and smears near the cut.
- Surfaces underneath are covered in thick glossy blood with smears; the amount is very large (carotid and jugular
  transection, RB §3, §6).
- **For our game:** the plan's dismemberment is phase C; the knife itself cannot sever the neck (RB), but deep neck
  cuts must show the same cut-face structure in their walls (muscle bundles, vessel openings, airway) and produce the
  same wide speckle and heavy flow.

### 5.3 Multiple gunshot wounds in a seated person
- **Blood follows the body's shape downward:** from face/head wounds it runs down the jaw and neck, soaks the collar and
  shoulder of the shirt dark, streaks down the arm in several rivulets, and drips from the lowest point (the fingers of
  the hanging arm) into a pool on the floor directly below.
- **The pool is very large** (roughly a metre or more across on a hard floor) with a near-black glossy centre,
  darker lumpy clots, bright red thin edges, and splash drops and small satellite spatter around it on the tiles.
- **Posture after collapse in a chair:** head tipped back or to the side, mouth slightly open, arms completely limp —
  one hanging over the armrest — legs extended or splayed; nothing is held or braced (flaccid tone, BB §4).
- **For our game:** blood routing must follow gravity over whatever pose the body is in (seated, lying, slumped), with
  drip-off points at the lowest extremities feeding a pool; the shirt/shorts soak along the path.

### 5.4 Amputation of hands and feet (sharp cut through the limbs)
- Stumps show a cut surface of pink-red muscle around a pale bone end; the skin edge retracts; after heavy bleeding the
  cut surfaces turn paler and duller.
- The rest of the body goes **pale** (blood loss), while the face and neck can look dark purple-red from congestion and
  bruising — strong contrast between regions.
- Blood pools under the body at its lowest point and runs along the ground's slope.
- **For our game:** beyond v1 scope (hands/feet are simplified; dismemberment is phase C), but the stump look (muscle
  ring, pale bone end with marrow, retracted skin, pale bled-out surfaces) is the reference if it is added.

## 6. What to change in our assets (actionable)

| Where | Change |
|---|---|
| Wound interiors (head gore.py now; Godot wound walls later) | Add high-frequency displacement (ridges, pits, overhangs), shredded flap geometry at margins, strand/tissue-bridge geometry across gaps, dark glossy clot blobs sitting in cavities; per-texel colour variation between fresh muscle, clot, fascia, fat and bone chips. No smooth bowls, no single-colour interiors. |
| Blood on skin | Thickness-driven colour (Beer–Lambert, RB §3), smeared translucent areas, thick dark accumulations in creases, contour-following rivulets, wide fine speckle around high-energy wounds, darker matte drying on thin areas first. Much more coverage than now. |
| Cloth (shorts) | Soak shader: fast wicking with a pinkish halo front, saturated near-black maroon core, glossy only when oversaturated; area 2–4× the skin stain. |
| Floor and surroundings | Large pools with near-black glossy centres, bright thin rims, clot lumps, satellite drops, drip trails and smears; directional spatter with tails on walls and objects; runs down vertical surfaces. |
| Exsanguination | Waxy pale yellow-grey skin tone as blood volume falls; face/neck may stay dark purple-red from congestion or bruising (regional contrast). |
| Repeated blunt/chop hits (§5.1) | Damage accumulates: contour collapse, folded layered flaps, bone fragments, clot-filled pits; never just more round dents. |
| Deep neck cuts (§5.2) | Wall geometry shows muscle bundles, vessel openings and airway ring; lumpy retracted cut face; wide fine speckle on the face and head. |
| Blood routing (§5.3) | Flow follows gravity over the current pose (standing, seated, lying), soaks clothing along the path, drips from the lowest extremity into a pool below it. |
| Death posture (§5.3) | Flaccid slump: head tipped back or sideways, mouth slightly open, limbs hanging, nothing braced. |
| Review tests | Critics compare close-ups against these properties: a wound or scene that looks clean, dry, uniform or sparse in blood fails, the same as a sticker-looking wound. |
