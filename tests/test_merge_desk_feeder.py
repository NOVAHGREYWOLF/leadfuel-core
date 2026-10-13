"""The Merge desk feeder must say 'unknown' whenever its inputs cannot establish a value."""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "watch"))

import merge_desk_feeder as m  # noqa: E402


def chk(status, conclusion="", start="2026-10-04T10:00:00Z", end="2026-10-04T10:05:00Z"):
    return {"status": status, "conclusion": conclusion, "startedAt": start, "completedAt": end}


def test_draft_wins_over_green():
    assert m.classify([chk("COMPLETED", "SUCCESS")], True)[0] == "draft"


def test_no_checks_is_unknown_not_green():
    assert m.classify([], False)[0] == "unknown"


def test_red_beats_running():
    assert m.classify([chk("COMPLETED", "FAILURE"), chk("IN_PROGRESS")], False)[0] == "ci-red"


def test_running():
    assert m.classify([chk("COMPLETED", "SUCCESS"), chk("IN_PROGRESS", "", end="0001-01-01T00:00:00Z")], False)[0] == "ci-running"


def test_skipped_counts_as_passing():
    assert m.classify([chk("COMPLETED", "SUCCESS"), chk("COMPLETED", "SKIPPED")], False)[0] == "green-waiting"


def test_unrecognised_check_state_is_unknown():
    assert m.classify([chk("COMPLETED", "SOMETHING_NEW")], False)[0] == "unknown"


def test_eta_unknown_without_enough_ci_samples():
    mins, why = m.eta_for("green-waiting", None, 1, None, (2, True), 3.0)
    assert mins is None and "fewer than" in why


def test_eta_unknown_when_not_in_slot_queue():
    mins, why = m.eta_for("green-waiting", 6.0, 40, None, None, None)
    assert mins is None and "no ticket" in why


def test_eta_is_position_times_measured_ci():
    # 2 ahead, slot held 2m of a 6m median: holder left 4 + (2+1)*6 = 22
    mins, _ = m.eta_for("green-waiting", 6.0, 40, None, (2, True), 2.0)
    assert mins == 22


def test_eta_unknown_for_red_and_draft_and_no_pr():
    for st in ("ci-red", "draft", "no-pr"):
        assert m.eta_for(st, 6.0, 40, None, None, None)[0] is None


def test_running_eta_floor_when_over_median():
    mins, why = m.eta_for("ci-running", 6.0, 40, 9.0, None, None)
    assert mins == 6 and "floor" in why


def test_median_needs_minimum_samples():
    assert m.median_or_none([1.0, 2.0], 3) is None
    assert m.median_or_none([1.0, 2.0, 9.0], 3) == 2.0


def test_desk_from_ticket_name():
    assert m.desk_from_name("20261002T123500Z-f2785e-DOORS-pr709-squash-only") == "DOORS"
    assert m.desk_from_name("not-a-ticket") is None


def test_locks_unreadable_is_none(tmp_path):
    assert m.read_locks(str(tmp_path / "missing")) is None


def test_locks_holder_and_waiters(tmp_path):
    (tmp_path / "ci-hubx").mkdir()
    (tmp_path / "ci-hubx" / "held-by-NODE").write_text("held-by NODE (pr12) 2026-10-04T10:00:00Z", encoding="utf-8")
    w = tmp_path / "ci-hubx.wait"
    w.mkdir()
    (w / "20261004T090000Z-NODE-job").write_text("PR #34 session local_0123abcd KIND: merge-on-green", encoding="utf-8")
    locks = m.read_locks(str(tmp_path))
    assert locks["ci-hubx"]["holder"]["prs"] == [12]
    assert locks["ci-hubx"]["holder"]["since"] == "2026-10-04T10:00:00Z"
    assert locks["ci-hubx"]["waiters"][0]["prs"] == [34]
    assert locks["ci-hubx"]["waiters"][0]["sessions"] == ["local_0123abcd"]
