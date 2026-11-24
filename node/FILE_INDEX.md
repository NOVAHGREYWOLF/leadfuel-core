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

## Smart indexing: near-duplicates and tags (cluster files part 4)

Code: [`node/file_smart.py`](file_smart.py). Tests: [`tests/test_file_smart.py`](../tests/test_file_smart.py).
It opens the index above **read-only** and writes its own results to `smart.sqlite` beside it
(`%LOCALAPPDATA%\cluster_files\smart.sqlite`; override with `--smart-db` or `CLUSTER_FILES_SMART_DB`).
Like the index, it lists real paths: keep it and its reports off the vault.

```
python node/file_smart.py run --machine greywolf --images 3000 --pdfs 300 --model-sample 100 --minutes 75 --gb 5 --wait-lock 20
python node/file_smart.py report --out %LOCALAPPDATA%\cluster_files\report   # near.json, near.md
python node/file_smart.py stats
```

`run` takes `scripts/heavy_lock.py` (`HEAVY_LOCK_PY`), drops to background priority, caps reads at
`--mbps`, stops at `--minutes` and `--gb`, and refuses busy hours (08:00-22:00 local) unless the machine
has had no keyboard or mouse input for 15 minutes; when idleness cannot be read in busy hours it refuses.
It never rescans the drive: it works from the index plus a bounded sample of files.

### Methods (all local, no vendor API)

| What | How |
|---|---|
| Same photo, different size | Pillow decodes the image (JPEG in draft mode), applies EXIF rotation, 9x8 greyscale, 64-bit difference hash. Near when the Hamming distance is at most 5 and the aspect ratios agree within 3%. Pairs come from multi-index hashing (eight one-byte buckets). Flat images (<=3 or >=61 bits set) are skipped and counted. heic, svg, raw and psd have no local decoder: `unknown`. |
| Same document, different format | Word 4-gram shingles of the text the index already holds (md, txt, html with tags and scripts stripped, docx, xlsx, pptx, ...), plus pdf text from pypdf in a bounded sample (first 20 pages, a pdf whose name matches a document first). One-permutation MinHash, 64 bins, densified; 16 bands of 4 for candidates; similarity >= 0.8 confirms. Under 50 words: not compared. Only the first 16,000 characters per file are compared (what the index keeps). |
| Groups | Union of confirmed pairs. A set that is byte-identical throughout is left to the exact report above. The proposed keep copy: most durable location (the part 5 rule), then the largest picture or the editable source format (md/docx before txt before html before pdf), then the oldest date, then the shortest path. Report only; nothing is moved. |
| Image sample | Images whose normalised name (`IMG_0042-1024x768 (1).jpg` -> `img_0042`) is shared by another image first, then a seeded random fill. |
| Rule tags | Facets `media`, `kind` (code, docs, data, media, backup, model, archive, binary), `scope` (estate, personal), `project`, `client` (the folder under `clients`), `privacy`. From path, name, extension and the git flag only. A facet no rule can decide is left open, never guessed. |
| Model tags | A bounded sample of files the rules left without a scope or project goes to Ollama on loopback (`qwen3:4b-instruct-2507-q8_0` by default), 20 per call, temperature 0, JSON only. Answers outside the allowed values become `unknown`; retired arm names map to the ratified ones. The model's confidence is self-reported and stored as such. No model reachable: the sample is tagged `unknown` with no confidence. |
| Privacy | A privacy-tier path (the index's verdict, re-checked) is never decoded, never text-read, never pdf-read, and reaches the model by its path only. |

Every tag row has `source` (`rule` or `model`, enforced by a CHECK constraint) and `confidence`.
