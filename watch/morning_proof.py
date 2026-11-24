#!/usr/bin/env python3
"""WATCH p16-2: the morning proof read. One read-only pass that writes OK, FAIL or UNKNOWN for every watcher.

WHY: three watchers failed silently for weeks (the nightly full run, the library nightly, the vault sync)
because nothing read their status, and two missed backups were found only because someone looked. This is
the no-install stopgap until the long-term alarm (oss-4) lands. Run it after 04:45 PT; it writes one dated
file, one line per watcher:

    <watcher id> | OK|FAIL|UNKNOWN | <evidence, with the time of the subject in Pacific>

THE RULE THIS FILE EXISTS TO KEEP: a check that cannot see its subject says UNKNOWN, never OK.
  * A source that is absent, unreadable, undated, dated in the future, or a copy taken before the run it
    should hold is UNKNOWN. So is a source with no result for the last scheduled slot. A stale OK is not OK.
  * A job that has a schedule is judged by the result at its last scheduled slot. A later manual success does
    not rescue a failed scheduled run (the timer is what the watcher is for), and a manual success alone does
    not prove the timer. FAIL stays FAIL. The window of today's run, while it is still open, falls back to
    yesterday's result and says so.
  * A count that may be cut off (a gh list that hit its limit) is not a count.
  * Every run first classifies built-in samples whose answers are known; if any is wrong every line is
    UNKNOWN, so a reader that always says OK cannot pass. A watcher that crashes becomes UNKNOWN; the others
    still run.
  * Thresholds are the constants below, in one place. They are WATCH's defaults, not the owner's rulings.

READ-ONLY, LOCAL-FIRST: it writes only the two report files in --out-dir. It reads local logs, copies of
files from other machines, and (through `gh`, read verbs only) GitHub. It never ssh-es anywhere: the sources
that live on overlord are read from COPIES that NODE must expose (see MIRRORS), and say UNKNOWN naming the
exact path until they do. The certificate lines make one TLS handshake each, sending no request, and only
with --live-tls (it is off by default; that is the owner's call). --offline runs no process and opens no
socket. Nothing is posted, mailed, pushed or spent. No secret is read.

THE EXIT CODE IS NOT THE VERDICT UNDER THE SCHEDULER (conhost does not pass it through: see
nightly_full_run.py). The dated file is the verdict.

COMMANDS (stdlib only, run by path):
  python watch/morning_proof.py run [--now ISO] [--out-dir DIR] [--inputs-dir DIR] [--hub DIR] [--offline]
        [--live-tls] [--nightly-log P] [--library-log P] [--archive-dir D] [--vault-log P] [--no-write]
  python watch/morning_proof.py selftest

MIRRORS (the exact files NODE must expose, fresh each morning before the read; the file's modification time
on this PC is taken as the moment the source was read, so write it fresh, do not preserve the source time):
  <inputs>/overlord/vzdump-tasks-index.txt    <- grep -a ':vzdump:103:' /var/log/pve/tasks/index | tail -n 40
  <inputs>/overlord/vault-sync.status         <- tail -n 40 /var/log/vault-sync.status
  <inputs>/overlord/greywolf-state.status     <- tail -n 40 /var/log/greywolf-state.status
  <inputs>/overlord/utilization.json          <- cat /var/lib/cluster/utilization.json
  <inputs>/router-desk-questions.json         <- the Router desk `questions` collection, one JSON object keyed
                                                 by card id (a desk with ArtifactData writes it; an optional
                                                 top-level "exported_at" is used as its time)
Times are shown in Pacific; every machine field is UTC.

SCHEDULE: watch/Register-MorningProof.ps1 (a dry run unless -Apply is given: registering a standing task is the
owner's yes). It copies this file and vault_sync_status.py to %LOCALAPPDATA%\\morning-proof and runs the copy at 04:50.

FIRST REAL READ, 2026-11-23 (read-only, on this PC), found three ways the first build could never say OK, each of
them quiet because the fixtures had been written to the guess and not to the real source; all three are fixed and
tested against the real shape:
  * library-nightly: a real success line has no `errors=` field (the writer adds the counter only on an error), and
    the reader demanded errors=0, so a real success read UNKNOWN for ever.
  * hub-tests-main: gh refuses to print a job log that holds colour codes unless given --allow-escape-sequences, so
    the count-guard line was unreadable on every run and the line read UNKNOWN for ever.
  * done-desks-unarchived: it read OK from "0 PASS" while the same review listed 132 CHECK FIRST. A review that
    could not tell for 132 desks cannot say none is done and unarchived: UNKNOWN until that count is zero.
"""
import argparse
import datetime as dt
import importlib.util
import json
import os
import re
import socket
import ssl
import subprocess
import sys
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Optional

SCHEMA = "watch.morning_proof/1"
OK, FAIL, UNKNOWN = "OK", "FAIL", "UNKNOWN"
STATUSES = (OK, FAIL, UNKNOWN)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT_DIR = r"F:\Claude Sessions\handoff\proof"
DEFAULT_INPUTS = os.path.join(DEFAULT_OUT_DIR, "inputs")
DEFAULT_NIGHTLY_LOG = r"F:\Claude Sessions\handoff\nightly-full-run.log"
DEFAULT_LIBRARY_LOG = r"F:\Claude Sessions\Document Library\NIGHTLY-LOG.txt"
DEFAULT_ARCHIVE_DIR = r"F:\Claude Sessions\handoff\watch-archive-review"
DEFAULT_HUB = r"F:\Leadfuel\repos\novahub"

# ---- thresholds: WATCH defaults, one place -----------------------------------------------------------
FUTURE_SLACK = dt.timedelta(minutes=10)          # a clock this far ahead is a clock that is wrong
WINDOW_BEFORE_MIN = 10                           # a slot's result may be stamped this long before it
# job id -> ((Pacific hour, minute) of the schedule, minutes after it that the result may be stamped)
SLOTS = {
    "vzdump-vm103": ((2, 15), 90),               # Proxmox job vault-nightly, VM 103 only
    "vault-sync": ((2, 45), 90),                 # root cron on overlord
    "greywolf-state-pull": ((4, 10), 60),        # root cron on overlord
    "nightly-full-run": ((4, 30), 330),          # the line is written at the END of a run of up to 4.75 h
    "library-nightly": ((2, 30), 90),
    "done-desks-unarchived": ((2, 0), 90),       # the nightly desk-archival review
}
UTIL_MIRROR_MAX_AGE = dt.timedelta(hours=3)      # the copy must be taken close to the read
UTIL_FEED_MAX_AGE = dt.timedelta(minutes=15)     # the feed runs every 5 minutes: three missed runs
CARDS_SNAPSHOT_MAX_AGE = dt.timedelta(hours=6)
CARD_ROUTE_GRACE = dt.timedelta(hours=2)         # the wake pass's own limit before it calls a card UNDELIVERED
HUB_TESTS_MAX_AGE = dt.timedelta(hours=72)
OPEN_PR_STALE = dt.timedelta(hours=72)           # a non-draft hub PR older than this is waiting on the train
PR_LIST_LIMIT = 300
CERT_FAIL_DAYS = 14.0                            # Let's Encrypt renews at 30 days left; 14 means it has not
EARLY_READ = (4, 45)                             # before this Pacific time last night's jobs may be running
FEED_TIME_FIELDS = ("generated_at", "generated", "updated_at", "timestamp", "ts", "at")
EVIDENCE_MAX = 400
CERT_HOSTS = (("cert-leadfuel-cloud", "leadfuel.cloud"), ("cert-www-leadfuel-cloud", "www.leadfuel.cloud"))

Result = namedtuple("Result", "ts state detail")      # state: ok | fail | unknown
Read = namedtuple("Read", "text mtime error")        # text None when missing or unreadable


# ---------------------------------------------------------------- time (Pacific by the US rule, no tzdata)

def _nth_sunday(year, month, n):
    d = dt.date(year, month, 1)
    return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))


def pacific(t):
    """UTC datetime -> (naive Pacific datetime, 'PST'|'PDT')."""
    t = t.astimezone(dt.timezone.utc)
    start = dt.datetime.combine(_nth_sunday(t.year, 3, 2), dt.time(10), tzinfo=dt.timezone.utc)
    end = dt.datetime.combine(_nth_sunday(t.year, 11, 1), dt.time(9), tzinfo=dt.timezone.utc)
    if start <= t < end:
        return (t - dt.timedelta(hours=7)).replace(tzinfo=None), "PDT"
    return (t - dt.timedelta(hours=8)).replace(tzinfo=None), "PST"


def pt_to_utc(naive):
    """Naive Pacific wall time -> UTC. A time that does not exist (the spring gap) reads as PST."""
    for off in (7, 8):
        cand = (naive + dt.timedelta(hours=off)).replace(tzinfo=dt.timezone.utc)
        if pacific(cand)[0] == naive:
            return cand
    return (naive + dt.timedelta(hours=8)).replace(tzinfo=dt.timezone.utc)


def fmt_pt(t):
    if t is None:
        return "unknown"
    local, abbr = pacific(t)
    h = local.hour % 12 or 12
    return "%s %d, %d:%02d %s %s" % (local.strftime("%b"), local.day, h, local.minute, "AM" if local.hour < 12 else "PM", abbr)


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def latest_slot_start(now, slot):
    """The most recent scheduled start at or before now (slot is a Pacific (hour, minute))."""
    local, _ = pacific(now)
    day = local.date()
    for back in (0, 1, 2):
        d = day - dt.timedelta(days=back)
        cand = pt_to_utc(dt.datetime(d.year, d.month, d.day, slot[0], slot[1]))
        if cand <= now:
            return cand
    return cand


_TS_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
_TS_COMPACT = re.compile(r"^\d{8}T\d{6}Z$")


def parse_ts(s):
    try:
        if _TS_ISO.match(s or ""):
            return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        if _TS_COMPACT.match(s or ""):
            return dt.datetime.strptime(s, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc)
    except ValueError:
        pass
    return None


def _clean(s, n=EVIDENCE_MAX):
    s = re.sub(r"\s+", " ", str(s)).strip().replace(" | ", " / ")
    return s if len(s) <= n else s[: n - 3] + "..."


@dataclass
class Finding:
    id: str
    status: str
    evidence: str
    subject_at: Optional[dt.datetime] = None

    def __post_init__(self):
        if self.status not in STATUSES:
            self.evidence, self.status = "reader gave an unrecognised status %r" % (self.status,), UNKNOWN
        self.evidence = _clean(self.evidence)


# ---------------------------------------------------------------- the scheduled-slot rule

def _slot_label(slot):
    return "%02d:%02d PT" % slot


def judge_scheduled(results, now, slot, win_after_min, observed_at=None, win_before_min=WINDOW_BEFORE_MIN, name="run"):
    """Judge a job by its result at its last scheduled slot. Returns (status, evidence, subject time).

    results: [Result]; observed_at: when the source was read (None is treated as 'before every window')."""
    wb, wa = dt.timedelta(minutes=win_before_min), dt.timedelta(minutes=win_after_min)
    future = [r for r in results if r.ts > now + FUTURE_SLACK]
    seen = sorted((r for r in results if r.ts <= now + FUTURE_SLACK), key=lambda r: r.ts)

    def in_window(start):
        return [r for r in seen if start - wb <= r.ts <= start + wa]

    cur = latest_slot_start(now, slot)
    start, note = cur, ""
    hit = in_window(cur)
    if not hit and now < cur + wa:
        start = latest_slot_start(cur - dt.timedelta(minutes=1), slot)
        hit = in_window(start)
        note = "today's %s run is not logged yet (window open until %s); " % (_slot_label(slot), fmt_pt(cur + wa))
    if not hit:
        why = "no %s result in the %s window of %s" % (name, _slot_label(slot), fmt_pt(cur))
        if future:
            why += "; %d future-dated line(s) ignored (the clock or the log is wrong)" % len(future)
        if observed_at is None or observed_at < cur + wa:
            why += "; the source was read %s, before that window closed" % fmt_pt(observed_at)
        if seen:
            why += "; newest line %s %s: %s" % (fmt_pt(seen[-1].ts), seen[-1].state, seen[-1].detail)
        else:
            why += "; the source holds no readable lines"
        return UNKNOWN, why, seen[-1].ts if seen else None
    r = hit[-1]
    later = [x for x in seen if x.ts > start + wa]
    tail = ""
    if later:
        tail = "; a later off-schedule line says %s at %s" % (later[-1].state, fmt_pt(later[-1].ts))
    status = {"ok": OK, "fail": FAIL}.get(r.state, UNKNOWN)
    return status, "%s%s [%s]%s" % (note, r.detail, fmt_pt(r.ts), tail), r.ts


# ---------------------------------------------------------------- line parsers (pure)

_VZ = re.compile(r"^UPID:[^:]*:[0-9A-Fa-f]+:[0-9A-Fa-f]+:([0-9A-Fa-f]+):vzdump:(\d+):[^:]*:\s*(.*)$")
_VS = re.compile(r"^(\d{8}T\d{6}Z)\s+(?:RESULT\s+)?(OK|UNKNOWN|FAILED|FAIL)\b\s*(.*)$")
_GW = re.compile(r"^(\d{8}T\d{6}Z)\s+(OK|SKIPPED|FAILED|FAIL)\b\s*(.*)$")
_NF = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (PASS|FAIL|UNKNOWN|SKIPPED-BUSY)\b(.*)$")
_LB = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) status=(\S+)\s*(.*)$")


def parse_vzdump(text, vmid):
    """Proxmox task index lines for `vzdump` of one VM. A line with no end or status is unknown."""
    out = []
    for line in (text or "").splitlines():
        m = _VZ.match(line.strip())
        if not m or int(m.group(2)) != int(vmid):
            continue
        ts = dt.datetime.fromtimestamp(int(m.group(1), 16), dt.timezone.utc)
        e = re.match(r"([0-9A-Fa-f]+)\s+(.*)$", m.group(3).strip())
        if not e:
            out.append(Result(ts, "unknown", "vzdump VM %s task has no end time or status (running, or killed)" % vmid))
        elif e.group(2).strip() == "OK":
            out.append(Result(ts, "ok", "vzdump VM %s OK" % vmid))
        else:
            out.append(Result(ts, "fail", "vzdump VM %s: %s" % (vmid, e.group(2).strip())))
    return out


def parse_vault_sync(text):
    out = []
    for line in (text or "").splitlines():
        m = _VS.match(line.strip())
        ts = parse_ts(m.group(1)) if m else None
        if not ts:
            continue
        word, rest = m.group(2), m.group(3)
        if word == "OK":
            d710, d620 = re.search(r"\bdrift710=(\S+)", rest), re.search(r"\bdrift620=(\S+)", rest)
            if not (d710 and d620):
                out.append(Result(ts, "unknown", "OK line without drift fields: the log format changed, or a dry run (%s)" % rest))
            elif d710.group(1) != "0" or d620.group(1) != "0":
                out.append(Result(ts, "fail", "vault-sync drift: %s" % rest))
            else:
                out.append(Result(ts, "ok", "vault-sync OK %s" % rest))
        elif word == "UNKNOWN":
            out.append(Result(ts, "unknown", "vault-sync UNKNOWN %s" % rest))
        else:
            out.append(Result(ts, "fail", "vault-sync FAIL %s" % rest))
    return out


def parse_greywolf(text):
    out = []
    for line in (text or "").splitlines():
        m = _GW.match(line.strip())
        ts = parse_ts(m.group(1)) if m else None
        if not ts:
            continue
        word, rest = m.group(2), m.group(3)
        if word == "OK":
            marks = re.findall(r"\bintegrity=(\S+)", rest)
            if not marks:
                out.append(Result(ts, "unknown", "OK line without an integrity mark: the log format changed (%s)" % rest))
            elif any(x != "ok" for x in marks):
                out.append(Result(ts, "fail", "greywolf-state integrity not ok: %s" % rest))
            else:
                out.append(Result(ts, "ok", "greywolf-state pull OK %s" % rest))
        elif word == "SKIPPED":
            out.append(Result(ts, "fail", "greywolf-state pull skipped: %s" % rest))
        else:
            out.append(Result(ts, "fail", "greywolf-state pull FAILED %s" % rest))
    return out


def parse_nightly_full(text):
    """The WATCH nightly full run log. PASS and FAIL pass through; UNKNOWN and SKIPPED-BUSY read unknown."""
    out = []
    for line in (text or "").splitlines():
        m = _NF.match(line)
        ts = parse_ts(m.group(1)) if m else None
        if not ts:
            continue
        kv = {k: v.strip('"') for k, v in re.findall(r'(\w+)=("[^"]*"|\S+)', m.group(3))}
        word = m.group(2)
        bits = ["main=%s" % kv.get("main", "?")[:7], "collected=%s" % kv.get("collected", "?")]
        if "failed" in kv:
            bits.append("failed=%s" % kv["failed"])
        if kv.get("reason"):
            bits.append("reason: %s" % kv["reason"])
        out.append(Result(ts, {"PASS": "ok", "FAIL": "fail"}.get(word, "unknown"), "nightly full run %s %s" % (word, " ".join(bits))))
    return out


def parse_library(text):
    """The library's NIGHTLY-LOG. Dry runs are skipped.

    The writer (Document Library/tools/nightly_capture.py, log_line) gives the line `status=ok` only when the run
    recorded no error, and it creates the `errors=N` counter only when an error is recorded. So a real success
    line carries NO `errors=` field (read from the writer and from all 7 real success lines on 2026-11-23: the
    first version of this reader required `errors=0`, so a real success could never read OK). ok therefore needs
    status=ok, dry=False and secs=<n> (a cut-off line has no secs) and no errors counter above 0."""
    out = []
    for line in (text or "").splitlines():
        m = _LB.match(line)
        ts = parse_ts(m.group(1)) if m else None
        if not ts:
            continue
        status, rest = m.group(2), m.group(3)
        dry, errs = re.search(r"\bdry=(True|False)\b", rest), re.search(r"\berrors=(\d+)\b", rest)
        if dry and dry.group(1) == "True":
            continue
        n = int(errs.group(1)) if errs else None
        text_m = re.search(r"errors_text=(\[.*\])\s*$", rest)
        why = ""
        if text_m:
            try:
                why = " (%s)" % "; ".join(str(x) for x in json.loads(text_m.group(1)))
            except ValueError:
                why = " (%s)" % text_m.group(1)[:120]
        complete = bool(dry) and bool(re.search(r"\bsecs=\d+\b", rest))
        if status == "ok" and n is not None and n > 0:
            out.append(Result(ts, "fail", "library nightly status=ok but errors=%d%s" % (n, why)))
        elif status == "ok" and complete:
            out.append(Result(ts, "ok", "library nightly status=ok, no errors recorded"))
        elif status == "ok":
            out.append(Result(ts, "unknown", "library nightly status=ok without dry= and secs= fields: the line is cut off or the log format changed"))
        else:
            out.append(Result(ts, "fail", "library nightly status=%s errors=%s%s" % (status, n if n is not None else "?", why)))
    return out


# ---------------------------------------------------------------- the world the watchers read

@dataclass
class Ctx:
    now: dt.datetime
    io: Any
    paths: dict


def make_paths(inputs_dir=DEFAULT_INPUTS, hub_dir=DEFAULT_HUB, nightly_log=None, library_log=None, archive_dir=None):
    return {
        "vzdump_mirror": os.path.join(inputs_dir, "overlord", "vzdump-tasks-index.txt"),
        "vault_sync_mirror": os.path.join(inputs_dir, "overlord", "vault-sync.status"),
        "greywolf_mirror": os.path.join(inputs_dir, "overlord", "greywolf-state.status"),
        "util_mirror": os.path.join(inputs_dir, "overlord", "utilization.json"),
        "cards_snapshot": os.path.join(inputs_dir, "router-desk-questions.json"),
        "nightly_log": nightly_log or DEFAULT_NIGHTLY_LOG,
        "library_log": library_log or DEFAULT_LIBRARY_LOG,
        "archive_dir": archive_dir or DEFAULT_ARCHIVE_DIR,
        "hub_dir": hub_dir,
    }


# what NODE must expose for each mirror: the source on overlord
MIRROR_SOURCE = {
    "vzdump_mirror": "/var/log/pve/tasks/index (its :vzdump:103: lines)",
    "vault_sync_mirror": "/var/log/vault-sync.status",
    "greywolf_mirror": "/var/log/greywolf-state.status",
    "util_mirror": "/var/lib/cluster/utilization.json",
}


def _mirror(ctx, key):
    """(Read, None) for a usable copy of a file on overlord, else (None, UNKNOWN evidence)."""
    path = ctx.paths[key]
    rd = ctx.io.read(path)
    if rd.text is None:
        if rd.error == "missing":
            return None, "no copy at %s; NODE must expose overlord %s at that path" % (path, MIRROR_SOURCE[key])
        return None, "the copy at %s is %s" % (path, rd.error)
    if rd.mtime is None:
        return None, "the copy at %s has no readable modification time, so when it was taken is unknown" % path
    if rd.mtime > ctx.now + FUTURE_SLACK:
        return None, "the copy at %s is dated %s, in the future: the clock is wrong" % (path, fmt_pt(rd.mtime))
    return rd, None


def _local(ctx, key):
    path = ctx.paths[key]
    rd = ctx.io.read(path)
    if rd.text is None:
        return None, ("no file at %s" % path) if rd.error == "missing" else ("the file at %s is %s" % (path, rd.error))
    return rd, None


def _scheduled(ctx, wid, rd, bad, parser, name):
    if bad:
        return Finding(wid, UNKNOWN, bad)
    slot, wa = SLOTS[wid]
    observed = rd.mtime if rd.mtime is not None else None
    status, ev, at = judge_scheduled(parser(rd.text), ctx.now, slot, wa, observed_at=observed, name=name)
    return Finding(wid, status, ev, at)


def w_vzdump(ctx):
    rd, bad = _mirror(ctx, "vzdump_mirror")
    return _scheduled(ctx, "vzdump-vm103", rd, bad, lambda t: parse_vzdump(t, 103), "vzdump VM 103")


def w_vault_sync(ctx):
    rd, bad = _mirror(ctx, "vault_sync_mirror")
    return _scheduled(ctx, "vault-sync", rd, bad, parse_vault_sync, "vault-sync")


def w_greywolf(ctx):
    rd, bad = _mirror(ctx, "greywolf_mirror")
    return _scheduled(ctx, "greywolf-state-pull", rd, bad, parse_greywolf, "greywolf-state pull")


def w_nightly_full_run(ctx):
    rd, bad = _local(ctx, "nightly_log")
    if bad:
        return Finding("nightly-full-run", UNKNOWN, bad + " (a night with no line means the task did not start)")
    f = _scheduled(ctx, "nightly-full-run", Read(rd.text, ctx.now, None), None, parse_nightly_full, "nightly full run")
    return f


def w_library(ctx):
    rd, bad = _local(ctx, "library_log")
    if bad:
        return Finding("library-nightly", UNKNOWN, bad)
    return _scheduled(ctx, "library-nightly", Read(rd.text, ctx.now, None), None, parse_library, "library nightly")


def w_vault_private(ctx):
    wid = "vault-private-sync"
    try:
        st = ctx.io.vault_private(ctx.now)
    except Exception as e:                       # the reader is someone else's code: its crash is not a pass
        return Finding(wid, UNKNOWN, "the VAULT private sync reader failed: %s" % e.__class__.__name__)
    if not isinstance(st, dict) or st.get("state") not in ("ok", "failed", "unknown"):
        return Finding(wid, UNKNOWN, "the VAULT private sync reader gave no recognised state")
    at = parse_ts(st.get("last_start") or "")
    return Finding(wid, {"ok": OK, "failed": FAIL}.get(st["state"], UNKNOWN),
                   "VAULT private sync: %s%s" % (st.get("reason", st["state"]), " [last run started %s]" % fmt_pt(at) if at else ""), at)


def w_utilization(ctx):
    wid = "utilization-feed"
    rd, bad = _mirror(ctx, "util_mirror")
    if bad:
        return Finding(wid, UNKNOWN, bad)
    age_copy = ctx.now - rd.mtime
    if age_copy > UTIL_MIRROR_MAX_AGE:
        return Finding(wid, UNKNOWN, "the copy was taken %s, %.1f h ago: it cannot tell a stopped feed from a stopped copy"
                       % (fmt_pt(rd.mtime), age_copy.total_seconds() / 3600), rd.mtime)
    try:
        data = json.loads(rd.text)
    except ValueError:
        return Finding(wid, UNKNOWN, "the copy is not valid JSON")
    if not isinstance(data, dict):
        return Finding(wid, UNKNOWN, "the copy is not a JSON object")
    stamp = None
    for field in FEED_TIME_FIELDS:
        stamp = _feed_time(data.get(field))
        if stamp:
            break
    if not stamp:
        return Finding(wid, UNKNOWN, "no timestamp field in the feed (looked for %s); NODE must name it" % ", ".join(FEED_TIME_FIELDS))
    if stamp > rd.mtime + FUTURE_SLACK:
        return Finding(wid, UNKNOWN, "the feed's own time %s is after the copy was taken: a clock is wrong" % fmt_pt(stamp), stamp)
    age = rd.mtime - stamp
    mins = age.total_seconds() / 60
    if age > UTIL_FEED_MAX_AGE:
        return Finding(wid, FAIL, "the feed was %.1f h old when copied %s (it should refresh every 5 min)" % (mins / 60, fmt_pt(rd.mtime)), stamp)
    return Finding(wid, OK, "the feed was %.0f min old when copied %s" % (mins, fmt_pt(rd.mtime)), stamp)


def _feed_time(v):
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        v = v / 1000.0 if v > 1e11 else v
        return dt.datetime.fromtimestamp(v, dt.timezone.utc) if 1e9 < v < 4e9 else None
    if isinstance(v, str):
        try:
            t = dt.datetime.fromisoformat(v.strip().replace("Z", "+00:00"))
        except ValueError:
            return None
        return t.astimezone(dt.timezone.utc) if t.tzinfo else None     # a time with no zone is a guess: refuse it
    return None


def _card_list(data):
    """(cards as [(id, dict)], exported_at) from the shapes a snapshot may take, or (None, None)."""
    exported = None
    if isinstance(data, dict):
        exported = parse_ts(data.get("exported_at") or "") if isinstance(data.get("exported_at"), str) else None
        for key in ("cards", "questions"):
            if isinstance(data.get(key), (dict, list)):
                data = data[key]
                break
    if isinstance(data, dict):
        if all(isinstance(v, dict) for v in data.values()):
            return list(data.items()), exported
        return None, None
    if isinstance(data, list) and all(isinstance(v, dict) for v in data):
        return [(str(v.get("id") or v.get("doc_id") or "?"), v) for v in data], exported
    return None, None


def w_cards(ctx):
    wid = "cards-unrouted"
    path = ctx.paths["cards_snapshot"]
    rd = ctx.io.read(path)
    if rd.text is None:
        why = ("no snapshot at %s; a desk with ArtifactData must write the Router desk `questions` collection there" % path
               if rd.error == "missing" else "the snapshot at %s is %s" % (path, rd.error))
        return Finding(wid, UNKNOWN, why)
    try:
        cards, exported = _card_list(json.loads(rd.text))
    except ValueError:
        cards, exported = None, None
    if cards is None:
        return Finding(wid, UNKNOWN, "the snapshot at %s is not a set of cards" % path)
    taken = exported or rd.mtime
    if taken is None:
        return Finding(wid, UNKNOWN, "the snapshot has no time (no exported_at and no modification time)")
    if taken > ctx.now + FUTURE_SLACK or ctx.now - taken > CARDS_SNAPSHOT_MAX_AGE:
        return Finding(wid, UNKNOWN, "the snapshot was taken %s: not within the last %.0f h" % (fmt_pt(taken), CARDS_SNAPSHOT_MAX_AGE.total_seconds() / 3600), taken)
    pending, no_time = [], []
    for cid, c in cards:
        if c.get("status") == "withdrawn":
            continue
        ans = c.get("answer")
        if ans is None or (c.get("kind") == "step" and ans == "not_yet"):
            continue
        routed = c.get("routed")
        if isinstance(routed, dict) and routed.get("at"):
            continue
        stamps = [parse_ts(c.get(k) or "") for k in ("answered_at", "note_at") if isinstance(c.get(k), str)]
        stamps = [s for s in stamps if s]
        (pending if stamps else no_time).append((cid, ctx.now - max(stamps) if stamps else None))
    stuck = sorted((p for p in pending if p[1] > CARD_ROUTE_GRACE), key=lambda p: -p[1].total_seconds())
    n = len(pending) + len(no_time)
    if stuck:
        cid, age = stuck[0]
        return Finding(wid, FAIL, "%d answered and not routed; %d older than %.0f h, oldest %s (%.1f h)" % (
            n, len(stuck), CARD_ROUTE_GRACE.total_seconds() / 3600, cid, age.total_seconds() / 3600), taken)
    if no_time:
        return Finding(wid, UNKNOWN, "%d answered and not routed, %d with no time so it cannot be told whether they are stuck (%s)" % (
            n, len(no_time), no_time[0][0]), taken)
    return Finding(wid, OK, "%d answered and not routed, none older than %.0f h (snapshot %s)" % (
        n, CARD_ROUTE_GRACE.total_seconds() / 3600, fmt_pt(taken)), taken)


_NOTES_NAME = re.compile(r"^NOTES-(\d{4}-\d{2}-\d{2})\.md$")
_NOTES_RESULT = re.compile(r"Result:\s*(\d+)\s+PASS,\s*(\d+)\s+CHECK FIRST,\s*(\d+)\s+KEEP,\s*(\d+)\s+LIVE.*?of\s+(\d+)\s+unarchived", re.S)


def w_done_desks(ctx):
    wid = "done-desks-unarchived"
    d = ctx.paths["archive_dir"]
    names = ctx.io.listdir(d)
    if names is None:
        return Finding(wid, UNKNOWN, "no folder at %s (the nightly desk-archival review writes NOTES-<date>.md there)" % d)
    names = sorted((n for n in names if _NOTES_NAME.match(n)), reverse=True)[:4]
    if not names:
        return Finding(wid, UNKNOWN, "no NOTES-<date>.md in %s" % d)
    rows = []
    for n in names:
        rd = ctx.io.read(os.path.join(d, n))
        if rd.text is None or rd.mtime is None:
            continue
        m = _NOTES_RESULT.search(rd.text)
        if not m:
            rows.append(Result(rd.mtime, "unknown", "%s has no recognisable Result line: the review's format changed" % n))
            continue
        p, c, k, live, tot = (int(x) for x in m.groups())
        detail = "%d pass the gate, %d check first, %d keep, %d live of %d unarchived" % (p, c, k, live, tot)
        # PASS means the review proved the desk is done and nothing is owed: those are the FAIL. CHECK FIRST means
        # the review could not prove either way, so "none are done and unarchived" is not something it can say:
        # ok only when both are zero (first real read, 2026-11-23: 0 PASS beside 132 CHECK FIRST must not read OK).
        if p:
            rows.append(Result(rd.mtime, "fail", detail + " and are not archived"))
        elif c:
            rows.append(Result(rd.mtime, "unknown", detail + ": the review cannot say none of the %d check-first desks is done" % c))
        else:
            rows.append(Result(rd.mtime, "ok", detail))
    slot, wa = SLOTS[wid]
    status, ev, at = judge_scheduled(rows, ctx.now, slot, wa, observed_at=ctx.now, name="desk-archival review")
    return Finding(wid, status, ev, at)


def _gh_json(ctx, args):
    rc, out = ctx.io.gh(args)
    if rc != 0:
        return None, "gh %s failed: %s" % (" ".join(args[:2]), _clean(out, 100))
    try:
        return json.loads(out), None
    except ValueError:
        return None, "gh %s gave output that is not JSON" % " ".join(args[:2])


_ANSI = re.compile(r"\x1b\[[0-9;?]*[ -/]*[@-~]")


def w_hub_tests(ctx):
    wid = "hub-tests-main"
    rows, bad = _gh_json(ctx, ["run", "list", "--workflow", "test.yml", "--branch", "main", "--limit", "20",
                               "--json", "databaseId,conclusion,status,headSha,event,createdAt,updatedAt"])
    if bad:
        return Finding(wid, UNKNOWN, bad)
    if not isinstance(rows, list) or not rows:
        return Finding(wid, UNKNOWN, "gh lists no test.yml runs on main")
    rows = sorted((r for r in rows if isinstance(r, dict)), key=lambda r: r.get("createdAt") or "", reverse=True)
    verdict = [r for r in rows if r.get("status") == "completed" and r.get("conclusion") in ("success", "failure", "timed_out", "startup_failure")]
    if not verdict:
        return Finding(wid, UNKNOWN, "no completed run with a verdict among the last %d on main (cancelled, skipped or in progress say nothing)" % len(rows))
    r = verdict[0]
    sha, rid = str(r.get("headSha") or "?")[:7], r.get("databaseId")
    done_at = parse_ts(r.get("updatedAt") or "")
    newer = [x for x in rows if x.get("status") != "completed" and (x.get("createdAt") or "") >= (r.get("createdAt") or "")]
    note = "; a newer run is in progress" if newer else ""
    if r.get("conclusion") != "success":
        return Finding(wid, FAIL, "run %s concluded %s on %s%s" % (rid, r.get("conclusion"), sha, note), done_at)
    if not done_at:
        return Finding(wid, UNKNOWN, "run %s has no readable finish time" % rid)
    age = ctx.now - done_at
    if age > HUB_TESTS_MAX_AGE or age < -FUTURE_SLACK:
        return Finding(wid, UNKNOWN, "the newest success (run %s on %s) finished %s, not within %.0f h%s" % (
            rid, sha, fmt_pt(done_at), HUB_TESTS_MAX_AGE.total_seconds() / 3600, note), done_at)
    jobs, bad = _gh_json(ctx, ["run", "view", str(rid), "--json", "jobs"])
    if bad:
        return Finding(wid, UNKNOWN, "run %s succeeded on %s but the job list is unreadable: %s" % (rid, sha, bad), done_at)
    job = next((j for j in (jobs or {}).get("jobs", []) if j.get("name") == "pytest"), None)
    if not job or job.get("conclusion") != "success":
        return Finding(wid, UNKNOWN, "run %s succeeded on %s but its job `pytest` is not shown as success" % (rid, sha), done_at)
    # gh refuses to print a log that holds terminal escape sequences unless told to (first real read, 2026-11-23:
    # without the flag the guard line was unreadable on every run, so this line could never say OK). The log is
    # only matched against a pattern here, never shown, and the colour codes are stripped first.
    rc, log = ctx.io.gh(["api", "--allow-escape-sequences", "repos/{owner}/{repo}/actions/jobs/%s/logs" % job.get("databaseId")])
    m = re.search(r"OK: ran (\d+) == collected (\d+)", _ANSI.sub("", log)) if rc == 0 else None
    if not m or m.group(1) != m.group(2):
        return Finding(wid, UNKNOWN, "run %s succeeded on %s but the count guard's `OK: ran N == collected N` line is not readable in the job log" % (rid, sha), done_at)
    return Finding(wid, OK, "run %s success on %s; count guard OK: ran %s == collected %s; finished %s%s" % (
        rid, sha, m.group(1), m.group(2), fmt_pt(done_at), note), done_at)


def w_hub_prs(ctx):
    wid = "hub-open-prs"
    rows, bad = _gh_json(ctx, ["pr", "list", "--state", "open", "--limit", str(PR_LIST_LIMIT),
                               "--json", "number,isDraft,createdAt,updatedAt"])
    if bad:
        return Finding(wid, UNKNOWN, bad)
    if not isinstance(rows, list):
        return Finding(wid, UNKNOWN, "gh pr list gave no list")
    if len(rows) >= PR_LIST_LIMIT:
        return Finding(wid, UNKNOWN, "the list hit its limit of %d, so the count is a lower bound and not a count" % PR_LIST_LIMIT)
    drafts = sum(1 for r in rows if r.get("isDraft"))
    stale = []
    for r in rows:
        made = parse_ts(r.get("createdAt") or "")
        if not r.get("isDraft") and made and ctx.now - made > OPEN_PR_STALE:
            stale.append((ctx.now - made, r.get("number")))
    head = "%d open (%d draft)" % (len(rows), drafts)
    if stale:
        age, num = max(stale)
        return Finding(wid, FAIL, "%s; %d non-draft open over %.0f h, oldest #%s (%.0f h)" % (
            head, len(stale), OPEN_PR_STALE.total_seconds() / 3600, num, age.total_seconds() / 3600))
    return Finding(wid, OK, "%s; no non-draft open over %.0f h" % (head, OPEN_PR_STALE.total_seconds() / 3600))


def _cert(wid, host):
    def watcher(ctx):
        if not ctx.io.live_tls():
            return Finding(wid, UNKNOWN, "the live TLS read is off for %s (one handshake, no request); run with --live-tls once the owner approves it" % host)
        try:
            info = ctx.io.tls(host)
        except ssl.SSLCertVerificationError as e:
            return Finding(wid, FAIL, "%s certificate does not verify: %s" % (host, getattr(e, "verify_message", None) or e))
        except Exception as e:
            return Finding(wid, UNKNOWN, "the handshake to %s failed: %s" % (host, e.__class__.__name__))
        na = (info or {}).get("not_after")
        if not isinstance(na, dt.datetime):
            return Finding(wid, UNKNOWN, "the handshake to %s gave no expiry" % host)
        days = (na - ctx.now).total_seconds() / 86400
        if days < 0:
            return Finding(wid, FAIL, "%s certificate expired %s" % (host, fmt_pt(na)), na)
        if days < CERT_FAIL_DAYS:
            return Finding(wid, FAIL, "%s: %.1f days left (expires %s); under %.0f means renewal has not run" % (host, days, fmt_pt(na), CERT_FAIL_DAYS), na)
        return Finding(wid, OK, "%s: %.1f days left (expires %s)" % (host, days, fmt_pt(na)), na)
    return watcher


WATCHERS = [
    ("vzdump-vm103", "vzdump VM 103 (Proxmox job vault-nightly, 02:15 PT)", w_vzdump),
    ("vault-sync", "vault-sync on overlord (02:45 PT)", w_vault_sync),
    ("greywolf-state-pull", "greywolf-state pull (04:10 PT)", w_greywolf),
    ("nightly-full-run", "WATCH nightly full run (04:30 PT)", w_nightly_full_run),
    ("library-nightly", "Document Library nightly (02:30 PT)", w_library),
    ("vault-private-sync", "VAULT private sync (04:30 PT)", w_vault_private),
    ("hub-tests-main", "last hub tests run on main, with its count", w_hub_tests),
    ("utilization-feed", "utilization feed age", w_utilization),
    (CERT_HOSTS[0][0], "days left on the leadfuel.cloud certificate", _cert(*CERT_HOSTS[0])),
    (CERT_HOSTS[1][0], "days left on the www.leadfuel.cloud certificate", _cert(*CERT_HOSTS[1])),
    ("cards-unrouted", "cards answered and not routed", w_cards),
    ("hub-open-prs", "open hub PRs", w_hub_prs),
    ("done-desks-unarchived", "DONE desks not archived", w_done_desks),
]


# ---------------------------------------------------------------- controls, report, files

def run_controls(now):
    """Built-in samples with known answers, judged by the same code as the real sources."""
    slot, wa = (2, 15), 90
    s = latest_slot_start(now, slot)
    cases = [
        ("ok in the slot", judge_scheduled([Result(s + dt.timedelta(minutes=3), "ok", "d")], now, slot, wa, observed_at=now)[0], OK),
        ("fail in the slot", judge_scheduled([Result(s + dt.timedelta(minutes=3), "fail", "d")], now, slot, wa, observed_at=now)[0], FAIL),
        ("no lines", judge_scheduled([], now, slot, wa, observed_at=now)[0], UNKNOWN),
        ("stale ok", judge_scheduled([Result(s - dt.timedelta(hours=72), "ok", "d")], now, slot, wa, observed_at=now)[0], UNKNOWN),
        ("manual ok alone", judge_scheduled([Result(s + dt.timedelta(hours=5), "ok", "d")], s + dt.timedelta(hours=6), slot, wa,
                                            observed_at=s + dt.timedelta(hours=6))[0], UNKNOWN),
        ("vault-sync ok line", [r.state for r in parse_vault_sync("20261123T104728Z OK files=1 drift710=0 drift620=0")], ["ok"]),
        ("vault-sync no drift fields", [r.state for r in parse_vault_sync("20261123T104728Z OK files=1")], ["unknown"]),
        ("vault-sync unknown line", [r.state for r in parse_vault_sync("20261121T104504Z UNKNOWN WHY: 710 unreachable")], ["unknown"]),
        ("vzdump ok and error", [r.state for r in parse_vzdump(
            "UPID:n:0001:0002:6B016F2A:vzdump:103:root@pam: 6B016F2B OK\nUPID:n:0001:0002:6B016F2C:vzdump:103:root@pam: 6B016F2D storage is not online", 103)],
         ["ok", "fail"]),
        ("greywolf skipped", [r.state for r in parse_greywolf("20261120T121011Z SKIPPED GREYWOLF unreachable")], ["fail"]),
        ("nightly pass and unknown", [r.state for r in parse_nightly_full(
            "2026-11-22T14:00:00Z PASS main=a collected=9\n2026-11-22T15:00:00Z UNKNOWN main=a reason=\"x\"")], ["ok", "unknown"]),
        ("library errors and dry", [r.state for r in parse_library(
            "2026-11-23T10:30:01Z status=errors dry=False errors=1\n2026-11-23T10:31:01Z status=ok dry=True errors=0")], ["fail"]),
        ("library real success line", [r.state for r in parse_library(
            "2026-11-23T10:30:01Z status=ok dry=False secs=61 files_written=3\n2026-11-23T10:31:01Z status=ok")], ["ok", "unknown"]),
    ]
    bad = [name for name, got, want in cases if got != want]
    return not bad, bad


def build_report(ctx):
    controls_ok, bad = run_controls(ctx.now)
    lines = []
    for wid, label, fn in WATCHERS:
        if not controls_ok:
            f = Finding(wid, UNKNOWN, "reader controls failed (%s): this reader cannot be trusted today" % ", ".join(bad))
        else:
            try:
                f = fn(ctx)
            except Exception as e:                                  # one broken watcher must not blank the file
                f = Finding(wid, UNKNOWN, "the reader crashed: %s" % e.__class__.__name__)
        lines.append({"id": wid, "label": label, "status": f.status, "evidence": f.evidence,
                      "subject_at": iso(f.subject_at) if f.subject_at else None})
    summary = {s: sum(1 for l in lines if l["status"] == s) for s in STATUSES}
    local, _ = pacific(ctx.now)
    return {"schema": SCHEMA, "generated_at": iso(ctx.now), "read_pacific": fmt_pt(ctx.now),
            "pacific_date": local.strftime("%Y-%m-%d"), "controls_ok": controls_ok, "controls_failed": bad,
            "early_read": (local.hour, local.minute) < EARLY_READ, "summary": summary, "lines": lines}


def render_text(rep):
    s = rep["summary"]
    head = "# MORNING PROOF %s | read %s (%s) | OK %d FAIL %d UNKNOWN %d" % (
        rep["pacific_date"], rep["read_pacific"], rep["generated_at"], s[OK], s[FAIL], s[UNKNOWN])
    if rep["early_read"]:
        head += " | EARLY: read before %02d:%02d PT, so the 04:10 pull and the 04:30 full run may still be going" % EARLY_READ
    out = [head,
           "# one line per watcher: id | OK, FAIL or UNKNOWN | evidence. OK only where the source was seen; UNKNOWN names what to expose.",
           "# read-only; times in Pacific; the file, not the exit code, is the verdict."]
    out += ["%s | %s | %s" % (l["id"], l["status"], l["evidence"]) for l in rep["lines"]]
    return "\n".join(out) + "\n"


def write_report(rep, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.join(out_dir, "proof-%s" % rep["pacific_date"])
    paths = (base + ".txt", base + ".json")
    for path, body in ((paths[0], render_text(rep)), (paths[1], json.dumps(rep, indent=1) + "\n")):
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(body)
        os.replace(tmp, path)
    return paths


def exit_code(summary):
    return 1 if summary.get(FAIL) else 3 if summary.get(UNKNOWN) else 0


# ---------------------------------------------------------------- the real world

_GH_API_WRITES = {"-X", "--method", "-f", "-F", "--field", "--raw-field", "--input"}


def assert_read_only_gh(args):
    """gh is allowed three read shapes and nothing else. A verb that writes raises before any process starts."""
    if not args:
        raise ValueError("no gh arguments")
    if args[0] == "api":
        if any(a in _GH_API_WRITES or a.startswith("--method=") for a in args[1:]):
            raise ValueError("gh api with a write flag is refused")
        return
    if args[0] == "run" and len(args) > 1 and args[1] in ("list", "view"):
        return
    if args[0] == "pr" and len(args) > 1 and args[1] == "list":
        return
    raise ValueError("gh %s is not a read this watcher makes" % " ".join(args[:2]))


def _decode(raw):
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", "replace")
    return raw.decode("utf-8-sig", "replace")


def _load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class RealIO:
    TAIL_BYTES = 8 * 1024 * 1024

    def __init__(self, hub_dir=DEFAULT_HUB, vault_log=None, offline=False, live_tls=False):
        self.hub_dir, self.vault_log, self.offline, self._live = hub_dir, vault_log, offline, live_tls

    def read(self, path):
        try:
            st = os.stat(path)
            with open(path, "rb") as f:
                if st.st_size > self.TAIL_BYTES:
                    f.seek(st.st_size - self.TAIL_BYTES)
                raw = f.read()
            return Read(_decode(raw), dt.datetime.fromtimestamp(st.st_mtime, dt.timezone.utc), None)
        except (FileNotFoundError, NotADirectoryError):
            return Read(None, None, "missing")
        except OSError as e:
            return Read(None, None, "unreadable: %s" % e.__class__.__name__)

    def listdir(self, path):
        try:
            return os.listdir(path)
        except OSError:
            return None

    def gh(self, args):
        assert_read_only_gh(args)
        if self.offline:
            return 127, "offline: gh was not run"
        try:
            p = subprocess.run(["gh"] + list(args), cwd=self.hub_dir, capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=180, env=dict(os.environ, GH_PROMPT_DISABLED="1", NO_COLOR="1"))
            return p.returncode, (p.stdout if p.returncode == 0 else p.stderr)
        except Exception as e:
            return 127, "gh could not run: %s" % e.__class__.__name__

    def live_tls(self):
        return bool(self._live) and not self.offline

    def tls(self, host):
        """One verifying handshake, no request sent. Raises on any failure; ssl.SSLCertVerificationError means FAIL."""
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as s:
                cert = s.getpeercert()
        return {"not_after": dt.datetime.fromtimestamp(ssl.cert_time_to_seconds(cert["notAfter"]), dt.timezone.utc)}

    def vault_private(self, now):
        return _load_sibling("vault_sync_status").read_status(self.vault_log, now)


def _parse_now(s):
    t = parse_ts(s)
    if not t:
        raise SystemExit("--now must look like 2026-11-23T12:50:00Z")
    return t


def _cmd_run(a):
    now = _parse_now(a.now) if a.now else dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    paths = make_paths(a.inputs_dir, a.hub, a.nightly_log, a.library_log, a.archive_dir)
    io = RealIO(hub_dir=a.hub, vault_log=a.vault_log, offline=a.offline, live_tls=a.live_tls)
    rep = build_report(Ctx(now=now, io=io, paths=paths))
    sys.stdout.write(render_text(rep))
    if not a.no_write:
        txt, js = write_report(rep, a.out_dir)
        print("wrote %s and %s" % (txt, js))
    return exit_code(rep["summary"])


def _cmd_selftest(_a):
    now = dt.datetime.now(dt.timezone.utc).replace(microsecond=0)
    ok, bad = run_controls(now)
    print("controls ok" if ok else "controls FAILED: %s" % ", ".join(bad))
    return 0 if ok else 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="read every watcher and write the dated proof file")
    r.add_argument("--now", help="UTC time to read as, 2026-11-23T12:50:00Z (default: now)")
    r.add_argument("--out-dir", default=DEFAULT_OUT_DIR)
    r.add_argument("--inputs-dir", default=DEFAULT_INPUTS, help="where the copies from other machines are exposed")
    r.add_argument("--hub", default=DEFAULT_HUB, help="the hub checkout gh runs in (it names the repo)")
    r.add_argument("--nightly-log", default=None)
    r.add_argument("--library-log", default=None)
    r.add_argument("--archive-dir", default=None)
    r.add_argument("--vault-log", default=None)
    r.add_argument("--offline", action="store_true", help="run no process and open no socket; gh and TLS lines read UNKNOWN")
    r.add_argument("--live-tls", action="store_true", help="make one TLS handshake per certificate host (the owner's call)")
    r.add_argument("--no-write", action="store_true", help="print the report and write no file")
    r.set_defaults(fn=_cmd_run)
    s = sub.add_parser("selftest", help="run the built-in controls and print the answer")
    s.set_defaults(fn=_cmd_selftest)
    a = p.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
