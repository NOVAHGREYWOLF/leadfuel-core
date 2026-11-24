# Competitor note: Otto and XAIStack (mail2-37)

Scope: INTELLIGENCE, written 2026-11-23 from public pages only (nothing of the owner's data sent anywhere). Source of the ask: two private notes (details in the private handoff, not this repo). Default: desk proceeds, the owner only reads it.

## Otto (myotto.ai)

Read from the public home page on 2026-11-23. Everything below is what the page says, not tested.

| Question | Answer |
|---|---|
| What it sells | An "agent computer" device plus its software, "Otto OS". "Buy now" and "Order a device" links. |
| Price | Not on the page. Unknown. |
| What runs locally | One model is labelled local, on-device (llama-3.3). Other models shown (a Claude and a GPT model) are not labelled local, so they are cloud calls. |
| What the software does | Otto OS: a maintained base for running agents. Gateway: per-agent spend limits and model routing, "cloud-to-local routing". Passkey: one-tap sign-in to 2,000+ services without OAuth or CLI tokens. Coming soon: Identity (an email and phone number per agent) and Spend (a virtual card per agent or task). Mobile app to deploy agents and watch spend. |
| Privacy claim | "Not rented from a cloud", Otto OS tagged "E2E encrypted"; the page does not say what the encryption covers. |

## XAIStack

Not found. A web search on 2026-11-23 for the name returned nothing about a product with that name (only generic self-hosted-AI guides). Do not treat any claim about it as known. To close this: the link is in a private note; reading it is an owner-side step (OWNER-STEP below).

## Where NovahOS says or does something different (three lines)

1. Spend and egress are gated by the owner's own approval (Law 9), not a per-agent limit the agent can be configured around; a cloud path is a decision, never a fallback. Otto's Gateway routes to cloud by policy.
2. NovahOS holds the owner's own brain (mail, notes, wearable captures, memory) and learns from it; Otto's page sells an agent runner and credential convenience, with no stated memory of the person.
3. Credentials: Otto Passkey reaches 2,000+ services; NovahOS holds handles, never values, and the model never reads a password (draft PR for chats-11, credential handle layer). The price and range of services are Otto's advantage today.

## Honest read

Otto validates the "own your AI on a box" market and is shipping the agent-identity and virtual-card pieces we have only as design. It is a hardware product; ours is software on the owner's existing machines plus the cluster. No evidence here of what it costs or how well it works.

OWNER-STEP: supply the XAIStack link or name in the desk chat (its location is in the private handoff) | blocks: the XAIStack half of this note.
