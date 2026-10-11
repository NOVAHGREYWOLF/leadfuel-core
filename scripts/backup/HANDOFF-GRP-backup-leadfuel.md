# HANDOFF · NODE~GRP-backup-leadfuel (second desk, background agent of ROUTER #34)

State as of 2026-10-11 03:50 PDT. Re-read before acting; do not trust these lines. Counts and ids only.

## Where it stands: working, verified, restore test passed

- Weekly task `LeadfuelBackup` (Sunday 03:30, runs the script under Windows PowerShell 5.1) ran for the
  first time on 2026-10-11: 0x0, `DONE failures=0`, 6 min 15 s, no error lines. It copied 159,949 + 1,706 +
  7,392 files (4.60 + 0.59 + 3.04 GiB).
- A second pass (started once by hand through the same task, with the fixed script) copied only the 33 + 0 + 2
  files that live trees had changed since: 0x0, `DONE failures=0`, 4 s. The incremental path works.
- `-Verify` after that: Leadfuel 159,979 files / 4,935,305,058 bytes, Claude Sessions 1,706 / 638,556,025,
  novah 7,392 / 3,266,905,772. Source and backup equal on all three, would-copy 0, extras 0.
- Skipped by design (dependency and cache folders): Leadfuel 158,318 files / 3.24 GB, Claude Sessions 44 files,
  novah none.
- `-RestoreTest`: one random folder (11, 5 and 6 files) and 150 random files from each tree restored and
  matched the source by SHA256. Matched 100%, drift 0, mismatch 0. A doctored backup (one flipped byte, two trees
  absent) made it fail with exit 1, so a pass is not vacuous.
- Same-disk refusal holds in all three modes and leaves nothing behind on the wrong disk.
- Free space on the backup drive was 601 GB against a 8.8 GB source (rule: at least 3x).

## What this branch changes over the first desk's script

1. The same-disk check ran after the destination folder was created, so a refused run left a folder on the wrong
   disk. It now runs first, checks every source disk, and refuses on "unknown" as well as "same".
2. New `-Verify` (list-only robocopy, counts and bytes per tree, never names).
3. `-RestoreTest` now samples all three trees, not one 9-file folder, and fails if it had nothing to draw from.

Parse-checked under Windows PowerShell 5.1 (5.1.26100) before it was copied to the task's script location. The
deployed copy and this file have the same SHA256.

## Not done / for the owner

- Nothing leaves the machine. The backup folder holds credential files by design; keep that drive private.
- The destination and the sources are all on this one PC: this protects against a dead source drive, not against a
  dead machine or a stolen one. An off-machine copy is a separate owner decision (card Q125 said local only).
- The task's own limits are unchanged (4 h cap, not on battery, no wake). The next run is 2026-10-18 03:30.
- The log header says counts only, but robocopy prints a file's path in an error line if one ever fails. Read the
  log with a filter on summary lines, as this desk did.

## To do after the next Sunday

1. Newest log must end `DONE failures=0`, and task result must be 0x0.
2. Run the script with `-Verify` (expect small would-copy counts only if trees changed since 03:30) and with
   `-RestoreTest` (expect `RESTORE TEST OK`), both under `powershell.exe`, not `pwsh`.
