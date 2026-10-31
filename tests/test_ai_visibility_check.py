import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts" / "ai_visibility"))
import check  # noqa: E402


def test_questions_are_ten_and_draft():
    d = check.load_questions()
    assert len(d["questions"]) == 10 and d["status"] == "DRAFT"


def test_dry_run_sends_nothing(monkeypatch):
    def boom(q):
        raise AssertionError("sent")

    monkeypatch.setitem(check.ADAPTERS, "x", boom)
    rec = check.run(check.load_questions(), live=False, assistant="x", approval=None)
    assert rec["mode"] == "dry-run" and all("answer" not in r for r in rec["results"])


def test_live_refused_without_approval(tmp_path):
    assert check.main(["--live", "--assistant", "x", "--approval", str(tmp_path / "none.json")]) == 2


def test_live_refused_bad_card_or_assistant(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"approved": True, "card_id": "nope", "assistants": ["x"]}))
    assert check.main(["--live", "--assistant", "x", "--approval", str(p)]) == 2
    p.write_text(json.dumps({"approved": True, "card_id": "q1", "assistants": ["y"]}))
    assert check.main(["--live", "--assistant", "x", "--approval", str(p)]) == 2


def test_approved_but_no_adapter_sends_nothing(tmp_path):
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"approved": True, "card_id": "q1", "assistants": ["x"]}))
    assert check.main(["--live", "--assistant", "x", "--approval", str(p)]) == 2


def test_live_with_fake_adapter_scores_and_stores(tmp_path, monkeypatch):
    monkeypatch.setitem(check.ADAPTERS, "fake", lambda q: "ETG and LeadFuel")
    p = tmp_path / "a.json"
    p.write_text(json.dumps({"approved": True, "card_id": "q9", "assistants": ["fake"]}))
    rec = check.run(check.load_questions(), live=True, assistant="fake", approval=p)
    assert rec["card_id"] == "q9" and rec["results"][0]["mentioned"]
    path = check.store(rec, tmp_path)
    assert path.is_file() and "q9" in check.history(tmp_path)[0]
