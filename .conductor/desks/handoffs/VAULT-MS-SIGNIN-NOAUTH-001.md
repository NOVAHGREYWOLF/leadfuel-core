# VAULT~MS-SIGNIN-NOAUTH, handoff 001

- **Desk:** VAULT one-interface part 2, a background agent of ROUTER #35 (local_19f89eda-38f2-4c2c-9d32-3a2d41c77356).
- **True source:** owner card q357 = A (Router desk), filed as conductor pick VAULT~MS-SIGNIN-NOAUTH. Finding B1 on hub #803.
- **Written:** 2026-10-12, about 00:05Z.

## State (re-read before acting; do not trust these lines)

- **PR:** hub #808, branch `vault/ms-signin-noauth`, head `89aba42d8e93428d469572f36694308c47613e34`, which includes main `33903f34`. It is a draft and not merged.
- **Worktree:** `F:/Leadfuel/repos/novahub/.claude/worktrees/vault-ms-signin-noauth`. It is clean and pushed (checked with ls-remote).
- **Fix: done.** The PR body says what counts as proof (`xms_edov` or the consumer tenant, read from the ID token), the linked-only path, and the `/auth/microsoft/link` route.
- **Tests:** 25 new tests in `tests/test_ms_signin_noauth.py`. All six exploit cases failed on main `2cec3769` and pass on the head.
- **Gates:** `SKIP_TESTS=1 sh scripts/gates.sh` on the merged tree gives 13 of 15 green, 2 skipped.
- **CI run 38183599602 on the head:**
  - Attempt 1 failed only prime-digest, a known run-order test.
  - Attempt 2 (the one allowed re-run) failed 5 tests in `test_spoke_reports.py` at 00:00:01Z, as the run crossed midnight UTC.
  - Those 5 pass 15/15 locally at 00:00Z and are not touched by this PR.
  - Per the brief ("anything else: stop and report") I stopped here.
- **ci-novahub:** released. Re-queued at the original timestamp `20261011T221525Z-VAULT-ms-signin-noauth--hub-pr808`, precondition: waiting on the ROUTER #35 ruling.

## Next step (for the successor, once ROUTER #35 rules a further CI run is allowed)

Take ci-novahub when it is offered, then:
1. Merge current origin/main in and push. Pushing fires CI.
2. Wait for CI `tests/pytest` to succeed on that exact head (full 40-hex SHA), with the count guard line showing ran == collected.
3. Confirm with `ls-remote` that main has not moved.
4. Undraft and squash.
5. Read the Railway deploy record for the merge SHA.
6. Release the slot.

## Owner step (in the PR, not done)

Add `xms_edov` and `email` as optional ID-token claims on the Microsoft app registration. That gives one-click sign-in back to unlinked work accounts on verified domains. Until then they use email sign-in, then Connections, then Microsoft, which links the account.
