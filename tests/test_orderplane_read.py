"""ARMS fold-s-orderplane: the order-plane switch read kit is names and state words only, plan by
default, target mandatory, unknown never off, and it has no path out of the machine."""
import importlib.util
import io
import os
import subprocess
import sys
from contextlib import redirect_stdout

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "scripts", "orderplane_read",
                     "orderplane_read.py")
_spec = importlib.util.spec_from_file_location("orderplane_read", _PATH)
op = importlib.util.module_from_spec(_spec)
sys.modules["orderplane_read"] = op
_spec.loader.exec_module(op)

SECRET = "sk-live-SHOULD-NEVER-APPEAR-123"


def test_classify_bool_never_echoes_the_value():
    assert op.classify_bool(None) == "unset"
    assert op.classify_bool("  ") == "unset"
    assert op.classify_bool("1") == "on" and op.classify_bool("TRUE") == "on"
    assert op.classify_bool("0") == "off" and op.classify_bool("No") == "off"
    assert op.classify_bool(SECRET) == "other"


def test_probe_program_prints_only_state_words(monkeypatch):
    rows = [r for r in op.switch_rows() if r["service"] == "echo"]
    monkeypatch.setenv("SPOKE_WORKER_ENABLED", "yes")
    monkeypatch.setenv("SERVICE_TOKEN_ECHO", SECRET)
    monkeypatch.setenv("LEADFUEL_SERVICE_TOKEN", "")
    prog = op.probe_program(rows)
    buf = io.StringIO()
    with redirect_stdout(buf):
        exec(compile(prog, "probe", "exec"), {})
    out = buf.getvalue()
    assert SECRET not in out
    got = op.parse_answer(out)
    assert got == {"SPOKE_WORKER_ENABLED": "on", "SERVICE_TOKEN_ECHO": "present",
                   "LEADFUEL_SERVICE_TOKEN": "absent"}


def test_probe_program_reads_only_allowlisted_names():
    for svc in op.SERVICES:
        names = [r["name"] for r in op.switch_rows() if r["service"] == svc]
        prog = op.probe_program([r for r in op.switch_rows() if r["service"] == svc])
        assert "os.environ.get(name)" in prog and "os.environ[" not in prog
        assert "environ.items" not in prog and "print(raw" not in prog
        assert names  # every service has rows


def test_parse_answer_rejects_anything_unusable():
    assert op.parse_answer("") is None
    assert op.parse_answer("ORDERPLANE_STATES not json") is None
    assert op.parse_answer('ORDERPLANE_STATES {"A": "sk-123"}') is None  # a value, not a state


def test_unknown_is_never_reported_as_off():
    text, verdict = op.render_report("railway", "run", {s: None for s in op.SERVICES}, "t")
    assert verdict == "INCOMPLETE"
    assert " off" not in text and "unknown" in text


def test_arm_verdict_needs_switch_and_token_and_is_unknown_when_unread():
    full = {"SPOKE_WORKER_ENABLED": "on", "SERVICE_TOKEN_ORBIT": "absent",
            "LEADFUEL_SERVICE_TOKEN": "present"}
    assert op.arm_verdict(full, "orbit") == "RUNS"
    assert op.arm_verdict(dict(full, SPOKE_WORKER_ENABLED="off"), "orbit") == "dormant"
    assert op.arm_verdict(dict(full, LEADFUEL_SERVICE_TOKEN="absent"), "orbit") == "dormant"
    assert op.arm_verdict({}, "orbit") == "unknown"


def test_complete_report_when_every_service_answers():
    answers = {}
    for svc in op.SERVICES:
        answers[svc] = {r["name"]: ("present" if r["kind"] == "presence" else "off")
                        for r in op.switch_rows() if r["service"] == svc}
    text, verdict = op.render_report("local-vm106", "run", answers, "t", "desk chat")
    assert verdict == "COMPLETE" and text.startswith("TARGET: local-vm106")


def test_cli_target_is_mandatory_and_plan_run_conflict(capsys):
    assert op.main([]) == 2
    assert op.main(["--target", "railway", "--plan", "--run"]) == 2


def test_run_is_refused_without_the_typed_yes_and_nothing_connects():
    calls = []
    rc = op.main(["--target", "railway", "--run"], runner=lambda *a, **k: calls.append(a))
    assert rc == 2 and calls == []


def test_default_is_plan_and_connects_to_nothing(capsys):
    calls = []
    rc = op.main(["--target", "railway"], runner=lambda *a, **k: calls.append(a))
    out = capsys.readouterr().out
    assert rc == 0 and calls == []
    assert out.startswith("TARGET: railway") and "VERDICT: PLAN ONLY" in out


def test_run_with_injected_runner_parses_and_clears_railway_token(monkeypatch):
    monkeypatch.setenv("RAILWAY_API_TOKEN", "x")
    seen = []

    def fake(argv, input, capture_output, text, cwd, env, timeout):
        seen.append(env.get("RAILWAY_API_TOKEN"))
        names = [r for r in op.switch_rows() if r["name"] in input]
        ans = {r["name"]: ("present" if r["kind"] == "presence" else "on") for r in names}
        import json
        return subprocess.CompletedProcess(argv, 0, "ORDERPLANE_STATES " + json.dumps(ans), "")

    answers = op.run_target("railway", runner=fake)
    assert set(seen) == {None}
    assert all(v is not None for v in answers.values())


def test_unreachable_service_is_unknown():
    def boom(*a, **k):
        raise OSError("no route")
    answers = op.run_target("railway", runner=boom)
    assert all(v is None for v in answers.values())


def test_module_has_no_network_client_and_no_cloud_path():
    src = open(_PATH, encoding="utf-8").read()
    for bad in ("import requests", "import urllib", "import http", "import socket",
                "anthropic", "openai", "boto3"):
        assert bad not in src, bad


def test_arm_names_are_the_ratified_ones():
    assert set(op.ARM_KEYS) >= {"orbit", "signal", "reach", "scope", "odyssey"}
    for retired in ("novahawk", "novahound", "novaherald", "smarticp", "icp"):
        assert retired not in op.ARM_KEYS
