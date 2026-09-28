# Orchestration scripts (exact prompts used in the cloud session)

These are the Claude Code Workflow scripts that built and reviewed this project. They contain every prompt, JSON schema
and control-flow decision given to the agents, verbatim. Paths inside them are the cloud container's
(`/home/user/YAYSTO/...`, `/opt/godot/...`, `/tmp/claude-0/.../scratchpad`); change them to your local paths before
re-running.

| File | What it did | State |
|---|---|---|
| `01_head_build_and_review.js` | Head: parallel anatomy/gore/materials builders → integrator → 3 critics → fixer (×3) → finalizer. Includes the verbatim anti-sticker USER_FEEDBACK block. | Build + integrate done; review/fix/final NOT run |
| `02_research_round1.js` | 6 research topics → independent fact-checkers → REALISM_BIBLE.md → FULL_BODY_PLAN.md | Done |
| `03_research_round2.js` | 6 behaviour topics → fact-checkers → BEHAVIOUR_BIBLE.md | Done |
| `04_body_blender.js` | Full body in Blender (B0 → B1/B3/B2/B4/B5/B8 → B7 → B6 → critics/fixers) | Launched then stopped; nothing produced |
| `05_body_godot.js` | Godot game (audio-strip prep → G0/G1 → G2/G5 → G3/G6 → G4/G7 → integrate → 5 critics/fixers) | Launched then stopped; nothing produced |

`AGENT_REPORTS.md` has every agent's final report (verbatim). `journals/` has the raw workflow journals.
