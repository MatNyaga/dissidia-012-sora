# Menu art for owner 33 (Sora): party / Labyrinth / story-mode screens

Started 2026-10-16 by the menu-art helper (Claude). Base disc = `dumps/ULUS10566-test275-solo2s.iso`.
Mat's reports on test275: Quick Battle "party" screen shows a friend card instead of Sora's face; Labyrinth menu
shows no face; Untold Tales (story mode) icon looks like Chaos and the next menu's party icon looks like WoL.
Everything below is static analysis (no emulator). Overlay addresses are OVL_MENU_APP.ELF VAs
(file offset = VA − 0x089DD4C0 + 0x54, ISO sector 185056).

Tools used (scratch, not canonical): pack lister (menu pak header: u16 count at +0x0A, u16 id_base at +0x0C,
then {u32 off, u32 size}; see notes/qb-grid-pictures.md), overlay pack-list finder ({i32 type, char *path} pairs).

## Labyrinth (dungeon scene, group 4)

- Packs: list 0x08B41CC4 = menu/menu_pk_dungeon_gim_0.bin (id_base 4096, 45 entries) + EN menu_lpk_dungeon_gim_0.bin
  (4096, 45). Loaded by FUN_08b3cc94 → FUN_088d1028(renderer, …, 0xC8000, group 4, list).
- Party face icons = `wm_<key>` GIMs, 64×32 index8, pk entries 8..39 (ids 0x1008..0x1027), alphabetical order
  (one100, one200, two100, …, for100, for110, for200, …).
- **Owner table 0x08B4173C**, 6-byte rows indexed by OWNER (row 0 = none): `u16 wm icon texture id, u16 a, i16 b`.
  Owner 1 = (0x1008, 4, 1), Cloud 13 = (0x1016, 0xC, 0x13), owner 32 = (0x1027, 0x13, 0x55).
  **Owner 33 row (0x08B41802) = (0, 0, −1)**: zero padding → texture id 0 → no face drawn. That is the bug.
- Users: party face draw FUN_08b3b980.. (0x08B3BA20: row = owner*6, the row's first u16 is passed as the 4th argument of 0x0892bacc with group 4,
  sprite part 0x1208); second loop at 0x08B414E4 reads fields +2 (u16) and +4 (i16) into 0x08B43024 / 0x08B43048
  (meaning not traced; not art).
- All ids 4096..4140 are used by one of the two packs → no free id inside the range. Nothing else in the overlay uses
  0x102D as an immediate. Fix: append Sora's wm icon to menu_pk_dungeon_gim_0 at entry 45 = **id 0x102D (4141)**
  and set owner-33 row field 0 = 0x102D. Fields +2/+4 left as they are.

## "Party" screens: one shared party module that uses OWNER − 1 (Quick Battle party + An Untold Tale)

"Untold Tales" = story mode entry **"An Untold Tale"** (text/EN/mess_pk_story_mode_0.bin group 2 #2: "Travel the
world with a party of your choosing"; "Select members to join your party. Members can be used as Assist
Characters."). Message packs decode with spot33_desc's rule (u16 offsets ×2, KEY[(2·id+18+j)%32]).

Several scenes carry the same five per-character picture runs (32 pictures each, picture order = owner − 1) and a
config with five u16 bases (grid icon 32×64, face_in_name 128×32, face_in_name_r 128×32, name 128×32, logo 128×64):

| scene (group) | bases grid / face / face_r / name / logo | set at |
|---|---|---|
| free battle / Quick Battle (0x1D) | 0x702F / 0x70B2 / 0x70D2 / 0x704F / 0x706F | FUN_08a9acac (notes/qb-grid-pictures.md) |
| story mode (0x1E) | 0x74AB / 0x744A / 0x746A / 0x742A / 0x748A | 0x08A96C0C.. (FUN_08a96b34) |
| party_setting (0x19) | 0x600F / 0x602F / 0x604F / 0x606F / 0x608F | 0x08B29838.. |
| party_arrange (0x26) | 0x940C / 0 / 0x942C / 0x944C / 0x946C | 0x08B32400.. |

Draw code computes `id = base + owner − 1` → owner 33 = picture 32 = the FIRST picture of the NEXT run:
- party member slots FUN_08b2c330 (grid 0x08B2C538, face_r 0x08B2C598, name 0x08B2C5E8) and the party list
  FUN_08b2aa04 (grid 0x08B2AB58). Quick Battle: grid → 28751 = p_one100_name, face_r → 28914 =
  BattleOptionCastomize_handicap (a 256×64 card-like banner = the "friend card"), name → 28783 = title01.
  Story: name → 0x744A = **p_one100_face_in_name (Warrior of Light)** = "party icon looks like WoL".
- the same slot also plays a per-owner frame from u16 table 0x08B2D168[owner − 1] (31 entries, owners 1..31;
  owner 33 reads the next table → frame 3). Newcomers (owners 23..31) all use frame 14.
- more owner − 1 draws: 0x08AAC364/0x08AAC49C/0x08AACCDC/0x08AACE8C (free-battle party module, bases at obj+0x66C..),
  0x08B2DBA4 (party select, face_r), 0x08B30BE0/0x08B30C24 (face + name, config copied at obj+0x7A0),
  0x08A8D130/0x08A8D184 (story: face_r/name from DAT_08a93b1a/1c = 0x746A/0x742A), level adjust
  0x08B263A0/0x08B26400 (bases 0x8029 face / 0x8009 name from 0x08B27EF0; owner 33 → name = WoL face strip).
  Customization (0x08AE…, 0x08B04…) also uses owner − 1 but its slot 32 is Aerith's old slot, already Sora
  (spot33_qbpics customize_inplace).

**First Untold-Tale menu ("Sora's icon looks like Chaos")**: the member list is the chara-select grid (same row
table 0x08A864D0; Sora sits in Chaos's old row 31 with pic 245 / name 245 / logo 148). In the story scene that asks
for ids 0x74AB+245 etc., which no pack has → (likely; not traced at runtime) the cell keeps the SEQ's default
texture, i.e. the picture that cell was authored with (Chaos). Same for party_setting / party_arrange / Original Quest grids.

Fix plan (spot33_menuart.py): remap owner − 1 = 32 → 245 at every owner − 1 draw above (same 245 the grid row
uses), give each scene Sora's five pictures at base + 245 (logo at base + 148), and point the party-slot frame of
owner 33 at a newcomer's frame (14).

## Done: test278 `dumps/ULUS10566-test278-menuart.iso` (2026-10-16T14:25Z, static only, NOT played)

= copy of test275 (fe2d1066…) + `tools/scripts/spot33_menuart.py` only. sha256
fcd6681f8125ad0238486375ba6b1226ef4713d90216c92483bd4f54d963d370. Re-run = "already" everywhere.
- Code: 13 sites rewritten in place (same length; redundant `andi`/nop slots reused): `t1 = owner−1, 245 if it is
  32` (`addiu/xori 0x20/addiu 245/movz`). Party slots: s6 = owner (246 for 33) for grid/face_r/name, frame row
  index = owner 24's (frame 14) for 33. Every site asserts its original words first.
- Labyrinth: owner-33 row icon id 0 → 0x102D; new wm GIM (template wm_sev100, its cut-corner alpha) at
  menu_pk_dungeon_gim_0[45]. Picture = tools/art/sora_wm.png (`--make-wm`: make_title_art cut-out, crop
  (30,60)-(158,124) → 64×32 profile eye-to-chin, dark backdrop).
- Pictures appended (filler size-0 entries between; existing entries asserted byte-identical; all packs under their
  load buffers): story gim_2 (5: 29982 logo, 29983 name, 30015 face, 30047 face_r, 30112 icon), party_setting gim_1
  (24836/24867/24868/24900/24932), party_arrange gim_1 (38144/38145/38177/38209), original_quest gim_3 (art 25862 =
  approved portrait, logo 25864, icon 25897, name 25929, face_r 26028, face 26063), level_adjust gim_0 (name 33022,
  face 33054). Pixels = Sora's free-battle GIMs (QB ids 28964/29095/29127/28996/28931) decoded and re-encoded into
  each scene's own Cloud template with keep() markers.
- menu/JP/common/chara_face_in_name/p_sev120_face_in_name.gim (common name plate FUN_08b558f0, left side; was
  still Aerith) → Sora's face strip (guard: vanilla sha a5d83c55…).
- Previews: dumps/renders/menuart/*.png (one per new GIM).
- Not covered / open: calendar `%schara%02d.gim` (0x08ACA4C8, index unknown), party slot frame 14 meaning not seen,
  Labyrinth row fields +2/+4 still (0, −1). build_sora.sh not changed (step would go after spot33_portrait).

## Museum > Character Files (2026-10-16T17:39Z) — test299 `dumps/ULUS10566-test299-museum.iso`

**Cause.** The list is data in package file `collection_param.bin` (no code table): header u16 2, u16 9 sections,
9 u16 counts, 9 u16 byte sizes, sections back to back, then 9×64-byte path strings (FUN_08a3be70 sets the section
pointers; FUN_08a3c110 = character record by index). Section 0 = 34 records × 48 B:
+0 list-name / +2 name / +4 subtitle / +6 profile text ids (text/EN/mess_pk_collection_0.bin group 1; id k = entry
k+1; entry 1 has offset 0 = "no string"), +8 unlock flag bit (DAT_089d726c, 0xFFFF = always), +10 "viewed" flag bit
(3651..3685, 3681 unused), +12..+18 objentry ids for "View Character" (1P/2P/3P/manikin, −1 none; Cloud 0/49/552/224),
+20/+22 DLC costume objentry ids, +24..+28 viewer numbers (Shantotto 230/100/45 = small), +30 −1, +32 char[16]
picture name → `menu/JP/character_select/chara2/<name>.gim` (string 1 of the path block). The list builder
(FUN_08a2fff0.., list at obj+0x550, 80 slots) shows every record whose unlock flag is set. Owner 33 has no record →
no entry, no picture. (Records screen = separate hard-coded owner list 0x08A40880 + appended owners; Player Icons =
section 4, 413 user_icon entries — neither changed.)

**Fix** `tools/scripts/spot33_museum.py` (guarded, --dry, re-runnable; VIEWER=0 = no viewer): record 34 appended
(texts 137..140, flag 0xFFFF, viewed flag 3681, models objentry 1187/1436/1437 = P_SEV120_1P/2P/3P, −1 manikin,
camera = Tidus 370/210/72, picture p_sev120_1p = Sora's portrait already on the disc); group 1 gets "Sora", "Sora",
"　", profile (30 chars/line, KH2 section header with the game's colour escape). All other records / text entries /
groups byte-identical (asserted). Files grow 48 B / 1024 B (loaded by size).
Risk: the viewer loads Sora's 2,499,028-byte gmo; the viewer call passes 0x270800 (2,557,952) → fits by ~58 KB.
If View Character crashes, rebuild with VIEWER=0.
- **Mat on test301 (2026-10-16T17:47:40Z): Museum entry + 3D viewer work well (USER-VERIFIED). Picture must be the approved select-screen portrait, not the older one.**

Mat on test301 (2026-10-16): Museum entry + 3D viewer work ✅ (USER-VERIFIED); list picture was the OLD art.

## test302 `dumps/ULUS10566-test302-icons.iso` (2026-10-16T17:49Z, static only) = test301 + spot33_museum.py extended
sha256 415bc4a8c6ebd509eecca918f19e0a9fac34e6dbe53d335d8cacc3e098714557. Re-run = "already" everywhere.
- **Character Files picture**: menu/JP/character_select/chara2/p_sev120_1p.gim (read by Character Files via the
  record name, and by arcade mode FUN_089ea4d0 `menu/JP/character_select/chara2/p_%s_1p.gim`; both should show the
  select portrait) re-encoded from tools/art/approved/qb_art.png (sha guard) with keep(Cloud's p_sev100_1p) + put.
  Cause of the old art: build_sora.sh's spot33_faces writes tools/art/qb_art.png there, which make_title_art had
  regenerated; museum runs later and now overwrites it.
- **Player Icon No. 414 "Sora"**. Data path found:
  - icon list = collection_param section 4 (8-byte rows: s16 series text id in collection group 0 (132 = FF I …
    193 = DISSIDIA), 0, format text 128 "No. n: name (series)" / 130 "No. n: name", −1; byte +3 = 0 → always listed,
    owned state from FUN_088cc3b0(i));
  - icon names = collection text group 4 entry i (413 entries);
  - ownership = system.bin chunk "uicn" (u16 1, u16 count 413, rows u16 index, icon no., unlock flag bit, viewed
    flag 2580+i); EBOOT FUN_088cc1d0 copies it into a 0xD24 buffer (room for 420 rows); flag 1 = owned from start
    (icons 1-6, 412, 413);
  - pictures: menu/JP/Collection/user_icon/user_icon%03d.gim (Museum) and friend cards from
    general_archive/menu/user_icon%02d.bin (MPK, 32 icons each, member name user_iconNNN.gim; #12 = 385..413).
  Added: user_icon414.gim (64x64 index8 from template 413; approved VS face p_sev120_1p 52x52 on white at (1,1) like
  the character icons), the same GIM as member user_icon414.gim of user_icon12.bin, section-4 row (212, 0, 128, −1),
  text group 0 #212 "KINGDOM HEARTS II", group 4 #413 "Sora", uicn row (413, 414, flag 1, viewed 2993 (unused)).
  Not added to the PP Catalog: it is owned from the start instead.
- **Records**: the record array holds exactly 32 (obj+0x4B8, 0x10C each, then the sort list at +0x2638) → no
  33rd slot without moving data. Chaos (owner 23) has no Quick Battle row in this mod (row 31 = Sora), so the last
  hard-coded append at 0x08A3D8F4: its owner constant 0x17 → 0x21 (same size, guarded). Records icon id table
  0x08A40720[owner] (owner 33 word 0x08A407A4 = alignment padding 0, no xrefs) → 0x4060 = new entry 96 of
  menu_pk_collection_gim_0 (Sora's VS face in Cloud's 64x64 template). Stats come from save arrays indexed by owner
  (+0x3B7A4 arrays have 35 slots → owner 33 inside).
- Previews: dumps/renders/menuart/museum_portrait_p_sev120_1p.png, user_icon414.png, records_icon_0x4060.png.

## Aerith leftovers audit (Mat, test321: Shop showed Aerith) — test325 `dumps/ULUS10566-test325-shopart.iso` (2026-10-17T01:10Z, sha256 0cf10f5d…5090, static only)

Method (static): every menu pack named in the menu overlay pack lists + EBOOT strings (136 packs, EN lpk) and the
packs nested in general_archive/field/menu.bin, field/EN/menu_lang.bin, main/main.bin, main/EN/main_lang.bin were
scanned for GIMs named *sev120* (Aerith's key = owner 33's key) that are still byte-identical to the vanilla ISO;
every loose path pattern from the EBOOT/overlay strings (story_mode/chara2, p_zako_, common face strips + name,
encount, battle/chara_image P_SEV120_1P/2P/3P(+_A/_PUB…), arcade_last, character_select/chara2, party command
pictures) was checked for a vanilla sev120 file; all EN mess packs searched for "Aerith".
Found (all vanilla Aerith, in owner−1 = 32 slots, same layout as Customization):
- menu_pk_shop_gim_0 entry 68 p_sev120_face_in_name (id 7236) and entry 101 p_sev120_1p 32×64 icon (id 7269) = the Shop
  picture → Sora's Customization face strip / icon (customize entries 74 / 107, made from qb_custface / qb_icon).
- menu_pk_level_adjust_gim_0 entry 73 (id 32841) face strip → same (Level Adjust already draws id 33054 since
  test278's remap; replaced anyway).
Clean: Customization, exmode, every loose sev120 file, Labyrinth (own wm icon), arcade, VS/loading/HUD,
Collection. Calendar `%schara%02d.gim` = month pictures (index = byte obj+0xBF4, 1..10), not owner-based. Text:
"Aerith" only as Player Icon No. 248's name (a real FF7 icon), not an owner-33 leftover.
Fix: spot33_menuart.py step 5 (AERITH table; vanilla-sha or ours guard; in place, same size; previews
dumps/renders/menuart/aerith_fix_*.png). Rescan after: 0 vanilla sev120 entries left.

## Artifacts + □ crash (Mat, test330) — test332 `dumps/ULUS10566-test332-artifacts.iso` (2026-10-17, static only)

= copy of test330 (29be9f3f…) + NEW `tools/scripts/spot33_charpanel.py` only (build_sora.sh: after spot33_menuart).
sha256 8b8f0c25c3d13a928dadc98694e1e30e6eb640cac159dfb2d60816aca61ff7a0. Re-run = "already" everywhere.

**Screen.** Communications Mode → Artifacts (start-menu text 8; artifact = online-battle item). Its button bar is
network text g1: id 9 "△ Sell", id 10 "□ Characters". □ opens the shared **"Characters" panel** = faces of every
listed character, lit if the item's equip mask has their bit. The same panel is □ in **Customization equipment**
(customize_common g0 #10) and the **Shop** (shop g2 #13): one code path, three scenes.
- Artifacts module = network scene (DAT_08a23ff0, group 9), obj *(m+0x28f0): FUN_08a25730 fills the panel struct at
  +0x249c (+4 sprite array = obj+0x400, +0x14 base 0x62, +0xfc item mask from FUN_088c1998), FUN_08a25864 →
  **FUN_08aff218**; Customization FUN_08ae7d38 (+0x963c, base 0x81, group 5); Shop FUN_08b0bdc8 (+0x1f6cc, base 0xbf,
  group 8).
- FUN_08aff218 (menu overlay): s3 = unlocked mask (FUN_088d5ce8), s2 = item mask; walks owner list **0x08B0119C**
  (test 14's `select-swap 32 33` replaced 32 = Feral Chaos with 33); per owner s4: if unlocked bit (s4−1)&31 → anim
  0/1 (item bit) on sprite **array[base + s4 + 1]**, store s4 at +0x1c[n] and cell slot (table 0x08B0121C) at
  +0xa8[n]; else hide that sprite. FUN_08af9880 then positions sprite base + owner + 1 at its cell.
- Sprites come from per-scene tables (elem, part) → parts (seq, texture): owners 1..32 only. Artifacts: elem 0x63+k
  → part 21+k = (seq 8756, texture 8208+k), menu_pk_network_gim_0 entries 17..48 = 32×64 icons (byte-identical to
  the shop's). **Owner 33 → sprite 0x84 never created → NULL → FUN_088d9f5c → FUN_088d9a94 reads the anim table of
  NULL** (crash regs: s4 = 33 owner, s5 = 30 list index, s3 = 0xffbfffff unlocked mask, a0 = 0). Customization
  (0xa3) and the Shop (0xe1; only an unrelated part-69 sprite in one optional layout) have no owner-33 sprite either
  → their □ panels would crash the same way.

**Fix** (owner 32 is not in the list any more, so its sprite is free):
- Code, FUN_08aff218, 5 words in place (new words are ours): 0x08AFF2EC (an empty delay slot) → `sltiu t9,s4,0x21`;
  0x08AFF310 (an empty delay slot) → `addu t9,t9,s4` (t9 = sprite owner + 1, 33 for Sora; both are delay slots
  executed on every path); 0x08AFF318 (a redundant constant load) → `addiu s4,t9,-1` (after the item-bit test, so bits
  stay owner 33 = bit 0; the stored owner for FUN_08af9880 becomes 32); hide path 0x08AFF388: the row index now uses
  t9 instead of the owner (`addu a0,a0,t9`), 0x08AFF398: the load offset 4 → 0 (`lw a0,0(a0)`). Owners 1..32:
  identical behaviour.
- Owner 32's face part now shows Sora's icon: Customization parts 0x08AEB130 (loaded from part 6) part 57 texture
  3178 → 3179 (customize pk entry 107 = Sora); Shop parts 0x08B1B5B8 part 68: 7268 → 7269 (shop pk entry 101 = Sora,
  test325); Artifacts parts 0x08A23538 part 53: 8240 → **8321 = new entry 129 of menu_pk_network_gim_0** (copy of
  customize entry 107; no free id in the network packs: pk + lpk cover 8192..8320). Each part is used only by
  owner 32's sprite. Network pk 542,512 → 545,872 B (buffer 0x100000), moved to the ISO end by pkg_put.
- Side effects checked: the network scene's dynamic user-icon ids start at max gim id + 1 (+0xd98, read by both
  the register and draw code) → shift by one, consistent; texture pool 730 nodes vs ~593 used.
- Known limits: Feral Chaos (32) is still missing from the panel (since test 14; a 32nd cell needs new layout
  rows); Sora's light uses bit 0 (WoL's), so Sora-only items 678-681 also light WoL here (cosmetic).
