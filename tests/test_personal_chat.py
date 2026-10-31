"""WEB-H4: the personal-chat app refuses a cloud path, never claims a tier it did not measure,
never claims a licence a preview build cannot have, and keeps the tier ladder in one place."""
import importlib.util
import json
import os
import sys

import pytest

_DIR = os.path.join(os.path.dirname(__file__), os.pardir, "node", "personal-chat")
_APP = os.path.join(_DIR, "app")
sys.path.insert(0, os.path.abspath(_APP))


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_APP, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclasses look their module up here; pc's `import seats` reuses it
    spec.loader.exec_module(mod)
    return mod


seats = _load("seats")
pc = _load("personal_chat")

SALE = {"sale_enabled": True, "store_org_id": "org-test", "max_seats": 3}
PREVIEW_BUILD = {"sale_enabled": False, "store_org_id": None, "max_seats": 3}


# -- cloud path -----------------------------------------------------------------------------

@pytest.mark.parametrize("url", ["http://127.0.0.1:11434", "localhost:11434", "http://[::1]:11434"])
def test_loopback_hosts_are_accepted(url):
    assert pc.require_loopback(url).startswith("http://")


@pytest.mark.parametrize("url", ["http://api.example.com", "https://127.0.0.1:11434",
                                 "http://10.0.0.5:11434", "http://127.0.0.1.evil.test"])
def test_anything_off_this_computer_is_refused(url):
    with pytest.raises(pc.CloudPathRefused):
        pc.require_loopback(url)


def test_main_refuses_to_start_on_a_remote_model_host(monkeypatch):
    monkeypatch.setenv("OLLAMA_HOST", "http://api.example.com")
    assert pc.main(["--no-browser"]) == 2


# -- tier -----------------------------------------------------------------------------------

LADDER = {"cpuOnly": {"tier": "CPU-ONLY", "chatModel": "small-model", "note": "n"}}


def test_measured_tier_is_used_and_marked_measured():
    cfg = {"tier": {"tier": "TIER-4", "chatModel": "mid-model", "note": "x"}}
    t = pc.resolve_tier(cfg, LADDER)
    assert (t["tier"], t["chatModel"], t["measured"]) == ("TIER-4", "mid-model", True)


def test_no_verdict_falls_to_cpu_row_and_says_unknown():
    t = pc.resolve_tier(None, LADDER)
    assert t["tier"] == "unknown" and t["measured"] is False
    assert t["chatModel"] == "small-model"


def test_no_verdict_and_no_ladder_has_no_model():
    t = pc.resolve_tier(None, None)
    assert t["chatModel"] is None and t["measured"] is False


def test_the_ladder_is_not_restated_in_personal_chat():
    """NodeSpec.ps1 holds the only copy. No threshold or ladder model name may appear here."""
    needles = ["qwen2.5", "mistral-small", "llama3.2", "23.5", "15.5", "11.5", "7.5", "5.5"]
    hits, scanned = [], 0
    for base, _dirs, files in os.walk(_DIR):
        if {"dist", "dist-mac"} & set(base.split(os.sep)):
            continue
        for f in files:
            if f.endswith((".py", ".ps1", ".sh", ".iss", ".html", ".md")):
                scanned += 1
                text = open(os.path.join(base, f), encoding="utf-8").read()
                hits += [(f, n) for n in needles if n in text]
    assert scanned >= 6, "scanned too few files: this guard cannot see what it checks"
    assert hits == []


# -- seats ----------------------------------------------------------------------------------

def test_preview_build_reports_preview_and_makes_no_call(tmp_path):
    def boom(*a, **k):
        raise AssertionError("a preview build must not call the store")
    st = seats.check(str(tmp_path), PREVIEW_BUILD, transport=boom)
    assert st.state == seats.PREVIEW
    with pytest.raises(seats.NotForSale):
        seats.activate("KEY-1", str(tmp_path), PREVIEW_BUILD, transport=boom)


def test_sale_build_without_activation_is_unlicensed(tmp_path):
    assert seats.check(str(tmp_path), SALE, transport=None).state == seats.UNLICENSED


def test_activation_stores_record_and_sends_random_label(tmp_path):
    sent = {}

    def ok(url, body):
        sent.update(url=url, body=body)
        return 200, {"id": "act-1"}

    st = seats.activate("KEY-1", str(tmp_path), SALE, transport=ok)
    assert st.state == seats.LICENSED
    assert sent["url"] == "https://api.polar.sh" + seats.ACTIVATE_PATH
    assert sent["body"]["label"].startswith("pc-")
    assert sent["body"]["label"] != os.environ.get("COMPUTERNAME", "")
    assert seats.read_record(str(tmp_path))["activation_id"] == "act-1"


def test_fourth_computer_is_refused(tmp_path):
    with pytest.raises(seats.SeatLimitReached):
        seats.activate("KEY-1", str(tmp_path), SALE, transport=lambda u, b: (403, {}))
    assert seats.read_record(str(tmp_path)) is None


def _activated(tmp_path):
    seats.activate("KEY-1", str(tmp_path), SALE, transport=lambda u, b: (200, {"id": "act-1"}))


def test_store_unreachable_is_unknown_not_licensed(tmp_path):
    _activated(tmp_path)

    def down(url, body):
        raise OSError("no route")
    assert seats.check(str(tmp_path), SALE, transport=down).state == seats.UNKNOWN


def test_unexpected_answer_is_unknown(tmp_path):
    _activated(tmp_path)
    assert seats.check(str(tmp_path), SALE, transport=lambda u, b: (500, None)).state == seats.UNKNOWN
    assert seats.check(str(tmp_path), SALE,
                       transport=lambda u, b: (200, {"status": "weird"})).state == seats.UNKNOWN


def test_granted_is_licensed_and_revoked_is_unlicensed(tmp_path):
    _activated(tmp_path)
    assert seats.check(str(tmp_path), SALE,
                       transport=lambda u, b: (200, {"status": "granted"})).state == seats.LICENSED
    assert seats.check(str(tmp_path), SALE,
                       transport=lambda u, b: (200, {"status": "revoked"})).state == seats.UNLICENSED


def test_store_host_off_the_allowlist_is_refused(tmp_path):
    build = dict(SALE, store_host="evil.example")
    with pytest.raises(seats.NotForSale):
        seats.activate("KEY-1", str(tmp_path), build, transport=lambda u, b: (200, {"id": "x"}))


# -- the HTTP surface -----------------------------------------------------------------------

def _serve(tmp_path, monkeypatch):
    import threading
    from http.server import ThreadingHTTPServer
    bundle = tmp_path / "bundle"
    (bundle / "static").mkdir(parents=True)
    (bundle / "static" / "index.html").write_text("<p>hi</p>", encoding="utf-8")
    (bundle / "ladder.json").write_text(json.dumps(LADDER), encoding="utf-8")
    (bundle / "build_info.json").write_text(json.dumps(PREVIEW_BUILD), encoding="utf-8")
    monkeypatch.setattr(pc, "ollama_state", lambda base: {"running": False, "models": []})
    app = pc.App(str(bundle), str(tmp_path / "home"), "http://127.0.0.1:9")
    srv = ThreadingHTTPServer(("127.0.0.1", 0), pc.make_handler(app))
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv, app


def _req(srv, method, path, body=None, headers=None):
    import http.client
    c = http.client.HTTPConnection("127.0.0.1", srv.server_address[1], timeout=5)
    c.request(method, path, body=json.dumps(body) if body is not None else None,
              headers=headers or {"Content-Type": "application/json"})
    r = c.getresponse()
    return r.status, json.loads(r.read() or b"null")


def test_status_says_preview_and_unknown_tier(tmp_path, monkeypatch):
    srv, _ = _serve(tmp_path, monkeypatch)
    try:
        code, s = _req(srv, "GET", "/api/status")
        assert code == 200
        assert s["licence"]["state"] == "preview"
        assert s["tier"]["tier"] == "unknown" and s["tier"]["measured"] is False
        assert s["build"]["signed"] is False
    finally:
        srv.shutdown()


def test_cross_origin_post_is_refused(tmp_path, monkeypatch):
    srv, app = _serve(tmp_path, monkeypatch)
    try:
        code, _ = _req(srv, "POST", "/api/quit", {}, {"Content-Type": "application/json",
                                                      "Origin": "https://evil.example"})
        assert code == 403 and not app.stop.is_set()
    finally:
        srv.shutdown()


def test_chat_with_model_down_is_503_not_a_fake_answer(tmp_path, monkeypatch):
    srv, _ = _serve(tmp_path, monkeypatch)
    try:
        code, j = _req(srv, "POST", "/api/chat", {"messages": [{"role": "user", "content": "hi"}]})
        assert code == 503 and "reply" not in j
    finally:
        srv.shutdown()
