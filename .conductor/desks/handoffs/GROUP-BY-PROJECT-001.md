# GROUP-BY-PROJECT handoff 001 (NODE, background agent of ROUTER #28)

2026-10-07, about 10:3x UTC. Public repo: ids, titles, status and PR numbers only.

## Done
- Draft PR #35 (base `way/plugin`, head `way/group-by-project`) is open: leadfuel-way 0.1.8.
  - Desks are titled `LANE · <project part> · n` and filed in their project's sidebar group.
  - The archive guard reads the desk's own group from `get_session` on `self`.
  - `move_sessions` naming more than one session is refused.
  - Older title forms are still read exactly as before.
  - Six skills, the banner, the README and hooks.json are updated.
  - New tests in `tests/test_way_projects.py` (119 cases).
- Source: the owner in conductor 019 (`local_1a4942ec`), pick `NODE~GROUP-BY-PROJECT`.

## State
- Bare `pytest` passed 494 of 494 on commit 51af74f.
- CI `pytest` passed on 51af74f.
- The last commit, 28a24c0, is wording only, in the router and new-project skills. Its runs were in flight at handoff; read PR #35 for the result.

## Next
- The owner confirms the title format; the three points are in the PR body under "OWNER CONFIRMATION".
- After the owner confirms: undraft and merge into `way/plugin`.
- The owner installs it with `git pull` in the marketplace checkout, then `claude plugin update leadfuel-way@leadfuel`.

## Owed
- Follow-up for whoever owns `watch/sessions_desk_feeder.py`: its title parser reads only `LANE · TASK n/m · topic`. New-form titles show the lane only.
