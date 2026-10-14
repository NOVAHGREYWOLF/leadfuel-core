# Handoff: CONDUCTOR · system build, 038 (SLOT RUN way-slot-03) -> 039, ~02:2xZ UTC 10-14, context guard at 300k

Ids only (public repo). Session local_1dc1a95a-b6e6-44c8-be91-33b66f7bffa5, branch claude/conductor-038 (cut from claude/conductor-037 @ 2bdca6b). 037 was archived by 038 through the gate. Tick: cron 17a67e3c at :13/:43 is SESSION-ONLY and dies with this session: the successor must re-create it (CronCreate, daily touch-ledger step: python -I owner_touch_ledger.py --days 3 in F:\Claude Sessions\handoff\NODE-full-system-automation-part-1; UNKNOWN never 0; tile is dash/b-tiles on the Conductor desk, replace the whole items array pinned to the version). Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (board key conductor, v557 text, names 038; the successor must update it). Live router: ROUTER #54 local_2afda8d8 (way-slot-04; router/current v559 names it). A slot run cannot be filed in a sidebar group, cannot call run_scheduled_task, and cannot launch its own successor: a REGULAR session must start 039 (NODE~SLOT-LAUNCHER-SESSION, rank 264, not built yet), so 039 is a paste prompt for the owner.

## Rules I worked by (from the owner)
Pick recorded ONLY from an owner-answered card, or his own chat/page click, noted 'recorded from the card, not a page click' or 'from the owner chat'. Never queue on my own. Flip done only on a merged PR read with gh. Law 9 / spend / sends / deploy-config / credentials / flag flips stay the owner's alone.

## Done (verified by me unless marked)
- Picks 265 (q411 A), 266-276 (the owner's #52 chat message 01:24:49Z, plumbing), 277 (q412 B scope design), 278-282 (q414 A wave 1), 283 (q449 B, S1 canary scanner), 284-285 (q451 A), 286-303 (the owner's chat 02:19Z: 'i want to finish as much of the command with my allowance and everything that we have written about it and get that fully operational ...'; includes new task SURFACE~COMMAND-COMPLETION-PLAN, DECIDE-IN-PLACE, HELD-ASK-NOTES, GUESSES-TO-CHECK-SCREEN, ASK-MODEL-PICKER, ASK-LOCAL-MODEL, the ten Oracle tasks, STUDIO-GENERATE-PREREQS, WORLD-FLAG-ON-PREREQS). 264 is 037's (NODE~SLOT-LAUNCHER-SESSION; its decided_at stamp 01:35Z may be ahead of the real clock, unverified).
- Filed UNQUEUED, by me: NODE~ENVELOPES-SESSION-EGRESS-HOOK-FEASIBILITY (touches the owner's settings file).
- Router #54 was briefed (delivered) that the /command program is what the allowance is for and that its q447 pace hold should fall on the other work first. Pace is the router's call; I did not verify its usage arithmetic.

## State to re-read
Hub main 0985656e (02:14Z, gh). Open cards: q452 (override pace per task), q415-q435 are ROUTER #50's. Not queued by me and why: ORACLE tasks are in; GOAL-WEEKLY-NUDGE-IN-SYSTEM (sends), VAULT~APPROVAL-LINK-REVIEW-FOLLOWUPS (waits on hub#818, a draft), DOORS~SPEND-GATE-ACCOUNT-CAP-FAILOPEN (a real gate defect, not command), the CAND/OWED/unverified entries.

## Next
1. Re-create the tick. Re-read cards (query with where and out_dir, never list). Record picks only from answers.
2. Watch ROUTER #54's pace and the /command order; answer router briefs sent to the conductor session id.
3. Update board key conductor with 039's session id; archive 038 only after 039 is live and this note is pushed.

## Gotchas
No move_sessions; generic SendMessage refused, use mcp__ccd_session_mgmt__send_message; PowerShell for git; ArtifactData update deep-merges objects but REPLACES arrays; pin every write; picks doc ids use ~ (files use @); decided_at must come from the clock (Get-Date UTC), not a guess.
