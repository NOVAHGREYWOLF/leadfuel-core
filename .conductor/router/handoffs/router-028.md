# Router handoff #028 -> #029 (2026-10-07 ~17:05Z UTC, at the 300k guard)

ROUTER #28 is local_efc92f9b-bf92-414c-a977-98109c332b33. Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v269+. Router desk LzmP6QcxmYh9TdvMMjS883. Conductor desk MKAx49RAskZ3cV7f2EkDMF.
Keys: log_28..log_28f, agents_28..agents_28f, agent_reports_28*, blocker_28, clock_28, owed_28*. Newer keys supersede this note.

## Done by #28
Claimed v254. Merged leadfuel-core#35 (GROUP-BY-PROJECT, way 0.1.8, b92f65c57); card q344 asks the owner to install it. Pushed hub one-interface S1, S5 branches (S6 was up). Woke merge train 6/6: #784 #788 #787 landed (gh verified). Cards q343 (law 11, #738 held), q344. DOORS review of S1 read: no blocking finding, N1-N5 to fix before the production flag.

## Running (they die if #28 is archived: #28 stays open until they report)
Agents under #28: S1 3/3 (N1-N5 fixes pushed once to hub #793's branch), S2 2/2 (Focus HUD, base S1 branch), S3 2/2 (console; commits LOCAL ONLY, bundle backup in the sessions handoff folder), S5 3/3 (push + PR #791 body). Reports reach #28 only; #28 copies each into agent_reports_28. Under #27 (also stays open): PHOTO-CLIENT-STORE 3/3, VAULT reader.

## BLOCKER (16:59Z, verified by me)
GitHub answers HTTP 500 to POST actions/runners/registration-token for the hub and leadfuel-core; hub runner containers crash-loop; zero hub runners, so no hub CI: #793 and #791 tests pending/queued since 10:12-10:32Z; #786's train run failed 09:56Z (not read). S3's pushes got 500 too. githubstatus says operational. Watcher in #28 wakes on a runner online.

## Next
1. Wait for runners; then #793 green on its NEW head -> undraft, tell 6/6 (local_866e6aba) S1 first, retarget S2/S3 PRs to main, #790 after #786. COMMAND_HOME production flip only after N1+N2 are fixed and merged (a flags desk).
2. S4 (layers/views) when a slot frees and S2 has pushed. DOORS reviews owed: S2/S3 routes, hero_llm.py (#790), S5 reach send_email gap.

## Owed
Cards open: q208, q294, q343, q344. WATCH follow-up: sessions-desk feeder shows lane only for new-form titles. Archive #27 after its two agents report; holds #24 #25 #26. Sends since owner typed: 2 of 10.

## Gotchas
Board time stamps by agents and by #28 (10:xx to 11:xx) are wrong: a usage pause skipped 6.4 h; use GitHub time. An agent whose own isolation worktree breaks cannot be resumed: start a fresh one. Stopped agents leave ci-novahub tickets: remove them.
