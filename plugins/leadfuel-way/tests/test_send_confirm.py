"""send_confirm.py: a session messages another and learns whether it landed.

The send-result strings are the ones measured on 2026-10-13 and recorded in test_wake_on_answer.py (the
classifier is that script's, imported). What is new here is the plan, the next step, and the fallback.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from kit import PLUGIN, load_module
from test_wake_on_answer import (SEND_DELIVERED, SEND_HELD_NOTICE, SEND_NOT_FOUND, SEND_QUEUED, SEND_SELF,
                                 search_hits)

SCRIPT = PLUGIN / "scripts" / "send_confirm.py"
ME = "local_b9c3638b-4980-4c9d-9a83-c8ce0c44063b"
TARGET = "local_f2423ffb-4885-4c30-89a9-0f3789ffe900"
OTHER = "local_11111111-2222-4333-8444-555555555555"
T0 = "2026-10-20T10:00:00Z"
SEND_TRANSIENT = "Message not delivered: the app could not reach the session. (delivery: undelivered; message_id: 1a2b3c4d)"


@pytest.fixture(scope="module")
def sc():
    return load_module(SCRIPT, "send_confirm_under_test")


def plan(sc, **kw):
    args = dict(sender=ME, target=TARGET, subject="STATUS: proof | NODE~X | no PR", body="all good", now=T0)
    args.update(kw)
    p = sc.make_plan(**args)
    assert not p["errors"], p
    return p


# ---- prepare -------------------------------------------------------------------------------------

def test_the_plan_stamps_a_token_into_the_text(sc):
    p = plan(sc)
    assert p["token"].startswith("MSG-") and p["token"] in p["text"]
    assert p["text"].splitlines()[0] == f"MSG {p['token']} from {ME} | {p['subject']}"
    assert "all good" in p["text"] and "ignore this copy" in p["text"]


def test_the_token_changes_with_the_message_and_the_moment(sc):
    a, b = plan(sc), plan(sc, body="different")
    assert a["token"] != b["token"] != plan(sc, now="2026-10-20T10:01:00Z")["token"]
    assert plan(sc)["token"] == a["token"]  # a resend reuses the prepared file, and the token is stable


@pytest.mark.parametrize("kw, fragment", [
    (dict(target="NODE · one-interface part · 1"), "--to must be"),   # a name is held across permission modes
    (dict(target="local_nope"), "--to must be"),
    (dict(sender="self"), "--from must be"),
    (dict(target=ME), "cannot message itself"),
    (dict(subject=""), "--subject is required"),
    (dict(subject="x" * 121), "--subject is 121"),
    (dict(body="   \n"), "body is empty"),
])
def test_the_plan_refuses_what_cannot_land(sc, kw, fragment):
    args = dict(sender=ME, target=TARGET, subject="s", body="b", now=T0)
    args.update(kw)
    errors = sc.make_plan(**args)["errors"]
    assert errors and any(fragment in e for e in errors), errors


def test_warnings_for_a_long_body_and_for_nearing_the_send_pause(sc):
    p = plan(sc, body="x" * 1600, sends_so_far=8)
    assert any("1600 characters" in w for w in p["warnings"])
    assert any("pauses after 10" in w for w in p["warnings"])
    assert plan(sc)["warnings"] == []


# ---- judge: state and next step -------------------------------------------------------------------

def run(sc, sent, seen, attempts=1, now="2026-10-20T10:05:00Z", p=None):
    return sc.judge(p or plan(sc), sent, seen, attempts=attempts, now=now)


def test_delivered_only_when_the_target_holds_the_token(sc):
    r = run(sc, SEND_DELIVERED, search_hits(TARGET))
    assert (r["state"], r["next"]) == ("DELIVERED", "DONE") and "fallback" not in r


def test_the_tool_saying_delivered_is_a_claim_not_a_pass(sc):
    """The sender's own transcript holds the token too: only a hit in the TARGET counts."""
    for seen in (search_hits(OTHER, ME), "No matching sessions found.", None):
        r = run(sc, SEND_DELIVERED, seen)
        assert r["state"] == "UNKNOWN" and r["next"] == "RECHECK", seen


@pytest.mark.parametrize("sent", [SEND_QUEUED, SEND_HELD_NOTICE])
def test_a_queued_or_held_message_is_held_and_never_resent(sc, sent):
    r = run(sc, sent, "No matching sessions found.")
    assert (r["state"], r["next"]) == ("HELD", "RECHECK")


def test_a_held_message_that_later_shows_up_becomes_delivered(sc):
    r = run(sc, SEND_QUEUED, search_hits(TARGET), now="2026-10-20T10:40:00Z")
    assert r["state"] == "DELIVERED"


def test_a_held_message_past_the_limit_falls_back_and_is_not_resent(sc):
    r = run(sc, SEND_QUEUED, "No matching sessions found.", now="2026-10-20T12:30:00Z")
    assert (r["state"], r["next"]) == ("UNDELIVERED", "FALLBACK")
    assert sc.HOLD_LIMIT_MIN == 120


@pytest.mark.parametrize("sent", [SEND_NOT_FOUND, SEND_SELF])
def test_a_missing_target_or_a_message_to_yourself_goes_straight_to_the_fallback(sc, sent):
    r = run(sc, sent, "No matching sessions found.")
    assert (r["state"], r["next"], r["reason"]) == ("UNDELIVERED", "FALLBACK", "permanent")


def test_a_transient_failure_is_resent_once_then_falls_back(sc):
    first = run(sc, SEND_TRANSIENT, "No matching sessions found.")
    assert (first["state"], first["next"], first["reason"]) == ("UNDELIVERED", "RESEND", "transient")
    second = run(sc, SEND_TRANSIENT, "No matching sessions found.", attempts=2)
    assert (second["state"], second["next"]) == ("UNDELIVERED", "FALLBACK")


def test_a_silent_send_is_unknown_and_resent_once(sc):
    for sent in (None, "", "the tool timed out"):
        r = run(sc, sent, "No matching sessions found.")
        assert (r["state"], r["next"]) == ("UNKNOWN", "RESEND"), sent
    assert run(sc, None, "No matching sessions found.", attempts=2)["next"] == "FALLBACK"


def test_a_search_that_cannot_be_read_never_passes(sc):
    r = run(sc, SEND_DELIVERED, "search blew up")
    assert r["state"] == "UNKNOWN" and r["seen"] is None


def test_a_resend_that_lands_is_delivered_even_after_a_failed_first_send(sc):
    r = run(sc, SEND_DELIVERED, search_hits(TARGET), attempts=2)
    assert r["state"] == "DELIVERED" and r["next"] == "DONE"


# ---- the fallback record --------------------------------------------------------------------------

def test_the_fallback_carries_ids_and_status_never_the_body(sc):
    p = plan(sc, body="a private detail that must not reach a public PR comment")
    r = run(sc, SEND_NOT_FOUND, "No matching sessions found.", p=p)
    rec = r["fallback"][p["token"]]
    assert rec["from"] == ME and rec["to"] == TARGET and rec["subject"] == p["subject"] and rec["state"] == "UNDELIVERED"
    blob = json.dumps(r)
    assert "private detail" not in blob
    assert p["token"] in r["pr_comment"] and "private detail" not in r["pr_comment"]


# ---- command line ---------------------------------------------------------------------------------

def cli(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8")


def test_the_cli_round_trip(tmp_path):
    body = tmp_path / "body.txt"
    body.write_text("hello router", encoding="utf-8")
    out = tmp_path / "w"
    r = cli("prepare", "--from", ME, "--to", TARGET, "--subject", "STATUS: proof", "--body-file", body,
            "--out", out, "--now", T0)
    assert r.returncode == 0, r.stderr
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith("SEND "))
    token = line.split("token=")[1].split()[0]
    assert (out / f"msg-{token}.txt").read_text(encoding="utf-8").startswith(f"MSG {token} from {ME}")

    sent, seen = tmp_path / "sent.txt", tmp_path / "seen.txt"
    sent.write_text(SEND_NOT_FOUND, encoding="utf-8")
    seen.write_text("No matching sessions found.", encoding="utf-8")
    j = cli("judge", "--plan", out / "plan.json", "--sent", sent, "--seen", seen, "--out", out / "out",
            "--now", "2026-10-20T10:02:00Z")
    assert j.returncode == 1 and "UNDELIVERED next=FALLBACK" in j.stdout
    assert json.loads((out / "out" / "fallback.json").read_text(encoding="utf-8"))[token]["to"] == TARGET
    assert (out / "out" / "pr-comment.txt").is_file()

    sent.write_text(SEND_DELIVERED, encoding="utf-8")
    seen.write_text(search_hits(TARGET), encoding="utf-8")
    ok = cli("judge", "--plan", out / "plan.json", "--sent", sent, "--seen", seen)
    assert ok.returncode == 0 and "DELIVERED next=DONE" in ok.stdout

    sent.write_text(SEND_QUEUED, encoding="utf-8")
    seen.write_text("No matching sessions found.", encoding="utf-8")
    held = cli("judge", "--plan", out / "plan.json", "--sent", sent, "--seen", seen, "--now", "2026-10-20T10:02:00Z")
    assert held.returncode == 2 and "HELD next=RECHECK" in held.stdout


def test_the_cli_refuses_a_name_and_an_unreadable_plan(tmp_path):
    body = tmp_path / "body.txt"
    body.write_text("x", encoding="utf-8")
    r = cli("prepare", "--from", ME, "--to", "ROUTER #92", "--subject", "s", "--body-file", body, "--out", tmp_path / "w")
    assert r.returncode == 2 and "REFUSED" in r.stdout and not (tmp_path / "w").exists()
    bad = cli("judge", "--plan", tmp_path / "missing.json", "--sent", body, "--seen", body)
    assert bad.returncode == 2 and "UNKNOWN" in bad.stdout


def test_it_imports_the_watchers_classifier_instead_of_copying_it(sc):
    woa = load_module(PLUGIN / "scripts" / "wake_on_answer.py", "woa_for_identity")
    assert sc.W.parse_send(SEND_QUEUED) == woa.parse_send(SEND_QUEUED)
    assert "def parse_send" not in SCRIPT.read_text(encoding="utf-8")
