# SURFACE · apple app (TestFlight) 2/2: handoff 002 (updated)

Session local_772034d0, 2026-10-02. Source: ROUTER #9/#10/#11 briefs; owner queued GOAL-iphone-command-center (rank 59) and TUFTE-G9-iphone (rank 74). Owner answers relayed by routers: Q139 = HOME (command center is home, tabs stay, bundle id cloud.leadfuel.app, owner does Apple enrolment); q145 = yes (CI workflow).

## Done (all draft PRs on private NOVAHGREYWOLF/leadfuel-ios, stacked 1 -> 2 -> 4; 3 is separate)
- main d46e223: Money as sentences.
- PR 1: Campaigns as sentences. PR 2: goals on home tab (worst first), tab "Command".
- PR 3: .github/workflows/ci.yml, tsc + jest, [self-hosted, novah]. NODE owns .github/workflows/**: handoff is a comment on PR 3 only; a runner for the repo is still owed (router passing to conductor).
- PR 4: web preview fix (TabList asChild unwraps one layer; bar flattened). Demo preview renders; screenshots timed out, checked via page text.
- Ran: tsc clean; jest sentences+hub 15/15. Never ran: full jest, device, live goal_status, the CI workflow.

## Waiting
- Owner: Apple Developer enrolment, Expo account, eas login/init/build/submit in his terminal (docs/SHIP.md).
- NODE: land PR 3 + runner.

## Next
- Once enrolled and signed in on a device: verify real goal_status shape; adjust goalLines.
- Owed to others: native approve needs a hub-side device credential (DOORS, not briefed).
