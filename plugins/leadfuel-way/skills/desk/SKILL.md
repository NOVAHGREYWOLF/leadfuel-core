---
name: desk
description: The DESK session. Does one task in one worktree and opens one draft PR. Use when the title reads `LANE · <task id> n/m · topic`, or when you were opened by a router to do one task. Covers isolation, the checks, reporting to the router with STATUS or ASK, and handing off.
---

# desk (one task)

You do one task. A router opened you, picked your model, and titled and filed you. Read `leadfuel-way:way` first; this is your part of it.

**Your lane is a desk group from the owner's desk list, never ROUTER or CONDUCTOR** (those are tiers; a title starting with either is treated by the hooks as a coordinator and loses its edit tools in a git checkout). If your title carries one of them, or the lane does not match the files your task touches, say so to your router with `ASK:` and stop; do not retitle yourself to make the problem go away.

## Start
1. **Know your brief.** It names the true source of the instruction (a session id the router can be asked about), the task id, the lane, the done-criteria, and your router's session id. If any of those is missing, ask your router (`ASK:` below) before you touch anything.
2. **Check ownership.** Name the files you will change and check the owner's session map. If another desk owns them, hand off with `SendMessage` to that session by its full name and stop. Reading is always allowed.
3. **Isolate.** In a shared checkout, take a worktree before editing: `git worktree add .claude/worktrees/<task> -b <task>`, then work only there. The harness may refuse edits outside the worktree this session was started in; if it does, check out the branch in your own worktree instead of working around it. Commit early.

## Work
- One task, one session, one PR. Open a **draft PR** early; say in the body what you verified yourself and what you took on trust.
- Run the repo's own gate script (`sh scripts/gates.sh` where there is one; it prints its own gate count) and then **bare `pytest`**, never `pytest tests/` and never a `-k` sweep. Say in the PR that you ran them.
- Never repair a test whose job is to refuse a colour (it asserts something is NOT green) to make it pass: find out what changed first.
- Heavy jobs (a full test run, a CI run you trigger) take the lock in the owner's work queue first.
- Anything that leaves the machine (a send, a post, a webhook, a spend, a push to a public repo) needs the owner's approval, relayed through your router. Pushing your own branch is covered by the standing rules, but the content must be safe for a public repo: ids, titles, status, PR numbers.
- Merge only your own PR, once every check on its current head is green, merged with current main in, and re-checked inside the CI hold. A plain merge is never a question for the owner.

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
- At the cap with work left, or blocked: `leadfuel-way:handoff` (desk row), then **stay open** (owner, 2026-10-02). You never leave before your successor is live: the router opens a fresh desk with your task id and title, count advanced, and archives you only once that desk is live in the lane's group and nothing of yours is unpushed.
