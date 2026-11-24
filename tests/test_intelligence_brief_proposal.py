import pytest

from intelligence import brief, proposal


def test_morning_empty_says_nothing_recorded_not_all_clear():
    text = brief.morning_brief({})
    assert text.count("- nothing recorded") == 3
    assert "all clear" not in text.lower()


def test_morning_caps_moves_at_three():
    text = brief.morning_brief({"moves": ["a", "b", "c", "d"]})
    assert "- c" in text and "- d" not in text


def test_evening_sections_and_blank_items_dropped():
    text = brief.evening_close({"done": ["shipped x", "  "], "paid": []})
    assert "- shipped x" in text
    assert text.count("- nothing recorded") == 3


def test_spoken_minute_fits_budget():
    long = "\n".join("word " * 50 for _ in range(10))
    assert len(brief.spoken_minute(long).split()) <= brief.SPOKEN_WORDS_PER_MINUTE


def test_proposal_needs_sources_and_undo():
    with pytest.raises(ValueError):
        proposal.Proposal("t", "edit", "r", [], lambda: 1, lambda: 1)
    with pytest.raises(ValueError):
        proposal.Proposal("t", "edit", "r", ["s"], lambda: 1)


def test_irreversible_is_labelled_and_has_no_undo():
    p = proposal.Proposal("pay", "payment", "r", ["inv"], lambda: 1)
    assert "CANNOT BE UNDONE" in p.explain()
    with pytest.raises(ValueError):
        proposal.Proposal("pay", "payment", "r", ["inv"], lambda: 1, lambda: 1)
    stop = proposal.StopControl()
    p.approve(stop)
    with pytest.raises(ValueError):
        p.undo_it(stop)


def test_working_example_sources_undo_and_stop():
    log = []
    p = proposal.Proposal("move block", "edit", "gap in calendar", ["cal row 4"],
                          lambda: log.append("do"), lambda: log.append("undo"))
    assert "cal row 4" in p.explain() and "Can be undone" in p.explain()
    stop = proposal.StopControl()
    p.approve(stop)
    p.undo_it(stop)
    assert log == ["do", "undo"]
    stop.stop()
    with pytest.raises(proposal.StopRequested):
        p.approve(stop)
    assert log == ["do", "undo"]
