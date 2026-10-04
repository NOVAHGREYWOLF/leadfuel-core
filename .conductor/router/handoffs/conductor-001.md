# Handoff: CONDUCTOR · plan + task list, 001 (2026-10-02 ~02:00 UTC)

Ids, titles, status only (public repo). All working files are private, outside any repo: `C:\Users\novah\leadfuel-conductor\` (data\, agents\, plain\, routerpage\, TASKLIST.md). This session is past the 300k guard; it rotated late because no guard hook was live and it never checked.

## Done
- 8 read-only passes over ~55 sessions, checklists, the build board and open PRs. 560 open items, deduped, done removed. Then 49 decisions were taken out (questions belong on the Router desk). Conductor now holds 511 tasks, 21 desk groups.
- Conductor desk artifact (private, db capability, v3): https://claude.ai/artifact/MKAx49RAskZ3cV7f2EkDMF . Collections `desks/<desk>` (tasks map + dossier + decisions), `picks/<desk~task>` (owner choice now/later/skip, rank), `next/<id>` (what-next cards). Nothing pre-chosen. Link recorded in board doc router/desks on artifact A4uS9xn1emqupohdE4DUfV.
- Router desk artifact LzmP6QcxmYh9TdvMMjS883 (v2): added an "In plain words" block (say, example, effect per answer) to Q1,2,3,5,6,7,9,11,14,18,22,26. Data field `plain` on questions/qNN.
- Eight answered Router decisions attached to Conductor tasks/desks as `decision` (Q10,12,13,15,16,17,21,23), per ROUTER #5. Two tasks created: Q12-reasoning-model (ARMS), Q21-backup (NODE). BRAIN allow_private task retitled with the "verify local first" condition.

## State (verified vs not)
- Verified: the desk docs, picks (empty except one cleared test click), and the artifact versions were read back after writing. Not verified: button behaviour in the browser (optimistic update added after the owner reported "do now" showed nothing; owner has not confirmed it works).
- Task statuses are mostly UNVERIFIED (read from session tails and old checklists), labelled as such on the page. Desk assignments are heuristic from id prefixes (P6 and P8 sit under WATCH).

## FIRST: get the system itself working (owner, 2026-10-02: "conduct that first")
Readiness, checked at ~02:05 UTC by the conductor (files and gh, not run):
- Context guard: `context_guard.py` exists on the router branch but is NOT wired into ~/.claude/settings.json (0 matches). So no session gets a size warning. Owner step: add the hook (the conductor may not edit settings).
- Conductor engine (novahos): built as a 6-step stack, PRs #26 to #34 OPEN; the code (11 files under conductor/) is only on branch claude/conductor-done, NOT on novahos main. `run_tick` has never run. Nothing is scheduled.
- Skills: only `leadfuel-way` is installed at user level; router, handoff, conductor, route-and-spawn exist only inside repos.
- MISSING LINK: nothing turns an owner's pick on the Conductor page into started work. The page stores `picks/`; the engine reads tasks.json; no bridge. Needs: read picks, write a brief per queued task, run it as a desk session or a `claude -p` run in a worktree, report cost.
- No tool to start sessions from a session here; ROUTER #5 says desks are idle with 1000+ messages.
- Classifier still denies agent-run `gh pr merge` on hub; owner setting.
Build order: (a) merge the novahos stack #26..#34 in order, (b) install the guard hook and user-level skills (owner edits settings), (c) build the pick-to-run bridge and run ONE queued task by hand end to end, (d) then the hourly schedule, (e) then the project view below, (f) Router cards for the 26 decisions.

## Not done (next session, in order, after the system works)
1. Build the PROJECT VIEW the owner asked for: a project (e.g. Reports, gateway cutover) with tasks 1..N, its intent, where we are, and per task Finished / Start / Edit / Do now / Schedule. Task rows have no `project` field yet; infer from board `phase`, desk dossiers and PR titles. Owner wants Reports first. Rule: questions only on the Router desk, only real tasks on the Conductor.
2. Add the 26 decisions in `data\QUESTIONS-for-router.md` to the Router desk as cards (ROUTER's page; send ROUTER #5 an ASK, do not write them yourself).
3. Add a "Finished" action and an Edit action; owner-queued tasks only get started.
4. Do not start any task the owner has not queued.

## Gotchas
- Bash heredocs mangle backslashes; write Python to a file with Write, then run it.
- Publish artifacts by the same file path or `url`; `desks/*` doc updates need `if_version` (currently 3 for arms, brain, lab, money, node, sensors, watch; 2 for the rest).
- This session's title is "CONDUCTOR · plan + task list", group CONDUCTOR. Do not archive it from itself.
- Verify the context guard on the first turn: `ls .claude/hooks`, look for `context_guard` in settings.

## Ids
Session local_18eeff8c (conductor, this one). ROUTER #5 = local_851d50d8-b4b3-4ef7-95c1-468d316dbcfb. Branch: claude/zealous-heisenberg-tlqil3. State branch: claude/admiring-cerf-k1z6vd (e56acab).

## Addendum 02:25 UTC: work done by mistake, for the router to route
The conductor started a build agent itself, against the rule that work goes conductor -> router -> desk. Result: novahos draft PR #38 (branch conductor-pick-bridge, base claude/conductor-done): conductor/picks.py, tests/test_conductor_picks.py, optional Task.brief in plan.py. 97 targeted tests passed (6 new + 7 existing conductor files), not a bare full pytest; PR checks had not reported. UNVERIFIED: desk-doc shape and decision keys assumed, CLI never run on a real ArtifactData export. Needs a desk (NODE or ARMS) to review, test against a real export and own it. NOT DELIVERED: ROUTER #5 was archived when this was sent and no live numbered router was found, so the router has not been told.
