# Handoff: desks-3-6 (NovahOS phone, GREYWOLF CPU, Siri guide), NODE, 2026-11-23

Status: CONTINUING. Router: ROUTER #135. Branch `node/desks-3-6-phone-siri-cpu`, draft PR from it. Nothing on the PC was
changed (no process stopped, no setting, no pairing, no chat sent). Every line says VERIFIED (ran today, 14:00 to 14:35
Pacific) or TRUSTED (read from a file or a report).

## Findings

### Phone "cannot connect (Tailscale)": that diagnosis is stale. The live blocker is pairing.
VERIFIED: Tailscale 1.104.5 Running, Health empty, iPhone peer Online. `tailscale ping` to the iPhone: 4 of 4 pongs via
DERP(lax), 68 to 109 ms. The phone host listens on the tailnet address only, port 8106; `/api/health` is 200 directly and
200 through overlord's forward (29 ms). Firewall: `Tailscale-In` allows the tailnet address in Domain and Private, and the
Tailscale adapter is Private. `POST /api/ask` and `/api/send` without a device key give `401 {"error":"not paired"}`, so the
2026-11-07 Siri shortcut (no key) fails today whatever the tunnel does.
VERIFIED from the host log (`%LOCALAPPDATA%\Novah\Prime\services\novahos-phone.log`): since v1.3 went live (11-09 16:43) every
page load ends at `GET /api/boot 401` (11-09, 11-10 twice, 11-17, 11-18, 11-19) and there is no `POST /api/pair` after it.
Something reached the host through the forward, then stopped at the "Not paired" panel. The log has no peer address, so
UNKNOWN whether that was the iPhone. `devices.json`: one active device "iPhone", paired 11-08 01:42 PST.
TRUSTED: `F:\novah-estate\13-ONLY-YOU.md` step 4 and `15-TURN-ON-RUNBOOK.md` step 1 already ask him to run Pair-Phone.cmd
and type the code; the log says it has not been done. The 11-07 "rx/tx 0 on overlord" is the previous desk's reading.
NOT VISIBLE from this PC: the iPhone's own request to overlord (no ssh allowed). Suspects: not paired or the Home Screen app
has empty storage; Tailscale toggled off at that moment; nothing else seen.

### CPU at 100 percent: the agent fleet, amplified by throttling, not one process
VERIFIED: 100 percent at every sample; kernel time 50 to 59 percent; 40k to 53k context switches per second; run queue 50 to
91 on 16 logical CPUs; `% Processor Performance` 41 to 45 (CPU about 43 percent of nominal while saturated; temperature
unreadable without admin: UNKNOWN). Plugged in, High performance. By name, percent of the machine: claude 15 to 24, python
10, Defender 8 to 12, WSL vmmem 7, dwm 4 to 6, WMI 4 to 9, find 4. Counts: 24 to 28 claude.exe, 17 to 19 node, 21 to 31
python, 29 to 56 bash, 590 to 636 processes. Same shape as 11-07.
VERIFIED leak: two `find.exe / -iname ...` from agent sessions, 131 and 35 minutes old, one at 3,965 CPU-seconds. In Git Bash
`/` includes every drive mount, so each walks all of F:. `node/windows/Stop-LeakedScans.ps1` (dry run) lists exactly these.
VERIFIED: Ollama has no model loaded and the GPU is idle, but its log shows about 1.2 to 1.5 requests per second of pure
polling (/api/tags, /api/version, /api/ps): 67,805 requests in about 10 hours against 5 inference calls; /api/tags takes 0.1
to 4.4 s each under load. WHO polls is UNKNOWN (all 127.0.0.1); the phone host polls once per 30 s, so not it.
Slow first replies: the host is pinned to qwen2.5:14b-instruct-q4_K_M (VERIFIED by `/api/health`; the "owner q9432 A, about
59 percent GPU / 41 percent CPU, about 2.5 tok/s" is the source comment, TRUSTED). I did not change it; it is his decision.

## What is in the PR
- `docs/NOVAHOS_PHONE_SIRI.md`: the guide rewritten in full (key header, pairing shortcut, one call to `/api/ask`, Version B
  fallback, error table, revoke). Public copy with placeholders for the tailnet addresses.
- `node/windows/Stop-LeakedScans.ps1`: owner-step script; prints by default, stops only with `-Apply`. Dry-run tested.
Not tested: the iPhone taps; a paired `/api/ask` (pairing is approved at the PC by him); whether iOS times out before 150 s.

## Owner steps
1. iPhone: Tailscale app Connected; open the overlord address in Safari (Add to Home Screen); if it says "Not paired", at
   GREYWOLF double-click `Pair-Phone.cmd` and type the code on the phone. Then build the two shortcuts from the guide.
2. GREYWOLF: `powershell -NoProfile -File Stop-LeakedScans.ps1 -Apply` (about one core back).
Optional, his call: Defender exclusion for the worktree folders (lowers protection; benefit unmeasured).
Router-level: cap parallel agent desks; 24 to 28 concurrent claude.exe is what keeps the box saturated.

## Left to do (not built, I hit the size cap)
1. `node/phone_path_check.py` + `tests/test_phone_path_check.py`: a read-only check that prints a verdict first line
   (GREYWOLF-SIDE-OK / GREYWOLF-SIDE-DOWN / UNKNOWN, never "phone works", because it cannot see the phone's own request),
   with the evidence above: tailscale status and ping, health direct and via the forward, count of active devices (never a
   digest), whether the host log has any `POST /api/pair` since the last start. Style: `node/captive_probe.py`.
2. `node/cpu_who.py` + tests: the per-name attribution and the leaked-`find` rule above, as pure functions over a JSON
   process list, with a fixture from this note.
3. Find who polls Ollama at 1.2 to 1.5 requests per second (candidates: the NovahOS window or launcher, the supervisor's
   ollama check, Open WebUI, Hermes). Read-only: count by User-Agent is not logged, so sample connections with `netstat`.
4. Private copy of the guide with real addresses at `F:\novah-estate\phone-siri-shortcut.md` (replace `OVERLORD-IP` and
   `GREYWOLF-IP`), then commit it in that local repo.
5. Re-check from the phone once he has paired: done_when "Phone chat answers from the local model".
