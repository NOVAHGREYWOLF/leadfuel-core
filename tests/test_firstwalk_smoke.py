"""SURFACE firstwalk: the read-only smoke pass, the walk data and the checklist pages.

What these tests hold the code to (the estate's rule: a check that cannot establish a state must not
report one):
  * nothing but loopback is ever probed, and a redirect is reported, never followed;
  * an environment where everything is absent, or every call raises, gives no `pass` anywhere;
  * the positive controls can fail (a broken check is caught by them);
  * the walk state never moves because a smoke check passed: only the owner's marks move it;
  * the generated checklist pages are exactly what the data says.
"""
import copy
import http.server
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import threading

import pytest

_ROOT = os.path.join(os.path.dirname(__file__), os.pardir, "firstwalk")


def _load(name):
    spec = importlib.util.spec_from_file_location("firstwalk_" + name, os.path.join(_ROOT, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


sm = _load("smoke")
rd = _load("render")
WALK_PATH = os.path.join(_ROOT, "walk.json")


@pytest.fixture(scope="module")
def walk():
    return sm.load_walk(WALK_PATH)


# The rows the NODE acceptance tool printed on 2026-11-23 (31 rows). walk.json may only name rows from
# this list: a typo would otherwise read as "row not supplied", an unknown that looks like a gap.
ACCEPTANCE_ROWS_SEEN = frozenset("""
shell.local_cold_start shell.one_ai_entry shell.one_startup_window shell.no_offpc_socket shell.doors_closed
ollama.up ollama.one_owner ollama.policy ollama.tray_out_of_startup openwebui.chats_imported openwebui.server_off
openwebui.web_search_carried hermes.messaging_off hermes.api_server_off hermes.acp_present hermes.memories_imported
prime.services_off_prime prime.voice_in_app prime.voice_interpreter prime.cloud_tts_off decompress.archive_db
decompress.owner_data_moved chardesign.service_entry chardesign.api lmstudio.no_autostart lmstudio.no_server
lmstudio.downloads_folder hub.mcp_entry hub.local_mcp gpu.lease_route gpu.comfy_probe
""".split())


# ----------------------------------------------------------------------------- loopback only

class TestLoopbackOnly:
    def _no_sockets(self, monkeypatch):
        def boom(*a, **k):
            raise AssertionError("a socket was opened for a non-loopback host")
        monkeypatch.setattr(socket, "create_connection", boom)
        monkeypatch.setattr(socket.socket, "connect", boom)

    @pytest.mark.parametrize("url", [
        "http://example.com/x", "https://leadfuel.cloud/login", "http://10.0.0.5:8080/", "http://192.168.1.2/",
        "http://100.64.1.1:8106/", "http://[2001:db8::1]/", "http://0.0.0.0:80/", "http://127.0.0.1.evil.test/",
        "http://localhost.evil.test/",
    ])
    def test_http_refuses_non_loopback_before_a_socket(self, monkeypatch, url):
        self._no_sockets(monkeypatch)
        with pytest.raises(PermissionError):
            sm.RealEnv().http(url)

    @pytest.mark.parametrize("host", ["example.com", "10.0.0.5", "100.64.1.1", "0.0.0.0", "", None])
    def test_tcp_refuses_non_loopback_before_a_socket(self, monkeypatch, host):
        self._no_sockets(monkeypatch)
        with pytest.raises(PermissionError):
            sm.RealEnv().tcp(host, 80)

    def test_a_refused_host_reads_unknown_not_fail_and_not_pass(self):
        class Off(sm._Fake):
            def http(self, url, **k):
                raise PermissionError("loopback only")
        state, _ = sm._get(Off("ok200"), "http://example.com/")[1]
        assert state == sm.UNKNOWN

    def test_every_probe_target_in_the_module_is_loopback(self):
        for url in (sm.OLLAMA, sm.HUB, sm.MCP, sm.WINDOW, sm.PRIME_DASH, sm.CHARDESIGN, sm.COMFY):
            assert url.startswith("http://127.0.0.1:"), url


class _Redirector(http.server.BaseHTTPRequestHandler):
    seen = []

    def do_GET(self):
        type(self).seen.append(self.path)
        if self.path == "/offsite":
            self.send_response(302)
            self.send_header("Location", "https://example.invalid/login")
        elif self.path == "/hop":
            self.send_response(302)
            self.send_header("Location", "/landed")
        else:
            self.send_response(200)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *a):
        pass


def test_redirects_are_reported_never_followed():
    _Redirector.seen = []
    srv = http.server.HTTPServer(("127.0.0.1", 0), _Redirector)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        base = "http://127.0.0.1:%d" % srv.server_address[1]
        off = sm.RealEnv().http(base + "/offsite")
        hop = sm.RealEnv().http(base + "/hop")
    finally:
        srv.shutdown()
        srv.server_close()
    assert off.status == 302 and off.headers["location"] == "https://example.invalid/login"
    assert hop.status == 302 and hop.headers["location"] == "/landed"
    assert _Redirector.seen == ["/offsite", "/hop"], "a redirect was followed"


def test_a_refused_connection_is_refused_and_a_closed_port_is_not_a_timeout():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()
    # Windows retries a refused loopback connect for about two seconds before it reports it, so the
    # timeout here is generous: a timeout would (rightly) read as NoAnswer, never as Refused.
    with pytest.raises(sm.Refused):
        sm.RealEnv().http("http://127.0.0.1:%d/" % port, timeout=10)
    with pytest.raises(sm.Refused):
        sm.RealEnv().tcp("127.0.0.1", port, timeout=10)


# ----------------------------------------------------------------------------- controls and no-pass rules

def test_controls_come_out_ok(walk):
    ok, problems = sm.run_controls(sm.all_check_ids(walk))
    assert ok, problems


def test_controls_can_fail_a_check_that_always_passes_is_caught(walk, monkeypatch):
    what, source, _ = sm.CHECKS["local.hub.api_requires_login"]
    monkeypatch.setitem(sm.CHECKS, "local.hub.api_requires_login", (what, source, lambda env, ctx: (sm.PASS, "always")))
    ok, problems = sm.run_controls(sm.all_check_ids(walk))
    assert not ok
    assert any("api_requires_login" in p for p in problems)


def test_a_check_that_cannot_see_must_not_pass(walk, monkeypatch):
    # a liar in the 'absent' environment is caught too
    what, source, _ = sm.CHECKS["local.mcp.health"]
    monkeypatch.setitem(sm.CHECKS, "local.mcp.health", (what, source, lambda env, ctx: (sm.PASS, "always")))
    ok, problems = sm.run_controls(sm.all_check_ids(walk))
    assert not ok and any("local.mcp.health" in p for p in problems)


@pytest.mark.parametrize("mode", ["absent", "raise"])
def test_nothing_passes_when_everything_is_absent_or_raises(walk, mode):
    ids = sm.all_check_ids(walk) + sorted(sm.CHECKS)
    for cid in ids:
        r = sm.run_one(sm._Fake(mode), {}, cid)
        assert r["state"] != sm.PASS, (cid, r)
        assert r["state"] in sm.CHECK_STATES


def test_a_raising_check_is_unknown_with_the_exception_named():
    r = sm.run_one(sm._Fake("raise"), {}, "local.hub.healthz")
    assert r["state"] == sm.UNKNOWN and "RuntimeError" in r["detail"]


def test_an_unknown_check_id_is_unknown_not_a_pass():
    r = sm.run_one(sm._Fake("ok200"), {}, "local.does.not.exist")
    assert r["state"] == sm.UNKNOWN and r["what"] == "no such check"


def test_a_check_returning_a_bad_state_is_unknown(monkeypatch):
    monkeypatch.setitem(sm.CHECKS, "t.bad", ("x", "t", lambda env, ctx: ("green", "x")))
    assert sm.run_one(sm._Fake("ok200"), {}, "t.bad")["state"] == sm.UNKNOWN


# ----------------------------------------------------------------------------- the checks, one by one

def _env_with(replies):
    """An env answering {path suffix: Reply}; anything else is refused."""
    class E(sm._Fake):
        def http(self, url, **k):
            for suffix, rep in replies.items():
                if url.endswith(suffix):
                    if isinstance(rep, Exception):
                        raise rep
                    return rep
            raise sm.Refused("no route")
    return E("ok200")


def J(status, obj):
    return sm.Reply(status, {"content-type": "application/json"}, json.dumps(obj).encode())


class TestChecks:
    def test_a_timeout_is_unknown_not_down(self):
        env = _env_with({"/healthz": sm.NoAnswer("slow")})
        assert sm.run_one(env, {}, "local.hub.healthz")["state"] == sm.UNKNOWN

    def test_refused_is_fail(self):
        assert sm.run_one(_env_with({}), {}, "local.hub.healthz")["state"] == sm.FAIL

    def test_healthz_needs_ok_true(self):
        assert sm.run_one(_env_with({"/healthz": J(200, {"ok": True})}), {}, "local.hub.healthz")["state"] == sm.PASS
        assert sm.run_one(_env_with({"/healthz": J(200, {"ok": False})}), {}, "local.hub.healthz")["state"] == sm.FAIL

    def test_api_requires_login_one_open_route_fails_it(self):
        env = _env_with({"/feed": J(401, {}), "/character": J(200, {"x": 1}), "/atlas": J(401, {})})
        r = sm.run_one(env, {}, "local.hub.api_requires_login")
        assert r["state"] == sm.FAIL and "/api/command/character" in r["detail"]

    def test_api_requires_login_a_404_is_not_a_refusal(self):
        env = _env_with({"/feed": J(404, {}), "/character": J(404, {}), "/atlas": J(404, {})})
        assert sm.run_one(env, {}, "local.hub.api_requires_login")["state"] == sm.UNKNOWN

    def test_command_local_200_passes_and_says_what_it_did_not_read(self):
        r = sm.run_one(_env_with({"/command": sm.Reply(200)}), {}, "local.hub.command_opens_locally")
        assert r["state"] == sm.PASS and "not read" in r["detail"]

    def test_command_local_redirect_off_machine_fails_and_names_the_host(self):
        env = _env_with({"/command": sm.Reply(302, {"Location": "https://leadfuel.cloud/login"}),
                         "/login": J(503, {"error": "login not enabled on this service"})})
        r = sm.run_one(env, {}, "local.hub.command_opens_locally")
        assert r["state"] == sm.FAIL and "leadfuel.cloud" in r["detail"] and "not followed" in r["detail"]

    def test_command_local_redirect_to_loopback_is_unknown(self):
        env = _env_with({"/command": sm.Reply(302, {"Location": "http://127.0.0.1:8080/login"})})
        assert sm.run_one(env, {}, "local.hub.command_opens_locally")["state"] == sm.UNKNOWN

    def test_window_route_only_passes_on_a_json_404(self):
        assert sm.run_one(_env_with({"/firstwalk-probe": J(404, {"error": "x"})}), {}, "local.window.route")["state"] == sm.PASS
        assert sm.run_one(_env_with({"/firstwalk-probe": sm.Reply(404, {}, b"<html>")}), {}, "local.window.route")["state"] == sm.FAIL

    def test_chat_model_needs_capabilities_it_can_read(self):
        tags = {"models": [{"name": "a", "size": 5}]}  # a server that reports no capabilities
        r = sm.run_one(_env_with({"/api/tags": J(200, tags)}), {}, "local.ollama.chat_model_installed")
        assert r["state"] == sm.UNKNOWN
        tags = {"models": [{"name": "emb", "size": 1, "capabilities": ["embedding"]}]}
        assert sm.run_one(_env_with({"/api/tags": J(200, tags)}), {}, "local.ollama.chat_model_installed")["state"] == sm.FAIL
        tags = {"models": [{"name": "big", "size": 9, "capabilities": ["completion"]},
                           {"name": "small", "size": 2, "capabilities": ["completion", "tools"]}]}
        r = sm.run_one(_env_with({"/api/tags": J(200, tags)}), {}, "local.ollama.chat_model_installed")
        assert r["state"] == sm.PASS and "small" in r["detail"]

    def test_chat_roundtrip_is_not_run_without_the_flag(self):
        r = sm.run_one(_env_with({}), {}, "local.ollama.chat_roundtrip")
        assert r["state"] == sm.UNKNOWN and "--model-call" in r["detail"]

    def test_chat_roundtrip_asks_with_keep_alive_zero_and_needs_a_reply(self):
        sent = {}
        tags = {"models": [{"name": "m-instruct", "size": 3, "capabilities": ["completion"]}]}

        class E(sm._Fake):
            def http(self, url, method="GET", body=None, timeout=5.0):
                if url.endswith("/api/tags"):
                    return J(200, tags)
                sent.update(body or {})
                return J(200, {"done": True, "message": {"content": "OK"}, "total_duration": 2_000_000_000})
        r = sm.run_one(E("ok200"), {"model_call": True}, "local.ollama.chat_roundtrip")
        assert r["state"] == sm.PASS and sent["keep_alive"] == 0 and sent["stream"] is False
        empty = lambda self, url, method="GET", body=None, timeout=5.0: (  # noqa: E731
            J(200, tags) if url.endswith("/api/tags") else J(200, {"done": True, "message": {"content": ""}}))
        E.http = empty
        assert sm.run_one(E("ok200"), {"model_call": True}, "local.ollama.chat_roundtrip")["state"] == sm.FAIL

    def test_postgres_is_connect_only(self):
        class Up(sm._Fake):
            def tcp(self, host, port, timeout=4.0):
                assert (host, port) == ("127.0.0.1", 5432)
                return True
        r = sm.run_one(Up("ok200"), {}, "local.brain.postgres_tcp")
        assert r["state"] == sm.PASS and "not read" in r["detail"]

    def test_phone_listener_cases(self):
        def env(listeners):
            class E(sm._Fake):
                def listeners(self):
                    return listeners
            return E("ok200")
        cid = "local.phone.listener"
        assert sm.run_one(env(None), {}, cid)["state"] == sm.UNKNOWN
        assert sm.run_one(env({("0.0.0.0", 80)}), {}, cid)["state"] == sm.FAIL
        assert sm.run_one(env({("100.98.6.6", sm.PHONE_PORT)}), {}, cid)["state"] == sm.PASS
        assert sm.run_one(env({("0.0.0.0", sm.PHONE_PORT)}), {}, cid)["state"] == sm.UNKNOWN
        assert sm.run_one(env({("192.168.1.9", sm.PHONE_PORT)}), {}, cid)["state"] == sm.UNKNOWN

    @pytest.mark.parametrize("addr,want", [("100.64.0.1", True), ("100.127.255.1", True), ("100.63.0.1", False),
                                           ("100.128.0.1", False), ("10.0.0.1", False), ("junk", False), ("", False)])
    def test_tailnet_range(self, addr, want):
        assert sm._in_tailnet(addr) is want

    def test_vault_sync_states(self):
        cid = "watch.vault_sync_status"
        run = lambda ctx: sm.run_one(sm._Fake("ok200"), ctx, cid)  # noqa: E731
        assert run({})["state"] == sm.UNKNOWN
        assert run({"vault_sync": {"state": "ok", "last_end": "t"}})["state"] == sm.PASS
        assert run({"vault_sync": {"state": "failed", "reason": "exit 3"}})["state"] == sm.FAIL
        assert run({"vault_sync": {"state": "unknown"}})["state"] == sm.UNKNOWN
        assert run({"vault_sync": {"state": "weird"}})["state"] == sm.UNKNOWN
        assert run({"vault_sync": []})["state"] == sm.UNKNOWN

    def test_node_rows(self):
        rows = sm.load_acceptance(json.dumps([{"id": "a.b", "state": "pass", "detail": "d"},
                                              {"id": "c.d", "state": "fail", "detail": "x"},
                                              {"id": "e.f", "state": "green"}]))
        ctx = {"acceptance": rows}
        run = lambda cid: sm.run_one(sm._Fake("ok200"), ctx, cid)["state"]  # noqa: E731
        assert run("node.a.b") == sm.PASS and run("node.c.d") == sm.FAIL
        assert run("node.e.f") == sm.UNKNOWN, "a state outside pass/fail/unknown is unknown"
        assert run("node.no.such") == sm.UNKNOWN, "a row not supplied is unknown"
        assert sm.run_one(sm._Fake("ok200"), {}, "node.a.b")["state"] == sm.UNKNOWN, "no acceptance file is unknown"

    @pytest.mark.parametrize("text", ["", "not json", "{}", "[]", '"x"', "[1,2]"])
    def test_load_acceptance_gives_none_on_nothing_usable(self, text):
        assert sm.load_acceptance(text) is None


# ----------------------------------------------------------------------------- page source checks

PAGE = """<html><body>
{# a comment about the stage 3 plan and id="ghost" #}
<!-- not wired yet and id="ghostb" -->
<script>var s = '<div id="ghostc"></div> stage 4';</script>
<div id="char"></div><div id="afeed" title="hover stage 5"></div><div id="board"></div>
<div id="party"></div><span id="res-day"></span><div id="radar"></div>
</body></html>"""


class TestPageSource:
    def test_visible_text_drops_comments_scripts_and_tags_but_keeps_title_attributes(self):
        t = sm.visible_text(PAGE)
        assert "stage 3" not in t and "not wired yet" not in t and "stage 4" not in t
        assert "hover stage 5" in t, "a title attribute is read on hover"

    def test_ids_in_comments_and_scripts_are_not_on_the_page(self):
        ids = sm.template_ids(PAGE)
        assert {"char", "afeed", "board", "party", "res-day", "radar"} <= ids
        assert not ({"ghost", "ghostb", "ghostc"} & ids)

    def test_region_status(self):
        ids = sm.template_ids(PAGE)
        spec = dict((k, s) for k, _, s in sm.DOC04_REGIONS)
        menu = {"contracts": {"state": "not built"}, "log": {"state": "partly"}}
        assert sm.region_status(ids, spec["left_action_feed"], menu) == "present"
        assert sm.region_status(ids, spec["top_resources"], menu) == "present"
        assert sm.region_status(ids, spec["overlay_contracts"], menu) == "declared_not_built"
        assert sm.region_status(ids, spec["overlay_log"], menu) == "absent"
        assert sm.region_status(ids, spec["overlay_log"], None) == "absent"

    def _hub(self, tmp_path, page=PAGE, menu=None, js=True):
        (tmp_path / "templates").mkdir(parents=True)
        (tmp_path / "static" / "command").mkdir(parents=True)
        (tmp_path / "templates" / "command_screen.html").write_text(page, encoding="utf-8")
        if menu is not None:
            (tmp_path / "static" / "command" / "start.json").write_text(json.dumps({"entries": menu}), encoding="utf-8")
        return {"hub_root": str(tmp_path)}

    def test_regions_six_of_eight_is_a_fail_that_says_which(self, tmp_path):
        ctx = self._hub(tmp_path, menu=[{"key": "contracts", "state": "not built"}, {"key": "log", "state": "not built"}])
        r = sm.run_one(sm.RealEnv(), ctx, "source.command.regions")
        assert r["state"] == sm.FAIL and "6 of 8" in r["detail"] and "Overlay: Log" in r["detail"]

    def test_the_action_feed_check_does_not_fail_for_the_other_regions(self, tmp_path):
        ctx = self._hub(tmp_path, menu=[])
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.region.action_feed")["state"] == sm.PASS
        ctx = self._hub(tmp_path / "x", page="<div id='nothing'></div>", menu=[])
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.region.action_feed")["state"] == sm.FAIL

    def test_no_hub_root_is_unknown(self):
        for cid in ("source.command.regions", "source.command.region.action_feed", "source.command.dead_strings",
                    "source.command.world_controls", "source.command.phone_layout"):
            assert sm.run_one(sm.RealEnv(), {}, cid)["state"] == sm.UNKNOWN, cid

    def test_dead_strings_read_visible_words_and_the_menu(self, tmp_path):
        ctx = self._hub(tmp_path, page="<p>Arrives in stage 6</p>", menu=[])
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.dead_strings")["state"] == sm.FAIL
        ctx = self._hub(tmp_path / "b", page=PAGE.replace('title="hover stage 5"', ""), menu=[])
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.dead_strings")["state"] == sm.PASS
        ctx = self._hub(tmp_path / "c", page="<p>fine</p>", menu=[{"key": "x", "today": "coming soon"}])
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.dead_strings")["state"] == sm.FAIL
        ctx = self._hub(tmp_path / "d", page="<p>fine</p>", menu=None)
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.dead_strings")["state"] == sm.UNKNOWN, \
            "the menu data is half of what is read: without it the answer is unknown"

    def test_world_controls_need_the_script_too(self, tmp_path):
        page = "".join('<button id="%s"></button>' % i for i in ("x3d-3d", "x3d-orbit", "x3d-rotate", "x3d-reset"))
        ctx = self._hub(tmp_path, page=page, menu=[])
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.world_controls")["state"] == sm.FAIL
        (tmp_path / "static" / "command" / "crystal3d.js").write_text("//", encoding="utf-8")
        assert sm.run_one(sm.RealEnv(), ctx, "source.command.world_controls")["state"] == sm.PASS


class TestFiles:
    def test_artifacts_need_a_real_page(self, tmp_path):
        root = tmp_path / "artifacts"
        (root / "flow__AAA").mkdir(parents=True)
        (root / "flow__AAA" / "current.html").write_bytes(b"x" * 60000)
        (root / "live__BBB").mkdir()
        (root / "live__BBB" / "current.html").write_bytes(b"x" * 10)
        ctx = {"artifacts_root": str(root), "atlas_ids": ["AAA", "BBB"]}
        assert sm.run_one(sm.RealEnv(), ctx, "files.artifacts.original_atlas")["state"] == sm.PASS
        ctx["atlas_ids"] = ["BBB", "ZZZ"]
        assert sm.run_one(sm.RealEnv(), ctx, "files.artifacts.original_atlas")["state"] == sm.FAIL
        ctx = {"artifacts_root": str(tmp_path / "missing"), "atlas_ids": ["AAA"]}
        assert sm.run_one(sm.RealEnv(), ctx, "files.artifacts.original_atlas")["state"] == sm.UNKNOWN
        assert sm.run_one(sm.RealEnv(), {}, "files.artifacts.original_atlas")["state"] == sm.UNKNOWN

    def test_mockups_one_missing_fails_it(self, tmp_path):
        root = tmp_path / "a"
        (root / "m1__X1").mkdir(parents=True)
        (root / "m1__X1" / "index.html").write_bytes(b"x" * 20000)
        ctx = {"artifacts_root": str(root), "mockups": [{"id": "M1", "artifact_id": "X1"}, {"id": "M2", "artifact_id": "X2"}]}
        r = sm.run_one(sm.RealEnv(), ctx, "files.artifacts.mockups")
        assert r["state"] == sm.FAIL and "M2" in r["detail"] and "M1" not in r["detail"]

    def test_library_and_doc04(self, tmp_path):
        lib = tmp_path / "lib"
        (lib / "artifacts" / "one__A").mkdir(parents=True)
        (lib / "INDEX.md").write_text("i", encoding="utf-8")
        assert sm.run_one(sm.RealEnv(), {"library_root": str(lib)}, "files.documents.library_present")["state"] == sm.PASS
        (lib / "INDEX.md").unlink()
        assert sm.run_one(sm.RealEnv(), {"library_root": str(lib)}, "files.documents.library_present")["state"] == sm.FAIL
        d = tmp_path / "d.md"
        d.write_bytes(b"x" * 2000)
        assert sm.run_one(sm.RealEnv(), {"doc04": str(d)}, "files.documents.doc04")["state"] == sm.PASS
        assert sm.run_one(sm.RealEnv(), {"doc04": str(tmp_path / "no.md")}, "files.documents.doc04")["state"] == sm.FAIL
        assert sm.run_one(sm.RealEnv(), {}, "files.documents.doc04")["state"] == sm.UNKNOWN


# ----------------------------------------------------------------------------- walk, marks, rollup

class TestRollup:
    N, P, F, C = "not_tested", "pass", "fail", "closed_by_design"

    @pytest.mark.parametrize("states,want", [
        ([], "not_tested"),
        (["pass"], "pass"), (["pass", "pass"], "pass"),
        (["pass", "not_tested"], "not_tested"),
        (["not_tested", "not_tested"], "not_tested"),
        (["fail"], "fail"), (["pass", "fail", "not_tested"], "fail"), (["fail", "closed_by_design"], "fail"),
        (["closed_by_design"], "closed_by_design"), (["pass", "closed_by_design"], "closed_by_design"),
        (["closed_by_design", "not_tested"], "not_tested"),
        (["pass", "nonsense"], "not_tested"), (["nonsense"], "not_tested"),
    ])
    def test_rollup(self, states, want):
        assert sm.rollup(states) == want

    def test_smoke_rollup(self):
        assert sm.smoke_rollup([]) == sm.NOT_RUN
        assert sm.smoke_rollup(["pass", "pass"]) == "pass"
        assert sm.smoke_rollup(["pass", "unknown"]) == "unknown"
        assert sm.smoke_rollup(["pass", "unknown", "fail"]) == "fail"


class TestMarks:
    def good(self, **marks):
        return json.dumps({"schema": "firstwalk.marks/1", "exported_at": "2026-11-23T00:00:00Z", "marks": marks, "cells": {}})

    def test_a_good_file_is_read(self):
        got = sm.load_marks(self.good(**{"L01.1": {"state": "pass", "proof": "p"}, "L01.2": "fail"}))
        assert got == {"L01.1": "pass", "L01.2": "fail"}

    @pytest.mark.parametrize("text", [
        "", "nope", "[]", "{}", '{"schema": "firstwalk.marks/2", "marks": {}}',
        '{"schema": "firstwalk.marks/1"}', '{"schema": "firstwalk.marks/1", "marks": []}',
        '{"schema": "other", "marks": {"L01.1": {"state": "pass"}}}', None,
    ])
    def test_a_wrong_schema_or_shape_reads_as_no_marks(self, text):
        assert sm.load_marks(text) == {}

    def test_an_unknown_state_word_is_dropped_not_read_as_a_pass(self):
        got = sm.load_marks(self.good(**{"L01.1": {"state": "passed"}, "L01.2": {"state": "pass"}, "L01.3": {}}))
        assert got == {"L01.2": "pass"}


class TestWalkData:
    def test_shape(self, walk):
        assert walk["schema"] == "firstwalk.walk/1"
        assert [c["id"] for c in walk["lines"]] == ["L%02d" % i for i in range(1, 16)]
        assert [c["id"] for c in walk["rooms"]] == ["R%02d" % i for i in range(1, 10)]
        assert [n["id"] for n in walk["named"]] == ["N%02d" % i for i in range(1, 13)]
        assert [m["id"] for m in walk["mockups"]] == ["M1", "M2", "M3"]

    def test_ids_are_unique_and_steps_belong_to_their_cell(self, walk):
        seen = set()
        for _, c in sm.walk_cells(walk):
            assert c["id"] not in seen
            seen.add(c["id"])
            assert c["steps"], c["id"]
            for i, s in enumerate(c["steps"], 1):
                assert s["id"] == "%s.%d" % (c["id"], i), s["id"]
                assert s["id"] not in seen
                seen.add(s["id"])

    def test_every_step_says_what_to_do_expect_and_prove(self, walk):
        for _, c in sm.walk_cells(walk):
            for s in c["steps"]:
                for key in ("do", "expect", "proof"):
                    assert isinstance(s.get(key), str) and s[key].strip(), (s["id"], key)

    def test_queue_ids_are_strings_and_cells_have_titles(self, walk):
        for _, c in sm.walk_cells(walk):
            assert c["title"].strip()
            assert all(isinstance(q, str) and q for q in c["queue"]), c["id"]
        for n in walk["named"]:
            assert all(isinstance(q, str) and q for q in n["queue"]), n["id"]

    def test_named_things_carry_a_known_status_and_real_mockups(self, walk):
        mock = {m["id"] for m in walk["mockups"]}
        for n in walk["named"]:
            assert n["built"] in ("built", "partial", "not built", "unknown"), n["id"]
            assert set(n["mockups"]) <= mock, n["id"]
            assert n["evidence"].strip() and n["title"].strip() and n["asked"].strip()
        for _, c in sm.walk_cells(walk):
            assert set(c.get("mockups", [])) <= mock, c["id"]

    def test_mockups_name_an_artifact_and_say_how_sure(self, walk):
        for m in walk["mockups"]:
            assert len(m["artifact_id"]) == 22 and m["artifact_id"].isalnum(), m["id"]
            assert m["confidence"].strip() and m["role"].strip()

    def test_every_check_id_resolves(self, walk):
        for cid in sm.all_check_ids(walk):
            if cid.startswith(sm.NODE_PREFIX):
                assert cid[len(sm.NODE_PREFIX):] in ACCEPTANCE_ROWS_SEEN, "no such NODE acceptance row: " + cid
            else:
                assert cid in sm.CHECKS, "no such check: " + cid
            r = sm.run_one(sm._Fake("absent"), {}, cid)
            assert r["what"] != "no such check", cid

    def test_every_check_is_used_by_some_cell(self, walk):
        used = set(sm.all_check_ids(walk))
        assert set(sm.CHECKS) - used == set(), "a check no cell uses reads nothing: " + ", ".join(sorted(set(sm.CHECKS) - used))

    def test_scoreboard_cells_cover_every_line_and_room_once(self, walk):
        m = walk["scoreboard_cells"]
        ids = [c["id"] for _, c in sm.walk_cells(walk)]
        assert sorted(m) == sorted(ids)
        assert len(set(m.values())) == len(m)
        assert [m["L%02d" % i] for i in range(1, 16)] == ["line-%02d" % i for i in range(1, 16)]
        assert [m["R%02d" % i] for i in range(1, 10)] == [
            "room-command-center", "room-atlas", "room-reports", "room-approvals", "room-prime-voice",
            "room-character-design", "room-decompress", "room-home-node-controls", "room-documents"]

    def test_the_text_leaks_nothing_private(self, walk):
        text = json.dumps(walk)
        for needle in ("C:\\\\Users", "/home/", "@", "sk-", "BEGIN PRIVATE"):
            assert needle not in text, needle


# ----------------------------------------------------------------------------- results

def _results(walk, check_states=None, marks=None, controls_ok=True):
    ids = sm.all_check_ids(walk)
    checks = [{"id": cid, "what": "w", "state": (check_states or {}).get(cid, sm.PASS), "detail": "d", "source": "s",
               "observed_utc": "2026-11-23T00:00:00Z"} for cid in ids]
    inputs = {"generated_utc": "2026-11-23T00:00:00Z", "described": {}}
    return sm.build_results(walk, checks, marks or {}, inputs, {"ok": controls_ok, "problems": []}, "x.json",
                            {"path": "m.json", "date": "2026-11-23"} if marks else None)


class TestResults:
    def test_all_smoke_passing_never_moves_a_walk_cell(self, walk):
        r = _results(walk)
        assert r["summary"]["checks"]["fail"] == 0
        assert {c["walk_state"] for c in r["cells"]} == {"not_tested"}
        assert r["summary"]["line"] == "cells passed / cells not closed by design = 0 / 24"

    def test_cells_without_checks_say_not_run_not_pass(self, walk):
        r = _results(walk)
        by = {c["id"]: c for c in r["cells"]}
        assert by["L02"]["smoke_result"] == sm.NOT_RUN and by["L15"]["smoke_result"] == sm.NOT_RUN
        assert by["L01"]["smoke_result"] == sm.PASS

    def test_a_failed_control_makes_every_cell_unknown(self, walk):
        r = _results(walk, controls_ok=False)
        assert all(c["smoke_result"] in (sm.UNKNOWN, sm.NOT_RUN) for c in r["cells"])
        assert not any(c["smoke_result"] == sm.PASS for c in r["cells"])

    def test_one_failing_check_fails_its_cells_only(self, walk):
        r = _results(walk, {"local.hub.healthz": sm.FAIL})
        failed = {c["id"] for c in r["cells"] if c["smoke_result"] == sm.FAIL}
        want = {c["id"] for _, c in sm.walk_cells(walk) if "local.hub.healthz" in c["checks"]}
        assert failed == want and "L01" not in failed

    def test_marks_move_the_walk_and_only_the_walk(self, walk):
        every = {s["id"]: "pass" for s in walk["lines"][0]["steps"]}
        r = _results(walk, {"node.shell.one_ai_entry": sm.FAIL}, marks=every)
        by = {c["id"]: c for c in r["cells"]}
        assert by["L01"]["walk_state"] == "pass" and by["L01"]["smoke_result"] == sm.FAIL
        assert by["L02"]["walk_state"] == "not_tested"
        assert by["L01"]["walk_steps"] == {"total": 3, "marked": 3}
        assert r["summary"]["line"].startswith("cells passed / cells not closed by design = 1 / 24")

    def test_a_cell_with_one_step_missing_is_not_a_pass(self, walk):
        steps = walk["lines"][0]["steps"]
        r = _results(walk, marks={steps[0]["id"]: "pass", steps[1]["id"]: "pass"})
        assert {c["id"]: c for c in r["cells"]}["L01"]["walk_state"] == "not_tested"

    def test_closed_by_design_lowers_the_denominator(self, walk):
        marks = {s["id"]: "closed_by_design" for s in walk["lines"][13]["steps"]}
        r = _results(walk, marks=marks)
        assert r["summary"]["line"] == "cells passed / cells not closed by design = 0 / 23"

    def test_the_scoreboard_cell_id_travels_with_each_cell(self, walk):
        r = _results(walk)
        assert [c["scoreboard_cell"] for c in r["cells"]][:2] == ["line-01", "line-02"]
        assert all(c["scoreboard_cell"] for c in r["cells"])

    def test_exit_code(self, walk):
        assert sm.exit_code(_results(walk)) == 0
        assert sm.exit_code(_results(walk, {"local.hub.healthz": sm.FAIL})) == 1
        assert sm.exit_code(_results(walk, {"local.hub.healthz": sm.UNKNOWN})) == 2
        assert sm.exit_code(_results(walk, controls_ok=False)) == 2

    def test_cell_files_are_named_by_the_scoreboard_cell(self, walk):
        r = _results(walk)
        files = sm.cell_files(r, walk, {})
        assert sorted(files) == sorted(v + ".json" for v in walk["scoreboard_cells"].values())
        one = files["room-atlas.json"]
        assert one["schema"] == sm.SCHEMA_CELL and one["cell"]["id"] == "R02"
        assert [s["id"] for s in one["steps"]] == ["R02.1", "R02.2", "R02.3", "R02.4"]
        assert {s["walk_state"] for s in one["steps"]} == {"not_tested"}
        assert [c["id"] for c in one["checks"]] == one["cell"]["smoke_checks"]


class _Args:
    def __init__(self, **k):
        self.walk = WALK_PATH
        self.out = None
        self.cells_dir = None
        self.hub_root = self.hub_rev = self.artifacts_root = self.library_root = self.doc04 = None
        self.acceptance_json = self.vault_sync_json = self.marks = None
        self.model_call = False
        self.__dict__.update(k)


def test_a_whole_run_in_an_environment_where_nothing_answers_passes_nothing(tmp_path, capsys):
    out = tmp_path / "r" / "results.json"
    cells = tmp_path / "cells"
    code = sm.cmd_run(_Args(out=str(out), cells_dir=str(cells)), env=sm._Fake("absent"))
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema"] == sm.SCHEMA_RESULTS and data["controls_ok"] is True
    assert len(data["cells"]) == 24
    assert data["summary"]["checks"]["pass"] == 0, [c for c in data["checks"] if c["state"] == "pass"]
    assert {c["walk_state"] for c in data["cells"]} == {"not_tested"}
    assert not any(c["smoke_result"] == "pass" for c in data["cells"])
    assert code in (1, 2)
    assert len(list(cells.iterdir())) == 24
    capsys.readouterr()


class _ReadsFiles(sm._Fake):
    """Everything absent on the network, but the owner's marks file can be read from disk."""
    def read_text(self, path, limit=2 * 1024 * 1024):
        return sm.RealEnv().read_text(path, limit)


def test_a_run_with_the_owners_marks_reads_them(tmp_path, walk, capsys):
    marks = tmp_path / "marks.json"
    steps = {s["id"]: {"state": "pass", "proof": "p"} for s in walk["lines"][6]["steps"]}
    marks.write_text(json.dumps({"schema": "firstwalk.marks/1", "marks": steps}), encoding="utf-8")
    out = tmp_path / "results.json"
    sm.cmd_run(_Args(out=str(out), marks=str(marks)), env=_ReadsFiles("absent"))
    by = {c["id"]: c for c in json.loads(out.read_text(encoding="utf-8"))["cells"]}
    assert by["L07"]["walk_state"] == "pass" and by["L06"]["walk_state"] == "not_tested"
    assert json.loads(out.read_text(encoding="utf-8"))["inputs"]["marks"]["steps_marked"] == 1
    capsys.readouterr()


@pytest.mark.parametrize("content", [None, "not json", '{"schema": "firstwalk.marks/9", "marks": {"L01.1": "pass"}}',
                                     '{"schema": "firstwalk.marks/1", "marks": {}}'])
def test_a_marks_file_that_reads_as_nothing_is_an_error_not_a_quiet_not_tested(tmp_path, capsys, content):
    marks = tmp_path / "marks.json"
    if content is not None:
        marks.write_text(content, encoding="utf-8")
    out = tmp_path / "results.json"
    code = sm.cmd_run(_Args(out=str(out), marks=str(marks)), env=_ReadsFiles("absent"))
    assert code == 3 and not out.exists()
    assert "Nothing was written" in capsys.readouterr().err


def test_the_cli_controls_command_runs():
    p = subprocess.run([sys.executable, "-B", os.path.join(_ROOT, "smoke.py"), "controls"], capture_output=True, text=True, timeout=60)
    assert p.returncode == 0 and "controls ok" in p.stdout


# ----------------------------------------------------------------------------- the generated pages

class TestRender:
    def test_the_committed_pages_match_the_data(self, walk):
        assert rd.check(walk) == [], "run: python firstwalk/render.py --write"

    def test_a_hand_edited_page_is_noticed(self, walk, tmp_path):
        rd.write(walk, str(tmp_path))
        assert rd.check(walk, str(tmp_path)) == []
        p = tmp_path / rd.MD_NAME
        p.write_text(p.read_text(encoding="utf-8").replace("L01.1", "L01.X", 1), encoding="utf-8")
        assert rd.check(walk, str(tmp_path)) == [rd.MD_NAME]
        (tmp_path / rd.HTML_NAME).unlink()
        assert rd.check(walk, str(tmp_path)) == [rd.MD_NAME, rd.HTML_NAME]

    def test_crlf_checkouts_do_not_read_as_drift(self, walk, tmp_path):
        rd.write(walk, str(tmp_path))
        p = tmp_path / rd.MD_NAME
        p.write_bytes(p.read_bytes().replace(b"\n", b"\r\n"))
        assert rd.check(walk, str(tmp_path)) == []

    def test_a_changed_datum_changes_the_page(self, walk):
        other = copy.deepcopy(walk)
        other["lines"][0]["steps"][0]["do"] = "Do something else entirely."
        assert rd.render_md(other) != rd.render_md(walk) and rd.render_html(other) != rd.render_html(walk)

    def test_cli_check_and_write(self, walk, tmp_path):
        script = os.path.join(_ROOT, "render.py")
        bad = subprocess.run([sys.executable, "-B", script, "--check", "--out-dir", str(tmp_path)], capture_output=True, text=True)
        assert bad.returncode == 1 and "DRIFT" in bad.stdout
        ok = subprocess.run([sys.executable, "-B", script, "--write", "--out-dir", str(tmp_path)], capture_output=True, text=True)
        assert ok.returncode == 0
        again = subprocess.run([sys.executable, "-B", script, "--check", "--out-dir", str(tmp_path)], capture_output=True, text=True)
        assert again.returncode == 0

    def test_markdown_has_every_step_every_named_thing_and_every_mockup(self, walk):
        md = rd.render_md(walk)
        for sid in rd.step_ids(walk):
            assert "| %s |" % sid in md, sid
        for n in walk["named"]:
            assert "| %s |" % n["id"] in md
        for m in walk["mockups"]:
            assert m["artifact_id"] in md
        assert md.count("[ ] pass [ ] fail [ ] closed by design") == len(rd.step_ids(walk))

    def test_html_has_one_radio_set_and_one_proof_field_per_step(self, walk):
        page = rd.render_html(walk)
        for sid in rd.step_ids(walk):
            assert 'data-step="%s"' % sid in page
            for state, _ in rd.STATES:
                assert 'name="m-%s" value="%s"' % (sid, state) in page
        assert page.count('type="text"') == len(rd.step_ids(walk))
        assert page.count('data-step="') == len(rd.step_ids(walk))

    def test_html_default_for_every_step_is_not_tested(self, walk):
        page = rd.render_html(walk)
        assert page.count(' value="not_tested" checked') == len(rd.step_ids(walk))
        assert ' value="pass" checked' not in page

    def test_html_is_self_contained(self, walk):
        page = rd.render_html(walk)
        for needle in ("<script src", "<link ", "@import", "src=\"http", "src='http", "url(http", "fetch(", "XMLHttpRequest",
                       "sendBeacon", "WebSocket", "<img", "<iframe"):
            assert needle not in page, needle
        hrefs = set(re.findall(r'href="([^"]+)"', page))
        assert all(h.startswith("#") or h.startswith(rd.ARTIFACT_URL) for h in hrefs), hrefs

    def test_html_storage_is_guarded_and_the_export_schema_is_the_one_smoke_reads(self, walk):
        page = rd.render_html(walk)
        assert "try { store = window.localStorage; store.getItem(KEY); } catch (e) { store = null; }" in page
        assert 'SCHEMA = "%s"' % sm.SCHEMA_MARKS in page and rd.SCHEMA_MARKS == sm.SCHEMA_MARKS
        # every touch of storage sits inside a try block
        js = page.split("<script>")[1]
        for m in re.finditer(r"store\.(getItem|setItem)", js):
            head = js[:m.start()]
            assert head.rfind("try {") > head.rfind("} catch"), "unguarded storage access near offset %d" % m.start()

    def test_the_page_script_rolls_up_like_the_python(self, walk):
        node = shutil.which("node")
        if not node:
            pytest.skip("node is not installed: the page's rollup() was not compared with smoke.rollup()")
        js = rd.JS
        start = js.index("function rollup")
        end = js.index("var LABEL")
        fn = js[start:end]
        states = ["not_tested", "pass", "fail", "closed_by_design"]
        combos = [[]] + [[a] for a in states] + [[a, b] for a in states for b in states] + \
                 [[a, b, c] for a in states for b in states for c in states]
        prog = fn + "\nvar combos = %s;\nconsole.log(JSON.stringify(combos.map(rollup)));" % json.dumps(combos)
        p = subprocess.run([node, "-e", prog], capture_output=True, text=True, timeout=60)
        assert p.returncode == 0, p.stderr
        assert json.loads(p.stdout) == [sm.rollup(c) for c in combos]

    def test_the_page_script_has_no_syntax_error(self):
        node = shutil.which("node")
        if not node:
            pytest.skip("node is not installed: the page script was not parsed")
        p = subprocess.run([node, "-e", "new Function(%s)" % json.dumps(rd.JS)], capture_output=True, text=True, timeout=60)
        assert p.returncode == 0, p.stderr
