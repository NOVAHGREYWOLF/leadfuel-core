#!/usr/bin/env python
"""Phone cards: the bridge between the Router desk page and the owner's phone (G39, piece D).

    python phone_cards.py status
    python phone_cards.py plan  --cards DIR --count N [--limit 500] --out payload.json
    python phone_cards.py push  --payload payload.json --out resp.json
    python phone_cards.py apply --answers resp.json --cards DIR --count N [--versions versions.json]
                                [--now ISO] --out DIR
    python phone_cards.py ack   --ids q1,q2 [--out ack.json]

The desk cards (the Router desk page, collection `questions`) go to the hub, the phone answers them there,
and the next push hands the answers back; `apply` writes each one onto its desk card so the existing wake
pass delivers it to the session that asked. A Claude session runs the steps (`leadfuel-way:wake`, step 3b)
because only it can read and write the page's database; this script does everything else.

LAW 9. `push` and `ack` are the only commands that touch the network, and the only code in this plugin that
can. They do nothing unless PHONE_CARDS_PUSH is exactly `1` AND PHONE_CARDS_URL, PHONE_CARDS_TOKEN and
PHONE_CARDS_ACCOUNT are all set; otherwise they print `PHONE-CARDS OFF: <names that are missing>` (names, never
values), exit 0 and open no connection. The URL must be https (http only for localhost, 127.0.0.1 and [::1])
and a redirect is refused. The token and the account are never printed: not on success, not in an error, not
in a traceback (every failure is reworded to its class name, and what is printed is scrubbed again).

A CHECK THAT CANNOT SEE ITS SUBJECT SAYS UNKNOWN. A hub answer that is not JSON, whose `ok` is not true, or that
has no `answers` list is `PHONE-CARDS UNKNOWN: <why>`, exit 2, and no file is written for `apply` to read.
`complete` (which lets the hub withdraw cards that are no longer on the desk) is true only when every card the
query reported was read, nothing was cut off by a limit and nothing was left out of the payload.

What goes out is the contract's card shape and nothing else: the asking session's id, `wake`, `routed`,
`answer`, `links` and every other key are dropped (and `local_<uuid>` is scrubbed from the text).
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ENV_PUSH, ENV_URL, ENV_TOKEN, ENV_ACCOUNT = "PHONE_CARDS_PUSH", "PHONE_CARDS_URL", "PHONE_CARDS_TOKEN", "PHONE_CARDS_ACCOUNT"
SYNC_PATH, ACK_PATH = "/api/owner-cards/sync", "/api/owner-cards/ack"
TIMEOUT = 20                       # seconds, one request
LOCAL_HOSTS = ("localhost", "127.0.0.1", "::1")
MAX_BODY = 4_000_000               # bytes of a hub answer we will read

MAX_CARDS = 200                    # the hub refuses more in one sync
MAX_OPTIONS = 27
MAX_GUIDE = 20
MAX_ACK = 200
QUERY_LIMIT = 500                  # the wake pass's `limit`: a result that reaches it may be cut off
STALE_HOURS = 48                   # wake_on_answer.MAX_AGE_HOURS: an older answer is listed, never sent
KINDS = ("choice", "step")
VERDICTS = ("approve", "reject", "neutral")
X_KEY = "X"
# Field -> most characters. The hub cuts longer text itself and never refuses it; the bridge cuts first so a
# payload says the same thing on both sides. (Copied from the hub's LIMITS; the key may not be cut at all.)
LIMITS = {"id": 64, "title": 140, "say": 600, "why": 1200, "check": 800, "asker": 140, "posted": 140,
          "default_reason": 400, "label": 200, "effect": 300, "guide": 300, "key": 8, "note": 1000}

SID = re.compile(r"local_[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", re.I)
HEADER_SAFE = re.compile(r"[\x21-\x7e]+")
SLUG = re.compile(r"[a-z][a-z0-9_]{0,39}")


# ---- printing: never a secret -------------------------------------------------------------------------

def _secrets() -> list:
    return [v for v in (os.environ.get(ENV_TOKEN, "").strip(), os.environ.get(ENV_ACCOUNT, "").strip()) if len(v) >= 4]


def say(line: str) -> None:
    """print, with the token and the account scrubbed out of whatever is about to be shown."""
    text = str(line)
    for secret in _secrets():
        text = text.replace(secret, "[hidden]")
    print(text)


# ---- the gate ------------------------------------------------------------------------------------------

def gate(env=None) -> tuple:
    """('on', config) | ('off', [env names]) | ('bad', reason). Reads names and shapes; prints nothing.

    `PHONE_CARDS_PUSH` is listed when it is unset or anything but `1`, the other three when unset or blank."""
    env = os.environ if env is None else env
    missing = []
    if str(env.get(ENV_PUSH, "")).strip() != "1":
        missing.append(ENV_PUSH)
    for name in (ENV_URL, ENV_TOKEN, ENV_ACCOUNT):
        if not str(env.get(name, "")).strip():
            missing.append(name)
    if missing:
        return "off", missing
    token, account = str(env[ENV_TOKEN]).strip(), str(env[ENV_ACCOUNT]).strip()
    for name, value in ((ENV_TOKEN, token), (ENV_ACCOUNT, account)):
        if not HEADER_SAFE.fullmatch(value):
            return "bad", f"{name} has a character a request header cannot carry"
    base = hub_base(str(env[ENV_URL]))
    if base is None:
        return "bad", f"{ENV_URL} must be an https URL (http only for localhost) with no login, query or fragment"
    return "on", {"base": base, "token": token, "account": account}


def hub_base(raw: str):
    """The URL without a trailing slash, or None when it is not allowed."""
    try:
        p = urllib.parse.urlsplit(raw.strip())
        host = p.hostname
        p.port  # noqa: B018 - raises ValueError on a bad port
    except ValueError:
        return None
    if not host or p.username or p.password or p.query or p.fragment:
        return None
    if p.scheme == "https" or (p.scheme == "http" and host.lower() in LOCAL_HOSTS):
        return urllib.parse.urlunsplit((p.scheme, p.netloc, p.path.rstrip("/"), "", ""))
    return None


def _gate_or_exit():
    """(config, None) to go ahead, else (None, exit code) after printing why not."""
    state, info = gate()
    if state == "off":
        say(f"PHONE-CARDS OFF: {', '.join(info)}")
        return None, 0
    if state == "bad":
        say(f"PHONE-CARDS UNKNOWN: {info}")
        return None, 2
    return info, None


# ---- cards: what the page holds ---------------------------------------------------------------------------

def answered(card: dict) -> bool:
    """Same meaning as wake_on_answer.answered: a step card's `not_yet` is not an answer (the owner still owes it)."""
    ans = card.get("answer")
    if ans is None:
        return False
    return not (card.get("kind") == "step" and ans == "not_yet")


def read_cards(cards_dir):
    """({doc id: card}, files seen, [unreadable file names]). One `<id>.json` per card, as ArtifactData
    `query` with `out_dir` writes them (`<out_dir>/questions/<id>.json`); the id is the file name."""
    d = Path(cards_dir)
    files = sorted(d.glob("*.json")) if d.is_dir() else []
    cards, bad = {}, []
    for f in files:
        try:
            value = json.loads(f.read_text(encoding="utf-8-sig"))
        except (OSError, ValueError):
            bad.append(f.name)
            continue
        if isinstance(value, dict):
            cards[f.stem] = value
        else:
            bad.append(f.name)
    return cards, len(files), bad


# ---- cards: what goes to the hub ---------------------------------------------------------------------------

def _text(value, limit: int) -> str:
    """A string cut like the hub cuts it, with any session id taken out. Not a string -> empty."""
    return SID.sub("[session id]", value.strip())[:limit] if isinstance(value, str) else ""


def _key(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _number(card: dict, cid: str):
    n = card.get("n")
    if isinstance(n, int) and not isinstance(n, bool):
        return n
    if isinstance(n, str) and n.strip().isdigit():
        return int(n.strip())
    m = re.fullmatch(r"q(\d+)", cid)
    return int(m.group(1)) if m else None


def clean_wire(raw):
    """One card in the hub's shape, built from the contract's keys only, or None when it cannot be sent.

    A card is not sent when it has no id or title, or when ANY option is malformed (a missing or duplicate
    key, a key longer than the hub keeps, a missing label): dropping one option would show the owner a
    smaller question than the desk asked."""
    if not isinstance(raw, dict):
        return None
    cid, title = _text(raw.get("id"), LIMITS["id"]), _text(raw.get("title"), LIMITS["title"])
    if not cid or not title:
        return None
    options_in = raw.get("options")
    if not isinstance(options_in, list) or not 1 <= len(options_in) <= MAX_OPTIONS:
        return None
    options, keys = [], set()
    for o in options_in:
        if not isinstance(o, dict):
            return None
        key, label = _key(o.get("key")), _text(o.get("label"), LIMITS["label"])
        if not key or len(key) > LIMITS["key"] or not label or key in keys:
            return None
        keys.add(key)
        opt = {"key": key, "label": label}
        if key != X_KEY and o.get("verdict") in VERDICTS:
            opt["verdict"] = o["verdict"]
        options.append(opt)
    card = {"id": cid}
    n = raw.get("n")
    if isinstance(n, int) and not isinstance(n, bool):
        card["n"] = n
    card["kind"] = raw.get("kind") if raw.get("kind") in KINDS else "choice"
    card["title"] = title
    for name in ("say", "why", "check", "asker", "posted"):
        card[name] = _text(raw.get(name), LIMITS[name])
    default = _key(raw.get("default"))
    if default in keys:
        card["default"] = default
    card["default_reason"] = _text(raw.get("default_reason"), LIMITS["default_reason"])
    card["options"] = options
    effects = raw.get("effects")
    if isinstance(effects, dict):
        kept = {k: _text(v, LIMITS["effect"]) for k, v in ((_key(k), v) for k, v in effects.items()) if k in keys}
        if kept:
            card["effects"] = kept
    guide = raw.get("guide")
    if isinstance(guide, list):
        lines = [_text(g, LIMITS["guide"]) for g in guide[:MAX_GUIDE] if isinstance(g, str)]
        lines = [g for g in lines if g]
        if lines:
            card["guide"] = lines
    return card


def desk_to_wire(cid: str, card: dict):
    """The wire card for one desk card (`plain.say` becomes `say`, `plain.effects` becomes `effects`), or None."""
    plain = card.get("plain")
    say_text = plain.get("say") if isinstance(plain, dict) else (plain if isinstance(plain, str) else card.get("say"))
    effects = plain.get("effects") if isinstance(plain, dict) and plain.get("effects") else card.get("effects")
    return clean_wire({"id": cid, "n": _number(card, cid), "kind": card.get("kind"), "title": card.get("title"),
                       "say": say_text, "why": card.get("why"), "check": card.get("check"), "asker": card.get("asker"),
                       "posted": card.get("posted"), "default": card.get("default"),
                       "default_reason": card.get("default_reason"), "options": card.get("options"),
                       "effects": effects, "guide": card.get("guide")})


def make_payload(cards: dict, count: int, files: int, unreadable=(), limit: int = QUERY_LIMIT, max_cards: int = MAX_CARDS):
    """(payload {cards, complete}, report). Newest `n` first, at most `max_cards`."""
    sendable, not_sent, on_desk_answered, on_desk_withdrawn = [], {}, 0, 0
    for cid, card in cards.items():
        if card.get("status") == "withdrawn":
            on_desk_withdrawn += 1
            continue
        if answered(card):
            on_desk_answered += 1
            continue
        wire = desk_to_wire(cid, card)
        if wire is None:
            not_sent[cid] = "no title, or an option that is missing its key or label (or a key repeated or too long)"
        else:
            sendable.append((_number(card, cid), cid, wire))
    sendable.sort(key=lambda t: ((t[0] if t[0] is not None else -1), t[1]), reverse=True)
    cut = len(sendable) - max_cards if len(sendable) > max_cards else 0
    out = [w for _, _, w in sendable[:max_cards]]
    # The first reason that makes the set not provably the whole desk. Any of them means: add and refresh, never withdraw.
    reason = None
    if files != count or len(cards) != count:
        reason = (f"the query reported {count} cards, {files} files are there and {len(cards)} were readable"
                  + (f" (unreadable: {', '.join(list(unreadable)[:5])})" if unreadable else ""))
    elif count >= limit:
        reason = f"the query reached its limit of {limit}, so it may have been cut off"
    elif cut:
        reason = f"{cut} older card(s) did not fit in {max_cards}"
    report = {"sent": len(out), "eligible": len(sendable), "not_sent": not_sent, "answered_on_desk": on_desk_answered,
              "withdrawn_on_desk": on_desk_withdrawn, "complete_reason_not": reason}
    return {"cards": out, "complete": reason is None}, report


# ---- the network --------------------------------------------------------------------------------------

class Unreachable(Exception):
    """The hub could not be asked or answered. The text is already worded for printing: no URL, no secret."""


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # None: urllib then raises the 3xx as an HTTPError
        return None


def _opener(url: str):
    handlers = [_NoRedirect()]
    host = (urllib.parse.urlsplit(url).hostname or "").lower()
    if host in LOCAL_HOSTS:
        handlers.append(urllib.request.ProxyHandler({}))
    return urllib.request.build_opener(*handlers)


def _post(cfg: dict, path: str, body: dict):
    """(HTTP status, parsed JSON object or None). Raises Unreachable, worded without the URL or any secret."""
    url = cfg["base"] + path
    data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, method="POST", headers={
        "Content-Type": "application/json", "Accept": "application/json", "User-Agent": "leadfuel-way-phone-cards/1",
        "X-Service-Token": cfg["token"], "X-Acting-Email": cfg["account"]})
    try:
        with _opener(url).open(req, timeout=TIMEOUT) as resp:
            status, raw = resp.status, resp.read(MAX_BODY)
    except urllib.error.HTTPError as exc:
        status = exc.code
        try:
            raw = exc.read(MAX_BODY)
        except Exception:  # noqa: BLE001
            raw = b""
    except urllib.error.URLError as exc:
        raise Unreachable(f"the hub could not be reached ({type(exc).__name__}: {type(exc.reason).__name__})") from None
    except Exception as exc:  # noqa: BLE001 - reworded: an exception's text can hold the header value
        raise Unreachable(f"the request failed ({type(exc).__name__})") from None
    try:
        parsed = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        parsed = None
    return status, parsed


def _slug(parsed) -> str:
    err = parsed.get("error") if isinstance(parsed, dict) else None
    return f", error {err}" if isinstance(err, str) and SLUG.fullmatch(err) else ""


def check_sync(status: int, parsed):
    """(response, None) or (None, why). Valid only when it is a JSON object, `ok` is true and `answers` is a list."""
    if 300 <= status < 400:
        return None, f"the hub answered with a redirect (HTTP {status}); refused"
    if not isinstance(parsed, dict):
        return None, f"the hub's answer is not a JSON object (HTTP {status})"
    if not 200 <= status < 300:
        return None, f"the hub refused the request (HTTP {status}{_slug(parsed)})"
    if parsed.get("ok") is not True:
        return None, f"the hub's answer does not say ok{_slug(parsed)}"
    if not isinstance(parsed.get("answers"), list):
        return None, "the hub's answer has no answers list"
    return parsed, None


def check_ack(status: int, parsed):
    if 300 <= status < 400:
        return None, f"the hub answered with a redirect (HTTP {status}); refused"
    if not isinstance(parsed, dict):
        return None, f"the hub's answer is not a JSON object (HTTP {status})"
    if not 200 <= status < 300:
        return None, f"the hub refused the request (HTTP {status}{_slug(parsed)})"
    if parsed.get("ok") is not True or not isinstance(parsed.get("delivered"), int) or isinstance(parsed.get("delivered"), bool):
        return None, f"the hub's answer does not say how many were delivered{_slug(parsed)}"
    return parsed, None


# ---- the commands ---------------------------------------------------------------------------------------

def _write_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")


def cmd_status(args) -> int:
    state, info = gate()
    if state == "on":
        say("PHONE-CARDS ON")
        return 0
    if state == "off":
        say(f"PHONE-CARDS OFF: {', '.join(info)}")
        return 0
    say(f"PHONE-CARDS UNKNOWN: {info}")
    return 2


def cmd_plan(args) -> int:
    cards, files, bad = read_cards(args.cards)
    payload, rep = make_payload(cards, args.count, files, bad, limit=args.limit)
    _write_json(Path(args.out), payload)
    say(f"PHONE-CARDS plan: sending={rep['sent']} eligible={rep['eligible']} not-sendable={len(rep['not_sent'])} "
        f"answered-on-desk={rep['answered_on_desk']} withdrawn-on-desk={rep['withdrawn_on_desk']} "
        f"complete={'true' if payload['complete'] else 'false'}")
    for cid, why in sorted(rep["not_sent"].items()):
        say(f"PHONE-CARDS NOT SENT {cid}: {why}")
    if rep["complete_reason_not"]:
        say(f"PHONE-CARDS WARNING: complete=false, so the hub withdraws nothing: {rep['complete_reason_not']}")
    return 0


def cmd_push(args) -> int:
    cfg, code = _gate_or_exit()
    if cfg is None:
        return code
    out = Path(args.out)
    try:
        out.unlink()  # a stale answer file must never be read as this push's answer
    except OSError:
        pass
    try:
        payload = json.loads(Path(args.payload).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        say("PHONE-CARDS UNKNOWN: the payload file cannot be read")
        return 2
    raw_cards = payload.get("cards") if isinstance(payload, dict) else None
    if not isinstance(raw_cards, list) or not isinstance(payload.get("complete"), bool):
        say("PHONE-CARDS UNKNOWN: the payload is not {cards: [...], complete: true|false}")
        return 2
    cards = [c for c in (clean_wire(x) for x in raw_cards) if c is not None]
    dropped = len(raw_cards) - len(cards)
    complete = payload["complete"] and dropped == 0 and len(cards) <= MAX_CARDS
    body = {"cards": cards[:MAX_CARDS], "complete": complete}  # rebuilt here, so a hand-edited file cannot add a key
    try:
        status, parsed = _post(cfg, SYNC_PATH, body)
    except Unreachable as exc:
        say(f"PHONE-CARDS UNKNOWN: {exc}")
        return 2
    resp, why = check_sync(status, parsed)
    if resp is None:
        say(f"PHONE-CARDS UNKNOWN: {why}")
        return 2
    _write_json(out, resp)
    if dropped:
        say(f"PHONE-CARDS WARNING: {dropped} payload card(s) were not in the card shape and were not sent; complete=false")
    say(f"PHONE-CARDS pushed={len(body['cards'])} upserted={resp.get('upserted')} withdrawn={resp.get('withdrawn')} "
        f"skipped={resp.get('skipped')} withdraw_applied={resp.get('withdraw_applied')} answers={len(resp['answers'])}")
    return 0


def cmd_ack(args) -> int:
    cfg, code = _gate_or_exit()
    if cfg is None:
        return code
    ids = list(dict.fromkeys(i.strip()[:LIMITS["id"]] for i in args.ids.split(",") if i.strip()))
    if not ids:
        say("PHONE-CARDS ack: no ids, nothing sent")
        return 0
    delivered = ignored = 0
    last = None
    for start in range(0, len(ids), MAX_ACK):
        try:
            status, parsed = _post(cfg, ACK_PATH, {"card_ids": ids[start:start + MAX_ACK]})
        except Unreachable as exc:
            say(f"PHONE-CARDS UNKNOWN: {exc}")
            return 2
        resp, why = check_ack(status, parsed)
        if resp is None:
            say(f"PHONE-CARDS UNKNOWN: {why}")
            return 2
        delivered += resp["delivered"]
        ignored += resp["ignored"] if isinstance(resp.get("ignored"), int) else 0
        last = resp
    if args.out and last is not None:
        _write_json(Path(args.out), dict(last, delivered=delivered, ignored=ignored))
    say(f"PHONE-CARDS acked={delivered} ignored={ignored} of {len(ids)}")
    return 0


# ---- apply: a phone answer becomes a desk answer ---------------------------------------------------------

def parse_time(value):
    try:
        t = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def page_stamp(t: datetime) -> str:
    """The page's own time format: `2026-10-14T01:45:40.495Z`."""
    t = t.astimezone(timezone.utc)
    return t.strftime("%Y-%m-%dT%H:%M:%S.") + f"{t.microsecond // 1000:03d}Z"


def read_answers(resp):
    """([clean answers], malformed count). An answer needs a card id, a key, a readable time and via `phone`."""
    good, bad = [], 0
    for a in resp.get("answers") or []:
        t = parse_time(a.get("answered_at")) if isinstance(a, dict) else None
        if (not isinstance(a, dict) or not _key(a.get("card_id")) or not _key(a.get("key")) or t is None
                or a.get("via") != "phone"):
            bad += 1
            continue
        note = a.get("note")
        good.append({"id": _key(a["card_id"]), "key": _key(a["key"]), "at": t,
                     "note": note.strip()[:LIMITS["note"]] if isinstance(note, str) else ""})
    return good, bad


def classify(answer: dict, cards: dict, full_read: bool):
    """(state, why). apply | already | conflict | unknown.

    The desk wins: a phone answer is applied only to a card that is still unanswered on the desk. A card that is
    missing from the read is a conflict only when the read was the whole set (the query returns the cards nobody
    has routed, so an absent one was answered and routed, or removed); on a short read it is unknown."""
    card = cards.get(answer["id"])
    if card is None:
        if full_read:
            return "conflict", "not among the desk's unrouted cards: the desk answered and routed it, or removed it"
        return "unknown", "the card is not in a read that was not provably the whole set"
    if card.get("status") == "withdrawn":
        return "conflict", "the desk withdrew the card"
    if answered(card):
        if card.get("answer") == answer["key"] and card.get("answered_via") == "phone":
            return "already", "this phone answer is on the desk card already"
        return "conflict", f"the desk answered {card.get('answer')!r} first"
    options = card.get("options")
    if not isinstance(options, list) or not all(isinstance(o, dict) for o in options):
        return "unknown", "the desk card's options cannot be read"
    if answer["key"] not in {_key(o.get("key")) for o in options}:
        return "conflict", "the key is not one of the desk card's options"
    return "apply", ""


def click_fields(answer: dict) -> dict:
    """What the page writes on a click (answer, answered_at, note, note_at, routed null) plus `answered_via`."""
    stamp = page_stamp(answer["at"])
    data = {"answer": answer["key"], "answered_at": stamp, "answered_via": "phone", "routed": None}
    if answer["note"]:
        data["note"], data["note_at"] = answer["note"], stamp
    return data


def cmd_apply(args) -> int:
    try:
        resp = json.loads(Path(args.answers).read_text(encoding="utf-8-sig"))
    except (OSError, ValueError):
        say("PHONE-CARDS UNKNOWN: the answers file cannot be read")
        return 2
    if not isinstance(resp, dict) or resp.get("ok") is not True or not isinstance(resp.get("answers"), list):
        say("PHONE-CARDS UNKNOWN: the answers file is not a valid hub answer (ok true and an answers list)")
        return 2
    answers, malformed = read_answers(resp)
    cards, files, bad = read_cards(args.cards)
    full_read = files == args.count and len(cards) == args.count
    try:
        versions = json.loads(Path(args.versions).read_text(encoding="utf-8-sig")) if args.versions else {}
    except (OSError, ValueError):
        versions = {}
    if not isinstance(versions, dict):
        versions = {}
    now = parse_time(args.now) if args.now else datetime.now(timezone.utc)

    out = Path(args.out)
    (out / "cards").mkdir(parents=True, exist_ok=True)
    batch, ack_now, ack_after, hold, unpinned, conflicts, seen_ids = [], [], [], [], [], [], set()
    for ans in answers:
        cid = ans["id"]
        if cid in seen_ids:  # the hub sends one answer per card; a repeat is the same card
            continue
        seen_ids.add(cid)
        state, why = classify(ans, cards, full_read)
        if state in ("conflict", "already"):
            ack_now.append(cid)
            if state == "conflict":
                conflicts.append(cid)
                say(f"PHONE-CARDS CONFLICT {cid}: {why}; the desk wins, nothing written (phone said {ans['key']})")
            continue
        if state == "unknown":
            hold.append(cid)
            say(f"PHONE-CARDS HOLD {cid}: {why}; not written, not acknowledged")
            continue
        age = (now - ans["at"]).total_seconds() / 3600 if now else None
        if age is not None and age > STALE_HOURS:
            say(f"PHONE-CARDS NOTE {cid}: answered on the phone over {STALE_HOURS} hours ago, so the wake pass lists it "
                f"as stale and does not send it unless it is run with --only {cid}")
        try:
            version = int(versions[cid])
        except (KeyError, TypeError, ValueError):
            unpinned.append(cid)
            continue
        path = (out / "cards" / f"{cid}.json").resolve()
        path.write_text(json.dumps(click_fields(ans), indent=2, ensure_ascii=False), encoding="utf-8")
        # The same entry wake_on_answer.py judge writes: an `update` merge of the fields in that file, pinned.
        batch.append({"op": "update", "collection": "questions", "doc_id": cid, "if_version": version,
                      "file_path": str(path)})
        ack_after.append(cid)
    _write_json(out / "batch.json", batch)
    _write_json(out / "ack.json", {"ack_now": ack_now, "ack_after_batch": ack_after, "hold": hold + unpinned})
    pins = [b["doc_id"] for b in batch] + unpinned
    if pins:
        say(f"PIN cards={','.join(pins)}")
    if unpinned:
        say(f"NOT WRITTEN (no version to pin): {','.join(unpinned)}")
    if ack_now:
        say(f"ACK-NOW ids={','.join(ack_now)}")
    if ack_after:
        say(f"ACK-AFTER-BATCH ids={','.join(ack_after)}")
    if malformed:
        say(f"PHONE-CARDS WARNING: {malformed} answer(s) in the hub's reply were unreadable (no id, key, time or via phone) and were skipped")
    if bad:
        say(f"PHONE-CARDS WARNING: unreadable card file(s): {', '.join(bad[:5])}")
    say(f"PHONE-CARDS applied={len(batch)} conflict={len(conflicts)}")
    return 2 if hold else 0


# ---- command line -------------------------------------------------------------------------------------------

def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("status", help="print PHONE-CARDS ON or OFF (names only); touches nothing")
    p = sub.add_parser("plan", help="build the payload of unanswered desk cards")
    p.add_argument("--cards", required=True, help="the folder of card files ArtifactData wrote (<out_dir>/questions)")
    p.add_argument("--count", required=True, type=int, help="how many documents the query said it returned")
    p.add_argument("--limit", type=int, default=QUERY_LIMIT, help="the query's own limit; a count that reaches it is not complete")
    p.add_argument("--out", required=True)
    s = sub.add_parser("push", help="POST the payload to the hub (gated by PHONE_CARDS_PUSH=1)")
    s.add_argument("--payload", required=True)
    s.add_argument("--out", required=True, help="where the hub's answer is written, only when it is valid")
    a = sub.add_parser("apply", help="write the phone's answers onto the unanswered desk cards")
    a.add_argument("--answers", required=True, help="the file push wrote")
    a.add_argument("--cards", required=True)
    a.add_argument("--count", required=True, type=int)
    a.add_argument("--versions", default=None, help='{"<card id>": <version>} from the query lines, as for wake judge')
    a.add_argument("--now", default=None)
    a.add_argument("--out", required=True)
    k = sub.add_parser("ack", help="tell the hub which answers are on the desk (gated like push)")
    k.add_argument("--ids", required=True, help="comma list of card ids")
    k.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    handler = {"status": cmd_status, "plan": cmd_plan, "push": cmd_push, "apply": cmd_apply, "ack": cmd_ack}[args.cmd]
    try:
        return handler(args)
    except Exception as exc:  # noqa: BLE001 - never a traceback: it can carry a header value
        say(f"PHONE-CARDS UNKNOWN: internal error ({type(exc).__name__})")
        return 2


if __name__ == "__main__":
    sys.exit(main())
