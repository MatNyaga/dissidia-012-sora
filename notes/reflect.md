# Reflect — Sora's EX Mode special (research 2026-10-15)

Mat: "in EX Mode his block becomes Reflect, which reflects all damage back at the attacker" — and: "it reflects
everything in KH2" (Bravery AND HP attacks, melee AND projectiles/magic). Script: `tools/scripts/spot33_reflect.py`.
**NEW (2026-10-16, §11): test221 = full Reflect redesign** (melee/HP via a fresh hit in the game's direct-hit queue with atkp source = attacker, owner = Sora; projectiles deflected AT the caster, also "unreflectable" ones). Static only — phase 2 (in game) pending.
**IN-GAME RESULT (2026-10-15, §10): damage is NOT returned yet.** Hook 2 (melee damage return) is switched OFF
(`MELEE_REFLECT = False`) because it moved no damage and once froze the game. What works: EX guard can't be broken by
HP attacks, EX guard blocks every projectile; normal guard unchanged; no crash; win → menus OK.

**Implemented (Mat: FULL strength, reflects everything, EX Mode only): `dumps/ULUS10566-test184-reflect.iso`** =
test179-oldfx + `spot33_reflect.py --apply-code` (code hooks + data part). Static checks only — not run in game yet.
(test173 = an older data-only prototype on test166.)

## 1. How Dissidia's guard works (EBOOT + battle overlay, dumps/decomp/all.c)

- Sora's guard = motion **470** (ground, p_se block 20) / **471** (air, block 21). Script: op 0x00 hitbox
  **GUARD 0x30A** (atkp kind **4**) frames 0–36, op 0x45 frames 0–4, op 0x22 / 0x1e / 0x02 / 0x15 plumbing.
  `FUN_08837360(f)` = "guarding" = motion id 0x1d6/0x1d7 (470/471).
- **Hit vs hit clash** = `FUN_08809f00(?, B = fighter whose hit is touched, entry)` (EBOOT). Registers (Ghidra
  listing): `fp` = A's hit record (the incoming hit), `s7` = B's hit record, `s3` = B fighter (also at
  `sp+0x200` = local_40; `s3` is reused as B's outcome from 0x0880a3b4), `s5` = A fighter, `s1`/`s0` = A/B hit
  kinds (atkp +4), contact data at `sp+0x208` (local_38), entry at `sp+0x204`.
- Outcome = 16×16 table at EBOOT `0x089d4978` (`FUN_0884a454(myKind, otherKind)`). Guard rows:
  `kind 4` (guard): vs 0 (melee Bravery) → **3** (repel; attacker gets 1 = recoil), vs 2/3 (HP) → **4** (guard crushed).
  `kind 12` (special guard): **3 vs every attack kind** (cannot be crushed).
- `FUN_0884a53c(myHit, otherHit, outcome)` applies it: 1/2 = push/recoil (reaction byte = the OTHER hit's atkp +5),
  3 = guard success flags (fighter+0x384 |= 0x10040000), 4 = guard crushed (the clash code then calls
  `FUN_08808ee4(entry, guarder, contact, 0)` = **the normal "hit lands on fighter" function** → damage).
- **Built-in special guard** (0x0880a2c4–0x0880a380): if B's kind is 4, B is guarding, B has general-ability
  effect **0x40** (`FUN_088bf4cc(abilities, 0x40)`) and fighter+0x195 bit **0x20** (op 0x45 window, guard frames 0–4)
  and not +0x198 bit 8 → kind 12 + hit +0x10 |= 0x200 + `FUN_08b34f9c` (a slow-motion flash). = a "just guard".
  Effect 0x40 is that just-guard ability, not a damage return.
- **Blocking does NOT damage the attacker** anywhere (melee): outcome 1 only pushes him. GUARD_REF (0x349, kind 7,
  power 5) is never referenced by id in code; kind 7 behaves like "always wins" in the table. Not used by guards.

## 2. Projectiles: Dissidia already has a REFLECT

- Projectile vs hit = `FUN_08ada0a4` (battle overlay): outcome from per-projectile-kind tables
  (`FUN_08adb330`: kind 3 HP magic `0x08adba84`, 7 `0x08adbb04`, 8 `0x08adbac4`, 10, 11). Vs guard 4 / 12:
  kind 3 (HP magic) **4 / 0**, kind 8 **3 / 0**, kind 7 (Bravery magic) **0 / 0**.
- `FUN_08adaa68(proj, outcome, guarder, reflectBit, …)`: outcome 3 (and 0/1/2 with conditions) → `FUN_08ada640`
  → **`FUN_08ada2f8`** = deflect: the projectile changes side and flies off. With **reflectBit** = guarder
  fighter+0x195 bit 0x20 **or 0x40**, it is aimed **at the guarder's opponent** (= sent back to the caster); without
  it, it flies off in a random direction. Magi row data +2 (u16, via row +0x24) ≠ 0 = "can't be reflected".
- A projectile's hit record keeps the atkp row of the caster (resolved at creation, `FUN_08807860`), so a reflected
  projectile hits its caster with **his own spell's damage** = real damage return.
- fighter+0x195 bits are set by script ops (dispatcher `FUN_08829930`, flags struct = fighter+0x130):
  **op 0x45** ('E') → bit 0x20 (+ param≠0 → +0x198 bit 8); **op 0x46** ('F') → bit **0x40**, no params.

## 3. EX Mode

- In EX Mode: `FUN_08b34378(f)` = (fighter+0x5b2 & 4) && chrp row (+0x5a4) && not EX-Burst (`FUN_08b3406c`).
- EX Mode bonuses = bits of chrp row +0x0C (fighter+0x5a4 → +0xc), one predicate each: 1 (Bravery scaling),
  4, 0x20, 0x40, 0x80, 0x100 (drain from Bravery dealt, `FUN_08842d18`), 0x200, 0x400, 0x20000, 0x40000, 0x80000.
  **None returns damage** → Reflect needs new behaviour.
- **Script events can be EX-only by data**: main-event condition byte 1 (event +7) = **mode**: 0 any, 1 normal,
  **2 = EX Mode**, 4/5/6 special (matcher `FUN_08828eec`; mode from `FUN_0882f30c` / one-shots `FUN_0882f17c`).
  Byte 0 (+6) = the motion's type-7 variant.
- Status struct `*(fighter+0x52C)`: +0 level, +8 HP damage taken, +0xC max HP (HP = +0xC − +8), **+0x14 Bravery**
  (short, 0–9999), +0x16 base Bravery, +0x18 EX gauge (float), +0x1C assist gauge, +0x28 flags.
  Owner number = byte *(*(fighter+0x2F8)+6).

## 4. Design ("reflects everything")

| part | covers | how | status |
|---|---|---|---|
| A data | Bravery-type projectiles | op 0x46 frames 0–36, cond byte1 = 2 (EX only), in guard blocks 20/21 | **built (test173)** |
| B code hook 1 | HP melee no longer crushes his guard | EX Sora's guard kind 4 → 12 before the outcome lookup | assembled, not applied |
| C code hook 2 | melee Bravery + HP damage returned | on guard success apply the attacker's own hit to the attacker | assembled, not applied |
| D code hook 3 | HP magic / every projectile kind | projectile vs EX Sora's guard → outcome 3 (reflect) | assembled, not applied |
| E look | KH2 Reflect barrier + sounds | EX-only one-shots (op 0x19 effect, op 0x03 sound) in the guard blocks | todo |

**Hook 2 detail (EBOOT 0x0880a410, after both `FUN_0884a53c` calls):** if B's outcome (s3) = 3 and B (sp+0x200) is
Sora in EX Mode: A = hit owner `*(fp+0x18)`; set the hit's owner to **Sora for Bravery hits** (Sora gains what A
loses) or keep **A for HP hits** (atkp +0x08 & 0x10: A's own Bravery becomes HP damage to A and resets, exactly as
if A were hit by his own HP attack; with Sora as owner it would spend Sora's Bravery instead); call
`FUN_08808ee4(&hit, A, contact = sp+0x208, 0)`; restore the owner. Runs after A's recoil, so the hit reaction wins.

**Code (spot33_reflect.py `--code-plan`)**: shared `IS_SORA_EX` (owner 33 + `FUN_08b34378`), hooks
`0x0880a384` (2 words: the first becomes `j C1`, the original first word moves into the delay slot), `0x0880a410`
(2 words: the game's branch pair becomes `j C2` / `nop`; C2 runs the replaced pair at its end), `0x08ada22c` (the
game's call becomes `jal C3`). No branch lands in the replaced pairs.
**Total 75 words = 300 bytes.**

### Where the code can live (open)
- EBOOT gap **0x089DD3C0–0x089DD4C0 (256 B)**: between the EBOOT's data end and the battle overlay; outside the
  loaded segment today → needs program header 0 FileSiz/MemSiz 0x1D9380 → 0x1D9480 (file bytes 0x1DA398.. are
  zero padding up to the second segment at 0x1DB000). Too small by 44 bytes.
- Battle overlay tail **0x08B62F70–0x08B63170 (512 B)**: between the battle overlay's end and the EBOOT's second
  segment. Needs OVL_BATTLE_APP.ELF's PROGBITS/phdr grown by up to 0x200 (the file's last ISO sector has ~0x468 B
  slack, but the section headers + shstrtab sit right after the data and must move). All three hooks only run in
  battle, so they may live there.
- Recommended: SUB + hooks 1/2 (53 words) in the EBOOT gap, hook 3 (21 words) in the overlay tail — or shrink.
- Unknown: whether anything writes the EBOOT gap / overlay tail at runtime (no reference found). Boot test first.

### Risks
- `FUN_08808ee4` with owner = victim (HP case) may be refused by the hit object's vtable +0x34 → fallback: owner =
  Sora + restore Sora's Bravery afterwards (+0x14 of his status) — 4 more instructions.
- Multi-hit moves: each hit that touches the guard is reflected (fits "reflects everything").
- The CPU still attacks into the guard (it doesn't know about Reflect) — good for testing, maybe too strong; tune
  with Mat (e.g. only Bravery, or ×0.5).
- Cloud vs Sora: everything is gated by owner 33 + EX Mode; the data part is in Sora's own file only.
- Projectiles marked unreflectable (magi row data +2 ≠ 0) are still only blocked, unless hook 3 is extended.

## 5. KH2 side
- Animations (P_EX100.mset): **164 REFLECT** (A320, 30 f), **172 REFLECT_AIR** (A350, 20 f), 284 MAGIC_REFLECT
  (40 f), 288 MAGIC_REFLECT_FINISH (50 f). Sora's guard slot _160A is KH2 168 AUTOGUARD 0–16 today.
- Effect: `kh2_export/raw/kh2_fifth/original/magic/REFLECT_3.mag` (Reflega, PAX "reflect3": 17 elements, 9 effects,
  1 DPD). Textures → `dumps/renders/kh2reflect/dpd0_tex*.png` (light streak, cyan-white barrier-panel gradient,
  ring flashes; the hexagon is a DPD model).
- Sounds (se000): **177** barrier up (1.93 s), **139** barrier hum (1.47 s), **178** hit on the barrier (2.02 s),
  **173** burst (0.94 s) → `dumps/renders/kh2reflect/se_<id>.wav`.

## 6. Test plan (needs the game)
1. Boot test173, Sora vs CPU Cloud (projectiles: Cloud's Fire = Bravery magic, kind 7/8). Fill Sora's EX gauge
   (float at *(fighter+0x52C)+0x18 = 10000), R+□ → EX Mode, guard (R) while Cloud casts Fire/Blizzard:
   expect the ball to fly back and hit Cloud (his Bravery drops, Sora's not). Without EX Mode: normal block.
2. Log with ppbpwatch on `0x08ada2f8` (deflect) and `0x08ada640` to see the reflect calls.
3. Code hooks (after placement is decided): boot test → menu → battle (crash = cave memory in use). Then EX Sora
   guards Cloud's ◯ combo (Bravery: Cloud's Bravery → Sora), Cross-slash / Braver (HP: guard holds, Cloud loses HP),
   Meteorain (HP magic: rocks fly back). Watch for double hits, hangs, wrong owners (Bravery numbers).
4. Mat decides: strength (full / half), Bravery-only vs HP too (they said both), CPU fairness.

## 7. Implementation (2026-10-15, test184)

**Code placement (final):** all hook code (shared check + hooks 1/2/3, 80 words = 320 B) is APPENDED to the battle
overlay at **0x08B62F70–0x08B630B0**. Why not the EBOOT gap: the overlay loader `FUN_089331fc` reads
`p_offset + p_filesz` bytes of the overlay file to `p_vaddr - p_offset`, i.e. the overlay's 0x54-byte ELF header lands
at **0x089DD46C–0x089DD4C0 inside the EBOOT gap** on every overlay load (only 172 B of that gap would be safe).
Safety of 0x08B62F70–0x08B63170 (between the battle overlay's end and the EBOOT's second LOAD segment):
- no data word and no `lui/addiu`-style address pair in EBOOT / battle / menu / extra overlays points into it
  (only the EBOOT's own section-header table, which is not loaded, names 0x08B62F70 as an empty NOBITS marker)
- the EBOOT's BSS (section 23, NOBITS) starts at 0x08B63280 — no overlap; the overlay has no BSS (filesz = memsz)
- the loader has no size cap; the new overlay load range 0x089DD4C0–0x08B630B0 ends 0xC0 below 0x08B63170
- all three hooks run only in battle (hit clash / projectile code), i.e. only while the battle overlay is loaded
- on disc the overlay keeps its 780 sectors (1,596,632 B ≤ 1,597,440; 4 more spare sectors before OVL_EXTRA)
- the EBOOT's program headers are NOT changed (no segment growth needed)

**Disc changes (whole-ISO sector diff vs test179):** sector 27 (DATA directory record: overlay size 1,596,312 →
1,596,632, LE + BE), 574 (EBOOT: 4 words at 0x0880A384/88 and 0x0880A410/14), 185824 (overlay ELF header: e_shoff),
186329 (overlay word at 0x08ADA22C), 186603 (overlay tail: cave + moved shstrtab + section headers), 26053 +
872028–872780 (PACKAGE_INFO + Sora's objx: guard blocks 20/21 +12 B each). **Sora's effe chunk: 848,640 B (unchanged).**
readelf on the new overlay: LOAD filesz/memsz 0x185BF0, section 1 size 0x185BF0, shstrtab at 0x185C44, e_shoff
0x185C60 — all consistent; inside the original code only the hook word changed. Re-running changes nothing.

**Hook details as built** (`spot33_reflect.py --code-plan` prints the addresses):
- `IS_SORA_EX` 0x08B62F70: owner byte *(*(f+0x2F8)+6) == 33, then tail-jumps to `FUN_08b34378` (EX Mode test).
- hook 1 site 0x0880A384 (`j C1`, the original first word kept in the delay slot): B's kind (s0) 4 + IS_SORA_EX(B = s3) → s0 = 12.
- hook 2 site 0x0880A410 `j C2 / nop`: B outcome (s3) == 3, B's touched hit (s7) is a GUARD (atkp kind 4),
  IS_SORA_EX(B = sp+0x200): owner of A's hit (fp+0x18) := Sora unless A's atkp +0x08 has flag 0x10 (HP hit),
  `FUN_08808ee4(&hit, A, contact sp+0x208, 0)`, owner restored; then the two original words it replaced.
- hook 3 site 0x08ADA22C `jal C3`: if the touched fighter (*( *(s0+0x100)+0x1C)) is Sora in EX Mode and his touched
  hit kind is 4 or 12 → outcome 3 (deflect: `FUN_08adaa68` → `FUN_08ada640` → `FUN_08ada2f8` makes the projectile
  Sora's (+0x68 owner) with target +0x6C = his target) for every projectile kind; else the original `FUN_08adb330`.
- data part (op 0x46, EX only, guard frames 0–36) is in too, but it is REDUNDANT with hook 3: re-reading
  `FUN_08adaa68` argument by argument, the +0x195 bits only stop the outcome-0/1 → deflect conversion; with hook 3
  forcing outcome 3 they don't matter. Kept because it is harmless (only during EX guards). Can be dropped.

**Open questions only the game can answer:** does a deflected projectile fly back AT the caster (homing on the new
target) or bounce off randomly; does `FUN_08808ee4` accept owner == victim (HP case; fallback: owner = Sora and
restore his Bravery — 4 instructions); multi-hit moves reflect every hit; does the CPU keep attacking into the guard.

## 8. KH2 Reflect look (described, NOT built — effe must stay 848,640 B; build_sora.sh untouched)
- **Animation:** guard = motion 470 → p_se block 20 → GMO slot **_160A** (ground, today KH2 168 AUTOGUARD 0–16) and
  471 → block 21 → **_161A** (air, already KH2 **172 REFLECT_AIR**). Ground → KH2 **164 REFLECT**: build_sora.sh MOVES
  `_160A=168:0-16` → `_160A=164` (30 anim frames = 60 script frames ≥ the guard window 0–36 / op22 at 38). Applies to
  every guard, not only EX (both modes share motion 470; an EX-only pose would need its own motion id — not found).
  KH2 164 is KH2's normal guard anyway (notes/kh2-finishers.md), so it fits both.
- **EX-only barrier effect:** a one-shot `op 0x19 [effect id, 0]` at frame 0 of blocks 20/21 with one-shot condition
  bytes `[00 02 00 00]` (one-shot cond +5 = mode, 2 = EX Mode; matcher `FUN_08829104`). Size-neutral effect idea:
  recolour an unused leaf of Sora's FEP into Reflega's cyan-white (KH2 textures dumps/renders/kh2reflect/dpd0_tex1 =
  barrier panel gradient, tex2 = ring flashes) — same size, existing TEX slot replaced in place, a FEPA row copied
  like spot33_fx did for Explosion. Hand to the effects helper (it owns effe; test182 in progress).
- **EX-only sounds:** one-shot `op 0x03 [snd id, 0, 0]` with the same EX condition: se 177 barrier up at frame 0
  (dumps/renders/kh2reflect/se_177.wav, 1.93 s → trim ~1.2 s), and se 178 on each reflected hit — the latter would
  need hook 2/3 to play a sound (not built). New snd_ slots (81/82) via spot33_sfx.py (owner: main session).

## 9. Test steps (test184)
1. Boot test184 → title → Quick Battle (game must boot: the overlay grew — a crash/black screen here = loader issue).
2. Sora vs CPU **Cloud**, normal mode: guard Cloud's combo → normal block (no reflect). Cloud's Fire → normal.
3. Fill Sora's EX gauge (*(fighter+0x52C)+0x18 = 10000.0) → R+□ EX Mode → guard (R):
   a. Cloud's ◯ combo (Bravery melee): Cloud flinches/takes the hit, **Cloud's Bravery drops, Sora's rises** by the hit.
   b. Cloud's Cross-slash / Braver (HP melee): Sora's guard **holds** (not crushed); **Cloud loses HP** = his own Bravery,
      his Bravery resets. If nothing happens here: owner==victim refused → apply the fallback.
   c. Cloud's Fire / Fira (Bravery magic) and Meteorain (HP magic): projectiles bounce off Sora's guard and should fly
      back at Cloud and hit him (watch: random direction instead = needs aiming code).
4. Logs: ppbpwatch on 0x08B62FC4 (C2), 0x08B63048+ (C3), 0x08808ee4 and 0x08ada2f8; HUD Bravery/HP numbers.
5. Cloud vs Sora with Sora NOT in EX, and Cloud in EX guarding Sora: no reflect for anyone but EX Sora.
6. Regression: a normal battle start → win → menus (overlay switch battle ↔ menu still fine).

**Build line** (after `spot33_magic.py`/`spot33_exmode.py`, any place after the p_se blocks exist; the code part only
needs the EBOOT/overlay, so it may also run last):
```
    python3 -I $S/spot33_reflect.py "$2" --apply-code                                # EX Mode Reflect (notes/reflect.md)
```

## 10. In-game test of test184 (2026-10-15; PPSSPP, vs CPU Cloud and CPU Lightning, owner 31)

Driver: scratchpad `ppreflect.py` (one debugger connection; guard spam R facing the foe, keeps both alive, pausing
breakpoints on the cave + FUN_08ada2f8 / FUN_08adaa68 / FUN_08808ee4 exits; breakpoints are handled only after each
request's reply — handling them mid-request swallowed replies and stalled the driver once).

| check | result |
|---|---|
| boots, battle starts (overlay grew) | ✅ boots, quick battles start, rematches and new battles reload the overlay fine |
| normal guard outside EX | ✅ hooks gated: C1 never fires, C3 falls through (original outcome); a normal deflect still happens |
| EX guard vs HP attack | ✅ guard holds (C1 → kind 12; Lightning HP attacks 10074/10071 → she recoils 911, Sora loses no HP) — ❌ no damage back |
| EX guard vs melee (Bravery) | ❌ no damage back. Hook 2 call `FUN_08808ee4(attacker's hit → attacker)`: (a) `+0x18` swapped only: hit landed (Cloud hurt motion 551) but no Bravery moved — `+0x14` (credited fighter) was still Cloud = "Cloud hits Cloud"; (b) `+0x14` and `+0x18` swapped: refused by the victim-state check `FUN_088377d0` (attacker is mid-swing: fighter+0x190 bits 0x20/0x40) → early exit 0x08808ffc for every melee swing; (c) one kind-7 magic hit (Lightning atkp 0x7ee) passed that check and **HUNG the game** (endless loop, 94% CPU, debugger dead) |
| EX guard vs projectile | ⚠️ blocked (hook 3 forces outcome 3 for every kind: 89× in the last run; Sora takes nothing) but **not sent back**: `FUN_08adaa68` deflects only projectiles whose magi row +2 == 0 — Lightning's (kind 7/8) aren't; the few that deflect (Cloud's orb, 3× Lightning) fly off in a random direction (`FUN_08ada640` random matrix) and hit nobody |
| no freeze / crash | ✅ with hook 2 OFF (≈4 min of EX guarding, 2 battles); ❌ with hook 2 ON (1 freeze) |
| win → menus | ✅ forced win (foe at 1 HP): win pose 1200, results, next battle loads |

Clips: dumps/screens/reflect_t184_exguard.mp4 (EX guard: deflect, guarded HP attack, deflect; log time ≈ video + 41 s),
full runs rec_20261015-093910.mp4 (final build, vs Lightning), rec_20261015-091806.mp4 (vs Cloud, hook 2 v1),
rec_20261015-092822.mp4 (vs Lightning, hook 2 v2 incl. the freeze at the end).

**Current test184 = hook 1 + hook 3 + data part; hook 2 off** (cave 42 words 0x08B62F70–0x08B63020, ≤ 0x08B63100).

### What a working "reflects everything" needs (next design)
- **Melee/HP damage**: don't re-run the attacker's hit. Instead apply the damage directly at guard success: e.g. at
  hook 2's place, compute the Bravery damage the game would have dealt (the battle damage path FUN_08ae2af8 /
  FUN_08ae975c builds attacker/defender Bravery from the hit) and call that path with attacker/defender swapped, or
  queue a damage event with Sora as attacker and the foe as defender. Find how FUN_08807e6c → owner vt+0x1b4 builds the
  battle damage event, and build one ourselves (no hit-list / victim-state checks). For HP hits: HP damage = foe's
  own Bravery. Must be tested in game; the hang in (c) shows the hit pipeline isn't safe to re-enter.
- **Projectiles**: in FUN_08adaa68 case 3, skip the "magi row +2 == 0" check for EX Sora, and aim the deflect at the
  caster (FUN_08ada2f8 gets a random matrix from FUN_08ada640 — call FUN_08ada2f8 with a matrix toward the foe, or the
  branch of FUN_08adaa68 taken when its fourth argument is 1, which targets the guarder's target).

## 11. test221 design: reflect by a FRESH hit + aimed projectile deflect (2026-10-16, static; not run in game yet)

Disc: **`dumps/ULUS10566-test221-reflect.iso`** = test219-exsnd + `spot33_reflect.py --apply-code` (new code). Switches
in the script: `MELEE_REFLECT` (part 1), `PROJ_AIM` (part 2), `PROJ_ALL` (part 2 also for "unreflectable" projectiles).
All off = byte-identical cave to test219 (224 B). All on = **496 B** (124 words) at 0x08B62F70..0x08B63160 (room
0x08B63170); `PROJ_ALL = False` = 512 B exactly. The old 0x08B63100 Reflect/EX-audio split is gone (EX_SND lives here).

### 11.1 How the game itself applies damage (found statically)
- **Hit object** `FUN_08807860(hit, src, owner, id, grp)`: +0x14 credited = +0x18 owner = `owner`, **+0x20 = `src`**
  (atkp source), +0x24 id (short), +0x34 atkp row = `FUN_08837f14(src, id)` (src's own table at fighter+0x49c, binary
  search of 0x44-byte rows, fallback global table). So owner and atkp source are separate parameters.
- **Result** `FUN_088131bc` (pool of 4 at 0x089D47D8): +0x20 credited, +0x24 victim, +0x2c hit, +0x30 atkp, +0x38 HP
  damage. **HP damage = `FUN_08813510(hit+0x20 = source)` = the SOURCE's Bravery** (+ credited's Bravery if he has
  ability 0xfb). HP flag = atkp +8 & 2 (`FUN_088132bc`).
- **Landing** `FUN_08807e6c(hit, victim, atkp, 0, flag)` → owner vt+0x1b4 = `FUN_08b33938` → `FUN_08838734` records the hit
  into the owner's dealt list (fighter+0x534, 6×0x40, `FUN_088393f4`) and the victim's taken list (`FUN_088394b8`);
  record +0x20 atkp, +0x24 owner, +0x28 **source**, +0x2c victim, +0x30 HP damage. Then victim vt+0x74 = `FUN_08b2de00`
  → `FUN_0883a150` (reaction; HP damage via `FUN_08831ea8`).
- **Bravery** is moved later by the OWNER's battle state: `FUN_08ae45b8` reads the dealt records (Bravery hits only) and
  calls `FUN_08ae6d2c(state, ev, dmg)`: owner's Bravery += dmg, his opponent's −= dmg (power = atkp +0x10, owner's
  attack vt+0x174 vs victim's defence vt+0x17c, `FUN_08b34244` multiplier).
- **HP hits** are handled by `FUN_08ae5bc8` (same state, records with atkp +8 & 2): if record **source == owner** → the
  owner's state goes to state 1 (`FUN_08ae1270(state,1)` = after-HP-attack, Bravery reset); **if source != owner →
  the OPPONENT's state** gets +0x240 = 1 and state 1 instead (`FUN_08ae137c` then reads the opponent's records). The
  game has a built-in "reflected HP attack" case.
- **Projectiles already use it:** after a deflect (`FUN_08ada2f8`: +0x104 = 1, +0x68 owner = deflecter, +0x6c = his
  target, +0x78 timer 0, old hit dropped by `FUN_08ada06c`, +0x106 = 0) the next hit is built by `FUN_08ad9ce4` →
  `FUN_0880b05c(hit, magi+0x108 = caster (src), proj+0x68 = deflecter (owner), id)` (id = magi row +0xc when vt+0x64
  says "reflected", else +0xa). So a deflected projectile hitting its caster = source caster, owner deflecter.
- **Direct-hit queue** `FUN_08808468(attacker, id, victim, dir*, 1)` (32 slots at 0x09AF84F0; used by EX Bursts and
  script op 8) → next hit update `FUN_08807538` → `FUN_088076d4` → `FUN_08808ae8`: fresh hit `FUN_08807860(hit, attacker,
  attacker, id, -1)` → `FUN_08807e6c` (flag 1) → effects `FUN_08808748` → victim reaction vt+0x74 → `FUN_08813180`,
  `FUN_08808214`. Only victim check: `FUN_088378c4` (+0x190 bit 0x40 = script op 0x55 window). No clash, no
  `FUN_088377d0` (the +0x190 bit 0x20/0x40 check that refused test184's hook 2; bit 0x20 = script op 0x06).
- Hit classes: base 0x089C6C40 (direct hits), 0x089C6CA8 (`FUN_0880b05c`, projectiles, +0x2c = 0), 0x089C6CE0
  (`FUN_0880b768`), **0x089C6D18 = fighter hitboxes** (`FUN_0880b8e4` from `FUN_0883e108`, +0x2c = 1, +0x80 = shape).
  Projectile hits DO go through the melee clash `FUN_08809f00` (it sets their +0x10 bit 8; `FUN_08ada0a4` reacts).
- fighter+0x384 bit 0x20 = "clashed this frame" (set by `FUN_0884a53c`, which applies only the first clash per
  frame; cleared every frame unless the motion is 900–911 = recoil).
- Atkp ids: max **0xD1B** over all 139 atkp tables on the disc → bit 0x4000 is free as a marker.

### 11.2 Rules (decided; write-up for Mat)
- **Bravery attack guarded in EX Mode:** the attacker is hit by his own move, credited to Sora: **Sora gains and the
  attacker loses** the Bravery damage of that move (computed with Sora as attacker: the attacker's move power, Sora's
  attack vs the attacker's defence, Sora's EX multiplier). The attacker can be Bravery-broken this way.
- **HP attack guarded in EX Mode:** the guard holds (hook 1) and the attacker takes **HP damage = his own Bravery**, then
  his Bravery resets (as after his own HP attack). Sora's Bravery is not spent. = "hit by his own HP attack".
- **Projectile / magic:** flies back **at the caster** (owner = Sora); on contact the caster takes his own spell's damage
  by the same two rules (Bravery spell → Bravery transfer to Sora; HP spell → HP damage = caster's Bravery).
- Every guarded hit is reflected (multi-hit moves: each hit). Only EX Mode Sora (owner 33), only his guard (motion
  470/471 GUARD hitbox, atkp kind 4), only attackers that are main fighters (not assists / summons — v1 limit).

### 11.3 Code (spot33_reflect.py; `--code-plan` prints the addresses)
| part | site (what changes) | cave |
|---|---|---|
| hook 1 (unchanged) | EBOOT 0x0880A384: 2 words → `j C1` + the original first word in the delay slot | C1 0x08B62F9C |
| **C2** melee/HP | EBOOT **0x0880A408**: the call to `FUN_0884a53c` → `jal C2` (delay slot unchanged) | 0x08B62FC4 |
| **C4** | EBOOT **0x08808B74**: the call to `FUN_08807860` → `jal C4` (delay slot unchanged) | 0x08B6306C |
| hook 3 | overlay 0x08ADA22C: the call to `FUN_08adb330` → `jal C3` (EX Sora's guard → outcome **7**) | C3 0x08B6307C |
| **C7** projectiles | overlay **0x08ADAAAC**: the outcome bound check 7 → 8 (one more case); **0x08ADB32C** jump-table padding 0 → C7 | 0x08B630D0 |
| EX_SND (unchanged) | 0x08A3A15C / 0x08A3A374 | 0x08B63128 |
| old hook 2 | 0x0880A410 stays original (retired) | — |

- **C2** (runs before the defender's own clash apply; fp = attacker's hit, s7 = touched hit, s3 = defender outcome,
  sp+0x200 = defender): outcome 3 && fp+0x2c == 1 (melee hitbox, not a projectile) && touched atkp kind 4 &&
  owner(fp+0x18) == source(fp+0x20) && owner+0x542 == 0 && defender+0x384 bit 0x20 clear && IS_SORA_EX(defender) →
  `FUN_08836dac(Sora, A, dir)`, `FUN_08808468(Sora, id | 0x4000, A, dir, 1)`; then tail-jumps to the original
  `FUN_0884a53c(s7, fp, s3)` with ra restored. No re-entry into the hit pipeline inside the clash.
- **C4** (4 words): `andi t1,a3,0x4000 / movn a1,s2,t1 / j 0x08807860 / xor a3,a3,t1` → marked ids get src = victim.
- **C7** (inside FUN_08adaa68's frame, s0 = projectile, a0 = guarder): `FUN_089a38e0(buf, caster+0x80, Sora+0x80)`,
  `FUN_089a3bc8(buf, buf)` (normalise xyz), w = 0, `FUN_08ada2f8(proj, Sora, buf, -, t0 = 1, t1 = 0, t2 = 0)`, exit
  through the epilogue 0x08ADAD38 with v0 = 1 (the normal "deflected" return). Caster 0 → 0x08ADAD34 (return 3). With
  `PROJ_ALL = False` C7 first checks magi row +2 like case 3 (unreflectable → blocked as in test219).
- Why outcome 7 and not a deflect inside C3: after `FUN_08ada2f8` the projectile's hit is gone (+0x100 = 0) and
  FUN_08ada0a4 dereferences +0x100 right after the C3 call → crash. The vt+0x2c call is the last use. No vanilla
  table produces 7 (the five tables hold 0–6 / −1), so only C3 reaches C7.
- mips_asm.py: added `movn`/`movz` and `.word X` (label or number).
- apply: all sites are checked before any write; a switch turned off restores its sites (tested on a sparse copy:
  on → off → on round-trips byte-identical; re-run = no change). Disc diff vs test219: sectors 27, 571, 574, 185824,
  186009, 186329–186331, 186603 (dir record, EBOOT 2 sites, overlay header + 4 sites + cave). readelf: LOAD
  filesz/memsz 0x185CA0 (ends 0x08B63160), file 1,596,808 B ≤ 780 sectors.

### 11.4 Risks / what phase 2 must check
1. **Victim window:** `FUN_08808ae8` drops the queued hit if the attacker has +0x190 bit 0x40 (script op 0x55) on the
   next frame. Expect most swings to be interrupted by the repel (outcome 1 → recoil 900–911) first; HP attacks with
   long invulnerability may be dropped silently (no hang). Log: bp 0x08808B74 (C4 reached) vs 0x08807e6c.
2. **Bravery numbers:** static reading says Sora gains / attacker loses; verify HUD (Bravery = *(f+0x52C)+0x14).
3. **HP rule:** attacker HP −= his Bravery, his Bravery → 0 (state 1 of HIS battle state); Sora's Bravery unchanged.
4. **Reaction:** the attacker gets the hurt reaction of his own move (big finishers knock him far) — intended.
5. **Projectiles:** aim = parallel to Sora→caster at the projectile's height; homing ones also get target = caster.
   `PROJ_ALL` deflects projectiles the game never deflects (beams, ground waves…): watch for odd motion / hangs; if
   so set `PROJ_ALL = False` (512 B, still fits).
6. **Stack alignment:** C2/C7 buffers are 16-byte aligned only if the game's sp is (all its frames are ×16; VFPU
   vector loads in FUN_089a38e0/089a3bc8 need it). Note: test184's hook 2 used a 0x28 frame (misaligned) before calling
   FUN_08808ee4 — a possible extra cause of the test184 hang.
7. Not covered: assists / summons as attackers (+0x542 ≠ 0), attacks whose owner ≠ atkp source.
8. CPU fairness: CPUs keep attacking into the guard → very strong. Tune with Mat after the test.

### 11.5 Phase-2 test plan (needs the emulator)
Boot test221 → Quick Battle (go_battle.py) vs CPU Cloud, then CPU Lightning; EX gauge = 10000.0, R+□, hold guard:
(a) Cloud ◯ combo → Cloud flinches, Bravery Cloud→Sora; (b) Cloud/Lightning HP attack → guard holds, foe HP −= foe
Bravery, foe Bravery 0; (c) Fire/Lightning projectiles → fly back at the caster and hit; (d) normal guard outside EX
unchanged; (e) no freeze over several minutes; (f) win → menus. Breakpoints (log + auto-resume): C2 0x08B63014 (slow
path), C4 0x08B6306C, C7 0x08B630D0, FUN_08ada2f8, FUN_08808ae8.

## 12. Phase 2 — test221 in game (2026-10-16, PPSSPP; vs CPU Cloud and CPU Lightning, Minimal, Order's Sanctuary)

Driver: scratchpad `ppreflect2.py PORT FOE_OWNER SECONDS` (EX gauge kept at 10000, R tapped whenever the foe is in an
attack motion ≥ 10000 and re-tapped every 0.45 s during it, Sora's HP kept full, breakpoints counted with
auto-resume: C2 slow path 0x08B63014 (before IS_SORA_EX), C4, C3, C7, FUN_08ada2f8, FUN_08808ae8). Bravery read at
status +0x14 (+0x16 = base); HUD and memory matched (e.g. HUD 634 / 266 = memory).

| check | result |
|---|---|
| melee Bravery reflect vs Cloud (10020 ×7, 10050) | ✅ every guard → C2 → C4 → direct hit; Cloud recoil 911 → hurt 560/700; Bravery moves exactly: 10050 Sora 314→646 / Cloud 333→1 (±332); 10020 +66/−66 each time (e.g. Sora 613→679, Cloud 287→221); a reflect can Bravery-break (Cloud 1→0, Sora +515 stage bonus) |
| melee Bravery reflect vs Lightning (10000, 10002, 10004 ×6) | ✅ e.g. 10004 Sora 200→331 / Lightning 184→57; 10002 ±21; 10000 ±65; breaks her when she is low |
| **HP attack reflect** (Lightning 10074 ×2) | ✅ guard holds; Lightning hurt 700; **her HP 2639 → 2206 (−433 = her Bravery 433), her Bravery → 0; Sora's Bravery unchanged**. Second one: HP 2206 → 2012 |
| **projectile reflect** (Lightning magic 10045/10051 ×4) | ✅ C3 → C7 → aimed FUN_08ada2f8 → the spell flies back and **hits Lightning** (hurt 550): Bravery 10 → 0 + break (Sora +10, then +515), 179→158 / Sora +21, 158→148 / +10, 3→… |
| normal guard (EX off, NOEX run 200 s) | ✅ no C2 slow path, no direct hit, C3 fell through to the original table (no C7); HP attacks crush the guard as in vanilla |
| freezes / crashes | ✅ none in ≈ 25 min of driving (5 battles, rematches, forfeit → setup → CPU select → new battle) |
| misses | some HP attacks still hit Sora: they land 2–4 s after the attack motion starts and my scripted guard timing missed them, or EX had run out. Not a code fault |

Unexplained, probably unrelated: once (EX had just run out after Sora was hit, 704) Lightning's Bravery rose +520
with no reflect involved; and once Sora's Bravery 1227 → 613 right after a break bonus. Both outside the hooks.

**Verdict:** all three parts work as designed and are stable. Set `MELEE_REFLECT = True`, `PROJ_AIM = True`,
`PROJ_ALL = True` for the build (= test221's cave, 496 B). Balance is up to Mat (the CPU walks into it all day).

## 13. KH2 Reflect sound — verified in game (2026-10-16, test245)
Log breakpoint on the play-sound function 0x088a24d4 (a1 = absolute sound id; bank base 21900000 for #33 on test245),
tools/scripts/pp_guard_snd.py: 3 guards outside EX Mode → 21910037 + 21900021 (normal guard sounds) only; 3 guards in
EX Mode → the same + **21900081 = slot 81 (KH2 se 177 barrier up)** every time (called from 0x088383c4, the p_se op 0x03
path). Barrier EFFECT still with Codex. Tip: an unconditional log breakpoint on that hot function floods the debugger,
so don't read memory while it is on (the tool reads first, then only presses buttons).

## 14. EX-only Reflect cast animation — stance system (2026-10-16, static; test248)
Mat (test247): "now all the block animations have shifted to the reflect one" → normal guard must keep the old guard
pose, only the EX guard shows the KH2 Reflect cast. Voice split (normal "Defense!", EX "Back off!") already worked.
**Solution = data only, the game's own stance system** (`tools/scripts/spot33_exguard.py`, disc
`dumps/ULUS10566-test248-exguard.iso`). No code hook.

### 14.1 How the engine swaps motions by stance (dumps/decomp/all.c)
- `FUN_0882f0d4(…, ctrl, id)` (set motion): stores id at ctrl+0x50 (= fighter+0x180, so "is guarding" = 470/471
  still holds), then **`FUN_0882fe28(ctrl, id)`** = the override table at **ctrl+0x160 (= fighter+0x290)**: 4 pairs
  (from, to); if from == current id → the type-7 lookup uses `to`. So the block (= script + GMO motion) changes, the
  motion id does not. Filled only by `FUN_08acf2a0` (stance apply) via `FUN_0882fdc4`, cleared by `FUN_0882fe00`.
- **Stance table = system.bin `jobp`** (tag found in the EBOOT tag list at 0x089cb918), u32 4, u32 rows, rows of 0x70:
  head 0x10 (+0 u16 key, +2 stance count, +3 start stance, +4/+5 menu job-panel bytes, +6 cycle flag) + 3 entries ×
  0x20: +0 mesh variant (ff none), +1 needs EX, +2 i16 → fighter+0x39c table (-1 keep), +4/+6 i16 (`FUN_088c5e4c`),
  +8 i16 (menu "job switch" flag if ≠ -1), +0xA/+0xE i16 effect on switch (`FUN_08b33ddc`), +0xC u8 (0 → stance =
  ability-set index via `FUN_08acf234`; 1 → always set 0), **+0x10 4 × (from motion, to motion)**.
  Loaded by `FUN_088c1b9c` into a static buffer 0x09b692b0; next referenced global 0x09b69868 → **0x5B8 B = 8 + 13 rows**
  (10 used on the clean disc). Fighter: `FUN_08b2eac0` → if chrp row +8 ≠ -1, `FUN_08acf118(fighter+0xd5c, f, key)`
  (+0xd5c row pointer, +0xd60 current stance).
- **EX Mode start** `FUN_08acafac`: if chrp +0x0C & **2** → `FUN_08b33ddc(f, -1)` (next stance); **EX end**
  `FUN_08aca77c`: chrp +0x0C & 2 → `FUN_08b33ddc(f, 0)`. When the stance changes while the current motion is in the old
  or new override list, the motion is restarted (`FUN_0882fa10`). Users on the clean disc: WoL (key 3), Gabranth (2),
  Kuja (5), owner 29 (8), Feral Chaos (9: stance 1 overrides 2 → 12 in EX; +0xC = 1 both entries) — the precedent.
- Other readers of a stance table, checked: event matchers compare main-event cond byte +8 / one-shot +6 with
  stance+1 — **no #33 event sets them** (the nonzero ones are the costume byte +9/+7 = sword trails); line 37443 passes
  entry +4/+6 (ours 0,0 = the no-table default); `FUN_08ab3610` gives 1 unless chrp +0x0C bit 8 (Sora: 0x801 → bit 8
  clear); `FUN_089e4e34` is Cecil-only (key 0); AI `FUN_08a6ba80` asks set (0+1)%2 only after a miss, as for Feral;
  menu (menu_all.c 432664-437629) uses head +4/+5 and entry +8 only (ours 0/0/-1 = normal Customization).

### 14.2 What spot33_exguard.py writes
- system.bin: jobp row **key 10** appended (11 rows ≤ 13): stance 0 = WoL's neutral entry, no pairs; stance 1 = same
  entry + **470 → 10318, 471 → 10319**. chrp row of owner 33: **+8 0xff → 10, +0x0C 0x801 → 0x803**. system.bin +112 B.
- objx p_se: type-7 rows **10318 → block 60, 10319 → block 67** (variant 0); **block 60 := copy of guard block 20,
  block 67 := copy of block 21** (byte 0 renumbered; every event incl. GUARD hitbox, Reflect op 0x46, se 177, voice
  split). objx −656 B (Cloud's old blocks were bigger). Run LAST (after spot33_soundids + spot33_reflectvoice), so the
  copies carry the final sound ids. Re-run = no change; copies refresh if blocks 20/21 change.
- Model (`--gmo`, build_sora.sh before pkg_put of 1P, replaces the old take into _160A/_161A): Codex's cast
  _160A → **_702A (60)**, _161A → **_706B (67)**; dead stubs _700A _701A _704A _706A := copy of _070A. Model
  **2,497,336 B** (limit 2,506,640; test245 2,499,612 = mirror-match-tested). _160A/_161A = old guard again.

### 14.3 Dead-slot proof (test247 objx; spot33_exguard re-checks the first three at every run)
| slot (GMO idx) | size | motion ids → block | plya / comb | engine constant | tool template | verdict |
|---|---|---|---|---|---|---|
| _702A (60) | 10,148 stub | 10040 only | no piece (+0x1c or landing +0x10) | none (0x2738) | no (firefx only notes it as dead) | **DEAD → Reflect ground** |
| _706B (67) | 10,148 stub | 10097 only | no piece (AF3 landing was 10097, now -1) | none | no | **DEAD → Reflect air** |
| _700A (58) / _704A (62) | 10,148 | 10090 / 10092 | no piece | none | spot33_chain AUTHOR tpl (script only) | dead anim → _070A copy; block kept |
| _701A (59) / _706A (66) | 10,148 | 10041-43 / 10096 | no piece | none | spot33_magic tpl / SLOTS tpl (script) | dead anim → _070A copy; block kept |
| _704B (63) / _704C (64) | 10,148 | 10093 / 10094 | piece 0x5cb AIR_FINISH2 (motion + landing), in NO comb action | none | — | dead in practice, left alone |
| _630A (53) | 10,148 | 10030 | no piece | **played by FUN_08a2b98c** (special state) | SLOTS tpl | NOT dead |
| _651A (57) | 15,612 | 10061 | piece 0xb31 unused | **0x274d played by FUN_08a2b98c** | — | NOT dead |
| _719A (86) | 36,336 | 10299 | — | results camera hook | — | hook, keep |

Thinning (every 2nd key, gmo_thin.py, measured on test247): total possible 463 KB; biggest: _910A win −27.3 KB,
_812C −16.2, _000A idle −16.6, _812A −15.4, _719A −13.3, _911A −10.0, _725A −9.4, _900A −9.2, _812B −9.0, _801B strain
−8.8, _060A −8.4, _902A −7.5. Not needed for test248 (no visible motion thinned).

### 14.4 Runtime checks (not run yet — emulator busy)
Normal guard ground/air = old pose + "Defense!"; EX guard ground/air = Reflect cast + "Back off!" + se 177; Reflect
still sends hits/spells back; EX ends mid-guard → guard restarts in the old pose; EX Burst/KO/win unchanged; no crash vs
CPU Sora (mirror: 2P model) and vs Cloud; Customization screen for Sora unchanged.
Static verification of test248 vs test247/test245: objx changed only p_se type-7 (+2 rows, sorted) and type-8 (blocks
60/67 = 20/21 except byte 0; all other 102 blocks identical); main.bin changed only system.bin (chrp row 33 bytes
+8 and +0xC; jobp rows 0-9 identical + row 10); GMO motions vs test245 changed only 58/59/60/62/66/67; 1P = 2P = 3P.
Hashes: ISO 2964d2acc9950bf2…, GMO 787a198182b15328… (2,497,336 B), objx dd44e861e2589889… (1,534,464 B).

## 15. EX Reflect barrier = KH2 Reflega shell (2026-10-16, static; test249)
- Mat (test247): "the reflect barrier effect is not visible" → "has to look as close to the KH2 one as possible".
- `tools/scripts/spot33_barrier.py ISO CLEAN_ISO [--dry]` (build line after spot33_reflect): EX-only one-shot
  op 0x19 at frame 0 of the guard blocks (same condition bytes as the EX sound-81 one-shot, [0,2,0,0]):
  ground (motion 470 → block 20; EX copy 10318 → block 60 when spot33_exguard ran) = FEPA id **9120** = KH2 dome
  (model 0, r 1.98 m, 0.68 m above root); air (471 → 21; 10319 → 67) = id **9121** = KH2 full faceted sphere (model 6,
  r 2.07 m, on root). KH2 TEX1 cyan panels per facet (new TEX 21), 34-frame life, no fade yet.
- Resources (dead Cross-slash effects, proof + KH2 layer timing + options): notes/kh2-effects.md "Barrier resource
  audit". effe stays 848,640 B. Disc dumps/ULUS10566-test249-barrier.iso = test247 + this (test248's EX-cast routing
  is NOT in it; the two steps stack in either order).
- Check in game: notes/kh2-effects.md "Runtime checks" (EX guard only, ground + air, disappears cleanly, no freeze,
  other effects unchanged, mirror match).
- 2026-10-16T06:53:56Z v2 (test253 = test248 + spot33_barrier v2): test250-252 froze (v1's 768/1,344-vertex meshes are the suspect).
  Now one triangle strip per shell, asserted <= 384 vertices: ground = full KH2 dome (303), air = KH2 sphere minus
  pole cap + lowest ring (371); BARRIER_SCALE default 2.5; only leaves 49/50 emptied. Arena/crash analysis and the
  bisect plan if it still freezes: notes/kh2-effects.md "Vertex budget and effect arena".
- 2026-10-16T07:55:11Z test264 = test262b + spot33_barrier with pole caps (Mat: "there's a hole"): ground half dome closed on top
  (369 vertices), air sphere closed at both ends (440, bottom = cone to the pole). notes/kh2-effects.md "Pole caps".
