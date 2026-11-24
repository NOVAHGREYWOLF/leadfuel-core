"""NODE cluster-for-the-build (c): send small mechanical work to the local model on the RTX 3070.

Two parts, both refusing rather than falling through:

``classify(task)`` decides whether a task is small mechanical work (a sweep, lint, a docs fix, a
typo, a bump, formatting) that the local model may do. It answers ``local`` only on a positive
match AND no risk word AND an effort that is not high; everything else is ``not-local``, which
means "this helper will not do it", not "send it to the cloud". Choosing a cloud model is the
caller's decision (the router's ``route.py``), never this module's fallback.

``LocalModel`` talks to Ollama on THIS machine only. The endpoint must be a loopback address
(127.0.0.1, ::1, localhost); anything else is refused before a socket opens, unless the caller
names the exact private-LAN host in ``allow_lan`` (still never a public address). Any failure
raises ``LocalUnavailable``; there is no second endpoint and no vendor path anywhere in this file
(Law 9: nothing leaves the machine, a cloud path is a decision, never a fallback).

``placement()`` reads Ollama's ``/api/ps`` to say where the loaded model really sits: ``gpu``
(all of it in VRAM), ``partial``, ``cpu`` or ``unknown``. A model that is not loaded, or an
answer without the fields, is ``unknown``, never ``gpu``. ``run(..., require_gpu=True)`` raises
unless it reads ``gpu`` after the call, so a silently CPU-only Ollama (seen on this PC after an
update) cannot pass for the RTX 3070.

CLI (stdlib only)::

    python node/local_route.py classify '{"title": "lint sweep of docs/", "effort": "low"}'
    python node/local_route.py run --prompt-file p.txt [--model M] [--require-gpu]
    python node/local_route.py placement [--model M]
"""
from __future__ import annotations

import ipaddress
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

DEFAULT_ENDPOINT = "http://127.0.0.1:11434"
# Fits the 8 GB RTX 3070 Laptop with room for context (4.4 GB on disk, read from /api/tags
# on GREYWOLF 2026-11-23). The caller may name another installed model.
DEFAULT_MODEL = "qwen2.5:7b-instruct-q4_K_M"

LOCAL_KINDS = ("sweep", "lint", "docs", "doc", "typo", "bump", "format", "rename", "comment")
_LOCAL_WORDS = re.compile(
    r"\b(sweep|lint|linting|docs?|documentation|readme|typos?|spelling|bump|format(ting)?|"
    r"whitespace|rename|comments?|docstrings?|changelog)\b", re.I)
# Any of these makes a task not-local, whatever else it says (the router's route.py sends
# them to Opus; this helper must never be the cheaper path around that).
_RISK_WORDS = re.compile(
    r"\b(security|secrets?|credentials?|tokens?|passwords?|auth\w*|oauth|migrations?|migrate|"
    r"deploy\w*|production|prod|spend\w*|money|payments?|billing|doors?|egress|outward|send|"
    r"delete|drop|architecture|rewrite|critical|law ?9|consent|privacy)\b", re.I)
_HIGH_EFFORT = {"high", "xhigh", "max"}


@dataclass(frozen=True)
class Route:
    route: str   # "local" or "not-local"
    why: str


def classify(task: dict) -> Route:
    """``local`` only when the task is plainly small mechanical work; ``not-local`` otherwise."""
    if not isinstance(task, dict):
        return Route("not-local", "task is not an object")
    if task.get("model_pin"):
        return Route("not-local", f"model_pin {task['model_pin']!r} wins")
    text = " ".join(str(task.get(k) or "") for k in ("title", "kind", "summary"))
    if not text.strip():
        return Route("not-local", "no title, kind or summary to judge")
    effort = str(task.get("effort") or "").lower()
    if effort in _HIGH_EFFORT:
        return Route("not-local", f"effort {effort}")
    risk = _RISK_WORDS.search(text)
    if risk:
        return Route("not-local", f"risk word {risk.group(0)!r}")
    kind = str(task.get("kind") or "").lower()
    if kind in LOCAL_KINDS:
        return Route("local", f"kind {kind}")
    hit = _LOCAL_WORDS.search(text)
    if hit:
        return Route("local", f"mechanical word {hit.group(0)!r}")
    return Route("not-local", "no mechanical kind or word")


class LocalUnavailable(RuntimeError):
    """The local model could not do it. Callers decide what next; nothing here falls through."""


class NotLocal(ValueError):
    """The endpoint is not on this machine (or the named LAN host). Refused before connecting."""


def check_endpoint(endpoint: str, allow_lan: tuple[str, ...] = ()) -> str:
    u = urllib.parse.urlsplit(endpoint)
    if u.scheme != "http" or not u.hostname:
        raise NotLocal(f"endpoint {endpoint!r}: want http://<loopback>:<port>")
    host = u.hostname
    if host == "localhost":
        return endpoint.rstrip("/")
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        raise NotLocal(f"endpoint host {host!r} is a name, not a loopback address") from None
    if ip.is_loopback:
        return endpoint.rstrip("/")
    if host in allow_lan and ip.is_private and not ip.is_global:
        return endpoint.rstrip("/")
    raise NotLocal(f"endpoint host {host} is not loopback and not a named private LAN host")


def _http(method: str, url: str, body: dict | None, timeout: float) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method,
                                 headers={"Content-Type": "application/json"})
    # No proxy: a proxy would carry a loopback request off the machine.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(req, timeout=timeout) as r:
            return json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise LocalUnavailable(f"{method} {url}: {exc.__class__.__name__}: {exc}") from None


class LocalModel:
    def __init__(self, endpoint: str = DEFAULT_ENDPOINT, model: str = DEFAULT_MODEL,
                 allow_lan: tuple[str, ...] = (), timeout: float = 300.0, http=_http):
        self.endpoint = check_endpoint(endpoint, allow_lan)
        self.model = model
        self.timeout = timeout
        self._http = http

    def placement(self) -> str:
        """``gpu`` | ``partial`` | ``cpu`` | ``unknown`` for self.model, from /api/ps."""
        try:
            ps = self._http("GET", self.endpoint + "/api/ps", None, 10.0)
        except LocalUnavailable:
            return "unknown"
        for m in (ps or {}).get("models") or []:
            if m.get("name") != self.model and m.get("model") != self.model:
                continue
            size, vram = m.get("size"), m.get("size_vram")
            if not isinstance(size, int) or not isinstance(vram, int) or size <= 0:
                return "unknown"
            if vram >= size:
                return "gpu"
            return "partial" if vram > 0 else "cpu"
        return "unknown"

    def run(self, prompt: str, *, system: str | None = None, require_gpu: bool = False) -> dict:
        body = {"model": self.model, "prompt": prompt, "stream": False,
                "options": {"temperature": 0}}
        if system:
            body["system"] = system
        out = self._http("POST", self.endpoint + "/api/generate", body, self.timeout)
        text = out.get("response") if isinstance(out, dict) else None
        if not isinstance(text, str):
            raise LocalUnavailable("local model answered without a response field")
        where = self.placement()
        if require_gpu and where != "gpu":
            raise LocalUnavailable(f"model placement is {where}, not gpu (require_gpu)")
        return {"response": text, "model": self.model, "placement": where,
                "eval_count": out.get("eval_count"), "total_duration_ns": out.get("total_duration")}


def main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(prog="local_route")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("classify")
    c.add_argument("task_json")
    r = sub.add_parser("run")
    r.add_argument("--prompt-file", required=True)
    r.add_argument("--model", default=DEFAULT_MODEL)
    r.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    r.add_argument("--require-gpu", action="store_true")
    pl = sub.add_parser("placement")
    pl.add_argument("--model", default=DEFAULT_MODEL)
    pl.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    a = p.parse_args(argv)
    if a.cmd == "classify":
        route = classify(json.loads(a.task_json))
        print(json.dumps({"route": route.route, "why": route.why}))
        return 0 if route.route == "local" else 1
    lm = LocalModel(a.endpoint, a.model)
    if a.cmd == "placement":
        print(lm.placement())
        return 0
    try:
        with open(a.prompt_file, encoding="utf-8") as f:
            res = lm.run(f.read(), require_gpu=a.require_gpu)
    except LocalUnavailable as exc:
        print(f"LOCAL-UNAVAILABLE {exc}", file=sys.stderr)
        return 2
    print(json.dumps(res))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
