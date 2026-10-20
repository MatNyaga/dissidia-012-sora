# Roadmap

Last updated: 20 October 2026.

## Where things stand

| Stage | What it means | Status |
|---|---|---|
| Sora as a fighter | Model, moves, EX Mode, voices, menus, saves | Done, playable |
| Phase 1: release 1.0 | Sora as a package, a clean disc layout, a patch app | Release candidate 3 in progress |
| Phase 2: multi-fighter engine | New fighters without new game code for each | Planned; first tools written |
| Phase 3 and 4 | More select-screen space; drop-in fighter packs | Ideas for later |

## Release 1.0

### Already checked

On release-candidate builds in PPSSPP, using copies of a fresh save and a 100 % save:

- Buying Sora in the PP Catalog, his NEW tag, and the KH2 icons, avatar and music purchases (they no longer clash
  with flags the game uses for level rewards).
- Saves: Sora's record takes friend card slot 25. On a save that already holds 25 cards, the oldest unlocked card
  makes room, the same way the game handles a new card. Sora's level and progress survive saving and reloading.
- Moves on old saves: a one-time catch-up gives Sora every move his level already earned.
- Battles in Quick Battle, Arcade and Labyrinth, mirror matches, and CPU Sora at maximum strength.
- EX Mode ending and clean-up between rounds; replays.
- Menus: Equipment and Optimize, the Characters panel, Records, the Museum viewer with all six outfits,
  and the Jukebox (Sora's voice set and music only show once bought; vs Sora uses the stage music if the KH2 tracks
  aren't bought).
- Original Quest: create, test, save, load, play, forfeit, retry and return; Sora's slot face, name and banner are
  correct.
- Friend cards and ghosts with Sora; Sora as an assist; Data Install on the release layout.
- The patch app on Linux: real-window runs produce the exact expected file and handle every error case.

On a **PS Vita with Adrenaline**: boot, character select, Sora battles, EX Mode, winning and returning to the menu,
Data Install and Sora as an assist all pass. An early crash in every Sora battle on the Vita (a missing Sora row in a
game table that the emulator ignored) was found and fixed this way.

### Left before 1.0

1. **Release candidate 3**: a clean build with the latest fixes (the Vita crash fix, Original Quest menu fixes and
   faster menus on the Vita), then the full PPSSPP and Vita checks again.
2. **Patch app builds for Windows and macOS**, each started once on its own system with a full patch run.
3. **Publish** on the [releases page](https://github.com/MatNyaga/sora-fan-patch/releases), with a short guide and
   the [project page](https://matnyaga.github.io/sora-fan-patch/).
4. A refreshed export of this research repository with the newer tools.

### Known issues

- In Quick Battle, "Opponent Info" shows no name for Sora (cosmetic).
- On a Vita, menus can feel a little slower than in the original game. Release candidate 3 keeps menus at the
  higher CPU speed, which is much better in testing.
- Some old Adrenaline game plugins stop the game from starting; turn game plugins off.
- A real PSP has not been tested. It will need custom firmware.
- Not covered yet: Chaos's round-specific lines, Aerith-assist lines and Cosmos story scenes keep the game's
  normal behaviour.
- Playing online or ad hoc with someone who doesn't have the same mod is not supported.

## Phase 2: the multi-fighter engine

Today Sora works because about **80 places** in the game's code and tables say "owner 33 = Sora". A second new
fighter would need all 80 again, and some of those places have no room left.

**The plan:** replace those places with **one lookup table** (the "registry": one row per extra fighter), and move
Sora's special code (EX run speed, Reflect guard, Trinity Limit, his items) into our own module `EXTRA.PRX`, which is
already on the release disc. After that, a new fighter is a package plus one registry row, with no new game code.
The technical design is in [ENGINE.md](ENGINE.md#version-2-planned-for-phase-2).

**How we'll know it works:**
1. Sora rebuilt on the engine behaves exactly like the released Sora.
2. A throwaway **test fighter on owner 34** (a renamed copy of an existing fighter, never released) can be picked,
   fights, saves and shows up in every menu, without one line of owner-34 code.

**Limits:** with today's select screen there is room for two extra fighters (33 and 34). Each extra fighter uses one
friend-card slot (25 → 24 → 23). Phase 2 discs are test discs; the 1.0 release stays as it is until an engine
release is ready.

| Step | What | Status |
|---|---|---|
| Inventory | List every owner-33 place in the game | Draft done (80 places) |
| Engine design | Registry layout, stub table, feature switches | Design written, needs review |
| Registry builder | Turn package manifests into `EXTRA.REG` | Written, self-test passes |
| ID and flag allocator | Find numbers a package can safely take, including flags the game itself writes | Flag and ID maps done; allocator script open |
| Lookup conversions | Replace "is this owner 33?" checks with registry lookups | To do |
| Behaviour in the module | Move Sora's special code into `EXTRA.PRX` | To do |
| Save slots | One record slot per extra fighter, without breaking old saves | To do |
| Shared space | Find where the game runs out of room for a second fighter | To do |
| Sora on the engine | Rebuild Sora as package number 1 and compare with the release | To do |
| Test fighter | Owner 34 with no fighter-specific code | To do |
| Acceptance list | One checklist and test kit every package must pass | To do |
| Delivery | One patch app with a fighter-pack checklist | Decided; to do |
| Hardware | Engine discs on the PS Vita | Partly proven: the module and its file hook already work on the Vita |

## Later

- **Phase 3:** a second page on the character select screen, for more than two extra fighters.
- **Phase 4:** fighter packs you can drop onto the memory stick.
- **New fighters:** planned separately, once the test fighter works.

## Optional ideas

Not needed for a release, and only if they're picked later: a Sora story campaign or ending, a Keyblade crafting
chain, more music or voice content, and new manikin content.

## How you can help

- Test on a **real PSP** with custom firmware and report what happens.
- Report bugs with your version, platform and steps ([CONTRIBUTING.md](../CONTRIBUTING.md)).
