# Handoff: SENSORS · novah estate part · 2 (task web-liveness-collapse), note 002

Session local_116f2b3e-fea7-4f3f-a0da-3784af88e7bd, router local_3dcfabeb-3f91-4824-a749-42f64c84f680 (ROUTER #126). Predecessor part 1 (local_c4f5b466) is archived. Successor title: `SENSORS · novah estate part · 3`. Earlier note: web-liveness-collapse-001.md. Brief: F:\Claude Sessions\handoff\web-liveness-collapse-brief-2026-11-18.md.

## Done
- Hub PR novahub#1132 (draft), branch `sensors/web-liveness-collapse`, head e74a73c5 pushed (5df435a4, e74a73c5 on top of a982b441). Worktree F:\Leadfuel\repos\novahub\.claude\worktrees\web-liveness-collapse.
- Mutation checks: 20 guards broken once; 16 killed, 4 survived (barrier, apply live scope, rowcount checks, cap in digest). Tests added; second pass killed all but one equivalent mutant (m21). Scripts: F:\Claude Sessions\handoff\web-liveness-collapse-mutate.py and -mutate2.py (arg: output json path).
- Independent review (sub-agent, finished) found: stale report baseline in check(), survivor kept first days_to_expiry, weak write guard, apply could run before readers deployed, undo unchecked. All fixed in e74a73c5.
- My own find: a WLC_CONFIG line above the module is a SyntaxError (`from __future__`). Now the module has one `WLC_CONFIG = None` line the launcher replaces; plan for undo rides as `plan_json`.

## State (me: verified 73 tests pass on e74a73c5, repo venv; NOT verified below)
- Gates on e74a73c5: not run (the run on 5df435a4 gave no output). CI on e74a73c5: not read. Mutation pass on the final guard and check code: not run. Hub main moved 8 commits past a982b441 (CI green on a982b441 does not count).

## Next
1. `SKIP_TESTS=1 sh scripts/gates.sh` in the hub worktree, in the background (over 5 minutes).
2. Merge origin/main in, push. Take `ci-novahub` (README at F:\Claude Sessions\.locks\README.md; lock was FREE with 5 old INTELLIGENCE tickets queued, nothing reaped, heads not found among live peers), pytest job success on that exact head, `ls-remote` main unmoved, mark ready, squash, release. Then confirm the deploy finished (GitHub deployments for the repo).
3. Ask Novah BY NAME, in your own chat, for a typed yes to the production READ. Until then no Railway at all. Launcher (compile check built in): F:\Claude Sessions\handoff\web-liveness-collapse-wlc_run.ps1, `-Mode dry -ModulePath <file saved from git show origin/main:web_liveness_collapse.py> -OutDir <dir>`. It saves @@PLAN first. Report: rows, runs, survivors, retired, weekly, order disagreements, flap before and after, address sizes, findings_gone, findings_new, collapse_gone, readers_skip_retired. Stop. A second yes before apply.

## Owed
- Both typed yeses. Follow ups, not mine: brain.count_unembedded counts retired rows (cosmetic); the INFO text "in N probes" will read 1 (INTELLIGENCE owns _check_liveness).
- STATUS to the router: send CONTINUING from your first turn.

## Gotchas
Bash tool halves backslashes (use Write for files). A Bash `cd` into F:\Claude Sessions changed my cwd; use absolute paths.
