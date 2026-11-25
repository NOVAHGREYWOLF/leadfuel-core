# NovahOS front door: sign in on any device, connectors that follow him, one route to any model (p16-9)

Desk NODE, part 203, 2026-11-23 Pacific. Status: **DRAFT for approval from the mockup** ([`docs/mockups/front-door.html`](mockups/front-door.html), open it in a browser; it is a picture, nothing in it is wired). Queue id `p16-9` (also closes `own-4`, its duplicate on the DOORS lane).
Owner words this rests on: 2026-11-18, "signs in on any device and it does the syncing ... must call any model anywhere (API and Claude Code) ... privacy tiers come from surveying the data first"; 2026-10-26, connectors "both, either from desktop app or online, like Claude".

The page is four parts, as the queue item asked: sign-in on two devices, where a connector linked once lives, the model routing table by privacy tier, and the build steps that are not queued yet. Nothing here is built by this PR.

## 1. Sign-in on two devices

| Step | What happens | Where it runs |
|---|---|---|
| 1 | The owner opens NovahOS on GREYWOLF and signs in once with the one account. | The shell's sign-in screen; the account lives on the hub (`lfdesk/auth`). |
| 2 | The hub issues a device session for GREYWOLF: a long-lived token for this device only, stored in the OS credential store (never a file, never the repo). | Hub issues, device stores. |
| 3 | On the Surface he signs in with the same account. The hub issues a second, separate device session. Revoking one never signs out the other. | Same. |
| 4 | Both devices read the same rooms and history from the hub; the device keeps a local cache and syncs by the existing `sync/policy.py` privacy ladder. | Hub is the single home; the vault (VM 103) holds the data. |
| 5 | A new device needs a second proof: a code shown on a device that is already signed in. No code, no session. | Owner's own hands. |

Local-only mode (no account) stays a finished state, not a degraded one: it keeps the local stores and shows "signed out" with no cloud path (`lfdesk/auth/mode.py` LOCAL).

**Open and not decided here:** a new device that cannot reach the hub (no Tailscale yet). The proposal is that it opens in LOCAL mode only and says so.

## 2. Where a connector linked once is stored

One rule, from the owner's 2026-10-26 words: **the connection belongs to the account, every client uses it**.

- The credential lives on the hub, in its credential store, keyed to the account and the connector. It is not copied to the PC and not copied to the phone. (Spec `home-node/33-Connectors-Spec.md` section 0 item 3, "two homes, never both", is overruled by this and needs a revision; that is a spec edit, listed in section 4.)
- The desktop shell, the web shell and the phone are **clients** of that connection. A connector linked on the desktop shows as linked online, and the reverse.
- **Connecting is not arming.** Every use of a connector that leaves the machine is still an order through `lfdesk.doors.out()` and waits for the owner's approval (Law 9). Linking a connector gives no standing permission to send.
- Logins held by a command-line tool on the PC (`gh`, `railway`) stay on the PC; the shell shows their status, it does not copy them.
- Open and not decided: what the desktop does in LOCAL mode with no account (proposal: connectors show as "needs sign-in", nothing is queued).

## 3. Model routing table by privacy tier

Tiers are the four that already exist (`home-node/27-Store-Privacy-Tiers.md`; the JSON the code reads is `lfdesk/privacy/store_tiers.json`). **The assignment of real data to tiers is pending the data survey (queue items U08, W02); this table says what each tier is allowed to reach, not which of his files is in which tier.**

| Tier | Local model (the one service, `node/model_service.json`) | Claude Code or a vendor API | Copy to his other machines |
|---|---|---|---|
| `shared` | yes | yes, each call approved at the gate | yes |
| `private` | yes | yes, each call approved at the gate | yes |
| `secret` | yes | **never as context**; one item at a time through the out door, approved for that item | his own machines only |
| `local_only` | yes | **never** | **never** |

Rules for the router, all of them already policy elsewhere and restated so one page holds them:
1. **Local first.** A request goes to the one local model service unless the owner picked another route for it.
2. **A vendor route is a named decision, never a fallback.** If the local service is down the router says `unknown` or `down` and stops; it does not reach for a vendor. (`node/model_service.py` raises instead of falling through.)
3. **One approval gate** for every outbound model call, free or paid.
4. **Provider keys stay on the vault**, not on any client.
5. Driving Claude Code from the app is a route like an API route, with the same gate. Open and unverified: whether a Claude subscription login may be driven by an app (terms not read).

## 4. Build steps, listed as items not yet queued

These are proposals for the owner to queue; none is in `QUEUE-v2.json` today.

| # | Step | Depends on | Needs the owner |
|---|---|---|---|
| FD-1 | Device sessions on the hub: issue, list, revoke per device; second-device code. | hub change (the hub is shared: its own worktree and desk) | approve the design from the mockup |
| FD-2 | Shell sign-in screen and device-token storage in the OS credential store. | FD-1 | no |
| FD-3 | Account-level connector store on the hub; the desktop reads it as a client. Revise `33-Connectors-Spec.md` section 0 item 3. | FD-1 | approve the spec revision |
| FD-4 | Model router: reads `model_service.json` (built, #this PR) and the tier table above; every vendor route behind the gate. | G03 enabled; U08/W02 survey for real tier assignment | the survey run |
| FD-5 | The walk step: sign in on the Surface and see the same rooms (firstwalk steps 2 and 9). | FD-1, FD-2 | his hands on the Surface |

## Verified and taken on trust

- Verified by reading: the four tiers and their columns (`27-Store-Privacy-Tiers.md`), the LOCAL mode meaning (`lfdesk/auth/mode.py` is cited by the home-node docs; not re-opened), the owner's two quoted instructions (estate memory notes).
- Taken on trust: that sign-in code to the hub exists as the shell claims (CONNECTIONS.md G33 says "not measured"); the hub credential-store shape.

OWNER-STEP: open `docs/mockups/front-door.html`, approve or mark up sections 1 to 3 | blocks: FD-1 to FD-3 (nothing is built until he approves from the mockup).
