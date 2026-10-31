# Personal Chat installer (WEB-H4)

A private chat window on the buyer's own computer, answered by a local model through Ollama.
Product facts from the task row: one-time price, Windows and Mac, up to 3 computers per key,
sold through Polar (decision V6). **Nothing here sells, signs, uploads or publishes.** Every
build is an unsigned preview and says so in its file name.

## Layout

| Path | What it is |
|---|---|
| `app/personal_chat.py` | The app. Stdlib only. Serves one page on `127.0.0.1`, talks to Ollama on loopback and to nothing else |
| `app/seats.py` | Seat licensing (one key, the build's seat count). Reports `preview`, `unlicensed`, `licensed` or `unknown` |
| `app/static/index.html` | The chat page |
| `build/Export-Ladder.ps1` | Writes `ladder.json` **from** `home-node/installer/NodeSpec.ps1` |
| `build/build-windows.ps1` | Windows build: ladder, build info, PyInstaller, Inno Setup, SHA-256 |
| `build/personal-chat.iss` | Inno Setup script. Per-user install, no admin |
| `build/setup-windows.ps1` | First-run setup on the buyer's PC: spec check, Ollama, model download (asks first) |
| `build/build-mac.sh` | Mac build: `.app` and `.dmg`. **UNTESTED** |
| `../../tests/test_personal_chat.py` | The tests |

## The rules it keeps

- **One tier ladder.** `NodeSpec.ps1` holds the only copy. The build exports it to `ladder.json`
  with the SHA-256 of the file it read; the Windows installer ships `NodeSpec.ps1` itself and runs
  it on the buyer's PC. No threshold or ladder model name is written anywhere in this folder, and
  a test fails if one appears.
- **No cloud path.** The model host must be loopback. Anything else stops the app at start-up.
  There is no vendor key or vendor client.
- **No claimed tier.** Without the spec check's verdict the app uses the ladder's CPU-only row and
  shows `tier: unknown`.
- **No claimed licence.** A build with no store configured reports `preview` and makes no call. A
  configured build that cannot reach the store reports `unknown`, never `licensed`.
- **Law 9.** The one outward call is to the store host on the build's allowlist, https only, and
  only on Activate or a re-check of a key the buyer entered. The seat label is a random install
  id, not the computer's name. Model downloads happen on the buyer's PC only after they say yes.
- **Cross-site requests are refused.** A POST carrying another site's `Origin` gets 403, so a web
  page cannot drive the app through the browser.

## Build on Windows (verified on this PC, 2026-10-30)

Needs Python 3.12 with PyInstaller, and Inno Setup 6 (per-user install under
`%LOCALAPPDATA%\Programs\Inno Setup 6`).

```powershell
cd node\personal-chat\build
.\build-windows.ps1 -Version 0.1.0
# -> dist\out\PersonalChat-Setup-0.1.0-UNSIGNED.exe
```

`-NodeSpec <path>` points at another copy of `NodeSpec.ps1`; the default is the estate's
`F:\Leadfuel\home-node\installer\NodeSpec.ps1`. Output goes under `dist\` only (gitignored).

What was run here: the build end to end (about 8.7 MB setup file); the frozen app started, served
the page, reported `preview` / `tier: unknown` / unsigned, saw the local Ollama, refused a
cross-origin POST with 403, and quit cleanly on `/api/quit`; `setup-windows.ps1 -NoDownloads`
ran the spec check under Windows PowerShell 5.1 and wrote the tier verdict to a scratch folder.

**Not run here:** the setup `.exe` itself (it would install into this PC's profile), the
winget and model-pull paths, and a real chat answer through the frozen app. A clean Windows
machine is the test for those, as for the home-node installer (master checklist C11).

## Build on a Mac (UNTESTED)

Written on Windows with no Mac available. **Not one line has run.**

```bash
cd node/personal-chat/build
./build-mac.sh --version 0.1.0 --ladder ../dist/stage/ladder.json
# or, with pwsh installed:  ./build-mac.sh --version 0.1.0 --nodespec /path/to/NodeSpec.ps1
# -> dist-mac/out/PersonalChat-0.1.0-UNSIGNED.dmg
```

`NodeSpec.ps1` is Windows-only (master checklist C12), so a Mac install has no measured tier and
runs the ladder's CPU-only row with `tier: unknown`. Mapping Apple-silicon unified memory onto
the ladder is a decision for `NodeSpec.ps1`, not for this build.

## What is not done, and whose call it is

| Item | Blocked on |
|---|---|
| Code signing (Windows Authenticode; Apple Developer ID and notarisation) | Owner spend, card V7 |
| Store organisation, product, licence-key benefit with a 3-activation limit | Owner, Polar setup card |
| Key-entry screen in the app (the `/api/activate` route exists) | Lands with the Polar card |
| Polar endpoint shapes in `seats.py` | Written from Polar's public docs, not exercised: needs a test-mode key once |
| The CPU-only row's model licence | Check before sale: it may be a research (non-commercial) licence, and non-commercial items never reach other users |
| Mac tier mapping | NodeSpec.ps1 (C12) |
| Clean-machine install on Windows and on a Mac | A spare machine |
| Upload, release, download page, live sale | Owner handoff approval (preview-only rule) |
