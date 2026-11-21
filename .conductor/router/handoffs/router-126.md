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

## Update (2026-11-21 about 16:00 PST, about 330k tokens)
- Cards posted: q9549 (archive old scheduled runs, open), q9550 (restore desk or reuse Phase 0 copy), q9551 (hub PR 1102); cluster audit agent ac1146925dd53246c DONE, posted q9560 to q9563, findings on board router/cluster_audit_1 (R620 power supply 1 dead, power event 15:07 Nov 20, F1 likely the built in NIC fault, 710 storage back about 13:08 Nov 21).
- NOT LANDED (undelivered, held): relays of the audit findings to NODE overlord storage part 3 (local_756bc124-5bb2-4a69-8d1e-5d1615dbac5b: its drives chain failed 7:30 am Nov 20 rc 4) and NODE always on part 4 (local_eb4bc8eb-4c75-46ce-b936-bac9c9239574: vault backup 2:15 and sync 2:45 am Nov 21 failed because the 710 was down; check the 2:15 am Nov 22 run). The cards carry the same facts; resend when the owner types in those chats.
- SENSORS part 1 (local_c4f5b466-aec8-4253-accd-6470fcf9b3a5) is at about 318k and asked for SENSORS part 2: hub draft PR 1132 (head a982b441, pytest pending), handoff note .conductor/desks/handoffs/web-liveness-collapse-001.md on claude/sensors-web-liveness-collapse-453414 (f94b8b3, verified on remote). start_session was refused in a message driven turn; open part 2 in the next turn the owner types into, or by a way slot, nested under the router, then archive part 1 through the gate. The desk stays open meanwhile (hard cap 450k).
- Globe merge settled by SURFACE part 21: merges go ahead, only the deploy is blocked (q9518 B); redeploy owed when he picks a Railway plan.
- Send cap: about 8 of 10 used, plus 2 undelivered.
- Agents still running at this point: DOORS 1, DOORS 2, INTELLIGENCE 4, ARMS 1, NODE 12, routing audit done, Railway check aaef57bcb05349e60.

## Update 2 (about 16:10 PST)
- ROUTER #124 reports CONFIRMED (Outlook metadata, its own check): 8 command books Nov 11 to 18 have no attachment, none after Nov 19 5:54 am PST; cause unknown. Lead only: the spend approval mail (11 asks, up to 0.82 dollars, Nov 19 6:45 am PST, owner forward 12:40 pm) says nothing runs until answered; Railway deploys are blocked (q9518 B). #124 is at its cap and writing its handoff; its successor owns the reports lane. I post nothing for reports.
- Hub main moved: 7c6feb95 (a commit #124 could not match to a merged PR; newest merged PR still 1131). PR 1102 head 0c93df2e is ahead 2, behind 14. Landing agents must merge current main, not 0a763d29.

## Update 3 (about 16:25 PST)
- Storage part 3 (local_756bc124) did pick up the relay and CHECKED the audit itself (read only): chain failure at 07:30 Nov 20 was NOT power (worn disk sda, real unreadable sectors); power event journals say 15:04 not 15:07; the 2 TB drive is safe (copy on the 620 verified 07:26 Nov 20); it relocked sda, sdb, sdc read only and started a new chain at 14:42 for sdb then sdc; sda salvage is the owner's call (the desk posts its own card). Correct cluster_audit_1 wording if it says 15:07 or power as cause. Relay to always on part 4 (local_eb4bc8eb) still unconfirmed.

## Update 4 (about 16:35 PST)
- Always on part 4 (local_eb4bc8eb) verified the audit itself and re-ran its own file backup by hand at 2:43 pm (55,783 files, drift 0 on the 710 and the 620); vzdump vault-nightly failed Nov 21 02:15 only because r710-backup was offline; check the Nov 22 02:15 run after 3:15 am. NEW RISK: the 620 library disk /srv/library is 91 percent full (262 GB free) after the storage desk's copy and the vault nightly adds about 15 GB, so about 17 days of runway: needs a card or the storage desk's (owner's) decision, not yet posted. The 710 firewall rule (tcp 2049) is still not in, so the vault survey stays blocked (needs his typed 'add the rule' in fleet part 3's chat). Both storage desks have now confirmed the audit; relay done.

## Update 5 (about 16:45 PST)
- Railway check agent aaef57bcb05349e60 DONE (read only, a sub-agent's report): the workspace is PRO and UNPAID (open invoice 4 Oct to 4 Nov, 59.23 dollars, card declined), NOT a trial. Production serves (healthz 200, build 94e64d48 from Nov 11); no deploy since; whether deploys are refused is UNKNOWN. The only copy of the live hub database is on Railway (5.8 GB, no backup schedule). Card q9552 posted (copy first or pay first), open. novahub-cron-daily and APOLLO have no live deployment (crashed for too long) and the spend-reconcile cron is stale 2.4 days: separate fix, no desk opened. Correct the q9518 wording when routing: it says trial.

## Update 6 (about 17:00 PST, about 355k tokens)
- MERGED (verified by me with gh): hub 1012, 1114 (3fd7b744, paid Fieldy stays off), reach 48 and 49. Open: hub 1115 (head 0c3e2bc6), 1116, 1117 and 1118 (undrafted, landing), 1119, 1112 still drafts. Red cause on 1114 was a flake fixed on main by 1128, so older heads fail until main is merged in.
- NODE 12 agent a51b12bdebfe1f6bc (interim report, agent still has background work): app reinstalled signed from local branch node/p12-turn-on (06509bd, d4a96c7, F:\novah-estate, push disabled); done q9432 14b, q9433 signed build, q9436 embed worker, q9439, q9442, q9443 (no hooks.json so no hook runs); waiting on hub PRs: q9434 needs 1115, q9441 needs 1116, q9440 needs 1117 to 1119. Owner taps are card q9564 plus runbook section 15. Table F:\Claude Sessions\handoff\node-part-12-turn-on-table-2026-11-21.md. Relay to installer desk local_15185106 sent (base next install on node/p12-turn-on).
