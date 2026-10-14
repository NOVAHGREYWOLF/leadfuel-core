# Router handoff #050 -> #054 · owed questions, note 001 (2026-10-14 ~01:5xZ UTC; guard said ~302k)

ROUTER #50 = local_f6a2e469-bd24-489b-8667-ae954d6b5685 (Sonnet 5.5). Ids only. State doc: board router/owed50 (artifact A4uS9xn1emqupohdE4DUfV, read with out_dir). Router desk LzmP6QcxmYh9TdvMMjS883. Conductor desk MKAx49RAskZ3cV7f2EkDMF. Live: ROUTER #53 one-interface local_76d5692d; ROUTER #52 live (routed my q400/q401); conductor 036 local_9190119c. Predecessor #46 local_e8036ce2 NOT archived (app refused: kept for the user).

## Done
- Claimed from #46. q392 scope read: agent REFUSED by the production guard, chip desk ran `go names` (owner typed it in the desk chat); result on card q392 field `result`: scope has no HUB_API_URL, writes never reach the hub, counts UNKNOWN. Desk archived by me. Conductor key for_conductor_035_from_router_50b.
- Routed: q394 D, q397 B (conductor already filed NODE~RAILWAY-APOLLO-LOOK). q399 is #49's; relayed the owner's "I set all six". q400 B routed by #52.
- FINDING: before the census, ZERO cards were truly open: the 24 "unanswered" cards are all status=withdrawn (32 in all). I closed 6 as superseded with notes (q07 q09 q14 q27 q43 q44).
- Census (owner: "find all questions, put them on the board, ask me them all here"): agent abc1e3bfb0fcbe9cb DONE. 21 DECISION cards q415-q435 on the Router desk page; index in board router/owed50_census (decisions with options matching each card one for one, plus 30 steps, 21 router-owned, 43 superseded, 18 unknown/stale).

## Next
1. The owner DISMISSED my first in-chat batch (AskUserQuestion on q415-q418, all four). Do NOT re-ask by that tool unless he says so; wait for his word on how he wants them (the cards are on the page, clickable; q415-q435 are open). He asked to be asked "all here": ask him which form he wants.
2. When he answers (page click or chat), write each answer on its card (answer letter, answered_at, answered_via) and route it: tell the asker desk or the conductor (router/current key for_conductor_036_from_router_N). Production-read or secret steps need his typed go in the desk's own chat.
3. Hand him the 30 STEPS list from owed50_census as a separate checklist (not questions).
4. q246 cron-daily hold stands (NODE~HUB-RAILWAY-TS-DRIFT first, his queue click).

## UPDATE 02:3xZ UTC 10-14 (supersedes Next items 1-3)
- The owner ANSWERED all 21 census cards q415-q435 by page click (01:44-01:49Z). I routed every one (routed field, cards v3). Filing list for the conductor: board router/owed50 field for_conductor_036_from_router_50 (router/current refused my write, upstream_invalid_argument at v559, probably its size: do not write big keys there).
- DELIVERY: conductor 036 local_9190119c and ROUTER #53 local_76d5692d are ARCHIVED (sends bounced). The live conductor looks like local_1dc1a95a (CONDUCTOR · system build, not in the CONDUCTOR group); my send to it was UNDELIVERED ("no sign of starting in 20s"). Re-send once; the board field is the durable channel.
- NUMBERING: #54 is ROUTER #54 one-interface (local_2afda8d8), NOT mine. Take the next free number (#55 or later); the worktree router-54-owed-questions on claude/router-54 is mine anyway, use it.
- q436-q449 exist (other routers' cards); not read by me.
- Next now: (a) re-send the filing list to the live conductor; (b) check whether it filed the 12 tasks; (c) ask the owner how he wants the STEPS list (30, in owed50_census) delivered; (d) the in-chat batch was dismissed, do not re-ask.

## Owed / not delivered
Sends: 2 to #49 about q399 (one delivered, one queued). Owner to archive #46 from the sidebar or retry. Census cards say created_at 10-14 UTC where the page may show 10-13.

## Gotchas
Bash cd persists and flips the primary dir between worktrees: cd to yours before git. router/current is huge: read only with out_dir. A card's `answer` null is not "open": check `status` withdrawn. Router numbers are global (#53 is one-interface; take the next free).
