# Heartbeat routine prompt (paste verbatim into create_trigger)

name: Router heartbeat (hourly) | cron: 0 * * * * | initiation: human_request | persistent_session_id: <the live router session>

```
HEARTBEAT (hourly; the owner approved this wake-up on 2026-10-01). Do ONE sweep pass, then stop. Follow the router skill (.claude/skills/router/SKILL.md, section "Intake: PULL first") and its rules.
1. Sweep: for each non-archived session in board doc router/roster, call get_session and read external_metadata.post_turn_summary {status_category, status_detail, needs_action}, status_bucket and used_tokens (valid when idle). If router/roster does not exist yet, build it from the ids in the newest handoff and the sessions tagged project:leadfuel-reports. Delegate to a read-only subagent if there are more than about 8 sessions.
2. Update router/roster and router/inbox (pin if_version).
3. Anything newly need_input, blocked, or completed goes into one NEEDS YOU block with a recommendation each. Use PushNotification once, batched, only if something new actually blocks work.
4. Owner rules still hold: never merge, never deploy, never force-push, never print secrets, archive only under the archive gate, and NEVER bulk mark-done (owner, 2026-10-01).
5. If your own context is past the guard's soft cap (300k), rotate per the skill instead of continuing.
6. If nothing changed since the last sweep, reply with the single line "no change" and stop. Do no build work.
```
