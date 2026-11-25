"""NODE cluster files part 2 rules: one heavy slot per machine pass, refused when held or unknown, in-use
machines left alone by day, every remote scan under nice/ionice. Nothing here starts a scan."""
import datetime as dt
import importlib.util
import json
import os
import subprocess
import sys

import pytest

_NODE = os.path.join(os.path.dirname(__file__), os.pardir, "node")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_NODE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


ss = _load("cluster_scan_slot")


class Calls:
    """A fake `run` that plays heavy_lock.py: status text, acquire (writes the token file), release."""

    def __init__(self, status="slot-1: free\nhub CI: idle\n", status_rc=0, acquire_rc=0):
        self.status, self.status_rc, self.acquire_rc, self.log = status, status_rc, acquire_rc, []

    def __call__(self, argv, **k):
        self.log.append(argv[2] if len(argv) > 2 else argv)
        if argv[2] == "status":
            return subprocess.CompletedProcess(argv, self.status_rc, self.status, "")
        if argv[2] == "acquire":
            if self.acquire_rc == 0:
                with open(argv[argv.index("--token-file") + 1], "w", encoding="utf-8") as f:
                    f.write("tok-123")
            return subprocess.CompletedProcess(argv, self.acquire_rc, "granted" if self.acquire_rc == 0 else "refused: held", "")
        return subprocess.CompletedProcess(argv, 0, "released", "")


@pytest.fixture
def lock_py(tmp_path):
    p = tmp_path / "heavy_lock.py"
    p.write_text("# reads actions/runners\n", encoding="utf-8")
    return str(p)


def test_slot_held_then_released_even_on_error(lock_py):
    c = Calls()
    with pytest.raises(RuntimeError):
        with ss.scan_slot("pass-1", lock_py, run=c) as tok:
            assert tok == "tok-123"
            raise RuntimeError("scan blew up")
    assert c.log == ["status", "acquire", "release"], "the slot is released when the pass fails"


@pytest.mark.parametrize("status,rc,state", [
    ("slot-1: live pid 5 job gates\n", 0, "held"),
    ("slot-1: free\nhub CI: unknown\n", 0, "unknown"),
    ("", 1, "unknown"),
])
def test_held_and_unknown_refuse_and_never_acquire(lock_py, status, rc, state):
    c = Calls(status=status, status_rc=rc)
    with pytest.raises(ss.SlotRefused) as e:
        with ss.scan_slot("p", lock_py, run=c):
            pytest.fail("must not run the pass")
    assert e.value.state == state and c.log == ["status"]


def test_acquire_refused_after_free_status_is_refused(lock_py):
    c = Calls(acquire_rc=3)
    with pytest.raises(ss.SlotRefused):
        with ss.scan_slot("p", lock_py, run=c):
            pytest.fail("must not run the pass")
    assert "release" not in c.log


def test_no_lock_path_or_stale_lock_script_is_unknown(tmp_path):
    with pytest.raises(ss.SlotRefused) as e:
        with ss.scan_slot("p", "", run=Calls()):
            pytest.fail("no pass without a lock file")
    assert e.value.state == "unknown"
    stale = tmp_path / "heavy_lock.py"
    stale.write_text("# old, no GitHub runners read\n", encoding="utf-8")
    with pytest.raises(ss.SlotRefused) as e:
        with ss.scan_slot("p", str(stale), run=Calls()):
            pytest.fail("a stale lock script must not read as free")
    assert "stale" in e.value.why


def test_in_use_machine_only_outside_working_hours():
    pc = {"id": "greywolf", "os": "windows", "scan": {"in_use": True}}
    srv = {"id": "r710-1", "os": "linux", "scan": {"in_use": False}}
    noon, night = dt.datetime(2026, 11, 24, 12, 0), dt.datetime(2026, 11, 24, 23, 30)
    assert ss.scan_allowed(pc, noon)[0] is False and ss.scan_allowed(pc, night)[0] is True
    assert ss.scan_allowed(srv, noon)[0] is True
    assert ss.scan_allowed(pc, dt.datetime(2026, 11, 24, 7, 59))[0] is True
    assert ss.scan_allowed(pc, dt.datetime(2026, 11, 24, 8, 0))[0] is False


def test_undeclared_policy_is_treated_as_in_use():
    ok, why = ss.scan_allowed({"id": "x", "os": "linux"}, dt.datetime(2026, 11, 24, 12, 0))
    assert ok is False and "no scan policy" in why
    assert ss.scan_policy({"id": "x", "scan": {"in_use": "yes"}})["declared"] is False


def test_throttle_prefix_and_plan_lists_every_machine():
    assert ss.throttle_argv({"os": "linux"}) == ["nice", "-n", "19", "ionice", "-c3"]
    assert "Idle" in ss.WINDOWS_THROTTLE
    with pytest.raises(ValueError):
        ss.throttle_argv({"os": "windows"})
    ms = [{"id": "a", "os": "linux", "scan": {"in_use": False}, "route": {"kind": "ssh"}},
          {"id": "b", "os": "linux", "scan": {"in_use": False}, "route": {"kind": "none"}},
          {"id": "c", "os": "windows", "scan": {"in_use": True}, "route": {"kind": "local"}}]
    p = ss.plan(ms, dt.datetime(2026, 11, 24, 12, 0))
    assert [(x["machine"], x["go"]) for x in p] == [("a", True), ("b", False), ("c", False)]
    assert "no route" in p[1]["why"]


def test_targets_file_declares_a_scan_policy_for_every_machine():
    d = json.load(open(os.path.join(_NODE, "cluster_inventory_targets.json"), encoding="utf-8"))
    for m in d["machines"]:
        assert ss.scan_policy(m)["declared"], m["id"]
    pol = {m["id"]: m["scan"]["in_use"] for m in d["machines"]}
    assert pol["greywolf"] and pol["surface"] and pol["msi"] and not pol["r710-1"]
