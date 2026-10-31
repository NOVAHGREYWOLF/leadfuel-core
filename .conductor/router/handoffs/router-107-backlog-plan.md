# NovahOS app backlog plan: every unbuilt task, as parallel desk briefs (2026-10-31 Pacific)

Planner: read-only agent for ROUTER #107 · one-app. Source of the order: owner via CONDUCTOR 056 (relayed, not heard by me).
No repo file changed. Base for every brief: **`one-app/int9`** (the newest train: int8 + modes1/2, left1, bridge1, hl1-hl4, panes1).
Branches `w3a`-`w3e`, `left2`, `hl6`, `hl7`, `proof1` are **not in int9 yet** (checked with `git merge-base --is-ancestor`).

## 0 - What was subtracted, and how I know

App Build page (artifact WXb79XUAzLZ6GUgKmJEkpw, collection `tasks`): **88 rows** (86 plus RUN-01/RUN-02). The page's own
status column is stale. I re-scored each row from branch commits and the handoff notes on those branches:

| Bucket | Count | Rows |
|---|---|---|
| Done (built on a branch; in int8/int9 or waiting on the train) | 74 | BP-01..04 (conv1, conv2); GAP-01..16 (ctx1, ctx2, cmd1, shell1; GAP-09 seen in app.js:1354); GAP-18..27, 29..48, 50, 51, 53..57 (shell1, shell2, agt1, code1, sto1, w3a, w3d, left1); HM-01, IN-03, IN-04, ST0..ST9, TP-01..03, VO-02 |
| In progress or train-owned | 4 | IN-01, RUN-01, RUN-02 (exe rebuild after the int9 train), GAP-28 (real-window proofs; behind panes1) |
| Waiting on the owner (excluded) | 10 | GAP-17, GAP-49, GAP-52, IN-02, IN-05 (other tiers need other hardware), IN-06, IN-07, IN-08, ST10, VO-01 |
| Whole rows still unbuilt | 0 | only remainders: GAP-16 skills still say "not built" in the / menu (shell1 note); `/init` and `/review` flip (left2 note, owner card) |

So the backlog below comes from: **doc 41 section 5** (C-tasks with no file anywhere), **doc 31 / 31a** rows still MISSING
or NOT WIRED and not owned, **doc 37** gaps (local AI), the **Command Center Build** page (CC-50/51/99, local half only),
and the owner areas REPORTS, COMMAND, LOCAL AI. Owned elsewhere and left out on purpose: hub/brain/connector work (ROUTER #109,
HL-1..HL-5 and hl6/hl7), trains int8/int9, the 11 pane/dock selftest failures (panes1), the left2 work, ST10, the outward
parts of GAP-17/49/52 and IN-06/07/08, Command Center account readers and H1-H4.

**Verified from git (int9 tree, all one-app branches):** no `ui/chrome.js`, `ui/looks.css`, `ui/bugreport*`,
`workstreamgate.py`, git pane, reports pane, command-center pane, curator, `tool_search`, or archive compact/rebuild/remove
exists on any `one-app/*` branch. `loop_guard.py` has no caller outside itself. `Assistant.py:185` still builds
`LocalEngine()` with no `gpu_yield`. No "regenerate" in the UI. `HUB_COMMIT` (a8e18856) already is PR #900, and
`home-node/tools/local_command.py` exists (62693d1), so CC-50 is mostly done. Settings sections Usage/Projects/Routines/Remote exist (shell2gate).
**Taken from docs, not re-checked:** doc 31 row meanings, doc 37 matrix, doc 41 C-task text, CC row text, every
"done" claim inside a handoff note (I read the notes; I ran no test).

## 1 - Rules for every brief

- Branch from `one-app/int9`. Local only. No download, no network, no spend, no secret. Interpreter `home-node/build/venv-assistant`.
- **NEW files only**, plus **at most one-line edits** to the shared files: `ui/index.html` (one `<link>`/`<script>` line per new file),
  `ui/panes.js`, `ui/app.js`, `assistant/gate_list.py` (one `Gate(...)` line), `assistant/wiring.py`, `tests/mockbridge.js`
  (one fenced `/* <ID> begin */ ... /* <ID> end */` block). Anything bigger in a shared file: stop and ask the router.
- **Do not edit `ui/selftest.js`** (panes1 holds it). Add `ui/selftest_<id>.js`; the train wires the one call.
- Every new gate module: one line in `build/NovahOS.spec` hidden imports (the left1 test asserts it).
- Tests: the new test files plus neighbours, and `SKIP_TESTS=1 sh scripts/gates.sh` if the repo has it. No full pytest (train's job).
- A check that cannot see a state says `unknown`, never a colour.

## 2 - Desk briefs (14, disjoint NEW files)

| # | Brief | Items (id: one-line goal) | NEW files | Shared one-liners | Outward? | Size |
|---|---|---|---|---|---|---|
| 1 | **CHROME** window frame and menus | C1.1: menu button + title bar (sidebar toggle, back/forward, title menu, right toolbar, panes toggle), status strip under it; C2.4: menus wired to existing actions (New, side chat, open folder, settings, reopen closed, zoom, theme, full screen, Help); GAP-05 rest: `Ctrl+\`; N24: narrow-window drawer sidebar | `ui/chrome.js`, `ui/chrome.css`, `ui/responsive.css`, `tests/test_chrome_ui.mjs`, `tests/test_chrome_ui.py` | index.html x3 | none | L |
| 2 | **LOOKS** look tokens | C1.2: one token file per look, `data-look` on the root, View-menu switch (uses CHROME's menu if present, else a Settings palette row); stop forcing `skin-mockup3.css` | `ui/looks.css`, `ui/looks.js`, `tests/test_looks_ui.mjs` | index.html x2 | none (owner Q1 picks the default) | M |
| 3 | **SIDEBAR-V4** nav finish + bug report | C2.2 rest: v4 nav order, Library merges Archive + Catalogue, Character Design leaves the nav, account footer row + menu + bug icon (applied through the NovahNav API, not by editing panes.js); C3.6: Report a problem pane writing a local file only | `ui/navv4.js`, `ui/navv4.css`, `ui/footer.js`, `ui/bugreport.js`, `assistant/bugreportgate.py`, tests | index.html x4, gate_list x1, mockbridge block | none (file stays on the PC) | M; start after panes1 lands |
| 4 | **WORKSTREAMS** store and Code sidebar | C3.1: project > workstream store + bridge (`workstreams_list`, `workstream_parts`, `workstream_tests`; desk/build gates switch to it on their own); C3.4: Code sidebar project > workstream > Desk/Build tabs > sessions (mounted by a new file, `NovahCode` hook only); conv2 rest: Desk with a count in the Home nav; H17: board view of a workstream's parts | `assistant/workstreamgate.py`, `lfdesk/workstreams/store.py`, `ui/wsnav.js`, `ui/wsboard.js`, `ui/ws.css`, tests | gate_list x1, index.html x3, mockbridge block | none (Sec review: new store) | L |
| 5 | **CHAT-ACTIONS** | N4/W4: pin and tag a chat; N5/W5: archive and export a chat (local file); W6: regenerate, continue, branch from a message; W7: per-chat system prompt, saved presets, prompt library (chatgate already has pin/tag/archive/export/branch: UI only for those) | `ui/chatactions.js`, `ui/chatactions.css`, `assistant/presetgate.py`, `lfdesk/presets/store.py`, tests | app.js x1 (message-menu hook), index.html x2, gate_list x1, mockbridge block | none | L |
| 6 | **ARCHIVE-MAINT** | D6: sources table; D7: remove a source (originals untouched); D16: compact (drop unreferenced blobs, VACUUM); D17: read-latency benchmark; D18: rebuild search index; D22: 2-4 ingest workers, opt-in | `lfdesk/panes/archive_maint.py`, `assistant/archivemaintgate.py`, `ui/archivemaint.js`, tests | gate_list x1, index.html x1, mockbridge block | none (D7/D16 are guarded writes: card + typed confirm) | M-L; start from left2's tip (it touched archivegate/archive.js) |
| 7 | **MODEL-MANAGER** (LOCAL AI: tiers, context, speed) | tier readout from NodeSpec/node-manifest; "recommended for this PC" shelf (doc 37 model shelf); per installed model measured tokens/s, first-token and load time on loopback Ollama; num_ctx probe on THIS tier (the measurable half of IN-05); O11: create a model from a local Modelfile (derived ctx/keep-alive variants) with an ask card. Read `modelsgate.py` first (it mentions Modelfile) and do not edit `models.js` | `assistant/modelmgrgate.py`, `lfdesk/models/bench.py`, `lfdesk/models/modelfile.py`, `ui/modelmgr.js`, `ui/modelmgr.css`, tests | gate_list x1, index.html x2, mockbridge block | none for these; pulls stay door-off (owner Q6) | L |
| 8 | **LOCAL-STACK** (LOCAL AI: Ollama/Hermes/Open WebUI) | one panel: each service's port, owner process, up/down/unknown, GPU or CPU (`ollama ps` PROCESSOR), the CPU-only-after-update check with a guided local restart through the supervisor, log tail; Hermes 64K model check (HM-01) and Engine C switch state (H25, `LFDESK_ALLOW_HERMES`); O9: give `LocalEngine` the GPU-yield prompt (keep / wait / unload) | `assistant/stackgate.py`, `lfdesk/stack/probe.py`, `ui/stack.js`, `ui/stack.css`, tests | gate_list x1, index.html x2, mockbridge block, `Assistant.py:185` one line (`gpu_yield=`) | none (loopback only) | M |
| 9 | **AGENT-SAFETY + small-model tools** (LOCAL AI) | H19: wire `tools/loop_guard.py` into the chat tool loop and `agentloop`; H20: prompt-injection scan before a routine is enabled; H38: `tool_search` (names first, schema on demand) for small local models; GAP-16 rest: skills listed in the / menu; `/init` + `/review` flip once owner Q3 answers | `lfdesk/tools/toolsearch.py`, `lfdesk/tools/loopwire.py`, `lfdesk/scheduler/scan.py`, tests | wiring.py x1 (wrap), `taskgate.py` x1 hook, `commands.py` small rows | none | M |
| 10 | **CURATOR** (LOCAL AI: self-learning, H8) | a nightly local routine reads the day's chats and writes an owner-approved suggestion list (memory proposals, skill drafts, routine ideas); never applies anything itself; local model only, refuses a cloud engine | `lfdesk/curator/review.py`, `lfdesk/curator/store.py`, `assistant/curatorgate.py`, `ui/curator.js`, `ui/curator.css`, tests | gate_list x1, index.html x2, mockbridge block | none | L |
| 11 | **REPORTS** pane and day-report quality | Reports pane: lists reports from the LOCAL hub (loopback) and local report files (the hub's offline interactive HTML), opens each in the sealed artifact frame; Fieldy day-report rubric scorer (named route, people and what they said, what the wearer did, real open items) with golden fixtures, shown as a score and "what is missing"; a daily routine that fetches the newest day report from the local hub only. Improving the generator itself (`novahub/fieldy_report.py`) is hub repo work: hand it to the hub reports router, not this one | `assistant/reportsgate.py`, `lfdesk/reports/index.py`, `lfdesk/reports/rubric.py`, `ui/reports.js`, `ui/reports.css`, `tests/fixtures/reports/*`, tests | gate_list x1, index.html x2, mockbridge block | hosted hub read = owner Q8 (default local only) | L |
| 12 | **COMMAND** local command center in the app | a Command pane that frames the loopback local command center (`home-node/tools/local_command.py` ticket flow; the device token never reaches the page); status line: node hub up, `HUB_COMMIT` pin, arm URLs loopback (CC-50 rest); CC-51: measure which local model answers the Ask box on loopback and record it; CC-99: link-lane reader reporting to the LOCAL hub only | `assistant/cmdcentergate.py`, `ui/cmdcenter.js`, `ui/cmdcenter.css`, `home-node/tools/link_reader.py` (estate repo, NODE lane), tests | gate_list x1, index.html x2, mockbridge block | switch-on and node restart = owner Q9 | L |
| 13 | **IMPORTS + BACKUP** | W2: Open WebUI history import screen over w3e's runner (dry run shown, typed phrase commits, verified backup first); H1: Hermes memories import over the g18 reader, same flow; H50: app-data backup and restore pane (local folder, restore needs a typed phrase) | `ui/imports.js`, `assistant/importsgate.py`, `assistant/backupgate.py`, `lfdesk/backup/snapshot.py`, `ui/backup.js`, tests | gate_list x2, index.html x2, mockbridge block | none; commit = owner Q5 | M; start after w3e lands |
| 14 | **STUDIO + GIT panes** | C4.2: Clip pane for Character Design results (studio window stays "open in own window"); C11: stop a render job (loopback `POST /api/jobs/{id}/stop`); C3: VRAM and CPU numbers on the studio chip; C3.7: Git pane for Code sessions (branch, status, log, diff, local reads only) | `ui/clip.js`, `ui/clip.css`, `lfdesk/tools/chardesign_jobs.py`, `assistant/gitgate.py`, `ui/gitpane.js`, tests | gate_list x1, index.html x3, mockbridge block, wiring.py x1 (job-stop tool) | PR status from GitHub = owner Q7 (default local git only) | M + M |

Totals: **51 unbuilt items in 14 briefs** (B1 4, B2 1, B3 2, B4 4, B5 5, B6 6, B7 5, B8 4, B9 5, B10 1, B11 3, B12 4, B13 3, B14 4).
Order of risk for the train: B3 waits on panes1, B6 on left2, B13 on w3e; B4 and B9 want a Sec read (new store, tool-loop wiring).
Not briefed (owned or later): real-window proofs GAP-28/C5.3 and the exe rebuild (train after panes1); vision, SSH, phone
approval, web search, music, code interpreter (downloads or outward: owner first).

## 3 - Owner questions (plain words, default in brackets)

1. Which look should the app open in? [the approved v4 mockup look; navy stays as a choice]
2. The Switches (shell, computer use) live in their own pane. Move them into Settings? [keep their own pane]
3. Typing /init or /review in a chat: act on the open Code session, or refuse in chat? [act on the open Code session]
4. Starting a repo's dev server in Code runs that repo's code. One confirm click each time? [yes, a confirm click]
5. Import your Open WebUI chats and Hermes memories into the app's history? [show the dry run; nothing written until you type the phrase]
6. Let the app download models you pick, one yes per model? [off; the app lists them only]
7. May the Git pane read pull-request status from GitHub (that goes online)? [no; local git only]
8. May the Reports pane read reports from the hosted hub (online), or only the hub on this PC? [this PC only]
9. Local command center: you restart the node hub and turn on NOVAH_LOCAL_AUTHORITY after the build. [built and left off until you do]
10. Drag one file from Explorer into Archive once, so we know real drops work. [until then the Add files button is the way]
