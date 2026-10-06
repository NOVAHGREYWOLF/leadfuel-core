# LOCAL BOOTSTRAP: move the LeadFuel router, conductor and desks from cloud to the owner's computer

Written by cloud router #2, 2026-10-01 ~23:20 UTC. Public repo: ids, titles, status, PR numbers only. No secrets.
Read this first, then `.conductor/router/handoffs/router-002-to-local.md` and `.conductor/router/ACCESS.md`.

## 0. Why local, and the one rule
Cloud sessions cannot reach Railway (no login), routines have no connectors, child-to-router messages stall on a permission prompt, and the owner is blocked all day.
Locally the owner is already logged in to Railway, gh and git, and can see every folder. The code-building automation we built today has a LOCAL mode. Use it.
Rules that still hold: never merge or deploy outside the merge gate below, never delete ANTHROPIC_API_KEY until the owner says so for that step, no force-push, no secrets in chat or in this public repo, never bulk mark-done sessions, models per `route-and-spawn` (Sonnet default).

## 1. Folders on the owner's PC (verified from remote URLs)
Real clones: `F:\Leadfuel\repos\<name>` for novahub, signal (=novahound), scope (=icp), reach (=novaherald), orbit (=novahawk), lucid, echo, odyssey, novahub-mcp, apollo-enricher, instagram-outreach, howlclip, NovahPrime. Folders named `.wt-*` are old worktrees: do not use.
Missing, clone them: leadfuel-core and novahos into `F:\Leadfuel\repos`.
Old notes and the owner's earlier desk system: `F:\Leadfuel` (PROGRESS.md, CLAUDE.md) and `F:\Claude Sessions` (desks, WORK_QUEUE.md, SESSION_MAP.md, STANDING_AUTHORITY.md). Read only when needed. `F:\Claude Sessions\CREDENTIALS.md` is a credentials file: never open it, never run sessions in that folder.

## 2. What we built today (all of it applies locally)
| Piece | Where | Local use |
|---|---|---|
| Router skill (message protocol, rotation, rules) | leadfuel-core branch `claude/zealous-heisenberg-tlqil3`: `.claude/skills/router/SKILL.md` | The desktop-app session the owner talks to. Rotation by handoff note, not by create_session. |
| Context guard hook (soft 300k, hard 450k) | same branch: `.claude/hooks/context_guard.py` + `.claude/settings.json` | Works locally unchanged. Copy to user level (step 3). |
| Handoff skill | same branch and novahos `.claude/skills/handoff` | Same. |
| Child protocol, access inventory, handoffs | `.conductor/router/` on that branch | Local children report by their final message; the router reads it. No send_message needed. |
| Conductor kit (plan, tick, report, board, local runner, cloud runner) | novahos branch `claude/conductor-done` (docs PRs #34 #35 #36 #37) | Use the LOCAL runner: `conductor/runner.py run_tick(repo)` runs `claude -p --model X --max-turns N` in a git worktree per task, records cost and tokens in tasks.json, never pushes, never archives. First real run is untested: verify the JSON shape. |
| conductor, route-and-spawn skills | novahos `.claude/skills/conductor`, `route-and-spawn` | Copy to user level (step 3). |
| Plan and state (project.json, tasks.json, board.md, report.md) | leadfuel-core branch `claude/admiring-cerf-k1z6vd` (leadfuel-core PR #7) | Check out as a worktree (step 3). Commit state updates there only. |
| Task briefs (141 tasks) | Private "LeadFuel Build Board" Claude artifact `A4uS9xn1emqupohdE4DUfV`, collection `tasks`, templates `TEMPLATE-child-brief` and `TEMPLATE-babysit-brief`, rules `RULE-session-budget`, `RULE-session-size` | Read with the Artifact tool in a logged-in local session, or ask the owner to export it. |
| Desks (lanes) | Tag/title scheme: `lane:<DESK> role:<r> task:<id> model:<m>`, title `<DESK> · topic`. Lanes: ROUTER, SENSORS, DOORS, INTELLIGENCE, ARMS, NODE, SURFACE, LAB, MONEY, VAULT, SUITE, ROUNDTRIP, COMMS, FIELD, PRIVACY, PRODUCT, WATCH, MARKET, BRAIN, WEBSITES | Locally a desk = a named folder/session group. The owner's existing desks are in `F:\Claude Sessions\desks`: map lanes onto them, do not duplicate. |
| Policy | guard 300k/450k, reuse idle session under 200k, Haiku under 150k, budget soft 5M / hard 8M, max 8 parallel | Same numbers. |
| Merge gate (owner, 2026-10-01) | state-branch handoff | Merge a task's PR only when all checks on its current head are green, it is mergeable and ready (undraft first). Never merge production cutover steps or PRs touching secrets. |

## 3. Local setup (PowerShell, in order)
```
cd F:\Leadfuel\repos
git clone https://github.com/NOVAHGREYWOLF/leadfuel-core
git clone https://github.com/NOVAHGREYWOLF/novahos
cd leadfuel-core; git fetch origin; git checkout claude/zealous-heisenberg-tlqil3
git worktree add ..\leadfuel-state origin/claude/admiring-cerf-k1z6vd
cd ..\novahos; git fetch origin; git checkout claude/conductor-done
railway whoami; gh auth status; python --version; claude --version
# user-level skills and guard so every local session has them
mkdir $HOME\.claude\skills -Force
Copy-Item ..\leadfuel-core\.claude\skills\router,..\leadfuel-core\.claude\skills\handoff -Destination $HOME\.claude\skills -Recurse -Force
Copy-Item .claude\skills\conductor,.claude\skills\route-and-spawn -Destination $HOME\.claude\skills -Recurse -Force
```
Then merge `..\leadfuel-core\.claude\settings.json` hook block and the SESSION_SOFT_TOKENS/SESSION_HARD_TOKENS env into `$HOME\.claude\settings.json` (keep existing entries; copy `context_guard.py` next to it and fix the path).
Tick check (read-only): `cd ..\leadfuel-state; $env:PYTHONPATH="F:\Leadfuel\repos\novahos"; python -m conductor.cloud --dir .conductor report`.
Start tasks locally: in a Python shell with the same PYTHONPATH, `from conductor.runner import run_tick; run_tick("F:/Leadfuel/repos/leadfuel-state", max_parallel=3)`. Worktrees land in `.conductor/worktrees/<id>`. The runner builds one prompt per task from tasks.json; paste the board brief into the task first if the task needs more than its title.
Hourly automation: the cloud routine is dead (no connectors). Either start a tick by hand, or add a Windows Task Scheduler job that runs the tick command hourly. Do this only after one manual tick works.

## 4. Cloud inventory at hand-off (verified 23:00Z)
- Merged today: novahub #697, leadfuel-core PR #2 (reports plan). Already merged earlier: scope#21, reach#31, lucid#124.
- Open, not merged: novahub #692 (P5-F4), #694, #696 (CI red or draft); novahos #25 (draft), #35 (CND-2 size policy), #36, #37 (green drafts); orbit #25, #27, #28; reach #28 (G4); scope #11 stack (#12 #13; CI red in 3s earlier, billing suspected); signal #13 (CI red: ruff, check_writing, pip-audit) and #28; leadfuel-core PR #7 (state branch).
- Cloud sessions: all finished or idle, none running. Task sessions P6/P7/P8/CND-1/G4/G5/G6 produced drafts or runbooks; the 25 older idle sessions are over 100k tokens and cannot take new work: start fresh local tasks instead. Archive nothing without the owner (old coordinators 01V9wYwN and 01PHuaca stay as is).
- Routines, all unusable until connectors are added: hourly tick `trig_015prRzaktsxeYJLiD7x8G9B` (paused), heartbeat `trig_01DiwJhuwjtyDx4TyH4v6Fxa`, nightly `trig_01U9CpzgkUWKbLeymJ46qmuA`, 4-hourly novahos tick `trig_01SXmjamu3JKRDbFyVvvHtGN` (paused, owner OK to retire). Leave them off.

## 5. Work to finish, and how (status from the board)
Method for every task: take its brief from the board, run it as a local `claude -p` task in a worktree of the right repo, open a DRAFT PR, run the repo's tests and CI, apply the merge gate. One task, one worktree, one PR.
- **MONEY (gateway cutover), owner-assisted, first.** Order from signal#28's runbook: (1) merge and deploy novahub #456, confirm `POST /llm/v1/messages` is not 404; (2) mint signal's gateway token per novahub `docs/LLM_GATEWAY.md`; (3) `railway variable set` LLM_GATEWAY_URL=https://leadfuel.cloud/llm and LLM_GATEWAY_TOKEN on the novahound service (check `railway list`, `railway link` first); (4) fix signal#13 CI, merge #13 then #28, deploy; (5) NOVAHOUND_USE_APOLLO=0; (6) only on the owner's word, delete ANTHROPIC_API_KEY. Same pattern for reach (G4/G7, reach#28, docs/GATEWAY_CUTOVER.md) and scope (G5, merge #13 into #12, #12 into #11, then #11). Then G8 (verify each service's variables), G9 (3 token table mismatches), G10 (verify every service is on the newest commit). Tasks: G1-followup-coresettings, G4-followup-models, G4, G5, G6, G7, G8, G9, G10.
- **INTELLIGENCE (Reports).** P5-F4 (novahub #692: fix CI/undraft, merge), P5-F5 (briefings show 'late': 20s pull timeout), P6 Scope+Core builders, P7 Estate weekly and P8 DMARC digest (marked blocked; cloud did not establish why: read their tasks and drafts first), then P9 (attach every report as a PDF) after P6-P8 are done, then P10 (end-to-end check, deploy by owner). Reports plan: `docs/REPORTS_PLAN.md` (merged). Report document: new doc daily titled `conductor_report YYYY-MM-DD`.
- **ROUTER/conductor.** CND-1 (conductor fixes, review), CND-2 (novahos #35 stacked on #34), novahos #36 and #37 (green drafts: owner reviews). Retire the cloud-only parts of the plan once local runs.
- **Names (N-series).** N1-F1 doing, N1-F2-orbit-png-pdf (orbit#25; the Windows re-render is the owner's), N6 (orbit#27), N2 (Railway/DNS plan, owner on PC), N3-F1, N3-F2, N4, N9, N10, N11, N12.
- **DOORS (outbound).** D1 to D7 (route sends through the door, request_uid dedupe, CI check).
- **Health and risk.** R1 (four red tests on main), R2 to R6, R9 (blocked, novahub #667), R10-F1-approval-followup (novahub #684), R10-F3, R10-F4, R12-F1-verify-tzfpy-prod, R12b, R13-F1, R13-F3, R14-about-owner-model-check, R16-F2, R16-F3. Y9, Y11, Y5 are blocked; Y12 and H1 need the owner at the PC (see the board). M1 to M3 model choice.
- **Owner decisions on record.** Never bulk mark-done. New daily report doc. Leave old coordinators. Do not unarchive PRIVACY/NODE. Hold on Sonnet/Haiku lifted (confirm with the owner). Merge gate above. Remaining owner asks: merge queue order, the Railway steps, novahos #35/#36/#37 review, orbit#28 Windows script.

## 6. First 30 minutes locally
1. Run section 3. 2. `railway whoami` and `gh auth status` pass. 3. Run the read-only tick. 4. Report to the owner in five lines: what you verified, the first three tasks you will start (suggest G-series first, then P5-F4, then R1), and what you need from the owner. 5. Start them.
