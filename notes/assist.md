# Sora as an ASSIST (owner 33) — how assists work, what Sora had, the fix

Started 2026-10-16 by Claude (assist helper). Static only (no emulator). Base = dumps/ULUS10566-test275-solo2s.iso.

## 1. Key fact: owner 33 WAS an assist-only fighter (Aerith)
- In 012 Aerith (owner 33, key sev120) is assist-only. Her assist data still sits in every table, so "owner 33 as an
  assist" today = **Aerith's assist** (her model, her moves, her voice), not Sora.
- Her files (clean disc, untouched by the Sora build): obj/p_sev120_a.objx (355,020 B),
  obj/P_SEV120_1P_A.gmo / _2P_A / _3P_A (~405 KB each, Aerith model + assist motions), voice bank
  voice_P_SEV120_A_00.scd (bank 219600). Sound bank of the _a objx = 219500.

## 2. Tables (system/main.bin)
- **main.bin member `assist.bin`** (3,620 B, read by FUN_088b39e0): u32 0x15 (version), u32 31 rows,
  31 × 104-byte rows: u32 owner, u16 name/info id, u8, u8, then 4 × 24-byte "assist move" records
  (u16 global index, u16 1, u8 kind, u8 flag, u16 id-or-FFFF, 4 × f32 = AI/use ranges). Then u32 126 + 126 × u16
  = **action id per move record**, then 33 global f32 params.
  - Cloud (13): actions 314 / 321 / 326 / 328 (= his own ground Brv / air Brv / ground HP / air HP ids).
  - Aerith (33): actions 933 / 934 / 935 / 936. Row for 33 already exists → no new row needed.
  - Owners 1..31 (no 23 Chaos, no 32 Feral Chaos) + 33.
- **objentry kind-8 rows** = the assist object (name +0x24 → obj/<NAME>.gmo, model +0x34 → obj/<model>.objx):
  Cloud: P_SEV100_{1,2,3}P_A / p_sev100_a (+2 = 6); owner 33: rows 922/923/993 P_SEV120_{1,2,3}P_A / p_sev120_a
  (+2 = 340 = Aerith's type id, extra-id list empty). The Sora build changed only owner 33's kind-0 rows (copies of
  Cloud's) — the kind-8 assist rows are still Aerith's.
- Assist pick list (menu): FUN_08af4374 → FUN_088d5ac8(list, 0x23, 0, 1): every owner of the EBOOT unlock table
  0x089D7BE0 (bit set) **plus** owner 33 (flags 2|4|8) if FUN_0885c304(DAT_089d4e14) (= Aerith unlocked).
  Since test20 the unlock table row 22 = (33, −1) → owner 33 is ALWAYS in the list now (and twice if Aerith is
  unlocked on the save — to check).

## 3. How an assist is built and loaded (static, decompile)
- Battle start: FUN_08888354 makes the assist object for each side from the side's assist objentry (kind 8 row):
  assist.bin row (by owner) → a blank save record + owner + level, loadout = **eqaa** preset (system.bin `eqaa`,
  94-byte rows, key = assist.bin row +4). Cloud: eqaa 301 = his idx 1/7/10/13 (= actions 314/321/326/328).
  **Owner 33: eqaa 396 = idx 0/1/2/3** → ablt 0x2100-0x2103 → today Sora's 1020 / 321 / 326 / 328.
- Which assist move runs (FUN_08b2e638 caller ~all.c:508800, CPU version ~390136): assist.bin row byte +6
  (bit0 Bravery / bit1 HP: pick the ground/air record by the TARGET's state, else by the caller's), record 0..3 =
  ground Brv / air Brv / ground HP / air HP; record +2 u16 must be ≠ 0; record +4 flags (bit0 = skip range check);
  action id = assist.bin u16 list[record index] → looked up in the ASSIST object's own comb. Comb entries are
  enabled from the eqaa loadout (FUN_08ab7f40 → ablt +12), so the assist comb ids must equal those ablt actions.
- Files loaded for an assist (log of a Terra assist): obj/<NAME>.gmo (objentry +0x24, e.g. P_SIX100_1P_A),
  obj/<main 1P row name>.cosx, obj/<model>.objx (+0x34, p_six100_a), voice/EN/battle/voice_<chrp key>_a_00.scd
  (format "voice_%s_a%s.scd", FUN_08845230). No .exex, no voice_load list for assists. Loading-screen face =
  menu/JP/common/chara_face_in_name_r/p_<key>_face_in_name_r.gim (Sora's already, spot33_faces).
- Each object load gets a 0x264000-byte work block (FUN_0884417c) — the same ~2.5 MB limit as fighters. Vanilla
  assist sizes: objx 210-391 KB, GMO 405-776 KB (Gabranth biggest, 1.10 MB together). Cloud 310 KB + 581 KB.
- The `_a.objx` is a plain SUBSET of the fighter's own objx: Cloud's 18 script blocks are byte copies of his
  main blocks (same sound ids 22xxxxx — the engine adds +50000 for kind-8 rows), type-7 table remapped to the new
  block numbers, plya/atkp = only the rows the 4 assist actions use, comb = 4 entries, own small snd_ bank
  (bank 22500, only used slots), own effe (FEP id 0x511c0000 = assist family, textures 0xa8011cNN, only the
  leaves it needs), brat/text/wind/hit shapes copied. The `_A.gmo` = same skeleton + only the 18 motions the
  blocks need (motion index = block number), EX-weapon textures stubbed (texture block keeps only its name arg).
- Generic assist motions (ids → Cloud assist block): 0x1/0xa idle _000A, 0x65 _021A, 0x66 _022A, 0xf0 _500A
  (dash in, hit FACT_LEAP), 0x12c _170A, 0x1f4/0x1fe/0x226/0x230 _210A, 0x1f5/0x1ff/0x227/0x231 _211A,
  0x385/0x38f _043A. Sora's own main blocks for these = Cloud's assist blocks byte for byte (only sound ids differ).

## 4. What owner 33 had before this work (test275)
- assist list: yes, owner 33 is in it (EBOOT unlock table row (33, −1) since test20; FUN_088d5ac8 may add 33 a
  second time when "Aerith unlocked" FUN_0885c304(DAT_089d4e14) is true → possibly two Sora entries).
- Picking him loads **Aerith's** files (P_SEV120_xP_A.gmo = Aerith model, p_sev120_a.objx = her Cure/Holy moves,
  voice_P_SEV120_a_00.scd = her voice). assist.bin asks for actions 933-936 (her comb), but eqaa 396 now enables
  ablt 0x2100-0x2103 = Sora's 1020/321/326/328 → none of her comb entries is enabled (her single-piece moves may
  still start; untested). objentry kind-8 rows still Aerith's (+2 = 340, her type id).

## 5. The fix: tools/scripts/spot33_assist.py → dumps/ULUS10566-test279-assist.iso (static only, not played)
Base test275-solo2s (fe2d1066…) + this script only. test279 sha256
0c01da624ec63cb628e1a2e9bf1ab4a1e1683427da59503a4cb9728cb20cc79b. Second run = "nothing to do".
- **Moves** (all KH2 animations already in Sora's model, script blocks = byte copies of Sora's own blocks):
  ground Bravery (action 1020) = Slide Dash → swing → swing → Upper Slash launcher (pieces 0x5c1 0x5bf 0x7d8 0x5c2);
  air Bravery (321) = KH2 air combo, 3 swings (0x5c5 0x5c6 0x5cc); ground HP (326) = Explosion (Sora's
  "Explosion alone" block, 6 sweeps + blast hit); air HP (328) = Aerial Finish (5 sweeps).
  Menu names come from ablt 0x2100-0x2103 = Combo Plus / Air Combo Plus / Explosion / Aerial Finish.
- obj/p_sev120_a.objx 393,072 B (Aerith's 355,020; vanilla max 391,296): 17 blocks, own snd_ (h14 219500, 22 slots
  130,800 B), effe = Cloud's stock assist effe re-IDed 0x511c0000 → 0x51280000 (61 id refs) + keys
  0xa8011cNN → 0xa80128NN (94) — NO tree copied/emptied (node serials untouched). FXSE rows: hit marks take
  Sora's own KH2 hit sound row (slots 85/86), all Cross-slash/Braver rows silenced.
- obj/P_SEV120_{1,2,3}P_A.gmo 728,764 B each (Aerith's ~405 KB, Gabranth's 775,856): Sora's model, 17 motions,
  6 generic motions thinned :2, textures file15/file17/file19/texture-1/ultima_weapon stubbed (Cloud's assist model
  stubs its EX weapon textures the same way). file2 (TexAnm lip target) and texture-0 (eye atlas) kept.
- voice/EN/battle/voice_P_SEV120_a_00.scd 62,224 B (h14 219600; slots the blocks use + 1, 4).
- main.bin: objentry rows 922/923/993 (+2 340 → 6, extra id 0x34 like Cloud's kind-8 rows); assist.bin owner-33
  row: byte +6 0 → 3, records = Cloud's 4 melee records (flags 3, extra id −1), list 933-936 → 1020/321/326/328.
- Not done / known gaps: Explosion's two Cloud "burst" effects (FEPA 57/68) are not in the assist effe → dropped
  (swings + hits + sounds only). A KH2 blast for the assist needs a leaf transplant + node-serial renumber
  (spot33_magnet.renumber_serials). Assist list may show Sora twice if the save has Aerith unlocked (EBOOT
  FUN_088d5ac8 adds 33 again) — both entries give the same Sora assist.
- Size risk: assist objx + GMO = 1.12 MB, ~20 KB above the biggest vanilla assist (Gabranth 1.10 MB). If a battle
  with Sora as assist crashes/freezes at load: stub file2 too (−67 KB) or thin more motions.
- Mat (2026-10-16T17:43:29Z): with Sora as assist, the assist gauge doesn't fill.

## 6. Mat (test301): "with Sora as assist the assist gauge doesn't fill" — static findings (2026-10-16)
- Gauge = float at *(fighter+0x52c)+0x1c, 0..10000 (5000 = 1 stock: FUN_08b3418c; 10000 = 2: FUN_08b341e8).
  Fill on hits = FUN_08aee124 (only on a STARTER piece's hit, plya +3 == 0, battle-rule % DAT_09afde8c), on damage
  dealt = FUN_08aedc80 (needs ability effect 0x5b). Fill rates are global (assist.bin floats + battle rules), NOT
  per assist: nothing in assist.bin / eqaa / chrp gives an assist its own gauge rate.
- Gate (FUN_08aeda5c): fighter+0x1108 (assist object) != 0, no effect 0x54 (unless 0x57), and FUN_08b019ec(side) == 0,
  i.e. the assist object must be HIDDEN (assist+0x388 & 0x10000, set by the hide call FUN_08b35118 at creation and
  when an assist attack ends, FUN_08b01cec), its cooldown (assist manager +side*0x18+0x14) ≤ 0, and its break
  state (+side*0x18+0x18) not 2/3 (assist break, FUN_08b04870).
  ⇒ an empty gauge means the Sora assist object is missing, never hidden (stuck "out"), or stuck in break/cooldown.
- Owner-33 table side is identical in kind to Cloud's (assist.bin records = Cloud's, eqaa 396 enables our comb ids,
  objentry kind-8 bytes = Cloud's); no table difference explains it. Ghidra cuts several assist-manager functions at
  FUN_08838300 (wrongly marked no-return), so the rest needs a runtime look.
- Bisect disc dumps/ULUS10566-test303-assistdiag.iso (sha256 41e3fdd7…) = test301 + diag_assist_cloudfiles.py:
  owner-33 assist built from CLOUD's stock assist files (objentry name/model, eqaa 396 ← eqaa 301, list 314/321/
  326/328), everything else of spot33_assist kept. Gauge fills → fault in the Sora assist files; still empty →
  fault on the owner-33 table/menu side. DIAGNOSTIC ONLY.
- Runtime 2026-10-16T18:00:47Z: mid-fight setup assist owner -1, objentry 0xffff, all ids -1, A = 0, gauge fixed 4000 → setup/menu side never registers Sora as assist.

## 7. Real cause + fix (2026-10-16): the game drops assist owner 33 unless "Aerith unlocked"
- Runtime (main session, test301 mid-fight): setup assist owner *(s8)0x09AFC8FA = −1, objentry *(u16)0x09AFC7DE =
  0xFFFF, base+0x7F0 = −1 → no assist object ever made; the gauge (4000) never moves.
- Static: battle setup FUN_088f9bb0 copies the fighter's record and then does
  a check: when "Aerith unlocked" (FUN_0885c304(DAT_089d4e14)) is false and the loadout's assist owner (+0xb8) is 33,
  it sets that owner to 0xff (none) — owner 33 was Aerith,
  an assist you had to unlock. Mat's save doesn't have her unlocked, so Sora is wiped from the loadout before the
  fight. Same check in FUN_088f6a58 (another setup path, record +200) and FUN_0892905c (friend-card owner check
  returns 2 = "locked" for 33). The assist menu itself lists Sora through the unlock-table row (33, −1).
- Fix (spot33_assist.py part EBOOT, guarded old/new words): the owner-33 compare constant (0x21) in the instruction at EBOOT 0x088F9CA4,
  0x088F6C04 and 0x08929060 changes 0x21 → 0x7F (no owner) → owner 33 is never dropped; FUN_0892905c then checks 33 against the
  normal available list (has it).
- Disc dumps/ULUS10566-test304-assistfix.iso = test302-icons (415bc4a8…) + spot33_assist.py (EBOOT 3 words +
  p_sev120_a.objx rebuilt from test302's Sora objx: newer brat), sha256
  79470345aa61976b54e0f9bf22ccb6d85904cff47237e01fe745580acc2276ff. Static only.
- 2026-10-16T18:14:20Z test304-assistfix USER-VERIFIED (Mat): Sora as assist works (EBOOT owner-33 drop-check fix confirmed). (The failing test304 read was a run where Sora had not been picked as assist.)
