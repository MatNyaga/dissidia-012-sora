# Ability text in Customization: info panel, □ command chart (2026-10-17, ability text helper)

Mat (test321): "Customization → Abilities → □ on Sora's abilities shows no additional description."

## What □ opens: the COMMAND CHART (static, menu overlay)
- □ on an attack ability → FUN_08ad788c → FUN_08ad887c(list): the selected ability + every listed ability whose
  ablt +6 parent is it (its chains, max 9 ids). Each id is looked up in **command_list_param.bin** by FUN_08ad113c
  (linear search, so record order does not matter). No record → nothing drawn (= Sora's empty page).
- `command_list_param.bin` = standalone PACKAGE file (pkg index 4910, 23,268 B on the clean disc), loaded by
  FUN_08ad103c into an exact-size heap block: "ACMD" 12 10 08 20 + 8×FF; +0x10 s16 n8 = 1, +0x12 s16 n40 = 581;
  n8 × 8 B (u16 = group-1 text id of the line-drawing character list, entry 0 "━┃┳┣┗┻╋"); n40 × 40 B records:
  `+0 u16 ability id | +2 s16 header text | +4 9 × (s16 input text, s16 description text), −1 = end`.
  Owners 1-32 have records (no 23); owner 33 had none.
- Texts = **group 1 (OFF4)** of `text/EN/mess_pk_customize_ability_0.bin` (u32 count 2604, u32 offsets in 4-byte
  units, entry = u32 length + UTF-16LE, byte j of entry L ^ KEY[(2L+20+j)%32] — voice_text.py's codec).
  Group 0 (u16 table) is the short info-panel text (ablt +4, spot33_desc.py).
- Header = the chart: icons joined by ━, end "━━Wall Rush (→)" / "━━Chase" / nothing (spells). Rows (max 10 on
  the screen in total, pages of 7) = input icon | description, description tail "/" + effect icons, optional
  coloured note `\x10脁！` text `\x1b` (vanilla "Move OK"). Chain headers are merged into the parent's
  line by line (the LONGER line wins), so a chain header = blank cells `\x1e＂` + ┳ / ┃ / ┗ + □ icon.
- Icons `\x15` + char (high byte 0x22 = icon set, low byte − 1 = index), meaning from vanilla statistics:
  ground ◯ presses 1-6 `∘∙√∛∡∢` (single press `∗`), air ◯ presses 1-6 `∤∥∦∧∨∩` (single `∣`), ground □ `∪`, air □
  `∳`; numbering continues ground→air (Climhazzard ∘ ∙ ∦). Tails: `≘` on every HP hit, `≚` on strong hits, `≙` on
  area / pull moves. ⚠ The Customization help legend (mess_pk_customize_resident_0 group 2 #55-57) lists ≛ crush
  defenses, ≙ blocks attacks, ≚ invincibility, ≘ precise timing — that does NOT match how the chart uses ≘/≚
  (≘ is on every HP attack), so the chart probably uses another icon atlas; Sora's texts copy vanilla usage.

## Fix: `tools/scripts/spot33_cmdlist.py ISO [--dry] [-v]` (build_sora.sh, right after spot33_desc)
- 23 records (0x2100-0x2116, names checked against ability.bin) + 68 new group-1 texts (ids 2604-2671, deduped).
- Sizes: command_list_param.bin 23,268 → 24,188 B (in its old 12 sectors); the pak stays 281,840 B: group 0 gives
  the bytes back by emptying 326 unused "Name NN" fillers (no ablt +4 points at them; same method as spot33_desc,
  ~30 fillers left for future group-0 text): group 0 128,302 → 122,480 B, group 1 153,500 → 159,316 B. All vanilla records/texts
  byte-identical (asserted); rerun = "no change"; changed texts → our old records/texts are rebuilt.
- Content (accurate to the current moves, notes/abilities-owner33.md "Four combos" + spot33_chain AUTHOR):
  Combo Plus (6 phases = 9 presses / 12 hits → Wall Rush →), Air Combo Plus / Aerial Spiral / Aerial Dive (5
  phases), Slide Dash (6), Dodge Slash (5); HP: Explosion, Aerial Finish, Firaga/Thundaga/Blizzaga ground + air;
  chains Upper Slash ×2, Guard Break ×2, Dodge Slash > Explosion, Magnet Burst, Retaliating Slash, Horizontal
  Slash, Aerial Sweep (coloured note = when to press □, e.g. "After swing 2 or 5"). Vanilla has max 6 numbered
  presses, so Sora's 9-press combos are shown as phases ("Slash three times in quick succession").
  Wall Rush arrows from the hit templates (0x36e launches up → ↑, 0x37d → ↘, Cross-slash/Guard Break → →).
- Disc: dumps/ULUS10566-test322-abilitydetail.iso = test321 + spot33_cmdlist (static only), sha256 25ec2c50…f4ba8f
  (only command_list_param.bin, the pak and their PACKAGE_INFO size fields differ from test321).
- Mat check: Customization → Sora → Abilities → □ on Combo Plus (chart + 6 rows, plus Upper Slash / Guard Break
  rows when those are equipped/listed), Air Combo Plus, a spell; icons look like vanilla Cloud's.

## Battle Tips (Customization page 2 → Battle Tips) — 2026-10-17, test326
- Viewer = EBOOT help system FUN_088fd928 (menu FUN_08af73d4, id 0x10, pack text/EN/mess_pk_customize_common_0.bin
  group 2 = titles 0-44 + pages 45-177). Topic list = **manual_param.bin** (member of general_archive/main/main.bin,
  loader FUN_088fc938, list builder FUN_088fd4c4): "MANU" header, +0x10 s16 28 categories, +0x12 s16 201 rows;
  8-B categories; 22-B rows: +0 s8 category (16 = Battle Tips), +1 u8 sub-list (0 TIPs, 1 Character Info),
  +2 s16 row id, +4 s16 unlock flag (−1 = always), +6/+8/+10 s16 new/read flags (−1 = none), +0xc u8 title text,
  +0xd 9 × u8 page texts (0xFF end). Flags = bits of DAT_089d726c. The loader allocates room for 0x1C categories
  and 0xCD (205) rows → 4 rows can be appended without code.
- Character Info is per SERIES (FF I … XIII, Secrets 1-3), not per owner → Sora had nothing (no Aerith slot).
- Fix: NEW `tools/scripts/spot33_tips.py ISO [--dry] [-v]` (build_sora.sh after spot33_cmdlist): row 201 (cat 16,
  sub-list 1, no flags, after "Secrets (part 3)"), group-2 texts 178 = "◇Character Info: KINGDOM HEARTS II", 179-185 =
  7 pages in vanilla style (Selphie's diary voice, ≤10 lines, ≤56 chars): Profile, Equipment/Attack Abilities (gear =
  WoL's eligibility, notes/ex-equipment.md), Combos, □ finishers, Magic, EX Mode, Trinity Limit + Sora-only gear
  (Kingdom Key, Protect Belt, "more gear made just for him" for the items still being added). Glyphs: ◯ `\x1e⼁`,
  □ `\x1e、`, R `\x1eⴁ`, L `\x1eⰁ`, ✕ `\x1e㄁`; heading `\x10膁！…\x1b`, highlight
  `\x10脁ﾁ…\x1b`. main.bin 1,220,752 → 1,220,784 B (in place; members after manual_param shift 32 B, found by
  name); the pak 88,544 → 93,264 B (moved to the ISO end; same heap slot as the 281 KB ability pak). Other groups,
  rows and texts byte-identical (asserted); rerun = "no change".
- Disc: dumps/ULUS10566-test326-battletips.iso (13fc0c9e…96c8ec) = test322 + spot33_tips. Static only.
- Mat check: Customization → page 2 → Battle Tips → Character Info list → last entry "KINGDOM HEARTS II", 7 pages.
