# Router handoff #001 -> #002 (2026-10-01, ~21:50 UTC)

Router #1 = session_01PjWdddCUgWifTFgyqnt7Pe. It reached ~145k tokens during setup (guard fired, hard cap 120k), so it is rotating by its own rule.

## Done
- Skill `.claude/skills/router/SKILL.md` (rules, message protocol, rotation, watchdog), `.conductor/router/CHILD_PROTOCOL.md`, context guard hook + `.claude/settings.json` (soft 90k, hard 120k; smoke-tested at 95k), handoff skill copied from novahos.
- Board doc `router/current` written (ArtifactData on artifact A4uS9xn1emqupohdE4DUfV, version 1). Router #1 tagged `router`, `router:current`, `incarnation:1`.
- Read-only sweep of all 25 non-archived sessions delegated to a background subagent in router #1. Result will reach router #1 as a notification; #1 relays it to you by `send_message`.

## State (verified vs believed)
- VERIFIED: 25 non-archived sessions, 24 idle, nearly all over 100k tokens (cannot be woken for new work). 8 lack the `config:meta-mcp-own-entry` tag (older coordinators, P5-F2, P5-F4, N1-F2 fix) and may have no `send_message`.
- VERIFIED: five-hour window resets 2026-10-02 00:30 UTC; weekly limit resets 2026-10-03 21:00 UTC.
- VERIFIED: a running session reads `used_tokens: 0` about itself; idle ones read true.
- NOT PROVEN: child -> router delivery. Smoke test 1 (session_019VMz6fwDdJ2LzGC3cTuEwd, Haiku) failed because it used the generic `SendMessage` tool, not the MCP `send_message`.
- Routines NOT edited yet, on purpose, until delivery is proven.

## Next (in order)
1. Run Claim (SKILL.md "Rotate", successor steps).
2. Smoke test 2: Haiku child whose prompt names `mcp__claude-code-remote__send_message` and says to load it with ToolSearch `select:mcp__claude-code-remote__send_message`. Check its transcript (list_events kinds user, limit 10) for the tool_result, and that the message reaches you as a turn.
3. If it passes: append the Watchdog block to hourly routine trig_015prRzaktsxeYJLiD7x8G9B and have its pass send STATUS to the router; add "send the report PR link to the router" to nightly trig_01U9CpzgkUWKbLeymJ46qmuA (`update_trigger`, keep the old prompt text intact).
4. Post the first NEEDS YOU block from the sweep digest once router #1 relays it.
5. Ask the owner: (a) standing OK to archive router predecessors (`router/config.archive_predecessors`)? (b) retire the overlapping 4-hourly novahos tick trig_01SXmjamu3JKRDbFyVvvHtGN?

## Gotchas
- ToolSearch for "SendMessage" returns the wrong tool (see above).
- `list_sessions` with 50 rows is ~100KB; `list_events` pages are huge (thinking signatures). Extract with python, delegate wide sweeps to a read-only subagent.
- All incarnations push to branch claude/zealous-heisenberg-tlqil3 (use `outcome_branch`). No PR subscriptions (owner rule).
- Throwaway test session session_019VMz6fwDdJ2LzGC3cTuEwd is an archive candidate (not a plan task).

## Ids
Board artifact A4uS9xn1emqupohdE4DUfV. Hourly tick trig_015prRzaktsxeYJLiD7x8G9B, nightly trig_01U9CpzgkUWKbLeymJ46qmuA, 4-hourly novahos tick trig_01SXmjamu3JKRDbFyVvvHtGN. State branch for the plan: claude/admiring-cerf-k1z6vd (leadfuel-core PR #7).

## POLICY CHANGE (owner, 2026-10-01, after router #2 started): bigger sessions
Owner: weekly usage is ~4% after the reset, plenty of room, make sessions bigger so work gets finished.
- Guard: soft 300k, hard 450k (`.claude/settings.json` env; pull the branch, it applies to new sessions from this checkout). Reuse an idle session under 200k; do not wake one over 300k for new work. Haiku stays under 150k (200k window).
- Project budget raised on the state branch (claude/admiring-cerf-k1z6vd): soft 5M, hard 8M tokens (was 700k/1M, already exceeded at 969k, which blocked new starts such as P9).
- DONE by router #1 (owner said "lift it" and "do anything else before I hit router two"): hourly routine trig_015prRzaktsxeYJLiD7x8G9B updated (own size 200k, nudge over 300k, size policy, model hold removed); nightly trig_01U9CpzgkUWKbLeymJ46qmuA updated (flags sessions over 300k, not 100k; own run size unchanged); state-branch handoff note coordinator-2026-10-01.md no longer says Sonnet/Haiku-only and says handoff at 200k; board docs `router/current` (thresholds 300k/450k) and `router/config` (owner decisions recorded, `archive_predecessors: false`).
- The model hold is LIFTED (owner, directly to router #1). Confirm it to the owner in one line; do not re-ask. Tasks with a `model_pin` (e.g. P9 pinned sonnet) keep their pin.
- 4-hourly tick trig_01SXmjamu3JKRDbFyVvvHtGN has no size or model text, so nothing to edit. It drives the NovahOS plan on novahos branch claude/conductor-done (277 adopted sessions, budget still 100k/150k there, archives only tasks marked done, which nothing marks automatically). Recommendation to the owner: retire (pause) it, the router covers the roster. Owner decides.
- STILL OPEN for the owner (ask once, together, with recommendations): archive router predecessors automatically; retire the 4-hourly tick; bulk mark-done of 238 sessions (irreversible, recommend NOT yet); merges and the Railway cutover; the six coordinator questions (text not retrieved).
- Novahos code still has the old constants (tick.py reuse < 60,000; child_brief "handoff at 100k, hard stop 150k"; context_guard defaults 100k/150k; route-and-spawn 60k/100k). Needs a novahos PR (push access). Start it as a task.
