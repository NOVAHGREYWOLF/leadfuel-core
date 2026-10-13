# Router handoff #004 -> #005 (2026-10-02 00:57 UTC)

Router #4 = local session local_fe99f3da, retired by note: past 300k and the guard hook was never installed for it. First `git pull --ff-only` the router branch. The owner pastes: "You are ROUTER #5. Read .claude/skills/router/SKILL.md and .conductor/router/handoffs/router-004.md, then run the Claim steps."

## Owner structure (2026-10-02)
- Skill `leadfuel-way` governs every session and all work (user level `~/.claude/skills/leadfuel-way/`, copy in `.claude/skills/leadfuel-way/`, loaded by section 11 of the owner's global CLAUDE.md). Another session, "ROUTER · the way: always-on skill design" (local_5da205d9), works on the same subject: confirm it extends `leadfuel-way` and does not duplicate it.
- **Router desk** (artifact LzmP6QcxmYh9TdvMMjS883, db `questions`): questions only, 25 live (Q22 withdrawn). Pull answers with ArtifactData, then write `routed`.
- **Conductor desk**: the complete task list by desk. BEING BUILT by CONDUCTOR · plan + task list (local_18eeff8c); URL goes in board doc `router/desks` (private board A4uS9xn1emqupohdE4DUfV). Do not build it twice.
- The guard hook and a settings snippet (`python`, not `python3`) are staged in the skill folder. Switching it on is the owner's step.

## Open
Odyssey purge desk (local_27593340) was unreachable; its commits are on no remote. The cloud cleanup session (local_ff6f10b8) archived FIN-1 and ROUTER #2; owner questions Q7, Q24, Q25 and Q26 came from it.

## State (re-read before acting)
hub main 5556c6b. signal #13 and #28 green; the DOORS desk waits for the owner's word typed in its own session. Never archive Odyssey, A6, MONEY metering, DOORS mail or the world lane until pushed.

## Gotchas
Sends pause after 10 (8 used). A proof of identity must be readable by the desk (session id plus `list_events`). Plain merges and deploys never go on the owner's list. `gh` times are UTC. Heartbeat is off.
