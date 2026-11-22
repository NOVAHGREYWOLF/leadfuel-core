# Handoff: N1, the nightly full run gives no verdict (WATCH)

Branch: `worktree-agent-abe0989f6d98db626`. Draft PR: see `gh pr list --head worktree-agent-abe0989f6d98db626`.
Stopped at ROUTER #122's time box. No lock held. Nothing has been deployed.

## Measured (by this desk)
- Runner: `watch/nightly_full_run.py`, deployed copy under `%LOCALAPPDATA%\nightly-full-run` (byte-identical to main
  when this started). Task: "WATCH nightly full run", 04:30 PST daily, PT5H limit, `conhost.exe --headless python ...`.
- orchestrator.log, 11-01 to 11-07: fetch, lock and worktree take about 5 s altogether. All the rest is pytest,
  killed at 180 min every night. The raw outputs end at 93-95% (77% on 11-01), and each file was still growing in its
  last minute, so the run is slow, not hung. It needs about 190-195 min at November's pace.
  Finished runs: 10-27, 14357 tests in 2h39m; 10-29, 14567 in 2h42m.
- CPU: `\Processor Information(_Total)\% Processor Performance` = 20.6 at 22:00Z on 11-07, with the box at 100% load.
- 10-31 UNKNOWN: the acquire call to the lock helper (180 s timeout) hit TimeoutExpired, because docker was too
  slow to answer.
- LastTaskResult is 0 after UNKNOWN nights. conhost does not pass the exit code on, so the log line is the only
  verdict.
- hub main has been 3540eff8f3a5 since 10-31, which is why every night tested the same SHA.

## In this branch (built by a sub-agent; not re-run here in full)
- A bare `--collect-only` count before the run. PASS now needs that count to equal the run's own `scope:` count.
  If they differ, or the count is unknown, the night is UNKNOWN.
- A single time budget (`--budget-minutes` 285, inside PT5H). The cap is now 270 and is clipped to the time left.
- A progress line every 10 min. A stall cap (`--stall-minutes` 30). A capped night now says the percent reached and
  the pace.
- The acquire helper timeout is 600 s, and a timed-out attempt is retried.
- New log fields go at the end of the line: `bare= collect= progress= budget=`.
- The sub-agent reported: tests/test_nightly_full_run.py 94 passed, 1 failed (in its own test), the failing test
  fixed and passing alone, and the whole file NOT re-run.

## Next
1. Re-run `python -m pytest -q tests/test_nightly_full_run.py` (it took 49 min on the starved box). Then review the diff.
2. Merge on green (the repo is public, and CI `test` / `pytest` runs on ubuntu-latest).
3. Deploy by a hash-verified copy into `%LOCALAPPDATA%\nightly-full-run`. Do NOT re-run the Register script with
   its default `-Time 05:30`, because that would move the start from 04:30 to 05:30 PST.
4. Run `--dry-run`, then one manual run under the heavy slot, only when it is free and hub CI is idle. Or let
   the 04:30 PST run be the check. Done means two nights in a row with a verdict and `bare=` equal to `collected=`.
5. Q-CI1 (overlord) is still open. At this box's pace a night that waits 90 min for the slot gets about 3h12m of
   pytest, which is right at the edge.
