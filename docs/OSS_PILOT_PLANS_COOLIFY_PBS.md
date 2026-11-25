# Open-source pilot plans: Coolify for the deployer (oss-1), Proxmox Backup Server for VM backups (oss-5)

Desk NODE, part 203, 2026-11-23 Pacific. Both are class B, "desk proceeds, plan-only first step". **Plans only. Nothing is downloaded, installed or changed.** Source for both rows: `OPEN-SOURCE.md` "pull sooner" ranks 1 and 5 (NODE part 13 handoff folder, written 2026-11-21).

## oss-1: Coolify as the deployer, pilot on the suite VM

**First step as queued:** after U09 (pick the always-on guest VM) and P03 (copy the hub database home and prove it), write a one-page plan to run the hub and the MCP from Coolify on the suite VM.

**Gate check:** both predecessors are open items in the queue (U09 needs the owner's pick of the VM; P03's done-when is a restore proved on VM 200). A plan can be written now; running anything cannot start before they close. I did not re-verify their state beyond the queue text.

### Plan
1. **Where:** the one always-on guest VM that U09 picks (the vault plan names VM 103 on overlord as the data home; the pilot VM must not be the vault). Coolify runs there as its own container set.
2. **What it deploys first:** a *copy* of the hub from our own repo into a staging app named `hub-pilot`, never the production service. Production stays on Railway until P03 is proved and the owner says cut over.
3. **Source:** pulls only from our own repositories, over a deploy key kept on that VM and never printed in a log.
4. **Telemetry:** read Coolify's settings before first start and switch off any usage reporting and update check that phones home. Record what the page said and what the process opened (`ss -tnp` on the VM) in the pilot note. The catalogue says telemetry is *unstated*, so this check is part of the pilot, not an assumption.
5. **Exposure:** no public tunnel, no port forward, no DNS change. The dashboard binds to the LAN address only. The hub-pilot URL is LAN-only.
6. **Backups:** the VM is in the vault-style `vzdump` job class before the pilot starts, and the Coolify data directory is on that VM's disk.
7. **Pass criteria:** hub-pilot builds from `main`, starts, answers its health route from a LAN machine, and a rollback to the previous build works. Fail criteria: any outbound connection to a host we did not name.

### Stays the owner's
Any public tunnel, port or DNS change. Any use of production secrets (the pilot uses a test configuration; a secret on a hosted runner is a Law 9 problem too).

OWNER-STEP: pick the pilot VM (U09) and say go for downloading Coolify there | blocks: step 1 of the pilot (the install is a download).

## oss-5: Proxmox Backup Server with restic (pilot first)

**First step as queued:** confirm what the vault nightly uses (P07), then plan a PBS target for whole-VM backups.

### What the vault nightly uses (read from the plan, not from the box)
`/f/novah/always-on/VAULT-001-fitted-to-estate-plan.md` records a separate Proxmox job `vault-nightly` at 02:15 to storage `r710-backup` (keep 7 daily, 4 weekly), made with `pvesh create /cluster/backup` (a `vzdump` job), plus a nightly restic or rsync from inside the VM. One test backup of 356 MB succeeded. **That is a plan note; P07's own done-when ("the Nov 22 run's log read after 03:15 PT") is a separate check that needs the Proxmox host, and I did not do it.** So "what it uses" is: vzdump whole-VM archives to a directory-style storage on the R710, no deduplication.

### Plan
1. **Why PBS:** vzdump to a plain storage stores a full archive per run; PBS stores deduplicated chunks, so 7 daily and 4 weekly copies cost far less and an incremental run is quick.
2. **Where:** a PBS guest on the R710 (it already holds `r710-backup`), with its datastore on that disk. LAN only.
3. **Add, do not replace:** keep the working `vault-nightly` job unchanged. Add a second job pointing at the PBS datastore for the same VMs. Do not retire the old job before a **restore from PBS is proven** by restoring a VM to a scratch ID and booting it.
4. **restic stays for files** (the in-VM file copy); PBS is for whole VMs.
5. **No cloud target.** A Backblaze or any off-site datastore is a separate decision behind the approval gate; this plan names none.
6. **Pilot size:** one small VM first, then VM 200 (the Postgres standby) only after the restore test passes.
7. **Pass criteria:** a restored scratch VM boots and its data check passes; storage used by the PBS copy is measured against the vzdump copy.

OWNER-STEP: say go for downloading the PBS installer onto the R710 | blocks: the PBS pilot (it is a download and a Proxmox change on a host he owns).
