# Router handoff #072 -> #73 (2026-10-19 ~07:50Z UTC, ~300k, 6 landers still running)

ROUTER #72 = local_47411781-90af-470d-93c6-b310a287fd12 (slot way-slot-04, NOT archived: it hosts the agents below; they die if it is archived or stopped). Predecessor #71 archived by me through the gate. Conductor 046 = local_259a7d41-316f-422b-93d3-9306c2b5f09b. Launcher local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Ids only. State lines are mine: re-read them (gh, ls-remote, board). Build Board A4uS9xn1emqupohdE4DUfV: router/current (get with out_dir ONLY), router/roster72 (full log, small, safe: read it first). Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q576), Conductor desk MKAx49RAskZ3cV7f2EkDMF.

Program: owner picks 421/431/432 (command center end to end, all at once). Briefs in F:\Claude Sessions\handoff\one-interface-research\ (LANDER-BRIEF-COMMON.md, COMMAND-CENTER-DESK-BRIEF-COMMON.md, DOORS-REVIEW-<pr><letter>.md).

## Hosting rule
#72 stays open until its agents report; successor archives #72 through the gate after. Running (report to #72): LANDER-900 a45ce26c7dbc98ada (hub #900 @7977f93e, holds or is next for ci-novahub), LANDER-909 a6438bc67e8f4f689 (#909 @9354457a), LANDER-905 a5784f7d1aa0fe4b0 (#905 @f8e289cd), LANDER-897 acde4168e186ccb51 (#897 @9736103a), LANDER-904 a45e8c860b2e12604 (#904 @853ad352), LANDER-910 a0f4da3a1c3239c08 (#910 @d0f81587). They queue FIFO on F:\Claude Sessions\.locks\ci-novahub.wait; when one reports DONE, WAKE THE NEXT BY AGENT ID with SendMessage (landers cannot reach each other by name). Stale tickets of merged PRs (907, 899, 898, 906, 901) are ignored, never reaped.

## Landed this shift (gh verified by me): hub #891 17b14f63, #903 36423250, #892 55c9d252, #907 9977b5b8, #899 c4a36aaf, #898 2a4cf515, #906 1bd843a7, #901 4286e1e6 (main = 4286e1e6 at last read).

## Open, not landing yet
- PR #911 (NODE part 10, head 5e002712, draft): CI runner has NO node, so ~377 node-gated tests SKIP in CI and the count guard counts skips as ran. #911 adds setup-node + a --forbid-skip guard. It changes the test workflow, so it needs a full local bare pytest (heavy lock, WORK_QUEUE.md) AFTER the lander queue drains and AFTER #910 lands; then undraft, push without [skip ci] inside a ci-novahub hold, merge on green. Landing early turns main red. I did not read #911's diff beyond file list; DOORS-lane review not done.
- #902 stacked on unmerged #859, not landable. 908 (regions unknown pin, 06d88664) has no door review; lander must read the diff; not opened yet.

## Owed (no owner pick; not started)
ARMS handoff for 5 spokes (901 readiness board): conductor filed it UNQUEUED. LOWs: 909 arrow keys behind inspector, 909 credits wording (nonexistent flag), 909 layer-reading-0 pin, 900 PR body says 200 not 403, 892 panels.js:379/391 test, 897 screen-side pin of 907 loopback + Esc stops speech, 899 V04/V05, 904 clearing-mutant text pin. Views part 2 (22 of 37 views blocked on data). L2-1 needs his typed go. q574 (flag switches, default B) and q575 (embed non-loopback, default A) cards are open.

## Gotchas
Handoff note's claims were wrong once (no 899 delta review): check each verdict file covers the head before opening a lander. Stop hook false-positives on the word handoff in board writes. ArtifactData get on router/current WITHOUT out_dir dumps ~25k tokens. Cancel superseded pending test.yml runs (gh run cancel) so the single-concurrency queue moves. A lander cannot wake its successor: wake by agent id.
