# FIELD · fieldy retention hold on hub — handoff 001

Session `local_ccbb8afd-09ad-49fe-ab48-86bf5cde9405` (FIELD group, Fable), 2026-10-07. Owner-direct task, no board id. Branch `claude/zealous-heisenberg-tlqil3` (leadfuel-core). No PR; nothing in this note is private.

## Done
- Owner asked for `FIELDY_RETENTION_HOLD=1` on the NovaHub service (LeadfuelBusinessSuites / production). **Verified already set** (`railway variables --service NovaHub`, filtered by exact name; value is one byte `1`). Nothing changed, no redeploy.
- Owner then asked for the day's Fieldy content. Delivered in chat only (private). Source: hub MCP (`fieldy_digest`, `fieldy_review`, `recent_memory` kinds=location) plus one owner-approved read-only `railway ssh` run of `scratchpad/fieldy_dump.py` (session scratchpad, not in repo) calling `fieldy_digest._load_conversations` + `fieldy_report.stitch`.

## Findings (verified myself)
1. **Digest write-up empty three builds running** (days 2026-10-04/05/06): `summaries: []`, `review_error: "the extraction pass returned nothing"` — `fieldy_report.synthesize` map step returns no episodes (fieldy_report.py:492-497). `search_brain` also `upstream_unavailable` twice. Same cause not proven.
2. **Watchdog false "down"**: `source_down:ingest:fieldy` at 05:03Z claimed newest Fieldy row 2026-10-04 while 464 rows landed 10-06 and 81 more 04:57–08:07Z 10-07. WATCH lane.
3. All Fieldy segments unattributed (`speaker: Unknown`, no profile ids); 50 items in review queue.
4. Hold contradicts `data_policy.html` 30-day redaction promise (fieldy_retention.py:64-69 says whoever sets the hold owns the page).

## Next
Send ROUTER #26 (`local_0185d288-2c99-49e5-8c15-5412aecd8eaf`) a brief: (1) FIELD — diagnose the empty extraction pass (hub `/api/fieldy/report` has `probe`/`trace` diagnostics, service-token only); (2) WATCH — fieldy watchdog stale signal; (3) `data_policy.html` wording while hold is on. Owner has not said to queue them — ask first.

## Owed
None sent to other sessions. No owner decision pending.

## Gotchas
- `railway ssh` quotes args containing `(` or `"` itself; single quotes become literal. Pipe the script on stdin: `Get-Content script.py -Raw | railway ssh --service NovaHub -- /opt/venv/bin/python -`.
- Container `python3` is bare Nix; the app venv is `/opt/venv/bin/python` (cwd `/app`).
- Railway SSH proxy throttles after a burst: TCP opens, banner exchange times out for ~10 min. Back off 90 s.
- `recent_memory` caps at 100 rows; location rows are `kind=location`, Overland, place+lat/lng.
