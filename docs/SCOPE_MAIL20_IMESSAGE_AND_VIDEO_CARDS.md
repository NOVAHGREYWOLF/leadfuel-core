# Scope: mail-20, an iMessage send door and video business cards

Status: SCOPE ONLY. No code, no send path, nothing queued by this document. The owner queues or drops each item.
Source: the owner's note to himself, 2026-08-15 (SELF-MAIL.md mail-20): "I want to be able to send iMessages. So it's me talking and can shoot things off. Need to make video business cards. Then I can go up to people."
Verified by the author: the hub egress door and its destination table were read in `F:\Leadfuel\repos\novahub\egress.py` (the `social` destination is GATED on `outreach_intent.verify`; `email`, `calendar` and `webhook` are LOGGED; there is no `imessage` or `sms` destination). `privacy.py` already lists `imessage` and `messages` as private sources (reading). Taken on trust: the mail body (the part 15 note says it was not opened; the quote above is from the self-mail index) and every Apple platform fact below (nothing was tested).

---

## Item 1. iMessage send door

### What he wants
Send an iMessage as himself ("it's me talking") and have the system shoot messages off for him.

### The fact that decides the design
iMessage has no public send API. Apple's Messages can be driven only from an Apple device signed in to his Apple ID. This estate is Windows plus an iPhone app (`F:\Leadfuel\repos\leadfuel-ios`). I have not confirmed he owns a Mac, so the Mac routes are listed but marked unverified.

### Options, strongest gate first
| Option | How it sends | Who presses send | Law 9 posture |
|---|---|---|---|
| A. Compose-and-tap (recommended first) | The hub holds an approved draft. The iPhone app opens the Messages composer pre-filled (the `sms:` URL or share sheet). | **He taps Send on the phone.** | The tap is the approval. Nothing leaves our systems on its own. The message text does transit our hub to the phone, which is already inside the estate. |
| B. iOS Shortcut sends on an approved item | The app triggers a Shortcut with the Send Message action. | Nobody, if the Shortcut is set to run without asking. | Autonomous send from a phone. Needs the full gate below. Platform limits unverified. |
| C. Mac relay (Messages plus AppleScript, or a third-party bridge) | A Mac runs a small worker that sends through Messages. | Nobody. | Autonomous, plus a new always-on machine and, for bridges, a third party in the path. Not recommended. |

Recommendation: build A first. It is the only option where the human act is physical and cannot be forged by a stale approval. Revisit B only if he says the tap is too slow after A has been used.

### Law 9 gate (named)
An iMessage is a message that reaches a person who never asked, and it cannot be unsent. It is the same harm class as the `social` destination, so it must be gated the same way, not LOGGED like email.

1. New destination `imessage` in the hub's `DESTINATIONS` table (owner of that file: DOORS), policy GATED, handler delegating to `outreach_intent.verify(account_email, approval_id, target=<recipient>, channel="imessage")`. Fail closed: no approval id, a different person, an expired approval, or an unreadable approval row all mean REFUSED with a machine-readable reason.
2. Intent row (`status='intent'`) written before anything is handed to the phone, settled after, as every door does. For option A the settled state is `handed_to_composer`, not `sent`, because we cannot see whether he tapped. The door must never record `sent` for something it cannot observe. A state it cannot establish is `unknown`.
3. Recipient chosen by a person before any text is drafted (the `outreach_intent` rule): the model may draft, it may not pick who gets it.
4. Default deny and a daily ceiling, like `EGRESS_EMAIL_DAILY_MAX`: unset means nothing goes.
5. No fan-out. One recipient per item; a list is refused.
6. Inbound iMessage stays a private source (`privacy.py`). A send door does not authorise reading replies; reading is a separate decision.
7. The app can read and reject but never approve through the connector token (existing owner rule). Approval stays on the owner-only path, not in the phone app's token.

### Open questions for the owner (do not ask in chat; card candidates)
- Does he own a Mac? (decides whether B or C is even possible)
- Is the tap acceptable (A), or must it send without him touching the phone?
- Which recipients: his own contacts only, or leads from scope? Leads makes this commercial outreach and brings consent rules (SMS and iMessage marketing is regulated in the US); that needs a PRIVACY read before it is allowed.

### Lanes and files
DOORS owns the destination, the gate and the egress row. SURFACE or the iOS desk owns the composer hand-off in `leadfuel-ios`. Per SESSION_MAP, DOORS owns `egress.py`; this document edits none of it.

### Done when (from the queue item)
One page scope with the Law 9 gate named: this page. Then queued or dropped by the owner.

---

## Item 2. Video business cards

### What he wants
A short video he can show or send when he meets someone ("then I can go up to people").

### Scope
A card is a 15 to 30 second vertical video (who he is, what he does, one call to action) plus a link or QR to a page. Two separable parts:

1. **Make the video.** LAB's video generation lane (ComfyUI, the GPU). Input: his approved script and his photo or footage. Output: an mp4 in the video app's exports. This is local and spends nothing. LAB never touches `F:\Leadfuel`, so the asset is produced there and handed over as a file.
2. **Deliver it.** Three ways, from safest: (a) he opens it on his phone and shows it in person, nothing transmits; (b) a QR on a physical card or phone wallpaper that opens a page; (c) sending the file or link to a person. (c) is a transmission and is the same gate as Item 1 (a person picks the recipient, he approves, it is logged).

### Law 9 gate (named)
Making the video: none, it stays on the machine. Hosting it on a public URL is publishing, which needs his approval per the standing publish rule; use the existing hub page or `/hire` surface rather than a new vendor. Sending it to a person goes through the Item 1 `imessage` door or the existing `email` door, never a new path. A cloud video generator is a spend and a transmission and is not part of this scope (a cloud path is a decision, never a fallback).

### Open questions
- Script and tone: his words, his face; needs his input, not a model's guess.
- Does the card point at his personal site (`novahgreywolf.com`) or a business front door? That is his call.
- Does he want it playable offline on the phone only (simplest), or hosted?

### Lanes and files
LAB (video generation) for the asset; SURFACE for the page it points at. Nothing in `F:\Leadfuel` changes for the video itself.

### Done when
One page scope with the gate named: this page. Then queued or dropped.

---

## Suggested queue entries (not created here)
- DOORS: `imessage` GATED destination, option A, after the owner answers the Mac and tap questions. Size: small door change plus tests.
- LAB: video card v1, local only, after the owner supplies script and photo.
