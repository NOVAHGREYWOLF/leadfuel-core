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
