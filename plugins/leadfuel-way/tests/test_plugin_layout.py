"""The plugin's files agree with each other: manifests, hook registration, skills, public-repo hygiene."""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys

import pytest

from kit import PLUGIN, load_module

REPO = PLUGIN.parents[1]
EVENTS = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "PreToolUse"}
SKILLS = sorted(p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md"))


def test_the_expected_skills_exist():
    assert set(SKILLS) == {"way", "handoff", "desk", "conductor", "router", "new-project"}


def test_plugin_manifest():
    meta = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert meta["name"] == "leadfuel-way" and re.fullmatch(r"\d+\.\d+\.\d+", meta["version"])
    assert "@" not in json.dumps(meta)  # public repo: no email


def test_every_place_that_states_the_version_agrees(hook):
    """Claude Code caches an installed plugin by version, so a change that does not bump it never
    reaches a machine that already installed the plugin. The three copies must move together."""
    meta = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    [entry] = [p for p in market["plugins"] if p["name"] == "leadfuel-way"]
    assert meta["version"] == entry["version"] == hook.VERSION


def test_marketplace_lists_the_plugin_at_a_real_path():
    market = json.loads((REPO / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8"))
    [entry] = [p for p in market["plugins"] if p["name"] == "leadfuel-way"]
    assert entry["source"] == "./plugins/leadfuel-way"
    assert (REPO / entry["source"] / ".claude-plugin" / "plugin.json").is_file()
    assert "@" not in json.dumps(market)


def test_hooks_json_registers_all_five_events_on_the_one_script():
    cfg = json.loads((PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8"))
    assert set(cfg["hooks"]) == EVENTS
    for name, groups in cfg["hooks"].items():
        assert len(groups) == (2 if name == "PreToolUse" else 1), name
        for group in groups:
            [hook] = group["hooks"]
            assert hook["type"] == "command" and hook["timeout"] == 10
            assert hook["command"] == 'python "${CLAUDE_PLUGIN_ROOT}/hooks/way_hook.py"', name
    # The doctor's synthetic run uses PreToolUse[0], so the edit rule stays first.
    assert cfg["hooks"]["PreToolUse"][0]["matcher"] == "Edit|Write|MultiEdit|NotebookEdit"
    archive = cfg["hooks"]["PreToolUse"][1]["matcher"]
    for tool in ("mcp__ccd_session_mgmt__archive_session", "mcp__claude-code-remote__archive_session"):
        assert re.search(archive, tool), tool
    assert not re.search(archive, "mcp__ccd_session_mgmt__unarchive_session")
    assert (PLUGIN / "hooks" / "way_hook.py").is_file()


def test_hooks_json_uses_python_not_the_windows_store_stub():
    text = (PLUGIN / "hooks" / "hooks.json").read_text(encoding="utf-8")
    assert "python3" not in text  # python3 is the Microsoft Store stub on the owner's PC (exit 49)


@pytest.mark.parametrize("name", SKILLS)
def test_skill_frontmatter(name):
    text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    m = re.match(r"---\nname: (?P<n>[^\n]+)\ndescription: (?P<d>[^\n]+)\n---\n", text)
    assert m, f"{name}: frontmatter must be name then description"
    assert m["n"] == name and len(m["d"]) > 40


@pytest.mark.parametrize("name", SKILLS)
def test_description_is_a_safe_yaml_plain_scalar(name):
    """`claude plugin validate` caught `description: The DESK session: one task`: a colon and a space
    ends a YAML plain scalar, so the whole frontmatter failed to parse and the skill loaded with
    empty metadata. A space then `#` starts a comment and silently truncates it."""
    text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
    desc = re.match(r"---\nname: [^\n]+\ndescription: ([^\n]+)\n---\n", text)[1]
    assert ": " not in desc and " #" not in desc and not desc.endswith(":")
    assert desc[0] not in "\"'[{&*!|>%@`"


def test_claude_cli_validates_the_plugin():
    """The real parser, when this machine has it. Skipped (not passed) elsewhere."""
    claude = shutil.which("claude")
    if not claude:
        pytest.skip("the claude CLI is not installed here")
    done = subprocess.run([claude, "plugin", "validate", str(PLUGIN), "--strict"], capture_output=True, text=True,
                          encoding="utf-8", errors="replace", timeout=120)
    assert done.returncode == 0, done.stdout + done.stderr


def test_skill_cross_references_resolve():
    for name in SKILLS:
        text = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        for ref in re.findall(r"leadfuel-way:([a-z-]+)", text):
            assert ref in SKILLS, f"{name} refers to leadfuel-way:{ref}, which does not exist"


def test_the_banner_only_names_skills_that_exist(hook):
    text = hook.banner("startup", None, "UNFILED", None, None, None, 1, 2)
    for ref in re.findall(r"leadfuel-way:([a-z-]+)", text):
        assert ref in SKILLS


def test_hook_messages_only_name_skills_that_exist(hook):
    src = (PLUGIN / "hooks" / "way_hook.py").read_text(encoding="utf-8")
    refs = set(re.findall(r"leadfuel-way:([a-z-]+)", src))
    assert "handoff" in refs  # the guard and the Stop gate both send a session to this skill
    assert all(ref in SKILLS for ref in refs)
    # A plugin skill is invoked by its namespaced name. A bare "the `handoff` skill" would not resolve.
    assert "`handoff` skill" not in src


# Standing rules: the retired arm spellings never reappear; a public repo carries no emails.
# The pattern is assembled from fragments so that this file does not itself contain a retired name.
RETIRED = re.compile("|".join(r"\b" + "nova" + tail + r"\b" for tail in ("hawk", "hound", "herald", "hunt", "hub")) + r"|\bsmart" + "icp", re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.I)


def shipped_files():
    return [p for p in PLUGIN.rglob("*") if p.is_file() and "__pycache__" not in p.parts and p.suffix != ".pyc"]


def test_no_retired_arm_names_or_emails_in_what_ships():
    files = shipped_files()
    assert len(files) >= 10  # a scan over nothing would pass; make sure it saw the plugin
    for p in files:
        text = p.read_text(encoding="utf-8", errors="replace")
        assert not RETIRED.search(text), f"{p.relative_to(REPO)} names a retired arm"
        assert not EMAIL.search(text), f"{p.relative_to(REPO)} contains an email address"


# route.py: copied from the conductor kit, so pin the behaviour the router depends on.
@pytest.fixture(scope="module")
def route_mod():
    return load_module(PLUGIN / "scripts" / "route.py", "route_under_test")


@pytest.mark.parametrize(
    "task, model",
    [
        ({"title": "Fix typo in the README", "effort": "small"}, "haiku"),
        ({"title": "Rewrite the door", "effort": "medium"}, "opus"),
        ({"title": "Add a column", "envelope": "critical"}, "opus"),
        ({"title": "Add a column", "effort": "xhigh"}, "opus"),
        ({"title": "Add a column", "effort": "medium"}, "sonnet"),
        ({"title": "Rewrite the door", "model_pin": "haiku"}, "haiku"),
        ({"title": "Docs sweep", "effort": "small", "envelope": "door"}, "opus"),
    ],
)
def test_route_picks_the_model(route_mod, task, model):
    assert route_mod.route(task)["model"] == model


def test_route_ids_are_current(route_mod):
    assert set(route_mod.IDS) == {"fable", "opus", "sonnet", "haiku"}
    assert "haiku" in route_mod.IDS["haiku"]
    assert route_mod.IDS["fable"] == "claude-fable-5-1"


@pytest.mark.parametrize("pin", ["fable", "FABLE", "claude-fable-5-1"])
def test_route_obeys_a_fable_pin(route_mod, pin):
    """Owner, 2026-10-02: queue work on Fable. Before this the pin was dropped silently and the
    task routed by the rules, so a router could not put a desk on Fable through route.py."""
    out = route_mod.route({"title": "Add a column", "effort": "small", "model_pin": pin})
    assert out["model"] == "fable" and out["model_id"] == "claude-fable-5-1"


@pytest.mark.parametrize(
    "task",
    [
        {"title": "Rewrite the security door", "effort": "xhigh", "envelope": "critical"},
        {"title": "Add a column", "effort": "medium"},
    ],
)
def test_route_never_picks_fable_on_its_own(route_mod, task):
    assert route_mod.route(task)["model"] != "fable"


@pytest.mark.parametrize("pin", ["fabel", "gpt", "claude-opus-4-1"])
def test_route_refuses_a_pin_it_cannot_read(route_mod, pin):
    """A pin that names no model must not quietly become whatever the rules say."""
    with pytest.raises(route_mod.BadTask):
        route_mod.route({"title": "Add a column", "model_pin": pin})


def test_route_passes_the_model_effort_through(route_mod):
    out = route_mod.route({"title": "Audit the doors", "model_pin": "fable", "model_effort": "XHigh"})
    assert out["model_effort"] == "xhigh"
    assert "model_effort" not in route_mod.route({"title": "Add a column"})
    with pytest.raises(route_mod.BadTask):
        route_mod.route({"title": "Add a column", "model_effort": "huge"})


def test_route_cli_exits_nonzero_on_a_bad_pin():
    run = subprocess.run(
        [sys.executable, str(PLUGIN / "scripts" / "route.py"), json.dumps({"title": "x", "model_pin": "fabel"})],
        capture_output=True, text=True, timeout=30,
    )
    assert run.returncode != 0 and run.stdout == "" and "fabel" in run.stderr


UNCONDITIONAL = re.compile(r"archive yourself as your last act|archives itself as its last act|archives itself at handoff", re.I)


@pytest.mark.parametrize("path", [PLUGIN / "skills" / s / "SKILL.md" for s in SKILLS]
                         + [REPO / ".claude" / "skills" / s / "SKILL.md" for s in ("leadfuel-way", "router", "handoff")])
def test_no_skill_archives_a_session_before_its_successor_is_live(path):
    """Owner, 2026-10-02: "MAKE SURE ROUTER DOESNT LEAVE ITSELF UNTIL IT HAS A SUCCESSOR", and a desk
    at its limit hands off and stays open. The older unconditional "archive yourself as your last
    act" let ROUTER #9 archive itself with no ROUTER #10, so it must not come back in any copy."""
    if not path.is_file():
        pytest.skip(f"{path} is not in this tree")
    assert not UNCONDITIONAL.search(path.read_text(encoding="utf-8")), path


@pytest.mark.parametrize("name", ["way", "handoff", "router", "conductor", "desk"])
def test_each_tier_skill_says_stay_open_until_the_successor_is_live(name):
    low = (PLUGIN / "skills" / name / "SKILL.md").read_text(encoding="utf-8").lower()
    assert "stay open" in low and "successor" in low and "live" in low, name


def test_the_handoff_skill_names_the_proof_the_guard_needs():
    handoff = (PLUGIN / "skills" / "handoff" / "SKILL.md").read_text(encoding="utf-8")
    assert "archive_session" in handoff and "git ls-remote" in handoff and "list_sessions" in handoff
