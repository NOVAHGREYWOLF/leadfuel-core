"""WATCH webchat-8: the provider-error alarm raises once, locally, and says UNKNOWN when it cannot see."""
import importlib.util
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "provider_error_alarm.py")
_spec = importlib.util.spec_from_file_location("provider_error_alarm", _PATH)
pea = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(pea)

NOW = 1_800_000_000.0


def ev(n_ok, n_fail, prov="anthropic", age=60, err="auth"):
    rows = [(NOW - age - i, prov, True, None) for i in range(n_ok)]
    rows += [(NOW - age - 100 - i, prov, False, err) for i in range(n_fail)]
    return rows


def test_forced_failure_is_alarm():
    v = pea.judge(ev(8, 12), 0, NOW)["anthropic"]
    assert v["verdict"] == "ALARM" and v["top_error"] == "auth"


def test_dead_key_all_failing_is_alarm():
    assert pea.judge(ev(0, 20), 0, NOW)["anthropic"]["verdict"] == "ALARM"


def test_ten_percent_exactly_is_ok():
    assert pea.judge(ev(18, 2), 0, NOW)["anthropic"]["verdict"] == "OK"


def test_few_calls_is_unknown_not_ok():
    assert pea.judge(ev(0, 2), 0, NOW)["anthropic"]["verdict"] == "UNKNOWN"
    assert pea.judge(ev(2, 0), 0, NOW)["anthropic"]["verdict"] == "UNKNOWN"


def test_calls_outside_window_are_not_seen():
    assert pea.judge(ev(0, 20, age=3 * 3600), 0, NOW) == {}


def test_unreadable_lines_degrade_ok_to_unknown_but_not_alarm():
    assert pea.judge(ev(20, 0), 1, NOW)["anthropic"]["verdict"] == "UNKNOWN"
    assert pea.judge(ev(0, 20), 1, NOW)["anthropic"]["verdict"] == "ALARM"


def test_alarm_raised_once_then_rearmed_after_ok(tmp_path):
    a, s = str(tmp_path / "alarms.jsonl"), str(tmp_path / "state.json")
    bad = pea.judge(ev(2, 18), 0, NOW)
    assert len(pea.raise_alarms(bad, NOW, a, s)) == 1
    assert pea.raise_alarms(bad, NOW + 60, a, s) == []          # still failing: no second row
    unk = pea.judge(ev(1, 1), 0, NOW)
    pea.raise_alarms(unk, NOW + 120, a, s)                      # UNKNOWN does not re-arm
    assert pea.raise_alarms(bad, NOW + 180, a, s) == []
    pea.raise_alarms(pea.judge(ev(20, 0), 0, NOW), NOW + 240, a, s)   # recovered
    assert len(pea.raise_alarms(bad, NOW + 300, a, s)) == 1     # fails again: raised again
    rows = [json.loads(x) for x in open(a, encoding="utf-8")]
    assert len(rows) == 2 and all(r["outward"] == "held-for-approval" for r in rows)


def test_cli_end_to_end_local_only(tmp_path, capsys):
    calls = tmp_path / "calls.jsonl"
    lines = [{"ts": NOW - 30 - i, "provider": "anthropic", "ok": i % 2 == 0, "error": "5xx"} for i in range(20)]
    calls.write_text("\n".join(json.dumps(x) for x in lines) + "\nnot json\n", encoding="utf-8")
    a, s = tmp_path / "alarms.jsonl", tmp_path / "state.json"
    args = ["--calls", str(calls), "--now", str(NOW), "--alarms", str(a), "--state", str(s)]
    assert pea.main(args) == 1
    assert pea.main(args) == 1
    assert len(a.read_text(encoding="utf-8").splitlines()) == 1
    assert "not sent anywhere" in capsys.readouterr().out


def test_cli_missing_log_or_empty_is_unknown(tmp_path):
    assert pea.main(["--calls", str(tmp_path / "none.jsonl"), "--alarms", str(tmp_path / "a")]) == 2
    empty = tmp_path / "e.jsonl"
    empty.write_text("", encoding="utf-8")
    assert pea.main(["--calls", str(empty), "--now", str(NOW), "--alarms", str(tmp_path / "a"),
                     "--state", str(tmp_path / "s")]) == 2
    assert not (tmp_path / "a").exists()


def test_module_has_no_network_imports():
    src = open(_PATH, encoding="utf-8").read()
    for bad in ("import socket", "urllib", "requests", "smtplib", "http.client", "subprocess"):
        assert bad not in src
