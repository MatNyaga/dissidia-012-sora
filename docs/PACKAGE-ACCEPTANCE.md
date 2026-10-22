# Per-package acceptance list (P2.10)

Draft 2026-10-20 by Claude (P2.0 helper), extended the same day (P2.9/P2.10 research helper). **Replaced 2026-10-22**
by the reviewed list of notes/phase2/P2.10-kit-built.md §4 (Claude, P2 docs helper): items marked **NEW** were not in
the 2026-10-20 draft, **CHANGED** = the draft text was outdated. Sources: notes/dlc.md §F (lessons 1-21),
the Phase 1 release-readiness list RR-01..RR-22 (private plan), [TEST-ON-VITA.md](TEST-ON-VITA.md) V1-V8, what P2.3 / P2.4 / P2.5 ran by hand. Tool inventory and
the `tools/qa/runtime/` fold plan: notes/phase2/P2.10-testkit.md. Owner-34 specifics: notes/phase2/P2.9-testfighter.md.

Some tools named here are in the private working project and not published yet:
[list](REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).

**The kit** (built 2026-10-21, notes/phase2/P2.10-kit-built.md):
- **Static (A):** `python3 -I tools/qa/acceptance/run_static.py --disc DISC --profile P` runs every A item (read
  only) and writes `report.md` + `report.json` + `logs/` (default `dumps/acceptance/<disc>-<sha8>-<profile>/`).
  `--fast` (no equiv / tree tests, ≈ 2 min), `--with-verify` (pkgapply verify, ≈ 16 min), `--controls` (A16),
  `--only` / `--skip`, `--list-profiles`. Exit 0 = PASS (known limits listed), 1 = FAIL.
- **Profiles:** `tools/qa/acceptance/profiles/<P>.json` = what the disc kind must look like (reference disc + sha,
  owners, registry sources, equiv allow-sites / shrink / **exact allowed-word count**, owner_scan owner-33 compare site list + budget,
  freed ranges, frozen module + EXTRA.REG + stub layout, package dirs, known limits). Today: `oracle-r4`, `p24-step1`,
  `p24-items`, `p23-flags`, `p25-saves`, `p28-sorac` (engine + Sora in layout C, P2.8, in progress). A new package / disc kind = a new profile; the runner has no Sora default.
- **Emulator (B, E):** `python3 -I tools/qa/acceptance/runtime_plan.py --disc DISC --profile P --port N` prints the
  exact steps + commands for every B item and the strict smoke E (n/a for features the package does not have). It
  runs nothing; the emulator owner runs the steps.

Every fighter package must pass this list before it ships, on the disc that will ship. `OWNER` = the package's owner
number (33, 34, ...), `KEY` = its 6-letter key. Always: copy of saves, disposable PPSSPP profile, CPU **Minimal** +
**Order's Sanctuary** set explicitly in every test battle (and the Battle Setup screenshot checked before VS), and a
**vanilla fighter on the same screen as a control** (lesson F-5). Who: S = `run_static.py` runs it, R =
`runtime_plan.py` prints it (PPSSPP), H = Mat on the PS Vita.

Variables: `CLEAN` = dumps/ULUS10566.iso (read only), `ORACLE` = dumps/ULUS10566-P2-oracle-R4.iso (read only),
`DISC` = the candidate (a copy; never the clean dump), `PKG` = the package dir, `REG` = the package's registry source
(tools/dlc/registry/<id>.json), `PORT` = **your own free port** per helper (41336-41344 were used; **never 41335** =
Mat's own profile; runtime_plan.py refuses it). Python always `python3 -I`.

## A. Static (S) — every build; `run_static.py --profile P` (≈ 10 min, `--fast` ≈ 2 min)
| # | check | how (tool run by run_static.py) | note |
|---|---|---|---|
| A0 | disc identity: sha256 before + after the run (unchanged), = the recipe / release value, not in use, not the clean dump | run_static.py (built in; A0b = after) | **CHANGED**: old A10 + the disc half of old B18. Second build / install = same sha (determinism, D) |
| A1 | every per-owner system.bin table has a row for each package owner (grwp, chrp, eqpm, amas, chrl, acab, ...) | `tools/qa/owner_rows.py DISC --owners 33,34` (all package owners) | `eqao` = REVIEW (not a failure); covers system.bin only (F-10) |
| A2 | package valid + reproduces its reference build | `tools/pkg/validate.py PKG [PKG2 …] --strict` (every package of the roster: cross-package clashes); `tools/pkg/pkgapply.py verify CLEAN REF PKG` = n/n REPRODUCES (`--with-verify`, ≈ 16 min) | engine discs: since P2.8 E1-E3 the engine and Sora are packages too (format 1.1, `packages/engine` + `packages/sora-C`); `pkgapply.py verify` reads 1.0 packages only, layout C is checked with `tools/pkg/layoutc.py verify` |
| A3 | registry sources valid against the disc | `tools/dlc/registry.py validate SRC… --disc DISC` (all sources at once) 0 errors | WARNs listed in the report; rejects objentry ids that are not free and flags outside the package pools (all packages except `sora`) |
| A4 | flags / ids clash-free, none written by vanilla code, package pools | inside A3 (rule 10 uses tools/dlc/flag_map.json; objentry ids vs tools/dlc/id_spaces.json `free_id_ranges_below_1338`; package #≥2 purchase flags in 3200-3455) | allocate.py still missing |
| A5 | only the expected differences vs the oracle | `tools/pkg/equiv.py ORACLE DISC --expect-engine --allow-site … --allow-shrink … --json` from the profile; the allowed-word count must equal the profile's (`equiv.py --expect-words N` does the same check in one tool) | **CHANGED**: `--allow-site` exists (no hand reading of code-word lines). **NEW**: exact allowed-word count, because allow-site ids only grow (P2.10 §6 #4) |
| A6 | no owner / package constant in code | `tools/pkg/owner_scan.py --disc DISC --json OUT` vs the profile's exact owner-33 compare site list + constant budget (`--budget COMPARES,OTHER` exits non-zero when over) | **CHANGED**: disc mode (P2.4 step 1); a finished package = 0 / 0 |
| A7 | every owner → name map has each owner (EBOOT 0x089CC020 + 0x089CF350, menu 0x08A23ACC + 0x08A544E0, battle 0x08AFB6E8) | `tools/qa/owner_names.py DISC --owners 33,34` | **CHANGED**: BY-CODE lines are a FAIL on discs with the P2.3 generic name code (P2.3-names and later). Calibrated: R3 → FAIL (battle row 33 = −1,−1, RR-22 #5), oracle R4 → PASS |
| A8 | event-only vanilla models keep their companion files; OWNER's model rows win the owner lookup | `tools/qa/objentry_resolve.py DISC --owner OWNER` | C1/C2/C3 (Cosmos `P_ORG800*` rows for owner 34; objentry sorted; ids unique) |
| A9 | Sora-specific release checks | `tools/qa/static_checks.py DISC --json OUT` (exit 1 on any FAIL since 2026-10-22) | owner 33 only (chrp 33 burst/EX flags, motion windows, item rows, costume rows 1..6); package #2 needs its own case list (open) |
| A11 | **NEW** installer rows on the disc = rows from the registry | `tools/pkg/rowgen.py check --disc DISC --registry …` | P2.3-rowgen |
| A12 | **NEW** freed code has no live user | `tools/pkg/engine/p24_refscan.py` over the profile's freed ranges (a hit counts unless "self" or inside the profile's dead-code areas) | lessons F 17/18 (incl. data pointers) |
| A13 | **NEW** the module calls game code only with a 16-byte aligned stack; no vectors on its stack | `tools/qa/acceptance/stack_rule.py` | lesson F 15; finds the P24-tri freeze statically |
| A14 | **NEW** engine install state: module + EXTRA.REG = the recipe's frozen files, EXTRA.REG decodes, XSTB fallbacks + REG block 0 on disc (static module-missing / registry-missing), abi_hash = layout, patch writers "already" | `tools/qa/acceptance/engine_disc.py`, `p24_stubs.py DISC --layout L --dry`, `patches/p23_names.py DISC --dry`, `patches/p23_lookups.py DISC --upto S --dry` | the runner refuses to call a writer without `--dry` |
| A15 | **NEW** tree tests | `run_host_test.py`, `run_host_test_v2.py`, `run_p23_test.py`, selftests of rowgen / registry / equiv / p24_stubs / find_status / stack_rule / engine_disc | test the source tree, not the disc (say so in the record) |
| A16 | **NEW** equiv controls: each new allow-site is needed | equiv once more per listed allow-site with that site left out → DIFFERENT (`--controls`) | what the P2.4 helpers did by hand ("without p24_freed_items: DIFFERENT") |
| A17 | **NEW (not built)** registry constants decoded from both halves of the built constant, not the upper half alone | registry.py validate (proposal) | lesson F 13 (ex_run_mult 1.3984 vs 1.4); until then B20 catches it |

## B. Emulator (R) — per release candidate; `runtime_plan.py --profile P --port N` prints the commands
All B items run inside the strict session of section E.
| # | check | pass looks like | how (tool / steps printed by runtime_plan.py) | note |
|---|---|---|---|---|
| B0 | strict session real + module live | running profile shows `IgnoreBadMemAccess = False`, `CPUCore = 0`; find_status LIVE, warn 0, rejected 0 | `launch_isolated.sh` STRICT=1 (E2-E3), `tools/pkg/engine/find_status.py PORT` (layout 2: registry, XSTB, FN_PTR table, stub_calls, abi hashes), `p24rt.py words` | **CHANGED**: find_status layout 2 exists |
| B1 | boot + a fresh save AND the 100 % save | no freeze; 0 "Invalid memory" / "Read Word at" | E2 with `SAVES=none` (fresh profile), then the 100 % save copy; log grep at the end (B18) | **CHANGED**: the fresh profile exists since P2.4 step 4 |
| B2 | unlock / purchase on fresh and 100 % saves (PP Catalog) | locked until bought on fresh; NEW tag after buying; not pre-bought on 100 % (F-1, F-2) | flag word dump before / after buying (flag word = *(u32*)0x089D726C + (flag>>5)·4; the plan prints the maths per registry flag); `snapshot-20261020/flagw.py` (owner 33 only, port 41336 fixed); poke PP at 0x096B2DC0 if short (note it); repeat on the 100 % copy | a generic flag reader is still missing |
| B3 | character select: cell, picture, blurb, name | own picture + blurb (RR-17), vanilla neighbour unchanged | Quick Battle → player grid: OWNER's cell (33 = 7th bottom cell, 34 = 8th); `shot.sh` + the neighbour; main-menu Character Select too | |
| B4 | Quick Battle vs CPU OWNER + Opponent Info | name shown (F-11), battle runs, Forfeit → Battle Setup | `p24/boot_nav.sh`, `setup_enter.sh`, `forfeit.sh`: CPU = OWNER, STAGE Order's Sanctuary (12/35) + STRENGTH Minimal (1/9) → **setup screenshot checked** → VS → "Lv… <name>" → fight 30 s → Forfeit. Control: CPU Lightning | **NEW**: the Battle Setup screenshot is the proof of stage / strength / level / type and is CHECKED before VS (one setup shot once landed on another screen, P2.4-items §7) |
| B5 | OWNER as player: moves, sounds, voice, win / loss poses | no Cloud / donor leftovers (RR-02) | OWNER vs CPU Minimal; every starter + HP attack once (`tools/scripts/ppcombo.py`), win and lose once; listen for donor voice | |
| B6 | EX lifecycle + EX Burst | no state leaks into the next battle (RR-05); burst plays to the end | gauge fill, R+□; EX expiring while running and guarding; forfeit inside EX; `p24/exburst_seq.py PORT full\|inc LABEL` | **CHANGED**: full burst at least 3× under the JIT (the freeze did not hit every burst) + once strict |
| B7 | assist in 4 contexts (Quick Battle, story party, Labyrinth, Original Quest) | listed exactly once (or absent everywhere if the package has none), called in battle (RR-14) | by hand: each picker, R+○ / R+□ once per context; assist gauge = *(F+0x52C)+0x1C | |
| B8 | Museum: Character Files, View Character (all outfits), Jukebox, Records | own entries; Jukebox hides unbought rows on a 100 % save (F-2); Records name / icon (RR-09/10/11) | by hand + shots: record, 3D viewer every costume, Jukebox lists on the 100 % copy, Records after one OWNER battle; vanilla rows before / after unchanged | |
| B9 | Labyrinth battle vs OWNER with and without bought tracks | own BGM or stage music, never silence (F-3) | `snapshot-20261020/bgmwatch.py` (BGM pick 0x0888B544: mode *(a0+0x4C) = 7, pick *(s32)(a0+0x804)); pick ≥ 0, or −1 then the fallback plays stage music | BGM fallback = BGM_FB (REG_ROW) since P2.3 |
| B10 | Original Quest: create, OWNER in battle 1, Test, save, load, play, return | slot face + name, party banner, header title (F-5, RR-18) | Collection → Creation → Create New Quest → Battle & Event Settings → Battle 1st = OWNER (Cloud as control slot) → Test → Start Quest → VS → pause → **Win** → Save → Quest Select → Load → Start Quest → Forfeit → Retry → Forfeit → Return to Creation Menu | |
| B11 | replay / ghost / Friend Card with OWNER | record saved, card shows OWNER (RR-19) | by hand: save + play a replay; Friend Card with OWNER as card fighter; ghost battle vs that card | |
| B12 | save → reboot → load; old save from the previous release | record intact; friend-card cap = lowest installed record slot (slot = 57 − owner, P2.5) | save in the data menu, kill own PID, relaunch the same TRIAL, load; Records + level kept; then a save made by the previous release (copy); `tools/qa/runtime/p25/p25rt.py` blob dumps | P2.5-saves (the old "25 − packages" rule is superseded) |
| B13 | Customization: equip lists, item panel, EX Mode page, stats | only OWNER's items lit for OWNER (RR-12, RR-17) | `p24/items_rt.py` + shots: Equipment lists, item panel, Battle Tips, □ command chart, EX Mode page; then a vanilla fighter: OWNER's items not offered | **CHANGED**: P2.4 is done, eligibility is by owner number; still look at Garland for owner 34 (shared vanilla equip bit) |
| B14 | Data Install, then an OWNER battle | install COMPLETE, OWNER still loads (F-6) | Extras → Data Install on the fresh profile → COMPLETE → B4 again | layout B / C only |
| B15 | menu speed vs the reference | busy ticks within noise (±5 %) of the reference; 333 MHz in menus | `snapshot-20261020/frames.py` + `clockcheck.py` on title / main / Battle / QB select; **`p24/menu_cost.py`** worst frame per action, A vs B | **NEW**: worst frame of the list-building actions (Shop / Buy list ≈ 29,600 hook calls in one frame), not only still screens; on the Vita compare with Adrenaline CPU Default |
| B16 | Cosmos story scene (owner 34, or any owner shared with a vanilla event model) | Cosmos loads his own files; nothing asks (OWNER, 1) for him | `tools/scripts/ppnames.py PORT 600 OUT` + log-only breakpoint 0x08846CCC (`a1 == OWNER`); only `obj/P_ORG800_1P.gmo/.cosx` (P2.9 §3.4) | |
| B17 | vanilla regression on the same disc | Cloud, Lightning, Garland unchanged on the screens OWNER touches | select cell, Opponent Info, one battle, Museum record, OQ slot; shots vs the reference; any difference = FAIL (F-5) | |
| B18 | log after every session | no bad access | `grep -c "Invalid memory\|Read Word at" $TRIAL/ppsspp.log` = 0 | **CHANGED**: the disc-sha half moved to A0 |
| B19 | **NEW** module-missing + registry-missing controls | menus open, battle runs, the designed degraded look, no hang | scratch copies: `install_engine.py --out SCRATCH --rollback` / `--engine <profile's engine> --no-reg` (the plan prints the engine name) | every P2.3 / P2.4 / P2.5 step ran them by hand |
| B20 | **NEW** behaviour A/B vs the reference with identical assisted steps | same numbers as the reference | `p24/exrun_seq.py`, `reflect_ab.sh` + `reflect_sum.py`, `shield_seq.py`, `kkey_seq.py`, `helm_seq.py`, `exburst_seq.py` | lesson F 13: equiv cannot see a wrong constant once it lives in EXTRA.REG |
| B21 | **NEW** JIT and interpreter | both PASS | `launch_isolated.sh` (no STRICT / `CPUCORE=2` / `STRICT=1`) | lessons F 14 / 15 |
| B22 | **NEW** new game on a fresh save gives the start-owned items | start-owned items in the inventory | `p24/items_rt.py inv`, `SAVES=none` | P2.4-items |

## C. Real hardware (H) — Mat's PS Vita (Adrenaline, game plugins off), per release candidate
The 5-minute quick check of docs/TEST-ON-VITA.md (from P2.10-kit-built §5) with OWNER in place of Sora; the long
V6-V8 (Original Quest slot, Data Install, assist) when a release needs them. **CHANGED**: game plugins off, Adrenaline
CPU **Default** for the menu feel (the 333 setting hid the menu-clock difference, 2026-10-20), a full EX Burst on
hardware (the freeze class), the Shop → Buy list (heaviest menu frame).
Before copying: the A report PASS and section E PASS on the same sha. Copy rules of TEST-ON-VITA.md (verify the sha
after remount, eject before unplugging). Results go to the "Results log" of TEST-ON-VITA.md with the disc sha. A
V-item that needs a feature the package does not have (Reflect, assist) is "n/a", not PASS.

## D. Installer — layouts A / B / C (layout C built in P2.8 step E3; P2.8 in progress)
Layouts A / B / C from the player's clean ISO; output sha = the reference sha (A0's sha check is this half); second
run identical (determinism); the clean dump is refused as output.
How: `python3 -I tools/pkg/install.py …` (layouts A / B, and layout C since P2.8 step E3:
`install.py CLEAN OUT.iso packages/engine packages/sora-C --layout C`) into two new output paths → `sha256sum`
both = reference; `equiv.py REF OUT --expect-engine` IDENTICAL; release path: `sorapatch-cli <release dir> CLEAN
--out-dir <scratch>` → "MATCH" (RC3 recipe, private Phase 1 notes); clean sha re-checked after
(df94177d…). Installer-app checks (one-click, no trademarks) = [INSTALLER-UX.md](INSTALLER-UX.md), per release.

## E. The strict smoke every R item runs inside (RC3 / R4 recipe; `runtime_plan.py` prints it for the disc)
1. `cp --reflink=auto` the candidate if anything might touch it; record `sha256sum DISC`. Base-image rule: name the
   disc + sha in the project's internal question queue before building or patching anything.
2. `flatpak run --env=STRICT=1 --env=PORT=N --command=sh org.ppsspp.PPSSPP tools/pkg/engine/launch_isolated.sh DISC`
   (own port per helper; throwaway profile, copies of Mat's saves; `SAVES=` for another save set, `SAVES=none` = fresh).
   The plan puts the trial folder where the host can read it (a folder in PPSSPP's Flatpak cache, passed as
   `--env=TRIAL=…`; untested, P2.10-kit-built §7 Q5). Note the PPSSPPSDL PID.
3. In the running profile: `IgnoreBadMemAccess = False`, `CPUCore = 0`, `RemoteISOPort = N`.
4. Boot → autosave notice → title: `find_status.py N` (B0) — **press nothing before find_status** (boot_nav.sh does
   the presses from the autosave notice on). Clock 333 MHz at title (clockcheck).
5. Extras → Data Install (layout B/C) → COMPLETE (B14). Load the 100 % save copy.
6. Quick Battle 1-on-1: player OWNER, CPU OWNER, STAGE Order's Sanctuary + STRENGTH Minimal explicitly → **check the
   setup screenshot** → VS → Opponent Info name (B4) → battle 30-60 s → Forfeit → Return to Battle Setup. Then CPU
   Lightning control.
7. Original Quest slot (B10 short form: create → battle 1 = OWNER → slot face + name).
8. Screens: game window only (`import -window <id>`; window title contains "DISSIDIA"/"duodecim") into
   `dumps/screens/<disc>/NN.png`.
9. End: kill **only the noted PID** (`kill <PID>`, never pkill), `grep` the log (B18), re-check the disc sha (A0),
   delete the throwaway profile.
Smoke = E1-E9 ≈ 25 min. Full R list = smoke + B2-B22 ≈ 3-4 h per package (B10/B11/B12 are the slow ones).

## F. Order, scope and records
- **Every build:** `run_static.py --profile P` (the report folder is the record). Before an emulator session: the
  static report PASS on the same sha. Every test disc that changes a screen: E + the B items of that screen + B17.
  Release candidate: A + E + all B + C + D.
- With two or more packages on one disc, run A and B per OWNER, plus B17 once.
- Record each run as a row in a results table (date UTC, disc sha, item, PASS/FAIL/n-a, evidence path) — in the
  package's notes and, for releases, in the project's build list (private). A FAIL of a known limit is written as
  "FAIL (known: <task>)", never as PASS (the profile's `known` map does that in the report).

## Open (P2.10 rest)
- **Static dry run: DONE 2026-10-21** (notes/phase2/P2.10-kit-built.md §3): oracle vs itself PASS (incl. pkgapply
  verify), P24-items PASS, old P24-tri FAIL for exactly the known reason (stack rule A13 + unknown module A14), P24-tri2
  PASS, a deliberately broken copy FAIL with the reason.
- **Runtime dry run: still open** — `runtime_plan.py --profile oracle-r4` E smoke must reproduce the R4 / RC3 results.
- Fold the session tools into `tools/qa/runtime/` (plan: notes/phase2/P2.10-testkit.md; copies in
  `tools/qa/runtime/snapshot-20261020/`, not yet parameterised).
- Tools still missing: allocator (A4), a generic flag reader (B2), select-cell presses for another owner (B4 / E6), a
  case list like static_checks.py for package #2 (A9), A17. (`equiv.py --allow-site` and find_status layout 2 exist.)
- Installer-written profiles for package builds (P2.10-kit-built §7 Q2, for P2.8).
