#!/usr/bin/env python3
"""NODE cluster files part 7: one read-only reader per machine, feeding the SAME index as the part 5
pilot (node/file_index.py).

Machines come from node/cluster_inventory_targets.json (part 1: routes, os, in-use flag); what is read
on each comes from node/cluster_reader_sources.json. Per machine pass:

  1. the pass may start only if the machine's window allows it (GREYWOLF, SURFACE, MSI: 22:00 to
     08:00 Pacific; servers any time) and its guards say go (R620: the Postgres standby guard; R710 #1:
     no storage ingest running, else its dumps subtree stays unread);
  2. it takes the estate heavy slot for that ONE machine (node/cluster_scan_slot.py) and releases it
     after, so passes are one at a time and the slot is free between machines;
  3. a WALK script runs on the machine (Linux: `nice -n 19 ionice -c3 python3 -`; Windows: PowerShell
     at Idle priority) and streams back one JSON line per directory: names, sizes, mtimes. Nothing
     else. The index on GREYWOLF ingests it with file_index's incremental rules;
  4. a HASH script runs on the machine for files whose size is shared by another file anywhere in the
     cluster (quick hash, then full SHA-256 of quick collisions), throttled, and returns path + hash.
     File content never leaves the machine. GREYWOLF's own files are read in-process.

Honesty rules (all tested in tests/test_cluster_readers.py):
  * A machine that cannot be reached (no route, ssh timeout, refused address) is recorded `unknown`
    with the reason; rows from an earlier scan are kept, never dropped, never reported as empty.
  * A root that is missing or not mounted is `unknown`, not empty. A walk whose stream ends without
    its end line (connection cut, killed, budget) is `partial`; only `complete` drops vanished rows.
  * A subtree a walk did not enter (unreadable, other file system, guard) keeps its rows.
  * Privacy tier (health, financial, credential paths): name, size and date only. Never hashed,
    never content-read; the hash request never names them.
  * The heavy slot held or unknown, the window closed, a guard not ok, or Pacific time unreadable:
    the pass is DEFERRED with the reason. Nothing proceeds "anyway".
  * Transport is ssh BatchMode to loopback, RFC 1918 or tailnet addresses only (aliases resolved with
    `ssh -G` first). No key is created, copied or printed by this file (KEY-STEPS.md is the owner's).

`plan` (the default) prints what a run would do and touches nothing: no ssh, no lock, no index write.
Stdlib only.
"""
from __future__ import annotations

import argparse
import base64
import datetime as dt
import hashlib
import importlib.util
import itertools
import json
import os
import shlex
import subprocess
import sys
import threading
import time
from types import SimpleNamespace
from typing import Iterable, Iterator

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = os.path.join(HERE, "cluster_inventory_targets.json")
SOURCES = os.path.join(HERE, "cluster_reader_sources.json")
ROUTE_TARGETS = os.path.join(HERE, "cluster_targets.json")
SOURCES_SCHEMA = "cluster-reader-sources-1"
PACIFIC = "America/Los_Angeles"
HASH_BATCH = 2000
DEFAULT_MINUTES = 120.0
DEFAULT_MBPS = 40.0
WATCHDOG_SLACK_S = 300
REMOTE_CONTENT_STATE = "remote"     # extract_state of a remote file: content is never read off-machine


def _load(name: str, file: str):
    """Sibling module under a private name (the way cluster_scan_slot loads cluster_route), so this
    file never replaces a module another importer already holds."""
    key = f"_cluster_readers_{name}"
    if key not in sys.modules:
        spec = importlib.util.spec_from_file_location(key, os.path.join(HERE, file))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[key] = mod
        spec.loader.exec_module(mod)
    return sys.modules[key]


def fi():
    return _load("file_index", "file_index.py")


def inv():
    return _load("inventory", "cluster_inventory.py")


def slot_mod():
    return _load("scan_slot", "cluster_scan_slot.py")


class Unreadable(Exception):
    """The machine could not be read. The reason is recorded; the machine reads `unknown`."""


# --------------------------------------------------------------------------- remote scripts
# Both scripts are pure stdlib Python (Linux servers) or PowerShell 5.1 (Windows laptops). They read
# metadata or bytes and print ASCII JSON lines; they never write, move, rename or delete anything.

PY_WALK = r'''
import json, os, sys, time
def emit(o):
    sys.stdout.write(json.dumps(o) + "\n")
def is_git(p):
    return os.path.isdir(os.path.join(p, ".git")) or os.path.isfile(os.path.join(p, ".git"))
def main():
    root = JOB["root"]
    end = time.monotonic() + JOB["budget_s"] if JOB.get("budget_s") else None
    skip = set(n.lower() for n in JOB.get("skip_names", []))
    excl = [e.replace("\\", "/").rstrip("/") for e in JOB.get("excludes", [])]
    def excluded(p):
        p = p.replace("\\", "/")
        return any(p == e or p.startswith(e + "/") for e in excl)
    try:
        st0 = os.stat(root)
    except OSError as e:
        emit({"end": "missing", "why": "root not found: " + type(e).__name__}); return
    if JOB.get("require_mount") and not os.path.ismount(root):
        emit({"end": "missing", "why": "root is not mounted"}); return
    dev = st0.st_dev
    stack = [(root, is_git(root))]
    dirs = files = 0
    state = "complete"
    while stack:
        if end is not None and time.monotonic() >= end:
            state = "partial"; break
        d, g = stack.pop()
        try:
            ents = list(os.scandir(d))
        except OSError as e:
            emit({"u": d, "e": type(e).__name__}); continue
        dirs += 1
        fl = []
        for e in ents:
            try:
                if e.is_symlink():
                    continue
                if e.is_dir(follow_symlinks=False):
                    p = e.path
                    if e.name.lower() in skip or excluded(p):
                        continue
                    # os.lstat, not e.stat(): a Windows DirEntry leaves st_dev at 0
                    if JOB.get("one_fs", True) and os.lstat(p).st_dev != dev:
                        emit({"u": p, "e": "other file system, not crossed"}); continue
                    stack.append((p, g or is_git(p))); continue
                if not e.is_file(follow_symlinks=False):
                    continue
                s = e.stat(follow_symlinks=False)
            except OSError as err:
                emit({"u": e.path, "e": type(err).__name__}); continue
            files += 1
            fl.append([e.name, s.st_size, s.st_mtime_ns, "g" if g else ""])
        emit({"d": d, "f": fl})
    emit({"end": state, "dirs": dirs, "files": files})
main()
sys.stdout.flush()
'''

PY_HASH = r'''
import hashlib, json, os, sys, time
QUICK = 65536
def emit(o):
    sys.stdout.write(json.dumps(o) + "\n")
class Throttle:
    def __init__(self, mbps):
        self.rate = mbps * 1024 * 1024; self.t0 = time.monotonic(); self.done = 0
    def took(self, n):
        self.done += n
        if self.rate > 0:
            ahead = self.done / self.rate - (time.monotonic() - self.t0)
            if ahead > 0:
                time.sleep(ahead)
def main():
    th = Throttle(JOB.get("mbps", 0))
    end = time.monotonic() + JOB["budget_s"] if JOB.get("budget_s") else None
    for it in JOB["items"]:
        path, size = it["p"], it["s"]
        if end is not None and time.monotonic() >= end:
            emit({"end": "partial"}); return
        try:
            if os.stat(path).st_size != size:
                emit({"p": path, "e": "changed"}); continue
            with open(path, "rb") as fh:
                if JOB["mode"] == "quick":
                    h = hashlib.sha256(str(size).encode())
                    head = fh.read(QUICK); h.update(head); n = len(head)
                    if size > 2 * QUICK:
                        fh.seek(size - QUICK); tail = fh.read(QUICK); h.update(tail); n += len(tail)
                    th.took(n)
                else:
                    h = hashlib.sha256()
                    while True:
                        b = fh.read(1048576)
                        if not b:
                            break
                        h.update(b); th.took(len(b))
            emit({"p": path, "h": h.hexdigest()})
        except OSError as e:
            emit({"p": path, "e": type(e).__name__})
    emit({"end": "complete"})
main()
sys.stdout.flush()
'''

# PowerShell 5.1. Output is ASCII only (every non-ASCII UTF-16 unit is escaped as \uXXXX), so the
# console code page of the ssh session cannot corrupt a path.
PS_COMMON = r'''
$ErrorActionPreference = 'Stop'
$out = [Console]::Out
function Q([string]$s) {
  $s = $s.Replace('\', '\\').Replace('"', '\"')
  return '"' + [regex]::Replace($s, '[^\x20-\x7e]', { param($m) '\u{0:x4}' -f [int][char]$m.Value }) + '"'
}
function L([string]$s) { $out.WriteLine($s) }
$job = ConvertFrom-Json $JOBJSON
$deadline = if ($job.budget_s) { [DateTime]::UtcNow.AddSeconds([double]$job.budget_s) } else { [DateTime]::MaxValue }
'''

PS_WALK = r'''
$root = $job.root
$skip = @{}; foreach ($n in $job.skip_names) { $skip[$n.ToLower()] = 1 }
$excl = @($job.excludes | ForEach-Object { $_.Replace('/', '\').TrimEnd('\').ToLower() })
function Excluded([string]$p) {
  $l = $p.ToLower()
  foreach ($e in $excl) { if ($l -eq $e -or $l.StartsWith($e + '\')) { return $true } }
  return $false
}
function IsGit([string]$p) { return ([IO.Directory]::Exists($p + '\.git') -or [IO.File]::Exists($p + '\.git')) }
if (-not [IO.Directory]::Exists($root)) { L '{"end":"missing","why":"root not found"}'; $out.Flush(); return }
$epoch = [int64]621355968000000000
$stack = New-Object System.Collections.Stack
$stack.Push(@($root, (IsGit $root)))
$dirs = 0; $files = 0; $state = 'complete'
while ($stack.Count -gt 0) {
  if ([DateTime]::UtcNow -ge $deadline) { $state = 'partial'; break }
  $item = $stack.Pop(); $d = [string]$item[0]; $g = [bool]$item[1]
  try { $ents = (New-Object IO.DirectoryInfo $d).GetFileSystemInfos() }
  catch { L ('{"u":' + (Q $d) + ',"e":' + (Q $_.Exception.GetType().Name) + '}'); continue }
  $dirs++
  $parts = New-Object System.Collections.Generic.List[string]
  foreach ($e in $ents) {
    try {
      $a = [int64]$e.Attributes
      if ($a -band 0x10) {
        if ($a -band 0x400) { continue }
        $p = $e.FullName
        if ($skip.ContainsKey($e.Name.ToLower()) -or (Excluded $p)) { continue }
        $stack.Push(@($p, ($g -or (IsGit $p)))); continue
      }
      $fl = ''
      if ($g) { $fl += 'g' }
      if ($a -band 0x441000) { $fl += 'c' }
      $ns = ([int64]$e.LastWriteTimeUtc.Ticks - $epoch) * 100
      $parts.Add('[' + (Q $e.Name) + ',' + [int64]$e.Length + ',' + $ns + ',"' + $fl + '"]')
      $files++
    } catch { L ('{"u":' + (Q $e.FullName) + ',"e":' + (Q $_.Exception.GetType().Name) + '}') }
  }
  L ('{"d":' + (Q $d) + ',"f":[' + ($parts -join ',') + ']}')
}
L ('{"end":"' + $state + '","dirs":' + $dirs + ',"files":' + $files + '}')
$out.Flush()
'''

PS_HASH = r'''
$sha = [Security.Cryptography.SHA256]::Create()
$rate = [double]$job.mbps * 1048576
$t0 = [DateTime]::UtcNow; $done = [double]0
function Took([int64]$n) {
  $script:done += $n
  if ($rate -gt 0) {
    $ahead = $script:done / $rate - ([DateTime]::UtcNow - $t0).TotalSeconds
    if ($ahead -gt 0) { Start-Sleep -Milliseconds ([int]($ahead * 1000)) }
  }
}
function ReadFull($fs, [byte[]]$buf, [int]$want) {
  $got = 0
  while ($got -lt $want) { $n = $fs.Read($buf, $got, $want - $got); if ($n -le 0) { break }; $got += $n }
  return $got
}
$empty = New-Object byte[] 0
$buf = New-Object byte[] 1048576
foreach ($it in $job.items) {
  if ([DateTime]::UtcNow -ge $deadline) { L '{"end":"partial"}'; $out.Flush(); return }
  $p = [string]$it.p; $size = [int64]$it.s
  try {
    if ((New-Object IO.FileInfo $p).Length -ne $size) { L ('{"p":' + (Q $p) + ',"e":"changed"}'); continue }
    $fs = [IO.File]::Open($p, 'Open', 'Read', 'ReadWrite')
    try {
      [void]$sha.Initialize()
      if ($job.mode -eq 'quick') {
        $sb = [Text.Encoding]::ASCII.GetBytes([string]$size)
        [void]$sha.TransformBlock($sb, 0, $sb.Length, $null, 0)
        $n = ReadFull $fs $buf 65536; [void]$sha.TransformBlock($buf, 0, $n, $null, 0); $tot = $n
        if ($size -gt 131072) {
          [void]$fs.Seek($size - 65536, 'Begin')
          $n = ReadFull $fs $buf 65536; [void]$sha.TransformBlock($buf, 0, $n, $null, 0); $tot += $n
        }
        Took $tot
      } else {
        while ($true) {
          $n = $fs.Read($buf, 0, $buf.Length)
          if ($n -le 0) { break }
          [void]$sha.TransformBlock($buf, 0, $n, $null, 0); Took $n
        }
      }
      [void]$sha.TransformFinalBlock($empty, 0, 0)
      $hex = [BitConverter]::ToString($sha.Hash).Replace('-', '').ToLower()
      L ('{"p":' + (Q $p) + ',"h":"' + $hex + '"}')
    } finally { $fs.Dispose() }
  } catch { L ('{"p":' + (Q $p) + ',"e":' + (Q $_.Exception.GetType().Name) + '}') }
}
L '{"end":"complete"}'
$out.Flush()
'''

# Runs first on Windows: Idle priority (cluster_scan_slot.WINDOWS_THROTTLE), then the real script,
# which arrives base64-encoded on stdin (ASCII, so no code page can touch it).
PS_BOOTSTRAP = ("(Get-Process -Id $PID).PriorityClass = 'Idle'; "
                "$s = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String([Console]::In.ReadToEnd().Trim())); "
                "Invoke-Expression $s")


def python_script(kind: str, job: dict) -> bytes:
    body = {"walk": PY_WALK, "hash": PY_HASH}[kind]
    return (f"JOB = __import__('json').loads({json.dumps(job)!r})\n" + body).encode("utf-8")


def powershell_script(kind: str, job: dict) -> str:
    body = {"walk": PS_WALK, "hash": PS_HASH}[kind]
    lit = json.dumps(job).replace("'", "''")
    return f"$JOBJSON = '{lit}'\n" + PS_COMMON + body


def ps_bootstrap_argv() -> list[str]:
    enc = base64.b64encode(PS_BOOTSTRAP.encode("utf-16-le")).decode("ascii")
    return ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", enc]


def script_bytes(os_name: str, kind: str, job: dict) -> bytes:
    """What goes on the remote's stdin."""
    if os_name == "windows":
        return base64.b64encode(powershell_script(kind, job).encode("utf-8")) + b"\n"
    return python_script(kind, job)


# --------------------------------------------------------------------------- transport

def ssh_opts() -> list[str]:
    return list(inv().SSH_OPTS) + ["-o", "Compression=yes"]


def remote_argv(machine: dict) -> list[str]:
    """The one command line that runs a reader script on `machine`; the script comes on stdin. Raises
    Unreadable for a route that cannot carry it. Does not touch the network."""
    route = machine.get("route") or {}
    kind = route.get("kind")
    if kind == "none":
        raise Unreadable(route.get("reason") or "no route")
    if machine.get("os") == "windows":
        if kind != "ssh":
            raise Unreadable(f"a Windows reader needs an ssh route, not {kind!r}")
        return _ssh(route, " ".join(ps_bootstrap_argv()))
    low = " ".join(slot_mod().throttle_argv(machine)) + " python3 -"
    if kind == "ssh":
        return _ssh(route, low)
    if kind == "ssh-via":
        inner = ("ssh -o BatchMode=yes -o ConnectTimeout=8 -o IdentitiesOnly=yes -i "
                 f"{shlex.quote(route['via_key'])} {route['host']} {shlex.quote(low)}")
        return ["ssh", *ssh_opts(), route["via"], inner]
    raise Unreadable(f"route kind {kind!r} has no remote reader")


def _ssh(route: dict, cmd: str) -> list[str]:
    argv = ["ssh", *ssh_opts()]
    if route.get("key"):
        argv += ["-i", os.path.expanduser(route["key"])]
    return argv + [route["host"], cmd]


def check_route(machine: dict, run=subprocess.run) -> None:
    """Refuse any destination that is not loopback, RFC 1918 or tailnet (aliases via `ssh -G`)."""
    route = machine.get("route") or {}
    try:
        if route.get("kind") == "ssh":
            inv().check_address(route["host"])
            inv().resolve_alias(route["host"], run)
        elif route.get("kind") == "ssh-via":
            inv().check_address(route["host"])
            inv().resolve_alias(route["via"], run)
    except inv().Unreadable as e:
        raise Unreadable(str(e)) from None
    except (OSError, subprocess.SubprocessError) as e:
        raise Unreadable(f"could not resolve the route: {type(e).__name__}") from None


class SshTransport:
    """Streams a reader script's JSON lines from a machine. `popen` is injectable for tests."""

    def __init__(self, machine: dict, popen=subprocess.Popen, run=subprocess.run):
        self.m, self.popen, self.run = machine, popen, run
        self.checked = False

    def stream(self, kind: str, job: dict, timeout_s: float) -> Iterator[str]:
        if not self.checked:
            check_route(self.m, self.run)
            self.checked = True
        argv = remote_argv(self.m)
        data = script_bytes(self.m.get("os", "linux"), kind, job)
        return _stream_process(argv, data, timeout_s, self.popen)


def _stream_process(argv, data: bytes, timeout_s: float, popen=subprocess.Popen) -> Iterator[str]:
    """Yield stdout lines. Nothing at all and a failed exit is Unreadable (the reason from stderr);
    lines then a cut is just the end of the stream: the caller sees no end line and says partial."""
    try:
        p = popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError as e:
        raise Unreadable(f"cannot start {e.filename}") from None
    err = bytearray()
    killed = threading.Event()

    def feed():
        try:
            p.stdin.write(data)
            p.stdin.close()
        except OSError:
            pass

    def drain():
        for chunk in iter(lambda: p.stderr.read(4096), b""):
            err.extend(chunk)
            del err[:-2048]

    def watchdog():
        if not done.wait(timeout_s):
            killed.set()
            p.kill()

    done = threading.Event()
    for f in (feed, drain, watchdog):
        threading.Thread(target=f, daemon=True).start()

    def lines():
        n = 0
        try:
            for raw in p.stdout:
                n += 1
                yield raw.decode("ascii", "replace").rstrip("\r\n")
            rc = p.wait()
        finally:
            done.set()
        if n == 0:
            if killed.is_set():
                raise Unreadable(f"no answer in {int(timeout_s)} s (unknown, not down)")
            if rc != 0:
                tail = next((x for x in reversed(err.decode("utf-8", "replace").strip().splitlines())
                             if x and not x.startswith("**")), "no output")
                raise Unreadable(f"ssh/exec rc={rc}: {tail[:160]}")

    return lines()


class LocalPythonTransport:
    """Runs the same Python reader scripts on this machine, with this Python. For tests and for a
    Linux node reading itself; never used for GREYWOLF, which is read in-process."""

    def __init__(self, python: str = sys.executable, popen=subprocess.Popen):
        self.python, self.popen = python, popen

    def stream(self, kind: str, job: dict, timeout_s: float) -> Iterator[str]:
        return _stream_process([self.python, "-I", "-"], python_script(kind, job), timeout_s, self.popen)


class LocalPowerShellTransport:
    """Runs the Windows reader scripts on this machine through the same bootstrap ssh would start."""

    def __init__(self, exe: str = "powershell", popen=subprocess.Popen):
        self.exe, self.popen = exe, popen

    def stream(self, kind: str, job: dict, timeout_s: float) -> Iterator[str]:
        argv = [self.exe] + ps_bootstrap_argv()[1:]
        return _stream_process(argv, script_bytes("windows", kind, job), timeout_s, self.popen)


def peek(it: Iterator[str]) -> Iterator[str]:
    """Pull the first line now, so an unreachable machine raises Unreadable before any scan row is
    written; the line is put back."""
    first = next(it, None)
    return iter(()) if first is None else itertools.chain([first], it)


# --------------------------------------------------------------------------- ingest (index side)

def _under(path: str, root: str) -> bool:
    r = root.rstrip("/")
    return path == root or path == r or path.startswith(r + "/")


def _join(d: str, name: str) -> str:
    return (d if d.endswith("/") else d + "/") + name


def ingest_walk(con, machine: str, root: str, lines: Iterable[str], excludes=(), log=print,
                guard_skipped=()) -> dict:
    """Feed a walk stream into the index with file_index's rules. Returns the scan row."""
    F = fi()
    root_n = F.norm(root)
    now = time.time()
    cur = con.execute("INSERT INTO scans (machine, root, started, state) VALUES (?,?,?,?)",
                      (machine, root_n, now, "running"))
    scan_id = cur.lastrowid
    con.execute("INSERT OR REPLACE INTO sources VALUES (?,?,?,?,?)",
                (machine, root_n, json.dumps(list(excludes)), scan_id, "running"))
    con.commit()
    st = {"dirs": 0, "files": 0, "new": 0, "changed": 0, "removed": 0, "unreadable": 0}
    unreadable = [F.norm(g) for g in guard_skipped]
    for g in unreadable:
        con.execute("INSERT OR REPLACE INTO unreadable VALUES (?,?,?,?)",
                    (machine, g, "guard: not read this pass", scan_id))
    end, why, bad, pending = None, None, 0, 0
    try:
        for line in lines:
            try:
                msg = json.loads(line)
            except ValueError:
                bad += 1
                continue
            if not isinstance(msg, dict):
                bad += 1
                continue
            if "end" in msg:
                end, why = msg.get("end"), msg.get("why")
                break
            if "u" in msg:
                u = F.norm(str(msg["u"]))
                if not _under(u, root_n):
                    bad += 1
                    continue
                unreadable.append(u)
                con.execute("INSERT OR REPLACE INTO unreadable VALUES (?,?,?,?)",
                            (machine, u, str(msg.get("e", "unreadable"))[:80], scan_id))
                st["unreadable"] += 1
                continue
            if "d" not in msg or not isinstance(msg.get("f"), list):
                bad += 1
                continue
            nd = F.norm(str(msg["d"]))
            if not _under(nd, root_n):
                bad += 1
                continue
            st["dirs"] += 1
            known = {r["name"]: r for r in con.execute(
                "SELECT id, name, size, mtime_ns FROM files WHERE machine=? AND dir=?", (machine, nd))}
            for ent in msg["f"]:
                try:
                    name, size, mtime_ns, flags = str(ent[0]), int(ent[1]), int(ent[2]), str(ent[3])
                except (TypeError, ValueError, IndexError):
                    bad += 1
                    continue
                if not name or "/" in name or "\\" in name or name in (".", ".."):
                    bad += 1
                    continue
                st["files"] += 1
                row = known.get(name)
                if row is not None and row["size"] == size and row["mtime_ns"] == mtime_ns:
                    con.execute("UPDATE files SET seen_scan=? WHERE id=?", (scan_id, row["id"]))
                else:
                    s = SimpleNamespace(st_size=size, st_mtime=mtime_ns / 1e9, st_mtime_ns=mtime_ns)
                    attrs = F.CLOUD_ATTRS if "c" in flags else 0
                    F._upsert(con, machine, _join(nd, name), nd, name, s, attrs, "g" in flags, scan_id,
                              row, extract=False, content_state=REMOTE_CONTENT_STATE)
                    st["changed" if row is not None else "new"] += 1
                pending += 1
            if pending >= 5000:
                con.commit()
                pending = 0
    except Unreadable as e:
        why = str(e)
    con.commit()
    if end == "missing":
        state, note = "unreachable", f"root {root_n}: {why or 'missing'} (unknown, not empty)"
    elif end == "complete" and bad == 0:
        state, note = "complete", None
    else:
        state = "partial"
        note = ("stream ended without its end line (cut, killed or failed)" if end is None
                else f"walk said {end}") + (f"; {bad} malformed line(s) ignored" if bad else "") + \
            (f"; {why}" if why and end is None else "") + "; rows not reached are kept, removals skipped"
    if state == "complete":
        st["removed"] = F._drop_missing(con, machine, root_n, scan_id, unreadable)
    con.execute("UPDATE scans SET finished=?, state=?, dirs=?, files=?, new=?, changed=?, removed=?, "
                "unreadable=?, note=? WHERE id=?",
                (time.time(), state, st["dirs"], st["files"], st["new"], st["changed"], st["removed"],
                 st["unreadable"], note, scan_id))
    con.execute("UPDATE sources SET state=? WHERE machine=? AND root=?", (state, machine, root_n))
    con.commit()
    out = dict(con.execute("SELECT * FROM scans WHERE id=?", (scan_id,)).fetchone())
    log(f"walk {machine} {root_n}: {state}, {st['files']} files in {st['dirs']} dirs ({st['new']} new, "
        f"{st['changed']} changed, {st['removed']} removed, {st['unreadable']} not entered)"
        + (f"; {note}" if note else ""))
    return out


def _apply_hashes(con, mode: str, by_path: dict, lines: Iterable[str]) -> dict:
    st = {"ok": 0, "errors": 0, "changed": 0, "ignored": 0, "end": None}
    for line in lines:
        try:
            msg = json.loads(line)
        except ValueError:
            st["ignored"] += 1
            continue
        if not isinstance(msg, dict):
            st["ignored"] += 1
            continue
        if "end" in msg:
            st["end"] = msg["end"]
            break
        rid = by_path.get(msg.get("p"))
        if rid is None:          # the machine answered for a path it was not asked about
            st["ignored"] += 1
            continue
        h = msg.get("h")
        if isinstance(h, str) and len(h) == 64 and all(c in "0123456789abcdef" for c in h):
            if mode == "quick":
                con.execute("UPDATE files SET quick=?, hash_state='quick' WHERE id=?", (h, rid))
            else:
                con.execute("UPDATE files SET hash=?, hash_state='full' WHERE id=?", (h, rid))
            st["ok"] += 1
        elif msg.get("e") == "changed":
            st["changed"] += 1   # left pending: the next walk sees the new size and date
        else:
            con.execute("UPDATE files SET hash_state='error' WHERE id=?", (rid,))
            st["errors"] += 1
    con.commit()
    return st


def hash_on_machine(con, machine: str, transport, mbps: float, deadline: float | None,
                    batch: int = HASH_BATCH, log=print, clock=time.monotonic) -> dict:
    """Quick then full hashes of `machine`'s candidates, computed ON the machine, in batches. The
    request carries path and size only; private and cloud rows are never candidates."""
    F = fi()
    st = {"quick": 0, "full": 0, "errors": 0, "stopped": None}

    def left():
        return None if deadline is None else deadline - clock()

    for mode in ("quick", "full"):
        if mode == "quick":
            rows = F.quick_candidates(con, machine)
        else:
            rows = [r for g in F.quick_groups(con) for r in F.full_candidates(con, g["quick"], machine)]
        for i in range(0, len(rows), batch):
            rem = left()
            if rem is not None and rem <= 0:
                st["stopped"] = "time budget"
                break
            # Belt and braces: a private row is never a candidate (hash_state 'private'), and even if
            # one were, its path is not put in a request.
            part = [r for r in rows[i:i + batch] if F.privacy_of(r["path"]) is None]
            if not part:
                continue
            by_path = {r["path"]: r["id"] for r in part}
            job = {"mode": mode, "items": [{"p": r["path"], "s": r["size"]} for r in part], "mbps": mbps,
                   "budget_s": rem}
            res = _apply_hashes(con, mode, by_path,
                                peek(transport.stream("hash", job, (rem or 6 * 3600) + WATCHDOG_SLACK_S)))
            st[mode] += res["ok"]
            st["errors"] += res["errors"]
            if res["end"] != "complete":
                st["stopped"] = "hash stream did not finish"
                break
        if st["stopped"]:
            break
    log(f"hash {machine}: {st['quick']} quick, {st['full']} full on the machine, {st['errors']} errors"
        + (f", stopped: {st['stopped']}" if st["stopped"] else ", complete"))
    return st


# --------------------------------------------------------------------------- config and plan

def load_machines(targets: str = TARGETS, sources: str = SOURCES) -> list[dict]:
    """Targets joined with sources, in the targets' order. A machine in one file and not the other is
    an error: none may be silently skipped."""
    with open(targets, encoding="utf-8") as fh:
        t = json.load(fh)
    with open(sources, encoding="utf-8") as fh:
        s = json.load(fh)
    if s.get("schema") != SOURCES_SCHEMA:
        raise ValueError(f"{sources}: schema is not {SOURCES_SCHEMA}")
    ids = [m["id"] for m in t["machines"]]
    if set(ids) != set(s["machines"]):
        raise ValueError(f"machines differ between targets and sources: {sorted(set(ids) ^ set(s['machines']))}")
    out = []
    for m in t["machines"]:
        src = dict(s["machines"][m["id"]])
        excl = list(s.get("presets", {}).get(src.get("excludes_preset"), [])) + list(src.get("excludes", []))
        if src.get("exclude_index_dir"):
            excl.append(fi().norm(os.path.dirname(os.path.abspath(fi().default_db()))))
        out.append({**m, "sources": {**src, "excludes": excl}})
    return out


def pacific_now() -> dt.datetime | None:
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo(PACIFIC))
    except Exception:
        return None


def window(machine: dict, now: dt.datetime | None) -> tuple[bool, str, float | None]:
    """(go, why, seconds until the window closes or None). Unreadable Pacific time refuses an
    in-use machine."""
    pol = slot_mod().scan_policy(machine)
    if not pol["in_use"]:
        return True, "server: any time, under the throttle", None
    if now is None:
        return False, "Pacific time could not be read: an in-use machine is not scanned", None
    ok, why = slot_mod().scan_allowed(machine, now)
    if not ok:
        return False, why, None
    lo, _hi = slot_mod().WORK_HOURS
    close = now.replace(hour=lo, minute=0, second=0, microsecond=0)
    if now.hour >= lo:
        close += dt.timedelta(days=1)
    return True, why + f"; this pass stops by {lo:02d}:00 Pacific", (close - now).total_seconds()


def roots_of(machine: dict) -> list[dict]:
    return list(machine["sources"].get("roots") or [])


def walk_job(machine: dict, root: dict, budget_s: float | None, extra_skip=()) -> dict:
    return {"root": root["path"], "require_mount": bool(root.get("require_mount")),
            "one_fs": bool(machine["sources"].get("one_fs", True)),
            "skip_names": sorted(fi().SKIP_DIR_NAMES),
            "excludes": list(machine["sources"]["excludes"]) + list(extra_skip),
            "budget_s": budget_s}


def describe_route(machine: dict) -> str:
    r = machine.get("route") or {}
    k = r.get("kind")
    if k == "none":
        return f"none: {r.get('reason') or 'no route'}"
    if k == "local":
        return "local (this machine, read in-process)"
    if k == "ssh":
        return f"ssh {r['host']}" + (f" with key {r['key']}" if r.get("key") else " (ssh config key)")
    if k == "ssh-via":
        return f"ssh {r['via']}, then {r['host']} with {r['via']}'s key {r['via_key']}"
    return f"unknown route kind {k!r}"


def plan(machines: list[dict], now: dt.datetime | None, minutes: float = DEFAULT_MINUTES) -> list[dict]:
    """What a run would do, machine by machine, in order. Touches nothing: no ssh, no lock, no index."""
    out = []
    for m in machines:
        route = (m.get("route") or {}).get("kind")
        item = {"machine": m["id"], "os": m.get("os"), "route": describe_route(m),
                "roots": [r["path"] for r in roots_of(m)], "excludes": m["sources"]["excludes"],
                "guards": m["sources"].get("guards", []), "steps": []}
        if route == "none" or not roots_of(m):
            item.update(go=False, verdict="unknown",
                        why=(m.get("route") or {}).get("reason") or m["sources"].get("why") or "nothing to read",
                        steps=["record `unknown` with the reason; nothing is sent"])
            out.append(item)
            continue
        ok, why, until = window(m, now)
        budget = minutes * 60 if until is None else min(minutes * 60, until)
        item.update(go=ok, verdict="go" if ok else "deferred", why=why,
                    budget_s=round(budget) if ok else None)
        steps = []
        for g in item["guards"]:
            if g["kind"] == "standby":
                steps.append("read cluster_route's Postgres standby guard through overlord (grep and pgrep "
                             "only); anything but ok defers this pass")
            elif g["kind"] == "ingest":
                steps.append(f"read active ingest-* units on {g['via']} (systemctl, read-only); if any is "
                             f"active or the read fails, {g['subtree']} is not entered and stays unknown")
        steps.append("take the estate heavy slot for this one machine (HEAVY_LOCK_PY); held or unknown "
                     "defers; released after the pass")
        if route == "local":
            steps.append("walk each root in-process at background priority (file_index.scan), text extracts "
                         "for GREYWOLF's own files only; then quick and full hashes in-process, throttled")
        else:
            argv = remote_argv(m)
            show = " ".join(shlex.quote(a) for a in argv[:-1]) + " " + shlex.quote(
                argv[-1] if len(argv[-1]) < 120 else argv[-1][:60] + "...")
            for r in roots_of(m):
                sb = script_bytes(m.get("os", "linux"), "walk", walk_job(m, r, budget))
                steps.append(f"walk {r['path']}" + (" (must be a mount, else unknown)" if r.get("require_mount") else "")
                             + f": {show}  <- walk script on stdin, {len(sb)} bytes, sha256 "
                             f"{hashlib.sha256(sb).hexdigest()[:12]}; back: one JSON line per directory "
                             "(names, sizes, dates)")
            steps.append(f"hash on {m['id']}: quick hash of files whose size another file shares, then full "
                         f"SHA-256 of quick collisions, batches of {HASH_BATCH}, {DEFAULT_MBPS:g} MB/s cap; "
                         "request is path+size, answer is path+hash; private and cloud files are never asked")
        steps.append("privacy tier (health, financial, credential): name, size, date only; never hashed or read")
        item["steps"] = steps
        out.append(item)
    return out


def render_plan(items: list[dict], now: dt.datetime | None) -> str:
    lines = [f"cluster readers plan, Pacific {now.strftime('%Y-%m-%d %H:%M') if now else 'unknown'}. "
             "DRY RUN: nothing was contacted, locked or written.", ""]
    for it in items:
        lines.append(f"{it['machine']}: {it['verdict'].upper()}  ({it['why']})")
        lines.append(f"  route: {it['route']}")
        if it["roots"]:
            lines.append(f"  roots: {', '.join(it['roots'])}")
        if it.get("budget_s"):
            lines.append(f"  pass budget: {it['budget_s'] // 60} min")
        for i, s in enumerate(it["steps"], 1):
            lines.append(f"  {i}. {s}")
        lines.append("")
    lines.append("Passes run one machine at a time, in this order. A machine that cannot be reached is "
                 "recorded unknown with the reason; its earlier rows are kept.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- run

def _route_guard(target_id: str, path: str = ROUTE_TARGETS) -> dict | None:
    with open(path, encoding="utf-8") as fh:
        for t in json.load(fh).get("targets", []):
            if t.get("id") == target_id:
                return t.get("guard")
    return None


def ingest_guard_command() -> str:
    return "systemctl list-units --type=service --state=active --no-legend --plain 'ingest-*'"


def read_ingest_guard(via: dict, run=subprocess.run) -> tuple[str, str]:
    """('idle'|'active'|'unknown', why). Read-only systemctl on the via machine."""
    try:
        check_route(via, run)
        argv = _ssh(via["route"], ingest_guard_command())
        r = run(argv, capture_output=True, text=True, timeout=30, stdin=subprocess.DEVNULL)
    except Unreadable as e:
        return "unknown", str(e)
    except (OSError, subprocess.SubprocessError) as e:
        return "unknown", type(e).__name__
    if r.returncode != 0:
        return "unknown", f"systemctl rc={r.returncode}"
    units = [ln.split()[0] for ln in r.stdout.splitlines() if ln.strip()]
    return ("active", "running: " + ", ".join(units)) if units else ("idle", "no ingest unit active")


def run_pass(con, machine: dict, all_machines: list[dict], now: dt.datetime | None,
             minutes: float = DEFAULT_MINUTES, mbps: float = DEFAULT_MBPS, lock_py: str | None = None,
             transport=None, slot=None, run=subprocess.run, standby=None, log=print,
             clock=time.monotonic) -> dict:
    """One machine pass. Returns {machine, verdict: done|partial|unknown|deferred, why}."""
    mid = machine["id"]
    roots = roots_of(machine)
    route = (machine.get("route") or {}).get("kind")
    if route == "none" or not roots:
        why = (machine.get("route") or {}).get("reason") or machine["sources"].get("why") or "nothing to read"
        fi().record_unreachable(con, mid, "(machine)", why)
        return {"machine": mid, "verdict": "unknown", "why": why}
    ok, why, until = window(machine, now)
    if not ok:
        return {"machine": mid, "verdict": "deferred", "why": why}
    skipped = []
    by_id = {m["id"]: m for m in all_machines}
    for g in machine["sources"].get("guards", []):
        if g["kind"] == "standby":
            guard = _route_guard(g["guard_from"])
            if guard is None:
                return {"machine": mid, "verdict": "deferred", "why": "standby guard not configured"}
            state, gwhy = (standby or (lambda gd: slot_mod()._route().read_standby_guard(gd, run=run)))(guard)
            if state != "ok":
                return {"machine": mid, "verdict": "deferred", "why": f"standby guard {state}: {gwhy}"}
        elif g["kind"] == "ingest":
            state, gwhy = read_ingest_guard(by_id[g["via"]], run=run)
            if state != "idle":
                skipped.append(g["subtree"])
                log(f"{mid}: {g['subtree']} not entered this pass (ingest guard {state}: {gwhy})")
    budget = minutes * 60 if until is None else min(minutes * 60, until)
    deadline = clock() + budget
    S = slot_mod()
    slot = slot or (lambda job: S.scan_slot(job, lock_py))
    results = []
    try:
        with slot(f"cluster-read-{mid}"):
            if route == "local":
                return _local_pass(con, machine, budget, mbps, log)
            tr = transport or SshTransport(machine, run=run)
            for r in roots:
                rem = deadline - clock()
                if rem <= 0:
                    results.append("partial")
                    break
                mine = [s for s in skipped if _under(fi().norm(s), fi().norm(r["path"]))]
                try:
                    lines = peek(tr.stream("walk", walk_job(machine, r, rem, extra_skip=mine),
                                           rem + WATCHDOG_SLACK_S))
                except Unreadable as e:
                    fi().record_unreachable(con, mid, r["path"], str(e))
                    results.append("unknown")
                    log(f"{mid} {r['path']}: unknown ({e})")
                    continue
                sc = ingest_walk(con, mid, r["path"], lines, machine["sources"]["excludes"], log,
                                 guard_skipped=mine)
                results.append(sc["state"])
            if any(x in ("complete", "partial") for x in results) and deadline - clock() > 0:
                try:
                    hs = hash_on_machine(con, mid, tr, mbps, deadline, log=log, clock=clock)
                    if hs["stopped"]:
                        results.append("partial")
                except Unreadable as e:
                    log(f"{mid}: hashing stopped, {e}; unhashed files stay unknown")
                    results.append("partial")
    except S.SlotRefused as e:
        return {"machine": mid, "verdict": "deferred", "why": str(e)}
    if results and all(x == "unknown" or x == "unreachable" for x in results):
        return {"machine": mid, "verdict": "unknown", "why": "no root could be read"}
    verdict = "done" if results and all(x == "complete" for x in results) else "partial"
    return {"machine": mid, "verdict": verdict, "why": ", ".join(results)}


def _local_pass(con, machine: dict, budget_s: float, mbps: float, log) -> dict:
    F = fi()
    log(f"priority: {F.lower_priority()}")
    b = F.Budget(budget_s)
    states = []
    for r in roots_of(machine):
        if not os.path.isdir(r["path"]):
            F.record_unreachable(con, machine["id"], r["path"], "root not found (unknown, not empty)")
            states.append("unknown")
            continue
        sc = F.scan(con, machine["id"], r["path"], tuple(machine["sources"]["excludes"]), b, log=log)
        states.append(sc["state"])
    if not b.out():
        hs = F.hash_candidates(con, mbps, budget=b, machine=machine["id"], log=log)
        if hs["stopped"]:
            states.append("partial")
    verdict = "done" if states and all(s == "complete" for s in states) else (
        "unknown" if states and all(s == "unknown" for s in states) else "partial")
    return {"machine": machine["id"], "verdict": verdict, "why": ", ".join(states)}


def run(con, machines: list[dict], now_fn=pacific_now, **kw) -> list[dict]:
    """Every machine, one at a time, in order; the slot is taken and released per machine."""
    out = []
    for m in machines:
        res = run_pass(con, m, machines, now_fn(), **kw)
        kw.get("log", print)(f"{res['machine']}: {res['verdict']} ({res['why']})")
        out.append(res)
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="cluster_readers", description=__doc__.split("\n")[0])
    ap.add_argument("--targets", default=TARGETS)
    ap.add_argument("--sources", default=SOURCES)
    sub = ap.add_subparsers(dest="cmd")
    p = sub.add_parser("plan", help="dry run: list what a run would do (default; touches nothing)")
    p.add_argument("--machine", action="append")
    p.add_argument("--at", help="pretend Pacific time, YYYY-MM-DDTHH:MM (to see the night plan)")
    p.add_argument("--minutes", type=float, default=DEFAULT_MINUTES)
    p.add_argument("--json", action="store_true")
    r = sub.add_parser("run", help="read the named machines (one pass each, heavy slot per pass)")
    r.add_argument("--machine", action="append", required=True)
    r.add_argument("--db", default=None)
    r.add_argument("--minutes", type=float, default=DEFAULT_MINUTES, help="budget per machine pass")
    r.add_argument("--mbps", type=float, default=DEFAULT_MBPS, help="hash read cap on the machine, MB/s")
    r.add_argument("--heavy-lock", default=os.environ.get("HEAVY_LOCK_PY", ""))
    a = ap.parse_args(argv)
    machines = load_machines(a.targets, a.sources)
    if a.cmd in (None, "plan"):
        sel = getattr(a, "machine", None)
        ms = [m for m in machines if not sel or m["id"] in sel]
        if getattr(a, "at", None):
            from zoneinfo import ZoneInfo
            now = dt.datetime.fromisoformat(a.at).replace(tzinfo=ZoneInfo(PACIFIC))
        else:
            now = pacific_now()
        items = plan(ms, now, getattr(a, "minutes", DEFAULT_MINUTES))
        print(json.dumps(items, indent=1) if getattr(a, "json", False) else render_plan(items, now))
        return 0
    unknown = set(a.machine) - {m["id"] for m in machines}
    if unknown:
        print(f"no such machine: {', '.join(sorted(unknown))}")
        return 2
    F = fi()
    con = F.connect(a.db or F.default_db())
    res = run(con, [m for m in machines if m["id"] in a.machine], minutes=a.minutes, mbps=a.mbps,
              lock_py=a.heavy_lock)
    return 0 if all(x["verdict"] == "done" for x in res) else 2


if __name__ == "__main__":
    sys.exit(main())
