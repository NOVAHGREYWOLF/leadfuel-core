# SURFACE · apple app (TestFlight) 2/2: handoff 002 (updated)

Session local_772034d0, 2026-10-02. Source: ROUTER #9/#10 briefs; owner queued GOAL-iphone-command-center (rank 59) and TUFTE-G9-iphone (rank 74). Owner answer Q139 = HOME (relayed by ROUTER #10): command center is the home screen, other tabs stay, owner does Apple enrolment, bundle id cloud.leadfuel.app.

## Done (leadfuel-ios has a private remote origin; my earlier "no remote" was wrong)
- main d46e223: Money screen as sentences.
- PR 1 (draft, tufte-g9-campaigns 9258d68): Campaigns queue as sentences.
- PR 2 (draft, command-center-home f5a6b14, stacked on PR 1): goals on the home tab worst first, tab renamed Command, hub.goalStatus + demo data.
- Ran: tsc clean; jest sentences+hub 15/15. Not run: full jest, Metro/web preview, device, live goal_status.

## Waiting
- Owner: Apple Developer enrolment, Expo account, then eas login/init/build/submit in his own terminal (docs/SHIP.md). STATUS NEEDS-NOVAH sent to ROUTER #10 (queued, no delivery notice seen).

## Next
- Check CI on both PRs; run Metro web preview with EXPO_PUBLIC_DEMO=1 and screenshot; verify the real goal_status shape once signed in.
- Owed to others: native approve needs a hub-side device credential (DOORS, not briefed).
