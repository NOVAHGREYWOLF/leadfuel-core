# World: public cameras, aircraft and ship tracks, places (design notes CC-58 and CC-59)

Two design notes for the one-interface command center's World layer. **No code. Nothing is
built from this document, no camera, no track client, no places switch.** Lane INTELLIGENCE,
project one-interface, part 120.

**Source.** The owner, Router desk cards answered 2026-10-30 evening Pacific, relayed by
ROUTER #110:
- **q809, answer B, CC-58:** "Design note only (sources, stills vs streams)". No cameras are built.
- **q810, answer A, CC-59:** "Yes, design notes only". No client is built.

**What nothing in this note does.** No live source was fetched, no vendor was called, no key
was requested and nothing left the machine while writing it. Every fact about a vendor below is
carried from an earlier read-only survey and is marked as such.

**Marks.**
- **[V]** I read it myself, in hub code on `origin/main` at `d45910fa` (2026-10-31), or on the
  Command Center Build page rows `tasks/cc58` and `tasks/cc59` (version 3 of each).
- **[T]** Taken on trust. Almost all vendor facts come from the World view open-source survey
  002 (2026-10-17, a read-only research agent for ROUTER #65, which marks each fact VERIFIED,
  SECONDARY or UNVERIFIED in its own terms), and the OpenWeb Ninja prices from the hub's
  `docs/OPENWEB_NINJA_BLUEPRINT.md` (last updated 2026-07-25). I did not re-check any of them,
  because re-checking would mean fetching a live page. Treat every [T] as a reason to read the
  vendor's current terms before any build, not as a finding.

---

## 0. Where the code stands today [V]

`world_layers.py` holds the World layers as data. The rows these notes are about:

| Layer | Line | `show_only` | Providers | Client | State it reads as today |
|---|---|---|---|---|---|
| `cameras` | 62-63 | True | none | none | `show` (drawn hollow, never in the brief), carries `REFUSAL` |
| `aircraft` | 71-72 | True | `opensky`, `adsbdb` | none | `show` |
| `ships` | 73-74 | True | none | none | `show` |
| `places` | 97-99 | **False** | `openweb` | `openweb_ninja_client` | `blocked` ("commercial use needs a written agreement"), wherever `OPENWEB_NINJA_AGREEMENT_SIGNED` is not set |

The `state_of()` order matters. A show-only layer returns `show` before the providers are even
consulted, so cameras, aircraft and ships read as `show` with no provider and no client. That is
honest about what they are (hollow, a demo) but it does not say "nothing is wired": the hollow
drawing has to carry that by itself. `places` is **not** show-only: it was designed to feed the
brief, and today it is held at `blocked` by the terms registry, not by a switch.

**The standing refusal is data, not a comment** [V]. `IDENTIFIES_PEOPLE = False`; `REFUSAL` reads
"No face recognition over public feeds. Public cameras may be shown; nobody is identified from
them."; `assert_refusals()` raises if the camera layer stops being show-only or loses the
refusal, and `tests/test_world_lane.py` (lines 83 and 98) pins it. The `plates` layer carries the
same idea: "where readers stand (OSM), never what they read".

**The transport every open feed shares** [V]. `world_http.py`: a switch that defaults off, a
cooldown after a 429, a result that keeps "could not look" apart from "looked and it was
quiet", and a guarded production GET (no redirects, a byte cap, one deadline for the whole
call). Its own header says the spend gate cannot see free providers, "so the brake is the
switch plus a cooldown, never a price". The hub's `vendor-egress-gate` check lists each feed
client's outbound verb, so a new client that is not registered there is a CI finding.

---

## CC-58: public cameras (CCTV)

### 1. The plain answer

Not the private and security CCTV people usually mean. Lists of exposed cameras are
unauthorised access and the app would be publishing the intrusion. What exists legitimately is
government traffic and weather cameras plus public webcam directories, and almost all of it is
**still frames** refreshed every few seconds to fifteen minutes, not video [T].

### 2. Still frames versus streams

| | Still frames | Streams (live video) |
|---|---|---|
| What it is | the latest JPEG a camera published, on a URL from an official list | a player embedded in the page (in practice YouTube Live; some aggregators' players) |
| Who calls the vendor | **our server**, once per view, through `world_http` | **the viewer's browser**, directly: their IP address and, for YouTube, their cookies go to the vendor |
| Law 9 shape | one outbound host per source, behind one switch we own | the same, **plus** a transmission from every viewer's machine that our egress check cannot see, because it happens in their browser |
| Storage | cache no longer than the source's own refresh; several terms say show, do not store [T] | YouTube's developer policies forbid downloading, caching or storing copies without written approval [T] |
| Temptation to analyse | low (one frame, minutes old) | high (a moving picture invites detection) |
| Cost | none from the free government programs [T] | none, but the viewer pays in data |

**Recommendation: stills only, if cameras are ever built.** Fetch the latest frame server-side
on view, cache it for no longer than the source's refresh, keep nothing after. No embedded
players; if a true-video window is ever wanted, click-to-load with a plain line saying the
video comes from the vendor and they will see the viewer's address.

### 3. The refusal, kept

Nothing in this note weakens it, and any future camera build inherits it as a done-criterion:
- No face recognition, no person identification, no re-identification across frames, over any
  public feed, whoever asks. (`IDENTIFIES_PEOPLE` stays False; `assert_refusals()` stays pinned.)
- No number-plate reading on any frame. The `plates` layer shows where readers stand, never what
  they read.
- No storage of frames beyond the refresh interval, and no frame enters the brain, the brief or
  an alert (show-only layers never do).
- No person, vehicle or crowd detection on frames either: a count of people is still analysis of
  people, and it is the first step toward the refused thing.
- Why it matters beyond principle [T]: under GDPR video of identifiable people is personal data
  and storing or analysing it makes the app a controller with duties; in the US the sharp edge
  is face geometry (Illinois BIPA). Not legal advice.
- The owner's **own** cameras are a different subject: enrolment only, and they belong to the
  local node, not to this lane [V, `world_layers.py` docstring].

### 4. Every fetch leaves the machine, so every source is its own Law 9 gate

A camera source is not "free" because it bills nothing. Each poll tells the far end that we
asked, from which address, and when. So, per source, before any build:
1. The owner approves that one source by name (a card), not "cameras" as a class.
2. A dated `world_terms` row records its licence and storage verdict, read off the vendor's
   current page.
3. Its client reads only through `world_http` with a switch that defaults off, and it is
   registered in the vendor egress check.
4. A key, where one is needed, is a credential decision of the owner's, separate from the source
   decision.
5. Embedding (a viewer's browser calling the vendor) is a separate, stronger approval, and this
   note recommends against it.

### 5. Per source: build or skip

The owner chose B: **nothing is built.** The column below is what this desk would recommend if
he reopens the question, so the answer is ready. Every fact is [T] from survey 002.

| Source | What it gives | Key | Licence (as reported) | Recommend | Why |
|---|---|---|---|---|---|
| **Singapore LTA traffic images** | expressway and checkpoint stills | none (optional key raises limits) | Singapore Open Data Licence, personal or commercial (marked VERIFIED in 002) | **build first, if reopened** | the cleanest licence and no key |
| **Finland Digitraffic weather cameras** | road-weather stills about every 10 minutes, 24 h history | none; a `Digitraffic-User` header is expected | CC BY 4.0 with a source line (SECONDARY) | **build, if reopened** | keyless, open licence, a good "window on the world"; confirm the licence on the current page first |
| **Hong Kong Transport Department snapshots** | stills every 2 minutes | none found | portal terms allow reuse with attribution; not for safety decisions (SECONDARY) | **build, if reopened** | open terms; read them first |
| **London TfL JamCams** | about 900 stills plus short clips | anonymous works lightly; key for higher limits | reported OGL-based with TfL amendments; the terms page could not be read (UNVERIFIED) | **skip until terms are read** | do not build on unread terms |
| **Caltrans CWWP2** | California CCTV, signs, weather | not stated | conditions page unread (UNVERIFIED) | skip until read | unread terms |
| **State and provincial 511 APIs** | a cameras endpoint per state | mostly a free developer key | per state, unread | skip | many keys, many unread terms |
| **WSDOT** | snapshots | access code from an email form | unread | skip | needs a sign-up with contact detail |
| **Windy Webcams API** | about 65,000 webcams, mostly stills, timelapse player | **required** | API terms: link and credit every image, no stated storage right, may end at any time; image tokens expire in 10 to 15 minutes | **skip now; later candidate** | a key (credential), commercial use unaddressed, and the expiring tokens force a call on every view |
| **YouTube Live embeds** | the only compliant true live video | none to embed | no caching or storing; embedded players collect viewer data | **skip** | a stream, not a still; transmits the viewer |
| **NYC DOT cameras** | live stills | no API found | no reuse terms; a data-sharing agreement may be needed | skip (link out at most) | no terms |
| **National Highways (England)** | camera images | n/a | non-commercial private study only | skip | the licence forbids product use |
| **FAA WeatherCams** | aviation weather stills | no API | none found | skip | no API, no terms |
| **EarthCam** | partner-only feeds | partner API | no rebroadcast without permission | skip | no scraping, no re-hosting |
| **OpenWebcamDB** | named by another project as a source | unknown | unverified | skip | unverified |
| **Exposed-camera lists, default-password cameras, consumer cameras (doorbells, baby monitors, dashcams)** | private cameras their owners never published | n/a | unauthorised access | **never** | refused outright, like face recognition |

### 6. Owner questions (CC-58)

Each has a default; the default stands unless he picks otherwise.

- **C58-1. Is the camera layer reopened for a build at any point?** A) No, the hollow layer and
  the refusal stay as they are. B) Yes, after the command center is operational, starting with
  the three open-licence still sources (Singapore, Digitraffic, Hong Kong). X) Something else.
  **Default A** (his q809 answer; nothing here feeds the command center).
- **C58-2. If a build is ever approved, stills only or video too?** A) Stills only, fetched by our
  server, cached no longer than the source refresh. B) Stills plus click-to-load video windows,
  each telling the viewer their address goes to the vendor. X) Something else. **Default A** (one
  egress path we own; nothing leaves a viewer's browser).
- **C58-3. Should the hollow camera layer say "nothing is wired" in words?** Today `state_of()`
  returns `show` for it with no provider. A) Yes, a show-only layer with no provider reads
  "show only, nothing wired", a SURFACE or INTELLIGENCE follow-up. B) No, the hollow drawing is
  enough. X) Something else. **Default A** (a layer that cannot show anything should not look like
  one that can).

---

## CC-59: aircraft and ship tracks, and OpenWeb Ninja places

### 7. What "show-only" means for tracks today [V]

`aircraft` and `ships` are in `SHOW_ONLY`: drawn hollow, never in the brief, never in an alert.
Neither has a client. `aircraft` names two providers whose terms already block storage in
`world_terms.py`:
- `opensky`: commercial **FORBIDDEN**, storage **LIVE_ONLY**; the row notes the licence is
  non-commercial and that operational REST use in a live product can need a prior written
  agreement even for non-profit use, and that "keyless and free" is exactly why it reads as
  unencumbered when it is not.
- `adsbdb` (aircraft and route enrichment): commercial **UNKNOWN**, storage **LIVE_ONLY**; no
  general licence, and route data may not be copied into other databases without permission.

`ships` names no provider. So "show-only today" is true for tracks in the strict sense: nothing
is drawn from a live source, and nothing could be stored if it were.

### 8. Per source: what it gives, licence, cost, and how it would stay show-only

The owner chose A: **design notes only, no client is built.** The "Recommend" column is the
ready answer if he reopens it. Vendor facts are [T] from survey 002 unless marked.

**Aircraft**

| Source | Gives | Licence (as reported) | Cost | Recommend | Why |
|---|---|---|---|---|---|
| **adsb.lol** | live ADS-B positions, ADS-B Exchange-compatible schema, yearly history dumps | **ODbL** (attribution, share-alike for derived databases); primary docs could not be read | free today; a future key earned by feeding a receiver | **the candidate, if reopened** | open licence; show-only and never stored keeps us clear of the share-alike database question |
| **OpenSky Network** | live state vectors; anonymous 400 credits a day (about 100 global snapshots) | non-commercial; `world_terms` already FORBIDDEN [V] | free; more needs an OAuth2 account (a credential) | **skip for the product** | non-commercial; at most an owner-only view under his own account, never shown to other users |
| **airplanes.live** | community ADS-B, 1 request a second | labelled non-commercial | free today; feeding may become required | skip (owner-only at most) | non-commercial |
| **adsbdb** | aircraft and route enrichment | no general licence; `world_terms` UNKNOWN [V] | free | skip | unknown terms fail closed |
| **ADS-B Exchange** | the largest unfiltered network | commercial use needs written authorisation | paid, sold through a marketplace | skip | a spend, and terms forbid product use without permission |
| **OurAirports** | airports, runways, navaids as nightly CSV | public domain | free | optional backdrop | static reference data, not a track; still a Law 9 fetch, so it needs its own approval |

**Ships**

| Source | Gives | Licence (as reported) | Cost | Recommend | Why |
|---|---|---|---|---|---|
| **Digitraffic marine (Finland)** | live AIS in Finnish waters, keyless REST and MQTT | CC BY 4.0 (SECONDARY) | free | **the candidate, if reopened** | keyless and open, but a regional slice, not a world sky |
| **AISStream** | live global AIS over a websocket, bounding box required | commercial use not addressed (UNVERIFIED) | key required (a credential); pricing unverified | skip until terms are read | credential plus unread commercial terms; must be proxied through our server |
| **BarentsWatch open AIS (Norway)** | live AIS in the Norwegian zone | NLOD | registered client credentials | skip for now | a credential for a regional slice |
| **AISHub** | global AIS | contribution-based | you must feed your own receiver | skip | needs hardware we do not run |
| **NOAA/BOEM MarineCadastre** | historical US AIS, one-minute | CC0 | free bulk files, months behind | skip for tracks | history, not live; a replay idea, not this layer |
| **Global Fishing Watch** | fishing effort, dark-vessel detections | CC BY-NC 4.0, token on registration | free with a token | skip | non-commercial and a credential |

**How a track layer would stay show-only.** It already is by construction: `show_only` returns
`show` before any provider is consulted, `SHOW_ONLY` keeps it out of the brief and alerts, and
both providers named for aircraft are `LIVE_ONLY`, so `may_ingest()` refuses to store them. A
future client would draw live positions on view and keep nothing.

**What a track client would need** (none is built):
1. The owner's Law 9 approval for that one source, by name.
2. A dated `world_terms` row read off the vendor's current terms page (for adsb.lol and
   Digitraffic marine, which are not recorded today).
3. A vendor file that reads only through `world_http` (switch off by default, cooldown,
   guarded GET), with `fetch` registered in the vendor egress check, and the layer's `client`
   key set so the state can read `dormant` or `on`.
4. Live-only handling: positions drawn and dropped, no table, no brain rows, no history, the
   retention class `EXHAUST` already used for `opensky` [V, `world_retention.py:54`].
5. Tests from a recorded body only (the root conftest refuses non-loopback sockets).
6. For a keyed source, a separate credential decision. For a websocket source, a server-side
   proxy so no key reaches a browser.

### 9. OpenWeb Ninja places

**What it gives** [V, `openweb_ninja_client.py`]: one key for a family of APIs: web search,
news, local business search, events, directions, job search, company reviews, website contacts
and social links. The `places` layer reads it as "Places, events and reviews near you".

**Licence** [V, `world_terms.py` row `openweb`]: commercial **NEEDS_AGREEMENT**; storage is
allowed only once an agreement exists. The terms restrict systematic storage and commercial use
without written permission [T, the client's own docstring and the blueprint]. Setting
`OPENWEB_NINJA_AGREEMENT_SIGNED` lifts the verdict to OK on the next boot, so signing is a
deployment step, not a patch.

**Cost: this one is a spend, so it needs the spend gate as well as Law 9.** Prices as the
blueprint recorded them in 2026-07 [T, not re-checked]: a free plan of 100 requests a month,
then monthly plans from $25 (10,000 requests) to $150 (200,000), or pay-as-you-go at $0.005 a
request.

**Two things the switch does not make obvious** [V]:
1. **The meter reads $0 until a price is configured.** `costs.openweb_ninja_cost()` returns 0.0
   until `OPENWEB_NINJA_PRICE_PER_CALL` is set, and the comment beside it says the aggregate
   dollar ceiling "only bites once a real price is configured". So with no price set, a
   spend-shaped check sees nothing, and the only brakes are the per-caller count caps and the
   switch. Any approval to turn places on must set the price first.
2. **The switch is suite-wide, not per layer.** `OPENWEB_NINJA_ENABLED=1` plus a key turns on
   every caller of the client, not just `places`: `app.py`, `blog_seo.py` and `prospector.py`
   also call it. Approving places by flipping that switch approves those too.

**How places would be show-only today.** It is not: `places` has `show_only: False` and was
designed to feed the brief. Today it reads `blocked` by the terms registry. To make it
show-only, flip that row to `show_only: True` (drawn hollow, never in the brief), which would
also make it read `show` regardless of the agreement, and fetch on view with nothing stored.
That is a one-line change in a layer catalogue, but it changes what a layer is, so it is the
owner's call (C59-3).

**What a client would need.** The client exists and is dormant, so the remaining steps are
decisions, not code:
1. The owner's spend approval (which plan, which monthly ceiling) and Law 9 approval.
2. The written agreement, if anything is ever stored or used in the paid product; without it,
   live display only.
3. `OPENWEB_NINJA_PRICE_PER_CALL` set to the plan's real per-request price before the switch is
   turned on, so the dollar ceiling can see it.
4. A per-layer switch, if he wants places on without also turning on the other callers (a
   small build, not designed here).

### 10. Owner questions (CC-59)

- **C59-1. Are aircraft or ship tracks reopened for a build?** A) No, both stay hollow with no
  client. B) Yes, after the command center is operational: adsb.lol for aircraft and Digitraffic
  marine for ships, live-only, after their terms are read. X) Something else. **Default A** (his
  q810 answer and Q13's default C; nothing here feeds the command center).
- **C59-2. Is OpenWeb Ninja worth paying for, for places?** A) No, places stays blocked; no spend.
  B) Yes, live display only on the smallest paid plan, price configured first, no storage
  without the written agreement. X) Something else. **Default A** (a spend with a $0-reading
  meter and a suite-wide switch, for a layer that does not feed the command center).
- **C59-3. Should `places` become show-only?** A) Leave it as designed (feeds the brief once the
  agreement exists), blocked until then. B) Make it show-only, so it can never feed the brief or
  an alert. X) Something else. **Default A** (no change to a layer's nature without a reason to
  build it).
- **C59-4. Should non-commercial track sources (OpenSky, airplanes.live) ever appear on the
  owner's own screen only?** A) No. B) Yes, owner-only, never shown to another user, after he
  approves the outbound call. X) Something else. **Default A** (his rule is that non-commercial
  data never reaches other users; owner-only use is allowed but nothing here asks for it).

---

## 11. What I verified and what I took on trust

- **Verified [V]:** the two task rows (`tasks/cc58`, `tasks/cc59`, version 3); `world_layers.py`
  rows, `state_of()` order, the refusal constants and `assert_refusals()`; the `world_terms`
  rows for `openweb`, `opensky` and `adsbdb` and the `may_ingest()` logic; `world_http.py`'s
  header; the vendor egress check listing `openweb_ninja_client` and the feed clients;
  `costs.openweb_ninja_cost()` returning 0 without a configured price; the other callers of
  `openweb_ninja_client`; that no aircraft, ship or webcam client exists (by `git grep` for the
  vendor names). All on hub `origin/main` at `d45910fa`.
- **Taken on trust [T]:** every vendor's licence, key, quota and cadence (survey 002, 2026-10-17,
  with that survey's own VERIFIED/SECONDARY/UNVERIFIED marks); OpenWeb Ninja prices and terms
  (hub blueprint, 2026-07-25). None of it re-fetched.
- **Not read:** any vendor page today (nothing was fetched); production environment variables,
  so whether `OPENWEB_NINJA_ENABLED`, `OPENWEB_NINJA_AGREEMENT_SIGNED` or a price is set on any
  deployed service is **unknown**, and the `blocked` state above holds only where the agreement
  variable is unset.
