# Router handoff #010 -> #011 (2026-10-02 ~19:20 UTC)

ROUTER #10 (local session titled ROUTER #10, Opus) rotating at ~300k. Ids only. Router desk LzmP6QcxmYh9TdvMMjS883 (`questions`), Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor is CONDUCTOR 005 local_083bdfe0. Re-read live state; do not trust these lines.

## Done (verified with gh unless noted)
- novahub merged: #725 (SUITE), #729/#731/#732 (PRIVACY), #733/#734 (DOORS), #661 (WATCH), #735 (reports Fix Ledger, 18:03Z). Archived through the gate: PRIVACY 2/2, WATCH 2/2.
- On the owner's word in my chat: backup key deleted on lucid + NovaHound (Q137); task LeadfuelBackup registered, Sunday 03:30 (Q138).
- Desks opened: ATLAS-B2 local_b0fbc21c (#728), FixLedger 2/2 local_2ef6c551 (DONE, owes 4 items), CC per-user 2/2 local_087f843b (#713), CC 2/2 egress local_f0386c17, ATLAS 2/2 local_1fd82a50 (#730, parked), VAULT-private-remotes local_00ff8154 (DONE; keep open for Q143), MONEY 2/2 local_af080d34 (#727), WAY-no-orphan local_8f3b92b6 (DONE, leadfuel-core #17; archive after a push check).

## Next
1. OPEN two DOORS desks (owner "yes queue both", ~19:13Z, ranks 87-88): CAND-signal-own-anthropic-client (signal voice.py:75) and CAND-scope-own-anthropic-client (scope admin_routes.py:3216). Route through llm_gateway like reach agents.py, raise when unset, never delete ANTHROPIC_API_KEY. Brief in CONDUCTOR 005's message.
2. ci-novahub: CLEANUP-1 released ~19:15Z and woke WATCH P8 (local_1998189a); delivery of that wake is unconfirmed. Make sure someone holds it.
3. Archive ATLAS 1/1 local_e0d6819a once its detached pytest ends (2/2 is live).

## Owed
- Owner cards open: Q141 (queue order), Q142 (checkSuites), Q143 (sync cadence), Q144 (stacked-merge re-run).
- Owner: production reads Q136, Q140; reach token Q135; signal cutover token; DATABASE_VOLUME_GB; plugin update (`git -C C:\Users\novah\leadfuel-way-plugin pull --ff-only`, then `claude plugin update leadfuel-way@leadfuel`); Apple enrolment.
- Cloud cleanup local_ff6f10b8: archive P5-F2, WARDEN, 01XURAmW once Chrome runs (CPU).
- Hung run 37003267585 (book-act): re-check before anyone cancels.

## Gotchas
- My guard refuses: cancelling others' runs, production reads, relaying secret steps. Relays never clear a desk's guard; the owner acts in the desk's chat.
- Desks hold ci-novahub idle when a watch misses (DOORS 2h43m, CLEANUP-1 held it for local runs). Check holders on every wake.
- Chips start on Opus; set the model after.
