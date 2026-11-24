"""own-2 and own-3: the level rule and the payout ledger refuse what they cannot see.

The subjects are the false pass (a click passes a level), the false zero (an unreadable source reads as
nothing paid) and the level that runs out. Every refusal has a positive control that does count.
"""
import datetime as dt

from game import level_rule as lr
from game import payout_ledger as pl

TODAY = dt.date(2026, 11, 23)


def outcome(**kw):
    base = {"id": "o1", "date": "2026-11-20", "kind": "money_in", "value": 100, "source": "bank",
            "measured": True}
    base.update(kw)
    return base


# ---- ledger -------------------------------------------------------------------------------------------
def test_unreadable_source_is_unknown_not_zero():
    led = pl.build_ledger(None)
    assert led["status"] == "unknown" and led["totals"] == {}
    assert "UNKNOWN" in pl.render_text(led)


def test_empty_but_read_is_empty_not_unknown():
    led = pl.build_ledger([])
    assert led["status"] == "empty"
    assert "UNKNOWN" not in pl.render_text(led)


def test_a_click_is_never_a_payout_and_is_listed_as_refused():
    led = pl.build_ledger([outcome(id="c1", source="click"), outcome(id="c2", measured=False), outcome(id="ok")])
    assert [ln["id"] for ln in led["lines"]] == ["ok"]
    assert {r["id"] for r in led["refused"]} == {"c1", "c2"}


def test_positive_control_a_measured_line_counts():
    led = pl.build_ledger([outcome()])
    assert led["status"] == "ok" and led["totals"]["money_in"]["value"] == 100


def test_kinds_are_never_added_together():
    led = pl.build_ledger([outcome(id="a", value=50), outcome(id="b", kind="hours_returned", value=3, source="loop"),
                           outcome(id="c", kind="thing_running", value=1, source="run_log")])
    assert set(led["totals"]) == {"money_in", "hours_returned", "thing_running"}
    assert led["totals"]["hours_returned"]["unit"] == "hours"
    assert "total" not in led


def test_refuses_bad_shapes():
    bad = [outcome(id="k", kind="likes"), outcome(id="v", value=-1), outcome(id="s", value="5"),
           outcome(id="d", date="soon"), outcome(id="u", unit="eur"), {"value": 3}, "text", outcome(id="b", value=True)]
    led = pl.build_ledger(bad)
    assert led["lines"] == [] and len(led["refused"]) == len(bad)


def test_duplicate_id_counts_once():
    led = pl.build_ledger([outcome(), outcome()])
    assert led["totals"]["money_in"]["value"] == 100 and len(led["refused"]) == 1


# ---- levels -------------------------------------------------------------------------------------------
def test_gap_that_blocks_most_comes_first_then_goal_then_recheck():
    gaps = [{"key": "g1", "title": "Answer ICP", "blocks": 1}, {"key": "g2", "title": "Connect mail", "blocks": 3}]
    goals = [{"key": "x", "title": "Land a client", "confirmed": True}]
    first = lr.next_level(gaps, goals, [], [], TODAY)["level"]
    assert first["key"] == "g2" and first["source"] == "gap"
    only_goal = lr.next_level([], goals, [], [], TODAY)["level"]
    assert only_goal["source"] == "goal"


def test_unconfirmed_goal_and_zero_block_gap_make_no_level():
    r = lr.next_level([{"key": "g", "title": "t", "blocks": 0}], [{"key": "x", "title": "t", "confirmed": False}], [], [], TODAY)
    assert r["level"] is None and r["reason"] == "nothing_owed"


def test_never_runs_out_a_passed_level_comes_back_for_a_recheck():
    lid = lr.level_id("gap", "g1")
    passed = [{"id": lid, "key": "g1", "source": "gap", "title": "Answer ICP", "passed_on": "2026-08-01"}]
    r = lr.next_level([{"key": "g1", "title": "Answer ICP", "blocks": 2}], [], passed, [], TODAY)
    assert r["level"]["source"] == "recheck"
    assert r["level"]["id"] != lid


def test_recent_pass_gives_nothing_owed_with_a_next_date_not_game_over():
    lid = lr.level_id("gap", "g1")
    passed = [{"id": lid, "key": "g1", "source": "gap", "title": "t", "passed_on": "2026-11-01"}]
    r = lr.next_level([{"key": "g1", "title": "t", "blocks": 2}], [], passed, [], TODAY)
    assert r["level"] is None and r["next_check"] == "2027-01-30"


def test_declined_level_retires_thirty_days_then_returns():
    lid = lr.level_id("gap", "g1")
    gaps = [{"key": "g1", "title": "t", "blocks": 1}]
    held = lr.next_level(gaps, [], [], [{"id": lid, "declined_on": "2026-11-10"}], TODAY)
    assert held["level"] is None and held["next_check"] == "2026-12-10"
    back = lr.next_level(gaps, [], [], [{"id": lid, "declined_on": "2026-10-10"}], TODAY)
    assert back["level"]["id"] == lid


def test_difficulty_grows_with_passed_count_and_is_capped():
    assert lr.tier(0) == 1 and lr.tier(5) == 2 and lr.tier(10_000) == lr.TIER_CAP


def test_level_ids_are_stable():
    assert lr.level_id("gap", "g1") == lr.level_id("gap", "g1") != lr.level_id("goal", "g1")


def test_a_level_passes_only_on_a_measured_ledger_line_traced_to_it():
    lvl = lr.next_level([{"key": "g1", "title": "t", "blocks": 1}], [], [], [], TODAY)["level"]
    assert lr.passes(lvl, pl.build_ledger(None)) is False
    assert lr.passes(lvl, pl.build_ledger([])) is False
    assert lr.passes(lvl, pl.build_ledger([outcome(source="click", trace=lvl["id"])])) is False
    assert lr.passes(lvl, pl.build_ledger([outcome(trace="L-other")])) is False
    assert lr.passes(lvl, pl.build_ledger([outcome(trace=lvl["id"])])) is True
