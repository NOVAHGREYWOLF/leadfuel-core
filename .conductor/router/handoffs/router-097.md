# ROUTER #97 · one-app handoff (ids and status only, 2026-10-29 PT)
Predecessor: router-096.md. #97 session: local_4faaba43-2587-4976-bf91-f01441277662 (slot run). Conductor: CONDUCTOR 054 local_6751ce61-7c3e-45f1-8470-4d404e395fa2. Code is LOCAL ONLY in private estate F:\Leadfuel, never push one-app/*. Worktrees under F:\Leadfuel\.claude\worktrees\one-app-*.

## State (re-read git before trusting)
- one-app/int3 ad992bd: all UI work (8 UR desks + security fixes ursec + int 4/5/6 fixes). Real-window selftest 138/138; full suite 2829 tests/23 suites run twice, one unexplained lfdesk/history failure in run 1 (not reproduced).
- one-app/int4 f92db0c (= int3 3fb61a2 + inst + vox, targeted tests only).
- one-app/inst 42d129b installer + node-manifest.json, Pester 40/40, never run for real. one-app/vox af96cd9 Chatterbox driver, fake-worker tests only.
- Running at write time: background agent ab7b2c9395eb30fc6 (verify 7: merge int3 into int4, explain history flake, full suite x2 + selftest under the heavy lock, no-network -WhatIf and Verify of the install, writes home-node/handoffs/ONE-INT-7.md). It dies if this session is archived: wait for its report or reopen from its handoff.
- Specs/handoffs: home-node/36-Frontier-UI-Review.md, handoffs ONE-UR*.md, ONE-SECURITY-REVIEW.md, ONE-SEC-FIX.md, ONE-INT-4/5/6.md, ONE-INST.md, ONE-VOX.md, ONE-INT-MERGE6.md.

## Owner cards: q652-q660 (manifest) and q662-q666 (UI) answered and routed. q661 moot. None open for one-app. q667-q676 are offer strategy (not mine).
## Owner steps for the install (do NOT run before verify 7 reports): admin PowerShell; `.\Install-HomeNode.ps1 -WhatIf -Audience Owner -IncludeBatchModel`, read it; run without -WhatIf, type `yes` once; `VERIFY.cmd -Audience Owner`. DaVinci is manual.
## Open / needs owners
- modes.py + permissions.py + mcp_client.py + engine/local.py edits need the owning desk's review (no named owner for modes.py).
- On-PC hub reads (search_brain, read_my_mail) still run in chat without asking.
- WebView2 sandbox and real Chatterbox/installer untested; chatterbox-tts==0.1.2 pin and mistral-small tag UNVERIFIED (no network by Law 9).
- Client tiers TIER-1/2/6/CPU-ONLY blocked until licences are read.
- Merge int3/int4 to anything shared is not planned; code stays local.
## NEXT
1. Read ONE-INT-7.md when verify 7 reports; if suites green, tell the owner the install is ready to run.
2. After the install: a desk for the checklist boxes the owner chooses (conductor decides), accessibility pass (UR-14), mic/WebView2 checks.
