# AUTO-LAUNCH handoff 001 (NODE · AUTO-LAUNCH 1/1, local_bee20a8d)

2026-10-07 ~04:00 UTC. Router: ROUTER #24 local_17705746 (rotating to #25). Step 1 FAILED, so no build,
per the brief. Desk stays open until the router rules.

## Done (all verified by this desk)
- Probe 1: `claude --bg` (CLI on PATH, 2.1.229), Haiku, plan mode, bg id a891a0b2.
  Probe 2: the desktop's bundled CLI (2.1.286), same flags, run from this worktree, bg id b8e457cb.
  Both stopped and removed. The daemon is not running, and no worktree was created.
- (a) Shows in the desktop sidebar: **FAILED.** Neither probe appeared in `list_sessions`
  (checked from 20 s to 4 min after start). There is no `local_` id. They exist only in `claude agents`.
- (b) Titled and grouped with the ccd tools: **FAILED**, because there is no `local_` id to pass.
- (c) SendMessage by `local_` id: **FAILED**, for the same reason. Partial: probe 1 was listed in
  `ListAgents` as a `bg` peer under its `--name`, so a send by name might reach one. Not tested.
- (d) Chosen model and mode: the mode is **verified** (its own screen showed plan mode on). The model is
  **unknown**, because the probe never made a call.
- (e) Not a side session: **verified only trivially.** The CLI daemon hosts it, outside the app entirely.
- Second blocker: the standalone CLI is not logged in. `auth status` reads `loggedIn: false` for
  both binaries. Desktop sessions get their auth from the app, and a `--bg` child does not inherit it.
  Both probes sat at "Not logged in".
- A chip desk cannot detach itself: `detach_session self` was refused because the session was user-placed.
  `start_session` is not in this build (ToolSearch).

## Next
The router turns the ASK into a card and the owner picks one. Build nothing before then.

## Owed
- ASK AUTO-LAUNCH, sent to ROUTER #24. Whether it was delivered is in this desk's final message.

## Design note from ROUTER #24 (received after the BLOCKED report was sent; it does not change the steps)
- The owner liked the script idea, and card q322 asks whether every tier could run on scripts plus one skill.
  q322 was unanswered when the note was sent.
- If a launcher is ever built, it is the first piece of that kit. It needs one shared module for session
  lookups and board reads, a stable command-line contract and JSON output. Only the launcher goes in its PR.
  Watchdog, gate, handoff and report wait for q322 and become separate NODE tasks.
- The launcher must set the model and the permission mode explicitly. Switching the mode does not release
  a prompt that is already pending: stop the session, then send continue.
- Measured on this chip desk (get_session self): model opus-5-5, effort **xhigh** (the router's, where
  route.py said high), mode **bypassPermissions** (not the default mode), parentSessionId = ROUTER #24,
  detached false.

## Gotchas
- The `claude` on PATH is a WinGet 2.1.229, while the app bundles 2.1.286. With 2.1.286, `--bg` refuses
  an untrusted folder.
- `claude agents --json --all` lists a stopped bg row `da2224f1` titled "CONDUCTOR · system build".
  It is not this desk's.
- The agent-view docs never mention the desktop app. A WebFetch summary claimed they do; do not quote it.
- Git Bash mangles `git show ref:path`. Set `MSYS_NO_PATHCONV=1`.
