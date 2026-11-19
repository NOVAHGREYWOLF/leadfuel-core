# Handoff 001: SURFACE · one-interface part · 17

Session `local_1cd4574b-3128-48fa-8e25-fb1162e2ccd8` (Opus), nested under part 15 (`local_1146d1f7-08f6-4eb2-b990-3844c4347b15`), group one-interface. No router: the owner talks to this desk. Private build material: `F:\Claude Sessions\handoff\surface-one-interface-17\material.md` (the mockup kit, asset ids, preview recipe).

## Done
- **Mockups:** the Design canvas `RTbymAgoSTKozb7h5kHbPp` has four boards: 0 first run as the game, A window first, B game first, C phone. All published and opened for the owner. His reply: he likes all four.
- **Globe build, looked at locally:** the NASA Earth draws under the globe's lines at 1440x900 once the camera lands, with its credit. Screenshot in the material folder.

## Owner's new ask (his words, condensed; 2026-11-19 ~04:25 UTC)
- One more mockup: **game first**, plus a chat box that answers questions about anything on the screen **and navigates the screen**.
- The whole thing is written so AI agents can do everything, on screen or with no screen, even by just talking to them.
- A regular Claude-like GUI is a different skin, maybe for a different type of user.
- The "hook it all up" first run should be similar to "the launch that we are developing" (which launch is not confirmed).

## State
- Hub branch `surface/command-globe-imagery` (worktree `.claude/worktrees/surface-globe-imagery` in novahub), commits `bcd1a2e1`, `741cacb5`, `1ca5c7f1`. **Not pushed, no PR.**
- Gates and targeted tests: a verifier sub-agent was still running at handoff; **treat its result as lost and re-run them.**
- Verified by me: the three commits exist locally; the Earth renders in a local preview; `6ce0df8` (part 15's handoff) is on `claude/conductor-050`. On trust: the build report's 20 tests and 7 mutants.

## Next
1. Board D on the same canvas (the new ask). Reuse the kit.
2. Globe: `SKIP_TESTS=1 sh scripts/gates.sh` plus the targeted tests, a phone-width look, then push, draft PR, `ci-novahub` hold, CI `pytest` green on the head, merge. The owner's go is given. A merge does not reach production until he picks a Railway plan (q9518).
3. Once the hub branch is pushed, archive part 15 and then part 17.

## Owed (owner decides)
- q9518: the Railway plan (he cannot pay yet). The FIRMS key; EONET and CelesTrak terms. The real "you are here" pin is INTELLIGENCE's (`world_routes`).

## Gotchas
- A screenshot taken mid-flight shows only lines: the picture loads once `lod.globe >= 0.2`.
- `rail.js:73` throws in the local preview's fake customer session. rail.js is not in this branch.
- The canvas page republishes `canvas.json` itself when opened. Read it before publishing the index.
