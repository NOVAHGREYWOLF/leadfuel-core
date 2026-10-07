# Handoff: CONDUCTOR · system build, 019 (2026-10-07 ~18:20Z, rotating at ~300k)

Ids only (public repo). This session: local_1a4942ec (read your own id with get_session "self"). Branch claude/conductor-019. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current). The tick cron 4abcb783 dies with this session: re-create it at minutes 13,43 (prompt as in 013's note). Cards: start at n >= 346 (q344, q345 seen); picks: decided_at > 2026-10-07T09:31Z.

## Done (verified by me)
- Archived 018 through the gate. Kept conductor 005 and ROUTER #11-#13.
- Picks: NODE~GROUP-BY-PROJECT rank 234 (owner yes in my chat); S1, S5, S6 set to doing in the SURFACE and INTELLIGENCE lane docs.
- Filed unqueued from ROUTER #27's relay (FIELD handoffs 001/002 and two code lines read by me): FIELD FIELDY-EXTRACTION-EMPTY, WATCH FIELDY-WATCHDOG-FALSE-DOWN, PRIVACY FIELDY-HOLD-DATA-POLICY.
- SUITE TEST-ISOLATION: basis corrected, status open. From hub CI run 37608069124 (failed log read by me): test_prime_digests_everything.py:212, delivered == 1 but 5 accounts (shared test DB), NOT date-bound. #28 and #29 hold the correction.

## State (re-read before acting)
- Live router ROUTER #29 local_46ddffce (claimed 17:38Z). #28 local_efc92f9b and #27 local_dc4fea43 stay open for their agents.
- Per #29 (gh-verified by it): hub #786 landed 3d64acc5; #793 (S1) undrafted, green, MERGE-TRAIN 7/7 local_4d18486c landing it; #794 (S2), #795 (S3) wait on S1.
- GROUP-BY-PROJECT: leadfuel-core#35 merged (b92f65c57, per #28); way 0.1.8. q344 (install and wording) unanswered. q345 answered B (no local preview).

## Next
Run the tick, read new owner answers, file only answers that create new work, brief #29 only when something is new.

## Owed
- Owner: queue SUITE TEST-ISOLATION? Asked twice; "KEEP GOING" is not a yes. On yes: pick SUITE~TEST-ISOLATION (re-get desks/suite first), brief #29.
- Owner: queue COUNSEL PHOTO-STORE-WORDING? Same.
- Owner: q344. Mark GROUP-BY-PROJECT done only after he settles the wording (B means reword).
- Sends this owner turn: 2, both delivered (to #27, #28); read receipts unconfirmed.

## Gotchas
- Git Bash had no git on PATH: use PowerShell. gh with a Start-Job timeout.
- ArtifactData update merges nested keys; pin if_version; compare task counts afterward.
- Agents' own timestamps are unreliable and the box slept ~6.5 h (10:30-17:00Z, GitHub 500s): use date -u.
