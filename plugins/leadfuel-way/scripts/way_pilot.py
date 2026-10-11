#!/usr/bin/env python
"""Headless pilot of the way: one small Haiku run with a low soft cap, then read what the hooks did.

    python way_pilot.py [--plugin-dir DIR] [--model haiku] [--soft 5000] [--budget 1.00]
    python way_pilot.py --analyze STREAM.jsonl        # judge a stream you already have

It needs the `claude` CLI to be logged in (`claude auth status`). Nothing is installed and no
settings file is touched: the plugin is loaded for this one run with `--plugin-dir`, in a scratch git
repo, with the hook's state directory pointed at the scratch folder.

It asks three questions and answers each OK, FAIL or UNKNOWN, where UNKNOWN means the evidence was
not there to see (for example the model call failed, so no guard or Stop gate could have fired):
    (a) the banner: a SessionStart hook response carries the THE WAY banner.
    (b) the guard: a UserPromptSubmit or PostToolUse hook response carries CONTEXT BUDGET.
    (c) the Stop gate: a Stop hook response blocks, and a handoff write follows it.
Exit code: 0 all OK, 1 any FAIL, 2 otherwise.
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
import uuid
from pathlib import Path

OK, FAIL, UNKNOWN = "OK", "FAIL", "UNKNOWN"
PROMPT = ("Two steps, one short line of reply each. Step 1: run 'git log --oneline' and tell me the commit message. "
          "Step 2: create a file notes.txt containing the word done. Then stop.")
HANDOFF = re.compile(r"hand-?off", re.I)
WRITES = re.compile(r"\bgit\s+(add|commit|push)\b|>>?\s*\S|\btee\b|\b(Set|Add|Out)-Content\b|\bOut-File\b|\b(cp|mv)\s|\b(Copy|Move|New)-Item\b", re.I)


def records(lines):
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        if isinstance(rec, dict):
            yield rec


def _hook_output(rec: dict) -> str:
    return str(rec.get("output") or rec.get("stdout") or "")


def _context_of(output: str) -> str:
    """The text a hook injected: additionalContext (or the Stop reason) out of its JSON stdout."""
    try:
        data = json.loads(output)
    except ValueError:
        return output
    if not isinstance(data, dict):
        return output
    return str((data.get("hookSpecificOutput") or {}).get("additionalContext") or data.get("reason") or output)


def _is_handoff_write(block: dict) -> bool:
    name = str(block.get("name") or "")
    inp = block.get("input") or {}
    if name in ("Write", "Edit", "MultiEdit"):
        return bool(HANDOFF.search(str(inp.get("file_path") or "")))
    if name in ("Bash", "PowerShell"):
        cmd = str(inp.get("command") or "")
        return bool(HANDOFF.search(cmd) and WRITES.search(cmd))
    return False


def analyze(lines) -> list[tuple[str, str, str]]:
    """[(question, OK|FAIL|UNKNOWN, evidence)] from a stream-json log made with --include-hook-events."""
    banner = guard = None
    saw_hooks = blocked = handoff_after = passed_after = False
    model_ran, failure = False, ""
    for rec in records(lines):
        kind = rec.get("type")
        if kind == "system" and rec.get("subtype") == "hook_response":
            saw_hooks = True
            ev, out = rec.get("hook_event"), _hook_output(rec)
            text = _context_of(out)
            if ev == "SessionStart" and "THE WAY" in text and banner is None:
                banner = text.splitlines()[0][:110]
            elif ev in ("UserPromptSubmit", "PostToolUse") and "CONTEXT BUDGET" in text and guard is None:
                guard = f"{ev}: {text[:110]}"
            elif ev == "Stop":
                if ('"decision"' in out and "block" in out) or str(rec.get("outcome")).lower().startswith("block"):
                    blocked = True
                elif blocked and handoff_after:
                    passed_after = True
        elif kind == "assistant":
            msg = rec.get("message") or {}
            if rec.get("error") or rec.get("is_api_error_message") or msg.get("model") == "<synthetic>":
                failure = failure or str(rec.get("error") or "api error")
                continue
            model_ran = True
            if blocked:
                for block in msg.get("content") or []:
                    if isinstance(block, dict) and block.get("type") == "tool_use" and _is_handoff_write(block):
                        handoff_after = True
        elif kind == "result" and rec.get("is_error"):
            failure = f"{failure}; {rec.get('result')}" if failure else str(rec.get("result"))
    why = f"no model turn ran ({failure[:110] or 'no assistant record'}), so this could not fire"
    a_status = OK if banner else FAIL if (saw_hooks or model_ran) else UNKNOWN
    a_note = banner or ("hooks ran but none carried the banner" if a_status == FAIL else "no hook event in the stream at all: the plugin did not load, or the run died first")
    out = [("(a) banner injected at SessionStart", a_status, a_note)]
    out.append(("(b) guard spoke past the soft cap", OK if guard else (FAIL if model_ran else UNKNOWN),
                guard or (why if not model_ran else "the model ran past the cap and the guard never spoke")))
    if blocked and handoff_after and passed_after:
        out.append(("(c) Stop blocked until a handoff was written", OK, "Stop blocked, a handoff write followed, the next Stop passed"))
    elif blocked and handoff_after:
        out.append(("(c) Stop blocked until a handoff was written", OK, "Stop blocked and a handoff write followed (no second Stop was logged)"))
    elif blocked:
        out.append(("(c) Stop blocked until a handoff was written", FAIL, "Stop blocked, but no handoff write followed it"))
    else:
        out.append(("(c) Stop blocked until a handoff was written", FAIL if model_ran else UNKNOWN,
                    "the model ran and Stop never blocked" if model_ran else why))
    return out


def logged_in(claude: str) -> bool | None:
    try:
        done = subprocess.run([claude, "auth", "status"], capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
        return bool(json.loads(done.stdout).get("loggedIn"))
    except (OSError, subprocess.SubprocessError, ValueError):
        return None


def run_pilot(plugin_dir: Path, model: str, soft: int, budget: float) -> Path:
    claude = shutil.which("claude")
    if not claude:
        sys.exit("the `claude` CLI is not on PATH")
    if logged_in(claude) is False:
        sys.exit("the claude CLI is logged out (`claude auth status`): sign in once with `claude auth login`, then rerun")
    work = Path(tempfile.mkdtemp(prefix="way-pilot-"))
    repo = work / "repo"
    repo.mkdir()
    for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "pilot-noreply"], ["git", "config", "user.name", "pilot"]):
        subprocess.run(cmd, cwd=repo, check=True)
    (repo / "README.md").write_text("pilot repo\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", "pilot: first commit"], cwd=repo, check=True)
    env = {**os.environ, "SESSION_SOFT_TOKENS": str(soft), "SESSION_HARD_TOKENS": "1000000", "WAY_STATE_DIR": str(work / "state")}
    cmd = [claude, "-p", "--plugin-dir", str(plugin_dir), "--model", model, "--session-id", str(uuid.uuid4()),
           "--output-format", "stream-json", "--verbose", "--include-hook-events",
           "--permission-mode", "acceptEdits", "--allowedTools", "Bash", "Skill", "Write", "Read", "Edit",
           "--max-turns", "12", "--max-budget-usd", f"{budget:.2f}", PROMPT]
    stream = work / "stream.jsonl"
    with stream.open("wb") as fh:
        subprocess.run(cmd, cwd=repo, env=env, stdout=fh, stderr=subprocess.DEVNULL, timeout=600)
    print(f"stream: {stream}")
    return stream


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--plugin-dir", default=str(Path(__file__).resolve().parents[1]))
    ap.add_argument("--model", default="haiku")
    ap.add_argument("--soft", type=int, default=5000, help="SESSION_SOFT_TOKENS for the run (low, so the guard fires)")
    ap.add_argument("--budget", type=float, default=1.0)
    ap.add_argument("--analyze", help="judge an existing stream-json file instead of running")
    args = ap.parse_args(argv)
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    path = Path(args.analyze) if args.analyze else run_pilot(Path(args.plugin_dir).resolve(), args.model, args.soft, args.budget)
    results = analyze(path.read_text(encoding="utf-8", errors="replace").splitlines())
    for q, status, evidence in results:
        print(f"[{status:<7}] {q}: {evidence}")
    statuses = [s for _, s, _ in results]
    return 1 if FAIL in statuses else 0 if all(s == OK for s in statuses) else 2


if __name__ == "__main__":
    sys.exit(main())
