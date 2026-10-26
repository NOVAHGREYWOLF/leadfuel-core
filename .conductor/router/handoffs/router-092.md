# ROUTER #92 · one-app handoff (ids and status only)
Source: owner via CONDUCTOR 053 (local_6fc9e01a-601e-4c47-bb30-815437069049) 2026-10-26: all groups queued, as many desks in parallel as fit, models by route.py, nothing pushed, code local only. Plan: home-node/26-One-App.md sections 8-9 (private estate repo F:\Leadfuel, commit 91aa2a0). Plan files: .conductor/projects/one-app/ (this branch).
Group: home node. Report to the conductor named on the board (currently local_6fc9e01a).

DONE (branches in F:\Leadfuel, local only): a (ONE-0..3), b (ONE-13 doors), c (ONE-4, ONE-23), d (ONE-24 tiers), e (ONE-5, ONE-15), f (ONE-14), g7 (ONE-7), g8 (ONE-8 NODE half), g17 (ONE-17), g18 (ONE-18), g19 (ONE-19), g21 (ONE-21), g22 (ONE-22), g24 (ONE-24 NODE), g25 (ONE-25), h (ONE-6), i (ONE-8 LAB re-copy), j (ONE-9), lab10 (ONE-10). Branch prefix one-app/.
Integration branch one-app/int (worktree .claude/worktrees/one-app-int) held a..j at 2f5a662. RUNNING: background agent a9ef3edc769beea88 merging g7..lab10 into it and running all suites (dies if this session is archived or rotated: wait for its report, then run the next step).
EXTERNAL: novahub draft PR #1012 (doors destinations), not merged, CI owed. LAB patch for F:\video\ai at branch lab/gpu-lease (not applied).

NEXT: (1) read the integration report; fix merge-caused failures. (2) ONE-11 installer + ONE-12 acceptance (NODE, after int is green). (3) ONE-16 web search and ONE-20 messaging gateways wait on PR 1012 reaching the hub and the owner naming messaging platforms. (4) NODE follow-ups noted by desks: mount the GPU lease route, register store tools/new tools in the live registry and mode table, UI button to clear the untrusted taint, wire Archive/Character panes into the window, 27-Permission-Modes.md terminal note.
Owner items already sent to the conductor: messaging platforms, Hermes real-profile browser, edge-tts Law 9, EGRESS_* values for PR 1012, Hermes drops list, landing path (local only for now), Ollama Startup aside, LM Studio settings, token rotation.
LIVE CONFIG: ONE-6 edited F:\novah\services.json (backup F:\novah\services.json.pre-ONE-6.bak; revert = copy back).
Rules: desks Sonnet by route.py (Opus for door/security); no desk edits live config without backup and telling the router; no service entry points on live ports.

## Owner answers 2026-10-26 (relayed by CONDUCTOR 053, local_6fc9e01a)
- No messaging platforms for now: ONE-20 stays PARKED, no bot credentials.
- EGRESS_* values for novahub PR #1012 stay UNSET (everything off).
- Hermes DROP? rows stay NEEDS-OWNER-WORD, none dropped (confirmed again after the retraction below).
- ONE-16 web search may proceed once PR #1012 lands.
- Standing: Hermes real-profile browser use must be explicit opt-in per use; edge-tts behind a Law 9 gate, off by default (queued as a NODE desk after the integration report).
- lab/gpu-lease stays with LAB (not applied to F:\video\ai).

## Hermes drops: RETRACTED 2026-10-26 (CONDUCTOR 053 relaying the owner: nothing is dropped without asking him)
An earlier version of this section said every DROP? row was approved. That was RETRACTED. Every DROP? row in 28-Hermes-Capability-Inventory.md (branch one-app/g25) stays NEEDS-OWNER-WORD. Mark nothing DECIDED. Policy: carry everything instead of dropping; the conductor puts the rows to the owner as questions. Anything that transmits stays off until he opts in per provider through the out door.

## Integration result (agent a9ef3edc769beea88 reported, its word, not re-run by me)
one-app/int head c34bb0a (worktree F:\Leadfuel\.claude\worktrees\one-app-int): g7 g8 g17 g19 g21 g22 g24 g25 lab10 merged, no conflicts; full offline run 18/18 suites OK, 1847 tests. gates.sh not run (repo has none). NO background agent is running now, so rotation is clean.
SUCCESSOR OPENS NEXT (all based on one-app/int @ c34bb0a, NODE, Sonnet unless route.py says otherwise):
 1. follow-up desk: Hermes real-profile browser opt-in per use; edge-tts behind a Law 9 gate (off by default); register new tools (store tools, browser, computer, todo/clarify) in the live registry and mode table; UI button to clear the untrusted taint; mount the GPU lease route (proposed 127.0.0.1:8766, unconfirmed); wire Archive and Character panes into the window.
 2. ONE-11 one installer/one icon (node.iss ships panes, migration checklist per old program, Startup entries consolidated; retires nothing, D5), after 1.
 3. ONE-12 acceptance script per program (unknown never green), last.
 4. ONE-16 web search after novahub PR #1012 lands; ONE-20 parked.

## Hermes cards answered 2026-10-26 (CONDUCTOR 053 relaying the owner)
KEEP (carry, nothing dropped; items that transmit are built but gated and OFF): self-improvement q627 (curator and background review as owner-approved suggestion lists, never unattended writes); transmitting items q629; remote/platform surfaces q630; window furniture and plugin marketplace q632; research/housekeeping extras q633.
ROW BY ROW, HOLD those rows until answered: cloud model plumbing q628 and agent loops/risk modes q631; row cards q634-q641 are posted. Successor: do not build or drop those rows until the cards show an answer.
Consequence for ONE-25 follow-ups: the successor turns the KEEP rows of 28-Hermes-Capability-Inventory.md (branch one-app/g25) into NODE port tasks (gated, off by default); the DROP? rows are not dropped.

## Hermes row cards answered 2026-10-26 (owner's own answers, read by CONDUCTOR 053 from the Router desk DB; not re-read by me)
KEEP: q634 caching/fast mode/effort/fallbacks/credential pools; q635 providers/auth/OAuth/billing; q636 connectors/managed gateway; q637 /moa; q638 /goals; q639 smart approval (never able to lift the delete or egress floors).
DROP (his word): q640 yolo mode; q641 kanban dashboard/gantt/graph plugins (the same data shows in a pane the app already has).
Anything that transmits or spends stays gated and OFF until he approves. This supersedes the HOLD above: Hermes drops are now fully decided by him (only q640 and q641 are dropped; everything else is carried).

## Loose end
Branch one-app/f (ONE-14 LM Studio fold-in, d467d63, based on one-app/e) is NOT in one-app/int @ c34bb0a: merge it before ONE-11. It needs owner steps: LM Studio downloadsFolder points into Ollama's blob store; its Run-key login entry; retiring LM Studio or the stray manifest file is his call.
