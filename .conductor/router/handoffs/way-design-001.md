# Handoff: way design session -> ROUTER #5 (2026-10-02 ~01:20 UTC)

Session local_5da205d9, `ROUTER · the way: always-on skill design`. It retires on the owner's word ("retire what you need to") and archives itself after this push. Ids only: this is a public repo.

## Done (verified by this session)
- The guard never ran anywhere. The repo hook calls `python3`, which is the Store stub on this PC (exit 49, a silent non-blocking error). User settings.json is `null`. `router` and `handoff` exist only in leadfuel-core; `conductor` and `route-and-spawn` only in novahos.
- `start_session` and `hand_off_to_session` exist in desktop app 2.19675 but are gated off (`side_sessions_off`). No user setting for them was found.
- Owner clicks, 2026-10-02: one router per project; investigate start_session; build the plugin and pilot it; the build desk goes in NODE; this session stays in ROUTER; ROUTER and CONDUCTOR are never desk lanes.

## Opened
- WAY-1, local_12597f42, `NODE · WAY-1 1/1 · leadfuel-way plugin build`, on Sonnet. It builds on branch `way/plugin` from fe04a63 and now reports to ROUTER #5.
- ROUTER #5, local_851d50d8, on Sonnet.

## Not confirmed delivered
Four messages to WAY-1 and one to ROUTER #5 are queued, not confirmed read: the lane fix, the self-archive rule (0df25ff), the report redirect, and the ROUTER #5 brief.

## Next
WAY-1 sends STATUS with a draft PR and the owner's install step. That step changes ~/.claude/settings.json, so it becomes a Router desk card. Then the desktop pilot.

## Gotchas
- A task-card session cannot carry a model, starts at effort `max`, and cannot be detached by the session that suggested it. Check its model with get_session the moment it starts.
- ROUTER #5 confirms that it and WAY-1 survived this session's archive.
