# Handoff: SURFACE · ORACLE-FORTUNE-TELLER-ROOM 001

- Task: ORACLE-FORTUNE-TELLER-ROOM (pick 296, project one-interface), lane SURFACE, background desk agent.
- PR: NOVAHGREYWOLF/novahub#844 (draft, base main, stacked on #843: do not merge before it).
- Branch: `surface/oracle-fortune-teller-room`, head 36ed27a2 (pushed; checked with ls-remote). Faculty
  branch merged in at 40f8b8d7, main at 9ccc242e.
- Worktree: `F:/Leadfuel/repos/novahub/.claude/worktrees/oracle-room`.

## Done
- `oracle_routes.py`, `templates/oracle.html`, `static/oracle.{css,js}`, one register block in app.py,
  `tests/test_oracle_room.py` (37 tests, committed first while failing, d98eae3e).
- Customer gate: `oracle_routes.room_open_for`. Only an account on COMMAND_OWNER_EMAILS is admitted;
  an unset list admits nobody; everyone else gets a 404 on every route.
- Mutants on the gate, price-first, no-model-when-unset and the panel: all killed.
- Gates: `SKIP_TESTS=1 sh scripts/gates.sh` 14/16 green, 2 skipped. Touched file plus neighbours: 625
  passed. After the re-merge: 71 passed.
- Browser preview (local-only harness kept in scratch, not committed): saw the table, a three-card draw
  with its motion, the reading panel, a mark and the journal. The coin and rune motion was NOT watched.

## Left for the next desk
1. Wait for the hub `tests` CI on #844's head; report the result. Do not merge, undraft or take ci-novahub.
2. Watch the coin-throw and rune-pull motion in a preview. The harness is described in the PR body; re-create
   it from that description.
3. Act on the PRIVACY and DOORS review comments when they arrive.
4. Follow-ups, out of scope here (in the PR body): the world landmark, the phone tab, the
   once-per-person sentence, and the deck scans. Also two "needs from the faculty" items.
