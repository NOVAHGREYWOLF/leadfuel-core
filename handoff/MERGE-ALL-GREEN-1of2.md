# Handoff: WATCH · MERGE-ALL-GREEN 1/1 -> 2/2

Predecessor: local session "WATCH · MERGE-ALL-GREEN 1/1 · merge every green PR". Task: picks/u-merge-all-green.
Router: ROUTER #19 (local_b8b79bf8). It was ROUTER #13 (local_21748811) before that.
Report: reports/MERGE-ALL-GREEN.md on leadfuel-core branch claude/optimistic-ardinghelli-c2be56.
Re-read every state line below with gh, git ls-remote and the lock dirs before acting. All times are UTC.

## Owner authority in hand
- On 2026-10-02 the owner said to merge every green PR (via CONDUCTOR).
- On 2026-10-03 the owner asked this session directly to run Set B. After a classifier denial, the owner said "Try again" in this session on 2026-10-05. A successor session needs its own owner word for `railway config apply`; this note is not that word.

## Done
- Merged: odyssey#50 (8e9d136), novahub-mcp#35 (1e18f2d), orbit#26 (b40e800).
- Set B (wait for CI, checkSuites true), merged and applied. orbit deploy 589e8025 SUCCESS:
  - signal#31: 4633b82; applied 2026-10-05; deploy 250a640c SUCCESS.
  - scope#26: 2938e6e; deploy 6c4578cf SUCCESS.
  - orbit#32: 894dc71; deploy check was running.
  - echo#56: a35d5c9; applied ~09:45Z. Its deploy was NOT confirmed: check `railway deployment list --service echo` from F:eadfueleposecho.
- reach#37: merged and applied by NODE · RAILWAY-SET-A 2/2 (ROUTER #19), not by me.
- Set A (remove railway.toml): ROUTER #13 took these on the owner's card q187. I have not verified them.

## Left
1. **odyssey#51 and novahub-mcp#38** (Set B). For each: take ci-<repo>; update-branch; CI green on that head; plan from the head with `scratchpad\rw.ps1 -Mode plan`; `gh pr ready`; check main is unmoved; squash with `--match-head-commit`; re-plan from merged main; apply only if the plan is exactly `checkSuites` (null -> true) plus default-null lines with 0 destroy; confirm the deploy; release the lock.
   - The odyssey plan may cover two services (odyssey and Odyssey Cron).
   - The railway/iac SDK needs `$env:_` set to `%APPDATA%\npm\node_modules\@railway\cli\bin\railway.exe`, plus a node_modules junction to the checkout. rw.ps1 does both; copy it from this session's scratchpad or rebuild it from the report.
   - An apply also starts a production deploy of main's head, which now waits for CI.
2. **Hub #737** stays held until the hub CI runners are rebuilt.
3. **Hub ticket** `ci-novahub.wait/20261002T212711Z-WATCH-MERGE-ALL-GREEN` covers #717, #715, #726, #721 and #638. Re-check each one: other desks may have merged them since 10-02.
4. Hub #714 (nixpacks) went to ROUTER #13 on 10-03. Check its state.
