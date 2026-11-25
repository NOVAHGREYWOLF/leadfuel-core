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


def test_spoken_minute_long_first_line_is_cut_not_silent():
    text = "word " * (brief.SPOKEN_WORDS_PER_MINUTE + 20)
    out = brief.spoken_minute(text)
    assert len(out.split()) == brief.SPOKEN_WORDS_PER_MINUTE


@pytest.mark.parametrize("kind", ["email", "transfer", "delete", "deploy", "publish", "", "EDIT"])
def test_unknown_kind_fails_closed_to_irreversible(kind):
    # An unknown kind must never be labelled "Can be undone", and may not carry an undo.
    p = proposal.Proposal("t", kind, "r", ["s"], lambda: 1)
    assert not p.reversible
    assert "Can be undone" not in p.explain()
    assert "CANNOT BE UNDONE" in p.explain()
    with pytest.raises(ValueError):
        proposal.Proposal("t", kind, "r", ["s"], lambda: 1, lambda: 1)


@pytest.mark.parametrize("kind", ["send", "payment", "post", "transfer"])
def test_irreversible_approve_runs_once(kind):
    ran = []
    p = proposal.Proposal("t", kind, "r", ["s"], lambda: ran.append(1))
    stop = proposal.StopControl()
    p.approve(stop)
    with pytest.raises(proposal.AlreadyApproved):
        p.approve(stop)
    assert ran == [1]


def test_irreversible_that_raises_is_still_spent():
    ran = []

    def boom():
        ran.append(1)
        raise OSError("network dropped mid-send")

    p = proposal.Proposal("t", "payment", "r", ["s"], boom)
    stop = proposal.StopControl()
    with pytest.raises(OSError):
        p.approve(stop)
    with pytest.raises(proposal.AlreadyApproved):
        p.approve(stop)
    assert ran == [1]


def test_reversible_approve_twice_refused_until_undone():
    log = []
    p = proposal.Proposal("t", "edit", "r", ["s"],
                          lambda: log.append("do"), lambda: log.append("undo"))
    stop = proposal.StopControl()
    p.approve(stop)
    with pytest.raises(proposal.AlreadyApproved):
        p.approve(stop)
    p.undo_it(stop)
    p.approve(stop)
    assert log == ["do", "undo", "do"]


def test_reentrant_approve_refused():
    holder = {}
    stop = proposal.StopControl()

    def act():
        with pytest.raises(proposal.AlreadyApproved):
            holder["p"].approve(stop)
        return "ok"

    holder["p"] = proposal.Proposal("t", "send", "r", ["s"], act)
    assert holder["p"].approve(stop) == "ok"


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
