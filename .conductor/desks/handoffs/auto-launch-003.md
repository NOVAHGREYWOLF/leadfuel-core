# handoff: NODE · auto-launch part · 2 final (session local_17329271-af57-469a-a2de-0a9fc6bf1778), 2026-10-13

Supersedes the "Next" list of auto-launch-002. PR https://github.com/NOVAHGREYWOLF/leadfuel-core/pull/41 (base `way/plugin`).

## Done (verified by me)
- Owner set Bypass on `way-slot-01..06` (card q399 A, relayed by ROUTER #51 at 12:29 UTC; ROUTER #50 also relayed it). Proof is mine: six launched runs each reported `permissionMode: bypassPermissions` from their own `get_session` and ended `READY way-slot-NN`.
- Full path on slot 01: model pinned in the slot file (Haiku), `set_session_effort low`, `GO` delivered, the run reported with `send_message` (queued while I was mid-turn, arrived when my turn ended) and ended `PROBE-DONE`.
- Result recorded in `docs/SLOT-LAUNCH.md` ("Bypass end-to-end") and the skill's Limits. Bare `pytest` 579 passed locally before the doc edit; CI decides the head.
- Runs archived: slots 02 to 06 checks, the earlier probes; slot 01's last probe `local_ff39e5c2` is archived after merge. All six slot files are back to idle (no `model:` line, idle prompt, "(idle)" title).

## Owed to the owner (not mine)
- Update the installed plugin to 0.1.11 once #41 is merged and `way/plugin` reaches the marketplace checkout: `claude plugin update leadfuel-way@leadfuel`, then a fresh session.
- Accept that launched sessions show under Scheduled, not in a project group (card q399 context).

## Gotchas
- A slot run's `list_events` shows only visible lines; to read its `get_session` and tool results, parse its transcript under `~/.claude/projects/<project>/<cli session id>.jsonl` with `python -I`.
- A slot launcher must end its own turn to receive a report; a send to a mid-turn launcher is `queued`.
- `set_session_model` and `set_session_effort` apply from the next turn; the model pin in the slot file applies to the first.
