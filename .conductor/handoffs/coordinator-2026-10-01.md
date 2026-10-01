# Handoff: conductor coordinator, 2026-10-01 (predecessor session_01BRArxH6fbwuHsz6KhxYsDh, stopped at ~245k tokens, over the 150k cap)

Read `.conductor/report.md` and `board.md` first. Do ONE status pass per tick, then stop. Check your own
`external_metadata.context_usage.used_tokens` via get_session at the start; at 90k write a handoff and spawn a successor.

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
P5-F4 (novahub#692) is `pr`: CI green, waiting for the owner to mark ready and merge.
P9 waits on P6+P7+P8 `done` (pinned sonnet). P10 waits on P9 merged and deployed by the owner.

## How to tick (until CND-1 merges)
Run from this repo root with `PYTHONPATH=<novahos clone at branch claude/conductor-done>`. `get_session` is wrapped in `ccr` and tokens/cost sit
under `external_metadata` (context_usage.used_tokens, usage.cost_usd), so write a flat file
`{id, status_bucket, context_usage:{used_tokens}, usage:{cost_usd}}` and feed it to `python3 -m conductor.cloud status <task> <file>`.
A 0 token reading from a running session is stale; ignore it. Use `plan --max-parallel 8` (tick counts pr/review as in flight).
Child prompts are NOT built by `plan` alone: briefs live on the private build board and are appended by hand (CND-1 fixes this).

## Rules
No merge, no deploy. No archive without the owner's yes (auto_archive is off). Sonnet/Haiku only until the weekly limit resets 2026-10-03 21:00 UTC.
On merge of a task's PR: `mark-done <task> --pr N`. Commit .conductor/ to claude/admiring-cerf-k1z6vd (leadfuel-core PR #7, state branch, public repo: no private details).

## Owner-only (do not do)
Merge novahub#692; archive OKs (P5-F2 session, stray #683 merge session, coordinator sessions); the six open questions in the board handoff;
close leadfuel-core#2; gateway steps G7-G10 (Railway/PC); rotate the hub database password (board Y12).
