"""VAULT S1: the leak scanner finds a value in any common form, never prints it, and says unknown
when it cannot see (no canary, zero bytes, an unreadable file, a secret it was not given).

Every value here is synthetic, made in the test. No test reads the real environment: each one
passes its own `env` mapping, and the default-names test checks names only.
"""
import ast
import base64
import io
import json
import os
import importlib.util
import secrets
import sys

import pytest

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "vault", "leak_scan.py")
_spec = importlib.util.spec_from_file_location("leak_scan", _PATH)
ls = importlib.util.module_from_spec(_spec)
sys.modules["leak_scan"] = ls  # dataclasses look their module up by name
_spec.loader.exec_module(ls)

NAME = "SYNTH_TOKEN"


def synthetic(n=37):
    """A fresh fake token with characters that make every encoded form differ from the raw one."""
    # The space makes quote_plus differ from quote, so the test proves that form too.
    return secrets.token_urlsafe(n)[:n - 8] + ' +/"\\=x'


KEY = secrets.token_bytes(32)  # the state key; in real runs it lives in <state>.key


def write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


def run_cli(argv, env):
    out = io.StringIO()
    code = ls.main(argv, env=env, out=out)
    return code, out.getvalue()


def forbidden_forms(value):
    raw = value.encode()
    forms = {f for _l, f in ls.encoded_forms(value)}
    # Independent of the module, so a bug in encoded_forms cannot hide a leak from this check.
    forms |= {raw, base64.b64encode(raw), base64.urlsafe_b64encode(raw), raw.hex().encode(),
              raw.hex().upper().encode(), json.dumps(value)[1:-1].encode()}
    return forms


def numbers_in(obj):
    if isinstance(obj, bool):
        return
    if isinstance(obj, (int, float)):
        yield obj
    elif isinstance(obj, dict):
        for v in obj.values():
            yield from numbers_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from numbers_in(v)


def keys_in(obj):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield k
            yield from keys_in(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from keys_in(v)


def assert_never_printed(value, *texts):
    for text in texts:
        blob = text.encode()
        for form in forbidden_forms(value):
            assert form not in blob, "a form of the value was printed"


# --- the design's six named tests -------------------------------------------------------------

def test_scan_finds_planted_value_and_never_prints_it(tmp_path, capsys):
    value = synthetic(53)
    root = tmp_path / "root"
    write(str(root / "a" / "transcript.jsonl"), "line one\nline two\nthe token " + value + " here\n")
    write(str(root / "b.txt"), "nothing\n")
    code, out = run_cli(["--root", str(root), "--names", NAME], env={NAME: value})
    captured = capsys.readouterr()
    report = json.loads(out)

    assert code == ls.EXIT_FOUND
    assert report["result"] == "found"
    assert report["secrets"][NAME]["status"] == "found"
    [hit] = report["findings"]
    assert hit["secret"] == NAME and hit["line"] == 3 and hit["form"] == "raw"
    assert hit["path"].endswith("transcript.jsonl")
    assert set(hit) == {"secret", "path", "line", "form", "new"}  # no text, no column, no length
    assert_never_printed(value, out, captured.out, captured.err)
    assert len(value) not in set(numbers_in(report)), "the value's length is in the report"
    assert not [k for k in keys_in(report) if "len" in k.lower() or "size" in k.lower()]
    assert not (root / ls.CANARY_FILE).exists(), "the canary must be removed after the run"


def test_scan_without_canary_says_unknown(tmp_path, monkeypatch):
    root = tmp_path / "root"
    write(str(root / "log.txt"), "plenty of real content and no secret\n")
    env = {NAME: synthetic()}

    # 1. A filter that hides the canary is a blind scan: it would hide other files the same way.
    report, _ = ls.scan([str(root)], names=[NAME], env=env, excludes=[".*"])
    assert report["result"] == "unknown"
    assert report["secrets"][NAME]["status"] == "unknown"
    assert report["roots"][0]["canary"] == "missing"

    # 2. A canary that was never planted.
    monkeypatch.setattr(ls, "_plant", lambda *a, **k: None)
    report, _ = ls.scan([str(root)], names=[NAME], env=env)
    assert report["result"] == "unknown"
    assert report["roots"][0]["canary"].startswith("not planted")

    # 3. A matcher that has gone blind to one encoding: the canary proves every form, not just raw.
    monkeypatch.undo()
    real = ls.encoded_forms
    monkeypatch.setattr(ls, "_needles", lambda s, v: [
        ls._Needle(s, label, f"{label}#{i}", data if label != "hex" else b"\0never\0")
        for i, (label, data) in enumerate(real(v))])
    report, _ = ls.scan([str(root)], names=[NAME], env=env)
    assert report["result"] == "unknown"
    assert report["roots"][0]["canary"] == "missing"


def test_zero_bytes_scanned_says_unknown(tmp_path):
    empty = tmp_path / "empty"
    empty.mkdir()
    report, _ = ls.scan([str(empty)], names=[NAME], env={NAME: synthetic()})
    assert report["roots"][0]["canary"] == "found"  # it could see; there was nothing to see
    assert report["roots"][0]["bytes_covered"] == 0
    assert report["result"] == "unknown"

    missing = tmp_path / "does-not-exist"
    report, _ = ls.scan([str(missing)], names=[NAME], env={NAME: synthetic()})
    assert report["result"] == "unknown"

    report, _ = ls.scan([], names=[NAME], env={NAME: synthetic()})
    assert report["result"] == "unknown"


def test_finds_base64_hex_url_json_forms(tmp_path):
    value = synthetic(41)
    raw = value.encode()
    root = tmp_path / "root"
    files = {}
    for k, prefix in enumerate([b"", b"x", b"xy"]):  # all three base64 alignments
        files[f"b64_{k}.txt"] = base64.b64encode(prefix + raw + b"tail").decode()
        files[f"b64url_{k}.txt"] = base64.urlsafe_b64encode(prefix + raw + b"tail").decode()
    files["hex.txt"] = "0x" + raw.hex()
    files["hexupper.txt"] = raw.hex().upper()  # not HEX.txt: Windows names ignore case
    from urllib.parse import quote, quote_plus
    files["url.txt"] = "https://example.invalid/?k=" + quote(value, safe="") + "&z=1"
    files["urlplus.txt"] = "k=" + quote_plus(value, safe="")
    files["json.jsonl"] = json.dumps({"tool_result": "env says " + value})
    files["json2.jsonl"] = json.dumps({"outer": json.dumps({"inner": value})})
    for name, text in files.items():
        write(str(root / name), "header\n" + text + "\n")

    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    found = {os.path.basename(f["path"]): f for f in report["findings"]}
    assert set(found) == set(files), sorted(set(files) - set(found))
    assert all(f["line"] == 2 for f in found.values())
    assert found["hex.txt"]["form"] == "hex" and found["url.txt"]["form"] == "url"
    assert found["json.jsonl"]["form"] == "json" and found["b64_1.txt"]["form"] == "base64"
    # A fragment with no + / - _ in it is the same bytes in both alphabets, de-duplicated.
    assert found["b64url_2.txt"]["form"] in {"base64", "base64url"}


def test_shape_fingerprint_finds_forgotten_secret(tmp_path):
    key = secrets.token_bytes(32)
    forgotten = "".join(secrets.choice(ls.URLSAFE) for _ in range(64))
    other = "".join(secrets.choice(ls.URLSAFE) for _ in range(64))
    spec = ls.ShapeSpec("APPROVAL_LINK_SECRET", ls.URLSAFE, 64,
                        ls.fingerprint(key, forgotten.encode()), key)
    root = tmp_path / "root"
    write(str(root / "mail.txt"), "a\nb\nlink sig=" + forgotten + "&id=7\n")
    write(str(root / "noise.txt"), "another run of the same shape: " + other + "\n")
    write(str(root / "longer.txt"), "embedded in a longer run: " + forgotten + "Q\n")

    report, _ = ls.scan([str(root)], names=[], env={}, shapes=[spec])
    assert [(os.path.basename(f["path"]), f["line"], f["form"]) for f in report["findings"]] \
        == [("mail.txt", 3, "shape")]
    assert report["result"] == "found"
    out = json.dumps(report)
    assert forgotten not in out and key.hex() not in out and spec.fingerprint not in out
    assert "key" not in repr(spec)


def test_incremental_offsets_skip_nothing_appended(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "CHUNK", 64)  # force many chunk boundaries too
    value = synthetic(45)
    root = tmp_path / "root"
    log = root / "session.jsonl"
    half = len(value) // 2
    write(str(log), "".join(f"filler line {i}\n" for i in range(20)) + "start " + value[:half])

    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, key=KEY)
    assert report["result"] == "clean" and report["mode"] == "full"
    first_size = log.stat().st_size
    assert sorted(e["offset"] for e in state["files"].values()) == [first_size]

    # Append the rest of the value (straddling the old end), more lines, and a second copy.
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(value[half:] + " end\nmore\nagain " + value + "\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state, key=KEY)
    assert report["mode"] == "incremental"
    assert report["roots"][0]["bytes_scanned"] == log.stat().st_size - first_size
    assert [(f["line"], f["new"]) for f in report["findings"]] == [(21, True), (23, True)]

    # Nothing appended: nothing new, the old findings still reported, and not blind.
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state, key=KEY)
    assert report["roots"][0]["bytes_scanned"] == 0
    assert report["roots"][0]["bytes_covered"] == log.stat().st_size
    assert [(f["line"], f["new"]) for f in report["findings"]] == [(21, False), (23, False)]
    assert report["result"] == "found"

    # A file rewritten in place (its head changed) is scanned again from the start.
    other = root / "other.txt"
    write(str(other), "x" * 100 + "\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state, key=KEY)
    write(str(other), value + "y" * 100 + "\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state, key=KEY)
    assert any(f["path"] == str(other) and f["line"] == 1 for f in report["findings"])

    # A new secret name means the offsets do not apply: a full scan.
    report, _ = ls.scan([str(root)], names=[NAME, "SYNTH_OTHER"],
                        env={NAME: value, "SYNTH_OTHER": synthetic()}, state=state, key=KEY)
    assert report["mode"] == "full"


def test_every_chunk_alignment_found_exactly_once(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "CHUNK", 16)
    value = synthetic(29)
    root = tmp_path / "root"
    for pad in range(40):
        write(str(root / f"p{pad:02d}.txt"), "\n" * (pad % 3) + "z" * pad + value + "z" * (pad % 7))
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    by_file = {}
    for f in report["findings"]:
        by_file.setdefault(os.path.basename(f["path"]), []).append(f["line"])
    assert by_file == {f"p{pad:02d}.txt": [pad % 3 + 1] for pad in range(40)}


# --- more ways to be blind, and more ways to leak -----------------------------------------------

def test_clean_only_when_everything_was_seen(tmp_path):
    root = tmp_path / "root"
    write(str(root / "a.txt"), "nothing secret\n")
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: synthetic()})
    assert report["result"] == "clean"
    assert ls.exit_code(report) == ls.EXIT_CLEAN
    assert report["roots"][0]["canary"] == "found" and report["roots"][0]["blind"] == []


def test_secret_not_in_environment_is_unknown_not_clean(tmp_path):
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")
    report, _ = ls.scan([str(root)], names=[NAME, "SYNTH_ABSENT"], env={NAME: synthetic(),
                                                                       "SYNTH_EMPTY": ""})
    assert report["secrets"]["SYNTH_ABSENT"]["status"] == "unknown"
    assert report["secrets"][NAME]["status"] == "clean"
    assert report["result"] == "unknown"


def test_unreadable_file_is_unknown_not_clean(tmp_path, monkeypatch):
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")
    write(str(root / "locked.txt"), "content\n")
    real_open = ls._open_for_read

    def fake_open(path):
        if path.endswith("locked.txt"):
            raise PermissionError(13, "denied")
        return real_open(path)

    monkeypatch.setattr(ls, "_open_for_read", fake_open)
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: synthetic()})
    assert report["result"] == "unknown"
    assert report["roots"][0]["unreadable"] == [str(root / "locked.txt")]


def test_a_path_holding_the_value_is_withheld_and_the_value_is_never_printed(tmp_path):
    value = secrets.token_urlsafe(30)
    root = tmp_path / "root"
    write(str(root / ("named-" + value + ".txt")), "and inside " + value + "\n")
    code, out = run_cli(["--root", str(root), "--names", NAME], env={NAME: value})
    assert_never_printed(value, out)
    report = json.loads(out)
    assert report["result"] == "found" and code == ls.EXIT_FOUND
    assert report["findings"] and {f["path"] for f in report["findings"]} == {ls.WITHHELD}

def test_an_error_prints_its_type_only(tmp_path, monkeypatch):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")

    def boom(*a, **k):
        raise ValueError("could not parse " + value)

    monkeypatch.setattr(ls, "scan", boom)
    code, out = run_cli(["--root", str(root), "--names", NAME], env={NAME: value})
    assert code == ls.EXIT_UNKNOWN
    assert json.loads(out)["result"] == "unknown" and json.loads(out)["error"] == "ValueError"
    assert_never_printed(value, out)


def test_canary_only_reads_no_secret(tmp_path):
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")

    class Spy(dict):
        def get(self, k, d=None):
            raise AssertionError("canary-only must not read the environment")

    code, out = run_cli(["--root", str(root), "--canary-only"], env=Spy())
    assert code == ls.EXIT_CLEAN and json.loads(out)["result"] == "canary-ok"
    code, out = run_cli(["--root", str(tmp_path / "nope"), "--canary-only"], env=Spy())
    assert code == ls.EXIT_UNKNOWN


def test_state_file_round_trip_holds_no_value(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "x " + value + "\n")
    state = str(tmp_path / "state.json")
    code, _ = run_cli(["--root", str(root), "--names", NAME, "--state", state], env={NAME: value})
    assert code == ls.EXIT_FOUND
    with open(state, encoding="utf-8") as fh:
        assert_never_printed(value, fh.read())
    code, out = run_cli(["--root", str(root), "--names", NAME, "--state", state], env={NAME: value})
    assert json.loads(out)["mode"] == "incremental" and code == ls.EXIT_FOUND


def test_root_is_required_and_defaults_are_the_three_names():
    with pytest.raises(SystemExit):
        ls._parse([])
    assert ls.DEFAULT_NAMES == ("RAILWAY_API_TOKEN", "HOSTINGER_API_TOKEN", "BESTTIME_KEY")


# --- DOORS review of #45: F1 to F4 and the cheap "reads clean but leaks nothing" gaps -------------

def test_f1_a_value_pasted_mid_file_then_grown_is_found_on_the_next_incremental_run(tmp_path):
    value = synthetic(45)
    root = tmp_path / "root"
    note = root / "handoff.md"
    lines = [f"note line {i} with some filler text to make it long\n" for i in range(130)]
    write(str(note), "".join(lines))
    assert sum(len(x) for x in lines[:100]) > 4096  # the edit below sits past the first 4 KB
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, key=KEY)
    assert report["result"] == "clean"

    # Rewrite in place: a value pasted into the middle (line 101), and the note grew.
    lines[100] = "pasted: " + value + "\n"
    write(str(note), "".join(lines) + "a later line\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state, key=KEY)
    assert report["result"] == "found"
    assert [f["line"] for f in report["findings"]] == [101]


def test_f1_without_a_key_every_run_is_a_full_scan(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "nothing\n")
    _, state = ls.scan([str(root)], names=[NAME], env={NAME: value})  # no key
    assert state["files"] == {}
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state)
    assert report["mode"] == "full"


def test_f2_full_run_after_a_redaction_still_reports_the_find(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    leak = root / "leak.txt"
    write(str(leak), "x " + value + "\n")
    state = str(tmp_path / "state.json")
    argv = ["--root", str(root), "--names", NAME, "--state", state]
    code, _ = run_cli(argv, env={NAME: value})
    assert code == ls.EXIT_FOUND

    write(str(leak), "redacted\n")  # the file is cleaned, the secret has still left the machine
    code, out = run_cli(argv + ["--full"], env={NAME: value})
    assert code == ls.EXIT_FOUND and json.loads(out)["result"] == "found"
    code, out = run_cli(argv, env={NAME: value})  # and a later incremental run
    assert code == ls.EXIT_FOUND
    assert [f["new"] for f in json.loads(out)["findings"]] == [False]


def test_f2_a_shorter_names_list_keeps_the_other_names_findings(tmp_path):
    first, second = synthetic(), synthetic()
    root = tmp_path / "root"
    write(str(root / "leak.txt"), "x " + first + "\n")
    state = str(tmp_path / "state.json")
    env = {NAME: first, "SYNTH_TWO": second}
    code, _ = run_cli(["--root", str(root), "--names", NAME + ",SYNTH_TWO", "--state", state], env=env)
    assert code == ls.EXIT_FOUND
    code, out = run_cli(["--root", str(root), "--names", "SYNTH_TWO", "--state", state], env=env)
    report = json.loads(out)
    assert code == ls.EXIT_FOUND and report["secrets"][NAME]["status"] == "found"
    # Nothing was erased from the state either.
    code, out = run_cli(["--root", str(root), "--names", NAME + ",SYNTH_TWO", "--state", state], env=env)
    assert code == ls.EXIT_FOUND and json.loads(out)["secrets"][NAME]["status"] == "found"


def test_f2_findings_clear_only_on_request(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    leak = root / "leak.txt"
    write(str(leak), "x " + value + "\n")
    state = str(tmp_path / "state.json")
    argv = ["--root", str(root), "--names", NAME, "--state", state]
    run_cli(argv, env={NAME: value})
    write(str(leak), "redacted\n")
    code, out = run_cli(argv + ["--full", "--clear-findings"], env={NAME: value})
    assert code == ls.EXIT_CLEAN and json.loads(out)["findings"] == []


def test_f2_an_unusable_state_file_is_unknown_and_is_not_overwritten(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")
    state = tmp_path / "state.json"
    state.write_text("{ this is not json", encoding="utf-8")
    code, out = run_cli(["--root", str(root), "--names", NAME, "--state", str(state)], env={NAME: value})
    assert code == ls.EXIT_UNKNOWN and json.loads(out)["result"] == "unknown"
    assert state.read_text(encoding="utf-8") == "{ this is not json"  # earlier findings may be in it


def test_f3_the_state_holds_no_value_no_path_and_no_unkeyed_hash(tmp_path):
    import hashlib
    value = secrets.token_urlsafe(30)
    root = tmp_path / "root"
    named = root / ("named-" + value + ".txt")
    write(str(named), "and inside " + value + "\n")
    token = root / "token.txt"
    write(str(token), value + "\n")  # a file that is just the token
    write(str(root / "plain.txt"), "plain content here\n")
    state = tmp_path / "state.json"
    code, _ = run_cli(["--root", str(root), "--names", NAME, "--state", str(state)], env={NAME: value})
    assert code == ls.EXIT_FOUND
    text = state.read_text(encoding="utf-8")
    assert_never_printed(value, text, json.dumps(json.loads(text), ensure_ascii=False))
    for blob in (value + "\n", "plain content here\n"):
        for n in (len(blob), 4096):
            assert hashlib.sha256(blob.encode()[:n]).hexdigest() not in text, "an unkeyed hash is stored"
    assert "plain.txt" not in text and str(named) not in text, "a file path is stored in plain text"
    key = (tmp_path / "state.json.key").read_bytes()
    assert key.hex() not in text and len(key) == 32
    # And the finding for the path survives as a finding, with the path withheld.
    code, out = run_cli(["--root", str(root), "--names", NAME, "--state", str(state)], env={NAME: value})
    assert code == ls.EXIT_FOUND
    assert_never_printed(value, out, state.read_text(encoding="utf-8"))


def test_f3_a_bad_state_key_file_means_full_scans_not_a_wrong_skip(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")
    state = tmp_path / "state.json"
    (tmp_path / "state.json.key").write_bytes(b"short")
    argv = ["--root", str(root), "--names", NAME, "--state", str(state)]
    run_cli(argv, env={NAME: value})
    code, out = run_cli(argv, env={NAME: value})
    assert json.loads(out)["mode"] == "full" and code == ls.EXIT_CLEAN


def test_f4_an_existing_canary_named_file_is_never_overwritten_or_deleted(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    precious = root / ls.CANARY_FILE
    write(str(root / "a.txt"), "other content\n")
    write(str(precious), "a real note that holds the token " + value + "\n")
    before = precious.read_bytes()
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    assert precious.read_bytes() == before and precious.exists()
    assert report["result"] == "found"  # it was scanned like any other file, not skipped
    assert report["roots"][0]["canary"].startswith("not planted")
    assert "already exists" in report["roots"][0]["canary"]
    assert report["canary_removed"] is True  # nothing of ours to remove

    write(str(precious), "a real note, no token\n")
    before = precious.read_bytes()
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    assert report["result"] == "unknown" and report["secrets"][NAME]["status"] == "unknown"
    assert precious.read_bytes() == before


def test_f4_only_the_canary_this_run_created_is_removed(tmp_path):
    root_a, root_b = tmp_path / "a", tmp_path / "b"
    write(str(root_a / "x.txt"), "content\n")
    write(str(root_b / "y.txt"), "content\n")
    write(str(root_b / ls.CANARY_FILE), "keep me\n")
    ls.scan([str(root_a), str(root_b)], names=[NAME], env={NAME: synthetic()})
    assert not (root_a / ls.CANARY_FILE).exists()
    assert (root_b / ls.CANARY_FILE).read_text(encoding="utf-8") == "keep me\n"


def test_utf16_files_are_found(tmp_path):
    value = synthetic(33)
    root = tmp_path / "root"
    os.makedirs(root)
    for name, enc in (("le.txt", "utf-16"), ("be.txt", "utf-16-be"), ("le_nobom.txt", "utf-16-le")):
        with open(root / name, "wb") as fh:
            fh.write(("first\nsecret=" + value + "\nlast\n").encode(enc))
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    found = {os.path.basename(f["path"]): f for f in report["findings"]}
    assert set(found) == {"le.txt", "be.txt", "le_nobom.txt"}
    assert all(f["line"] == 2 for f in found.values())


def test_the_canary_proves_the_wrapped_base64_form(tmp_path, monkeypatch):
    root = tmp_path / "root"
    write(str(root / "log.txt"), "plenty of real content\n")
    monkeypatch.setattr(ls._Matcher, "_wrapped", lambda self, buf: iter(()))
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: synthetic()})
    assert report["roots"][0]["canary"] == "missing" and report["result"] == "unknown"


def test_the_canary_proves_the_utf16_forms(tmp_path, monkeypatch):
    root = tmp_path / "root"
    write(str(root / "log.txt"), "plenty of real content\n")
    real = ls._needles

    def blind(secret, value):
        return [n if not n.form.startswith("utf-16") else ls._Needle(secret, n.form, n.ident, b"\0never\0")
                for n in real(secret, value)]

    monkeypatch.setattr(ls, "_needles", blind)
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: synthetic()})
    assert report["roots"][0]["canary"] == "missing" and report["result"] == "unknown"


@pytest.mark.parametrize("eol", ["\n", "\r\n"])
@pytest.mark.parametrize("pad", [b"", b"x", b"xy"])
def test_base64_wrapped_at_76_columns_is_found(tmp_path, eol, pad):
    value = synthetic(41)
    blob = base64.b64encode(pad + b"filler" * 20 + value.encode() + b"tail" * 20).decode()
    wrapped = eol.join(blob[i:i + 76] for i in range(0, len(blob), 76))
    assert eol in wrapped
    root = tmp_path / "root"
    root.mkdir()
    with open(root / "mime.txt", "wb") as fh:
        fh.write(("Content-Transfer-Encoding: base64" + eol + wrapped + eol).encode())
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    assert report["result"] == "found"
    [hit] = report["findings"]
    assert hit["path"].endswith("mime.txt") and 2 <= hit["line"] <= 6 and hit["form"] == "base64"
    assert_never_printed(value, json.dumps(report))


def test_base64_wrapped_match_across_a_chunk_boundary_is_found_once(tmp_path, monkeypatch):
    monkeypatch.setattr(ls, "CHUNK", 32)
    value = synthetic(41)
    blob = base64.b64encode(b"pre" + value.encode() + b"post").decode()
    wrapped = "\n".join(blob[i:i + 20] for i in range(0, len(blob), 20))
    root = tmp_path / "root"
    for pad in range(8):
        write(str(root / f"w{pad}.txt"), "z" * pad + "\n" + wrapped + "\n")
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    assert sorted(os.path.basename(f["path"]) for f in report["findings"]) \
        == [f"w{pad}.txt" for pad in range(8)]


def test_json_escaped_slash_is_found(tmp_path):
    value = synthetic(40)
    assert "/" in value
    root = tmp_path / "root"
    escaped = json.dumps(value)[1:-1].replace("/", "\\/")
    write(str(root / "php.json"), '{"k": "' + escaped + '"}\n')
    write(str(root / "twice.json"), json.dumps({"o": '{"k": "' + escaped + '"}'}) + "\n")
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value})
    assert {os.path.basename(f["path"]) for f in report["findings"]} == {"php.json", "twice.json"}


def test_a_value_with_stray_whitespace_is_found_stripped(tmp_path):
    value = secrets.token_urlsafe(30)
    root = tmp_path / "root"
    write(str(root / "a.txt"), "token=" + value + "&x=1\n")
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value + "\r\n"})
    assert report["result"] == "found"
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: "   \n"})  # blank: nothing to search
    assert report["result"] != "found"


def test_a_value_in_a_file_or_folder_name_is_found_and_not_printed(tmp_path):
    value = secrets.token_urlsafe(30)
    root = tmp_path / "root"
    write(str(root / ("dir-" + value) / "inner.txt"), "plain\n")
    write(str(root / ("file-" + value + ".txt")), "plain\n")
    state = tmp_path / "state.json"
    code, out = run_cli(["--root", str(root), "--names", NAME, "--state", str(state)], env={NAME: value})
    assert code == ls.EXIT_FOUND
    assert_never_printed(value, out, state.read_text(encoding="utf-8"))
    report = json.loads(out)
    assert report["secrets"][NAME]["status"] == "found"
    assert {f["path"] for f in report["findings"]} == {ls.WITHHELD}


def test_excludes_and_what_is_not_looked_for_are_in_the_report(tmp_path):
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")
    write(str(root / "t.jsonl"), "content\n")
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: synthetic()}, excludes=["*.jsonl"])
    assert report["excludes"] == ["*.jsonl"] and report["roots"][0]["excludes"] == ["*.jsonl"]
    assert "*.jsonl" in report["secrets"][NAME]["why"]
    joined = " ".join(report["not_looked_for"]).lower()
    for gap in ("compressed", "git", "truncated", "empty folder"):
        assert gap in joined, gap
    forms = " ".join(report["forms"])
    for form in ("raw", "base64", "hex", "url", "json", "utf-16le", "utf-16be", "wrapped", "names"):
        assert form in forms, form
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: synthetic()})
    assert report["excludes"] == [] and "no --exclude" in report["secrets"][NAME]["why"]


def test_an_unreadable_folder_is_unknown_not_clean(tmp_path, monkeypatch):
    root = tmp_path / "root"
    write(str(root / "a.txt"), "content\n")
    real_walk = os.walk

    def walk(top, onerror=None, **kw):
        if onerror:
            onerror(PermissionError(13, "denied", os.path.join(top, "locked")))
        return real_walk(top, onerror=onerror, **kw)

    monkeypatch.setattr(ls.os, "walk", walk)
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: synthetic()})
    assert report["result"] == "unknown"
    assert report["roots"][0]["unreadable"] == [os.path.join(str(root), "locked")]


def test_no_network_and_no_process_code():
    with open(_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module)
    allowed = {"__future__", "argparse", "base64", "fnmatch", "hashlib", "hmac", "json", "os",
               "re", "secrets", "sys", "dataclasses", "datetime", "urllib.parse",
               "ctypes"}  # ctypes: only to set the key file's ACL, see the test below
    assert imported <= allowed, sorted(imported - allowed)
    calls = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not calls & {"system", "popen", "startfile", "spawnl", "execv", "putenv", "unsetenv"}


# --- DOORS re-review of #45 at 7bd51c75: F5, F6 and the follow-ups --------------------------------

def _state_text(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def test_f5_a_rotated_value_written_before_the_env_changed_is_found_on_the_incremental_run(tmp_path):
    old, new = synthetic(41), synthetic(43)
    root = tmp_path / "root"
    note = root / "transcript.jsonl"
    write(str(note), "".join(f"filler line {i}\n" for i in range(50)))
    state = str(tmp_path / "state.json")
    argv = ["--root", str(root), "--names", NAME, "--state", state]
    code, out = run_cli(argv, env={NAME: old})
    assert code == ls.EXIT_CLEAN

    # The new token is pasted into the note BEFORE the environment holds it; a scheduled run goes
    # past it (honestly clean: the new value is not the one it was given yet).
    with open(note, "a", encoding="utf-8", newline="\n") as fh:
        fh.write("rotated: " + new + "\n")
    code, out = run_cli(argv, env={NAME: old})
    assert code == ls.EXIT_CLEAN

    # Then the environment is updated. The bytes already passed were never searched for this value.
    code, out = run_cli(argv, env={NAME: new})
    report = json.loads(out)
    assert code == ls.EXIT_FOUND and report["result"] == "found"
    assert [f["line"] for f in report["findings"]] == [51]
    assert_never_printed(new, out, _state_text(state))
    assert_never_printed(old, out, _state_text(state))


def test_f5_a_value_that_comes_back_into_the_environment_rescans_from_the_start(tmp_path):
    first, second = synthetic(41), synthetic(43)
    root = tmp_path / "root"
    write(str(root / "a.txt"), "x " + second + "\n")
    _, state = ls.scan([str(root)], names=[NAME, "SYNTH_TWO"], env={NAME: first}, key=KEY)
    # SYNTH_TWO was absent (unknown). Now it is set: the same names, new values.
    report, _ = ls.scan([str(root)], names=[NAME, "SYNTH_TWO"], env={NAME: first, "SYNTH_TWO": second},
                        state=state, key=KEY)
    assert report["secrets"]["SYNTH_TWO"]["status"] == "found"


def test_f5_unchanged_values_still_resume_and_a_changed_form_list_does_not(tmp_path, monkeypatch):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "".join(f"line {i}\n" for i in range(200)))
    _, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, key=KEY)
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state, key=KEY)
    assert report["mode"] == "incremental" and report["files_resumed"] == 1  # the guard is not a no-op
    assert report["roots"][0]["bytes_scanned"] == 0

    monkeypatch.setattr(ls, "FORMS", ls.FORMS + ("a form added later",))
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state, key=KEY)
    assert report["files_resumed"] == 0 and report["roots"][0]["bytes_scanned"] > 0


def test_f5_the_value_fingerprint_is_not_in_the_state(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "plain\n")
    state = tmp_path / "state.json"
    run_cli(["--root", str(root), "--names", NAME, "--state", str(state)], env={NAME: value})
    text = state.read_text(encoding="utf-8")
    assert_never_printed(value, text)
    assert "needle" not in text.lower() and "digest" not in text.lower()


def test_f6_clearing_findings_forces_a_full_rescan(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "leak.txt"), "x " + value + "\n")
    state = str(tmp_path / "state.json")
    argv = ["--root", str(root), "--names", NAME, "--state", state]
    code, _ = run_cli(argv, env={NAME: value})
    assert code == ls.EXIT_FOUND
    # The value is still on disk. Clearing the old findings must not make the next run clean.
    code, out = run_cli(argv + ["--clear-findings"], env={NAME: value})
    report = json.loads(out)
    assert code == ls.EXIT_FOUND and report["mode"] == "full"
    assert [f["new"] for f in report["findings"]] == [True]
    code, out = run_cli(argv, env={NAME: value})  # and the run after it
    assert code == ls.EXIT_FOUND


def test_f6_clearing_findings_after_a_real_redaction_is_clean(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    leak = root / "leak.txt"
    write(str(leak), "x " + value + "\n")
    state = str(tmp_path / "state.json")
    argv = ["--root", str(root), "--names", NAME, "--state", state]
    run_cli(argv, env={NAME: value})
    write(str(leak), "redacted\n")
    code, out = run_cli(argv + ["--clear-findings"], env={NAME: value})
    assert code == ls.EXIT_CLEAN and json.loads(out)["findings"] == []


def test_fu1_a_root_given_twice_is_scanned_once_and_leaves_no_canary(tmp_path):
    value = synthetic()
    root = tmp_path / "root"
    write(str(root / "a.txt"), "plain content\n")
    spellings = [str(root), str(root) + os.sep, str(root / "."), str(root / ".." / "root")]
    report, _ = ls.scan(spellings, names=[NAME], env={NAME: value})
    assert not (root / ls.CANARY_FILE).exists(), "the canary was left behind"
    assert report["canary_removed"] is True
    assert len(report["roots"]) == 1 and report["result"] == "clean"
    code, out = run_cli(["--root", str(root), "--root", str(root), "--names", NAME], env={NAME: value})
    assert code == ls.EXIT_CLEAN and not (root / ls.CANARY_FILE).exists()


def test_fu2_a_key_file_that_cannot_be_protected_is_not_used_and_is_removed(tmp_path, monkeypatch):
    state = str(tmp_path / "state.json")
    monkeypatch.setattr(ls, "_protect_key_file", lambda path: False)
    assert ls._load_key(state) is None
    assert not os.path.exists(state + ".key")  # an unprotected key must not stay on disk


def test_fu2_the_key_file_is_protected_before_the_key_is_written(tmp_path, monkeypatch):
    state = str(tmp_path / "state.json")
    seen = []
    real = ls._protect_key_file

    def spy(path):
        seen.append(os.path.getsize(path))  # empty at this point: the key is not yet exposed
        return real(path)

    monkeypatch.setattr(ls, "_protect_key_file", spy)
    key = ls._load_key(state)
    assert key is not None and len(key) == 32 and seen == [0]


def test_fu2_an_existing_key_file_is_protected_again_on_every_load(tmp_path, monkeypatch):
    state = str(tmp_path / "state.json")
    assert ls._load_key(state) is not None
    calls = []
    monkeypatch.setattr(ls, "_protect_key_file", lambda path: calls.append(path) or False)
    assert ls._load_key(state) is None and calls  # cannot be shown private: not used
    assert os.path.exists(state + ".key")  # not ours to delete on a load


@pytest.mark.skipif(os.name != "nt", reason="the Windows ACL")
def test_fu2_on_windows_the_key_file_acl_is_the_current_user_only(tmp_path):
    import subprocess  # the test may start a process; the module under test must not
    state = str(tmp_path / "state.json")
    assert ls._load_key(state) is not None
    out = subprocess.run(["icacls", state + ".key"], capture_output=True, text=True).stdout
    assert out.count(":(") == 1, out  # exactly one entry
    assert "(I)" not in out, out  # nothing inherited from the folder
    assert "(F)" in out and os.environ["USERNAME"].lower() in out.lower(), out


def test_ctypes_is_used_only_to_set_the_key_files_acl():
    with open(_PATH, encoding="utf-8") as fh:
        tree = ast.parse(fh.read())
    owner = {}
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef):
            for node in ast.walk(fn):
                owner[id(node)] = fn.name
    outside = [n.lineno for n in ast.walk(tree)
               if isinstance(n, ast.Name) and n.id in ("ctypes", "wintypes")
               and owner.get(id(n)) != "_restrict_to_user"]
    assert not outside, outside
    called = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)
              and isinstance(n.value, ast.Name) and n.value.id in ("adv", "k32")}
    assert called <= {"ConvertStringSecurityDescriptorToSecurityDescriptorW", "GetSecurityDescriptorDacl",
                      "SetNamedSecurityInfoW", "OpenProcessToken", "GetTokenInformation",
                      "ConvertSidToStringSidW", "GetCurrentProcess", "CloseHandle", "LocalFree"}, called


def test_fu3_a_second_file_named_after_the_value_is_its_own_new_finding(tmp_path):
    value = secrets.token_urlsafe(30)
    root = tmp_path / "root"
    write(str(root / ("a-" + value + ".txt")), "plain\n")
    write(str(root / ("b-" + value + ".txt")), "plain\n")
    state = str(tmp_path / "state.json")
    argv = ["--root", str(root), "--names", NAME, "--state", state]
    code, out = run_cli(argv, env={NAME: value})
    first = json.loads(out)["findings"]
    assert code == ls.EXIT_FOUND and [f["new"] for f in first] == [True, True]
    code, out = run_cli(argv, env={NAME: value})
    assert [f["new"] for f in json.loads(out)["findings"]] == [False, False]
    write(str(root / ("c-" + value + ".txt")), "plain\n")
    code, out = run_cli(argv, env={NAME: value})
    findings = json.loads(out)["findings"]
    assert sorted(f["new"] for f in findings) == [False, False, True]
    assert_never_printed(value, out, _state_text(state))


def test_fu3_without_a_key_two_withheld_findings_still_count_two(tmp_path):
    value = secrets.token_urlsafe(30)
    root = tmp_path / "root"
    write(str(root / ("a-" + value + ".txt")), "plain\n")
    write(str(root / ("b-" + value + ".txt")), "plain\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value})  # no key
    assert [f["new"] for f in report["findings"]] == [True, True]
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state)
    assert [f["new"] for f in report["findings"]] == [False, False]
    write(str(root / ("c-" + value + ".txt")), "plain\n")
    report, _ = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state)
    assert sorted(f["new"] for f in report["findings"]) == [False, False, True]


def test_fu4_a_value_in_one_path_withholds_only_that_path(tmp_path):
    named, content = secrets.token_urlsafe(30), secrets.token_urlsafe(31)
    root = tmp_path / "root"
    bad = root / ("named-" + named + ".txt")
    write(str(bad), "plain\n")
    write(str(root / "other.txt"), "a line " + content + "\n")
    env = {NAME: named, "SYNTH_TWO": content}
    code, out = run_cli(["--root", str(root), "--names", NAME + ",SYNTH_TWO"], env=env)
    report = json.loads(out)
    assert code == ls.EXIT_FOUND and "withheld" not in report and "roots" in report
    by_secret = {f["secret"]: f for f in report["findings"]}
    assert by_secret[NAME]["path"] == ls.WITHHELD
    assert by_secret["SYNTH_TWO"]["path"].endswith("other.txt")
    assert_never_printed(named, out)
    assert_never_printed(content, out)  # the second value is in a path nowhere in the report


def test_fu4_a_value_in_the_root_path_itself_prints_nothing_but_still_reports(tmp_path):
    value = secrets.token_urlsafe(30)
    root = tmp_path / ("root-" + value)
    write(str(root / "a.txt"), "x " + value + "\n")
    code, out = run_cli(["--root", str(root), "--names", NAME], env={NAME: value})
    assert code == ls.EXIT_FOUND and json.loads(out)["result"] == "found"
    assert_never_printed(value, out)
