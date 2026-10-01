# Handoff: conductor coordinator, 2026-10-01 (predecessor session_01BRArxH6fbwuHsz6KhxYsDh, stopped at ~245k tokens, over the 150k cap)

Read `.conductor/report.md` and `board.md` first. Do ONE status pass per tick, then stop. Check your own
`external_metadata.context_usage.used_tokens` via get_session at the start; at 200k write a handoff and spawn a successor (owner raised session sizes 2026-10-01: guard soft 300k, hard 450k, reuse under 200k, budget soft 5M / hard 8M).

## Running (all Sonnet, draft PRs only, tracked in tasks.json)
| task | session | repo | expected output |
|---|---|---|---|
| P6 Scope+Core builders | session_01UmpNPpyBBhJ3AaWbXr1BKZ | novahub | draft PR |
| P7 Estate weekly | session_013Z7qK6SXAW9BqJZXFfWdn9 | novahub | draft PR |
| P8 DMARC digest | session_014H6eSc9uEDH6SiGfaVVidc | novahub | draft PR |
| CND-1 conductor fixes | session_01DzL21KWPysGdrEsyy3TQ28 | novahos (base claude/conductor-done) | draft PR stacked on #32 |
| G4-followup-models | session_01LN9oNYiQiMJPRLGipHDHcL | reach | draft PR |
| G5 scope gateway PR check | session_018RmgeA3SD8vyYRgLpVAQgD | scope | updates to scope#11 stack or a note |
| G6 signal gateway | session_011bRcro9wS5dVuaiVxnNkX2 | signal | draft PR |
P5-F4 (novahub#692) is `pr`: CI green, waiting to be marked ready and merged by the tick (merge gate).
P9 waits on P6+P7+P8 `done` (pinned sonnet). P10 waits on P9 merged and deployed by the owner.

## How to tick (until CND-1 merges)
Run from this repo root with `PYTHONPATH=<novahos clone at branch claude/conductor-done>`. `get_session` is wrapped in `ccr` and tokens/cost sit
under `external_metadata` (context_usage.used_tokens, usage.cost_usd), so write a flat file
`{id, status_bucket, context_usage:{used_tokens}, usage:{cost_usd}}` and feed it to `python3 -m conductor.cloud status <task> <file>`.
A 0 token reading from a running session is stale; ignore it. Use `plan --max-parallel 8` (tick counts pr/review as in flight).
Child prompts are NOT built by `plan` alone: briefs live on the private build board and are appended by hand (CND-1 fixes this).

## Rules
No deploy. MERGING IS AUTOMATED (owner, 2026-10-01): merge a task's PR once all checks on its current head are green, it is mergeable and ready for review (undraft first); production cutover steps and PRs touching secrets or deploy config get a look first. No archive without the owner's yes (auto_archive is off). Models: follow route-and-spawn (Sonnet default, Opus for critical/door envelopes, high or xhigh effort, security/auth/migration/architecture, Haiku for small mechanical work). The Sonnet/Haiku-only hold was LIFTED by the owner on 2026-10-01.
On merge of a task's PR: `mark-done <task> --pr N`. Commit .conductor/ to claude/admiring-cerf-k1z6vd (leadfuel-core PR #7, state branch, public repo: no private details).

## Owner-only (do not do)
archive OKs (P5-F2 session, stray #683 merge session, coordinator sessions); the six open questions in the board handoff;
close leadfuel-core#2; gateway steps G7-G10 (Railway/PC); rotate the hub database password (board Y12).

## Archive gate (owner rule, 2026-10-01; auto_archive is now ON for this project)
A session is archived only when ALL hold: (1) its PR is merged; (2) its last message explicitly says DONE; (3) it left a handoff or a final
done report. `mark-done` is the gate: run it only when all three hold, because auto_archive then archives every task marked `done`.
Idle sessions outside the plan (not archived yet, owner said they must first say DONE and leave a handoff or final report):
- session_01AqEe6LghcvzuWQHGmvaSFs (P5-F2): says #691 merged, but board task still `pr` and an owner decision open. Not an explicit DONE.
- session_01XLr7jXSgaGwbgTbfoXtNd4 (stray #683 merge): final merge report exists, no explicit DONE (#683 itself is merged).
- session_013KaA5oWtyQXtWULYd32wx7 (old Reports coordinator): waiting on the owner's six questions. Not done.
First tick: send_message each one: "If your work is complete reply DONE plus a five-line final report; otherwise say what remains."
When a reply satisfies the gate, list it as ready-to-archive in your report for the owner's yes. Do not archive these yourself.

## Routine and verification
Hourly routine trig_015prRzaktsxeYJLiD7x8G9B (minute :36, fresh session each fire, first fire 22:36 UTC). It stores NO connectors.
UNVERIFIED: that a fired session has add_repo / create_session / get_session. At the first tick after 22:36 UTC, find the session it started
(list_sessions) and confirm it ran a pass; if it could not, tell the owner (fix is in the claude.ai routines UI).
The predecessor's own check-in trigger (trig_01181qvrG12rNQZsPBZfcss7) is deleted.
