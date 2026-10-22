# Music (BGM): how it works and how we add KH2 tracks

Owner: Claude (music helper), 2026-10-16 23:10 UTC. Codex delivery: `tools/music/20261016-kh2-music/` (Tension Rising,
Working Together, Sinister Shadows; ATRAC3plus `encoded/KH2_TR.AT3`, `KH2_WT.AT3`, `KH2_SS.AT3`).
Tool: `tools/scripts/spot33_music.py` (last step of `build_sora.sh`). Disc: `dumps/ULUS10566-test319-music.iso`.

## 1. Where the music lives (static, test316 = clean dump for all of this)

- **Audio files:** standalone ISO files `PSP_GAME/USRDIR/DATA/BGM/*.AT3` (134 files, NOT in PACKAGE.BIN).
  The game opens `DISC0:/PSP_GAME/USRDIR/DATA/BGM/%s` (EBOOT FUN_088a04a8) with the file name from the BGM table.
  Directory extent = sectors 28..31 (8192 B, 4 sectors), sorted names, records never cross a sector; free bytes per
  sector 10/52/24/168. Each record = 33 + name + pad + 14 B XA system-use ("UXA", attr 0x0d55) → 58 B for a
  10-char name. **Three 10-char records (Codex's KH2_TR.AT3 names) do NOT fit** after re-packing (needs a 5th
  sector); 9-char names (56 B) do: disc names **KH2TR.AT3 / KH2WT.AT3 / KH2SS.AT3** (sorted between INSTALL_OK.AT3
  and LOSE_B.AT3; sector use then 2038/2046/2020/2002 → no room left). More tracks later = relocate the BGM
  directory (bigger extent at the ISO end + its record in DATA + its "." record + the L and M path tables).
  test316's BGM directory listing = the clean dump's (isoinfo md5 identical).
- **BGM table:** `general_archive/main/main.bin` (MPK) → `bgm_entry.bin`: "BENT" header 16 B (+8 u32 count = 131),
  then 44-byte rows. Loader FUN_0889ee60 allocates room for 256 rows (rows past the file count are DLC rows, named
  from their own 0x84-B records). Lookup by id = linear scan (FUN_0889f5e8). Row:
  - +0 u16 BGM id, +2 u16 text id (bgm_name), +4 4×s16 unlock flags (DAT_089d726c bits, -1 = none)
  - +12 u8 flags: bit0 / bit1 = battle track (bit1 = the "local_14==1" pool, e.g. B01_01; bit0 = the other pool),
    bit2 = DLC/Museum-only (battle list rejects it)
  - +13 s8 volume (×0.01; vanilla 25..100), +14 u8 random weight (0 = never in a weighted pick), +15 0
  - +16 2×u32 series mask (bit = stage/world series number), +24 u32 stage-code mask (bit from the EBOOT table
    0x089caa10: one00=0, two00/two05=1, … org00=10, org50=11, ele00=12 … vni00=18) → used by the auto/random pick
  - +28 char[16] file name (case does not matter: table says `B01_01.at3`, disc has `B01_01.AT3`).
  All ids 0..130 are used; 131+ free.
- **Names:** `general_archive/main/EN/main_lang.bin` (MPK, only EN exists on the US disc) → `bgm_name.bin`.
  Same codec as ability.bin: u16[0] = N (132), u16 offsets at positions 1..N (×2 = byte offset; 0 = no string),
  text id k = position k+1; entry = u16 byte length + UTF-16LE text incl. NUL, XOR KEY[(2*(k+1)+18+j) % 32].
  (Codex's "ability decoder fails" = the old ability_text.decode treats u16[0] as entry 0; position 132 = text id 131
  "FFXI - Heavens Tower" sits right after the table.) Text ids 61/62 (M04/M05) have offset 0 = no name.
  Text lookup FUN_0887afbc → FUN_0887a800: id < N else default string. Free text ids: 132+ (127 is also unused).
- **Museum music list:** `collection_param.bin` section 6, 8-byte records (u16 BGM id, u16 unlock flag (0xFFFF =
  always), u16 seconds (play time before it moves on), u16 0xFFFF). 127 records. Menu FUN_08a36d1c builds up to 256
  entries from these + DLC BGM rows (bit2). Name = bgm_name via the row's text id. Header: counts at +4 (section 6 =
  u16 +0x10), sizes at +22 (section 6 = u16 +0x22); sections back to back from 40, then 9×64 B strings.
- **BGM picker (NOT Quick Battle — correction 2026-10-16T23:40Z after Claude's runtime: QB 1-on-1 has no BGM row).**
  Owner chain: picker FUN_08a55a10/08a55acc (panel +0x578) ← 6-item battle-settings panel FUN_08a573b4 ← Creation Room
  scenes FUN_08a4f364 (loads text/JP/mess_pk_creation_room_0, panel at +0x6fd0) and FUN_08a6b418 (built at 0x08a4… lines
  367048/367161, same scene). = Creation → Original Quest editor → a battle's "Battle and Event Settings". Quick Battle music
  = automatic by stage (series/stage-code masks). Picker list = menu FUN_08a55d54: every row with (flags & 3) and !(flags & 4) whose unlock flags
  are all set, max 128 (67 eligible now). Selected id stored as a **short** (FUN_08a55b4c → settings +6) and used by
  the battle (FUN_0888b544 modes 1/2/3/0xb/0xc: `DAT_09afde4c+2` short) → ids > 127 are fine here.

## 2. Forced / mode music (not changed)
FUN_0888b544 (battle start) picks the BGM per mode (+0x4c):
- modes 0,4,6,8,10,13,14: scenario record (FUN_088bbd8c, 36-B records) **+0x22 signed char** forced id; if -1 →
  weighted random by series + stage code (FUN_08ade9a4/FUN_08adf04c).
- modes 1,2,3,11 (+12): no scenario → the player's selected short; with a scenario → its forced char id or random by
  stage (FUN_08ade6a4/FUN_08adebb4).
- mode 5: FUN_08adeaa8 (series ×2 + stage code); mode 7: FUN_08ade42c/3cc (flag bit0/bit1 pool by DAT_09afe05a&1);
  mode 9: `*(+0x7c8)+0x22e4` (an explicit id from another struct).
- The forced id is a **signed byte** (`lb` at 0x08ade65c): a scenario can only force ids ≤ 127, so new tracks (131+)
  can never be forced by a scenario row — they never replace story/Chaos music. Random picks only take rows whose
  series/stage masks match the stage; new rows have masks 0, so they are never auto-picked (vanilla stages keep their
  music). Chaos multi-round / any-round selection: not traced (needs runtime); left alone.

## 3. Audio format
Native `B01_01.AT3`: RIFF, fmt 52 B (WAVE_FORMAT_EXTENSIBLE 0xFFFE, ATRAC3plus GUID, 12-B codec tail
`01 00 28 45 00…` = version 1 + config word 0x2845: low 10 bits = frame/8 − 1 → 560-B frames = 96 kbps, 0x28 =
stereo), fact (end sample, delay 2524), smpl (1 loop; coordinates include the delay), data. Streamed through a
0x18000-B (96 KB) buffer (FUN_088a05b0).
Codex's files: 352.8 kbps (2048-B frames), fmt 40 B (no codec tail), fact delay 4096 (+368 decoder = 4464 measured).
spot33_music rewrites only the fmt chunk into the native 52-B layout (native bytes with avg bytes/s 44100, block 2048,
config 0x28FF); fact/smpl/data stay Codex's bytes.
Loudness (vgmstream, whole file RMS × volume): 10 native battle tracks median −16.2 dBFS; KH2 −16.2/−15.9/−15.9
at volume 100 → **volume 100** (same as the u_* 012 tracks).

## 4. Release consideration (not decided)
The xdelta patch will contain ATRAC3plus audio derived from Mat's own KH2 copy (KH2 PC export SCDs, music114/053/111).
That is copyrighted Square Enix/Disney music, like the model/voice data already in the patch — Mat decides.
Real-PSP risk: 352.8 kbps = only ~2.2 s in the 96 KB stream buffer (native 96 kbps = ~8 s); a lower bitrate encode
(e.g. 128 kbps AT3+ or 132 kbps ATRAC3) would be safer on hardware if Codex's encoder can do it.

## 5. What spot33_music.py does (2026-10-16 UTC, test319)
`python3 -I tools/scripts/spot33_music.py ISO [--dry] [--tracks N] [--rollback]` — last step of build_sora.sh.
| track | disc file | BGM id | text id | name | Museum record | intro | loop end (= file end) | loop length | Museum seconds |
|---|---|---|---|---|---|---|---|---|---|
| Tension Rising (KH2 music114) | KH2TR.AT3 3,561,636 B | 131 | 132 | KHII - Tension Rising | #127 | 12.00 s | 80.57 s | 68.57 s | 91 |
| Working Together (music053) | KH2WT.AT3 3,225,764 B | 132 | 133 | KHII - Working Together | #128 | 12.15 s | 72.91 s | 60.76 s | 83 |
| Sinister Shadows (music111) | KH2SS.AT3 2,599,076 B | 133 | 134 | KHII - Sinister Shadows | #129 | 5.68 s | 58.74 s | 53.05 s | 69 |
- bgm_entry rows: flags 1 (Quick Battle BGM list; 67 → 70 eligible, cap 128), volume 100, weight 1, masks 0, no unlocks.
  Example row (TR): `83008400 ffff×4 01 64 01 00 00000000 00000000 00000000 "KH2TR.AT3"`.
- Museum: records (id, 0xFFFF = always unlocked, seconds, 0xFFFF) → the three tracks are the LAST entries of the
  Museum music list (after "FFVI - Victory Fanfare"); Quick Battle BGM list: LAST three (after "DFF - Opening").
- Guards: vanilla rows/names/Museum records must equal the clean-dump hashes; our extra rows must be exactly ours
  (prefix, order TR/WT/SS); 134 vanilla BGM files; Codex AT3 sha256; directory must fit in its 4 sectors.
- Proof (test316 copy): Tension-Rising-only run, re-run = "already"; `--rollback` → sha256 = test316 exactly
  (56219f4f…); then `--tracks 1` + full run + re-run. `isoinfo -l` diff vs test316 = only the 3 new lines; 134 old
  files same extents/sizes; changed old sectors = PVD 16, BGM dir 29-31, PACKAGE_INFO rows, collection_param,
  main_lang, main.bin (all three tables in place). `isoinfo -x` of each new file = the prepared bytes; vgmstream
  decode of the disc files = byte-identical PCM to Codex's originals (header rewrite changes no audio); ffprobe:
  atrac3p 44100 Hz stereo 352.8 kbps; vgmstream loop TR 529189..3553125 samples.
- **dumps/ULUS10566-test319-music.iso** = test316-fromclean + spot33_music (all 3 tracks), 1,810,565,120 B,
  sha256 d902c26d46c32fade1a880b2a99f4de3b0cbabe42477b13c49eab5f54d5550b2. Static only, not played.
- Saves: a Quick Battle setting that remembers a KH2 track (id 131-133) on a disc without these rows finds no row →
  that battle has no/auto music (no crash expected). Not a problem while the patch is applied.

## 6. Runtime test plan (Claude runs it; settings CPU Minimal + Order's Sanctuary)
1. Museum → Music: scroll to the END of the list. Expect "KHII - Tension Rising", "KHII - Working Together",
   "KHII - Sinister Shadows" after "FFVI - Victory Fanfare". Play TR: KH2 intro (0:00-0:12), then the loop part;
   at **1:20.6** it must jump cleanly back to the 0:12 material (no click/gap/silence/crackle); the Museum moves on at
   ~1:31. WT seam at **1:12.9** (moves on ~1:23), SS seam at **0:58.7** (~1:09). Listen: stereo, no stutter, loudness
   close to the FF tracks around it (pick "FFVII - Fight On!" right after for comparison).
2. (CORRECTED: not Quick Battle) Creation → Create New Quest → add/edit a battle → Battle and Event Settings → BGM: the three KHII names are the
   LAST entries (after "DFF - Opening"). Pick Tension Rising → battle music = TR; stay ≥ 2:30 to hear two seams
   (1:20.6 and 2:29.1). Then Retry/rematch: same track. Then Cloud vs Garland with Sinister Shadows (no Sora).
3. Regression: one vanilla BGM in Quick Battle + one in Museum still plays; stage auto music unchanged (BGM default).
4. If silent: check PPSSPP log for sceAtrac / file-open errors on DISC0:/PSP_GAME/USRDIR/DATA/BGM/KH2TR.AT3.
5. Not covered (left alone): Story/Labyrinth/Arcade forced music, Chaos rounds (scenario forced id is a signed byte
   ≤ 127; new ids can't be forced; no per-round picker added).
- Runtime 2026-10-16T23:16:48Z (Claude, test319): Jukebox shows the 3 tracks (128-130); Tension Rising plays, game-audio RMS −15.8 dBFS, matches the source WAV. Loop + battle selection pending.
- Runtime 2026-10-16T23:37:42Z: loop PASS (1:20.6 → 0:12.0, continuous match).

## 7. Auto music when Sora is in the fight (2026-10-16 UTC, test320)
- The "series" mask at +16 is really an **owner mask** (64 bits, bit = fighter owner id): FFI rows bits 1,2
  (WoL/Garland), FFVII rows 13,14,26 (Cloud/Sephiroth/Tifa), FFXIII 31 (Lightning), Chaos rows 32. No vanilla row has
  bit 33 → vs CPU Sora the pool held only stage-bound rows. Owner 33 inherits nothing here (Cloud's FFVII music comes
  only from bit 13).
- Battle start FUN_0888b544 (EBOOT): modes 0/4/6/8/10/13/14 → FUN_08ade458 → FUN_08ade9a4/FUN_08adf04c: weighted
  random (+14 weight) over unlocked rows with **opponent** owner bit (`lb` setup block 2 byte 0 = 0x09afc900, the
  CPU/2nd fighter) OR stage-code bit (+24, map record +0x20 string → EBOOT table 0x089caa10). Mode 5: player OR
  opponent OR stage (FUN_08adf22c). Mode 7: opponent bit + flag pool bit0/bit1 (FUN_08adeeb4). Scenario-forced ids win.
  The Opponent Info screen's "BATTLE BGM" label shows the result (Claude: vs CPU Cloud → "FFVII - Let the Battles Begin!").
- Only these pickers read +16/+20/+24 (grep of every bgm-table walker in all.c/menu_all.c). Owner bit 33 is used by
  no other row.
- spot33_music AUTO (default): KH2 rows owner bit 33 (+20 = 2), flags 3, weight TR 2 / WT 1 / SS 1 (TR 50 %, WT/SS
  25 % each when no stage-bound row qualifies). MUSIC_AUTO=0 = test319 rows. Vanilla rows untouched → every matchup
  without Sora keeps exactly its vanilla pool.
- Sora as the PLAYER (vs CPU X) still gets X's music in modes 0/4/…: the rule only reads the opponent. Changing that
  needs code (e.g. hook 0x0888b5b0, where the opponent's owner byte is loaded → use 33 when the player's byte 0x09afb8a0 is 33);
  not done.
- dumps/ULUS10566-test320-musicauto.iso = test319 + AUTO rows (7 bytes in main.bin; sha256
  eb112d02bc014fa229495c81bb1f5201a2857fb992dd312858ddf0d37b43a832). Static only.
- Runtime check (Opponent Info "BATTLE BGM" label): player Cloud vs CPU Sora → a KHII name (TR most often; if the stage
  has its own rows, e.g. Order's Sanctuary, a stage row can come up too — repeat 4-6 times); player Sora vs CPU Cloud
  → FFVII names only; Cloud vs Lightning → FFXIII names only; Sora vs CPU Sora → KHII.
- Runtime 2026-10-17T00:18:17Z (Claude, test320): Opponent Info label = Quick Battle BGM picker (◀ ▶), KHII at the end; picked Tension Rising plays in battle (audio match). Auto vs CPU Sora: KH2 2/8, stage tracks 6/8 → weights to raise.

## 8. KH2 odds vs Sora (2026-10-17 UTC, test321)
- Claude runtime test320 (weights 2/1/1, vs CPU Sora, Order's Sanctuary, 8 battles): DFF - Opening ×4, Cosmos,
  Cantata Mortis, TR, WT → stage rows compete (Order's Sanctuary = stage bit 11: Cosmos w1, Cantata Mortis w2, DFF
  Opening w1 = 4). The Opponent Info "BATTLE BGM" label is the Quick Battle ◀ ▶ picker (KHII = last 3 after "No BGM").
- Weight byte (row +14) is read as a signed byte (at 0x08adea08) → ≤ 127; the sum is a 32-bit int (no overflow).
  Vanilla stage-tied weight sums (all rows counted as unlocked = worst case): 5 on stage bits 0-9 and 14-18, 4 on bit 11,
  3 on bits 12/13, 1 on bit 10, 0 elsewhere. Worst mixed pool (mode 5: stage + the other fighter's owner rows) = 13.
- New weights TR 32 / WT 16 / SS 16 (sum 64, 2:1:1). KH2 share vs Sora = 64/(64+W): worst stage 92.8 %, Order's
  Sanctuary 94.1 % (TR 47 %, WT 23.5 %, SS 23.5 %), bits 12/13 95.5 %, bit 10 98.5 %, stages without own rows 100 %;
  mode-5 worst 83 %. Max qualifying rows 11 < picker cap 32.
- dumps/ULUS10566-test321-musicodds.iso = test320 + weights (3 bytes), sha256
  cdb4c6956c203e1dfbad03ee983c3f6be64978f25c9a2cbacc682025e0b9e464. spot33_music accepts test319/test320 rows.
- Runtime 2026-10-17T00:35:31Z (Claude, test321): auto BGM vs CPU Sora 6/6 KH2 (TR 4, WT 1, SS 1). PASS.
