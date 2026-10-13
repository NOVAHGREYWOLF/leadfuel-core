# SLOT-LAUNCH: starting a session with no click (way plugin 0.1.11)

Owner, 2026-10-13: "when a session needs to create a new session this should be automated. I
shouldn't have to say yes." The procedure is the skill `leadfuel-way:launch`; this file is why it
looks the way it does, and what was measured versus taken on trust.

## The ways to start a session, and where each stands
| Way | Click | Status |
|---|---|---|
| `start_session` tool | none | Not in this build. The app's own tool text names it; AUTO-LAUNCH 1/1 (2026-10-07) found it switched off for this account; re-checked 2026-10-13, a ToolSearch finds nothing. There is no switch a session can flip. |
| `claude --bg` from a shell | none | Dead. The session never reaches the sidebar and the command line is not logged in (AUTO-LAUNCH 1/1, 2026-10-07; not re-tested). |
| `spawn_task` chip | one | The click the owner objected to. |
| Background agent (Agent tool) | none | Works for desks (way 0.1.7, ROUTER #25 and #26: 8 agents, 97 edits, 0 refusals). It dies with its router and is not a sidebar session, so it cannot be a successor. |
| **Scheduled-task run** (`run_scheduled_task`) | **none** | **Measured below. This is the launch slot.** |

## Measured on 2026-10-13 (NODE · auto-launch part · 1, two probes, both cleaned up)
- `run_scheduled_task` starts a new session at once and returns its id. No click.
- The same task run twice gives two different sessions. `update_scheduled_task` between the runs
  changed the prompt and the title; the second run did the new prompt and carried the new title. A
  task is therefore a reusable launch slot. A task with a run in progress refuses a second run.
- `set_session_model` on the running session worked and took effect from its next turn (sonnet to
  haiku, confirmed by the session's own reply).
- `SendMessage` to the launched session by its `local_` id was delivered and acted on.
- `archive_session` on a finished run, called from outside, worked.
- `move_sessions` is refused: "Routine runs show under their routine, not as their own sidebar rows,
  so they can't be grouped, pinned or marked." So a slot session never has a project group.
- The launched session reported permission mode `default`, model sonnet-5-5, effort medium. An
  earlier run (ROUTER #48's test) got fable-5-1 at high effort. The rule is unknown; a launcher
  must set model and effort, and cannot rely on inheriting.

## End-to-end check of the skill's own slot block (2026-10-13, slot way-slot-06, a fresh slot)
- Launched with the block exactly as the skill gives it. The session started, ran the self-check,
  found permission mode `default`, and stopped without a title change, a file or a PR: the Bypass
  self-check works.
- Its attempt to send `SLOT-NOT-BYPASS` to the launcher was refused: "it needs a person's approval
  and nobody has opened this scheduled run". So the block now has the session end its turn with that
  line, and the launcher reads it with `list_events`.
- `set_session_model` on the running first turn replied that the current turn finishes on the previous
  model: the reason the block makes the first turn a short check that ends with `READY`.
- **Not run:** the `READY`, `GO`, report path, which needs a slot in Bypass. After the owner sets
  Bypass on a slot, one launch of a harmless brief proves it, and settles whether a Bypass run can
  send a message to its launcher. Until then the skill's claim for that path is a design, not a result.

## Measured later the same day (NODE · auto-launch part · 2, 06:00 to 06:07 UTC, slot way-slot-01, all runs archived, slot restored to idle)
- **Bypass is still not set.** A second fresh slot, launched with the skill's slot block, stopped on its
  self-check with `SLOT-NOT-BYPASS way-slot-01 mode=default`, readable from `list_events`. The
  `READY`, `GO`, report path is therefore still not run; it waits on the owner's step 1 below. The
  WATCH desk's handoff (ROUTINE-NO-PROMPT-001, 2026-10-06) read the app and says a routine's
  permission mode is a per-task field the scheduled-task tools cannot set; `create_scheduled_task` has
  no such field either (checked 2026-10-13).
- **A `model:` line in a slot's `SKILL.md` frontmatter sets the run's model.** Suggested by the same
  WATCH handoff. With `model: claude-haiku-4-5-20251001` the run's `get_session` reported
  `claude-haiku-4-5-20251001` (a fresh run of the same slot without the line had been
  `claude-sonnet-5-5`). `update_scheduled_task` on the title, description and prompt left the line in
  place. A later run with `model: claude-sonnet-5-5` and `effort: low` reported sonnet at effort
  `medium`: the model line is honoured, an `effort:` line is not (the key spelled `effort` only).
- So the launcher pins the model before the run and the first turn already starts on it. Effort
  still needs `set_session_effort`, which applies from the next turn, so the `READY`, `GO` step stays.

## Taken on trust (ROUTER #48's SUCCESSOR-TEST run, 2026-10-13; read from its report and `get_session`)
- The way's session-start banner appeared in the run (plugin 0.1.9, title None, role UNFILED), and
  the run could retitle itself.
- Its Bash had no git on PATH (exit 127); PowerShell had git.
- The generic `SendMessage` tool was refused inside the run; `mcp__ccd_session_mgmt__send_message`
  queued the report instead.
- `archive_session` on `self` was refused by this plugin's own guard, since no successor was
  visible in a sidebar group.

## Not verified
- `notifyOnCompletion`: set true on both probe runs; nothing arrived in `ReadNotifications` after
  either finished. Nothing is built on it. A launched session reports by message.
- Whether a freshly created task stops on tool approvals at its first run (the tool text warns it
  may). The probes used only ToolSearch and `get_session` and did not stop.
- Whether a run in Bypass can send a message to its launcher (a run in default cannot; see the
  end-to-end check). The launcher also reads a session's transcript, so reports are not lost either way.
- Whether any tool can set a routine's stored permission mode. It looks owner-only, in the app.
  Until it is Bypass, a launched session starts in default mode and stalls; the slot block's first
  step catches that (`SLOT-NOT-BYPASS`).

## What the design does about each
- **Six slots**, `way-slot-01` to `way-slot-06`, so up to six launches are in flight at once.
- **A short first turn.** A model change applies from a session's next turn, so the slot block makes
  the first turn a self-check that ends with `READY`; the launcher then sets model and effort and
  sends `GO`. One send per launch, and messaging pauses after 10 sends until the owner types.
- **The archive guard reads the slot id where it used to read a group.** A slot session can never be
  in a group, so `is_successor` accepts a row whose `scheduledTaskId` is `way-slot-NN` in place of the
  group test, and still requires it live, the same role and the next of the same line. A row from
  `list_sessions` that does not carry `scheduledTaskId` is unknown, not a pass; the skill says to
  read the successor back with `get_session` on its id.
- **The wrapper notice** ("the user is not present", "write actions only if the task file asks for
  that specific action") is addressed in the block: the brief lists the write actions it asks for.

## Owner steps (no session can do them)
1. Open each `way-slot-NN` routine in the app and set its permission mode to Bypass, once.
2. Update the installed plugin to 0.1.11 once this merges: pull the marketplace checkout, then
   `claude plugin update leadfuel-way@leadfuel`, and start a fresh session.
3. Accept that launched sessions show under Scheduled, named by their title, not in a project group.
