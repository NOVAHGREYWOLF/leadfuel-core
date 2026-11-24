# Setup walkthrough: your Echo (S24) and your look (S25)

Item `webchat-11` (SURFACE). A short spec to read on a phone and approve. Docs only: **the code is not in this repo.** It is
on the estate repo's local branch `surface/webchat-11-echo-look` (that repo's push is disabled; it goes out by the VAULT
sync), so this draft PR carries the spec and nothing else. Nothing was sent anywhere and the author did not open a camera.
Each line says whether it was **read** in the code or **claimed** by an earlier desk's note and not re-checked.

## The queue row was out of date
The row says both steps are "only simulated". That was true on 2026-11-11. Since then the installer line
`node/installer-batch2-echo` built them for real (read: `ui/echoscreen.js`, `echogate.py`, `echostore.py`,
`ui/echocapture.js`, `ui/echoface.js`, `ui/setupfinish.js`, with their tests). This change does not rebuild them. It adds the
one thing the owner asked for that was still missing: **pick a colour** (read: S25 said "Choosing your own accent colour is
not built yet").

## The three answers the row asks for
1. **Where does the capture run?** On this computer only, inside the NovahOS window. The face tracker is bundled with the app
   and loaded from the app's own folder, never from the internet. The camera frames stay in the page's memory, are measured
   and overwritten, and are never written to disk. Only about 40 rounded measurements (a drawing recipe, under 2 KB) cross to
   the app, and are kept in the person's own app folder with a consent log. No image leaves the machine and no vendor model is
   called (read: the Echo code names no host; claimed by the installer desk, not re-run here: a headless-browser run that
   counted zero outside requests).
2. **What does Character Design receive?** Nothing, in this version. Character Design is a separate studio with its own
   password and no link to the window; the app never sends it data (read: the installer's Echo design note, section 0; the
   owner-card default "the avatar never leaves the computer"). Sending the recipe to the studio later is its own decision with
   a yes per use. Not built.
3. **Which installer step shows it?** The first-run guide, stage 5, in this order: **S19 Meet your system, S24 Build your Echo,
   S25 Choose your look**, then S20 Bring in your history. The result is visible in the NovahOS shell, not only in the guide:
   the account chip shows the person's Echo, **Settings > Your Echo** lets them view, redo or delete it, and **Settings > Look**
   holds the look and the accent colour.

## What the change adds (the "choose your look" step)
- **An accent colour** on top of a look: Indigo, Blue, Teal, Green, Gold, Clay, Rose, Violet, or "Match the look" (the default,
  which changes nothing). It sets the colour of buttons, links and highlights in all four looks and both themes.
- **Safe by construction:** every accent clears 4.5:1 text contrast on every background of every look in its theme, and the text
  on an accent button clears 4.5:1, recomputed from the stylesheets by a test. High contrast and Colour-blind safe still replace
  the accent on purpose. No colour is the only cue: each swatch shows its name.
- **Where:** S25, Settings > Look, and Ctrl+K ("Accent: Teal"). The window opens in the chosen accent from the first paint.
- **Your Echo in the look:** S25 shows the person's own Echo (when one exists) drawn in the look they are choosing.
- **Kept on this computer only.** The choice lives in the window's own storage. No bridge call, nothing sent.

## Checked, and what was not
Read back by running: 168 unit tests in 13 test files (the 18 new accent tests plus the existing look, setup-guide, Echo and
stream tests, which include their Node runs), all green, no full suite run; and the mockup's cascade in a browser over
loopback for each look, both themes, an accent over the HUD, and High contrast winning.

## Not built, and not claimed
- **A real camera run in the installed window.** The tracker has never been run in the real window by any desk (read: the Echo
  screen's own header says so). The owner's one check on his PC (consent, scan, camera light off, chip shows the Echo, network
  cable out, Delete) is still owed.
- **A free colour wheel.** Eight tested colours instead, because an arbitrary colour cannot be guaranteed readable.
- **Keeping the look with the account**, so every computer matches. It needs the account; the screen says so.
- **The choice between the app's warm look and the Greywolf black, red and gold** is a separate decision (`webchat-10`).
