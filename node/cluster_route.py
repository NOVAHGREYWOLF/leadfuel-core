#!/usr/bin/env python3
"""NODE cluster-job-router: send a test, lint or build job to the machine that is free for it.

Why: desks run their narrow tests, lint and builds on GREYWOLF (a laptop at 100% CPU with dozens of
sessions) while VM 102 (20 vCPU, the CI runners), the R620 (24 threads) and the R710 (16 threads)
sit idle. GitHub's `runs-on` labels place CI jobs on VM 102 already; nothing placed a job a desk runs
by hand. This file is that one router: run it where the desk is, it measures the targets over ssh,
decides, ships the source and runs the job there.

Rules, all of them refusals rather than fall-throughs:
  * Targets are tried in the order of the targets file (VM 102 first). A target is picked only when
    it is enabled, its facts were measured just now, and it is free: load below `max_load_frac` of
    its threads, and for a heavy job no CI job (`Runner.Worker`) running on a runner host.
  * A target that cannot be reached, or answers with anything unusable, is `unknown`. Unknown is
    never free and never picked. If nothing is free the answer is `wait` (exit 3), never "here".
    Running on this machine instead is the caller's decision, not a fallback of this router.
  * A heavy job (`--heavy`, and every build) honours the estate heavy lock (`heavy_lock.py`, owner
    ruling q205 A): the slot must read free before placement, and `run --go` takes it with
    `heavy_lock.py acquire` and releases it after. Held, stale or unreadable = wait.
  * Small mechanical work (`--kind mechanical`) goes to the local model on THIS machine's loopback
    (node/local_route.py), only when local_route.classify says it is mechanical and the model
    answers. Otherwise it is refused or waits. There is no cloud path anywhere in this file (Law 9;
    a cloud path is a decision, never a fallback).
  * The R620 hosts the hub's Postgres standby (VM 200). Owner's decision (relayed by CONDUCTOR 060
    via ROUTER #138): it takes jobs at low priority (nice 19, idle I/O, a CPU cap well under its 24
    threads) and is SKIPPED whenever its load is at or above half, the standby copy is older than
    its limit or a refresh is running. If either cannot be read, it is unknown and skipped. The
    guard reads overlord's refresh status file with grep and pgrep only (`read_standby_guard`).
  * Transport stays on the LAN: an ssh alias must resolve (`ssh -G`) to a loopback, private or
    tailnet (100.64/10) address, or the target is unknown and nothing is sent.
  * The job runs with no network: the source is a `git archive` of a commit, plus a vendored copy
    of pytest, streamed over ssh into `docker run --rm --network none` (runner hosts) or a mktemp
    directory run as `nobody` under `nice` and `timeout` and removed after (plain hosts). No
    credential, no clone, no push is needed, and nothing is installed on the target.

Usage (dry-run is the default: `where`, and `run` without `--go`, only print):
    cluster_route.py probe                                       measure every target, print facts
    cluster_route.py where --kind test [--heavy] -- python -m pytest -q tests/test_x.py
    cluster_route.py run   --kind test --ref HEAD --go -- python -m pytest -q tests/test_x.py
    cluster_route.py run   --kind mechanical --title "fix typos in README" --prompt-file p.txt --go
  Options: --targets FILE (default node/cluster_targets.json, or $CLUSTER_ROUTE_TARGETS)
           --facts FILE (use recorded facts instead of probing; tests and rehearsals)
           --heavy-lock-state free|held|unknown (tests only; default reads heavy_lock.py status)
           --repo DIR --ref REF --timeout S --log FILE

Exit codes: 0 placed (dry-run) or the job passed; 1 the job failed; 2 refused or error;
3 wait (nothing free, lock not free, or the local model not up).

Stdlib only. Lives in leadfuel-core node/; tests in tests/test_cluster_route.py.
"""
from __future__ import annotations

import argparse
import datetime as dt
import importlib.util
import io
import ipaddress
import json
import os
import re
import secrets
import shlex
import subprocess
import sys
import tarfile
import tempfile
from dataclasses import dataclass, field

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_TARGETS = os.path.join(HERE, "cluster_targets.json")
TARGETS_SCHEMA = "cluster-targets-1"
DEFAULT_HEAVY_LOCK = os.environ.get(
    "HEAVY_LOCK_PY", r"F:\Leadfuel\repos\novahub\scripts\heavy_lock.py")
DEFAULT_LOG = os.path.join(os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"),
                           "cluster_route", "placements.jsonl")
KINDS = ("test", "lint", "build", "mechanical")
# pytest and what it needs on Python 3.11+ (importlib.metadata.requires("pytest"), pytest 9.0).
VENDOR = ("pytest", "_pytest", "pluggy", "iniconfig", "packaging", "pygments", "py")
SSH_OPTS = ["-o", "BatchMode=yes", "-o", "ConnectTimeout=8"]
PROBE_TIMEOUT_S = 25
LAN_NETS = tuple(ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16",   # RFC 1918
    "100.64.0.0/10",                                    # the tailnet (CGNAT range)
    "fc00::/7"))                                        # IPv6 unique local

# One line per fact; `pgrep -x` matches the process name, so the probe cannot count itself.
PROBE_SCRIPT = ("echo nproc=$(nproc); echo load=$(cat /proc/loadavg); "
                "echo workers=$(pgrep -c -x Runner.Worker 2>/dev/null || true); "
                "echo memavail_kb=$(awk '/MemAvailable/{print $2}' /proc/meminfo)")


def _local_route():
    spec = importlib.util.spec_from_file_location("local_route", os.path.join(HERE, "local_route.py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules.setdefault("local_route", mod)
    spec.loader.exec_module(mod)
    return sys.modules["local_route"]


# ---------------------------------------------------------------------------------------- model
@dataclass(frozen=True)
class Target:
    id: str
    ssh: str
    exec: str                 # "docker" or "plain"
    python: str = "python3"
    image: str = ""
    enabled: bool = False
    counts_runners: bool = False
    cpus: int = 4
    memory_gb: int = 4
    max_load_frac: float = 0.5
    cpu_cap: int = 0          # plain hosts: taskset to CPUs 0..cap-1 (0 = no cap)
    idle_io: bool = False     # plain hosts: ionice -c3, so the job's disk work yields to everything
    guard: dict | None = None # {"kind": "standby-refresh", "via": alias, "status_file": ..., "max_age_s": n}

    @classmethod
    def from_dict(cls, d: dict) -> "Target":
        if not isinstance(d, dict) or not d.get("id") or not d.get("ssh"):
            raise ValueError(f"target needs an id and an ssh alias: {d!r}")
        if d.get("exec") not in ("docker", "plain"):
            raise ValueError(f"target {d.get('id')}: exec must be docker or plain")
        if d["exec"] == "docker" and not d.get("image"):
            raise ValueError(f"target {d['id']}: a docker target names its image")
        if not isinstance(d.get("enabled", False), bool):
            raise ValueError(f"target {d['id']}: enabled must be true or false")
        frac = float(d.get("max_load_frac", 0.5))
        if not 0 < frac <= 1:
            raise ValueError(f"target {d['id']}: max_load_frac must be in (0, 1]")
        guard = d.get("guard")
        if guard is not None:
            if (not isinstance(guard, dict) or guard.get("kind") != "standby-refresh"
                    or not guard.get("via") or not guard.get("status_file")
                    or not isinstance(guard.get("max_age_s"), int) or guard["max_age_s"] <= 0):
                raise ValueError(f"target {d['id']}: guard needs kind standby-refresh, via, "
                                 "status_file and a positive max_age_s")
            if frac > 0.5 or not int(d.get("cpu_cap", 0)):
                raise ValueError(f"target {d['id']}: a guarded host takes max_load_frac <= 0.5 "
                                 "and a cpu_cap (owner, CONDUCTOR 060)")
        cap = int(d.get("cpu_cap", 0))
        if cap < 0:
            raise ValueError(f"target {d['id']}: cpu_cap must be 0 or more")
        return cls(id=str(d["id"]), ssh=str(d["ssh"]), exec=d["exec"],
                   python=str(d.get("python", "python3")), image=str(d.get("image", "")),
                   enabled=d.get("enabled", False), counts_runners=bool(d.get("counts_runners", False)),
                   cpus=int(d.get("cpus", 4)), memory_gb=int(d.get("memory_gb", 4)), max_load_frac=frac,
                   cpu_cap=cap, idle_io=bool(d.get("idle_io", False)), guard=guard)


@dataclass(frozen=True)
class Facts:
    state: str                # "ok" or "unknown"
    why: str
    threads: int | None
    load1: float | None
    workers: int | None
    mem_avail_gb: float | None
    guard: str | None = None      # for a guarded target: "ok", "lag" or "unknown"; None = not read
    guard_why: str = ""

    @classmethod
    def from_dict(cls, d: dict) -> "Facts":
        f = cls(str(d.get("state")), str(d.get("why", "")), d.get("threads"), d.get("load1"),
                d.get("workers"), d.get("mem_avail_gb"), d.get("guard"), str(d.get("guard_why", "")))
        return f if f.state == "ok" and _usable(f) else Facts.unknown(f"recorded facts unusable: {d!r}")

    @staticmethod
    def unknown(why: str) -> "Facts":
        return Facts("unknown", why, None, None, None, None)


def _usable(f: Facts) -> bool:
    return (isinstance(f.threads, int) and f.threads > 0
            and isinstance(f.load1, (int, float)) and f.load1 >= 0)


@dataclass
class Decision:
    action: str               # "run", "wait" or "refuse"
    target: str | None
    why: str
    considered: list = field(default_factory=list)   # (target id, verdict, why)


def load_targets(path: str) -> list[Target]:
    with open(path, encoding="utf-8-sig") as f:   # a BOM from PowerShell 5 is fine
        doc = json.load(f)
    if not isinstance(doc, dict) or doc.get("schema") != TARGETS_SCHEMA:
        raise ValueError(f"{path}: schema is not {TARGETS_SCHEMA}")
    targets = [Target.from_dict(t) for t in doc.get("targets") or []]
    if len({t.id for t in targets}) != len(targets):
        raise ValueError(f"{path}: a target id appears twice")
    return targets


# -------------------------------------------------------------------------------- decision core
def is_heavy(job: dict) -> bool:
    return bool(job.get("heavy")) or job.get("kind") == "build"


def decide(job: dict, targets: list[Target], facts: dict, heavy_lock: str,
           local_model: str = "unknown") -> Decision:
    """Pure: where this job goes, from facts already measured. Never raises on bad facts."""
    kind = job.get("kind")
    if kind not in KINDS:
        return Decision("refuse", None, f"kind {kind!r} is not one of {', '.join(KINDS)}")

    if kind == "mechanical":
        c = _local_route().classify(job)
        if c.route != "local":
            return Decision("refuse", None,
                            f"not small mechanical work ({c.why}); the local model will not take it "
                            "and this router has no other model. Choosing one is the caller's "
                            "decision, never a fallback")
        if local_model != "up":
            return Decision("wait", None, f"local model is {local_model}; no fallback")
        return Decision("run", "local-model", f"mechanical ({c.why}), local model up on loopback")

    heavy = is_heavy(job)
    if heavy and heavy_lock != "free":
        return Decision("wait", None, f"heavy job and the heavy lock is {heavy_lock}")

    considered = []
    for t in targets:
        if not t.enabled:
            considered.append((t.id, "disabled", "enabled is false in the targets file"))
            continue
        f = facts.get(t.id)
        if not isinstance(f, Facts) or f.state != "ok" or not _usable(f):
            considered.append((t.id, "unknown", f.why if isinstance(f, Facts) else "not measured"))
            continue
        if t.guard is not None and f.guard != "ok":
            verdict = "busy" if f.guard == "lag" else "unknown"
            considered.append((t.id, verdict, "standby guard: " + (f.guard_why or "not read")))
            continue
        frac = f.load1 / f.threads
        if frac >= t.max_load_frac:
            considered.append((t.id, "busy", f"load {f.load1:g} on {f.threads} threads"))
            continue
        if t.counts_runners and heavy:
            if not isinstance(f.workers, int):
                considered.append((t.id, "unknown", "CI job count not measured"))
                continue
            if f.workers > 0:
                considered.append((t.id, "busy", f"{f.workers} CI job(s) running"))
                continue
        considered.append((t.id, "free", f"load {f.load1:g} on {f.threads} threads"))
        return Decision("run", t.id, f"{t.id} is free", considered)
    return Decision("wait", None, "no enabled target is free and measured", considered)


# --------------------------------------------------------------------------------------- facts
def parse_probe(text: str, counts_runners: bool) -> Facts:
    kv = {}
    for line in (text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    try:
        threads = int(kv.get("nproc", ""))
        load1 = float(kv.get("load", "").split()[0])
    except (ValueError, IndexError):
        return Facts.unknown(f"probe answer unusable: {text[:120]!r}")
    workers = None
    if kv.get("workers", "").isdigit():
        workers = int(kv["workers"])
    elif counts_runners:
        return Facts.unknown("runner host did not say how many CI jobs run")
    mem = None
    if kv.get("memavail_kb", "").isdigit():
        mem = round(int(kv["memavail_kb"]) / 1048576, 1)
    f = Facts("ok", "probed", threads, load1, workers, mem)
    return f if _usable(f) else Facts.unknown(f"probe values out of range: {text[:120]!r}")


class NotLan(ValueError):
    """The target does not resolve to this machine, the LAN or the tailnet. Nothing is sent."""


def check_lan(host) -> str:
    try:
        ip = ipaddress.ip_address(host)
    except (ValueError, TypeError):
        raise NotLan(f"{host!r} is not an address") from None
    # Named ranges, not `is_private`, which also counts documentation and reserved blocks.
    if ip.is_loopback or any(ip.version == n.version and ip in n for n in LAN_NETS):
        return host
    raise NotLan(f"{host} is not loopback, private or tailnet")


def resolve_alias(alias: str, run=subprocess.run) -> str:
    out = run(["ssh", "-G", alias], capture_output=True, text=True, timeout=10)
    for line in out.stdout.splitlines():
        if line.startswith("hostname "):
            return line.split(None, 1)[1].strip()
    return ""


def probe(target: Target, run=subprocess.run, resolve=None) -> Facts:
    """Measure one target over ssh. Any failure is `unknown`, with the reason."""
    try:
        check_lan((resolve or (lambda a: resolve_alias(a, run)))(target.ssh))
    except NotLan as e:
        return Facts.unknown(f"transport refused: {e}")
    except (OSError, subprocess.SubprocessError) as e:
        return Facts.unknown(f"could not resolve {target.ssh}: {e}")
    try:
        r = run(["ssh", *SSH_OPTS, target.ssh, PROBE_SCRIPT], capture_output=True, text=True,
                timeout=PROBE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return Facts.unknown(f"probe timed out after {PROBE_TIMEOUT_S} s")
    except OSError as e:
        return Facts.unknown(f"ssh could not start: {e}")
    if r.returncode != 0:
        return Facts.unknown(f"ssh exit {r.returncode}: {(r.stderr or '').strip()[:160]}")
    f = parse_probe(r.stdout, target.counts_runners)
    if target.guard is not None and f.state == "ok":
        g, why = read_standby_guard(target.guard, run=run, resolve=resolve)
        f = Facts(f.state, f.why, f.threads, f.load1, f.workers, f.mem_avail_gb, g, why)
    return f


# The R620 hosts the hub's Postgres standby (VM 200). It is a copy refreshed from GREYWOLF by
# overlord's cron (/root/pg-standby-refresh.sh nightly, /root/pg-standby-catchup.sh every 2 h). The
# refresh writes one line per run to a status file; the newest " OK " line is when the copy was
# last good. "Lag" here is that age, the same measure catchup uses (its MAXAGE, 24 h). Read-only:
# grep and pgrep on overlord. No Postgres connection, no lock taken (`flock -n` would take it),
# nothing written. `[p]g-...` keeps pgrep from counting its own command line.
def standby_guard_script(guard: dict) -> str:
    f = shlex.quote(guard["status_file"])
    return ("echo now=$(date -u +%s); "
            f"echo last_ok=$(grep ' OK ' {f} 2>/dev/null | tail -1 | cut -d' ' -f1); "
            "echo refreshing=$(pgrep -fc '[p]g-standby-refresh' 2>/dev/null || true)")


def parse_standby_guard(text: str, max_age_s: int) -> tuple[str, str]:
    """("ok"|"lag"|"unknown", why). Anything it cannot read is unknown, never ok."""
    kv = {}
    for line in (text or "").splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            kv[k.strip()] = v.strip()
    now, last, busy = kv.get("now", ""), kv.get("last_ok", ""), kv.get("refreshing", "")
    if not now.isdigit():
        return "unknown", "overlord's clock was not read"
    if not busy.isdigit():
        return "unknown", "could not tell whether a refresh is running"
    if int(busy) > 0:
        return "lag", "a standby refresh is running now"
    if not re.fullmatch(r"\d{8}T\d{6}Z", last):
        return "unknown", f"no readable OK line in the status file ({last[:40]!r})"
    try:
        t = dt.datetime.strptime(last, "%Y%m%dT%H%M%SZ").replace(tzinfo=dt.timezone.utc).timestamp()
    except ValueError:
        return "unknown", f"OK timestamp {last!r} does not parse"
    age = int(now) - int(t)
    if age < -300:
        return "unknown", f"OK timestamp is {-age} s in the future of overlord's clock"
    if age > max_age_s:
        return "lag", f"standby copy is {age // 3600} h old, over {max_age_s // 3600} h"
    return "ok", f"standby copy is {max(age, 0) // 3600} h old, no refresh running"


def read_standby_guard(guard: dict, run=subprocess.run, resolve=None) -> tuple[str, str]:
    try:
        check_lan((resolve or (lambda a: resolve_alias(a, run)))(guard["via"]))
    except NotLan as e:
        return "unknown", f"guard transport refused: {e}"
    except (OSError, subprocess.SubprocessError) as e:
        return "unknown", f"could not resolve {guard['via']}: {e}"
    try:
        r = run(["ssh", *SSH_OPTS, guard["via"], standby_guard_script(guard)], capture_output=True,
                text=True, timeout=PROBE_TIMEOUT_S)
    except subprocess.TimeoutExpired:
        return "unknown", f"guard read timed out after {PROBE_TIMEOUT_S} s"
    except OSError as e:
        return "unknown", f"ssh could not start: {e}"
    if r.returncode != 0:
        return "unknown", f"guard ssh exit {r.returncode}"
    return parse_standby_guard(r.stdout, guard["max_age_s"])


def parse_heavy_status(text: str, rc: int) -> str:
    """free only when every slot line says free; a live holder is held; anything else unknown."""
    if rc != 0:
        return "unknown"
    slots = [ln.split(":", 1)[1].strip() for ln in (text or "").splitlines() if ln.startswith("slot-")]
    if not slots:
        return "unknown"
    if all(s == "free" for s in slots):
        return "free"
    if any(s.startswith("live") for s in slots) and all(s == "free" or s.startswith("live") for s in slots):
        return "held"
    return "unknown"


def heavy_lock_state(path: str = DEFAULT_HEAVY_LOCK, run=subprocess.run) -> tuple[str, str]:
    if not os.path.isfile(path):
        return "unknown", f"heavy_lock.py not found at {path}"
    try:
        r = run([sys.executable, path, "status"], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return "unknown", str(e)
    return parse_heavy_status(r.stdout, r.returncode), r.stdout.strip()


def local_model_state() -> str:
    lr = _local_route()
    try:
        m = lr.LocalModel()
        m._http("GET", m.endpoint + "/api/tags", None, 5.0)
        return "up"
    except (lr.LocalUnavailable, lr.NotLocal):
        return "unknown"


# ------------------------------------------------------------------------------------ execution
def _safe_id(job_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9-]", "", job_id)[:40] or "job"


def remote_command(target: Target, argv: list[str], job_id: str, timeout_s: int) -> str:
    """The one shell string run on the target; the bundle arrives on its stdin."""
    argv = [target.python if i == 0 and a == "python" else a for i, a in enumerate(argv)]
    job = " ".join(shlex.quote(a) for a in argv)
    t = int(timeout_s)
    if target.exec == "docker":
        inner = (f"mkdir -p /w && cd /w && tar -xzf - && "
                 f"PYTHONPATH=/w/_vendor HOME=/w PYTHONDONTWRITEBYTECODE=1 timeout {t} {job}")
        return (f"docker run --rm -i --network none --cpus {target.cpus} --memory {target.memory_gb}g "
                f"--name jobroute-{_safe_id(job_id)} --label jobroute=1 {shlex.quote(target.image)} "
                f"sh -c {shlex.quote(inner)}")
    low = "nice -n 19"
    if target.idle_io:
        low += " ionice -c3"
    if target.cpu_cap:
        low += f" taskset -c 0-{target.cpu_cap - 1}"
    return (f'd=$(mktemp -d /var/tmp/jobroute.XXXXXX) && chown nobody "$d" && cd "$d" && '
            f"runuser -u nobody -- tar -xzf - && "
            f'runuser -u nobody -- env PYTHONPATH="$d/_vendor" HOME="$d" PYTHONDONTWRITEBYTECODE=1 '
            f"{low} timeout {t} {job}; rc=$?; cd /; "
            f'[ -n "$d" ] && rm -rf "$d"; exit $rc')


def git_archive(repo: str, ref: str, run=subprocess.run) -> bytes:
    r = run(["git", "-C", repo, "archive", "--format=tar", ref], capture_output=True, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"git archive {ref} failed: {r.stderr.decode(errors='replace')[:200]}")
    return r.stdout


def make_bundle(tree_tar: bytes, vendor=VENDOR) -> bytes:
    """The tree plus a vendored copy of pytest (pure Python) under _vendor/, no bytecode, gzipped."""
    out = io.BytesIO()
    with tarfile.open(fileobj=out, mode="w:gz", compresslevel=6) as dst:   # the link is slow
        with tarfile.open(fileobj=io.BytesIO(tree_tar)) as src:
            for m in src.getmembers():
                dst.addfile(m, src.extractfile(m) if m.isfile() else None)
        for name in vendor:
            spec = importlib.util.find_spec(name)
            if spec is None or not spec.origin:
                continue
            base = os.path.dirname(spec.origin) if spec.submodule_search_locations else spec.origin
            dst.add(base, arcname="_vendor/" + os.path.basename(base),
                    filter=lambda ti: None if "__pycache__" in ti.name or ti.name.endswith(".pyc") else ti)
    return out.getvalue()


def log_event(path: str, **fields) -> None:
    fields["ts"] = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(fields, sort_keys=True) + "\n")


def acquire_heavy(job_id: str, path: str = DEFAULT_HEAVY_LOCK, run=subprocess.run):
    tok = os.path.join(tempfile.gettempdir(), f"cluster_route-{_safe_id(job_id)}.token")
    r = run([sys.executable, path, "acquire", "--job", f"cluster-route-{_safe_id(job_id)}",
             "--pid", str(os.getpid()), "--token-file", tok], capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None, (r.stdout + r.stderr).strip()
    with open(tok, encoding="utf-8") as f:
        return f.read().strip(), r.stdout.strip()


def release_heavy(token: str, path: str = DEFAULT_HEAVY_LOCK, run=subprocess.run) -> None:
    run([sys.executable, path, "release", "--token", token], capture_output=True, text=True, timeout=60)


# ------------------------------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="cluster_route", description=__doc__.split("\n")[0])
    sub = p.add_subparsers(dest="cmd", required=True)
    pr = sub.add_parser("probe")
    pr.add_argument("--targets", default=os.environ.get("CLUSTER_ROUTE_TARGETS", DEFAULT_TARGETS))
    for name in ("where", "run"):
        s = sub.add_parser(name)
        s.add_argument("--kind", required=True, choices=KINDS)
        s.add_argument("--heavy", action="store_true")
        s.add_argument("--title", default="")
        s.add_argument("--effort", default="")
        s.add_argument("--repo", default=".")
        s.add_argument("--ref", default="HEAD")
        s.add_argument("--timeout", type=int, default=1800)
        s.add_argument("--targets", default=os.environ.get("CLUSTER_ROUTE_TARGETS", DEFAULT_TARGETS))
        s.add_argument("--facts")
        s.add_argument("--heavy-lock-state", choices=("free", "held", "unknown"))
        s.add_argument("--local-model-state", choices=("up", "unknown"))
        s.add_argument("--prompt-file")
        s.add_argument("--log", default=DEFAULT_LOG)
        s.add_argument("--go", action="store_true", help="run: actually start the job")
        s.add_argument("argv", nargs="*")
    return p


def main(argv=None, run=subprocess.run, out=None) -> int:
    out = out or sys.stdout
    say = lambda *a: print(*a, file=out, flush=True)  # noqa: E731
    a = build_parser().parse_args(argv)
    try:
        targets = load_targets(a.targets)
    except (OSError, ValueError) as e:
        say(f"ERROR targets: {e}")
        return 2

    if a.cmd == "probe":
        for t in targets:
            f = probe(t, run=run)
            say(json.dumps({"target": t.id, "enabled": t.enabled, **f.__dict__}))
        return 0

    job = {"kind": a.kind, "heavy": a.heavy, "title": a.title, "effort": a.effort}
    if a.kind != "mechanical" and not a.argv:
        say("ERROR: give the job's command after --")
        return 2
    if a.facts:
        with open(a.facts, encoding="utf-8") as f:
            facts = {k: Facts.from_dict(v) for k, v in json.load(f).items()}
    elif a.kind == "mechanical":
        facts = {}
    else:
        facts = {t.id: probe(t, run=run) for t in targets if t.enabled}
    lock, lock_text = (a.heavy_lock_state, "given") if a.heavy_lock_state else (
        heavy_lock_state(run=run) if is_heavy(job) else ("not-needed", ""))
    model = a.local_model_state or (local_model_state() if a.kind == "mechanical" else "unknown")
    d = decide(job, targets, facts, lock, model)
    for tid, verdict, why in d.considered:
        say(f"  {tid:8} {verdict:8} {why}")
    job_id = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + secrets.token_hex(2)

    if d.action != "run":
        say(f"{d.action.upper()}: {d.why}")
        if a.go:
            log_event(a.log, event=d.action, job=job_id, kind=a.kind, why=d.why)
        return 3 if d.action == "wait" else 2

    if d.target == "local-model":
        cmd = [sys.executable, os.path.join(HERE, "local_route.py"), "run", "--prompt-file",
               a.prompt_file or "<prompt file>", "--require-gpu"]
        say(f"{'RUN' if a.cmd == 'run' and a.go else 'WOULD run'} on local-model: {' '.join(cmd)}")
        if not (a.cmd == "run" and a.go):
            return 0
        if not a.prompt_file:
            say("ERROR: --prompt-file is required to run mechanical work")
            return 2
        log_event(a.log, event="placed", job=job_id, kind=a.kind, target="local-model")
        r = run(cmd)
        log_event(a.log, event="finished", job=job_id, target="local-model", rc=r.returncode)
        return 0 if r.returncode == 0 else 1

    target = next(t for t in targets if t.id == d.target)
    remote = remote_command(target, a.argv, job_id, a.timeout)
    ssh = ["ssh", *SSH_OPTS, target.ssh, remote]
    if not (a.cmd == "run" and a.go):
        say(f"WOULD run on {target.id} ({d.why}); source = git archive {a.ref} of {a.repo} + vendored pytest")
        say("  " + " ".join(shlex.quote(x) for x in ssh))
        return 0

    token = None
    if is_heavy(job):
        token, msg = acquire_heavy(job_id, run=run)
        if token is None:
            say(f"WAIT: heavy lock refused: {msg}")
            log_event(a.log, event="wait", job=job_id, kind=a.kind, why="heavy lock refused: " + msg)
            return 3
    try:
        bundle = make_bundle(git_archive(a.repo, a.ref, run=run))
        sha = run(["git", "-C", a.repo, "rev-parse", a.ref], capture_output=True, text=True,
                  timeout=30).stdout.strip()
        log_event(a.log, event="placed", job=job_id, kind=a.kind, target=target.id, sha=sha,
                  argv=a.argv, bundle_bytes=len(bundle))
        say(f"RUN {job_id} on {target.id}: {sha[:12]} {' '.join(a.argv)}")
        r = run(ssh, input=bundle, timeout=a.timeout + 120)
        log_event(a.log, event="finished", job=job_id, target=target.id, rc=r.returncode)
        say(f"DONE {job_id} on {target.id}: exit {r.returncode}")
        return 0 if r.returncode == 0 else 1
    finally:
        if token:
            release_heavy(token, run=run)


if __name__ == "__main__":
    sys.exit(main())
