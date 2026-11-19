# HANDOFF: NODE · overlord storage part · 1 (2026-11-18, 300k cap)

Me: local_24043a3a-a165-47da-b633-0f662496141f. Lane NODE, group NODE. No router (owner-driven). Full private note: F:\Claude Sessions\handoff\node-overlord-storage\NODE-overlord-storage-part-001-handoff-2026-11-18.md (not pushed; scripts in its `scripts` folder).

**Done:** answered overlord's M.2 question (second socket looks free); owner's 2 TB personal backup drive needs a bit-for-bit image plus a second verified copy before anything is wiped; measured the path (710 disk ~175 MB/s, one gigabit line ~100 MB/s, SSK came up at USB 2); built a dedicated storage VLAN on the Cisco (running config only, not saved) and cabled overlord and the 710 into it.

**State (verified this turn, re-read before acting):** the drive is NOT attached; nothing copied; backup folder on the 710 store is empty. Runtime-only addresses on overlord's free port and the 710's port 2; no config file changed. Cisco change is unsaved.

**Open problem:** over the new link the 710 receives frames but sends nothing back (nic1 TX +0), so ping and ssh fail. Not diagnosed; checks listed in the private note.

**Next:** diagnose on the 710 (tcpdump, policy routing, firewall); when the link works, owner re-enables the Cisco and I run `write memory`; persist interfaces; build the `ingest` tool; on plug-in lock the drive read-only by hand first (the udev rule does not work) and check the USB link is 5000M or more.

**Owed:** owner types the Cisco enable password again; re-plug the SSK on a USB 3 cable; decision after two verified copies on whether the card becomes overlord's landing pool. I made no power action and nothing left the machine.

**Gotchas:** say "710", not pve-ng; use `ssh -n` inside heredocs; udev cannot set read-only; never `ifreload -a` on overlord (firewall host).
