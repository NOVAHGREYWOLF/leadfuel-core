# AUTO-DESKS: desks that start with no owner click

Task AUTO-DESKS (NODE), queued by the owner in CONDUCTOR 013 (`local_f999aa65`), 2026-10-06 ~00:59 UTC.
Desk: `NODE · AUTO-DESKS 1/1` (`local_9345bf47`), reporting to ROUTER #21 (`local_d51bda2e`).
Plugin change: leadfuel-way 0.1.7 (this branch). Times are UTC.

## The problem

A router opens a desk with `spawn_task`, which puts a chip in front of the owner; nothing happens until
the owner clicks it. `start_session` / `hand_off_to_session` would remove the click but are gated off for
this account (conductor 013 confirmed on 2026-10-06 that neither is in its tool list; taken on trust).
The Agent tool with `isolation: "worktree"` gives a background agent its own git worktree with no click.
The question was whether the way plugin lets such an agent work, and what it can and cannot do.

## What was measured (by this desk, 2026-10-06, CLI 2.1.286)

1. **A subagent's hook events carry the parent session's `session_id` and `transcript_path`, plus an
   `agent_id`.** Read from the CLI bundle's hook-input schema ("agent_id: present only when the hook fires
   from within a subagent"; `transcript_path` is derived from the session id), then confirmed live: this
   desk started a Haiku probe agent with `isolation: "worktree"`. Before the probe, this desk's hook state
   read role `UNFILED` (no title at session start, no Edit or Write since). After the probe's one Write and
   one Edit, the same state file read `PreToolUse: 2`, role `DESK`, lane `NODE`, and a title scan that had
   read this desk's own transcript (scan offset 849,825 bytes; the agent's whole transcript was smaller).
   The agent's writes were judged by the parent's title.
2. **So in a ROUTER the 0.1.3 hook refuses a background agent's every Edit and Write.** The same code path
   reads `ROUTER #21`, and the agent's worktree is a git checkout. Replayed on the measured event shape
   against the 0.1.3 source: `deny`. Against 0.1.7: allowed. (Synthetic replay, not yet a live router run;
   see "Pilot" below.)
3. **The agent's worktree** is `<router's repo>/.claude/worktrees/agent-<id>` on branch
   `worktree-agent-<id>`, with a `.git` file. ROUTER #21 runs in the main leadfuel-core checkout, so its
   agents get leadfuel-core worktrees. A task in another repo needs the agent to take its own worktree there.
4. **What the probe could do:** Write and Edit (in a DESK parent), Bash, `gh` 2.98.0, Python 3.12, git with
   the owner's identity, `SendMessage` to `main` (delivered into this desk's conversation mid-run), and
   ToolSearch loaded `ArtifactData`, `list_sessions`, `move_sessions` and `set_session_title`. Its final
   message came back on its own as a task notification. It cost about 60k tokens for 7 tool calls: a Haiku
   agent starts near 48k because of the tool list.
5. **The danger in item 4:** `self` in a session tool called from an agent is the parent. An agent that
   follows the way's first-turn step ("title and group yourself") would move the ROUTER into a desk group;
   `archive_session self` would archive the router and end every agent it runs. (`set_session_title`
   already says a subagent cannot rename the session it runs in; `move_sessions` and `archive_session` say
   nothing, so they are refused here rather than trusted.)
6. **The guard measured the wrong transcript:** a subagent's `PostToolUse` read the parent's size, so a
   small desk agent of a router past 300k would have been told to hand off, and a big agent never would.
   Agent transcripts are separate files (`<session>/subagents/agent-<id>.jsonl`, every record `isSidechain`).

## The change (0.1.7)

All in `hooks/way_hook.py`, keyed on `agent_id`:

| Rule | Before | After |
|---|---|---|
| Edit/Write by a ROUTER's or CONDUCTOR's agent | refused everywhere in a checkout | allowed in a linked worktree that is not the coordinator's own checkout; refused in the coordinator's checkout and in any main checkout; with the coordinator's cwd unknown, only `.claude/worktrees/agent-*` passes |
| Edit/Write by the coordinator itself | refused | unchanged, including inside its agents' worktrees |
| `archive_session` from any agent | judged as the parent's self-archive | refused outright |
| `move_sessions` / `set_session_title` on `self` from an agent | not hooked | refused (matcher widened to `mcp__.*__(archive_session\|move_sessions\|set_session_title)`) |
| Context guard for an agent | parent's size, parent's wording | the agent's own transcript and caps, wording for an agent (`STATUS: CONTINUING` + handoff path) |
| Hook state | agents wrote the parent's state file | agents keep `agents/<session>--<agent>.json`; the parent's file is never written by its agents |

`WAY_ENFORCE_ROLES=0` turns the agent rules off with the coordinator rule. The router, desk and way
skills say how to start an agent, what goes in its prompt, and what an agent skips.

Tests: `plugins/leadfuel-way/tests/test_way_agents.py` (36). A positive control was run against the 0.1.3
source on the same event: the router-agent edit came back `deny` there and allowed here, and
`move_sessions self` came back allowed there and `deny` here, so the tests can see what they claim to.

## What an agent can and cannot do (router skill, "Background desk agents")

- **Can:** edit in its own worktree (0.1.7), run gates and bare pytest (heavy jobs still take the
  WORK_QUEUE lock), push its own branch, open its own draft PR with `gh`, read and write the boards,
  `SendMessage` to `main` (its router).
- **Cannot:** be titled, filed or archived; be seen in the sidebar (the owner sees its roster row and its
  draft PR); outlive its router (agents end with the router session); take a per-agent effort setting (the
  Agent tool takes a model only).
- **Reports** with its final message, the STATUS block, which is all that enters the router's context.

## Risks and what holds them

- **Agents die with the router.** A router must not rotate, archive or restart while an agent runs: wait
  for the notification, or hand off the task as lost on rotation. Not enforced by the hook yet (the Stop
  event's `background_tasks` field could carry it; follow-up).
- **The router's context grows by each report.** Five-line reports only.
- **Model and size rules per desk.** The model comes from route.py per task (passed as `model`); the guard
  now measures each agent's own size. There is no SubagentStop gate yet, so an agent past its cap is told,
  not stopped (follow-up).
- **The doctor has no synthetic agent step yet** (left out to avoid colliding with PR #19, which edits the
  doctor; follow-up).

## Pilot

Proposed to ROUTER #21 with `ASK` before running, as the brief requires: run **NODE ·
WAY-POSITIVE-CONTROL** (queued, rank 206; a standing-rule line in the way skill, same leadfuel-core repo
the router runs in, route.py says Sonnet) as a background agent started by the router. The owner's
close-first rule (ROUTER #21, 01:1xZ) means the router may need the owner's yes to open it at all.

- **Under the installed 0.1.3** the agent's first Edit should be refused. That run measures the block live
  in a real ROUTER; the agent is told to report the refusal text and stop, not to work around it with shell
  writes.
- **Under 0.1.7** (after this PR merges and the owner installs it: `git -C C:\Users\novah\leadfuel-way-plugin
  pull --ff-only`, then `claude plugin update leadfuel-way@leadfuel`, then a fresh router session) the same
  brief should run end to end: edit, draft PR, report.

Result: pending the router's answer. This section is updated with the measured outcome.

### The pilot call (for ROUTER #21 to paste once it answers the ASK)

`Agent` with `subagent_type: "general-purpose"`, `isolation: "worktree"`, `run_in_background: true`,
`model: "sonnet"` (route.py), `description: "NODE · WAY-POSITIVE-CONTROL 1/1"`, and this prompt:

```
Task WAY-POSITIVE-CONTROL (NODE lane). Goal: the way skill states, as a standing rule, "pair every zero
with a positive control in the same command": a check that reports zero (no failures, no matches, nothing
unpushed) must show in the same command that it can see a known positive, or it reports unknown.
True source: the owner queued it in conductor 008's chat (local_b666d711), 2026-10-03 ~02:30 UTC, pick
NODE~WAY-POSITIVE-CONTROL rank 206; basis from ROUTER #13 (local_21748811). Task record: Conductor desk
doc desks/node, tasks.WAY-POSITIVE-CONTROL. No other session holds it (ROUTER #21 checked).
Repo: leadfuel-core, base branch way/plugin. Files: plugins/leadfuel-way/skills/way/SKILL.md (section 3,
the "Verify" bullet), the version in plugin.json, marketplace.json and VERSION in hooks/way_hook.py
(bump to the next free patch above every open way PR). Router to report to: ROUTER #21 (your parent).
Done when: the rule is in the way skill, bare pytest from the repo root passes, a draft PR into way/plugin
is open, and you have reported.
PILOT MEASUREMENT: your first edit must use the Edit tool. If the Edit tool is refused, do NOT write the
file any other way: end at once with STATUS: BLOCKED and the refusal text (first 200 characters).

You are a background desk agent, not a sidebar session. Invoke leadfuel-way:way and leadfuel-way:desk, but
skip titling and filing: never call set_session_title, move_sessions or archive_session (self is the
router that started you; the hook refuses it). Work only in your worktree: git fetch origin way/plugin,
then git checkout -b way/positive-control origin/way/plugin. Draft PR, bare pytest, as any desk (this repo
has no gates.sh; say so). Public repo: ids, titles, status only. Your final message is your report: the
STATUS line and at most 5 lines. At your size cap: commit, push, write a handoff note in the repo, end
with STATUS: CONTINUING.
```

After it reports, ROUTER #21 sends its STATUS block and the notification's token and duration line to
`NODE · AUTO-DESKS 1/1` (`local_9345bf47`), which records the result here.
