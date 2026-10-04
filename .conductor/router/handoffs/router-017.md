# Router handoff #017 -> #018 (2026-10-04 ~20:40 UTC, ROTATING)

ROUTER #17 is local_2c00a079-dc83-4bdb-8b51-510a648a49a1 (Opus), at the 300k cap. Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v52 carries the detail. Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor is now 011 local_495986b8. No start_session: desks are chips. Owner: "keep going, fully auto".

## Done (gh verified)
hub #740, #760, #757 merged; novahub-mcp #41, #42 merged. Archived: AI-STORE-DEFAULT-ICP, GOALSTATUS-WRITES, REPORTS-AUDIT, CI-QUEUE-PRUNE.

## State
- ci-novahub: CI-STARVATION local_5bc2f56b holds it since 20:25Z for #755 (CI running). Next holder: MERGE-TRAIN local_ed6ea561 (q242 = batch5; drain list = last row of WORK_QUEUE.md).
- Live desks: MERGE-DESK-PAGE local_aeeca517, MERGE-TRAIN local_ed6ea561, PUSH-AUDIT local_aa23b41d (NODE); AI-STORE-PLAN-ASYNC local_598fe3d1 (hub half waits for a slot); AI-STORE-MARKET-RESEARCH local_3d574886 (DOORS row ruled keep; a DOORS read before merge); RAILWAY-SET-A local_1137441b (q200 go: reach #34 next, then the rest, hub #699 last); SIGNAL-WORLD local_59345d5d (owns #762, DO NOT MERGE before q237 = done); ATLAS-B1 local_70fae0d7 (owes a digest check, then DONE).
- Chips waiting: SESSIONS-DESK-PAGE (task_868c7a37), REPORTS-VISUAL-REBUILD (task_8548730e).

## Next
Route desk reports. Open the rest of the queue as desks free up: AI-STORE-ERROR-HYGIENE, AI-STORE-RETIRED-KEYS (rename waits on q236), ATLAS-OPS-BRIDGE (design only). Send each page URL to conductor 011 when published.

## Owner items
q237 (SIGNAL_ROUTER_ACCOUNTS), q241 (Voyage digest email), q243 (hub tests on hosted, default B), q208, q232-q236. Next free card q244.

## Gotchas
- Not archived: ROUTER #16 local_dd131408. Its side sessions PART-SCHEMA (#759 open) and CI-OVERFLOW (waiting on q243) would be swept with it. ROUTER #14 local_34998bfa waits on its ATLAS chip desks.
- stop_session on another desk was refused by the classifier. Don't route around it; post a card instead.
- Chips open on the router's model: set each desk's model and effort right after it starts.
- This note lives on branch claude/sad-pare-06dcb7 (the prepared router-17 worktree is a different worktree, and the edit hook blocks writing there).
