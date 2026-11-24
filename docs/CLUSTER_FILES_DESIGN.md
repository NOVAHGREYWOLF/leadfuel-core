# Cluster files: see everything, search everything, then dedupe (all local)

NODE cluster files part 4 (the inventory step), 2026-11-23 Pacific. Owner: "show all drives and devices. all overlords drives and be able to go through them. We should be able to search freely with all the files in the cluster. then we want to condense this. get rid of all the things repeating. dedupe. then we do smart indexing." And: "all local". Brief: CONDUCTOR 061 CLUSTER-FILES-BRIEF (parts 1 to 6). This note covers part 1 (the inventory, built) and the heavy-lock design for part 2.

## What exists, and what this adds

| Piece | Where | State |
|---|---|---|
| Connect "Files" window, disk map, folder-size tree per machine, Explorer folder, read-only live listing and file fetch, phone Files tab | `C:\Users\novah\Connect\files\` (GREYWOLF, not in git), served to the phone by overlord's `nc-phone.service`; notes in `F:\Claude Sessions\handoff\node-workstation-setup\NODE-cluster-files-part-00{1,2}-handoff.md` | Built by parts 1 and 2 of that desk. `data\cluster-files.json` was last written 2026-11-20 (five machines, folder names and sizes to three levels, never file names). Not touched here. |
| File-level scan of GREYWOLF, overlord's old SSD copies, SURFACE (path, size, mtime, extension; nothing hashed) | `F:\Claude Sessions\handoff\node-workstation-setup\inventory\*.sqlite`, report `INVENTORY-REPORT-2026-11-05.md` | 2026-11-05, 2.7 million rows, 22 days old. **The sqlite files are tracked in the vault repo and are over its 50 MB limit (catalog.sqlite 436 MB, greywolf.sqlite 267 MB, surface2.sqlite 72 MB, overlord.sqlite 60 MB).** Part 2 moves them out; this PR does not touch them. |
| Cluster job router (placement of test, lint, build jobs; reads `HEAVY_LOCK_PY`) | `node/cluster_route.py`, `node/cluster_targets.json` (PRs 103, 99, 109) | Merged or draft. Part 2 reuses its heavy-lock functions. |
| **Inventory of every drive and device (this PR)** | `node/cluster_inventory.py`, `node/cluster_inventory_targets.json`, `tests/test_cluster_inventory.py` | Built and run on the real cluster: see "Result". |
| **Heavy-lock rules for the file index (this PR)** | `node/cluster_scan_slot.py`, `tests/test_cluster_scan_slot.py` | Built, tested with a fake lock. Nothing starts a scan yet. |
| File index, search, smart tags, dedupe report, condense proposal | not built | Parts 2 to 6, below. |

Why the Connect disk map was not simply reused: it is a Windows PowerShell tool whose output is a folder tree for a window, with the machine list typed inside `machines.json` on GREYWOLF, and it has no MSI, no R610, no R710 #2, no VM disks or container mounts, and no "unknown" state for a machine it could not reach. The inventory below is the flat, machine-readable layer under it.

## Part 1: the inventory

`python node/cluster_inventory.py collect` reads, over the existing ssh routes, one fixed script per machine and writes `inventory.json`, `inventory.csv` and `INVENTORY.md` (default `F:\novah\cluster-files\inventory\`, outside git: they carry serial numbers and the layout of the owner's disks; the repo holds only code, a synthetic-fixture test and this note). `render --raw-dir` re-parses recorded answers without touching a machine.

Row: `machine, kind, device, parent, mount, size, used, free, fs, label, model, serial, transport, state, status, last_seen, source, note`. Kinds: `disk`, `partition`, `volume` (LVM and device-mapper), `filesystem` (Windows drive letter), `network-mount` (NFS, CIFS, mapped drive), `cloud-drive` (Google Drive's virtual disk, not a local disk), `zpool`, `zfs-dataset`, `lvm-vg`, `lvm-lv`, `storage-pool` (Proxmox `pvesm`), `vm-disk` (from the guest config, with thin-LV usage), `ct-mount` (container rootfs and mount points), `machine` (the placeholder for an unreadable machine).

What each machine is asked (all read-only, no install, no write): Linux `lsblk -J`, `df -PkT`, `zpool list`, `zfs list`, `vgs`, `lvs`, `pvesm status`, `qm list`, `pct list`, and only the disk and name lines of `/etc/pve/qemu-server/*.conf` and `/etc/pve/lxc/*.conf` (an awk filter, so a `cipassword`, ssh key or network line is never read). Windows one PowerShell read: `Win32_DiskDrive`, `Win32_LogicalDisk`, `Get-Partition`. A test asserts the script contains no write verb.

### The rules that keep it honest (all tested)
- A machine that cannot be read is `unknown` with the reason. It is never empty: the last-known rows from the previous `inventory.json` are kept as `stale` with their own old `last_seen`, or, with no history, one `machine` row says `unknown`. A placeholder is never carried forward as if it were a reading.
- A section that fails on a reachable machine (non-zero rc, or output cut off) makes the machine `partial`; that section's last-known rows are carried as `stale`. A tool that is not installed (rc 127, for example `zpool`) is `absent`, a fact and not a failure. A reachable machine that returns no rows at all is `unknown`, not `verified`.
- A size nobody reported is `null`, never 0; an unmounted filesystem has no `used`. Thin-LV usage is `size * data_percent`.
- Transport is ssh `BatchMode` and only to loopback, RFC 1918 or tailnet addresses (an alias is resolved with `ssh -G` first); anything else is refused and nothing is sent. The script goes in as bytes on stdin (text mode on Windows turned `\n` into `\r\n` and broke `sh`; found on the first live run).
- No key, password or token is stored anywhere in the targets file.

### Result of the live run, 2026-11-23 Pacific 23:37 (read from GREYWOLF)
8 machines, 155 rows: 5 verified, 0 partial, 3 unknown; 152 rows read now, 0 stale.

| Machine | Status | Rows | How reached |
|---|---|---|---|
| overlord | verified | 69 (5 physical disks, local-lvm, 8 VM disks, 2 CT mounts, the NFS view of the R710 backup) | ssh alias `overlord` |
| r710-1 (pve-ng) | verified | 43 (system disk, 3.6 TB VM disk, 7.3 TB backup disk, 6 VM disks) | ssh, GREYWOLF key |
| r620 | verified | 21 (system disk, 2.7 TB library disk, VM 200) | ssh through overlord with overlord's own key |
| greywolf | verified | 11 (2 NVMe disks, C:, F:, Google Drive as `cloud-drive`) | local PowerShell |
| surface | verified | 8 | ssh `milto@100.102.130.109`, PowerShell |
| r710-2, r610 | **unknown** | 1 each | no route: VLAN 30 lab lockdown (from the 2026-11-05 survey and the 2026-11-21 audit; not re-tried, nothing to try with) |
| msi | **unknown** | 1 | `192.168.1.91` ssh timed out; on a different subnet from the cluster, not on the tailnet |

Method: counts are `len(rows)` per machine in `inventory.json`; the summary line is printed by the tool. Verified means every read section returned rc 0 or `absent` on this run. It does not mean the figures were cross-checked against a second source: the sizes come from lsblk, df, lvs, pvesm and Windows CIM as they answered.

Not in the inventory yet: iDRAC virtual media shows as 0 byte disks on the R710 (kept, as the machine reports them); USB sticks and phones that are not plugged in; the old drives under `/mnt/ro` on overlord appear as unmounted partitions with no `used` (not mounted at read time, so `unknown`); `overlord` VM 106 and the other guests' internal file systems (that is part 2's file index, not a drive).

## Part 2 design: the heavy lock

Rule from the brief: one heavy job at a time estate-wide, `scripts/heavy_lock.py`, nice and low priority, never a full-disk hash on a machine in use during the day. `node/cluster_scan_slot.py` encodes it, so a part 2 scanner cannot skip it:

1. **One slot per machine pass, not per run.** `scan_slot(job)` checks `heavy_lock.py status` (via `cluster_route.heavy_lock_state`), acquires, runs one machine's pass, releases in a `finally`. Between machines the slot is free, so CI and other desks are never starved by an overnight whole-cluster scan. A pass is bounded (a time budget, then it stops and records where it got to) so a slot is not held for hours.
2. **Held, stale or unknown refuses.** The same trust rules as the job router: no `HEAVY_LOCK_PY` is `unknown`, a `heavy_lock.py` that does not read GitHub's runners API is stale and refused, `hub CI: unknown` is refused. The scanner waits and re-asks; it never proceeds "anyway".
3. **Who may be scanned when.** `scan.in_use` in the targets file: GREYWOLF, SURFACE and the MSI are the owner's, heavy passes only 22:00 to 08:00 Pacific; the servers any time. A machine with no declared policy counts as in use. The R620 also hosts the Postgres standby: part 2 runs `cluster_route`'s standby guard (skip when load is at or above half, a refresh is running, or its state cannot be read) before it hashes there.
4. **Throttle on the machine that does the work.** The hash and the walk run on the machine that owns the disk (so file bytes never cross the 1 Gb link just to be hashed): `nice -n 19 ionice -c3` on Linux, Idle priority on Windows. Only the small result rows cross the network (path, size, mtime, hash).
5. **Order and sizing.** One machine at a time. First the pilot (GREYWOLF `F:\` minus the repos, at night), measure files per second and bytes per second and the index size, then the R710 #1 (7.3 TB, the largest and the canonical store), the R620, overlord's old SSDs, SURFACE, the MSI after its backup is verified. A machine whose scan did not finish says `partial` with the last path done and is resumed, never reported complete.
6. **Never during an ingest.** Reuse the Connect guard: if a storage-desk `ingest-*` systemd unit is active on overlord (read-only `systemctl`), or the check cannot be made, the 710's `overlord-dumps` subtree is `unknown`, not walked.

## Parts 2 to 6, in order (not built)

2. **File index**: one SQLite or DuckDB file outside git (on the R710 #1, `/mnt/backup/cluster-index/`, not in the vault), a small tracked README with its location. Incremental by (machine, path, size, mtime): re-hash only what changed. Hash streamed and throttled under the slot above; text and document extracts local only. Privacy tiers (health, financial, credentials) are listed by folder name and size and are never content-indexed into a shared search without the owner's yes. The book at `F:\repos\resonance` is its own source.
3. **Search**: a page and a CLI in the home-node app over that file; every answer shows the real path and the machine; a machine or folder not indexed yet answers `not indexed yet`, never zero results.
4. **Smart indexing**: rule tags first (extension, location, git repo), then the local model stack (Ollama or Hermes) for the leftovers; every tag stores its source (rule or model) and confidence. No cloud embedding, ever; a step that cannot run locally stops.
5. **Dedupe report**: exact duplicates by hash, grouped, ranked by reclaimable space, a proposed canonical copy per group (most durable location, oldest mtime, inside a git repo), a click-through page (Keep canonical, Keep both, Decide later). The report moves nothing. A later, separate, gated step applies his clicks by moving to a quarantine folder (reversible for 30 days), never deleting.
6. **Condense**: a proposed folder structure per source. Proposal only.

## OWNER-STEPs found

- The MSI is not reachable (a different subnet, off the tailnet). To inventory it, it must be on the cluster network or the tailnet with ssh on, or the owner runs the same read on it. Until then it is `unknown`.
- The R710 #2 and the R610 are behind the VLAN 30 lockdown. Opening a read route is a firewall decision (not this desk's; the R710 firewall belongs to the fleet desk).
- Moving the four tracked sqlite files out of the vault repo is a change in `F:\Claude Sessions`; it belongs to the desk that owns that repo's hygiene.
