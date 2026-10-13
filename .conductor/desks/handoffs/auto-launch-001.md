# handoff: NODE · auto-launch part · 1 (session local_ceaeea09-2a01-4b39-aaf9-e5102fc72ffe), 2026-10-13

Owner ask (chat, then "go"): sessions that need a new session must start it with no click.

## Done
- Branch `way/launch-slots` (base `way/plugin`): plugin 0.1.11. New skill `leadfuel-way:launch`; router, handoff, conductor, way, desk, new-project point at it; hook `is_successor` accepts a `way-slot-NN` `scheduledTaskId` in place of a group; `docs/SLOT-LAUNCH.md` (measured, on trust, not verified).
- Six idle scheduled tasks `way-slot-01` to `way-slot-06` exist (manual only, outside the repo, in `~/.claude/scheduled-tasks`).
- Probes cleaned up: `launch-probe-1` deleted, three probe sessions archived, slot 06 reset to idle.

## State (verified by me unless marked)
- 510 plugin tests pass locally. CI not yet run on the head. Draft PR against `way/plugin`.
- Measured: run_scheduled_task starts a session with no click; re-run after update_scheduled_task gives a new session with the new prompt and title; model change and message by id work; cannot be grouped; a fresh slot starts in `default` and a default run cannot send a message.
- NOT run: the `READY`, `GO`, report path. It needs a slot in Bypass. `notifyOnCompletion` unverified.

## Next
1. Owner sets Bypass on `way-slot-01..06` in the app (once).
2. Launch one harmless brief into a Bypass slot as `leadfuel-way:launch` says; confirm `READY`, `GO`, the report, and whether a Bypass run can send. Record it in `docs/SLOT-LAUNCH.md`.
3. CI green on the head SHA (job `pytest`), merge main into the branch if needed, then merge the PR into `way/plugin`.
4. Owner updates the installed plugin to 0.1.11 (pull the marketplace checkout, `claude plugin update leadfuel-way@leadfuel`), fresh session.

## Owed / not delivered
- Findings message to ROUTER #48 (local_e4ee0816-7d58-4bfd-a102-f02d188116af) came back queued, message id fc5dcc8c-bf1e-4afd-8b3e-58f89a23fc8a; not confirmed read. Same content is in `F:\Claude Sessions\handoff\NODE-auto-launch-part-1-findings.md`.

## Gotchas
- `set_session_model` applies from the next turn, so the first turn must be short.
- A Bash `cd` changes the session working directory; a heredoc with an apostrophe fails in the Bash tool, use Write.
