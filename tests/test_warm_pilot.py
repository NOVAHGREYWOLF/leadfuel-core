"""WEB-H1: the warm-network pilot harness. Every person here is fictional and made in the test;
no test reads a real export. Each test runs in a temp data root outside any git tree.

What these prove: consent gates import and the model step; the ranking comes from the hub's
rules (the real file when this machine has it, a stand-in otherwise); the model step can only
reach loopback and there is no cloud path; whose export it is gets refused rather than guessed;
deletion happens at 30 days after delivery and is checked; the calibration log starts at
ranking and survives deletion only de-identified.
"""
import csv
import datetime as dt
import importlib.util
import json
import os
import sys
import tempfile
import types
import urllib.request
import zipfile

import pytest
from shutil import rmtree as _rmtree

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "pilot", "warm_pilot.py")
_spec = importlib.util.spec_from_file_location("warm_pilot", _PATH)
wp = importlib.util.module_from_spec(_spec)
sys.modules["warm_pilot"] = wp
_spec.loader.exec_module(wp)

NOW = dt.datetime(2026, 10, 30, 12, 0, tzinfo=dt.timezone.utc)
ME = "https://www.linkedin.com/in/sample-owner"
A = "https://www.linkedin.com/in/fictional-ada"      # active, relevant
B = "https://www.linkedin.com/in/fictional-bo"       # active, not relevant
C = "https://www.linkedin.com/in/fictional-cy"       # connection only, relevant
D = "https://www.linkedin.com/in/fictional-di"       # pitched me, never answered
HUB_ROUTE = wp.DEFAULT_HUB_ROUTE


@pytest.fixture
def root():
    # The system temp dir, not pytest's tmp_path: tmp_path may sit under a checkout on some
    # runners, and the harness rightly refuses a root inside a git tree.
    d = tempfile.mkdtemp(prefix="warm-pilot-test-")
    if wp._inside_git(d):
        pytest.skip("system temp dir is inside a git tree here")
    yield d
    _rmtree(d, ignore_errors=True)   # the real one, even when a test stubbed wp.shutil.rmtree


def _export(folder):
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "Connections.csv"), "w", encoding="utf-8", newline="") as fh:
        fh.write("Notes:\n\"Some notes line\"\n\n")
        w = csv.writer(fh)
        w.writerow(["First Name", "Last Name", "URL", "Email Address", "Company", "Position",
                    "Connected On"])
        w.writerow(["Ada", "Sample", A, "", "Fractional CFO Partners", "Fractional CFO", "01 Jan 2024"])
        w.writerow(["Bo", "Sample", B, "", "Bakery", "Baker", "01 Jan 2024"])
        w.writerow(["Cy", "Sample", C, "x@example.invalid", "Ops Consulting", "Consultant", "01 Jan 2024"])
        w.writerow(["Di", "Sample", D, "", "Recruiting Co", "Recruiter", "01 Jan 2024"])
    rows = []

    def msg(conv, frm, frm_url, to_urls, when, text):
        rows.append([conv, "", frm, frm_url, "", ",".join(to_urls),
                     when.strftime("%Y-%m-%d %H:%M:%S UTC"), "", text, "INBOX"])

    t = NOW - dt.timedelta(days=200)
    for i in range(6):                              # Ada: a real back-and-forth
        msg("c-ada", "Me", ME, [A], t + dt.timedelta(days=i * 10), f"Hey Ada, following up on our chat about finance ops number {i}.")
        msg("c-ada", "Ada", A, [ME], t + dt.timedelta(days=i * 10, hours=3), f"Thanks, sounds good {i}")
    for i in range(3):                              # Bo: a smaller real exchange, recent
        msg("c-bo", "Me", ME, [B], NOW - dt.timedelta(days=20 - i), f"Bo, the bread was excellent, thank you again {i}!")
        msg("c-bo", "Bo", B, [ME], NOW - dt.timedelta(days=20 - i, hours=-1), "glad you liked it")
    for i in range(4):                              # Di: one-way pitches
        msg("c-di", "Di", D, [ME], NOW - dt.timedelta(days=40 - i), "Exciting opportunity!")
    msg("c-grp", "Me", ME, [A, B], NOW - dt.timedelta(days=5), "Group hello to both of you, nice to see everyone")
    with open(os.path.join(folder, "messages.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["CONVERSATION ID", "CONVERSATION TITLE", "FROM", "SENDER PROFILE URL", "TO",
                    "RECIPIENT PROFILE URLS", "DATE", "SUBJECT", "CONTENT", "FOLDER"])
        w.writerows(rows)
    return folder


def _fake_scorer():
    """A stand-in with the hub's call shape, for machines without the hub checkout."""
    m = types.SimpleNamespace()
    m.cooccurrence = lambda groups: []

    def routes(people, target=None, *, links=(), now=None, limit=10):
        out = []
        for p in people:
            two_way = p["sent"] and p["received"]
            if not two_way and (p["sent"] or p["received"]):
                continue
            score = (p["sent"] + p["received"]) / 20.0
            out.append({"person": p["id"], "display": p["display"], "hops": 1, "via": None,
                        "warmth": score, "band": "warm" if two_way else "cold",
                        "state": "live", "relevance": 1.0, "matched": [], "score": score,
                        "why": "stand-in. Stand-in",
                        "tie": {"interactions": p["sent"] + p["received"], "sent": p["sent"],
                                "received": p["received"], "copied": p["copied"],
                                "days_since": 1}})
        out.sort(key=lambda r: -r["score"])
        return {"routes": out[:limit], "considered": len(people), "excluded": {}, "note": "fake"}
    m.routes = routes
    return m


def _ready(root, tmp, *, scopes=("local_processing",)):
    wp.init("sample", root=root, now=NOW)
    for s in scopes:
        wp.record_consent("sample", s, granted_by="customer", method="test", root=root, now=NOW)
    wp.import_export("sample", _export(os.path.join(tmp, "export")), root=root, now=NOW)


def _sheet(root):
    with open(os.path.join(root, "sample", "out", "top25.csv"), encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def test_root_inside_git_is_refused(tmp_path):
    (tmp_path / ".git").mkdir()
    with pytest.raises(wp.PilotError, match="git working tree"):
        wp.pilot_root(str(tmp_path / "data"))


def test_customer_id_must_be_a_slug(root):
    with pytest.raises(wp.PilotError, match="slug"):
        wp.init("Ada Sample", root=root)


def test_import_needs_consent(root, tmp_path):
    wp.init("sample", root=root, now=NOW)
    with pytest.raises(wp.ConsentMissing):
        wp.import_export("sample", _export(str(tmp_path / "e")), root=root, now=NOW)


def test_import_from_zip_keeps_only_the_two_files(root, tmp_path):
    src = _export(str(tmp_path / "e"))
    z = tmp_path / "export.zip"
    with zipfile.ZipFile(z, "w") as zf:
        zf.write(os.path.join(src, "Connections.csv"), "Basic/Connections.csv")
        zf.write(os.path.join(src, "messages.csv"), "../../messages.csv")   # crafted path
        zf.writestr("Profile.csv", "should not be kept")
    wp.init("sample", root=root, now=NOW)
    wp.record_consent("sample", "local_processing", granted_by="customer", method="t", root=root)
    meta = wp.import_export("sample", str(z), root=root, now=NOW)
    assert sorted(os.listdir(os.path.join(root, "sample", "raw"))) == ["Connections.csv", "messages.csv"]
    assert meta["delete_after"] == wp._iso(NOW + dt.timedelta(days=30))
    assert not os.path.exists(os.path.join(os.path.dirname(root), "messages.csv"))


def test_owner_is_inferred_and_measured(root, tmp_path):
    _ready(root, str(tmp_path))
    d = os.path.join(root, "sample", "raw")
    conns = wp.read_connections(os.path.join(d, "Connections.csv"))
    msgs = wp.read_messages(os.path.join(d, "messages.csv"))
    owner = wp.infer_owner(msgs, conns)
    assert owner["url"] == wp.norm_url(ME) and owner["coverage"] == 1.0
    people, groups, extra = wp.build_people(conns, msgs, owner["url"])
    by = {p["id"]: p for p in people}
    ada = by[wp.norm_url(A)]
    assert (ada["sent"], ada["received"], ada["copied"]) == (6, 6, 1)
    assert ada["their_median_reply_hours"] == 3.0 and ada["replies_from_them"] == 6
    assert ada["first_contact_by"] == "me" and ada["facts"]["position"] == "Fractional CFO"
    assert by[wp.norm_url(D)]["sent"] == 0 and by[wp.norm_url(D)]["received"] == 4
    assert by[wp.norm_url(C)]["mutual_connection"] and by[wp.norm_url(C)]["sent"] == 0
    assert len(groups) == 1
    assert all("Ada," in s or "Bo," in s or "Hey" in s for s in wp.voice_samples(extra["mine_1to1"]))


def test_owner_that_cannot_be_established_is_refused(root, tmp_path):
    _ready(root, str(tmp_path))
    # Two conversations with disjoint people: nobody is on 90% of them.
    path = os.path.join(root, "sample", "raw", "messages.csv")
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["CONVERSATION ID", "CONVERSATION TITLE", "FROM", "SENDER PROFILE URL", "TO",
                    "RECIPIENT PROFILE URLS", "DATE", "SUBJECT", "CONTENT", "FOLDER"])
        w.writerow(["x1", "", "A", A, "", B, "2026-01-01 00:00:00 UTC", "", "hi", "INBOX"])
        w.writerow(["x2", "", "C", C, "", D, "2026-01-02 00:00:00 UTC", "", "hi", "INBOX"])
        w.writerow(["x3", "", "M", ME, "", C, "2026-01-03 00:00:00 UTC", "", "hi", "INBOX"])
    with pytest.raises(wp.PilotError, match="cannot establish"):
        wp.rank("sample", root=root, scorer=_fake_scorer(), now=NOW)


def test_rank_with_stub_makes_no_network_call(root, tmp_path, monkeypatch):
    _ready(root, str(tmp_path))

    def boom(*a, **k):
        raise AssertionError("network touched in stub mode")
    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setattr(urllib.request.OpenerDirector, "open", boom)
    run = wp.rank("sample", root=root, scorer=_fake_scorer(), now=NOW)
    assert run["egress"] == "none" and run["drafts"]["mode"] == "stub"
    rows = _sheet(root)
    assert rows and all(r["draft"] == wp.STUB_DRAFT for r in rows)
    assert "fictional-di" not in " ".join(r["profile"] for r in rows)
    cal = wp._read_jsonl(os.path.join(root, "sample", "calibration.jsonl"))
    assert [e["event"] for e in cal] == ["ranked"] * len(rows)


@pytest.mark.skipif(not os.path.isfile(HUB_ROUTE), reason="hub checkout not on this machine")
def test_rank_with_the_hubs_own_rules(root, tmp_path):
    _ready(root, str(tmp_path))
    with open(os.path.join(root, "sample", "offer.json"), "w", encoding="utf-8") as fh:
        json.dump({"roles": ["fractional cfo", "consultant"]}, fh)
    run = wp.rank("sample", root=root, now=NOW)
    assert run["scorer"]["sha256"] and run["scorer"]["path"] == HUB_ROUTE
    rows = _sheet(root)
    names = [r["name"] for r in rows]
    # Ada talks to the owner and matches; Cy matches but was never messaged, so the hub's
    # structural rule puts the conversation first. Bo does not match; Di is one-way.
    assert names[0] == "Ada Sample"
    assert "Cy Sample" in names and names.index("Cy Sample") > 0
    assert "Di Sample" not in names and "Bo Sample" not in names
    cy = rows[names.index("Cy Sample")]
    assert "email on file" in cy["best_channel"]


def test_model_step_reaches_loopback_only(root, tmp_path):
    _ready(root, str(tmp_path), scopes=("local_processing", "local_model"))
    for url in ("http://example.com:11434", "http://10.0.0.5:11434", "https://api.example.ai"):
        with pytest.raises(wp.EgressRefused):
            wp.rank("sample", root=root, scorer=_fake_scorer(), drafts="ollama",
                    ollama_model="m", ollama_url=url, now=NOW)
    with pytest.raises(wp.EgressRefused):
        wp._post_local("http://evil.example/api/generate", {}, 1)


def test_there_is_no_cloud_path_even_with_consent(root, tmp_path):
    _ready(root, str(tmp_path), scopes=("local_processing", "cloud_model"))
    with pytest.raises(wp.CloudRefused):
        wp.rank("sample", root=root, scorer=_fake_scorer(), drafts="cloud", now=NOW)


def test_local_model_needs_its_own_consent(root, tmp_path):
    _ready(root, str(tmp_path))
    with pytest.raises(wp.ConsentMissing, match="local_model"):
        wp.rank("sample", root=root, scorer=_fake_scorer(), drafts="ollama", ollama_model="m",
                now=NOW)


def test_local_model_failure_raises_not_falls_through(root, tmp_path, monkeypatch):
    _ready(root, str(tmp_path), scopes=("local_processing", "local_model"))
    monkeypatch.setattr(wp, "_post_local", lambda *a, **k: {"response": ""})
    with pytest.raises(wp.PilotError, match="returned nothing"):
        wp.rank("sample", root=root, scorer=_fake_scorer(), drafts="ollama", ollama_model="m",
                now=NOW)
    monkeypatch.setattr(wp, "_post_local",
                        lambda *a, **k: {"response": "<think>x</think>Hi Ada, been a while."})
    wp.rank("sample", root=root, scorer=_fake_scorer(), drafts="ollama", ollama_model="m", now=NOW)
    assert all(r["draft"] == "Hi Ada, been a while." for r in _sheet(root))


def test_deletion_at_30_days_after_delivery_keeps_only_deidentified_calibration(root, tmp_path):
    _ready(root, str(tmp_path))
    wp.rank("sample", root=root, scorer=_fake_scorer(), now=NOW)
    delivered = NOW + dt.timedelta(days=3)
    wp.deliver("sample", root=root, now=delivered)
    wp.calibrate("sample", A, "sent", root=root, now=delivered + dt.timedelta(days=1))
    wp.calibrate("sample", A, "replied", root=root, now=delivered + dt.timedelta(days=4),
                 note="private note that must not survive")
    with pytest.raises(wp.PilotError, match="not in a ranked list"):
        wp.calibrate("sample", "https://www.linkedin.com/in/nobody", "sent", root=root)

    day29 = wp.sweep(root=root, now=delivered + dt.timedelta(days=29))
    assert day29 == [{"customer": "sample", "action": "kept",
                      "delete_after": wp._iso(delivered + dt.timedelta(days=30))}]
    assert wp.sweep(root=root, now=delivered + dt.timedelta(days=30), dry_run=True)[0]["action"] == "would_delete"
    assert os.path.isdir(os.path.join(root, "sample"))

    rep = wp.sweep(root=root, now=delivered + dt.timedelta(days=30))
    assert rep[0]["action"] == "deleted" and not os.path.exists(os.path.join(root, "sample"))
    with open(os.path.join(root, "calibration_aggregate.jsonl"), encoding="utf-8") as fh:
        agg = fh.read()
    for leak in ("fictional", "linkedin.com", "Ada", "private note"):
        assert leak not in agg
    rows = [json.loads(x) for x in agg.splitlines()]
    assert any(r["outcomes"] == ["sent", "replied"] for r in rows)
    with open(os.path.join(root, "ledger.jsonl"), encoding="utf-8") as fh:
        ledger = fh.read()
    assert "linkedin.com" not in ledger and "deleted" in ledger


def test_undelivered_export_is_still_deleted(root, tmp_path):
    _ready(root, str(tmp_path))
    assert wp.sweep(root=root, now=NOW + dt.timedelta(days=30))[0]["action"] == "deleted"


def test_revoking_consent_makes_it_due_now(root, tmp_path):
    _ready(root, str(tmp_path))
    later = NOW + dt.timedelta(days=2)
    wp.record_consent("sample", "local_processing", granted_by="customer", method="email",
                      revoke=True, root=root, now=later)
    assert not wp.has_consent(root, "sample", "local_processing")
    with pytest.raises(wp.ConsentMissing):
        wp.rank("sample", root=root, scorer=_fake_scorer(), now=later)
    assert wp.sweep(root=root, now=later)[0]["action"] == "deleted"


def test_failed_deletion_is_not_reported_as_deleted(root, tmp_path, monkeypatch):
    _ready(root, str(tmp_path))
    wp.rank("sample", root=root, scorer=_fake_scorer(), now=NOW)
    monkeypatch.setattr(wp.shutil, "rmtree", lambda *a, **k: None)
    rep = wp.sweep(root=root, now=NOW + dt.timedelta(days=31))
    assert rep[0]["action"] == "still_present"
    assert not os.path.exists(os.path.join(root, "calibration_aggregate.jsonl"))
    # Due now by revocation, so the CLI (which uses the real clock) sees it too, and exits 1.
    wp.record_consent("sample", "local_processing", granted_by="customer", method="t",
                      revoke=True, root=root)
    assert wp.main(["--root", root, "sweep"]) == 1


def test_cli_prints_counts_not_people(root, tmp_path, capsys, monkeypatch):
    _ready(root, str(tmp_path))
    monkeypatch.setattr(wp, "load_scorer", lambda path=None: _fake_scorer())
    assert wp.main(["--root", root, "rank", "sample"]) == 0
    out = capsys.readouterr().out
    assert "fictional" not in out and "Ada" not in out and '"ranked"' in out
    assert wp.main(["--root", root, "rank", "sample", "--drafts", "cloud"]) == 2
