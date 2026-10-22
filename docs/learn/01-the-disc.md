# Chapter 1 — The game disc and its files

**The big idea:** the whole game is one big file on your computer. Inside it is a giant
"filing cabinet" holding about 11,000 smaller files. The game finds each file by a number made
from its name. To change the game, we swap files in that cabinet.

---

## 1.1 Words you need first

**Byte.** The smallest piece of a file. One byte holds a number from 0 to 255.

**Hex (hexadecimal).** A way of writing numbers that computer people like. It counts in 16s
instead of 10s, using the digits 0–9 and then a–f. Hex numbers start with `0x`.
- `0x10` = 16, `0x20` = 32, `0x100` = 256, `0x800` = 2048.
- You will see hex everywhere in the notes. You don't need to do maths with it. Just read
  `0x...` as "a number written the computer way".

**Offset.** "How far from the start." `+0x10` means "16 bytes after the start of this thing".
When the notes say "atkp +0x10 = power", they mean: go to the start of one row of the atkp
table, step 16 bytes in, and the power number is there.

**u8, u16, u32, f32.** Sizes of numbers in a file:
| name | size | holds |
|---|---|---|
| u8 | 1 byte | 0–255 |
| u16 | 2 bytes | 0–65,535 |
| u32 | 4 bytes | 0–4 billion |
| s16 / i32 | 2 / 4 bytes | the same, but can be negative ("signed") |
| f32 | 4 bytes | a number with a decimal point ("float"), like 1.5 |

**Little-endian.** The PSP stores the smallest byte of a number first. So the bytes
`00 00 1c 31` in a file mean the number `0x311C0000`. You read them backwards. This is why
byte dumps in the notes sometimes look "reversed".

---

## 1.2 The disc image (ISO)

An **ISO** is a copy of a whole disc, saved as one file. Think of it as a photograph of every
byte on the disc.

- Mat's own copy: `dumps/ULUS10566.iso`, 1,754,529,792 bytes (about 1.75 GB).
- `ULUS10566` is the game's ID. It means the **US** version of Dissidia 012 duodecim.
  (The EU version is `ULES01505`; our tools only know the US one.)
- **Rule: nobody ever writes to `dumps/ULUS10566.iso`.** Every test is a *copy* with changes.
  The clean disc is only ever read.

Inside the ISO is a normal folder tree, like a USB stick:

```
ULUS10566.iso
└── PSP_GAME/
    ├── SYSDIR/
    │   ├── EBOOT.BIN          the main program (the game's code)
    │   └── BOOT.BIN           all zeros, a dummy
    └── USRDIR/
        ├── PACKAGE.BIN        ~1 GB: the filing cabinet (11,043 files)
        ├── PACKAGE_INFO.BIN   the cabinet's index cards
        └── DATA/
            ├── OVL_BATTLE_APP.ELF   extra code, loaded during fights
            ├── OVL_MENU_APP.ELF     extra code, loaded in menus
            ├── OVL_EXTRA_APP.ELF    a small extra
            └── MODULE/*.PRX         fonts and small libraries
```

The **code** files (EBOOT and the "OVL" overlays) are explained in
[Chapter 7](07-game-code.md). This chapter is about the **data**: PACKAGE.BIN.

A disc is divided into **sectors**. A sector is a block of 2,048 bytes (`0x800`). Files on
a disc always start at the beginning of a sector. Positions are often given as
"sector number", not as a byte count.

---

## 1.3 PACKAGE.BIN — the filing cabinet

`PACKAGE.BIN` is 1,034,358,784 bytes. It holds **11,043 files** packed one after another.
Fighters, models, sounds, menus, stages, text: almost everything is in here.

It has no names inside. It is just files glued together. To find a file you need the index.

### PACKAGE_INFO.BIN — the index cards

`PACKAGE_INFO.BIN` is the list that says where each file is. Think of a stack of index cards.
Each card is 12 bytes and says three things:

```
card (12 bytes)
  u32 hash     a "fingerprint" number made from the file's name
  u32 sector   where the file starts inside PACKAGE.BIN (in sectors)
  u32 size     how many bytes long (low 28 bits) + a 4-bit flag
```

The list starts with a small header: the number `0x20090218` (a date, 2009-02-18), the word
"pack", and the count 11,043. The cards are **sorted by hash**, so the game can find one fast
by jumping to the middle and halving (this is called a *binary search*).

The 4-bit flag has values 0–3. **Solved 2026-10-18 (P0.9):** it is the **Data Install tier**. The Extras →
Data Install menu offers 3 sizes; size L copies every file whose flag is 1..L to the memory stick (0 = never
copied). Limit: 4,050 files. Details: `notes/dlc-phase0.md` P0.9.

### How a file is found by its hash

The game never stores the name `obj/p_sev100.objx` on the card. It stores a **hash**:
a number you get by putting the name through a fixed mathematical "blender".

- The blender here is **CRC-32/BZIP2** of the name written in lower case
  (found in the game code at `FUN_08871288`; our copy is `tools/scripts/pkghash.py`).
- You cannot turn the number back into the name. But you can *check a guess*: blend your
  guessed name and see if the number is on a card.
- That is how we learned real names like `obj/p_sev100.objx` (Cloud's battle file) and
  `obj/P_SEV100_1P.gmo` (Cloud's model). We guessed names we saw in the game's code and
  checked them.

Analogy: a library where the cards show only a fingerprint of each book title. If you
already know a title, you can make its fingerprint and find the book. If you don't, you
can still open every book by its card number.

`tools/scripts/unpack_package.py` copies all 11,043 files out into `dumps/package/`, named by
their index and hash (for example `dumps/package/03394_4e88d7ff_t1.bin` = Cloud's battle file).
`dumps/package/index.tsv` lists them all.

**[PROVEN]** Checked: every file fits its gap, with less than one sector of padding.

---

## 1.4 Boxes inside boxes: container formats

Many files in the cabinet are themselves little boxes of smaller pieces. You will meet
these names again and again:

| magic word at the start | what it is | our tool |
|---|---|---|
| `ARC\x01` | a box of **chunks**, each with a 4-letter tag (like `comb`, `atkp`, `snd_`) | `arc.py`, `arcfile.py` |
| `MPK ` | a box of named members (like `system.bin`, `ability.bin`) | `mpk.py` |
| `menu pak` | a box of menu pictures, picked by number | `spot33_qbpics.py` |
| `mess pak` | a box of menu text groups | `spot33_desc.py` |
| `OMG.00.1PSP` | a 3D model (GMO) | `gmo.py` |
| `MIG.00.1PSP` | a picture (GIM) | `gim.py` |
| `SSCF` | a sound bank | `sscf.py` |

A **chunk** is one labelled piece inside an ARC box. Example: a fighter file is an ARC with
chunks `comb` (move list), `atkp` (hits), `snd_` (sounds), `effe` (effects) and more.
Chapter 2 opens one up.

The "magic word" is just the first few bytes of a file. Programs use it to know what kind of
file it is, the way a label on a jar tells you what's inside.

Some important nested paths:

```
PACKAGE.BIN
└── general_archive/main/main.bin      (MPK)
    └── system.bin                      (ARC)  ← the game's big rule book
        ├── chrp   one row per character (voice key, sound ids, ...)
        ├── ablt   the ability table (every move you can equip)
        ├── amas   "master this to learn that" lists
        ├── eqpm   starting equipment presets
        ├── chrl   which ability is learned at which level
        └── ... (item, acsr, eqaa, ...)
```

---

## 1.5 Changing a file: `pkg_put.py`

`tools/scripts/pkg_put.py ISO PATH FILE` is the tool we use most. It puts one file into a disc
copy under a name. Example:

```
python3 -I tools/scripts/pkg_put.py dumps/ULUS10566-testNN.iso obj/P_SEV120_1P.gmo dumps/models/sora_final_kc.gmo
```

What it does:

1. Makes the hash of `PATH` and looks for its card in PACKAGE_INFO.
2. **If the new file fits** in the old file's sectors, it writes it there ("in place").
3. **If it is bigger**, it can't squeeze in: PACKAGE.BIN is packed tight. So it writes the file
   at the **very end of the ISO**, then:
   - points the card at the new place,
   - stretches PACKAGE.BIN's size in the disc's folder list so that the end of the ISO now
     counts as "inside" PACKAGE.BIN,
   - updates the disc's total size (the "PVD", the disc's front page).
4. **If the name has no card yet**, it adds a new card, keeping the list sorted.

Analogy: the cabinet is full. A bigger folder goes on a new shelf at the end of the room,
and we fix the index card to point there. The old spot just stays empty.

Side effect: every time a file moves to the end, the ISO grows a bit (for example +1.4 MB).
That's fine.

**[PROVEN]** Test 16 (2026-10-12): Cloud's battle file copied as a brand-new file
`obj/p_sev120.objx` at the end of the ISO. The game loaded it. That was the first new file
ever added to this game, as far as we know.

### How many new files can we add?

The game reads PACKAGE_INFO into a memory buffer of a fixed size (`0x20F8C` bytes). That
gives room for 11,253 cards. Around test 24 we had used 11,130. So there is room for
**about 120 more new files** in total. Every new voice line or picture costs one. Keep that
in mind.

### Other ISO tools

| tool | what it does |
|---|---|
| `pkg_add.py ISO NEW_PATH SRC_INDEX` | add a new file as a copy of an existing one |
| `arcfile.py` | open a fighter's ARC file, grow chunks, write it back (keeps chunks on 16-byte steps, because textures and models need that) |
| `pkghash.py` | make a name's hash |
| `unpack_package.py` | copy every file out of PACKAGE.BIN |

---

## 1.6 Rules for working with discs

- **Never write the clean dump** `dumps/ULUS10566.iso`.
- **Never rebuild an ISO while PPSSPP has it open.** Once Mat heard beeps and no music
  because the disc changed under the running game.
- Test discs are named `dumps/ULUS10566-testNN-name.iso` (see [Chapter 10](10-build-pipeline.md)).
- Old test discs are deleted when a newer one works. The clean dump and the newest good test
  are kept.
- We never share discs or game files. We share only an **xdelta patch** (Chapter 10).

---

## 1.7 Where to look

- `notes/package-format.md` — the exact layout.
- `notes/iso-files.txt` — the list of files on the disc.
- `notes/roster.md`, test 16 — the first added file.
- `tools/scripts/pkg_put.py`, `pkg_add.py`, `pkghash.py`, `unpack_package.py`.

Next: [Chapter 2 — A fighter's file and roster slot #33](02-a-fighter-and-slot-33.md).
