# Handoff: SURFACE · ORACLE-FORTUNE-TELLER-ROOM 002

- Task: ORACLE-FORTUNE-TELLER-ROOM (pick 296, project one-interface), lane SURFACE, background desk agent.
- PR: NOVAHGREYWOLF/novahub#844 (draft, base main, stacked on #843: do not merge before it).
- Branch: `surface/oracle-fortune-teller-room`, head 46cdc1d3 (pushed; checked with ls-remote). Faculty
  head 9b40b339 and main 9ccc242e merged in at 842ac7c2.
- Worktree: `F:/Leadfuel/repos/novahub/.claude/worktrees/oracle-room` (clean).
- Re-read the branch and the PR body before trusting these lines.

## Done this round
- CI fix: `oracle_routes` declared under sf-wall in `scripts/atlas_placement.hub.json` (bf7e5112).
- DOORS R1-R3: failing tests 2226aabb, fix ab3053ee (token header refused by presence, before the session).
- World landmark (teller's tent, camera flies in, then opens the room), phone tab under the Character,
  terms sentence once per person (settings_store key `oracle_terms_seen`, versioned), 1909-deck stand-in
  named as a placeholder: 46cdc1d3. All owner only via `oracle_routes.entry_url_for`.
- 10 mutants on the new guards, all killed. Gates 14/16 green, 2 skipped. Neighbours: 690 passed, 1 skipped.
- Browser (local harness, loopback only): coins, runes, tent flight, tab, terms dismissal seen at 364 px.
  Customer: no tent, no tab, room 404. Tent at 1280 px only measured.
- PR body rewritten (stacked, done, not done, verified vs trust).

## Left for the next desk
1. Wait for hub `tests` CI (workflow test.yml, job pytest) on 46cdc1d3 and report the result. No merge,
   no undraft, no ci-novahub lock.
2. Ask DOORS (and PRIVACY) to re-review the new head: the door change, `terms-seen`, the ways in.
3. Owner's calls, untouched: deck scans (download), the terms wording (COUNSEL draft, not agreed),
   the teller's name, whether the tent's look suits.
