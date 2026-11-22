"""Tests for scripts/way_doctor.py. The point of the doctor is that a check which cannot see its
subject says UNKNOWN, so most of these are about what it must NOT call OK."""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time

import pytest

from kit import PLUGIN, load_module


@pytest.fixture(scope="module")
def doc():
    return load_module(PLUGIN / "scripts" / "way_doctor.py", "way_doctor_under_test")


@pytest.fixture
def ctx(doc, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    return doc.Ctx(plugin_dir=PLUGIN, home=home, state_dir=tmp_path / "state", cwd=tmp_path / "cwd", use_cli=False)


def R(doc, status):
    return doc.Result("x", status, "d")


# --- the verdict ----------------------------------------------------------------------------

def test_verdict_live_only_when_everything_is_ok(doc):
    assert doc.verdict([R(doc, doc.OK), R(doc, doc.OK)]) == "LIVE"


def test_verdict_any_fail_is_not_live(doc):
    assert doc.verdict([R(doc, doc.OK), R(doc, doc.FAIL), R(doc, doc.UNKNOWN)]) == "NOT LIVE"


def test_verdict_unknown_is_unproven_never_live(doc):
    assert doc.verdict([R(doc, doc.OK), R(doc, doc.UNKNOWN)]) == "UNPROVEN"


def test_verdict_ignores_advisories_but_not_when_they_are_all_there_is(doc):
    assert doc.verdict([R(doc, doc.OK), R(doc, doc.WARN)]) == "LIVE"
    assert doc.verdict([R(doc, doc.WARN)]) == "UNPROVEN"
    assert doc.verdict([]) == "UNPROVEN"  # a doctor that saw nothing must not say LIVE


# --- python ---------------------------------------------------------------------------------

def test_missing_python_is_a_failure(doc, ctx, monkeypatch):
    monkeypatch.setattr(doc.shutil, "which", lambda name: None)
    [r] = doc.check_python(ctx)
    assert r.status == doc.FAIL


def test_the_store_stub_is_a_failure_and_python3_stub_an_advisory(doc, ctx, monkeypatch):
    stub = r"C:\Users\x\AppData\Local\Microsoft\WindowsApps\python.exe"
    monkeypatch.setattr(doc.shutil, "which", lambda name: stub if name == "python" else stub.replace("python.exe", "python3.exe"))
    results = doc.check_python(ctx)
    assert [r.status for r in results] == [doc.FAIL, doc.WARN]


def test_a_working_python_is_ok(doc, ctx, monkeypatch):
    monkeypatch.setattr(doc.shutil, "which", lambda name: sys.executable if name == "python" else None)
    [r] = doc.check_python(ctx)
    assert r.status == doc.OK


# --- manifests ------------------------------------------------------------------------------

def test_the_real_plugin_manifests_are_ok(doc, ctx):
    results = doc.check_manifests(ctx)
    assert all(r.status == doc.OK for r in results), [(r.name, r.detail) for r in results]


@pytest.fixture
def plugin_copy(tmp_path):
    dst = tmp_path / "plugin"
    shutil.copytree(PLUGIN, dst, ignore=shutil.ignore_patterns("__pycache__", "tests", ".pytest_cache"))
    return dst


def test_an_unregistered_event_is_a_failure(doc, plugin_copy, ctx):
    p = plugin_copy / "hooks" / "hooks.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    del cfg["hooks"]["Stop"]
    p.write_text(json.dumps(cfg), encoding="utf-8")
    ctx.plugin_dir = plugin_copy
    [r] = [r for r in doc.check_manifests(ctx) if r.name.startswith("hooks.json")]
    assert r.status == doc.FAIL and "Stop" in r.detail


def test_a_command_pointing_at_a_missing_script_is_a_failure(doc, plugin_copy, ctx):
    (plugin_copy / "hooks" / "way_hook.py").unlink()
    ctx.plugin_dir = plugin_copy
    [r] = [r for r in doc.check_manifests(ctx) if r.name.startswith("hooks.json")]
    assert r.status == doc.FAIL and "does not exist" in r.detail


def test_unparseable_hooks_json_is_a_failure(doc, plugin_copy, ctx):
    (plugin_copy / "hooks" / "hooks.json").write_text("{nope", encoding="utf-8")
    ctx.plugin_dir = plugin_copy
    assert any(r.status == doc.FAIL for r in doc.check_manifests(ctx))


# --- the synthetic session ------------------------------------------------------------------

def test_the_real_hook_passes_every_synthetic_check(doc, ctx):
    results = doc.check_synthetic(ctx)
    assert len(results) == 8
    assert all(r.status == doc.OK for r in results), [(r.name, r.detail) for r in results]


def test_a_silent_hook_is_never_ok(doc, plugin_copy, ctx):
    """The failure this whole plugin exists to prevent: a hook that runs, exits 0 and does nothing."""
    (plugin_copy / "hooks" / "way_hook.py").write_text("import sys\nsys.exit(0)\n", encoding="utf-8")
    ctx.plugin_dir = plugin_copy
    results = doc.check_synthetic(ctx)
    by = {r.name: r.status for r in results}
    assert by["hook: banner on SessionStart"] == doc.FAIL
    assert by["hook: guard speaks past the cap"] == doc.FAIL
    assert by["hook: Stop gate blocks with no handoff"] == doc.FAIL
    assert by["hook: PreToolUse denies a router's edit"] == doc.FAIL
    # The two "stays quiet" checks pass for a silent hook, which is why the loud ones above must exist.
    assert by["hook: Stop gate lets a handoff through"] == doc.OK


def test_a_crashing_hook_is_a_failure(doc, plugin_copy, ctx):
    (plugin_copy / "hooks" / "way_hook.py").write_text("import sys\nsys.exit(49)\n", encoding="utf-8")
    ctx.plugin_dir = plugin_copy
    results = doc.check_synthetic(ctx)
    assert all(r.status == doc.FAIL for r in results)
    assert "49" in results[0].detail


def test_a_missing_hook_script_is_a_failure(doc, plugin_copy, ctx):
    (plugin_copy / "hooks" / "way_hook.py").unlink()
    ctx.plugin_dir = plugin_copy
    [r] = doc.check_synthetic(ctx)
    assert r.status == doc.FAIL


# --- real sessions --------------------------------------------------------------------------

def write_state(ctx, sid, **d):
    ctx.state_dir.mkdir(parents=True, exist_ok=True)
    (ctx.state_dir / f"{sid}.json").write_text(json.dumps(d), encoding="utf-8")


def test_no_state_files_is_unknown_not_ok(doc, ctx):
    assert doc.check_real_sessions(ctx).status == doc.UNKNOWN


def test_stale_state_files_are_unknown(doc, ctx):
    write_state(ctx, "old", updated_at=time.time() - 3 * 86400, seen={"SessionStart": 1})
    assert doc.check_real_sessions(ctx).status == doc.UNKNOWN


def test_recent_sessions_that_never_saw_the_banner_are_unknown(doc, ctx):
    write_state(ctx, "pre-install", updated_at=time.time(), seen={"PostToolUse": 4})
    r = doc.check_real_sessions(ctx)
    assert r.status == doc.UNKNOWN and "SessionStart" in r.detail


def test_a_recent_session_that_saw_the_banner_is_ok(doc, ctx):
    write_state(ctx, "abcdef123456", updated_at=time.time(), seen={"SessionStart": 1, "PostToolUse": 9},
                role="DESK", lane="DOORS", model="claude-sonnet-5-5", tokens=42_000, stops_blocked=0)
    r = doc.check_real_sessions(ctx)
    assert r.status == doc.OK and "abcdef12" in r.detail and "DESK/DOORS" in r.detail and "42k" in r.detail


def test_corrupt_state_files_are_skipped_not_fatal(doc, ctx):
    ctx.state_dir.mkdir(parents=True)
    (ctx.state_dir / "bad.json").write_text("{", encoding="utf-8")
    assert doc.check_real_sessions(ctx).status == doc.UNKNOWN


# --- duplicates and settings ----------------------------------------------------------------

def test_the_old_user_level_copy_is_flagged_not_deleted(doc, ctx):
    old = ctx.home / ".claude" / "skills" / "leadfuel-way"
    old.mkdir(parents=True)
    (old / "SKILL.md").write_text("old", encoding="utf-8")
    [r] = [r for r in doc.check_duplicates(ctx) if r.name == "duplicate skill copy"]
    assert r.status == doc.WARN and "owner step" in r.fix
    assert old.exists()  # the doctor never deletes


def test_settings_that_are_null_are_reported(doc, ctx):
    (ctx.home / ".claude").mkdir(parents=True)
    (ctx.home / ".claude" / "settings.json").write_text("null", encoding="utf-8")
    [r] = [r for r in doc.check_duplicates(ctx) if r.name == "user settings readable"]
    assert r.status == doc.WARN and "null" in r.detail


def test_a_python3_hook_in_settings_is_reported(doc, ctx):
    ctx.cwd.mkdir(parents=True)
    (ctx.cwd / ".claude").mkdir()
    (ctx.cwd / ".claude" / "settings.json").write_text(
        json.dumps({"hooks": {"Stop": [{"hooks": [{"type": "command", "command": 'python3 "x.py"'}]}]}}), encoding="utf-8")
    assert any(r.name == "project settings calls python3" for r in doc.check_duplicates(ctx))


def test_clean_settings_raise_nothing(doc, ctx):
    ctx.cwd.mkdir(parents=True)
    (ctx.cwd / ".claude").mkdir()
    (ctx.cwd / ".claude" / "settings.json").write_text(json.dumps({"hooks": {}}), encoding="utf-8")
    assert not [r for r in doc.check_duplicates(ctx) if "settings" in r.name]


# --- the CLI-dependent checks and the whole run ---------------------------------------------

def test_cli_checks_are_unknown_when_the_cli_is_off(doc, ctx):
    assert doc.check_enabled(ctx).status == doc.UNKNOWN
    assert doc.check_validate(ctx).status == doc.UNKNOWN


def test_cli_checks_are_unknown_when_the_cli_is_missing(doc, ctx, monkeypatch):
    ctx.use_cli = True
    monkeypatch.setattr(doc.shutil, "which", lambda name: None)
    assert doc.check_enabled(ctx).status == doc.UNKNOWN
    assert doc.check_validate(ctx).status == doc.UNKNOWN


@pytest.mark.parametrize(
    "rows, status",
    [
        ([], "FAIL"),                                                      # nothing installed
        ([{"id": "leadfuel-way@leadfuel", "enabled": True}], "OK"),
        ([{"id": "leadfuel-way@leadfuel", "enabled": False}], "FAIL"),
        ([{"id": "leadfuel-way@leadfuel"}], "UNKNOWN"),                    # the list does not say
        ([{"id": "other@x", "enabled": True}], "FAIL"),
    ],
)
def test_enabled_check_reads_the_plugin_list(doc, ctx, monkeypatch, rows, status):
    ctx.use_cli = True
    monkeypatch.setattr(doc.shutil, "which", lambda name: "claude")
    monkeypatch.setattr(doc, "run", lambda cmd, **kw: (0, json.dumps(rows), ""))
    assert doc.check_enabled(ctx).status == status


def test_enabled_check_with_a_failing_list_command_is_unknown(doc, ctx, monkeypatch):
    ctx.use_cli = True
    monkeypatch.setattr(doc.shutil, "which", lambda name: "claude")
    monkeypatch.setattr(doc, "run", lambda cmd, **kw: (1, "", "boom"))
    assert doc.check_enabled(ctx).status == doc.UNKNOWN
    monkeypatch.setattr(doc, "run", lambda cmd, **kw: (0, "not json", ""))
    assert doc.check_enabled(ctx).status == doc.UNKNOWN


def test_without_the_cli_the_verdict_can_never_be_live(doc, ctx):
    results = doc.run_all(ctx)
    assert doc.verdict(results) != "LIVE"
    assert any(r.status == doc.UNKNOWN for r in results)


def test_the_command_line_prints_json_and_an_exit_code(tmp_path):
    done = subprocess.run(
        [sys.executable, str(PLUGIN / "scripts" / "way_doctor.py"), "--no-cli", "--json"],
        capture_output=True, text=True, encoding="utf-8", timeout=180,
    )
    out = json.loads(done.stdout)
    assert out["verdict"] in {"LIVE", "NOT LIVE", "UNPROVEN"} and out["verdict"] != "LIVE"
    assert done.returncode == {"NOT LIVE": 1, "UNPROVEN": 2}[out["verdict"]]
    assert {"name", "status", "detail", "fix"} <= set(out["results"][0])


def test_the_text_report_states_the_rule(doc):
    text = doc.render([R(doc, doc.OK), R(doc, doc.UNKNOWN)])
    assert "VERDICT: UNPROVEN" in text and "not a pass" in text


# --- way_caps.py and the doctor's report of an override -------------------------------------

def test_caps_script_sets_shows_and_clears(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("WAY_STATE_DIR", str(tmp_path / "s"))
    caps = load_module(PLUGIN / "scripts" / "way_caps.py", "way_caps_under_test")
    assert caps.main(["set", "40000", "90000", "--minutes", "5"]) == 0
    data = json.loads((tmp_path / "s" / "caps-override.json").read_text(encoding="utf-8"))
    assert (data["soft"], data["hard"]) == (40_000, 90_000) and data["expires"] > time.time()
    caps.main(["show"])
    assert "40000" in capsys.readouterr().out
    assert caps.main(["clear"]) == 0 and not (tmp_path / "s" / "caps-override.json").exists()
    assert caps.main(["set", "5000", "1000"]) == 2  # soft above hard is refused


def test_the_hook_obeys_what_the_caps_script_wrote(tmp_path, monkeypatch):
    monkeypatch.setenv("WAY_STATE_DIR", str(tmp_path / "s"))
    caps = load_module(PLUGIN / "scripts" / "way_caps.py", "way_caps_under_test2")
    hook = load_module(PLUGIN / "hooks" / "way_hook.py", "way_hook_for_caps")
    caps.main(["set", "12000", "34000"])
    assert hook.caps_for("claude-sonnet-5-5") == (12_000, 34_000)


def test_the_doctor_reports_an_active_override_but_not_an_expired_one(doc, ctx):
    ctx.state_dir.mkdir(parents=True, exist_ok=True)
    path = ctx.state_dir / "caps-override.json"
    path.write_text(json.dumps({"soft": 40_000, "hard": 90_000, "expires": time.time() + 600}), encoding="utf-8")
    [r] = [r for r in doc.check_duplicates(ctx) if r.name == "forced caps active"]
    assert r.status == doc.WARN and "40k" in r.detail and "clear" in r.fix
    path.write_text(json.dumps({"soft": 40_000, "hard": 90_000, "expires": time.time() - 1}), encoding="utf-8")
    assert not [r for r in doc.check_duplicates(ctx) if r.name == "forced caps active"]


# --- the handoff skill must keep the no-orphan rule (owner, 2026-10-02) ---------------------------

def test_the_real_handoff_skill_ends_in_self_archive(doc, ctx):
    r = doc.check_handoff_archives(ctx)
    assert r.status == doc.OK, r.detail


def _handoff_copy(plugin_copy, mutate):
    p = plugin_copy / "skills" / "handoff" / "SKILL.md"
    p.write_text(mutate(p.read_text(encoding="utf-8")), encoding="utf-8")


def test_a_handoff_skill_without_the_archive_step_fails(doc, plugin_copy, ctx):
    ctx.plugin_dir = plugin_copy
    _handoff_copy(plugin_copy, lambda t: t[: t.index("6. **Never leave")] + "\n## Where the note goes\n" + t.split("## Where the note goes\n", 1)[1])
    r = doc.check_handoff_archives(ctx)
    assert r.status == doc.FAIL and "archive_session" in r.detail


def test_a_handoff_skill_that_archives_without_verifying_the_push_fails(doc, plugin_copy, ctx):
    ctx.plugin_dir = plugin_copy
    _handoff_copy(plugin_copy, lambda t: t.replace("git ls-remote", "git status"))
    r = doc.check_handoff_archives(ctx)
    assert r.status == doc.FAIL and "git ls-remote" in r.detail


def test_archiving_that_is_not_the_last_step_fails(doc, plugin_copy, ctx):
    """Steps after the archive would never run: the conversation ends with it."""
    ctx.plugin_dir = plugin_copy
    _handoff_copy(plugin_copy, lambda t: t.replace("\n## Where the note goes", "7. Then tell the owner it went well.\n\n## Where the note goes", 1))
    assert doc.check_handoff_archives(ctx).status == doc.FAIL


def test_a_missing_or_stepless_handoff_skill_is_a_failure_not_unknown(doc, plugin_copy, ctx):
    ctx.plugin_dir = plugin_copy
    _handoff_copy(plugin_copy, lambda t: t.replace("## Steps", "## Procedure"))
    assert doc.check_handoff_archives(ctx).status == doc.FAIL
    (plugin_copy / "skills" / "handoff" / "SKILL.md").unlink()
    assert doc.check_handoff_archives(ctx).status == doc.FAIL


def test_the_doctor_run_includes_the_self_archive_check(doc, ctx):
    assert any(r.name == "handoff: no self-archive before a live successor" for r in doc.run_all(ctx))


def test_unconditional_self_archive_wording_in_any_skill_fails(doc, plugin_copy, ctx):
    """The wording that let ROUTER #9 archive itself with no successor must not come back anywhere."""
    ctx.plugin_dir = plugin_copy
    p = plugin_copy / "skills" / "router" / "SKILL.md"
    p.write_text(p.read_text(encoding="utf-8") + "\nThen archive yourself as your last act.\n", encoding="utf-8")
    r = doc.check_handoff_archives(ctx)
    assert r.status == doc.FAIL and "router" in r.detail


def test_a_handoff_step_that_does_not_say_stay_open_fails(doc, plugin_copy, ctx):
    ctx.plugin_dir = plugin_copy
    _handoff_copy(plugin_copy, lambda t: t.replace("**stay open**", "leave"))
    r = doc.check_handoff_archives(ctx)
    assert r.status == doc.FAIL and "stay open" in r.detail


def test_a_handoff_step_without_the_list_sessions_proof_fails(doc, plugin_copy, ctx):
    ctx.plugin_dir = plugin_copy
    _handoff_copy(plugin_copy, lambda t: t.replace("list_sessions", "a look around"))
    assert doc.check_handoff_archives(ctx).status == doc.FAIL


# --- the archive guard must be registered ---------------------------------------------------

def test_the_real_archive_guard_is_registered(doc, ctx):
    r = doc.check_archive_guard_registered(ctx)
    assert r.status == doc.OK, r.detail


def test_an_unregistered_archive_guard_fails(doc, plugin_copy, ctx):
    ctx.plugin_dir = plugin_copy
    p = plugin_copy / "hooks" / "hooks.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["hooks"]["PreToolUse"] = cfg["hooks"]["PreToolUse"][:1]
    p.write_text(json.dumps(cfg), encoding="utf-8")
    assert doc.check_archive_guard_registered(ctx).status == doc.FAIL


def test_a_matcher_that_also_catches_unarchive_fails(doc, plugin_copy, ctx):
    ctx.plugin_dir = plugin_copy
    p = plugin_copy / "hooks" / "hooks.json"
    cfg = json.loads(p.read_text(encoding="utf-8"))
    cfg["hooks"]["PreToolUse"][1]["matcher"] = "mcp__.*archive_session"
    p.write_text(json.dumps(cfg), encoding="utf-8")
    assert doc.check_archive_guard_registered(ctx).status == doc.FAIL


def test_the_synthetic_run_proves_the_archive_guard_both_ways(doc, ctx):
    by = {r.name: r for r in doc.check_synthetic(ctx)}
    assert by["hook: self-archive refused with no successor"].status == doc.OK, by["hook: self-archive refused with no successor"].detail
    assert by["hook: self-archive allowed once the successor is live"].status == doc.OK, by["hook: self-archive allowed once the successor is live"].detail