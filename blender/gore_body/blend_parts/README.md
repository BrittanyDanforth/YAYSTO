# gore_body.blend in 3 pieces (byte-exact, nothing changed)

GitHub refuses files over 100 MB, so the 104.7 MB `gore_body.blend` (cloud build, saved 2026-09-27 16:27 UTC) is stored
here cut into 3 raw pieces of ~35 MB. Nothing was compressed, re-saved or altered: joining the pieces gives the
original file bit for bit.

Join (run inside this folder):

- Windows (Command Prompt): `copy /b gore_body.blend.part0 + gore_body.blend.part1 + gore_body.blend.part2 ..\gore_body.blend`
- Linux/macOS: `cat gore_body.blend.part0 gore_body.blend.part1 gore_body.blend.part2 > ../gore_body.blend`

Check it (must match exactly):

- Windows: `certutil -hashfile ..\gore_body.blend SHA256`
- Linux/macOS: `sha256sum ../gore_body.blend`
- Expected SHA-256 of the joined file: `6cc02652ef0503f2b93987bb24ba461ff45a842aab6f75e23f0cf48b2dddbf03`
- Per-piece hashes: `parts.sha256`

Note: this copy may predate the last fix-round-2 script edits. The newest version can always be rebuilt with
`blender -b --python blender/gore_body/build.py -- --stage all`.
