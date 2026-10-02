# Brief + handoff: WAY-router-no-orphan (successor desk of WAY-1)

Ids only (public repo). Title: `NODE · WAY-router-no-orphan 1/1 · router never leaves before its successor`. Sonnet, effort medium. Work on `way/plugin` (draft PR #10) in your own worktree; bare `pytest`; draft PR; STATUS to the conductor `local_c7dff3be` (no router live).

## Source (verify, do not trust)
Owner decision relayed by CONDUCTOR · system build (`local_c7dff3be`, 2026-10-02 ~12:00 UTC): a router must not leave itself until it has a successor. Memory note `archive-rules` records it. Incident: ROUTER #9 (`local_61ed8382`) archived itself at 11:36 UTC and no ROUTER #10 existed. **Cause: text WAY-1 ported into the plugin skills** (from router-branch `0df25ff`): "archive yourself as your last act", even when the successor is only a paste prompt. PR #10 flagged it unconfirmed; installed 0.1.0 shipped it.

## Change 1: skills, tier-aware
- **Router and conductor:** if `start_session` is unavailable, give the owner the paste prompt, stop answering, **do not archive**; the successor archives the predecessor (router Claim step 3). If `start_session` is available, archive only after `list_sessions` for the group shows the successor live.
- Edit: router (Rotate step 4, Claim step 3), handoff (step 6, the table, "A blocked session..." line), way (section 5 bullet, section 6 sentence), conductor ("Rotating").
- **Desks:** the conductor says unchanged (archive after the push is verified). **Open conflict, raise it as a card, do not pick quietly:** memory `archive-rules` says a desk is archived only when completely done, and a session archived at its size limit with no new session opened must be raised to the owner. They differ when a desk hands off at its limit with work remaining.

## Change 2: guard, if feasible
A `PreToolUse` hook entry (matcher `mcp__ccd_session_mgmt__archive_session`) denying `session_id: "self"` from a ROUTER or CONDUCTOR tier (`role_of`). A hook cannot call `list_sessions`. Either (a) always deny for tiers (reason: the successor archives you); safe, simple, **recommended now**; or (b) require a `list_sessions` result in the transcript, after the last handoff write, showing another live session of the same tier in the group.

## Also
`way_doctor.check_handoff_archives` must require the live-successor wording; add a doctor check that the guard is registered; replace `test_skills_follow_the_self_archive_rule`; bump to 0.1.2 (three places, a test keeps them equal). Still open from PR #10: the map-writer carve-out card, section 11 wording.
