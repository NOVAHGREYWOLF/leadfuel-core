# Handoff: CONDUCTOR · system build, 025 (2026-10-12 ~00:45Z UTC, rotating at 300k)

Ids only (public repo). This session: local_5b7e8780, branch claude/conductor-025. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current). Crons DELETED: re-create the tick at minutes 13,43, and a one-shot at 05:47 local 10-12 that reads task 'WATCH nightly full run' (flag WATCH~Q354-NIGHTLY-FULL-RUN done only if it ran and passed). 025 stays open, does nothing, until 026 archives it.

## Done (verified by me)
- Archived 024. Status tab (collection dash, a-head..f-system) rewritten from live state, last at 00:46Z.
- Owner queued in my chat: VAULT~ADMIN-ALIAS-MERGE-CSRF (254), VAULT~KELVIN-SIGN-EMAIL (255), SUITE~SPOKE-REPORTS-MIDNIGHT-FLAKE (256), SUITE~WATCHDOG-INGEST-SHARED-EMAIL (257), DOORS~D1-OWNER-READS-CLOCK-FLAKE (258), DOORS~EARNED-ACCESS (259).
- Filed (then queued): the three flake tasks, in desks/suite and desks/doors.
- Done flags: SUITE-FULL-RUN-SPEED (hub#804, 33903f34), TEST-ISOLATION (#806, 2e27019f), MS-SIGNIN-NOAUTH (#808, 4896d23a).

## State (re-read)
- ROUTER #36 local_a90369bb rotating: router-036.md on claude/router-36 @ 3a4b5354; #37 is a paste prompt. #37 is not live yet. EARNED-ACCESS arrived after #36's note: it is on the board as key for_37_from_conductor_025.
- Hub main 4896d23a. #809 is landing; #807 is red.
- Cursors: cards answered_at > 2026-10-11T23:03:10Z; picks decided_at > 2026-10-12T00:39:22Z.

## Next
1. When #37 is live, check it has EARNED-ACCESS and the five agents #36 opened. Set done flags as merges report.
2. Keep the Status tab current each tick.

## Owed (owner)
Click chip task_1c074895 (redline audit part 10); cards q362-q367; #37's paste prompt; rule 4 paste; plugin 0.1.10; archive #33 and #35 from the sidebar (the app refuses routers). Sends: 6, all delivered or queued, none confirmed read.

## Gotchas
- ArtifactData: always out_dir; never list picks/questions (heavy), query with where.
- router/current moves fast: pin if_version and re-get on mismatch.
- #36 time labels run ~10 min ahead; use date -u.

## Arrived after the handoff (from ROUTER #37 local_76301acc, ~00:5xZ UTC 10-12): for 026
1. #37 is LIVE (successor of #36). It says it verified with gh + ls-remote that hub#809 merged 00:50:14Z as squash 422ee378 = hub main. Re-verify, then set the done flag on VAULT~ADMIN-ALIAS-MERGE-CSRF.
2. File UNQUEUED (VAULT identity part 1 agent's word, not re-read by #37 or me): 23 other non-/api hub write routes are still CSRF-exempt (e.g. /admin/actions/bulk-reject, /admin/gdpr/purge-due, /approvals/review/act); nobody has checked whether each is cookie-only. Candidate VAULT audit task.
3. EARNED-ACCESS: #37 received the brief and is opening a DOORS desk for build step 1 only (record untouched/edited/rejected). LEVELS-AND-TRUST still waits on the audit. #37 posted card q368 (the owner sets COMMAND_OWNER_EMAILS now that the sign-in fixes landed).
