# Fighter package format (v1.0)

This spec describes a **package**: one folder with everything a fighter adds to the clean game. It is part of
Phase 1 (see the [roadmap](ROADMAP.md)). Nothing here touches an ISO.

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
- `format_version` = `"MAJOR.MINOR"` in the manifest and in every rows/patches/order file. Current: **1.0**.
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
