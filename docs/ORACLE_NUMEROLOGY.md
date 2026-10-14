# Numerology: the person's numbers, computed from what they state

Part of the oracle set: [ORACLE_PLAN.md](ORACLE_PLAN.md) (overview, principles, tasks),
[ORACLE_ASTROLOGY.md](ORACLE_ASTROLOGY.md), [ORACLE_FORTUNE_TELLER.md](ORACLE_FORTUNE_TELLER.md).
Written 2026-10-12 by DESIGN · one-interface part · 4 on the owner's direct request. Proposal, not built.

## What it is in one line

A deterministic engine that turns two stated facts (full birth name, date of birth) into the
person's numerology profile, shows every number with the arithmetic that produced it, feeds a
"Numbers" family on the character sheet, and adds one free line a day to the morning plan.
No model call is needed for any number. A model is used only for an optional written reading,
and that goes through the fortune teller (see ORACLE_FORTUNE_TELLER.md).

## Inputs, and where they come from

| Input | Needed for | Source rule |
| --- | --- | --- |
| Date of birth | Life Path, Birthday, Personal Year/Month/Day, Maturity | Stated by the person on the character sheet. Never inferred from mail or calendar. A birthday seen in the corpus may raise a gap quest ("is 14 July your birthday?") but the number is computed only from the stated value. |
| Full name at birth | Expression, Inner Self, Personality, Maturity | Stated by the person. The name in mail signatures is the *used* name, not the birth name; it produces the "minor" set only, labelled as such. |
| Name used today | Minor Expression, Minor Inner Self, Minor Personality | Stated, or confirmed from the signature evidence the sheet already shows. |

Both inputs are person statements in the Self (top tier, like every explicit statement in S3):
confirmed by the person, confidence 1.0, never written by a distillation pass. They sit beside
the birth time and place that astrology needs (ORACLE_ASTROLOGY.md), so the sheet asks for all
four in one gap quest: "Tell me when and where you were born and your numbers and your chart
unlock." The reward is named in capability terms, as the game rules require.

## The system: Pythagorean, with the choices written down

Numerology has several schools and several ways to reduce a date. The engine implements one
set of rules and records which, so two people never get different numbers from the same inputs.

**Letter values (Pythagorean)**

| 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| A J S | B K T | C L U | D M V | E N W | F O X | G P Y | H Q Z | I R |

**Reduction.** A number reduces by summing its digits until one digit remains, except that
11, 22 and 33 are kept as master numbers wherever they appear as a component or a result.
The lesson number numbers 13, 14, 16 and 19 are noted when they appear *before* a reduction
and then reduced normally.

**Vowels.** A, E, I, O, U are vowels. Y is a vowel when the syllable has no other vowel
(Lynn, Yvonne); otherwise a consonant. W is always a consonant. The engine applies the rule
mechanically and shows the person which letters it counted as vowels, so a wrong call is one
tap to correct (a correction is a confirmed claim and outranks the rule).

**Names.** Letters only; accents are folded to their base letter; hyphens, apostrophes and
spaces are dropped; suffixes such as Jr are excluded unless on the birth certificate as stated.

### The core numbers

| Number | Formula | Reads as (one line for the sheet) |
| --- | --- | --- |
| Life Path | reduce(month) + reduce(day) + reduce(year), then reduce; master numbers kept at each step | The road: the lesson of the life as a whole |
| Birthday | the day of the month, reduced (11 and 22 kept) | A gift carried from the start |
| Expression (Destiny) | sum of all letters of the birth name, reduced | What the person is equipped to do |
| Inner Self | sum of the vowels of the birth name, reduced | What the person wants underneath |
| Personality | sum of the consonants of the birth name, reduced | How the person comes across before they speak |
| Maturity | Life Path + Expression, reduced | What the second half of life turns toward |
| Personal Year | reduce(month of birth) + reduce(day of birth) + reduce(current year), reduced | The theme of this year, from birthday to birthday |
| Personal Month | Personal Year + current month, reduced | This month's theme |
| Personal Day | Personal Month + current day, reduced | Today's theme (the morning line) |

Second tier, worth adding once the core set is on the sheet: the four Challenge numbers and the
four Pinnacles (life periods with their own number), the Hidden Passion (the most frequent letter
value in the name), the Karmic Lessons (rename before building: contains a refused word) (values absent from the name), and the Chaldean variant as
an alternative the person can switch on. None of these need new inputs.

### A worked example, which is also the first test

Date of birth 14 July 1990. Month 7 gives 7. Day 14 gives 1 + 4 = 5. Year 1990 gives 1 + 9 + 9 + 0 = 19, then 1 + 9 = 10, then 1.
Life Path = 7 + 5 + 1 = 13 (lesson number 13 noted), then 1 + 3 = **4**.
Birthday = 14 gives **5**. Personal Year for 2026 = 7 + 5 + reduce(2026) where 2026 gives 10 then 1, so 13 then **4**.

Name "Ann Lee": A1 N5 N5 L3 E5 E5 = 24 gives **6** Expression. Vowels A1 E5 E5 = 11 gives **11**
Inner Self (master number kept). Consonants N5 N5 L3 = 13 (lesson number 13) gives **4** Personality.

Every number on the sheet shows this arithmetic when tapped. That is its evidence, in the sense
the Evidenced Self uses the word: the person can see exactly why the system says 4.

## Where it lives in the system

By the ratified test in the desks README, numerology **produces a model from data** and is
therefore a **faculty of the brain**, not a sensor and not an arm. It is INTELLIGENCE's lane.

- **Module.** One pure module in the hub (working name `oracle/numerology.py`): `profile(name, dob)`
  returns a dict of numbers, each with its formula string and components; `today(dob, date)`
  returns Personal Year, Month and Day. Stdlib only. No model call. No network.
- **Persistence.** Nothing new to store. The profile is recomputed from the two statements on
  every read; it is cheap and it can never drift from its inputs. The daily numbers are computed
  at render time.
- **Character sheet.** A new family "Numbers" on the sheet (the q377 pattern: new families are
  added and marked NEW). Each line is a number with its one-line reading and its arithmetic as
  evidence. State: these lines are **DERIVED**, not INFERRED: the input is confirmed by the
  person and the formula is fixed, so there is nothing to confirm; "hide" still applies.
- **Morning line.** One line in the day plan / morning briefing, free, template text from a
  nine-entry table: "Personal day 7: a day for study and quiet work." Numerology also gives the
  fortune teller its first stock-in-trade.
- **MCP tool.** `my_numbers` (read-only) so the connector and the suite read the same profile.
- **Customers.** Works at level 1 with no corpus at all: two typed facts and the sheet fills a
  family. That makes it a cheap early payoff.

## Rules this must keep

- The number is never computed from an inferred date of birth. Absent a statement, the family
  shows its gap quest and nothing else. An empty state and a broken state must not look the same
  (DESIGN's rule): "not told yet" is a different line from "could not compute".
- Date of birth and birth name are personal data. They are excluded from every outward surface
  and from the likeness license projection (S3, P2). They never appear in a URL. The derived
  numbers are not secret but travel with the same rule, because a Life Path plus a public name
  narrows a birthday.
- No badge, streak or score attaches to any of this (the game's exclusions).
- Nothing here spends and nothing here transmits (Law 9 has nothing to gate in this document).

## Tests that must exist

- The worked example above, digit by digit, including the lesson number note and the master number.
- Master numbers survive each reduction step they appear in (11 November 2011 keeps 11 twice).
- Y handling: "Lynn" counts Y as a vowel; "Yolanda" counts it as a consonant.
- Accent folding and punctuation stripping (a name such as O'Brien-Núñez).
- Personal Day rolls correctly across a year boundary and across the person's birthday.
- A profile request with no stated date of birth returns the gap, not a number and not an error.
- A property test: the module imports nothing that can reach the network.

## Open choices (defaults chosen here; the owner can change any by card)

1. Reduce the date by components (chosen) rather than by summing all eight digits. The two
   methods differ only in when master numbers appear; the component method is the common one.
2. Y rule as above (chosen) rather than "Y is always a vowel". The person can correct per letter.
3. Pythagorean first; Chaldean as a later switch.
