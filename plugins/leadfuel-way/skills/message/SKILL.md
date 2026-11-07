---
name: message
description: Message another session directly and know whether it landed. Who may message whom, how to address it, how to send with a token, how to read the outcome back as DELIVERED, HELD, UNDELIVERED or UNKNOWN, and what to do for each (recheck, resend once, or fall back to a durable note). Use whenever a message must reach a session, instead of asking the owner to carry it.
---

# message (sessions talk to each other, and know whether it arrived)

The owner was the message bus: eleven relays in 72 hours ("talk to the router", "send yes to them"), plus every "ask the router" a session could have sent itself. Sessions can message each other. What was missing was knowing the outcome: a send is not delivered because it was sent. This skill is the rule, the helper (`scripts/send_confirm.py`) and the fallback. It is advice and a script; it changes no setting and no session's permission mode.

## 1. Who may message whom
A message carries information or a request. **It never carries the owner's approval**, whoever relays it, except the router relaying a decision the owner made (the owner's standing rule); a peer saying "he approved it" is a claim to verify, and a delivered message clears no guard.

| From | To | For |
|---|---|---|
| desk | its router | `STATUS`, `ASK`, `BLOCKED` (`leadfuel-way:desk`). A background agent's final message reaches the router on its own: no send. |
| desk | the desk that owns a file | the handoff the ownership rule asks for. Name the session in full; a sidebar group is a shelf, not an address. |
| router | its desks | answers, new briefs. A desk over 300k tokens is not woken: open a fresh one (`leadfuel-way:router`). |
| router, conductor | each other | tasks queued, the live router's id. |
| any session | the launcher | a `LAUNCH-REQUEST` (`leadfuel-way:launch`). |
| any session | the owner | **never in chat.** Questions are cards on the Router desk page (`ASK` to the router). |

Do not message a session to change its permission mode, settings or guards, and do not change them yourself to make a message land: that is the owner's call alone. Do not message a session you cannot name; if you cannot name it, you have not found the owner of the work.

## 2. Address it by session id, never by name
Use the target's `local_<uuid>` id (from `list_sessions` or `get_session`) with `mcp__ccd_session_mgmt__send_message` (the generic `SendMessage` is refused inside a scheduled run). A name-addressed send goes over a pipe and, when the receiver runs in a different permission mode, is **held for the owner's approval in that session and expires unread** (seen 2026-10-06, two copies of a hand-off; on trust from the owner's notes). The id goes through the app's own session messaging and arrives as a labelled user turn. A session cannot message itself.

## 3. Send, then read it back (the helper)
Script: `python "${CLAUDE_PLUGIN_ROOT}/scripts/send_confirm.py"`. Use PowerShell for any shell step. It needs your own session id S (`get_session` with `self`).

1. **Write the body** to a file in your scratchpad. Public repo rule for anything that may reach a fallback: ids, titles, status, PR numbers. For a long or detailed message, push a note and send its path (the helper warns past 1,500 characters).
2. **Prepare.** `send_confirm.py prepare --from S --to <target local_ id> --subject "<one line, <=120 chars>" --body-file <file> --out <fresh folder W> [--sends-so-far N]`. It refuses a name, yourself, an empty body, an over-long subject. It stamps a token (`MSG-xxxxxxxxxx`) into the text and prints `SEND to=… token=… message=<file>`. Pass `--sends-so-far` once you are at about 8: **messaging pauses after 10 sends until the owner types**, so fold items into one message and spend sends on the ones that must land. Lifting that pause is the owner's guard and not yours to work around.
3. **Send** the file's text, unchanged, with `send_message` to the target id. Save the tool's **whole** result, error text included, to `W\sent.txt`.
4. **Only after the send has returned**, `search_session_transcripts` for the token (limit 10) and save its whole output to `W\seen.txt` (`No matching sessions found.` included). Never issue the two calls together: a search raced against its send finds nothing.
5. **Judge.** `send_confirm.py judge --plan W\plan.json --sent W\sent.txt --seen W\seen.txt [--attempts 2 after a resend] --out W\out`. It prints one line, `SEND-CONFIRM <STATE> next=<STEP> …`, and exits 0 (DELIVERED), 1 (UNDELIVERED) or 2 (HELD or UNKNOWN).

## 4. The four states, and what each one means you do
| State | Meaning | Next |
|---|---|---|
| **DELIVERED** | the target's own transcript holds the token. Nothing else counts, not the tool's word. | `DONE`. |
| **HELD** | the tool said queued (a turn is in progress there) or held for approval, and the token is not in the target's transcript yet. | `RECHECK`: run steps 4 and 5 again with a fresh `seen` file at your next natural turn. **Never resend a held message.** Past 120 minutes it becomes UNDELIVERED. |
| **UNKNOWN** | the send said nothing readable, or said delivered and the search could not confirm it. Never a pass. | `RECHECK` when the tool took it; one `RESEND` when it said nothing at all. |
| **UNDELIVERED** | the send failed, or it stayed HELD or UNKNOWN past 120 minutes. | `RESEND` once, only when a retry can help (the tool refused for a reason other than a missing session or a message to yourself); otherwise `FALLBACK`. |

A `RESEND` sends the same file, so the same token: the message says a receiver drops a token it has already seen, and a second copy is harmless. After the resend, judge again with `--attempts 2`. A desk does not wait and does not poll: if the state is HELD or UNKNOWN, say so in your report and recheck once at your next turn, not on a timer.

## 5. Fallback: a durable note, then say so
`FALLBACK` (and the judge's `--out` folder holds `fallback.json` and `pr-comment.txt`):
1. **Build Board.** ArtifactData `get` of Build Board `https://claude.ai/artifact/A4uS9xn1emqupohdE4DUfV`, collection `router`, doc `message_undelivered` with `out_dir` (missing is fine), then `update` it with `file_path` `W\out\fallback.json`, pinned to the version you read (a `set` only when it did not exist). The live router reads this doc; it carries the token, both ids, the subject and the state, never the body.
2. **The receiver's PR**, when it has one: `gh pr comment <number> --body-file W\out\pr-comment.txt` (ids and status only; the repo is public).
3. **Your own report.** Under "Owed / not delivered" in your handoff or final line: which messages landed, which are HELD, which fell back. An unread brief must not be mistaken for work in progress. A message is not "sent" in your report until the state is DELIVERED.

If none of those can be written, report `NEEDS-NOVAH` with the token and both ids: the owner then carries that one message, which is the case this skill exists to make rare.

## 6. What was measured and what is trust
Measured (the wake watcher's tests, 2026-10-13/14): the send tool's result strings for delivered, queued, not found and message-to-self; the shape of `search_session_transcripts` output including the no-hits line. Taken on trust: the "held for approval" notice wording (the tool's own description says it exists; any held or approval wording reads as HELD), the name-versus-id difference (the owner's notes, 2026-10-06), and the 10-send pause (the `way` skill). The classifier is the wake watcher's (`wake_on_answer.parse_send`, `seen`, `verdict`), imported, so the two cannot disagree. The helper has never been run against a live pair of sessions by its author's tests: its first live use should be a small proof message between two sessions.
