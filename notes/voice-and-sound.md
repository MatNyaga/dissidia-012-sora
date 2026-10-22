# Voices, subtitles, sounds and entry animations (2026-10-12)

## 1. Which files a fighter uses
Voice key = `system.bin/chrp` row +0x74 char[8] (Cloud "P_SEV100"; #33 now "P_SEV120").
| What | File | Format / tool |
|---|---|---|
| Attack shouts, grunts | `voice/EN/battle/voice_<KEY>_00.scd` | SSCF bank → `tools/scripts/sscf.py` |
| Spoken line list | `voice/EN/voice_load_<KEY>.bin` | "VOLD" → `tools/scripts/voice_lines.py` |
| Spoken lines | `voice/EN/battle/<clip>.at3` (ATRAC3 in RIFF; ffmpeg decodes) | one file per clip |
| Subtitles of all lines | `general_archive/field/EN/field_lang.bin` (MPK) → `battle_voice_name.bin` | "OFF4" → `tools/scripts/voice_text.py` |
| Weapon / hit / jump sounds | chunk `snd_` inside the fighter file `obj/p_<model>.objx` | SSCF bank → `sscf.py` |
| Shared sounds (dash etc.) | not in the fighter's bank (shared bank, not mapped) | |
No JP voices on the US disc (voice/EN only).

## 2. VOLD line list (`voice_load_<KEY>.bin`)
Header 16 B ("VOLD", u32 date, u32 count, u32 0), then count × 24 B rows:
char[16] clip name, u16 **line id** (= subtitle id), u16 **moment** (0x0046 battle start, 0x0146 win,
0x0246 loss), u16 **condition**, u16 **value**.
| condition | meaning | value |
|---|---|---|
| 0 | general line | how hard the fight is: start 0 normal / 2 tough / 3 very tough; win 0 easy / 1 foe careless / 2 tough / 3 close; loss 0 vs weaker / 2 vs stronger |
| 5 | general, random pick | 0 |
| 2 | vs a specific opponent | opponent owner number (every fighter has one per opponent, mirror included) |
| 6 | **reply** to another fighter's line | that line's id → this is how intro conversations work |
| 8 | team battle | 0 first fight, 1 next, 2 later ("One down!", "Forgive me, comrades") |
| 7 | another special mode | 0/1 (not pinned down) |
The game picks randomly among all rows that fit, so a new line only plays sometimes.
Line ids: 1206..3260 used (all of them), **0..1205 free**. Feral Chaos (32) has 3 rows, no voice.
Full labelled catalogue (2179 rows, every fighter, real subtitle text): `dumps/voice_catalog/voice_lines.md`
and `.csv`, plus every clip as 16 kHz WAV in `dumps/voice_catalog/wav/` (built by `tools/scripts/voice_catalog.py`).

## 3. Subtitles (`battle_voice_name.bin`, "OFF4")
"OFF4", u32 count (3261), count × u32 offset in 4-byte units from file start (0 = none); entries: u32 byte length
(UTF-16LE + NUL, padded to 4) + text XOR-scrambled with a 32-byte key:
byte j of the text of line id L ^= KEY[(2·L + 20 + j) % 32] (key in voice_text.py). Lengths are not scrambled.
Found by comparing the disc file with the decoded copy in RAM (PPSSPP RAM dump; the game decodes it on load).
First guess (key position by file order) was wrong — Mat saw garbage subtitles in test 28; fixed to line id.
Re-encoding the original gives byte-identical output. The field_lang.bin MPK is rebuilt by voice_lines.py.

## 4. SSCF sound banks (fighter `snd_` and `voice_*_00.scd`)
Header 0x20 (u32 size @8, u32 count @0xC), count × 32 B entries (+4 data offset from bank start, +8 size,
+0xC u16 sample rate, then playback params), data = PSP ADPCM (VAG; 16-byte blocks of 28 samples).
`sscf.py list|wav|replace` (replace keeps the slot size → bank never grows; resamples WAV to the slot's rate).
Proof (test 25): all of #33's sounds → 1 kHz beep, A/B game-audio recording (parec @DEFAULT_MONITOR@):
beep disc 32 tone windows, normal disc 0 (`tools/scripts/tone_check.py`).

### Cloud/#33 bank slot map (test 26, CPU breakpoint 0x08991A70 at the play code's read of entry field +0x8; s0 = entry)
`tools/scripts/ppslotwatch.py PORT BANK_ADDR 70 OUT.json 0x08991A70` (bank in RAM: search "SSCF" size 0x52DB0;
was 0x093B8BC0). Tentative: 27 jump take-off, 20 whoosh (also starts ground HP), 2 ground Bravery swing,
1/15/2 air Bravery combo, ground HP 20,2,1,3 then 39+37 per hit, air HP 35,15,1,62,23,22, 21 guard,
dash = shared bank. (Audio-based mapping, ppsound_map.py, failed: battle music masks the tones.)

## 5. Animations — battle entry
Animation controller = fighter + 0x130; current animation id at fighter + 0x180 (controller + 0x50).
`FUN_0882f4e4(controller, gmo_index)` sets an animation; id → GMO motion index via the table at controller+0x48.
Logged at battle start (both fighters): id **1100** then **1110**, then 1 (idle). For Cloud's model:
1100 → motion `_900A` (80 frames), 1110 → `_902A` (68 frames). `_910A`/`_911A` = win pose (proved in test 27).
GMO motion = args 0x80B1 frame range, 0x80B2 fps (30), 0x80B3 per bone/channel (0x48 translate, 0x4B rotate,
0x4D scale) → fcurve index; fcurve = u32 format (0x80 half floats; +4 per-frame quaternions), dims, key count,
keys (half frame + values). Tool: `tools/scripts/gmo_motion.py list|copy|take`.
Test 27 ✅: #33's own `obj/P_SEV120_1P.gmo` with _900A/_902A ← _910A/_911A → #33 does Cloud's win pose as its
entrance (video A/B in dumps/screens/test27/). ⇒ **A unique Sora entrance = new data in those two motions.**
Still to build: glTF/Blender animation → fcurves writer (bake per-frame local rotations on Cloud's bones).

## 6. Test 28 — `dumps/ULUS10566-test28-lines.iso` (from test 24) — new lines + own subtitles ✅
`tools/scripts/voice_lines.py test28 ISO`: #33's rows get their own line ids 1000–1071 with "[33] …" subtitles,
Lightning gets a new "vs #33" row (id 1100, clip li_battle_93), #33 gets a reply row to it (id 1101).
Seen in game: "[33] Let me test you." ✅ (own subtitles work). The vs/reply rows not seen yet (random pick).

## 7. Plan for Sora's voice (needs Mat's own KH2 copy)
1. ~70 Sora clips → .at3 (ATRAC3; needs an encoder — not set up yet) named so_battle_NN, rows in
   voice_load_P_SEV120.bin with the conditions above, subtitles via voice_text.py at free ids.
2. Grunts → replace slots of voice_P_SEV120_00.scd (sscf.py). Keyblade sounds → #33's `snd_` slots (map above).
3. Lines for other fighters vs Sora: new rows (condition 2, value 33) in their VOLD files; audio = one of their
   existing clips, or KH2 clips of the same actors (Cloud and Tifa have the same English voices in KH2).
   Replies (condition 6) make real back-and-forth intros.
4. Budget: PACKAGE_INFO has room for ~120 more new files in total.

## 8. Sora's battle voice — test 50 `dumps/ULUS10566-test50-voice.iso` ✅ (2026-10-13)
- Cloud's voice bank transcribed (dumps/voice_sora/cloud_text.tsv): 41 sounds = grunts (0-3, 6, 10-13, 19-21, 33-37),
  hurt (4, 5, 22), lines: 7 "See ya!", 15 "Stars, rain down!", 16 "It's not your day.", 17 "No hard feelings.",
  18 "This ends here!", 23 "GO!", 25 "There!", 27 "Over here!", 28 "You're gone!", 29 "BURN!", 30 "Give me
  strength!", 31 "Breaking my limit!", 32 "This is it.", 39+40 "This... is it?!", 42 "I need this power!". 38/41 empty.
- Mapping slot → Sora KH2 clip: `tools/voice/sora_battle_voice.txt` (e.g. 15 → "LIGHT!", 18 → "It's over!",
  29 → "FIRE!", 30 → "Give me strength!"). Clips converted with ffmpeg (16 kHz mono, silence trimmed, peak 31000).
- `sscf.py rebuild BANK MAP OUT` = new: each listed sound at its own length, data re-laid out, bank size updated
  (bank 214,224 → 170,144 bytes). pkg_put → voice/EN/battle/voice_P_SEV120_00.scd.
- Proof: the bank in RAM (0x0940B9C0, 170,144 bytes) is byte-identical to ours; `tools/scripts/ppsoundwatch.py PORT
  SECS` (CPU breakpoint 0x08991A70 + attack presses on one connection) logged Sora's bank playing slots 19, 1, 2 while
  attacking. (Speech-to-text on game audio failed — music masks the voice.)
- Not done: Keyblade swing/hit sounds (fighter snd_ bank, kh2_export/sfx 44 unlabeled se500 sounds) — needs labels.

## ATRAC3 encoder (2026-10-13) ✅ (not yet tested in game)
Game spoken-line clips (voice/EN/battle/*.at3): RIFF ATRAC3, mono, 44100 Hz, 192-byte frames (~66 kbps).
`tools/atracdenc/atracdenc` (atracdenc + mono.patch, see tools/atracdenc/README.md) makes the same format with
ATRAC3_MONO=1. Decoded by ffmpeg fine; speech-band spectrogram correlation 0.98 with the source.
In game (test 64 `dumps/ULUS10566-test64-lines.iso`, smoke test map tools/voice/sora_lines_smoketest.txt =
KH2 battle shouts on #33's intro/win/loss clips): after Sora won, the WHOLE new so_battle_29.at3 ("Yeah!", 4,492 B)
was found byte-identical in RAM at 0x09568960 → the game loads and plays our encoded clips; no hang.
Tool: `tools/scripts/spot33_lines.py ISO MAP` (CLIP WAV SUBTITLE lines; `@LINE_ID CLIP` re-points a row).
How to check a clip played: dump RAM after the line, search a 64-byte piece of the clip's data (skip silent-frame
false hits at 0x08800000). Recording audio: route ONLY PPSSPP's stream to a null sink (pactl load-module
module-null-sink + move-sink-input; Chromium shares the speaker) and move it back after; speech-to-text and
spectrogram matching can't pick voices out of the battle music. Never `pkill -f` a pattern that is in your own
command line (it killed the shell before the routing was restored).
Story lines: 1,183 KH2 Sora event clips (`*sr.win32.scd`, speaker code sr; do = Donald, go = Goofy) decoded with
tools/vgmstream/vgmstream-cli to dumps/kh2story/wav/, being transcribed to dumps/kh2story/sora_story_text.tsv.

## Sora's spoken lines from KH2 story voices (test 74 `dumps/ULUS10566-test74-story.iso`, 2026-10-13) ✅
- 1,183 Sora event clips (speaker code `sr`) → WAV (tools/vgmstream) → text (transcribe.py, faster-whisper small.en)
  = dumps/kh2story/sora_story_text.tsv. Picked lines → tools/voice/sora_lines.txt (CLIP WAV SUBTITLE), applied by
  spot33_lines.py (build_sora.sh LINES=…, default this file):
  intros "Only one way to find out.", "Then, let's finish it.", "Good, now we can settle this!", "Better think
  again!", "Our hearts are connected.", "I bet you can't even fight!" …; vs Cloud (cond 2/13) "Long time, no see!",
  vs Squall (2/15) "Leon, come on!"; wins "All in a day's work!", "Don't mess with street rats.", "We did it!",
  "Oh wow! … Hooray!" …; losses "We can't win.", "No fair!", "It's no use! We can't beat them!" …
  Other vs-specific / reply rows reuse the intro lines. Cloud's shared UP09_* clips: rows 1047/1048 re-pointed to
  so_battle_23/24.
- Seen in game: "DEFEATED… No fair!" subtitle at a loss (dumps/screens/end74/s_013.png). Intro lines are hard to
  catch on camera (battle starts fast).
- Ideas: vs-specific lines for more KH-related fighters (Sephiroth, Tifa have no Sora story lines in KH2 —
  maybe from other clips), trim long clips.

## ❗ Spoken lines broken in tests 64–80 → fixed in test 81 (2026-10-13)
- Mat: "cutscene voice lines" (intro/win/loss dialogue) didn't play — for everyone in fights with #33 (grunts fine).
- PPSSPP log (`PPLOG=file PPARGS=-d tools/scripts/go_battle.sh ISO`): `SCE_ERROR_ATRAC_BAD_CODEC_PARAMS=
  sceAtracSetDataAndGetID` for every new so_battle_*.at3. Cause: atracdenc writes fact end-sample = frames×1024;
  sceAtrac skips 1093 samples first and needs end + 1093 ≤ frames×1024 (Sony files: end ≈ frames×1024 − 2084).
  Fix in spot33_lines.at3(): pad 2048 silent samples, write the real sample count into fact. Test 81: no ATRAC
  errors, new clips accepted (e.g. 0x508C bytes).
- Sound bank ids: SSCF +0x12 u16 = bank id, per fighter base×1000 (+0 snd_, +100 voice, +500/+600 assist):
  WoL 10, Terra 20, Cloud 22, Sephiroth 23, Squall 24, Tidus 28 (= 8 + 2·FF number, villain +1). #33's banks are
  Cloud's copies → 22000/22100 (clash only when Cloud is in the same fight: Mat heard no Braver weapon sound).
  Changing only the bank headers (old spot33_soundids.py, test 82) silenced Sora completely. **Solved
  (2026-10-14) → notes/sound-bank-ids.md**: ids are absolute DATA in #33's own files (p_se 8 ops 0x03/0x11/0x15,
  effe fxseb, chrp +0x7c..+0x88); spot33_soundids.py now moves all of them to 219000/219100. Not run in game yet.

## Battle voice slots by action (test 85/86, `tools/scripts/ppsoundseq.py PORT STEP…`, 2026-10-13)
- Logged live (bank id 22100 = #33's voice bank): EX Mode start (R+Square, gauge full) → slot 30; block (R) → slot 37
  every time (+ snd_ 22000 slot 21); KO (finishing blow received) → slot 4 (only then).
- Mat's choices: EX Mode = "LIGHT!" (tt0_sora_010), block = "Defense!" (tt0_sora_017), KO = "No way!" (story clip
  dc10806sr; KH2 has no "can't go on" line in any of the 15 Sora battle banks — all 472 clips transcribed in
  dumps/kh2battle/sora_battle_text.tsv: same ~31 shouts per world + partner names, plus "Ugh!" wi0_sora_31).
  Fight shouts stay HA!/Yeah!/Back off!/HUH…; never partner names (Aladdin, Goofy, Donald… — Mat).
- Bank map: dumps/voice_sora/map.txt (copy: tools/voice/sora_battle_voice_map.txt); sources tools/voice/sora_battle_voice.txt.
  Clips: 16 kHz mono, silence trimmed, peak 31000. Test 86 bank 181,312 B.
- Intro "That's what you think!" → "Come on!" (hb41703sr) (Mat).
- Win lines (Mat: full sentences like "Don't mess with street rats."): test 109 = 8 sentence lines (see tools/voice/sora_lines.txt so_battle_26..33).
- Mat rejected win lines bb20906sr, he13910sr, eh11311sr → ca20912sr, lk12202sr, lk12213sr (test 110).

## Hurt voices (test 115 log, 2026-10-14, `OWNER=33 ppsoundwatch.py PORT SECS EVERY BUTTON` prints #33's motion too)
#33 voice bank = the 181,312 B SSCF. Getting HIT plays slots **0/1** (air/ground hit 560/561, combo hit 600),
**2** (blown away 700/750), **3** (702 get up), **5** (recoil 901/911), **4** only at the KO blow. Attacks use
7, 13, 19–24, 26, 27 (e.g. 19 = 10000 NEAR1, 7 = 10020, 22 = 10030). Old map had attack shouts (HA!/HUH) on 0–2 and
"Gah!" (KH2 hurt cry) on attack slot 22 → Mat heard a hurt cry while attacking. Test 116: 0 Ugh! (wi0_sora_31),
1 Gah! (wi0_sora_29), 2 Gah! (tt0_sora_001), 5 Ugh!, 22 HA! (wi0_sora_021). Bank 184,144 B.
- Test 116 log while Mat played a chase: blown away 700 → slot 2; **dodge in a chase = motion 822 → slot 36**.
  Slot 36 was wi0_sora_001 ("YEAH!" in the transcript, but 0.94 s long = KH2 KO groan; Mat: "sounded like a death
  sound"). → tt0_sora_020 "HUH" (test 117). Lesson: wi0 bank order differs from tt0; check clip LENGTH, not only text.

## Title call ("Square Enix presents… Dissidia Duodecim") = picked by the PSP DATE (vanilla) — 2026-10-16
Mat: "only Kefka says it". Not a mod bug. OVL_MENU_APP FUN_089deaa8 plays voice/JP/event/title_call/<name> (+ a second
"_DDD" half), index from FUN_089dfd6c: needs a save flag (+0x1de68 & 0x100) and a sane clock, then
**day of month → table DAT_089e07d8 (31 words)** into the 34-name list at 0x089e08b0 (wo ga fn em on cd ce gb ca bu ed gi
ti cf cl sf tf la sq am zi kj td yu je pr sh va gs li co ch na ae). Day 16 and 26 = cf = Kefka; 17 Tifa, 18 Laguna…
Overrides: weekday/month combos (gi, pr, gs, ae), a save-data date (co), 5 % random (ch), a flag (na). Otherwise −1 = no
voice. For a Sora title call: add a file and point a table entry (or the whole table) at it.

## Approved voices vs Sora — test337 `dumps/ULUS10566-test337-voices.iso` (2026-10-18, Claude voice helper)
Source: Codex package `tools/voice/20261018-approved-voices/` (Mat-approved, 37 files). Tool:
`tools/scripts/spot33_vsvoices.py ISO [--dry] [--no-title]` (build_sora.sh: right after spot33_lines). test337 =
test336-hpproj (69965250…) + this script only; sha256 `1026928f22cff6fc882dd8bae9c7232cbdf4cac76d0441d59a598fe6878bbd3c`.
Re-run on its own output = no change (encoder deterministic, every site "already"). Static checks 28 PASS / 24 INFO.
- **How the game picks the intro line** (battle overlay FUN_08b00b2c ← FUN_08b0d7f4 ← FUN_08b0e40c): it searches the
  fighter's OWN loose `voice/EN/voice_load_<key>.bin` (loaded at fighter+0xd4). Order: reply (cond 6, value = the
  other line id) when a line id is passed; series/team modes cond 8 / cond 7 (value 0 = last battle of the series,
  1 = not last — no opponent check); else if the battle's encounter (`encounter/*.enc` +8) is non-zero → **cond 2,
  value = opponent owner byte** (*(fighter+0x5a4) = chrp row byte 0 → 33 for Sora), otherwise cond 0/3 by strength.
  Up to 8 matches, random pick; no match → cond 5 (general random). So a vs-33 row plays on EVERY "vs-specific"
  intro against Sora (natives had none → general lines). Row bytes: +0x13 moment high byte, +0x14 cond, +0x16 value.
- `voice/EN/voice_load_parameter.mpk` = a second copy of every list (lower-case `voice_load_p_<key>.bin`, no Sora)
  read only by the Museum (menu FUN_08a384ac). Battle never reads it → left unchanged.
- **Owner check**: P_GST110 = **Prishe = 29**, P_GST120 = **Vaan = 30** (mirror rows + "The mighty Prishe is here!").
  The Codex manifest (and voice_catalog.py NAMES) have 29/30 swapped — the script maps by voice key, not manifest owner.
- **Rows added** (moment 0x0046, cond 2, value 33; clip `<prefix>_vs_sora`, line id 1110 + owner):
  wo 1111, ga 1112, fn 1113, em 1114, on 1115, cd 1116, ce 1117, gb 1118, bu 1119, ed 1120, ti 1121, cf 1122,
  cl 1123, sf 1124, sq 1125, am 1126, zi 1127, kj 1128, td 1129, je 1130, sh 1131, gs 1132, gi 1135, tf 1136,
  la 1137, yu 1138, pr 1139, va 1140; Lightning's test-28 row **1100** re-pointed li_battle_93 ("My blade'll fix
  this.", shared vanilla clip, untouched) → `li_vs_sora` (subtitle unchanged "A new face? Fine."; Sora's reply 1101
  "Come on!" still answers it); **Sora mirror** = Sora's own row `so_vs_sora` 1143 cond 2/33. 1133 (Chaos) / 1134
  (Kain) unused (excluded). No other row changed; no Sora reply rows added (native: only 30 of 1024 cond-2 lines
  have a reply). Subtitles = manifest text; display-only normalisation: curly → straight apostrophes (Bartz),
  Gilgamesh caps → sentence case, "Keyblade???" → "...Another... Keyblade?", "light ... will" → "light... will".
- **Title call**: Sora = new index 34 (`title_so_SQE.at3` "Square. Enix." / `title_so_DDD.at3` "Dissidia Duodecim"
  in voice/EN/event/title_call/; the code asks for voice/JP/… and the loader maps it to EN). Menu overlay:
  0x089DEC04 index bound 0x22→0x23; 0x089DECD0 DDD base 0x0938→0x0504; new 35-word DDD table at 0x089E0504 + DDD strings
  re-packed (13 B each) in 0x089E0504..0x089E06F0 and the old DDD table words 0x089E093C..0x089E09BF; SQE[34] =
  0x089E0938. Only the two table loads point at those strings (scanned the whole overlay segment 0x089DD4C0..
  0x08B59258). **Days 25 and 29** → Sora (were Exdeath 15/25 and Kuja 19/29; both keep one day; Kefka keeps 16/26).
  All 34 native title calls still resolve to their files.
- Audio: originals (24 kHz, SHA-256 = manifest) → spot33_lines.at3() unchanged (16 kHz derivatives not used: they
  would cut everything above 8 kHz). Decode check per clip: ATRAC3 mono 44.1 kHz 192-B frames, fact = source
  samples, speech-band spectrogram corr 0.96–0.99 vs source, level change ≤ 0.02 dB, no clipping. Sizes 14–42 KB;
  **Shantotto 42,316 B > native max 38,092 B** (ed_battle_58). 32 new PACKAGE entries (11147 → 11179, ~74 left).
- **Loudness (diagnostic, NOT changed)**: active-speech RMS of the new lines is **~11–14 dB below** each speaker's
  native vs-lines (e.g. WoL −25.5 vs −12.4 dBFS; Lightning −8.5 dB, Vaan −7.6 dB best). Expect them to sound quiet in
  battle. A fix needs Mat's OK: separately named gain derivatives (peaks reach −3.3 dBFS for Exdeath/Jecht, so
  plain gain can't close the gap without a limiter).
- **Held**: Cosmos (owner 34 P_ORG800 has no voice_load file; not a battle fighter), Aerith (assist-only in vanilla;
  owner 33 is Sora now; assists have no voice_load list) — no clean native route. Sora-vs-Chaos round 3: no native
  selector can say "vs Chaos AND final round" (cond 7/8 series rows ignore the opponent; Sora isn't in story mode) →
  HOLD; so_battle_12 untouched. Alternates (Cecil option3, Jecht ending17) kept in the package, not inserted.
- Long subtitles: Shantotto 67 chars, Terra 63, Prishe 63 (native max 61) → check they fit on screen.
- **WHO speaks at the intro (2026-10-18, after Claude's test337 runtime: P1 Lightning vs CPU Sora ×6 → Lightning's
  line never played; first intro showed Sora's vs-Lightning row "Don't worry, we'll take care of them.")**:
  the intro shot comes from the stage's encounter file `<map>.enc` inside `map/maparc_<map>_1.mpk` (Order's Sanctuary
  = org00). Header "ENCO", counts at +8..+0x1c; last section = shots (16 B: +0 id, +6 script group, +8 kind 1 = vs /
  0 = general, +0xc must be 0 for Quick Battle); script commands 0x24 B grouped by first short; command +0x18 int =
  event type, +0x1c = parameter; **event 10 = voice, parameter = side** (handler table 0x08B11F7C, FUN_08b11114 →
  FUN_08b0d938 plays the line already chosen for that side). Shot choice (battle overlay FUN_08b11988 → FUN_08b0d5b4):
  random among the stage's shots of the kind byte 1 of the battle setup (DAT_09AFDE50+1; 2 = any) allows.
  **Every Quick Battle stage (one00…thn00, org00/50, vni/vsi/vth/vtw00): vs shots have ONE voice event = side 1;
  general shots have ONE voice event = side 0.** So a vs-specific line is spoken only by the SECOND fighter (side 1 =
  CPU / P2 slot) and only on a vs shot (org00: 1 vs + 1 general → ~50 % per new battle; Retry skips the intro).
  Side 0 only ever says general lines (cond 0/3 → 5); a reply (cond 6) needs the caller's line id (DAT_09AFD83C,
  normally -1). Consequence: the vs-Sora openings play with **Sora as P1 and the speaker as CPU/P2**; the mirror
  line plays from the side-1 Sora; with P1 = speaker vs CPU Sora, Sora's own vs-<speaker> row plays instead (what
  the test saw). Test 108's "A new face? Fine." = Mat as Sora vs CPU Lightning. No data change needed; making side 0
  speak vs lines too would mean editing every stage's intro scripts for every matchup (not done).
- **LOUDER — test338 `dumps/ULUS10566-test338-voicesloud.iso` (Mat "Raise them please")**: = test336 + spot33_vsvoices.py
  with GAIN_MODE=match (now the default; GAIN_MODE=off = byte-identical test337 clips). Per clip: target = median
  K-weighted integrated loudness (BS.1770-style, gated) of that speaker's own native battle-start clips decoded from
  the disc (47-57 clips each; mirror = Sora's 55 so_battle lines; title halves = all 65 native title_call files,
  -15.4); one static gain + look-ahead peak limiter (5 ms look-ahead/attack ramp, 80 ms release, ceiling -1.5 dBFS,
  steps down if the decoded peak passes -1 dBFS); aim measured on the 0-11.5 kHz band the codec keeps; gentleness cap
  LIM_MED_MAX=6 dB median limiting on speech (env; 99 = no cap); GAIN_TRIM=dB shifts every target. Same sample count
  (timing/pauses/pitch untouched). Decode checks: peak ≤ -1 dBFS, no clipped samples, codec level vs processed PCM
  < 1 dB, frame spectral-shape correlation vs the approved original 0.92-0.95.
  Result (decoded loudness vs target, was 11-14 dB under): 26 of 32 within 1 dB; capped (gentleness) Jecht -1.8,
  Sora mirror -1.3, Bartz/Cloud/Squall -1.0, Kuja -0.9, Prishe -0.9, Onion Knight -0.8, Yuna -0.7 dB. Limiter work:
  median 0.1-6.0 dB on speech; heaviest (median 6 dB): WoL, Onion Knight, Bartz, Kefka, Cloud, Squall, Kuja, Jecht,
  Yuna, Prishe, Sora mirror → listen to these for density/crunch first.
- **Runtime 2026-10-18T10:32:07Z (Claude, test338): vs-Sora intro lines PLAY — trace shows PLAY clip=li_vs_sora on 3/7 intros (cond 2, value 33); other intros = general lines. PASS.**

## Sora's own matchup lines + Kain — test340 `dumps/ULUS10566-test340-sorasvs.iso` (2026-10-18T13:48:17Z, Claude)
Codex updated the approved package in place (tools/voice/20261018-approved-voices, 12:32 UTC: 73 files) — Kain take17
approved, 33 "Sora vs <opponent>" lines approved (Sora = speaker 33), Chaos main/alternate approved but routing HOLD.
The old guard "Kain must stay excluded" stopped build_sora.sh (found by the P1.0 R0 builds). spot33_vsvoices.py now:
- Kain = speaker (24, P_FOR110, prefix ca): row ca_vs_sora id 1134 cond 2 value 33.
- Sora speaking: Sora's ONE existing cond-2 row per opponent (a cloned generic KH2 clip so_battle_41..72, ids 1015..1046)
  is re-pointed to so_vs_<opp> id 1150+owner (1151..1182). 29 lines: owners 2-22, 25-32 (Feral Chaos 32 = so_vs_fc).
  Native pattern kept (1 row per opponent); the KH2 clips still play in general intros. Opponent owners from
  SPEAKERS (manifest Vaan/Prishe owners swapped: Prishe = 29 P_GST110, Vaan = 30 P_GST120).
  These play when Sora is the CPU / side 1 (P1 = opponent vs CPU Sora), see "WHO speaks" above.
- Not written: WoL's Sora line (not approved yet → WoL keeps so_battle_41 generic row), Kain's Sora line (none),
  vs Chaos (23) row stays generic; HOLD: Chaos's own line + alt take22, Sora vs Chaos round 1/2/3, Aerith assist,
  Cosmos story.
- Bug fixed: Tidus's vs-Sora id was 1129, but EVERY fighter (Sora too) has a native reply row cond 6 value 1129 (a line
  no chrp voice list owns) → Sora replied "Don't worry, we'll take care of them." to Tidus. Moved to 1144 (old
  subtitle 1129 dropped); the free-id check now also counts reply targets.
- Same level matching (target = Sora's so_battle median); all 30 new clips decode-checked (spec corr 0.958-0.981).
test340 = test339 + spot33_vsvoices (new) + spot33_installfix (30 new rows → tier 0). Runtime: not tested yet.
- test342 `dumps/ULUS10566-test342-wol.iso` = test341 (NEW-tag fix) + Codex's WoL Sora line (approved 13:40 UTC,
  manifest sha 65c4bbdb…): Sora vs 1 = so_vs_wo id 1151 → 30 Sora matchup lines. spot33_vsvoices re-run on test340 now
  = no-op except the new WoL clip (Sora loudness target fixed to include the re-pointed so_battle_41..72; free-id check
  listener-aware — Chaos's reply row to 1128 (Kuja's id) is harmless).
- Runtime attempt 2026-10-18T14:29:42Z (Claude, test340, disposable profile, P1 Lightning vs CPU Sora, org00): 13 traced
  intros all = side 0 general (KIND a1=1, cond 3 → li_battle_93..101); Sora's side-1 vs line never chosen. P1 HUD showed
  "COM" (auto-play got toggled by the input loop) — likely forces general shots. Setup byte DAT_09AFDE50+1 was 0
  each battle; poking 1 or 2 before load changed nothing (re-set at battle init). → runtime check left to Mat
  (normal P1 vs CPU Sora, several new battles from Battle Setup, not Retry).
- **Final package adopted (2026-10-18T16:02:28Z):** spot33_vsvoices.py PKG = tools/voice/20261018-1408-approved-voices-complete (75 files;
  corrected Prishe 29 / Vaan 30 both directions; final Sora→Kain take5). New checks: speaker manifest owner = disc owner,
  Sora-line opponent_owner = disc owner. Dry run on test342: 70 clips "already" (audio identical), 1 new: Sora vs 24
  so_vs_ca id 1174 (row so_battle_45 re-pointed) → 31 Sora matchup lines (all opponents 1-32 except Chaos 23).
  test343 = dumps/ULUS10566-test343-final-voices.iso = test342 + that line. HOLD unchanged: Chaos (own line + rounds
  1/2/3), Aerith assist, Cosmos story, alternates.
- **Runtime 2026-10-18T16:25:23Z (Claude, test343, disposable profile + copy of a 100 % save):** on this save
  vs shots happen (KIND a1=0; the low-progress save only ever gave a1=1 general shots). P1 Sora vs CPU Lightning →
  PLAY li_vs_sora (Lightning's approved line to Sora). P1 Lightning vs CPU Sora → intro 2 PLAY **so_vs_li** (Sora's new
  line to Lightning); intro 1 = general (li_battle_94). Both directions of the new matchup lines confirmed in-game.
  Other test343 checks on that save: Museum → Character Files → Sora (text + KH2 tag) and 3D viewer OK; Records list
  works (Sora absent with 0 battles); Quick Battle NEW tag shown once then cleared after leaving the grid; Sora Lv42 on
  this save (old dev data → RR-03 catch-up matters). Jukebox lost its gold star (KH2 tracks unbought) → RR-08 note.
