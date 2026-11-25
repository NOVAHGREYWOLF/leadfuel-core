"""NODE p16-3: read the R710 outage of 2026-11-20 from overlord's and the 710's own logs.

Why. Both nightly backups missed on 2026-11-21 for one cause: overlord's storage `r710-backup`
(NFS from the R710) was "not online" from overlord's boot at 15:32 PT on 11-20 until about 13:08 PT
on 11-21. The window was read once by hand (done/P07.md, 2c); why the 710 was down and why it
stayed down about 21 hours was never established. This tool turns that into a command that reads
LOG TEXT and says what the text proves, and, where it proves nothing, says UNKNOWN and lists what
was read. It never guesses a cause.

Read-only and offline. `explain` only reads files you hand it. `plan` prints the exact commands to
collect those files by hand; every one is an allowlisted read (journalctl, uptime, last, grep,
tail, ipmitool sel list, racadm getsel), asserted by `assert_read_only`. Nothing here connects to a
machine, so no production read happens until the owner or a desk runs the printed commands.

Verdict (first line of the report):
  EXPLAINED  outage window start and end, both from storage-offline lines, and a cause line from
             the 710's own record (iDRAC event log or `last -x`) that falls inside the window
  WINDOW     the window is known from overlord's journal, the cause is not (the 710's own log was
             not given, or holds no event inside the window)
  UNKNOWN    no storage-offline line was found. Missing input says UNKNOWN, never "no outage".

Usage:
    python outage_explainer.py plan
    python outage_explainer.py explain --overlord-journal j.txt [--r710-log s.txt] [--year 2026] [--json]

Stdlib only.
"""
import argparse
import datetime as dt
import json
import re
import shlex
import sys

STORAGE = "r710-backup"

# Verbs a collected command may start with. Anything else is refused by assert_read_only.
_READ_VERBS = {"journalctl", "uptime", "last", "grep", "tail", "ipmitool", "racadm", "pvesm", "df", "ping", "cat"}
# Subcommands of ipmitool / racadm that are reads. Everything else is refused.
_READ_SUB = {"ipmitool": {"sel"}, "racadm": {"getsel", "getsysinfo"}}
_SHELL_META = re.compile(r"[>|;&`$()<]")

MONTHS = {m: i for i, m in enumerate(
    ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"], 1)}

# journalctl short format: "Nov 20 15:33:54 overlord pvestatd[1234]: storage 'r710-backup' is not online"
_SHORT = re.compile(r"^([A-Z][a-z]{2})\s+(\d{1,2})\s+(\d\d):(\d\d):(\d\d)\s+(\S+)\s+(.*)$")
# short-iso: "2026-11-20T15:33:54-0800 overlord ..." (also with +00:00 or Z)
_ISO = re.compile(r"^(\d{4})-(\d\d)-(\d\d)[T ](\d\d):(\d\d):(\d\d)(?:[.,]\d+)?([+-]\d\d:?\d\d|Z)?\s+(\S+)\s+(.*)$")

_OFFLINE = re.compile(r"storage\s+'%s'\s+is\s+not\s+online" % re.escape(STORAGE), re.I)
_BOOT = re.compile(r"(?:-- Boot|Linux version|systemd\[1\]: Started|Reached target (?:Multi-User|Graphical))", re.I)
_RECOVER = re.compile(r"%s.*(?:nfsrahead|mounted|is online|activated)|(?:nfsrahead|mounted).*%s" % (STORAGE, STORAGE), re.I)

# The 710's own record. A cause is named only when one of these appears inside the window.
_CAUSES = [
    ("ac_power_loss", re.compile(r"AC\s+(?:power\s+)?(?:lost|loss)|power\s+(?:input\s+)?lost|input\s+voltage\s+lost", re.I)),
    ("power_supply_fault", re.compile(r"power\s+suppl(?:y|ies).*(?:fail|fault|redundancy\s+lost|absent)", re.I)),
    ("unclean_shutdown", re.compile(r"crash|unexpected\s+shutdown|system\s+(?:hang|halt)|watchdog|kernel\s+panic", re.I)),
    ("power_on_restored", re.compile(r"AC\s+(?:power\s+)?restored|power\s+(?:button|on)|system\s+boot", re.I)),
]


def assert_read_only(command):
    """Refuse any collected command that is not a plain read. Returns the command for chaining."""
    if _SHELL_META.search(command):
        raise ValueError("shell metacharacter in %r" % command)
    toks = shlex.split(command)
    if not toks or toks[0] not in _READ_VERBS:
        raise ValueError("not an allowlisted read: %r" % command)
    sub = _READ_SUB.get(toks[0])
    if sub and (len(toks) < 2 or toks[1] not in sub):
        raise ValueError("not an allowlisted read: %r" % command)
    return command


def plan():
    """The collection commands, with the host each runs on. Printed, never run."""
    steps = [
        ("overlord", "journalctl --since '2026-11-20 14:00' --until '2026-11-21 14:00' --no-pager -o short-iso -g r710-backup"),
        ("overlord", "uptime -s"),
        ("overlord", "last -x reboot shutdown -n 10"),
        ("overlord", "tail -n 40 /var/log/vault-sync.status"),
        ("overlord", "tail -n 40 /var/log/greywolf-state.status"),
        ("r710", "uptime -s"),
        ("r710", "last -x reboot shutdown -n 10"),
        ("r710", "journalctl --list-boots --no-pager"),
        ("r710-idrac", "racadm getsel"),
    ]
    return [{"host": h, "command": assert_read_only(c)} for h, c in steps]


def _tzoffset(tok):
    if not tok or tok == "Z":
        return dt.timedelta(0)
    sign = -1 if tok[0] == "-" else 1
    t = tok[1:].replace(":", "")
    return sign * dt.timedelta(hours=int(t[:2]), minutes=int(t[2:]))


def parse_line(line, year):
    """(naive-local datetime, text) or None. Short-format lines need `year`; ISO lines carry it."""
    line = line.strip()
    m = _ISO.match(line)
    if m:
        y, mo, d, h, mi, s = (int(m.group(i)) for i in range(1, 7))
        return dt.datetime(y, mo, d, h, mi, s), m.group(9)
    m = _SHORT.match(line)
    if m and m.group(1) in MONTHS and year:
        mo, d, h, mi, s = MONTHS[m.group(1)], int(m.group(2)), int(m.group(3)), int(m.group(4)), int(m.group(5))
        try:
            return dt.datetime(year, mo, d, h, mi, s), m.group(7)
        except ValueError:
            return None
    return None


def _scan(text, year):
    rows = []
    for line in (text or "").splitlines():
        p = parse_line(line, year)
        if p:
            rows.append(p)
    return rows


def explain(overlord_text, r710_text=None, year=None):
    """Return the report dict. Times are the log's own local clock; no zone is invented."""
    read = []
    rows = _scan(overlord_text, year)
    read.append("overlord journal: %d dated lines" % len(rows))
    offline = [t for t, msg in rows if _OFFLINE.search(msg)]
    boots = [t for t, msg in rows if _BOOT.search(msg)]
    recov = [t for t, msg in rows if _RECOVER.search(msg) and not _OFFLINE.search(msg)]
    undated = [ln for ln in (overlord_text or "").splitlines() if ln.strip() and not parse_line(ln, year)]
    if undated and not rows and any(_SHORT.match(ln.strip()) for ln in undated) and not year:
        read.append("short-format lines present but no --year given, so none could be dated")
    if not offline:
        return {"verdict": "UNKNOWN", "reason": "no '%s is not online' line was found in what was read" % STORAGE,
                "window": None, "cause": None, "read": read}
    start, end_offline = min(offline), max(offline)
    # The window ends at the first recovery line after the last offline line, else at the last offline line.
    after = [t for t in recov if t >= end_offline]
    end = min(after) if after else end_offline
    recovered = bool(after)
    window = {"start_seen": start.isoformat(), "end": end.isoformat(), "recovered_line_seen": recovered,
              "hours": round((end - start).total_seconds() / 3600.0, 2), "offline_lines": len(offline)}
    first_boot_before = [b for b in boots if b <= start]
    if first_boot_before:
        window["overlord_boot_before_start"] = max(first_boot_before).isoformat()
    note = ("start_seen is the first not-online line that was read, not when the 710 went down; "
            "overlord's own boot bounds how early it can be seen")
    if not r710_text:
        read.append("710's own log: not given")
        return {"verdict": "WINDOW", "reason": "window from overlord's journal; the 710's own record was not read, "
                "so why it went down and why it stayed down are UNKNOWN", "window": window, "cause": None,
                "note": note, "read": read}
    r_rows = _scan(r710_text, year)
    read.append("710 log: %d dated lines" % len(r_rows))
    pad = dt.timedelta(hours=1)
    hits = []
    for t, msg in r_rows:
        if start - pad <= t <= end + pad:
            for name, rx in _CAUSES:
                if rx.search(msg):
                    hits.append({"at": t.isoformat(), "kind": name, "line": msg[:160]})
    # A boot-only hit proves a restart, not a cause.
    causal = [h for h in hits if h["kind"] != "power_on_restored"]
    if not causal:
        reason = ("the 710's log was read and holds no power-loss, fault or crash event inside the window"
                  + ("; it does show a power-on/boot event" if hits else ""))
        return {"verdict": "WINDOW", "reason": reason, "window": window, "cause": None, "evidence": hits,
                "note": note, "read": read}
    return {"verdict": "EXPLAINED", "reason": "the 710's own record has %s at %s" % (causal[0]["kind"], causal[0]["at"]),
            "window": window, "cause": causal[0]["kind"], "evidence": hits, "note": note, "read": read}


def render(rep):
    out = ["%s: %s" % (rep["verdict"], rep["reason"])]
    w = rep.get("window")
    if w:
        out.append("window: %s to %s (%.2f h, %d not-online lines, recovery line %s)" % (
            w["start_seen"], w["end"], w["hours"], w["offline_lines"], "seen" if w["recovered_line_seen"] else "NOT seen"))
    if rep.get("note"):
        out.append("note: " + rep["note"])
    for h in rep.get("evidence") or []:
        out.append("evidence: %s %s %s" % (h["at"], h["kind"], h["line"]))
    out.append("read: " + "; ".join(rep["read"]))
    return "\n".join(out)


def _read(path):
    if not path:
        return None
    with open(path, "r", encoding="utf-8", errors="replace") as fh:
        return fh.read()


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("plan")
    ex = sub.add_parser("explain")
    ex.add_argument("--overlord-journal", required=True)
    ex.add_argument("--r710-log")
    ex.add_argument("--year", type=int)
    ex.add_argument("--json", action="store_true")
    a = ap.parse_args(argv)
    if a.cmd == "plan":
        for s in plan():
            print("%-11s %s" % (s["host"], s["command"]))
        return 0
    rep = explain(_read(a.overlord_journal), _read(a.r710_log), a.year)
    print(json.dumps(rep, indent=1) if a.json else render(rep))
    return {"EXPLAINED": 0, "WINDOW": 0, "UNKNOWN": 3}[rep["verdict"]]


if __name__ == "__main__":
    sys.exit(main())
