# KH2 magic as HP attacks: Firaga / Thundaga / Blizzaga (2026-10-14)

Static research on `dumps/ULUS10566-test145-exp2.iso` and the clean ISO (both read-only). Not run in game.

Dry-run tool: **`tools/scripts/spot33_magic.py ISO CLEAN_ISO [--out NEW.objx]`**.
- It adds the 3 hits, 15 magi, 6 pieces, 6 script blocks and 6 actions below. Rerun-safe.
- Templates come from Cloud's untouched file in the **clean** ISO, because the test ISOs carry an old edit of
  Cloud's own file.
- Checked on test 145:
  - file 1,363,456 → 1,370,480 B
  - magi 27 → 42 rows, sorted, float tail unchanged
  - atkp 70 → 73, sorted
  - plya 34 → 40
  - blocks 96 → 102, layout valid
- Formats are in notes/hitbox-shapes.md: §4 magi, §1/§10 events, §9 end rule.

## 1. What makes a projectile deal HP damage
A magi's damage is its hit row:
- Magi row +0x0A / +0x0C = **atkp hit id**, looked up in the **owner's** atkp (FUN_08807860 → FUN_08837f14(owner, id)).
- The hit row decides Bravery vs HP. A magi copy pointed at an HP hit is an HP projectile.

Cloud's rows (atkp +0x04 "kind", +0x08 flags, +0x10 power):
| hit | kind | flags | pow | delivered by | type |
|---|---|---|---|---|---|
| LAND_LONG2 / LONG2_2 (Fire bursts / balls) | 8 | 0x80 | 10 / 7 | magi 0x124 / 0xD5-D7 | Bravery, magic |
| LAND_LONG3 / LONG4 (Fira / Firaga) | 7 | 0x80 | 5 / 10 | magi 0x125 / 0x0 | Bravery, ranged |
| LAND_LONG1_2 / _3 (Blade Beam wave) | 7 | 0x80 | 5 / 10 | magi 0xCD / 0x52C | Bravery, ranged |
| LAND_FINISH2 (Meteorain rising orb) | 8 | 0x80 | 10 | magi 0x9 | Bravery |
| **LAND_FINISH2_3 (Meteorain meteors)** | **3** | **0x92** | 0 | magi 0x233 tree / 0x7BD tree | **HP** |
| AIR_FINISH1_3 / _4 (Braver shockwaves) | 3 | 0x12 | 0 | magi 0x528 / 0x529 | HP |
| LAND_FINISH1_3, AIR_FINISH2_3 (melee HP finishes) | 2 | 0x12 | 0 | op 0x43 / op 0x00 | HP |

- **kind** = attack class: 0/1 Bravery melee, 2 HP melee, 3 HP ranged, 7 Bravery ranged, 8 Bravery magic.
  FUN_08ada0a4 upgrades 0/1 → 2 and 7/8 → 3 in a special state, and FUN_08adb330 / FUN_08809f00 use it for clashes.
- **Flag 0x10** at +0x08 is set on every one of Cloud's HP-damage hits and on no Bravery hit. **Flag 0x80** marks
  projectile hits.
- I did not trace which of these the damage code reads. **Copying a whole HP projectile row (LAND_FINISH2_3) gives
  all of them**, and Meteorain proves that row deals HP in game.
- The piece must also be an HP piece (plya +0x0F = 2, flags 0x00010012), as Cloud's are.

**Appending magi rows works:**
- Rows are 204 B, **sorted by s16 id** (binary search FUN_088289d0). New ids must be > 0x7C0 and < 0x8000.
- Insert them before the 49-float tail and bump header +8. The tail must stay right after the rows; FUN_08828a98
  finds it from the count.
- The chunk is heap-copied at its exact size, so growing is fine.
- New float values: append to the tail and bump header +0x0C. Parameter indexes are u8, so at most 255.

New HP hits (spot33_magic NEW_HITS; ids after 0x1006):
| id | name | row | knock-back from |
|---|---|---|---|
| 0x1007 | FIRAGA | LAND_FINISH2_3 | LAND_FINISH1_3 (react 0x0C, blow away 50 / 0.5 / 40) |
| 0x1008 | THUNDAGA | LAND_FINISH2_3 | its own (react 0x04, push 8 / 0.5) |
| 0x1009 | BLIZZAGA | LAND_FINISH2_3 | AIR_FINISH1_3 (blow away 30 / 10 / 30) |

## 2. Spawn frames in Cloud's blocks (script frames, 60/s; GMO anim end × 2)
| motion / block | move | magi spawns (one-shot op 4) | end markers | anim |
|---|---|---|---|---|
| 10041 / 59 var 1 | Fire | **f24**: 0xD5 (−25°), 0xD6 (0°), 0xD7 (+25°) | op28 70, op1e 82 | _701A 0-46 → 92 |
| 10042 / 59 var 2 | Fira | f24 0x125 (ball → 0x128 multi-burst) | same block | |
| 10043 / 59 var 3 | Firaga | f24 0x0 (slow homing ball, life 300) | same block | |
| 10040 / 60 | Blade Beam | sword hit LAND_LONG1 34-40 + **f36** 0xCD (wave → 0x52C) | op28 60 | _702A 0-51 → 102 |
| 10095 / 65 (orig.) | Meteorain | f20 0x9 (rising orb, Bravery), **f80 0x233** (meteors, HP) | op28 134 | _705A 0-88 → 176 |
| 10098 / 68 (orig.) | air Meteorain | f20 0x9, **f66 0x7BD** (→ 0x7BE → 0x7C0, impacts 0x2C7 / 0x52E) | op0a 0-170, os02 168, op28 134 | _707A 0-88 → 176 |

Spell sound (one-shot op 0x15) comes ~4 frames before the release (Fire f20, Meteorain f2).

**Variant trap:**
- Block 59's spawns are conditioned on the motion's **type-7 variant** (cond byte 0 = 1/2/3).
- spot33_chain SLOTS writes variant 0, so a plain SLOTS copy of 10041 would spawn **nothing**.
- spot33_magic drops the template's op 4 records and adds its own spawns with cond 0.

**KH2 release moments:**
- From the P_EX100.mset triggers (`kh2_triggers.py`). Trigger frames are already 60/s, the same as script frames.
- In the table: release = trigger type 17 + type 31 frame; "free" = type 14 range start.

| KH2 | clip | release | free | clip end (script) |
|---|---|---|---|---|
| 224 MAGIC_FIRE | Firaga cast | 22 | 30 | 80 |
| **228 MAGIC_FIRE_FINISH** | big cast | **28** | 36 | 100 |
| **232 MAGIC_FIRE_AIR** | | **28** | 36 | 84 |
| 236 MAGIC_BLIZZARD | | 16 | 24 | 72 |
| **240 MAGIC_BLIZZARD_FINISH** | | **40** | 48 | 92 |
| **244 MAGIC_BLIZZARD_AIR** | | **36** | 44 | 76 |
| 248 MAGIC_THUNDER | | 18 | 26 | 68 |
| **252 MAGIC_THUNDER_FINISH** | | **34** | 42 | 98 |
| **256 MAGIC_THUNDER_AIR** | | **30** | 38 | 82 |

Only 224 / 228 are baked in dumps/kh2anim yet. build_sora.sh bakes the others on demand.

## 3. Recipes (spot33_magic.py SPELLS)
Re-timing is piecewise linear like AUTHOR, but keyed on the release instead of hits (AUTHOR needs ≥ 1 template hit):
- 0 → 0
- template release → KH2 release
- template end (op28 start / os02) → new end; later frames shift by the same amount
- The air blocks keep §9: op0a end, os02 and op28 ≤ clip end (asserted).

| motion → block | spell | template | KH2 clip | spawns | end | piece |
|---|---|---|---|---|---|---|
| 10310 → 96 | **Firaga** (ground □) | 10041 Fire plumbing | 228 | f28 **0x7C1** | op28 90 | 0x1010 HP_FIRAGA |
| 10311 → 97 | **Thundaga** (ground □) | 10095 Meteorain (orig.), release 80 | 252 | f34 **0x7C4** | op28 88 | 0x1011 HP_THUNDAGA |
| 10312 → 98 | **Blizzaga** (ground □) | 10041 | 240 | f40 **0x7CB, 0x7CC, 0x7CD** | op28 82 | 0x1012 HP_BLIZZAGA |
| 10313 → 99 | Firaga (air □) | 10098 air Meteorain, release 66 | 232 | f28 0x7C1 | os02 76, op0a 0-78 | 0x1013 HP_A_FIRAGA |
| 10314 → 100 | Thundaga (air □) | 10098 | 256 | f30 **0x7C8** | os02 74 | 0x1014 HP_A_THUNDAGA |
| 10315 → 101 | Blizzaga (air □) | 10098 | 244 | f36 0x7CB-0x7CD | os02 68 | 0x1015 HP_A_BLIZZAGA |

Magi (copies of Cloud's rows; fx = Cloud's effects for now):
- **Firaga:** 0x7C1 ← 0xD6 (Fire's centre ball: straight, life 42, fx 1 fireball), HP 0x1007. Its burst children
  0x52D / 0x124 (r 2.5, fx 20 / 5) become 0x7C2 / 0x7C3, also HP 0x1007.
- **Thundaga:**
  - ground: 0x7C4 ← 0x233; 0x7C5 ← 0x2DB (falling strikes); impacts 0x7C6 ← 0x2C7, 0x7C7 ← 0x52E.
  - air: 0x7C8 ← 0x7BD, 0x7C9 ← 0x7BE, 0x7CA ← 0x7C0.
  - All on HP 0x1008, fx 4 (meteor).
  - Meteorain's meteors are already HP. The new rows only give Thundaga its own hit. Pointing the spawn at 0x233 /
    0x7BD directly also works.
  - The rising orb 0x9 (a Bravery hit) is dropped.
- **Blizzaga:** 0x7CB / 0x7CC / 0x7CD ← 0xD5 / 0xD6 / 0xD7 (3-way spread ±25° = ice shards), HP 0x1009. Bursts
  0x7CE / 0x7CF.
  - It still looks like fire.
  - Only the first HP hit to land matters: HP damage = Bravery, which drops to 0 after the hit.
  - Alternative: Blade Beam's ground wave (0xCD → 0x52C, r 2 / 4) copied with hit 0x1009, and block 60's sword hit
    (op00 LAND_LONG1) dropped.

Pieces: appended rows, copies of Cloud's **original** LAND_FINISH2 (ground) / HP_A_METEO1 (air):
- role 0 (starter), +0x0E 4 (HP long), +0x0F 2 (HP), flags 0x00010012
- 0x02 = skip the distance check, so the player can use them at any range. The 7–25 m window is used by the CPU;
  Firaga / Blizzaga min distance is set to 0.
- +0x05: 2 = only on the ground, 1 = only in the air
- +0x1C motion, +0x21 banner (set it once the text entries exist), +0x64 name
- New ids 0x1010–0x1015. Piece lookup is linear, like 0xFF0, so any unused id works.
- Proposed `NEW_PIECES` mechanism for spot33_combos.py: `{id: (Cloud piece name, motion, banner, name)}`. It copies
  the row from the clean Cloud file (not #33's re-used LONG rows) and appends it. spot33_magic does exactly this.

**Input / slot:**
- HP abilities go into any ground (+23 = 0) or air (+23 = 1) HP slot in Customization: neutral / toward / away □.
  The slot is the player's choice, not the piece's.
- comb: one single-step action each, **1021–1026** = [piece] (alt −1, parent −1, like Cloud's 327 / 928).
- ablt (spot33_moves.py MOVES): use template Cloud idx **11** (Meteorain, ground HP) and **18** (air Meteorain):
  ```
  (17, 'Firaga', '…', 1, 0, 1021, 11, LV), (18, 'Thundaga', …, 1, 0, 1022, 11, LV), (19, 'Blizzaga', …, 1, 0, 1023, 11, LV),
  (20, 'Firaga', …, 1, 1, 1024, 18, LV), (21, 'Thundaga', …, 1, 1, 1025, 18, LV), (22, 'Blizzaga', …, 1, 1, 1026, 18, LV)
  ```
- GMO (build_sora.sh):
  - SLOTS `_730A=_701A _731A=_705A _732A=_701A _733A=_707A _734A=_707A _735A=_707A` (motion index = block 96–101, same
    order)
  - MOVES / AIR `_730A=nat:228 _731A=nat:252 _732A=nat:240 _733A=nat:232 _734A=nat:256 _735A=nat:244`

**Order in the build:**
1. spot33_magic after spot33_chain (blocks must be appended in order: 96 = the next one after SLOTS' 95)
2. then spot33_effects / spot33_soundids. The copied blocks carry Cloud's sound ids, and spot33_soundids maps them.
   The `--out` copy of test 145 still has Cloud's ids in blocks 96–101.

## 4. Limits
- **ablt: 803 of 808 rows used.** Six new abilities need 809. Either drop one, or patch the EBOOT row cap first:
  - EBOOT VA 0x088B1CF0 (ELF 0xAECC8, ISO 0x1C6CC8): the row limit constant 808 (0x328) (notes/abilities-owner33.md §2)
  - e.g. 808 → 832 rows (0x340)
- Learned list: 150 per owner, about 116 after these.
- comb: 25 of 256 entries.
- Banner text (fighter `text` chunk) has **0 slack** in test 145.
  - "Firaga" + "Thundaga" + "Blizzaga" (air versions share them) ≈ 60 B.
  - spot33_battlenames must grow the chunk (rebuild_arc + pkg_put) instead of writing in place.
  - Then set plya +0x21 (game index = entry − 1).
- Ability names / descriptions: spot33_moves TEXT0 placeholders and spot33_desc (enough placeholders, see
  abilities-owner33.md).
- **magi objects: a global pool of 32** (FUN_08ad0810, 0x130 B each) for both fighters. Thundaga spawns
  0x233 → several 0x2DB → impacts; Blizzaga up to 3 balls + 6 bursts. Fine for one cast, tight if Cloud's Meteorain
  runs at the same time.
- atkp ids must stay the biggest (binary search). magi ids sorted and > 0x7C0.
- Effects: fx ids index #33's own FEPA (a copy of Cloud's, own FEP id since spot33_effects).
  - Useful ids: 1 fireball, 5 / 20 Firaga burst, 4 meteor, 2 blade beam.
  - New looks (ice, thunder) need new FEP resources. That is not possible yet.
  - spot33_effects must keep running after spot33_magic; it only touches the effe chunk.

## 5. Test 149 bug: Firaga / Blizzaga shot nothing — FIXED in spot33_magic (test 150)
- Spawn worked (BP 0x08AD0978 logged a0 = 0x7C1), but the ball was deleted at once.
- Why (decompiled): magi update FUN_08ad1588 → bullet create FUN_08ad43b4 → init (vtable+0x14 = FUN_08ad96f0) →
  FUN_08ad46f0 → spawn place FUN_08ad5d70. For magi row **+0x1e = 6** (Fire balls 0xD5–0xD7, 0x0) the place is a
  LIVE EFFECT of the caster: obj+0x38 = op 4 arg, or row +0x20 (= 19) if the arg is 0 → FUN_08ad3c24 →
  FUN_08ad3690 → FUN_088aa350(effect lib, id 19, fighter+0x4c8). No such effect → init returns 0 → bullet freed.
- FEPA id 19 = FIGA_START (Fire charge), auto-spawned only by the FEPA row bound to slot **_701A** frame 24 (Cloud's
  Fire anim). Sora's spells use new slots _730A… → no anchor.
- Fix: SPELLS `fx=[(release−2, 19)]` = one-shot op 0x19 id 19 in the spell block (Firaga ground/air, Blizzaga
  ground/air). Thundaga (0x233 / 0x7BD rows, +0x1e = 0 = at the fighter) never needed it — Mat saw its meteor.
- Other +0x1e spawn modes (FUN_08ad5d70): 0 fighter pos, 1/2 bone row+0x20 (FUN_08836648), 3/4/8/9/11/12 target
  (+0x80 / +0x100), 5 magi obj, 7 origin, 10 FUN_08b34db8, 13 lock-on partner. +0x22 = direction (1 facing,
  2 fighter+0x20, 3 magi obj, 4 = normalised).
- Tools: `ppbpwatch.py PORT SECS ADDR…` (breakpoint logger, DUMP=N dumps v0 object), `ppmagi.py` (one-connection
  RAM snapshots), Ghidra `ReadWords.java OUT ADDR N` (overlay data words, e.g. vtables).

## Thundaga straight down (2026-10-15, in progress — offline decoding, game tests pending)
❗ 2026-10-16: the parameter guesses below are WRONG (p0-8 = count / first delay / interval, not x/y/z offsets;
pitch + = DOWN). Correct decode + the redo (spot33_thundaga.py, test287): notes/thunder.md.
Goal (Mat): bolts strike STRAIGHT DOWN onto the foe, not Meteorain's slanted meteors.
- magi row (204 B): +0x1e u16 spawn mode, +0x20 bone/effect, +0x22 u16 direction mode, +0x24 u16 (1 everywhere),
  +0x26 u16 target choice for modes 3/4 (2 = the other target pointer), +0x2c f32, +0x34 f32.
  Bytes +0x40..+0xCB = 140 one-byte indexes into the chunk's float table (header +0x0C = count, floats after the
  rows; Sora's file: 49 floats, idx 0 = 1.0, idx 1 = 0.0). Parameters come in (min, max, per-frame change) triples.
  Working guesses from Cloud's rows: p0-8 spawn offset x/y/z (Meteorain strike 0x2DB: x 5, y 18, z 16 with -2/frame),
  p18-20 speed, p24-26 PITCH (air spawner 0x7BD: -89.9 = straight down, with direction mode 0), p27-29 yaw
  (0x2DB: -10..10 random), p30-38 spins, p42/p48 sizes, p75/78/81 scale x/y/z (Fire ball 1.5), p93/p129 lifetimes,
  p102/p108 9999 ranges.
- Spawn modes (FUN_08ad5d70): 0 caster +0x80, 1/2 bone (+0x20), 3/4 = TARGET (+0x80 / +0x100) clamped by
  FUN_08ad3a2c(minH, maxH, minV, maxV, …) — spawn point = caster + horizontal/vertical distance to the target
  clamped into those ranges (instance +200..+0xd4), 5 = parent magi object, 6 = live effect, 7 origin,
  8/9 like 3/4, 10 FUN_08b34db8, 11/12 = target +0x80/+0x100 (prefers the first target pointer), 13 lock-on partner.
- Direction modes: 0 = default axis (+pitch/yaw params → 0x7BD points down with pitch -89.9), 1 = caster facing
  (+0x90), 2 = caster +0x20, 3 = parent magi object's direction, 4 = normalised.
- Plan: strike rows 0x7C5 / 0x7C9 → spawn mode 11 or 12 (at the foe), offset y ≈ +8 (p3/p4), x/z small random
  (2-4 strikes around the foe), direction mode 0 + pitch -89.9 (p24/p25), faster speed, shorter life; spawner
  0x7C4 / 0x7C8 count/interval → 2-4 strikes. Test live with tools/scripts/ppmagipatch.py (patches every copy of
  Sora's MAGI chunk in RAM; values must exist in the float table), then bake into tools/scripts/spot33_thunder.py.
- spot33_thunder.py written (2026-10-15, offline): strike rows 0x7C5 / 0x7CA → spawn mode 11 (target feet),
  p0/1 x ±0.5, p3/4 y 9.0, p6/7 z ±0.5, p8 0 (Meteorain had z -2/frame), direction mode 0, p24/25 pitch -89.9,
  p27/28 yaw 0, p57-59 (30, 30, 9) [guess: speed], p129-133 life 20 [guess]; spawners 0x7C4 / 0x7C9 p93/94 = 3
  [guess: strikes per cast]. All values already in the float table (size-neutral). Thundaga pieces 0x1011 / 0x1014
  min distance 7 → 0 (the only field that differed from Firaga's working pieces; the coordinator saw no Thundaga at
  7-13 m on neutral □ in test188). Applied: dumps/ULUS10566-test193-thunder.iso (= test188-anchor + this).
  NOT verified in game yet. Unknowns to bisect live: whether mode 11 spawns at the foe (the clamp FUN_08ad3a2c is only
  used by modes 3/4/8/9/11/12 — its limits come from the instance +200..+0xd4, source not decoded), which param is
  the speed, and whether p93 is the strike count.

## Firaga = KH2 flame flurry around Sora (2026-10-15, Mat: "it uses cloud's fireball instead of a flurry of flames
around you like KH2")
- spot33_magic.py SPELLS 10310 / 10313: magi = [] (no projectile), new `hits=` list → op 0x00 body-sphere hits
  (shape 0x06 r 2.5): 0x1006 hold hits at 24/30/36/42, HP blow-away 0x1007 at 48-56. Look = FIRE_RING_FX one-shots
  (FEPA ids from spot33_firefx.py, effects helper). Effect 19 (FIGA_START) no longer needed (it only fed the magi ball).
