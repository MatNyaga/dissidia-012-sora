# Chapter 14 — DLC and adding more fighters

What we learned on 2026-10-18 about the game's own DLC system, the plan for adding fighters after Sora as
self-contained "packages", and what Phases 0, 1 and 2 built (§14.5-§14.7, updated 2026-10-22). Full research:
[notes/dlc.md](../../notes/dlc.md). Plans: the Phase 0 and Phase 1 plans (private working
files), [PHASE2-PLAN.md](../PHASE2-PLAN.md). Status of every phase:
[ROADMAP.md](../ROADMAP.md).

---

## 14.1 The game's own DLC (what it can and can't do)
- At every boot the menu program asks the memory stick for **296 files**: 256 "costume" files, 20 music files and
  20 music-name files (plus one Aerith check). Those are the `…/ULUS10566/<8 hex>.edat FILE NOT FOUND` lines in
  the PPSSPP log.
- The 8 hex digits are the **CRC-32 of an internal path** (same hash as the disc file index, `pkghash.py`), e.g.
  `dlc/obj/dlc_000oe.bin` → `a590d742.edat`.
- **Costume files** overwrite one existing model-table row and make the game load that costume's model/costume
  files from the memory stick. The battle file of a fighter always comes from the disc.
- **Music files** add new tracks (up to 256) with names.
- Files are encrypted EDATs; because our EBOOT is already plain, the checks can be patched to read plain files.
- **It can't add a fighter**: no new owners, moves, voices, text, menus or unlock flags.

## 14.2 Why "one more fighter" was hard (2026-10-18)
Everything for Sora was built by ~61 guarded scripts, ~20 of which patch game code with "owner == 33" checks.
A second fighter hits walls (how each was solved: §14.6-§14.7):
- **Disc file index:** 74 free entries (Sora used 136).
- **Code space:** the battle-overlay cave and the dead EBOOT functions are used; ~30 loose words left.
- **Select grid:** 32 cells + random, all used (Sora took Chaos's row).
- **One-extra tables:** character face panel, Records (32), saved fighter records (friend-card slot), start
  equipment presets, unlock table (1 row left), 32-bit unlock/item/AI masks (owner 34 shares Garland's bit),
  player icons (3 left), model table (21 rows spare; a full fighter needs ~9–12).
- **Free owner numbers:** 34 (Cosmos's number, not playable) is like 33 was; 35 fits one of the two save stat
  blocks; 36+ need save changes. Owner 23 is Chaos (story boss), not free. → **2–4 extra fighters** realistic.

## 14.3 The package plan
1. **Engine patch, once:** our own code module (`EXTRA.PRX`, loaded at boot by the game's own module loader like
   `libfont.prx`, written in C), a per-fighter **registry** (feature flags + parameters per owner instead of
   "owner == 33"), an **extra file index/container** (fixes the 74-file wall), generic menus/save/Records/names.
2. **Package per fighter:** a folder with a manifest (owner, key, names, ids) + all its files + its table rows +
   one registry row. A single installer merges packages into the ISO (memory-stick loading later, optional).
3. A new fighter then costs mostly art/sound work (model, animations, effects, voices) — the same work either way.

| phase | what | effort |
|---|---|---|
| 0 | probes: toolchain, module load, free RAM, owner 34, grid, plain DLC, extra index, registry spec | 1–2 days |
| 1 | one installer from a manifest; rebuild Sora as a package, byte-identical | 3–5 days |
| 2 | generic engine patch (module, registry, extra index, generic menus/save) | 5–10 days |
| 3 | bigger select grid | 2–5 days (least known) |
| 4 | optional memory-stick DLC loading | 3–6 days |

## 14.4 "Full Sora quality" checklist for any new fighter
Model + outfits (cosx/exex per outfit) · moveset (plya/comb/atkp/magi) · effects (keep the 3 effect-file rules from
Chapter 6) · EX Mode (weapon, damage flag, speed, special guard) · EX Burst (vanilla controller = no code, or a
behaviour module like TRI) · CPU AI (brain row, brat, styles, reactions) · assist version · own equipment (+ level
scaling, effects) · voice bank, battle lines, vs-lines both ways, title call, subtitles · every menu (grid,
portraits, faces, icons, HUD, Customization pages incl. command charts, Battle Tips, EX Mode page, Museum + 3D
viewer, Records, Friend Card, PP Catalog purchase/icons/avatar/BGM, Labyrinth, Shop, character panel) · music
(BGM rows + owner-bit auto music) · save data (owner-indexed stats, unlock flags). `notes/dlc.md` §2–3 says for
each item whether it is package data, a generic hook, or behaviour code.

## 14.5 Phase 0 results (2026-10-18)
All nine probes answered; full table in `notes/dlc-phase0.md` §Summary.
- **Toolchain:** PSP C compiler works (pspdev in a docker container).
- **Own code module:** `EXTRA.PRX` loads at boot through the game's own module loader and keeps running in menus and
  battles (PPSSPP); a missing file is harmless. ~240 KB free block for it after boot.
- **Extra file index:** one RAM-patched word lets `EXTRA.IDX` answer file lookups first → the 74-file wall is gone,
  and the game's own index can go back to the original bytes.
- **Owner 34:** usable like 33; only Cosmos's model id 1338 collides (use lower ids). Story check still to do.
- **Grid:** 34 cells per page → exactly one more fighter; more need an L/R page (code).
- **Plain DLC files:** read from the memory stick (PPSSPP; 7-word patch for a real PSP).
- **Data Install:** a cache keyed by index position, not a delivery route; the level-3 bug on the Sora disc is fixed.
- **Registry spec:** `tools/dlc/owner_tables.json` lists all 89 per-fighter places;
  `python3 -I tools/dlc/owner_tables.py --owner 34` prints what a new fighter on owner 34 needs.
- **Still open:** real-PSP runs (module, plain DLC, RAM hook), the Cosmos story check, DLC stage B.

## 14.6 Phase 1 results (2026-10-18 to 2026-10-20)
- **Sora became a package** (`packages/sora`): cut from the reference build by `tools/pkg/extract.py`, and
  `tools/pkg/pkgapply.py verify` proves it reproduces that build's content from the clean disc.
- **One installer** (`tools/pkg/install.py`) puts packages onto the clean disc. **Layout B** keeps the game's own
  file list untouched and serves Sora's files through `EXTRA.IDX`: the 74-file wall is gone and Data Install keeps
  working.
- **Release 1.0** shipped on 2026-10-20 as a VCDIFF patch inside a patch app (Chapter 10 §10.7).
- Lessons from the release tests, for every future fighter: [notes/dlc.md](../../notes/dlc.md) §F (for example:
  every per-owner table needs a row for every package owner; PPSSPP hides the missing row, the Vita crashes).

## 14.7 Phase 2: the engine (since 2026-10-19)
Goal: no "owner == 33" left in the game code; a new fighter = a package + one registry row. Done so far:
- **The engine module** `EXTRA.PRX` (C) runs Sora's behaviour (EX run, Trinity Limit, Reflect, item effects and
  menus) through a fixed stub table; without the module the game is vanilla (P2.4). Code room is no longer a wall.
- **Lookups** (names, pictures, Museum, Original Quest face, unlock gates) read small per-owner tables the installer
  writes (P2.3).
- **Save records** for any package fighter: slot = 57 − owner (P2.5).
- **Capacity:** the grid rows moved to a new home with room for a 34th cell; one generic writer computes every
  installer number; the title call is generated (P2.7).
- **In progress:** Sora rebuilt as package #1 on the engine, installer layout C (P2.8). **Next:** a throw-away test
  fighter on owner 34 (P2.9).

How the engine works, step by step: [Chapter 15 — The engine and the registry](15-engine-and-registry.md).
The architecture on one page: [modding/OVERVIEW.md](../modding/OVERVIEW.md). Making a fighter today, with the known
limits for fighter #2: [modding/MAKE-A-FIGHTER.md](../modding/MAKE-A-FIGHTER.md). How changes are checked:
[modding/TESTING.md](../modding/TESTING.md).

Back to [00 — Start here](00-START-HERE.md) · [13 — Open questions](13-open-questions.md)
