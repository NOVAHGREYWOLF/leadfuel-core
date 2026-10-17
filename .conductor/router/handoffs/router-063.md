# Router handoff #063 -> #64 · one-interface (2026-10-17, ~300k tokens)

ROUTER #63 = local_9be8f00c-13a4-49f0-9745-96acd82d647e (slot way-slot-01, no group, Sonnet 5.5). #62 = local_e3fc56fc-2683-45f6-8aae-3e400ebc5e51 (all its agents failed; archive refused twice, live work, probably Remote Control: owner archives it from the sidebar or retry). Conductor 041 = local_3ab0cbad-417d-482d-a28f-1d56ad614a93. Launcher = local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Ids only.

Board A4uS9xn1emqupohdE4DUfV: router/current (claim_63), router/roster63 (update_1..11, READ FIRST with out_dir). Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q489). Conductor desk MKAx49RAskZ3cV7f2EkDMF.

## Owner rulings (cards read by me, all answered 2026-10-17)
q481 A, q482 B (leadfuel-core to private, his step), q483 A (purge done), q486 A (one chip desk for production reads), q487 A (levels gate access), q488 A (the whole queue runs: admin_grant migration after door review + green CI on the exact head, deploy-config PRs, $0 frontier spend, keep qwen3). q484 answered in CHAT: reading A (admin sees the platform, never any account's data; every account has its own command center). Priority (via 041): command center fully operational, everything else stops, run unattended, one touch only.

## Running (background agents; they die if I am archived, so #63 STAYS OPEN until they report)
aec1daca3122825cb VAULT 20 (hub#847 + wall tests); a36d48502b48b57ea SURFACE 16 (per-account map); ae0bebf619ba0dfeb SENSORS 20 (inventory of 63 unread parts); acd2865006cf1664c NODE 26 (pick 344 local-first digest plan); a9b7670855bc9874f DOORS 51 (admin_grant, platform view, owner-list removal, DRAFT PRs, no merge); a62021c15ecf53262 SURFACE 17 (Fable, pick 346 spec + one batch of questions); a192571ef797d7aef DOORS 52 (pre-redeploy safety check). Chip waiting for the owner's click: task_dce74e0f DOORS 53 (Railway read, typed go).
Done: 329, 334/338, 335, 336, 337 parts 1+2 (part 3 stopped), 339, 340, 341, 342, DOORS 50 (live site stopped updating 2026-10-13: hub deployment e9bf47a2 never finished; main 00137c9a, 39 commits ahead, six other services also stuck).

## Next
1. When SENSORS 20 and NODE 26 report: open one desk per independent build batch in parallel, then review desk and lander per draft PR (ci-novahub hold, test.yml pytest success on the exact head, main merged in).
2. When SURFACE 17 reports: post its batch as ONE card (apply defaults where a ruling exists, say defaulted), relay the spec path to the running desks, hold any contradicted step.
3. Step 10 (levels gate build, door work, Opus) and step 7 after DOORS 51 and VAULT 20 land. NEVER merge the admin_grant migration before door review; a hub merge deploys in 5 s and production is stuck anyway: no redeploy without the owner's typed go (q486 chip).
4. Pick 345 (demos) starts only when 341-346 queue reports operational; tell 041 then.
5. Pick 337 part 3 (plugin draft PR) stopped; worktree node-337-prearchive left in C:/Users/novah/leadfuel-way-plugin; resume only when 041 queues it. q485 nightly is on hold.

## Gotchas
Stop hook false-positives on the word handoff in board writes. ArtifactData get without out_dir floods context. Agents report to me only. Sends to desk agents use SendMessage with the agentId. The 25 fossil tickets under .locks/ci-novahub.wait are other sessions'.
