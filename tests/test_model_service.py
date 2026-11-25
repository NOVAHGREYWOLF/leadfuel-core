"""fold-c-G03: one local model service, one address in one file. Nothing leaves the private network, and
with no usable service the resolver raises instead of reaching for anything else. Each "never" has a
positive control (same fixture, one fact changed)."""
import ast
import copy
import importlib.util
import io
import json
import os

import pytest

_HERE = os.path.dirname(__file__)
_NODE = os.path.join(_HERE, os.pardir, "node")
_spec = importlib.util.spec_from_file_location("model_service", os.path.join(_NODE, "model_service.py"))
ms = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ms)


def _shipped():
    return ms.load(os.path.join(_NODE, "model_service.json"))


def _data(**over):
    d = {"schema": "model-service-1", "one": "a", "services": [
        {"id": "a", "base_url": "http://overlord:8080/v1", "enabled": True, "scheduled_ok": True},
        {"id": "b", "base_url": "http://127.0.0.1:11434/v1", "enabled": True, "scheduled_ok": False}]}
    d.update(over)
    return d


def _write(tmp_path, d):
    p = tmp_path / "ms.json"
    p.write_text(json.dumps(d))
    return str(p)


def test_shipped_file_loads_and_names_one_service():
    d = _shipped()
    assert d["one"] == "overlord-gpu"
    assert sum(1 for s in d["services"] if s["id"] == d["one"]) == 1


def test_shipped_file_does_not_claim_the_overlord_service_is_live():
    # it is not deployed (W09); enabling it is the owner's one-word edit, not ours
    one = {s["id"]: s for s in _shipped()["services"]}["overlord-gpu"]
    assert one["enabled"] is False


def test_shipped_resolves_to_the_interim_for_the_shell_and_refuses_scheduled_work():
    d = _shipped()
    assert ms.resolve(d)["id"] == "greywolf-ollama"
    with pytest.raises(ms.NoModelService):
        ms.resolve(d, scheduled=True)   # nothing on a schedule may depend on GREYWOLF being on


@pytest.mark.parametrize("url", [
    "http://127.0.0.1:11434/v1", "http://localhost:11434/v1", "http://overlord:8080/v1",
    "http://10.0.0.5:8080/v1", "http://192.168.1.9/v1", "http://100.100.1.2:8080/v1",
    "http://box.lan:8080/v1", "http://[::1]:8080/v1", "http://x.tail1234.ts.net/v1"])
def test_private_addresses_are_accepted(url):
    assert ms.check_base_url(url) == url.rstrip("/")


@pytest.mark.parametrize("url", [
    "https://api.openai.com/v1", "https://api.anthropic.com", "http://8.8.8.8/v1", "http://example.com:8080/v1",
    "http://172.32.0.1/v1", "ftp://overlord/v1", "http://user:pw@overlord/v1", "overlord:8080", ""])
def test_public_or_odd_addresses_are_refused(url):
    with pytest.raises(ms.ModelServiceError):
        ms.check_base_url(url)


def test_a_vendor_url_in_the_file_is_refused_when_the_file_is_read(tmp_path):
    d = _data()
    d["services"][0]["base_url"] = "https://api.openai.com/v1"
    with pytest.raises(ms.ModelServiceError):
        ms.load(_write(tmp_path, d))
    assert ms.load(_write(tmp_path, _data()))     # positive control


def test_the_one_wins_when_enabled():
    assert ms.resolve(_data())["id"] == "a"


def test_the_one_off_falls_to_the_next_allowed_service_and_scheduled_skips_the_unfit_one():
    d = _data()
    d["services"][0]["enabled"] = False
    assert ms.resolve(d)["id"] == "b"
    with pytest.raises(ms.NoModelService):
        ms.resolve(d, scheduled=True)


def test_nothing_enabled_raises_and_names_why_never_a_default():
    d = _data()
    for s in d["services"]:
        s["enabled"] = False
    with pytest.raises(ms.NoModelService) as e:
        ms.resolve(d)
    assert "no model service" in str(e.value)


def test_enabled_must_be_exactly_true():
    d = _data()
    d["services"][0]["enabled"] = "yes"
    d["services"][1]["enabled"] = 1
    with pytest.raises(ms.NoModelService):
        ms.resolve(d)


@pytest.mark.parametrize("mut", [
    lambda d: d.update(schema="x"), lambda d: d.update(one="zzz"), lambda d: d.update(services=[]),
    lambda d: d["services"].append(copy.deepcopy(d["services"][0]))])
def test_malformed_files_are_refused(tmp_path, mut):
    d = _data()
    mut(d)
    with pytest.raises(ms.ModelServiceError):
        ms.load(_write(tmp_path, d))


def test_missing_file_is_an_error_not_a_default(tmp_path):
    with pytest.raises(ms.ModelServiceError):
        ms.load(str(tmp_path / "nope.json"))


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_probe_reads_model_ids_from_the_validated_address_only():
    seen = []

    def opener(url, timeout):
        seen.append(url)
        return _Resp(json.dumps({"data": [{"id": "qwen3"}, {"id": "mistral"}]}).encode())

    assert ms.probe({"base_url": "http://overlord:8080/v1"}, opener=opener) == ["mistral", "qwen3"]
    assert seen == ["http://overlord:8080/v1/models"]
    with pytest.raises(ms.ModelServiceError):
        ms.probe({"base_url": "https://api.openai.com/v1"}, opener=opener)
    assert len(seen) == 1                                  # the refused one never opened


def test_cli_exit_codes(tmp_path, capsys):
    p = _write(tmp_path, _data())
    assert ms.main(["--file", p, "resolve"]) == 0
    assert capsys.readouterr().out.strip() == "http://overlord:8080/v1"
    d = _data()
    d["services"][0]["enabled"] = False
    d["services"][1]["enabled"] = False
    assert ms.main(["--file", _write(tmp_path, d), "resolve"]) == 2
    assert ms.main(["--file", p, "probe", "nope"]) == 2


def test_only_probe_opens_a_socket():
    tree = ast.parse(open(os.path.join(_NODE, "model_service.py"), encoding="utf-8").read())
    for fn in [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]:
        names = {n.attr for n in ast.walk(fn) if isinstance(n, ast.Attribute)} | \
                {n.id for n in ast.walk(fn) if isinstance(n, ast.Name)}
        uses = "urlopen" in names or "opener" in names
        if fn.name == "probe":
            assert uses
        elif fn.name != "main":
            assert not uses, fn.name
    src = open(os.path.join(_NODE, "model_service.py"), encoding="utf-8").read()
    for banned in ("import socket", "subprocess", "requests", "ssh "):
        assert banned not in src


def test_default_opener_refuses_redirects_and_ignores_proxy_env(monkeypatch):
    import http.server
    import threading
    import urllib.error
    hits = []

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            hits.append(self.path)
            if self.path == "/redir":
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:1/elsewhere")
                self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(b"{}")

        def log_message(self, *a):
            pass

    srv = http.server.HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    try:
        with pytest.raises(urllib.error.HTTPError) as ei:      # a redirect is refused, not followed
            ms._default_opener(base + "/redir", 5)
        assert ei.value.code == 302
        for k in ("HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy", "ALL_PROXY"):
            monkeypatch.setenv(k, "http://127.0.0.1:9")        # a dead proxy would break a proxied call
        monkeypatch.setenv("NO_PROXY", "")
        with ms._default_opener(base + "/ok", 5) as r:
            assert r.status == 200
    finally:
        srv.shutdown()
