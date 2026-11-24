# One app: triage of the 57 gap proposals of the Full Claude gap audit (doc 38)

Item `redline-6` (NODE, ROUTER #135 wave 3), 2026-11-23. Source list: `home-node/38-Full-Claude-Gap-Audit.md`
section 3 (GAP-01..GAP-57, written 2026-10-30 against `one-app/int4`). Checked against the estate's `main` at
`96a57c9` (the app is `home-node/app/assistant/` in the estate repo). Names: hub, signal, scope, reach, orbit,
odyssey; the product is NovahOS.

## The finding that changes the job

**The queue's premise is stale. The 57 proposals are not "unfiled and not started".** All 57 have code on estate
`main`: the one-app desks (ONE-CTX2, ONE-SHELL-1, ONE-SHELL2, ONE-CMD-1, ONE-CODE1, ONE-AGT1, ONE-W3A, ONE-STO1,
ONE-C1, ONE-C3, ONE-D1, ONE-D2, ONE-D4, ONE-LEFT1/2, ONE-TERM-1 and others) built them on local branches in the
two days after the audit, and the int-train merged them. The queue's "0 hits in QUEUE.md, RUNBOOK.md, lanes.md"
was true and meant only that nobody had filed them there. So this triage is a verification, not a plan.

What I did and did not verify (read this before trusting a row):

- **Verified by me (ran):** an anchor check, one regex per proposal on the main tree. A missing file or pattern
  prints MISSING, never ok; it found one wrong anchor of mine (GAP-16 lives in `ui/composer.js`, read and
  confirmed) and 56 of 57 present as first written. It proves **code exists**, not that it works.
  Also ran 14 test modules for the landed features on a clean worktree of main, `unittest`, 364 tests, OK
  (test_ctxextras, ctxgate, ctxbar, shell1, shell2, cmd1, codex, agt1, skills_sto1, w3a_switches, phone_approve,
  imagegate_c1, d2_ssh, gate_list).
- **Verified by me (ran), a defect:** engine warnings never reach the page. See "Found while checking" below.
- **Taken on trust, from the desks' own handoffs (`home-node/handoffs/ONE-*.md`):** that each feature was looked at
  in a browser on the mock host, and every "not seen in the real WebView2 window". No desk looked at most of the
  new panes in the real window, and the real-window selftest is load-sensitive (ONE-GATEFIX-1). **"Landed" below
  means code and tests on main, not "proven in the window".** That proof is queue Stage 3, "prove by running".
- **Not checked:** the mockup (artifact) rows of doc 38; production; any network. Nothing here left the machine.

## Found while checking: engine warnings are dropped (build now, first)

`lfdesk/engine/base.py` says warnings that must reach the owner ride as `meta["warnings"]` on the `done` chunk. The
local engine puts these there: `CONTEXT_COMPACTED` (it removed earlier messages), `CONTEXT_TRUNCATED` (the server
cut the front of the conversation: the model is reasoning from a hole), `TOOL_BATCH_DISCARDED`,
`TOOL_CALL_REPEATED`, `MAX_TOOL_CALLS` ("Stopped after N tool calls"). The page has a handler for `warning`
events (`ui/app.js` `case "warning"`). **`assistant/turn.py` never forwards them**: its `done` branch returns only
tokens and model, and `git log -S` finds no commit that ever handled `warnings` there. Probe (run, a Turn over a
scripted engine whose `done` carries a `CONTEXT_COMPACTED` warning): events `turn_start, text, usage, turn_end`,
zero `warning` events. Doc 38 CB-08 said the compaction "is reported as a warning card"; that was read from the page
handler, not from a run.
Consequence: GAP-04's effort ("low" = 4 tool rounds) stops a reply with no word to the owner, and GAP-03's engine
compaction and the truncation tripwire are invisible. This is the first build-now item. Probe script and fix
plan are in `docs/handoffs/redline-6-handoff.md`.

## The table

Rooms are the NovahOS shell's rooms (sidebar v4, `ui/navv4.js`, plus the bars and panes inside them): **Chat**
(transcript), **Chat box** (composer, slash menu, attach), **Context bar** (the line under the box and the session
rail), **Code**, **Terminal**, **Memory**, **Artifacts**, **Library** (Archive and Catalogue), **Routines**,
**Agents** (agents, tasks, notifications panes under More), **Connections** (System), **Settings**, **Phone**,
**Shell** (window, keys, status strip).

Disposition: **landed** = code and tests on main, nothing owed that is small and code-only. **build now** = a
small, code-only, local slice is left and a desk can take it today. **later** = left, but large, Sec (running code,
memory, egress) or waiting on a download, a pairing or an owner choice. **closed by design** = a standing rule
forbids the Claude form (named in the row).
Sec = Opus plus a Law 9 look, as doc 38 tagged it.

| Proposal | Room | State on main | Disposition | Why / what is left |
|---|---|---|---|---|
| GAP-01 context line under the box | Context bar | `ui/ctxbar.js`, `ctxextras.py`; 187+30 tests per ONE-CTX2 | landed | Percent, used/total, hint line. Unknown shows "unknown". |
| GAP-02 `context_breakdown` and `/context` | Context bar | `ctxextras.py` | landed | chars/4 estimates marked approx. |
| GAP-03 compaction visible, `/compact` | Context bar | owner `/compact` built; engine compaction **invisible** | **build now** | Forward `done` warnings (finding above). Model-written summary stays out (Sec, a model turn). |
| GAP-04 effort and thinking | Context bar | `ctx_set_effort`, `ctx_set_thinking` | **build now** (warnings) / later (persist) | Effort stops are silent until the warnings forward. Persisting across restart is a choice (engine-wide today), later. |
| GAP-05 key grammar, Claude chords | Shell | `Ctrl+\`, `Ctrl+Shift+M`, Ctrl+` built; `Ctrl+Shift+E`, `Ctrl+Shift+B` **absent** (checked) | **build now** | Both were held back "nothing behind them"; effort (GAP-04) and the Code Preview tab (GAP-46) now exist. `ui/keymap.js` only. |
| GAP-06 local usage | Context bar | `ctx_usage`, `/usage`, Settings > Usage | landed (slice later) | Session model time and lines changed stay `unknown` on purpose: no per-reply time is stored (schema change), so later. |
| GAP-07 model warm until | Context bar | `ctx_warm` (loopback `/api/ps`) | landed | Local `/api/ps` read only; a silent probe says unknown. |
| GAP-08 header chips folder, branch, repo | Context bar | `ctxbar.js`, repo from `.git/config` | landed | Display only; credentials stripped from the remote. |
| GAP-09 copy chat id | Chat | `ui/app.js` menu | landed | Menu item and a Copy in the rail. |
| GAP-10 running-work badge, tasks | Context bar | `ctx_tasks`, Background tasks card | landed | Unknown parts are named, not counted as zero. |
| GAP-11 todo and plan | Code, Chat | `todogate.py`, Code Plan tab, Plan pane, Ctrl+T | landed | Code Plan tab and chat Plan pane; the list is per chat. |
| GAP-12 output styles | Chat box | `shellgate.py`, `/output-style` | landed | On the engine's copy only, never stored; skipped on voice turns. |
| GAP-13 vim keys | Chat box | `ui/shell1.js`, `/vim` | landed | Low value, built anyway. |
| GAP-14 session rail | Context bar | `ctxbar.js` rail, five cards | landed | Context, Environment, Changes, Background tasks, Usage. |
| GAP-15 RAM and VRAM | Context bar, Shell | `ctx_machine` | landed | RAM from the OS, VRAM from `nvidia-smi` capped at 3 s. |
| GAP-16 `/` slash menu | Chat box | `commands.py` registry, `ui/shell1.js`, `ui/composer.js` | landed | `/init`, `/review` flipped by ONE-D4. |
| GAP-17 images in | Chat box | `imagegate.py`, `ui/images.js` | landed (download later) | Vision model is on the installer list; **pulling it is a download the owner approves**. |
| GAP-18 attach anywhere | Chat box | `attach_pick`, text only | landed (slice later) | PDF and docx text extraction not built; needs a library choice. |
| GAP-19 `@` mentions | Chat box | `mention_search` | landed | The page can attach only a token the last search returned, never a typed path. |
| GAP-20 terminal output to chat | Terminal | `ui/term.js` "Send to chat" | landed | Proven in the real window per ONE-AGT1. |
| GAP-21 history, Ctrl+R, stash | Chat box | `ui/shell1.js` | landed | Local storage of this window; works if storage is blocked. |
| GAP-22 suggested next prompt | Chat box | `suggest_*`, off by default | landed | Local model only, only when idle. |
| GAP-23 incognito | Chat | `purge_incognito`, store channel | landed | Sec, reviewed by its desk; cloud models still see what you send. |
| GAP-24 inline charts, diagrams | Chat | `lfdesk/artifacts/charts.py` | landed | A live model turn with a chart fence was never run (ONE-SHELL2). Prove by running. |
| GAP-25 edit a reply | Chat | `message_edit` | landed | Keeps the old text, marks the reply edited by you, Undo. |
| GAP-26 session recap | Chat | `chat_recap` | landed | String work, no model; an Ask-the-model button uses the local model. |
| GAP-27 goal mode | Chat | `shell2gate.py`, `/goal` | landed | Auto-continue never run against a real engine. Prove by running. Sec. |
| GAP-28 end-to-end proof | Memory, Artifacts, Routines | `test_e2e_knowledge_proof.py`, selftest 13.8 | landed | Window selftest is load-sensitive; the real-window walk is Stage 3. |
| GAP-29 local subagents | Agents | `agentgate.py`, `agentloop.py` | landed | Sec; local engine only, reads run, writes held. |
| GAP-30 memory topics, sensitive switch | Memory | `lfdesk/memory/topics.py` | landed | Sensitive-topics switch is off by default and needs a confirm to turn on. |
| GAP-31 sources card, wire rag | Memory, Chat | `rag/tool.py`, `ui/sources.js` | landed | First caller of `lfdesk/rag`; keyword search, loopback embedder only if wired. |
| GAP-32 document and slide artifacts | Artifacts | `artifacts/docs.py` | landed | Local sandboxed render, export to one .html. |
| GAP-33 `chat_search` as a model tool | Memory | `tools/pastchats.py` | landed | Skips the open chat, trash, secret and incognito chats; unknown state reads none. |
| GAP-34 catalogue store | Library | browse UI `ui/storebrowse.js`; fetch is `StoreOff` | landed (fetch later) | Selling and fetching are the later, gated build (two-products note). Law 9: a fetch needs a door the owner arms. |
| GAP-35 skills folder, `/` invocation, authoring | Chat box | `skillgate.py`, `lfdesk/skills/` | landed (authoring later) | Invocation built; "create a skill" command is not. Small, but wait for the skills pane. |
| GAP-36 plugins as local bundles | Library | `lfdesk/plugins/` | landed | Closed by design: a remote marketplace and URL install (Law 9). |
| GAP-37 owner hooks | Settings | viewer and validator; `run()` always raises `HooksOff` | later | Sec. The runner runs owner code: needs the owner's yes and a reviewed runner. |
| GAP-38 per-folder instructions file | Code | `codexgate.py`, `NOVAHOS.md` | landed | NOVAHOS.md, then CLAUDE.md, then AGENTS.md; marks the session untrusted. |
| GAP-39 command sandbox | Code, Chat | research note, `run_bounded` timeout fix | later | Sec. Job caps, low-integrity children, network are owner decisions in ONE-LEFT1. |
| GAP-40 Diagnose | Settings | `diaggate.py`, `/doctor` | landed | Checks gates, engines, store, routines, agents and notifications. |
| GAP-41 Terminal findable, Ctrl+` | Terminal, Shell | launcher button, `pane.term.toggle` | landed (tabs later) | One terminal only: multiple tabs (Claude has them) not built; a UI and host change, later. Mockup v4 draws Terminal in the toolbar. |
| GAP-42 diff line comments | Code | `codexgate.py` | landed | Comments are sent as one message; stored beside the worktree. |
| GAP-43 local code review | Code | `codexgate.py`, `/review` | landed | Local backend only, no tools; findings can be turned into a message, never sent for you. |
| GAP-44 `edit_file` and editable Files | Code | `edit_tools.py`, Files tab | landed (chat later) | `edit_file` is not in the chat catalogue (checked, `wiring.py`). Sec: a model editing files from chat; needs the mode classifier decision (IN-04). |
| GAP-45 checkpoints, rewind | Code, Chat | gate + Code Rewind tab | landed (chat later) | No rewind picker in chat (checked: only `ui/code2.js` calls it). Esc Esc is closed by design (owner rule, Esc never opens anything). |
| GAP-46 loopback preview, launch.json | Code | `devserver.py`, `ui/preview1.js` | landed | Dev-server start is a confirm click (owner card default A). |
| GAP-47 pop-out, split | Code, Shell | Code content only | later | Chat panes do not pop out; panes system is another desk's. |
| GAP-48 model shell, per-command card | Chat | `shell_tools.py`, switch off by default | landed | Sec, behind the owner's Switches pane. |
| GAP-49 SSH to own nodes | Connections | `sshgate.py`, `ssh_tools.py` | landed | Arming leaves the PC: owner step per host. |
| GAP-50 agent routine steps, `/loop` | Routines, Agents | `agentloop.py`, `routine_loop` | landed | Local engine only; none means recorded as error, never a cloud fallback. |
| GAP-51 task view | Agents | `taskviewgate.py`, pane | landed | Anything it cannot see says unknown, never empty. |
| GAP-52 phone approval | Phone | `phoneapprove.py`, `ui/phone.js` | landed (pairing owner) | The phone pairing and LAN listener are the owner's native yes. |
| GAP-53 computer-use switch | Settings, Shell | `computer_trust.py`, Switches pane | landed | Switches sits under More; whether it moves into Settings is open (ONE-W3A). |
| GAP-54 local notifications | Agents | `toast.py`, `notifygate.py` | landed | Toast shown on screen not seen by its desk. |
| GAP-55 Settings sections | Settings | `ui/shell2.js` | landed | Usage, Projects, Routines, Remote; read-only. |
| GAP-56 high-contrast, colorblind skin | Settings | `ui/palettes.css` | landed | Contrast and colour-blind separation are computed in a test. |
| GAP-57 history folders | Chat | `chat_folders*` | landed | Folder filter not exercised in the mock. |

Counts of the table: **landed 51** (9 of them name a later slice or an owner step in the same row: GAP-06, 17, 18,
34, 35, 41, 44, 45, 52), **build now 3** (GAP-03, GAP-04, GAP-05; GAP-04 also names a later slice), **later 3**
(GAP-37, GAP-39, GAP-47), **closed by design 0** as a whole proposal (parts only: a remote plugin marketplace,
Esc Esc rewind, cloud effort). The counts are recomputed from the rows by `tests/test_one_app_gap_triage.py`.

## Proposed order (the owner approves this; it is the one owner step)

1. **Forward the dropped engine warnings** (GAP-03 and GAP-04 residue). It is a truth bug under two landed
   features and one file, `turn.py`.
2. **Register `Ctrl+Shift+E` and `Ctrl+Shift+B`** (GAP-05). The owner asked for the whole context bar and the
   keys; this closes the last two chords.
3. **Walk the landed rooms in the real window**, one recorded run per room (queue Stage 3). The 51 landed rows
   are code and tests, not proof; start with the Context bar and Chat box, which the owner asked for first.
4. **Small slices, one desk each:** session model time and lines changed (GAP-06, needs a stored per-reply time),
   effort and thinking persisted (GAP-04, an owner choice), terminal tabs (GAP-41), chat-side rewind picker
   (GAP-45), skill authoring (GAP-35), PDF and docx attach (GAP-18).
5. **Sec group, Opus with a Law 9 look:** `edit_file` in chat (GAP-44), the hooks runner (GAP-37), sandbox build
   (GAP-39), pop-out of chat panes (GAP-47).
6. **Gated, last, per the two-products note** (first MVP is the chat app; selling and the catalogue come later):
   store fetch and install (GAP-34, GAP-36 remote), the vision-model download (GAP-17), phone and SSH arming.

## Owner step

**Approve or change this order** (one card on the Router desk). Nothing else here needs him: no build above
transmits, spends or downloads.

## Doc 38 rows, landed or open

The rows follow their proposal: every CB, CH, KN, EX, CD, AG, ST row whose "Task proposal" cell names a GAP marked
landed above is landed. Rows still open after this triage: CB-08 (engine compaction never shown), CB-12 and
CB-13 (not persisted), CB-20 and CB-21 (session model time, session lines), CH-11 (PDF), CD-01 (terminal tabs),
CD-09 (chat rewind picker), CD-14 (chat panes), EX-05 (remote plugins, closed by design), EX-08 (hooks runner),
EX-15 (sandbox). The 55 rows doc 38 gave no proposal ("none") are unchanged by this triage.
