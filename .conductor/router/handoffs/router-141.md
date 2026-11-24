# ROUTER #141 · novah estate: HANDOFF at the 300k point (2026-11-23 PT, ~00:40)
Session local_838fc083-00e8-465b-8423-ef146df7ea5d (way-slot-02), branch claude/router-141. Predecessors #140 local_0de18479 and #139 local_beaf4b11 stay open to drain. Conductor 061 local_2c7769d4. router/current v710 names me; successor rewrites it (pinned). Cap now 100 agents, 20 per process (owner via 061). Roster: F:\Claude Sessions\handoff\ROUTER-141\ROSTER.md (parts 186-239 incl.; next part 240). Brief pattern: ROUTER-141\BRIEF-COMMON.md. All state is a claim: re-read.

## My agents (die if I am archived: stay open until they report)
Running at handoff: lander NODE 237 (a85c932ed6c83bc41, hub queue 1124,1179,1188,1186,1192,1185,1187,1086,1196,1205; 1123/1182 held), WATCH 234 (1200 main merge, CI pending), SURFACE 235/236 (walk page links, P11/W03), NODE 229, 230, 231 and INTELLIGENCE 228 (K-series builds), NODE 232 (fix lc 110 leaks, urgent), INTELLIGENCE 239 (fix lc 111 leaks), DOORS 238 (re-read lc 112 at b55af8b).
## LAND-OK (current heads, DOORS reads)
hub 1124 356f2d50, 1179 db0dd926, 1188 7b37a490, 1192 547721d4, 1196 34157fff, 1205 137f106e, 1185/1187/1086, 1197/1199/1202, 1206 3966bd10, 1207 e2e16cd0, 1200 809f6d66 (content; new head after WATCH 234 needs re-read); lc 107 5cbf541, 108 1567d6a, 109 e0977aa.
## CHANGES, fix running or owed
hub 1193 (fixed adc2755c by ARMS 200; DOORS 225 re-read running), 1156 (ARMS 226 running, needs 1193 first + novahos tiers), 1194 701d8d77 and 1195 fd5084ac (fixed by SENSORS 201, CI + re-read owed), 1198/1201/1203 (DOORS 220 running), 1204 (DOORS 221 running), lc 110 (NODE 232), lc 111 (INTELLIGENCE 239), lc 112 (re-read DOORS 238). Open: DOORS 208 q9277-like QBO scope wall PR, DOORS 211 done.
## Owed
Re-reads after each fix lands; landing after LAND-OK (second lander pass for 1206, 1207, 1197-1203 etc.); 1123/1182 conflict fix + read; K-series PR reads; SURFACE 218 + 219 done; book/PRIVACY/COMMS lanes not opened; ROUTER #142/#143 slices proposed to 061 (answered cards, VAULT/COUNSEL/MONEY/BOOK B rows; SENSORS coverage-25, ROUNDTRIP coverage-40). W03 'ARMS step 5' card does not exist. NODE 21 local_28c73fb5 gets walk-page news.
## Gotchas
Stop hook misreads ROSTER.md as a handoff. cd to leadfuel-core before spawning Agents; worktree isolation errors are transient, retry. Owner steps live on the Owner Walk page https://claude.ai/artifact/1i1FhsztHxTi16NYwYhpNL (v12+).

## Addendum (after the first push)
- lc 113 (NODE 203) got CHANGES at 3723bce (DOORS 224, comment 7124830991): private names in docs/SURFACE_OFFLOAD_REVIEW.md and docs/NODE_PART203_DECISION_RECORDS.md (public repo; use category counts, squash the branch clean) + probe should not follow redirects/proxies. Fix agent NOT opened: open one (NODE) first thing. model_service itself passes Law 9.
- hub 1193 LAND-OK adc2755c (DOORS 225). lc 110 fix by NODE 232 running; lc 111 by INTELLIGENCE 239.
- Successor: my arm of slot 06 was refused (nobody typed into this run); LAUNCH-REQUEST sent to conductor 061 (queued) with brief F:\Claude Sessions\handoff\ROUTER-141\SUCCESSOR-BRIEF-144.md. Slot 06's model line is now sonnet-5-5. If no ROUTER #144 appears, the owner pastes that brief into a fresh session.

## Addendum 2
- hub 1200 new head 86cba04a (WATCH 234; CI tests+lint success on it; stacked on 1105 -> 1070, none landed): needs a fresh DOORS read; its LAND-OK at 809f6d66 is stale.
- SENSORS part 4 RAN the read-only Railway production pass (owner typed yes, ~23:35 PT): report F:\Claude Sessions\handoff\ROUTER-141-or-140\SENSORS-4\out\report_railway_run_20261124_073530Z.txt. lucid:day has 0 rows ever (do NOT flip LUCID-DAY-RECURRING); QBO 6 of 8 rails over budget, 0 rows in 7d, re-sign-in owner step real; watchdog heartbeat alive; ingest_rejected 66 all-time. Walk page needs: mark the read-only pass step done; cut-uid count still needs its own yes. #140 is now ARCHIVED (its agents' reports are lost).

## Addendum 3
- lc 110 cleaned by NODE 232: squashed to f6f12d1 (allowlist guard, real guards, scanner fix, 93 tests); needs a fresh DOORS read at f6f12d1 (DOORS 212's CHANGES was at b7a2ffd). Old head b7a2ffd (IPs, login name, aliases; no credentials) may still be served by GitHub by SHA; main also already carries IPs from #103 (node/cluster_targets.json, tests/test_cluster_route.py). OWNER-STEPs: decide whether to change the IPs/login, whether to ask GitHub Support to purge b7a2ffd and whether a desk moves #103's values to a local file.
- Successor: conductor 061 passed LAUNCH-REQUEST to CONDUCTOR 062 (live ~23:53 PT), who arms a Bypass slot for ROUTER #144.
- hub 1124: lander NODE 237 merged main in (head 91f3e24d), CI running.

## Addendum 4: new drafts needing a DOORS read
hub 1208 (QBO scope wall, DOORS 208, 22e30810), hub 1213 (K01 web_liveness exclusion), hub 1214 (W16 prompt-site list), lc 112 LAND-OK b55af8b (DOORS 238), hub 1204 fixed to 59652538 (re-read owed), hub 1200 86cba04a (re-read owed). Owner Walk L-SURFACE row now links the 11-lane index (v13). K02 overtaken by hub 1078. Owner-steps: brain_census production read (counts only) for W16; rulings on W16 tensions (router posts a card).
