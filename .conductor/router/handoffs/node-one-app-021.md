# Handoff: NODE · one-app part · 21 (P3, phone read-only brain)

Session local_8b740825-c588-4608-9a5f-37e36ecba88e, at its context cap, 2026-11-07 ~23:25 PST.
Opener / report to: local_f22f96a8-948e-40cf-a88d-6a87803e23bf (`NODE · novah estate part · 1`).

## Done
- Branch `one-app/phone-brain` (local only; F:\Leadfuel has no remote), head 3d59e34, 5 commits
  on 9c1a530, worktree `F:\Leadfuel\.claude\worktrees\one-app-phone`.
- New `home-node/app/assistant/phone_tools.py`; changed `phonehost.py`, `PHONE.md`; new
  `tests/test_phone_tools.py`.
- 150/150 on the two touched test files. Live proof on side port 8107 from overlord, using commit
  98082da.
- lfdesk proxy note at `F:\novah-estate\evidence\lfdesk-trust-env-handoff.md`. Runbook P3 row
  updated.

## State
HOLD from the opener. Do not merge or restart until the owner answers the scope question and P1
(local_7147ccc1-693e-4e8c-a9de-e6eb2f905cf6) lands main. Default scope is `business`. Either answer
is `NOVAHOS_PHONE_SCOPE` in services.json env, then a restart.

## Not done
- Rebase onto main after P1, re-run both test files, then merge.
- Restart `novahos-phone` (announce the ~1 min gap first), then a live brain question from
  overlord on :8106.
- Static gates: unknown (no scripts/gates.sh in F:\Leadfuel).

## Gotchas
- The service runs the primary tree's `phonehost.py`, so it changes only once the branch is on main.
- A cold reply takes 90 to 100 s under load.
- Use `F:/repos/Prime/.venv/Scripts/python.exe -m pytest` from `home-node/app`.
