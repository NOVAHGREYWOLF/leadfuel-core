# Handoff: CONDUCTOR system build, 045 -> 046, 2026-10-19 ~01:15Z

045 = session local_50165db9-7e6b-4bc7-a8a6-cbc69cf9c383 (slot way-slot-04), predecessor 044 local_b57528f8 (archived 10:54Z by NODE conductor relaunch part 1). Rotation requested by NODE · full system automation part · 2 (local_86c2e874-fed8-4acf-84ea-ba780c7e1038), relaying the owner's words in its chat, 2026-10-19 ~01:03Z: "restart the conductor and the router not sure what happened". Launcher: NODE · launcher part · 1 (local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7). Ids only; the repo is public.

## What happened (045 verified)
The PC rebooted 2026-10-19 ~00:03Z and the app restarted ~01:01Z (the relaying desk's reading of process start times; 045 verified only that the clock reads 10-19 01:11Z and that CronList still showed tick b13a4ed0 "next run Oct 18 6:27pm", never fired). The last tick ran 19:43Z 10-18. The session-only tick died with the reboot. ROUTER #69's background agents are reported dead (that desk's word, not verified by 045).

## Rules (kept)
A pick only from an owner-answered card or his own chat, verbatim. Verify before relaying. Production reads, secrets, his flag flips, spend or send need his typed go in the desk's own chat; route around them, do not stop. ArtifactData: get or query with out_dir only, never an unfiltered list; pin if_version.

## Owner's standing words (2026-10-18, in 045's chat)
- Pick 431 SURFACE~COMMAND-CENTER-KEEP-GOING: never stop again, keep going till it is completely done; where waiting on a card, take the plan's default and move on.
- Pick 432 SURFACE~COMMAND-CENTER-ALL-AT-ONCE: open every remaining item as desks at once, build in parallel, put the PRs in the ci-novahub queue instead of one by one. Dependencies are the router's call. Pick 421 (SURFACE~COMMAND-CENTER-END-TO-END) stands under both.

## State (re-read before acting)
- Picks recorded through rank 432 (Conductor desk MKAx49RAskZ3cV7f2EkDMF, collection picks). Next free rank 433.
- Card cursor: last read answered_at 2026-10-18T10:20Z (q572, moot). No card answered after it at the last query (19:43Z). Next free card 573 (board).
- Router: ROUTER #69 local_f021e3bf-4803-4634-9dca-5261fd4b6919 idled 19:41Z; NODE full system automation part 2 told it to rotate to ROUTER #70 via the launcher. The board router/current session_id will name the live one: read it, do not trust this line. Board conductor key still names 045 (v593): set it to your own id, pin if_version.
- Roster ROUTER #69 gave at ~19:20Z (its word): seven desks building: 5a 3D crystal, L2-2 shell, L2-3 character, L2-4 quests, L2-5 earned access, L2-7 live regions, L2-10 oracle for customers. Held to wave 2: 5b, 5c (stack on 5a), plan 6, 7, L2-6, 8, 9, 11, 12, 13, 14. L2-15 deferred (Q23). L2-1 needs his typed go.
- Hub PRs per gh at 01:11Z 10-19: #889 (5a, draft), #891 (L2-2 shell, draft), #892 (L2-3 character, WIP draft) open; #890 (L2-10 oracle) merged 19:37:19Z; #888 merged 19:10:43Z. Desks for items 4, 5, 7 had no PR at 19:43Z.
- Command Center Build page LRC41csTPNRzSk9ddbDFzj (collection tasks): b01-b04 done, b05 doing (#889), m02 doing (#891), m03 doing (#892), m10 done (#890), rest todo. Move rows only from gh state.

## Tick (session-only, re-create; 15 minutes at :07,:22,:37,:52)
Prompt: stall check first (get_session and list_events limit 6 on the live router; read Build page tasks; gh for hub PRs; if the router is idle with no command center desk or PR in flight while rows remain todo, nudge it by id that picks 421, 431, 432 queue the whole program; if the router is archived or dead ask the launcher for a router); then query Router desk LzmP6QcxmYh9TdvMMjS883 questions answered after the cursor, record picks, update Build page rows from gh only. Never queue a task of your own; no merges, deploys or spend.

## First turn for 046
1. Re-create the tick. 2. Set board router/current conductor key to your id. 3. Find the live router (board session_id, list_sessions) and confirm the build is running again; if ROUTER #70 is live, send it picks 421, 431, 432 with their true sources. 4. Query cards after the cursor. 5. Archive 045 (local_50165db9-7e6b-4bc7-a8a6-cbc69cf9c383) through the gate once you are live and this note is pushed. 6. Report to the requester of this launch, NODE · full system automation part 2 (local_86c2e874-fed8-4acf-84ea-ba780c7e1038), first line STATUS.
Write actions allowed: Board, Conductor desk and Command Center Build page database writes; commit and push of your own handoff note on your own claude/conductor-046 branch; archive_session on 045 through the gate; send_message to the router, the requester and the launcher. Nothing else leaves the machine. No merge, deploy, secret, spend, settings or permission-mode change; no archive_session on self.

## Gotchas
Slot runs cannot launch successors (ask the launcher). The Stop hook misreads a note written for a predecessor as a rotation; it fired three times at 045 and was ignored correctly then. A machine sleep or reboot kills session-only crons and jumps the clock: always check date, not the last tick's stamp.
