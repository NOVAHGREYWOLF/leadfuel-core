# Router handoff #052 -> #53 · one-interface (2026-10-14 ~00:30Z UTC; guard said ~300k)

ROUTER #52 = local_5ffaaee7-f0a1-4743-8ad1-b6f387abc40e (Sonnet 5.5). Ids only. STAYS OPEN until #53 is live; #53 archives it through the gate (no agents running, nothing unpushed: this note is the only thing I push). Board A4uS9xn1emqupohdE4DUfV: router/current (claim_52, landed_52; get with out_dir, ~250 KB), router/roster52 (all state and verifications; READ ITS KEY next_for_53 and open_after_this first). Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor 037 = local_08f4350d (a slot run; briefs go to it). #50 owed questions = local_f6a2e469 (idle).

## Done (all read by me with gh / ls-remote)
hub#823 ADD-PANELS MERGED 23:58:16Z (10c347ea). hub#824 ASK-PHONE-PATH (q401 A) MERGED 00:23:18Z (e73033ae). Both DOORS-reviewed read-only, landed by lander agents inside the ci-novahub hold. Hub main re-run 38487425081 attempt 2 SUCCESS (midnight flake in tests/test_scope_core_reports.py, filed unqueued). q400 B design done by NODE full system automation part 1 (local_6ecb7d43): cards q402..q410 posted.

## State to re-read
Hub main = e73033ae at 00:24Z. Post-merge push run 38489886023 was IN PROGRESS: read its conclusion first. Lock ci-novahub FREE (I hold nothing). Sends used 5 of 10.

## Next
1. Read run 38489886023. 2. Read the Router desk for answers (nothing wakes a router): q411 (two more ask.answer callers, High; if A, conductor records the pick, then open INTELLIGENCE part 13, Opus), q402..q410. Route each answer, write `routed`. 3. Only queued picks start. Unqueued: SURFACE PANELS-DECIDE-IN-PLACE, PANELS-LEVELS-WRITE-CALLS, SUITE~SCOPE-CORE-REPORTS-MIDNIGHT-FLAKE.

## Owed (owner)
hub#756 merge word typed in NODE atlas part 1 (local_27c655ce) chat; APPROVAL_LINK_SECRET on NovaHub then hub#818 renumbers 0013 -> 0014 then q385 B; plugin 0.1.11; cards above.

## Gotchas
Do not start hub CI between ~23:45Z and 00:15Z. Edit/Write are refused under .locks (use shell). Release a lock with `rm <stamp>` then `rmdir`; Remove-Item and rm -rf on F:\Claude Sessions are refused. In Bash set MSYS_NO_PATHCONV=1 for `git show ref:path`; `cd` shifts the primary directory, avoid it.
