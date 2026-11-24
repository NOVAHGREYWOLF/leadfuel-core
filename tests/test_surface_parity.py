"""WATCH fold-x-G20: the parity check fails on a difference and says unknown when it cannot see."""
import importlib.util
import json
import os
import sys

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "surface_parity.py")
_spec = importlib.util.spec_from_file_location("surface_parity", _PATH)
sp = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sp)

SAME = "The nightly run passed."


def test_controls_pass():
    ok, bad = sp.run_controls()
    assert ok, bad


def test_agreeing_surfaces_are_ok_and_normalised():
    out = sp.classify({"web": SAME, "connector": "  the NIGHTLY run passed ", "arm": SAME})
    assert out["state"] == "ok", out


def test_difference_fails_even_with_a_silent_surface():
    out = sp.classify({"web": SAME, "connector": "It failed.", "arm": None})
    assert out["state"] == "failed", out


def test_silent_required_surface_is_unknown_not_ok():
    assert sp.classify({"web": SAME, "connector": SAME, "arm": None})["state"] == "unknown"
    assert sp.classify({"web": SAME, "connector": SAME})["state"] == "unknown"


def test_fourth_surface_counts_when_present():
    ans = {"web": SAME, "connector": SAME, "arm": SAME, "shell": "Different."}
    assert sp.classify(ans)["state"] == "failed"
    ans["shell"] = SAME
    assert sp.classify(ans)["state"] == "ok"
    ans["shell"] = None
    out = sp.classify(ans)
    assert out["state"] == "ok" and "shell" in out["silent"]


def test_broken_comparer_is_caught_by_controls(monkeypatch):
    monkeypatch.setattr(sp, "classify", lambda *a, **k: {"state": "ok"})
    ok, bad = sp.run_controls()
    assert not ok and "differ" in bad


def _cfg(tmp_path, **surfaces):
    p = tmp_path / "c.json"
    p.write_text(json.dumps({"question": "q?", "timeout_seconds": 20,
                             "surfaces": {k: {"argv": v} for k, v in surfaces.items()}}))
    return str(p)


def _echo(text):
    return [sys.executable, "-c", f"print({text!r})"]


def test_end_to_end_with_real_subprocesses(tmp_path):
    path = _cfg(tmp_path, web=_echo(SAME), connector=_echo(SAME), arm=_echo(SAME))
    assert sp.check(path)["state"] == "ok"
    path = _cfg(tmp_path, web=_echo(SAME), connector=_echo("No."), arm=_echo(SAME))
    assert sp.check(path)["state"] == "failed"
    bad = [sys.executable, "-c", "import sys; sys.exit(3)"]
    path = _cfg(tmp_path, web=_echo(SAME), connector=_echo(SAME), arm=bad)
    out = sp.check(path)
    assert out["state"] == "unknown" and out["notes"]["arm"] == "exit 3"


def test_missing_or_bad_config_is_unknown(tmp_path):
    assert sp.check(str(tmp_path / "nope.json"))["state"] == "unknown"
    p = tmp_path / "x.json"
    p.write_text("{}")
    assert sp.check(str(p))["state"] == "unknown"
