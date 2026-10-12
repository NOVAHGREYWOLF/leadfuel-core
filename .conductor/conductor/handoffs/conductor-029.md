# Handoff: CONDUCTOR · system build, 029 (LOCAL), interim note ~23:5xZ UTC 10-12

Ids only (public repo). This session: local_aac451eb-b644-4f2e-8cd9-0347a89be81c, branch claude/conductor-029 (worktree conductor-029, cut from claude/conductor-028 @ 3d8616a). Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current, router/log41 once #41 writes it; log39 is #39's, closed at e12). Tick cron f8484b39 (13,43 * * * *) is session-only: it dies with this session, so the next conductor re-creates it.

## How 029 started (read this first)
The owner opened 029 with the cloud conductor 026's START-HERE.md (OneDrive folder "Conductor handoff 2026-10-12"). That file is STALE: it was written ~19:50Z for a "027" and asks for the docs page, the level mock and the q369 relay. By 23:37Z conductors 027 and 028 had both run. 029 therefore followed 028's note, not START-HERE, and checked each START-HERE item against live state instead of redoing it:
- Docs page HSSytRjXnG7y73i3Jbg8JF and level mock ToawzsXxbYLX5ANXNdMH2H (with the character sheet) exist, built by ROUTER #39's agents; the owner read both and answered in #39's chat (log39 e05, e08). Not re-rendered by 029.
- q369 was answered C (talk it through), not B; q373 landed (hub#814, 14cf097f); the three done flags (DOORS~D1-OWNER-READS-CLOCK-FLAKE, VAULT~KELVIN-SIGN-EMAIL, WATCH~Q354-NIGHTLY-FULL-RUN) are set, read by 029 on the picks; hub#811 451b6fae and hub#813 c53a4b1f are ancestors of hub main (gh compare, 029). The nightly-run PASS is 027's reading of the Task Scheduler result and log; 029 did not re-read the log.
- The Questions page CLYHwR59LM4SGxn5XjVket has no saved answers (answers collection empty, read by 029): nothing to relay.

## Done (verified by me)
- Titled, filed in CONDUCTOR. Archived conductor 028 (local_83483fa2) through the gate: handoff 3d8616a = ls-remote, worktree clean, 0 ahead, idle.
- q374 = A (owner in ROUTER #38's chat: "fix it now", same for the local twin; found by transcript search, context not read): filed VAULT~APPROVAL-LINK-HARDENING UNQUEUED (desks/vault v20), added the local-twin rule to VAULT~NODE-CREDENTIAL-DESIGN (v20) and NODE~LOCAL-FIRST-CROSSOVER (desks/node v63). Unchanged tasks compared before writing: 0 changed.
- Board: router/current v453, keys `conductor` (now 029) and `for_41_from_conductor_029` (brief for ROUTER #41). SendMessage to ROUTER #41 (local_c17aaac6) queued, not confirmed read; to ROUTER #38 (local_fed56153) undelivered (idle). The board key carries the same facts.
- Status tab (collection dash) a-head v28, e-owner v28, f-system v18 current at 16:44 PDT / 23:44 UTC.

## State (re-read before acting)
- Hub main 14cf097f. hub#815 (VAULT q371 A, approve is person-only) is an open draft, head 9d5c3a0f, CLEAN (gh, 029); the VAULT part 3 desk (local_0510ec9a, idle) merges on green. When it merges: verify with gh and git, then the line "The two approval switches" in dash f-system.
- ROUTER #41 local_c17aaac6 claimed at 23:41Z (router/current claim_41). ROUTER #40 local_c4f9af1e (owed questions) is live. ROUTER #38 and #39 are idle past their caps. SURFACE one-interface part 13 (local_4a06afda) is the q369 talk-through (router's word; the session exists and runs).
- Unanswered Router desk cards: 27 (q375, q376, q377 recent; 24 older), counted by 029 from all 377 cards at ~23:43Z.
- Children: none.

## Next
1. Re-create the tick (minutes 13,43). Each tick: new log41 entries and `for_conductor_029` keys -> verify merges with git/gh -> done flags; refresh Status lines whose facts changed.
2. When ROUTER #41 acts on VAULT~APPROVAL-LINK-HARDENING (it may ask for a one-line card), keep the Status line "Approval links get their own secret" current.
3. When hub#815 merges, set the line in f-system and check the follow-ups ROUTER #39 named: MCP approve error (ARMS~MCP-APPROVE-PERSON-ONLY-MESSAGE) and the CONNECTOR_APPROVE_ENABLED deploy-config cleanup (owner card from the router).

## Owed (owner)
Cards q375, q376, q377 and the 24 older (ROUTER #40 walks him through them); queue or drop the ten unqueued tasks; real test sign-in from an unlinked work account (q367 A); archive conductor 026 on claude.ai (the PC cannot reach it); archive ROUTER #33 and #35; rule 4 paste; plugin 0.1.10; delete or refresh the stale START-HERE.md in the OneDrive handoff folder.

## Gotchas
- ArtifactData: always use out_dir. To change a desk task, write {"tasks": <whole map>} from a file_path pinned to the version read; compare the unchanged entries first.
- Git Bash mangles `rev:path`: run git show from PowerShell. `git worktree add ... origin/<branch>` sets a wrong upstream: `git branch --unset-upstream`.
- Messages report "queued/delivered", never "read". 029 used 2 sends since the owner last typed here; the cap is 10.

## Arrived after the first push (029 acted)
- ~23:50Z: NODE · claude audit part · 2 (local_41191020-50f2-43bc-b64d-b3d88be9dcdf) sent the owner's three-levels decision (project = corpus, workstream = goal and sidebar group, desk = one task). 029 read the pushed handoff NODE-claude-audit-001.md on claude/claude-audit @ 16728fa6 (= ls-remote) and a transcript hit in part 2; the owner's raw message (said in the archived part 1, local_6f61aa7c) was NOT read. Filed NODE~WAY-WORKSTREAM-WORDING UNQUEUED (desks/node v64). 029 keeps its own title and the current wording until the owner queues it. The Conductor desk 'Projects' tab change belongs to the session that owns that page (local_18eeff8c), not to the conductor.
