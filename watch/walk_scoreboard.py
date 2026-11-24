#!/usr/bin/env python3
"""WATCH p16-1: the walk scoreboard. Every line of the root goal as not tested, pass, fail,
unknown or closed by design, fed by run files, drawn as one self-contained page.

THE RULE THIS FILE EXISTS TO KEEP: a cell changes only when a run file exists.
  * The grid (watch/walk/walk_grid.json) says WHAT is on the scoreboard. It never says how a cell
    is doing. Every cell starts `not tested`.
  * A run file (watch/walk/runs/<cell>__<UTC time>.json) is the only thing that moves a cell. It
    names the cell, the result, who ran it, and at least one evidence file kept in
    watch/walk/evidence/ with its sha256. The newest run file for a cell decides.
  * A check that cannot see its subject says `unknown`, never a result. So does a newest run file
    that is malformed, future dated or points at evidence that is missing or changed, and so does
    a pass or fail older than the cell's max_age_hours. None of these falls back to an older pass.
  * `closed by design` lowers the denominator (cells passed / cells not closed by design), so it is
    accepted only with the owner's own decision named in the run file and an evidence file.
  * Every run of `build` first answers built-in samples whose answers are known. If any is wrong
    the build stops and writes nothing.

COMMANDS (stdlib only, run by path; nothing leaves the machine, no network, no secrets read):
  python watch/walk_scoreboard.py build [--now ISO] [--ref main] [--out-dir DIR] [--check]
      Reads the grid and the run files, writes walk_scoreboard.json (the data) and
      walk_scoreboard.html (the page). --check rebuilds in memory at the committed generated_at
      and exits 1 if either committed file differs: the outputs may not be edited by hand.
  python watch/walk_scoreboard.py record --cell ID --result pass|fail|unknown|closed_by_design
        --by TEXT --how TEXT --evidence FILE [--evidence FILE ...] [--reason TEXT]
        [--decision-by owner --decision-source TEXT] [--subject-at ISO]
      Copies the evidence into watch/walk/evidence/ and writes one run file. The repo is PUBLIC:
      evidence that holds a home path, an IP address, an email address or a key-shaped string is
      refused.
  python watch/walk_scoreboard.py probe off-machine|nightly-full-run [--log PATH]
      Runs WATCH's own reader once and records what it said. It is a read of local files only.
  python watch/walk_scoreboard.py selftest
      Runs the built-in samples and prints each answer.

Times are shown in Pacific on the page; every machine field is UTC.
"""
import argparse
import datetime as dt
import hashlib
import html
import importlib.util
import json
import os
import re
import sys
import tempfile
import urllib.parse

SCHEMA_GRID = "watch.walk_grid/1"
SCHEMA_RUN = "watch.walk_run/1"
SCHEMA_OUT = "watch.walk_scoreboard/1"

NOT_TESTED, PASS, FAIL, UNKNOWN, CLOSED = "not tested", "pass", "fail", "unknown", "closed by design"
STATUSES = (NOT_TESTED, PASS, FAIL, UNKNOWN, CLOSED)
SLUG = {NOT_TESTED: "not-tested", PASS: "pass", FAIL: "fail", UNKNOWN: "unknown", CLOSED: "closed"}
GLYPH = {NOT_TESTED: "\u25cb", PASS: "\u2713", FAIL: "\u2715", UNKNOWN: "?", CLOSED: "\u25a0"}
RESULT_TO_STATUS = {"pass": PASS, "fail": FAIL, "unknown": UNKNOWN, "closed_by_design": CLOSED}

FUTURE_SLACK = dt.timedelta(minutes=10)
MAX_EVIDENCE_BYTES = 1024 * 1024
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
GRID_PATH = os.path.join(HERE, "walk", "walk_grid.json")
OUT_JSON, OUT_HTML = "walk_scoreboard.json", "walk_scoreboard.html"
NIGHTLY_LOG_DEFAULT = r"F:\Claude Sessions\handoff\nightly-full-run.log"

TS_FMT = "%Y-%m-%dT%H:%M:%SZ"
TS_RX = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
RUN_NAME_RX = re.compile(r"^(?P<cell>[a-z0-9][a-z0-9-]*)__(?P<ts>\d{8}T\d{6}Z)\.json$")
SHA_RX = re.compile(r"^[0-9a-f]{64}$")
VERDICT_RX = re.compile(r"^(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z) (PASS|FAIL|UNKNOWN|SKIPPED-BUSY)\b")

# The repo is public. Nothing that matches one of these may be written into evidence.
PRIVATE_PATTERNS = (
    (re.compile(r"[A-Za-z]:\\Users\\"), "a Windows user path"),
    (re.compile(r"(?:/home|/Users)/[A-Za-z0-9_.-]+/"), "a home folder path"),
    (re.compile(r"\b\d{1,3}(?:\.\d{1,3}){3}\b"), "an IP address"),
    (re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"), "an email address"),
    (re.compile(r"\b(?:sk|pk|rk)_(?:live|test)_[A-Za-z0-9]{8,}|\bsk-[A-Za-z0-9_-]{20,}|\bgh[pousr]_[A-Za-z0-9]{20,}"
                r"|\bAKIA[0-9A-Z]{16}\b|\bxox[abp]-[A-Za-z0-9-]{10,}"), "a key-shaped string"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "a private key"),
)


class ScoreboardError(Exception):
    """Something the caller must fix; the message says what."""


# ---------------------------------------------------------------- time

def parse_ts(s):
    if not isinstance(s, str) or not TS_RX.match(s):
        return None
    try:
        return dt.datetime.strptime(s, TS_FMT).replace(tzinfo=dt.timezone.utc)
    except ValueError:
        return None


def iso(t):
    return t.astimezone(dt.timezone.utc).strftime(TS_FMT)


def compact(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _nth_sunday(year, month, n):
    d = dt.date(year, month, 1)
    return d + dt.timedelta(days=(6 - d.weekday()) % 7 + 7 * (n - 1))


def pacific(t):
    """UTC datetime -> (naive Pacific datetime, 'PST'|'PDT') by the US rule since 2007. No tzdata needed."""
    t = t.astimezone(dt.timezone.utc)
    start = dt.datetime.combine(_nth_sunday(t.year, 3, 2), dt.time(10), tzinfo=dt.timezone.utc)   # 02:00 PST
    end = dt.datetime.combine(_nth_sunday(t.year, 11, 1), dt.time(9), tzinfo=dt.timezone.utc)     # 02:00 PDT
    if start <= t < end:
        return (t - dt.timedelta(hours=7)).replace(tzinfo=None), "PDT"
    return (t - dt.timedelta(hours=8)).replace(tzinfo=None), "PST"


def fmt_pt(t):
    if t is None:
        return "unknown"
    local, abbr = pacific(t)
    h = local.hour % 12 or 12
    return "%s %d, %d:%02d %s %s" % (local.strftime("%b"), local.day, h, local.minute, "AM" if local.hour < 12 else "PM", abbr)


def utc_now():
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0)


# ---------------------------------------------------------------- files

def sha256_bytes(b):
    return hashlib.sha256(b).hexdigest()


def read_json(path):
    with open(path, "rb") as f:
        return json.loads(f.read().decode("utf-8"))


def write_text(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def private_hits(text):
    return [why for rx, why in PRIVATE_PATTERNS if rx.search(text)]


def blob_url(link, ref, path):
    return "https://github.com/%s/blob/%s/%s" % (link["repo"], urllib.parse.quote(ref, safe="/"), urllib.parse.quote(path, safe="/"))


# ---------------------------------------------------------------- the grid

def load_grid(path=GRID_PATH):
    g = read_json(path)
    if g.get("schema") != SCHEMA_GRID:
        raise ScoreboardError("grid has an unrecognised schema")
    sections, seen = [], set()
    for s in g["sections"]:
        sec = {"id": s["id"], "title": s["title"], "blurb": s.get("blurb", ""), "kind": s["kind"], "cells": [], "columns": [], "rows": [],
               "row_label": s.get("row_label", "")}
        if s["kind"] == "list":
            for c in s["cells"]:
                sec["cells"].append(dict(c, section=s["id"]))
        elif s["kind"] == "matrix":
            sec["columns"] = s["columns"]
            sec["rows"] = s["rows"]
            for r in s["rows"]:
                for col in s["columns"]:
                    sec["cells"].append({
                        "id": "%s-%s-%s" % (s["id"], r["id"], col["id"]), "section": s["id"],
                        "label": "%s: %s" % (r["label"], col["label"]), "needs": col["needs"],
                        "claim": r.get("claim", ""), "row": r["id"], "col": col["id"],
                        "max_age_hours": col.get("max_age_hours")})
        else:
            raise ScoreboardError("section %s has an unknown kind" % s["id"])
        for c in sec["cells"]:
            if not re.match(r"^[a-z0-9][a-z0-9-]*$", c["id"]) or c["id"] in seen:
                raise ScoreboardError("cell id %r is malformed or repeated" % c["id"])
            seen.add(c["id"])
        sections.append(sec)
    g["sections"] = sections
    return g


# ---------------------------------------------------------------- run files

def load_runs(runs_dir):
    """-> ({cell: [(ts, filename, record_or_None, [read problems])]} newest last, [global problems])."""
    by_cell, problems = {}, []
    if not os.path.isdir(runs_dir):
        return by_cell, problems
    for name in sorted(os.listdir(runs_dir)):
        if name.startswith("."):
            continue
        m = RUN_NAME_RX.match(name)
        if not m:
            problems.append("runs folder: %s is not named <cell>__<UTC time>.json and is ignored" % name)
            continue
        rec, errs = None, []
        try:
            rec = read_json(os.path.join(runs_dir, name))
            if not isinstance(rec, dict):
                rec, errs = None, ["the file is not a JSON object"]
        except (OSError, ValueError) as e:
            errs = ["the file cannot be read (%s)" % e.__class__.__name__]
        by_cell.setdefault(m.group("cell"), []).append((m.group("ts"), name, rec, errs))
    for runs in by_cell.values():
        runs.sort(key=lambda r: (r[0], r[1]))
    return by_cell, problems


def _evidence_problems(root, evidence_dir, ev):
    out = []
    if not isinstance(ev, list) or not ev:
        return ["no evidence file is named"]
    if len(ev) > 10:
        return ["more than 10 evidence files"]
    base = os.path.realpath(os.path.join(root, *evidence_dir.split("/")))
    for item in ev:
        path, sha = (item.get("path"), item.get("sha256")) if isinstance(item, dict) else (None, None)
        if not isinstance(path, str) or not path.startswith(evidence_dir + "/") or ".." in path.split("/") or "\\" in path:
            out.append("evidence path %r is not inside %s" % (path, evidence_dir))
            continue
        if not isinstance(sha, str) or not SHA_RX.match(sha):
            out.append("evidence %s has no sha256" % path)
            continue
        full = os.path.realpath(os.path.join(root, *path.split("/")))
        try:
            inside = os.path.commonpath([full, base]) == base
        except ValueError:
            inside = False
        if not inside or not os.path.isfile(full):
            out.append("evidence file %s cannot be seen" % path)
            continue
        try:
            with open(full, "rb") as f:
                got = sha256_bytes(f.read())
        except OSError:
            out.append("evidence file %s cannot be read" % path)
            continue
        if got != sha:
            out.append("evidence file %s has changed since the run (sha256 differs)" % path)
    return out


def check_run(rec, cell_id, ts_name, now, root, evidence_dir):
    """Every reason this run file cannot be believed. Empty list = it can."""
    p = []
    if rec.get("schema") != SCHEMA_RUN:
        p.append("schema is not %s" % SCHEMA_RUN)
    if rec.get("cell") != cell_id:
        p.append("cell inside the file does not match its name")
    ran = parse_ts(rec.get("ran_at"))
    if ran is None:
        p.append("ran_at is not a UTC time like 2026-11-23T20:00:00Z")
    elif compact(ran) != ts_name:
        p.append("ran_at does not match the file name")
    elif ran > now + FUTURE_SLACK:
        p.append("ran_at is in the future")
    result = rec.get("result")
    if result not in RESULT_TO_STATUS:
        p.append("result must be pass, fail, unknown or closed_by_design")
    for key, limit in (("ran_by", 200), ("how", 400)):
        v = rec.get(key)
        if not isinstance(v, str) or not v.strip() or len(v) > limit:
            p.append("%s is missing or longer than %d characters" % (key, limit))
    reason = rec.get("reason")
    if reason is not None and (not isinstance(reason, str) or len(reason) > 600):
        p.append("reason is longer than 600 characters")
    if result in ("fail", "unknown", "closed_by_design") and not (isinstance(reason, str) and reason.strip()):
        p.append("a %s result needs a reason" % result)
    if rec.get("subject_at") is not None:
        subj = parse_ts(rec.get("subject_at"))
        if subj is None:
            p.append("subject_at is not a UTC time")
        elif subj > now + FUTURE_SLACK:
            p.append("subject_at is in the future")
    if result == "closed_by_design":
        d = rec.get("decision")
        if not (isinstance(d, dict) and d.get("by") == "owner" and isinstance(d.get("source"), str) and d["source"].strip()):
            p.append("closed by design needs decision.by = owner and decision.source naming where he decided it")
    p.extend(_evidence_problems(root, evidence_dir, rec.get("evidence")))
    return p


def resolve_cell(cell, runs, now, root, evidence_dir):
    """The status of one cell and why. `runs` is the cell's run list (newest last) or []."""
    out = {"status": NOT_TESTED, "reason": "no run file exists for this cell", "run": None, "evidence": [], "runs_seen": len(runs or []),
           "degraded": False}
    if not runs:
        return out
    ts_name, fname, rec, read_errs = runs[-1]
    out["run"] = {"file": fname}
    problems = read_errs or check_run(rec, cell["id"], ts_name, now, root, evidence_dir)
    if rec is not None:
        out["run"].update(ran_at=rec.get("ran_at"), ran_by=rec.get("ran_by"), how=rec.get("how"),
                          result=rec.get("result"), subject_at=rec.get("subject_at"), decision=rec.get("decision"))
        out["evidence"] = [e.get("path") for e in (rec.get("evidence") or []) if isinstance(e, dict) and isinstance(e.get("path"), str)]
    if problems:
        out.update(status=UNKNOWN, degraded=True, reason="the newest run file (%s) cannot be believed: %s" % (fname, "; ".join(problems)))
        return out
    status = RESULT_TO_STATUS[rec["result"]]
    out.update(status=status, reason=(rec.get("reason") or "").strip() or ("the run file says %s" % rec["result"]))
    limit = cell.get("max_age_hours")
    if limit and status in (PASS, FAIL):
        when = parse_ts(rec.get("subject_at")) or parse_ts(rec["ran_at"])
        age = (now - when).total_seconds() / 3600
        if age > limit:
            out.update(status=UNKNOWN, degraded=True,
                       reason="the evidence is %.1f h old and this cell's limit is %g h; the last run said %s" % (age, limit, status))
    return out


def _acceptable(spec_needs):
    return (PASS, FAIL, CLOSED) if spec_needs == "result" else (PASS, CLOSED)


def build_data(grid, runs_by_cell, run_problems, now, root, ref):
    link = grid["link"]
    evidence_dir = link["evidence_dir"]
    sections, all_cells, counts = [], {}, {s: 0 for s in STATUSES}
    for sec in grid["sections"]:
        cells = []
        for c in sec["cells"]:
            r = resolve_cell(c, runs_by_cell.get(c["id"], []), now, root, evidence_dir)
            if r["run"] and r["evidence"]:
                proof = {"kind": "evidence", "label": r["evidence"][0].rsplit("/", 1)[-1], "url": blob_url(link, ref, r["evidence"][0])}
            elif r["run"]:
                proof = {"kind": "run", "label": r["run"]["file"], "url": blob_url(link, ref, link["runs_dir"] + "/" + r["run"]["file"])}
            else:
                proof = {"kind": "needed", "label": "proof needed", "url": blob_url(link, ref, link["grid_file"])}
            cell = {k: c[k] for k in ("id", "label") if k in c}
            if "row" not in c:          # a matrix cell's proof text lives once on its column
                cell["needs"] = c["needs"]
            for k in ("text", "claim", "row", "col", "max_age_hours"):
                if c.get(k):
                    cell[k] = c[k]
            cell.update(status=r["status"], status_reason=r["reason"], run=r["run"], evidence=r["evidence"],
                        runs_seen=r["runs_seen"], proof=proof, warnings=[], degraded=r["degraded"])
            if c.get("rolls_up_from"):
                cell["_rolls"] = c["rolls_up_from"]
            counts[r["status"]] += 1
            cells.append(cell)
            all_cells[c["id"]] = cell
        sections.append({"id": sec["id"], "title": sec["title"], "blurb": sec["blurb"], "kind": sec["kind"], "row_label": sec["row_label"],
                         "columns": sec["columns"], "rows": sec["rows"], "cells": cells})
    # A line marked pass while the cells it rests on say otherwise gets a warning. Its status does not change.
    by_section = {s["id"]: s["cells"] for s in sections}
    for cell in all_cells.values():
        spec = cell.pop("_rolls", None)
        if not spec or cell["status"] != PASS:
            continue
        linked = by_section[spec["section"]] if "section" in spec else [all_cells[i] for i in spec["cells"]]
        bad = [x for x in linked if x["status"] not in _acceptable(spec["needs"])]
        if bad:
            cell["warnings"].append("Marked pass, but %d of %d linked cells are not %s." % (
                len(bad), len(linked), "pass or closed by design" if spec["needs"] == "pass" else "settled (pass, fail or closed by design)"))
    for sec in sections:
        c = {s: 0 for s in STATUSES}
        for cell in sec["cells"]:
            c[cell["status"]] += 1
        sec["counts"] = c
        sec["passed"], sec["not_closed"] = c[PASS], len(sec["cells"]) - c[CLOSED]
    total = sum(counts.values())
    headline = {"passed": counts[PASS], "not_closed_by_design": total - counts[CLOSED], "total": total,
                "closed_by_design": counts[CLOSED]}
    headline["text"] = "%d / %d" % (headline["passed"], headline["not_closed_by_design"])
    runs_read = sum(len(v) for v in runs_by_cell.values())
    problems = list(run_problems)
    known = set(all_cells)
    for cid in sorted(runs_by_cell):
        if cid not in known:
            problems.append("runs folder: %d run file(s) name the cell %r, which is not in the grid; they change nothing" % (len(runs_by_cell[cid]), cid))
    return {"schema": SCHEMA_OUT, "generated_at": iso(now), "ref": ref,
            "source": {"grid": link["grid_file"], "runs_dir": link["runs_dir"], "run_files_read": runs_read, "problems": problems},
            "headline": headline, "counts": counts, "sections": sections, "notes": grid.get("notes", []),
            "built_from": grid.get("built_from", []), "link": link}


# ---------------------------------------------------------------- page

CSS = """
:root{
  --ws-bg:#f1f4f6; --ws-surface:#ffffff; --ws-ink:#15202a; --ws-muted:#52606b; --ws-line:#d3dbe1; --ws-line-soft:#e4eaee; --ws-accent:#0b6a8a;
  --ws-nt-fg:#46545e; --ws-nt-bg:#e6ebef; --ws-nt-dot:#9aa8b1;
  --ws-pass-fg:#1b6a2e; --ws-pass-bg:#dcf0df; --ws-pass-dot:#2f9e4a;
  --ws-fail-fg:#a2261c; --ws-fail-bg:#fbe3e0; --ws-fail-dot:#d33a2c;
  --ws-unk-fg:#855000; --ws-unk-bg:#fdebc9; --ws-unk-dot:#d98a12;
  --ws-clo-fg:#573d90; --ws-clo-bg:#eae3f6; --ws-clo-dot:#7b5cc7;
  --ws-font:system-ui,-apple-system,"Segoe UI",Roboto,"Helvetica Neue",Arial,sans-serif;
  --ws-mono:ui-monospace,"SFMono-Regular",Consolas,"Liberation Mono",monospace;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){
    --ws-bg:#0f161b; --ws-surface:#172028; --ws-ink:#e4ecf0; --ws-muted:#9db0bb; --ws-line:#2b3944; --ws-line-soft:#212d36; --ws-accent:#5bbbdb;
    --ws-nt-fg:#aebdc6; --ws-nt-bg:#25313a; --ws-nt-dot:#5f6f7a;
    --ws-pass-fg:#88d69c; --ws-pass-bg:#1a3423; --ws-pass-dot:#4cc06a;
    --ws-fail-fg:#ff968c; --ws-fail-bg:#3a1c1a; --ws-fail-dot:#ff6f62;
    --ws-unk-fg:#f3bb62; --ws-unk-bg:#37290f; --ws-unk-dot:#f0a93a;
    --ws-clo-fg:#c2acf2; --ws-clo-bg:#2b2243; --ws-clo-dot:#a98ae8;
    color-scheme:dark;
  }
}
:root[data-theme="dark"]{
  --ws-bg:#0f161b; --ws-surface:#172028; --ws-ink:#e4ecf0; --ws-muted:#9db0bb; --ws-line:#2b3944; --ws-line-soft:#212d36; --ws-accent:#5bbbdb;
  --ws-nt-fg:#aebdc6; --ws-nt-bg:#25313a; --ws-nt-dot:#5f6f7a;
  --ws-pass-fg:#88d69c; --ws-pass-bg:#1a3423; --ws-pass-dot:#4cc06a;
  --ws-fail-fg:#ff968c; --ws-fail-bg:#3a1c1a; --ws-fail-dot:#ff6f62;
  --ws-unk-fg:#f3bb62; --ws-unk-bg:#37290f; --ws-unk-dot:#f0a93a;
  --ws-clo-fg:#c2acf2; --ws-clo-bg:#2b2243; --ws-clo-dot:#a98ae8;
  color-scheme:dark;
}
body{background:var(--ws-bg);color:var(--ws-ink);font-family:var(--ws-font);font-size:15px;line-height:1.5}
.ws-wrap{max-width:1040px;margin-inline:auto;padding-block:20px 56px;padding-left:max(16px,env(safe-area-inset-left,0px));padding-right:max(16px,env(safe-area-inset-right,0px))}
.ws-wrap *{box-sizing:border-box}
.ws-wrap h1,.ws-wrap h2,.ws-wrap p,.ws-wrap ul,.ws-wrap dl,.ws-wrap dd{margin:0}
.ws-wrap h1{font-size:28px;line-height:1.15;font-weight:700;letter-spacing:-.01em}
.ws-wrap h2{font-size:18px;line-height:1.25;font-weight:700;text-wrap:balance}
.ws-wrap a{color:var(--ws-accent);overflow-wrap:anywhere}
.ws-wrap a:focus-visible,.ws-wrap button:focus-visible{outline:2px solid var(--ws-accent);outline-offset:2px}
.ws-mono{font-family:var(--ws-mono);font-size:.86em}
.ws-sub{color:var(--ws-muted);max-width:72ch;margin-top:6px}
.ws-top{display:grid;grid-template-columns:minmax(0,auto) minmax(0,1fr);gap:16px 28px;align-items:end;margin-top:18px}
.ws-big{font-size:56px;line-height:1;font-weight:700;font-variant-numeric:tabular-nums;letter-spacing:-.02em}
.ws-cap{color:var(--ws-muted);font-size:13.5px;margin-top:6px;max-width:30ch}
.ws-tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(112px,1fr));gap:8px}
.ws-tile{font:inherit;color:inherit;text-align:left;cursor:pointer;padding:9px 11px;border:1px solid var(--ws-line);border-radius:8px;background:var(--ws-surface);min-width:0}
.ws-tile b{display:block;font-size:24px;line-height:1.1;font-variant-numeric:tabular-nums}
.ws-tile span{font-size:12.5px;color:var(--ws-muted)}
.ws-tile i{font-style:normal;font-weight:700}
.ws-t-not-tested i{color:var(--ws-nt-dot)}.ws-t-pass i{color:var(--ws-pass-dot)}.ws-t-fail i{color:var(--ws-fail-dot)}.ws-t-unknown i{color:var(--ws-unk-dot)}.ws-t-closed i{color:var(--ws-clo-dot)}
.ws-tile[aria-pressed="true"]{border-color:var(--ws-accent);box-shadow:0 0 0 1px var(--ws-accent)}
.ws-bar{display:flex;height:10px;border-radius:5px;overflow:hidden;background:var(--ws-line-soft);margin-top:14px}
.ws-bar i{display:block;height:100%}
.ws-fresh{margin-top:12px;font-size:13px;color:var(--ws-muted)}
.ws-banner{margin-top:12px;padding:10px 12px;border-radius:8px;background:var(--ws-unk-bg);color:var(--ws-unk-fg);font-size:13.5px}
.ws-banner p+p{margin-top:4px}
.ws-nav{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:18px;font-size:14px}
.ws-sec{margin-top:26px;min-width:0}
.ws-sech{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:2px 16px}
.ws-count{font-size:13px;color:var(--ws-muted);font-variant-numeric:tabular-nums}
.ws-blurb{color:var(--ws-muted);font-size:14px;margin-top:3px;max-width:75ch}
.ws-defs{margin-top:8px;font-size:13px;color:var(--ws-muted);display:grid;gap:3px;max-width:80ch}
.ws-defs dt{display:inline;font-weight:600;color:var(--ws-ink)}
.ws-defs dd{display:inline}
.ws-list{list-style:none;margin:10px 0 0;padding:0;border:1px solid var(--ws-line);border-radius:10px;background:var(--ws-surface);overflow:hidden}
.ws-item{display:grid;grid-template-columns:9.5rem minmax(0,1fr);gap:4px 16px;padding:12px 14px;border-top:1px solid var(--ws-line-soft)}
.ws-item:first-child{border-top:0}
.ws-lab{font-weight:600;overflow-wrap:anywhere}
.ws-text{margin-top:3px;overflow-wrap:anywhere;max-width:80ch}
.ws-meta{margin-top:6px;font-size:13px;color:var(--ws-muted);display:grid;gap:2px;min-width:0;overflow-wrap:anywhere}
.ws-warn{color:var(--ws-unk-fg);font-weight:600}
.ws-chip{display:inline-flex;align-items:center;gap:6px;padding:2px 10px;border-radius:999px;font-size:12.5px;font-weight:600;white-space:nowrap}
.ws-chip i{font-style:normal}
.ws-s-not-tested{background:var(--ws-nt-bg);color:var(--ws-nt-fg)}
.ws-s-pass{background:var(--ws-pass-bg);color:var(--ws-pass-fg)}
.ws-s-fail{background:var(--ws-fail-bg);color:var(--ws-fail-fg)}
.ws-s-unknown{background:var(--ws-unk-bg);color:var(--ws-unk-fg);outline:1px dashed var(--ws-unk-fg);outline-offset:-1px}
.ws-s-closed{background:var(--ws-clo-bg);color:var(--ws-clo-fg)}
.ws-when{display:block;margin-top:5px;font-size:12px;color:var(--ws-muted)}
.ws-scroll{margin-top:10px;overflow-x:auto;border:1px solid var(--ws-line);border-radius:10px;background:var(--ws-surface)}
.ws-tab{width:100%;border-collapse:collapse;font-size:14px}
.ws-tab th,.ws-tab td{padding:9px 12px;text-align:left;vertical-align:top;border-top:1px solid var(--ws-line-soft)}
.ws-tab thead th{border-top:0;font-size:12.5px;color:var(--ws-muted);font-weight:600;white-space:nowrap}
.ws-tab th[scope=row]{font-weight:600;min-width:11rem}
.ws-tab .ws-claim{display:block;font-weight:400;font-size:12px;color:var(--ws-muted)}
.ws-tab td{min-width:12rem}
.ws-tab td a{font-size:12.5px}
.ws-foot{margin-top:30px;font-size:12.5px;color:var(--ws-muted);max-width:80ch;display:grid;gap:6px}
@media (max-width:620px){
  .ws-top{grid-template-columns:minmax(0,1fr)}
  .ws-item{grid-template-columns:minmax(0,1fr)}
  .ws-big{font-size:46px}
}
"""

JS = """
(function(){
  var root=document.getElementById('walk-scoreboard');
  if(!root){return;}
  var tiles=root.querySelectorAll('[data-filter]');
  var current='all';
  function apply(f){
    current=f;
    root.querySelectorAll('[data-statuses]').forEach(function(el){
      var s=el.getAttribute('data-statuses').split(' ');
      el.hidden=!(f==='all'||s.indexOf(f)>=0);
    });
    tiles.forEach(function(t){t.setAttribute('aria-pressed',String(t.getAttribute('data-filter')===f));});
  }
  tiles.forEach(function(t){
    t.addEventListener('click',function(){var f=t.getAttribute('data-filter');apply(current===f?'all':f);});
  });
})();
"""


def _e(s):
    return html.escape("" if s is None else str(s), quote=True)


def _chip(cell):
    s = cell["status"]
    return '<span class="ws-chip ws-s-%s"><i aria-hidden="true">%s</i>%s</span>' % (SLUG[s], GLYPH[s], _e(s))


def _when(cell):
    run = cell["run"]
    if not run or not run.get("ran_at"):
        return ""
    ran = parse_ts(run["ran_at"])
    text = "checked %s" % fmt_pt(ran)
    subj = parse_ts(run.get("subject_at"))
    if subj:
        text += " (evidence from %s)" % fmt_pt(subj)
    return '<time class="ws-when" datetime="%s">%s</time>' % (_e(run["ran_at"]), _e(text))


def _proof(cell, label=None):
    p = cell["proof"]
    return '<a href="%s" target="_blank" rel="noopener">%s</a>' % (_e(p["url"]), _e(label or p["label"]))


def _meta_lines(cell, shared_needs=None):
    lines = []
    if cell["status"] == NOT_TESTED:
        if shared_needs:
            lines.append("Proof: %s" % _proof(cell))
        else:
            lines.append("Proof needed: %s (%s)" % (_e(cell["needs"]), _proof(cell, "where this is defined")))
    else:
        lines.append("Why: %s" % _e(cell["status_reason"]))
        run = cell["run"] or {}
        if run.get("ran_by"):
            lines.append("Run by: %s" % _e(run["ran_by"]))
        if run.get("decision"):
            lines.append("Closed by design on: %s" % _e((run["decision"] or {}).get("source")))
        lines.append("Proof: %s" % _proof(cell))
        if cell["runs_seen"] > 1:
            lines.append("%d run files for this cell; the newest decides." % cell["runs_seen"])
    return lines


def _shared_needs(sec):
    needs = {c["needs"] for c in sec["cells"] if "needs" in c}
    return needs.pop() if len(needs) == 1 and len(sec["cells"]) > 1 else None


def _render_list(sec):
    shared = _shared_needs(sec)
    out = ['<p class="ws-defs">Proof needed for every row here: %s</p>' % _e(shared)] if shared else []
    out.append('<ul class="ws-list">')
    for c in sec["cells"]:
        meta = ["<span>%s</span>" % ln for ln in _meta_lines(c, shared)]
        meta += ['<span class="ws-warn">%s</span>' % _e(w) for w in c["warnings"]]
        if c.get("claim"):
            meta.append("<span>Source: %s</span>" % _e(c["claim"]))
        out.append(
            '<li class="ws-item" id="ws-%s" data-statuses="%s"><div>%s%s</div><div><div class="ws-lab">%s</div>%s<div class="ws-meta">%s</div></div></li>'
            % (_e(c["id"]), SLUG[c["status"]], _chip(c), _when(c), _e(c["label"]),
               ('<p class="ws-text">%s</p>' % _e(c["text"])) if c.get("text") else "", "".join(meta)))
    out.append("</ul>")
    return "".join(out)


def _render_matrix(sec):
    cols = sec["columns"]
    by = {(c["row"], c["col"]): c for c in sec["cells"]}
    out = ['<dl class="ws-defs">']
    for col in cols:
        out.append("<div><dt>%s:</dt> <dd>%s</dd></div>" % (_e(col["label"]), _e(col["needs"])))
    out.append('</dl><div class="ws-scroll"><table class="ws-tab"><thead><tr><th scope="col">%s</th>' % _e(sec.get("row_label") or "Row"))
    out.append("".join('<th scope="col">%s</th>' % _e(col["label"]) for col in cols))
    out.append("</tr></thead><tbody>")
    for row in sec["rows"]:
        cells = [by[(row["id"], col["id"])] for col in cols]
        stats = " ".join(sorted({SLUG[c["status"]] for c in cells}))
        out.append('<tr id="ws-row-%s-%s" data-statuses="%s"><th scope="row">%s%s</th>' % (
            _e(sec["id"]), _e(row["id"]), stats, _e(row["label"]),
            ('<span class="ws-claim">%s</span>' % _e(row["claim"])) if row.get("claim") else ""))
        for c in cells:
            warn = "".join('<span class="ws-warn">%s</span> ' % _e(w) for w in c["warnings"])
            why = "" if c["status"] == NOT_TESTED else ' title="%s"' % _e(c["status_reason"])
            out.append('<td id="ws-%s"%s>%s%s<span class="ws-when">%s%s</span></td>' % (
                _e(c["id"]), why, _chip(c), _when(c), warn, _proof(c)))
        out.append("</tr>")
    out.append("</tbody></table></div>")
    return "".join(out)


def render_html(data):
    h, counts = data["headline"], data["counts"]
    total = max(h["total"], 1)
    gen = parse_ts(data["generated_at"])
    tiles = ['<button type="button" class="ws-tile ws-t-%s" data-filter="%s" aria-pressed="false"><b>%d</b><span><i aria-hidden="true">%s</i> %s</span></button>'
             % (SLUG[s], SLUG[s], counts[s], GLYPH[s], _e(s)) for s in STATUSES]
    bar = "".join('<i style="width:%.3f%%;background:var(--ws-%s-dot)" title="%s: %d"></i>' % (
        100.0 * counts[s] / total, {"not-tested": "nt", "pass": "pass", "fail": "fail", "unknown": "unk", "closed": "clo"}[SLUG[s]], _e(s), counts[s])
        for s in STATUSES if counts[s])
    problems = data["source"]["problems"]
    unk_cells = [c["id"] for sec in data["sections"] for c in sec["cells"] if c["degraded"]]
    banner = ""
    if problems or unk_cells:
        lines = ["<p>%s</p>" % _e(p) for p in problems]
        if unk_cells:
            lines.append("<p>%d cell(s) read unknown because their newest run file could not be believed or is older than the cell's limit: %s.</p>"
                         % (len(unk_cells), _e(", ".join(unk_cells[:6]) + (" and more" if len(unk_cells) > 6 else ""))))
        banner = '<div class="ws-banner" role="status">%s</div>' % "".join(lines)
    nav = "".join('<a href="#ws-sec-%s">%s</a>' % (_e(s["id"]), _e(s["title"])) for s in data["sections"])
    secs = []
    for s in data["sections"]:
        body = _render_matrix(s) if s["kind"] == "matrix" else _render_list(s)
        secs.append('<section class="ws-sec" id="ws-sec-%s"><div class="ws-sech"><h2>%s</h2><span class="ws-count">%d passed / %d not closed by design</span></div><p class="ws-blurb">%s</p>%s</section>'
                    % (_e(s["id"]), _e(s["title"]), s["passed"], s["not_closed"], _e(s["blurb"]), body))
    notes = "".join("<p>%s</p>" % _e(n) for n in data["notes"])
    built = "".join("<li>%s</li>" % _e(b) for b in data["built_from"])
    blob = json.dumps(data, ensure_ascii=False, indent=1).replace("<", "\\u003c")
    return (
        '<title>Walk Scoreboard</title>\n<meta name="claude:viewport-fit-sides" content="cover">\n<style>%s</style>\n'
        '<main class="ws-wrap" id="walk-scoreboard">\n'
        '<h1>Walk scoreboard</h1>\n'
        '<p class="ws-sub">Every line of the root goal, NovahOS finished, as not tested, pass, fail, unknown or closed by design. '
        'A cell moves only when a run file exists, and every row links its proof. Until a run exists the link shows what proof is needed.</p>\n'
        '<div class="ws-top"><div><div class="ws-big" aria-label="%s cells passed over cells not closed by design">%s</div>'
        '<p class="ws-cap">cells passed / cells not closed by design</p></div><div class="ws-tiles">%s</div></div>\n'
        '<div class="ws-bar" role="img" aria-label="Share of cells by status">%s</div>\n'
        '<p class="ws-fresh">Built %s from %s and %d run file(s) in %s. Rebuild with <span class="ws-mono">python watch/walk_scoreboard.py build</span>. '
        'A pass or fail older than its limit reads unknown.</p>\n'
        '%s\n<nav class="ws-nav" aria-label="Sections">%s</nav>\n%s\n'
        '<div class="ws-foot">%s<p>Built from:</p><ul>%s</ul></div>\n</main>\n'
        '<script type="application/json" id="ws-data">%s</script>\n<script>%s</script>\n'
    ) % (CSS, _e(h["text"]), _e(h["text"]), "".join(tiles), bar, _e(fmt_pt(gen)), _e(data["source"]["grid"]),
         data["source"]["run_files_read"], _e(data["source"]["runs_dir"]), banner, nav, "\n".join(secs), notes, built, blob, JS)


# ---------------------------------------------------------------- build / check

def build(grid_path=GRID_PATH, root=REPO, now=None, ref=None, out_dir=None, write=True, runs_dir=None):
    grid = load_grid(grid_path)
    ref = ref or grid["link"]["ref_default"]
    runs_dir = runs_dir or os.path.join(root, *grid["link"]["runs_dir"].split("/"))
    now = now or utc_now()
    runs, problems = load_runs(runs_dir)
    data = build_data(grid, runs, problems, now, root, ref)
    page = render_html(data)
    text = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if write:
        out_dir = out_dir or os.path.join(root, "watch", "walk")
        write_text(os.path.join(out_dir, OUT_JSON), text)
        write_text(os.path.join(out_dir, OUT_HTML), page)
    return data, text, page


# ---------------------------------------------------------------- recording

def _evidence_name(cell_id, ran, basename):
    safe = re.sub(r"[^A-Za-z0-9._-]", "_", basename)[:80] or "evidence"
    return "%s__%s__%s" % (cell_id, compact(ran), safe)


def write_run(root, grid, cell_id, result, by, how, evidence_items, reason=None, decision=None, subject_at=None, ran_at=None, now=None):
    """Write one run file (and its evidence) or raise ScoreboardError. evidence_items = [(basename, bytes)]."""
    now = now or utc_now()
    ran = ran_at or now
    cells = {c["id"]: c for s in grid["sections"] for c in s["cells"]}
    if cell_id not in cells:
        raise ScoreboardError("cell %r is not in the grid" % cell_id)
    if result not in RESULT_TO_STATUS:
        raise ScoreboardError("result must be pass, fail, unknown or closed_by_design")
    link = grid["link"]
    ev_dir = os.path.join(root, *link["evidence_dir"].split("/"))
    runs_dir = os.path.join(root, *link["runs_dir"].split("/"))
    ev, staged = [], []
    for basename, blob in evidence_items:
        if len(blob) > MAX_EVIDENCE_BYTES:
            raise ScoreboardError("evidence %s is larger than 1 MiB" % basename)
        hits = private_hits(blob.decode("utf-8", "replace"))
        if hits:
            raise ScoreboardError("evidence %s holds %s; the repo is public, so remove it and record again" % (basename, ", ".join(hits)))
        name = _evidence_name(cell_id, ran, basename)
        ev.append({"path": "%s/%s" % (link["evidence_dir"], name), "sha256": sha256_bytes(blob)})
        staged.append((os.path.join(ev_dir, name), blob))
    rec = {"schema": SCHEMA_RUN, "cell": cell_id, "result": result, "ran_at": iso(ran), "ran_by": by, "how": how, "evidence": ev}
    if subject_at:
        rec["subject_at"] = iso(subject_at)
    if reason:
        rec["reason"] = reason
    if decision:
        rec["decision"] = decision
    run_path = os.path.join(runs_dir, "%s__%s.json" % (cell_id, compact(ran)))
    if os.path.exists(run_path):
        raise ScoreboardError("%s already exists; run files are never overwritten" % os.path.basename(run_path))
    for path, blob in staged:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(blob)
    problems = check_run(rec, cell_id, compact(ran), now, root, link["evidence_dir"])
    if problems:
        for path, _ in staged:
            os.remove(path)
        raise ScoreboardError("the run file would not be believed: " + "; ".join(problems))
    write_text(run_path, json.dumps(rec, indent=2, ensure_ascii=False) + "\n")
    return run_path


def _load_sibling(name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(HERE, name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def probe_off_machine(root, grid, log=None, now=None):
    """Run WATCH's vault-sync reader once and record its own verdict. The log path is dropped."""
    now = now or utc_now()
    st = _load_sibling("vault_sync_status").read_status(log, now)
    keep = ("schema", "state", "reason", "last_start", "last_end", "exit_code", "age_hours", "targets_verified",
            "runs_seen", "checked_at", "log_present", "controls_ok")
    ev = {k: st.get(k) for k in keep}
    result = {"ok": "pass", "failed": "fail"}.get(st.get("state"), "unknown")
    subject = parse_ts(st.get("last_end")) or parse_ts(st.get("last_start"))
    return write_run(root, grid, "protect-off-machine", result,
                     "WATCH desk, watch/vault_sync_status.py read through walk_scoreboard.py probe",
                     "Ran the reader over the VAULT private sync log. The evidence is the reader's own output with the log path removed.",
                     [("vault_sync_status.json", (json.dumps(ev, indent=2) + "\n").encode("utf-8"))],
                     reason="reader state %s: %s" % (st.get("state"), st.get("reason")), subject_at=subject, now=now)


def probe_nightly(root, grid, log=None, now=None):
    """Record the last verdict line of the nightly full run. PASS/FAIL pass through; anything else is unknown."""
    now = now or utc_now()
    log = log or NIGHTLY_LOG_DEFAULT
    ev, result, subject, reason = {"schema": "watch.walk_probe.nightly_full_run/1"}, "unknown", None, None
    try:
        with open(log, "rb") as f:
            lines = f.read().decode("utf-8", "replace").splitlines()
    except OSError as e:
        lines = None
        ev.update(log_present=False)
        reason = "the nightly log cannot be read (%s)" % e.__class__.__name__
    if lines is not None:
        idx = [i for i, ln in enumerate(lines) if VERDICT_RX.match(ln)]
        ev.update(log_present=True, verdict_lines_in_log=len(idx))
        if not idx:
            reason = "the nightly log holds no verdict line"
        else:
            last = idx[-1]
            m = VERDICT_RX.match(lines[last])
            ev.update(verdict_line=lines[last], lines_after=[ln for ln in lines[last + 1:last + 21] if ln.startswith(" ")])
            subject = parse_ts(m.group(1))
            result = {"PASS": "pass", "FAIL": "fail"}.get(m.group(2), "unknown")
            reason = "last verdict line says %s" % m.group(2)
    return write_run(root, grid, "protect-nightly-full-run", result,
                     "WATCH desk, last verdict line of the nightly full run read through walk_scoreboard.py probe",
                     "Read the last verdict line of the nightly full run log. PASS and FAIL pass through; UNKNOWN and SKIPPED-BUSY read unknown.",
                     [("nightly_full_run_verdict.json", (json.dumps(ev, indent=2) + "\n").encode("utf-8"))],
                     reason=reason, subject_at=subject, now=now)


# ---------------------------------------------------------------- positive controls

def _fixture(tmp, max_age=None):
    link = {"repo": "o/r", "ref_default": "main", "grid_file": "watch/walk/walk_grid.json", "runs_dir": "watch/walk/runs",
            "evidence_dir": "watch/walk/evidence"}
    grid = {"schema": SCHEMA_GRID, "link": link, "sections": [
        {"id": "a", "title": "A", "blurb": "", "kind": "list", "cells": [
            {"id": "a-one", "label": "one", "needs": "n", "max_age_hours": max_age}, {"id": "a-two", "label": "two", "needs": "n"},
            {"id": "a-three", "label": "three", "needs": "n"}]}]}
    gp = os.path.join(tmp, "grid.json")
    write_text(gp, json.dumps(grid))
    return gp, load_grid(gp)


def run_controls():
    """Known samples with known answers, answered by the real code. Returns (ok, [names that went wrong])."""
    now = dt.datetime(2026, 11, 23, 20, 0, 0, tzinfo=dt.timezone.utc)
    bad = []

    def counts(tmp, gp, at=now):
        data, _, _ = build(gp, root=tmp, now=at, write=False)
        return data, {c["id"]: c["status"] for s in data["sections"] for c in s["cells"]}

    with tempfile.TemporaryDirectory() as tmp:
        gp, grid = _fixture(tmp, max_age=24)
        data, st = counts(tmp, gp)
        if set(st.values()) != {NOT_TESTED} or data["headline"]["text"] != "0 / 3":
            bad.append("empty runs must leave every cell not tested")
        evid = [("e.txt", b"proof")]
        write_run(tmp, grid, "a-one", "pass", "ctl", "ctl", evid, now=now, ran_at=now - dt.timedelta(hours=1))
        data, st = counts(tmp, gp)
        if st["a-one"] != PASS or st["a-two"] != NOT_TESTED or data["headline"]["text"] != "1 / 3":
            bad.append("one valid pass must move exactly one cell")
        later = now + dt.timedelta(hours=30)
        _, st = counts(tmp, gp, later)
        if st["a-one"] != UNKNOWN:
            bad.append("a pass older than max_age_hours must read unknown")
        ev_file = os.path.join(tmp, "watch", "walk", "evidence", os.listdir(os.path.join(tmp, "watch", "walk", "evidence"))[0])
        with open(ev_file, "wb") as f:
            f.write(b"tampered")
        _, st = counts(tmp, gp)
        if st["a-one"] != UNKNOWN:
            bad.append("changed evidence must read unknown, not pass")
        os.remove(ev_file)
        _, st = counts(tmp, gp)
        if st["a-one"] != UNKNOWN:
            bad.append("missing evidence must read unknown, not pass")
        try:
            write_run(tmp, grid, "a-two", "closed_by_design", "ctl", "ctl", evid, reason="r", now=now)
            bad.append("closed by design without the owner's decision must be refused")
        except ScoreboardError:
            pass
        write_run(tmp, grid, "a-two", "closed_by_design", "ctl", "ctl", evid, reason="r",
                  decision={"by": "owner", "source": "ctl"}, now=now)
        data, st = counts(tmp, gp)
        if st["a-two"] != CLOSED or data["headline"]["not_closed_by_design"] != 2:
            bad.append("closed by design must leave the denominator")
        write_run(tmp, grid, "a-three", "pass", "ctl", "ctl", evid, now=now)
        _, st = counts(tmp, gp, now - dt.timedelta(hours=2))
        if st["a-three"] != UNKNOWN:
            bad.append("a future dated run must read unknown")
        try:
            write_run(tmp, grid, "a-three", "pass", "ctl", "ctl", evid, now=now, ran_at=now + dt.timedelta(hours=2))
            bad.append("record must refuse a future dated run")
        except ScoreboardError:
            pass
    return not bad, bad


# ---------------------------------------------------------------- CLI

def _cmd_build(a):
    ok, bad = run_controls()
    if not ok:
        print("positive controls failed, nothing written: %s" % bad, file=sys.stderr)
        return 2
    out_dir = a.out_dir or os.path.join(REPO, "watch", "walk")
    if a.check:
        prev = os.path.join(out_dir, OUT_JSON)
        try:
            old = read_json(prev)
            at, old_ref = parse_ts(old["generated_at"]), old.get("ref")
        except (OSError, ValueError, KeyError):
            at, old_ref = None, None
        if at is None:
            print("--check needs a committed %s with a generated_at" % OUT_JSON, file=sys.stderr)
            return 1
        data, text, page = build(now=at, ref=a.ref or old_ref, write=False)
        same = []
        for name, want in ((OUT_JSON, text), (OUT_HTML, page)):
            with open(os.path.join(out_dir, name), "rb") as f:
                got = f.read().decode("utf-8").replace("\r\n", "\n")
            same.append(got == want)
        print("scoreboard files are %s" % ("current" if all(same) else "STALE or hand edited: run build"))
        return 0 if all(same) else 1
    now = parse_ts(a.now) if a.now else None
    if a.now and now is None:
        print("--now must look like 2026-11-23T20:00:00Z", file=sys.stderr)
        return 2
    data, _, _ = build(now=now, ref=a.ref, out_dir=out_dir)
    print("wrote %s and %s in %s: %s cells passed / cells not closed by design" % (OUT_JSON, OUT_HTML, out_dir, data["headline"]["text"]))
    print("  " + ", ".join("%s %d" % (s, data["counts"][s]) for s in STATUSES))
    for p in data["source"]["problems"]:
        print("  PROBLEM: " + p)
    return 0


def _cmd_record(a):
    grid = load_grid()
    items = []
    for p in a.evidence:
        try:
            with open(p, "rb") as f:
                items.append((os.path.basename(p), f.read()))
        except OSError as e:
            print("cannot read evidence %s (%s)" % (p, e.__class__.__name__), file=sys.stderr)
            return 2
    decision = {"by": a.decision_by, "source": a.decision_source} if a.decision_by or a.decision_source else None
    subject = parse_ts(a.subject_at) if a.subject_at else None
    if a.subject_at and subject is None:
        print("--subject-at must look like 2026-11-23T20:00:00Z", file=sys.stderr)
        return 2
    try:
        path = write_run(REPO, grid, a.cell, a.result, a.by, a.how, items, a.reason, decision, subject)
    except ScoreboardError as e:
        print("refused: %s" % e, file=sys.stderr)
        return 2
    print("wrote %s; now run: python watch/walk_scoreboard.py build" % path)
    return 0


def _cmd_probe(a):
    grid = load_grid()
    try:
        fn = probe_off_machine if a.which == "off-machine" else probe_nightly
        path = fn(REPO, grid, a.log)
    except ScoreboardError as e:
        print("refused: %s" % e, file=sys.stderr)
        return 2
    print("wrote %s; now run: python watch/walk_scoreboard.py build" % path)
    return 0


def _cmd_selftest(_a):
    ok, bad = run_controls()
    print("controls: %s" % ("all answered correctly" if ok else "WRONG: %s" % bad))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--now")
    b.add_argument("--ref", default=None, help="git ref the proof links point at (default main; use the branch before merge)")
    b.add_argument("--out-dir")
    b.add_argument("--check", action="store_true")
    b.set_defaults(fn=_cmd_build)
    r = sub.add_parser("record")
    r.add_argument("--cell", required=True)
    r.add_argument("--result", required=True, choices=sorted(RESULT_TO_STATUS))
    r.add_argument("--by", required=True)
    r.add_argument("--how", required=True)
    r.add_argument("--evidence", action="append", required=True)
    r.add_argument("--reason")
    r.add_argument("--decision-by")
    r.add_argument("--decision-source")
    r.add_argument("--subject-at")
    r.set_defaults(fn=_cmd_record)
    p = sub.add_parser("probe")
    p.add_argument("which", choices=("off-machine", "nightly-full-run"))
    p.add_argument("--log")
    p.set_defaults(fn=_cmd_probe)
    s = sub.add_parser("selftest")
    s.set_defaults(fn=_cmd_selftest)
    a = ap.parse_args(argv)
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
