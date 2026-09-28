# LOCAL HANDOFF — continue this project on the user's PC without losing 1:1 realism

Written 2026-09-28 ~01:40 UTC at the end of the cloud session. Read this AFTER `CLAUDE.md` (which Claude Code loads
automatically) and BEFORE touching anything. The user's standing order: **"ensure 1:1 realism on ur efforts. allways"**
— every change is judged against real anatomy and the user's real reference photos; nothing is done without renders
that prove it. The user will be angry at anything lazy, placeholder-looking, glossy-plastic, sticker-like or half-done.

---


## 0. Task list (the cloud session's task tracker, with HONEST status)

| # | Task | Real status |
|---|---|---|
| 1 | Head build + review rounds 1-3 + final pass | done → continued as #8 |
| 2 | Research round 1 (wounds, bleeding, death/eyes, anatomy, Godot tech) | done, fact-checked (`docs/research/`, REALISM_BIBLE, FULL_BODY_PLAN) |
| 3 | Research round 2 (neuro deficits, reactions, falls, agonal movement, severe trauma, sound) | done, fact-checked (`docs/research2/`, BEHAVIOUR_BIBLE; sound = reference only) |
| 4 | Build full body B0-B8 (skin+shorts, skeleton, organs, cord, vessels, rig, export) | done → review/fix continues as #9 |
| 5 | Build the Godot 4.5 game (gore, physiology, vessels, neuro, eyes, reactions, ragdoll, tools, UI) — NO AUDIO | **NOT STARTED** — only when the user says go (`orchestration/05_body_godot.js`) |
| 6 | Final QA, Windows/Linux exports, README, screenshots, push | **NOT STARTED** (exports need the user's OK to download Godot export templates) |
| 7 | Strip audio sections from FULL_BODY_PLAN.md and BEHAVIOUR_BIBLE.md | done |
| 8 | Finish head review/fix rounds (anti-sticker first) | **IN PROGRESS** — head fix pass 2: blood done, wounds mostly done, then face, then strict critics |
| 9 | Build the full-body character in Blender (no game yet) | **IN PROGRESS** — body fix round 2, then review round 3 |
| 10 | Remove audio from plan and bibles | done |
| 11 | Update CLAUDE.md status when builds finish, commit and push | in progress (updated at hand-off; update again when #8/#9 finish) |
| 12 | Fix the head's face per FACE_FEEDBACK.md | pending — part 3 of head fix pass 2 (deep-set eyes dropped by the user) |

## 0b. The whole conversation is saved

`gore-game/docs/orchestration/SESSION_LOG.md` = every user message verbatim and every reply, 2026-09-25 → 09-28
(regenerate on the cloud with `gore-game/tools/dump_session_log.py`). All research is in the bibles and
`docs/research/`, `docs/research2/` (fact-checked source files); user feedback verdicts are in REFERENCE_NOTES
§5.9-5.22 and CLAUDE.md §7; the agents' step logs are in `orchestration/agent_memory/`; the latest reviewer/fixer
reports verbatim are in `orchestration/LATEST_REPORTS.md`; every workflow script (all prompts) is in `orchestration/`.
When unsure what the user wanted, search SESSION_LOG.md for their exact words.

## 1. First-hour checklist (do these in order)

1. **Stop the cloud first, then pull.** The cloud fixers (head wounds fixer, body fix round 2) were still running after
   this handoff was written and may have pushed later commits. Make sure the cloud session is stopped, then pull the
   branch `claude/blender-cloud-l8ujco` (all code, docs, renders, game assets, agent memory), then read
   `orchestration/agent_memory/live/*.md` for their newest steps. Never run a local fixer while a cloud one still edits
   the same files — two copies overwrite each other.
2. **Reference photos:** copy the user's forensic reference photos into `refs/` at the repo root (git-ignored on
   purpose; never commit them). Expected files: `1.png 2.png 3.webp 4.webp 5.webp 6.webp 7.png 8.png
   12_our_render_wall_stripes.png 13_blast_face_mouth_explosive.png 14_body_position_pool.png
   15_repeated_blunt_face_a.png 16_repeated_blunt_face_b.webp 17_neck_transection_pool.png
   18_chop_head_torn_tissue.webp 19_skull_cut_brain_exposed.webp 20_gsw_pathology_grid.webp
   21_face_gsw_seated_pool.png 25_our_blood_disconnected.png 26_our_blood_disconnected_zoom.png
   gsw_pathology_sheet.webp face_ref_male.webp face_ref_sculpt.png` (12, 25, 26 are OUR bad renders = what to avoid).
   If the user does not have them locally, ask them to copy them — reviews without the refs are invalid.
   Upload → name mapping (the user's chat uploads): 1-8 → `1.png`…`8.png`; 9 → `face_ref_sculpt.png`; 10 →
   `face_ref_male.webp`; 11 → `gsw_pathology_sheet.webp`; 13-16 → `13_…16_…`; 17-21 → `17_…21_…`. OUR annotated bad
   renders (12, 22-31, 25, 26 — what to avoid) ARE committed in `gore-game/docs/feedback_renders/`; copy them into
   `refs/` too.
3. **Toolchain check (Blender 5.1 was never run here; only the bpy 5.0.1 module):**
   - `cd blender/gore_head && blender -b --python build.py -- --no-render` → must print all verify checks passed.
   - `blender -b --python gore.py -- --no-render` (verify_gore) and `blender -b --python anatomy.py` (30 overlap checks).
   - Fix any 5.0→5.1 API differences before anything else. Use the GPU for Cycles if available (much faster than
     the cloud's 4-core CPU where one 640 px preset took 2–5 min and a full head build with renders ~1.5–2 h).
4. **Body .blend:** `blender/gore_body/gore_body.blend` (~105 MB, already zstd-compressed, over GitHub's 100 MB file
   limit) is NOT in git. Regenerate it: `cd blender/gore_body && blender -b --python build.py -- --stage all`
   (check `build.py --help`; the fixers used `--stage all`, also partial stages like `--stage skin head skeleton`).
   The Godot-facing export in `gore-game/assets/generated/` IS in git (last complete set: commit 950fb5b, fix round 2
   build). The user said: **do not compress/split/downscale the body files** without asking.
5. **Paths:** docs and orchestration scripts contain cloud paths. Map them:
   | cloud path | local |
   |---|---|
   | `/home/user/YAYSTO/` | your repo root |
   | `/tmp/claude-0/-home-user-YAYSTO/<session>/scratchpad/` | any local scratch folder (NOT in git; old scratch renders are gone) |
   | `python3 script.py` (bpy module) | `blender -b --python script.py --` |
   The build scripts themselves use relative paths (`gh_common.HERE`); the dev_tools and workflow prompts do not.

## 2. Where things stand (honest)

| Track | State | Evidence |
|---|---|---|
| Research + bibles | done, fact-checked (numbers tagged V/C/K/E/G) | `docs/REALISM_BIBLE.md`, `BEHAVIOUR_BIBLE.md`, `FULL_BODY_PLAN.md` |
| Head (Blender) | built; review rounds 1–3 + final pass done; **fix pass 2 in progress**: blood part DONE, wounds part ~most done, face part + strict review NOT done | `blender/gore_head/renders/`, `orchestration/LATEST_REPORTS.md` |
| Body (Blender) | built B0–B8, exported to Godot; fix round 1 done; review round 2 done (all 3 critics "needs_work"); **fix round 2 in progress** | `blender/gore_body/`, `gore-game/assets/generated/`, `LATEST_REPORTS.md` |
| Godot game | **NOT started** (user: "dont start making the actual game yet") | — |

Last estimate given to the user (09-28 01:04): overall ~35-45 % (research ~100 %, head ~70 %, body ~60 %, Godot 0 %).
First playable (room, shoot, blood from wounds, bleed, ragdoll fall, basic brain/spine) ≈ 1-3 days of agent work once
the user says start; the full polished 1:1 version and the 60 fps gate need the user's GPU and many visual fix rounds.

**KEEP (user-approved or proven; do not regress):** the intact head's tooth shapes ("U DID TEETH GREAT"; the brown
speckle on the body and the cube/candy teeth in the blast are still bugs); the nose base and curve; loose teeth and a
broken jaw in the mouth blast; the eye cutaway section; the branching scalp-split pour; blood seeded on the rim with
zero gap (`proof_blood.py`).

What got clearly better during the cloud session (keep it, don't regress it):
- Blood comes OUT of the wound: every run is seeded on the wound's own rim, never wider than the rim part it spills
  over; `blender/gore_head/proof_blood.py` renders every bleeding wound at 0/5/10/20/40/60 s × straight/45°/graze and
  counts skin pixels between rim and blood (0 = pass). Last exit proof 17/18 then 18/18 after a fix.
- Bleeding is wired to a named head-vessel table (temporal, occipital, facial, labial, meningeal, sinuses...).
- Branching, curving, heavier streams (scalp split, forehead entry); eye rupture, torn lid, black eye; burn reaching
  the eye; crushed face as a torn crater with bruising; neck lengthened on the body; eye texture bug fixed.

## 3. Everything still open (fix ALL of these; each is a HIGH unless marked)

Full verbatim details with concrete fixes: `gore-game/docs/orchestration/LATEST_REPORTS.md` (38 HIGH issues from the
latest reviewers + fixers' own "still open" lists) and `CLAUDE.md §7` (user feedback log). Summary:

**Head wounds / blood** (gore.py, materials.py)
- Blood look: too glossy / "red paint"/"gel"; streams still partly flat red slabs or ribbons with jagged cut-out
  edges (exit close-up); needs thin translucent films, drying darker edges, colour variation, clots, contour-following.
- Crushed preset: lower face coated in a thick glossy blood slab; nose tip not injured enough; silhouette cave-in
  modest; bone pieces paper/plaster-like; leftover yellow bits.
- Exit wound: fragments read as dotted tiles / earlier candy marbles; must be ragged/stellate with chalky bone and
  shredded extruded tissue (refs 20, gsw sheet).
- Cheek slash: still a "second mouth"; walls = gold/orange foil with stepped stripes (ref 12 artefact) — the wall
  ring extrusion + muscle fibre shader along object Z cause the banding (see LATEST_REPORTS).
- Throat cut: glossy tube, no cross-section (muscle masses, trachea/larynx rings, vessel openings, clot; refs 1/17).
- Yellow fat far too visible (REFERENCE_NOTES §5.22): face/neck fat 2–6 mm, pale cream, mostly blood-stained.
- Mouth blast: teeth = white cubes, tissue = round candy beads; gums/palate/tongue must be destroyed (§5.15, ref 13).
- Blunt: swelling/bruising at the impact spot, crushed abraded margins (refs 15/16).
- Entry: still a neat round grommet with a soft halo; must be small irregular with a 1.6–2.4 mm abrasion collar.
- Multi-hit face (e.g. 4 entries): by ~48 s blood must cover much of the face and pour off the chin (the 4-shot clip had
  one straight line per run and far too little blood).
- Cutaway: brain cut centre = flat white disc (needs grey ribbon + white matter + folds + blood in sulci).
- Burn: too glossy; odd pale blob beside the eye.
- Face (FACE_FEEDBACK.md): ears clay-like, cheekbones, head length, nostrils, eyelid thickness/crease/lash line,
  mannequin skin. (Deeper-set eyes NO LONGER required.)

**Body** (blender/gore_body)
- Neck base ledge + seam line of dots at the head/body join; neck still "mannequin socket" from side/back (user HIGH;
  acceptance = head on body vs standalone head from the same cameras, face/jaw/under-ear must match).
- Eyes exported INSIDE-OUT (normals inward, negative volume) and eye/lid bone pivots 2.5 mm off the globe centre.
- Lash/brow cards: flat fan pasted on the lid.
- Shorts tear/poke through at hip flexion (FB-2 FAIL); lower-back belt line; double nipples (areola paint 35 mm off).
- Skin in game textures = mannequin/vinyl; stray dark dots.
- Teeth not seated in bone; mandible a plank; mid-face/skull base one solid slab (no sinuses/ear canal).
- Vessel tubes inside bone / through skin; heart = smooth blob with pipes (pericardium grey-white block); brain colour.
- Build not deterministic (UV packing).

## 4. How to continue (recommended order)

1. Toolchain check (§1.3). 2. Regenerate body .blend (§1.4).
3. **Read the agent memory first:** `gore-game/docs/orchestration/agent_memory/INDEX.md` (newest last) and
   `agent_memory/live/*.md` (running notes the last fixers wrote: what they changed, what the renders showed, what
   was next). Re-run `python3 gore-game/tools/dump_agent_memory.py <transcripts dir>` only on the cloud; locally the
   dumped files are what you have.
4. **Head:** finish fix pass 2 = wounds items above → face (FACE_FEEDBACK.md) → full `build.py` → `proof_blood.py`
   → then a STRICT review: independent critics that open every file in `refs/`, render every wound from straight /
   45° / grazing + a cross-section, fill in REFERENCE_NOTES §5.18 section H PASS/FAIL, and fail anything cleaner,
   drier, glossier, more uniform or less bloody than the refs → fix → re-review until no HIGH remains.
   The exact prompts, item list (17 items + 16b) and schemas: `gore-game/docs/orchestration/06_head_fix_pass2.js`.
5. **Body:** finish fix round 2 (issues above) → full build + verify + export → review round 3 → fix.
   Prompts: `orchestration/04_body_blender.js`. Then re-export with the finished head.
6. **Only when the user says so:** start the Godot game (`orchestration/05_body_godot.js`, FULL_BODY_PLAN §6/§8).

## 5. Quality gates that must never be skipped

- Every agent that touches wounds, blood, tissue, bone, skull, brain, organs or the body opens EVERY file in `refs/`
  (list them in its report) and compares renders side by side. No refs → invalid.
- `CLAUDE.md §8` anti-sticker rule + blood-from-the-wound rule, verbatim, go to every such agent.
- `REFERENCE_NOTES.md §5.9–5.22` (user verdicts) and `§5.18` visual acceptance standard (section H table) are the
  pass/fail bar. §5.19: blood out of the hole itself, zero gap; §5.21: every stream traces up into an overflowing
  low point of a wound rim; §5.20: nose/eye injury rules; §5.22: fat thin and pale.
- Nothing is "done" without renders you looked at. Show the user renders often, with honest flaws.
- No downloads of assets/add-ons/plugins; tools only from official sources and only after telling the user.
- No audio. No stickers. Never compress/split/downscale body files without asking.
- Keep writing agent memory: every long-running fixer keeps `agent_memory/live/<task>.md` updated after every step.
- Commit and push progress regularly on the branch.
