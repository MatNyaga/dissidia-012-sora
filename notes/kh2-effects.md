# KH2 effects → Dissidia (start: Explosion) — 2026-10-14

Static research only (no PPSSPP, no builds, ISOs read-only). Disc data from `dumps/ULUS10566-test145-exp2.iso`
(#33 = Sora) and the clean ISO. Tools: `tools/scripts/kh2_pax_dump.py` (KH2 side), `tools/scripts/fep_dump.py`
(Dissidia side). Pictures: `dumps/renders/kh2fx/`.

## TL;DR
- KH2 Explosion = PAX elements **44–48** in `kh2_export/raw/kh2_sixth/original/obj/P_EX100.a.us` (BAR entry type 18
  "p_ex"). The motion 664 triggers `t1 [44..47]` at f0 and `t1 [48]` at f34 are PAX **element ids**. Element 48 is the
  burst (orbs + rings + streak trails + sparkle shower); 44–47 are the Keyblade charge glow and small glints.
- KH2 effect textures decode cleanly (8 PNGs). The orb texture is `dpd3_tex7` (soft white orb + swirl sphere,
  128×64 8-bit). The pink colour in the video comes from **vertex colour × layer colour**, not from the texture.
- Dissidia `.fep` = its own particle/mesh system: **TEX** (8-bit CLUT, PSP-swizzled, 128×64/128×128), **MDL** (small
  PSP GE meshes, each bound to one texture key), **ANM**, and 75 **leaf effects** (node trees: emitters/meshes with
  keyframed pos/rot/scale/RGBA). Effect ids in FEPA → leaf. Fully decodable container, node param blocks partly.
- **Correction:** one-shot `op 0x19 id 5` (the Explosion "Firaga stand-in" in tests 144/145) spawns FEPA id 5 =
  leaf **DOGE_UKEMI** (Cloud's air-recover whoosh, bound to `_170A`, scale 0.4), **not** Firaga. The magi row's
  "+0x04 fx" is a *bit number* into FEPA +0x3c, a different id space. Cloud's Firaga explosion (magi 0x124, fx 5) =
  FEPA **id 22 = FIGA_HIT_WALL**. Other Firaga ids: 21 FIGA_HIT, 23 FIGA_HIT_LAND, 73 FIGA_HIT_AIR, 20 FIGA_BALL.
- ❗ (later, same day) The per-leaf texture lists in §2 came from reading node +4 as an MDL index; +4 is the node
  life. Real resource refs = node components (see "Stage B/C progress"). Free leaves / TEX slots are listed there.
- Dissidia's **global** effect textures (system `resident.frr`, keys 0xF00000NN, shared by every fighter) already
  contain KH-like pieces: soft orbs + sparkle + bubble ring (G5), expanding ring frames (G12/0xc, unused by fighters),
  ring arc + starburst (G3), big soft orb (G15/0xf). A KH2-looking burst can be built mostly from those.

## 1. KH2 side

### Where it lives
| what | where |
|---|---|
| motion | `P_EX100.mset` entry 664 (A315). Frame triggers (60 Hz ticks): `[f0 t1 44] [f0 t1 45] [f0 t1 46] [f0 t1 47] [f34 t1 48]`, hit areas `t10 [911,19]` 32–57, `[912,19]` 57–64 |
| effects | `P_EX100.a.us` BAR → entry 0 type 18 **PAX** "p_ex" (0x7c570 B). 57 elements, DPX with 40 effects, 4 DPD |
| HD remaster | `kh2_export/raw/kh2_sixth/remastered/obj/P_EX100.a.us/-0..-7.dds` = same 128×64 textures (not upscaled) + `-8` face sheet. PNG copies in `dumps/renders/kh2fx/hd/` |
| sounds | element `se` = 999038 (44), 999042 (48) — KH2 se bank ids, not ported |

### Format (OpenKH `OpenKh.Kh2` Pax/Dpx/Dpd/DpdPData, decompiled with tools/dotnet-tools/ilspycmd)
- **PAX**: `"PAX_"`, nameOff, nElem, dpxOff; 80-B elements {u16 effectNo → DPX, u16 id (= trigger param), u8 group,
  u8 fadeFrames, s16 bone (0x4000|n = special: 0x4000 root/world, 0x4003 weapon), u64 category, u32 flags (Bind,
  BindOnlyStart, DestroyFadeout, DestroyWhenObjectLeaves, GetObjectFade …), f32 wait, s32 se, T/R/S (x,z,y order)}.
- **DPX** (ver 130): effect list {dpdOffset, pdataIndex, effectNo}; then the DPD list.
- **DPD** (ver 150): particle-data list, textures, shapes (sprite animations), models (OMD meshes), VSF.
  - particle data = 272-B header (bbox, offset, `abUse*` 128-bit sets of used textures/shapes/models/vsf) + a program
    file of **layers**. Each layer runs a list of **"ppp" programs** (KH2's particle bytecode, ~240 kinds):
    Point/Angle/Scale/Color, *Move/*Accele (keyframed per-frame velocity/acceleration), Matrix*, DrawShapeX (sprite),
    DrawMdl3/DrawMdlTs3 (mesh), RyjMegaBirth (mass particles), VertexApLc (spawn child layers at a model's
    vertices), EiDrawShipoly (ribbon trail), ParMatrix (follow parent). Time keys are ×4096 per frame.
    Colours are s16 RGBA, 0x4000 = 128 = 1.0 (PS2 convention).
  - texture = PS2 GS PSMT8 (256-colour CLUT, CSM1 swizzle) or PSMT4, linear pixels, alpha 0x80 = opaque.
  - shape = sprite animation: frames {wait, quads (screen rect + texel rect), RGBA per quad (128 = 1.0)}.

### What the Explosion effect is (video `…All Abilities…mp4` 12:20–12:23, sheet `dumps/renders/kh2fx/kh2_explosion_video_12fps.jpg`)
| elem | when | bone | effect → DPD 3 pdata | content |
|---|---|---|---|---|
| 44 | f0 | 0x4003 (weapon) | 31 → 11 | Keyblade charge: flash sprites (shapes 12/13/20), small mesh (model 17), sparkle birth (shape 13), white flash at the tip |
| 45 | f0 | 67, +18.75 | 32 → 12 | hand/blade flash sprites, scale 3, ~14 frames; sparkle birth |
| 46/47 | f0 | 170 / 78 | 33 → 13 | small glints (shape 8), 10 frames |
| **48** | **f34** | root (world, bind only at start), fade 8 | **34 → 14** | **the burst** (below) |

Element 48 layers (frames = 4096 units):
- L0 (start 6, 14 f): flat disc mesh on the ground (model 19, scale 0.25×0.03×0.25), purple RGBA (105,84,200).
- L1: invisible **spinning carrier** 1.3 m up (Point y −130 cm, KH2 −Y = up), scale 0.63, spin 3018/65536 turn per
  frame (≈16.6°/f) slowing by 84/f². Its model's vertices emit (VertexApLc) the child layers below → the orbs are
  placed on a rotating shape and fly out in a **spiral**.
- L3: orb mover (random angle, own spin, growing scale) → emits L4.
- L4 (20 f): **streak trail** = sprite shape 11 + EiDrawShipoly ribbon, whitish (141,134,125).
- L5 (17 f): **orb** sprite shape 9 on tex 7 (soft orb + swirl sphere), scale 0.108 → grows, alpha fades in/out.
  Sprite colours (219,172,101)/(113,154,196) × layer → the pink-magenta + white core seen in the video.
- L6 (17 f): big flare sprite shape 10 (scale up to 3.5). L7 (8 f): flash shape 12 (3.3×2.8).
- L8 (16 f): **ring** mesh (model 28) spinning about its axis (25064/65536 per frame), bluish (117,124,160).
- L2: sparkle shower (RyjMegaBirth, shape 13).
Video look: 5–6 pink/magenta orbs with white cores and transparent bubble rings spiral out from Sora at chest
height, light streaks curl around him, sparkles linger ~1 s.

Exports: `dumps/renders/kh2fx/dpd3_tex0..7_*.png` (Explosion uses **tex6** = lens streak line, **tex7** = orb +
swirl sphere), sheet `kh2_dpd3_textures_sheet.png`. Run
`python3 -I tools/scripts/kh2_pax_dump.py kh2_export/raw/kh2_sixth/original/obj/P_EX100.a.us --elem 44 45 46 48 --shapes`
for the full program listing.

## 2. Dissidia side (fighter `effe` chunk)
`effe` MPK members are taken by index: 0 `.fep`, 1 `.feb` (FEPA), 2 `.fxseb` (FXSE sounds). Loader FUN_088459e0 →
library FUN_088a54b0; FEP registration FUN_08943124 (checks magic/version 1/3 FUN_089434d8, id clash
FUN_0894349c, relocates offsets in place FUN_0894351c, registers TEX/MDL/ANM via FUN_08947004 / 0894728c /
08947444 / 089475fc into managers at store +0xa4/+0xa0/+0x9c/+0xa8).

### FEP layout (Sora's = Cloud's copy, 0xc4470 B, id 0x31280000)
| off | meaning |
|---|---|
| +0x00 | "FEP\xCD", u16 1, u16 3 |
| +0x08 | → {162, ptr} 8-B table (per-node counts? not needed) |
| +0x0c | runtime "relocated" flags (0 on disc) |
| +0x10 | id (top 14 bits, unique per loaded FEP) · +0x14 size · +0x18 u16 memory pool (3) |
| +0x1c | u16 nLeaf 75 (+0x1e copy) · +0x20 nTEX 21 · +0x22 nMDL 85 · +0x24 nANM 21 · +0x26 0 |
| +0x28 | → 75 ptrs: leaf index {u32 key = id \| res<<10, u16 tree index, u16 nVariant, ptr → variant bodies (0xa0 B: key, transform defaults)} |
| +0x2c | → 75 ptrs: node tree (52 B) {+4 duration (frames), +0x10 nNodes<<16 \| nRoots, +0x1c roots, +0x20 → node ptrs, …} |
| +0x30/34/38/3c | → TEX / MDL / ANM / (none) 20-B records {1.0f, key, 0, ptr data, handle} |
| +0x40 | → (unused here) · +0x44 → {75, ptr} names {key, len, "P0071_…_LEAF_0"} — **FEPA res indexes this** |
- Leaf lookup (FUN_08944694 → FUN_089444b0): FEPA res → names[res].key → leaf whose key bits 0x1fc00 match, variant
  = key & 0x1ff.
- **ANM** (21): sprite/flipbook animations over a texture sheet (UV frames); they reference TEX keys — most use
  **G5** (orb/sparkle sheet) or Gb (blue puffs); own 06/0f/13 are only reached through ANMs (0x81/0x83, 0x8a, 0x8f/0x90).
- **TEX**: "TEX\0", key, 1, 0, 4, 1, size, w, h, 0x30, pad | w×h 8-bit indices, PSP-swizzled (16 B × 8 rows) |
  16-B CLUT header (256) | 256 × RGBA8888. Same size class as KH2's (128×64 8-bit) → **a KH2 texture can replace an
  own TEX byte-for-byte** (re-swizzle, palette CSM1 → linear, alpha ×2).
- **MDL**: "MDL\0", 1, 8, key, …, **+0x1c texture key**, UV scale/offset floats, then PSP GE vertices (u8 uv,
  RGBA4444, s8 xyz × scale). Billboards, cards, rings, cylinders.
- **Node** (0x48 B): u16 ?, u16 **kind**, u16 **MDL index**, u16 node index, 20 B, 11 ptrs (p0 = keyframe-track list,
  p1 = param block, …). Kinds by param size: 0x8e (424 B, particle emitter: count/life/speed min-max pairs,
  spread, gravity …; defaults pos +0x40, rot +0x50 (deg), scale % +0x60, **RGBA +0x70, 128 = 1.0**), 0xe0 (348 B),
  0xc0/0xc7/0xa7 (236/208 B, mesh/billboard), 0x100/0x120 (380 B), 0x24 (spawner parent of a 0x100 child).
- Own textures (9): 98011c02 wisps, 03 cloud noise, 06 fire puffs (anim 4×4), 09 orange flames, 0e smoke band,
  0f blue magic puffs (anim), 12 lava rock, 13 gradient (only ANM 0x8f/0x90 use it), 14 clouds. Global textures
  used: G0–G9, Gb, Ge. PNGs: `dumps/renders/kh2fx/dissidia_fep/` (+ `sheet_global_and_sora.png`).

### FEPA (.feb) fields added
- +0x24 id (op 0x19, main op 0x66, FUN_088aa5b8 first match), +0x28 res (leaf), **+0x30 start offset** (copied as a
  float to the instance: start partway into the leaf), +0x38 magi kind mask, **+0x3c magi fx bit mask**
  (FUN_088aa9ec; magi row +0x04 = bit number), +0x44 trail variant mask, +0x18 scale.
- 9999 rows = *_LOCUS (sword trails), 8888 rows = SWORD_LIGHT / ULTIMA_AURA / FAST_GLOW / CHOU_V5_SWORD (blade glow).

### Can we add / change effects?
| change | size | difficulty | notes |
|---|---|---|---|
| op 0x19 id / frame in Sora's script | same | trivial | already done for id 5; switch to 22 (Firaga explosion) or another leaf |
| FEPA scale (+0x18), start offset (+0x30), node/attach | same | trivial | per FEPA row; rows can point at any leaf |
| new FEPA row (new id → existing leaf, other scale/offset) | +0x104 in .feb | easy | mpk.replace + rebuild_arc + pkg_put (objx grows) |
| node default RGBA / scale (424-B emitters) | same | easy, **unverified** | keyframe tracks may override; check in game |
| recolour an own TEX palette | same | easy | changes every leaf using that texture (FIGA_* share o2/oe/o12 → Sora's Fire HP move too) |
| replace own TEX pixels with KH2 orb | same | easy | 128×64 CLUT8 both sides; then point an MDL's +0x1c (or an ANM) at it; pick a texture only unused leaves reach |
| never touch Global textures (0xF00000NN) | — | — | shared by every fighter (system resident.frr) |
| new TEX / MDL / leaf inside the FEP | grows | medium–hard | relink 4 lists + names + keys (id \| idx<<10), node trees use absolute (pre-relocation) offsets → a FEP writer is needed; effect memory budget untested |
| copy a leaf from another fighter's FEP | grows | medium–hard | same writer + its MDL/TEX deps; ids rewritten to 0x3128… |

Other fighters' leaves that already look like magic orbs (scan of every FEP for G5/G3/Gf use): Emperor
(`P0022_FLARE_EISYO`, `FLARE_EXP`, `AIR_FLARE_EXP`, pkg 00410), Warrior of Light (`P_ONE100_MSWORD_*`,
`LIGHT_WAVE_HIT`, pkg 03314), Golbez (`GOL_CHOU_AURA_*`, pkg 08523), Terra (`GRAVIGA_APP`, pkg 10745), Tifa
(`EX_AURA_BODY_MAX`, pkg 00090), Zidane? (`SOLUTION_APP`, pkg 07264).

## 3. Plan (staged)
### Stage A — quick win (½ day + 1 Mat look)
1. Fix the stand-in: Explosion's one-shot `19 02 … 05 00 00 00` → **id 22** (FIGA_HIT_WALL = real Firaga
   explosion) in slot 10305 and 10308 (spot33_chain / AUTHOR spec). Same-size edit. Build a 4-variant test ISO
   (22, 21, 27 HAKOU_HIT = Blade Beam hit, 52 CHOU_LIGHT) or one ISO and Mat compares.
2. Bigger/longer: FEPA row 22 scale (+0x18) 1.0 → 1.6; if too long, +0x30 start offset.
3. Recolour test (size-neutral): set the 424-B emitter defaults RGBA of leaf 18's 0x8e nodes from (128,128,128,128)
   to pink-white e.g. (128,90,128,128) (`fep_dump.py … --leaf 18` prints the file offsets). If nothing changes in
   game, the colour comes from tracks → stage B decodes them.
Effort ~2–4 h of work. Result: a big magic burst on the plant; still Firaga-shaped, maybe tinted.

### Stage B — medium (2–4 sessions): KH2-looking burst inside the existing FEP, size-neutral
1. Write `fep_edit.py` (copy-on-write, dry-run like spot33_effects): set node RGBA/scale, MDL texture key, TEX
   pixels+palette from PNG/KH2 DPD.
2. Import KH2 `dpd3_tex7` (orb + swirl) and `tex6` (streak) into own TEX slots that only unused leaves reach (find
   with fep_dump: TEX → MDL/ANM → node → leaf → FEPA/script use) — converter: KH2 PSMT8 → swizzled CLUT8.
3. Sacrifice one leaf Sora doesn't use (candidates: KYOU_WORDS_1–4, CHOU_V5_* if the EX Burst no longer needs them —
   check every FEPA/op 0x19/magi reference first) and turn it into "EXPLOSION": point its node MDLs at
   orb/ring/streak MDLs (Global G5 orb + bubble ring, G3 ring arc, imported orb), colours from KH2 (orb ≈ (180,113,158)
   with white core, ring (117,124,160), streak (141,134,125)), lifetimes 14–20 frames, 5–6 emissions.
4. Decode the 424-B emitter block fields needed (count, life, speed, spread, spin) by A/B tests (one field per test
   ISO, Mat screenshot) — the min/max pairs are visible (45/45, 0.3/0.3, 5/5, 180, −0.4).
5. FEPA row for it (reuse the leaf's row or retarget id 22's res) + op 0x19 at the plant frame.
Risk: shared MDLs — editing an MDL changes every leaf using it; prefer MDLs referenced only by the sacrificed leaf.

### Stage C — full port (3–6 weeks): PAX → FEP converter
1. FEP **writer** (rebuild from parsed parts, relocatable offsets, keys id|idx<<10, names, counts) + round-trip test
   (parse Cloud's FEP → write → byte-identical).
2. Full node/track grammar (all node kinds, keyframe tracks, ANM) from the decompile (instantiation FUN_08945bec and
   the per-kind update/draw functions) + in-game A/B.
3. KH2 → FEP mapping for the ~25 ppp programs Explosion uses: Point/Angle/Scale/Color + Move/Accele → keyframe tracks;
   DrawShapeX → billboard MDL + sprite UV anim (ANM); DrawMdl3/Ts3 → MDL from OMD mesh; VertexApLc/RyjMegaBirth →
   emitter nodes; EiDrawShipoly → trail; units cm/−Y → Dissidia, 4096-unit keys → frames.
4. Then other KH2 moves (Ars Arcanum, Ragnarok, Strike Raid, magic) reuse it.
A one-off hand-authored Explosion leaf with the stage-C writer (no general converter) is ~1–2 weeks.

### Next exact steps
1. Stage A.1: edit the Explosion one-shot effect id 5 → 22 in the AUTHOR spec (slots 10305/10308), rebuild, Mat looks.
2. `python3 -I tools/scripts/fep_dump.py ISO --leaf 18` → patch the printed RGBA offsets on a copy (stage A.3).
3. Start `fep_edit.py` with TEX import (KH2 tex7 → a free own TEX) — fully understood, size-neutral.
4. List which leaves Sora still needs (op 0x19/0x66 ids in its scripts, magi fx bits, FEPA slot-bound rows, trails)
   to know which leaves/MDLs are free to sacrifice.

## Tools
- `tools/scripts/kh2_pax_dump.py FILE [--elem ID…] [--shapes] [--png OUTDIR]` — KH2 PAX/DPX/DPD: elements, effects,
  DPD contents, particle programs (ppp names, colours decoded), sprite shapes, texture PNGs.
- `tools/scripts/fep_dump.py ISO [obj/p_sev120.objx] | FILE.objx | FILE.fep [FILE.feb] [--leaf N…] [--png OUTDIR]`
  — FEP resources, every leaf with node kinds and textures, FEPA rows (id → leaf, magi fx bits, slot, frame, scale).
- `tools/scripts/fep.py FILE|ISO [--roundtrip [--grow OUT]] [--map]` — FEP parser/writer library (relocatable
  blobs, add_tex/add_resource, rekey, node_components/node_resources).
- `tools/scripts/fep_edit.py ISO [--usage] [--rekey] [--tex …] [--mdl-tex M=T] [--out NEW.objx]` — copy-on-write
  edits of #33's FEP + the "what does Sora still use" report.

## Stage B/C progress (2026-10-14, static only)
### FEP writer `tools/scripts/fep.py` ✅
- Offset grammar = the loader's relocation FUN_0894351c (decompiled; full list in the fep.py docstring). Besides the
  known lists: header +0x08 → {162, ptr → 162×8 B}; +0x40 → {u16 0, 0xcdcd, ptr}; tree +0x1c roots (+4 ptr), +0x24,
  +0x28 (12 × {.., +4 ptr}), +0x2c (n +0x18), +0x30 (n +0x1a); node (only if u8 +8 ≠ 0): +0x1c u8[+8] tracks
  {.., +8 ptr}, +0x20 {.., +8 ptr} if u8 +0x12, +0x24 u8[+0x13] × {.., +8 ptr}, +0x28..+0x44 8 plain ptrs.
  Sora/Cloud FEP: 18126 offset fields, 14445 targets.
- Model: every target starts a blob (runs to the next target, keeps its padding — originals use 0xCD fill);
  offsets stored symbolically; write() re-lays blobs (TEX/MDL/ANM data 16-aligned, rest 4) and rewrites +0x14 size.
- Tests (`fep.py FILE --roundtrip --grow [OUT]`): Sora (test149) and Cloud (clean) FEP → **byte-identical**;
  **shift test** (4 spare bytes after the header table → 14443/14445 blobs move) re-parses to the same semantic view
  (every field kind + target bytes) → no unknown offset fields; **grow test** (+1 TEX, copy of o02 as key
  0x98011c15) → 22 TEX, re-parses, decodes to the same PNG with fep_dump, nothing else differs.
- Resource records: {1.0f, key, **data size** (0 for global keys), ptr data, handle}. Global-key records point at
  the next own data blob (placeholder, ignored).
- Registration (FUN_08947004 & co → manager vtable +0x34 = FUN_089420f0 / 08942c94 / 08971d5c): **a key that is
  already registered is reused (refcount++), the new data is ignored** (FUN_08941d40 lookup by key). Global test =
  `(key >> 27 & 0xf) == 0xe`.
- Key scheme (checked on 7 FEPs incl. ids 0x1447/0x144a/0x284a): g = id >> 18, own key = 0x80000000 |
  (g & 0x3f00) << 17 | (g & 0xff) << 10 | type << 8 | index (TEX type 0, MDL type 1, ANM = TEX space with
  0x80 | index). Cloud g 0xc47 → 0x98011cNN / 0x98011dNN / 0x98011c8N; Sora g 0xc4a → 0x980128NN (unique; Aerith
  assist 0x144a → 0xa80128NN). Key references: TEX data +4; records +4; MDL data +8 (self) + texture table
  (count +0xc, offset +0x10, 0x18-B rows, key at +0 — FUN_08971554; all 85 have 1 row, at +0x1c); ANM data +4
  (self) + texture table (count +0x20, offset +0x30, 8-B rows — FUN_089428f8; all at +0x50). Nothing else (FEPA,
  other chunks, nodes) holds keys.
- ❗ **Sora's FEP still uses Cloud's resource keys** (spot33_effects only renamed the FEP id refs). In Cloud vs Sora
  the fighter loaded first supplies all 9 own TEX / 77 MDL / 15 ANM for both. Harmless while identical, but **any
  TEX/MDL/ANM edit in Sora's FEP needs a rekey first** (0x98011c→0x980128, 0x98011d→0x980129 for id 0x31280000),
  else Cloud vs Sora shows Cloud's textures on Sora (or Sora's KH2 orb on Cloud). fep_edit.py does this (`--rekey`).

### TEX import `tools/scripts/fep_edit.py` ✅ (static; not yet seen in game)
- `fep_edit.py ISO [--rekey] [--tex IDX|KEY (--kh2 [PAX:]D:T | --png FILE) [--premultiply]] [--mdl-tex M=T]
  [--out NEW.objx] [--png-dir DIR]` — reads obj/p_sev120.objx from the ISO, edits the FEP with fep.py, rebuilds MPK
  (mpk.replace) + objx (rebuild_arc) only if the size changed, writes a copy; never touches the ISO.
- TEX layout confirmed: +0x18 = clut offset (0x30 + w·h), record +8 = 0x30 + w·h + 0x410. Own textures are mostly
  **alpha 255 on black** (additive look); G5/o06/o14 carry real alpha. KH2's tex6/7 carry alpha → `--premultiply`
  if the target material turns out additive (check in game).
- KH2 conversion: kh2_pax_dump.texture() already maps pixels through the CSM1 swap (bits 3↔4), so its pixel values
  index the stored palette linearly → TEX palette = stored palette, alpha ×2 clamp. Cross-check: our tex7 decode vs
  the remaster's own DDS (hd3) mean abs diff 1.5/255 → palette order is right.
- Test 1: `--rekey --tex 0x13 --kh2 3:7` (orb + swirl into o13, 128×64 → same size) → decoded back = KH2 PNG
  **pixel-identical** (0 differing pixels). Test 2: `--tex 0x0f --png dpd3_tex6_128x64.png` (128×128 slot → 128×64,
  FEP shrinks 8 KB, MPK/objx rebuilt, other chunks/members byte-equal, re-parse + shift test OK) → pixel-identical.
  Pictures: `dumps/renders/kh2fx/import_test/compare.png` (+ decoded PNGs). (Test 2 is only a writer test: o0f is a
  4×4 flipbook sheet for ANMs, a size change would break their UV frames.)

### ❗ Node → resource references (correction; fep.py `node_resources`, fep_dump fixed)
- Node header: +0 u16 flags, +2 kind, **+4 u16 = life in frames (NOT an MDL index)**, +6 node index, +8 u8 track
  count, +0x12 u8 has-init-data, +0x13 u8 n24 count. Old fep_dump read +4 as MDL index, so **the per-leaf texture
  lists earlier in this note (§2 leaf table, "kind:texture") were wrong**; fep_dump now prints the real ones.
- Nodes are **component lists**: tracks = {u16 component id, u16 ?, u32 n, next ptr}; init data (node +0x20 →
  {0, n, ptr}) starts with n × {u16 track index, u16 offset, u32 0}, each component's parameters at that offset
  (e.g. comp 1 pos, 4 scale % (100), 7 RGB (128 = 1.0), 9 ...). Tree +0x24 = list of component ids used; header
  +0x08 = 162-entry component-version table checked at spawn (FUN_089453f4 vs DAT_089d9a98).
- Resource comps (index ranges vs list sizes over 7 fighters' FEPs; Emperor ANM 36 > TEX 25 decides ANM):
  **0x0b / 0x14 = u16 MDL index, 0x0a / 0x15 = u16 ANM index, 0x6a = u16 TEX index (blade-trail ribbon,
  unconfirmed)**. Every drawable node has exactly one; kinds 0x24/0x84/0x88/0xa4/0xa8 draw nothing (spawners).
  Check: METEO_BODY now draws o12 (lava rock), FIGA_* o9 flames + ANM 0x83 (o06 fire puffs), dodges G6 wisps.
- Draw code does not index the FEP lists at run time (only register/unregister touch +0x30..+0x38); the MDL/ANM →
  texture link is resolved by key at registration (FUN_08971554 / FUN_089428f8).

### What Sora's FEP still needs — `fep_edit.py ISO --usage` (test149, static)
Sources checked: every p_se type-8 block (one-shot 0x19/0x2f/0x30 ids, main 0x66 ids, main 0x2a trail ids,
one-shot op 4 + main op 0x43 p2 magi → children closure → magi row +4 fx bit and +0x20 FIGA_START id when
+0x1e = 6), FEPA slot binding (+0x88 model, +0xc8 slot, +0x7c & 0x80 = never auto), engine calls with constant ids.
- Script ids: **19, 22** (op 0x19 Explosion/spells); trails 8888/9999. Magi reachable: Cloud's Fire/Fira/Firaga,
  Blade Beam, Cross-slash marks 47c–47f, Limit 4ad, Braver 528/529/52a/52b, + the 15 HP-magic rows 7c1–7cf.
- **USED** leaves (41): 0–5 DOGE_*, 7/8 trails, 9 HTM_FINISH, 15–19 FIGA_*, 22/23 HAKOU_BODY/HIT, 26–29 METEO_*
  (Thundaga), 33–36 + 56/57/69 EX trails/auras, 37 CHOU_HIT, 38/39 HAKOU_*_HTM, 49–52 KYOU_WORDS_*, 61 ROT_HTM,
  62/63 BRAVER_FINISH_HIT*, 66–68 CHOU_V5_BOMB*, 70 FIGA_HIT_AIR.
- **Conditional** (25): only slot-bound rows (fire only if FUN_088aa844's model-name check — name at listener +4,
  8 chars when it starts with 'P' — matches Sora; still `p_sev100_1p` in Sora's FEPA, open) or ids found in
  character-specific EBOOT code (FUN_08a2d41c..08a4f454: 41,45–48,51,52,55,60,61,78; probably not Cloud):
  10 12 14 20 21 24 30 31 40–45 47 48 54 55 58–60 71–74.
- **FREE** (no reference found, 9): **6 HTM, 11 DIST, 13 SWORD_LOCUS_B, 25 GARYUU_HIT, 32 KYOU_HTM, 46 CHOU_FIRE,
  53 CHOU_HIT_LOSS, 64 CHOU_V5_HIT, 65 CHOU_V5_TOSSIN_HIT** (FEPA ids 6, 13/14, 17, 29, 36, 50, 57, 67, 68).
  Caveat: hit sparks come from a per-character table (FUN_0881591c → FUN_0881e67c(DAT_089d4910, fighter+0x568,
  hit id) → +4 = fighter-library FEPA id); its data was not found on disc. *_HTM (= hit mark) leaves 6 and 32 are the
  likely targets of that table → treat 6/32 as not free. Safest: 11, 13, 46, 53, 64, 65 (and 25).
- **MDL used only by free leaves**: 48 49 50 (leaf 32), 60 (46), 72 (global key), 73 (53; 320-B G5 billboard),
  81 (65; G3 ring arc), 82 (65; oe). No MDL/ANM is unused by everyone.
- **Own TEX**: every own texture is drawn by at least one used/conditional leaf. **o14 (clouds) is reached only by
  leaf 47 CHOU_SMOKE (conditional, EX-Burst slot _801B / id 51)** → best size-neutral slot for the KH2 orb. o13 (my
  import test slot) is NOT free: METEO_HIT_LAND (Thundaga) and HAKOU_HIGH_HTM draw it via ANM 0x8f/0x90. Own ANMs
  reached only by conditional leaves: 0x8d, 0x8e (24 GARYUU), 0x94 (59). Alternative with no sharing at all: **add**
  a TEX (fep.py add_tex, +9 KB) and point MDL 73 / 81 at it.
- Leaf 65 CHOU_V5_TOSSIN_HIT (FEPA id 68, 100 frames, 11 nodes) is already a magic burst: G5 orb emitters (ANM 5/6,
  kind 0x8e), two G3 ring arcs (MDL 81), oe swirl (MDL 82), flash (ANM 0 = G81), streak (MDL 79 G6). Best base
  for the Explosion leaf: `op 0x19 id 68` at the plant frame spawns it, no FEPA change.
- Import into the recommended slot: `fep_edit.py ISO --rekey --tex 0x14 --kh2 3:7 --out X.objx` → o14 decoded back
  = KH2 tex7 pixel-identical; picture `dumps/renders/kh2fx/import_test/compare.png` (row 2).

### Next exact steps — KH2-looking Explosion leaf (stage B, all size-neutral except optional add_tex)
1. Build step (another agent / build_sora.sh owner): after spot33_effects.py, run
   `fep_edit.py ISO --rekey --tex 0x14 --kh2 3:7 --out X.objx` + pkg_put. Check in game: Cloud vs Sora → Cloud's
   effects unchanged (rekey works), Sora's EX-Burst smoke (if it ever shows) now orb-textured.
2. Explosion script: one-shot `op 0x19 id 22` → **id 68** (leaf 65 CHOU_V5_TOSSIN_HIT, a G5-orb + G3-ring magic
   burst) — first look in game as-is (no FEP edit), compare with 22.
3. Make leaf 65 KH2-coloured: comp 7 init data = 4 B pad + RGB floats (128 = 1.0) — present on its orb emitters
   (nodes 2/4/9, kind 0x8e) → pink-white (180,113,158). The ring nodes 1/3 (kind 0xc0, MDL 81) have no comp 7
   (colour = MDL vertex colours / comp 9, to decode). Needs a small `fep_edit --rgb LEAF NODE R G B` op
   (fep.node_components gives the comp-7 offset); verify in game that tracks don't override it.
4. Swap textures: MDL 82 (oe swirl, only leaf 65) `--mdl-tex 82=0x14` → KH2 orb+swirl; optionally MDL 81 → KH2 ring
   (needs a ring texture: KH2 tex7 left half is the bubble sphere; G12/0xc ring frames exist as a global ANM).
5. Decode the 0x8e emitter component (comp 0x0f/0x15 params: count, life, speed, spread) by A/B tests → 5–6 orbs
   flying out in a spiral, life 17–20 frames like KH2 element 48.
6. Then stage C: copy leaf 65 as a NEW leaf (needs fep.py add_leaf: leaf index + variant + tree + nodes + name, keys
   id | res << 10, FEPA row) so Sora keeps CHOU_V5_TOSSIN_HIT's slot free for other KH2 effects.

## Stage B applied — test155 (2026-10-14 night, static checks only; NOT seen in game yet)
New build step `tools/scripts/spot33_fx.py ISO [--dry]` (run after spot33_effects.py; re-runnable: skips the FEP part
when MDL 82 already draws o14). On `dumps/ULUS10566-test155-fx.iso` (= test154 + this step):
- rekey 229 key fields → Sora's own base 0x980128NN (Cloud vs Sora no longer share own TEX/MDL/ANM).
- o14 (clouds; only the conditional EX-Burst smoke leaf 47) ← KH2 dpd3 **tex6** (light streak), premultiplied
  (the swirl material is additive: the old band o0e is alpha 255 on black).
- MDL 82 (swirl band, only leaf 65) → o14; vertex colours × KH2 streak (141,134,125). MDL 81 (G3 ring arc, only
  leaf 65) vertex colours × KH2 ring (117,124,160). MDL vertices: draw list u32 count +0x34, table +0x38 (0x18-B
  rows {prim, vtype 0x99 = u8 UV + RGBA4444 + s8 xyz, stride 8, ?, n, offset}); colours carry fades
  (0x0000/0x4444/0x8888/0xbbbb) → tint scales each channel, alpha kept.
- Leaf 65 orb emitters (nodes 2/4/9, kind 0x8e, comp 7 = 4 B pad + RGBA floats, no tracks) → (180,113,158,128).
- Leaf 65 node 8 drew MDL 83 (orange flame ring, o09; MDL shared with Firaga leaves) → comp 0x14 MDL index 83 → 82
  (second streak swirl, no fire).
- Explosion scripts: one-shot op 0x19 id 22 → **68** (FEPA row 68 → leaf 65) at 10305 f116/f146, 10308 f32/f62.
- Checks: FEP round trip byte-identical + shift test clean; objx same size; only `effe` (9573 B) and 4 script bytes
  differ from test154. Preview of the pieces: `dumps/renders/kh2fx/test155/explosion_fx_preview.png`; decoded
  textures `dumps/renders/kh2fx/test155/fep_980128NN.png`.
- Open: FEPA row 68 is "kind 1" (hit-type, like *_HTM) while the old stand-in 22 was kind 0 — if op 0x19 id 68 shows
  nothing or appears at the foe, retarget a kind-0 row instead. ⚠ Unrelated finding: FEPA rows bound to Cloud slots
  that Sora's moves now reuse (row 28 GARYUU → `_703A` f33 = Upper Slash's slot; rows 10-18 → `_700A`) would
  auto-spawn Cloud effects if FUN_088aa844's model-name check matches Sora (still `p_sev100_1p` in the FEPA → probably not).

### test157 → test158: "the sound is there but the effect is not" (Mat, test157)
- What differs between row 22 (Firaga blast, showed) and row 68 (leaf 65, showed nothing): +0x10 rotation y 180°,
  +0x38 kind 1 (hit-type), +0x48 0 (22: 2), +0x50 1 (22: 0), +0x3c magi bit 18, +0xf4 culling radius 3 (22: 4).
  FEPA row layout now: +0x00 pos xyz, +0x0c rot xyz (deg), +0x18 scale xyz, +0x24 id, +0x28 res, +0x30 start,
  +0x38 kind mask, +0x3c/+0x40 magi fx bits, +0x44 trail variant mask, +0x48 hit category, +0x50 hit-orientation
  mode, +0x70 attach type (4 = special), +0x74 frame, +0x7c flags (0x40/0x200 used in update), +0x80/+0x84,
  +0x88 model name, +0xa8 node, +0xc8 slot, +0xf4 culling radius, +0xf8 culling mode.
- Decompile: op 0x19 (script one-shot) = FUN_088a9de8(fighter lib, id, fighter+0x4c8) → FUN_088aa5b8 (first row
  with +0x24 == id) → FUN_088aa4e0 → FUN_088a68fc (reads +0x28 res, +0x30, +0x70, +0x74, +0x88/+0xa8/+0xc8 only) →
  FUN_088a4d7c → FUN_08941914 → leaf lookup FUN_089444b0 (key bits 0x1fc00 = res, variant 0x1ff). Kind/+0x48/+0x50/
  bits are only read by the magi/hit spawners (FUN_088aa9ec filter, FUN_0880966c hit marks: +0x50 orients by the
  hit direction, +0x38 & 0x40). lib+0x28/+0x2c (magic 0x20070422, 0x140 B per res) = FXSE sound table, not drawing.
  Leaf 65's header/variant/tree match leaf 18's layout; node scales are the same order as FIGA_HIT_WALL's.
  → **No static reason found** why 68 is invisible; the row fields that differ are not read on this path.
- test158 (`spot33_fx.py` updated, re-runnable): row 68 := row 22's fields (kind 0, +0x48 2, +0x50 0, no rotation,
  radius 4) keeping id 68 / res 65, magi bits 0; orb RGBA capped at 128 (128,80,112 — 180 > 1.0 might wrap);
  Explosion scripts: FIRST op 0x19 (orb start: 10305 f116, 10308 f32) → 68, the strike (f146 / f62) → **22 again**
  = in-game control. Mat's look decides: blast yes + burst no → leaf 65 itself (or its FEP edits) is the problem →
  next test = leaf 65 without any FEP edit (only the FEPA row), then add edits one by one; neither → Sora's FEP edits
  (rekey) broke drawing → check Firaga/trails too.

## EX Burst background (2026-10-14 night, test162; static only, NOT seen in game yet)
Mat: "the limit background … right now it's very FF7 pink etc, we need to make it KH2 themed".
**What draws it** (Sora runs Cloud's Omnislash code; all pieces are leaves in Sora's own FEP, copied from Cloud):
- Burst scripts (motions 8000-8600, blocks 69-81) spawn no effects by id: only sword trails (main op 0x2a ids
  9999/8888) and screen flashes (one-shot op 0x1b [frames, 0, len, colour 0 white / 1 black / 2 red]: 8102 f0,
  8500 f124).
- FEPA rows bound to burst slots (fire when the slot plays): 47/48 GAMEN_HIT(2) `_801A` f12/f54, 50 CHOU_FIRE /
  51 CHOU_SMOKE / 52 CHOU_LIGHT `_801B` f0 (flags 0x83), 62 CHOU_KOUKA_PERFECT `_802A` f14, 58 CHOU_FINISH_APPEAR /
  59 CHOU_HIT_FINISH `_812C`, 49 CHOU_HIT_LOSS_FINISH / 64 CHOU_LOSS_YOIN `_812A`, 63 CHOU_PERFECT_YOIN `_812C` f200
  (node camera2_include = screen-attached).
- Cloud's burst code FUN_08a3a638 (the "Rapidly tap ◯" phase) spawns **id 51 CHOU_SMOKE on every tap** and **id 52
  CHOU_LIGHT** when the tap target is reached (FUN_088a9de8 on the fighter library, at fighter+0x4c8).
  **Correction (2026-10-16, notes/ex-burst-controller.md §9):** FUN_08a3a638 is controller-0 VARIANT 1, which no chrp
  row selects. Cloud's/Sora's burst is variant 0 (FUN_08a3a0b8): ids 50/51/52 spawn ONCE each at 5/10/15 taps, nothing per tap.
- The look: CHOU_FIRE = MDL 60 with o09 orange flame texture + peach emitter colour (200,128,112); CHOU_SMOKE = the
  swirling cloud dome behind the fight (MDL 61 o14 clouds + MDL 62 G6 wisps, colour (96,112,128)); CHOU_LIGHT violet
  (72,48,128) / lavender (98,98,128); finish leaves orange-red (200,64,12) and peach/pink/orange (KOUKA_PERFECT).
  Own textures are grey (except o09 flames), so the "pink" is these colour values + the flame texture.
- Colour values = RGBA floats (128 = 1.0) inside the leaves' node data, either init data {0xcdcdcdcd pad, R, G, B, A}
  or keyframes {3 equal floats (scale), pad, R, G, B, A, …}; found by scanning aligned float quads.
- Not Sora's FEP (not changed): the pink "LIMIT BREAK" / "Omnislash" banner boxes (battle HUD, shared by everyone);
  the green blobs in old burst shots (test60) — no green value in these leaves; probably the opponent's hit effects
  or Gb/G0 emitters with keyframed colour (to check in game).
**Change** — new build step `tools/scripts/spot33_burstfx.py ISO [--dry]` (re-runnable; run after spot33_effects.py):
- MDL 60 (only CHOU_FIRE): texture o09 → global G6 soft wisps, grey vertices × white-gold (224,200,136) = light aura.
- MDL 61 (only CHOU_SMOKE): texture → G6, grey vertices × deep navy (40,60,132) = dark-blue swirling sky. MDL 62 ×
  KH blue (80,112,184). (Exclusivity asserted at run time; globals only referenced by key.)
- 44 colour values in leaves 46/47/48/54/55/58: COLOURS table in the script (FF7 warm/pink/violet → KH2 night blues,
  moonlight white, white-gold). Exact old values only → re-runs change nothing (checked: "nothing to do").
- test162 = test160 + this step: only `effe` differs (518 B), FEP round trip byte-identical + shift test clean.
  Preview: `dumps/renders/kh2fx/test162/burst_kh2_preview.png`.
- Next (bigger, not size-neutral): a real KH2 backdrop texture (Kingdom Hearts heart moon / Dive-to-the-Heart
  stained glass from the remastered menu images) as a NEW TEX (fep.py add_tex, +9 KB) on MDL 61; decode keyframe
  tracks to retime/re-shape; ports of KH2 Limit Form effects (P_EX100_KH1F.a.us).

### test164 — white strike flash + bigger KH2 orbs (2026-10-15)
In game (test160, coordinator clip dumps/screens/explosion_test160.mp4): effect 68 DOES show — blue-white bursts and a
cloud of **tiny blue dots** (the orbs), then the orange Firaga control blast. Mat: strike "shouldn't be an orange
Firaga blast but a bright white light"; orbs "Yes, that's what I want KH2 style bigger".
- Strike: unused leaf **53 CHOU_HIT_LOSS** (FEPA 57: flash ANM G83, light lines G8, glows G5/G86, colour-only meshes
  36/71/72; magi fx bit 14 = unreachable) → all its colours white: (128,128,128) → (255,255,255) ×14 and
  (128,160,240) → (235,245,255) ×3. Row 57 := row 22's fields (like 68), scale 2.2. Scripts: strike one-shot op 0x19
  (10305 f146, 10308 f62) → **57**. Effect 22 itself untouched (Sora's Firaga hit uses it; row 22 still fx 5, 1.0).
- Orbs: leaf 65 orb emitters (nodes 2/4/9) comp 7 RGBA → (255,150,220,176) (values > 128 are valid: Cloud's own
  leaves use 200-255; R must exceed 1.0 because the G5 orb sprites lean blue) and **comp 4 = sprite scale %**
  100 → 280; FEPA row 68 scale 1.0 → 1.4. Leaf 65's remaining warm orange colours (missed before: (200,130,72) ×3,
  (200,140,98) ×4, (200,128,64) ×2, (240,160,98) ×2) → white-pink.
- Colour rule (leaf data): RGBA floats directly after a 0xcdcdcdcd pad, plus the 2nd quad of a start/end pair right
  after it (+16). spot33_fx.py LEAF_COLOURS / ROW_SCALE / ORB_RGBA / ORB_SCALE; re-runnable ("nothing to do").
- test164 = test160 + this: `effe` 157 B + 2 script bytes; FEP round trip byte-identical. Preview (approximation):
  `dumps/renders/kh2fx/test164_explosion_preview.png`. Clean-build dry run (test154) applies every step.
- Orb COUNT (5-6 like KH2): the emitter comps 0x0e/0x15 hold small ints 5/6 (likely counts) — undecoded, unchanged.

## Firaga (2026-10-15, test167; static only, NOT seen in game yet)
Mat: "start on the KH2 fire for Firaga".
**KH2 side** — `kh2_export/raw/kh2_fifth/original/magic/FIRE_3.mag` (Firaga; FIRE_1/2 = Fire/Fira, *lk = variants) =
BAR {PAX "fire3" 73920 B, 2 small type-3 entries}. PAX: 13 elements, 8 effects, 1 DPD with **ONE 128×64 PSMT8
greyscale texture** (left half soft fire blob, right half cellular fire shell; remaster `remastered/magic/FIRE_3.mag/-0.dds`
= same at 256×128), 10 sprite shapes, 6 models. Colour comes from layer/shape colours: shell red-orange (183,35,19),
highlights (196,151,89) / (231,184,101) / (225,184,107), dark red (65,20,18), smoke (58,35,21). Elements: 0 = ball
(bone sp3, loops, se 116), 1 = ball body layers (shapes 0-2, models 0-2, DrawMdlTs3 shell), 2/5/10 = hand flare
(sp0, se 156), 3/4 = explosion (se 118/119, scale 1.16/0.88), 6/7 = cast flash (se 999016), 8/9 + 11/12 = trails
(sp3/sp4, se 146). PNGs: `dumps/renders/kh2fx/firaga/kh2/` (dpd0_tex0, hd_tex0).
**KH2 Firaga sounds** (tools/scripts/kh2_se.py; WAVs in dumps/renders/kh2sounds/; not wired yet):
| se id | file | len | what (element) |
|---|---|---|---|
| 156 | se000_059.wav | 2.23 s | cast at the hand (2/5) |
| 999016 | se999_016.wav | 1.41 s | cast flash (6/7) |
| 116 | se000_055.wav | 1.64 s | fireball flying (0, loops while it flies) |
| 146 | se000_054.wav | 2.26 s | trail (11) |
| 118 / 119 | se000_056.wav (same audio) | 1.97 s | explosion (3 / 4) |
**Sora side** — leaves 15 FIGA_START (id 19), 16 FIGA_BALL (20, magi fx 1), 17 FIGA_HIT (21), 18 FIGA_HIT_WALL (22),
19 FIGA_HIT_LAND (23), 70 FIGA_HIT_AIR (73). Own textures: o09 flames (also KYOU_WORDS 49-52 = Cross-slash marks,
KYOU_HTM, CHOU_V5_*: NOT free), ANM 3 = o06 fire-puff flipbook (also Thundaga's METEO_HIT 28/29). Fire-only meshes:
MDL 15 (flame mesh in all six), 21 (ball flames), 20 (ball shell, G0), 19 (Ge), 14/17 (START). MDL 18 (KOUKA), 22
(HAKOU_HIGH_HTM), 16 (CHOU_HIT_LOSS = Explosion strike flash) are shared → untouched.
**Change** — new build step `tools/scripts/spot33_firefx.py ISO [--dry] [--png OUT]` (re-runnable):
- NEW own TEX index 0x15 (key 0x98012815, +9312 B FEP / objx) = KH2 FIRE_3 tex 0, palette greys gradient-mapped
  (black → (90,12,6) → (190,45,16) → (235,110,35) → (245,180,90) → (255,240,200), ×1.3) and premultiplied.
- MDL 15, 21, 20 → that texture (exclusivity asserted). o09 / o06 unchanged.
- 73 colour values in the six FIGA leaves (old → new): (200,112,48)→(220,80,30), (240,98,64)→(240,70,30),
  (200,64,12)→(190,40,16), (128,64,24)→(120,32,16), (200,130,72)→(230,150,80), (240,128,64)→(240,110,40),
  (240,160,128)→(255,200,120), (220,160,48)→(240,190,90), (48,64,128)→(60,36,22).
- test167 = test163 + this: only `effe` member p_sev100.fep differs (803952 → 813264 B), FEP round trip
  byte-identical + shift test clean, new TEX decodes back (`firaga/test167/fep_98012815.png`), re-run "nothing to
  do". objx moved to the ISO end by pkg_put (ISO +1.4 MB).
- Preview (mock-ups from real textures/colours, not a capture): `dumps/renders/kh2fx/firaga/firaga_preview.png`.
- ⚠ First FEP growth in game: effect memory budget untested (Cloud vs Sora loads both FEPs). If Sora's effects
  vanish / the game hangs in test167 → this is the suspect.
- Next: KH2 Firaga sounds (table above, via spot33_sfx-style slots + op 0x03 in 10310/10313 and the magi hit);
  ball size/shape (magi row scale, FEPA 20 scale); KH2 trail (EiDrawShipoly) look.

## Thundaga (2026-10-15, test169; static only, NOT seen in game yet)
Mat: "add thunder blizzard as well, right now thunder is meteor rain".
**KH2** `magic/THUNDER_3.mag`: PAX "thunder3", 6 elements, 1 DPD with 7 textures — tex2 256×128 = two lightning
bolts (left white-gold, right blue), tex1/6 arcs, tex0/3/4/5 flashes; 27 models. Elements: 0 Keyblade charge (sp3,
se 126), 1 (sp3), 2/3 strikes (world, se 164), 4/5 big impact (se 128, scale 1.41/1.45).
Sounds (kh2_se.py): 126 → se000_127.wav 1.98 s (charge/cast) · 164 → se000_131.wav 2.29 s (bolt strike) ·
128 → se000_128.wav 1.79 s (big impact).
**Sora** — Thundaga magi 0x7C4/0x7C5/0x7C9/0x7CA carry fx bit 4 → FEPA 30-33 → leaves 26 METEO_APPEAR, 27
METEO_BODY (the falling rock), 28 METEO_HIT, 29 METEO_HIT_LAND. Exclusive meshes: MDL 40/41/42 (27), 44 (29).
**Change** (`tools/scripts/spot33_magicfx.py`): NEW own TEX 0x16 (+9.3 KB) = KH2 bolt (tex2 left half 128×128 →
128×64, premultiplied; bolt runs along v); MDL 40/41/42/44 → it; leaf 27 rock nodes 0/1 (rot −90° X, long axis =
flight) comp 4 (12,15,12) → (4,70,4), shell node 2 (15,5,15) → (6,40,6) = thin glowing rod along the flight path;
colours of 26-29 → electric yellow-white/blue (THUNDER_COLOURS, 33 values); o06 fire-puff emitters in 28/29
(ANM 3, shared texture) → RGBA 0 (hidden).
- Still Meteorain's MOTION: the bolts fly in on Cloud's meteor paths (slanted from the sky). For real KH2 strikes
  (straight down onto/around the foe) the magi must change (spot33_magic, coordinator): falling-strike rows
  0x7C5/0x7C9 → spawn directly above the target, straight down, much faster, short life; fewer per cast.
- Preview: `dumps/renders/kh2fx/magic169/thundaga_blizzaga_preview.png`; bolt `magic169/kh2_bolt_128x64.png`.

## Blizzaga (2026-10-15, test169: data ready, INACTIVE until the magi change below)
**KH2** `magic/BLIZZARD_3.mag`: PAX "blizzard3", 8 elements, 1 DPD, tex0 128×64 ice surface, tex1 128×64 ice
crystals (2 big crystals, shards, sparkle, glow); 13 shapes, 8 models. Elements: 0 Keyblade charge (sp3, se 120),
1/7 cast (sp3/sp4, se 159), 3/4 shards (world, se 160/161), 5/6 impacts (se 124/125).
Sounds: 120 → se000_005.wav 1.97 s (charge) · 159 → se000_016.wav 1.89 s (cast) · 160 → se000_015.wav 1.90 s ·
161 → se000_014.wav 1.77 s (shards flying) · 124 → se000_004.wav 1.42 s · 125 → se000_008.wav 1.62 s (impact/shatter).
**Sora today**: Blizzaga magi 0x7CB-0x7CD = copies of Fire's 3-way balls, fx bit 1 → FIGA rows 20/21/23 → it LOOKS
LIKE FIRE (now KH2 fire). Bursts 0x7CE (fx 20 → FIGA_HIT_AIR) / 0x7CF (fx 5 → FIGA_HIT_WALL + HTM_FINISH).
**Change** (spot33_magicfx.py): magi bit 3 is used by no magi (also 6, 8, 14, 17, 18, 21+) → FEPA rows 67 (leaf 64
CHOU_V5_HIT), 29 (leaf 25 GARYUU_HIT), 78 (leaf 74 GARYUU_FIN_HIT) := Fire rows 20 / 21 / 23 (ball / hit /
ground hit: kind 0 / 1 / 12 + their other fields), magi bits = 1 << 3, own res kept. NEW own TEX 0x17 (+9.3 KB) =
KH2 tex1 ice crystals (premultiplied) on MDL 37 / 38 (only leaves 25 / 74). Colours of 64 / 25 / 74 → ice blue /
white (ICE_COLOURS). (Leaf 74's row 78 = id 78 appears in other fighters' EBOOT code only; row 74 CHOU_V5_LOCUS
slot-bound `_706A` never fired for Sora → treated as dead.)
**Needed in spot33_magic (coordinator)**: magi 0x7CB / 0x7CC / 0x7CD +0x04 fx bit 1 → **3**; bursts 0x7CE / 0x7CF
+0x04 → **0xFFFF** (no effect, like 0x2C7). Then the shards draw leaf 64 (icy glow), hits leaf 25, ground hits leaf 74.
**FXSE sounds** (spot33_magicfx.py, run after spot33_sfx): Fire hits (leaves 17/18/19/70, one-shot records) → slot 76
(done in test169: 24/25/25/67 → 76); Thundaga hits 28/29 → slot 77; Blizzaga hits 25/74 → slot 78 — written only once
those slots exist in #33's snd_ bank (test169 has 77 slots → 77/78 skipped). Records: per leaf 16 × 20 B {base,
slot, frame, ?, flags}; flags 0 once at frame, 4 loop while alive (FIGA_BALL slot 25 = Cloud's flying loop, kept),
2 = other bank (100000). Base 2200000 / 21900000 both handled.
- FEP growth so far: +27.9 KB (fire 0x15, bolt 0x16, ice 0x17) — effect memory budget still untested in game.

## ❗ Effects memory: the effe chunk must NOT grow (2026-10-15, test182)
Coordinator's bisect (Mat in game): test171 froze PPSSPP even on a plain Bravery attack; test179 = test171 with
test166's effe (848640 B = Cloud's size) works, Explosion orbs/flash included. Cause = effe +27,920 B (new TEX from
spot33_firefx +9.3 KB, spot33_magicfx +18.6 KB) → effect memory budget exceeded. **Rule: never append TEX/MDL/leaf;
overwrite slots Sora never draws, same size. Scripts assert the FEP size.**
**Which own textures are free** — reachability by MOTION (not every p_se block): the blocks of Cloud attack motions
no #33 piece uses (10003-05, 10012, 10030, 10032, 10040 Blade Beam, 10041-43 Fire, 10051, 10090 Cross-slash,
10092, 10096, 10097, 10299) never run → their magi (0xCD Blade Beam, 0x47C-0x47F Cross-slash marks) are dead.
Reachable magi: 4AD, 528/529, 7C1-7CF (fx bits 1, 3, 4, 5, 9, 15, 16, 20).
| slot | Cloud's use | drawn by (after the steps) | now |
|---|---|---|---|
| o0f 128×128 | Blade Beam flipbook (ANM 10) | dead leaves 22 HAKOU_BODY, 39 HAKOU_BG_HTM + MDL 15/20/21 | **KH2 fire** (128×64, rows doubled) — spot33_firefx |
| o12 128×64 | lava rock | MDL 40/41/42/44 (Thundaga's own meshes only) | **KH2 bolt** — spot33_magicfx |
| o09 128×64 | flames | MDL 80 (leaf 64 = Blizzaga ball) + dead KYOU_WORDS 49-52, KYOU_HTM 32 (MDL 49/50/64/66/68/70), CHOU_V5_BOMB 67 (MDL 83) + MDL 37/38 | **KH2 ice crystals** — spot33_magicfx |
o14 stays the Explosion swirl (KH2 streak, spot33_fx). Risk noted: KYOU_HTM (hit mark) could still come from the
per-character hit-spark table if a Cross-slash hit id (0x365-0x367) lands — it would then show ice instead of flames.
- Blizzaga magi 0x7CB-0x7CD already have fx bit 3 (coordinator) → rows 67/29/78 (ice) are live.
- FXSE (spot33_magicfx): FIGA_BALL's looping flying record (slot 25, flags 4) muted (= 20 zero bytes, like the 1132
  unused records); Blizzaga hit leaves 25/74 had two one-shot records each → first → slot 78, second emptied.
- test182 = test171 with test166's effe + spot33_fx / burstfx / firefx / magicfx (all "nothing to do" on re-run):
  effe 848640 B ✓, FEP 803952 B, round trip byte-identical, TEX count 21 (no additions). Slots old/new:
  `dumps/renders/kh2fx/test182/slots_old_new.png`.

### test182 in game (Mat): no freeze ✅, but Explosion shows NO effects, Thundaga still looks like Meteorain
- Explosion wiring in 182 == 179 (op 0x19 68 at the orbs, 57 at the strike; rows 68 → leaf 65 ×1.4, 57 → leaf 53
  ×2.2). vs test160 (faint orbs + Firaga blast seen): only the test164 look changed. **comp 4 on the 0x8e emitters is
  the emitter TRANSFORM scale** (param block: rot +0x50, scale % +0x60, RGBA +0x70), not the sprite size → 280 % ×
  row 1.4 ≈ 3.9× spread: the orbs spawn/fly ~4× further out (likely off camera). Leaf 53 (CHOU_HIT_LOSS) at the
  strike was never seen working (unique node kinds 0xCE/0xDE). "test179 works" meant no freeze only.
- Thundaga: leaf 27 changes ARE in 182 (MDL 40/41/42/44 → o12 = bolt, rods 4×70×4, electric colours). The magi's
  +0x02 = 1 is not a separate rock model (the objx d_se GMO = camera/skeleton dummy, `wind` GIM = 32×64 UI boxes).
  So: either the bolt reads badly on the rock mesh (its UVs may sample a dark part), or "Meteorain" = the MOTION
  (slanted falls from the sky) → needs the magi change (straight down above the target).
- Bisect discs (from 182, effe 848640 B each):
  | disc | Explosion orbs | leaf-65 colours | strike | Thundaga |
  |---|---|---|---|---|
  | test185-fxfix | white-pink (255,150,220,128), transform 100 %, row 1.0 | white-pink | **57 → leaf 55** (EX-Burst finish flash, ×1.3) | as 182 |
  | test186-exp160 | test160 exact (128,80,112,128), 100 %, 1.0 | original warm | **22** (Firaga blast) | as 182 |
  | test187-diag | as 185 | white-pink | **22** | METEO_BODY nodes **bright cyan** (diagnostic) |
  Leaf 53 colours reverted (unused). spot33_fx.py constants still = test171 values → set after the result.

### test188 — anchoring (Mat, test185: white flash shows but "away from the camera, a little behind")
- FUN_088a68fc attaches an effect when strlen(row +0x88 model name) > 0 (FUN_089359e8 = strlen): +0xa8 node name =
  bone of the spawner (fighter+0x4c8), +0xc8 slot, +0x00 offset in bone space (r_wep x = along the blade, root
  y < 0 = up). Rows copied from 22 had empty names → world placement off Sora's body.
- spot33_fx.py ANCHOR: row 68 (orbs) → `p_sev100_1p` / `hip` / (0,0,0); row 57 (flash, leaf 55) → `r_wep` /
  (1.0,0,0) = Keyblade tip; both flags 0x80 + slot `_000A` like row 8 SWORD_LIGHT (works at Sora). Constants now =
  test185 look (orbs 255/150/220/128, emitter 100 %, row 1.0; flash leaf 55 ×1.3).
- spot33_magicfx.py: Thundaga falling body row 31 → leaf 48 CHOU_LIGHT (KH-blue light column) instead of the rock.
- test188 = test185 + these; effe 848640 B; all four steps "nothing to do" on re-run.

### test195 (2026-10-15)
- Blizzaga "shoots out nothing, a blow-up on the ground" (Mat, test191r): row 67 (ball, bit 3, kind 0) drew leaf 64
  CHOU_V5_HIT = a one-shot hit flash, not a projectile body → the ball flew invisible, only the hits showed. Now row
  67 → **leaf 27 METEO_BODY** (the meteor's own flying body, free since Thundaga's row 31 draws CHOU_LIGHT) with
  MDL 40/41/42 → o09 = KH2 ice crystals, nodes (10,12,10)/(15,5,15), colours ice (spot33_magicfx ICE_BODY_*,
  ICE_ROW_RES). Bolt texture (o12) now only on the thunder impact debris MDL 44.
- Blizzaga magi still use +0x1e = 6 (spawn at the caster's live effect +0x20 = 19 FIGA_START = the FIRE charge) →
  its cast shows a fire flare. Suggestion for spot33_magic: Blizzaga magi +0x1e → 0 (fighter position, like
  Thundaga) and drop op 0x19 19 from the Blizzaga blocks.
- Explosion flash row 57 (leaf 55, r_wep) ×1.3 → ×0.8 (Mat: too bright; leaf 55 is shared with the burst → no recolour).
- KH2 Fire (no projectile, flames around Sora; coordinator's scripts): spot33_firefx SPELL_ROWS — **id 53** = leaf 15
  FIGA_START ×2.2 at the hip (74 frames ≈ 1.2 s, one-shot), **id 54** = leaf 18 FIGA_HIT_WALL ×1.5 at the hip (end
  burst). Rows 53/54 were KYOU_WORDS_1/2 (Cross-slash marks, dead for Sora). Anchor = model `p_sev100_1p` + bone +
  flags 0x80 + slot `_000A`.
- test195 = test188 + all of the above; effe 848640 B; all steps "nothing to do" on re-run.

## Lightning's thunder in Sora + KH2 ice + Fire anchors (2026-10-15, test199)
**Thundaga = Lightning's own Thunder** (Mat: CHOU_LIGHT columns = "a bunch of cones"; "Lightning has thunder").
Lightning = owner 31, `obj/p_gst130.objx` (clean ISO), FEP id 0x32080000: THUNDER_APPER (46, 0 nodes), THUNDER_BODY
(47, 12 nodes: o06 bolt on MDL 57, global arc meshes 10/12/58/59, G82/G8a flashes, G5 sparks via her ANM 4),
THUNDER_HIT (48). Also RAIKOU_* (66/67/55) = her other lightning move (not used).
New: `tools/scripts/fep_transplant.py` (copy a leaf's tree subgraph between FEPs, remap MDL/ANM/TEX indexes in the
copied nodes, gut dead trees, pad to size) + `tools/scripts/spot33_lightningfx.py ISO CLEAN_ISO` (re-runnable):
her 47 → Sora leaf 22, 48 → 23 (Blade Beam, dead); her own MDL 2/13/57/60 → Sora 63-66 (Cross-slash marks, dead);
her global MDLs 10/12/59 = Sora 71/13/72, 58 (f000010b) → Sora slot 67 turned global-key record; her ANM 4 → Sora
ANM 10; her o06 → Sora o12. FEPA 31 (falling strike) → 22 ×0.8, 32/33 (hits) → 23 ×0.5, 30 (meteor portal) → 49
(gutted = nothing). FXSE leaf 22 emptied, 23 → slot 77. Size: her trees +3.3 KB → leaves 49/50 gutted, pad → FEP
803952 B, effe 848640 B (asserted). Component-version tables (header +0x08) of both FEPs are identical.
**Leaf ranges fixed** (spot33_burstfx.leaf_ranges/scan, used by fx/burstfx/firefx/magicfx): each leaf = the exact blobs
of its tree subgraph (was "first node .. next leaf's first node", wrong after a transplant; a min..max span is wrong
too). Same colour spots as before on a normal layout (44 / 70 / 11 checked on test154).
**Blizzaga** ("all black, and kind of white", test196): o09 held KH2 tex1 = a crystal SPRITE SHEET; the meteor mesh
maps the whole sheet → mostly empty/grey masks. Now o09 = KH2 tex0 = the ice SURFACE, gradient-mapped to ice blues
→ white, alpha 255; MDL 41 vertices white, 42 doubled; body nodes (7,20,7) shard + sheath (6,30,6) trail; hits
brighter (190,225,255).
**Fire/Explosion anchors**: 'hip' at (0,0,0) did not show (Firaga flurry 53, Explosion orbs 68; the r_wep flash
did) → root with y < 0 (up) like Cloud's body rows: 68 root (0,-1,0), 53 root (0,-0.9,0), 54 root (0,-1,0).
test199 = test196-all + all of this; every step "nothing to do" on re-run; effe 848640 B. Textures:
`dumps/renders/kh2fx/test199/textures.png`.

## Lightning freeze bisect + safe Thundaga (2026-10-15, test202)
test200 (full Lightning transplant from test199) **froze on the first Bravery swing**. Bisect (test201 base):
- A full transplant → freeze. B resources only (o12 tex, MDL installs, global MDL 67, ANM 10) → no freeze.
- C gut leaves 49/50 only → no freeze. D only her leaf 47 tree → Sora 22 → **freeze**.
- ⇒ her node kinds 0x150 / 0xD0 / 0x64 (not in Sora's FEP) hang the game. Also: her ANM in Sora **ANM 10**
  froze **Explosion** (ANM 10 is shared with hit-mark leaf 39). Never transplant foreign trees/ANMs.
**spot33_lightningfx.py v3 (safe)**: TREES/ANM_OWN/MDL_OWN/MDL_GLOBAL/GUT all empty. Only: her o06 bolt tex → Sora
o12; Blade Beam wave MDL 30/31 (leaf 22) → o12; leaf 22 ANM remap 10→1; leaf 22/23 colours white-blue; FEPA 31→22
×1.0, 32/33→23 ×1.0, 30→23 ×0.6; FXSE leaf 22 empty, 23 → slot 77. Bisect env switches NO_TREES / GUT_ONLY kept.
Run: `python3 -I tools/scripts/spot33_lightningfx.py ISO dumps/ULUS10566.iso` (after spot33_magicfx).
**Firaga**: SPELL_ROWS 53 → leaf 19 FIGA_HIT_LAND root (0,-0.9,0) ×2.2 (fire ring at the feet); 54 → FIGA_HIT_WALL
root (0,-1,0) ×1.5.
**test202-fx verified in game** (live loadout poke): Bravery combos ×3, Explosion ×2 (orbs + flash), Thundaga ×2
(white-blue bolt down + burst), Blizzaga ×2 (ice ball, unchanged), Firaga ×2 (big fire burst) — no freeze, game
responsive after. Clips: dumps/screens/rec_20261015-082817 / 082941 / 083304 / 083415 / 083529 .mp4.
effe 848640 B; all five effect scripts "nothing to do" on re-run.

## test206 (2026-10-15 evening) — Firaga swirl + Thundaga bolt shape
Mat (after playing test205): "the thunder effects and the fire effects are still not done". test202's look, from the
clips: Firaga = one huge fire explosion filling the screen (FIGA_HIT_WALL ×1.5 + the FIGA_HIT_LAND ring at the feet);
Thundaga = the bolt texture on the Blade Beam CRESCENT mesh (MDL 30/31, a wide curved surface) → a big flat slab.
Targets: Firaga = flames circling AROUND Sora (KH2 Fire); Thundaga = bolts striking straight down + impact flash.
**Static findings** (scratch dumps; tools: fep_dump --leaf, node comps via fep.node_components):
- Node comps: 0x01 = rotation (deg; CHOU_FIRE's 6 flame cards at Y 0/±45), 0x04/0x09 = scale-like triples (meaning
  differs per kind; e0 nodes with 7 tracks carry (0,0,360) in 0x04 = probably a spin), 0x14 = MDL, 0x15 = ANM. The
  track "n" is a per-comp constant (0x0e always 3, 0x14 always 2), NOT a key count — keyframe curves not decoded.
  No usable orbit node found → the swirl is built from FEPA placement + spawn timing instead.
- MDL vertices = u8 u, u8 v (128 = 1.0), RGBA4444, s8 xyz; one triangle strip (prim 4) or list (prim 3) per draw row.
  MDL 30 = crescent (x ±127, bulging to +z, y = height); MDL 15 (FIGA flame mesh) = a tube (rxz 51-127).
- FX bit 19 (leaves 66-68 CHOU_V5_BOMB*) is LIVE (magi 0x52a/0x52b) — not free. FEPA rows 10-14, 16-18 (Cross-slash,
  slot _700A = stub for #33, ids in no script) are free; row 15 (ROT_HTM, fx 15) is live.
**Firaga** (spot33_firefx.py, now also edits the Firaga script blocks): SWIRL = rows 10-14,16-18 → ids 9100-9107,
leaf 16 FIGA_BALL (KH2 fire texture) ×0.7 anchored at `root` on a circle r 1.1 m, heights 0.5 → 1.4 m (rising
spiral), start offset +0x30 = 14 (only the last part of each 30-34 frame fireball). Blocks 97/100 (motions
10310/10313): op 0x19 one-shots 53/54 removed, swirl added every 3 frames 22-64 (≈2 laps) + burst id 54 at 50.
Row 53 (feet ring) is no longer spawned. Preview (mock-up): dumps/renders/kh2fx/test206/firaga_swirl_preview.png.
**Thundaga** (spot33_lightningfx.py): leaf 22's own meshes rewritten in place (same vertex count): MDL 30 → 3 crossed
ribbon planes along local z (w 22, colour 0xCCCC), MDL 31 → 3 wider dimmer planes (w 40, 0x6666), bolt texture o12
along them (u); MDL 33 (Ge crescent glow) collapsed (zero-area). FEPA 31 (falling strike) scale (1.2, 1.2, 2.0),
impacts 32/33 ×1.4. Assumes local z = flight axis (Blade Beam flies along +z); `BOLT_AXIS=y` env builds along y.
Preview: dumps/renders/kh2fx/test206/thundaga_bolt_preview.png.
`dumps/ULUS10566-test206-fx.iso` = test205-keyblade + both steps; effe 848640 B, FEP round trip byte-identical,
both steps "nothing to do" on re-run. Build lines unchanged (both steps already in build_sora.sh; spot33_firefx runs
after spot33_magic, so its script edit always finds the Firaga blocks). NOT yet seen in game (Mat playing).

## test210 (2026-10-15 evening) — Firaga comets + Lightning's real bolt mesh
Mat on test208: Firaga "the balls of fire are around him and don't leave, also the look should look like the KH2 not
like Cloud's"; Thundaga "does not look like thunder. Lightning from FF13 has thunder".
**Why the fireballs never left:** tree header +0x00 = **2 = LOOP** (every persistent body: SWORD_LOCUS trails,
FIGA_BALL, HAKOU_BODY, METEO_BODY, ULTIMA_AURA, CHOU_FIRE/SMOKE/LIGHT, KYOU_WORDS…; one-shots have 0). An op 0x19
spawn has no magi to kill it → each of test206's swirl fireballs burned forever. FEPA +0x30 = start time (the
instantiation FUN_08945bec refuses start ≥ tree duration +0x04, so it is a time skip).
**Firaga v3** (spot33_firefx.py): LOOP_OFF FIGA_BALL tree 2 → 0 (one-shot 50 frames; FIGA_BALL is drawn by no live magi
for Sora). KH2 FIRE_3 = two fireballs on orbit bones sp3/sp4 with flame trails → TWO COMETS 180° apart: 8 inner rows
(10-14, 16-18; ids 9100-9107) at r 1.0 m, chest height 1.0 m, x0.75, every 2 frames from 16 to 46 both comets step one
angle (16 frames a lap, ~2 laps), each fireball visible only its last SWIRL_LIFE = 5 frames (start 45) → two 3-ball arcs
racing round. Then the ring FLIES OUT: 6 OUTER rows (dead Blade Beam rows 24/25/26/27/43 + row 53, ids 9108-9113) at
r 2.0 m, x0.9, all at frame 47, 12 frames; end burst row 54 FIGA_HIT_WALL x1.5 → x0.8 at frame 48. MDL 19 (FIGA_BALL
glow, Ge) → KH2 fire texture o0f too. Preview: dumps/renders/kh2fx/test210/firaga_preview.png (top view mock-up).
**Lightning freeze, static digging:** component handlers are C++ objects registered at boot (0x0894dd74…0x0894e364:
each stores its vtable pointer into slot 0x089d9858 + 4*id, 95 ids) → every component exists for every fighter; the
per-FEP version table (header +0x08, 162 u32) is identical for Sora and Lightning; FUN_089453f4 checks each tree's
component list (tree +0x24, count +0x14) against it. Node +2 ("kind") is NOT derived from the components (same kind,
different component sets). Lightning-only pieces: components 0x19 (her leaves 33/47/63/66), 0x1a, 0x27, 0x3a, 0x44,
0x50, 0x96, 0x97; kinds 0x150 (47/66 = the bolt node), 0x64, 0xe7, 0xd4, 0xc4, 0xb0, 0x81… Component 0x19 = vtable
0x089dc608, only two own functions (init 0x0896d11c returns 1) = a DATA component read by another component (likely the
mesh draw 0x14 or 0x3d/0x3e of the kind-0x150 node). THUNDER_BODY (her leaf 47): nodes 0/1/3/4 kind 0xa7 sprites on
GLOBAL flipbooks G82/G8a (= Sora ANM 7 / 19), 5/6 0x100 global mesh f0000110, 7/8 0x8e her ANM 4 (G5 sparks), 9-11
0xd0 global meshes, **node 2 = kind 0x150 + comp 0x19 + her MDL 57 = the bolt** → prime freeze suspect. Bisect still
needs PPSSPP: her leaf 47 with node 2 removed vs only node 2.
**Thundaga v4** (spot33_lightningfx.py; only edit classes the test201 bisect proved safe): her MDL 57 (198-vertex strip,
a jagged forked bolt along her local y, uv on her o06 bolt = Sora o12) → Sora MDL 30 (leaf 22 node 5, native kind
0x100), axes y↔z (long axis = the strike's flight axis z), extents +0x40/44/48 x(1.5, 1.5, 2.9); MDL 31 (test206 glow
ribbon) shrunk to one degenerate triangle (1264 → 184 B) to pay the +640 B; FEP padded back (asserted 803952 /
effe 848640). Flash sprites → Lightning's global electric flipbooks: leaf 22 ANM 8 → 7 (G82), 9 → 19 (G8a); leaf 23
ANM 1 → 7, 0 → 19. test206 RIBBONS off. Preview: dumps/renders/kh2fx/test210/thundaga_bolt_preview.png (mesh with o12).
Risk: if the bolt lies flat in game, swap the axis mapping (y↔z assumption, same as test206's BOLT_AXIS).
`dumps/ULUS10566-test210-fx.iso` = test209-snd + both steps; effe 848640; firefx / lightningfx / weaponsfx all
"nothing to do" on re-run. NOT seen in game (PPSSPP busy with test209). Previews: tools/scripts/preview_fx210.py.
### test211 / test213 / test214 in game (2026-10-15 night; frame captures = pause → screenshot → resume, scratchpad spell.py)
- **Thundaga (test211 = test210 effects):** the bolt comes down VERTICALLY onto the foe (y↔z axis guess right): a thin
  bright white-blue streak, visible ~2-3 frames (the strike falls fast), then a large white-blue electric burst at the
  foe (G82/G8a flipbooks), sparkles. No freeze. Sheets: dumps/screens/test211fx/thun3_sheet.jpg, thun3_bolt.png. The
  orange glow on the raised Keyblade during the cast = Sora's weapon light/trail rows 7/8 (ids 9999/8888), not the spell.
- **Firaga test211:** fireballs no longer linger (LOOP_OFF works), but x0.75 at 1.0 m = small dark smoky puffs at his
  legs, and the FIGA_HIT_WALL end burst = Cloud's big orange smoky explosion hiding everything (fira2_sheet.jpg).
- **Firaga test213 fix** (spot33_firefx.py): SWIRL_SCALE 1.6, height 1.3, OUTER x1.8 at r 2.2 m, BURST = None (row 54 no
  longer scheduled; OLD_IDS 53/54 removed from the blocks), Cloud's smoke colour (48,64,128) → bright flame
  (250,150,50) (was KH2 smoke brown = dark), FIGA_BALL-only BALL_COLOURS → bright orange-yellow. In game: bright
  orange fireballs/flames all around Sora through the cast, no dark smoke, no Cloud explosion, nothing lingers, no
  freeze (dumps/screens/test213/fira_sheet.jpg).
- **Reproducible:** test214-full = coordinator's test212 (fresh build_sora.sh + _400A fix) + spot33_firefx /
  lightningfx / weaponsfx (only firefx changed anything) = objx byte-identical to test213 in every chunk; all steps
  "nothing to do" on re-run. Smoke test test214: battle, Bravery combo hits, Firaga cast, game keeps running.

## Q005 runtime experiments (2026-10-16 night, Fire/Thunder helper; baseline test223-reflect = test220 effe)
Baseline `dumps/ULUS10566-test223-reflect.iso`: objx 7e52a132…9fba, effe 848640 B 2972c168…38a3 (= test220/214).
**Method** (scratch tools in session scratchpad q005/: trace3.py log-BPs, step.py frame-stepped screenshots,
mkcand.py candidate discs). Effect clock = instance +0x15c, advances 2.0 per update at 30 updates/s (= 60/s, same rate
as script frames); a fighter trail instance (tree 1) is used as the global clock "c". ❗ PPSSPP JIT gotcha: log/pause
breakpoints added while the game RUNS are silently lost on some addresses (race) → add them while paused
(`cpu.stepping` → add → resume). Conditions on breakpoints did not fire at all here. `{[a1+0x15c]:f}` memory
derefs in logFormat work. KILLN/KILLI BPs stayed unreliable; node deaths come from the node lists instead.
Instance layout: +8 u16 tree index, +0x10 local pos (= FEPA row pos), +0x50..0x8c WORLD matrix (row vectors,
translation +0x80), +0x15c time, +0x1a8 duration, +0x1b8/+0x1bc node lists (node: +0x22 index, +0x30 age, +0x34 life).
Instantiation FUN_08945bec (f12 = start, a2 = tree) ✓ called from FUN_089444b0 @0x08944620.
### Fire (leaf 16, rows 9100-9113) — T0 baseline, ground 10310 + air 10313
- **FEPA +0x30 is NOT a seek.** FUN_08945bec gets start **0.0** for all 38 spawns (rows say 45/38). Every instance:
  nodes 0-5/7/9 spawn at t=2 (age 2), 6/8 at t=4 (children of spawner nodes 7/9), flame nodes die at age = life
  (30/34), instance dies at t=50 (natural end, ra 0x0894b4ec), 48 clock units after spawn — inner (45) and outer (38)
  rows identical. The row value goes to the effect HANDLE +0xe4 (FUN_088a68fc) = a countdown: 0x088a8f9c subtracts
  dt, at ≤0 calls FUN_088a4a6c → FUN_088a6aa4/6a78 (stop/release) — no visible effect on these one-shot trees.
  ⇒ "start 45 skips the flame phase" is REJECTED; the full 50-frame FIGA_BALL plays for every spawn.
- **Height: the flames are UNDER THE FLOOR on the ground.** The `root` bone is 0.63-1.06 m above the feet and its Y
  axis points world-UP (world +y = up: jumping gives pos y 2.16), so row pos y = -1.3 puts the anchor 1.3 m BELOW root:
  flame anchor −0.26…−1.04 m below the floor (mean −0.62, 753 samples). Air cast: root 1.09-1.48 m above the feet,
  anchor −0.63…+0.75 m relative to the feet (mean −0.13) = around/below Sora's feet. Frames: ground = only flame tips
  poking out of the floor around the legs; air = big fire masses under Sora (scratchpad sheet_T0fg.jpg / sheet_T0fa.jpg).
  The old note "root y<0 = up" is WRONG for this attachment; the visible fire was the upper part of meshes.
### Thunder (leaf 22 body / leaf 23 flashes) — T0 baseline, ground 10311 + air 10314
- Per ground cast: magi 0x7C4 at c, 0x7C5 at c+6, 0x7C6 at c+10. **Only ONE row-31 body (tree 22) spawns, at c, with
  0x7C4** (the spawner). Its world position: t=2 ≈7 m above SORA, then −(1.33, 1.37, −0.58)… ≈1 m/frame diagonally to the
  ground beside the foe (t=12, y 0.14); killed at t=14 explicitly (FUN_089446f0 mode 0, ra 0x089419a8 =
  FUN_08941994 = owner teardown). Its Z (long) axis = flight direction (diagonal), not vertical.
- Node 5 (bolt mesh, life 12) is NOT the limit: spawner node 4 re-emits node 5 at t=2, 12, 22 … (air cast shows 3
  generations); the instance kill at ground contact ends it.
- Visibility (stepped frames, camera behind Sora): t=2-8 the body is above/out of the top of the screen; it is in view
  only c+8…c+12 (≈3 stepped frames), then row-32 flash (started c+8) + "HIT" text cover the spot.
- Rows: 32 at c+8 at the foe (y 1.25, the hit), 33 at c+12 at the ground exactly where the body ended, 32 again at
  c+16 on the launched foe (0x7C6 impact). Air cast: 32 (foe) and 33 (ground) at the SAME clock. All leaf 23 ×1.4,
  60 frames each → 3 overlapping white flash trees per ground cast.
- **Interpreter is the reliable trace mode.** Under the JIT, which breakpoints fire was random run-to-run even when
  added while halted. With `[CPU] CPUCore = 0` (interpreter, ~87 % speed here) PAUSING breakpoints fire every time
  (log-only BPs pause instead of logging there). Start positions/timings are then frame-identical between runs
  (deterministic), which makes A/B comparisons exact. Config backup: scratchpad q005/ppsspp.ini.q005bak.
- **Thunder magi chain (interpreter, ground, foe 20 m start → Sora placed 8 m away):** c+0 0x7C4 + row 31 body (tree 22);
  c+6 0x7C5 spawned AND freed in the same frame (pos ≈2.9 m high, 2.2 m short of the foe; obj+0x24 = magi row ptr
  0x099cc314); c+8 row 32 at the foe (y 1.27) = the hit; c+12 row 33 at the ground where 0x7C4 lands + 0x7C6 (impact,
  spawn mode 5 at parent) + row 32 on the launched foe (y 2.52); c+14 0x7C4 freed; c+16 tree 22 killed (mode 0,
  owner teardown); c+26 0x7C6 freed (life 10); leaf-23 instances end at t=60. Row 30 is never spawned.
  ⇒ visible bolt lifetime = 0x7C4 flight (7 m above Sora → ground at the foe, ≈1 m/frame, pitch p24/25 = 60,
  speed p57/58 = 22, offset p18/19 = 7), NOT 0x7C5 and NOT node-5 life.
- T1 test226 (row 32 1.4→0.7) / T2 test227 (row 33 1.4→0.7): the bolt's on-screen window is unchanged (≈3 stepped
  frames, c+8…c+12, it is above the top of the screen before); the white ball afterwards is whichever leaf-23 row is
  still ×1.4 (T1: ground dome 33; T2: foe flash 32). Masking only covers the impact AFTER the bolt is already gone.
- T3 test228 (row 30 0.6→0.3): not run — row 30 never appears in any FX spawn log (FUN_088a68fc), so it cannot matter.
- T5 test229 (0x7C5 p57 30→9): timeline identical to baseline frame for frame (0x7C5 still freed at c+6) → p57 of
  0x7C5 has no effect; same expected for p58/p59 (T6/T7 below).
- ⚠ Side effect (my fault, 04:15 local): after a Thundaga KO the clip script's Square landed on the results screen →
  "Save Replay" wrote PSP/SAVEDATA/ULUS10566Replay01 (69 KB). Game saves untouched. Tools now refuse to press unless
  both fighters are live.
- T6 test230 (0x7C5 p58 30→9): identical to baseline. T7 test231 (0x7C5 p59 9→0): 0x7C5 still freed at c+6 and
  the first hit still c+8, but row 33/0x7C6 at c+10, 0x7C4 freed c+12, tree 22 killed t=14 — the visible body lands
  2 frames earlier, reproducible in 3 runs. Mechanism unresolved (0x7C5's p59 influencing 0x7C4).
- F0 test232 / F1 test233 / F2 test234 (all 14 Fire rows +0x30 → 0 / 38 / 45): interpreter traces identical to the
  baseline (38× start 0.0, same node table, 38× natural kill at t=50, same clocks) → FEPA +0x30 has no runtime effect
  on these op-0x19 one-shot FIGA_BALLs.
- T4 / F3 / F4 not run: no verified reversible draw/alpha/curve control (Codex stop condition).
- **Conclusions for the redesign:** Thunder = re-aim or replace the 0x7C4 body (it is the visible bolt; 0x7C5 never
  moves); keep only one leaf-23 flash at the impact (rows 32/33 overlap, 30 is dead). Fire = the ring anchor sign is
  inverted (use y > 0 for "up" from root on this attachment), lifetime is the full 50-frame tree per spawn.
- Answer with all hashes/byte manifests: codex/QUESTIONS.md Q-20261015-CODEX-005 "Answer — Claude". Evidence:
  dumps/screens/q005/ (sheets, frame stills, logs, tools, candidates.log). PPSSPP config restored to CPUCore = 1.

## Barrier resource audit (2026-10-16, Claude helper; Q-20261016-CODEX-001; static, NOT seen in game)
Baseline `dumps/ULUS10566-test247-reflectv.iso` (read-only): objx `be45da17…f546a`, effe 848,640 B, FEP 803,952 B.
Scratch tools (temporary, not kept):
(pse_scan.py, piece_scan.py, budget.py, detail.py, pdata.py). Canonical result: `tools/scripts/spot33_barrier.py`
(+ `kh2_reflect_mesh.py`), disc `dumps/ULUS10566-test249-barrier.iso` = test247 + it.

### Verdicts (the Codex asks)
| resource | verdict | evidence |
|---|---|---|
| leaves 49/50 KYOU_WORDS_1/2 | **FREE** | no FEPA row points at them (rows 53/54 were repointed to Firaga). The ONLY leaf-spawn path is FEPA row → FUN_088aa4e0 → FUN_088a68fc → FUN_088a4d7c(res = row +0x28) → FUN_08941914 (each has a single caller in dumps/decomp/all.c) → a leaf without a row cannot be instantiated. Emptying 49/50 already ran in game without a freeze (test201 bisect C). |
| leaves 51/52 KYOU_WORDS_3/4 | **FREE** | only rows 55/56 → them; their only spawners are magi fx bits 12/13 = magi 0x47D/0x47C (no other magi has those bits); 0x47C-0x47F are spawned ONLY by op 0x43 hits in p_se block 58, whose only motion is 10090 (Cloud's Cross-slash). No plya piece has 10090 at +0x1c/+0x10/+0x1e, no comb action reaches such a piece, no script parameter names 10090. Explosion/Guard Break (block 65, ex-Cross-slash copy) no longer carries the 0x47C-0x47E params. FXSE records of leaves 49-52: none. |
| FEPA row 55 (id 55) | **FREE** (for Sora) | id 55 is a literal in EBOOT FUN_08a4e1d8 = update of EX-Burst **controller 14** (vtable at manager +0x160 → index (0x160-0x10)/0x18 = 14) and spawns from THAT fighter's own library; #33 runs controller 0 (chrp +6 = 0). Repointed to id 9121 anyway. |
| FEPA row 56 (id 56) | **FREE** | no literal anywhere (literal ids in all.c: 0-6, 8, 9, 12-17, 20, 41, 45-48, 51, 52, 55, 60, 61, 78, 80, 81, 85, 86, 96…125, 1000). Now id 9120. |
| MDL 63-70 (6,664 B) | **FREE** | each drawn only by one of leaves 49-52 (63/64 → 49, 65/66 → 50, 67/68 → 51, 69/70 → 52); no shared data blobs. |
| TEX 9 (o09) / TEX 20 (o14) | **IN USE** — untouched | o09 = KH2 ice (MDL 37/38/40-42/80/83 + 64/66/68/70), o14 = Explosion swirl (MDL 82). The step asserts both byte-identical. |
| new TEX index 21 | **ALLOWED** (static) | appending a TEX record is a format-normal op (fep.py add_tex; Emperor's FEP has 25 TEX); bytes paid inside the FEP so effe stays 848,640. Runtime unknown: texture-manager capacity with two Soras (mirror match, 2 × 22 TEX; Emperor mirror = 2 × 25 works in the vanilla game, so very likely fine). |
Corrections to older notes: leaf 46 CHOU_FIRE is NOT free (FEPA id **50** is spawned by the burst grade table, notes/ex-burst-controller.md §2) — fep_edit --usage cannot see table-driven ids; FEPA ids 50/51/52 (= leaves 46/47/48) must not be confused with leaves 50/51/52.

### More provably dead effect resources (for later layers; same no-FEPA-row proof)
Leaves with NO FEPA row on test247 (bytes = tree subgraph): 10 KYOUGIRI_KENATSU 2,600 (+excl. MDL 9 3,024), 11 DIST
2,372, 12 KYOU_APPEAR 6,900 (+MDL 10 2,416), 13 SWORD_LOCUS_B 1,712, 14 KYOUGIRI 3,996 (+MDL 12 2,416), 20 HAKOU_APPEAR
7,440, 21 HAKOU_SHOT 14,904 (+MDL 26/28 2,176), 26 METEO_APPEAR 8,932, 28 METEO_HIT 8,080, 29 METEO_HIT_LAND 14,680
(+MDL 44 2,024), 39 HAKOU_BG_HTM 5,276 (ANM 10/18 exclusive — do NOT edit ANMs: ANM 10 froze Explosion once), 49/50,
53 CHOU_HIT_LOSS 14,420 (MDL 72/73 share a blob with global 71 — leave them), 64 CHOU_V5_HIT 7,152. ≈ 105 KB of trees
+ ≈ 16 KB exclusive MDLs. Used by spot33_barrier so far: 10, 12, 14, 49, 50 (+ MDL 9/10/12/63-67/69 → degenerate).
Rows that look idle but are NOT proven free: slot-bound rows (28, 34, 35, 44, 46-49, 58, 59, 62-64, 74-77 —
FUN_088aa844 name check unresolved), *_HTM rows 6/9/15/36/42 (per-character hit-spark table data never found),
row 54 (rewritten by spot33_firefx on every run), rows 50-52 (burst grades). Extra layers therefore need either new
FEPA rows appended to the .feb (+0x104 B each, paid from the FEP pad; static only) or a slot-bound proof.

### KH2 Reflega as authored (kh2_pax_dump pdata programs; KH2 cm, −Y up, 4096 time units = 1 frame)
- Element 0 (ground, se177): pdata 0, all layers TEX0 + refraction VSF 0, offset 85 cm up from bone sp0.
  L1 model 4 (dome) scale 0.58 frames 0-25, colour (169,162,112) → after 4 f ≈ (79,205,181) (cyan), UV scroll
  (DrawMdlTs3); L2 model 0 (same dome) 0.58, frames 8-27; L3 model 5 hull 0.23 frames 0-12 (inner flash);
  L4 model 3 side shell 0.23, 0-8; L5 model 1 ground ring at y 60, 0.36 growing +0.0137/f, 0-10, alpha fade;
  L6 big glow sprite (shape 7, ×7) 0-10; L7 sparkle particles 5-27; L0 model 2 plane = refraction layer.
- Element 2 (air variant): pdata 2: model 6 (full faceted sphere) 0.56 × element 1.08, same colour scheme, + models
  7-10 (refraction plane, hulls). The shell layers have NO scale programs (constant size): the "pop" is the hull/ring/
  glow flash; the end is the 8-frame DestroyFadeout. Reflected-hit layers = pdata 4-6 (models 12-17, TEX1/TEX2, se178);
  burst = pdata 7/8 (models 18-20, se173/174).
- TEX0 = a narrow iridescent streak (u 4-22 of 128); the shell's KH2 UVs (each facet 16 texels wide, u 16-72)
  only hit it while KH2 scrolls them — a static native copy is ≈ invisible (offline render confirmed).

### What was built (spot33_barrier.py, v1 = closest provably safe version)
| layer | KH2 source | native | cost |
|---|---|---|---|
| ground guard (blocks of 470 / 10318) | dome model 0 ×0.58 (r 1.98 m) | leaf 52 node 0 (kind 0xc0) → MDL 70, FEPA row 56 id 9120, root +0.68 m | 6,272 B |
| air guard (blocks of 471 / 10319) | sphere model 6 ×0.605 (r 2.07 m) | leaf 51 node 0 → MDL 68, FEPA row 55 id 9121, root 0 | 10,880 B |
| texture | KH2 TEX1 (cyan panel gradient), premultiplied | NEW TEX 21 key 0x98012815, each facet mapped over the whole texture (uv 'facet') | 9,280 B |
Node init: rotation 0, scale 100 %, offset 0, life 34 (guard 0-36), tree one-shot 40 frames; node 1 of both leaves
hidden. Paid by emptying trees 10/12/14/49/50 (-17,468 B) + MDL 9/10/12/63-67/69 → degenerate; pad → FEP exact.
Remaining FEP headroom (trailing zeros): 4,464 B. kh2_reflect_mesh reproduces Codex's shell0 prototype byte-exactly
(768/768 vertices + UVs) at Codex's 1.4 m scale. Preview (offline, flat-shaded additive):
`dumps/renders/kh2reflect/barrier/preview_test249.png` (KH2 wireframe | native decoded | textures).
Order-independent with spot33_exguard (test248): either order + re-run = "nothing to do" (blocks 60/67 get the same
records). Other effect steps (fx, burstfx, firefx, magicfx, lightningfx, weaponsfx) = "nothing to do" on top.
Codex's pending Fire/Thunder candidate (tools/codex/20261016-fire-thunder-redesign) touches only tree 16 + FEPA rows
10/14/32/33 → no overlap.

### Fidelity options, ranked (closest to KH2 first) and their cost
1. v1 built: real KH2 dome/sphere geometry at KH2 size, cyan panels, 34-frame life (static size, pops in/out).
2. + inner hull flash (model 5 ground / 8 air, ×0.23, 12 frames): +7.4 / 9.7 KB + one FEPA row each (append). Budget
   OK (free trees above). Static only.
3. + ground ring (model 1, growing 10 frames) and the white glow sprite: needs node scale/alpha animation — decode
   comp 0x04/0x09 (values like 52.3 → 36.0 on FIGA_HIT_WALL's ring) or keyframe tracks by A/B runs.
4. + reflected-hit panel shell + rings (pdata 4-6, TEX1/TEX2) on every reflected hit: needs an effect spawn from the
   spot33_reflect hooks (code; battle-overlay cave is full) — larger job.
5. KH2's TEX0 sheen with UV scroll, colour warm→cyan, 8-frame fade, refraction: needs native UV/colour tracks
   (undecoded); screen refraction probably not possible on this engine.
A/B switch already in the step: SHELL_TEX = 0 + uv 'source' = KH2's own static mapping (expect near-invisible).

### Runtime checks (need the emulator; nobody ran them)
1. test249, CPU Minimal + Order's Sanctuary: EX Mode, guard on the ground → dome around Sora from frame 0, gone after
   ~0.6 s; guard in the air → sphere; normal (non-EX) guard → no barrier. Repeat 5× → nothing lingers/accumulates.
2. Reflect an attack (melee + projectile) while it shows → no freeze; EX expiry during a guard.
3. Look: dome open at the BOTTOM (if upside-down: flip y in kh2_reflect_mesh), rim near the floor, top above the
   head; size (ROW_SCALE), height (ROW_POS), brightness (TINT) on a bright stage.
4. Unchanged: Firaga, Thundaga, Blizzaga, Explosion, weapon trails, dodges, hit sparks, EX Burst; Cloud vs Sora and
   Sora vs Sora (two FEPs with TEX 21: texture-manager capacity).
5. Unknowns this tests: comp 0x01 = rotation / 0x04 = scale % / 0x0e = offset (inferred from values); additive blend
   (premultiplied texture); one 768 / 1,344-vertex triangle-list draw row on a kind-0xc0 node.

### Vertex budget and effect arena (v2 / test253, 2026-10-16T06:53:56Z, static; test250-252 froze in game)
Mat: test250/251/252 (v1 barrier on test248, test252 = without TEX 21) froze after EX guards; crash PC 0x08964eac
(FUN_08964eac) from FUN_089656d8 (ra 0x08965778). test248 alone is fine. v1 meshes: MDL 70 = 768-, MDL 68 =
1,344-vertex triangle LISTS; every original Sora MDL is <= 454 vertices (MDL 57 strip), largest list 384 (MDL 41).
**Effect scratch arena (store +0xb0)** = FUN_08974a3c bump allocator {+0 buf0, +4 buf1, +8 cursor, +0xc index,
+0x10 half size, +0x14 bytes used last frame}: created in FUN_08941388 as FUN_089749d4(arena, effect heap + 0x40000,
**0x8000**) = two 16 KB halves; FUN_08974a00 flips halves once per effect frame (FUN_08940bd4) -> **16,384 B per frame
for every effect on screen** (one effect system for all fighters). Users: particle sprite draws (16 B per particle,
FUN_08975594 + 8 siblings), ribbon/trail draws FUN_08964eac (64 or 96 B per point), FUN_08978bf8, FUN_08984dec,
FUN_0898658c/866c8/86834, 0x089c2e10.. (32 B units). Every caller checks for 0 and skips drawing.
**MDL meshes do NOT use it:** component 0x14 draw FUN_08956200 -> FUN_089720b0 -> FUN_08971768 -> FUN_08972194 hands
the GE the MDL's own vertex memory (FUN_089a0520(prim, vtype, n, 0, mdl + offset)), only a material callback per draw
row; init/update slots make no calls. MDL header correction: +0x14 = PART count, +0x18 part table, 0x34 B per part
{n rows, rows offset, cull flag (0 = no culling), 6 floats, UV scale, UV offset}; rows {prim, vtype, stride, texture
index, n, offset}. The per-vertex float rebuild into the display list (FUN_0895e7b8, n x 24 B through the UNBOUNDED
FUN_089a00f4) is component 0x44's (Lightning only).
**Crash site:** FUN_089656d8 = component 0x3b's draw (vtable 0x089dc248 +0x24), a ribbon; NO tree in Sora's FEP has
component 0x3b -> the victim is another library's effect (system/common or the opponent's). The JIT fault is in the
first block (pointer loads from the instance +0x8c/+0x90), so the instance memory was already bad, not the arena.
-> Shared memory corruption whose writer is not found statically; vertex count is the empirical suspect only.
**v2 rule (asserted):** every barrier MDL = ONE triangle strip (prim 4, like the originals), <= 384 vertices
(kh2_reflect_mesh.MAX_VERTS). Strips follow KH2's own quad bands (the OMD quad list is quad-strip ordered; bands split
where the run turns); per-facet UVs mirrored along a band so neighbours share vertices; one repeated vertex flips the
diagonal wherever KH2 changes its fold (hex look), within the budget:
| layer | KH2 facets | strip vertices | KH2 fold diagonals | MDL bytes |
|---|---|---|---|---|
| ground dome (model 0) | 128 / 128 (4 rings) | 303 | 128 / 128 | 2,552 |
| air sphere (model 6) | 160 / 224 (5 rings; pole cap + lowest ring dropped) | 371 | 144 / 160 | 3,096 |
(full sphere = 534 strip vertices; without only the pole cap 406/470.) Byte cost now small: only leaves 49/50 are
emptied (exactly the test201 bisect-C set; trees 10/12/14 stay, their MDL 9/10/12 degenerate). FEP headroom 4,096 B.
BARRIER_SCALE default 2.5 (Mat: bigger); the ground row offset keeps KH2's rim 0.28 m above the floor (2.55 m above
root at 2.5). Preview: dumps/renders/kh2reflect/barrier/preview_test253.png (KH2 source | native strip | game-scale side
view with floor + 1.5 m bar). Disc dumps/ULUS10566-test253-barrier.iso = test248 + v2 (sha256 10b2c92f…e9a2).
**If test253 still freezes**, vertex count was not the cause; bisect next (each one change on test248): (1) remove only
the op 0x19 records (resources bound, never spawned) -> if it freezes, a load/registration problem; (2) spawn with
BARRIER_SCALE=1.0; (3) keep the KYOU_WORDS node init values (rotation 90 / scale 30 / offset -1.2); (4) loop flag/
duration untouched. In the debugger: a write breakpoint on the crashing comp-0x3b instance's +0x8c field finds the
writer directly (the coordinator owns the emulator).

### Pole caps (test264, 2026-10-16T07:55:11Z, static; Claude helper)
Mat (test262b, half dome x4.0, TEX 9): "for the barrier there's a hole, can this be covered up?". KH2's sphere model
6 is itself open at both poles (64 boundary edges = two 32-vertex loops). Each loop is a 16-pointed star: top tips
r 175 / h 313, notches r 144 / h 333 KH2 units (≈ 7 m across at x4); the air sphere's cut at ring 5: tips r 315 /
h −159, notches r 292 / h −206. A zigzag fill folds over a star (offline render showed overlap stripes), so
kh2_reflect_mesh.cap_strip fans around a NEW pole vertex on the sphere (radius 342 → shallow cone), strip-encoded
as L0 P L1 L2 | L2 P L3 L4 ... (no duplicated triangles, ~2 vertices per loop vertex; asserted triangle set).
Mode 'tips' fans over the 16 outer tips only (half the cost; still covers the hole in projection).
| layer | facets | caps | strip vertices | budget | KH2 diagonals |
|---|---|---|---|---|---|
| ground half dome (model 6 top 4 rings) | 128 | top full fan (32 loop verts) | 369 | 384 | 128/128 |
| air sphere (model 6, 5 rings) | 160 | top full fan + bottom tips fan (cone to the pole) | 440 | 454 (MDL 57) | 128/160 |
The ground half dome stays open only at its floor rim. FEP size: the barrier now needs ~1 KB more than test262b had
free in reachable form; the old pad bytes absorbed into the file's last blob are now trimmed and re-padded
(spot33_barrier edit_fep), so effe stays 848,640 B and only MDL 68/70 differ from test262b (asserted: every tree,
TEX (count 21), ANM, FEPA, FXSE identical). Preview with the disc's real TEX 9:
dumps/renders/kh2reflect/barrier/preview_test264.png. Disc dumps/ULUS10566-test264-barriercap.iso = test262b +
spot33_barrier (sha256 49134d6f483184430677ba4a963fc2fbb99d5a63bfa6525f0834a2f6393b83f6). Not played.
Pre-existing on test262b (not from the barrier): spot33_weaponsfx --dry wants to change 26 blocks, spot33_lightningfx
asserts "MDL 30 also drawn by {22, 23}" — both identical on unmodified test262b (Fire/Thunder integration).

## Magnet Burst (2026-10-16, Claude Magnet helper; static, NOT seen in game)
Mat: Magnet Burst should look like KH2 (purple-pink-white gravity orb, rings pulling in, then a burst), not Cloud's.
Before: test275 = Codex stopgap (Explosion swirl FEPA 68 @18 + flash 57 @60 in block 68; Mat: at least visible).
**KH2 sources** (`tools/scripts/kh2_magnet_mesh.py`, sha256-guarded):
- KH2FM Magnet Burst = `P_EX100.a.us` PAX elements **51** (vortex, bone sp0 1.27 m up, loops while motion 788 runs,
  se 169 = the Magnega loop sound) and **52** (burst at f31). DPD 3 model **27** = star-shaped swirl disc (48 verts,
  3 rings x 16, KH2 billboard), drawn with DPD 3 tex 5 = the **Magnet swirl streaks** (byte-identical to MAGNET_3 tex
  0); model 35/36 = flat burst rings; orbiting orbs = sprites (tex 7) on spinning carriers.
- Magnega = `magic/MAGNET_3.mag` element 3: model 9 (= model 27), model 10 = **ring band** (cylinder r 800 h +-97,
  warm/cool vertex colours alternating, spins), 11 = small swirl disc, 12/13 = arcs, tex 1 = the orb sprite.
  Textures: dumps/renders/kh2magnet/src/. Video frames: dumps/renders/kh2video/magnet_burst_16m28.jpg.
- Many KH2 models use "common" textures (TBP outside the DPD) -> not available; the swirl texture is.
**What was built** (`tools/scripts/spot33_magnet.py`, disc test277):
| layer | KH2 | native | spawns (block 68) |
|---|---|---|---|
| ORB | orb sprite -> 2 nested spheres with the KH2 swirl texture (a sprite always looks round; so does a sphere) | MDL 26 (334 v strip), leaf 20 | 14 (36 f), 38 (22 f), pulses 20/42 x1.35, flash 60 x2.4 |
| RINGS | disc model 27 (KH2 UVs) + band model 10 | MDL 28 (206 v strip), leaf 39 | pull-in 4 rings 3.2 -> 1.3 m every 3 f before each hit (8, 30, 48), turning 22.5 deg + tilted; burst 1.2 -> 5.4 m at 60/62/64/66 |
- TEX 19 o13 (Cloud's gradient) <- KH2 swirl, same size/key (brightened: premultiplied ^0.7 x1.6). o13 was drawn only
  by ANM 16 = leaves 29 (no row) / 38 (row 42, magi bit of unreached magi). TEX count stays 21.
- MDL 26/28 = Blade Beam meshes of leaf 21 HAKOU_SHOT (no FEPA row). MDLs sharing a blob with a global record (24, 4,
  72/73) avoided; barrier/fire/thunder MDLs untouched.
- Leaves 20 HAKOU_APPEAR / 39 HAKOU_BG_HTM (no row) <- copy of **p_thr100 leaf 46 SWORD_WIND** (clean ISO): the only
  single-node kind-0xc0 tree with the barrier node's component list (01/04/07/11/0e/14); version tables identical
  (asserted). Comps 0x11/0x14 params set to the barrier node's vanilla bytes (0x11 ends 0x0101 vs donor 0x0001 =
  maybe blend; 0x14 donor had 2/6/64/32 = maybe UV scroll). Their FXSE records (Cloud slots 36/25) muted.
- FEPA rows 11-13, 16-18, 24-27, 43, 53 = spot33_firefx's pool (ids 9101-9113 except 9104, unspawned since Codex Fire
  v1) -> ids 9130-9141, root-anchored (y > 0 up), +0x30 start offset = shorter life (visible = 36 - start).
  Re-running spot33_firefx after this silently takes the rows back (it also undoes Codex Fire: never rerun it late).
- Re-run checks on test277 vs test275 (--dry): fx, burstfx, magicfx, lightningfx, barrier, exguard, reflectvoice =
  'nothing to do' on both; firefx/weaponsfx/trinity want the same pre-existing changes on both. Only new one:
  spot33_sndtrim would now empty Cloud slots 25/36 (their only users were the muted FXSE records) = harmless.
- FEPA rotation +0x0c = degrees (Cloud's rows use -90/90/-70; checked).
- Previews: dumps/renders/kh2magnet/preview_meshes.png (KH2 source vs native), preview_timeline.png (all live
  instances per script frame at game scale, 1.5 m bar = Sora).
- Also: plya 0xb32 flags 0x10013 -> 0x10012 (stuck-in-fall fix, notes/abilities-owner33.md).
- Disc `dumps/ULUS10566-test277-magnet.iso` = test275-solo2s + spot33_magnet only (sha256 82de4bc4980fec09…f3f693);
  only obj/p_sev120.objx (+304 B, + its size field) differs. NOT in build_sora.sh yet (would replace the
  magnet-visible-dispatch line, after the Codex Fire chain). Not played.
**Runtime unknowns:** whether the kind-0xc0 mesh draws world-flat discs readable from the battle camera; brightness
(MAGNET_TEX_GAIN / MAGNET_OPACITY env); size (MAGNET_SCALE); root rotation during the 788 spin.

### ❗ Freeze in test280 (test275 + AI + magnet) = node serials (Magnet helper, 2026-10-16T14:24:38Z, static)
Mat: Sora vs CPU Sora froze on a GROUND Bravery attack, PC 0x08964eac (from 0x089656d8, ribbon draw = the same PC as
the barrier freezes test250-252). Coordinator's bisect: test276 (AI only) does not freeze -> spot33_magnet.
- Each tree's t2c list (tree +0x2c, count +0x18) = {u16 n, ptr -> n x (u16, u16 SERIAL)}, one entry per node slot.
  Vanilla (Cloud 469 entries, p_thr100 567): serials = ONE FEP-wide sequence 0..N-1 in tree order. The engine evidently
  keeps a per-FEP table of N entries indexed by serial (the loader does not touch them; instancing does).
- Removing nodes leaves holes but keeps the old serials -> max serial >= N -> out-of-bounds writes for the last trees:
  test275: N 463, GARYUU_FIN_HIT (leaf 74, Blizzaga hit) serials 463-468 overflow (latent!). test277/280: my 1-node trees
  replaced 7+4 nodes -> N 454 and the donor's serial 307 twice -> leaves 72-74 overflow, incl. **73 DRAW_SONIC = FEPA
  row 77, slot-bound to _600A frame 0 (a ground Bravery slot)** -> heap corruption on the first ground attack -> freeze.
- Same story explains: Lightning tree transplant test200 ("froze on the first Bravery swing": her serials, her
  numbering) and barrier v1 test250-252 (5 trees gutted, 17 serials over). The 22nd-texture verdict (test258) may be
  partly this too (test253 = only 6 over).
- RULE: any step that copies, guts or shrinks a tree must rewrite the serials dense 0..N-1 in tree order.
  spot33_magnet.renumber_serials() does it (whole FEP, idempotent); it also clears test275's latent leaf-74 overflow.
  spot33_barrier still guts 49/50 without renumbering (fine as long as spot33_magnet runs later; better: add it there).
- Fix disc: dumps/ULUS10566-test281-magnetfix.iso = test275 + fixed spot33_magnet (serials 0..453, no dups/holes)
  sha256 bd8a6aec5113b3bfd9fd37dbb836d22f9d3ede8333a78af37a147f8f5e2e4e02. Only obj/p_sev120.objx (+ size field)
  differs. barrier/lightningfx/fx/magicfx/burstfx --dry = nothing to do. test277 (and test280) = DO NOT USE.

### ❗❗ Real freeze cause (test280/284): node init data lost its 16-byte alignment (Magnet helper, 2026-10-16T14:49:41Z, static)
test281's serial fix did NOT help (test284 froze the same: PC 0x08964eac, a1 = 0x09c6c08c, a 16-byte VFPU vector load from a1).
- FUN_089656d8(.., node instance, third argument = a component's INIT DATA inside the loaded FEP, ..) -> FUN_08964eac
  reads that init data with 16-byte VFPU vector loads (need 16-byte alignment). Init data +0x2c = TEX index -> it is the
  sword-TRAIL component
  (0x69/0x6a, leaves 7/13/33/35/56/57) = drawn on every attack, by both Soras.
- Vanilla rule (Cloud 469/469, p_thr100 553/553): every node init block (fep.py kinds n20_data, n24_data) starts at a
  file offset = 12 mod 16 (4-byte header, then the vectors 16-aligned; the FEP loads at base = 4 mod 16).
- fep.py write() only aligns blobs to 4 (16 for TEX/MDL). My tree copies changed sizes by non-multiples of 16
  (-6008, -3844 B) at leaf 20 (early in the file) -> EVERY later init block moved to 4/8 mod 16 -> the first trail
  drawn reads misaligned -> address error -> hang. test275 is fine: only leaf 16 (FIGA_BALL, Codex Fire) has 59
  misaligned blocks (kept as is, apparently not read by vector loads).
- Very likely the same cause: barrier v1 test250-252 (same PC; guts of trees 10/12/14 shifted the layout), Lightning
  transplant test200 (froze on the first Bravery swing). The serial overflow theory above is unproven (renumbering
  kept anyway: it is the vanilla format).
- Fix in spot33_magnet: align_layout() inserts zero filler blobs so every blob keeps its input offset mod 16 (copied
  blobs: the donor's). Asserted: all 13,935 other blobs = same kind + same offset mod 16 as test275; init-data
  misalignment count unchanged (59, leaf 16 only); the two magnet nodes' init data = 12 mod 16.
- RULE for every FEP writer (barrier, firefx, lightningfx, Codex): keep each blob's offset mod 16 (or at least
  n20_data/n24_data = 12 mod 16). Better: make fep.Fep.write() do it (not changed yet: shared tool).
- Disc dumps/ULUS10566-test285-magnetfix2.iso = test275 + spot33_magnet (alignment + serial fix), sha256
  98b7260ab31eab4b83632e6e5eb390cb3846369a2b01b9e192848ec013398c63; only obj/p_sev120.objx (+ size field) differs;
  barrier/lightningfx/fx/magicfx/burstfx --dry = nothing to do. test277/281 (and 280/284) = DO NOT USE.
- AI v2's newly reachable CPU moves (Explosion, Fire, Aerial Finish, Blizzard, Thunder): none spawns a resource the
  magnet step changed (rows 10/14, 22/23/27/25/74, 68/57, trails); they froze only because ALL init data was shifted.
- **Runtime (2026-10-16T15:11:24Z, Claude): test286 (AI v2 + magnet alignment fix) ~10 min vs CPU Sora, no freeze → alignment fix confirmed in practice.**
- **Mat on test287 (2026-10-16T16:55:30Z): Sora falls/lands well after Magnet (stuck fix verified), but the new Magnet effects are NOT visible.**

### ❗ Invisible Magnet (test287, Mat: "Sora falls down well but I can't see the new effects") — KEYFRAMES (2026-10-16T17:02:08Z, static)
- A node's drawn values live in its KEY blocks, not in the init block (n20) that spot33_barrier/magnet edited:
  node +0x24 -> node[0x13] items {u16 start, u16 len, u32 n, ptr} -> n x {u16 track, u16 offset, u16 start, u16 len}
  + params (same layout as the init block). Key 0 holds every comp; later keys hold only comp 0x11 (alpha keys).
  Node header +0x0c/+0x0e = key change frames. fep.node_resources() reads only the init block (MDL users miss keys).
- My donor tree's key 0: scale 10 %, rotation z 180, RGB (128,160,192), alpha 160 and **comp 0x14 MDL index 79** (the
  donor's own) -> the magnet nodes drew Sora's MDL 79 at 10 % -> nothing to see.
- Side finding, barrier: its init edits (rotation 0, scale 100, offset 0) are no-ops; in game it uses key 0 =
  rotation (90,0,0), scale 30 %, offset (0,0,-1.2) (vanilla KYOU_WORDS). Native meshes are authored flat in x/z with
  y up (MDL 22 Firaga ground ring draws with rotation 0; KYOU marks are flat and stood up by rotation 90) -> the
  barrier's y-up KH2 dome is probably drawn rotated 90 deg about x (dome axis forward/back). Mat liked it, so not
  touched; explains why it needed x4 and odd offsets. If Mat wants a true dome over him: set its key-0 rotation 0.
- Fix (spot33_magnet KEY_VEC/KEY_RAW): every key block of leaves 20/39: rotation 0, scale 100, RGB 128, offset 0;
  comp 0x11 keys + comp 0x14 key = the barrier node's vanilla bytes (alpha 0 -> 128 fade-in over 3 frames, flags
  0x0101 / 01 03 00) with MDL 26 / 28. 76 FEP bytes change; layout, alignment (59 = leaf 16 only), serials unchanged.
- Disc dumps/ULUS10566-test290-magnetvis.iso = test289-firecore + this, sha256
  7e861cc5472aa1ffd97ea33300ffd5da5e1aab3399fa5bfca359f218230a30c8 (only the effe chunk differs; barrier /
  lightningfx --dry nothing to do).

### Barrier upright + centred (test292, 2026-10-16T17:07:28Z, Magnet helper, static; Mat: "yes")
- spot33_barrier now edits the KEY blocks of the shell nodes (leaves 51/52 node 0): key 0 rotation (90,0,0) -> 0,
  offset (0,0,-1.2) -> 0; scale kept at the vanilla 30 % (visible radius = 2.07 m x 0.30 x BARRIER_SCALE 4.0 ~ 2.5 m,
  the size Mat approved). Guarded (old values or ours, scale asserted 30 %), re-runnable. Alpha keys / timing
  (fade-in 0 -> 128 over frames 0-20, hold to 34) untouched; opacity 0.25 unchanged. Init-block NODE_INIT edits stay
  (harmless no-ops).
- Air sphere row 55: y 0 -> +0.35 (env BARRIER_AIR_Y; root ~ hips -> centre on the chest). Ground row 56 stays
  y -0.85 (sphere centre = feet -> half dome base on the floor).
- New guard misaligned_init(): the FEP rewrite may not add node init/key blocks off 12 mod 16 (test280 freeze rule).
- Preview (offline, disc MDL 70/68 + TEX 9): dumps/renders/kh2reflect/barrier/preview_test292_before_after.png -
  BEFORE = dome lying on its side behind Sora; AFTER = half dome over him (base at the feet) / sphere on his chest.
- Disc dumps/ULUS10566-test292-barrier.iso = test290-magnetvis + spot33_barrier only (12 FEP bytes + FEPA row 55),
  sha256 9f48d1167a589eaf8881e76583de27317eb8bbf1f43247bb120be4528b1cfdf6. barrier/magnet/lightningfx --dry =
  nothing to do; alignment (59 = leaf 16 only) and serials unchanged. Not played.
- ❗ Also noticed (Q005 runtime trace, line ~723): FEPA +0x30 start offset has NO runtime effect on op 0x19
  one-shots -> spot33_magnet's short ring lives (start 30/31) do not work: every magnet ring/pulse lives the full node
  life (36 frames) -> rings of all sizes overlap; the burst flash orb lasts 36 frames. Fix needs the node life / key
  timing of leaf 39 shortened (or fewer spawns) - waiting for Mat's look at test290/292 first.
