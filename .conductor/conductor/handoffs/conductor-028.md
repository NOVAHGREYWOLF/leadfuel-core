# Handoff: CONDUCTOR · system build, 028 (LOCAL) -> 029, ~23:2xZ UTC 10-12, ~300k tokens

Ids only (public repo). This session: local_83483fa2-1ed0-4076-87bf-6e6be1930857, branch claude/conductor-028 (worktree conductor-028; this session's cwd is the primary checkout, so read and write this file through the worktree path). Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current, router/log39). My tick cron 87e67a89 is DELETED at rotation: 029 re-creates it at minutes 13,43.

## Done (verified by me)
- Titled, filed in CONDUCTOR, archived conductor 027 (local_7058d9c7) through the gate (handoff 7efec4e = ls-remote, worktree clean, 0 ahead).
- Status tab (collection dash: a-head, b-tiles, e-owner, f-system, new g-memory) current at 16:21 PDT / 23:21 UTC. The old "Hub drafts in flight = 0" tile counted the routers' logs, not gh; it is now "Hub PRs open" (15 by gh at 22:36Z).
- Filed UNQUEUED on the Conductor desk (none picked by me): ARMS~MCP-APPROVE-PERSON-ONLY-MESSAGE (desks/arms), INTELLIGENCE~TIERED-MEMORY-PHASE0-PROMPT-SITES, ~PHASE1-PACKS, ~SPECS-DOCS-PR (desks/intelligence), VAULT~CREDENTIALS-MS-SIGNIN-ENTRY, VAULT~ADMIN-CUSTOMER-SEPARATION (desks/vault), SURFACE~ONE-INTERFACE-TALK-THROUGH (desks/surface; rests on the owner's direct words in ROUTER #38's chat, card q369 = C). Earlier from 027: VAULT~NODE-CREDENTIAL-DESIGN, NODE~LOCAL-FIRST-CROSSOVER.
- Board: router/current `conductor` key points at 028; `for_41_from_conductor_028` and `for_41_from_conductor_028b` are the briefs for ROUTER #41 (talk-through is its first item).
- Verified by me: hub#814 merged 21:11:42Z (14cf097f = hub main); step 2 mock page ToawzsXxbYLX5ANXNdMH2H exists and its published file holds the character sheet features, no fetch calls; branch tiered-memory-phase1 f90a3cd3 on the hub remote; hub#803 merged 10-11 21:16:08Z.

## State (re-read before acting)
- Hub main 14cf097f (ls-remote 23:21Z). hub#815 (VAULT q371 A, approve person-only) is an OPEN DRAFT, head 9d5c3a0f, test.yml run on that SHA success; the VAULT desk (local_0510ec9a, ROUTER #39's child) merges on green. When it merges: verify with gh and git, then the Status line in f-system "The two approval switches".
- ROUTER #39 local_11693482 is past its cap, status rotating; successor ROUTER #41 (one-interface) has worktree router-41 on claude/router-41 @ 76f8241e but NO session is live (paste prompt is with the owner). #39 stays open until #41 claims. ROUTER #38 local_fed56153 (owed questions) is over its cap but the owner keeps talking to it; successor worktree router-40-owed-questions (claude/router-40 @ 2f933c5), no #40 session live.
- Agent a96e68336a251ccf2 (character sheet) hit its cap and published; its report goes to #39.
- Cursors: Router desk cards answered through q369 (n>377: none yet); 28 unanswered by my arithmetic (4 recent: q374, q375, q376, q377; 24 from 10-02 to 10-04, some stale, q238 closed by a router). log39 read through e12 (v12). router/current v451. picks decided_at > 2026-10-12T20:29:00Z: none new. Router timestamps on cards run a few minutes ahead of this PC's clock.
- Children: none.

## Next
1. Re-create the tick. Each tick: new log39 entries -> verify merges with git/gh -> done flags; refresh Status lines whose facts changed.
2. When ROUTER #41 is live, SendMessage it the pointer to for_41_from_conductor_028 and 028b (the owner's talk-through is its first item). Not yet done: it does not exist.
3. When hub#815 merges, set the done flag and refresh f-system.

## Arrived AFTER the handoff was pushed (not acted on by 028; 029 does these)
From ROUTER #38 (local_fed56153), delivery not confirmed, NOT verified by 028: the owner answered card q374 = A in #38's chat (~23:4xZ per #38; verify with list_events or search_session_transcripts on local_fed56153; his words as #38 gave them: "i would say we should do A fix it now and also A should be with the local too"). q374 replaces his q372 C. A = a NEW dedicated secret, held by no other app, for the approval-link signature (today the hub service token signs it, one link covers every pending action for 7 days, no sign-in); each link approves ONE item ONCE; links already in his inbox die at the deploy. #38 asks, and the order is 029's call:
1. File the build as a VAULT task on the Conductor desk (DOORS for the routes, PRIVACY review). Whether his "fix it now" counts as his queue word is your call; I never queue, and the precedent in the SURFACE talk-through task was to file it, say it rests on his direct words, and brief the router. Check card q374 on the Router desk first (answer and routed note).
2. Add to VAULT~NODE-CREDENTIAL-DESIGN and NODE~LOCAL-FIRST-CROSSOVER the owner's rule that the LOCAL twin uses the same design: its own dedicated secret per node, one-item single-use approval links.
3. Brief ROUTER #41 on the board (router/current, a new for_41_from_conductor_029 key): no one-interface router is live to open the VAULT desk. His own step when the desk asks: he creates the secret value and sets it in Railway under the name the desk gives; nobody else sets it.
I told #38 once that 029 will do this (one send).

## Owed (owner)
Paste ROUTER #41's prompt (talk-through of the command screen waits on it); cards q374, q375, q376 (may the system infer politics, religion, health, sexuality, finance, ethnicity), q377 (eight design defaults) and the 24 older ones (ROUTER #38 is walking him through them); a real test sign-in from an unlinked work account (q367 A: he says he added the Azure claims, unverified); queue or drop the nine unqueued tasks; archive conductor 026 (claude.ai); ROUTER #33 and #35; rule 4 paste; plugin 0.1.10.

## Gotchas
- ArtifactData: always use out_dir. To add a desk task, write {"tasks": <whole map>} from a file_path, pinned to the version read; compare the existing entries before writing (I did, 0 changed). Status docs are replaced by update with file_path (arrays replaced whole).
- Git Bash mangles `rev:path`: run git show from PowerShell. Prefix session ids do not resolve; use full ids.
- Messages to routers report "queued/delivered", never "read". I used 4 sends since the owner last typed in this session; the cap is 10.
