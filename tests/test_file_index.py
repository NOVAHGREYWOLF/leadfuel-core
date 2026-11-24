"""Cluster files parts 2+3 and the report-only dedupe: the local index is incremental and read-only,
privacy-tier files are never content-read, unknown is never reported as zero, and the dedupe report
proposes a canonical copy by the brief's rule without touching any file."""
import ast
import importlib.util
import json
import os
import sys
import threading
import urllib.request
import zipfile

import pytest

_HERE = os.path.dirname(__file__)
_PATH = os.path.join(_HERE, os.pardir, "node", "file_index.py")
spec = importlib.util.spec_from_file_location("file_index", _PATH)
fi = importlib.util.module_from_spec(spec)
sys.modules["file_index"] = fi
spec.loader.exec_module(fi)


def _w(p, data, mtime=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(p, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as fh:
        fh.write(data)
    if mtime:
        os.utime(p, (mtime, mtime))


@pytest.fixture
def tree(tmp_path, monkeypatch):
    # pytest's tmp_path sits under a Temp folder; only the tree's own Downloads counts as transient here
    monkeypatch.setattr(fi, "TRANSIENT_SEGMENTS", {"downloads"})
    r = tmp_path / "F"
    _w(str(r / "notes" / "plan.md"), "the zebra migration plan\n", mtime=1_600_000_000)
    _w(str(r / "copy" / "plan.md"), "the zebra migration plan\n", mtime=1_700_000_000)
    _w(str(r / "Downloads" / "plan (1).md"), "the zebra migration plan\n", mtime=1_500_000_000)
    _w(str(r / "big" / "a.bin"), b"\x00" * 300_000)
    _w(str(r / "big" / "b.bin"), b"\x00" * 300_000)
    _w(str(r / "big" / "c.bin"), b"\x00" * 299_999 + b"\x01")   # same size, differs at the end
    _w(str(r / "Taxes 2025" / "return.txt"), "zebra secret number 123-45-6789")
    _w(str(r / "Taxes 2025" / "return-copy.txt"), "zebra secret number 123-45-6789")
    _w(str(r / "proj" / ".env"), "API_KEY=zebra")
    _w(str(r / "repos" / "x" / "zebra.md"), "zebra")
    _w(str(r / "repos" / "resonance" / "book.md"), "zebra chapter")
    _w(str(r / "node_modules" / "z.js"), "zebra")
    _w(str(r / "doc" / "report.pdf"), b"%PDF-1.4 zebra")
    d = r / "doc" / "letter.docx"
    os.makedirs(d.parent, exist_ok=True)
    with zipfile.ZipFile(d, "w") as z:
        z.writestr("word/document.xml", "<w:document><w:p><w:t>quokka paragraph</w:t></w:p></w:document>")
    _w(str(r / "gitrepo" / ".git" / "HEAD"), "ref: x")
    _w(str(r / "gitrepo" / "src" / "unique.py"), "print('only here')")
    return r


def _db(tmp_path):
    return fi.connect(str(tmp_path / "idx" / "index.sqlite"))


def _index(con, tree, **kw):
    sc = fi.scan(con, "greywolf", str(tree), excludes=(str(tree / "repos"),), log=lambda *a: None, **kw)
    fi.hash_candidates(con, mbps=0, log=lambda *a: None)
    return sc


def _paths(con):
    return {r["path"].rsplit("/F/", 1)[-1] for r in con.execute("SELECT path FROM files")}


def test_scan_excludes_repos_book_and_skip_dirs(tmp_path, tree):
    con = _db(tmp_path)
    sc = _index(con, tree)
    assert sc["state"] == "complete"
    p = _paths(con)
    assert "notes/plan.md" in p and "gitrepo/src/unique.py" in p
    assert not any(x.startswith("repos/") for x in p)
    assert not any("node_modules" in x or "/.git/" in x or x.startswith("gitrepo/.git") for x in p)


def test_book_is_never_indexed_even_without_the_repos_exclude(tmp_path, tree):
    con = _db(tmp_path)
    fi.scan(con, "greywolf", str(tree), excludes=(), log=lambda *a: None)
    p = _paths(con)
    assert "repos/x/zebra.md" in p
    assert not any("resonance" in x for x in p)


def test_privacy_tier_is_never_content_read_or_hashed(tmp_path, tree):
    con = _db(tmp_path)
    _index(con, tree)
    rows = {r["name"]: r for r in con.execute("SELECT * FROM files WHERE private IS NOT NULL")}
    assert {"return.txt", "return-copy.txt", ".env"} <= set(rows)
    for r in rows.values():
        assert r["hash"] is None and r["quick"] is None
        assert r["hash_state"] == "private" and r["extract_state"] == "private"
    body = con.execute("SELECT group_concat(body) FROM fts").fetchone()[0]
    assert "123-45-6789" not in body and "API_KEY" not in body
    # names are still findable, flagged
    res = fi.search(con, "return", field="name")
    assert res["count"] == 2 and all(x["private"] for x in res["results"])


@pytest.mark.parametrize("path,tier", [
    ("F:/Apple Health/export.zip", "health"), ("F:/x/Bank statements/jan.pdf", "financial"),
    ("F:/novah/.ssh/config", "credential"), ("F:/a/id_ed25519", "credential"),
    ("F:/a/server.pem", "credential"), ("F:/a/b/.env", "credential"),
])
def test_privacy_rules(path, tier):
    assert fi.privacy_of(path).startswith(tier)


def test_privacy_rules_do_not_hit_plain_words():
    for p in ("F:/docs/syntax.md", "F:/video/monkeys.mp4", "F:/novah/reference/plan.md"):
        assert fi.privacy_of(p) is None


def test_content_search_finds_text_and_docx_and_reports_blind_spots(tmp_path, tree):
    con = _db(tmp_path)
    _index(con, tree)
    res = fi.search(con, "zebra", field="content")
    names = {x["path"].rsplit("/", 1)[-1] for x in res["results"]}
    assert {"plan.md", "plan (1).md"} <= names
    assert "return.txt" not in names
    assert fi.search(con, "quokka")["count"] == 1
    joined = " ".join(res["notes"])
    assert "no-extractor" in joined and "private" in joined   # the pdf and the private files


def test_unindexed_machines_read_unknown_not_zero(tmp_path, tree):
    con = _db(tmp_path)
    _index(con, tree)
    res = fi.search(con, "zebra", machine="surface")
    assert res["count"] == 0
    assert any("surface: unknown" in n and "not absent" in n for n in res["notes"])
    cov = fi.coverage(con)
    assert cov["greywolf"]["state"] == "indexed"
    assert cov["overlord"]["state"] == "unknown"


def test_filters_type_ext_date(tmp_path, tree):
    con = _db(tmp_path)
    _index(con, tree)
    assert {x["type"] for x in fi.search(con, "", ftype="code")["results"]} == {"code"}
    assert all(x["path"].endswith(".md") for x in fi.search(con, "plan", ext="md")["results"])
    old = fi.search(con, "plan", field="name", before="2018-01-01")["results"]
    assert [x["path"].rsplit("/F/", 1)[-1] for x in old] == ["Downloads/plan (1).md"]


def test_incremental_rescan_changes_only_what_changed(tmp_path, tree):
    con = _db(tmp_path)
    first = _index(con, tree)
    second = fi.scan(con, "greywolf", str(tree), excludes=(str(tree / "repos"),), log=lambda *a: None)
    assert first["new"] > 0 and second["new"] == 0 and second["changed"] == 0 and second["removed"] == 0
    _w(str(tree / "notes" / "plan.md"), "now about otters\n")
    os.remove(str(tree / "copy" / "plan.md"))
    third = fi.scan(con, "greywolf", str(tree), excludes=(str(tree / "repos"),), log=lambda *a: None)
    assert third["changed"] == 1 and third["removed"] == 1
    row = con.execute("SELECT hash, quick, hash_state FROM files WHERE path LIKE '%notes/plan.md'").fetchone()
    assert row["hash"] is None and row["hash_state"] == "pending"
    assert fi.search(con, "otters")["count"] == 1


def test_partial_scan_never_removes_rows(tmp_path, tree):
    con = _db(tmp_path)
    _index(con, tree)
    n = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    sc = fi.scan(con, "greywolf", str(tree), excludes=(str(tree / "repos"),), budget=fi.Budget(-1),
                 log=lambda *a: None)
    assert sc["state"] == "partial" and sc["removed"] == 0
    assert con.execute("SELECT COUNT(*) FROM files").fetchone()[0] == n
    assert fi.coverage(con)["greywolf"]["state"] == "partial"


def test_unreadable_dir_keeps_its_rows(tmp_path, tree, monkeypatch):
    con = _db(tmp_path)
    _index(con, tree)
    real = os.scandir
    bad = str(tree / "notes")

    def fake(p):
        if os.path.abspath(p) == os.path.abspath(bad):
            raise PermissionError(p)
        return real(p)
    monkeypatch.setattr(fi.os, "scandir", fake)
    sc = fi.scan(con, "greywolf", str(tree), excludes=(str(tree / "repos"),), log=lambda *a: None)
    assert sc["unreadable"] == 1 and sc["removed"] == 0
    assert con.execute("SELECT COUNT(*) FROM files WHERE path LIKE '%notes/plan.md'").fetchone()[0] == 1
    assert con.execute("SELECT COUNT(*) FROM unreadable").fetchone()[0] == 1


def test_dedupe_groups_rank_and_canonical(tmp_path, tree):
    con = _db(tmp_path)
    _index(con, tree)
    rep = fi.dedupe_groups(con)
    assert rep["groups_total"] == 2
    top = rep["groups"][0]
    assert top["size"] == 300_000 and top["copies"] == 2 and top["reclaimable"] == 300_000
    plan = rep["groups"][1]
    assert plan["copies"] == 3
    # Downloads copy is oldest but transient; of the two ordinary copies the older wins
    assert plan["canonical"]["path"].endswith("notes/plan.md")
    assert "oldest" in plan["reason"]
    # the same-size-but-different file is not grouped
    assert not any(o["path"].endswith("c.bin") for g in rep["groups"] for o in g["others"])
    assert rep["hash_coverage"]["private"] == 3


def test_canonical_prefers_git_repo():
    copies = [{"machine": "g", "path": "F:/a/x.txt", "mtime": 1, "in_git": 0},
              {"machine": "g", "path": "F:/repo/x.txt", "mtime": 9, "in_git": 1}]
    c, why = fi.propose_canonical(copies)
    assert c["path"] == "F:/repo/x.txt" and "git" in why


def test_quick_hash_collision_resolved_by_full_hash(tmp_path):
    r = tmp_path / "q"
    head = b"H" * fi.QUICK_BYTES
    _w(str(r / "a"), head + b"A" * 1000 + head)
    _w(str(r / "b"), head + b"B" * 1000 + head)
    con = _db(tmp_path)
    fi.scan(con, "greywolf", str(r), log=lambda *a: None)
    st = fi.hash_candidates(con, mbps=0, log=lambda *a: None)
    assert st["quick"] == 2 and st["full"] == 2
    assert fi.dedupe_groups(con)["groups_total"] == 0


def test_byte_budget_stops_and_leaves_unknown(tmp_path, tree):
    con = _db(tmp_path)
    fi.scan(con, "greywolf", str(tree), excludes=(str(tree / "repos"),), log=lambda *a: None)
    st = fi.hash_candidates(con, mbps=0, byte_budget=10, log=lambda *a: None)
    assert st["stopped"] == "byte budget" and st["full"] == 0
    assert fi.dedupe_groups(con)["hash_coverage"]["quick"] > 0


def test_throttle_sleeps_to_cap_rate():
    t = [0.0]
    slept = []
    th = fi.Throttle(1, sleep=lambda s: (slept.append(s), t.__setitem__(0, t[0] + s)), clock=lambda: t[0])
    th.took(2 * 1024 * 1024)
    assert slept and abs(slept[0] - 2.0) < 1e-6


def test_decisions_record_only_and_never_touch_files(tmp_path, tree):
    con = _db(tmp_path)
    _index(con, tree)
    before = sorted((p, os.path.getsize(p)) for p in map(str, tree.rglob("*")) if os.path.isfile(p))
    rep = fi.dedupe_groups(con)
    h = rep["groups"][0]["hash"]
    n = fi.record_decisions(con, {h: {"decision": "keep_canonical", "canonical": "x"},
                                  "bad": {"decision": "keep_canonical"},
                                  "0" * 64: {"decision": "delete_now"}})
    assert n == 1
    assert fi.dedupe_groups(con)["groups"][0]["decision"] == "keep_canonical"
    after = sorted((p, os.path.getsize(p)) for p in map(str, tree.rglob("*")) if os.path.isfile(p))
    assert before == after


def test_dedupe_page_has_three_choices_and_no_network():
    rep = {"generated": "x", "groups_total": 0, "reclaimable_total": 0, "groups": [],
           "hash_coverage": {}, "note": ""}
    page = fi.dedupe_page(rep)
    for label in ("Keep canonical", "Keep both", "Decide later"):
        assert label in page
    for bad in ("fetch(", "XMLHttpRequest", "http://", "https://", "WebSocket"):
        assert bad not in page
    assert "Nothing on any drive is moved or deleted" in page


def test_source_has_no_destructive_calls_and_no_outbound_network():
    src = open(_PATH, encoding="utf-8").read()
    tree = ast.parse(src)
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) \
                and isinstance(node.func.value, ast.Name):
            calls.add((node.func.value.id, node.func.attr))
    for mod in ("os", "shutil", "Path", "pathlib"):
        for bad in ("remove", "unlink", "rmtree", "rename", "replace", "move", "rmdir", "truncate",
                    "removedirs", "renames"):
            assert (mod, bad) not in calls, (mod, bad)
    assert "shutil" not in src
    for mod in ("requests", "urllib.request", "http.client", "smtplib", "ftplib"):
        assert f"import {mod}" not in src
    # every open() of an indexed path is read-only
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", None) == "open":
            if len(node.args) > 1 and isinstance(node.args[1], ast.Constant):
                mode = node.args[1].value
                if "w" in mode:
                    # only report outputs and the token file are written
                    assert ast.unparse(node.args[0]).startswith(("os.path.join(a.out", "tok")), ast.unparse(node)


def test_serve_refuses_non_loopback(tmp_path):
    with pytest.raises(SystemExit):
        fi.serve(str(tmp_path / "x.sqlite"), host="0.0.0.0", port=0)


def test_serve_search_api_on_loopback(tmp_path, tree):
    db = str(tmp_path / "idx" / "index.sqlite")
    con = fi.connect(db)
    _index(con, tree)
    con.close()
    srv = fi.ThreadingHTTPServer(("127.0.0.1", 0), fi.make_handler(db))
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    try:
        base = f"http://127.0.0.1:{srv.server_address[1]}"
        d = json.load(urllib.request.urlopen(base + "/api/search?q=zebra&field=name&machine=greywolf&limit=x"))
        assert "results" in d
        page = urllib.request.urlopen(base + "/").read().decode()
        assert "Cluster file search" in page
        dd = urllib.request.urlopen(base + "/dedupe").read().decode()
        assert "Keep both" in dd
    finally:
        srv.shutdown()


def test_cli_index_refuses_without_heavy_lock(tmp_path, tree, capsys):
    rc = fi.main(["--db", str(tmp_path / "i.sqlite"), "index", str(tree), "--heavy-lock", str(tmp_path / "none.py")])
    assert rc == 3 and "heavy lock unknown" in capsys.readouterr().out


def test_cli_index_search_dedupe_roundtrip(tmp_path, tree, capsys):
    db = str(tmp_path / "i.sqlite")
    assert fi.main(["--db", db, "index", str(tree), "--machine", "greywolf", "--no-lock", "--mbps", "0",
                    "--exclude", str(tree / "repos")]) == 0
    assert fi.main(["--db", db, "search", "zebra"]) == 0
    out = capsys.readouterr().out
    assert "greywolf:" in out and "result(s)" in out
    outdir = tmp_path / "rep"
    assert fi.main(["--db", db, "dedupe", "--out", str(outdir)]) == 0
    assert (outdir / "dedupe.html").exists() and json.load(open(outdir / "dedupe.json"))["groups_total"] == 2


def test_cli_unknown_lock_does_not_queue(tmp_path, tree, capsys):
    t0 = __import__("time").monotonic()
    rc = fi.main(["--db", str(tmp_path / "i.sqlite"), "index", str(tree), "--wait-lock", "5",
                  "--heavy-lock", str(tmp_path / "none.py")])
    assert rc == 3 and __import__("time").monotonic() - t0 < 30


def test_search_works_while_a_scan_holds_the_write_lock(tmp_path, tree, capsys):
    db = str(tmp_path / "i.sqlite")
    con = fi.connect(db)
    _index(con, tree)
    con.execute("BEGIN IMMEDIATE")
    con.execute("UPDATE files SET seen_scan=seen_scan")   # a scan mid-transaction
    try:
        assert fi.main(["--db", db, "search", "zebra"]) == 0
        assert "result(s)" in capsys.readouterr().out
    finally:
        con.rollback()


def test_search_on_a_missing_index_reads_unknown(tmp_path):
    res = fi.search(fi.connect_ro(str(tmp_path / "new" / "i.sqlite")), "x")
    assert res["count"] == 0 and any("greywolf: unknown" in n for n in res["notes"])
