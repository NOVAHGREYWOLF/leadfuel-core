#!/usr/bin/env python3
"""ARMS fold-s-orderplane: a names-and-on/off-only read kit for the order-plane switches.

What it reads: for the hub, each arm and the connector, whether a fixed list of switches is
`on`, `off`, `unset` or `other`, and whether a service token is `present` or `absent`. It never
prints, stores or hashes a value. The list of names is below and nothing outside it is read.

The switches (verified in code on 2026-11-24, not in production):
  * each arm, `SPOKE_WORKER_ENABLED`: the order-plane pull loop stays dormant until it is on AND a
    token exists (`spoke_worker.enabled()` = switch and token). Token names are
    `SERVICE_TOKEN_<APP_KEY>` or the shared `LEADFUEL_SERVICE_TOKEN`; only present/absent is read.
  * the hub, `RUNNER_ENABLED` and `RUNNER_REQUIRE_APPROVAL`, and the contract gates
    `SPOKE_ENFORCE_CONFORMANCE` and `SPOKE_ENFORCE_LIVENESS` (permissive while unset).
  * the connector (novahub-mcp), `RUNNER_ENABLED`: the tool surface, mirrors the hub's.

Rules, all refusals:
  * `--target` is mandatory (`railway` or `local-vm106`), no default, first line of the report.
  * Dry by default. Without `--run` it prints the plan and the exact program, and connects to
    nothing. `--plan` and `--run` together are refused.
  * `--run` is refused unless `--typed-yes-ref` names where the owner typed the yes in the ARMS
    "land the backlog" desk chat. That is a production read on `railway`. This kit ships `--plan`
    as the thing to use until then; nothing in the tests ever runs `--run`.
  * The program piped to the target reads only the allowlist, by name, from the process
    environment. It has no network, file or database access and prints only state words.
  * A service that cannot be reached, or answers with anything unusable, is `unknown`, never
    `off`. The report says COMPLETE only when every switch has a state word.
  * No cloud path, no http client, no secret. Stdlib only (Law 9).

Usage:
    orderplane_read.py --target railway --plan
    orderplane_read.py --target local-vm106 --plan --out-dir DIR
    orderplane_read.py --target railway --run --typed-yes-ref "ARMS land the backlog part 1, <time>"
    orderplane_read.py --target railway --plan --render FILE   (re-render a saved answer; no connect)
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import subprocess
import sys

TARGETS = ("railway", "local-vm106")
STATES = ("on", "off", "unset", "other")
PRESENCE = ("present", "absent")
_TRUE = ("1", "true", "yes", "on")
_FALSE = ("0", "false", "no", "off")
_NAME_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")

# The arms by their ratified names. The railway service names other than the hub are NOT
# verified: confirm each with `railway status` (names only) before the first run. A wrong
# service name makes that row `unknown`, never `off`.
ARM_KEYS = ("orbit", "signal", "reach", "scope", "odyssey", "echo", "lucid")

SERVICES = {
    "hub": {"railway": "NovaHub", "vm106": "hub", "python": "/opt/venv/bin/python",
            "verified_service": True},
    "connector": {"railway": "novahub-mcp", "vm106": "mcp", "python": "python",
                  "verified_service": False},
}
for _a in ARM_KEYS:
    SERVICES[_a] = {"railway": _a, "vm106": _a, "python": "python", "verified_service": False}


def switch_rows() -> list[dict]:
    """The full allowlist: one row per (service, name, kind). kind is `bool` or `presence`."""
    rows = []
    for name in ("RUNNER_ENABLED", "RUNNER_REQUIRE_APPROVAL",
                 "SPOKE_ENFORCE_CONFORMANCE", "SPOKE_ENFORCE_LIVENESS"):
        rows.append({"service": "hub", "name": name, "kind": "bool"})
    rows.append({"service": "connector", "name": "RUNNER_ENABLED", "kind": "bool"})
    for arm in ARM_KEYS:
        rows.append({"service": arm, "name": "SPOKE_WORKER_ENABLED", "kind": "bool"})
        rows.append({"service": arm, "name": "SERVICE_TOKEN_" + arm.upper(), "kind": "presence"})
        rows.append({"service": arm, "name": "LEADFUEL_SERVICE_TOKEN", "kind": "presence"})
    for r in rows:
        assert _NAME_RE.match(r["name"]), r
    return rows


def classify_bool(raw) -> str:
    """Map a raw value to a state word. Never returns the raw text."""
    if raw is None:
        return "unset"
    s = str(raw).strip().lower()
    if not s:
        return "unset"
    if s in _TRUE:
        return "on"
    if s in _FALSE:
        return "off"
    return "other"


def classify_presence(raw) -> str:
    return "present" if raw is not None and str(raw).strip() else "absent"


# The program piped on stdin to the service's python. It is written so the only thing it can
# print is a state word: there is no code path from a value to the output.
PROBE_PROGRAM = '''\
import json, os
ROWS = json.loads(%(rows)r)
TRUE = ("1", "true", "yes", "on")
FALSE = ("0", "false", "no", "off")
out = {}
for name, kind in ROWS:
    raw = os.environ.get(name)
    if kind == "presence":
        out[name] = "present" if raw is not None and raw.strip() else "absent"
    elif raw is None or not raw.strip():
        out[name] = "unset"
    elif raw.strip().lower() in TRUE:
        out[name] = "on"
    elif raw.strip().lower() in FALSE:
        out[name] = "off"
    else:
        out[name] = "other"
print("ORDERPLANE_STATES " + json.dumps(out, sort_keys=True))
'''


def probe_program(rows_for_service: list[dict]) -> str:
    pairs = [[r["name"], r["kind"]] for r in rows_for_service]
    return PROBE_PROGRAM % {"rows": json.dumps(pairs)}


def command_for(target: str, service: str) -> str:
    s = SERVICES[service]
    if target == "railway":
        return ("cd F:\\Leadfuel\\repos\\novahub ; (program on stdin) | railway ssh --service "
                f"{s['railway']} -- {s['python']} -   (RAILWAY_API_TOKEN cleared for this process only)")
    return ("(program on stdin) | ssh -J overlord -i $env:USERPROFILE\\.ssh\\id_ed25519_overlord "
            "novah@10.20.0.120 'cd /opt/novahos/rehearsal && sudo -n docker compose exec -T "
            f"{s['vm106']} {s['python']} -'")


def argv_for(target: str, service: str) -> tuple[list[str], str | None]:
    s = SERVICES[service]
    if target == "railway":
        return (["railway", "ssh", "--service", s["railway"], "--", s["python"], "-"],
                "F:\\Leadfuel\\repos\\novahub")
    key = os.path.join(os.path.expanduser("~"), ".ssh", "id_ed25519_overlord")
    return (["ssh", "-J", "overlord", "-i", key, "novah@10.20.0.120",
             f"cd /opt/novahos/rehearsal && sudo -n docker compose exec -T {s['vm106']} {s['python']} -"],
            None)


def parse_answer(text: str) -> dict | None:
    """Parse one service's output. Anything unusable is None (unknown), never a guess."""
    for line in (text or "").splitlines():
        if line.startswith("ORDERPLANE_STATES "):
            try:
                data = json.loads(line[len("ORDERPLANE_STATES "):])
            except ValueError:
                return None
            if isinstance(data, dict) and all(
                    isinstance(v, str) and v in STATES + PRESENCE for v in data.values()):
                return data
    return None


def arm_verdict(states: dict, arm: str) -> str:
    """Would this arm's pull loop run? Needs the switch on AND a token present. Unknown if unread."""
    sw = states.get("SPOKE_WORKER_ENABLED")
    toks = [states.get("SERVICE_TOKEN_" + arm.upper()), states.get("LEADFUEL_SERVICE_TOKEN")]
    if sw is None or any(t is None for t in toks):
        return "unknown"
    return "RUNS" if sw == "on" and "present" in toks else "dormant"


def render_report(target: str, mode: str, answers: dict, stamp: str, ref: str = "") -> tuple[str, str]:
    """answers: service -> parsed dict or None. Returns (report text, verdict)."""
    rows = switch_rows()
    lines = [f"TARGET: {target}", f"MODE: {mode}   UTC: {stamp}"]
    if ref:
        lines.append(f"typed-yes-ref: {ref}")
    lines.append("Names and state words only. No value was read into this report.")
    lines.append("")
    complete = True
    for svc in SERVICES:
        svc_rows = [r for r in rows if r["service"] == svc]
        ans = answers.get(svc)
        flag = "" if SERVICES[svc]["verified_service"] else "  (service name unverified)"
        lines.append(f"[{svc}]{flag}" + ("  UNREAD: unknown" if ans is None else ""))
        for r in svc_rows:
            st = "unknown" if ans is None else ans.get(r["name"], "unknown")
            if st == "unknown":
                complete = False
            lines.append(f"  {r['name']:<28} {st}")
        if svc in ARM_KEYS:
            lines.append(f"  order-plane pull loop       {arm_verdict(ans or {}, svc)}")
    verdict = "COMPLETE" if complete and mode == "run" else (
        "PLAN ONLY" if mode == "plan" else "INCOMPLETE")
    lines += ["", f"VERDICT: {verdict}"]
    return "\n".join(lines) + "\n", verdict


def render_plan(target: str, stamp: str) -> str:
    rows = switch_rows()
    out = [f"TARGET: {target}", f"MODE: plan   UTC: {stamp}",
           "Nothing connects in plan mode. Names read, per service:", ""]
    for svc in SERVICES:
        names = [r["name"] for r in rows if r["service"] == svc]
        out.append(f"[{svc}] {', '.join(names)}")
        out.append("  " + command_for(target, svc))
    out += ["", "Program piped on stdin (hub shown; each service gets only its own names):", "",
            probe_program([r for r in rows if r["service"] == "hub"]), "VERDICT: PLAN ONLY"]
    return "\n".join(out) + "\n"


def run_target(target: str, runner=subprocess.run, timeout: int = 60) -> dict:
    """Connect to each service and parse its answer. `runner` is injected by tests."""
    rows = switch_rows()
    answers = {}
    env = dict(os.environ)
    env.pop("RAILWAY_API_TOKEN", None)
    for svc in SERVICES:
        argv, cwd = argv_for(target, svc)
        prog = probe_program([r for r in rows if r["service"] == svc])
        try:
            cp = runner(argv, input=prog, capture_output=True, text=True, cwd=cwd, env=env,
                        timeout=timeout)
            answers[svc] = parse_answer(cp.stdout) if cp.returncode == 0 else None
        except Exception:  # noqa: BLE001  unreachable is unknown, never off
            answers[svc] = None
    return answers


def main(argv=None, runner=subprocess.run) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--target", choices=TARGETS)
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--typed-yes-ref", default="")
    ap.add_argument("--out-dir", default="")
    a = ap.parse_args(argv)
    if not a.target:
        print("REFUSED: --target is mandatory (railway or local-vm106), no default. "
              "Nothing was built, nothing was sent.", file=sys.stderr)
        return 2
    if a.plan and a.run:
        print("REFUSED: --plan and --run together.", file=sys.stderr)
        return 2
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    if a.run:
        if not a.typed_yes_ref.strip():
            print("REFUSED: --run needs --typed-yes-ref naming where the owner typed the yes "
                  "(ARMS land the backlog desk chat). Plan mode connected to nothing.",
                  file=sys.stderr)
            return 2
        text, verdict = render_report(a.target, "run", run_target(a.target, runner), stamp,
                                      a.typed_yes_ref.strip())
        kind = "run"
    else:
        text, verdict, kind = render_plan(a.target, stamp), "PLAN ONLY", "plan"
    print(text)
    if a.out_dir:
        os.makedirs(a.out_dir, exist_ok=True)
        with open(os.path.join(a.out_dir, f"report_{a.target}_{kind}_{stamp}.txt"), "w",
                  encoding="utf-8") as f:
            f.write(text)
    return 0 if verdict in ("COMPLETE", "PLAN ONLY") else 1


if __name__ == "__main__":
    sys.exit(main())
