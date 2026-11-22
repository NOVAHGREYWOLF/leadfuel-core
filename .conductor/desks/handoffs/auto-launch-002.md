# handoff: NODE · auto-launch part · 2 (session local_17329271-af57-469a-a2de-0a9fc6bf1778), 2026-10-13

Continues auto-launch-001. Branch `way/launch-slots`, draft PR https://github.com/NOVAHGREYWOLF/leadfuel-core/pull/41 (base `way/plugin`).

## Done this session (verified by me unless marked)
- Titled and filed (group `auto-launch`); archived part 1 (`local_ceaeea09`) after its handoff was on the remote and its worktree was clean (0 ahead, 0 behind).
- Slot probe: `way-slot-01` launched with the skill's slot block ended `SLOT-NOT-BYPASS way-slot-01 mode=default`, read with `list_events`. **The owner has not set Bypass.** Run archived.
- Measured: a `model:` line in a slot's `SKILL.md` frontmatter sets the run's model (Haiku line gave a Haiku run; the same slot without it gave Sonnet); `update_scheduled_task` on title, description and prompt leaves the line alone; an `effort:` line is ignored. Source of the idea: WATCH's ROUTINE-NO-PROMPT-001 handoff (on trust for the permission-mode claim: a routine's mode is per-task and no scheduled-task tool sets it; I also checked that `create_scheduled_task` has no such field).
- Skill `launch` step 4 now pins the model in the slot file on every launch; step 5 sets effort and checks the model; Limits and `docs/SLOT-LAUNCH.md` record it; one new test. Bare `pytest` locally: 579 passed.
- All three test runs archived; `way-slot-01` restored to its idle file (no `model:` line, idle prompt).
- ASK sent to ROUTER #49 (`local_6b51b50e-d0a2-4c04-bb04-bc8d0ed532db`): **delivered** (message id 9b3cd5c1-b677-40c2-a8a6-75598c1880f5), not confirmed read. Asks for an owner card: set `way-slot-01..06` to Bypass.

## State
- CI on the new head: see the PR (the head moved when this note and the skill edit were pushed; the old green on 7367f7f does not cover it).
- PR #41 not merged, still draft. Merge waits on the end-to-end proof below.

## Next
1. Owner sets Bypass on `way-slot-01..06` (router card; no tool can do it).
2. Launch one harmless brief into a Bypass slot, per `leadfuel-way:launch` (pin the model in the slot file, `update_scheduled_task`, `run_scheduled_task`, set effort, read back, send `GO`). Confirm `READY`, `GO`, the report, and whether a Bypass run can send a message to its launcher. Record in `docs/SLOT-LAUNCH.md` ("Not verified" and "Not run" lines become results). Restore the slot to idle, archive the run.
3. CI green on the head SHA (workflow `test`, job `pytest`; `gh run list --workflow test.yml --branch way/launch-slots --json headSha,conclusion,status`), then `gh pr ready 41`, merge into `way/plugin`.
4. Owner updates the installed plugin to 0.1.11 (pull the marketplace checkout, `claude plugin update leadfuel-way@leadfuel`), fresh session.

## Owed / not delivered
- Findings message to ROUTER #48 (`local_e4ee0816-7d58-4bfd-a102-f02d188116af`, id fc5dcc8c) was queued, not confirmed read; the same content is in `F:\Claude Sessions\handoff\NODE-auto-launch-part-1-findings.md`, and ROUTER #49 got a fresh ASK.

## Gotchas
- A launched slot run's `list_events` shows only the visible turn; it hides hook and tool traffic (47 messages, one visible line for an idle run).
- A Bash `cd` changes the session working directory; a heredoc with an apostrophe fails in the Bash tool, use Write.
- `set_session_model` and `set_session_effort` apply from the next turn.
