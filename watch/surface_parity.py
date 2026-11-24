"""WATCH fold-x-G20: ask one question through every surface and fail when the answers differ.

CONNECTIONS.md gap G20: "Every surface gives the same answer". Surfaces: web, connector, arm
(required) and the NovahOS shell (the fourth surface, optional until the shell can be driven).

This module holds NO network code and NO credentials. Each surface is a command the owner
configures (a JSON file, see --config); the command receives the question on stdin and prints the
answer on stdout. Whatever that command reaches is the owner's decision (Law 9), not this file's,
and nothing is run unless the owner registers the weekly task. Nothing is a fallback: a surface
that cannot be asked is reported, never replaced by another.

Config example (parity-config.json):
    {"question": "What is the status of the hub nightly run?",
     "timeout_seconds": 120,
     "surfaces": {"web":       {"argv": ["python", "ask_web.py"]},
                  "connector": {"argv": ["python", "ask_connector.py"]},
                  "arm":       {"argv": ["python", "ask_arm.py"]},
                  "shell":     {"argv": ["python", "ask_shell.py"]}}}

Verdict (a check that cannot establish a state must not report one):
  * ok       every REQUIRED surface answered, and all answers (required and configured optional)
             agree after normalisation (case, whitespace, trailing punctuation).
  * failed   two or more surfaces answered and at least two answers differ. A difference is proof
             even if another surface was unreachable.
  * unknown  anything else: no config, a required surface not configured, a surface that timed
             out, errored or answered nothing while the rest agree, fewer than two answers, or the
             positive controls below came out wrong.

Positive controls run first on every invocation: samples with known verdicts (agree, differ, one
missing, none answered) are classified by the same code. A comparer that always says "ok" cannot
pass them, and then the result is `unknown`.

Stdlib only. Run by path:  python watch/surface_parity.py --config PATH [--write [PATH]]
Exit code: 0 ok, 1 failed, 2 unknown.
"""
import argparse
import datetime as dt
import json
import os
import re
import subprocess
import sys

SCHEMA = "watch.surface_parity/1"
REQUIRED = ("web", "connector", "arm")
OPTIONAL = ("shell",)
DEFAULT_TIMEOUT = 120
MAX_ANSWER_CHARS = 20000


def normalise(answer):
    """Compare meaning-neutral form: lower case, collapsed whitespace, no trailing punctuation."""
    if answer is None:
        return ""
    s = re.sub(r"\s+", " ", str(answer)).strip().lower()
    return s.rstrip(" .!?;:")


def classify(answers, required=REQUIRED, optional=OPTIONAL):
    """Pure verdict. `answers` maps surface name -> answer text, or None when it could not be asked.

    Returns {"state", "reason", "answered", "silent", "groups"}; groups lists surfaces that agree.
    """
    answered = {n: normalise(a) for n, a in answers.items() if normalise(a)}
    silent = sorted(n for n in answers if n not in answered)
    groups = {}
    for name, norm in sorted(answered.items()):
        groups.setdefault(norm, []).append(name)
    group_list = sorted(groups.values())
    out = {"state": "unknown", "reason": "", "answered": sorted(answered), "silent": silent,
           "groups": group_list}
    if len(answered) < 2:
        out["reason"] = f"only {len(answered)} surface(s) answered; parity cannot be judged"
        return out
    if len(group_list) > 1:
        out["state"] = "failed"
        out["reason"] = "answers differ: " + " | ".join("+".join(g) for g in group_list)
        return out
    not_configured = [n for n in required if n not in answers]
    missing_required = sorted(n for n in required if n in silent)
    if not_configured:
        out["reason"] = f"required surface(s) not configured: {not_configured}"
        return out
    if missing_required:
        out["reason"] = f"required surface(s) gave no answer: {missing_required}"
        return out
    out["state"] = "ok"
    extra = f" (silent optional: {silent})" if silent else ""
    out["reason"] = f"{len(answered)} surfaces gave the same answer{extra}"
    return out


def run_controls():
    """Known inputs with known verdicts through the same classifier."""
    same = "The nightly run passed."
    cases = [
        ("agree", {"web": same, "connector": same.upper(), "arm": " the nightly   run passed"}, "ok"),
        ("differ", {"web": same, "connector": same, "arm": "The nightly run failed."}, "failed"),
        ("one_silent", {"web": same, "connector": same, "arm": None}, "unknown"),
        ("none", {"web": None, "connector": "", "arm": None}, "unknown"),
        ("not_configured", {"web": same, "connector": same}, "unknown"),
        ("difference_beats_silence", {"web": same, "connector": "other", "arm": None}, "failed"),
    ]
    bad = [name for name, ans, want in cases if classify(ans)["state"] != want]
    return not bad, bad


def ask(surface_cfg, question, timeout):
    """Run one surface command with the question on stdin. Returns (answer or None, note)."""
    argv = surface_cfg.get("argv") if isinstance(surface_cfg, dict) else None
    if not argv or not isinstance(argv, list) or not all(isinstance(a, str) for a in argv):
        return None, "no argv configured"
    try:
        p = subprocess.run(argv, input=question, capture_output=True, text=True,
                           timeout=timeout, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return None, f"timed out after {timeout}s"
    except OSError as e:
        return None, f"could not start: {e.__class__.__name__}"
    if p.returncode != 0:
        return None, f"exit {p.returncode}"
    text = (p.stdout or "").strip()
    if not text:
        return None, "empty answer"
    return text[:MAX_ANSWER_CHARS], "ok"


def load_config(path):
    try:
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    except (OSError, ValueError) as e:
        return None, f"config unreadable: {e.__class__.__name__}"
    if (not isinstance(cfg, dict) or not isinstance(cfg.get("question"), str)
            or not cfg["question"].strip() or not isinstance(cfg.get("surfaces"), dict)):
        return None, "config needs a non-empty 'question' and a 'surfaces' object"
    return cfg, None


def check(config_path, now=None, runner=ask):
    now = now or dt.datetime.now(dt.timezone.utc)
    base = {"schema": SCHEMA, "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config_path": config_path}
    controls_ok, bad = run_controls()
    cfg, err = load_config(config_path) if config_path else (None, "no config path given")
    if err:
        return {**base, "state": "unknown", "reason": err, "controls_ok": controls_ok}
    timeout = cfg.get("timeout_seconds", DEFAULT_TIMEOUT)
    answers, notes = {}, {}
    for name, scfg in cfg["surfaces"].items():
        answers[name], notes[name] = runner(scfg, cfg["question"], timeout)
    out = classify(answers)
    if not controls_ok:
        out.update(state="unknown", reason=f"parity positive controls failed: {bad}")
    return {**base, **out, "controls_ok": controls_ok, "notes": notes,
            "question": cfg["question"]}


def default_status_path():
    base = os.environ.get("LOCALAPPDATA")
    return os.path.join(base, "surface-parity", "status.json") if base else None


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--config", required=True)
    ap.add_argument("--write", nargs="?", const="", default=None, metavar="PATH")
    args = ap.parse_args(argv)
    result = check(args.config)
    if args.write is not None:
        path = args.write or default_status_path()
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                json.dump(result, f, indent=1)
    print(json.dumps(result, indent=1))
    return {"ok": 0, "failed": 1}.get(result["state"], 2)


if __name__ == "__main__":
    sys.exit(main())
