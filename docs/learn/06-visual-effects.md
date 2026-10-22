# Chapter 6 — Visual effects

**The big idea:** every fighter carries a **box of fireworks**: pictures, little 3D shapes, and
recipes that say how to combine them into a sparkle, a flame, or a bolt. A separate **menu
card** says "firework number 22 = recipe 18, 1.5× bigger, stuck to the hip". Scripts and
projectiles call fireworks by number. We gave Sora KH2-looking fireworks by **repainting and
reshaping the ones he already had** — because the box must never get bigger, or the game
freezes.

This was the hardest part of the project so far, with the most freezes. Read the stories.

---

## 6.1 The effects chunk (`effe`)

Inside the battle file, chunk `effe` is an **MPK box** with three members, taken **by position**
(not by name):

| # | member | what it is |
|---|---|---|
| 0 | `p_sev100.fep` | the **FEP**: the box of fireworks (textures, shapes, recipes) |
| 1 | `p_sev100.feb` | the **FEPA** table: the menu card (id → recipe, size, where to attach) |
| 2 | `p_sev100.fxseb` | the **FXSE** table: sounds tied to effects (Chapter 5) |

(The names still say `p_sev100` = Cloud. That's harmless: nothing looks them up by name.)

### Inside the FEP

| part | count (Sora) | what it is |
|---|---|---|
| **TEX** | 21 | textures: 256-colour pictures, 128×64 or 128×128, PSP-swizzled |
| **MDL** | 85 | tiny meshes: billboards (flat cards that face the camera), rings, tubes |
| **ANM** | 21 | flipbooks: animations that step through frames of a texture sheet |
| **leaf** | 75 | one **effect** = a tree of **nodes** |

A **leaf** is one firework recipe, for example `FIGA_HIT_WALL` (Firaga hitting a wall). Its
**nodes** are the parts: an emitter that throws out particles, a mesh that grows, a flash.
Each node is a list of **components** (position, rotation, scale, colour, which MDL to draw,
which ANM to play…), some with keyframe tracks over time.

Colours are numbers where **128 = normal brightness** (PS2 habit). Values above 128 glow brighter.

A tree's header has a **loop flag**: `2` = keep playing forever (trails, auras, flying
fireballs), `0` = play once. Remember this one (6.8).

### Global textures

Some textures belong to **everyone**: keys `0xF00000NN`, stored in a system file
(`resident.frr`). Soft orbs, sparkles, ring flashes. **Never edit them** — every fighter would
change. Sora's leaves can *use* them freely.

### The FEPA table (the menu card)

Rows of 0x104 bytes. Fields we use:

| offset | meaning |
|---|---|
| +0x00 / +0x0c / +0x18 | position / rotation (degrees) / scale |
| +0x24 | **effect id** (what scripts ask for) |
| +0x28 | which leaf (recipe) to play |
| +0x30 | start time (skip into the effect) |
| +0x3c | projectile effect **bits** |
| +0x74 | frame to start at (for slot-bound rows) |
| +0x7c | flags (0x80 = don't auto-start) |
| +0x88 | **model name** — if set, the effect is attached to the fighter |
| +0xa8 | **bone name** to attach to (`root`, `hip`, `r_wep`…) |
| +0xc8 | motion slot name (auto-start when this slot plays) |

### Ways an effect starts

1. **By id** from a script: one-shot op **0x19** `[id]`, or main op 0x66. The game takes the
   **first FEPA row with that id**.
2. **From a projectile** (`magi` row +0x04). **Careful: this is a *bit number* into FEPA
   +0x3c — a different numbering than op 0x19.**
3. **Weapon trails:** main op 0x2a with ids 8888 / 9999.
4. **Automatically** when a motion starts, if the row's model name matches the fighter and its
   slot matches the motion. Sora's FEPA still says `p_sev100_1p`, so Cloud's slot-bound effects
   (Meteorain on `_705A` etc.) **don't** fire on Sora's KH2 moves. That's what we want.

**Lesson — two id spaces:** we first spawned "effect 5" with op 0x19, thinking it was Firaga's
explosion (because a Firaga *projectile* row said 5). In op-0x19 numbering, id 5 is
`DOGE_UKEMI` — Cloud's small air-recover whoosh at 0.4 size. Firaga's explosion is id **22**.
Tool `fep_dump.py ISO` lists every id → leaf, so check there.

---

## 6.2 Story: the effects clash (Cloud's effects vanished)

**Symptom (Mat, test 133, Cloud vs Sora):** Cloud's weapon trails, Meteorain's meteors, and
Climhazzard's effect sound didn't come out.

**Cause:** every FEP has a global **id** at +0x10. Sora's was a byte copy of Cloud's:
`0x311C0000`. The game's effect store accepts **one FEP per id**. The second fighter to load got
**no FEP at all**, so every effect of that fighter silently did nothing: trails, projectile
visuals, effects by id, and the effect sounds tied to them. In Mat's test, Cloud loaded second.

**Fix:** `tools/scripts/spot33_effects.py` gives Sora's FEP its own id `0x31280000` (3146 — the
free number between Tifa's 3145 and the FF8 fighters' 3153) and rewrites the 225 internal
references that contain it. Same size. Runs early in the build's effect steps.

### The second clash: resource keys

Inside a FEP, textures/meshes/flipbooks are registered by **key**. If a key is already
registered, the game **reuses the old one and ignores the new data**. Sora's FEP still used
Cloud's keys (`0x98011cNN`). Harmless while identical — but the moment we repaint a texture,
Cloud vs Sora would show Cloud's picture on Sora (or our KH2 orb on Cloud).
Fix: `spot33_fx.py` **rekeys** Sora's 229 key fields to `0x980128NN` first.

**Rule:** any copy-based fighter needs its own FEP id **and** its own resource keys.

---

## 6.3 The tools: reading and writing FEPs

| tool | job |
|---|---|
| `fep_dump.py` | read-only: every resource, leaf, node, FEPA row |
| `fep.py` | parser + writer; **round trip is byte-identical** for Sora's and Cloud's FEP |
| `fep_edit.py` | copy-on-write edits: rekey, import a KH2 or PNG texture, usage report |
| `fep_transplant.py` | copy a leaf tree from another fighter's FEP (used carefully, see 6.6) |
| `kh2_pax_dump.py` | read KH2's own effect files (PAX) and their textures |

The FEP is full of internal **offsets** (pointers written as "N bytes from the start"). The game
turns them into real addresses when it loads (`FUN_0894351c`). `fep.py` copies that function's
complete list of offset fields, so it can move things and keep every link right. Tested by
shifting everything by 4 bytes and re-reading: no unknown fields.

### KH2's side

KH2 effects are **PAX** files (in `P_EX100.a.us` for Sora's attacks, `magic/*.mag` for
spells). Inside: elements → effects → **DPD** particle data with textures, sprite shapes, meshes,
and a small **particle program** language (~240 instruction kinds: move, accelerate, spin, draw
sprite, spawn at mesh vertices, ribbon trail…). KH2 textures are PS2-style; they convert cleanly
to Dissidia's format (re-swizzle, palette order, alpha ×2). **[PROVEN]** our KH2 orb import
decoded back pixel-identical.

A full PAX → FEP converter would take weeks (stage C, not done). We use KH2 **textures and
colours** on Sora's **existing** recipes instead.

---

## 6.4 THE SIZE RULE: the effects chunk must never grow

**Story (2026-10-15, with Mat):**
1. Firaga's KH2 look (test167) **added** a new texture: +9.3 KB. Thundaga/Blizzaga added two more.
   Total +27.9 KB → `effe` 876,560 bytes instead of 848,640.
2. **Test171 froze PPSSPP on the very first Bravery attack.**
3. Bisect with Mat: the same disc with the old, Cloud-sized `effe` → **works**. Sound bank
   (508 KB) and model (2.499 MB) were not the cause.

**Cause:** the fighter's **effect memory budget**. A bigger FEP doesn't fit.

**Rule: Sora's `effe` chunk must stay exactly 848,640 bytes.** Never append a texture, mesh or
leaf. Instead, **overwrite slots Sora never draws**, at the same size. Every effect script now
asserts the size.

Which textures are free? We traced, motion by motion, which leaves Sora can still reach
(scripts, projectiles, slot-bound rows). Cloud's attacks Sora no longer uses (Blade Beam,
Cross-slash, Cloud's Fire) make their textures dead:

| texture | was (Cloud) | now |
|---|---|---|
| o0f 128×128 | Blade Beam flipbook | **KH2 fire** (`spot33_firefx.py`) |
| o12 128×64 | lava rock (Meteorain) | **lightning bolt** (`spot33_lightningfx.py`) |
| o09 128×64 | flames | **KH2 ice** (`spot33_magicfx.py`) |
| o14 | clouds (EX Burst smoke only) | KH2 light streak (Explosion swirl) |

Free/dead leaves are listed in `notes/kh2-effects.md` ("What Sora's FEP still needs").

---

## 6.5 Story: Explosion (orbs, flash, and invisible effects)

KH2's Explosion: Sora slams the Keyblade down; pink-white light **orbs with rings spiral out**
around him, then a burst.

- **Stage A:** the stand-in effect was id 5 = the wrong leaf (6.1). Switched to 22 as a control.
- **Stage B (test155–158):** found leaf 65 `CHOU_V5_TOSSIN_HIT`, an unused magic burst already
  made of global orb sprites and ring arcs. Recoloured it KH2 pink-white, swapped its swirl
  texture to a KH2 light streak, spawned it with op 0x19 id 68. **Mat (test157): "the sound is
  there but the effect is not."**
- **test160:** effect 68 *does* show, as faint blue lights. Mat: "Yes, that's what I want, KH2
  style, bigger." And the strike should be **bright white light**, not orange.
- **test182:** no effects at all. Cause: we set a node component to 280% thinking it was the
  sprite size. It was the **emitter's transform scale** — the orbs spawned ~4× further out,
  off camera. Lesson: test one field at a time.
- **test185:** white flash shows, but "away from the camera, a little behind". Cause: **an
  effect row is only attached to the fighter when its model name is set.** Our copied rows had
  empty names → placed in the world, not on Sora.
- **test188 (anchor fix):** rows get model `p_sev100_1p` + a bone. `hip` at (0,0,0) still
  showed nothing; `root` with y below 0 (in this space, negative y = up) works, like Cloud's own
  body effects. The flash goes on `r_wep` 1.0 along the blade = the Keyblade tip.
  **[PROVEN]** orbs around Sora + white flash.
- Mat: flash "a bit too bright" → 0.8 → 0.5.

---

## 6.6 Story: Lightning's thunder froze the game

Mat: Thundaga should look like thunder — "Lightning from FF13 has thunder, so you don't have to
look far."

- **test199/200:** copied Lightning's `THUNDER_BODY` tree (owner 31, `obj/p_gst130.objx`) into one
  of Sora's dead leaves, with her textures and flipbook. **Froze on the first Bravery swing.**
- **Bisect on test201:**
  - A — full transplant → **freeze**
  - B — her texture, meshes and flipbook only → OK
  - C — emptying two dead leaves only → OK
  - D — only her tree in Sora's leaf → **freeze**
- **Cause:** her nodes use **kinds Sora's FEP never has** (0x150 bolt mesh, 0xD0 arcs, 0x64).
  They seem to need code or tables only Lightning's setup provides. Also: putting her flipbook
  into Sora's ANM 10 froze **Explosion**, because ANM 10 is shared with a hit-mark leaf.
- **Rule: never transplant foreign effect trees or flipbooks.** Data inside Sora's own node
  kinds only.
- **Safe v3:** only her bolt **texture**, drawn by Cloud's own Blade Beam meshes. Mat: the wide
  curved mesh looked like a flat slab.
- **v4 (test210):** her bolt **mesh** data (a jagged forked strip, 198 vertices) written *into*
  Sora's own mesh slot 30, which a native node kind draws. Axes swapped so the long axis is the
  strike direction. Flash sprites → Lightning's global electric flipbooks.
  **[PROVEN]** test211: a thin white-blue bolt comes **straight down** onto the foe, then a big
  electric burst. No freeze.

---

## 6.7 Story: Blizzaga looked black and white

- First Blizzaga drew a one-shot hit flash as its "ball" → the ball flew invisible; only the
  hits showed ("shoots out nothing, a blow-up on the ground").
- Then the ball used the meteor's body mesh with KH2's ice crystal **sprite sheet**. The mesh maps
  the whole sheet → mostly empty and grey → "all black, and kind of white".
- Fix: KH2's ice **surface** texture, coloured to ice blues → white. **Mat: "perfect".**

---

## 6.8 Story: Firaga — fireballs that never left

Mat wanted KH2 Firaga: fire **swirling around Sora**, then flying out and gone.

- **test206:** 8 fireballs placed on a spiral by FEPA rows. Mat: "the balls of fire are around
  him and **don't leave**."
- **Cause:** the fireball leaf's tree header says `2` = **LOOP**. A fireball normally dies when its
  projectile dies. Spawned by op 0x19 there is no projectile to kill it → each one burned forever.
- **test210:** `LOOP_OFF` (2 → 0). Two "comets" 180° apart race round Sora, then a ring flies out.
- **test211:** too small and dark, and Cloud's big orange smoky end explosion hid everything.
- **test213/214:** bigger (×1.6), higher (1.3 m), bright flame colours, no Cloud end burst.
  **[PROVEN]** bright fire all around Sora through the cast, nothing lingers, no freeze.
  **[OPEN]** Mat still to judge if it reads as KH2.

---

## 6.9 EX Burst background (built, not judged)

Mat: "the limit background is very FF7 pink, make it KH2 themed." `spot33_burstfx.py` recolours
the burst's aura, cloud dome and flashes from FF7 warm/pink/violet to KH2 night blues,
moonlight white and white-gold, all size-neutral. **[BUILT, not seen in game yet]**
The pink "LIMIT BREAK" banner box is the shared battle HUD, not Sora's file.

---

## 6.10 Rules, collected

1. `effe` stays **exactly 848,640 bytes**.
2. Never touch global textures (`0xF00000NN`).
3. Own FEP id, own resource keys (rekey before any texture edit).
4. No foreign trees or flipbooks. Reuse dead leaves and slots.
5. Op-0x19 ids ≠ projectile effect bits. Check with `fep_dump.py`.
6. Attach rows with a model name + bone; `root` with negative y = up.
7. Persistent leaves loop; spawned by id they must be set to play once.
8. Change one thing per test.
9. Every effect script is **re-runnable**: a second run prints "nothing to do".

---

## 6.11 Where to look

- `notes/kh2-effects.md` — everything, in order (long; bottom = newest).
- `notes/effects-clash.md` — the FEP id clash.
- `notes/hitbox-shapes.md` §5 — FEPA basics.
- `tools/scripts/fep*.py`, `spot33_effects.py`, `spot33_fx.py`, `spot33_firefx.py`,
  `spot33_magicfx.py`, `spot33_lightningfx.py`, `spot33_burstfx.py`, `kh2_pax_dump.py`.
- Pictures: `dumps/renders/kh2fx/`.

## 2026-10-16: three effect-file rules (break one = freeze or invisible)

1. **Alignment:** every blob keeps its file offset mod 16; node init blocks sit at 12 mod 16 (read with `lv.q`).
2. **Serials:** node serial numbers run 0..N-1 over the whole file, no gaps, no repeats.
3. **Key blocks draw:** a node draws from its key-frame blocks (node +0x24), key 0 = all settings; editing only the
   start-value block changes nothing on screen.
`spot33_magnet.py` (`align_layout`, `renumber_serials`) does all three; `spot33_barrier.py` now fixes key 0 too.
Magnet Burst = KH2FM P_EX100 swirl + Magnega band (`notes/kh2-effects.md` "Magnet Burst").

Next: [Chapter 7 — Game code](07-game-code.md).
