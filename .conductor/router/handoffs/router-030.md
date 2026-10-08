# Router handoff #030 -> #031 (2026-10-08 ~01:05Z UTC, at the 300k guard)

ROUTER #30 is local_7ae54716-9d21-4b45-92ca-5ba596f828ab ("ROUTER #30 · one-interface", ROUTER group). Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v311+: keys log_30*, agent_reports_30*, agents_30*, owed_30*, pr796 supersede this note. Router desk LzmP6QcxmYh9TdvMMjS883. Conductor desk MKAx49RAskZ3cV7f2EkDMF; live conductor 021 local_1ff6c57b.

## Done by #30
Claimed v304. Archived 7/7, #28, #29 through the gate. Hub main f02e3382 (#795, #792 landed). DOORS reviews done: COMMAND_HOME (blocked by B1-B4) and #797 layers (blocked by B1, B2); files in F:/Claude Sessions/handoff/one-interface-doors-review-command-home.md and ...-s4-layers.md.

## Running (they die if #30 is archived: #30 STAYS OPEN until all report; reports reach #30 only, copy to the board)
- a1831740f1d4a204e INTELLIGENCE HUB738-PLACES-FIX 2/2: lands #738 itself in the ci-novahub hold; holds the heavy lock (pid 57128) since 23:42Z.
- a4b1b5f692276e13c SURFACE COMMAND-HOME-FIXES: draft PR #796. It does NOT land; read the diff myself, then SendMessage it by agent id to land.
- a1bc2a0aededd7244 SURFACE S4 n=3: fixing DOORS B1/B2 on draft PR #797 (head was 073464e1).
- abde7ba76f744e714 NODE GROUP-BY-PROJECT 2/2, paused on card q347: branch way/group-by-project-2 da1488a. A: merge to way/plugin, 0.1.9, install, verify installed_plugins.json. B: discard branch and worktree. Then tell conductor 021 (pick WAY-TITLE-REWORD-B).

## Next
1. On each report: verify with gh and ls-remote, copy to agent_reports_30*.
2. After #796 lands: Router desk card for the COMMAND_HOME production flip (Railway env, owner-only).
3. #797: short DOORS re-look at B1/B2, then NODE MERGE-TRAIN 8/8 or the owning agent in the hold; CI pytest on the exact tree decides.
4. After #738 lands: open SUITE PLACES-GATE-LAND.

## Owed
Cards open: q347, q208, q294. Sends since owner typed: 2 of 10. NOT queued, do not start: SUITE TEST-ISOLATION, WORLD-FLAG-ON-PREREQS, STUDIO-GENERATE-PREREQS, REACH-SEND-EMAIL-DESIGN, COUNSEL PHOTO-STORE-WORDING.

## Gotchas
S4 n=1 spent its whole budget planning: say BUILD in the brief. After a cd the shell cwd flips into worktrees: use git -C. Older routers #11 #13 #14 #18 #21 #22 #24 #25 #26 are still open: gate each, one at a time.
