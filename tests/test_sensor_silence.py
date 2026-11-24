"""WATCH: silence must read stale or unknown, never ok; the owner is told once per outage."""
import importlib.util
import json
import os
from datetime import datetime, timedelta, timezone

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "sensor_silence.py")
_spec = importlib.util.spec_from_file_location("sensor_silence", _PATH)
ss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ss)

NOW = datetime(2026, 11, 22, 12, 0, tzinfo=timezone.utc)
FEEDS = {"location": {"max_quiet_minutes": 60}}


def ago(minutes):
    return (NOW - timedelta(minutes=minutes)).isoformat()


def test_fresh_is_ok_and_old_is_stale():
    assert ss.evaluate(FEEDS, {"location": ago(10)}, NOW)["location"]["verdict"] == "ok"
    assert ss.evaluate(FEEDS, {"location": ago(23 * 60)}, NOW)["location"]["verdict"] == "stale"


def test_no_evidence_is_unknown_never_ok():
    for seen in ({}, None, {"location": None}, {"location": "garbage"}, {"location": 5},
                 {"location": "2026-11-22T11:50:00"}, {"location": ago(-600)}):
        assert ss.evaluate(FEEDS, seen, NOW)["location"]["verdict"] == "unknown", seen


def test_bad_limit_is_unknown():
    for bad in (None, 0, -5, True, "60"):
        r = ss.evaluate({"location": {"max_quiet_minutes": bad}}, {"location": ago(1)}, NOW)
        assert r["location"]["verdict"] == "unknown"


def test_default_covers_location():
    assert "location" in ss.DEFAULT_FEEDS


def test_told_once_then_rearmed(tmp_path):
    st, al = str(tmp_path / "s.json"), str(tmp_path / "a.json")
    _, fresh = ss.run(FEEDS, {"location": ago(500)}, st, al, NOW)
    assert fresh == ["location"]
    _, fresh = ss.run(FEEDS, {"location": ago(501)}, st, al, NOW)
    assert fresh == []
    with open(al, encoding="utf-8") as f:
        assert json.load(f)["active"] == ["location"]
    ss.run(FEEDS, {"location": ago(1)}, st, al, NOW)
    _, fresh = ss.run(FEEDS, {"location": ago(500)}, st, al, NOW)
    assert fresh == ["location"]


def test_unreadable_state_alarms_again(tmp_path):
    st = tmp_path / "s.json"
    st.write_text("{not json")
    _, fresh = ss.run(FEEDS, {}, str(st), None, NOW)
    assert fresh == ["location"]


def test_exit_codes(tmp_path):
    seen = tmp_path / "seen.json"
    feeds = tmp_path / "f.json"
    feeds.write_text(json.dumps(FEEDS))
    now = NOW.isoformat()
    seen.write_text(json.dumps({"location": ago(5)}))
    assert ss.main(["--seen", str(seen), "--feeds", str(feeds), "--now", now]) == 0
    seen.write_text(json.dumps({"location": ago(500)}))
    assert ss.main(["--seen", str(seen), "--feeds", str(feeds), "--now", now]) == 1
    missing = str(tmp_path / "missing.json")
    assert ss.main(["--seen", missing, "--feeds", str(feeds), "--now", now]) == 2
