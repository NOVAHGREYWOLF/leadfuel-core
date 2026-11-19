# Handoff 001: SURFACE · one-interface part · 18

Session `local_f1a8ccd5-28d7-4b88-b1a5-f38f7b1ff15a` (Opus), nested under part 17 (archived), group one-interface. No router: the owner talks to this desk. Private build material: `F:\Claude Sessions\handoff\surface-one-interface-18\material.md`.

## Done
- Boards D (game first, the AI drives the screen) and D2 (same moment, Plain skin) published on Design canvas `RTbymAgoSTKozb7h5kHbPp` and opened for the owner.
- Globe: gates 14 of 16 green (2 skipped by design); 34 touched-file test files, 1,933 passed; phone width looked at locally. Branch `surface/command-globe-imagery` pushed at `1ca5c7f1`; draft PR NOVAHGREYWOLF/novahub#1122, bound to this session.
- Part 15 found already archived; part 17 archived by me (read back).

## State (re-read before acting)
- CI on `1ca5c7f1`: lint and security success. tests/pytest attempt 1 FAILED, 1 of 14,928: `tests/test_command_rungs.py::test_no_test_names_it_is_an_empty_list_and_differs_from_unknown` (`assert [] is None`). Not this diff (no Python touched; main `94e64d48`, this branch's base, passed it). Cause read, not proven: the test writes one file twice in quick succession and `command_focus._parts_cache` is keyed by mtime. Attempt 2 (re-run of the failed job, run 44461670911) was pending at handoff.
- `F:\Claude Sessions\.locks\ci-novahub` is HELD by me (`held-by-SURFACE-one-interface-18--local_f1a8ccd5`). The successor takes over the hold: replace that stamp with its own, then finish the sequence and release. The `.wait` queue holds 5 tickets 12-43 days old whose desks are not live sessions.

## Next
1. Read attempt 2 of the tests run on `1ca5c7f1`. On success: `git ls-remote` main still `94e64d48`, mark #1122 ready, squash-merge, release the lock. On a second failure of the same test: do not touch the test; report it and card it.
2. Redraw board D inside the NovahOS Windows app window (owner's words verified in part 15's transcript; the brief is in the material file), one sub-agent, then publish D plus canvas.json.
3. Tell the owner: a merge does not reach production until a Railway plan is picked (q9518).

## Owed (owner decides)
- Which launch "hook it all up" follows (assumed: the NovahOS setup guide). q9518 Railway plan.
