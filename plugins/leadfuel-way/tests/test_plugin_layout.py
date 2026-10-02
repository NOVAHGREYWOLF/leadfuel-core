"""The plugin's files agree with each other: manifests, hook registration, skills, public-repo hygiene."""
from __future__ import annotations

import json
import re

import pytest

from kit import PLUGIN, load_module

REPO = PLUGIN.parents[1]
EVENTS = {"SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "PreToolUse"}
SKILLS = sorted(p.parent.name for p in (PLUGIN / "skills").glob("*/SKILL.md"))


def test_the_expected_skills_exist():
    assert set(SKILLS) == {"way", "handoff", "desk", "conductor", "router", "new-project"}


def test_plugin_manifest():
    meta = json.loads((PLUGIN / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    assert meta["name"] == "leadfuel-way" and meta["version"] == "0.1.0"
    assert "@" not in json.dumps(meta)  # public repo: no email


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
        [group] = groups
        [hook] = group["hooks"]
        assert hook["type"] == "command" and hook["timeout"] == 10
        assert hook["command"] == 'python "${CLAUDE_PLUGIN_ROOT}/hooks/way_hook.py"', name
    assert cfg["hooks"]["PreToolUse"][0]["matcher"] == "Edit|Write|MultiEdit|NotebookEdit"
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
    for ref in set(re.findall(r"leadfuel-way:([a-z-]+)", src)) | set(re.findall(r"`(handoff)` skill", src)):
        assert ref in SKILLS


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
    assert set(route_mod.IDS) == {"opus", "sonnet", "haiku"}
    assert "haiku" in route_mod.IDS["haiku"]
