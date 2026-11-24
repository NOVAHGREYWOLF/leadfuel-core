# Cluster file index (cluster files parts 2 and 3, plus the report half of part 5)

Code: [`node/file_index.py`](file_index.py) (stdlib only). Tests: [`tests/test_file_index.py`](../tests/test_file_index.py).
Brief: `F:\Claude Sessions\handoff\CONDUCTOR-061\CLUSTER-FILES-BRIEF.md`.

## Where the index lives (outside git, never commit it)

| Machine | Index file | Set by |
|---|---|---|
| GREYWOLF | `%LOCALAPPDATA%\cluster_files\index.sqlite` (`C:\Users\novah\AppData\Local\cluster_files\index.sqlite`) | default; override with `--db` or `CLUSTER_FILES_DB` |

It is one SQLite file with an FTS5 table, plus its `-wal` file. It holds the paths, names, sizes and
dates of indexed files and, for text and office documents outside the privacy tier, up to 64 KB of
extracted text each. It never leaves the machine it describes. Do not copy it into `F:\Claude Sessions`
(a 50 MB file broke vault sync once, see leadfuel-core PR 105).

## What exists already, and what this adds

- Part 1 (`F:\Claude Sessions\handoff\node-workstation-setup\remote\files\`): `cluster-files.json`,
  folder names and sizes down to three levels, **no file names**, plus live listing over ssh and the
  phone's Files tab. Good for browsing; it cannot search files or find duplicates.
- A one-off file-level scan from 2026-11-05 (`inventory/catalog.sqlite`, about 2.7 M rows) was the base
  of the first clean-up plan. It is a snapshot: no incremental re-scan, no content, no hashes.
- Part 4 (sibling desk, `node/cluster_inventory.py`) inventories drives and devices. Not touched here.
- **This adds** a per-file index that re-scans only what changed, a throttled content hash for
  duplicate candidates, local text extraction, a search CLI and loopback page, and a report-only
  exact-duplicate review page.

## Commands

```
python node/file_index.py index F:\ --machine greywolf --pilot --minutes 150 --mbps 60 --hash-gb 60 --wait-lock 120
python node/file_index.py search "zebra plan" [--field name|path|content] [--machine greywolf] [--type doc] [--after 2026-01-01]
python node/file_index.py coverage
python node/file_index.py stats
python node/file_index.py dedupe --out <folder>        # dedupe.json, dedupe.md, dedupe.html
python node/file_index.py decisions dedupe-decisions.json   # records clicks; touches no file
python node/file_index.py serve                        # http://127.0.0.1:8471/ and /dedupe, loopback only
```

`index` is a heavy job: it takes `scripts/heavy_lock.py` (set `HEAVY_LOCK_PY` to the hub's copy) and
queues for it with `--wait-lock`; if the lock cannot be read it says `unknown` and does not run.
`--no-lock` exists for tests and small folders only. The process drops itself to background CPU and
I/O priority, and hashing is capped at `--mbps`.

## Rules the code keeps

- **Read only.** Files are opened for reading; nothing is written, moved, renamed or deleted. A test
  walks the source for destructive calls and outbound network imports.
- **Excluded**: `F:\repos` and `F:\Leadfuel\repos` in the pilot (`--pilot`), every `.git`,
  `node_modules`, virtualenv and cache folder, every `.claude\worktrees`, and always the book
  (`\repos\resonance`) unless it is itself the root being indexed as its own source. Junctions and
  symlinks are never followed.
- **Privacy tier**: a path whose folder or file name reads as health, financial or credential material
  (`Apple Health`, `Taxes 2025`, `.ssh`, `*.pem`, `.env`, ...) is indexed by name, size and date only.
  Its content is never read: no text extract and no hash, so it is never in a duplicate group.
  The rule over-blocks on purpose (a code file called `health.py` is private too).
- **Cloud placeholders** (files whose read would recall them from a cloud service) are not read either.
- **Unknown is not zero.** A machine without a complete scan reads `unknown (not indexed yet)` in
  search; a directory that cannot be listed is recorded and its old rows are kept; a scan that stops
  early is `partial` and removes nothing; a content search lists how many files in scope had no
  content indexed (pdf, private, cloud, too big, pending).
- **Hashing** is two-stage: a quick hash (size + first and last 64 KiB) for every file whose size is
  shared, then a full SHA-256 only where quick hashes collide, largest possible reclaim first, inside a
  byte budget. A file with a unique size cannot have an exact duplicate and is not hashed.
- **Dedupe is a report.** Groups come from full SHA-256 matches only, ranked by reclaimable space. The
  proposed canonical copy: inside a git repo first, then the vault-synced and estate trees, then
  ordinary folders, with downloads, tmp, scratch and cache last; ties go to the oldest modified date,
  then the shortest path. The page offers Keep canonical / Keep both / Decide later and exports the
  clicks as a file; `decisions` stores them. Applying them is a separate, gated step (quarantine
  first, reversible for 30 days) that does not exist yet.

## Pilot (GREYWOLF F:\, 2026-11-23/24)

Measured on 2026-11-24 (Pacific), one run under the heavy lock, below-normal priority, hash cap 60 MB/s:

| What | Result |
|---|---|
| Files indexed | 347,595 in 43,483 folders, 731.5 GB; 0 unreadable folders; scan `complete` |
| First scan (walk + text extract + FTS) | 1,596 s (about 218 files/s) |
| Re-scan, nothing much changed | 44.5 s (712 new, 6 changed, 3 removed) |
| Content extracted | 218,969 files (16 K characters each at most) |
| Content not indexed (reported as unknown) | 3,432 private, 7,044 `.log`/`.jsonl`, 948 pdf/old office, 293 cloud placeholders, 47 too big, 11 errors |
| Privacy tier (name only) | 1,431 credential, 1,252 health, 749 financial |
| Hashing | 291,642 quick hashes, 185,987 full SHA-256 (38.4 GB read in about 31 min, about 20 MB/s), 71 read errors; 52,157 files have a unique size and need no hash |
| Exact duplicates | 41,080 groups, 19.4 GB reclaimable (report only) |
| Index size | 2.4 GB (most of it the content text and its FTS index) |
| Search | 1.5 to 1.9 s per query, cold start, from the CLI |

Machines other than GREYWOLF are `unknown` until each is indexed through its own path. On GREYWOLF
only `F:\` minus the exclusions is indexed; `C:\` is `unknown`.

## The other machines: per-machine readers (part 7)

Code: [`node/cluster_readers.py`](cluster_readers.py), what to read per machine:
[`node/cluster_reader_sources.json`](cluster_reader_sources.json) (machines, routes and the in-use flag
come from part 1's `node/cluster_inventory_targets.json`). Tests: `tests/test_cluster_readers.py`.
They write into the SAME index file above, under the inventory's machine ids (`overlord`, `r710-1`,
`r620`, `greywolf`, `surface`, `msi`; `r710-2` and `r610` have no route and read `unknown`).

```
python node/cluster_readers.py plan [--at 2026-11-24T23:30] [--machine r620] [--json]   # dry run, touches nothing
python node/cluster_readers.py run --machine r620 [--minutes 120] [--mbps 40]           # one pass per machine
```

- The walk and the hashing run ON the machine that owns the disk (`nice -n 19 ionice -c3 python3 -`
  on the Proxmox hosts, PowerShell at Idle priority on the laptops); only path, size, date and hash
  come back. No file content leaves a machine; remote files have `extract_state = remote`, which a
  content search reports as unknown.
- One machine pass at a time, each under the estate heavy slot (`node/cluster_scan_slot.py`), the
  laptops and GREYWOLF only 22:00 to 08:00 Pacific (a pass stops at 08:00), the R620 only when the
  Postgres standby guard says ok, the R710 #1's `overlord-dumps` left unread while an ingest runs.
- A machine that cannot be reached is recorded `unknown` with the reason (coverage and search say so);
  its earlier rows stay. Key setup is the owner's step:
  `F:\Claude Sessions\handoff\ROUTER-142\CLUSTER-FILES-7\KEY-STEPS.md`.
