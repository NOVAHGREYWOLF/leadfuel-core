"""NODE lab plans: render (never run) the shell scripts for six home-lab chores:
machines-6, P08, P14, desks-1-9, W09, machines-8.

Design rules (Law 9 and the no-delete rule):
  * PLAN ONLY. This module prints a script for a person to run on the named host.
    It opens no connection and runs nothing.
  * NO REAL HOST DATA IN THIS REPO. Addresses, ssh logins, aliases, VM ids and paths come from
    a local, git-ignored JSON file (default node/lab_hosts.local.json, or --hosts PATH). Without
    one, the CLI refuses unless --placeholders is given, and then every value is an obvious
    placeholder (10.0.0.x, VM 90x) and the script says so in its header. Format: docs/NODE_LAB_PLANS.md.
  * ALLOWLIST, NOT DENYLIST. Every command is rendered from one of the exact shapes in SHAPES,
    whose slots accept only a narrow character set (no spaces, quotes, $, ;, |, &, <, >).
    assert_safe() accepts a command only if it is exactly one shape with valid slot values, so a
    quoted, re-spaced or variable-built verb matches nothing and is refused.
  * LAN only: every host slot, and every IPv4 literal anywhere in a command, must be loopback,
    RFC 1918 or tailnet; a name must be a listed ssh alias.
  * Some shapes are GATED-ONLY (standing config, long copies, the one scratch-VM destroy): they
    are only accepted as GATED steps, which render commented out.
  * A check that cannot establish a state prints UNKNOWN and exits 1. Guards never rely on
    `set -e` around `!`, a pipeline or an `&&` list, because errexit ignores all three.
"""
from __future__ import annotations

import argparse
import copy
import ipaddress
import json
import os
import re
import sys

TAILNET = ipaddress.ip_network("100.64.0.0/10")
LAN = [ipaddress.ip_network(n) for n in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "127.0.0.0/8")]
DEFAULT_CONFIG = os.path.join(os.path.dirname(os.path.abspath(__file__)), "lab_hosts.local.json")

# Placeholders only. Real values live in the git-ignored local file.
PLACEHOLDERS = {
    "hosts": {"proxmox": "root@10.0.0.10", "backup": "root@10.0.0.11", "library": "root@10.0.0.12",
              "ci_vm": "root@10.0.0.13"},
    "aliases": [],
    "ids": {"ci_vm": 902, "restore_vm": 901, "gpu_ct": 905},
    "paths": {"backup_root": "/mnt/backup", "pve_storage": "backup-store", "pve_mount": "/mnt/pve/backup-store",
              "library_root": "/srv/library", "opt_root": "/opt", "opt_folders": ["export-a", "export-b"],
              "busy_pattern": "ingest-chain", "salvage_disk": "/dev/sdz",
              "surface_home": "C:\\Users\\<user>"},
}


class Refused(ValueError):
    pass


# ---------- slot types: each value must fullmatch, and the charset never includes shell syntax ----------
_IPV4 = r"\d{1,3}(?:\.\d{1,3}){3}"
SLOT_TYPES = {
    "HOST": (r"(?:[a-z_][a-z0-9_-]{0,31}@)?(?:[a-z][a-z0-9-]{0,62}|" + _IPV4 + r")", None),
    "PATH": (r"/[A-Za-z0-9._/-]{0,200}", lambda v: ".." not in v and not v.startswith("/dev/") and "//" not in v),
    "DEV": (r"/dev/(?:sd[a-z]|nvme\d{1,2}n\d{1,2})", None),
    "INT": (r"[0-9]{1,6}", None),
    "VMID": (r"[1-9][0-9]{2,8}", None),
    "SCRATCH": (r"91[0-9]{2}", None),
    "NAME": (r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}", None),
    "NAMES": (r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}(?: [A-Za-z0-9][A-Za-z0-9._-]{0,63}){0,15}", None),
    "VOLID": (r"[A-Za-z0-9][A-Za-z0-9._:/-]{0,200}", lambda v: ".." not in v),
}
SLOTS = {  # slot name -> type
    "src": "HOST", "dst": "HOST",
    "tarf": "PATH", "dir": "PATH", "root": "PATH", "lst": "PATH", "out": "PATH", "mnt": "PATH", "file": "PATH",
    "dev": "DEV", "need": "INT", "days": "INT", "mem": "INT", "vmid": "VMID", "ct": "VMID", "scratch": "SCRATCH",
    "storage": "NAME", "proc": "NAME", "folders": "NAMES", "archive": "VOLID",
}
DATE_RX = re.compile(r"\d{4}-\d{2}-\d{2}|\d{8}|DATE")   # DATE is the unfilled placeholder

# ---------- the allowlist: (shape, gated_only) ----------
_SPACE = ('A=$(ssh <<dst>> df --output=avail -B1G <<dir>> | tail -n 1 | tr -d " ")\n'
          'case "$A" in ""|*[!0-9]*) echo "UNKNOWN: free space not readable (got \'$A\')"; exit 1;; esac\n'
          '[ "$A" -ge <<need>> ] || { echo "NOT ENOUGH SPACE: ${A}G free, need <<need>>G"; exit 1; }')
_SPACE_LOCAL = _SPACE.replace("ssh <<dst>> ", "")
SHAPES = {
    "busy-check": ('rc=0; pgrep -f <<proc>> >/dev/null || rc=$?\n'
                   '[ "$rc" -eq 1 ] || { echo "BUSY-or-UNKNOWN: pgrep rc=$rc for <<proc>>"; exit 1; }', False),
    "space-remote": (_SPACE, False),
    "space-local": (_SPACE_LOCAL, False),
    "no-overwrite": ('rc=0; ssh <<dst>> test -e <<tarf>> || rc=$?\n'
                     '[ "$rc" -eq 1 ] || { echo "EXISTS-or-UNKNOWN: test -e rc=$rc, refusing to overwrite"; exit 1; }',
                     False),
    "tar-stream": ("ssh <<src>> 'tar -C <<root>> -cf - <<folders>>' | ssh <<dst>> 'set -C; cat > <<tarf>>'", False),
    "sha-both": ("A=$(ssh <<src>> 'tar -C <<root>> -cf - <<folders>> | sha256sum' | cut -d' ' -f1)\n"
                 "B=$(ssh <<dst>> sha256sum <<tarf>> | cut -d' ' -f1)\n"
                 'if [ "${#A}" -eq 64 ] && [ "$A" = "$B" ]; then echo "MATCH $A"; '
                 'else echo "MISMATCH-or-UNKNOWN src=$A dst=$B"; exit 1; fi', False),
    "tar-list": ("ssh <<dst>> tar -tf <<tarf>> >/dev/null || { echo 'UNREADABLE archive'; exit 1; }\n"
                 'echo "entries: $(ssh <<dst>> tar -tf <<tarf>> | wc -l)"', False),
    "vzdump-job": ("pvesh create /cluster/backup --vmid <<vmid>> --storage <<storage>> --schedule 'sun 03:30' "
                   "--mode snapshot --compress zstd --enabled 1", True),
    "usage": ("U=$(df -P <<root>> | tail -n 1 | awk '{print $5}')\n"
              'case "$U" in *%) echo "usage $U";; *) echo "UNKNOWN: df gave \'$U\'"; exit 1;; esac', False),
    "cold-list": ("find <<root>> -xdev -type f -mtime +<<days>> -print0 > <<lst>>", False),
    "dry-run": ("rsync -a --checksum --dry-run --itemize-changes --from0 --files-from=<<lst>> / "
                "<<dst>>:<<dir>>/ > <<lst>>.dry\ntail -n 20 <<lst>>.dry", False),
    "rsync-copy": ("rsync -a --checksum --from0 --files-from=<<lst>> / <<dst>>:<<dir>>/", True),
    "hash-candidates": ("xargs -0 sha256sum < <<lst>> > <<lst>>.src.raw\n"
                        "sort <<lst>>.src.raw > <<lst>>.src.sha\n"
                        "ssh <<dst>> 'cd <<dir>> && find . -type f -print0 | xargs -0 sha256sum' > <<lst>>.dst.raw\n"
                        "sed 's# \\./# /#' <<lst>>.dst.raw | sort > <<lst>>.dst.sha\n"
                        "comm -12 <<lst>>.src.sha <<lst>>.dst.sha > <<lst>>.candidates\n"
                        'echo "CANDIDATES (hash matches both ends, never removed here): '
                        '$(wc -l < <<lst>>.candidates) in <<lst>>.candidates"', False),
    "smart": ("smartctl -a <<dev>> | head -n 60   # informational: smartctl's status is ignored on purpose", False),
    "setro": ("blockdev --setro <<dev>>\n"
              'RO=$(blockdev --getro <<dev>>)\n'
              '[ "$RO" = 1 ] || { echo "NOT READ-ONLY: getro=$RO"; exit 1; }', False),
    "mounted": ("mountpoint -q <<mnt>> || { echo 'UNKNOWN: <<mnt>> is not mounted'; exit 1; }\nmkdir -p <<out>>", False),
    "ddrescue-1": ("ddrescue -n -b4096 <<dev>> <<out>>/disk.raw <<out>>/disk.map", True),
    "ddrescue-2": ("ddrescue -r2 -b4096 <<dev>> <<out>>/disk.raw <<out>>/disk.map", True),
    "hash-image": ("cd <<out>>\nsha256sum disk.raw > SHA256.txt\ncat SHA256.txt", False),
    "task-logs": ("L=$(ls -1t /var/log/pve/tasks/*/*vzdump* 2>/dev/null | head -n 3)\n"
                  "[ -n \"$L\" ] || { echo 'UNKNOWN: no vzdump task logs found'; exit 1; }\n"
                  'for f in $L; do echo "== $f"; tail -n 5 "$f"; done', False),
    "storage-online": ("S=$(pvesm status --storage <<storage>> 2>/dev/null | awk 'NR==2 {print $3}')\n"
                       '[ "$S" = active ] || { echo "UNKNOWN-or-OFFLINE: storage <<storage>> status \'$S\'"; exit 1; }',
                       False),
    "backups-present": ("pvesm list <<storage>> --vmid <<vmid>>", False),
    "id-free": ("pvesh get /cluster/nextid --vmid <<scratch>> >/dev/null || "
                "{ echo 'IN-USE-or-UNKNOWN: id <<scratch>>'; exit 1; }", False),
    "restore": ("qmrestore <<archive>> <<scratch>> --storage <<storage>> --unique 1", False),
    "links-down": ("for n in $(qm config <<scratch>> | sed -n 's/^\\(net[0-9]*\\):.*/\\1/p'); do "
                   "qm set <<scratch>> --$n \"$(qm config <<scratch>> | sed -n \"s/^$n: //p\"),link_down=1\"; done\n"
                   "C=$(qm config <<scratch>>)\n"
                   "[ -n \"$C\" ] || { echo 'UNKNOWN: qm config empty'; exit 1; }\n"
                   "if printf '%s\\n' \"$C\" | grep '^net' | grep -qv 'link_down=1'; then "
                   "echo 'A NIC IS STILL UP: not booting'; exit 1; fi", False),
    "boot-check": ("qm start <<scratch>>\nsleep 60\nS=$(qm status <<scratch>>)\n"
                   '[ "$S" = "status: running" ] || { echo "NOT RUNNING: $S"; exit 1; }', False),
    "vm-stop": ("qm stop <<scratch>>", False),
    "destroy-scratch": ("qm destroy <<scratch>> --purge", True),
    "headroom": ("M=$(awk '/^MemAvailable:/ {print int($2/1024)}' /proc/meminfo)\n"
                 'case "$M" in ""|*[!0-9]*) echo "UNKNOWN: MemAvailable not readable"; exit 1;; esac\n'
                 '[ "$M" -ge <<need>> ] || { echo "NO HEADROOM: ${M} MB free, need <<need>> MB"; exit 1; }\n'
                 "pct config <<ct>>", False),
    "ct-cap": ("pct set <<ct>> --memory <<mem>> --swap 0 --onboot 0", False),
    "ct-gpu": ("pct start <<ct>>\nsleep 10\npct exec <<ct>> -- vulkaninfo --summary | head -n 20", False),
    "ct-disk": ("pct exec <<ct>> -- df -h /", False),
    "owner-step": ("echo OWNER-STEP-install-runtime", False),
}
_SLOT_RX = re.compile(r"<<(\w+)>>")


def _compile(shape: str) -> re.Pattern:
    parts, seen, pos = [], set(), 0
    for m in _SLOT_RX.finditer(shape):
        parts.append(re.escape(shape[pos:m.start()]))
        name = m.group(1)
        if name in seen:
            parts.append(f"(?P={name})")
        else:
            seen.add(name)
            parts.append(f"(?P<{name}>{SLOT_TYPES[SLOTS[name]][0]})")
        pos = m.end()
    parts.append(re.escape(shape[pos:]))
    return re.compile("".join(parts))


_COMPILED = {k: (_compile(s), g) for k, (s, g) in SHAPES.items()}


def check_lan(host: str, aliases=()) -> str:
    """host may be user@addr; a name that is not an address must be one of `aliases`."""
    addr = host.split("@")[-1]
    try:
        ip = ipaddress.ip_address(addr)
    except ValueError:
        if addr == "localhost" or addr in aliases:
            return host
        raise Refused(f"{addr!r} is neither a LAN address nor a listed ssh alias")
    if ip in TAILNET or any(ip in n for n in LAN):
        return host
    raise Refused(f"{addr} is not loopback, private or tailnet")


def _check_slot(name: str, value: str, aliases) -> None:
    rx, extra = SLOT_TYPES[SLOTS[name]]
    if not re.fullmatch(rx, value) or (extra and not extra(value)):
        raise Refused(f"slot {name}={value!r} is not a valid {SLOTS[name]}")
    if SLOTS[name] == "HOST":
        check_lan(value, aliases)


def assert_safe(cmd: str, gated: bool = False, aliases=()) -> str:
    """Accept cmd only if it is exactly one allowlisted shape with valid slots (see SHAPES)."""
    for ip in re.findall(r"(?<![\d.])" + _IPV4 + r"(?![\d.])", cmd):
        check_lan(ip)
    for key, (rx, gated_only) in _COMPILED.items():
        m = rx.fullmatch(cmd)
        if not m:
            continue
        try:
            for name, value in m.groupdict().items():
                _check_slot(name, value, aliases)
        except Refused:
            continue
        if gated_only and not gated:
            raise Refused(f"shape {key} is only allowed as a GATED step")
        return cmd
    raise Refused(f"not an allowlisted command shape: {cmd!r}")


def render_shape(key: str, aliases=(), **slots) -> str:
    shape, _ = SHAPES[key]
    names = set(_SLOT_RX.findall(shape))
    if names != set(slots):
        raise Refused(f"shape {key} needs slots {sorted(names)}, got {sorted(slots)}")
    for name, value in slots.items():
        _check_slot(name, str(value), aliases)
    return _SLOT_RX.sub(lambda m: str(slots[m.group(1)]), shape)


def check_date(date: str) -> str:
    if not DATE_RX.fullmatch(date or ""):
        raise Refused(f"--date must be YYYY-MM-DD or YYYYMMDD (digits), got {date!r}")
    return date


def load_config(path: str | None = None, placeholders: bool = False) -> dict:
    """Merge a local host file over the placeholders. Missing file: refuse unless placeholders=True."""
    cfg = copy.deepcopy(PLACEHOLDERS)
    cfg["placeholder"] = True
    path = path or DEFAULT_CONFIG
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            local = json.load(f)
        unknown = set(local) - set(PLACEHOLDERS)
        if unknown:
            raise Refused(f"unknown sections in {os.path.basename(path)}: {sorted(unknown)}")
        for section, val in local.items():
            if isinstance(cfg[section], dict):
                bad = set(val) - set(cfg[section])
                if bad:
                    raise Refused(f"unknown keys in {section}: {sorted(bad)}")
                cfg[section].update(val)
            else:
                cfg[section] = list(val)
        cfg["placeholder"] = False
    elif not placeholders:
        raise Refused(f"no host file at {path}: write one (format in docs/NODE_LAB_PLANS.md) or pass --placeholders")
    for h in cfg["hosts"].values():
        check_lan(h, cfg["aliases"])
    return cfg


class Plan:
    def __init__(self, plan_id: str, host: str, title: str, cfg: dict):
        self.aliases = tuple(cfg["aliases"])
        self.id, self.host, self.title = plan_id, check_lan(host, self.aliases), title
        self.placeholder = cfg.get("placeholder", True)
        self.steps: list[tuple[str, str, bool]] = []   # (note, command, gated)

    def add(self, note: str, shape: str, gated: bool = False, **slots):
        cmd = render_shape(shape, self.aliases, **slots)
        self.steps.append((note, assert_safe(cmd, gated=gated, aliases=self.aliases), gated))
        return self

    def render(self) -> str:
        hosts = ("PLACEHOLDER values (10.0.0.x, VM 90x): NOT runnable as is; write the local host file"
                 if self.placeholder else "from the local host file")
        out = ["#!/bin/sh", f"# {self.id}: {self.title}", f"# RUN ON: {self.host}   (rendered, not executed)",
               f"# HOSTS: {hosts}",
               "# GATED steps are commented out: a person removes the '#' on purpose.", "set -eu", ""]
        for note, cmd, gated in self.steps:
            out.append(f"# {note}")
            out.append("\n".join("# GATED: " + ln for ln in cmd.splitlines()) if gated else cmd)
            out.append("")
        return "\n".join(out)


def _p(cfg):
    return cfg["paths"]


def machines6(date: str, cfg: dict) -> Plan:
    """CI VM data under opt_root to the backup host, verified; vzdump job drafted but GATED."""
    date, h, pa = check_date(date), cfg["hosts"], _p(cfg)
    src, dst, folders = h["ci_vm"], h["backup"], " ".join(pa["opt_folders"])
    tarf = f"{pa['backup_root']}/ci-opt-{date}.tar"
    p = Plan("machines-6", h["proxmox"], "tar the CI VM's data folders to the backup host and verify", cfg)
    p.add("Heavy slot first (estate rule) and the ingest chain must be idle (pgrep rc 1 only)",
          "busy-check", proc=pa["busy_pattern"])
    p.add("Space on the backup host (need about 20 GB free)", "space-remote", dst=dst, dir=pa["backup_root"], need=25)
    p.add("Refuse to overwrite an existing archive (rc 1 = absent; 0 = exists; anything else = unknown)",
          "no-overwrite", dst=dst, tarf=tarf)
    p.add("Stream the folders, read-only on the CI VM; set -C refuses to clobber on the far side",
          "tar-stream", src=src, root=pa["opt_root"], folders=folders, dst=dst, tarf=tarf)
    p.add("sha256 of the stream recomputed on the source side vs the file on the backup host",
          "sha-both", src=src, root=pa["opt_root"], folders=folders, dst=dst, tarf=tarf)
    p.add("List the archive (readable and complete)", "tar-list", dst=dst, tarf=tarf)
    p.add("Vzdump job for the CI VM (Proxmox standing config: draft only)", "vzdump-job", gated=True,
          vmid=cfg["ids"]["ci_vm"], storage=pa["pve_storage"])
    return p


def p08(cfg: dict, cold_days: int = 365, date: str = "DATE") -> Plan:
    """Library disk: copy cold files to the backup host, verify by hash, emit removal CANDIDATES only."""
    date, h, pa = check_date(date), cfg["hosts"], _p(cfg)
    root, dst = pa["library_root"], h["backup"]
    p = Plan("P08", h["library"], f"{root}: copy files untouched {cold_days} days to the backup host, hash-verified", cfg)
    lst = f"/root/p08-cold-{date}.list"
    target = f"{pa['backup_root']}/library/cold-{date}"
    p.add("Usage now (UNKNOWN stops the script)", "usage", root=root)
    p.add("Cold list (read only, null separated)", "cold-list", root=root, days=cold_days, lst=lst)
    p.add("Dry run first", "dry-run", lst=lst, dst=dst, dir=target)
    p.add("Copy (additive: nothing on the source changes)", "rsync-copy", gated=True, lst=lst, dst=dst, dir=target)
    p.add("Hash both ends; list only files whose hashes match: removal CANDIDATES for the owner, never removed here",
          "hash-candidates", lst=lst, dst=dst, dir=target)
    return p


def p14(cfg: dict, date: str = "DATE") -> Plan:
    """Worn disk on the Proxmox host: read-only salvage image to the backup storage. The disk is never written."""
    date, h, pa = check_date(date), cfg["hosts"], _p(cfg)
    dev, mnt = pa["salvage_disk"], pa["pve_mount"]
    out = f"{mnt}/dumps/salvage-{date}"
    p = Plan("P14", h["proxmox"], f"salvage-copy {dev} (read only), keep the disk, no wipe", cfg)
    p.add("Identify the disk and its health (read only)", "smart", dev=dev)
    p.add("Mark the block device read-only for this boot, and prove it", "setro", dev=dev)
    p.add("The backup storage must be mounted, else UNKNOWN stops", "mounted", mnt=mnt, out=out)
    p.add("And it needs room for the image", "space-local", dir=out, need=300)
    p.add("Pass 1 (skip bad areas); the mapfile lets later passes resume; output is a seekable file",
          "ddrescue-1", gated=True, dev=dev, out=out)
    p.add("Pass 2: retry bad areas", "ddrescue-2", gated=True, dev=dev, out=out)
    p.add("Hash the image and record it (fails, and stops, if no image was made)", "hash-image", out=out)
    return p


def desks19(cfg: dict, archive: str = "LATEST", scratch: str = "9101") -> Plan:
    """Restore the firewall VM to a scratch id and boot it WITHOUT network."""
    if not re.fullmatch(SLOT_TYPES["SCRATCH"][0], str(scratch)):
        raise Refused("scratch id must be 9100-9199")
    h, pa, vm = cfg["hosts"], _p(cfg), cfg["ids"]["restore_vm"]
    st = pa["pve_storage"]
    p = Plan("desks-1-9", h["proxmox"], "restore proof from the backup storage, isolated boot", cfg)
    p.add("Last three weekly runs", "task-logs")
    p.add("Is the storage online? UNKNOWN stops", "storage-online", storage=st)
    p.add("Backups present", "backups-present", storage=st, vmid=vm)
    p.add("Scratch id must be free (pvesh errors when it is taken, or when it cannot tell)", "id-free", scratch=scratch)
    p.add("Restore (UNGATED on purpose: creates the scratch VM only, refuses an existing id); --unique regenerates MACs",
          "restore", archive=archive, scratch=scratch, storage=st)
    p.add("The VM has static LAN addresses: every NIC link-down before boot, then prove none is up",
          "links-down", scratch=scratch)
    p.add("Boot (UNGATED on purpose: network is down) and confirm running after 60 s", "boot-check", scratch=scratch)
    p.add("Stop the scratch VM", "vm-stop", scratch=scratch)
    p.add(f"Remove ONLY scratch id {scratch} (the source VM is never touched): a person runs this",
          "destroy-scratch", gated=True, scratch=scratch)
    return p


def w09(cfg: dict, mem_mb: int = 16384) -> Plan:
    h, ct = cfg["hosts"], cfg["ids"]["gpu_ct"]
    p = Plan("W09", h["proxmox"], f"GPU container: reuse, cap memory at {mem_mb} MB, check Vulkan", cfg)
    p.add("Headroom: refuse unless MemAvailable covers the cap plus 2 GB (unreadable is UNKNOWN, not a yes)",
          "headroom", need=mem_mb + 2048, ct=ct)
    p.add("Cap memory, no swap, no onboot (UNGATED on purpose: a reversible container setting; onboot is the owner's)",
          "ct-cap", ct=ct, mem=mem_mb)
    p.add("Start (UNGATED on purpose) and check the GPU is visible", "ct-gpu", ct=ct)
    p.add("Models live on the container's local disk; check free space", "ct-disk", ct=ct)
    p.add("Runtime install is a download: owner step, not in this script", "owner-step")
    return p


def surface_syncthing(cfg: dict, vault_device="<VAULT-DEVICE-ID>", folders=None) -> dict:
    """Send-only folder definitions for Syncthing's REST config (PUT /rest/config/folders/<id>).
    Receiver side must set ignoreDelete so the laptop's auto-filer moves never delete vault copies."""
    home = _p(cfg)["surface_home"]
    folders = folders or [
        ("surface-claude-projects", home + r"\.claude\projects"),
        ("surface-documents", home + r"\Documents"),
        ("surface-downloads", home + r"\Downloads"),
        ("surface-desktop-docs", home + r"\Desktop"),
    ]
    out = [{"id": fid, "label": fid, "path": path, "type": "sendonly", "devices": [{"deviceID": vault_device}],
            "fsWatcherEnabled": True, "ignorePerms": True} for fid, path in folders]
    return {"sender": out,
            "receiver_note": "On the vault, add the same ids as receiveonly (or sendreceive) with ignoreDelete=true, "
                             "path <backup_root>/docs/surface/<id>",
            "phase2_not_included": "OneDrive folders: Files-On-Demand placeholders would download every cloud-only file; "
                                   "check attributes first.",
            "device_id_is_placeholder": vault_device.startswith("<"),
            "hosts_are_placeholders": cfg.get("placeholder", True)}


def main(argv=None, out=sys.stdout) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("plan", choices=["machines-6", "P08", "P14", "desks-1-9", "W09", "machines-8"])
    ap.add_argument("--date", default="DATE", help="YYYY-MM-DD or YYYYMMDD; DATE leaves a placeholder")
    ap.add_argument("--hosts", default=None, help="local host file (default node/lab_hosts.local.json, git-ignored)")
    ap.add_argument("--placeholders", action="store_true", help="render with placeholder hosts when no host file exists")
    a = ap.parse_args(argv)
    try:
        check_date(a.date)
        cfg = load_config(a.hosts, a.placeholders)
        builders = {"machines-6": lambda: machines6(a.date, cfg).render(),
                    "P08": lambda: p08(cfg, date=a.date).render(),
                    "P14": lambda: p14(cfg, a.date).render(), "desks-1-9": lambda: desks19(cfg).render(),
                    "W09": lambda: w09(cfg).render(),
                    "machines-8": lambda: json.dumps(surface_syncthing(cfg), indent=2)}
        text = builders[a.plan]()
    except Refused as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    out.write(text + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
