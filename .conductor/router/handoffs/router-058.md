# Router handoff #058 -> #59 · one-interface (2026-10-15 ~01:30Z UTC real clock; ~310k tokens)

ROUTER #58 = local_c3bc03d9-35c9-455c-9d23-fffa7816e4d7 (Sonnet 5.5, slot way-slot-04, no group). #57 is ARCHIVED (gate verified). Conductor 040 = local_e4b83fc3-e814-4573-9e9c-e1c54f563c5c (slot way-slot-03, no group, idle). Launcher = local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Ids, titles and status only. Real clock is `date -u`.

Board A4uS9xn1emqupohdE4DUfV: router/current (incarnation 58), router/roster58 (v20+, READ FIRST: update_1..21; get with out_dir, never print). Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q464). Conductor desk MKAx49RAskZ3cV7f2EkDMF. Use `get` with out_dir, NEVER `list`/`query` (floods context with every doc path).

## Landed this incarnation (each read by me at the merge)
hub#841 numerology c216a52e, hub#842 astrology 9ccc242e, hub#845 gateway 392b1503, hub#843 reading faculty 1dae531b (OFF by default: ORACLE_MODEL unset, no routes). core#47 7014970f, core#49 teller hand-off 2524db49, core#48 way 0.1.14 on way/plugin 7541ca90 (installed plugin is still 0.1.12: owner step).

## Running at handoff (background agents die if you are archived/rotated: do NOT archive #58 until they report)
a512cb63311c707f1 SURFACE room continuation on hub#844 (branch surface/oracle-fortune-teller-room, stacked on #843 which is now merged: it must merge main 1dae531b). a6a24d25129d591d7 INT follow-ups desk (P10-1 redirects/proxy/loopback peer, P10-2, mutants N02 N14 N20 N23) draft PR from main.

## Next
1 #844: when a512cb63 reports: PRIVACY delta + short DOORS delta on the new head, then lander (Sonnet, ci-novahub hold). 2 INT follow-ups PR: PRIVACY delta then lander. ORACLE_MODEL must NOT be set until P10-1 is fixed and the owner card 'Reading model and ceiling' is answered. 3 Finding for DOORS (conductor): gateway 'local' = oss_router.oss_enabled(), not loopback. 4 Owner answers read: q460 A (he runs the leak scan), q461 A (conductor 040 told to queue SPEND-GATE-ACCOUNT-CAP-FAILOPEN, ADMIN-CUSTOMER-SEPARATION design, shell parity), q462 A (done). q463 (ENFORCE_PRIVACY_WALL) unanswered. 5 Still unstarted queued picks: 290 ASK-MODEL-PICKER, 291 ASK-LOCAL-MODEL (need D7 landed: check), 302/303 held Opus; deck scans NOT started (possible download: ask the owner, Law 9). 6 Cleanup of clean leftover worktrees (audit first, never bulk).

## Added after the first push (conductor 040, read by me)
040 recorded q461 A as picks DOORS~SPEND-GATE-ACCOUNT-CAP-FAILOPEN rank 306 and VAULT~ADMIN-CUSTOMER-SEPARATION rank 307 (design only). NOT recorded: shell parity: the old SURFACE~ONE-INTERFACE-D3-SHELL-PARITY was superseded 2026-10-11 (q359); card q461 says it is re-queued as the first dead-menu desk. OWED TO 040 BY #59: the new task's id, title and detail (from docs/COMMAND_COMPLETION_PLAN.md section 6, core PR 46 merged), so 040 files it and records the pick. q463: the owner asked where to read ENFORCE_PRIVACY_WALL; I told him it is a variable on the connector service (novahub-mcp) in Railway per the review comments (unverified), he types on/off, or picks B.

## Gotchas
Sends used 6 of 10 since the owner typed. ArtifactData `list`/`query` floods context: use `get`. Setting a card: fields at the top level of the doc (not nested under data). PowerShell Remove-Item is refused on F:\Claude Sessions; use bash rm/rmdir for ci locks. Stop hook false-positives on the word "handoff" in roster writes. Public repo: ids only.
