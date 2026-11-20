# Handoff 001: SURFACE · one-interface part · 20

Session `local_1b5834ec-d7a5-43cd-b408-3d364a0e729f` (Opus), nested under part 19, which is archived. Group `one-interface`. There is no router: the owner talks to this desk. Private material: `F:\Claude Sessions\handoff\surface-one-interface-20\material.md`.

## Done (verified by this desk)
- Part 19 archived through its gate; its preview server is stopped.
- Hub PR #1131 reviewed by an independent sub-agent: MERGE AFTER NITS, all nine safety rules hold, 359 passed.
- Hub CI was down: VM 102 `ci-runners` had been stopped since overlord's reboot. I started it and set onboot 1, both on the owner's words. Runners online 06:39 UTC.
- The owner's cut-off message was "the left pane doesn't scroll on NovahOS", and he said it is NODE's. Handed to NODE installer (`local_5d6dd110`): delivered.
- Off railway part 1's ASK answered to part 2 (`local_e0453c29`): build in-desk with sub-agents. Queued, not confirmed read.

## State (re-read before acting)
- **Sub-agents running at writing.** Each commits in its worktree and does not push.
  - Review fixes: `F:\Leadfuel\repos\novahub\.claude\worktrees\surface-chat-steers` (branch `surface/command-chat-steers`, pushed head `c983aefd`).
  - Step 6 task B, the frame: `...\worktrees\surface-plain-frame` (branch `surface/plain-skin-frame` from `c983aefd`).
  - Check `git log` there. A commit past `c983aefd` is their work. Re-run its tests before pushing.
- CI run 44685243860 on the OLD head `c983aefd` was in progress. Merge only on the fixed head's own green.
- The `ci-novahub` lock is free and not held. Its queue has 5 stale tickets (`lockq.py`).

## Next
1. Push the #1131 fixes, mark the PR ready, take `ci-novahub`, merge on `tests`/`pytest` success on that exact head, squash with `--match-head-commit`, release, then remove the worktree.
2. Send the merged SHA to NODE installer (`local_5d6dd110`) for HUB_COMMIT.
3. Step 6: follow `step6-plan.md` (in the material's scratchpad). Task A (skin.set game|plain, register.set) gets its own worktree from the fixed step 4 head; merge A and B; then task C (plain.js); then review, PR, CI and merge.
4. Steps 5, 7, 8 and the approval queue are other desks' (ARMS, NODE, DOORS). Brief them.

## Owed
- None from the owner.
