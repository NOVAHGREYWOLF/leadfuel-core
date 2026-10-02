# SUITE · the gate's blind spots — handoff 002 (desk 2/2)

Lane SUITE. Ids, titles and status only.

## Done
- hub #725 squashed as e42b661: one-door probe race, getsource ban message, gates.sh deselect removal (591 -> 601 root tests). CI green on head f1da976 (gates, pytest, pip-audit), main unmoved at merge.
- ci-novahub released after #725; PRIVACY 2/2 woken.

## Next (one task)
hub #657, branch fix/scratch-dirs-are-not-created-to-be-discarded (worktree F:\Leadfuel\repos\novahub\.claude\worktrees\suite-scratch, head bcd2736 when last read).
- Its pytest job died mid-smoke-step on 2026-09-27: step conclusions empty = runner died, not code. Lint and pip-audit were green.
- Ticket: ci-novahub.wait/20261002T125422Z-SUITE-2of2-657-rerun (20th of 20 at 2026-10-02 ~13:00Z). Body says READY NOW.
- Inside the hold: merge main in -> push (fires CI) -> CI green on current head -> main unmoved -> squash -> release and message the next waiter by name. Two checkout deaths (RPC failed / early EOF) -> release and message the next waiter.
- Re-read live state (gh, git ls-remote, the lock dir) before acting; do not trust these lines.

## Not mine to start (sent to the conductor as candidate tasks)
- Six run-B failures, order/time dependent; need the full-suite slot.
- scripts/check_export_harvest.py is missing, so gates.sh SKIPs the export-harvest gate.

## Gotchas
- NEVER stop processes by command-line pattern. I killed about 12 other desks' pytest runs with a '-m pytest' filter. Stop only a PID you started and verified.
- Do not merge main into a worktree while a test run is using it: the run measures a changed tree.
- A local smoke run once crashed with Windows fatal exception 0xc000070a in test_wall_goal_lens (passed 25/25 alone); cause unknown, not reproduced.
- Branch protection returns 403 on this plan; waiting for green is a convention.

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
