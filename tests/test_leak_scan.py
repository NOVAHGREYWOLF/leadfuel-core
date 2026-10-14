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
    return secrets.token_urlsafe(n)[:n - 6] + '+/"\\=x'


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

    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value})
    assert report["result"] == "clean" and report["mode"] == "full"
    first_size = log.stat().st_size
    assert state["files"][os.path.abspath(str(log))]["offset"] == first_size

    # Append the rest of the value (straddling the old end), more lines, and a second copy.
    with open(log, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(value[half:] + " end\nmore\nagain " + value + "\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state)
    assert report["mode"] == "incremental"
    assert report["roots"][0]["bytes_scanned"] == log.stat().st_size - first_size
    assert [(f["line"], f["new"]) for f in report["findings"]] == [(21, True), (23, True)]

    # Nothing appended: nothing new, the old findings still reported, and not blind.
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state)
    assert report["roots"][0]["bytes_scanned"] == 0
    assert report["roots"][0]["bytes_covered"] == log.stat().st_size
    assert [(f["line"], f["new"]) for f in report["findings"]] == [(21, False), (23, False)]
    assert report["result"] == "found"

    # A file rewritten in place (its head changed) is scanned again from the start.
    other = root / "other.txt"
    write(str(other), "x" * 100 + "\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state)
    write(str(other), value + "y" * 100 + "\n")
    report, state = ls.scan([str(root)], names=[NAME], env={NAME: value}, state=state)
    assert any(f["path"] == str(other) and f["line"] == 1 for f in report["findings"])

    # A new secret name means the offsets do not apply: a full scan.
    report, _ = ls.scan([str(root)], names=[NAME, "SYNTH_OTHER"],
                        env={NAME: value, "SYNTH_OTHER": synthetic()}, state=state)
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


def test_value_in_a_path_withholds_every_path(tmp_path):
    value = secrets.token_urlsafe(30)
    root = tmp_path / "root"
    write(str(root / ("named-" + value + ".txt")), "and inside " + value + "\n")
    code, out = run_cli(["--root", str(root), "--names", NAME], env={NAME: value})
    assert_never_printed(value, out)
    report = json.loads(out)
    assert "withheld" in report and "findings" not in report
    assert report["result"] == "found" and code == ls.EXIT_FOUND


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
               "re", "secrets", "sys", "dataclasses", "datetime", "urllib.parse"}
    assert imported <= allowed, sorted(imported - allowed)
    calls = {n.func.attr for n in ast.walk(tree)
             if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
    assert not calls & {"system", "popen", "startfile", "spawnl", "execv", "putenv", "unsetenv"}
