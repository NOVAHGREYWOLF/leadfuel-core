"""oss-3: the llama-swap + LiteLLM files list local endpoints only and no fallback of any kind."""
import importlib.util
import os
import sys

import pytest

_ROOT = os.path.join(os.path.dirname(__file__), os.pardir, "node")
_spec = importlib.util.spec_from_file_location("gateway_guard", os.path.join(_ROOT, "gateway_guard.py"))
g = importlib.util.module_from_spec(_spec)
sys.modules["gateway_guard"] = g
_spec.loader.exec_module(g)

with open(os.path.join(_ROOT, "gateway", "litellm_config.yaml"), encoding="utf-8") as _fh:
    GOOD = _fh.read()
with open(os.path.join(_ROOT, "gateway", "llama-swap.yaml"), encoding="utf-8") as _fh:
    SWAP = _fh.read()


def _bad(extra="", base="http://overlord:8080/v1", model="openai/local-small", key="none"):
    return (GOOD.replace("general_settings: {}", extra + "\ngeneral_settings: {}")
            .replace("openai/local-small", model, 1)
            .replace("http://overlord:8080/v1", base, 1)
            .replace("api_key: none", "api_key: " + key, 1))


def test_shipped_files_are_clean():
    assert g.check_dir(os.path.join(_ROOT, "gateway")) == []


def test_missing_dir_fails_not_passes(tmp_path):
    assert len(g.check_dir(str(tmp_path))) == 2


def test_shipped_files_parse_as_yaml_when_available():
    yaml = pytest.importorskip("yaml")
    cfg = yaml.safe_load(GOOD)
    assert [m["model_name"] for m in cfg["model_list"]] == ["local-small", "local-code"]
    assert "fallback" not in str(cfg)
    assert set(yaml.safe_load(SWAP)["models"]) == {"local-small", "local-code"}


def test_control_unchanged_text_is_clean():
    assert g.check_litellm(_bad()) == []


@pytest.mark.parametrize("text", [
    _bad(model="anthropic/claude-sonnet"),
    _bad(model="gemini/gemini-pro"),
    _bad(model="gpt-4o"),
    _bad(base="https://api.openai.com/v1"),
    _bad(base="http://8.8.8.8:8080/v1"),
    _bad(base="http://user:pw@overlord:8080/v1"),
    _bad(key="os.environ/OPENAI_API_KEY"),
    _bad(key="sk-abc"),
    _bad(extra="router_settings:\n  fallbacks: [{\"local-small\": [\"gpt-4\"]}]"),
    _bad(extra="  context_window_fallbacks: [{\"local-small\": [\"gpt-4\"]}]"),
    _bad(extra="  success_callback: [\"langfuse\"]"),
    _bad(extra="  master_key: sk-1234"),
    GOOD.replace("telemetry: false", "telemetry: true"),
    GOOD.replace("telemetry: false", "num_retries: 0"),
    GOOD.replace("      api_base: http://overlord:8080/v1\n", "", 1),
])
def test_cloud_shaped_config_is_refused(text):
    assert g.check_litellm(text), text


def test_local_to_local_fallback_also_refused():
    assert g.check_litellm(_bad(extra="  fallbacks: [{\"local-small\": [\"local-code\"]}]"))


def test_lan_names_and_loopback_allowed():
    for base in ("http://127.0.0.1:8080/v1", "http://100.64.1.2:8080/v1", "http://box.local:8080/v1"):
        assert g.check_litellm(_bad(base=base)) == []


def test_llama_swap_cmd_may_not_fetch():
    assert g.check_llama_swap(SWAP) == []
    assert g.check_llama_swap(SWAP + '  "x":\n    cmd: llama-server --hf-repo a/b\n')
    assert g.check_llama_swap(SWAP + '  "y":\n    cmd: llama-server -m https://x/y.gguf\n')
    assert g.check_llama_swap("healthCheckTimeout: 1\n")


def test_guard_opens_no_socket():
    with open(os.path.join(_ROOT, "gateway_guard.py"), encoding="utf-8") as fh:
        src = fh.read()
    for word in ("import socket", "urlopen", "import requests", "subprocess"):
        assert word not in src


def test_cli_exit_codes(tmp_path):
    assert g.main([]) == 0
    assert g.main(["--dir", str(tmp_path)]) == 1
