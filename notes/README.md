# Research notes

These are the project's working notes, exported on 22 October 2026 as a reviewed subset. They hold the exact
findings: addresses, table layouts, file formats and test results. The guides in [docs/](../docs/) explain the same
things in plain words; start with [docs/modding/OVERVIEW.md](../docs/modding/OVERVIEW.md) or the learning path
[docs/learn/00-START-HERE.md](../docs/learn/00-START-HERE.md).

How to read them:

- **They are working notes.** Many were written during a test and later corrected in the same file. When an early
  line and a later line disagree, the later one is the newer finding. Newer Phase 2 notes are in
  [phase2/](phase2/), one per step.
- **No game code.** Where the private notes quote the game's own instructions, this copy says the address and what
  changes instead. Short code that remains is our own patch code (stubs, thunks, hook words we wrote).
- **Local file names.** Paths such as `dumps/…` (test discs, screenshots, logs) and `packages/…` are files on the
  project's own machine. They are named so a result can be traced; they are never published.
- **Tools.** Some tools named here are not in this repository yet: see
  [docs/REPRODUCIBILITY.md](../docs/REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).
- **The 100 % save** used in many tests is a downloaded save with every fighter and menu unlocked; only copies of it
  are used.
- **P2.8 (Sora as package #1 on the engine) is in progress.** Its notes describe the current state, not a finished
  result.

## Topics

| note | about |
|---|---|
| [dlc.md](dlc.md) | DLC and new-fighter research; §F: lessons every new fighter must respect |
| [dlc-phase2.md](dlc-phase2.md) | Phase 2 start: the owner-33 inventory and the engine design inputs |
| [roster.md](roster.md) | How owner 33 became Sora's roster slot |
| [character-file.md](character-file.md), [package-format.md](package-format.md), [gmo-format.md](gmo-format.md) | The battle file, the disc's packages, the model format |
| [abilities-owner33.md](abilities-owner33.md), [ability-table.md](ability-table.md), [ability-text.md](ability-text.md), [hitbox-shapes.md](hitbox-shapes.md) | Moves, abilities, their text and hit shapes |
| [kh2-sora.md](kh2-sora.md), [kh2-finishers.md](kh2-finishers.md), [kh2-limit.md](kh2-limit.md), [kh2-effects.md](kh2-effects.md), [kh2-extraction-instructions.md](kh2-extraction-instructions.md) | Bringing KH2 content over |
| [reflect.md](reflect.md), [ex-burst-controller.md](ex-burst-controller.md), [ex-damage.md](ex-damage.md), [ex-equipment.md](ex-equipment.md), [hp-magic.md](hp-magic.md), [thunder.md](thunder.md), [effects-clash.md](effects-clash.md) | EX Mode, the Reflect barrier, the Trinity Limit EX Burst, magic and effects |
| [voice-and-sound.md](voice-and-sound.md), [sound-bank-ids.md](sound-bank-ids.md), [music.md](music.md) | Voices, sounds and music |
| [menu-art.md](menu-art.md), [qb-grid-pictures.md](qb-grid-pictures.md), [outfits.md](outfits.md), [unlocks.md](unlocks.md) | Menus, pictures, outfits, unlocks |
| [assist.md](assist.md), [cpu-ai.md](cpu-ai.md) | Sora as an assist, CPU behaviour |
| [release-save-safety.md](release-save-safety.md), [release-1.0-lessons.md](release-1.0-lessons.md) | Saves and friend cards; how release 1.0 shipped |
| [phase2/](phase2/) | One note per Phase 2 step (P2.1-P2.10) |
