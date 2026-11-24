"""NODE cluster-job-router: the decision core sends test/lint/build jobs to VM 102 or, when they are
free and enabled, the R620/R710; small mechanical work to the local model; and waits otherwise.
Unknown is never free, the heavy lock is honoured, and there is no cloud path at all."""
import ast
import importlib.util
import io
import json
import os
import sys
import tarfile

import pytest

_HERE = os.path.dirname(__file__)
_NODE = os.path.join(_HERE, os.pardir, "node")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_NODE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


cr = _load("cluster_route")

VM = {"id": "vm102", "ssh": "ci-vm", "exec": "docker", "image": "python:3.12-slim",
      "python": "python", "enabled": True, "counts_runners": True, "cpus": 8, "memory_gb": 8,
      "max_load_frac": 0.5}
R620 = {"id": "r620", "ssh": "pve-r620", "exec": "plain", "python": "python3", "enabled": True,
        "counts_runners": False, "max_load_frac": 0.5}
R710 = dict(R620, id="r710", ssh="pve-ng")
TARGETS = [cr.Target.from_dict(d) for d in (VM, R620, R710)]


def ok(threads=20, load=1.0, workers=0):
    return cr.Facts("ok", "probed", threads, load, workers, 10.0)


def unknown(why="ssh timed out"):
    return cr.Facts("unknown", why, None, None, None, None)


ALL_FREE = {"vm102": ok(), "r620": ok(24, 0.3), "r710": ok(16, 0.2)}


# ------------------------------------------------------------------ placement of CPU jobs
@pytest.mark.parametrize("kind", ["test", "lint", "build"])
def test_vm102_first_when_free(kind):
    d = cr.decide({"kind": kind}, TARGETS, ALL_FREE, heavy_lock="free")
    assert (d.action, d.target) == ("run", "vm102")


def test_busy_vm102_goes_to_r620_then_r710():
    facts = dict(ALL_FREE, vm102=ok(load=15.0))
    assert cr.decide({"kind": "test"}, TARGETS, facts, "free").target == "r620"
    facts["r620"] = ok(24, 20.0)
    assert cr.decide({"kind": "test"}, TARGETS, facts, "free").target == "r710"


def test_heavy_job_does_not_share_vm102_with_a_ci_job():
    facts = dict(ALL_FREE, vm102=ok(load=1.0, workers=1))
    assert cr.decide({"kind": "test", "heavy": True}, TARGETS, facts, "free").target == "r620"
    # positive control: a light job may sit beside an idle-ish CI job
    assert cr.decide({"kind": "lint"}, TARGETS, facts, "free").target == "vm102"


def test_unknown_is_never_picked():
    facts = {"vm102": unknown(), "r620": unknown("not measured"), "r710": unknown()}
    d = cr.decide({"kind": "test"}, TARGETS, facts, "free")
    assert d.action == "wait" and d.target is None
    assert [c[1] for c in d.considered] == ["unknown"] * 3


def test_missing_facts_are_unknown_not_free():
    d = cr.decide({"kind": "test"}, TARGETS, {}, "free")
    assert d.action == "wait"
    assert all(c[1] == "unknown" for c in d.considered)


def test_disabled_target_is_never_picked():
    targets = [cr.Target.from_dict(dict(R620, enabled=False))]
    d = cr.decide({"kind": "test"}, targets, {"r620": ok(24, 0.1)}, "free")
    assert d.action == "wait" and d.considered[0][1] == "disabled"


def test_all_busy_waits_and_never_names_this_machine():
    facts = {k: ok(t, t * 0.9) for k, t in (("vm102", 20), ("r620", 24), ("r710", 16))}
    d = cr.decide({"kind": "build"}, TARGETS, facts, "free")
    assert d.action == "wait" and d.target is None


# ------------------------------------------------------------------ the heavy lock
@pytest.mark.parametrize("state", ["held", "unknown"])
def test_heavy_job_waits_unless_the_lock_is_free(state):
    d = cr.decide({"kind": "test", "heavy": True}, TARGETS, ALL_FREE, heavy_lock=state)
    assert d.action == "wait" and "heavy lock" in d.why


def test_build_is_heavy_by_default():
    assert cr.decide({"kind": "build"}, TARGETS, ALL_FREE, "held").action == "wait"


def test_light_job_does_not_need_the_heavy_lock():
    assert cr.decide({"kind": "lint"}, TARGETS, ALL_FREE, "held").target == "vm102"


@pytest.mark.parametrize("text,rc,want", [
    ("slot-1: free\nhub CI: idle (x)", 0, "free"),
    ("slot-1: live -- gates pid 1\nhub CI: unknown (y)", 0, "held"),
    ("slot-1: stale -- pid 2\nhub CI: idle", 0, "unknown"),
    ("slot-1: unknown -- unreadable", 0, "unknown"),
    ("", 0, "unknown"),
    ("slot-1: free", 2, "unknown"),
    ("garbage", 0, "unknown"),
])
def test_heavy_lock_status_parse(text, rc, want):
    assert cr.parse_heavy_status(text, rc) == want


# ------------------------------------------------------------------ small mechanical work
def test_mechanical_goes_to_the_local_model():
    d = cr.decide({"kind": "mechanical", "title": "lint sweep of docs/", "effort": "low"},
                  TARGETS, ALL_FREE, "free", local_model="up")
    assert (d.action, d.target) == ("run", "local-model")


def test_mechanical_waits_when_the_local_model_is_not_up():
    d = cr.decide({"kind": "mechanical", "title": "fix typos in README"}, TARGETS, ALL_FREE,
                  "free", local_model="unknown")
    assert d.action == "wait" and d.target is None


def test_risky_work_is_refused_not_sent_anywhere_else():
    d = cr.decide({"kind": "mechanical", "title": "rotate the auth tokens"}, TARGETS, ALL_FREE,
                  "free", local_model="up")
    assert d.action == "refuse" and d.target is None
    assert "decision" in d.why


def test_unknown_kind_is_refused():
    assert cr.decide({"kind": "deploy"}, TARGETS, ALL_FREE, "free").action == "refuse"


# ------------------------------------------------------------------ probe parsing
def test_probe_parse_ok():
    f = cr.parse_probe("nproc=20\nload=1.45 5.51 4.79 1/360 99\nworkers=0\nmemavail_kb=22000000\n",
                       counts_runners=True)
    assert (f.state, f.threads, f.load1, f.workers) == ("ok", 20, 1.45, 0)


@pytest.mark.parametrize("text", [
    "",
    "nproc=\nload=1 1 1\nworkers=0\nmemavail_kb=1",
    "nproc=20\nload=x y z\nworkers=0\nmemavail_kb=1",
    "nproc=0\nload=1 1 1\nworkers=0\nmemavail_kb=1",
    "nproc=20\nload=-1 1 1\nworkers=0\nmemavail_kb=1",
    "nproc=20\nload=1 1 1\nworkers=\nmemavail_kb=1",     # runner host must say how many workers
])
def test_probe_parse_unusable_is_unknown(text):
    assert cr.parse_probe(text, counts_runners=True).state == "unknown"


def test_probe_workers_not_needed_on_a_host_without_runners():
    f = cr.parse_probe("nproc=24\nload=0.3 0.3 0.3\nworkers=\nmemavail_kb=1", counts_runners=False)
    assert f.state == "ok"


def test_probe_failure_is_unknown():
    target = TARGETS[0]
    def runner(argv, **kw):
        raise cr.subprocess.TimeoutExpired(argv, 10)
    f = cr.probe(target, run=runner, resolve=lambda alias: "10.20.0.53")
    assert f.state == "unknown" and "timed out" in f.why


def test_probe_nonzero_exit_is_unknown():
    class R:
        returncode, stdout, stderr = 255, "", "Connection refused"
    f = cr.probe(TARGETS[0], run=lambda argv, **kw: R(), resolve=lambda a: "10.20.0.53")
    assert f.state == "unknown"


# ------------------------------------------------------------------ the transport stays on the LAN
@pytest.mark.parametrize("host", ["127.0.0.1", "10.20.0.53", "192.168.1.91", "100.112.232.94", "::1"])
def test_lan_hosts_allowed(host):
    assert cr.check_lan(host) == host


@pytest.mark.parametrize("host", ["8.8.8.8", "github.com", "", None, "1.1.1.1", "203.0.113.9",
                                  "192.0.2.1", "240.0.0.1"])
def test_public_or_named_hosts_refused(host):
    with pytest.raises(cr.NotLan):
        cr.check_lan(host)


def test_probe_refuses_a_target_that_resolves_off_the_lan():
    called = []
    f = cr.probe(TARGETS[0], run=lambda *a, **k: called.append(a), resolve=lambda a: "203.0.113.9")
    assert f.state == "unknown" and not called


# ------------------------------------------------------------------ the commands it would run
def test_docker_command_has_no_network_and_limits():
    cmd = cr.remote_command(TARGETS[0], ["python", "-m", "pytest", "-q", "tests/x.py"], "j1", 600)
    assert "--network none" in cmd and "--rm" in cmd and "--cpus 8" in cmd
    assert "python:3.12-slim" in cmd and "timeout 600" in cmd


def test_plain_command_runs_as_nobody_in_a_scratch_dir_and_cleans_up():
    cmd = cr.remote_command(TARGETS[1], ["python", "-m", "pytest", "-q"], "j2", 600)
    assert "runuser -u nobody" in cmd and "mktemp -d /var/tmp/jobroute." in cmd
    assert "python3 -m pytest" in cmd and "nice -n 19" in cmd
    assert '[ -n "$d" ] && rm -rf "$d"' in cmd


def test_job_id_and_argv_are_quoted():
    cmd = cr.remote_command(TARGETS[0], ["python", "-c", "print('a b'); import os"], "j;rm", 60)
    assert "jobroute-jrm " in cmd and "j;rm" not in cmd
    # the argv reaches the remote shell as one quoted word per argument
    import shlex
    outer = shlex.split(cmd)
    inner = outer[-1]
    assert "'print('\"'\"'a b'\"'\"'); import os'" in inner


def test_bundle_carries_the_tree_and_vendored_pytest(tmp_path):
    raw = io.BytesIO()
    with tarfile.open(fileobj=raw, mode="w") as t:
        data = b"x = 1\n"
        info = tarfile.TarInfo("pkg/mod.py")
        info.size = len(data)
        t.addfile(info, io.BytesIO(data))
    out = cr.make_bundle(raw.getvalue(), vendor=("pluggy",))
    names = tarfile.open(fileobj=io.BytesIO(out)).getnames()
    assert "pkg/mod.py" in names
    assert any(n.startswith("_vendor/pluggy/") for n in names)
    assert not any("__pycache__" in n for n in names)


# ------------------------------------------------------------------ Law 9: no cloud path
def test_no_cloud_or_vendor_path_in_the_source():
    src = open(os.path.join(_NODE, "cluster_route.py"), encoding="utf-8").read()
    for word in ("anthropic", "openai", "api.", "https://", "requests", "railway"):
        assert word not in src.lower(), word


def test_only_ssh_git_and_heavy_lock_start_processes():
    tree = ast.parse(open(os.path.join(_NODE, "cluster_route.py"), encoding="utf-8").read())
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call)
             and isinstance(n.func, ast.Attribute) and isinstance(n.func.value, ast.Name)
             and n.func.value.id == "subprocess"]
    assert {c.func.attr for c in calls} <= {"run"}


def test_dry_run_prints_and_starts_nothing(capsys, tmp_path):
    facts = tmp_path / "facts.json"
    facts.write_text(json.dumps({"vm102": {"state": "ok", "why": "test", "threads": 20,
                                           "load1": 1.0, "workers": 0, "mem_avail_gb": 9}}))
    targets = tmp_path / "t.json"
    targets.write_text(json.dumps({"schema": "cluster-targets-1", "targets": [VM]}))
    started = []
    rc = cr.main(["where", "--kind", "lint", "--targets", str(targets), "--facts", str(facts),
                  "--heavy-lock-state", "free", "--", "python", "-m", "ruff", "check", "."],
                 run=lambda *a, **k: started.append(a))
    out = capsys.readouterr().out
    assert rc == 0 and not started
    assert "WOULD run on vm102" in out and "--network none" in out





# ------------------------------------------------------------------ the R620 standby guard (owner, CONDUCTOR 060)
GUARD = {"kind": "standby-refresh", "via": "overlord", "status_file": "/var/log/pg-standby.status",
         "max_age_s": 86400}
R620G = cr.Target.from_dict(dict(R620, cpu_cap=6, idle_io=True, guard=GUARD))


def guarded(load=1.0, guard="ok", why="copy 3 h old"):
    return cr.Facts("ok", "probed", 24, load, 0, 50.0, guard, why)


def test_guarded_host_healthy_is_allowed():
    d = cr.decide({"kind": "test"}, [R620G], {"r620": guarded()}, "free")
    assert (d.action, d.target) == ("run", "r620")


def test_guarded_host_load_above_half_is_skipped():
    d = cr.decide({"kind": "test"}, [R620G], {"r620": guarded(load=12.5)}, "free")
    assert d.action == "wait" and d.considered[0][1] == "busy"


def test_guarded_host_lagging_is_skipped():
    d = cr.decide({"kind": "test"}, [R620G], {"r620": guarded(guard="lag", why="30 h old")}, "free")
    assert d.action == "wait" and d.considered[0][1] == "busy" and "30 h" in d.considered[0][2]


@pytest.mark.parametrize("g", ["unknown", None, "garbage"])
def test_guarded_host_unreadable_guard_is_skipped(g):
    d = cr.decide({"kind": "test"}, [R620G], {"r620": guarded(guard=g)}, "free")
    assert d.action == "wait" and d.considered[0][1] in ("unknown", "busy")
    assert d.target is None


def test_guarded_host_is_skipped_and_the_next_target_used():
    d = cr.decide({"kind": "test"}, [R620G, TARGETS[2]],
                  {"r620": guarded(guard="lag"), "r710": ok(16, 0.2)}, "free")
    assert d.target == "r710"


def test_guarded_host_command_is_low_priority_and_capped():
    cmd = cr.remote_command(R620G, ["python", "-m", "pytest", "-q"], "j3", 600)
    assert "nice -n 19 ionice -c3 taskset -c 0-5 timeout 600 python3 -m pytest" in cmd


@pytest.mark.parametrize("bad", [dict(R620, guard=GUARD),                      # no cpu cap
                                 dict(R620, guard=GUARD, cpu_cap=6, max_load_frac=0.8),
                                 dict(R620, guard=dict(GUARD, max_age_s=0), cpu_cap=6),
                                 dict(R620, guard={"kind": "other"}, cpu_cap=6)])
def test_guarded_host_config_must_keep_the_owner_limits(bad):
    with pytest.raises(ValueError):
        cr.Target.from_dict(bad)


NOW = 1795488436   # 2026-11-24T02:47:16Z


@pytest.mark.parametrize("text,want", [
    (f"now={NOW}\nlast_ok=20261123T113001Z\nrefreshing=0\n", "ok"),
    (f"now={NOW}\nlast_ok=20261122T113001Z\nrefreshing=0\n", "lag"),       # 39 h old
    (f"now={NOW}\nlast_ok=20261123T113001Z\nrefreshing=1\n", "lag"),       # refresh running
    (f"now={NOW}\nlast_ok=\nrefreshing=0\n", "unknown"),                     # no OK line
    (f"now={NOW}\nlast_ok=garbage\nrefreshing=0\n", "unknown"),
    (f"now={NOW}\nlast_ok=20261123T113001Z\nrefreshing=\n", "unknown"),     # pgrep unread
    ("now=\nlast_ok=20261123T113001Z\nrefreshing=0\n", "unknown"),
    (f"now={NOW}\nlast_ok=20261130T113001Z\nrefreshing=0\n", "unknown"),    # in the future
    ("", "unknown"),
])
def test_standby_guard_parse(text, want):
    assert cr.parse_standby_guard(text, 86400)[0] == want


class _R:
    def __init__(self, rc, out):
        self.returncode, self.stdout, self.stderr = rc, out, ""


def _fake_ssh(guard_rc=0, guard_out=f"now={NOW}\nlast_ok=20261123T113001Z\nrefreshing=0\n",
              load="0.3"):
    calls = []
    def run(argv, **kw):
        calls.append(argv)
        if argv[-2] == "overlord":
            return _R(guard_rc, guard_out)
        return _R(0, f"nproc=24\nload={load} 0.3 0.3 1/1 1\nworkers=0\nmemavail_kb=50000000\n")
    return run, calls


def test_probe_reads_the_guard_for_a_guarded_host():
    run, calls = _fake_ssh()
    f = cr.probe(R620G, run=run, resolve=lambda a: "10.20.0.52")
    assert f.state == "ok" and f.guard == "ok"
    assert [c[-2] for c in calls] == [R620G.ssh, "overlord"]
    assert cr.decide({"kind": "test"}, [R620G], {"r620": f}, "free").target == "r620"


def test_probe_guard_ssh_failure_skips_the_host():
    run, _ = _fake_ssh(guard_rc=255, guard_out="")
    f = cr.probe(R620G, run=run, resolve=lambda a: "10.20.0.52")
    assert f.guard == "unknown"
    assert cr.decide({"kind": "test"}, [R620G], {"r620": f}, "free").action == "wait"


def test_probe_guard_lag_skips_the_host():
    run, _ = _fake_ssh(guard_out=f"now={NOW}\nlast_ok=20261121T221704Z\nrefreshing=0\n")
    f = cr.probe(R620G, run=run, resolve=lambda a: "10.20.0.52")
    assert f.guard == "lag"
    assert cr.decide({"kind": "test"}, [R620G], {"r620": f}, "free").action == "wait"


def test_guard_script_is_read_only():
    s = cr.standby_guard_script(GUARD)
    assert "flock" not in s and "psql" not in s and ">" not in s.replace("2>/dev/null", "")
    assert "[p]g-standby-refresh" in s


def test_default_targets_enable_all_three_and_guard_the_r620():
    targets = cr.load_targets(os.path.join(_NODE, "cluster_targets.json"))
    by = {t.id: t for t in targets}
    assert [t.id for t in targets] == ["vm102", "r620", "r710"]
    assert all(t.enabled for t in targets)
    r620 = by["r620"]
    assert r620.guard and r620.guard["kind"] == "standby-refresh"
    assert 0 < r620.cpu_cap <= 24 // 2 and r620.max_load_frac <= 0.5 and r620.idle_io