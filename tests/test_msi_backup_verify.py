import io
import json
import shutil
import subprocess

import pytest

from node import msi_backup_verify as m

SRC = "D-Photo\t10\t1000\nUsers-x\t5\t500\n# END 2\n"


def test_match_is_complete():
    r = m.compare(SRC, SRC)
    assert r["overall"] == "COMPLETE" and r["wipe_allowed"] is False


def test_short_and_missing_are_incomplete():
    r = m.compare(SRC, "D-Photo\t9\t900\n# END 1\n")
    v = {x["folder"]: x["verdict"] for x in r["folders"]}
    assert v == {"D-Photo": "SHORT", "Users-x": "MISSING"} and r["overall"] == "INCOMPLETE"


def test_extra_bytes_not_complete():
    r = m.compare(SRC, "D-Photo\t10\t1001\nUsers-x\t5\t500\n# END 2\n")
    assert r["overall"] == "INCOMPLETE"


def test_empty_or_truncated_listing_is_unknown_not_complete():
    assert m.compare("", "")["overall"] == "UNKNOWN"
    assert m.compare(SRC, "D-Photo\t10\t1000\n")["overall"] == "UNKNOWN"
    assert m.compare(SRC, "D-Photo\t10\t1000\n# END 5\n")["overall"] == "UNKNOWN"
    assert m.compare("D-Photo\t10\t1000\n", SRC)["overall"] == "UNKNOWN"


def test_zero_file_source_is_unknown():
    r = m.compare("D-Photo\t0\t0\n# END 1\n", "D-Photo\t0\t0\n# END 1\n")
    assert r["overall"] == "UNKNOWN"


def test_garbage_line_is_unknown():
    assert m.compare("D-Photo\tten\t1\n# END 1\n", SRC)["overall"] == "UNKNOWN"


def test_duplicate_folder_is_unknown():
    r = m.compare("D-Photo\t1\t1\nD-Photo\t1\t1\n# END 2\n", "D-Photo\t1\t1\n# END 1\n")
    assert r["overall"] == "UNKNOWN"


def test_target_only_folder_reported_not_failing():
    r = m.compare(SRC, SRC.replace("# END 2", "old\t1\t1\n# END 3"))
    assert r["overall"] == "COMPLETE" and r["target_only_folders"] == ["old"]


def test_tolerance_needs_equal_bytes():
    t = "D-Photo\t9\t1000\nUsers-x\t5\t500\n# END 2\n"
    assert m.compare(SRC, t)["overall"] == "INCOMPLETE"
    assert m.compare(SRC, t, 1)["overall"] == "COMPLETE"
    assert m.compare(SRC, t.replace("1000", "999"), 1)["overall"] == "INCOMPLETE"


def test_plan_target_refuses_bad_root():
    for bad in ("rel/path", "/a/../b", "/a b", "/a;rm -rf /", "/a$(x)", "/a//b", ""):
        with pytest.raises(m.Refused):
            m.plan_target(bad)


def test_plans_are_read_only():
    text = m.plan_source() + m.plan_target("/mnt/x/y")
    code = "\n".join(ln for ln in text.splitlines() if not ln.lstrip().startswith("#"))
    for verb in ("rm ", "mv ", "cp ", "rsync", "scp", "Remove-Item", "Copy-Item", "Move-Item", "curl", "wget", "du ", "dd "):
        assert verb not in code
    assert "-printf" in code and "Get-ChildItem" in code


@pytest.mark.skipif(shutil.which("sh") is None or shutil.which("find") is None, reason="needs sh and GNU find")
def test_target_script_runs_and_counts(tmp_path):
    (tmp_path / "A").mkdir()
    (tmp_path / "A" / "f1").write_bytes(b"x" * 10)
    (tmp_path / "A" / "f2").write_bytes(b"y" * 5)
    (tmp_path / "B").mkdir()
    root = str(tmp_path).replace("\\", "/")
    if not m.PATH_RX.fullmatch(root):
        pytest.skip("tmp path has characters the plan refuses")
    out = subprocess.run(["sh", "-c", m.plan_target(root)], capture_output=True, text=True).stdout
    parsed, problems = m.parse_listing(out)
    if "A" not in parsed["folders"]:
        pytest.skip("this sh/find cannot run the plan")
    assert parsed["folders"] == {"A": (2, 15), "B": (0, 0)} and not problems


def test_cli_verify_writes_once_and_never_overwrites(tmp_path):
    s, t, o = tmp_path / "s", tmp_path / "t", tmp_path / "o.json"
    s.write_text(SRC)
    t.write_text(SRC)
    assert m.main(["verify", "--source", str(s), "--target", str(t), "--out", str(o)], out=io.StringIO()) == 0
    assert json.loads(o.read_text())["overall"] == "COMPLETE"
    assert m.main(["verify", "--source", str(s), "--target", str(t), "--out", str(o)], out=io.StringIO()) == 2


def test_cli_missing_file_is_unknown(tmp_path):
    s = tmp_path / "s"
    s.write_text(SRC)
    assert m.main(["verify", "--source", str(s), "--target", str(tmp_path / "nope")], out=io.StringIO()) == 3


def test_cli_reads_utf16_source(tmp_path):
    s, t = tmp_path / "s", tmp_path / "t"
    s.write_bytes(SRC.replace("\n", "\r\n").encode("utf-16"))
    t.write_text(SRC)
    assert m.main(["verify", "--source", str(s), "--target", str(t)], out=io.StringIO()) == 0


def test_module_has_no_network_or_delete_calls():
    src = open(m.__file__, encoding="utf-8").read()
    for bad in ("socket", "urllib", "requests", "subprocess", "os.remove", "shutil.rmtree", "os.unlink"):
        assert bad not in src.split('"""', 2)[2]
