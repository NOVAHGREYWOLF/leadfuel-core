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
4. (#37, ~01:xxZ) REDLINE AUDIT outputs (part 10, Fable) are in F:/Claude Sessions/handoff/one-interface-redline-audit/. The V2 re-check is pending; part 11 folds it in. Headline (the audit's word, not re-read by #37 or me): none of doc 04's eight regions exists; there is no level/ring/quest/credit/likeness code; 'nothing leaves without you' is false today (runner and campaign sends skip the approval queue by default, any spoke token can approve, and the approvals link is keyed on a secret every spoke holds). #37 posted cards q369 (rebuild scope, default A), q370 (turn on the two approval switches), q371 (person-only approve), q372 (own secret for approval links).
   - File the build phases as tasks ONLY after the owner answers q369 (they are in STEPS.md in that folder).
   - File UNQUEUED three small VAULT tasks from the audit: P0-6, P0-7, S-2 (read their text in that folder first).
5. (#37, ~01:3xZ) DONE FLAGS to set after re-verifying (#37 says it verified with gh + ls-remote; hub main 451b6fae): SUITE~WATCHDOG-INGEST-SHARED-EMAIL = hub#810 merged 01:02:59Z (06d4ee4b); SUITE~SPOKE-REPORTS-MIDNIGHT-FLAKE = hub#812 merged 01:14:32Z (7309a41a); DOORS~D1-OWNER-READS-CLOCK-FLAKE = hub#811 merged 01:27:58Z (451b6fae); SURFACE~ONE-INTERFACE-REDLINE-AUDIT is DONE (part 11 finished it, outputs in the audit folder, part 10 archived).
   - File UNQUEUED (SUITE agent's word, exposure unchecked): the same import-time-day pattern as the midnight flake at tests/test_e2e_daily_chain.py:37, tests/test_approvals_by_email.py:35, tests/test_scope_core_reports.py:23, tests/test_spend_in_app.py:37.
   - Audit V2: the expiry sweeper already exists (app.py:18428-18456), so STEPS P0-3 is verify-only. Note this on the P0-3 task when the phases are filed (after q369).
6. (#37, ~01:4xZ) DONE FLAG after re-verifying: VAULT~KELVIN-SIGN-EMAIL = hub#813 merged 01:38:03Z, squash c53a4b1f = hub main (per #37, which says it verified with gh + ls-remote). ROUTER #36 is archived per #37.
7. (#37, ~02:xxZ) DOORS~EARNED-ACCESS step 1: hub#814 DRAFT, head 503dadeb, pytest SUCCESS (per #37's gh read). It records how each approval ended (untouched/edited+delta/rejected/unknown, original kept) on web, Slack, Teams, mesh and campaign paths; it sends nothing. It carries migration 0012 (new table) = a production schema change: card q373 (default A, land after review); a read-only PRIVACY/Law 9 review runs first. Keep the pick DOING, not done; add a note. Steps 2-4 wait on q369.
   - File UNQUEUED (desk's word, code not re-read by #37 or me): (a) the web approvals page cuts drafts to 4,000 characters, so approving a longer draft there sends it cut short; (b) for app_action rows, an edit on the web approvals page is stored where the sender never reads it, so it is silently dropped. Probably DOORS (the approvals path).
