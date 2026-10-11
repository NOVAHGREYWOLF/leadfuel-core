#!/usr/bin/env python
"""Prove, piece by piece, that the way is live on this machine. Stdlib only.

    python way_doctor.py [--plugin-dir DIR] [--hours 24] [--no-cli] [--json]

Why it exists: the handoff guard ran nowhere for weeks, and nothing said so. A hook that is not
firing looks exactly like a session that is small. So every check here has three answers, and the
third is the one that matters:

    OK       the thing was seen working.
    FAIL     the thing was seen not working.
    UNKNOWN  the check could not see its subject. This is NEVER reported as OK.

Advisories (WARN) never change the verdict. The verdict is LIVE only if every check is OK;
NOT LIVE if any is FAIL; otherwise UNPROVEN. Exit code: 0 LIVE, 1 NOT LIVE, 2 UNPROVEN.

What it does not do: edit settings, install anything, or delete the duplicate copies it finds.
Those are the owner's steps; the doctor prints them.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

EVENTS = ("SessionStart", "UserPromptSubmit", "PostToolUse", "Stop", "PreToolUse")
PLUGIN_NAME = "leadfuel-way"
OK, FAIL, UNKNOWN, WARN = "OK", "FAIL", "UNKNOWN", "WARN"


@dataclass
class Result:
    name: str
    status: str
    detail: str
    fix: str = ""


@dataclass
class Ctx:
    plugin_dir: Path
    home: Path = field(default_factory=Path.home)
    state_dir: Path | None = None
    hours: float = 24.0
    use_cli: bool = True
    cwd: Path = field(default_factory=Path.cwd)

    @property
    def hook_script(self) -> Path:
        return self.plugin_dir / "hooks" / "way_hook.py"


# --- helpers ------------------------------------------------------------------------------

def run(cmd, timeout=30, env=None, stdin=None, shell=False):
    try:
        done = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=timeout,
                              env=env, shell=shell, encoding="utf-8", errors="replace")
        return done.returncode, done.stdout, done.stderr
    except (OSError, subprocess.SubprocessError) as exc:
        return None, "", f"{type(exc).__name__}: {exc}"


def is_store_stub(path: str | None) -> bool:
    return bool(path) and "windowsapps" in path.replace("/", "\\").lower()


def verdict(results: list[Result]) -> str:
    counted = [r for r in results if r.status != WARN]
    if any(r.status == FAIL for r in counted):
        return "NOT LIVE"
    if all(r.status == OK for r in counted) and counted:
        return "LIVE"
    return "UNPROVEN"


def load_hooks_json(ctx: Ctx):
    return json.loads((ctx.plugin_dir / "hooks" / "hooks.json").read_text(encoding="utf-8"))


def expand(command: str, ctx: Ctx) -> str:
    return command.replace("${CLAUDE_PLUGIN_ROOT}", str(ctx.plugin_dir))


# --- checks -------------------------------------------------------------------------------

def check_python(ctx: Ctx) -> list[Result]:
    out = []
    path = shutil.which("python")
    if not path:
        out.append(Result("python resolves", FAIL, "`python` is not on PATH, so every hook command fails silently",
                          "install Python 3 and put it on PATH"))
    elif is_store_stub(path):
        out.append(Result("python resolves", FAIL, f"`python` is the Microsoft Store stub ({path})",
                          "install Python, or turn off the python.exe app execution alias"))
    else:
        code, so, se = run([path, "-c", "import sys; print('%d.%d' % sys.version_info[:2])"], timeout=20)
        if code == 0:
            out.append(Result("python resolves", OK, f"{path} (Python {so.strip()}); this shell's PATH, the app may differ"))
        else:
            out.append(Result("python resolves", FAIL, f"{path} exited {code}: {se.strip()[:120]}"))
    p3 = shutil.which("python3")
    if p3 and is_store_stub(p3):
        out.append(Result("python3 is a stub", WARN,
                          f"`python3` is the Microsoft Store stub ({p3}); any hook that calls it exits 49 and never runs",
                          "use `python` in hook commands"))
    return out


def check_manifests(ctx: Ctx) -> list[Result]:
    out = []
    try:
        meta = json.loads((ctx.plugin_dir / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
        ok = meta.get("name") == PLUGIN_NAME and bool(meta.get("version"))
        out.append(Result("plugin.json", OK if ok else FAIL, f"name={meta.get('name')} version={meta.get('version')}"))
    except (OSError, ValueError) as exc:
        out.append(Result("plugin.json", FAIL, f"{type(exc).__name__}: {exc}"))
    try:
        cfg = load_hooks_json(ctx)
    except (OSError, ValueError) as exc:
        out.append(Result("hooks.json registers every event", FAIL, f"{type(exc).__name__}: {exc}"))
        return out
    problems = []
    hooks = cfg.get("hooks") or {}
    for ev in EVENTS:
        groups = hooks.get(ev) or []
        cmds = [h.get("command", "") for g in groups for h in g.get("hooks", [])]
        if not cmds:
            problems.append(f"{ev}: not registered")
            continue
        for c in cmds:
            m = re.search(r'"([^"]+)"', expand(c, ctx))
            target = Path(m.group(1)) if m else None
            if not target or not target.is_file():
                problems.append(f"{ev}: command points at a file that does not exist ({target})")
    extra = sorted(set(hooks) - set(EVENTS))
    if "PreToolUse" in hooks and not (hooks["PreToolUse"][0].get("matcher")):
        problems.append("PreToolUse: no matcher, so the rule would run on every tool")
    out.append(Result("hooks.json registers every event", FAIL if problems else OK,
                      "; ".join(problems) if problems else f"{len(EVENTS)} events, each pointing at a real file"
                      + (f" (extra: {', '.join(extra)})" if extra else "")))
    skills = sorted(p.parent.name for p in (ctx.plugin_dir / "skills").glob("*/SKILL.md"))
    out.append(Result("skills present", OK if skills else FAIL, ", ".join(skills) or "no skills/*/SKILL.md found"))
    return out


def check_validate(ctx: Ctx) -> Result:
    name = "claude plugin validate"
    if not ctx.use_cli:
        return Result(name, UNKNOWN, "skipped (--no-cli)")
    claude = shutil.which("claude")
    if not claude:
        return Result(name, UNKNOWN, "the `claude` CLI is not on PATH, so the manifest was not validated")
    code, so, se = run([claude, "plugin", "validate", str(ctx.plugin_dir)], timeout=60)
    if code is None:
        return Result(name, UNKNOWN, se[:160])
    return Result(name, OK if code == 0 else FAIL, (so + se).strip().splitlines()[-1][:160] if (so + se).strip() else f"exit {code}")


def synthetic_run(ctx: Ctx, event: dict, workdir: Path, env_extra: dict):
    """Run the command hooks.json registers for this event, feeding it a synthetic event."""
    cfg = load_hooks_json(ctx)
    command = expand(cfg["hooks"][event["hook_event_name"]][0]["hooks"][0]["command"], ctx)
    env = {**os.environ, "WAY_STATE_DIR": str(workdir / "state"), **env_extra}
    for var in ("SESSION_GUARD_OFF", "WAY_ENFORCE_ROLES", "WAY_ARCHIVE_GUARD"):
        env.pop(var, None)
    code, so, se = run(command, timeout=20, env=env, stdin=json.dumps(event), shell=True)
    parsed = None
    if so.strip():
        try:
            parsed = json.loads(so)
        except ValueError:
            pass
    return code, parsed, se


def _now_iso() -> str:
    """Transcript records carry a timestamp; the hook counts only session reads from the last 10 minutes."""
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def _jl(path: Path, *recs: dict) -> int:
    with path.open("ab") as fh:
        for r in recs:
            fh.write((json.dumps(r) + "\n").encode("utf-8"))
    return path.stat().st_size


def _asst(tokens: int, content=None) -> dict:
    return {"type": "assistant", "isSidechain": False, "message": {
        "model": "claude-sonnet-5-5", "content": content or [{"type": "text", "text": "x"}],
        "usage": {"input_tokens": tokens, "cache_read_input_tokens": 0, "cache_creation_input_tokens": 0}}}


def check_synthetic(ctx: Ctx) -> list[Result]:
    """Make the hook speak: feed it synthetic sessions and read what it says."""
    out: list[Result] = []
    if not ctx.hook_script.is_file():
        return [Result("synthetic session", FAIL, f"{ctx.hook_script} does not exist")]
    caps = {"SESSION_SOFT_TOKENS": "1000", "SESSION_HARD_TOKENS": "50000"}
    with tempfile.TemporaryDirectory(prefix="way-doctor-") as tmp:
        tmp_path = Path(tmp)
        repo = tmp_path / "repo"
        (repo / ".git").mkdir(parents=True)
        tr = tmp_path / "t.jsonl"
        tr.write_bytes(b"")
        _jl(tr, {"type": "custom-title", "customTitle": "DOORS · T-1 1/1 · doctor"}, _asst(5000))
        base = {"session_id": "doctor-1", "transcript_path": str(tr)}

        def step(label, ev, want, **kw):
            try:
                code, parsed, err = synthetic_run(ctx, {**base, **ev}, tmp_path, kw.get("env", caps))
            except Exception as exc:  # noqa: BLE001
                out.append(Result(label, FAIL, f"could not run: {type(exc).__name__}: {exc}"))
                return
            if code != 0:
                out.append(Result(label, FAIL, f"hook exited {code}: {err.strip()[:140]}"))
                return
            ok, detail = want(parsed)
            out.append(Result(label, OK if ok else FAIL, detail))

        def text_of(p):
            return ((p or {}).get("hookSpecificOutput") or {}).get("additionalContext", "")

        step("hook: banner on SessionStart", {"hook_event_name": "SessionStart", "source": "startup"},
             lambda p: ("THE WAY" in text_of(p) and "DESK" in text_of(p),
                        "banner injected, role read from the title" if "THE WAY" in text_of(p) else f"no banner: {p!r}"[:160]))
        step("hook: guard speaks past the cap", {"hook_event_name": "UserPromptSubmit"},
             lambda p: ("CONTEXT BUDGET" in text_of(p), "guard spoke at ~5k vs a 1k test cap" if "CONTEXT BUDGET" in text_of(p) else f"silent: {p!r}"[:160]))
        step("hook: Stop gate blocks with no handoff", {"hook_event_name": "Stop"},
             lambda p: ((p or {}).get("decision") == "block", "Stop blocked" if (p or {}).get("decision") == "block" else f"did not block: {p!r}"[:160]))
        _jl(tr, {"type": "assistant", "isSidechain": False, "message": {"model": "x", "content": [
            {"type": "tool_use", "id": "w", "name": "Write", "input": {"file_path": str(repo / ".conductor" / "router" / "handoffs" / "router-000.md")}}],
            "usage": {"input_tokens": 5000}}})
        step("hook: Stop gate lets a handoff through", {"hook_event_name": "Stop"},
             lambda p: (not p, "Stop passed once a handoff write followed the crossing" if not p else f"still blocked: {p!r}"[:160]))

        coord = tmp_path / "c.jsonl"
        coord.write_bytes(b"")
        _jl(coord, {"type": "custom-title", "customTitle": "ROUTER #9"}, _asst(10))
        pre = {"session_id": "doctor-2", "transcript_path": str(coord), "hook_event_name": "PreToolUse",
               "tool_name": "Edit", "tool_input": {"file_path": str(repo / "src" / "app.py")}}

        def denied(p):
            d = ((p or {}).get("hookSpecificOutput") or {}).get("permissionDecision")
            return d == "deny", "ROUTER edit inside a checkout denied" if d == "deny" else f"not denied: {p!r}"[:160]

        step("hook: PreToolUse denies a router's edit", pre, denied)
        desk = tmp_path / "d.jsonl"
        desk.write_bytes(b"")
        _jl(desk, {"type": "custom-title", "customTitle": "DOORS · T-1 1/1 · x"}, _asst(10))
        step("hook: PreToolUse lets a desk edit", {**pre, "session_id": "doctor-3", "transcript_path": str(desk)},
             lambda p: (not p, "desk edit allowed" if not p else f"wrongly denied: {p!r}"[:160]))

        rt = tmp_path / "r.jsonl"
        rt.write_bytes(b"")
        _jl(rt, {"type": "custom-title", "customTitle": "ROUTER #9"}, _asst(10))
        arch = {"session_id": "doctor-4", "transcript_path": str(rt), "hook_event_name": "PreToolUse",
                "tool_name": "mcp__ccd_session_mgmt__archive_session", "tool_input": {"session_id": "self"}}
        step("hook: self-archive refused with no successor", arch,
             lambda p: (denied(p)[0], "ROUTER #9 self-archive refused: no successor seen" if denied(p)[0] else f"not refused: {p!r}"[:160]))
        row = {"sessionId": "local_x", "title": "ROUTER #10", "isArchived": False, "group": {"id": "g", "name": "ROUTER"}}
        _jl(rt, _asst(10, [{"type": "tool_use", "id": "me", "name": "mcp__ccd_session_mgmt__get_session", "input": {"session_id": "self"}}]),
            {"type": "user", "isSidechain": False, "timestamp": _now_iso(), "message": {"content": [
                {"type": "tool_result", "tool_use_id": "me", "content": [{"type": "text", "text": json.dumps({"sessionId": "local_me", "isArchived": False})}]}]}})
        _jl(rt, _asst(10, [{"type": "tool_use", "id": "ls", "name": "mcp__ccd_session_mgmt__list_sessions", "input": {"limit": 500}}]),
            {"type": "user", "isSidechain": False, "timestamp": _now_iso(), "message": {"content": [
                {"type": "tool_result", "tool_use_id": "ls", "content": [{"type": "text", "text": json.dumps([row])}]}]}})
        _jl(rt, _asst(10, [{"type": "tool_use", "id": "gx", "name": "mcp__ccd_session_mgmt__get_session", "input": {"session_id": "local_x"}}]),
            {"type": "user", "isSidechain": False, "timestamp": _now_iso(), "message": {"content": [
                {"type": "tool_result", "tool_use_id": "gx", "content": [{"type": "text", "text": json.dumps(row)}]}]}})
        step("hook: self-archive allowed once the successor is live", arch,
             lambda p: (not p, "allowed after list_sessions showed ROUTER #10 live in the group" if not p else f"still refused: {p!r}"[:160]))
        kid = {"sessionId": "local_kid", "title": "DOORS · T-1 1/1 · x", "isArchived": False, "group": {"id": "g", "name": "DOORS"}}
        _jl(rt, _asst(10, [{"type": "tool_use", "id": "ls2", "name": "mcp__ccd_session_mgmt__list_sessions", "input": {}}]),
            {"type": "user", "isSidechain": False, "timestamp": _now_iso(), "message": {"content": [
                {"type": "tool_result", "tool_use_id": "ls2", "content": [{"type": "text", "text": json.dumps([row, kid])}]}]}})
        step("hook: archive refused over an unread live listing row", arch,
             lambda p: (denied(p)[0], "archive refused: a live listed session with no parent field was never read with get_session (unknown, not clear)" if denied(p)[0] else f"not refused: {p!r}"[:160]))
    return out


def check_enabled(ctx: Ctx) -> Result:
    name = "plugin enabled"
    fix = ("owner step: claude plugin marketplace add <this repo>, then claude plugin install "
           f"{PLUGIN_NAME}@leadfuel (see the PR body)")
    if not ctx.use_cli:
        return Result(name, UNKNOWN, "skipped (--no-cli)")
    claude = shutil.which("claude")
    if not claude:
        return Result(name, UNKNOWN, "the `claude` CLI is not on PATH, so the installed plugins were not read")
    code, so, se = run([claude, "plugin", "list", "--json"], timeout=60)
    if code != 0:
        return Result(name, UNKNOWN, f"`claude plugin list --json` exited {code}: {se.strip()[:140]}")
    try:
        rows = json.loads(so)
    except ValueError:
        return Result(name, UNKNOWN, "`claude plugin list --json` did not return JSON")
    rows = rows if isinstance(rows, list) else rows.get("plugins", []) if isinstance(rows, dict) else []
    mine = [r for r in rows if isinstance(r, dict) and str(r.get("name") or r.get("id") or "").split("@")[0] == PLUGIN_NAME]
    if not mine:
        return Result(name, FAIL, f"{PLUGIN_NAME} is not installed ({len(rows)} other plugin(s) are)", fix)
    row = mine[0]
    enabled = row.get("enabled")
    if enabled is None:
        return Result(name, UNKNOWN, f"installed as {row.get('id') or row.get('name')}, but the list does not say whether it is enabled")
    if not enabled:
        return Result(name, FAIL, f"{row.get('id') or row.get('name')} is installed but disabled", f"claude plugin enable {PLUGIN_NAME}")
    return Result(name, OK, f"{row.get('id') or row.get('name')} {row.get('version', '')} enabled".strip())


def read_state_files(state_dir: Path):
    rows = []
    for p in sorted(state_dir.glob("*.json")) if state_dir.is_dir() else []:
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(d, dict):
            rows.append((p.stem, d))
    return rows


def check_real_sessions(ctx: Ctx) -> Result:
    name = "hooks have fired in real sessions"
    sdir = ctx.state_dir or Path(os.environ.get("WAY_STATE_DIR") or Path(tempfile.gettempdir()) / "leadfuel-way")
    rows = read_state_files(sdir)
    if not rows:
        return Result(name, UNKNOWN, f"no state files in {sdir}: the plugin is not installed, or no session has started since it was",
                      "install the plugin, start a fresh session, run the doctor again")
    cutoff = time.time() - ctx.hours * 3600
    recent = [(sid, d) for sid, d in rows if float(d.get("updated_at") or 0) >= cutoff]
    if not recent:
        return Result(name, UNKNOWN, f"{len(rows)} state file(s) in {sdir}, none touched in the last {ctx.hours:g}h")
    started = [(sid, d) for sid, d in recent if (d.get("seen") or {}).get("SessionStart")]
    if not started:
        events = sorted({e for _, d in recent for e in (d.get("seen") or {})})
        return Result(name, UNKNOWN, f"{len(recent)} recent session(s) fired {', '.join(events) or 'nothing'} but none fired SessionStart (they may predate the install)")
    bits = []
    for sid, d in started[:6]:
        bits.append(f"{sid[:8]} {d.get('role', '?')}{'/' + d['lane'] if d.get('lane') else ''} {d.get('model') or 'model?'} "
                    f"{(d.get('tokens') or 0) // 1000}k blocks={d.get('stops_blocked', 0)}")
    return Result(name, OK, f"{len(started)} of {len(recent)} recent session(s) saw the banner: " + "; ".join(bits))


def check_duplicates(ctx: Ctx) -> list[Result]:
    out = []
    user_copy = ctx.home / ".claude" / "skills" / PLUGIN_NAME
    if user_copy.exists():
        out.append(Result("duplicate skill copy", WARN,
                          f"{user_copy} still exists. Plugin skills are namespaced (`{PLUGIN_NAME}:way`), so the old `{PLUGIN_NAME}` skill "
                          "and the plugin's would both load.",
                          "owner step, after the plugin is installed and this doctor says LIVE: delete that folder (and its hooks/ and guard-settings.json)"))
    sdir = ctx.state_dir or Path(os.environ.get("WAY_STATE_DIR") or Path(tempfile.gettempdir()) / "leadfuel-way")
    try:
        ov = json.loads((sdir / "caps-override.json").read_text(encoding="utf-8"))
        if float(ov["expires"]) > time.time():
            out.append(Result("forced caps active", WARN,
                              f"every session on this machine is being told to hand off at {int(ov['soft']) // 1000}k (hard {int(ov['hard']) // 1000}k) "
                              f"until the override expires ({(float(ov['expires']) - time.time()) / 60:.0f} min)",
                              "python scripts/way_caps.py clear, when the pilot is over"))
    except (OSError, ValueError, KeyError, TypeError):
        pass
    for root in {ctx.cwd, *ctx.cwd.parents}:
        skills = root / ".claude" / "skills"
        copies = [s for s in ("handoff", "router") if (skills / s / "SKILL.md").is_file()]
        if copies and (root / ".git").exists():
            out.append(Result("repo-local skill copies", WARN, f"{skills} holds {', '.join(copies)}, which the plugin now supersedes",
                              "retire in a follow-up PR once the plugin is installed everywhere"))
            break
    for label, p in (("user settings", ctx.home / ".claude" / "settings.json"), ("project settings", ctx.cwd / ".claude" / "settings.json")):
        if not p.is_file():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            out.append(Result(f"{label} readable", WARN, f"{p} is not valid JSON"))
            continue
        if not isinstance(data, dict):
            out.append(Result(f"{label} readable", WARN, f"{p} holds {json.dumps(data)[:30]}, not an object: no hooks or plugins are configured there"))
            continue
        if re.search(r'"command"\s*:\s*"[^"]*\bpython3\b', json.dumps(data)):
            out.append(Result(f"{label} calls python3", WARN, f"{p} has a hook that calls `python3` (a Store stub here): it has never run",
                              "change it to `python`"))
    return out


UNCONDITIONAL_ARCHIVE = re.compile(r"archive yourself as your last act|archives itself as its last act|archives itself at handoff", re.I)


def check_handoff_archives(ctx: Ctx) -> Result:
    """The handoff skill's last step must keep the owner's rule (2026-10-02): no session leaves
    before its successor is live. With only a paste prompt it stays open; it archives itself only
    after `list_sessions` shows the successor live and `git ls-remote` shows nothing is unpushed.
    No skill may carry the older unconditional "archive yourself as your last act", which orphaned
    ROUTER #9's project. A static check on text the doctor reads in full, so OK or FAIL, never
    UNKNOWN. Whether a live session obeys is the hook guard's job (see the synthetic checks)."""
    name = "handoff: no self-archive before a live successor"
    stale = [p.parent.name for p in sorted((ctx.plugin_dir / "skills").glob("*/SKILL.md"))
             if UNCONDITIONAL_ARCHIVE.search(p.read_text(encoding="utf-8", errors="replace"))]
    if stale:
        return Result(name, FAIL, f"unconditional self-archive wording in: {', '.join(stale)}",
                      "a session archives itself only once its successor is live (owner, 2026-10-02)")
    path = ctx.plugin_dir / "skills" / "handoff" / "SKILL.md"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        return Result(name, FAIL, f"cannot read {path.name}: {type(exc).__name__}")
    section = re.search(r"^## Steps\n(.*?)(?=^## |\Z)", text, re.S | re.M)
    if not section:
        return Result(name, FAIL, "the handoff skill has no '## Steps' section")
    starts = [m.start() for m in re.finditer(r"^\d+\. ", section.group(1), re.M)]
    if not starts:
        return Result(name, FAIL, "the Steps section has no numbered steps")
    last = section.group(1)[starts[-1]:]
    low = last.lower()
    missing = [what for what, ok in (("archive_session", "archive_session" in last), ("self", "`self`" in last),
                                      ("git ls-remote", "git ls-remote" in last), ("list_sessions", "list_sessions" in last),
                                      ("'stay open'", "stay open" in low), ("'successor'", "successor" in low)) if not ok]
    earlier = section.group(1)[:starts[-1]].lower()
    if "push" not in earlier:
        missing.append("a push step before it")
    if missing:
        return Result(name, FAIL, f"the last step ({len(starts)}) does not keep the no-orphan rule; missing: {', '.join(missing)}",
                      "restore the step, or (if the owner withdraws the rule) change this check and its test together")
    return Result(name, OK, f"step {len(starts)}: stay open on a paste prompt; archive self only once list_sessions shows the "
                            "successor live and git ls-remote verifies the push")


def check_archive_guard_registered(ctx: Ctx) -> Result:
    """hooks.json must route archive_session through the hook, or the guard is text nobody runs."""
    name = "archive guard registered"
    try:
        groups = (load_hooks_json(ctx).get("hooks") or {}).get("PreToolUse") or []
    except (OSError, ValueError) as exc:
        return Result(name, FAIL, f"{type(exc).__name__}: {exc}")
    tools = ("mcp__ccd_session_mgmt__archive_session", "mcp__claude-code-remote__archive_session")
    for g in groups:
        matcher = str(g.get("matcher") or "")
        try:
            hits = [t for t in tools if re.fullmatch(matcher, t)]
        except re.error:
            continue
        if len(hits) == len(tools) and not re.fullmatch(matcher, "mcp__ccd_session_mgmt__unarchive_session") and g.get("hooks"):
            return Result(name, OK, f"PreToolUse matcher {matcher!r} covers archive_session (desktop and remote), not unarchive")
    return Result(name, FAIL, "no PreToolUse matcher sends archive_session to the hook",
                  "add a PreToolUse entry with matcher mcp__.*__archive_session pointing at way_hook.py")


# --- main ---------------------------------------------------------------------------------

def run_all(ctx: Ctx) -> list[Result]:
    results: list[Result] = []
    results += check_python(ctx)
    results += check_manifests(ctx)
    results.append(check_handoff_archives(ctx))
    results.append(check_archive_guard_registered(ctx))
    results.append(check_validate(ctx))
    results += check_synthetic(ctx)
    results.append(check_enabled(ctx))
    results.append(check_real_sessions(ctx))
    results += check_duplicates(ctx)
    return results


def render(results: list[Result]) -> str:
    width = max(len(r.name) for r in results)
    lines = []
    for r in results:
        lines.append(f"[{r.status:<7}] {r.name:<{width}}  {r.detail}")
        if r.fix and r.status != OK:
            lines.append(f"{'':11}{'':<{width}}  -> {r.fix}")
    counts = {s: sum(r.status == s for r in results) for s in (OK, FAIL, UNKNOWN, WARN)}
    lines.append("")
    lines.append(f"VERDICT: {verdict(results)}   ({counts[OK]} ok, {counts[FAIL]} fail, {counts[UNKNOWN]} unknown, {counts[WARN]} advisory)")
    lines.append("LIVE needs every check OK. UNKNOWN means the doctor could not see it, which is not a pass.")
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plugin-dir", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--hours", type=float, default=24.0, help="how recent a session must be to count")
    ap.add_argument("--no-cli", action="store_true", help="do not call the `claude` CLI (those checks report UNKNOWN)")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ctx = Ctx(plugin_dir=Path(args.plugin_dir).resolve(), hours=args.hours, use_cli=not args.no_cli)
    results = run_all(ctx)
    if args.json:
        print(json.dumps({"verdict": verdict(results), "results": [asdict(r) for r in results]}, indent=2))
    else:
        print(render(results))
    return {"LIVE": 0, "NOT LIVE": 1}.get(verdict(results), 2)


if __name__ == "__main__":
    sys.exit(main())
