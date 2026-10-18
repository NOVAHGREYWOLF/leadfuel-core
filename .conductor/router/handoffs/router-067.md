# Router handoff #067 -> #68 · one-interface (2026-10-18, ~300k)

ROUTER #67 = local_4ae89c47-87bf-4d21-b0d1-b2e860cf810a (slot way-slot-01). Conductor 044 = local_b57528f8-d8b0-497e-a721-eefa93a26fdf (way-slot-05). Launcher local_a6ce3e66-858d-46fe-a6e7-f3f6e50a83d7. Ids only. State lines are mine and unverified by you: re-read.

Board A4uS9xn1emqupohdE4DUfV: router/current (incarnation 67), router/roster67 (v22+). Router desk LzmP6QcxmYh9TdvMMjS883 (only q208 open; next free q564). Conductor desk MKAx49RAskZ3cV7f2EkDMF.

## Program (pick SURFACE~COMMAND-CENTER-END-TO-END rank 421, owner "go")
Whole command center build, one desk at a time, each door-reviewed (Opus, read-only agent), landed by a lander agent in the ci-novahub hold on a green CI pytest on the exact head. Order: plan PRs 3,4,5a,5b,5c,6,7 then Layer 2 items 1-15 (F:\Claude Sessions\handoff\one-interface-research\COMMAND-CENTER-FULL-VISION-MAP-001.md section 3). Else waits: oss one-liners, B1-B6, #859/#818/#790, test.yml, store orders, ever_paired. Owner answers: q552 C (SURFACE owns screen files; map row b147836 written), q553 A, q554 B, q555 A, q556 A, q557 B, q558 C, q559 B, q560 A, q561 B (no D7), q562 B (world flag stays off). Layer 2 item 1 READ (044 did it; hub main c3fc0308 = healthz rev).

## Done by #67 (gh)
hub #876-#881 merged; #882 (PR 1, squash 0d46adee) and #883 (PR 2, squash c3fc0308) merged. #66, #64 archived.

## Next
1. Hub #884 = PR 3, draft, head f6a7c7eb, by SURFACE 24 (agent a88aa1054474a83dd, DONE). Open ONE DOORS review (Opus, read-only): it deviates (reads public static/atlas/topology.json for edge state because /api/command/atlas drops state; 3-line screen.js edit; no new script tag), account rule: unknown never 0. Then a lander. Then PR 4 (q549 B auto-rotate ON differs from plan, say so), 5a (q551 B 3D default differs).
2. Website: LAUNCH-REQUEST sent to the launcher for SURFACE · leadfuel.cloud website part · 2 (owner "sned to router to open" in part 1 local_c164e7c8, found in its transcript). Wait for LAUNCHED; track as kind slot; part 1 stays open until part 2 is live, then archive it through the gate. Part 2 has two live-site claims to ASK on.
3. Archive ROUTER #65 local_7e9a0f7b (refused twice: live work) and chip desk DOORS 53 local_69c542dc (check clean first) through the gate.

## Gotchas
Stop hook false-positives on the word handoff in board writes (not a rotation). A ROUTER cannot Edit files (hook): delegate map edits to a small Haiku agent. Pin ArtifactData writes if_version; a card may be answered between read and write.
