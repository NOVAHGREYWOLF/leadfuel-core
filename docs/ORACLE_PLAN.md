# The oracle set: numerology, astrology and the fortune teller in the one-interface game

Written 2026-10-12 (Pacific; 2026-10-13 UTC) by DESIGN · one-interface part · 4 (session
local_9d3041cc-2536-487f-8ec4-10650fab3eaf) on the owner's direct request in that session's chat:

> "also in tasks I want to add nerology to the system as well as astrology. I also want a place
> you can go to the fortune teller. The fortune teller uses tarro decks or other methods to predict
> your future. it has all your info. THoughts about this an dimplementation. then add these
> documents to the repository"

This is the plan record. Code lives in `NOVAHGREYWOLF/novahub` (hub) and `novahub-mcp`; this repo
holds only the documents. Nothing in this set is built. The three method documents:

- [ORACLE_NUMEROLOGY.md](ORACLE_NUMEROLOGY.md): the numbers, from a stated name and date of birth.
- [ORACLE_ASTROLOGY.md](ORACLE_ASTROLOGY.md): the natal chart and today's sky, from stated date, time and place.
- [ORACLE_FORTUNE_TELLER.md](ORACLE_FORTUNE_TELLER.md): the place, the character, the methods, and how a reading is grounded in the brain.

## Thoughts

**It fits the game better than it fits a dashboard.** The owner's one-interface is an RPG where you
go into your character and places pull up (2026-10-07), the character is the person themselves
(q361 B), the character sheet is the pane already there, extended with the person (2026-10-12), and
the owner accepted the sheet's eight defaults (q377 A). Numerology and astrology are two more
families on that sheet, computed from facts the person states. The fortune teller is a place in
the world with a character in it, which every RPG has and which this one can do honestly, because
the brain holds evidence about the person. Build it as part of the game, not as a widget.

**It is the cheapest early payoff the game has.** Levels unlock on data readiness and every level
must end in a payoff (The Game of Your Life). Numerology needs two typed facts and astrology three;
both fill a family on the sheet at level 1 with an empty corpus. The fortune teller's daily card
needs nothing at all. That is a day-one hook for a customer who has connected nothing yet.

**It must stay out of the Self.** The brain's own doctrine is explicit: `first_principles.py` uses
"horoscope" as the name for an unfounded claim (lines 366 and 464 on hub main, agent's read), and
W1 says every belief about a person carries evidence. A reading is not evidence about the person.
So: the oracle reads from the Self and never writes to it; a reading is a document, not a claim;
the strategist, needs and goals never take a reading as input; the only path from a reading into
the person's life is a quest they accept by hand. With that line held, the oracle and the Evidenced
Self do not contradict each other. They are two registers: one says what is known, the other plays.

**The six refused kinds apply with full force.** The owner ruled (q376 A) that politics, religion,
health, sexuality, finance and ethnicity are never inferred. A fortune teller is the surface most
likely to drift into them ("I see illness", "money is coming"). The composer refuses them by code,
with tests, for every method and whatever the question; health is never in its context at all.

**Law 9 has three edges here, not one.** A composed reading is a model call (metered, priced,
local first, cloud only as a named decision). A place name turned into coordinates is a lookup
(shipped gazetteer, not a web call). A spoken teller is a transmission (local voice or none). All
three are decisions in this plan, none is a fallback.

**Credibility.** A business customer on the sales skin may not want a fortune teller on an ops
screen. The place is something you walk to, never a card in the Action Feed; the daily line is one
sentence on the life side of the book; and one switch turns the whole oracle off for an account.
Whether it is on by default for every account is the owner's call (card 5 below).

**Numbers and sky are astronomy and arithmetic; readings are writing.** The engines are
deterministic, offline and testable to the decimal. Keep them that way: no model touches a number
or a planet. The model writes only the reading, and only when the owner has named one.

## How it plugs into the hub (survey of hub main `fb1e6714`, 2026-10-13, by a read-only agent for this desk; its findings, not re-read by me except where marked)

| Need | What exists today | What the build does |
| --- | --- | --- |
| Birth date, time, place; birth name | **Nothing.** No field holds the owner's birth data (agent searched `Person`, `UserProfile.facets`, `SelfClaim`, `UserModel`, `/api/whoami`). `harvest_coverage.py:231` and `:435` drop the owner's own birthday from Instagram and ChatGPT exports with the note "already in the self-model", which the agent could not back. | Four person statements in the Self: user-confirmed `SelfClaim` rows written the way `gaps.store_answer` (gaps.py:52) writes an answer, under a `birth` entry in `self_directory.DIRECTORY_SPEC` (self_directory.py:50) so `my_gaps` raises the quest and `answer_about_me` fills it. The harvested birthday becomes an evidence-backed proposal the person confirms (W1), never a silent value. |
| Place to coordinates, time zone on the date | `geocode.py` is reverse only (coordinates to name, via Nominatim, an outside call). `tzfpy` is already a dependency (requirements.txt:95) and gives a zone from coordinates. | A shipped gazetteer (towns with coordinates) resolved locally; `tzfpy` for the zone; the tz database for the rule in force on the date. No outside call (the CI vendor-egress gate would refuse one anyway). |
| A faculty that reads the brain and may call a model | `interest_deepen.py` (entry `deepen` :92; consent `identity_consent.may_infer` :100; `self_cogs.blocked` :107; `llm_client.call_claude_with_cost(feature=...)` :79; saves with `brain.upsert_self_claim`). The dossier `self_report.py` stores a versioned `UserModel` row. | `oracle/` modules in the hub: `numerology.py`, `astrology.py` (pure), `reading.py` (draw, context pack, free rendering, composer). The composer uses `llm_client.call_claude(feature="oracle.reading", trigger="user")`; readings are stored as documents (kind `oracle.reading`), never as claims. |
| The model call, spend, local first | `llm_client.call_claude` (llm_client.py:680) runs the open-source model when configured and no cloud key is present, else asks approval per job; `oss_router.complete(task, tier)` picks local or frontier; feature names for the approval screen live in `spend_approval.FEATURE_NAMES` (:66) and `FEATURE_DESCRIPTIONS` (:111); `llm_meter.spend_by_feature` reports by feature. | Feature `oracle.reading` registered in both tables; flag `ORACLE_MODEL` (unset = OFF, the `COMMAND_ASK_MODEL` pattern, verified by me in `command_ask.py:54` on the D7 worktree); tier local; no fallback to frontier. |
| The place on the screen | `/command` (app.py:17094) renders `command_screen.html` + `screen.js`; a layer is added through `command_layers.py` and `GET /api/command/layers`; a self-registering lane is the studio (`studio_routes.register(app, limiter=, require_owner=)`, wired at the bottom of app.py, with `/command/studio` and `/api/studio`). | `oracle_routes.register(app, limiter=)`: `/command/oracle` (the room), `/api/command/oracle/{draw,readings,mark,quest}`; a line on the character pane; a landmark in the world view; a tab on the phone. |
| Character sheet families | The step-2 mock holds the sheet (ToawzsXxbYLX5ANXNdMH2H); families are added and marked NEW (q377). | Families "Numbers" and "Sky", lines in state DERIVED with the computation as evidence. |
| MCP tools | `novahub-mcp`: `tools/<module>.py` with `@mcp.tool()`, registered through `tools/__init__.py`, grouped in `tools/guide.py _CATALOG` (:157) with `requires_entitlement`; calls go through `mesh_client` with `X-Acting-Email`. | `my_numbers`, `my_chart`, `sky_today`, `oracle_reading` (read), `oracle_draw` (inward write). |
| The morning line | The command book: `command_book.compose` (command_book.py:649) sets `book[...]` fields; `render_book_html` (:1217) renders lines such as `health_line` (:1171). `MASTER_REPORT_ENABLED` gates the cron; the inventory says it is unset in production (agent's word, unconfirmed). | One `oracle_line` field: personal day, Moon sign and phase, card of the day. Deterministic, free. |
| Entitlement | No per-user feature-flag table; `_CATALOG` groups gate on an app key (`lucid`, `echo`); `APP_CATALOG` (app.py:99) and `app_entitlement` rows for a new key. | Gate the oracle group on an existing personal key in v1; a per-account switch in `system_settings` turns it off. |

## Rules the whole set keeps

1. Inputs are stated, never inferred; a harvested birthday is a proposal until confirmed.
2. The six refused kinds (q376 A) are refused in code with tests; health is never in a reading's context.
3. A reading is a document; nothing writes to the Self; the strategist never reads a reading.
4. Numbers and positions are computed offline; the only model call is the composed reading, behind `ORACLE_MODEL`, priced first, local first, never a fallback.
5. Birth data is top-tier personal data: out of every outward surface and the license projection, never in a URL or a log.
6. Nothing outward. A reading can propose a quest; the quest goes through the queue like any other.
7. No badges, streaks or scores attach to any of it.
8. Every empty state is named: "not told yet", "no time of birth", "model not named", each its own line.

## Tasks (filed on the Conductor desk, unqueued; the owner queues)

One desk each. Order within the set: 0 and 1 first, then 2 and 3 in parallel, then 4, then 5 with 6 reviewing, then 7; 8 and 9 any time, 9 before any customer sees the room. Project `one-interface` for all.

| # | Lane · key | Does | Done when | Size |
| --- | --- | --- | --- | --- |
| 0 | PRIVACY · ORACLE-BIRTH-DATA-RULES | Classifies birth date, time, place and birth name as top-tier statements; sets retention, the outward and license exclusions, the no-URL no-log rule; reviews task 1's PR. | A written rule in the privacy register and a PASS comment on task 1's PR. | S |
| 1 | INTELLIGENCE · ORACLE-BIRTH-STATEMENTS | The four statements as user-confirmed claims; the `birth` directory entry so `my_gaps` asks and `answer_about_me` fills; the gazetteer and zone resolution, offline; the harvested-birthday proposal; fixes the unbacked "already in the self-model" drop. | Gap quest shows on an empty account; answering it stores four confirmed claims; place resolves offline; tests; draft PR green. | M |
| 2 | INTELLIGENCE · ORACLE-NUMEROLOGY | `oracle/numerology.py` per ORACLE_NUMEROLOGY.md; `my_numbers`; the book line; the Numbers family payload. | The worked example and every listed test pass; the line appears in a book render; draft PR green. | M |
| 3 | INTELLIGENCE · ORACLE-ASTROLOGY | `oracle/astrology.py` per ORACLE_ASTROLOGY.md; skyfield + vendored DE421 (after card 1); houses and angles in our code; `my_chart`, `sky_today`; the book line; the Sky family payload. | J2000 anchor and published-chart fixtures pass; degraded charts and the DST refusal work; no runtime fetch; draft PR green. | L |
| 4 | SURFACE · ORACLE-CHARACTER-FAMILIES | Numbers and Sky families on the character pane (DERIVED state, computation as evidence), the gap-quest line, the "Visit the fortune teller" line; phone layout. | Pane renders both families from the hub payloads with correct empty states; byte-identical page for accounts with no statements; tests; draft PR green. | M |
| 5 | INTELLIGENCE · ORACLE-READING-FACULTY | `oracle/reading.py`: draws with `secrets` and recording; the 78, 64 and 24 tables as data; the context pack with its refusals; free rendering; the composer behind `ORACLE_MODEL`; reading documents; quest proposals. | Every test in ORACLE_FORTUNE_TELLER.md passes; with the flag unset no model call is made; draft PR green; DOORS review requested. | L |
| 6 | DOORS · ORACLE-GATEWAY-AND-REVIEW | Feature `oracle.reading` in the spend tables; flag semantics; local tier, no fallback; proof that nothing in `oracle/` or the room reaches any host but the gateway; review of 5 and 7. | PASS comments on 5 and 7, or findings filed; the egress gate run on both heads. | M |
| 7 | SURFACE · ORACLE-FORTUNE-TELLER-ROOM | `oracle_routes.register`: `/command/oracle` with the table, the draw, the reading and the journal; the world landmark; the phone tab; price shown before any composed reading. | Room works end to end with the flag unset (free readings) and with a mocked model; the "what she drew on" panel lists every pack item; tests; draft PR green. | L |
| 8 | DESIGN · ORACLE-TELLER-AND-DECK | The teller (three names for the owner to pick, face, voice notes), the room's look in the crystal aesthetic, the deck plan (1909 deck as stand-in; a Studio deck later under the owner's ceiling), the draw motion. | A page the owner can open; assets or the Studio brief handed to 7. | M |
| 9 | COUNSEL · ORACLE-TERMS-LINE | The "for reflection and play, not advice" sentence in the user terms outline (L1) and in the room; what a reading is not. | Text agreed and placed; the room's footer shows it. | S |

## Decisions for the owner (cards through the router; defaults chosen so work can start)

1. **Ephemeris route.** skyfield (MIT) with a vendored public-domain JPL file and houses in our code (default), or Swiss Ephemeris under its paid licence (a spend and a vendor).
2. **Reading model and ceiling.** Which local model writes composed readings, and the per-reading ceiling. Default: none named; free readings work from day one; nothing composed until he names one.
3. **Money questions.** May the teller speak to a money question using the runway figure the person already sees on the Resources bar. Default: yes, only when asked, never from inferred finance claims; health never.
4. **Deck art.** The public-domain 1909 deck now, a commissioned deck in the game's style later through the Studio under his ceiling. Default: yes to both, in that order.
5. **On by default.** The oracle present for every account with one switch off (default), or opt-in per account.

No card is needed to queue the tasks: the owner queues on the Conductor desk.

## What this desk verified, and what it took on trust

Verified by me: the owner's words above (this session); q361, q369, q376, q377 and the eight sheet
defaults (read on the Router desk and the Build Board); The Game of Your Life, P1, P2, K6, W1, W2
and S3 (read in the audit folder's sources); `COMMAND_ASK_MODEL` unset = OFF (read in
`command_ask.py` on the D7 worktree); no astronomy library in the hub's requirements or venv; this
repo's bare `pytest` on the docs branch (538 passed).

Taken on trust, from the read-only survey agent: every hub file and line number in the table
above, the absence of birth fields, the `harvest_coverage.py` note, the `MASTER_REPORT_ENABLED`
production state. The local hub checkout was 52 commits behind `origin/main` when it looked; its
lines are from `origin/main`.

Not done here: no code, no hub change, no Railway change, no model call, nothing sent off this machine.
