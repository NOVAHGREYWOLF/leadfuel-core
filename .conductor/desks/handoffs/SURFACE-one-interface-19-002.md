# Handoff 002: SURFACE · one-interface part · 19

Session `local_b4236aaf-d394-4eff-ae35-4601fe92ba4e` (Opus), group `one-interface`. There is no router: the owner talks to this desk. This note replaces 001's "State" and "Next"; 001's "Done" still holds. Private material: `F:\Claude Sessions\handoff\surface-one-interface-19\material.md`.

## Done since 001 (verified by this desk)
- Step 4 is built: hub PR #1131 (draft), branch `surface/command-chat-steers`, head `c983aefd`, on main `f2a58543`. It is pushed.
  - The chat steers the screen: `! steer` mode, `POST /api/command/steer`, and `command_steer.py`.
  - It calls the local model only, under `ask.local`. The server runs nothing; the browser runs the validated screen steps through `cmdx:act`. Hub actions are only shown, with outward ones marked held.
  - Re-run by this desk: `SKIP_TESTS=1 sh scripts/gates.sh` printed "All 14 of 16 gates green, 2 skipped". The steer, console, ask_local, local_authority and levels_write_calls test files: 376 passed.
- The owner asked for NovahOS and the screen to be "intertwined". NODE · home node part · 20 installer (`local_5d6dd110-1cb8-4ff1-9320-ec0a2d069c23`) was briefed on five points:
  - HUB_COMMIT;
  - the ask-local settings for the local hub;
  - how step 7 puts the screen in the NovahOS window (top-level or framed; a frame needs DOORS);
  - a bridge so the NovahOS assistant can call `cmdx:act`;
  - which of these are owner steps.
  The message was queued, not confirmed read.

## State (re-read before acting)
- PR #1131 is a draft and its CI has not been run under the hold. The `ci-novahub` lock is not held by this desk.
- Worktree `F:\Leadfuel\repos\novahub\.claude\worktrees\surface-chat-steers` is clean and pushed. Remove it after the merge.
- A local preview of main runs from launch config `hub-command-preview` (port 5074) in leadfuel-core's untracked `.claude/launch.json`. Stop it when done.

## Next
1. **Review #1131.** Use a sub-agent that did not write it, with the code, not a conclusion. Focus: the validation in `command_steer.py`; that no path runs or queues an action; the estate rule; the `fetch(` pin change in `tests/test_command_console.py` (1 to 2, same rules for `STEER_URL`).
2. **Merge #1131.** Mark it ready, then follow the CI hold: take `ci-novahub`, merge main in, wait for CI `tests`/`pytest` success on that exact head with "OK: ran N == collected N", check main is unmoved, `gh pr merge --squash --match-head-commit`, release the lock.
3. **Tell NODE.** Send the installer desk the merged main SHA for HUB_COMMIT, and read its reply on "intertwined".
4. **Step 6: the Plain skin** (board D2 on the canvas `RTbymAgoSTKozb7h5kHbPp`).
5. **Later:** putting held outward actions in the approval queue needs DOORS to agree (`_enqueue_pending_action`, `notify=False`).

## Follow-ups (not done)
- 001's list still stands: `gazetteer.py` mtime cache, `character.js` Esc, `tests/shell_harness.js` stopPropagation.
- Steer is not tested with a real model; nor `card.open made_of` right after a jump; nor `skin.set` inside a run.

## Owed (owner decides)
- q9518 (the Railway plan); q9527-q9531 (off Railway; there is no home copy of the hub DB).
- The owner's message "when i go through novahos it seems line" was cut off. Ask what he saw.
