"""Seat licensing for the personal-chat app: one key, up to the build's seat count (3).

The rule this file exists to keep: **a check that cannot establish a state must not report
one.** The app reports exactly one of four states, and only `licensed` unlocks the
"licensed" wording in the UI:

    preview     this build is not configured for sale (no store organisation baked in).
                Every build made before the owner's Polar card is answered is a preview.
    unlicensed  configured for sale, and this computer holds no activation.
    licensed    the store confirmed this computer's activation.
    unknown     configured for sale, an activation is held, but the store could not be
                reached or answered something we do not understand.

Law 9: the only call that leaves the machine goes to the store host named in the build
(allowlisted, https only), and only when the person clicks Activate or the app re-validates a
key they entered. An unconfigured build makes no call at all. The seat label sent to the store
is a random per-install id, never the computer's name.

The store is Polar (owner decision V6). The endpoint shapes below are the public
customer-portal license-key routes as documented by Polar; they are NOT exercised against the
live service by this build (no account exists yet), so treat them as unverified until the
Polar setup card is answered and a test-mode key has been activated once.
"""
from __future__ import annotations

import json
import os
import secrets
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass

PREVIEW, UNLICENSED, LICENSED, UNKNOWN = "preview", "unlicensed", "licensed", "unknown"

ACTIVATE_PATH = "/v1/customer-portal/license-keys/activate"
VALIDATE_PATH = "/v1/customer-portal/license-keys/validate"
DEFAULT_STORE_HOST = "api.polar.sh"


class SeatError(Exception):
    """Activation did not happen. The message is safe to show the person."""


class SeatLimitReached(SeatError):
    pass


class NotForSale(SeatError):
    pass


@dataclass
class Status:
    state: str
    detail: str

    def as_dict(self) -> dict:
        return {"state": self.state, "detail": self.detail}


def store_configured(build: dict) -> bool:
    return bool(build.get("sale_enabled")) and bool(build.get("store_org_id"))


def _store_url(build: dict, path: str) -> str:
    host = build.get("store_host") or DEFAULT_STORE_HOST
    allowed = set(build.get("store_hosts_allowed") or [DEFAULT_STORE_HOST])
    if host not in allowed:
        raise NotForSale(f"store host {host!r} is not on this build's allowlist")
    return urllib.parse.urlunsplit(("https", host, path, "", ""))


def urllib_transport(url: str, body: dict, timeout: float = 15.0):
    """POST json, return (status, parsed body or None). Raises OSError on no answer."""
    req = urllib.request.Request(
        url, data=json.dumps(body).encode("utf-8"), method="POST",
        headers={"Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            raw = r.read()
            return r.status, _parse(raw)
    except urllib.error.HTTPError as e:
        return e.code, _parse(e.read())


def _parse(raw: bytes):
    try:
        return json.loads(raw.decode("utf-8")) if raw else None
    except (ValueError, UnicodeDecodeError):
        return None


def _record_path(store_dir: str) -> str:
    return os.path.join(store_dir, "seat.json")


def read_record(store_dir: str):
    try:
        with open(_record_path(store_dir), encoding="utf-8") as f:
            rec = json.load(f)
        return rec if isinstance(rec, dict) else None
    except (OSError, ValueError):
        return None


def _write_record(store_dir: str, rec: dict) -> None:
    os.makedirs(store_dir, exist_ok=True)
    tmp = _record_path(store_dir) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(rec, f, indent=2)
    os.replace(tmp, _record_path(store_dir))


def install_id(store_dir: str) -> str:
    """A random id for this install. Sent as the seat label instead of the computer's name."""
    path = os.path.join(store_dir, "install_id")
    try:
        with open(path, encoding="utf-8") as f:
            v = f.read().strip()
        if v:
            return v
    except OSError:
        pass
    v = "pc-" + secrets.token_hex(6)
    os.makedirs(store_dir, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(v)
    return v


def _clean_key(key: str) -> str:
    key = (key or "").strip()
    if not key or len(key) > 200 or any(c.isspace() for c in key):
        raise SeatError("That does not look like a licence key.")
    return key


def activate(key: str, store_dir: str, build: dict, transport=urllib_transport) -> Status:
    if not store_configured(build):
        raise NotForSale("This is a preview build. It is not sold yet and takes no licence key.")
    key = _clean_key(key)
    body = {"key": key, "organization_id": build["store_org_id"], "label": install_id(store_dir)}
    try:
        code, data = transport(_store_url(build, ACTIVATE_PATH), body)
    except OSError:
        raise SeatError("Could not reach the store. Check the connection and try again.")
    if code in (200, 201) and isinstance(data, dict) and data.get("id"):
        _write_record(store_dir, {"key": key, "activation_id": data["id"],
                                  "org": build["store_org_id"]})
        return Status(LICENSED, "Activated on this computer.")
    if code == 403:
        n = build.get("max_seats", 3)
        raise SeatLimitReached(
            f"This key is already active on {n} computers. Deactivate one first.")
    if code in (401, 404, 422):
        raise SeatError("The store did not accept that key.")
    raise SeatError(f"The store answered {code}; nothing was activated.")


def check(store_dir: str, build: dict, transport=urllib_transport) -> Status:
    if not store_configured(build):
        return Status(PREVIEW, "Preview build: not for sale, no licence needed or checked.")
    rec = read_record(store_dir)
    if not rec or not rec.get("activation_id") or rec.get("org") != build["store_org_id"]:
        return Status(UNLICENSED, "No licence on this computer yet.")
    body = {"key": rec.get("key", ""), "organization_id": build["store_org_id"],
            "activation_id": rec["activation_id"]}
    try:
        code, data = transport(_store_url(build, VALIDATE_PATH), body)
    except (OSError, NotForSale):
        return Status(UNKNOWN, "Could not reach the store to confirm the licence.")
    if code == 200 and isinstance(data, dict) and data.get("status") == "granted":
        return Status(LICENSED, "Licensed on this computer.")
    if code in (404, 422) or (code == 200 and isinstance(data, dict)
                              and data.get("status") in ("revoked", "disabled")):
        return Status(UNLICENSED, "The store no longer accepts this computer's licence.")
    return Status(UNKNOWN, f"The store answered {code}; licence not confirmed.")
