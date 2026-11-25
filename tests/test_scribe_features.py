"""SCRIBE K09: the FEATURES generator never says `shipped` without a checked pointer, and never for a flag that is off.

Everything runs on a throwaway fake hub in tmp_path. Nothing reads the real estate, runs `gh`, or opens a socket.
"""
import importlib.util
import json
import os

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "scribe", "features.py")
_spec = importlib.util.spec_from_file_location("scribe_features", _PATH)
ft = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ft)


@pytest.fixture
def hub(tmp_path):
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_door.py").write_text("def test_x(): pass\n")
    (tmp_path / "tests" / "test_flagged.py").write_text("def test_y(): pass\n")
    (tmp_path / "app.py").write_text(
        'import os\n'
        'A = os.environ.get("ALPHA_ENABLED", "")\n'
        'B = os.environ.get("BETA_ENABLED", "1")\n'
        'C = os.environ.get("GAMMA_ENABLED")\n'
        'D = os.getenv("DELTA_ENABLED", default_for_it())\n'
        'E = os.environ.get("EPS_ENABLED", "0")\n'
        'F = os.environ.get("EPS_ENABLED", "1")\n')
    # a test file's flags are not product flags
    (tmp_path / "tests" / "test_ignored.py").write_text('import os\nX = os.environ.get("IGNORED_ENABLED")\n')
    return tmp_path


def _status(rows, feature):
    return next(r["status"] for r in rows if r["feature"] == feature)


def test_scan_reads_defaults_and_skips_tests(hub):
    f = ft.scan_flags(hub)
    assert f["ALPHA_ENABLED"]["default"] == "off"
    assert f["BETA_ENABLED"]["default"] == "on"
    assert f["GAMMA_ENABLED"]["default"] == "off"
    assert f["DELTA_ENABLED"]["default"] == "unknown"      # an expression is not guessed
    assert f["EPS_ENABLED"]["default"] == "unknown"        # two call sites disagree
    assert "IGNORED_ENABLED" not in f


def test_shipped_needs_a_checked_pointer(hub):
    reg = [{"feature": "ok", "evidence": {"test": "tests/test_door.py"}},
           {"feature": "ghost", "evidence": {"test": "tests/test_nope.py"}},
           {"feature": "bare"}]
    rows = ft.build_rows(reg, hub)
    assert _status(rows, "ok") == ft.SHIPPED
    assert _status(rows, "ghost") == ft.UNVERIFIED
    assert _status(rows, "bare") == ft.UNVERIFIED


def test_pr_pointer_needs_the_merged_list(hub):
    reg = [{"feature": "p", "evidence": {"pr": 12}}]
    assert _status(ft.build_rows(reg, hub), "p") == ft.UNVERIFIED                  # no list: cannot check
    assert _status(ft.build_rows(reg, hub, merged={99: "other"}), "p") == ft.UNVERIFIED
    assert _status(ft.build_rows(reg, hub, merged={12: "it"}), "p") == ft.SHIPPED


def test_a_flag_that_is_off_never_says_shipped(hub):
    reg = [{"feature": "off", "flag": "ALPHA_ENABLED", "evidence": {"test": "tests/test_flagged.py"}}]
    rows = ft.build_rows(reg, hub)
    assert _status(rows, "off") == ft.DORMANT
    assert "deployment not read" in next(r for r in rows if r["feature"] == "off")["state_source"]


def test_snapshot_overrides_the_code_default(hub):
    reg = [{"feature": "on", "flag": "ALPHA_ENABLED", "evidence": {"test": "tests/test_flagged.py"}},
           {"feature": "off", "flag": "BETA_ENABLED", "evidence": {"test": "tests/test_flagged.py"}}]
    rows = ft.build_rows(reg, hub, flag_state={"ALPHA_ENABLED": "on", "BETA_ENABLED": "off"})
    assert _status(rows, "on") == ft.SHIPPED
    assert _status(rows, "off") == ft.DORMANT


def test_unreadable_flag_state_is_unverified_not_shipped(hub):
    reg = [{"feature": "m", "flag": "MISSING_ENABLED", "evidence": {"test": "tests/test_flagged.py"}},
           {"feature": "d", "flag": "DELTA_ENABLED", "evidence": {"test": "tests/test_flagged.py"}}]
    rows = ft.build_rows(reg, hub)
    assert _status(rows, "m") == ft.UNVERIFIED
    assert _status(rows, "d") == ft.UNVERIFIED


def test_planned_is_only_what_the_registry_says(hub):
    rows = ft.build_rows([{"feature": "later", "planned": True}], hub)
    assert _status(rows, "later") == ft.PLANNED


def test_unregistered_flags_appear_and_are_never_shipped(hub):
    rows = ft.build_rows([], hub)
    names = {r["flag"]: r["status"] for r in rows}
    assert names["ALPHA_ENABLED"] == ft.DORMANT
    assert names["BETA_ENABLED"] == ft.UNVERIFIED          # default on, nobody registered it
    assert ft.SHIPPED not in names.values()


def test_no_row_anywhere_is_shipped_without_a_pointer(hub):
    reg = [{"feature": "a", "flag": "BETA_ENABLED"}, {"feature": "b"}, {"feature": "c", "evidence": {"pr": 1}}]
    for r in ft.build_rows(reg, hub, flag_state={"BETA_ENABLED": "on"}):
        assert r["status"] != ft.SHIPPED or r["evidence"] not in ("none", "")


def test_empty_input_says_nothing_to_show(tmp_path):
    text = ft.render(ft.build_rows([], tmp_path), "2026-11-23")
    assert "Nothing to show" in text and "|" not in text


def test_cli_unknown_when_the_hub_is_missing(tmp_path, capsys):
    assert ft.main(["--hub", str(tmp_path / "nope"), "--as-of", "2026-11-23"]) == 2
    assert "UNKNOWN" in capsys.readouterr().err


def test_cli_writes_the_file(hub, tmp_path):
    reg = tmp_path / "r.json"
    reg.write_text(json.dumps([{"feature": "ok", "evidence": {"test": "tests/test_door.py"}}]))
    out = tmp_path / "F.md"
    assert ft.main(["--hub", str(hub), "--registry", str(reg), "--as-of", "2026-11-23", "--out", str(out)]) == 0
    assert "| ok | shipped |" in out.read_text()


def test_seed_registry_rows_are_all_pointered_or_planned():
    path = os.path.join(os.path.dirname(_PATH), "features.json")
    for e in json.load(open(path, encoding="utf-8")):
        assert e.get("planned") or e.get("evidence"), e["feature"]
