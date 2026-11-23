"""NODE cluster (c): the local-model route says local only for plainly mechanical work, talks to
loopback only, and never falls through to anything else."""
import importlib.util
import inspect
import os
import re
import sys

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "node", "local_route.py")
_spec = importlib.util.spec_from_file_location("local_route", _PATH)
lr = importlib.util.module_from_spec(_spec)
sys.modules["local_route"] = lr   # dataclasses look the module up by name
_spec.loader.exec_module(lr)


@pytest.mark.parametrize("task", [
    {"title": "lint sweep of docs/", "effort": "low"},
    {"title": "fix typos in README"},
    {"title": "anything", "kind": "bump"},
    {"title": "reformat whitespace in node/"},
])
def test_mechanical_work_is_local(task):
    assert lr.classify(task).route == "local"


@pytest.mark.parametrize("task,why", [
    ({"title": "docs for the auth flow"}, "risk"),
    ({"title": "lint the migration chain"}, "risk"),
    ({"title": "README for the deploy workflow"}, "risk"),
    ({"title": "typo in spend gate message"}, "risk"),
    ({"title": "docs sweep of the doors"}, "risk"),
    ({"title": "lint sweep", "effort": "high"}, "effort"),
    ({"title": "lint sweep", "model_pin": "opus"}, "model_pin"),
    ({"title": "build the feature flag page"}, "no mechanical"),
    ({}, "no title"),
    ("lint", "not an object"),
])
def test_everything_else_is_not_local(task, why):
    r = lr.classify(task)
    assert r.route == "not-local"
    assert why in r.why


@pytest.mark.parametrize("ep", [
    "http://127.0.0.1:11434", "http://localhost:11434", "http://[::1]:11434", "http://127.0.0.2:1",
])
def test_loopback_endpoints_accepted(ep):
    assert lr.check_endpoint(ep) == ep


@pytest.mark.parametrize("ep", [
    "https://api.openai.com", "http://8.8.8.8:11434", "http://example.com:11434",
    "http://10.20.0.53:11434", "ftp://127.0.0.1", "127.0.0.1:11434",
])
def test_non_local_endpoints_refused_before_connecting(ep):
    calls = []
    with pytest.raises(lr.NotLocal):
        lr.LocalModel(ep, http=lambda *a: calls.append(a))
    assert calls == []


def test_named_lan_host_only_when_private():
    assert lr.check_endpoint("http://10.20.0.53:11434", allow_lan=("10.20.0.53",))
    with pytest.raises(lr.NotLocal):
        lr.check_endpoint("http://8.8.8.8:11434", allow_lan=("8.8.8.8",))


def _fake(ps_models, gen=None, fail_gen=False):
    seen = []

    def http(method, url, body, timeout):
        seen.append((method, url))
        assert url.startswith("http://127.0.0.1:11434/")
        if url.endswith("/api/ps"):
            return {"models": ps_models}
        if fail_gen:
            raise lr.LocalUnavailable("connection refused")
        return gen if gen is not None else {"response": "ok", "eval_count": 3}
    return http, seen


M = lr.DEFAULT_MODEL


@pytest.mark.parametrize("models,want", [
    ([{"name": M, "size": 100, "size_vram": 100}], "gpu"),
    ([{"name": M, "size": 100, "size_vram": 40}], "partial"),
    ([{"name": M, "size": 100, "size_vram": 0}], "cpu"),
    ([], "unknown"),                                       # not loaded: cannot see it
    ([{"name": "other:1b", "size": 1, "size_vram": 1}], "unknown"),
    ([{"name": M}], "unknown"),                            # fields missing
    ([{"name": M, "size": 0, "size_vram": 0}], "unknown"),
])
def test_placement_says_unknown_when_it_cannot_see(models, want):
    http, _ = _fake(models)
    assert lr.LocalModel(http=http).placement() == want


def test_placement_unknown_when_ollama_down():
    def http(*a):
        raise lr.LocalUnavailable("down")
    assert lr.LocalModel(http=http).placement() == "unknown"


def test_run_returns_response_and_placement():
    http, seen = _fake([{"name": M, "size": 10, "size_vram": 10}])
    out = lr.LocalModel(http=http).run("hi", require_gpu=True)
    assert out["response"] == "ok" and out["placement"] == "gpu"
    assert ("POST", "http://127.0.0.1:11434/api/generate") in seen


@pytest.mark.parametrize("models", [
    [{"name": M, "size": 10, "size_vram": 0}], [{"name": M, "size": 10, "size_vram": 5}], [],
])
def test_require_gpu_refuses_cpu_partial_and_unknown(models):
    http, _ = _fake(models)
    with pytest.raises(lr.LocalUnavailable):
        lr.LocalModel(http=http).run("hi", require_gpu=True)


def test_failure_raises_and_calls_nothing_else():
    http, seen = _fake([], fail_gen=True)
    with pytest.raises(lr.LocalUnavailable):
        lr.LocalModel(http=http).run("hi")
    assert seen == [("POST", "http://127.0.0.1:11434/api/generate")]


def test_answer_without_response_is_unavailable():
    http, _ = _fake([], gen={"error": "model not found"})
    with pytest.raises(lr.LocalUnavailable):
        lr.LocalModel(http=http).run("hi")


def test_no_vendor_path_in_the_module():
    src = inspect.getsource(lr)
    for word in ("anthropic", "openai", "api.", "https://", "fallback("):
        assert word not in src.lower().replace("never a fallback", ""), word
    assert re.findall(r"http://[^\s\"']+", src) == ["http://127.0.0.1:11434",
                                                   "http://<loopback>:<port>"]


def test_cli_classify_exit_codes(capsys):
    assert lr.main(["classify", '{"title": "lint sweep"}']) == 0
    assert lr.main(["classify", '{"title": "deploy docs"}']) == 1
