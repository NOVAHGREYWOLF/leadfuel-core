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
| **Scheduled-task run** (`run_scheduled_task`) | **none** | **Measured below. This is the launch slot. Only a regular session may run it (2026-10-14): the launcher does, for everyone.** |

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
- That run could not take the `READY`, `GO`, report path (it needs a slot in Bypass). The path was
  run the same day once the owner had set Bypass: see "Bypass end-to-end" below.

## Measured later the same day (NODE · auto-launch part · 2, 06:00 to 06:07 UTC, slot way-slot-01, all runs archived, slot restored to idle)
- **Bypass was not yet set at 06:00 UTC.** A second fresh slot, launched with the skill's slot block,
  stopped on its self-check with `SLOT-NOT-BYPASS way-slot-01 mode=default`, readable from
  `list_events`. The `READY`, `GO`, report path waited on the owner's step 1 below. The
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

## Bypass end-to-end (2026-10-13 12:40 to 12:50 UTC, NODE · auto-launch part · 2, after owner card q399 A)
The owner set Bypass on the six slots (card q399 answered A at 12:29 UTC, relayed by ROUTER #51;
ROUTER #50 also relayed his "I set all six", unverified by this desk). Nobody can read a routine's
mode, so each run's own `get_session` is the proof. All runs below were archived afterwards and the
six slot files restored to idle.
- **All six slots are in Bypass.** Each of the six launched runs reported `permissionMode:
  bypassPermissions` from its own `get_session` and ended its first turn `READY way-slot-NN`
  (slots 02 to 06: self-check only, no `GO`, archived; slot 01: the full path below).
- **The full path ran on slot 01** with the skill's steps: `update_scheduled_task`, the `model:` pin
  in the slot file (Haiku), `run_scheduled_task`, `set_session_effort low`, read back, `GO`. The run
  started on `claude-haiku-4-5-20251001` (the pin worked on all six), its first turn ended `READY
  way-slot-01`, `GO` was delivered, and it answered it with one `mcp__ccd_session_mgmt__send_message`
  to the launcher and `PROBE-DONE`. Its own `get_session` showed `effort: low`.
- **A Bypass run can send.** The run's `send_message` returned `delivery: queued`, "that session is
  holding it (a turn is in progress there ...) and runs it when that clears": the launcher was
  mid-turn, so the message waits for the launcher's turn to end. It is not refused, which is what a
  default-mode run got. It was delivered: after the launcher ended its turn the message arrived in
  its conversation, from the probe's session id, with the line the brief asked for. The launcher
  therefore must end its turn to receive a report; a launcher that never does reads the run with
  `list_events` instead.

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
- Whether any tool can set a routine's stored permission mode. It looks owner-only, in the app
  (the WATCH handoff says so; `create_scheduled_task` and `update_scheduled_task` have no such field).
  Until it is Bypass, a launched session starts in default mode and stalls; the slot block's first
  step catches that (`SLOT-NOT-BYPASS`).
- Whether a slot's Bypass survives the owner editing a routine or a plugin or app update. Each launch's
  self-check re-proves it, so nothing depends on it staying set.

## What the design does about each
- **Six slots**, `way-slot-01` to `way-slot-06`, so up to six launches are in flight at once.
- **The launcher sends `GO`.** The slot block names two ids: `<launcher id>`, whose `GO` the run waits for, and `<requester id>`, who gets the report. A requester that is itself a slot run cannot run the slot, so `GO` always comes from the launcher.
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

## Three walls, measured 2026-10-14 by conductor 037 (taken on trust here; this desk did not re-run them)
Conductor 037 was itself a slot run (`way-slot-02`, `get_session` showed `bypassPermissions`) when it tried to launch a successor. Its results:
1. **`update_scheduled_task` inside a slot run is refused**: "needs a person's approval, and nobody has opened this scheduled run". Bypass does not help, because the approval is not a tool permission.
2. **A slot task's title must differ from the session title it sets.** Once the owner was in the session the same call went through, then failed on a duplicate title: "A scheduled task is already listed as ... way-slot-02". Rule from here on: the task's title is always `slot NN | <TITLE>` and the session's is `<TITLE>`, so they cannot be equal.
3. **`run_scheduled_task` is refused from any scheduled-task run, in every state**: "Refusing to run a scheduled task from a scheduled-task run session. Run it from a regular session instead." The app's own rule; no setting fixes it.

So the first slot hop works (conductor 036, a regular session, launched 037) and the second cannot: a slot-launched router or conductor cannot launch its own successor. Not verified by anyone yet: whether a **regular** session's `update_scheduled_task` runs unattended without an approval card. Regular sessions have called `run_scheduled_task` since 0.1.11, so the run call is known to work from one; the update call is the open question (ROUTER #52 was asked to make it).

## The launcher session (0.1.12, owner pick 264, 2026-10-14: "Standing launcher session (Recommended)")
**One small regular session whose only job is launching.** Any session, slot run or regular, sends it a `LAUNCH-REQUEST` (format in `skills/launch/SKILL.md`, "Ask the launcher"); it picks a free slot, runs the 0.1.11 steps, sends `GO` from its own id, and answers the requester `LAUNCHED <session id> <slot id> <title>` or `LAUNCH-FAILED <reason>`. The standing procedure is the skill's section "If you are the launcher", kept in the skill rather than in a pasted prompt so that it survives a `clear_session`.
- **Why a regular session.** Wall 3: only a regular session may run a scheduled task.
- **Model.** Sonnet, effort low. The work is mechanical but has several exact edits (the slot file's `model:` line, the slot block's placeholders) and a check of the brief. Haiku is the saving to try after ten clean launches, with the retry-one-tier-up rule if it fails a step twice. Not measured on either model yet.
- **Permission.** Bypass, set by the owner when he starts it, once. It then never stops on a prompt. Its risk is amplification: it starts a Bypass session from any live router, conductor or desk's brief. It therefore checks that the requester is a live coordinator or desk, that the title is in the way's form and unique, and that a brief asking for anything that leaves the machine names the owner's approval. It is a conduit with the requester's authority and no more.
- **Rotation.** It holds no state (the requester has the roster), so it clears itself with `clear_session` on `self` as the last act of every request, when no other request is waiting. Its context never grows past one launch. Unverified: that `clear_session` on `self` runs without a card in Bypass (the tool text says Bypass does not ask), that the clear survives a message waiting from another session (the tool text says a waiting user message drops it), and that the SessionStart banner returns after a clear. If clear is refused, it works until the plugin guard's cap and hands off like any session; a replacement is one paste.
- **Cost.** A launch is about fifteen tool calls and a few thousand tokens, once per successor. An idle launcher costs nothing.
- **Finding it.** `list_sessions` for a title starting `NODE · launcher`, or the board's `launcher/current` beside `router/current`, which the launcher writes on its first request after a start.

**Can a session create it without the owner? No.** `start_session` and `hand_off_to_session` are not in the toolset of a background desk agent, a router or a slot run (ToolSearch on 2026-10-14 finds nothing under those names); a background agent is not a sidebar session; a slot run is a scheduled run, so it cannot be the regular session; `claude --bg` never reaches the sidebar; and a `spawn_task` chip needs a click. So the owner starts it with one paste, once, into a fresh Sonnet session set to Bypass:
```
You are NODE · launcher part · 1, the standing launcher. Set your title to that and file yourself in the full system automation group. Invoke leadfuel-way:way and leadfuel-way:launch and follow its section "If you are the launcher". Write your own session id to the board as launcher/current. Then wait for LAUNCH-REQUEST messages and end your turn.
```
That is the one paste the system asks for; after it, no launch needs the owner.

## A stop for the walls, in the plugin (0.1.12)
The app already refuses a slot run's `run_scheduled_task` and `update_scheduled_task`, but only after the session has done its work, and with a message that does not say what to do. The hook now (a) denies both calls from a session whose first message carries the slot block, naming the launcher, and (b) on Stop sends a slot-run router or conductor back once per stop (three at most) if it has written a handoff without a `LAUNCH-REQUEST` in its transcript. Limits: it cannot tell a regular session from any other, so "a regular session asks the launcher" is advice, not a wall; it reads the first 256 KB of the transcript for the slot marker and the last 768 KB for the request; a slot run launched from an older brief without the marker is not covered.

## Owner steps (no session can do them)
1. ~~Open each `way-slot-NN` routine in the app and set its permission mode to Bypass, once.~~ Done
   2026-10-13 (card q399 A); proven by the six runs above.
2. Update the installed plugin to 0.1.12 once this merges (it carries 0.1.11): pull the marketplace checkout, then
   `claude plugin update leadfuel-way@leadfuel`, and start a fresh session.
3. Accept that launched sessions show under Scheduled, named by their title, not in a project group.
4. Start the launcher: paste the prompt above into a fresh Sonnet session and set it to Bypass (section "The launcher session"). Until it is live, a regular session runs the launch steps itself and a slot run falls back to the paste prompt.
