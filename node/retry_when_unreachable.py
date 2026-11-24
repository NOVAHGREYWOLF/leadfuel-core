"""NODE p16-3: run a backup job only when r710-backup is reachable; wait a bounded time if it is not,
and when it never comes back, write the status line the morning proof read understands.

Why. On 2026-11-21 vault-nightly (vzdump), vault-sync and greywolf-state-pull each ran at their cron
minute while the R710 was down, failed once and never tried again. The morning proof read could see
the failure only because the job wrote one. This wrapper makes a cron entry wait for the 710 and,
on giving up, raise a line instead of staying quiet.

OFF BY DEFAULT. Without `--enable` (or env R710_RETRY=1) the wrapper runs the command exactly once,
unchanged, and exits with its code: installing it in a cron line changes nothing until switched on.

Behaviour when enabled:
  1. Probe the 710 (TCP connect to host:port, default 10.20.0.51:2049, the NFS port; LAN only).
  2. Reachable: run the command ONCE. Its exit code is returned as it is. A job that runs and fails
     is not retried: a retry would mask a real failure and could run a disk job twice.
  3. Unreachable: sleep --wait seconds and probe again, up to --tries probes (default 6 x 600 s).
  4. Never reachable: do not run the command. Append one line to --status-file and exit 75.

The line, in the format watch/morning_proof.py parses (`<UTC stamp> <WORD> <text>`):
  vault-sync       UNKNOWN WHY: 710 unreachable after N probes over M min   (unknown, not fail: the
                   log cannot say the 710 is the fault, only that it could not be reached)
  greywolf-state   FAILED cannot reach the 710 after N probes over M min
  vault-nightly    FAILED storage r710-backup unreachable after N probes over M min  (a pre-flight for
                   the Proxmox job; the vzdump task itself is the job's own record)
A probe that cannot be made says UNKNOWN, never "reachable".

Usage (cron on overlord, once an owner switches it on):
    R710_RETRY=1 python3 retry_when_unreachable.py --job vault-sync --status-file /var/log/vault-sync.status -- /root/vault-sync.sh

Stdlib only. Nothing leaves the LAN; the only network act is the TCP connect.
"""
import argparse
import datetime as dt
import os
import socket
import subprocess
import sys
import time

DEFAULT_HOST = "10.20.0.51"
DEFAULT_PORT = 2049
EXIT_UNREACHABLE = 75   # EX_TEMPFAIL

LINES = {
    "vault-sync": "UNKNOWN WHY: 710 unreachable after {n} probes over {m} min",
    "greywolf-state": "FAILED cannot reach the 710 after {n} probes over {m} min",
    "vault-nightly": "FAILED storage r710-backup unreachable after {n} probes over {m} min",
}


def probe(host, port, timeout=5.0):
    """True only when a TCP connection was made. Any error is False (callers treat it as not reachable)."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def status_line(job, n, minutes, now=None):
    now = now or dt.datetime.now(dt.timezone.utc)
    stamp = now.strftime("%Y%m%dT%H%M%SZ")
    return "%s %s" % (stamp, LINES[job].format(n=n, m=minutes))


def run(job, command, status_file, host=DEFAULT_HOST, port=DEFAULT_PORT, tries=6, wait=600, enabled=False,
        probe_fn=probe, sleep_fn=time.sleep, run_fn=None, now_fn=None):
    run_fn = run_fn or (lambda cmd: subprocess.call(cmd))
    if not enabled:
        return run_fn(command)
    n = 0
    while n < tries:
        n += 1
        if probe_fn(host, port):
            return run_fn(command)
        if n < tries:
            sleep_fn(wait)
    line = status_line(job, n, (n - 1) * wait // 60, now_fn() if now_fn else None)
    with open(status_file, "a", encoding="utf-8") as fh:
        fh.write(line + "\n")
    return EXIT_UNREACHABLE


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--job", required=True, choices=sorted(LINES))
    ap.add_argument("--status-file", required=True)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--tries", type=int, default=6)
    ap.add_argument("--wait", type=int, default=600, help="seconds between probes")
    ap.add_argument("--enable", action="store_true", help="switch the retry on (or env R710_RETRY=1)")
    ap.add_argument("command", nargs=argparse.REMAINDER)
    a = ap.parse_args(argv)
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        ap.error("give the command after --")
    enabled = a.enable or os.environ.get("R710_RETRY") == "1"
    return run(a.job, cmd, a.status_file, a.host, a.port, max(1, a.tries), max(0, a.wait), enabled)


if __name__ == "__main__":
    sys.exit(main())
