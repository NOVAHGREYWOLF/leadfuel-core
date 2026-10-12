# Router handoff #038 -> #040 · owed questions, note 002 (supersedes 001) (2026-10-12 ~22:4xZ UTC, at ~405k)

ROUTER #38 = local_fed56153-e4fc-4391-945e-2c3c5cf178cd. Ids only. State doc: board router/owed38 (A4uS9xn1emqupohdE4DUfV, always use out_dir). Router desk LzmP6QcxmYh9TdvMMjS883.

## What changed since note 001 (READ THIS FIRST)
ROUTER #39 (local_11693482-5f7c-441f-93d5-13de56ece00a, live) already routed the cards the owner clicked on the desk page: q362, q364, q365, q366 (21:12Z), q370, q371, q372 (21:08-21:09Z), q373 (merged, hub#814). So do NOT re-route those. Re-read the desk cards directly; trust the cards, not this note.

## Done by #38 (verified by me)
q294 B; q315 A (Google key rotated, old gone, gcloud ids); q316 A (queries run; desk local_786396c4 asked for a read-only code check, reply owed); q317 A (read ran 10-07, hub#705 merged); q318 A (settings fixed; read half tested on default-mode desk local_e22bd45b, Haiku, idle). q362 note "b but we want a cross over later" written and sent to local_b62be96c.

## OPEN, in the order to walk (6)
q363 (mxbai re-embed now? unanswered), q367 (Azure claims, his own step), q368 (COMMAND_OWNER_EMAILS), q369 (rebuild /command or add levels; he prefers B but wants to read docs first; never relay an unclicked B), q374 (plain note on the approval-link secret; asked by owner on q372), q375 (how long to keep earned-access draft text). Send one-interface answers (q367-q369, q374, q375) to #39. q363 goes to local_b62be96c.

## UPDATE ~23:0xZ UTC (supersedes the open list above where it differs)
- q363 = C recorded and sent (desk replied DONE; q366 count already ran; no Voyage-vs-mxbai test exists, spec section 9 lists it owed).
- q367 = A recorded: OWNER does it. The sign-in app is `Novah_Email_app`, client id 396093c2-a360-4277-b3ea-f2f6a961b711 (= hub MS_CLIENT_ID, a public id I read from Railway filtered to that one line; shown redirect URIs include /auth/microsoft/callback plus mail, calendar and Teams connect callbacks). NOT `leadfuel_approvals` (no redirect URI). Owner adds optional ID-token claims email + xms_edov, then says "q367 done"; tell ROUTER #39.
- CORRECTION ~23:1xZ (owner's screenshot of Certificates & secrets): the app has TWO secrets: "Description v0-local" expired 8/20/2026 (value starts 9k7) and "NovaHawk - Production" valid to 5/21/2028 (starts W4g). So the list's "Expired" was only the old one, and the lead below is WEAK (it lapsed Aug 20, not near Oct 1). Open question: which secret does the hub's MS_CLIENT_SECRET hold? If the expired one, sign-in and the mail/Teams connects are broken since Aug 20 (his step to rotate). The owner can compare the first 3 characters on his own Railway screen. Do not read the secret yourself.
- (original, now weak) LEAD, not verified: the Azure app list showed that app's secret as Expired. That app also serves the mail, calendar and Teams connects, so an expired secret could explain "mailbox / Teams stopped reporting since Oct 1" in the command book and the q316 mail question. Owner was asked to read the secret's expiry DATE on Certificates & secrets. If expired, rotating it is HIS step; tell #39 (VAULT) and desk local_786396c4.
- q368 was asked (A recommended) and is unanswered. Still open: q367 (waiting his done), q368, q369, q374, q375.

## Owner-only follow-ups, not cards
- q366: he types "go" in INTELLIGENCE · tiered memory part · 2's own chat for the production count.
- q370/q371: click chip "VAULT · one-interface part · 3" and type "go" in its chat.

## Owed
- Findings to the live conductor local_83483fa2-1ed0-4076-87bf-6e6be1930857 (027 is archived): owed38 keys finding_for_conductor, finding_for_conductor_2, plus Atlas st-vault row from the 4.2% raw_ref measure.
- Desk local_8387ff2c (SESSION_MAP documentation) asked who writes five owed map rows; told to hold. Put to the owner as a card.
- Unipile $55 payment failure: told to the owner only.
- Archive test desk local_e22bd45b and the idle desks local_7ddb1c08, local_6b8ff456 through the gate when appropriate.

## Gotchas
ArtifactData without out_dir floods context. Pin card writes to if_version; #39 also writes cards. Never relay a default. Bash tool halves backslashes: use chr(92) in python.

## UPDATE ~23:2xZ UTC: FINDING on q367 (owner's own screen read, 3 characters only)
Owner compared the first 3 characters of the hub's MS_CLIENT_SECRET (NovaHub, Railway) with Azure's Novah_Email_app secrets: the hub's starts 369; Azure lists 9k7 (v0-local, expired 8/20/2026) and W4g (NovaHawk - Production, valid to 5/21/2028). It matches NEITHER. Reading: the hub holds a secret that is not on that app now, so Microsoft sign-in and the mail/Teams connects cannot exchange codes (UNVERIFIED: not tested in production; the variable or service could be a different one). Fix is the owner's: new client secret on the app, VALUE copied once, set as MS_CLIENT_SECRET on NovaHub, redeploy, test. Tell ROUTER #39 (VAULT) and desk local_786396c4. q367 stays open until he adds the claims AND says done.
