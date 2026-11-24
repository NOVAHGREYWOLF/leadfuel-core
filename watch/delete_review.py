#!/usr/bin/env python3
"""delete_review - the page that shows exactly which rows a delete would remove, BEFORE any delete.

Owner hold q1015 (2026-10-31): "ask before deleting, with a page that says exactly what is
happening". Answer A on that card does NOT authorise a delete; a delete waits for a yes given on
THIS page, for THIS plan, and no other.

THIS FILE CAN NOT DELETE ANYTHING. It has no database driver, no network and no SQL. It reads a
plan file (and, optionally, the text a dry run printed and a backup file on disk) and writes one
self-contained HTML page plus a JSON snapshot of what the page says. The static test
`test_module_cannot_delete` fails if a delete statement, a database or network import ever lands
here.

  python watch/delete_review.py render --plan plan.json [--dry-run-text out.txt --dry-run-at ISO
                                        --dry-run-item E10-egress ...] [--out DIR]
  python watch/delete_review.py check  --plan plan.json --decisions decisions.json

`render` writes DIR/delete_review.html and DIR/delete_review.json (default DIR:
%LOCALAPPDATA%\\delete-review). `check` prints which items carry a valid yes. Exit 0 = at least one
valid yes, 1 = none, 2 = unreadable input.

HONESTY RULES (the estate's own: a check that cannot establish a state must not report one)
  * A count is shown as COUNTED only when the plan names who counted it, when, and how. A figure
    that only appears in a card or a checklist is a CLAIM and is shown as one. No figure at all is
    "unknown", never 0.
  * A backup is VERIFIED only when the file exists, can be read, and every id the plan would remove
    is in it. Anything less is partial / none / unknown, and the page says which.
  * A "yes" is only offered when the count is COUNTED and the backup is VERIFIED. Otherwise the
    page offers "no, not yet" and says what is missing. The yes carries a fingerprint of the plan
    it answered; if the counts, rule or ids change afterwards the old yes stops counting.
  * Sample rows are masked (e-mail addresses are partly hidden, long values cut) because the page
    is a file on the owner's machine, not a place for account data.

PLAN FILE (JSON): {"generated": ISO, "hold": "q1015", "items": [ITEM, ...]} with ITEM
  id, title, card_rows[], store, table, method ("hard" | "soft" | "undecided"), rule (plain words),
  why, claim {"count": int|null, "source": str}, counted {"count": int, "at": ISO, "by": str,
  "how": str} | null, ids [..] | ids_file path | null, sample [{col: val}], backup {"path": str} |
  null, undo (plain words), source_rule (optional: "egress_log" | "user_memory", links a dry run).

Backup / ids files may be a JSON list (of ids or of {"id": ..}), or JSONL whose lines hold
{"id": ..}, {"ids": [..]} or {"rows": [{"id": ..}, ..]} (the shape scripts/prune_q115.py records).

Stdlib only.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

OUT_DEFAULT = os.path.join(os.environ.get("LOCALAPPDATA", os.path.expanduser("~")), "delete-review")
HERE = os.path.dirname(os.path.abspath(__file__))
SEED = os.path.join(HERE, "delete_review_seed.json")
METHODS = ("hard", "soft", "undecided")
EMAIL_RE = re.compile(r"([A-Za-z0-9._%+-])[A-Za-z0-9._%+-]*@([A-Za-z0-9])[A-Za-z0-9.-]*(\.[A-Za-z]{2,})")
MAX_CELL = 60
MAX_SAMPLE = 8


# ---------------------------------------------------------------- reading inputs

def load_json(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _ids_from_obj(o, out):
    if isinstance(o, bool):
        return
    if isinstance(o, (int, str)):
        out.add(str(o))
    elif isinstance(o, list):
        for x in o:
            _ids_from_obj(x, out)
    elif isinstance(o, dict):
        if "rows" in o and isinstance(o["rows"], list):
            for r in o["rows"]:
                if isinstance(r, dict) and "id" in r:
                    _ids_from_obj(r["id"], out)
        if "ids" in o and isinstance(o["ids"], list):
            _ids_from_obj(o["ids"], out)
        if "id" in o and not isinstance(o["id"], (dict, list)):
            _ids_from_obj(o["id"], out)


def read_ids(path):
    """The set of ids named in a JSON list or a JSONL file, as strings. Raises on unreadable."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    ids = set()
    stripped = text.lstrip()
    if stripped.startswith("["):
        _ids_from_obj(json.loads(text), ids)
        return ids
    for line in text.splitlines():
        line = line.strip()
        if line:
            _ids_from_obj(json.loads(line), ids)
    return ids


def parse_prune_dry_run(text):
    """Parse what `scripts/prune_q115.py` prints on a dry run. One dict per rule section:
    {rule, total, would_remove, payload_only}. A number not found is None, never 0."""
    out, cur = [], None
    num = r"([\d,]+)"
    for line in text.splitlines():
        m = re.match(r"\s*==\s*(\w+)\s*==\s*$", line)
        if m:
            cur = {"rule": m.group(1), "total": None, "would_remove": None, "payload_only": None}
            out.append(cur)
            continue
        if cur is None:
            continue
        for key, pat in (("total", r"(?:matching refusal rows in total|live rows)\s*:\s*" + num),
                         ("would_remove", r"WOULD REMOVE\s*:\s*" + num),
                         ("payload_only", r"payload-only comparison would flag\s*" + num)):
            m = re.search(pat, line)
            if m:
                cur[key] = int(m.group(1).replace(",", ""))
    return out


def apply_dry_run(plan, parsed, at, by="dry run output supplied to the page", item_id=None):
    """Fill `counted` on the item(s) whose source_rule matches a parsed section. The dry run
    prints a count but not the ids, so ids stay as the plan has them (None -> backup unknown)."""
    for it in plan["items"]:
        if item_id and it["id"] != item_id:
            continue
        sec = next((p for p in parsed if p["rule"] == it.get("source_rule")), None)
        if sec and sec["would_remove"] is not None:
            it["counted"] = {"count": sec["would_remove"], "at": at, "by": by,
                             "how": "scripts/prune_q115.py dry run, read-only, rule %s" % sec["rule"]}
    return plan


# ---------------------------------------------------------------- judging an item

def mask(v):
    s = "" if v is None else str(v)
    s = EMAIL_RE.sub(lambda m: "%s***@%s***%s" % (m.group(1), m.group(2), m.group(3)), s)
    return s if len(s) <= MAX_CELL else s[:MAX_CELL - 1] + "…"


def ids_digest(ids):
    return hashlib.sha256("\n".join(sorted(ids)).encode()).hexdigest()[:16] if ids else None


def fingerprint(it, count, ids):
    body = {"id": it.get("id"), "store": it.get("store"), "table": it.get("table"),
            "method": it.get("method"), "rule": it.get("rule"), "count": count,
            "ids": ids_digest(ids)}
    return hashlib.sha256(json.dumps(body, sort_keys=True).encode()).hexdigest()[:16]


def judge_count(it):
    """-> (state, count, note). counted | claimed | unknown."""
    c = it.get("counted")
    claim = (it.get("claim") or {})
    if isinstance(c, dict) and isinstance(c.get("count"), int) and not isinstance(c.get("count"), bool) \
            and c.get("at") and c.get("by") and c.get("how"):
        note = ""
        if isinstance(claim.get("count"), int) and claim["count"] != c["count"]:
            note = "The earlier claim was %s; the count differs." % format(claim["count"], ",")
        return "counted", c["count"], note
    if isinstance(claim.get("count"), int):
        return "claimed", claim["count"], ""
    return "unknown", None, ""


def planned_ids(it):
    """-> (ids set|None, problem str|None)."""
    if isinstance(it.get("ids"), list):
        return {str(x) for x in it["ids"]}, None
    if it.get("ids_file"):
        try:
            return read_ids(it["ids_file"]), None
        except (OSError, ValueError) as e:
            return None, "ids file unreadable (%s)" % type(e).__name__
    return None, None


def judge_backup(it, ids):
    """-> (state, text). verified | partial | none | unknown. Verified needs every planned id."""
    b = it.get("backup")
    if not b or not b.get("path"):
        return "none", "No backup file is named. Nothing is saved yet."
    path = b["path"]
    if not os.path.isfile(path):
        return "none", "The backup file named in the plan does not exist on this machine."
    try:
        have = read_ids(path)
    except (OSError, ValueError) as e:
        return "unknown", "The backup file exists but could not be read (%s)." % type(e).__name__
    if not ids:
        return "unknown", ("The backup file holds %s rows, but the plan has no list of the ids it "
                           "would remove, so coverage cannot be compared." % format(len(have), ","))
    missing = len(ids - have)
    if missing == 0:
        return "verified", "Every one of the %s rows is in the backup file (%s rows in the file)." % (
            format(len(ids), ","), format(len(have), ","))
    if missing < len(ids):
        return "partial", "%s of %s rows are NOT in the backup file." % (format(missing, ","),
                                                                        format(len(ids), ","))
    return "partial", "None of the %s rows are in the backup file." % format(len(ids), ",")


def judge_item(it):
    cstate, count, cnote = judge_count(it)
    ids, idprob = planned_ids(it)
    if cstate == "counted" and ids is not None and len(ids) != count:
        cnote = (cnote + " " if cnote else "") + "The id list holds %s ids but the count says %s." % (
            format(len(ids), ","), format(count, ","))
        cstate = "claimed"          # two numbers disagree: neither is established
    bstate, btext = judge_backup(it, ids)
    method = it.get("method") if it.get("method") in METHODS else "undecided"
    missing = []
    if cstate != "counted":
        missing.append("an exact count (%s)" % ("only a claim exists" if cstate == "claimed" else "none exists"))
    if bstate != "verified":
        missing.append("a verified backup (%s)" % bstate)
    can_yes = not missing
    return {
        "id": it["id"], "title": it.get("title", it["id"]), "card_rows": it.get("card_rows", []),
        "store": it.get("store", "unknown"), "table": it.get("table", "unknown"),
        "method": method, "rule": it.get("rule", "unknown"), "why": it.get("why", "unknown"),
        "undo": it.get("undo", "unknown"),
        "count_state": cstate, "count": count, "count_note": cnote,
        "claim": it.get("claim") or {}, "counted": it.get("counted"),
        "id_problem": idprob, "id_count": None if ids is None else len(ids),
        "sample": [{k: mask(v) for k, v in row.items()} for row in (it.get("sample") or [])[:MAX_SAMPLE]],
        "backup_state": bstate, "backup_text": btext,
        "can_say_yes": can_yes, "missing_for_yes": missing,
        "fingerprint": fingerprint(it, count if cstate == "counted" else None, ids),
    }


def build(plan, now=None):
    now = now or datetime.now(timezone.utc)
    views = [judge_item(it) for it in plan.get("items", [])]
    return {"generated": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "hold": plan.get("hold", "q1015"),
            "nothing_deleted_by_this_page": True, "items": views}


def valid_yes(snapshot, decisions):
    """Ids with a yes that (a) names the item's CURRENT fingerprint and (b) is still allowed
    (counted + verified backup). This is the only reading of a decision file a later delete step
    may rely on, and it still deletes nothing."""
    by_id = {v["id"]: v for v in snapshot["items"]}
    ok = []
    for d in (decisions or {}).get("decisions", []):
        v = by_id.get(d.get("id"))
        if v and d.get("answer") == "yes" and d.get("fingerprint") == v["fingerprint"] and v["can_say_yes"]:
            ok.append(v["id"])
    return ok


# ---------------------------------------------------------------- the page

E = html.escape

STATE_WORDS = {"counted": "COUNTED", "claimed": "CLAIM ONLY, not counted", "unknown": "UNKNOWN"}
METHOD_WORDS = {"hard": "Hard delete: the rows are gone for good.",
                "soft": "Soft delete: rows are hidden (a deleted_at stamp), not erased. Reversible.",
                "undecided": "Method not chosen yet. This page proposes no delete method."}


def _fmt(n):
    return "unknown" if n is None else format(n, ",")


def _card(v):
    if v["count_state"] == "counted":
        c = v["counted"]
        count_html = ("<b class=big>%s rows</b> <span class=tag ok>COUNTED</span>"
                      "<div class=sub>Counted %s by %s. How: %s.</div>" % (
                          _fmt(v["count"]), E(str(c["at"])), E(str(c["by"])), E(str(c["how"]))))
    elif v["count_state"] == "claimed":
        count_html = ("<b class=big>about %s rows</b> <span class=tag warn>%s</span>"
                      "<div class=sub>%s Nobody has counted this on the live data. Treat it as a guess.</div>" % (
                          _fmt(v["count"]), E(STATE_WORDS["claimed"]), E(v["claim"].get("source", "Source not named.")) ))
    else:
        count_html = "<b class=big>unknown</b> <span class=tag bad>UNKNOWN</span><div class=sub>No figure exists yet.</div>"
    if v["count_note"]:
        count_html += "<div class=sub warnnote>%s</div>" % E(v["count_note"])
    if v["sample"]:
        cols = list(v["sample"][0].keys())
        head = "".join("<th>%s</th>" % E(c) for c in cols)
        body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % E(r.get(c, "")) for c in cols) for r in v["sample"])
        sample_html = "<table><tr>%s</tr>%s</table><div class=sub>First %d rows only, partly masked.</div>" % (
            head, body, len(v["sample"]))
    else:
        sample_html = "<div class=sub>No sample rows yet: the rows have not been read. Showing none is not the same as there being none.</div>"
    bclass = {"verified": "ok", "partial": "bad", "none": "bad", "unknown": "warn"}[v["backup_state"]]
    if v["can_say_yes"]:
        buttons = ("<button data-a=yes>Yes, remove exactly this</button> "
                   "<button data-a=no>No, do not remove</button>")
        gate = ""
    else:
        buttons = "<button disabled title='Not allowed yet'>Yes, remove exactly this</button> <button data-a=no>No, not yet</button>"
        gate = "<div class='gate'>A yes is not offered yet. Missing: %s.</div>" % E("; ".join(v["missing_for_yes"]))
    return (
        "<section class=card data-id='%(id)s' data-fp='%(fp)s'>"
        "<h2>%(title)s</h2><div class=rows>Card rows: %(rows)s</div>"
        "<dl>"
        "<dt>Where</dt><dd>%(store)s, table <code>%(table)s</code></dd>"
        "<dt>Which rows</dt><dd>%(rule)s</dd>"
        "<dt>Why</dt><dd>%(why)s</dd>"
        "<dt>How many</dt><dd>%(count)s</dd>"
        "<dt>Sample</dt><dd>%(sample)s</dd>"
        "<dt>How it would be removed</dt><dd>%(method)s</dd>"
        "<dt>Can it be undone</dt><dd>%(undo)s</dd>"
        "<dt>Backup</dt><dd><span class='tag %(bclass)s'>%(bstate)s</span> %(btext)s</dd>"
        "</dl>%(gate)s<div class=answer>%(buttons)s <span class=said></span></div></section>") % {
        "id": E(v["id"]), "fp": E(v["fingerprint"]), "title": E(v["title"]),
        "rows": E(", ".join(v["card_rows"]) or "none named"), "store": E(v["store"]), "table": E(v["table"]),
        "rule": E(v["rule"]), "why": E(v["why"]), "count": count_html, "sample": sample_html,
        "method": E(METHOD_WORDS[v["method"]]), "undo": E(v["undo"]), "bclass": bclass,
        "bstate": E(v["backup_state"].upper()), "btext": E(v["backup_text"]), "gate": gate, "buttons": buttons}


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Before anything is deleted</title>
<style>
:root{--bg:#fff;--fg:#1b1f24;--mut:#5b6670;--card:#f5f7f9;--line:#d6dce1;--ok:#17703a;--warn:#8a5a00;--bad:#a4262c}
@media (prefers-color-scheme:dark){:root{--bg:#14181c;--fg:#e8ecef;--mut:#9aa6b0;--card:#1d2328;--line:#343c44;--ok:#5fcf8a;--warn:#e6b04a;--bad:#ff8a8f}}
body{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;margin:0;padding:16px;max-width:860px;margin-inline:auto}
h1{font-size:1.5rem;margin:.2em 0}.banner{border:2px solid var(--ok);border-radius:8px;padding:10px 14px;margin:12px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:12px 14px;margin:16px 0}
h2{font-size:1.15rem;margin:.1em 0}.rows,.sub{color:var(--mut);font-size:.875rem}.warnnote{color:var(--warn)}
dl{display:grid;grid-template-columns:9em 1fr;gap:6px 12px}dt{font-weight:600}dd{margin:0;min-width:0;overflow-wrap:anywhere}
.big{font-size:1.1rem}.tag{font-size:.75rem;font-weight:700;border:1px solid currentColor;border-radius:4px;padding:0 5px}
.tag.ok{color:var(--ok)}.tag.warn{color:var(--warn)}.tag.bad{color:var(--bad)}
table{border-collapse:collapse;font-size:.8rem;display:block;overflow-x:auto}td,th{border:1px solid var(--line);padding:2px 6px;text-align:left}
.gate{border-left:4px solid var(--bad);padding:4px 10px;margin:8px 0}button{font:inherit;padding:6px 12px;margin:4px 6px 4px 0;min-height:40px}
button[disabled]{opacity:.5}.said{font-weight:600}@media (max-width:560px){dl{grid-template-columns:1fr}}
</style></head><body>
<h1>Before anything is deleted</h1>
<div class=banner><b>Nothing has been deleted.</b> This page only shows what a delete would remove. Pressing a button here
records your answer in a file; it removes nothing. Hold __HOLD__, page made __GEN__.</div>
__CARDS__
<p><button id=dl>Save my answers to a file</button> <span class=sub>The file lists each answer with the fingerprint of the plan it answered.
If the counts or rules change later, an old yes stops counting.</span></p>
<script type="application/json" id=snap>__SNAP__</script>
<script>
(function(){
var snap=JSON.parse(document.getElementById('snap').textContent),dec={},KEY='delete-review-'+snap.generated;
try{dec=JSON.parse(localStorage.getItem(KEY)||'{}')}catch(e){dec={}}
function paint(){document.querySelectorAll('.card').forEach(function(c){var d=dec[c.dataset.id];
c.querySelector('.said').textContent=d?('Your answer: '+d.answer.toUpperCase()):''})}
function save(){try{localStorage.setItem(KEY,JSON.stringify(dec))}catch(e){}}
document.querySelectorAll('.card button[data-a]').forEach(function(b){b.addEventListener('click',function(){
var c=b.closest('.card');dec[c.dataset.id]={id:c.dataset.id,answer:b.dataset.a,fingerprint:c.dataset.fp,
at:new Date().toISOString()};save();paint()})});
document.getElementById('dl').addEventListener('click',function(){
var out={plan_generated:snap.generated,hold:snap.hold,decisions:Object.keys(dec).map(function(k){return dec[k]})};
var a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(out,null,1)],{type:'application/json'}));
a.download='delete-review-decisions.json';a.click()});
paint()})();
</script></body></html>
"""


def render_page(snapshot):
    snap_json = json.dumps(snapshot).replace("</", "<\\/")
    return (PAGE.replace("__HOLD__", E(str(snapshot["hold"]))).replace("__GEN__", E(snapshot["generated"]))
            .replace("__CARDS__", "\n".join(_card(v) for v in snapshot["items"]))
            .replace("__SNAP__", snap_json))


# ---------------------------------------------------------------- command line

def cmd_render(a):
    plan = load_json(a.plan)
    for i, path in enumerate(a.dry_run_text or []):
        with open(path, encoding="utf-8") as f:
            parsed = parse_prune_dry_run(f.read())
        apply_dry_run(plan, parsed, a.dry_run_at or "time not given",
                      item_id=(a.dry_run_item[i] if a.dry_run_item and i < len(a.dry_run_item) else None))
    snap = build(plan)
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(a.out, "delete_review.html"), "w", encoding="utf-8") as f:
        f.write(render_page(snap))
    with open(os.path.join(a.out, "delete_review.json"), "w", encoding="utf-8") as f:
        json.dump(snap, f, indent=1)
    for v in snap["items"]:
        print("%-22s count=%-8s backup=%-9s yes_offered=%s" % (
            v["id"], v["count_state"], v["backup_state"], v["can_say_yes"]))
    print("wrote", os.path.join(a.out, "delete_review.html"), "- nothing was deleted")
    return 0


def cmd_check(a):
    snap = build(load_json(a.plan))
    ok = valid_yes(snap, load_json(a.decisions))
    print("valid yes:", ", ".join(ok) if ok else "none")
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--plan", default=SEED)
    r.add_argument("--dry-run-text", action="append", help="file holding prune_q115.py dry run output")
    r.add_argument("--dry-run-at", help="ISO time the dry run was taken")
    r.add_argument("--dry-run-item", action="append", help="item id the matching --dry-run-text applies to")
    r.add_argument("--out", default=OUT_DEFAULT)
    c = sub.add_parser("check")
    c.add_argument("--plan", default=SEED)
    c.add_argument("--decisions", required=True)
    a = ap.parse_args(argv)
    try:
        return cmd_render(a) if a.cmd == "render" else cmd_check(a)
    except (OSError, ValueError, KeyError) as e:
        print("UNREADABLE INPUT (%s): %s" % (type(e).__name__, e), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
