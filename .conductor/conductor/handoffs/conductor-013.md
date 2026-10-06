# Handoff: CONDUCTOR · system build, 013 (2026-10-06, rotating at ~280k)

Ids only (public repo). This session: local_f999aa65, branch claude/conductor-013. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current names the live router in `session_id`). The 30-min tick cron is DELETED; re-create it at minutes 13,43 (prompt: re-read cards answered since the last tick, new picks, the live router from router/current, hub tests runs; file only owner answers that create new work as picks; brief the router only when something is new; never answer cards, merge, deploy, spend or archive).

## Done (verified by me)
- Archived 012 local_6247b62d through the gate.
- Corrected 012's "crash loop": the hub runners are ephemeral (F:/novah/ci/NOTES.md line 3), so restart counts prove nothing. The real fault: no runner took a job 16:52-18:28Z on 10-05. Told ROUTER #20; q277 reworded; #20 opened NODE CI-RUNNER-STALL local_b44c4f26.
- Filed UNQUEUED: SURFACE TUFTE-G7-SKIN-TOKENS, ARMS ICP-SLUG-RATIFY.
- Owner QUEUED, both HELD under close-first: NODE AUTO-DESKS (pick rank 204) and SURFACE PHOTO-CLIENT-STORE (rank 205). Briefed ROUTER #21 (delivered); both are in router/current (`auto_desks`, `photo_client_store`).

## State (trust; re-read)
- Live router: ROUTER #22 local_09dd8448, claimed 01:36Z 10-06. #20 and #21 are still open (chip side sessions, successor archive).
- start_session / hand_off_to_session absent from this session's tools (checked 10-06).
- Hub CI 02:42Z: no stall. Train merge-train/20261006T015000Z tests failed 02:21Z (the train's concern).
- Keep #11, #12, #13 and conductor 005 local_083bdfe0.

## Next
Re-create the tick. If the owner calls AUTO-DESKS a close-first exception, tell the live router.

## Owed
- Owner: is AUTO-DESKS a close-first exception? Asked in chat 00:59Z, unanswered.

## Gotchas
- gh can hang on the slow link (timed out ~02:28Z): wrap it in `timeout`.
- Desk JSON: get with out_dir, edit in python (utf-8, ensure_ascii=False), set with if_version.
- list_sessions limit 200 overflows to a file: parse it with python.
