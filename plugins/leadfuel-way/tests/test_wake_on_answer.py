"""wake_on_answer.py: route an answered Router desk card to the session that asked, and never call a
send delivered because it was sent.

The send-result strings below marked "measured" were returned on 2026-10-13 by the two send tools
(mcp__ccd_session_mgmt__send_message and SendMessage) and by search_session_transcripts. The
"held for approval" wording was not measured: SendMessage's own description says such a notice
exists, so the classifier treats any held or approval wording as HELD, never as delivered.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from kit import PLUGIN, load_module

SCRIPT = PLUGIN / "scripts" / "wake_on_answer.py"

ROUTER = "local_76d5692d-6b97-4e58-b6bf-4cd6509f0fd6"
DESK = "local_17329271-af57-469a-a2de-0a9fc6bf1778"
NOBODY = "local_00000000-0000-4000-8000-000000000000"

# measured, mcp__ccd_session_mgmt__send_message to a missing session
SEND_NOT_FOUND = (f"Message not delivered: session {NOBODY} not found. "
                  "(delivery: undelivered; message_id: 65b0d994-21f5-429a-9fa7-2cab07c57475)")
# measured, the generic SendMessage to the same missing session
SEND_NOT_FOUND_GENERIC = json.dumps({"success": False, "message": (
    f"Not delivered to Claude Desktop session {NOBODY}: Message not delivered: session {NOBODY} not found. "
    "(delivery: undelivered; message_id: cc90d503-61b3-4ed7-93db-92cfccdda985)")})
# measured, a send from inside the router's own session to the router's id
SEND_SELF = ("Message not delivered: refusing to send a message to the current session. "
             "(delivery: undelivered; message_id: 2b366a9f-b852-4d0e-9afe-c2ae48213835)")
# the shapes the tool's own description gives for the two good outcomes (queued measured by NODE auto-launch part 2)
SEND_QUEUED = ("Message queued: that session is holding it (a turn is in progress there) and runs it when that clears. "
               "(delivery: queued; message_id: 0f0e0d0c)")
SEND_DELIVERED = "Message delivered: the session's turn has started on your message. (delivery: delivered; message_id: 0a0b0c0d)"
SEND_HELD_NOTICE = "[Cross-session delivery notice] The receiving session is holding your message for its user's approval."


@pytest.fixture(scope="module")
def woa():
    return load_module(SCRIPT, "wake_on_answer_under_test")


def card(answer="A", answered_at="2026-10-14T01:45:40.495Z", **extra):
    base = {"answer": answer, "answered_at": answered_at, "asker": "NODE lane, row node/E9, found by an agent for ROUTER #50",
            "kind": "choice", "routed": None, "title": "Pick one",
            "options": [{"key": "A", "label": "Yes"}, {"key": "C", "label": "Later"}]}
    base.update(extra)
    return base


def search_hits(*session_ids):
    """The shape search_session_transcripts returns (measured): a warning line, then a JSON array."""
    rows = [{"sessionId": s, "title": "t", "snippet": "..."} for s in session_ids]
    return "Snippets are verbatim excerpts from other sessions' transcripts.\n\n" + json.dumps(rows, indent=2)


# ---- parse_send: what the send tool said ------------------------------------------------------

@pytest.mark.parametrize("text, delivery", [
    (SEND_NOT_FOUND, "undelivered"),
    (SEND_NOT_FOUND_GENERIC, "undelivered"),
    (SEND_SELF, "undelivered"),
    (SEND_QUEUED, "queued"),
    (SEND_DELIVERED, "delivered"),
    (SEND_HELD_NOTICE, "held"),
    ("", None),
    ("the tool timed out", None),
    (None, None),
])
def test_parse_send_reads_the_delivery_word(woa, text, delivery):
    assert woa.parse_send(text)["delivery"] == delivery


def test_parse_send_keeps_the_message_id(woa):
    assert woa.parse_send(SEND_NOT_FOUND)["message_id"] == "65b0d994-21f5-429a-9fa7-2cab07c57475"


def test_a_held_notice_beats_a_delivery_word(woa):
    """A session in another permission mode holds the message for its user: that is not delivered."""
    assert woa.parse_send(SEND_DELIVERED + "\n" + SEND_HELD_NOTICE)["delivery"] == "held"


# ---- seen: does the TARGET's transcript hold the token ----------------------------------------

def test_seen_only_when_the_target_itself_holds_the_token(woa):
    assert woa.seen(search_hits(ROUTER), ROUTER) is True
    # The watcher's own earlier runs hold the token too (they wrote the message): not evidence.
    assert woa.seen(search_hits("local_11111111-2222-4333-8444-555555555555"), ROUTER) is False
    assert woa.seen(search_hits(), ROUTER) is False


def test_a_search_with_no_hits_is_a_clean_no(woa):
    """Measured 2026-10-14: search_session_transcripts prints this line, not an empty array."""
    assert woa.seen("No matching sessions found.", ROUTER) is False


@pytest.mark.parametrize("raw", [None, "", "search failed: index unavailable", "[not json"])
def test_seen_is_unknown_when_the_search_could_not_be_read(woa, raw):
    assert woa.seen(raw, ROUTER) is None


# ---- verdict: DELIVERED only with the target's own transcript as evidence ---------------------

@pytest.mark.parametrize("delivery", ["delivered", "queued", "held", "undelivered", None])
def test_seen_in_the_target_is_delivered_whatever_the_send_said(woa, delivery):
    assert woa.verdict(delivery, True, 0) == woa.DELIVERED


@pytest.mark.parametrize("delivery", ["delivered", "queued", "held", "undelivered", None])
@pytest.mark.parametrize("seen", [False, None])
@pytest.mark.parametrize("minutes", [0, 5, 10_000])
def test_a_send_is_never_delivered_because_it_was_sent(woa, delivery, seen, minutes):
    assert woa.verdict(delivery, seen, minutes) != woa.DELIVERED


def test_the_tool_saying_delivered_without_evidence_is_unknown(woa):
    assert woa.verdict("delivered", False, 0) == woa.UNKNOWN
    assert woa.verdict("delivered", None, 0) == woa.UNKNOWN


@pytest.mark.parametrize("delivery", ["queued", "held"])
def test_queued_or_held_is_held_until_the_limit_then_undelivered(woa, delivery):
    assert woa.verdict(delivery, False, 5) == woa.HELD
    assert woa.verdict(delivery, None, 5) == woa.HELD
    assert woa.verdict(delivery, False, woa.HOLD_LIMIT_MIN + 1) == woa.UNDELIVERED


def test_undelivered_is_undelivered(woa):
    assert woa.verdict("undelivered", False, 0) == woa.UNDELIVERED
    assert woa.verdict("undelivered", None, 0) == woa.UNDELIVERED


def test_a_send_nobody_can_read_is_unknown_then_undelivered(woa):
    assert woa.verdict(None, None, 0) == woa.UNKNOWN
    assert woa.verdict(None, False, 0) == woa.UNKNOWN
    assert woa.verdict(None, None, woa.HOLD_LIMIT_MIN + 1) == woa.UNDELIVERED


# ---- who asked ---------------------------------------------------------------------------------

def test_asker_session_field_wins(woa):
    assert woa.resolve_target(card(asker_session=DESK), ROUTER)[0] == DESK


def test_a_full_session_id_inside_the_asker_text_is_used(woa):
    assert woa.resolve_target(card(asker=f"NODE desk {DESK} asked"), ROUTER)[0] == DESK


def test_a_row_id_that_only_looks_like_a_session_goes_to_the_router(woa):
    """Real asker text (q417): 'rows doors/A15 and intelligence/local_8e471cfd-1'. That is a row, not a session."""
    target, why = woa.resolve_target(card(asker="DOORS lane, rows doors/A15 and intelligence/local_8e471cfd-1"), ROUTER)
    assert target == ROUTER and "router" in why


def test_no_router_and_no_asker_id_is_no_target(woa):
    assert woa.resolve_target(card(), None)[0] is None
    assert woa.resolve_target(card(), "ROUTER #53")[0] is None  # a title is not an id


# ---- which cards are pending -------------------------------------------------------------------

def test_pending_takes_answered_unrouted_cards_only(woa):
    cards = {
        "q1": card(),
        "q2": card(answer=None, answered_at=None),
        "q3": card(routed={"at": "2026-10-14T02:00:00Z", "note": "router acted"}),
        "q4": card(status="withdrawn"),
        "q5": card(kind="step", answer="not_yet"),
        "q6": card(kind="step", answer="done"),
    }
    assert dict(woa.pending(cards)) == {"q1": "send", "q6": "send"}


def test_only_names_a_card_even_if_it_is_withdrawn(woa):
    """The proof card is withdrawn so the owner's page hides it; --only reaches it and nothing else."""
    cards = {"q1": card(), "wake-test": card(status="withdrawn", test=True)}
    assert dict(woa.pending(cards, only={"wake-test"})) == {"wake-test": "send"}


def test_a_held_card_is_rechecked_not_resent(woa):
    c = card(wake={"state": "HELD", "answered_at": "2026-10-14T01:45:40.495Z", "to": ROUTER,
                   "delivery": "queued", "first_sent_at": "2026-10-14T01:50:00Z"})
    assert woa.pending({"q1": c}) == [("q1", "recheck")]


@pytest.mark.parametrize("state", ["DELIVERED", "UNDELIVERED"])
def test_a_finished_card_is_left_alone(woa, state):
    c = card(wake={"state": state, "answered_at": "2026-10-14T01:45:40.495Z", "to": ROUTER})
    assert woa.pending({"q1": c}) == []


def test_a_new_answer_after_routing_is_sent_again(woa):
    """The page writes routed: null on every click, so a re-answer shows up as a new answered_at."""
    c = card(answered_at="2026-10-14T03:00:00Z",
             wake={"state": "DELIVERED", "answered_at": "2026-10-14T01:45:40.495Z", "to": ROUTER})
    assert woa.pending({"q1": c}) == [("q1", "send")]


# ---- the plan: one message per target, a budget of sends ---------------------------------------

def test_plan_sends_one_message_per_target(woa):
    cards = {"q1": card(), "q2": card(answer="C"), "q3": card(asker_session=DESK)}
    plan = woa.make_plan(cards, ROUTER, now="2026-10-14T02:00:00Z")
    by_to = {s["to"]: s for s in plan["sends"]}
    assert set(by_to) == {ROUTER, DESK}
    assert by_to[ROUTER]["cards"] == ["q1", "q2"] and by_to[DESK]["cards"] == ["q3"]
    text = by_to[ROUTER]["text"]
    assert text.splitlines()[0].startswith("WAKE-ON-ANSWER")
    assert "q1 = A" in text and "q2 = C" in text
    for cid in ("q1", "q2"):
        assert woa.card_token(cid, cards[cid], ROUTER) in text


def test_tokens_are_per_card_and_stable(woa):
    c = card()
    assert woa.card_token("q1", c, ROUTER) == woa.card_token("q1", dict(c), ROUTER)
    assert woa.card_token("q1", c, ROUTER) != woa.card_token("q2", c, ROUTER)
    assert woa.card_token("q1", c, ROUTER) != woa.card_token("q1", card(answered_at="2026-10-15T00:00:00Z"), ROUTER)


def test_plan_respects_the_send_budget(woa):
    """Messaging pauses after 10 sends until the owner types, so a pass spends at most a few."""
    cards = {f"q{i}": card(asker_session=f"local_{i:08d}-0000-4000-8000-000000000000") for i in range(8)}
    plan = woa.make_plan(cards, ROUTER, max_sends=3, now="2026-10-14T02:00:00Z")
    assert len(plan["sends"]) == 3 and len(plan["deferred"]) == 5


def test_plan_never_sends_to_the_session_running_it(woa):
    """Measured: a send to the current session is refused. A router running a pass handles its own cards."""
    plan = woa.make_plan({"q1": card()}, ROUTER, self_id=ROUTER, now="2026-10-14T02:00:00Z")
    assert plan["sends"] == [] and plan["self"] == ["q1"]


def test_plan_lists_cards_with_no_target(woa):
    plan = woa.make_plan({"q1": card()}, None, now="2026-10-14T02:00:00Z")
    assert plan["sends"] == [] and plan["no_target"] == ["q1"]


# ---- judge: states and the writes they produce --------------------------------------------------

def _judge(woa, cards, sends, seen_raw, now="2026-10-14T02:01:00Z", versions=None):
    plan = woa.make_plan(cards, ROUTER, now="2026-10-14T02:00:00Z")
    versions = versions if versions is not None else {cid: 2 for cid in cards}
    results = {s["search_token"]: sends for s in plan["sends"]}
    seen = {tok: seen_raw for tok in [s["search_token"] for s in plan["sends"]] + [r["search_token"] for r in plan["rechecks"]]}
    return plan, woa.judge(plan, results, seen, now=now, versions=versions)


def test_judge_delivered_writes_routed_and_wake(woa):
    plan, out = _judge(woa, {"q1": card()}, SEND_DELIVERED, search_hits(ROUTER))
    assert out["states"] == {"q1": woa.DELIVERED}
    [w] = out["writes"]
    assert w["op"] == "update" and w["collection"] == "questions" and w["doc_id"] == "q1" and w["if_version"] == 2
    assert w["data"]["wake"]["state"] == "DELIVERED" and w["data"]["wake"]["to"] == ROUTER
    assert w["data"]["routed"]["by"] == "wake-on-answer" and w["data"]["routed"]["at"]
    assert "answer" not in w["data"]  # the owner's answer is never rewritten
    assert out["fallback"] == {}


def test_judge_held_writes_wake_only(woa):
    plan, out = _judge(woa, {"q1": card()}, SEND_QUEUED, search_hits())
    assert out["states"] == {"q1": woa.HELD}
    [w] = out["writes"]
    assert w["data"]["wake"]["state"] == "HELD" and "routed" not in w["data"]
    assert out["fallback"] == {}


def test_judge_undelivered_writes_a_durable_note(woa):
    plan, out = _judge(woa, {"q1": card()}, SEND_NOT_FOUND, search_hits())
    assert out["states"] == {"q1": woa.UNDELIVERED}
    [w] = out["writes"]
    assert w["data"]["wake"]["state"] == "UNDELIVERED" and "routed" not in w["data"]
    note = out["fallback"]["q1"]
    assert note["to"] == ROUTER and note["answer"] == "A" and note["state"] == "UNDELIVERED"


def test_judge_with_no_send_result_and_no_search_is_unknown(woa):
    """A check that cannot see its subject prints UNKNOWN; it does not pass."""
    plan = woa.make_plan({"q1": card()}, ROUTER, now="2026-10-14T02:00:00Z")
    out = woa.judge(plan, {}, {}, now="2026-10-14T02:01:00Z", versions={"q1": 2})
    assert out["states"] == {"q1": woa.UNKNOWN}
    assert "UNKNOWN" in out["summary"] and "DELIVERED=0" in out["summary"]


def test_judge_does_not_write_a_card_it_cannot_pin(woa):
    plan, out = _judge(woa, {"q1": card()}, SEND_DELIVERED, search_hits(ROUTER), versions={})
    assert out["writes"] == [] and out["unpinned"] == ["q1"]


def test_a_recheck_turns_held_into_delivered_once_the_target_shows_it(woa):
    c = card(wake={"state": "HELD", "answered_at": "2026-10-14T01:45:40.495Z", "to": ROUTER,
                   "delivery": "queued", "first_sent_at": "2026-10-14T01:50:00Z", "sends": 1})
    plan = woa.make_plan({"q1": c}, ROUTER, now="2026-10-14T02:00:00Z")
    assert plan["sends"] == [] and [r["card"] for r in plan["rechecks"]] == ["q1"]
    tok = plan["rechecks"][0]["search_token"]
    out = woa.judge(plan, {}, {tok: search_hits(ROUTER)}, now="2026-10-14T02:00:00Z", versions={"q1": 3})
    assert out["states"] == {"q1": woa.DELIVERED} and out["writes"][0]["data"]["wake"]["sends"] == 1


def test_a_recheck_past_the_limit_is_undelivered_with_a_note(woa):
    c = card(wake={"state": "HELD", "answered_at": "2026-10-14T01:45:40.495Z", "to": ROUTER,
                   "delivery": "queued", "first_sent_at": "2026-10-13T20:00:00Z", "sends": 1})
    plan = woa.make_plan({"q1": c}, ROUTER, now="2026-10-14T02:00:00Z")
    tok = plan["rechecks"][0]["search_token"]
    out = woa.judge(plan, {}, {tok: search_hits()}, now="2026-10-14T02:00:00Z", versions={"q1": 3})
    assert out["states"] == {"q1": woa.UNDELIVERED} and "q1" in out["fallback"]


def test_the_card_never_carries_the_token(woa):
    """The token is the evidence. If the card held it, a router that read the card would show it in its
    transcript and a message that never arrived would read as delivered."""
    c = card()
    plan, out = _judge(woa, {"q1": c}, SEND_QUEUED, search_hits())
    tok = woa.card_token("q1", c, ROUTER)
    assert tok not in json.dumps(out["writes"]) and tok not in json.dumps(out["fallback"])


# ---- the command line, end to end over files ----------------------------------------------------

def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)


def _cards_dir(tmp_path, cards):
    d = tmp_path / "cards" / "questions"
    d.mkdir(parents=True)
    for cid, c in cards.items():
        (d / f"{cid}.json").write_text(json.dumps(c), encoding="utf-8")
    return d


def test_cli_plan_then_judge(tmp_path):
    d = _cards_dir(tmp_path, {"q1": card()})
    cur = tmp_path / "current.json"
    cur.write_text(json.dumps({"session_id": ROUTER, "incarnation": 53}), encoding="utf-8")
    plan = tmp_path / "plan.json"
    run = _run("plan", "--cards", d, "--count", 1, "--router-current", cur, "--now", "2026-10-14T02:00:00Z", "--out", plan)
    assert run.returncode == 0, run.stderr
    assert "PIN cards=q1" in run.stdout  # the session pins exactly these versions
    p = json.loads(plan.read_text(encoding="utf-8"))
    [send] = p["sends"]
    work = tmp_path / "work"
    (work / "sent").mkdir(parents=True)
    (work / "seen").mkdir()
    (work / "sent" / f"{send['search_token']}.txt").write_text(SEND_DELIVERED, encoding="utf-8")
    (work / "seen" / f"{send['search_token']}.txt").write_text(search_hits(ROUTER), encoding="utf-8")
    (work / "versions.json").write_text(json.dumps({"q1": 2}), encoding="utf-8")
    out = tmp_path / "out"
    run = _run("judge", "--plan", plan, "--work", work, "--now", "2026-10-14T02:01:00Z", "--out", out)
    assert run.returncode == 0, run.stderr
    assert run.stdout.strip().splitlines()[-1].startswith("WAKE-PASS DELIVERED=1 HELD=0 UNDELIVERED=0 UNKNOWN=0")
    assert json.loads((out / "writes.json").read_text(encoding="utf-8"))[0]["doc_id"] == "q1"
    [entry] = json.loads((out / "batch.json").read_text(encoding="utf-8"))
    assert "data" not in entry and entry["if_version"] == 2 and entry["doc_id"] == "q1"
    assert json.loads(open(entry["file_path"], encoding="utf-8").read())["wake"]["state"] == "DELIVERED"


def test_cli_plan_says_unknown_when_the_files_do_not_match_the_count(tmp_path):
    d = _cards_dir(tmp_path, {"q1": card()})
    cur = tmp_path / "current.json"
    cur.write_text(json.dumps({"session_id": ROUTER}), encoding="utf-8")
    run = _run("plan", "--cards", d, "--count", 3, "--router-current", cur, "--out", tmp_path / "plan.json")
    assert run.returncode == 2 and "UNKNOWN" in run.stdout


def test_cli_plan_with_a_true_empty_read_is_nothing_to_do(tmp_path):
    cur = tmp_path / "current.json"
    cur.write_text(json.dumps({"session_id": ROUTER}), encoding="utf-8")
    run = _run("plan", "--cards", tmp_path / "missing", "--count", 0, "--router-current", cur, "--out", tmp_path / "plan.json")
    assert run.returncode == 0 and "nothing to deliver" in run.stdout


def test_cli_plan_without_a_router_file_is_unknown(tmp_path):
    d = _cards_dir(tmp_path, {"q1": card()})
    run = _run("plan", "--cards", d, "--count", 1, "--router-current", tmp_path / "nope.json", "--out", tmp_path / "plan.json")
    assert run.returncode == 2 and "UNKNOWN" in run.stdout


def test_cli_judge_exit_codes(tmp_path):
    """0 every card delivered (or nothing to do), 1 any undelivered, 2 any held or unknown."""
    d = _cards_dir(tmp_path, {"q1": card()})
    cur = tmp_path / "current.json"
    cur.write_text(json.dumps({"session_id": ROUTER}), encoding="utf-8")
    plan = tmp_path / "plan.json"
    _run("plan", "--cards", d, "--count", 1, "--router-current", cur, "--now", "2026-10-14T02:00:00Z", "--out", plan)
    tok = json.loads(plan.read_text(encoding="utf-8"))["sends"][0]["search_token"]
    for text, code in ((SEND_NOT_FOUND, 1), (SEND_QUEUED, 2), (None, 2)):
        work = tmp_path / f"w{code}{text is None}"
        (work / "sent").mkdir(parents=True)
        (work / "seen").mkdir()
        if text is not None:
            (work / "sent" / f"{tok}.txt").write_text(text, encoding="utf-8")
            (work / "seen" / f"{tok}.txt").write_text(search_hits(), encoding="utf-8")
        (work / "versions.json").write_text(json.dumps({"q1": 2}), encoding="utf-8")
        run = _run("judge", "--plan", plan, "--work", work, "--now", "2026-10-14T02:01:00Z", "--out", tmp_path / "o")
        assert run.returncode == code, (text, run.stdout, run.stderr)
