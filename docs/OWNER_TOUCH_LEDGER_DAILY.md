# Owner-touch ledger, daily run (proposal)

Task `OWNER-TOUCH-LEDGER-DAILY`, part 1. Lane WATCH. Status: **proposal**. The script and its test are
in this PR; the scheduled task and the Conductor desk write are NOT created here (standing
configuration and board writes are the router's or the owner's call).

## What exists after this PR

`watch/owner_touch_ledger.py` (stdlib only, read-only) counts the times the owner typed into a session:
user-role transcript lines whose `origin.kind` is `human`. It keeps counts only; no message text is
written anywhere. The category split is a heuristic and indicative; the totals are the solid part.

It exits **2 and prints `UNKNOWN`** instead of a zero when it cannot see:

| Case | Why it must not read as zero |
|---|---|
| no transcript file in the window | an empty or moved transcripts root looks like a quiet day |
| fewer files than `--min-transcripts` | a run inside a Claude session always sees its own transcript, so "at least one" proves nothing there |
| user messages read, none with an `origin` field | if the app stops writing `origin`, every count becomes 0 and reads as a pass |

A genuine zero (transcripts present, `origin` present, nobody human typed) still exits 0 and says
`owner touches: 0` beside the number of transcripts scanned. Tests: `tests/test_owner_touch_ledger.py`
(each UNKNOWN case, the counted case, the genuine zero, the one-line form; with the two guards
removed, six of the first nine fail).

## Proposed daily run

One scheduled task, daily, **06:10 Pacific** (after the 04:30 vault sync, before the owner's day).
Because the Conductor desk page is written through the artifact database tools, which only a session
can call, the run is a scheduled Claude session (same shape as the Sessions desk keeper,
`docs/SESSIONS_DESK_KEEPER.md`), not a bare Windows task.

Task prompt, in full:

1. Run, from the merged leadfuel-core checkout (not a worktree):
   `python -I watch/owner_touch_ledger.py --days 1 --min-transcripts 2 --line`
2. Whatever it prints (one line) and its exit code are the result. Exit 0 and exit 2 are both
   written; any other exit is written as `OWNER-TOUCH-LEDGER <date> UNKNOWN: script failed (exit N)`.
   Never write a number the script did not print.
3. Write that one line to the Conductor desk page (below), then stop.

`--min-transcripts 2` is the point of the second guard: the scheduled session's own transcript is the
first file, so a root that otherwise holds nothing reads UNKNOWN, not "1 transcript, 0 touches".

## The one line

```
OWNER-TOUCH-LEDGER 2026-10-20 last 1d (UTC): 53 owner touches in 13 sessions, 35 transcripts scanned; top: 47 other, 3 paste, 3 go
OWNER-TOUCH-LEDGER 2026-10-20 UNKNOWN: <reason>. This is not zero.
```

(The first line is real output of the script run against this machine's transcripts on 2026-10-20,
counts only. The second shows the failure form.)

**Where it goes:** proposed as a single document `ledger/owner-touch` on the Conductor desk page's
database, replaced in place each day, with fields `line` (the text above), `status` (`counted` or
`unknown`), `touches`, `sessions`, `transcripts` (numbers, absent when unknown) and `written_at`
(UTC). Replacing one document keeps it a single line on the page and leaves the `desks/<lane>` task
docs alone. **This path is a proposal: I did not read the Conductor desk page, and the router should
confirm the path (or name another) before the task is created.** The page itself would need a small
render for `ledger/owner-touch`; that is a SURFACE/WATCH page change and is not in this PR.

## Not in this PR (reported as NEXT)

1. Create the scheduled task above (router or owner; it is standing configuration).
2. Confirm the `ledger/owner-touch` path and add the one-line render to the Conductor desk page.
3. Part 2 (the weekly synthetic) and the stuck-session detector wait for `NODE~WAKE-ON-ANSWER`.

## Verified and taken on trust

Verified by running: the script, its self-test and the ten tests; the real output line above; that
removing the two UNKNOWN guards fails the tests. Taken on trust: that `origin.kind == "human"` is
what the app sets for typed text (the original author's finding; the live transcripts do carry the
field, but I did not check it against a case where I know the owner typed), and that `watch/` is
WATCH's directory (the session map has no per-file row for it; its neighbours there are WATCH's).
