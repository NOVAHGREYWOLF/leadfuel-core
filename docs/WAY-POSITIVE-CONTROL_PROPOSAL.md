# WAY-POSITIVE-CONTROL: pair every zero with a positive control (proposal, nothing changed)

Task NODE~WAY-POSITIVE-CONTROL (desk NODE, pick 206). **Proposal only.** No skill, hook, version or
test changed. The owner decides whether this becomes a standing rule. If he does, the wording in
"Proposed wording" goes into `plugins/leadfuel-way/skills/way/SKILL.md` section 3 in a separate PR,
with a plugin version bump.

## Source of the task (not verified by this desk)
- Owner queued it in conductor 008's chat (`local_b666d711`), 2026-10-03, pick rank 206. Taken on
  trust from the router's record.
- Basis: ROUTER #13 (`local_21748811`), report after the artifact code review (`local_addebdbe`).
- Conductor 051 and ROUTER #92 relayed the owner's 2026-10-20 "open as many as you possibly can" order.

## Status check before writing (verified by this desk)
- `plugins/leadfuel-way/skills/` on `way/plugin`: no text matching "positive control" or "every zero".
- `origin/main` and `origin/way/plugin`: the phrase appears only in `docs/AUTO-DESKS.md`, as the pilot
  brief (not a rule), and in `.conductor/desks/handoffs/AUTO-DESKS-003.md`.
- `docs/AUTO-DESKS.md` on `way/plugin` records the router's ruling that the formal WAY-POSITIVE-CONTROL
  pilot does not run; live router use is the validation. This proposal does not revive that pilot.
- No open or merged PR and no remote branch carries the rule (`gh pr list`, `git ls-remote`).

## The candidate rule
> A check that reports zero (no failures, no matches, no unpushed commits, no drift, no rows) must, in
> the same command, run the same check against a known positive and show that it found it. If the
> positive is not found, the report is `unknown`, never zero.

## Why (the failure it closes)
The owner's private standing rules already state this in general form: a check that cannot establish a
state must not report one, and a green result should be tested against what the check would print if
its subject were absent. Those rules are general and not quoted here (the repo is public). This proposal
is the concrete habit they imply:

- A `git` check that cannot see remote branches returns zero, which reads exactly like a pass.
- A probe that times out under load says `down` and restarts a second process. It should say `unknown`.
- A grep for a string returns zero because the path changed, not because the string is absent.

A zero from any of these looks identical to a real zero. The positive control is the only cheap way to
tell them apart.

## Why "in the same command"
A positive control run in an earlier step can pass while the real check is broken later: the path moves,
the tool changes, the probe starts reading another source. Running both in one command means the control
and the check share the same input, the same environment and the same moment. This is the desk's
judgement, not a finding from a measurement.

## Existing examples in the repo (verified by this desk with `git grep`)
These already follow the pattern, so the rule would be codifying practice, not adding a new cost:
- `watch/vault_sync_status.py` on `way/plugin`: every invocation first classifies built-in samples with
  known answers; a failed control reports `unknown` (lines 18-20, 178).
- `tests/test_vault_sync_status.py` on `way/plugin` line 125: a test whose comment is the positive control.
- `watch/nightly_full_run.py` on `origin/main`: positive controls first; a failed control stops the run as
  `UNKNOWN` (lines 9 and 740).
- `vault/leak_scan.py` on `origin/main`: plants a fresh random canary before each run (line 26).

## Examples of a positive control (for the desks, not a full catalogue)
- Grep for absence: plant a unique token in a scratch file and confirm the same grep finds it, then grep
  the real tree.
- Unpushed commits: in the same command, count a known unpushed commit in a scratch branch before counting
  the real branches.
- Failures count: run the check against a fixture with one known failure and confirm the count is one.
- Remote state: `git ls-remote` on a known branch name must return that branch before an empty result is
  trusted.

## Limits
- The control must be cheap. It must never add a full `pytest`, `gates.sh` or other heavy job, because
  the one-heavy-job rule applies to those.
- It applies to checks that report a zero as a pass. It does not apply to reading another session's report,
  which section 3 "Verify" already covers.
- It does not change the test rule (section 3, card q354 A) or the rule against repairing a test that refuses
  a colour.

## Proposed wording (not applied; for section 3 of the way skill if the owner adopts it)
> - **A zero needs a positive control in the same command.** A check that reports nothing found (no
>   failures, no matches, nothing unpushed, no drift) runs against a known positive in the same command and
>   shows it found it. If the positive is missed, the report says `unknown`, not zero. Keep the control
>   cheap: no full test run inside it.

## Options for the owner (for the router's card; desk default is A)
- **A.** Adopt as a standing rule: add the wording above to way skill section 3 in a follow-up PR with a
  plugin version bump. DEFAULT.
- **B.** Keep it as desk practice only: this doc stays as the reference, no skill change.
- **C.** Drop it: the global section 2 and 4 rules are enough.

## What this PR changes
- One new file: `docs/WAY-POSITIVE-CONTROL_PROPOSAL.md`.
- No `SKILL.md`, hook, `plugin.json`, `marketplace.json`, version, or test file changed. Docs only, so no
  version bump.

## Verified by this desk vs taken on trust
- Verified: the absence check and the existing examples (above, `git grep` on the named refs); the
  router's pilot ruling (`docs/AUTO-DESKS.md` on `way/plugin`); no PR or branch carries the rule.
- Taken on trust: the owner's order and pick rank (from the router's record); ROUTER #13's basis; the
  owner's private standing rules, paraphrased above from the session's CLAUDE.md (not checked in any repo).
