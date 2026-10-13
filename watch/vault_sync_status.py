"""WATCH: read the nightly VAULT private-sync log and say ok, failed or unknown.

The sync (VAULT's `vault_private_sync.py`, Windows task `VAULT private sync`, 04:30 Pacific)
appends to %LOCALAPPDATA%\\vault-private-sync\\sync.log. Each run is bracketed by

    === vault_private_sync start <UTC>
    [<target>] pushed N ref(s) [...]; remote has M branch(es); ls-remote verified
    === vault_private_sync end <UTC> exit=<code>

Rules (a check that cannot establish a state must not report one):
  * ok      only when the LAST run finished with exit=0, is fresh, and logged a verified push for
            every expected target. A dry run also exits 0 but pushes nothing, so exit=0 alone is
            not enough.
  * failed  the last run ended with a non-zero exit, or started and never finished within the
            task's 2 h limit (killed or crashed).
  * unknown everything else: no log, empty or unreadable log, no run in it, a run still in
            progress, a run older than STALE_AFTER_HOURS, exit=0 without the push evidence, or
            the positive controls below did not come out as expected.

Positive controls: every invocation first classifies built-in samples whose answers are known
(ok, failed, missing, stale). If any comes out wrong the reader is broken and the result is
`unknown`, so a reader that always says "ok" cannot pass.

Stdlib only; run by path:  python watch/vault_sync_status.py [--log PATH] [--write [PATH]]
"""
import argparse
import datetime as dt
import json
import os
import re
import sys

SCHEMA = "watch.vault_sync_status/1"
EXPECTED_TARGETS = ("claude-sessions", "leadfuel-estate")  # TARGETS in vault_private_sync.py
STALE_AFTER_HOURS = 27.0   # daily run + 2 h task limit + 1 h slack
RUN_LIMIT_HOURS = 2.0      # the scheduled task's execution limit
STATUS_FILE_MAX_AGE_HOURS = 26.0

START_RX = re.compile(r"^=== vault_private_sync start (\S+)\s*$")
END_RX = re.compile(r"^=== vault_private_sync end (\S+) exit=(-?\d+)\s*$")
PUSHED_RX = re.compile(r"^\[([\w.\-]+)\] pushed \d+ ref\(s\) .*ls-remote verified\s*$")

EXIT_MEANING = {
    1: "a git/gh command failed or ls-remote disagreed",
    2: "scan found unreviewed findings; nothing pushed",
    3: "an excluded path or a big blob survived the filter; nothing pushed",
    4: "remote not reported PRIVATE; nothing pushed",
    5: "a branch was not a fast-forward and was skipped",
}


def default_log_path():
    base = os.environ.get("LOCALAPPDATA")
    return os.path.join(base, "vault-private-sync", "sync.log") if base else None


def _utc(s):
    return dt.datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)


def _iso(t):
    return t.strftime("%Y-%m-%dT%H:%M:%SZ") if t else None


def decode_log(raw):
    """cmd's `>>` writes the console bytes; tolerate UTF-16 (a PowerShell redirect) and junk."""
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16", "replace")
    return raw.decode("utf-8-sig", "replace")


def parse_runs(text):
    """Split the log into runs: [{"start", "end", "exit", "verified": set()}], oldest first."""
    runs = []
    for line in text.splitlines():
        line = line.strip()
        m = START_RX.match(line)
        if m:
            try:
                runs.append({"start": _utc(m.group(1)), "end": None, "exit": None, "verified": set()})
            except ValueError:
                pass
            continue
        if not runs:
            continue
        cur = runs[-1]
        m = END_RX.match(line)
        if m and cur["end"] is None:
            try:
                cur["end"], cur["exit"] = _utc(m.group(1)), int(m.group(2))
            except ValueError:
                pass
            continue
        m = PUSHED_RX.match(line)
        if m and cur["end"] is None:
            cur["verified"].add(m.group(1))
    return runs


def classify(text, now, targets=EXPECTED_TARGETS, stale_after=STALE_AFTER_HOURS):
    """Pure verdict over the log text (None = no log). Returns a dict without controls."""
    out = {"state": "unknown", "reason": "", "last_start": None, "last_end": None,
           "exit_code": None, "age_hours": None, "targets_verified": [], "runs_seen": 0}
    if text is None:
        out["reason"] = "no log file: the sync has not run, or logs elsewhere"
        return out
    runs = parse_runs(text)
    out["runs_seen"] = len(runs)
    if not runs:
        out["reason"] = "log holds no sync run"
        return out
    run = runs[-1]
    age = (now - run["start"]).total_seconds() / 3600
    out.update(last_start=_iso(run["start"]), last_end=_iso(run["end"]), exit_code=run["exit"],
               age_hours=round(age, 2), targets_verified=sorted(run["verified"]))
    if age < -0.1:
        out["reason"] = "last run starts in the future: clock or log is wrong"
        return out
    if run["end"] is None:
        if age > RUN_LIMIT_HOURS:
            out["state"] = "failed"
            out["reason"] = f"last run started {age:.1f} h ago and never finished (killed or crashed)"
        else:
            out["reason"] = "a run is in progress"
        return out
    if run["exit"] != 0:
        out["state"] = "failed"
        out["reason"] = f"exit {run['exit']}: {EXIT_MEANING.get(run['exit'], 'unrecognised exit code')}"
        return out
    if age > stale_after:
        out["reason"] = f"last clean run is {age:.1f} h old (stale after {stale_after:g} h)"
        return out
    missing = [t for t in targets if t not in run["verified"]]
    if missing:
        out["reason"] = f"exit 0 but no verified push for {missing} (a dry run, or the log format changed)"
        return out
    out["state"] = "ok"
    out["reason"] = f"pushed and verified {len(targets)} target(s) {age:.1f} h ago"
    return out


def _sample(start, exit_code, pushed=EXPECTED_TARGETS):
    s, e = _iso(start), _iso(start + dt.timedelta(minutes=12))
    body = "".join(f"[{t}] pushed 1 ref(s) ['refs/heads/main']; remote has 3 branch(es); ls-remote verified\n"
                   for t in pushed)
    return f"=== vault_private_sync start {s}\n{body}=== vault_private_sync end {e} exit={exit_code}\n"


def run_controls(now):
    """Known samples with known answers, classified by the same code as the real log."""
    cases = [
        ("ok", _sample(now - dt.timedelta(hours=3), 0), "ok"),
        ("failed", _sample(now - dt.timedelta(hours=3), 2, pushed=()), "failed"),
        ("missing", None, "unknown"),
        ("stale", _sample(now - dt.timedelta(hours=STALE_AFTER_HOURS + 5), 0), "unknown"),
    ]
    got = {name: classify(text, now)["state"] for name, text, _ in cases}
    bad = [name for name, _, want in cases if got[name] != want]
    return not bad, bad


def read_status(log_path=None, now=None):
    """Classify the log at log_path (default: the task's log) and attach the controls."""
    now = now or dt.datetime.now(dt.timezone.utc)
    log_path = log_path or default_log_path()
    text, err = None, None
    if log_path and os.path.isfile(log_path):
        try:
            with open(log_path, "rb") as f:
                text = decode_log(f.read())
        except OSError as e:
            err = f"log unreadable: {e.__class__.__name__}"
    out = classify(text, now)
    if err:
        out.update(state="unknown", reason=err)
    controls_ok, bad = run_controls(now)
    if not controls_ok:
        out.update(state="unknown", reason=f"reader positive controls failed: {bad}")
    return {"schema": SCHEMA, **out, "checked_at": _iso(now), "log_path": log_path,
            "log_present": text is not None, "controls_ok": controls_ok}


def read_status_file(path, now=None, max_age=STATUS_FILE_MAX_AGE_HOURS):
    """For readers of a saved status.json: a missing, foreign or old file is unknown, never ok."""
    now = now or dt.datetime.now(dt.timezone.utc)
    base = {"schema": SCHEMA, "state": "unknown", "checked_at": None}
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, dict):
            raise ValueError("not an object")
    except (OSError, ValueError) as e:
        return {**base, "reason": f"status file unreadable: {e.__class__.__name__}"}
    if data.get("schema") != SCHEMA or data.get("state") not in ("ok", "failed", "unknown"):
        return {**base, "reason": "status file has an unrecognised schema"}
    try:
        age = (now - _utc(data.get("checked_at") or "")).total_seconds() / 3600
    except ValueError:
        return {**data, "state": "unknown", "reason": "status file has no checked_at"}
    if age > max_age or age < -0.1:
        return {**data, "state": "unknown",
                "reason": f"status file checked {age:.1f} h ago; was {data['state']}: {data.get('reason', '')}"}
    return data


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--log", help="sync log (default: %%LOCALAPPDATA%%\\vault-private-sync\\sync.log)")
    ap.add_argument("--write", nargs="?", const="", metavar="PATH",
                    help="also save the JSON (default: status.json beside the log)")
    args = ap.parse_args(argv)
    status = read_status(args.log)
    if args.write is not None:
        path = args.write or (os.path.join(os.path.dirname(status["log_path"]), "status.json")
                              if status["log_path"] else None)
        if not path:
            print("no path to write status to", file=sys.stderr)
            return 2
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(status, f, indent=1)
        os.replace(tmp, path)
    print(json.dumps(status, indent=1))
    return {"ok": 0, "failed": 1}.get(status["state"], 3)


if __name__ == "__main__":
    sys.exit(main())
