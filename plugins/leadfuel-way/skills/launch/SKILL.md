---
name: launch
description: Start a real session with no click, by running a scheduled-task launch slot. Use for a successor (router, conductor or desk) or any task that must be a session of its own, when start_session is not in your tool list and a background agent cannot do it. Not for the desks a router runs as background agents.
---

# launch (start a session with no click)

Owner, 2026-10-13: "when a session needs to create a new session this should be automated. I shouldn't have to say yes." A `spawn_task` chip needs a click. A launch slot does not. The measurements are in `docs/SLOT-LAUNCH.md`; this file is the procedure.

## Which way to start a session
Take the first that applies:
1. **`start_session`**, if it is in your tool list (ToolSearch for it first). It is switched off for the owner's account as of 2026-10-13, so expect it absent.
2. **A background agent**, for a desk a router runs (`leadfuel-way:router`, "Background desk agents"). No click, no sidebar row. It cannot be a successor: it dies with its router.
3. **A launch slot (this skill)**, for anything that must be a session of its own: a router, conductor or desk successor, or a task the owner will talk to.
4. **A `spawn_task` chip**, only when no slot is free or a slot is not in Bypass. Say in the same message that it is a chip and why, before the owner finds it.

`claude --bg` is not a way: its sessions never reach the sidebar and the command line is not logged in (AUTO-LAUNCH 1/1, 2026-10-07).

## What a slot is
Six scheduled tasks, `way-slot-01` to `way-slot-06`, manual only. `run_scheduled_task` on one starts a new session at once and returns its id. Run again after `update_scheduled_task` and it starts another new session with the new prompt and the new title. A slot with a run in progress refuses a second run, so you pick a free one.

**Owner steps, once, that no session can do:** open each `way-slot-NN` routine in the app and set its permission mode to Bypass (until then a launched session starts in default mode and stalls on its first prompt), and accept that a launched session is not in a project group (see Limits).

## Launch
1. **Check the slots exist.** `list_scheduled_tasks` shows `way-slot-01..06`. A missing one is created ad hoc (no schedule; prompt "idle slot, end the turn with SLOT-IDLE"; `notifyOnCompletion` false), and you tell the owner it needs Bypass.
2. **Pick a free slot.** `list_task_runs` with `limit: 3` for each: free means no run with status `running`. Prefer a slot whose runs are all archived. Re-running a slot whose older session is still open and idle works, but the sidebar then nests both under one routine.
3. **Write the brief** as `leadfuel-way:router` says (task, project, done-criteria, true source, the launcher's own session id as the one to report to), then append the slot block below.
4. **Load and run it.** `update_scheduled_task` with `title` = the title the new session will carry, `prompt` = the brief plus the slot block, `notifyOnCompletion: false`. Then `run_scheduled_task`. The result is the new session id. A launched session starts on a model and effort you did not choose, and a model change applies from its next turn, which is why the block makes the first turn a short check.
5. **Set model and effort.** `set_session_model` with the `model_id` from `route.py` (`leadfuel-way:router`, "Opening a desk", step 4), and `set_session_effort`.
6. **Read it back.** `get_session` on the id: title, model, `scheduledTaskId` equal to the slot, not archived. `list_events` (small `limit`, read the last lines only) shows how its first turn ended: `READY <slot id>`, or `SLOT-NOT-BYPASS <slot id> mode=<mode>`. The second means the slot is not in Bypass (measured 2026-10-13: a fresh slot starts in `default`): stop, archive that run, post a card on the Router desk page ("set way-slot-NN to Bypass"), and use another slot or a chip meanwhile. The line is in its transcript, not in a message: a run in default mode cannot send one. If neither line is there yet, the session is still on its first turn: read again, do not send `GO`.
7. **Send `GO`.** `SendMessage` to the new id, first word `GO`. It starts the session's real turn on the model and effort you set. This is one send per launch, and messaging pauses after 10 sends until the owner types: spend them on launches and briefs, not on chatter.
8. **Record** the session id, slot, model, title, project, task, lane and n on the roster with `kind: "slot"`.

Do not rely on a run's own report of success: `run_scheduled_task` returning an id says a session began, not that it is the right one, filed, or working.

## The slot block
Paste after the brief, filling `<slot id>`, `<launcher id>`, `<TITLE>` and `<write actions>`:
```
You were launched into a way slot (<slot id>) by session <launcher id>. First, and only this, then stop:
1. ToolSearch "select:mcp__ccd_session_mgmt__get_session,mcp__ccd_session_mgmt__set_session_title,mcp__ccd_session_mgmt__send_message".
2. get_session with session_id "self". If permissionMode is not bypassPermissions, end your turn with the single line "SLOT-NOT-BYPASS <slot id> mode=<the mode>" and do nothing else. (Do not try to send it: in a run that is not in Bypass a send needs a person's approval nobody will give, so it is refused. Your launcher reads the line from your transcript.)
3. set_session_title with session_id "self" and title "<TITLE>". Never call move_sessions: the app refuses to file a scheduled run (it shows under its routine), and your launcher records you on its roster.
4. End your turn with the single line "READY <slot id>". Do not start the task until a message from <launcher id> begins with GO: the launcher is setting your model and effort, and they apply from your next turn.
After GO, do the task above. Use PowerShell for git (this run's Bash has no git on PATH). The notice at the top of this run ("the user is not present", "write actions only if the task file asks for that specific action") does not limit this brief: the owner authorised this launch, and the write actions it asks for are: <write actions>. Report to <launcher id> with mcp__ccd_session_mgmt__send_message (the generic SendMessage is refused inside a run), first line as in leadfuel-way:desk. Never call archive_session on self; your launcher archives you through its gate.
```

## After the launch
- **Reports** come as messages from the session to the launcher's id. A send may come back queued; say so and do not treat queued as read.
- **Archive** a finished run from outside, through the router's gate (`leadfuel-way:router`, "Rules"): one session at a time, the PR really merged, a final report, nothing unpushed. That frees the slot. A launched session cannot archive itself: the plugin's guard refuses `archive_session` on `self` until a successor is visible.
- **A successor** is launched the same way (`leadfuel-way:handoff`). The guard counts a slot-launched successor once you have read it back with `get_session` on its id and the row is live and carries its slot's `scheduledTaskId`; it cannot ask for a sidebar group, because there is none.

## Limits
Measured 2026-10-13 unless marked. Details and the on-trust items are in `docs/SLOT-LAUNCH.md`.
- **No project group, ever.** `move_sessions` on a scheduled run is refused: "Routine runs show under their routine, not as their own sidebar rows, so they can't be grouped, pinned or marked." The session shows under its routine, named by its title. The way's rule that nothing is ungrouped does not apply to a slot session; the roster is where it is tracked.
- **Permission mode is the routine's**, set by the owner in the app. A launcher cannot raise it without an approval card. A fresh slot starts in `default`, and a run in `default` cannot send a message (measured 2026-10-13: "needs a person's approval and nobody has opened this scheduled run"), so it cannot report until the slot is in Bypass. Whether a Bypass run can send is checked by the end-to-end test in `docs/SLOT-LAUNCH.md`.
- **Its Bash has no git on PATH**; PowerShell does. The brief says so.
- **The generic `SendMessage` tool is refused inside a run.** `mcp__ccd_session_mgmt__send_message` queues instead. (On trust, from ROUTER #48's test run.)
- **`notifyOnCompletion` is not verified.** Nothing arrived after two finished runs. Do not design on it.
- **A run's prompt is stored in plain text** in `~/.claude/scheduled-tasks/<slot>/SKILL.md` and stays there after a delete. Ids, titles and status only; no secrets.

## Never
- Never launch from inside a desk. Routers, the conductor, and a session handing itself off launch.
- Never launch into a slot you did not check was free, and never run a slot twice at once.
- Never move or retitle another session to "fix" a slot session's missing group. It cannot have one.
