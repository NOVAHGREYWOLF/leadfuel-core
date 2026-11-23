"""phone_cards.py: the bridge that carries Router desk cards to the owner's phone and his answers back (G39, piece D).

Three things are proved here and not assumed. (1) Law 9: with the gate off nothing opens a connection, and no
token or account ever reaches a printed line. (2) A check that cannot see its subject says UNKNOWN: a short read
never withdraws cards, a hub answer that cannot be read applies no answer. (3) A phone answer looks to the wake
pass like a click on the page, written through the same batch entry wake_on_answer.py judge writes, and the desk
wins a clash.

The hub's wire shapes are from its source (`owner_cards.py`, the sync and ack routes); nothing here calls it.
The servers below are local stand-ins on 127.0.0.1.
"""
from __future__ import annotations

import ast
import http.server
import json
import os
import re
import socket
import subprocess
import sys
import threading
import time
import urllib.request

import pytest

from kit import PLUGIN, load_module

SCRIPT = PLUGIN / "scripts" / "phone_cards.py"
ME = "local_17e8ba63-4dd2-4846-8c8a-629b9c3750b2"
ROUTER = "local_76d5692d-6b97-4e58-b6bf-4cd6509f0fd6"

# Test values only. The account is built in pieces: this file ships in a public repo, which carries no email.
TOKEN = "tok-" + "9f3a7c1e5b2d4a60"
ACCOUNT = "owner" + "@" + "example.test"
ENV_NAMES = ("PHONE_CARDS_PUSH", "PHONE_CARDS_URL", "PHONE_CARDS_TOKEN", "PHONE_CARDS_ACCOUNT")

# The contract's card keys, and the keys the desk holds that must never leave.
WIRE_KEYS = {"id", "n", "kind", "title", "say", "why", "check", "asker", "posted", "default", "default_reason",
             "options", "effects", "guide"}
NEVER_SENT = ("asker_session", "wake", "routed", "answer", "answered_at", "note", "links", "status", "plain", "by_default")


@pytest.fixture(scope="module")
def pc():
    return load_module(SCRIPT, "phone_cards_under_test")


@pytest.fixture(scope="module")
def post_card():
    return load_module(PLUGIN / "scripts" / "post_card.py", "post_card_for_phone_tests")


@pytest.fixture(scope="module")
def woa():
    return load_module(PLUGIN / "scripts" / "wake_on_answer.py", "wake_for_phone_tests")


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    for name in ENV_NAMES:
        monkeypatch.delenv(name, raising=False)


def gate_on(monkeypatch, url="https://hub.example.test"):
    monkeypatch.setenv("PHONE_CARDS_PUSH", "1")
    monkeypatch.setenv("PHONE_CARDS_URL", url)
    monkeypatch.setenv("PHONE_CARDS_TOKEN", TOKEN)
    monkeypatch.setenv("PHONE_CARDS_ACCOUNT", ACCOUNT)


def desk_card(post_card, n=9617, **over):
    """A card exactly as post_card.py builds it: the shape the live cards have."""
    args = dict(n=n, asker="NODE · phone cards part · 1", asker_session=ME, title=f"Should it {n}?", say="Make it so?",
                why="Because.", check="verified: read the code.", options=[("A", "Yes"), ("B", "No")], default="A",
                default_reason="Safer.")
    args.update(over)
    return post_card.build_card(**args)


def write_cards(tmp_path, cards: dict, name="cards"):
    d = tmp_path / name / "questions"
    d.mkdir(parents=True, exist_ok=True)
    for cid, card in cards.items():
        (d / f"{cid}.json").write_text(json.dumps(card), encoding="utf-8")
    return d


def run(pc, capsys, *args):
    """(exit code, everything printed) for an in-process run."""
    code = pc.main([str(a) for a in args])
    cap = capsys.readouterr()
    return code, cap.out + cap.err


def no_secrets(text):
    assert TOKEN not in text and ACCOUNT not in text and ACCOUNT.split("@")[0] + "@" not in text


# ---- a stand-in hub on localhost ---------------------------------------------------------------------------

class Hub:
    """Records every request and answers from `reply(path, n)` -> (status, headers, body bytes)."""

    def __init__(self, reply):
        self.requests, self.reply = [], reply
        hub = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                size = int(self.headers.get("Content-Length") or 0)
                body = self.rfile.read(size)
                hub.requests.append({"path": self.path, "headers": {k.lower(): v for k, v in self.headers.items()},
                                     "body": body})
                status, headers, payload = hub.reply(self.path, len(hub.requests))
                self.send_response(status)
                for k, v in headers.items():
                    self.send_header(k, v)
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, *args):
                pass

        self.server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.server.daemon_threads = True
        threading.Thread(target=self.server.serve_forever, daemon=True).start()

    @property
    def url(self):
        return f"http://127.0.0.1:{self.server.server_address[1]}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()


def json_reply(obj, status=200):
    return lambda path, n: (status, {"Content-Type": "application/json"}, json.dumps(obj).encode("utf-8"))


@pytest.fixture
def hub():
    made = []

    def make(reply):
        h = Hub(reply)
        made.append(h)
        return h

    yield make
    for h in made:
        h.close()


OK_SYNC = {"ok": True, "upserted": 1, "withdrawn": 0, "skipped": 0, "withdraw_applied": True, "answers": []}


def payload_file(tmp_path, cards, complete=True):
    path = tmp_path / "payload.json"
    path.write_text(json.dumps({"cards": cards, "complete": complete}), encoding="utf-8")
    return path


def wire_card(pc, post_card, n=1):
    return pc.desk_to_wire(f"q{n}", desk_card(post_card, n=n))


# ---- the gate: nothing leaves unless the owner switched it on -------------------------------------------------

@pytest.mark.parametrize("missing", [
    ["PHONE_CARDS_PUSH"], ["PHONE_CARDS_URL"], ["PHONE_CARDS_TOKEN"], ["PHONE_CARDS_ACCOUNT"],
    ["PHONE_CARDS_PUSH", "PHONE_CARDS_URL", "PHONE_CARDS_TOKEN", "PHONE_CARDS_ACCOUNT"],
])
def test_status_names_what_is_missing_and_never_a_value(pc, capsys, monkeypatch, missing):
    gate_on(monkeypatch)
    for name in missing:
        monkeypatch.delenv(name)
    code, text = run(pc, capsys, "status")
    assert code == 0 and text.strip() == "PHONE-CARDS OFF: " + ", ".join(n for n in ENV_NAMES if n in missing)
    no_secrets(text)


@pytest.mark.parametrize("push_value", ["", "0", "true", "yes", "11", " 0 "])
def test_push_is_off_unless_it_is_exactly_one(pc, capsys, monkeypatch, push_value):
    gate_on(monkeypatch)
    monkeypatch.setenv("PHONE_CARDS_PUSH", push_value)
    code, text = run(pc, capsys, "status")
    assert code == 0 and text.strip() == "PHONE-CARDS OFF: PHONE_CARDS_PUSH"


def test_blank_values_count_as_missing(pc, capsys, monkeypatch):
    gate_on(monkeypatch)
    monkeypatch.setenv("PHONE_CARDS_URL", "   ")
    monkeypatch.setenv("PHONE_CARDS_TOKEN", "")
    code, text = run(pc, capsys, "status")
    assert code == 0 and text.strip() == "PHONE-CARDS OFF: PHONE_CARDS_URL, PHONE_CARDS_TOKEN"


def test_status_on_says_only_on(pc, capsys, monkeypatch):
    gate_on(monkeypatch)
    code, text = run(pc, capsys, "status")
    assert code == 0 and text.strip() == "PHONE-CARDS ON"
    no_secrets(text)


@pytest.fixture
def tripwire(monkeypatch):
    """Any attempt to open a connection is recorded and fails. A test then asserts the record is empty."""
    calls = []

    def boom(*args, **kwargs):
        calls.append(args)
        raise AssertionError("a network call was made")

    monkeypatch.setattr(socket.socket, "connect", boom)
    monkeypatch.setattr(socket.socket, "connect_ex", boom)
    monkeypatch.setattr(socket, "create_connection", boom)
    monkeypatch.setattr(socket, "getaddrinfo", boom)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", boom)
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    return calls


@pytest.mark.parametrize("off", [
    {"PHONE_CARDS_PUSH": None}, {"PHONE_CARDS_PUSH": "0"}, {"PHONE_CARDS_URL": None}, {"PHONE_CARDS_TOKEN": None},
    {"PHONE_CARDS_ACCOUNT": None}, {"PHONE_CARDS_URL": "", "PHONE_CARDS_TOKEN": None},
])
def test_push_and_ack_with_the_gate_off_open_no_connection(pc, capsys, monkeypatch, tmp_path, tripwire, post_card, off):
    gate_on(monkeypatch)
    for name, value in off.items():
        monkeypatch.delenv(name) if value is None else monkeypatch.setenv(name, value)
    payload = payload_file(tmp_path, [wire_card(pc, post_card)])
    out = tmp_path / "resp.json"
    code, text = run(pc, capsys, "push", "--payload", payload, "--out", out)
    assert code == 0 and text.startswith("PHONE-CARDS OFF: ") and not out.exists()
    code, text2 = run(pc, capsys, "ack", "--ids", "q1,q2", "--out", tmp_path / "ack.json")
    assert code == 0 and text2.startswith("PHONE-CARDS OFF: ") and not (tmp_path / "ack.json").exists()
    assert tripwire == []
    no_secrets(text + text2)


def test_the_tripwire_really_trips(tripwire):
    """The gate tests above are only as good as their tripwire: prove it fires on a connect and on urlopen."""
    with pytest.raises(AssertionError):
        socket.create_connection(("127.0.0.1", 9))
    with pytest.raises(AssertionError):
        urllib.request.urlopen("http://127.0.0.1:9/")
    assert len(tripwire) == 2


@pytest.mark.parametrize("url", [
    "http://hub.example.test", "ftp://hub.example.test", "hub.example.test", "https://", "https://u:p@hub.example.test",
    "https://hub.example.test/?a=1", "https://hub.example.test/#x", "http://192.0.2.1", "https://hub.example.test:notaport",
])
def test_a_url_that_is_not_allowed_is_unknown_and_opens_no_connection(pc, capsys, monkeypatch, tmp_path, tripwire, post_card, url):
    gate_on(monkeypatch, url)
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]),
                     "--out", tmp_path / "resp.json")
    assert code == 2 and text.startswith("PHONE-CARDS UNKNOWN: PHONE_CARDS_URL must be") and tripwire == []
    assert url not in text and "hub.example" not in text
    no_secrets(text)


@pytest.mark.parametrize("url, base", [
    ("https://hub.example.test", "https://hub.example.test"),
    ("https://hub.example.test/", "https://hub.example.test"),
    ("https://hub.example.test/api/", "https://hub.example.test/api"),
    ("http://localhost:8080", "http://localhost:8080"),
    ("http://127.0.0.1:5000/", "http://127.0.0.1:5000"),
    ("http://[::1]:5000", "http://[::1]:5000"),
    ("HTTP://LOCALHOST", "http://localhost"),
])
def test_https_is_required_except_for_localhost(pc, url, base):
    got = pc.hub_base(url)
    assert got is not None and got.lower() == base.lower()


@pytest.mark.parametrize("secret_env", ["PHONE_CARDS_TOKEN", "PHONE_CARDS_ACCOUNT"])
def test_a_secret_a_header_cannot_carry_is_unknown_and_never_printed(pc, capsys, monkeypatch, tmp_path, tripwire, post_card, secret_env):
    gate_on(monkeypatch)
    bad = "line1\nline2-" + TOKEN
    monkeypatch.setenv(secret_env, bad)
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]),
                     "--out", tmp_path / "resp.json")
    assert code == 2 and "UNKNOWN" in text and secret_env in text and tripwire == []
    assert "line1" not in text and TOKEN not in text


def test_the_request_timeout_is_twenty_seconds(pc):
    assert pc.TIMEOUT == 20


# ---- plan: which desk cards go, and in what shape --------------------------------------------------------------

def test_plan_reads_the_layout_the_wake_pass_reads(pc, tmp_path, capsys, post_card):
    """`<out_dir>/questions/<id>.json`, one JSON object per card, the id is the file name, `--count` is the N the query reported."""
    d = write_cards(tmp_path, {"q9617": desk_card(post_card, 9617), "q9618": desk_card(post_card, 9618)})
    out = tmp_path / "payload.json"
    code, text = run(pc, capsys, "plan", "--cards", d, "--count", 2, "--out", out)
    body = json.loads(out.read_text(encoding="utf-8"))
    assert code == 0 and set(body) == {"cards", "complete"} and body["complete"] is True
    assert [c["id"] for c in body["cards"]] == ["q9618", "q9617"]  # newest n first
    assert "sending=2" in text and "complete=true" in text


def test_the_wire_card_carries_the_contract_keys_and_nothing_else(pc, post_card):
    card = desk_card(post_card, 9617, effects={"A": "does it", "b": "does not"}, verdicts={"B": "reject"})
    card.update({"wake": {"state": "HELD"}, "answer": None, "routed": None, "note": "n", "status": "open",
                 "links": [{"label": "x", "url": "https://example.test"}], "by_default": False, "surprise": 1})
    wire = pc.desk_to_wire("q9617", card)
    assert set(wire) <= WIRE_KEYS and {"id", "n", "kind", "title", "say", "why", "check", "asker", "posted", "default",
                                       "default_reason", "options", "effects"} <= set(wire)
    for key in NEVER_SENT + ("surprise",):
        assert key not in wire
    assert wire["say"] == "Make it so?" and wire["effects"] == {"A": "does it", "B": "does not"}
    assert wire["n"] == 9617 and wire["kind"] == "choice" and wire["default"] == "A"
    assert [set(o) for o in wire["options"]] == [{"key", "label"}, {"key", "label", "verdict"}, {"key", "label"}]
    assert wire["options"][1]["verdict"] == "reject"
    assert ME not in json.dumps(wire)


def test_option_x_never_carries_a_verdict_even_if_the_desk_card_does(pc, post_card):
    card = desk_card(post_card)
    card["options"][-1]["verdict"] = "approve"
    wire = pc.desk_to_wire("q1", card)
    assert wire["options"][-1]["key"] == "X" and "verdict" not in wire["options"][-1]


def test_an_unknown_verdict_is_dropped_not_sent(pc, post_card):
    card = desk_card(post_card)
    card["options"][0]["verdict"] = "yes please"
    assert "verdict" not in pc.desk_to_wire("q1", card)["options"][0]


def test_the_session_id_never_leaves_even_inside_the_text(pc, post_card):
    sid = "local_11111111-2222-4333-8444-555555555555"
    card = desk_card(post_card, asker=f"NODE desk {sid} asked", why=f"see {sid}", check=f"read by {sid}")
    wire = pc.desk_to_wire("q1", card)
    assert "local_" not in json.dumps(wire) and "[session id]" in wire["asker"]


def test_a_step_card_keeps_its_guide_and_never_its_links(pc, post_card):
    card = desk_card(post_card, kind="step", guide=["Open the app.", "Tap done."], links=[("Router desk", "https://example.test/x")])
    wire = pc.desk_to_wire("q1", card)
    assert wire["kind"] == "step" and wire["guide"] == ["Open the app.", "Tap done."] and "links" not in wire


def test_plan_sends_only_cards_nobody_has_answered(pc, tmp_path, capsys, post_card):
    answered = dict(desk_card(post_card, 1), answer="A", answered_at="2026-11-23T20:00:00.000Z")
    gone = dict(desk_card(post_card, 2), status="withdrawn")
    not_yet = dict(desk_card(post_card, 3, kind="step"), answer="not_yet")  # wake: a step card's not_yet is not an answer
    done = dict(desk_card(post_card, 4, kind="step"), answer="done")
    open_one = desk_card(post_card, 5)
    d = write_cards(tmp_path, {"q1": answered, "q2": gone, "q3": not_yet, "q4": done, "q5": open_one})
    out = tmp_path / "payload.json"
    code, text = run(pc, capsys, "plan", "--cards", d, "--count", 5, "--out", out)
    assert [c["id"] for c in json.loads(out.read_text(encoding="utf-8"))["cards"]] == ["q5", "q3"]
    assert "answered-on-desk=2" in text and "withdrawn-on-desk=1" in text


@pytest.mark.parametrize("answer, kind", [(None, "choice"), ("A", "choice"), ("not_yet", "step"), ("done", "step"),
                                          ("not_yet", "choice"), ("", "choice")])
def test_answered_means_what_it_means_to_the_wake_pass(pc, woa, answer, kind):
    card = {"answer": answer, "kind": kind}
    assert pc.answered(card) == woa.answered(card)


@pytest.mark.parametrize("break_it", [
    lambda c: c.update(options=[]), lambda c: c.update(options=None), lambda c: c.update(options="A"),
    lambda c: c["options"].append("B"), lambda c: c["options"][0].pop("label"), lambda c: c["options"][0].update(label=" "),
    lambda c: c["options"][0].pop("key"), lambda c: c["options"][1].update(key="A"),
    lambda c: c["options"][0].update(key="TOOLONGKEY"), lambda c: c.update(title=""),
])
def test_a_card_whose_options_are_not_valid_is_not_sent_and_is_named(pc, tmp_path, capsys, post_card, break_it):
    bad = desk_card(post_card, 1)
    break_it(bad)
    d = write_cards(tmp_path, {"q1": bad, "q2": desk_card(post_card, 2)})
    out = tmp_path / "payload.json"
    code, text = run(pc, capsys, "plan", "--cards", d, "--count", 2, "--out", out)
    assert [c["id"] for c in json.loads(out.read_text(encoding="utf-8"))["cards"]] == ["q2"]
    assert "NOT SENT q1" in text


def test_text_is_cut_to_the_hubs_limits(pc, post_card):
    card = desk_card(post_card, say="s" * 900, why="w" * 2000, check="c" * 2000, posted="p" * 400, default_reason="d" * 900,
                     effects={"A": "e" * 900}, options=[("A", "l" * 500), ("B", "No")])
    wire = pc.desk_to_wire("q1", card)
    assert len(wire["say"]) == 600 and len(wire["why"]) == 1200 and len(wire["check"]) == 800
    assert len(wire["posted"]) == 140 and len(wire["default_reason"]) == 400 and len(wire["effects"]["A"]) == 300
    assert len(wire["options"][0]["label"]) == 200


def test_the_payload_is_capped_at_200_newest_first_and_is_then_not_complete(pc, post_card):
    cards = {f"q{n}": desk_card(post_card, n) for n in range(1, 251)}
    payload, rep = pc.make_payload(cards, 250, 250)
    assert len(payload["cards"]) == 200 and payload["cards"][0]["id"] == "q250" and payload["cards"][-1]["id"] == "q51"
    assert payload["complete"] is False and "did not fit" in rep["complete_reason_not"]


@pytest.mark.parametrize("count, files_extra, unreadable, limit, expect", [
    (3, 0, 0, 500, True),    # N reported, N read
    (4, 0, 0, 500, False),   # the query said 4, three are there
    (2, 1, 0, 500, False),   # a stray file beyond N
    (3, 0, 1, 500, False),   # one of the files cannot be read
    (3, 0, 0, 3, False),     # the query reached its own limit: it may have been cut off
])
def test_complete_is_true_only_when_the_whole_read_is_confirmed(pc, tmp_path, capsys, post_card, count, files_extra, unreadable, limit, expect):
    cards = {f"q{n}": desk_card(post_card, n) for n in range(1, 4 - unreadable)}
    d = write_cards(tmp_path, cards)
    for k in range(unreadable):
        (d / f"q9{k}.json").write_text("{not json", encoding="utf-8")
    for k in range(files_extra):
        (d / f"q8{k}.json").write_text(json.dumps(desk_card(post_card, 80 + k)), encoding="utf-8")
    out = tmp_path / "payload.json"
    code, text = run(pc, capsys, "plan", "--cards", d, "--count", count, "--limit", limit, "--out", out)
    assert code == 0 and json.loads(out.read_text(encoding="utf-8"))["complete"] is expect
    assert ("WARNING: complete=false" in text) is (not expect)


def test_an_empty_desk_read_is_complete_and_a_missing_folder_with_a_count_is_not(pc, tmp_path, capsys):
    out = tmp_path / "payload.json"
    run(pc, capsys, "plan", "--cards", tmp_path / "nowhere", "--count", 0, "--out", out)
    assert json.loads(out.read_text(encoding="utf-8")) == {"cards": [], "complete": True}
    run(pc, capsys, "plan", "--cards", tmp_path / "nowhere", "--count", 3, "--out", out)
    assert json.loads(out.read_text(encoding="utf-8")) == {"cards": [], "complete": False}


# ---- push: one POST, the headers, and a hub answer that must be readable -----------------------------------------

def test_push_posts_the_clean_body_with_the_two_headers_and_saves_the_answer(pc, capsys, monkeypatch, tmp_path, hub, post_card):
    h = hub(json_reply(dict(OK_SYNC, answers=[{"card_id": "q1", "key": "B", "note": "", "answered_at": "2026-11-23T20:15:03+00:00",
                                               "via": "phone", "approving": False}])))
    gate_on(monkeypatch, h.url)
    sneaky = dict(wire_card(pc, post_card, 1), asker_session=ME, wake={"state": "HELD"}, routed=None, answer="A")
    out = tmp_path / "resp.json"
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [sneaky]), "--out", out)
    assert code == 0, text
    [req] = h.requests
    assert req["path"] == "/api/owner-cards/sync"
    assert req["headers"]["x-service-token"] == TOKEN and req["headers"]["x-acting-email"] == ACCOUNT
    assert req["headers"]["content-type"] == "application/json"
    body = json.loads(req["body"])
    assert set(body) == {"cards", "complete"} and body["complete"] is True and body["cards"][0]["id"] == "q1"
    assert set(body["cards"][0]) <= WIRE_KEYS
    for key in NEVER_SENT:
        assert key not in body["cards"][0]
    assert ME not in req["body"].decode("utf-8")
    assert json.loads(out.read_text(encoding="utf-8"))["answers"][0]["key"] == "B"
    assert "answers=1" in text and "upserted=1" in text
    no_secrets(text)


def test_push_cannot_be_talked_into_sending_more_than_the_contract(pc, capsys, monkeypatch, tmp_path, hub, post_card):
    h = hub(json_reply(OK_SYNC))
    gate_on(monkeypatch, h.url)
    cards = [dict(wire_card(pc, post_card, n)) for n in range(1, 4)]
    cards[1]["options"] = []  # not a card: dropped, and then the set is not provably whole, so nothing may be withdrawn
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, cards, complete=True), "--out", tmp_path / "r.json")
    body = json.loads(h.requests[0]["body"])
    assert [c["id"] for c in body["cards"]] == ["q1", "q3"] and body["complete"] is False
    assert "WARNING" in text


def test_push_never_sends_complete_true_with_more_than_the_cap(pc, capsys, monkeypatch, tmp_path, hub, post_card):
    h = hub(json_reply(OK_SYNC))
    gate_on(monkeypatch, h.url)
    cards = [wire_card(pc, post_card, n) for n in range(1, 206)]
    run(pc, capsys, "push", "--payload", payload_file(tmp_path, cards, complete=True), "--out", tmp_path / "r.json")
    body = json.loads(h.requests[0]["body"])
    assert len(body["cards"]) == 200 and body["complete"] is False


@pytest.mark.parametrize("status, headers, payload, why", [
    (200, {}, b"<html>sign in</html>", "not a JSON object"),
    (200, {}, b"", "not a JSON object"),
    (200, {}, b"[1, 2]", "not a JSON object"),
    (200, {}, b'"ok"', "not a JSON object"),
    (200, {}, json.dumps({"ok": False, "answers": []}).encode(), "does not say ok"),
    (200, {}, json.dumps({"ok": "true", "answers": []}).encode(), "does not say ok"),
    (200, {}, json.dumps({"answers": []}).encode(), "does not say ok"),
    (200, {}, json.dumps({"ok": True}).encode(), "no answers list"),
    (200, {}, json.dumps({"ok": True, "answers": None}).encode(), "no answers list"),
    (200, {}, json.dumps({"ok": True, "answers": {"q1": "A"}}).encode(), "no answers list"),
    (503, {}, json.dumps({"ok": False, "error": "unreadable"}).encode(), "HTTP 503, error unreadable"),
    (403, {}, json.dumps({"ok": False, "error": "not_the_bridge"}).encode(), "HTTP 403, error not_the_bridge"),
    (500, {}, b"boom", "not a JSON object"),
    (503, {}, json.dumps({"ok": True, "answers": []}).encode(), "HTTP 503"),  # a 5xx with ok:true is still no answer
    (302, {"Location": "https://elsewhere.example.test/x"}, b"", "redirect"),
])
def test_a_hub_answer_that_cannot_be_read_is_unknown_and_writes_no_answers_file(pc, capsys, monkeypatch, tmp_path, hub, post_card,
                                                                               status, headers, payload, why):
    h = hub(lambda path, n: (status, dict({"Content-Type": "application/json"}, **headers), payload))
    gate_on(monkeypatch, h.url)
    out = tmp_path / "resp.json"
    out.write_text(json.dumps(dict(OK_SYNC, answers=[{"card_id": "stale"}])), encoding="utf-8")  # a left-over from an earlier pass
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", out)
    assert code == 2 and text.startswith("PHONE-CARDS UNKNOWN: ") and why in text, text
    assert not out.exists()  # a stale answers file must never be read as this push's
    assert len(h.requests) == 1  # no redirect was followed
    no_secrets(text)


def test_a_redirect_to_another_host_is_refused_and_never_followed(pc, capsys, monkeypatch, tmp_path, hub, post_card):
    elsewhere = hub(json_reply(OK_SYNC))
    h = hub(lambda path, n: (302, {"Location": elsewhere.url.replace("127.0.0.1", "localhost") + "/api/owner-cards/sync"}, b""))
    gate_on(monkeypatch, h.url)
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", tmp_path / "r.json")
    assert code == 2 and "redirect" in text and "refused" in text
    assert elsewhere.requests == [] and len(h.requests) == 1  # the token went to the configured host only
    no_secrets(text)


def test_a_slow_hub_is_unknown_not_a_hang(pc, capsys, monkeypatch, tmp_path, hub, post_card):
    def slow(path, n):
        time.sleep(1.5)
        return 200, {}, json.dumps(OK_SYNC).encode()

    h = hub(slow)
    gate_on(monkeypatch, h.url)
    monkeypatch.setattr(pc, "TIMEOUT", 0.3)
    started = time.time()
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", tmp_path / "r.json")
    assert code == 2 and "UNKNOWN" in text and time.time() - started < 5
    no_secrets(text)


def test_a_hub_that_cannot_be_reached_is_unknown_and_names_no_host(pc, capsys, monkeypatch, tmp_path, post_card):
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()  # nothing listens here now
    gate_on(monkeypatch, f"http://127.0.0.1:{port}")
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", tmp_path / "r.json")
    assert code == 2 and "could not be reached" in text and str(port) not in text
    no_secrets(text)


def test_an_exception_that_holds_the_token_is_reworded_to_its_class(pc, capsys, monkeypatch, tmp_path, post_card):
    """http.client puts the header value in its ValueError. Neither the token nor the account may reach a printed line."""
    gate_on(monkeypatch)

    class Opener:
        def open(self, req, timeout=None):
            raise ValueError(f"Invalid header value {TOKEN!r} for {ACCOUNT}")

    monkeypatch.setattr(pc, "_opener", lambda url: Opener())
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", tmp_path / "r.json")
    assert code == 2 and "ValueError" in text
    no_secrets(text)


def test_a_bug_inside_a_command_prints_a_class_name_not_a_traceback_with_the_secret(pc, capsys, monkeypatch, tmp_path, post_card):
    gate_on(monkeypatch)
    monkeypatch.setattr(pc, "_post", lambda *a, **k: (_ for _ in ()).throw(RuntimeError(f"{TOKEN} {ACCOUNT}")))
    code, text = run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", tmp_path / "r.json")
    assert code == 2 and "RuntimeError" in text and "Traceback" not in text
    no_secrets(text)


def test_the_request_is_made_with_the_twenty_second_timeout(pc, capsys, monkeypatch, tmp_path, post_card):
    gate_on(monkeypatch)
    seen = {}

    class Opener:
        def open(self, req, timeout=None):
            seen["timeout"] = timeout
            raise OSError("stop")

    monkeypatch.setattr(pc, "_opener", lambda url: Opener())
    run(pc, capsys, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", tmp_path / "r.json")
    assert seen["timeout"] == 20


@pytest.mark.parametrize("content", ["{not json", "[]", json.dumps({"cards": "x", "complete": True}),
                                     json.dumps({"cards": []}), json.dumps({"cards": [], "complete": "yes"})])
def test_a_payload_that_is_not_the_body_shape_is_unknown_and_sends_nothing(pc, capsys, monkeypatch, tmp_path, hub, content):
    h = hub(json_reply(OK_SYNC))
    gate_on(monkeypatch, h.url)
    path = tmp_path / "payload.json"
    path.write_text(content, encoding="utf-8")
    code, text = run(pc, capsys, "push", "--payload", path, "--out", tmp_path / "r.json")
    assert code == 2 and "UNKNOWN" in text and h.requests == []


# ---- ack ---------------------------------------------------------------------------------------------------------

def test_ack_posts_the_ids_once_each_and_prints_the_counts(pc, capsys, monkeypatch, tmp_path, hub):
    h = hub(json_reply({"ok": True, "delivered": 2, "ignored": 1}))
    gate_on(monkeypatch, h.url)
    out = tmp_path / "ack.json"
    code, text = run(pc, capsys, "ack", "--ids", "q1, q2,q1,,q3", "--out", out)
    [req] = h.requests
    assert code == 0 and req["path"] == "/api/owner-cards/ack"
    assert json.loads(req["body"]) == {"card_ids": ["q1", "q2", "q3"]}
    assert req["headers"]["x-service-token"] == TOKEN and req["headers"]["x-acting-email"] == ACCOUNT
    assert "acked=2 ignored=1 of 3" in text and json.loads(out.read_text(encoding="utf-8"))["delivered"] == 2
    no_secrets(text)


def test_ack_with_no_ids_sends_nothing(pc, capsys, monkeypatch, hub):
    h = hub(json_reply({"ok": True, "delivered": 0}))
    gate_on(monkeypatch, h.url)
    code, text = run(pc, capsys, "ack", "--ids", " , ")
    assert code == 0 and h.requests == [] and "nothing sent" in text


def test_ack_sends_at_most_200_ids_in_a_request(pc, capsys, monkeypatch, hub):
    h = hub(json_reply({"ok": True, "delivered": 100, "ignored": 0}))
    gate_on(monkeypatch, h.url)
    code, text = run(pc, capsys, "ack", "--ids", ",".join(f"q{n}" for n in range(450)))
    assert code == 0 and [len(json.loads(r["body"])["card_ids"]) for r in h.requests] == [200, 200, 50]
    assert "acked=300" in text


@pytest.mark.parametrize("status, payload", [
    (200, b"nope"), (200, json.dumps({"ok": True}).encode()), (200, json.dumps({"ok": False, "delivered": 1}).encode()),
    (200, json.dumps({"ok": True, "delivered": "2"}).encode()), (503, json.dumps({"ok": False, "error": "unreadable"}).encode()),
])
def test_an_ack_the_hub_does_not_confirm_is_unknown(pc, capsys, monkeypatch, tmp_path, hub, status, payload):
    h = hub(lambda path, n: (status, {}, payload))
    gate_on(monkeypatch, h.url)
    out = tmp_path / "ack.json"
    code, text = run(pc, capsys, "ack", "--ids", "q1", "--out", out)
    assert code == 2 and text.startswith("PHONE-CARDS UNKNOWN: ") and not out.exists()


# ---- apply: a phone answer becomes a desk answer, written the way wake_on_answer.py writes ------------------------

def hub_answer(card_id="q1", key="A", note="", at="2026-11-23T20:15:03.123456+00:00", via="phone", approving=False):
    return {"card_id": card_id, "key": key, "note": note, "answered_at": at, "via": via, "approving": approving}


def answers_file(tmp_path, *answers, name="resp.json"):
    path = tmp_path / name
    path.write_text(json.dumps(dict(OK_SYNC, answers=list(answers))), encoding="utf-8")
    return path


def versions_file(tmp_path, versions):
    path = tmp_path / "versions.json"
    path.write_text(json.dumps(versions), encoding="utf-8")
    return path


def apply(pc, capsys, tmp_path, answers, cards, count=None, versions=None, now="2026-11-23T20:20:00Z"):
    d = write_cards(tmp_path, cards)
    args = ["apply", "--answers", answers_file(tmp_path, *answers), "--cards", d,
            "--count", len(cards) if count is None else count, "--now", now, "--out", tmp_path / "out"]
    if versions is not None:
        args += ["--versions", versions_file(tmp_path, versions)]
    code, text = run(pc, capsys, *args)
    out = tmp_path / "out"
    return code, text, json.loads((out / "batch.json").read_text(encoding="utf-8")), json.loads((out / "ack.json").read_text(encoding="utf-8"))


def test_apply_writes_what_the_page_writes_on_a_click_plus_answered_via(pc, capsys, tmp_path, post_card):
    code, text, batch, ack = apply(pc, capsys, tmp_path, [hub_answer(note="do it, but small")], {"q1": desk_card(post_card, 1)},
                                   versions={"q1": 7})
    [entry] = batch
    data = json.loads(open(entry["file_path"], encoding="utf-8").read())
    assert data == {"answer": "A", "answered_at": "2026-11-23T20:15:03.123Z", "answered_via": "phone", "routed": None,
                    "note": "do it, but small", "note_at": "2026-11-23T20:15:03.123Z"}
    assert code == 0 and ack == {"ack_now": [], "ack_after_batch": ["q1"], "hold": []}
    assert text.strip().splitlines()[-1] == "PHONE-CARDS applied=1 conflict=0"


def test_a_phone_answer_without_a_note_writes_no_note_fields(pc, capsys, tmp_path, post_card):
    _, _, [entry], _ = apply(pc, capsys, tmp_path, [hub_answer(note="")], {"q1": desk_card(post_card, 1)}, versions={"q1": 1})
    assert set(json.loads(open(entry["file_path"], encoding="utf-8").read())) == {"answer", "answered_at", "answered_via", "routed"}


def wake_batch_entry(woa_script, tmp_path):
    """One batch.json entry as `wake_on_answer.py judge` really writes it, through its command line."""
    d = tmp_path / "wk" / "questions"
    d.mkdir(parents=True)
    card = {"answer": "A", "answered_at": "2026-10-14T01:45:40.495Z", "asker": "NODE lane for ROUTER #50", "kind": "choice",
            "routed": None, "title": "Pick one", "options": [{"key": "A", "label": "Yes"}, {"key": "C", "label": "Later"}]}
    (d / "q1.json").write_text(json.dumps(card), encoding="utf-8")
    cur = tmp_path / "wk" / "current.json"
    cur.write_text(json.dumps({"session_id": ROUTER}), encoding="utf-8")
    plan = tmp_path / "wk" / "plan.json"
    sh = lambda *a: subprocess.run([sys.executable, str(woa_script), *map(str, a)], capture_output=True, text=True,
                                   encoding="utf-8", timeout=60)
    assert sh("plan", "--cards", d, "--count", 1, "--router-current", cur, "--now", "2026-10-14T02:00:00Z", "--out", plan).returncode == 0
    send = json.loads(plan.read_text(encoding="utf-8"))["sends"][0]
    work = tmp_path / "wk" / "work"
    (work / "sent").mkdir(parents=True)
    (work / "seen").mkdir()
    (work / "sent" / f"{send['search_token']}.txt").write_text("(delivery: delivered; message_id: ab12)", encoding="utf-8")
    (work / "seen" / f"{send['search_token']}.txt").write_text(
        json.dumps([{"sessionId": ROUTER, "title": "t", "snippet": "x"}]), encoding="utf-8")
    (work / "versions.json").write_text(json.dumps({"q1": 2}), encoding="utf-8")
    assert sh("judge", "--plan", plan, "--work", work, "--now", "2026-10-14T02:01:00Z", "--out", tmp_path / "wk" / "out").returncode == 0
    [entry] = json.loads((tmp_path / "wk" / "out" / "batch.json").read_text(encoding="utf-8"))
    return entry


def test_the_batch_entry_has_the_same_shape_wake_judge_writes(pc, capsys, tmp_path, post_card):
    """The same ArtifactData batch step writes both: same keys in the same order, an `update` on `questions`, an
    `if_version` integer, and a file_path to a file of the fields to merge (no inline `data`)."""
    theirs = wake_batch_entry(PLUGIN / "scripts" / "wake_on_answer.py", tmp_path)
    _, _, [ours], _ = apply(pc, capsys, tmp_path, [hub_answer()], {"q1": desk_card(post_card, 1)}, versions={"q1": 7})
    assert list(ours) == list(theirs)  # keys and their order
    assert ours["op"] == theirs["op"] == "update" and ours["collection"] == theirs["collection"] == "questions"
    assert isinstance(ours["if_version"], int) and isinstance(theirs["if_version"], int) and ours["if_version"] == 7
    assert "data" not in ours and ours["doc_id"] == "q1"
    from pathlib import Path
    assert Path(ours["file_path"]).is_absolute() and Path(ours["file_path"]).name == "q1.json" == Path(theirs["file_path"]).name
    assert Path(ours["file_path"]).parent.name == Path(theirs["file_path"]).parent.name == "cards"


def test_a_phone_answer_reads_to_the_wake_pass_like_a_page_click(pc, woa, capsys, tmp_path, post_card):
    desk = desk_card(post_card, 1)
    _, _, [entry], _ = apply(pc, capsys, tmp_path, [hub_answer(key="B", note="no, smaller")], {"q1": desk}, versions={"q1": 3})
    merged = dict(desk, **json.loads(open(entry["file_path"], encoding="utf-8").read()))
    assert woa.pending({"q1": desk}) == []  # before: unanswered, nothing to deliver
    assert woa.pending({"q1": merged}) == [("q1", "send")]  # after: answered and unrouted, so the pass delivers it
    plan = woa.make_plan({"q1": merged}, ROUTER, now="2026-11-23T20:30:00Z")
    [send] = plan["sends"]
    assert send["to"] == ME and "q1 = B" in send["text"] and "no, smaller" in send["text"]  # to the desk that asked
    assert plan["stale"] == [] and merged["answered_via"] == "phone"


def test_the_desk_wins_when_it_answered_first(pc, capsys, tmp_path, post_card):
    desk = dict(desk_card(post_card, 1), answer="B", answered_at="2026-11-23T20:10:00.000Z")
    code, text, batch, ack = apply(pc, capsys, tmp_path, [hub_answer(key="A")], {"q1": desk}, versions={"q1": 7})
    assert code == 0 and batch == [] and ack == {"ack_now": ["q1"], "ack_after_batch": [], "hold": []}
    assert "CONFLICT q1" in text and text.strip().splitlines()[-1] == "PHONE-CARDS applied=0 conflict=1"
    assert not (tmp_path / "out" / "cards" / "q1.json").exists()  # nothing written for it


def test_the_same_phone_answer_arriving_twice_is_not_a_conflict_and_not_written_again(pc, capsys, tmp_path, post_card):
    desk = dict(desk_card(post_card, 1), answer="A", answered_via="phone", answered_at="2026-11-23T20:15:03.123Z")
    code, text, batch, ack = apply(pc, capsys, tmp_path, [hub_answer(key="A")], {"q1": desk}, versions={"q1": 7})
    assert batch == [] and ack["ack_now"] == ["q1"] and text.strip().splitlines()[-1] == "PHONE-CARDS applied=0 conflict=0"


def test_a_withdrawn_desk_card_is_a_conflict(pc, capsys, tmp_path, post_card):
    desk = dict(desk_card(post_card, 1), status="withdrawn")
    _, text, batch, ack = apply(pc, capsys, tmp_path, [hub_answer()], {"q1": desk}, versions={"q1": 7})
    assert batch == [] and ack["ack_now"] == ["q1"] and "withdrew" in text


def test_a_key_the_desk_card_does_not_have_is_a_conflict_not_a_write(pc, capsys, tmp_path, post_card):
    _, _, batch, ack = apply(pc, capsys, tmp_path, [hub_answer(key="Q")], {"q1": desk_card(post_card, 1)}, versions={"q1": 7})
    assert batch == [] and ack["ack_now"] == ["q1"]


def test_a_card_missing_from_a_whole_read_is_a_conflict_and_from_a_short_read_is_held(pc, capsys, tmp_path, post_card):
    """The query returns the unrouted cards, so a card absent from a whole read was answered and routed (or removed):
    the desk wins. From a read that is not provably whole it is unknown: not written, not acknowledged, exit 2."""
    other = {"q2": desk_card(post_card, 2)}
    whole, short = tmp_path / "whole", tmp_path / "short"
    whole.mkdir()
    short.mkdir()
    code, text, batch, ack = apply(pc, capsys, whole, [hub_answer("q1")], other, versions={"q1": 7})
    assert code == 0 and batch == [] and ack == {"ack_now": ["q1"], "ack_after_batch": [], "hold": []}
    code, text, batch, ack = apply(pc, capsys, short, [hub_answer("q1")], other, count=5, versions={"q1": 7})
    assert code == 2 and batch == [] and ack == {"ack_now": [], "ack_after_batch": [], "hold": ["q1"]} and "HOLD q1" in text


def test_no_version_means_nothing_is_written_or_acknowledged_until_one_is_given(pc, capsys, tmp_path, post_card):
    cards = {"q1": desk_card(post_card, 1)}
    code, text, batch, ack = apply(pc, capsys, tmp_path, [hub_answer()], cards)  # the first run, no versions yet
    assert code == 0 and batch == [] and ack == {"ack_now": [], "ack_after_batch": [], "hold": ["q1"]}
    assert "PIN cards=q1" in text and "NOT WRITTEN (no version to pin): q1" in text
    code, text, batch, ack = apply(pc, capsys, tmp_path, [hub_answer()], cards, versions={"q1": 4})  # the second, with them
    assert [b["if_version"] for b in batch] == [4] and ack["ack_after_batch"] == ["q1"]


def test_apply_with_a_hub_answer_that_is_not_ok_applies_nothing(pc, capsys, tmp_path, post_card):
    d = write_cards(tmp_path, {"q1": desk_card(post_card, 1)})
    for name, content in (("a.json", "<html>"), ("b.json", json.dumps({"ok": False, "answers": [hub_answer()]})),
                          ("c.json", json.dumps({"ok": True})), ("d.json", json.dumps({"ok": True, "answers": "x"})),
                          ("missing.json", None)):
        if content is not None:
            (tmp_path / name).write_text(content, encoding="utf-8")
        out = tmp_path / ("out-" + name)
        code, text = run(pc, capsys, "apply", "--answers", tmp_path / name, "--cards", d, "--count", 1, "--out", out)
        assert code == 2 and text.startswith("PHONE-CARDS UNKNOWN: ") and not out.exists(), name


def test_unreadable_answers_are_skipped_loudly_and_the_good_ones_still_apply(pc, capsys, tmp_path, post_card):
    cards = {"q1": desk_card(post_card, 1), "q2": desk_card(post_card, 2)}
    answers = [hub_answer("q1"), hub_answer("q2", via="web"), hub_answer("q3", at="yesterday"), {"card_id": "", "key": "A"}, "junk"]
    code, text, batch, ack = apply(pc, capsys, tmp_path, answers, cards, versions={"q1": 1, "q2": 1})
    assert [b["doc_id"] for b in batch] == ["q1"] and "4 answer(s)" in text and "unreadable" in text


def test_apply_without_a_readable_time_does_not_invent_one(pc, capsys, tmp_path, post_card):
    _, _, batch, ack = apply(pc, capsys, tmp_path, [hub_answer(at="")], {"q1": desk_card(post_card, 1)}, versions={"q1": 1})
    assert batch == [] and ack["ack_now"] == [] and ack["hold"] == []


def test_a_phone_answer_older_than_the_wake_age_limit_is_flagged(pc, capsys, tmp_path, post_card):
    _, text, [entry], _ = apply(pc, capsys, tmp_path, [hub_answer(at="2026-11-20T00:00:00Z")], {"q1": desk_card(post_card, 1)},
                                versions={"q1": 1})
    assert "NOTE q1" in text and "--only q1" in text


def test_apply_writes_only_under_its_out_folder(pc, capsys, tmp_path, post_card):
    before = {p for p in tmp_path.rglob("*")}
    apply(pc, capsys, tmp_path, [hub_answer()], {"q1": desk_card(post_card, 1)}, versions={"q1": 1})
    new = {p for p in tmp_path.rglob("*")} - before
    inputs = {tmp_path / "cards", tmp_path / "cards" / "questions", tmp_path / "cards" / "questions" / "q1.json",
              tmp_path / "resp.json", tmp_path / "versions.json"}
    assert all((tmp_path / "out") in p.parents or p == tmp_path / "out" or p in inputs for p in new), new


# ---- the whole path, over a real process ------------------------------------------------------------------------

def _cli(env, *args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True, encoding="utf-8",
                          timeout=60, env=env)


def _clean_env():
    return {k: v for k, v in os.environ.items() if k not in ENV_NAMES}


def test_cli_end_to_end_plan_push_apply_ack(pc, monkeypatch, tmp_path, hub, post_card):
    sync = dict(OK_SYNC, answers=[hub_answer("q9617", key="B", note="smaller")])
    h = hub(lambda path, n: (200, {}, json.dumps(sync if path.endswith("/sync") else {"ok": True, "delivered": 1, "ignored": 0}).encode()))
    env = dict(_clean_env(), PHONE_CARDS_PUSH="1", PHONE_CARDS_URL=h.url, PHONE_CARDS_TOKEN=TOKEN, PHONE_CARDS_ACCOUNT=ACCOUNT)
    d = write_cards(tmp_path, {"q9617": desk_card(post_card, 9617), "q9618": desk_card(post_card, 9618)})
    steps = [("status",), ("plan", "--cards", d, "--count", 2, "--out", tmp_path / "p.json"),
             ("push", "--payload", tmp_path / "p.json", "--out", tmp_path / "r.json"),
             ("apply", "--answers", tmp_path / "r.json", "--cards", d, "--count", 2, "--out", tmp_path / "o"),
             ("apply", "--answers", tmp_path / "r.json", "--cards", d, "--count", 2, "--versions", versions_file(tmp_path, {"q9617": 5}),
              "--out", tmp_path / "o"),
             ("ack", "--ids", "q9617")]
    texts = []
    for step in steps:
        run_ = _cli(env, *step)
        assert run_.returncode == 0, (step, run_.stdout, run_.stderr)
        texts.append(run_.stdout + run_.stderr)
    assert texts[0].strip() == "PHONE-CARDS ON"
    assert "applied=1 conflict=0" in texts[4]
    assert [r["path"] for r in h.requests] == ["/api/owner-cards/sync", "/api/owner-cards/ack"]
    for text in texts:
        no_secrets(text)


def test_cli_with_the_gate_off_prints_off_and_exits_zero(monkeypatch, tmp_path, post_card, pc):
    env = _clean_env()
    run_ = _cli(env, "push", "--payload", payload_file(tmp_path, [wire_card(pc, post_card)]), "--out", tmp_path / "r.json")
    assert run_.returncode == 0 and run_.stdout.strip() == "PHONE-CARDS OFF: " + ", ".join(ENV_NAMES)
    run_ = _cli(env, "ack", "--ids", "q1")
    assert run_.returncode == 0 and run_.stdout.startswith("PHONE-CARDS OFF: ")


# ---- Law 9, the wake skill, and the plugin ---------------------------------------------------------------------------

NETWORK_MODULES = {"socket", "http", "urllib", "requests", "httpx", "smtplib", "ftplib", "webbrowser", "ssl", "aiohttp", "telnetlib"}


def _imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    return names | {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}


def test_phone_cards_is_the_only_plugin_code_that_can_reach_the_network():
    """Law 9: one door, and the gate is in it. Every other script and the hook import nothing that opens a connection."""
    others = [p for p in list((PLUGIN / "scripts").glob("*.py")) + list((PLUGIN / "hooks").glob("*.py")) if p.name != "phone_cards.py"]
    assert len(others) >= 8
    for path in others:
        assert not _imports(path) & NETWORK_MODULES, f"{path.name} imports a network module"
    mine = _imports(SCRIPT)
    assert mine & {"urllib"} and not mine & (NETWORK_MODULES - {"urllib"})
    assert {m for m in mine if m not in sys.stdlib_module_names} == set()  # stdlib only


def test_the_gate_check_comes_before_any_request_in_push_and_ack():
    src = SCRIPT.read_text(encoding="utf-8")
    for fn in ("cmd_push", "cmd_ack"):
        body = src.split(f"def {fn}(")[1].split("\ndef ")[0]
        assert body.index("_gate_or_exit()") < body.index("_post(")


SKILL = (PLUGIN / "skills" / "wake" / "SKILL.md").read_text(encoding="utf-8")


def test_the_wake_skill_teaches_the_bridge_before_the_routing_read():
    assert "3b. **PHONE BRIDGE" in SKILL
    assert SKILL.index("\n3. **A fresh folder**") < SKILL.index("\n3b. **PHONE BRIDGE") < SKILL.index("\n4. **Read the cards.**")
    step = SKILL.split("\n3b. **PHONE BRIDGE")[1].split("\n4. **Read the cards.**")[0]
    for must in ("phone_cards.py", "PHONE_CARDS_PUSH=1", "PHONE-CARDS OFF", "versions.json", "ACK-NOW", "ACK-AFTER-BATCH",
                 "batch.json", "if_version", "PHONE-CARDS UNKNOWN", "CONFLICT", "never read it as \"no answers\""):
        assert must in step, must
    order = [m.group(1) for m in re.finditer(r'phone_cards\.py" (status|plan|push|apply|ack)\b', step)]
    assert [c for i, c in enumerate(order) if c not in order[:i]] == ["status", "plan", "push", "apply", "ack"]
    # The gate is read before anything is queried, and the ack comes after the batch write returned.
    assert step.index('phone_cards.py" status') < step.index("ArtifactData `query`")
    assert step.index("`batch`") < step.index('phone_cards.py" ack')
    assert "Only after that batch returned" in step and "Never acknowledge a card whose write failed" in step
    assert "do nothing else in this step" in step and "nothing is sent" in step


def test_the_wake_skill_no_longer_says_never_push_to_the_phone_and_keeps_the_other_never_lines():
    never = SKILL.split("\n## Never\n")[1]
    assert "never push to the phone" not in SKILL.lower()
    assert "only through `phone_cards.py`" in never and "PHONE_CARDS_PUSH=1" in never
    assert "Never change any session's permission mode" in never and "set_session_permission_mode" not in SKILL
    assert "Never run this pass from a desk" in never


def _flags(text):
    return set(re.findall(r"--[a-z][a-z-]*", text))


def test_every_command_line_the_skill_shows_uses_flags_the_script_has():
    """The skill is what a Haiku run follows. A flag it names that the parser lacks would stop the pass mid-step."""
    step = SKILL.split("\n3b. **PHONE BRIDGE")[1].split("\n4. **Read the cards.**")[0]
    shown = re.findall(r"phone_cards\.py\"? (status|plan|push|apply|ack)([^`]*)`", step)
    assert {cmd for cmd, _ in shown} == {"status", "plan", "push", "apply", "ack"}
    for cmd, rest in shown:
        helptext = subprocess.run([sys.executable, str(SCRIPT), cmd, "--help"], capture_output=True, text=True, encoding="utf-8",
                                  timeout=60).stdout
        assert _flags(rest) <= _flags(helptext), (cmd, _flags(rest) - _flags(helptext))


def test_the_readme_and_manifests_name_this_release():
    readme = (PLUGIN / "README.md").read_text(encoding="utf-8")
    assert "**The phone bridge" in readme and "0.1.25" in readme and "PHONE_CARDS_PUSH" in readme
