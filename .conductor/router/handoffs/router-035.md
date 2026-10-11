# Router handoff #035 -> #036 (2026-10-11 ~23:0xZ UTC, soft cap)

ROUTER #35 is local_19f89eda-38f2-4c2c-9d32-3a2d41c77356. Ids only. Board router/current (A4uS9xn1emqupohdE4DUfV) keys claim_35, agents_35*, agent_reports_35*, log_35* supersede this note. Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF. Conductor 024 local_5b6f1dd2-2c2b-4745-8512-abba6e4aa375.

## Done (verified by me with gh / ls-remote)
- #34 archived. Hub merged: #803 D1 (9ae43a38), #805 merge-train readiness (2cec3769).
- Owner answered and routed: q353 A, q355 A, q356 A, q357 A, q358 A, q359 C (talked through with conductor), q360 A.

## Running background agents (MINE: they die if #35 is archived; #35 stays open and relays each to the board)
- SUITE ci speed part 4 abe619324b9dd3512: land hub#804 at 8 workers on CI (my decision; agent_reports_35g)
- VAULT one-interface part 2 a4dfa3d87738e3b01: hub#808 Microsoft sign-in fix, self-lands on CI
- NODE ci speed part 7 a7852e75e2194ad76: CI-SHARDING finish; close #807 if no gain
- INTELLIGENCE one-interface part 3 a6fae4d355a2e9a20: D6 to green draft
- INTELLIGENCE one-interface part 4 a040d62f9eb8587fa: D7 to green draft

## Next
1. Claim. Then start SURFACE~ONE-INTERFACE-REDLINE-AUDIT (Conductor desk desks/surface): owner asked for a large read-only background fan-out (his words in conductor 024's chat ~22:39Z). Size it; output to F:/Claude Sessions/handoff (private).
2. On #804 landed: open SUITE ci speed part 6 to land hub#806 (TEST-ISOLATION; test-setup change; 0xc000070a process-start failures are a NODE environment finding, not a test verdict).
3. D6/D7 green drafts: reviews (D6 DOORS, D7 DOORS+VAULT) and land only if the audit says they fit.

## Owed
Cards open: q294, q315-q318. Archive #33 local_62d2f0c7 (app refuses: live work). Earned-access desk local_04d666b8 done; archive needs the owner's yes (outside plan). COMMAND_OWNER_EMAILS stays unset until #808 lands. SESSION_MAP row for merge_train.py (filed ROUTER~SESSION-MAP-ROWS-1011).

## Gotchas
Router desk list without where floods context. Agents near 300k hand off: open successors with n advanced. ci-novahub wait dir holds ~30 Oct 2-7 tickets (see READ-ME-FOSSIL-QUEUE).
