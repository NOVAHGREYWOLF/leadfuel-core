# Handoff 001: SURFACE · one-interface part · 21

Session `local_7fb3d5d0-56cb-4349-953b-1e62e440426b` (Opus). Nested under part 20, which this desk archived. Group `one-interface`. There is no router: the owner talks to this desk. Private material: `F:\Claude Sessions\handoff\surface-one-interface-21\material.md`.

## Done (verified by this desk)
- Part 20 archived through its gate. Its handoffs were on origin (44ed164), both hub worktrees were clean and pushed, and no owner decision was pending.
- Hub #1131 (step 4, the chat steers the screen) merged 2026-11-20 07:36 UTC as `0a763d29`.
  - Inside the `ci-novahub` hold.
  - `tests`/`pytest` succeeded on head a802c4e6, run 44690421433: ran 15809 == collected 15809.
  - Main was unmoved before the squash.
  - Its worktree is removed.
- Briefs, all delivered, none confirmed read:
  - NODE installer part 20: the SHA, plus steps 7 and 8.
  - DOORS part 31: a ruling on the approval queue.
  - ROUTER #126: q9518, that merges go ahead and only the deploy is blocked.
  - ARMS step 5: no live desk, so it is a proposal card `ARMS · one-interface part · 2` for the owner.
- Step 6 (the Plain skin) built as branch `surface/plain-skin`, pushed at `0273005d`. There is no PR yet. On `0a763d29`:
  - `f4365146`, task B, the frame;
  - `55222831`, task A, `skin.set` is the look and `register.set` the words: re-run by me on an export, 711 passed;
  - `0273005d`, task C, `plain.js`, the events, the skin-keeping links, the game-key guard and the header wrap. A sub-agent reported gates 14 of 16 green with 2 skipped, 2,655 passed in 46 files, no pin changed, and its mutation checks caught. Not re-run by me.

## State (re-read before acting)
- Hub main has moved to `680f1e89` (#1133). Merge main into `surface/plain-skin` first.
- The `ci-novahub` lock was held by NODE · MERGE-TRAIN at 2026-11-21 23:26 UTC. Opening the PR fires CI, so open it inside your own hold.
- Worktrees in `F:\Leadfuel\repos\novahub\.claude\worktrees\`:
  - `surface-plain-skin` (step 6);
  - `surface-plain-frame` (task B's old branch, pushed at 7d75d5aa, now folded into step 6). Remove it after step 6 merges.

## Next
1. Have an independent sub-agent review the step 6 diff (`0a763d29..0273005d`); it must not be the one that wrote it.
2. Take a browser look at `?skin=plain` and `?skin=game` through the local preview (`preview.py` in the material folder). Check the switch in place, Undo, and the header at 1440px.
3. Take `ci-novahub`. Merge main in, run the static gates and the touched tests, push, open the PR, wait for `tests`/`pytest` success on that exact head, confirm main is unmoved, squash with `--match-head-commit`, then release.
4. Send the step 6 SHA to the NODE installer: part 20 (`local_5d6dd110`) or its successor part 21.
5. Send the owner a short report on what was verified and what was taken on trust. Read replies from DOORS and ARMS, and NODE's step 7/8 answers, if any came.

## Owed
- Railway redeploy (q9518 = B): when the owner picks a plan, redeploy the hub. Production stays on the 11-10 build until then.
- The ARMS step 5 card waits for the owner's click.
