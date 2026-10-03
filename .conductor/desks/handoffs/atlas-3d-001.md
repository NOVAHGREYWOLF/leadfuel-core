# DESIGN · ATLAS-3D · handoff 001 (2026-10-02)

Session local_0f7bb7a2-78ca-4492-87fc-6429dccd1629 (`DESIGN · ATLAS-3D 1/1 · Atlas Live in 3D`, Opus). It handed off at the 300k context guard before writing any code. Follows design-spatial-views-003.md (Build A).

## Done
- Read both pages in full: Atlas Live (6LEvF7K9u9qnSxh68VWsfA, v4) and the 3D Flow Atlas (UCCG9zfCDWeveQMuT1MFZ5, 1,863 lines).
- Settled the design and wrote it to a private plan on the home PC: `F:\Claude Sessions\desks\handoffs\ATLAS-3D-build-plan.md`. It is not in this repo because it names hub routes and gate bypasses, and this repo is public.
- Nothing published. No code PR.

## State
- **Verified here:** the result shapes of the five connector tools, in novahub-mcp c9187a8 and hub main 324ffc3. The five hub routes behind them require the mesh service token, so a browser page cannot call them as they stand: Build B needs routes for the signed-in owner, or a proxy. The real corpus source keys came from one read-only corpus_stats call (counts only, none recorded).
- **Taken on trust:** handoffs 002 and 003 on how Atlas Live v4 behaves. v4's own connector calls have never run.
- **Found:** when the spend meter is unavailable, Atlas Live v4 shows "none held" instead of unknown. The plan fixes this.

## Update after handoff (2026-10-03, from INTELLIGENCE · ATLAS-HUB, session local_e6d728e5)
- **Peer report, NOT verified here:** Router desk card q177 ("where does the atlas live?") was answered A at 2026-10-03T00:27:13Z: the atlas lives in the hub as the MAP view, and Atlas Live stays as a debugging mirror. On that basis that desk stopped Build B and asked ROUTER #13 to stand it down.
- **Verified here:** hub PRs #730 (`/goal/atlas`, three.js vendored) and #736 (`/goal/atlas/live`, live per-line counts) both exist and are **OPEN, not merged**.
- **Peer says:** the hub CSP is `script-src 'self'`, so CDN three.js will not load there. #736's feed is keyed `"from>to": {count, state, unit, reader, note}`. That is the shape to target if the hub adapter stays.
- **So, before building:** ask ROUTER #13 whether Build A still stands as briefed, and whether its scope shrinks now that the hub owns the MAP view. Do not assume either answer.

## Next
The successor first gets ROUTER #13's answer (above). If Build A stands, it runs `Artifact read` on both pages (every line of the saved Flow Atlas file) and builds from the plan. It checks the page once locally at desktop and phone width, with the hub adapter fed stub JSON. It then publishes to UCCG9zfCDWeveQMuT1MFZ5 with the plan's mcp declaration and writes atlas-3d-002.md.

## Owed
- Build B (INTELLIGENCE, task_9e9c7a2d) depends on this adapter. The hub stub switches on when the page defines `window.ATLAS_HUB`.
- No way-plugin banner was visible when this session started. The context guard did fire.

## Gotchas
- `git show <rev>:<path>` in Git Bash needs `MSYS_NO_PATHCONV=1`.
- The Artifact read of the Flow Atlas saves a file. A republish counts as viewed only once every line has been Read.
