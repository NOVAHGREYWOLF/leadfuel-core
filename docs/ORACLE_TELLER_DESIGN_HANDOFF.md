# The teller, the room and the deck: design hand-off for the room desk

**Proposal, not built.** Written 2026-10-14 (UTC) by DESIGN for task `ORACLE-TELLER-AND-DECK`
(step 8 of [ORACLE_PLAN.md](ORACLE_PLAN.md)), for the desk that builds step 7,
`SURFACE · ORACLE-FORTUNE-TELLER-ROOM`. It turns the "The teller" and "Deck art" sections of
[ORACLE_FORTUNE_TELLER.md](ORACLE_FORTUNE_TELLER.md) into things you can build from. The wording of
the footer line is COUNSEL's draft in [ORACLE_TERMS_LINE.md](ORACLE_TERMS_LINE.md) and is not agreed.

The live mock is a private Artifact (id `BBFNSKRJdwNGFApvzBthzL`, project one-interface). It shows the
room's states, the three draws and the deck stages working with example data. Read it with the
Artifact tool; it is the visual source and this file is the text source. If they disagree, this
file wins and the page is stale.

**Nothing here spends or sends.** No Studio generation was run (spend is not authorised). The face
and the deck are briefs. This file carries ids and design text only: no personal data, no birth
data, no real reading.

## Defaults taken, not owner answers

- **Deck art** (pending owner card): the card is unanswered. Its stated default is yes to both, in
  order: the public-domain 1909 deck now (stage A), a commissioned deck in the game's style later
  through the Studio under the owner's spend ceiling (stage B). This hand-off designs to that
  default. If the owner answers differently, section 6 changes and the rest stands.
- **The teller's name** is the owner's pick. Three candidates are below. Build with the name read
  from one config value; use `Wren` as the working default until the owner picks.

## 1. Tokens

The room is a life-side surface inside the Command screen. The frame (bar, resource strip) keeps the
ops-room cyan; the room inside uses the Novah personal skin's indigo on the same near-black ground.
Values come from `tokens-command.css` (frame) and `tokens-novah.css` (interior) in the hub; use the
hub's variables, not these hex values, where the variable exists.

| Role | Frame (ops room) | Interior (life side) |
| --- | --- | --- |
| Ground | `#04080d` | `#07070d`, panels `#0d0d16`, raised `#141420` |
| Line | `#14303f`, strong `#1f4b61` | `#262633`, strong `#34345f` |
| Accent | `#4fd6ff` (selected, current) | `#6366F1`, text on dark `#b9b6ff`, hover `#8b5cf6` |
| Text | `#dbe9f2` | `#ECECF1`, soft `#c9c9d8`, muted `#9a9aae` |
| Warning / placeholder | `#ffb457` | `#fbbf24` |
| Done | `#5ef2c0` | `#34d399` |

Type: Barlow Condensed (display, uppercase), Barlow (body; the teller's lines in Barlow italic,
indigo text), JetBrains Mono (labels, stamps, state words). Panels are square with a thin line and
indigo corner brackets at top left and bottom right. Pips are hexagons and travel with a word.
Unknown or not generated is hollow, dashed or hatched, never a plain fill.

## 2. The teller

A separate NPC, not the player's character. She is reached from the pane line, the world landmark
or the phone tab. She sees the person only through the context pack for that reading, and
remembers only what the journal holds.

### Voice rules

1. Second person, present tense.
2. Names the card, line or rune first, then what it might mean for this person.
3. Brief: under 120 words on screen by default; the composer's cap stays at 500.
4. Warm and specific: cites one real item from the pack by its label; no general praise.
5. Says what she does not know, in her own line, whenever it changes the reading.
6. Marks inference: "The cards suggest it, and your records hint at it. You have not said it is so."
7. Refuses the six kinds in character (the refusal itself is code in the composer, with tests).
8. She may use "predict" and "your future" because she is a character. The product's own copy
   (menus, buttons, footer, notifications, help) does not, per the COUNSEL draft.
9. Text only in v1. A voice later must run on the node.

### Example lines (starting point, text only)

| Moment | Line |
| --- | --- |
| Greeting, nothing stated | Sit down. I do not know much about you yet, and I will say so when it matters. Ask something, or take the card of the day. |
| Greeting, numbers stated | Your personal day is 7 and the Moon is in your sign. A quiet day to ask a real question. You have not told me where you were born, so I cannot see your rising sign. (7 is an example number.) |
| Before the words | It is drawn. Look first. I will talk when you are ready. |
| Something missing | I cannot read the chart without a time of birth. Tell me, or ask me something the cards can answer. |
| An inferred item | Your records hint that this matters to you. You have not said so, so I am holding it loosely. |
| A health question | That is not mine to read, and I do not look at your health. A doctor can. Ask me about your week and I will. |
| A money question (pending card) | I can only use the runway figure you already see. I will not guess beyond it. |
| After "this landed" | Noted. It stays in the journal as you drew it. It is not a score. |
| Leaving | Come back when it has happened, or when it has not. I will lay it out as it was. |

### Three names (the owner picks)

| Name | Reads as | Risk | |
| --- | --- | --- | --- |
| **Wren** | A small bird at the edge of a clearing. Plain, quiet, short to type. | Common word and surname; least distinctive to search for. | Design recommendation |
| **Verity** | Means truth. Warm, a little formal. | Claims what the product is careful not to claim; a reading is a document, not a claim. | |
| **Tamsin** | A human first name with an old-country sound. | Warmest, so the most likely to read as a real person; needs the "she is a character" line most. | |

Collision check done: none is a ratified arm name; a text search of the estate's `.md` and `.py`
files found no product or desk with these names. The hub code was not searched.

### The face

A hexagon portrait (points 25% 3%, 75% 3%, 100% 50%, 75% 97%, 25% 97%, 0 50%) with a thin indigo
outline. A placeholder ships: a plain head-and-shoulders silhouette, hatched fill, labelled
"face placeholder". The Studio set drops in by file name: `teller/<name>-<expression>.png`, name in
lower case, expressions `listening`, `speaking`, `drawing`, `unsure`, `closing`; 1024, 256 and 64
px, PNG, transparent outside the hexagon. Show `speaking` while text is on screen, `drawing`
during a draw, `unsure` on any "not told yet" line, `listening` otherwise.

**Studio brief (not submitted):**

```
SUBJECT  Bust portrait of the teller, an NPC in a game. An adult, age not fixed. Reads as
         someone you would trust at a counter: calm, attentive eyes, a slight half-smile,
         hands not shown. Female, following the source document's "she". Not a real person.
AVOID    No headscarf with coins, no turban, no crystal ball, no heavy eye makeup, no
         stage-gypsy costume, no mystic symbols on clothing. No ethnicity signalled by
         costume. No text, logo or watermark.
DRESS    Dark layered collar, one indigo accent (#6366F1). Plain.
LIGHT    One low lamp from lower left, warm. Indigo rim light from upper right.
STYLE    The game's own: flat shading with a thin line, dark ground, hexagon crop with a thin
         indigo outline. Nothing photographic.
SET      Five images of one face and dress: listening, speaking, drawing, unsure, closing.
         Same seed or reference for all five.
ORDER    Only after the owner has picked the name. Nothing in the image names her.
PRICE    Unknown. Read the Studio's quote and show it before any call. A generation is a spend
         and needs the owner's ceiling (Law 9).
```

## 3. The room: three states and the journal

One screen, four tabs (a tab bar on the phone). A footer line on every state:
"For reflection and play. Not advice." (COUNSEL draft wording, not agreed.)

1. **Table.** The teller's greeting. Methods as objects on a table: deck (cards), three coins
   (I Ching), rune bag, chart wheel, numbers board. An object whose inputs are missing is dashed and
   says what it needs ("Not told yet. Needs your date, time and place of birth."). Tapping it makes
   the teller say the missing-data line; it does not start anything. An optional question box
   (required for Celtic Cross, yes or no, I Ching: "This one needs a question."). A price line
   before any touch: free table text; a composed reading shows its price first; with `ORACLE_MODEL`
   unset it reads "Composed reading: model not named, so it is off."
2. **Draw.** The draw is recorded and stamped, then moves, and the result is on screen before any
   word. The stamp reads `DRAW <id> RECORDED · <cards/lines/runes> · <time UTC>`. Two buttons:
   draw again and "Read it". "Read it" is enabled only when the motion has finished.
3. **Reading.** The draw as chips at the top. The words (composed if on, else the free text; the
   free text is always one tap away). The panel "What she drew on": one row per pack item with its
   kind (`Stated`, `Measured`, `Inferred` dashed, `Question`) and one row `Not used` that names what
   she did not have and says health is never used. Three buttons: This landed, This did not, Make it
   a quest. A mark is a note on the reading, not a score. A quest goes to the queue with
   `source = oracle`, no outward action, and runs only when the person accepts it.
4. **Journal.** Every past reading by date and method, collapsed to one row with its mark. Opened,
   it shows the draw exactly as recorded, the price paid and the rendering used. Empty: "No readings
   yet. Take the card of the day; it needs nothing."

Other states, worded: birth date without time ("No time of birth: I can read your sun and moon, not
your rising sign."); refused kind asked (the refusal line, then what she can read; no pack is
built); oracle off for the account (no landmark, no pane line, no tab, not a disabled version).

## 4. Motion

The idle room is still. Nothing loops, nothing sparkles, no confetti. Motion shows an order of events.

| Motion | Time | Easing | What it means |
| --- | --- | --- | --- |
| Draw stamp appears | 160 ms fade | linear | The draw is recorded before any motion or words. |
| Card deal | 220 ms each, 120 ms apart | ease-out | Cards leave the deck for their places, face down. Position is meaning. |
| Card turn | 600 ms (rotateY), 450 ms between | ease-out | Attention paced one card at a time. A reversed card turns up rotated 180 degrees and says "Reversed". |
| Coin throw | 650 ms, 350 ms between, six throws | ease-out | A real roll per throw. The line is added after the coins land. |
| Line added | 160 ms fade | linear | The hexagram builds from the bottom, as it is read. |
| Rune pull | 380 ms rise, 500 ms glyph stroke | ease-out | The stone comes out blank; the glyph is drawn on as if carved. |
| Tab change | 120 ms fade | linear | A state change, nothing more. |
| Reading text | none | none | Appears whole. No typing effect: it is already written. |
| Marks, save | none | none | A note, not an event. No burst, no badge. |

Reduced motion: all durations to zero, same order (stamp, then result, then "Read it"). Nothing is
conveyed by motion or colour alone: reversed is a word, changing lines carry a mark (`o` for old
yang, `x` for old yin), runes carry their names, inferred is dashed and says so.

Coin outcome: each coin is 3 (heads) or 2 (tails); a throw sums to 6, 7, 8 or 9. 6 is old yin
(broken, changing), 7 young yang (solid), 8 young yin (broken), 9 old yang (solid, changing). The
second hexagram flips the changing lines. The draw is made server-side with `secrets` and recorded
before the animation starts; the animation shows the record and never decides it.

## 5. Method objects drawn in code (free, no Studio)

Coins, hexagram lines, runes, the chart wheel and the numbers board are small SVG shapes. The mock
page has the working versions. The rune glyphs, in a 24 by 40 box, stroke only (round caps and
joins, stroke width about 2.4 at 30 by 48 px), in Elder Futhark order. These are approximate
strokes made for the mock; a designer can redraw them without changing the data shape.

```json
[
 ["Fehu","M12 4V36M12 14L22 6M12 24L22 16"],
 ["Uruz","M6 36V4L18 14V36"],
 ["Thurisaz","M8 4V36M8 12L20 20L8 28"],
 ["Ansuz","M8 4V36M8 4L20 14M8 14L20 24"],
 ["Raidho","M8 4V36M8 4L20 12L8 20L20 36"],
 ["Kenaz","M18 8L8 20L18 32"],
 ["Gebo","M6 8L18 32M18 8L6 32"],
 ["Wunjo","M8 4V36M8 4L20 12L8 20"],
 ["Hagalaz","M6 4V36M18 4V36M6 14L18 26"],
 ["Nauthiz","M12 4V36M6 16L18 24"],
 ["Isa","M12 4V36"],
 ["Jera","M9 6L5 12L9 18M15 22L19 28L15 34"],
 ["Eihwaz","M12 4V36M12 4L18 10M12 36L6 30"],
 ["Perthro","M6 4V36M6 4L18 12V28L6 36"],
 ["Algiz","M12 4V36M12 20L4 8M12 20L20 8"],
 ["Sowilo","M16 4L8 14L16 26L8 36"],
 ["Tiwaz","M12 4V36M12 4L5 14M12 4L19 14"],
 ["Berkano","M7 4V36M7 4L18 12L7 20L18 28L7 36"],
 ["Ehwaz","M5 36V4L12 14L19 4V36"],
 ["Mannaz","M6 4V36M18 4V36M6 4L18 20M18 4L6 20"],
 ["Laguz","M8 4V36M8 4L18 14"],
 ["Ingwaz","M12 6L20 20L12 34L4 20Z"],
 ["Dagaz","M5 6L19 34V6L5 34Z"],
 ["Othala","M12 4L20 14L12 22L4 14ZM12 22L6 36M12 22L18 36"]
]
```

## 6. The deck

Card art is a data file. Reading text is keyed by card id, so swapping the deck changes pictures,
never readings. Proposed shape:

```json
{ "deck": "rws-1909", "stage": "stand-in", "source_url": "recorded by the room desk",
  "back": "decks/rws-1909/back.webp",
  "cards": [ { "id": 0, "name": "The Fool", "image": "decks/rws-1909/00.webp", "alt": "The Fool" } ] }
```

Ids: 0 to 21 major arcana in the usual order (Strength 8, Justice 11); 22 to 35 Wands, 36 to 49
Cups, 50 to 63 Swords, 64 to 77 Pentacles, each Ace to Ten then Page, Knight, Queen, King.

**Stage A, now (default taken).** The 1909 Pamela Colman Smith deck, 78 scans. The source document
states it is public domain in the United States; this desk did not verify that independently.
Before bundling, the room desk picks a scan, records its source and terms of use in the deck file
(a library or museum can attach conditions to its file even when the painting is old), and checks
them. Shown unaltered in a game frame; never recoloured. Reversed is the image rotated 180 degrees
with the word "Reversed" beside it. Image size is unmeasured; plan on one 600 px wide WebP per card.
Cost: none.

**Stage B, later (default taken; no spend authorised).** A deck in the game's style through the
Studio, under a spend ceiling the owner has not set. Three tranches, each priced before it is made
and approved before the next: the back plus the 22 major cards; the 16 court cards; the 40 number
cards. The deck switches as a whole, only when all 78 are approved. Same symbols as the 1909 deck
so the meaning tables stay valid, drawn fresh: flat shapes, thin lines, dark ground, hexagon motif,
indigo as the single accent. Master 1050 by 1800 px (7:12), exports 525 by 900 and 263 by 450. The
Studio's price is unknown.

## 7. Checks the room should pass

- The recorded draw is on screen before any word of the reading, in all three motions and in
  reduced motion.
- With `ORACLE_MODEL` unset the room is complete: free text, no model call, price line reads "off".
- Nothing is carried by colour or motion alone.
- Works at 400 px wide: the teller card stacks above the table, objects wrap, no sideways scroll.
- Every control is at least 44 px high and has a visible focus ring.
- No outward link, share button, badge, streak or score. No `predict` in the product's own copy.

## 8. Open choices that remain the owner's

1. The teller's name (three candidates above).
2. Deck art card (pending): defaults taken as above; stage B needs a spend ceiling before anything
   is generated.
3. Face: the Studio brief is ready; generation waits for the name and for a ceiling.
4. Composed readings: which local model, and the per-reading ceiling (ORACLE_PLAN decision 2).

## What this desk verified, and what it took on trust

Read by DESIGN: the task text; `ORACLE_FORTUNE_TELLER.md`, `ORACLE_PLAN.md` and
`ORACLE_TERMS_LINE.md` on main at `7014970`; the existing character-pane mock for the frame tokens;
the personal skin token file for the indigo values; the page was syntax-checked and its draw logic
reviewed but its animation was not watched running (the preview pane showed a static snapshot).

Taken on trust: that the 1909 deck is public domain in the United States (source document); that
the Deck art card is still unanswered (task text); that the Studio takes the brief as written (its
interface was not read); that the pane line, landmark and phone tab exist as ORACLE_FORTUNE_TELLER.md
describes. Not done: no Studio call, no image, no spend, nothing sent anywhere.
