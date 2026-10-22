# Fighter package format (v1.0, v1.1)

This spec describes a **package**: one folder with everything a fighter adds to the clean game. It is part of
Phase 1 (see the [roadmap](ROADMAP.md)). Format 1.1 (§16) adds identity keys, the registry inside the package and
the engine package for layout C (Phase 2 task P2.8, **in progress**). Nothing here touches an ISO.

Some tools named here are in the private working project and not published yet:
[list](REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).

- Machine-readable parts: `tools/pkg/schema/` (manifest / rows / patches / order schemas + `spaces.json`).
- Checker: `python3 -I tools/pkg/validate.py PKG [PKG ...]`. Sealer: `python3 -I tools/pkg/pkgformat.py seal PKG`.
- Extractor and installer (since the 20 October 2026 refresh): `tools/pkg/extract.py`, `install.py`,
  `containers.py`, `pkgapply.py` and `code_sites.json` (see §15). The small worked example (`tools/pkg/examples/mini/`,
  dummy data) is not in this snapshot.

Phase 1 task labels used below: **P1.2** extractor (reference build minus clean disc → package), **P1.3** installer
in layout A (rows added to the game's own index), **P1.4** engine module, **P1.5** installer in layout B (the game's
index untouched, our own `EXTRA.IDX`; this is the release layout), **P1.6** equivalence checker, **P1.8** release
identity, **P1.9** release patch, **P1.10** patch app. **R0** is the reference build the extractor compares with.

## 0. In plain words
A **package** is one folder that holds everything one fighter (or the engine) adds to the clean game:
- `manifest.json` — who it is (owner number, key like `sev120`, names), what it needs, **every number it takes**
  from shared number spaces (effect ids, sound banks, model ids, flags, picture numbers …), the list of its files
  and a sha256 for every file;
- `files/` — whole files it adds or replaces (its battle file, models, voice bank, music …);
- `rows/` — small edits inside **shared** game files (one row of the ability table, a subtitle, a voice-list row in
  another fighter's list …), one JSON file per table, named by the table's id in `tools/dlc/owner_tables.json`;
- `patches/` — code words for today's "if owner is 33" special cases (layout A; Phase 2 replaces them);
- `order.json` — only where the order of appended rows matters;
- a `features` block — the switches and numbers the Phase-2 engine registry will read (Reflect guard, EX speed,
  burst controller, item effects …).

The installer (P1.3/P1.5) reads clean ISO + packages and writes a new ISO. The validator proves a package is
complete and consistent before anything is built, and that several packages don't take the same numbers.

Making a new package: [modding/MAKE-A-FIGHTER.md](modding/MAKE-A-FIGHTER.md).

## 1. Folder layout
```
<package>/
  manifest.json                     identity, allocations, file list, features, inventory (sha256 of every file)
  files/package/<PACKAGE path>      file served through the PACKAGE index (PACKAGE_INFO in layout A, EXTRA.IDX in B)
  files/iso/PSP_GAME/<ISO path>     loose ISO9660 file (DATA/BGM/*.AT3, DATA/MODULE/*.PRX, …)
  rows/<owner_tables id>.json       row edits inside shared containers, one table per file
  patches/<owner_tables id>.json    code edits of one code site (EBOOT / menu overlay / battle overlay)
  order.json                        optional: append order where it is not key order
```
Nothing else may be in the folder (the validator rejects stray files; READMEs live outside the package).

## 2. Determinism rules
1. **Canonical JSON** for every `.json` in the package: UTF-8, no BOM, keys sorted, 2-space indent, `", "`/`": "`
   separators as Python's `json.dumps(sort_keys=True, indent=2, ensure_ascii=False)`, LF line ends, one final
   newline. `pkgformat.canon_bytes()` writes it; the validator re-serialises and compares bytes.
2. **Sorted lists**: `files` by (target, path); `rows`/`patches` id lists alphabetically; rows inside a rows file by
   (ns, key tuple in `key_fields` order; integers before strings); patch edits by (image, va); allocation `ids`
   ascending, ranges `[lo, hi]` inclusive, no overlap.
3. **No volatile data**: no timestamps, user names, host names or absolute paths anywhere in a package. Provenance
   is recorded only as hashes (`provenance.*_sha256`, `tool`).
4. **Hex** is lowercase: bytes as plain hex pairs (`"0308"`), addresses and 32-bit words as `"0x%08x"`.
   Floats only inside `features.*.params` (Python `repr`, shortest round-trip).
5. **Hashes**: `inventory` = `{relpath: {sha256, size}}` for every file except `manifest.json`;
   `package_sha256` = sha256 of the canonical manifest without its `package_sha256` field (so it covers every file
   through the inventory). `pkgformat.py seal` refreshes both; the validator recomputes them.
6. **Installer determinism** (contract for P1.3/P1.5): packages applied in dependency order (`requires`,
   `install_after`), ties by `id`; inside a package the fixed apply order of §10; new data appended in
   (target, lower-case path) order at 2048-byte sector alignment. Same inputs → same output ISO sha256.

## 3. Versioning
- `format_version` = `"MAJOR.MINOR"` in the manifest and in every rows/patches/order file. Current: **1.0** (layouts A/B,
  release 1.0) and **1.1** (layout C, the engine; §16).
- **Minor** bump = additive only (new optional field, new allocation space in `spaces.json`, new `produce` transform).
  A validator/installer of 1.x refuses files newer than its own minor (no silent ignoring of fields it does not know).
- **Major** bump = incompatible; new schema `$id`, old packages are converted by a tool, never reinterpreted.
- Package `version` is semver (`1.0.0`) of the package contents; `requires` uses `>=X.Y.Z` or `==X.Y.Z`.
- The engine is a package too (`kind: "engine"`, P1.4: EXTRA.PRX + loader patch set); fighter packages that need
  layout B list it in `requires`.

## 4. Distribution rule (derived game data)
Packages in the repo contain **derived game data** (Sora's battle file and model start from Cloud's; rows carry
game bytes). Hence `"distribution": "never-publish-raw"` is required in every manifest, and:
- a package folder is **never** published, attached or uploaded raw;
- releases are **deltas against the player's own clean ISO** (P1.9: VCDIFF whose ADD data is only our bytes) plus our
  own tools/art (P1.10);
- `files[].origin` marks `derived` (made from game data) vs `own` (our art, our audio); this helps a later decision on
  memory-stick packages but does not relax the rule above.

## 5. manifest.json
| field | req | meaning |
|---|---|---|
| `format` | ✔ | `"dissidia012-package"` |
| `format_version` | ✔ | `"1.0"` |
| `id` | ✔ | slug, unique across installed packages (`sora`, `engine`) |
| `version` | ✔ | semver of this package |
| `kind` | ✔ | `fighter` (needs owner + key) · `engine` · `content` (e.g. music only) |
| `owner` | fighter | owner number 1..255 (Sora 33, next 34); unique across packages |
| `key` | fighter | file key `^[a-z]{3}[0-9]{3}$` (`sev120`); unique |
| `display_names` | ✔ | `{EN, FR, DE, IT, ES, JP}` → name; `EN` required (informative; in-game names are rows) |
| `distribution` | ✔ | `"never-publish-raw"` (§4) |
| `base` | ✔ | `{serial: "ULUS10566", clean_iso_sha256?}` |
| `requires` | ✔ | `[{id, version}]` (may be empty) |
| `conflicts`, `install_after` | – | package ids |
| `layouts` | ✔ | which installer layouts the package supports: `A` (rows in PACKAGE_INFO) and/or `B` (EXTRA.IDX) |
| `allocations` | ✔ | §6 |
| `files` | ✔ | §10; one entry per file under `files/` (+ `produce` entries without bytes) |
| `rows` | ✔ | sorted list of table ids that have `rows/<id>.json` (must match the folder) |
| `patches` | ✔ | sorted list of code-site ids that have `patches/<id>.json` |
| `features` | ✔ | §11 (may be `{}`) |
| `release` | – | `{label, param_sfo_bump}` for P1.8 (release string / PARAM.SFO byte) |
| `provenance` | – | `{clean_iso_sha256, reference_iso_sha256, tool, tool_sha256}` (P1.2 fills it) |
| `notes` | – | free text |
| `inventory`, `package_sha256` | ✔ | §2.5 |

## 6. Allocations (every number a package takes)
`allocations` maps a **space** name to a list of entries `{ids | values, ns?, role?, table?, note?}`:
- `ids`: integers or inclusive ranges `[lo, hi]`, sorted; `values`: strings (string spaces);
- `ns`: sub-namespace when the number is only unique inside one container (picture packs, catalog tabs, text groups,
  code images); `role`: what the number is for (`fighter`/`assist`, `unlock`/`viewed`, `snd`/`voice` …);
- `table`: override of the space's owner_tables id (used by `text_index`).

The spaces live in `tools/pkg/schema/spaces.json` (adding one = minor bump). **scope** `global` = must not overlap
across packages (checked by the validator); `owner` = keyed by owner (unique anyway); `package` = file-local,
recorded for the record. Limits marked *warn* are known soft ceilings that need code first (Phase 2); limits that
are plain 0..65535 are generic until P1.2 confirms tighter ones (`fep_id` 0..16383 = 14-bit `id >> 18`, provisional).

| space | owner_tables id | kind | scope | ns | limits |
|---|---|---|---|---|---|
| `ablt_index` | `ablt_rows` | int | owner | – | 0..65535 |
| `assist_row` | `assist_bin` | int | global | – | 0..65535 |
| `battle_tips_row` | `battle_tips` | int | global | – | 0..204 (warn) |
| `bgm_id` | `bgm_entry` | int | global | – | 0..255 (warn) |
| `brain_row` | `brai_seco` | int | global | – | 0..65535 |
| `catalog_item` | `pp_catalog` | int | global | tab | 0..65535 |
| `cmd_record` | `cmd_list` | int | global | – | 0..65535 |
| `code_cave` | `eboot_dead_code` | int (VA) | global | image | 32-bit |
| `comb_id` | `own_battle_file` | int | package | – | 0..65535 |
| `fep_id` | `fep_id` | int | global | – | 0..16383 |
| `fepa_id` | `fepa_ids` | int | package | – | 32-bit |
| `item_id` | `item_rows` | int | global | – | 0..683 (warn: loader/save ceiling) |
| `jobp_stance` | `jobp_stance` | int | global | – | 0..12 (warn: 13-row buffer) |
| `jukebox_group` | `jukebox_voice` | int | global | – | 0..65535 |
| `motion_slot` | `own_battle_file` | int | package | – | 0..65535 |
| `museum_icon` | `museum_icons` | int | global | – | 0..999 |
| `museum_record` | `museum_char_files` | int | global | – | 0..65535 |
| `name_index` | `name_index_eboot` | int | global | – | 0..65535 |
| `objentry_id` | `objentry` | int | global | – | 0..65535; **owner ≥ 34: ≤ 1337** (P0.4 Cosmos rule, error) |
| `picture_number` | `picture_numbers` | int | global | pack path | 0..65535 |
| `plya_id` | `own_battle_file` | int | package | – | 0..65535 |
| `record_slot` | `save_record_slot` | int | global | – | 0..255 |
| `save_flag` | `unlock_flags` | int | global | – | 0..65535 (unlock, Museum viewed, icon viewed, BGM … = one bit space) |
| `sound_bank` | `sound_bank_ids` | int | global | – | 32-bit (snd / voice / assist pairs; Sora 219000/219100) |
| `subtitle` | `voice_subtitles` | int | global | – | 0..1205 (warn) |
| `text_index` | `customize_desc_text` (override per entry) | int | global | `<path>#<group>` | 0..65535 |
| `texture_key_prefix` | `texture_keys` | string | global | – | length 2..16; clash = equal or prefix |
| `voice_line` | `voice_subtitles` | int | global | – | 0..1205 (warn) |

The owner number and key are top-level fields (unique across packages), not allocations.
For Sora the entries are e.g. `objentry_id` 1187, 1436, 1437, 1457..1459 (+ assist rows),
`save_flag` 925 (unlock) / 1263..1270 (KH2 music and icon purchases) / 2993 (icon viewed) / 3681 (viewed),
`museum_record` 35, `museum_icon` 414..417, `item_id` 678..681, `sound_bank` 219000/219100, `voice_line` 1000..1143
+ vs lines, `battle_tips_row` 201, `name_index` 63, `record_slot` 24, `cmd_record` 0x2100..0x2116 — the extractor
derives the real lists from R0. (`owner_tables.json` in this snapshot still lists the older flag numbers.)
**Lesson:** Sora's first music and icon flags (1249..1254) turned out to be flags the game itself sets for level
milestones, so they were moved to 1263..1270. A new package must avoid every number the game's own code writes,
not just the ones its data tables use.

## 7. rows/<owner_tables id>.json
```json
{
  "format_version": "1.0",
  "table": "ablt_rows",              // = file name = an owner_tables.json id (kind data/text/menu-pack/save)
  "row_size": 40,                    // bytes, or null for variable rows (text)
  "key_fields": ["owner", "idx"],    // fields that identify a row inside its ns
  "codec": "ablt.v1",                // optional: decoder that maps raw <-> fields (P1.2 codec registry)
  "rows": [
    {"ns": "pkg:main.bin!system.bin!ablt", "key": {"owner": 33, "idx": 0}, "op": "add",
     "raw": "…", "fields": {…}}
  ]
}
```
**ns** (where the row lives):
- `pkg:<PACKAGE path>[!<inner member>…][#<group>]` — a PACKAGE file, optionally inside nested archives
  (`main.bin!system.bin!ablt`, `main_lang.bin!ability.bin`) and a text group (`text/EN/mess_pk_exmode_0.bin#2`);
  paths after language substitution (`text/EN/…`), case-insensitive like the game's hash;
- `iso:PSP_GAME/<path>` — a loose ISO file; `img:EBOOT|OVL_MENU_APP|OVL_BATTLE_APP` — a data table inside a code
  image (unlock table, name tables, Labyrinth rows; key = index or VA); `save:<name>` — save-format items (Phase 2).

**op**: `add` (needs `raw`) · `replace` (`raw` + `old_raw` guard) · `delete` (`old_raw`) · `patch` (bytes inside one
existing row: `offset`, `old`, `new`, equal length; used when only a few bytes differ, e.g. chrp +0x0C EX damage).
`raw` is what the installer writes; `fields` / `text` are the decoded view for humans and diffs (when a codec exists
the installer checks they agree; raw wins). For tables where the position is the identity (append lists), put the
position in the key (`pos`).

Rules: one table per file; the table id must exist in owner_tables.json; keys unique and sorted; `raw` length =
`row_size` when fixed; a package must not both ship a container whole (`files/`) and edit it with rows; two packages
must not touch the same (table, ns, key) or one replace a file whole that another edits by rows.

**Keys (fixed 2026-10-22, P2.8 §3; applies from format 1.1, §16):** v1.0 / §15 keys `add` rows by their **final** row
index and bytes leaves by byte offset. Those keys do not compose: a second package shifts final indexes and edits the
same count / offset bytes. From 1.1 every row is keyed by **identity** (owner, text entry, model id, picture id,
allocated id, or (owner, k) for append lists); final positions, counts, offset tables and fillers are derived by the
installer, never stored (§16).

## 8. patches/<owner_tables id>.json (code; transitional layout A)
```json
{
  "format_version": "1.0",
  "site": "reflect_guard",           // = file name = an owner_tables.json id (kind code-site / iso-file)
  "set": "owner33",                  // owner<N> (owner-specific, transitional) | engine | generic
  "layouts": ["A", "B"],             // optional subset of the manifest's layouts
  "edits": [
    {"image": "EBOOT", "va": "0x0880a384", "old": "0x…", "new": "0x…"},
    {"image": "OVL_BATTLE_APP", "va": "0x08b62f70", "old_bytes": null, "new_bytes": "…", "append": true}
  ]
}
```
- `image` → file: `EBOOT` = `PSP_GAME/SYSDIR/EBOOT.BIN` (plain, after the `eboot_plain` transform; VA = ELF off −
  0x1018 + 0x08804040), `OVL_MENU_APP` / `OVL_BATTLE_APP` = `PSP_GAME/USRDIR/DATA/OVL_*_APP.ELF` (off = VA −
  0x089DD4C0 + 0x54). Same conventions as `owner_tables.json` `address_conventions`.
- Word edit: `va` 4-aligned, `old`/`new` = the 32-bit little-endian word. Byte edit: `old_bytes`/`new_bytes` equal
  length; `old_bytes: null` only with `append: true` (bytes past the image's clean end — the battle overlay cave
  0x08B62F70.., which grows the file).
- The installer checks every `old` before writing (wrong base = stop), and writes nothing on any mismatch.
- Code room a package fills (dead EBOOT functions, caves) is also declared as a `code_cave` allocation so two
  packages cannot both claim it.
- Two packages editing the same word is an error. Today every owner-33 hook site is single-owner, so a **second
  fighter in layout A cannot reuse those hooks** — that is exactly what Phase 2's generic engine (features + registry)
  replaces. Each patch file therefore links to the feature it implements (`features.*.transitional_patches`).

## 9. order.json (optional)
Only when the final position of appended rows in a shared container differs from key order, e.g. VOLD rows merged
into other fighters' voice lists (`vold_lists`). Each sequence names `table`, `ns`, a `reason`, and lists **every**
row key of that (table, ns) in application order; the keys must exist in `rows/<table>.json`.
Order **between** packages is not here: it is `requires` / `install_after`, ties by package id.

## 10. files/
Each file under `files/` has exactly one entry in `manifest.files`:
`{path, target, action, table, origin, sha256, size, tier?, layouts?, produce?, note?}`.
- `target: package` — `files/package/<path>`; `path` = the PACKAGE path as the game asks for it (after language
  substitution), unique by lower case **and** by PACKAGE hash (CRC-32/BZIP2 of the lower-case path, `pkghash.py`).
  Layout A: appended to PACKAGE.BIN, row in PACKAGE_INFO (`action: replace` = repoint an existing row; `tier` 0..3
  = Data-Install flag, today's builds use 1 for additions; `spot33_installfix.py` semantics). Layout B: appended once,
  row in `DATA/EXTRA.IDX` (replace = override row searched first), tier forced 0, vanilla PACKAGE_INFO untouched.
- `target: iso` — `files/iso/PSP_GAME/<path>`; loose ISO9660 file added or replaced (`DATA/BGM/*.AT3` is read from
  disc0, never through PACKAGE; `DATA/MODULE/EXTRA.PRX` and `DATA/EXTRA.IDX` belong to the engine package — EXTRA.IDX
  itself is generated by the installer, not shipped).
- `action`: `add` (path must be new) or `replace` (path must exist in the clean disc; `validate.py --pkginfo` checks
  both against a PACKAGE_INFO.BIN you extracted).
- `table`: the owner_tables id that owns the file (`fighter_files`, `own_battle_file`, `bgm_files`, `extra_prx`,
  `eboot_plain` …).
- `produce`: the bytes are **not** shipped; the installer derives them from the clean ISO with a named transform and
  checks the result against `sha256`/`size`. v1.0 knows `eboot_plain` (decrypted EBOOT; engine package). Patches to
  EBOOT apply after the transform.
- Shared containers (main.bin, system.bin, main_lang, menu packs, text paks, VOLD lists, collection_param,
  update_list_param, bgm_entry, brai …) should be **rows**, not whole files, so several packages can edit them.
  A whole-file replacement of a shared container is allowed only as a stop-gap (it blocks every other package from
  that file; the validator reports the clash).

## 11. features (Phase-2 registry block)
`features` maps a feature name to `{enabled, kind, table, params?, transitional_patches?, note?}`:
- `kind: behaviour` — engine code switched on per owner with parameters (module code in Phase 2);
  `kind: lookup` — a plain per-owner value the engine looks up instead of an "owner == 33" special case;
- `table`: the owner_tables id it generalises; `transitional_patches`: patch files that implement it today (layout A).
In Phase 1 the installer ignores `features` (the patches do the work); Phase 2 builds the registry row from it and
drops the transitional patches. Names in use (extend freely; the table id is what the validator checks):

| feature | kind | table | params (examples) |
|---|---|---|---|
| `reflect_guard` | behaviour | `reflect_guard` | barrier, voice slot, refill rules |
| `ex_run_speed` | behaviour | `exrun_hook` | `mult` (Sora 1.40, the built value) |
| `ex_damage` | behaviour | `chrp` | flag word (Sora 0xC03) |
| `burst_controller` | behaviour | `burst_controller` | `controller` (`vanilla` id 0..19, or a module such as `trinity`) |
| `ex_burst_sound_skip` | behaviour | `ex_burst_sound_skip` | – |
| `item_effects` | behaviour | `item_battle_effects` | `[{item, effect, value}]` |
| `item_owner` | lookup | `item_code_hooks` | items only this owner may equip |
| `title_call` | lookup | `title_call` | voice id |
| `assist_drop` | lookup | `assist_drop_words` | – |
| `name_index` | lookup | `name_index_eboot` | `index` (Sora 63) |
| `record_slot` | lookup | `save_record_slot` | `slot` (Sora 24) |
| `start_preset` | lookup | `start_preset_table` | preset id |
| `picture_remap` | lookup | `menu_picture_remaps` | per-scene picture numbers |
| `party_frame`, `labyrinth_face`, `records_icon`, `network_name`, `museum_viewer` | lookup | `party_frame`, `labyrinth_face`, `records_icons`, `network_names`, `museum_viewer_owners` | per-owner values |

## 12. How the other Phase-1 tasks use this
- **P1.2 extractor** (`extract.py CLEAN R0 OUT`): file-level diffs → `files/` (+ `table`, `tier` from R0's row,
  `origin derived` unless the bytes are our own art/audio); container diffs → `rows/<id>.json` with a codec per
  container (fall back to `patch` ops with raw bytes where no codec exists yet); EBOOT/overlay word diffs →
  `patches/<site>.json` grouped by owner_tables code-site; allocations from the rows/files it wrote; then
  `pkgformat.py seal` and `validate.py`. Unmatched diff = stop (missing owner_tables entry).
- **P1.3 installer, layout A** — fixed apply order: (1) check clean sha256, refuse OUT == CLEAN / existing OUT;
  (2) `produce` transforms; (3) patches (old-value guard, sorted by image/va); (4) rows per container: decode clean
  container, apply delete → replace → patch → add (key order, or the order.json sequence), re-encode; (5) files:
  package target into PACKAGE.BIN + PACKAGE_INFO, iso target into ISO9660; (6) indexes/directory records. Packages in
  dependency order.
- **P1.5 layout B**: same package, different placement (EXTRA.IDX instead of PACKAGE_INFO; vanilla PACKAGE.BIN
  range untouched); needs the engine package (EXTRA.PRX file + the loader patch set). Patch files are named by owner_tables id, so
  the engine's `patches/engine-loader.json` is `patches/extra_prx.json` (`set: engine`) in this format.
- **P1.6 equivalence** (`tools/pkg/equiv.py A.iso B.iso [--mode content|layout] [--expect-engine]`) resolves every
  game path (EXTRA.IDX first, then PACKAGE_INFO), compares bytes and names differences by owner_tables id.

## 13. Tools
```
python3 -I tools/pkg/validate.py PKG [PKG ...] [--pkginfo PACKAGE_INFO.BIN] [--strict]   # read-only
python3 -I tools/pkg/pkgformat.py seal PKG [--dry]   # canonical JSON + inventory + package_sha256 (writes only in PKG)
```
`validate.py` checks: schemas (built-in JSON-Schema subset, no third-party module), canonical JSON, every file hash
and size, nothing missing/extra, every table/site/feature/allocation table id exists in `owner_tables.json`,
row/patch/allocation rules (incl. owner ≥ 34 objentry < 1338), order.json keys, and across all given packages:
unique id/owner/key, overlapping global allocations, same file/row/code word touched twice, whole-file vs rows
clashes, PACKAGE-hash clashes, requires/conflicts. Tested on `examples/mini` (VALID) and on broken copies
(corrupt file, unknown table, owner-34 id 1400, unsorted rows, non-canonical JSON, schema errors, two packages
with the same numbers — all reported).

## 14. Open points from the first draft

Written before the extractor existed; newer tools settle some of these.
- Exact row sizes / key fields / codecs per table (the example's `ablt_rows` row size 8 is a dummy).
- Whether subtitle ids always equal voice line ids (then `subtitle` can be dropped in a minor bump).
- Tight limits for `fep_id`, `sound_bank`, `picture_number` per pack, catalog tabs.
- Whether any Sora file must stay a whole-file replacement of a shared container in layout A (then list it).
- P1.4 wrote `tools/pkg/engine/patches/engine-loader.json` in its own shape (`words` list, uppercase hex). When the
  engine becomes a package it converts 1:1 to `patches/extra_prx.json` (`set: engine`, `image: EBOOT`, lowercase
  `va`/`old`/`new`); `engine.json` maps to the engine manifest's `files` entry for `DATA/MODULE/EXTRA.PRX`.

## 15. Settled by the extractor

The extractor (P1.2, `tools/pkg/extract.py`) settles most of §14 without a schema change: every rows file uses the
key field `at`, data tables inside code images are rows with `ns: img:<IMAGE>`, and code-word differences are grouped
by `tools/pkg/code_sites.json` (address range → owner_tables id, the script that writes it, a note).
- 2026-10-20 (release candidate 3): new code site `menu_clock` (`spot33_menuclock.py`: EBOOT 0x08860DF8-FF,
  0x08860E90-97, 0x08860EA0-A3 → `patches/menu_clock.json`); new `grwp` rows (the Max CP growth table in
  `system.bin`, `spot33_grwp.py` → `rows/grwp.json`); the `oq_slot_tables` ranges widened to whole words.

Details (P1.2 helper, 2026-10-18, and later additions; code: `tools/pkg/containers.py` (codec registry +
apply), `tools/pkg/pkgapply.py` (in-memory apply + verify), `tools/pkg/code_sites.json`):
- **One key field for every rows file: `key_fields: ["at"]`.** Its meaning comes from the node the `ns` names:
  container node (MPK member name, ARC chunk key = tag or `tag.N` for a repeated tag, menu-pak entry id,
  collection_param section `sec0..sec8`/`tail`) → whole-member add / replace / delete; **grid** leaf (fixed rows,
  registry in containers.py: objentry 8+68, ablt 16+40, item 16+104, chrp 8+144, eqpm 8+126, jobp 8+112, uicn 4+8,
  bgm_entry 16+44, VOLD 16+24 — loose lists and the Museum copies `voice_load_parameter.mpk!voice_load_p_<key>.bin`,
  collection_param sections) → row index (`hdr` / `tail` for the bytes around the rows;
  replace/patch/delete use the clean index, add the final index — **superseded in format 1.1 by identity keys, §16**; row-count fields are derived, never stored);
  **bytes** leaf (texts, mess-pak groups `#g`, chrl/amas/acab, brai, assist, manual_param, command/update_list
  params) → byte offset in the clean node (replace old_raw→raw, add = insert, delete = remove; never overlapping).
- **Data tables inside code images** (owner_tables kind data/save: unlock_table, start_preset_table, scenario_names,
  qb_grid_rows, select_panel_list, ex_mode_page, records_icons, labyrinth_face, menu_name_keys, opp_info_name) are rows with
  `ns: img:<IMAGE>`, `key.at` = VA (int), op replace with equal-length `old_raw`/`raw`; `fields.va` shows it in hex.
  Code-site / iso-file ids stay `patches/`. Apply order on an image: produce (eboot_plain) → patches → img: rows.
- **Canonical container re-encoders** (installer default): MPK = header + entry table + names, members 16-aligned,
  end padded to 16; ARC = `pack4` for main.bin!system.bin (spot33_save.arc_join), `grow16` elsewhere (arcfile.py);
  pak = header + table, entries 16-aligned, zero filler, empty entries offset 0, end padded to 16; collection_param =
  20×u16 header (2, 9, counts, sizes) + sections + tail.
- **Layout pin** = row `key.at: "layout"`, op replace on a container ns: `raw` = the exact non-member bytes of the
  reference container (index table, gaps, filler, tail), `old_raw` = the skeleton of the canonical re-encode (the
  guard). Only where today's bytes are history-dependent (old 0x77 filler kept, in-place writes). Sora R0: 8 paks.
  A pin makes that container single-package in layout A (a second package touching it collides on the pin key).
- **Code sites** for word diffs: `tools/pkg/code_sites.json` (VA range → owner_tables id, writing script, note).
  New owner_tables ids from P1.2: `save_record_hooks`, `network_name_hook` (code parts of save_record_slot /
  network_names, so patches never target a data/save id).
  2026-10-19 (RR-08/RR-17 helper): `bgm_mode7_fallback` (code-site, spot33_bgmfallback.py: EBOOT 0x0888B61C-73,
  0x0888B6A4-B3 and the BGM-mode jump-table word 0x089CA530 -> patches/bgm_mode7_fallback.json; the jump-table word
  is kept with its code, not as an img: row) and `char_blurbs` (text, spot33_selectblurb.py: mess-pak groups
  chara_select #2, creation_room #5, party_setting #5, story_mode #1, update_list #7 -> rows/char_blurbs.json; rules
  in extract.py TABLE_RULES ahead of the whole-file text rules). Re-extract after the next R build.
  2026-10-19 (RR-08 Jukebox gate helper): `jukebox_gate_code` (code-site, spot33_jukeboxgate.py: OVL_MENU_APP
  0x08A36DB0-EB, 0x08A36F7C-B7, 0x08A370D8-113 -> patches/jukebox_gate_code.json); `jukebox_list_code` range
  0x08A37078-12B split into 0x08A37078-9B + 0x08A37128-2B around it (same words). Re-extract after the next R build.
  2026-10-18 (RC2 helper): spot33_selectblurb rewrites `mess_pk_chara_select_0` / `mess_pk_story_mode_0` so their
  re-encode differs (2 new layout pins, 10 in total); the whole-pack ns of those two paks → `char_blurbs` (extract.py
  TABLE_RULES), otherwise the pin row was UNMATCHED.
  2026-10-20 (RC3 helper): `menu_clock` (new owner_tables id, code-site, spot33_menuclock.py: EBOOT 0x08860DF8-FF,
  0x08860E90-97, 0x08860EA0-A3 -> patches/menu_clock.json); `grwp` rows (system.bin chunk grwp, containers.py grid
  codec header 8 / row 0x1C / count u32 @4, extract.py TABLE_RULES -> rows/grwp.json); `oq_slot_tables` ranges
  widened to whole words (0x08A6B3D4, 0x08A6CB94: the changed u16 fields sit in the upper half of a word, so the
  word diff started 2 bytes before the old range and was UNMATCHED).
  2026-10-20 (opp-info helper, R4 test): `opp_info_name` (new owner_tables id, kind data, spot33_oppinfo.py:
  OVL_BATTLE_APP 0x08AFB7F0-F7 = owner-33 row of the battle overlay owner → name-index table 0x08AFB6E8 →
  rows/opp_info_name.json, ns img:OVL_BATTLE_APP, same-length replace before the cave).
- §14 answers: row sizes/codecs = above; fighter-own files (`*sev120*`) are whole files, every shared container is
  rows (no stop-gap needed for Sora); subtitle vs voice line not separated (allocations list `voice_line` only);
  `eboot_plain` lives in the Sora manifest until the engine package exists (then it moves there).

## 16. v1.1 — identity keys, registry in the package, engine package (built in P2.8 step E2)
Design: [notes/phase2/P2.8-sora-package.md](../notes/phase2/P2.8-sora-package.md) §2-§3 (prototype codecs
`tools/pkg/p28_codecs.py prove`, 82/82 PASS). Designed 2026-10-21; built in P2.8 step E2 on 2026-10-22 (`tools/pkg/containers.py`, `tools/pkg/pkg11.py convert`,
`validate.py` rules, the package `packages/sora-C`; P2.8 as a whole is still **in progress**). Where this design and
the build differ, §16.1 "As built" wins;
v1.0 packages (`packages/sora-R4`) stay readable; a 1.1 package is re-extracted (`packages/sora-C`), not converted
in place. Minor bump: a 1.0 installer refuses 1.1 files (§3).
- **`registry` field** (manifest): path of the package's registry source (`"registry": "registry.json"` = today's
  `tools/dlc/registry/<id>.json`: row, behaviours, items, flags, install.*). It is the one source; `features` with
  `transitional_patches` (§11) goes away. Install fields added in P2.7: `install.title_call {sqe, ddd, days}` (the
  caller index is derived per roster), `install.qb_row: "append"` (the fighter gets a character-grid row of its own,
  GRD1 row 33), `install.uicn` (its entry count drives the size of the uicn buffer).
- **Codecs with identity keys** (design: `codec` + `key_fields` per rows file; as built the codec sits on each row and
  carries the `.v1` names below, §16.1):
  | codec | tables | key fields |
  |---|---|---|
  | `odir.v1` | owner directories (amas, chrl): header 16 B (count @8), rows sorted by owner, data region kept, new lists appended | `owner` (one keyed row = the owner's whole list) |
  | `acab.v1` | acab lists | `owner` (e.g. Sora = "share owner 13's list") |
  | `text.v1` | text groups (u16 and OFF4) | (`group`, `entry`) — plain text; XOR from the final index applied by the installer; vanilla placeholder entries reused via a global `text_index` allocation |
  | `grid-id.v1` | sorted, binary-searched grids (ablt u16 id, objentry s16 id) | `id` |
  | `positional.v1` | grids where the index is the id (bgm_entry = BGM id, item = id − 1, uicn, jobp, collection_param sections, eqpm preset) | the allocated id (gap filler for an absent lower package: open, P2.8 §3.3) |
  | `append.v1` | append lists (VOLD lists: one row per other fighter) | (`owner`, `k`), merged in owner order |
  | `pak-fill.v1` | picture packs | absolute picture id from the `picture_number` allocation |
  brai seco and the string tables (ability / item / item_help / bgm_name / battle_voice_name, manual / command_list /
  update_list params, assist) have no identity codec yet: as built they are `bytes.v1` rows with one editor per node;
  identity codecs for them are still to build (P2.9 / E8).
- **Derived, never stored:** counts, offsets / offset tables, final row indexes, picture-pack fillers (size-0 entries
  that keep ids contiguous), sort order. Rows of `img:` data tables that rowgen generates (G5) are not stored either
  (installer: `rowgen.generate(roster)`, `p23_lookups.tables(roster)`, `panel_tex`).
- **Layout pins** (§15) = **sole editor only**: a pin applies when its package is the only editor of that container;
  with two editors the installer re-encodes canonically and reports it (Sora-only discs stay byte-identical; Mat
  decided Q-P28-M2 = yes).
- **`set: transitional`** (patches, §8): owner-specific code that a later engine task retires (designed for
  Sora's `save_record_hooks` and `title_call`; P2.5 and P2.7 retired both before the build, so no package uses it). It carries an **exclusive claim**: a second package touching the same words is an
  error. The installer treats it as plain package data.
- **Engine package** (`kind: engine`, id `engine`, folder `packages/engine`): `produce: eboot_plain`, the file
  `DATA/MODULE/EXTRA.PRX` (engine v2), `patches/engine_base.json` (`set: engine`, the clean-based base words with
  **old = clean words**), the `code_cave` allocations (EBOOT 0x089A8B14–0x089A8F0C, TRI 0x089C1C8C–0x089C2508, jump
  table 0x089D1FB4–0x089D2084). No owner, no registry row. Fighter packages declare
  `requires: [{"id": "engine", "version": ">=2.5.0"}]`.
- **Declared reuse:** vanilla ids a package reuses are declared in its allocations (`role: reused_rows`, flags
  `reuse_vanilla`) instead of a validator exemption list.

### 16.1 As built (2026-10-22, P2.8 build steps E1-E3; P2.8 in progress)
Source: [notes/phase2/P2.8-build.md](../notes/phase2/P2.8-build.md).
Plain words: a 1.1 package stores each edit by **what it is** (an owner, a text entry, an id, a picture number), never
by where it ends up; the installer works out positions, counts and fillers when it builds a disc. Where the design
above differs from what was built, this section wins.
- **Codec per row, not per file.** A 1.1 row may carry `"codec"`; `key_fields` stays `["at"]` (as in §15) and
  `key.at` holds the row's identity for that codec. One table file may mix codecs (e.g. `museum_icons`: positional
  section rows + pak entries); the rows of one node (ns) share one codec. Codecs (`tools/pkg/containers.py`):
  | codec | node | `key.at` = | notes |
  |---|---|---|---|
  | `odir.v1` | system.bin amas / chrl | owner | op add, raw = the owner's entry list; offsets / count derived |
  | `acab.v1` | system.bin acab | owner | op add, `fields.share` = the owner whose list is shared (raw ""), or raw = own list + `fields.n` |
  | `text.v1` | mess-pak text group (u16 or OFF4) | entry index | raw = the PLAIN entry; replace / delete carry `old_sha256` (sha256 of the clean plain entry) and `old_raw: ""`, so no clean text is shipped |
  | `grid-id.v1` | sorted grids: ablt (u16), objentry (s16), eqpm (u16) | the row id | add inserts in id order; replace / patch address the clean row with that (unique) id |
  | `positional.v1` | grids whose index is the identity: bgm_entry, item, uicn, jobp, collection_param sections | final row index | all adds of all packages must form ONE contiguous block that starts at or before the clean row count (collection_param sec8: row 32 = owner − 1 goes in before the last clean row); a gap = refused (open question: a package owning lower positions is missing) |
  | `append.v1` | VOLD lists (`voice_load_p_*`) | `"owner:k"` | appended after the clean rows in (owner, k) order |
  | `pak-fill.v1` | menu picture pack entries | absolute picture id | size-0 filler entries are derived (never shipped) |
  | `bytes.v1` | bytes leaves without an identity codec yet (brai seco, ability / item / item_help / bgm_name / battle_voice_name string tables, manual / command_list / update_list params, assist) | byte offset in the clean node (1.0 meaning) | **one editor per ns** (validator error otherwise); identity codecs for these are still to build (P2.9 / E8) |
  Rows without a codec keep their 1.0 meaning (container members by name, grid replace / patch by clean index, layout
  pins). A 1.1 row without a codec may not add grid rows by final index, and a byte-offset row must say `bytes.v1`.
- **Layout pins** stay sole-editor. With two editors of a pinned container the installer drops the pin and re-encodes
  canonically (Mat Q-P28-M2 = yes; `install.py --pins refuse` turns that into an error instead).
- **registry.json** sits at the package top level (allowed only with `"registry": "registry.json"` in a 1.1 manifest);
  the validator checks its owner / package against the manifest. `features` is `{}` in a 1.1 fighter.
- **Layout C** = `"layouts": ["C"]`; a layout-C fighter must `require` the engine (`>=2.5.0` for sora-C). The engine
  package (§16 above) is `packages/engine`: patch files `engine_base`, `extra_prx`, `menu_clock` (each `set: engine`,
  old = clean words), EXTRA.PRX, `produce: eboot_plain`, `code_cave`. `set: transitional` exists in the schema but no
  package uses it: P2.5 and P2.7 retired both Sora-only patches before this build.
- **Fighter packages hold no code patches** (sora-C: 0): every Sora code word is engine base or an installer word
  (rowgen / OXT / SRC1 / panel_tex, `tools/pkg/rostergen.py`). `img:` rows and grwp rows are generated, never stored.
- **Tools:** `tools/pkg/pkg11.py convert SRC_1.0 OUT --registry SRC.json` (re-key a 1.0 package into a NEW folder; it
  proves every touched PACKAGE file comes out byte-identical before writing), `tools/pkg/layoutc.py verify CLEAN REF
  PKG...` (layout-C contents in memory vs a reference disc), `tools/pkg/engine/make_engine_pkg.py`, `tools/pkg/rostergen.py`.
  `pkgapply.py verify` still reads 1.0 packages only. `pkgformat.FORMAT_MINOR` = 1 (a 1.0 tool refuses 1.1 files).
- **Distribution:** unchanged (§4): sora-C ships the same derived files as sora-R4, minus the eboot produce entry;
  text rows ship plain text instead of XOR-ed bytes and no clean text at all (sha guards).
