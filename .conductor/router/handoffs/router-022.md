# Router handoff #022 -> #023 (2026-10-06 ~05:2xZ, rotating near the cap)

ROUTER #22 is local_09dd8448-54a8-49bd-9165-7233c021860a. Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v159+. Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor: CONDUCTOR 014 local_dfe9f475-0789-4c58-863e-0a548e77a2dc.
PRIVATE detail: F:/Claude Sessions/handoff/ROUTER-22-inbox.md. Read it first.

## Owner rule
Close-first holds. Open a desk only on an owner answer.

## Done by #22
Claimed v146. Removed 73 worktrees (re-verified, no force). Archived 11 desks through the gate (board archived_by_22, archived_by_22_b). Re-sent #21's rulings, nudged 10 stalled desks. Routed q277, q278, q280-q284. Opened CORE10-GREEN (DONE, open until #10 lands) and RESCUE-UNSYNCED (DONE, archived).

## Open owner cards
q279, q285, q286, q287, q288, q208. Clicks on q279/q285/q286 once failed to save: if still empty, ask for a re-click.

## Next
1. Pull answers, fan out. q286 A: open REPORTS-FINISH 2/2 and ONE-PLACE-SHELL 2/2 (Fable pin); prompts in their last STATUS.
2. q288: land or close core #10, then archive CORE10-GREEN local_67c66e25.
3. q285 A (after the owner installs 0.1.7): run the pilot, tell AUTO-DESKS local_9345bf47.
4. Gate held: local_fdfd3d2f (last turn ended mid tool call), CI-RUNNER-STALL local_b44c4f26 (check its detector).
5. Archive #21 local_d51bda2e only when its 9 side desks are finished; #20 after MERGE-TRAIN 3/3, CI-RUNNER-STALL, ATLAS-DOORS 2/2; #18 after HUB727-LAND pushes.
6. Archive me once you are live.

## Gotchas
- 10 sends per owner message; full local_ ids.
- TLS to GitHub fails intermittently (q287): retry once, say unknown.
- detach_session refuses chip-placed sessions.
