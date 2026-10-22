# Patch app: how it works

The patch app turns a player's own clean `.iso` into a new `.iso` with Sora in it. It ships as one file per
operating system with the release patch built in.

**Where the code lives.** The maintained app is in its own public repository,
<https://github.com/MatNyaga/sora-fan-patch> (GPL-3.0-or-later). `tools/installer/` in this repository is an
**early copy** (refreshed 20 October 2026, before the 1.0.0 version bump): the decoder, checks, EBOOT decryption,
CLI, window and the GPL text (`tools/installer/LICENSE`) are there, but not the build pipeline. Use the app
repository for anything current. Screens and texts: [INSTALLER-UX.md](INSTALLER-UX.md).

**Status.** Release 1.0 shipped with this app on 20 October 2026 (Windows, macOS, Linux). A version for more
fighters is **planned, not built**: Phase 2 decision P2.11 is one app with a fighter-pack checklist, every pack
installed from the player's own clean disc (see [ROADMAP.md](ROADMAP.md)).

## 1. Design rules

- **One window, one action.** Drop the file (or click "Choose file…"); checking, building and checking the result
  then run by themselves. No options, no command line.
- **The player's file is only ever read.** The new file goes next to it under a new name. It is written under a
  hidden temporary name and renamed only after its SHA-256 matches the release. A failure, Stop, or closing the
  window removes the temporary file. If the app is killed hard, the next run in that folder removes its own leftover
  after 10 minutes of no activity, and never touches any other file.
- **It never overwrites anything.** If the name is taken, it adds " (2)", " (3)" and so on.
- **Plain words.** Every message says what happened and what to do next. Technical details sit in a small
  "Details for helpers" fold.
- **No trademarks.** No company names, logos or game art, no "official", "update" or "DLC" wording. The game's name
  appears only as plain text, to say which game the patch is for.

## 2. Why Tauri and Rust

**Tauri v2 (Rust) with our own pure-Rust streaming VCDIFF decoder.**

- The window is HTML/CSS, so the reviewed mock-up *is* the app's UI.
- The work happens in a small Rust library (`core/`): file checks, SHA-256, VCDIFF decoding, safe temp file and
  rename. No external binary. The same code runs in a command-line tool (`sorapatch-cli`) used for tests.
- One self-contained file per OS with the patch embedded. A few MB plus the patch on Windows and macOS; the Linux
  AppImage is about 95 MB because it carries WebKitGTK. Low memory use (about 30–50 MB measured).
- Fallback if WebKitGTK causes trouble on some Linux distros: the same core behind an egui window.

| | Tauri v2 + Rust | Python + PySide6 | Electron | Go + Wails / Fyne | Rust + egui | Web page + WASM |
|---|---|---|---|---|---|---|
| Size per OS | small on Win/mac; ~95 MB AppImage | 40–80 MB | 80–150 MB | 8–25 MB | 5–10 MB | none |
| One file, nothing to install | yes | yes, but unpacks on every start | yes | yes | yes | needs Chromium to save big files |
| VCDIFF without an external binary | our decoder | slow in pure Python | needs a JS/WASM decoder | would need writing | our decoder | can't stream-write 1.8 GB on Firefox/Safari |
| Drag and drop with real paths | yes | yes | yes | yes | yes | no |
| Look | full HTML/CSS | good, more work | full HTML/CSS | Wails good, Fyne plain | custom-drawn | HTML |
| Antivirus false alarms | low | high (onefile bundles are often flagged) | medium | low | low | n/a |

Electron is too big for a small helper, PyInstaller trips antivirus tools, and a web page can't save a 1.8 GB file
next to the original on every browser. Wails came closest; Tauri won because the Rust decoder is shared with the CLI.

## 3. The patch and the release folder

**Decoder.** Default code table, source-copy windows, and xdelta3's per-window Adler-32 checksum (a corrupt download
is caught). It cleanly refuses secondary compression, custom code tables and target-copy windows, so patches must be
made with **`xdelta3 -e -9 -S none`**. Source bytes are read from the player's file on demand, so a whole-disc
source window (`-B 2147483648`) decodes in about 30 MB of RAM. A decoder bug can't produce a bad file silently: the
output SHA-256 must match before the rename.

**Release folder.** Exactly three files: `patch.vcdiff` (only our changes), `release.json`, and `README.txt`. The
app embeds `release.json` and `patch.vcdiff` at build time.

```json
{ "format": 2, "title": "Sora for Dissidia 012", "version": "1.0",
  "input":  { "disc_id": "ULUS-10566", "size": 1754529792, "sha256": "df94177d…ab6e" },
  "output": { "file_name": "Dissidia 012 + Sora (fan patch 1.0).iso", "size": <size>, "sha256": "<sha256>" },
  "source": { "kind": "plain_eboot", "file": "PSP_GAME/SYSDIR/EBOOT.BIN", "offset": 1146880,
              "encrypted_size": 4641296, "encrypted_sha256": "8fbf3541…3394",
              "plain_size": 4640948, "plain_sha256": "0bc8e779…fe6d" },
  "older_outputs": [ { "version": "…", "sha256": "…" } ],
  "other_regions": { "ULES-01505": "European", "ULJM-05814": "Japanese" } }
```

**Why format 2.** The modded game needs a decrypted EBOOT, but the release must not carry any of the game's own
code. So the app decrypts **the player's own** EBOOT in memory (pure Rust, offline, about a second) and applies the
patch against a "virtual source": the clean disc with that one file swapped for its decrypted form. Nothing is
written except the output. Every size and hash is checked on the way; any mismatch stops with `E-DECRYPT`. A side
effect: plain xdelta3 tools can't apply the release directly; `sorapatch-cli RELEASE_DIR ISO` is the command-line
route. (Format 1, a plain patch against the player's file, is still accepted by the core.)

**Release rules** (each release's `README.txt` repeats these for players):

- A version is identified by the SHA-256 of its result file; published files never change. 1.x versions keep the
  same save layout, so saves carry over; a change that breaks saves would be 2.0.
- Updates are always built from the **original** file, not from the previous Sora file. Each release lists earlier
  results in `older_outputs`; given an older Sora file, the app says which version it is and asks for the original.
- The game's title, disc code and save data ID stay as on the original disc, so an existing Data Install stays
  valid (Sora's files are always read from the disc).
- To uninstall, delete the Sora `.iso`. Saves are shared with the original game; back them up first, and restore the
  backup to go back (loading a Sora-era save in the original game isn't supported).

## 4. Tests

- **Synthetic suite** (`tools/installer/tests/run_synthetic.sh`, 22 cases): round trips against the real xdelta3
  encoder at several settings, never overwriting, the input staying byte-identical, every problem code (wrong
  region, other game, incomplete, modified, already patched, older patch, archive, compressed image, empty, folder,
  not found, not a disc, can't write), refused DJW patches, a flipped patch byte caught, and no file left behind in
  any case. `--check-strings` confirms all 19 problem codes have a title and text.
- **Real release, command line (Linux):** wrong file, other region, other game, truncated, modified, already
  patched, read-only folder and "(2)" naming all behave as designed. A hard kill mid-build used to leave a temporary
  file that blocked the next run; that is fixed and re-tested.
- **Real window (Linux AppImage, under Xvfb):** a non-disc file is refused with nothing written; the clean ISO
  produces the expected file (hash match); closing the window mid-build quits within a second with no leftover.
- **Windows cross-build check:** `sorapatch-cli.exe` passed the same checks under Wine with a synthetic release.
- Still to test: the native file picker, drag and drop and "Open folder" on real desktops, and one full run of each
  Windows and macOS build on its own OS.

## 5. Building

Core, CLI and tests (any OS with Rust 1.80 or newer):

```sh
cd tools/installer && cargo test && tests/run_synthetic.sh
```

The app window on Linux is built in a Docker box (`app/Dockerfile`, Ubuntu 22.04, so the AppImage runs on 22.04 and
newer) with the Tauri CLI: `cargo tauri build --bundles appimage`. Pick the embedded release with
`SORAPATCH_RELEASE_DIR=<folder with release.json and patch.vcdiff>`; the default is the synthetic test release.
In the app repository, GitHub Actions builds Windows (installer and portable exe), macOS (Apple Silicon and Intel,
`.dmg`) and Linux (AppImage), each with the licence text, a source link and checksums.

## 6. First start of an unsigned app

Version 1 ships unsigned (signing costs money and ties a real name to a fan mod):

- **Windows:** "Windows protected your PC" → **More info → Run anyway**. Browsers may also say "not commonly
  downloaded" → Keep.
- **macOS:** the first open is blocked → **System Settings → Privacy & Security → Open Anyway** (on older macOS,
  right-click the app → Open). If it says the app "is damaged":
  `xattr -dr com.apple.quarantine "/Applications/Sora Fan Patch.app"`.
- **Linux:** allow the AppImage to run (file properties, or `chmod +x`). Some distros need `libfuse2`.

## 7. Licence

The EBOOT decryption in the app (`core/src/pspcrypt.rs`, also in `tools/installer/` here) is a fresh Rust port of the type-2
~PSP decryption path from **pspdecrypt** (GPL-3.0), whose PRX code comes from **PPSSPP** (GPL-2.0-or-later) and whose
KIRK engine is **libkirk** (GPL-3.0-or-later). All three allow combination under GPL-3.0-or-later, so the core, the
CLI and the app are **GPL-3.0-or-later**. Their dependencies (RustCrypto, serde, fs4, Tauri) are MIT/Apache-2.0 and
compatible. Every download ships the GPL text and a link to the exact source. The release data (patch and
`release.json`) is our own content and is kept separate from the program. The rest of this research repository is
MIT ([LICENSE](../LICENSE)); `tools/installer/` keeps GPL-3.0-or-later.

## 8. Dependency note: glib advisory GHSA-wrw7-89jp-8q8g

The Linux build pulls in glib 0.18 through Tauri 2's GTK3 stack. The advisory affects `VariantStrIter` only; no
fixed 0.18 release exists, and moving to glib 0.20 means GTK4 (Tauri 3). Neither our code nor any dependency in the
lock calls the affected API, so it is recorded as **not reachable** and re-checked at every release. Windows and
macOS builds contain no glib.

## 9. Measured numbers (release 1.0 build)

- **Patch size.** `tools/pkg/make_release.py` encodes with `xdelta3 -e -9 -S none -B 2147483648` (one source window
  for the whole disc). That gave 15.6 MB for the release layout; the default 64 MiB window gave 20.4 MB and stored
  617 KB of unchanged game bytes as new data, because edited files sit far from their originals. The format 2
  (decrypt-on-the-player's-machine) patch is 14.7 MB; the EBOOT part of it is 1,885 bytes of our own changes, with
  0 bytes of the game's EBOOT stored.
- **Speed and memory.** The command-line tool built the full result from a clean disc in about 150 s with about
  33 MB of memory. On a 256 MB synthetic disc: check 2.4 s, build 3.2 s, final flush 4.5 s, peak memory 49.6 MB.
- **App sizes.** Linux AppImage about 95 MB (it carries WebKitGTK 4.1, built on Ubuntu 22.04 so it runs on 22.04 and
  newer); the inner program is about 21 MB. A Windows cross-build check made a 5.3 MB GUI exe and a 560 KB
  `sorapatch-cli.exe`, which passed the real-release checks under Wine; the shipped Windows builds come from CI.
- **Why not DJW compression.** `-S djw` patches were 16 % smaller on synthetic data, but the app refuses them
  (`E-PATCH`); with the whole-disc window the plain patch was small enough, so no extra decoder was added.

## 10. CI and release lessons

The app repository's workflow (`.github/workflows/build.yml`) runs `test` (cargo test, the synthetic suite, the
strings check) → `release-data` (downloads the release zip given as input, checks its SHA-256 and that it holds
only `release.json`, `patch.vcdiff` and `README.txt`; without input it uses the synthetic release) → a `build`
matrix (Windows NSIS setup and portable exe, macOS arm64 and x64 `.dmg` with an ad-hoc signature, Linux AppImage).
Rust and the Tauri CLI are pinned and builds run `--locked`. Every artifact carries `LICENSE.txt`, `SOURCE.txt`
(the exact commit) and `SHA256SUMS.txt`.

Lessons from shipping 1.0 (more in [notes/release-1.0-lessons.md](../notes/release-1.0-lessons.md)):

- GitHub renames release assets (spaces become dots, brackets are dropped), so the checksum file must use the
  GitHub names; the attach step now renames before hashing.
- A release event runs the workflow files as they are at the **tag**, not at `main`.
- In a public repository, workflow artifacts can be downloaded by any logged-in user, so a run with the real
  release data makes the patch downloadable before launch.
- A hard kill mid-build once left a hidden temporary file that made the next run fail with "We can't save in this
  folder"; the app now removes only its own temporary files after 10 minutes without activity, and the window
  cancels and cleans up when closed mid-build.
