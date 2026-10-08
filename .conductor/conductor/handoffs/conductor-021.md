# Handoff: CONDUCTOR · system build, 021 (2026-10-08 ~06:30Z UTC, rotating at ~300k)

Ids only (public repo). This session: local_1ff6c57b-dacc-45db-9914-e0059e65044c, branch claude/conductor-021. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current). Tick cron a9d9f918 was CANCELLED by 021 before rotating: re-create at minutes 13,43 (prompt as in 013's note; cursors below). 021 stays open, does nothing, until 022 is titled and filed and archives it.

## Done (verified by me unless marked)
- Archived 020 (handoff c72665a pushed, worktree clean). Kept conductor 005 (local_083bdfe0) and ROUTER #11, #12, #13.
- Owner q346=B then q347=A (01:09:10Z): desk title is LANE · <project> part · n. Picks NODE~WAY-TITLE-REWORD-B and NODE~GROUP-BY-PROJECT marked done. I read installed_plugins.json: leadfuel-way 0.1.9, sha da1488ac == origin way/plugin. NOT observed: a fresh session's 0.1.9 banner (022 is that session: check it).
- Filed UNQUEUED (reviews read in full by me; PROVED lines are the reviewers', not re-run): DOORS SPEND-GATE-ACCOUNT-CAP-FAILOPEN (N11, a real gate defect, I suggest the owner queue it), SURFACE ONE-INTERFACE-HELD-ASK-NOTES, detail added to SUITE TEST-ISOLATION.

## State (re-read before acting)
- Board router/current v338: session_id local_d83413b9 (ROUTER #32), status rotating; #33 not live at 06:23Z (owner pastes). #31 archived by #32; #30 local_7ae54716 may still be open.
- Hub main 4a9c3c28 (#798 places gate, merged 06:00:35Z), tests/lint/security green (gh, me). #738, #796, #797 merged earlier.
- Cursors: cards answered_at > 2026-10-08T01:09:10Z (none since); picks decided_at > 2026-10-07T23:23:16Z (none since).

## Next
Run the tick. When ROUTER #33 is live, brief it only if something is new.

## Owed
- Owner: cards q208, q294, q348, q349 open. Not queued by the owner: SUITE TEST-ISOLATION, COUNSEL PHOTO-STORE-WORDING, INTELLIGENCE WORLD-FLAG-ON-PREREQS, DOORS STUDIO-GENERATE-PREREQS, ARMS REACH-SEND-EMAIL-DESIGN, the two new tasks above.
- Watch: #32 log_32c says a serial bare pytest on the #797 branch failed 3, one new and unread (tests/test_source_snapshot.py::test_it_agrees_with_inspect_exactly). If #33 confirms it on main, file it as a SUITE follow-up.
- Sends: 4 to routers, all delivered.

## Gotchas
- gh hangs: wrap in Start-Job with a 40s cap and quote --json fields. Query ArtifactData with where on answered_at/decided_at, not list. router/current is ~210 KB: get with out_dir.
- Primary cwd follows cd into a worktree; return to the main checkout. Use Write for files.
