# Architecture and folder map

A short technical tour. For the same story in plain words, read [GUIDE.md](GUIDE.md).

## The game disc

The disc image holds ISO9660 file records, `PACKAGE_INFO.BIN` (an index sorted by file-name hash) and `PACKAGE.BIN`
(the file data). Each index row gives a file's sector offset, size and Data Install tier. `pkg_get.py`, `pkg_put.py`,
`pkg_add.py` and related tools find, replace and append files. The patched ISO is always a local build output.

## Sora's roster spot

Sora uses roster owner **33** and the file key `sev120`. The bootstrap script copies Cloud's structures as a starting
point, gives owner 33 its own ability, save, name and voice resources, and restores the Cloud files that early
experiments had changed. `build_sora.sh` then runs every feature patcher in a fixed order. Don't reorder its last
steps (events, assist, sound IDs, music, NEW tag, the `grwp` row and menu clock, install tiers) without a good reason; later steps depend on them.

## Model and animation

Model conversion resizes Cloud's skeleton to Sora's proportions, converts GMO to glTF for mesh fitting, attaches the
Keyblades, converts back to GMO, then retargets and bakes KH2 animation clips onto it. `tools/poses/` holds hand-made
pose recipes. A motion must last at least as long as the move's script events, or the character stays stuck in the
last pose.

## Combat and effects

Combat changes touch the ability and action tables, hit definitions and event scripts. EX Mode and Reflect use
guarded code edits and shared code areas. Effects reuse the game's FEP resources, which are sensitive at run time:
alignment, node serial numbers, vertex limits and memory budgets all matter. A file that is structurally valid can
still fail in battle, so effects always need an in-game test.

## Folder map

| Path | Purpose |
|---|---|
| `tools/scripts/` | Format tools, conversion helpers and feature patchers |
| `tools/poses/` | Hand-made animation recipes |
| `tools/codex/` | Helper scripts from Codex deliveries that build scripts read (one folder per delivery) |
| `tools/dlc/` | PSP module probes, toolchain wrapper, owner-table registry |
| `tools/pkg/` | Package schema, validator, extractor, installer, release maker, equivalence checker and the engine module |
| `tools/kh2bake/` | Small .NET programs for baking KH2 animations (OpenKH DLLs not included) |
| `tools/installer/` | Early copy of the patch app (GPL-3.0-or-later): Rust core and CLI, Tauri window, synthetic tests |
| `tools/repository/` | Checks that need no game files, and an input inventory |
| `manifests/` | Hashes and selection metadata only |
| `docs/` | Guides and technical specs; `docs/learn/` = the learning path, `docs/modding/` = the modding layer |
| `notes/` | Research notes (reviewed subset); `notes/phase2/` = one note per Phase 2 step |
| `dumps/`, `kh2_export/` | Your own local game files and build outputs; ignored by Git |

## Engine module and packages

The engine module `EXTRA.PRX` is loaded at boot and looks up an extra file index (`EXTRA.IDX`) before the game's own
index. That lets the release disc keep the game's index exactly as shipped while still finding Sora's files. Details:
[ENGINE.md](ENGINE.md). The package format that describes everything a fighter adds is in
[PACKAGE-FORMAT.md](PACKAGE-FORMAT.md). The Phase 2 engine (a stub table in the EBOOT, the registry `EXTRA.REG`
and Sora's behaviour in the module) is described in [modding/OVERVIEW.md](modding/OVERVIEW.md) and ENGINE.md; most
of its sources are not in this snapshot yet ([list](REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot)).
Status: [roadmap](ROADMAP.md).

## Patch app

The patch app streams a VCDIFF patch over the player's own ISO, checks the input and the result by SHA-256, and never
changes the original file. The Rust core and CLI build on their own, so their tests don't need a desktop toolkit. See
[INSTALLER-TECH.md](INSTALLER-TECH.md). No game patch is included in this repository.
