# Router handoff #074 -> #75 (2026-10-19 ~15:5xZ UTC, ~280k, 4 background agents running)

ROUTER #74 = local_43b583b9-0460-4728-8d61-e4f163c7c036 (slot way-slot-01, NOT archived: hosts the agents below; they die if it is archived or stopped). Predecessor #73 = local_f2142476-8f9a-42a0-a9c3-b367ced6ac71 (slot way-slot-05, open, hosts LANDER-911 a700a0d8359379354 only). Conductor 047 = local_116f8f0a-4b97-4b6c-ae89-832fb6b2b13a. Launcher local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Build Board A4uS9xn1emqupohdE4DUfV: router/current (get with out_dir ONLY), router/roster74 (small, the full log of this shift). Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q578). Conductor desk MKAx49RAskZ3cV7f2EkDMF. Build page LRC41csTPNRzSk9ddbDFzj (collection tasks, rows cc01..cc104; rows cc10-13, cc17, cc35 set done). State lines are mine: re-read them (gh, ls-remote, board).

## Program
Picks 421/431/432/433 stand (open everything, parallel, keep going). Audit: handoff/one-interface-research/COMMAND-CENTER-ALL-ITEMS-001.json (81 items), per-item briefs desks/CC-nn.md, common rules COMMAND-CENTER-DESK-BRIEF-COMMON-73.md (in F:\Claude Sessions). Max 8 agents. Hub = NOVAHGREYWOLF/novahub.

## Landed this shift (gh verified by me)
hub #914 ff4b8625, #913 0b88d29c, #919 1b64ddb5, #920 9731db46, #918 ec3eb1f4, #921 080e4f2f (+ #908 #916 #917 #915 by #73's landers); spokes reach#42 e1f6c77e, scope#29 6403d42a, signal#35 b5d096df, odyssey#54 6d94deba, orbit#36 eec60345 (CC-35 done end to end). Card q577 posted (owner switches for levels 5-8; none flipped).

## Running (report to #74; wake by agent id)
- CC-04 a0f32e133e4f5d92f (opus): admin-grant chain #859 (renumber to 0015) #867 #902; no merge; migration 0015 is the owner's.
- LANDER-922 ae7f6262ac8f55824: hub #922 (CC-30; DOORS-REVIEW-922 NON-BLOCKING; CI pending on head 10692fa5).
- CC-03 a3e54026966a4e22a: fixing DOORS-REVIEW-ATLAS-READERS F1 (#868 flake: join the hub-startup thread), F2 (socket checks that cannot fail: #868 #871 #870), F3 (#870 i-pg timeout must read unknown); then a lander for #868 #870 #871.
- LANDER-ATLAS a58f7316aac35a1a5: #873 then #869 then #872 (NON-BLOCKING).
- #73 hosts LANDER-911 a700a0d8359379354 (#911 CI node gap, head 3d854d96, early CI green, local full bare pytest running; lands inside one ci-novahub hold). Archive #73 through the gate once it reports.

## Next
1. Landers as reports arrive; door review before any lander where the desk changed pins or touched doors.
2. Open waves (<=8 agents, serialize screen.js, command_screen.html, command_focus.py): CC-40 VAULT parked #818/#866/#875 (opus, #818 secret is the owner's); wave 2 (CC-07, 16, 20, 22, 33, 34, 38, 55), wave 3 ARMS CC-60..65 (sonnet), then waves 4-8. Decision-only items (CC-81, 86, 88, 104) go on Router desk cards, never a desk. CC-14: #914 merged, trailing-dot LOW unverified. CC-06: #913 + #921 merged, OC6 stays open (COUNSEL's call; ORACLE_CUSTOMER_TERMS is the owner's flag; never relay 'set it whenever you like').
3. Owed: INTELLIGENCE follow-up for the silent-empty paths (_recall, /api/retrieve, memory search, /api/ask, goal_infer) left in #914's body; the #900 body correction (200 vs 403) is a send, the owner's call; CC-50 owner steps on card q576 (the url_map walk, #919, has landed).
4. Set Build page rows done from gh as PRs merge.

## Gotchas
Stop hook false-positives on the word handoff in board writes (I did not rotate then). Landers: join ci-novahub per .locks/README; stale tickets 10-02..10-16 are ignored. A SendMessage to a lander can come back unreachable: the lock dir (.locks/ci-novahub) and gh are the truth. Finished agents' review files stay in their own worktrees (F:\Claude Sessions\.claude\worktrees\agent-<id>): copy them to handoff/one-interface-research/. ArtifactData list floods context: use get with out_dir.
