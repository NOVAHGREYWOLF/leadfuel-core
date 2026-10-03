# Handoff: ATLAS-DOORS 1/1 (DOORS desk)

Re-read state before acting; the lines below were true at 2026-10-03 ~20:57 UTC.

- Task: ATLAS-DOORS (Conductor desk, desks/doors). Router: ROUTER #16 local_dd131408.
- PR: NOVAHGREYWOLF/novahub#752 (draft), branch `atlas-doors`, head 48b6537, worktree
  `F:/Leadfuel/repos/novahub/.claude/worktrees/atlas-doors`.
- Done in #752: hub email (q219 = A), LinkedIn and X all cross egress.send. Gateway and
  warden measured 19:16 UTC (deployed; enforcing, fail-closed).
- Held: no merge until owner card q227 (sizing the email ceiling; prod value 100, read by NODE) is
  answered. ci-novahub ticket 20261003T191744Z-DOORS-ATLAS-DOORS-pr752 is marked NOT READY.
- Next: full gates on 48b6537 once the full-suite lock is offered (ticket
  20261003T205622Z-DOORS-ATLAS-DOORS--gates-pr752), then mark #752 ready, then merge inside the
  ci-novahub hold after q227.
- Orphan pytest 31656/21864 (cwd atlas-doors) is the owner's to kill (card q229); do not touch it.
- Overlap: DOORS ARM-SENDS-DOORS (local_66060050) rebases #754 and #758 onto #752 after it lands.
- Out of scope, proposed to the router as separate tasks: reach, signal, lucid and odyssey sends.
