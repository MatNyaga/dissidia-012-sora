# Testing

## Kinds of checks

Keep these separate when you report results: source checks (syntax, unit tests), file hashes, structural checks of a
built disc, short in-game smoke tests, full in-game tests, hardware tests, and the project owner's own acceptance.
A newer build isn't automatically a tested build.

## Checks that need no game files

From the repository root:

```sh
bash tools/repository/smoke.sh
```

This makes a temporary copy of the committed source (`git archive HEAD`), runs every check on it with Cargo
offline and synthetic test files, then deletes the copy. It needs Bash, Git, tar, Python 3, Cargo, xdelta3 and an
already filled Cargo cache. It does not test uncommitted edits. The last recorded run passed: 203 Python syntax
checks, 19 Bash syntax checks, 12 JSON files, 5 Rust unit tests and 22 synthetic patch-app cases.

You can also run the parts one by one:

```sh
python3 tools/repository/check_source.py
cargo test --locked --manifest-path tools/installer/Cargo.toml
bash tools/installer/tests/run_synthetic.sh /tmp/dissidia-synthetic-test
```

The synthetic suite makes its own tiny test files and checks VCDIFF round trips, that the input is never changed,
"(2)" naming instead of overwriting, wrong region or game, truncated, modified or already-patched files, archives and
compressed images, missing or empty inputs, read-only output folders, unsupported compression and corrupted patches.
Don't point its working folder at real game files.

Some tools are not asset-free: `tools/pkg/engine/test/run_host_test.py` reads a real local disc, and
`tools/scripts/test_combo.sh`, the debugger tools and GUI automation can change emulator state. Read them before you
run them.

## Testing a built disc

- Note the input and output hashes, the commands and the tool versions.
- Check package bounds, IDs, event order, FEP alignment and serials, sound budget, and that a patcher run twice gives
  the same result. Always on a throwaway copy.
- `tools/pkg/equiv.py` compares two discs by content or by layout. Use it instead of requiring whole-ISO equality
  after a layout change.

## Testing in the game

Use a fresh, throwaway PPSSPP profile and **copies** of saves. For quick battles, set CPU strength to Minimal and the
stage to Order's Sanctuary each time (a restart resets them).

Cover Sora as player and as CPU, a mirror match, all six outfits, normal and EX Mode, Trinity Limit (full,
incomplete and KO), ground and air magic, Reflect, assists, the menus (shop, customisation, Museum, Jukebox,
Records), saves and unlocks, music, and intros from both sides. Check other fighters too, especially Cloud and
Garland. Long battles and many rematches in a row matter, because shared sound-bank memory problems show up late.

PPSSPP is more forgiving than real hardware: a bad memory read that crashes a Vita can pass silently in the
emulator. Turn off PPSSPP's "ignore bad memory accesses" option for test runs, and test on a PS Vita or PSP when you
can.

## Testing on a PS Vita

The Vita runs PSP games through **Adrenaline**, which uses Sony's own PSP firmware, so it is much closer to a real
PSP than an emulator.

1. Back up your Vita save (`ux0:pspemu/PSP/SAVEDATA/ULUS10566*`).
2. Copy the Sora `.iso` to `ux0:pspemu/ISO/`. A card reader is safer than USB mode; always eject before unplugging.
3. In Adrenaline, **turn off game plugins** (hold R at start → Recovery → Plugins). Some old plugin packs stop both
   the original game and the Sora version from starting.
4. Check: the game boots and loads your save; Sora is on the character select; a battle with Sora plays with his
   model, moves and voice; EX Mode works; winning and returning to the menu doesn't freeze; Data Install works; Sora
   works as an assist.

Saves created in PPSSPP may show as "corrupted" on hardware, with the original game too. That isn't caused by the mod.

## Known limitations

- A fresh clone can't do a full build until the excluded inputs and missing helpers are restored locally.
- There is no pinned dependency environment yet.
- A real PSP hasn't been tested.
- The Phase 2 multi-fighter engine is a plan with early tools, not a tested feature.
- The 20 October 2026 refresh brings the build scripts up to release 1.0; the missing helpers listed in
  [REPRODUCIBILITY.md](REPRODUCIBILITY.md) are still missing.

Current release status and known issues are in the [roadmap](ROADMAP.md).
