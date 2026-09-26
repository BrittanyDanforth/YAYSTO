export const meta = {
  name: 'gore-head-build',
  description: 'Build a procedural Blender head (skull, brain, eyes, teeth) with a layered gore system, then critique and fix it',
  phases: [
    { title: 'Build', detail: 'anatomy, materials and gore modules in parallel' },
    { title: 'Integrate', detail: 'assemble build.py, presets, renders, .blend' },
    { title: 'Review', detail: 'visual, gore and system critics' },
    { title: 'Fix', detail: 'apply critic findings and re-render' },
    { title: 'Finalize', detail: 'clean rebuild, README, final renders' },
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

const ANATOMY = `${PRE}

YOUR TASK: you own ${DIR}/anatomy.py (plus the landmark table in CONTRACT.md if you change landmarks). Implement build_anatomy() exactly per the contract: GH_Skin, GH_Muscle, GH_Skull, GH_Jaw, GH_Brain, GH_Eye_L, GH_Eye_R, GH_Teeth_Upper, GH_Teeth_Lower, GH_Gums, GH_Tongue, GH_MouthCavity, all in collection GoreHead, returned as a dict. Also export ANATOMY_LANDMARKS (dict of actual coordinates).

QUALITY BAR: a believable adult human head (neutral expression, stylized-realistic, like a clean game-character base mesh), NOT an egg, blob or mannequin. Clearly readable: brow ridge, eye sockets with upper and lower eyelids wrapping the eyeballs, nose bridge, nose tip, nostrils and alae, cheekbones, nasolabial folds, upper lip with cupid's bow and lower lip, lips parted ~6-8 mm with a dark mouth cavity behind where the upper/lower teeth and tongue are visible, chin, jawline running back to the ears, real ears (helix, antihelix, concha, lobe; not bumps), neck with a flat cut at the bottom.
Inside (seen through wounds and in a cutaway): skull with real bone thickness (outer + inner surface, closed solid), orbits, nasal aperture, cheekbones/zygomatic arches, maxilla; mandible (GH_Jaw); brain with two hemispheres separated by the longitudinal fissure, convincing gyri and sulci folds (not just noise bumps: use ridged/turbulent patterns so it reads as brain folds), cerebellum, brain stem, sitting in the cranial cavity with a 2-3 mm gap; two eyeballs (origin at eyeball center, local -Y forward, radius 0.012, with a slight cornea bulge; iris/pupil are shaded by the materials module from local coordinates, so keep that convention); individual shaped teeth (incisors, canines, premolars, molars; 14-16 per row) on a proper dental arch in gums; tongue; mouth cavity lining that closes the skin's mouth opening so there is no void.
GH_Muscle is a soft-tissue shell between skin and skull (3-4 mm under skin on scalp, thicker at cheeks/jaw) that must not intersect the skull.
No interpenetrations: brain inside skull cavity; skull inside muscle inside skin; eyes inside orbits and not poking through the eyelids; teeth behind the lips; tongue inside mouth. Skin should be a clean manifold with even density (evaluated >= ~60k verts is fine; keep total build under ~60 s).
Techniques you may use: bmesh + math (quad sphere / subdivided cube deformed by sums of smooth falloff bumps and dents placed at landmarks, openings cut and extruded inward), separately-modelled ears joined and remeshed, voxel remesh of unions of shapes (booleans/metaballs) then smoothing, Subdivision/Displace/Smooth/CorrectiveSmooth modifiers applied, Blender's built-in procedural textures for displacement. Expect to iterate a LOT on the face shape: render front, three-quarter and side views after each change and compare against your knowledge of real head anatomy and proportions.

TESTS: \`python3 anatomy.py\` must build everything with simple temporary look-dev materials (skin-ish, bone, pink brain, white eyes with dark iris disc, off-white teeth) and render ${DIR}/renders/anatomy_front.png, anatomy_three_q.png, anatomy_side.png, plus ${DIR}/renders/anatomy_cutaway.png: a cutaway (e.g. Boolean DIFFERENCE of a box over x>0 added only for that render) that shows skin, muscle, skull thickness, the brain inside, eyes in orbits, teeth and tongue. Also print a check report of the interpenetration tests you implemented (e.g. sample points / BVH overlap between layers).
Report in summary: object list, landmark coordinates, vertex counts, build time, anything the gore/material modules must know (e.g. eye convention, whether GH_MouthCavity is separate).`

const MATERIALS = `${PRE}

YOUR TASK: you own ${DIR}/materials.py. Implement build_materials() -> dict and assign_materials(objs, mats) per the contract (Materials section and the gore attribute table). Materials: GH_Skin, GH_Muscle, GH_Fat, GH_Bone, GH_Brain, GH_Blood, GH_Eye, GH_Teeth, GH_Gums, GH_Tongue, GH_MouthInterior (+ GH_Lips optional). assign_materials maps: GH_Skin->GH_Skin, GH_Muscle->GH_Muscle, GH_Skull & GH_Jaw->GH_Bone, GH_Brain->GH_Brain, GH_Eye_L/R->GH_Eye, GH_Teeth_*->GH_Teeth, GH_Gums, GH_Tongue, GH_MouthCavity->GH_MouthInterior; skip missing objects gracefully. The gore geometry nodes will use Set Material with GH_Blood, GH_Fat and GH_Muscle by name, so those must exist exactly.
QUALITY: realistic procedural shading (all procedural nodes, no images):
- GH_Skin: subsurface scattering (Principled BSDF, random walk), micro bump pores (voronoi/noise), subtle mottling and redness variation, driven by skin_tone (light->dark) and pallor (desaturate/grey-blue). Reads gore attributes via Attribute nodes (attribute_type 'GEOMETRY'): gore_wound + gore_depth paint the wound interior in rings skin -> yellow fat -> dark red striated muscle -> off-white bone; gore_edge = abraded/torn dark red-brown rim; gore_blood = wet blood layer on top (color & roughness from wetness/blood_age, thin film look); gore_bruise = purple-blue-yellow bruise under the skin; gore_burn = charred black-brown, cracked, with raw red blistered transition. With all attributes absent (0) it must look like clean healthy skin.
- GH_Muscle: dark red, fiber striation (stretched wave/noise), wet sheen, fascia hints. GH_Fat: yellow lobular fat. GH_Bone: off-white/ivory, porous bump, reads gore_fracture (dark crack lines, blood in cracks) and gore_blood. GH_Brain: pinkish-grey, glossy wet, fine vessels, blood from gore_blood. GH_Blood: fresh = deep saturated red with glossy clearcoat and slight translucency; blood_age -> dark brown-black matte; wetness controls roughness. GH_Eye: sclera (slightly veiny, bloodshot by gore_blood), iris with radial fibers and limbal ring, black pupil, glossy clear cornea (coat); convention: eye origin at eyeball center, local -Y is forward, eyeball radius 0.012, iris radius ~0.0058, pupil ~0.0022 — shade by Texture Coordinate Object. GH_Teeth: enamel, slight translucency, yellowish gradient to the root. GH_Gums/GH_Tongue/GH_MouthInterior: wet pink-red, tongue papillae bump.
- Drivers from GH_Controls via gh_common.drive for wetness, blood_age, skin_tone, pallor on node values (Value nodes are convenient).
TESTS: \`python3 materials.py\` builds a look-dev scene: spheres/test shapes per material, plus a gore test object (a subdivided sphere with synthetic gore attributes you compute in Python: a wound disc with gore_wound=1 and a radial gore_depth gradient, an edge ring, blood streaks running downward, a bruise patch, a burn patch, and a bone sphere with fracture lines). Render to ${DIR}/renders/materials_lookdev.png and materials_gore_test.png (+ a close-up of the eye as materials_eye.png) and LOOK at them; iterate until they look photographic, not like flat CG. Also render the same gore test with blood_age=1 (materials_dried.png).
Report: material names, which attributes each reads, driver hookups, any convention the anatomy/gore modules must follow.`

const GORE = `${PRE}

YOUR TASK: you own ${DIR}/gore.py. Implement the gore system exactly per the contract's "Gore system" section: hit collections under GH_Hits (GH_Hits_Bullet, _Exit, _Slash, _Blunt, _Burn), empties as hits (location/rotation/scale semantics as specified), add_hit(kind, location, direction=None, size=1.0, elongation=1.0, depth=0.6, name=None) that snaps to the skin surface (raycast against the evaluated GH_Skin along the direction, or nearest surface point), clear_hits(), and build_gore_system(objs) that adds a geometry-nodes modifier named GH_Gore on every damageable layer (GH_Skin, GH_Muscle, GH_Skull, GH_Jaw, GH_Brain, GH_Eye_L/R, GH_Teeth_Upper/Lower, GH_Gums) using one shared node group with a layer setting, and drivers from GH_Controls (damage, bleed, drip_time, bruising, swelling) via gh_common.drive.
It must be LIVE: GN reads the hit collections (Collection Info with Separate Children / Instance transforms, Object Info, etc.), no Python baking. Moving, rotating or scaling an empty changes the wound.
WOUND LOOKS (should read as real injuries on a horror-film prop, not blobby dents):
- bullet entry: small clean round hole (~4-5 mm radius at size 1) with a dark abrasion collar (gore_edge), punches through layers according to depth; at depth 1 it holes the skull (with visible bone thickness and bevelled inner table) and craters the brain.
- exit: 2-4 cm ragged, star-shaped tear with everted (outward-pushed) torn flaps, bone fragments / jagged bone edge when through the skull, lots of blood.
- slash: long thin gash along the empty's local X (length from scale.y), gaping lips, V-shaped walls, depth to muscle or bone.
- blunt: swelling (from swelling control), bruise (gore_bruise, from bruising control), stellate split in the skin at the center, depressed skull fracture with radiating crack lines (gore_fracture) when deep; teeth near a blunt hit get knocked out (removed or displaced/tilted and bloodied).
- burn: charred, shrunken skin with blister bumps and peeling edges (gore_burn).
LAYERING: shared group with a layer parameter so holes are nested and aligned: skin hole widest, muscle smaller, skull smaller still and only breached when depth >= ~0.8 (bullet/exit/blunt), brain gets a crater. Wound walls must have thickness: extrude the hole boundary inward toward the next layer with gore_depth rising 0 -> 1 down the wall so the shader paints skin/fat/muscle/bone rings; ragged torn edges via noise. Write all attributes from the contract table (gore_wound, gore_depth, gore_edge, gore_blood, gore_bruise, gore_burn, gore_fracture). Set wound-wall materials with Set Material (GH_Fat / GH_Muscle exist by those names if materials.py has run; create simple stand-ins if not).
BLOOD: gore_blood coverage pooled around wounds and running downward (world -Z) on the surface; real drip geometry on the skin layer: curves starting at wound rims, flowing downward under gravity while hugging the surface (step the curve down, snap each point to the nearest surface point / raycast, offset slightly along the normal), per-drip random length and width, bulbous bead at the tip, length grows with drip_time and bleed; convert to mesh tubes with GH_Blood material. Also a few spatter droplets around high-energy wounds (exit/bullet).
CONTROLS: damage=0 -> geometry identical to no hits (everything intact); bleed scales blood/drips; drip_time animates drips; bruising/swelling for blunt.
PERFORMANCE: full head with ~6 hits evaluates in < ~5 s.
DEVELOPMENT: the anatomy and materials builders are working in parallel right now. Start with placeholder layers made in your test harness (ellipsoid skin; muscle 4 mm inside; skull shell 6-7 mm thick; brain inside; a few simple extras) and switch to the real modules when they exist and work (\`import anatomy; anatomy.build_anatomy()\`, \`import materials\`), wrapped in try/except with fallbacks. Re-test against the real anatomy near the end if it's available.
TESTS: \`python3 gore.py\` renders close-ups ${DIR}/renders/gore_bullet.png, gore_exit.png, gore_slash.png, gore_blunt.png, gore_burn.png and gore_all.png (if materials.py is not available, shade with a debug material that visualises the attributes). LOOK at each one and iterate until they convincingly read as those injuries. Include verify_gore() that checks: attributes exist on evaluated meshes; damage=0 equals the no-hit result; moving an empty changes the evaluated skin; drip_time 0 vs 1 changes drip geometry; evaluation time. Run it and paste its output in your summary.
Report: node group names, modifier input names/identifiers, how hits are read, attributes written, known limitations.`

phase('Build')
const builds = await parallel([
  () => agent(ANATOMY, { label: 'build:anatomy', phase: 'Build', schema: BUILD_SCHEMA }),
  () => agent(GORE, { label: 'build:gore', phase: 'Build', schema: BUILD_SCHEMA }),
  () => agent(MATERIALS, { label: 'build:materials', phase: 'Build', schema: BUILD_SCHEMA }),
])
const [anat, gore, mats] = builds
const buildReport = JSON.stringify({ anatomy: anat, gore: gore, materials: mats }, null, 1)
log(`Build done: anatomy=${anat && anat.status}, gore=${gore && gore.status}, materials=${mats && mats.status}`)

phase('Integrate')
const INTEGRATE = `${PRE}

YOUR TASK: integrate. You own ${DIR}/build.py and you may make integration fixes in any module (list every change). The three module builders just finished; their reports:
${buildReport}

Write build.py that: reset_scene(); objs = anatomy.build_anatomy(); mats = materials.build_materials(); materials.assign_materials(objs, mats); gore.build_gore_system(objs); stage lighting and cameras; apply_preset(name) with presets:
- intact: no hits.
- gunshot: bullet entry at the right temple, exit wound on the opposite side toward the back (depth 1 so the skull is breached and brain shows through the exit), blood drips.
- slash: a deep slash across one cheek and a second cut across the forehead.
- blunt: blunt hit to the jaw that knocks out teeth + blunt hit on the cranium with a depressed skull fracture.
- burn: burn covering one half of the face.
- carnage: a heavy mix of all types, skull breached with brain visible, lots of blood.
Save ${DIR}/gore_head.blend (compressed, relative path) with the 'gunshot' preset active and an animation: damage 0 -> 1 over frames 1-12, drip_time 0 -> 1 over frames 12-120 (keyframes on GH_Controls props), frame range 1-120, cameras named for each view, the front camera active.
CLI: \`python3 build.py [--preset NAME] [--no-render] [--out FILE] [--samples N] [--res N]\` (also parse args after '--' so \`blender -b --python build.py -- --no-render\` works). Renders: for each preset, front and three_q into ${DIR}/renders/preset_<name>_<view>.png (640px, ~40 samples), plus ${DIR}/renders/cutaway.png (side cutaway of the intact head: skin/muscle/skull thickness/brain/eyes/teeth/tongue visible), plus a close-up of the gunshot exit wound ${DIR}/renders/closeup_exit.png.
Verify: the full build runs from scratch in one process with no errors; wounds line up through all layers on the REAL anatomy (tune per-layer radii/offsets if the layers are spaced differently than the placeholders); materials render correctly on the gore attributes; damage=0 looks intact. LOOK at every render and fix integration problems (holes that show void/black interior, misaligned layers, z-fighting, blood floating off the surface, teeth not visible, etc.). Report timings (build, evaluation, render) and the .blend size.`
const integ = await agent(INTEGRATE, { label: 'integrate', phase: 'Integrate', schema: BUILD_SCHEMA })


const USER_FEEDBACK = `USER FEEDBACK (TOP PRIORITY, the user was blunt about it): "THE CUTS LOOK LIKE STICKERS. Ensure it's the actual skin, all that cutting and slicing, not a sticker, nicely realistic, 1:1 realism." Every wound must be REAL GEOMETRY in the skin, never a flat painted patch:
- the skin surface itself is cut and displaced: the two edges of a cut are physically separated (gape), the margin shows the skin's own thickness (a thin pale epidermis/dermis line, then yellow lobular fat, then red muscle walls going down into a V-shaped or irregular recessed bed), with ambient occlusion/shadow inside;
- wound lips are slightly swollen and raised or everted, with irregular micro-torn margins (lacerations: abraded, bridged, ragged; incised cuts: sharp but still with thickness and gape), never a perfectly smooth lens outline;
- the wound bed sits clearly BELOW the surrounding surface; blood pools inside it and wells over the lowest lip before running down;
- silhouette test: viewed at a grazing angle or in profile the wound visibly breaks the surface contour (a notch/opening), and a cross-section shows real walls;
- bullet holes are real openings you can look into, bruising/abrasion is under or on the skin, burns shrink/blister/split the skin geometry.
Also match the fact-checked research in /home/user/YAYSTO/gore-game/docs/research/01_gunshot_wounds.md and 02_sharp_blunt_burn.md: 9 mm entrance in scalp ~6-9 mm hole (0.7-1.0 x calibre), elsewhere often SMALLER than the bullet (4-6 mm), with a 1-3 mm red-brown abrasion collar (eccentric for angled shots); head exits 10-30 mm stellate/irregular, everted, no collar; cut gape = length x G(theta) x depth x region factor (a 40 mm cut across tension lines through the dermis gapes ~6-10 mm, along the lines only 1-2 mm; scalp cuts through the galea gape 12-20 mm); lacerations over bone (eyebrow, cheekbone, chin, scalp) are ragged with tissue bridges. Entrance holes that are coin-sized are wrong.
Also apply the "current head vs real" fix table in /home/user/YAYSTO/gore-game/docs/REALISM_BIBLE.md §2.7 (25 rows: e.g. skull entry hole larger than the skin hole with inward bevel, concentric collar unless angled, soot/stipple for close shots, varied exit shapes, spatter directed away from the victim, knife cannot cut through the skull, bruises/burns develop over time, wider drips, thick pools near-black red). Other known issues: a shot into the open mouth lands inside the mouth cavity and does not hit lips/teeth; blunt splits have paper-sharp edges (need crushed, abraded, bridged margins); teeth show brown speckles that read as rot instead of blood; not enough blunt swelling; burns look like even confetti instead of zones of different depth with shrinking and cracking skin.`

const CRITICS = [
  {
    key: 'visual',
    prompt: (round, prior) => `${PRE}

YOU ARE A CRITIC (round ${round}); do not edit project files. Role: senior character artist judging the ANATOMY and overall visual quality. Look at ${DIR}/renders/ (preset_*, cutaway, anatomy_*, materials_*). Re-render extra angles or close-ups if needed (python, write to ${SCRATCH}/critic_visual_r${round}/; you may write small scratch scripts there that import the project modules). Judge: head proportions and silhouette; eyes and eyelids; nose; lips parted with teeth and tongue visible; ears; neck; skin shading realism; skull thickness; brain folds and placement; eyes in orbits; teeth shapes on the arch; intersections. Compare against real human anatomy. Also flag any wound that reads as a flat sticker rather than cut skin (see below).
${USER_FEEDBACK}
${prior}
Severity: high = immediately looks broken/ugly/fake or a contract feature is missing; medium = clearly noticeable quality gap; low = polish. Give concrete, actionable fixes (file, function, what to change). Verdict 'ship' only if there are no high issues and it would impress a demanding user.`,
  },
  {
    key: 'gore',
    prompt: (round, prior) => `${PRE}

YOU ARE A CRITIC (round ${round}); do not edit project files. Role: horror film prosthetics/VFX supervisor judging the GORE. Look at ${DIR}/renders/ (preset_*, closeup_exit, gore_*). Render your own close-ups of each wound type on the real head (write scratch scripts in ${SCRATCH}/critic_gore_r${round}/ that import build.py/gore.py; add hits with gore.add_hit). Judge each type against how that injury really looks: bullet entry (small round hole, abrasion collar), exit (ragged everted stellate tear, bone fragments), slash (gaping clean-edged gash, V walls), blunt (swelling, bruise colours, stellate split, depressed fracture, knocked-out teeth), burn (char, blisters, peeling). ${USER_FEEDBACK}
Render every wound type close-up from 3 angles (straight on, 45 degrees, grazing/profile) plus a cross-section; any wound that reads as a flat sticker at any angle is a HIGH severity issue. Also: do the layers line up and show skin/fat/muscle/bone rings with thickness, or do wounds read as dents / show void; is the brain visible through deep wounds; does blood obey gravity and hug the surface; drip shapes and beads; fresh vs dried blood colours (blood_age); does it look like a real prop or like CG blobs?
${prior}
Severity: high = injury clearly unconvincing/broken or a contract wound feature missing; medium = noticeable quality gap; low = polish. Concrete fixes (file/node group/what to change). Verdict 'ship' only if every wound type is convincing.`,
  },
  {
    key: 'system',
    prompt: (round, prior) => `${PRE}

YOU ARE A CRITIC (round ${round}); do not edit project files (scratch scripts only, in ${SCRATCH}/critic_system_r${round}/). Role: technical artist / tools engineer judging the SYSTEM and CODE. Actually run things, don't just read code:
- \`cd ${DIR} && python3 build.py --no-render\` from clean; time it; check console for errors/warnings.
- Load gore_head.blend (bpy.ops.wm.open_mainfile) and check: collections, objects, GH_Gore modifiers on every layer, drivers valid (no errors, fcurve.driver.is_valid), keyframes, frame range, file size, and that it evaluates correctly after reload (no Python needed at load time: the system must work in a plain Blender without these scripts).
- add_hit for every kind at several surface points; move/rotate/scale an empty and confirm the evaluated skin changes; damage=0 -> identical to no hits; bleed=0 -> no drips; drip_time 0 vs 1 changes drips; blood_age/wetness change material values; extreme values (size 3, depth 1, overlapping hits, hit on the ear, hit at the back of neck, 20 hits) don't crash or explode; evaluation time with 20 hits.
- Contract compliance (names, attributes, controls), \`blender -b --python build.py -- --no-render\` compatibility of argv handling (simulate sys.argv), relative paths only, code clarity/readability, README accuracy if present.
${prior}
Severity: high = crash/error, broken feature, contract violation; medium = fragile/slow/confusing; low = polish. Concrete fixes. Verdict 'ship' only if everything works.`,
  },
]

const history = []
for (let round = 1; round <= 3; round++) {
  const prior = history.length
    ? `Previous rounds (check that these were actually fixed; re-report any that were not):\n${JSON.stringify(history, null, 1)}`
    : ''
  const results = await parallel(CRITICS.map(c => () =>
    agent(c.prompt(round, prior), { label: `critic:${c.key}:r${round}`, phase: 'Review', schema: CRITIC_SCHEMA })
      .then(r => (r ? { critic: c.key, ...r } : null))))
  const critiques = results.filter(Boolean)
  const issues = critiques.flatMap(c => c.issues.map(i => ({ critic: c.critic, ...i })))
  const highs = issues.filter(i => i.severity === 'high').length
  const mediums = issues.filter(i => i.severity === 'medium').length
  log(`Round ${round}: ${highs} high, ${mediums} medium, ${issues.length - highs - mediums} low; verdicts ${critiques.map(c => c.critic + '=' + c.verdict).join(', ')}`)
  if (critiques.length === CRITICS.length && critiques.every(c => c.verdict === 'ship') && highs === 0) {
    history.push({ round, verdicts: critiques.map(c => c.verdict), issues, fixed: 'no fix needed' })
    break
  }
  const FIX = `${PRE}

YOUR TASK: fix round ${round}. You may edit any project file in ${DIR} (anatomy.py, materials.py, gore.py, build.py, gh_common.py, CONTRACT.md).
${USER_FEEDBACK}
Treat the sticker problem as the #1 issue until the critics confirm every wound is real cut geometry from every angle. Critics reported these issues:
${JSON.stringify(issues, null, 1)}
${history.length ? 'Earlier rounds:\n' + JSON.stringify(history.map(h => ({ round: h.round, fixed: h.fixed })), null, 1) : ''}
Fix ALL high issues and as many medium issues as you can (low ones when cheap). Prioritise what the user will see first: the head's looks and the wounds. After fixing, run the full \`python3 build.py\` (renders included) and LOOK at every render in ${DIR}/renders/; make sure nothing regressed and the module self-tests still pass (\`python3 gore.py\` verify_gore, etc.). In your summary, list each issue and what you did (or why not).`
  const fix = await agent(FIX, { label: `fix:r${round}`, phase: 'Fix', schema: BUILD_SCHEMA })
  history.push({
    round,
    verdicts: critiques.map(c => `${c.critic}=${c.verdict}`),
    issues: issues.map(i => `[${i.severity}] ${i.critic}/${i.area}: ${i.problem}`),
    fixed: fix ? fix.summary : 'fix agent failed',
    still_open: fix ? fix.known_issues : [],
  })
}

phase('Finalize')
const FINAL = `${PRE}

YOUR TASK: finalize. You may edit any project file in ${DIR}.
${USER_FEEDBACK}
Before finishing, re-render every wound type close-up at 3 angles and confirm none reads as a sticker; fix it if any does. Review history:
${JSON.stringify(history, null, 1)}
1. Delete stale/throwaway files from ${DIR} and ${DIR}/renders (keep only renders the README uses plus module look-dev renders that are current). Remove __pycache__.
2. Run \`cd ${DIR} && python3 build.py\` from clean (full renders); confirm no errors; LOOK at every render. If something is visibly broken, fix it and re-run.
3. Also render ${DIR}/renders/hero.png: 1024x1024, ~96 samples, three-quarter view of the 'carnage' preset — the showcase image. And ${DIR}/renders/stages.png: one image with 4 panels (intact, blunt, gunshot, carnage) side by side (compose with bpy image pixels / numpy, no external tools).
4. Write ${DIR}/README.md: what it is; that everything is procedural (no downloaded assets); how to open gore_head.blend in Blender 5.1 and use it (drag hit empties, which collection = which wound, what scale x/y/z and rotation mean, GH_Controls sliders table with meanings, the animation, how to add a new wound by duplicating an empty into another collection); how to rebuild (python3 build.py / blender -b --python build.py -- options); presets; file overview; performance notes; embed hero.png, stages.png, cutaway.png and closeups with relative paths. Keep it accurate to the code.
5. Ensure .gitignore in ${DIR} ignores __pycache__ and *.blend1.
Report: final file list with sizes, render list, build/eval/render timings, remaining known limitations (be honest).`
const fin = await agent(FINAL, { label: 'finalize', phase: 'Finalize', schema: BUILD_SCHEMA })

return { builds: { anatomy: anat, gore: gore, materials: mats }, integrate: integ, history, final: fin }
