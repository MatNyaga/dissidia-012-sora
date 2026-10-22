History / working note — for the current picture start at [README](../../README.md).

> This was the project's README from 2026-10-11 to 2026-10-22: the first plan, written before any move or roster slot
> worked. Every stage below was done (stage 3 became roster slot #33, stage 4 and 5 became Sora). It is kept as a
> record of how the project started. Links in it point at the files as they were then.

# Dissidia 012 — new moves, then Sora

> **New session or new agent?** (At the time: read the project's internal work log first. In this repository, start
> with [AGENTS.md](../../AGENTS.md).)
> **Want to understand the whole process? Read [`docs/GUIDE.md`](../GUIDE.md).**
>
> Some tools named here are in the private working project and not published yet: [list](../REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).

Goal: add **new moves** to Dissidia 012 (PSP). Sora is the end goal, moves are the real project.

Order:
1. Change a move on an existing character.
2. Add a brand-new move to an existing character.
3. Add a new roster slot (a copy of an existing character).
4. Skin-swap that slot to Sora (solved problem, use existing tools).
5. Give the new slot its own moves.

Nobody has published working new moves or new roster slots for this game.
We are mapping unknown ground. Write everything down in `notes/`.

## Folders

| Folder     | What goes in it                                            |
|------------|------------------------------------------------------------|
| `dumps/`   | Your own ISO, extracted files, decrypted EBOOT. **Never share.** |
| `notes/`   | What we learn: addresses, table layouts, file formats.     |
| `tools/`   | Ghidra, ghidra-allegrex, scripts we write.                 |
| `patches/` | Our changes as cheats / xdelta patches. Safe to share.     |

## Setup checklist

- [x] Dumped: `dumps/ULUS10566.iso` (US).
- [x] PPSSPP — user flatpak. Run: `flatpak run org.ppsspp.PPSSPP`
- [x] Java 21 (`tools/jdk21`) + Ghidra 12.1.3 (`tools/ghidra`) + [ghidra-allegrex](https://github.com/kotcrab/ghidra-allegrex) v21.4
      (in Ghidra's user Extensions folder). Run: `tools/ghidra.sh` or `tools/ghidra-headless.sh`.
      Updating Ghidra means getting the matching ghidra-allegrex zip too — versions must match exactly.
- [x] ISO extracted, PACKAGE.BIN unpacked (`dumps/package/`). See `notes/package-format.md`.
- [x] EBOOT decrypted with `tools/pspdecrypt`. Ghidra project: `ghidra-projects/dissidia012` (EBOOT + battle overlay).
- [x] Battle code: `OVL_BATTLE_APP.ELF`, plain ELF at 0x089DD4C0.

## Stage 1 — change a move on an existing character

Pick one character (start with Cloud: lots of mod docs reference him).

1. **Find the equip list in RAM.** In the Customize menu, equip/unequip an HP attack.
   Use PPSSPP's memory search for the value that changes. That's the ability ID.
2. **Swap IDs.** Poke a different ID from the same character into that slot. Does the move change in battle?
3. **Find the move's data.** Follow the ID in Ghidra: what table does the battle code read with it?
   Look for damage, hitbox, animation ID, effect ID, startup/recovery frames.
4. **Change one number** (e.g. damage). Confirm in battle.
5. **Point the move at a different animation** from the same character.
6. **Cross-character test:** give Cloud another character's move. Expect a crash
   (their animations/effects aren't loaded). The crash tells us how loading works.

Done when: we can describe the move table in `notes/move-table.md` and edit one move on purpose.

## Stage 2 — a brand-new move

Add a new table entry (or reuse an unused one). Reuse existing animations first.
New animations come later (from KH2 via OpenKH, retargeted to the Dissidia skeleton).

## Stage 3 — new roster slot

Find the character table and the select-screen grid. Look for hardcoded character counts.
DLC/costume slots are a possible shortcut.

## Rules

- Own copies only. No ISOs, game files, or ripped models in `patches/` or online.
- Share changes as cheats or xdelta patches only.
