# Handoff: cloud router #2 -> LOCAL session (2026-10-01, ~23:00 UTC)

Owner decision: stop running in the cloud, run everything locally (Claude Code on the owner's computer, Railway CLI already logged in there). Cloud sessions are finished or idle; nothing in them is running. Ids/PR numbers only (public repo).

## Why local
Cloud sessions have no Railway login and routines have no connectors. See .conductor/router/ACCESS.md.

## Cloud results (verified by get_session at 23:00Z)
- MERGE-1 (session_0183yt7c...): novahub #697 MERGED. #692, #694, #696 NOT merged (CI red or still draft). Asks: undraft and/or wait for CI.
- MERGE-2 (session_01T4YnuY...): novahos#25 still a draft (not merged); orbit#28 not touched (add_repo denied in that session).
- MERGE-3 (session_01MzXHJS...): signal#13 CI RED (ruff, check_writing, pip-audit, ~2s); #28 green but stacked. NOT merged on purpose: runbook says deploy novahub #456 and set gateway vars first.
- MERGE-4 (session_01Ybjjia...): scope#21, reach#31, lucid#124 were ALREADY merged (2026-09-30), CI green.
- leadfuel-core PR #2 (reports plan): MERGED (4fb234c) by owner's word.
- Tick (session_01Qampsd...): 7 tasks reported, all drafts/runbooks, nothing merged; P9 blocked on merges; P6 CI unchecked.
- CND-2: draft novahos PR #35 (size policy), tests pass. Docs PR novahos#36 and code PR #37 are green drafts for the owner.
- Hourly tick trig_015prRzaktsxeYJLiD7x8G9B is PAUSED (routines have no connectors). Heartbeat trig_01DiwJhuwjtyDx4TyH4v6Fxa and nightly trig_01U9CpzgkUWKbLeymJ46qmuA: same problem. Do not rely on them.

## Owner decisions on record
Never bulk mark-done. Old coordinators (01V9wYwN, 01PHuaca): leave for now. Do not unarchive PRIVACY/NODE. Report doc: new doc daily `conductor_report YYYY-MM-DD`. Models: Sonnet/Haiku hold reported lifted (owner told another session); confirm with the owner.

## Railway cutover (owner runs, order matters; from signal#28 runbook)
1 merge+deploy novahub #456, check POST /llm/v1/messages not 404. 2 mint signal gateway token (docs/LLM_GATEWAY.md). 3 on novahound set LLM_GATEWAY_URL=https://leadfuel.cloud/llm and LLM_GATEWAY_TOKEN. 4 merge signal#13 (fix red CI) then #28, deploy. 5 NOVAHOUND_USE_APOLLO=0. 6 only then delete ANTHROPIC_API_KEY. Scope/reach: own token per service, delete key last. Do not delete ANTHROPIC_API_KEY until the owner says.

## Open owner items
Merge queue: novahub #692/#694/#696 (CI/draft), novahos #25 (+ commit check), #35/#36/#37, orbit#28 (+ Windows script, owner runs). Six coordinator questions: answered in this thread (see owner decisions). P7/P8 "blocked": reason not established.

## Local first steps
1 `railway whoami`. 2 read ACCESS.md. 3 check CI on the PRs above with `gh`. 4 do the cutover with the owner, stopping before the key delete.
