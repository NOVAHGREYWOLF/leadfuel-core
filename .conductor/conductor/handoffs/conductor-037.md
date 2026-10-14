# Running note: CONDUCTOR · system build, 037 (LOCAL SLOT RUN), started 23:51Z UTC 10-13

Not a rotation yet: this is the state as of ~00:0xZ UTC 10-14 so a crash or a successor can pick up. It is overwritten at rotation. Ids only (public repo).

Session local_08f4350d-d9ad-4521-83cd-384c13405693, branch claude/conductor-037 (cut from claude/conductor-036 @ 1ce6ebf), worktree .claude/worktrees/conductor-037. Launched with NO paste by conductor 036 (local_9190119c) through launch slot way-slot-02 (scheduledTaskId way-slot-02, claude-sonnet-5-5 at xhigh, bypassPermissions, read back with get_session). A slot run cannot be filed in a sidebar group (group null), so move_sessions was NOT called. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (doc router/current, v547 after my write; my keys: conductor, conductor_note_037, for_router_52_from_conductor_037).

## Done (verified by me unless marked)
- Read conductor-036.md from claude/conductor-036 @ 1ce6ebf (git show on the fetched ref), re-read live state instead of trusting it.
- Cards q400 = B (answered 23:46:49Z) and q401 = A (23:45:43Z) read on the cards; no card from q397 up is unanswered. Recorded them from the card answers as picks: INTELLIGENCE~ASK-PHONE-PATH-LOCAL-ONLY-GAP rank 262 and NODE~STANDING-ENVELOPES-DECISION rank 263 (design only, nothing granted, scope C not chosen). Picks, both desk docs, dash b-tiles (v44) and a-head (v44) written in one pinned batch and deep-compared after: MATCH. e-owner and f-system NOT patched, NOT re-read.
- Board keys written and deep-compared: MATCH. ROUTER #52 (local_5ffaaee7) briefed by session id, delivered.
- Touch ledger run by me: 268 touches in 98 sessions; UTC days 59 / 84 / 125.
- Tick re-created: cron 3f3429af at 13,43 with the daily touch-ledger step (session-only, expires after 7 days).
- Archived predecessor 036 (local_9190119c) through the gate: ls-remote == worktree HEAD (1ce6ebf), clean, nothing unpushed, no stashes; get_session reads isArchived true. Its worktree .claude/worktrees/conductor-036 is still on disk (archive leaves it).

## State (re-read before acting)
Hub main 9beed18a (13:56:31Z). 9 open hub PRs (gh, repo NOVAHGREYWOLF/novahub): 823 (surface/add-panels, new draft) 818 790 778 756 737 710 704 592. ROUTER #52 live (board claim_52, session_id on router/current; the board key `router` still names #51: stale, the router's to fix). Picks queued 267 (derived, never recounted).

## Next
1. On each tick: new owner queue click or answered card means record it, brief the live router by session id, only for an owner-queued pick. Never queue.
2. Daily: owner_touch_ledger.py --days 3 (F:\Claude Sessions\handoff\NODE-full-system-automation-part-1\), update the touch tile, UNKNOWN never 0.
3. Watch for ROUTER #52's reply on q400 (is B an owner-queued pick?) and for a desk opened for either pick.

## Owed / not delivered
Owner: q399 step (six slots to Bypass; this slot is in Bypass), queue clicks (GOAL-WEEKLY-NUDGE, APOLLO-LOOK, RW-1..3), about 70 unqueued, rule 4 paste, plugin 0.1.10. Report to 036 about the archive: 036 is archived, so a message to it has no reader; the board key conductor_note_037 is the record.

## Rotation rule relayed by 036 after it was archived (a peer relay, partly verified)
036 (local_9190119c) sent, after its archive: every successor (conductor, router, desk) is started by the outgoing session through a launch slot with no paste (leadfuel-way:launch, docs/SLOT-LAUNCH.md, leadfuel-core PR 41); paste only when no slot is free or a slot is not in Bypass, and say why; check first that no successor is already live. VERIFIED by me: the launch brief I was started with carries the owner's 2026-10-13 rule 'when a session needs to create a new session this should be automated'. NOT verified: the other quoted owner words ('start the router successor the same way', 'do this everytime'); a transcript search finds the first only inside 036's own transcript and the second nowhere. Following the rule costs nothing (it is the path I was launched by), so at rotation I use a slot and say so; a slot not in Bypass means paste fallback.

## Gotchas
ArtifactData update deep-merges nested objects; arrays need a whole-field write. Build JSON patches with pwsh scripts or the Write tool, never Bash heredocs. Picks done-flip: done true, rank null, note appended. The query tool with `where` and `out_dir` returns only the matches (use it instead of list). gh repo NOVAHGREYWOLF/novahub. Pick counts 265/267 are derived, never recounted. Git here: PowerShell only.
