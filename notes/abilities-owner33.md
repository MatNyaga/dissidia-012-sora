# Giving #33 (Sora) ~20 abilities that work in Customization → Abilities

Research from 2026-10-14. Static only: EBOOT decompile (dumps/decomp/all.c, plus the EBOOT part of menu_all.c),
menu overlay, and the data in dumps/ULUS10566-test108-lines.iso. Nothing here has been run in game.

## 1. What makes an ability show up, and how it is saved

**The Customization → Abilities list** is built by menu FUN_08ad6698 (menu_all.c ~437840). It walks **every ablt
row in table order** and adds a row when both of these hold:
- row **+27 (user byte) == the record's owner**, or +27 == 0xFF (general abilities), and
- the ability id is in the fighter's **learned list** (FUN_088b8414).

Each added row goes into 9 lists (FUN_08ace01c / FUN_08acde24), each capped at **150 entries** (0x4B0 / 8):
- +22 type 0 = Bravery → list 0, or list 1 if +23 == 1 (air)
- type 1 = HP → list 2 / 3
- types 2–4 = general/support → lists 4–6
- list 8 = all

Rows whose +8 (alias) equals the ability's id are listed with it (FUN_088b9da8).
**On-screen order = ablt row order**, so insert #33's rows in the order you want them shown.

amas only adds a marker flag: FUN_08ad0d48 returns 0x10/0x20 when the ability is a mastery prerequisite. It is not
needed for listing, but the owner must have an amas row, or the menu loops forever (already fixed by spot33_amas).

**Fighter save record** (0x778 bytes; #33's record lives at blob + 0x38090):

| offset | what |
|---|---|
| +0 | owner |
| +1 | level |
| +4 | EXP |
| +0x10 | 5 loadout sets × 0xC6 |
| +0x3EE | **learned list: 150 × 6 bytes** — u16 ability id (−1 = end), u16 AP so far, u16 flags (bit1 = mastered, bit0 = "new" marker; FUN_088cbbb4 clears bit0) |
| +0x762 | owner copy |
| +0x773 | current set |
| +0x775 | accessory-slot count (capped at 10) |

- Mastery: AP is added by FUN_088b7f58, capped at row **+18**; reaching it sets the mastered bit.
- Battle copies 900 bytes = 150 learned entries (FUN_08935524 at all.c:479147). **Cap: 150 learned abilities per
  owner, general ones included.** A Lv100 #33 now has about 57 (chrl general) + 38 (amas general) + 4 own ≈ 99,
  so roughly 50 more fit.

**One loadout set (0xC6 bytes):**
- 3 stance groups × 30 bytes. Row +30 is a stance bitmask (7 = all three; 1/2/4 for stance fighters).
- Inside a group, as Cloud's eqpm presets show:
  - Bravery ground: 3 × [attack, link, link, link] (4 bytes each)
  - Bravery air: 3 × 4 bytes
  - HP ground: 3 bytes
  - HP air: 3 bytes

  Bytes are u8 ability indexes; 0xFF = empty; id = owner byte (+0xB6) << 8 | idx.
- Hard caps: **3 attacks per category per stance**; linked HP follow-ups go in the link bytes.
- +0x5A: 64 general-ability bytes (id 0x4000 | idx).
- +0x9A: 4 × u16; +0xA2: 10 × u16 (accessories).
- +0xB6: owner.

**Battle:** FUN_08ab7f40 enables matching fighter comb entries in a 256-bit field (8 words), so the fighter's
comb/action table can have at most 256 entries. #33's comb has 19 entries now. Every new ablt +12 action id must
exist as an entry id (or alt id) in obj/p_sev120.objx comb, or the slot does nothing.

**How abilities get learned** (all via FUN_088b7ed4):
- (a) **chrl** level table, applied by FUN_088cbd24(record, old_level, new_level) on level-up. It collects at most
  **80 ids** per call (FUN_088b6f48).
- (b) The default eqpm preset (#33 = 250) when the record is created (FUN_088cbbb4).
- (c) amas "learn X by mastering Y" chains.

Cloud's 17 own abilities come from: 6 in his preset (0,2,7,8,10,13), 9 from chrl, and 2 from amas (0x0D0C, 0x0D0E).
chrl rows: u8 level, u8 bonus (+0x775), 3 × u16 ids (0xFFFF = free). #33's chrl row has 52 levels and **99 free id
slots**, so new ids fit without growing the chunk.

**The catch:** an existing #33 record (already Lv9/Lv100) will not pick up chrl entries for levels it has already
passed. Fix: in spot33_save's owner-33 branch of FUN_088cb164, call **FUN_088cbd24(rec, 1, rec[1])** every time.
- It learns everything for levels 2..current and is idempotent.
- Starting from level 1 skips the level-1 row, which is the only one with a bonus byte, so +0x775 never grows.
- Put Sora's new ids at levels ≥ 2.
- Alternative: one-time reset of the record (the code re-inits when rec[0] != 33).

## 2. Is adding ablt rows enough?

**Needed:**
1. **ablt rows.** Insert them **sorted** (binary search by u16 id = owner<<8 | idx): after row 620 (0x2103) and
   before row 621 (owner 34, 0x2200), as ids 0x2104… Set +1 and +27 both to 33, and bump the count at header +8.
   - Runtime buffer FUN_088b1cc0 = 16 + **0x328 (808) rows**, fixed, so **18 more rows max** (790 → 808).
   - More than 808 overflows: memcpy of the whole chunk into the fixed block.
   - To allow more, patch EBOOT **0x088B1CF0** (the row-count constant 0x328 = 808), file offset 0xAECC8 in the ELF,
     ISO 0x1C6CC8, e.g. to 0x340 for 832 rows (+960 B heap).
   - main.bin load buffer is 0x180000 (now 1,219,328 B), so it is fine.
2. **Learned list:** via chrl (and/or the preset or amas), see above. Without it the row is invisible and unusable
   (test 15).
3. **Comb entries** in p_sev120.objx for each +12 action.
4. **Text** (section 4).

**Optional:**
- eqpm preset 250 (initial equips; edit in place, the buffer has no room to grow).
- amas entries (u16 new, u16 1, u16 prereq, u16 0xFFFF; grows amas, whose buffer is exact-size, so that is fine).

**Fixed caps:**
- ablt 808 rows
- 150 learned per owner
- 150 per menu list
- 3 per equip category per stance
- 80 ids per chrl collection
- idx must be ≤ 0xFE
- 256 comb entries

No 32/64-bit per-owner ability bitfields were found.

## 3. ablt row fields (40 bytes; checked against all 622 fighter rows and Cloud's 17)

| off | meaning |
|---|---|
| +0 u8 | idx (low byte of id) |
| +1 u8 | owner |
| +2 u16 | name text id |
| +4 u16 | description text id |
| +6 s16 | **parent ability id** for linked HP follow-ups (equipped in the parent's link bytes, FUN_088b7698). Cloud: 0x0D0C → parent 0x0D01, 0x0D0E → parent 0x0D07. 100 rows use it; −1 otherwise. |
| +8 s16 | **alias**: shares the learned entry of that id (FUN_088b9e28); −1 normally |
| +10 s16 | exclusivity group (same +27 and +10 = only one, FUN_088b5254); −1 normally |
| +12 u16 | action id (switches on matching comb entries) |
| +14 u16 | **CP cost** (30) |
| +16 u16 | **CP cost once mastered** (15) |
| +18 u16 | **AP to master** (Cloud 80–220) |
| +20 u16 | 0xFFFF in 608 rows (unknown; keep 0xFFFF) |
| +22 u8 | type: 0 Bravery, 1 HP (2–4 = general categories) |
| +23 u8 | 0 ground, 1 air, 0xFF = linked follow-up (uses the parent's) |
| +24..26 | always 00 03 00 |
| +27 u8 | user/owner (0xFF = general) |
| +28..29 | 0 |
| +30 u16 | stance mask (7) |
| +32..39 | 8 CPU-preference bytes (mostly 0; 39 rows 00 00 01 01 01 00 00 00) |

## 4. ability.bin text: why "add" garbled it, and the room for strings

**Real format:**
- u16 N (count; read as a signed short)
- **N** u16 offsets at u16 positions 1..N (in 2-byte units)
- data from position N+1
- game text id k = position k+1. Entries are u16 byte length + text XOR'd per entry (FUN_0887a6a0).
- The loader copies the exact size from the MPK into the heap (FUN_0887ac70) and decodes **every** entry in place.

**The bug:** ability_text.py `add_texts` treats position 0 as an offset. It leaves the old last offset (position N)
in place as "data", so after the insert the game reads one extra offset at position N+k. That offset is unshifted
and points into the text near the old end, and the in-place decode XORs that region a second time, which is the
garbling. (The original last entry, id 1306, is lost too.)

**The fix:**
- Rewrite `add` to shift all N offsets (positions 1..N) by k.
- Write the new offsets at positions N+1..N+k, with key index = position.
- Set u16[0] = N+k.

With that, growing is safe up to the u16-offset limit (ability.bin ≤ 128 KB; it is 41 KB now). The main_lang.bin load
buffer is 0x80000 (now 397,872 B, so about 126 KB of room).

**Simpler option: reuse placeholders.** 380 text ids are not referenced by any ablt row; **315 are dev
placeholders** ("Gabra12", "Sephiroth07", "Kuja03", …). 392–399 are already used by #33. Ranges of placeholders
with 9 or more in a row:
- 1041–1053
- 1083–1095
- 1125–1137
- 1166–1178
- 1189–1199
- 1212–1221
- 1249–1263
- 1274–1284
- 1297–1305

That is more than enough for 40 strings. Use `ability_text.py set` (longer texts are appended in place; no new
entries, so no header change). Before relying on them, check that no other chunk points at those ids (only ablt
was checked).

## Recipe (≈18 new moves, idx 4..21)

1. Build the new actions in p_sev120.objx comb (one entry per action id).
2. Text: `ability_text.py set` on about 36 placeholder ids (names + descriptions).
3. ablt: insert 18 rows (ids 0x2104–0x2115) between rows 620 and 621. Copy the closest Cloud row and set:
   - +0, +1/+27 = 33, +2/+4, +12
   - +22/+23 (type and ground/air)
   - +6 = parent for any Brv→HP link (+23 = 0xFF)
   - CP/AP as Cloud's (30/15, 80–150)

   Count 790 → 808.
4. chrl: drop the new ids into #33's free slots at levels 2..~60 (no size change).
5. EBOOT: in the #33 branch of FUN_088cb164 add `FUN_088cbd24(rec, 1, rec[1])`, so existing saves learn them.
6. Optional: eqpm preset 250 in place (best starting kit); amas chains for "master X → learn Y".
7. Re-run spot33_amas / spot33_save as usual (they are idempotent) and test. In Customization, check the lists, the
   CP costs, equip/unequip, mastery, and that each move fires in battle.

## Built (test 112 `dumps/ULUS10566-test112-moves.iso`, 2026-10-14)
`tools/scripts/spot33_moves.py ISO` (MOVES table): ablt row per move (Cloud row as template, +0 idx, +1/+27 owner,
+2/+4 text ids, +12 action, +22/+23), text into placeholder entries 1042+ ("Kefka57"… → game ids 1041+), chrl learn
level (if no row for that level, the next higher row with a free slot is moved down to it). Reads main.bin via the
package table (ablt_patch.py `list` reads the ORIGINAL ISO offset — stale since main.bin moved!).
First move: idx 4 "Slide Dash" (ground Brv, action 316 = [LAND_MIDDLE1], learned at Lv11; Mat's #33 is Lv10).
No EBOOT change (no safe code cave found for FUN_088cbd24 on every record fetch) → moves come by levelling.
- Test 113: chain abilities (Brv→HP, +6 parent, +23 0xFF): idx5 Combo Plus > Spin Finish (action 315), idx6 Air Combo Plus > Aerial Flurry (323), idx7 Slide Dash > Spin Finish (313), learned Lv12; base combos have no Square links now; Slide Dash ◯ → ground combo. Base names: Combo Plus / Air Combo Plus. Mat (112): Slide Dash learned at level-up, equippable, works.
- Test 114: Slide Dash hits (LAND_MIDDLE1, LAND_MIDDLE1_2) get light reactions (Mat: knocked too far for ◯ follow-up).
- Fast levelling for tests: #33's record = *(0x089D712C) + 0x38F98 (+0 owner 33, +1 level, +4 u32 EXP towards
  the next level). Writing a big value at +4 (500000) then winning a battle → multi-level-up through the normal
  path (chrl abilities learned). Done live 2026-10-14 on Mat's save.

## Where the ability DESCRIPTION comes from (test113 follow-up, 2026-10-14)

**ablt +4 is the description index. It does not index ability.bin.** It indexes **group 0 of
`text/EN/mess_pk_customize_ability_0.bin`** (281,840 B; the code asks for text/JP/…, which is swapped for EN).

Code path:
- Customization loads the pack: FUN_08af7aec → FUN_0887b260(pack, "text/JP/mess_pk_customize_ability_0.bin"), stored
  at menu+0x140+0x8A0.
- The info panel (menu_all.c ~436235) shows `FUN_08af3a70(menu, group 0, row +4)` → FUN_0887b500(pack, 0, index).
- If the row has a parent (+6 ≠ −1), the panel first adds the parent's NAME (ability.bin, row +2 of the parent)
  plus common string 0x3D, then a newline.

Checks:
- Cloud: +4 = 625 → "[Close] Quick slash.\nLow power, fast execution.\n…".
- #33 idx 0: +4 = 395 → "WOL 15", which is what Mat sees.
- #33 idx 4–7: +4 = 1042/1044/1046/1048 → "Ultimecia 59/61/63/65".

### File format

**mess pak:**
- "mess pak", u16 1, u16 group count (2), u32 0
- per group: u32 offset, u32 size
- group 0 at 0x20 (128,302 B); group 1 at 0x1F550 (an "OFF4" table, 32-bit offsets)

**Group 0** is the same plain text table as ability.bin, and the same table layout as ability.bin's real one:
- u16 N (1221)
- N u16 offsets in 2-byte units, at u16 positions 1..N
- data after that
- index k = position k+1
- each entry is u16 byte length + UTF-16LE text with NUL, byte j XOR `KEY[(2*(k+1) + 18 + j) % 32]`
  (KEY from voice_text.py). This is the same key rule as ability_text.py, with the position = index + 1.

Decoder: scratchpad txt.py logic, i.e. ability_text.py with the corrected header.

The loader (FUN_0887b260) reads the whole file into an exact-size heap block and **decodes every entry in place**
(FUN_0887a6a0). So:
1. no two entries may share bytes, and
2. the header count must match the table exactly.

Formatting codes inside descriptions: `\n` is a line break. The coloured last line is
`\x10` `Ł` `ａ` … text … `\x1b` (for example "\x10ŁａAdditional Effect: chase\x1b"). Copy those bytes from Cloud's
entries.

### Room

- Group 0 has 542 entries that no ablt +4 points at; **397 are dev placeholders** ("Bartz 12", "WOL 15", "Ultimecia 59",
  … 10–24 bytes each).
- Runs of 9 or more: 215–227, 234–244, 411–419, 430–442, 451–459, 516–524, 531–541, 549–562, 570–579, 594–604,
  613–621, 669–680, 692–702, 713–721, 787–797, 804–814, 826–838, 845–855, 863–879, 945–953, 986–995, 1066–1074,
  1082–1091, 1102–1116, 1123–1133, 1165–1175, 1189–1199, 1212–1220.
- 95 more unreferenced entries are real, unused descriptions of 90–202 B (cut moves).
- **Size limit:** offsets are u16 × 2, so group 0 must stay ≤ 131,070 B. It is 128,302 now, leaving **2,768 B**.
  A typical description is about 164 B, so only ~16 can be appended as-is.

### Recipe for #33 idx 0..21

1. Pick 22 description indexes. Keep 395–398 and 1042/1044/1046/1048 (already in #33's rows; all placeholders).
   Add 14 more placeholders, e.g. 1066–1074 + 1082–1086. Write them into ablt +4 of rows idx 8–21.
2. Re-encode group 0 completely; don't patch in place.
   - Decode all 1221 entries.
   - Replace the chosen ones with Sora's texts (copy Cloud's style: "[Close] …\n…\n\x10ŁａAdditional Effect: …\x1b").
   - To stay under 131,070 B, set about 60 other unused placeholders (not any ablt +4 value) to "" (just the NUL).
     That saves ~1 KB+. Or reuse the long unused real descriptions in place.
   - Write N, the offsets (positions 1..N), and each entry 2-byte aligned and XOR'd with its own index's key.
3. Rebuild the mess pak: header + group 0 at 0x20 + pad to 16 + group 1 unchanged. Update both (offset, size)
   pairs. Then `pkg_put.py ISO text/EN/mess_pk_customize_ability_0.bin NEW`. The heap block is exact-size, so a
   slightly bigger file is fine.
4. Names are separate: ablt +2 → ability.bin (general_archive/main/EN/main_lang.bin), as before.
5. Fix ability_text.py's header model (N, then offsets at 1..N) and reuse it for both files.

**Not needed for descriptions:** group 1 (OFF4) is read via FUN_08ad113c(ability id), which uses another 40-byte
table at DAT_09b6cd94 (probably the command-list/tips screen). Check it only if #33's command list shows garbage.

### Done: `tools/scripts/spot33_desc.py ISO` (test 115, 2026-10-14; build_sora.sh step after spot33_moves)
- Own encoder for group 0 (u16 N, offsets at 1..N, entries 2-aligned); re-encoding the stock group gives the exact bytes.
- DESC table = description id → text (ids 395–398, 1042/1044/1046/1048 now). Entry list index = id.
- Same size on purpose (a grown table garbled in RAM before): unused "Name NN" fillers (no ablt +4 points at them)
  are emptied from the end until it fits, then zero-padded to the old size. 8 texts cost 39 fillers.
  File stays 281,840 B and is written in place. Rerun-safe.
- ✅ Checked in game (Claude, test 115): all 8 show, chain ones under "Branching from …" (dumps/screens/t115menu/d_all.png).

### Confirmed (Mat, 2026-10-14, test 113)
After a normal level-up 11→12 the chain abilities idx 5–7 (Lv12 in chrl) appear in the lists. So rows + chrl are
right; RAM pokes of the learned list just don't stick. New moves = pick a learn level above the save's level.

### Combo links come from the STARTING action (test 117/118, 2026-10-14, ppcombo log)
Slide Dash action 316 = [0x5c1, N2]: Slide Dash → N2 worked, then the chain STOPPED, although action 1020 has
N2 → N1_2. Normal N1 → N2 → N1_2 … goes on. ⇒ follow-ups are looked up in the action that started the chain (plus
chain abilities whose +6 parent is that ability), not in every equipped action. Fix: 316 = [0x5c1] + GROUND[1:]
(spot33_combos.py). Test 118: 10010 → 10001 → 10007 → 10002 → 10050 → 10011 → 10224 → 10021 → 10022 → 10060 → 10061.
Every new starter move needs its own full follow-up list.

### Own ground-chain finisher: Finishing Leap (test 119, 2026-10-14) ✅
Mat: both long combos ended with the same finisher. Now GROUND ends with piece 0x5c3 (LAND_MIDDLE3, unused) whose
plya +0x1c motion id → 10094 = block 64 = GMO slot _704C (unused by #33; spot33_combos MOTION). Block 64 = COPY of
block 53 (AIR_MIDDLE1 events: hits 20-60 + 66-72, end 92; spot33_chain COPY). Animation KH2 668 (Finishing Leap)
via `_704C=atk:668:40,69:mslot=_630A` (Keyblade matched to Cloud's ORIGINAL _630A swing, because the hitbox follows
the weapon and the copied block's hits are _630A's; kh2_attack MATCH_SLOT/MATCH_MODEL).
ppcombo log: … 10060 → 10061 → **10094** → Lightning 550/700 (blown away); air chain … → **10030** (Aerial Finish).
Recipe for any new move with its own animation: unused piece + unused block (free: _701A 59, _702A 60, _705A 65,
_706B 67, _707A 68) + COPY of a template block + atk:KH2:hits:mslot=TEMPLATE_SLOT.

### KH2 finishers on Square: Explosion + Magnet Burst (test 120, 2026-10-14, Mat: "multiple finishers … use a number")
- New atkp hits (spot33_combos NEW_HITS, appended, ids > 0xff0): 0x1000 EXPLOSION (copy of LAND_FINISH1_3, HP blow
  away), 0x1001 MAGNET_BURST (copy of AIR_FINISH2_3).
- Explosion: piece 0x5c9 LAND_FINISH2 (Meteorain, role → 1, min dist 7 → 0, reach 6, height ±6), motion 10095 =
  block 65 _705A ← COPY of Cross-slash block 58 with last hit 0x367 → 0x1000 and every frame × 0.5 (SCALE):
  hits 19-22, 38-41, 58-61, end 81. Animation KH2 664 `atk:664:21,59:end=41` (no match).
- Magnet Burst: piece 0xb32 HP_A_METEO1 (role → 1, flags 0x10013, min 0, reach 7, height ±10), motion 10098 =
  block 68 _707A ← COPY of Braver block 63 with hit 0x36a → 0x1001 (hit 26-44, end 94). `atk:788:35:mslot=_704B:end=47`.
- Chains (ablt idx 9-11, Lv13): 314 "Combo Plus > Explosion" [N12, EXP, N4, EXP] (after hit 3/5), 317 "Slide Dash >
  Explosion" (same), 927 "Air Combo Plus > Magnet Burst" [AN2, MB, R1, MB]. Spin Finish (315, after hit 2/4) and
  Aerial Flurry (323, after AN3/R2) branch at other hits → all can be equipped together. 313 Slide Dash > Spin
  Finish now also after hit 2/4: [0x5c1, LF3, N2, LF3, N3, LF3].
- kh2_attack END=frames (build `:end=N`) = new animation length for copied/scaled blocks.

### Explosion → Guard Break (Mat 2026-10-14, test 124)
Mat: KH2 Explosion = the EX002 swing (612) + a MAGIC burst around Sora with area damage (664 was not it). KH2's
effect files exist (kh2_export/raw/kh2_sixth/original/obj/P_EX100.a.us = Sora's attack effects, kh2_fifth/original/
magic/*.mag) but are KH2's own particle format (PAX) → porting = big separate project. Mat: "go with Guard Break, will
do explosion later". Same piece/block/hit as before (0x5c9, block 65 _705A, hit 0x1000 now named GUARD_BREAK),
animation KH2 660 (`atk:660:21,59:mslot=_700A:end=41:env=MATCH_AT=20/40/60,MATCH_SCALE=2`): Keyblade matched to
Cloud's Cross-slash at all 3 hits (the copied block runs 2x faster → MATCH_SCALE=2). With 664 + only 2 matched hits
the last blow landed 2/5. Names "Combo Plus > Guard Break" / "Slide Dash > Guard Break".
Slide Dash continue window 42-72 → 34-72 (spot33_speed OP01; Mat: CPU escapes after Slide Dash — log showed a 0.6 s
gap before NEAR2's hit). NOTE spot33_speed SHIFT is NOT rerun-safe (shifts again) — only run on fresh builds.

### New animation slots + fixes (test 126, 2026-10-14; helper research notes/hitbox-shapes.md §8-10)
- **New slots work like this**: GMO motions are type 0x0B blocks at the end of the model block; nothing counts them →
  `gmo_motion.py append` adds `_720A` etc. (motion index 86+). p_se type-8 block index = GMO motion index; type-7 rows
  map motion id → block. spot33_chain.py SLOTS {motion id: (block, template motion)} appends both (ids from 10300).
  build_sora.sh SLOTS="_720A=_630A" appends the GMO motion before the MOTIONS loop. First user: Finishing Leap
  (10300 → block 86 → _720A). Block 64 / 10094 is NOT free: it is Braver's LANDING (AIR_FINISH2 plya +0x10 = 10094);
  10097 (block 67) is AIR_FINISH3's landing.
- **Banner** = plya +0x21 (text entry − 1). Meteorain pieces had 4 → both Guard Break and Magnet Burst said "Ragnarok".
  Now 5 Guard Break, 6 Spin Finish, 8 Aerial Flurry, 11 Magnet Burst (new entry; 0xb32 +0x21 = 10).
- **Stuck after a move**: a slot's animation must last ≥ its script (last one-shot op 0x02 "end motion", op 0x28,
  op 0x0a "stay airborne" end ≤ 2 × last frame). Magnet Burst had end=47 (94) vs op02 102 / op0a 104 → hung in the
  air (Mat). Now `_707A … end=55`; `_720A` keeps the template's 66 frames.
- **One-shot list** (after the main events; header byte 3 = count, u16 +4 = start): SCALE now scales them too
  (Guard Break sounds/shakes/camera at 19/38/57); DROP_MAGI removes Braver's shockwave magi 0x529 from Magnet Burst.

### Combo escapes vs Average CPU (test 126-130, 2026-10-14; POS=1 ppcombo logs distance d / height h per change)
- Settings reset to Average after each PPSSPP start (Mat's settings) → realistic test; CPU Sora broke out around hit
  5 and hit 9. One run still landed all 12 hits + Finishing Leap.
- atkp +0x16/+0x17 (15 on light hits, 50 big, 100 Cross-slash finish): NOT stun — 30 made it WORSE (escape after hit
  2), 6 changed nothing → leave 15 (probably re-hit protection / something else). BR_A_REN1_1 has 0 there.
- Distance grew with every hit (1.1 → 2.5 → 3-4 m at hit 5) because only NEAR1 had op 0x39 (lunge toward the foe,
  params 0.2, 8.0, 0.5, 0, 0). spot33_chain ADVANCE adds it to 10001/10007/10002/10050 → distance stays 1.5-2 m.
- Between hits the CPU often went back to idle (O1) and then blocked (470) / dodged (400). Sora's HURT animations are
  KH2 clips much shorter than Cloud's (500/501 13 vs 30 frames, 550/56x 19 vs 30, 600/601 36 vs 46). If hitstun
  follows the hurt animation, CPU Sora (and Sora in general) recovers 2x too fast. test 130: clips slowed
  (`42@0.43:0-29` …) to Cloud's lengths. Check whether escapes stop.

### Air moveset + air opener speed (test 131, 2026-10-14)
- Base air chain now only KH2 normal air swings: AN1 724, AN2 728, AN3 732 (was 768), R1 736 (was 764 Aerial Sweep),
  R2 724 (was 772 Horizontal Slash), finisher Aerial Finish 776.
- New (Lv14): Aerial Dive (air Brv starter, foe below; piece 0x85c = clone of N4 row, role 0; slot _723A / motion
  10303 / block 89 = copy of N4's block + window 20-50; KH2 768) → action 325 = [DV] + AIR[1:].
  Air Square finishers, one branch each: Magnet Burst after AN2 (927), Aerial Flurry after AN3 (323), Horizontal Slash
  after R1 (318; piece 0x5c4 = clone of AF3 row, slot _721A / 10301 / block 87 = AF3's block ×0.5, KH2 772), Aerial
  Sweep after R2 (319; piece 0x5cd = clone of AF3, slot _722A / 10302 / block 88 = AIR_MIDDLE1 timing with own HP
  hits 0x1002/0x1003, KH2 764). Banners 12 Horizontal Slash, 13 Aerial Sweep (mlng grew 1612 → 1680 B: battlenames
  now rebuilds the ARC when it grows — watch for garbled banners in game).
- plya fields seen: +5 = 2 ground / 1 air / 0 both; +0x0f = 1 Circle / 2 Square; +0x10 = landing motion (AF2 10094,
  AF3 10097); +0x21 = banner. spot33_combos CLONE copies a template row (keeps id + name).
- Air opener AN1 (10020): hits 18/34, next piece only from 42 → AN2 came 0.9 s late, CPU recovered (test 130) →
  SHIFT 10 (`_620A=atk:724:12,28:match=22`).
- Test 130 result (vs Average CPU Sora): with Cloud-length hurt clips, 3/5 full 12-hit ground combos; Guard Break 3/3.

### Test 131/132 results (2026-10-14, vs Average CPU Sora; ppcombo `m10060` = mash Circle until motion, `u…` wait,
`w0.2` pause, SY/OY = height offsets of Sora / the foe)
- Ground combo: 4/4 full 12-hit combos ending in Finishing Leap (blow away) — after the lunge + hurt-length fixes.
- Aerial Dive (10303, SY=5, stick "away" FY=-1): hits 2/3, AN2 follows. Aerial Spiral (10031, OY=5, toward FY=1):
  hits 3/4, AN2 follows (then misses: the teleported foe falls).
- Air finishers only work in AIR-STARTED combos (parent = Air Combo Plus 0x2101): in the ground combo's air part
  Square does nothing (links come from the starting ability's chains). → design question for Mat.
- Magnet Burst / Horizontal Slash land when AN2 connects; Aerial Sweep: 2nd (blow-away) hit at 66-72 came after the
  CPU fell out → test 132: both its hits = own blow-away hit 0x1003. Air opener window 28-62 (test 132): AN1 → AN2 →
  Magnet Burst blow-away 3/5.
- Menu: air Bravery slots are "stick toward foe" / "stick away from foe" (any air Brv ability fits any slot).
- PPSSPP debugger hangs every few tool runs (no fix found; ppcombo now closes its socket and connects with 30 s
  timeout) → restart PPSSPP (go_battle.sh) when a handshake times out.
- Test save (a copy of the 100 % save, Sora Lv14) equipment changed by Claude for tests: Combo Plus > Spin Finish and Slide Dash >
  Spin Finish OFF; Combo Plus > Guard Break, Air Combo > Magnet Burst, Aerial Spiral, Aerial Dive ON.

### AUTHORED blocks (spot33_chain.py AUTHOR, 2026-10-14)
Why: COPY keeps the template's hit pattern (Finishing Leap = copy of Cloud's AIR_MIDDLE1: a 20-60 multi-hit with blue
sparks — Mat: "Onion Knight's finisher"). AUTHOR = {motion: dict(tpl, hits=[(from, to, hit, shape)], end)}: template
plumbing (trails op2a, sounds op11/op03/op15, airborne op0a, cancel op22, free op28, end one-shot op02, facing op02,
expressions op14 …) stretched piecewise-linearly (template first hit → hits[0], last hit end → hits[-1], template end
→ end), template hits dropped, own op00 hits added. Order in spot33_chain: SLOTS → COPY → ADVANCE → AUTHOR → WINDOWS.
Dry run (FL, tpl 10030, one hit 34-40, end 90): op22 40, op28 60, op0a 0-92, end op02 90. ✓ re-runnable.
KH2's own hit windows: tools/scripts/kh2_triggers.py OUT.json IDX… (R entries type 10 = hitbox, params [attack id,
?]; only special moves have them — normal swings don't; type 11 = combo-continue from; F type 1 = effect, type 2 =
sound). e.g. 668: hitbox 34-38; 664: 32-57 + 57-64 (+ 124 area 32-64); 788: 16-56, 64-70, 20-56 (+ area 20-70).

### Test 135 — every KH2 move authored at natural speed (2026-10-14)
Video check (helper, notes/kh2-finishers.md top table, Mat's reference video with chapters): 664 = Explosion
(Keyblade up, slam, light orbs — the swing Mat saw is the combo hit before it), 668 = Finishing Leap, 776 = Aerial
Finish (5 sweeps), 652 = Dodge Slash, 644 = Slapshot, 772 = Horizontal Slash (3 slashes L/R/down), 784 = Aerial Dive,
768 = Aerial Spiral (were swapped), 764 = Aerial Sweep, 788 = Magnet Burst, 660 = Guard Break, 648 = Upper Slash,
656 = Slide Dash, 676 Flash Step, 680 Vicinity Break, 684 Counterguard, 688 Retaliating Slash.
Natural hit moments (tools/scripts/kh2_hits.py, script frames): 772 16/26/38 · 776 26/34/54/74/84 · 668 28/44 ·
664 32/68 · 652 16/34/48/54/60 · 660 4/32 · 788 22/44/62 · 764 10/34 · 768 16/30 · 784 12/26/34/40.
Build: `nat:IDX[,IDX]` = kh2_combo.py NATURAL (no warp, no MATCH, root pinned). AUTHOR specs in spot33_chain.py:
air chain R1/R2 = Horizontal Slash ×2 (6 slashes, Mat), Aerial Finish = new slot 10304 (5 sweeps), Finishing Leap 2
hits, Aerial Spiral 768, Aerial Dive 784, Guard Break 660, Magnet Burst 788, Aerial Sweep 764, HS finisher 772,
ground □ = "Dodge Slash" 652→664 Explosion (slot 10305: 4 flurry hits + plant + AREA hit 0x1005 on body sphere 0x06
+ one-shot op 0x19 effect 5 = Cloud's Firaga burst as stand-in), air □ = Aerial Finish HP (slot 10306, no Braver).
Names: idx2 Firaga → Dodge Slash, banner 4 → Dodge Slash.

### Test 136-138 (2026-10-14): Horizontal Slash reach, Dodge Slash / Explosion split
- Natural-speed KH2 swings + Keyblade spheres (0x30) whiffed (Horizontal Slash, CPU escaped). Shape 0x13 (r 2 at
  2 m) landed but hit beyond the blade (Mat). Now FRONT = 0x32 (≈ r 1.3 at 1.8 m, blade-tip distance) + AUTHOR
  `lunge` (op 0x39 before slashes) + HS_SLASH hit 0x1006 (BR_A_REN1_1 with AIR_FINISH3_1's reaction: push 0.3, keeps
  the foe in place).
- Authored combo pieces need op 0x28 ("free to act") late: at 45 with the window at 40 the presses started a NEW
  combo instead of the finisher (test 135/136 logs) → AUTHOR `free=`.
- Mat: "the move is two moves, dodge slash into explosion. Only the explosion is the HP attack": ground □ = Explosion
  alone (slot 10305 nat:664, plant 30-34 + area 64-74 on body sphere 0x06 + effect 5 one-shot); Dodge Slash = Bravery
  ground starter (piece 0x604 clone of N1, slot 10307 nat:652, 4 hits, lunges) → action 327 = [DS] + GROUND[1:];
  chain "Dodge Slash > Explosion" (action 320 [DS, EX2], EX2 = 0x605 clone of LF1 → same Explosion block). Lv15.
- Screen capture (x11grab) only works while Mat's screen is on; PPSSPP's gpu.buffer.screenshot fails ("Could not
  download output") → visuals need Mat.

### Test 140/141 results (2026-10-14, vs Average CPU Sora) ✅
- Horizontal Slash = ONE piece with 6 slashes (nat:772/0-22,772 — frames 0-22 of the first pass, then a full pass;
  with the full first clip slash 4 came 0.6 s after slash 3 and the CPU air-dodged out). kh2_combo.py NATURAL clips
  accept IDX/A-B. Slashes = HS_SLASH 0x1006 (keeps the foe in place) + lunges. Landed 6,6,6,6,5,5 of 6 (7 starts).
- Finishers: Finishing Leap 2/2 knock away, Aerial Finish (10304, sweeps also HS_SLASH + lunges) 5 sweeps / 3 + knock.
- Explosion (ground □): 5/5 plant hit (600) → area hit knocks away (700/750). Aerial Finish HP (air □): 1 clean (4
  sweeps + 700), 1 partial.
- Combo pieces: AUTHOR drops template op 0x01 windows (WINDOWS adds ours → re-runs give the same result) and op 0x59.
- Dodge Slash (test 141, Lv15, slot "stick AWAY from foe + ◯" on the ground): 4 hits 3/3, flows into the long ground
  combo (… → Horizontal Slash 6 slashes); Square right after Dodge Slash → Explosion 3/3 (600 → 700/704).
- Test save (100 % save copy) now Lv15, equipment changed by Claude: Dodge Slash + Dodge Slash > Explosion ON, Aerial Spiral /
  Aerial Dive OFF, Combo Plus mastered (CP 15).

### Dodges (test 142, 2026-10-14; Mat: "R+X backwards dodges forwards")
Logged: stick back → motion 400 (_100A), stick toward → 460 (_150A, was still CLOUD's animation), sideways → either.
Sora keeps facing the foe, so 400 = KH2 838 (dodge roll) REVERSED = backward roll (`_100A=nat:838/rev`), 460 = 838
forward roll. Dodge blocks have no end ops (animation length = dodge length: 27 frames; Cloud's 460 was 46).
In-game: both play and end (~0.9 s), no hang. Looks need Mat.
- Test 142 back dodge (838 reversed) looked "very off": reversed roll = stand-up first, roll last (recording
  dumps/screens/rec/dodge.mp4, dz_sheet.png). Test 143: 400 _100A = backward hop that opens KH2 Guard Break (660 frames
  0-11, `combo:660/0-11:-` = stretched to the slot's 27 frames). ✅ Mat: "it works".

### Test 144 (2026-10-14, Mat after test 143)
Mat: keep Spin Finish; replace Aerial Flurry with a KH2 move; likes Horizontal Slash / Aerial Finish / Finishing Leap;
"explosion still doesn't have its dodge slash wind up and it's a single strike with orbs surrounding him" (the 2-hit
version: "3 unless the first hit hits").
- Ground □ Explosion (slot 10305) = nat:652,664: Dodge Slash wind-up WITHOUT hits + ONE area strike 146-158 (0x1005,
  body sphere 0x06) + burst effect 5 at 146. Chain "Dodge Slash > Explosion" uses new slot 10308 (nat:664, strike
  62-74) so the spin isn't done twice.
- Air chain AF3 (was Cloud's Omnislash v5 "Aerial Flurry") → Retaliating Slash (KH2 688, slot 10309: HP hits 6-10,
  22-26, 38-44 blow away, lunges), name/desc/banner 8 renamed, landing motion removed (AF3 +0x10 → 0xFFFF).
- Risk: no hits during the 1.4 s wind-up → the foe can walk out before the strike (watch in test).

### Win camera bug (Mat: "in the win animation he suddenly vanished … it was working before but it stopped")
Recorded (dumps/screens/rec/win3/win6/win7.mp4): Sora doesn't vanish — ~4.5 s into the win pose the CAMERA cuts to a
wide shot and pans away from him. _910A and the win script (block 84: sounds/shakes only) are identical to test 86.
Test 148 = same disc with the GMO cut back to 86 motions → camera stays on Sora (8+ s). ⇒ the game takes the results
camera from GMO motion 86 if it exists (Cloud has 86 motions = none); our appended _720A (Finishing Leap, camera
curves of Cloud's _630A) was motion 86. Fix: motion 86 = _719A = copy of the win pose (build SLOTS + STUBS copy after
the MOTIONS loop); all new slots shift to 87+ (spot33_chain SLOTS blocks +1). Helper's magic blocks → 97+.
- ✅ Test 149: motion 86 = _719A (win pose copy) → camera stays on Sora through the whole win pose (~9 s), then the
  normal stage pan (dumps/screens/rec/win8.mp4, w10_sheet.png). Model 2.48 MB (+ magic slots) still loads (mirror too).
- Test 149 also has the HP magic (Firaga/Thundaga/Blizzaga ground+air, Lv18, ablt cap 832) — not tested in game yet.

## Four combos (2026-10-15)
Mat (3 AM): "I want 4 combos, right now all combos lead to one finisher in the air. I want different combo variations."
Before: Combo Plus / Slide Dash / Dodge Slash all ran GROUND (→ Finishing Leap); all air starters ran AIR (→ Aerial Finish).
Now (spot33_combos.py ACTIONS, no new animations / GMO slots / effects):

| # | starter (input) | route (KH2 clips) | finisher |
|---|---|---|---|
| 1 Ground Rave | Combo Plus (◯ close, ground) | 604 → 608 → 612 → 604 → 608 → 620 | 620 ground swing, Bravery BLOW-AWAY (0x36e) — Sora stays on the ground |
| 2 Sky Rave | Slide Dash (◯ from range) | dash 656 → 608 → 616 (airborne) → 648 launch → 732 → 728 → 732 → Horizontal Slash ×6 | Aerial Finish (776, 5 sweeps) |
| 3 Spin Leap | Dodge Slash (◯ + stick away) | 652 spin (4 hits) → 620 → 612 → 616 → 648 launch → 732 | Finishing Leap (668 slam, shockwave) |
| 4 Air | Air Combo / Aerial Spiral / Aerial Dive | Air Combo: 724 → 728 → 732 → Horizontal Slash → Aerial Finish; Aerial Spiral: 768 → 728 → 732 → Horizontal Slash ×6 with the LAST slash blowing away; Aerial Dive: 784 → 728 → 732 → Finishing Leap plunge | three different air endings |

How (no new animations): **type-7 VARIANTS** (spot33_chain.py `VARIANTS` + `variant()`): a p_se block can serve several motion
ids; each type-7 row = motion id → block + variant, and events whose condition byte 0 = v only run in variant v (0 = always).
- 10003 = block 43 variant 2 (Cloud's own row; all events cond 0 → identical to N1) → piece G4 0x1020 (604 again).
- 10004 = block 45 variant 2 (Cloud's own row, hit 0x64e) → piece G5 0x1021: + continue window 18-48 (WINDOWS), lunge copy, free 50.
- 10005 = block 46 variant 2 (Cloud's own row) → piece GF 0x1022: N3's hit made variant-1-only, variant 2 gets 0x36e
  (Bravery blow-away, same hit as Finishing Leap; a new atkp id would break spot33_magic's sorted appends) + lunge, no window.
- 10316 = NEW row → block 56 (Horizontal Slash) variant 2; 10060's row variant 0 → 1; its hits/window made variant-1-only;
  variant 2 = same 6 slashes with the last = 0x36e → piece HSF 0x1023.
New pieces are appended plya rows (spot33_combos NEW_PIECES, copies of N1 / N2 / N3 / R1 with the new motion, role 1).
Square chains moved to branch points that exist in the new routes: Combo Plus > Upper Slash after hit 2 or 5 (N2/G5),
> Guard Break after hit 3 or 4 (N12/G4); Slide Dash > Upper Slash right after the dash, > Guard Break after its hit 2.
Air chains unchanged. Descriptions updated (spot33_desc.py). Quick test disc (no full build yet):
dumps/ULUS10566-test191q-combos.iso = test189 + spot33_combos + spot33_chain (SFX_BASE=21900000) + spot33_fx + spot33_desc.
- 12+ hits (Mat: "all the combos should be 12 hits plus"; hits counted from the blocks): Ground Rave 12
  (604-608-612-604-608-Dodge-Slash-spin(4)-612-620-620 finisher; new variant motions 10317 = block 94 v2, 10008 = block
  44 v2), Sky Rave 19, Spin Leap 13 (+604), Air Combo 15, Aerial Spiral 16 (Horizontal Slash x6 twice, Mat's tip),
  Aerial Dive 13 (+Horizontal Slash). Ground Rave finisher hit = 0xb85 BR_A_REN1_1 (unused) as a horizontal blow-away.
- test191s (Mat on test191r: "4th hit of back+O [air = Aerial Dive] … Sora goes too close"): Aerial Dive's template dash
  (op 0x02 mode 4, frames 0-10) carried Sora into the foe → AUTHOR `nodash`. Air links AN1/AN2/AN3/NM3 got NEAR1
  lunges (ADVANCE; they had none) and light air hits push 1.5 instead of 4 (KNOCK). FRONT-sphere moves (hits 1.8 m
  ahead: Aerial Dive, Aerial Spiral) get NO lunge (`nolunge`; the NEAR1 lunge closes to ~0.5 m).

### Magnet Burst "stuck in a falling pose" (Mat test275; 2026-10-16, Magnet helper, static only)
- Mat: "the Magnet HP attack has an animation leaving him stuck in a falling pose until you dodge or move" (= the CPU
  Sora "stuck after an air move" too).
- NOT the animation length: `_707A` = KH2 788 frames 0-45 = 90 ticks, block 68 one-shot op 0x02 end at 90, op 0x28 at
  82 = the same convention as Cloud's template (10092: `_704A` 0-62 = 124 ticks, op 0x02 at 124). Codex's two op 0x19
  effect one-shots (18/60) change no timing. Block 68 op 0x0a "stay airborne" 0-65535 = same as the template.
- Cause = piece flags: plya 0xb32 (HP_A_METEO1) +0x18 = **0x10013** (spot33_combos FLAGS, set when Magnet was still a
  copy of Braver's plunge). Bit 0 = plunge piece: waits to LAND, then plays plya +0x10 (Braver 0x5cb → 10094, 0x5cf →
  10097 have it; 0xb32 has +0x10 = none). Block 68 is now authored from 10092 (stays in the air) → never lands → stuck.
  Vanilla 0xb32 = 0x10012; AIR_FINISH1 (0x5ca, our Aerial Finish HP 10306, works) = 0x10212.
- Fix: spot33_combos FLAGS MB → 0x10012 (future full builds) + spot33_magnet.py sets it on a disc (guarded
  0x10013 → 0x10012, owner 33 only). In test277. NOT runtime-checked: if he still hangs, next suspect = the op 0x02 end
  one-shot cond 0x10 (needs a trace).
