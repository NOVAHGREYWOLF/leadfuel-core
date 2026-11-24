#!/usr/bin/env python3
"""NODE cluster files, the heavy-lock rules for part 2 (the file index and its hashing).

Owner: "no heavy full-disk hash on a machine in use during the day: one heavy job at a time
estate-wide (scripts/heavy_lock.py), nice/low priority". This module is that rule as code, so part 2
cannot hash a disk without it. It adds nothing to the lock itself: it uses node/cluster_route.py's
check/acquire/release of the hub's heavy_lock.py (`HEAVY_LOCK_PY`, owner ruling q205 A).

  * `scan_slot(job)` takes the estate heavy slot for ONE machine pass and releases it after, so the
    slot is free between machines and a CI job or another desk never waits for a whole-cluster scan.
    Held, stale or unreadable (`unknown`) refuses with the reason; it never proceeds "anyway".
  * `scan_allowed(machine, now)` says whether a heavy pass on that machine may start now: a machine in
    use by the owner (GREYWOLF, SURFACE, MSI: `scan.in_use` in the targets file) only outside working
    hours; a server any time. An unreadable policy is refused, not assumed fine.
  * `throttle_argv(machine)` is the prefix every remote hash or walk runs under: `nice -n 19` and
    `ionice -c3` on Linux, Idle priority on Windows. A scan without it is not started.
  * The pass list is one machine at a time, never in parallel, and `plan()` orders it.

Stdlib only; tests in tests/test_cluster_scan_slot.py.
"""
from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WORK_HOURS = (8, 22)          # local (Pacific) hours when an in-use machine is left alone
LINUX_THROTTLE = ["nice", "-n", "19", "ionice", "-c3"]
WINDOWS_THROTTLE = "(Get-Process -Id $PID).PriorityClass = 'Idle'; "


def _route():
    """cluster_route.py under a private module name: registering it as `cluster_route` would replace
    the module another importer already holds, and its dataclasses would stop matching."""
    name = "_cluster_route_for_scan_slot"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, "cluster_route.py"))
        mod = importlib.util.module_from_spec(spec)
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[name]

class SlotRefused(Exception):
    """The heavy slot was not granted. `.state` is held or unknown; neither means go."""

    def __init__(self, state: str, why: str):
        super().__init__(f"heavy slot {state}: {why}")
        self.state, self.why = state, why


@contextlib.contextmanager
def scan_slot(job: str, lock_py: str | None = None, run=None):
    """Hold the estate heavy slot for one machine pass."""
    cr = _route()
    kw = {} if run is None else {"run": run}
    path = lock_py if lock_py is not None else cr.DEFAULT_HEAVY_LOCK
    state, text = cr.heavy_lock_state(path, **kw)
    if state != "free":
        raise SlotRefused(state, text.splitlines()[0] if text else "no answer")
    token, msg = cr.acquire_heavy(job, path, **kw)
    if not token:
        raise SlotRefused("unknown" if not msg else "held", msg or "acquire gave no token")
    try:
        yield token
    finally:
        cr.release_heavy(token, path, **kw)


def scan_policy(machine: dict) -> dict:
    """The machine's `scan` block, or a refusal-shaped default (in use, so daytime is off limits)."""
    sc = machine.get("scan")
    if not isinstance(sc, dict) or not isinstance(sc.get("in_use"), bool):
        return {"in_use": True, "declared": False}
    return {"in_use": sc["in_use"], "declared": True}


def scan_allowed(machine: dict, now: dt.datetime) -> tuple[bool, str]:
    """`now` is local (Pacific) wall time. A machine with no declared policy counts as in use."""
    pol = scan_policy(machine)
    if not pol["in_use"]:
        return True, "server: any time, under the throttle"
    lo, hi = WORK_HOURS
    if lo <= now.hour < hi:
        why = "in use by the owner" if pol["declared"] else "no scan policy declared, treated as in use"
        return False, f"{why}: heavy passes only {hi}:00 to {lo}:00"
    return True, "in use by day; outside working hours"


def throttle_argv(machine: dict) -> list[str]:
    if machine.get("os") == "windows":
        raise ValueError("a Windows pass is a PowerShell script that starts with WINDOWS_THROTTLE")
    return list(LINUX_THROTTLE)


def plan(machines: list[dict], now: dt.datetime) -> list[dict]:
    """One pass per machine, in the order given, never parallel. A machine that cannot be reached
    (route none) or is not allowed now is listed with the reason, not dropped."""
    out = []
    for m in machines:
        ok, why = scan_allowed(m, now)
        if m.get("route", {}).get("kind") == "none":
            ok, why = False, "no route: unknown, not scanned"
        out.append({"machine": m["id"], "go": ok, "why": why})
    return out
