"""The delete-review page must show what a delete would remove, must never be able to delete, and must
say 'unknown' or 'claim only' wherever it has not established a number or a backup."""
import ast
import copy
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "watch"))

import delete_review as d  # noqa: E402

SRC = os.path.join(os.path.dirname(__file__), "..", "watch", "delete_review.py")

DRY_RUN = """
== egress_log ==
   rule: delete 'refused' embedding rows ...
   matching refusal rows in total : 219,400
   WOULD REMOVE                   : 218,950
     sample (1, '2026-10-01', 'f', 'awaiting_email_approval', 3)

== user_memory ==
   rule: soft-delete live rows identical ...
   live rows                      : 198,000
   (payload-only comparison would flag 21,000; the extra 762 differ in another column and are KEPT)
   WOULD REMOVE                   : 20,238

DRY RUN: nothing was changed.
"""


def item(**kw):
    base = {"id": "t1", "title": "T", "card_rows": ["X"], "store": "s", "table": "t", "method": "soft",
            "rule": "r", "why": "w", "claim": {"count": 3, "source": "a card"}, "undo": "u"}
    base.update(kw)
    return base


def plan(*items):
    return {"hold": "q1015", "items": list(items)}


COUNTED = {"count": 3, "at": "2026-11-23T10:00:00Z", "by": "a dry run", "how": "read-only"}


def backup_file(tmp_path, ids, name="b.jsonl"):
    p = tmp_path / name
    p.write_text(json.dumps({"event": "batch", "rows": [{"id": i} for i in ids]}) + "\n", encoding="utf-8")
    return str(p)


def view(it):
    return d.judge_item(it)


# ---------------------------------------------------------------- the seed

def test_seed_counts_nothing_and_offers_no_yes():
    snap = d.build(d.load_json(d.SEED))
    assert len(snap["items"]) == 4
    for v in snap["items"]:
        assert v["count_state"] in ("claimed", "unknown") and v["count_state"] != "counted"
        assert v["backup_state"] == "none"
        assert v["can_say_yes"] is False
    assert snap["nothing_deleted_by_this_page"] is True


def test_seed_covers_the_three_card_rows():
    rows = {r for it in d.load_json(d.SEED)["items"] for r in it["card_rows"]}
    assert rows == {"E10", "GRP-brain-hygiene", "Q6d"}


def test_seed_page_says_claim_and_nothing_deleted():
    page = d.render_page(d.build(d.load_json(d.SEED)))
    assert "Nothing has been deleted" in page
    assert "CLAIM ONLY" in page and "COUNTED" not in page.split("<script")[0]
    assert page.count("<button disabled") == 4


# ---------------------------------------------------------------- counts

def test_no_figure_is_unknown_not_zero():
    v = view(item(claim={}))
    assert v["count_state"] == "unknown" and v["count"] is None
    assert "unknown" in d.render_page(d.build(plan(item(claim={}))))


def test_claim_is_not_a_count():
    v = view(item())
    assert v["count_state"] == "claimed" and v["can_say_yes"] is False


def test_counted_needs_who_when_and_how():
    for drop in ("at", "by", "how"):
        c = {k: val for k, val in COUNTED.items() if k != drop}
        assert view(item(counted=c))["count_state"] == "claimed"
    assert view(item(counted=COUNTED))["count_state"] == "counted"
    assert view(item(counted=dict(COUNTED, count=True)))["count_state"] == "claimed"


def test_counted_differing_from_claim_is_said():
    v = view(item(counted=dict(COUNTED, count=5), claim={"count": 3, "source": "c"}))
    assert v["count_state"] == "counted" and "differs" in v["count_note"]


def test_id_list_that_disagrees_with_the_count_demotes_it():
    v = view(item(counted=COUNTED, ids=[1, 2]))
    assert v["count_state"] == "claimed" and "ids" in v["count_note"]


# ---------------------------------------------------------------- backups

def test_yes_only_with_counted_and_verified_backup(tmp_path):
    b = backup_file(tmp_path, [1, 2, 3, 4])
    v = view(item(counted=COUNTED, ids=[1, 2, 3], backup={"path": b}))
    assert v["backup_state"] == "verified" and v["can_say_yes"] is True
    assert "data-a=yes" in d.render_page(d.build(plan(item(counted=COUNTED, ids=[1, 2, 3], backup={"path": b}))))


def test_partial_backup_is_not_verified(tmp_path):
    b = backup_file(tmp_path, [1, 2])
    v = view(item(counted=COUNTED, ids=[1, 2, 3], backup={"path": b}))
    assert v["backup_state"] == "partial" and "1 of 3" in v["backup_text"] and not v["can_say_yes"]


def test_backup_with_none_of_the_rows(tmp_path):
    b = backup_file(tmp_path, [9])
    assert "None of the 3" in view(item(counted=COUNTED, ids=[1, 2, 3], backup={"path": b}))["backup_text"]


def test_missing_backup_file_is_none_not_verified(tmp_path):
    v = view(item(counted=COUNTED, ids=[1, 2, 3], backup={"path": str(tmp_path / "nope.jsonl")}))
    assert v["backup_state"] == "none" and not v["can_say_yes"]


def test_unreadable_backup_is_unknown(tmp_path):
    p = tmp_path / "bad.jsonl"
    p.write_text("{not json", encoding="utf-8")
    v = view(item(counted=COUNTED, ids=[1, 2, 3], backup={"path": str(p)}))
    assert v["backup_state"] == "unknown" and not v["can_say_yes"]


def test_backup_without_a_planned_id_list_cannot_be_compared(tmp_path):
    b = backup_file(tmp_path, [1, 2, 3])
    v = view(item(counted=COUNTED, backup={"path": b}))
    assert v["backup_state"] == "unknown" and "cannot be compared" in v["backup_text"]


def test_read_ids_shapes(tmp_path):
    p = tmp_path / "x.json"
    p.write_text(json.dumps([{"id": 1}, 2, "3"]), encoding="utf-8")
    assert d.read_ids(str(p)) == {"1", "2", "3"}
    q = tmp_path / "y.jsonl"
    q.write_text('{"ids":[4,5]}\n{"id":6}\n{"event":"committed","n":2}\n', encoding="utf-8")
    assert d.read_ids(str(q)) == {"4", "5", "6"}


def test_ids_file_is_used(tmp_path):
    ids = tmp_path / "ids.json"
    ids.write_text("[1,2,3]", encoding="utf-8")
    v = view(item(counted=COUNTED, ids_file=str(ids)))
    assert v["id_count"] == 3 and v["count_state"] == "counted"
    v2 = view(item(counted=COUNTED, ids_file=str(tmp_path / "gone.json")))
    assert v2["id_problem"] and v2["id_count"] is None


# ---------------------------------------------------------------- decisions

def test_yes_for_a_changed_plan_stops_counting(tmp_path):
    b = backup_file(tmp_path, [1, 2, 3])
    it = item(counted=COUNTED, ids=[1, 2, 3], backup={"path": b})
    snap = d.build(plan(it))
    fp = snap["items"][0]["fingerprint"]
    dec = {"decisions": [{"id": "t1", "answer": "yes", "fingerprint": fp}]}
    assert d.valid_yes(snap, dec) == ["t1"]
    it2 = copy.deepcopy(it)
    it2["counted"] = dict(COUNTED, count=4)
    it2["ids"] = [1, 2, 3, 4]
    assert d.valid_yes(d.build(plan(it2)), dec) == []
    it3 = copy.deepcopy(it)
    it3["rule"] = "a different rule"
    assert d.valid_yes(d.build(plan(it3)), dec) == []


def test_a_yes_is_void_if_the_backup_goes_missing(tmp_path):
    b = backup_file(tmp_path, [1, 2, 3])
    it = item(counted=COUNTED, ids=[1, 2, 3], backup={"path": b})
    fp = d.build(plan(it))["items"][0]["fingerprint"]
    os.remove(b)
    assert d.valid_yes(d.build(plan(it)), {"decisions": [{"id": "t1", "answer": "yes", "fingerprint": fp}]}) == []


def test_no_and_unknown_ids_are_never_a_yes(tmp_path):
    b = backup_file(tmp_path, [1, 2, 3])
    it = item(counted=COUNTED, ids=[1, 2, 3], backup={"path": b})
    snap = d.build(plan(it))
    fp = snap["items"][0]["fingerprint"]
    assert d.valid_yes(snap, {"decisions": [{"id": "t1", "answer": "no", "fingerprint": fp}]}) == []
    assert d.valid_yes(snap, {"decisions": [{"id": "zzz", "answer": "yes", "fingerprint": fp}]}) == []
    assert d.valid_yes(snap, None) == []


# ---------------------------------------------------------------- dry run text

def test_parse_prune_dry_run():
    got = {p["rule"]: p for p in d.parse_prune_dry_run(DRY_RUN)}
    assert got["egress_log"]["total"] == 219400 and got["egress_log"]["would_remove"] == 218950
    assert got["user_memory"]["would_remove"] == 20238 and got["user_memory"]["payload_only"] == 21000


def test_parse_unrecognised_text_gives_none_not_zero():
    got = d.parse_prune_dry_run("== egress_log ==\n   something else entirely\n")
    assert got == [{"rule": "egress_log", "total": None, "would_remove": None, "payload_only": None}]
    p = plan(item(source_rule="egress_log"))
    d.apply_dry_run(p, got, "now")
    assert "counted" not in p["items"][0]


def test_dry_run_makes_a_count_but_not_a_backup():
    p = plan(item(id="e", source_rule="egress_log"), item(id="m", source_rule="user_memory"))
    d.apply_dry_run(p, d.parse_prune_dry_run(DRY_RUN), "2026-11-23T10:00:00Z")
    snap = d.build(p)
    e, m = snap["items"]
    assert e["count_state"] == "counted" and e["count"] == 218950
    assert m["count"] == 20238
    assert e["backup_state"] == "none" and not e["can_say_yes"]


# ---------------------------------------------------------------- the page

def test_sample_is_masked():
    v = view(item(sample=[{"who": "alice.smith@example.com", "text": "x" * 200}]))
    row = v["sample"][0]
    assert "alice.smith" not in row["who"] and row["who"].startswith("a***@e***")
    assert len(row["text"]) <= d.MAX_CELL


def test_page_escapes_markup():
    page = d.render_page(d.build(plan(item(title="<script>alert(1)</script>", rule="a & b"))))
    assert "<script>alert(1)</script>" not in page
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in page
    snap_part = re.search(r'id=snap>(.*?)</script>', page, re.S).group(1)
    assert "</" not in snap_part


def test_page_has_no_network():
    page = d.render_page(d.build(d.load_json(d.SEED)))
    assert not re.search(r"https?://|fetch\(|XMLHttpRequest|<form", page)


def test_cli_render_and_check(tmp_path, capsys):
    out = tmp_path / "o"
    assert d.main(["render", "--out", str(out)]) == 0
    assert (out / "delete_review.html").exists() and json.loads((out / "delete_review.json").read_text())
    assert "nothing was deleted" in capsys.readouterr().out
    dec = tmp_path / "dec.json"
    dec.write_text(json.dumps({"decisions": [{"id": "egress-refusals", "answer": "yes", "fingerprint": "x"}]}))
    assert d.main(["check", "--decisions", str(dec)]) == 1


def test_cli_unreadable_plan_is_2(tmp_path):
    assert d.main(["render", "--plan", str(tmp_path / "missing.json"), "--out", str(tmp_path)]) == 2


def test_cli_dry_run_flags(tmp_path):
    t = tmp_path / "dry.txt"
    t.write_text(DRY_RUN, encoding="utf-8")
    out = tmp_path / "o"
    assert d.main(["render", "--dry-run-text", str(t), "--dry-run-at", "2026-11-23T10:00:00Z",
                   "--dry-run-item", "egress-refusals", "--out", str(out)]) == 0
    snap = json.loads((out / "delete_review.json").read_text())
    by = {v["id"]: v for v in snap["items"]}
    assert by["egress-refusals"]["count_state"] == "counted"
    assert by["memory-exact-copies"]["count_state"] == "claimed"      # not named, so not filled


# ---------------------------------------------------------------- it cannot delete

def test_module_cannot_delete():
    src = open(SRC, encoding="utf-8").read()
    tree = ast.parse(src)
    imported = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            imported |= {a.name.split(".")[0] for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            imported.add((n.module or "").split(".")[0])
    banned = {"sqlalchemy", "psycopg2", "psycopg", "sqlite3", "socket", "urllib", "http", "requests",
              "subprocess", "shutil", "smtplib", "ftplib"}
    assert not (imported & banned), imported & banned
    code_only = "\n".join(l for l in src.splitlines() if not l.lstrip().startswith(("#",)))
    assert not re.search(r"\b(DELETE\s+FROM|UPDATE\s+\w+\s+SET|DROP\s+TABLE|TRUNCATE)\b", code_only, re.I)
    for n in ast.walk(tree):
        if isinstance(n, ast.Attribute) and n.attr in {"remove", "unlink", "rmtree", "rmdir"}:
            raise AssertionError("file removal call in delete_review: %s" % n.attr)
    assert "os.remove" not in src and "os.unlink" not in src
