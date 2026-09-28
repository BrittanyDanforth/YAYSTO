# Visual reference notes (generic, from real forensic reference photos)

> **Reference photos:** real forensic reference photos are in the git-ignored folder `refs/` at the repo root (1-8, 13-21, face refs, GSW sheets; OUR flagged bad renders 12, 22-31, 25, 26 are also committed in `gore-game/docs/feedback_renders/`). LOOK at them with the image viewer whenever you build or judge anything wound-, blood-, tissue-, bone-, skull-, brain- or death-related, and compare your renders side by side. Use injury/blood/tissue properties only; never faces or identities. Per-image notes: `gore-game/docs/REFERENCE_NOTES.md` §5.

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

### 5.5 Large skull and scalp defect exposing the brain (slicing-blade injury to the side of the head)
- A big oval section of scalp and skull is gone; the brain surface is directly visible: pale cream-pink gyri with
  darker red-purple sulci, a thin film of blood over it, glossy wet highlights, and dark near-black clotted blood lying
  as ribbons inside the fissures and low areas (not a uniform red).
- The rim is a ring of cut skull: pale bone edge showing its thickness, the scalp retracted a few mm back from it, the
  scalp margin raw red and ragged, hair matted with blood at the edge. Torn vessels and tissue hang at the lower rim.
- For our game: a skull breach shows the real gyri through a hole with a visible bone-thickness rim, blood filling the
  sulci darker than on the crowns, and a retracted raw scalp margin.

### 5.6 Bleeding from the mouth after a shot inside the mouth
- Blood leaves the mouth as a steady stream down the chin and beard and falls in a thick column onto the chest; the
  shirt below becomes a long, glossy, dark vertical soaked band. Drips and strings land on the forearms and lap; the
  rest of the face stays relatively clean.
- For our game: oral wounds route bleeding out of the mouth opening (lips → chin → chest), and clothing soaks in a
  vertical band along that path.

### 5.7 Stab wounds of the chest and arm; the face after death
- Stab wounds are narrow gaping slits, not round holes: ~15–25 mm long, elliptical gape of a few mm, dark red to
  near-black inside, sharp clean margins with a thin dark rim, one end often more pointed (single-edged blade). Several
  cluster on the chest; they bleed little externally (bleeding is mostly internal); thin dried streaks run down from
  each. Surrounding skin is pale and otherwise clean.
- The dead face: eyes half-open with slack lids, gaze unfocused and slightly divergent, dull corneas with no bright
  catch-light; mouth hanging slightly open showing the teeth; all facial muscles slack, no expression (RB #42–#46).
- For our game: knife stabs create slit-shaped real openings sized by blade width with little external blood; the dead
  face uses half-open slack lids, dull corneas, slightly divergent gaze and a dropped jaw.

### 5.8 Gunshot wound morphology sheet (forensic pathology teaching images, `refs/gsw_pathology_sheet.webp`)
These are cleaned autopsy-table wounds (not actively bleeding): use them for SHAPE, EDGE and COLOUR; add active
bleeding on top per RB §3 for living victims.
- **Contact/near-contact head entrance over bone:** a dark, soot-blackened central hole with **stellate radial splits
  (4-8 rays)** running out 1-3 cm, the split margins dark red-brown and seared; soot fans into the hair/skin around it.
- **Distant entrances:** small round-to-oval holes, a few mm, with a **pink-red to red-brown abrasion ring** of even width
  (eccentric/teardrop when angled); the centre dark red-black; several entrances can cluster (shotgun pellets / multiple
  shots) as **pink, puckered, slightly raised craters** with dried margins.
- **Exit wounds:** irregular — **stellate/star tears with 3-6 long rays** (up to several cm on the scalp and face),
  **slit-like elongated tears** (15-30 mm, sometimes with a dark clotted track), or **ragged everted holes**; margins are
  **turned outward**, torn, with tissue tags and no abrasion collar; the rays taper to fine points; dark clotted blood
  and red tissue fill the central defect.
- **Shored or skin-backed wounds:** broader irregular abrasion margins.
- **Keyhole / graze on the scalp:** elongated gutter with a split skin trough, dark red base.
- **Heavily destructive wound (close-range/high-energy):** a large gaping crater of shredded dark red muscle, clot and
  tissue tags with a torn rolled skin edge — see §2.
- **Skin tone around wounds:** normal skin colour, with livid red-purple bruised tissue only right at the margins;
  wounds on darker skin show a pale pink raw interior inside a darker rim.
- **For our game:** entrance = small clean hole + even abrasion ring (eccentric if angled), contact = stellate seared
  tear with soot; exits = weighted mix of stellate (long tapering rays), slit, and ragged everted holes, never a
  uniform crater; interiors dark red-black with clot; then active bleeding per the physiology.

## 5.9 Blood source rule (user requirement)

BLOOD MUST COME FROM THE WOUND (user, verbatim: "VERY UNREALISTIC BLOOD WOULD POUR OUT THE WOUND OF HEADSHOT AND NOT MAGICALLY APPEAR BLOOD AROUND THE HOLE IT WOULD COME FROM THE INJURY ETC BE 1:1 REALISTIC THATS STANDARD EXTREME REALISM"):
- NO blood may appear on the skin that did not physically get there. Remove any pre-painted halo/pool/smear around a wound (e.g. gore_blood teardrops or rings stamped around the hole). Every stain on the skin must be connected to the wound by the path the blood actually travelled, or be an impact spatter droplet thrown at the moment of the hit.
- Sequence (animate/time-drive it): t=0 hole opens, impact spatter only (exits throw blood and tissue AWAY from the head; entrances get back-spatter toward the shooter, very little on the victim's own skin); then blood WELLS UP inside the wound cavity (a blood surface filling the hole, dark and glossy, brain/tissue extruding at exits); it OVERFLOWS at the LOWEST point of the wound rim; a continuous stream POURS from that lip and runs down under gravity following the skin's shape (around the jaw line, down the neck), with a rounded bead at the leading front; the front advances at a realistic speed (cm/s on skin), the stream widens with volume, more streams split off the rim as flow increases, it collects in creases and drips off low points (chin, earlobe, nose). Behind the front, a thinner film/stain remains along the path and darkens as it dries at the edges.
- Flow rate follows the injury: scalp/head wounds bleed heavily and keep pouring; arterial = pulsing surges; after cardiac arrest only slow gravity drainage.
- Look: thick blood is dark maroon to near-black, glossy, with clots; thin films are translucent red; never uniform bright-red tubes.
- Test: render a time sequence (at least 6 moments from 0 to 60 s) — the blood must visibly originate in the wound and travel outward/downward; any blood appearing somewhere without a path from the wound is a HIGH-severity failure.

## 5.10 Wound-wall artefact in OUR render (`refs/12_our_render_wall_stripes.png`) — HIGH priority
Our cut walls show regular vertical stripes like fence planks or corrugated card: evenly spaced parallel bands of
alternating dark/light red running down the wall, plus a hard orange lip line. This is a CG artefact (extruded ring
quads + a straight fibre texture), not tissue. Real wound walls (refs 13, 15, 16, 3, 4, 6) are irregular: lumpy torn
muscle, ragged fascia sheets, clot blobs, strands, pits, glistening wet highlights broken up everywhere, with no
repeating pattern at all. Fix: break up wall geometry with multi-octave noise displacement and random tears/strands/clot
blobs, randomise ring spacing, drop the straight stripe texture (fibres only where muscle is cut along the grain, and
then irregular), and cover the wall and lip in wet dark clot and pooled blood.

## 5.11 Explosive in the mouth (`refs/13_blast_face_mouth_explosive.png`, cleaned at autopsy)
- The lower-mid face is blown open from the mouth outward: a large central crater of shredded, bright-to-dark red muscle
  and soft tissue running from the lips up through the nose and cheek into the orbit area on one side.
- The mandible is fractured: a bone segment WITH TEETH STILL IN IT is broken off and displaced, hanging in the wound;
  other teeth are loose or missing; pale bone fragments sit in the tissue.
- Torn skin flaps with ragged, irregular margins; the unaffected skin around is intact but blackened/soot-speckled and
  burned (powder tattooing, searing) and swollen; one eye half-closed and swollen.
- No regular structure anywhere: everything is lumpy, stringy, torn. In life this is covered in a lot of blood.

## 5.12 Body position and pooling (`refs/14_body_position_pool.png`)
- Body supine on a hard floor, legs straight and slightly apart, feet turned outward, arms limp at the sides; clothing
  soaked from the head/shoulder down.
- A large dark-red pool spreads from the head/upper body across the floor, thick and glossy near the body, thinner and
  brighter at the edges, with smears and splash marks; blood also on nearby objects.

## 5.13 Repeated heavy blunt impacts to the face (`refs/15_...`, `refs/16_...`)
- The face is crushed and collapsed: the facial skeleton is broken into pieces so the contours cave in; the eyes look
  SUNKEN into the head (orbit floor/walls broken); lids swollen or torn.
- Large areas of skin are torn away in flaps with pale fatty undersides, exposing bright orange-red muscle, yellow fat,
  pale bone fragments and teeth; tissue is pulpy and lumpy.
- Remaining skin is waxy pale-yellow (blood loss / post-mortem), strongly contrasting with the raw red tissue.
- Thick dark blood pools beneath; clots and strands everywhere.
- For our game: repeated hammer/blunt hits on one area accumulate into this (contour collapse, sunken eyes, flaps, bone
  and teeth exposed), not into neat stacked dents.

## 5.14 More reference images (refs 17-21)
- **17 neck transection:** cut surface a dense mix of dark red muscle, clot and vessel openings; face covered in fine
  dark speckle; very large glossy dark-red pool spreading over the surface under the body, with smears and spray on
  nearby objects.
- **18 heavy chopping blows to the head:** the head is a mass of torn, folded sheets of dark red muscle and skin, deep
  clot-filled cavities, glossy wet surfaces everywhere, strands and flaps; the surrounding skin is completely smeared
  in blood; thick pooled blood with dark clots underneath. No regular structure at all.
- **19 skull cap cut off, brain exposed:** a ring of cut skull with the scalp retracted; brain gyri pale cream with red
  blood in the sulci and a dark near-black clot stripe lying in a fissure; the scalp edge raw red and ragged; the
  cranial cavity rim lined with red tissue.
- **20 gunshot wound grid (pathology teaching):** contact head entrances = black stellate splits radiating from a sooty
  centre; small entrances = pink puckered holes with an abrasion rim; exits = star/slit tears with everted edges and
  dark clot; a big shredded exit crater in a limb; tiny slit-like wounds. All irregular, none a perfect circle.
- **21 multiple face gunshots, seated:** the face looks mostly intact from a distance, but blood streams from several
  small facial wounds down over the cheek, jaw and hand, soaks the shirt shoulder in a dark band, runs down the arm and
  pours onto the floor forming a very large pool with splash marks beside the chair. Small entrances + heavy, gravity-
  driven bleeding and pooling — exactly the blood-source rule.

## 5.15 User verdict on the mouth-blast render (fixer round 3, `fixer3/blast_wide.png`) — CORRECTED
- The user was being sarcastic: the gums and mouth lining in the MIDDLE of the blast are left "perfectly fine" (intact,
  clean, glossy pink) and that is NOT realistic. An explosive in the mouth destroys the gums, palate, tongue and mouth
  lining first: they must be torn, shredded, charred and blood-soaked, with teeth blown out or shattered, the palate
  broken, and the tongue lacerated — nothing in the blast zone may stay intact or clean (refs 13, 15, 16).
- Also wrong: the jawbone is clean white plastic and unbroken (real: broken segment with teeth hanging, fragments,
  blood-stained bone); wound walls are smooth glossy plastic (real: shredded, lumpy, stringy torn tissue with clot);
  far too little blood; no soot/burn on surrounding skin.

## 5.16 Material separation and wall thickness (user feedback on `fixer3/blast_wide_c.png`)
- MATERIAL SEPARATION (biggest win): today too many surfaces share the same deep-red glossy shine.
  - Bone: MATTE and PALE (ivory/grey-white, rough, porous, dry-looking except where blood films it); broken edges
    chalky, cancellous bone spongy with blood in the pores.
  - Tissue (muscle, fat, mouth lining, torn skin): DARKER, SOFTER, low-to-medium sheen, subsurface scattering,
    irregular — muscle dull dark red to maroon, fat yellow and lumpy, torn skin underside pale.
  - Wet fresh blood: the ONLY strongly reflective, mirror-glossy surface; thick pools near-black red; clots duller.
  - Teeth: pale enamel with a slight sheen, blood-smeared.
- Break up smooth wound edges and blood streams so they don't look moulded or painted on: irregular ragged margins,
  varying stream width, beads, splits, drying edges.
- WALL THICKNESS: our inner wound walls are too thick, smooth and "molded". In the reference photos the exposed
  layers are thin and ragged: skin ~1-3 mm (face/scalp up to ~5-7 mm), a thin fat layer, then torn muscle. There is no
  thick smooth rim or tube around an opening. Make the extruded walls thinner, ragged and torn, collapsing into
  irregular tissue, not a smooth sleeve.
- Keep: loose teeth and the broken jaw in the mouth blast (they sell it).

## 5.17 Blood stream DISCONNECTED from the wound (our render, `refs/25_...`, `refs/26_...`) — HIGH priority
The user spotted it: the blood stream starts BELOW the hole with a visible gap of clean skin between the wound rim and
the top of the stream, so it looks stuck on under the hole instead of pouring OUT of it. Required: the blood must be
one continuous body from INSIDE the wound cavity (a blood surface filling the hole) over the lowest point of the rim
(the lip itself wet and covered) and down the skin — no gap, no separate object starting under the hole, the stream's
top merges into the pooled blood in the wound. Test: close-up at the rim from straight on and 45°: zero skin visible
between wound blood and stream.

## 5.18 VISUAL ACCEPTANCE STANDARD (from ALL real refs 1-8, 13-21, GSW sheets) — applies to every wound, blood and body render

The user (after we reviewed every reference together): "look at the 10+ real gore images now and update any standard ...
u can see the mushyness the everything some caved in heads some heads cut off half way some are shot in face". This
section is the pass/fail bar. A render that fails any HIGH line below is not done, whatever else is good.

**A. Destroyed tissue is MUSH, not sculpted shapes (HIGH).** Refs 3, 13, 15, 16, 18.
- Severely damaged areas are a wet pulp: hundreds of small irregular lumps, torn shreds, folded sheets and fibrous
  strings with NO geometric order — no smooth bowls, no clean extruded rings, no repeating pattern, no symmetry.
- Scale mix: big torn flaps (20-60 mm) folded over each other, medium lumps (3-10 mm), fine grit and strands (< 2 mm).
  Test: at 1:1 close-up there must be detail at all three scales; a surface that is smooth at any scale fails.
- Skin at the margin is TORN into flaps that curl and fold back, showing their pale yellow-white fatty underside.
  Flap edges are thin (1-3 mm skin, scalp up to 5-7 mm), ragged, never a thick moulded rim.
- Dark clot-filled pits and pockets everywhere between the lumps (near-black `#2A0306`-`#5E070C`), some glossy, some matte.
- Tissue bridges and strings span gaps; pieces hang off by threads.

**B. Colour palette (HIGH).** Real destroyed tissue is never one red.
- Fresh exposed muscle: bright orange-red to scarlet (`#B8231A`-`#D8452E`), the brightest thing in the wound.
- Blood/clot: maroon to near-black (`#5E070C`, `#3A0508`); thin films translucent red over skin.
- Fat: yellow to cream lobules (`#D8B26A`-`#EAD7A0`), blood-stained pink at the edges.
- Bone: pale chalky cream/ivory (`#E6DCC4`), MATTE, in sharp fragments mixed through the pulp, with blood in cracks.
- Brain: cream-pink grey (`#D9B8A8`-`#C9A99A`), soft and wet, blood in the sulci, black clot in fissures (ref 19).
- Intact skin around heavy trauma: pale, waxy, yellow-grey (blood loss); bruised/congested zones dark purple-red
  (refs 5, 15, 16). Regional contrast between pale body and dark swollen face is typical.
- Test: sample 5 points inside a large wound — at least 4 clearly different colours (bright muscle, dark clot, yellow
  fat, pale bone/brain). A single-hue wound fails.

**C. Wetness and specular (HIGH).** Refs 3, 13, 17, 18, 21.
- Everything fresh is wet: many small, BROKEN specular highlights scattered over the lumps (thousands of tiny glints),
  not one smooth plastic sheen. Pools on flat surfaces are mirror-glossy and flat-topped with a slight meniscus.
- Bone and dried areas are matte. Exposed tissue is softer/less sharp gloss than liquid blood (see §5.16).
- Test: a wound surface with one big continuous highlight = plastic = fail.

**D. Caved-in / crushed head and face (refs 15, 16, 3).**
- The facial skeleton COLLAPSES: the mid-face (nose, cheekbones, orbit rims) is pushed in, the face flattens and
  widens, the profile loses its nose/brow projection; eyes sink or are hidden in swollen tissue.
- Skin splits over bone into several ragged lacerations with bridges; the rest is massively swollen, shiny-tight and
  dark purple; lips swollen and everted.
- Skull depressions: the surface outline visibly dents inward (silhouette test), bone fragments displaced inward,
  step-offs at the fracture edges; the scalp over it may be intact but boggy and discoloured.
- The head shape itself must change. A crushed preset whose silhouette matches the intact head fails.

**E. Partial decapitation / deep neck cut (refs 1/17, 18).**
- The cut face is a cross-section, not a painted disc: granular dark-red muscle mass, pale rings/spots of cartilage
  (trachea/larynx) and vessel openings, torn edges, clot filling the gap, strands between the two sides.
- The head tips/rotates away from the cut under gravity and the wound gapes widely (skin and muscles retract).
- Everything nearby (face, hair, clothing, surfaces) is covered in FINE mist speckle (0.2-2 mm) plus larger drops.
- Pools under it are huge, flat, mirror-glossy and dark, with clots.

**F. Shot / blasted face (refs 13, 20, 21, 7, GSW sheet).**
- Entrance wounds are small, irregular, never perfect circles; contact wounds tear stellate; exits are ragged/
  stellate/irregular with everted shredded margins and extruding tissue.
- High energy / in the mouth: the mid-face becomes pulp (section A), jaw broken into segments with teeth still in
  them, loose teeth, gums/palate/tongue destroyed (§5.15), soot and stipple on remaining skin.
- Blood from the face/mouth runs DOWN: chin → neck → chest; it falls in thick ropey clotted strands and sheets, soaks
  the shirt dark-wet (nearly black where saturated) and runs down the arm and drips off the fingers (refs 7, 21).

**G. Blood volume, clothing and pools (HIGH).** Refs 3, 5, 7, 14, 17, 21.
- There is FAR more blood than feels "enough": whole shoulders/shirt fronts soaked, streams down limbs, floor pools
  larger than the head (a 1 L pool ≈ 70 cm across).
- Pools: near-black glossy centre, thinner brighter red edge, big dark jelly clot lumps sitting in it, splash
  satellites and drip trails around it; blood mixes with floor dirt at the edges.
- Every stain connects to its source by the path the blood took (§5.9, §5.17) or is a thrown spatter droplet.

**H. Pass/fail procedure for reviewers.** For every wound/preset: render straight, 45°, grazing and a cross-section at
≥ 640 px, put each next to the matching ref (A → 3/13/18, B/C → 13/18/19, D → 15/16, E → 1/17, F → 13/20/21, G →
7/14/21) and write one line per section: PASS or FAIL + what differs. Anything that reads cleaner, drier, smoother,
more uniform, more symmetric or less bloody than the refs is a FAIL.

## 5.19 User verdict on the final-pass exit sequence (2026-09-27, `renders/seq_exit_*`) — HIGH priority

User, verbatim: "THERES STILL LEGIT A GAP ITS NOT COMMING FROMM THE ACTUAL WOUND LIKE U CAN SEE SLIGHT GAP STILL ALSO THE
SKIN STILL LOOKS THICK AND ENSURE ARTERYS ETC ALL THAT IS WIRED FOR BLOOD TOO VERY NICELY 1:1 REALISM LIKE PHOTOS I GAVE U SHOW".
1. **Blood comes OUT OF THE HOLE ITSELF (user clarified: "BY GAP I MEAN FROM THE HOLE OF THE INJURY THERES A SLIGHT
   GAP WERE BLOOD STARTS ITS NOT COMMING FROM INJURY HOLE").** Zoomed renders show it: at the entry the dark opening is
   empty and dry, and the stream starts on the brown abrasion ring BELOW the opening; at the exit a thin pale band of
   skin/rim sits between the torn opening and the top of the streams. Required: the opening fills with dark glossy blood
   from inside (welling up out of the track), that blood surface rises to and over the lowest part of the opening's own
   edge, and the stream is the continuation of that same liquid body — its top is INSIDE the hole, not on the skin or
   collar next to it. The collar/rim below the opening is covered by the flowing blood.
   User's crop of `renders/hero.png` (forehead entry): the stream is WIDER than the hole's lower edge and its top is a
   flat cut line; on the RIGHT side of the hole a wedge of clean skin sits between the hole's edge and the top of the
   stream, so the blood looks like it "just appears" beside the wound. Required: the stream's top outline must follow
   the hole's own lower edge exactly (the liquid spills over the lip it is touching), be no wider than the part of the
   rim it leaves from, and widen only further down as it spreads; blood that reaches the skin beside the hole must
   visibly come over the rim at that point. No flat-topped streams, no stream starting on skin next to the hole.
   **Zero gap, proven.** The stream must be ONE continuous liquid body with the blood inside the wound: the blood
   surface in the cavity, the wet rim lip and the stream share geometry (or overlap by >= 1 mm) with no skin pixel
   between them at ANY time (0, 5, 10, 20, 40, 60 s) and from any angle. Test: close-up renders at the rim from straight,
   45 deg and grazing at every sequence time; sample the image along the stream axis from inside the hole to 5 mm below
   the rim — any skin-coloured pixel = FAIL. Also the rim itself is wet and covered where blood leaves it.
2. **Skin is thin.** Wound margins still read as a thick moulded sleeve. Real scalp/face skin is 1.5-3 mm (scalp up to
   5-7 mm incl. galea): the visible cut edge is a thin pale dermis line over yellow fat, torn and irregular, with the
   deeper tissue recessed and shredded below it — never a thick smooth rounded lip. Reduce wall thickness/bevel radius
   and remove rounded rims.
3. **Blood is wired to real vessels.** How much a wound bleeds, where from, colour and pulsing must come from the named
   vessels it hits (REALISM_BIBLE circulation + ~55-vessel table; head: superficial temporal, occipital, posterior
   auricular, supraorbital/supratrochlear, facial, angular, labial, dural/meningeal, venous sinuses, scalp venous plexus).
   Arterial hits = bright scarlet, pulsing surges with the heartbeat, faster/longer streams, spray; venous = dark steady
   welling; scalp = heavy and persistent (galea holds vessels open); bone/diploe and brain = oozing dark blood mixed with
   tissue. Blood amount and stream count per wound follow that source, so two wounds never bleed identically. In the
   Blender head: map each hit to its nearest vessels (a vessel table for the head in gore.py/CONTRACT.md) and drive
   bleed rate, colour and pulse from it. In the body/Godot game: bleeding already comes from the vessel graph
   (vessels.json) — keep it 1:1 with the bible.
4. Compare every frame against the refs (2, 7, 17, 21 for flow and volume; 13, 18 for wound edges).

## 5.20 User verdict on the crushed preset (2026-09-27, `renders/preset_crushed_front.png`) — HIGH priority

User: "WHY IS THE TIP OF NOSE ... STILL GLITCHED ... NOT AFFECTS THE TIP OF IT ... THE EYEBALL IS PRETTY BIG ... THE EYE
SHOULD BE ABLE TO GET DAMAGED AND BE REALISTIC LIKE REAL LIFE 1:1".
1. **Nose tip untouched inside the damage zone.** The crush destroys the cheek, orbit and nasal side, but the nose tip
   stays a clean, intact, un-bruised lump floating at the wound edge. It must be part of the same injury: a mid-face
   crush breaks and displaces the nasal bones/cartilage (nose pushed flat and to the side), tears or splits the skin of
   the nose, bruises and swells it dark purple, and blood comes from the nostrils. No region inside or bordering a wound
   may stay pristine — check every hit's falloff reaches the nose, lips, eyelids and ears.
2. **Eyeball too big.** An adult globe is ~24 mm across and is NEVER enlarged by trauma; in the render it looks
   ~1.5x bigger and bulging. Keep the eye at true size (GH_Eye r 0.012) and remove any scale/inflate applied by the crush.
3. **The eye must take real damage** (all driven by the hits, 1:1 with forensic reality):
   - globe rupture: the eye DEFLATES and collapses (wrinkled, flattened, misshapen), it does not swell or stay a
     perfect sphere; clear/jelly vitreous and dark uveal tissue extrude through the tear, the cornea clouds or tears;
   - hyphaema: blood layered in the front chamber (a red/dark level behind the cornea);
   - subconjunctival haemorrhage: the white turns solid bright red under the surface (flat, not spotty dots);
   - lid lacerations, periorbital "black eye" swelling that can close the lids, orbital-floor blow-out fracture with
     the globe sunk (enophthalmos) or displaced; retrobulbar bleeding pushes the eye forward only a few mm;
   - a bullet/fragment through the orbit destroys the globe; a nearby headshot gives raccoon eyes over hours.
   Build this as part of GH_Gore on the eye layer (per-hit: rupture, collapse, extrusion, haemorrhage, hyphaema),
   verify with close-ups against real anatomy, and keep the undamaged eye pristine only when no hit reaches it.

## 5.21 User verdict on the cheek-slash test (2026-09-27, fix pass 2 blood test `t4s_Slash_Cheek_wide_60s.png`) — HIGH

User: "THE BLOOD U CAN SEE STREAK ON RIGHT SIDE IS COMMING FROM NOTHING? ABOVE IT ISNT A WOUND ... IT WOULDNT MAKE SENSE
THAT SECOND ONE BE THERE IN THAT SPECIFIC SPOT ALSO THE DROPLETS ... A BIT THICK".
1. **Every stream must start at a point of the wound rim that is directly above it and actually overflowing.** In the
   test the right-hand stream starts on intact skin to the right of the cut's end, with no wound above it. Streams may
   only be seeded at rim points that are (a) on the wound's own edge, (b) local LOW points of that edge under gravity,
   (c) where the pooled blood level reaches the rim. A second stream must come from a second low point of the SAME rim
   (or from a separate wound), and its top must visibly connect to the rim. Test: trace every stream upward — it must
   end inside a wound opening; any stream whose top is on skin = HIGH FAIL (same class as 5.9/5.17).
2. **Drops too thick.** Pendant drops are ~30-60 uL (a bead ~3-4.5 mm across), slightly flattened against the skin,
   teardrop-shaped, translucent at the thin edge; the stream feeding them is 2-5 mm wide and ~0.1-0.4 mm thick
   (REALISM_BIBLE rivulet row). Current drops read as fat glossy berries and the streams as thick flat tape.

## 5.22 User verdict: far too much yellow fat (2026-09-27, fix pass 2 test `fix2_wounds/d4m.png` throat cut, also burn/crush)

User: "Y SO MUCH FAT OR YELLOW THAT ISNT REALISTIC". The throat cut shows a thick bright yellow beaded rim of "fat" running
along both lips; yellow also dots the burn and crushed wounds. Real facts: face/neck subcutaneous fat in a lean adult male
is thin (face 2-6 mm, anterior neck 2-5 mm, scalp ~1-3 mm with almost none on the forehead) and it is PALE CREAM to faintly
yellow, glistening, often pink-tinged and quickly stained red/brown by blood — never a saturated yellow band or a row of
yellow beads. In a fresh wound the fat layer shows only as a thin, partly blood-covered pale line between the dermis
and the dark red muscle, visible mainly where the wound gapes (refs 15/16/18: small pale lobules, mostly bloody).
Fix: reduce fat thickness to anatomical values per region, desaturate to pale cream #E8D9B5-#D9C6A0 with blood staining,
no bead/cobble pattern at the rim, and let blood cover most of it. A clearly visible yellow band anywhere = FAIL.

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
