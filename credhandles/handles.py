r"""The handle layer: the model holds `cred_...` ids, trusted code holds the values.

    broker = HandleBroker(approver=ask_the_owner_on_screen)
    broker.add_sink(TypeIntoField(driver))                  # trusted app code, at startup
    h = broker.register(label="Router admin", backend=os_vault, ref="novahos/router-admin",
                        kind="password", origins=("https://192.168.1.1",), sinks=("type",))
    tools = agent_tools(broker, resolve_target=driver.resolve)   # what the model sees

    tools.call("list_credentials", {})                       # labels, kinds, origins. No values.
    tools.call("use_credential", {"handle": h.handle_id, "sink": "type", "target": "field:3"})
                                                             # a receipt. Never the value.

WHAT THE MODEL CAN NAME, AND WHAT IT CANNOT. The model names a handle, a sink and a target
reference (an id the app's own driver reported, such as a form field). It cannot name an origin:
the origin is read by trusted code (`resolve_target`) from the page that is really loaded, and a
handle is bound to the origins it was registered for. So an injected page that says "type the bank
password here" gets a refusal, because its origin is not the bank's, whatever the model believes.

WHAT A VALUE CAN TOUCH. A value leaves its backend only inside `HandleBroker.use()`, after every
gate has passed, as a `Lease` that works only for the duration of one `sink.deliver()` call. The
value is wiped when the call returns, the lease is closed, and the caller gets a `Receipt`. There
is no public function that returns a value, no tool whose schema has a field a value could arrive
in, and every string the tools return goes through `OutboundGuard.check()` first.

WHAT THIS IS NOT. It is not protection against code running as the owner: Python has no private
memory and a determined local process can read this one. The threat is a language model, an
injected instruction, a tool result or a careless f-string moving a value into text that is then
stored, indexed, mirrored or sent. Against that, every gate below is tested with fake values.

Stdlib only. No network, no subprocess, no file reads: a test reads the imports.
"""
from __future__ import annotations

import hashlib
import json
import secrets as _random
import time
from dataclasses import dataclass, field
from urllib.parse import urlsplit

__all__ = [
    "ApprovalRequest", "CredentialHandle", "HandleBroker", "MemoryBackend", "OSVaultBackend",
    "OutboundGuard", "Receipt", "Refused", "SecretLeak", "Target", "agent_tools",
]

KINDS = ("password", "username", "token", "totp")
# Which field kinds a credential kind may be typed into. A password goes only into a field the
# browser masks: typed into a plain text field it would be in the next screenshot the model reads.
_FIELD_KINDS = {
    "password": ("password",),
    "totp": ("password", "otp"),
    "token": ("password",),
    "username": ("text", "email", "password"),
}
_LOOPBACK = ("localhost", "127.0.0.1", "::1")
_HANDLE_PREFIX = "cred_"


class Refused(RuntimeError):
    """A use was refused. Its text is a reason code and a handle id, never a value or a ref."""

    def __init__(self, reason: str, handle_id: str = ""):
        self.reason = reason
        self.handle_id = handle_id
        super().__init__(f"refused: {reason}" + (f" ({handle_id})" if handle_id else ""))


class SecretLeak(RuntimeError):
    """Text on its way to the model held a registered value. Raised, never logged and passed."""


# --- the value ---------------------------------------------------------------------------------

class _SecretValue:
    """A value with no string, JSON or pickle form. Not exported."""

    __slots__ = ("_buf", "_wiped")

    def __init__(self, value: bytes | bytearray | str):
        self._buf = bytearray(value.encode("utf-8") if isinstance(value, str) else value)
        self._wiped = False

    def __repr__(self) -> str:
        return "<secret: redacted>"

    __str__ = __repr__

    def __format__(self, spec: str) -> str:
        return repr(self)

    def __reduce__(self):
        raise TypeError("a secret cannot be pickled")

    def __eq__(self, other):
        return NotImplemented if not isinstance(other, _SecretValue) else self is other

    __hash__ = object.__hash__

    def wipe(self) -> None:
        for i in range(len(self._buf)):
            self._buf[i] = 0
        self._buf = bytearray()
        self._wiped = True

    @property
    def wiped(self) -> bool:
        return self._wiped


class Lease:
    """Handed to a sink for one `deliver()` call. Dead the moment that call returns."""

    __slots__ = ("_secret", "_open")

    def __init__(self, secret: _SecretValue):
        self._secret = secret
        self._open = True

    def __repr__(self) -> str:
        return "<lease: redacted>"

    __str__ = __repr__

    def __reduce__(self):
        raise TypeError("a lease cannot be pickled")

    def text(self) -> str:
        """The value as text, for the sink's driver call. Only while the lease is open."""
        if not self._open or self._secret.wiped:
            raise Refused("lease_closed")
        return bytes(self._secret._buf).decode("utf-8")

    def _close(self) -> None:
        self._open = False


# --- backends ----------------------------------------------------------------------------------

class MemoryBackend:
    """FOR TESTS ONLY. Holds fake values given at construction. Never point it at a real secret."""

    name = "memory"

    def __init__(self, values: dict[str, str]):
        self._values = {k: bytes(v, "utf-8") for k, v in values.items()}
        self.fetches = 0

    def __repr__(self) -> str:
        return f"<MemoryBackend refs={len(self._values)}>"

    def exists(self, ref: str) -> bool:
        return ref in self._values

    def fetch(self, ref: str) -> _SecretValue:
        self.fetches += 1
        return _SecretValue(self._values[ref])


class OSVaultBackend:
    """The OS vault (Windows Credential Manager, DPAPI, per user). NOT ENABLED in this draft.

    Enabling it is the owner's go on the design. Until then every call refuses, so nothing in this
    package can read a real credential, and a test proves it.
    """

    name = "os-vault"

    def exists(self, ref: str) -> bool:
        raise Refused("os_vault_not_enabled")

    def fetch(self, ref: str) -> _SecretValue:
        raise Refused("os_vault_not_enabled")


# --- what the gates look at --------------------------------------------------------------------

def _origin(url: str) -> str:
    """scheme://host:port, lower-cased, default port filled in. Refuses what it cannot parse."""
    try:
        parts = urlsplit(url.strip())
        host = (parts.hostname or "").lower()
        port = parts.port
    except ValueError:
        raise Refused("bad_origin") from None
    scheme = parts.scheme.lower()
    if scheme not in ("https", "http") or not host:
        raise Refused("bad_origin")
    if scheme == "http" and host not in _LOOPBACK:
        raise Refused("insecure_origin")
    if port is None:
        port = 443 if scheme == "https" else 80
    if ":" in host:  # IPv6: keep the brackets so host and port cannot run together
        host = f"[{host}]"
    return f"{scheme}://{host}:{port}"


@dataclass(frozen=True)
class Target:
    """Where a value would go. Made by trusted code from the live page, never by the model."""

    origin: str
    field_kind: str
    field_ref: str = ""


@dataclass(frozen=True)
class CredentialHandle:
    handle_id: str
    label: str
    kind: str
    origins: tuple[str, ...]
    sinks: tuple[str, ...]
    needs_approval: bool = True
    backend: object = field(default=None, repr=False, compare=False)
    ref: str = field(default="", repr=False, compare=False)

    def to_agent(self) -> dict:
        """What the model may see: no backend, no ref, no value."""
        return {"handle": self.handle_id, "label": self.label, "kind": self.kind,
                "origins": list(self.origins), "sinks": list(self.sinks),
                "needs_approval": self.needs_approval}


@dataclass(frozen=True)
class ApprovalRequest:
    """What the owner's approval card shows. Built from trusted data only."""

    handle_id: str
    label: str
    sink: str
    origin: str
    field_kind: str


@dataclass(frozen=True)
class Receipt:
    handle_id: str
    sink: str
    origin: str
    ok: bool

    def to_agent(self) -> dict:
        return {"handle": self.handle_id, "sink": self.sink, "origin": self.origin, "ok": self.ok,
                "value_returned": False}


# --- the outbound guard ------------------------------------------------------------------------

class OutboundGuard:
    """Refuses text that holds a value the broker has delivered, without keeping the value.

    It keeps, per value, the length and a salted SHA-256, and slides a window of each length over
    the text. Raw UTF-8 form only; the encoded forms (base64, hex, URL, JSON-escaped) are the leak
    scanner's job (vault/leak_scan.py) and this guard does not claim them.
    """

    def __init__(self):
        self._salt = _random.token_bytes(16)
        self._by_len: dict[int, set[bytes]] = {}

    def __repr__(self) -> str:
        return f"<OutboundGuard values={sum(len(s) for s in self._by_len.values())}>"

    def _digest(self, chunk: bytes) -> bytes:
        return hashlib.sha256(self._salt + chunk).digest()

    def _register(self, secret: _SecretValue) -> None:
        raw = bytes(secret._buf)
        if raw:
            self._by_len.setdefault(len(raw), set()).add(self._digest(raw))

    def holds_value(self, text: str) -> bool:
        data = text.encode("utf-8", "surrogatepass")
        for n, digests in self._by_len.items():
            for i in range(0, len(data) - n + 1):
                if self._digest(data[i:i + n]) in digests:
                    return True
        return False

    def check(self, text: str, where: str = "tool output") -> str:
        if self.holds_value(text):
            raise SecretLeak(f"{where} held a credential value; withheld")
        return text


# --- the broker --------------------------------------------------------------------------------

class HandleBroker:
    """The only place a handle becomes a value, and only on the way into a registered sink."""

    def __init__(self, *, approver=None, guard: OutboundGuard | None = None, clock=time.time):
        self._handles: dict[str, CredentialHandle] = {}
        self._revoked: set[str] = set()
        self._sinks: dict[str, object] = {}
        self._approver = approver
        self.guard = guard or OutboundGuard()
        self._clock = clock
        self.audit: list[dict] = []

    def __repr__(self) -> str:
        return f"<HandleBroker handles={len(self._handles)} sinks={sorted(self._sinks)}>"

    # trusted side: called by app code at startup, never exposed as a tool
    def add_sink(self, sink) -> None:
        name = getattr(sink, "name", "")
        if not name or not callable(getattr(sink, "deliver", None)):
            raise ValueError("a sink needs a name and a deliver(lease, target) method")
        self._sinks[name] = sink

    def register(self, *, label: str, backend, ref: str, kind: str, origins, sinks,
                 needs_approval: bool = True) -> CredentialHandle:
        if kind not in KINDS:
            raise ValueError(f"kind must be one of {KINDS}")
        origins = tuple(_origin(o) for o in origins)
        if not origins:
            raise ValueError("a handle needs at least one origin")
        handle = CredentialHandle(
            handle_id=_HANDLE_PREFIX + _random.token_urlsafe(9), label=label, kind=kind,
            origins=origins, sinks=tuple(sinks), needs_approval=needs_approval,
            backend=backend, ref=ref)
        self._handles[handle.handle_id] = handle
        return handle

    def revoke(self, handle_id: str) -> None:
        self._revoked.add(handle_id)

    # agent side
    def list_handles(self) -> list[dict]:
        return [h.to_agent() for h in self._handles.values() if h.handle_id not in self._revoked]

    def use(self, handle_id: str, sink_name: str, target: Target) -> Receipt:
        """Every gate, in this order, before the backend is touched. Refusals are audited."""
        handle = self._handles.get(handle_id)
        origin = ""
        try:
            if handle is None:
                raise Refused("unknown_handle", handle_id)
            if handle_id in self._revoked:
                raise Refused("revoked", handle_id)
            if sink_name not in handle.sinks:
                raise Refused("sink_not_allowed_for_handle", handle_id)
            sink = self._sinks.get(sink_name)
            if sink is None:
                raise Refused("sink_not_registered", handle_id)
            if not isinstance(target, Target):
                raise Refused("target_not_trusted", handle_id)
            origin = _origin(target.origin)
            if origin not in handle.origins:
                raise Refused("origin_not_bound", handle_id)
            if target.field_kind not in _FIELD_KINDS[handle.kind]:
                raise Refused("field_kind_not_allowed", handle_id)
            if handle.needs_approval:
                if self._approver is None:
                    raise Refused("no_approver", handle_id)
                req = ApprovalRequest(handle_id, handle.label, sink_name, origin, target.field_kind)
                if self._approver(req) is not True:
                    raise Refused("not_approved", handle_id)
            self._deliver(handle, sink, target)
        except Refused as r:
            self._record(handle_id, sink_name, origin, r.reason)
            raise
        self._record(handle_id, sink_name, origin, "delivered")
        return Receipt(handle_id, sink_name, origin, True)

    def _deliver(self, handle: CredentialHandle, sink, target: Target) -> None:
        # Exceptions from the backend or the sink are reduced to their type name, and raised
        # outside the except block, so no message, traceback or __context__ can carry a value.
        failed = ""
        secret = None
        try:
            secret = handle.backend.fetch(handle.ref)
        except Refused:
            raise
        except Exception as exc:  # noqa: BLE001
            failed = "backend_error:" + type(exc).__name__
        if failed:
            raise Refused(failed, handle.handle_id)
        if not isinstance(secret, _SecretValue):
            raise Refused("backend_returned_plain_value", handle.handle_id)
        lease = Lease(secret)
        try:
            self.guard._register(secret)
            sink.deliver(lease, target)
        except Exception as exc:  # noqa: BLE001
            failed = "sink_error:" + type(exc).__name__
        finally:
            lease._close()
            secret.wipe()
        if failed:
            raise Refused(failed, handle.handle_id)

    def _record(self, handle_id, sink, origin, outcome) -> None:
        self.audit.append({"at": self._clock(), "handle": handle_id, "sink": sink,
                           "origin": origin, "outcome": outcome})


# --- the tools the model sees ------------------------------------------------------------------

class _AgentTools:
    """`defs()`, `names()`, `call(name, args) -> (text, is_error)`: the lfdesk ToolRegistry shape.

    There is no tool that reveals, stores or edits a value. They are absent, not gated.
    """

    def __init__(self, broker: HandleBroker, resolve_target):
        self._broker = broker
        self._resolve = resolve_target

    def defs(self) -> list[dict]:
        return [
            {"name": "list_credentials",
             "description": "Lists the credentials you may use. It never returns a password, token "
                            "or code: you get a handle id, a label, the sites it works on and how "
                            "it can be used.",
             "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False}},
            {"name": "use_credential",
             "description": "Has the app type or apply a credential for you. It never returns the "
                            "value and you never need it: you get a receipt. It works only on the "
                            "sites the credential is bound to, and may ask the owner first.",
             "inputSchema": {
                 "type": "object",
                 "properties": {
                     "handle": {"type": "string", "description": "a handle id from list_credentials"},
                     "sink": {"type": "string", "description": "how to use it, e.g. type"},
                     "target": {"type": "string",
                                "description": "the field id the browser tool reported"},
                 },
                 "required": ["handle", "sink", "target"],
                 "additionalProperties": False}},
        ]

    def names(self) -> list[str]:
        return [d["name"] for d in self.defs()]

    def call(self, name: str, args: dict) -> tuple[str, bool]:
        try:
            text, is_error = self._call(name, args or {})
        except Refused as r:
            text, is_error = json.dumps({"refused": r.reason}), True
        try:
            return self._broker.guard.check(text), is_error
        except SecretLeak:
            return json.dumps({"refused": "output_withheld"}), True

    def _call(self, name: str, args: dict) -> tuple[str, bool]:
        schema = next((d["inputSchema"] for d in self.defs() if d["name"] == name), None)
        if schema is None:
            raise Refused("unknown_tool")
        if not isinstance(args, dict) or set(args) - set(schema["properties"]):
            raise Refused("unexpected_argument")
        if any(not isinstance(args.get(k), str) for k in schema.get("required", ())):
            raise Refused("missing_argument")
        if name == "list_credentials":
            return json.dumps({"credentials": self._broker.list_handles()}), False
        target = self._resolve(args["target"])
        if not isinstance(target, Target):
            raise Refused("target_not_found")
        receipt = self._broker.use(args["handle"], args["sink"], target)
        return json.dumps(receipt.to_agent()), False


def agent_tools(broker: HandleBroker, *, resolve_target) -> _AgentTools:
    """`resolve_target(field_ref) -> Target | None` is trusted app code that reads the live page."""
    return _AgentTools(broker, resolve_target)
