# router-124-reports handoff (ROUTER #124 · reports, local_dcb9f28b-fb6e-45b9-a201-db9dc9cad788), 2026-11-21 ~3 pm Pacific

(File is router-124-reports.md because router-124.md belongs to the older estate router.)
Source: the owner opened #124 himself; the way-slot-01 brief was ROUTER #118's request to CONDUCTOR 058 (local_b7630866-f2e7-4436-9936-af237cbc5c34). Owner done-criterion: ALL reports work LOCALLY. The estate router is ROUTER #126 (local_3dcfabeb) and holds board router/current `session_id`; REP-R0..R7 are its, I open no R-desk.

## Done (verified by me)
- Claimed board router/current field `reports` (read back); archived #118 (local_8b689a34) through the gate; marked q9123, q9141, q9259 read.
- Posted Router desk card q9555 (options A to D, X; default A; asker_session was me). Nothing is queued for reports, so nothing is started.
- Outlook (metadata only): last command book arrived Nov 19 5:54 am Pacific, none since; the 8 before (Nov 12 to 19) had no attachment and match "PDF engine not installed". Cause unknown.

## Missing books: UNLINKED LEADS ONLY, no conclusion
Leads, none linked to the cause: an "Approve spend: 11 asks, up to $0.82" mail arrived Nov 19 6:45 am Pacific (its preview says nothing runs until answered); Router desk cards q9518 (answer B) and q9319 (unanswered) about Railway; #126's unconfirmed claim that the newest Railway deploy is Nov 10. I read no mail body and did not touch Railway or production.

## Successor: the owner opens routers himself (058 relayed this, unverified by me). No slot is used; slot way-slot-07 was armed then disabled by me before it fired.
Paste into a fresh session:
`You are ROUTER #127 · reports. Invoke leadfuel-way:way and leadfuel-way:router, read .conductor/router/handoffs/router-124-reports.md on claude/conductor-050, re-read live state (gh, git ls-remote, the pages), then continue from "Next". Rewrite only the board router/current field "reports"; session_id, status and next_session_id are ROUTER #126's. Once you are titled, archive your predecessor local_dcb9f28b-fb6e-45b9-a201-db9dc9cad788 if its handoff is pushed and nothing of it is unpushed. Report to CONDUCTOR 058 (local_b7630866-f2e7-4436-9936-af237cbc5c34).`
(#125 and #126 are the estate router's numbers, so reports takes 127; say "reports" when you name yourself.)

## State (re-read before acting)
Hub main was 7c6feb95 at ~2:40 pm (moved from 0a763d29; not from a merged PR as far as gh showed; unread). #1048 head d158d836 is stale. #1102 ahead 2, behind 14. #1121 and #1124 to #1127 are drafts with pytest FAILURE. Branches reports-attach-all 1004f9ad, reports-local-qa bd08dbea, fieldy-local 3e58aa50 exist only in hub worktrees: no push without the owner's word.

## Next
1. Set q9555 `asker_session` to your own id (the wake pass delivers to the asker), pinned. When answered, relay to 058 for the pick record and do what it says.
2. Open no desk until the owner queues one. Missing books: read-only checks only; Railway and production reads need the owner's word.

## Owed
Owner answer on q9555 and #126's q9551 (PR 1102). My books message to #126 is queued (e20dc693); 058 got its copy (1be250df).

## Gotchas
router/current `status`, `next_session_id`, `session_id` are the ESTATE router's: on rotation write only the `reports` field. Picks are lane-keyed (WATCH~REP-R0). ArtifactData list/query floods: use out_dir and parse locally. gh through Start-Process splits quoted args.
