"""WATCH: the weekly synthetic and the stuck-session detector must say UNKNOWN, never PASS or none,
when delivery or the card record cannot be established. Fixtures are fake transcripts under tmp_path."""
import importlib.util
import json
import os
import time

_PATH = os.path.join(os.path.dirname(__file__), os.pardir, "watch", "owner_touch_checks.py")
_spec = importlib.util.spec_from_file_location("owner_touch_checks", _PATH)
otc = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(otc)

GOOD = {"card_id": "q-synth-1", "push": "confirmed", "answer_delivered": True, "human_touches": 0}


def test_all_confirmed_passes():
    assert otc.judge_synthetic(GOOD)[0] == "PASS"


def test_push_only_requested_is_unknown_not_pass():
    assert otc.judge_synthetic(dict(GOOD, push="requested"))[0] == "UNKNOWN"


def test_missing_fields_are_unknown():
    for k in ("push", "answer_delivered", "human_touches"):
        ev = {x: y for x, y in GOOD.items() if x != k}
        assert otc.judge_synthetic(ev)[0] == "UNKNOWN", k
    assert otc.judge_synthetic(None)[0] == "UNKNOWN"
    assert otc.judge_synthetic({})[0] == "UNKNOWN"


def test_owner_typing_or_failed_delivery_fails():
    assert otc.judge_synthetic(dict(GOOD, human_touches=1))[0] == "FAIL"
    assert otc.judge_synthetic(dict(GOOD, answer_delivered=False))[0] == "FAIL"
    assert otc.judge_synthetic(dict(GOOD, push="failed"))[0] == "FAIL"
    assert otc.judge_synthetic(dict(GOOD, human_touches=True))[0] == "UNKNOWN"


def test_synthetic_cli_exit_codes(tmp_path):
    p = tmp_path / "e.json"
    p.write_text(json.dumps(GOOD), encoding="utf-8")
    assert otc.main(["synthetic", "--evidence", str(p)]) == 0
    assert otc.main(["synthetic", "--evidence", str(tmp_path / "nope.json")]) == 2


def _session(root, sid, event, idle_minutes):
    d = root / "p"
    d.mkdir(parents=True, exist_ok=True)
    f = d / (sid + ".jsonl")
    f.write_text(json.dumps(event) + "\n", encoding="utf-8")
    t = time.time() - idle_minutes * 60
    os.utime(f, (t, t))


def _ask(text="shall I go on?"):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": text}]}}


def test_stuck_found_and_card_behind_it_clears_it(tmp_path):
    _session(tmp_path, "s-stuck", _ask(), 90)
    _session(tmp_path, "s-card", _ask(), 90)
    _session(tmp_path, "s-fresh", _ask(), 1)
    _session(tmp_path, "s-done", _ask("all done."), 90)
    verdict, n, ids, _ = otc.find_stuck(str(tmp_path), 30, {"s-card"})
    assert (verdict, n, ids) == ("FAIL", 4, ["s-stuck"])


def test_ask_user_question_tool_counts_as_waiting(tmp_path):
    ev = {"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "AskUserQuestion"}]}}
    _session(tmp_path, "s1", ev, 90)
    assert otc.find_stuck(str(tmp_path), 30, set())[2] == ["s1"]


def test_no_card_record_is_unknown_not_none_stuck(tmp_path):
    _session(tmp_path, "s1", _ask(), 90)
    assert otc.find_stuck(str(tmp_path), 30, None)[0] == "UNKNOWN"
    assert otc.main(["stuck", "--root", str(tmp_path)]) == 2


def test_empty_root_is_unknown(tmp_path):
    assert otc.find_stuck(str(tmp_path), 30, set())[0] == "UNKNOWN"


def test_clean_root_passes_and_output_has_ids_only(tmp_path, capsys):
    _session(tmp_path, "s1", _ask("finished."), 90)
    cards = tmp_path / "c.json"
    cards.write_text("[]", encoding="utf-8")
    assert otc.main(["stuck", "--root", str(tmp_path), "--cards", str(cards)]) == 0
    assert "PASS" in capsys.readouterr().out
