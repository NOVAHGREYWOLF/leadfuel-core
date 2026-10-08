# Router handoff #031 -> #032 (2026-10-08 ~03:20Z UTC, at the 300k guard)

ROUTER #31 is local_5890b893-c0c8-45a9-b0a1-39e87580f339 ("ROUTER #31 · one-interface", ROUTER group). Ids only. Re-read live state before acting.
Board router/current (A4uS9xn1emqupohdE4DUfV) v326+: keys log_31*, agent_reports_31* (a to e), agents_31e, owed_31c, tool_note_31 supersede this note. Router desk LzmP6QcxmYh9TdvMMjS883. Conductor desk MKAx49RAskZ3cV7f2EkDMF; live conductor 021 local_1ff6c57b.

## Done by #31
Claimed v313. Plugin 0.1.9 installed (q347 = A; I read installed_plugins.json: 0.1.9, da1488ac). Hub main verified by gh and ls-remote at each step: #738 -> 01d6e6d1, #796 -> 15f55e4b, #797 -> 24403f83 (I landed #797 myself under ci-novahub). DOORS re-checks clean: command-home flag (15f55e4b) and S4 layers (7f5540f6); reports in F:/Claude Sessions/handoff/ (...-command-home-recheck.md, ...-s4-layers-recheck.md). Cards posted: q348 (retention, default A), q349 (COMMAND_HOME production flip, default A, owner's own Railway step). #30 archive was REFUSED by the app (live work); gate otherwise met.

## Running (die if #31 is archived: #31 STAYS OPEN until it reports)
- a5f9520058448354c SUITE PLACES-GATE-LAND (Sonnet, my agent; SendMessage it by agent id). Lands the gates.sh places stanza plus two docs/THE_PLACES.md lines. Waits on heavy slot-1 (pid 3840, orphan serial pytest of the landed S4 branch, since 01:45:29Z) and ci-novahub (free now).

## Next
1. On its report: verify PR state and merged sha with gh and ls-remote, copy to agent_reports_32*.
2. Archive #30 (local_7ae54716) when the app allows, else ask the owner to archive it from the sidebar. Then archive #31 only after a5f9520058448354c has reported and #32 is live.
3. q349 answered B: only record it, the owner sets the variable. Cards open: q348, q349, q208, q294.
4. Older routers #11 #13 #14 #18 #21 #22 #24 #25 #26 still open: gate each, one at a time.

## Owed
Conductor 021 was told (delivered) about #797, q349, DOORS N11 (spend gate runs with no cap when an account cap is unreadable), F1-F3, N9, N10: NOT queued, do not start. Ask the owner before stopping the orphan pytest (pid 3840). Sends since owner typed: 7 of 10.

## Gotchas
Agent isolation:worktree failed twice ("git could not be resolved"): start read-only agents without it. An agent can be messaged only by the session that started it. Agents share one scratchpad: give each its own subfolder. After a cd, use git -C.
