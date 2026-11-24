# redline-5: one-interface status table (26 questions, 22 Law 9 paths, steps)

SURFACE part 218, 2026-11-23 Pacific. Read-only. Sources: the audit folder `F:\Claude Sessions\handoff\one-interface-redline-audit\`
(OWNER-QUESTIONS.md, LAW9.md, STEPS.md) and the card files in `F:\Claude Sessions\handoff\NODE-novah-estate-part-13\raw\router\questions\`.
Code read at these SHAs, read-only (fresh detached worktrees, fetched 2026-11-23):

| repo | SHA read |
|---|---|
| hub | `f95e47a7` (main, 2026-11-23 23:00 PT) |
| echo | `893734f` (main) |
| lucid | `d269f32b` (main) |
| orbit | `6d53753c` (origin/main, for Law 9 row 22 only) |

Vocabulary. Status words: ANSWERED (a card carries the owner's answer), OVERTAKEN (a later card or merged change made the
question moot), DEFAULT STANDS (no card; the build proceeds on the audit's default). Law 9 verdicts: UNGATED, GATED, REFUSED,
NOT BUILT, plus BUILT-OFF (code exists, switch off by default) and CARRIED (not re-read this pass; the audit's 2026-10-12
verdict is repeated and says so). A production value of any switch is UNKNOWN from code (no production reads were made).

## 1. The 26 owner questions

Count check: 15 ANSWERED + 2 OVERTAKEN + 9 DEFAULT STANDS = 26. Card ids were matched by the question id in the card text, then
the card title was read; "taken on trust" means the answer letter is read from the card file, not re-asked.

| id | status | evidence (card, answer) | queue id covering the rest |
|---|---|---|---|
| Q-A1 | ANSWERED B | q369 B (2026-10-13): keep today's layout, add panels. Audit default A withdrawn. | none owed |
| Q-A2 | OVERTAKEN | q368 B removed the owner-email variable; the "zero rows" read stays a counts-only production read needing his typed go | S-4 below (OWNER-STEP, not built) |
| Q-R1-1 | DEFAULT STANDS | no card; world is a view from Radar / key W | redline-2 or W03 to confirm |
| Q-R1-2 | ANSWERED A, then B | q509 A (LAB Character Design app, local). q554 B (GAME LAYER 1/7, "what makes the character's picture") was answered later and differs; which one governs is not stated on either card | needs a card (option X) to reconcile q509 vs q554 |
| Q-R1-3 | ANSWERED A | q510 A (local voice, speaker off by default) | P4-2 |
| Q-R1-4 | ANSWERED A | q511 A (earcons, local, off by default) | P4-2 |
| Q-R1-5 | DEFAULT STANDS | no card; skin A | none |
| Q-R1-6 | ANSWERED A | q383 A (D7 may land; model by `COMMAND_ASK_MODEL`, spend-gated, OFF until set). The local-model path (#897) is separate. | P4-3 done in code; setting a model in production remains his step |
| Q-R2-1 | DEFAULT STANDS | no card; q358 A (earlier) already fixes trust at Standing | none |
| Q-R2-2 | ANSWERED A | q556 A (GAME LAYER 3/7, autonomy ceiling: earned only, no plan caps). Matched on card title. | none |
| Q-R2-3 | ANSWERED A | q455 A (undo hold; #895 built a 10-minute hold, switch off) | P4-1 |
| Q-R2-4 | ANSWERED A | q897 A (CC-104, untouched approvals before first grant) | P4-1 |
| Q-R2-5 | DEFAULT STANDS | no card; "seen" = acknowledged in own session (quest code #822 built it so; not re-verified) | none |
| Q-R2-6 | ANSWERED B / A | q499 B (ATLAS 10/24) and q555 A (GAME LAYER 2/7). Merged card with Q-R3-2. The two answers use different letter sets; q555 A is the later and is what hub #1008-era code (db1b3cab CC-86, "earn-only at 0") applies | none; hub db1b3cab applies q555 A |
| Q-R2-7 | OVERTAKEN | q380 A: hub #816 removed `CONNECTOR_APPROVE_ENABLED`; `app.py` ~13679 says nothing reads it | none |
| Q-R2-8 | DEFAULT STANDS | no card | none |
| Q-R2-9 | DEFAULT STANDS | no card | none |
| Q-R3-1 | ANSWERED A | q512 A (market deal decided only in the Action Feed) | P4-4 (not built) |
| Q-R3-2 | ANSWERED B / A | same cards as Q-R2-6 (q499 B, q555 A) | as Q-R2-6 |
| Q-R3-3 | ANSWERED A | q898 A (CC-104, Runway cell) | P3-5 |
| Q-R3-4 | DEFAULT STANDS | no card; one station per `arms.keys()` | none |
| Q-R3-5 | DEFAULT STANDS | no card | none |
| Q-R3-6 | DEFAULT STANDS | no card | none |
| Q-V1-2 | ANSWERED A | q372 C (2026-10-12) then q374 A (note card, 2026-10-12 later): own secret, action-bound, single-use. No merged PR found in hub main history for it | P0-6, see Section 3 |
| Q-V1-3 | ANSWERED A | q370 A: both approval switches on. Code default is still False (`system_settings.py` 2046-2068) and `.railway/railway.ts` says `preserve()`, so whether it is on in production is UNKNOWN | owner's switch; W03 should read it counts-only |
| Q-V1-4 | ANSWERED A | q371 A, hub #815 merged: approve refused for every mesh token (`app.py` ~13675) | none |

## 2. The 22 Law 9 paths

Today's verdict at the SHAs above. "Changed" says what moved since the audit's 2026-10-12 read.

| # | path | verdict now | evidence read (file, SHA) | changed since audit |
|---|---|---|---|---|
| 1 | Echo `POST /tts` (edge-tts to Microsoft) | GATED (owner only, fails closed) | echo `app/routers/twin.py:940` `is_nc_owner`; `app/config.py:62` `nc_owner_emails`, empty = nobody. Still transmits for the one allowed owner. | yes: was UNGATED (pick 435, CC-106a) |
| 2 | Browser Web Speech API | Echo UNGATED; hub GATED | echo `app/static/app.html:1888` and `voice.html:131` still use `SpeechRecognition`/`speechSynthesis`; hub `static/command/voice.js:66` keeps only voices with `localService === true` and has no recognition | hub gained on-device read-aloud (#897) |
| 3 | Server STT (faster-whisper on Echo) | GATED by login (CARRIED) | echo `app/stt.py`, `main.py:212` present; route head not re-read | not re-read |
| 4 | Ask on the screen (D7) | BUILT-OFF | hub `command_ask.py:67` `COMMAND_ASK_MODEL`, unset means nothing is asked; `command_ask_local.py:47` local model only when the gateway is loopback; merged #820 and #897 | yes: landed on main, OFF |
| 5 | Phone `POST /api/ask` | GATED (spend), still mislabelled | hub `app.py:15660`; docstring at `app.py:15666` still reads "it never sends, posts, or changes anything" while it makes a metered model call. Local-only rows are now dropped (#824, #833) | docstring not fixed |
| 6 | Model calls behind the screen | GATED (spend) (CARRIED) | hub `llm_client.py:864` `call_claude`, `:1270` `call_claude_with_cost` exist; gate body not re-read | not re-read |
| 7 | Studio generate | REFUSED | hub `egress.py` has no `studio` match (`git grep -c` empty); `studio.py:72` `STUDIO_GENERATE` | unchanged |
| 8 | Embeddings | GATED | hub `egress.py:369` `"embedding": Door(GATED, "_carry_embedding", "embed_gateway", ...)` | unchanged |
| 9 | Radar connect (OAuth) | GATED by the person (CARRIED) | not re-read; `command_radar.py` now exists on main | not re-read |
| 10 | World feeds and alerts | GATED by switch, still not through `egress.send` | hub `world_http.py:17` per-feed switch, no `egress` call in `world_http.py`/`world_feeds.py` (comments only); `world_alerts.py:53` `WORLD_ALERTS_ENABLED`, `:123` `"transactional": True` still set | unchanged |
| 11 | `egress.send` and sends after approval | GATED (CARRIED), approval half now closed by row 12 | executor not re-read | partly |
| 12 | Who can approve | GATED | hub `app.py:13675-13690`: approve refused for every mesh token (#815), switch deleted (#816). Open: the emailed link `/approve/email/<id>` is built with `exp` and `sig` (`app.py:14543`); whether its key is still `SERVICE_TOKEN_HUB`, action-bound and single-use was NOT read. `_owner_confirmed` guards the spend paths (`app.py:14084`) | yes: was UNGATED for most tokens |
| 13 | Outward with no approval (runner, campaign) | UNGATED by code default; production UNKNOWN | hub `system_settings.py:2046-2068` both default False; `app.py:12378` single reader; `.railway/railway.ts:63,171` `preserve()` | no code change; q370 A says turn on |
| 14 | Mail reports to the owner | PARTLY GATED (CARRIED) | `app.py:12083` `_is_owner_self_send` still present | not re-read |
| 15 | QuickBooks reads | GATED, read only (CARRIED) | not re-read | not re-read |
| 16 | Market deals and disclosures | NOT BUILT | `git grep -l -i "market_deal|MarketDeal|disclosure_record" -- '*.py'` on hub: no files | unchanged |
| 17 | Twin name fetched from Echo | INTRA-ESTATE, ungated | hub `twin_name.py:29` `ECHO_URL` default, `:121` email in the path. The "reads nothing" docstring in `app.py` was not checked | unchanged |
| 18 | Likeness, avatar, voice clone | NOT BUILT | hub `git grep -l -i "character_maker|likeness_maker|avatar_store"` empty | unchanged |
| 19 | Credits debit sync | DORMANT | hub `ledger_sync.py:57` off unless `CREDIT_LEDGER_SYNC` truthy | unchanged |
| 20 | Standing-grant execution | BUILT-OFF | hub `standing_grant.py:66` `STANDING_GRANT_ENABLED` unset = no grant can be made; `standing_grant_runner.py` built dormant (#895, #925) | yes: was NOT BUILT |
| 21 | Referral credit and quest writes | NOT BUILT (referral) | no `referral` match in `quest.py`, `command_quests.py` | unchanged |
| 22 | Orbit auto-send at score 0.92 | BUILT, default OFF, outside `action_tier` | orbit `origin/main` `6d53753c` `apps/novahawk/ri/mail_drafter.py:210-227`: min score 0.92, daily cap 20, needs `RI_AUTOPILOT_AUTOSEND` truthy, default OFF; production value UNKNOWN | yes: was UNVERIFIED |

CARRIED rows (3, 6, 9, 11, 14, 15) were not re-read; do not quote them as current. Row 12's emailed-link secret is the one
unverified claim that matters most.

## 3. The steps (STEPS.md lists 31 ids: P0-1..P0-7, P1-1..P1-6, P2-1..P2-4, P3-1..P3-5, P4-1..P4-5, S-1..S-4)

The brief says 30; STEPS.md has 31 rows. The "8-step list in the part 21 handoff" was not read; Part 14 re-cut the steps after Q-A1 B.
PR numbers come from titles in hub `git log` on main; "present on main" means the module exists and was not read in depth.

| step | status | evidence | covering queue id / next |
|---|---|---|---|
| P0-1 decision record | merged | hub #814 (`models.py:2021` `ApprovalDecision`, migration 0012) | none |
| P0-2 session + CSRF decision routes | merged | #837 (approve, approve with edits, reject, compare-and-set, expiry) | none |
| P0-3 expiry sweeper | exists, plus #837 expiry | `app.py:20203` `_expire_overdue_pending_actions`; cron firing in production not checked | W03 read counts-only |
| P0-4 character read | merged | #823 (`command_character.py` present) | none |
| P0-5 land D6 | merged | #819 | none |
| P0-6 approvals link hardening | not started or unfound | q374 A answered; no PR found by title search | needs a desk (DOORS); W03 |
| P0-7 person-principal rule | merged | #815 (approve refused for every token); `MESH_ENFORCE_SCOPES` still `preserve()` and default off in `mesh_auth.py` | owner switch |
| P1-1 home stage | partly | #823, #837, CC-38 `81c23efe`; layout is the q369 B panels, not a rebuild | none |
| P1-2 quest progression | merged | #822, then #1150 connector read | none |
| P1-3 skill ledger and trust | merged (slice 1) | #836; regression `c00c83d4`/#947 | none |
| P1-4 rings, payoff, revoke | merged | #892, #894, #947 | none |
| P1-5 character sheet | merged | #892 | none |
| P1-6 likeness | not started | no avatar or maker code on hub main; q509 A vs q554 B unreconciled | card (option X) |
| P2-1 board read | merged | #936 | none |
| P2-2 board block attach | not found | no `board/block` route found by title; Lucid `app/main.py:1419` `POST /api/day/block` exists | D02 or redline-2 |
| P2-3 crews | merged | `962874dc` CC-91 (local, platform only); `command_crew.py` | none |
| P2-4 world as a view | unverified | #896 puts world intelligence on the screen; the Radar/W view switch was not read | redline-2 |
| P3-1 resources | merged | #1008 (cc92, resources strip) | none |
| P3-2 radar | present on main | `command_radar.py` exists; PR not identified | none |
| P3-3 log | merged | #999 (CC-94); retention still an open VAULT question | VAULT card |
| P3-4 credits display | merged | #894, `db1b3cab` CC-86 | none |
| P3-5 runway and regression words | partly | q898 A answered; regression #947 | none |
| P4-1 standing grant | built, OFF | #895, #925; needs `STANDING_GRANT_ENABLED` | owner switch |
| P4-2 voice and sound | partly | #897 on-device read-aloud via browser local voices; local synthesis host (Piper) and earcons not built | NODE desk |
| P4-3 Ask overlay | merged, OFF | #820, #897, #1131 | owner sets a model |
| P4-4 market spoke | not built | row 16 | card (below) |
| P4-5 contracts overlay | not started | depends on P4-4 | card (below) |
| S-1 Echo edge-tts switch and door | partly | different design shipped: owner-only gate (row 1), not a switch plus an egress door | none, or a card if a door is still wanted |
| S-2 connector approve flag | merged | #816 | none |
| S-3 Lucid note | not started | docs only | low |
| S-4 owner-only `COMMAND_OWNER_EMAILS` | overtaken | q368 B | OWNER-STEP: counts-only production read needs his typed go |

## 4. P4 rows as cards (drafted here, NOT posted: this desk posts no cards)

Every card carries option X "None of these: something else".

1. P4-4 Market spoke: vendor program, prices, weekly cap default, notice text. A) start with no vendor, a ledger of offers
   only; B) name a program and cap on this card; X) something else. Default A. Needs: q512 A already says deals are decided
   in the Action Feed.
2. P4-2 Voice: which local voice engine and who records the consented session. A) Piper stock voice now, own voice later;
   B) record first; X) something else. Default A.
3. P1-6 Likeness: q509 A (LAB app) and q554 B disagree; which one is current. A) q509 A; B) q554 B; X) something else.
4. Q-V1-2 follow-up: confirm the emailed-link secret is separate and links are single use (P0-6), or order the desk.

Where the first three exist as answered cards already (q512, q510, q509), the new card is only the part the old card left out.
