# ROUTER #126 · novah estate · handoff (interim, 2026-11-21 about 15:30 PST, about 300k tokens)
Session local_3dcfabeb-3f91-4824-a749-42f64c84f680, slot way-slot-03 (owner opened it). router/current names #126 (v685, read back). #125 archived. DO NOT ROTATE WHILE AGENTS RUN (they die with the router); this note is the interim record, update it at the real rotation. All state lines are agent reports unless marked verified. Re-read live state.

## Done (verified by me)
- Claim written and read back; #125 archived through the gate; 7 empty or finished sessions archived (535216c2 6437f106 be93a270 ea7b3328 5a28adfd 9578c287 176cf567).
- Hub main tests green on 0a763d29 (gh): #125's "shared red test on main" is false. Hub 1099, 1131 merged (gh).
- Cards routed: q9534 (to home node part 21 installer, delivered), q9518 (to SURFACE one-interface part 21, queued), q9485 (to CONDUCTOR 058, delivered); routed written on all three. Card q9549 posted (archive old scheduled runs), open.
- Roster: board router/roster_126 (v2). Sends used about 7 of 10.

## Running (all report by task notification; ids are agent ids)
- SENSORS · novah estate part 1 session local_c4f5b466-aec8-4253-accd-6470fcf9b3a5 (web_liveness collapse; needs the owner's typed yes in its chat for the production dry run).
- a1e54992a82f93d81 DOORS 1: hub 1012, 1115, 1116. aca813528163e88e1 DOORS 2: hub 1117, 1118, 1119. a85113363bce7079c INTELLIGENCE 4: hub 1114 (paid Fieldy stays off, q9438 X). a14df2a454553f7f5 ARMS 1: hub 1112, reach 48 and 49. a51b12bdebfe1f6bc NODE 12: answered Turn on cards q9424 to q9443. ac1146925dd53246c cluster audit (read only, findings to board router/cluster_audit_1, cards q9560 to q9569 reserved). a0c6c71621b860102 drafts two cards (files in scratchpad carddrafts; post as q9550 restore desk task_0ce2c63d and q9551 PR 1102). aaef57bcb05349e60 verifies Railway plan and deploy state (read only).

## Owed
- Route the rest of the 25 answered cards (table: scratchpad routing_table.md of the first #126 session; summary: 17 acted already, write routed notes saying so; q9468 hold, conflicts with q9534 and q9548; q9515 C needs a free spec task; q9514, q9470, q9471 held). Write routed notes.
- Archive audit of the real desks (about 197 non-routine sessions) through the gate, one at a time; the nightly review (F:\Claude Sessions\handoff\watch-archive-review\NOTES-2026-11-21.md) found 0 pass, 136 check first. Wake-run archive waits on card q9549.
- Post cards q9550, q9551 from the drafts; the cluster audit posts its own.
- INTELLIGENCE part 1 (local_b6ba70a1) needs the SENSORS desk id (the desk said it would tell it).
- REP-R0, R2, R3, R6, R7 picks and the REP unopened list: queued behind the cap; ROUTER #124 reports (local_dcb9f28b) owns reports PRs.
- Merge only on tests job success on the exact head, via scripts/merge_train.py.
- Conflict list from the routing audit: q9468 vs q9534 and q9548 on where the hub lives; Railway plan state; globe merge wording (asked SURFACE part 21).

## Gotchas
start_session is refused in notification turns (agents instead); ArtifactData get with out_dir only; list_sessions saved file parsed with scratchpad parse_sessions.py; wake runs and cards are UNDELIVERED because of the 10 send cap and unknown askers.
