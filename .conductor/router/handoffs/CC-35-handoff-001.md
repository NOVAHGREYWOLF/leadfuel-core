# CC-35 handoff 001 (ARMS desk, background agent for ROUTER #73, 2026-10-19). Ids only.

Brief: desks/CC-35.md + COMMAND-CENTER-DESK-BRIEF-COMMON-73.md (shared checkout, one-interface-research). Branch in every repo: `arms/cc-35-spoke-levels`, worktree `.claude/worktrees/cc-35-spoke-levels` in each repo.

## Done (pushed, draft PRs open)
- hub NOVAHGREYWOLF/novahub#918, head 55e3b5db: `spoke_level_reports.py` (new), `spoke_contract.py` (+level_gate column, record/read), `level_surfaces._part_row` asks `spoke_level_reports.judge`, `app.py` heartbeat passes `level_gate`. tests/test_spoke_level_reports.py 30 pass; gates 14/16 green, 2 skipped.
- reach NOVAHGREYWOLF/reach#42, head 6a80c6a: `spoke_levels.py` drop-in, `auth.owns_app` = `_paid_owns_app` then `spoke_levels.allows`, `/app` level-locked paid -> hub root, `spoke_worker.heartbeat` carries `coverage()`, `test_spoke_levels.py` (29, portable across spokes via `auth.LEVEL_KEYS`).
- scope NOVAHGREYWOLF/scope#29, head 99c0431: same, LEVEL_KEYS ("scope","smarticp"); bare pytest 66 passed (scope has no CI tests job).

## Left (start here)
1. **signal** (head 8983daf, WIP: drop-in + spoke_worker copied, NOT wired). Wire `auth.owns_app` exactly as scope (signal auth.py:103). LEVEL_KEYS ("signal","novahound"). Two `?upgrade=novahound` redirects: app.py ~438 (before_request gate, also has a JSON 402 branch) and ~617 (/app). scheduler.py:141,318 call AUTH.owns_app too (the level then also gates scheduled posts: say so in the PR). Copy reach's `test_spoke_levels.py`; signal CI has test.yml. Open a draft PR.
2. **odyssey** (head 6feabc6, WIP). odyssey `auth.owns_app(email, app_key=APP_KEY, *, is_admin=False)` at auth.py:186 has a different shape (is_admin kwarg; governance/storage.py uses it for plan caps). LEVEL_KEYS ("odyssey","novahunt"). Read odyssey's own posture before wiring.
3. **orbit** (head 6a9d0c5, WIP; files in apps/novahawk/). Orbit is NOT on the seed ladder (only the part `orbit_drafts`, which has no surface: a separate item). Wire `ri/leadfuel_auth.py:189 owns_app` the same way with LEVEL_KEYS ("orbit","novahawk") so the report exists; the verdict will be not_on_ladder.
4. After each spoke PR opens, add its link to hub #918's body ("Spoke PRs" list; currently only reach is named, add scope#29 too).
5. Final report to ROUTER #73: the STATUS line. The NEEDS-NOVAH gates are in #918's body: SPOKE_WORKER_ENABLED plus a per-spoke token so spokes heartbeat; LEVELS_DATABASE_URL if hub DATABASE_URL != SHARED_DATABASE_URL (RUNBOOK 0.2 is open); then LEVELS_5_8_OPEN and LEVEL_GATE_ENFORCE on the hub and the four ladder spokes.

## Notes
- Drop-in source of truth: the reach worktree's `spoke_levels.py`, `spoke_worker.py` and `test_spoke_levels.py`. spoke_worker.py was byte-identical across all five on origin/main before this change.
- Mutation checks are done on the hub (5/5 caught) and reach (11/11 caught). The shared scratchpad's `mutate.py` was overwritten by another agent: use your own file name.
- Not verified: whether production spokes heartbeat today; whether hub DATABASE_URL == SHARED_DATABASE_URL. No production read, no flag flip, no merge.
