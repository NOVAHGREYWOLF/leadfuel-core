# Router handoff #070 -> #71 (2026-10-19, ~300k, agents still running)

ROUTER #70 = local_8adab0be-c87a-4cd9-b7ff-dc70fb5913a0 (slot way-slot-05, NOT archived: it hosts the background agents below; they die if it is archived or stopped). Conductor 046 = local_259a7d41-316f-422b-93d3-9306c2b5f09b. Launcher local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Predecessor #69 archived. Ids only. State lines are mine: re-read them (gh, git ls-remote, the pages). Build Board A4uS9xn1emqupohdE4DUfV (router/current v597+, router/roster70 has the full log: READ WITH out_dir ONLY). Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q574). Conductor desk MKAx49RAskZ3cV7f2EkDMF.

Program: owner picks 421/431/432 (command center end to end, never stop, all at once, plan defaults). Common brief F:\Claude Sessions\handoff\one-interface-research\COMMAND-CENTER-DESK-BRIEF-COMMON.md. Lander brief LANDER-BRIEF-COMMON.md in the same folder. Door reviews DOORS-REVIEW-<pr>[b].md there.

## Hosting rule (important)
#70 stays open until every agent below has reported, then the successor archives #70 through the gate. Notifications for agents land in #70; #70 forwards one line each to #71. Do not archive #70 early. A new router (#71) opens NEW agents itself.

## PRs (hub NOVAHGREYWOLF/novahub, all drafts unless merged; gh verify)
- Landing now (landers waiting on ci-novahub, FIFO): 896 world intel (ae788b8677bf5b9d2 holds), 895 earned access (aed97472c506c26fa), 893 regions (a984d478fbe1c2520), 894 quests (a95093160bded983a).
- Ready for a lander, not opened: 903 places (DOORS NON-BLOCKING 678c83d7), 891 shell (NON-BLOCKING 88437287), 899 views (fix a2aa28e5 pushed), 900 node door (fix 74855295 pushed; needs a quick re-review of the delta, then land; node half = patch NODE-L2-14-node-half.patch + commit 62693d1 in F:\Leadfuel\.claude\worktrees\node-command-local, owner steps in PR body).
- 3D stack: 889 (NON-BLOCKING 138dce7a; test-gap desk ab5e7ed15dc2bbf3b running), then 898 (5b) and 904 (5c) stacked on it: retarget to main and rebase after 889 lands.
- 905 phone stacked on 891 (review ab0a02f8ff1b53e6a running).
- Blocked: 897 ask-local (BLOCKING: _embed_local proxy/redirect leak; INTELLIGENCE desk a9a5aa7eae983a6bb hardens brain._embed_local in its own PR; 897 merges after), 901 levels (fix desk ab20de6d52f160dc0: header bypass; then re-review), 902 connector card (stacked on unmerged #859, migration 0014 also used by #895 and #859: second to land renumbers), 892 character (fix desk a29508afce8ac7c04: overall trust state must not read live with nothing measured; then land).
- Running: plan 6 gap audit (ac8178b1eabb3deb3).
- CI note: hub pytest is one at a time, FIFO, up to 100 queued; every PR push queues a run. I cancelled runs of heads about to be superseded. A lander's run waits behind all earlier ones.

## Owner steps (card on the Router desk, non-blocking; not yet carded)
895: STANDING_GRANT_ENABLED, release_due runner, alembic stamp 0014. 896: WORLD_INTELLIGENCE_PAGE=1 + feeds. 897: env to turn on (after fix). 900: 4 node steps in the PR body. 901: LEVELS_5_8_OPEN, LEVEL_GATE_ENFORCE (ARMS handoff owed: 5 spokes read the shared table themselves). L2-1 production read needs his typed go in a desk chat. L2-15 deferred (Q23). Views: 22 of 37 views blocked on missing data (card or defer).

## Owed follow-ups
SURFACE desk: pin 'unknown never reads live' in test_command_regions.py (893 medium gap); 894 wording notes (HUD cause, credits sentence, payoff card silent hide); 891 Esc double-handling LOW at Z5/Z6; 896 LOW wording. Report to conductor 046 (STATUS) when the first PRs merge.

## Gotchas
Stop hook false-positives on the word handoff in board writes (said no LAUNCH-REQUEST was owed until now). A ROUTER cannot Edit repo files. Pin ArtifactData if_version. I wrongly told a fix desk the Sentry scrub was in node files; it is hub app.py. Reviews I took on the reviewer's word are marked in each DOORS file. The flaky test_command_screen owner-account-in-platform test: reviewers think it is the documented clock flake; CI on the exact head decides.
