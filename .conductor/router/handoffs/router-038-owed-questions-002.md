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

## RETRACTION ~23:3xZ UTC (supersedes the "FINDING on q367" and the expired-secret lead above)
Owner corrected himself: the first 3 characters of the hub's MS_CLIENT_SECRET are W4g = "NovaHawk - Production", valid to 5/21/2028. The earlier "369" reading was wrong. The "matches neither Azure secret" finding is WITHDRAWN. The expired v0-local secret (9k7, lapsed 8/20/2026) is not the hub's, so the expired-secret theory for mail/Teams silence since Oct 1 is DEAD (3-char match on the owner's own screen; not otherwise verified). q367 now needs only: owner adds ID-token optional claims email + xms_edov on Novah_Email_app, says "q367 done", then tell ROUTER #39.

## FINAL UPDATE ~23:5xZ UTC (at the 450k cap)
- q367: owner said "I added it" (the email + xms_edov claims on Novah_Email_app); recorded on the card (not verified by me); ROUTER #39 told (delivered, not confirmed read) to test an unlinked work account. The card stays open until that test or his "done". The hub's secret is the production one (W4g, valid to 5/21/2028); the old v0-local one (expired 8/20/2026) is not the hub's.
- Owner asked to rename the Azure app so it is findable. Advice given: rename the app display name only (cosmetic), do NOT rename secrets (needs rotation). Offer pending: ask the live conductor local_83483fa2-1ed0-4076-87bf-6e6be1930857 to file, unqueued, a small desk task for a credentials map line (app name, client id 396093c2-a360-4277-b3ea-f2f6a961b711, hub vars MS_CLIENT_ID and MS_CLIENT_SECRET on NovaHub). Owner has not said yes.
- Still open: q368 (unanswered, recommend A), q369, q374, q375, plus q367's test.

## LAST LINES ~00:0xZ UTC 10-13 (from ROUTER #39's reply)
- #39 (local_11693482) is handing off to ROUTER #41 · one-interface (note router-039.md, branch claude/router-41). Until #41 is live, send one-interface answers to #39; after, to #41.
- q367 test is a PERSON step, no desk opens it (no desk may enter an account password): the owner signs in to the hub once with a real, unlinked Microsoft WORK account and reports if it lands signed in (one-click) or is asked to link first, via #39/#41. Optional: he said nobody he knows uses one. Azure app rename is his display-name change only; no secret is rotated.

## RENAME DONE ~00:1xZ UTC 10-13 (owner's word, not verified by me)
The Azure app Novah_Email_app (client id 396093c2-a360-4277-b3ea-f2f6a961b711) is now named "LeadFuel Hub - Sign-in and Connects" (the first try with the word Microsoft in it was rejected by Entra). Client id, redirect URIs and secrets unchanged. Credentials-map line (app name, client id, hub vars MS_CLIENT_ID and MS_CLIENT_SECRET on NovaHub) still NOT filed; ask the owner, then the live conductor local_83483fa2-1ed0-4076-87bf-6e6be1930857, unqueued.

## ~00:3xZ UTC 10-13
- Credentials-map task: owner said yes; sent to the live conductor local_83483fa2 (delivered, not confirmed read); it files it UNQUEUED. Do not resend. Check the Conductor desk before saying it exists.
- Owner raised a product-naming question (LeadFuel as the umbrella vs a new umbrella; NovahOS = system, NovahPrime = character already in use; LeadFuel = sales/marketing suite). He has not yet asked for a card. Offer one (A keep LeadFuel as umbrella, B new umbrella with LeadFuel as the business suite, C full rebrand later), after the open cards.
- Owner wants to keep walking the questions; next is q368 (unanswered, recommend A).

## CLOCK CORRECTION (date -u read 23:01:17Z 10-12 at this point)
My time stamps after 22:29Z in this note and on the cards (q367 routed "23:4xZ", the "00:xZ 10-13" lines) were GUESSES and run ahead by about an hour or more: read them as ordering only. Use date -u. Conductor local_83483fa2 filed VAULT~CREDENTIALS-MS-SIGNIN-ENTRY (desks/vault v18, UNQUEUED; target F:/Claude Sessions/CREDENTIALS.md; delivered 23:0xZ). Still open: q367 test, q368 (unanswered), q369, q374, q375.

## STATE AT THE END (date -u was 23:01Z earlier; later stamps are approximate)
- DONE since the last note: q368 = B (variable unset; owner model: customer view vs separate admin; conductor filed VAULT~ADMIN-CUSTOMER-SEPARATION unqueued); q369 = C (talk-through; conductor filed SURFACE~ONE-INTERFACE-TALK-THROUGH and briefed #41, nothing built); q374 = A (new dedicated approval-link secret, one item once, apply to local too; replaces q372 C).
- q374 BUILD IS NOT FILED: conductor 028 handed off; its successor 029 is an unused paste prompt. 028 wrote the build + the two additions (node-credential, local-first) + the board brief for #41 into conductor-028.md as owed to 029. Do not resend unless 029 asks.
- Unused paste prompts waiting on the owner: ROUTER #40 (owed questions, this), ROUTER #41 (one-interface), CONDUCTOR 029.
- OPEN: q375 (retention of earned-access draft text: read the card, summarize, ask), q367 (claims added, sign-in test optional). Then ask about the naming card (LeadFuel umbrella) and the SESSION_MAP owed rows.
