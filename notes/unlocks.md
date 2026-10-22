# Unlocks / PP Catalog / secret voices (menu-art helper, 2026-10-17) — static only

## 1. PP Catalog data
- `update_list_param.bin` (package root path; label/"update list" scene, texts text/EN/mess_pk_update_list_0.bin):
  `u16 4, u16 tab counts 117/44/31/93/41, u16 32 (string count), u16 -1`, then 28-byte items back to back, then
  32 × 64-byte strings (preview picture / voice file names for the character items).
- Item (u32 + 12 × s16): PP cost; name text (group 0; 21 = just "%s"); help text (group 3); ?; visible-after flag ×2
  (−1 = always listed); **flag set when bought**; "new" flag; message kind (2 = "You can now play as %s!"); arg kind;
  arg (character name = group 2 index, BGM = bgm text id = group 6 index); arg-2 kind; arg 2.
- Tabs: 0 = characters (items 0-14: villains 30-100 PP, Prishe/Gilgamesh 300, Feral Chaos 350; flag = EBOOT unlock
  table flag 700+owner−1), alternate looks (costume flags 735+/770+), "Encounter Voice"/"Secret Voice" items,
  "Chaos (CPU)" (item 15, 90 PP, flag 925); 1 = modes/options; 2 = level bonuses; 3 = player-icon sets (each sets a flag;
  system.bin "uicn" icon rows with that unlock flag become owned; "[Avatar] X" = icon of X's chibi avatar costume on a
  gold card, 150 PP, flags 1136-1153); 4 = items/BGM ("BGM - %s" 150/240 PP, flag = bgm_entry row unlock flag 1047-1071).
- Fighter availability = EBOOT unlock table 0x089D7BE0 (owner, unlock flag, costume-2 flag, costume-3 flag, SEEN flag — see §5);
  flag bits in DAT_089d726c (save data). Row 22 (Chaos, flag 925) has been owner 33 since test20 (eboot_plain).

## 2. test327 `dumps/ULUS10566-test327-ppcatalog.iso` (2026-10-17T01:28Z, sha256 38e8611d…a44c) = test325 +
- **spot33_catalog.py (new)**: tab-0 item 15 "Chaos (CPU)" → "Sora" (300 PP, always listed, sets flag 925 — Chaos is
  not in the unlock table any more, so that item did nothing); EBOOT unlock row 22 → (33, **925**, 1, 1, 3623);
  tab 3 + "[KINGDOM HEARTS II] Set of 3" (150 PP, flag 1253) + "[Avatar] Sora" (150 PP, flag 1254) at the end of the
  icon tab; tab 4 + three "BGM - KHII - …" (240 PP, flags 1249/1250/1251); texts group 0 #169/#170, group 2 #63
  "Sora", group 6 #132-134. UNLOCK=0 env = Sora stays unlocked from the start.
- **spot33_museum.py**: player icons 414 Sora (unchanged art), 415 Riku (KH2 journal jmface_ex8), 416 Kairi
  (jmface_ex4) on white = KH set (uicn flag 1253; 414 was flag 1 = owned from the start in test302-325), 417 Sora
  avatar (jmface_ex1 on the avatar gold, flag 1254); collection section-4 rows, group-4 names, icon files, friend-card
  archive user_icon12 (385-416) + **new user_icon13.bin** (the game loads ceil(icons/32) archives: 417 → 14).
  uicn 417 rows (EBOOT buffer max 420). ICONS_FREE=1 env = all owned from the start.
- **spot33_music.py** (MUSIC_UNLOCK, default on): KH2 bgm_entry rows' first unlock slot and their Museum records =
  1249/1250/1251 → locked until bought (not in the BGM pickers / Museum list; auto music vs Sora falls back to the
  stage's music until bought). MUSIC_UNLOCK=0 = always.
- spot33_outfits.py / eboot_plain.py accept the new unlock row (re-runs stay "already").
- Flags: 1249-1251/1253/1254 are not used by any flag table (catalog items, unlock table, uicn, bgm_entry, Museum
  sections, Jukebox voices) and appear in no code immediate; 925 = Chaos's old unlock flag.
- **Existing save**: a save that bought "Chaos (CPU)" (or a 100 % save) has flag 925 → Sora stays unlocked and his
  catalog item shows as bought. Otherwise Sora is locked until bought for 300 PP (also gone as assist until then;
  the assist drop-check fix stays). The save file itself was not found/readable here (PPSSPP memstick not under the
  usual paths; downloads/ has encrypted DISSIDIA.BIN backups only).

## 3. "Secret Voice"
- PP Catalog tab 0 items 109-116: "Secret Voice - <name>" (150-300 PP; Cecil, Bartz, Vaan, Laguna, Yuna, Kain, Tifa,
  Prishe). Help: "Unlocks secret voice data for <name>. Playable in the Jukebox." Each sets a flag 842-850.
- Jukebox data = `collection_voice_param.bin`: u16 1, u16 33 groups (owners 1-32 + 255 = system), 44-byte voice rows
  (category, unlock flag, …, file name). The flag-842..850 rows are single special lines inside those characters'
  normal voice banks (e.g. voice_p_for200_00 #11, voice_p_gst110_01 #1-11 for Prishe) — hidden extra lines that only
  become playable in Museum → Jukebox once bought. Nothing changes in battle.
- Owner 33 has no Jukebox voice group at all (not an Aerith leftover: Aerith never had one), so Sora has no voices in
  the Jukebox and no secret voice. Adding one = a 34th group with rows pointing at Sora's voice bank lines (+ texts).
  **→ Done 2026-10-18 (test345): group 33 + catalog item, see §6.** (Still no Secret Voice for Sora.)

## 4. Records / Friend Card names + Records wins/losses (test329, 2026-10-17T01:46Z)
`dumps/ULUS10566-test329-records.iso` = **copy of test330-merge** + spot33_museum (icons 415-417) + spot33_catalog +
spot33_ownername (new) + spot33_music (UNLOCK); sha256 6485be0b8d274795efbcfd53e5f45918a2d13dc0756cfcb7422c2959fcd4ced2.
Every step re-run --dry = "already" (also menuart, outfits --no-events, eboot_plain).
- **Name lookups by owner** (all lacked owner 33):
  - EBOOT FUN_088d6254(owner) → u32 0x089CC020[owner] (owners 0..32; bound check 35) → owner 33 read string bytes.
    Callers: Records (FUN_08a3eb78, collection text group 3), menu FUN_089ef21c / FUN_089f46e8 / FUN_089f4a4c,
    EBOOT all.c 491108. Fix: rewritten in place (11 words): out of range → 0 as before, owner 33 → 63.
  - menu FUN_08a1d7f8 (network scene = Friend Card Settings: favourite-character icon name, Ghost character name)
    → u16 0x08A23ACC[owner−1] (32 owners; owner 33 read the next table = 97). Fix: 13 words in place, owner 33 → 63.
  - EBOOT 0x089CF350[owner] (u16 name, u16 manikin name; owners 1..31; used by EBOOT 0x08911DBC scenario
    characters and the Labyrinth menu 0x08B4E414/0x08B4E688): owner 33's slot 0x089CF3D4 was zero padding (= WoL)
    → (63, 63). Not touched: battle overlay table (file 0x11E284, owner 33 = (−1, −1)).
  - "Sora" appended as name 63 to the 63-name groups: collection 3, colosseum 1, creation_room 1, dungeon 2,
    loading 1, md_list 4, network 3, worldmap 1 (update_list 2 via spot33_catalog).
- **Wins/losses — save data**: battle results are written per OWNER by FUN_08b0c4xx → FUN_08adcfa0(save+0x10CEC):
  "as this character" block at +0x10D38 + owner×200 (room for owners 0..35) and "against this opponent" block at
  +0x12958 + owner×0x30 (owners 0..34). Owner 33 fits in both and nothing skips him, so his numbers ARE stored (no
  save change needed; Chaos's owner-23 slots untouched). Records (FUN_08a3f518) reads the same blocks by owner.
  List filter (FUN_08a3dd10): Wins / Losses / Battle Time / most per-character pages show a character only if he is in
  the available list (unlock row; after test327 = flag 925 bought) **and has battles AS that character**
  (record[3] ≠ 0) and the value ≠ 0; the "… by opponent" pages use the opponent block instead. So Sora's Wins/Losses
  rows appear only for fights where you PLAYED AS Sora (vs-CPU-Sora fights count on the "by opponent" pages). With the
  name missing his rows were also easy to miss (icon + number only).

## 5. Yellow "NEW" tag after buying Sora (2026-10-18, static; test341)
Runtime (Claude, p14-engine = test339 + engine): after buying Sora no yellow NEW on his grid cell / series logo;
Garland, bought just before, had both.
- **Unlock table field 5 is the SEEN flag, not a text id** (EBOOT 0x089D7BE0 rows = owner, unlock flag, costume-2
  flag, costume-3 flag, SEEN flag; vanilla SEEN = 3600 + owner, 3601..3632).
  - FUN_088d5ac8 (select list for the QB grid, Customization, …) stores FUN_088d60e4(owner) in entry +4:
    1 = the row's SEEN flag bit (DAT_089d726c) is clear → NEW on the cell + logo. FUN_088d5e0c gives the costume bits.
  - Leaving the grid (menu FUN_08a80c24) clears bit 0 of every entry and calls FUN_088d61ec → FUN_088d617c, which
    sets the SEEN flag of every listed fighter. Buying in the catalog sets only the unlock flag.
  - New-game init (EBOOT, DAT_089d726c[0x70]/[0x71]) pre-sets SEEN for the starting fighters (3601-3615 odd,
    3617/3619/3624/3626-3628/3630/3631). Flag area = DAT_089d712c+0x1df88, 0x280 B = flags 0..5119.
- **Cause**: row 22 (Chaos's row, owner 33 since test20) kept Chaos's SEEN flag **3623**. Sora was always unlocked in
  test20-326, so any save that opened the grid then has 3623 set → after buying him he counts as already seen.
  A fresh save would have shown NEW. Not an owner-mask problem (the 32-bit mask FUN_088d5ce8 is only the colosseum
  reward screen / item code).
- **Fix** `tools/scripts/spot33_newtag.py ISO [--dry] [--rollback]`: row 22 SEEN 3623 → **3633** (= 3600+33). One EBOOT
  word (ISO byte 0x2ECD80: 0x27 → 0x31). 3633 is in no unlock row, catalog item flag field, collection_param record,
  code immediate, and not in the new-game init. Guards: plain ELF; row 22 = (33, -1|925, 1, 1, 3623|3633); the three
  reader functions byte-identical to the clean EBOOT (sha256 prefixes in the script); 3633 unused (checked live).
  Effect: every save shows NEW once on Sora after he is unlocked (also saves that bought him already / UNLOCK=0
  builds: NEW on the first grid visit), then it clears like vanilla. Chaos's 3623 is orphaned (harmless).
  spot33_outfits.py / spot33_catalog.py accept and keep 3633 on re-runs; eboot_plain.py already ignored field 5.
  build_sora.sh: after spot33_music, before spot33_installfix (still LAST).
- Test disc `dumps/ULUS10566-test341-newtag.iso` = copy of test340-sorasvs (720428b8…0075) + spot33_newtag;
  sha256 8fc470239a339a00ce1fff355702fc275e0ebeff5ae9c4443a426a9369ecbe6b; cmp = that 1 byte only. Not run yet.
- Runtime check: ptr = u32 @0x089D726C; word ptr+0x1C4: bit 7 (0x80) = 3623, bit 17 (0x20000) = 3633. On Mat's
  save copy expect 3623 set, 3633 clear before the first grid visit; Sora NEW (if bought) → leave grid → 0x20000 set,
  NEW gone. A 2nd new fighter needs its own SEEN flag (3634+ looks free up to 3650; Museum viewed = 3651..3685).

## 6. Sora in Museum → Jukebox + "Encounter Voice - Sora" (2026-10-18, static; test345, RR-10)
Mat: "Add Sora voice to jukebox as well, make this as legitimate feeling as possible."
- **Native data** (all static; menu overlay OVL_MENU_APP):
  - Character list = `collection_param.bin` **section 8** (33 × 4 B: u16 unlock flag, u8 owner, u8 0xFF; order 31,30,27,
    28,24,26,1..22,29,25,23,32,255 = system). FUN_08a36ee8 copies listed entries to obj+0x710 (cap **0x21**, memset 0x42);
    FUN_08a37024 puts the chosen fighter's visible rows at obj+0x752 (cap 0x200, memset 0x400); obj+0xb52 = file-name buffer.
  - Rows = `collection_voice_param.bin` (§3 layout: u16 1, u16 groups; group = u16 owner, u16 rows, u16 bytes, −1; 44-B row =
    category, unlock flag, index, bank slot, kind 0 at3 / 1 scd slot / 2 event at3, −1, char[32] file). Category text =
    collection text group 6: 2 "Encounter %s", 3 "Victory (%s)", 4 "Loss (%s)", 5 "Battle (%s)", 11..42 "vs <fighter>"
    (category = 10 + display order: 11 WoL, 15 Kain, 19 Tifa, 25 Vaan, 38 Prishe, 40 Gilgamesh, 41 Chaos, 42 Feral Chaos),
    44 "Loss - Battle", 45 "Assist", 46 "Secret Voice %s". Shown as "<name>：<category>" (text 55; name = FUN_088d6254 →
    collection group 3, owner 33 → 63 "Sora"). **No line text/subtitle is shown in the Jukebox for any fighter.**
  - Kind-0 rows only play if the clip is in the owner's **museum VOLD copy** `voice/EN/voice_load_parameter.mpk` member
    `voice_load_p_<key>.bin` (EBOOT FUN_088a3a94, 35 slots, key table 0x089D6CA8, [33] = "sev120"; volume = row moment low
    byte 0x46 = 70 %). Vanilla: every member is byte-identical to the loose `voice_load_<KEY>.bin`; there was no sev120.
  - Rule (checked for all 30 regular fighters): Encounter N = moment 0x46 rows cond 0/5/7/8 (unique, list order), vs X =
    cond-2 row value X, Victory N = all 0x146 rows, Loss N = all 0x246 rows, Battle N = chosen voice-bank slots (Cloud: 0-3,
    5-37, 42), Loss - Battle = KO slot (Cloud 4), Assist = assist-bank slot (Cloud 41). Encounter + vs rows need the
    fighter's Encounter Voice flag **856..887** (PP Catalog tab 0 items 77-108, 180 PP, Feral Chaos 10 PP; owners 1-22 →
    856-877, 24-31 → 878-885, FC 886, Chaos 887); every "vs Feral Chaos" row needs FC's 886; Victory/Loss/Battle = −1.
  - Jukebox "complete" (FUN_08a3c9c8, used by FUN_08a4175c/FUN_08a3cc18 Museum completion) walks every section-8 entry and
    row → a 100 % Museum now also needs "Encounter Voice - Sora" (like the KHII BGM items for music).
- **Fix** `tools/scripts/spot33_jukebox.py ISO [--dry]` (build_sora.sh: after spot33_savefix, before spot33_installfix):
  1. PP Catalog tab 0 #109 (right after "Encounter Voice - Feral Chaos"): **"Encounter Voice - Sora", 180 PP, sets flag 888**,
     listed after Sora's unlock flag 925 with "new" flag **2093** (villain pattern); UNLOCK=0 builds → always listed, no
     new flag (hero pattern). Texts are the game's own (name 30 "Encounter Voice - %s", help 4, arg = name 63 "Sora").
     spot33_catalog.py keeps the item on re-runs (strip_ev/insert_ev).
  2. Section 8: + (925 | −1, owner 33) after Feral Chaos, before the system entry.
  3. Collection text group 6 #78 **"vs Sora"**.
  4. Group 33 (after 32), 93 rows from Sora's loose VOLD + bank: Encounter 1-15 (so_battle_11..25), vs 1..32 by category
     (30 so_vs_* + so_vs_fc under 886) + "vs Sora" mirror (so_vs_sora), Victory 1-7, Loss 1-5, Battle 1-33 (voice_p_sev120_00
     slots of Cloud's native list, empty/identical-audio slots 5/22/26/30/36 skipped), Loss - Battle = slot 4 ("No way!").
     Same-audio copies skipped (a native group never lists a line twice): so_battle_30 (=26), 39 (=34), 40 (=35) and the
     generic vs-Chaos fallback so_battle_71 (=24) → **no "vs Chaos" row until a real Sora-vs-Chaos line is routed** (re-run
     picks it up). No Assist row (Sora's assist bank slot 41 is empty). Flags: Encounter/vs 888, vs FC 886, rest −1.
     + a **"vs Sora" row in 30 other groups** (owners 1-22, 24-31; after their vs-FC row; flag = that fighter's own Encounter
     Voice flag): <prefix>_vs_sora / li_vs_sora / ca_vs_sora (Chaos/FC have no vs-Sora line).
  5. Museum VOLD copies = the loose lists again (30 members got their vs-Sora row from spot33_vsvoices) + new
     voice_load_p_sev120.bin. Re-run spot33_jukebox after any VOLD change (build order already does).
  6. OVL_MENU_APP 10 words: 0x08A36F20 compare bound 0x22→0x23, 0x08A36F2C cap 0x21→0x22, 0x08A36F40 memset 0x42→0x44;
     0x08A37078 compare bound 0x201→0x200, 0x08A37084 cap 0x200→0x1FF, 0x08A37090 base 0x752→0x754, 0x08A37098 memset 0x400→0x3FE,
     0x08A37128 / 0x08A37CA0 / 0x08A38444 0x752→0x754 (all obj+0x752 users; overlay scanned for immediates 0x700-0x75F).
     Row list still ends at 0xB52; largest group 292 rows < 511.
- **Flags free (checked on every run)**: 888 / 2093 not in any catalog item field, unlock row, collection_param section
  0/6/8 flag, Jukebox row, uicn row, bgm_entry row, nor an ori/addiu-from-zero immediate in EBOOT / menu / battle code.
  888 = next after the Encounter Voice block 856..887 (888-891 is a gap in the catalog flag area); 2093 = next after
  Chaos's 2092. Not proven: flags set by story event scripts (none of the scanned tables uses them).
- Guards: catalog tab 0 = 117 vanilla-count items (+ ours); section 8 = vanilla sha (+ ours); text group 6 = vanilla 78
  entries (+ ours); every Jukebox group = vanilla sha (+ our vs-Sora row), group 33 = ours; every museum member = vanilla
  sha or the loose list; menu words vanilla or ours + 11 vanilla neighbour words; refuses an ISO PPSSPP has open.
- Test disc `dumps/ULUS10566-test345-jukebox.iso` = copy of test343-final-voices (1f371261…2552) + spot33_jukebox only;
  sha256 a3979cf87d7de6be9e5ce17e7ae1274189e2844cc2cddb933e2ed7afa1b61552. equiv.py vs test343: exactly the 5 package files
  + 10 menu words; re-run --dry = all "already"; spot33_catalog/museum/music/newtag/ownername/vsvoices --dry on it =
  already/no change. No PACKAGE_INFO row added (installfix not needed). Not run in the emulator yet.
- Runtime check: flag 888 = word ptr(0x089D726C)+0x6C bit 24 (0x01000000); 2093 = +0x104 bit 13 (0x2000).

### §6 runtime — PASS (2026-10-18T16:47:10Z, Claude, test345, copy of the 100% save)
PP Catalog → Characters: "Encounter Voice - Sora" right after "Encounter Voice - Feral Chaos", 180 PP, NEW marker,
native help text; bought → BOUGHT, PP 196671 → 196491. Museum → Jukebox → Voices: L/R order … Feral Chaos → **Sora** →
Cosmos (system); labels "Sora：Encounter 1", "Sora：vs Cecil", "Sora：Victory (2)/(5)" etc. Playing Encounter 1: game
audio silent at idle, ~2.5 s of speech on play (RMS per second 0 / 3716 / 6120 / 3472). Side effect seen: catalog
Complete 99% and Jukebox star grey on a 100% save until the new items are bought (expected, like DLC-style additions).

## 7. RR-08 flag collision: vanilla sets 1250-1262 → KH2 catalog flags moved to 1263-1267 (2026-10-18, static; test349)
Runtime (coordinator, test348 on a COPY of a downloaded vanilla 100 % save): flag word 39 = 0xff807ffc
→ 1250-1262 and 1271-1279 set, 1248/1249 and 1263-1270 clear. So KHII Working Together (1250), Sinister Shadows (1251),
"[KINGDOM HEARTS II] Set of 3" (1253) and "[Avatar] Sora" (1254) counted as bought; vs CPU Sora picked bgm 133.
§2's claim "1249-1254 not used by any table / no code immediate" was true but incomplete: the setter uses bit MASKS.
- **Setter (menu overlay, clean dump): FUN_08a2b07c** (called from menu scene setup FUN_089e1a64 /
  FUN_089e3db8). Highest record level of owners 1..32 except 23 (`FUN_088cb164(save+0xF58, owner)+1`):
  > 29 → `*(ptr+0x9C) |= 4` (**1250**), > 49 → `|= 8` (**1251**), > 69 → `|= 0x10` (1252); then table 0x08A2E8AC
  (owner, level, flag): owners 8, 10, 24, 25, 26, 27, 28, 29, 30, 31 at level 100 → **1253**, **1254**, 1255 … 1262.
  system.bin `infp` (FUN_088c0b10: kind, if-flag, set-flag) turns 1250-1255/1257-1261 into info flags 1301-1312 (all
  set on the save, 1307 clear = consistent). **Genuinely vanilla**: any save with a Lv30 fighter has 1250, Lv50 1251;
  not a save-editor artifact. (Side effect of test327-348: buying a KH2 item on a low save also set 1301/1302/1304/1305.)
- 1271-1284 (set on the save) = vanilla icon-set flags (catalog tab 3 items + uicn rows); never ours.
- uicn icon flags are 1076-1203, 1207-1247, 1271-1284; the gap **1263-1270** sits between the level flags and the
  icon flags: no setter (FUN_08a2b07c's masks/table stop at 1262; it is the only constant-offset writer of word 39 in
  EBOOT/battle/menu decompiles), no table entry (catalog fields, unlock table, comflag lists, collection_param
  sections 0/6/8, Jukebox rows, uicn, infp, tuto, bgm_entry, party_battle-pbtl rows), no ori/addiu immediate, and
  clear on the 100 % save. 1249 is also unset by vanilla but moves with the block.
- **New numbers**: TR 1249 → **1263**, WT 1250 → **1264**, SS 1251 → **1265**, KH set 1253 → **1266**, avatar
  1254 → **1267** (word +0x9C bits 0x8000 / 0x10000 / 0x20000 / 0x40000 / 0x80000). 1268-1270 stay free.
- **Fix**: `tools/scripts/spot33_unlockflags.py ISO [--dry] [--rollback]` (build_sora.sh after spot33_oqrecord,
  before spot33_installfix = still LAST). Migrates in place: catalog items (tab 3 last 2, tab 4 last 3, field "flag
  set when bought"), uicn rows 413-416 (+4), bgm_entry rows 131-133 (+4), Museum music records 127-129 (+2); each
  must be ours with old or new numbers (ICONS_FREE flag 1 / MUSIC_UNLOCK=0 −1 left alone), else stop. Re-checks the
  evidence above on every forward run (+ FUN_08a2b07c and its table byte-identical to clean). Refuses the clean dump
  and an ISO PPSSPP has open. spot33_catalog / spot33_museum / spot33_music now write 1263-1267 and accept the old
  numbers (rewrite them). Same sizes; nothing else changes.
- Other mod flags vs the same evidence: 888 (EV Sora) clear, 2093 (EV "new") clear, 3681 (Museum viewed) clear,
  925 set = intended (Chaos (CPU) bought → Sora owned). 3633 (Sora SEEN) set — vanilla rows only use 3601-3632, so
  this was the test348 grid visit (expected) unless a save editor set it. 2993 (icon 414 "viewed", vanilla viewed
  flags end at 2992) set while 2994-2996 clear — most likely viewed in the test348 session because 1253 made icon 414
  owned; confirm. Cosmetic: the Sora catalog item reuses Chaos's "new" flag 2263, set on any save that saw the Chaos
  item → no NEW marker on Sora's item there (not an ownership problem; a free "new" flag would fix it).
- Old purchases: a dev save that bought an item on test327-348 loses it (old bit no longer read). Released builds
  never shipped those numbers; packages/sora rows (uicn.json, pp_catalog.json, bgm_entry.json, museum_music.json)
  still carry 1249-1254 → **P1.2 owner must re-extract after this lands in an R build**.
- **Test disc** `dumps/ULUS10566-test349-rr.iso` = copy of test348 (3d7ca927…1aed, only read) + spot33_unlockflags;
  sha256 60731b0ecca64ce45d898ca36468371f7fcd9d88673f43a34349d86e53f9143f. isodiff vs test348: 3 package files
  (update_list_param.bin, main.bin, collection_param.bin), same sizes, 15 bytes (low byte of each flag). Re-run =
  "already"; spot33_catalog/music/museum/jukebox/newtag --dry on it = already. Not run in the emulator.
- **Runtime check** (same save copy): ptr = u32 @0x089D726C, w = u32 @ptr+0x9C. Before buying: w & 0x000F8000 == 0;
  catalog shows all 5 items unbought; KH2 tracks absent from BGM pickers/Museum; icons 414-417 locked; vs CPU Sora the
  music is not bgm 131-133. Buy TR → 0x8000, WT → 0x10000, SS → 0x20000, KH set → 0x40000, avatar → 0x80000; the
  vanilla bits 0x4/0x8/0x10/0x20/0x40… stay as they were, and word ptr+0xA0 (1280-1311 info flags) does not change.
  Save → reload → bits and BOUGHT kept.
- **Addendum 2026-10-19 — Jukebox listed unbought KH2 tracks (test349 runtime) → fixed in test351.** On the same save
  copy, after buying only Sinister Shadows (1265 set, 1263/1264 clear), Museum → Jukebox → Music still listed all three
  KH2 tracks. Cause: menu FUN_08a36d1c (music list) lists a section-6 record when its flag is 0xFFFF/set **or when
  FUN_08a41098() — flag 1372, word ptr+0xA8 bit 0x10000000 — is set ("list everything")**. Our records 127-129 carry
  the right flags; the save evidently has 1372 set (to confirm in RAM), so every record shows. The same override sits
  in the voice character list FUN_08a36ee8, the voice-row list FUN_08a37024 and the Museum item lists FUN_08a301b0
  (via FUN_08a30480 → obj+0x6d6). Vanilla PP BGM rows (flags 1047-1071) are gated the same way: own flag, overridden by
  1372 — a 100 % save owns them all, so only ours leaked. test348 (old flags) leaked identically. 1372: no constant
  writer in EBOOT/menu/battle decompiles, no catalog/unlock/uicn/infp/tuto/Museum/Jukebox/bgm_entry/pbtl row; origin
  on that save unknown.
- **Fix** `tools/scripts/spot33_jukeboxgate.py ISO [--dry] [--rollback]` (build_sora.sh before spot33_installfix =
  still LAST): 3 × 15 OVL_MENU_APP words in place, no cave. Each builder's gate block keeps the flag in a1 (sllv uses
  only the low 5 bits, so the andi goes) and ends `addiu a2,a1,-LO; sltiu a2,a2,N; sltu a2,a2,OVR; movn a0,1,a2` →
  the override no longer applies to music flags 1263..1270 (the mod's reserved block), Jukebox character flag 925
  (Sora) and voice-row flag 888 (Encounter Voice - Sora); every other row exactly as vanilla. Guards: each function
  hashes to the clean overlay with our block and spot33_jukebox's list-size words normalised; FUN_08a41098 clean;
  all-or-nothing state; clean-dump + PPSSPP-open refusal; re-run "already"; --rollback byte-identical.
- Player Icons / Friend Card: not affected. Museum Player Icons list (FUN_08a39f88: section-4 byte +3 = 0 → always
  listed, owned per uicn) and star (FUN_08a3cb5c), and the Friend Card icon picker (FUN_08a18974) all call
  FUN_088cc3b0 = uicn row +4 flag → rows 413-415 = 1266, 416 = 1267 on test350/351; none reads flag 1372.
- Test disc `dumps/ULUS10566-test351-rr.iso` = copy of test350 (1c18c996…c51d, only read) + spot33_jukeboxgate;
  sha256 2041f7f65a09da0451a759ad69e8e9b5b23d569848f25eb17100c15961f3fe6f; equiv.py vs test350 = OVL_MENU_APP 24
  changed words only. Runtime check steps: notes/release-rr-static-b.md RR-08 (2026-10-19 Jukebox entry).
