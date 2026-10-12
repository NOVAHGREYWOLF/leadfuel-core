# Router handoff #037 -> #039 (2026-10-12 ~20:4xZ UTC, soft cap 307k)

ROUTER #37 is local_76301acc-e12f-458b-bce2-4975a4d87359. Ids only. Board router/current (A4uS9xn1emqupohdE4DUfV; ALWAYS use out_dir) keys agents_37*, for_37_from_conductor_027, reserved_38; doc router/log37 (e01-e12). Router desk LzmP6QcxmYh9TdvMMjS883, Conductor desk MKAx49RAskZ3cV7f2EkDMF.
ROUTER #38 local_fed56153 ("owed questions") is a separate router that clears open cards with the owner; it relays one-interface answers to the live router. Conductor 027 is local_7058d9c7-b1f4-4850-9560-b12328cedd6a (025 and 026 are archived/rotated).

## Done (verified by me with gh / ls-remote / get_session)
- #36 and SURFACE part 10 archived through the gate. Redline audit DONE (part 11), outputs in F:/Claude Sessions/handoff/one-interface-redline-audit/.
- Hub merges seen: #809 422ee378, #810 06d4ee4b, #811 451b6fae, #812 7309a41a, #813 c53a4b1f (= hub main at 20:31Z).
- Hub#814 (EARNED-ACCESS step 1, draft, head 72dd7f53 = ls-remote, pytest job SUCCESS, main unmoved at c53a4b1f): first review FAILED (real bug, fixed), second review PASS with notes. Carries migration 0012.
- Nothing is running under #37: all four agents reported.

## Next (in order)
1. Claim (title ROUTER #39 · one-interface, ROUTER group, router/current). Archive #37 once its handoff is pushed.
2. Read the Router desk cards yourself (out_dir). Answered by the owner 19:34-19:42Z and NOT yet routed: q373 A (land #814), q372 C (note: "send me a note on this i am note sure"), q371 A, q370 A, q366 A, q365 B (note: hybrid, local and cloud), q364 A, q362 B, q315 B. #38 relays them; confirm on the cards, then write routed.
3. LAND hub#814 under q373 A: landing agent in the ci-novahub hold, merge main in if moved, CI pytest SUCCESS on the exact head, re-check main, squash --match-head-commit; report to conductor 027. Post a retention card (rows only die by account erasure).
4. Conductor 027 request (key for_37_from_conductor_027): open a DESIGN or SURFACE desk, project one-interface, for STEP 1 only: one private phone-readable page showing the levels and game design as the docs state them, each claim cited. Do not act on q369 until its card shows an answer.
5. q370 A and q371 A: VAULT desks (route.py says opus) to turn on RUNNER_REQUIRE_APPROVAL and CAMPAIGN_REQUIRE_APPROVAL and make approve person-only with MESH_ENFORCE_SCOPES; these are production settings the owner decided, verify each after. q372 C: owner wants a plain note on what the approval-link secret means (owed to him).
6. Tiered memory answers (q362 B, q364 A, q365 B, q366 A) go to INTELLIGENCE tiered memory part 2 local_b62be96c-cdf5-429f-824b-69dd7887fe1d (idle since 10-11; open part 3 if over 300k). q366 and q317 also need his typed go in the desk's own chat.

## Owed
Open cards: q294, q316-q318, q363, q367-q369. #35 local_19f89eda and #33 local_62d2f0c7: pushed and clean, the app refuses to archive them ("live work"); the owner archives them from the sidebar.

## Gotchas
router/current writes collide (version moves); ArtifactData without out_dir costs ~25k tokens. Clock jumps between my turns: use date -u. Agents cannot message sessions; I relay. Background agents die if I am archived: none run now.
