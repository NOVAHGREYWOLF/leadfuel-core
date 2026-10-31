# Autopilot for the app agents: one-page spec (WAY-AUTOPILOT-1, code side)

Status: SPEC ONLY, nothing built. Owner, 2026-10-30, CONDUCTOR 055 chat: "we should have something
like that inside our code and in our skill, a mode, fully auto, no questions, MVP". The skill side
is `plugins/leadfuel-way/skills/autopilot/` (0.1.16). This page is the same mode for the home node
and one-app agents. Owning desks build it; this page names no file outside this repo as changed.

## The rule it rests on
The Command Center rule (`F:\Leadfuel\home-node\25-The-Command-Centre.md`): **a board proposes; the
approval queue is the only door.** In autopilot an agent may do anything that stays on the machine
and is reversible. Everything else is a row in the hub's approval queue (`pending_action`,
`models.py` class `PendingAction`: status pending -> approved -> executed | rejected | failed), and
nothing executes a row but an owner approval. Autopilot adds no second door and no bypass.

## Objects
- **GoalBrief** (one per goal): `goal_id` (the existing column on `pending_action`), the owner's
  words with source, `mvp` (checkable lines, each with its proof kind), `may_decide` (kinds of
  decision the agent takes alone, each with its rule), `allow_egress` (kinds the owner allowed at
  switch-on; empty by default), `expires_at` (7 days default, 14 max), `approved_by` (the approval
  row that switched it on). Same sections as `skills/autopilot/GOAL_BRIEF.md`.
- **AutopilotDecision** (append-only): `goal_id`, `at`, `agent`, `what`, `why`, `brief_rule`,
  `reversible`, `outcome` (`decided` | `queued:<pending_action id>` | `denied:<gate>`). Every
  autonomous decision writes one; the MVP report is this list.

## The loop
1. Switch-on is itself a `pending_action` (`kind = autopilot.on`, params = the brief). Only its
   approval sets the brief live. `autopilot.off` needs no approval and wins immediately.
2. First act: a checkpoint row (`kind = autopilot.checkpoint`: plan, MVP, decisions it will take
   alone, "say stop if wrong"). The agent proceeds without waiting; a rejection is `off`.
3. Each step: classify the intended action (below). Local and reversible: do it, log a decision.
   Otherwise: enqueue a `pending_action` with `goal_id`, `source_app = "autopilot"`, log
   `queued:<id>`, continue with work that does not depend on it.
4. Digest: one notification per milestone or gate batch, never per row. At MVP: stop, attach the
   demo link and the decision list, switch off.

## Classification (the hard gates are code, not prompt)
One function, `autopilot_gate(action) -> local | queue | refuse`, called by the executor before any
side effect, so an agent cannot talk past it:
- **Always `queue`, never allowable:** spend, credentials, sends and posts, deploy configuration,
  downloads, permission or settings changes, irreversible steps, and changes to the brief itself.
- **`queue` unless in `allow_egress`:** anything else that leaves the machine (Law 9: free paths
  such as webhooks and posts count, a cloud fallback is never automatic).
- **`local`:** reads of local data, writes inside the agent's own workspace, drafts that nothing sends.
- Unknown action kind: `queue`. A gate that cannot classify does not pass.

## Stops
Weekly all-models usage >= 88%, or unknown, or older than 6 h: no new step starts (the queue still
accepts rows). Context at the handoff cap: the normal handoff, the brief and decision log carry over.
Expiry: off. Every stop is a decision row.

## Not settled (owner)
Where the weekly usage figure is read from; whether the board (claude.ai) and the queue (hub) count
as leaving the machine for the mode's own cards; the trial project.

## Tests the owning desk writes
Each hard-gate kind returns `queue` even with every `allow_egress` set; an unknown kind returns
`queue`; `off` beats a live brief; an expired brief is off; usage unknown refuses a new step; no code
path executes a `pending_action` without an approval row.
