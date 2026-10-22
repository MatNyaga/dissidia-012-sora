# Chapter 7 — Game code: EBOOT, overlays, Ghidra and code caves

**The big idea:** most of the mod is *data* (tables, models, sounds). But a few things can only
be done by changing the game's *program*: giving #33 a saved record, making room for more
abilities, fixing a menu picture lookup, and Reflect. We read the program with a tool that
turns machine code back into readable text, then make tiny, careful edits. When a change needs
more room than we have, we put our own code in an empty spot (a **code cave**) and make the
game take a **detour** there.

---

## 7.1 Words you need first

- **CPU:** the PSP's brain. Its kind is **MIPS** (Sony's version is called **Allegrex**).
- **Instruction:** one tiny command for the CPU ("add these", "load that", "jump there").
  Every MIPS instruction is exactly **4 bytes** (one "word").
- **Machine code:** a program as raw instruction bytes. Not readable by people.
- **Address:** a numbered place in the PSP's memory. User memory runs from `0x08800000` to
  `0x0A000000`. Code addresses look like `0x0880A384`.
- **VA (virtual address)** = the address in memory. **File offset** = the position in the file
  on disc. Converting between them is simple subtraction once you know where the file loads.
- **Function:** a named piece of code you can call. Ghidra names them by address, e.g.
  `FUN_08809f00` = "the function at 0x08809f00".
- **Register:** a tiny storage slot inside the CPU (`a0`, `s0`, `ra`, `sp` …). `ra` holds the
  "return address" (where to go back after a call); `a0`–`a3` carry a function's inputs.

---

## 7.2 The program files

| file | what | notes |
|---|---|---|
| `PSP_GAME/SYSDIR/EBOOT.BIN` | the **main program** | encrypted on the disc |
| `USRDIR/DATA/OVL_BATTLE_APP.ELF` | battle **overlay** | plain (not encrypted) |
| `USRDIR/DATA/OVL_MENU_APP.ELF` | menu overlay | plain |

**EBOOT** is the PSP's standard name for a game's main program. It's encrypted on the disc.
`tools/pspdecrypt` decrypts it → `dumps/extracted/EBOOT.elf`. In test 20 we put the
**decrypted** EBOOT on the disc (same slot) and PPSSPP boots it fine. **[UNKNOWN]** A real PSP
needs custom firmware for that (fan translations do the same); not tested on hardware yet.

**Overlay:** the PSP has little memory, so the game doesn't keep all its code loaded. The battle
code and the menu code take turns in **the same memory area** (`0x089DD4C0` onward). Analogy:
one theatre stage; between acts they swap the scenery. So battle code and menu code can't both
be running, and they need separate Ghidra projects.

Memory map (simplified):

```
0x08804040 ─ 0x089DD3C0   EBOOT code + data
0x089DD3C0 ─ 0x089DD4C0   a small gap (256 bytes) — looks empty, but see 7.6!
0x089DD4C0 ─ 0x08B62F70   the overlay slot (battle OR menu code)
0x08B62F70 ─ 0x08B63170   free space after the battle overlay (512 bytes) ← our code cave
0x08B63170 ─ …            more EBOOT data
```

---

## 7.3 Ghidra: reading the program

**Ghidra** is a free tool (from the NSA) that takes machine code and shows it as assembly
(one line per instruction) and as a **decompile** (C-like text a person can follow).
**ghidra-allegrex** is a plugin that teaches Ghidra the PSP's CPU.

- Setup: `tools/ghidra.sh` (window) or `tools/ghidra-headless.sh` (no window), Java 21 in
  `tools/jdk21`, project `ghidra-projects/dissidia012`. Ghidra and the plugin versions must match
  exactly.
- The whole decompile is saved as text: `dumps/decomp/all.c` (EBOOT + battle overlay) and
  `dumps/decomp/menu_all.c` (with the menu overlay). **We `grep` these files** to find where a
  number is used. That's how most code findings were made.
- Our Ghidra scripts: `Decomp.java`, `Disasm.java`, `PatchDisasm.java` (check our patches
  disassemble correctly), `FixNoReturn.java`, `Redisasm.java`, `ReadWords.java`.

**Lesson:** Ghidra wrongly marked one function (`FUN_088d9f5c`) as "never returns", so it cut
every function that calls it short — code after the call was missing from the decompile. Fixed
with `FixNoReturn.java`. If a function looks oddly short, check the disassembly.

**No public decompilation of Dissidia 012 exists.** Everything here is new.

---

## 7.4 Writing code: tiny and checked

- `tools/scripts/mips_asm.py` — a mini assembler for the few instructions we need. Input looks
  like Ghidra's listing (one instruction per line, in the usual MIPS notation). It was checked
  against the game's own code.
- `tools/scripts/mdis.py` — a tiny disassembler for the menu overlay.
- Every patch script first **checks the original bytes** are there, then writes. Running it
  twice prints "already patched". That way a patch never lands on the wrong version.

### The code changes in the mod

| change | where | tool |
|---|---|---|
| owner 33 always unlocked | EBOOT unlock table (data) | built in test 20 |
| #33's own saved record | EBOOT `FUN_088cb3b4`, `FUN_088cb164`; friend-card limit 25 → 24 | `spot33_save.py` |
| ability table room 808 → 832 rows | EBOOT `0x088B1CF0`: the row limit constant 808 (0x328) → 832 (0x340) | `spot33_ablt_cap.py` |
| setup screen shows Sora's art, not "FINAL FANTASY" | menu overlay `FUN_08aa44ac` / `FUN_08aa6148` | `spot33_qbpics.py` |
| Reflect (EX Mode guard) | EBOOT + battle overlay, 3 hooks + cave | `spot33_reflect.py --apply-code` |

### Example: making room without moving code

The setup-screen fix needed three extra instructions (`xori`, `addiu`, `movz` = "if this is
owner 33, use picture 245 instead of 32"). There was no free space. But the function loaded the
same value three times in a row (the same field of the same object), so we **compacted** those lines and used the
freed words. Same size, nothing moved.

---

## 7.5 Code caves and hooks

A **code cave** is an unused spot in memory where we can put our own instructions.
A **hook** is a small change in the original code that jumps to the cave. The cave does its work,
then jumps back to just after the hook. Analogy: a **detour sign** on a road. The road is the
same; for a moment traffic goes round the block and comes back.

```
original code                         code cave (our code)
  ...                                   C1: if (fighter is Sora in EX Mode) …
  0x0880A384:  j C1        ───────────►     do our extra work
  0x0880A388:  (delay slot)                 run the instructions we replaced
  ...          ◄──────────────────────  j back to 0x0880A38C
```

(MIPS detail: the instruction right after a jump still runs — the "delay slot". Hooks must
account for it.)

---

## 7.6 Reflect — Sora's EX Mode special

Mat: "in EX Mode his block becomes Reflect, which reflects all damage back at the attacker"
and "it reflects everything in KH2". Mat chose **full strength, EX Mode only**.

### How Dissidia's guard works (from the code)

- Sora's guard = motion 470 (ground) / 471 (air). Its script turns on a GUARD hit (kind 4).
- When two hits touch, `FUN_08809f00` looks up the outcome in a **16 × 16 table** at
  `0x089d4978` (my hit kind × your hit kind):
  - guard (kind 4) vs melee Bravery → **repel** (attacker recoils)
  - guard vs HP attack → **guard crushed** (you get hit)
  - special guard (kind 12) vs anything → repel (can't be crushed)
- **Blocking never damages the attacker** in normal Dissidia melee. Nothing to borrow.
- **Projectiles** have their own tables. Dissidia already has a **deflect**: the projectile
  changes side and flies off, aimed **at the guarder's opponent** if a reflect bit is set, else
  in a random direction.
- EX Mode check: `FUN_08b34378(fighter)`.

### The design: three hooks

| hook | where | what |
|---|---|---|
| shared check | cave | "is this fighter owner 33 **and** in EX Mode?" |
| 1 | EBOOT `0x0880A384` | if so, turn his guard kind 4 → 12 (HP attacks can't crush it) |
| 2 | EBOOT `0x0880A410` | on guard success, apply the attacker's own hit to the attacker |
| 3 | battle overlay `0x08ADA22C` | projectile vs his guard → always outcome 3 (deflect) |

### Where to put 320 bytes of code? (the lesson of the "empty" gap)

- First idea: the 256-byte **gap in the EBOOT** at `0x089DD3C0–0x089DD4C0`. It looked unused.
- Reading the overlay **loader** (`FUN_089331fc`) showed it copies the overlay file *including its
  0x54-byte ELF header* to just below `0x089DD4C0` — **inside that gap** — every time an overlay
  loads. Our code would be overwritten. Only 172 bytes were safe.
- Chosen: the 512 bytes **after the battle overlay's end** (`0x08B62F70–0x08B63170`). We **grow**
  the overlay file by 320 bytes (moving its section tables after the data). No data or code
  anywhere points into that range; the EBOOT's data that follows starts later; the hooks only run
  in battle, when the battle overlay is loaded anyway.
- On disc the overlay still fits its sectors. The disc's folder entry gets the new file size.

**Lesson:** "looks empty" isn't proof. Read the code that *writes* memory near your cave.

### In-game result (test184, 2026-10-15) **[PROVEN]**

| check | result |
|---|---|
| game boots, battles start, rematches reload the overlay | yes |
| normal guard outside EX Mode | unchanged |
| EX guard vs HP attack | **holds**; the attacker recoils; Sora loses no HP |
| EX guard vs projectile | **blocked** every time — but not sent back |
| EX guard vs melee: damage back | **no** |
| no freeze | yes, *with hook 2 switched off* |
| win → menus | fine |

Why hook 2 failed:
- (a) Re-running the attacker's hit on the attacker: the hit landed (Cloud flinched) but no
  Bravery moved — the hit was still credited to Cloud: "Cloud hits Cloud".
- (b) Crediting Sora instead: the game **refuses hits on a fighter who is mid-attack** (a
  victim-state check), so every melee reflect was dropped.
- (c) One magic hit passed that check and **hung the game** (endless loop).
- → `MELEE_REFLECT = False`. Lesson: the game's hit pipeline is not safe to re-enter.

Why projectiles don't fly back: the deflect code only reflects projectiles marked "reflectable";
Lightning's aren't. The few that deflect fly in a random direction.

**State on 2026-10-15:** hooks 1 + 3 on, hook 2 off. The next design was to apply the damage
*directly* at guard success and to aim projectile deflects at the caster (`notes/reflect.md` §10).

**Later [PROVEN]:** the finished EX Reflect sends melee hits, HP attacks and spells back (an HP
attack costs the attacker HP equal to his own Bravery) behind the KH2 Reflega barrier. In Phase 2
its code moved out of the battle-overlay cave into our C module, and the overlay went back to its
original size ([P2.4-reflect.md](../../notes/phase2/P2.4-reflect.md), §7.9 below).

---

## 7.7 Other code we read (useful facts)

**The fighter in memory** (found live, Chapter 9):

| where | what |
|---|---|
| fighter +0x544 | vtable `0x08B3A9A8` (how tools find fighters in RAM) |
| fighter +0x2F8 → +6 | owner number |
| fighter +0x80 | position (x, y, z) |
| fighter +0x90 | facing direction |
| fighter +0x180 | **current motion id** (u16) |
| fighter +0x3BC | animation speed multiplier |
| `*(fighter+0x52C)` +0x14 | **Bravery** |
| `*(fighter+0x52C)` +0x0C − +0x08 | **HP** (max − damage taken) |
| `*(fighter+0x52C)` +0x18 | **EX gauge** (float, 0–10,000) |

**Hard-coded sounds:** Cloud's Omnislash code builds the sound numbers 2200053 / 2200054 directly
from two-instruction constants. A future hook can compute Sora's numbers instead (designed in
`notes/sound-bank-ids.md`).

**Movement speed [NOT FOUND]:** run speed is not in `chrp`, `chrl`, or the animation speed.
It probably comes from the action state's own code. Still open.

**Menu freeze recipe:** pause the CPU a few times in the debugger and read `pc`/`ra`. The
addresses that keep showing up are the looping function; look it up in `menu_all.c`. That's how
the Customization freeze (missing `amas` row) was found.

---

## 7.8 Where to look

- `notes/reflect.md` — the whole Reflect story and code plan.
- `notes/roster.md` tests 20–21 — the save-record code.
- `notes/abilities-owner33.md` §1–2 — the ability buffer cap.
- `notes/qb-grid-pictures.md` — the menu overlay patches.
- `tools/scripts/mips_asm.py`, `mdis.py`, `spot33_save.py`, `spot33_ablt_cap.py`,
  `spot33_reflect.py` (`--code-plan` prints all addresses).
- `dumps/decomp/all.c`, `dumps/decomp/menu_all.c`.

## 2026-10-16: new code facts

- Sora's Trinity controller (TRI) lives in **dead EBOOT code at 0x089c1c8c** (probe-proven); a dispatcher at
  0x08a39e04 sends owner 33 there and everyone else (Garland = variant 1) to the original code.
  (Since Phase 2 step P2.4 the controller is C code in the module; that dead range now holds the stub table, §7.9.)
- CPU AI: move picker `FUN_08a7c1dc`, brain file owner table, `brat` per fighter (`notes/cpu-ai.md`).
- Magi rows: type 11 = placed at the target; K8 = pitch (+ = down); +0x3c = AI threat tags (`notes/thunder.md`).
- EX damage: chrp +0x0C flag bits pick the multiplier (`notes/ex-damage.md`).
- Title call speaker = the PSP's day of the month (`notes/voice-and-sound.md`).

## 7.9 Phase 2: from owner-33 patches to an engine (2026-10-19 onward)

**The big idea:** by release 1.0, about 86 places in the code and tables said "owner 33 = Sora",
and every safe code cave was used. A second fighter would need all of it again, with no room
left. Phase 2 turns those places into one generic **engine**. This section is the code side;
the one-page picture is [modding/OVERVIEW.md](../modding/OVERVIEW.md), the detail is
[ENGINE.md](../ENGINE.md).

**Our own module, `EXTRA.PRX`.** Instead of more hand-written MIPS in caves, the special code is
C, compiled with the PSP compiler (pspdev) into a module file on the disc,
`DATA/MODULE/EXTRA.PRX`. A 53-word EBOOT patch makes the game's own module loader start it at
boot. If the file is missing, the game runs as vanilla. **[PROVEN]** in PPSSPP and on a PS Vita.

**Three ways the game reaches our code:**

| way | what | example |
|---|---|---|
| install-time data | small per-owner tables in the EBOOT that the installer fills in; no code runs | picture index, setup banner, grid rows, Opponent Info name |
| registry lookup | the EBOOT helper **REG_ROW** returns owner N's row from `EXTRA.REG` (or 0) | the Labyrinth music fallback |
| behaviour stub | a hook calls a fixed 4-word **stub**; the stub jumps into the module, or into a copy of the original instructions (the **fallback**) | EX run speed, Trinity Limit, Reflect, item effects |

A stub is `lui at / lw at,FN_PTR / jr at / nop`. The module only writes the pointer `FN_PTR`
(a data word), never an instruction. That avoids the emulator's stale-code problem with code
written at runtime (the JIT keeps old translated code).

**Where it lives.** Three ranges of the EBOOT were proven dead (never called; a marker probe
showed it in menus, Quick Battle, replays, Extras and Story):

| range (EBOOT) | now holds |
|---|---|
| `0x089A8B14-0x089A8F0C` | the stub-table header **XSTB** at `0x089A8B24`, the REG block, the **OXT** per-owner tables (`0x089A8B94`…) |
| `0x089C1C8C-0x089C2508` (Sora's old TRI code) | the stubs, the fallbacks, **GRD1** (grid rows, `0x089C2140`), **SRC1** (save-record data, `0x089C2340`) |
| `0x089D1FB4-0x089D2084` | free (52 words) |

The first 4 words of each dead function stay original. Restoring a range's clean bytes makes the
image vanilla again there: "free" does not mean zeros.

**Two rules learned the hard way:**
- **The 16-byte stack rule.** psp-gcc keeps the stack 8-byte aligned; the game stores vectors on
  its stack with `sv.q`, which needs 16. A C function that called game code with a misaligned
  stack froze PPSSPP's JIT forever. Every call from module C into game code now goes through an
  aligning thunk; `tools/qa/acceptance/stack_rule.py` checks it without the emulator
  ([P2.4-tri.md](../../notes/phase2/P2.4-tri.md) §8).
- **Check which overlay is loaded.** Battle and menu code share `0x089DD4C0` (§7.2). Hooks that
  touch overlay memory read the copied ELF header at `0x089DD46C` first.

**How a port is proven.** The old hand-written asm and the new C run side by side in a small
MIPS emulator (`tools/pkg/engine/test/mips_emu.py`) on the same fake game memory; every game
call and its arguments must match. Then the disc runs in PPSSPP next to the frozen reference
disc with the same scripted steps (A/B), in the JIT and the IR interpreter, with "module
missing" and "registry missing" controls, then on the Vita. The scan for owner-33 constants in
the code (`tools/pkg/owner_scan.py --disc`) went from 16 owner-33 compare sites to **0**.

Where to look: [ENGINE.md](../ENGINE.md), [PHASE2-START.md](../PHASE2-START.md) §6 (address map) and
§11 (traps), `notes/phase2/P2.3-*.md` and `P2.4-*.md`.

Next: [Chapter 8 — Menus, names, pictures and abilities](08-menus-and-abilities.md).
