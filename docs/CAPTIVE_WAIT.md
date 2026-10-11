# CAPTIVE-WAIT: wait out the Wi-Fi portal, do not fail

Task `NODE · CAPTIVE-WAIT 1/1`. Owner answered q290 = C on the Router desk page (2026-10-06):
"Queue a NODE task so runners and desks detect 'captive portal' and wait instead of failing."

## Why

The TLS-INTERCEPT desk found that the PC's Wi-Fi drops into a captive portal, from seconds to
hours. While it does, the portal answers HTTPS for every site with its own self-signed
certificate and its DNS gives wrong answers. Windows logs it (NCSI: "Hotspot detected"). All 89
`DEPTH_ZERO_SELF_SIGNED_CERT` errors in the session logs fell inside those windows, and the CI
runner containers share the host's network (WSL mirrored mode), so everything failed at once.
That is the network, not the code, the runner or the vendor.

## What landed

| Piece | File | What it does |
|---|---|---|
| Probe | `node/captive_probe.py` | Says `CAPTIVE`, `ONLINE` or `UNKNOWN` (exit 3 / 0 / 2). |
| Stall check | `node/ci/runner_stall_check.sh` | Asks the probe first and again at the end; `CAPTIVE` (exit 3) means wait and retry later. |
| Watch wrapper | `node/ci/runner_stall_watch.sh` | Unchanged except a comment: records exit 3 like any other. |
| Tests | `tests/test_captive_probe.py`, `tests/test_runner_stall_captive.py` | 89 tests; mutation-checked. |

### The probe

Two signals, and `ONLINE` needs both:

* **Windows' own verdict.** The newest `Microsoft-Windows-NCSI/Operational` event per address
  family for the interface that carries the default route. Numeric fields only, so it does not
  depend on the display language. `ActiveHttpProbeFailedHotspotDetected` or a "Hotspot detected"
  event means captive; `SuspectDnsProbeFailed` alone does **not** (it came four times in the
  log, and only once was a portal behind it).
* **One plain-HTTP GET** of `http://www.msftconnecttest.com/connecttest.txt`, the URL Windows
  itself probes. The body must be exactly the known text. A redirect, a 511 or another page is
  a portal. Redirects are not followed.

A probe that cannot tell says `UNKNOWN`: an unreadable log, no default route, a timeout, the two
signals disagreeing, or `--no-http` (which can never say `ONLINE`).

What it never does, and a test fails if a later edit tries: make a TLS connection, import `ssl`,
trust or install a certificate, follow a redirect, send a POST, or read a credential. The only
traffic is the one GET. `--no-http` sends nothing. `--as-of <UTC>` replays the Windows log at a
past time (read-only, no GET) for proving a verdict against a known episode.

### The stall check

* **Captive at the start:** it prints `CAPTIVE <why>`, skips every `docker exec` and `gh` call
  (they hang during an outage: three of the first four scheduled runs on 10-06 only said "timed
  out"), and exits 3 in under a second.
* **Trouble found, then captive at the end:** if the runner probes found something and the
  portal came up while they ran, it prints `CAPTIVE` and lists each finding as
  `held back (would be STALLED|UNKNOWN)`. Findings are never dropped.
* **Not captive:** the old verdicts stand. A probe that is `UNKNOWN`, crashes, hangs, is missing
  or prints nonsense changes nothing and is shown as `captive probe: UNKNOWN ...`.
* **It restarts nothing.** The script never ran `docker restart|stop|rm` or touched a
  registration, and a test asserts that across every verdict.

## Verified, and taken on trust

Verified by this desk: the probe on the live PC (ONLINE, 2 to 7 s per run); its Windows signal
replayed over the real log (10-05 captive from 16:55:06Z, 10-06 captive from 02:13:31Z and the
short 05:21Z blip, all matching TLS-INTERCEPT's windows); the real stall check replaying the
10-06 02:18Z episode through the real probe (`CAPTIVE`, exit 3, 0.8 s, no docker call); the real
scheduled task `NODE runner stall check` running the new scripts (`captive probe: ONLINE`); bare
`pytest` 464 passed. The first two live runs found two bugs the tests had missed (a POSIX path
`python.exe` cannot open, and `WinError 6` for a missing stdin under `conhost --headless`); both
are fixed with tests.

Taken on trust (TLS-INTERCEPT's report, not re-checked): that the portal is the network's and
not software on the PC. **Not tested:** a live portal episode through the live stall check; none
happened while this desk ran. The replay and the stubbed tests stand in for it.

## Deployment

The source of truth is `node/` in this repo. The PC runs copies in `F:\novah\ci\`
(`captive_probe.py`, `runner_stall_check.sh`, `runner_stall_watch.sh`); copy them over with a
rename so a run in progress keeps its old file. `F:\novah\ci\NOTES.md` has the same description.

## Not done, on purpose

* **`entrypoint.sh` backoff.** The runner container's token mint fails during a portal, the
  container exits, and Docker restarts it about once a minute (79 times on 10-05). Making it
  wait instead is the right fix for that churn, but it needs a runner recreate, which kills any
  job in flight. A sketch: on a failed mint, run a plain `curl` of the same NCSI URL without
  `-L`; if it is not the known text, sleep 60 and try again instead of exiting. Needs an owner
  decision before any runner is recreated.
* **Pushing the verdict to a session.** Nothing does; the router or WATCH reads
  `state/runner-stall.latest`, as before. `CAPTIVE` there means wait.

## PROPOSED note for desks (not adopted; the owner or router decides where it lives)

> **On a certificate error, check the network before you blame the code.** If a command or API
> call fails with a certificate error (`DEPTH_ZERO_SELF_SIGNED_CERT`, `SELF_SIGNED_CERT_IN_CHAIN`,
> curl exit 60, `RemoteCertificateNameMismatch`, `UnknownIssuer`), or with a burst of DNS or
> connection resets that has no other cause, run `python F:/novah/ci/captive_probe.py` (read-only:
> one plain-HTTP GET, no TLS). If the first word is **CAPTIVE**, the PC's Wi-Fi is behind a
> captive portal, which can last seconds or hours: do not fail the task, do not retry in a tight
> loop, do not restart anything, and never trust the certificate, set `NODE_EXTRA_CA_CERTS` or
> turn verification off (that would hand your tokens to the portal). Wait with
> `python F:/novah/ci/captive_probe.py --wait 900` (re-checks every 60 s for up to 15 minutes;
> exit 0 means back online, 3 still captive), then retry the step once. If it is still captive
> after a few rounds, report `STATUS: BLOCKED | <task id> | <PR or no PR> | network captive since
> <UTC>` and write your handoff rather than failing. **ONLINE** means the network is fine, so the
> certificate error is real: stop and investigate, and do not retry with secrets. **UNKNOWN**
> means the probe could not tell: say so, retry once after a minute, and assume neither.
