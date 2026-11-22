# router-130-reports handoff (ROUTER #130 · reports, local_258b7b39-89bd-4a93-bc51-c7b1f9cd0505), 2026-11-22 ~2:50 am Pacific

Predecessors: router-127-reports.md, router-124-reports.md. Owner done-criterion: ALL reports work LOCALLY. Owner 2026-11-22 (typed to CONDUCTOR 058): "run as mych of the que as you can push". Reports go to CONDUCTOR 058 (local_b7630866-f2e7-4436-9936-af237cbc5c34); coordinate agent slots with ROUTER #131 (app cap 20 subagents shared). Successor title: ROUTER #131 is another router: use the next free number (check list_sessions).

## Done (read by me with gh on hub main unless marked)
Landed: #1048 (Ledger), #1135, #1134, #1108 (38-row registry), #1139 (proof-send script, dry-run default, never run with --send), #1141 (run_reports_local.py, sample data only). #1096 (another desk's) landed by accident by my agent; 058 told, its desk not.
Board `router/current` field `reports` rewritten at claim (v696); do not touch session_id/status/next_session_id (estate router).

## In flight / open (re-read before acting)
- Hub #1140 local book composer (head 6f9836d7, tests success on it): owner answered q9602 A (read by me, 2026-11-22 19:18Z). A landing agent (--prs 1140) was started; read result.
- Hub #1136 fieldy-local (head 058d15db, tests success, draft): HELD for card q9603 (local default Fieldy tier). oss_router.py timeout_s kwarg: both PRs carry the identical hunk; go-ahead = owner click q9596 A, recorded in both PR bodies; no session owns oss_router.py.
- leadfuel-core #79 REPORTS_PLAN refresh: draft, not merged.
- #1102 is ROUTER #128's; spoke PRs 1121, 1124-1127 are owner sessions' (10f0a004, f67e0839).
- P5-F1 DONE (audit, tests not run). P7 DONE.

## Queue for the owner's "run as much as you can" (058 writes picks "now")
Asked 058 for picks on code-only rows: intelligence/REP-R5 Horizons, watch/REP-R6 reports board and health, intelligence/REPORTS-MASTER-STORE-SILENT (verify then fix), watch/REPORTS-DELIVERABILITY-DORMANT, node/REP-R2 (needs P1 check). Open each as a background agent only after 058 confirms the pick. Blocked on the owner's typed word: REP-R0 (production read), REP-R3 (channel + test send), REP-R7 (cutover), GRP-reports-finish (needs-owner), REP-R4 (PDF vs q9001 A offline HTML), q9595 B production data copy, the real proof send (--send --confirm <code>, EGRESS_EMAIL_DAILY_MAX>=1).

## Gotchas
ALWAYS `merge_train.py ... --prs <n>`: a run without it landed #1096. Read answered cards yourself (wake pass HELD). ArtifactData always with out_dir. Agents' reports are claims: read the gh run on the exact head. The Stop hook mis-fires on the word "handoff" in board writes. Card numbers: highest seen q9603. Worktrees left in novahub: train-1135, fieldy-local-merge, reports-attach-all, book-local-composer.
