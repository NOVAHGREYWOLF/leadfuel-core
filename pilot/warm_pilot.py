"""WEB-H1: the Next Clients warm-network pilot harness. Local only, one folder per customer.

WHAT IT DOES. A customer hands over their own LinkedIn data export. This reads the two files
that matter (`Connections.csv`, `messages.csv`) into a per-customer folder on this machine,
measures every tie from the customer's own messages, ranks the people with the HUB'S OWN pure
routing rules (`relationship_route.routes`, loaded read-only from the hub checkout, never
copied here), and writes the "25": a sheet with why-them, the measured tie, why-now, the best
channel, and a draft slot, plus voice samples taken from the customer's own sent messages.

THE THREE PROMISES, AND WHERE EACH IS ENFORCED.
  * The customer sends every note themselves. Nothing here can send: there is no send code.
  * We never touch their accounts. Input is a file they downloaded; nothing logs in anywhere.
  * The export is deleted 30 days after delivery. `sweep` deletes any folder past its
    `delete_after` and proves the folder is gone; it says so loudly when it cannot.

NOTHING LEAVES THE MACHINE (Law 9). The only network call in this file is the optional local
model step, and `_loopback_only` refuses any host that is not 127.0.0.1, ::1 or localhost,
with proxies disabled so a system proxy cannot carry it off the box. There is no cloud path.
Asking for one raises `CloudRefused`: a cloud path must be a decision (card 4), not a fallback,
and when the local model fails this raises rather than falling through to anything.

THE DATA ROOT MUST NOT BE INSIDE A GIT WORKING TREE. Customer data is third-party personal data
and this repository is public, so `pilot_root` refuses any root with a `.git` above it.

THE WEIGHTS ARE UNCALIBRATED, and the hub says so itself. The calibration log is how they
eventually stop being: every ranked person gets a baseline row, and the 14-day check-in adds
sent / replied / conversation against the score they were ranked with. At deletion the log is
reduced to de-identified rows (band, scores, outcome; no names, no URLs) so the calibration
survives the 30-day promise without keeping anyone's identity.

Stdlib only, like the rest of this repository.
"""
from __future__ import annotations

import argparse
import csv
import datetime as _dt
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import statistics
import sys
import urllib.parse
import urllib.request
import zipfile

RETENTION_DAYS = 30
DEFAULT_TOP = 25
DEFAULT_HUB_ROUTE = os.environ.get(
    "LEADFUEL_HUB_ROUTE", r"F:\Leadfuel\repos\novahub\relationship_route.py")
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "::1", "localhost"})

#: Consent scopes. `local_processing` covers import, ranking and the stub drafts, all on this
#: machine. `local_model` additionally covers the local model reading the customer's own sent
#: messages to draft in their voice. `cloud_model` is recordable (the terms may grant it) but
#: no code here acts on it; see `CloudRefused`.
SCOPES = ("local_processing", "local_model", "cloud_model")

_EXPORT_FILES = ("Connections.csv", "messages.csv")
_CUSTOMER_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,47}$")


class PilotError(RuntimeError):
    """A refusal with its reason. The CLI prints it and exits 2."""


class EgressRefused(PilotError):
    """A network call to anything that is not this machine."""


class CloudRefused(PilotError):
    """Somebody asked for a cloud model. Not built, on purpose."""


class ConsentMissing(PilotError):
    pass


def _now() -> _dt.datetime:
    return _dt.datetime.now(_dt.timezone.utc)


def _iso(d: _dt.datetime) -> str:
    return d.astimezone(_dt.timezone.utc).isoformat(timespec="seconds")


def _parse_iso(s):
    if not s:
        return None
    d = _dt.datetime.fromisoformat(str(s).replace("Z", "+00:00"))
    return d if d.tzinfo else d.replace(tzinfo=_dt.timezone.utc)


# --------------------------------------------------------------------------- #
# the data root and the customer folder                                       #
# --------------------------------------------------------------------------- #

def _inside_git(path: str) -> str | None:
    p = os.path.abspath(path)
    while True:
        if os.path.exists(os.path.join(p, ".git")):
            return p
        parent = os.path.dirname(p)
        if parent == p:
            return None
        p = parent


def pilot_root(root: str | None = None) -> str:
    """The data root, created if missing. Refuses a root inside any git working tree."""
    r = root or os.environ.get("LEADFUEL_PILOT_ROOT") or os.path.join(
        os.environ.get("LOCALAPPDATA") or os.path.expanduser("~"), "leadfuel-pilot")
    r = os.path.abspath(r)
    repo = _inside_git(r)
    if repo:
        raise PilotError(f"data root {r} is inside the git working tree {repo}; customer data "
                         "must never be where a commit can reach it. Set LEADFUEL_PILOT_ROOT.")
    os.makedirs(r, exist_ok=True)
    return r


def _cdir(root: str, customer: str) -> str:
    if not _CUSTOMER_RE.match(customer or ""):
        raise PilotError("customer id must be a short slug (a-z, 0-9, -), never a real name")
    return os.path.join(root, customer)


def _read_json(path, default=None):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return default


def _write_json(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(obj, fh, indent=2, ensure_ascii=False, default=str)
    os.replace(tmp, path)


def _append(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(obj, ensure_ascii=False, default=str) + "\n")


def _read_jsonl(path) -> list[dict]:
    try:
        with open(path, encoding="utf-8") as fh:
            return [json.loads(line) for line in fh if line.strip()]
    except FileNotFoundError:
        return []


def _ledger(root, customer, event, now):
    """The root ledger holds ids and events only: never a name, a URL or a message."""
    _append(os.path.join(root, "ledger.jsonl"), {"at": _iso(now), "customer": customer,
                                                 "event": event})


def _meta(root, customer) -> dict:
    m = _read_json(os.path.join(_cdir(root, customer), "meta.json"))
    if m is None:
        raise PilotError(f"no customer folder for {customer!r}; run `init` first")
    return m


def _save_meta(root, customer, meta):
    _write_json(os.path.join(_cdir(root, customer), "meta.json"), meta)


OFFER_TEMPLATE = {
    "_help": ("What the customer sells, from the intake call. Words in roles/keywords are "
              "matched only against the company and position that came with each connection. "
              "Leave all empty to rank by tie strength alone."),
    "roles": [],
    "keywords": [],
    "company": "",
}


def init(customer: str, *, root=None, now=None) -> str:
    now = now or _now()
    root = pilot_root(root)
    d = _cdir(root, customer)
    if os.path.exists(os.path.join(d, "meta.json")):
        raise PilotError(f"{customer!r} already exists")
    os.makedirs(os.path.join(d, "raw"), exist_ok=True)
    os.makedirs(os.path.join(d, "out"), exist_ok=True)
    _write_json(os.path.join(d, "offer.json"), OFFER_TEMPLATE)
    _save_meta(root, customer, {"customer": customer, "created_at": _iso(now),
                                "imported_at": None, "delivered_at": None,
                                "delete_after": None, "export_sha256": None})
    _ledger(root, customer, "init", now)
    return d


# --------------------------------------------------------------------------- #
# consent                                                                      #
# --------------------------------------------------------------------------- #

def record_consent(customer, scope, *, granted_by, method, note="", revoke=False, root=None,
                   now=None) -> dict:
    """Append one consent event. Revoking `local_processing` makes the folder due for deletion
    now: without that consent there is no basis to hold the data at all."""
    now = now or _now()
    root = pilot_root(root)
    if scope not in SCOPES:
        raise PilotError(f"scope must be one of {SCOPES}")
    if not granted_by or not method:
        raise PilotError("consent needs who gave it (--by, a role such as 'customer') and how "
                         "(--method, e.g. 'signed pilot terms v1')")
    meta = _meta(root, customer)
    entry = {"at": _iso(now), "scope": scope, "granted": not revoke, "by": granted_by,
             "method": method, "note": note}
    _append(os.path.join(_cdir(root, customer), "consent.jsonl"), entry)
    if revoke and scope == "local_processing":
        meta["delete_after"] = _iso(now)
        _save_meta(root, customer, meta)
    _ledger(root, customer, f"consent:{scope}:{'revoked' if revoke else 'granted'}", now)
    return entry


def has_consent(root, customer, scope) -> bool:
    """The latest event for the scope wins. No event is no consent."""
    state = False
    for e in _read_jsonl(os.path.join(_cdir(root, customer), "consent.jsonl")):
        if e.get("scope") == scope:
            state = bool(e.get("granted"))
    return state


def _require(root, customer, scope):
    if not has_consent(root, customer, scope):
        raise ConsentMissing(f"{customer!r} has no recorded {scope} consent; record it with "
                             f"`consent {customer} {scope} --by ... --method ...` first")


# --------------------------------------------------------------------------- #
# import                                                                       #
# --------------------------------------------------------------------------- #

def import_export(customer, export_path, *, root=None, now=None) -> dict:
    """Copy Connections.csv and messages.csv out of the export (a folder or the LinkedIn zip)
    into the customer's raw folder. Only those two files, matched by base name, so nothing
    else in the export is kept and a crafted zip path cannot write outside the folder."""
    now = now or _now()
    root = pilot_root(root)
    _require(root, customer, "local_processing")
    meta = _meta(root, customer)
    raw = os.path.join(_cdir(root, customer), "raw")
    os.makedirs(raw, exist_ok=True)
    found = {}
    h = hashlib.sha256()
    if os.path.isdir(export_path):
        for dirpath, _dirs, files in os.walk(export_path):
            for f in files:
                if f in _EXPORT_FILES and f not in found:
                    with open(os.path.join(dirpath, f), "rb") as fh:
                        found[f] = fh.read()
    elif zipfile.is_zipfile(export_path):
        with zipfile.ZipFile(export_path) as z:
            for info in z.infolist():
                base = os.path.basename(info.filename.replace("\\", "/"))
                if base in _EXPORT_FILES and base not in found:
                    found[base] = z.read(info)
    else:
        raise PilotError(f"{export_path} is neither a folder nor a zip")
    if "Connections.csv" not in found and "messages.csv" not in found:
        raise PilotError("the export holds neither Connections.csv nor messages.csv")
    for name in _EXPORT_FILES:
        if name in found:
            h.update(name.encode() + b"\0" + found[name])
            with open(os.path.join(raw, name), "wb") as fh:
                fh.write(found[name])
    meta["imported_at"] = _iso(now)
    meta["export_sha256"] = h.hexdigest()
    meta["export_files"] = sorted(found)
    # Provisional deletion date, so data that is never delivered still goes. Delivery resets
    # it to delivery + 30 days, which is the promise on the page.
    if not meta.get("delivered_at"):
        meta["delete_after"] = _iso(now + _dt.timedelta(days=RETENTION_DAYS))
    _save_meta(root, customer, meta)
    _ledger(root, customer, "import", now)
    return meta


# --------------------------------------------------------------------------- #
# reading the export                                                           #
# --------------------------------------------------------------------------- #

def norm_url(u) -> str:
    u = (u or "").strip().lower()
    if not u:
        return ""
    u = re.sub(r"^https?://", "", u)
    u = re.sub(r"^www\.", "", u)
    u = u.split("?")[0].split("#")[0].rstrip("/")
    return u


_DATE_FORMATS = ("%Y-%m-%d %H:%M:%S %Z", "%Y-%m-%d %H:%M:%S", "%d %b %Y", "%m/%d/%y, %I:%M %p",
                 "%m/%d/%Y", "%Y-%m-%d")


def parse_date(s):
    s = (s or "").strip()
    if not s:
        return None
    for fmt in _DATE_FORMATS:
        try:
            d = _dt.datetime.strptime(s, fmt)
            return d.replace(tzinfo=_dt.timezone.utc)
        except ValueError:
            continue
    try:
        return _parse_iso(s)
    except ValueError:
        return None


def _csv_rows(path, header_starts):
    """LinkedIn prefixes some CSVs with a few "Notes:" lines; start at the real header."""
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8-sig", newline="") as fh:
        text = fh.read()
    lines = text.splitlines(keepends=True)
    start = next((i for i, ln in enumerate(lines) if ln.lstrip().startswith(header_starts)), None)
    if start is None:
        raise PilotError(f"{os.path.basename(path)}: header starting {header_starts!r} not found")
    return list(csv.DictReader(io.StringIO("".join(lines[start:]))))


def read_connections(path) -> dict[str, dict]:
    out = {}
    for r in _csv_rows(path, "First Name"):
        url = norm_url(r.get("URL"))
        if not url:
            continue
        name = " ".join(x for x in ((r.get("First Name") or "").strip(),
                                    (r.get("Last Name") or "").strip()) if x)
        out[url] = {"name": name, "company": (r.get("Company") or "").strip(),
                    "position": (r.get("Position") or "").strip(),
                    "email": bool((r.get("Email Address") or "").strip()),
                    "connected_on": parse_date(r.get("Connected On"))}
    return out


def read_messages(path) -> list[dict]:
    out = []
    for r in _csv_rows(path, "CONVERSATION ID"):
        if (r.get("FOLDER") or "").strip().upper() in ("SPAM", "DRAFT", "DRAFTS"):
            continue
        sender = norm_url(r.get("SENDER PROFILE URL"))
        when = parse_date(r.get("DATE"))
        if not sender or when is None:
            continue
        recips = [norm_url(x) for x in re.split(r"[,;]", r.get("RECIPIENT PROFILE URLS") or "")]
        out.append({"conv": (r.get("CONVERSATION ID") or "").strip(), "from": sender,
                    "from_name": (r.get("FROM") or "").strip(),
                    "to": [x for x in recips if x], "at": when,
                    "content": r.get("CONTENT") or ""})
    return out


def infer_owner(messages, connections) -> dict:
    """Whose export is this. The owner is on every conversation, so the URL present in the most
    conversations is the owner. Never in Connections (nobody is their own connection).

    A CHECK THAT CANNOT ESTABLISH THE OWNER MUST NOT GUESS ONE: below 90% coverage this refuses,
    because every sent/received count downstream would be inverted for the wrong guess."""
    convs: dict[str, set] = {}
    for m in messages:
        convs.setdefault(m["conv"], set()).update([m["from"], *m["to"]])
    if not convs:
        return {"url": None, "coverage": None, "conversations": 0, "method": "no messages"}
    counts: dict[str, int] = {}
    for parts in convs.values():
        for p in parts:
            counts[p] = counts.get(p, 0) + 1
    url, n = max(counts.items(), key=lambda kv: (kv[1], kv[0] not in connections))
    cov = n / len(convs)
    return {"url": url, "coverage": round(cov, 3), "conversations": len(convs),
            "method": "most-present participant", "in_connections": url in connections}


def build_people(connections, messages, me) -> tuple[list[dict], list[dict], dict]:
    """The person dicts `relationship_route.routes` expects, the co-occurrence groups, and the
    owner's own sent 1:1 messages (for voice samples)."""
    people: dict[str, dict] = {}
    names: dict[str, str] = {}

    def _p(url):
        if url not in people:
            c = connections.get(url) or {}
            people[url] = {"id": url, "display": c.get("name") or names.get(url) or url,
                           "sent": 0, "copied": 0, "received": 0, "met": 0,
                           "mutual_connection": url in connections, "first": None, "last": None,
                           "channels": ["linkedin"],
                           "facts": {"company": c.get("company") or "",
                                     "position": c.get("position") or ""},
                           "_first_by": None, "_mine": [], "_theirs": []}
        return people[url]

    for url in connections:
        _p(url)
    by_conv: dict[str, list[dict]] = {}
    for m in messages:
        if m["from"] != me and m["from_name"]:
            names.setdefault(m["from"], m["from_name"])
        by_conv.setdefault(m["conv"], []).append(m)

    groups, mine_1to1 = [], []
    for conv, msgs in by_conv.items():
        msgs.sort(key=lambda m: m["at"])
        parts = set()
        for m in msgs:
            parts.update([m["from"], *m["to"]])
        if me not in parts:
            continue                     # not the owner's conversation; nothing to measure
        peers = sorted(p for p in parts if p != me)
        if len(peers) >= 2:
            groups.append({"peers": peers, "at": msgs[-1]["at"]})
        for m in msgs:
            if m["from"] == me:
                tos = [t for t in m["to"] if t != me] or peers
                for t in tos:
                    p = _p(t)
                    p["sent" if len(tos) == 1 else "copied"] += 1
                    _touch(p, m["at"], "me")
                if len(peers) == 1:
                    mine_1to1.append(m)
            elif me in m["to"] or len(peers) >= 1:
                p = _p(m["from"])
                p["received"] += 1
                _touch(p, m["at"], "them")
        if len(peers) == 1:
            _latency(_p(peers[0]), msgs, me)

    out = []
    for p in people.values():
        for key, src, n in (("my_median_reply_hours", "_mine", "replies_to_them"),
                            ("their_median_reply_hours", "_theirs", "replies_from_them")):
            xs = p.pop(src)
            p[n] = len(xs)
            p[key] = round(statistics.median(xs), 2) if xs else None
        p["first_contact_by"] = p.pop("_first_by")
        p["display"] = (connections.get(p["id"]) or {}).get("name") or names.get(p["id"]) or p["id"]
        out.append(p)
    return out, groups, {"mine_1to1": mine_1to1}


def _touch(p, when, who):
    if p["first"] is None or when < p["first"]:
        p["first"] = when
        p["_first_by"] = who
    if p["last"] is None or when > p["last"]:
        p["last"] = when


def _latency(p, msgs, me):
    """Pair each unanswered run of messages with the next reply from the other side, each reply
    consumed once, so three unanswered messages count as one wait, not three."""
    wait_them = wait_me = None
    for m in msgs:
        if m["from"] == me:
            if wait_them is not None:
                p["_mine"].append((m["at"] - wait_them).total_seconds() / 3600.0)
                wait_them = None
            if wait_me is None:
                wait_me = m["at"]
        else:
            if wait_me is not None:
                p["_theirs"].append((m["at"] - wait_me).total_seconds() / 3600.0)
                wait_me = None
            if wait_them is None:
                wait_them = m["at"]


def voice_samples(mine_1to1, *, n=12, min_len=40, max_len=600) -> list[str]:
    """The customer's own words, most recent first. Only their sent 1:1 messages; nothing the
    other person wrote is ever used to model a voice."""
    seen, out = set(), []
    for m in sorted(mine_1to1, key=lambda m: m["at"], reverse=True):
        t = " ".join((m["content"] or "").split())
        if min_len <= len(t) <= max_len and t not in seen:
            seen.add(t)
            out.append(t)
        if len(out) >= n:
            break
    return out


# --------------------------------------------------------------------------- #
# the hub's rules                                                              #
# --------------------------------------------------------------------------- #

def load_scorer(path=None):
    """The hub's `relationship_route`, loaded read-only from its checkout. Only its pure half is
    called (`routes`, `cooccurrence`); the database half is never touched. When the file is not
    there this raises: a different ranking quietly standing in would be a different product."""
    path = path or DEFAULT_HUB_ROUTE
    if not os.path.isfile(path):
        raise PilotError(f"hub routing rules not found at {path}; set LEADFUEL_HUB_ROUTE or "
                         "--hub-route to the hub's relationship_route.py")
    spec = importlib.util.spec_from_file_location("hub_relationship_route", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    for fn in ("routes", "cooccurrence"):
        if not callable(getattr(mod, fn, None)):
            raise PilotError(f"{path} has no {fn}(); not the routing module this was built for")
    with open(path, "rb") as fh:
        mod.__pilot_sha256__ = hashlib.sha256(fh.read()).hexdigest()
    mod.__pilot_path__ = path
    return mod


# --------------------------------------------------------------------------- #
# the model step: local only                                                   #
# --------------------------------------------------------------------------- #

def _loopback_only(url: str) -> str:
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host not in LOOPBACK_HOSTS:
        raise EgressRefused(f"model URL host {host!r} is not this machine; the pilot never "
                            "sends customer data off the box (Law 9)")
    return url.rstrip("/")


def _post_local(url, payload, timeout):
    _loopback_only(url)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        with opener.open(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (OSError, ValueError) as e:   # URLError, HTTPError and timeouts are OSErrors
        raise PilotError(f"the local model at {url} failed ({e}); not substituting anything. "
                         "Re-run when it is up, or use --drafts stub") from e


STUB_DRAFT = "[stub: no model ran; write this note by hand in the walkthrough]"


def draft_note(person_row, samples, *, mode, model=None, url=DEFAULT_OLLAMA_URL, timeout=180):
    if mode == "stub":
        return STUB_DRAFT
    if mode == "cloud":
        raise CloudRefused("no cloud model path exists. Drafting off this machine is the owner's "
                           "decision (card 4) plus the customer's cloud_model consent, and a desk "
                           "must build it as its own gated door; this harness will not fall "
                           "through to one")
    if mode != "ollama":
        raise PilotError(f"unknown draft mode {mode!r}")
    if not model:
        raise PilotError("--ollama-model is required for ollama drafts")
    base = _loopback_only(url)
    facts = person_row.get("matched") or []
    fact = facts[0]["value"] if facts else ""
    prompt = (
        "You write one short LinkedIn message (2 to 4 sentences) as the sender, in the sender's "
        "own voice. Here are messages the sender wrote before:\n\n"
        + "\n---\n".join(samples[:8])
        + "\n\nWrite to " + (person_row.get("display") or "them").split(" ")[0]
        + (f", whose current role is: {fact}" if fact else "")
        + f". The tie: {_tie_for_prompt(person_row)}. Write warmly and plainly. No sales pitch, "
        "no flattery, no invented facts or shared history, no placeholders. Output only the "
        "message.")
    out = _post_local(base + "/api/generate",
                      {"model": model, "prompt": prompt, "stream": False,
                       "options": {"temperature": 0.6}}, timeout)
    text = re.sub(r"<think>.*?</think>", "", out.get("response") or "", flags=re.S).strip()
    if not text:
        raise PilotError("the local model returned nothing; not substituting anything")
    return text


# --------------------------------------------------------------------------- #
# rank: the "25"                                                               #
# --------------------------------------------------------------------------- #

SHEET_COLUMNS = ("rank", "name", "profile", "company", "position", "band", "warmth",
                 "relevance", "score", "why_them", "relationship", "why_now", "best_channel",
                 "draft")


def _why_now(r):
    t = r.get("tie") or {}
    d = t.get("days_since")
    if r.get("hops") == 2:
        return f"reachable through {r['via']['display']}, a tie you can ask"
    if (t.get("interactions") or 0) == 0:
        return "an accepted connection you have never messaged"
    if d is None:
        return "no dated exchange on record"
    if r.get("state") == "dormant":
        return f"a real exchange that has been quiet for {d} days"
    return f"you last spoke {d} days ago"


def _tie_for_prompt(row) -> str:
    """What the model is told about the tie: the measured facts in plain words, never the
    other person's messages."""
    t = row.get("tie") or {}
    if (t.get("interactions") or 0) == 0:
        return ("you are connected on LinkedIn but have never messaged; introduce yourself "
                "briefly and say why you are writing, without pretending to know them")
    d = t.get("days_since")
    return (f"you have exchanged messages before ({t.get('sent', 0)} from you, "
            f"{t.get('received', 0)} from them)"
            + (f", last about {d} days ago" if d is not None else ""))


def rank(customer, *, root=None, top=DEFAULT_TOP, hub_route=None, scorer=None, me_url=None,
         drafts="stub", ollama_model=None, ollama_url=DEFAULT_OLLAMA_URL, now=None) -> dict:
    now = now or _now()
    root = pilot_root(root)
    _require(root, customer, "local_processing")
    if drafts == "ollama":
        _require(root, customer, "local_model")
        _loopback_only(ollama_url)           # refuse before any work, not halfway through
    if drafts == "cloud":
        draft_note({}, [], mode="cloud")     # raises CloudRefused
    meta = _meta(root, customer)
    d = _cdir(root, customer)
    if not meta.get("imported_at"):
        raise PilotError(f"{customer!r} has no imported export")
    scorer = scorer or load_scorer(hub_route)
    conns = read_connections(os.path.join(d, "raw", "Connections.csv"))
    msgs = read_messages(os.path.join(d, "raw", "messages.csv"))

    owner = infer_owner(msgs, conns)
    if me_url:
        me = norm_url(me_url)
        owner = {**owner, "url": me, "method": "given (--me-url)"}
    elif msgs and (owner["coverage"] or 0) < 0.9:
        raise PilotError(f"cannot establish whose export this is: the most-present participant "
                         f"is on {owner['coverage']:.0%} of conversations. Pass --me-url.")
    me = owner["url"]

    people, groups, extra = build_people(conns, msgs, me) if me else (
        build_people(conns, [], "__none__"))
    target = {k: v for k, v in (_read_json(os.path.join(d, "offer.json"), {}) or {}).items()
              if not k.startswith("_") and v}
    links = scorer.cooccurrence(groups) if groups else []
    res = scorer.routes(people, target or None, links=links, now=now, limit=top)
    samples = voice_samples(extra["mine_1to1"])

    rows = []
    for i, r in enumerate(res["routes"], 1):
        t = r.get("tie") or {}
        c = conns.get(r["person"]) or {}
        r["why_now"] = _why_now(r)
        rows.append({
            "rank": i, "name": r.get("display"), "profile": "https://www." + r["person"],
            "company": c.get("company", ""), "position": c.get("position", ""),
            "band": r.get("band"), "warmth": r.get("warmth"), "relevance": r.get("relevance"),
            "score": r.get("score"), "why_them": (r.get("why") or "").split(". ", 1)[-1],
            "relationship": (f"{t.get('sent', 0)} sent / {t.get('received', 0)} received"
                             + (f", {t.get('copied')} copied" if t.get("copied") else "")),
            "why_now": r["why_now"],
            "best_channel": "LinkedIn message" + (" (email on file)" if c.get("email") else ""),
            "draft": draft_note(r, samples, mode=drafts, model=ollama_model, url=ollama_url),
        })

    out = os.path.join(d, "out")
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"top{top}.csv"), "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=SHEET_COLUMNS)
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out, "voice_samples.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(samples) + ("\n" if samples else ""))

    run = {
        "generated_at": _iso(now), "customer": customer, "top": top,
        "scorer": {"module": "relationship_route.routes",
                   "path": getattr(scorer, "__pilot_path__", None),
                   "sha256": getattr(scorer, "__pilot_sha256__", None),
                   "note": res.get("note")},
        "owner": {k: owner.get(k) for k in ("coverage", "conversations", "method",
                                            "in_connections")},
        "counts": {"connections": len(conns), "messages": len(msgs), "people": len(people),
                   "groups": len(groups), "links": len(links), "considered": res["considered"],
                   "ranked": len(rows), "voice_samples": len(samples)},
        "excluded": res.get("excluded"), "target": target or None,
        "drafts": {"mode": drafts, "model": ollama_model if drafts == "ollama" else None},
        "egress": "none" if drafts == "stub" else f"loopback only ({ollama_url})",
    }
    _write_json(os.path.join(out, "run.json"), run)
    # The calibration log starts here: one baseline row per ranked person, carrying the score it
    # was ranked with, so the 14-day check-in has something to be measured against.
    cal = os.path.join(d, "calibration.jsonl")
    for row in rows:
        _append(cal, {"at": _iso(now), "event": "ranked", "person": row["profile"],
                      "rank": row["rank"], "band": row["band"], "warmth": row["warmth"],
                      "relevance": row["relevance"], "score": row["score"],
                      "run": run["generated_at"]})
    _ledger(root, customer, f"rank:{len(rows)}", now)
    return run


# --------------------------------------------------------------------------- #
# delivery, calibration, deletion                                              #
# --------------------------------------------------------------------------- #

def deliver(customer, *, root=None, now=None) -> dict:
    now = now or _now()
    root = pilot_root(root)
    meta = _meta(root, customer)
    meta["delivered_at"] = _iso(now)
    meta["delete_after"] = _iso(now + _dt.timedelta(days=RETENTION_DAYS))
    _save_meta(root, customer, meta)
    _ledger(root, customer, "deliver", now)
    return meta


CAL_EVENTS = ("sent", "replied", "conversation", "no_reply", "not_sent")


def calibrate(customer, person, event, *, root=None, now=None, note="") -> dict:
    now = now or _now()
    root = pilot_root(root)
    if event not in CAL_EVENTS:
        raise PilotError(f"event must be one of {CAL_EVENTS}")
    d = _cdir(root, customer)
    _meta(root, customer)
    want = "https://www." + norm_url(person)
    base = [e for e in _read_jsonl(os.path.join(d, "calibration.jsonl"))
            if e.get("event") == "ranked" and e.get("person") == want]
    if not base:
        raise PilotError("that person was not in a ranked list for this customer")
    b = base[-1]
    entry = {"at": _iso(now), "event": event, "person": want, "rank": b["rank"],
             "band": b["band"], "score": b["score"], "warmth": b["warmth"],
             "relevance": b["relevance"], "run": b["run"], "note": note}
    _append(os.path.join(d, "calibration.jsonl"), entry)
    _ledger(root, customer, f"calibrate:{event}", now)
    return entry


def _deidentify(customer, entries) -> list[dict]:
    """One row per ranked person: band, scores, rank and outcomes. No name, no URL, no note."""
    per: dict[tuple, dict] = {}
    for e in entries:
        key = (e.get("run"), e.get("person"))
        if e.get("event") == "ranked":
            per[key] = {"customer": customer, "run": e.get("run"), "rank": e.get("rank"),
                        "band": e.get("band"), "warmth": e.get("warmth"),
                        "relevance": e.get("relevance"), "score": e.get("score"),
                        "outcomes": []}
        elif key in per:
            per[key]["outcomes"].append(e.get("event"))
    return list(per.values())


def sweep(*, root=None, now=None, dry_run=False) -> list[dict]:
    """Delete every customer folder past its delete_after. De-identified calibration rows are
    kept in the root; everything else goes. Each deletion is checked afterwards, and a folder
    that is still there is reported as `still_present`, never as deleted."""
    now = now or _now()
    root = pilot_root(root)
    report = []
    for name in sorted(os.listdir(root)):
        d = os.path.join(root, name)
        meta = _read_json(os.path.join(d, "meta.json")) if os.path.isdir(d) else None
        if not meta:
            continue
        due = _parse_iso(meta.get("delete_after"))
        if due is None or now < due:
            report.append({"customer": name, "action": "kept",
                           "delete_after": meta.get("delete_after")})
            continue
        if dry_run:
            report.append({"customer": name, "action": "would_delete",
                           "delete_after": meta.get("delete_after")})
            continue
        keep = _deidentify(name, _read_jsonl(os.path.join(d, "calibration.jsonl")))
        shutil.rmtree(d, ignore_errors=True)
        gone = not os.path.exists(d)
        # Written only once the folder is really gone, so a failed sweep that is retried does
        # not count the same people twice.
        if gone:
            for row in keep:
                _append(os.path.join(root, "calibration_aggregate.jsonl"), row)
        report.append({"customer": name, "action": "deleted" if gone else "still_present",
                       "delete_after": meta.get("delete_after")})
        _ledger(root, name, "deleted" if gone else "delete_failed", now)
    return report


def status(*, root=None) -> list[dict]:
    root = pilot_root(root)
    out = []
    for name in sorted(os.listdir(root)):
        meta = _read_json(os.path.join(root, name, "meta.json"))
        if meta:
            out.append({k: meta.get(k) for k in ("customer", "imported_at", "delivered_at",
                                                  "delete_after")}
                       | {"consent": [s for s in SCOPES if has_consent(root, name, s)]})
    return out


# --------------------------------------------------------------------------- #
# CLI                                                                          #
# --------------------------------------------------------------------------- #

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="warm_pilot", description=__doc__.split("\n\n")[0])
    ap.add_argument("--root", help="data root (default LEADFUEL_PILOT_ROOT or "
                                   "%%LOCALAPPDATA%%/leadfuel-pilot); never inside a git tree")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("init"); s.add_argument("customer")
    s = sub.add_parser("consent"); s.add_argument("customer"); s.add_argument("scope", choices=SCOPES)
    s.add_argument("--by", required=True); s.add_argument("--method", required=True)
    s.add_argument("--note", default=""); s.add_argument("--revoke", action="store_true")
    s = sub.add_parser("import"); s.add_argument("customer"); s.add_argument("export")
    s = sub.add_parser("rank"); s.add_argument("customer")
    s.add_argument("--top", type=int, default=DEFAULT_TOP)
    s.add_argument("--hub-route"); s.add_argument("--me-url")
    s.add_argument("--drafts", choices=("stub", "ollama", "cloud"), default="stub")
    s.add_argument("--ollama-model"); s.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    s = sub.add_parser("deliver"); s.add_argument("customer")
    s = sub.add_parser("calibrate"); s.add_argument("customer"); s.add_argument("person")
    s.add_argument("event", choices=CAL_EVENTS); s.add_argument("--note", default="")
    s = sub.add_parser("sweep"); s.add_argument("--dry-run", action="store_true")
    sub.add_parser("status")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "init":
            res = init(a.customer, root=a.root)
        elif a.cmd == "consent":
            res = record_consent(a.customer, a.scope, granted_by=a.by, method=a.method,
                                 note=a.note, revoke=a.revoke, root=a.root)
        elif a.cmd == "import":
            res = import_export(a.customer, a.export, root=a.root)
        elif a.cmd == "rank":
            res = rank(a.customer, root=a.root, top=a.top, hub_route=a.hub_route,
                       me_url=a.me_url, drafts=a.drafts, ollama_model=a.ollama_model,
                       ollama_url=a.ollama_url)
        elif a.cmd == "deliver":
            res = deliver(a.customer, root=a.root)
        elif a.cmd == "calibrate":
            res = calibrate(a.customer, a.person, a.event, root=a.root, note=a.note)
        elif a.cmd == "sweep":
            res = sweep(root=a.root, dry_run=a.dry_run)
        else:
            res = status(root=a.root)
    except PilotError as e:
        print(f"REFUSED: {e}", file=sys.stderr)
        return 2
    # Counts and paths only: the CLI never prints a name, a URL or a message.
    if a.cmd == "rank":
        res = {k: res[k] for k in ("generated_at", "counts", "excluded", "drafts", "egress")}
    if a.cmd == "calibrate":
        res = {k: res[k] for k in ("at", "event", "rank", "band", "score")}
    print(json.dumps(res, indent=2, default=str))
    if a.cmd == "sweep" and any(r["action"] == "still_present" for r in res):
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
