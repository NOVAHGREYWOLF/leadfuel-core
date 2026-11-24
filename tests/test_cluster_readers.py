"""NODE cluster files part 7: per-machine readers feed the part 5 index. No machine is contacted here:
the remote scripts run on this machine through the same stdin path ssh would use, and every network,
lock and guard call is a fake. The rules under test: unknown is never empty, a cut walk is partial,
private files are never hashed, passes wait for the window, the slot and the guards, and `plan`
touches nothing."""
import contextlib
import datetime as dt
import importlib.util
import json
import os
import shutil
import subprocess
import sys

import pytest

_HERE = os.path.dirname(__file__)
_NODE = os.path.join(_HERE, os.pardir, "node")
spec = importlib.util.spec_from_file_location("cluster_readers", os.path.join(_NODE, "cluster_readers.py"))
cr = importlib.util.module_from_spec(spec)
sys.modules["cluster_readers"] = cr
spec.loader.exec_module(cr)
fi = cr.fi()

try:
    from zoneinfo import ZoneInfo
    PT = ZoneInfo("America/Los_Angeles")
except Exception:  # pragma: no cover
    PT = dt.timezone(dt.timedelta(hours=-8))

DAY = dt.datetime(2026, 11, 24, 14, 0, tzinfo=PT)
NIGHT = dt.datetime(2026, 11, 24, 23, 30, tzinfo=PT)
PWSH = shutil.which("powershell") or shutil.which("pwsh")


def _w(p, data, mtime=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(data if isinstance(data, bytes) else data.encode("utf-8"))
    if mtime:
        os.utime(p, (mtime, mtime))


@pytest.fixture
def tree(tmp_path):
    r = tmp_path / "srv"
    _w(str(r / "a" / "plan.md"), "zebra plan\n")
    _w(str(r / "b" / "plan copy.md"), "zebra plan\n")
    _w(str(r / "big" / "x.bin"), b"\x00" * 300_000)
    _w(str(r / "big" / "y.bin"), b"\x00" * 300_000)
    _w(str(r / "big" / "z.bin"), b"\x00" * 299_999 + b"\x01")
    _w(str(r / "Taxes 2025" / "return.txt"), "zebra plan\n")      # same size as plan.md: still never hashed
    _w(str(r / "proj" / ".env"), "API_KEY=zebra")
    _w(str(r / "node_modules" / "z.js"), "zebra")
    _w(str(r / "repo" / ".git" / "HEAD"), "ref: x")
    _w(str(r / "repo" / "src" / "m.py"), "print(1)")
    _w(str(r / "caf\u00e9" / "na\u00efve.txt"), "accents")
    return r


@pytest.fixture
def con(tmp_path):
    return fi.connect(str(tmp_path / "idx" / "index.sqlite"))


def _root(p):
    return fi.norm(str(p))


def _linux(mid="r710-1", in_use=False, roots=None, guards=None, route=None):
    return {"id": mid, "os": "linux", "route": route or {"kind": "ssh", "host": "root@10.20.0.51"},
            "scan": {"in_use": in_use},
            "sources": {"roots": roots or [], "one_fs": True, "excludes": [], "guards": guards or []}}


def _walk(con, mid, root, transport=None, **job):
    tr = transport or cr.LocalPythonTransport()
    m = _linux(mid, roots=[{"path": str(root)}])
    j = cr.walk_job(m, {"path": str(root), **job}, None)
    return cr.ingest_walk(con, mid, str(root), cr.peek(tr.stream("walk", j, 120)), log=lambda *a: None)


def _rows(con, mid):
    return {r["path"].rsplit("/srv/", 1)[-1]: dict(r) for r in con.execute("SELECT * FROM files WHERE machine=?", (mid,))}


# --------------------------------------------------------------------------- config

def test_every_inventory_machine_has_a_reader_entry_and_ids_match_the_index():
    ms = cr.load_machines()
    with open(cr.TARGETS, encoding="utf-8") as fh:
        ids = [m["id"] for m in json.load(fh)["machines"]]
    assert [m["id"] for m in ms] == ids
    assert set(fi.KNOWN_MACHINES) == set(ids)
    gw = next(m for m in ms if m["id"] == "greywolf")
    assert any(e.endswith("cluster_files") for e in gw["sources"]["excludes"])   # never index the index
    assert "C:/Windows" in gw["sources"]["excludes"]


def test_a_machine_missing_from_sources_is_an_error(tmp_path):
    with open(cr.SOURCES, encoding="utf-8") as fh:
        s = json.load(fh)
    del s["machines"]["msi"]
    p = tmp_path / "s.json"
    p.write_text(json.dumps(s), encoding="utf-8")
    with pytest.raises(ValueError, match="msi"):
        cr.load_machines(cr.TARGETS, str(p))


def test_config_files_hold_no_secret_material():
    for path in (cr.SOURCES, cr.TARGETS):
        text = open(path, encoding="utf-8").read()
        assert "BEGIN" not in text and "PRIVATE KEY" not in text and "password\":" not in text.lower()


# --------------------------------------------------------------------------- plan is a dry run

def test_plan_touches_nothing_and_respects_the_window(monkeypatch, tmp_path):
    def boom(*a, **k):
        raise AssertionError("plan must not start a process")
    monkeypatch.setattr(subprocess, "run", boom)
    monkeypatch.setattr(subprocess, "Popen", boom)
    monkeypatch.setenv("CLUSTER_FILES_DB", str(tmp_path / "never" / "index.sqlite"))
    ms = cr.load_machines()
    day = {i["machine"]: i for i in cr.plan(ms, DAY)}
    assert {k for k, v in day.items() if v["verdict"] == "deferred"} == {"greywolf", "surface", "msi"}
    assert {k for k, v in day.items() if v["verdict"] == "unknown"} == {"r710-2", "r610"}
    assert {k for k, v in day.items() if v["verdict"] == "go"} == {"overlord", "r710-1", "r620"}
    night = {i["machine"]: i for i in cr.plan(ms, NIGHT)}
    assert night["surface"]["verdict"] == "go" and night["surface"]["budget_s"] <= 8.5 * 3600
    assert any("nice -n 19 ionice -c3 python3 -" in s for s in night["overlord"]["steps"])
    assert any("standby guard" in s for s in night["r620"]["steps"])
    assert any("overlord-dumps" in s for s in night["r710-1"]["steps"])
    assert not os.path.exists(tmp_path / "never")
    text = cr.render_plan(cr.plan(ms, NIGHT), NIGHT)
    assert "DRY RUN" in text and "r710-2: UNKNOWN" in text


def test_plan_cli_runs_offline(capsys, monkeypatch):
    monkeypatch.setattr(subprocess, "Popen", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no process")))
    assert cr.main(["plan", "--at", "2026-11-24T23:30", "--json"]) == 0
    items = json.loads(capsys.readouterr().out)
    assert len(items) == 8


def test_window_closes_at_eight_and_unreadable_time_refuses():
    m = _linux("surface", in_use=True, roots=[{"path": "C:/"}])
    ok, why, until = cr.window(m, dt.datetime(2026, 11, 25, 7, 30, tzinfo=PT))
    assert ok and until == 30 * 60
    ok, why, _ = cr.window(m, None)
    assert not ok and "Pacific time could not be read" in why
    assert cr.window(_linux(), None)[0]          # a server does not need the clock


# --------------------------------------------------------------------------- transport shape

def test_remote_argv_throttles_and_never_carries_the_script_on_the_command_line():
    lin = cr.remote_argv(_linux())
    assert lin[0] == "ssh" and "BatchMode=yes" in lin and lin[-1] == "nice -n 19 ionice -c3 python3 -"
    via = cr.remote_argv(_linux("r620", route={"kind": "ssh-via", "via": "overlord", "host": "root@10.20.0.52",
                                              "via_key": "/root/.ssh/id_ed25519_auto"}))
    assert via[-2] == "overlord" and "-i /root/.ssh/id_ed25519_auto root@10.20.0.52" in via[-1]
    assert "nice -n 19 ionice -c3 python3 -" in via[-1]
    win = cr.remote_argv({"id": "surface", "os": "windows", "route": {"kind": "ssh", "host": "u@100.64.0.9"}})
    assert "-EncodedCommand" in win[-1]
    import base64
    boot = base64.b64decode(win[-1].split()[-1]).decode("utf-16-le")
    assert "PriorityClass = 'Idle'" in boot and "FromBase64String" in boot
    with pytest.raises(cr.Unreadable, match="lockdown"):
        cr.remote_argv(_linux(route={"kind": "none", "reason": "VLAN 30 lab lockdown"}))


def test_public_address_is_refused_before_anything_is_sent():
    calls = []
    t = cr.SshTransport(_linux(route={"kind": "ssh", "host": "root@8.8.8.8"}),
                        popen=lambda *a, **k: calls.append(a), run=lambda *a, **k: calls.append(a))
    with pytest.raises(cr.Unreadable, match="refused"):
        cr.peek(t.stream("walk", {"root": "/"}, 5))
    assert calls == []


def test_failed_or_silent_process_is_unreadable_never_an_empty_listing():
    die = [sys.executable, "-c", "import sys; sys.stderr.write('ssh: connect to host x port 22: Connection timed out\\n'); sys.exit(255)"]
    with pytest.raises(cr.Unreadable, match="rc=255: ssh: connect"):
        cr.peek(cr._stream_process(die, b"", 30))
    hang = [sys.executable, "-c", "import time; time.sleep(30)"]
    with pytest.raises(cr.Unreadable, match="unknown, not down"):
        cr.peek(cr._stream_process(hang, b"", 1))


def test_scripts_hold_no_write_verbs():
    bad_py = ("os.remove", "os.unlink", "os.rename", "shutil", "rmtree", "'w'", '"w"', "'wb'", "'a'", "makedirs")
    for s in (cr.PY_WALK, cr.PY_HASH):
        assert not [b for b in bad_py if b in s]
    bad_ps = ("Remove-Item", "Set-Content", "Out-File", "Move-Item", "Rename-Item", "New-Item", "Add-Content",
              "Copy-Item", "Delete(", "WriteAllBytes", "WriteAllText", "'Write'", "OpenWrite", "Create(")
    for s in (cr.PS_COMMON, cr.PS_WALK, cr.PS_HASH):
        hits = [b for b in bad_ps if b in s]
        assert hits in ([], ["Create("]) and ("Create(" not in hits or "SHA256]::Create()" in s)


# --------------------------------------------------------------------------- walk and ingest

def test_walk_feeds_the_index_incrementally_without_content(con, tree):
    first = _walk(con, "r710-1", tree)
    assert first["state"] == "complete" and first["new"] >= 9
    rows = _rows(con, "r710-1")
    assert "node_modules/z.js" not in rows                         # skip names apply on the machine
    assert rows["a/plan.md"]["extract_state"] == "remote"           # no content crossed
    assert rows["Taxes 2025/return.txt"]["hash_state"] == "private"
    assert rows["proj/.env"]["hash_state"] == "private"
    assert rows["repo/src/m.py"]["in_git"] == 1
    assert "caf\u00e9/na\u00efve.txt" in rows
    second = _walk(con, "r710-1", tree)
    assert second["new"] == 0 and second["changed"] == 0 and second["removed"] == 0
    os.remove(str(tree / "b" / "plan copy.md"))
    _w(str(tree / "a" / "plan.md"), "zebra plan, longer now\n")
    third = _walk(con, "r710-1", tree)
    assert third["removed"] == 1 and third["changed"] == 1
    res = fi.search(con, "zebra", field="content", machine="r710-1")
    assert any("remote" in n for n in res["notes"])                  # content there is unknown, said so


def test_missing_or_unmounted_root_is_unknown_and_keeps_rows(con, tree, tmp_path):
    _walk(con, "r620", tree)
    n = con.execute("SELECT COUNT(*) FROM files WHERE machine='r620'").fetchone()[0]
    sc = _walk(con, "r620", tree, require_mount=True)              # a temp dir is not a mount point
    assert sc["state"] == "unreachable" and "not mounted" in sc["note"]
    assert con.execute("SELECT COUNT(*) FROM files WHERE machine='r620'").fetchone()[0] == n
    cov = fi.coverage(con)["r620"]
    assert cov["state"] == "unknown" and "unreachable" in cov["detail"] and "kept" in cov["detail"]
    sc = _walk(con, "overlord", tmp_path / "nope")
    assert sc["state"] == "unreachable" and fi.coverage(con)["overlord"]["state"] == "unknown"


def test_cut_stream_is_partial_and_removes_nothing(con, tree):
    _walk(con, "r710-1", tree)
    n = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    lines = list(cr.LocalPythonTransport().stream("walk", cr.walk_job(_linux(), {"path": str(tree)}, None), 60))
    assert json.loads(lines[-1])["end"] == "complete"
    sc = cr.ingest_walk(con, "r710-1", str(tree), lines[:2], log=lambda *a: None)
    assert sc["state"] == "partial" and sc["removed"] == 0 and "end line" in sc["note"]
    assert con.execute("SELECT COUNT(*) FROM files").fetchone()[0] == n
    assert fi.coverage(con)["r710-1"]["state"] == "partial"


def test_lines_outside_the_root_or_malformed_are_ignored_and_make_it_partial(con, tree):
    root = _root(tree)
    lines = [json.dumps({"d": "/etc", "f": [["passwd", 1, 1, ""]]}),
             json.dumps({"d": root, "f": [["../escape", 1, 1, ""], ["ok.txt", 5, 10, ""]]}),
             "not json", json.dumps({"end": "complete"})]
    sc = cr.ingest_walk(con, "r620", str(tree), lines, log=lambda *a: None)
    assert sc["state"] == "partial" and "malformed" in sc["note"]
    assert [r["name"] for r in con.execute("SELECT name FROM files")] == ["ok.txt"]


def test_unentered_subtree_keeps_its_rows(con, tree):
    _walk(con, "r710-1", tree)
    lines = [json.dumps({"d": _root(tree), "f": []}),
             json.dumps({"u": _root(tree) + "/big", "e": "PermissionError"})]
    for sub in ("a", "b", "Taxes 2025", "proj", "repo", "repo/src", "caf\u00e9"):
        files = [[e.name, e.stat().st_size, e.stat().st_mtime_ns, ""] for e in os.scandir(tree / sub) if e.is_file()]
        lines.append(json.dumps({"d": _root(tree) + "/" + sub, "f": files}))
    lines.append(json.dumps({"end": "complete"}))
    sc = cr.ingest_walk(con, "r710-1", str(tree), lines, log=lambda *a: None)
    assert sc["state"] == "complete"
    assert "big/x.bin" in _rows(con, "r710-1")                       # not dropped: unknown, not gone


def test_guard_skipped_subtree_is_kept(con, tree):
    _walk(con, "r710-1", tree)
    j = cr.walk_job(_linux(), {"path": str(tree)}, None, extra_skip=[str(tree / "big")])
    sc = cr.ingest_walk(con, "r710-1", str(tree), cr.LocalPythonTransport().stream("walk", j, 60),
                        log=lambda *a: None, guard_skipped=[str(tree / "big")])
    assert sc["state"] == "complete" and "big/y.bin" in _rows(con, "r710-1")


# --------------------------------------------------------------------------- hashing on the machine

class Recording:
    def __init__(self, inner):
        self.inner, self.jobs = inner, []

    def stream(self, kind, job, timeout_s):
        self.jobs.append((kind, job))
        return self.inner.stream(kind, job, timeout_s)


def test_hash_on_machine_matches_the_local_hash_and_finds_cross_machine_duplicates(con, tree, tmp_path):
    other = tmp_path / "other"
    _w(str(other / "copy.bin"), b"\x00" * 300_000)
    _walk(con, "r710-1", tree)
    _walk(con, "r620", other)
    rec = Recording(cr.LocalPythonTransport())
    for mid in ("r710-1", "r620"):
        st = cr.hash_on_machine(con, mid, rec, mbps=0, deadline=None, log=lambda *a: None)
        assert st["stopped"] is None
    asked = [it["p"] for _k, j in rec.jobs for it in j["items"]]
    assert asked and not any("Taxes" in p or ".env" in p for p in asked)   # private never asked
    x = con.execute("SELECT quick, size, path FROM files WHERE path LIKE '%big/x.bin'").fetchone()
    assert x["quick"] == fi.quick_hash(str(tree / "big" / "x.bin"), x["size"], fi.Throttle(0))
    rep = fi.dedupe_groups(con)
    big = next(g for g in rep["groups"] if g["size"] == 300_000)
    assert big["copies"] == 3
    assert {o["machine"] for o in big["others"]} | {big["canonical"]["machine"]} == {"r710-1", "r620"}
    z = con.execute("SELECT hash_state FROM files WHERE path LIKE '%big/z.bin'").fetchone()
    assert z["hash_state"] == "quick"                                  # quick differs: no full read


def test_a_changed_file_stays_pending_and_foreign_answers_are_ignored(con, tree):
    _walk(con, "r710-1", tree)
    rows = fi.quick_candidates(con, "r710-1")
    by_path = {r["path"]: r["id"] for r in rows}
    p0 = rows[0]["path"]
    st = cr._apply_hashes(con, "quick", by_path, [json.dumps({"p": p0, "e": "changed"}),
                                                  json.dumps({"p": "/etc/shadow", "h": "0" * 64}),
                                                  json.dumps({"end": "complete"})])
    assert st == {"ok": 0, "errors": 0, "changed": 1, "ignored": 1, "end": "complete"}
    assert con.execute("SELECT hash_state FROM files WHERE path=?", (p0,)).fetchone()[0] == "pending"


def test_local_hash_never_opens_another_machines_rows(con, tree):
    _walk(con, "r710-1", tree)                  # remote rows whose paths also exist here, by design
    con.execute("UPDATE files SET path='/srv/not-here/' || name")
    con.commit()
    fi.hash_candidates(con, mbps=0, machine="greywolf", log=lambda *a: None)
    states = {r[0] for r in con.execute("SELECT DISTINCT hash_state FROM files")}
    assert "error" not in states and "quick" not in states


@pytest.mark.skipif(not PWSH, reason="PowerShell not on this machine")
def test_powershell_reader_agrees_with_the_python_reader(con, tree):
    ps = cr.LocalPowerShellTransport(PWSH)
    sc = _walk(con, "surface", tree, transport=ps)
    assert sc["state"] == "complete"
    py = cr.ingest_walk(fi.connect(":memory:"), "x", str(tree),
                        cr.LocalPythonTransport().stream("walk", cr.walk_job(_linux(), {"path": str(tree)}, None), 60),
                        log=lambda *a: None)
    assert sc["files"] == py["files"]
    rows = _rows(con, "surface")
    assert "caf\u00e9/na\u00efve.txt" in rows and rows["repo/src/m.py"]["in_git"] == 1
    assert rows["a/plan.md"]["mtime_ns"] == os.stat(tree / "a" / "plan.md").st_mtime_ns
    st = cr.hash_on_machine(con, "surface", ps, mbps=0, deadline=None, log=lambda *a: None)
    assert st["errors"] == 0 and st["quick"] > 0
    for name in ("big/x.bin", "a/plan.md"):
        r = con.execute("SELECT quick, hash, size FROM files WHERE machine='surface' AND path LIKE ?",
                        ("%" + name,)).fetchone()
        assert r["quick"] == fi.quick_hash(str(tree / name), r["size"], fi.Throttle(0))
        if r["hash"]:
            assert r["hash"] == fi.full_hash(str(tree / name), fi.Throttle(0))


# --------------------------------------------------------------------------- passes

class FakeSlot:
    def __init__(self, refuse=None):
        self.refuse, self.log = refuse, []

    @contextlib.contextmanager
    def __call__(self, job):
        if self.refuse:
            raise cr.slot_mod().SlotRefused(self.refuse, "fake")
        self.log.append(("take", job))
        try:
            yield "tok"
        finally:
            self.log.append(("release", job))


class Down:
    def stream(self, kind, job, timeout_s):
        def gen():
            raise cr.Unreadable("ssh/exec rc=255: ssh: connect to host 192.168.1.91 port 22: Connection timed out")
            yield  # pragma: no cover
        return gen()


def test_unreachable_machine_reads_unknown_with_reason_and_keeps_rows(con, tree):
    _walk(con, "msi", tree)
    n = con.execute("SELECT COUNT(*) FROM files WHERE machine='msi'").fetchone()[0]
    m = {**_linux("msi", roots=[{"path": str(tree)}])}
    res = cr.run_pass(con, m, [m], NIGHT, transport=Down(), slot=FakeSlot(), log=lambda *a: None)
    assert res["verdict"] == "unknown"
    cov = fi.coverage(con)["msi"]
    assert cov["state"] == "unknown" and "timed out" in cov["detail"]
    assert con.execute("SELECT COUNT(*) FROM files WHERE machine='msi'").fetchone()[0] == n
    assert fi.search(con, "zebra", machine="msi")["notes"]


def test_no_route_machine_is_recorded_unknown_without_sending(con):
    m = {**_linux("r610", route={"kind": "none", "reason": "VLAN 30 lab lockdown"})}
    res = cr.run_pass(con, m, [m], NIGHT, transport=Down(), slot=FakeSlot(refuse="held"), log=lambda *a: None)
    assert res["verdict"] == "unknown" and fi.coverage(con)["r610"]["detail"].startswith("unreachable: VLAN 30")


def test_slot_held_or_window_closed_defers_and_writes_nothing(con, tree):
    m = _linux("r710-1", roots=[{"path": str(tree)}])
    res = cr.run_pass(con, m, [m], NIGHT, transport=cr.LocalPythonTransport(), slot=FakeSlot(refuse="unknown"),
                      log=lambda *a: None)
    assert res["verdict"] == "deferred" and "unknown" in res["why"]
    s = _linux("surface", in_use=True, roots=[{"path": str(tree)}])
    res = cr.run_pass(con, s, [s], DAY, transport=cr.LocalPythonTransport(), slot=FakeSlot(), log=lambda *a: None)
    assert res["verdict"] == "deferred" and "22:00" in res["why"]
    assert con.execute("SELECT COUNT(*) FROM scans").fetchone()[0] == 0


def test_standby_guard_not_ok_defers_the_r620(con, tree):
    m = _linux("r620", roots=[{"path": str(tree)}], guards=[{"kind": "standby", "guard_from": "r620"}])
    for state in ("lag", "unknown"):
        res = cr.run_pass(con, m, [m], NIGHT, transport=cr.LocalPythonTransport(), slot=FakeSlot(),
                          standby=lambda g, s=state: (s, "fake"), log=lambda *a: None)
        assert res["verdict"] == "deferred" and state in res["why"]
    res = cr.run_pass(con, m, [m], NIGHT, transport=cr.LocalPythonTransport(), slot=FakeSlot(),
                      standby=lambda g: ("ok", "fresh"), log=lambda *a: None)
    assert res["verdict"] == "done"


def test_ingest_guard_unknown_leaves_the_dumps_subtree_unread(con, tree):
    over = _linux("overlord", route={"kind": "ssh", "host": "root@10.20.0.10"})
    m = _linux("r710-1", roots=[{"path": str(tree)}],
               guards=[{"kind": "ingest", "via": "overlord", "subtree": str(tree / "big")}])

    def fake_run(argv, **kw):
        return subprocess.CompletedProcess(argv, 1, "", "")       # systemctl failed: unknown
    res = cr.run_pass(con, m, [m, over], NIGHT, transport=cr.LocalPythonTransport(), slot=FakeSlot(),
                      run=fake_run, log=lambda *a: None)
    assert res["verdict"] == "done"
    assert not any(p.startswith("big/") for p in _rows(con, "r710-1"))
    assert con.execute("SELECT error FROM unreadable WHERE path LIKE '%/big'").fetchone()[0].startswith("guard")


def test_passes_run_one_machine_at_a_time_and_release_between(con, tree, tmp_path):
    other = tmp_path / "o"
    _w(str(other / "f.txt"), "x")
    ms = [_linux("r710-1", roots=[{"path": str(tree)}]), _linux("r620", roots=[{"path": str(other)}])]
    slot = FakeSlot()
    out = cr.run(con, ms, now_fn=lambda: NIGHT, transport=cr.LocalPythonTransport(), slot=slot,
                 log=lambda *a: None)
    assert [r["verdict"] for r in out] == ["done", "done"]
    assert slot.log == [("take", "cluster-read-r710-1"), ("release", "cluster-read-r710-1"),
                        ("take", "cluster-read-r620"), ("release", "cluster-read-r620")]
