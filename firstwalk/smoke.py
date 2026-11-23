r"""SURFACE firstwalk: a read-only smoke pass for the owner's first-user walk of NovahOS.

    python firstwalk/smoke.py run --out results.json [--hub-root DIR] [--artifacts-root DIR] ...
    python firstwalk/smoke.py controls        # only the positive controls

The walk itself (the 15 lines and the nine rooms in `walk.json`) is the OWNER'S. This script never
walks anything and never writes a walk result. It writes one file in which every cell has:

  * `walk_state`   not_tested | pass | fail | closed_by_design. It changes ONLY when the owner's
                   exported marks file is passed in (`--marks`). A smoke result never moves it.
  * `smoke_result` pass | fail | unknown | not_run. A PREFLIGHT: what answers on this machine today.

Rules (a check that cannot establish a state must not report one):
  * A probe that times out or is cut off is `unknown`, never `fail` and never `pass` (busy is not down).
  * Only a refused connection or an answer that contradicts the expectation is `fail`.
  * A check whose subject cannot be read (no file, no input given) is `unknown`.
  * A check that RAISES is `unknown` with the exception named.
  * Before every run the reader classifies built-in samples whose answers are known (an environment
    that answers 200 to everything must NOT read as "signed-out requests are refused"; an environment
    where everything is absent or raises must produce no `pass`). If a control comes out wrong the
    whole run is `unknown`.

READ-ONLY, AND NOTHING LEAVES THE MACHINE (Law 9).
  * HTTP and TCP go to loopback only; any other host is refused before a socket exists. No proxy.
    Redirects are NOT followed (a redirect off this machine is reported, never followed).
  * It starts, stops and writes nothing except its own `--out` file. The one opt-in call that makes
    a local model do work is `--model-call` (a tiny local chat on loopback; it unloads the model).

Stdlib only. Run by path.
"""
import argparse
import datetime as dt
import hashlib
import html
import json
import os
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request

SCHEMA_RESULTS = "firstwalk.results/1"
SCHEMA_CELL = "firstwalk.cell/1"
SCHEMA_MARKS = "firstwalk.marks/1"
PASS, FAIL, UNKNOWN, NOT_RUN = "pass", "fail", "unknown", "not_run"
CHECK_STATES = (PASS, FAIL, UNKNOWN)
WALK_STATES = ("not_tested", "pass", "fail", "closed_by_design")
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
MAX_BODY = 256 * 1024

OLLAMA = "http://127.0.0.1:11434"
HUB = "http://127.0.0.1:8080"
MCP = "http://127.0.0.1:8787"
WINDOW = "http://127.0.0.1:8766"
PRIME_DASH = "http://127.0.0.1:8765"
CHARDESIGN = "http://127.0.0.1:8760"
COMFY = "http://127.0.0.1:8188"
PG_PORT = 5432
PHONE_PORT = 8106


class Refused(Exception):
    """The far end actively refused the connection: established as not answering."""


class NoAnswer(Exception):
    """No answer in time, or the exchange broke: we could not tell."""


class Reply:
    def __init__(self, status, headers=None, body=b""):
        self.status = status
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}
        self.body = body or b""

    def json(self):
        try:
            return json.loads(self.body.decode("utf-8", "replace"))
        except ValueError:
            return None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


# ----------------------------------------------------------------------------- the environment

class RealEnv:
    """Every OS touch. A test hands a fake with the same methods. A method returns None when it
    cannot read its subject; `http` and `tcp` raise Refused or NoAnswer."""

    def now(self):
        return dt.datetime.now(dt.timezone.utc)

    @staticmethod
    def _loopback_only(host):
        if (host or "") not in LOOPBACK_HOSTS:
            raise PermissionError("firstwalk probes loopback only; refused %r" % (host,))

    def http(self, url, method="GET", body=None, timeout=5.0):
        self._loopback_only(urllib.parse.urlsplit(url).hostname)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), _NoRedirect())
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(url, data=data, method=method,
                                     headers={"Content-Type": "application/json"} if data else {})
        try:
            with opener.open(req, timeout=timeout) as r:                    # noqa: S310 (loopback)
                return Reply(r.status, dict(r.headers.items()), r.read(MAX_BODY))
        except urllib.error.HTTPError as e:
            try:
                b = e.read(MAX_BODY)
            except Exception:                                               # noqa: BLE001
                b = b""
            return Reply(e.code, dict(e.headers.items()) if e.headers else {}, b)
        except urllib.error.URLError as e:
            if isinstance(e.reason, ConnectionRefusedError):
                raise Refused(str(e.reason))
            raise NoAnswer(str(e.reason))
        except (socket.timeout, TimeoutError) as e:
            raise NoAnswer("timed out (%s)" % (e,))
        except ConnectionRefusedError as e:
            raise Refused(str(e))
        except OSError as e:
            raise NoAnswer(str(e))

    def tcp(self, host, port, timeout=4.0):
        self._loopback_only(host)
        try:
            s = socket.create_connection((host, port), timeout)
            s.close()
            return True
        except ConnectionRefusedError as e:
            raise Refused(str(e))
        except OSError as e:
            raise NoAnswer(str(e))

    def listeners(self):
        """{(address, port)} of listening TCP sockets from `netstat -ano -p tcp`, or None."""
        try:
            out = subprocess.run(["netstat", "-ano", "-p", "tcp"], capture_output=True, text=True,
                                 timeout=20)
        except Exception:                                                   # noqa: BLE001
            return None
        if out.returncode != 0 or not out.stdout:
            return None
        found = set()
        for line in out.stdout.splitlines():
            parts = line.split()
            if len(parts) >= 4 and parts[0].upper() == "TCP" and parts[3].upper() == "LISTENING":
                addr, _, port = parts[1].rpartition(":")
                if port.isdigit():
                    found.add((addr.strip("[]"), int(port)))
        return found or None

    def read_text(self, path, limit=2 * 1024 * 1024):
        try:
            with open(path, "rb") as f:
                return f.read(limit).decode("utf-8", "replace")
        except OSError:
            return None

    def size(self, path):
        try:
            return os.path.getsize(path)
        except OSError:
            return None

    def listdir(self, path):
        try:
            return sorted(os.listdir(path))
        except OSError:
            return None


# ----------------------------------------------------------------------------- helpers

def utc_iso(t):
    return t.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _get(env, url, method="GET", body=None, timeout=5.0):
    """(Reply, None) on an answer, else (None, (state, detail)) already classified."""
    try:
        return env.http(url, method=method, body=body, timeout=timeout), None
    except Refused:
        return None, (FAIL, "nothing is listening (connection refused)")
    except NoAnswer as e:
        return None, (UNKNOWN, "no answer: %s. A slow or busy service is not a down one." % e)
    except PermissionError as e:
        return None, (UNKNOWN, str(e))


def visible_text(page):
    """The words a person can read on a template: comments, Jinja tags, scripts and styles removed;
    the text of title, placeholder, aria-label and alt attributes kept (they are read on hover)."""
    t = without_comments_and_scripts(page)
    attrs = " ".join(re.findall(r'\b(?:title|placeholder|aria-label|alt)="([^"]*)"', t, flags=re.I))
    t = re.sub(r"\{%.*?%\}|\{\{.*?\}\}", " ", t, flags=re.S)
    t = re.sub(r"<[^>]+>", " ", t)
    return html.unescape(re.sub(r"\s+", " ", t + " " + attrs))


DEAD_WORDS = re.compile(r"\bstage\s+\d+\b|not wired yet|arrive in stage|coming soon", re.I)

# doc 04's eight regions and where the page proves each (template ids), with the page's own Start
# menu entry as the second witness. `menu` is the key in static/command/start.json.
DOC04_REGIONS = (
    ("centre_character", "Centre: Character", {"ids": ["char"], "menu": "character"}),
    ("left_action_feed", "Left: Action Feed", {"ids": ["afeed"], "menu": "feed"}),
    ("right_mission_board", "Right: Mission Board", {"ids": ["board"], "menu": "board"}),
    ("bottom_crews", "Bottom: Crews", {"ids": ["party", "regions"], "menu": "party"}),
    ("top_resources", "Top: Resources", {"id_prefixes": ["res-"], "menu": "credits"}),
    ("edge_radar", "Edge: Radar", {"ids": ["radar"], "menu": None}),
    ("overlay_contracts", "Overlay: Contracts", {"ids": [], "menu": "contracts"}),
    ("overlay_log", "Overlay: Log", {"ids": [], "menu": "log"}),
)


def without_comments_and_scripts(page):
    """The template with Jinja comments, HTML comments, scripts and styles removed, tags kept.
    An id that only a comment or a script string mentions is not on the page."""
    t = re.sub(r"\{#.*?#\}", " ", page, flags=re.S)
    t = re.sub(r"<!--.*?-->", " ", t, flags=re.S)
    return re.sub(r"<(script|style)\b.*?</\1\s*>", " ", t, flags=re.S | re.I)


def template_ids(page):
    return set(re.findall(r'\bid="([^"]+)"', without_comments_and_scripts(page)))


def region_status(ids, spec, menu_entries):
    """present: a template id exists; declared_not_built: no id and the page's own menu says not
    built; absent: neither."""
    want = set(spec.get("ids") or [])
    pref = tuple(spec.get("id_prefixes") or [])
    if (want & ids) or (pref and any(i.startswith(pref) for i in ids)):
        return "present"
    entry = (menu_entries or {}).get(spec.get("menu"))
    if entry and str(entry.get("state", "")).lower() == "not built":
        return "declared_not_built"
    return "absent"


# ----------------------------------------------------------------------------- the checks

CHECKS = {}


def check(cid, what, source="smoke"):
    def deco(fn):
        CHECKS[cid] = (what, source, fn)
        return fn
    return deco


@check("local.ollama.up", "the local model server answers on loopback")
def c_ollama_up(env, ctx):
    r, bad = _get(env, OLLAMA + "/api/tags")
    if bad:
        return bad
    d = r.json() if r.status == 200 else None
    if r.status == 200 and isinstance(d, dict) and isinstance(d.get("models"), list):
        return PASS, "%d models installed" % len(d["models"])
    return (FAIL if r.status >= 400 else UNKNOWN), "answered %s without a model list" % r.status


def _chat_models(env):
    """(models with a completion capability sorted by size, state/detail on trouble)."""
    r, bad = _get(env, OLLAMA + "/api/tags")
    if bad:
        return None, bad
    d = r.json() if r.status == 200 else None
    if not isinstance(d, dict) or not isinstance(d.get("models"), list):
        return None, (UNKNOWN, "answered %s without a model list" % r.status)
    have_caps = [m for m in d["models"] if isinstance(m, dict) and m.get("capabilities")]
    if not have_caps:
        return None, (UNKNOWN, "this server does not report model capabilities, so chat models cannot be told apart")
    chat = [m for m in have_caps if "completion" in m["capabilities"]]
    chat.sort(key=lambda m: m.get("size") or 0)
    return chat, None


@check("local.ollama.chat_model_installed", "at least one installed model can chat (completion)")
def c_chat_model(env, ctx):
    chat, bad = _chat_models(env)
    if bad:
        return bad
    if not chat:
        return FAIL, "no installed model reports the completion capability"
    return PASS, "%d chat-capable models, smallest %s" % (len(chat), chat[0].get("name"))


@check("local.ollama.chat_roundtrip", "the local model answers one tiny question (opt-in, unloads after)")
def c_chat_roundtrip(env, ctx):
    if not ctx.get("model_call"):
        return UNKNOWN, "not run: needs --model-call (it makes the local model do work once)"
    chat, bad = _chat_models(env)
    if bad:
        return bad
    if not chat:
        return FAIL, "no chat-capable model to ask"
    pick = next((m for m in chat if "instruct" in str(m.get("name"))), chat[0])
    body = {"model": pick["name"], "stream": False, "keep_alive": 0,
            "messages": [{"role": "user", "content": "Reply with the single word OK."}],
            "options": {"num_predict": 64, "temperature": 0}}
    r, bad = _get(env, OLLAMA + "/api/chat", method="POST", body=body, timeout=240.0)
    if bad:
        return bad
    d = r.json()
    msg = (d or {}).get("message") or {}
    text = (msg.get("content") or "") + (msg.get("thinking") or "")
    if r.status == 200 and isinstance(d, dict) and d.get("done") and text.strip():
        secs = (d.get("total_duration") or 0) / 1e9
        return PASS, "%s answered in %.1f s on this machine (loopback only)" % (pick["name"], secs)
    return FAIL, "answered %s with no usable reply from %s" % (r.status, pick["name"])


@check("local.hub.healthz", "the local hub answers its health route")
def c_hub_health(env, ctx):
    r, bad = _get(env, HUB + "/healthz")
    if bad:
        return bad
    d = r.json()
    if r.status == 200 and isinstance(d, dict) and d.get("ok") is True:
        w = (d.get("warden") or {}).get("state")
        return PASS, "ok; warden %s; health route alone, not the brain or the database" % (w or "not reported")
    return FAIL, "answered %s without ok=true" % r.status


@check("local.hub.command_opens_locally", "/command opens on this machine without sending the browser off it")
def c_command_local(env, ctx):
    r, bad = _get(env, HUB + "/command")
    if bad:
        return bad
    if r.status == 200:
        return PASS, "served locally; whether it is signed in and shows data is not read"
    if r.status in (301, 302, 303, 307, 308):
        loc = r.headers.get("location", "")
        host = urllib.parse.urlsplit(loc).hostname
        if host and host not in LOOPBACK_HOSTS:
            lr, lbad = _get(env, HUB + "/login")
            own = "its own /login is not read" if lbad else "its own /login answers %s" % lr.status
            err = (lr.json() or {}).get("error") if (lr is not None and isinstance(lr.json(), dict)) else None
            return FAIL, "redirects to %s (off this machine; not followed); %s%s" % (host, own, (": " + str(err)) if err else "")
        return UNKNOWN, "redirects to a local address (%s); the sign-in behind it is not read" % (loc[:80] or "none")
    if r.status in (401, 403):
        return UNKNOWN, "refused with %s; signed in it may open" % r.status
    return FAIL, "answered %s" % r.status


@check("local.hub.api_requires_login", "signed-out requests for the owner's own data are refused")
def c_api_login(env, ctx):
    routes = ("/api/command/feed", "/api/command/character", "/api/command/atlas")
    seen = []
    for rt in routes:
        r, bad = _get(env, HUB + rt)
        if bad:
            return bad
        if r.status == 200:
            return FAIL, "%s answered 200 with no sign-in" % rt
        if r.status not in (401, 403):
            return UNKNOWN, "%s answered %s, not a clear refusal" % (rt, r.status)
        seen.append(r.status)
    return PASS, "all %d routes refused a signed-out request (%s)" % (len(routes), "/".join(map(str, seen)))


@check("local.mcp.health", "the local MCP server answers its health route")
def c_mcp(env, ctx):
    r, bad = _get(env, MCP + "/health")
    if bad:
        return bad
    d = r.json()
    if r.status == 200 and isinstance(d, dict) and d.get("status") == "ok":
        return PASS, "ok (%s)" % d.get("service", "service not named")
    return FAIL, "answered %s without status ok" % r.status


@check("local.brain.postgres_tcp", "the local brain's database accepts a connection (connect and close, no query)")
def c_pg(env, ctx):
    try:
        env.tcp("127.0.0.1", PG_PORT, timeout=4.0)
    except Refused:
        return FAIL, "nothing is listening on %d" % PG_PORT
    except NoAnswer as e:
        return UNKNOWN, "no answer: %s" % e
    except PermissionError as e:
        return UNKNOWN, str(e)
    return PASS, "port %d accepts a connection; the brain's contents are not read" % PG_PORT


@check("local.window.route", "the NovahOS window's own route answers on loopback")
def c_window(env, ctx):
    r, bad = _get(env, WINDOW + "/gpu/lease/firstwalk-probe")
    if bad:
        return bad
    d = r.json()
    if r.status == 404 and isinstance(d, dict):
        return PASS, "the lease route answered (unknown lease id gives 404, as designed)"
    if r.status == 200:
        return UNKNOWN, "answered 200 for an id that should not exist"
    return FAIL, "answered %s, not the expected JSON 404" % r.status


@check("local.prime.dashboard", "Prime's dashboard answers on 8765")
def c_prime(env, ctx):
    r, bad = _get(env, PRIME_DASH + "/", timeout=12.0)
    if bad:
        return bad
    if r.status == 200:
        return PASS, "answered 200"
    return FAIL, "answered %s" % r.status


@check("local.chardesign.page", "Character Design's page answers on 8760")
def c_chardesign(env, ctx):
    r, bad = _get(env, CHARDESIGN + "/")
    if bad:
        if bad[0] == FAIL:
            return FAIL, "nothing is listening on 8760 now (it is started from its pane, so this may mean 'not started')"
        return bad
    if r.status == 200:
        return PASS, "answered 200"
    return FAIL, "answered %s" % r.status


@check("local.comfyui.up", "the image engine's queue can be read")
def c_comfy(env, ctx):
    r, bad = _get(env, COMFY + "/system_stats")
    if bad:
        return bad
    d = r.json()
    if r.status == 200 and isinstance(d, dict) and "system" in d:
        return PASS, "system stats read"
    return FAIL, "answered %s without system stats" % r.status


def _in_tailnet(addr):
    p = addr.split(".")
    try:
        a, b = int(p[0]), int(p[1])
    except (ValueError, IndexError):
        return False
    return a == 100 and 64 <= b <= 127


@check("local.phone.listener", "the phone chat host is listening on this machine's tailnet address")
def c_phone(env, ctx):
    lst = env.listeners()
    if lst is None:
        return UNKNOWN, "the listener table (netstat) could not be read"
    mine = sorted(a for a, p in lst if p == PHONE_PORT)
    if not mine:
        return FAIL, "nothing listens on port %d" % PHONE_PORT
    tail = [a for a in mine if _in_tailnet(a)]
    if tail:
        return PASS, "listening on %s:%d; a paired phone reaching it is not read" % (tail[0], PHONE_PORT)
    return UNKNOWN, "listens on %s, not a tailnet address; the design says tailnet only" % ", ".join(mine)


@check("watch.vault_sync_status", "the off-machine copy's last run (WATCH's reader output)", source="watch")
def c_vault(env, ctx):
    d = ctx.get("vault_sync")
    if not isinstance(d, dict):
        return UNKNOWN, "not supplied: run watch/vault_sync_status.py and pass its JSON with --vault-sync-json"
    st = d.get("state")
    detail = "%s (last end %s)" % (d.get("reason") or st, d.get("last_end"))
    if st == "ok":
        return PASS, detail
    if st == "failed":
        return FAIL, detail
    return UNKNOWN, detail


# --- source and file checks (read local files only) ---

def _hub_file(env, ctx, rel):
    root = ctx.get("hub_root")
    if not root:
        return None
    return env.read_text(os.path.join(root, *rel.split("/")))


def _start_menu(env, ctx):
    """{key: entry} from the page's own Start menu data, or {} when it cannot be read."""
    raw = _hub_file(env, ctx, "static/command/start.json")
    if not raw:
        return {}
    try:
        return {e.get("key"): e for e in json.loads(raw).get("entries", []) if isinstance(e, dict)}
    except (ValueError, AttributeError):
        return {}


@check("source.command.region.action_feed", "doc 04's Action Feed region (left) is on the /command page (template source)")
def c_region_feed(env, ctx):
    page = _hub_file(env, ctx, "templates/command_screen.html")
    if page is None:
        return UNKNOWN, "the page source was not readable (pass --hub-root)"
    key, name, spec = next(r for r in DOC04_REGIONS if r[0] == "left_action_feed")
    st = region_status(template_ids(page), spec, _start_menu(env, ctx))
    if st == "present":
        return PASS, "%s has its template id; that it shows cards is not read" % name
    return FAIL, "%s is %s in the template" % (name, st.replace("_", " "))


@check("source.command.regions", "doc 04's eight regions are on the /command page (template source)")
def c_regions(env, ctx):
    page = _hub_file(env, ctx, "templates/command_screen.html")
    if page is None:
        return UNKNOWN, "the page source was not readable (pass --hub-root)"
    menu = _start_menu(env, ctx)
    ids = template_ids(page)
    got = {key: region_status(ids, spec, menu) for key, _, spec in DOC04_REGIONS}
    names = {key: name for key, name, _ in DOC04_REGIONS}
    ok = [names[k] for k, v in got.items() if v == "present"]
    nb = [names[k] for k, v in got.items() if v == "declared_not_built"]
    ab = [names[k] for k, v in got.items() if v == "absent"]
    counts = {}
    for e in menu.values():
        counts[e.get("state")] = counts.get(e.get("state"), 0) + 1
    tail = "; the page's own Start menu: %s" % ", ".join("%d %s" % (n, s) for s, n in sorted(counts.items(), key=lambda x: str(x[0]))) if counts else ""
    detail = "%d of 8 regions in the template (%s)%s%s%s" % (
        len(ok), ", ".join(ok) or "none",
        ("; says 'not built' for: " + ", ".join(nb)) if nb else "",
        ("; absent: " + ", ".join(ab)) if ab else "", tail)
    return (PASS if len(ok) == 8 else FAIL), detail


@check("source.command.dead_strings", "no visible 'stage N' or 'not wired yet' words on the page (template and menu text)")
def c_dead(env, ctx):
    page = _hub_file(env, ctx, "templates/command_screen.html")
    if page is None:
        return UNKNOWN, "the page source was not readable (pass --hub-root)"
    words = DEAD_WORDS.findall(visible_text(page))
    menu_raw = _hub_file(env, ctx, "static/command/start.json")
    if menu_raw is None:
        return UNKNOWN, "the Start menu data was not readable, so only part of the visible words can be read"
    words += DEAD_WORDS.findall(menu_raw)
    if words:
        return FAIL, "%d dead words left, e.g. %r" % (len(words), words[0])
    return PASS, "0 dead words in the template's visible text and the menu data; words drawn by scripts are not read"


@check("source.command.world_controls", "the 3D crystal and world have turn, rotate and reset controls and a script")
def c_world(env, ctx):
    page = _hub_file(env, ctx, "templates/command_screen.html")
    if page is None:
        return UNKNOWN, "the page source was not readable (pass --hub-root)"
    ids = template_ids(page)
    need = {"x3d-3d", "x3d-orbit", "x3d-rotate", "x3d-reset"}
    missing = sorted(need - ids)
    js = _hub_file(env, ctx, "static/command/crystal3d.js")
    if missing:
        return FAIL, "controls missing from the template: %s" % ", ".join(missing)
    if js is None:
        return FAIL, "crystal3d.js is not readable although the controls are there"
    return PASS, "controls and crystal3d.js are in the source; that it runs smoothly is not read"


@check("source.command.phone_layout", "the page links its phone stylesheet and script")
def c_phone_layout(env, ctx):
    page = _hub_file(env, ctx, "templates/command_screen.html")
    if page is None:
        return UNKNOWN, "the page source was not readable (pass --hub-root)"
    css = _hub_file(env, ctx, "static/command/phone.css")
    screen_js = _hub_file(env, ctx, "static/command/screen.js") or ""
    linked = "command/phone.css" in page
    loaded = 'phone.js' in screen_js
    if linked and loaded and css:
        return PASS, "phone.css is linked and screen.js loads phone.js; how it looks at 375 px is not read"
    return FAIL, "phone stylesheet linked=%s, script loaded=%s, css present=%s" % (linked, loaded, bool(css))


def _artifact_dir(env, root, artifact_id):
    names = env.listdir(root)
    if names is None:
        return None, None
    for n in names:
        if n.endswith("__" + artifact_id):
            return n, os.path.join(root, n)
    return "", None


def _artifact_page_size(env, d):
    best = 0
    for fn in ("current.html", "index.html"):
        s = env.size(os.path.join(d, fn))
        if s:
            best = max(best, s)
    return best


@check("files.artifacts.original_atlas", "a saved copy of the original Atlas exists in the artifacts folder")
def c_atlas(env, ctx):
    root, ids = ctx.get("artifacts_root"), ctx.get("atlas_ids") or []
    if not root or not ids:
        return UNKNOWN, "not supplied: pass --artifacts-root"
    out = []
    for aid in ids:
        name, d = _artifact_dir(env, root, aid)
        if name is None:
            return UNKNOWN, "the artifacts folder could not be read"
        size = _artifact_page_size(env, d) if d else 0
        out.append((aid, size))
    good = [a for a, s in out if s >= 50000]
    if good:
        return PASS, "%d of %d candidate Atlas copies hold a page of 50 KB or more; which one is 'the original' is the owner's to confirm" % (len(good), len(out))
    return FAIL, "no candidate Atlas copy holds a real page: %s" % ", ".join("%s=%sB" % o for o in out)


@check("files.artifacts.mockups", "the approved mockups are saved in the artifacts folder")
def c_mockups(env, ctx):
    root, mocks = ctx.get("artifacts_root"), ctx.get("mockups") or []
    if not root or not mocks:
        return UNKNOWN, "not supplied: pass --artifacts-root"
    bad = []
    for m in mocks:
        name, d = _artifact_dir(env, root, m["artifact_id"])
        if name is None:
            return UNKNOWN, "the artifacts folder could not be read"
        if not d or _artifact_page_size(env, d) < 10000:
            bad.append(m["id"])
    if bad:
        return FAIL, "no saved page for: %s" % ", ".join(bad)
    return PASS, "all %d mockups (%s) have a saved page of 10 KB or more" % (len(mocks), ", ".join(m["id"] for m in mocks))


@check("files.documents.library_present", "the Document Library folder is there with an index and saved artifacts")
def c_library(env, ctx):
    root = ctx.get("library_root")
    if not root:
        return UNKNOWN, "not supplied: pass --library-root"
    names = env.listdir(root)
    if names is None:
        return UNKNOWN, "the library folder could not be read"
    arts = env.listdir(os.path.join(root, "artifacts"))
    has_index = any(n.upper().startswith(("INDEX", "MANIFEST")) for n in names)
    if has_index and arts:
        return PASS, "an index and %d saved artifact folders; a documents room in the window is not read" % len(arts)
    return FAIL, "index present=%s, artifact folders=%s" % (has_index, len(arts) if arts else 0)


@check("files.documents.doc04", "doc 04 (command center data contract) is on disk")
def c_doc04(env, ctx):
    p = ctx.get("doc04")
    if not p:
        return UNKNOWN, "not supplied: pass --doc04"
    s = env.size(p)
    if s is None:
        return FAIL, "the file is not at the given path"
    return (PASS, "%d bytes" % s) if s > 1000 else (FAIL, "only %d bytes" % s)


# --- acceptance rows from the NODE desk's own tool (read-only; run separately, passed in) ---

NODE_PREFIX = "node."


def node_check(cid, ctx):
    rows = ctx.get("acceptance")
    rid = cid[len(NODE_PREFIX):]
    if not isinstance(rows, dict):
        return UNKNOWN, "not supplied: run `python -m lfdesk.install.acceptance --json` in home-node/app and pass it with --acceptance-json"
    row = rows.get(rid)
    if not isinstance(row, dict):
        return UNKNOWN, "row %s is not in the supplied acceptance results" % rid
    st = row.get("state")
    if st not in CHECK_STATES:
        return UNKNOWN, "row %s has state %r" % (rid, st)
    return st, str(row.get("detail", ""))[:240]


def load_acceptance(text):
    """{row id: row} from the acceptance tool's --json output, or None."""
    try:
        data = json.loads(text)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, list):
        return None
    out = {}
    for r in data:
        if isinstance(r, dict) and r.get("id"):
            out[r["id"]] = r
    return out or None


def run_one(env, ctx, cid):
    now = utc_iso(env.now())
    if cid.startswith(NODE_PREFIX):
        what, source = "NODE acceptance row %s" % cid[len(NODE_PREFIX):], "acceptance"
        try:
            state, detail = node_check(cid, ctx)
        except Exception as e:                                              # noqa: BLE001
            state, detail = UNKNOWN, "check raised %s: %s" % (type(e).__name__, e)
    elif cid in CHECKS:
        what, source, fn = CHECKS[cid]
        try:
            state, detail = fn(env, ctx)
        except Exception as e:                                              # noqa: BLE001
            state, detail = UNKNOWN, "check raised %s: %s" % (type(e).__name__, e)
    else:
        what, source, state, detail = "no such check", "none", UNKNOWN, "no check is defined for %s" % cid
    if state not in CHECK_STATES:
        state, detail = UNKNOWN, "check returned %r" % (state,)
    return {"id": cid, "what": what, "state": state, "detail": detail, "source": source, "observed_utc": now}


# ----------------------------------------------------------------------------- positive controls

class _Fake:
    """An environment for the controls. mode 'ok200' answers 200 JSON to everything; 'refuse401'
    answers 401 to everything; 'redirect' sends every path to a production sign-in page; 'absent'
    answers nothing; 'raise' raises on every call."""

    def __init__(self, mode):
        self.mode = mode

    def now(self):
        return dt.datetime(2026, 1, 1, tzinfo=dt.timezone.utc)

    def http(self, url, method="GET", body=None, timeout=5.0):
        if self.mode == "raise":
            raise RuntimeError("boom")
        if self.mode == "absent":
            raise Refused("refused")
        if self.mode == "refuse401":
            return Reply(401, {"content-type": "application/json"}, b'{"error": "sign in"}')
        if self.mode == "redirect":
            if url.endswith("/login"):
                return Reply(503, {"content-type": "application/json"}, b'{"error": "login not enabled"}')
            return Reply(302, {"location": "https://example.invalid/login"}, b"")
        return Reply(200, {"content-type": "application/json"}, b'{"ok": true, "status": "ok", "models": [], "system": {}}')

    def tcp(self, host, port, timeout=4.0):
        if self.mode == "raise":
            raise RuntimeError("boom")
        if self.mode == "absent":
            raise Refused("refused")
        return True

    def listeners(self):
        if self.mode == "raise":
            raise RuntimeError("boom")
        return None

    def read_text(self, path, limit=0):
        if self.mode == "raise":
            raise RuntimeError("boom")
        return None

    def size(self, path):
        if self.mode == "raise":
            raise RuntimeError("boom")
        return None

    def listdir(self, path):
        if self.mode == "raise":
            raise RuntimeError("boom")
        return None


def run_controls(check_ids):
    """(ok, list of problems). The controls the estate asks of every reader."""
    problems = []
    # 1. a server that answers 200 to everything must NOT read as "signed-out requests are refused"
    r = run_one(_Fake("ok200"), {}, "local.hub.api_requires_login")
    if r["state"] != FAIL:
        problems.append("api_requires_login read %s against a server that serves everything" % r["state"])
    #    and a server that refuses everything must read as refused: the check can see both ways
    r = run_one(_Fake("refuse401"), {}, "local.hub.api_requires_login")
    if r["state"] != PASS:
        problems.append("api_requires_login read %s against a server that refuses every request" % r["state"])
    # 1b. a /command that sends the browser off this machine must NOT read as opening locally,
    #     and a server that answers 200 to an id that cannot exist must NOT read as the lease route
    r = run_one(_Fake("redirect"), {}, "local.hub.command_opens_locally")
    if r["state"] != FAIL:
        problems.append("command_opens_locally read %s when /command redirects off this machine" % r["state"])
    r = run_one(_Fake("ok200"), {}, "local.window.route")
    if r["state"] == PASS:
        problems.append("window.route read pass against a server that answers 200 to an unknown lease id")
    # 2. a server that answers nothing must NOT read as up
    for cid in ("local.hub.healthz", "local.mcp.health", "local.ollama.up", "local.comfyui.up"):
        r = run_one(_Fake("absent"), {}, cid)
        if r["state"] == PASS:
            problems.append("%s read pass against an environment where nothing answers" % cid)
    # 3. with nothing readable, or everything raising, no check anywhere may pass
    for mode in ("absent", "raise"):
        for cid in sorted(set(check_ids)):
            r = run_one(_Fake(mode), {}, cid)
            if r["state"] == PASS:
                problems.append("%s read pass in the '%s' environment" % (cid, mode))
    return (not problems), problems


# ----------------------------------------------------------------------------- walk, marks, results

def load_walk(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def walk_cells(walk):
    """Lines then rooms, in walk order, each with its steps and check ids."""
    cells = []
    for kind, key in (("line", "lines"), ("room", "rooms")):
        for c in walk.get(key, []):
            cells.append((kind, c))
    return cells


def all_check_ids(walk):
    ids = []
    for _, c in walk_cells(walk):
        for cid in c.get("checks", []):
            if cid not in ids:
                ids.append(cid)
    return ids


def rollup(step_states):
    """A cell's walk state from its steps' states. pass only if every step passed; any fail is a
    fail; closed_by_design only if every step is pass or closed_by_design and one is closed; else
    not_tested (a cell with no marks, or with a hole, is never a pass)."""
    s = [x if x in WALK_STATES else "not_tested" for x in step_states]
    if not s:
        return "not_tested"
    if "fail" in s:
        return "fail"
    if all(x == "pass" for x in s):
        return "pass"
    if all(x in ("pass", "closed_by_design") for x in s) and "closed_by_design" in s:
        return "closed_by_design"
    return "not_tested"


def load_marks(text):
    """{step id: state} from an exported marks file; anything unreadable gives {}."""
    try:
        d = json.loads(text)
    except (ValueError, TypeError):
        return {}
    if not isinstance(d, dict) or d.get("schema") != SCHEMA_MARKS or not isinstance(d.get("marks"), dict):
        return {}
    out = {}
    for sid, m in d["marks"].items():
        st = m.get("state") if isinstance(m, dict) else m
        if st in WALK_STATES:
            out[sid] = st
    return out


def smoke_rollup(states):
    if not states:
        return NOT_RUN
    if FAIL in states:
        return FAIL
    if UNKNOWN in states:
        return UNKNOWN
    return PASS


def build_results(walk, check_results, marks, ctx_inputs, controls, evidence_file, marks_info=None):
    now = ctx_inputs["generated_utc"]
    by_id = {r["id"]: r for r in check_results}
    cells = []
    for kind, c in walk_cells(walk):
        sids = [s["id"] for s in c.get("steps", [])]
        wstate = rollup([marks.get(s, "not_tested") for s in sids]) if marks else "not_tested"
        marked = sum(1 for s in sids if marks.get(s, "not_tested") != "not_tested") if marks else 0
        cstates = [by_id[cid]["state"] for cid in c.get("checks", []) if cid in by_id]
        cells.append({
            "id": c["id"], "kind": kind, "title": c["title"],
            "scoreboard_cell": (walk.get("scoreboard_cells") or {}).get(c["id"]),
            "walk_state": wstate,
            "walk_steps": {"total": len(sids), "marked": marked},
            "walk_evidence": (marks_info or {}).get("path") if marks else None,
            "walk_evidence_date": (marks_info or {}).get("date") if marks else None,
            "smoke_result": smoke_rollup(cstates) if controls["ok"] else UNKNOWN,
            "smoke_checks": list(c.get("checks", [])),
            "smoke_note": ("A preflight about what answers on this machine today. It does not move walk_state, and a "
                           "pass here covers only what each check's detail says, never the whole cell."),
            "evidence_file": evidence_file, "evidence_date": now[:10],
            "owner_step": "Walk %s (%d steps) and mark each in the checklist page." % (c["id"], len(sids)),
            "queue": list(c.get("queue", [])),
        })
    n_pass = sum(1 for c in cells if c["walk_state"] == "pass")
    n_closed = sum(1 for c in cells if c["walk_state"] == "closed_by_design")
    chk = {s: sum(1 for r in check_results if r["state"] == s) for s in CHECK_STATES}
    sm = {s: sum(1 for c in cells if c["smoke_result"] == s) for s in (PASS, FAIL, UNKNOWN, NOT_RUN)}
    named = [dict(n) for n in walk.get("named", [])]
    built_counts = {}
    for n in named:
        built_counts[n["built"]] = built_counts.get(n["built"], 0) + 1
    return {
        "schema": SCHEMA_RESULTS,
        "generated_utc": now,
        "run_by": "SURFACE desk, a background agent for ROUTER #135 (fold-a-firstwalk, chats-2)",
        "walk_written": walk.get("written"),
        "goal": walk.get("goal"),
        "inputs": ctx_inputs["described"],
        "controls_ok": controls["ok"],
        "controls_problems": controls["problems"],
        "summary": {
            "cells": len(cells),
            "walk": {s: sum(1 for c in cells if c["walk_state"] == s) for s in WALK_STATES},
            "smoke_by_cell": sm, "checks": chk, "named_things_by_status": built_counts,
            "line": "cells passed / cells not closed by design = %d / %d" % (n_pass, len(cells) - n_closed),
        },
        "cells": cells,
        "checks": check_results,
        "named": named,
        "mockups": walk.get("mockups", []),
    }


def cell_files(results, walk, marks):
    """One small file per cell for a reader that wants a single room (the walk scoreboard), named by the
    scoreboard's cell id: {file name: object}. The same facts as results.json for that cell, plus each
    step's words and the full result of each of its checks."""
    by_id = {r["id"]: r for r in results["checks"]}
    src = {c["id"]: c for _, c in walk_cells(walk)}
    out = {}
    for cell in results["cells"]:
        name = (cell.get("scoreboard_cell") or cell["id"]) + ".json"
        steps = [{"id": s["id"], "do": s["do"], "expect": s["expect"], "proof_wanted": s["proof"],
                  "walk_state": (marks or {}).get(s["id"], "not_tested")} for s in src[cell["id"]]["steps"]]
        out[name] = {
            "schema": SCHEMA_CELL,
            "generated_utc": results["generated_utc"],
            "controls_ok": results["controls_ok"],
            "cell": cell,
            "steps": steps,
            "checks": [by_id[cid] for cid in cell["smoke_checks"] if cid in by_id],
            "reading_it": ("walk_state is the owner's alone and stays not_tested until his exported marks are passed in. "
                           "smoke_result is a preflight, never a walk result."),
        }
    return out


def exit_code(results):
    states = [r["state"] for r in results["checks"]]
    if FAIL in states:
        return 1
    if UNKNOWN in states or not results["controls_ok"]:
        return 2
    return 0


def _sha256(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _read_json_arg(env, path):
    if not path:
        return None, None
    txt = env.read_text(path)
    if txt is None:
        return None, "unreadable"
    return txt, _sha256(txt)


def cmd_run(a, env=None):
    env = env or RealEnv()
    walk = load_walk(a.walk)
    ids = all_check_ids(walk)
    controls_ok, problems = run_controls(ids)
    ctx = {"model_call": bool(a.model_call), "hub_root": a.hub_root, "artifacts_root": a.artifacts_root,
           "library_root": a.library_root, "doc04": a.doc04,
           "atlas_ids": [m["artifact_id"] for m in walk.get("mockups", []) if m["id"] == "M1"] + ["6LEvF7K9u9qnSxh68VWsfA"],
           "mockups": walk.get("mockups", [])}
    described = {"model_call": bool(a.model_call), "hub_root": a.hub_root, "hub_rev": a.hub_rev,
                 "artifacts_root": a.artifacts_root, "library_root": a.library_root, "doc04": a.doc04}
    txt, h = _read_json_arg(env, a.acceptance_json)
    ctx["acceptance"] = load_acceptance(txt) if txt else None
    described["acceptance_json"] = {"path": a.acceptance_json, "sha256_16": h, "rows": len(ctx["acceptance"] or {})} if a.acceptance_json else None
    txt, h = _read_json_arg(env, a.vault_sync_json)
    try:
        ctx["vault_sync"] = json.loads(txt) if txt else None
    except ValueError:
        ctx["vault_sync"] = None
    described["vault_sync_json"] = {"path": a.vault_sync_json, "sha256_16": h} if a.vault_sync_json else None
    marks, minfo = {}, None
    if a.marks:
        mt = env.read_text(a.marks)
        marks = load_marks(mt) if mt else {}
        if not marks:
            # A file the owner handed over that reads as nothing is an error to say out loud: a quiet
            # "not tested" everywhere would look like he had marked nothing.
            print("firstwalk smoke: %s is unreadable, is not a %s file, or holds no marked step. Nothing was written."
                  % (a.marks, SCHEMA_MARKS), file=sys.stderr)
            return 3
        minfo = {"path": a.marks, "date": utc_iso(env.now())[:10]}
        described["marks"] = {"path": a.marks, "steps_marked": len(marks)}
    controls = {"ok": controls_ok, "problems": problems}
    results_list = []
    for cid in ids:
        r = run_one(env, ctx, cid)
        if not controls_ok:
            r["state"], r["detail"] = UNKNOWN, "controls failed, so no result is trusted: " + r["detail"]
        results_list.append(r)
    inputs = {"generated_utc": utc_iso(env.now()), "described": described}
    results = build_results(walk, results_list, marks, inputs, controls, a.out or "(stdout)", minfo)
    text = json.dumps(results, indent=1, ensure_ascii=False)
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
        with open(a.out, "w", encoding="utf-8", newline="\n") as f:
            f.write(text + "\n")
    if a.cells_dir:
        os.makedirs(a.cells_dir, exist_ok=True)
        for name, obj in cell_files(results, walk, marks).items():
            with open(os.path.join(a.cells_dir, name), "w", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(obj, indent=1, ensure_ascii=False) + "\n")
    s = results["summary"]
    print("firstwalk smoke: %d cells; checks pass %d, fail %d, unknown %d; controls %s" % (
        s["cells"], s["checks"][PASS], s["checks"][FAIL], s["checks"][UNKNOWN], "ok" if controls_ok else "FAILED"))
    print(s["line"])
    for r in results["checks"]:
        print("  %-8s %-38s %s" % (r["state"].upper(), r["id"], r["detail"][:150]))
    return exit_code(results)


def main(argv=None):
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser(description="SURFACE firstwalk: read-only, loopback only.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--walk", default=os.path.join(here, "walk.json"))
    r.add_argument("--out")
    r.add_argument("--cells-dir", help="also write one <scoreboard cell id>.json per cell into this folder")
    r.add_argument("--hub-root", help="a checkout or export holding templates/ and static/command/")
    r.add_argument("--hub-rev", help="the commit that checkout is, as the caller states it (not verified here)")
    r.add_argument("--artifacts-root")
    r.add_argument("--library-root")
    r.add_argument("--doc04")
    r.add_argument("--acceptance-json")
    r.add_argument("--vault-sync-json")
    r.add_argument("--marks", help="the exported marks file from checklist.html (the owner's walk)")
    r.add_argument("--model-call", action="store_true",
                   help="ask the local model one tiny question on loopback (it unloads afterwards)")
    sub.add_parser("controls")
    a = ap.parse_args(argv)
    if a.cmd == "controls":
        ok, problems = run_controls(all_check_ids(load_walk(os.path.join(here, "walk.json"))))
        print("controls ok" if ok else "controls FAILED: " + "; ".join(problems))
        return 0 if ok else 1
    return cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
