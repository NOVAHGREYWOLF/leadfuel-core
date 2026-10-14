# Handoff: INTELLIGENCE~ORACLE-READING-FACULTY 001

Background desk agent, stopped at the context guard (~310k). Ids only.

- Task: INTELLIGENCE~ORACLE-READING-FACULTY, pick rank 292, Conductor desk page MKAx49RAskZ3cV7f2EkDMF (desks/intelligence, tasks.ORACLE-READING-FACULTY).
- Repo: NOVAHGREYWOLF/novahub. Branch `intelligence/oracle-reading-faculty`, head 791ff000 (verified by `git ls-remote`). Base: main 9ccc242e.
- Draft PR: https://github.com/NOVAHGREYWOLF/novahub/pull/843 (body lists defaults taken, DOORS notes, follow-ups).
- Worktree: `F:\Leadfuel\repos\novahub\.claude\worktrees\oracle-reading-faculty`.

## Done
- `oracle/reading.py`, `oracle/reading_pack.py`, `oracle/kinds.py`; data `oracle/data/{tarot,iching,runes}.json` (41.0 / 22.0 / 11.0 KB).
- `brain.py` (embed_document refuses the kind, backfill excludes it) and `self_infer.py` (corpus load and new-item count exclude it).
- `tests/test_oracle_reading.py` (93) and `tests/test_oracle_reading_service.py` (32): 125 passed locally.

## Owed by the next agent (in this order)
1. Merge current `origin/main` into the branch.
2. `SKIP_TESTS=1 sh scripts/gates.sh` in the worktree; fix anything it raises (lint on the new files first).
3. Pytest on neighbours: `tests/test_oracle_*.py`, the brain/embed tests (`tests/test_embed_gateway.py` and any test naming `embed_document` or `backfill`), the self_infer tests (grep `_load_corpus`). No local full pytest.
4. Guard mutations, each must turn a test red, then revert: (a) `secrets` -> `random` in `draw`; (b) drop the `is_refused_claim` filter line in `reading_pack.build`; (c) wrap that filter in a try/except that keeps rows on error; (d) remove the `NOT_EVIDENCE_KINDS` check in `brain.embed_document`; (e) remove the `Document.kind.notin_` line in `self_infer._load_corpus`; (f) make `model_setting` return a model when unset; (g) drop `trace_check` in `compose`; (h) store `free` for numbers/chart; (i) move `_new_doc` after `render_free`. Record results in the PR body.
5. Update the PR body Checks section; push; verify head with `git ls-remote`; request DOORS and PRIVACY review per the brief. Do not merge, undraft or take ci-novahub.

## Taken on trust
- The router's read of hub main state and the owner-card defaults ('Money questions' yes-when-asked; 'Reading model and ceiling' none named).
