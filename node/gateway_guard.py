#!/usr/bin/env python3
"""Guard for the local model gateway files (queue item oss-3): llama-swap behind LiteLLM, local only.

  python node/gateway_guard.py [--dir node/gateway]     exit 0 clean, 1 with every finding printed

Reads node/gateway/litellm_config.yaml and llama-swap.yaml as text. Opens no socket, starts nothing.
A cloud route is a named decision behind the approval gate, never a config entry, so this fails on:
  * any `api_base` whose host is not loopback, RFC 1918, tailnet or a LAN-style name;
  * any litellm_params `model` that is not `openai/<name>` (the OpenAI-compatible local route), so a
    provider prefix such as anthropic/, gemini/, azure/, bedrock/ or vertex_ai/ cannot be listed;
  * any route without its own `api_base` (LiteLLM would then use the vendor's default URL);
  * any `api_key` other than the literal `none`, and any `os.environ/` reference (no secret here);
  * any fallback key (fallbacks, context_window_fallbacks, content_policy_fallbacks, ...) at all,
    local-to-local included: no silent route change;
  * any callback or hosted logger, telemetry not set to false, or a master key / database url set;
  * a llama-swap model whose cmd fetches from a URL (http, --hf-repo, -hf, --model-url).
A missing file is a failure, never a pass. Stdlib only.
"""
from __future__ import annotations

import argparse
import ipaddress
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
LAN_NETS = [ipaddress.ip_network(n) for n in (
    "10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "100.64.0.0/10", "127.0.0.0/8", "fd00::/8", "::1/128")]
LAN_SUFFIXES = (".lan", ".local", ".internal", ".home.arpa", ".ts.net")
FALLBACK_KEY = re.compile(r"^\s*-?\s*\w*fallbacks?\s*:", re.I)
CALLBACK_KEY = re.compile(r"^\s*(success_callback|failure_callback|callbacks|service_callback|"
                          r"langfuse\w*|otel\w*|sentry\w*)\s*:", re.I)
KEY_LINE = re.compile(r"^\s*-?\s*([\w\-\"']+)\s*:\s*(.*?)\s*$")


def host_is_private(host: str) -> bool:
    host = (host or "").strip("[]").lower()
    if not host:
        return False
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return host == "localhost" or "." not in host or host.endswith(LAN_SUFFIXES)
    return any(ip.version == n.version and ip in n for n in LAN_NETS)


def _unq(v: str) -> str:
    return v.strip().strip("\"'")


def check_litellm(text: str) -> list:
    out = []
    telemetry = None
    blocks, cur = [], None
    for n, raw in enumerate(text.splitlines(), 1):
        line = raw.split(" #", 1)[0].rstrip()
        if line.lstrip().startswith("#") or not line.strip():
            continue
        if re.match(r"^\s*-\s*model_name\s*:", line):
            cur = {"line": n, "kv": {}}
            blocks.append(cur)
        m = KEY_LINE.match(line)
        if not m:
            continue
        k, v = _unq(m.group(1)), _unq(m.group(2))
        if FALLBACK_KEY.match(line):
            out.append("line %d: fallback key %r (no fallback of any kind is allowed)" % (n, k))
        if CALLBACK_KEY.match(line):
            out.append("line %d: callback or hosted logger %r" % (n, k))
        if k == "telemetry":
            telemetry = v.lower()
        if k in ("master_key", "database_url", "salt_key") and v:
            out.append("line %d: %s must not be set in this file" % (n, k))
        if "os.environ/" in v:
            out.append("line %d: environment secret reference %r (no secret belongs here)" % (n, v))
        if cur is not None and k in ("model", "api_base", "api_key"):
            cur["kv"][k] = (v, n)
    if telemetry != "false":
        out.append("litellm_settings.telemetry must be false (found %r)" % telemetry)
    if not blocks:
        out.append("no model_list entries found")
    for b in blocks:
        kv = b["kv"]
        model = kv.get("model")
        if not model or not re.fullmatch(r"openai/[\w.\-:]+", model[0]):
            out.append("line %d: model %r is not openai/<name> (a provider prefix is a cloud route)"
                       % (model[1] if model else b["line"], model[0] if model else None))
        base = kv.get("api_base")
        if not base:
            out.append("line %d: route has no api_base (LiteLLM would use the vendor default)" % b["line"])
        else:
            p = urllib.parse.urlparse(base[0])
            if p.scheme not in ("http", "https") or p.username or not host_is_private(p.hostname or ""):
                out.append("line %d: api_base %r is not a private http(s) address" % (base[1], base[0]))
        key = kv.get("api_key")
        if key and key[0] != "none":
            out.append("line %d: api_key must be the literal none" % key[1])
    return out


def check_llama_swap(text: str) -> list:
    out = []
    if not re.search(r"^models\s*:", text, re.M):
        out.append("no models: block")
    for n, raw in enumerate(text.splitlines(), 1):
        m = re.match(r"^\s*cmd\s*:\s*(.*)$", raw)
        if m and re.search(r"https?://|--hf-repo|(^|\s)-hf(\s|$)|--model-url|(^|\s)-mu(\s|$)", m.group(1)):
            out.append("line %d: model command fetches from the network" % n)
    return out


def check_dir(d: str = os.path.join(HERE, "gateway")) -> list:
    out = []
    for name, fn in (("litellm_config.yaml", check_litellm), ("llama-swap.yaml", check_llama_swap)):
        try:
            with open(os.path.join(d, name), encoding="utf-8") as fh:
                text = fh.read()
        except OSError as exc:
            out.append("%s: cannot read (%s); a missing file is a failure, not a pass" % (name, exc))
            continue
        out += ["%s: %s" % (name, f) for f in fn(text)]
    return out


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dir", default=os.path.join(HERE, "gateway"))
    findings = check_dir(ap.parse_args(argv).dir)
    for f in findings:
        print("FAIL", f)
    if not findings:
        print("gateway guard: clean (local endpoints only, no fallback, no callback)")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
