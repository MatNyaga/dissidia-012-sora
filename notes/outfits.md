# Outfits / costumes per character (Claude outfits helper, 2026-10-16) — static only, no emulator

Mat: "see how many [outfits] the game can have". Sora = owner 33.

## 1. How the game decides which costumes a character has (EBOOT, dumps/decomp/all.c)
- **Costume number** = objentry row byte **+7** (1P = 1, 2P = 2, 3P = 3, ...). A fighter copies it to fighter+0x1079
  (FUN at all.c 509032). Files of costume k = the objentry row (owner, +7 = k, +8 kind 0) name N (+0x24):
  `obj/N.gmo`, `obj/N.cosx`, `obj/N.exex`, `menu/JP/battle/chara_image/N.gim` (HUD face). Row lookup
  FUN_08846ccc(owner, costume, assist) = first row with +6 owner, +7 costume, (+8 & 8) == assist, name "P_*", not "_W".
  If costume k has no row / file, FUN_088fb934 / FUN_088450a8 fall back to costume 1.
- **Costume mask** FUN_088d5e0c(owner) (u16 at +6 of every "available characters" list entry):
  - bit 1 = costume 1, always;
  - bit 2 / bit 3 = costumes 2 / 3, only if the EBOOT unlock table 0x089D7BE0 row (owner, unlock flag, **costume-2 flag,
    costume-3 flag**, text) has that flag bit set in DAT_089d726c (**-1 = never**);
  - **bits 4..12 = costumes 4..12 ("DLC costumes"): set if an objentry row (owner, +7 = k, kind 0) exists** — no flag,
    no unlock (skipped only when DAT_089d5f1f = demo/no-DLC build flag from language.bin, 0 on retail).
  - Same 4..12 loop in the Museum viewer (FUN_08a32284) and Colosseum random costume (FUN_089f0ce8, bits 1..12).
- → **Engine maximum = 12 costumes per character** (1..3 on disc + 4..12 DLC slots). The battle-setup record keeps
  the main costume as a full byte (menu_all.c 162134); only the ASSIST costume is a 2-bit field (0..3).
- Real DLC came as `ms0:` .edat packages `dlc/obj/dlc_%03doe.bin` (FUN_08862288) incl. a replacement objentry.bin
  (FUN_08847158(archive)); objentry +9 = "load from DLC" flag (0 = PACKAGE.BIN). With +9 = 0 the files come from
  PACKAGE.BIN like 1P/2P/3P.

## 2. Vanilla counts
- On the disc every playable character has exactly **3** costumes (P_xxx_1P/2P/3P .gmo/.cosx/.exex/chara_image);
  no vanilla objentry row has +7 >= 4. The `_4P_PUB` / `_3P_PUB` rows (+7 = 1!) are not costume rows (13 characters
  have a 4P_PUB = the real 012 DLC 4th-costume list: WoL, Firion, Cecil, Bartz, Terra, Squall, Laguna, Kuja, Tidus,
  Tifa, Shantotto, owners 30/31).
- **4th costume = the real DLC slot**: Cloud's/Sora's scripts carry sword-trail events for costumes 1-4 (see §3);
  Tifa's carry events up to costume 4 too. Nothing in vanilla data goes past costume 4.
- Sora's unlock-table row (since test20) = (33, -1, **-1, -1**, 3623) → his costume mask is 2 = **only outfit 1 is
  selectable**; 2P (Limit) / 3P (Master) were reachable only through the mirror-match CPU.

## 3. Per-costume script events (p_se) — the one data catch
- Event condition byte = main event +9 / one-shot +7: 0 = any costume, v = only costume v-1 (FUN_08828eec /
  FUN_08829104, param = fighter+0x1079).
- Sora's p_se (Cloud-derived): trail op 0x2a events **100 × costume 1, 80 × costume 2, 80 × 3, 80 × 4**
  (costume 1 has 20 more = the new KH2 moves). Variant param p[2]: costume 1 = 0 normal / 1 EX, costume 2 = 2 / 4
  (Cloud 2P's other sword), costume 3/4 = 0 / 1. One-shot op 3 (sound) × 7 only for costume 2 (Cloud 2P sword sounds, blocks 5/17/18/19/22/27/66).
- → costumes 5+ would have NO keyblade trail, costume 2 has Cloud-2P trail variants and no trails on the KH2 moves.
- Every costume-2/3/4 trail has a costume-1 twin (same frames/state, only the variant differs) → safe to make the
  costume-1 trails "any costume" and switch the duplicates off.

## 4. What adding outfit k (4..12) takes — data only, no code
1. objentry row in general_archive/main/main.bin: copy of the P_SEV120_2P row, +0 new id (sorted, above 1456),
   +7 = k, +0x24 name P_SEV120_kP. Buffer 0x13d30 = 1194 rows max (vanilla 1170 → 24 spare; battle.bin spec buffer
   0x09b12b88 follows directly, so never overflow). main.bin grows 68 B/row (load buffer 0x180000, fine).
2. New PACKAGE files: obj/P_SEV120_kP.gmo (2,499,028 B = 1P + Drive textures; same size as 1P, only one costume's model
   loads per fighter), .cosx (68 B) + .exex (88 B) = 1P's (EX banner/aura), menu/JP/battle/chara_image/P_SEV120_kP.gim
   (HUD face, 1P's). PACKAGE_INFO had room for 122 more entries (12 used).
3. Nothing else is per costume: names, select/VS/results art, voices, moves are per owner. No costume-name text exists.
4. Outfits 2/3 additionally need the unlock-row costume flags (EBOOT data words, not code).
5. Script events: make costume-only events costume-neutral (§3), else outfits 5+ have no Keyblade trail.
- Limits / not covered: Museum viewer shows 1P-3P only (its 4..12 path uses an owner table 0x08A358FC that has no
  Sora entry; index 34 reads unrelated data = 8). Assist Sora stays outfit 1-3 (assist costume = 2-bit field) and its
  _A models have no Drive textures. Real DLC (if ever loaded) replaces objentry.bin and would drop rows 4-6 (fallback 1).

## 5. Built — tools/scripts/spot33_outfits.py (extended, guarded, --dry, re-runnable) → test306
- `python3 -I spot33_outfits.py ISO [--dry] [--no-events | --events-only]`. build_sora.sh: `--no-events` at the old
  place (after spot33_2p/p2fix), `--events-only` as the LAST p_se writer (after the Codex fire-core step).
- **dumps/ULUS10566-test306-moreoutfits.iso** = test305 + it, sha256
  a16bffde6aca34c9772d71f522764496a5357d7b52b7348122ec1ed41b530c0d (1,824,389,120 B, +7.5 MB at the ISO end).
  Changes vs test305: PVD/dir size, EBOOT sector 1497 (unlock row owner 33: costume flags -1/-1 → 1/1), PACKAGE_INFO
  (+12 entries), main.bin (objentry +3 rows ids 1457/1458/1459 = P_SEV120_4P/5P/6P costume 4/5/6; other members
  byte-identical, shifted 208 B), obj/p_sev120.objx p_se (347 condition bytes, same size: 100 trails → any costume,
  240 costume-2/3/4 duplicates + 7 costume-2 sounds → never), 12 new files at the end.
- Outfits: 1 = normal, 2 = Limit, 3 = Master, **4 = Valor, 5 = Wisdom, 6 = Final** (Codex texture variants).
  Re-run --dry = "already" everywhere. Static only, NOT played.
- Mat to check (CPU Minimal, Order's Sanctuary): Customization / character-select outfit choice offers 6 outfits
  for Sora (2/3 newly selectable); each outfit in battle (model textures, Keyblade trail normal + EX, HUD face, EX
  banner "My friends are my power!"); mirror-match CPU (= outfit 2 Limit); menu pictures are per character (same for
  every outfit) — only the battle HUD face is per outfit (all = 1P face). If outfit 5/6 misbehave in a menu (the
  vanilla game only ever used up to 4 = DLC slot), drop them: EXTRA in the script → (4, 'Valor', 1457) only.
