# Router handoff #029 -> #030 (2026-10-07 19:3xZ UTC, at the 300k guard)

ROUTER #29 is local_46ddffce-5fef-4faf-a3b7-b4622c1952d8. Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v296+; keys log_29..log_29k, agent_reports_29*, owed_29*, clock_29 (my stamps are ordering only; use date -u). Router desk LzmP6QcxmYh9TdvMMjS883.

## Done by #29
Claimed v277. hub (NOVAHGREYWOLF/novahub) landed on main, gh verified: #786 3d64acc5, #793 S1 82513aea, #791 S5 3e428cd9, #794 S2 8a2ffa9b, #777/#779/#780/#781 d3ef0842. WAY 0.1.8 installed (card q346 asks the owner the title wording). q343=A routed, q344/q345 routed. Archived train 6/6. DOORS reviews done: S1 N1-N5 fixed, S2, S3 fixes, S5 and S6 (files in F:/Claude Sessions/handoff/one-interface-doors-review-*.md). Follow-ups filed by conductor 020 (not queued).

## Running (they die if #29 is archived: #29 STAYS OPEN until S3 4/4 reports)
- S3 4/4 agent adfb6384cd1322ddb (Opus): hub #795 main-sync pushed (9603183e), job B (Act view 'Nothing waits' fix at command_shell.py:398-399, failing-first) pending; its report reaches #29 only. Its proof that tree == main + S3's own diff is still to be verified by me.
- MERGE-TRAIN 7/7 local_4d18486c-f008-4ef7-88c6-0bb7bc9e99df (Opus, my chip child, holds ci-novahub): #738 train running.
- #28 local_efc92f9b (S5 3/3 bare pytest) and #27 stay open until their agents report.

## Next
1. When S3 4/4 reports: verify head and proof, retarget #795 to main (gh pr edit 795 --base main), tell 7/7 the head in one send.
2. #792 head cc81a4d5 is READY (DOORS-reviewed, owner-only studio pages); 7/7 was told, trains it after #738.
3. COMMAND_HOME / WORLD_INTELLIGENCE_PAGE / STUDIO_GENERATE flips need their prerequisites first; the Act-view fix must be on main before COMMAND_HOME.

## Owed
Cards open: q346, q208, q294. SUITE TEST-ISOLATION (the flake reddening every hub run) is not queued by the owner. Sends since owner typed: 8 of 10 (a 7/7 STATUS came back queued once).

## Gotchas
Stacked PRs after a squash merge conflict: derive tree = main + the PR's own reviewed diff via merge-tree --merge-base, prove +/- lines equal, record with merge -s ours then read-tree. 7/7 started on Sonnet by default: set Opus.
