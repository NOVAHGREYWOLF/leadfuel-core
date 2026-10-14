# Handoff: CONDUCTOR · system build, 037 (SLOT RUN way-slot-02) -> 038, ~00:3xZ UTC 10-14, context past 300k

Ids only (public repo). Session local_08f4350d-d9ad-4521-83cd-384c13405693, branch claude/conductor-037 (cut from claude/conductor-036 @ 1ce6ebf), worktree .claude/worktrees/conductor-037. Pages: Conductor desk MKAx49RAskZ3cV7f2EkDMF, Router desk LzmP6QcxmYh9TdvMMjS883, Build Board A4uS9xn1emqupohdE4DUfV (router/current v553; my keys conductor, conductor_note_037 to 037e).

## Done (verified by me unless marked)
- Archived 036 through the gate. Recorded owner card answers as picks, not page clicks: q401 A (rank 262), q400 B (rank 263, design only).
- Flipped done on merged hub PRs read with gh: ADD-PANELS (#823), ASK-PHONE-PATH (#824, e73033ae).
- Filed UNQUEUED: SURFACE~ONE-INTERFACE-PANELS-DECIDE-IN-PLACE, SURFACE~ONE-INTERFACE-PANELS-LEVELS-WRITE-CALLS, SUITE~SCOPE-CORE-REPORTS-MIDNIGHT-FLAKE, INTELLIGENCE~ASK-CALLERS-LOCAL-ONLY-GAP-2. Dash a-head and b-tiles deep-compared through v49 and v48.

## State (re-read before acting)
Hub main e73033ae (00:23Z); its push run 38489886023 was in progress, NOT read. 8 open hub PRs. Cards unanswered at 00:19Z: q411 and q402 to q410. ROUTER #52 (local_5ffaaee7) wrote handoff_52 and stays open until ROUTER #53 claims (a paste prompt for the owner), so session_id on router/current is still #52.

## Next
1. Re-create the tick at 13,43 with the daily touch step: python -I on F:\Claude Sessions\handoff\NODE-full-system-automation-part-1\owner_touch_ledger.py --days 3 (last run 23:5xZ 10-13: 268 in 98 sessions; UNKNOWN never 0).
2. Re-read the cards. A q411 answer of A becomes a pick for ASK-CALLERS-LOCAL-ONLY-GAP-2; brief the live router by session id. Flip done only on merged PRs read with gh. Never queue.

## Owed
Owner: q411, q402 to q410, queue clicks (the unqueued tasks above, GOAL-WEEKLY-NUDGE, APOLLO-LOOK, RW-1..3), hub#756 merge word, APPROVAL_LINK_SECRET, plugin 0.1.11. Report to 036 went undelivered (archived).

## Gotchas
Slot run: no move_sessions; generic SendMessage is refused, use mcp__ccd_session_mgmt__send_message; PowerShell for git. No backticks in double-quoted pwsh strings (they become control characters). ArtifactData update deep-merges; query with where and out_dir, never list. Pin every write; the board moved once between my read and write. Successors start by launch slot with no paste (docs/SLOT-LAUNCH.md).
