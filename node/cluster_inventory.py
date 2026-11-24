#!/usr/bin/env python3
"""NODE cluster files, part 1: one machine-readable inventory of every drive and device of the cluster.

Owner, 2026-11-23: "show all drives and devices. all overlords drives and be able to go through
them." This file is that inventory: for every machine, every disk, partition, mounted or network
filesystem, ZFS pool, LVM volume group and logical volume, Proxmox storage pool, VM disk and
container mount, as rows (machine, kind, device, mount, size, used, free, fs, state, status,
last_seen). Output is small JSON, CSV and a plain Markdown page. Nothing is a database and nothing
big is written.

READ ONLY. The collector sends one fixed script of read commands (lsblk, df, zpool list, zfs list,
vgs, lvs, pvesm status, qm list, pct list, and only the disk lines of the guest config files so a
cipassword or a key can never be read) or one fixed PowerShell read (Win32_DiskDrive,
Win32_LogicalDisk, Get-Partition). It mounts, moves, writes and installs nothing, on any machine.
Transport is ssh with BatchMode over the LAN or the tailnet; an address anywhere else is refused.

A CHECK THAT CANNOT SEE ITS SUBJECT MUST NOT REPORT ONE:
  * A machine that cannot be read is `unknown` with the reason, never empty and never zero rows. Its
    last-known rows (from the previous inventory) are kept and marked `stale` with their old
    last_seen, or, when there are none, one placeholder row says `unknown`.
  * A section that failed on a reachable machine (rc not 0) is `unknown` for that section and its
    previous rows are carried as `stale`. A tool that is not installed (rc 127, e.g. zpool on a box
    without ZFS) is `absent`: that is a fact, not a failure.
  * A size, used or free that the machine did not report is null, never 0. A filesystem that is not
    mounted has no `used`.

Usage:
    cluster_inventory.py collect [--targets F] [--only ID,ID] [--previous inventory.json] [--out DIR]
                                 [--raw-dir DIR] [--timeout S]
    cluster_inventory.py render  --raw-dir DIR [--previous ...] [--out DIR]   (re-parse recorded raw)
Outputs in --out: inventory.json, inventory.csv, INVENTORY.md. Stdlib only; tests in
tests/test_cluster_inventory.py. The real outputs go outside git (F:\\novah\\cluster-files\\inventory):
they carry serial numbers and the layout of the owner's disks.
"""
from __future__ import annotations

import argparse
import base64
import csv
import datetime as dt
import ipaddress
import json
import os
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGETS = os.path.join(HERE, "cluster_inventory_targets.json")
TARGETS_SCHEMA = "cluster-inventory-targets-1"
SCHEMA = "cluster-inventory-1"
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=8", "-o", "IdentitiesOnly=yes"]
LAN_NETS = tuple(ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "fc00::/7"))
COLUMNS = ["machine", "kind", "device", "parent", "mount", "size", "used", "free", "fs", "label",
           "model", "serial", "transport", "state", "status", "last_seen", "source", "note"]

# ----------------------------------------------------------------------------- the read scripts
# `sec` runs one command, stderr to /dev/null (so JSON stays JSON), and prints its exit code. A
# missing tool is rc 127 via `command -v`, which the parser reads as `absent`.
LINUX_SCRIPT = r"""
sec() { n=$1; shift; echo "@@BEGIN $n"; if command -v "$1" >/dev/null 2>&1; then "$@" 2>/dev/null; rc=$?; else rc=127; fi; echo "@@END $n rc=$rc"; }
confdisks() { for f in "$1"/*.conf; do [ -f "$f" ] || continue; echo "#FILE $f"; awk '/^\[/{exit} /^(name|hostname|scsi[0-9]+|virtio[0-9]+|sata[0-9]+|ide[0-9]+|efidisk[0-9]+|tpmstate[0-9]+|rootfs|mp[0-9]+):/' "$f"; done; }
echo "@@BEGIN now"; date +%s; echo "@@END now rc=0"
sec lsblk lsblk -b -J -o NAME,KNAME,TYPE,SIZE,FSTYPE,MOUNTPOINT,MODEL,SERIAL,LABEL,RO,ROTA,PKNAME,FSUSED,TRAN,RM
sec df df -PkT
sec zpool zpool list -Hp
sec zfs zfs list -Hp -o name,used,avail,mountpoint
sec vgs vgs --noheadings --separator '|' --units b --nosuffix -o vg_name,vg_size,vg_free
sec lvs lvs --noheadings --separator '|' --units b --nosuffix -o lv_name,vg_name,lv_size,data_percent,pool_lv,lv_attr
sec pvesm pvesm status
sec qm qm list
sec pct pct list
echo "@@BEGIN qmconf"; if [ -d /etc/pve/qemu-server ]; then confdisks /etc/pve/qemu-server; rc=0; else rc=127; fi; echo "@@END qmconf rc=$rc"
echo "@@BEGIN pctconf"; if [ -d /etc/pve/lxc ]; then confdisks /etc/pve/lxc; rc=0; else rc=127; fi; echo "@@END pctconf rc=$rc"
"""

WINDOWS_SCRIPT = r"""
$ErrorActionPreference = 'Stop'
$o = [ordered]@{ now = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds(); errors = [ordered]@{} }
try { $o.disks = @(Get-CimInstance Win32_DiskDrive | ForEach-Object { [ordered]@{ index = $_.Index; model = $_.Model; serial = ($_.SerialNumber -as [string]).Trim(); size = $_.Size; iface = $_.InterfaceType; media = $_.MediaType } }) } catch { $o.errors.disks = $_.Exception.Message }
try { $o.logical = @(Get-CimInstance Win32_LogicalDisk | ForEach-Object { [ordered]@{ id = $_.DeviceID; label = $_.VolumeName; fs = $_.FileSystem; size = $_.Size; free = $_.FreeSpace; type = $_.DriveType; provider = $_.ProviderName } }) } catch { $o.errors.logical = $_.Exception.Message }
try { $o.parts = @(Get-Partition | ForEach-Object { [ordered]@{ disk = $_.DiskNumber; part = $_.PartitionNumber; letter = ($_.DriveLetter -as [string]); size = $_.Size; type = ($_.Type -as [string]) } }) } catch { $o.errors.parts = $_.Exception.Message }
'@@JSON'
$o | ConvertTo-Json -Depth 5 -Compress
'@@ENDJSON'
"""


# ------------------------------------------------------------------------------------- helpers
def now_iso(ts: float | None = None) -> str:
    t = dt.datetime.fromtimestamp(ts, dt.timezone.utc) if ts is not None else dt.datetime.now(dt.timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def to_int(v) -> int | None:
    """An integer, or None. Never 0 for 'not reported'."""
    if v is None:
        return None
    if isinstance(v, bool):
        return None
    if isinstance(v, (int, float)):
        return int(v)
    s = str(v).strip()
    if not s or s == "-":
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


_UNITS = {"K": 1 << 10, "M": 1 << 20, "G": 1 << 30, "T": 1 << 40, "": 1}


def kib(v) -> int | None:
    n = to_int(v)
    return None if n is None else n * 1024


def pve_size(s: str | None) -> int | None:
    """Proxmox sizes ('32G', '512M', '1T') are binary."""
    if not s:
        return None
    m = re.fullmatch(r"(\d+(?:\.\d+)?)([KMGT]?)", s.strip())
    return int(float(m.group(1)) * _UNITS[m.group(2)]) if m else None


def row(machine, kind, device, **kw) -> dict:
    r = {c: None for c in COLUMNS}
    r.update(machine=machine, kind=kind, device=device)
    r.update({k: v for k, v in kw.items() if k in COLUMNS})
    return r


def split_sections(text: str) -> dict[str, dict]:
    """`@@BEGIN n` ... `@@END n rc=N` -> {n: {"rc": N, "text": ...}}. A section with no END (the
    connection died mid-way) is rc None, which reads as unknown."""
    out: dict[str, dict] = {}
    cur, buf = None, []
    for line in text.splitlines():
        if line.startswith("@@BEGIN "):
            cur, buf = line[8:].strip(), []
        elif line.startswith("@@END ") and cur is not None:
            m = re.match(r"@@END (\S+) rc=(\d+)", line)
            out[cur] = {"rc": int(m.group(2)) if m and m.group(1) == cur else None, "text": "\n".join(buf)}
            cur = None
        elif cur is not None:
            buf.append(line)
    if cur is not None:
        out[cur] = {"rc": None, "text": "\n".join(buf)}
    return out


# ------------------------------------------------------------------------------- linux parsers
def parse_lsblk(text: str, machine: str, df: dict[str, dict]) -> list[dict]:
    """`df` maps a mount point to its df row so used/free come from the file system itself."""
    data = json.loads(text)
    rows: list[dict] = []
    seen: set[str] = set()

    def walk(node, parent):
        typ = node.get("type")
        if typ in ("loop", "rom"):
            return
        name = node.get("name")
        if name in seen:   # lsblk repeats a device under each parent (an LVM thin pool, a RAID)
            return
        seen.add(name)
        mount = node.get("mountpoint")
        d = df.get(mount) if mount and mount != "[SWAP]" else None
        fs = node.get("fstype") or ("swap" if mount == "[SWAP]" else None)
        used = to_int(d["used"]) if d else to_int(node.get("fsused"))
        free = to_int(d["free"]) if d else None
        kind = "disk" if typ == "disk" else "partition" if typ == "part" else "volume"
        tran = node.get("tran")
        if tran is None and typ == "disk" and node.get("rm") not in (None, False):
            tran = "removable"
        rows.append(row(
            machine, kind, "/dev/" + str(name), parent=("/dev/" + parent) if parent else None,
            mount=mount, size=to_int(node.get("size")), used=used, free=free, fs=fs,
            label=node.get("label"), model=(node.get("model") or "").strip() or None,
            serial=node.get("serial"), transport=tran,
            state="read-only" if node.get("ro") in (True, 1, "1") else None, source="lsblk",
            note=(f"media={'hdd' if node.get('rota') in (True, 1, '1') else 'ssd'}" if typ == "disk" else None)))
        for c in node.get("children") or []:
            walk(c, name)

    for n in data.get("blockdevices") or []:
        walk(n, None)
    return rows


NETWORK_FS = {"nfs", "nfs4", "cifs", "smb3", "smbfs", "fuse.sshfs", "9p", "virtiofs", "ceph", "glusterfs"}


def parse_df(text: str) -> list[dict]:
    """df -PkT -> [{fs, type, size, used, free, mount}] with sizes in bytes."""
    out = []
    for line in text.splitlines()[1:]:
        p = line.split(None, 6)
        if len(p) < 7:
            continue
        out.append({"source": p[0], "type": p[1], "size": kib(p[2]), "used": kib(p[3]),
                    "free": kib(p[4]), "mount": p[6].strip()})
    return out


def df_by_mount(df_rows: list[dict]) -> dict[str, dict]:
    return {r["mount"]: r for r in df_rows}


def parse_network_mounts(df_rows: list[dict], machine: str) -> list[dict]:
    return [row(machine, "network-mount", r["source"], mount=r["mount"], size=r["size"], used=r["used"],
                free=r["free"], fs=r["type"], source="df") for r in df_rows if r["type"] in NETWORK_FS]


def parse_zpool(text: str, machine: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        p = line.split("\t") if "\t" in line else line.split()
        if len(p) < 10:
            continue
        rows.append(row(machine, "zpool", p[0], size=to_int(p[1]), used=to_int(p[2]), free=to_int(p[3]),
                        fs="zfs", state=p[9], source="zpool"))
    return rows


def parse_zfs(text: str, machine: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        p = line.split("\t") if "\t" in line else line.split()
        if len(p) < 4:
            continue
        used, avail = to_int(p[1]), to_int(p[2])
        rows.append(row(machine, "zfs-dataset", p[0], mount=None if p[3] in ("-", "none", "legacy") else p[3],
                        size=(used + avail) if used is not None and avail is not None else None,
                        used=used, free=avail, fs="zfs", source="zfs"))
    return rows


def _pipe_rows(text: str) -> list[list[str]]:
    return [[c.strip() for c in line.split("|")] for line in text.splitlines() if line.strip()]


def parse_vgs(text: str, machine: str) -> list[dict]:
    rows = []
    for p in _pipe_rows(text):
        if len(p) < 3:
            continue
        size, free = to_int(p[1]), to_int(p[2])
        rows.append(row(machine, "lvm-vg", p[0], size=size, free=free,
                        used=(size - free) if size is not None and free is not None else None,
                        fs="lvm", source="vgs"))
    return rows


def parse_lvs(text: str, machine: str) -> list[dict]:
    """A thin volume's `used` is what it has allocated (size * data_percent), a plain volume's is
    unknown here (the file system knows; lsblk/df carry it)."""
    rows = []
    for p in _pipe_rows(text):
        if len(p) < 6:
            continue
        size = to_int(p[2])
        pct = None
        try:
            pct = float(p[3]) if p[3] else None
        except ValueError:
            pct = None
        thin = p[5][:1] in ("t", "V") and (p[5][:1] == "t" or p[4] != "")
        used = int(size * pct / 100) if (size is not None and pct is not None) else None
        rows.append(row(machine, "lvm-lv", f"{p[1]}/{p[0]}", parent=p[1], size=size, used=used,
                        free=(size - used) if size is not None and used is not None else None,
                        fs="lvm-thin" if thin else "lvm", source="lvs",
                        note=("thin pool" if p[5][:1] == "t" else f"thin volume in {p[4]}" if p[4] else None)))
    return rows


def parse_pvesm(text: str, machine: str) -> list[dict]:
    rows = []
    for line in text.splitlines()[1:]:
        p = line.split()
        if len(p) < 7:
            continue
        rows.append(row(machine, "storage-pool", p[0], size=kib(p[3]), used=kib(p[4]), free=kib(p[5]),
                        fs=p[1], state=p[2], source="pvesm"))
    return rows


def parse_guest_list(text: str) -> dict[str, dict]:
    """qm list / pct list -> {vmid: {name, status}}. qm: VMID NAME STATUS ...; pct: VMID Status Lock Name."""
    out: dict[str, dict] = {}
    lines = text.splitlines()
    if not lines:
        return out
    head = lines[0].split()
    for line in lines[1:]:
        p = line.split()
        if not p or not p[0].isdigit():
            continue
        if "NAME" in head:
            out[p[0]] = {"name": p[1] if len(p) > 1 else "", "status": p[2] if len(p) > 2 else ""}
        else:  # pct: VMID Status [Lock] Name
            out[p[0]] = {"name": p[-1], "status": p[1] if len(p) > 1 else ""}
    return out


def parse_confdisks(text: str) -> dict[str, dict]:
    """The `#FILE path` blocks -> {vmid: {"name": ..., "lines": [(key, value)]}}."""
    out: dict[str, dict] = {}
    cur = None
    for line in text.splitlines():
        if line.startswith("#FILE "):
            vmid = os.path.basename(line[6:].strip()).rsplit(".", 1)[0]
            cur = out.setdefault(vmid, {"name": "", "lines": []})
        elif cur is not None and ":" in line:
            k, v = line.split(":", 1)
            v = v.strip()
            if k in ("name", "hostname"):
                cur["name"] = v
            else:
                cur["lines"].append((k, v))
    return out


def parse_guest_disks(machine: str, qm: dict, pct: dict, qmconf: dict, pctconf: dict, lv_used: dict) -> list[dict]:
    """VM disks (scsiN, virtioN, sataN, ideN, efidiskN, tpmstateN) and container mounts (rootfs, mpN).
    A CD-ROM or `none` is not a disk. Used comes from the thin LV when the volume is one."""
    rows = []
    for guests, conf, tag in ((qm, qmconf, "vm"), (pct, pctconf, "ct")):
        for vmid in sorted(set(guests) | set(conf), key=int):
            g = guests.get(vmid, {})
            name = g.get("name") or conf.get(vmid, {}).get("name") or ""
            label = f"{tag} {vmid}" + (f" {name}" if name else "")
            for key, val in conf.get(vmid, {}).get("lines", []):
                if val.startswith("none") or "media=cdrom" in val:
                    continue
                first, *opts = val.split(",")
                od = dict(o.split("=", 1) for o in opts if "=" in o)
                size = pve_size(od.get("size"))
                storage, _, vol = first.partition(":") if not first.startswith("/") else ("", "", first)
                used = lv_used.get(vol) if vol else None
                kind = "vm-disk" if tag == "vm" else "ct-mount"
                mount = od.get("mp") if tag == "ct" else None
                note = f"{label} ({g.get('status') or 'status unknown'})"
                if first.startswith("/"):
                    note += "; host path or passthrough device"
                rows.append(row(machine, kind, f"{tag}{vmid}:{key}", parent=storage or None, mount=mount,
                                size=size, used=used,
                                free=(size - used) if size is not None and used is not None else None,
                                label=vol or first, state=g.get("status") or None,
                                source="qmconf" if tag == "vm" else "pctconf", note=note))
    return rows


# ----------------------------------------------------------------------------- windows parsers
def parse_windows(payload: dict, machine: str) -> tuple[list[dict], dict[str, str]]:
    """-> (rows, {section: ok|unknown}). A PowerShell section that raised is in payload.errors."""
    errs = payload.get("errors") or {}
    status = {s: ("unknown" if s in errs or payload.get(s) is None else "ok") for s in ("disks", "logical", "parts")}
    rows: list[dict] = []
    def letter(p):
        v = str(p.get("letter") or "").strip().strip("\x00")
        return v.upper() + ":" if v.isalpha() else None   # a partition without a letter has a blank one

    for d in payload.get("disks") or []:
        rows.append(row(machine, "disk", f"disk{d.get('index')}", size=to_int(d.get("size")),
                        model=d.get("model"), serial=d.get("serial") or None, transport=d.get("iface"),
                        note=d.get("media"), source="disks"))
    for p in payload.get("parts") or []:
        rows.append(row(machine, "partition", f"disk{p.get('disk')}:part{p.get('part')}",
                        parent=f"disk{p.get('disk')}", size=to_int(p.get("size")), mount=letter(p),
                        note=p.get("type"), source="parts"))
    types = {2: "removable", 3: "fixed", 4: "network", 5: "optical", 6: "ram"}
    for l in payload.get("logical") or []:
        t = to_int(l.get("type"))
        size, free = to_int(l.get("size")), to_int(l.get("free"))
        note = types.get(t, f"drive type {t}")
        if l.get("provider"):
            note += f"; {l['provider']}"
        label = l.get("label") or ""
        kind = "network-mount" if t == 4 else "filesystem"
        if t == 3 and ("Google" in label or "@" in label) and (l.get("fs") or "").upper() == "FAT32":
            # Google Drive's virtual drive: a fixed FAT32 disk of a made-up size. Nothing here is local.
            kind, note = "cloud-drive", "cloud drive (virtual size, not a local disk; nothing is read from the cloud)"
        rows.append(row(machine, kind, l.get("id"), mount=l.get("id"), size=size, free=free,
                        used=(size - free) if size is not None and free is not None else None,
                        fs=l.get("fs") or None, label=label or None, source="logical", note=note))
    return rows, status


# ---------------------------------------------------------------------------------- collection
class Unreadable(Exception):
    pass


def check_address(host: str) -> None:
    """Refuse any ssh destination that is not loopback, RFC 1918 or tailnet. A name with no address in
    it (an ssh alias) is checked by `ssh -G` in `resolve_alias`."""
    h = host.rsplit("@", 1)[-1]
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        return
    if not (ip.is_loopback or any(ip in n for n in LAN_NETS)):
        raise Unreadable(f"{h} is not loopback, private or tailnet: refused, nothing sent")


def resolve_alias(host: str, run=subprocess.run) -> None:
    h = host.rsplit("@", 1)[-1]
    try:
        ipaddress.ip_address(h)
        return
    except ValueError:
        pass
    r = run(["ssh", "-G", host], capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise Unreadable(f"ssh alias {host} does not resolve")
    for line in r.stdout.splitlines():
        if line.startswith("hostname "):
            check_address(line.split()[1])
            return
    raise Unreadable(f"ssh alias {host} has no hostname")


def ssh_argv(route: dict, remote_cmd: str) -> list[str]:
    key = route.get("key")
    argv = ["ssh", *SSH_OPTS]
    if key:
        argv += ["-i", os.path.expanduser(key)]
    argv += [route["host"], remote_cmd]
    return argv


def ssh_via_argv(route: dict) -> list[str]:
    """overlord's own key reaches the R620; stdin passes through both hops."""
    inner = ("ssh -o BatchMode=yes -o ConnectTimeout=8 -o IdentitiesOnly=yes -i "
             f"{route['via_key']} {route['host']} sh -s")
    return ["ssh", *SSH_OPTS, route["via"], inner]


def ps_argv(script: str) -> list[str]:
    enc = base64.b64encode(script.encode("utf-16-le")).decode("ascii")
    return ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc]


def fetch(machine: dict, run=subprocess.run, timeout: int = 90) -> str:
    """The raw output of the machine's one read script, or Unreadable(reason)."""
    route = machine["route"]
    kind = route.get("kind")
    if kind == "none":
        raise Unreadable(route.get("reason") or "no route")
    try:
        if kind == "local":
            argv, stdin = ps_argv(WINDOWS_SCRIPT), None
        elif kind == "ssh-via":
            check_address(route["host"])
            resolve_alias(route["via"], run)
            argv, stdin = ssh_via_argv(route), LINUX_SCRIPT
        elif kind == "ssh":
            check_address(route["host"])
            resolve_alias(route["host"], run)
            if machine["os"] == "windows":
                argv, stdin = ssh_argv(route, " ".join(ps_argv(WINDOWS_SCRIPT))), None
            else:
                argv, stdin = ssh_argv(route, "sh -s"), LINUX_SCRIPT
        else:
            raise Unreadable(f"unknown route kind {kind!r}")
        # Bytes both ways: text mode on Windows would turn the script's \n into \r\n and sh would
        # choke on it. No stdin at all is /dev/null, so ssh cannot read this process's terminal.
        kw = {"input": stdin.encode("utf-8")} if stdin is not None else {"stdin": subprocess.DEVNULL}
        r = run(argv, capture_output=True, timeout=timeout, **kw)
    except subprocess.TimeoutExpired:
        raise Unreadable(f"timed out after {timeout}s (unknown, not down)")
    except FileNotFoundError as e:
        raise Unreadable(f"cannot start {e.filename}")
    out, err = _text(r.stdout), _text(r.stderr)
    if r.returncode != 0 and not out.strip():
        lines = err.strip().splitlines()
        tail = next((l for l in reversed(lines) if l and not l.startswith("**")), "no output")
        raise Unreadable(f"ssh/exec rc={r.returncode}: {tail[:160]}")
    return out.replace("\r\n", "\n")


def _text(b) -> str:
    if b is None:
        return ""
    return b if isinstance(b, str) else b.decode("utf-8", errors="replace")


def failed_sources(failed: set[str]) -> set[str]:
    """Section name -> the `source` its rows carry (qm/pct list feed the same rows as their config)."""
    out = set(failed)
    if failed & {"qm", "qmconf"}:
        out.add("qmconf")
    if failed & {"pct", "pctconf"}:
        out.add("pctconf")
    return out


def build_machine(machine: dict, raw: str | None, reason: str | None, prev_rows: list[dict],
                  prev_seen: dict[str, str], read_at: str) -> tuple[list[dict], dict]:
    """Rows and the machine summary for one machine. `raw` None means it could not be read.

    unknown  = nothing was read now (last-known rows are kept as `stale`, or one placeholder row)
    partial  = read, but a section failed (that section's last-known rows are kept as `stale`)
    verified = every section either read or absent (the tool is not installed)"""
    mid = machine["id"]
    summary = {"machine": mid, "role": machine.get("role"), "os": machine.get("os"),
               "status": "unknown", "reason": reason, "last_seen": prev_seen.get(mid), "sections": {}}
    rows: list[dict] = []
    failed: set[str] = set()
    if raw is not None:
        try:
            rows, secs, seen = (_build_windows if machine["os"] == "windows" else _build_linux)(mid, raw)
        except (ValueError, KeyError, TypeError) as e:   # an answer that does not parse is unusable
            raw = None
            summary["reason"] = f"the answer could not be parsed ({type(e).__name__}: {str(e)[:100]})"
        else:
            summary["sections"] = secs
            failed = {s for s, v in secs.items() if v == "unknown"}
            when = now_iso(seen) if seen else read_at
            for r in rows:
                r["status"], r["last_seen"] = "verified", when
            if rows:
                summary["last_seen"] = when
                summary["status"] = "partial" if failed else "verified"
                summary["reason"] = ("sections unreadable: " + ", ".join(sorted(failed))) if failed else None
            else:
                summary["reason"] = ("read, but no rows came back" + (
                    "; sections unreadable: " + ", ".join(sorted(failed)) if failed else ""))
                failed = set(secs)   # nothing was seen: every section is unknown
    carry = failed_sources(failed) if raw is not None else {r.get("source") for r in prev_rows}
    rows += [dict(r, status="stale") for r in prev_rows if r.get("source") in carry]
    if not rows:
        rows = [dict(row(mid, "machine", mid, note=summary["reason"] or "unreadable", source="none"),
                     status="unknown", last_seen=None)]
    summary["rows"] = len(rows)
    summary["rows_verified"] = sum(1 for r in rows if r["status"] == "verified")
    return rows, summary

def _sec_status(sections: dict[str, dict], name: str) -> str:
    s = sections.get(name)
    if s is None or s["rc"] is None:
        return "unknown"
    if s["rc"] == 127:
        return "absent"
    return "ok" if s["rc"] == 0 else "unknown"


def _build_linux(mid: str, raw: str):
    sec = split_sections(raw)
    secs = {n: _sec_status(sec, n) for n in
            ("lsblk", "df", "zpool", "zfs", "vgs", "lvs", "pvesm", "qm", "pct", "qmconf", "pctconf")}
    seen = None
    if sec.get("now", {}).get("rc") == 0:
        seen = to_int(sec["now"]["text"].strip())
    ok = lambda n: secs[n] == "ok"   # noqa: E731
    df_rows = parse_df(sec["df"]["text"]) if ok("df") else []
    rows: list[dict] = []
    if ok("lsblk"):
        rows += parse_lsblk(sec["lsblk"]["text"], mid, df_by_mount(df_rows))
    rows += parse_network_mounts(df_rows, mid)
    if ok("zpool"):
        rows += parse_zpool(sec["zpool"]["text"], mid)
    if ok("zfs"):
        rows += parse_zfs(sec["zfs"]["text"], mid)
    if ok("vgs"):
        rows += parse_vgs(sec["vgs"]["text"], mid)
    lvs_rows: list[dict] = []
    if ok("lvs"):
        lvs_rows = parse_lvs(sec["lvs"]["text"], mid)
        rows += lvs_rows
    if ok("pvesm"):
        rows += parse_pvesm(sec["pvesm"]["text"], mid)
    lv_used = {r["device"].split("/", 1)[1]: r["used"] for r in lvs_rows if r["used"] is not None}
    rows += parse_guest_disks(
        mid,
        parse_guest_list(sec["qm"]["text"]) if ok("qm") else {},
        parse_guest_list(sec["pct"]["text"]) if ok("pct") else {},
        parse_confdisks(sec["qmconf"]["text"]) if ok("qmconf") else {},
        parse_confdisks(sec["pctconf"]["text"]) if ok("pctconf") else {}, lv_used)
    return rows, secs, seen


def _build_windows(mid: str, raw: str):
    m = re.search(r"@@JSON\s*(\{.*\})\s*@@ENDJSON", raw, re.S)
    if not m:
        raise ValueError("no @@JSON block")
    payload = json.loads(m.group(1))
    rows, secs = parse_windows(payload, mid)
    return rows, secs, to_int(payload.get("now"))


# --------------------------------------------------------------------------------- the inventory
def load_targets(path: str) -> list[dict]:
    with open(path, encoding="utf-8-sig") as fh:
        d = json.load(fh)
    if d.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"{path}: schema must be {TARGETS_SCHEMA}")
    ids = [m["id"] for m in d["machines"]]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate machine id")
    return d["machines"]


def load_previous(path: str | None) -> tuple[dict[str, list[dict]], dict[str, str]]:
    if not path or not os.path.isfile(path):
        return {}, {}
    with open(path, encoding="utf-8") as fh:
        d = json.load(fh)
    by: dict[str, list[dict]] = {}
    for r in d.get("rows", []):
        if r.get("status") == "unknown" and r.get("kind") == "machine":
            continue   # a placeholder is not a reading
        by.setdefault(r["machine"], []).append(r)
    seen = {m["machine"]: m.get("last_seen") for m in d.get("machines", []) if m.get("last_seen")}
    return by, seen


def make_inventory(machines: list[dict], raws: dict[str, str | None], reasons: dict[str, str | None],
                   previous: str | None = None, read_at: str | None = None) -> dict:
    read_at = read_at or now_iso()
    prev_rows, prev_seen = load_previous(previous)
    all_rows, summaries = [], []
    for m in machines:
        mid = m["id"]
        rows, s = build_machine(m, raws.get(mid), reasons.get(mid), prev_rows.get(mid, []), prev_seen, read_at)
        all_rows += rows
        summaries.append(s)
    counts = {"machines": len(summaries)}
    for st in ("verified", "partial", "unknown"):
        counts[st] = sum(1 for s in summaries if s["status"] == st)
    counts["rows"] = len(all_rows)
    counts["rows_verified"] = sum(1 for r in all_rows if r["status"] == "verified")
    counts["rows_stale"] = sum(1 for r in all_rows if r["status"] == "stale")
    return {"schema": SCHEMA, "generated": read_at, "counts": counts, "machines": summaries, "rows": all_rows}


def collect(machines: list[dict], run=subprocess.run, timeout: int = 90, raw_dir: str | None = None):
    raws: dict[str, str | None] = {}
    reasons: dict[str, str | None] = {}
    for m in machines:
        try:
            raws[m["id"]], reasons[m["id"]] = fetch(m, run, timeout), None
        except Unreadable as e:
            raws[m["id"]], reasons[m["id"]] = None, str(e)
        if raw_dir and raws[m["id"]] is not None:
            os.makedirs(raw_dir, exist_ok=True)
            with open(os.path.join(raw_dir, m["id"] + ".raw"), "w", encoding="utf-8", newline="\n") as fh:
                fh.write(raws[m["id"]])
    return raws, reasons


# ------------------------------------------------------------------------------------ rendering
def gib(n) -> str:
    if n is None:
        return "unknown"
    return f"{n / (1 << 30):,.1f}" if n >= (1 << 30) else f"{n / (1 << 20):,.0f} MiB"


def render_csv(inv: dict) -> str:
    import io
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=COLUMNS, lineterminator="\n")
    w.writeheader()
    for r in inv["rows"]:
        w.writerow({c: ("" if r.get(c) is None else r[c]) for c in COLUMNS})
    return buf.getvalue()


def render_md(inv: dict) -> str:
    c = inv["counts"]
    out = [f"# Cluster inventory, read {inv['generated']}", "",
           f"{c['machines']} machines: {c['verified']} verified, {c['partial']} partial, {c['unknown']} unknown. "
           f"{c['rows']} rows ({c['rows_verified']} read now, {c['rows_stale']} stale from an earlier reading). "
           "Read only. `unknown` means the machine could not be read, never that it is empty; "
           "`stale` means the row is from an earlier reading and shows its own date.", "",
           "| Machine | Status | Last read | Rows | Note |", "|---|---|---|---|---|"]
    for s in inv["machines"]:
        out.append(f"| {s['machine']} | {s['status']} | {s.get('last_seen') or 'never'} | {s['rows']} | "
                   f"{(s.get('reason') or '').replace('|', '/')} |")
    for s in inv["machines"]:
        rows = [r for r in inv["rows"] if r["machine"] == s["machine"]]
        out += ["", f"## {s['machine']}: {s['status']}", "", f"{s.get('role') or ''}", ""]
        if s.get("reason"):
            out += [f"Reason: {s['reason']}", ""]
        out += ["| Kind | Device | Mount | Size GiB | Used GiB | Free GiB | FS | Label / model | State | Status | Last read |",
                "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in rows:
            out.append("| " + " | ".join(str(x if x is not None else "") for x in (
                r["kind"], r["device"], r["mount"], gib(r["size"]) if r["size"] is not None else "unknown",
                gib(r["used"]) if r["used"] is not None else "unknown",
                gib(r["free"]) if r["free"] is not None else "unknown", r["fs"],
                " ".join(x for x in (r["label"], r["model"]) if x), r["state"], r["status"], r["last_seen"]))
                + " |")
    return "\n".join(out) + "\n"


def write_outputs(inv: dict, out_dir: str) -> list[str]:
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    for name, text in (("inventory.json", json.dumps(inv, indent=1, ensure_ascii=False) + "\n"),
                       ("inventory.csv", render_csv(inv)), ("INVENTORY.md", render_md(inv))):
        p = os.path.join(out_dir, name)
        tmp = p + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        os.replace(tmp, p)
        paths.append(p)
    return paths


def main(argv=None, run=subprocess.run) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=("collect", "render"))
    ap.add_argument("--targets", default=os.environ.get("CLUSTER_INVENTORY_TARGETS", DEFAULT_TARGETS))
    ap.add_argument("--only", help="comma separated machine ids")
    ap.add_argument("--previous", help="the last inventory.json, for stale carry-over")
    ap.add_argument("--out", default=os.path.join(os.environ.get("CLUSTER_FILES_DIR", r"F:\novah\cluster-files"),
                                                  "inventory"))
    ap.add_argument("--raw-dir", help="collect: save each raw answer here; render: read them from here")
    ap.add_argument("--timeout", type=int, default=90)
    a = ap.parse_args(argv)
    machines = load_targets(a.targets)
    if a.only:
        want = set(a.only.split(","))
        unknown = want - {m["id"] for m in machines}
        if unknown:
            print(f"unknown machine ids: {sorted(unknown)}", file=sys.stderr)
            return 2
        machines = [m for m in machines if m["id"] in want]
    prev = a.previous or os.path.join(a.out, "inventory.json")
    if a.cmd == "collect":
        raws, reasons = collect(machines, run, a.timeout, a.raw_dir)
    else:
        if not a.raw_dir:
            print("render needs --raw-dir", file=sys.stderr)
            return 2
        raws, reasons = {}, {}
        for m in machines:
            p = os.path.join(a.raw_dir, m["id"] + ".raw")
            if os.path.isfile(p):
                with open(p, encoding="utf-8") as fh:
                    raws[m["id"]], reasons[m["id"]] = fh.read(), None
            else:
                raws[m["id"]], reasons[m["id"]] = None, "no recorded raw answer"
    inv = make_inventory(machines, raws, reasons, prev)
    for p in write_outputs(inv, a.out):
        print(p)
    c = inv["counts"]
    print(f"machines {c['machines']}: verified {c['verified']}, partial {c['partial']}, unknown {c['unknown']}; "
          f"rows {c['rows']} (read now {c['rows_verified']}, stale {c['rows_stale']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
