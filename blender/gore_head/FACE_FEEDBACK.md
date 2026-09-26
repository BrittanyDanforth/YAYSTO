# Face feedback from the user (to apply to anatomy.py after the current gore review/fix run)

Reference images (git-ignored, local only): `refs/face_ref_sculpt.png` (neutral sculpted head, 3 views) and
`refs/face_ref_male.webp` (realistic bald adult male, several angles). Use them for proportions and form only —
do not copy a specific person's likeness; our head stays a generic fictional man.

The user's verdict on the current head (verbatim intent):
- **Ears are NOT correct-looking.** Rebuild them: proper helix rim curling over, antihelix Y-fork, deep concha bowl
  leading into the canal, tragus and antitragus, and a SMALL lobe. Ears sit between brow line and nose base, tilted back
  ~15-20°, and stand off the head only slightly.
- **Earlobes are far too long.** Shorten to a normal adult lobe (~15-20 mm of the ~60-65 mm ear height).
- **Eyes look bug-eyed.** Seat the eyeballs deeper in the orbits: more brow-ridge overhang, deeper upper-lid crease and
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
