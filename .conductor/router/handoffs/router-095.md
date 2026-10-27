# ROUTER #95 · one-app handoff (ids and status only)
Source: owner orders typed in ROUTER #95 chat 2026-10-26, relayed context from CONDUCTOR 053 (local_6fc9e01a-601e-4c47-bb30-815437069049). Predecessor note: router-092.md (branch claude/router-92-bc180e). Router #95 session: local_b4cc90b7-dbe0-462e-8e54-4351e6cde5b4 (a way-slot run; stays open until its background agents finish, then the launcher archives it).
Repo for the code: private estate F:\Leadfuel (NOT this public repo). Code is LOCAL ONLY: never push one-app/* branches. Branch prefix one-app/. Integration branch one-app/int, worktree F:\Leadfuel\.claude\worktrees\one-app-int. Shared brief for desks: scratchpad file ONE-APP-brief-common.md (path in #95's scratchpad; recreate from this note if lost). Tests: from home-node/app `python run_tests.py --python F:\Leadfuel\home-node\build\venv-assistant\Scripts\python.exe`.

## Merged in one-app/int @ 3cef60f (local)
FU-A, FU-B, RESTART, BRAIN, 11+12 (g11), SIGNIN, BRAND (NovahOS, no logo asset exists), VOICE, COMPUTER, CLARIFY, PARITY (doc 31), UI0, F1 (gate seam), NAV spec (doc 32), CONNECT spec (doc 33). Last full run on int before UI0/F1: 19/19 suites OK.

## DONE on own branch, NOT yet merged into int (merge in this order via ONE integration desk; resolve index.html/gate_list.py/mockbridge.js by keeping both sides; run full suite once at the end; investigate one unexplained lfdesk/history/tests failure seen by ONE-L)
f2 (panes+NovahNav), m (terminal/files/System), b2 (chat store; live history.db has all 99 chats archived, owner decision pending), l (status strip), k (settings + shortcuts), nav12 (Home+Search). Requests carried: chunk A to call NovahNav.merge(true) at boot and retarget selftest rail asserts, expose window.NovahChat {open,start}; NovahNav needs list()/show().

## RUNNING background agents (die if #95 is archived; wait for them) / branches
a2 (chat UI, only desk allowed in ui/app.js), e2 (Archive pane), cd2 (Character Design embed), c2 (permission UI, Opus), d (Models pane + downloads gated off, Opus), code (Code surface, Opus), cn26 (connectors registry+bridge, Opus), cn7 (connectors UI), cn1 (EGRESS passthrough in run_local_hub.py, Opus).
STOPPED by user, uncommitted work in F:\Leadfuel\.claude\worktrees\one-app-g1: g1 (voice UX). Ask the owner whether to resume.

## NEXT wave (not opened)
H engine wiring (wiring.py, turn.py; owns registering new tools), I Routines/tasks, J memory+skills, N file-edit/shell tools, N2 execute-code, O attach+vision, Artifacts (NAV-5/6), Customize (NAV-8/9), CN3 OAuth, CN4 CLI connect, CN5 downloads/quarantine, DOORS: CN0 hub destinations + CN8 disarm (after hub PR 1012 merges), S installer+acceptance LAST (spec/iss rows for every new file). Also: acceptance prime.voice_interpreter row wording; GpuYield call-site broker wiring; ui0 rail/sidebar merge.

## OWNER (relayed answers)
Skip history imports. Claude-style surfaces wanted (Home/Code/Search/Artifacts/Routines/Customize/Settings). Connectors first: Microsoft 365, Google, Railway, GitHub, brain, Slack; outbound polling only; own OAuth client ids; Brave key as credential ref; he runs installs; Signal not now. Embed Character Design. Decompress OCR yes. Prime HUD yes. Shell + computer use wanted (computer use stays off until he sets LFDESK_ALLOW_COMPUTER=1 and LFDESK_COMPUTER_BACKEND=windows). Pane named System. LM Studio retired: router edited its settings (downloadsFolder -> .lmstudio\models, Run key removed, backup settings.json.pre-novahos.bak).
Owner steps still his: review/merge hub PR NOVAHGREYWOLF/novahub#1012 (draft, pytest SUCCESS on 9dba539f) then move HUB_COMMIT (CN1 prepares it) and restart (Restart-OneApp.ps1); set EGRESS_* himself; voice interpreter (venv-voice or LEADFUEL_VOICE_PYTHON); token rotation; Ollama run key check. Brain proof GREEN (--auth, owner ran it). ONE-16 waits for #1012 in the hub; ONE-20 parked.
Reporting: STATUS to the conductor via mcp__ccd_session_mgmt__send_message (local_6fc9e01a). Do not claim router/current. Pacific time for the owner.

## Added after the note (2026-10-26 evening, owner request)
ONE-REMOTE (Opus agent, branch one-app/remote): Claude control channel for NovahOS (local MCP server 'novahos-control', off by default, scoped, audited, does not bypass gates). Spec home-node/34-Claude-Control-Spec.md. Also finished+unmerged since note: cn1, cn7, a2, e2, cd2, cn26, code (plus f2 m b2 l k nav12). Still running: c2 (permission UI), d (models), remote. Stopped: g1 (voice).
