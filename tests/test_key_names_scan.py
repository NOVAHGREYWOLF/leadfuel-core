"""VAULT P11: the name scan reports names and places only, says unknown when blind, has no network."""
import ast
import importlib.util
import io
import json
import os
import sys

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "vault", "key_names_scan.py")
_spec = importlib.util.spec_from_file_location("key_names_scan", _PATH)
k = importlib.util.module_from_spec(_spec)
sys.modules["key_names_scan"] = k
_spec.loader.exec_module(k)

FAKE = "sk-ant-api03-" + "Zq" * 20  # synthetic


def w(p, t):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as fh:
        fh.write(t)


def test_finds_names_and_never_prints_values(tmp_path):
    w(str(tmp_path / "a" / ".env"), f"X=1\nANTHROPIC_API_KEY={FAKE}\nADMIN_PASSWORD=$ADMIN\n")
    w(str(tmp_path / "b.md"), "the variable ANTHROPIC_ADMIN_KEY is hub-only\n")
    rep = k.scan([str(tmp_path)])
    assert rep["status"] == "found"
    by = {(os.path.basename(h["path"]), h["name"]): h for h in rep["hits"]}
    assert by[(".env", "ANTHROPIC_API_KEY")]["literal_on_line"] is True
    assert by[(".env", "ANTHROPIC_API_KEY")]["line"] == 2
    assert by[(".env", "ADMIN_PASSWORD")]["literal_on_line"] is False
    assert by[("b.md", "ANTHROPIC_ADMIN_KEY")]["literal_on_line"] is False
    assert FAKE not in json.dumps(rep)


def test_clean_unknown(tmp_path):
    w(str(tmp_path / "ok.txt"), "nothing here\n")
    assert k.scan([str(tmp_path)])["status"] == "clean"
    assert k.scan([str(tmp_path / "missing")])["status"] == "unknown"
    empty = tmp_path / "empty"
    empty.mkdir()
    assert k.scan([str(empty)])["status"] == "unknown"  # zero files seen is blind, not clean


def test_check_env_kind_only():
    r = k.check_env({"ANTHROPIC_API_KEY": FAKE, "ADMIN_PASSWORD": "hunter2"})
    assert r["env"]["ANTHROPIC_API_KEY"] == {"set": True, "kind": "api key"}
    assert r["env"]["ADMIN_PASSWORD"] == {"set": True, "kind": "n/a"}
    assert r["env"]["ANTHROPIC_ADMIN_KEY"] == {"set": False}
    assert FAKE not in json.dumps(r) and "hunter2" not in json.dumps(r)


def test_checklist_names_owner_step():
    buf = io.StringIO()
    assert k.main(["checklist"], out=buf) == 0
    assert "OWNER-STEP" in buf.getvalue()


def test_no_network_or_process_imports():
    with open(_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    mods = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)}
    assert not mods & {"socket", "urllib", "http", "requests", "subprocess", "ssl", "httpx", "ctypes"}
