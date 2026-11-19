# HANDOFF: NODE · overlord storage part · 2 (2026-11-18, 300k cap)

Me: local_6eb9eed6-4051-425b-88c4-c678813d2a7d, nested under part 1 (local_24043a3a-a165-47da-b633-0f662496141f). Lane NODE, group NODE. No router (owner-driven). Private full note: `F:\Claude Sessions\handoff\node-overlord-storage\NODE-overlord-storage-part-002-handoff-2026-11-18.md` (not pushed; scripts in its `scripts` folder).

**Done (verified by me):** the storage link works. The cause was the 710's own Proxmox firewall, not the switch; one accept line added with a backup. Link addresses persisted on both machines. A udev guard now sets every USB disk read-only on plug-in (proven). The `ingest` tool is built and deployed on overlord: sparse image to the 710, per-slice sha256, independent read-back and source re-read, second copy to another machine, a one-flipped-byte check that is caught. Selftest and an 8.6 GB benchmark pass.

**Measured:** send about 93 MB/s, independent read-back about 84 MB/s on the whole pipeline. The 710's CPU (sha256sum 48 MB/s per stream) and ssh, not its disk (158 to 201 MB/s writes), limit it.

**State:** the drive is NOT attached (only the Cruzer stick is). Cisco config still unsaved: the save script and a console tab for the owner are ready, he has not typed the enable password. Predecessor not archived (its Remote Control link blocks it).

**Next:** read the owner's reply and the console tab; optional speed work (Python hashlib on the 710, more read-back streams) only if the drive is not yet plugged; when it is plugged in: `ingest /dev/sdX --name owner-2tb-970evoplus-2026-11-18 --background`, then `ingest copy2` to the 620; nothing wiped without the owner's yes.

**Owed:** owner types the enable password; plugs the drive on a USB 3 cable; later decides wipe-or-keep. Relay about the Postgres restore delivered to `NODE · cluster files part · 1`, unanswered. No power action, nothing left the machine.

**Gotchas:** say "710"; bare `ingest` auto-detects (I started it by accident on the stick, removed cleanly; now needs confirmation); never `ifreload -a` on overlord.
