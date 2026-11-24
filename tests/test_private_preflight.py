"""NODE redline-1: the private-repo preflight is read-only and says unknown when it cannot see."""
import datetime as dt
import importlib.util
import os

import pytest

_NODE = os.path.join(os.path.dirname(__file__), os.pardir, "node")


def _load(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(_NODE, name + ".py"))
    m = importlib.util.module_from_spec(spec)
    import sys
    sys.modules[name] = m
    sys.path.insert(0, _NODE)
    try:
        spec.loader.exec_module(m)
    finally:
        sys.path.remove(_NODE)
    return m


pf = _load("private_preflight")
db = _load("delete_high_branches")

NOW = dt.datetime(2026, 11, 24, 12, 0, tzinfo=dt.timezone.utc)
H1, H2 = list(pf.HIGH_BRANCHES)
T1, T2 = (pf.HIGH_BRANCHES[H1]["tip"], pf.HIGH_BRANCHES[H2]["tip"])


def fake_api(private=False, tips=None, runners=("r1",), clients_files=(), fail=()):
    tips = {H1: T1, H2: T2, "main": "a" * 40} if tips is None else tips
    calls = []

    def api(path):
        calls.append(path)
        for f in fail:
            if f in path:
                raise pf.GhError("boom")
        if path.startswith("repos/O/core/branches/"):
            n = path.split("/branches/")[1]
            if n not in tips:
                raise pf.GhError("404")
            return {"commit": {"sha": tips[n]}}
        if path.startswith("repos/O/core/branches?"):
            return [{"name": n, "commit": {"sha": s}} for n, s in tips.items()]
        if path == "repos/O/core":
            return {"private": private, "visibility": "private" if private else "public"}
        if path == "repos/O/clients":
            return {"default_branch": "main"}
        if path.startswith("repos/O/core/git/trees/"):
            return {"tree": [{"type": "blob", "path": "lava-cap-audit/a.pdf"},
                             {"type": "blob", "path": "lava-cap-site/b.md"}, {"type": "blob", "path": "README.md"}]}
        if path.startswith("repos/O/clients/git/trees/"):
            return {"tree": [{"type": "blob", "path": p} for p in clients_files]}
        if path.endswith("/actions/runners"):
            return {"runners": [{"name": n, "status": "online"} for n in runners]}
        if "/actions/runs" in path:
            return {"total_count": 12}
        raise AssertionError("unexpected path " + path)

    api.calls = calls
    return api


def wf_dir(tmp_path, text):
    d = tmp_path / "wf"
    d.mkdir()
    (d / "test.yml").write_text(text, encoding="utf8")
    return str(d)


HOSTED = "name: t\njobs:\n  pytest:\n    runs-on: ubuntu-latest\n"


def test_only_get_paths_are_requested(tmp_path):
    api = fake_api()
    pf.build("O/core", "O/clients", wf_dir(tmp_path, HOSTED), api, NOW)
    assert api.calls and all(p.startswith("repos/") for p in api.calls)


def test_public_repo_with_runner_and_hosted_job_is_flagged(tmp_path):
    rep = pf.build("O/core", "O/clients", wf_dir(tmp_path, HOSTED), fake_api(), NOW)
    text = " ".join(rep["breaks_on_private"])
    assert "1 job(s) run on a GitHub-hosted runner" in text and "steps=0" in text
    assert "still PUBLIC" in text
    assert rep["branches"]["high"][H1]["present"] and rep["branches"]["high"][H2]["tip_matches_report"]
    assert "OWNER-STEP" in rep["owner_step"]


def test_gh_failure_is_unknown_never_clean(tmp_path):
    rep = pf.build("O/core", "O/clients", wf_dir(tmp_path, HOSTED), fake_api(fail=("/branches", "/actions/runners")), NOW)
    assert rep["branches"]["state"] == "unknown"
    assert rep["runners"]["state"] == "unknown"
    assert rep["clients_copy"]["state"] == "unknown"
    assert "UNKNOWN" in pf.render(rep)


def test_missing_workflow_dir_is_unknown(tmp_path):
    rep = pf.build("O/core", "O/clients", str(tmp_path / "nope"), fake_api(), NOW)
    assert rep["workflows"]["state"] == "unknown"
    assert any(x.startswith("UNKNOWN") for x in rep["breaks_on_private"])


def test_empty_branch_list_is_unknown(tmp_path):
    rep = pf.build("O/core", "O/clients", wf_dir(tmp_path, HOSTED), fake_api(tips={}), NOW)
    assert rep["branches"]["state"] == "unknown"


def test_moved_tip_is_reported(tmp_path):
    rep = pf.build("O/core", "O/clients", wf_dir(tmp_path, HOSTED), fake_api(tips={H1: "b" * 40, H2: T2}), NOW)
    assert rep["branches"]["high"][H1]["tip_matches_report"] is False


def test_clients_copy_lists_missing_files(tmp_path):
    d = wf_dir(tmp_path, HOSTED)
    rep = pf.build("O/core", "O/clients", d, fake_api(clients_files=["x/other.txt"]), NOW)
    c = rep["clients_copy"]
    assert c["state"] == "ok" and c["files_on_branch"] == 2
    assert c["missing_in_clients"] == ["lava-cap-audit/a.pdf", "lava-cap-site/b.md"]
    ok = pf.build("O/core", "O/clients", d, fake_api(clients_files=["lava-cap/a.pdf", "lava-cap-site/b.md"]), NOW)
    assert ok["clients_copy"]["found_in_clients"] == 2  # matched by path tail, any folder


def test_parser_control_and_selfhosted(tmp_path):
    w = pf.workflow_section(wf_dir(tmp_path, "jobs:\n  a:\n    runs-on: [self-hosted, novah]\n"))
    assert w["self_hosted_jobs"] == 1 and w["hosted_jobs"] == 0


# ---- delete script ----

def run_delete(argv, **kw):
    deleted = []
    rc = db.main(["--repo", "O/core"] + argv, api=fake_api(**kw), delete=deleted.append)
    return rc, deleted


def test_dry_run_deletes_nothing():
    rc, deleted = run_delete([], private=True)
    assert rc == 2 and deleted == []


def test_refuses_while_public():
    rc, deleted = run_delete(["--confirm-delete"], private=False)
    assert rc == 1 and deleted == []


def test_deletes_only_the_two_named_branches_when_private_and_confirmed():
    rc, deleted = run_delete(["--confirm-delete"], private=True, tips={H1: T1, H2: T2, "main": "a" * 40})
    assert rc == 0
    assert deleted == [f"repos/O/core/git/refs/heads/{H1}", f"repos/O/core/git/refs/heads/{H2}"]


def test_moved_tip_blocks_all_deletion():
    rc, deleted = run_delete(["--confirm-delete"], private=True, tips={H1: "c" * 40, H2: T2, "main": "a" * 40})
    assert rc == 1 and deleted == []


def test_unreadable_visibility_blocks_deletion():
    rc, deleted = run_delete(["--confirm-delete"], private=True, fail=("repos/O/core",))
    assert rc == 1 and deleted == []
