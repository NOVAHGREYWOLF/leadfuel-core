# Handoff: SENSORS · novah estate part · 1 (task web-liveness-collapse), note 001

Session local_c4f5b466-aec8-4253-accd-6470fcf9b3a5, router local_3dcfabeb-3f91-4824-a749-42f64c84f680 (ROUTER #126). Successor title: `SENSORS · novah estate part · 2`.
Brief: F:\Claude Sessions\handoff\web-liveness-collapse-brief-2026-11-18.md (from INTELLIGENCE local_b6ba70a1-04ad-4c24-9d74-139b30362339).

## Done
- Hub PR novahub#1132 (draft), branch `sensors/web-liveness-collapse`, head a982b441, worktree F:\Leadfuel\repos\novahub\.claude\worktrees\web-liveness-collapse.
- `web_liveness_collapse.py` (plan, check, collapse, undo, guard, status bar, stdin main), `tests/test_web_liveness_collapse.py` (46), `tests/test_liveness_soft_delete_readers.py` (sub-agent), two `deleted_at IS NULL` filters in `hostinger_ingest.py` and `estate_report.py`.

## State (verified by me: yes; re-read it anyway)
- Gates `SKIP_TESTS=1 sh scripts/gates.sh`: 14 of 16 green, 2 skipped. Targeted pytest: 46 passed, 50 passed (readers + estate_report + hostinger_door), on system python 3.12.10, not the repo `.venv`.
- Taken on trust: the 30,131 count, the 99 percent figure. Nothing touched production. No PR checks read yet.

## Next
1. Mutation checks (not done): drop a filter, `_is_protected` always False, no signature rewrite, no order check, barrier; each named test must fail. Re-run the two test files with `F:\Leadfuel\repos\novahub\.venv\Scripts\python.exe`.
2. Read CI on #1132; merge current main in; take the `ci-novahub` hold; merge on green `pytest` job on the exact head (filters must be live before any apply).
3. Ask Novah by name, in the desk's own chat, for a typed yes to the production READ (dry run). Then pipe the module on stdin: `Get-Content web_liveness_collapse.py -Raw` with a `WLC_CONFIG = r'''...'''` header into `railway ssh --service NovaHub -- /opt/venv/bin/python -`. Save the `@@PLAN` line to a file first. Clear a stale `RAILWAY_API_TOKEN` inside a .ps1 (memory: reference_fieldy_dump_via_railway_ssh).
4. Report dry run numbers (rows, runs, survivors, retired, rows per week, order disagreements, flap table, address sizes for the cap, findings diff). Stop. A second, separate yes before apply (`expect_sha`, `protect_from` from the plan).

## Owed / not delivered
- Message to INTELLIGENCE local_b6ba70a1 (desk exists; days_to_expiry finding) was UNDELIVERED. Re-send.
- STATUS to ROUTER #126 delivered earlier; send a CONTINUING with this note path.
- After PR open: `ccd_pr` get_status, bind_pr not done.

## Gotchas
Gates take over 5 minutes here; run in background. Passing options to the container goes by the `WLC_CONFIG` header, not arguments.
