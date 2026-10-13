"""WATCH Q189: the vault-sync log reader says ok only on proof, and unknown when it cannot see."""
import datetime as dt
import importlib.util
import json
import os

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "vault_sync_status.py")
_spec = importlib.util.spec_from_file_location("vault_sync_status", _PATH)
vss = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vss)

NOW = dt.datetime(2026, 10, 3, 18, 0, tzinfo=dt.timezone.utc)
START = "=== vault_private_sync start {}\n"
END = "=== vault_private_sync end {} exit={}\n"
PUSHED = "[{}] pushed 1 ref(s) ['refs/heads/main']; remote has 3 branch(es); ls-remote verified\n"


def ts(hours_ago, now=NOW):
    return (now - dt.timedelta(hours=hours_ago)).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_block(hours_ago, exit_code=0, pushed=vss.EXPECTED_TARGETS, extra="", now=NOW):
    return (START.format(ts(hours_ago, now)) + "".join(PUSHED.format(t) for t in pushed) + extra
            + END.format(ts(hours_ago - 0.2, now), exit_code))


def state(text):
    return vss.classify(text, NOW)


def test_clean_fresh_run_is_ok():
    out = state(run_block(5))
    assert out["state"] == "ok", out
    assert out["targets_verified"] == sorted(vss.EXPECTED_TARGETS)
    assert out["runs_seen"] == 1


@pytest.mark.parametrize("code", [1, 2, 3, 4, 5, 9])
def test_nonzero_exit_is_failed(code):
    out = state(run_block(5, exit_code=code, pushed=()))
    assert out["state"] == "failed", out
    assert f"exit {code}" in out["reason"]


def test_missing_log_is_unknown_never_ok():
    assert state(None)["state"] == "unknown"


@pytest.mark.parametrize("text", ["", "\n\n", "some unrelated output\n", "=== vault_private_sync start garbage\n"])
def test_empty_or_runless_log_is_unknown(text):
    assert state(text)["state"] == "unknown"


def test_stale_clean_run_is_unknown_never_ok():
    out = state(run_block(vss.STALE_AFTER_HOURS + 1))
    assert out["state"] == "unknown", out
    assert "stale" in out["reason"]


def test_exit_zero_without_push_evidence_is_unknown():
    # A --dry-run also ends exit=0 but pushes nothing.
    dry = "[claude-sessions] dry-run clean: 10 blobs, exclusions verified\n"
    out = state(run_block(5, pushed=(), extra=dry))
    assert out["state"] == "unknown", out


def test_exit_zero_missing_one_target_is_unknown():
    out = state(run_block(5, pushed=("leadfuel-estate",)))
    assert out["state"] == "unknown"
    assert "claude-sessions" in out["reason"]


def test_started_never_finished_past_limit_is_failed():
    out = state(START.format(ts(vss.RUN_LIMIT_HOURS + 1)) + PUSHED.format("leadfuel-estate"))
    assert out["state"] == "failed", out


def test_run_in_progress_is_unknown():
    assert state(START.format(ts(0.5)))["state"] == "unknown"


def test_last_run_wins_over_earlier_ok():
    text = run_block(30) + run_block(5, exit_code=2, pushed=())
    out = state(text)
    assert out["state"] == "failed" and out["runs_seen"] == 2


def test_earlier_failure_then_clean_run_is_ok():
    text = run_block(30, exit_code=1, pushed=()) + run_block(5)
    assert state(text)["state"] == "ok"


def test_crashed_run_followed_by_new_run_reads_the_new_one():
    # A traceback with no end line, then a fresh clean run.
    text = START.format(ts(28)) + "Traceback (most recent call last):\n" + run_block(4)
    assert state(text)["state"] == "ok"


def test_future_start_is_unknown():
    assert state(run_block(-5))["state"] == "unknown"


def test_utf16_log_is_decoded(tmp_path):
    p = tmp_path / "sync.log"
    p.write_bytes(run_block(5).encode("utf-16"))
    assert vss.read_status(str(p), NOW)["state"] == "ok"


def test_read_status_on_real_file_with_controls(tmp_path):
    p = tmp_path / "sync.log"
    p.write_text("older noise\n" + run_block(5), encoding="utf-8")
    out = vss.read_status(str(p), NOW)
    assert out["state"] == "ok" and out["controls_ok"] is True and out["log_present"] is True
    assert out["schema"] == vss.SCHEMA and out["checked_at"] == "2026-10-03T18:00:00Z"


def test_read_status_missing_file_is_unknown(tmp_path):
    out = vss.read_status(str(tmp_path / "absent.log"), NOW)
    assert out["state"] == "unknown" and out["log_present"] is False and out["controls_ok"] is True


def test_controls_catch_a_reader_that_always_says_ok(tmp_path, monkeypatch):
    # Positive control: if the classifier were broken into "always ok", the result must be unknown.
    p = tmp_path / "sync.log"
    p.write_text(run_block(5), encoding="utf-8")
    monkeypatch.setattr(vss, "classify", lambda text, now, **k: {"state": "ok", "reason": "x"})
    out = vss.read_status(str(p), NOW)
    assert out["state"] == "unknown" and out["controls_ok"] is False


def test_controls_pass_on_the_real_classifier():
    ok, bad = vss.run_controls(NOW)
    assert ok and bad == []


# --- the saved status file, for readers that do not run the reader themselves ---

def write_status(tmp_path, **over):
    data = {"schema": vss.SCHEMA, "state": "ok", "reason": "fine", "checked_at": ts(1), **over}
    p = tmp_path / "status.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return str(p)


def test_status_file_fresh_ok_is_ok(tmp_path):
    assert vss.read_status_file(write_status(tmp_path), NOW)["state"] == "ok"


def test_status_file_old_ok_becomes_unknown(tmp_path):
    out = vss.read_status_file(write_status(tmp_path, checked_at=ts(vss.STATUS_FILE_MAX_AGE_HOURS + 1)), NOW)
    assert out["state"] == "unknown" and "was ok" in out["reason"]


@pytest.mark.parametrize("over", [{"schema": "other/1"}, {"state": "green"}, {"checked_at": None}])
def test_status_file_foreign_or_incomplete_is_unknown(tmp_path, over):
    assert vss.read_status_file(write_status(tmp_path, **over), NOW)["state"] == "unknown"


def test_status_file_missing_or_garbage_is_unknown(tmp_path):
    assert vss.read_status_file(str(tmp_path / "nope.json"), NOW)["state"] == "unknown"
    p = tmp_path / "bad.json"
    p.write_text("{not json", encoding="utf-8")
    assert vss.read_status_file(str(p), NOW)["state"] == "unknown"


def test_cli_writes_status_and_exit_code(tmp_path, capsys):
    log = tmp_path / "sync.log"
    # The CLI reads the wall clock, so the run is placed relative to it.
    log.write_text(run_block(1, exit_code=4, pushed=(), now=dt.datetime.now(dt.timezone.utc)), encoding="utf-8")
    rc = vss.main(["--log", str(log), "--write"])
    saved = json.loads((tmp_path / "status.json").read_text(encoding="utf-8"))
    assert rc == 1 and saved["state"] == "failed"
    assert json.loads(capsys.readouterr().out)["state"] == "failed"
