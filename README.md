# Sora for Dissidia 012: research and tools

This is a fan project that adds **Sora** (from Kingdom Hearts II) as a playable fighter to
**Dissidia 012 Final Fantasy** for the PSP (US version, ULUS-10566).

This repository holds the **research side**: the scripts, notes and specs used to build the mod. If you only want to
play, you don't need anything here. Use the patch app instead (see below).

> No Dissidia files are included. Sora's model and sounds are fan-ported from Kingdom Hearts II.
> Fan-made, not affiliated with Square Enix or Disney.

## Status (October 2026)

- **Sora is playable** in his own roster spot (#33, bottom row of the character select). He has his own model,
  Keyblade, KH2 animations, combos, magic, EX Mode with a Reflect barrier, a Trinity Limit EX Burst, voice lines,
  six outfits, Sora-only items, an assist, CPU behaviour, and entries in the Museum, Jukebox and Records.
  You unlock him in the PP Catalog.
- **Release 1.0 is coming.** Release candidate 3 is being built and checked now.
- **Tested on:** PPSSPP on PC, and a PS Vita running PSP games through Adrenaline (turn off game plugins in
  Adrenaline first). A real PSP has **not** been tested yet.
- **Next goal:** "Phase 2", a multi-fighter engine so more new fighters can be added without new game code for each
  one. See the [roadmap](docs/ROADMAP.md).

## Playing the mod

The mod comes as a **patch only**. You need your own copy of the game as an `.iso` file. The patch app checks the
file, then makes a **new** copy with Sora in it. Your original file is never changed.

- Patch app (source code, GPL-3.0): <https://github.com/MatNyaga/sora-fan-patch>
- Downloads, once 1.0 is out: <https://github.com/MatNyaga/sora-fan-patch/releases>
- Project page (coming soon): <https://matnyaga.github.io/sora-fan-patch/>

Before you play, **back up your save**. Sora's progress uses the space of friend card 25, so the friend-card limit
becomes 24. Going back to the original game with a save used with Sora isn't supported; restore your backup instead.

## What's in this repository

This is a snapshot of the research source code, exported on 18 October 2026. It's useful if you want to learn how
the mod works or build on it. It is **not** a ready-to-run build kit.

- `tools/scripts/`: the build scripts and the per-feature patchers for roster spot 33 (Sora).
- `tools/poses/`: hand-made animation recipes (intro, win and loss poses).
- `tools/kh2bake/`: small C# programs that turn KH2 animations into frame data.
- `tools/pkg/` and `tools/dlc/`: the fighter package format, the engine module and research probes.
- `tools/installer/`: an early prototype of the patch app (the maintained app lives in its own repository).
- `tools/repository/`: checks that run without any game files.
- `manifests/`: metadata only (hashes and selections), no game files.
- `codex/inbox/`: helper scripts that the build still reads from this folder (to be reorganised).

To rebuild the mod yourself you also need your own game files, your own KH2 files and several outside tools. These
are not included, and a few helper scripts are still missing from this snapshot. [Reproducibility](docs/REPRODUCIBILITY.md)
lists everything. Newer tools (the package installer, the release maker and the Phase 2 tools) will come with a
later export.

Quick check that needs no game files:

```sh
bash tools/repository/smoke.sh
```

## Docs

**Start here**
- [How the mod works](docs/GUIDE.md): the whole process in plain words.
- [Roadmap](docs/ROADMAP.md): what's done, what's left for 1.0, and the Phase 2 plan.
- [Architecture and folder map](docs/ARCHITECTURE.md).

**Building and testing**
- [Setup and build](docs/SETUP.md)
- [Reproducibility](docs/REPRODUCIBILITY.md): every outside input and what's still missing.
- [Assets and sources](docs/ASSETS.md): what we never put in Git, and why.
- [Testing](docs/TESTING.md) and [Troubleshooting](docs/TROUBLESHOOTING.md)
- [Audio](docs/AUDIO.md)

**Technical specs**
- [Engine module (EXTRA.PRX)](docs/ENGINE.md)
- [Fighter package format](docs/PACKAGE-FORMAT.md)
- [Patch app technology](docs/INSTALLER-TECH.md)

**Contributing**
- [Contributing](CONTRIBUTING.md) and [notes for AI coding assistants](AGENTS.md)

## Licence and credits

- No licence has been chosen for this research repository yet. Until one is added, please ask Mat before reusing
  code from it. The patch app is GPL-3.0-or-later in [its own repository](https://github.com/MatNyaga/sora-fan-patch).
- Outside tools used along the way keep their own licences and are not included here: OpenKH, PPSSPP,
  pspdecrypt, libkirk, vgmstream, atracdenc, xdelta3, Ghidra, Blender and Tauri. Thanks to everyone behind them.
- Built by Mat with help from AI tools (Claude, Codex).
- Dissidia 012 Final Fantasy and Kingdom Hearts II belong to their owners. This is a non-commercial fan project and
  is not affiliated with Square Enix or Disney.
