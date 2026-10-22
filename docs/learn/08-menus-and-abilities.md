# Chapter 8 — Menus, names, pictures and abilities

**The big idea:** a fighter shows up in many screens — the select grid, the setup screen, the VS
screen, the battle HUD, Customization. Each screen gets its picture or text from a **different**
place, often by a number. For #33 most numbers pointed at nothing (or at Aerith, or at Cloud).
We fixed them one screen at a time. Abilities are the same: a row in a table, a learned list in
the save, a level table, name and description text in two different files.

---

## 8.1 Abilities: what makes a move equippable

Five things must all be right for one move to work in Customization → Abilities:

```
1. an ablt row          (system.bin)          the ability itself
2. a learned entry      (the save record)     "Sora knows this"
3. a comb action        (Sora's battle file)  the move it switches on (Chapter 4)
4. a name               (ability.bin)         "Slide Dash"
5. a description        (mess_pk_customize_ability_0.bin)   the info panel text
```

### The ablt row (40 bytes)

| offset | meaning |
|---|---|
| +0 / +1 | index / owner (id = owner << 8 \| index, e.g. 0x2104) |
| +2 | name text id |
| +4 | description text id |
| +6 | **parent** ability (for chain moves like "Combo Plus > Upper Slash") |
| +12 | **action id** (switches on the comb action) |
| +14 / +16 | CP cost / CP cost once mastered (30 / 15) |
| +18 | AP needed to master |
| +22 | type: 0 Bravery, 1 HP |
| +23 | 0 ground, 1 air, 0xFF = linked follow-up |
| +27 | user/owner (0xFF = general skill) |
| +30 | stance mask (7) |

Rows are **sorted by id** (binary search). #33's rows go after row 620 (0x2103) and before
owner 34's.

**Room:** the game copies the table into a memory block sized for **808 rows** (`0x328`).
More rows overflow it. `spot33_ablt_cap.py` changes one instruction so the block holds 832
(Chapter 7). **[PROVEN]** in builds since test 149.

### Learned list and levels

- The Customization list shows a row only if the row's owner byte matches **and** the ability
  is in the fighter's **learned list** (150 entries max per fighter, general skills included).
- Abilities are learned on **level-up** from the `chrl` level table. **Catch:** a save that is
  already past a level won't learn what's listed at that level. **Rule: put new moves at a
  level above the save's current level.** (Code to re-learn on every load was designed, but no
  safe cave was found.)
- Fast levelling for tests: write a big EXP value into #33's record (`*(0x089D712C) + 0x38F98`,
  +4) and win a battle → normal multi-level-up, abilities learned.
- **[PROVEN]** Mat (test 113): chain abilities appeared after levelling 11 → 12 normally.

### The amas freeze (test 54)

Opening Customization → Abilities for #33 gave a **white screen**. Pausing the CPU showed a
menu loop in `FUN_08ad0d48`, which looks up the fighter in the `amas` table ("master X to
learn Y"). Owners 1–32 have rows; 33 had none → the menu looped over garbage.
`spot33_amas.py` adds a row for 33. **[PROVEN]** the screen opens.

### Loadout limits

One equipment set holds per stance: 3 ground Bravery + 3 air Bravery (each with 3 link
bytes for chained HP moves), 3 ground HP, 3 air HP. A fighter's action table holds at most 256
actions. The menu's air-Bravery slots are "stick toward" / "stick away".

---

## 8.2 Text: names and descriptions

### Move names (`ability.bin`)

`general_archive/main/EN/main_lang.bin` (MPK) → `ability.bin`. A table of entries, each
**XOR-scrambled** with a 32-byte key (same family as the subtitles).

**Lesson:** adding new entries ("add") **garbled** text near the old end of the table in game.
The real cause was found later: our tool misread the table's header (the count and the offset
list are one apart), so the game read one stale offset and decoded a region twice. Instead of
growing it, we **reuse developer placeholders**: hundreds of entries no ability points at, with
names like "Firion08", "Kefka57", "Gabra12". `spot33_movenames.py` and `spot33_moves.py`
write Sora's names there.

### Descriptions (a different file!)

Mat saw "WOL 15" and "Ultimecia 59" as move descriptions. Why: ablt +4 does **not** index
`ability.bin`. It indexes group 0 of `text/EN/mess_pk_customize_ability_0.bin`. Those ids
landed on placeholders there.

- That table's offsets are 16-bit, so it must stay under 131,070 bytes (it's 128,302 — only
  2,768 bytes spare).
- `spot33_desc.py` re-encodes the whole group and empties unused placeholder fillers until
  Sora's texts fit, keeping the **same file size**.
- Descriptions can carry formatting codes (`\n` = new line; a coloured "Additional Effect"
  last line). Copy the codes from Cloud's entries.
- **[PROVEN]** test 115: all descriptions show, chain moves under "Branching from …".

### In-battle name banners ("Firaga!", "Ars Arcanum")

These are **not** in `ability.bin`. They're in the battle file's own `text` chunk ("mlng",
6 languages, the US game uses block 0). A piece's plya byte **+0x21** picks the banner
(game index k = text entry k+1).

**Lesson (test 61):** entry 0 of that table is "end of data", not a name. Dropping it gave
garbage. Also: two moves both said "Ragnarok" because they shared Cloud's banner number.

Examples of Sora's banners: Ars Arcanum (the burst), Dodge Slash, Upper Slash, Finishing Leap,
Aerial Finish, Guard Break, Magnet Burst, Horizontal Slash, Aerial Sweep, and the EX Mode line
"My friends are my power!". The exact list is the NAMES table in `spot33_battlenames.py`.

---

## 8.3 Pictures (GIM)

Menu pictures are GIMs (256-colour, see Chapter 3). `gim_put.py` writes a PNG over a GIM of
the **same size**. **Tip:** reduce the PNG to 256 colours *before* `gim_put` (its own fallback
looks blotchy).

### Faces

From KH2's HD **Jiminy's Journal** portrait of Sora (`jmface_ex0`). `spot33_faces.py` makes:
the VS screen face (64×64), the battle HUD head (128×128), the eye strip next to the name.
Then Mat's style: art from the KH2 **opening-menu illustration** (Sora standing in the water,
looking back), made darker gold (`make_title_art.py`). Mat: "that darkened image is perfect".

### The name "Sora" in the game's own font

No font tool: `name_banner.py` **cuts letters out of other fighters' name banners** and glues
them: S from Squall, o from Cloud, r and a from Garland → `tools/art/sora_name_banner.png`.
Used for the Customization header, VS screen and loading screen. The big glowing intro name
(`encount_sev120.gim`) is made the same way (`spot33_vsname.py`).

---

## 8.4 The Quick Battle grid pictures (how numbers become textures)

Grid icon, big art, name and game logo come from "menu pak" files. Each pack has an **id base**;
every picture in it gets id = base + its position. The screen asks for **slot base + the
picture number** from the grid row:

| what | slot base | Cloud (picture 12) |
|---|---|---|
| big art | 0x700C | 28696 |
| grid icon | 0x702F | 28731 |
| name | 0x704F | 28763 |
| logo | 0x706F | (+ logo number) |

Problem: **every id from 28672 to 28928 is already used.** Picture 32 (the next one) collides
with other textures. So `spot33_qbpics.py` **appends** Sora's pictures at the end of
`menu/menu_pk_free_battle_gim_3.bin` (ids above 28928) and gives #33's grid row picture
**245**, name 179/245, logo 148 (a KINGDOM HEARTS II logo). **[PROVEN]** test 69: icon, art,
"Sora" name and KH2 logo on the select screen.

### The setup screen used "owner − 1"

The setup screen (Enter Battle / Stage list) doesn't read the grid row. It computes
**owner − 1** = 32 for #33 → art = an empty slot, name = the FF1 logo (the red "FINAL FANTASY"
Mat saw). Fix: a small menu-overlay patch, "if it's 32, use 245" (Chapter 7). **[PROVEN]**
test 73: "Lv7 Sora" with Sora's art.

### The missing blue name band (a lovely little bug)

The blue (player) / red (CPU) band behind a fighter's name is **not its own picture**. It's a
sprite that samples a tiny **3×3 grey block** of exactly (128,128,128) in the **corner** of the
name picture, then tints it. Every original name picture has that grey block at x 0–2, y 29–31.
Sora's new picture was transparent there → the band sampled "nothing" → no band.
Fix: `gim_markers.py` copies the grey marker pixels from Cloud's template into every new picture.

**Lesson:** when you replace a game picture, keep its invisible "helper" pixels.

---

## 8.5 Small facts and non-bugs

- Yuna shows "Lv 1" on the grid in the downloaded 100% save: that save's equipment Set B has a
  level setting. Set E shows Lv100. **Not our bug.**
- The Customization header's lower strip shows #33's *assist* (Cloud) — that's fine.
- The grid cell shows only the top ~32×35 pixels of the 32×64 icon.
- **[OPEN]** The CPU-side banner frame row for #33 is not remapped (matters only when #33 is
  the CPU).

---

## 8.6 Where to look

- `notes/abilities-owner33.md` — rows, learned list, chrl, descriptions, chains, combos.
- `notes/ability-table.md` — the first ablt tests.
- `notes/qb-grid-pictures.md` — grid, setup screen, bands.
- `notes/roster.md` tests 22–23, 53–55, 63, 65 — names and pictures.
- `tools/scripts/spot33_moves.py`, `spot33_desc.py`, `spot33_movenames.py`, `spot33_amas.py`,
  `spot33_battlenames.py`, `spot33_qbpics.py`, `spot33_faces.py`, `spot33_vsname.py`,
  `spot33_banner.py`, `name_banner.py`, `gim_put.py`, `gim_markers.py`, `make_title_art.py`,
  `ability_text.py`.

## 2026-10-16: menus found today

- Menu code computed "owner − 1" in 13 places; owner 33 fell into the next picture set (friend card, WoL, Chaos
  icons). `spot33_menuart.py` points them at 245 (`notes/menu-art.md`).
- Museum Character Files = `collection_param.bin` (Sora = entry 35); Player Icon 414; Records list is hard-coded
  (32 slots, Sora replaces the unused Chaos slot) — `spot33_museum.py`.
- EX Mode banner text/aura per costume (`.cosx` +0x38, `.exex`) — `spot33_p2fix.py`.
- Assist: `main.bin/assist.bin` + objentry kind-8 rows + `p_sev120_a.objx` / `P_SEV120_*P_A.gmo` (`notes/assist.md`).

Next: [Chapter 9 — How we test](09-testing.md).
