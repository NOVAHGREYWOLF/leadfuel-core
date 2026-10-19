# Router rotation #083 -> #84 (successor title ROUTER #84 · one-interface) (2026-10-19 ~00:0xZ UTC 10-20, ~300k)

ROUTER #83 = local_4b0acbb8-c44b-4a0d-b841-a342fc53609e (slot way-slot-04), holds router/current (incarnation 83, v630+). It STAYS OPEN: it hosts the agents below, which die if it is archived. #81 local_7e19b69d stays open for LANDER-927b a16ac1148aa34984b only. #79 local_ace81e74 (DOSSIER ad860e466ec0e9a89, LANDER-944 a5cafd8bb93944a0f) and #75 local_dd534bdc (LANDER-926 a7a856bf1c1f98b4b, LANDER-928 ac1f3c0b713c50594) stay open. Cluster routers: #80 local_00e98c14, #82 local_8dbf0105. Conductor 049 = local_4b77bcc9-5b9d-47c7-a491-7e614c02cf2e. Launcher local_a6ce3e66. Board A4uS9xn1emqupohdE4DUfV: router/current, router/roster83 (full log, read it by key with out_dir), router/roster80 (for_vault_90). Router desk LzmP6QcxmYh9TdvMMjS883 (next free card q611; re-read). State lines are mine: re-read them.

## Done by #83
Merged: odyssey#59 (ad58f77e), orbit#38 (b517aa55), both gh-verified. q595 and q597 outcome notes written. Cards posted: q607 (signal/orbit attestation), q608 (hub #949 test-setup ruling), q609 (hub #932 spokes doc), q610 (oracle room for the owner's user account).

## Running (my background agents; they report to the live router session that hosts them, i.e. #83)
VAULT part 90 a7f6c2de3b8d907be (aggregate module floor 3, own draft PRs stacked on #875 head 60cee86c and #946 head; q603 A vs q605 C unsettled: q606), NODE part 94 af5265314cc6af40e (Q574 needs list), (NODE part 95 a582a539f85e8e935 REPORTED DONE: leadfuel-core draft PR #51, flags-in-code audit + rule wording, for the owner; not merged), DOORS part 96 a8a2649da496a62f3 (hub attestation for signal.post_now/approve_post/edit and orbit.send_draft, stacked on #948 92f8de01), DOORS part 99 a77f6405771cbe9a4 (delta review hub #945 07d09f3f).

## Next
1. As each reports: gh-verify the PR, DOORS read-only review, lander (repo's hold, CI green on exact head, squash).
2. Hub order: #948 (92f8de01, DOORS PASS-WITH-NITS, CI pytest was pending) and part 96's PR land BEFORE orbit#37 (27f09a42, code PASS) and signal#37 (cbccd3f, needs DOORS review). Hub lock ci-novahub: LANDER-926 holds (attempt 2 of run 39333055314), waiters LANDER-927 then 944.
3. Owner cards open: q604, q606 (q603 vs q605), q607, q608, q609, q610. Nothing lands on #946/#875 until q606.
4. hub #949 DOORS review owed (q608). Hub #945 lander only after part 99 PASS. #932 lander held until q609.
5. Archive #75 and #79 and #81 through the gate when their agents report; #83 archives itself never (the successor does).

## Gotchas
Stop hook fires on the word handoff in board writes; real size by get_usage. ArtifactData get/list without out_dir floods context. Messages to agents hosted by another session fail. Cross-session sends: about 10 per owner turn; agents and board are free.
