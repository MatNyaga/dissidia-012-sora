# Sora for Dissidia 012: research, tools and the fighter engine

This is a fan project that adds **Sora** (from Kingdom Hearts II) as a new playable fighter to **Dissidia 012
duodecim Final Fantasy** for the PSP (US disc, ULUS-10566). It is also building an **engine**: a one-time set of
changes to the game so that more new fighters can be added later as self-contained **packages**, without new game
code for each one.

This repository holds the **research side**: the scripts, notes, specs and guides used to build the mod. If you only
want to play, you don't need anything here. Use the patch app instead (see [Where to start](#where-to-start)).

> No Dissidia files are included. Sora's model and sounds are fan-ported from Kingdom Hearts II.
> Fan-made, not affiliated with Square Enix or Disney.

New words are defined the first time they appear. All of them are in the [glossary](docs/learn/GLOSSARY.md).
The phases and their status are on one page: [docs/ROADMAP.md](docs/ROADMAP.md).

---

## What it is

- **The fan patch.** Sora plays like any other fighter: his own model and Keyblade, KH2 animations and combos, HP
  magic, EX Mode with a Reflect barrier, the Trinity Limit EX Burst, voice lines and subtitles, six outfits, his own
  items, an assist version, CPU behaviour, and entries in the Museum, Jukebox and Records. You unlock him in the PP
  Catalog.
- **His place in the game.** Every fighter has an **owner** number (the game's fighter number; most tables are
  indexed by it). Vanilla playable fighters are 1 to 32. Sora is **owner 33**, a hidden number the game only used for
  Aerith as an assist. Owner 34 (Cosmos's number, not playable) is the one more free number.
- **The engine.** Release 1.0 works because about 86 places in the game's code and tables say, in effect,
  "owner 33 = Sora". The engine replaces those places with generic ones: small per-fighter tables the installer
  fills in, a fixed jump table in the game's main program, and our own code module (`EXTRA.PRX`, written in C) that
  runs the special moves. A fighter then becomes a **package** (a folder with its files, its table rows and one
  registry row) that one generic **installer** adds to your own clean copy of the game.
  One-page picture: [docs/modding/OVERVIEW.md](docs/modding/OVERVIEW.md).

## Status (22 October 2026)

| | state |
|---|---|
| **Release 1.0** | **Out** since 20 October 2026: a patch app for Windows, macOS and Linux makes a new ISO from your own. Tested on PPSSPP (PC) and on a PS Vita (PSP mode, Adrenaline; turn off game plugins first). A real PSP is **not tested yet**. |
| Release 1.0.1 | A candidate exists (adds Sora's name on Quick Battle's "Opponent Info" screen). Not released. |
| Phase 2 engine | **Done:** file lookups and menus through per-fighter tables (P2.3), Sora's behaviour moved into the C module (P2.4), save records for any package fighter (P2.5), shared capacity such as the character grid rows (P2.7), the acceptance test kit (P2.10, static part). Each step was compared with a frozen reference disc (release 1.0 plus the 1.0.1 fix), in PPSSPP and, for the behaviour module, also on the Vita. |
| Sora as a package | **In progress (P2.8):** the engine is now a package of its own, Sora is package #1 on it, and the installer has a new "layout C" for it. First discs built 2026-10-22; testing is under way. |
| A second fighter | **Planned (P2.9):** a throw-away test fighter (a copy of Cloud) on owner 34, to prove that a second fighter needs no new fighter code. Then real fighters. |
| More than 34 grid cells, Memory Stick DLC | **Planned later** (Phases 3 and 4). |

Details per task: [docs/ROADMAP.md](docs/ROADMAP.md).

## What is new for this game

As far as we know, nobody had published new movesets or new roster slots for Dissidia 012 before this project.

- **A new roster slot.** Owner 33 became a full fighter with its own files, saved record, names, pictures and voices,
  instead of a skin over an existing fighter. Story: [docs/learn/02-a-fighter-and-slot-33.md](docs/learn/02-a-fighter-and-slot-33.md).
- **New moves.** New move recipes, attack pieces and hits, played with KH2 animations retargeted onto the game's
  skeleton. Story: [docs/learn/04-moves-and-combos.md](docs/learn/04-moves-and-combos.md).
- **Behaviour in a loadable module.** `EXTRA.PRX` is our own C module. The game's own module loader starts it at boot,
  next to the game's modules. If it is missing, the game runs as vanilla.
- **Our own file list.** `EXTRA.IDX` lets the game find the new fighter's files while the game's own file list stays
  exactly as shipped (so the game's Data Install keeps working).
- **Fighter packages and one installer.** A fighter is data, not a set of hand-written patches.

## Where to start

| I want to … | read |
|---|---|
| **play it** | Get the patch app from the [releases page](https://github.com/MatNyaga/sora-fan-patch/releases) (project page: <https://matnyaga.github.io/sora-fan-patch/>, source: <https://github.com/MatNyaga/sora-fan-patch>). You need your own US copy of the game as an `.iso`; the app checks it and makes a **new** copy with Sora, your original file is never changed. **Back up your save first.** Sora uses the space of friend card 25, so you can keep 24 friend cards. Going back to the original game with a Sora save is not supported; restore your backup. More: [docs/RELEASE-POLICY.md](docs/RELEASE-POLICY.md). |
| **understand how it works** | [docs/modding/OVERVIEW.md](docs/modding/OVERVIEW.md) (one page), then the learning path [docs/learn/00-START-HERE.md](docs/learn/00-START-HERE.md) (chapters 00-15, plus the glossary). The short tour: [docs/GUIDE.md](docs/GUIDE.md). |
| **make a fighter** | [docs/modding/MAKE-A-FIGHTER.md](docs/modding/MAKE-A-FIGHTER.md): what a package needs today, step by step, and the known limits for fighter #2. The tooling is still being finished (P2.8, P2.9). |
| **check a change** | [docs/modding/TESTING.md](docs/modding/TESTING.md): the checks, from the ones that need no game files to the PS Vita. |
| **rebuild from source** | [docs/SETUP.md](docs/SETUP.md), [docs/ASSETS.md](docs/ASSETS.md) and [docs/REPRODUCIBILITY.md](docs/REPRODUCIBILITY.md) (every outside input, and what is still missing). |
| **help** | [docs/modding/CONTRIBUTING.md](docs/modding/CONTRIBUTING.md): sharing rules, naming, how to report a finding. Bug reports: [CONTRIBUTING.md](CONTRIBUTING.md). |
| **find a document** | [docs/README.md](docs/README.md): every doc, grouped by audience. |

## What's in this repository

This is a **source-only snapshot** of the research project: code first exported on 18 October 2026 and refreshed on
20 October 2026 to match release 1.0; the docs for modders, the learning path and a reviewed subset of the research
notes (including the Phase 2 engine findings) were added on 22 October 2026. It's useful if you want to learn how the
mod works or build on it. It is **not** a ready-to-run build kit.

| folder | what is in it |
|---|---|
| `docs/` | guides and specs; `docs/learn/` (the learning path), `docs/modding/` (the modding layer) |
| `notes/` | research notes: exact addresses, layouts, test results ([notes/README.md](notes/README.md)); `notes/phase2/` has one note per Phase 2 step |
| `tools/scripts/` | the build scripts and the per-feature patchers for roster spot 33 (Sora) |
| `tools/poses/` | hand-made animation recipes (intro, win and loss poses) |
| `tools/kh2bake/` | small C# programs that turn KH2 animations into frame data |
| `tools/pkg/`, `tools/dlc/` | the fighter package format, the engine module (v1), the installer, the release maker and research probes |
| `tools/installer/` | an early copy of the patch app (GPL-3.0-or-later; the maintained app lives in its own repository) |
| `tools/codex/` | helper scripts from Codex deliveries that the build reads (one folder per delivery) |
| `tools/repository/` | checks that run without any game files |
| `manifests/` | metadata only (hashes and selections), no game files |

Never in this repository: game discs, files from them, decompiled game code, packages (they hold data derived from
the game), test discs, saves. To rebuild the mod you also need your own game files, your own KH2 files and several
outside tools; a few helper scripts and most Phase 2 tools are not in this snapshot yet.
[Reproducibility](docs/REPRODUCIBILITY.md) lists everything, including the
[Phase 2 tools not published yet](docs/REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).

Quick check that needs no game files:

```sh
bash tools/repository/smoke.sh
```

## Rules for sharing

- **Patch only.** We share only our own changes: a patch (a VCDIFF delta against the clean disc) and our own tools.
- **Own disc only.** The patch works on your own, unmodified US ISO: ULUS-10566, 1,754,529,792 bytes, SHA-256
  `df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e`. Other regions are not supported.
- **No game files, ever.** No ISO, no EBOOT (encrypted or decrypted), no files extracted from the disc, no
  decompiled game code, and no `packages/` folder (packages hold data derived from the game: they are installed from
  your own disc, never published raw).
- Details and the reasons: [docs/modding/CONTRIBUTING.md](docs/modding/CONTRIBUTING.md).

## Licence and credits

- Built by Mat with help from AI tools (Claude, Codex).
- No Dissidia files are included. Sora's model and sounds are fan-ported from Kingdom Hearts II.
  Fan-made, not affiliated with Square Enix or Disney.
- This research repository is under the [MIT License](LICENSE), except `tools/installer/`, which is a copy of the
  patch app and stays GPL-3.0-or-later ([tools/installer/LICENSE](tools/installer/LICENSE)) because it contains code
  ported from pspdecrypt and libkirk. The maintained patch app is in
  [its own repository](https://github.com/MatNyaga/sora-fan-patch).
- `tools/scripts/kh2_mdlx2gltf.py` has a model decoder adapted from [OpenKH](https://github.com/OpenKH/OpenKh)
  (Apache-2.0, commit 7a3b945). Thanks to the OpenKH team.
- Tools we rely on: [OpenKH](https://github.com/OpenKH/OpenKh) (KH2 extraction and its animation emulator),
  [Ghidra](https://ghidra-sre.org/) with [ghidra-allegrex](https://github.com/kotcrab/ghidra-allegrex),
  [PPSSPP](https://www.ppsspp.org/), pspdev (the PSP C compiler), pspdecrypt and libkirk (EBOOT decryption, ported
  into the patch app), vgmstream, atracdenc, xdelta3, Blender and Tauri. They keep their own licences and are not
  included here. Thanks to everyone behind them.
- Dissidia 012 Final Fantasy and Kingdom Hearts II belong to their owners. This is a non-commercial fan project.
- How the project started (the first stage plan): [docs/history/ORIGINAL-PLAN.md](docs/history/ORIGINAL-PLAN.md).

---

AI coding assistant or new contributor? Read [AGENTS.md](AGENTS.md) first.
