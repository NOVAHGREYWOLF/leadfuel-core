"""SALES K06: the dry-run harness makes the guards read the exact string that would leave, and sends nothing.

The subject is the em-dash class: a character added at send time, after the guard scored the draft. The fake
outbound app below fills tokens the way the real one does (a value is substituted into the text), so a sender
company that contains a dash puts a dash in the outgoing mail that the draft never had.
"""
import hashlib
import importlib.util
import os
import socket
import sys

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "sales", "dry_run.py")
_spec = importlib.util.spec_from_file_location("sales_dry_run", _PATH)
dr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(dr)

LONG = "We help small shops keep their books tidy and their weekends free, and we would like to show you how it works."


class FakeReach:
    """render_with_report fills {{sender_company}} and {{first_name}}; assessment flags an em-dash. Records what it read."""
    def __init__(self):
        self.read = []

    def render_with_report(self, subject, body, lead, sender, extra):
        vals = {"first_name": (lead.name or "").split(" ")[0], "sender_company": (sender or {}).get("company", "")}
        def fill(s):
            for k, v in vals.items():
                s = (s or "").replace("{{%s}}" % k, v)
            return s
        ok = bool(vals["first_name"])
        return fill(subject), fill(body), {"renderable": ok, "reason": "" if ok else "no first name"}

    def assessment(self, text):
        self.read.append(text)
        tells = [{"kind": "punctuation", "term": "em-dash"}] if "\u2014" in text else []
        return {"tells": tells, "confident": len(text.split()) >= 12}


def _draft(**kw):
    d = {"id": "d1", "subject": "Quick note", "body": f"Hi {{{{first_name}}}}, {LONG}",
         "lead": {"name": "Ana Lopez", "company": "Lopez Books"}, "sender": {"company": "Acme"}}
    d.update(kw)
    return d


def test_clean_draft_is_clean_by_this_guard_only():
    [r] = dr.dry_run(FakeReach(), [_draft()])
    assert r["verdict"] == dr.CLEAN and r["injected_at_send"] == []
    assert "Hi Ana," in r["outbound_text"]


def test_a_dash_added_by_token_fill_is_caught_though_the_draft_had_none():
    d = _draft(body=f"Hi {{{{first_name}}}}, {LONG} {{{{sender_company}}}}", sender={"company": "Acme \u2014 Books"})
    assert "\u2014" not in d["body"]
    [r] = dr.dry_run(FakeReach(), [d])
    assert r["verdict"] == dr.TELLS
    assert r["injected_at_send"] == [["punctuation", "em-dash"]]
    assert r["tells_written"] == []


def test_a_dash_added_by_a_later_send_stage_is_caught():
    stage = lambda s, b, lead: (s, b + " \u2014 sent from my phone")
    [r] = dr.dry_run(FakeReach(), [_draft()], stages=[stage])
    assert r["injected_at_send"] == [["punctuation", "em-dash"]]


def test_the_guard_reads_exactly_the_string_that_would_leave():
    reach = FakeReach()
    stage = lambda s, b, lead: (s, b + " P.S. see you soon")
    [r] = dr.dry_run(reach, [_draft()], stages=[stage])
    assert reach.read[0] == r["outbound_text"]                      # the first read is the outbound string
    assert "P.S. see you soon" in reach.read[0]                      # including what a late stage appended
    assert r["outbound_sha"] == hashlib.sha256(r["outbound_text"].encode()).hexdigest()


def test_unrenderable_lead_is_blocked_even_when_the_guard_finds_nothing():
    [r] = dr.dry_run(FakeReach(), [_draft(lead={"name": None, "company": "x"})])
    assert r["verdict"] == dr.BLOCKED and r["reason"] == "no first name"


def test_too_little_text_is_unverified_not_clean():
    [r] = dr.dry_run(FakeReach(), [_draft(body="Hi {{first_name}}.")])
    assert r["verdict"] == dr.UNVERIFIED


def test_control_a_guard_that_always_passes_would_hide_the_dash():
    class Blind(FakeReach):
        def assessment(self, text):
            return {"tells": [], "confident": True}
    d = _draft(body=f"Hi {{{{first_name}}}}, {LONG} {{{{sender_company}}}}", sender={"company": "A \u2014 B"})
    [r] = dr.dry_run(Blind(), [d])
    assert r["verdict"] == dr.CLEAN and "\u2014" in r["outbound_text"]   # what the harness would miss with a blind guard


def test_empty_drafts_say_nothing_to_show():
    assert dr.dry_run(FakeReach(), []) == []
    assert "nothing to show" in dr.render_table([])


def test_no_network_and_no_sender_module(monkeypatch):
    def no_socket(*a, **k):
        raise AssertionError("the harness opened a socket")
    monkeypatch.setattr(socket, "socket", no_socket)
    before = set(sys.modules)
    dr.dry_run(FakeReach(), [_draft(), _draft(id="d2")])
    new = set(sys.modules) - before
    assert not {m for m in new if m.split(".")[0] in {"sender", "requests", "smtplib", "anthropic", "httpx"}}


def test_load_reach_refuses_a_missing_checkout(tmp_path):
    with pytest.raises(FileNotFoundError):
        dr.load_reach(tmp_path)
    assert dr.main(["--reach", str(tmp_path), "--drafts", str(tmp_path / "d.json")]) == 2


def test_load_reach_reads_a_checkout_by_path(tmp_path):
    (tmp_path / "render.py").write_text(
        "def render_with_report(s, b, lead, sender=None, extra=None):\n    return s, b, {'renderable': True}\n")
    (tmp_path / "voice_verify.py").write_text("def assessment(t):\n    return {'tells': [], 'confident': True}\n")
    reach = dr.load_reach(tmp_path)
    [r] = dr.dry_run(reach, [{"id": 1, "subject": "s", "body": "b", "lead": {}}])
    assert r["verdict"] == dr.CLEAN


_REAL = os.environ.get("REACH_CHECKOUT", "")


@pytest.mark.skipif(not _REAL or not os.path.isfile(os.path.join(_REAL, "render.py")),
                    reason="set REACH_CHECKOUT to a reach checkout to run this test")
def test_against_the_real_reach_render_and_guard():
    reach = dr.load_reach(_REAL)
    good = {"id": "g", "subject": "A note for {{first_name}}", "body": "Hi {{first_name}}, " + LONG,
            "lead": {"name": "Ana Lopez", "company": "Lopez Books"}, "sender": {"name": "Sam", "company": "Acme"}}
    bare = {"id": "b", "subject": "Hello", "body": "Hi {{first_name}}, " + LONG, "lead": {"name": None, "company": None}}
    rows = {r["id"]: r for r in dr.dry_run(reach, [good, bare])}
    assert rows["g"]["renderable"] and "Hi Ana," in rows["g"]["outbound_text"]
    assert rows["b"]["verdict"] == dr.BLOCKED          # a bare-email lead is never sent "Hi,"
