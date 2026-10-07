# AUTO-DESKS handoff 002 (NODE · AUTO-DESKS 1/1, local_9345bf47)

2026-10-07 ~08:0x UTC, at ~315k tokens. Desk stays open; successor desk AUTO-DESKS 2/2 finishes.

## Measured live (owner asked "check if its working?")
- Installed: leadfuel-way 0.1.7 at 2026-10-07T04:03:26Z (installed_plugins.json, from 09f59c9);
  cache 0.1.7 hooks.json has the widened matcher.
- The installed hook passes 5 synthetic cases: a router's agent may edit its own worktree, may not edit the
  router's checkout; the router itself is still refused; an agent's move_sessions self and archive are refused.
- Real use since install: the hook's `agents/` state folder (written only by 0.1.7) holds ~23 agents.
  ROUTER #25 and #26 ran desks as background agents (MONEY PHOTO-STRIPE-ISOLATION, INTELLIGENCE
  CC-PHONE-READY 1/2 and 2/2, NODE RUNNER-WAIT 2/2, SURFACE PHOTO-PRINTFUL-AUTO, VAULT HUB-TODO-ANON-STATE,
  DOORS ARM-SENDS-DOORS 3/3, INTELLIGENCE HERO-COUNCIL 1/2): 97 Edit/Write calls succeeded, 0 refused by
  the hook (1 ordinary "string not found" Edit error). One ROUTER #25 agent was refused a session tool on
  `self` (session_tools_refused=1). Agents past 300k got the agent-worded warning, measured on their own size.
- Those agents ran without `isolation: worktree` (no worktreePath in their meta) and took their own
  worktrees (e.g. `.claude/worktrees/cc-phone-ready`), which the 0.1.7 rule allows.
- The formal pilot WAY-POSITIVE-CONTROL has NOT run (no PR for it); the live router use above is a
  stronger measurement than one pilot.

## Left for AUTO-DESKS 2/2
1. Small PR into `way/plugin`: record the above in `docs/AUTO-DESKS.md` "Pilot" (replace "pending").
2. Decide with the router whether WAY-POSITIVE-CONTROL still runs as the pilot or as an ordinary desk.
3. STATUS DONE to the live router (ROUTER #26 local_0185d288 at 07:57Z; re-read `router/current`).
