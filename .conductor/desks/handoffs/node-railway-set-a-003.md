# Handoff: NODE · RAILWAY-SET-A 2/2 · cutover merges — 003

Desk session local_1137441b. Written ~2026-10-13 03:0xZ UTC at ~305k tokens. Earlier notes: node-railway-set-a-002.md and node-railway-iac-001.md in F:/Claude Sessions/.conductor/desks/handoffs (local only: that repo's push is disabled).

## Done (verified by this desk on 10-13 unless marked)
- Railway Set A cutover COMPLETE, 9 of 9: scope #23, orbit #30, reach #34, lucid #126, echo #55, novahub-mcp #37, odyssey #49, hub #699, signal #29 (merged 10-13 01:16Z by ROUTER #43's NODE agent, not this desk; no proof comment on the PR).
- `railway deployment list` newest per service, all SUCCESS: NovaHub, NovaHawk, NovaHerald, NovaHound, lucid, echo, novahub-mcp, odyssey, SMART ICP, novahub-cron-15min, Odyssey Cron: configFile None. novahub-cron-daily: still /deploy/cron-daily.toml (on hold, card q246).
- /healthz 200 on every web domain; mcp /health 200.
- Wait-for-CI PRs merged: scope #26, orbit #32, reach #37, signal #31, echo #56, novahub-mcp #38, odyssey #51. Hub #737 still draft. reach applied by this desk 10-05. Whether the others were applied: a read-only plan agent was running at handoff; result not yet in.
- Owner set SOURCE_WATCHDOG_ENABLED on 10-06 (already 1, no-op).

## Next
NODE~HUB-RAILWAY-TS-DRIFT (filed unqueued by conductor 032; ROUTER #44's finding, card q246 hold): add preserve() for the six live NovaHub variables named in board key for_conductor_031_from_router_44 to hub .railway/railway.ts, re-plan to 0 destroy, draft PR, CI, merge. The apply is deploy config: Router desk card, owner clicks. Then the owner clears cron-daily's path. Then remove the cron tomls (hub deploy/cron-15min.toml, cron-daily.toml; odyssey railway.cron.toml), updating RUNBOOK.md, docs/RAILWAY_CRON_SETUP.md, docs/CRON_INVENTORY.md, scripts/cron_tick.py, app.py strings, and tests/test_daily_due.py, which reads cron-daily.toml. Hub #737 is not applied before the drift fix.

## Owed
- Owner said in this chat (10-13): "check the railway that is done. then lets finish the other desks. we want to make sure nothing is outdated." Whether the drift task counts as queued by that: ask ROUTER (router/current) or the owner.
- Unowned, deadline 2026-12-01: leadfuel-intake (railway.toml) and JobHunter (railway.toml, frontend/railway.toml) have no .railway IaC.

## Gotchas
- `railway config apply` redeploys the service. The permission check refused a deploy-status read once (10-05).
- Read-only plan: run from the repo's railway-iac worktree; railway/iac resolves from the repo-root node_modules.
