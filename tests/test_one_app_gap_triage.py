"""The gap triage must account for every one of doc 38's 57 proposals exactly once.

A table that silently lost a row, or invented a disposition, would still read as a finished triage. So the
test counts the rows itself and fails on any id missing, repeated or unknown, and on an empty 'why'."""
import os
import re

_DOC = os.path.join(os.path.dirname(__file__), os.pardir, "docs", "ONE_APP_GAP_TRIAGE.md")
ROOMS = {"Chat", "Chat box", "Context bar", "Code", "Terminal", "Memory", "Artifacts", "Library", "Routines",
         "Agents", "Connections", "Settings", "Phone", "Shell"}
DISPOSITIONS = ("landed", "build now", "later", "closed by design")


def _rows():
    rows = []
    for line in open(_DOC, encoding="utf-8").read().splitlines():
        m = re.match(r"^\| GAP-(\d\d) (.+?) \| (.+?) \| (.+?) \| (.+?) \| (.+) \|$", line)
        if m:
            rows.append({"id": int(m.group(1)), "proposal": m.group(2), "rooms": m.group(3),
                         "state": m.group(4), "disp": m.group(5), "why": m.group(6)})
    return rows


def _disp(cell):
    c = cell.replace("*", "").strip().lower()
    for d in DISPOSITIONS:
        if c.startswith(d):
            return d
    return None


def test_every_proposal_appears_exactly_once():
    ids = [r["id"] for r in _rows()]
    assert sorted(ids) == list(range(1, 58)), "missing or repeated GAP ids: %r" % sorted(ids)


def test_every_row_has_a_known_disposition_known_rooms_and_a_reason():
    for r in _rows():
        assert _disp(r["disp"]), "GAP-%02d has no known disposition: %r" % (r["id"], r["disp"])
        for room in r["rooms"].split(","):
            assert room.strip() in ROOMS, "GAP-%02d names an unknown room %r" % (r["id"], room)
        assert r["why"].strip() and r["state"].strip(), "GAP-%02d has an empty cell" % r["id"]


def test_the_counts_in_the_prose_match_the_rows():
    counts = {d: 0 for d in DISPOSITIONS}
    for r in _rows():
        counts[_disp(r["disp"])] += 1
    text = open(_DOC, encoding="utf-8").read()
    m = re.search(r"\*\*landed (\d+)\*\*.*?\*\*build now (\d+)\*\*.*?\*\*later (\d+)\*\*.*?\*\*closed by design (\d+)\*\*",
                  text, re.S)
    assert m, "the counts sentence is missing"
    stated = dict(zip(DISPOSITIONS, map(int, m.groups())))
    assert stated == counts, "prose %r, rows %r" % (stated, counts)
    assert sum(counts.values()) == 57
