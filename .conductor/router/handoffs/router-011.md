# Router handoff #011 -> #012 (2026-10-02 ~22:10 UTC)

ROUTER #11 (local_99c30023, Opus) rotating at 300k. Ids only. Router desk LzmP6QcxmYh9TdvMMjS883 (`questions`), Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor is CONDUCTOR 006 local_4de240e1 (005 local_083bdfe0 stays unarchived; ROUTER #11 and 006 are its side sessions, so the owner must drag them out first). Re-read live state; do not trust these lines.

## Done (verified with gh / ls-remote unless noted)
- Archived through the gate: ROUTER #10, WATCH P8 (hub #695), WATCH P5-F5 (#700), SURFACE ATLAS 1/1, DOORS signal (signal #30 closed as duplicate of #13), DOORS scope (scope #25 closed; q146=pr11), DOORS Odyssey purge (odyssey #50 merged).
- Fanned out and marked routed: q126, q129, q141-q147, q149-q153. q148 is unanswered (the owner was given a script for the 7 wait-for-CI PRs; novahub #737 waits on the hub runner recreate).

## Desks live (all mine; they are my side sessions)
- SURFACE ATLAS-LIVE-FLOWS local_6345dfcd (Opus, high): hub #736, stacked on #730.
- WATCH REPORT-DESK-LOG local_be232c9f (Sonnet): token set (q147); it verifies after merge.
- INTELLIGENCE LAW-DATA-PLACES local_198a164a (Opus, high): hub #738. SUITE 2/2 local_ae2f0221 writes the gates stanza on top of it; ratification by card.
- WATCH MERGE-ALL-GREEN local_874ae11a (Opus): merging green PRs; skips the gateway cutovers and the Railway config PRs (owner merges those).
- Older: SURFACE ATLAS 2/2 local_1fd82a50 (#730, parked); CLEANUP-1 local_16a76eb4 (#706; detached run, log at F:\Claude Sessions\parked\cleanup-1-q58\run.log, ends with PYTEST EXIT); SURFACE apple app 2/2 local_772034d0 (leadfuel-ios #3 workflow, for NODE); VAULT local_00ff8154 (archive after the first nightly sync push, 2026-10-03 04:30 PT).

## Next
1. Open ATLAS-VIEWS (rank 90, 14 views, ship Journey/Out-door/Follow first) and ATLAS-ACT (rank 91, VAULT review before CHANGE/OUTWARD) once ATLAS-LIVE-FLOWS lands.
2. Route leadfuel-ios #3 plus a new runner to NODE once the conductor queues CAND-ios-runner.
3. Check the ci-novahub holder on every wake (desks hold it idle when a watch misses).

0. FIRST, before the weekly reset at 2026-10-03 21:00 UTC: the FABLE LIST (CONDUCTOR 006, owner in local_41e34e93). Conductor desk picks ranked -20 to -11 are pinned to claude-fable-5-1 at xhigh: FABLE-1-door-audit, ATLAS-B1-embed-refusals, ATLAS-ACT (design only), FABLE-4-injection-fence, FABLE-5-connector-oauth, FABLE-6-rights-design, FABLE-7-replica-sync, FABLE-8-postmerge-review, FABLE-9-csrf-runB, FABLE-10-runbooks. Rules are in each task's basis. Set model and effort by hand and read them back. At most 3 at once. Run get_usage before each open. Stop at 90% of the weekly bar or 85% of the 5-hour bar. Open nothing after the reset. Ranks 94-119 are queued too, including CAND-ios-ci-workflow/runner and 11 SPATIAL-*. The 96 OWED-* rows are not queued.

## Owed
- Owner: q148 script; scope + signal gateway tokens; drag the routers out from under CONDUCTOR 005; Apple enrolment.
- Candidates with the conductor: CAND-check-all-partial-count, CAND-hub-runners-recreate, CAND-vault-sync-watch, CAND-ios-runner, CAND-ULF-T1..T5.

## Gotchas
- Auto mode refused NODE's merge of #714 as a production deploy; MERGE-ALL-GREEN's own merges went through.
- Session sends pause after 10 until the owner types.
- Before archiving yourself, detach_session the desks you started (side sessions get swept).
