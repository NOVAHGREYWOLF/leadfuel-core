"""Autopilot (WAY-AUTOPILOT-1, 0.1.16): OFF by default, hard gates denied outright when on, nothing
leaves the machine unless the owner allowed that kind, no new desk before the checkpoint card or at
weekly usage >= 88% or unknown, and every denial lands in the audit log."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time

import pytest

from kit import PLUGIN, event, load_module, title_rec

GATE = load_module(PLUGIN / "hooks" / "autopilot.py", "autopilot_under_test")
CLI = PLUGIN / "scripts" / "way_autopilot.py"
ROUTER = "ROUTER #7 · leadfuel offer"
DESK = "NODE · leadfuel offer part · 5"
OTHER = "NODE · reports part · 2"


def state_dir(tmp_path):
    return tmp_path / "state"


def write_state(tmp_path, **cfg):
    d = state_dir(tmp_path)
    d.mkdir(parents=True, exist_ok=True)
    base = {"on": True, "approved_card": "q900", "expires": time.time() + 86400, "allow": [],
            "checkpoint_card": "q901", "usage": {"weekly_pct": 40, "at": time.time(), "source": "test"}}
    base.update(cfg)
    (d / "autopilot.json").write_text(json.dumps({"projects": {"leadfuel offer": base}}), encoding="utf-8")


def log_rows(tmp_path):
    p = state_dir(tmp_path) / "autopilot-log.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def pre(hook, transcript, tool, **inp):
    return hook.handle(event("PreToolUse", transcript, tool_name=tool, tool_input=inp))


def denied(out) -> str | None:
    hso = (out or {}).get("hookSpecificOutput") or {}
    return hso.get("permissionDecisionReason") if hso.get("permissionDecision") == "deny" else None


# --- off by default --------------------------------------------------------------------------

@pytest.mark.parametrize("tool, inp", [
    ("Bash", {"command": "git push origin node/x"}),
    ("Bash", {"command": "curl https://example.com/x.zip -o x.zip"}),
    ("mcp__abc__send_my_mail", {"to": "x"}),
    ("Agent", {"prompt": "go"}),
])
def test_no_state_file_means_off_everywhere(hook, transcript, tool, inp):
    transcript.add(title_rec(ROUTER))
    assert denied(pre(hook, transcript, tool, **inp)) is None
    assert GATE.decide(tool, inp, ROUTER) is None


def test_a_project_switched_on_does_not_gate_another_project(hook, transcript, tmp_path):
    write_state(tmp_path)
    transcript.add(title_rec(OTHER))
    assert denied(pre(hook, transcript, "Bash", command="git push origin node/x")) is None


def test_switched_off_or_lapsed_is_off(tmp_path):
    write_state(tmp_path, on=False)
    assert GATE.decide("Bash", {"command": "railway up"}, ROUTER) is None
    write_state(tmp_path, expires=time.time() - 1)
    assert GATE.decide("Bash", {"command": "railway up"}, ROUTER) is None


# --- hard gates --------------------------------------------------------------------------------

HARD_CASES = [
    ("spend", "mcp__x__purchase_credits", {}),
    ("credentials", "Read", {"file_path": "F:/repo/.env"}),
    ("credentials", "Bash", {"command": "gh auth token"}),
    ("send", "mcp__9027__send_my_mail", {}),
    ("send", "mcp__9027__approve_post", {}),
    ("send", "PowerShell", {"command": "Send-MailMessage -To x"}),
    ("deploy-config", "Write", {"file_path": "F:/repo/railway.toml"}),
    ("deploy-config", "Edit", {"file_path": "F:/repo/.github/workflows/test.yml"}),
    ("deploy-config", "Bash", {"command": "railway up"}),
    ("deploy-config", "mcp__f5f6__redeploy", {}),
    ("download", "Bash", {"command": "curl -L https://example.com/tool.zip -o t.zip"}),
    ("download", "PowerShell", {"command": "Invoke-WebRequest https://x.test/a -OutFile a"}),
    ("download", "Bash", {"command": "pip install requests"}),
    ("permission-mode", "mcp__ccd_session_mgmt__set_session_permission_mode", {"mode": "bypassPermissions"}),
    ("permission-mode", "Edit", {"file_path": "C:/Users/x/.claude/settings.json"}),
    ("permission-mode", "Skill", {"skill": "update-config"}),
    ("irreversible", "Bash", {"command": "git push --force origin node/x"}),
    ("irreversible", "Bash", {"command": "git push origin main"}),
    ("irreversible", "Bash", {"command": "git reset --hard HEAD~1"}),
    ("irreversible", "mcp__7c67__trash_thread", {}),
    ("autopilot-self", "Bash", {"command": "python scripts/way_autopilot.py on --project p --card q1 --brief b"}),
    ("autopilot-self", "Edit", {"file_path": "C:/p/plugins/leadfuel-way/hooks/autopilot.py"}),
]


@pytest.mark.parametrize("gate, tool, inp", HARD_CASES)
def test_classify_names_each_hard_gate(gate, tool, inp):
    assert GATE.classify(tool, inp)[0] == gate


@pytest.mark.parametrize("gate, tool, inp", HARD_CASES)
def test_hard_gates_are_denied_even_with_everything_allowed(hook, transcript, tmp_path, gate, tool, inp):
    write_state(tmp_path, allow=list(GATE.EGRESS_KINDS) + ["mcp:send_my_mail", "mcp:purchase_credits"])
    transcript.add(title_rec(ROUTER))
    reason = denied(pre(hook, transcript, tool, **inp))
    assert reason and f"HARD GATE ({gate})" in reason
    assert log_rows(tmp_path)[-1]["decision"] == "denied"


@pytest.mark.parametrize("title", [ROUTER, DESK])
def test_the_router_and_its_desks_are_both_gated(hook, transcript, tmp_path, title):
    write_state(tmp_path)
    transcript.add(title_rec(title))
    assert denied(pre(hook, transcript, "Bash", command="railway up"))


def test_a_background_agent_is_gated_by_its_routers_title(hook, transcript, tmp_path):
    write_state(tmp_path)
    transcript.add(title_rec(ROUTER))
    out = hook.handle(event("PreToolUse", transcript, tool_name="Bash", agent_id="a1",
                            tool_input={"command": "curl https://example.com/x"}))
    assert denied(out)


def test_role_enforcement_off_does_not_turn_autopilot_off(hook, transcript, tmp_path, monkeypatch):
    monkeypatch.setenv("WAY_ENFORCE_ROLES", "0")
    write_state(tmp_path)
    transcript.add(title_rec(ROUTER))
    assert denied(pre(hook, transcript, "Bash", command="railway up"))


# --- leaving the machine ----------------------------------------------------------------------

@pytest.mark.parametrize("kind, tool, inp", [
    ("git-push", "Bash", {"command": "git push -u origin node/way-autopilot-1"}),
    ("gh-pr", "Bash", {"command": "gh pr create --draft --title x"}),
    ("web", "WebFetch", {"url": "https://example.com"}),
    ("artifact-publish", "Artifact", {"file_path": "x.html"}),
    ("mcp:search_brain", "mcp__9027__search_brain", {"q": "x"}),
])
def test_egress_is_denied_unless_the_owner_allowed_that_kind(tmp_path, kind, tool, inp):
    write_state(tmp_path)
    assert "leaves the machine" in GATE.decide(tool, inp, ROUTER)
    write_state(tmp_path, allow=[kind])
    assert GATE.decide(tool, inp, ROUTER) is None
    assert log_rows(tmp_path)[-1]["decision"] == "allowed-by-owner-list"


@pytest.mark.parametrize("tool, inp", [
    ("Read", {"file_path": "F:/repo/app.py"}),
    ("Edit", {"file_path": "F:/repo/app.py"}),
    ("Bash", {"command": "git commit -m x && git fetch origin && gh pr view 12 && gh run list"}),
    ("Bash", {"command": "curl http://localhost:8000/health"}),
    ("Bash", {"command": "python way_autopilot.py usage --project p --pct 40 --source x"}),
    ("ArtifactData", {"action": "update"}),
    ("SendMessage", {"to": "main"}),
    ("mcp__ccd_session_mgmt__get_session", {"session_id": "self"}),
    ("mcp__scheduled-tasks__update_scheduled_task", {"taskId": "way-slot-03", "fireAt": "2026-10-30T20:00:00Z"}),
])
def test_local_work_passes(tmp_path, tool, inp):
    write_state(tmp_path)
    assert GATE.decide(tool, inp, ROUTER) is None


def test_changing_any_other_scheduled_task_is_standing_configuration(tmp_path):
    write_state(tmp_path)
    assert "permission-mode" in GATE.decide("mcp__scheduled-tasks__update_scheduled_task", {"taskId": "wake-on-answer", "enabled": True}, ROUTER)


# --- starting work: checkpoint and usage ------------------------------------------------------

def test_no_desk_before_the_checkpoint_card(tmp_path):
    write_state(tmp_path, checkpoint_card=None)
    assert "checkpoint" in GATE.decide("Agent", {"prompt": "x"}, ROUTER)


@pytest.mark.parametrize("usage, word", [
    ({"weekly_pct": 88, "at": None}, "88"),
    (None, "unknown"),
    ({"weekly_pct": 10, "at": 0}, "old"),
])
def test_no_desk_at_88_percent_or_unknown_or_stale_usage(tmp_path, usage, word):
    if usage and usage["at"] is None:
        usage["at"] = time.time()
    write_state(tmp_path, usage=usage)
    reason = GATE.decide("Agent", {"prompt": "x"}, ROUTER)
    assert reason and word in reason
    # arming a launch slot is starting a session too
    assert GATE.decide("mcp__scheduled-tasks__update_scheduled_task",
                       {"taskId": "way-slot-01", "fireAt": "2026-10-30T20:00:00Z"}, ROUTER)


def test_a_desk_starts_when_checkpoint_and_usage_are_fine(tmp_path):
    write_state(tmp_path)
    assert GATE.decide("Agent", {"prompt": "x"}, ROUTER) is None


# --- unknown is not off -----------------------------------------------------------------------

def test_unreadable_state_gates_every_session(hook, transcript, tmp_path):
    d = state_dir(tmp_path)
    d.mkdir(parents=True, exist_ok=True)
    (d / "autopilot.json").write_text("{not json", encoding="utf-8")
    transcript.add(title_rec(OTHER))
    assert denied(pre(hook, transcript, "Bash", command="git push origin node/x"))
    assert denied(pre(hook, transcript, "Agent", prompt="x"))
    assert denied(pre(hook, transcript, "Read", file_path="F:/repo/app.py")) is None


def test_a_missing_gate_module_with_a_state_file_denies(hook, transcript, tmp_path, monkeypatch):
    write_state(tmp_path)
    monkeypatch.setattr(hook, "AUTOPILOT", None)
    transcript.add(title_rec(OTHER))
    assert denied(pre(hook, transcript, "Bash", command="echo hi"))
    assert denied(pre(hook, transcript, "Read", file_path="F:/repo/app.py")) is None


# --- the hook registration reaches these tools ------------------------------------------------

def _matches(tool: str) -> int:
    cfg = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    return sum(bool(re.search(g["matcher"], tool)) for g in cfg["hooks"]["PreToolUse"])


@pytest.mark.parametrize("tool", ["Bash", "PowerShell", "Read", "WebFetch", "Agent", "Edit", "Write",
                                  "mcp__9027__send_my_mail", "mcp__ccd_session_mgmt__set_session_permission_mode",
                                  "mcp__ccd_session_mgmt__archive_session", "mcp__scheduled-tasks__update_scheduled_task"])
def test_every_gated_tool_reaches_the_hook_exactly_once(tool):
    assert _matches(tool) == 1, tool


# --- the switch ---------------------------------------------------------------------------------

def run_cli(tmp_path, *args):
    env = {"WAY_STATE_DIR": str(state_dir(tmp_path)), "PATH": "", "SYSTEMROOT": __import__("os").environ.get("SYSTEMROOT", "")}
    return subprocess.run([sys.executable, str(CLI), *args], capture_output=True, text=True, env=env, timeout=30)


def test_on_needs_a_card_and_a_brief_and_refuses_hard_gates(tmp_path):
    brief = tmp_path / "GOAL_BRIEF.md"
    brief.write_text("# brief", encoding="utf-8")
    assert run_cli(tmp_path, "on", "--project", "leadfuel offer", "--card", "yes", "--brief", str(brief)).returncode == 2
    assert run_cli(tmp_path, "on", "--project", "leadfuel offer", "--card", "q9", "--brief", str(tmp_path / "nope")).returncode == 2
    bad = run_cli(tmp_path, "on", "--project", "leadfuel offer", "--card", "q9", "--brief", str(brief), "--allow", "send")
    assert bad.returncode == 2 and "never allowable" in bad.stderr
    assert not (state_dir(tmp_path) / "autopilot.json").exists()
    ok = run_cli(tmp_path, "on", "--project", "leadfuel offer", "--card", "q9", "--brief", str(brief), "--allow", "git-push")
    assert ok.returncode == 0, ok.stderr
    data = json.loads((state_dir(tmp_path) / "autopilot.json").read_text(encoding="utf-8"))
    cfg = data["projects"]["leadfuel offer"]
    assert cfg["on"] is True and cfg["allow"] == ["git-push"] and cfg["checkpoint_card"] is None
    # switched on, but no desk until the checkpoint card and a usage reading
    assert "checkpoint" in GATE.decide("Agent", {}, ROUTER)
    assert run_cli(tmp_path, "checkpoint", "--project", "leadfuel offer", "--card", "q10").returncode == 0
    assert "unknown" in GATE.decide("Agent", {}, ROUTER)
    assert run_cli(tmp_path, "usage", "--project", "leadfuel offer", "--pct", "41", "--source", "test").returncode == 0
    assert GATE.decide("Agent", {}, ROUTER) is None
    assert run_cli(tmp_path, "decide", "--project", "leadfuel offer", "--decision", "use sqlite", "--why", "brief 3").returncode == 0
    assert run_cli(tmp_path, "off", "--project", "leadfuel offer").returncode == 0
    assert GATE.decide("Bash", {"command": "railway up"}, ROUTER) is None
    kinds = [r["decision"] for r in log_rows(tmp_path)]
    assert kinds[:1] == ["autopilot-on"] and "autonomous" in kinds and kinds[-1] == "autopilot-off"


def test_the_skill_and_template_say_off_by_default_and_name_the_gates():
    skill = (PLUGIN / "skills" / "autopilot" / "SKILL.md").read_text(encoding="utf-8")
    brief = (PLUGIN / "skills" / "autopilot" / "GOAL_BRIEF.md").read_text(encoding="utf-8")
    assert "OFF by default" in skill and "wake-on-answer" in skill.lower()
    for word in ("spend", "credentials", "sends and posts", "deploy", "downloads", "permission-mode", "88%"):
        assert word in skill and word in brief, word
    for section in ("The goal, in the owner's words", "The MVP: done when", "What the router may decide alone"):
        assert section in brief
