# Handoff: N3, echo and signal pip-audit (ARMS)

Stopped on ROUTER #122's time box, 2026-11-07. Ids and status only (public repo).

## State at handoff (UTC, re-read before acting)
- echo PR 63, draft, branch `n3-filelock-cve`, head `ad69a85`. `security` green on the head (hosted pip-audit success, fallback skipped); `writing` green; `tests` / `pytest` QUEUED. echo main `39ab083`, unmoved since the branch was cut.
- signal PR 42, draft, branch `n3-filelock-cve`, head `f85ab0b`. Every check green on that head, but signal main MOVED to `fab2fb0` after the branch was cut (1383a7a). Merge main in and re-green before merging.
- Locks: this desk took none. `ci-signal` was held by `ARMS-novah-estate-part-4--B8` at 21:51Z. `ci-echo` was free.

## The fix (same in both)
filelock 3.32.7 carries 13 advisories (CVE-2026-112907..112940, OSV, all AV:L local). Fix: 4.2.1. The cap is litellm: stable 1.104.0 to 1.108.2 require `filelock<4.0`; 1.103.x has no filelock dependency; only 1.109.0rc1 lifts the cap to `<5`. requirements.txt now has `litellm>=1.55,<1.104`, `filelock>=4.2.1`, `huggingface-hub<2` (holds hub at 1.33.0). Resolved: litellm 1.103.10, filelock 4.2.9, openai 3.46.0 -> 2.54.0. Lift all three once a stable litellm 1.109+ ships.

## Next
1. echo: take `ci-echo`, mark PR 63 ready, wait for `pytest` success on the head SHA, ls-remote main unmoved, `gh pr merge 63 --squash --match-head-commit <sha>`, release.
2. signal: queue for `ci-signal`, merge origin/main into the branch, wait for `security`, `tests`, `lint` and `writing` success on the new head, ls-remote main unmoved, squash with --match-head-commit, release.
3. Confirm `security` green on both mains after merge.
