# chats-11: a password manager inside the NovahOS desktop app, and credentials the model never sees

Status: **DRAFT, design awaiting the owner's go.** The handle layer in [`credhandles/`](../credhandles/)
is built and tested with fake values only. Nothing in this PR reads, stores or prints a real
credential, and the OS-vault backend refuses every call until the go.

Asked four times: a KeePass vault with Drive sync (2026-08-24), "do credentials without knowing the
password" (2026-10-14), "embedded in the NovahOS desktop app" (2026-10-30), and the local AI typing
passwords and opening admin panels (2026-11-09). Source: queue item `chats-11`.

## 1. What already exists, and what this adds

The home-node app already has a KeePassXC bridge, `home-node/app/lfdesk/vault/` (estate repo, not
this one). It covers the owner's **existing** vault: search titles, apply a value to registered app
code, copy to the clipboard with auto-clear, and create a new entry whose password KeePassXC
generates. It has no show-in-chat, no unlock tool, a voice challenge word, and no cloud access.
That design is sound and this one does not replace it.

What it does not cover, and this adds:

| Gap | This design |
|---|---|
| The model names entries by vault path, so the path is the capability | The model holds **opaque handles** (`cred_` + random), minted per app session, meaningless outside it, revocable |
| No way to **type** a credential into a page (the 2026-11-09 ask) | A `type` sink that trusted driver code calls, with the value going straight from the store to the field |
| Nothing binds a credential to **where** it may go | Each handle is bound to exact origins (scheme, host, port). The origin is read from the live page by trusted code, never taken from the model |
| App-held credentials (connector tokens, the app's own keys) have no home | The **OS vault** (section 3) |
| No check on what flows back to the model after a value is used | `OutboundGuard` refuses any tool output that holds a delivered value |

## 2. Threat model

**Protected asset.** Credential values: passwords, API tokens, TOTP codes and seeds, recovery codes.

**Who we defend against.**

1. **The model itself**, local or cloud. Anything in its context can be repeated, summarised, stored
   in history, embedded, mirrored to Postgres, or sent to a vendor. A cloud model is a transmission
   (Law 9). So the rule is structural: **a value is never in the model's context, inputs or outputs.**
2. **Prompt injection.** A web page, email or document the model reads tells it to type the bank
   password into a field on the attacker's page, or to "read the password back to confirm".
3. **Accidental persistence.** A value in an f-string, an exception message, a log line, an audit
   row, a traceback, a screenshot, the clipboard history.
4. **Look-alike targets.** `bank.example.com.evil.test`, an http downgrade, a different port, a
   redirect parameter that contains the real host.

**Not in scope, stated so nobody assumes it.** Malware running as the owner (it can read this
process and the OS vault alike); a compromised OS; physical access to an unlocked machine; the
owner choosing to read his own vault in his own password manager window.

**Attack paths and the control for each.**

| Path | Control | Test |
|---|---|---|
| Model asks for the value | No tool returns one; the schema has no field a value can arrive in or leave by | `test_tool_schemas_have_nowhere_for_a_value`, `test_tool_use_round_trip_returns_receipt_only` |
| Model smuggles a value in (to store it) | `additionalProperties: false` plus a second check in code | `test_tool_refuses_a_smuggled_value_field` |
| Injected page asks for the bank password | Origin read from the live page by the driver, compared to the handle's bound origins | `test_tool_cannot_choose_the_origin`, `test_wrong_origin_refused_without_fetch` |
| Look-alike or downgraded origin | Exact scheme+host+port match, http only for loopback | the six parametrised origins |
| Password typed into a plain text field, then screenshotted | A password, token or TOTP goes only into a masked field | `test_password_never_typed_into_plain_text_field` |
| A use the owner did not mean | Per-use approval card built from trusted data (label, origin, sink), fails closed with no approver; only `True` approves | `test_approval_denied_refused_without_fetch`, `test_no_approver_fails_closed`, `test_truthy_non_true_approval_is_not_approval` |
| A handle copied from an old transcript | Handles are random per session and revocable | `test_revoked_and_unknown_and_foreign_handles_refused` |
| Value in an exception, traceback or audit row | Errors reduced to a type name and raised outside the `except`, so there is no message and no `__context__`; audit rows hold handle, sink, origin, outcome only | `test_backend_error_text_never_surfaces`, `test_sink_error_text_never_surfaces_and_value_is_wiped` |
| Value lingering in memory | Delivered through a `Lease` that dies when `deliver()` returns; the buffer is zeroed | `test_lease_is_dead_after_delivery` |
| Page echoes the value back and the model reads it | `OutboundGuard` keeps a salted hash per delivered value and refuses tool output that contains it | `test_guard_catches_a_delivered_value_without_keeping_it`, `test_tool_output_is_guarded` |
| `str`, `repr`, `json`, `pickle` of a value | No such form; each redacts or raises | `test_secret_value_has_no_string_json_or_pickle_form` |
| The layer itself reaching the network | Stdlib only, imports read by a test | `test_module_imports_no_network_process_or_file_api` |

**Honest limits.** Python has no private memory, so the guarantees are against accident and against
the model, not against hostile local code. The outbound guard checks the raw UTF-8 form only; encoded
forms (base64, hex, URL, JSON-escaped) are the leak scanner's scope (`vault/leak_scan.py`), not this
guard's. A screenshot of a masked field shows dots; a page that unmasks it on its own is caught only
if its text comes back through a tool, not if it comes back as pixels. That last one is why the
`type` sink should blank or skip the screenshot that follows a delivery (section 4, open item).

## 3. Where secrets live

**The app stores credentials in the OS vault, and nowhere else.**

- Windows: Credential Manager generic credentials, protected by DPAPI under the owner's own Windows
  account. Target names are namespaced `novahos/<label>`. macOS Keychain and the Secret Service API
  are the same shape for later machines.
- **Never** in `.env`, a config file, the app's SQLite history, the Postgres mirror, the brain, a
  synced folder, a log, or the clipboard history.
- The handle registry holds `(backend, ref)` pairs. A `ref` is a name inside the store, never a
  value, and the model never sees it either.

**The owner's own password manager stays his.** His existing KeePassXC vault is reached through the
existing `lfdesk.vault` bridge as a second, read-through backend: the handle layer asks it for a
value at the moment of use and never copies the value into the OS vault or anywhere else. That
keeps one source of truth for his passwords, keeps his Drive-synced file under his control, and
means this design adds no new copy of any password he already has.

**How a credential gets into a store, without the model.** Only by the owner, in his own UI: the
app's credential screen (a native password box that writes straight to the OS vault), or his
KeePassXC window. A credential the app makes for itself (a generated password, an OAuth refresh
token from a connector the owner signed in to) is written by trusted code straight to the OS vault.
No tool can store a value.

## 4. The interface the agent sees

Two tools. Nothing else exists: no reveal, no store, no edit, no unlock. Absent, not gated.

```
list_credentials {}                                   -> {"credentials": [
                                                           {"handle": "cred_Xy...", "label": "Router admin",
                                                            "kind": "password",
                                                            "origins": ["https://192.168.1.1:443"],
                                                            "sinks": ["type"], "needs_approval": true}]}

use_credential {"handle": "cred_Xy...",               -> {"handle": "cred_Xy...", "sink": "type",
                "sink": "type",                           "origin": "https://192.168.1.1:443",
                "target": "field:3"}                      "ok": true, "value_returned": false}
                                                       or {"refused": "<reason code>"}
```

- `target` is a field id the app's browser tool reported. Trusted driver code turns it into a
  `Target(origin, field_kind)` by reading the live page. The model cannot supply an origin.
- `sink` is a name of trusted app code registered at startup. Planned sinks: `type` (into a masked
  field), `apply` (hand to a registered consumer, the same idea as the bridge's `use`), `clipboard`
  (with auto-clear, the bridge's existing mode). This draft ships the gate; the real `type` sink is
  written against the browser driver once the design has its go.
- The gate order in `HandleBroker.use()`: handle known, not revoked, sink allowed for the handle,
  sink registered, target came from trusted code, origin bound, field kind allowed, approval. **The
  backend is not touched until all eight pass** (each refusal test asserts zero fetches).
- Tool shape is the `lfdesk` `ToolRegistry` duck type (`defs`, `names`, `call -> (text, is_error)`),
  so it can sit beside the vault bridge's tools without a special case.

**Open items for the build after the go** (not built here): the Windows Credential Manager backend
(ctypes `CredReadW`/`CredWriteW`, no subprocess); the `type` sink against the app's browser driver,
including blanking the screenshot after a delivery; the owner's credential screen; the approval card
in the app; wiring the KeePassXC bridge as a backend; persisting the audit rows (they are safe to
persist: no values, no refs).

## 5. What the go decides

One yes on this shape: **the OS vault is the app's only store; the owner's KeePassXC vault is a
read-through backend that is never copied; the model sees handles, never values; every use is bound
to an origin and approved.** With that, the next desk builds the Windows backend, the `type` sink and
the approval card. Without it, nothing here can touch a real credential, because the only real
backend refuses.

## Verified and taken on trust

- Verified by this desk: the handle layer and its 34 tests pass locally with fake values
  (`python -m pytest tests/test_credhandles.py`); the existing bridge's modes and its no-show-in-chat
  reasoning, read from `lfdesk/vault/__init__.py`, `tools.py`, `secret.py` and `SETUP.md`.
- Taken on trust: the dates and wording of the four asks, from the queue item's planner fields; the
  VAULT desk's `SECRETS-NEVER-SEEN` design, which is private and was not read.
