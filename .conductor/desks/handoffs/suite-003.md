# SUITE · land the backlog part 1 (was SUITE 2/2) — handoff 003

Ids, titles and status only. Supersedes suite-002.md.

## Done (verified)
- hub #725 squashed e42b661; places-gate stanza is on main via hub #738 (merged 2026-10-08).
- hub #657 squashed c3677b4: CI green on head 17d18a86 (lint, security, tests incl. count guard), main unmoved c6bdec39. Placed scripts/check_eager_scratch under i-ci in scripts/atlas_placement.hub.json (first CI run failed 2 atlas-inventory tests without it); made two setdefault(mkdtemp()) calls lazy.
- ci-novahub released; DOORS (queue worker) told; I hold no lock.
- Report sent to ROUTER #134 (card q9635 B), queued.

## Owed, NOT started (candidate tasks for the conductor; only queued work gets started)
1. Six run-B failures, order/time dependent; need the heavy slot (scripts/heavy_lock.py).
2. scripts/check_export_harvest.py is missing; gates.sh SKIPs that gate.
3. Main's gates.sh still has one --deselect line, unexamined.

## Mistakes on record
- 2026-10-02: stopped ~12 other desks' pytest processes with a too-broad Stop-Process filter.
- 2026-10-13: mistyped worktree path ran a merge in my own leadfuel-core branch (local commit b5ab11d, unpushed, harmless).

## Next
Nothing queued. Re-read live state before acting; do not trust these lines. Archive only through the gate (router's call).

Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>
