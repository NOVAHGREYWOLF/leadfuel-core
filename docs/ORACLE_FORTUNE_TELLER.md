# The Fortune Teller: a place you go, a character who reads for you, and knows you

Part of the oracle set: [ORACLE_PLAN.md](ORACLE_PLAN.md) (overview, principles, tasks),
[ORACLE_NUMEROLOGY.md](ORACLE_NUMEROLOGY.md), [ORACLE_ASTROLOGY.md](ORACLE_ASTROLOGY.md).
Written 2026-10-12 by DESIGN · one-interface part · 4 on the owner's direct request. Proposal, not built.

The owner's words (2026-10-12, this desk's chat): "I also want a place you can go to the fortune
teller. The fortune teller uses tarro decks or other methods to predict your future. it has all
your info."

## What it is in one line

A room on the command screen with a character in it. You bring a question or just sit down. She
reads for you with tarot, the I Ching, runes, your numbers or your chart, and the reading is
grounded in what the brain already knows about you: your goals, your needs, today's plan, what
happened lately, what is rising and what is cooling. The draw is honest (real randomness, recorded),
the reading says what it drew on, and it is saved so you can come back to it.

## Why it fits the game

The owner wants an RPG where you go into the character and places and things pull up (2026-10-07).
Every RPG has a fortune teller: the NPC in the tent at the edge of town who tells you something
true about your quest. Here the "something true" is real, because the brain has the evidence. The
character sheet shows what you are; the fortune teller tells you what it might mean. It is the
warmest surface in the product and it works at level 1 with almost no data, which makes it a hook:
the first visit already knows your numbers and your sun sign, and every level after that she knows
more and says so.

It also fits the rules the owner has already set: nothing outward, nothing spent without a shown
price, inferred things marked inferred, the six protected kinds never guessed, and a cloud model
only as a decision. A reading is inward: it changes nothing in the world. At most it proposes a
quest, which goes through the same queue as everything else.

## The place

Under q369 B (keep today's /command, add panels), the fortune teller is not a new region; it is
a **destination** reached from two existing places:

- **From the character pane:** a "Visit the fortune teller" line under the Numbers and Sky
  families (the pane is the one that is already there, extended; the owner's words of 2026-10-12).
- **From the map / world view:** a landmark (the tent, or a crystal room in the owner's crystal
  aesthetic) that the camera flies to. On the phone it is a tab under the Character.

Inside, one screen with three states:

1. **The table.** The teller (face, name, a line of greeting that uses what she knows: "Your
   personal day is 7 and the Moon is in your sign; a quiet day to ask a real question"). The
   methods laid out as objects on the table: a deck, three coins, a bag of runes, a chart wheel,
   a numbers board. A question box (optional). The price of a written reading shown before you
   touch anything: free for the daily card and the template lines, a shown price for a composed
   reading (metered model call), and zero when the local model does it.
2. **The draw.** The animation: cards turned one by one, coins thrown six times, runes pulled.
   The result is on screen before any words, so the person sees the draw was made first and the
   words came after.
3. **The reading.** The composed text, with a "what she drew on" panel listing every fact from
   the brain that was used (each a line the person already has on the sheet), and three buttons:
   save (default, already saved), "this landed", "this did not" (a journal mark, not a score), and
   "make it a quest" for any concrete suggestion in the text.

A fourth state is the **journal**: every past reading, by date and method, re-readable, with the
draw shown exactly as it was.

## The teller

A separate NPC persona, not the owner's own character (the owner's character is the player; the
teller is someone you visit). She has a name (DESIGN proposes three; the owner picks), a face from
the Studio in the game's style, and a voice later. Her tone is warm, specific and brief; she speaks
in second person, names the cards, and never pads. She says what she does not know ("you have not
told me where you were born, so I cannot see your rising sign").

Voice is text-only in v1. A spoken voice must run on the node (local TTS); a hosted voice service
transmits the reading off the machine and is a Law 9 gate on its own, even when free.

## The methods

| Method | Draw | Material | Needs |
| --- | --- | --- | --- |
| Card of the day | One card, once a day, reversals on | Rider-Waite-Smith deck, 78 cards | Nothing |
| Three cards | Past, present, future, or situation, action, outcome (the person picks) | Same deck | Nothing; better with a question |
| Celtic Cross | Ten positions | Same deck | A question |
| Yes or no | One card; upright yes, reversed no, with the card's reason | Same deck | A question |
| I Ching | Three coins thrown six times; hexagram, changing lines, the resulting hexagram | Wilhelm/Baynes or Legge text (public domain) | A question |
| Runes | One, three or five from the Elder Futhark (24) | Rune meanings | Nothing |
| Your numbers | No draw: the profile and today's numbers | ORACLE_NUMEROLOGY.md | Date of birth and name stated |
| Your chart | No draw: natal placements and this week's transits | ORACLE_ASTROLOGY.md | Date, time, place stated |
| Oracle decks | Later: other decks as data files | Per deck | Per deck |

**Honest randomness.** Every draw uses the operating system's cryptographic random source
(`secrets`), server-side. The draw is recorded with the reading (card ids, orientations, coin
values) so the reading is reproducible and so nobody can later claim the system chose flattering
cards. The composer never sees a choice of cards; it is told the draw.

**Card meanings.** A table in our own words: for each of the 78 cards, upright and reversed,
keywords and a one-paragraph meaning, plus position-sensitive notes. Waite's 1910 text is public
domain and a source; the shipped table is written for this product. Same for 64 hexagrams and 24
runes. These tables are data files, not code, and are the only material the free, no-model
readings use.

**Deck art.** The 1909 Pamela Colman Smith deck is public domain in the United States and is the
stand-in. A deck in the game's own style (the Studio, DESIGN's lane) is the real thing and is a
later task with the owner's spend ceiling on it.

## "It has all your info": what the reading is grounded in, and what it is not

The composer is handed a **context pack** built from the brain for that person, in this order of
trust (W1: a correction outranks any inference, a confirmed claim is 1.0):

1. **Stated and confirmed:** name, the numbers, the chart, confirmed goals (with momentum),
   confirmed interests and their phase, confirmed relationships named on the sheet.
2. **Measured, already shown elsewhere:** today's plan from Lucid, outcomes recorded this week,
   the queue size, sleep and recovery if the person connected Apple Health and sees it on the sheet.
3. **Inferred, unconfirmed:** interests and traits the sheet shows as INFERRED. Used only as
   "the cards suggest, and your records hint" language, never as fact, and listed in the "what
   she drew on" panel as inferred.
4. **The question**, verbatim.

**Never in the pack, under any method, whatever the question:** the six kinds the owner ruled on
(q376 A): politics, religion, health, sexuality, finance and ethnicity, as inferences. Health is
never in the pack at all, measured or not. Finance appears only as a figure the person already
sees on the Resources bar (runway, queue), and only if the question is about money. The reading
never diagnoses, never names a prognosis, never tells the person to buy, sell, sign or stop a
treatment. These are refusals in the composer with tests, not a line in a prompt.

Third parties: a relationship line may name a person the sheet already names to the person
(q377: names show to you only). The reading never characterises a third party beyond what the
sheet already holds, and readings are never shareable from the product.

## How a reading is made

```
question + method
  -> draw (secrets; recorded)
  -> context pack (brain reads; trust order above; refused kinds stripped; every item listed)
  -> free rendering (template text from the tables: always produced, costs nothing)
  -> composed rendering (optional): one model call through the LLM gateway,
       feature tag oracle.reading, spend metered, price shown first,
       model = ORACLE_MODEL (unset = OFF, like COMMAND_ASK_MODEL),
       local model first; cloud is a separate, named decision, never a fallback
  -> reading document saved (draw, pack listing, both renderings, price paid)
  -> optional: "make it a quest" -> a quest proposal (inward only)
```

The free rendering means the fortune teller works with the model switched off: she lays the cards
and gives the table meanings, and the person can still read them. The composed rendering is the
one that "knows you". The owner wants all model work local eventually ("eventually all the llm
processing will come from the local system", 2026-10-12); the composer is written so the model is
a configured name and nothing else changes.

The composer's prompt holds the draw, the pack, the method's rules and the teller's voice. It asks
for: what the draw says, how it meets the person's actual situation (citing pack items by label),
one thing to do or watch this week, and a closing line. Under five hundred words. It must not
invent facts about the person; a test feeds it a pack and checks every claimed fact traces to a
pack item.

## What it writes, and where

- **Readings** are documents: one per reading, in the Briefcase/document store under the person,
  kind `oracle.reading`, holding the draw, the pack listing (labels and ids, not raw excerpts),
  the free text, the composed text, the model name, the price, and the journal marks. They are
  never embedded into the Self: a reading is not evidence about the person.
- **Quests** proposed from a reading go to the quest log as `source = oracle` with the reading id,
  reward stated in capability terms, and no outward action attached.
- **Nothing else.** No claim is written to the Self by the teller. No outcome is recorded by the
  teller. "This landed" is a mark on the reading, not a score.

## Frame and consent

- The screen carries one plain line, once per person and then in the room's footer: "For
  reflection and play. Not advice." COUNSEL puts the matching sentence in the user terms (L1).
- The product never says "predict" in its own voice; the teller may, because she is a character.
  The owner's brief says predict; the terms say reflection. Both are true in their register.
- A composed reading is a metered step: inference consent and the cost ceiling apply (S3), the
  price is shown first, and the game's rule holds ("a quest that costs money shows the price").
- Minors: never, as everywhere in the product.

## Where it lives in the system

Three lanes, three pieces:

- **INTELLIGENCE** builds the faculty: draws, tables, the context pack with its refusals, the
  composer, the reading document, the quest proposal. Working name `oracle/` in the hub, beside
  the numerology and astrology modules.
- **SURFACE** builds the place: the pane line and the landmark, the room with its three states
  and the journal, reading from the hub through one route family (`/api/command/oracle/*`) and
  writing only decisions (draw, save, mark, make-a-quest).
- **DOORS** owns the model call: the gateway feature tag, the spend meter, the flag, the
  local-first choice, and the review that the room has no outward path and no fallback.

DESIGN owns the teller's look and the deck; COUNSEL and PRIVACY own the line and the data rules.

## Tests that must exist

- The draw uses `secrets`, never `random`; a draw is recorded before any composition; the recorded
  draw reproduces the displayed cards.
- With `ORACLE_MODEL` unset no model call is made for any method, and the free rendering is complete.
- The context pack never contains an item of the six refused kinds, for every method and for
  questions that ask for them directly ("will I get sick", "should I vote for"); health is absent
  even when Apple Health is connected.
- Every fact the composed text asserts about the person traces to a pack item (a mocked model
  returning an invented fact must be caught).
- Inferred items are labelled inferred in the pack listing and in the panel.
- A reading document is written once per reading and is never embedded into the Self.
- A quest made from a reading carries no outward action and shows `source = oracle`.
- Nothing in the room's routes or the faculty opens a connection to any host but the gateway.

## Open choices (defaults chosen here; owner cards where marked)

1. **Model and spend** (card): which local model composes readings, and the per-reading ceiling.
   Default: no composed readings until named; free readings work from day one.
2. **Deck art** (card): the public-domain 1909 deck now, a commissioned deck in the game's style
   later through the Studio. Default: yes to both, in that order.
3. **Money questions** (card): may the teller speak to a money question using the runway figure
   the person already sees. Default: yes, only when asked, never from inferred finance claims.
4. Reversed cards on by default; a switch to turn them off. No card.
5. Text-only teller in v1; a local voice later. No card.
6. The daily card in the morning plan, on by default, free. No card.
