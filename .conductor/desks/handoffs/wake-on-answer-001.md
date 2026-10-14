# Handoff: NODE~WAKE-ON-ANSWER 001 (desk agent of ROUTER #53, 2026-10-14 ~02:05 UTC)

Branch `node/wake-on-answer` off `way/plugin`; draft PR into `way/plugin` (see the PR list). Plugin 0.1.12.
Handed off at the agent's 300k guard. The build and the proof are done; what is left is small.

## Done (verified by this desk)
- `plugins/leadfuel-way/scripts/wake_on_answer.py` (plan / judge) and `tests/test_wake_on_answer.py`
  (85 tests, written failing first, commit add747b). Skill `skills/wake/SKILL.md`. Router skill steps 3
  and 4 (`asker_session`, the watcher). README, layout test, version 0.1.12 in three places.
- Touched tests pass locally: test_wake_on_answer, test_plugin_layout (includes `claude plugin
  validate`), test_way_hook, test_way_launch, test_way_projects. No full local pytest (q354 rule).
- End-to-end proof on the real Router desk collection, cards `questions/wake-test-001` and
  `wake-test-002` (withdrawn, so the owner's page hides them; left as evidence):
  - 001, asker a missing id: send `delivery: undelivered` -> UNDELIVERED; note written to Build Board
    `router/wake_undelivered` (one TEST entry, left as evidence).
  - 002, asker the fake asker slot run `local_0c1da952` (launched by ROUTER #53, way-slot-05): send said
    `delivered`, the search raced it and found nothing -> UNKNOWN (correct); next pass rechecked ->
    the target's transcript held the token -> DELIVERED, `routed` written. Its ACK seen in list_events.
  - HELD was not observed live (the target was idle); it is unit-tested only.

## Left
1. Check CI (`test` workflow, job `pytest`) on the PR head; undraft only when it is `success`.
2. The router (now ROUTER #54, `local_2afda8d8`) archives the fake asker run `local_0c1da952`.
3. Owner steps (a card): approve creating the scheduled task `wake-on-answer` (Haiku, every 15 min,
   prompt in the PR body), set it to Bypass in the app, update the installed plugin to 0.1.12.

## Gotchas
- 21 real cards (q415-q435) are answered and unrouted right now; only a router acts on them.
- A send from inside a router's own session to its own id is refused, so the watcher cannot live in a router.
