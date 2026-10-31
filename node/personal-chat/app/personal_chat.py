"""Personal chat: a private chat window on the person's own computer, answered by a local model.

What it is: a tiny local web app (stdlib only) bound to 127.0.0.1, which the browser opens. It
talks to Ollama on the same computer and to nothing else.

What it refuses, on purpose:
  * A cloud path. The model host must be loopback; anything else raises CloudPathRefused at
    start-up instead of quietly reaching a vendor (estate rule: "a cloud path must be a
    decision, not a fallback"). There is no vendor key and no vendor client in this app.
  * Guessing a tier. The model comes from the spec check's verdict (NodeSpec.ps1 on Windows,
    run by the installer). With no verdict it uses the ladder's CPU-ONLY row and SAYS the tier
    is unknown; it never claims a tier it did not measure.
  * Claiming a licence. Licence state comes from seats.check(), which says `preview` for every
    build made before the store is configured.

The ONLY copy of the tier ladder is home-node/installer/NodeSpec.ps1. This app reads the
ladder.json the build exports from it; no threshold or model name is written in this file.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)

import seats  # noqa: E402

LOOPBACK = {"127.0.0.1", "localhost", "::1"}
DEFAULT_OLLAMA = "http://127.0.0.1:11434"
MAX_BODY = 1_000_000


class CloudPathRefused(RuntimeError):
    pass


def bundle_dir() -> str:
    """Where the read-only files live: next to the frozen exe, or next to this file."""
    base = getattr(sys, "_MEIPASS", None)
    return base or HERE


def home_dir() -> str:
    """Per-user writable folder: config.json, seat.json, install_id."""
    override = os.environ.get("PERSONAL_CHAT_HOME")
    if override:
        return override
    if sys.platform == "win32":
        return os.path.join(os.environ.get("APPDATA") or os.path.expanduser("~"), "PersonalChat")
    if sys.platform == "darwin":
        return os.path.expanduser("~/Library/Application Support/PersonalChat")
    return os.path.join(os.path.expanduser("~"), ".config", "personal-chat")


def load_json(path: str):
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, ValueError):
        return None


def require_loopback(url: str) -> str:
    parts = urllib.parse.urlsplit(url if "://" in url else "http://" + url)
    host = (parts.hostname or "").lower()
    if parts.scheme != "http" or host not in LOOPBACK:
        raise CloudPathRefused(
            f"model host {url!r} is not this computer; personal chat only talks to a local model")
    port = parts.port or 11434
    h = f"[{host}]" if ":" in host else host
    return f"http://{h}:{port}"


def ollama_base() -> str:
    return require_loopback(os.environ.get("OLLAMA_HOST") or DEFAULT_OLLAMA)


def resolve_tier(config, ladder) -> dict:
    """The model to use, and whether the tier was measured.

    config: the installer's config.json (holds the spec check's tier verdict) or None.
    ladder: ladder.json exported from NodeSpec.ps1 at build time, or None.
    """
    if isinstance(config, dict) and isinstance(config.get("tier"), dict) \
            and config["tier"].get("chatModel"):
        t = config["tier"]
        return {"tier": t.get("tier", "unknown"), "chatModel": t["chatModel"],
                "measured": True, "note": t.get("note", "")}
    if isinstance(ladder, dict) and isinstance(ladder.get("cpuOnly"), dict) \
            and ladder["cpuOnly"].get("chatModel"):
        c = ladder["cpuOnly"]
        return {"tier": "unknown", "chatModel": c["chatModel"], "measured": False,
                "note": "The spec check has not run on this computer, so the smallest model "
                        "on the ladder is used until it does."}
    return {"tier": "unknown", "chatModel": None, "measured": False,
            "note": "No tier verdict and no ladder in this build. Reinstall."}


def _post(url: str, body: dict, timeout: float):
    req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), method="POST",
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def ollama_state(base: str) -> dict:
    """running / models, or running False with the reason. Never raises."""
    try:
        with urllib.request.urlopen(base + "/api/tags", timeout=3) as r:
            data = json.loads(r.read().decode("utf-8"))
        return {"running": True, "models": [m.get("name") for m in data.get("models", [])]}
    except (OSError, ValueError) as e:
        return {"running": False, "models": [], "reason": type(e).__name__}


def chat(base: str, model: str, messages: list, post=_post) -> str:
    if not model:
        raise ValueError("no model chosen")
    clean = [{"role": m["role"], "content": str(m["content"])} for m in messages
             if isinstance(m, dict) and m.get("role") in ("user", "assistant", "system")]
    data = post(base + "/api/chat", {"model": model, "messages": clean, "stream": False}, 600)
    return (data.get("message") or {}).get("content", "")


class App:
    def __init__(self, bundle: str, home: str, base: str):
        self.bundle, self.home, self.base = bundle, home, base
        self.build = load_json(os.path.join(bundle, "build_info.json")) or {}
        self.ladder = load_json(os.path.join(bundle, "ladder.json"))
        self.config = load_json(os.path.join(home, "config.json"))
        self.tier = resolve_tier(self.config, self.ladder)
        self.stop = threading.Event()

    def status(self) -> dict:
        return {"build": {"version": self.build.get("version", "dev"),
                          "signed": bool(self.build.get("signed"))},
                "tier": self.tier, "ollama": ollama_state(self.base),
                "licence": seats.check(self.home, self.build).as_dict()}


def make_handler(app: App):
    class Handler(BaseHTTPRequestHandler):
        server_version = "PersonalChat"

        def log_message(self, *a):  # keep the console quiet; nothing is logged to disk
            pass

        def _send(self, code: int, body, ctype="application/json"):
            raw = body if isinstance(body, bytes) else json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(raw)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(raw)

        def _same_origin(self) -> bool:
            # A page on another site must not be able to drive this app through the browser.
            origin = self.headers.get("Origin")
            host = self.headers.get("Host", "")
            return origin is None or origin in (f"http://{host}",)

        def do_GET(self):
            if self.path in ("/", "/index.html"):
                with open(os.path.join(app.bundle, "static", "index.html"), "rb") as f:
                    return self._send(200, f.read(), "text/html; charset=utf-8")
            if self.path == "/api/status":
                return self._send(200, app.status())
            return self._send(404, {"error": "not found"})

        def do_POST(self):
            if not self._same_origin():
                return self._send(403, {"error": "cross-origin request refused"})
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._send(413, {"error": "too large"})
            try:
                body = json.loads(self.rfile.read(n) or b"{}")
            except ValueError:
                return self._send(400, {"error": "bad json"})
            if self.path == "/api/chat":
                try:
                    reply = chat(app.base, app.tier["chatModel"], body.get("messages") or [])
                except (OSError, ValueError) as e:
                    return self._send(503, {"error": f"the local model did not answer ({type(e).__name__})"})
                return self._send(200, {"reply": reply})
            if self.path == "/api/activate":
                try:
                    st = seats.activate(body.get("key", ""), app.home, app.build)
                except seats.SeatError as e:
                    return self._send(400, {"error": str(e)})
                return self._send(200, st.as_dict())
            if self.path == "/api/quit":
                app.stop.set()
                return self._send(200, {"ok": True})
            return self._send(404, {"error": "not found"})

    return Handler


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    try:
        base = ollama_base()
    except CloudPathRefused as e:
        print(f"Personal chat will not start: {e}")
        return 2
    app = App(bundle_dir(), home_dir(), base)
    srv = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(app))
    url = f"http://127.0.0.1:{srv.server_address[1]}/"
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    print(f"Personal chat is running at {url}", flush=True)
    print("Close this window, or press Quit in the app, to stop it.", flush=True)
    if "--no-browser" not in argv:
        webbrowser.open(url)
    try:
        app.stop.wait()
    except KeyboardInterrupt:
        pass
    srv.shutdown()
    return 0


if __name__ == "__main__":
    sys.exit(main())
