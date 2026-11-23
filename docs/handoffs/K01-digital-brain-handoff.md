# K01 digital brain: handoff (2026-11-23 Pacific, background desk agent for ROUTER #135)

Scope and phase table: `docs/DIGITAL_BRAIN_PHASES_0_6.md` (copy at `F:\Claude Sessions\handoff\ROUTER-135\K01\SCOPE.md`).

## State, re-check before trusting
- novahub-mcp draft PR 54, https://github.com/NOVAHGREYWOLF/novahub-mcp/pull/54, branch `brain-p0-connector-reads`, head f8acbe4. Local worktree (temporary, may be gone): `C:\Users\novah\AppData\Local\Temp\claude\dbcfc8230e7026ae\a46f75ee-b00b-475e-9d4c-fd4eae004e92\scratchpad\mcp-wt-brain-p0`. The branch is pushed; re-create the worktree from it if needed.
- The PR touches `tools/apps.py`, the ARMS MCP tool floor, and is a Law 9 gate. ARMS and DOORS have NOT been messaged by me; the router routes the review. Live ARMS desk seen in the session list: `ARMS · land the backlog part · 1` (`local_197a5c5c-4126-494e-8be6-9ffc8ca783bb`); DOORS: `DOORS · one-interface part · 31` (`local_c8ea9628-3b44-40a6-8724-b1201badc347`). Both unconfirmed as the right owners.
- CI on PR 54 was started by the push and not read.

## Left to do
1. Route PR 54 to ARMS and DOORS (router). `lucid.today` is the one entry that needs DOORS to say yes.
2. Part 16 additions: evening routines with schedule and last good run (CONNECTIONS.md G21); one-brain test line, window answered from the brain in LOCAL and CLOUD mode (G34).
3. Mail 2 item 3: map the 2026-08-13 NovahBrain blueprint against the brain as built.
4. Link the scope file from the RUNBOOK.md BRAIN section (NODE desk script owns that file).
5. Hub gap, a separate small hub PR for INTELLIGENCE or ARMS: add `fieldy.window`, `fieldy.get`, `memory.recent` to `_HUB_LOCAL_APP_ACTIONS` in `app.py`, or stop advertising them in the catalog, plus a test that goes through `/api/app-action`, not `_run_hub_local_action`.

## Owner steps
Listed in section 6 of the scope file. The one that blocks the phase 0 done test is answering the `embed.query` approval email with an indefinite or long window.
