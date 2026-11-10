# router-118 handoff (ROUTER #118 · reports, local_8b689a34-59b5-465e-8b33-a5821bbb557e), 2026-11-10 ~3 pm Pacific

Source: owner via CONDUCTOR 058 (local_b7630866-f2e7-4436-9936-af237cbc5c34): "Do it all. You choose. Let's keep going" and "the locks are not real ... we need the train more efficient"; owner card q9259 A (batch train + 15-minute lock timer). Done-criterion: ALL reports work LOCALLY. Re-read all state; do not trust these lines.

## Merged on hub main (gh-verified by me)
#1042 c823059f, #1045 374c30d7 (#710 closed), #1052 52d42c9c, #1046 d86bda7a, #1047 64199c46.

## Open
- #1048 head 5afaf6d4 (fix for spend-names guard, ledger spoke): tests run 42920052084 pending. When pytest = success on EXACTLY 5afaf6d4 and main still 64199c46: take ci-novahub only if FREE (own tickets INTELLIGENCE-reports-part-6 / -part-2), `gh pr merge 1048 --squash --match-head-commit 5afaf6d4d30cd05eccc1d0bccf3581966591eccb`, release, message the head desk by name (undeliverable, expected). Worktree hub .claude/worktrees/land-1048.
- Draft PRs, do not touch: #1097 visual-4, #1098 cmdbook, #1100 schedule, #1101 fieldy-quality, #1102 reports-pdf-engine (DEPLOY CONFIG, owner looks first, never in a batch).
- Local-only branches (hub worktrees): reports-attach-all (19 sources offline, dry-run email, sends nothing), reports-local-qa (mail time fix c24b80c7, self_report fix bd08dbea), fieldy-local @3e58aa50 (local tier + 4-pass write-up; oss_router.py change needs DOORS ack), arms/mcp-guide-memory-tools @7368e47, arms/mcp-fieldy-digest-coverage @1b1cf06 (novahub-mcp). Push only when the owner/058 orders it (058 earlier: no new hub pushes until the queue drains; superseded for train work).

## Owed
- MIN_TOOLS 106 in .github/workflows/test.yml is NODE's (058 handed it over).
- Flaky tests/test_decision_shape.py::test_measuring_a_large_draft_is_bounded_and_still_right fails main's post-merge runs: queued as a DOORS task by 058; not mine.
- Router desk cards: q9121-q9123 (N15 decisions), q9271 (skip head ticket; 058 chose A), q9259 answered A. Owner artifact https://claude.ai/artifact/3QjsgS2KSLbwTKnrP6tXJe is stale (shows 11 drafts, none merged): republish with merged list.
- Archive FIELD reports part 1 (local_25b163fd-5b53-41ad-ad28-56338e3ece7a) only after #1101 lands; INTELLIGENCE reports part 3 (local_ced7b0a4-6a5f-455b-a278-792a5d25de12) is idle, archive through the gate.
- Attachment train (REPORTS-ATTACH-ALL): the one full-set send to the owner (q9001 A) needs files passing on stored data and a dry run, then a desk send; MASTER_ATTACH_REPORTS stays off until then. Token guide: F:\Claude Sessions\desks\handoffs\SURFACE-reports-part-2-token-guide.md.

## Gotchas
ci-novahub head ticket INTELLIGENCE-KNOWLEDGE-PROPOSE-1of2 has no reachable desk (message_id ee3c7ffe-aaf9-4dee-8631-afd0b371471f undelivered); never reap tickets. Card ids collide: use `set` with a high id. gh calls time out under load: background them. Stop hook misfires on the word "handoff" in text.
