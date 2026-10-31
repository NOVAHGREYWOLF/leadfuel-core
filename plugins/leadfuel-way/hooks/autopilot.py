"""Autopilot gates for the way's hook (WAY-AUTOPILOT-1, plugin 0.1.16).

Autopilot is a mode in which one router runs a project from a goal brief to an MVP and asks the owner
only at hard gates (`leadfuel-way:autopilot`). OFF unless the owner switches it on for a project:
with no state file there is no autopilot anywhere, and this module returns None for every call.

What it does when a project is on, for every session whose title names that project (its router
`ROUTER #N · <project>`, its desks `LANE · <project> part · n`, and their background agents, whose
hook events carry the parent's title):
    1. Hard gates. A tool call that spends, touches credentials, sends or posts, changes deploy
       configuration, downloads, changes permission mode or settings, cannot be undone, or changes
       the autopilot's own switch is DENIED outright, never asked: in autopilot nobody is watching a
       permission prompt. These can never be allowed by the brief.
    2. Leaving the machine. Any other call that leaves the machine (a push, a PR write, a web fetch,
       a browser, a published page, any MCP tool not on the local list) is denied unless the owner
       named that kind in the project's `allow` list when he switched the mode on.
    3. Starting work. Opening a desk (Agent / Task) or arming a launch slot is denied until the
       early checkpoint card is recorded, and while weekly all-models usage is >= 88%, unknown, or
       older than its max age. A check that cannot establish the usage does not report it as low.
Every denial, and every call let through only by the owner's `allow` list, is appended to the audit
log `<state dir>/autopilot-log.jsonl`.

Unreadable state (the file exists but is not valid) is not "off": every session is gated as if its
project were on with nothing allowed, until the file is fixed or removed.

Shell commands are matched as text. A named pattern is a wall; what a script does once it runs is
not visible here, so for shells this is a strong nudge, not a sandbox. The spec says so too.
"""
from __future__ import annotations

import json
import os
import re
import tempfile
import time
from pathlib import Path

STATE_FILE = "autopilot.json"
LOG_FILE = "autopilot-log.jsonl"
USAGE_STOP_PCT = 88
USAGE_MAX_AGE_S = 6 * 3600

# Never autonomous, never allowable by the brief.
HARD = ("spend", "credentials", "send", "deploy-config", "download", "permission-mode",
        "irreversible", "autopilot-self")
# Leaves the machine; allowable only when the owner names the kind in `allow` at switch-on.
EGRESS_KINDS = ("git-push", "gh-pr", "gh-write", "web", "browser", "artifact-publish")  # plus "mcp:<tool>"

ROUTER_PROJECT = re.compile(r"^\s*ROUTER\s*#\s*\d+\s*·\s*(.+?)\s*$", re.I)
DESK_PROJECT = re.compile(r"^\s*(?!(?:ROUTER|CONDUCTOR)\b)[A-Z][A-Z0-9_-]+\s*·\s*([^·]*\S)\s+part\s*·\s*\d+\s*$")

# --- local tools: never gated -------------------------------------------------------------
# The board (ArtifactData) is claude.ai, not this machine, but it is the only channel to the owner:
# without it the mode could not even post the card for a gate. Listed for the owner to approve.
LOCAL_TOOLS = {"ArtifactData", "SendMessage", "TodoWrite", "ToolSearch", "Grep", "Glob", "Monitor",
               "TaskStop", "EnterWorktree", "ExitWorktree", "ListSkills", "ListPlugins", "SearchSkills"}
LOCAL_MCP = re.compile(
    r"^mcp__(ccd_turn|ccd_session|ccd_view|ccd_window|visualize)__"
    r"|^mcp__ccd_session_mgmt__(get_session|list_sessions|list_events|get_usage|search_session_transcripts"
    r"|send_message|set_session_title|archive_session|unarchive_session|export_transcript)$"
    r"|^mcp__ccd_sidebar__(list_groups|list_sections|move_sessions|set_unread|mark_completed|set_view)$"
    r"|^mcp__scheduled-tasks__(list_scheduled_tasks|list_task_runs)$"
)
START_WORK = {"Agent", "Task"}
SLOT_ID = re.compile(r"^way-slot-\d{2}$")

# --- paths --------------------------------------------------------------------------------
CRED_PATH = re.compile(
    r"(^|/)\.env(\.(?!example$|sample$|template$)[^/]*)?$|credential|(^|/)\.netrc$|\.pem$|\.p12$|\.pfx$"
    r"|(^|/)id_(rsa|ed25519|ecdsa)|\.git-credentials$|(^|/)\.npmrc$|(^|/)\.pypirc$|(^|/)secrets?(\.[a-z]+)?$"
    r"|\.key$", re.I)
DEPLOY_PATH = re.compile(
    r"(^|/)(railway\.(json|toml)|dockerfile[^/]*|docker-compose[^/]*\.ya?ml|procfile|nixpacks\.toml|fly\.toml"
    r"|vercel\.json|netlify\.toml|render\.ya?ml|app\.json)$|/\.github/workflows/", re.I)
PERMISSION_PATH = re.compile(r"/\.claude/settings(\.local)?\.json$|managed-settings|/\.githooks/", re.I)
SELF_PATH = re.compile(r"autopilot\.json$|autopilot-log\.jsonl$|way_autopilot\.py$|/hooks/autopilot\.py$"
                       r"|/hooks/way_hook\.py$|/hooks/hooks\.json$", re.I)

# --- shell --------------------------------------------------------------------------------
SH_SELF = re.compile(r"way_autopilot\.py\W+(on|allow)\b|autopilot\.json|autopilot-log\.jsonl", re.I)
SH_CRED = re.compile(
    r"\bgh\s+auth\b|\b(gh|railway)\s+(secret|variables?)\b|(^|[\s/\\'\"=])\.env\b(?!\.(example|sample|template))"
    r"|credential|\.git-credentials|id_(rsa|ed25519)|\.netrc|\.pypirc|\.npmrc|\b(Get|Export)-(Credential|PfxCertificate)\b",
    re.I)
SH_IRREVERSIBLE = re.compile(
    r"\bgit\s+push\b[^\n;|&]*(--force|--force-with-lease|\s-f\b|\s\+\S)|\bgit\s+reset\s+--hard\b|\brm\s+-[a-z]*r[a-z]*f"
    r"|\brm\s+-[a-z]*f[a-z]*r|\bRemove-Item\b[^\n;|]*-Recurse|\bgit\s+branch\s+-D\b|\bgit\s+clean\s+-[a-z]*f"
    r"|\bgit\s+worktree\s+remove\b|\bgit\s+stash\s+(drop|clear)\b|\bgh\s+repo\s+delete\b|\bdropdb\b|\bDROP\s+(TABLE|DATABASE)\b",
    re.I)
SH_PERMISSION = re.compile(r"settings(\.local)?\.json|\bcore\.hooksPath\b|\bSet-ExecutionPolicy\b|--dangerously|bypassPermissions", re.I)
SH_DEPLOY = re.compile(r"\brailway\b|checkSuites|\bdocker\s+(push|login)\b|\bvercel\b|\bflyctl\b|\bfly\s+deploy\b", re.I)
SH_SPEND = re.compile(r"\bstripe\b|\bpurchase\b|\bbilling\b", re.I)
SH_SEND = re.compile(r"\bSend-MailMessage\b|\bsendmail\b|\bmailx?\s|\btwilio\b|\bsmtp", re.I)
SH_DOWNLOAD_CMD = re.compile(r"\b(curl|wget|Invoke-WebRequest|iwr|Invoke-RestMethod|irm|Start-BitsTransfer|aria2c)\b", re.I)
SH_INSTALL = re.compile(r"\bgit\s+clone\b|\b(pip3?|uv|npm|pnpm|yarn|choco|winget|scoop|cargo|go)\s+(install|add|i|get)\b"
                        r"|\bnpx\s|\bpython\s+-m\s+pip\s+install\b", re.I)
SH_REMOTE = re.compile(r"\b(ssh|scp|sftp|rsync|ftp|telnet|nc|ncat)\s", re.I)
SH_PUSH = re.compile(r"\bgit\s+push\b([^\n;|&]*)", re.I)
SH_GH = re.compile(r"\bgh\s+([a-z-]+)(?:\s+([a-z-]+))?([^\n;|&]*)", re.I)
GH_PR_WRITE = {"create", "merge", "comment", "review", "edit", "close", "ready", "reopen"}
GH_READ = {"view", "list", "checks", "status", "diff", "watch", "checkout"}
URL = re.compile(r"https?://([^/\s'\"]+)", re.I)
LOCAL_HOST = re.compile(r"^(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$|\.localhost(:\d+)?$", re.I)

MCP_SPEND = re.compile(r"(pay|purchase|spend|billing|invoice|checkout|charge|subscri|buy|order)", re.I)
MCP_SEND = re.compile(r"(send|reply|forward|post|publish|approve|invite|share|campaign|webhook|respond|"
                      r"do_as_me|vacation|filter|withdraw|create_event|update_event|create_chat)", re.I)
MCP_DEPLOY = re.compile(r"(deploy|redeploy|restart|set-variables|create-service|update-service|delete-service|"
                        r"create-domain|update-domain|generate-domain|feature-flag|create-project|template|function|"
                        r"volume|bucket|tcp-proxy|connect-service)", re.I)
MCP_IRREVERSIBLE = re.compile(r"(delete|trash|remove|purge|clear_session|empty)", re.I)
MCP_PERMISSION = re.compile(r"(permission_mode|set_remote_control|set_session_connector_enabled|"
                            r"set_auto_merge|create_scheduled_task|delete_scheduled_task)", re.I)
MCP_CRED = re.compile(r"(credential|secret|token|auth|reconnect)", re.I)


def state_dir() -> Path:
    return Path(os.environ.get("WAY_STATE_DIR") or Path(tempfile.gettempdir()) / "leadfuel-way")


def state_path() -> Path:
    return state_dir() / STATE_FILE


def load(path: Path | None = None) -> tuple[str, dict]:
    """("absent" | "ok" | "unreadable", data). Absent is off. Unreadable is not off."""
    p = path or state_path()
    if not p.exists():
        return "absent", {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "unreadable", {}
    if not isinstance(data, dict) or not isinstance(data.get("projects", {}), dict):
        return "unreadable", {}
    return "ok", data


def project_of_title(title: str | None) -> str | None:
    """The project a router or project-form desk title names, or None."""
    t = title or ""
    m = ROUTER_PROJECT.match(t) or DESK_PROJECT.match(t)
    return " ".join(m.group(1).split()) if m else None


def active(data: dict, title: str | None, now: float | None = None) -> tuple[str, dict] | None:
    """(project, its config) when this session's project has autopilot on and unexpired, else None."""
    project = project_of_title(title)
    if not project:
        return None
    now = time.time() if now is None else now
    for name, cfg in (data.get("projects") or {}).items():
        if not isinstance(cfg, dict) or str(name).casefold() != project.casefold():
            continue
        if cfg.get("on") is not True:
            return None
        try:
            if float(cfg.get("expires") or 0) <= now:
                return None  # a lapsed switch is off: back to normal mode, where prompts reach the owner
        except (TypeError, ValueError):
            return None
        return name, cfg
    return None


def _norm(path: str) -> str:
    return str(path or "").replace("\\", "/")


def _shell_kind(cmd: str) -> tuple[str, str] | None:
    if SH_SELF.search(cmd):
        return "autopilot-self", "changes the autopilot switch, allow list or log"
    if SH_CRED.search(cmd):
        return "credentials", "touches credentials or secrets"
    if SH_IRREVERSIBLE.search(cmd):
        return "irreversible", "cannot be undone"
    if SH_PERMISSION.search(cmd):
        return "permission-mode", "changes settings, hooks or permission mode"
    if SH_DEPLOY.search(cmd):
        return "deploy-config", "deploy tooling or deploy configuration"
    if SH_SPEND.search(cmd):
        return "spend", "may spend"
    if SH_SEND.search(cmd):
        return "send", "sends a message"
    if SH_DOWNLOAD_CMD.search(cmd):
        hosts = URL.findall(cmd)
        if not hosts or not all(LOCAL_HOST.search(h) for h in hosts):
            return "download", "fetches from the network"
    if SH_INSTALL.search(cmd):
        return "download", "downloads or installs a package"
    if SH_REMOTE.search(cmd):
        return "send", "opens a remote shell or copies to another machine"
    for m in SH_PUSH.finditer(cmd):
        rest = m.group(1)
        if re.search(r"(^|\s|:)(main|master)\b|\s--(all|mirror|tags)\b", rest):
            return "irreversible", "pushes to main (a production deploy) or pushes everything"
        return "egress:git-push", "pushes a branch to a remote"
    for m in SH_GH.finditer(cmd):
        group, verb, rest = m.group(1).lower(), (m.group(2) or "").lower(), m.group(3) or ""
        if group == "api":
            if re.search(r"(-X|--method)\s*(POST|PUT|PATCH|DELETE)|\s-(f|F)\s|--field|--raw-field|--input", (verb + rest), re.I):
                return "egress:gh-write", "writes to GitHub through the API"
            continue
        if group == "pr" and verb in GH_PR_WRITE:
            return "egress:gh-pr", f"gh pr {verb}"
        if verb in GH_READ or group in ("help", "version", "--version"):
            continue
        return "egress:gh-write", f"gh {group} {verb}".strip()
    return None


def classify(tool: str, inp: dict) -> tuple[str, str] | None:
    """(gate, what) for a call that is a hard gate or leaves the machine, else None.
    gate is one of HARD, or "egress:<kind>"."""
    inp = inp if isinstance(inp, dict) else {}
    if tool in LOCAL_TOOLS:
        return None
    if tool in ("Read", "Edit", "Write", "MultiEdit", "NotebookEdit"):
        path = _norm(inp.get("file_path") or inp.get("notebook_path") or inp.get("path") or "")
        if tool != "Read" and SELF_PATH.search(path):
            return "autopilot-self", f"edits the autopilot's own gate or state ({path})"
        if CRED_PATH.search(path):
            return "credentials", f"opens a credential file ({path})"
        if tool != "Read" and PERMISSION_PATH.search(path):
            return "permission-mode", f"edits settings or hooks ({path})"
        if tool != "Read" and DEPLOY_PATH.search(path):
            return "deploy-config", f"edits deploy configuration ({path})"
        return None
    if tool in ("Bash", "PowerShell"):
        return _shell_kind(str(inp.get("command") or ""))
    if tool in ("WebFetch", "WebSearch"):
        return "egress:web", tool
    if tool == "Skill":
        skill = str(inp.get("skill") or "").lower()
        if skill.endswith(("update-config", "fewer-permission-prompts", "keybindings-help")):
            return "permission-mode", f"skill {skill} changes settings"
        if skill.endswith("schedule"):
            return "egress:mcp:schedule", "cloud routines run off this machine"
        return None
    if tool in ("Artifact", "ArtifactComments"):
        action = str(inp.get("action") or "publish").lower()
        if action in ("read", "list", "open", "quickstart", "get"):
            return None
        if action == "delete":
            return "irreversible", f"{tool} delete"
        return "egress:artifact-publish", f"{tool} {action}"
    if tool in START_WORK:
        if str(inp.get("isolation") or "") == "remote":
            return "egress:mcp:remote-agent", "a remote agent runs off this machine"
        return None
    if tool.startswith("mcp__"):
        if LOCAL_MCP.search(tool):
            return None
        last = tool.rsplit("__", 1)[-1]
        if tool.endswith("__update_scheduled_task"):
            if SLOT_ID.match(str(inp.get("taskId") or inp.get("task_id") or "")):
                return None  # arming a launch slot (`leadfuel-way:launch`): local, and the start-work gate applies
            return "permission-mode", "changes a scheduled task (standing configuration)"
        for rx, gate in ((MCP_PERMISSION, "permission-mode"), (MCP_CRED, "credentials"), (MCP_SPEND, "spend"),
                         (MCP_IRREVERSIBLE, "irreversible"), (MCP_SEND, "send"), (MCP_DEPLOY, "deploy-config")):
            if rx.search(last):
                return gate, tool
        if "claude-in-chrome" in tool or "Claude_Browser" in tool:
            return "egress:browser", tool
        return f"egress:mcp:{last}", f"{tool} leaves the machine"
    return None


def _starts_work(tool: str, inp: dict) -> bool:
    if tool in START_WORK:
        return True
    return tool.endswith(("__update_scheduled_task", "__run_scheduled_task", "__start_session")) and (
        tool.endswith(("__run_scheduled_task", "__start_session")) or bool(str(inp.get("fireAt") or "").strip()))


def start_work_refusal(cfg: dict, now: float | None = None) -> str | None:
    now = time.time() if now is None else now
    if not str(cfg.get("checkpoint_card") or "").strip():
        return ("no early checkpoint card is recorded. Post it on the Router desk page (the plan, the MVP line, "
                "the decisions you will take alone, \"say stop if wrong\"), then record it with "
                "`way_autopilot.py checkpoint --project <p> --card q<N>`.")
    usage = cfg.get("usage") if isinstance(cfg.get("usage"), dict) else {}
    try:
        pct, at = float(usage["weekly_pct"]), float(usage["at"])
    except (KeyError, TypeError, ValueError):
        return "weekly all-models usage is unknown. Unknown is not low: record it with `way_autopilot.py usage`."
    max_age = float(cfg.get("usage_max_age_s") or USAGE_MAX_AGE_S)
    if now - at > max_age:
        return f"the recorded weekly usage is {int((now - at) // 60)} minutes old (max {int(max_age // 60)}). Re-read it and record it."
    if pct >= USAGE_STOP_PCT:
        return (f"weekly all-models usage is {pct:g}%, at or past the {USAGE_STOP_PCT}% stop. Start nothing: post the "
                "stop card with the decision log, write the handoff and stop.")
    return None


def log(entry: dict) -> None:
    try:
        state_dir().mkdir(parents=True, exist_ok=True)
        with (state_dir() / LOG_FILE).open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({"at": time.time(), **entry}) + "\n")
    except OSError:
        pass


def decide(tool: str, inp: dict, title: str | None, now: float | None = None,
           path: Path | None = None) -> str | None:
    """The reason to deny this call under autopilot, or None. Logs every denial and every call let
    through only by the owner's allow list."""
    status, data = load(path)
    if status == "absent":
        return None
    if status == "unreadable":
        project, cfg = "(unknown: autopilot.json is unreadable)", {"allow": []}
    else:
        hit = active(data, title, now)
        if hit is None:
            return None
        project, cfg = hit
    inp = inp if isinstance(inp, dict) else {}
    found = classify(tool, inp)
    reason = None
    if found:
        gate, what = found
        allow = {str(a) for a in (cfg.get("allow") or [])}
        if gate in HARD:
            reason = (f"AUTOPILOT HARD GATE ({gate}): {what}. In autopilot this is never decided alone and never "
                      "asked as a prompt. Post one card on the Router desk page with options and a default, log it "
                      "(`way_autopilot.py decide`), and carry on with work that does not need it, or stop.")
        elif gate.split(":", 1)[1] not in allow:
            reason = (f"AUTOPILOT: this leaves the machine ({gate.split(':', 1)[1]}: {what}) and the owner did not "
                      f"allow that kind for project '{project}' when he switched autopilot on. Post a card, log it, "
                      "and continue with local work.")
        else:
            log({"project": project, "tool": tool, "gate": gate, "what": what, "decision": "allowed-by-owner-list"})
    if reason is None and _starts_work(tool, inp):
        why = "autopilot state is unreadable" if status == "unreadable" else start_work_refusal(cfg, now)
        if why:
            reason = f"AUTOPILOT: no new desk or session may start: {why}"
    if reason:
        log({"project": project, "tool": tool, "gate": (found or ("start-work", ""))[0], "decision": "denied",
             "reason": reason[:400]})
    return reason
