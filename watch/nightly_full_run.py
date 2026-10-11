"""WATCH Q354-NIGHTLY-FULL-RUN: one full SERIAL bare pytest on the hub's origin/main, on this PC, every night.

WHY (owner, q354 "A"): desks stop running the full suite locally; CI (Linux, xdist) runs it once. CI cannot
see two kinds of failure, and this job is the guard for both:
  1. failures that only show in a serial run or a different test order (CI shards with xdist);
  2. failures that only happen on Windows (the home node runs on Windows).

WHAT ONE RUN DOES (stdlib only, run by path, Windows or POSIX):
  1. positive controls: the classifier must give the known answer on built-in samples, or the run is UNKNOWN;
  2. takes a small local mutex so two runs (or a dry run and the real one) never share the worktree;
  3. `git fetch origin main` in the hub repo and checks the fetched SHA against `git ls-remote`;
  4. takes the estate's heavy slot with the hub's own `scripts/heavy_lock.py` (taken from that same commit),
     retrying every POLL seconds for up to WAIT minutes, then records SKIPPED-BUSY. It NEVER runs pytest
     without the slot;
  5. refreshes the DEDICATED worktree `<hub>/.claude/worktrees/nightly-full-run`, detached at that SHA
     (never the shared checkout, never another desk's worktree), and refuses to touch a folder it cannot
     prove is that worktree;
  6. runs `<interpreter> -m pytest -q -p no:cacheprovider` there, serial (no -n), with a wall cap;
  7. classifies the output, appends ONE result line to the log, releases the slot, exits with a code that
     mirrors the verdict (PASS 0, FAIL 1, UNKNOWN 2, SKIPPED-BUSY 3) so Task Scheduler's LastTaskResult says it too.

NOTHING LEAVES THE MACHINE (Law 9): the only network use is the inbound `git fetch` / `git ls-remote` from the
hub's own origin. No email, webhook, push or post. The pytest child runs with secret-looking environment
variables removed (and the hub's conftest refuses network calls), so no credential reaches the tests.

THE VERDICT RULES (a check that cannot establish a state must not report one):
  PASS          only when pytest exited 0, printed its final summary, the hub conftest's own `base:` line names
                the commit we meant to test, `scope: N tests selected` is present and above the floor, nothing
                failed or errored, and passed+skipped+xfailed+xpassed adds up to N.
  FAIL          pytest showed failures or errors (rc 1 or 2). The failing ids go under the line.
  SKIPPED-BUSY  the slot (or hub CI) stayed busy for the whole wait. Nothing was run.
  UNKNOWN       everything else: a crash with no summary, a timeout, an unparseable run, a fetch that could not
                be verified, a worktree that could not be proved, an interpreter that does not import pytest,
                a lock helper that could not be read, hub CI state that docker could not answer, ...
  A dry run (`--dry-run`) never writes a result line, so it cannot leave a PASS behind.

THE LOG (one line per night, UTC, key=value; failing ids indented underneath on a FAIL):
  2026-10-12T13:07:22Z PASS main=4a9c3c289376 collected=6688 passed=6670 failed=0 skipped=18 errors=0 \
      xfail=0 xpass=0 wall=34m12s wait=0m py=3.12.10 pytest=9.1.1 host=GREYWOLF
  A night with NO line means the task did not start (PC off, asleep or the task disabled). Read that as UNKNOWN.
  Only ids, counts and short reasons are written: no test output, no environment, no secrets.

Raw pytest output is kept locally for the last RUNS_KEPT nights under the state directory (never committed).

Usage:  python watch/nightly_full_run.py [--dry-run] [--wait-minutes N] [--poll-seconds N] [--cap-minutes N]
        [--hub PATH] [--log PATH] [--state PATH] [--python PATH] [--min-collected N]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import socket
import subprocess
import sys
import time
import traceback

SCHEMA = "watch.nightly_full_run/1"
JOB = "nightly-full-run"
DESK = "WATCH nightly-full-run (scheduled task)"
EXIT = {"PASS": 0, "FAIL": 1, "UNKNOWN": 2, "SKIPPED-BUSY": 3}

DEFAULT_HUB = r"F:\Leadfuel\repos\novahub"
DEFAULT_LOG = r"F:\Claude Sessions\handoff\nightly-full-run.log"
WORKTREE_REL = os.path.join(".claude", "worktrees", "nightly-full-run")
WAIT_MINUTES = 90          # how long to wait for the heavy slot before SKIPPED-BUSY
POLL_SECONDS = 120         # between slot attempts (each attempt asks docker, so not too often)
CAP_MINUTES = 180          # pytest wall cap; a serial run is ~30-60 min, a 21 h one is a starved box
MIN_COLLECTED = 1000       # a "pass" over fewer tests than this is not the suite
DROP_NOTE_PERCENT = 10     # note when collected fell by more than this against the previous night
MUTEX_STALE_HOURS = 6.0    # WAIT + CAP + slack; a mutex older than this is stale whatever its pid says
RUNS_KEPT = 10
IDS_IN_LOG = 100
TAIL_BYTES = 4 * 1024 * 1024

# Environment names that look like credentials never reach the pytest child.
SECRET_RX = re.compile(r"(KEY|TOKEN|SECRET|PASSW|CREDENTIAL|DSN|AUTH)", re.IGNORECASE)
# Names that would change WHICH tests run or WHERE they point; the hub's conftest chooses its own database.
DROP_ENV = {"PYTEST_ADDOPTS", "PYTEST_PLUGINS", "DATABASE_URL", "GITHUB_ACTIONS", "HEAVY_LOCK_TOKEN",
            "HUB_TEST_USE_AMBIENT_DB", "HUB_TEST_ALLOW_NETWORK"}


# ── small helpers ─────────────────────────────────────────────────────────────────────────────

def utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def stamp(t: dt.datetime | None = None) -> str:
    return (t or utc_now()).strftime("%Y-%m-%dT%H:%M:%SZ")


def human_duration(seconds: float | None) -> str:
    if seconds is None:
        return "-"
    s = int(round(seconds))
    h, rem = divmod(s, 3600)
    m, sec = divmod(rem, 60)
    if h:
        return f"{h}h{m:02d}m{sec:02d}s"
    return f"{m}m{sec:02d}s"


def norm(path: str) -> str:
    return os.path.normcase(os.path.realpath(path))


def default_state_dir() -> str:
    base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~")
    return os.path.join(base, "nightly-full-run")


def scrubbed_env(extra: dict | None = None) -> dict:
    """The pytest child's environment: the user's, minus anything credential-shaped and anything that
    would steer the run (ambient addopts, a pre-set database, a held-lock token)."""
    env = {}
    for k, v in os.environ.items():
        if k in DROP_ENV or SECRET_RX.search(k):
            continue
        env[k] = v
    env["PYTHONFAULTHANDLER"] = "1"      # same as the hub's CI: a C-level crash leaves a traceback
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"     # so a non-cp1252 character in the output cannot crash the writer
    # Deliberately NOT PYTHONUTF8: Windows-only encoding failures are exactly what this job exists to see.
    if extra:
        env.update(extra)
    return env


def pid_alive(pid: int) -> bool | None:
    """True, False, or None when it cannot be told. Not os.kill(pid, 0) on Windows: it does not raise
    for an exited process there (the same measurement heavy_lock.py records)."""
    if pid <= 0:
        return None
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes
            k = ctypes.windll.kernel32
            handle = k.OpenProcess(0x1000, False, pid)           # PROCESS_QUERY_LIMITED_INFORMATION
            if not handle:
                return False if k.GetLastError() == 87 else None  # 87 = invalid parameter = no such pid
            try:
                code = wintypes.DWORD()
                if not k.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return None
                return code.value == 259                           # STILL_ACTIVE
            finally:
                k.CloseHandle(handle)
        except Exception:  # noqa: BLE001
            return None
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return None
    return True


# ── the verdict (pure; no I/O) ────────────────────────────────────────────────────────────────

_COUNT_RX = re.compile(r"(\d+) (passed|failed|skipped|errors?|xfailed|xpassed|deselected|warnings?|rerun)\b")
# The whole final line, so a log line that merely contains "in 3s" can never pass for it. With -q pytest prints
# it bare ("6670 passed, 18 skipped in 2000.12s (0:33:20)"); without -q it is wrapped in "=" runs.
_SUMMARY_LINE_RX = re.compile(r"^(?:=+ )?(?:(?:\d+ [a-z]+(?:, )?)+|no tests ran) in \d+(?:\.\d+)?s(?: \(\d+:\d{2}:\d{2}\))?(?: =+)?$")
_SCOPE_RX = re.compile(r"^\s*scope:\s+(\d+) tests selected\s*$")
_BASE_RX = re.compile(r"^\s*base:\s+([0-9a-f]{7,40})\b(?:\s+\(\+(\d+) uncommitted)?")
_SHORT_SUMMARY_RX = re.compile(r"^=+ short test summary info =+\s*$")
_ID_RX = re.compile(r"^(FAILED|ERROR) (\S.*?)(?: - .*)?\s*$")


def parse_pytest_output(text: str) -> dict:
    """Facts read from the tail of a pytest -q run. Anything not seen is None; nothing is guessed."""
    lines = text.splitlines()
    out = {"summary_seen": False, "counts": {}, "collected": None, "base": None, "base_dirty": None,
           "ids": [], "ids_seen": False}
    summary_at = len(lines)
    for i in range(len(lines) - 1, -1, -1):
        ln = lines[i].strip()
        if not _SUMMARY_LINE_RX.match(ln):
            continue
        counts = {}
        for n, word in _COUNT_RX.findall(ln):
            word = {"error": "errors", "warning": "warnings"}.get(word, word)
            counts[word] = counts.get(word, 0) + int(n)
        if counts or ln.lstrip("= ").startswith("no tests ran"):
            out["summary_seen"] = True
            out["counts"] = counts
            summary_at = i
            break
    for ln in lines:
        m = _SCOPE_RX.match(ln)
        if m:
            out["collected"] = int(m.group(1))
        m = _BASE_RX.match(ln)
        if m:
            out["base"] = m.group(1)
            out["base_dirty"] = int(m.group(2)) if m.group(2) else 0
    start = None
    for i, ln in enumerate(lines[:summary_at]):
        if _SHORT_SUMMARY_RX.match(ln.strip()):
            start = i
    if start is not None:
        out["ids_seen"] = True
        seen = set()
        for ln in lines[start + 1:summary_at]:
            m = _ID_RX.match(ln.rstrip())
            if m:
                tid = m.group(2).strip()[:300]
                if tid not in seen:
                    seen.add(tid)
                    out["ids"].append(f"{m.group(1)} {tid}")
    return out


def classify(rc: int | None, text: str, *, timed_out: bool = False, expected_sha: str | None = None,
             min_collected: int = MIN_COLLECTED, prev_collected: int | None = None,
             cap_minutes: int = CAP_MINUTES) -> dict:
    """PASS only on proof. See the module docstring for the rules."""
    p = parse_pytest_output(text or "")
    c = p["counts"]
    res = {"status": "UNKNOWN", "reason": "", "collected": p["collected"], "passed": c.get("passed"),
           "failed": c.get("failed"), "skipped": c.get("skipped"), "errors": c.get("errors"),
           "xfail": c.get("xfailed"), "xpass": c.get("xpassed"), "ids": p["ids"], "notes": []}
    if p["summary_seen"]:
        for k in ("passed", "failed", "skipped", "errors", "xfail", "xpass"):
            if res[k] is None:
                res[k] = 0
    if timed_out:
        res["reason"] = f"exceeded the {cap_minutes} min wall cap; killed, no verdict"
        return res
    if rc is None:
        res["reason"] = "pytest did not report an exit code"
        return res
    if not p["summary_seen"]:
        res["reason"] = f"pytest ended rc={rc} without a final summary line (crash, kill or collection abort)"
        return res
    base_ok = None
    if expected_sha is not None:
        if p["base"] is None:
            base_ok = False
        else:
            base_ok = expected_sha.lower().startswith(p["base"].lower())
    if p["base_dirty"]:
        res["notes"].append(f"tree-dirty-after-run={p['base_dirty']}")
    failures = (res["failed"] or 0) + (res["errors"] or 0)

    if failures > 0:
        if rc not in (1, 2):
            res["reason"] = f"{failures} failure(s) reported but pytest exited rc={rc}"
            return res
        if p["base"] is not None and base_ok is False:
            res["reason"] = "failures seen, but the run's own base line names a different commit than the one we meant to test"
            return res
        if p["base"] is None:
            res["notes"].append("base-line-missing")
        res["status"] = "FAIL"
        res["reason"] = f"{res['failed']} failed, {res['errors']} errors"
        if p["collected"] is None:
            res["notes"].append("scope-line-missing")
        if not p["ids_seen"]:
            res["notes"].append("ids-unavailable-no-short-summary")
        elif not p["ids"]:
            res["notes"].append("no-ids-parsed")
        return res

    if rc != 0:
        res["reason"] = f"pytest exited rc={rc} with no failures counted"
        return res
    if base_ok is not True:
        res["reason"] = ("the run's own base line is missing" if p["base"] is None
                         else f"the run's base {p['base']} is not the commit we meant to test")
        return res
    if p["collected"] is None:
        res["reason"] = "the hub conftest's `scope: N tests selected` line is missing; cannot show the whole suite ran"
        return res
    if p["collected"] < min_collected:
        res["reason"] = f"only {p['collected']} tests were selected (floor {min_collected}); that is not the suite"
        return res
    ran = (res["passed"] or 0) + (res["skipped"] or 0) + (res["xfail"] or 0) + (res["xpass"] or 0)
    if ran != p["collected"]:
        res["reason"] = f"outcomes add up to {ran} but {p['collected']} were selected"
        return res
    if (res["passed"] or 0) < 1:
        res["reason"] = "nothing passed"
        return res
    res["status"] = "PASS"
    if prev_collected and p["collected"] < prev_collected * (100 - DROP_NOTE_PERCENT) / 100.0:
        res["notes"].append(f"collected-fell-{prev_collected}-to-{p['collected']}")
    return res


# Samples whose answer is known. If the classifier gets one wrong it is broken, and the night is UNKNOWN.
_SAMPLE_BASE = "abcdef123456"
_SAMPLE_PASS = ("....\n\n=== this run is a statement about ===\n  base:  abcdef1\n  scope: 1500 tests selected\n"
                "1490 passed, 8 skipped, 2 xfailed, 3 warnings in 12.00s (0:00:12)\n")
_SAMPLE_FAIL = ("..F\n=== this run is a statement about ===\n  base:  abcdef1\n  scope: 1500 tests selected\n"
                "=========================== short test summary info ============================\n"
                "FAILED tests/test_a.py::test_x - assert 1 == 2\nERROR tests/test_b.py::test_y\n"
                "1 failed, 1497 passed, 1 error in 9.00s\n")
_SAMPLE_CRASH = "....\nWindows fatal exception: access violation\n"
_SAMPLE_SHORT = ("  base:  abcdef1\n  scope: 3 tests selected\n3 passed in 0.10s\n")
_SAMPLE_OTHER_BASE = _SAMPLE_PASS.replace("abcdef1", "9999999")
_SAMPLE_SUM_WRONG = _SAMPLE_PASS.replace("1490 passed", "1400 passed")


def self_check() -> str | None:
    """None when the classifier gives the known answer on every sample, else a description of the miss."""
    cases = [
        ("pass sample", classify(0, _SAMPLE_PASS, expected_sha=_SAMPLE_BASE)["status"], "PASS"),
        ("fail sample", classify(1, _SAMPLE_FAIL, expected_sha=_SAMPLE_BASE)["status"], "FAIL"),
        ("crash sample", classify(3221225477, _SAMPLE_CRASH, expected_sha=_SAMPLE_BASE)["status"], "UNKNOWN"),
        ("too-short sample", classify(0, _SAMPLE_SHORT, expected_sha=_SAMPLE_BASE)["status"], "UNKNOWN"),
        ("wrong-base sample", classify(0, _SAMPLE_OTHER_BASE, expected_sha=_SAMPLE_BASE)["status"], "UNKNOWN"),
        ("sum-mismatch sample", classify(0, _SAMPLE_SUM_WRONG, expected_sha=_SAMPLE_BASE)["status"], "UNKNOWN"),
        ("timeout sample", classify(None, _SAMPLE_PASS, timed_out=True, expected_sha=_SAMPLE_BASE)["status"], "UNKNOWN"),
        ("exit-0-with-failures sample", classify(0, _SAMPLE_FAIL, expected_sha=_SAMPLE_BASE)["status"], "UNKNOWN"),
    ]
    bad = [f"{name}: got {got}, wanted {want}" for name, got, want in cases if got != want]
    return "; ".join(bad) if bad else None


def lock_refusal_kind(output: str) -> str:
    """'busy' or 'unknown' from heavy_lock.py's refusal text. Unknown is never read as busy or free."""
    low = (output or "").lower()
    if "hub ci is busy" in low:
        return "busy"
    if "every heavy slot is taken" in low:
        return "unknown" if re.search(r"slot-\d+: unknown", low) else "busy"
    return "unknown"


def one_line(text: str, limit: int = 220) -> str:
    s = re.sub(r"\s+", " ", str(text)).strip().replace('"', "'")
    return s if len(s) <= limit else s[:limit - 3] + "..."


def format_result(status: str, *, sha: str | None, res: dict | None, wall_s: float | None, wait_s: float | None,
                  py: str | None, pytest_version: str | None, reason: str = "", notes: list | None = None,
                  when: dt.datetime | None = None, host: str | None = None) -> str:
    """The one log line, then (FAIL) the failing ids. Always ends with a newline."""
    r = res or {}

    def f(key):
        v = r.get(key)
        return "-" if v is None else str(v)

    parts = [stamp(when), status, f"main={(sha or '-')[:12]}",
             f"collected={f('collected')}", f"passed={f('passed')}", f"failed={f('failed')}",
             f"skipped={f('skipped')}", f"errors={f('errors')}", f"xfail={f('xfail')}", f"xpass={f('xpass')}",
             f"wall={human_duration(wall_s)}", f"wait={human_duration(wait_s)}",
             f"py={py or '-'}", f"pytest={pytest_version or '-'}", f"host={host or socket.gethostname()}"]
    all_notes = list(notes or []) + list(r.get("notes") or [])
    if reason and status != "PASS":
        parts.append(f'reason="{one_line(reason)}"')
    if all_notes:
        parts.append(f'note="{one_line("; ".join(all_notes))}"')
    out = " ".join(parts) + "\n"
    ids = r.get("ids") or []
    if status == "FAIL" and ids:
        for tid in ids[:IDS_IN_LOG]:
            out += "  " + tid + "\n"
        if len(ids) > IDS_IN_LOG:
            out += f"  ... and {len(ids) - IDS_IN_LOG} more (full list in the night's raw output under the state dir)\n"
    return out


def previous_collected(log_text: str | None) -> int | None:
    """`collected=` of the last PASS or FAIL line in the log, for the fell-sharply note."""
    if not log_text:
        return None
    for ln in reversed(log_text.splitlines()):
        m = re.match(r"^\S+ (PASS|FAIL) .*?\bcollected=(\d+)\b", ln)
        if m:
            return int(m.group(2))
    return None


# ── the run (I/O) ─────────────────────────────────────────────────────────────────────────────

class Stop(Exception):
    """A step could not be established; the night ends UNKNOWN (or SKIPPED-BUSY) with this reason."""

    def __init__(self, status: str, reason: str):
        super().__init__(reason)
        self.status = status
        self.reason = reason


class Ctx:
    def __init__(self, args):
        self.args = args
        self.hub = args.hub
        self.wt = os.path.join(args.hub, WORKTREE_REL)
        self.state = args.state
        self.log = args.log
        self.t0 = time.monotonic()
        self.sha: str | None = None
        self.py_label: str | None = None
        self.pytest_version: str | None = None
        self.wait_s: float | None = None
        self.wall_s: float | None = None
        self.notes: list[str] = []
        self.mutex_path = os.path.join(args.state, "nightly.lock")
        self.have_mutex = False
        self.token: str | None = None
        self.helper: str | None = None

    def say(self, msg: str) -> None:
        line = f"{stamp()} {msg}"
        try:
            print(line, flush=True)
        except (OSError, ValueError):
            pass                                  # no usable console under the scheduler is not a reason to stop
        try:
            os.makedirs(self.state, exist_ok=True)
            path = os.path.join(self.state, "orchestrator.log")
            if os.path.isfile(path) and os.path.getsize(path) > 400_000:
                os.replace(path, path + ".1")
            with open(path, "a", encoding="utf-8") as fh:
                fh.write(line + "\n")
        except OSError:
            pass


def git(cwd: str, *args: str, timeout: int = 300, raw: bool = False):
    env = dict(os.environ)
    env["GIT_TERMINAL_PROMPT"] = "0"       # a missing credential must fail, never hang a headless task
    env["GCM_INTERACTIVE"] = "never"
    try:
        p = subprocess.run(["git", *args], cwd=cwd, env=env, capture_output=True, timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Stop("UNKNOWN", f"git {args[0]} could not run: {exc.__class__.__name__}") from exc
    err = p.stderr.decode("utf-8", errors="replace")
    if p.returncode != 0:
        raise Stop("UNKNOWN", f"git {args[0]} failed rc={p.returncode}: {one_line(err or p.stdout.decode('utf-8', errors='replace'), 160)}")
    return p.stdout if raw else p.stdout.decode("utf-8", errors="replace").strip()


def take_mutex(ctx: Ctx) -> None:
    os.makedirs(ctx.state, exist_ok=True)
    for _attempt in range(2):
        try:
            fd = os.open(ctx.mutex_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError:
            try:
                with open(ctx.mutex_path, encoding="utf-8") as fh:
                    held = json.load(fh)
                pid = int(held["pid"])
                age_h = (time.time() - float(held["time"])) / 3600.0
            except (OSError, ValueError, KeyError, TypeError):
                raise Stop("UNKNOWN", "another run's mutex file exists and cannot be read; not touching it") from None
            alive = pid_alive(pid)
            if alive is False or age_h > MUTEX_STALE_HOURS:
                try:
                    os.replace(ctx.mutex_path, ctx.mutex_path + ".stale")   # keep the record; never delete
                except OSError:
                    pass
                continue
            raise Stop("UNKNOWN", f"another nightly run is in progress (pid {pid}, {age_h:.1f} h); this one did nothing")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump({"pid": os.getpid(), "time": time.time(), "started": stamp(), "dry_run": bool(ctx.args.dry_run)}, fh)
        ctx.have_mutex = True
        return
    raise Stop("UNKNOWN", "could not take the run mutex")


def release_mutex(ctx: Ctx) -> None:
    if ctx.have_mutex:
        try:
            os.remove(ctx.mutex_path)
        except OSError:
            pass
        ctx.have_mutex = False


def fetch_main(ctx: Ctx) -> str:
    """The SHA of origin/main, fetched and confirmed against the remote's own answer."""
    if not os.path.isdir(os.path.join(ctx.hub, ".git")) and not os.path.isfile(os.path.join(ctx.hub, ".git")):
        raise Stop("UNKNOWN", f"hub repo not found at {ctx.hub}")
    for attempt in (1, 2):
        git(ctx.hub, "fetch", "--no-tags", "--quiet", "origin", "main", timeout=900)
        local = git(ctx.hub, "rev-parse", "--verify", "refs/remotes/origin/main^{commit}")
        remote = git(ctx.hub, "ls-remote", "origin", "refs/heads/main", timeout=120).split()
        if not remote or not re.fullmatch(r"[0-9a-f]{40}", remote[0]) or not re.fullmatch(r"[0-9a-f]{40}", local):
            raise Stop("UNKNOWN", "could not read origin/main from the remote; refusing to report on a guess")
        if local == remote[0]:
            return local
        ctx.say(f"origin/main moved during the fetch (attempt {attempt}); fetching again")
    raise Stop("UNKNOWN", "origin/main kept moving; could not pin one commit to test")


def extract_helper(ctx: Ctx, sha: str) -> str:
    """The hub's own heavy_lock.py at the tested commit, copied outside every worktree."""
    data = git(ctx.hub, "show", f"{sha}:scripts/heavy_lock.py", raw=True)
    if b"def acquire" not in data:
        raise Stop("UNKNOWN", "scripts/heavy_lock.py at that commit does not look like the lock helper")
    os.makedirs(ctx.state, exist_ok=True)
    path = os.path.join(ctx.state, "heavy_lock.py")
    with open(path, "wb") as fh:
        fh.write(data)
    return path


def helper_env(ctx: Ctx) -> dict:
    env = dict(os.environ)
    env.pop("HEAVY_LOCK_TOKEN", None)
    env.pop("GITHUB_ACTIONS", None)
    env["HEAVY_LOCK_DESK"] = DESK
    return env


def run_helper(ctx: Ctx, *args: str, timeout: int = 180) -> tuple[int, str]:
    try:
        p = subprocess.run([sys.executable, ctx.helper, *args], cwd=ctx.state, env=helper_env(ctx),
                           capture_output=True, encoding="utf-8", errors="replace", timeout=timeout)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 99, f"helper could not run: {exc.__class__.__name__}"
    return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()


def acquire_slot(ctx: Ctx, *, wait_minutes: float, poll_seconds: float, sleep=time.sleep, clock=time.monotonic) -> str:
    """Return the slot token, or raise Stop(SKIPPED-BUSY | UNKNOWN). Never returns without a token."""
    token_file = os.path.join(ctx.state, "slot.token")
    start = clock()
    deadline = start + wait_minutes * 60.0
    last_kind, last_msg = "unknown", "no attempt was made"
    attempts = 0
    while True:
        attempts += 1
        try:
            os.remove(token_file)
        except OSError:
            pass
        rc, out = run_helper(ctx, "acquire", "--job", JOB, "--pid", str(os.getpid()), "--token-file", token_file)
        token = ""
        try:
            with open(token_file, encoding="utf-8") as fh:
                token = fh.read().strip()
        except OSError:
            pass
        try:
            os.remove(token_file)
        except OSError:
            pass
        ctx.wait_s = clock() - start
        if rc == 0:
            if token:
                ctx.say(f"slot granted after {human_duration(ctx.wait_s)} ({attempts} attempt(s)): {one_line(out, 120)}")
                return token
            raise Stop("UNKNOWN", f"the lock helper exited 0 but took no slot ({one_line(out, 120)}); "
                                  "not running without the lock")
        if rc == 3:
            last_kind, last_msg = lock_refusal_kind(out), out
        else:
            raise Stop("UNKNOWN", f"the lock helper failed rc={rc}: {one_line(out, 160)}")
        if clock() + poll_seconds > deadline:
            break
        ctx.say(f"slot refused ({last_kind}); retrying in {int(poll_seconds)}s: {one_line(last_msg, 140)}")
        sleep(poll_seconds)
    if last_kind == "busy":
        raise Stop("SKIPPED-BUSY", f"waited {human_duration(ctx.wait_s)}: {one_line(last_msg, 170)}")
    raise Stop("UNKNOWN", f"the lock could not be established in {human_duration(ctx.wait_s)}: {one_line(last_msg, 170)}")


def release_slot(ctx: Ctx) -> None:
    if not ctx.token:
        return
    rc, out = run_helper(ctx, "release", "--token", ctx.token, timeout=60)
    if rc == 0 and "released" in out and "nothing held" not in out:
        ctx.say("slot released")
    else:
        ctx.notes.append("slot-release-FAILED")
        ctx.say(f"slot release did not confirm (rc={rc}): {one_line(out, 140)}")
    ctx.token = None


def prepare_worktree(ctx: Ctx, sha: str) -> None:
    """Make <hub>/.claude/worktrees/nightly-full-run a clean detached checkout of `sha`, or raise Stop.
    It only ever deletes inside a folder it has proved is that worktree."""
    hub, wt = ctx.hub, ctx.wt
    if os.path.lexists(wt) and not (os.path.isdir(wt) and not os.listdir(wt)):
        listed = []
        for ln in git(hub, "worktree", "list", "--porcelain").splitlines():
            if ln.startswith("worktree "):
                listed.append(norm(ln[len("worktree "):]))
        if norm(wt) not in listed:
            raise Stop("UNKNOWN", f"{wt} exists but git does not list it as a worktree of the hub; not touching it")
        top = git(wt, "rev-parse", "--show-toplevel")
        common = git(wt, "rev-parse", "--path-format=absolute", "--git-common-dir")
        if norm(top) != norm(wt) or norm(common) != norm(os.path.join(hub, ".git")):
            raise Stop("UNKNOWN", f"{wt} does not resolve to the hub's nightly worktree; not touching it")
        git(wt, "checkout", "--detach", "--force", "--quiet", sha)
        git(wt, "clean", "-fdxq")
    else:
        os.makedirs(os.path.dirname(wt), exist_ok=True)
        git(hub, "worktree", "add", "--detach", "--force", "--quiet", wt, sha)
    head = git(wt, "rev-parse", "HEAD")
    dirty = git(wt, "status", "--porcelain")
    if head != sha or dirty:
        raise Stop("UNKNOWN", f"worktree is not a clean checkout of {sha[:12]} (head {head[:12]}, "
                              f"{len(dirty.splitlines())} changed path(s))")


def resolve_python(ctx: Ctx) -> tuple[str, str]:
    """(interpreter, label). The hub's own .venv is what requirements.txt describes (gates.sh prefers it)."""
    if ctx.args.python:
        return ctx.args.python, "given"
    for rel in (os.path.join(".venv", "Scripts", "python.exe"), os.path.join(".venv", "bin", "python")):
        cand = os.path.join(ctx.hub, rel)
        if os.path.isfile(cand):
            return cand, "venv"
    return sys.executable, "system"


def preflight_python(ctx: Ctx) -> None:
    py, label = resolve_python(ctx)
    code = "import sys, pytest; print(sys.version.split()[0]); print(pytest.__version__)"
    try:
        p = subprocess.run([py, "-c", code], cwd=ctx.state, env=scrubbed_env(), capture_output=True,
                           encoding="utf-8", errors="replace", timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise Stop("UNKNOWN", f"interpreter {py} could not run: {exc.__class__.__name__}") from exc
    vals = (p.stdout or "").split()
    if p.returncode != 0 or len(vals) < 2:
        raise Stop("UNKNOWN", f"interpreter {py} does not import pytest: {one_line(p.stderr, 140)}")
    ctx.py_label = f"{vals[0]}-{label}"
    ctx.pytest_version = vals[1]


def kill_tree(proc: subprocess.Popen) -> None:
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"], capture_output=True, timeout=60)
        else:
            proc.kill()
    except Exception:  # noqa: BLE001
        pass
    try:
        proc.kill()
    except Exception:  # noqa: BLE001
        pass


def run_pytest(ctx: Ctx, out_path: str, cap_minutes: float) -> tuple[int | None, bool, float]:
    py, _label = resolve_python(ctx)
    cmd = [py, "-m", "pytest", "-q", "-p", "no:cacheprovider"]
    env = scrubbed_env({"HEAVY_LOCK_TOKEN": ctx.token or ""})
    flags = getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0
    t = time.monotonic()
    timed_out = False
    rc: int | None = None
    with open(out_path, "wb") as fh:
        proc = subprocess.Popen(cmd, cwd=ctx.wt, env=env, stdin=subprocess.DEVNULL, stdout=fh,
                                stderr=subprocess.STDOUT, creationflags=flags)
        try:
            rc = proc.wait(timeout=cap_minutes * 60.0)
        except subprocess.TimeoutExpired:
            timed_out = True
            kill_tree(proc)
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                pass
    return rc, timed_out, time.monotonic() - t


def read_tail(path: str, limit: int = TAIL_BYTES) -> str:
    with open(path, "rb") as fh:
        fh.seek(0, os.SEEK_END)
        size = fh.tell()
        fh.seek(max(0, size - limit))
        return fh.read().decode("utf-8", errors="replace")


def prune_runs(state: str) -> None:
    runs = os.path.join(state, "runs")
    try:
        names = sorted(d for d in os.listdir(runs) if os.path.isdir(os.path.join(runs, d)))
    except OSError:
        return
    for name in names[:-RUNS_KEPT]:
        d = os.path.join(runs, name)
        try:
            for f in os.listdir(d):
                os.remove(os.path.join(d, f))
            os.rmdir(d)
        except OSError:
            pass


def write_log(ctx: Ctx, text: str) -> None:
    try:
        os.makedirs(os.path.dirname(ctx.log), exist_ok=True)
        with open(ctx.log, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
        return
    except OSError as exc:
        ctx.say(f"could not write {ctx.log}: {exc.__class__.__name__}; writing the fallback log instead")
    try:
        with open(os.path.join(ctx.state, "nightly-full-run.fallback.log"), "a", encoding="utf-8", newline="\n") as fh:
            fh.write(text)
    except OSError:
        pass
    sys.stderr.write(text)


def previous_from_log(ctx: Ctx) -> int | None:
    try:
        with open(ctx.log, encoding="utf-8", errors="replace") as fh:
            return previous_collected(fh.read())
    except OSError:
        return None


def finish(ctx: Ctx, status: str, reason: str, res: dict | None = None) -> int:
    line = format_result(status, sha=ctx.sha, res=res, wall_s=ctx.wall_s, wait_s=ctx.wait_s, py=ctx.py_label, pytest_version=ctx.pytest_version, reason=reason,
                         notes=ctx.notes)
    if ctx.args.dry_run:
        ctx.say(f"DRY RUN would end as {status}; nothing was written to the log")
        sys.stdout.write(line)
        return EXIT.get(status, 2)
    write_log(ctx, line)
    ctx.say(f"{status}: {one_line(reason or 'ok', 160)}")
    return EXIT.get(status, 2)


def run(args) -> int:
    ctx = Ctx(args)
    try:
        try:
            bad = self_check()
            if bad:
                raise Stop("UNKNOWN", f"positive controls failed, the classifier cannot be trusted: {bad}")
            take_mutex(ctx)
            ctx.say(f"{'DRY RUN ' if args.dry_run else ''}start: hub={ctx.hub} worktree={ctx.wt}")
            ctx.sha = fetch_main(ctx)
            ctx.say(f"origin/main = {ctx.sha[:12]} (fetched, confirmed against ls-remote)")
            ctx.helper = extract_helper(ctx, ctx.sha)
            preflight_python(ctx)
            ctx.say(f"interpreter {ctx.py_label}, pytest {ctx.pytest_version}")

            if args.dry_run:
                rc, out = run_helper(ctx, "status")
                ctx.say("slot status (read-only):\n" + out)
                prepare_worktree(ctx, ctx.sha)
                ctx.say(f"worktree ready: clean, detached at {ctx.sha[:12]}")
                py, _label = resolve_python(ctx)
                ctx.say(f"DRY RUN stops here. Would take the slot (wait up to {args.wait_minutes} min), then run in "
                        f"{ctx.wt}: {py} -m pytest -q -p no:cacheprovider")
                return EXIT["PASS"]

            ctx.token = acquire_slot(ctx, wait_minutes=args.wait_minutes, poll_seconds=args.poll_seconds)
            prepare_worktree(ctx, ctx.sha)
            ctx.say(f"worktree ready: clean, detached at {ctx.sha[:12]}")
            run_dir = os.path.join(ctx.state, "runs", utc_now().strftime("%Y%m%dT%H%M%SZ"))
            os.makedirs(run_dir, exist_ok=True)
            out_path = os.path.join(run_dir, "pytest.out")
            ctx.say(f"pytest starts (cap {args.cap_minutes} min); raw output {out_path}")
            rc, timed_out, wall = run_pytest(ctx, out_path, args.cap_minutes)
            ctx.wall_s = wall
            ctx.say(f"pytest ended rc={rc} timed_out={timed_out} after {human_duration(wall)}")
            res = classify(rc, read_tail(out_path), timed_out=timed_out, expected_sha=ctx.sha,
                           min_collected=args.min_collected, prev_collected=previous_from_log(ctx),
                           cap_minutes=args.cap_minutes)
            if res["ids"] and len(res["ids"]) > IDS_IN_LOG:
                with open(os.path.join(run_dir, "failing-ids.txt"), "w", encoding="utf-8") as fh:
                    fh.write("\n".join(res["ids"]) + "\n")
            try:
                head_after = git(ctx.wt, "rev-parse", "HEAD")
                if head_after != ctx.sha:
                    ctx.notes.append("head-moved-during-run")
                    if res["status"] == "PASS":
                        res["status"], res["reason"] = "UNKNOWN", "the worktree HEAD changed during the run"
            except Stop:
                ctx.notes.append("head-unreadable-after-run")
            prune_runs(ctx.state)
            return finish_after_release(ctx, res["status"], res["reason"], res)
        except Stop as stop:
            return finish_after_release(ctx, stop.status, stop.reason, None)
        except KeyboardInterrupt:
            return finish_after_release(ctx, "UNKNOWN", "interrupted", None)
        except Exception as exc:  # noqa: BLE001 -- any bug is UNKNOWN, never a pass and never a silent exit
            ctx.say("internal error:\n" + traceback.format_exc())
            return finish_after_release(ctx, "UNKNOWN", f"internal error: {exc.__class__.__name__}", None)
    finally:
        release_slot(ctx)
        release_mutex(ctx)


def finish_after_release(ctx: Ctx, status: str, reason: str, res: dict | None) -> int:
    """Release the slot BEFORE the line is written, so the line can say if the release failed."""
    release_slot(ctx)
    return finish(ctx, status, reason, res)


def parse_args(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true",
                    help="fetch, prove the worktree, preflight the interpreter, read the slot status; stop before "
                         "pytest; take no slot and write no log line")
    ap.add_argument("--hub", default=DEFAULT_HUB)
    ap.add_argument("--log", default=DEFAULT_LOG)
    ap.add_argument("--state", default=None, help="scratch + raw output dir (default %%LOCALAPPDATA%%\\nightly-full-run)")
    ap.add_argument("--python", default=None, help="interpreter for pytest (default: the hub's .venv, else this one)")
    ap.add_argument("--wait-minutes", type=float, default=WAIT_MINUTES)
    ap.add_argument("--poll-seconds", type=float, default=POLL_SECONDS)
    ap.add_argument("--cap-minutes", type=float, default=CAP_MINUTES)
    ap.add_argument("--min-collected", type=int, default=MIN_COLLECTED)
    args = ap.parse_args(argv)
    args.state = args.state or default_state_dir()
    return args


def main(argv=None) -> int:
    args = parse_args(argv)
    try:
        return run(args)
    except BaseException:  # noqa: BLE001 -- the last net: a bug is UNKNOWN (exit 2), never a quiet success
        traceback.print_exc()
        return EXIT["UNKNOWN"]


if __name__ == "__main__":
    sys.exit(main())
