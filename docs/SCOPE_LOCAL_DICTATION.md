# Scope: local push-to-talk dictation into any app (mail2-18)

Desk NODE, part 203, 2026-11-23 Pacific. One page, scope only. Queue id `mail2-18` (class B, "desk proceeds, one-page scope"). He mailed himself the same dictation ad twice (2026-11-07, 2026-11-16) and types every instruction to every session.

## The ask
Hold a key, speak, release: the words are typed into whatever window has focus, including the Claude desktop app. No audio leaves the machine. A cloud dictation app is ruled out by his own rule that voice is local (no edge-tts, no cloud speech).

## What already exists (read, not run)
- **Local speech-to-text on the home node for the shell's Ask box**: `home-node/app/assistant/voicehost.py` runs under Prime's venv. Its header says the samples never leave that process (the pipe carries transcripts and commands only), the microphone is off until asked and closes three ways, including a dead-man timer.
- Its pipe is the shell's (`voicelink.py`); I read only the header and found no key injection into other windows. I did not search the file for it, so treat "shell only" as likely, not proven.

## The two ways to get there
| | A. Reuse our voicehost, add a "type into the focused window" sink | B. An existing open-source local dictation app, checked first |
|---|---|---|
| Audio stays local | Yes, by the voicehost design | Must be shown per app: read its network behaviour; a page that says "local" is a claim |
| Types into any window | New: a hotkey listener plus a key-injection step on Windows | Usually built in |
| What we keep owning | Another input-injection component in the product | Nothing, but we depend on its updates and licence |
| Fits "one app" | Yes, it becomes a NovahOS setting | A separate program, which the one-app vision is trying to remove |

**Recommendation: A for the shell (already done) and B as the bridge until A's injection sink exists**, because typing into other programs is an OS-level capability that deserves its own gate. The OPEN-SOURCE catalogue (`OPEN-SOURCE.md`) has no dictation row yet; the check-open-source-first step is therefore **not done here** and is the first step of whoever builds B. Candidate names are not given because none was read today.

## Guards (Law 9 and the owner's voice rule)
1. No audio and no transcript is sent anywhere. The speech model is a local file.
2. Push-to-talk only: the microphone is open only while the key is held, with the same dead-man close as the voicehost.
3. Injection is a capability, so it is off until the owner turns it on, and it never types into a password field or a window flagged secure by Windows.
4. A transcript is never logged with the window title it was typed into.

## Done when (from the queue)
This page names the tool and says it types into any focused window and that no audio leaves the machine. It does the first and third as a plan; "types into any window" is a design goal, not a measurement. **He queues or drops it.**

OWNER-STEP: say queue or drop for local dictation (A for the shell is already built; B or the injection sink is the new work) | blocks: any build of the injection sink.
