"""chats-11 handle layer. Every value here is FAKE and says so; no real credential is read."""
from __future__ import annotations

import ast
import json
import pickle
from pathlib import Path

import pytest

from credhandles import (
    HandleBroker, MemoryBackend, OSVaultBackend, OutboundGuard, Refused, SecretLeak, Target,
    agent_tools,
)
from credhandles.handles import Lease, _SecretValue

FAKE_PW = "FAKE-not-a-real-password-7731"
FAKE_USER = "fake-user@example.test"
ROUTER = "https://router.example.test"


class RecordingSink:
    """Stands in for the browser driver's type-into-field call."""

    name = "type"

    def __init__(self):
        self.typed: list[tuple[str, Target]] = []
        self.leases: list[Lease] = []

    def deliver(self, lease, target):
        self.leases.append(lease)
        self.typed.append((lease.text(), target))


class BrokenSink:
    name = "type"

    def deliver(self, lease, target):
        raise RuntimeError("driver blew up while typing " + lease.text())


class LeakyBackend:
    name = "leaky"

    def fetch(self, ref):
        raise KeyError(f"no entry; the value was {FAKE_PW}")


def _setup(*, approver=lambda req: True, needs_approval=True, kind="password", sinks=("type",)):
    backend = MemoryBackend({"router-admin": FAKE_PW, "router-user": FAKE_USER})
    broker = HandleBroker(approver=approver)
    sink = RecordingSink()
    broker.add_sink(sink)
    handle = broker.register(label="Router admin", backend=backend, ref="router-admin",
                             kind=kind, origins=(ROUTER,), sinks=sinks,
                             needs_approval=needs_approval)
    return broker, backend, sink, handle


def _pw_field(origin=ROUTER):
    return Target(origin=origin, field_kind="password", field_ref="field:3")


def _everything_said(broker, *extra) -> str:
    return json.dumps([broker.audit, broker.list_handles(), repr(broker), [repr(e) for e in extra]],
                      default=repr)


# --- the value has no readable form ------------------------------------------------------------

def test_secret_value_has_no_string_json_or_pickle_form():
    s = _SecretValue(FAKE_PW)
    for rendered in (str(s), repr(s), f"{s}", f"{s!r}", "%s" % (s,)):
        assert FAKE_PW not in rendered
    with pytest.raises(TypeError):
        json.dumps(s)
    with pytest.raises(TypeError):
        pickle.dumps(s)
    s.wipe()
    assert s.wiped and bytes(s._buf) == b""


def test_lease_is_dead_after_delivery():
    broker, _, sink, h = _setup()
    broker.use(h.handle_id, "type", _pw_field())
    with pytest.raises(Refused):
        sink.leases[0].text()
    with pytest.raises(TypeError):
        pickle.dumps(sink.leases[0])


# --- the happy path returns a receipt, never a value -------------------------------------------

def test_use_types_value_and_returns_only_a_receipt():
    broker, backend, sink, h = _setup()
    receipt = broker.use(h.handle_id, "type", _pw_field())
    assert sink.typed == [(FAKE_PW, _pw_field())]
    assert receipt.ok and receipt.origin == "https://router.example.test:443"
    assert FAKE_PW not in json.dumps(receipt.to_agent())
    assert FAKE_PW not in _everything_said(broker, receipt, h, backend)
    assert broker.audit[-1]["outcome"] == "delivered"


def test_handle_shows_no_ref_backend_or_value():
    broker, backend, _, h = _setup()
    shown = json.dumps(broker.list_handles())
    assert "router-admin" not in shown and "memory" not in shown and FAKE_PW not in shown
    assert "router-admin" not in repr(h)
    assert h.handle_id.startswith("cred_")


# --- every gate refuses before the backend is touched ------------------------------------------

@pytest.mark.parametrize("origin", [
    "https://router.example.test.evil.test",   # lookalike suffix
    "https://evil.test/?next=https://router.example.test",
    "https://router.example.test:8443",        # same host, other port
    "http://router.example.test",              # downgrade
    "javascript:alert(1)",
    "",
])
def test_wrong_origin_refused_without_fetch(origin):
    broker, backend, sink, h = _setup()
    with pytest.raises(Refused):
        broker.use(h.handle_id, "type", _pw_field(origin))
    assert backend.fetches == 0 and sink.typed == []
    assert broker.audit[-1]["outcome"] != "delivered"


def test_origin_case_and_default_port_normalised():
    broker, _, sink, h = _setup()
    broker.use(h.handle_id, "type", _pw_field("HTTPS://Router.Example.Test:443/login"))
    assert len(sink.typed) == 1


def test_loopback_http_allowed_other_http_refused_at_register():
    broker = HandleBroker(approver=lambda r: True)
    broker.register(label="dev", backend=MemoryBackend({}), ref="x", kind="token",
                    origins=("http://localhost:8080",), sinks=("type",))
    with pytest.raises(Refused):
        broker.register(label="bad", backend=MemoryBackend({}), ref="x", kind="token",
                        origins=("http://router.example.test",), sinks=("type",))


def test_password_never_typed_into_plain_text_field():
    broker, backend, sink, h = _setup()
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", Target(ROUTER, "text", "field:1"))
    assert e.value.reason == "field_kind_not_allowed"
    assert backend.fetches == 0


def test_username_may_go_into_a_text_field():
    backend = MemoryBackend({"u": FAKE_USER})
    broker = HandleBroker(approver=lambda r: True)
    sink = RecordingSink()
    broker.add_sink(sink)
    h = broker.register(label="u", backend=backend, ref="u", kind="username",
                        origins=(ROUTER,), sinks=("type",))
    broker.use(h.handle_id, "type", Target(ROUTER, "text"))
    assert sink.typed[0][0] == FAKE_USER


def test_sink_not_allowed_for_handle():
    broker, backend, _, h = _setup(sinks=("clipboard",))
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "sink_not_allowed_for_handle" and backend.fetches == 0


def test_sink_allowed_but_not_registered():
    broker, backend, _, h = _setup(sinks=("type", "clipboard"))
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "clipboard", _pw_field())
    assert e.value.reason == "sink_not_registered" and backend.fetches == 0


def test_untrusted_target_shape_refused():
    broker, backend, _, h = _setup()
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", {"origin": ROUTER, "field_kind": "password"})
    assert e.value.reason == "target_not_trusted"


def test_approval_denied_refused_without_fetch():
    seen = []
    broker, backend, _, h = _setup(approver=lambda req: seen.append(req) or False)
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "not_approved" and backend.fetches == 0
    assert seen[0].label == "Router admin" and seen[0].origin.endswith(":443")
    assert FAKE_PW not in repr(seen[0])


def test_truthy_non_true_approval_is_not_approval():
    broker, backend, _, h = _setup(approver=lambda req: "yes")
    with pytest.raises(Refused):
        broker.use(h.handle_id, "type", _pw_field())


def test_no_approver_fails_closed():
    broker, backend, _, h = _setup(approver=None)
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "no_approver" and backend.fetches == 0


def test_revoked_and_unknown_and_foreign_handles_refused():
    broker, backend, _, h = _setup()
    other, _, _, foreign = _setup()
    with pytest.raises(Refused):
        broker.use(foreign.handle_id, "type", _pw_field())
    with pytest.raises(Refused):
        broker.use("cred_madeup", "type", _pw_field())
    broker.revoke(h.handle_id)
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "revoked"
    assert broker.list_handles() == [] and backend.fetches == 0


# --- failures carry a type name, never the value -----------------------------------------------

def test_backend_error_text_never_surfaces():
    broker = HandleBroker(approver=lambda r: True)
    broker.add_sink(RecordingSink())
    h = broker.register(label="x", backend=LeakyBackend(), ref="x", kind="password",
                        origins=(ROUTER,), sinks=("type",))
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "backend_error:KeyError"
    assert FAKE_PW not in str(e.value) and e.value.__context__ is None
    assert e.value.__cause__ is None
    assert FAKE_PW not in _everything_said(broker)


def test_sink_error_text_never_surfaces_and_value_is_wiped():
    backend = MemoryBackend({"r": FAKE_PW})
    broker = HandleBroker(approver=lambda r: True)
    broker.add_sink(BrokenSink())
    h = broker.register(label="x", backend=backend, ref="r", kind="password",
                        origins=(ROUTER,), sinks=("type",))
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "sink_error:RuntimeError"
    assert FAKE_PW not in str(e.value) and e.value.__context__ is None


def test_backend_returning_plain_string_refused():
    class PlainBackend:
        name = "plain"

        def fetch(self, ref):
            return FAKE_PW

    broker = HandleBroker(approver=lambda r: True)
    broker.add_sink(RecordingSink())
    h = broker.register(label="x", backend=PlainBackend(), ref="r", kind="password",
                        origins=(ROUTER,), sinks=("type",))
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "backend_returned_plain_value"


def test_os_vault_backend_is_not_enabled_in_this_draft():
    broker = HandleBroker(approver=lambda r: True)
    broker.add_sink(RecordingSink())
    h = broker.register(label="x", backend=OSVaultBackend(), ref="novahos/anything",
                        kind="password", origins=(ROUTER,), sinks=("type",))
    with pytest.raises(Refused) as e:
        broker.use(h.handle_id, "type", _pw_field())
    assert e.value.reason == "os_vault_not_enabled"


# --- the outbound guard ------------------------------------------------------------------------

def test_guard_catches_a_delivered_value_without_keeping_it():
    broker, _, _, h = _setup()
    broker.use(h.handle_id, "type", _pw_field())
    page_echo = f"<input value='{FAKE_PW}'> welcome back"
    with pytest.raises(SecretLeak) as e:
        broker.guard.check(page_echo)
    assert FAKE_PW not in str(e.value)
    assert broker.guard.check("welcome back") == "welcome back"
    held = repr(vars(broker.guard)) + repr(broker.guard)
    assert FAKE_PW not in held and FAKE_PW.encode() not in held.encode()


def test_guard_unicode_text_is_fine():
    g = OutboundGuard()
    s = _SecretValue("FAKE-ünïcode-pw")
    g._register(s)
    assert g.holds_value("prefix FAKE-ünïcode-pw suffix")
    assert not g.holds_value("prefix FAKE-unicode-pw suffix")


# --- the tools the model sees ------------------------------------------------------------------

def _tools(broker, targets=None):
    targets = targets or {"field:3": _pw_field()}
    return agent_tools(broker, resolve_target=targets.get)


def test_tool_schemas_have_nowhere_for_a_value():
    broker, _, _, _ = _setup()
    tools = _tools(broker)
    assert tools.names() == ["list_credentials", "use_credential"]
    for d in tools.defs():
        schema = d["inputSchema"]
        assert schema["additionalProperties"] is False
        for prop in schema["properties"]:
            assert not any(w in prop.lower() for w in ("pass", "value", "secret", "token", "origin"))


def test_tool_use_round_trip_returns_receipt_only():
    broker, _, sink, h = _setup()
    tools = _tools(broker)
    text, err = tools.call("list_credentials", {})
    assert not err and h.handle_id in text and FAKE_PW not in text
    text, err = tools.call("use_credential", {"handle": h.handle_id, "sink": "type",
                                              "target": "field:3"})
    assert not err and json.loads(text)["value_returned"] is False and FAKE_PW not in text
    assert sink.typed[0][0] == FAKE_PW


def test_tool_refuses_a_smuggled_value_field():
    broker, backend, _, h = _setup()
    text, err = _tools(broker).call("use_credential", {"handle": h.handle_id, "sink": "type",
                                                       "target": "field:3", "password": "x"})
    assert err and json.loads(text) == {"refused": "unexpected_argument"}
    assert backend.fetches == 0


def test_tool_cannot_choose_the_origin():
    broker, backend, _, h = _setup()
    # The model points at a field on an injected page. The driver reports the page's real origin.
    tools = _tools(broker, {"field:9": Target("https://evil.test", "password", "field:9")})
    text, err = tools.call("use_credential", {"handle": h.handle_id, "sink": "type",
                                              "target": "field:9"})
    assert err and json.loads(text) == {"refused": "origin_not_bound"}
    assert backend.fetches == 0


def test_tool_unknown_target_and_unknown_tool():
    broker, _, _, h = _setup()
    tools = _tools(broker)
    text, err = tools.call("use_credential", {"handle": h.handle_id, "sink": "type",
                                              "target": "field:404"})
    assert err and "target_not_found" in text
    text, err = tools.call("show_credential", {"handle": h.handle_id})
    assert err and "unknown_tool" in text


def test_tool_output_is_guarded():
    broker, _, _, h = _setup()
    broker.use(h.handle_id, "type", _pw_field())
    # A label that happens to hold a delivered value is withheld, not returned.
    broker.register(label=FAKE_PW, backend=MemoryBackend({}), ref="z", kind="token",
                    origins=(ROUTER,), sinks=("type",))
    text, err = _tools(broker).call("list_credentials", {})
    assert err and FAKE_PW not in text and "output_withheld" in text


# --- the module reaches nothing outside the process --------------------------------------------

def test_module_imports_no_network_process_or_file_api():
    src = (Path(__file__).resolve().parents[1] / "credhandles" / "handles.py").read_text("utf-8")
    imported = set()
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Import):
            imported |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            imported.add(node.module or "")
    assert imported <= {"__future__", "hashlib", "json", "secrets", "time", "dataclasses",
                        "urllib.parse"}
    assert "open(" not in src
