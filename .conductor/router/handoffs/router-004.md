# Router handoff #004 -> #005 (2026-10-02, ~01:30 UTC)

Router #4 = local session local_fe99f3da, past the 300k cap. The guard hook was never installed for it, so it hands over by note. The owner opens a fresh session and pastes: "You are ROUTER #5. Read .claude/skills/router/SKILL.md and .conductor/router/handoffs/router-004.md, then run the Claim steps." First `git pull --ff-only` the router branch.

## New today (owner, 2026-10-02)
- One skill, `leadfuel-way`, governs every session and all work: user level `~/.claude/skills/leadfuel-way/`, copy in `.claude/skills/leadfuel-way/`, loaded by section 11 of the owner's global CLAUDE.md. This router skill is only the router's part. A router and the conductor do no work; all work is in desk sessions.
- **Router desk** (artifact LzmP6QcxmYh9TdvMMjS883, db `questions`): questions only, one click each. Pull answers with ArtifactData, then write `routed`. **Conductor desk**: the complete task list by desk with full docs; the conductor asks "what next?"; only owner-queued tasks start. **BEING BUILT by CONDUCTOR · plan + task list (local_18eeff8c), which holds a 560-item list: do not build it twice.** Check board doc `router/desks` (private board A4uS9xn1emqupohdE4DUfV) for the URL; ROUTER #4's unrun assignment script is board doc `router/build_conductor_py`.
- Guard hook and settings snippet are staged in the skill folder (`python`, not `python3`). Switching it on is the owner's step.

## Not delivered
Odyssey purge desk (local_27593340) unreachable; its commits are on no remote. The archive-sweep session was unreachable once.

## State (re-read before acting)
hub main 5556c6b. signal #13 and #28 green; the DOORS desk waits for the owner's word typed in its own session. Archive sweep archived 4; never archive Odyssey, A6, MONEY metering, DOORS mail or the world lane until pushed.

## Gotchas
Sends pause after 10 until the owner types. Proof of identity must be readable by the desk (session id plus `list_events`). Plain merges and deploys never go on the owner's list. `gh` times are UTC. Heartbeat is off.
