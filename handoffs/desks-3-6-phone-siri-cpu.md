# Handoff: desks-3-6 (NovahOS phone, GREYWOLF CPU, Siri guide), NODE, 2026-11-23

Status: tools built, owner steps remain (see below). First desk: ROUTER #135; continuation: ROUTER #136, 2026-11-23. Branch `node/desks-3-6-phone-siri-cpu`, draft PR from it. Nothing on the PC was
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

## What is in the PR (draft, never merged by this desk)
- `docs/NOVAHOS_PHONE_SIRI.md`: the guide rewritten (key header, pairing shortcut, one call to `/api/ask`, Version B fallback,
  error table, revoke) and, new, a troubleshooting row for `phone_path_check.py`. Public copy, placeholders for addresses.
- `node/phone_path_check.py` + `tests/test_phone_path_check.py` (93 tests): read-only check of the GREYWOLF end of the phone path.
  First line `GREYWOLF-SIDE-OK | GREYWOLF-SIDE-DOWN | FORWARD-DOWN | UNKNOWN`, then evidence (tailscale, host, forward, the phone peer
  and `tailscale ping`, what the host log says about pairing, a device COUNT) and a `next:` line. It cannot see the iPhone's own
  request, so it never says the phone works. A timeout says UNKNOWN, never DOWN. Run: `python node/phone_path_check.py --forward
  http://<overlord address>:8106` (the forward address is never written in the repo; it can come from NOVAHOS_PHONE_FORWARD).
- `node/cpu_who.py` + `tests/test_cpu_who.py` (90 tests): two process-list samples give each process NAME's share of the whole
  machine; the machine's own busy figure comes from GetSystemTimes, and what no process explains is its own line. Lists leaked
  `find` scans with the parent chain and prints no command line. `--clients-of 11434` names who holds connections to a port;
  `--ollama-rate` reads Ollama's log tail for the request rate. It stops nothing (a test pins that).
- `node/windows/Stop-LeakedScans.ps1` (re-written) + `Stop-LeakedScans.cmd` + `tests/test_stop_leaked_scans.py`: owner-run script,
  dry run by default. Held to the same rule as `cpu_who.find_leaks` by one table of 15 command lines run through both (PowerShell
  5.1 and 7).

## Verified in the continuation (2026-11-23, 15:30 to 16:50 Pacific, all read-only)
- `phone_path_check.py` run live: `GREYWOLF-SIDE-OK`; host and forward both answered with the host's health body; the phone peer
  Online with 3 of 3 `tailscale ping` pongs via DERP(lax), 36 to 62 ms; pairing line `LAST-PAGE-LOAD-REFUSED` (last
  `GET /api/boot 401` at 2026-11-19 11:03:46, no `POST /api/pair` since the last host start); devices: 1 active of 2 enrolled.
  This reproduces the first desk's findings with a tool instead of by hand.
- A bug in my own first draft, found by running it: `Self.Online` in `tailscale status --json` reads `false` (LastSeen year 1)
  on this PC while Tailscale is Running and the phone answers pings, so trusting it made every run UNKNOWN. It is ignored now,
  with a test that says why.
- `cpu_who.py` run live (8 s interval, 16 logical CPUs): SATURATED, machine 100 percent busy, processes explain 74 percent. By
  name: claude.exe 11.7 percent (41 processes), powershell 9, MsMpEng 8.4, python 5.9, find.exe 4.9 (the two leaks), WmiPrvSE 4.1.
  The two leaked finds from the first note are STILL RUNNING (age 3 h 17 min and 101 min at that sample, 5,356 and 2,360
  CPU-seconds), parents already gone (orphans). Together they hold about 5 percent of the machine.
- Ollama request log, last 118 minutes: 1.59 requests per second, 99.96 percent status polls: `/api/tags` 0.91/s (median gap 1.0
  s), `/api/version` 0.51/s (2.0 s), `/api/ps` 0.16/s (5.0 s), 4 POSTs. Three different periods, so at least three independent
  timers. `--clients-of 11434` (one netstat read): NovahOS.exe holds 3 open connections, the phone host's python 1, plus 28
  TIME_WAIT sockets whose owner Windows does not record. TRUSTED, from reading source only, not measured: `probes.py` repeats a
  sweep every 4 s and `ui/panel.js` polls every 5 s; none of the sources found yet explains a 1 s `/api/tags` loop.
- A fault in the previous desk's owner step, found by running it: `powershell -File Stop-LeakedScans.ps1` is REFUSED on this PC
  ("running scripts is disabled": every execution-policy scope is Undefined, so the client default Restricted applies). The
  `.cmd` wrapper adds `-ExecutionPolicy Bypass` for that one process and changes no setting.
- A latent bug in the previous script, found by the table test: its pattern read `find / -name find x` as root `x` (a miss, so it
  stopped less than it should), skipped `find -L / ...`, and would have counted a Windows `find /i "text"` in System32 as a root.
  All three are fixed and tested. It also now says UNKNOWN for a `find` whose command line it cannot read, instead of "nothing to
  do", and re-reads a pid's start time before it stops it.
- Not run by me (guard): `Stop-LeakedScans -Apply`, anything that stops a process, any scan.

## Owner steps
1. iPhone: Tailscale app Connected; open the overlord address in Safari (Add to Home Screen); if it says "Not paired", at
   GREYWOLF double-click `Pair-Phone.cmd` (home-node/app/assistant) and type the code on the phone. Then build the two
   shortcuts from the guide. After that `python node/phone_path_check.py --forward ...` should show `LAST-PAGE-LOAD-PAIRED`.
2. GREYWOLF: in a terminal, `node/windows/Stop-LeakedScans.cmd` (lists), then `node/windows/Stop-LeakedScans.cmd -Apply`
   (stops the two scans, about one core back). Plain `powershell -File ...ps1` will be refused by the execution policy.
Optional, his call: a Defender exclusion for the worktree folders (lowers protection; benefit unmeasured; MsMpEng was 8.4 percent).
Router-level: cap parallel agent desks; 40 or so concurrent claude.exe is what keeps the box saturated.

## Left to do
1. Find the 1 s `/api/tags` poller. Method now exists: `python node/cpu_who.py --ollama-rate` before and after the owner closes
   one thing at a time (the NovahOS window first: it holds 3 of the 4 open connections), then compare the median gaps. The
   candidates are timers inside NovahOS.exe (the window's panels), not Open WebUI or Hermes, which hold no connection right now.
   Fixing it is a code change in the NovahOS app (`home-node/app`), which is not this desk's lane: hand to the owner of that code.
2. The private guide copy with the real addresses is committed LOCALLY in the private estate repo on branch `node/desks-3-6-guide`
   (worktree `.claude/worktrees/desks-3-6-guide`, commit aa3e2df, not pushed). The stale 2026-11-07 file at the checkout's
   `phone-siri-shortcut.md` (untracked, says "no keys needed") was left alone because the checkout holds other sessions' work;
   whoever merges the branch should move the old file aside first, or git will refuse to overwrite it.
3. Re-check from the phone once paired: done_when "Phone chat answers from the local model". Only the owner can do this.
4. Not measured: whether iOS gives up on a request before 150 s (guide Version B covers it); the phone's 14B first-reply time.
