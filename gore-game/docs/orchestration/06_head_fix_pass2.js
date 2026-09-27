export const meta = {
  name: 'gore-head-fix-pass-2',
  description: 'Thorough head fix pass: blood from the hole, vessels, streams, wounds, bone, eyes, crush, face; critics against the refs and 5.18 standard',
  phases: [
    { title: 'Fix', detail: 'blood/vessels, wounds/eyes/bone, face; then fixes after each review' },
    { title: 'Review', detail: 'blood, wounds and face/system critics vs the real refs' },
  ],
}

const DIR = '/home/user/YAYSTO/blender/gore_head'
const SCRATCH = '/tmp/claude-0/-home-user-YAYSTO/e2a2594c-08ec-5384-b9ca-fd553ec0f442/scratchpad'

const PRE = `You are part of a small team building a procedural human head with a layered gore system in Blender, entirely from code, for a horror game / film-prop style asset.
Project folder: ${DIR}. Read ${DIR}/CONTRACT.md first: it is the spec. ${DIR}/gh_common.py has shared helpers (reset_scene, get_collection, ensure_controls, drive, setup_stage, render, render_views) — use them.
Blender is available as the Python module: run scripts with \`cd ${DIR} && python3 <script>.py\` (bpy 5.0.1, Cycles CPU, 4 cores, no GPU). There is no GUI: check your work by rendering PNGs and LOOKING at them with the Read tool. Do this repeatedly and be harshly self-critical about what you see. The user explicitly wants a high-effort result and got angry at anything that looked lazy; a blobby, placeholder-looking or half-working result is a failure.
HARD RULES:
- Absolutely no downloads of any kind (no meshes, textures, HDRIs, add-ons, pip installs, git clones, curl/wget). The user explicitly forbade it. Everything is procedural code. Blender's built-in procedural textures/nodes are fine.
- Do not git commit or push; the lead does that.
- Only edit the files you own (named in your task). If you need something from another module, work around it in your own file and mention it in your notes.
- Keep test renders <= 640px and <= 48 samples (denoised). Another agent may be rendering at the same time on the same 4 cores. Put throwaway renders in ${SCRATCH}/<your-name>/, only keep final module renders in ${DIR}/renders/.
- Blender 5.x Python API: verify API names by trying them (print dir(...)), don't guess. Geometry nodes: bpy.data.node_groups.new(name,'GeometryNodeTree'), ng.interface.new_socket(name=..., in_out='INPUT'|'OUTPUT', socket_type='NodeSocketFloat'|...), ng.is_modifier=True; set modifier inputs via mod[socket.identifier].
- Code must also run as \`blender -b --python build.py\` on Blender 5.1: no absolute paths (use gh_common.HERE), no reliance on module-only behavior.
- Match a clean, readable code style: docstrings on public functions, short comments where the math is not obvious.`

const BUILD_SCHEMA = {
  type: 'object',
  properties: {
    status: { type: 'string', enum: ['done', 'partial', 'failed'] },
    files_changed: { type: 'array', items: { type: 'string' } },
    renders: { type: 'array', items: { type: 'string' } },
    summary: { type: 'string', description: 'what was built and how, API/interface details other modules need' },
    known_issues: { type: 'array', items: { type: 'string' } },
  },
  required: ['status', 'files_changed', 'renders', 'summary', 'known_issues'],
}

const CRITIC_SCHEMA = {
  type: 'object',
  properties: {
    verdict: { type: 'string', enum: ['ship', 'needs_work'] },
    what_is_good: { type: 'string' },
    issues: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['high', 'medium', 'low'] },
          area: { type: 'string', description: 'file / feature' },
          problem: { type: 'string', description: 'what is wrong, with evidence (render path, command output)' },
          fix: { type: 'string', description: 'concrete fix: what to change where' },
        },
        required: ['severity', 'area', 'problem', 'fix'],
      },
    },
  },
  required: ['verdict', 'what_is_good', 'issues'],
}


const USER_FEEDBACK = `USER FEEDBACK (TOP PRIORITY, the user was blunt about it): "THE CUTS LOOK LIKE STICKERS. Ensure it's the actual skin, all that cutting and slicing, not a sticker, nicely realistic, 1:1 realism." Every wound must be REAL GEOMETRY in the skin, never a flat painted patch:
- the skin surface itself is cut and displaced: the two edges of a cut are physically separated (gape), the margin shows the skin's own thickness (a thin pale epidermis/dermis line, then yellow lobular fat, then red muscle walls going down into a V-shaped or irregular recessed bed), with ambient occlusion/shadow inside;
- wound lips are slightly swollen and raised or everted, with irregular micro-torn margins (lacerations: abraded, bridged, ragged; incised cuts: sharp but still with thickness and gape), never a perfectly smooth lens outline;
- the wound bed sits clearly BELOW the surrounding surface; blood pools inside it and wells over the lowest lip before running down;
- silhouette test: viewed at a grazing angle or in profile the wound visibly breaks the surface contour (a notch/opening), and a cross-section shows real walls;
- bullet holes are real openings you can look into, bruising/abrasion is under or on the skin, burns shrink/blister/split the skin geometry.
Also match the fact-checked research in /home/user/YAYSTO/gore-game/docs/research/01_gunshot_wounds.md and 02_sharp_blunt_burn.md: 9 mm entrance in scalp ~6-9 mm hole (0.7-1.0 x calibre), elsewhere often SMALLER than the bullet (4-6 mm), with a 1-3 mm red-brown abrasion collar (eccentric for angled shots); head exits 10-30 mm stellate/irregular, everted, no collar; cut gape = length x G(theta) x depth x region factor (a 40 mm cut across tension lines through the dermis gapes ~6-10 mm, along the lines only 1-2 mm; scalp cuts through the galea gape 12-20 mm); lacerations over bone (eyebrow, cheekbone, chin, scalp) are ragged with tissue bridges. Entrance holes that are coin-sized are wrong.
Also apply the "current head vs real" fix table in /home/user/YAYSTO/gore-game/docs/REALISM_BIBLE.md §2.7 (25 rows: e.g. skull entry hole larger than the skin hole with inward bevel, concentric collar unless angled, soot/stipple for close shots, varied exit shapes, spatter directed away from the victim, knife cannot cut through the skull, bruises/burns develop over time, wider drips, thick pools near-black red). Other known issues: a shot into the open mouth lands inside the mouth cavity and does not hit lips/teeth; blunt splits have paper-sharp edges (need crushed, abraded, bridged margins); teeth show brown speckles that read as rot instead of blood; not enough blunt swelling; burns look like even confetti instead of zones of different depth with shrinking and cracking skin.`

const BLOOD_RULE = `BLOOD MUST COME FROM THE WOUND (user, verbatim: "VERY UNREALISTIC BLOOD WOULD POUR OUT THE WOUND OF HEADSHOT AND NOT MAGICALLY APPEAR BLOOD AROUND THE HOLE IT WOULD COME FROM THE INJURY ETC BE 1:1 REALISTIC THATS STANDARD EXTREME REALISM"):
- NO blood may appear on the skin that did not physically get there. Remove any pre-painted halo/pool/smear around a wound (e.g. gore_blood teardrops or rings stamped around the hole). Every stain on the skin must be connected to the wound by the path the blood actually travelled, or be an impact spatter droplet thrown at the moment of the hit.
- Sequence (animate/time-drive it): t=0 hole opens, impact spatter only (exits throw blood and tissue AWAY from the head; entrances get back-spatter toward the shooter, very little on the victim's own skin); then blood WELLS UP inside the wound cavity (a blood surface filling the hole, dark and glossy, brain/tissue extruding at exits); it OVERFLOWS at the LOWEST point of the wound rim; a continuous stream POURS from that lip and runs down under gravity following the skin's shape (around the jaw line, down the neck), with a rounded bead at the leading front; the front advances at a realistic speed (cm/s on skin), the stream widens with volume, more streams split off the rim as flow increases, it collects in creases and drips off low points (chin, earlobe, nose). Behind the front, a thinner film/stain remains along the path and darkens as it dries at the edges.
- Flow rate follows the injury: scalp/head wounds bleed heavily and keep pouring; arterial = pulsing surges; after cardiac arrest only slow gravity drainage.
- Look: thick blood is dark maroon to near-black, glossy, with clots; thin films are translucent red; never uniform bright-red tubes.
- Test: render a time sequence (at least 6 moments from 0 to 60 s) — the blood must visibly originate in the wound and travel outward/downward; any blood appearing somewhere without a path from the wound is a HIGH-severity failure.`
const REFS_RULE = `
MANDATORY VISUAL REFERENCES (user is angry nobody looked at them): open EVERY image in /home/user/YAYSTO/refs/ (list the folder first; there are 21+ files) with the Read tool, one by one, before judging or changing any wound. In your report, list every refs/ filename you opened and one line of what you took from it — a report without that list is invalid, and compare your renders side by side against them. Per-image notes: /home/user/YAYSTO/gore-game/docs/REFERENCE_NOTES.md §5 (esp. §5.10-5.13). refs/12_our_render_wall_stripes.png shows OUR current cut wall: the regular vertical stripe/fence-plank banding and hard orange lip line are a HIGH-severity artefact — real wound walls (refs 13, 15, 16) are irregular, lumpy, torn, wet, clot-filled with strands and pits and no repeating pattern. Use the refs for injury/tissue/blood properties only, never faces or identities.`

// ---------------------------------------------------------------------------
// Head fix pass 2 (2026-09-27): every point the user raised after the final pass,
// plus everything the lead flagged, fixed thoroughly and proven with renders.
// ---------------------------------------------------------------------------
const ALL_ITEMS = `EVERYTHING BELOW IS MANDATORY (the user: "ENSURE ALL THOSE STUFF I SAID AND U SAID WILL GO INTO FINAL PASS ... VERY VERY THOROUGH AND NOT LAZY ... USES STANDARD ETC AND REAL IMAGES I GAVE"; standing rule: "ensure 1:1 realism on ur efforts. allways").
Read in full before starting: /home/user/YAYSTO/gore-game/docs/REFERENCE_NOTES.md sections 5.9-5.21 (5.21: every stream must trace up into an overflowing low point of a wound rim, never start on intact skin beside a cut; drops ~3-4.5 mm, streams 2-5 mm wide and 0.1-0.4 mm thick, not fat berries/tape) and section 6 (5.18 is the VISUAL ACCEPTANCE STANDARD, 5.19 and 5.20 are the newest user verdicts), /home/user/YAYSTO/CLAUDE.md sections 7 and 8 (incl. "Head backlog after the final pass"), ${DIR}/FACE_FEEDBACK.md, and REALISM_BIBLE.md section 2.7 plus the circulation / vessel table (grep the headings).
ITEMS (all HIGH):
1. BLOOD COMES OUT OF THE HOLE ITSELF, ZERO GAP (5.17, 5.19.1, the user's crop of renders/hero.png). The opening fills with dark glossy blood welling from inside the track; that surface rises to and over the LOWEST point of the opening's own edge; the stream is the same liquid body, its top INSIDE the hole, its top outline following the rim it spills over, never wider than that part of the rim, widening only further down. Today: entry = dry dark hole with the stream starting on the collar below it; exit = pale strip of skin between the torn opening and the streams; hero forehead entry = flat-topped stream wider than the hole with a wedge of clean skin on its right. PROOF REQUIRED: a script that renders every bleeding wound (entry, exit, slash, blunt, blast, crushed) at t = 0/5/10/20/40/60 s from straight, 45 deg and grazing at the rim, crops to the rim and samples pixels along the stream axis from inside the hole to 5 mm below the rim; any skin-coloured pixel = FAIL. Save the crops as ${DIR}/renders/proof_rim_zero_gap.png and report the numbers.
2. THIN SKIN (5.16, 5.19.2): wound margins read as thick moulded sleeves/rounded lips. Real face skin 1.5-3 mm, scalp up to 5-7 mm with galea: a thin pale dermis line over yellow lobular fat, torn and irregular, deeper tissue recessed and shredded. Remove rounded rims, cut wall thickness and bevel.
3. BLEEDING WIRED TO REAL VESSELS (5.19.3): add a head vessel table (superficial temporal a./v. with frontal/parietal branches, occipital, posterior auricular, supraorbital/supratrochlear, facial/angular, superior/inferior labial, infraorbital, middle meningeal, diploic veins, superior sagittal/transverse sinuses, scalp venous plexus, ophthalmic/retinal for the eye) in gore.py + CONTRACT.md with approximate paths in head coordinates. Each hit finds the vessels it cuts and that drives bleed rate, stream count/length, colour (arterial bright scarlet #C0141E with pulsing surges and faster/longer streams; venous dark maroon #8E1420 steady welling; bone/diploe and brain = dark ooze mixed with tissue) and persistence (scalp keeps pouring). Two wounds never bleed identically. Keep the table machine-readable so the Godot game can reuse it.
4. STREAMS (5.18 G): no straight even-width bars/ribbons/rods with flat ends. Branching, beading fronts with rounded drops, thin translucent film behind, contour-following (around the brow, nose, lips, jaw line, down the neck), collecting in creases, dripping off chin/nose/earlobe, drying darker edges, clots; FAR more volume (refs 2, 7, 17, 21: soaked faces, streams down the neck).
5. EXIT WOUND: currently a near-square hole with white chips and flat red slabs. Must be ragged/stellate/irregular (shape mix in CLAUDE.md section 10), everted 1-4 mm, shredded margins with extruding brain/tissue and bone fragments, larger than the entry (head exits 10-30 mm). Match refs/20 and refs/gsw_pathology_sheet.webp.
6. BONE everywhere: matte, pale chalky ivory #E6DCC4 with blood in cracks, chunky fragments with thickness, diploe visible on broken edges; never white paper sheets, plaster flakes or pebbles.
7. MUSH (5.18 A-C): destroyed tissue = wet pulp, lumps at 3 scales, torn folded flaps with pale fatty undersides, strings, clot-filled pits; 4+ distinct colours per large wound; broken scattered specular (no plastic sheen); no regular stripes/banding (refs/12); tissue bridges few and irregular (the comb-like parallel strings across the blunt wound are wrong).
8. CRUSHED PRESET: the head SILHOUETTE must change (mid-face and orbit pushed in, nose flattened and deviated, profile loses projection), massive dark purple swelling (refs 15, 16). The NOSE TIP is part of the injury (5.20.1): broken/flattened/displaced, skin split, swollen purple, blood from the nostrils. No region inside or bordering a wound stays pristine (nose, lips, lids, ears).
9. EYES (5.20.2-3): true size (GH_Eye r 0.012; trauma never enlarges it; the crushed render shows it ~1.5x and bulging). Build real eye damage in GH_Gore on the eye layer, per hit: globe rupture (deflates, collapses, wrinkles, misshapen; jelly vitreous and dark uveal tissue extruded through the tear; cornea clouded/torn), hyphaema (layered blood behind the cornea), subconjunctival haemorrhage (solid bright red white of the eye), lid lacerations, periorbital swelling that can close the lids, orbital blow-out with enophthalmos, a bullet/fragment through the orbit destroys the globe. An uninjured eye stays pristine. Close-up renders vs real anatomy.
10. MOUTH BLAST (5.15): mid-face pulp beyond a neat oval, jaw in segments with teeth still in them, loose teeth, gums/palate/tongue/lining destroyed (nothing intact), soot and stipple on the remaining skin, heavy blood down chin and neck. Teeth: realistic enamel (ivory, translucent edges, blood smears), not white plastic.
11. SLASH: irregular torn/tapered outline (not a perfect lens), gape per skin tension lines, V-shaped walls with a thin skin line; the black dots in the tail are an error, remove them; streams per item 4.
12. BLUNT: crushed abraded margins, tissue bridges, swelling, bruising (red-purple at this wound age); a scalp wound pours heavily (today the blunt preset's scalp split does not bleed at all, only the lip does).
13. BURN: less plastic gloss, irregular zone boundaries (not a straight line down the face), dose-driven zones, blisters.
14. ENTRY: small and irregular (scalp 6.3-9 mm, abrasion collar 1.6-2.4 mm), not a neat round ring; the skull hole larger with an inward bevel.
15. CUTAWAY: the brain cut face shows gyri/sulci folds, grey vs white matter, blood in the sulci, no flat cream patch; the eye in the cutaway is a real globe section (lens, vitreous, retina layers), not a disc; bone with cortex + diploe.
16. FACE (FACE_FEEDBACK.md): eyelids with real thickness, upper-lid crease, lash line, caruncle and tear film (today the eye openings look cut into a flat mask, renders/materials_head_eye.png); correct ears (helix roll, antihelix Y, concha, tragus, SMALL lobe ~15-20 mm), real cheekbones with a sub-malar hollow, head not too long / not egg-shaped, open teardrop nostrils with alar rims and columella; keep the nose base and the teeth design. The deeper-set-eye change is NO LONGER required (keep the eyes unless anatomically wrong). The face stays a generic fictional man, not a specific person.
16b. FROM THE FINAL PASS'S OWN FAIL LIST (also mandatory): the deep cheek slash reads as a 'second mouth' from 3/4 (must read as a cut, walls with tissue layers, not lips); the throat cut needs cross-section anatomy (granular muscle, trachea/larynx rings, vessel openings, clot, refs 1/17); burn: eye in the burn zone must be affected (cooked opaque cornea, singed lashes/brows), lid and lip contraction (ectropion), no near-vertical edge beside the nose, blisters not glossy plastic; the entrance abrasion collar must not read as an even ring decal; the tongue must not be a slab (real domed muscular tongue, papillae, torn when hit); the crushed-orbit eye must not be a dark maroon ball from 3/4 (follow item 9); the face must not read as a mannequin (skin micro-detail: pores, fine wrinkles, subtle colour zones; ears not clay-like).
17. The head on its own must stay undeformed; do NOT edit /home/user/YAYSTO/blender/gore_body/ (the body imports the head read-only and another team is working on it right now).
Every item ends with renders you LOOKED at, placed side by side with the matching refs, and a 5.18 section-H PASS/FAIL table.`

const BUDGET = `The CPU is shared with the body team: Cycles renders use at most 2 threads (scene.render.threads_mode='FIXED', threads=2), <= 640 px and <= 48 samples while iterating; run the full \`python3 build.py\` only once your changes are in. Never run two head builds at the same time (check \`ps\` for another build.py under ${DIR}).`

const FIXERS = [
  { key: 'blood', title: 'blood source, vessels and streams', items: '1, 2, 3, 4 (and the blood parts of 5, 10, 11, 12)' },
  { key: 'wounds', title: 'wound morphology, bone, mush, crush, nose, eyes, teeth', items: '5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15' },
  { key: 'face', title: 'face anatomy + full build', items: '16 (then re-verify 17 and run the full build with all renders)' },
]

const history = []
phase('Fix')
for (const f of FIXERS) {
  const r = await agent(`${PRE}

YOUR TASK: head fix pass 2, part "${f.title}". You may edit any project file in ${DIR} (anatomy.py, materials.py, gore.py, build.py, gh_common.py, CONTRACT.md, FACE_FEEDBACK.md). You own items ${f.items} of the list below; do them completely and properly, not a token change. Earlier parts of this pass already ran (their reports follow); do not undo their work. NOTE: a container restart interrupted an earlier run of this pass; the previous blood fixer's edits (vessel table, cavity blood fill, rim overflow in gore.py/materials.py, test scripts in ${SCRATCH}/fix2_blood/) are already in the files. Inspect the current state first and continue from it; its last tests still showed a gap under the blunt scalp split, a stream starting on skin beside the cheek slash, fat berry drops and thick tape streams.
${ALL_ITEMS}
${USER_FEEDBACK}
${BLOOD_RULE}
${REFS_RULE}
${BUDGET}
Earlier parts: ${JSON.stringify(history, null, 1)}${f.key === 'wounds' ? '\nNOTE: a second container restart interrupted an earlier run of this wounds part after ~6 hours of work; its edits are already in gore.py/materials.py/anatomy.py and its renders/tests are in '+SCRATCH+'/fix2_wounds/ (latest sheets f3.png, m10.png). Done so far per its renders: crushed crater incl. nose side, eye rupture, eye/orbit cutaway, burn reaching the eye with irregular zones, blast mid-face pulp, open neck gash. Still open per the lead: cheek slash reads as a second mouth; neck gash needs a torn cross-section (muscle, trachea, vessels); crushed lower face coated in one glossy blood gel bag; bone plates paper-like; exit streams flat jagged cut-outs; blast teeth candy-white; cutaway brain centre flat; everything too glossy; no swelling/bruise on the blunt preset. Inspect the current state, do NOT redo finished work, finish the open items, then run the full build.' : ''}
Put throwaway renders in ${SCRATCH}/fix2_${f.key}/. Run \`cd ${DIR} && python3 gore.py --no-render\` (verify_gore) and \`python3 anatomy.py\` (overlap checks) after your changes; both must pass. Report honestly what is still not 1:1.`,
    { label: `fix2:${f.key}`, phase: 'Fix', schema: BUILD_SCHEMA })
  history.push({ part: f.key, summary: r ? r.summary : 'agent failed', still_open: r ? r.known_issues : [] })
}

const CRITICS2 = [
  { key: 'blood', role: 'forensic pathologist / blood-flow VFX supervisor', focus: 'items 1-4: the zero-gap proof (re-run the rim pixel test yourself and inspect proof_rim_zero_gap.png), vessel wiring (does each wound bleed per its vessels?), stream realism and volume vs refs 2, 7, 17, 21' },
  { key: 'wounds', role: 'horror prosthetics supervisor + forensic pathologist', focus: 'items 5-15: exit shape, bone look, mush standard, crushed silhouette and nose, eye size and eye trauma, blast, slash, blunt, burn, entry, cutaway vs refs 3, 13, 15, 16, 18, 19, 20 and the GSW sheet; render every wound from 3 angles + a cross-section' },
  { key: 'face', role: 'senior character artist + systems reviewer', focus: 'item 16 vs refs/face_ref_* proportions (ears, cheekbones, head length, nostrils), item 17, code health: verify_gore and the anatomy overlap checks pass, build.py runs clean, damage=0 is intact, CONTRACT.md updated, paths work on Blender 5.1' },
]
for (let round = 1; round <= 2; round++) {
  phase('Review')
  const res = await parallel(CRITICS2.map(c => () => agent(`${PRE}

YOU ARE A CRITIC (fix pass 2, review round ${round}); do not edit project files; scratch renders only under ${SCRATCH}/critic2_${c.key}_r${round}/. Role: ${c.role}. Focus: ${c.focus}.
${ALL_ITEMS}
${REFS_RULE}
${BUDGET}
What the fixers reported: ${JSON.stringify(history, null, 1)}
Be strict: anything cleaner, drier, smoother, more uniform, more symmetric, less bloody or less anatomically right than the refs is a HIGH issue. Put the 5.18 section-H PASS/FAIL table in what_is_good. Verdict 'ship' only if every item in your focus passes.`,
    { label: `critic2:${c.key}:r${round}`, phase: 'Review', schema: CRITIC_SCHEMA }).then(r => (r ? { critic: c.key, ...r } : null))))
  const crits = res.filter(Boolean)
  const issues = crits.flatMap(c => c.issues.map(i => ({ critic: c.critic, ...i })))
  const highs = issues.filter(i => i.severity === 'high').length
  log(`Fix pass 2 review r${round}: ${highs} high, ${issues.length} total; ${crits.map(c => c.critic + '=' + c.verdict).join(', ')}`)
  if (crits.length === CRITICS2.length && crits.every(c => c.verdict === 'ship') && highs === 0) { history.push({ round, result: 'all critics ship' }); break }
  phase('Fix')
  const fx = await agent(`${PRE}

YOUR TASK: head fix pass 2, fixes after review round ${round}. You may edit any project file in ${DIR}. Fix ALL high issues and every medium you can:
${JSON.stringify(issues, null, 1)}
${ALL_ITEMS}
${REFS_RULE}
${BUDGET}
Then run verify_gore, the anatomy overlap checks and the full \`python3 build.py\` (all renders, including proof_rim_zero_gap.png), LOOK at every render next to the refs, and report honestly.`,
    { label: `fix2:r${round}`, phase: 'Fix', schema: BUILD_SCHEMA })
  history.push({ round, issues: issues.map(i => `[${i.severity}] ${i.critic}/${i.area}: ${i.problem}`), fixed: fx ? fx.summary : 'fix failed', open: fx ? fx.known_issues : [] })
}
return { history }
