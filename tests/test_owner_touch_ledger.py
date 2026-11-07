"""WATCH: the owner-touch ledger says UNKNOWN (exit 2) when it cannot see, and counts only on evidence.

The subject of the guard test is the false zero: a ledger that prints "0 owner touches" because no
transcript was found, or because the `origin` field it keys on has gone, reads exactly like a quiet day.
Every fixture here is a fake transcripts root under tmp_path; nothing reads the real ~/.claude.
"""
import importlib.util
import json
import os
import subprocess
import sys
import time

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "owner_touch_ledger.py")
_spec = importlib.util.spec_from_file_location("owner_touch_ledger", _PATH)
otl = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(otl)


def _ts(offset_seconds=0):
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(time.time() - offset_seconds))


def _user(text, kind="human", with_origin=True, offset=60, **extra):
    o = {"type": "user", "timestamp": _ts(offset), "message": {"role": "user", "content": text}}
    if with_origin:
        o["origin"] = {"kind": kind}
    o.update(extra)
    return json.dumps(o, separators=(",", ":"))


def _write(root, project, sid, lines, age_seconds=0):
    d = root / project
    d.mkdir(parents=True, exist_ok=True)
    f = d / (sid + ".jsonl")
    f.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if age_seconds:
        t = time.time() - age_seconds
        os.utime(f, (t, t))
    return f


def _run(root, *args):
    return subprocess.run([sys.executable, "-I", _PATH, "--root", str(root), *args],
                          capture_output=True, text=True, encoding="utf-8")


def test_empty_root_is_unknown_exit_2_not_zero(tmp_path):
    r = _run(tmp_path, "--days", "1")
    assert r.returncode == 2
    assert r.stdout.startswith("UNKNOWN")
    assert "not zero" in r.stdout
    assert "owner touches: 0" not in r.stdout


def test_missing_root_is_unknown_exit_2(tmp_path):
    r = _run(tmp_path / "does-not-exist", "--days", "1", "--line")
    assert r.returncode == 2
    assert "UNKNOWN" in r.stdout and "owner touches" not in r.stdout


def test_only_stale_transcripts_is_unknown(tmp_path):
    _write(tmp_path, "p", "old", [_user("go")], age_seconds=10 * 86400)
    r = _run(tmp_path, "--days", "1")
    assert r.returncode == 2
    assert "UNKNOWN" in r.stdout


def test_origin_field_gone_is_unknown_not_zero(tmp_path):
    _write(tmp_path, "p", "s1", [_user("hello there", with_origin=False), _user("go", with_origin=False)])
    r = _run(tmp_path, "--days", "1")
    assert r.returncode == 2
    assert "origin.kind" in r.stdout
    assert "owner touches: 0" not in r.stdout


def test_counts_human_touches_and_ignores_the_rest(tmp_path):
    tool_result = json.dumps({"type": "user", "timestamp": _ts(30), "origin": {"kind": "human"},
                              "message": {"content": [{"type": "tool_result", "content": "x"}]}})
    _write(tmp_path, "p", "s1", [
        _user("go"),                                              # human touch
        _user("whats next"),                                      # human touch
        _user("a scheduled tick", kind="task-notification"),      # not human
        _user("sidechain text", isSidechain=True),                # not counted
        _user("meta text", isMeta=True),                          # not counted
        tool_result,                                              # not counted
        _user("a long ago human line", offset=5 * 86400),         # outside the window
        "not json at all",                                        # tolerated
    ])
    _write(tmp_path, "q", "s2", [_user("the seed bank is what i was talking about")])
    seen, touches, user_msgs, with_origin = otl.read_touches(str(tmp_path), time.time() - 86400)
    assert seen == 2
    assert sorted(c for _, _, c in touches) == sorted([
        "go / approve / click-answer",
        "status poll (nothing pushed it to me)",
        "other (new input or a real decision)",
    ])
    assert with_origin > 0


def test_genuine_zero_is_reported_as_zero_with_evidence(tmp_path):
    # transcripts exist, origin is present, and nobody human typed: that is a real 0, exit 0.
    _write(tmp_path, "p", "s1", [_user("tick", kind="task-notification")])
    r = _run(tmp_path, "--days", "1")
    assert r.returncode == 0
    assert "owner touches: 0" in r.stdout and "transcripts scanned: 1" in r.stdout


def test_line_form_is_one_line_and_names_counts(tmp_path):
    _write(tmp_path, "p", "s1", [_user("go"), _user("whats next")])
    r = _run(tmp_path, "--days", "1", "--line")
    assert r.returncode == 0
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1
    assert lines[0].startswith("OWNER-TOUCH-LEDGER ")
    assert "2 owner touches in 1 sessions, 1 transcripts scanned" in lines[0]


def test_unknown_line_form_is_one_line(tmp_path):
    r = _run(tmp_path, "--days", "1", "--line")
    assert r.returncode == 2
    assert len(r.stdout.strip().splitlines()) == 1
    assert r.stdout.startswith("OWNER-TOUCH-LEDGER ") and "UNKNOWN" in r.stdout


def test_selftest_passes():
    r = subprocess.run([sys.executable, "-I", _PATH, "--selftest"], capture_output=True, text=True)
    assert r.returncode == 0
    assert "selftest: ok" in r.stdout


def test_min_transcripts_floor_makes_a_lone_self_transcript_unknown(tmp_path):
    # A scheduled run inside a Claude session always sees its own transcript; with the floor at 2 that
    # alone must not read as "the ledger could see".
    _write(tmp_path, "p", "me", [_user("tick", kind="task-notification")])
    r = _run(tmp_path, "--days", "1", "--min-transcripts", "2", "--line")
    assert r.returncode == 2
    assert "UNKNOWN" in r.stdout and "fewer than the 2 expected" in r.stdout
    _write(tmp_path, "q", "other", [_user("go")])
    r = _run(tmp_path, "--days", "1", "--min-transcripts", "2", "--line")
    assert r.returncode == 0
