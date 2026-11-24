# INTELLIGENCE part 204: the owner-pre-decided (B-class) batch

Written 2026-11-23. Source of the defaults: a conductor-relayed owner classification (see the private handoff). Nothing here sends data anywhere, spends, or reads production. Each section says what was verified and what is left for the owner.

## Status table

| id | default taken | state | where |
|---|---|---|---|
| desks-1-13 | go on cert-expiry fix | built, draft PR | hub PR 1207 (counts from `cert_not_after`) |
| mail2-38 | want, local-first, paid gated | already done | leadfuel-core PR 97 merged |
| chats-11 | design as drafted, local, no plaintext | already built as draft | leadfuel-core PR 90 (credential handles) |
| mail2-37 | desk proceeds | written | `COMPETITOR_NOTE_OTTO_XAISTACK.md` (XAIStack half needs the link) |
| chats-3 | each card's stated default | partly checked, below | this file |
| chats-4 | count-only inventory of own mail | listings exist; opening bodies is owner-side | below |
| chats-6 | one-page MVP, no build | written | below |
| desks-3-7 | search, else record never written | found, already in the Document Library | below |
| fold-s-jobhunter | keep archived, do not delete | recorded | below |
| fold-s-market | approve scope, counsel before build | scope written | below |
| mail2-39 | park | recorded as parked with its two gaps | below |
| mail2-46 | park | recorded as parked | below |
| own-1, own-5, own-7 | defaults in the csv | designs written, no code this pass | below |
| coverage-39 | adaptors and panes as drafted | not done, see below | below |

## chats-3: archive retrospective loose ends

Checked in this checkout's `main` (read-only):
- Patch `leadfuel-core-drop-python3-hook`: its target state is in force. `.claude/settings.json` holds only the two `SESSION_*_TOKENS` env entries and no python3 hook. Applied.
- Patch `way-continue-unless-gated`: no text matching it anywhere in this repo's `plugins` tree or docs. The way plugin ships from the `way/plugin` branch, which was not checked here. Unconfirmed, not applied on `main`.
- Cards 3, 5, 6, 7 and the 2026-12-01 monthly loop: need the card pages and the scheduler; not read here. The standing default for each card is its option A. The loop is a scheduled task; scheduling it is the routine desk's step.
- "Always mock up first" rule: not found by text search in `plugins`; it is kept in private notes. Whether the way skill carries it was not confirmed.

OWNER-STEP: none. Router: have the desk that owns the way plugin confirm the continue-unless-gated patch and the mock-up rule on `way/plugin`.

## chats-4: mail-to-self and the OneDrive "chat sessions" folder

A first pass already exists: first-pass inventory files in a private handoff folder (counts there) and the queue rows they produced. What is left is the OneDrive "chat sessions" folder and opening bodies. Reading his mail or that folder through a connector sends contents through a model, which the standing yes does not cover, so it is not done here. A local count of the OneDrive folder needs only filenames and is allowed; the folder was not found at the usual OneDrive path under this account on this pass.

OWNER-STEP: say where the OneDrive "chat sessions" folder is (or that it is not synced to this PC), in the desk chat | blocks: the count-only inventory.

## chats-6: goal-to-business "fully auto" mode, one-page MVP (no build)

Ask (three private notes): give a money goal, the system plans and builds the site, domain and setup with no questions.

MVP in one sentence: goal in, plan out, every outward step an approval card, build runs locally, launch only after typed approval.

1. Goal in: one sentence plus a number and a date ("$2,000 a month from X by March"). Stored in the brain.
2. Plan: the local model drafts the plan from the brain and the existing test findings (AI-STORE-GOAL-TEST, AI-STORE-DEFAULT-ICP): offer, buyer (scope), channel (reach), site, cost list. Local only. Output: a plan page and a mockup of the site.
3. Approvals as cards, one per outward call, each with exact cost and recipient. Nothing runs before its card is approved.
4. Build: local files only (site draft, copy, a checklist).
5. Launch: a human-approved step per item.

Every outward call and its gate:

| call | gate |
|---|---|
| domain purchase | spend gate, exact price, owner approval |
| hosting or DNS change | change card, owner approval (Law 9) |
| posting or sending to anyone | the arm's own approval path (reach / DOORS), person-only approve |
| any paid model call | spend gate; the plan itself runs on the local model |
| ad spend | spend gate with a cap in the card |
| payment or checkout setup | owner does it; credentials are handles, never values |

"Fully auto" means no questions while planning and building, never no approvals for outward steps. Park condition: if the local model cannot produce a usable plan, the MVP is parked, not routed to a cloud model.

OWNER-STEP: pick build or park on the Router desk card for this page | blocks: any build.

## desks-3-7: document "Security and Data Architecture" (doc #25)

FOUND, on this PC. A later filename search using the underscored name `25_SECURITY_AND_DATA_ARCHITECTURE.md` hit (my first search used spaces and missed it). Source: `F:\Leadfuel\repos\NovahPrime\docs\25_SECURITY_AND_DATA_ARCHITECTURE.md`. It is already in the Document Library, canon copy at `F:\Claude Sessions\Document Library\local-documents\other\F-docs\novahos\03-CANON\25_SECURITY_AND_DATA_ARCHITECTURE.md`, plus a 2026-05-21 working copy under `by-project\novahos` and `by-project\novahprime`. Done; the manifest should list the canon path. No owner step.

OWNER-STEP: say whether doc #25 "Security and Data Architecture" ever existed outside this PC (mail, claude.ai) | blocks: closing the library manifest hole.

## fold-s-jobhunter: retired JobHunter repo

Default: keep archived, do not delete. Checked: no directory named like `jobhunter` under `F:\Leadfuel\repos` or `F:\Leadfuel`. SPOKES.md row: "retired, sleeping"; the owner left it "until odyssey fully works". Record: kept, not deleted, no action. The only live work is making sure the NovahOS shell does not point at it; nothing found pointing at it in this repo.

## fold-s-market: consent and disclosure schema scope (MARKET spoke)

Approved scope per default; counsel before any build.

- Purpose: record, for any person whose data the owner's system holds or contacts, what was disclosed to them and what they consented to, so outbound market actions can check it.
- Stays on the node: the consent ledger itself (one row per person per purpose: purpose, wording shown, version, date, channel, how withdrawn), the disclosure texts, and the check result. Nothing about a person leaves the machine to build or test this.
- Needs his approval to leave: any message carrying a disclosure, any export of the ledger, any sharing with a vendor.
- Schema (draft): `person_ref`, `purpose` (outreach, recording, newsletter, data-sale), `lawful_basis`, `disclosure_version`, `granted_at`, `withdrawn_at`, `source`, `evidence_ref`. A send door refuses when no live row exists for that person and purpose; absence reads as no, never as unknown-so-allow.
- Out of scope until counsel: jurisdiction rules, retention periods, recorded-conversation consent (see mail2-39).
- Done when: this page is approved and counsel has the schema. No code written.

OWNER-STEP: send this schema to counsel | blocks: any build of the market spoke consent layer.

## mail2-39: parked concept (see private handoff)

Default: park. The concept is described in the private handoff. Parked, not queued. The two blockers are product gaps in their own right and each gets a row or a reason:
- lucid cannot propose or approve a calendar block: wanted by the "act, not report" goal (own-1); queue as a lucid write-surface item under the approvals plan when the first spoke loop is chosen. Not needed for the parked concept.
- consent and retention for a recorder around other people: covered by the fold-s-market schema above plus counsel.

## mail2-46: parked concept (see private handoff)

Default: park. The Personal Core in the spec is what the digital brain (K01) and tiered memory (W16) already build; parking avoids a second store. If revived later, new work is only: ingestion of other people's work, advisor routing, council synthesis. The spec package is not filed here; filing it into the library is a step for whoever holds it.

## own-1, own-5, own-7: designs (no code yet)

- own-1, the loop on one spoke. First spoke: the inbound engine (default). Loop: notice a gap in his own data, propose one action with a reason and an expected result, one approval in the one approval queue, the arm acts, measure against the expectation, write the result to the brain so the next proposal differs. Depends on fold-s-orderplane (the one approval queue); do not build until that lands.
- own-5, morning brief and evening close. Two pages and one spoken minute each, local model and local voice only. Morning: overnight events, the three moves that matter, what waits on him. Evening: done, what the game paid, what was learned, what is tried tomorrow. No paid model calls (a paid brief was refused by the owner). A deterministic template over local data is the first build; the local model only phrases it.
- own-7, explain, undo, stop. Rule: every proposal shows its sources; an action that can be reversed carries an undo; a send, a post or a payment cannot be undone and is labelled so before approval; one stop control halts everything the local AI is doing. Depends on fold-a-G40. One working example (a proposal with sources, an undo, and the stop control) is the done condition.

## coverage-39: PRODUCT batch

Not done. The rollup bundles eight tasks (D4 adaptors, H1 panes, PRODUCT-020, -021, -022 and others) whose raw text sits in `raw/conductor/desks/product.json`; the "as drafted" defaults need that text and each task re-verified with gh, which is a pass of its own and one PR per task. Passed to the next part.

## Verified versus taken on trust

Verified myself: hub PR 1207 tests and gates, PR 97 merged, PR 90 open, the python3 hook patch state, the local file search. Taken on trust: the planner rows, the owner defaults in the csv, and every Otto fact (from its public page, not tested).
