# SURFACE · apple app (TestFlight): handoff 001

Session [c353e8], 2026-10-02. Instruction source: Novah, directly in this session. His decisions:
Expo/React Native cloud build, he enrols in the Apple Developer Program himself ($99/yr, his spend),
scope "as much as we can", TestFlight only.

## Done
- New repo `F:\Leadfuel\repos\leadfuel-ios`, local commit `aac0d8a`, **no remote yet**. Expo SDK 57.
- Screens: Today, Approvals (read + reject), Ask, Inbox, More (campaigns, money, search, connections, account).
- `tsc --noEmit` clean; jest 5 suites pass. I ran both.
- Docs in that repo: README, `docs/SHIP.md` (Novah's steps), `docs/AUTH.md`.
- Declared the repo to ROUTER #8 (queued; no delivery notice seen).

## State (successor re-reads; none of this is trusted)
Verified live: the MCP resource names an AuthKit **staging** tenant as issuer; a public client was
registered for `leadfuel://oauth`; its authorize endpoint accepted that redirect; MCP is 401 without a token.
Verified from source: the hub refuses `approve` for connector tokens.
NOT verified: Metro/web preview never ran, token exchange, hub accepting the token, real response
shapes (normalisers are defensive), any iPhone.

## Next
Run `EXPO_PUBLIC_DEMO=1 npx expo start --web`, screenshot every screen, fix layout, run `expo lint`.

## Added after this note was pushed: GOAL-iphone-command-center (rank 59)
Relayed by ROUTER #8 (peer message, after the cap; the successor owns it). Its words: the owner queued it via the
conductor, "the iphone app - it needs to have the command center interface only ... under surface ... a goal we push".
Router's brief, unverified by me: this desk holds it, no new desk. Step one is READ-ONLY: what the app shows today,
and how `/goal` is served. Then a plan with the owner-only steps listed BEFORE any build. Nothing goes to Apple
without the owner. The web command center is a separate desk (`INTELLIGENCE · command center per user 1/1`, not in my
earlier session list, so verify it exists): agree the page contract with it, do not duplicate it. Also read
`SURFACE · command center nav button` and `SURFACE · command url check` (both open on leadfuel-core PR 8). Report
STATUS/ASK to ROUTER #8. Note "command center only" may mean dropping or hiding the tabs built so far; ask before
deleting any.

## Owed
- Novah: Apple enrolment; approve creating a GitHub repo for `leadfuel-ios`; confirm bundle id
  `cloud.leadfuel.app` (permanent after first upload); replace the generated placeholder icon; say whether the
  staging AuthKit tenant is the intended production issuer.
- Not routed: native in-app approve needs a hub-side device-bound credential. That is the approval gate
  owner's (DOORS), not this desk's. Not briefed yet.

## Gotchas
Machine is slow (jest 60 to 110 s a suite, npm about 3 min). TypeScript 6 needs `types: ["jest","node"]`.
`leadfuel-ios` sits inside the `F:\Leadfuel` work tree (`repos/` is ignored), so it needed its own `git init`.
`leadfuel-core` is deprecated: build nothing there. Not archived: the app repo has no remote.
