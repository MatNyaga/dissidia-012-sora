# Sora EX equipment + EX movement (Claude equipment helper, 2026-10-16)

Source packages (Codex): tools/codex/20261016-earned-ex-native, tools/codex/20261016-earned-ex-equipment
(Q-20261016-CODEX-003 / -004). Base for this work: dumps/ULUS10566-test305-outfits.iso
(sha256 5b517bffc3e106b91d7e24b280b7970440ab910436b773b27267a43f64f347c3, re-hashed 2026-10-16T19:30Z).
No C compiler for Allegrex on this machine (no psp-gcc / mips gcc / clang mips / capstone) → all game code is
hand-written assembly through tools/scripts/mips_asm.py; Codex's earned_ex.c is the rule reference only.

## Code-room allocation (EBOOT dead function 0x089a8b14-0x089a8f0c, 254 words, probe test272p PASS)
| range | owner | what |
|---|---|---|
| 0x089a8b14-0x089a8b23 | (original) | first 4 words kept original = probe hook (same convention as TRI) |
| 0x089a8b24-0x089a8b93 | spot33_exspeed.py | EXRUN (25 of 28 words) |
| 0x089a8b94-0x089a8f0b | reserved: Phase 2 EX-gain code (spot33_reflect.py / spot33_exitems.py) | 222 words |
The function's own jump table at 0x089d1fb4 is dead with it and untouched. Not used: TRI range (spot33_reflect),
EBOOT gap 0x089DD3C0, reserved assist words 0x088F9CA4 / 0x088F6C04 / 0x08929060.

## 1. Phase 1 — EX-only run speed (spot33_exspeed.py) — static, 2026-10-16T19:33:52Z
**Hook verified statically (battle overlay, clean = test305 bytes):** FUN_08b2d2cc(fighter) has exactly ONE caller
(the call at 0x08b372a0 in FUN_08b36d2c = the input/move-vector update; called only when fighter+0x380 bit 2 is
clear and FUN_08b30544 says the fighter is in a "can move" state). It adds the vector at +0x550 to +0xb0, then sets
the speed +0xbc = (spec row from +0x39c: field +0x18, or +0x1c when +0x384 bit 0 is set) × +0x3d4 × +0xbc and stores
it at 0x08b2d380; if FUN_088374b0 is true for the fighter it multiplies +0xbc by spec+0x64. +0xbc is rebuilt from the stick vector before each call (otherwise vanilla
would compound), so a multiply after the store is applied once per update and disappears as soon as a gate fails.
- Site (2 words, in place, overlay keeps its size): 0x08b2d380: the original store + call pair becomes a call to
  EXRUN (0x089a8b24), with the original store moved into the delay slot.
- EXRUN gates: owner byte (fighter → pointer at +0x2f8 → byte +6) == 33, motion u16 s0+0x180 == 2 (free run `_010A`; ground only — air
  moves, dashes, dodges, attacks have other motions), native EX predicate FUN_08b34378(s0) (+0x5b2 bit 4, +0x5a4,
  not during a burst). Pass → +0xbc × EXSPEED_MULT (a float constant). Always ends by jumping on to FUN_088374b0 with the fighter as
  argument and the original return address 0x08b2d388, so the rest of FUN_08b2d2cc is byte-for-byte native.
- Not touched: +0x3bc animation rate, +0x3d4 (gear/effect 0x11f factor — still multiplies as before, no double
  count), +0x3d8 jump, vertical velocity, the shared spec row 1, other owners, normal mode.
- Multiplier: env EXSPEED_MULT (default 1.10, script refuses outside 1.0-1.25). EXSPEED=0 = exact rollback.
- Static checks on test307: disassembly reviewed (scratch eq/dis.py); re-run = "already done: no change";
  EXSPEED=0 → EBOOT + battle overlay byte-identical to test305; 1.25 → 1.10 swap rewrites only the constant.
- Disc: dumps/ULUS10566-test307-exspeed.iso = test305 + spot33_exspeed.py (1.10),
  sha256 0d5d11e14fa9773008e97bb33b53987e0df7f49b64e8b961a7880173ac2050ff.
- Coexists with spot33_reflect --apply-code (it re-reads the overlay from disc and only rewrites its own sites/cave).
- build_sora.sh line (for the canonical owner to add, after spot33_reflect): `python3 -I $S/spot33_exspeed.py "$2"`.

### 1.1 Runtime check needed (not done: emulator off-limits for this helper)
Tool: tools/scripts/ppexspeed.py (read-only memory logger, holds the stick, appends dumps/exspeed_runs.csv).
On test307, Order's Sanctuary, CPU Minimal (opponent idle, e.g. CPU Sora), flat open floor, no gear that changes
movement:
1. `python3 -I tools/scripts/ppexspeed.py PORT normal1 4 1,0`
2. enter EX Mode (R+Square with a full EX gauge), walk back to the same spot, `... PORT ex 4 1,0`
3. wait for EX to end, same spot, `... PORT normal2 4 1,0`
Pass: ex speed / normal ≈ 1.10 (both normal runs equal), bc in EX ≈ 1.10 × bc normal, 3d4 unchanged, dy ≈ 0.
Also look: no stutter at run start/stop, EX expiry mid-run drops back at once, CPU Sora in EX also faster (same
code), air movement unchanged. If the ratio is 1.00 while bc is 1.10× → +0xbc is not what moves him (then the
real consumer must be traced; roll back with EXSPEED=0).

## 2. Phase 2 — Kingdom Key / Protect Belt: static findings (2026-10-16T19:41:20Z) — NOT built, decisions needed
**Item table** = main.bin → system.bin chunk `item` (header 'ITEM', u32 count 677 @+8, u32 sets 53 @+12), 104-B rows
sorted by id (0..677, 673 missing), then 53 set rows (52 B), 16-B footer. Row: +0 id, +2 name (item.bin), +4 help
(item_help.bin), +0xc slot (0 weapon, 3 armor), +0x18 u32 equip mask, +0x1c 4 fixed stat slots (effects 0x6b ATK,
0x6c DEF, 0x6d HP, 0x6e, u16 values at +0x3c; every row has exactly these 4 → item rows cannot carry special
effects like accessories do). Loader FUN_088c0d70 allocates size + (683 − count) × 104 → 683-row ceiling.
- **Free IDs: 678, 679** (append after 677 keeps the sorted order; 679 rows ≤ 683). 673 is a gap but inserting there
  would put a new id in the middle of every save's sorted inventory → avoid.
- **Inventory = save data**, 683 slots × 4 B (u16 id, u8 count, u8 flags; FUN_088b8538 clears, FUN_088b8634 fills
  ids from the table on NEW GAME only, count at +0x15f4), looked up by binary search over the saved count
  (FUN_088b715c via FUN_088b8fd0). Nothing merges new table rows into an existing save → **an existing save (Mat's)
  can never hold id 678/679** unless code appends them. New game: they get a slot with count 0.
- **Eligibility:** menu FUN_08af3b64 / EBOOT FUN_088c1ae8 / FUN_088c1234 use `1 << ((character − 1) & 31)`; owner 33 →
  bit 0 = owner 1 (Warrior of Light). Sora's equippable gear today = WoL's. All 32 bits belong to playable owners
  (1..32, 23 = Chaos), so no free bit: a Sora-only item needs an id-aware check in those 3 functions (menu overlay
  08af8e14 effective mask, EBOOT 088c1ae8 "still allowed" check of the 4 equipped slots, 088c1234 list search).
  Without it WoL could equip them (the EX effects would still be owner-33 only).
- **Text:** item.bin 762 entries; 677-761 are set / accessory-style names, only #677 'Not Used' is filler.
  item_help.bin uses another layout (not decoded yet). New names = grow the table (ability.bin growth garbled
  before) or re-use filler entries at the same size.
- **Native EX gain path:** FUN_08aec558 (EX-gauge object event handler) case 0x16 → FUN_08aec628 (object, source,
  pointer to an amount) = add the amount to the gauge word (block at fighter+0x52c, +0x18), clamp 0..10000, blocked by effects 0x53/0x56, no 0xfa conversion.
  FUN_08aec1ec (float amount) = same plus 0xfa conversion (used by the per-frame fill/drain FUN_08aebf94 / FUN_08aec000).
  Native precedent: damage handler FUN_08aecf30 sends event 0x16 with an amount through FUN_08afd170 for accessory
  effect 0x158 (Promyvion Shard; 0x156/0x157 send 0x15/0x14); the target is the handler's second argument, whose first
  word is the fighter. → recommended call for our adapter: FUN_08afd170 with Sora's participant handle, event 0x16
  and the amount (the game's own route, respects
  "EX gauge blocked" effects). The handle ↔ fighter link still needs a runtime trace.
- **Hooks (plan):** combo hits = Sora's Bravery-dealt record (FUN_08ae45b8 → FUN_08ae6d2c), defense = C2's
  guard-outcome-3 branch (already in spot33_reflect's cave; it runs once per guarded clash) + C7 (projectile
  reflected). HP Reflect = C2 path where TRI_HPROW found an HP row. Equipped weapon/armor of a battle fighter:
  loadout +0x9a 4 × u16 via FUN_088b7b18 / FUN_088b97e8 (Codex) → needs a runtime read of Sora's live loadout.
- Code room for all of it: EBOOT 0x089a8b94-0x089a8f0b (222 words) + 68 B left in the battle cave.

### Decisions needed (stop point)
1. How Mat gets them: (a) new ids 678/679 + one-time EBOOT migration that appends both to the loaded inventory
   (count 1) = "owned from the start", works on Mat's save; or (b) re-use two existing rows every save already has
   (removes two vanilla items).  Recommendation: (a).
2. Sora-only: patch the 3 eligibility functions (recommended) or accept WoL can equip them (effects Sora-only).
3. Tuning (Codex proposal, not approved): +100 EX per connected combo hit, cap 300 per combo, none in EX;
   +200 per successful guard (armor); HP Reflect in EX +500 instead of +200 (armor-gated).
4. Names: grow item.bin/item_help.bin by 2+2 entries vs. reuse filler.
Runtime traces needed before writing the gain code: Sora's participant handle (event target), live loadout ids,
one connected combo hit + one guard + one HP Reflect passing the planned hook points.
- **Runtime 2026-10-16T20:00:31Z (Claude, test309 vs Lightning): steady ground run 0.2808 → 0.3089 units/frame in EX = ×1.100; +0xbc 0.14040 → 0.15444; +0x3d4 unchanged. PASS.**

## 3. Phase 2 BUILT — test310-exitems (static only, 2026-10-16T20:00:55Z)
Decisions (coordinator, Mat autonomous): owned from the start via a one-time inventory append; Sora-only via id checks;
Codex tuning as env defaults; names/help by growing the text tables (round-trip proven).
**Disc:** dumps/ULUS10566-test310-exitems.iso = test309-combined + spot33_exitems.py + spot33_reflect.py --apply-code
(EXITEMS on), sha256 7be0ff2c51151083f0a1fa454aa91fc3689899915e40df8f337d8cdd3c68fbb5.
### Data (tools/scripts/spot33_exitems.py)
- item rows 678 Kingdom Key = Broadsword clone (slot 0), 679 Protect Belt = Leather Armor clone (slot 3), mask 0x1,
  name idx 762/763, help idx 784/785; system.bin 357272 → 357480 B, main.bin 1220416 → 1220624 B (pkg_put moves it to
  the ISO end), every other chunk/member byte-identical.
- item.bin (UTF-16, spot33_desc decode/encode) 762 → 764 entries; item_help.bin ('UTF8' variant: u32 magic, u32 n,
  u16 offsets ×2, entries u16 len + bytes XOR per u16 with the 16 keys at EBOOT 0x089d68aa, key index = entry + word)
  784 → 786. Both formats round-trip byte-exact before editing; all old entries re-decoded identical after.
  Vanilla equipment help entries are only "　" — if the menu never shows item help for gear, the text is unseen.
### Code (EBOOT 0x089a8b94-0x089a8da4 = spot33_exitems, 131/132 words)
| site | what changes |
|---|---|
| 0x088b8fd0 (FUN_088b8fd0, every item-inventory lookup) | the first two words become a jump to ENSURE 0x089a8b94 (stack set-up kept in the delay slot) |
| 0x088b8778 (new-game init → empty stub 088b87ac) | the call to the empty stub becomes a call to NEWGAME_GIVE 0x089a8c38 |
| 0x088c1afc (FUN_088c1ae8 mask) | the call to FUN_088c1998 becomes a call to ELIG_MASK 0x089a8c98 |
| 0x088c132c, 0x088c1364 (FUN_088c1234 list search) | the row-mask load becomes a call to ROWMASK 0x089a8cf4 |
| menu 0x08af9004 (FUN_08af8f84), 0x08af8ed8 (FUN_08af8ea8) | the call to FUN_08af8e14 becomes a call to MENU_FIX 0x089a8d2c |
- Inventory facts: 683 × (u16 id, u8 count, u8 flags) at (save base, the word at 0x089d712c) + 0xf6e0, count +0x15f4, sorted, binary search;
  add-item FUN_088b8da8 sets flag 8, "seen" FUN_088b8e14 flag 2; new-game init writes flags 5. ENSURE appends with
  count 1, flags 0x0b, only for that inventory, only if the list ends below 678/679 (≤ 681 entries).
### Battle effects (tools/scripts/spot33_reflect.py, switch EXITEMS, needs TRINITY_CTL; env EE_HIT_GAIN 100,
EE_COMBO_CAP 300, EE_COMBO_GAP 60 frames, EE_COMBO_IN_EX 0, EE_GUARD_GAIN 200, EE_HPREF_GAIN 500, EE_DUP_FRAMES 180)
- EE_HIT 0x089c225c + EE_GUARD 0x089c2340 behind TRI (TRI range now 494/523 words); EE_B (EE_HAS 0x089a8da4,
  EE_PIDX 0x089a8dec, EE_GIVE 0x089a8e44, EE_PROJ 0x089a8e68) + state 0x089a8edc-0x089a8f0c (2 × 0x18: combo used,
  last hit frame, guard attacker / motion / motion time / frame).
- Sites: battle overlay 0x08ae6ed4: the native event-0x10 send through FUN_08afd170 becomes a call to EE_HIT (in
  the SITES table, guarded + rollback like the others); our C2 gets a call to EE_GUARD right after it saves its
  return address; our C7 gets a call to EE_PROJ (arguments: the attacker state and the projectile's +0x68 word). Cave 448 → 464 B.
- Gain = FUN_08afd170 with the participant, event 0x16 and the amount (native EX-add event). Participant = entry 0
  or 1 of the table pointed to by 0x089d69f8, whose word 0 == the fighter (FUN_0888700c builds them; FUN_08afcd40 hooks listeners at +0xd0; the EX-gauge listener is FUN_08aebee8's
  0x10-byte object → FUN_08aec558 case 0x16 → FUN_08aec628).
- Event 0x10 (FUN_08ae6d2c): attacker's participant gets {damage, gain, …} when a hit takes Bravery; s1 = attacker
  battle state, s1+0x10 = the hitting fighter (≠ participant[0] for assist hits → skipped). Magic Bravery hits
  (Firaga) also count as combo hits. Reflected hits only happen in EX → no combo gain anyway.
- Live loadout: *(fighter+0x30c) = 0x778-B record copy made at fighter setup (FUN_088355ac), set index (s8) +0x773,
  4 slot ids u16 at +0x10 + set*0xc6 + 0x9a (FUN_08847830 / FUN_08847b8c read the same).
- Not rewarded: projectile guards outside EX (C3 non-EX path untouched), HP-ness of reflected projectiles (C7 gives
  the guard amount).
### Static checks
re-run of both scripts = no change; EXITEMS=0 on both → main.bin, main_lang.bin, objx, EBOOT, battle + menu overlay
identical to test309; reapplied; disassembly of all new code + sites reviewed (scratch eq/ee_dis.txt); spot33_exspeed
--dry on test310 = already done.

### 3.1 Runtime trace plan (coordinator runs it when the emulator is free; test310, Sora with both items equipped)
Fighter F = tools/scripts/ppplay.find_fighter(ws, 33). Gauge = float at *(F+0x52c)+0x18 (0..10000).
1. Inventory (title → load save → Customization): u32 *(0x089d712c) = B; count u32 B+0xf6e0+0x15f4 should be 679;
   entries B+0xf6e0+4*677 / +4*678 = `a6 02 01 0b` / `a7 02 01 0b`. Customization → Sora → Weapon: Kingdom Key
   listed; Armor: Protect Belt. Warrior of Light's lists: not offered / greyed (check both). Equip both, save.
2. Battle setup: u32 0x089d69f8 = T; T[0], T[1] = participants; one has word 0 == F (else EE_PIDX is wrong).
   R = u32 F+0x30c, s = s8 R+0x773, u16×4 at R+0x10+s*0xc6+0x9a → contains 678 and 679 (else EE_HAS reads the
   wrong record). u32 F+0x324 grows ~60 per second (else EE_COMBO_GAP / EE_DUP_FRAMES units are wrong).
3. Combo (normal mode): breakpoints 0x089c225c (EE_HIT, every Bravery hit) and 0x089a8e44 (EE_GIVE: a1 = amount).
   Ground combo on CPU Sora: EE_GIVE a1=100 on hits 1-3 only, gauge +100 each, 4th+ hit no call; >1 s pause → next
   combo gives again. Also break 0x08aec628 once to see the native add run. In EX Mode: no EE_GIVE from hits.
4. Guard (normal): let the CPU hit Sora's guard (melee): 0x089c2340 (EE_GUARD) hit per guarded clash, EE_GIVE a1=200
   once per enemy attack (multi-hit attack = one reward). In EX vs Cloud HP attack (Braver / Cross-Slash, Reflect):
   EE_GIVE a1=500 (not 200+500). EX projectile reflect: 0x089a8e68 (EE_PROJ) → EE_GIVE a1=200.
5. Without the items equipped: no EE_GIVE at all. CPU Sora without them: none. Long fight: no freeze.
- Runtime 2026-10-16T20:09:57Z (Claude, test310): no freeze 200 s with hooks live (items unequipped); inventory count 679 with 678/679 present (count 1). Equip/gain checks pending (menu).

## 4. Phase 3 — EX Mode page text (spot33_exitems.py, test311-extext, static only, 2026-10-16T20:17:40Z)
- Runtime (coordinator, test309): EX ground run 0.2808 → 0.3089 units/frame = ×1.100, +0xbc 0.14040 → 0.15444, +0x3d4
  same, dy 0 → Phase 1 USER-SIDE PASS. test310: inventory append verified (count 679, a6 02 01 0b / a7 02 01 0b),
  200 s battle with EXITEMS hooks, no freeze. Equip + gain traces still pending.
- Customization → EX Mode page = menu overlay FUN_08b22ec0, table 0x08b23f28: 0x20-B rows (int character; 2 × 7 u16:
  burst, burst 2, 23 Regen, 68 Critical Boost, up to 3 effects; -1 none), terminated by -1. Ids index
  text/EN/mess_pk_exmode_0.bin group 2 (names) / group 3 (descriptions) (mess pak: 4 groups, header u16 at +10 =
  count, (offset,size) at +0x10; gaps/tail filled with 0x77). Owner 33 had NO row → his page was empty.
- Change: row 22 (character 23 = Chaos, unplayable; burst 0, no effects) → character 33: burst 82 Trinity Limit,
  Regen, Critical Boost, 83 Ultima Weapon (ATK) (HP-based bonus + 50%, per notes/ex-damage.md; not "flat"), 84 Reflect
  (GUARD), 85 Haste (RUN) ("Runs 10% faster on the ground", measured). Groups 2/3 82 → 86 entries; other groups
  byte-identical; EXITEMS=0 → file + menu overlay identical to test309 (checked), re-run = no change.
- dumps/ULUS10566-test311-extext.iso = test310 + this, sha256 792cf55542921bcb90afecd30ce447582d78eddad31450a0d426fe4c7a3994b9.
- Mat check: Customization → Sora → EX Mode shows Trinity Limit + the 4 effects (text fits the box, circle glyph
  shows); Cloud's page unchanged; a Chaos page (if any menu shows one) would now show nothing.
- **Runtime 2026-10-16T20:33:03Z (Claude, test311, Mat AFK asked me to test):** Customization: Kingdom Key ×1 (NEW) in Sora's weapon list, Protect Belt ×1 (NEW) in armor list; both equipped, help texts show ("Sora only. …"). EX Mode page: Trinity Limit + Regen/Critical Boost/Ultima Weapon (ATK)/Reflect (GUARD)/Haste (RUN), ◯ glyph OK — BUT the page header portrait is another character's (blue armour), not Sora's. LOOK cycles Normal / Alt 1 / Alt 2 / DLC 1 / DLC 2 / DLC 3 (6 outfits; reset to Normal). Battle vs Lightning: three 4-hit ground combos → EX gauge 0 → 300 → 600 → 900 (exactly the 300-per-combo cap) = Kingdom Key gain PASS. Not checked: guard/Reflect gain, WoL can't equip.

## 5. EX Mode page header portrait fix — test312-exportrait (static only, 2026-10-16T20:43:19Z)
- Runtime test311 (coordinator): items NEW + equipped, help OK, Kingdom Key cap works (0 → 300 → 600 → 900 over
  three 4-hit combos), EX page shows Trinity Limit + effects, ◯ OK; header picture = a blue-armoured character.
- Cause: the header is EBOOT FUN_088d5638 (called by menu FUN_08af3824 / FUN_08af371c): face = bases[0] + owner − 1,
  name = bases[1] + owner − 1, assist face = bases[0] + assist − 1 (record +0x2bfc = the set's assist). EX scene
  bases (0x08b23f22) = 15395 / 15363 → owner 33 got 15427 (an EN lpk label) and 15395 = Warrior of Light's EX-page
  face (the blue armour). The main Customization header (bases 3114/3081) was already fine (slot 32 = Sora).
- Fix (spot33_exitems): EBOOT sites 0x088d56a4 / 0x088d56d8 (owner s3) and 0x088d5714 (assist s0):
   the native "base + owner − 1" pair becomes a call to PICID3 / PICID0 (0x089a8da8 / 0x089a8da0): owner 33 with base 15395 →
  15434, base 15363 → 15435, everything else the original sum. Pictures appended byte-preserving (table grows,
  offsets shifted, old bytes kept; exact strip for rollback): menu_pk_exmode_gim_0 entry 74 = id 15434 = Sora's
  customize face (customize entry 74; the 32 EX faces are byte-identical to the customize faces), EN
  menu_lpk_exmode_gim_0 entries 74 (empty) / 75 = id 15435 = Sora's name plate (lpk_customize 41). EX scene packs
  720480 of the 0xb6800 (747520) B load buffer (FUN_088d00fc group 0x10, list 0x08b24368).
- Room: exitems now 0x089a8b94-0x089a8de3 (148/148 words); spot33_reflect EE_B moved to 0x089a8de4 (49 words, state
  0x089a8edc), EE_PROJ moved behind TRI (0x089c2454; TRI range 510/523). **Do not re-run the new scripts on
  test310/test311** (old layout); rebuild from test309 or use test312.
- Checks: re-run both = no change; EXITEMS=0 on both → EBOOT, battle + menu overlay, main.bin, main_lang, objx,
  exmode text and both EX packs byte-identical to test309; reapplied.
- dumps/ULUS10566-test312-exportrait.iso = test311 + this, sha256 ebbb829852ec4f17fa5928b28ec73be40f6796c0acf9b3a4deb11a6a3110e510.
- Mat check: EX Mode page header shows Sora's face + "Sora" name plate; with an assist set, the assist's face is
  still right; main Customization header unchanged; WoL's EX page unchanged.
- Runtime 2026-10-16T20:52:36Z (Claude, test312): EX Mode header shows Sora face + name. PASS. No freeze 150 s.
- 2026-10-16T21:15:27Z Mat: 40% → EXSPEED_MULT 1.40 default; runtime test314 0.2808 → 0.3931 (×1.400). EX page text 'Runs 40% faster on the ground.'

## 6. HP Reflect = full EX refill (innate) + Protect Belt per hit — test318-reflectrefill (static, 2026-10-16T21:54:12Z)
- Mat: "a HP reflect attack in EX mode should refill the EX gauge" + Protect Belt = +10 % of the bar on EVERY blocked
  hit (normal and EX, per hit, no dedup).
- EE_GUARD (C2) rewritten: owner 33 → participant; EX Mode + HP attack (kind 2 + HP flag, or TRI_HPROW, now
  table-bounded) → event 0x16 with EE_HPREF_GAIN = 10000 (native add clamps = full), NO item needed, once per
  incoming attack (same dedup: attacker / motion / motion time / EE_DUP_FRAMES); every other blocked hit (and later
  hits of an already-refilled HP attack) → Protect Belt equipped → +EE_GUARD_GAIN = 1000, per hit. EE_PROJ (EX
  projectile reflect) → belt +1000. Env: EE_GUARD_GAIN, EE_HPREF_GAIN, EE_DUP_FRAMES.
- Texts: Protect Belt help "Sora only. Every blocked hit fills\n10% of the EX gauge."; EX page Reflect (GUARD):
  "Blocking casts Reflect: attacks, / spells, even HP attacks go back. / Reflecting an HP attack refills / the EX
  gauge." (5 lines like the game's longest; ≤ 32 chars). Haste line (40 %) from the speed change kept.
- Disc dumps/ULUS10566-test318-reflectrefill.iso = test317-hprowbound + spot33_exitems + spot33_reflect
  --apply-code + spot33_desc.py, sha256 851b9d1c36f5c22ad3f3d634b24cd8663fe4631da545d314aa595fc33ec17c7b. Re-run both = no change.
- Code room left: TRI range 520/523 words (3 free); EE_B 0x089a8de4 49 words + 13 free before state 0x089a8edc;
  spot33_exitems 148/148 (0 free); battle cave 464/512 B (48 B free); spot33_exspeed 25/28.
- Runtime check: EX Mode, guard a CPU HP attack (Cloud Braver / Cross-Slash) → EX bar jumps to full once; normal-mode
  guards with the belt: +10 % per blocked hit (multi-hit = per hit); without the belt only the HP-Reflect refill.
- Runtime 2026-10-16T22:10:34Z (Claude, test318): Protect Belt +1000 per blocked hit observed 3×. HP Reflect refill in EX not yet observed.
- Runtime 2026-10-16T23:48:09Z (Claude, test319 vs CPU Cloud): HP Reflect in EX refill PASS (3428 → 9982 while guarding).

## 7. Level scaling of Kingdom Key ATK / Protect Belt HP — test323-itemscale (static, 2026-10-17T01:07:31Z, sha256 eb5e86d2fd4fddca61a19e8ceb90f10a5421f522aa4e7872a8676ffc05c0e3e1)
- Stat path (EBOOT, shared by battle fighter setup and every menu stat build): FUN_088bf238 → FUN_088beb84 asks the
  provider per effect id → FUN_088be63c(out, max, effect, RECORD, provider) walks the 4 equipped slots and calls
  FUN_088bdb2c with row + 0x1c, which reads the fixed slots through the loader's pointers (row+0x20+8i →
  row+0x3c+2i; 0x6b ATK, 0x6c DEF, 0x6d HP). Record byte +1 = level (FUN_088cba10 sets 1).
- Hook: 0x088be63c: the function's first two words become a jump to STASH, with the stack set-up kept in the delay
  slot (STASH keeps the record argument in SCR); 0x088be96c: the call to FUN_088bdb2c becomes a call to SCALE (the
  delay slot still passes the 5th argument, SCALE keeps it). SCALE: if the row
  id is ours, writes the scaled value into the row's RAM value (row+0x3c+2*slot) from the record's level, then
  jumps on to FUN_088bdb2c. Only Sora can equip the items, so the shared RAM row is always his.
- Room: the DEAD jump table of dead function 0x089a8b14 at 0x089d1fb4-0x089d2083 (52 words; its only reference is
  that function's own indirect jump, re-checked: no pointer words / address-pair uses elsewhere in EBOOT or the 3 overlays).
  Uses 168/208 B (code 31 words + SCR + table 12 B per item). NOT the EBOOT gap 0x089DD3C0: it lies OUTSIDE the
  EBOOT LOAD segment (filesz ends at 0x089DD3C0), so bytes there are never loaded.
- Formula: 32-level segments, V0 Lv1, V1 Lv33, V2 Lv65, V3 Lv97, V4 slope point (Lv100 = top tier); points = best
  vanilla gear of the template's category at that level: swords (type 0) ATK 4/40/58/63(+→67), light armor (type 21)
  HP 428/1882/2610/2610(+→2973). Samples: ATK Lv1 4, Lv38 42, Lv60 55, Lv100 67 (vanilla best ≤38: 40, ≤60: 58);
  HP Lv1 428, Lv38 1995, Lv60 2496, Lv100 2973 (vanilla ≤38: 1882, ≤60: 2610).
- Help texts get "ATK/HP grows with Sora's level." (3rd line).
- Caveat: the item LIST "+N" reads the RAM row directly → shows the value of the last stat build (Sora's own level
  once his status/preview was computed; the Lv1 value before that after a fresh boot).
- EBOOT diff vs test321: only 0x088be63c/40, 0x088be96c and the jump table. Re-run = no change.

## 8. Full set: Save the King (680) + Crown Pendant (681) — test324-fullset (static, 2026-10-17T01:19:58Z, sha256 683acfc6f5c5268c0df96c224a62805ffc81cdb2211ef59d905a0e777b12b724)
- Items: 680 "Save the King" = clone of Buckler (57, shield, type 12), 681 "Crown Pendant" = clone of Bronze Helm
  (81, helm, type 17; helms' main stat is slot 3 = BRV, plus DEF 2). Names item.bin 764/765, help item_help 786/787.
  Owned from the start: ENSURE now appends every missing id 678..681 in order (also upgrades saves that already got
  678/679); new game gives all 4. Sora-only: the same 3+2 checks, now an id RANGE (678..681).
- spot33_exitems code rewritten compact (140/148 words, was 148): ENSURE loop, NEWGAME, ELIG/ROWMASK/MENU_FIX range
  checks, PICID, + SHIELD.
- Level scaling (dead jump table, 192/208 B): 680 DEF 3/39/61/67(→73): Lv1 3, Lv38 42, Lv60 57, Lv100 73 (best vanilla
  shield ≤38: 39, ≤60: 61); 681 BRV 38/167/255/255(→290): Lv1 38, Lv38 180, Lv60 241, Lv100 290 (best helm ≤38 167,
  ≤60 255).
- Save the King: every hit is built by FUN_08807860(hit, source, owner, id) (EBOOT; projectiles via FUN_0880b05c);
  hit +0x2a = power % (100), copied by FUN_088395b8 into the damage record +0x32, which FUN_08ae45b8 uses as the
  Bravery damage multiplier. SHIELD (site 0x088079ac: the call to 0x089a3890 becomes a call to SHIELD, end of FUN_08807860): if
  source != owner (= a reflected hit: C4 melee reflect, C7-deflected projectiles; Sora's own hits have source ==
  owner), source != 0, and the owner has item 680 → +0x2a = +0x2a × SHIELD_MULT (×192 >> 7 = 1.5). HP-attack Reflect
  damage (= the attacker's own Bravery, FUN_088131bc) does not use +0x32 → NOT boosted.
- Crown Pendant: FUN_08aec000 per-frame EX drain 10000/duration·dt (0x08aec160) × CROWN_DRAIN 0.7 when the gauge's
  fighter has 681 → EX lasts 1/0.7 = 1.43× as long (help: "drains 30% slower"). HELM = last 12 words of the battle
  cave (spot33_reflect; cave now 512/512 B FULL).
- Room left: exitems 8 words; jump table 16 B; EE_B tail 13 words; TRI 3 words; battle cave 0; exspeed 3 words.
- Runtime checks: (1) Customization: all 4 items listed + Sora-only, DEF/BRV values at Lv38 = 42/180; (2) EX Mode vs
  CPU Cloud, guard a Bravery attack with / without Save the King: reflected Bravery damage number ×1.5 (breakpoint
  0x089a8d74, our store of the new power: 150 vs 100); HP-attack reflect unchanged; (3) EX Mode, stand still, full gauge:
  EX duration in seconds without / with Crown Pendant ≈ 1 : 1.43 (breakpoint 0x08b63164 hit each EX frame with it).
- 2026-10-17T01:21:45Z Crown Pendant = EX lasts x1.30 (Mat): CROWN_DRAIN default 1/1.3 (0.769, cave constant 0x3f44ec4f); help 'Sora only. EX Mode lasts 30% longer. / BRV grows with Sora's level.' Disc dumps/ULUS10566-test328-crown30.iso = test324 + both scripts re-run, sha256 94da61f4378faa2599345ca90f6a668663d69958888948804b2cf6b6c846ee99. Runtime: EX duration with/without helm ~1.30 : 1.
- 2026-10-17T01:49:39Z Item help box limit (Mat test331: text outside the box): vanilla item help = max 2 lines, max ~31 visible chars (most ≤ 25). All 4 Sora item helps rewritten to 2 lines ≤ 28 chars: 'Sora only. Combos build EX. / ATK grows with Sora's level.', 'Sora only. Blocks: EX +10%. / HP grows with Sora's level.', 'Sora only. Reflect dmg +50%. / DEF grows with Sora's level.', 'Sora only. Longer EX (+30%). / BRV grows with Sora's level.' Disc dumps/ULUS10566-test334-itemtext.iso = test333 + spot33_exitems (item_help only), sha256 71d95f48b71cfc49cfafd3d38ccded27db98edde5d99550e9141da70a7bef190.

### HP projectile refill repair — Codex — 2026-10-17T02:13:23.309533+00:00
Transferred canonical spot33_reflect.py now routes incoming projectile hit through existing EE_GUARD: kind3HP gets innate10000 and accepted caster/motion/time/frame dedup; BRV Belt1000 preserved; self-owned repeat rejected. test336-hpproj SHA25669965250e084f834e7b198fa5d04c408ffc35bf2fbfbed0afe7ec72f1132e91a = confirmed335 +212code bytes ONLY (fullISO comparison), TRI520/523 unchangedbudget. Original335 regression fails bothHP cases; repaired passes, melee/BRV/owner/nonEX-helper/dedup/register tests pass. Static28PASS/24INFO. Runtime pending: safe alternate PPSSPP memstick/config routing not yet verified; no original-save writes/gameplay launch. Exact evidence and inheriteddedup limitations tools/codex/20261017-hp-projectile-refill/HANDOFF.md.

## 9. RR-12 □ panel fix — PANEL_LIT (Claude RR static-A helper, 2026-10-18T17:59:57Z, test346-rr, static only)
Mat (p16): □ "Can be equipped by" lit all 33 portraits for Kingdom Key (WoL's real list correctly omits it). Cause: the
Customization panel mask = FUN_08af8ea8 → MENU_FIX = −1 while Sora is edited (owner 33 = bit 0 = WoL, so no mask can
single him out). spot33_exitems PANEL_LIT (EBOOT 0x089a8dc4, 8 words; range now 148/148 full) replaces the panel's lit
test at menu 0x08aff32c: items 678-681 → lit only when s4 == 32 (Sora's sprite slot after spot33_charpanel). Details,
lifecycle audit and runtime tests: notes/release-rr-static-a.md.
