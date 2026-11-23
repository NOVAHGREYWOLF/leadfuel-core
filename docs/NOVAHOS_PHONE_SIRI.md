# Talk to NovahOS with Siri (guide v2)

"Hey Siri, ask NovahOS." Siri listens, sends what you said to the local AI on your PC, waits for the
answer, and reads it out loud.

Rewritten 2026-11-23 by NODE (task desks-3-6). It replaces the 2026-11-07 guide, which no longer
works (see "What changed"). Addresses are placeholders in this public copy: `OVERLORD-IP` is the
Tailscale address of the overlord machine (the forward to the phone host), and `GREYWOLF-IP` is the
PC's own Tailscale address. The private copy in the estate folder has the real values.

## What changed since the first guide

1. **A key is now required.** Since the v1.3 hardening (2026-11-08/09) every route that reaches the
   chat needs a paired-device key in the header `X-NovahOS-Device`. The first guide said "no
   passwords, keys or tokens are needed". That was true on 2026-11-07 and is false now. Checked live
   on 2026-11-23: a request without the key gets `401 {"ok": false, "error": "not paired",
   "paired": false}` on both `/api/send` and `/api/ask`, so the old shortcut would say "NovahOS says:
   not paired".
2. **One call replaces the polling loop.** `POST /api/ask` sends the message and waits for the
   answer. The old repeat-and-wait steps are gone from the main version.
3. **The phone's model is the 14B now** (owner card q9432 A; the host's own comment says about 59%
   GPU and 41% CPU on the 8 GB card, about 2.5 tokens per second). A first answer can take a minute
   or more, and a cold model load longer. `/api/ask` waits at most 150 seconds and then answers
   `504 timed out` while the turn keeps running. The shortcut below handles that. Whether iOS gives
   up on a request before 150 seconds was **not measured**: if Shortcuts stops with a timeout
   error, use Version B at the end, which never waits for long.

## Before you start

- **Tailscale must be Connected on the iPhone** (the Tailscale app says Connected). The addresses
  below only work inside the tailnet.
- The PC must be on, with Ollama running and the NovahOS phone host up.
- The phone must be **paired** (Part 1). Pairing is approved at the PC's own screen.
- You need the **Shortcuts** app.

## The address to use

    http://OVERLORD-IP:8106

Use the overlord address. When the PC is off it still answers, with a small "GREYWOLF is offline"
page, so the shortcut can say so in words. The direct address `http://GREYWOLF-IP:8106` also works,
but when the PC is off it only fails with a generic error.

Tip for every step: to add an action, tap the search bar at the bottom, type the action name and tap
it. To pick a value such as "Dictated Text", tap the blue field and choose it from the variable list
above the keyboard.

## Part 1: pair the shortcut (once)

The phone page and each shortcut hold separate keys, so the shortcut pairs on its own. Do this when
you are at the PC.

**On the PC:** double-click `Pair-Phone.cmd` (in `home-node/app/assistant`). It shows a code like
`ABCD-EFGH`. It lasts 10 minutes, works once, and is voided by 5 wrong tries. To label this key
separately, run `phone_guard.py pair --label "iPhone Siri"` instead (same folder). That makes a later
revoke of just this key easy.

**On the iPhone, build "Pair NovahOS":**

1. Shortcuts, tap **+**, rename it **Pair NovahOS**.
2. Add **Ask for Input**. Input Type **Text**. Prompt: `Pairing code from the PC`.
3. Add **Get Contents of URL**. URL: `http://OVERLORD-IP:8106/api/pair`. Tap **Show More**.
   - **Method**: **POST**.
   - **Headers**: add `Content-Type` = `application/json`, and `X-NovahOS` = `1`.
   - **Request Body**: **JSON**. Add a **Text** field: key `code`, value **Provided Input**.
4. Add **Get Dictionary Value**: Get **Value** for `token` in **Contents of URL**.
5. Add **Set Variable**, name it **Key**.
6. Add **If**: **Key** **has any value**.
7. Inside it add **Copy to Clipboard** with **Key**, then **Show Alert**: `Paired. The key is on your
   clipboard. Paste it into Ask NovahOS, step 3, then copy any other text to clear it.`
8. In **Otherwise** add **Get Dictionary Value**: Get **Value** for `error` in **Contents of URL**,
   then **Show Alert** with `NovahOS says: ` and that value. ("code not accepted" means: make a new
   code on the PC.)

Run it, type the code. The key is never shown on screen. It exists only on your clipboard until you
paste it in Part 2. If you lose it, pair again: each pairing makes a new key.

## Part 2: build "Ask NovahOS"

**Version A (one call):**

1. Shortcuts, tap **+**, rename it **Ask NovahOS**.
2. Add **Text**: `http://OVERLORD-IP:8106`. Add **Set Variable**, name it **Server**.
3. Add **Text** and **paste the key** (touch and hold the field, tap Paste). Add **Set Variable**,
   name it **Device**. This text is the key: never share or export this shortcut.
4. Add **Dictate Text**. Tap the arrow, set **Stop Listening** to **After Pause**.
5. Add **Get Contents of URL**. URL: pick **Server**, then type `/api/ask`. Tap **Show More**.
   - **Method**: **POST**.
   - **Headers**: `Content-Type` = `application/json`; `X-NovahOS` = `1`; `X-NovahOS-Device` =
     the variable **Device**.
   - **Request Body**: **JSON**. A **Text** field: key `text`, value **Dictated Text**.
6. Add **Get Dictionary Value**: Get **Value** for `text` in **Contents of URL**. **Set Variable**
   **Answer**.
7. Add **If**: **Answer** **has any value**.
8. Inside it: **Speak Text** with **Answer**.
9. In **Otherwise**: **Get Dictionary Value**: **Value** for `error` in **Contents of URL**. **Set
   Variable** **Problem**.
10. Add **If**: **Problem** **has any value**. Inside it, add another **If**: **Problem** **is**
    `timed out`. Inside that, **Speak Text**: `Still thinking. The answer will be in the NovahOS
    app.` In its **Otherwise**, **Speak Text**: `NovahOS says: ` then **Problem**.
11. In the outer **Otherwise** (no `error` either): **Speak Text**: `I can't reach GREYWOLF. Check
    that the PC is on and Tailscale is on.`
12. Tap **Done**.

Say **"Hey Siri, ask NovahOS."** Speak after the chime, then pause. If Siri mishears the name,
rename the shortcut to something easier, such as **Ask Nova**. The first run asks to allow the
connection: tap **Always Allow**.

## Version B (use this if Version A stops with a timeout)

Same as Version A through step 4, then:

5. **Get Contents of URL**: URL **Server** + `/api/send`, POST, the same three headers, JSON body
   `text` = **Dictated Text**. It returns at once with `conv_id`.
6. **Get Dictionary Value** `conv_id` -> **Set Variable** **Chat**. If **Chat** has no value, read
   `error` as in step 9 above, speak it, and **Stop This Shortcut**.
7. **Repeat** 60 times: **Wait** 3 seconds, then **Get Contents of URL**: URL **Server** +
   `/api/conversation?id=` + **Chat**, method **GET**, one header `X-NovahOS-Device` = **Device**.
   Then **Get Dictionary Value** `conversation`, then `messages`, **Get Item from List** **Last
   Item**, **Get Dictionary Value** `stop_reason`. **If** it has any value: take `text` from the
   item, **Speak Text**, **Stop This Shortcut**.
8. After **End Repeat**: **Speak Text**: `Still thinking. The answer will be in the NovahOS app.`

(The second call is a GET: it needs only the key header, not `X-NovahOS` or a content type.)

## "Keep going" version (optional)

Duplicate **Ask NovahOS**, rename the copy **Continue NovahOS**. Right after step 3 add **Get
Contents of URL** (`Server` + `/api/conversations`, GET, header `X-NovahOS-Device`), **Get Dictionary
Value** `items`, **Get Item from List** **First Item**, **Get Dictionary Value** `id`, **Set
Variable** **Last**. In the body of the ask call add a second Text field: key `conv_id`, value
**Last**. With no recent chat, **Last** is empty and NovahOS starts a new one.

## What you hear when something is off

| Situation | Answer |
|---|---|
| The PC is off (overlord address) | "I can't reach GREYWOLF. Check that the PC is on and Tailscale is on." |
| The PC is off (direct address) | Nothing spoken; Shortcuts stops with a connection error |
| Tailscale is off on the iPhone | Nothing spoken; Shortcuts waits, then stops with a connection error |
| Not paired, key wrong or revoked | "NovahOS says: not paired" (401). Pair again (Part 1) |
| The PC cannot check who you are | "NovahOS says: identity check unavailable" (503). Wait a minute; it happens when the PC is overloaded |
| Another turn is running | "NovahOS says: a turn is already running" (409). Wait, ask again |
| Missing or wrong headers | "NovahOS says: missing X-NovahOS header" (403), or "Content-Type must be application/json" (415) |
| Nothing was heard | "NovahOS says: empty message" (400). Speak sooner |
| More than 150 seconds | "Still thinking. The answer will be in the NovahOS app." (504, the turn keeps running) |

## Troubleshooting

| Problem | Try |
|---|---|
| "I don't see an app for that" | Say the shortcut's name exactly, or rename it **Ask Nova** |
| It hears nothing | **Dictate Text**: **Stop Listening** must be **After Pause** |
| Always "I can't reach GREYWOLF" | Is Tailscale on? Is the PC on? Open `http://OVERLORD-IP:8106` in Safari. If the page loads, the address is fine; check the headers in step 5 |
| Always "not paired" | Pair again (Part 1). Check that the key was pasted whole, with no space, into step 3 |
| "misdirected request" | The address was typed differently. Use exactly `http://OVERLORD-IP:8106`, no `https` |
| Very slow first answer | The 14B model is cold or the PC is busy. Ask again once it has loaded. A cold load can take minutes |
| Siri cuts the shortcut off | Run it once from the Shortcuts app first, then try Siri |

## If the phone is lost, or you want the key gone

On the PC, from the assistant folder: `phone_guard.py list` shows paired devices, `phone_guard.py
revoke <id>` removes one, `phone_guard.py revoke --all` removes every key at once. The change takes
effect on the next request; no restart. `phone_guard.py brain off` stops the phone reading your brain
while keeping chat.

## What was checked, and what was not

Checked live from the PC on 2026-11-23: the phone host and the overlord forward both answer
`/api/health` with 200; a request without a key to `/api/ask` or `/api/send` gets the 401 body
quoted above; the route table and the header and status rules in this guide match the host's source
(`phonehost.py`, `phone_guard.py`) and its spec (`PHONE.md`).

**Not checked:** the taps on an iPhone (labels differ a little between iOS versions); a paired
`/api/ask` call (pairing is approved at the PC by you, so nobody else can do it); how long iOS waits
before giving up on a slow request; the "PC is off" rows.
