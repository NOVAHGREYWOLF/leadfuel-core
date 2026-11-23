"""WATCH: the approval-mail check says FAIL for a misfiled mail and UNKNOWN, never PASS, when it
cannot see the mail or its folder."""
import importlib.util
import json
import os

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "approval_mail_check.py")
_spec = importlib.util.spec_from_file_location("approval_mail_check", _PATH)
amc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(amc)


def mail(folder="Inbox", **kw):
    m = {"id": "m1", "sender": "hello@mail.leadfuel.cloud",
         "subject": "Approve spend: 11 asks - up to $0.82 total", "folder": folder}
    m.update(kw)
    return m


def test_inbox_passes():
    assert amc.judge([mail()])[0] == "PASS"


def test_misfiled_fails():
    assert amc.judge([mail("Archive/Hub")])[0] == "FAIL"


def test_one_misfiled_among_good_fails():
    assert amc.judge([mail(), mail("Hub", id="m2")])[0] == "FAIL"


def test_no_folder_is_unknown():
    assert amc.judge([mail(folder=None)])[0] == "UNKNOWN"


def test_no_approval_mail_is_unknown_not_pass():
    other = mail(subject="Your command book", sender="prime@mail.leadfuel.cloud")
    assert amc.judge([other])[0] == "UNKNOWN"
    assert amc.judge([])[0] == "UNKNOWN"
    assert amc.judge(None)[0] == "UNKNOWN"


def test_cli_exit_codes(tmp_path):
    p = tmp_path / "e.json"
    p.write_text(json.dumps([mail("Junk")]))
    assert amc.main(["--evidence", str(p)]) == 1
    p.write_text(json.dumps([mail()]))
    assert amc.main(["--evidence", str(p)]) == 0
    assert amc.main(["--evidence", str(tmp_path / "missing.json")]) == 2
