# NODE · novah estate part · 18 · handoff 001 (2026-11-21 about 23:15 PT, about 305k tokens)

Session local_4f93581f-f910-471e-8dc4-98bdfb644ac4, nested under part 17 (archived by me through the gate). Router: ROUTER #129 local_2a029bfa-0490-4d8a-be6d-4cfba4c09dcb is handing off to ROUTER #131; send later traffic to `router/current.session_id` on the Build Board. Conductor: 058 local_b7630866-f2e7-4436-9936-af237cbc5c34. True source of every instruction: the owner's typed messages in this session (list_events on my id). State lines are mine; re-read live state.

Desk folder (the only place written, plus the page artifact YHBPZMmcs6kZndq5HvGxqt and my own Router desk cards): session folder `handoff/NODE-novah-estate-part-13`. My checks are in `done/part17-checks.md` there.

## The owner's words in this session (in order)
1. How to make sure everything on the list starts getting done; where the full runbook is; finish it step by step.
2. He wants ONE session he works through; everything else reports to it; if a session needs him, point to it and say what it needs; desks open nested and run to done.
3. "make 129 my one session and start the work".
4. A status bar for completed items on the queued list, shown to him, the router and the conductor, plus a dashboard.
5. Make it fit a phone; can he chat with it and stay focused.
6. Can 129 and the artifact share something so we keep attacking one thing.
7. "Keep going. How long to get off railway?"

## Done by part 18
- Part 17 archived through the gate. Cards q9582-q9592 re-pointed to me; the owner's eleven answers written into GAME-DESIGN.md section 9.0 and done/K17.md. Memory saved: feedback_one_front_door_session.
- Dashboard on the estate page https://claude.ai/artifact/YHBPZMmcs6kZndq5HvGxqt (version 9, first tab): overall bar, one bar per stage 0-5, started/finished cards (phone width checked at 375 px on a local copy, no overflow, no console errors), an Ask box (`sample` capability), and a shared board.
- Shared board (`db`, rules: read view, write admin): collection `live` (doc id = queue item id; data state queued|running|blocked|done, by, at, note) and doc `focus/now` {text, by, at}. The page reads them live and they override `status.json`. Verified by me: view-level read sees the rows; an interact-level write is refused. ROUTER #129 wrote `focus/now` itself (version 2, about 22:45 PT): the router-to-page link works. Not verified: the live page rendering the rows (the browser pane is not signed in to Claude; only a local copy was rendered).
- Status build: `scripts/make_status.py` (reads QUEUE-v2.json desk_result rows and `LIVE.json`, writes `page/status.json`); page block in `scripts/dash_block.js`, spliced by `scripts/splice_dash.py`. Today: 7 done, 2 running, 1 blocked, 7 first pass, 327 not started of 344 (file counts; board rows override).
- Seeded rows (reported by 058 and ROUTER #129, not re-checked by me): done U03, U04, C10; running U02 (kept running, not done: no run seen, no run folder since 2026-11-10; flips when the 04:30 verdict exists), W05; blocked W08 (card q9598).
- Stale text fixed in START-HERE.md (344 items) and ORCHESTRATION.md (q9581 replaced q9580). Not fixed: the queue `counts` block still says 141 not checked (router said 258; 058 has since filed more). The page copy `page/orchestration.md` was edited too but NOT republished.
- Off Railway (owner asked how long): no schedule exists in `F:\novah\always-on\OFF-RAILWAY-001-plan.md`; only the cutover night (about an hour) and a 14-day hold are timed. Phase 0 data copy done and checked per part 3 (run phase0-20261122T043228Z, 710 and R620 copies); not re-run by me. Left: memory-ranking card, suite VM build, rehearsal on the tailnet, deploy path (q9530 B), his go-aheads (DNS move, tunnel, secrets), cutover, 14-day hold, deletion card. My estimate, unconfirmed, given to the owner: roughly one to three weeks to cutover.

## Owed (successor), in order
1. First turn: send your STATUS to the live router (`router/current.session_id`; #129 hands off to #131), then archive me through the gate once this note is on the remote and nothing of mine is unpushed.
2. After 03:15 PT on 2026-11-22, on overlord (ssh alias `overlord`, read only): `grep -a vzdump:103 /var/log/pve/tasks/index | tail -2` and `tail -2 /var/log/vault-sync.status`; after 04:10 PT `tail -3 /var/log/greywolf-state.status`. Record in `done/P07.md`, `done/machines-7.md` and the two items' `desk_result` in QUEUE-v2.json; then write the `live/P07` and `live/machines-7` rows on the board (state done only if the logs end OK) and republish `page/queue.json` after an Artifact read.
3. Read the board (`live`, `focus`) and `list_events` on the live router to see whether it keeps writing rows; if the page needs a republish (orchestration.md edit), do it with the status.json.
4. Keep pointing the owner at any session that needs him and say what it needs (his one-front-door rule). Open cards of mine: q9582-q9592 answered and recorded; q9592 (digital brain PDFs) unresolved.
5. Do NOT delete the six personal photos part 16 reported in its tool-results folder unless the owner types that he wants them deleted.
6. Optional: the queue `counts` block; re-verify the Ask box on the live page when a signed-in browser is available.

## Weak points
- The Ask box and the live board rendering were not seen on the live page.
- Rows on the board are other sessions' reports; the page labels them as such.
- `LIVE.json` in the desk folder and the board can disagree; the board wins on the page, the file wins in `make_status.py` output only.

## Not done
No desk opened, nothing merged, no mail sent or changed. Published: the page (versions 6 to 9), board rows, the two design-file edits.
