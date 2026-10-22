# The engine: EXTRA.PRX, EXTRA.REG and the stub table

**Start here.** The current engine is **2.5.0** (`EXTRA.PRX` 26,682 B, sha256 `4e546662…`). It is installed with
**layout C**: the engine package plus the fighter packages, merged into a copy of the player's clean ISO. Layout C is
part of P2.8, which is **in progress** (first discs built and tested 2026-10-22). Release 1.0 still ships the v1
module (5,702 B, `e7e25242…`) with layout B. The one-page picture is [modding/OVERVIEW.md](modding/OVERVIEW.md);
words are in the [glossary](learn/GLOSSARY.md).

Some tools named here are in the private working project and not published yet:
[list](REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).

## Contents

This file has three parts: the v1 module as it ships in release 1.0, the v2 design (Phase 2), and the as-built
record of every Phase 2 step, oldest first. A later block overrides an earlier one where they differ.

1. **Module v1 (release 1.0):** [In plain English](#in-plain-english) · [Files](#files) ·
   [What the module does at boot](#what-the-module-does-at-boot-module_start) ·
   [Status block v1](#status-block-layout-v1-0x80-bytes-frozen-later-layouts-only-append) ·
   [API skeleton](#api-skeleton-phase-2-no-behaviour-in-v1) ·
   [EXTRA.IDX v1](#extraidx-v1-file-psp_gameusrdirdataextraidx-little-endian) ·
   [Installer](#installer-install_enginepy) · [Example test disc p14](#example-test-disc-p14) ·
   [Limits](#limits--open-points)
2. **v2 design (P2.1):** [Registry + stubs v2](#registry--stubs-v2-p21-design-2026-10-19-built-in-p23-p28) ·
   [design changes](#v2-design-changes--decided-2026-10-20-claude-on-mats-go-ahead-codex-review-still-welcome) ·
   [freed code ranges](#1-where-the-code-lives-freed-eboot-ranges-verified) ·
   [stub table (XSTB)](#2-stub-table-fixed-in-eboot-vanilla-safe) ·
   [registry lookups](#3-registry-lookups-eboot-helpers-no-module-needed-to-run-them) ·
   [registry row](#4-registry-row-v1-64-b-little-endian-file-rows-may-be-longer-readers-use-the-first-64-b) ·
   [feature ids](#5-feature-ids-extra_featureid-returns-a-bitmask-of-rows-using-it-0--off) ·
   [EXTRA.REG](#6-extrareg-v1-psp_gameusrdirdataextrareg-little-endian) ·
   [status block v2](#7-status-block-v2-append-only-v1-0x000x7f-unchanged-incl-tail-at-0x7c)
3. **As built, step by step:** [P2.2](#p22-notes-registry-builder-2026-10-19) ·
   [P2.4 steps 0 + 1](#p24-steps-0--1--as-built-claude-p24-step-1-helper-2026-10-21-pilot-report-8-folded-in) ·
   [P2.4 step 2](#p24-step-2--as-built-claude-p24-step-2-helper-2026-10-21-notesphase2p24-reflectmd) ·
   [P2.4 step 3](#p24-step-3--as-built-claude-p24-step-3-helper-2026-10-21-notesphase2p24-shieldmd) ·
   [P2.4 step 4](#p24-step-4--as-built-claude-p24-step-4-helper-2026-10-21-notesphase2p24-itemsmd) ·
   [P2.3 steps 3-7 (OXT)](#p23-steps-3-7--as-built-claude-p23-lookups-helper-2026-10-21-notesphase2p23-homemd--p23-picturesmuseumoqfaceflagsmd) ·
   [P2.5 (SRC1)](#p25--as-built-claude-p25-save-records-helper-2026-10-22-notesphase2p25-savesmd) ·
   [engine package](#engine-package-p28-design-2026-10-21-built-in-step-e1-2026-10-22) ·
   [P2.7 (GRD1)](#p27--as-built-claude-p27-capacity-helper-2026-10-22-notesphase2p27-capacitymd) ·
   [P2.8 E1-E3 (in progress)](#p28-e1-e3--as-built-the-engine-package-and-installer-layout-c-p28-in-progress)

## Module v1 (release 1.0)

Code: `tools/pkg/engine/`. This module ships on the Sora release disc. Earlier research steps are referred to by
short labels: **P0.2** proved the game can load our own module, **P0.3** measured free memory, and **P0.7** proved an
extra file index works. "Layout A" is the older disc layout (Sora's files added to the game's own index); "layout B"
is the release layout (the game's index untouched, Sora's files in our index). Version 2 (Phase 2) follows the v1
part.

## In plain English

- **What it is.** A small piece of our own code (5.7 KB) that the game loads at boot, next to its own two modules.
  Today it does one job: it lets the game find files that are listed in **our own file list** (`EXTRA.IDX`) instead
  of only the game's list (`PACKAGE_INFO.BIN`). That is what lets the release disc layout (layout B) keep the game's list
  exactly as Sony shipped it, while Sora's files are still found.
- **How it hooks in.** The game has one "find this file name" function. The module changes **one instruction** in
  it, in memory only (the disc's game code is not changed for this), so that our list is asked first, then the
  game's list. Before changing it, it checks the instruction is the original one (and copes with the emulator's
  JIT, a problem found during the P0.7 research).
- **It can't break the game.** Every check that fails — no list on the disc, a damaged list, not enough memory,
  someone else already changed that instruction, a row pointing outside the data file — means the module simply
  does nothing and the game runs as normal. It never writes any other game memory (the Phase-0 test words at
  0x089A8B14 are not used any more), has no background thread, and keeps all its state inside itself.
- **Safety rule for our list.** If our list contains a file that the game's own list already has, that is an
  **override** (we replace a game file). Overrides must be marked as intended in our list; an unmarked one is
  treated as a mistake and ignored (the installer refuses to write it in the first place).
- **How to see what it did.** It keeps a "status block" in memory with a fixed signature (`XTRA`). The tool
  `find_status.py` finds it through the emulator's debugger and prints everything in plain lines (loaded rows,
  rejected rows, hits, hook state, error reason).
- **Ready for Phase 2.** It already exposes an "API" block (`XAPI`) with an empty slot for the Phase-2 registry
  table and a feature switch that always says "off". Nothing uses it yet; it changes no behaviour.
- **Installing it** is one command (`install_engine.py`), which adds the module + our list to a disc and patches
  the game's module loader (the patch proven in P0.2). It can be run again safely, and it can undo itself (rollback).

## Files

The built and generated files in this table (`extra.prx`, `extra.layout`, `engine.json`, `patches/`) are not
committed in this snapshot; the build commands below make them. The export list `exports.exp`, which the Makefile
needs, is also missing from this snapshot.

| path | what |
|---|---|
| `tools/pkg/engine/extra/extra.c`, `exports.exp`, `Makefile` | module source (C + 18-word asm trampoline) |
| `tools/pkg/engine/extra/extra.prx` | built module (5,702 B, sha256 `e7e25242fa90eb07afe16ef6d606822ff377149b18ba25384257c637ebee7116`) |
| `tools/pkg/engine/extra/extra.layout` | symbol offsets + section sizes (from `psp-nm` / `psp-size`) |
| `tools/pkg/engine/engine.json` | module identity: size, sha256, status-block offset, symbols, sections |
| `tools/pkg/engine/patches/engine-loader.json` | EBOOT patch set (55 words: va/old/new + 8 context words) |
| `tools/pkg/engine/patches/extra_prx.json` | same edits in the [package format](PACKAGE-FORMAT.md) shape (`set: engine`, 53 changed words) |
| `tools/pkg/engine/make_manifest.py` | writes the three JSON files (`--check` = compare only) |
| `tools/pkg/engine/install_engine.py` | guarded installer / rollback |
| `tools/pkg/engine/xidx.py` | EXTRA.IDX build / parse / check (same rules as the module) |
| `tools/pkg/engine/isolib.py` | ISO9660 helpers (add/replace/remove one record, append, tree walk) |
| `tools/pkg/engine/find_status.py` | debugger tool: find + decode the status block (`--selftest` offline) |
| `tools/pkg/engine/test/run_host_test.py` (+ `host_test.c`, `host_mock.h`) | host unit test of the boot logic |
| `tools/pkg/engine/test/p14_rows.json` | rows of the p14 test disc |

Build (deterministic: a clean rebuild gives the same sha256):
```
tools/dlc/pspenv.sh make -C tools/pkg/engine/extra
python3 -I tools/pkg/engine/make_manifest.py
python3 -I tools/pkg/engine/test/run_host_test.py      # 14 cases, no emulator, ISO read only
```

## What the module does at boot (module_start)

Loaded by the EBOOT stub (loader patch) after LIBFONT and LIBSUPPREACC, before the NP-DRM key call, with "try once"
(a missing or failing module never hangs the boot).

1. Status block `g_extra`: magic, self pointer, version, state 0 ("starting"), step counter.
2. `disc0:/PSP_GAME/USRDIR/DATA/EXTRA.IDX`: header check, rows into partition-2 memory (`PSP_SMEM_High`, 12 B/row),
   optional override bitmap into a temporary block. Checks: strictly ascending hash, sector < 2^20, size 1..2^28-1
   with install flag 0, checksum (rows + bitmap), unused bitmap bits 0.
3. Bounds: `sceIoGetstat(PACKAGE.BIN)`; every row must end inside PACKAGE.BIN (else the whole index is refused).
4. Collision check: reads the disc's own `PACKAGE_INFO.BIN` in 4,080-B chunks (temporary block); every one of our
   rows whose hash is in it must have its override bit, otherwise it is **dropped** (rows stay sorted).
5. If rows are left: JIT-safe guard on 0x08871420 (cache sync; the original call word there = mode 1, PPSSPP block
   marker with original neighbours = mode 2), one aligned store of our call to `xidx_tramp`, cache sync, read back.
6. Returns 0 (always stays resident: the game keeps pointers to our rows for the whole session).

Lookup at run time (P0.7, unchanged): `xidx_tramp` calls the game's hash, binary-searches our rows; hit → the
game's own hit path 0x088714BC with our row (name cache + every reader work unchanged, reads go through
PACKAGE.BIN); miss → the game's own search. Our rows are searched first, so a flagged row overrides the game's.
In layout A discs the disc PACKAGE_INFO also holds Sora's rows, so overriding a Sora
row needs the flag too; in layout B the disc index is the vanilla one.

Cost: image 3,680 B in RAM (text 2,624 + stubs/exports/rodata + data 48 + bss 128) + 12 B per row; temporary
blocks (bitmap ≤ 2 KB, 4,080 B read buffer) are freed before module_start returns; PACKAGE_INFO.BIN is read once
more at boot (≈134 KB). No thread. Free memory at that point is ≈4.3 MB (P0.3), ≈240 KB after the game's heaps.

## Status block (layout v1, 0x80 bytes, frozen; later layouts only append)

Find it: a 16-aligned address A with u32 `0x41525458` ("XTRA", bytes `58 54 52 41`) at A, A at A+0x08 and
`0xBEADABA7` (~"XTRA") at A+0x7C. Module offset: g_extra = module base + 0xDE0 (base = module_start − 0x124).

| off | field | meaning |
|---|---|---|
| 0x00 | magic | "XTRA" |
| 0x04 | u16 layout, u16 size | 1, 0x80 |
| 0x08 | self | A |
| 0x0C | base | &module_start |
| 0x10 | version | 0x00010000 = 1.0.0 |
| 0x14 | state (signed) | see below |
| 0x18 | warn bits | 1 PACKAGE_INFO unreadable (collision check skipped), 2 PACKAGE.BIN size unknown (bounds check skipped), 4 JIT marker accepted at the hook, 8 hook read-back differs |
| 0x1C | rows | address of the live rows |
| 0x20 | count | live rows |
| 0x24 | file_rows | rows in EXTRA.IDX |
| 0x28 | rejected | rows dropped by the collision check |
| 0x2C | overrides | live flagged rows that shadow a disc PACKAGE_INFO row |
| 0x30 | lookups | our search calls (= the game's non-cached lookups) |
| 0x34 | hits | |
| 0x38 / 0x3C | last_hit / last_hash | hashes |
| 0x40 | hook_at | 0x08871420 |
| 0x44 | hook_word | word read back after the patch (0 = no hook) |
| 0x48 | guard_seen | word at the hook after the cache sync, before patching |
| 0x4C | guard_mode | 1 vanilla, 2 JIT marker accepted, 0 refused / not reached |
| 0x50 / 0x54 | boot_max / boot_total | free memory at module_start |
| 0x58 | api | &g_api ("XAPI") |
| 0x5C | info_rows | disc PACKAGE_INFO rows scanned |
| 0x60 | first_rejected | hash of the first dropped row |
| 0x64 | pkg_size | PACKAGE.BIN size seen |
| 0x68..0x77 | row_hits[4] | hits on live rows 0..3 |
| 0x78 | step | last module_start step reached (8 = finished) |
| 0x7C | tail | 0xBEADABA7 |

**state**: 2 live (rows + hook) · 1 index OK but no row left (empty, or every row rejected) → no hook · 0 starting
(if it stays 0, the module died inside module_start: `step` says where) · −1 no EXTRA.IDX (vanilla; normal for an
engine-only disc) · −2 bad header · −3 no memory · −4 short read · −5 bad row · −6 bad checksum · −7 hook word not
vanilla · −8 row past the end of PACKAGE.BIN · −9 bad override bitmap. Every state ≠ 2 = no game word changed.

## API skeleton (Phase 2; no behaviour in v1)

`g_api` (module base + 0xDB0), also returned by the exported `extra_get_api()` (library `ExtraEngine` v1, exports
`extra_get_api`, `extra_find_row`, `extra_feature`):

| off | field | v1 |
|---|---|---|
| 0x00 | magic "XAPI" | |
| 0x04 | u16 version, u16 size | 1, 0x30 |
| 0x08 | registry | NULL — Phase 2: owner registry table (rows per `tools/dlc/owner_tables.json` id) |
| 0x0C | registry_count | 0 |
| 0x10 | find_row(hash) | read-only search of our rows (no counters) |
| 0x14 | feature(id) | always 0 (= vanilla behaviour) |
| 0x18 | status | &g_extra |
| 0x1C | reserved[5] | 0 |

Phase 2 plan: game code that needs per-owner data gets a `jal` into the module (or reads `registry` through a
fixed pointer written at module_start); features are switched on by id only when a package asks for them.

## EXTRA.IDX v1 (file `PSP_GAME/USRDIR/DATA/EXTRA.IDX`, little-endian)

```
0x00 "XIDX"   0x04 u16 version = 1   0x06 u16 header size (>= 32, multiple of 4)
0x08 u32 count N (0..16384)   0x0C u32 flags: bit 0 = override bitmap present (other bits must be 0)
0x10 u32 PACKAGE.BIN ISO sector = 186624 (sanity)
0x14 u32 sum = 32-bit sum of (hash ^ sector ^ size) over all rows + every u32 word of the override bitmap
0x18 u32 override bitmap offset (flag bit 0): ceil(N/32) u32 words, bit i of word i>>5 = row i is an intended
     override; >= header + 12*N; bits past row N-1 = 0
0x1C u32 names offset (tools only; the module never reads it): N NUL-terminated game paths in row order
header: rows[N] = u32 hash (CRC-32/BZIP2 of the lower-case path = pkghash.py), u32 sector (PACKAGE.BIN-relative,
     < 2^20), u32 size (1..2^28-1, top 4 bits 0 = never served from a Data Install), strictly ascending by hash
```
Compatible with the P0.7 research files (flags 0, offsets 0); the production module would drop their override row
because it has no override bit — correct behaviour. Paths are the path after language substitution
(`text/<lang>/…`), like PACKAGE_INFO. File data lives inside PACKAGE.BIN's extent (appended tail stretched by the
layout-B installer). Library: `tools/pkg/engine/xidx.py` (`build(rows)`, `parse(bytes)`).

## Installer: `install_engine.py`

```
python3 -I tools/pkg/engine/install_engine.py ISO [--out OUT] [--rows ROWS.json | --idx FILE | --no-idx]
        [--clean CLEAN.iso] [--allow-unflagged] [--rollback] [--dry] [--no-sha]
```
- Works on a **plain-EBOOT** disc (every Sora build and every package-installer output). The clean retail dump has
  an encrypted EBOOT → refused with a message (the package installer decrypts it first); OUT = the clean dump is
  refused.
- ISO is changed in place, or with `--out` copied to OUT first (an existing OUT must be a stock or engine disc).
- Accepts **stock** (vanilla loader words) or its **own output** (patched words); anything else is refused.
  Patch words are checked word by word against `engine-loader.json` (+ 8 context words around the site/callers).
- Index: `--rows` builds EXTRA.IDX from a rows file (`{"format":1,"rows":[{"path","from"|"sector"+"size",
  "override"}]}`), `--idx` takes a prebuilt one, `--no-idx` removes it, no option keeps the disc's one. Every
  index is parsed with the module's rules, then: **collision check** against the vanilla PACKAGE_INFO (read from
  `--clean`, default `dumps/ULUS10566.iso`, read only) and the target disc's PACKAGE_INFO — a colliding row
  without `"override": true` is refused; bounds check against PACKAGE.BIN. `--allow-unflagged` / per-row
  `"test_collision": true` exist only to build test discs (the module drops those rows at boot).
- Write order: file data (appended at the ISO end, or in place when a new version fits the old sectors),
  directory records, PVD size, EBOOT words last. Verifies afterwards (state, files identical, PACKAGE_INFO
  untouched). A second identical run prints "same" and changes nothing.
- `--rollback`: EBOOT words back to stock, EXTRA.PRX + EXTRA.IDX records removed, their data cut off the ISO tail
  when it is ours and nothing else lies after it (else the sectors are zeroed). Tested: Sora test disc → install →
  rollback = the same disc byte-for-byte; install again = the same sha256 as the first install.
- `--dry` prints the plan and writes nothing.

## Example test disc p14

The engine's first test disc, `dumps/ULUS10566-p14-engine.iso`, was a copy of a Sora test build in the older
layout (`dumps/ULUS10566-test339-installfix.iso`, sha256 25419c9e…04c6) plus the engine:
```
python3 -I tools/pkg/engine/install_engine.py dumps/ULUS10566-test339-installfix.iso \
        --out dumps/ULUS10566-p14-engine.iso --rows tools/pkg/engine/test/p14_rows.json
```
- 1,812,543,488 B, sha256 **fe54d164e46dbed3dc968c6e21f79bd8c28eb05d55eb793e757be89e95f09a00**.
- Diff vs the input disc: sectors 16 (PVD size), 27 (DATA dir), 32 (MODULE dir), 775 + 1168 (EBOOT: 52 loader words + site
  0x0893361C `0E218994` → `0E21BBD8`) + 4 appended sectors: EXTRA.PRX (sector 885027, 5,702 B) and EXTRA.IDX
  (sector 885030, 144 B, sha256 a7e52ae5…c232b). PACKAGE_INFO unchanged.
- EXTRA.IDX rows: **2e27ac41** `menu/JP/story_mode/chara2/p_sev120_1p.gim` (Sora's 64×64 VS face) → Lightning's
  `p_gst130_1p.gim` data (sector 242709, 5,408 B), **flagged override** = the one harmless override (as p07b);
  **5dfed0af** `menu/JP/story_mode/chara2/p_gst130_1p.gim` → Sora's face data (674330, 5,408 B), **not flagged**
  (vanilla path) = deliberate collision the module must drop.
- Host unit test predicts: state 2, count 1, file_rows 2, rejected 1 (first 5dfed0af), overrides 1, info_rows
  11179, pkg_size 1430329344, warn 0, guard_mode 1.

### Checking it in the emulator (throwaway profile, remote debugger on, CPU Minimal + Order's Sanctuary set each time)
`P` = debugger port.
1. Boot `ULUS10566-p14-engine.iso` → title. `python3 -I tools/pkg/engine/find_status.py $P` (searches user RAM; if
   the module loads at the address seen in P0.7, B = 0x09B8DA00, the block is at **0x09B8E7E0**, module_start 0x09B8DB24,
   API 0x09B8E7B0; any other address is fine). Expected:
   - `state 2`, `step 8/8`, `warn 0x0` (0x4 = JIT marker accepted and 0x8 = read-back marker are also OK);
   - rows: file 2, live 1, rejected 1 (first 5dfed0af), overrides 1, PACKAGE_INFO rows scanned 11179,
     PACKAGE.BIN 1430329344 B; `row 0: 2e27ac41 sector 242709 size 5408`;
   - hook 0x08871420 written `0x0C000000 | (B >> 2)` (B = 0x09B8DA00 → **0x0E6E3680**), guard mode 1 (or 2);
     "word at 0x08871420 now" = our jal or a JIT marker;
   - api: magic XAPI ver 1 size 48, registry 0, count 0; boot free ≈ 4.3 MB.
2. Old Phase-0 words untouched: `python3 -I tools/scripts/ppdbg.py $P read 0x089A8B14 16` =
   `f0 ff bd 27 08 00 b2 af 01 00 d2 24 04 00 b1 af`.
3. Quick Battle P1 Sora vs CPU Sora: VS/loading screen shows **Lightning's face for Sora** (override served).
   Status: hits ≥ 1, row_hits[0] ≥ 1, last hit 2e27ac41; lookups keep rising in battle (play ~30 s, normal).
4. Optional: a battle with Lightning on the VS screen shows **Lightning's own face** (the unflagged row was dropped).
5. Boot/menus/battle otherwise exactly like the input disc (fonts, save/load).
Failure meanings: no block found = module not loaded/started (PPSSPP log: `sceKernelLoadModule(...EXTRA.PRX)`);
state 0 with step < 8 = crash inside module_start at that step; −7 = hook word not vanilla (report guard_seen);
state 2 but Sora's own face on the VS screen = the lookup for that file does not pass 0x08871420 (check last_hash);
rejected 0 with warn 1 = PACKAGE_INFO could not be read (collision check skipped).

## Limits / open points
- Hardware: the plain PRX and the runtime code write need custom firmware. On a PS Vita with Adrenaline the module
  loads and serves Sora's files (release-candidate disc, October 2026). A real PSP is untested.
- `--no-idx` leaves the old EXTRA.IDX data as dead sectors; rollback then cannot cut the tail exactly (it zeroes).
- Keeping a disc's index whose rows were test collisions (p14) is refused without `--allow-unflagged` (by design).
- The module reads the disc index, not a "vanilla" list: in layout A, overriding a Sora row needs the flag too.

## Registry + stubs v2 (P2.1 design, 2026-10-19; built in P2.3-P2.8)

Written by Claude (P2.1 ABI helper) on 2026-10-19 as the design, from the files only. It has been built step by
step since; the "as built" blocks further down say what changed. A review by Codex is still welcome. Inputs:
[notes/dlc-phase2.md](../notes/dlc-phase2.md) (the owner-33 inventory), Sora's release patch files, the clean game
images, [notes/ex-burst-controller.md](../notes/ex-burst-controller.md) §21 (dead-code proof), P0.3 (free RAM), P0.7
(JIT guard).

### v2 design changes — DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome)
Sources: notes/phase2/P2.4-behaviour.md §6/§12, notes/phase2/P2.3-lookups.md §1/Q1, notes/phase2/P2.1-review.md §2.
Start guide: docs/PHASE2-START.md. These override the text below where they differ (marked "v2 change" there).
1. **Header-indirect stub table "XSTB".** Only a 6-word header is fixed, at **0x089A8B24** (the first word EXRUN frees):
   `+0 "XSTB" (0x42545358) · +4 u16 version 1, u16 count · +8 fnptr_base · +0xC stub_base (16 B per stub) ·
   +0x10 fallback_lo · +0x14 fallback_hi`. The module looks only here and trusts only what the header says (plus
   `fallback_lo <= FN_PTR[n] < fallback_hi`). Pilot layout (28 words 0x089A8B24–0x089A8B94): header, REG_PTR 0x089A8B3C,
   REG_COUNT 0x089A8B40, FN_PTR[0] 0x089A8B44, STUB_0 0x089A8B48, FALLBACK_0 0x089A8B58 (the displaced original words,
   then a jump back to 0x088374B0),
   REG_ROW 0x089A8B60 (12 words), 1 spare. After the TRI port the arrays move into the TRI range by changing two header
   words (fnptr_base, stub_base). So the EXRUN pilot can land before TRI moves. (P2.4 note §6.) Open: the header has no
   `reg_base` word; the final REG block's place (fixed offset from fnptr_base, or a fixed address) is frozen with the
   TRI step.
2. **Lookups:** table-shaped lookups (pictures, frames, Museum viewer, OQ pairs, flags bitmap …) use **small per-owner
   tables written by the installer** (P2.3 "OXT": vanilla values for owners 0..32, package values for 33+). They cost what
   vanilla costs, can be checked offline, and still work when EXTRA.PRX fails to load. REG_ROW / REG_FLAG stay for code
   sites that need them (BGM fallback owner bound, visibility gate, record lookup). The EXTRA.REG row fields
   name_index / pic_slot / party_frame / setup_frame / oq_* are then read by tools and diagnostics, not by game code.
   *2026-10-20 (P2.3 steps 1-2):* the table spec lives in `tools/dlc/owner_tables.json` → `tables[].rowgen` (format in
   `legend.rowgen`); the generator is `tools/pkg/rowgen.py` (notes/phase2/P2.3-rowgen.md). The owner → name code (EBOOT
   FUN_088D6254, menu FUN_08A1D7F8) is generic in place and reads the rowgen D1 row (`tools/pkg/engine/patches/p23_names.py`, moved 2026-10-21 — old path kept as a wrapper;
   notes/phase2/P2.3-names.md).
   *2026-10-21 (P2.3 steps 3-7, BUILT):* the OXT tables live in the EBOOT block 0x089A8B94-0x089A8F0C (header "OXT1",
   PIC_IDX, PARTY_FRAME, SETUP_OFF, VIEWER_OWNER, REC_ICON, PANEL_SPRITE, OQ_PAIR, REC_APPEND, KEY_POOL + 4 helpers);
   REG_ROW is used by the BGM fallback, the flag ranges (EXTRA.REG, engine 2.5.0) by the Jukebox gates. Block "P2.3
   steps 3-7 — as built" at the end of this section; notes/phase2/P2.3-home.md.
3. **Stub list:** S23 EX_SND **dropped** (never built: TRINITY_CTL = 1; feature id 3 retired, never reused).
   **S24 PANEL_LIT added** (menu 0x08AFF32C: that one word becomes a `jal` to the stub, mid-code, live a1/a3, today's target 0x089A8DC4).
   S11 C4 becomes a fallback-only stub (its generic transform runs with or without the module).
4. **Fixes from the P2.1 review (High), now part of the design:**
   - **Visibility gate:** the unlock walker (EBOOT FUN_088d5ac8 / FUN_088d5ce8) lists an owner ≥ 33 only when its
     registry row exists (`REG_ROW(owner) != 0`; list-build only, not per frame). Module or registry missing → the game
     is vanilla + inert data, never a half-working fighter.
   - **Item eligibility for every package owner:** the item-eligibility stubs (S15 ELIG, S16 ROWMASK, S17 MENU_FIX,
     S20 SHIELD) are installed whenever any row has owner ≥ 33, because the equip masks use bit (owner − 1) & 31 —
     owner 34 shares Garland's bit 1. Builder sets a derived feature bit OWNER_MASK_FIX on every row.
   - **Pointer table for P2.7 moved buffers:** the REG block gets `BUF_PTR[8]` + `u16 buf_size[8]`; on disc each
     pointer = the **vanilla** buffer address, module_start replaces it when it allocates a bigger buffer. Overlay code
     reads the pointer from fixed EBOOT memory (data-indirect, like the stubs).
   - **Identity:** EXTRA.REG header grows to 0x48: `+0x40 u32 roster_id` (hash of the sorted package ids +
     package_sha256), `+0x44 u32 stub_abi_hash` (hash over n, name, site VA, contract of the stub list). EXTRA.IDX
     header grows to 0x24: `+0x20 u32 roster_id` (its header-size field already allows this). The module embeds its
     stub-list hash; mismatch → stub_state −4, nothing written; roster mismatch between the two files → reg_state −9,
     nothing published.
   - **Publish order:** rows, REG_PTR, FLAG/ITEM/BUF pointers first, **REG_COUNT last** (REG_ROW tests REG_COUNT),
     **FN_PTRs after the registry** (stubs last). Every wrapper starts in asm with "REG_COUNT != 0 and owner is a package
     owner, else jump vanilla[n]" before any C prologue.
   - **Overlay-loaded guard:** menu and battle overlays share base 0x089DD4C0. A wrapper reads or calls overlay code or
     data only after checking which overlay is resident (candidate: the copied ELF header word 0x089DD4B0 = p_filesz
     0x185AB0 battle / 0x17BD98 menu — unconfirmed at runtime — or a known word at 0x08B34378). Wrappers called from
     EBOOT sites use EBOOT/module data only.
   - Owner ceiling: validator should ERROR above owner 34 until P2.7 relocations exist (chrp, Opponent Info rows, grid
     bounds and the save stats blocks end at 34). Not yet in registry.py (it warns above 35).
5. **"Done" check (P2.3 + P2.4):** no owner-33 compare (an exclusive-or of the owner with 0x21) in any code image **and** no
   other new-vs-clean owner-33 or package constant: 33 loaded or compared as an immediate (e.g. TRI_BAR_VOICE loaded
   33 as a constant at 0x089C2184),
   item ids 678-682 / −678, sprite cell 32, voice 21910042, motion 8501, EX-page pictures, multipliers.
   tools/pkg/owner_scan.py should report both groups (an `--image` disc mode is still to add).

### In plain English
- The game reaches our code in three ways, and v2 gives each one a fixed, safe shape:
  1. **Install-time data** (most sites): tables and limits inside the game's own images that the installer simply
     fills for every package fighter (unlock rows, Labyrinth faces, title-call tables, list sizes…). No runtime code.
  2. **Registry lookups**: places where the game used to ask "is this owner 33?" now ask a tiny helper in the EBOOT
     "give me this owner's row". The row comes from a data file `EXTRA.REG` that the module loads at boot.
  3. **Behaviour stubs**: places that run Sora-only logic (Trinity Limit, Reflect guard, item effects, EX run speed)
     call a fixed **stub** in the EBOOT. The stub jumps wherever a pointer says: the module's code if the module
     loaded and a package uses that feature, otherwise a tiny copy of the original game instructions.
- **No module, no registry, or a broken file → the game behaves like vanilla** for every vanilla fighter. The module
  writes only **data words** (pointers), never instructions, so the emulator's JIT problem from P0.7 cannot happen.

### 1. Where the code lives (freed EBOOT ranges, verified)
Once Sora's routines move into the module (P2.4), three proven-dead EBOOT ranges are free:

| range | bytes | proof | v2 use |
|---|---|---|---|
| `0x089C1C8C–0x089C2508` (dead fn FUN_089c1c8c, today TRI) | 2,172 (543 words); first 4 words stay original (probe hook) → **usable 0x089C1C9C–0x089C2508 = 539 words** | §21 static scan; runtime marker probe test272p PASS (never called in menus, QB, replay, Extras, Story); re-scan 2026-10-19 (below) | **stub table** + REG block + fallbacks |
| `0x089A8B14–0x089A8F0C` (dead fn, today EXRUN/EXITEMS/EE_B) | 1,016 (254 words); first 4 stay original → **usable 0x089A8B24–0x089A8F0C = 250 words** | same | **lookup helpers** (+ P2.3 shared site helpers) |
| `0x089D1FB4–0x089D2084` (its switch table, today SCALE) | 208 (52 words) | only referenced by its dead function's own indirect jump | reserve (P2.3 spill) |

Re-scan 2026-10-19 (a scratch scan script over the clean EBOOT + menu + battle + extra overlays: every jump and call
target, branch target, raw word and high/low address pair): the only references into the ranges are (a) the dead switch table → the
dead function (dead together), (b) the dead function's own switch load, (c) 5 "branches" that are rodata words at
0x089D1D54–0x089D5DB0 (already known in §21), (d) 6 address pairs with the high half 0x089D at 0x08870F1C/28, 0x08871114,
0x088821DC–E4 that are **false hits** (the register is reloaded before the offset is added, or a different base
pointer is used — checked by hand). Not usable: EBOOT gap 0x089DD3C0–0x089DD46C (overlay header area), anything past 0x08B63170 (bss).

### 2. Stub table (fixed, in EBOOT, vanilla-safe)
**v2 change 2026-10-20:** the fixed table at 0x089C1C9C below is replaced by the header-indirect XSTB (header at
0x089A8B24, see "v2 design changes" item 1). Entry layout, register contract and fallbacks stay as written here; the
arrays live wherever fnptr_base / stub_base point (pilot: 0x089A8B44 / 0x089A8B48; final: TRI range).
```
0x089C1C9C  "XSTB"              u32 magic 0x42545358
0x089C1CA0  u16 version = 1, u16 count = 32
0x089C1CA4  u32 fallback_lo     first byte of the fallback area
0x089C1CA8  u32 fallback_hi     end of the fallback area
0x089C1CAC  FN_PTR[32]          u32 each; ON DISC = address of fallback n (vanilla behaviour); module_start may replace
0x089C1D2C  STUB[32]            16 B each:  lui at,%hi(FN_PTR+4n) / lw at,%lo(FN_PTR+4n)(at) / jr at / nop
0x089C1F2C  REG block (data, 0 on disc, written by module_start):
            +0 REG_PTR (row array, 31 slots × 64 B, index owner−33)  +4 REG_COUNT
            +8 FLAG_PTR (package-flag bitmap) +0xC u16 FLAG_LO, u16 FLAG_BITS
            +0x10 ITEM_PTR (item→owner bytes) +0x14 u16 ITEM_LO, u16 ITEM_COUNT  +0x18..0x1F reserved 0
0x089C1F4C  fallbacks           per stub: the displaced original instruction(s) + `j` back / `j` original callee
            (2–4 words; ≈ 96 words for 24 stubs) → ends ≈ 0x089C20CC; ≈ 270 words left in the range
```
- **Hook sites stay one word** (`jal STUB_n` or `j STUB_n`, exactly today's site shapes; data-pointer sites such as
  the controller vtable word 0x08A3B1BC and the deflect-table word 0x08ADB32C hold `&STUB_n`). Overlays and EBOOT are
  in the same 256 MB `j` segment as 0x089C1D2C, so a plain `jal` reaches every stub. Overlay words are disc patches
  (re-read every scene change) and never hold a module address — only stub addresses, which never move.
- **Register contract:** a stub clobbers **only `$at`**. `ra` is untouched (call sites) so fallbacks can tail-jump
  to the original callee and module wrappers return straight to the hook site. Checked 2026-10-19: none of the 24
  hook delay-slot words reads or writes `$at`; compiled game code never keeps `$at` live across an instruction
  boundary (it is only used inside one assembler macro). The registry builder (P2.2) must keep this rule: **a hook's
  delay slot may not touch `$at`**.
- **Vanilla-safe defaults:** on disc every FN_PTR points into the fallback area, so with no module (or a module that
  refuses the registry) every hook runs the original instructions. A stub costs 4 words + 1 pointer + its fallback.
- **module_start fills them** (after EXTRA.IDX, step 9+): check magic/version/count; for each stub n the module
  implements **and** whose feature is used by at least one loaded row: require `fallback_lo <= FN_PTR[n] <
  fallback_hi` (else leave it, warn), remember the old value as `vanilla[n]` (module wrappers jump there for non-
  package owners), store `&wrapper_n` (one aligned `sw`), read back. No cache maintenance is needed: these are data
  words. Then publish REG/FLAG/ITEM pointers (REG_PTR written **last**, after the rows are complete).
- **JIT safety (P0.7 lesson):** PPSSPP replaces the first word of a compiled block with a marker, which is why the
  P0.7/P1.4 hook needs a guard. v2 writes no instruction words (only FN_PTR/REG block data, never executed), and
  `lw at,FN_PTR` is a real memory load on every call, so a stub compiled before module_start still sees the new
  pointer. The P1.4 xidx hook (0x08871420) stays the module's only instruction write.

**Stub list (24 used, 8 spare), from the R2 package hooks** (26 hook words). **v2 change 2026-10-20:** still 24 used
(S0–S22 + S24 PANEL_LIT; S23 dropped) for 28 hook sites / 36 hook words (P2.4 note §4):

| n | stub | hook site(s) | today's target | feature id |
|---|---|---|---|---|
| 0 | TRI_DISPATCH | B 0x08A39E04 jal | 0x089C1C9C | 7 BURST_MODULE |
| 1 | TRI_BAR_VOICE | B 0x08A39ECC jal | 0x089C2164 | 7 |
| 2 | TRI_PROMPT | B 0x08A3A048 jal | 0x089C2074 | 7 |
| 3 | TRI_EXIT | B 0x08A3FCA4 jal | 0x089C20A8 | 7 |
| 4 | TRI_VT5C | B 0x08A3B1BC vtable word | 0x089C2024 | 7 |
| 5 | EE_HIT | B 0x08AE6ED4 jal | 0x089C2280 | 5 ITEM_EFFECTS |
| 6 | CROWN_DRAIN | B 0x08AEC160 jal | cave 0x08B63140 | 5 |
| 7 | EXRUN | B 0x08B2D380 jal | 0x089A8B24 | 1 EX_RUN |
| 8 | REFLECT_C1 | E 0x0880A384 `j` (mid-function) | cave 0x08B62F9C | 2 REFLECT_GUARD |
| 9 | REFLECT_C2 | E 0x0880A408 jal | cave 0x08B62FC4 | 2 |
| 10 | REFLECT_C3 | B 0x08ADA22C jal | cave 0x08B63088 | 2 |
| 11 | REFLECT_C4 | E 0x08808B74 jal | cave 0x08B63078 | 2 |
| 12 | REFLECT_C7 | B 0x08ADB32C table word | cave 0x08B630DC | 2 |
| 13 | ITEM_ENSURE | E 0x088B8FD0 `j` (function entry) | 0x089A8B94 (**built step 4: module stub 13**) | 4 ITEM_OWNER (start-owned items) |
| 14 | ITEM_NEWGAME | E 0x088B8778 jal | 0x089A8C0C (**built step 4**) | 4 (start-owned items) |
| 15 | ITEM_ELIG | E 0x088C1AFC jal | 0x089A8C54 (**built step 4**) | 4 |
| 16 | ITEM_ROWMASK | E 0x088C132C, 0x088C1364 jal | 0x089A8C9C (**built step 4**) | 4 |
| 17 | ITEM_MENU | M 0x08AF8ED8, 0x08AF9004 jal | 0x089A8CC4 (**built step 4**) | 4 |
| 18 | ITEM_PICID3 | E 0x088D56A4, 0x088D56D8 jal | 0x089A8D88 (**built step 4**) | aux EXPAGE (as built; this table said 4) |
| 19 | ITEM_PICID0 | E 0x088D5714 jal | 0x089A8D80 (**built step 4**) | aux EXPAGE (as built) |
| 20 | ITEM_SHIELD | E 0x088079AC jal | 0x089A8D24 (**built step 3: module stub 20**) | 5 ITEM_EFFECTS (as built; this table said 4) |
| 21 | ITEM_STASH | E 0x088BE63C `j` (function entry) | JT 0x089D1FB4 (**built step 4**) | 6 ITEM_SCALING |
| 22 | ITEM_SCALE | E 0x088BE96C jal | JT 0x089D1FC4 (**built step 4**) | 6 |
| ~~23~~ | ~~EX_SND~~ — **dropped 2026-10-20** (never built, TRINITY_CTL=1; feature id 3 retired) | – | – | – |
| 24 | PANEL_LIT (**added 2026-10-20**) | M 0x08AFF32C jal (mid-code, live a1/a3) | 0x089A8DC4 (**built step 4**) | 4 ITEM_OWNER |
| 25–31 | spare (23 stays unused) | | | |

Side benefit: today 3 EBOOT hooks (C1, C2, C4) jump straight into the **battle overlay** cave (valid only because they
fire in battle); through stubs they reach the always-resident module instead.

### 3. Registry lookups (EBOOT helpers, no module needed to run them)
**v2 change 2026-10-20:** table-shaped lookups use installer-written per-owner tables instead (item 2 above). REG_ROW
(12 words) lands first in the EXRUN pilot range (0x089A8B60, owner-dense rows, REG_COUNT written last); the other
helpers go into the ≈ 270 spare words of the TRI range once TRI moves. REG_BY_MUSEUM and REG_NEXT are likely not
needed (Museum viewer = per-owner table; Aerith append is vanilla code, P2.3 note §0.7). New use: the visibility gate.
Helpers in the freed range at 0x089A8B24 (≈ 63 words total). ABI: in `a0`, out `v0`, clobber **`at`, `v0` only**.
| helper | does | words |
|---|---|---|
| REG_ROW(owner) | `v0` = &row if 33 ≤ owner < 64, REG_PTR ≠ 0 and row.owner == owner, else 0 | ≈ 15 |
| REG_FLAG(flag) | `v0` = 1 if the flag is in the package-flag bitmap (0 when FLAG_PTR = 0) | ≈ 14 |
| REG_NEXT(prev) | next registered owner > prev, or 0 (append loops: Records list, Aerith check) | ≈ 14 |
| REG_BY_MUSEUM(rec) | owner whose `museum_record` == rec, or 0 | ≈ 12 |
| REG_ITEM_OWNER(item) | owner byte for item, 0 = everyone | ≈ 8 |
A typical converted site calls REG_ROW with the owner, takes the vanilla path when the result is 0 and loads the
field it needs: ≈ 4–6 words, about the size of the release's owner-33 compare blocks. Per-site register allocation is P2.3's job.

### 4. Registry row v1 (64 B, little-endian; file rows may be longer, readers use the first 64 B)
| off | type | field | read by (inventory #) | Sora (owner 33) |
|---|---|---|---|---|
| 0x00 | u8 | owner (33..63; 0 = empty slot) | all | 33 |
| 0x01 | u8 | row_flags (bit 0 valid) | all | 1 |
| 0x02 | u16 | feat (bit = feature id − 1) | stubs | EX_RUN, REFLECT, ITEM_OWNER, ITEM_EFFECTS, ITEM_SCALING, BURST_MODULE, PKG_FLAGS, RECORD_SLOT, OQ_FACE |
| 0x04 | u16[3] | panel_tex (Characters-panel textures) | #13 | 3179, 7269, 8321 (check order in P2.3) |
| 0x0A | u16 | panel_sprite (sprite cell) | #13 | 32 (owner 32's free cell) |
| 0x0C | u16 | name_index (collection group 3) | #1, #2 | 63 |
| 0x0E | u8 | record_slot (0 = none) | #3 | 24 |
| 0x0F | u8 | museum_record | #16 | 34 |
| 0x10 | u16 | pic_slot (owner−1 runs: QB, untold tale, party, arrange, OQ grid, Level Adjust, Shop, setup) | #14, #15 | 245 |
| 0x12 | u16 | pic_slot_party (party slots) | #14 | 246 |
| 0x14 | u16 | party_frame | #14 | 14 |
| 0x16 | u16 | setup_frame | #15 | own frame (value from setup_banner_remap, P2.2) |
| 0x18 | u16 | oq_name (full-name entry) | #21 | 122 |
| 0x1A | u16 | oq_face_pic | #21 | 25897 |
| 0x1C | u16 | oq_face_layout | #21 | 0x660E |
| 0x1E | u16 | oq_banner | #21 | 26028 (check vs spot33_oqslot in P2.2) |
| 0x20 | u16[3] | oq_row (face_r, face, name) | #21 | 26028, 26063, 25929 |
| 0x26 | u8 | burst_ctl (0xFF = chrp choice, 0x80 = module controller 0 = TRI) | #10 | 0x80 |
| 0x27 | u8 | reserved 0 | | |
| 0x28 | f32 | ex_run_mult (0 = off) | #7 | 1.3984375 (upper half of the release constant) |
| 0x2C | u32 | key_off (string table: `sev120`) | diagnostics, tools | → "sev120" |
| 0x30 | u8[16] | params (per behaviour; v1 TRI: u16 item_a, u16 item_b; reflect: u16 refill_item, u16 mult_item, u16 voice_slot; crown: f32 drain) | #9–#11 | 678, 679 / 680, 681, voice / 0.7 |
Max **31 rows** (owners 33..63, the 64-bit music-mask ceiling); the save format limits real use to owners 33..35
until P2.5 (validator warns above 35). RAM: 31 × 64 = 1,984 B (dense, indexed by owner − 33).

Not in the row (install-time data, written into the images by the installer for every package owner): unlock
table rows, start preset, scenario names, Records icon, Labyrinth face, menu name keys, QB grid rows, select-panel
entry, EX-Mode page row, OQ full-name / banner / party-row tables, title-call tables + bound, ablt cap, Jukebox list
caps, friend-card limit (25 − rows with record_slot), PROJ_AIM bound. Sites #6 (BGM fallback) and #4 (assist drop
0x7F) need nothing (made generic once).

### 5. Feature ids (`extra_feature(id)` returns a bitmask of rows using it; 0 = off)
1 EX_RUN · 2 REFLECT_GUARD · 3 EX_BURST_SOUND_SKIP · 4 ITEM_OWNER · 5 ITEM_EFFECTS · 6 ITEM_SCALING ·
7 BURST_MODULE · 8 PKG_FLAGS · 9 RECORD_SLOT · 10 OQ_FACE (extra OQ face handle). Unknown ids → 0.

### 6. EXTRA.REG v1 (`PSP_GAME/USRDIR/DATA/EXTRA.REG`, little-endian)
A loose file next to EXTRA.IDX, read by the same code path P1.4 already uses for EXTRA.IDX (sceIoOpen at boot,
before any game file state). Deviation from the plan's "served through EXTRA.IDX": a loose file needs no PACKAGE.BIN
seek logic and keeps the module identical for every roster; tools may still list it in the EXTRA.IDX names block.
```
0x00 "XREG"  0x04 u16 version = 1  0x06 u16 header size (>= 0x40)
0x08 u16 row_size (>= 64)  0x0A u16 row_count (0..31)   0x0C u32 rows_off
0x10 u32 item_owner_off  0x14 u16 item_lo  0x16 u16 item_count      (u8 owner per item id from item_lo)
0x18 u32 item_fx_off     0x1C u32 item_fx_count                       (8-B rows: u16 item, u8 effect, u8 0, f32 value)
0x20 u32 flagmap_off     0x24 u16 flag_lo   0x26 u16 flag_bits        (bitmap, bit i = flag flag_lo + i)
     (2026-10-21, engine 2.5.0 / min engine 0x00020500: 0x20 franges_off, 0x24 u16 frange_count, 0x26 u16 0 = a list of
      u32 lo | count << 16 gate-flag runs; block "P2.3 steps 3-7 — as built")
0x28 u32 aux_off         0x2C u32 aux_size                            (per-behaviour tables, e.g. today's SCALE TAB)
0x30 u32 strings_off     0x34 u32 strings_size
0x38 u32 sum (32-bit sum of every u32 after the header)   0x3C u32 min_engine_version (0x00020000)
```
Load rules (any failure → nothing published, REG_PTR stays 0, every stub stays vanilla): magic/version/sizes inside
the file; rows ascending by owner, 33 ≤ owner ≤ 63, unique; known feat bits only; burst_ctl ∈ {0xFF, 0x80}; item and
flag ranges inside the file; sum; min_engine_version ≤ module version. A disc with packages but no usable registry
runs package fighters in a degraded way (vanilla paths for owner ≥ 33), so the installer refuses to write packages
without the engine + EXTRA.REG, and the status block reports it.

### 7. Status block v2 (append-only; v1 0x00–0x7F unchanged, incl. tail at 0x7C)
`layout` = 2, `size` = 0xC0. New fields:
| off | field |
|---|---|
| 0x80 | reg_state: 2 live · −1 no EXTRA.REG (normal for an engine-only disc) · −2 bad header · −3 no memory · −4 short read · −5 bad row · −6 bad sum · −7 engine too old · −8 bad section |
| 0x84 | reg_rows · 0x88 reg_addr · 0x8C reg_file_size |
| 0x90 | stub_state: 2 written · 1 table OK, nothing to write · −1 no XSTB (pre-Phase-2 disc) · −2 version/count mismatch · −3 a pointer outside the fallback area |
| 0x94 | stub_base · 0x98 stub_count · 0x9C stub_written (bit n = FN_PTR[n] now points into the module) |
| 0xA0 | feat_live (OR of row feat) · 0xA4 item_count · 0xA8 fx_count · 0xAC flag_bits |
| 0xB0 | first_bad (owner / offset that failed) · 0xB4 behaviour_calls (module wrappers, diagnostics) · 0xB8 reserved |
| 0xBC | tail2 0x32525458 ("XTR2") |
XAPI: `registry` / `registry_count` filled; `feature(id)` real (§5). `find_status.py` must learn layout 2 (P2.2).

### 8. Cost estimate
- Per behaviour entry: hook 1 word (unchanged) + stub 4 + pointer 1 + fallback 2–4 ≈ **8 words**; 24 entries ≈ 200 words
  in the TRI range (539 available). Per lookup site ≈ 4–6 words (≈ today's owner-33 blocks). Helpers ≈ 63 words.
- Disc images: ≈ 1,000 behaviour words (TRI 536, EXITEMS 212, EE_B 61, EXRUN 25, cave 128 code words = 512 B — corrected 2026-10-20, P2.4 note §2) leave the EBOOT/overlays;
  the battle-overlay cave can go back to vanilla size once C1–C7/CROWN move.
- Registry: 64 B per row in the file and in RAM (dense 1,984 B), item tables ≈ 8 B per item effect, flag bitmap ≤ 512 B.
- Module (estimate, C at ≈ 1.5× the hand-written asm): today 3,680 B + registry loader/validator ≈ 1.5 KB + TRI ≈ 2.5 KB
  + items ≈ 2 KB + reflect ≈ 1.2 KB + item effects ≈ 0.6 KB + EXRUN 0.2 KB + 24 asm wrappers ≈ 1.4 KB + tables ≈ 3 KB
  ≈ **16–20 KB**, + 12 B per EXTRA.IDX row (Sora layout B ≈ 255 rows ≈ 3 KB) → **≈ 20–25 KB for Sora**, ≈ +4–8 KB per
  extra fighter (more only with a custom behaviour). P0.3: 247,040 B largest free block after boot (445,440 B total)
  → ≈ 10 % of the largest block.

### 9. Open points for review (no decision by Mat needed)
- Module wrappers must reproduce each routine's register contract (today's asm routines rely on specific live
  registers); P2.4 writes one asm wrapper per entry around C code.
- Dense 31-slot array vs. 3-slot (owners 33..35): 1,984 B vs 192 B; kept dense for O(1) helpers.
- params[16] may be too small for a future custom controller; such behaviours use the `aux` section.

### P2.2 notes (registry builder, 2026-10-19)
- Builder/validator/decoder: `tools/dlc/registry.py`; sources `tools/dlc/registry/*.json`; details and the check list in
  notes/dlc-phase2.md "P2.2 registry builder". Sora EXTRA.REG = 220 B, Sora + owner-34 placeholder = 296 B (**536 B since 2026-10-20**: test34's unlock flag moved to the pool, 1285 → 3200, so the one-range gate-flag bitmap spans 888..3200).
- Corrections to §4: `setup_frame` = 12 (Cloud's frame row, borrowed), `oq_banner` = 26028 (= oq_row face_r);
  Crown Pendant drain = 0.769 (1/1.3), not 0.7. `params` v1 layout `behaviours-v1` = `<4HBBHf` (items[4], voice_bar,
  voice_reflect, reserved u16 = 0 (was shield_pct /128 until 2026-10-21: RETIRED, item_fx REFLECT_POWER is the one
  source, P2.4 step 3), reserved f32 = 0 (was crown_drain 0.769 until 2026-10-21: RETIRED in P2.4 step 4, item_fx EX_DRAIN is
  the one source)); all zero for fighters without behaviours.
- Item effect codes for the fx section: 1 EX_HIT_GAIN, 2 EX_GUARD_GAIN, 3 REFLECT_POWER, 4 EX_DRAIN.
- Item ids must stay < 683 until P2.7 raises the item ceiling (only id 682 is free after Sora).


- 2026-10-20T12:39:30Z P2.4 research (Claude P2.4 helper): behaviour hook sites, wrapper rules, EXRUN pilot with a header-indirect stub table, toolchain proof, port order → [notes/phase2/P2.4-behaviour.md](../notes/phase2/P2.4-behaviour.md) (suggested edits for this section in its §12; not applied).
- 2026-10-20 (Claude, start-guide helper): §12 edits folded in as "v2 design changes — DECIDED 2026-10-20" at the top of this section (XSTB header, OXT lookups, stub list S23 → dropped / S24 PANEL_LIT, P2.1-review High fixes, wider done check). Start guide: [docs/PHASE2-START.md](PHASE2-START.md).

### P2.4 steps 0 + 1 — as built (Claude, P2.4 step-1 helper, 2026-10-21; pilot report §8 folded in)
Sources: [notes/phase2/P2.4-exrun-pilot.md](../notes/phase2/P2.4-exrun-pilot.md) (step 0), [notes/phase2/P2.4-tri.md](../notes/phase2/P2.4-tri.md) (step 1).
- **§2 XSTB header (frozen):** 6 words at **0x089A8B24**: `"XSTB"`, `u16 version | u16 count << 16`, fnptr_base,
  stub_base, fallback_lo, fallback_hi. The module trusts only the header (+ `fallback_lo <= FN_PTR[n] < fallback_hi`).
  **REG block = header + 0x18** for every version: REG_PTR +0x18, REG_COUNT +0x1C, then FLAG_PTR, FLAG_LO|BITS,
  ITEM_PTR, ITEM_LO|COUNT, 2 reserved (8 words, 0 on disc; the module refuses to publish if any is not 0: stub_state −4,
  warn 0x10). REG_ROW stays at 0x089A8B60 (12 words).
  - version 1 = step-0 pilot: everything in the 28 EXRUN words, count 1, stub 0 = EXRUN (FN_PTR 0x089A8B44, STUB_0
    0x089A8B48, FALLBACK_0 0x089A8B58). Only the frozen pilot module (`extra/pilot/`, `--engine v2-pilot`) reads it;
    engine 2.1 answers −2 (vanilla).
  - **version 2 = step 1:** count 32, arrays in the freed TRI range: **abi_hash at fnptr_base − 4 = 0x089C1C9C**,
    FN_PTR[32] 0x089C1CA0, STUB[32] 0x089C1D20, fallbacks from 0x089C1F20 (step 1: to 0x089C1FA0). FN_PTR[n] = 0 means
    "stub n not on this disc" (skipped, no error). abi_hash = FNV-1a 32 of `p24_stubs.py abi_text()` (n, name, feature,
    sites, contract of every stub on the disc); step 1 = **0x39415849**; the module embeds it (extra/stub_abi.h,
    generated by `p24_stubs.py --gen-header`) and refuses another value: **stub_state −5**, nothing written.
  - Stub numbers = the table below. Step 1 uses 0-5, 7 and TEMPORARY 29/30/31 (cave C2/C7 → EE_GUARD / EE_PROJ /
    TRI_HPROW until step 2 removes the cave). Fallback 0 has the one allowed generic owner bound (owner < 33,
    at 0x089C1F3C): without the module, package owners run Cloud's variant-0 controller, everyone else Garland's.
  - Runtime: data-indirect stubs proven on PPSSPP JIT + interpreter (step 0); step 1's JIT freeze on a full Sora EX
    Burst (P2.4-tri §4.3) was a misaligned stack, not stub 5: FIXED in engine 2.1.1 (P2.4-tri §8, wrapper rule §10 below).
- **§3 REG_ROW** (12 words at 0x089A8B60) returns the dense SLOT pointer for 33 ≤ owner < 33 + REG_COUNT (owner byte
  0 = empty slot; callers check the field they need); REG_COUNT = highest registered owner − 32; publish REG_PTR, then
  REG_COUNT, stub pointers last. The module does not call it (it has its own lookup with the same rule); P2.3 code may.
- **§4/§6 registry:** EXTRA.REG aux section = "behaviours-v1 aux" records `u8 owner, u8 kind, u16 size` (kind 1 TRI:
  u32 voice_bank, u16 full / inc / follow motion, i8 banner_full, i8 banner_name, u8 prompt_text; kind 2 EE: u16
  combo_cap, combo_gap, hpref_gain, dup_frames, u8 hit_in_ex; unknown kinds skipped; kind 0xF0 = test-only bisection
  record, never in a package). Bar-full voice id = voice_bank × 100 + params.voice_bar (Sora 219100 × 100 + 42 =
  21910042). Item gains come from item_fx for items the row's owner owns. Registry values for constants come from the
  WHOLE built constant (both halves), never the upper half alone (EX run 1.4 = 0x3FB33333, not 1.3984375).
- **§7 status block layout 2:** 0xB4 reg_slots, 0xB8 v2_step, 0xBC "XTR2", 0xC0 stub_calls[32]; engine 2.1 appends
  0x140 abi_disc, 0x144 abi_module, 0x148 owners_tri, 0x14C owners_ee (EE_HIT | EE_GUARD << 16), 0x150 aux_rows,
  size **0x160**. stub_state: 2 written, 1 nothing to write, −1 no XSTB, −2 version/count/address, −3 FN_PTR outside
  the fallbacks, −4 REG block not 0, −5 abi mismatch. `extra_feature(id)` = owner bitmask (bit owner − 33).
- **§9 wrappers:** `CALLSITE_WRAP` (saves a0-a3, t0-t3, f12-f19, ra; counter in stub_calls[n]; C decides; return or
  tail to vanilla[n]) and `MIDCODE_WRAP` (every caller-saved integer register but the result survives); EXRUN keeps its
  asm fast path. C behaviours: tools/pkg/engine/extra/beh.c (no owner numbers, registry masks).
- **§10 wrapper rule — 16-byte stack for game calls (engine 2.1.1, P2.4-tri §8):** psp-gcc's EABI aligns sp to 8 only,
  the game assumes 16 (VFPU sv.q / lv.q on stack locals). Module C NEVER calls a game function directly: `GFN(type,
  addr)` expands to the thunk `gt_<addr>` (beh.c `GAME_FNS` list; a missing entry fails to compile), which aligns sp to
  16 with 16 free bytes, keeps a0-a3 / t0-t3 / f12-f19, and restores sp + ra. Asm wrappers must keep their frames a
  multiple of 16 (`CALLSITE_WRAP` 0x50; `MIDCODE_WRAP` 0x48 only reaches game code through C → thunk). Symptom of a
  break: PPSSPP JIT hangs at 100 % CPU in a fault loop (IR interpreter fine); on hardware an address error. Never put
  module code between a hook and game code that may run VFPU stack stores without this thunk.
- **Files:** extra/extra_v2.prx (engine 2.1, 6fa3720a… on P24-tri; engine 2.1.1 b13b3ae1… on P24-tri2) / engine_v2.json / Makefile.v2 / v2.c + beh.c +
  stub_abi.h; frozen pilot in extra/pilot/; `install_engine.py --engine v1|v2|v2-pilot`, `--reg`, `--no-reg`;
  `p24_stubs.py --layout v2|pilot`; build_p24_tri.sh / build_p24_pilot.sh. v1 extra.prx (e7e25242…) stays the
  release-1.0 module (install.py binds it).

### P2.4 step 2 — as built (Claude, P2.4 step-2 helper, 2026-10-21; notes/phase2/P2.4-reflect.md)
- **Stub list STUBS_V2R** (XSTB version 2 / count 32 unchanged; `p24_stubs.py --layout v2r`): 0-5 and 7 as step 1, plus
  **6 CROWN_DRAIN** (B 0x08AEC160 `jal`, the original float load stays in the delay slot; fallback = the displaced
  multiply + return), **8 REFLECT_C1** (E 0x0880A384 `j`, mid-code; fallback = the displaced word + jump back to
  0x0880A38C), **9 REFLECT_C2** (E 0x0880A408; fallback jumps to 0x0884A53C), **10 REFLECT_C3** (B 0x08ADA22C; to
  0x08ADB330), **11 REFLECT_C4** (E 0x08808B74; fallback = the release's C4 transform, which picks the guard argument
  from flag bit 0x4000 and jumps on to 0x08807860, **never replaced by the module**), **12 REFLECT_C7** (B 0x08ADB32C
  outcome-table word = &STUB_12; fallback to 0x08ADAD34). Temporary 29-31 removed. **abi_hash 0x3B25613D**;
  fallbacks 0x089C1F20-0x089C1FC0 (40 words). R4's install-time words at 0x08ADAAAC (a bound of 8) and 0x08ADB328 stay
  (checked, never written).
- **Battle cave removed:** OVL_BATTLE_APP.ELF = the clean 1,596,312 B (ELF header, shstrtab, section headers, ISO record
  size = clean; freed sector tail zeroed). Rule kept from here on: no package code inside a game file.
- **Engine 2.2.0** (extra_v2.prx 666aa688…; step-1 2.1.1 frozen in extra/tri2/, `install_engine.py --engine v2-tri2`):
  C `beh_c1/c2/c3/c7/helm`, `is_reflect_ex` (REFLECT_GUARD mask), wrappers `wrap_c1` (j-entered mid-code, frame 0x50),
  `wrap_c2/c3` (CALLSITE_WRAP 0x50; C2 reads the caller's sp+0x200 at 0x250), `wrap_c7` (entered by FUN_08adaa68's indirect jump,
  frame 0x20, sets s1 = guarder as R4; exits v0 = 1 + 0x08ADAD38 or vanilla[12]), `wrap_helm` (asm owner fast path,
  slow path frame 0x80 keeps every caller-saved int / float register R4 kept). Masks: HELM = ITEM_EFFECTS rows owning an
  item_fx EX_DRAIN item (float bits, 0 < v ≤ 4); C2 = REFLECT_GUARD | EE_GUARD rows. Status: +0x154 owners_reflect
  (low 16 REFLECT_GUARD, high 16 C2), +0x158 owners_helm (size still 0x160).
- **Overlay-resident guard (§9 / P2.4 Q4, confirmed at runtime):** the loader's copy of the resident overlay's ELF header
  at 0x089DD46C: p_vaddr (0x089DD4A8) = 0x089DD4C0 and p_filesz (0x089DD4B0) 0x185AB0 ≤ x ≤ 0x185CB0 = battle overlay
  (menu 0x17BD98, extra 0x5EF8). C1/C2 (EBOOT hooks calling battle code) do nothing when it fails.
- §10 wrapper rule applied: 5 new `gt_` thunks (0x08836DAC, 0x08808468, 0x089A38E0, 0x089A3BC8, 0x08ADA2F8); the C2 hit
  direction and the C7 aim vector live in 16-aligned module .bss (R4: stack frames).
- **equiv.py `--allow-shrink IMAGE:0xLO-0xHI`**: the only accepted way for a code image to change size (cut of A's
  load-segment end + shifted ELF bookkeeping, then word compare; printed as a SHRINK line, json "shrinks").

### P2.4 step 3 — as built (Claude, P2.4 step-3 helper, 2026-10-21; notes/phase2/P2.4-shield.md)
- **Stub list STUBS_V2S** (`p24_stubs.py --layout v2s`, XSTB version 2 / count 32): STUBS_V2R + **20 ITEM_SHIELD** (E
  0x088079AC becomes `jal STUB_20`, delay slot unchanged; feature ITEM_EFFECTS; fallback F20 at 0x089C1FC0 jumps to
  the original callee 0x089A3890; fallbacks
  0-12 keep their v2r addresses, fallback area 0x089C1F20-0x089C1FC8). **abi_hash 0x3BC585AE**. Layout v2s also puts
  EBOOT 0x089A8D24-0x089A8D80 (R4 SHIELD) and 0x089A8DE4-0x089A8F0C (R4 EE_B + EE state) back to the CLEAN words (= the
  never-called vanilla function 0x089A8B14; `p24_refscan.py`: no other user after step 2). equiv id `p24_freed`.
- **Engine 2.3.0** (extra_v2.prx d5cc2cba…; step-2 2.2.0 frozen in extra/reflect/, `install_engine.py --engine
  v2-reflect`, build_p24_reflect.sh still 48977859…): `beh_shield` = R4's integer math bit for bit (s16 power × q7 >> 7,
  16-bit store; q7 = round(REFLECT_POWER × 128) = 192 computed at load, 0 < v ≤ 3), owner test = registry mask
  `g_shield_owners` (ITEM_EFFECTS rows owning a REFLECT_POWER item) + live loadout; `wrap_shield` = CALLSITE_WRAP 0x50,
  tail vanilla[20]; no game call. Status **+0x15C owners_shield** (was reserved; size 0x160).
- **Registry:** `params.shield_pct` RETIRED (slot kept, 0; registry.py refuses it); item_fx REFLECT_POWER validated
  (0 < v ≤ 3, whole 128ths). Rule: an item's battle effect lives in item_fx only, never in the row's params.

### P2.4 step 4 — as built (Claude, P2.4 step-4 helper, 2026-10-21; notes/phase2/P2.4-items.md)
- **Stub list STUBS_V2I** (`p24_stubs.py --layout v2i`, XSTB version 2 / count 32): STUBS_V2S + **13 ITEM_ENSURE** (E
  0x088B8FD0 `j`, function entry, sp already −16; fallback = the displaced first word + jump back to 0x088B8FD8),
  **14 ITEM_NEWGAME** (E 0x088B8778; fallback to 0x088B87AC), **15 ITEM_ELIG** (E 0x088C1AFC; to 0x088C1998),
  **16 ITEM_ROWMASK** (E 0x088C132C / 0x088C1364, mid-code; fallback = the displaced load + return), **17 ITEM_MENU**
  (menu 0x08AF9004 / 0x08AF8ED8; to 0x08AF8E14), **18 / 19 ITEM_PICID3 / PICID0** (E 0x088D56A4 / 0x088D56D8 /
  0x088D5714, mid-code, t0 live; fallback = the displaced add + return, index minus 1), **21 ITEM_STASH** (E
  0x088BE63C `j`; fallback = the displaced stack store + jump back to 0x088BE644), **22 ITEM_SCALE** (E 0x088BE96C,
  t0 = 5th argument; to 0x088BDB2C), **24 PANEL_LIT** (menu 0x08AFF32C, mid-code; fallback = the displaced mask +
  return).
  **abi_hash 0x2F2EAE84**; F0-F12 and F20 keep their v2s addresses, F13..F24 follow from 0x089C1FC8 (fallback area
  0x089C1F20-0x089C2028). p24_stubs writes menu-overlay site words too (OVL_MENU_APP.ELF, sector 185056). Layout v2i
  also puts EBOOT 0x089A8B94-0x089A8D24 + 0x089A8D80-0x089A8DE4 (rest of R4's EXITEMS) and the dead jump table
  0x089D1FB4-0x089D2084 (R4's STASH / SCALE / SCR / TAB) back to the CLEAN words: 0x089A8B94-0x089A8F0C is one 222-word
  block of unreachable vanilla code again. equiv id **`p24_freed_items`**; `stub_hooks` += the 13 words.
- **Engine 2.4.0** (extra_v2.prx 69e02f65…; step-3 2.3.0 frozen in extra/shield/, `install_engine.py --engine v2-shield`,
  build_p24_shield.sh still 5267025c…): C `beh_item_ensure / newgame / elig / rowmask / menufix`, `beh_picid`,
  `beh_panel_lit`, `beh_item_scale`; wrappers `wrap_ensure` (asm fast path, frame 0x20), `wrap_rowmask` / `wrap_picid3/0`
  / `wrap_panel_lit` (asm fast paths with R4's scratch registers, MID_SAVE 0x50 for package items), `wrap_scale` (fast
  path, frame 0x30 keeps t0), `wrap_stash` (asm only), `wrap_menufix` (frame 0x10, vanilla callee first, asm fast path:
  the Shop / Buy list frames call it ~29,600 times), `CALLPOST_WRAP` 0x30 for ELIG, CALLSITE_WRAP for NEWGAME. No game
  call from these C functions. **Menu-overlay resident guard** `menu_resident()` = copied overlay header p_vaddr
  0x089DD4C0 and p_filesz 0x17BD98..0x17BF98 (MENU_FIX, PANEL_LIT; counter `menu_guard`).
- **Registry (EXTRA.REG v1, min engine now 0x00020400):** item_owner byte = owner (bits 0-5) | **bit 7 start-owned** (bit 6
  must be 0; an owner byte without a row / a start bit without an owner = bad section). Aux **kind 3 EXPAGE** (u16 face_pic,
  u16 name_pic: the EX Mode page header pictures for this owner; the EX scene bases 15395 / 15363 are module constants)
  and **kind 4 SCALE** (14-B entries: u16 item, u8 slot 0..3, u8 0, u16 points[5]; piecewise linear in 32-level
  segments, level from the stashed record +1). **`params.crown_drain` RETIRED** (f32 at params +0x0C written 0, refused
  in a source); item_fx EX_DRAIN is the one source. Item ownership for the equip / list / menu / panel stubs counts only
  rows with ITEM_OWNER.
- **Status block size 0x170:** +0x160 owners_items (ITEM_OWNER rows | start-owned rows << 16), +0x164 owners_pics_scale
  (EXPAGE rows | ITEM_SCALING rows << 16), +0x168 item_info (start items | scale entries << 8 | item range << 16),
  +0x16C menu_guard.
- **Tool fix:** p24_refscan.py lists every data word that points into a range (it used to skip words that decode as a jump
  or call, i.e. every EBOOT pointer). With this step P2.4 has no owner-33 compare / package constant left in a code
  image (disc total: 2 compares = P2.3's BGM fallback + party pictures).

### P2.3 steps 3-7 — as built (Claude, P2.3 lookups helper, 2026-10-21; notes/phase2/P2.3-home.md + P2.3-pictures/museum/oqface/flags.md)
- **Home decision (P2.3 Q1/Q8/Q2):** table-shaped lookups = **OXT, installer-written per-owner tables in the EBOOT block
  P2.4 freed** (v2 design item 2 confirmed with numbers: 4 instructions / 1 load per call = R4's remap, works without
  the module, checkable on the disc). Registry data at run time only for the BGM mode-7 fallback (REG_ROW, decision 4)
  and the Jukebox gates (flag ranges). New key strings: KEY_POOL in the same block (Q8). Menu gap 0x08B59258..: not used.
- **OXT block (EBOOT 0x089A8B94-0x089A8F0C, written by `tools/pkg/engine/patches/p23_lookups.py`):** header
  `"OXT1" | u16 36 | s16 −2` (the −2 doubles as PIC_IDX[−1]); PIC_IDX s16[36] 0x089A8B9C; PARTY_FRAME u16[36]
  0x089A8BE4; SETUP_OFF s16[36] 0x089A8C2C (frame-row byte offset 10 · row); VIEWER_OWNER s16[36] 0x089A8C74 (Museum
  record → owner); REC_ICON u32[36] 0x089A8CBC; PANEL_SPRITE u8[36] 0x089A8D4C; OQ_PAIR u32[2] 0x089A8D70 (owners 33,
  34; layout | picture << 16, −1 none); REC_APPEND u8 0x089A8D78 (6th Records append, vanilla 23); KEY_POOL 2 × 8 B
  0x089A8D7C; helpers FLAGPKG 0x089A8D8C (25 w), BGM_FB 0x089A8DF4 (14 w), OQ_BUILD 0x089A8E2C (34 w), REC_HELP
  0x089A8EB4 (2 w); 20 words spare. Vanilla columns = the clean images' values (incl. vanilla's reads past a table's
  end); package columns from the registry SOURCE (row.pic_slot / party_frame / setup_frame / museum_record /
  panel_sprite / oq_face_*, install.records_icon / records_append). Tables are indexed by owner without a bound (owners
  0..35 exist). `p24_stubs.py` treats the block as "p23 (kept)" once the header is there.
- **Sites (all in place; R4's owner-33 words gone):** 12 picture remaps + party list → PIC_IDX; party slots FUN_08B2C330
  = clean code + PIC_IDX in s6 + PARTY_FRAME; setup banner player/CPU → SETUP_OFF + PIC_IDX; Characters panel
  FUN_08AFF218 → PANEL_SPRITE; Museum FUN_08A3200C = clean with base VIEWER_OWNER, FUN_08A32284 clean; Records icon base
  → REC_ICON; Records 6th append → `jal REC_HELP` (tail call); OQ builder FUN_08A62530 clean + scene vtable 0x08A636BC
  → OQ_BUILD; Jukebox gates ×3 → `jal FLAGPKG`; BGM case 7 + case 0xC + jump-table entry 12 clean, case-7 tail →
  `j BGM_FB`. code_sites.json ids `p23_pictures`, `p23_museum`, `p23_oqface`, `p23_flags`, `p23_oxt` (exact changed words).
- **FLAGPKG ABI:** in a1 = flag, out a2 = 1 when a1 lies in a published gate-flag range, clobbers at + a2 only (+ ra via
  jal; v0/v1 kept on a 16-B frame). **BGM_FB:** entered by `j` with v0 = pick, uses REG_ROW (at, v0) and checks
  row.owner == owner (an empty slot inside REG_COUNT is not a row).
- **EXTRA.REG v1 header change (engine 2.5.0, MIN_ENGINE 0x00020500):** +0x20 franges_off, +0x24 u16 frange_count,
  +0x26 u16 0; entries u32 lo | count << 16 (runs, sorted, non-overlapping, count ≥ 1, ≤ flag 5119, ≤ 16). Older
  files (min engine < 2.5.0) carry the one-range bitmap at +0x20/+0x24/+0x26; registry.py decodes both.
- **REG block (XSTB header + 0x18):** +0x20 **FLAG_PTR** = &module g_franges, +0x24 **FLAG_N** (was "FLAG_LO|BITS",
  never published before 2.5.0); publish order REG_PTR, FLAG_PTR, FLAG_N, REG_COUNT, FN_PTRs; module_stop clears them.
- **Engine 2.5.0** extra_v2.prx 4e546662…6bb4 (step-4 module 2.4.0 frozen in extra/items/, `install_engine.py --engine
  v2-items`, build_p24_items.sh still 807e09fc…). Status +0xAC `flag_ranges` = ranges | flags << 16. Stub ABI unchanged
  (abi_hash 0x2F2EAE84).
- **Result:** final disc dumps/ULUS10566-P23-flags.iso 39d82a75…8fb3: owner-33 compares = **0**; other owner/package immediates
  = 5, all P2.5's save_record_hooks; picture constants 0. Menus within ±4 % of the oracle (P2.3-pictures §3).

### P2.5 — as built (Claude, P2.5 save-records helper, 2026-10-22; notes/phase2/P2.5-saves.md)
- **Save records are installer data + one EBOOT helper, no module:** record slot index = 57 − owner (rec = save base +
  0x1FECC + slot·0x10A8 + 0x10C); friend-card cap = lowest installed slot. The registry row's `record_slot` stays
  informational (validated = 57 − owner); nothing reads it at run time.
- **SRC1 block, EBOOT 0x089C2340-0x089C2508** (TRI-range tail after the XSTB v2 fallbacks, written by
  `tools/pkg/engine/patches/p25_saves.py`): +0x00 `"SRC1"`, +0x04 u8 REC_CAP (= both cap words; 25 = no package
  record), u8 36, u8 1 (version), u8 0; +0x08 REC_MARK u8[36] (catch-up marker per owner, 0 = no package record; Sora
  0xC1); +0x2C REC_FLAGS u8[36] (bit 0 LEGACY: marker 0 counts as valid in the migration; Sora only); +0x50 PKG_REC
  (94 words). Indexed by owner without a bound check beyond `owner < 36` (owners 0..35).
- **PKG_REC(a0 = owner) → v0 = record or 0** (frame 0x20, keeps s0-s7 / ra, clobbers t0-t3 / a0-a3 / v0 like any game
  call; calls game FUN_088f526c, FUN_088cbbb4, FUN_088cbd24): REC_MARK = 0 → 0; count > REC_CAP → count = REC_CAP, then
  for every slot i in REC_CAP .. min(old, 25) − 1 that is not a valid record of owner 57 − i: drop card i with
  FUN_088f526c and clear that record's first byte; then set-up (FUN_088cbbb4 when the record's owner byte ≠ owner)
  and catch-up (when byte 0x777 ≠ MARK: FUN_088cbd24 with the record, 1 and the level, then write the mark). GET_RECORD FUN_088CB164 calls it for owners outside the vanilla list (0 → vanilla blank record);
  OQ has-record FUN_089293DC = vanilla bound 1..34 and REC_MARK ≠ 0, else vanilla. The R4 SORA_REC cave (dead
  FUN_088CB2C0) is clean again.
- `p24_stubs.py` treats the TRI range as `v2i+p25` while the SRC1 header is there (tail kept; rollback refused). equiv id
  `p25_saves` (code_sites.json; the block also lies inside `stub_table`'s range). Registry: install.record_mark (u8
  1..255, required with RECORD_SLOT), install.record_legacy (grandfathered only); EXTRA.REG bytes unchanged.
- Frozen recipe: the P2.3 flags module 2.5.0 + EXTRA.REG in `extra/flags/` (`install_engine.py --engine v2-flags`).
- **Result:** dumps/ULUS10566-P25-saves.iso 8f163258…31c7 (`build_p25.sh`): owner immediates in the code images **0**,
  owner-33 compares **0**; module unchanged (engine 2.5.0, abi 0x2F2EAE84).

### Engine package (P2.8 design 2026-10-21, built in step E1 2026-10-22)
Sources: notes/phase2/P2.8-sora-package.md §1-§2 (design), [notes/phase2/P2.8-build.md](../notes/phase2/P2.8-build.md)
§0-§1 (as built).
- **What the engine base is** (`python3 -I tools/pkg/p28_plan.py words`, re-measured before E1 on the P2.7 engine disc
  P27-capacity 387b0a7e…): of the 1,340 code words that differ from the clean dump, LOADER 53 (P0.2 module loader,
  `patches/extra_prx.json`) + ENGINE 890 (XSTB, stub hooks, fallbacks, the roster-independent part of the OXT block +
  helpers, names C1/C2, P2.3 sites, P2.5 SRC1 code, P2.7 grid code, freed ranges back to clean words) + ENGINE_R4 184
  (generic engine words whose bytes came only from Sora's release patches: menu picture remaps, OQ slot face, Jukebox
  gates, setup banner, assistdup, menu_clock, the 38 save-hook words P2.5 kept as generic, …) = 1,127 words. The rest
  is generated for the roster (ROWGEN 199, OXT 8, SRC1 3, PANEL_TEX 3: never stored). **Sora-only words left: 0.**
- **As built, the engine package stores 890 words** = `engine_base.json` 832 + loader 53 + `menu_clock` 5. The other
  237 engine-base words lie inside generator regions (equal for the Sora roster and the empty roster); the installer
  writes them for every roster, so the package leaves them out.
- **The writers need a clean before-state (or the frozen package).** `p24_stubs.py`, `p23_names.py` and
  `p23_lookups.py` guard every site against the **R4** words, so they only run on an oracle copy. From the clean dump
  the ENGINE_R4 words come from nowhere. P2.8 step E1 therefore froze the engine as a package (`packages/engine`,
  `kind: engine`: EXTRA.PRX v2, produce `eboot_plain`, patch files with **old = clean words**, the `code_cave`
  allocations; [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md) §16). The in-place `--rollback` of the dev writers stays for
  oracle-based test discs only.
- An engine-only disc (no fighter package) gets: rowgen with an empty roster (the ablt floor 0x088B1CF0), the OXT
  vanilla columns, the 33 vanilla grid rows, no EXTRA.REG (reg_state −1 → every stub vanilla), no EXTRA.IDX. **Built
  2026-10-22** (`dumps/ULUS10566-P28-engine.iso`); in PPSSPP it boots to the menus and plays a vanilla battle, with
  EXTRA.IDX −1, registry −1, stubs 1 (table OK, nothing to write), ABI match (P2.8-build §1).

### P2.7 — as built (Claude, P2.7 capacity helper, 2026-10-22; notes/phase2/P2.7-capacity.md)
- **GRD1 block, EBOOT 0x089C2140-0x089C2340** (TRI-range tail right below SRC1; `p24_stubs.py` state `v2i+p25+p27`
  keeps it): `"GRD1"`, u8 rows (33 + packages with `install.qb_row: "append"`), u8 capacity 34, u8 1, u8 0; 34 × 12-B
  QB / select-grid rows (u16 pic, u16 name pic, u16 logo, u16 char number, i32 owner; row 32 = the random cell);
  GRID_CAP (22 words at 0x089C22E0); 2 clean words. Rows + header = installer data (rowgen `moved_rows`, written by
  `tools/pkg/engine/patches/p27_words.py`), code = `p27_grid.py`. TRI tail still free 0x089C2028-0x089C2140 (70 words).
- Menu sites: getter FUN_08a85ecc (the only reference to the old table 0x08A864D0) → 0x089C2148; builder 0x08A8522C
  `j GRID_CAP / nop` (clamp the entry list to the capacity byte, −1 into dropped entries, s7 = 2n, back to the builder's
  own layout path; no change for ≤ 34 entries). Row bounds 0x08A85100 / 0x08A7F30C / 0x08A8019C are installer
  immediates (rowgen `qb_grid_bounds`: 32 / 33 / 33 vanilla, rows with an appended row). The old menu table stays as
  it is (reused rows mirrored); nothing reads it. No module code; works without EXTRA.PRX.
- **One generic installer-word writer** `p27_words.py`: rowgen (all code-image tables + immediates incl. GRD1, title
  call D13, KEY_POOL D5b, uicn buffer, grid bounds) + OXT roster columns + SRC1 roster data. Sora-only = the P2.5
  disc in every word except GRD1. New keys live in the OXT KEY_POOL (EBOOT 0x089A8D7C, 2 × 8 B); the 5 key tables
  point there (EBOOT is mapped under every overlay).
- **Title call generated** (rowgen kind `title_call`; registry `install.title_call {sqe, ddd, days}`, index = 34 +
  position): R4's layout generalised, 0 new code words, bound 0x089DEC04 = N; Sora-only = R4's 155 words; 36 callers fit.
- Registry: owner > 34 = ERROR; OQ_FACE for owners 33/34 (P2.3's OQ_PAIR); ITEM_CEILING from owner_tables
  `item_rows.ceiling` (one source; `tools/pkg/engine/gen_limits.py` keeps beh.c's generated `ITEM_CEIL` line equal).
- Result: dumps/ULUS10566-P27-capacity.iso (sha in the note §5); module unchanged (engine 2.5.0, abi 0x2F2EAE84),
  EXTRA.REG unchanged (74eeaa85…). `p28_plan.py words` on P27: ROWGEN 197 (the 155 title-call words now generated),
  SORA_LEFT 68 = only the P2.5 save words of p28's pre-P2.5 rule (see the P2.5 note above).

### P2.8 E1-E3 — as built: the engine package and installer layout C (P2.8 in progress)
Claude (P2.8 build helper), 2026-10-22; [notes/phase2/P2.8-build.md](../notes/phase2/P2.8-build.md). **Status: in
progress.** Steps E1-E3 are built and their first discs pass the checks below; the full acceptance runtime list, the
Vita check (P2.12) and the remaining steps are still open.
Words used here: a **package** is a folder the installer reads (manifest + files + rows + patches, [PACKAGE-FORMAT.md](PACKAGE-FORMAT.md));
the **engine package** (`packages/engine`) is the part every fighter needs; a **fighter package** (`packages/sora-C`) adds
one fighter; the **roster** is the list of fighter packages on one disc; **installer words** are code-image bytes the
installer computes from the roster's registry files (never stored in a package); **layout C** is the install mode that
puts all of this together on a copy of the player's clean ISO.
- **Engine package** (`packages/engine`, engine 2.5.0, 26,682 B) = `tools/pkg/engine/make_engine_pkg.py` (engine disc `dumps/ULUS10566-P27-capacity.iso` minus the
  clean dump). Contents: `files/iso/PSP_GAME/USRDIR/DATA/MODULE/EXTRA.PRX` (engine 2.5.0 = the frozen
  `extra/flags/extra_v2_flags.prx`, abi_hash 0x2F2EAE84), `produce: eboot_plain` (the decrypted EBOOT, no bytes shipped),
  three patch files with **old = clean words** (890 words in all): `extra_prx.json` (module loader, 53 words), `menu_clock.json` (menus at
  333 MHz, 5 words; Mat Q-P28-M1 = yes, in for every roster; `make_engine_pkg.py --no-menu-clock` leaves it out) and
  `engine_base.json` (832 words: XSTB stub table + hooks + fallbacks, OXT helper code, names C1/C2, P2.3 sites, P2.5
  SRC1 code + GET_RECORD / OQ has-record, P2.7 grid getter + GRID_CAP, the 38 R4 save-hook words P2.5 kept as generic),
  and the `code_cave` allocations (EBOOT 0x089A8B24-0x089A8F0B, 0x089C1C8C-0x089C250F, 0x089D1FB4-0x089D2083).
  No owner, no registry row.
- **Installer words** = `tools/pkg/rostergen.py` (the logic of `patches/p27_words.py`, in memory): rowgen tables /
  immediates incl. the GRD1 block, OXT per-owner tables, SRC1 REC_CAP / REC_MARK / REC_FLAGS, panel_tex. The engine base
  never contains a word inside a generator region (237 such words of the P27 disc are equal for the Sora roster and the
  empty roster; the generator writes them). An empty roster is valid: vanilla columns, GRD1 = the 33 vanilla rows, the
  ablt floor.
- **Layout C** (`tools/pkg/install.py --layout C`, contents from `tools/pkg/layoutc.py`): produce eboot_plain → every
  package's patches (old = clean) → installer words for the roster (each byte must still be clean before it is written)
  → container rows of all packages + the roster's generated rows (grwp) through the format-1.1 codecs → whole files →
  `DATA/EXTRA.REG` = `registry.py build(roster)` (none for an engine-only disc). Placement as layout B: vanilla
  PACKAGE_INFO, the packages' PACKAGE files in `DATA/EXTRA.IDX`; an engine-only disc has no EXTRA.IDX and its PACKAGE.BIN
  record is left alone. Layouts A and B are unchanged (old vs new `plan()`: same writes on sora-R4; B still binds the
  v1 `extra/extra.prx` e7e25242…).
- **Discs:** `dumps/ULUS10566-P28-engine.iso` (engine only) and `dumps/ULUS10566-P28-soraC.iso` (engine + Sora), shas in
  the P2.8-build note. P28-soraC = P27-capacity in every code word and every game file (equiv content IDENTICAL, 0 code
  words); vs the oracle IDENTICAL with the 13 P2.7 allow ids, 1217 words. At boot the module reports EXTRA.IDX state 2
  (249 rows) + registry state 2 + stub state 2 at the same time (first disc where all three are live). Engine-only:
  idx −1, registry −1, stubs 1 (table OK, nothing to write), vanilla roster, battles run.
- **Still open:** E6 visibility gate (unlock walker lists owner ≥ 33 only with a REG_ROW), E7 roster_id in EXTRA.REG
  +0x40 / EXTRA.IDX +0x20 (module check, reg_state −9 on a mismatch): not built (P2.8-build §6).
