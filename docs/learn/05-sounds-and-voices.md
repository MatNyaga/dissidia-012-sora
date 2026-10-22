# Chapter 5 — Sounds and voices

**The big idea:** sounds live in **jukeboxes** (sound banks). Each jukebox has numbered
**slots**, one sound per slot. When the game wants a sound, it asks for one big number, for
example 2,200,021. The game finds the jukebox whose number range holds 2,200,021 and plays the
slot inside it. Sora started with copies of Cloud's jukeboxes, so at first Sora and Cloud had
the *same* numbers and stole each other's sounds.

---

## 5.1 The four kinds of sound

| kind | where it lives | example |
|---|---|---|
| weapon / body sounds | chunk `snd_` inside the battle file `obj/p_sev120.objx` | Keyblade swing, hit, jump |
| voice grunts and shouts | `voice/EN/battle/voice_P_SEV120_00.scd` | "HA!", "Ugh!", "LIGHT!" |
| spoken lines | `voice/EN/battle/so_battle_NN.at3` + a line list + subtitles | "Don't mess with street rats." |
| effect sounds | the `FXSE` table inside the effects chunk `effe` | the boom of an explosion effect |

Plus a **shared battle bank** that every fight loads (Break sound, some system sounds).

There are no Japanese voices on the US disc (only `voice/EN`).

---

## 5.2 The SSCF sound bank (the jukebox)

Both `snd_` and `voice_*_00.scd` are **SSCF** banks:

```
header (0x20 bytes):  "SSCF", …, u32 bank size @8, u32 sound count @0xC,
                      u16 @0x10, u16 @0x12, u32 @0x14   ← these set the bank's BASE number
count × 32-byte slot entries: data offset, data size, sample rate, playback settings
sound data: PSP ADPCM ("VAG"), 16-byte blocks of 28 samples
```

**ADPCM** is a simple way to squeeze sound to about a quarter of its size. Our tool
`tools/scripts/sscf.py` can list a bank, save slots as WAV, replace a slot (keeping its size,
so the bank never grows), and **rebuild** a bank with sounds of new lengths.

### How a slot is found (the base number)

When the bank loads, the game works out its **base** from the header:
`base = h12 × 100` (the u16 at +0x12), or, if that is 0 and the u32 at +0x14 is big,
`base = h14 × 100`. The bank answers every id from `base` to `base + count`.

A script asks for **base + slot**, written as one absolute number. Cloud:

| bank | header value | ids it answers |
|---|---|---|
| Cloud's `snd_` | 22000 | 2,200,000 + slot |
| Cloud's voice bank | 22100 | 2,210,000 + slot |
| (assist versions get +50,000 at run time) | | |

The pattern: fighters use 8 + 2 × (FF number), villains +1. The 012 newcomers (owners 24–32)
use 210000–218000. **Owner 33's numbers 219000 and 219100 were unused** — the developers' own
reserved slot for #33's banks (Aerith's assist uses 219500/219600).

### Where the absolute ids are written

There is **no table** that turns an owner number into a sound id. The full number is plain data
inside the fighter's own files:

| where | what |
|---|---|
| battle file scripts, one-shot op **0x03** and op **0x11** | weapon/body sounds (2200000 + slot) |
| battle file scripts, one-shot op **0x15** | voice (2210000 + slot) |
| `effe` → `p_sev100.fxseb` (FXSE rows) | effect sounds |
| `system.bin` `chrp` row +0x7c / +0x80 / +0x84 / +0x88 | KO voice, EX Mode voice, … |
| battle overlay, Cloud's Omnislash code | two numbers baked into the code: 2200053, 2200054 |

---

## 5.3 The sound-id clash and its fix

**Story:**
- **Test 80:** in Cloud vs Sora, Cloud's Braver weapon sound came out wrong. Both banks
  answered 2,200,000+; the first one registered won.
- **Test 82:** we changed only the two bank **headers** to new numbers. Result: **Sora went
  completely silent.** The banks moved, but every script still asked for the old numbers, and
  nothing answered. Lesson: the header and every request must change *together*.
- **2026-10-14:** `tools/scripts/spot33_soundids.py` moves **everything at once**: both bank
  headers → 219000/219100, every script op 0x03/0x11/0x15, every FXSE row, and the four `chrp`
  voice ids. A dry run on test 132 listed 326 writes. **[PROVEN]** test 133: in Cloud vs Sora
  both fighters' banks play.

**Rule: run `spot33_soundids.py` LAST in every build.** Any step that copies a Cloud script
block into Sora's file brings Cloud's old numbers back; soundids fixes them. All the other
sound tools work with either base (2200000 before, 21900000 after).

**Leftover [OPEN]:** the two Omnislash sounds are numbers inside Cloud's *code*. For Sora they
only play if Cloud is in the fight. Fixing them needs a small code hook (designed, not built).

---

## 5.4 Which slot is which sound

The bank only has numbers, not names. Two ways we found out:

1. **Beep test (test 25):** replaced every slot of #33's bank with a 1,000 Hz beep, recorded
   the game audio, counted beeps (`tone_check.py`): beep disc 32 tone windows, normal disc 0.
   Proved the bank is used, but not which slot is which.
2. **Breakpoint (test 26 and later):** the game's sound player runs the instruction at
   `0x08991A70` (a load from the sound slot) once per sound, and register `s0` points at the slot being played.
   A **CPU breakpoint** there (Chapter 9) logs `slot = (s0 − bank − 0x20) / 32` while we press
   moves. Tools: `ppslotwatch.py`, `ppsoundwatch.py`, `ppsoundseq.py`.

(Listening to recordings for tones failed: the battle music hides them.)

### Sora's own sound slots (added after Cloud's 0–69)

`tools/scripts/spot33_sfx.py` **appends** new slots to the `snd_` bank. Scripts play them with
one-shot op 0x03.

| slots | what |
|---|---|
| 0–69 | Cloud's copies (unused ones now silent, see 5.6) |
| 70–72 | Explosion start / orb / blast |
| 73–76 | Firaga cast / flash / fly / explode |
| 77–80 | Thundaga / Blizzaga |
| 81–82 | reserved for Reflect |
| 83–95 | Keyblade swings, hits, finishers, EX Burst (Codex's set, Mat approved) |
| **96** | next free |

`spot33_weaponsfx.py` wires them in: swing slots 83/84/87 cycle per hit (so a chain doesn't
sound the same every time), 88 is the heavy last hit, 89–95 are finisher sounds at KH2's
own ticks, 85/86 are contact hit sounds on the hit-mark effects.

**[PROVEN]** Mat: Keyblade sounds loud enough (test209). Logged in game: Explosion plays 70,
then 71 five times, then 72.

### KH2's own sound ids

KH2 sound id = bank × 1000 + sound number (999042 = bank se999, sound 42).
`tools/scripts/kh2_se.py` maps ids to files. **[GUESS → corrected]** We first guessed
999038 = `se999_038.wav`; the tool later said it is `se999_036` (sound numbers are 1-based).
Mat liked the `_038` pick by ear, so we kept it. Ears win.

---

## 5.5 Effect sounds (FXSE)

Some sounds hang off **effects**, not scripts. The FXSE table has, per effect leaf, up to 16
records `{base, slot, frame, ?, flags}`. Flags 0 = play once at that frame, 4 = loop while the
effect lives, 2 = another bank.

- The **Cloud vs Sora effects clash** (Chapter 6) also killed these: Cloud's Climhazzard
  weapon-effect sound was missing because Cloud's effects didn't load at all.
- Firaga's fireball looped Cloud's flying sound on top of our KH2 one → that FXSE record was
  muted (filled with zeros).

---

## 5.6 The memory limit story: the vanishing Break sound

**What happened (2026-10-15 evening):** after the Keyblade sounds went in, Mat noticed on test
209/210: **the BREAK sound was gone, and the win voice line was gone.**

**Why:** Sora's `snd_` bank had grown from 538 KB to 606 KB. In a **Sora vs Sora** fight the
game loads *two* copies of it. With both, it no longer loaded a 436,580-byte **shared** battle
sound bank — the one that holds the Break sound (its slots 96 and 57). The win line went
missing at the same time. **[GUESS]** both are victims of the same memory shortage.
The Break part was proved with a breakpoint logger: test204 and test211 play that bank at the Break; test210 had
no such bank loaded at all.

**Fix:** `tools/scripts/spot33_sndtrim.py` (runs just before soundids). Every Cloud slot
nothing references any more becomes a 32-byte silent sample → bank 498,528 bytes (smaller than
test204's 538,832). **[PROVEN]** test211: Break sound back, win line "Don't mess with street
rats." back, loss line back, in a mirror match.

**Rule: keep Sora's `snd_` bank at or under ~540 KB.** It is shown in `codex/START-HERE.md` §5.

---

## 5.7 Voice grunts (the voice bank)

- The voice key is `chrp` +0x74 = `P_SEV120` → files `voice_P_SEV120_00.scd` and
  `voice_load_P_SEV120.bin`.
- Cloud's 41 voice sounds were transcribed: grunts, hurt cries, and lines like "BURN!".
  Mapping slot → Sora's KH2 clip: `tools/voice/sora_battle_voice.txt`. Clips are converted to
  16 kHz mono, silence trimmed. `sscf.py rebuild` makes a new bank at the new lengths.
- **[PROVEN]** The bank in memory was byte-identical to ours, and the logger saw Sora's slots
  play while attacking (test 50).

Slot meanings found by logging (`ppsoundwatch.py` with `OWNER=33`):

| slot | when | Sora's clip |
|---|---|---|
| 0 / 1 | getting hit | "Ugh!" / "Gah!" |
| 2 | blown away | "Gah!" |
| 3 | getting up | |
| 4 | **KO** (only then) | "No way!" |
| 5 | recoil | "Ugh!" |
| 15 | (Thundaga used it) | "LIGHT!" |
| 30 | EX Mode start | "LIGHT!" |
| 36 | dodge in a chase | "HUH" |
| 37 | block | "Defense!" |
| 7, 13, 19–27 | attacks | HA!, Yeah!, Back off! … |

Lessons:
- At first the hurt slots had attack shouts, and an attack slot had a hurt cry → Mat heard
  "Gah!" while attacking. Remapped (test 116).
- Slot 36 was labelled "YEAH!" in a transcript, but the clip was 0.94 s long — really a KO
  groan. Mat: "sounded like a death sound". **Lesson: KH2 banks of different worlds are in
  different orders. Check the clip's length, not only the transcript.**
- Mat's rule: **never use partner names** (Donald, Goofy, Aladdin…) in Sora's shouts.
- `spot33_voicex.py` appends "Freeze!" (Blizzaga) and "Thunder!" (Thundaga) as new voice slots
  (Mat: "Sora says fire when he's doing blizzard").

---

## 5.8 Spoken lines: the line list, subtitles, and the .at3 files

### The line list (VOLD)

`voice/EN/voice_load_P_SEV120.bin` is a list of 24-byte rows:
`clip name, line id, moment, condition, value`.

| moment | when |
|---|---|
| 0x0046 | battle start |
| 0x0146 | win |
| 0x0246 | loss |

| condition | meaning |
|---|---|
| 0 | general line (value = how hard the fight is) |
| 5 | general, random pick |
| 2 | **vs a specific opponent** (value = their owner number) |
| 6 | **reply** to another fighter's line (value = that line's id) — how intro conversations work |
| 8 | team battle |

The game picks **randomly** among all rows that fit, so a new line only plays sometimes.
Line ids 0–1205 are free; 1206–3260 are used. Full catalogue of every fighter's lines with
their real subtitles: `dumps/voice_catalog/voice_lines.md`.

### Subtitles

All subtitles are one file: `general_archive/field/EN/field_lang.bin` → `battle_voice_name.bin`
("OFF4"). The text is scrambled with **XOR** (each byte mixed with a byte from a 32-byte key).

**Lesson (test 28):** the first guess said the key position depends on the entry's place in
the file. Mat saw **garbage subtitles**. The real rule uses the **line id**:
byte j of line L is XORed with `KEY[(2·L + 20 + j) % 32]`. Found by comparing the disc file
with the decoded copy in RAM (the game decodes it on load). Re-encoding the original now gives
byte-identical output. Tool: `voice_text.py`.

### The .at3 clips and the ATRAC3 bug

Spoken lines are **ATRAC3** files (Sony's sound format) in a RIFF wrapper: mono, 44,100 Hz.
We had no encoder, so we built `tools/atracdenc/atracdenc` with a small mono patch.

**The bug (tests 64–80):** Mat: the cutscene-style lines (intro/win/loss) didn't play — and
not just Sora's: **everyone's**, in any fight with #33. Grunts were fine.
A PPSSPP log showed `SCE_ERROR_ATRAC_BAD_CODEC_PARAMS` for every new clip. Cause: the encoder
wrote an "end sample" number that was too big. The PSP's ATRAC player skips 1,093 samples first
and needs `end + 1093 ≤ frames × 1024`. Fix in `spot33_lines.py`: pad 2,048 silent samples and
write the real count. **[PROVEN]** test 81: no errors, lines play.

### Where Sora's lines come from

- 1,183 KH2 **story** clips of Sora (speaker code `sr`) were decoded with vgmstream and
  transcribed offline (faster-whisper) into `dumps/kh2story/sora_story_text.tsv`.
- Picked lines → `tools/voice/sora_lines.txt` (format: `CLIP WAV SUBTITLE`). Applied by
  `spot33_lines.py`. Intros like "Only one way to find out.", wins like "Don't mess with street
  rats.", losses like "No fair!". Special lines vs Cloud ("Long time, no see!") and vs Squall
  ("Leon, come on!").
- `!LINE` entries change **other** fighters' lines about Sora, e.g. Lightning's vs-#33 subtitle
  "A new face? Fine."
- **[OPEN]** Mat will send voice lines for every character meeting Sora.

### How to check a clip really played

Dump the RAM right after the line and search for a 64-byte piece of the clip's data. Test 64:
the whole new `so_battle_29.at3` was found byte-identical in RAM → the game loaded our clip.

---

## 5.9 Recording game audio (and a warning)

- Route **only** PPSSPP's sound stream to a separate "null sink" and record that (the browser
  shares the speakers otherwise). Move it back afterwards.
- Never `pkill -f` a pattern that is part of your own command line: it once killed the shell
  before the audio routing was put back.
- Speech-to-text on game audio doesn't work: the music hides the voices.

---

## 5.10 Where to look

- `notes/voice-and-sound.md` — voices, lines, subtitles, banks, slot maps.
- `notes/sound-bank-ids.md` — the id system and the fix.
- `tools/scripts/sscf.py`, `spot33_sfx.py`, `spot33_weaponsfx.py`, `spot33_sndtrim.py`,
  `spot33_soundids.py`, `spot33_lines.py`, `voice_lines.py`, `voice_text.py`, `kh2_se.py`,
  `ppsoundwatch.py`.
- `tools/voice/` — the voice maps and line lists.

Next: [Chapter 6 — Visual effects](06-visual-effects.md).
