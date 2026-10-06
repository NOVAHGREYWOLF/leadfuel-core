# AUTO-DESKS handoff 001 (NODE · AUTO-DESKS 1/1, local_9345bf47)

2026-10-06 ~02:5x UTC. Desk stays open (owner rule); stopped at ~285k tokens.

## Done (verified with gh)
- leadfuel-core #27 merged 02:34:31Z into `way/plugin` as 0de31df: way plugin 0.1.7. A subagent's hook
  events carry the parent's session_id/transcript_path plus `agent_id`; 0.1.7 judges agents as agents
  (worktree-aware write rule for a coordinator's agent, no archive / no `self` move or title from an
  agent, guard on the agent's own transcript, agent state kept apart). Router, desk and way skills updated.
- Design note with the measurements and a paste-ready pilot call: `docs/AUTO-DESKS.md` on `way/plugin`.
- Bare pytest at a017366: 307 passed. No CI exists on `way/plugin` (zero checks; #17 and #18 the same).

## Not done: the live pilot
- Proposed pilot: NODE · WAY-POSITIVE-CONTROL (queued, rank 206) run by the router as a background agent,
  model sonnet (route.py). Call and prompt in `docs/AUTO-DESKS.md`, "The pilot call".
- Blocked on: (1) the owner installs 0.1.7 (`git -C C:\Users\novah\leadfuel-way-plugin pull --ff-only`,
  `claude plugin update leadfuel-way@leadfuel`, then a fresh router session; banner must read 0.1.7);
  (2) the router's go, which may need the owner's exception to close-first.
- Under 0.1.3 the agent's first Edit should be refused (replayed, not yet seen live in a router).
- After the run: record the agent's STATUS and the notification's token/duration line in
  `docs/AUTO-DESKS.md` (new small PR into `way/plugin`), then STATUS DONE.

## Follow-ups (not queued)
Doctor synthetic agent step; SubagentStop handoff gate; router refuses rotate/archive while agents run.

## Gotchas
- GitHub GraphQL timed out repeatedly on the slow link; `gh api` REST calls worked.
- The probe agent's worktree was auto-removed (no changes). Nothing unpushed on `way/auto-desks`.
