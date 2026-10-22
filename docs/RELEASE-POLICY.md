# Release policy: how the Sora fan patch is delivered, updated and removed (RR-21)

Written 2026-10-18 by Claude (release helper) for the Phase 1 release-readiness item RR-21 (refines P1.8–P1.11).
**Release 1.0 is out (20 October 2026)**; a 1.0.1 candidate exists and is not released. Plain English on purpose:
the player README and the app texts should say the same things. Technical detail: [INSTALLER-TECH.md](INSTALLER-TECH.md),
screens and texts: [INSTALLER-UX.md](INSTALLER-UX.md). Decisions already made by Mat are marked **(decided)**.

## 1. What a release is

- A release has a **title** ("Sora for Dissidia 012"), a **version** ("1.0", "1.1", …) and one exact **result file**.
  The result file's SHA-256 is the release's identity: two players with the same version have byte-identical files.
- A release folder holds three files and nothing else: `patch.vcdiff` (only our changes), `release.json` (format 2:
  input/output size + SHA-256, the EBOOT decrypt check, older versions) and `README.txt`. The patch app embeds the same
  `release.json` + `patch.vcdiff`.
- **Version numbers:** 1.x = same save layout, so a save keeps working when you update. A bug-fix release raises the
  second number (1.0 → 1.1). A change that needs a save migration or breaks old saves would be 2.0, and must ship with
  its own migration and a clear warning. Every release, even a tiny one, gets a new number; we never replace the files
  of a published version.
- **Release 1.0 (published 2026-10-20)** is release candidate 3, unchanged: patch 14,708,841 B; result
  1,798,516,736 B, SHA-256 `36b6bc40d014fe6296c7061b4a2538bd26e8384a0ef6f478e6e133b4a05a0cdd`. (RC1 `dumps/release-1.0-rc1/`, result
  e04ce4d2…fcf3, and RC2 `dumps/release-1.0-rc2/`, result 69a07222…e3d5 — no grwp row, crashes on real PSP/Vita — are
  superseded and were never published, so they are not listed in `older_outputs`.)
- The result file's name carries the version: `Dissidia 012 + Sora (fan patch 1.0).iso`. The game's own title, disc code
  and save data ID inside the disc stay exactly as on the original disc **(decided: no PARAM.SFO change)**.

## 2. Which game files work

- Only **your own, unmodified US copy** of Dissidia 012 as an `.iso`: disc code **ULUS-10566**, size
  **1,754,529,792 bytes**, SHA-256 **df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e**.
- Everything else is refused with a clear message and **nothing is written**: European (ULES-01505) and Japanese
  (ULJM-05814) copies, other games, incomplete copies, modified or damaged copies, compressed images (CSO/ZSO/DAX/JSO),
  zip/7z/rar archives, folders and PSP app files. A file that already has this version says "This file already has
  Sora!"; an older Sora version asks for the original file (§5).
- We do not support other regions. They are different builds; the patch would need its own version for each.

## 3. Data Install (decided: no PARAM.SFO bump, release layout B)

- If you used the game's **Data Install** on the original game, you **don't need to delete or redo it**. The Sora
  version keeps the original file table, so the old install stays valid, and Sora's new and changed files are always
  read from the disc (they sit in our own index, which is searched first and never installed).
- Installing data again from the Sora version is fine too (sizes 1–3 all fit).
- Still to confirm at runtime (P1.7 / RR-21): an install made on the original disc is accepted on the Sora version and
  Sora's files still show. If that fails, the fix is a new release, not a manual step for players.

## 4. Where the new file goes

- Your original file is **only read, never changed**.
- The new file is saved **next to the original** (or in a folder you pick). If a file with that name is already there,
  the app adds " (2)", " (3)", … **It never overwrites anything.**
- The app writes to a hidden temporary file and gives it the real name only after its SHA-256 matches the release. If
  anything goes wrong, or you press Stop or close the window, the temporary file is removed. If the app is killed hard
  (crash, power cut), the next run in that folder removes its own leftover after 10 minutes of no activity and never
  touches any other file.
- Needs about 1.8 GB free on the target drive (the app checks first and offers "Choose another folder…").

## 5. Updates (1.0 → 1.1 and later)

- An update is a **new full release** built from your **original** file, not from the previous Sora file. Keep your
  original `.iso`.
- Each new `release.json` lists every earlier result in `older_outputs` (version + SHA-256). If you give the new app an
  older Sora file, it says which version that is and asks for your original file instead.
- Your save carries over within 1.x (same layout; the one-time move catch-up adds any newly learnable moves for Sora).
- **No original any more?** Not supported in 1.x. A later release may add "update from the previous Sora file"
  deltas. Until then: make a fresh copy from your own disc/PSP.
- When an update is out, delete the old Sora file yourself after you have checked the new one works.

## 6. Going back / uninstalling

- **To uninstall: delete the new Sora `.iso`.** That is all; the app installs nothing else on your computer (the app
  itself is one file you can delete too). Your original `.iso` is unchanged and still plays as before.
- On a PSP, delete the Sora file from the memory stick's `ISO` folder.
- **Saves are shared** with the original game (same save data ID). Going back to the original game with a save that
  was used with Sora is **not supported** (§7). Restore your backup instead.

## 7. Back up your save first (put this in every README)

- **Before your first start of the Sora version, copy your save folder** (PPSSPP: `memstick/PSP/SAVEDATA/ULUS10566…`;
  PSP: `PSP/SAVEDATA/ULUS10566…` on the memory stick) somewhere safe.
- **Friend cards:** Sora's progress is stored in the space of friend card number 25, so the friend-card limit becomes
  **24**. If your save already holds 25 cards, the first time Sora's record is set up the game makes room the same way
  it does when a new card arrives: **the oldest card that is not locked is removed.** Locked cards are never touched.
  Lock any card you want to keep before you start.
- **Downgrade is not supported:** loading a Sora-era save on the original game can wipe Sora's record (the 25th card
  slot), and the original game doesn't know Sora's four items or replays with Sora. To go back, restore your backup.

## 8. Platforms and devices

| | Patch app | Notes |
|---|---|---|
| Windows 10 / 11 (64-bit) | shipped with 1.0, built in CI | uses WebView2 (part of Windows 11; Windows Update installs it on 10). Unsigned v1: SmartScreen "More info → Run anyway". |
| macOS 11+ (Apple Silicon and Intel) | shipped with 1.0, built in CI | unsigned v1: System Settings → Privacy & Security → Open Anyway. |
| Linux x86-64 | AppImage (built on Ubuntu 22.04, glibc ≥ 2.35); shipped with 1.0; the AppImage was tested with a real-window patch run | `chmod +x`; some distros need `libfuse2`. Command-line `sorapatch-cli` also works. |
| Phones / tablets | no patch app | patch on a computer, then copy the file to the device. |

| Playing the result | Status |
|---|---|
| PPSSPP on PC (Linux) | tested (RC3 output p18: strict-mode smoke PASS 2026-10-20) |
| PPSSPP on Windows / macOS / Android / iOS | expected to work (same emulator core), not tested yet |
| Real PSP | needs custom firmware (the disc runs an unsigned module and a decrypted EBOOT); **not tested yet**, advertise only after a real-PSP test |
| PS Vita (PSP mode, Adrenaline CFW) | **tested** on test353/test354 (same game bytes as release 1.0), V1-V5, V7, V8 PASS (2026-10-20); game plugins must be off ([TEST-ON-VITA.md](TEST-ON-VITA.md)) |

Advertise only rows that have a recorded test. Until then the README says "tested on PPSSPP (PC)".

## 9. Licence (GPL-3.0) and what we never ship

- The patch app and `sorapatch-cli` are **GPL-3.0-or-later** (they contain a port of GPL code for the EBOOT decrypt;
  INSTALLER-TECH §7). Every app download must ship **the GPL-3.0 licence text** (`LICENSE` / "Licence" file next to the
  app or inside the bundle) and **a link to the complete source** of that exact build (tag or commit), or the source
  itself. **DECIDED 2026-10-20 (Mat): a public GitHub repository holds the installer source:**
  <https://github.com/MatNyaga/sora-fan-patch>. App id io.github.matnyaga.sorapatch.
- **Credit (DECIDED 2026-10-20):** the author is credited as **"Mat"** in the post, README and installer.
- **Wording (DECIDED 2026-10-20, Mat):** README/posts say: "No Dissidia files are included. Sora's model and sounds
  are fan-ported from Kingdom Hearts II. Fan-made, not affiliated with Square Enix or Disney." Never "no game data
  at all" (the patch carries KH2-derived Sora assets).
- **AI note (DECIDED 2026-10-20, Mat):** every release page/README carries "Built by Mat with help from AI tools
  (Claude, Codex)." (GameBanana requires naming the tools.)
- **Venues (2026-10-20):** GitHub Releases = download home; then YouTube trailer,
  GameBanana (request a Dissidia 012 section), r/dissidia, r/KingdomHearts, GBAtemp, PPSSPP forums, Romhack Plaza,
  r/PPSSPP, r/romhacking, r/vitahacks. Check each subreddit's rules by hand before posting (tools can't read Reddit).
- The release data (`patch.vcdiff` + `release.json`) is our own content, kept separate from the program.
- **We never ship game files:** no ISO, no EBOOT (encrypted or decrypted), no extracted game data, no `packages/sora`
  (it is derived from the disc). The patch holds only our changes; the vanilla-code check in `make_release.py` fails the
  release if any vanilla executable bytes or unchanged disc sectors would be stored in it.
- No trademarks, and no branding that suggests the games' makers are involved, in the app, its name, its icon or the
  download page; "fan-made, not affiliated"
  is shown in the app and README.

## 10. Checks before a version is published

1. `make_release.py` → RELEASE OK (vanilla checks), `sorapatch-cli` on the clean ISO → expected SHA-256.
2. Error paths (wrong file, other region, truncated, modified, already patched, cancel/kill, existing output,
   read-only folder) → all pass ([INSTALLER-TECH.md](INSTALLER-TECH.md#4-tests)).
3. App built for each advertised OS with that release embedded, started once on that OS, one full patch run.
4. GUI dependency advisories triaged (glib GHSA-wrw7-89jp-8q8g disposition: INSTALLER-TECH §8).
5. README states: US only, back up saves, friend-card note, no downgrade, tested platforms, licence + source link.

Decisions 2026-10-20 (Mat): the trailer post doesn't mention the gauge refills between takes; the research repository
is under the MIT licence; the landing page went live on GitHub Pages when Mat published release v1.0.0. Mat posts
everything.
