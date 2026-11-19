# Handoff 001: SURFACE · one-interface part · 19

Session `local_b4236aaf-d394-4eff-ae35-4601fe92ba4e` (Opus). It was nested under part 18, which it archived, and is in group `one-interface`. There is no router: the owner talks to this desk. Private material: `F:\Claude Sessions\handoff\surface-one-interface-19\material.md`.

## Done (verified by this desk)
- Hub #1128 merged as main `e2797b9f`. It fixes the parts cache, which was keyed on mtime only: `command_focus`/`command_screen` now key on `(st_mtime_ns, st_size, st_ino)`. This was the estate-wide `test_command_rungs` flake. The test itself was not touched.
- Hub #1122 (globe) merged as main `635f2d4a`.
- Hub #1129 (step 2: screen moves as named actions with undo, `static/command/actions.js`) merged as main `3322f8b3`. CI ran 15,658 of 15,658 tests.
- Hub #1130 (step 3: the "What the AI can do here" sheet, `cando.js` and `GET /api/command/can-do`) merged as main `f2a58543`. CI ran 15,720 of 15,720 tests.
- Board D redrawn inside the NovahOS window and published on Design canvas `RTbymAgoSTKozb7h5kHbPp`.
- Part 18 archived through the gate and read back.

## State (re-read before acting)
- No PR of this desk is open. The `ci-novahub` lock was released at 09:42 UTC, and every SURFACE worktree this desk used is removed (each was clean and pushed).
- The `.wait` queue holds 5 old tickets whose desks are not live.

## Next (owner's go: "Ok let's do it"; order relayed as 2, 3, 4, 6, one PR per slice)
1. **Step 4: the chat steers the screen.** The ask-local path (`command_ask.py`, `command_ask_local.py`) gets the screen registry (`cmdxActions`) and the hub catalogue (`/api/command/can-do`) as tools. Outward actions go through the approval queue.
   - `command_ask_local` refuses unless the model and the embedder are on loopback on the hub's own machine, with no `ANTHROPIC_API_KEY` in the process.
   - Build and test against a fake model. Real use needs NODE to place the model and the local hub on the same box.
   - NODE · home node part · 20 installer (`local_5d6dd110-1cb8-4ff1-9320-ec0a2d069c23`) was told this. The message was queued, not confirmed read.
   - An outward action is held for the owner's yes only when the caller is the goal runner (`"conductor"`) or the approval switch is on. A chat caller must be held regardless: decide how, and check with DOORS, which owns `_ACTION_CLASS`/`/api/app-action`.
2. **Step 6: the Plain skin.** A second look over the same data and actions. See board D2.
3. Steps 5 (no-screen agents over the MCP connector: check the lane owner first), 7 (inside the NovahOS window, served by the local hub: NODE) and 8 (first run as quests: NODE installer).

## Follow-ups found (not done)
- `gazetteer.py` lines 77 and 122: the same mtime-only `lru_cache` bug as #1128.
- `character.js`: Esc with the character sheet open opens Start over it, because `shell.js` takes Esc first at window capture.
- `tests/shell_harness.js` treats `stopPropagation` like `stopImmediatePropagation`. That can hide listener-order bugs; other harnesses are not checked.
- For DOORS: `/api/command/can-do` exposes the catalogue (keys and descriptions, no data) to home-node sessions.

## Owed (owner decides)
- q9518: the Railway plan. A merge reaches production only while Railway deploys main.
- NODE · off railway part · 1's cards q9527–q9531, especially q9527: there is no home copy of the 5.75 GB hub DB.
- Which launch "hook it all up" follows. Assumed: the NovahOS setup guide.
