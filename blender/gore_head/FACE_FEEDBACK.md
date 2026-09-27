# Face feedback from the user (to apply to anatomy.py after the current gore review/fix run)

Reference images (git-ignored, local only): `refs/face_ref_sculpt.png` (neutral sculpted head, 3 views) and
`refs/face_ref_male.webp` (realistic bald adult male, several angles). Use them for proportions and form only —
do not copy a specific person's likeness; our head stays a generic fictional man.

The user's verdict on the current head (verbatim intent):
- **Ears are NOT correct-looking.** Rebuild them: proper helix rim curling over, antihelix Y-fork, deep concha bowl
  leading into the canal, tragus and antitragus, and a SMALL lobe. Ears sit between brow line and nose base, tilted back
  ~15-20°, and stand off the head only slightly.
- **Earlobes are far too long.** Shorten to a normal adult lobe (~15-20 mm of the ~60-65 mm ear height).
- ~~Eyes look bug-eyed / seat deeper~~ — **NO LONGER REQUIRED (user, 2026-09-27: "u dont gotta fix the eyes deepset just ensure 1:1 realism")**. Keep the eyes as they are; only fix them if something is anatomically wrong.
- (old note) **Eyes look bug-eyed.** Seat the eyeballs deeper in the orbits: more brow-ridge overhang, deeper upper-lid crease and
  orbital hollow, lids covering more of the globe (upper lid over the top of the iris), less of the eyeball exposed from
  the side.
- **Eyes are too far apart.** Reduce the interpupillary distance a little (adult male IPD ~62-64 mm, i.e. eye centres at
  about ±0.031-0.032 m; also check the inter-canthal distance ≈ one eye width ~30-32 mm).
- **Head is too long, with no cheekbones.** Shorten the face/cranium vertically where it is stretched, and build real
  zygomatic prominence (cheekbones) with the hollow below them, a defined jaw angle and chin; widen the face at the
  cheekbones rather than a long flat oval. The back of the head should not be egg-shaped.
- **Nostrils are collapsed.** Open the nostrils into proper teardrop openings with visible alar rims and columella.
  Keep the nose base and overall nose curve — the user likes those.
- **Teeth are great — keep them.**

Constraints: keep all layer nesting valid (skull, muscle, skin offsets derive from skin — move the skull/orbits with
the skin so eyes sit in the sockets), keep landmark table in CONTRACT.md updated, keep the gore system working (re-run
`python3 gore.py --no-render` verify and `python3 build.py`), and do NOT touch `blender/gore_body/` (the body build
imports the head read-only and will pick up the improved head on its next head-join/export).


## Blood source (user feedback after the headshot clip)

BLOOD MUST COME FROM THE WOUND (user, verbatim: "VERY UNREALISTIC BLOOD WOULD POUR OUT THE WOUND OF HEADSHOT AND NOT MAGICALLY APPEAR BLOOD AROUND THE HOLE IT WOULD COME FROM THE INJURY ETC BE 1:1 REALISTIC THATS STANDARD EXTREME REALISM"):
- NO blood may appear on the skin that did not physically get there. Remove any pre-painted halo/pool/smear around a wound (e.g. gore_blood teardrops or rings stamped around the hole). Every stain on the skin must be connected to the wound by the path the blood actually travelled, or be an impact spatter droplet thrown at the moment of the hit.
- Sequence (animate/time-drive it): t=0 hole opens, impact spatter only (exits throw blood and tissue AWAY from the head; entrances get back-spatter toward the shooter, very little on the victim's own skin); then blood WELLS UP inside the wound cavity (a blood surface filling the hole, dark and glossy, brain/tissue extruding at exits); it OVERFLOWS at the LOWEST point of the wound rim; a continuous stream POURS from that lip and runs down under gravity following the skin's shape (around the jaw line, down the neck), with a rounded bead at the leading front; the front advances at a realistic speed (cm/s on skin), the stream widens with volume, more streams split off the rim as flow increases, it collects in creases and drips off low points (chin, earlobe, nose). Behind the front, a thinner film/stain remains along the path and darkens as it dries at the edges.
- Flow rate follows the injury: scalp/head wounds bleed heavily and keep pouring; arterial = pulsing surges; after cardiac arrest only slow gravity drainage.
- Look: thick blood is dark maroon to near-black, glossy, with clots; thin films are translucent red; never uniform bright-red tubes.
- Test: render a time sequence (at least 6 moments from 0 to 60 s) — the blood must visibly originate in the wound and travel outward/downward; any blood appearing somewhere without a path from the wound is a HIGH-severity failure.

In gore.py: drop the stamped gore_blood pools/rings around wounds; add a blood-fill surface inside each wound cavity; seed streams only at the lowest rim point(s); drive stream length/width/branching and the trailing stain by drip_time and bleed; keep impact spatter only as flung droplets (exits spray away from the head).

## Status after fix round 3 (anatomy.py)

Done: eye centres at (±0.0315, −0.0675, 0.022) (IPD 63 mm, 2.5 mm deeper in the orbit), brow ridge ~40 % stronger,
upper lid lower over the iris (LID_UP 0.305); zygomatic prominence (Gaussian at x 0.050) with a deeper sub-malar
hollow and a wider cheekbone body; face block ~3 mm wider at the mid-face; a soft jaw-angle (gonion) mass; neck
necked in under the jaw (~100 mm wide mid-neck); cranium broader and less egg-shaped (radii 0.076 / 0.097 / 0.0975);
ears stand off less (17°) and lean back more (17°) with a shorter lobe (~14 mm); nostrils opened larger. All 30
layer overlap checks pass (`python3 anatomy.py`). Also new for the cutaway: cervical spine (`GH_Cervical`), the
spinal cord continuing the brain stem down the canal, an airway (pharynx → trachea) carved in the muscle layer,
a frontal sinus, a larger maxillary sinus, a thinner palate and a domed tongue.
Not done: a full sculpt-level rebuild of the auricle (helix roll / antihelix Y are the round-1 ones).


## Standing rule (user, 2026-09-27)
"ensure 1:1 realism on ur efforts. allways" — every change, on every part, is judged against real anatomy and the reference photos; nothing is "good enough" if it looks less real than the refs.
