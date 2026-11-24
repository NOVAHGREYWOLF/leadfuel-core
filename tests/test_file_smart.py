"""Cluster files part 4 (smart indexing): near-duplicates and tags stay local, read the index only,
never content-read the privacy tier, and say `unknown` instead of inventing a tag."""
import ast
import hashlib
import importlib.util
import json
import os
import random
import re
import sqlite3
import sys
import zipfile
from datetime import datetime

import pytest

_HERE = os.path.dirname(__file__)
_NODE = os.path.join(_HERE, os.pardir, "node")
for _name in ("file_index", "file_smart"):
    _spec = importlib.util.spec_from_file_location(_name, os.path.join(_NODE, f"{_name}.py"))
    _mod = importlib.util.module_from_spec(_spec)
    sys.modules[_name] = _mod
    _spec.loader.exec_module(_mod)
fi = sys.modules["file_index"]
fs = sys.modules["file_smart"]

TEXT = " ".join(f"word{i % 97} plan{i % 13} zebra migration step {i}" for i in range(120))
OTHER = " ".join(f"unrelated{i % 89} garden{i % 7} tomato harvest {i}" for i in range(120))


def _w(p, data, mtime=None):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    mode = "wb" if isinstance(data, bytes) else "w"
    with open(p, mode, **({} if mode == "wb" else {"encoding": "utf-8"})) as fh:
        fh.write(data)
    if mtime:
        os.utime(p, (mtime, mtime))


def _docx(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with zipfile.ZipFile(p, "w") as z:
        z.writestr("word/document.xml", f"<w:document><w:body><w:p><w:t>{text}</w:t></w:p></w:body></w:document>")


def _picture(seed, w=320, h=200):
    from PIL import Image
    rnd = random.Random(seed)
    im = Image.new("L", (16, 10))
    im.putdata([rnd.randrange(256) for _ in range(160)])
    return im.resize((w, h), Image.Resampling.BILINEAR).convert("RGB")


@pytest.fixture
def idx(tmp_path, monkeypatch):
    monkeypatch.setattr(fi, "TRANSIENT_SEGMENTS", {"downloads"})
    r = tmp_path / "F"
    _w(str(r / "notes" / "plan.md"), TEXT, mtime=1_600_000_000)
    _w(str(r / "Downloads" / "plan.html"), f"<html><body><p>{TEXT}</p><script>var x=1;</script></body></html>")
    _docx(str(r / "notes" / "plan.docx"), TEXT)
    _w(str(r / "notes" / "garden.md"), OTHER)
    _w(str(r / "notes" / "short.md"), "too short to compare")
    _w(str(r / "Taxes 2025" / "return.md"), TEXT)                     # private: never read
    _w(str(r / "Taxes 2025" / "return.pdf"), b"%PDF-1.4 not really")  # private pdf
    _w(str(r / "papers" / "plan.pdf"), b"%PDF-1.4 stand-in")
    pytest.importorskip("PIL")
    img = _picture(1)
    for d in ("Pictures", "Bank statements"):
        os.makedirs(r / d, exist_ok=True)
    img.save(str(r / "Pictures" / "IMG_0042.png"))
    img.resize((160, 100)).save(str(r / "Downloads" / "IMG_0042-160x100.jpg"), quality=90)
    img.crop((0, 0, 200, 200)).save(str(r / "Pictures" / "IMG_0042-square.png"))   # other aspect
    _picture(2).save(str(r / "Pictures" / "IMG_0099.png"))
    img.save(str(r / "Bank statements" / "scan.png"))                              # private: never decoded
    db = str(tmp_path / "index.sqlite")
    con = fi.connect(db)
    fi.scan(con, "greywolf", str(r), log=lambda *a: None)
    fi.hash_candidates(con, mbps=0, log=lambda *a: None)
    con.close()
    return {"root": r, "db": db, "smart": str(tmp_path / "smart.sqlite")}


def _cons(idx):
    return fs.connect_index_ro(idx["db"]), fs.connect_smart(idx["smart"])


def _quiet(*a, **k):
    pass


# --------------------------------------------------------------------------- images


def test_resized_photo_is_a_near_duplicate_and_largest_durable_copy_is_kept(idx):
    ic, sc = _cons(idx)
    st = fs.sign_images(ic, sc, 1, "greywolf", 100, fi.Throttle(0), fi.Budget(None), None, log=_quiet)
    assert st["done"] == 4 and st["private"] == 1          # the bank-statement scan was never decoded
    g = fs.build_near_groups(ic, sc, 1, "greywolf", "image", log=_quiet)
    assert g["groups"] == 1
    grp = sc.execute("SELECT * FROM near_groups WHERE kind='image'").fetchone()
    assert grp["canonical"].endswith("Pictures/IMG_0042.png")
    members = {os.path.basename(m["path"]): m for m in sc.execute("SELECT * FROM near_members")}
    assert set(members) == {"IMG_0042.png", "IMG_0042-160x100.jpg"}   # the square crop is not "the same photo"
    assert "160x100 vs 320x200" in members["IMG_0042-160x100.jpg"]["note"]
    assert not any("scan.png" in p for (p,) in sc.execute("SELECT path FROM imgsig"))


def test_dhash_is_stable_under_resize_and_differs_between_photos(tmp_path):
    pytest.importorskip("PIL")
    a, b, c = (str(tmp_path / n) for n in ("a.png", "b.jpg", "c.png"))
    _picture(5).save(a)
    _picture(5).resize((640, 400)).save(b, quality=85)
    _picture(6).save(c)
    ha, hb, hc = (fs.dhash_image(p)[0] for p in (a, b, c))
    assert fs.hamming(ha, hb) <= fs.IMG_MAX_DIST
    assert fs.hamming(ha, hc) > fs.IMG_MAX_DIST


def test_flat_images_are_skipped_and_counted():
    sigs = [{"dhash": "0000000000000000", "w": 10, "h": 10}, {"dhash": "0000000000000001", "w": 10, "h": 10}]
    pairs, flat = fs.image_pairs(sigs)
    assert pairs == [] and flat == 2


def test_image_sample_prefers_shared_stems_and_is_deterministic():
    rows = [{"name": n, "path": "/" + n} for n in
            ("IMG_1-1024x768.jpg", "IMG_1.png", "a.jpg", "b.jpg", "c.jpg", "IMG_2 (1).jpg", "img_2.jpg")]
    s = fs.pick_sample(rows, 5)
    assert {r["name"] for r in s[:4]} == {"IMG_1-1024x768.jpg", "IMG_1.png", "IMG_2 (1).jpg", "img_2.jpg"}
    assert s == fs.pick_sample(rows, 5)
    assert fs.norm_stem("IMG_0042-160x100.jpg") == fs.norm_stem("IMG_0042.png") == "img_0042"


def test_byte_budget_stops_and_leaves_the_rest_unknown(idx):
    ic, sc = _cons(idx)
    st = fs.sign_images(ic, sc, 1, "greywolf", 100, fi.Throttle(0), fi.Budget(None), 1, log=_quiet)
    assert st["stopped"] == "byte budget" and st["done"] == 0


# --------------------------------------------------------------------------- documents


def test_same_document_in_md_html_docx_is_one_cross_format_group(idx, monkeypatch):
    calls = []
    monkeypatch.setattr(fs, "pdf_text", lambda p: calls.append(p) or TEXT)
    ic, sc = _cons(idx)
    st = fs.sign_docs(ic, sc, 1, "greywolf", None, 10, fi.Throttle(0), fi.Budget(None), None, log=_quiet)
    assert st["private"] == 2 and st["too_short"] == 1 and st["pdf_signed"] == 1
    assert calls and not any("Taxes" in p for p in calls)               # the private pdf was never opened
    g = fs.build_near_groups(ic, sc, 1, "greywolf", "doc", log=_quiet)
    assert g["groups"] == 1 and g["cross_format_groups"] == 1
    grp = sc.execute("SELECT * FROM near_groups WHERE kind='doc'").fetchone()
    assert grp["formats"] == ".docx,.html,.md,.pdf"
    assert grp["canonical"].endswith("notes/plan.md") or grp["canonical"].endswith("notes/plan.docx")
    paths = [m["path"] for m in sc.execute("SELECT path FROM near_members")]
    assert not any("garden" in p or "Taxes" in p for p in paths)
    assert not any("Taxes" in p for (p,) in sc.execute("SELECT path FROM docsig"))


def test_minhash_same_text_same_signature_and_unrelated_text_low():
    a = fs.minhash(fs.doc_words(TEXT, ".md"))
    b = fs.minhash(fs.doc_words(f"<p>{TEXT}</p><style>p{{color:red}}</style>", ".html"))
    c = fs.minhash(fs.doc_words(OTHER, ".md"))
    assert fs.similarity(a, b) == 1.0
    assert fs.similarity(a, c) < 0.2
    edited = TEXT.replace("step 5 ", "step five ")
    assert fs.similarity(a, fs.minhash(fs.doc_words(edited, ".md"))) >= 0.8


def test_byte_identical_sets_are_left_to_the_exact_report(tmp_path, monkeypatch):
    monkeypatch.setattr(fi, "TRANSIENT_SEGMENTS", {"downloads"})
    r = tmp_path / "F"
    _w(str(r / "a" / "x.md"), TEXT)
    _w(str(r / "b" / "x.md"), TEXT)
    db = str(tmp_path / "i.sqlite")
    con = fi.connect(db)
    fi.scan(con, "greywolf", str(r), log=_quiet)
    fi.hash_candidates(con, mbps=0, log=_quiet)
    con.close()
    ic, sc = fs.connect_index_ro(db), fs.connect_smart(str(tmp_path / "s.sqlite"))
    fs.sign_docs(ic, sc, 1, "greywolf", None, 0, fi.Throttle(0), fi.Budget(None), None, log=_quiet)
    g = fs.build_near_groups(ic, sc, 1, "greywolf", "doc", log=_quiet)
    assert g["groups"] == 0 and g["exact_only_skipped"] == 1


def test_regrouping_replaces_old_groups(idx):
    ic, sc = _cons(idx)
    fs.sign_docs(ic, sc, 1, "greywolf", None, 0, fi.Throttle(0), fi.Budget(None), None, log=_quiet)
    fs.build_near_groups(ic, sc, 1, "greywolf", "doc", log=_quiet)
    fs.build_near_groups(ic, sc, 2, "greywolf", "doc", log=_quiet)
    assert sc.execute("SELECT COUNT(*) FROM near_groups WHERE kind='doc'").fetchone()[0] == 1


# --------------------------------------------------------------------------- tags


@pytest.mark.parametrize("path,ext,ftype,private,facet,value", [
    ("F:/Backups/x/report.docx", ".docx", "doc", None, "kind", "backup"),
    ("F:/SURFACE-offload-2026-11-18/a.py", ".py", "code", None, "kind", "backup"),
    ("F:/models/qwen.gguf", ".gguf", "binary", None, "kind", "model"),
    ("F:/novah/tools/run.py", ".py", "code", None, "kind", "code"),
    ("F:/novah/tools/run.py", ".py", "code", None, "scope", "estate"),
    ("C:/Users/novah/Desktop/run.py", ".py", "code", None, "scope", None),
    ("F:/Pictures/beach.jpg", ".jpg", "image", None, "scope", "personal"),
    ("F:/Pictures/beach.jpg", ".jpg", "image", None, "media", "image"),
    ("F:/Claude Sessions/handoff/x.md", ".md", "doc", None, "scope", "estate"),
    ("F:/work/clients/acme/site/index.html", ".html", "doc", None, "client", "acme"),
    ("F:/Leadfuel/home-node/app/x.py", ".py", "code", None, "project", "home-node"),
    ("F:/video/ai/app/main.py", ".py", "code", None, "project", "character-design"),
    ("F:/Taxes 2025/return.pdf", ".pdf", "doc", "financial:taxes", "privacy", "financial"),
    ("F:/Taxes 2025/return.pdf", ".pdf", "doc", "financial:taxes", "scope", "personal"),
])
def test_rule_tags(path, ext, ftype, private, facet, value):
    got = {f: v for f, v, _, _ in fs.rule_tags(path, ext, ftype, private, 0)}
    assert got.get(facet) == value


def test_retired_folder_names_map_to_ratified_arms():
    old = "nova" + "h" + "hound"
    got = {f: (v, c) for f, v, c, _ in fs.rule_tags(f"F:/Claude Sessions/{old}-notes/a.md", ".md", "doc", None, 0)}
    assert got["project"] == ("signal", 0.8)


def test_rules_never_guess_an_open_facet():
    got = {f for f, *_ in fs.rule_tags("F:/stuff/thing.xyz", ".xyz", "other", None, 0)}
    assert got == {"media"}                       # no kind, scope or project from nothing


def test_every_tag_has_source_and_confidence(idx):
    ic, sc = _cons(idx)
    fs.tag_rules(ic, sc, 1, "greywolf", log=_quiet)
    rows = sc.execute("SELECT source, confidence FROM tags").fetchall()
    assert rows and all(r["source"] == "rule" and 0 < r["confidence"] <= 1 for r in rows)
    with pytest.raises(sqlite3.IntegrityError):
        sc.execute("INSERT INTO tags VALUES ('m','p','kind','code','guess',0.5,'',1,'')")


def test_no_local_model_means_unknown_never_invented(idx, monkeypatch):
    ic, sc = _cons(idx)
    monkeypatch.setattr(fs, "model_available", lambda u, m: (False, "no local model server at test"))
    asked = []
    st = fs.tag_model(ic, sc, 1, "greywolf", 5, "http://127.0.0.1:9", "m", fi.Budget(None),
                      ask=lambda *a: asked.append(a) or [], log=_quiet)
    assert not asked and st["unknown_no_model"] == 5
    rows = sc.execute("SELECT value, confidence, source FROM tags WHERE source='model'").fetchall()
    assert len(rows) == 15 and {r["value"] for r in rows} == {"unknown"}
    assert all(r["confidence"] is None for r in rows)


def test_model_answers_are_cleaned_and_private_rows_go_by_path_only(idx, monkeypatch):
    ic, sc = _cons(idx)
    monkeypatch.setattr(fs, "model_available", lambda u, m: (True, "fake"))
    seen = []

    def ask(url, model, items):
        seen.extend(items)
        return [{"id": it["id"], "kind": "docs" if it["id"] % 2 else "spaceship", "scope": "estate",
                 "project": "nova" + "h" + "hub", "confidence": 3} for it in items]
    st = fs.tag_model(ic, sc, 1, "greywolf", 50, "http://127.0.0.1:9", "m", fi.Budget(None), ask=ask, log=_quiet)
    assert st["tagged"] == len(seen) > 0
    for it in seen:
        if fi.privacy_of(it["path"]):
            assert "snippet" not in it
    assert any("snippet" in it for it in seen)
    vals = {(r["facet"], r["value"]) for r in sc.execute("SELECT facet, value FROM tags WHERE source='model'")}
    assert ("kind", "unknown") in vals and ("kind", "docs") in vals and ("project", "hub") in vals
    assert max(r[0] for r in sc.execute("SELECT confidence FROM tags WHERE source='model' AND confidence IS NOT NULL")) <= 1.0


def test_model_must_be_on_loopback():
    with pytest.raises(SystemExit):
        fs.assert_loopback("http://192.168.1.20:11434")
    with pytest.raises(SystemExit):
        fs.model_available("https://api.example.com", "m")
    assert fs.assert_loopback("http://127.0.0.1:11434/") == "http://127.0.0.1:11434"


# --------------------------------------------------------------------------- guards


@pytest.mark.parametrize("hour,idle,ok", [(2, 0, True), (14, 5, False), (14, None, False), (14, 3600, True)])
def test_busy_hours_on_a_machine_in_use_refuse(hour, idle, ok):
    assert fs.may_run_now(datetime(2026, 11, 24, hour), idle=idle)[0] is ok


def test_index_is_opened_read_only_and_left_unchanged(idx, monkeypatch):
    monkeypatch.setattr(fs, "may_run_now", lambda: (True, "test"))
    before = hashlib.sha256(open(idx["db"], "rb").read()).hexdigest()
    rc = fs.main(["--db", idx["db"], "--smart-db", idx["smart"], "run", "--machine", "greywolf", "--no-lock",
                  "--skip", "model"])
    assert rc == 0
    assert fs.connect_smart(idx["smart"]).execute("SELECT COUNT(*) FROM near_groups").fetchone()[0] == 2
    ic = fs.connect_index_ro(idx["db"])
    with pytest.raises(sqlite3.OperationalError):
        ic.execute("DELETE FROM files")
    ic.close()
    assert hashlib.sha256(open(idx["db"], "rb").read()).hexdigest() == before


def test_cli_run_and_report_roundtrip(idx, tmp_path, monkeypatch, capsys):
    monkeypatch.setattr(fs, "may_run_now", lambda: (True, "test"))
    monkeypatch.setattr(fs, "model_available", lambda u, m: (False, "no local model server at test"))
    rc = fs.main(["--db", idx["db"], "--smart-db", idx["smart"], "run", "--machine", "greywolf", "--no-lock",
                  "--model-sample", "3"])
    assert rc == 0
    out = str(tmp_path / "rep")
    assert fs.main(["--smart-db", idx["smart"], "--db", idx["db"], "report", "--out", out]) == 0
    rep = json.load(open(os.path.join(out, "near.json"), encoding="utf-8"))
    assert rep["near"]["image"]["groups"] == 1 and rep["near"]["doc"]["groups"] == 1
    assert "unknown" in [v["value"] for v in rep["tags"]["kind"]["model"]]
    assert "Report only" in open(os.path.join(out, "near.md"), encoding="utf-8").read()
    run = fs.connect_smart(idx["smart"]).execute("SELECT state, counts FROM runs").fetchone()
    assert run["state"] == "complete" and "images" in json.loads(run["counts"])


def test_cli_refuses_without_the_heavy_lock(idx, monkeypatch, capsys):
    monkeypatch.setattr(fs, "may_run_now", lambda: (True, "test"))
    rc = fs.main(["--db", idx["db"], "--smart-db", idx["smart"], "run", "--heavy-lock", "Z:/missing.py"])
    assert rc == 3 and "heavy lock unknown" in capsys.readouterr().out


def test_cli_refuses_busy_hours(idx, monkeypatch, capsys):
    monkeypatch.setattr(fs, "may_run_now", lambda: (False, "busy hours and the machine is in use"))
    assert fs.main(["--db", idx["db"], "--smart-db", idx["smart"], "run", "--no-lock"]) == 4


def test_missing_index_is_an_error_not_empty(tmp_path):
    with pytest.raises(SystemExit):
        fs.connect_index_ro(str(tmp_path / "nope.sqlite"))


def test_source_has_no_destructive_calls_no_remote_network_no_retired_names():
    src = open(os.path.join(_NODE, "file_smart.py"), encoding="utf-8").read()
    tree = ast.parse(src)
    bad = {"remove", "unlink", "rmtree", "rename", "replace", "move", "rmdir", "truncate"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in bad and isinstance(node.value, ast.Name):
            assert node.value.id not in ("os", "shutil", "Path"), f"destructive call {node.value.id}.{node.attr}"
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [a.name for a in node.names] + [getattr(node, "module", "") or ""]
            assert not any(n.split(".")[0] in ("requests", "httpx", "socketserver", "ftplib", "smtplib")
                           for n in names)
    opens = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)
             and n.func.id == "open"]
    assert opens, "the check must see the open() calls it audits"
    writers = 0
    for n in opens:
        mode = n.args[1] if len(n.args) > 1 else next((k.value for k in n.keywords if k.arg == "mode"), None)
        assert isinstance(mode, ast.Constant), ast.get_source_segment(src, n)
        if set(mode.value) & set("wax+"):
            writers += 1                                    # only the report writes, into --out
            assert "a.out" in ast.get_source_segment(src, n.args[0]), ast.get_source_segment(src, n)
        else:
            assert mode.value == "rb", ast.get_source_segment(src, n)
    assert writers == 2
    assert re.findall(r"https?://[^\s\"']+", src) == ["http://127.0.0.1:11434"]
    retired = re.compile("|".join(r"\b" + "nova" + "h" + t + r"\b" for t in ("hub", "hawk", "hound", "herald", "hunt"))
                         + r"|\bsmart" + "icp", re.I)
    assert not retired.search(src)
