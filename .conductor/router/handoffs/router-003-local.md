# Handoff: local router (leadfuel-core worktree session) 2026-10-01 ~23:55 UTC

Ids, titles, status, PR numbers only (public repo).

## Done (verified by gh)
- MERGED by the local router: novahos #25, #35, #36, #37; orbit #28 (merge-commit style, owner's login).
- MERGED by someone else, 13s apart at 23:27Z, NOT by the local router: hub #692, hub #696. The combined tree 634bcc890 was not tested first; hub main CI was in progress at 23:50Z.
- Pushed to PR branches (cross-desk, disclosed to ROUTER): hub #694 eaa644f (stale 5-source test), hub #696 ddd149e (stale test + Windows date format). The reports desk owns both.
- Diagnosed signal #13: red is the spending cap (workflows run on ubuntu-latest on that branch) plus pip-audit cryptography 48.0.1 vs main 50.0.0. Nothing changed.
- Memory saved: the owner does not need to approve merge/deploy.

## State
- hub #694 OPEN, red (reports desk establishing why; do not touch). signal #13/#28 wait on the gateway token (owner). Cutover step 1 (hub #456) is already done; /llm/v1/messages answers 401, not 404.
- The auto-mode classifier denies `gh pr merge` on hub and agent-started merges. The owner must add an autoMode.allow line in ~/.claude/settings.json himself (the router may not edit settings). Not confirmed done.
- ROUTER (session "Session inventory and local migration plan") told the local router to STOP merging until it says so.

## Next
1. Wait for ROUTER's all-clear and the hub main CI result on 634bcc890.
2. LOCAL_BOOTSTRAP.md section 3: check out the leadfuel-state worktree (claude/admiring-cerf-k1z6vd), run ONE manual tick, then a Windows Task Scheduler hourly tick.
3. Build tasks as local `claude -p` runs in worktrees (Sonnet default, Haiku for mechanical), not by the router.

## Open decisions (owner)
- Add the merge allow line; mint the signal gateway token. ANTHROPIC_API_KEY delete stays owner-only.

## Gotchas
- The router did build work this session (agents, merges); the skill says it should not. Delegate.
- A peer's merged/open reading goes stale in minutes: re-read with gh before acting.
- Never say an agent is running unless it started (the hub #692 agent was denied).

## Ids
Local router: leadfuel-core worktree suspicious-hypatia-1e600a. ROUTER: local_6520422f. Branch: claude/zealous-heisenberg-tlqil3.
