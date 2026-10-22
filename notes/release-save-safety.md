# Release save safety: RR-01, RR-02, RR-03 (static, 2026-10-18)

Claude (save helper). Static analysis only: no emulator was run and no save was written. Sources: a local Ghidra decompile
of the EBOOT and the menu overlay (never published), the clean `dumps/extracted/*.ELF`, the test343 disc (read only) and `tools/scripts/spot33_*`.
Fix disc (v1, SUPERSEDED by test344c — see §1.5): `dumps/ULUS10566-test344-save.iso` = copy of test343-final-voices (sha256 1f371261…2552) + `spot33_savefix.py`;
sha256 032d86155d44a140d283a78e4c303dba97a00800826fae2c12b0e835866a7b61; only 174 EBOOT bytes differ (ISO bytes 1966452..1966919). Not run yet.

## Plain English summary

- **Where Sora's progress is stored.** The game saves records for 31 fighters. It never had a record for owner 33, the
  slot Sora uses (in vanilla that was Aerith, who is assist-only). The mod keeps Sora's record inside the space for
  friend card number 25, and lowers the friend-card limit from 25 to 24. The save file keeps its exact size and layout.
- **RR-01: there was a real problem with 25 cards, and test344 fixes it.** On a save that already holds 25 friend
  cards, the old code wrote Sora's record over card 25 the first time Sora was used. Card 25 then showed up as a
  broken card. Later card changes could also wipe Sora's progress. test344 treats card 25 as if it had just arrived
  with a full list, which is what the game itself does: it replaces the oldest card that isn't locked. Locked cards are
  never touched. Only then does it set up Sora's record. Net effect on a 25-card save: one old unlocked card goes,
  nothing breaks. Saves with 24 cards or fewer, and every mod save, are not affected.
- **RR-02: no other fighter's saved data can be overwritten by Sora.** Every save table indexed by fighter keeps Sora
  in his own slot. In the places that use a 32-bit fighter mask, Sora shares Warrior of Light's bit. All of those only
  read or filter: which items he may equip, which items CPU Sora carries, and an "is this fighter unlocked" check
  (WoL is always unlocked anyway). There are also a few gaps where the game simply skips Sora. When you sell an item
  he has equipped, he keeps it. The story-party restore doesn't tidy his sets. Some menus treat him as "no saved
  record". These are small consistency issues, not overwrites. They're listed below with runtime tests.
- **RR-03: yes, Sora learned only on level-up, and test344 adds a one-time catch-up.** The game has no catch-up for
  saved records. It never needed one because its learn tables never change. A Sora who was already past a move's
  level never got that move. That affects older test saves and any future update that adds moves. test344 runs the
  game's own learn routine for levels 2 up to Sora's current level, once per save, and records that it did. There was
  never any old owner-33 data that Sora could pick up: buying "Chaos (CPU)" (flag 925) or having Aerith creates no
  record.
- **Downgrade (a mod save loaded on the original game): don't support it.** The layout is the same, so the save
  loads. But the original game can wipe Sora's record by receiving a 25th card. It also sees item IDs 678–681 that it
  doesn't know, and any replays with Sora in them. Advise players to back up their save before installing. To go back,
  restore that backup.

## Risk table

| # | Item | Risk | Evidence | Fix | Runtime test |
|---|---|---|---|---|---|
| 1 | 25-card save: Sora's record is created over card 25 | **High** (corrupt card; Sora's progress can be lost later) | §1.2–1.3 | **test344** `spot33_savefix.py`: count ≥ 25 → count 24 + native `FUN_088f526c(list, card 24)`, then a fresh record | T1 |
| 2 | Sora's record overwritten later in 25-card state (card add picks index 24, or delete shifts it) | High (before the fix) | §1.3 | Same fix: count never stays at 25 once Sora's record is in use | T1 |
| 3 | Save size or layout change | None | §1.1: blob 0x3ECC8 and section table unchanged | none | T5 (file size) |
| 4 | Downgrade to vanilla | Medium | §1.4 | Policy: not supported, back up the save before installing. After a vanilla round trip, test344 keeps a 25th card and resets Sora to Lv1 | T6 (copied save only) |
| 5 | Owner 33 record aliasing WoL (1), Cloud (13), Chaos (23) or Aerith (33) | None | §2.1: owner list 0x089CBC98 = 1..22, 24..32; owner 33 gets its own branch | none | T4 |
| 6 | Per-owner stats blocks (Records) | None | §2.2: +0x10D38 + 200·owner (0..35), +0x12958 + 0x30·owner (0..34) | none | T4 |
| 7 | Unlock row 22 flags (925 reused from Chaos; SEEN 3633) | Low, intentional | notes/unlocks.md §2, §5 | none | done in test341 |
| 8 | Item equip masks use bit (owner − 1) mod 32 → Sora = WoL bit 0 | Low (read-only; Sora can equip WoL-exclusive vanilla gear) | §2.3 | intentional; 678–681 stay Sora-only through the exitems hooks | T4 (WoL list has no Kingdom Key) |
| 9 | Unlocked-fighters mask FUN_088d5ce8 | None | §2.3 | none | none |
| 10 | CPU gear (acit) uses bit (owner mod 32) | Low, intentional | notes/cpu-ai.md §4 | none | none |
| 11 | Shop "sell equipped item" scan skips Sora (FUN_08a255ac, owners 1..32) | Low–Medium (Sora keeps an item you sold; no overwrite) | §2.4 | Proposed only: bound 0x21 → 0x22 + "has record" for owner 33 (side effect: WoL is named in the warning). Not applied | T7 |
| 12 | Story-party restore loops skip Sora (FUN_088f3a7c / FUN_088f3b18 / FUN_088f42a8) | Low (item/temp-field tidy-up missing for Sora; no overwrite) | §2.5 | Proposed only: 3 loop bounds 0x21 → 0x22. Not applied | T8 |
| 13 | "Has saved record" = false for Sora (FUN_088cb1ec, 6 sites) | Low (features skipped, e.g. some ghost/level displays) | §2.6 | Not applied. A fix could put owner-33 ghosts on cards sent to unmodded players | T9 |
| 14 | GET_RECORD ignores the records-base argument for owner 33 | Low | §2.7: all non-live-base callers skip owner 33 | none | none |
| 15 | Moves missed by a Sora above their learn level | **Medium** (dev saves, future updates) | §3 | **test344**: one-time `FUN_088cbd24(rec, 1, level)`, marker byte rec+0x777 = 0xC1 | T2, T3 |
| 16 | Catch-up adds the Lv1 accessory-slot bonus again, or truncates | None | §3.3: only the Lv1 row has a bonus; 74 ids ≤ 80 cap | Guards in the script | T2 |

## 1. RR-01 — friend-card slot 24

### 1.1 Layout (EBOOT, static)
- Save base = the u32 at 0x089D712C; data blob = base+0xF08, size **0x3ECC8**. Set by FUN_088ab800 (new game memsets the whole
  blob, then writes a section-size header at blob+0: 10, 0x3ECC8, 0x1CEAC, …, 0x1A160 = friend-card section, …).
- Fighter records: base+0xF58, 31 × 0x778 (FUN_088cb210 inits owners from list 0x089CBC98).
- Friend-card section: base+0x1FDD8 (FUN_088f5870). Card list = **base+0x1FECC**, 25 × 0x10A8, count u32 at
  list+0x1A068 = **base+0x39F34**. Card init FUN_088f4fc8 memsets card+0xFC..+0xF54 (ghost data, 5 × 0x2D8).
- Sora's record (spot33_save GET_RECORD) adds 0x38F98 to the base → **base+0x38F98** = list + 24·0x10A8 + 0x10C
  → card 25 bytes +0x10C..+0x884 (inside its ghost data). The count field (base+0x39F34) is not overlapped.
- Limit 25 → 24: the compare limit changes 25 → 24 at 0x088F523C (FUN_088f520c init loop) and at 0x088F52A0
  (FUN_088f526c add). No size, header or section change, so the save **file layout and size are unchanged**.

### 1.2 Card functions that touch index 24 (all by count)
FUN_088f526c add: duplicate check FUN_088f56ec over `count` cards. If count < 24, it appends. Otherwise it replaces the
oldest card (u32 +0x1C) that isn't locked (+0x27 bit 0) **among all `count` cards**. FUN_088f53f4 delete: shifts cards
idx+1..count-1 down, count−1 (the source isn't cleared). FUN_088f5508: at most 8 or 9 locked cards. Others
(FUN_088f5584/55d0/55f4/5618/56b0, FUN_088fa474, FUN_0891e8a4, FUN_088c7fe4 ghost-item ids `(id&0x1F00)>>8`) address
a given index.

### 1.3 What test343 (without the fix) did to a 25-card save
1. Nothing lowers the count, so it stays 25 and card 25 is listed.
2. First fetch of owner 33: record byte 0 (card 25 +0x10C, ghost data) ≠ 33 → FUN_088cbbb4 writes 0x778 B into card 25.
   **Card 25 is corrupted, still listed and still counted.**
3. Receiving a card: count 25 ≥ 24 → replaces the oldest unlocked card among 25. If that's index 24, the new card
   overwrites Sora's record → **Sora resets to Lv1** on the next fetch.
4. Deleting a card shifts index 24 (Sora's record bytes inside it) into the visible index 23 → a visible garbage card.
Mod saves can't reach 25 (cap 24), so this only hits a vanilla save that already had 25 cards, or a mod save after a
vanilla round trip.

### 1.4 Downgrade (mod save on the unmodded game)
Same blob size and sections, so it loads. Vanilla ignores slot 24 while count ≤ 24. Risks: (a) vanilla's 25th card
overwrites Sora's record. Back on test344, that card is kept and Sora restarts at Lv1. (b) The inventory holds IDs 678–681
(spotted in exitems ENSURE). Vanilla's item row lookups (FUN_088c0f8c / FUN_088b97e8) return none. Most callers null-check,
but the menus weren't verified. (c) Owner 33 in the player's own friend card (favourite/ghost), replays with Sora, and
assist byte 33 (vanilla drops it unless Aerith DLC, and then it's Aerith). Policy: **not supported; back up first**.

### 1.5 Fix in test344 (`tools/scripts/spot33_savefix.py`)
GET_RECORD's owner-33 branch (0x088CB19C..0x088CB1B8) now calls **SORA_REC** at 0x088CB2C0. That's 44 of the 61
words of FUN_088cb2c0, whose only caller (0x088CB3DC, inside the original FUN_088cb3b4) was replaced by spot33_save's
LOOKUP. No jal/j targets it anywhere in the disc EBOOT, and none in the clean menu/battle overlays. SORA_REC(rec):
1. count ≥ 25 (count at list+0x1A068 = base+0x39F34):
   a. **valid Sora record already there** (owner byte 33 and level 1..100; owner 33 can't appear in a vanilla card): the
      save was used with test20..test343, card 25's ghost data is already overwritten → count = 24 only, keep the
      record (no receive-card with Sora bytes). Added after the runtime result below.
   b. otherwise → count = 24, `FUN_088f526c(list, list+0x18FC0)`: the game's own receive-card path. Card 25 replaces
      the oldest unlocked card among 0..23, or is dropped if it's a duplicate or all are locked. Then go to 2
      unconditionally: the old bytes were card data.

**Versions.** v1 = test344 (sha 032d8615…7b61) is **superseded, don't use it**. Its constants were wrong: list =
base+0x2FECC and count = list+0x2A068 (the high half was 0x2 instead of 0x1, so 0x2FECC/0x2A068 instead of
0x1FECC/0x1A068). So step 1 read a word
outside the save blob, at base+0x59F34 (0x08C08C6C with base 0x08BAED38). If that word had been ≥ 25, v1 would have
written 24 there and run receive-card on a garbage list. v2 = **test344c** `dumps/ULUS10566-test344c-save.iso` = copy of
test343 (1f371261…2552, only read) + spot33_savefix v2. sha256 b32d3ba0007e0975dae8715266fbe2de9cf9c9dc5aa50a43d166133c72b3d7b8;
204 EBOOT bytes (GET_RECORD hook + 54-word cave 0x088CB2C0..0x088CB398). The script recognises v1 (sha of its 44
cave words) and upgrades it.

**Runtime evidence, coordinator 2026-10-18T16:34:18Z, test344 (v1), copy of a 100 % save (played
with older mod builds).** Before the first Sora access: base 0x08BAED38, record 0x08BE7CD0 (= base+0x38F98), owner 33,
Lv42, marker 00, card count 25, learned list 58 real ids, no 0x0Dxx. After Customization → Sora: marker C1, Lv42,
learned list unchanged (he already had every id ≤ 42) → **T2 catch-up PASS** (marker path). Card count stayed 25 → step 1
didn't fire. Cause: the v1 address bug above. It also confirms the "already damaged" state: a valid Sora record sits in
card 25's area while card 25 is still listed. That's every 25-card save used with test20–test343. v2 case 1a handles it.
Re-test T1 on test344c with the same copied save: expect count 24, record unchanged (Lv42, marker C1), Friend Card
list = 24 cards, no card replaced. Then save, reload and check the same.
2. rec[0] ≠ 33 → `FUN_088cbbb4(rec, 33)` (unchanged from spot33_save).
3. Catch-up (RR-03).
Guards and rollback are in the script docstring. code_sites.json has the new range (save_record_hooks).
Build order: after spot33_newtag, before spot33_installfix. Note: re-running **spot33_save.py** on a finished disc puts
its own GET_RECORD back (it only checks the first word). savefix runs later in build_sora.sh and re-applies.

## 2. RR-02 — owner-33 aliasing audit

### 2.1 Saved records
Owner list 0x089CBC98 = [1..22, 24..32]. Chaos 23 and Aerith 33 never had a saved record: vanilla FUN_088cb164
returned the shared, unsaved global 0x09AEFAFC. LOOKUP returns −1 for 33, and GET_RECORD gives owner 33 the slot-24
record. WoL (idx 0) and Cloud (idx 12) are untouched. **No vanilla save holds owner-33 fighter data** (flag 925 =
"Chaos (CPU)" purchase is just an unlock bit).

### 2.2 Other save tables indexed by owner
Records stats blocks (FUN_08adcfa0): owners 0..35 / 0..34, Sora has his own rows. Unlock/SEEN flags: row 22 =
(33, 925, 1, 1, 3633). Default preset table 0x089CB7E8[33] = 250. BGM mask is 64-bit (bit 33 is his own). No other
owner-indexed save array was found (owner_tables.json kind=save: record slot, stats blocks, flags).

### 2.3 32-bit owner masks (all read-only)
Consumers found by scanning for the one-bit-per-owner mask (bit (owner − 1) mod 32): FUN_088c1234 (item list, ROWMASK hooked), FUN_088c1ae8 (may equip,
ELIG hooked), FUN_088d5ce8 (unlocked-fighter mask, used by menu 0x2149C/0x116DC0, WoL always unlocked), FUN_088f37bc
(story-party restore: re-equip filter, not hooked, only re-equips the party member's own backup), menu FUN_08af3b64
(used only by FUN_08af8da4/FUN_08af8f84, in the exitems MENU-hooked equip path), and acit (`owner&31`, CPU gear). None
writes save data indexed by the mask bit. Sora shares WoL's eligibility for vanilla items (intentional); 678–681 are
Sora-only at the hooked sites.

### 2.4 Shop sell scan
Menu FUN_08a255ac (called at 0x480BC / 0x480F4 via FUN_08a25550): owners 1..0x20 with has-record. It returns a
mask of who has the item equipped and, if asked, unequips it from everyone. Sora is never scanned, so selling an item he
wears leaves it on him with count 0.

### 2.5 Story/party-mode restore (save+0x1E208 block; menu FUN_089f9cb8 / FUN_089fc0a0 / FUN_08a04af8 / FUN_08a0689c)
FUN_088f40f0 restores the inventory (FUN_088f2fe0). It then restores the ≤5 backed-up party members by owner
(FUN_088f37bc → FUN_088cb164: Sora's own record if he was in the party), and for owners 1..32 except 23 it unequips
items no longer owned (FUN_088f3b80). FUN_088f3b18 zeroes record +0xC/+0x6 for owners 1..32 except 23. FUN_088f42a8 =
FUN_088f414c(owner, 1) (loadout re-check) for the same range. Sora is skipped in all three. That's a tidy-up gap, not an
overwrite (belongs with RR-04).

### 2.6 "Has saved record" checks (FUN_088cb1ec → false for 33)
EBOOT FUN_089293dc (owner 1..34) → menu FUN_08a5a88c (friend-card character build: FUN_088f5ba4) and FUN_08a6c3ec
(level display). Plus menu FUN_08a255ac, FUN_08a48db0 (sets level/fields on every owner with a record), battle 0xFED34
and FUN_08adc088. In all of them Sora is skipped, never redirected. Making it true for 33 changes what goes onto
friend cards, and those can be sent to unmodded players. Not done.

### 2.7 GET_RECORD base
For owner 33 it always uses the live save (the word at 0x089D712C), not the base passed in the first argument.
Callers that pass another base (FUN_088cb408's third argument, FUN_08adc088's second argument, FUN_088c31f4 via list 0x089CBB7A = 31 owners without 33) either iterate
lists without 33 or check has-record first. No path found that copies a temporary record over Sora's.

## 3. RR-03 — learning thresholds

### 3.1 How saved records learn
FUN_088cbd24(rec, old, new) → FUN_088b6f48 collects the chrl ids of rows with level in (old, new], at most 80. FUN_088b6e14
picks the last row ≤ L, so duplicate-level rows are fine. FUN_088b7ed4 adds each id unless it's already known. Callers on the
saved record: battle EXP level-up (EBOOT 0x08835764), level items (FUN_088cb408, 0x088CB578), creation
FUN_088cbbb4 (0, 1). **No catch-up for saved records exists.** FUN_088cbddc = FUN_088cbd24(rec, 0, level) is called only
when building temporary/auto records: CPU FUN_088b3b98, FUN_088b9e84, FUN_088bbab4, FUN_088fa5f4. So a CPU Sora at any
level knows every move, but a saved Sora above a learn level never got it (Sora's path skipped it).

### 3.2 Which saves miss moves
- Vanilla saves (incl. flag 925 / Aerith DLC): Sora starts Lv1, learns everything by levelling. Nothing missed.
- Mod saves whose Sora reached a level before that level's move was added (dev saves from test21+; the chrl rows moved by
  spot33_moves): missed. The same goes for any future update that adds moves at lower levels.

### 3.3 Fix in test344
SORA_REC step 3: if rec+0x777 ≠ 0xC1 → `FUN_088cbd24(rec, 1, rec[1])`, then rec+0x777 = 0xC1. Once per save (also on a
fresh record). +0x776/+0x777: no load/store with those immediates (or +0x766/+0x767 from the loadout base) in the EBOOT,
menu, battle or extra overlays, apart from a stack local. The record reset stops at +0x775. Owner 33 chrl on test343: 52 rows,
76 ids (74 at Lv2..100) ≤ 80, bonus byte only on Lv1 (3). Starting the range at 1 never re-adds the accessory bonus.
Duplicate rows Lv13 ×3 and Lv18 ×3 are handled (last-row search). Bump MARK when Sora's chrl changes in an update.

## 4. Runtime tests (copied saves only; never Mat's originals)
RAM: base = u32 @0x089D712C. Card count = base+0x39F34. Card i = base+0x1FECC+i·0x10A8 (+0x1C time, +0x27 bit0 locked).
Sora's record = base+0x38F98 (+0 owner, +1 level, +0x3EE learned list 150×6 B, +0x777 marker).
- **T1 (25 cards)**: copied save, test344, main menu. Copy card 0 → card 24, change one byte of its id at +0xC.., set count = 25.
  Open Customization → Sora. Expect count 24, the oldest unlocked card replaced by card 25's contents, locked cards
  unchanged, Sora Lv1 with marker 0xC1, the Friend Card list shows 24 valid cards. Save, reload: the same. On test343 the
  same steps leave count 25 and a broken card 25.
- **T2 (catch-up)**: copied mod save, test344. Before touching Sora, set record +1 = 60 and +0x777 = 0, and delete
  learned entries 0x2111..0x2116 (Lv18). Open Customization → Sora. Expect all 74 Lv2..60 ids present once, marker
  0xC1, +0x775 unchanged, no 0x0Dxx (Cloud) ids.
- **T3 (fresh)**: new game or never-used Sora. First access → Lv1, marker 0xC1, preset 250 abilities, nothing else.
- **T4 (isolation)**: level Sora by one battle, save, reboot. WoL/Cloud records, Records "as/against" rows, unlock rows
  unchanged. WoL's equip list has no Kingdom Key / Protect Belt.
- **T5**: save file size unchanged (DISSIDIA.BIN 257,240 B).
- **T6 (downgrade, copy only)**: load a test344 save on the clean ISO. Check boot, Customization, Shop/inventory, Friend
  Card, Records. Expected: loads. Unknown items may show oddly. Record the result for the release notes.
- **T7**: equip Sora with an item, sell your last one in the Shop. Expect (known gap) he keeps it.
- **T8**: story/party mode with and without Sora in the party; afterwards check Sora's sets and record +0x6/+0xC.
- **T9**: Friend Card favourite/ghost set to Sora. Note what shows and whether a card can be exchanged.

## 5. No-loss alternative: is there free space for the record inside the save? (coordinator follow-up, 2026-10-18T16:24:42Z)
**Answer: no. There is no contiguous 0x778-byte (1,912 B) region in the 0x3ECC8 blob that vanilla provably never
writes. test344's approach stays, and no test344b was built.**
- Every section in the new-game header (FUN_088ab800: 0x1CEAC, 0x80, 0x104, 0x280, 0x1BD0, 0x1A160, 0x1864, 8,
  0x290C, 0x6A8, 0x16C, 0xC80, 0xB4, 0x590) lines up with an init call at base+0xF58 / 0x1DF88 (flags) / 0x1E208 /
  0x1FDD8 / 0x39F38 / 0x3B7A4 / 0x3E0B0 / 0x3E758 / 0x3E8C8 / 0x3F548 / 0x3F63C. Each init fills its section with a
  fixed-count array:
  - 31 records × 0x778; inventory 683 + 630 + 64 + … entries (FUN_088b8538).
  - Stats: 35 × 200 + total, 35 × 0x30, 19 × 0x2C (FUN_088b3004/312c/31b4).
  - 100 × 2 B (FUN_088c288c).
  - 31 per-fighter blocks × 0x57C, exactly to base+0x1CEA8 (FUN_088c0450).
  - Friend cards 25 × 0x10A8 + count.
  - 20 × 0x138 + count = 0x1864 (FUN_088c7350).
  - 3 × 35 per-owner presets (FUN_08902734).
  - 5 × 0x154, 5 × 0x48, 5 × 0x280 (FUN_0892a514 / 0892a8b8 / 08912b5c).
- Slack found: about 0x40 B at the end of the friend section, about 0x3C B between base+0x3F5FC and 0x3F63C, about
  16 B of inventory slots, and the unused owner-34 rows (200 + 48 + 96·3 B). These are scattered pieces of a few hundred
  bytes at most. The owner-34 rows also sit inside arrays that are initialised and looped over as a whole (stats
  totals, preset tables). Bytes stored there could leak into Records totals.
- All 31 record slots and 31 per-fighter blocks belong to playable fighters (owner list 1..22, 24..32). Chaos (23) and
  Aerith (33) have none, so there is no spare record slot to reuse.
- Splitting the record across those pieces would need it held in RAM, plus new hooks on save-write and load-complete
  to scatter and gather it. That means more code, more sites, and a "never written" proof for every piece. It is not
  low-risk.
- The card-25 bytes are only free when card 25 has fewer than about 3 ghosts. That depends on the save's data, so it
  can't be guaranteed.
- Byte tolerance (asked): vanilla treats the blob as one block. It saves the whole 0x3ECC8 and keeps no per-section
  checksum in the game code (the PSP savedata layer hashes the whole file). Vanilla ignores card bytes past the count
  until it adds a 25th card. That is why test344's slot-24 storage is safe at 24 cards or fewer.
- Only no-loss option left (not built; Mat to decide): while the card count is 25, give Sora a temporary RAM-only
  record (progress not saved) instead of replacing a card. The player keeps every card, but Sora's progress silently
  doesn't save until a card is deleted. That is arguably worse than losing the oldest unlocked card the game itself
  would drop next.
- RR-02 addition: Sora has no per-fighter 0x57C block (base+0x124A4, ghost-behaviour data). FUN_088c04b4 returns NULL
  for owner 33, and all 3 callers (FUN_088f5ae8, FUN_088f5fec, FUN_08aef78c) null-check it. Safe; the feature is simply
  skipped.

## 6. Runtime evidence — test344 on a copy of the 100% save (2026-10-18T16:30:23Z, Claude, PPSSPP, disposable profile)
A 100 % save (played with older mod builds), copied. Before first Sora access:
base 0x08BAED38, record 0x08BE7CD0: owner 33, level 42, marker 00, **card count 25**, 58 learned ids, no Cloud ids.
→ This save is already in the damaged state (Sora's record over card 25's ghost data while card 25 is listed).
After Customization → Sora: marker C1, level 42, learned list unchanged (nothing missing ≤ 42), no Cloud ids — catch-up
PASS (T2-like). Card count stays 25 — the fix's 25-card branch only runs when no Sora record exists → follow-up:
count ≥ 25 + valid Sora record → set count 24, keep the record (test344c, helper).

**Decision 2026-10-18T16:36:51Z (Mat): option 1** (drop oldest unlocked card on 25-card saves; README: back up your save).

## 7. Runtime — test344c (savefix v2) PASS (2026-10-18T16:39:23Z, Claude, copy of the 100% save)
Before: owner 33 Lv42 marker 00, card count 25 (already-damaged state). Customization → Sora: count **24**, Lv42 kept,
marker C1, learned list intact, no Cloud ids. "Save and return to title" → reload: count 24, Lv42, marker C1 — persisted.
T1 (already-damaged 25-card branch) + T2 PASS. Fresh 25-card branch (no Sora record) not yet run at runtime.
