# SURFACE firstwalk: handoff 002 (fold-a-firstwalk and chats-2)

Written by the SURFACE background desk for ROUTER #135, 2026-11-23, at its size cap. Branch
`surface/firstwalk-checklist-smoke` (draft PR 91). Re-read live state before acting.

## Done (committed and pushed)
- `firstwalk/render.py` (`--write`, `--check` drift guard) and its two outputs `docs/firstwalk/CHECKLIST.md` and
  `docs/firstwalk/checklist.html` (one self-contained page, radios, proof field, guarded localStorage, export of
  `firstwalk.marks/1`). Driven in headless Chrome with the network black-holed: marks, roll-up badges, missing-proof
  warning, notes, reload persistence and export all behaved.
- `tests/test_firstwalk_smoke.py`: 131 tests, run alone (`python -m pytest tests/test_firstwalk_smoke.py -q`).
- `smoke.py`: action-feed check (R04 no longer fails for Contracts and Log), ids in comments no longer count as
  present, per-cell files (`--cells-dir`), more positive controls, an unreadable `--marks` file is exit 3.
- Real run at 2026-11-23T23:04Z: results in `F:\Claude Sessions\handoff\ROUTER-135\firstwalk\` (`results.json`,
  `cells\<scoreboard cell id>.json`, `inputs\`). chats-2 rows in
  `F:\Claude Sessions\handoff\ROUTER-135\chats-2\NOT-BUILT-ROWS.json`.

## Left
- Nothing blocks the PR. To refresh the preflight after the owner walks: `python firstwalk/smoke.py run --marks
  <exported file> ...` (flags as in the PR body); re-run the acceptance tool and the vault reader first.
- If the scoreboard (PR 92) renames a cell id, edit `scoreboard_cells` in `firstwalk/walk.json` and run
  `python firstwalk/render.py --write`.
- Merge is the merge-train desk's, on a green CI `pytest` job on the exact head.
