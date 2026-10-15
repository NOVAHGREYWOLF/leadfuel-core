# Handoff: CONDUCTOR system build, 040 -> 041 (SLOT RUN way-slot-03), 2026-10-15 ~06:5xZ UTC, guard at 300k

Session local_e4b83fc3-e814-4573-9e9c-e1c54f563c5c, branch claude/conductor-040 (from claude/conductor-039 @ bec41e2). 039 (local_98f2c433) archived by 040 through the gate. A duplicate idle run of slot 03 (local_bc9fbea8) archived. Tick cron ed33a1b8 at :13/:43 is SESSION-ONLY and dies with me: the successor re-creates it (prompt = re-read Router desk cards answered after the cursor, picks, board, daily touch ledger tile; same text as 039's note).

## Rules I worked by
A pick is recorded only from an owner-answered card ("recorded from the card, not a page click") or the owner's chat ("from the owner chat", read verbatim in the router's transcript via list_events). Never queue on my own. Flip done only on a merged PR read with gh (repos: novahub, orbit, scope, reach, signal, odyssey, echo under NOVAHGREYWOLF). Answers are not stretched: q468/q469 queued the check, not six fixes; q472 later did.

## State (re-read before acting)
- Live router: ROUTER #61 local_b6d7c10c-3f79-4e71-8178-03dbf7991826 (board router/current v572, slot way-slot-01). Board key `conductor` names 040 (v568); the successor must update it.
- Card cursor: last answered_at seen 2026-10-15T04:40:39Z (q473 A). Open owner cards: q474 (look at the one-skin mock, then queue real-board build), q475 (mail_manager/self_capture parse-but-fails path to cloud; if A, file a build task and record the pick). Desks: Conductor MKAx49RAskZ3cV7f2EkDMF (collections desks/<lane>, picks/<DESK~KEY>, dash/b-tiles), Router LzmP6QcxmYh9TdvMMjS883.
- Picks recorded 305-326, all done (merged, read with gh) EXCEPT: 314 SURFACE~COMMAND-ONE-GAME-GAP (ends in a doc; left open), 315 SURFACE~COMMAND-PLAY-ROOM-AUDIT (agent ran; no merged PR, unflipped), 317 ARMS cookie check (findings file; left open), 319 DOORS~RUNNER-REQUIRE-APPROVAL-PRODUCTION-CHECK (production read; needs the owner in the desk's own chat), 308 SURFACE~ONE-INTERFACE-SHELL-PARITY, 312 VAULT~ADMIN-CUSTOMER-SEPARATION-BUILD, 307 VAULT design (not reported merged), 305 NODE launch-by-fireat (landed core#48 on way/plugin, not main).
- Filed UNQUEUED (owner picks): DOORS: WORLD-FEEDS-BEFORE-ANY-SWITCH, DOORS-GATE-TILE-CACHE, DOORS-ADMIN-OBSERVABILITY-OPEN-QUESTIONS-PANEL, DOORS-TEST-WALL-PROFILE-ROUTE-LEVEL-CONTROL, LOCAL-FAIL-F5/-DEEP-PASS (a decision)/-TEST-GAP-P5, DOORS-OSS... (done); INTELLIGENCE: WORLD-ROWS-SELF-FOLLOWUPS; ARMS: ODYSSEY-IMPERSONATION-AUDIT-ROWS-CLEANUP, REACH-BARE-ADMIN-CID..., ORBIT-TEAM-PATHS..., SCOPE-INVITE-FLASH..., REACH-TEST-GUARD-DNS-LOOKUPS; COUNSEL-PRIVACY-PAGE-IMPERSONATION-CLAIM; PRIVACY-NAME-OPENERS-READING-PACK, PRIVACY-HUB844-FOLLOWUPS; SURFACE: ONE-SKIN-REAL-BOARD (card him to see the mock first), ECHO-MODAL-LOCAL-MODEL-UNAVAILABLE; NODE: NODE-HUB-PINS-GATE-FAILS-ON-PC, NODE-LEFTOVER-WORKTREE-AUDIT; plus 039's list.
- Touch ledger: last full day 10-14 = 30 (tile value updated at dash/b-tiles v52); 10-15 = 12 at 06:xxZ. The 72 h window sheds old days, so older counts shrink between runs.

## Next
1. Re-create the tick. 2. Query cards answered after 04:40:39Z (expect q474, q475). 3. Update board key conductor. 4. Archive 040 only via the owner or the successor (a slot run never archives itself).

## Owed / owner
Owner action noted by the arm reads: after deploy, an admin still holding the old impersonation cookie hits orbit /viewas/exit once. Install plugin 0.1.14 (way/plugin, not main); set way-slot-07 and auto-created slots to Bypass. Lanes on filed tasks are guesses, settled at queue time.

## Gotchas
No move_sessions in a slot run. ArtifactData update deep-merges objects, replaces arrays; pin writes. A router at 10 sends cannot message: answer via cards. Date from `date -u` fails in PowerShell; use Bash.
