# Ability table (ablt) — findings 2026-10-11

Where: `PACKAGE.BIN` → `general_archive/main/main.bin` (MPK) → `system.bin` (ARC) → chunk `ablt`.
ISO offset (ULUS10566): `0x16CB18D4`. Tool: `tools/scripts/ablt_patch.py`.

Header: `"ABI "`, `0x20100611`, count = 790, 0. Then 790 rows × 40 bytes.

| Off | Type | Meaning | Confidence |
|-----|------|---------|-----------|
| +0  | u8  | index within owner | sure |
| +1  | u8  | owner: character number 1–34, `0x40` = general skills | sure |
| +2  | u16 | name text id | likely |
| +4  | u16 | description text id | likely |
| +6  | 6 bytes | mostly `ff` — maybe links to other abilities | ? |
| +12 | u16 | **action id** (the move). `0xFFFF` on all 168 passive skills | very likely |
| +14 | u16 | 0x1e (30) on most moves — CP cost? | ? |
| +16 | u16 | 0x0f (15) — level? | ? |
| +18 | u16 | 90/100/120/… — AP to master? | ? |
| +22..+29 | | flags | ? |
| +30 | u8  | 7 for most; 1/2/3/4 for some — form/stance? (owners 7, 22, 23, 31 have stances) | guess |

Owners 1–31 = the 31 fighters. 32–34 = extra (assist/boss?). Number → name mapping: **unknown, find in game**.
Owner 29 has 78 rows (way more than others) — maybe the character with the biggest kit (Gilgamesh? Shantotto?).

Action ids are global (0 … ~1017). Actions themselves (animation, hitbox, damage) live somewhere else — not found yet.
Candidates: `battle.bin` chunks (`atkp`, `chrg`, `spec`, `wpnp`), per-character files in PACKAGE.BIN.

## Test 1 — `dumps/ULUS10566-test1-swap.iso`
For owners 1–31, the action ids of each owner's two lowest-index moves are swapped (62 rows, only bytes +12/+13 changed).
Owners 1–8, 10–23: idx 0↔1. Owner 9: 1↔2. 24: 5↔6. 25: 6↔7. 26: 13↔16. 27–30: 1↔2 (28: 2↔3). 31: 5↔6.
Expected if right: a character's first move shows its own name in the menu but does the second move in battle.
Result: inconclusive — tester pressed the HP button by mistake (Cross Slash/Braver are normal HP moves).

## Test 2 — `dumps/ULUS10566-test2-brv-is-hp.iso` (2026-10-12)
Every Bravery row (+22 == 0) for owners 1–31 got the action id of that owner's first HP move (ground/air matched by +23).
388 rows changed, only +12/+13. Plan: `notes/test2-plan.txt`.
Result (Cloud): **Bravery button does nothing at all**, ground and air. HP button normal.
→ The game DOES read the action id from this table at runtime. An HP action in a Bravery slot is rejected
  (probably the action's own data says it's HP, and the Bravery button path refuses it).

## Test 3 — `dumps/ULUS10566-test3-one-brv.iso` (2026-10-12)
All Bravery rows of each owner → that owner's first ground / first air Bravery action. HP rows untouched. Plan: `notes/test3-plan.txt`.
Result (Cloud): **no change at all** — every Bravery and HP move is normal.
→ Conclusion from tests 2+3: ablt +12 is read and *validated* (HP action in a Bravery slot = move refused),
  but it is NOT what picks the animation/attack. The executed move comes from somewhere else
  (probably keyed by ability id owner/idx, e.g. a per-character table). Next: find the code that reads ablt +12.

## Other containers
- `system.bin` chunks: chrp, rwdp, enmp, grwp, fnct, fncs, **ablt**, item, acsr, eqpm, eqaa, eqao, eqit, eqac, chrl, amas, …
- `battle.bin` chunks: spec, sklp, nekp, scrb, camr, chrg, atkp, scra, wpnp.
- `objentry.bin`: object/character list with model names (`p_sev100` …) — roster work later.
- Text (`general_archive/main/EN/ability.bin`, …) is obfuscated. Decoder not found yet.

## How abilities turn into moves (from code, 2026-10-12)
- `FUN_088b1cc0` copies `ablt` into a heap buffer sized for **0x328 = 808 rows** (790 used → **18 free slots**).
  Rows pointer at `0x089D7294`, header at `0x089D7290`.
- `FUN_088b1d9c(ability_id)` = binary search for a row by its u16 id (+0: idx | owner<<8).
- Battle `FUN_08ab7f40(state, char_action_table, ...)`: for every **equipped** ability, looks up its row, then walks the
  **character's own action table** (count at +2, u32 offsets from +4; each entry starts with u16 action id, alt id at entry+4)
  and sets an "enabled" bit for every entry whose id == row +12.
  → **ablt +12 doesn't pick the move. It switches on matching entries in the fighter's own action table.**
- Fits test 2 (Bravery rows pointing at HP ids → no Bravery entry enabled → button does nothing)
  and test 3 (only one Bravery entry enabled).
- `FUN_08a651a8` / `FUN_08a65248` (battle): slot (0..11) → ability id → row +12. Probably the command-slot → action lookup.
- Next: find the per-character action table (in the fighter's file in PACKAGE.BIN). That is where moves are really defined.
