# One place for everything: survey (ONE-PLACE-SURVEY, SURFACE, 2026-10-02)

Read-only. No code changed, nothing merged. Source: the owner in the conductor chat
(local_da515743, ~23:20 UTC): one interface everyone sees, "an upgraded Claude", holding the
command center, the spatial maps, the talking Jarvis and a place to ask, all congruent, skin and
fonts futuristic, spatial and deep; usable now, online or on his own computer.

**How this was read.** Hub `origin/main` is `d094a57` (2026-10-02 20:10 UTC). I read the six
artifacts, the four live SURFACE sessions and the conductor and router transcripts, the hub,
leadfuel-ios and Prime repos, the Conductor desk task store, and probed the live site with GET
requests. "Verified" below means I (or a read-only agent I ran, marked *agent*) read the file,
route or page; "trust" means a session, PR body or page said it and I did not re-check.

## 1. Inventory

| # | Piece | Where | State | PR / task | How sure |
|---|---|---|---|---|---|
| A | Admin command wall | hub `app.py:16211` `/admin/wall`, `/api/observability/wall` (16121), `templates/admin_wall.html` 691 lines, `wall_lenses.py`, `observability_wall.py` | **Live** (403 to everyone but a bare admin, probed today). Renders a focus and its neighbourhood (#654 merged 09-27), 4 lenses system/me/goal/connections, 3 registers, 6 presets, `view=spatial|tree`, `big=1`, a findings rail, SVG forms inline. No dolly, no timeline strip, no button (by design). 16 wall test files, 254 tests | hub #654 MERGED; #715 (TUFTE-G3) OPEN draft | verified (agent + my grep); live render seen by the owner 09-26 (trust) |
| B | Goal workspace | `/goal`, `/goal/<plan_id>` (`app.py:9401`), `goal_workspace.html` 215 lines, two POST controls | **Live** (200; signed-out shows the login prompt and "No active goal"). Nav button "Command Center" for every signed-in user points here (`tests/test_nav_command_center_link.py`) | merged | verified |
| C | Per-account command center `/command-center` | `account_wall.py` + `admin_wall.html` switches | **Draft** (live 404) | hub #713 OPEN draft (Q112 own_only) | PR body trust; 404 verified |
| D | Flow Atlas (3D crystal) | artifact `UCCG9zfCDWeveQMuT1MFZ5` (DESIGN) | **Design only**; 90 parts, 167 flows, states hand-recorded from main 4c54132; three.js from jsdelivr | — | verified (read) |
| E | Atlas in the Command Center `/goal/atlas` | branch `atlas-in-command-center`: `atlas.py` 238, `templates/goal_atlas.html` 985, `static/atlas/topology.json`, vendored three.js r147, admin only | **Draft, not on main** (no atlas file on main). Live `/goal/atlas` answers 200 but that is the `/goal/<plan_id>` catch-all (a nonsense id answers the same) | hub #730 OPEN draft; waits on #713/#719/#720 | verified branch + probe; merge order trust (router) |
| F | Atlas live per-line counts, `/goal/atlas/live` | branch `atlas-live-flows` stacked on #730 | **Draft**; CI pytest passed, gates job cancelled under load, local gates run orphaned | hub #736 OPEN draft (session local_6345dfcd) | trust (desk report) |
| G | Atlas as a command center (act) | `docs/ATLAS_COMMAND_CENTER.md` on `atlas-act-design` (569 lines): one route `POST /goal/atlas/act`, tiers SAFE/CHANGE/OUTWARD/FIX, T1-T19 threats, Q1-Q5 | **Design done**; build is part 2 in three PR slices after #736. Owner answered Q1-Q5 at 23:23 UTC (Q4 = A: user and admin modes; an admin never reaches another person's data) | hub #739 OPEN draft; ATLAS-ACT 2/2 live (local_da34f6df, Fable) | doc verified; answers from ROUTER #12's relay in that session (trust) |
| H | Atlas Live | artifact `6LEvF7K9u9qnSxh68VWsfA` | **Live on claude.ai**, polls the brain connector (recent_memory, corpus_stats, pending_actions, current_spend); two pools dashed as unknown | — | verified (read) |
| I | Spatial Views Menu | artifact `G6HiaFgajgX6FSvAhfyMQz`: 37 views V01-V37, 18 layers L01-L18 | **Design only**; all 55 picked build (conductor's reading); tasks SPATIAL-1..6b across DESIGN, INTELLIGENCE, NODE, WATCH, ARMS, SURFACE. "Where the atlas lives" has **no pick** | — | verified page; picks trust |
| J | LeadFuel Command v7 | artifact `P2My4JdZjnEUtZDFer3ZBs` | **Design only**: the futuristic skin (Barlow Condensed + JetBrains Mono, cyan on near-black, grid, dolly, "The day" strip). Partly ported by #654 (focus, rail, forms); dolly and strip not | — | verified |
| K | Command Wall Completion | artifact `T3xe9GE65ZjeVFaTGuW7K5` | The CWC-* to-do; 10 owner-only items are already cards q159-q168; 5 ATLAS-ACT questions cards q154-q158 | — | page verified; cards trust (ROUTER #12) |
| L | Tufte PRs | hub #720 (G1 `--lf-brand`, plan measure), #719 (G2 outcome layer on `/goal`), #715 (G3 wall plots real data), #716 (G7 house rules) | all OPEN drafts | — | gh verified |
| M | Skins and tokens | `static/brand/v1/tokens-leadfuel.css` = `static/leadfuel-design-tokens.css` (identical), same for the novah pair; admin base `templates/admin/_base.html` dark by default; `--lf-font` is the system stack; **no font files under static** | live | — | verified (cmp) |
| N | iPhone app | `leadfuel-ios` branch `command-center-home` (f5a6b14): Command, Approvals, Ask (chat over connector `ask`), Inbox, More; MCP connector only, OAuth PKCE; no wall, atlas or voice; no EAS build ever | **Local scaffold** | ios#1, #2, #3 OPEN drafts; no runner | agent verified |
| O | Voice / Jarvis | `F:/repos/Prime` branch `desktop-x17` (`jarvis/` 3,205 lines: wake word on local faster-whisper, local STT, **edge-tts default = a transmission**, Claude Agent SDK brain, hub as MCP); branch `voice-in-the-app` adds `docs/VOICE-IN-THE-APP.md` (P0-P6); home-node `app/assistant/voicehost.py`, `voicelink.py`, `ui/voice.js` in the estate repo | **Local, parked** (NODE session local_12cb0972 at its usage limit; task CAND-jarvis-voice-hud open). First finding: `setting_sources` unset, so a wake-word turn could run the 23 allowed Bash rules (railway, git push, gh, curl) | P1/P2 "landed" per commit messages (trust) | doc verified |
| P | Ask | hub `POST /api/ask` (service token, acting email, credit-gated, `ask.py`), `/api/ask/intent`, `/api/ask/route` (arms' ask, `docs/THE_ASK.md`); **no page**; connector tool `ask` (used by the iPhone Ask tab); `feat/ask-loop` branch is the arms' ask, 302 behind | APIs live, no person-facing box | CWC-E1 open, not started | verified |
| Q | What the app does (connector) | `what_can_you_do`: 16 groups, 99 tools (`novahub-mcp` c9187a8); outward actions always queued through the connector | live | — | verified (called it) |
| R | Flow Law Audit | artifact `8bsQE73XBSBNYoNED4ffHj` | What the surface must not claim: `RUNNER_REQUIRE_APPROVAL` defaults off; `egress.send` has one caller; wall Finance and Connectors boards read Ready on incidents (SURFACE-owned finding); 11 atlas corrections | — | verified (read) |
| S | Signed-in home | `/` → `home.html` launcher (no ask box); nav Home, Knowledge, Documents, Integrations, Command Center (`/goal`), Me, Connections, Welcome; dark when signed in | live | — | agent verified |
| T | Production substrate | DB never migrated (ON5), so goal_id, contacts, event_uid are absent online; `/healthz` today: rev d094a57, warden enforcing, worst cron `watchdog` stale 321 min | live | cards exist | probe verified; ON5 trust |

## 2. Conflicts

1. **Three "command centers".** `/admin/wall` (estate, bare admin, read-only, the v7 target), `/goal` (per person, operable, the nav calls it Command Center), `/command-center` (#713, per-account wall). Three gates: bare admin, session, `ADMIN_EMAILS` (T17, T19 in #739). The owner's Q4 answer settles the model (user and admin modes), not the URL.
2. **Three skins.** v7 (Barlow/JetBrains, cyan, Google Fonts) vs Novah tokens (indigo, system font: Flow Atlas, Spatial menu, Atlas Live) vs leadfuel tokens (admin base). The wall promises zero external assets and the CSP is `script-src 'self'`; v7's Google Fonts break that. Indigo means "selected" in the atlas and cyan means "accent" on the wall; the Tufte house rule says colour marks exceptions only.
3. **Where the atlas lives.** The menu lists four homes with no pick; #730 is already building it inside the hub; Atlas Live is already a claude.ai page; SPATIAL-1-live-atlas (DESIGN, "Opus high") would build a second live atlas over the connector. Two live atlases, one model.
4. **ON4 unresolved**: the wall JSON answers 403 to every public origin, so any phone, kiosk or client-rendered view of the wall is blocked; #730 side-steps it by composing in-process.
5. **Admin-only atlas vs "what everyone will see".** #730 is `_require_bare_admin`; the owner wants it as the person's place. No per-user atlas exists; #713 is the per-user precedent.
6. **Two act designs**: CWC-S11 "ACT lens on the wall" (the wall's no-button rule) vs ATLAS-ACT on `/goal/atlas` (the control family, owner-answered). Keep one.
7. **Two asks**: CWC-E1 (deterministic, graph retrieval, cites node ids, never decides) vs the connector `ask` (LLM over the brain, k=8, what the iPhone already uses) vs `/api/ask` (credit-gated, token only).
8. **Voice has no web path.** Prime jarvis is a desktop process; the home-node voicehost is a pane in the Assistant app; echo's tts is a cloud arm. Nothing speaks or listens in the browser. edge-tts as the default voice is a Law 9 transmission.
9. **Stale statuses on the CWC page**: S0, S3, S7, S8 read "open" but #654 shipped them; S16 is now answered by the owner's Q4; the page's section 7 recipe is the only local-run doc (OF1 open).
10. **Truth on the live site**: boards read UNKNOWN until ON5, and Finance/Connectors overstate (audit). A futuristic skin over those readings would be a lie dressed well.
11. **Duplicate token files** (two identical pairs).
12. **Model pins**: SPATIAL-1 says Opus; ATLAS-ACT and ATLAS-B1 are Fable; the owner asked whether this should be Fable (section 6).

## 3. One information architecture

One route family, one shell, one acting account per session (Q4 = A), two modes.

- **Shell** `/command` (one page; `/goal` and `/admin/wall` become views in it). Top bar: mark, apex state pill, **mode** user | admin, **register** plain | operator | developer, clock, **Ask box with a mic**. Skin: v7 with fonts self-hosted under `static/fonts/` and no external asset; one tokens file.
- **Views** (the v7 tab row):
  - **TODAY**: needs (the ME ladders), what is waiting on you (approvals with ages), goals worst first, what's on today. This is the iPhone Command tab's content; same JSON.
  - **MAP**: the atlas crystal (#730), live counts (#736), the part panel with SAFE/CHANGE/OUTWARD/FIX actions (#739 part 2).
  - **WALL**: the focus-and-neighbourhood renderer that exists, lenses system/me/connections/goal; the tree stays the engineering view.
  - **ACT**: the approval queue and the act audit; every outward step a proposal; disposition before the click.
  - **ASK**: a conversation over the person's brain; every answer cites the rows it read; the mic is an input to it; speech out is on-device.
- **Modes**: user = the person's own tree (#713's allow-list readers); admin = the estate boards plus the admin's own needs, never anyone else's information.
- **Data**: in-process composition on the hub (the 60 s snapshot), one session-authed JSON per view on a non-`/api` path (this is the ON4 decision), so the phone and a kiosk read the same feed.
- **Rules the shell keeps**: four states never folded; unknown never zero; a parent never greener than its worst child; nothing outward without the queue; colour only for exceptions and always with a word; reduced motion is a cut.

## 4. Fastest honest path to usable now

- **Online today, no work**: sign in at `leadfuel.cloud/admin/login` and open `/admin/wall` (bare admin). It renders the focus view with the four lenses and wall mode. `/goal` is live for any signed-in user. Honest caveats: most boards read UNKNOWN until the production migration (ON5); Finance and Connectors can read Ready during an incident (audit); it is not the futuristic skin and has no atlas.
- **On the owner's computer this week (the real fastest)**: a local run of the `atlas-live-flows` head (it contains #730) with the CWC section 7 recipe: SQLite, `NOVAHUB_OWNS_LOGIN=1`, a generated admin, port 5057. That shows `/admin/wall`, `/goal`, `/goal/atlas` with the crystal and live counts, all offline, without merging anything. OF1 (write the recipe into the repo as one command) is the only task it needs, and it is small.
- **Online with the atlas**: the merge train #720 → #719 → #713 → #730 → #736, each under the ci-novahub hold. The hold has been held by D4-build-A since 21:30 UTC with 16 waiters; the owner clearing that prompt is the only thing on the critical path today. One to two days of CI after that. No owner approval is needed for the merges themselves.
- **Not fast**: the skin, the ask box and voice. None of those exists in the hub today.

## 5. Ordered tasks per lane (with the why)

Wave 0, unblock (now, no owner decision):
- NODE/owner: clear the stuck prompt holding ci-novahub (card already asked). Why: five drafts and the atlas wait behind it.
- SURFACE: land #720, #719, #713, #730, #736 in that order (existing tasks TUFTE-G1, TUFTE-G2, ATLAS-in-command-center, ATLAS-LIVE-FLOWS), then #715, #716. Why: the atlas and the per-user wall are built and only need the hold.
- SURFACE: CWC-OF1 local run recipe as one command. Why: section 4.
- Conductor: mark CWC-S0, S3, S7, S8 done (shipped in #654) and close S16 (answered by Q4). Why: the page misleads the queue.

Wave 1, decide and design (after the cards in section 7):
- **NEW DESIGN · ONE-PLACE-DESIGN**: the shell in section 3 as a design artifact plus a tokens PR: v7 skin made CSP-clean (self-hosted Barlow and JetBrains Mono), one tokens file (delete the duplicate pair), mode/register/ask/mic chrome, phone and wall-mode layouts, the atlas and the wall sharing one palette (colour for exceptions only). Why: the owner picks the look once, before anything is built on it. Merges: CWC-S2 (palette), TUFTE-G7's house rules, DESIGN's Spatial-menu skin.
- **NEW SURFACE · ONE-PLACE-SHELL**: `/command` with TODAY, MAP, WALL, ACT, ASK tabs, user and admin modes, the nav button moved, `/goal` and `/admin/wall` redirecting in. Why: the one URL everyone sees. Merges: CWC-S8 (register switch), S9 (saved profile), H1 (signed-in home), S15 (links), S4 dolly, S5 arcs, S6 strip as its polish slice. Drops: CWC-S11 (ACT lens) in favour of the ACT tab plus ATLAS-ACT.
- DESIGN: **drop SPATIAL-1-live-atlas** as a build; keep Atlas Live (the claude.ai page) as the debugging mirror. Why: one live atlas, in the hub, first-hand states. ATLAS-VIEWS stays, after the shell.
- DOORS: **ON4 → NEW DOORS · SHELL-JSON-SESSION-READ**: session-authed per-view JSON on a non-`/api` path, rate-limited (CWC-F5), with the snapshot age (F6). Why: the phone, the kiosk and any client-rendered view need it; nothing else unblocks SPATIAL-2 or V37. After the owner's card.

Wave 2, act and ask:
- SURFACE: ATLAS-ACT 2/2 slice 1 SAFE + FIX (existing, Fable). Then **NEW VAULT · ATLAS-ACT-THREATS** (review T1-T19 and Q1-Q5 as answered) before slice 2 CHANGE and slice 3 OUTWARD. Why: the design says VAULT reviews before anything changes state.
- **NEW INTELLIGENCE · ONE-PLACE-ASK**: one ask path for the signed-in person, over the brain, every answer citing the rows it read, metered, served on the shell and shared by the iPhone Ask tab. Why: "a place to ask" exists only as an API and a phone tab; E1's rule (no citation, no answer) is the honesty bar. Replaces CWC-E1.

Wave 3, voice (NODE, after the P0 cards):
- NODE: resume CAND-jarvis-voice-hud: P1 first and alone (`setting_sources=[]` in three places; a wake-word turn must not reach the allowed Bash rules), then P2/P3. Why: a write path behind a microphone goes before any feature.
- **NEW NODE · VOICE-IN-THE-SHELL**: the mic on the Ask box talks to the home-node voicehost (local STT) on the owner's machine; speech out on-device (P4); edge-tts only behind the Law 9 gate; the online shell shows the mic greyed with the word "local only" until a gated path exists. Why: Law 9; a cloud path is a decision, not a fallback.

Wave 4, phone, wall and truth:
- SURFACE: GOAL-iphone-command-center → the iPhone shows TODAY, ASK and ACT over the connector from the same JSON; ios#1, ios#2; CAND-ios-ci-workflow (NODE registers the runner). Why: same views, no second product.
- SURFACE/INTELLIGENCE: the audit's wall truth fixes (Finance/Connectors Ready on incidents, CWC-T18, CWC-T4 egress ledger), TUFTE-G3. Why: the skin must sit on honest readings.
- DOORS/owner: ON5 migration decision (card exists). WATCH/NODE: SPATIAL-3b, SPATIAL-5 later; ARMS SPATIAL-4 after the shell.

## 6. Model advice

Fable weekly stood at 22% at 23:45 UTC today; it resets 2026-10-03 21:00 UTC; the cap is three Fable desks at once. Fable earns its cost where the shape is decided, not where it is typed.

- **Fable**: ONE-PLACE-DESIGN (the whole look and layout, once), ONE-PLACE-SHELL (one template hosting five views and two modes, many interacting rules), ONE-PLACE-ASK (the citation rule and the privacy wall together), ATLAS-ACT 2/2 slice 1 (already pinned). Open these after the reset, three at a time.
- **Opus** (security- or auth-shaped per the routing rule): SHELL-JSON-SESSION-READ (DOORS), ATLAS-ACT-THREATS (VAULT), ATLAS-ACT slices 2 and 3, voice P1 (NODE).
- **Sonnet**: the merge train and CI babysitting, OF1, the iPhone screens, ATLAS-VIEWS, SPATIAL-4.
- **Haiku**: deleting the duplicate token files, marking the CWC page.
- **Not a model**: ON4, ON5, the P0 voice decisions, and the cards below are the owner's.

## 7. Owner decisions needed (candidate Router desk cards)

Do not repost q154-q158 (ATLAS-ACT Q1-Q5, answered) or q159-q168 (CWC owner items). ON4 may already be among q159-q168; if so, C4 is a duplicate.

| id | Title | Options | Default | Why |
|---|---|---|---|---|
| C1 | Where the one place lives | A) new `/command` hosting every view; `/goal` and `/admin/wall` redirect into it. B) grow `/goal` into it. C) keep three pages and link them | **A** | one URL everyone sees; Q4's two modes map onto it; it answers S16 |
| C2 | The skin | A) v7 LeadFuel Command, fonts self-hosted. B) the Novah tokens (as the atlas). C) a new skin from DESIGN | **A** | the wall already half-implements it and it is the futuristic, deep one; self-hosting keeps zero external assets |
| C3 | Where the atlas lives | A) in the hub as the MAP view (#730/#736); Atlas Live stays a debugging mirror. B) a claude.ai page only (SPATIAL-1). C) both, fully | **A** | one live model with first-hand states; drops a duplicate build |
| C4 | How the phone and a kiosk read the wall (ON4) | A) session-authed JSON per view on a non-`/api` path. B) server-rendered only | **A** | nothing client-side can exist otherwise |
| C5 | Voice path | A) resume CAND-jarvis-voice-hud, P1 safety first, on-device speech, no edge-tts default. B) voice in the web shell first through the browser's speech services (a vendor transmission, gated). C) park voice until the shell ships | **A** | the `setting_sources` finding is a write path behind a microphone; Law 9 |
| C6 | Fable for this | A) Fable for design, shell and ask, three desks after the reset. B) Fable for design only. C) none | **A** | the shape decides everything after it; 22% used, reset in a day |
| C7 | Usable now | A) a local run of the #736 head on the owner's PC this week plus `/admin/wall` online as is. B) wait for the merge train | **A** | shows the whole future place in a day without merging |
| C8 | What "ask" means | A) one ask over the brain, cited rows, shared by the shell and the iPhone. B) E1's deterministic graph-only ask. C) both | **A** | one answer path; the citation rule keeps it honest |

## What this survey did not do

No database reads, no production settings, no pytest, no sign-in to the live site. The four live
sessions were read, not messaged. Claims from PR bodies and desk reports are marked trust above.
