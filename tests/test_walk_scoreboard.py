"""WATCH p16-1: the walk scoreboard moves a cell only on a run file, and says unknown when it cannot see.

The subject of the guard tests is the false pass: a scoreboard that shows a green cell because a run file
exists, while its evidence is gone, changed, stale, future dated or never decided by the owner. Every fixture
is a throwaway tree under tmp_path; nothing here writes into the real watch/walk folder.
"""
import datetime as dt
import importlib.util
import json
import os
import re

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "walk_scoreboard.py")
_spec = importlib.util.spec_from_file_location("walk_scoreboard", _PATH)
ws = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(ws)

NOW = dt.datetime(2026, 11, 23, 20, 0, 0, tzinfo=dt.timezone.utc)
HOUR = dt.timedelta(hours=1)
EVID = [("proof.txt", b"a result that a person can read")]
OWNER = {"by": "owner", "source": "owner typed it in the Router desk chat on 2026-11-23"}
WALK = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "walk")


def make_grid(tmp_path, max_age=None):
    grid = {"schema": ws.SCHEMA_GRID, "notes": [], "built_from": [],
            "link": {"repo": "o/r", "ref_default": "main", "grid_file": "watch/walk/walk_grid.json",
                     "runs_dir": "watch/walk/runs", "evidence_dir": "watch/walk/evidence"},
            "sections": [
                {"id": "a", "title": "A", "blurb": "b", "kind": "list", "cells": [
                    {"id": "a-one", "label": "One", "needs": "n1", "max_age_hours": max_age},
                    {"id": "a-two", "label": "Two", "needs": "n2"},
                    {"id": "a-line", "label": "Line", "needs": "n3", "rolls_up_from": {"section": "m", "needs": "result"}}]},
                {"id": "m", "title": "M", "blurb": "", "kind": "matrix", "row_label": "Row",
                 "columns": [{"id": "x", "label": "X", "needs": "nx"}, {"id": "y", "label": "Y", "needs": "ny"}],
                 "rows": [{"id": "r1", "label": "R1"}, {"id": "r2", "label": "R2"}]}]}
    path = tmp_path / "grid.json"
    path.write_text(json.dumps(grid), encoding="utf-8")
    return str(path), ws.load_grid(str(path))


def run(tmp_path, gp, at=NOW):
    data, text, page = ws.build(gp, root=str(tmp_path), now=at, write=False)
    status = {c["id"]: c["status"] for s in data["sections"] for c in s["cells"]}
    return data, status, page


def record(tmp_path, grid, cell, result="pass", ago=1, **kw):
    kw.setdefault("evidence_items", EVID)
    if result in ("fail", "unknown", "closed_by_design"):
        kw.setdefault("reason", "because")
    if result == "closed_by_design":
        kw.setdefault("decision", OWNER)
    return ws.write_run(str(tmp_path), grid, cell, result, kw.pop("by", "a desk"), kw.pop("how", "ran it"),
                        kw.pop("evidence_items"), now=NOW, ran_at=NOW - ago * HOUR, **kw)


# ---------------------------------------------------------------- the real grid

def test_real_grid_holds_every_part_of_the_done_when(tmp_path):
    grid = ws.load_grid()
    by = {s["id"]: s for s in grid["sections"]}
    assert len(by["lines"]["cells"]) == 15
    assert len(by["rooms"]["cells"]) == 9
    assert len(by["spokes"]["rows"]) == 33 and len(by["spokes"]["columns"]) == 2 and len(by["spokes"]["cells"]) == 66
    assert len(by["machines"]["rows"]) == 6 and len(by["machines"]["cells"]) == 12
    assert len(by["protect"]["cells"]) == 6
    ids = [c["id"] for s in grid["sections"] for c in s["cells"]]
    assert len(ids) == len(set(ids)) == 108
    assert all(c["text"].strip() for c in by["lines"]["cells"])


def test_every_cell_starts_not_tested_without_a_run(tmp_path):
    data, _, _ = ws.build(root=str(tmp_path), now=NOW, write=False)   # real grid, empty runs folder
    assert data["counts"] == {"not tested": 108, "pass": 0, "fail": 0, "unknown": 0, "closed by design": 0}
    assert data["headline"]["text"] == "0 / 108"
    assert all(c["proof"]["kind"] == "needed" for s in data["sections"] for c in s["cells"])


# ---------------------------------------------------------------- the rule: a run file moves a cell

def test_positive_controls_pass_and_a_reader_that_always_says_pass_cannot_get_through(monkeypatch):
    assert ws.run_controls() == (True, [])
    monkeypatch.setattr(ws, "resolve_cell", lambda cell, *a, **k: {
        "status": ws.PASS, "reason": "x", "run": None, "evidence": [], "runs_seen": 0, "degraded": False})
    ok, bad = ws.run_controls()
    assert not ok and bad


def test_one_valid_pass_moves_exactly_one_cell(tmp_path):
    gp, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-one")
    data, st, _ = run(tmp_path, gp)
    assert st["a-one"] == ws.PASS
    assert [k for k, v in st.items() if v != ws.NOT_TESTED] == ["a-one"]
    assert data["headline"]["text"] == "1 / 7"
    cell = data["sections"][0]["cells"][0]
    assert cell["proof"]["kind"] == "evidence" and cell["proof"]["url"].startswith("https://github.com/o/r/blob/main/watch/walk/evidence/")


@pytest.mark.parametrize("damage", ["delete", "change"])
def test_evidence_that_cannot_be_seen_or_has_changed_reads_unknown_never_pass(tmp_path, damage):
    gp, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-one")
    ev = os.path.join(str(tmp_path), "watch", "walk", "evidence")
    f = os.path.join(ev, os.listdir(ev)[0])
    if damage == "delete":
        os.remove(f)
    else:
        with open(f, "wb") as fh:
            fh.write(b"tampered")
    data, st, _ = run(tmp_path, gp)
    assert st["a-one"] == ws.UNKNOWN
    cell = data["sections"][0]["cells"][0]
    assert cell["degraded"] and "cannot be believed" in cell["status_reason"]
    assert data["headline"]["passed"] == 0


@pytest.mark.parametrize("path", ["../../outside.txt", "/etc/passwd", "watch\\walk\\evidence\\x", "watch/walk/runs/a.json",
                                  "watch/walk/evidence/../runs/a.json"])
def test_evidence_path_must_stay_inside_the_evidence_folder(tmp_path, path):
    gp, grid = make_grid(tmp_path)
    rec = record(tmp_path, grid, "a-one")
    doc = json.load(open(rec, encoding="utf-8"))
    doc["evidence"][0]["path"] = path
    json.dump(doc, open(rec, "w", encoding="utf-8"))
    _, st, _ = run(tmp_path, gp)
    assert st["a-one"] == ws.UNKNOWN


def test_a_pass_or_fail_older_than_its_limit_reads_unknown(tmp_path):
    gp, grid = make_grid(tmp_path, max_age=24)
    record(tmp_path, grid, "a-one", "pass", ago=2)
    assert run(tmp_path, gp)[1]["a-one"] == ws.PASS
    data, st, _ = run(tmp_path, gp, at=NOW + 30 * HOUR)
    assert st["a-one"] == ws.UNKNOWN
    assert "limit is 24 h" in data["sections"][0]["cells"][0]["status_reason"]


def test_staleness_counts_from_the_evidence_date_when_there_is_one(tmp_path):
    gp, grid = make_grid(tmp_path, max_age=24)
    record(tmp_path, grid, "a-one", "fail", ago=1, subject_at=NOW - 40 * HOUR)
    assert run(tmp_path, gp)[1]["a-one"] == ws.UNKNOWN


def test_a_future_dated_run_reads_unknown(tmp_path):
    gp, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-one", "pass", ago=0)
    assert run(tmp_path, gp, at=NOW - 2 * HOUR)[1]["a-one"] == ws.UNKNOWN
    with pytest.raises(ws.ScoreboardError):
        record(tmp_path, grid, "a-two", "pass", ago=-3)


def test_a_broken_newest_run_does_not_fall_back_to_an_older_pass(tmp_path):
    gp, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-one", "pass", ago=5)
    newer = record(tmp_path, grid, "a-one", "fail", ago=1)
    assert run(tmp_path, gp)[1]["a-one"] == ws.FAIL
    open(newer, "w").write("{not json")
    assert run(tmp_path, gp)[1]["a-one"] == ws.UNKNOWN


def test_newest_run_decides_and_history_is_counted(tmp_path):
    gp, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-one", "fail", ago=5)
    record(tmp_path, grid, "a-one", "pass", ago=1)
    data, st, _ = run(tmp_path, gp)
    assert st["a-one"] == ws.PASS and data["sections"][0]["cells"][0]["runs_seen"] == 2


def test_closed_by_design_needs_the_owner_a_source_and_evidence(tmp_path):
    gp, grid = make_grid(tmp_path)
    with pytest.raises(ws.ScoreboardError):
        record(tmp_path, grid, "a-one", "closed_by_design", decision={"by": "a desk", "source": "me"})
    with pytest.raises(ws.ScoreboardError):
        record(tmp_path, grid, "a-one", "closed_by_design", decision={"by": "owner", "source": ""})
    with pytest.raises(ws.ScoreboardError):
        record(tmp_path, grid, "a-one", "closed_by_design", evidence_items=[])
    record(tmp_path, grid, "a-one", "closed_by_design")
    data, st, _ = run(tmp_path, gp)
    assert st["a-one"] == ws.CLOSED
    assert data["headline"]["text"] == "0 / 6"          # closing lowers the denominator and nothing else
    assert data["headline"]["closed_by_design"] == 1


def test_closed_by_design_written_by_hand_without_the_owner_reads_unknown(tmp_path):
    gp, grid = make_grid(tmp_path)
    path = record(tmp_path, grid, "a-one", "closed_by_design")
    doc = json.load(open(path, encoding="utf-8"))
    doc["decision"] = {"by": "desk", "source": "x"}
    json.dump(doc, open(path, "w", encoding="utf-8"))
    data, st, _ = run(tmp_path, gp)
    assert st["a-one"] == ws.UNKNOWN and data["headline"]["text"] == "0 / 7"


def test_fail_and_unknown_results_need_a_reason(tmp_path):
    _, grid = make_grid(tmp_path)
    for result in ("fail", "unknown"):
        with pytest.raises(ws.ScoreboardError):
            ws.write_run(str(tmp_path), grid, "a-one", result, "a desk", "ran", EVID, now=NOW)


def test_a_run_for_a_cell_not_in_the_grid_changes_nothing_and_is_listed(tmp_path):
    gp, grid = make_grid(tmp_path)
    runs = tmp_path / "watch" / "walk" / "runs"
    runs.mkdir(parents=True)
    (runs / "ghost-cell__20261123T190000Z.json").write_text("{}", encoding="utf-8")
    (runs / "notes.txt").write_text("stray", encoding="utf-8")
    data, st, _ = run(tmp_path, gp)
    assert set(st.values()) == {ws.NOT_TESTED}
    problems = " | ".join(data["source"]["problems"])
    assert "ghost-cell" in problems and "notes.txt" in problems


def test_a_line_marked_pass_while_its_cells_are_open_gets_a_warning_but_keeps_its_status(tmp_path):
    gp, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-line", "pass")
    data, st, _ = run(tmp_path, gp)
    line = next(c for c in data["sections"][0]["cells"] if c["id"] == "a-line")
    assert st["a-line"] == ws.PASS and "4 of 4 linked cells" in line["warnings"][0]
    for cid in ("m-r1-x", "m-r1-y", "m-r2-x", "m-r2-y"):
        record(tmp_path, grid, cid, "fail", ago=2)       # a fail is a settled result for a "result" roll-up
    data, _, _ = run(tmp_path, gp)
    assert next(c for c in data["sections"][0]["cells"] if c["id"] == "a-line")["warnings"] == []


# ---------------------------------------------------------------- recording refuses private content

@pytest.mark.parametrize("blob", [b"path C:\\Users\\someone\\x", b"host 10.20.30.40 answered", b"mail a.b@example.com",
                                  b"token sk-abcdefghijklmnopqrstuvwxyz1234", b"-----BEGIN RSA PRIVATE KEY-----",
                                  b"see /home/someone/file"])
def test_public_repo_evidence_refuses_private_looking_content(tmp_path, blob):
    _, grid = make_grid(tmp_path)
    with pytest.raises(ws.ScoreboardError, match="public"):
        ws.write_run(str(tmp_path), grid, "a-one", "pass", "a desk", "ran", [("e.txt", blob)], now=NOW)
    assert not os.path.exists(os.path.join(str(tmp_path), "watch", "walk", "evidence"))


def test_a_run_file_is_never_overwritten(tmp_path):
    _, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-one")
    with pytest.raises(ws.ScoreboardError, match="never overwritten"):
        record(tmp_path, grid, "a-one")


def test_unknown_cell_and_bad_result_are_refused(tmp_path):
    _, grid = make_grid(tmp_path)
    with pytest.raises(ws.ScoreboardError):
        ws.write_run(str(tmp_path), grid, "nope", "pass", "a", "b", EVID, now=NOW)
    with pytest.raises(ws.ScoreboardError):
        ws.write_run(str(tmp_path), grid, "a-one", "green", "a", "b", EVID, now=NOW)


# ---------------------------------------------------------------- probes

SYNC_OK = ("=== vault_private_sync start 2026-11-23T10:00:00Z\n"
           "[claude-sessions] pushed 1 ref(s) ['refs/heads/main']; remote has 3 branch(es); ls-remote verified\n"
           "[leadfuel-estate] pushed 1 ref(s) ['refs/heads/main']; remote has 3 branch(es); ls-remote verified\n"
           "=== vault_private_sync end 2026-11-23T10:12:00Z exit=0\n")


def real_grid():
    return ws.load_grid()


def test_off_machine_probe_passes_only_on_the_readers_ok(tmp_path):
    log = tmp_path / "sync.log"
    log.write_text(SYNC_OK, encoding="utf-8")
    path = ws.probe_off_machine(str(tmp_path), real_grid(), str(log), now=NOW)
    data, _, _ = ws.build(root=str(tmp_path), now=NOW, write=False)
    cell = next(c for s in data["sections"] for c in s["cells"] if c["id"] == "protect-off-machine")
    assert cell["status"] == ws.PASS and os.path.basename(path).startswith("protect-off-machine__")
    ev = json.load(open(os.path.join(str(tmp_path), cell["evidence"][0]), encoding="utf-8"))
    assert "log_path" not in ev and ev["state"] == "ok"


def test_off_machine_probe_failed_and_missing_log(tmp_path):
    log = tmp_path / "sync.log"
    log.write_text(SYNC_OK.replace("exit=0", "exit=3"), encoding="utf-8")
    ws.probe_off_machine(str(tmp_path), real_grid(), str(log), now=NOW)
    cell = next(c for s in ws.build(root=str(tmp_path), now=NOW, write=False)[0]["sections"] for c in s["cells"]
                if c["id"] == "protect-off-machine")
    assert cell["status"] == ws.FAIL
    other = tmp_path / "second"
    other.mkdir()
    ws.probe_off_machine(str(other), real_grid(), str(tmp_path / "missing.log"), now=NOW)
    cell = next(c for s in ws.build(root=str(other), now=NOW, write=False)[0]["sections"] for c in s["cells"]
                if c["id"] == "protect-off-machine")
    assert cell["status"] == ws.UNKNOWN          # a reader that cannot see its log says unknown


@pytest.mark.parametrize("verdict,want", [("PASS", ws.PASS), ("FAIL", ws.FAIL), ("UNKNOWN", ws.UNKNOWN), ("SKIPPED-BUSY", ws.UNKNOWN)])
def test_nightly_probe_maps_the_last_verdict_line(tmp_path, verdict, want):
    log = tmp_path / "nightly.log"
    log.write_text("2026-11-22T17:00:00Z PASS main=abc\n2026-11-23T17:00:00Z %s main=def host=X\n    tests/test_x.py::t\n" % verdict, encoding="utf-8")
    ws.probe_nightly(str(tmp_path), real_grid(), str(log), now=NOW)
    cell = next(c for s in ws.build(root=str(tmp_path), now=NOW, write=False)[0]["sections"] for c in s["cells"]
                if c["id"] == "protect-nightly-full-run")
    assert cell["status"] == want


def test_nightly_pass_that_is_too_old_reads_unknown_and_a_missing_log_reads_unknown(tmp_path):
    log = tmp_path / "nightly.log"
    log.write_text("2026-11-20T17:00:00Z PASS main=abc host=X\n", encoding="utf-8")
    ws.probe_nightly(str(tmp_path), real_grid(), str(log), now=NOW)
    cell = lambda root: next(c for s in ws.build(root=str(root), now=NOW, write=False)[0]["sections"] for c in s["cells"]
                             if c["id"] == "protect-nightly-full-run")
    assert cell(tmp_path)["status"] == ws.UNKNOWN and cell(tmp_path)["degraded"]
    other = tmp_path / "second"
    other.mkdir()
    ws.probe_nightly(str(other), real_grid(), str(tmp_path / "nope.log"), now=NOW)
    assert cell(other)["status"] == ws.UNKNOWN


# ---------------------------------------------------------------- the page

def test_page_shows_headline_every_status_and_escapes_what_a_run_file_says(tmp_path):
    gp, grid = make_grid(tmp_path)
    record(tmp_path, grid, "a-one", "pass")
    record(tmp_path, grid, "a-two", "fail", reason="<script>alert(1)</script> & more")
    record(tmp_path, grid, "m-r1-x", "closed_by_design")
    path = record(tmp_path, grid, "m-r1-y", "pass", ago=3)
    open(path, "w").write("{broken")
    data, _, page = run(tmp_path, gp)
    assert 'aria-label="1 / 6 cells passed' in page and ">1 / 6<" in page
    for status in ws.STATUSES:
        assert "ws-s-%s" % ws.SLUG[status] in page
    assert "<script>alert(1)" not in page and "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    assert page.count("</script>") == 2                   # the data blob and the filter, nothing injected
    assert page.startswith("<title>Walk Scoreboard</title>") and "<!doctype" not in page.lower()
    assert "Built Nov 23, 12:00 PM PST" in page


def test_every_row_links_its_proof(tmp_path):
    data, _, page = ws.build(root=str(tmp_path), now=NOW, write=False)
    cells = [c for s in data["sections"] for c in s["cells"]]
    assert all(c["proof"]["url"].startswith("https://github.com/NOVAHGREYWOLF/leadfuel-core/blob/main/") for c in cells)
    assert page.count('target="_blank" rel="noopener"') >= 108 - 12      # shared wording rows still link


def test_ref_flag_points_proof_links_at_a_branch(tmp_path):
    data, _, _ = ws.build(root=str(tmp_path), now=NOW, write=False, ref="watch/p16-1-walk-scoreboard")
    assert "/blob/watch/p16-1-walk-scoreboard/" in data["sections"][0]["cells"][0]["proof"]["url"]


@pytest.mark.parametrize("when,local_hour,abbr", [
    (dt.datetime(2026, 11, 23, 22, 17, tzinfo=dt.timezone.utc), 14, "PST"),
    (dt.datetime(2026, 7, 1, 19, 0, tzinfo=dt.timezone.utc), 12, "PDT"),
    (dt.datetime(2026, 3, 8, 9, 59, 59, tzinfo=dt.timezone.utc), 1, "PST"),     # one second before 02:00 PST
    (dt.datetime(2026, 3, 8, 10, 0, 0, tzinfo=dt.timezone.utc), 3, "PDT"),
    (dt.datetime(2026, 11, 1, 8, 59, 59, tzinfo=dt.timezone.utc), 1, "PDT"),
    (dt.datetime(2026, 11, 1, 9, 0, 0, tzinfo=dt.timezone.utc), 1, "PST"),
])
def test_pacific_conversion_follows_the_us_rule(when, local_hour, abbr):
    local, got = ws.pacific(when)
    assert (local.hour, got) == (local_hour, abbr)


# ---------------------------------------------------------------- the committed files

def test_committed_outputs_are_what_build_makes_from_the_committed_inputs():
    """A hand edit of walk_scoreboard.json or .html, or a run file added without a rebuild, fails here."""
    assert ws.main(["build", "--check"]) == 0


def test_committed_runs_are_all_believed_and_no_pass_lacks_evidence():
    data = json.load(open(os.path.join(WALK, "walk_scoreboard.json"), encoding="utf-8"))
    assert data["source"]["problems"] == []
    for s in data["sections"]:
        for c in s["cells"]:
            assert not c["degraded"], c["id"]
            if c["status"] != ws.NOT_TESTED:
                assert c["run"] and c["evidence"], c["id"]
    n_runs = len([f for f in os.listdir(os.path.join(WALK, "runs")) if f.endswith(".json")])
    assert data["source"]["run_files_read"] == n_runs


def test_committed_files_are_safe_for_a_public_repo():
    bad = []
    for base, _, files in os.walk(WALK):
        for f in files:
            text = open(os.path.join(base, f), encoding="utf-8").read()
            for why in ws.private_hits(text):
                bad.append("%s: %s" % (f, why))
    assert not bad, bad


def test_retired_arm_names_do_not_appear_in_new_files():
    retired = re.compile(r"novahub|novahawk|novahound|novaherald|smarticp|novahunt|\bicp\b", re.I)
    paths = [_PATH] + [os.path.join(b, f) for b, _, fs in os.walk(WALK) for f in fs]
    hits = [p for p in paths if retired.search(open(p, encoding="utf-8").read())]
    assert not hits, hits


# ---------------------------------------------------------------- command line

def test_build_command_writes_both_files_and_reports_the_headline(tmp_path, capsys):
    assert ws.main(["build", "--out-dir", str(tmp_path), "--now", "2026-11-23T22:30:00Z"]) == 0
    assert (tmp_path / "walk_scoreboard.json").is_file() and (tmp_path / "walk_scoreboard.html").is_file()
    assert "cells passed / cells not closed by design" in capsys.readouterr().out
    assert ws.main(["build", "--out-dir", str(tmp_path), "--now", "yesterday"]) == 2


def test_build_writes_nothing_when_the_controls_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(ws, "run_controls", lambda: (False, ["broken"]))
    assert ws.main(["build", "--out-dir", str(tmp_path)]) == 2
    assert os.listdir(str(tmp_path)) == []


def test_selftest_command_passes():
    assert ws.main(["selftest"]) == 0
