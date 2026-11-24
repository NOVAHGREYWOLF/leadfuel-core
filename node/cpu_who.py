"""NODE desks-3-6: who is holding GREYWOLF's CPU?  Read-only: reads the process list, stops nothing.

Why. On 2026-11-23 the PC sat at 100 percent at every sample. Measured that day: no single process
held it. About 25 claude.exe, 20 node, 25 python and 40 bash were each a few percent; Windows
Defender, WSL and dwm took more; kernel time was 50 to 59 percent with 40k to 53k context switches
a second; and two `find /` scans launched from Git Bash by agent sessions had been walking every
drive for over two hours (one at 3,965 CPU-seconds), because in Git Bash `/` is the whole machine.
This tool turns that one-off investigation into one command, so the next "it is at 100 percent" is
answered from numbers and not guessed at.

Two samples of the process list, N seconds apart (default 10), each one `Get-CimInstance
Win32_Process` (the cumulative kernel and user CPU of every process). The difference, divided by
the seconds and the logical CPU count, is each process's share of the WHOLE machine. Shares are
summed by process name. The machine's own busy figure comes from GetSystemTimes over the same
interval, so what the processes do not explain (interrupts, DPCs, a process that exited between the
samples) is shown as its own line and is never folded into a name.

Verdict, the first line:
  SATURATED  the machine was 90 percent busy or more over the interval
  BUSY       60 percent or more
  QUIET      under 60 percent
  UNKNOWN    a sample could not be read, or the interval was under a second. A reading that cannot
             be taken says UNKNOWN, never QUIET.

Leaked scans. A `find` (GNU, not the Windows text filter in System32) whose search root is `/` or a
drive root and that has been running 30 minutes or more is listed with its parent chain, so the
session that left it behind can be named. It is only LISTED here. Stopping one is the owner's step:
node/windows/Stop-LeakedScans.ps1 (dry run by default, `-Apply` to stop). Command lines are never
printed in full (they can hold tokens): only the root and the process names.

Usage:
    python cpu_who.py                          sample 10 s, print the verdict, the top names, any leaks
    python cpu_who.py --seconds 5 --top 12
    python cpu_who.py --clients-of 11434       who holds connections to a local port right now (one netstat read)
    python cpu_who.py --ollama-rate            how often Ollama is being asked things, from its log's last 1 MiB

Stdlib only. Windows for the live sample; the parsing and the rules are plain functions.
"""
import argparse
import ctypes
import json
import os
import re
import subprocess
import sys
import time
from collections import namedtuple

Proc = namedtuple("Proc", "pid ppid name exe cmd created cpu_s")   # created: epoch seconds; cpu_s cumulative
Row = namedtuple("Row", "name procs pct cpu_s")
Attribution = namedtuple("Attribution", "rows explained_pct exited started no_cpu")
Conn = namedtuple("Conn", "local remote state pid")

SATURATED, BUSY, QUIET, UNKNOWN = "SATURATED", "BUSY", "QUIET", "UNKNOWN"
SATURATED_PCT, BUSY_PCT = 90.0, 60.0
LEAK_MIN_AGE_MIN = 30

PS_SNAPSHOT = (
    "[Console]::OutputEncoding=[Text.Encoding]::UTF8;"
    "Get-CimInstance Win32_Process -Property ProcessId,ParentProcessId,Name,ExecutablePath,CommandLine,CreationDate,"
    "KernelModeTime,UserModeTime | Where-Object { $_.ProcessId -ne $PID } | "
    "ForEach-Object { [pscustomobject]@{ pid=$_.ProcessId; ppid=$_.ParentProcessId;"
    " name=$_.Name; exe=$_.ExecutablePath; cmd=$_.CommandLine;"
    " created=$(if ($_.CreationDate) { [DateTimeOffset]::new($_.CreationDate).ToUnixTimeSeconds() } else { $null });"
    " kernel=$_.KernelModeTime; user=$_.UserModeTime } } | ConvertTo-Json -Compress"
)


# ---------------------------------------------------------------- reading a snapshot

def parse_snapshot(text):
    """(procs, bad) from the JSON the PowerShell line above prints. One object or a list. A row
    that lacks a pid or a name counts as bad. Missing CPU counters give cpu_s None, never 0."""
    doc = json.loads(text)
    if isinstance(doc, dict):
        doc = [doc]
    if not isinstance(doc, list):
        raise ValueError("the snapshot is not a list of processes")
    procs, bad = [], 0
    for row in doc:
        try:
            pid, name = int(row["pid"]), str(row["name"])
            k, u = row.get("kernel"), row.get("user")
            cpu = (int(k) + int(u)) / 1e7 if k is not None and u is not None else None
            created = int(row["created"]) if row.get("created") is not None else None
            procs.append(Proc(pid, int(row.get("ppid") or 0), name, row.get("exe"), row.get("cmd"), created, cpu))
        except (KeyError, TypeError, ValueError, AttributeError):
            bad += 1
    return procs, bad


# ---------------------------------------------------------------- the attribution

def attribute(before, after, interval_s, ncpu):
    """Each name's share of the whole machine over the interval. A process is the same process in both
    samples only when pid AND creation time match (pids are reused). A process that started inside the
    interval counts all its CPU; one that exited inside it cannot be counted and is only tallied."""
    b = {(p.pid, p.created): p for p in before}
    a = {(p.pid, p.created): p for p in after}
    by_name, no_cpu = {}, 0
    for key, p in a.items():
        if p.cpu_s is None:
            no_cpu += 1
            continue
        old = b.get(key)
        if old is not None:
            if old.cpu_s is None:
                no_cpu += 1
                continue
            delta = p.cpu_s - old.cpu_s
            if delta < 0:
                no_cpu += 1
                continue
        else:
            delta = p.cpu_s
        n, d = by_name.get(p.name, (0, 0.0))
        by_name[p.name] = (n + 1, d + delta)
    if interval_s <= 0 or ncpu < 1:
        raise ValueError("a share needs a positive interval and CPU count")
    scale = 100.0 / (interval_s * ncpu)
    rows = sorted((Row(name, n, d * scale, d) for name, (n, d) in by_name.items()), key=lambda r: -r.pct)
    return Attribution(rows, sum(r.pct for r in rows), sum(1 for k in b if k not in a),
                       sum(1 for k in a if k not in b), no_cpu)


def verdict(busy_pct, interval_s):
    """busy_pct is the machine's own figure (GetSystemTimes) or None. Unreadable stays UNKNOWN."""
    if busy_pct is None or interval_s < 1.0:
        return UNKNOWN
    if busy_pct >= SATURATED_PCT:
        return SATURATED
    return BUSY if busy_pct >= BUSY_PCT else QUIET


# ---------------------------------------------------------------- leaked scans

def tokenize(cmd):
    """Split a Windows command line on spaces outside double quotes; quotes are dropped. No escapes:
    a backslash in a path stays a backslash."""
    out, cur, quoted, started = [], [], False, False
    for ch in cmd or "":
        if ch == '"':
            quoted, started = not quoted, True
        elif ch.isspace() and not quoted:
            if started:
                out.append("".join(cur))
                cur, started = [], False
        else:
            cur.append(ch)
            started = True
    if started:
        out.append("".join(cur))
    return out


_WINDOWS_FIND_DIR = re.compile(r"\\(system32|syswow64|sysnative)\\", re.IGNORECASE)
_DRIVE_ROOT = re.compile(r"^[A-Za-z]:[\\/]+$")
_MSYS_DRIVE = re.compile(r"^/[A-Za-z]/*$")
_FIND_GLOBAL_OPTS = {"-H", "-L", "-P"}


def search_roots(cmd):
    """The search roots of a GNU find command line (everything before the first expression), or []
    when the line is not readable or has no path (`find -name x` searches `.`, not a leak)."""
    toks = tokenize(cmd)[1:]
    roots = []
    for tok in toks:
        if tok in _FIND_GLOBAL_OPTS:
            continue
        if tok.startswith("-") or tok in ("(", "!", ")"):
            break
        roots.append(tok)
    return roots


def is_root(path):
    return path == "/" or path == "//" or bool(_DRIVE_ROOT.match(path))


def find_leaks(procs, now, min_age_min=LEAK_MIN_AGE_MIN):
    """(leaks, ambiguous, unreadable) among the running find.exe processes.

    leak       GNU find, older than min_age_min, with `/` or a drive root among its search roots.
    ambiguous  a root of the form /c or /f that is a Git Bash drive mount for GNU find but is also
               one of the Windows find switches (/c /i /n /v); counted only when the executable path
               does not settle which find it is.
    unreadable find.exe whose command line (or start time) could not be read, so it could not be judged."""
    leaks, ambiguous, unreadable = [], [], []
    for p in procs:
        if p.name.lower() != "find.exe":
            continue
        if p.exe and _WINDOWS_FIND_DIR.search(p.exe):
            continue                     # the Windows text filter: it has no search root
        if not p.cmd or p.created is None:
            unreadable.append(p)
            continue
        if now - p.created < min_age_min * 60:
            continue
        roots = search_roots(p.cmd)
        if any(is_root(r) for r in roots):
            leaks.append(p)
        elif any(_MSYS_DRIVE.match(r) for r in roots):
            (leaks if p.exe else ambiguous).append(p)
    return leaks, ambiguous, unreadable


def parent_chain(procs, pid, depth=4):
    """["bash.exe(123)", "claude.exe(45)", ...] from the process up, names and pids only. When a
    parent is no longer running the chain ends with "pid N gone": Windows keeps the parent pid of
    an orphan, and the pid may since belong to a different process, so a parent whose start time is
    later than the child's is also reported as gone (the pid was reused)."""
    by_pid = {p.pid: p for p in procs}
    chain, cur, seen = [], by_pid.get(pid), set()
    while cur is not None and len(chain) < depth and cur.pid not in seen:
        seen.add(cur.pid)
        parent = by_pid.get(cur.ppid)
        if parent is None or (parent.created and cur.created and parent.created > cur.created):
            if cur.ppid:
                chain.append("pid %d gone" % cur.ppid)
            break
        chain.append("%s(%d)" % (parent.name, parent.pid))
        cur = parent
    return chain


# ---------------------------------------------------------------- who holds connections to a port

_NETSTAT = re.compile(r"^\s*TCP\s+(?P<local>\S+)\s+(?P<remote>\S+)\s+(?P<state>[A-Z_]+)\s+(?P<pid>\d+)\s*$")


def parse_netstat(text):
    """Connections from `netstat -ano -p tcp`. Rows it cannot read are skipped (header lines)."""
    out = []
    for line in (text or "").splitlines():
        m = _NETSTAT.match(line)
        if m:
            out.append(Conn(m.group("local"), m.group("remote"), m.group("state"), int(m.group("pid"))))
    return out


def _port(addr):
    try:
        return int(addr.rsplit(":", 1)[1])
    except (IndexError, ValueError):
        return None


def clients_of(conns, procs, port):
    """Who is on the client end of connections to `port`. Returns (by_owner, anonymous, listeners):
    by_owner maps 'name(pid)' to a count of open connections; anonymous maps a state (TIME_WAIT,
    ...) to a count of sockets Windows records with pid 0, whose owner is not recorded at all."""
    names = {p.pid: p.name for p in procs}
    by_owner, anonymous, listeners = {}, {}, []
    for c in conns:
        if c.state == "LISTENING":
            if _port(c.local) == port:
                listeners.append(c.pid)
            continue
        if _port(c.remote) != port:
            continue
        if c.pid == 0:
            anonymous[c.state] = anonymous.get(c.state, 0) + 1
        else:
            key = "%s(%d)" % (names.get(c.pid, "pid-not-in-list"), c.pid)
            by_owner[key] = by_owner.get(key, 0) + 1
    return by_owner, anonymous, listeners


# ---------------------------------------------------------------- how fast is Ollama being asked things

_GIN = re.compile(r'^\[GIN\] (?P<y>\d{4})/(?P<mo>\d\d)/(?P<d>\d\d) - (?P<h>\d\d):(?P<mi>\d\d):(?P<s>\d\d) \| (?P<status>\d{3}) \|'
                  r'[^|]*\|\s*(?P<ip>\S+)\s*\|\s*(?P<method>[A-Z]+)\s+"(?P<path>[^"?]*)')
_POLL_PATHS = ("/api/tags", "/api/version", "/api/ps")
Gin = namedtuple("Gin", "t method path status")      # t: seconds since midnight of the first day, as a float


def parse_gin(text):
    """(entries, bad) from Ollama's own request log. t is a number of seconds, day boundaries
    included, so gaps and rates are plain subtraction. Lines that are not request lines are skipped;
    a `[GIN]` line that does not parse counts as bad."""
    import datetime as dt
    out, bad, first = [], 0, None
    for line in (text or "").splitlines():
        if not line.startswith("[GIN]"):
            continue
        m = _GIN.match(line)
        if not m:
            bad += 1
            continue
        when = dt.datetime(int(m["y"]), int(m["mo"]), int(m["d"]), int(m["h"]), int(m["mi"]), int(m["s"]))
        first = first or when
        out.append(Gin((when - first).total_seconds(), m["method"], m["path"], int(m["status"])))
    return out, bad


def report_ollama_rate(entries, bad=0):
    """(first_line, evidence) from request-log entries. POLLING-DOMINATED when 95 percent or more of
    the requests are status calls (tags, version, ps); the log has no client address or agent, so
    the rate says how often, never who: pair it with --clients-of."""
    if len(entries) < 20:
        return "UNKNOWN only %d request line(s) in the part of the log that was read" % len(entries), []
    span = entries[-1].t - entries[0].t
    if span < 5:
        return "UNKNOWN the request lines span only %.0f s" % span, []
    per = {}
    for e in entries:
        per.setdefault((e.method, e.path), []).append(e.t)
    polls = sum(len(v) for (m, p), v in per.items() if m == "GET" and p in _POLL_PATHS)
    work = sum(len(v) for (m, p), v in per.items() if m == "POST")
    rate = len(entries) / span
    kind = "POLLING-DOMINATED" if polls >= 0.95 * len(entries) else "MIXED"
    first = "%s %.2f requests/s over %.1f min: %d status polls, %d POST (inference or other work)" % (
        kind, rate, span / 60.0, polls, work)
    ev = []
    for (m, p), ts in sorted(per.items(), key=lambda kv: -len(kv[1]))[:6]:
        gaps = sorted(b - a for a, b in zip(ts, ts[1:]) if b > a)
        med = "%.1f s" % gaps[len(gaps) // 2] if gaps else "n/a"
        ev.append("%-4s %-16s %5d  %.2f/s  median gap between calls %s" % (m, p, len(ts), len(ts) / span, med))
    ev.append("the request log carries no client address or user agent: this says how often, not who")
    if bad:
        ev.append("%d [GIN] line(s) could not be read" % bad)
    return first, ev


def read_tail_text(path, window=1 << 20):
    size = os.path.getsize(path)
    with open(path, "rb") as fh:
        if size > window:
            fh.seek(size - window)
        data = fh.read()
    text = data.decode("utf-8", "replace")
    return text.split("\n", 1)[1] if size > window and "\n" in text else text


def default_ollama_log(env=os.environ):
    base = env.get("LOCALAPPDATA")
    return os.path.join(base, "Novah", "Prime", "services", "ollama.log") if base else None


# ---------------------------------------------------------------- live readings (Windows)

class _FILETIME(ctypes.Structure):
    _fields_ = [("lo", ctypes.c_uint32), ("hi", ctypes.c_uint32)]


def system_times():
    """(idle, kernel_incl_idle, user) in 100 ns units from GetSystemTimes, or None off Windows.
    Reads three counters; sends nothing."""
    if os.name != "nt":
        return None
    try:
        idle, kern, user = _FILETIME(), _FILETIME(), _FILETIME()
        if not ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kern), ctypes.byref(user)):
            return None
        return tuple((f.hi << 32) | f.lo for f in (idle, kern, user))
    except (OSError, AttributeError):
        return None


def machine_busy_pct(t0, t1):
    """Percent of the machine's CPU time not idle between two system_times() readings, or None."""
    if not t0 or not t1:
        return None
    idle = t1[0] - t0[0]
    total = (t1[1] - t0[1]) + (t1[2] - t0[2])      # kernel time already includes idle
    if total <= 0:
        return None
    return max(0.0, min(100.0, 100.0 * (1.0 - idle / total)))


def read_snapshot_live(timeout=60):
    out = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", PS_SNAPSHOT],
                         capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if out.returncode != 0:
        raise OSError("powershell exit %d: %s" % (out.returncode, out.stderr.decode("utf-8", "replace").strip()[:200]))
    return out.stdout.decode("utf-8", "replace").lstrip("﻿")


def read_netstat_live(timeout=30):
    out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, timeout=timeout, stdin=subprocess.DEVNULL)
    if out.returncode != 0:
        raise OSError("netstat exit %d" % out.returncode)
    return out.stdout.decode("utf-8", "replace")


# ---------------------------------------------------------------- the report

def short_age(seconds):
    m = int(seconds // 60)
    return "%d min" % m if m < 120 else "%d h %02d min" % (m // 60, m % 60)


def report_cpu(before, after, interval_s, ncpu, busy_pct, now, top=10):
    """(first_line, evidence_lines) for two snapshots. Pure: nothing is read here."""
    att = attribute(before, after, interval_s, ncpu)
    v = verdict(busy_pct, interval_s)
    if busy_pct is None:
        first = "%s the machine's own busy figure could not be read; processes alone explain %.0f%% over %.1f s on %d logical CPUs" \
                % (v, att.explained_pct, interval_s, ncpu)
    else:
        first = "%s machine %.0f%% busy over %.1f s on %d logical CPUs; processes explain %.0f%% of it" \
                % (v, busy_pct, interval_s, ncpu, att.explained_pct)
    ev = ["top by name (share of the whole machine; process count):"]
    for r in att.rows[:top]:
        ev.append("  %-26s %5.1f%%  %3d proc(s)" % (r.name, r.pct, r.procs))
    if len(att.rows) > top:
        rest = att.rows[top:]
        ev.append("  %-26s %5.1f%%  %3d name(s)" % ("(all the others)", sum(r.pct for r in rest), len(rest)))
    if busy_pct is not None:
        gap = busy_pct - att.explained_pct
        ev.append("not explained by any process: %.0f points (interrupts, DPCs, %d process(es) that exited during the "
                  "interval and %d that started, and anything Windows hides from this query)" % (gap, att.exited, att.started))
    if att.no_cpu:
        ev.append("%d process(es) gave no usable CPU counter and are not counted" % att.no_cpu)
    leaks, ambiguous, unreadable = find_leaks(after, now)
    if leaks:
        ev.append("LEAKED SCANS: %d find.exe from / or a drive root, running %d min or more:" % (len(leaks), LEAK_MIN_AGE_MIN))
        for p in leaks:
            ev.append("  pid %d  age %s  cpu %s s  root %s  parents %s" % (
                p.pid, short_age(now - p.created), "%.0f" % p.cpu_s if p.cpu_s is not None else "?",
                " ".join(r for r in search_roots(p.cmd) if is_root(r) or _MSYS_DRIVE.match(r)),
                " < ".join(parent_chain(after, p.pid)) or "none found"))
        ev.append("  to stop them the owner runs node/windows/Stop-LeakedScans.ps1 -Apply; this tool stops nothing")
    else:
        ev.append("leaked scans: none seen")
    if ambiguous:
        ev.append("%d find.exe with a /x style root could not be told apart from the Windows find switches (no "
                  "executable path): not listed as leaks" % len(ambiguous))
    if unreadable:
        ev.append("UNKNOWN for %d find.exe whose command line or start time could not be read" % len(unreadable))
    return first, ev


def report_clients(conns, procs, port):
    by_owner, anonymous, listeners = clients_of(conns, procs, port)
    names = {p.pid: p.name for p in procs}
    srv = ", ".join("%s(%d)" % (names.get(pid, "pid-not-in-list"), pid) for pid in listeners) or "nothing"
    if not listeners:
        first = "UNKNOWN nothing is listening on port %d, so there is no client to find" % port
    elif by_owner:
        first = "CLIENTS-SEEN %d open connection(s) to port %d from %d process(es)" % (
            sum(by_owner.values()), port, len(by_owner))
    else:
        first = "NO-OPEN-CLIENT no process holds an open connection to port %d right now" % port
    ev = ["listening: " + srv]
    for k in sorted(by_owner, key=lambda k: -by_owner[k]):
        ev.append("open: %-34s %d connection(s)" % (k, by_owner[k]))
    for state in sorted(anonymous):
        ev.append("%s: %d socket(s) with no recorded owner (Windows keeps pid 0 once a socket is closing): "
                  "the process that opened them cannot be named from this table" % (state, anonymous[state]))
    if not by_owner and anonymous:
        ev.append("so a client that opens a fresh connection for each request (HTTP/1.0, no keep-alive) will not "
                  "show here; sample again, or correlate the request times in the server's own log")
    return first, ev


def main(argv=None, out=sys.stdout, clock=time.time, mono=time.monotonic, sleep=time.sleep,
         snapshot_fn=read_snapshot_live, netstat_fn=read_netstat_live, times_fn=system_times, ncpu_fn=os.cpu_count):
    ap = argparse.ArgumentParser(description="Who is holding this PC's CPU?  Read-only.")
    ap.add_argument("--seconds", type=float, default=10.0, help="seconds between the two samples (default 10)")
    ap.add_argument("--top", type=int, default=10, help="how many process names to list")
    ap.add_argument("--clients-of", type=int, metavar="PORT", help="list who holds connections to this local port")
    ap.add_argument("--ollama-rate", action="store_true", help="how often Ollama is being asked things (reads its log's tail)")
    ap.add_argument("--ollama-log", help="Ollama's log (default under %%LOCALAPPDATA%%\\Novah\\Prime\\services)")
    args = ap.parse_args(argv)

    try:
        if args.ollama_rate:
            path = args.ollama_log or default_ollama_log()
            if not path:
                print("UNKNOWN no Ollama log path (no LOCALAPPDATA; pass --ollama-log)", file=out)
                return 2
            first, ev = report_ollama_rate(*parse_gin(read_tail_text(path)))
        elif args.clients_of is not None:
            procs, _ = parse_snapshot(snapshot_fn())
            first, ev = report_clients(parse_netstat(netstat_fn()), procs, args.clients_of)
        else:
            ncpu = ncpu_fn() or 0
            if ncpu < 1:
                print("UNKNOWN the logical CPU count could not be read", file=out)
                return 2
            # Each reading is stamped right after its query returns: the two queries take about the
            # same time, so the gap between the stamps is the gap between the counters.
            before_text = snapshot_fn()
            t0, s0 = times_fn(), mono()
            sleep(max(0.0, args.seconds))
            after_text = snapshot_fn()
            t1, s1 = times_fn(), mono()
            # This tool's own python is left out; the PowerShell reads leave themselves out ($PID).
            before = [p for p in parse_snapshot(before_text)[0] if p.pid != os.getpid()]
            after = [p for p in parse_snapshot(after_text)[0] if p.pid != os.getpid()]
            first, ev = report_cpu(before, after, s1 - s0, ncpu, machine_busy_pct(t0, t1), clock(), args.top)
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        print("UNKNOWN a reading could not be taken (%s: %s)" % (type(exc).__name__, exc), file=out)
        return 2
    print(first, file=out)
    for line in ev:
        print("  " + line, file=out)
    return 2 if first.startswith("UNKNOWN") else 0


if __name__ == "__main__":
    sys.exit(main())
