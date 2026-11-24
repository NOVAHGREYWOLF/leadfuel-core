# redline-6 handoff: what is built, what a fresh agent builds next

Agent of ROUTER #135 (NODE, wave 3), 2026-11-23. Ids only; no secrets. The triage itself is
`docs/ONE_APP_GAP_TRIAGE.md` (this PR). Re-read live state before acting; do not trust the state lines below.

## Done in this PR
- `docs/ONE_APP_GAP_TRIAGE.md`: all 57 proposals, room, state on estate `main` `96a57c9`, disposition, why, the
  proposed order, the doc 38 rows still open. `tests/test_one_app_gap_triage.py` fails if a proposal is missing,
  repeated, has an unknown disposition or room, an empty cell, or if the counts in the prose differ from the rows.

## Not done: the build-now PRs (none was started; I hit the size cap first)
Where they go: the app is `home-node/app/assistant/` in the **estate repo** (`F:\Leadfuel`, remote
`leadfuel-estate`). Its push URL is deliberately disabled ("VAULT sync rewrites SHAs", `F:\Claude Sessions\scripts\VAULT_PRIVATE_SYNC.md`:
the sync script is the only push path; do not set a push URL). So a branch there is local until the 04:30 PT sync
pushes it, and a draft PR can only be opened after that. I made one worktree for it, no commits:
`F:\Leadfuel\.claude\worktrees\redline-6-gap-triage` on branch `node/redline-6-gap-triage` from `main`. Use it or
add your own. Interpreter: `F:\Leadfuel\home-node\build\venv-assistant\Scripts\python.exe`, tests with
`python -m unittest assistant.tests.<module>` from `home-node/app`. Targeted tests only, no full suite.

1. **Forward the done-chunk warnings** (GAP-03 and GAP-04 residue; highest value). `assistant/turn.py` `_map`, the
   `done` branch, returns tokens and model and drops `meta["warnings"]`. Fix: for each dict in `meta.get("warnings")`
   emit `self._emit(C.WARNING, turn_id=self.id, code=w["code"], message=w["message"])` before returning usage (guard
   for non-list and missing keys; a malformed entry must still say something, not vanish). The page already draws
   `warning` events (`ui/app.js` `case "warning"`). Add tests in `assistant/tests/test_turn.py`: a done chunk with
   `CONTEXT_COMPACTED` yields one `warning` event; no warnings yields none; a malformed entry yields a warning
   (code `WARNING_MALFORMED`), not nothing. Probe that shows the bug (run from `home-node/app`; prints
   `warning events: []` today):
   `from assistant.tests.test_turn import run; from assistant.contract import Chunk;
   t, evs, s = run([Chunk(kind="text", text="hi"), Chunk(kind="done", meta={"stop_reason": "end_turn",
   "warnings": [{"code": "CONTEXT_COMPACTED", "message": "x"}]})]); print([e for e in evs if e["e"] == "warning"])`.
   Engine warnings that will now surface: `CONTEXT_COMPACTED`, `CONTEXT_TRUNCATED`, `TOOL_BATCH_DISCARDED`,
   `TOOL_CALL_REPEATED`, `MAX_TOOL_CALLS` (`lfdesk/engine/local.py`). Also update the stale "compaction_note" in
   `ctxgate.py` (`compacted_last_turn`) once an event exists. `turn.py` is shared (check the SESSION_MAP row before
   editing; it is NODE's `home-node/` by the map).
2. **GAP-05**: register `Ctrl+Shift+E` (open the session rail and focus `#ctxeffort`, `ui/ctxbar.js`) and
   `Ctrl+Shift+B` (open Code, Preview tab: `NovahCode.addTab({id:"preview"})` in `ui/preview1.js`) in `ui/keymap.js`,
   update its header comment (it still says "no browser pane"), and the shortcuts sheet test. Chords are
   registered with `K.register({id, keys, label, group, handler})`.
3. Later slices, one desk each, listed in the triage "Proposed order" items 4 to 6.

## Verified here vs on trust
Verified (ran): anchor check on main (56 of 57 first pass, GAP-16 anchor was mine and wrong), 364 targeted tests OK
on a clean main worktree, the warnings probe, the triage test (3 passed). On trust: the desks' handoffs for
browser looks and "not seen in the real window"; the VAULT sync schedule (read from its doc, not queried).

## Owner step
Approve the order in `docs/ONE_APP_GAP_TRIAGE.md` (one card). Nothing else needs him.
