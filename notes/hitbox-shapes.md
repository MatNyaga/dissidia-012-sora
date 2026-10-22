# Hit shapes, magic (magi) and effects — how to make a body-centred AoE (Explosion), 2026-10-14

Research only (EBOOT decompile `dumps/decomp/all.c`, battle overlay, all 31 fighter files from `dumps/package/` and
#33's `obj/p_sev120.objx` from `dumps/ULUS10566-test123-sdgap.iso`). Nothing here has been run in game yet.

## Short version
- **op 0x00 / 0x43 param1 = hit-shape GROUP id.** It indexes the **p_se type 5 chunk** (1904 B, "hit-shape table"),
  not hibg (type 9) or type 6.
- Each group is one or more spheres. Each sphere sits on a **bone**, or on **0x4000 = the character's root**
  (position + facing).
- Sora's sword groups 0x30–0x36 use bone 50 = `r_wep`. That is why every hit follows the Keyblade.
- Cloud's file already has body-centred groups:
  - **0x06**: root, centre 1.0 up, radius 2.5 (used by AIR_FINISH2)
  - **0x21**: root, radius 7 (Limit Break hits)
  - **0x13**: root, 2 m in front, radius 2 (chase hits)
- Every fighter uses the same trick for area attacks. Exdeath's Almagest is radius 5 on the root; the Limit Break
  spheres are radius 7–24.
- **Cheapest AoE for Explosion: change 1 byte**, param1 0x31 → 0x06 on the EXPLOSION hit event (recipe A).
- **Bigger custom AoE**: append 2 records to type 5 (recipe A2, +64 B).
- **Visual effect**: one-shot event **op 0x19** (FEPA effect id). Cloud's Firaga burst = id 5 (recipe E).
- **magi** (projectiles): spawned by one-shot **op 4** (magi id) or **on hit by op 0x43** (param2). Type-5 magi rows
  are stationary bursts (Firaga explosion 0x124 = radius 2.5, lives 12 frames).

## 1. Hitbox events (p_se type 8, main event list)
Handler is FUN_08829930.

**op 0x00** (n = 2): `FUN_08833b80(fighter, p0 hit id, p1 group)`
- Sets bit p1 in the fighter's 64-bit "active shape groups" mask at +0x448. So **the group id must be < 64**.
- Creates (or reuses) a 0x220-byte attack object keyed by (hit id, group): FUN_0883e108 → FUN_0880b8e4, group at
  obj+0x80.

**op 0x43** (n = 7): same as op 0x00, plus extra on-hit data on the attack object:
| param | stored at | meaning |
|---|---|---|
| p2 | obj+0x20c | **magi id spawned when it hits a fighter** (FUN_0880b9c4 → vtable+0x11c = FUN_08b304c4 → FUN_08ad0978); −1 = none |
| p3 | obj+0x210 | arg for that magi |
| p4 == 1 | — | p5 → obj+0x214, p6 → obj+0x218 (FUN_08856d48 on hit, player only) |

Cloud examples:
- Cross-slash hits spawn magi 0x47c / 0x47d / 0x47e (the slash-mark effects).
- AIR_FINISH3_3 spawns 0x52a.
- Limit hits spawn 0x4ad.

**Per-frame hit test** = FUN_0880baa4. It walks the type-5 records with kind 4 or 6 (mask 0x50) whose group == obj+0x80
and whose group is active (FUN_08837d18).

For each kind-4 sphere:
1. Centre = bone matrix (FUN_088369a4) × record offset.
2. It is swept from last frame's position in steps of the radius (no gaps when the weapon swings fast).
3. It is tested against the target.

Kind-6 records of the same group are only counted there. They go to the per-fighter list +0x474, used by FUN_08809f00
(attack-vs-attack clash, likely).

## 2. Hit-shape table = p_se type 5
Loader FUN_088459e0: the type-5 chunk is copied into its own heap block, sized to the chunk, and kept at charData+0x18.
Per-kind lists are built at spawn (FUN_08831808).

**Header (16 B):** u64 default-on group mask (1 = group 0 = body hurt spheres), u32 count, u32 0.

**Record (32 B), linear scan (no sorting needed):**
| off | type | meaning |
|---|---|---|
| +0x00 | u8 | **group id** (= op00/op43 param1; 0 = body hurtbox) |
| +0x01 | 3 B | 0 |
| +0x04 | u8 | **kind**: 4 = hit sphere, 6 = clash/priority sphere (bigger), 5 / 7 = other (guard/search?), 0–3, 10, 11, 15 = body hurt parts |
| +0x05 | u8 | shape type, always 3 (sphere) |
| +0x06 | u16 | **bone index** into the model. **0x4000 = character root** (FUN_089a3efc: position/facing); any other 0x4000\|x = world identity |
| +0x08 | 3 × f32 | offset x, y (up), z (forward) in that bone's / the root's space |
| +0x14 | f32 | subtracted from centre y (always 0) |
| +0x18 | f32 | **radius** |
| +0x1c | f32 | second radius (always = +0x18 in all 31 files) |

Cloud bones: 3 = hip, 27 = waist, 29 = chest, 39 = neck, **50 = r_wep**.

### Sora's table (= Cloud's, 59 records, unchanged in test 123)
| group | records (kind: bone, offset, radius) | used by |
|---|---|---|
| 0x00 | body hurt spheres (kinds 0–3, 10, 11, 15) | always on |
| 0x06 | 4: **root (0, 1.0, 0) r 2.5**; 6: r 3.0 | AIR_FINISH2_1/2/3 |
| 0x13 | 4: root (0, 1, 2) r 2 | CHASE_ATTACK, SE_ATTACK_UPPER/LOWER, _ABILITY_FINISH |
| 0x14 | 6: root (0, 0.85, 0) r 1.1 | GUARD |
| 0x1a | 4 + 6: root (0, 0.9, 0) r 1.1 | FACT_LEAP / FACT_GRIND |
| **0x21** | 4: **root (0, 0, 0) r 7.0** | LIMIT_ATK01–06 |
| 0x30 | 4: r_wep x 0.4 and 1.4, r 0.8; 6: r_wep 0.9, r 1.5 | most combo hits |
| 0x31 | 4: chest r 1.0 + r_wep 0.41 / 1.4 r 0.8; 6: chest 1.2, r_wep 1.5 | NEAR3, AIR_NEAR2, Cross-slash (= Explosion now) |
| 0x32 / 0x33 | 4 / 6: root (0, 0.75, 1.8) and (0, 0.75, 0.25), r 0.8–1.3 | LAND_MIDDLE1 (+_2) |
| 0x34 / 0x35 | root (0, 0.8–1.6, 0.1–0.2), r 0.9–1.8 | AIR_MIDDLE1_0 / _1 |
| 0x36 | r_wep (1.3, −0.45, 0), r 1.3 / 1.5 | AIR_FINISH1_2 (Braver = Magnet Burst now) |
| 0x38 / 0x39 | root (0, 1, 0) r 1.5 / 2.0; waist r 1.5 / 2.0 | AIR_FINISH3 |
| 0x3c | root column (0, 0.5 – 4.4, 1.1) r 0.7 | LAND_LONG1 |

Free group ids in Sora's table: 0x01–0x03, 0x07–0x0d, 0x0f–0x11, 0x17–0x19, 0x1b–0x20, 0x22–0x2f, 0x37, 0x3d–0x3f.

### Area attacks in other fighters (kind 4, bone 0x4000, radius ≥ 2)
| file | group | sphere(s) | move |
|---|---|---|---|
| fiv200 (Exdeath) | 0x1f | (0, 1.5, 0) r 5 | ALMAGE1/2 (Almagest) |
| fiv200 (Exdeath) | 0x1a, 0x1b | column y 1.5 / 4.5 / 6.5, r 3 | TORNADO1–3 |
| thr200 (Cloud of Darkness) | 0x15, 0x16 | (0, 1.5, 0) r 5.5 | SNAKE_MIDDLE |
| thr200 (Cloud of Darkness) | 0x1f, 0x20 | ring of 9 spheres r 2 at 2.5 / 3.5 m | BR_L_SYOKU3 |
| six100 (Terra) | 0x0f, 0x11 | r 2.5 / 2.7 + column y 3 / 5 | ABI2 |
| sev200 (Sephiroth) | 0x13 | (0, 1, 0) r 3.5 | LONG_LOWER3 |
| nin200 | 0x31 | (0, 1.7, 0) r 2.8 | COMBO_HOLY2 |
| org210 | 0x3a, 0x3b | (0, 3.5, 0) r 6 | HP_L_BARK |
| org210 | 0x2a | r 24 | LIMIT_ATK04 |
| thr100 (Onion Knight) | 0x18 | (0, 1.1, 0) r 2.5 | AIR_NEAR_FINISH |
| gst200 | 0x0f / 0x21 / 0x24 / 0x25 | 4 spheres r 2–2.2 at ±2 m | JUDGEMANT (cross pattern) |

Every fighter has a "Limit" group of r 7–24 at the root.
→ A body-centred AoE is the normal way this engine does area hits.

## 3. Recipes for Explosion (motion 10095 = block 65 = slot _705A, test 123 file)
Block 65 hit events:
- 19–22 op43 LAND_FINISH1_1, group 0x31, magi 0x47c
- 38–41 op43 LAND_FINISH1_2, group 0x31, magi 0x47d
- **58–61 op43 EXPLOSION (0x1000), group 0x31, magi 0x47e**

### A — use Cloud's existing body sphere (1 byte, no size change)
In `obj/p_sev120.objx` (test 123), the EXPLOSION event's param1 is at **file +0x64A4: `31 00 00 00` → `06 00 00 00`**
(ISO offset 0x69B1BCA4 in test 123; the file moves between builds).
- Result: a 2.5-radius sphere centred 1 m above Sora's feet (clash sphere 3.0), in every direction, while the event is
  active (frames 58–61).
- Same idea for the first two hits: +0x6454 and +0x647C (`31` → `06`).
- Also set **param2 to −1**, so the Cross-slash marks stop appearing on hit:
  - EXPLOSION: +0x64A8 `7e 04 00 00` → `ff ff ff ff`
  - other hits: +0x6458 (0x47c) and +0x6480 (0x47d)
- Build-proof way: in spot33_chain.py COPY, after remapping hit ids, also set the op43 group (+16) / magi (+20) of the
  remapped events, for example a `SHAPE = {10095: {0x1000: (0x06, -1)}}` table.

### A2 — own bigger sphere (new group 0x3d, recommended)
1. Append 2 records to type 5 and set the header count +8: 59 → 61. The chunk grows 1904 → 1968 B; rebuild the ARC
   with `spot33_combos.rebuild_arc`. The heap copy is exact-size, so growing is fine.
   ```
   3d 00 00 00 04 03 00 40  00 00 00 00 00 00 80 3f 00 00 00 00 00 00 00 00 00 00 60 40 00 00 60 40   kind 4 hit   root (0,1,0) r 3.5
   3d 00 00 00 06 03 00 40  00 00 00 00 00 00 80 3f 00 00 00 00 00 00 00 00 00 00 80 40 00 00 80 40   kind 6 clash root (0,1,0) r 4.0
   ```
2. EXPLOSION event param1 → `3d 00 00 00`, param2 → `ff ff ff ff`.
- Scale guide: Cloud's body hurt sphere is r 0.9 at 1.1 up, so 1 unit ≈ 1 m. r 3.5 is a KH2-like burst; r 7 = Limit size.
- Demo: `scratchpad/aoe_demo.py IN.objx OUT.objx` (session scratchpad 37c8a793…) does A2 + E on a file copy.
  - Checked on a copy of test 123's file: only type 5 (+64 B) and type 8 (+16 B) changed, every other block is
    byte-identical, and the block layout checks out.
  - Not run in game.

### E — burst visual: one-shot op 0x19
Add a one-shot record to block 65 (16 B), then fix the block and table:
```
u16 frame, u8 0x19, u8 2, 4 B cond 0, u32 FEPA id, u32 0        e.g. 3a 00 19 02 00 00 00 00 05 00 00 00 00 00 00 00
```
- block byte +3 += 1, block u16 +6 (size) += 16
- shift later block offsets in the type-8 table

Handler (FUN_0882cec0 case 0x19): FUN_088a9de8(charData+0x5c = effect library, id, fighter+0x4c8). There is no
player-only check. Other fighters use this op 623 times; Cloud uses it 0 times.

Cloud effect ids that look like blasts (FEPA id → seen in):
| id | seen in |
|---|---|
| **5** | Firaga explosion (magi 0x124), attached to `root` |
| 20 | Firaga burst variant (magi 0x52d), world-placed |
| 16 | Braver ground shockwave (magi 0x529), `root` |
| 15 | magi 0x528, world |
| 19 | AIR_FINISH3 burst (0x52a/0x52b), `root` |
| 4 | Meteorain meteor (0x9, 0x233) |
| 9 | Limit (0x4ad) |
| 10–13 | Cross-slash marks |

Pick by eye in game; 5 first.

> **Correction (2026-10-14, notes/kh2-effects.md):** the "id" column above is the magi row's +0x04, which is a *bit
> number* into FEPA +0x3c, not a FEPA id. Op 0x19 looks up FEPA **+0x24 id**: id 5 = leaf DOGE_UKEMI (Cloud's
> air-recover whoosh). Firaga explosion for op 0x19 = **id 22** (FIGA_HIT_WALL; 21 FIGA_HIT, 23 FIGA_HIT_LAND,
> 73 FIGA_HIT_AIR). `tools/scripts/fep_dump.py ISO` lists every id → leaf.

### B — alternative: a magi burst
Copy magi row 0x124 (Firaga burst) as a new id > 0x7c0, e.g. 0x7c1, so the binary search stays sorted:
- hit (+0x0a) = 0x1000
- radius (+0x2c) = 3.5
- fx (+0x04) = 5

Spawn it with a one-shot op 4: `3a 00 04 02 00 00 00 00 c1 07 00 00 00 00 00 00`.
- magi header count +1 at +8; the row goes before the 49-float tail (+204 B).
- **Unknown:** where a fighter-spawned type-5 magi appears (root vs weapon vs target). Cloud's Braver spawns 0x529
  from its own script, so it probably appears at the fighter.
- A/A2 are fully understood, so use them first.

## 4. magi chunk ("MAGI", projectiles / bursts)
Loader puts it at charData+0x94 (FUN_08828a98): chunk, rows = chunk+0x10, tail = rows + count×0xcc.

**Header:** "MAGI", u32 0x20101011, u32 row count (27), u32 tail float count (49).

Then 27 rows × 204 B, **sorted by s16 id** (binary search FUN_088289d0), then 49 f32.

**Row:**
| off | meaning |
|---|---|
| +0x00 | s16 id |
| +0x02 | u16 ? (0/1) |
| +0x04 | **FEPA effect id** (visual) |
| +0x06 | 0xffff |
| +0x08 | u16 ? |
| +0x0a | **u16 atkp hit id** |
| +0x0c | u16 hit id 2 |
| +0x0e..+0x1c | 8 × u16 **child magi** (spawned on hit/end/split; 0xffff = none) |
| +0x1e | s16 **type**: 0 = travelling shot, **5 = stationary burst**, 6 = homing ball (uses +0x20), 8 = limit, 12 = ? |
| +0x20..+0x28 | small ints |
| +0x2c / +0x30 | **f32 collision radius / second radius** (× object scale, FUN_08ad1968) |
| +0x34 | f32 1.0 |
| +0x38 | u32 flags (0x8000, 0x80000, 0x200000, 0x40000000 tested) |
| +0x3c | 4 B |
| +0x40 | **46 × (min, max, per-frame delta) byte indexes into the float tail** (FUN_08ad0694: value = random(min..max), += delta per frame) |

Params seen:
- 0 = scale
- 25–27 = xyz scale
- 43 / 44 = lifetime frames (9999 = until it hits)
- 9–12 = spread angles for Firaga's 3 balls

**Spawn:**
- one-shot op 4 (u32 magi id, u32 arg)
- op 0x43 param2 (on hit)
- one-shot 0x29 / 0x2d / 0x33 (conditional variants)

All go through vtable+0x11c → FUN_08ad0978 (0x130-byte object from a pool of 32).

**Cloud's rows:**
| id | what |
|---|---|
| 0x0 / 0xd5–0xd7 | Firaga balls (type 6); 0xd5–0xd7 split into 0x124 / 0x52d bursts (type 5, r 2.5, life 12, hit LAND_LONG2) |
| 0xcd | Blade Beam (child 0x52c r 2 / 4) |
| 0x9, 0x233, 0x2db, 0x7bd–0x7c0 | Meteorain meteors (hit LAND_FINISH2(_3); impact children 0x2c7 / 0x52e r 2) |
| 0x528 / 0x529 | Braver-type shockwaves (r 2, life 10, hit AIR_FINISH1_3 / _4) |
| 0x47c–0x47f | Cross-slash marks (no hit) |
| 0x4ad | Limit |

Cloud's script spawns (one-shot op 4):
- block 59: Firaga variants 0xd5 / 0xd6 / 0xd7 / 0x125 / 0x0 per variant
- block 60: 0xcd
- block 63 (Braver): 0x529 @44
- block 64: 0x528 @0
- block 65: 0x9 @20, 0x233 @80
- block 68: 0x9, 0x7bd

## 5. Effects (effe chunk)
`effe` = MPK with `p_sev100.fep` (effect resources), **`p_sev100.feb` = "FEPA" effect table**, and `p_sev100.fxseb`
("FXSE", effect sounds).

**FEPA:** header "FEPA", u32 0x20100205, u32 size, u32 count (79), then 0x104-byte entries:
| off | meaning |
|---|---|
| +0x00 | pos xyz |
| +0x0c | rot xyz (degrees) |
| +0x18.. | scale |
| **+0x24** | **u32 effect id** (normally = index; weapon trails share id 8888 / 9999) |
| +0x28 | FEP resource index |
| +0x30 | int → start value |
| +0x44 | variant bit mask (costume / colour for trails) |
| +0x70 | attach mode |
| +0x74 | **motion frame to start at** (Cross-slash marks 38 / 58 / 76 match its hit frames) |
| +0x7c | flags (0x80 = not auto-spawned) |
| +0x88 | char[32] model name (`p_sev100_1p`; empty = world-placed) |
| +0xa8 | char[32] **node** (root, r_wep, hip, wep0, camera2_include) |
| +0xc8 | char[32] **motion slot** (_700A, _705A …) |

**Ways an effect starts:**
1. by id:
   - one-shot op 0x19 (id, value), op 0x2f, op 0x30
   - main op 0x66 (id, value, frame, …)
   - magi row +0x04
   - FUN_088aa5b8 = first entry with +0x24 == id
2. weapon trails: main op 0x2a (slot, id 8888 / 9999, mode) → fighter slots +0x5d8, spawned by FUN_0884e660 using the
   variant mask. Cond bytes [1] / [2] pick the variant. **op 0x2a = sword trail, not an explosion.**
3. **automatically when a motion starts**: FUN_088aa844 spawns every entry whose model name and motion slot (+0xc8)
   match the motion being played, unless +0x7c & 0x80.

   Cloud's Meteorain entries 34 / 35 are bound to `_705A` (start frames 12 / 100). So Sora's Explosion (slot _705A)
   may already spawn Cloud's Meteorain effect at frame 12, if Sora's model still registers as "p_sev100".
   Sora's GMO still has `p_sev100` part names; the name compare is the first 8 chars. To check in game.

   Editing entry 34's +0x28 (resource) / +0x74 (frame) in `p_sev100.feb` is a size-neutral way to give Explosion its own
   burst. Use mpk.replace + rebuild_arc.

Shared hit sparks come from a global table (FUN_0881591c), not the fighter file.

## 6. Script block layout (checked on all blocks of Cloud + Sora)
```
u8 id, u8 0, u8 main event count, u8 one-shot count, u16 one-shot list offset (= 8 + main events), u16 block size
main events  : u16 from, u16 to (0xFFFF open), u8 op, u8 n, 6 B cond (+0 variant, +1 mode, +2/+3 extra), n × u32
one-shot list: u16 frame, u8 op, u8 n, 4 B cond, n × u32     (FUN_08829104 picks, FUN_0882cec0 runs; any order)
```

**One-shot ops seen:**
| op | meaning |
|---|---|
| 3 | sound |
| 4 | **magi** |
| 6 | screen shake (frames, x%, y%) |
| 0x0f | footstep sound |
| 0x10 / 0x25 | camera |
| 0x11 / 0x12 | sound on bone |
| 0x15 | voice (player) |
| **0x19** | **effect** |
| 0x22 | (player) rumble / sound? |
| 0x2f / 0x30 | conditional effect |

## 7. Side findings
- **spot33_chain SCALE only scales the main events.** Explosion's one-shots (sounds 0x21b8d9–db, shakes, camera
  op25, op11 sounds) are still at Cross-slash frames 36–116. The block ends at 81, so the third set never plays. It
  should scale the one-shot frames too.
- **Magnet Burst (block 68, copy of Braver)** still spawns magi **0x529** at frame 44. That is Cloud's Braver
  shockwave, an r-2 HP hit (AIR_FINISH1_4) on top of the MAGNET_BURST hit.
- p_se type 6 (644 B) = angle-limited chains (±π limits, probably hair/cloth physics). Type 9 "hibg" is used by
  overlay code FUN_08acda90. Neither has hit shapes.
- Loader FUN_088459e0 (all.c ~36300) puts these at charData offsets:

  | chunk | +off |
  |---|---|
  | type 7 | 0x1c |
  | type 8 | 0x20 |
  | type 5 | 0x18 |
  | type 6 | 0x24 |
  | type 9 | 0x30 |
  | effe | 0x34 |
  | snd_ | 0x60 |
  | plya | 0x88 |
  | comb | 0x8c |
  | atkp | 0x90 |
  | magi | 0x94 |
  | brat | 0xa0 |

## 8. In-battle HP-attack name banner (follow-up, test 124)
**The banner text is selected by the plya piece, byte +0x21** (s8; −1 = no banner).

FUN_08b382b8 (start of an attack piece) calls FUN_08856d48(hud, fighter, banner index, 0) when the piece's byte
+0x21 (banner index) is not −1. That queues up to 6 banners, and
FUN_08856d70 renders them with FUN_0887ad78(charData+0xcc = the fighter file's `text` "mlng" table, 0, index).

Two other ways to show a banner exist:
- one-shot op 0x1d (n = 2: text index, flag; player only)
- op 0x43 with p4 = 1 (p5 = text index shown on hit, p6 flag)

**Index ↔ spot33_battlenames.py entry: game index k = entry k+1.**

The game's table model (FUN_0887a800 / FUN_0887a898) is: u16 N, then offsets at u16 positions 1..N, and index k uses
position k+1. That is the same as ability.bin. spot33's "entry 0 = end" u16 is the game's last index N−1 (an empty
pseudo-entry).

Cloud / #33 pieces:
| piece | +0x21 | entry shown |
|---|---|---|
| LAND_FINISH1 0x5c8 | 3 | 4 "Firaga" |
| **LAND_FINISH2 0x5c9 (Guard Break)** | **4** | **5 "Ragnarok"** |
| LAND_FINISH3 0x5ce (Spin Finish) | 5 | 6 "Explosion" |
| AIR_FINISH1 0x5ca | 6 | 7 "Aerial Finish" |
| AIR_FINISH2 0x5cb | −1 | none |
| AIR_FINISH3 0x5cf (Aerial Flurry) | 7 | 8 "Sonic Rave" |
| **HP_A_METEO1 0xb32 (Magnet Burst)** | **4** | **5 "Ragnarok"** |

plya +0x20 is a separate byte (0 for these). Reading +0x20 as u16 gave 0x300–0x700 in the old notes; that is +0x21 << 8.

**Adding entries works.**
- The table is decoded in place on an exact-size heap copy (FUN_0887ac24 → FUN_0887a6a0). Every index < N is valid.
- In test 124 the text chunk is 1612 B with **40 B of zero padding** at the end, and block 0 (English) is 276 B.
  - "Guard Break" into entry 5 + new entry 11 "Magnet Burst" = **+28 B → fits in place**.
  - Also renaming entry 6 → "Spin Finish" and entry 8 → "Aerial Flurry" = +36 B (fits).
- If it ever doesn't fit: grow the chunk with rebuild_arc + pkg_put (the heap copy is exact-size, so growing is fine).

**Fix (test 124 file offsets):**
1. `spot33_battlenames.py` NAMES: `5: 'Guard Break', 11: 'Magnet Burst'`. In main() add, before encoding:
   `while len(raws) <= lid: raws.append(encode(''))`.
2. plya HP_A_METEO1 0xb32 +0x21: `04` → `0a` (game index 10 = entry 11).
   - File +0x12ED09; ISO 0x6A085D09 in test 124.
   - Better: set it in spot33_combos.py where it already edits plya 0xb32 (+0x21 = 10).
3. Guard Break keeps +0x21 = 4 (entry 5 renamed). File +0x12E725 if you want it to point elsewhere.

## 9. "Stuck after the move": most likely Magnet Burst (block 68)
Facts:
- GMO motions are 30 fps and script frames are 60 fps. **A motion ends at script frame 2 × GMO end.**
  - FUN_0882ef10 sets runner+0x70 = FUN_0886b344(model, motion) = the GMO frame range.
  - FUN_08830444 sets "finished" (runner+0x58 | 1) when frame ≥ end **or** when one-shot op 0x02 has set
    runner+0x54 | 4.
- When the motion finishes, the one-shot list is only run up to the end frame (FUN_0882f17c(prev, end)).
  **One-shots placed after the motion end never fire.**
- Main op 0x0a (fighter+0x190 bit 2, FUN_0883752c) = "keep the attack going in the air". While it is set, the
  ground/fall code (FUN_0883b470, FUN_08a54e0c) does not switch to the fall motions 0x65/0x66.
- Main op 0x2d (+0x194 bit 8, FUN_08833898) = landing window. Touching ground inside it calls FUN_08833818
  (state landing).
- Main op 0x28 (+0x194 bit 4) = "free to act" (FUN_08b3a5bc returns 1, any action may cancel).
- One-shot op 0x02 = "end the motion now".

**Every one of Cloud's air moves ends the same way.**
- Rule: one-shot op 0x02 at or before the anim end, op 0x0a lasting until os02 + 2, op28 before that.
  Examples (anim end in script frames → os02 / op0a end):

  | block | anim end | os02 | op0a end |
  |---|---|---|---|
  | 48 | 88 | 80 | 82 |
  | 53 | 130 | 122 | 124 |
  | 62 | 124 | 124 | 126 |
  | 63 | 110 | 102 | 104 |
  | 66 | 230 | 222 | 224 |
  | 68 | 176 | 168 | 170 |

- Ground moves have no op0a / os02 and simply end at the anim end (Cross-slash 58: anim end 186, op28 162).

| #33 block | motion / GMO slot | anim end (script) | op28 | os02 | op0a | verdict |
|---|---|---|---|---|---|---|
| 65 Guard Break (ground) | 10095 _705A 0–41 | 82 | 81 | – | – | OK (ends at 82; one-shots after 82 never play) |
| **68 Magnet Burst (air)** | 10098 _707A 0–47 | **94** | 94 | **102** | **0–104** | **broken**: the end marker is never reached, while "stay airborne" (op0a) is still set when the motion runs out |
| 64 Finishing Leap (air chain end) | 10094 _704C 0–45 | **90** | 92 | **122** | **0–124** | same mismatch (copy of block 53, whose anim was 130). It may only get away with it when it ends on the ground; fix it too |

Magnet Burst is an air HP move (copy of Braver's plunge, Cloud anim 110 frames) on a 94-frame KH2 animation. So Sora
hangs in the last pose with op0a active and no os02 → "stuck".

The magi 0x529 and op2d are not the cause:
- the magi spawns at 44 (an extra Braver shockwave hit)
- op2d only matters if Sora touches ground during 28–42

**Byte fix, test 124 `obj/p_sev120.objx`** (block 68 at file +0x7310 / ISO 0x69F5E310; block 64 at +0x6198):
| what | file off | ISO (test 124) | old | new |
|---|---|---|---|---|
| b68 op0a `to` | 0x731A | 0x69F5E31A | `68 00` (104) | `58 00` (88) |
| b68 op28 `from` | 0x7488 | 0x69F5E488 | `5e 00` (94) | `4e 00` (78) |
| b68 os02 frame | 0x7500 | 0x69F5E500 | `66 00` (102) | `56 00` (86) |
| b68 drop Braver shockwave (os op4 magi id → −1, FUN_08828ae8 ignores −1) | 0x7510 | 0x69F5E510 | `29 05 00 00` | `ff ff ff ff` |
| b64 op0a `to` | 0x61A2 | 0x69F5D1A2 | `7c 00` (124) | `54 00` (84) |
| b64 op28 `from` | 0x6324 | 0x69F5D324 | `5c 00` (92) | `48 00` (72) |
| b64 os02 frame | 0x636C | 0x69F5D36C | `7a 00` (122) | `52 00` (82) |

The b68 values use Cloud's spacing: op28 = end−16, os02 = end−8, op0a end = end−6. Minimal alternative: os02 = 94,
op0a end = 96. In b64, op28 72 is after its last hit (66–72).

Alternative without touching blocks: make the animations as long as the copied blocks expect, so the templates fit
unchanged:
- `_707A=atk:788:35:mslot=_704B:end=55` (110 frames, like Braver's _704B)
- `_704C … :end=65` (130, like _630A)

**Rule for any copied/scaled block:** after the copy, the last os02 / op28 / op0a end must be ≤ 2 × (GMO end frame).
spot33_chain could check this automatically.

## 10. One-shot ("extra") records: format, and the SCALE / DROP code
Block = header 8 B, main events (12 + 4n each), one-shot list (8 + 4n each), end = block size. Header:
- byte +2 = main count
- byte +3 = **one-shot count**
- u16 +4 = **one-shot list offset** (= 8 + all main events)
- u16 +6 = block size

One-shot record:
```
+0 u16 frame   +2 u8 op   +3 u8 n   +4 u8 variant (0 any)   +5 u8 mode (0/4/5/6, as main events)   +6 u8 cond2 (0 any,
else value-1 must match)   +7 u8 cond3   +8 n × u32 params
```
- Fires once when prev < frame ≤ now (FUN_08829104 → FUN_0882cec0). Order does not matter.
- Never fires past the motion end (§9).

Ops: §6 table, plus:
| op | meaning |
|---|---|
| 0x02 | end motion |
| 0x1d | banner text |
| 0x29 / 0x2d / 0x33 | conditional magi |

spot33_chain.py COPY: add after the main-event loop (`new` = copied block):
```python
DROP_MAGI = {10098: {0x529}}                      # Magnet Burst: no Braver shockwave
e1, = struct.unpack_from('<H', new, 4)
recs = []
k = e1
for _ in range(new[3]):
    npar = new[k + 3]; rec = bytearray(new[k:k + 8 + 4 * npar]); k += len(rec)
    if rec[2] == 4 and struct.unpack_from('<I', rec, 8)[0] in DROP_MAGI.get(dst, ()):
        continue
    if dst in SCALE:
        struct.pack_into('<H', rec, 0, int(struct.unpack_from('<H', rec, 0)[0] * SCALE[dst]))
    recs.append(rec)
new = new[:e1] + b''.join(recs)
new[3] = len(recs)
struct.pack_into('<H', new, 6, len(new))
```
The existing code already shifts later block offsets by `len(new) - old`, so a smaller block is fine.

With SCALE 0.5, Guard Break's one-shots line up with its hits:
- voice/sound at 38/76/114 → 19/38/57
- shakes at 36/74/114 → 18/37/57
- camera op25 → 19/38/58
