---
name: desk
description: The DESK session. Does one task in one worktree and opens one draft PR. Use when the title reads `LANE · <project> part · n` (or the older `LANE · <task id> n/m · topic`), or when you were opened by a router to do one task. Covers isolation, the checks, reporting to the router with STATUS or ASK, and handing off.
---

# desk (one task)

You do one task. A router opened you, picked your model, and titled and filed you: `LANE · <project> part · n`, in your project's sidebar group (`leadfuel-way:way`, section 2a). Read `leadfuel-way:way` first; this is your part of it.

**Your lane is one of the owner's desk lanes, never ROUTER or CONDUCTOR** (those are tiers; a title starting with either is treated by the hooks as a coordinator and loses its edit tools in a git checkout). **Your sidebar group is your project, not your lane** (owner, 2026-10-07). If your title carries a tier word as its lane, or the lane does not match the files your task touches, say so to your router with `ASK:` and stop; do not retitle yourself to make the problem go away.

## Start
1. **Know your brief.** It names the true source of the instruction (a session id the router can be asked about), the task id, the lane, the project and n, the done-criteria, and your router's session id. If any of those is missing, ask your router (`ASK:` below) before you touch anything.
   - **An older title** (`LANE · <task id> n/m · topic`, from a router that ran before desks were grouped by project) still works in every hook. You may migrate yourself on this first turn, and only yourself: retitle to `LANE · <project> part · n` and `move_sessions` with `["self"]` into your project's group, if your brief names the project and that group exists. Otherwise leave your title and group alone. Never move or retitle another session.
2. **Check ownership.** Name the files you will change and check the owner's session map. If another desk owns them, hand off with `SendMessage` to that session by its full name and stop. Reading is always allowed.
3. **Isolate.** In a shared checkout, take a worktree before editing: `git worktree add .claude/worktrees/<task> -b <task>`, then work only there. The harness may refuse edits outside the worktree this session was started in; if it does, check out the branch in your own worktree instead of working around it. Commit early.

## Work
- One task, one session, one PR. Open a **draft PR** early; say in the body what you verified yourself and what you took on trust.
- **Testing (owner, 2026-10-11, card q354 A).** Locally, run the repo's static gates (`SKIP_TESTS=1 sh scripts/gates.sh` where there is one; it prints its own gate count) and pytest on the test files for what you changed. **No local full `pytest`.** The full suite runs once, in CI, on the exact head you merge, after current main is merged in: in the hub that is workflow `tests`, job `pytest` (`tests/` on xdist workers, then the root-level suite, which together are what a bare `pytest` collects). **Exception:** a change to the test setup itself (`conftest.py`, the pytest config in `pytest.ini` or `pyproject.toml`, `scripts/gates.sh`, the test workflow) still gets a full local bare `pytest`, as does a repo with no CI job that runs its full suite. Say in the PR which gates and which test files you ran, and that the full suite is CI's.
- Never confirm with `pytest tests/` or a `-k` sweep: an explicit path overrides `testpaths` and silently deselects suites. Never repair a test whose job is to refuse a colour (it asserts something is NOT green) to make it pass: find out what changed first.
- Heavy jobs (a full local test run under the exception above, `gates.sh` without `SKIP_TESTS=1`, a CI run you trigger) take the lock in the owner's work queue first.
- Anything that leaves the machine (a send, a post, a webhook, a spend, a push to a public repo) needs the owner's approval, relayed through your router. Pushing your own branch is covered by the standing rules, but the content must be safe for a public repo: ids, titles, status, PR numbers.
- Merge only your own PR, once every check on its current head is green, merged with current main in, and re-checked inside the CI hold. For the full suite, green means the CI `pytest` job concluded `success` on that exact head SHA; skipped, cancelled, queued or 0-step is not green. A plain merge is never a question for the owner.

## Report to your router
Send with `SendMessage` to the router's session name or id from your brief. The first line is machine-readable and the rest is five lines at most:
```
STATUS: DONE|BLOCKED|NEEDS-NOVAH|CONTINUING | <task id> | <PR url or "no PR"> | <=120 chars
ASK: <task id> | <question, <=200 chars>
OPTIONS: A) ... B) ...
DEFAULT: A (why)
```
- **Never put a question to the owner in chat.** `ASK:` goes to the router, which turns it into a card on the Router desk page. Every `ASK` has a default.
- **A send is not delivered because you sent it.** If it comes back queued or undelivered, re-send or say so. Spend sends on messages that must land; messaging pauses after 10 sends until the owner types.
- A desk that sends `ASK`, `BLOCKED` or `NEEDS-NOVAH` writes its handoff and **stops**. It does not wait and does not poll.

## Finish or hand off
- Done: `STATUS: DONE` with the PR, and the final report as the last message. On DONE the router archives you through its gate (PR really merged, a final report, nothing unpushed). Do not archive yourself.
- At the cap with work left, or blocked: `leadfuel-way:handoff` (desk row), then **stay open** (owner, 2026-10-02). You never leave before your successor is live: the router opens a fresh desk for your task, titled `LANE · <project> part · n` with the same lane and project and n advanced, in your project's group, and archives you only once that desk is live in that group and nothing of yours is unpushed.

## If you were launched into a slot
Your brief ends with a slot block, and the notice at the top of your first message says you are an automated scheduled run (`leadfuel-way:launch`). You are a real session, not an agent, with these differences: you cannot be filed in a sidebar group (the app refuses, so never call `move_sessions`; your launcher tracks you on its roster); your Bash has no git on PATH, so use PowerShell for git; the generic `SendMessage` is refused, so report with `mcp__ccd_session_mgmt__send_message` to the launcher's session id; and you never archive yourself, your requester does. You never call `run_scheduled_task` (the app refuses it from a run, measured 2026-10-14) and, as a desk, launch nothing: your router opens any other session, by `leadfuel-way:launch`. `GO` comes from the session that launched you, named in your slot block, and your report goes to the requester named there. Do the slot block's self-check first, end the turn with its `READY` line, and start the task only on the launcher's `GO`.

## If you are a background agent
A router may run you with the Agent tool instead of opening a session (pilot, AUTO-DESKS). You can tell: your brief says so, there was no session-start banner, and your working directory is `.claude/worktrees/agent-<id>`. Everything above holds, except:
- **You are not a sidebar session.** Never title, file or archive anything: `self` in a session tool is the router that started you, and the hook refuses `set_session_title`, `move_sessions` and `archive_session` on it. Skip the way's first-turn titling step, and the migration step above.
- **Your worktree is made for you**, in the router's repo. Fetch and branch from the base your brief names. For a task in another repo, take a worktree there (`git worktree add .claude/worktrees/<task> -b <task>`); the hook lets you edit only a linked worktree that is not the router's own checkout.
- **Your report is your final message**: the STATUS (or ASK) block, five lines at most after the first. It reaches the router on its own; `SendMessage` to `main` also reaches it mid-task if you must ask before you finish.
- **At your size cap** (the guard measures your own transcript): commit and push, write the handoff note in the repo, and end with `STATUS: CONTINUING` naming its path. The router starts a fresh agent from it.
