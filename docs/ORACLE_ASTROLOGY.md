# Astrology: the natal chart and today's sky, computed from what they state

Part of the oracle set: [ORACLE_PLAN.md](ORACLE_PLAN.md) (overview, principles, tasks),
[ORACLE_NUMEROLOGY.md](ORACLE_NUMEROLOGY.md), [ORACLE_FORTUNE_TELLER.md](ORACLE_FORTUNE_TELLER.md).
Written 2026-10-12 by DESIGN · one-interface part · 4 on the owner's direct request. Proposal, not built.

## What it is in one line

An ephemeris-backed engine that turns three stated facts (date, time and place of birth) into a
natal chart, computes the current sky against it every day (transits), feeds a "Sky" family on
the character sheet, and adds one free line a day to the morning plan. Positions are astronomy
and are computed locally with no model and no network. Interpretation is a separate, optional
step that goes through the fortune teller (ORACLE_FORTUNE_TELLER.md).

## Inputs, and where they come from

| Input | Needed for | Without it |
| --- | --- | --- |
| Date of birth | Everything | Nothing can be computed; the family shows its gap quest |
| Time of birth (local clock time) | Ascendant, Midheaven, houses, an exact Moon sign | A **degraded chart**: Sun and planets are exact, the Moon is shown as a range (it moves about 13 degrees a day and can change sign), no rising sign and no houses. The sheet says so in words, not with a grey box. |
| Place of birth (a town; the engine resolves latitude, longitude and the time zone in force on that date) | Ascendant, Midheaven, houses, converting the clock time to universal time | Same degradation as a missing time |

All three are person statements in the Self (top tier, S3): typed by the person on the
character sheet, never inferred. They share one gap quest with the numerology inputs. The place
is resolved to coordinates once, from a gazetteer shipped with the node (no lookup call at
runtime); the person confirms the resolved town. Historical daylight saving matters: the tz
database carries it, and the engine records which rule it applied.

## What is computed

**Natal chart (once per statement, recomputed when a statement changes).**

- Positions: Sun, Moon, Mercury, Venus, Mars, Jupiter, Saturn, Uranus, Neptune, Pluto; the lunar
  nodes; Chiron as an option. Tropical zodiac by default; sidereal (Lahiri) as a switch for people
  who use the Vedic system.
- Angles: Ascendant (rising sign) and Midheaven, when time and place are known.
- Houses: Whole Sign as the default (the oldest system and the simplest to get right); Placidus
  as a switch, because most Western readers expect it.
- Aspects between planets and to the angles: conjunction, sextile, square, trine, opposition, with
  orbs by planet class (wider for the Sun and Moon). Each aspect is recorded with its exact orb.
- Derived summaries the sheet can show in a line: the big three (Sun, Moon, rising), element and
  modality balance, chart ruler, retrograde planets at birth, the dominant planet by a stated
  weighting.
- Chinese zodiac animal and element for the birth year, from a table of lunar new year dates.
  Cheap, popular, and a second source of material for the teller.

**Transits (daily, at render time).**

- Today's positions for the same bodies, the Moon's sign and phase, planets currently retrograde.
- Transiting aspects to the natal chart within a tight orb, ranked: outer planets to the natal
  luminaries and angles first (these are the slow "seasons"), then the rest.
- The coming week's exact aspects, so the teller can speak about what is building.
- Solar return (the birthday chart) once a year; the morning plan notes the day.

**One free line a day** in the day plan / morning briefing, template text, no model:
"Moon in Taurus, waxing. Transiting Jupiter trine your natal Sun this week." Like the numerology
line, it costs nothing and sends nothing.

## Accuracy, and the library decision (needs the owner)

Planet positions need an ephemeris. Two credible routes:

| Route | Licence | Accuracy | Notes |
| --- | --- | --- | --- |
| **skyfield** (Python, MIT) with a JPL ephemeris file such as DE421 (public domain data, about 17 MB) | MIT; data is public domain | Arcsecond-level for every body here; more than any reading needs | Houses and angles are not in the library; we write them (Whole Sign is trivial; Placidus is a short iterative formula). The ephemeris file is vendored into the node image so the engine never fetches at runtime. Chiron needs a separate small-body file or is left out of v1. |
| **Swiss Ephemeris** (pyswisseph) | AGPL-3.0, or a paid professional licence from Astrodienst for closed-source use | The astrology standard; houses, nodes, Chiron and fixed stars built in | AGPL does not fit a closed commercial product; the paid licence is a spend and a vendor relationship. |

**Recommendation: skyfield + DE421, houses in our own code.** No licence question, no spend,
no runtime egress. The cost is writing about two hundred lines of well-known astronomy (sidereal
time, obliquity, Ascendant and Midheaven, Placidus cusps) and testing them against published
charts. This is a card for the owner because the alternative is a spend (Law 9) and because a
reader who insists on Swiss Ephemeris parity should say so before the build.

**Verification anchors for the tests.**

- J2000.0 (2000-01-01 12:00 TT at Greenwich): the Sun's apparent ecliptic longitude is close to
  280.4 degrees (10 degrees Capricorn). The engine must reproduce this to within a tenth of a degree.
- A set of published charts with known Ascendant and Midheaven (public figures with recorded
  birth times, or synthetic cases computed by two independent tools) as fixtures: every angle
  within a tenth of a degree, every house cusp within a quarter of a degree for Placidus.
- Daylight saving: a birth at 02:30 on a spring-forward night must be refused with a clear
  message (the time did not exist), not silently shifted.
- Southern hemisphere and high latitudes: Placidus fails above the polar circles; the engine falls
  back to Whole Sign there and says so.

## Where it lives in the system

Astrology **produces a model from data**, so by the ratified test it is a **faculty of the brain**
(INTELLIGENCE), not a sensor. The sky is not measured by us; it is computed.

- **Module.** `oracle/astrology.py` (working name): `natal(dob, time, place)` returns the chart as
  JSON (positions, angles, houses, aspects, summaries, the settings used, and a `degraded` list
  naming what could not be computed and why); `transits(chart, when)` returns the day's sky and
  the ranked contacts; `daily_line(chart, when)` returns the free sentence. Pure functions over the
  ephemeris; no network; no model.
- **Persistence.** The natal chart is derived data, regenerable from the three statements. Cache
  it per person with the hash of its inputs and settings; drop the cache when a statement changes.
  Transits are computed at render time and cached for the day.
- **Character sheet.** A new family "Sky" on the sheet (NEW, per q377): the big three on the pane
  line, the chart behind a tap (a wheel drawn from the JSON, no image service), each line DERIVED
  with its computation as evidence; the degraded notice as its own line when time or place is missing.
- **MCP tool.** `my_chart` (read-only) and `sky_today` (read-only).
- **Customers.** Three typed facts and the sheet fills a family. Level 1 payoff, like the numbers.

## Rules this must keep

- Birth time and place are personal data of the identifying kind (date plus place narrows a
  person to a handful). Top-tier statements; excluded from every outward surface and from the
  likeness license projection (S3, P2); never in a URL; never in a log line. The chart JSON travels
  under the same rule, because a chart with an exact Ascendant encodes the birth time.
- Nothing fetches at runtime: ephemeris, gazetteer and tz data are shipped with the node. A
  cloud lookup for a place name would be a transmission and is not a fallback (Law 9; "a cloud
  path must be a decision, not a fallback").
- A missing time produces a degraded chart that says what is missing, never a chart that
  silently assumes noon. Assumed values are a lie in the Evidenced Self's terms.
- No health, finance, politics, religion, sexuality or ethnicity line is ever derived from a
  chart (q376: those six are never inferred). The sixth house is not a health panel.
- Interpretation text (what a placement "means") is a separate step with its own rules, in
  ORACLE_FORTUNE_TELLER.md. This engine ships keyword tables only.

## Tests that must exist

- The J2000 anchor and the published-chart fixtures above.
- The daylight-saving refusal and the polar fallback.
- Missing time and missing place each produce the right `degraded` entries and no angles.
- Tropical and sidereal differ by the Lahiri ayanamsa for the same instant.
- Aspect finding is symmetric and respects the orb table; an aspect at exactly the orb edge is
  included once.
- The free daily line never contains a word from the six refused kinds (a word-list test).
- A property test: the module imports nothing that can reach the network.

## Open choices (defaults chosen here; the owner can change any by card)

1. skyfield + DE421 with houses in our code (chosen) versus Swiss Ephemeris (paid licence).
2. Whole Sign default, Placidus as a switch (chosen).
3. Tropical default, sidereal as a switch (chosen).
4. Chiron and asteroids out of v1 (chosen).
