# Engine module EXTRA.PRX (v1.0) and its installer

Code: `tools/pkg/engine/`. This module ships on the Sora release disc. Earlier research steps are referred to by
short labels: **P0.2** proved the game can load our own module, **P0.3** measured free memory, and **P0.7** proved an
extra file index works. "Layout A" is the older disc layout (Sora's files added to the game's own index); "layout B"
is the release layout (the game's index untouched, Sora's files in our index). Version 2, planned for Phase 2, is
summarised at the end.

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
5. If rows are left: JIT-safe guard on 0x08871420 (cache sync; vanilla `jal 0x08871288` = mode 1, PPSSPP block
   marker with vanilla neighbours = mode 2), one aligned store `jal xidx_tramp`, cache sync, read back.
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

## Version 2 (planned for Phase 2)

Today about 80 places in the game's code and tables say "owner 33 = Sora". Version 2 replaces them with one lookup
table, so a new fighter becomes a package plus one table row, with no new game code. The design is written but
nothing is built yet; see the [roadmap](ROADMAP.md#phase-2-the-multi-fighter-engine).

- **Three ways in.** (1) Install-time data: tables inside the game's own files that the installer fills for each
  package fighter (no runtime code). (2) Registry lookups: places that asked "is this owner 33?" ask a small EBOOT
  helper for "this owner's row" instead. (3) Behaviour stubs: places that run Sora-only logic (Trinity Limit, Reflect
  guard, item effects, EX run speed) call a fixed stub that jumps to the module's code.
- **Where it lives.** Once Sora's special code moves into the module, three unused EBOOT ranges become free. A fixed
  stub table (32 slots) goes there, plus five lookup helpers.
- **Safe without the module.** On disc, every stub points at a copy of the original game instructions. With no
  module, no registry or a broken file, every vanilla fighter behaves exactly as in the original game.
- **No new instruction writes.** The module only writes data words (pointers), never instructions, so the emulator's
  JIT problem from P0.7 can't come back. The `EXTRA.IDX` hook stays its only instruction write.
- **Registry file.** A data file `EXTRA.REG`, written by the installer and served through `EXTRA.IDX`, holds one
  64-byte row per extra fighter (up to 31). The module itself stays identical for every roster.
- **Size.** Roughly 20–25 KB of module for Sora, about 10 % of the largest free memory block at boot.
- **Status block layout 2** only appends fields to layout 1, as required above.
