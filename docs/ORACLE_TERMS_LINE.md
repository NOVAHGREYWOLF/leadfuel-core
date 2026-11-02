# The oracle terms line: the sentence and the paragraph

**DRAFT WORDING FOR THE OWNER'S AGREEMENT. Not agreed, not live, not legal advice.** Written
2026-10-13 (UTC) by COUNSEL · one-interface part · 1 for task `ORACLE-TERMS-LINE` (step 9 of
[ORACLE_PLAN.md](ORACLE_PLAN.md)). Source of the requirement: the "Frame and consent" section of
[ORACLE_FORTUNE_TELLER.md](ORACLE_FORTUNE_TELLER.md). Words only; no code. Nothing here goes
into a terms document, a page or the room until the owner agrees it, and a licensed attorney
should review the final terms text before publication.

## 1. The sentence (shown once per person, then in the room's footer)

Recommended, the one plain sentence:

> **Readings here are for reflection and play, not advice, and the teller is a character.**

The room's footer is narrow, so it also takes the short form of the same line, which is the
wording already in the Frame and consent section:

> **For reflection and play. Not advice.**

Why these words: "reflection and play" says what a reading is for; "not advice" covers medical,
legal and financial advice without listing them where the sentence must stay short (the list is in
the paragraph below); "the teller is a character" says in the room itself what the product's own
voice is not claiming. If the owner prefers the footer to carry the full sentence, one sentence
serves both places.

## 2. The paragraph for the L1 user terms outline

Where it goes: [L1 User Terms and Privacy] (Terms of service, required sections) takes it as a
new section **"Readings (the oracle room)"**, placed after item 8 "Fieldy and recording" and
before item 9 "Acceptable use", with two cross references: item 1 "The service" already says what
the service is not (a clinician, a lawyer, a financial advisor), and item 13 "Disclaimers and
limits" already says "no professional advice". The paragraph:

> **Readings.** The service includes a room where a character, the teller, gives readings from
> tarot, the I Ching, runes, your numbers and your chart. A reading is entertainment and a prompt
> for your own thinking. It is for reflection and play. It is not advice, and it is never medical,
> legal or financial advice, a diagnosis, or a recommendation to buy, sell, sign, start or stop
> anything. Do not rely on a reading for a decision about your health, your legal position or your
> money; ask a qualified professional. The teller is a fictional character. She may speak as if
> she can tell the future, and that is her voice, not a promise or a claim by us that the future can
> be known or that any reading will come true. A reading is made from a draw or a calculation and,
> when you ask for one, from facts you already see on your own sheet; it does not use anything the
> service has not shown you. Readings are for you; they are not shareable from the product. The
> room, like the rest of the service, is for people 18 and over. A reading that costs money shows
> its price before it is made.

## 3. Rule for the product's own copy

- **The product never says "predict" in its own voice.** That covers the menus, buttons, footer,
  landing copy, store listing, notifications, help text and emails. Also avoid "forecast",
  "foresee", "will happen" and "your future" as statements of fact in those places. Say
  "reading", "draw", "what the cards say", "a prompt to think about".
- **The teller may use those words**, because she is a character: her lines are in her voice, in
  quotation, inside the room. This is how both of the owner's statements stay true: his brief says
  predict, the terms say reflection, each in its own register.
- Where a character line is quoted outside the room (a screenshot on a page, a sample reading in a
  deck), it is shown as the teller speaking, with the sentence in section 1 beside it.

## 4. What must be literally true in the code before this is published

The L1 outline's governing rule is that every statement is true in the code before it is
published. The paragraph makes these claims. All are **unverified**: the fortune teller is a
proposal, not built, and COUNSEL did not read the hub. Owners named are the lanes in the plan.

| Claim in the paragraph | Must be true in | Status |
| --- | --- | --- |
| "does not use anything the service has not shown you" (the pack lists only sheet items) | the context pack and its "what she drew on" panel (INTELLIGENCE) | unverified, proposed in the Fortune Teller doc |
| never medical, legal or financial advice; no diagnosis, no buy, sell, sign or stop | the refusals for the six protected kinds, tested (INTELLIGENCE, q376 A) | unverified, proposed |
| "not shareable from the product" | no share, link or export route for readings (SURFACE, DOORS review) | unverified, proposed |
| 18 and over | account eligibility is enforced at sign-up (ToS item 2) | unverified; COUNSEL did not check |
| "shows its price before it is made" | the room's price step before a composed reading (SURFACE, DOORS) | unverified, proposed |

If any row turns out false at build time, the paragraph changes; the code is not made to fit the
words.

## 5. Handoff to SURFACE · ORACLE-FORTUNE-TELLER-ROOM

Use section 1 as written once the owner has agreed it. The room needs: the sentence shown once per
person (suggested: recorded as a notice the person has seen, with a version, like the L1 outline's
consent records, so it can be changed and re-shown; PRIVACY and SURFACE decide the mechanism), and
the short form in the room's footer on every state of the room (table, draw, reading, journal).
Apply section 3 to every string in the room outside the teller's own lines.

## Owner decisions this draft needs

1. Agree or change the sentence in section 1 (default: the recommended full sentence once, the
   short form in the footer).
2. Agree or change the paragraph in section 2, and its position in the L1 outline.
3. Confirm that the L1 outline, which lives outside this repo, is where the paragraph is placed;
   COUNSEL has not edited it.
