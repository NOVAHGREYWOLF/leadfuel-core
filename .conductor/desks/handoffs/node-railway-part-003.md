# Report: NODE · railway part · 3 — "check the railway that is done" (2026-10-13)

Desk session local_dc622035-52f8-4e86-a4c9-ec5eb503b1b9 (successor of local_1137441b, archived after its handoff `node-railway-set-a-003.md` was confirmed pushed at a07f0dc with a clean worktree). Router per board `router/current`: ROUTER #48 local_e4ee0816-7d58-4bfd-a102-f02d188116af. All times UTC. Read-only throughout: no `railway config apply`, no variable read, no Railway write.

## Verdict
The Set A cutover is real and live. Every claim in the predecessor's handoff held when re-read, with three things it did not know (below). Nothing was changed on Railway or in any repo.

## Verified by this desk (own commands, ~02:35-03:10Z)
- **PRs (`gh pr view`, 17):** the nine cutover PRs (scope #23, orbit #30, reach #34, lucid #126, echo #55, novahub-mcp #37, odyssey #49, hub #699, signal #29) and the seven wait-for-CI PRs (scope #26, orbit #32, reach #37, signal #31, echo #56, novahub-mcp #38, odyssey #51) are all MERGED. Hub #737 is OPEN, draft, last updated 10-02.
- **Newest deployment per service in project LeadfuelBusinessSuites (`railway deployment list`):** SUCCESS for NovaHub, NovaHawk, NovaHerald, NovaHound (6aa40956, the signal cutover), lucid, echo, novahub-mcp, odyssey, SMART ICP, Odyssey Cron, novahub-cron-15min, novahub-cron-daily. configFile is empty on all of them except novahub-cron-daily (`/deploy/cron-daily.toml`, on hold) and the unrelated `web` service (`/railway.toml`).
- **Health:** `/healthz` 200 on life, novahawk, orbit, novaherald, reach, novahound, signal, smarticp, scope, odyssey, lucid, echo and onboard `.leadfuel.cloud`; mcp `/health` 200. (onboard answered 000 once from a local TLS revocation check; 200 with the check off.)
- **Settings match the files, read from production:** read-only `railway config plan` from a detached worktree at each repo's origin/main (scope, orbit, reach, signal, lucid, echo, novahub-mcp, odyssey): **0 to destroy** in all eight, and the only diffs are the known Railway default lines (`restartPolicyType`, plus `numReplicas` on NovaHound). No `checkSuites` diff, so wait-for-CI is live on scope, orbit, echo, novahub-mcp, signal.
- **Odyssey #51 was the one the predecessor could not say (no worktree). Answered:** the plan is clean AND I proved the plan can see the field: flipping `checkSuites` to false in a throwaway copy made it print `source.checkSuites (true → null)` for odyssey and Odyssey Cron. So it is applied and live on both. (A plan that cannot see a field also prints no diff; this control is what makes the clean result mean something.)
- **Hub plan on main a929fc72 (read-only), 10-13:** 6 to destroy (six live NovaHub variables the file does not name; names are on the board key `for_conductor_031_from_router_44`, not repeated here) and `novahub-cron-daily deploy.cronSchedule ("0 12 * * *" → "50 * * * *")`. This reproduces ROUTER #44's finding exactly, so it is still open today. Anyone running `railway config apply` on hub now would delete those six variables.
- **Throwaway worktrees:** the nine I made under each repo's `.claude/worktrees/node-railway-plan-3` are removed (each was clean).
- **Repos on origin/main:** the Set A `railway.toml` files are gone everywhere. Still present: odyssey `railway.cron.toml`; hub `deploy/cron-15min.toml`, `deploy/cron-daily.toml`, `deploy/cron-weekly.toml` (no service for weekly).

## Three things the handoff did not have
1. **A third repo is uncovered, and the handoff listed two.** Railway services still on `railway.toml` with no `.railway/railway.ts` (checked by `gh api` tree and by each service's newest deployment): leadfuel-intake (project LeadfuelBusinessSuites, service `web`, onboard.leadfuel.cloud, `/railway.toml`), **howlclip (project HOWL, service `web`, `/railway.toml`, last deploy 07-27; not previously named)**, and JobHunter (project NovaHunt, 13 services: 12 on `/railway.toml`, `JobHunter_FrontEnd` on `/frontend/railway.toml`, all last deployed 08-10; `JobHunter_Backend` and Redis are SLEEPING). That is 15 services across 3 repos with the 2026-12-01 cutoff on all of them.
2. **Stale docs.** Five of the nine Set A repos still tell a reader the service is configured by `railway.toml`: orbit (README, `docs/DEPLOY.md`, `docs/DEPLOY_CHECKLIST.md`), reach (README), lucid (README), signal (`gunicorn.conf.py` comment), odyssey (README, `SUITE_DEPLOY.md`, comments in `app.py`, `db.py`, `release.py`, `readiness.py`). Hub's are already planned for the toml-removal step.
3. **`APOLLO` (LeadfuelBusinessSuites) has been CRASHED since 2026-07-07**, no source repo, no domain use known. Not mine; flagged for the owner.

## Took on trust
- The 2026-12-01 cutoff: the IaC file headers say it, and a web search of Railway's changelog and forum agrees (secondary sources; I did not read a Railway primary page). That search also mentions a forum claim that a later CLI (5.49.2) removed `railway config`; unverified, and this machine has 5.43.1. **Do not upgrade the Railway CLI before the IaC work is finished.**
- ROUTER #44's "subscription is past due" banner: not visible to a CLI; the owner has been told.
- That clearing a service's config path makes Railway fall back to the stored service value: from #44's plan reading and the toml's own comments, not tested.

## Next (answered 10-13 ~03:4xZ; nothing started, desk idles)
ROUTER #48 (one-interface, rotating) replied that it is NOT the router for Railway and decides none of RW-1..RW-3: Railway Set A is held by the owed-questions routers (#43, #44, #46; #46 is rotating, successor ROUTER #50 is a paste prompt, not yet live). Only owner-queued tasks start.
- **Landed (board router/current, now v524, committed):** key `for_conductor_034_from_node_railway_part_3` (files NODE~RAILWAY-SET-B and NODE~RAILWAY-TOML-AND-DOCS-CLEANUP, both unqueued, my claim) and key `for_router_50_from_node_railway_part_3` (the three owner decisions, for #50). ROUTER #48 recorded my message on router/relay48 key railway_asks.
- **Not sent:** nothing to ROUTER #46 or #50 (neither is taking messages; the board key is the channel). My first send to #48 was queued, not confirmed read.
- **Waiting on the owner's queue click or typed word, in order:** NODE~HUB-RAILWAY-TS-DRIFT (preserve() for the six variables in hub .railway/railway.ts, re-plan to 0 destroy, draft PR, CI, merge; the apply stays a Router card; then he clears cron-daily's path; hub #737 must not be applied first) then NODE~RAILWAY-TOML-AND-DOCS-CLEANUP, then NODE~RAILWAY-SET-B (first question: migrate or retire JobHunter and howlclip).
- Anyone starting NODE~HUB-RAILWAY-TS-DRIFT: work from a hub worktree on a fresh branch from origin/main; #737 is stale and has not been rebased.

## Gotcha for the next desk (cost me ten minutes)
`railway config plan` fails with "requires Railway CLI 5.42.1 or newer" even on 5.43.1 when run from Git Bash or via the `railway` npm shim: the SDK runs `$_ --version`. Use PowerShell with `$env:_` set to the real exe, `C:\Users\novah\AppData\Roaming\npm\node_modules\@railway\cli\bin\railway.exe`, and run from a worktree whose repo root has `node_modules/railway`.

## Update 2026-10-20 ~05:50Z UTC: the owner typed "go" in this desk's chat (a session id, not a queue click)
I took "go" to cover RW-1 and RW-2 (the two my last message said needed a typed word). NOT covered, not started: RW-3 / NODE~RAILWAY-SET-B (needs the owner's migrate-or-retire answer first), APOLLO-LOOK, VARIABLE-NAMES-CHECK. The Conductor desk still shows no picks row for any of my tasks.

### Re-read first (verified by me, 10-20)
- The six original undeclared variables are FIXED on hub main by #756 (merged 10-14 01:41Z, NODE atlas part 1). Hub main af269a48 plan then read: 2 to destroy (ORACLE_CUSTOMER_TERMS, WORLD_INTELLIGENCE_PAGE: live, undeclared) + SELF_CAPTURE_ENABLED to be set (declared "1", owner q212=B, intended) + novahub-cron-daily schedule "0 12 * * *" -> "50 * * * *" (intended, #789 q298=A) + restartPolicyType default. Third round of the same drift: `RAILWAY-VARIABLE-NAMES-CHECK` (unqueued) is what stops a fourth.
- odyssey Cron and novahub-cron-15min newest deployments: configFile empty. novahub-cron-daily: still `/deploy/cron-daily.toml` (hold stands).

### Open draft PRs, all mine, none merged, none undrafted
| PR | What | State |
|---|---|---|
| hub #963 (node/railway-preserve-oracle-world, bb1a86b2) | `preserve()` for the two names; plan from the branch = 0 destroy, 3 intended changes | gates 14/16 green (2 skipped by flag), tests/test_daily_due.py 46 passed; CI `tests` queued; **wait ticket filed in `F:/Claude Sessions/.locks/ci-novahub.wait/20261020T052726Z-NODE-railway-part-3--railway-preserve-pr963`** (13 other waiters ahead or alongside; do not poll, the releaser messages by name) |
| signal #38 | one comment in gunicorn.conf.py | diff read by me |
| reach #44 | one README line | diff read by me |
| lucid #129 | one README sentence | diff read by me |
| orbit #39 | README + docs/DEPLOY.md + docs/DEPLOY_CHECKLIST.md | diff read by me |
| odyssey #60 (e69920e) | deletes railway.cron.toml; comment/docs edits in 12 files | I re-checked: AST of app.py, db.py, release.py, readiness.py identical with docstrings normalised; read-only `railway config plan` from the branch = same as main (only the restartPolicyType default), so the railway.ts edits are comment-only. Took on trust: its local failure of test_migration_type_expressions_are_resolvable on main too (pgvector missing on this PC); CI decides. |

Agents (Sonnet) wrote the five docs PRs under briefs I gave them; I reviewed every diff. They ran no Railway commands.

### Next, in order
1. Per PR above, when its CI is green: undraft, merge main in, CI `pytest`/test job `success` on the exact head, `mkdir` the repo's `ci-<repo>` lock (hub's is the long queue; others have their own `.locks/ci-<repo>`), `ls-remote main` unmoved, squash `--match-head-commit`, release. Every merge to main redeploys that service (comment/docs-only, harmless; checkSuites on waits for CI).
2. After #963 lands: the apply of hub's file is a Router desk CARD (owner clicks): sets SELF_CAPTURE_ENABLED, the cron-daily schedule and the default line, 0 destroy. Re-run `railway config plan` from fresh main immediately before posting the card (the file moves every few days). Then the owner clears novahub-cron-daily's config path (q246). Never before the apply: it would drop the schedule to `0 12 * * *` and the 06:00 owner-local gate would never fire.
3. After that: remove hub `deploy/cron-15min.toml` (path already cleared), later `deploy/cron-daily.toml`, and fix hub's docs and scripts (RUNBOOK.md, docs/RAILWAY_CRON_SETUP.md, docs/CRON_INVENTORY.md, scripts/cron_tick.py, scripts/gen_cron_inventory.py, app.py strings, tests/test_daily_due.py reads cron-daily.toml). Look at gen_cron_inventory.py first: it may generate the inventory from the toml files.
4. Stale lines the agents flagged and did not touch: every repo's `.railway/railway.ts` header still says "WHILE railway.toml STILL EXISTS it wins" (comment-only fix; odyssey #60 already did its own); orbit DEPLOY_CHECKLIST says "no root-dir change needed" (Root Directory is /apps/novahawk); orbit DEPLOY.md line ~61 says signal has no /healthz route (signal's railway.ts sets it); orbit DEPLOY.md step 2 and lucid Deploy step 1 are new-service recipes that predate IaC.
5. RAILWAY-SET-B and the others wait for the owner's queue.

### Gotchas learned
- `ci-novahub` is held by a LANDER background agent and has a 14-ticket queue (one waiting 370 h): a merge there is hours or days away, not minutes. `python "F:/Claude Sessions/scripts/lockq.py"` shows it read-only.
- The plan needs PowerShell with `$env:_` set to the real railway.exe (see the gotcha below).
