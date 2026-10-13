# Sessions desk keeper

The Sessions desk page (`watch/sessions_desk_page.html`, published as a claude.ai Artifact) shows every
local session filed by sidebar group: role, task id, stage, progress toward done, size against the
handoff cap, and a keep / rotate / archive verdict. The keeper refreshes it every 30 minutes.

Session data is reachable only through the desktop app's session tools, so the keeper must be a
Claude session. It collects metadata with those tools, hands it to `watch/sessions_desk_feeder.py`
as files, and writes the result to the page's database. The script does everything that does not
need a session tool, and is tested in `tests/test_sessions_desk_feeder.py`.

## Database

| Path | Written by | Holds |
|---|---|---|
| `snapshot/current` | keeper only | the full snapshot: one row per session, summary, flags, gate rules |
| `feed/latest` | keeper only | the newest digest (the conductor reads this) |
| `feed/d<HHMM>` | keeper only | one digest per half hour slot, UTC; the slot id repeats daily, so the feed keeps 24 hours |

Both collections are readable by anyone who can view the page and writable only at admin level.

## One tick

1. `list_sessions` with `limit` 300 (non-archived). Save the array to `sessions.json`. A large result
   is saved to a file by the tool; use that file.
2. For each session the list reports running, `get_usage` (its `context.tokensUsed`) and
   `get_session` (its `model`). Write `usage.json` as `{sessionId: {"tokens": n, "model": m}}`.
   A stopped session reports no size; the feeder carries the last reading with its time.
3. Export the previous snapshot: ArtifactData `get` `snapshot/current` with `out_dir`, and the
   Conductor desk's `archive/gate` the same way.
4. Run the feeder:
   `python watch/sessions_desk_feeder.py --sessions sessions.json --usage usage.json --prev <snapshot file> --gate <gate file> --out <dir>`.
   It reads `gh`, the slot locks and each worktree's git refs (no fetch, no network beyond `gh`).
5. `to_read.json` lists sessions whose state changed since the last snapshot (or that were never
   read). For at most 20 of them, newest first, `list_events` with `limit` 12 and write
   `evidence.json` as `{sessionId: {"status_line", "handoff", "read_at"}}`:
   - `status_line`: the session's latest report in protocol form, `STATUS: <DONE|BLOCKED|NEEDS-NOVAH|CONTINUING> | <task> | <one clause>`
     or `ASK: <task> | <one clause>`, summarised from what the transcript shows. No private detail,
     no secrets, ids and titles only. Leave it null when the transcript shows no report.
   - `handoff`: true when the transcript shows a handoff note written, false when it shows the
     session ended without one, null when it does not show either.
   Then run the feeder again with `--evidence evidence.json`. No other transcript is read.
6. Write `snapshot.json` to `snapshot/current` and the digest to `feed/latest` and `feed/d<HHMM>`
   in one ArtifactData `batch`, each pinned to the version read in step 3.
7. Nudge only through the router: read `router/current` on the Build Board for the live router's
   `session_id`. If `digest.json` has any NEW `needed-stopped`, `past-cap`, `quiet-running` or
   `duplicate` ids, send that router one message (ids and titles only). Never message a desk,
   never archive, never edit another desk's work. `archivable` sessions are listed, not archived.

## Verdicts

The verdict applies the Conductor desk's existing archive gate (collection `archive`, doc `gate`)
cell for cell: merged (gh, not the badge), report (STATUS: DONE), handoff, pushed, decision. A
router or conductor is archivable only once a later incarnation is live and its handoff is pushed.
`rotate` means the context is past the cap (300k; 120k for Haiku) with no successor holding the
task. Any unknown cell keeps the session.

## Freshness

The page shows the last refresh time and says Stale past 45 minutes.
