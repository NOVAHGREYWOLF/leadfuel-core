# Handoff: CONDUCTOR · system build, 012 (2026-10-05, rotating at ~300k)

Ids only (public repo). This session: local_6247b62d, branch claude/funny-northcutt-8111f1. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883. The 30-min tick cron is DELETED; re-create it (prompt: re-read cards answered since last tick plus new picks, file only owner answers that create new work as picks, brief the live router; never answer cards, merge, deploy, spend or archive).

## Done (verified by me)
- Archived 011 local_495986b8 through the gate.
- Filed picks (choice=now): SURFACE CC-ROUTE-MOVE (q263), COMMS LINKEDIN-COOKIE-GATE (q269), WATCH PROOF-SEND (q264), WATCH BOOK-TIME-LOCAL (q276, owner via ROUTER #20). These are HELD under close-first.
- Filed picks (choice=now, close-first exception per owner): NODE CI-RUNNER-CRASHLOOP and NODE CI-HUB-HOSTED-TESTS (free minutes only; owner REJECTED paid hosted CI as too expensive, so the $0 cap stays).
- Filed unqueued: NODE FLAKY-WRITEBACK-DB-PATH.
- Wrote the owner's "55 layers" decision (relayed by ROUTER #20) into the SPATIAL-1, ATLAS-VIEWS, SPATIAL-2 and SPATIAL-6a/6b records.
- Root cause of the hub stall, read at 18:17Z: docker novah-runner-novahub restarts=158, novahub-2 restarts=84; tests jobs pending with runner=null since 16:52Z. Sent to ROUTER #20.

## State (trust; re-read)
- ROUTER #20 local_461fe4e9 is live. #18 local_55805a7f is held for its chip children.
- Owner rule (via #19): close-first, no new desks until the open ones close.
- Sessions at 18:17Z: 118 open (126 this morning, 18 archived). Hub: train A merged #709 #749 #750 #751 #758 at 16:51.
- q272's stray loops are gone (tasklist). The q276 card is unclicked, but its answer is in #20's chat.
- Keep #11, #12, #13 and conductor 005 local_083bdfe0.

## Next
Re-create the tick. Check that ROUTER #20 opened CI-RUNNER-CRASHLOOP and that the hub tests jobs run again. Report the done/still-needed counts to the owner.

## Gotchas
- list_sessions with limit 200 overflows; parse the saved tool-results file with python.
- Desk JSON: read as utf-8, write with ensure_ascii=False, pin if_version.
