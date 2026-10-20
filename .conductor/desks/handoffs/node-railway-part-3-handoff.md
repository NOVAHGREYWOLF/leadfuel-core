# Handoff: NODE · railway part · 3 (local_dc622035-52f8-4e86-a4c9-ec5eb503b1b9) → part 4

Written 2026-10-20 ~06:55Z UTC at ~310k tokens. Full evidence: `node-railway-part-003.md` in this folder (same branch, claude/node-railway-part-3). The state lines below are not to be trusted: re-read them.

## Done
- Railway Set A verified live 10-13; hub drift (#756 fixed the first six names; two more appeared) answered by hub #963.
- Five docs/comment draft PRs open (agents wrote, I read every diff): signal #38, reach #44, lucid #129, orbit #39, odyssey #60 (also deletes railway.cron.toml; AST of its 4 edited .py files identical, plan from its branch unchanged).

## State (mine, 06:55Z)
- **I HOLD `F:/Claude Sessions/.locks/ci-novahub`** (stamp held-by-NODE-railway-part-3--local_dc622035…), offered by ROUTER #87 local_b72e16fa. hub #963 head fd8dcfdb (main 175d5955 merged in), undrafted, CI run 39382205705 in progress; gates 14/16, test_daily_due 46 passed, plan 0 destroy. A background watcher (task biv3ieuwx) will report. If I am gone: read the run; on `success` with steps>0 and `git ls-remote origin main` still 175d5955, `gh pr merge 963 --squash --match-head-commit fd8dcfdb`; then rm the lock, `ls` the .wait dir, message the next waiter and ROUTER #87. If CI fails or main moved: merge main in again, re-run, or release. Never leave the lock held.
- Approval basis named to #87: owner's typed word "go" in this desk's chat (not a card).

## Next
1. Land #963 (above), release the lock.
2. Post the Router desk card for the hub APPLY (owner clicks): re-run `railway config plan` from fresh hub main first; expect 0 destroy, SELF_CAPTURE_ENABLED set, cron-daily "0 12 * * *" → "50 * * * *". THEN the owner clears novahub-cron-daily's config path (q246). Never earlier.
3. Land the five docs PRs one by one (each repo's `ci-<repo>` lock, CI green on exact head).
4. Then hub `deploy/cron-15min.toml` removal and hub docs (see report note, Next 3).

## Owed
- Owner: migrate-or-retire JobHunter and howlclip (NODE~RAILWAY-SET-B, unqueued). Not started.

## Gotchas
Run `railway config plan` from PowerShell with `$env:_` = the real railway.exe (npm\node_modules\@railway\cli\bin). ci-novahub queue is long.

## ADDENDUM 06:5xZ UTC (supersedes the lock lines above): hub #963 MERGED, lock RELEASED
- hub #963 squashed as 4cfe4846 (--match-head-commit fd8dcfdb) after pytest success on that exact head (12 of 12 steps), lint and security success, main unmoved at 175d5955. I verified each of those myself with gh and ls-remote.
- `ci-novahub` lock RELEASED (my stamp checked before rm); ROUTER #87 local_b72e16fa told (delivered, not confirmed read). **Nobody holds the lock on my account any more; ignore the "I HOLD" line above.**
- Next 1 is DONE. Start at Next 2: post the Router desk card for the hub apply (re-plan from fresh main first), then the docs PRs, then hub cron-15min.toml.
