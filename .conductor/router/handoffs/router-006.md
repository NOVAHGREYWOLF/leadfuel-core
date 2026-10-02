# Router handoff #006 -> #007 (2026-10-02 ~04:45 UTC)

Router #6 = this session (Sonnet 5.5), retiring at the 300k cap. Ids only (public repo). Pages: Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF.

## Done
- Owner answered Q30 "both" (REPORTS + INTEL). 17 desk chips raised; no start_session, so each starts when the owner clicks, then I verify title, group, model.
- Closed or shipped (desk-verified, not re-run by me): P5-F4, P6, P7, P10 (links only), B8, D4, G8, G9, G1-followup, L10, L11, KEYS-1 (leadfuel-core PR 12), Q31-triage (PR 13), Q3 (rule already in settings), D4-design (PR 14), PR-leadfuel-core-7 (PR 11), novahos PR 38 (draft).
- Cards: Q29-Q59 posted; Q32,34,38,39 withdrawn (no options); older off-scope cards parked via status=withdrawn (restore on request, Q26 GoDaddy password matters).

## Running (re-read with list_sessions)
P5-F5 local_9937b2f2 (novahub#700), P8 local_1998189a (#695), P9 local_178af2ba (#701, PDFs use existing skin), report fixes local_4213cd64, Dec-2 embedding compare, Q5 gcp-key script. DOORS one-door local_53691034 waits on Q2.

## Update 02:40 UTC (read this first)
Owner answered Q2 check (he runs the curl and tells DOORS local_53691034 the number), Q52 do_it, Q53 keep, Q54 yes, Q55 yes, Q56 yes, Q57 yes, Q58 finance, Q59 build. Done by me: DOORS told (Q2); chips raised for LEDGER-1 (WATCH) and CENSUS-1 (INTELLIGENCE, Q55). NOT done, queued for free slots (8 max): (a) KEYS-2 desk: remove ANTHROPIC_KEY_PREGATEWAY_BACKUP from lucid and NovaHound AFTER DOORS finishes Q2 (never touch ANTHROPIC_API_KEY, it holds gateway tokens); (b) one cleanup desk for Q56 (delete brain entries 12503-12505 after confirming exact duplicates of fact 6261, copy rows first), Q57 (git branch -d two merged branches), Q58 plus task d1c5a22e-4 (finance_read scope and recency in app.py); (c) D4-build PR A only (hub brain_events table + GET feed, flag off, draft, Opus, check echo ownership first, design = leadfuel-core PR 14). Routed notes on cards Q2,52-59 still owed (batch write failed on version_mismatch: read each card and write with if_version). Owner said: when rotating, open a fresh worktree session with the full brief and message every live session; do not archive without a live successor.
Live desks: P5-F5 local_9937b2f2, P8 local_1998189a, P9 local_178af2ba, report-fixes local_4213cd64, Dec-2 local_49f2c614 (PR 15), Q5 local_7ddb1c08, DOORS local_53691034, conductor local_e5823a22.

Archive ruling (owner via conductor, matches memory): router/conductor archive self only with a live successor and a pushed handoff; a desk archives only when fully done (PR merged per gh, final report, handoff, nothing unpushed, no owner decision pending), and every desk brief must say ASK the router before any self-archive; the router opens any new worktree or session, desks do not; an archive at the size limit with no new session is raised to the owner, never done quietly. Two earlier desks (D4, P6, P7 style) self-archived or said they would: check.

## Next
1. Read answers (answer set, routed empty) on Q2, Q52-Q59, Q54. Q2: owner runs one status-code curl and tells DOORS the number; 200 then DOORS merges signal #13 then #28. Q54 yes then open LEDGER-1, then 2-5 (picks rank 43-47), check no desk already holds them.
2. When the report-fixes desk reports, post its N14/N15/N17 questions as plain cards.
3. Next INTEL tasks by rank after L11: M1, M2, M3, R12b, R13-F1, S5, T3, X6 (owner call), X8, Z4, then the local_* ones; B4 waits on owner B3. Cap 8 desks.

## Owed
Conductor message about Q54 was queued, not confirmed read. SESSION_MAP edit for move_credit.py (Q40) not done: ROUTER's file.

## Gotchas
Picks are conductor-written, so confirm by card. Page hides status=withdrawn only. Use file_path for write_db JSON with backslashes. Never delete ANTHROPIC_API_KEY (callers hold gateway tokens there). Status on the Conductor page is mostly stale: about half the tasks were already shipped.
