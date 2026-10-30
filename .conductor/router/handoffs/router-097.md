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

## UPDATE 2026-10-30 (ids and status only)
Owner/conductor orders since: CONDUCTOR 054 (local_6751ce61-7c3e-45f1-8470-4d404e395fa2) says: finish the local install; open every independent desk in parallel; stop opening desks at weekly usage >= 88 percent (get_usage); keep 5 percent reserve; no spend, no downloads without the owner's one yes.
Desks (background agents of #97; they die if #97 is archived; each has a handoff note in its worktree, restart from it):
- verify 7 ab7b2c9395eb30fc6 : one-app/int4 (c2efd54 at last look): history flake, full suite x2, selftest, no-network install dry run; ONE-INT-7.md when done.
- docker stack 8 a16bf3ae86a615da9 : branch one-app/dock, ONE-DOCK.md.
- ollama tiers 9 aff65fccf9f192e54 : branch one-app/oll, why CPU-only, num_ctx measurements, ONE-OLL.md.
- a11y 10 a317848e2bcd87028 : branch one-app/a11y, ONE-A11Y.md.
- hub reads 11 aba36eae95a0d2578 : DONE, one-app/hub 670177d, ONE-HUB.md (hub mail/brain tools now ask in chat; review owner needed for modes.py, permissions.py, registry.py, settings.js).
- local AI worksheet 12 ae62dc336abca05f7 : MOCKUP FIRST per owner card q683 (conductor relay): publish mockup, stop, wait for approval card; then full interactive + worksheet. Nothing downloads/sends/spends.
Merge order owed when all report: dock, oll, a11y, hub into int4 (or int5), then one full suite on the result under the heavy lock.

## UPDATE 2 (2026-10-30, at the 300k cap)
- ollama tiers 9 aff65fccf9f192e54 DONE: one-app/oll 36fb989 (GPU works now; CPU-only cause = GPU discovery once at server start, 5 of 11 starts fell back; TIER-4 qwen2.5:7b fits at 24576, ceiling 31744). Cards q685 (auto-update) and q686 (CUDA_VISIBLE_DEVICES) posted for the owner.
- supervisor gpu 13 aaad4f6df94e81fdd RUNNING: one-app/sup from oll (restart-once-when-CPU detection, UNKNOWN never restarts), ONE-SUP.md.
- hub reads 11 DONE (one-app/hub 670177d). Still running: verify 7, docker 8 (a16bf3ae86a615da9), a11y 10 (a317848e2bcd87028), local AI worksheet 12 (ae62dc336abca05f7, mockup first, wait for approval card).
- This router is at the cap. SUCCESSOR PROMPT: 'You are ROUTER #100 · one-app. Invoke leadfuel-way:way and leadfuel-way:router, read .conductor/router/handoffs/router-097.md on branch claude/router-97, re-read live state (git in F:\Leadfuel one-app-* worktrees, ArtifactData on the Router desk page, get_session on the desk ids), then run the Claim steps. #97 stays open until its agents report.'

## UPDATE 3 (2026-10-30, conductor corrections)
- ROUTER NUMBER: #98 (one-interface) and #99 (leadfuel offer) are live; this project's successor is ROUTER #100 · one-app (supersedes the #98 prompt above).
- WINDOW MOCKUP CORRECTION (owner via CONDUCTOR 054): the approved mockup is the NovahOS WINDOW (the local app), NOT the Command Center look. Worksheet desk ae62dc336abca05f7 was told: search once more for the approved visual (transcripts, handoffs, Document Library artifacts, screens-int4, a11y shots); if not found build ONE labelled mockup from the approved description (home-node/32 lines 7-12, section 2, mockup 3 look) with the capability rows inside their pages; publish PRIVATE, copy to F:\Claude Sessions\Document Library\artifacts; STOP for the owner card; the interactive page and worksheet follow Command Center RULES (not look) only after approval.
- Cards posted for the owner: q685 (Ollama auto-update), q686 (CUDA_VISIBLE_DEVICES). supervisor gpu 13 aaad4f6df94e81fdd running (one-app/sup).
- Conductor will not archive #97; the successor archives #97 after its agents report.
