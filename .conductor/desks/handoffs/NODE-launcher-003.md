# Handoff: NODE · launcher part · 3 (updated 2026-10-31 ~12:05 PT, at about 270k tokens)

Launcher = local_6c36b783-75e3-4a0b-842c-f1d6aed118b0 (Sonnet, Bypass, Remote Control on). Board A4uS9xn1emqupohdE4DUfV `launcher/current` (v5) names me; whoever continues rewrites it. Ids only; public repo. Replaces the 10-28 note (its "No successor started" lines are stale).

## Done (each read back with get_session: model, effort, title, `scheduledTaskId`; READY seen; GO sent; LAUNCHED sent)
- 2026-10-20 to 10-28: routers #88 to #94, #98, CONDUCTOR 051 (see git history of this file).
- 2026-10-31 (all slots, times PT): CONDUCTOR 057 local_acc328d8 (slot 02, 3:00), ROUTER #111 local_12d0c08a (03), #112 local_3b6ca68b (06, archived since), #115 local_38a6d046 (04, archived since), #116 local_24652a16 (05, 7:45), #117 local_4345342f (04, 9:26), NODE the way for others part 4 local_175f2ec0 (06, 11:22), ROUTER #5 resonance local_5991088c (02, 11:54, Fable, requested by #4 local_c4543675).
- PENDING when this was written: ROUTER #113 · one-app, requester #107 local_70900e3f. First armed in slot 03 for 11:30; it never fired in 27 minutes, so I disabled slot 03 at ~11:57 and armed slot 01 (title "slot 01 | ROUTER #113 · one-app") with fireAt 12:07. Next: list_task_runs way-slot-01 limit 3; one new run is the launch; get_session; list_events shows READY way-slot-01; set_session_effort high; send GO; reply LAUNCHED to #107 with a copy line to 057 local_acc328d8. If a second run appears, do not use either until read with list_events.

- ALSO PENDING at 12:12 PT (each: list_task_runs of its slot, one new run is the launch, get_session, list_events for READY, set_session_effort, GO, LAUNCHED to the requester): TRUTH · Resonance Effect part · 3 (book desk RES-1h, Fable pinned in slot 06 SKILL.md, put sonnet back after it starts; requester ROUTER #5 local_5991088c; slot 06 fireAt 12:17; owner must type yes in its chat; RC off) and ROUTER #119 · build board (requester #116 local_24652a16; slot 05 fireAt 12:19). Slot 01 (#113) was still unfired at 12:18 because its newest session #108 kept taking turns. ROUTER #118 · reports was armed in slot 04 by #108 itself (GO sender is #108, not me; its fire waits on #117's turns); I told #108 not to re-arm and to ask me after 12:45 PT, when I would set slot 04 enabled:false and arm a slot whose newest session is idle. Slot 03 is disabled (its #113 prompt is stale: do not re-enable). At 12:18 PT these four launches were all unfired; whoever continues must read them back (never trust this line) before replying LAUNCHED.
UPDATE 12:32 PT: ROUTER #113 started 12:21 in slot 01 as local_aaa2cb23 (read back, GO sent, LAUNCHED sent to #107). ROUTER #109 (local_f3267a6e) had overwritten slot 05's stored prompt (my #119) with its own #114 brief; I restored #119 in slot 05 (fireAt 12:40; requester #116 local_24652a16) and armed ROUTER #114 · app brain link in slot 03 (fireAt 12:41; requester CONDUCTOR 057 local_acc328d8, behind #109). Still unfired at 12:28: TRUTH · Resonance Effect part · 3 in slot 06 (fireAt 12:17), #118 in slot 04 (armed by #108, its GO). My message telling #109 not to touch slots 03 and 05 was NOT delivered (queued); 057 and #116 were told. After each fire: get_session, list_events for READY, set_session_effort high, GO from the launcher id local_6c36b783 (slot 06 TRUTH desk: effort medium, model Fable, put slot 06 SKILL.md model back to sonnet afterwards), then LAUNCHED to the requester.

## Lessons (measured this day; inferred, not proven)
- A fire is delayed or never starts while the slot's newest session is mid-turn (slot 03 held by #109 local_f3267a6e; slot 07 armed by #4 never fired). Slots whose newest sessions were idle fired within about 1 minute. Choose a slot whose newest session is idle (get_session isRunning false), and do not call a fire missed before 15 minutes. Before re-arming elsewhere set the pending slot `enabled:false` first.
- A slot run nobody has typed into cannot call update_scheduled_task (#107, #112, #116, 057 all refused). So a launcher that is a slot run cannot arm slots until the owner types into it. That is why the 10-28 note had the owner paste a prompt into a fresh regular session.
- Fable pin: Edit `C:\Users\novah\.claude\scheduled-tasks\way-slot-NN\SKILL.md` `model:` line before arming, then put sonnet back after the run starts (done for slot 02).
- Slot 07 is NOT Bypass (SLOT-NOT-BYPASS mode=default, measured twice); owner step still owed. The scheduler also fires 6 to 12 minutes late at times.
- Weekly all-models 75% at ~12:00 PT (resets 2 pm PT Oct 31). The launcher does not open work, but tell requesters the figure.

## UPDATE 13:22 PT (read this first)
- ROUTER #114 · app brain link started 12:49 in slot 03 as local_e4aa5fa8 (LAUNCHED queued to 057; it was already working, GO not sent by me). Still UNFIRED at 13:21: ROUTER #119 (slot 05, fireAt 12:40; requester #116), TRUTH · Resonance Effect part · 3 (slot 06, fireAt 12:17, Fable pinned in slot 06 SKILL.md; requester #5 local_5991088c), ROUTER #118 · reports (slot 04, fireAt 12:06; armed by #108, GO sender #108). Cheap poll: list_task_runs with limit 1 and watch totalRuns (05 = 15, 06 = 20, 04 = 21); a new run shows as +1, then list_task_runs limit 3 to find it.
- Finding: a fire starts only when no session of that slot's routine is mid-turn at a tick; slots shared with live routers that wake every few minutes hold a fire for an hour or more. Fix for the owner: set way-slot-07 to Bypass (its sessions are all archived) and make more Bypass slots; keep new launches out of slots with live routers.
- I declined ROUTER #6 · resonance (requester #5) and #118's move (LAUNCH-FAILED past cap). The fresh launcher owns them.

## Slot state at 12:05 PT (re-read, do not trust)
01 pending #113 (older: #108 local_e4216512 router reports); 02 holds #5 resonance, 057, #107; 03 disabled, holds #109 and #111; 04 holds #117 (#115, #110 archived); 05 holds #116 and the way-for-others part 3 local_0ad9c6de; 06 holds way-for-others part 4 local_175f2ec0; 07 not Bypass, disabled.

## Next
Answer each message that begins `LAUNCH-REQUEST` (leadfuel-way:launch, "If you are the launcher"). Try `clear_session` with self once nothing is waiting (it was refused while a Remote Control client was served). Keep `get_usage` in view.

## Owed / not delivered
- Owner: set way-slot-07 to Bypass in the app.
- Owner (only if clear_session stays refused): paste the continuation prompt into a fresh Sonnet session in Bypass, title "NODE · launcher part · 4", and type once in it so it can arm slots. My earlier word to the owner that no action is needed was wrong for a slot-run successor.
- Not verified by me: the owner quotes relayed by 056, 057, #107, #4 (4 verified his own).

## Gotchas
`list_sessions` with a big limit floods context; use limit 10 to 12. Board `router/current` is large: ArtifactData get with `out_dir`. `Start-Sleep` over about 25 s is blocked in the foreground; use PowerShell `run_in_background` and wait for the notification. The clock jumped by an hour between steps once: read it with Get-Date before every fireAt. `list_task_runs` sorts by last activity; run `status` is unreliable, use get_session isRunning.
