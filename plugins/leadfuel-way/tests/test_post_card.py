"""post_card.py: a session posts its own card on the Router desk, shaped like the live cards, with option X always
present and the asker's own session id on it so the wake pass can carry the owner's click back.

The field list is read from two live cards (q9013 and q9123, 2026-11-01); the X rule is the owner's, 2026-10-30.
"""
from __future__ import annotations

import json
import subprocess
import sys

import pytest

from kit import PLUGIN, load_module

SCRIPT = PLUGIN / "scripts" / "post_card.py"
ME = "local_17e8ba63-4dd2-4846-8c8a-629b9c3750b2"
LIVE_FIELDS = {"id", "n", "kind", "title", "asker", "asker_session", "posted", "why", "plain", "check", "options",
               "default", "default_reason", "answer", "routed"}


@pytest.fixture(scope="module")
def pc():
    return load_module(SCRIPT, "post_card_under_test")


def build(pc, **over):
    args = dict(n=9124, asker="NODE · full system automation part · 4", asker_session=ME, title="Should it?",
                say="Make it so?", why="Because.", check="verified: read the code.",
                options=[("A", "Yes"), ("B", "No")], default="A", default_reason="Safer.")
    args.update(over)
    return pc.build_card(**args)


def test_a_card_has_exactly_the_live_fields_and_starts_unanswered(pc):
    c = build(pc)
    assert set(c) == LIVE_FIELDS
    assert c["id"] == "q9124" and c["n"] == 9124 and c["kind"] == "choice"
    assert c["answer"] is None and c["routed"] is None
    assert c["asker_session"] == ME and c["plain"] == {"say": "Make it so?"}
    assert c["posted"].endswith("NODE · full system automation part · 4")


def test_option_x_is_always_added_last_and_the_default_is_not_x(pc):
    c = build(pc)
    assert [o["key"] for o in c["options"]] == ["A", "B", "X"]
    assert c["options"][-1]["label"].startswith("None of these: something else")


def test_a_given_x_label_is_kept_not_duplicated(pc):
    c = build(pc, options=[("A", "Yes"), ("B", "No"), ("x", "Neither: say what you want")])
    assert [o["key"] for o in c["options"]] == ["A", "B", "X"] and c["options"][-1]["label"] == "Neither: say what you want"


@pytest.mark.parametrize("over", [
    {"default": "X"}, {"default": "C"}, {"options": [("A", "Only one")]}, {"options": [("A", "a"), ("A", "b")]},
    {"options": [("AB", "a"), ("B", "b")]}, {"asker_session": "ROUTER #5"}, {"asker_session": ""}, {"n": 0},
    {"title": "x" * 141}, {"check": ""}, {"default_reason": " "}, {"kind": "poll"},
    {"guide": ["step one"]},
])
def test_a_card_that_would_break_a_rule_is_refused(pc, over):
    with pytest.raises(pc.CardError):
        build(pc, **over)


def test_a_step_card_carries_its_guide_and_links(pc):
    c = build(pc, kind="step", guide=["Open the app.", "  Set Bypass. "], links=[("Router desk", "https://example.test/x")],
              effects={"a": "done"})
    assert c["guide"] == ["Open the app.", "Set Bypass."] and c["links"] == [{"label": "Router desk", "url": "https://example.test/x"}]
    assert c["plain"]["effects"] == {"A": "done"}


def test_the_card_names_no_token_secret_or_path(pc):
    assert "WAKE-" not in json.dumps(build(pc))


def test_the_script_has_no_network_and_no_page_access():
    import ast
    tree = ast.parse(SCRIPT.read_text(encoding="utf-8"))
    imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert not imported & {"socket", "http", "urllib", "requests", "httpx", "smtplib", "ftplib", "subprocess", "webbrowser"}


def _run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *map(str, args)], capture_output=True, text=True,
                          encoding="utf-8", timeout=60)


def test_cli_writes_the_file_and_says_what_to_do_next(tmp_path):
    out = tmp_path / "c" / "card.json"
    run = _run("--n", 9124, "--asker", "NODE · x part · 4", "--asker-session", ME, "--title", "T", "--say", "S", "--why", "W",
               "--check", "verified: me", "--option", "A=Yes", "--option", "B=No", "--default", "A",
               "--default-reason", "R", "--out", out)
    assert run.returncode == 0, run.stderr
    assert "ArtifactData set" in run.stdout and "n=9125" in run.stdout
    assert json.loads(out.read_text(encoding="utf-8"))["options"][-1]["key"] == "X"


def test_cli_refuses_with_a_clear_line_and_writes_nothing(tmp_path):
    out = tmp_path / "card.json"
    run = _run("--n", 1, "--asker", "a", "--asker-session", "not-a-session", "--title", "T", "--say", "S", "--why", "W",
               "--check", "c", "--option", "A=Yes", "--option", "B=No", "--default", "A", "--default-reason", "R", "--out", out)
    assert run.returncode == 2 and run.stdout.startswith("CARD-NOT-BUILT") and not out.exists()


def test_the_desk_and_router_skills_teach_the_asker_posts_its_own_card():
    desk = (PLUGIN / "skills" / "desk" / "SKILL.md").read_text(encoding="utf-8")
    router = (PLUGIN / "skills" / "router" / "SKILL.md").read_text(encoding="utf-8")
    for text in (desk, router):
        assert "post_card.py" in text and "AskUserQuestion" in text and "chip" in text
    assert "Post the card yourself" in desk
    assert "posts its own card" in router
    assert (PLUGIN / "scripts" / "post_card.py").is_file()


def test_the_router_and_handoff_skills_teach_the_pinned_router_current_rewrite():
    """Owner, 2026-11-01, card q9126 A: router/current is rewritten on every rotation, pinned with if_version."""
    router = (PLUGIN / "skills" / "router" / "SKILL.md").read_text(encoding="utf-8")
    handoff = (PLUGIN / "skills" / "handoff" / "SKILL.md").read_text(encoding="utf-8")
    for text in (router, handoff):
        assert "router/current" in text and "if_version" in text and "session_id" in text and "q9126" in text
    assert "Rewrite `router/current`" in router and "rewrites the Build Board `router/current` on every rotation" in handoff
