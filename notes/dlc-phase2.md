# Phase 2 research notes — generic character engine

Started 2026-10-19 by Claude (phase2 research helper), static only. Plan: [docs/PHASE2-PLAN.md](../docs/PHASE2-PLAN.md).
Inputs: `packages/sora/patches/*.json` (R2 extract, 20 patch files, 1,616 patched code words), `tools/pkg/code_sites.json`
(94 VA ranges, 31 owner_tables ids), `tools/dlc/owner_tables.json` (99 entries, read-only here), `notes/dlc.md`
appendix D/E, `notes/dlc-phase0.md` P0.4.

## Owner-33 hardcode inventory (2026-10-19)

### Method
- Decoded every new code word in `packages/sora/patches/*.json` (word edits + the battle-cave byte blob) and listed
  each instruction with an immediate operand whose value is owner-specific: 0x21 (owner 33),
  0x22/0x23 (owner bounds 34/35), name index 63, pictures 245/246, item ids 678-682 (also as −678), flags 1263/925/888
  (as −N), ablt cap 832, the assist "drop" value 0x7f. Scanner: kept in the helper scratchpad (logic = 25 lines,
  re-creatable from this description); raw output = the appendix table below.
- Data-in-code tables (index 33 inside a table in a code image) come from `code_sites.json` ranges with data ids.
- The OQ fix (`spot33_oqslot.py`, RR-18, in progress by another helper) is not in `packages/sora` yet; its sites are
  taken from `code_sites.json` and marked accordingly.
- Limits: a test written as a byte load + compare against a register loaded elsewhere, or an owner read through a pointer
  chain, is not visible to an immediate scan. Such sites are named from the scripts' own docstrings and marked
  **unconfirmed (indirect)**.

### Result in numbers
- **69 owner-specific constants in 17 patch sites** (26 × `owner==33`, 6 owner bounds, 16 picture numbers, 2 name
  index, 3 drop values, 13 item-id checks, 3 purchase-flag checks, 1 ablt cap).
- **+ 9 data-in-code tables indexed by owner** (unlock_table row 22, start_preset_table[33], scenario_names[33],
  records_icons[33], labyrinth_face[33], menu_name_keys[32], qb_grid_rows row 31, select_panel_list entry 30,
  ex_mode_page row 22) **+ 2 OQ sites** (oq_slot_code, oq_slot_tables: 3 owner-indexed entries).
- **Total: 80 owner-specific places** (78 confirmed by bytes, 2 OQ sites by code_sites.json only).

### Per site: what is hard-coded → generic replacement
Image legend: E = plain EBOOT, M = OVL_MENU_APP, B = OVL_BATTLE_APP. Words = patched code words in the package today.

| # | site (owner_tables id) | img | words | hard-coded today | generic replacement (Phase 2) |
|---|---|---|---|---|---|
| 1 | name_index_eboot | E | 10 | 0x088d625c: owner == 33 test → name index 63; owner bound 35 (`< 35`) | `name_index = REG[owner].name_index` when owner > 32 (registry field, bound = registry size) |
| 2 | network_name_hook | M | 7 | 0x08a1d80c: owner == 33 test → name index 63 | same registry field `name_index` |
| 3 | save_record_hooks | E | 123 | owner == 33 constants at 0x088cb180 / 0x088cb304 / 0x088cb348 / 0x088cb35c (record slot 24), 0x089293e4 + owner bound 35 at 0x089293f8 (OQ has-record), friend-card limit 0x088f523c / 0x088f52a0 | `REG[owner].record_slot` (0 = vanilla list); friend-card limit = 25 − number of package owners (module computes at boot) |
| 4 | assist_drop_words + assistdup | E | 19 | 3 × drop value 0x7f (no owner dropped: already generic); 0x088d5c7c: owner 33 constant (DLC-Aerith append skips owner 33) | keep 0x7f; Aerith check → "skip if owner already listed" loop over package owners |
| 5 | ablt_cap | E | 1 | cap constant 832 rows (0x340) | cap = vanilla 808 + Σ package ablt rows, written by the installer (data, not owner code) |
| 6 | bgm_mode7_fallback | E | 26 | 0x0888b668: owner == 33 test (empty pool + opponent 33 → stage music) | drop the owner test: empty pool → stage music for every owner (vanilla owners never have an empty pool) |
| 7 | exrun_hook | E+B | 25+2 | 0x089a8b34: owner == 33 test; multiplier constant | feature `ex_run_speed` (REG[owner].ex_run_mult, 0 = off) in module C |
| 8 | item_code_hooks | E+M | 212+2 | 4 × owner == 33 test (0x089a8c88 / 0x089a8cac / 0x089a8d10 / 0x089a8d94) + 10 item-id checks (base −678, bounds 679/682, 680) | per-item owner table `ITEM_OWNER[item] = owner` (0 = everyone) built from package `item_owner` features; ELIG/ROWMASK/MENU read it |
| 9 | item_battle_effects | E+B | 61+2 | no owner constant in EE_B (0x089a8de4..); cave 0x08b6314c: item 681 constant (Crown Pendant) | **unconfirmed (indirect)**: effects keyed by item id; generic = `[{item, effect, value}]` table in module |
| 10 | burst_controller (TRI) | E+B | 536+5 | 6 × owner == 33 test (0x089c1cb8 / 0x089c2058 / 0x089c2090 / 0x089c20b8 / 0x089c22b8 / 0x089c238c) + owner 33 constant at 0x089c2184, items 678/679 (0x089c22e4 / 0x089c245c); battle variant word 0x08a39e04 "33 → TRI" | dispatcher `REG[owner].burst_controller` (vanilla id 0..19 or module controller id); TRI becomes a module behaviour taking its item ids from params |
| 11 | reflect_guard + battle_overlay_cave | E+B | 4+3+165 | cave 0x08b62f80: owner == 33 test; hooks 0x0880a384 / 0x0880a408 / 0x08808b74 / 0x08ada22c / 0x08adaaac / 0x08adb32c are plain calls into our code | feature `reflect_guard` (params: barrier, voice slot, refill rules) in module C; hooks stay plain calls |
| 12 | ex_burst_sound_skip (EX_SND) | B | in cave | **unconfirmed (indirect)**: owner test inside the cave routine | feature flag `ex_burst_sound_skip` |
| 13 | char_panel_sprites | M | 9 | 0x08aff2ec: owner < 33 test (owners < 33 use the table, 33 → owner 32's free sprite) | `REG[owner].panel_sprite` + texture ids; a 2nd package needs a new sprite cell (capacity task) |
| 14 | menu_picture_remaps | M | 131 | 13 sites with picture number 245 + party slots: owner == 33 test / picture 246 (0x08b2c520..0x08b2c600) | `REG[owner].pictures[scene]` (per-scene picture numbers; installer allocates them when it appends to the packs) |
| 15 | setup_banner_remap | M | 48 | 0x08aa4584 / 0x08aa627c: picture number 245; frame table [owner−1] | `REG[owner].pictures.setup` + `REG[owner].setup_frame` |
| 16 | museum_viewer_code | M | 35 | 0x08a32024: record bound 34 → owner 33 (0x08a322f4) | relocated viewer list (record index → owner) generated from the registry |
| 17 | records_list | M | 1 | 0x08a3d8f4: owner 33 constant (Chaos's append re-used for 33) | append loop over package owners; array growth past 32 = capacity task (module-owned array) |
| 18 | jukebox_list_code | M | 10 | caps 35 / 34 (character list 34 entries) | cap = 33 + package count; buffers moved by the module (capacity task) |
| 19 | jukebox_gate_code | M | 24 | override skip for flags 1263..1270 (range test: base −1263, 8 flags), 925, 888 | `is_package_flag(flag)` = bitmap of every flag the allocator gave to packages |
| 20 | title_call | M | 155 | owner bound 35; DDD/SQE tables + day table (index 34 = Sora) | `REG[owner].title_call` (voice id, days); table rebuilt from the registry |
| 21 | oq_slot_code / oq_slot_tables (RR-18, in progress) | M | 38+21 (+tables) | face handle "entry ≥ 64 = owner-33 icon" (0x08a54044), 39th handle (0x08a62530), full-name entry 0x08A544E0+33·4, party banner 0x08A6B394+33·2, party row 0x08A6CAD0+33·6 | `REG[owner].oq_face / oq_banner / oq_name` (from code_sites.json; **not yet byte-checked**, package not re-extracted) |
| 22-30 | data-in-code tables | E/M | rows | unlock_table row 22 (owner 33, flag 925); start_preset_table[33] = 250; scenario_names[33]; records_icons[33] = 0x4060; labyrinth_face[33] (0x102D); menu_name_keys[32] = sev120; qb_grid_rows row 31; select_panel_list entry 30; ex_mode_page row 22 | installer writes rows for every package owner (already data, only capacity matters: unlock table has 1 free row, select list needs relocation) |

### Notes found while doing the inventory
- **EX run multiplier mismatch in docs (confirmed):** the built code is ×1.40 (`packages/sora/patches/exrun_hook.json`
  0x089a8b68 loads the float constant 0x3FB3… = 1.40; `spot33_exspeed.py` default 1.40, build_sora.sh sets no override). The `features`
  note in `packages/sora/manifest.json` and `docs/PACKAGE-FORMAT.md` §11 say `mult 1.1` → stale text; fix when the
  extractor next writes the manifest (P2.2 builds the registry value from the patch, not from the note).
- `packages/sora` objentry rows added at ids 1457..1459 (owner 33, fine). An owner-34 package must use ids < 1338
  (Cosmos `P_ORG800_1P` = 1338 answers first otherwise, P0.4).
- Overlay hooks cannot call into EXTRA.PRX directly: the module is relocatable and the overlays are re-read from disc.
  Needs a fixed stub table (see PHASE2-PLAN P2.1). Today's EBOOT dead code (EXRUN/EXITEMS/EE_B ≈ 1 KB at 0x089a8b14,
  TRI 2.1 KB at 0x089c1c8c, SCALE 52 words at 0x089d1fb4) is freed once those behaviours move into the module and is
  the natural home for that stub table.

### Appendix — raw constant hits (packages/sora, R2)
| img | site | hits |
|---|---|---|
| EBOOT | ablt_cap | `0x088b1cf0` (ablt cap 832) |
| EBOOT | assist_drop_words | `0x088d5c7c` (owner==33)<br>`0x088f6c04` (drop-owner 0x7f)<br>`0x088f9ca4` (drop-owner 0x7f)<br>`0x08929060` (drop-owner 0x7f) |
| OVL_BATTLE_APP | battle_overlay_cave | `0x08b62f80` (owner==33)<br>`0x08b6314c` (item 681) |
| EBOOT | bgm_mode7_fallback | `0x0888b668` (owner==33) |
| EBOOT | burst_controller | `0x089c1cb8` (owner==33)<br>`0x089c2058` (owner==33)<br>`0x089c2090` (owner==33)<br>`0x089c20b8` (owner==33)<br>`0x089c2184` (owner==33)<br>`0x089c22b8` (owner==33)<br>`0x089c22e4` (item 678)<br>`0x089c238c` (owner==33)<br>`0x089c245c` (item 679) |
| OVL_MENU_APP | char_panel_sprites | `0x08aff2ec` (owner==33) |
| EBOOT | exrun_hook | `0x089a8b34` (owner==33) |
| EBOOT | item_code_hooks | `0x089a8bb0` (item 679)<br>`0x089a8bdc` (item bound 682)<br>`0x089a8c30` (item base -678)<br>`0x089a8c7c` (item base -678)<br>`0x089a8c88` (owner==33)<br>`0x089a8ca0` (item base -678)<br>`0x089a8cac` (owner==33)<br>`0x089a8cf4` (item base -678)<br>`0x089a8d10` (owner==33)<br>`0x089a8d50` (item 680)<br>`0x089a8d94` (owner==33)<br>`0x089a8dc8` (item base -678)<br>`0x089d1fc8` (item base -678) |
| OVL_MENU_APP | jukebox_gate_code | `0x08a36ddc` (flag base -1263)<br>`0x08a36fa8` (flag -925)<br>`0x08a37104` (flag -888) |
| OVL_MENU_APP | jukebox_list_code | `0x08a36f20` (bound 35)<br>`0x08a36f2c` (bound 34) |
| OVL_MENU_APP | menu_picture_remaps | `0x08a8d140` (picture 245)<br>`0x08a8d198` (picture 245)<br>`0x08aac36c` (picture 245)<br>`0x08aac4a4` (picture 245)<br>`0x08aacce4` (picture 245)<br>`0x08aace94` (picture 245)<br>`0x08b263a8` (picture 245)<br>`0x08b26408` (picture 245)<br>`0x08b2ab6c` (picture 245)<br>`0x08b2c520` (owner==33)<br>`0x08b2c540` (picture 246)<br>`0x08b2c600` (picture 246)<br>`0x08b2dbac` (picture 245)<br>`0x08b30be8` (picture 245)<br>`0x08b30c2c` (picture 245) |
| OVL_MENU_APP | museum_viewer_code | `0x08a32024` (bound 34)<br>`0x08a322f4` (owner==33) |
| EBOOT | name_index_eboot | `0x088d6254` (bound 35)<br>`0x088d625c` (owner==33)<br>`0x088d627c` (name idx 63) |
| OVL_MENU_APP | network_name_hook | `0x08a1d80c` (owner==33)<br>`0x08a1d810` (name idx 63) |
| OVL_MENU_APP | records_list | `0x08a3d8f4` (owner==33) |
| EBOOT | save_record_hooks | `0x088cb180` (owner==33)<br>`0x088cb304` (owner==33)<br>`0x088cb348` (owner==33)<br>`0x088cb35c` (owner==33)<br>`0x089293e4` (owner==33)<br>`0x089293f8` (bound 35) |
| OVL_MENU_APP | setup_banner_remap | `0x08aa4584` (picture 245)<br>`0x08aa627c` (picture 245) |
| OVL_MENU_APP | title_call | `0x089dec04` (bound 35) |

## P2.1 engine ABI — findings (Claude, P2.1 ABI helper, 2026-10-19, static)
Spec: [docs/ENGINE.md §"Registry + stubs v2 (DRAFT, P2.1)"](../docs/ENGINE.md). Needs review by the other agent.

### Decisions in the draft
- Three mechanisms: **I** = install-time data in the game images (no runtime), **L** = registry lookup through EBOOT
  helpers (REG_ROW / REG_FLAG / REG_NEXT / REG_BY_MUSEUM / REG_ITEM_OWNER, clobber at+v0), **S** = behaviour stub
  (fixed EBOOT stub → FN_PTR → module wrapper or vanilla fallback).
- Stubs are **data-indirect** (`lui at / lw at,FN_PTR / jr at / nop`): the module writes pointers, never instructions →
  no JIT guard needed (P0.7 problem avoided), vanilla when the module is missing.
- Stub table in the freed TRI range (0x089C1C9C, 539 words), helpers in the freed EXRUN/EXITEMS range (0x089A8B24,
  250 words), switch table range (52 words) reserved. Registry row 64 B, max 31 rows, file EXTRA.REG (loose, next to
  EXTRA.IDX). Status block layout 2 (0xC0, tail2 "XTR2").

### Verified while doing it
- Dead ranges re-scanned on the clean images (EBOOT + menu + battle + extra overlay; j/jal, branches, raw words,
  lui+lo pairs): only known dead self-references, 5 rodata "branches", and 6 lui-pair false hits (checked by hand:
  at 0x08870F1C/28 and 0x08871114 the register is reloaded before the low half is added; 0x088821DC–E4 use an
  argument pointer). Combined with the test272p runtime marker probe → safe to reuse.
- R2 package has **26 hook words → 24 distinct behaviour entries** (TRI 5 + EE_HIT, reflect C1/C2/C3/C4/C7, CROWN,
  EXRUN, 11 item entries incl. STASH/SCALE in the switch table). The inventory's cave range starts at 0x08B62F80, not
  at the appended 0x08B63004 (C1 0x08B62F9C, C2 0x08B62FC4 are in-place cave words).
- **No hook delay slot touches `$at`** (all 24 sites checked) → a stub may clobber `$at` only.
- 3 EBOOT hooks (C1 0x0880A384, C2 0x0880A408, C4 0x08808B74) jump into the **battle overlay** cave today (fine only
  because they run in battle); stubs route them to the resident module.
- `char_panel_sprites` 0x08AFF32C calls 0x089A8DC4 inside the EXITEMS range: that helper becomes a REG_ROW lookup.

### Inventory site → v2 mechanism
| # | site | v2 | registry field / stub |
|---|---|---|---|
| 1 | name_index_eboot | L | name_index (bound → REG_ROW range check) |
| 2 | network_name_hook | L | name_index |
| 3 | save_record_hooks | L + I | record_slot; friend-card limit = I (25 − rows with record_slot) |
| 4 | assist_drop_words / assistdup | generic + L | 0x7F stays; Aerith check → REG_NEXT loop |
| 5 | ablt_cap | I | cap = 808 + Σ package ablt rows |
| 6 | bgm_mode7_fallback | generic | owner test dropped |
| 7 | exrun_hook | S7 | feat EX_RUN, ex_run_mult |
| 8 | item_code_hooks | S13–S22 + L | feat ITEM_OWNER / ITEM_SCALING; EXTRA.REG item_owner + aux (SCALE table) |
| 9 | item_battle_effects | S5, S6 | feat ITEM_EFFECTS; item_fx rows; params crown drain |
| 10 | burst_controller (TRI) | S0–S4 | burst_ctl = 0x80; params items |
| 11 | reflect_guard + cave | S8–S12 | feat REFLECT_GUARD; params refill/mult/voice; PROJ_AIM bound = I |
| 12 | ex_burst_sound_skip | S23 (spare-ish) | feat EX_BURST_SOUND_SKIP (unconfirmed site, only TRINITY_CTL=0 builds) |
| 13 | char_panel_sprites | L | panel_sprite, panel_tex[3]; new sprite cells = capacity (P2.7) |
| 14 | menu_picture_remaps | L | pic_slot, pic_slot_party, party_frame |
| 15 | setup_banner_remap | L | pic_slot, setup_frame |
| 16 | museum_viewer_code | L | museum_record (REG_BY_MUSEUM) |
| 17 | records_list | L | REG_NEXT append loop; array growth = P2.7 |
| 18 | jukebox_list_code | I | caps = 33 + rows; buffer moves = P2.7 |
| 19 | jukebox_gate_code | L | REG_FLAG (flag bitmap from the allocator, P2.6) |
| 20 | title_call | I | tables + bound written by the installer |
| 21 | oq_slot_code / tables | L + I | oq_name/oq_face_pic/oq_face_layout/oq_banner/oq_row; tables = I; handle list has room for exactly ONE extra pair (PAIR39) → P2.7 |
| 22–30 | data-in-code tables | I | rows per package owner; unlock table 1 free row + select list relocation = P2.7 |

### For later tasks
- P2.2: registry builder must emit EXTRA.REG + check "no `$at` in hook delay slots"; take setup_frame and oq_banner
  values from the patch words (two fields marked "check"); teach find_status.py layout 2.
- P2.4: one asm wrapper per stub reproducing today's register contract; `vanilla[n]` = old FN_PTR for non-package owners.
- P2.7: OQ face-handle list (1 spare pair), Characters-panel sprite cells, Records array (32), Jukebox character list
  buffer, unlock table (1 free row), select-panel list.
- No blocker found; no decision needed from Mat.

## P2.2 registry builder — Claude (P2.2 helper), 2026-10-19, static only

**Tool:** `tools/dlc/registry.py` (python3 -I; reads JSON + `tools/dlc/flag_map.json` + an ISO read-only with
`--disc`; writes only `-o`). Commands: `build SRC.json… -o OUT [--disc ISO] [--dry]`, `validate SRC.json… [--disc ISO]`,
`decode EXTRA.REG [-o OUT.json]`, `selftest [--disc ISO]`. Output = EXTRA.REG v1 exactly per ENGINE.md P2.1 §6
(64-B header, 64-B rows sorted by owner, item-owner bytes, 8-B item-fx rows, gate-flag bitmap, empty aux, strings,
32-bit sum). `build` refuses on any validator error and re-decodes its own output with the module's load rules.

**Sources:** `tools/dlc/registry/sora.json` (every value = [value, source]; traced to the R2-era scripts plus
spot33_oqslot of test352; `packages/sora-R2` did not exist yet and `packages/sora` was mid re-extract by the RC3
helper, so **nothing was read from packages/**). `tools/dlc/registry/test34.json` = synthetic Cloud-based placeholder
at owner 34 (P2.9 target: features PKG_FLAGS + RECORD_SLOT only, chrp burst controller, no items, no EX speed).

**Results:** EXTRA.REG **220 B** for Sora (`out/sora.EXTRA.REG` sha 88540de8…42a6), **296 B** for Sora + test34
(`out/sora+test34.EXTRA.REG` sha 82c6de7d…920f; decoded JSON next to it). Gate-flag bitmap 888..1285 (398 bits,
50 B). `selftest`: both builds round-trip byte-identical, 16 source error cases + 1 file-corruption case all caught
(`tools/dlc/registry/tests/cases.json`). Disc check on test352: Sora **0 errors** (name index 63 present in all 8
name-list groups, full name 122 in all 4 OQ groups, pictures base + 245 present in story / party_setting /
party_arrange / original_quest / level_adjust packs); test34 = 29 expected "missing" warnings (placeholder).
Negative real-disc check: Sora against R2 (before spot33_oqslot) → 4 errors "oq_name 122 missing" (correct).

**Validator checks** (source level; ERROR fails, WARN never fails):
1. owner int 33..63, unique, ≤ 31 rows; WARN owner > 35 (save format, P2.5)
2. u16/u8 ranges of every row field; panel_tex / oq_row = 3 × u16
3. features known; EX_RUN ⇔ ex_run_mult ≠ 0 (1.0..3.0); BURST_MODULE ⇔ burst_ctl 0x80; burst_ctl ∈ {0xFF, 0x80};
   RECORD_SLOT ⇔ record_slot ≠ 0; ITEM_OWNER ⇔ owned items; ITEM_EFFECTS ⇔ item effects; behaviour features need
   params layout behaviours-v1; params items ⊂ owned items, params ranges
4. key = 6 × [a-z0-9], unique
5. Original Quest consistency: pic_slot_party = pic_slot + 1; oq_face_pic = 0x6434 + pic_slot; oq_row = (0x64B7, 0x64DA,
   0x6454) + pic_slot; oq_banner = oq_row face_r; oq_face_layout = 0x660E
6. owner 34 objentry ids < 1338; item ids < item ceiling 683; effects known and only on owned items
7. unique across packages: name_index (≥ 63), oq_name (≥ 122), museum_record (≥ 34), pic_slot (≥ 245), key,
   title_call_index, items, objentry ids
8. record slots = 24, 23, … contiguous; friend-card limit 25 − n ≥ 1
9. OQ_FACE on at most 1 row (face-handle list room, P2.1 → P2.7)
10. flags: unique across packages, inside 0..5119; free in flag_map → OK; not free + `reuse_vanilla` + no game-CODE
    writer → WARN (Sora: 925 Chaos unlock, 2263 Chaos NEW); otherwise ERROR listing the vanilla users; no flag_map → WARN
11. `--disc` (layout A/R disc, read-only): name index in the 8 name-list groups, oq_name in the 4 full-name groups,
    pictures base + pic_slot in each scene's packs (icon/face/face_r/name); placeholder packages → WARN
File level (`decode` / module load rules, ENGINE.md §6): magic, version, sizes, sections inside the file, size % 4,
sum, min engine version, rows ascending/unique 33..63, valid bit, known feat bits, burst_ctl, key inside strings.

**Values resolved (the two P2.1 "to check"):**
- `setup_frame` = **12**: spot33_qbpics FRAME_PATCH / CPU_FRAME_PATCH make owner 33 use frame row 12 of 0x08AA8864 =
  owner 13 Cloud's row (frames 24/26/25/27/11). Not an "own frame" (owner_tables wording) but a borrowed row.
- `oq_banner` = **26028**: spot33_oqslot fix d writes 0x08A6B394[33] = 26028 = Sora's face_r (= OQ face_r base + 245),
  the same picture as oq_row[0] (validator rule 5).
Other corrections found while tracing:
- Crown Pendant drain = **1/1.3 = 0.769** (spot33_exitems CROWN_DRAIN default); the "0.7" in ENGINE.md P2.1 §4 comes
  from a stale comment in spot33_reflect.py.
- `params` v1 is now concrete: layout `behaviours-v1` = `<4HBBHf` items[4] (678 KK, 679 PB, 680 SK, 681 CP),
  voice_bar 42, voice_reflect 7, shield_pct 192 (= 1.5 × 128), crown_drain f32. Fighters without behaviours = 16 zero bytes.
  **2026-10-21 (P2.4 step 3):** shield_pct RETIRED — the u16 stays as reserved 0; Save the King's factor is only the
  item_fx REFLECT_POWER row (notes/phase2/P2.4-shield.md §4).
  **2026-10-21 (P2.4 step 4):** crown_drain RETIRED the same way (f32 = 0; item_fx EX_DRAIN is the one source). New
  registry data for items: item_owner byte bit 7 = start-owned (min engine 2.4.0), aux kind 3 EXPAGE (EX-page face /
  name pictures), aux kind 4 SCALE (level-scaled stats) — notes/phase2/P2.4-items.md §3.
- Item effects (fx section): 678 EX_HIT_GAIN 100 (combo cap 300 → aux, P2.4), 679 EX_GUARD_GAIN 1000, 680
  REFLECT_POWER 1.5, 681 EX_DRAIN 0.769.
- **Item ceiling**: owner_tables item_rows says ids 0..682 load/save (683); Sora uses 678..681 → **one free item id
  (682)**. Any second fighter with own items needs P2.7 to raise the ceiling (validator enforces it).
- Flags for test34 came straight from flag_map.json: unlock 1285 (free block 1285..1300; 1271..1284 are used),
  EV 889, NEW 2094, SEEN 3634 (3600 + owner pattern), viewed 3686 (3682..3685 are used).

**Open:**
- `find_status.py` layout-2 support (P2.1 asks for it in P2.2) not done: it lives in tools/pkg/, which the RC3 helper
  owned during this task. Small follow-up.
- Not covered by `--disc`: Quick Battle / select-grid pictures (free_battle / upper_chara_select packs use their own
  id bases, not owner runs), Characters-panel textures, layout-B discs (EXTRA.IDX reader not wired in).
- `aux` section empty (SCALE TAB, EE combo cap/gap, dedup frames go there in P2.4).
- panel_tex order still "check in P2.3"; test34 panel fields 0 = no Characters-panel cell (P2.7).
- Re-check sora.json against `packages/sora` once RC3 re-extract is done (values should not change).
- **Done 2026-10-20 (start-guide helper, from notes/phase2/P2.9-testfighter.md §6):** test34.json objentry ids
  1300-1302 (vanilla `P_*_3P_PUB` rows) → **1335-1337**; unlock flag 1285 → **3200** (P2.6 pool). registry.py now
  rejects (a) objentry ids that `tools/dlc/id_spaces.json` does not list as free (ids < 1338) or that sit in the
  vanilla range 1338..1456, and (b) flags outside the P2.6 package pools (3200-3455, 2094-2130, 2997-3040, 3686-3720,
  3632-3650, 889-891) — for every package except `sora` (package #1 keeps its 1.0 numbers); and validator rule 8 is now
  "record_slot == 57 − owner" (was "24, 23, … contiguous", which would wrongly refuse owners 33 + 35 without 34). Two new selftest cases;
  selftest PASS (18 cases + file case). Side effect: Sora + test34 EXTRA.REG grows 296 → **536 B** because the gate-flag
  bitmap is one range (888..3200 = 2,313 bits) — the P2.1 review's "list of flag ranges" fix (§2.9) would shrink it.
  `out/sora+test34.EXTRA.REG` rebuilt: sha 1206a019…0381 (two builds identical); `out/sora.EXTRA.REG` unchanged (88540de8…42a6).

## P2.6 allocator findings — Claude (P2.6 helper), 2026-10-19, static only

### In plain words
- I listed every place the clean game reads or sets an unlock flag that can be found without the emulator: 1,353
  flag numbers are used. Sora's own new flags (888, 1263-1270, 2093, 2993-2996, 3633, 3681) are all unused on the
  clean game. The two he shares on purpose (925 unlock and NEW tag 2263) both belong to Chaos's catalog item, which Sora
  took over.
- **New vanilla writer found:** flag **1372** (the Jukebox "show all" switch) is set by the game itself when the
  **Museum is 100 % complete** (menu 0x08A44EF4; the trigger byte comes from FUN_08a3cc18 = all 8 completion
  checks). The decompile missed this function, and the byte scan found it. So any 100 % save gets 1372, and it never clears.
- **The draft plan's "next package 1271-1278" is NOT free:** 1271-1284 are vanilla player-icon flags (PP Catalog
  + uicn). Use the pool below instead.
- Proposed package pool: **flags 3200-3455** (save words 100-107, 256 flags = 32 packages × 8), in the middle of
  the largest unused gap 3099-3600. Small per-subsystem pools continue the vanilla rows (table below).
- Still needed before the pool is final: **one emulator check** (R): read the whole flag array of the 100 % save
  (640 bytes at the pointer stored at 0x089D726C) and confirm words 96-112 are zero. 53 table-driven code functions take their flag
  numbers from data the game loads at run time (story/event scripts, quests, battle conditions). Static reading
  can't bound them, but a fully played save can.

### Tools and outputs (all read-only on the clean dump)
- `python3 -I tools/dlc/flag_writers.py [CLEAN.iso]` → `tools/dlc/flag_map.json` (flag → [kind W/C/R/RW, site,
  detail]; free ranges; code-writer ranges; helpers; table-driven sites with their source; coverage). Self-test:
  1250-1252 W FUN_08a2b07c, 1253-1262 W level table 0x08A2E8AC, 1372 R FUN_08a41098, 925 unlock row 22 (Chaos),
  856-887 W Catalog EV items, 886 R Jukebox rows, 1263-1270 unreferenced → all PASS (exit 1 on any failure).
- `python3 -I tools/dlc/id_spaces.py [ISO]` → `tools/dlc/id_spaces.json` (FEP ids, SSCF sound banks, objentry ids).
  It reads the whole disc once (~25 min on the project's spinning disk).
- Flag space: the new-game init FUN_088b0788 clears 0x80 words (flags 0-4095) and a second block of 0x20 words
  right after (4096-5119). The array sits in the save buffer (DAT_089d712c + 0x1DF88). **No code or data references
  block 2.** Don't allocate there until its reader is known (it may not be flags at all).

### Method and coverage
- Code: local Ghidra decompiles of the clean binaries (EBOOT + battle, EBOOT + menu; never published):
  constant word/mask set/clear/test, constant local arrays, helpers whose parameter is the flag (FUN_08a29b5c,
  FUN_08a48610, FUN_08a95034, FUN_08a97438) and their constant-argument callers, and every table-driven site.
- **Byte cross-check:** all 183 loads of the array pointer (the address pair that loads the pointer at 0x089D726C) in the plain EBOOT and the
  clean overlays get a small data-flow decode (constant word + mask, set/clear/test). 11 loads sit in functions the
  decompile doesn't show. They give 7 flag uses the decompile scan missed: 110 R (EBOOT 0x088C3EF0), 1041/1042 R
  (menu 0x08ABFF3C/0x08AC2088/0x08AC25E8/0x08AC2624), **1372 W (menu 0x08A44EF4)**.
- Tables in the code images: EBOOT unlock 0x089D7BE0 (unlock + 2 costume flags), comflag lists 0x089CDB18/28
  (3041-3096), level table 0x08A2E8AC, "all set?" list 0x08A455EC, plus small ones decoded by hand: EBOOT
  0x089CBB9C (541-560), 0x089CBBEC (481-510 pairs), menu 0x08A2E730 (701-730), 0x08AB2374 (930-939), 0x08B01C98
  (20/58/59), **0x08B1C692 (1850-1867)**, 0x08A8B67E/80 (541+i, 8), 0x08A93A2E (210).
- Data: PP Catalog (visible-after ×2 R, bought W, NEW RW), collection_param sections 0/6/8, collection_voice_param,
  system.bin uicn (unlock R, viewed RW) / infp (if R, set W) / tuto, bgm_entry, party_battle-pbtl.
- 158 table-driven code sites in 104 functions. Their sources: 51 functions are mapped to the tables/data above
  (`SOURCES` in the script; '?' marks a mapping inferred from the globals the function reads). **53 are UNRESOLVED**
  (listed in flag_map.json `unresolved_functions`). Most are EBOOT 0x088ad7bc..0x08928xxx (event/story/quest
  systems, incl. the 22 KB FUN_088e150c), battle 0x08af77dc..0x08af7fd0, menu 0x08a2c36c.., 0x08b0de00.., 0x08b381c8.

### Used / free (clean disc)
- Large unused ranges: 211-319, 321-391, 640-680, 800-841, 1445-1849, 1868-2033, 2093-2130, 2298-2399,
  2402-2553, 2993-3040, **3099-3600**, 3686-4095 (+ block 2 4096-5119).
- Code writers (set/clear by code or code tables): 1-4, 6, 8-12, 14, 18-25 (parts), 34, 40, 51-66 (parts), 71-73,
  396-397, 700-730, **1250-1262**, 1370, **1372**, 1850-1867, 3041-3096, 3098, 3601-3631 (new-game init, odd).
- Sora (mod) on the clean map: 888 free, 925 = Chaos's unlock (reused on purpose), 1263-1270 free, 2093 free,
  2263 = Chaos's catalog NEW tag (reused, known), 2993-2996 free, 3633 free, 3681 free. **None of Sora's flags
  collides with a vanilla writer.**

### Proposed allocation (for P2.6 allocator / registry)
| pool | flags | why | per package |
|---|---|---|---|
| purchase / unlock (package's own items) | **3200-3455** (words 100-107) | middle of the 502-flag gap 3099-3600, 100 away from comflag 3041-3098 and init 3601+; word-aligned so `is_package_flag` is a word-range test | 8 (Sora keeps 1263-1270 as package #1, grandfathered) |
| catalog NEW tags | 2094-2130 | continues vanilla NEW rows (Sora 2093) | 1 per catalog item |
| icon "viewed" | 2997-3040 | continues uicn viewed 2580-2992 (Sora 2993-2996) | 1 per icon |
| Museum record "viewed" | 3686-3720 | after vanilla 3651-3685 (Sora 3681 = the unused slot inside) | 1 |
| SEEN (catalog item seen) | 3632-3650 | next to Sora's 3633 | 1 |
| Encounter Voice | 889-891 (then pool) | after vanilla 856-887 + Sora 888; 892 is vanilla | 1 |
Gate: the 100 %-save flag-array dump (R) must show the chosen words zero; the allocator refuses any flag that
flag_map.json lists, and any word with a code writer.

### Other id spaces (clean disc, `id_spaces.json`)
- **FEP effect ids** (top 14 bits, unique per loaded FEP): 363 distinct ids on the disc (1024-11047). Fighter series
  3100-3199 uses 25 ids. **Free: 3146-3152** (Sora takes 3146 → owner 34 = 3147), plus 3100-3102, 3105-3112,
  3116-3122, 3156-3162 …. The same id in several files is a copy of one fighter's FEP (story/field variants), not a
  clash.
- **Sound banks** (base/100): 504 banks. The 012 newcomers use 210000 + 1000·(owner−24) (+0 snd, +100 voice, +200
  manikin, +500/+600 assist). Owner 33 = 219xxx (219500/219600 = Aerith's assist banks on the clean disc; 219000/219100
  free → Sora). **Owners 34-40: 220000-226000 are all free** (+0/+100/+500/+600 checked). Second choice 36000-39900
  (h12 form) free.
- **objentry ids:** clean 1,170 rows, RAM room 1,194 rows → **24 free rows** (Sora uses 3 → 21 on his disc; a 2nd
  fighter with 6 outfits + assist rows does not fit → Phase 2 buffer move, P2.7). Max id 1456. **273 free ids below
  1338** (owner-34 rule), e.g. 1255-1258, 1286-1287, 1335-1337, 1161-1164 (full list in the JSON).
- Voice line ids, texture keys, FEPA ids, picture numbers: no new scan; owner_tables.json values stand (voice
  subtitle ids ~1050 free after Sora's 1000-1143; texture keys/FEPA file-local; picture numbers = append to each pack).

### Open (for the allocator / next owner)
- R: full flag-array dump on the 100 % save (also gives the real meaning of block 2 if any bit is set there).
- Map the 53 unresolved functions to their data files (story/event scripts first). Each one mapped turns "probably
  free" into "proven free" for its range.
- `tools/pkg/allocate.py` (P2.6 Method) is not written. This task delivered its inputs (flag_map.json, id_spaces.json,
  the pool table).

## P2.0 oracle + inventory freeze — Claude (P2.0 helper), 2026-10-20, static

### Oracle (frozen 2026-10-20T12:05Z)
- **Choice: R4** = `dumps/ULUS10566-R4-test.iso`, sha256 **9d311d17a7739fee2c6768f0dce3e1703db587b7c0eefd5d5180e983eb92205f**
  (1,813,544,960 B) = R3 (release 1.0, 4cabe666…91fa) + spot33_oppinfo (RR-22 #5, 8 data bytes in OVL_BATTLE_APP).
- **Why (plan rule "p17, or RC3 if the OQ fix ships first"):** RC3 did ship (v1.0.0 = R3 / p18), so p17 is out. R4 beats
  R3 because the oracle must be what today's canonical scripts build: build_sora.sh now runs spot33_oppinfo, so with R3
  as oracle every Phase-2 disc would show one extra difference that is not a hook site. R4 is the reference build of
  the current inputs (scripts unchanged since: build_sora.sh c9be7bdd…, bootstrap_base.sh 33e561a5…, aggregate
  tools/scripts c8330339… = dumps/build-R4.inputs, rechecked 12:00Z).
- **Known delta to the release:** `equiv R3 vs R4` = exactly 1 content difference, OVL_BATTLE_APP 0x08AFB7F0/F4
  (−1,−1) → (63,63) (dumps/equiv-R3-vs-R4-test.txt). Anything else a P2 disc differs from R4 in is a regression.
- **Limits:** R4 is layout R (reference build: rows in PACKAGE_INFO, no EXTRA.PRX). There is no installed layout-B twin
  (no "p19"); `equiv.py --expect-engine` already proved R ↔ B equivalent for R3 ↔ p18, so engine discs (layout B/C) are
  compared straight against R4. R4 ran strict PPSSPP only (dumps/screens/r4/); the Vita ran test353/test354 = the
  same game bytes minus these 8.
- **Freeze:** read-only copy **`dumps/ULUS10566-P2-oracle-R4.iso`** (`cp --reflink=auto`, chmod 444, sha256 rechecked =
  9d311d17…205f). R4-test itself stays as it is (scratch name, may be rebuilt; the oracle copy is the reference).
  Inputs: dumps/build-R4.inputs + dumps/{bootstrap,build}-R4.log + dumps/build-R4.status. Rebuild recipe = clean dump →
  tools/scripts/bootstrap_base.sh → tools/scripts/build_sora.sh with those inputs (R3a == R3b showed it is deterministic).
- **Oracle package:** `packages/sora-R4` (NEW dir; `packages/sora` stays the 1.0/RC3 package 6742291b…e284) =
  `extract.py CLEAN P2-oracle-R4 packages/sora-R4 --report dumps/extract-P2-oracle-R4.report.json` → **UNMATCHED 0**,
  stop-gaps 1, layout pins 10, 183 files, 46 row tables, 22 patch sites, VALID, package_sha256
  **6cec661e714889461e2fd228ac5700f72b413468752b9c7edbb8a9568e72749b** (= the opp-info helper's scratch extract: the
  extractor is deterministic). Diff vs packages/sora: + rows/opp_info_name.json, manifest, and the harmless name spelling
  voice_P_SEV120_a_00.scd (same bytes). Log dumps/extract-P2-oracle-R4.log.
- **Compare a Phase-2 disc against the oracle:**
  `python3 -I tools/pkg/equiv.py dumps/ULUS10566-P2-oracle-R4.iso dumps/ULUS10566-p2N-<name>.iso --expect-engine --json dumps/equiv-oracleR4-vs-p2N.json > dumps/equiv-oracleR4-vs-p2N.txt`
  (exit 0 = IDENTICAL). Package check: `python3 -I tools/pkg/pkgapply.py verify dumps/ULUS10566.iso dumps/ULUS10566-P2-oracle-R4.iso packages/sora-R4`.
  Gap: equiv.py has no "allowed sites" list, so P2.3/P2.4's "only the converted site may differ" is read by hand from
  the owner_tables ids it prints next to each code word → add `--allow-site ID` (small, tools/pkg).

### Owner-33 inventory v2 — 2026-10-20 (oracle R4, byte-checked) — INPUT for P2.3 / P2.4 / P2.5 / P2.7 helpers
**Method:** same scan as the 2026-10-19 draft, re-written and run on `packages/sora-R4`: every new code word in
patches/*.json (word edits + the appended cave bytes) decoded, I-type immediates that are owner-specific listed
(33/34/35, name 63, pictures 245/246, items 678-682 / −678, flags −1263/−925/−888, ablt 832, drop 0x7f, OQ handle
≥ 64); img:* rows = data-in-code tables. Raw hits: `dumps/p2-oracle-owner-scan.json` (scanner
`tools/pkg/owner_scan.py`). Plus hand disassembly (tools/scripts/mdis.py on the oracle) for the OQ code and the hook
targets, and spot33_reflect.py source for the 3 draft "unconfirmed" items.

**Count:** code images carry **1,679 patched code words in 22 patch sites** (draft: 1,616 / 20). Owner-specific
places = **86, all confirmed by bytes** (draft 80 with 2 unconfirmed):
70 immediates in 19 sites (draft 69 + OQ handle test) + 2 more OQ constants found by disassembly (owner-33
face-table address, one-extra-pair loop end) + **14 data-in-code row edits in 11 tables** (draft counted 9 tables + "2 OQ
sites"; now oq_slot_tables = 4 rows, unlock_table = 2 words, ex_mode_page = 3 words, **+ opp_info_name** new).
Not owner-specific but in the code images: `menu_clock` (5 EBOOT words, global). `ex_burst_sound_skip` = **not on
the disc** (0 words, see #12). Data FILES: 46 row tables in packages/sora-R4/rows (+ `grwp` since the draft) — rows
per package, already generic; capacity notes below.

**What changed since the draft:** + `opp_info_name` (battle overlay table 0x08AFB6E8, row 33 at 0x08AFB7F0: (−1,−1) →
(63,63), spot33_oppinfo, RR-22 #5); + `menu_clock` (spot33_menuclock, Vita menu lag, global); + `grwp` (system.bin row,
spot33_grwp, Vita crash; data file, not code); OQ sites now in the package and byte-checked; #9/#12 resolved.
Everything in tools/scripts/build_sora.sh that touches a code image is covered (extract UNMATCHED 0 = no code word
outside code_sites.json, 98 ranges); no site was missing from code_sites.json.

**Draft "unconfirmed (indirect)" items, resolved:**
- #9 item_battle_effects (EE_B 0x089A8DE4..): **no owner test** (EE_HAS = loadout scan, EE_PIDX = participant, EE_GIVE
  = event 0x16). The owner tests of the item effects sit in EE_HIT 0x089C2280 (owner test at 0x089C22B8, item 678 at
  0x089C22E4) and EE_GUARD (owner test at 0x089C238C, item 679 at 0x089C245C) inside the burst_controller range. Crown
  Pendant HELM (cave 0x08B63140, hook 0x08AEC160) is **keyed by item id only** (constant 681, no owner test).
- #12 ex_burst_sound_skip (EX_SND): **not built.** spot33_reflect.py code_plan adds HOOK_EXSND only when
  TRINITY_CTL = 0; the build uses TRINITY_CTL = 1 (Sora runs his own controller TRI, never Cloud's variant-0 sound
  calls), so the cave has no EX_SND and 0x08A3A15C / 0x08A3A374 keep their clean words. → Nothing to port; P2.1 stub
  S23 can be dropped; owner_tables `ex_burst_sound_skip` = "not built (TRINITY_CTL=1)".
- #21 OQ: byte-checked on the oracle. oq_slot_code FUN_08A62530 builds pair 39 and stores it at 0x08A5468C
  + 0x30 = **0x08A546BC = face-table[33]** (owner 33 as an address), the loop-end constant allows **exactly one
  extra pair**; FUN_08A53F58 tests "entry ≥ 64 is a handle" (generic).

Legend — P2 task: **P2.3** lookup, **P2.4** behaviour (module C), **P2.5** save, **P2.7** capacity, **I** = stays
install-time data written per package (P2.1 mechanism I), **keep** = stays as is. Per-frame: **BATTLE/frame**, **MENU/frame
(likely)** = runs in draw/update code each frame (static reading of the role; not measured), **event** = list build /
scene build / load / once per hit.

| # | site (owner_tables id) | img | words | owner-33 assumption (bytes) | P2 task | per-frame |
|---|---|---|---|---|---|---|
| 1 | name_index_eboot | E | 10 | 0x088D625C owner==33 → name 63; bound 35 at 0x088D6254 | P2.3 — in place, 10 words, reads the scenario_names row (no registry; P2.3 note C1) | MENU/frame (likely: Records + menu name draws FUN_089ef21c/089f46e8/089f4a4c) |
| 2 | network_name_hook | M | 7 | 0x08A1D80C owner==33 → name 63 | P2.3 — in place: call #1 (FUN_088D6254), P2.3 note C2 | MENU/frame (likely, draw) |
| 3 | save_record_hooks | E | 123 | record slot 24 for 33 (0x088CB180/304/348/35C), OQ has-record 0x089293E4 + bound 35, friend-card limit 0x088F523C/52A0, 25-card migration helper | P2.5 (slot index = 57 − owner; one migration for all package slots) | event, but owner→record runs on every record read (menus read levels per cell) → keep O(1) |
| 4 | assist_drop_words + assistdup | E | 19 | 3 × drop 0x7f (generic); 0x088D5C7C Aerith append skips 33 | keep — the 0x21 there is vanilla's DLC-Aerith owner, assistdup is generic; the 3 drop words 0x7F = install-time immediate (only when a package owns 33). No REG_NEXT loop (P2.3 note §0.7) | event (list build) |
| 5 | ablt_cap | E | 1 | cap constant 832 rows | I / P2.7 (808 + Σ rows) | event (load) |
| 6 | bgm_mode7_fallback | E | 26 | 0x0888B668 opponent==33 + empty pool → stage music | P2.3 in place: owner bound = REG_ROW(opponent) in the same 9 words. **Do NOT drop the owner test** (vanilla mode-7 −1 for Chaos / Feral Chaos / locked Shantotto, Prishe; P2.4 note §3.7) — DECIDED 2026-10-20 | event (battle start) |
| 7 | exrun_hook | E+B | 25+2 | 0x089A8B34 owner==33, ×1.40 (the f32 constant 0x3FB33333 = **1.4**, not 1.3984375 — 2026-10-20 pilot); hook 0x08B2D380 | P2.4 (S7, ex_run_mult) — **ported** (step 0 pilot, step 1 stub 7) | **BATTLE/frame, every fighter** (movement update FUN_08b2d2cc; measured once per 30 Hz logic frame per moving fighter) |
| 8 | item_code_hooks | E+M | 212+2 | 4 × owner==33 (0x089A8C88/CAC/D10/D94) + 10 item-id tests 678-682 / −678 | P2.4 (S13-S22) + P2.7 (item ceiling 683: 1 free id) | mixed: PICID0/3 (item picture) + MENU_FIX = MENU/frame (likely, item lists / panel); SCALE/STASH = each stat build; ELIG/ROWMASK = list build; NEWGAME/ENSURE = load **Ported 2026-10-21 (P2.4 step 4, P24-items): stubs 13-19, 21, 22, 24 in EXTRA.PRX; EXITEMS + jump-table SCALE back to clean words; no owner / item constant left (P2.4-items.md).** |
| 9 | item_battle_effects | E+B | 61+2 | **no owner test** (see above); HELM keyed by item 681 | P2.4 (S5/S6, item_fx rows) | **HELM = BATTLE/frame for every fighter in EX** (EX drain FUN_08aec000; runs the 4-slot loadout scan); EE_HIT = per hit |
| 10 | burst_controller (TRI + EE_A) | E+B | 536+5 | 7 × owner==33 (TRI dispatch 0x089C1CB8, 0x089C2058 / 0x089C2090 / 0x089C20B8 = prompt / exit paths, bar voice owner 33 constant 0x089C2184, EE_HIT 0x089C22B8, EE_GUARD 0x089C238C), items 678/679; overlay variant-1 slot 0x08A39E04 | P2.4 (S0-S4, burst_ctl) | BATTLE/frame only during an EX Burst (dispatch + bar fill); prompt/exit once |
| 11 | reflect_guard + battle_overlay_cave | E+B | 7+128 (cave full, 512 B; "165" counted section headers, P2.4 note §2) | IS_SORA_EX 0x08B62F80 owner==33; hooks C1 0x0880A384 (a jump, no return), C2 0x0880A408, C4 0x08808B74, C3 0x08ADA22C, PROJ_AIM 0x08ADAAAC + table 0x08ADB32C | P2.4 (S8-S12); overlay back to vanilla size | BATTLE per clash / projectile collision (several per frame while hitboxes touch) |
| 12 | ex_burst_sound_skip (EX_SND) | – | 0 | **not built** (TRINITY_CTL=1) | none — drop | – |
| 13 | char_panel_sprites | M | 9 | 0x08AFF2EC owner < 33 test (owners < 33 use the table, 33 → owner 32's free sprite); PANEL_LIT 0x08AFF32C → EBOOT 0x089A8DC4 | P2.3 (panel_sprite, panel_tex) + P2.7 (sprite cells) | MENU/frame (likely, panel draw) — PANEL_LIT's EBOOT target is inside the EXITEMS range (moves with P2.4) |
| 14 | menu_picture_remaps | M | 131 | 13 × picture number 245 + party slots 0x08B2C520 owner==33 → 246, frame row 14 | P2.3 (pic_slot, pic_slot_party, party_frame) | **MENU/frame (likely)**: draw code computes base + owner − 1 per draw (notes/menu-art.md) |
| 15 | setup_banner_remap | M | 48 | 0x08AA4584 / 0x08AA627C picture 245, frame row 12 (Cloud's) | P2.3 (pic_slot, setup_frame) | MENU/frame (likely, setup draw) |
| 16 | museum_viewer_code | M | 35 | 0x08A32024 record 34 → 0x08A322F4 owner 33 | P2.3 (per-owner viewer table written by the installer) + P2.7 (viewer table 0x08A358FC = 34 entries, records 0..33, full; relocate) | event (viewer open) |
| 17 | records_list | M | 1 | 0x08A3D8F4 Chaos's append slot reused for 33 | P2.3 (REG_NEXT) + P2.7 (array 32) | event (list build) |
| 18 | jukebox_list_code | M | 10 | caps 35 / 34 + memset/offset changes | I + P2.7 (buffers full at 34) | event (list build) |
| 19 | jukebox_gate_code | M | 24 | flags 1263..1270 (range test: base −1263, 8 flags), 925, 888 | P2.3 (REG_FLAG bitmap from P2.6) | event (list build) |
| 20 | title_call | M | 155 | bound 35; DDD/SQE/day tables index 34 = Sora | I (installer rebuilds the tables) | event (once at title) |
| 21 | oq_slot_code | M | 58 | face-table[33] address 0x08A546BC; one extra pair (loop end 0x37C0); handle ≥ 64 test (generic) | P2.3 (oq_face_pic / layout) + P2.7 (handle storage exists for owners 33..35 — face table 36 words; the limit is the pair word only, P2.3 note §0.6) | builder = event (scene build); slot face FUN_08A53F58 = MENU/frame (likely) |
| 22 | menu_clock | E | 5 | none (global 333/333/166) | keep (engine base patch, not transitional) | event (scene change) |
| T | data-in-code rows (14 edits, 11 tables) | E/M/B | rows | unlock_table row 22 (2 words: owner 33, flag 925 / SEEN 3633); start_preset[33] = 250; scenario_names[33]; records_icons[33] = 0x4060; labyrinth_face[33] = 0x102D; menu_name_keys[32] = sev120; qb_grid_rows row 31; select_panel_list entry 30; ex_mode_page row 22 (3 words); oq_slot_tables (full name 0x08A54564 = 122, pair 39 0x08A637BC, banner 0x08A6B3D6 = 26028, party row 0x08A6CB96); **opp_info_name 0x08AFB7F0 = (63,63)** | I (installer writes a row per package owner) + P2.7 (unlock table 1 free row; select list relocate; opp_info rows end at 34) | none added (vanilla readers; keep them install-time data, not runtime lookups) |

**Owner-indexed places Sora did NOT need to patch, but owner 34 will** (from owner_tables.json, not owner-33 constants):
owner_bit_masks (33 aliases WoL bit 0, 34 aliases Garland bit 1 → item-owner table in module, P2.4 #8),
name_key_ptrs_eboot 0x089D6CA8 (room for 34, 35+ needs loop bound), battle_name_keys 0x08AFBC68 (34 OK), party_frame
0x08B2D168 (31 rows, 34 needs code → #14), network_names 0x08A23ACC (32 rows → #2), museum_viewer_owners 0x08A358FC
(30 rows, relocate → #16), grid_owner_bounds (≤ 34 OK), objentry id rule (owner 34 ids < 1338), save_stats_blocks
(≤ 34 / 35 OK), opp_info_name (row 34 exists, (−1,−1); row 35 = string data → owner 35 needs relocation).
- **owner_tables duplicate found:** `battle_names_file` ("battle overlay file off 0x11E284[owner−1]") is the SAME table
  as `opp_info_name` (VA 0x08AFB6E8 + 8·owner = file 0x11E27C + 8·owner; checked on clean + oracle: owner 13 = (12,29),
  33 = (−1,−1) clean / (63,63) oracle, 34 = (−1,−1), 35 = text bytes). Its "owner 33's row = Aerith's (unchanged)" was
  wrong — that blank row WAS the RR-22 #5 bug. Merge the two entries (P2.0 follow-up, owner_tables single writer).
  **Done 2026-10-20 (start-guide helper):** battle_names_file now mirrors opp_info_name's fields and is marked as a
  duplicate (kept so old references resolve).

**Per-frame cost (Vita menu lag lesson):** battle per-frame paths = #7 (every fighter, every frame), #9 HELM (every
fighter in EX), #10 (EX Burst only), #11 (contact frames). Menu per-frame paths (likely) = #1, #2, #8 PICID/MENU_FIX,
#13, #14 (13 sites), #15, #21 slot face. Scale: PPSSPP measured menus at 233-369 k ticks per frame of a 7.4 M budget
at 222 MHz (notes/dlc-phase1.md "Vita menu lag"), so an O(1) lookup of ~10-20 instructions even 100× per frame is
< 0.1 %. The real risks are not instruction counts: (a) a per-frame hook that calls into EXTRA.PRX through anything
slower than the data-indirect stub (syscall, kernel import, cache writeback / icache invalidate, file I/O); (b) a
registry LOOP (REG_NEXT / REG_BY_MUSEUM / item-owner search) placed in draw code instead of in the list builder;
(c) runtime code rewriting (JIT invalidation on PPSSPP, cache coherency on hardware). Rules for P2.3/P2.4:
per-frame sites use the EBOOT-resident O(1) REG_ROW (row = owner − 33, one bounds check, vanilla owners fall
through first); loops only in list/scene builders; behaviour stubs test "is a package owner" before jumping to the
module; every P2.3/P2.4 disc gets the per-screen tick count (PACKAGE-ACCEPTANCE B15) vs the oracle.
- **Oracle package proof:** `pkgapply verify CLEAN P2-oracle-R4 packages/sora-R4` → **REPRODUCES** 255/255 (rows 70, whole
  182, images 3; dumps/pkgapply-verify-P2-oracle-R4.log). packages/sora-R4 made read-only (chmod -R a-w) like the ISO.
- owner_tables.json (2 entries, 5 lines, format kept): `battle_names_file` marked "same table as opp_info_name" with the
  corrected owner-33 note; `ex_burst_sound_skip` → "not built", phase2_target none.

### Risks seen for P2.3 / P2.4 (from the inventory)
1. **[RESOLVED 2026-10-20 by decision: EXRUN pilot first, with the 6-word XSTB header + REG_ROW in the 28 words EXRUN frees — docs/PHASE2-START.md §4]** **Room before P2.4 (sequencing):** ENGINE.md puts the 5 lookup helpers (REG_ROW …) in 0x089A8B24-0x089A8F0C, which
   holds EXRUN / EXITEMS / EE_B until P2.4 ports them. So P2.3 cannot land its helpers first unless another EBOOT
   home is found (eboot_dead_code lists ~30 loose words + spare 0x0886EF90 — not enough for 63 words) or EXRUN
   (25 words, the smallest behaviour) is ported first to free 0x089A8B24-0x089A8B94 (28 words). Decide this before the
   first P2.3 disc.
2. **In-place menu sites have no spare words:** #14 (13 sites), #15, #2 were rewritten same-length using redundant
   slots; a generic site needs ≈ 4-6 words (a REG_ROW call, a register copy, a test and a load). Many will need a trampoline into the
   helper range → more words there than ENGINE.md's 63 estimate.
3. **Per-frame menu draws** (#1, #2, #13, #14, #15, #21) — any regression shows only on that one screen, and a slow
   helper shows as menu lag on the Vita only. Each P2.3 disc: vanilla control fighter on the same screen + tick count.
4. **Five copies of the owner → name map** (EBOOT 0x089CC020, 0x089CF350; menu 0x08A23ACC, 0x08A544E0; battle
   0x08AFB6E8) + owner_tables had one of them under two names. Convert or install-write all five together.
   **Update 2026-10-20 (P2.3 note §0.3):** the maps hold the same values (EBOOT 0x089CC020, menu 0x08A23ACC and battle
   0x08AFB6E8 for owners 1..32; 0x089CF350 for 1..31); 0x08A544E0 is the OQ full-name list (Sora = 122), a different list.
5. **P2.4 register contracts:** EE_PROJ uses the caller's fp/s0, EE_HIT reads s1, C1 is a jump (no return) inside the
   clash code, C1/C2/C4 are EBOOT hooks that jump into the battle overlay today. The C wrappers must keep exactly
   these contracts; stubs may clobber $at only (P2.1 check). TRI (536 words of hand asm + manager-block state) is the
   biggest port. Battle per-frame hooks (#7 every fighter, #9 HELM every fighter in EX) must test "package owner?"
   in the stub before entering the module.
6. **Item ceiling:** ids 0..682 load/save, Sora uses 678-681 → one free id; HELM/EE effects are keyed by item id, so a
   second package with items needs P2.7 first.
7. equiv.py cannot yet whitelist sites (see "Compare a Phase-2 disc" above).

### Next (my recommendation)
1. Add `equiv.py --allow-site ID` (tools/pkg) so every P2.3/P2.4 disc gets a one-line pass/fail vs the oracle.
2. Settle helper room (risk 1): port EXRUN first as the P2.4 pilot (smallest, battle per-frame → also proves the stub
   cost), which frees the start of the helper range; then P2.3 pilot = #1 + #2 name index (EBOOT + menu, smallest
   lookups, both per-frame → proves the O(1) path), with Records + network name screens and a vanilla control.
3. Codex review of P2.1 is still open (QUESTIONS 2026-10-19T11:28:49Z).
4. PACKAGE-ACCEPTANCE.md dry run on the oracle (P2.10).

## Phase-2 start guide, decisions and folded edits — Claude (start-guide helper), 2026-10-20, static
- Start here: [docs/PHASE2-START.md](../docs/PHASE2-START.md) (status, oracle, decisions, first three work items, space map,
  capacity, saves, tools, traps, open questions, glossary). Research notes: [notes/phase2/](phase2/).
- DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome): (1) table-shaped lookups use small per-owner
  tables written by the installer (P2.3 "OXT"), REG_ROW only where code needs it; (2) header-indirect XSTB stub table,
  6-word header fixed at 0x089A8B24; (3) first: P2.4 step 0 (infrastructure + EXRUN pilot) and P2.3 steps 1-2 (row
  generator with equiv IDENTICAL, then the two name rewrites), in parallel; (4) BGM fallback keeps an owner bound
  (REG_ROW), P2.3 in place; (5) stub list: S23 EX_SND dropped, PANEL_LIT added, P2.1-review High fixes in the design;
  (6) record slot index = 57 − owner (0-based: 24 = 25th card, 23 = 24th card), one migration for all package slots;
  (7) test34.json + registry.py fixed (above, P2.2 Open); (8) Cosmos fix F6 is part of P2.9's recipe; (9) "done" check =
  no owner-33 compare (0x21) left AND no other owner-33 / package immediates (owner_scan.py should report both).
- Inventory v2 rows changed above: #1, #2, #3, #4, #6, #11, #16, #21 (marked inline); risk 1 marked resolved; risk 4 got
  the "same values" finding.

## P2.4 steps 0 + 1 — inventory effects (Claude, P2.4 step-1 helper, 2026-10-21)
- #7 exrun_hook: behaviour in EXTRA.PRX (beh_exrun); registry ex_run_mult = 1.4. The EBOOT range 0x089A8B24-0x089A8B94
  now holds the XSTB header, the REG block (header + 0x18) and **REG_ROW 0x089A8B60 — owned by P2.4, P2.3 may call it**
  (owner_tables `stub_table`). Pilot report: notes/phase2/P2.4-exrun-pilot.md.
- #10 burst_controller (TRI + EE_A): ported to C (extra/beh.c, stubs 0-5 + temporary 29-31); the TRI range
  0x089C1C9C-0x089C2508 is the XSTB v2 table block now (abi_hash, FN_PTR[32], STUB[32], fallbacks; 193 of 539 words).
  Its 7 owner tests + items 678/679 + voice 21910042 + motion 8501 are gone from the disc (owner-compare scan 16 → 7 with P2.3
  names; P2.4 part 9). New registry data: aux TRI (`voice_bank` 219100, motions, banners, prompt) + aux EE.
  The only new owner immediate is the generic fallback bound (owner < 33) at 0x089C1F3C (owner_scan ALLOW):
  without the module, package owners run Cloud's variant-0 controller (runtime PASS, no hang).
- Open: a full Sora EX Burst freezes under PPSSPP's JIT on the step-1 disc when stub 5 (EE_HIT) is routed through the
  module (notes/phase2/P2.4-tri.md §4.3).
- **2026-10-21 P2.4 DONE (steps 2-4: P2.4-reflect / P2.4-shield / P2.4-items).** (The JIT freeze above was fixed in
  engine 2.1.1, P2.4-tri §8.) Step 4 (disc `dumps/ULUS10566-P24-items.iso` 807e09fc…1a0f): item ownership + menus
  (ENSURE, NEWGAME, ELIG, ROWMASK, MENU_FIX, PICID3/0, STASH, SCALE, PANEL_LIT) in EXTRA.PRX 2.4.0 behind stubs 13-19,
  21, 22, 24 (abi_hash 0x2F2EAE84); EXITEMS + the dead-jump-table SCALE back to clean words; registry: item_owner bit 7
  = start-owned, aux EXPAGE + SCALE, `params.crown_drain` retired. Disc owner-compare count 2 (BGM fallback + party pictures =
  P2.3); other owner/package immediates 14 (P2.3 / P2.5). What P2.3 / P2.5 / P2.7 / P2.9 inherit: P2.4-items.md §10.

- 2026-10-21 (P2.3 lookups helper): **P2.3 DONE** (steps 3-7). Inventory rows now generic: picture remaps / party frame /
  setup banner / Characters-panel owner → sprite (#14, #15, #13 part) = OXT tables PIC_IDX / PARTY_FRAME / SETUP_OFF /
  PANEL_SPRITE; Museum viewer (#16) = VIEWER_OWNER; Records icon = REC_ICON, Records append = REC_APPEND (+ REC_HELP);
  OQ face (#21) = OQ_PAIR + EBOOT OQ_BUILD (owners 33..34, the one-extra-face limit is gone); Jukebox gates (#19) =
  FLAGPKG over the EXTRA.REG flag-range list (engine 2.5.0, MIN_ENGINE 0x00020500; sora 3 ranges, sora + test34 4 =
  364 B instead of 536); BGM mode-7 fallback (#6) = REG_ROW via BGM_FB. All in the freed EBOOT block 0x089A8B94-0x089A8F0C
  (header "OXT1", 20 words spare). Final disc dumps/ULUS10566-P23-flags.iso 39d82a75…8fb3: owner-33 compares = 0, the 5 owner
  immediates left are the save hooks (#3, P2.5). Still for P2.7: Records array growth, owner-34 sprite cells, grid /
  select / EX-page rows, title-call slots; for P2.8: installer writes the OXT tables (p23_lookups.py logic), KEY_POOL
  for new keys, drop the now-unread rowgen rows (D4 0x08A407A4, D7 pair 0x08A637BC). notes/phase2/P2.3-flags.md §6.

- 2026-10-22 (P2.5 save-records helper): **P2.5 DONE** (notes/phase2/P2.5-saves.md). Inventory row #3 (save_record_hooks)
  is generic: GET_RECORD FUN_088CB164 → a call to PKG_REC for owners outside the vanilla list; the R4 SORA_REC cave
  (dead FUN_088CB2C0) is clean again; OQ has-record FUN_089293DC reads REC_MARK; the friend-card caps = REC_CAP. Rule:
  record slot = 57 − owner, cap = lowest installed slot, migration once for all package slots (count > cap → cut, re-
  receive every non-record card in the package slots, set up lazily). Data = installer-written "SRC1" block at EBOOT
  0x089C2340-0x089C2508 (REC_CAP, REC_MARK u8[36], REC_FLAGS u8[36] bit 0 LEGACY, PKG_REC 94 words); registry
  install.record_mark / record_legacy (EXTRA.REG unchanged). Disc dumps/ULUS10566-P25-saves.iso 8f163258…31c7:
  **owner-33 compares 0, other owner/package immediates 0** (allowed 3, no new ALLOW entry). Old plan text "friend-card limit = 25 −
  number of package owners (module computes at boot)" (rows #3 above) is superseded: the installer writes the cap
  (= min slot) and the module is not involved. Found: Mat's 100 % save file is still in the pre-344c legacy state
  (count 25, Sora unmarked); the Friend Card menu commit (FUN_088f7988) re-initialises cards 0..cap−1, so a removed
  pack's record is cleared by the next commit (P2.5-saves §3 D6).

- 2026-10-21 (P2.8 helper, design only; pointer added 2026-10-22): **P2.8 Sora as a package — DESIGN DONE (static); the build is in progress (notes/phase2/P2.8-build.md)**:
  notes/phase2/P2.8-sora-package.md. Engine base = 820 clean-based words (LOADER 53 + ENGINE 624 + ENGINE_R4 143,
  `tools/pkg/p28_plan.py words` on P23-flags), roster-generated rows / OXT / panel_tex never stored, Sora format 1.1
  (registry.json in the package, identity-keyed rows, transitional `save_record_hooks` / `title_call`), installer
  layout C, steps E1–E8 (§6). Merge gap classes G1–G5 (§3): identity-keyed codec prototypes `tools/pkg/p28_codecs.py
  prove` 82/82. Inventory effects: row #3 (save_record_hooks) is generic since P2.5 (so p28_plan's SORA_LEFT rule
  needs a P25 update, docs/ENGINE.md "Engine package"); title_call stays for P2.7. Open for Mat: Q-P28-M1 (menu_clock in
  the engine base), Q-P28-M2 (canonical re-encode of 10 pinned files with 2 packages).
