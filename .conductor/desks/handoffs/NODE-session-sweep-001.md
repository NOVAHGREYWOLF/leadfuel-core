# Handoff: NODE · session grouping + archive sweep (desk), 2026-10-06 ~02:00Z

Session local_201db653. Branch claude/zealous-heisenberg-tlqil3 (draft PR #8, main merged in at c3196ff for CORE-CI). Ids and titles only.

## Done (verified by me via tools unless marked)
- Sidebar: CONDUCTOR group created. Only 3 of 127 non-archived local sessions are ungrouped, all routine runs (2 "Merge desk refresh", 1 "WATCH · etg.ai Resend verification"); the app refuses to group routine runs.
- Archived (gate checked each): ROUTER #3, SURFACE TheCabbys, the apex-cert routine run, INTELLIGENCE debt signal fix.
- Child local_ff6f10b8 (cloud cleanup) finished 10-03 and is archived. By its own report (unverified by me) it archived 3 cloud sessions (WARDEN, P5-F2, Gateway vendor-host) through the claude.ai API; P7 and P5-F4 stay active; P8 unarchive was refused by the classifier, the owner's call.
- Owner model recorded in global CLAUDE.md section 10 and memory: one conductor (no work), routers per project (no work), desks do the work.

## State (list_sessions 10-06 02:00Z; re-read before acting)
127 non-archived, 71 running, 56 idle. CONDUCTOR holds two sessions titled "CONDUCTOR · system build" (083bdfe0 idle since 10-03, has a worktree; f999aa65 newer); the rule is exactly one. ROUTER group has 8 (#11 #12 #13 #14 #18 #20 #21 #22); idle: #11 #12 #14 #18 #21. ARMS session local_57b8a031 has no lane prefix.

## Next
1. Read-only gate audit of the 47 idle desk sessions (regenerate: list_sessions, idle, not router, conductor or routine run; 4 auditors split by group). Gate: PR really merged (gh), final report or DONE, handoff, nothing unpushed (git ls-remote). Archive one at a time, only passers. Skip desks idle under an hour: their router is still reconciling.
2. CONDUCTOR duplicate: archive 083bdfe0 only if f999aa65 is live, its handoff is pushed and nothing is unpushed in 083bdfe0's worktree.
3. Retitle 57b8a031 to "ARMS · Build hub verb POST /api/idea/evaluate".
4. Archive finished "Merge desk refresh" runs (owner-approved routine, every 15 min).
5. Idle routers: find each predecessor and successor from handoffs on main; archive only a pushed predecessor with a live successor.

## Owed
Owner: WATCH Resend run (no final report); P8 unarchive; ROUTER lineage. Undelivered: to ROUTER #4 (queued 10-02) and local_ff6f10b8 (queued, session since ended).

## Gotchas
list_sessions limit 500 is 73k chars and saves to a file: parse with PowerShell ConvertFrom-Json. The PR badge lies (#8 is this branch for any session in this checkout). Cloud and Remote Control rows are unreachable by sidebar tools.
