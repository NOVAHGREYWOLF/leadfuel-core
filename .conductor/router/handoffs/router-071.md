# Router handoff #071 -> #72 (2026-10-19, ~300k, 4 agents still running)

ROUTER #71 = local_64df054f-bf33-4516-9280-61c5abac4141 (slot way-slot-06, NOT archived: it hosts the agents below; they die if it is archived or stopped). Conductor 046 = local_259a7d41-316f-422b-93d3-9306c2b5f09b. Launcher local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. #70 archived (gate met). Ids only. State lines are mine: re-read them (gh, git ls-remote, pages). Build Board A4uS9xn1emqupohdE4DUfV: router/current (read with get is huge: use out_dir ONLY), router/roster71 (full log, small, safe), router/roster70. Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q576). Conductor desk MKAx49RAskZ3cV7f2EkDMF.

Program: owner picks 421/431/432 (command center end to end, never stop, all at once). Briefs: F:\Claude Sessions\handoff\one-interface-research\ (COMMAND-CENTER-DESK-BRIEF-COMMON.md, LANDER-BRIEF-COMMON.md; DOORS-REVIEW-<pr>[b].md).

## Hosting rule
#71 stays open until its agents report; successor archives #71 through the gate after. Agents running (report to #71): LANDER-891 ab4f62daa04e1ad3b (hub #891 shell, head 88437287, holds ci-novahub), LANDER-903 a1aee2aeea2e71b8e (#903 places, queued behind 891), DOORS part 19 aa76eaebce789fa52 (reviews #898 at head 107d51d1 and #904), SURFACE part 34 a76ea05842332083a (rebasing #904 onto rebased 5b, one force-with-lease). Their results land in #71: it forwards one line each to the successor.

## Landed (gh verified by me): hub #896 1397ea2e, #895 917633d1, #893 a8389bbb, #894 6d2167a0, #889 a51d44ab (main = a51d44ab at last read).

## Queue (ci-novahub, FIFO, one lander per PR, tickets named 2026101xTxxxxZ-LANDER-<pr>--...; lander merges main in, CI pytest success on its head, squash --match-head-commit)
Next to open as lock frees: 899 views (a2aa28e5, delta review NON-BLOCKING), 892 character (9acb5bce, DOORS-REVIEW-892b NON-BLOCKING), 900 node door (45f58ce0, 900b NON-BLOCKING + Sentry scrub fix), 907 embed hardening (c906cfc2, NON-BLOCKING) then 897 ask-local (merges AFTER 907; needs main merged in), 906 plan 6 (6375d45b, NON-BLOCKING + fixes), 901 levels (fa0a5266, 901b NON-BLOCKING + flake fix), 908 regions unknown pin (06d88664, no door review, one-line render fix; lander reads the diff). 898 (5b) rebased head 107d51d1 base main: land after DOORS 19 verdict. 904 (5c) stacked on 898: after rebase + verdict, retarget to main once 898 lands. 905 phone (93ca67fc, NON-BLOCKING) stacked on 891: retarget after 891 lands. 902 connector card stacked on unmerged #859 (migration 0014 also in main via 895: #859 must renumber); not landable.

## Owed
Follow-up desk(s): 894 wording notes (HUD never-computed wording, credits cell sentence, payoff card silent hide, words(q.cost) harness case); 892b LOW panels.js:379/391 behaviour test; 891 Esc LOW; 896 LOW wording. ARMS handoff owed (5 spokes read shared entitlement table; 901 readiness). Views part 2: 22 of 37 views blocked on missing data (card or defer). L2-1 NEEDS HIS TYPED GO. L2-15 deferred. Cards posted: q574 (owner switches 895/896/897/900/901, default B), q575 (embed non-loopback, default A). Report to conductor 046 as PRs merge.

## Gotchas
Stop hook fires false positives on the word handoff in board writes and the folder name. ArtifactData get on router/current WITHOUT out_dir dumps ~25k tokens: always out_dir. Every PR push queues a test.yml run (one at a time): cancel pending runs of heads about to be superseded (gh run cancel). A ROUTER cannot Edit repo files. archive_session refuses while a finished agent is still registered live.
