"""Cluster files part 8: the gated apply step. Temp folders only, never real data.

It acts only on recorded keep_canonical decisions, is a dry run without --apply, moves (never
deletes) into a quarantine with a manifest, re-checks the canonical before and after, refuses
private, book and repo paths, restores, and purges only after 30 days."""
import hashlib
import importlib.util
import json
import os
import sys

import pytest

_HERE = os.path.dirname(__file__)
_NODE = os.path.join(_HERE, os.pardir, "node")


def _load(name):
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, os.path.join(_NODE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


fi = _load("file_index")
da = _load("dedupe_apply")

M = "testbox"
BODY = b"the same bytes in three places\n" * 100
H = hashlib.sha256(BODY).hexdigest()


def _w(p, data, mtime=None):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write(data)
    if mtime:
        os.utime(p, (mtime, mtime))


def _index(db, root):
    con = fi.connect(db)
    fi.scan(con, M, str(root), log=lambda *a: None)
    fi.hash_candidates(con, mbps=0, log=lambda *a: None)
    con.close()


def _decide(db, h, decision, canonical):
    con = fi.connect(db)
    fi.record_decisions(con, {h: {"decision": decision, "canonical": canonical}})
    con.close()


@pytest.fixture
def env(tmp_path):
    root = tmp_path / "drive"
    keep = root / "archive" / "report.bin"
    c1 = root / "copy" / "report.bin"
    c2 = root / "other" / "report (1).bin"
    _w(keep, BODY, mtime=1_500_000_000)
    _w(c1, BODY, mtime=1_600_000_000)
    _w(c2, BODY, mtime=1_700_000_000)
    db = str(tmp_path / "idx" / "index.sqlite")
    _index(db, root)
    q = str(tmp_path / "drive" / fi.QUARANTINE_DIRNAME)
    return {"root": root, "db": db, "keep": fi.norm(str(keep)), "c1": fi.norm(str(c1)),
            "c2": fi.norm(str(c2)), "q": q}


def _run(env, apply, **kw):
    return da.run_apply(env["db"], [H], M, apply, env["q"], 0, log=lambda *a: None, **kw)


def test_group_is_indexed_as_three_copies(env):
    con = fi.connect_ro(env["db"])
    assert len(da.load_group(con, H)["copies"]) == 3
    con.close()


def test_undecided_group_is_refused(env):
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.REFUSED and "not decided" in r["why"]
    assert os.path.exists(env["c1"]) and os.path.exists(env["c2"])
    assert not os.path.exists(env["q"])


@pytest.mark.parametrize("decision", ["keep_both", "decide_later"])
def test_other_decisions_are_refused(env, decision):
    _decide(env["db"], H, decision, env["keep"])
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.REFUSED and decision in r["why"]
    assert os.path.exists(env["c1"]) and os.path.exists(env["c2"])


def test_dry_run_is_the_default_and_moves_nothing(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    [r] = _run(env, apply=False)
    assert r["verdict"] == da.PLANNED
    assert sorted(m["original"] for m in r["moves"]) == sorted([env["c1"], env["c2"]])
    assert os.path.exists(env["c1"]) and os.path.exists(env["c2"])
    assert not os.path.exists(env["q"])


def test_cli_without_apply_moves_nothing(env, capsys):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    rc = da.main(["--db", env["db"], "--mbps", "0", "apply", "--group", H, "--machine", M,
                  "--quarantine", env["q"]])
    assert rc == 0
    assert "DRY RUN" in capsys.readouterr().out
    assert os.path.exists(env["c1"]) and os.path.exists(env["c2"])


def test_apply_moves_copies_into_quarantine_with_a_manifest(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.MOVED
    assert os.path.exists(env["keep"])
    assert not os.path.exists(env["c1"]) and not os.path.exists(env["c2"])
    [mpath] = da.manifests_under(env["q"])
    man = json.load(open(mpath, encoding="utf-8"))
    assert {e["original"] for e in man["entries"]} == {env["c1"], env["c2"]}
    for e in man["entries"]:
        assert e["group_hash"] == H and e["state"] == "quarantined" and e["canonical"] == env["keep"]
        assert e["moved_at"] and e["size"] == len(BODY)
        assert hashlib.sha256(open(e["quarantined"], "rb").read()).hexdigest() == H
    assert "restore --manifest" in man["restore_command"] and "--apply" in man["restore_command"]
    assert man["restore_until"] > man["created"]


def test_restore_puts_everything_back(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _run(env, apply=True)
    [mpath] = da.manifests_under(env["q"])
    dry = da.restore(mpath, apply=False)
    assert all(x["verdict"] == "restore" for x in dry) and not os.path.exists(env["c1"])
    done = da.restore(mpath, apply=True)
    assert [x["verdict"] for x in done] == ["restored", "restored"]
    for p in (env["c1"], env["c2"]):
        assert hashlib.sha256(open(p, "rb").read()).hexdigest() == H
    man = json.load(open(mpath, encoding="utf-8"))
    assert {e["state"] for e in man["entries"]} == {"restored"}


def test_restore_never_overwrites(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _run(env, apply=True)
    _w(env["c1"], b"something new")
    [mpath] = da.manifests_under(env["q"])
    res = {x["original"]: x for x in da.restore(mpath, apply=True)}
    assert res[env["c1"]]["verdict"] == "refused"
    assert open(env["c1"], "rb").read() == b"something new"


def test_changed_canonical_refuses(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _w(env["keep"], b"edited after indexing")
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.REFUSED and "canonical changed" in r["why"]
    assert os.path.exists(env["c1"]) and os.path.exists(env["c2"])


def test_missing_canonical_refuses(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    os.remove(env["keep"])
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.REFUSED and "canonical missing" in r["why"]
    assert os.path.exists(env["c1"])


def test_changed_copy_refuses_the_whole_group(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _w(env["c2"], b"different now")
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.REFUSED and "re-index" in r["why"]
    assert os.path.exists(env["c1"]) and os.path.exists(env["c2"])


def test_canonical_failing_the_after_check_rolls_back(env, monkeypatch):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    real = da._check_hash
    calls = {"n": 0}

    def flaky(path, want, mbps):
        if path == env["keep"]:
            calls["n"] += 1
            if calls["n"] >= 3:              # plan, before-move pass; the after-check fails
                return "changed since it was indexed"
        return real(path, want, mbps)

    monkeypatch.setattr(da, "_check_hash", flaky)
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.ROLLED_BACK
    assert os.path.exists(env["c1"]) and os.path.exists(env["c2"])
    [mpath] = da.manifests_under(env["q"])
    man = json.load(open(mpath, encoding="utf-8"))
    assert {e["state"] for e in man["entries"]} == {"restored"}


def test_canonical_not_in_group_is_refused(env):
    _decide(env["db"], H, "keep_canonical", env["keep"] + ".nope")
    [r] = _run(env, apply=True)
    assert r["verdict"] == da.REFUSED and "not one of this group" in r["why"]


def test_remote_copies_refuse(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    [r] = da.run_apply(env["db"], [H], "another-box", True, env["q"], 0, log=lambda *a: None)
    assert r["verdict"] == da.REFUSED and "other machines" in r["why"]
    assert os.path.exists(env["c1"])


def test_not_a_hash_is_refused(env):
    [r] = da.run_apply(env["db"], ["'; drop table files; --"], M, True, env["q"], 0)
    assert r["verdict"] == da.REFUSED


@pytest.mark.parametrize("path,in_git,moving,expect", [
    ("F:/Leadfuel/repos/novahub/a.txt", 0, True, "repo path"),
    ("F:/x/.claude/worktrees/w/a.txt", 0, True, "repo path"),
    ("F:/data/a.txt", 1, True, "git repo (index)"),
    ("F:/repos/resonance/ch1.md", 0, False, "book"),
    ("F:/Finance/taxes/2025.pdf", 0, True, "privacy tier"),
    ("F:/stuff/.env", 0, False, "privacy tier"),
    ("F:/.cluster-files-quarantine/b/files/x", 0, True, "quarantine"),
])
def test_protected_paths(path, in_git, moving, expect):
    assert expect in (da.protected(path, in_git, moving) or "")


def test_canonical_inside_a_repo_is_allowed_but_a_copy_is_not():
    assert da.protected("F:/data/a.txt", 1, moving=False) is None
    assert da.protected("F:/data/a.txt", 1, moving=True)


def test_copy_under_a_git_folder_refuses(tmp_path):
    root = tmp_path / "d"
    _w(root / "keep" / "x.bin", BODY)
    _w(root / "proj" / "sub" / "x.bin", BODY)
    os.makedirs(root / "proj" / ".git")
    db = str(tmp_path / "i.sqlite")
    _index(db, root)
    # make the copy look non-git in the index so the live .git check is what refuses it
    con = fi.connect(db)
    con.execute("UPDATE files SET in_git=0")
    con.commit()
    con.close()
    _decide(db, H, "keep_canonical", fi.norm(str(root / "keep" / "x.bin")))
    [r] = da.run_apply(db, [H], M, True, str(root / fi.QUARANTINE_DIRNAME), 0)
    assert r["verdict"] == da.REFUSED and "git" in r["why"]
    assert os.path.exists(root / "proj" / "sub" / "x.bin")


def test_quarantine_is_not_indexed(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _run(env, apply=True)
    _index(env["db"], env["root"])
    con = fi.connect_ro(env["db"])
    paths = [r[0] for r in con.execute("SELECT path FROM files")]
    con.close()
    assert not any(fi.QUARANTINE_DIRNAME in p for p in paths)


def test_purge_refuses_young_batches_and_is_dry_by_default(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _run(env, apply=True)
    [mpath] = da.manifests_under(env["q"])
    young = da.purge(env["q"], apply=True)
    assert [x["verdict"] for x in young] == ["too-young"]
    later = lambda: json.load(open(mpath, encoding="utf-8"))["created_ts"] + 31 * da.DAY  # noqa: E731
    dry = da.purge(env["q"], apply=False, clock=later)
    assert [x["verdict"] for x in dry] == ["purge", "purge"]
    assert all(os.path.exists(x["quarantined"]) for x in dry)


def test_purge_days_cannot_go_under_30(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _run(env, apply=True)
    [mpath] = da.manifests_under(env["q"])
    t = json.load(open(mpath, encoding="utf-8"))["created_ts"] + 5 * da.DAY
    assert [x["verdict"] for x in da.purge(env["q"], True, days=1, clock=lambda: t)] == ["too-young"]


def test_purge_after_30_days_deletes_only_with_a_live_canonical(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _run(env, apply=True)
    [mpath] = da.manifests_under(env["q"])
    later = json.load(open(mpath, encoding="utf-8"))["created_ts"] + 31 * da.DAY
    os.remove(env["keep"])                      # canonical gone: the quarantined copies are the last ones
    kept = da.purge(env["q"], apply=True, clock=lambda: later)
    assert {x["verdict"] for x in kept} == {"kept"}
    assert all(os.path.exists(x["quarantined"]) for x in kept)


def test_purge_after_30_days_with_apply(env):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _run(env, apply=True)
    [mpath] = da.manifests_under(env["q"])
    later = json.load(open(mpath, encoding="utf-8"))["created_ts"] + 31 * da.DAY
    res = da.purge(env["q"], apply=True, clock=lambda: later)
    assert [x["verdict"] for x in res] == ["purged", "purged"]
    assert not any(os.path.exists(x["quarantined"]) for x in res)
    assert os.path.exists(env["keep"])


def test_all_keep_canonical_reads_only_keep_canonical(env, tmp_path):
    _decide(env["db"], H, "keep_canonical", env["keep"])
    _decide(env["db"], "b" * 64, "keep_both", "x")
    _decide(env["db"], "c" * 64, "decide_later", "y")
    assert da.keep_canonical_hashes(env["db"]) == [H]


def test_apply_never_deletes():
    """`os.remove` appears only in purge; apply and restore only rename."""
    src = open(os.path.join(_NODE, "dedupe_apply.py"), encoding="utf-8").read()
    body = src.split("def purge(", 1)
    assert "os.remove" not in body[0] and "shutil" not in src and "unlink" not in src
    assert "os.remove" in body[1]


def test_index_is_opened_read_only():
    src = open(os.path.join(_NODE, "dedupe_apply.py"), encoding="utf-8").read()
    assert "fi.connect(" not in src and "fi.connect_ro(" in src
