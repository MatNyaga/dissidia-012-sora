# Chapter 15 — The engine and the registry

**The big idea:** release 1.0 knows Sora because about 86 places in the game say, in effect, "if
the owner is 33, do Sora's thing". Phase 2 asks each of those places a different question:
"what does **this owner's row** say?" The rows live in data the installer writes, and the special
code lives in our own module. After that, a new fighter is data (a package and one registry
row), not new code. This chapter explains how, step by step, with one worked example.

Parts that P2.8 is still building are marked **[IN PROGRESS]**. Everything else is **[PROVEN]**
in PPSSPP against the frozen reference disc, unless a tag says otherwise. The short version of
this chapter is [modding/OVERVIEW.md](../modding/OVERVIEW.md); the full spec is
[ENGINE.md](../ENGINE.md).

---

## 15.1 Words you need first

- **Owner:** the game's fighter number. Vanilla playable fighters are 1-32, Sora is 33, and 34
  (Cosmos's number) is the one more free number. (Chapter 2)
- **Engine:** the one-time set of changes that makes the game ask "what does this owner's row
  say?" instead of "is this owner 33?".
- **Registry:** the file `EXTRA.REG` with one row per package fighter. A **registry row** is 64
  bytes: owner, name index, record slot, pictures, **feature bits** (switches such as "EX run" or
  "Reflect guard") and parameters (numbers such as the EX run multiplier).
- **Registry source:** the JSON file a row is built from, e.g. `tools/dlc/registry/sora.json`.
- **Module:** `EXTRA.PRX`, our own C code that the game loads at boot. (Chapter 7 §7.9)
- **Stub:** a fixed 4-instruction jump in the game's main program. It jumps into the module, or
  into a copy of the original instructions (the **fallback**).
- **Oracle:** the frozen reference disc every Phase 2 disc is compared with (release 1.0 plus
  the 1.0.1 fix).

---

## 15.2 Counting the "owner 33" places

Before changing anything, every Sora-specific place was listed **from the bytes**, not from the
names of the scripts that made them (P2.0). `tools/pkg/owner_scan.py` decodes every changed code
word and lists instructions whose constant is an owner number (33 = `0x21`) or a Sora-only
number (his item ids, sound bank, motion ids).

Result: **86 places**. Some surprises: one feature thought to exist (an EX Burst sound skip)
was never built, and one table was listed twice under two names. Lesson: **an inventory comes
from the bytes.** [PROVEN]

Each place got one of three treatments (15.3-15.5).

---

## 15.3 Way 1: tables the installer fills in (no code at run time)

Most places were "a table indexed by owner" in disguise. Example: the menu needs a picture
number for each fighter. Vanilla had a table for owners 0-32; release 1.0 added code that said
"if owner is 33, use picture 245".

Phase 2 builds a new, longer table in a dead part of the main program (the **OXT** block,
"owner-extension tables", at EBOOT `0x089A8B94`). The installer writes it:

| owner | value comes from |
|---|---|
| 0-32 | copied from the clean game's own table |
| 33 (Sora) | his registry source: `pic_slot` = 245 |
| 34 (a second fighter) | its registry source |

The menu code now reads the new table, so the "if owner is 33" code is gone. This costs exactly
what vanilla costs, the installer can check every value offline, and it works even if the module
fails to load. The same idea covers the grid rows (the **GRD1** block), the save-record data
(**SRC1**), the name keys (**KEY_POOL**), and about 20 lists and limits that already existed
in the game (unlock rows, Opponent Info names, title-call tables). One generator,
`tools/pkg/rowgen.py`, computes all of them for a roster; with only Sora installed it
reproduces the release bytes exactly. [PROVEN] (P2.3, P2.5, P2.7)

---

## 15.4 Way 2: asking the registry (REG_ROW)

A few places need a fighter's row at the moment something happens, for example the Labyrinth
music fallback ("this opponent has no own music → play the stage's"). They call a small EBOOT
helper, **REG_ROW**: "give me owner N's row, or 0". The rows come from `EXTRA.REG`, which the
module loads at boot.

Order matters. The module first copies the rows into memory, then publishes the pointer, and
only then the row **count**. Code that reads the count therefore never sees half-written rows.
If `EXTRA.REG` is missing or broken, the count stays 0 and every caller gets "no row": vanilla
behaviour. [PROVEN]

Building and checking the file:

```
python3 -I tools/dlc/registry.py validate tools/dlc/registry/sora.json
python3 -I tools/dlc/registry.py build tools/dlc/registry/sora.json -o OUT.EXTRA.REG
python3 -I tools/dlc/registry.py decode OUT.EXTRA.REG
```

(`registry.py` is in this repository; the registry source `tools/dlc/registry/sora.json` is not published yet:
[list](../REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).)

---

## 15.5 Way 3: behaviour stubs (code in the module)

Some places really are behaviour: Sora's EX run speed, the Trinity Limit, the Reflect guard,
his item effects and item menus. That code moved from hand-written MIPS in caves to C in the
module (P2.4). The game reaches it through a **stub table** whose header, **XSTB**, sits at EBOOT
`0x089A8B24`.

**Worked example: EX run speed.**

1. In release 1.0, the battle code that stores a fighter's run speed (battle overlay
   `0x08B2D380`) jumped into a small cave: "if owner 33 and in EX Mode and running, multiply the
   speed".
2. In Phase 2 that store calls a **stub** instead. A stub is 4 instructions:
   `lui at / lw at,FN_PTR / jr at / nop` — load a pointer, jump to it.
3. On the disc, the pointer points at the **fallback**: a copy of the original game
   instructions. With no module, the game runs exactly as vanilla.
4. At boot the module checks the stub table (right header, pointer inside the fallback area),
   keeps the old pointer, and writes the address of its own function. It writes **data**, never
   instructions, so the emulator's cached translated code never goes stale.
5. The module's function looks up the fighter's registry row: if the row has the EX-run feature
   bit and the fighter is running in EX Mode, it multiplies the speed by the row's
   `ex_run_mult` (Sora: 1.4). Every other fighter goes straight on.

The first try ran Sora at ×1.3984 instead of ×1.40. The multiplier had been copied from only the
upper half of a two-instruction float constant. The byte comparison could not see that, because
the number had moved from code into data. Lesson: **every converted behaviour needs a measured
run next to the oracle**, with identical steps (A/B), and registry numbers are decoded from the
whole instruction pair. [PROVEN] (P2.4 step 0)

A stub list has a hash (`abi_hash`, today `0x2F2EAE84`), so a module refuses a disc built for a
different list. [PROVEN]

---

## 15.6 What runs every frame must stay cheap

Some stubs run every frame for every fighter (EX run, the EX Mode helper), and some menu hooks
run thousands of times while a list is built. Opening the Shop's Buy list calls one item hook
about 29,600 times in **one** frame. Rules:
- the owner test runs in a few asm instructions before any C code;
- no loops over packages, no file access, no system calls in a hook;
- measure the busiest frame of each action against the oracle (`tools/qa/runtime/p24/menu_cost.py`),
  not only still screens. [PROVEN] (P2.4 step 4)

---

## 15.7 Saves: one slot rule for every fighter

A package fighter's saved record lives in the bytes of one friend-card slot: **slot = 57 −
owner** (Sora 24, owner 34 23, as 0-based indexes). Never "the n-th installed package": then
removing a package would hand its record to the next one. The installer writes the friend-card
limit (the lowest used slot) and one catch-up marker per fighter into the **SRC1** block. Old
saves are moved once, for all package slots together, with the game's own "receive a friend
card" function, so no card is lost. [PROVEN] (P2.5)

---

## 15.8 Packages and the installer — [IN PROGRESS]

With 15.3-15.7 in place, Sora needs no code of his own. P2.8 turns that into packages:

- The **engine package** (`packages/engine`) holds the module, the module loader patch, the
  menu clock fix and about 890 code words. Their "before" value is the clean game's, so the
  engine installs on a clean disc. [BUILT, first disc booted in PPSSPP]
- Sora becomes **format 1.1** (`packages/sora-C`): his `registry.json`, his files, and his edits
  to shared tables stored by identity (owner, text entry, model id, picture id), never by final
  row position. That is what lets a second package edit the same tables. [BUILT, testing]
- The installer's **layout C** builds a disc from the clean ISO + the engine + any fighters, and
  writes the tables of 15.3 for the whole roster:
  `python3 -I tools/pkg/install.py dumps/ULUS10566.iso OUT.iso packages/engine packages/sora-C --layout C`.
  [BUILT, testing]
- Next (P2.9): a throw-away test fighter on owner 34 next to Sora. [OPEN]

Steps and limits for a new fighter: [modding/MAKE-A-FIGHTER.md](../modding/MAKE-A-FIGHTER.md).

---

## 15.9 How we know it still works

Every engine step was proven the same way:
1. **Static:** `tools/pkg/equiv.py` against the oracle: the game reads the same bytes, and the
   code differs only at the declared sites, with the exact word count.
2. **Host test:** the old asm runs in a small MIPS emulator next to the new C on the same fake
   game memory; every game call and its arguments must match.
3. **Runtime A/B:** the same scripted steps on the new disc and on the oracle, in PPSSPP's JIT and
   IR interpreter, with "module missing" and "registry missing" controls, and strict mode.
4. **Hardware:** the Vita. The full P2.4 disc "works just like before" there.

All of it is now one command per disc (`tools/qa/acceptance/run_static.py --profile …`):
[modding/TESTING.md](../modding/TESTING.md).

---

## 15.10 Lessons (the short list)

- An inventory comes from the bytes, not from names. (15.2)
- A table the installer writes beats code that asks at run time. (15.3)
- Publish data first, the count last; stubs last of all. (15.4)
- The module writes pointers, never instructions. (15.5)
- Module C calls game code only with a 16-byte aligned stack (Chapter 7 §7.9).
- Measure converted behaviour next to the oracle; byte checks cannot see a wrong number in data. (15.5)
- Every per-owner table needs a row for every package owner: PPSSPP hides the missing row, the
  Vita crashes.
- Store package edits by identity, never by final position. (15.8)

The full list, with stories: [notes/dlc.md](../../notes/dlc.md) §F.

---

## 15.11 Where to look

- [ENGINE.md](../ENGINE.md): the stub table, the registry row, EXTRA.REG, every as-built step.
- [PACKAGE-FORMAT.md](../PACKAGE-FORMAT.md) §16: format 1.1.
- [PHASE2-START.md](../PHASE2-START.md) §6 (address map), §11 (traps).
- `notes/phase2/`: P2.3 (lookups), P2.4 (behaviour), P2.5 (saves), P2.7 (capacity), P2.8 (packages).
- Tools: `tools/dlc/registry.py`, `tools/pkg/rowgen.py`, `tools/pkg/engine/p24_stubs.py`,
  `tools/pkg/engine/find_status.py`, `tools/pkg/owner_scan.py`.
- Status: [ROADMAP.md](../ROADMAP.md).

Back to [14 — DLC and adding more fighters](14-dlc-and-more-fighters.md) · [00 — Start here](00-START-HERE.md)
