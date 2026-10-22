# Roster research (started 2026-10-12)

## File names
Character battle file = `obj/p_<model>.objx` (hash checked). Cloud = `obj/p_sev100.objx` = pkg 3394.
Model code: 3 letters = FF number (one, two, thr, for, fiv, six, sev, eht, nin, ten, gst = guests/012 newcomers?,
org = original), 100 = hero, 200 = villain, 110/120/… = extra characters. pkg 5973 (Cloud's lite copy) name unknown.

## Owners (ablt +1) ↔ models (from objentry.bin `_1P` rows)
1 one100, 2 one200, 3 two100, 4 two200, 5 thr100, 6 thr200, 7 for100, 8 for200, 9 fiv100, 10 fiv200,
11 six100, 12 six200, 13 **sev100 (Cloud)**, 14 sev200, 15 eht100, 16 eht200, 17 nin100, 18 nin200,
19 ten100, 20 ten200, 21 gst100, 22 gst200, 24 for110, 25 fiv210, 26 sev110, 27 eht110, 28 ten110,
29 gst110, 30 gst120, 31 gst130, 32 org210, 33 sev120 (**no objx file**), 34 org800 (**no objx file**). 23 missing.

## Tables sized per character
- objentry.bin (main.bin): u32 12, u32 1170, 68-byte rows: +0 u16 obj id, +2 u16 ?, +4 u16 ?, +6 u8 owner,
  +7 u8 1P/2P, +10.. list of extra ids (0xFF end), +0x24 char[16] NAME_1P, +0x34 char[16] model.
- system.bin/chrp: u32 33, u32 34, 34 × 144-byte rows (per-character params). → table sized for 34 characters.
- system.bin/chrl: "CLEV", 31 entries (level tables, playable characters only?).
- ablt: owners 1–34, 18 free row slots.

## Files per character (Cloud)
obj/p_sev100.objx = pkg 3394 (battle file), obj/p_sev100_w.objx = pkg 5973 (lite copy), obj/p_sev100_a.objx = pkg 4390
(alt costume?), obj/d_sev100.objx/.gmo. Aerith (owner 33) is a **helper-only** character in 012: has obj/p_sev120_a.objx, no p_sev120.objx.

## chrp row (144 bytes)
+0 owner, +1 level table id (chrl key; 0xFF = none), +5 another owner ref (Cloud 13, Aerith 33, but gst100 → 22?),
+0x74 char[8] model name (no NUL), then 4 × u32 ids. Lookup: FUN_088b70c8(owner) → bsearch on +0.

## Select screen (menu overlay, Ghidra program EBOOT_menu.elf; decompile in dumps/decomp/menu_all.c)
FUN_08aff218 builds the grid:
- list of owners at **0x08B0119C** (u32, −1 terminated, 31 entries; file offset = vaddr − 0x089DD4C0 + 0x54,
  OVL_MENU_APP.ELF at ISO sector 185056). The −1 is directly followed by the cell table → no room to append.
- skips owners whose **unlock bit** (1 << ((owner−1) & 31)) is not set in FUN_08af4224's mask → only 32 bits,
  owner 33 shares bit 0 with Warrior of Light.
- cell table u16 at 0x08B0121C (30…0, + one spare 0), row sizes i32 at 0x08B0125C: 6, 10, 10, 5, −1.
- per-owner UI objects at (*(menu+4))[menu+0x14 + owner].
Other owner lists: EBOOT 0x1C8A40 (sorted 1..32 no 23), 0x1C8B52 (heroes then villains), 0x1C8C70; menu u16 list
at 0x08AE45FA has 33 entries incl. 23 and 33 (gallery?).
Ghidra fix needed: FUN_088d9f5c wrongly marked no-return (tools/scripts/FixNoReturn.java, Redisasm.java).

## Test 14 — `dumps/ULUS10566-test14-spot33.iso` (copy of test 10)
`roster_patch.py`: copy-chrp 13 → 33; copy-objentry 13 p_sev100 → 33 p_sev120 (1P/2P/3P/PUB rows);
select-swap 32 → 33 (owner 32 org210 replaced on the grid).
Owner 33 has NO ablt rows → may have no attacks. Question: does spot 33 show, load Cloud, and stand in battle?
Result: (fill in)
Result: ❌ #33 not on the Quick Battle grid (16 unlocked + "?" random, which was always there). FUN_08aff218 is NOT the
Quick Battle grid (or not the only gate).

## Unlock table (EBOOT 0x089D7BE0, file off 0x1D4BB8): 5 × i32 rows, −1 terminated
(owner, unlock flag bit, costume-2 flag, costume-3 flag, SEEN flag 3601+ = yellow NEW tag while clear, notes/unlocks.md §5). Flag −1 = always. Bits in DAT_089d726c.
Owner 33 is not in it; owner 23 (Chaos, flag 925) is. FUN_088d5ac8 builds the "available characters" list
(owner, ?, level) from it (skips 23 unless asked; adds 33 = Aerith only for helper lists). FUN_08af7d94 →
DAT_09b6d76c / count DAT_09b6d7f8 = menu's available list. Save data per character: FUN_088cb3b4(owner) = index
in EBOOT list 0x089CBC98 (1..32), owner 33 → −1 → shared dummy record.
EBOOT.BIN is encrypted → edit EBOOT data with PPSSPP cheats (CWCheat _L 0x2AAAAAAA = 32-bit write at 0x08800000+A).

## Test 14b — test 14 ISO + cheat `patches/ULUS10566-cheats.ini` (copied to PPSSPP's PSP/Cheats/ULUS10566.ini)
Unlock table row 22 (Chaos) → (33, −1, …): owner 33 always unlocked.
Result: still not on the grid by itself — Quick Battle uses ANOTHER table (below). Cheat is still needed.

## Quick Battle grid table — menu overlay **0x08A864D0** (returned by FUN_08a85ecc), found live 2026-10-12
12-byte rows: u16 picture, u16 picture (= owner − 1), u16 game logo (FF1 = 0 … FF7 = 6), u16 owner, i32 owner.
Order = grid order (31,30,27,28,24,26, 1,3,…,19, 2,4,…,20, 21,22,29,25,32, 23). Last real row = 23 (Chaos, picture 22).
Rows show only if the owner is in the available list (unlock table above).
**Row 31 (Chaos) → (32, 32, 6, 33, 33)** + unlock cheat ⇒ a new cell appears on the grid (row 3, next to "?").
Picture 32 = broken "Wa…" image, name = placeholder "FINAL FANTASY" banner, FF7 logo OK, Lv 1.
Picking it works ("Play as this character?" → CPU select → setup → **battle loads with Cloud's model + HUD portrait**).
Saved in ISO with `roster_patch.py ISO qb-row 23 33 32 6` (test 14 ISO patched in place).

## Moves for owner 33
Save records: base = *(0x089D712C) + 0xF58, 0x778 bytes each, index = position of owner in EBOOT list 0x089CBC98.
Owner 33 → no index → shared blank record at **0x09AEFAFC** (init flag 0x09AEFAF8). Blank = nothing equipped ⇒ no
attacks (confirmed by Mat in battle). Loadouts: record + 0x10 + set × 0xC6 (current set at record + 0x773); slot
bytes = ability index within owner; **owner byte at loadout + 0xB6** (FUN_088b7dc0: id = owner << 8 | index).
⇒ copying Cloud's record (index 12) into 0x09AEFAFC gives owner 33 Cloud's equipped moves (ids 0x0Dxx).
Done live 2026-10-12 (debugger memory.write) mid-battle. Result: ❌ no attacks; Customization → Abilities showed
"Aerith Gainborough Lv1", nothing equippable, and Mat got stuck there (can't leave with 0 abilities) → restarted.
Reason: ids are owner<<8|idx and owner 33 had only 4 rows (Aerith's helper moves, actions 933–936).

## Driving PPSSPP myself (Settings > Tools > Developer tools > Allow remote debugger; port from `ss -ltnp`, was 32775)
tools/scripts/ppdbg.py (read memory), ppwatch.py (log breakpoint hits), ppsnap.py (dump all RAM), ppctl.py (press
buttons: cross circle square triangle up down left right start select). Screenshots: `import -window <PPSSPP X window id>`
(DISPLAY=:1; id from `xwininfo -root -tree | grep duodecim`). Cursor index of the QB grid at 0x09705BBC (heap).

## ablt per owner (790 rows, sorted by id = owner<<8|idx, binary-searched)
Cloud 17 rows (209–225), owner 23 (Chaos) 25, **owner 33: 4 rows (617–620, Aerith ground/air Bravery/HP)**,
owner 34: 1 row (621). main.bin has only 112 free bytes after it → can't grow ablt (17 rows = 680 bytes) yet.
Row +27 = owner again. +18 u16 = CP cost.

## Test 15 — `dumps/ULUS10566-test15-spot33-moves.iso` (copy of test 14) + cheats in `patches/ULUS10566-cheats.ini`
ablt rows 617–620 → copies of Cloud rows 209 (action 1020 = our 4-hit combo), 216 (321 air Bravery),
219 (326 ground HP), 222 (328 air HP) as owner 33 idx 0–3 (`ablt_patch.py copy-row`). Aerith's helper moves are gone.
Cheat "Spot 33 equip": blank record 0x09AEFAFC set 0 slots = [0,–,–, 1,–,–, 2,–,–, 3,–,–], owner byte 33, current set 0.
DON'T open Customization for #33.
Result (2026-10-12, Mat ran test 14 by mistake, so I patched ablt rows 617–620 live in RAM; ablt rows at *(0x089D7294)):
still no attacks. Battle copies the record (char+0x30C → copy) and the loadout was right, so I compared records.
**Missing piece = learned-ability list**: record +0x3EE, 6-byte entries (u8 idx, u8 owner, u8 mastery (6 = mastered),
3 bytes; empty = ff ff 00 00 01 00). Cloud: 25/40, aa/40 (general), then 00/0d, 02/0d, 07/0d … all 06.
After writing [25 40][aa 40][00 21 06][01 21 06][02 21 06][03 21 06] into the blank record and starting a new battle:
✅ **#33 ATTACKS** (Bravery 95→101, Lightning 95→89, damage 6). Mat confirmed: the 4-hit combo works and all
four moves (ground/air Bravery, ground/air HP) attack. Cheat "Spot 33 learned" added (16-bit writes).
Notes on driving: battle button presses need duration ≥ 12 frames (4 was ignored in battle); debugger handshakes
time out often → retry with 40 s timeout.

## Test 16 — `dumps/ULUS10566-test16-own-file.iso` (copy of test 15): #33 gets its own file ✅
- `pkg_add.py ISO obj/p_sev120.objx 3394`: copy of Cloud's file appended at the END of the ISO (ISO had no free space,
  PACKAGE.BIN had no gaps); PACKAGE.BIN directory size stretched to reach it (1,373,677,568); PACKAGE_INFO +1 entry
  (sorted by hash, 11044 entries, 132,544 bytes; buffer max 0x20F8C ⇒ ~210 more files); PVD volume size updated.
  Disc directory names have no ";1".
- `roster_patch.py set-model 33 p_sev100 p_sev120`: #33's objentry rows load obj/p_sev120.objx again.
- Mat: Cloud model shows, all moves work. ✅
- Tools now find added files by path (`pkg_offset('obj/p_sev120.objx')` after `use_iso(iso)`); arcfile/comb_add find
  size fields by hash (indexes shift after pkg_add).
- Separation check (patched in place): #33's NEW_MIDDLE3 → sideways 0, up 40 (launch straight up); Cloud's file
  unchanged (30 / 8, blast into wall). Result: ✅ Mat: #33 launches straight up, Cloud still hits the wall
  → #33 and Cloud are fully separate.

## Character-count limits (so far)
file index ~210 more files; chrp 34 rows; unlock mask 32 bits (owner 33+ share bits); QB grid 31 cells + random;
save records 31 (new owners share the blank record → no saved progress); ablt 18 free rows (needs main.bin room).
Hidden owner spots usable now: 33, 34, maybe 23.

## Release plan (Mat, 2026-10-12)
Share as an xdelta patch. Everything that is a cheat now (unlock, equip, learned) must become a real ISO change first.
After everything works, build ONE tool that applies every change to a clean ISO (keep each step recorded here).

## Files a fighter loads in battle (logged live with tools/scripts/ppnames.py, breakpoint on FUN_088713e4 = path)
For #33 (objentry name N = +0x24, e.g. P_SEV100_1P; model M = +0x34; chrp name C = +0x74):
  obj/N.gmo (BODY MODEL, ~2 MB), obj/N.cosx (68 B costume info), obj/N.exex (88 B EX info), obj/M.objx,
  voice/EN/battle/voice_C_00.scd, voice/EN/voice_load_C.bin, menu/JP/battle/chara_image/N.gim (HUD portrait),
  menu/EN/common/chara_name/p_X_name.gim + menu/JP/story_mode/chara2/p_X_1p.gim with X = "(null)" for #33
  (name/art key comes from yet another per-owner table — to find). Also map/org50.* = Order's Sanctuary.
_2P/_3P names = alternate colours (Cloud: P_SEV100_2P.gmo …). _A = alt costume (p_sev100_a.objx, P_SEV100_1P_A.gmo).

## Test 17 — `dumps/ULUS10566-test17-own-model.iso` (copy of test 16)
Added (pkg_add): obj/P_SEV120_{1,2,3}P.gmo (1P = Cloud's 2P model as a visible proof, 2P = Cloud 1P, 3P = Cloud 3P),
obj/P_SEV120_{1,2,3}P.exex, menu/JP/battle/chara_image/P_SEV120_{1,2,3}P.gim; replaced P_SEV120_{1,2,3}P.cosx data
with Cloud's (same 68 B; 1P gets the 2P one). objentry #33 names back to P_SEV120_1P/_2P/_3P/_1P_PUB/_2P_PUB/_3P_PUB.
pkg_add SRC is now an ORIGINAL index (looked up by hash); `--replace DST SRC` overwrites same-size data.
Expected: #33 looks like Cloud's alternate colour; real Cloud normal.
Result: ✅ (2026-10-12, I launched PPSSPP myself and drove it) #33 = black alternate outfit + different sword,
matching HUD portrait; real Cloud = normal outfit + Buster Sword. Screenshot: dumps/screens/test17-spot33-vs-cloud.png.
→ **Swapping #33's skin = replacing obj/P_SEV120_1P.gmo (+ .cosx/.exex/portrait).**

## Skin research (2026-10-12)
- Fan-made Sora costumes for 012 exist: Ultima Espio made 5 Sora DLC packs (KH1, KH2, KH2 Christmas, KH2 Halloween,
  DDD) as Cloud costumes, ~2011–2013 (gamergen). Proves a Sora GMO rigged to Cloud's skeleton works. Someone
  else's work → for a public patch we'd need permission/credit, or make our own.
- "Dissidia Modding Suite" (Scribd tutorial): DLC decrypt + GMO texture editing; includes GMO ID lists.
- GMO = PSP model format (meshes, textures, bones); Noesis can read GMO.
- Key requirement: a new body model must use Cloud's (Dissidia) skeleton so his animations play → KH2 Sora must be
  re-rigged onto Cloud's bones. OpenKH export route not confirmed by search yet (check OpenKH GitHub/Discord).
Full file log of a #33 battle: notes/files-loaded-spot33-battle.txt. Battle voice lines use a short prefix per
character (Cloud "cl_battle_NN.at3", Lightning "li_battle_NN.at3"); #33 used "cl_" → another per-owner table to find
for Sora's voice lines.

## Test 18 — `dumps/ULUS10566-test18-pink.iso` (copy of test 17) ✅ (I drove it myself, 2026-10-12)
obj/P_SEV120_1P.gmo = Cloud's skin exported to glTF, hair texture recoloured pink, rebuilt with gltf2gmo.py
(see notes/gmo-format.md). #33 = pink-haired Cloud, animates and fights; screenshots in dumps/screens/.

## Test 19 — `dumps/ULUS10566-test19-weapon.iso` (copy of test 18) ✅
#33 = Cloud skin rebuilt with weapons too (REBUILD_WEAPONS=1 NEW_SCALE=1): sword 1.6× longer, blue. Works in battle.

## Removing the cheats (2026-10-12)
- PSP_GAME/SYSDIR/EBOOT.BIN (sector 560, 4,641,296 B, encrypted ~PSP) can be replaced by the decrypted ELF
  (4,640,948 B — same size as the zeroed BOOT.BIN) in place; directory size updated. PPSSPP boots it.
- **Test 20** (`dumps/ULUS10566-test20-plain-eboot.iso`, copy of test 19): plain EBOOT with unlock-table row 22 →
  (33, −1) baked in (ELF file offset of 0x089D7BE0 + 22×20), cheat "Spot 33 unlock" switched OFF → #33 still on the
  grid, battle OK. ✅ Unlock cheat retired.
- Equip/learned cheats write the shared blank record (0x09AEFAFC, init once by FUN_088cb164 → FUN_088cb9e8 →
  FUN_088cba10, which is CODE, not a data template). Save data has exactly 31 records (EBOOT owner list 0x089CBC98,
  owners 1..32 without 23). Options: (A) map owner 33 to an existing slot (e.g. Feral Chaos #32) → real saved
  progress + normal Customization, but that character loses its slot; (B) code patch that fills the blank record
  with #33's equips/learned at first use → no saved progress for #33; (C) grow the save format (hard).
- Real PSP: custom firmware runs ISOs with decrypted EBOOTs (as fan translations do); needs a real-hardware test.

## 32nd save slot research (Mat chose this option, 2026-10-12)
- Save file ULUS10566GameData00/DISSIDIA.BIN = 257,240 B, PSP-encrypted (entropy 8.0). Game data size = 0x3ECC8
  (257,224) set in FUN_088aec54 (param+0x25C), data buffer = save base + 0xF08 (save base = *(0x089D712C),
  was 0x08BAED38, in EBOOT .bss). Fighter records: base+0xF58 = blob+0x50, 31 × 0x778 → blob+0xE7D8.
- Code-referenced save offsets listed (97). Big zero areas: blob+0x12428..0x1CEF8 = achievement/collection table
  (base+0x13330, FUN_08af880c) → fills up with progress, NOT safe. 27 × 0x10A8-byte entries from ~blob+0x1EF00 each
  end in 0xF62 zero bytes (unknown list). Tail after last referenced offset: blob+0x3E790..0x3ECC8 = 1,336 B (< 1,912).
- Growing the blob needs the save buffer moved (other .bss data follows it) + save/load code patches.
- Plan: compare with a 100%-complete save (decrypt with PPSSPP: load it in game, read RAM via debugger) → areas still
  zero at 100% = truly unused → place record #32 there and patch FUN_088cb3b4/FUN_088cb164 to map owner 33 to it.

## Test 21 — `dumps/ULUS10566-test21-own-record.iso` (copy of test 20) — #33 gets its own saved record
Built with `tools/scripts/spot33_save.py ISO` (re-runnable; prints "already patched"). Changes:
- EBOOT: FUN_088cb3b4 = short owner-list loop (keeps a0/a1); its tail 0x088cb3e4.. holds the rest of the blank
  path. FUN_088cb164: owner 33 → record at *(0x089D712C) + 0xF58 + 0x38040 (= blob + 0x38090, in friend card slot
  24); if record[0] != 33 → FUN_088cbbb4(rec, 33) (reset + owner + level 1 via chrl + preset via eqpm).
  Friend card limit 25 → 24 (the compare constant at 0x088f523c and 0x088f52a0). 0x089CB7E8[33] = preset 250.
- system.bin: eqpm + preset 250 (owner 33, Cloud preset 7 with idx 0/7/10/13 → 0/1/2/3); the eqpm RAM buffer
  0x09B59AF8..0x09B5DA00 has room for exactly ONE extra preset. chrl + table for owner 33 (Cloud's minus 0x0Dxx).
  main.bin grew 560 B → moved to the ISO end by pkg_put.
- Cheats equip + learned switched OFF (all three #33 cheats now off).
- Tools: tools/scripts/mips_asm.py (mini assembler, checked against the game's code), PatchDisasm.java (Ghidra check).
Result (a 100 % save): battle starts as #33; record in RAM = owner 0x21, Lv1, set 0 = [0,1,2,3],
learned 4025, 40aa, 2100–2103 (+ preset generals). ✅ Mat: #33 attacks with NO cheats (2026-10-12).
Note: learned moves now have mastery 0 (cheat had 6).
Save test ✅: after a win the record held 0x07D0 (2000, EXP?) at +4; game autosaved (leaving Data Config);
PPSSPP restarted + save loaded → #33 record unchanged (21 01 01 00 d0 07 …). Progress survives save + reload.

## Test 22 — `dumps/ULUS10566-test22-names.iso` (copy of test 21) — loading-screen name ✅
Owner → name key tables ("sev100" = Cloud; owner 33 = "sev120", Aerith's old key): EBOOT 0x1c7d18 strings, battle
overlay table 0x08AFBC68, menu overlay tables at file 0xcf58 and 0xf100 all have 33 entries; the third menu table
(file 0x17ab50 = VA 0x08B57FBC, used by the pre-battle loading screen FUN_08af6b70-like code) stopped at 32 →
"p_(null)_name.gim". `tools/scripts/spot33_names.py ISO [SRC_KEY]` points its entry 33 at "sev120" and adds
menu/EN/common/chara_name/p_sev120_name.gim, menu/JP/story_mode/chara2/p_sev120_1p.gim,
menu/JP/character_select/chara2/p_sev120_1p.gim, menu/EN/battle/encount/encount_text_tim2/encount_sev120.gim,
menu/JP/arcademode/arcade_last_chara_tim2/arcade_last_sev120.gim (copies of Cloud's). Face-in-name images for
sev120 already exist (Aerith's). Result: loading screen shows "Cloud Strife" + portrait for #33
(dumps/screens/test22/07-loading-banner.png). Still broken: Quick Battle grid (cell icon "Wa…", no name, no big
art, a stray "FINAL FANTASY" logo) → different source, to find next.
Driving note: the 100% save remembers cursors/stage, so drive_qb.sh's fixed presses land on the wrong cells —
navigate with screenshots (#33 cell = from Lightning: down ×3, right ×5).

## Test 23 — `dumps/ULUS10566-test23-grid-pic.iso` (copy of test 22) — Quick Battle grid ✅
Grid row pictures are indexes 0..31 into a 32-picture set (pic = owner − 1 for most; Feral Chaos 31). #33's row had
pic 32 (doesn't exist → "Wa…" junk, no name, no big art). `roster_patch.py ISO qb-row 33 33 12 6` → Cloud's
pic 12: icon, "Cloud Strife" name, big art and FF7 logo all show; Lv 1 proves it's #33
(dumps/screens/test23/grid-33.png). For Sora: either add a 33rd picture to that set (pack not found yet) or keep
pic 12 and replace images per key. TODO: find which files hold the grid pictures (icon / name / big art).

## Test 24 — `dumps/ULUS10566-test24-voice.iso` (copy of test 23) — #33's own voices ✅
Voice key = system.bin/chrp row +0x74 char[8] (Cloud "P_SEV100"). Files per key: voice/EN/battle/voice_<KEY>_00.scd
(SCD bank: attack shouts/grunts) and voice/EN/voice_load_<KEY>.bin ("VOLD": u32 magic, u32 date, u32 count, u32 0,
count × 24-byte rows = char[16] clip name, u16 line id, u16 ?, u16 condition, u16 condition 2). Clip = voice/EN/
battle/<name>.at3 (spoken lines; Cloud has 70 "cl_battle_NN" + 2 "UP09_…cl"). The "cl_" prefix is just DATA in that
list → no code table needed. `tools/scripts/spot33_voice.py ISO [PREFIX]`: chrp 33 key → P_SEV120, copies Cloud's
bank + list under it, renames list clips cl_battle_NN → so_battle_NN and adds copies of the 70 .at3 under the new
names (to be replaced by Sora's). Logged in battle (notes/files-loaded-test24-voice.txt): voice_P_SEV120_00.scd,
voice_load_P_SEV120.bin, intro line so_battle_56.at3 ✅. No JP voice files on the US disc (voice/EN only).
PACKAGE_INFO.BIN room: disc space runs to sector 26080 (zeros), game buffer max 0x20F8C → pkg_add/pkg_put now
allow up to 11253 entries (INFO_ROOM). Now 11130 used → ~120 new files left. Keep Sora's line count in mind.
Still Cloud-looking: Quick Battle setup screen's left banner (stray "FINAL FANTASY" logo, no name) — another table.

## Test 25 — `dumps/ULUS10566-test25-beep.iso` (copy of test 24) — #33's own weapon/hit sounds ✅
Fighter file chunk `snd_` (obj/p_sev120.objx, 339,376 B) and the voice banks (voice_*_00.scd) are both "SSCF"
banks: header 0x20 B (u32 size @8, u32 count @0xC), count × 32-byte entries (+4 data offset from bank start,
+8 size, +0xC u16 sample rate, then playback params), data = PSP ADPCM (VAG, 16-byte blocks / 28 samples).
#33/Cloud bank: 70 slots (one empty), 13–18 kHz, 0.2–0.8 s. Tool: `tools/scripts/sscf.py` (list / wav / replace;
replace fits the old size, so the bank never grows). Proof: all 69 sounds → 1000 Hz beep (in place, pkg_put).
A/B recording of the game's audio (parec @DEFAULT_MONITOR@), same 25 s of #33 pressing Circle on Order's
Sanctuary / Minimal: test 25 = 32 windows with a strong 1 kHz tone, test 24 = 0 (tools/scripts/tone_check.py,
recordings in dumps/audio/). Which slot is which sound is not mapped yet (find via one-slot beeps or the p_se
scripts' sound ids). Note: Square on the results screen = Save Replay (careful when driving).

## Test 26 — `dumps/ULUS10566-test26-tones.iso` — which sound slot plays for which move (2026-10-12)
#33's snd_ bank sits in RAM at 0x093B8BC0 in battle (search "SSCF", size 0x52DB0). Play code reads the entry with
s0 = entry pointer; CPU breakpoint at 0x08991A70 (the read of entry field +0x8) = one stop per sound → slot = (s0−bank−0x20)/32.
Tool: `tools/scripts/ppslotwatch.py PORT 0x093B8BC0 70 OUT.json 0x08991A70` (presses moves on a timetable).
(Recording-based tone detection, ppsound_map.py, was too noisy because of the battle music.)
Tentative map (2 rounds, times after the press):
  27 jump take-off (+0.2 s), 20 whoosh right after (+0.3 s; also starts the ground HP move)
  2 ground Bravery swing; 1 / 15 / 2 air Bravery combo swings
  ground HP: 20, 2, 1, 3, then 39 + 37 repeated (multi-hit), 3 = finisher?
  air HP: 35, 15, 1, 62, 23, 22 (when it connected)
  21 guard; dash: no sound from #33's own bank (shared bank)
Watch out: blind timed presses after a battle ends wander into menus (Mognet calendar etc.) — check the screen first.

## Tests 27–28 (2026-10-12) — entry animation and new voice lines → see notes/voice-and-sound.md §5–6
Test 27: #33's entrance = motions _900A/_902A in obj/P_SEV120_1P.gmo (swapped with the win pose → proven).
Test 28 (`dumps/ULUS10566-test28-lines.iso`): #33 own line ids 1000–1071 + own subtitles ("[33] Let me test you."
seen), Lightning "vs #33" line 1100, #33 reply 1101 (not seen yet; random pick).
Old test ISOs (1–23, 25–27) deleted 2026-10-12 at Mat's request; kept: original, test 24, test 28.

## Move names for #33 (2026-10-13) — test 53 `dumps/ULUS10566-test53-names.iso`
Menu move names/descriptions = `general_archive/main/EN/main_lang.bin` (MPK; hash b1e92c5e = pkg 7683) → `ability.bin`:
u16 offset[count] (×2 bytes; count = offset[0] = 1307), entries = u16 byte length + UTF-16LE text XOR KEY[(2·L+18+j)%32]
(subtitle key, +18 instead of +20). Game text id (ablt +2 name, +4 description) = entry index − 1.
`tools/scripts/ability_text.py dump|set|add`; mpk.replace() rebuilds an MPK. The game decodes the whole table in RAM.
GROWING the table (add) garbled entries near the old end in RAM (game buffer sized for the original?) → instead
`spot33_movenames.py ISO` reuses unused placeholder entries 392–399 ("Firion08"…, no ablt row points at them) and
points ablt rows 617–620 at them: Sonic Blade / Aerial Sweep / Firaga / Aerial Finish + descriptions. Verified in RAM.
Cloud's names for reference: 594–604, 615 Cross-slash, 617 Finishing Touch, 618 Braver, 619 Omnislash Version 5.
In-battle banner ("Crushing Blow", "Cross-Slash" … are the OPPONENT's/Lightning's) — Sora's own banners not checked.
**Customization → Abilities for #33 still freezes** (white screen; same on test 52, so not the names). Header shows
"Aerith Gainborough" (character name table for owner 33 not changed yet). Saves backed up first
(downloads/save_backup_20261013-0449/), restored/unchanged after.

## Customization for #33 works (test 54) + "Sora" header (test 55) — 2026-10-13
- Freeze cause: menu FUN_08ad0d48 looks up the owner in system.bin/**amas** ("AMAS": u32 count @8, rows u32 owner,
  u32 entries, u32 data offset, 0; entries 8 B: u16 ability, u16 1, u16 ability, u16 FFFF). Owners 1–32 only →
  owner 33 got NULL → loop over garbage. `tools/scripts/spot33_amas.py ISO` adds a row for 33 (Cloud's entries minus
  his 0x0Dxx abilities; 38 entries). Abilities screen now opens: Sonic Blade / Aerial Sweep / Firaga / Aerial Finish.
- Header banner = picture `p_sev120_name.tm2` (128×32 index8 GIM) inside menu packs ("menu pak"):
  menu/EN/menu_lpk_customize_gim_0.bin and menu/EN/menu_lpk_shop_gim_0.bin (hash 7bcc2b61). `name_banner.py`
  builds a word from letters cut out of other banners (S Squall 8-17, o Cloud 36-44, r/a Garland 57-62/47-55,
  PAD=0 GAP=1) → tools/art/sora_name_banner.png; `gim_put.py` writes a PNG over an index8 GIM in place (own palette
  builder; old Pillow); `spot33_banner.py ISO PNG` does both packs. Still Aerith: the small face picture next to it.
- Debug recipe for menu freezes: pause the CPU a few times (cpu.stepping + getAllRegs), the hot pc/ra point at the
  looping function in dumps/decomp/menu_all.c.

## VS / loading / encounter name "Sora" (test 63 `dumps/ULUS10566-test63-vsname.iso`, 2026-10-13) ✅
- VS screen + loading banner name = menu/EN/common/chara_name/p_sev120_name.gim (128×32 index8, same font as the
  Customization header) ← tools/art/sora_name_banner.png. Seen: VS screen "Sora vs Lightning".
- Big glowing intro name (shown for the OPPONENT: "vs Lightning" when #33 plays) =
  menu/EN/battle/encount/encount_text_tim2/encount_sev120.gim (256×64 index8) ← "Sora" glued from Squall's S,
  Cloud's o, Garland's r + a (`spot33_vsname.py`, pixels go to the nearest letter fill → no neighbour bits).
  Preview tools/art/sora_encount.png. Not seen in game yet (needs a battle where #33 is the opponent).
- Still Cloud: face pictures (VS 64×64 menu/JP/story_mode/chara2/p_sev120_1p.gim, HUD portrait, grid pic 12).
- Spoken lines: #33's intro line shows "[33] Ready?" = Cloud's .at3 audio + test-28 placeholder subtitle
  (voice_lines.py prefixes '[33] '). Fix = Sora's KH2 lines as ATRAC3 .at3 (encoder needed) + real subtitles.

## Face pictures (test 65 `dumps/ULUS10566-test65-faces.iso`, 2026-10-13) ✅
Source: KH2 HD Jiminy's Journal portrait kh2_export/raw/kh2_fifth/remastered/menu/jmface_ex0.imd/-0.dds (256², see-
through background; ex1 = smiling; jmface_ex2.. = Donald, Goofy, Kairi, Riku, Roxas … ex42). `spot33_faces.py ISO`:
- menu/JP/story_mode/chara2/p_sev120_1p.gim 64×64 = VS screen face ✅ seen
- menu/JP/battle/chara_image/P_SEV120_1P.gim 128×128 = battle HUD portrait ✅ seen
- menu/JP/common/chara_face_in_name_r/p_sev120_face_in_name_r.gim 128×32 = eye strip next to the Customization name
  (was Aerith's ORIGINAL file → Aerith's assist picture, if used anywhere, now shows Sora too). Not checked yet.
Still Cloud: grid cell / select big art / FF7 logo (pic 12 set, not found), character_select/chara2/p_sev120_1p.gim
256² full-body art, arcade_last_sev120.gim 512², Quick Battle setup banner (stray "FINAL FANTASY" logo).
Menu driving: the blind press list in test_combo.sh can wander (it opened Extras → Data Install; cancelled with
a HELD Circle, "install will be deleted" → YES; no install folder left; saves untouched). Drive step by step with
screenshots: title → Load (100% save) → Battle Mode → Quick Battle 1-on-1 → #33 = down×3 right×5 → CPU Lightning.
- Quick Battle select screen (grid icon, big art, "Cloud Strife" name, FF7 logo) = pictures picked BY NUMBER from
  "menu pak" files (magic "menu pak", u16 1, u16 count, u32 ?, then u32 offset + u32 size per entry; GIMs carry a
  .tm2 name but are not looked up by it): menu/menu_pk_free_battle_gim_1..3.bin (p_<key>_1p big art,
  p_<key>_face_in_name(_r)), menu/EN/menu_lpk_free_battle_gim_0.bin (p_<key>_name). No sev120 entries → #33 uses
  Cloud's (pic 12). Test 66: menu/JP/character_select/chara2/p_sev120_1p.gim (loaded by name "p_%s_1p", 256²) is
  NOT the Quick Battle art (no change seen) — some other screen. Fix needs the menu code that maps pic → entry.
- Test 76 (`dumps/ULUS10566-test76-arcade.iso`): spot33_faces.py also writes arcade_last_sev120.gim (512², a 480×272
  screen picture: render left + big faded journal face right, tools/art/qb_arcade.png) and
  character_select/chara2/p_sev120_1p.gim (256², = qb_art.png). Both were Cloud copies. Not seen in game yet.
- PPSSPP debugger (2026-10-13 evening): websocket handshakes suddenly took ~25 s (tools timed out / "hung"). Cause: the
  Origin header from python websocket-client. All tools now connect with `suppress_origin=True` → instant.
