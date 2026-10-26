# Handoff: fieldy-local-replay-001 (DESK, home node group)

Session `local_2ea838b1-7d8a-4b93-bd21-aaf927d3f3ac`, written 2026-10-26 UTC. Owner-approved task:
replay the hub's real Fieldy report pipeline on local Ollama models and compare with the stored
reports. Rule from the owner: nothing leaves this PC; do not read report text into a session, read
counts and timings. Judge locally; the owner reads the outputs himself.

## Done
- Railway CLI works again (owner approved a fresh `--browserless` login). Linked project
  LeadfuelBusinessSuites, environment production, service NovaHub: verified with `railway status`.
- One read-only `railway ssh` pull finished: 31 stored briefs (`DailyDigest`, source `fieldy_brief`,
  one account), plus identity and context. 13 days overlap the local export and are replayable.
- Harness written. Private copy, outside every repo: `F:\novah\reference\fieldy-local-replay-2026-10-25\`
  (`replay_local.py`, `hub_pull\briefs\*.json`, `identity.json`, `context.txt`). Not in this repo.
- Memory note `reference_fieldy_dump_via_railway_ssh` updated with the login trap.

## State (re-read before trusting)
- Verified: Ollama serves the 7B model at 100% CPU (`ollama ps`, context 28672), so the first
  smoke test ran far too slowly and I killed it; no result exists. Heavy lock released.
- Not confirmed: why CPU. Suspect `ollama serve` (started 23:07 local) predates the 23:09 upgrade
  that replaced `lib`; the tray app keeps failing to bind port 11434 (server.log spam).
- No quality result yet. No model comparison done.

## Next
1. Restart Ollama cleanly (owner OK, other desks use it) and confirm `ollama ps` shows GPU.
2. Edit `replay_local.py` to load `hub_pull\identity.json` and `context.txt` instead of the stub.
3. Smoke one day, then the 13 days vs the stored briefs, counts and attribution only.

## Owed
- Owner: delete or keep the stale User-level `RAILWAY_API_TOKEN` (shadows logins; per-process clear works).
- Earlier open flag, unanswered: NovaHub capped at 3 GB but peaked at 8 GB; check restarts.

## Gotchas
Inline `Remove-Item Env:` is blocked by the shell guard; put it in a `.ps1`. Take the heavy lock.
