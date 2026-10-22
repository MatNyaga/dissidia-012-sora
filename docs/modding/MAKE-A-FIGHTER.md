# Make a fighter

What a new fighter package needs today, step by step, as far as the tools are real. Read
[OVERVIEW.md](OVERVIEW.md) first. Terms: [glossary](../learn/GLOSSARY.md#phase-2-engine-and-package-terms).

> **In progress until P2.8 / P2.9 land.** Today exactly one fighter package exists on the engine: Sora
> (`packages/sora-C`). It was not written by hand: it was cut from a reference disc (built by Sora's old scripts)
> and then re-keyed into format 1.1. A second fighter has not been installed next to Sora yet. Task P2.9 does that
> with a throw-away test fighter (a Cloud copy on owner 34) and will turn this page into a tested recipe. Until then,
> the steps below say what the format and the tools expect, and each step says how real it is.
> Status: [ROADMAP.md](../ROADMAP.md).

> **Tools in this repository.** Many tools named on this page (the acceptance kit `tools/qa/`, the engine v2
> sources and step builders, `pkg11.py`, `rowgen.py`, the registry sources) are in the private working project and
> **not published here yet**: [list](../REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot). The commands show how
> the work is done; the ones you can run from this clone are marked there.

---

## What a fighter is made of

| part | what | where it goes |
|---|---|---|
| **files** | battle file (`obj/p_<key>.objx`: moves, hits, effects, sounds), models per outfit (`obj/P_<KEY>_1P.gmo` + `.cosx` + `.exex`), voice bank and line list, menu pictures (`.gim`), optional music (`DATA/BGM/*.AT3`) | `files/package/<PACKAGE path>`, `files/iso/<ISO path>` |
| **rows** | small edits inside game files that every fighter shares: ability table, level tables, text lists, model table (`objentry`), CPU AI rows, Museum and PP Catalog rows, voice lists of other fighters | `rows/<owner_tables id>.json` |
| **registry source** | the fighter's numbers and switches: owner, name index, record slot, pictures, feature bits, items, flags, install fields | `registry.json` |
| **manifest** | identity (owner, key, names), `requires` the engine, every number it takes from a shared space, the file list with sha256 | `manifest.json` |

A real example: `packages/sora-C` has 36 rows files (from `ability_text.json` to `vold_lists.json`), a
`registry.json`, and files for models, voices, pictures and three music tracks.

The full checklist of what Sora has (and so what a "full quality" fighter has) is in
[learn/14-dlc-and-more-fighters.md](../learn/14-dlc-and-more-fighters.md) §14.4 and [notes/dlc.md](../../notes/dlc.md) §2.

---

## Step 1: pick the owner number and the key

- **Owner:** only **34** is free (Cosmos's number; Cosmos is never playable). 33 is Sora. The registry checker
  refuses owners above 34 (they need Phase 3 work).
- **Key:** a 6-letter file key, like the game's own (`sev100` = Cloud, `sev120` = Sora). The test fighter uses
  `tst034`. File names follow it: `obj/p_tst034.objx`, `obj/P_TST034_1P.gmo`.
- **Record slot:** fixed by the owner: slot = 57 − owner. Owner 34 → slot index 23 (the 24th friend card's space).
  With Sora and a second fighter, players keep 23 friend cards.

*Real today:* yes (rules enforced by `tools/dlc/registry.py`).

## Step 2: make the files

Start from a vanilla fighter's files and change them. Sora started as a copy of Cloud's files. The methods are in
the learning path: models and animations [chapter 3](../learn/03-model-skeleton-animation.md), moves
[chapter 4](../learn/04-moves-and-combos.md), sounds [chapter 5](../learn/05-sounds-and-voices.md), effects
[chapter 6](../learn/06-visual-effects.md), menus [chapter 8](../learn/08-menus-and-abilities.md).

The file list for a Cloud-based fighter is in [P2.9-testfighter.md](../../notes/phase2/P2.9-testfighter.md) §4.1.

Watch out:
- **Everything with an id clashes when copied.** A copied battle file keeps the source fighter's effect-package id
  and sound-bank ids. Then the copy and the original cannot meet in one battle. Give the copy its own ids (free ones
  are in `tools/dlc/id_spaces.json`) or never test that match-up. Story: [learn/12-lessons-learned.md](../learn/12-lessons-learned.md) §B.
- **Effect files must never grow** and have alignment rules ([learn/06-visual-effects.md](../learn/06-visual-effects.md) §6.4, §6.10).
- **The model has a memory budget** ([learn/03-model-skeleton-animation.md](../learn/03-model-skeleton-animation.md) §3.10).

*Real today:* the methods are proven on Sora. The scripts in `tools/scripts/spot33_*.py` are written for owner 33
and edit a disc, not a package: use them as worked examples, not as a pipeline for a new fighter.

## Step 3: take your numbers

A fighter takes numbers from shared spaces: unlock and purchase flags, model-table ids, effect ids, sound banks,
picture numbers, text entries.

| space | where to look | rule |
|---|---|---|
| flags | `tools/dlc/flag_map.json` | package flags come from the pool **3200-3455** (fighter #2: 3200-3207). Never use a flag the game itself writes (the map lists them). |
| model-table (`objentry`) ids | `tools/dlc/id_spaces.json` | free ids below 1338 (Cosmos's rows start at 1338); the test fighter uses 1335-1337 |
| effect ids, sound banks | `tools/dlc/id_spaces.json` | reserved per owner (owner 34: effect package 3147, sound banks from 220000) |
| per-table checklist | `python3 -I tools/dlc/owner_tables.py --owner 34` | prints every per-fighter table and what owner 34 needs there (DATA, ALLOC, FULL, CODE …) |

*Real today:* the maps exist. The allocator script that picks numbers for you (`allocate.py`, task P2.6) is **not
written**; pick by hand and let the checker in step 4 catch clashes.

## Step 4: write the registry source

Copy `tools/dlc/registry/test34.json` (the test fighter's placeholder). Every field is a pair
`[value, "where this value comes from"]`, so a reviewer can check it. The groups:

- `row`: owner, `name_index`, `record_slot`, `museum_record`, picture slots, Original Quest name/face/banner,
  `burst_ctl` (which EX Burst controller), `ex_run_mult`, `key`, `features` (the switches, e.g. `PKG_FLAGS`,
  `RECORD_SLOT`; Sora also has the behaviour features).
- `items`: items the fighter owns, their effects.
- `flags`: every flag and its use.
- `install`: what the installer writes into the game's own tables: `objentry_ids`, `unlock_flag`, `seen_flag`,
  `qb_row: "append"` (a new grid row), `title_call {sqe, ddd, days}`, `start_preset`, `jukebox_group`,
  `records_append`, `record_mark`, and more.

Check it together with Sora's, so clashes show:

```
python3 -I tools/dlc/registry.py validate tools/dlc/registry/sora.json tools/dlc/registry/test34.json
python3 -I tools/dlc/registry.py build tools/dlc/registry/sora.json tools/dlc/registry/test34.json -o OUT.EXTRA.REG
python3 -I tools/dlc/registry.py decode OUT.EXTRA.REG
```

Exit code 1 = an error (warnings never fail). `--disc ISO` also checks the values against a disc.

*Real today:* yes. In a format-1.1 package this file becomes the package's `registry.json`.

## Step 5: build the package folder (format 1.1)

```
packages/<id>/
  manifest.json      id, kind "fighter", owner, key, format_version "1.1", requires engine >= 2.5.0,
                     distribution "never-publish-raw", allocations, files, inventory, package_sha256
  registry.json      step 4
  files/package/...  whole files served through EXTRA.IDX
  files/iso/...      loose ISO files (music)
  rows/<id>.json     row edits, one file per shared table, keyed by identity (owner, text entry, model id, picture id)
```

Spec: [PACKAGE-FORMAT.md](../PACKAGE-FORMAT.md) (§1 layout, §2 determinism, §6 allocations, §16 format 1.1 codecs).
Then seal and check:

```
python3 -I tools/pkg/pkgformat.py seal packages/<id>
python3 -I tools/pkg/validate.py --strict packages/engine packages/sora-C packages/<id>
```

`validate.py` with all packages together also checks the cross-package rules: no number taken twice, no file or row
edited twice, no overlapping code edits.

*Real today:* the format, the codecs (`tools/pkg/containers.py`), sealing and validation exist. There is **no
authoring tool** yet. Sora's package was made by `tools/pkg/extract.py` (reference disc minus clean disc) and
`tools/pkg/pkg11.py convert` (re-key to format 1.1). P2.9 will show how the test fighter's package is made.

## Step 6: install

Always try `--dry` first (computes everything, writes nothing):

```
python3 -I tools/pkg/install.py dumps/ULUS10566.iso dumps/ULUS10566-mine.iso packages/engine packages/sora-C packages/<id> --layout C --dry
python3 -I tools/pkg/install.py dumps/ULUS10566.iso dumps/ULUS10566-mine.iso packages/engine packages/sora-C packages/<id> --layout C
```

The installer refuses anything but the known clean dump, never overwrites an existing file, and builds the
per-fighter tables for the whole roster from the registry sources.

*Real today:* layout C installs engine + Sora (P2.8 step E3, 2026-10-22). Engine + Sora + a second package is the
P2.8 step E8 dry run and then P2.9. Not done yet.

## Step 7: test

See [TESTING.md](TESTING.md). In short: a profile file for your disc kind and `run_static.py` (no emulator), then
the emulator steps `runtime_plan.py` prints, with PPSSPP strict mode, then the five-minute check on a PS Vita.
Every menu that shows a fighter is checked with a vanilla fighter on the same screen as a control.

---

## Known limits for a second fighter

From [P2.7-capacity.md](../../notes/phase2/P2.7-capacity.md) §3 / §8 and [P2.9-testfighter.md](../../notes/phase2/P2.9-testfighter.md) §4.6.
Mat decided (2026-10-20, question Q-M1) that the test fighter may pass while missing the first five (Records list,
Characters panel, Museum, Jukebox list, Original Quest face); a **real** fighter must have them.

| limit | why | fix |
|---|---|---|
| No line in Museum → Records | the Records list arrays hold the vanilla fighters + Sora | about 40-60 code words + data; needed before a real fighter |
| No Characters panel cell | the panel layout has 31 cells | Phase 3 |
| No Museum character record | the test fighter has none | a real fighter adds its record (package data) |
| No Jukebox entry | the test fighter does not set it | a real fighter sets `install.jukebox_group: true`; the installer checks the list still fits |
| No Original Quest face unless set | needs the OQ icon picture and the `OQ_FACE` feature | the engine allows it for owner 34; P2.9 runtime check |
| No EX Mode page in Customization | the EX Mode page table is full | a new home for a 1.1 KB table + about 4 code words; needed before a real fighter |
| **34 grid cells per page** | one page = Sora + one more fighter. With both installed, the team-edit grids drop their "delete" cell. Mat accepted this (2026-10-22). | a second page, Phase 3 |
| **Title-call days** | only days 26 and 31 are free "second days"; fighter #2 takes one | Mat decided (2026-10-22): choose a shared-day table at fighter #3 |
| Start equipment preset | the preset buffer is full; `-1` = empty loadouts, and never use "reset to default" with it | data fix: rewrite Chaos's unused preset 78 |
| Shares Garland's equipment bit | owner 34 maps to Garland's bit in the game's 32-bit masks | handled by the module's item-owner table while `EXTRA.PRX` runs |
| Cosmos in story scenes | the game finds Cosmos's extra files by "owner 34, costume 1" | fix F6 (a 2-byte data change), needs one runtime check |
| Item ids | the item table stops at 683 | raising it is save-inventory work (separate task) |

## Read next

- How it is checked: [TESTING.md](TESTING.md). How to share and report: [CONTRIBUTING.md](CONTRIBUTING.md).
- The test fighter recipe in full: [P2.9-testfighter.md](../../notes/phase2/P2.9-testfighter.md).
- Lessons every new fighter must respect: [notes/dlc.md](../../notes/dlc.md) §F.
