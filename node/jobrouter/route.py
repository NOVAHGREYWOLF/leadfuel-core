#!/usr/bin/env python3
"""NODE: the cluster job router. `route.py pick <class>` says which machine a job goes on.

Why (K17 scope, fold-c-jobrouter-build; design: DESIGN-job-router-and-cpu-move-2026-11-17, steps 2-3).
About 90 hardware threads sit idle and nothing places work on them. This is the router: a host
registry (hosts.json), job classes (classes.json), placement rule v0, a small queue, and a log.
Owner answers on the Router desk: q9590 A, the first real class is the standby refresh catch-up on
overlord; q9591, pve-od and pve-r610 are not in the cluster (closed by design, may be managed later);
q9588 B, adopt Ray after a pilot. This file is the Ray-agnostic part: the PLACEMENT POLICY (who may
take a job, and "unknown is never picked") and a thin queue. Execution goes through one function
(the runner), so a Ray pilot, if it happens, replaces only that. Nothing here downloads or installs.

The load feed is /var/lib/cluster/utilization.json (schema utilization-1), written every 5 minutes
by /root/util-report.sh on overlord. The router never trusts a state it cannot establish:

  * the facts of a host must be at most 360 s old NOW (the age is worked out from the feed's own
    timestamps against this machine's clock; where the feed gives two ways to work it out the OLDER
    one wins). A stale copy of the file, or a collector that died, makes every host `unknown`.
    The 360 s limit can be lowered by hosts.json or by the feed, never raised: widening what the
    router trusts is a code change. (The feed is written every 5 minutes and some hosts' facts are
    up to 4 minutes old when it is written, so a strict 360 s will defer a job part of the time.
    That is the safe direction and the next tick retries; measure before loosening it.)
  * a host the feed does not list, lists as anything but `up`, or lists with a reading that is not
    a number in range, is `unknown`. `unknown` is never picked.
  * a feed that is missing, unreadable, empty, not JSON or the wrong schema is an ERROR (exit 2)
    that names the reason. There is no default host to fall back to.

Placement rule v0, in order:
  1. the class names which hosts may take it (`eligible_hosts`); no list means no host.
  2. host must be in the cluster, accept router jobs, be `up` on fresh facts, be always-on if the
     class asks for it, have the GPU the class asks for, and have a way to run the job here (a
     `local` host only when the router runs on it; an `ssh` host only when its entry says enabled).
  3. thermal rule: for a `cpu` class, a thermal-limited host is passed over whenever ANY other host
     is eligible and up, even if that host is full. A job waits rather than heat a laptop.
  4. capacity: free threads = threads x (ceiling - load) / 100, load = the busier of the 15-minute
     mean and the reading now; a memory-bound host, or one without the RAM the class needs, is full.
  5. the host with the most free threads wins; ties go to an always-on host, then registry order.
`class.requires_up` lists hosts that must be `up` for the job to make sense at all (a source the job
pulls from); if one is not up the job is deferred, not placed.

Exit codes: 0 placed / ok; 1 a job failed, or `check` found problems; 2 an error that stopped the
router (feed, registry, classes, state dir, log); 3 no host can take the job right now (it stays
queued; an `unknown` host is a reason to wait, never a reason to guess); 4 another dispatcher holds
the lock.

Queue (a directory, default /var/lib/cluster/jobrouter): queue/pending, queue/running, queue/done,
placements.jsonl (one JSON object per line: submitted, deferred, placed, finished; anyone may read
it), dispatch.lock. A job is claimed by renaming its file; the `placed` line is written BEFORE the
job starts, and if that line cannot be written the job does not start. A job found in `running`
with no router alive is shown by `status` as overdue and is never re-run by itself (it might have
half-run). `dispatch` runs one job at a time.

Law 9: this program sends nothing anywhere. The only way it touches another machine is the `ssh`
runner, which runs only for a host whose registry entry says `"enabled": true` (every one ships
false: it needs a key, which is the owner's step). No power action, no spend, no cloud call.

Usage:
    route.py pick <class> [--json] [--policy-only]   which host would take it (nothing is queued)
    route.py check                                   registry, classes and feed agree (hosts both ways)
    route.py submit <class>                          put a job in the queue
    route.py dispatch [--max N]                      place and run queued jobs
    route.py run <class>                             submit, then dispatch
    route.py status [--json]                         queue, last placements, where jobs ran
    route.py log [--last N]                          print the placement log
  Options: --feed --hosts --classes --state-dir --here HOST --as-of 2026-11-23T10:00:00Z

Stdlib only, Python 3.8 or newer. Source and tests live in leadfuel-core (node/jobrouter/).
"""
import argparse
import contextlib
import datetime as dt
import json
import os
import re
import secrets
import shlex
import socket
import subprocess
import sys
import time
from collections import namedtuple

HERE_DIR = os.path.dirname(os.path.abspath(__file__))
FEED_SCHEMA = "utilization-1"
HOSTS_SCHEMA = "jobrouter-hosts-1"
CLASSES_SCHEMA = "jobclasses-1"
DEFAULT_FEED = "/var/lib/cluster/utilization.json"
DEFAULT_STATE = "/var/lib/cluster/jobrouter"
STALE_AFTER_S = 360            # design 4.3: facts older than 6 minutes are unknown
FUTURE_SLACK_S = 90            # a timestamp this far ahead of our clock cannot be trusted
TAIL_CHARS = 4000

UP, UNKNOWN, CLOSED = "up", "unknown", "closed"
EXIT_OK, EXIT_FAILED, EXIT_ERROR, EXIT_NO_HOST, EXIT_LOCKED = 0, 1, 2, 3, 4

NOT_FOR_CLASS = "not a host this class may use"
_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_JOB_ID_RE = re.compile(r"^[0-9]{8}T[0-9]{6}Z-[a-z0-9][a-z0-9-]{0,62}-[0-9a-f]{6}$")

HOST_KEYS = {"id", "hostnames", "threads", "ram_gb", "gpu", "always_on", "thermal_limited",
             "ceiling_cpu_pct", "in_cluster", "accepts_jobs", "in_feed", "exec", "note"}
HOST_REQUIRED = {"id", "always_on", "thermal_limited", "ceiling_cpu_pct", "in_cluster", "accepts_jobs"}
CLASS_KEYS = {"about", "kind", "eligible_hosts", "requires_always_on", "requires_up", "needs", "argv",
              "timeout_s", "dedupe"}
CLASS_REQUIRED = {"kind", "eligible_hosts", "argv", "timeout_s"}


class RouterError(Exception):
    """Something stopped the router and it says what. Never swallowed into a default."""


class FeedError(RouterError):
    pass


class RegistryError(RouterError):
    pass


class LockHeld(RouterError):
    pass


Host = namedtuple("Host", "id hostnames threads ram_gb gpu always_on thermal_limited ceiling_cpu_pct "
                          "in_cluster accepts_jobs in_feed exec_mode ssh_alias ssh_enabled note index")
JobClass = namedtuple("JobClass", "name about kind eligible_hosts requires_always_on requires_up "
                                  "need_threads need_ram_gb need_gpu argv timeout_s dedupe")
Feed = namedtuple("Feed", "path generated_ts age_s stale_after_s rows")
HostState = namedtuple("HostState", "state why load_pct ram_pct ram_total_gb age_s memory_bound")
Verdict = namedtuple("Verdict", "host verdict why")
# outcome: "placed" or "no-host". kind (no-host only): dependency | unknown | none-eligible | full.
Decision = namedtuple("Decision", "outcome kind host why free_threads considered")
RunResult = namedtuple("RunResult", "status exit_code duration_s stdout_tail stderr_tail started_at finished_at")


# ------------------------------------------------------------------------------------ small helpers

def utc_iso(epoch):
    return dt.datetime.fromtimestamp(epoch, dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_time(text):
    """ISO-8601 with an explicit Z or offset -> epoch seconds, or None. A time with no zone is not
    trusted: the router will not guess which clock wrote it."""
    if not isinstance(text, str) or not text:
        return None
    s = text.strip()
    if s.endswith("Z") or s.endswith("z"):
        s = s[:-1] + "+00:00"
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        return None
    if d.tzinfo is None:
        return None
    return d.timestamp()


def _num(v, lo=0.0, hi=100.0):
    """A real number in range, or None (bools, NaN, strings and out-of-range values are not readings)."""
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    if v != v or v < lo or v > hi:
        return None
    return float(v)


def _atomic_write(path, text):
    tmp = "%s.tmp-%d-%s" % (path, os.getpid(), secrets.token_hex(3))
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _read_json_file(path, what, error_cls):
    try:
        with open(path, "rb") as f:
            raw = f.read()
    except FileNotFoundError:
        raise error_cls("%s not found: %s" % (what, path))
    except OSError as e:
        raise error_cls("%s unreadable: %s (%s)" % (what, path, e.strerror or e))
    if not raw.strip():
        raise error_cls("%s is empty: %s" % (what, path))
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, ValueError) as e:
        raise error_cls("%s is not valid JSON: %s (%s)" % (what, path, e))


# ------------------------------------------------------------------------------- registry and classes

def _bool(d, key, where):
    v = d.get(key)
    if not isinstance(v, bool):
        raise RegistryError("%s: '%s' must be true or false (no default is assumed)" % (where, key))
    return v


def load_registry(path):
    doc = _read_json_file(path, "host registry", RegistryError)
    if not isinstance(doc, dict) or doc.get("schema") != HOSTS_SCHEMA:
        raise RegistryError("host registry %s: schema must be %r" % (path, HOSTS_SCHEMA))
    stale = doc.get("stale_after_s", STALE_AFTER_S)
    if _num(stale, 1, 86400) is None:
        raise RegistryError("host registry: stale_after_s must be a number of seconds")
    rows = doc.get("hosts")
    if not isinstance(rows, list) or not rows:
        raise RegistryError("host registry %s: 'hosts' must be a non-empty list" % path)
    hosts, seen = [], set()
    for i, row in enumerate(rows):
        if not isinstance(row, dict):
            raise RegistryError("host registry: entry %d is not an object" % i)
        hid = row.get("id")
        where = "host %r" % (hid,)
        if not isinstance(hid, str) or not hid:
            raise RegistryError("host registry: entry %d has no id" % i)
        if hid in seen:
            raise RegistryError("host registry: id %r appears twice" % hid)
        seen.add(hid)
        extra = set(row) - HOST_KEYS
        if extra:
            raise RegistryError("%s: unknown field(s) %s (a typo here would silently change a rule)"
                                % (where, ", ".join(sorted(extra))))
        missing = HOST_REQUIRED - set(row)
        if missing:
            raise RegistryError("%s: missing %s" % (where, ", ".join(sorted(missing))))
        in_cluster = _bool(row, "in_cluster", where)
        accepts = _bool(row, "accepts_jobs", where)
        always_on = _bool(row, "always_on", where)
        thermal = _bool(row, "thermal_limited", where)
        ceiling = _num(row.get("ceiling_cpu_pct"), 1, 100)
        if ceiling is None:
            raise RegistryError("%s: ceiling_cpu_pct must be a number from 1 to 100" % where)
        threads = row.get("threads")
        if threads is not None and (isinstance(threads, bool) or not isinstance(threads, int) or threads < 1):
            raise RegistryError("%s: threads must be a whole number of 1 or more, or null" % where)
        if in_cluster and accepts and threads is None:
            raise RegistryError("%s: accepts jobs but has no thread count" % where)
        ram = row.get("ram_gb")
        if ram is not None and _num(ram, 0, 100000) is None:
            raise RegistryError("%s: ram_gb must be a number or null" % where)
        gpu = row.get("gpu", [])
        if not isinstance(gpu, list) or not all(isinstance(g, str) for g in gpu):
            raise RegistryError("%s: gpu must be a list of strings" % where)
        names = row.get("hostnames", [hid])
        if not isinstance(names, list) or not all(isinstance(n, str) for n in names):
            raise RegistryError("%s: hostnames must be a list of strings" % where)
        in_feed = row.get("in_feed", True)
        if not isinstance(in_feed, bool):
            raise RegistryError("%s: in_feed must be true or false" % where)
        ex = row.get("exec", {"mode": "none"})
        if not isinstance(ex, dict) or ex.get("mode") not in ("local", "ssh", "none"):
            raise RegistryError("%s: exec.mode must be local, ssh or none" % where)
        alias, enabled = None, False
        if ex["mode"] == "ssh":
            alias = ex.get("alias")
            if not isinstance(alias, str) or not re.match(r"^[A-Za-z0-9_.-]+$", alias):
                raise RegistryError("%s: exec.alias must be an ssh config alias (letters, digits, . _ -)" % where)
            enabled = ex.get("enabled", False)
            if not isinstance(enabled, bool):
                raise RegistryError("%s: exec.enabled must be true or false" % where)
        hosts.append(Host(hid, tuple(n.lower() for n in names), threads, ram, tuple(gpu), always_on, thermal,
                          ceiling, in_cluster, accepts, in_feed, ex["mode"], alias, enabled,
                          str(row.get("note", "")), i))
    return hosts, float(stale)


def load_classes(path, hosts):
    doc = _read_json_file(path, "job classes", RegistryError)
    if not isinstance(doc, dict) or doc.get("schema") != CLASSES_SCHEMA:
        raise RegistryError("job classes %s: schema must be %r" % (path, CLASSES_SCHEMA))
    raw = doc.get("classes")
    if not isinstance(raw, dict) or not raw:
        raise RegistryError("job classes %s: 'classes' must be a non-empty object" % path)
    ids = {h.id for h in hosts}
    out = {}
    for name, c in raw.items():
        where = "class %r" % name
        if not _NAME_RE.match(name):
            raise RegistryError("%s: name must be lowercase letters, digits and dashes" % where)
        if not isinstance(c, dict):
            raise RegistryError("%s: not an object" % where)
        extra = set(c) - CLASS_KEYS
        if extra:
            raise RegistryError("%s: unknown field(s) %s" % (where, ", ".join(sorted(extra))))
        missing = CLASS_REQUIRED - set(c)
        if missing:
            raise RegistryError("%s: missing %s" % (where, ", ".join(sorted(missing))))
        if c["kind"] not in ("cpu", "gpu"):
            raise RegistryError("%s: kind must be cpu or gpu" % where)
        elig = c["eligible_hosts"]
        if not isinstance(elig, list) or not elig or not all(isinstance(x, str) for x in elig):
            raise RegistryError("%s: eligible_hosts must be a non-empty list (no list means no host)" % where)
        req_up = c.get("requires_up", [])
        if not isinstance(req_up, list) or not all(isinstance(x, str) for x in req_up):
            raise RegistryError("%s: requires_up must be a list of host ids" % where)
        for hid in list(elig) + list(req_up):
            if hid not in ids:
                raise RegistryError("%s: names host %r, which is not in the registry" % (where, hid))
        needs = c.get("needs", {})
        if not isinstance(needs, dict) or set(needs) - {"threads", "ram_gb", "gpu"}:
            raise RegistryError("%s: needs may hold threads, ram_gb, gpu only" % where)
        nt = needs.get("threads", 1)
        if isinstance(nt, bool) or not isinstance(nt, int) or nt < 1:
            raise RegistryError("%s: needs.threads must be a whole number of 1 or more" % where)
        nr = needs.get("ram_gb", 0)
        if _num(nr, 0, 100000) is None:
            raise RegistryError("%s: needs.ram_gb must be a number" % where)
        ng = needs.get("gpu", [])
        if not isinstance(ng, list) or not all(isinstance(g, str) for g in ng):
            raise RegistryError("%s: needs.gpu must be a list of strings" % where)
        argv = c["argv"]
        if not isinstance(argv, list) or not argv or not all(isinstance(a, str) and a for a in argv):
            raise RegistryError("%s: argv must be a non-empty list of strings (no shell is used)" % where)
        to = c["timeout_s"]
        if isinstance(to, bool) or not isinstance(to, int) or to < 1:
            raise RegistryError("%s: timeout_s must be a whole number of seconds" % where)
        dedupe = c.get("dedupe", True)
        rao = c.get("requires_always_on", False)
        if not isinstance(dedupe, bool) or not isinstance(rao, bool):
            raise RegistryError("%s: dedupe and requires_always_on must be true or false" % where)
        out[name] = JobClass(name, str(c.get("about", "")), c["kind"], tuple(elig), rao, tuple(req_up),
                             nt, float(nr), tuple(ng), tuple(argv), to, dedupe)
    return out


# ----------------------------------------------------------------------------------------- the feed

def read_feed(path, now):
    doc = _read_json_file(path, "utilization feed", FeedError)
    if not isinstance(doc, dict):
        raise FeedError("utilization feed %s is not a JSON object" % path)
    if doc.get("schema") != FEED_SCHEMA:
        raise FeedError("utilization feed %s has schema %r; this router reads %r"
                        % (path, doc.get("schema"), FEED_SCHEMA))
    rows = doc.get("hosts")
    if not isinstance(rows, list):
        raise FeedError("utilization feed %s has no 'hosts' list" % path)
    by_id = {}
    for r in rows:
        if not isinstance(r, dict) or not isinstance(r.get("id"), str):
            raise FeedError("utilization feed %s has a host row with no id" % path)
        if r["id"] in by_id:
            raise FeedError("utilization feed %s lists host %r twice" % (path, r["id"]))
        by_id[r["id"]] = r
    stamps = []
    if doc.get("generated_ts") is not None:
        g = _num(doc.get("generated_ts"), 0, 4e9)
        if g is None:
            raise FeedError("utilization feed %s: generated_ts is not a usable number" % path)
        stamps.append(g)
    if doc.get("generated") is not None:
        g = parse_time(doc.get("generated"))
        if g is None:
            raise FeedError("utilization feed %s: 'generated' is not a time with a Z or offset" % path)
        stamps.append(g)
    if not stamps:
        raise FeedError("utilization feed %s has no usable generation time" % path)
    gen = min(stamps)                         # two stamps that disagree: believe the older one
    limit = _num(doc.get("stale_after_s"), 1, 86400)
    limit = STALE_AFTER_S if limit is None else min(limit, STALE_AFTER_S)
    return Feed(path, gen, now - gen, limit, by_id)


def classify(host, feed, now, stale_after_s):
    """What can the router say about this host right now? up | unknown | closed, with the reason."""
    none = None
    if not host.in_cluster:
        return HostState(CLOSED, "not in the cluster (%s)" % (host.note or "closed by design"),
                         none, none, none, none, False)
    row = feed.rows.get(host.id)
    if row is None:
        return HostState(UNKNOWN, "not listed in the utilization feed", none, none, none, none, False)
    state = row.get("state")
    if state != "up":
        return HostState(UNKNOWN, "feed says state %r%s" % (state, _why(row)), none, none, none, none, False)
    limit = min(stale_after_s, feed.stale_after_s)
    # How old are this host's facts NOW? Every way the feed lets us work it out; the oldest wins. A
    # field that is there but unusable makes the host unknown: a half-broken row is not evidence.
    coll_raw, fa_raw = row.get("collected"), row.get("facts_age_s")
    collected, fa = parse_time(coll_raw), _num(fa_raw, 0, 1e9)
    if (coll_raw is not None and collected is None) or (fa_raw is not None and fa is None):
        return HostState(UNKNOWN, "feed gives an unusable collection time or facts age for this host",
                         none, none, none, none, False)
    if collected is None and fa is None:
        return HostState(UNKNOWN, "feed gives no collection time for this host, so its age is not known",
                         none, none, none, none, False)
    ages = [now - feed.generated_ts]           # the facts cannot be newer than the file that quotes them
    if collected is not None:
        ages.append(now - collected)
    if fa is not None:
        ages.append(fa + (now - feed.generated_ts))
    age = max(ages)
    if min(ages) < -FUTURE_SLACK_S:
        return HostState(UNKNOWN, "feed timestamps are %.0f s ahead of this clock; cannot trust them" % -min(ages),
                         none, none, none, none, False)
    if age > limit:
        return HostState(UNKNOWN, "facts are %.0f s old (limit %.0f s)%s"
                         % (age, limit, _file_age_hint(feed, limit)), none, none, none, age, False)
    raw = [row.get("cpu15_pct"), row.get("cpu_now_pct")]
    vals = [_num(v) for v in raw]
    readings = [v for v in vals if v is not None]
    if not readings or any(v is None and rv is not None for v, rv in zip(vals, raw)):
        return HostState(UNKNOWN, "no CPU reading that is a number from 0 to 100", none, none, none, age, False)
    load = max(readings)                        # the busier of the 15-minute mean and now
    ram = _num(row.get("ram_pct"))
    return HostState(UP, "facts %.0f s old" % age, load, ram, _num(row.get("ram_total_gb"), 0, 1e6), age,
                     bool(row.get("memory_bound")))


def _why(row):
    r = row.get("state_reason")
    return " (%s)" % r if isinstance(r, str) and r else ""


def _file_age_hint(feed, limit):
    if feed.age_s > limit:
        return "; the feed file itself is %.0f s old, so the collector may not be running" % feed.age_s
    return ""


# ------------------------------------------------------------------------------------------ placement

def pick(cls, hosts, feed, now, stale_after_s=STALE_AFTER_S, runnable=None):
    """Placement rule v0. Returns a Decision; never raises for 'no host' and never guesses.
    runnable(host) -> (ok, why) says whether a job can actually be started on that host from here."""
    states = {h.id: classify(h, feed, now, stale_after_s) for h in hosts}
    by_id = {h.id: h for h in hosts}
    considered = []

    for dep in cls.requires_up:
        st = states[dep]
        if st.state != UP:
            why = "class needs %s up, but it is %s: %s" % (dep, st.state, st.why)
            considered.append(Verdict(dep, "dependency", why))
            return Decision("no-host", "dependency", None, why, None, considered)

    eligible, saw_unknown = [], False
    for h in hosts:
        st = states[h.id]
        if h.id not in cls.eligible_hosts:
            considered.append(Verdict(h.id, "skip", NOT_FOR_CLASS))
        elif not h.in_cluster:
            considered.append(Verdict(h.id, "closed", st.why))
        elif not h.accepts_jobs:
            considered.append(Verdict(h.id, "skip", "host does not take router jobs"))
        elif st.state != UP:
            saw_unknown = True
            considered.append(Verdict(h.id, "unknown", st.why))
        elif cls.requires_always_on and not h.always_on:
            considered.append(Verdict(h.id, "skip", "class needs an always-on host"))
        elif set(cls.need_gpu) - set(h.gpu):
            considered.append(Verdict(h.id, "skip", "lacks GPU %s" % ", ".join(sorted(set(cls.need_gpu) - set(h.gpu)))))
        else:
            ok, why = (True, "") if runnable is None else runnable(h)
            if not ok:
                considered.append(Verdict(h.id, "skip", why))
            else:
                eligible.append(h)

    if not eligible:
        kind = "unknown" if saw_unknown else "none-eligible"
        why = ("no eligible host is up on fresh facts; at least one candidate is unknown (never picked)"
               if saw_unknown else "no host passes the class's rules")
        return Decision("no-host", kind, None, why, None, considered)

    if cls.kind == "cpu" and any(not h.thermal_limited for h in eligible):
        kept = []
        for h in eligible:
            if h.thermal_limited:
                considered.append(Verdict(h.id, "held", "thermal rule: another eligible host is up"))
            else:
                kept.append(h)
        eligible = kept

    roomy, free_by = [], {}
    for h in eligible:
        st = states[h.id]
        free = h.threads * max(0.0, h.ceiling_cpu_pct - st.load_pct) / 100.0
        ram_total = st.ram_total_gb if st.ram_total_gb else h.ram_gb
        if st.memory_bound:
            considered.append(Verdict(h.id, "full", "feed marks it memory-bound"))
        elif cls.need_ram_gb > 0 and (st.ram_pct is None or not ram_total):
            considered.append(Verdict(h.id, "unknown", "class needs %.1f GB RAM and the RAM reading is missing" % cls.need_ram_gb))
            saw_unknown = True
        elif cls.need_ram_gb > 0 and ram_total * (100.0 - st.ram_pct) / 100.0 < cls.need_ram_gb:
            considered.append(Verdict(h.id, "full", "%.1f GB RAM free, class needs %.1f"
                                      % (ram_total * (100.0 - st.ram_pct) / 100.0, cls.need_ram_gb)))
        elif free < cls.need_threads:
            considered.append(Verdict(h.id, "full", "%.1f threads free under its %.0f%% ceiling (load %.1f%%), class needs %d"
                                      % (free, h.ceiling_cpu_pct, st.load_pct, cls.need_threads)))
        else:
            roomy.append(h)
            free_by[h.id] = free
            considered.append(Verdict(h.id, "eligible", "%.1f threads free (load %.1f%%, ceiling %.0f%%)"
                                      % (free, st.load_pct, h.ceiling_cpu_pct)))
    if not roomy:
        kind = "unknown" if saw_unknown else "full"
        return Decision("no-host", kind, None, "every eligible host is %s" % ("unknown or full" if saw_unknown else "full"),
                        None, considered)

    best = sorted(roomy, key=lambda h: (-free_by[h.id], not h.always_on, h.index))[0]
    considered = [Verdict(v.host, "picked", v.why + "; most free threads") if v.host == best.id and v.verdict == "eligible" else v
                  for v in considered]
    return Decision("placed", None, by_id[best.id], "%.1f threads free on %s" % (free_by[best.id], best.id),
                    free_by[best.id], considered)


def make_runnable(here, hosts_by_id=None):
    """Can a job start on this host from the machine the router is on? (never opens a connection)"""
    def runnable(h):
        if h.exec_mode == "local":
            if here is None:
                return False, "router cannot tell which host it is running on (use --here)"
            if here != h.id:
                return False, "local execution only: the router runs on %s, not %s" % (here, h.id)
            return True, ""
        if h.exec_mode == "ssh":
            if not h.ssh_enabled:
                return False, "ssh execution not enabled for this host (needs a key: owner step)"
            return True, ""
        return False, "no execution route defined for this host"
    return runnable


def detect_here(hosts, explicit=None):
    name = (explicit or os.environ.get("JOBROUTER_HERE") or socket.gethostname() or "").strip()
    if not name:
        return None
    low = name.lower()
    for h in hosts:
        if h.id.lower() == low or low in h.hostnames:
            return h.id
    return None


# --------------------------------------------------------------------------------------------- runners

def run_local(argv, timeout_s):
    started = time.time()
    try:
        p = subprocess.run(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           timeout=timeout_s)
    except subprocess.TimeoutExpired as e:
        return _result("timeout", None, started, e.stdout, e.stderr)
    except OSError as e:
        return _result("error", None, started, b"", ("could not start: %s" % e).encode("utf-8"))
    return _result("ok" if p.returncode == 0 else "failed", p.returncode, started, p.stdout, p.stderr)


def ssh_argv(alias, argv):
    """The command that would run `argv` on the host `alias` (an ssh config alias). Built, never run, by tests."""
    return ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", alias, "--", " ".join(shlex.quote(a) for a in argv)]


def run_ssh(alias, argv, timeout_s):
    return run_local(ssh_argv(alias, argv), timeout_s)


def _result(status, code, started, out, err):
    def tail(b):
        text = (b or b"").decode("utf-8", errors="replace")
        return text[-TAIL_CHARS:]
    now = time.time()
    return RunResult(status, code, round(now - started, 3), tail(out), tail(err), utc_iso(started), utc_iso(now))


def default_runner(host, cls):
    if host.exec_mode == "local":
        return run_local(list(cls.argv), cls.timeout_s)
    if host.exec_mode == "ssh" and host.ssh_enabled:
        return run_ssh(host.ssh_alias, list(cls.argv), cls.timeout_s)
    raise RouterError("no way to run a job on %s from here" % host.id)


# ------------------------------------------------------------------------------------------ the queue

Ctx = namedtuple("Ctx", "hosts classes stale_after_s feed_path state_dir here runner clock")


def _dirs(state_dir):
    q = os.path.join(state_dir, "queue")
    return {"pending": os.path.join(q, "pending"), "running": os.path.join(q, "running"),
            "done": os.path.join(q, "done"), "log": os.path.join(state_dir, "placements.jsonl"),
            "lock": os.path.join(state_dir, "dispatch.lock")}


def ensure_state(state_dir):
    d = _dirs(state_dir)
    try:
        for k in ("pending", "running", "done"):
            os.makedirs(d[k], exist_ok=True)
    except OSError as e:
        raise RouterError("state directory not usable: %s (%s)" % (state_dir, e.strerror or e))
    return d


def log_event(ctx, event, **fields):
    """Append one line to placements.jsonl and flush it to disk. Raises RouterError if it cannot."""
    rec = {"v": 1, "at": utc_iso(ctx.clock()), "event": event}
    rec.update(fields)
    line = json.dumps(rec, sort_keys=True, ensure_ascii=False) + "\n"
    try:
        with open(_dirs(ctx.state_dir)["log"], "a", encoding="utf-8", newline="\n") as f:
            f.write(line)
            f.flush()
            os.fsync(f.fileno())
    except OSError as e:
        raise RouterError("cannot write the placement log (%s): no job is started without one" % (e.strerror or e))
    return rec


def _job_files(d, where):
    try:
        return sorted(n for n in os.listdir(d[where]) if n.endswith(".json"))
    except FileNotFoundError:
        return []


def _load_job(path):
    with open(path, "r", encoding="utf-8") as f:
        job = json.load(f)
    if not isinstance(job, dict) or not isinstance(job.get("id"), str) or not isinstance(job.get("class"), str):
        raise ValueError("not a job file")
    if not _JOB_ID_RE.match(job["id"]) or os.path.basename(path) != job["id"] + ".json":
        raise ValueError("job id does not match its file name")
    return job


def submit(ctx, class_name):
    cls = ctx.classes.get(class_name)
    if cls is None:
        raise RouterError("unknown job class %r (known: %s)" % (class_name, ", ".join(sorted(ctx.classes))))
    d = ensure_state(ctx.state_dir)
    if cls.dedupe:
        for where in ("pending", "running"):
            for n in _job_files(d, where):
                try:
                    other = _load_job(os.path.join(d[where], n))
                except (OSError, ValueError):
                    continue
                if other["class"] == class_name:
                    return None, "a job of class %s is already %s (%s)" % (class_name, where, other["id"])
    now = ctx.clock()
    job_id = "%s-%s-%s" % (dt.datetime.fromtimestamp(now, dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ"),
                           class_name, secrets.token_hex(3))
    job = {"schema": "job-1", "id": job_id, "class": class_name, "submitted_at": utc_iso(now)}
    _atomic_write(os.path.join(d["pending"], job_id + ".json"), json.dumps(job, indent=1, sort_keys=True) + "\n")
    log_event(ctx, "submitted", job=job_id, **{"class": class_name})
    return job_id, "queued"


@contextlib.contextmanager
def dispatch_lock(path):
    f = open(path, "a+")
    try:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            raise LockHeld("another dispatcher holds %s" % path)
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt
                f.seek(0)
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        f.close()


def _finish(ctx, d, job, decision_rec, result):
    done = dict(job)
    done.update({"placement": decision_rec, "result": result._asdict()})
    _atomic_write(os.path.join(d["done"], job["id"] + ".json"), json.dumps(done, indent=1, sort_keys=True) + "\n")
    try:
        os.remove(os.path.join(d["running"], job["id"] + ".json"))
    except OSError:
        pass


_SEVERITY = [EXIT_OK, EXIT_NO_HOST, EXIT_ERROR, EXIT_FAILED]


def _worse(a, b):
    """The more serious of two exit codes: a failed job outranks a router error, which outranks waiting."""
    return a if _SEVERITY.index(a) >= _SEVERITY.index(b) else b


def dispatch(ctx, max_jobs=None, only_job=None):
    """Place and run queued jobs, one at a time. Returns (exit_code, outcomes)."""
    d = ensure_state(ctx.state_dir)
    outcomes, ran = [], 0
    code = EXIT_OK
    with dispatch_lock(d["lock"]):
        for name in _job_files(d, "pending"):
            if max_jobs is not None and ran >= max_jobs:
                break
            if only_job and name != only_job + ".json":
                continue
            ppath = os.path.join(d["pending"], name)
            try:
                job = _load_job(ppath)
            except (OSError, ValueError) as e:
                outcomes.append({"job": name[:-5], "outcome": "error", "why": "job file unreadable: %s" % e})
                code = _worse(code, EXIT_ERROR)
                continue
            cls = ctx.classes.get(job["class"])
            if cls is None:
                why = "class %r is no longer defined" % job["class"]
                _note_deferral(ctx, d, job, "class", why)
                outcomes.append({"job": job["id"], "outcome": "error", "why": why})
                code = _worse(code, EXIT_ERROR)
                continue
            now = ctx.clock()
            try:
                feed = read_feed(ctx.feed_path, now)
            except FeedError as e:
                _note_deferral(ctx, d, job, "feed", str(e))
                outcomes.append({"job": job["id"], "outcome": "deferred", "kind": "feed-error", "why": str(e)})
                code = _worse(code, EXIT_ERROR)
                continue
            dec = pick(cls, ctx.hosts, feed, now, ctx.stale_after_s, make_runnable(ctx.here))
            if dec.outcome != "placed":
                _note_deferral(ctx, d, job, dec.kind, dec.why, dec.considered)
                outcomes.append({"job": job["id"], "outcome": "deferred", "kind": dec.kind, "why": dec.why})
                code = _worse(code, EXIT_NO_HOST)
                continue
            rpath = os.path.join(d["running"], name)
            try:
                os.rename(ppath, rpath)             # the claim: whoever renames it owns it
            except OSError:
                continue
            rec = {"host": dec.host.id, "why": dec.why, "free_threads": dec.free_threads,
                   "considered": [v._asdict() for v in dec.considered]}
            try:
                log_event(ctx, "placed", job=job["id"], host=dec.host.id, why=dec.why,
                          considered=rec["considered"], **{"class": cls.name})
            except RouterError as e:
                os.rename(rpath, ppath)             # no log, no run: put it back
                outcomes.append({"job": job["id"], "outcome": "error", "why": str(e)})
                code = _worse(code, EXIT_ERROR)
                break
            try:
                result = ctx.runner(dec.host, cls)
            except Exception as e:                  # a runner bug must not leave a job stuck in running/
                t = utc_iso(ctx.clock())
                result = RunResult("error", None, 0.0, "", "runner raised %s: %s" % (type(e).__name__, e), t, t)
            ran += 1
            _finish(ctx, d, job, rec, result)
            try:
                log_event(ctx, "finished", job=job["id"], host=dec.host.id, status=result.status,
                          exit_code=result.exit_code, duration_s=result.duration_s, **{"class": cls.name})
            except RouterError as e:
                outcomes.append({"job": job["id"], "outcome": "error", "why": str(e)})
                code = _worse(code, EXIT_ERROR)
                continue
            outcomes.append({"job": job["id"], "outcome": "ran", "host": dec.host.id, "status": result.status,
                             "exit_code": result.exit_code, "duration_s": result.duration_s})
            if result.status != "ok":
                code = _worse(code, EXIT_FAILED)
    return code, outcomes


def _note_deferral(ctx, d, job, kind, why, considered=None):
    """Log a deferral once per distinct reason, so a job waiting two days does not write 24 lines a day."""
    path = os.path.join(d["pending"], job["id"] + ".json")
    sig = "%s|%s" % (kind, why)
    prior = job.get("deferred")
    if isinstance(prior, dict) and prior.get("sig") == sig:
        return
    job = dict(job)
    job["deferred"] = {"sig": sig, "kind": kind, "why": why, "since": utc_iso(ctx.clock())}
    _atomic_write(path, json.dumps(job, indent=1, sort_keys=True) + "\n")
    extra = {"considered": [v._asdict() for v in considered]} if considered else {}
    log_event(ctx, "deferred", job=job["id"], kind=kind, reason=why, **dict(extra, **{"class": job["class"]}))


# ------------------------------------------------------------------------------------- status and log

def read_log(state_dir, last=None):
    path = _dirs(state_dir)["log"]
    rows = []
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except ValueError:
                        rows.append({"event": "unreadable-line", "raw": line[:200]})
    except FileNotFoundError:
        return []
    return rows[-last:] if last else rows


def status(ctx):
    d = _dirs(ctx.state_dir)
    now = ctx.clock()
    out = {"state_dir": ctx.state_dir, "pending": [], "running": [], "done": 0, "last": []}
    for where in ("pending", "running"):
        for n in _job_files(d, where):
            try:
                j = _load_job(os.path.join(d[where], n))
            except (OSError, ValueError):
                out[where].append({"id": n[:-5], "problem": "file unreadable"})
                continue
            entry = {"id": j["id"], "class": j["class"], "submitted_at": j.get("submitted_at")}
            sub = parse_time(j.get("submitted_at"))
            if sub is not None:
                entry["age_s"] = round(now - sub)
            if isinstance(j.get("deferred"), dict):
                entry["waiting_because"] = j["deferred"].get("why")
            if where == "running":
                cls = ctx.classes.get(j["class"])
                if cls and sub is not None and now - sub > cls.timeout_s + 600:
                    entry["overdue"] = "older than its timeout plus 10 min, and no router is known to be running it; not re-run"
            out[where].append(entry)
    out["done"] = len(_job_files(d, "done"))
    out["last"] = [r for r in read_log(ctx.state_dir, 40) if r.get("event") in ("placed", "finished", "deferred")][-8:]
    return out


# --------------------------------------------------------------------------------------------- check

def check(ctx, now):
    """Registry, classes and feed agree. Returns (problems, notes). Raises FeedError if the feed cannot be read."""
    feed = read_feed(ctx.feed_path, now)
    problems, notes = [], []
    reg_ids = {h.id for h in ctx.hosts}
    for fid in sorted(feed.rows):
        if fid not in reg_ids:
            problems.append("host %r is in the feed but not in the registry" % fid)
    for h in ctx.hosts:
        if h.in_feed and h.id not in feed.rows:
            problems.append("host %r is in the registry (in_feed) but not in the feed" % h.id)
        if not h.in_feed and h.id in feed.rows:
            problems.append("host %r is marked in_feed=false but the feed lists it" % h.id)
        row = feed.rows.get(h.id)
        if row and h.threads and isinstance(row.get("threads"), int) and row["threads"] != h.threads:
            notes.append("host %r: registry says %d threads, feed says %d" % (h.id, h.threads, row["threads"]))
    for name, c in sorted(ctx.classes.items()):
        for hid in c.eligible_hosts:
            h = next(x for x in ctx.hosts if x.id == hid)
            if not (h.in_cluster and h.accepts_jobs):
                problems.append("class %s lists host %s, which is closed or does not take router jobs" % (name, hid))
        if c.requires_always_on and not any(h.always_on for h in ctx.hosts if h.id in c.eligible_hosts):
            problems.append("class %s needs an always-on host and none of its eligible hosts is" % name)
    return problems, notes


# --------------------------------------------------------------------------------------------- the CLI

def _format_decision(name, dec):
    if dec.outcome == "placed":
        head = "PICK %s" % dec.host.id
    else:
        head = "NONE (%s) %s" % (dec.kind, dec.why)
    lines = [head, "  class %s: %s" % (name, dec.why if dec.outcome == "placed" else "no host takes it now; it would stay queued")]
    others = [v.host for v in dec.considered if v.why == NOT_FOR_CLASS]
    for v in dec.considered:
        if v.why != NOT_FOR_CLASS:
            lines.append("  %-9s %-11s %s" % (v.verdict, v.host, v.why))
    if others:
        lines.append("  skip      (%d)        %s: %s" % (len(others), NOT_FOR_CLASS, ", ".join(others)))
    return "\n".join(lines)


def build_parser():
    p = argparse.ArgumentParser(prog="route.py", description="NODE cluster job router")
    p.add_argument("--feed", default=os.environ.get("JOBROUTER_FEED", DEFAULT_FEED))
    p.add_argument("--hosts", default=os.path.join(HERE_DIR, "hosts.json"))
    p.add_argument("--classes", default=os.path.join(HERE_DIR, "classes.json"))
    p.add_argument("--state-dir", default=os.environ.get("JOBROUTER_STATE", DEFAULT_STATE))
    p.add_argument("--here", default=None, help="host id this router runs on (default: this machine's hostname)")
    p.add_argument("--as-of", default=None, help="replay as of an ISO time with a Z, e.g. 2026-11-23T10:00:00Z")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("pick")
    s.add_argument("class_name")
    s.add_argument("--json", action="store_true")
    s.add_argument("--policy-only", action="store_true", help="ignore whether a job could be started on the host from here")
    sub.add_parser("check")
    s = sub.add_parser("submit")
    s.add_argument("class_name")
    s = sub.add_parser("dispatch")
    s.add_argument("--max", type=int, default=None)
    s = sub.add_parser("run")
    s.add_argument("class_name")
    s = sub.add_parser("status")
    s.add_argument("--json", action="store_true")
    s = sub.add_parser("log")
    s.add_argument("--last", type=int, default=20)
    return p


def main(argv=None, runner=None, out=None, clock=None):
    out = out or sys.stdout
    args = build_parser().parse_args(argv)

    def say(text=""):
        out.write(text + "\n")

    if args.as_of:
        t = parse_time(args.as_of)
        if t is None:
            say("ERROR: --as-of needs an ISO time with a Z, got %r" % args.as_of)
            return EXIT_ERROR
        def clock():
            return t
    clock = clock or time.time
    try:
        hosts, stale = load_registry(args.hosts)
        classes = load_classes(args.classes, hosts)
        ctx = Ctx(hosts, classes, stale, args.feed, args.state_dir, detect_here(hosts, args.here),
                  runner or default_runner, clock)
        if args.cmd == "pick":
            cls = classes.get(args.class_name)
            if cls is None:
                raise RouterError("unknown job class %r (known: %s)" % (args.class_name, ", ".join(sorted(classes))))
            now = clock()
            feed = read_feed(args.feed, now)
            dec = pick(cls, hosts, feed, now, stale, None if args.policy_only else make_runnable(ctx.here))
            if args.json:
                say(json.dumps({"class": cls.name, "outcome": dec.outcome, "kind": dec.kind,
                                "host": dec.host.id if dec.host else None, "why": dec.why,
                                "here": ctx.here, "considered": [v._asdict() for v in dec.considered]}, indent=1))
            else:
                say(_format_decision(cls.name, dec))
            return EXIT_OK if dec.outcome == "placed" else EXIT_NO_HOST
        if args.cmd == "check":
            problems, notes = check(ctx, clock())
            say("CHECK OK" if not problems else "CHECK PROBLEMS (%d)" % len(problems))
            for t in problems:
                say("  problem: " + t)
            for t in notes:
                say("  note: " + t)
            return EXIT_OK if not problems else EXIT_FAILED
        if args.cmd in ("submit", "run"):
            job_id, msg = submit(ctx, args.class_name)
            say("%s: %s" % ("SUBMITTED " + job_id if job_id else "NOT SUBMITTED", msg))
            if args.cmd == "submit":
                return EXIT_OK
            code, outcomes = dispatch(ctx, only_job=job_id) if job_id else dispatch(ctx)
            return _print_outcomes(say, code, outcomes)
        if args.cmd == "dispatch":
            code, outcomes = dispatch(ctx, max_jobs=args.max)
            return _print_outcomes(say, code, outcomes)
        if args.cmd == "status":
            st = status(ctx)
            if args.json:
                say(json.dumps(st, indent=1, sort_keys=True))
            else:
                say("pending %d, running %d, done %d (%s)" % (len(st["pending"]), len(st["running"]), st["done"], st["state_dir"]))
                for w in ("pending", "running"):
                    for j in st[w]:
                        extra = " waiting: %s" % j["waiting_because"] if j.get("waiting_because") else ""
                        extra += " OVERDUE: %s" % j["overdue"] if j.get("overdue") else ""
                        say("  %s %s %s s%s" % (w, j.get("id"), j.get("age_s", "?"), extra))
                for r in st["last"]:
                    say("  %s %s %s %s" % (r.get("at"), r.get("event"), r.get("class"), r.get("host") or r.get("reason") or ""))
            return EXIT_OK
        if args.cmd == "log":
            for r in read_log(args.state_dir, args.last):
                say(json.dumps(r, sort_keys=True, ensure_ascii=False))
            return EXIT_OK
    except LockHeld as e:
        say("LOCKED: %s" % e)
        return EXIT_LOCKED
    except RouterError as e:
        say("ERROR: %s" % e)
        return EXIT_ERROR
    return EXIT_ERROR


def _print_outcomes(say, code, outcomes):
    if not outcomes:
        say("nothing queued")
    for o in outcomes:
        if o["outcome"] == "ran":
            say("RAN %s on %s: %s (exit %s, %.1f s)" % (o["job"], o["host"], o["status"], o["exit_code"], o["duration_s"]))
        else:
            say("%s %s: %s" % (o["outcome"].upper(), o["job"], o["why"]))
    return code


if __name__ == "__main__":
    sys.exit(main())
