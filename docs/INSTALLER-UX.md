# Patch app: screens and texts (P1.10b + P1.10c)

Written 2026-10-18 by Claude (P1.10 helper). **Status: shipped in release 1.0 (2026-10-20)**; the maintained source
is <https://github.com/MatNyaga/sora-fan-patch>. Mat approved the look and the texts before release. Tech side: [INSTALLER-TECH.md](INSTALLER-TECH.md). Mock: open
`tools/installer/mock/index.html` in a browser (every screen side by side + a clickable demo).

Mat's brief: *"No trademark at all, we just want something user friendly to even the most tech illiterate person
while making it look good still."*

## 1. Principles
- **One window, one action.** Drop the file (or click "Choose file…"). Everything after that runs by itself: check,
  build, check the result. No options, no command line, no settings.
- **The player's file is only ever read.** The new file goes next to it under a new name. It is written under a hidden
  temporary name (`.<name>.part`) and only renamed once its fingerprint (SHA-256) matches the release. A failure,
  a cancel or a crash leaves no half-written file behind.
- **Plain words.** Short sentences. Every message says what happened *and* what to do next. No "ISO9660", "hash",
  "VCDIFF" or error numbers on screen. A small "Details for helpers" fold holds the technical line for support.
- **Calm.** Problems use a soft coral badge, never alarming red. "Already has Sora" is good news (green star), not an
  error. "Stopped" is neutral.
- **No trademarks.** No company names or logos, no game art, no lettering that imitates the games' own titles, and no
  "official", "update" or "DLC" wording. The game's name appears only as plain text, to say which game this works with.

## 2. Flow
```
Welcome ──drop / choose──▶ Working: [1 Check your file] → [2 Add Sora] → [3 Check the result] ──▶ Done
   ▲                              │ (problem or Stop)
   └──── Choose another file ◀── Problem / Stopped
```
Drag a file over the window at any calm screen (welcome, problem, done) → it jumps to the welcome screen with the drop
area lit up gold ("Let go to use this file").

## 3. Screens and texts (EN)
All texts live in one file: `tools/installer/app/ui/strings.en.js` (the CLI test checks every problem has a text).
Placeholders in `{braces}` are filled by the app.

**Every screen.** Header: our star emblem + **"Sora for Dissidia 012"** + gold pill **"FAN PATCH"**; buttons **A−**, **A+**
(text size), **Help**. Footer: *"Unofficial fan-made project. Not affiliated with, endorsed or sponsored by the makers
or publishers of the game."* + "Version {version}".

### 3.1 Welcome
- Title: **Add Sora to your game**
- Line: *This makes a new copy of your game with Sora in it. Your own game file stays exactly as it is.*
- Drop area (the whole area is one big button): disc-and-arrow icon, **Drop your game file here**, "or",
  **[Choose file…]** (gold). While dragging: **Let go to use this file**.
- Hint: *You need the US version of Dissidia 012 Duodecim Final Fantasy, saved as an .iso file.*
- Fold **How do I get this file?** → *Make it from your own game disc: on a PSP with custom firmware, set "USB Device" to
  "UMD Disc" in the VSH menu, connect the PSP to your computer with a USB cable, and copy the .iso file that appears.*
  (Own disc only; no download links anywhere.)
- The file picker shows `.iso` files ("Game file (.iso)").

### 3.2 Working (one screen, three steps)
Step pills at the top: **Check your file** → **Add Sora** → **Check the result** (done = green tick, current = gold ring).
File name chip under the text. Big progress bar (blue→gold) + big percentage. **[Stop]** always visible.

| step | title | line |
|---|---|---|
| 1 | Checking your file… | Making sure this is the right game. This takes about a minute. |
| 2 | Adding Sora… | Please keep this window open. Your original file is not being changed. |
| 3 | Checking the result… | Almost done. |

What happens in step 1, in this order (cheap checks first, so wrong files fail in under a second):
1. File exists, is a file, can be read.
2. First bytes: ZIP / 7Z / RAR → "still packed"; CSO / ZSO / DAX / JSO → "compressed"; PBP → "app file".
3. Game code from the disc's `UMD_DATA.BIN`: missing → "not a PSP game file"; another game → "different game";
   ULES-01505 / ULJM-05814 → "European / Japanese version".
4. Size smaller than the real disc → "incomplete".
5. SHA-256 of the whole file (the progress bar moves here): = clean US disc → go on; = this release's output →
   "already has Sora"; = an older release → "older Sora version"; anything else → "changed".
6. Room and permission: free space ≥ output size + 64 MB on the target drive; can create a file in the folder.

Timing (measured on synthetic data, i7-7700HQ, see TECH §4): about 15 s check + 25 s build for a 1.8 GB disc, plus
the time the drive needs to save it. "About a minute" is honest.

### 3.3 Done
- Green tick badge. Title: **Done! Sora is ready.**
- Box: **Your new game file** `Dissidia 012 + Sora (fan patch 1.0).iso`; **Saved in** `<folder>`.
- **[Open folder]** (gold; opens Explorer / Finder / file manager with the file selected) **[Close]**.
- Green line: *Your original game file was not changed.*
- **How to play** (two rows with simple icons, ours):
  - *On a PC, Mac or phone with PPSSPP: open PPSSPP and choose the new file.*
  - *On a PSP with custom firmware: copy the new file into the ISO folder of the memory stick.*
- If P1.8 decides on a PARAM.SFO bump, add one row: *If you used Data Install before, do it again from the game's
  Extras menu.* (Not shown today.)

### 3.4 Problems
Layout: badge, title, one or two sentences, buttons, "Details for helpers" fold (code + technical detail).
Default button: **[Choose another file]**. Space/permission problems also get **[Choose another folder…]**
(gold), which reruns with the same file and the new folder.

| code | title | text |
|---|---|---|
| not_found | We can't find that file | It may have been moved or deleted. Please choose it again. |
| is_folder | That's a folder, not a file | Open the folder and choose the game file inside it (its name ends in .iso). |
| cant_read | We couldn't read this file | If it's on a USB stick, an SD card or your PSP, copy it to your computer first and try again. |
| empty | This file is empty | There is nothing in it, so the copy probably didn't work. Please copy the game from your disc again. |
| archive | This file is still packed ({kind}) | Unpack it first (right-click it and choose Extract), then choose the .iso file that comes out. |
| compressed_image | This game file is compressed ({kind}) | Please use the full .iso file instead. A "CSO to ISO" converter can turn it back into an .iso. |
| eboot | This is a PSP app file, not a game disc file | Please choose the game's .iso file instead. |
| not_disc | This isn't a PSP game file | Please choose your Dissidia 012 Duodecim Final Fantasy .iso file. |
| other_game | This is a different game | This file is another PSP game (its code is {id}). Please choose Dissidia 012 Duodecim Final Fantasy. |
| wrong_region | This is the {region} version | This patch only works with the US version (code ULUS‑10566). Your file is {id}. |
| incomplete | This file is incomplete | It is {have}, but the full game is {want}. The copy probably stopped early. Please copy it again. |
| already_patched ★ | This file already has Sora! | It's already the Sora version {version}. You can play it right away. There's nothing more to do. |
| older_patch | This file has an older Sora version ({version}) | Please choose your original game file, the one without Sora. We'll build the new version from it. |
| modified | This file has been changed | It's the right game, but not an original copy. It may be damaged, or another mod was added. Please use a fresh copy made from your disc. |
| no_space | Not enough free space | You need about {need} free on this drive, but there is only {have}. Free up some space, or save the new file somewhere else. |
| no_space_late | The drive filled up | The drive ran out of space while building. Nothing was changed. Free up some space and try again. |
| cant_write | We can't save in this folder | Please choose another folder for the new file, for example Documents or Desktop. |
| build_failed | Something went wrong | The new file didn't come out right, so we removed it. Your original file is safe. Please try again. If it keeps happening, tell us this code: {code}. |
| cancelled | Stopped | Nothing was changed. You can start again any time. |

`build_failed` codes for helpers: `E-IO` read/write error, `E-SUM` a patch window did not match (corrupt download),
`E-PATCH` the patch file itself is bad (our bug), `E-HASH` the finished file's fingerprint was wrong (removed),
`E-APP` the app could not start the job.

### 3.5 Help (Help button or F1)
1. You need your own copy of Dissidia 012 Duodecim Final Fantasy, US version, as an .iso file.
2. Drop that file into this window, or click "Choose file…". Everything else happens by itself.
3. Your original file is never changed. The new file is saved next to it with a new name.
4. Then open the new file in PPSSPP, or copy it to the ISO folder of your PSP's memory stick.
[Got it]

## 4. Output file
- Name from the release manifest; proposed **`Dissidia 012 + Sora (fan patch 1.0).iso`** (works on Windows, macOS,
  Linux and the PSP memory stick). The game's own title on the XMB comes from inside the disc anyway.
- Saved next to the original. Existing file with that name → `… (2).iso`, `… (3).iso`. Nothing is ever overwritten.
- Folder not writable or too full → "Choose another folder…".

## 5. Accessibility
- Base text 17 px, titles 30 px, buttons ≥ 52 px tall. **A− / A+** (and Ctrl/Cmd + = / − / 0) scale everything:
  100 / 115 / 130 / 150 %, remembered on that computer. The window can be resized and the card scrolls.
- Full keyboard use: Tab order follows the screen; Enter/Space on the drop area opens the file picker; Ctrl/Cmd+O =
  choose file; F1 = help; a thick gold focus ring is always visible.
- Screen readers: every screen change moves focus to its title; a polite live region announces steps and results;
  the progress bar has role/aria values; icons are decorative (`aria-hidden`).
- Colour: body text ≥ 12:1, muted text ≥ 7:1 on the dark panel; meaning never by colour alone (badge symbol + title).
- `prefers-reduced-motion` turns off the twinkle and slide-in; `prefers-contrast: more` strengthens lines and text.

## 6. Look (P1.10c)
- **Name options** (plain text, no logo; Mat picks):
  1. **Sora for Dissidia 012**: fan patch *(used in the mock; says exactly what it is)*
  2. **Open Sky**: Sora fan patch for Dissidia 012 *(our own project name, "sora" = sky; can carry future fighters)*
  3. ~~Duodecim Plus~~ *(too close to the game's own title; not recommended)*
  Avoided on purpose: "Keyblade", "Kingdom", crowns, hearts, crystals, company names, "official", "update", "DLC".
- **Art**: all ours and drawn in code. Night-to-dawn sky gradient, CSS stars, a hand-drawn cloud bank, a soft dawn
  glow, a 4-point star emblem in a gold-to-blue ring (also the app icon, `app/src-tauri/icons/make_icons.py`).
  System fonts only.
- **Palette**: Night `#0B1026`, Deep `#142250`, Dusk `#1F3C7D`, Sky `#3D7BE0`, Sky light `#9CCBFF`, Gold `#F5C04A`
  (main buttons, text on gold `#1B1633`), Dawn `#FFB58A`, Good `#5BD6A0`, Problem `#FF8F7F`, Text `#F4F7FF`,
  Muted `#B8C4E2`.
- **Layout**: 800×720 window (min 560×560). Header bar, one frosted card in the middle, disclaimer footer.

## 7. Languages (later)
One strings file per language (`strings.<lang>.js`, same keys), picked from the system language with English as the
fallback. Candidates after EN: ES, FR, PT-BR, DE, IT, JA. The CLI check covers every language file.

## 8. Decided for release 1.0
The open points of the draft were settled before release 1.0: Mat approved the look and the texts, the app ships as
**Sora Fan Patch**, the output name is the one in §4, and version 1 ships unsigned with first-start instructions
([INSTALLER-TECH.md](INSTALLER-TECH.md#6-first-start-of-an-unsigned-app)). A later version for more fighters (one app
with a fighter-pack checklist, Phase 2 decision P2.11) is planned, not built.
