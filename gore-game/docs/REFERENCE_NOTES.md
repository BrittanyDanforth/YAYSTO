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

## 5. What to change in our assets (actionable)

| Where | Change |
|---|---|
| Wound interiors (head gore.py now; Godot wound walls later) | Add high-frequency displacement (ridges, pits, overhangs), shredded flap geometry at margins, strand/tissue-bridge geometry across gaps, dark glossy clot blobs sitting in cavities; per-texel colour variation between fresh muscle, clot, fascia, fat and bone chips. No smooth bowls, no single-colour interiors. |
| Blood on skin | Thickness-driven colour (Beer–Lambert, RB §3), smeared translucent areas, thick dark accumulations in creases, contour-following rivulets, wide fine speckle around high-energy wounds, darker matte drying on thin areas first. Much more coverage than now. |
| Cloth (shorts) | Soak shader: fast wicking with a pinkish halo front, saturated near-black maroon core, glossy only when oversaturated; area 2–4× the skin stain. |
| Floor and surroundings | Large pools with near-black glossy centres, bright thin rims, clot lumps, satellite drops, drip trails and smears; directional spatter with tails on walls and objects; runs down vertical surfaces. |
| Exsanguination | Waxy pale yellow-grey skin tone as blood volume falls. |
| Review tests | Critics compare close-ups against these properties: a wound or scene that looks clean, dry, uniform or sparse in blood fails, the same as a sticker-looking wound. |
