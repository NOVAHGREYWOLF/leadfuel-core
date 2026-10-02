# Router handoff #004 -> #005 (2026-10-02, ~01:15 UTC)

Router #4 = local desktop session local_fe99f3da. It is past the 300k soft cap. The context guard hook was never installed for it (this worktree was cut from main; the user-level settings file is empty), so nothing told it to rotate. It hands over by note. Local mode: no create_session. The owner opens a fresh session and pastes: "You are ROUTER #5. Read .claude/skills/router/SKILL.md and .conductor/router/handoffs/router-004.md, then run the Claim steps."

## Owner's structure (2026-10-02)
- Router desk = questions only. Artifact LzmP6QcxmYh9TdvMMjS883 (db: questions, work). 23 questions: steps and decisions, each with a default. Pull answers with ArtifactData; after acting write `routed: {at, note}`. Delete the `work` collection and the Your queue and All tasks tabs once the Conductor desk exists.
- Conductor desk = the complete task list, held on the conductor, grouped by desk like the sidebar, full documentation per task. The conductor asks "what next?"; the owner chooses. **NOT BUILT.** The router builds nothing: delegate it to CONDUCTOR · plan + task list (local_18eeff8c), or build the first cut and hand it over.

## Unfinished build
Build script saved in board doc `router/build_conductor_py` (board artifact A4uS9xn1emqupohdE4DUfV, private). Written, never run. Inputs: all 135 board tasks (ArtifactData list with out_dir), plus about 45 desk-owed items, plus the desk files. Design: one doc per desk (`desks/<id>` with a `tasks` map), `next/<id>` for proposals, no tasks chosen by default.

## Not delivered
Odyssey purge desk (local_27593340) and the archive-sweep session were unreachable by name. The Odyssey desk has commits on no remote.

## State (re-read before acting)
hub main 5556c6b. signal #13 and #28 green, wait on the owner's token and go-word typed in the DOORS desk session. Archive sweep archived 4; never archive Odyssey, A6, MONEY metering, DOORS mail, world lane until pushed.

## Gotchas
Messaging pauses after 10 sends until the owner types. A proof of identity must be reachable by the desk: point at the session transcript, not the private board. Merges and deploys never go on the owner's list (deploy-config PRs are the exception). gh times are UTC. Heartbeat is off.
