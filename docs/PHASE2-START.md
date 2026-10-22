# Phase 2 — start here

Written 2026-10-20 by Claude (start-guide helper), static only. It gathers the Phase-2 research in one place.
The plan is [docs/PHASE2-PLAN.md](PHASE2-PLAN.md). The engine design is [docs/ENGINE.md](ENGINE.md) §"Registry + stubs v2".
The research notes are in [notes/phase2/](../notes/phase2/). If this guide and a note disagree, the note has the detail,
and this guide has the decision.

Some tools named here are in the private working project and not published yet: [list](REPRODUCIBILITY.md#phase-2-tools-not-in-this-snapshot).
Disc names (`dumps/…`) and package folders (`packages/…`) are local files and are never published. Full glossary:
[learn/GLOSSARY.md](learn/GLOSSARY.md).

## 1. What Phase 2 is

Today Sora works because 86 places in the game's code and tables say "owner 33 = Sora". A second fighter would need
all of that again, and some places have no room left. Phase 2 turns those places into one generic engine: small
per-fighter tables that the installer writes, a fixed "switchboard" (stub table) in the game code, and our own C
module `EXTRA.PRX` that runs Sora's special moves (EX run speed, Reflect guard, Trinity Limit, item effects). After
Phase 2, a new fighter is a package plus one registry row, with no new fighter code. Proof: (1) Sora rebuilt on the
engine behaves exactly like the released Sora, and (2) a throw-away test fighter on owner 34 (a Cloud copy) works.
Out of scope: more select cells (Phase 3), Memory Stick drop-in DLC (Phase 4), owners 35 and up.

## 2. Where things stand (2026-10-22)

| task | status | evidence |
|---|---|---|
| P2.0 oracle + inventory | DONE (static) | oracle R4 frozen; inventory v2 = 86 places, all byte-checked — [notes/dlc-phase2.md](../notes/dlc-phase2.md) §P2.0 + "Owner-33 inventory v2"; `dumps/p2-oracle-owner-scan.json` |
| P2.1 engine ABI | DONE (static) draft + Claude review; **v2 changes DECIDED** (§4) | [ENGINE.md](ENGINE.md) §Registry + stubs v2; [P2.1-review.md](../notes/phase2/P2.1-review.md). Codex review still open |
| P2.2 registry builder | DONE (static); fixed 2026-10-20 (test34 ids/flag, new checks) | `tools/dlc/registry.py`, `tools/dlc/registry/*.json`, selftest PASS |
| P2.3 lookups | **DONE 2026-10-21** (steps 1-7): rowgen, names, **home decision (OXT in the freed EBOOT block)**, pictures, Museum, OQ face, flag gate + BGM fallback; static PASS + PPSSPP A/B PASS + controls + strict on every step disc; **owner-33 compares on the final disc = 0**, the 5 owner immediates left are P2.5's save hooks; engine 2.5.0 (EXTRA.REG flag-range list) | [P2.3-lookups.md](../notes/phase2/P2.3-lookups.md) (25 items: 14 data rows, 11 code); [P2.3-rowgen.md](../notes/phase2/P2.3-rowgen.md); [P2.3-names.md](../notes/phase2/P2.3-names.md); [P2.3-home.md](../notes/phase2/P2.3-home.md); [P2.3-pictures.md](../notes/phase2/P2.3-pictures.md) (disc `dumps/ULUS10566-P23-pictures.iso` 83ff4ca5…f381); [P2.3-museum.md](../notes/phase2/P2.3-museum.md) (`P23-museum` a105af3c…3008); [P2.3-oqface.md](../notes/phase2/P2.3-oqface.md) (`P23-oqface` d810dc20…fd6e); [P2.3-flags.md](../notes/phase2/P2.3-flags.md) (`P23-flags` 39d82a75…8fb3 = everything; §6 hand-offs to P2.5 / P2.7 / P2.8) |
| P2.4 behaviour in C | RESEARCH DONE; **step 0 (EXRUN pilot) DONE** 2026-10-20 (static + PPSSPP); **step 1 (TRI + EE_HIT, XSTB v2) DONE 2026-10-21 on disc tri2: static PASS + PPSSPP PASS** (the P24-tri JIT freeze = module C called game code with an 8-byte-aligned stack, a game sv.q needs 16; fixed in engine 2.1.1 with aligning thunks; stub 5 was not the cause); **step 2 (Reflect cave C1/C2/C3/C7 + HELM in C, C4 fallback-only, battle overlay back to its clean size) DONE 2026-10-21 on disc P24-reflect: static PASS + PPSSPP A/B PASS**; **step 3 (Save the King SHIELD in C, EE_B back to clean words, params.shield_pct retired) DONE 2026-10-21 on disc P24-shield: static PASS + PPSSPP A/B PASS**; **step 4 (item ownership + menus: ENSURE, NEWGAME, ELIG, ROWMASK, MENU_FIX, PICID, STASH, SCALE, PANEL_LIT in C; rest of EXITEMS + jump-table SCALE back to clean words; start-owned bit, aux SCALE / EXPAGE, crown_drain retired) DONE 2026-10-21 on disc P24-items: static PASS + PPSSPP A/B PASS → P2.4 DONE** (owner-33 compares left: 2, both P2.3) | [P2.4-behaviour.md](../notes/phase2/P2.4-behaviour.md); [P2.4-exrun-pilot.md](../notes/phase2/P2.4-exrun-pilot.md); [P2.4-tri.md](../notes/phase2/P2.4-tri.md) §8 (disc `dumps/ULUS10566-P24-tri2.iso` 52f63297…ae6b; old `P24-tri.iso` 197ebdf7…688f still freezes); [P2.4-reflect.md](../notes/phase2/P2.4-reflect.md) (disc `dumps/ULUS10566-P24-reflect.iso` 48977859…49c5); [P2.4-shield.md](../notes/phase2/P2.4-shield.md) (disc `dumps/ULUS10566-P24-shield.iso` 5267025c…9efb); [P2.4-items.md](../notes/phase2/P2.4-items.md) (disc `dumps/ULUS10566-P24-items.iso` 807e09fc…1a0f; §10 = what P2.3 / P2.5 / P2.7 / P2.9 inherit) |
| P2.5 save slots | **DONE 2026-10-22**: record slot = 57 − owner via the installer-written SRC1 block (EBOOT 0x089C2340-0x089C2508) + PKG_REC; one migration for all package slots; OQ has-record + caps generic; **owner immediates 5 → 0** (owner-33 compares 0); static + host + PPSSPP A/B + pack-change scratch + controls + strict PASS | [P2.5-saves.md](../notes/phase2/P2.5-saves.md) (disc `dumps/ULUS10566-P25-saves.iso` 8f163258…31c7); research [P2.5-P2.7-saves-capacity.md](../notes/phase2/P2.5-P2.7-saves-capacity.md) §A |
| P2.6 flags / ids | DONE (static); allocator script not written | `tools/dlc/flag_map.json`, `tools/dlc/id_spaces.json`, notes/dlc-phase2.md §P2.6 |
| P2.7 capacity | **DONE 2026-10-22**: QB / select-grid rows moved to the EBOOT GRD1 block 0x089C2140 (34-cell page, GRID_CAP 34-entry cap, installer bounds); one generic installer-word writer (`p27_words.py`: rowgen + OXT + SRC1; KEY_POOL home for new keys, uicn buffer, title call generated with 0 new code words); registry owner > 34 = ERROR; static + host + PPSSPP A/B + 34th-cell scratch PASS | [P2.7-capacity.md](../notes/phase2/P2.7-capacity.md) (disc `dumps/ULUS10566-P27-capacity.iso` 387b0a7e…fb40; §3 = the decision per item); research P2.5-P2.7 note §B |
| P2.8 Sora on the engine | **IN PROGRESS; E1-E3 BUILT 2026-10-22**: `packages/engine` (engine base 832 words + loader 53 + menu_clock 5, old = clean words; EXTRA.PRX 2.5.0), `packages/sora-C` (format 1.1: identity-keyed rows, registry.json, no code patches), installer layout C (`install.py --layout C`); discs `dumps/ULUS10566-P28-engine.iso` (engine only) + `dumps/ULUS10566-P28-soraC.iso` (= P27 content, equiv IDENTICAL 0 code words; vs oracle IDENTICAL 1217 words); PPSSPP PASS. Open: E6 visibility gate, E7 roster_id, E8 two-package dry run, bytes.v1 codecs | [P2.8-sora-package.md](../notes/phase2/P2.8-sora-package.md) (design, §6 steps); [P2.8-build.md](../notes/phase2/P2.8-build.md) (as built, tests, hand-offs) |
| P2.9 test fighter | RESEARCH DONE; blocked by P2.3 / P2.5 / P2.7 / P2.8 | P2.9 note; `tools/qa/objentry_resolve.py` |
| P2.10 acceptance + test kit | **static kit DONE 2026-10-21** (`tools/qa/acceptance/`): oracle / P24-items PASS, old P24-tri FAIL (stack rule), broken copy FAIL; list reviewed and folded into PACKAGE-ACCEPTANCE.md (2026-10-22); runtime plan generator done, runtime dry run TODO | [PACKAGE-ACCEPTANCE.md](PACKAGE-ACCEPTANCE.md); [P2.10-kit-built.md](../notes/phase2/P2.10-kit-built.md); [P2.10-testkit.md](../notes/phase2/P2.10-testkit.md) |
| P2.11 delivery | DECIDED (one installer, fighter-pack checklist) | PHASE2-PLAN P2.11 |
| P2.12 real hardware | PARTIAL: EXTRA.PRX + live file hook work on Mat's Vita; **2026-10-21 P24-items (all of P2.4: stubs, TRI, Reflect, items, menus) "works just like before" on Mat's Vita** | [TEST-ON-VITA.md](TEST-ON-VITA.md) |
| P2.13 docs | in progress 2026-10-22: README, ROADMAP, docs/modding/, learn/15, glossary | [modding/OVERVIEW.md](modding/OVERVIEW.md), [learn/15-engine-and-registry.md](learn/15-engine-and-registry.md) |

## 3. The frozen oracle and how to compare

The **oracle** is the reference disc. Every Phase-2 disc is compared against it. It is R4 = release 1.0 (R3) plus the
Opponent Info name fix (8 bytes).

- Disc: `dumps/ULUS10566-P2-oracle-R4.iso` (read-only, chmod 444), sha256
  `9d311d17a7739fee2c6768f0dce3e1703db587b7c0eefd5d5180e983eb92205f`.
- Package: `packages/sora-R4` (read-only), package sha256
  `6cec661e714889461e2fd228ac5700f72b413468752b9c7edbb8a9568e72749b`, UNMATCHED 0, REPRODUCES 255/255.
- Clean dump: `dumps/ULUS10566.iso`, sha256 `df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e`. Never write it.
- Known delta to the release: R3 vs R4 = only OVL_BATTLE_APP 0x08AFB7F0/F4 (−1,−1) → (63,63). Anything else is a regression.

Commands (Python always with `-I`):
```
# a new test disc starts as a COPY of the oracle (confirm the base in codex/QUESTIONS.md first)
cp --reflink=auto dumps/ULUS10566-P2-oracle-R4.iso dumps/ULUS10566-p2N-<name>.iso && chmod u+w dumps/ULUS10566-p2N-<name>.iso

# compare (exit 0 = IDENTICAL); read every code-word line's owner_tables id until --allow-site exists
python3 -I tools/pkg/equiv.py dumps/ULUS10566-P2-oracle-R4.iso dumps/ULUS10566-p2N-<name>.iso --expect-engine \
        --json dumps/equiv-oracleR4-vs-p2N.json > dumps/equiv-oracleR4-vs-p2N.txt

# the package still reproduces the oracle
python3 -I tools/pkg/pkgapply.py verify dumps/ULUS10566.iso dumps/ULUS10566-P2-oracle-R4.iso packages/sora-R4

# an engine disc (layout C, P2.8) is built from the clean dump instead of the oracle
python3 -I tools/pkg/install.py dumps/ULUS10566.iso OUT.iso packages/engine packages/sora-C --layout C

# static checks that every package disc must pass
python3 -I tools/qa/owner_rows.py DISC --owners 33,34
python3 -I tools/qa/owner_names.py DISC --owners 33,34
python3 -I tools/qa/objentry_resolve.py DISC --owner 34
python3 -I tools/dlc/registry.py validate tools/dlc/registry/sora.json tools/dlc/registry/test34.json --disc DISC
python3 -I tools/pkg/owner_scan.py PKG_DIR --json OUT.json
```
`equiv.py --allow-site ID` (only the listed sites may differ; ID = a code_sites.json id or IMAGE:0xLO-0xHI) exists
since 2026-10-20 (EXRUN pilot helper).

## 4. Decisions

**DECIDED 2026-10-20 (Claude, on Mat's go-ahead; Codex review still welcome).** Earlier decisions by Mat (2026-10-19):
one installer with a fighter-pack checklist; one friend-card slot per extra fighter is OK; the real-hardware gate is
Mat's PS Vita.

1. **Lookups that are "a table indexed by owner" use small per-owner tables written by the installer** (the P2.3 note
   calls them OXT, "owner-extension tables"), not runtime REG_ROW lookups. Why: they cost exactly what vanilla costs,
   the installer can check them offline, and they keep working even if EXTRA.PRX fails to load (this also answers
   part of the P2.1 review's issue #1). REG_ROW stays for code that needs it.
2. **Stub table = header-indirect "XSTB".** Only a 6-word header is fixed, at **0x089A8B24**. It points at the stub
   arrays. So the EXRUN pilot can land before Trinity Limit (TRI) moves out of its range. Layout: ENGINE.md
   "v2 design changes" item 1.
3. **Order.** First, in parallel: P2.4 step 0 (infrastructure + EXRUN pilot) and P2.3 steps 1-2 (installer row
   generator with equiv IDENTICAL, then the two in-place name rewrites). The rest of P2.3 waits for the freed space /
   the pilot. P2.5 and P2.7 come after. (PHASE2-PLAN "Order and parallel work".)
4. **BGM fallback keeps an owner bound.** It becomes REG_ROW(opponent) inside the same 9 words. *(Built 2026-10-21,
   P2.3-flags §3: REG_ROW did not fit in place, so case 7 is clean again and its tail `j BGM_FB` = a 14-word EBOOT
   helper in the OXT block; same behaviour, runtime A/B PASS.)* Do NOT drop the owner
   test: vanilla mode 7 also returns −1 for Chaos, Feral Chaos and the locked Shantotto / Prishe rows, and they would
   change. It belongs to P2.3 (in place, no module code).
5. **Stub list:** S23 EX_SND dropped (never built). PANEL_LIT (menu 0x08AFF32C) added as S24. The P2.1 review's High
   fixes are part of the v2 design: the unlock walker lists an owner ≥ 33 only when its registry row exists; the
   item-eligibility stubs are on for every package owner (owner 34 shares Garland's equipment bit); a pointer table
   (BUF_PTR) for P2.7's moved buffers; a stub-list hash + roster id in EXTRA.REG and EXTRA.IDX; publish order
   registry first, stubs last; an overlay-loaded guard. (ENGINE.md "v2 design changes" item 4.)
6. **Record slot = 57 − owner.** Slot numbers are 0-based **indexes**: owner 33 → index 24 = the 25th friend card's
   space; owner 34 → index 23 = the 24th card's space. "Slot 23" in the plan and in test34.json means index 23 — the
   same thing. The migration runs **once for all package slots together**, never per owner. registry.py now checks
   `record_slot == 57 − owner`.
7. **test34.json fixed:** objentry ids 1300-1302 (vanilla rows) → 1335-1337; unlock flag 1285 → 3200. registry.py now
   rejects vanilla objentry ids and flags outside the package pools (for every package except `sora`). Selftest PASS.
8. **Cosmos fix F6** (Cosmos's objentry rows 1338/1339: costume byte 1 → 15) is part of P2.9's recipe.
9. **Wider "done" check for P2.3 / P2.4:** not only "no owner-33 compare (a test against 0x21)", but also no other
   new owner-33 constant (owner 33 loaded or compared as an immediate anywhere, for example in the TRI bar-voice code
   at 0x089C2184) and no package constants (item ids 678-682 / −678, sprite cell 32, voice 21910042, motion 8501,
   EX-page pictures, multipliers). `tools/pkg/owner_scan.py` should report both groups. Caveat: a generic
   "owner ≥ 33" bound (for example the one in the new name code, §5.3) also contains the constant 0x21; such bounds go
   on an explicit allow-list with their address (P2.4 note §1, open question 6).

## 6. Address and space map

Image legend: E = plain EBOOT, M = OVL_MENU_APP, B = OVL_BATTLE_APP. **Menu, battle and extra overlays all load at
the same base 0x089DD4C0**, so a menu VA and a battle VA can be the same number with different code.

| range | size | today (R4) | after P2.4 | notes |
|---|---|---|---|---|
| E 0x089A8B14–0x089A8B23 | 4 words | original (probe head) | stays original | never reuse |
| E 0x089A8B24–0x089A8B94 | 28 words | EXRUN (25) | **XSTB header (fixed forever at 0x089A8B24)** + pilot REG_PTR/REG_COUNT, FN_PTR[0], STUB_0, FALLBACK_0, REG_ROW | the pilot frees it first |
| E 0x089A8B94–0x089A8DE4 | 148 words | EXITEMS (incl. PANEL_LIT target 0x089A8DC4) | lookup helpers (P2.3) | **clean words since P2.4 step 4 (P24-items)**: with EE_B one 222-word unreachable block 0x089A8B94–0x089A8F0C. **Since P2.3 (P23-* discs): the OXT block** (header "OXT1", 9 tables, KEY_POOL, helpers FLAGPKG / BGM_FB / OQ_BUILD / REC_HELP; 20 words spare), P2.3-home §2 |
| E 0x089A8DE4–0x089A8F0C | 74 words | EE_B 49 + 13 free + state 12 | helpers | clean words since P2.4 step 3 (P24-shield) |
| E 0x089C1C8C–0x089C1C9B | 4 words | original (probe head) | stays original | |
| E 0x089C1C9C–0x089C2508 | 539 words | TRI 520 + table 16 | stub arrays + REG block (incl. BUF_PTR) + fallbacks ≈ 270 used, ≈ 270 spare | TRI = P2.4 step 1. **Since P2.5 (P25-saves): 0x089C2340-0x089C2508 = the SRC1 save-record block** (p25_saves.py; p24_stubs keeps it as 'p25 (kept)'); 198 words 0x089C2028-0x089C2340 still free (future fallbacks first) |
| E 0x089D1FB4–0x089D2084 | 52 words | SCALE (dead jump table) | reserve | clean words since P2.4 step 4 (= the dead function's own switch table: 52 pointers into it, nothing points at the table); still free after P2.3 (P2.5 / P2.7) |
| B 0x08B62F70–0x08B63170 | 512 B | reflect cave, **full** (128 code words) | gone: overlay file back to the clean size 1,596,312 B | |
| M 0x08B59258–0x08B63170 | 40,728 B | menu-overlay gap | candidate home for menu-only P2.3 code/tables | **static: free** (no menu ref; header word 0x089DD4CC = end of the constructor list, not a heap). **Runtime: unconfirmed** (write watch + a longer menu file must load). **Not used by P2.3** (P2.3-home §4) |
| scraps | | 7 words 0x088CB398, 3 at 0x089C24BC, spare 0x0886EF90, FUN_08893558 ≈ 29 words (dead? unconfirmed) | | too small for helpers |
| E 0x089DD3C0–0x089DD46C | | overlay header area | **not usable** | loader copies the overlay ELF header to 0x089DD46C |
| past 0x08B63170 | | bss | **not usable** | |

Other fixed points: xidx hook 0x08871420 (the module's only instruction write; everything else is data words);
save base pointer 0x089D712C; flag array pointer 0x089D726C; fighter vtable 0x08B3A9A8. Free RAM at module start:
4.1-4.3 MB; after the game's heaps 445,440 B total, largest block 247,040 B. Module estimate after P2.4: ≈ 13-20 KB.

## 7. Owner 34 capacity (P2.5-P2.7 note §B)

| item | owner 34 today | what to do |
|---|---|---|
| unlock table (E 0x089D7BE0) | **fits** (exactly the last row; new −1 at 0x089D7E74) | 35+: relocate (12 EBOOT refs) |
| objentry rows | **fits** (21 spare; ids < 1338 and free, e.g. 1335-1337) + **fix F6** | heap buffer before more fighters |
| uicn icons | fits (3 free) | installer raises the 0xD24 alloc — **built (P2.7, rowgen uicn_alloc)** |
| ablt rows + cap | fits (826 ≤ 832) | cap written by the installer |
| name-key slots, Opponent Info row 34 | fit (last slot / last row) | new key strings: **KEY_POOL (P2.7, rowgen key_pool)** |
| OQ tables (full name, party row, banner) | fit | installer rows |
| grwp, chrp row 34, chrl/amas/acab, scenario names, start preset, Labyrinth face, save stats | fit | rows |
| **QB / select-grid rows** (M 0x08A864D0) | **yes since P2.7** | moved to EBOOT GRD1 0x089C2140 + installer bounds + GRID_CAP (34 entries per page; a 3rd extra fighter = Phase 3 page) |
| eqpm presets (16136/16136 B) | no | test fighter: start preset −1 (never use "reset to default": no NULL check) or rewrite Chaos's unreferenced preset 78 (P2.7 §3 #2); then the heap loader FUN_088bcb2c |
| Jukebox character list (34 entries) | no | in-place shift from `install.jukebox_group` (no new words; guarded since P2.7) or skip for the test fighter |
| Records list (32 entries) | no | known limit for the test fighter; real fighter: installer-data growth (tail arrays in an enlarged scene, ~40-60 words, P2.7 §3 #7) |
| Characters panel (31 layout cells) | no | known limit / Phase 3 |
| Museum viewer list (34 entries) | code yes since P2.3 (VIEWER_OWNER) | a fighter needs only its collection record 35 |
| OQ face pair 40 | **yes since P2.3** (OQ_BUILD + OQ_PAIR for owners 33, 34; found in P2.7) | owner 34 needs its OQ icon picture + OQ_FACE |
| title call | **yes since P2.7** (generated, 36 callers) | `install.title_call {sqe, ddd, days}`; free days 26 / 31 (Mat Q-P27-M1) |
| item id ceiling (683) | fits (test fighter has no items) | one source since P2.7 (owner_tables item_rows.ceiling); raising = save work |

The test fighter passes only with **known limits** (not in Records list, Characters panel, Museum viewer, Jukebox
list, OQ face; start preset −1; no title call) → accepted by Mat (Q-M1: yes, 2026-10-20).

## 8. Save plan (P2.5)

- The save keeps its exact size and layout. Sora's record lives in friend card **index 24** (the 25th card's
  bytes, save base + 0x38F98). Owner 34 gets **index 23** (the 24th card, base + 0x37EF0). Rule: index = 57 − owner.
- Friend-card limit = the lowest installed slot index (Sora only: 24; Sora + 34: 23). The installer writes both cap
  words (0x088F523C init loop, 0x088F52A0 add); they must change together.
- Migration: when count > cap, cut the list and re-receive every card sitting in a package slot (the game's own
  receive replaces the **oldest unlocked** card; locked cards are never dropped), then set records up lazily per owner.
  **Once for all slots together, never per owner** (per-owner order would silently lose a card).
- Removing a pack: its record stays until a new card lands in that slot. Old 1.0 Sora saves on a Sora-only engine disc:
  same code path and bytes as 1.0.
- Owner limit: **34**. The "as" and "vs" stats blocks hold owners 0..34; index 35 is the totals row.
- The generic record lookup (≈ 80-100 words) does not fit today's cave: it goes into the freed helper range or a stub.
- **Built 2026-10-22 (P2.5-saves.md):** GET_RECORD → PKG_REC in the SRC1 block (TRI-range tail), data REC_CAP /
  REC_MARK / REC_FLAGS written by `tools/pkg/engine/patches/p25_saves.py` from registry install.record_mark /
  record_legacy; no module needed. Mat's 100 % save file is still in the pre-344c legacy state (count 25): it migrates
  at the first Sora record read on any disc, as 1.0 does. A removed pack's record is cleared by the next Friend Card
  menu commit (it re-initialises cards below the cap).
- Tests S1-S7 (fresh, 100 % save, 25 cards, add a pack later, old save, isolation, file size 257,240 B): P2.5 note §A.4.

## 9. Test kit and acceptance list

- Acceptance list (every package, every release candidate): [docs/PACKAGE-ACCEPTANCE.md](PACKAGE-ACCEPTANCE.md)
  (reviewed 2026-10-22): A0-A17 static, B0-B22 PPSSPP strict, C Vita (5-minute check), D installer, E the strict smoke
  (≈ 25 min), F records. Kit: [notes/phase2/P2.10-kit-built.md](../notes/phase2/P2.10-kit-built.md).
- The two commands (profiles in `tools/qa/acceptance/profiles/`: oracle-r4, p24-step1, p24-items, p23-flags, p25-saves, p28-sorac):
  ```
  python3 -I tools/qa/acceptance/run_static.py --disc DISC --profile P [--fast] [--controls] [--with-verify]   # A items, report + exit code
  python3 -I tools/qa/acceptance/runtime_plan.py --disc DISC --profile P --port N [--out PLAN.md]             # prints the B + E steps, runs nothing
  ```
- Test kit plan: [notes/phase2/P2.10-testkit.md](../notes/phase2/P2.10-testkit.md): one command `tools/qa/runtime/qart.py`,
  one WebSocket client, an address file checked against the oracle before each run (`qart.py selfcheck`), package
  values from the registry (no default owner). Not written yet.
- P2.9 checks (15 items incl. the Cosmos scene): P2.9 note §7.

## 10. Tools that exist

| tool | use |
|---|---|
| `tools/pkg/owner_scan.py PKG_DIR [--json OUT] [--all-imm SITE]` | owner-specific immediates in a package's patch words + img: rows (scans a package, not a disc yet) |
| `tools/qa/owner_names.py ISO [--owners 33,34]` | every owner → name map (5 copies) has an entry for each package owner |
| `tools/qa/objentry_resolve.py ISO [--owner 34] [--simulate ID:COSTUME] [--event-costume 15]` | simulates the model owner lookup; Cosmos check (C1-C3); `--event-costume 15` = fix F6 |
| `tools/pkg/equiv.py A B [--expect-engine] [--allow-site ID] [--allow-shrink IMAGE:0xLO-0xHI] [--expect-words N] [--json OUT]` | content equivalence of two discs, code differences by VA + owner_tables id; `--expect-words N` (2026-10-22) = also FAIL unless exactly N allowed-site words (allow-site ids only grow) |
| `tools/pkg/rowgen.py tables / gen / check --pkg|--disc / selftest` | per-owner rows (18 tables) from registry sources + owner_tables.json `rowgen` specs (P2.3 step 1) |
| `tools/pkg/rowgen_disc.py strip|write DISC --registry sora [--dry]` | test-disc writer for rowgen rows (only dumps/ULUS10566-P23-*.iso; not the installer) |
| `tools/pkg/engine/patches/p23_names.py DISC [--dry] [--rollback] / --sim` | generic owner → name code C1 + C2 (P2.3 step 2); `--sim` = owners −2..40 on the disc's data. Moved 2026-10-21 (engine-base patch); `tools/pkg/p23_names.py` still works (wrapper) |
| `tools/pkg/engine/p24_stubs.py ISO --layout v2\|pilot [--dry] [--rollback] / --selftest / --gen-header / --list` | XSTB stub table writer (P2.4); `STUBS_V2` = the stub ABI → abi_hash + extra/stub_abi.h |
| `tools/pkg/engine/build_p24_tri.sh [OUT]` / `build_p24_pilot.sh [OUT]` | P2.4 step-1 / step-0 test discs from a copy of the oracle (refuse to overwrite) |
| `tools/pkg/owner_scan.py --disc DISC [--json OUT] [--budget XORI,OTHER]` | the P2.3/P2.4 "done" scan on a disc: owner-33 compare count + other owner/package immediates vs the clean images, ALLOW list; exit 0 (a report) unless `--budget` is given and exceeded (2026-10-22) |
| `python3 -I tools/pkg/engine/test/run_host_test_v2.py` | engine v2 host tests: status cases + C behaviours vs R4's asm in `test/mips_emu.py` (identical game calls) |
| `tools/qa/runtime/p24/exburst_seq.py PORT full\|inc\|incN LABEL` (+ `boot_to_battle.sh`) | EX Burst A/B sequencer (same assisted steps on every disc) |
| `tools/qa/runtime/p24/{reflect_ab.sh, reflect_seq.py, reflect_sum.py, look_frames.py, helm_seq.py, boot_nav.sh, navseq.py}` | P2.4 step 2: reflect A/B (CPU Lightning, Vicious), offline summary, frame-exact barrier screenshots, Crown Pendant drain A/B, one-connection menu walks |
| `tools/pkg/engine/build_p24_reflect.sh [OUT]` / `p24_stubs.py --layout v2r` | P2.4 step-2 test disc (Reflect cave in the module, battle overlay back to clean size); since step 3 built from the frozen extra/reflect/ module (`install_engine.py --engine v2-reflect`) |
| `tools/pkg/engine/build_p24_shield.sh [OUT]` / `p24_stubs.py --layout v2s` | P2.4 step-3 test disc (SHIELD stub 20 in the module, SHIELD + EE_B back to clean words); since step 4 built from the frozen extra/shield/ module (`install_engine.py --engine v2-shield`) |
| `tools/pkg/engine/build_p24_items.sh [OUT]` / `p24_stubs.py --layout v2i` (default) | P2.4 step-4 test disc (item ownership + menu stubs 13-19, 21, 22, 24 in the module; 10 EBOOT + 3 menu-overlay site words; rest of EXITEMS + dead jump table back to clean words) |
| `tools/pkg/engine/p24_refscan.py ISO LO HI [...]` | read-only: every j/jal / branch / lui pair / data word in EBOOT, overlays and PRX modules that points into a range (who still uses code before freeing it). **Fixed 2026-10-21 (step 4):** data words pointing into EBOOT space were skipped before |
| `tools/qa/runtime/p24/{shield_seq.py, ensure_battle.py}` | P2.4 step 3: power of every built hit (write breakpoint on the hit-list tail 0x089D2804; Save the King A/B), Cross until the battle runs (slow machine) |
| `tools/qa/runtime/p24/{items_rt.py, menu_cost.py}` + `launch_isolated.sh` `SAVES=none` | P2.4 step 4: save inventory / RAM item rows / stashed record / assisted "old save" (`strip`); per-frame busy ticks of the frames after a button press + stub_calls deltas (one connection); a FRESH profile with no save (new-game tests) |
| `tools/pkg/engine/build_p25.sh [OUT] [REGISTRY ...]` / `patches/p25_saves.py` / `test/run_p25_test.py` / `tools/qa/runtime/p25/{p25rt.py, launch.sh}` | P2.5 (2026-10-22): the save-record disc (build_p23.sh flags + SRC1 block); writer (--dry / --rollback / --sites / --selfcheck; `--registry sora --registry test34` = a cap-23 pack-change scratch disc); host test R4 vs P2.5 + 2-pack reference + planted bugs; runtime: plain save-blob dumps, one-connection walks with assisted pokes at the first GET_RECORD(33) (old25 / old25legacy / fresh), logging breakpoints; launcher with the save folder as an argument |
| `tools/pkg/engine/patches/p23_lookups.py DISC [--upto pictures|museum|oqface|flags] [--dry] [--rollback] / --sites / --selfcheck` | P2.3 steps 4-7: OXT tables + helpers in the freed EBOOT block, the lookup sites in place (guarded like p23_names) |
| `tools/pkg/engine/build_p23.sh STEP [OUT]` | P2.3 step discs, ONE cumulative recipe (P24-items recipe + p23_lookups up to STEP; flags = engine 2.5.0) |
| `python3 -I tools/pkg/engine/test/run_p23_test.py [BASE.iso]` | P2.3 host test: every R4 lookup block vs the new block in mips_emu, owner by owner (+ vs clean), 12 planted bugs |
| `python3 -I tools/pkg/p28_plan.py words [--engine-disc ISO] [--json OUT] / package / plan / leftovers / selftest` | P2.8 (read-only): splits every code word clean → engine disc into engine base / generated / still-Sora; fate of each Sora patch file + merge-gap class of each row; the generic install order with counts; Sora-specific constants left in tools (file:line → destination) |
| `python3 -I tools/pkg/p28_codecs.py prove [--clean ISO] [--ref ISO] [--pkg DIR] / selftest` | P2.8 (read-only): identity-keyed codec prototypes (odir / acab / text / grid-id / pak-fill): clean + Sora's re-keyed rows = the oracle bytes, + a synthetic owner 34 (82/82 PASS) |
| `python3 -I tools/pkg/engine/make_engine_pkg.py [--engine-disc ISO] [--no-menu-clock] [--replace] [--dry]` | P2.8 E1: freeze the engine as `packages/engine` from a tested engine disc minus the clean dump (old = clean words; menu_clock = one switch) |
| `python3 -I tools/pkg/pkg11.py convert SRC_1.0 OUT --registry SRC.json / selftest` | P2.8 E2: re-key a 1.0 fighter package into a NEW 1.1 folder (identity keys); proves every touched file byte-identical first |
| `python3 -I tools/pkg/install.py CLEAN OUT packages/engine [FIGHTER ...] --layout C [--pins canonical\|refuse]` | P2.8 E3: install layout C (engine package + 1.1 fighters, installer words from `tools/pkg/rostergen.py`, EXTRA.REG / EXTRA.IDX) |
| `python3 -I tools/pkg/layoutc.py verify CLEAN REF packages/engine [FIGHTER ...]` | P2.8: layout-C file contents in memory vs a reference disc (REPRODUCES / DIFFERENT) |
| `python3 -I tools/pkg/rostergen.py selftest` | P2.8: the installer words of a roster in memory (= p27_words' logic) |
| `tools/pkg/engine/build_p27.sh [OUT.iso] [REGISTRY ...]` / `tools/pkg/engine/patches/p27_words.py` / `python3 -I tools/pkg/engine/test/run_p27_test.py` | P2.7: the capacity disc (build_p25.sh + the generic installer-word writer + the GRD1 grid rows); its host test (installer words + grid cap) |
| acceptance profile `p28-sorac` | P2.8: the layout-C Sora disc for `run_static.py` / `runtime_plan.py` |
| `python3 -I tools/qa/acceptance/run_static.py --disc DISC --profile P [--fast] [--only A5,A6] [--controls] [--with-verify] / --list-profiles / --selftest` | P2.10 static acceptance runner (A items, read only): calls the tools below, judges them against the profile, writes report.md / report.json / logs/; exit 0 PASS, 1 FAIL |
| `python3 -I tools/qa/acceptance/stack_rule.py DISC.iso\|MODULE.prx [--json OUT] / --selftest` | A13: the 16-byte stack rule on the module's .text (every call into game code through the aligning thunk; tail jumps only from asm wrappers) |
| `python3 -I tools/qa/acceptance/engine_disc.py DISC.iso [--module PRX] [--reg FILE] [--layout v2i] [--owners 33,34] / --selftest` | A14: module + EXTRA.REG = the recipe's frozen files, EXTRA.REG decodes, XSTB fallbacks + REG block 0 on disc, abi_hash = layout |
| `python3 -I tools/qa/acceptance/runtime_plan.py --disc DISC --profile P --port N` | B + E checklist for one disc (commands, PASS looks like, n/a features); runs nothing |
| `tools/dlc/registry.py build/validate/decode/selftest` | EXTRA.REG builder + validator; `selftest` = round trip + 18 error cases |
| `tools/qa/owner_rows.py ISO --owners 33,34` | every per-owner system.bin table has a row (the grwp crash class); exit 1 on a gap |
| `tools/qa/static_checks.py ISO [--json OUT]` | Sora (owner 33) release checks (chrp flags, motion windows, item rows, costumes, texts); exit 1 on any FAIL case since 2026-10-22 (was always 0) |
| `tools/pkg/pkgapply.py verify CLEAN REF PKG` | a package reproduces its reference disc |
| `tools/dlc/owner_tables.py --owner 34 / --summary / --show ID` | read the registry spec |
| `tools/dlc/owner34_scan.py ISO [--owner N]` | every per-owner table's entry for one owner |
| `tools/dlc/flag_map.json`, `tools/dlc/id_spaces.json` | free flags / FEP ids / sound banks / objentry ids (from `flag_writers.py`, `id_spaces.py`) |
| `tools/pkg/engine/find_status.py PORT` | decode EXTRA.PRX's status block (layout 2: registry, XSTB, live FN_PTR table, stub_calls, abi hashes) |
| `tools/pkg/engine/launch_isolated.sh DISC` | disposable PPSSPP profile on port 41336 (`--env=STRICT=1` = bad reads stop the game; `--env=PORT=n` own port; `--env=CPUCORE=2` IR interpreter) |
| `tools/qa/runtime/snapshot-20261020/` | 29 session tools saved unchanged (SHA256SUMS): bgmwatch, flagw, exlab, frames, clockcheck, oi/ppw … still owner 33 + fixed addresses |

## 11. Traps and lessons (read before you start)

- **Overlays share the base 0x089DD4C0.** Quick Battle "Opponent Info" is battle-overlay code on a menu-looking
  screen. Find a screen's code with a **live breakpoint** (ra of the text call), not with the decompile of whatever
  overlay usually sits there. Module code must check which overlay is resident before it touches overlay memory.
- **Five copies of the owner → name map:** EBOOT 0x089CC020 and 0x089CF350, menu 0x08A23ACC and 0x08A544E0, battle
  0x08AFB6E8. They hold the same values (0x08A544E0 is the OQ full-name list, a different list). Fill or convert all
  of them together; `owner_names.py` checks them.
- **35 is the hard owner limit** (stats totals row, chrp, Opponent Info rows, grid bounds). Owner 34 is the last one.
- **Per-frame cost rules:** per-frame paths are EXRUN (every fighter), HELM (every fighter in EX), the EX Burst bar,
  projectile contacts, and many menu draws. Use O(1) lookups there; loops over packages only in list builders; no
  syscalls, cache maintenance, file I/O or code rewriting in a hook; the owner test runs in asm before any C prologue.
  Measure busy ticks per frame against the oracle on every disc (B15). The Vita menu lag was the CPU clock
  (menu_clock), not hook cost.
- **Inventory from bytes, not from script names.** EX_SND was never built; owner_tables had one table under two names.
- **Free flags must be free against game code**, not only data (1250-1262 are set by the game; 1372 lists every
  Jukebox row on 100 % saves; 1271-1284 are icon flags). New packages take flags from the pools (3200-3455 …).
- **Event-only vanilla models still pull companion files by (owner, costume)** → Cosmos and owner 34 (fix F6).
- **Do not "fix" vanilla patterns.** Check the vanilla behaviour first (Sora's "vs Feral Chaos" row on flag 886 is normal).
- **Every per-owner table needs a row for every package owner.** PPSSPP hides NULL reads; the Vita crashes (grwp).
- **Don't shadow the standard library in scratch folders.** A script folder with `ast.py` or `types.py` breaks
  `import ast` for every script started from it. `tools/qa/runtime/snapshot-20261020/` has an `ast.py`: always run
  with `python3 -I`, and rename it when the tool is folded into `qart.py`.
- **Vita lessons:** verify the ISO sha after a remount (the SD card silently dropped a 16 KB write); eject before
  unplugging; game plugins block discs (keep them off); PPSSPP-made saves are rejected by real firmware (use a save
  made on the Vita); use Adrenaline CPU **Default** for menu-speed comparisons; a card restore must include `ux0:license/`
  (Adrenaline's license), or Adrenaline fails with C0-11136-2. Details: [TEST-ON-VITA.md](TEST-ON-VITA.md).
- **Emulator manners:** one emulator owner; port 41336 only (another port is the owner's own profile); never `pkill -f`; kill only
  the noted PID; game-window screenshots only; one WebSocket client at a time; remove every breakpoint (a leftover one
  freezes the game).
- **Manifest notes can be stale** (EX run "1.1" vs built ×1.40): registry values come from built bytes.
- **Module C → game code only through the aligning thunk** (beh.c `GFN` → `gt_<addr>`, list in `GAME_FNS`): psp-gcc keeps
  sp 8-byte aligned, the game's VFPU stack stores need 16; a misaligned call froze PPSSPP's JIT forever on P24-tri
  (P2.4-tri §8, ENGINE.md §10 wrapper rule). A PPSSPP hang at 100 % CPU with a dead debugger: attach gdb from the
  shell that launched it (ptrace_scope 1) before guessing; repeat flaky bisection cases ≥ 3×.
- **Runtime harness (P2.4 step 2, P2.4-reflect §5):** ≤ 3 debugger reads per poll + 50 ms pause (8 back-to-back reads ran
  the game at 0.6 logic frames/s); CPU Minimal + TYPE Random hardly attacks, TYPE Vicious does (still Minimal); walk menus
  in one debugger connection (`navseq.py`; the debugger server wedged after many short ones); always check the setup
  screenshot; a size change of a code image needs `equiv.py --allow-shrink` (never silent).
- **Menu hooks: measure the list-building frames, not only still screens (P2.4 step 4, P2.4-items §6.1).** The item
  hooks are idle on still screens, but opening the Shop / Buy list calls MENU_FIX ~29,600 times in ONE frame (already
  ≈ 0.33-0.4 s of CPU on the oracle). A plain C wrapper there cost +1.7 %; an asm fast path (skip the C call for
  non-package items, minimal frame) brought it inside noise. `menu_cost.py` gives the worst frame per action, A vs B.
- **Block tests must compare the next call's arguments** (P2.3): a "spare" add of 940 folded into a store offset was
  the following call's argument; the mips_emu block test (calls + arguments + live registers) caught it.
- **A registry format change must keep reading old files** (P2.3): `install_engine.py` validates EXTRA.REG with the
  current rules, so the frozen recipes' older files must still decode (min engine decides the format).
- **Reference scans must include data pointers** (P2.4 step 4): p24_refscan used to skip every data word whose opcode
  field looks like j/jal — i.e. every EBOOT pointer — so pointer tables were invisible until the fix.
- **The engine writers assume the oracle base** (P2.8 §1): `p24_stubs.py`, `p23_names.py` and `p23_lookups.py` check
  that each site holds the **R4** words before they write; 143 generic engine words (ENGINE_R4) exist today only inside
  Sora's R4 patches. From the clean dump they come from nowhere, so the engine package must carry them (P2.8 step E1,
  old = clean words).
- **Final-index keys do not compose** (P2.8 §3): a package row stored by its final position (grid add, objentry row,
  count byte, offset table) is shifted or clashed by a second package (synthetic owner 34 moves Sora's objentry rows
  1170..1172 → 1173..1175). Store edits by identity (owner, text entry, model id, picture id); the installer
  recomputes counts, offsets, final indexes and fillers.
- **The shared session scratchpad has stdlib-named files** (e.g. a `dis.py` once shadowed numpy's import): run
  helper scripts from your own subfolder and with `python3 -I`; never name a scratch file after a stdlib module.

## 12. Open questions

**For Mat (decide, please):**
- **Q-M1 — DECIDED 2026-10-20 (Mat): yes.** The test fighter may PASS while missing from the Records list, the
  Characters panel, the Museum viewer, the Jukebox list and the OQ face list ("known limits"). A real fighter must
  have them.
- **Q-M2 — DECIDED 2026-10-20 (Mat): yes.** New fighters get a title call (the voice on the title screen on certain
  dates). The table is full (35 of 35), so P2.7 must add a 36th+ caller slot and strings; it is a required feature for
  real fighters, not optional.

**For Codex:** review of the P2.1 ABI + the 2026-10-20 v2 changes (XSTB header-indirect table at 0x089A8B24,
installer-written per-owner tables instead of REG_ROW lookups, P2.1-review fixes) — `codex/QUESTIONS.md`
Q-20261020-CLAUDE-001.

**Runtime checks (R, PPSSPP):**
- Menu-overlay gap 0x08B59258–0x08B63170: write watch across the menus, and does a longer OVL_MENU_APP load fully? (P2.3 Q2 — not needed by P2.3, 2026-10-21; only a possible P2.7 buffer home)
- Is FUN_08893558 dead (marker probe)? Only if no other home works. (P2.3 Q3)
- When is FUN_08A1D7F8 called with owner 0? (P2.3 Q4; 2026-10-20: not seen, C2 keeps its 2-word guard, so no longer blocking)
- Per-frame hit counts of the menu lookup sites and menu hooks (P2.3 Q5, P2.4 Q5). **P2.4 Q5 answered 2026-10-21
  (P2.4-items §6.1): 0 calls/s on still screens; per action, e.g. Buy list open = MENU_FIX 29,586 + ENSURE 1,057 in one
  frame; worst frame within ~1 % of the oracle.** P2.3 Q5 still open.
- Overlay-resident word 0x089DD4B0 identifies the overlay? (P2.4 Q4)
- Module missing + Sora EX Burst: Garland's controller or Cloud's variant 0 as fallback? (P2.4 Q2)
- ~~Card ghost data at +0x10C / +0x10D / +0x883 could look like a record? (P2.5 Q1)~~ answered 2026-10-22: it is the ghost's own record (vanilla owner), marker 0 (P2.5-saves §6). Cloud's preset as test34's start preset? (Q2) Heap headroom for eqpm/objentry moves? (Q3)
- 100 % save flag-array dump: words 96-112 zero? (P2.6 pool gate)
- Cosmos story scene on a throw-away copy, variants a and b (P2.9 §3.4).

**Static (S):** P2.3 Q6 (spare words in the setup-banner blocks — **answered 2026-10-21**: delay slots + duplicate `andi`, P2.3-pictures §1), Q8 (home of new key strings — **answered**: EBOOT KEY_POOL 0x089A8D7C, P2.3-home §3), Q9/Q10 (registry and
table-spec fields) **answered 2026-10-20** (P2.3-rowgen §5 fields, §3 spec); P2.4 Q3 (registry gaps: `voice_bank`, EX-page face/name pictures, item "start-owned" bit,
`aux` layout; keep item_fx REFLECT_POWER and drop `params.shield_pct` — **done 2026-10-21, P2.4-shield §4**; EX-page pictures = aux EXPAGE, start-owned = item_owner bit 7, aux SCALE, crown_drain retired — **done 2026-10-21, P2.4-items §3**), Q6 (allow-list for generic owner bounds);
P2.5 Q5 (Records growth offsets); P2.1 review: flag-range list instead of one bitmap range (**done 2026-10-21, P2.3-flags §2: engine 2.5.0; sora + test34 EXTRA.REG 536 → 364 B**; was: Sora + test34 EXTRA.REG is
536 B now because the bitmap spans 888..3200), `HAS_ASSIST` bit, validator owner > 34 = ERROR, fallback "no PC-relative
displaced word" check; P2.8 package-format codecs for bytes-leaf tables (blocks P2.9); `allocate.py` (P2.6).

## 13. Glossary

- **owner** — the game's fighter number (1..32 vanilla playable; 33 = Sora, taken from Aerith's assist number; 34 =
  Cosmos's number, free for the test fighter). Most tables are indexed by it.
- **key** — a fighter's 6-letter file key (`sev120` = Sora, `sev100` = Cloud, `tst034` = test fighter).
- **oracle** — the frozen reference disc R4 (§3). "Equivalent" means: same game-readable data, code differs only at hook sites.
- **layout R / A / B / C** — how a disc carries the package: **R** = the reference build from `build_sora.sh` (Sora's
  file rows in the game's own index PACKAGE_INFO, owner-33 patches in the code, no module); **A** = the installer's
  first layout, same shape as R; **B** = the release layout: the game's PACKAGE_INFO stays clean, our module serves
  Sora's files from EXTRA.IDX; **C** = the engine layout, built in P2.8 (B + registry + stubs, no owner-33 patches; P2.8 is in progress).
- **EXTRA.PRX** — our own code module (C), loaded at boot, always in memory.
- **EXTRA.IDX** — our own file list; the module answers file lookups from it first.
- **EXTRA.REG** — the registry file: one 64-byte row per package fighter, plus item, flag and string sections.
- **registry row** — that per-fighter row (owner, name index, record slot, pictures, feature bits, parameters).
- **stub** — a fixed 4-word jump in the EBOOT (`lui at / lw at,FN_PTR / jr at / nop`). It jumps to the module if the
  module filled the pointer, or to a copy of the original instructions (the **fallback**) if not.
- **XSTB** — the stub table header at 0x089A8B24 that tells the module where the stubs and pointers are.
- **REG_ROW** — the EBOOT helper "give me the registry row of owner N" (or 0).
- **OXT / per-owner table** — a small table indexed by owner, written by the installer: vanilla values for owners
  0..32, package values for 33+.
- **I-row / I-imm** — install-time data: a table row / an instruction constant the installer writes.
- **cave** — extra code space we appended (the 512-B battle-overlay cave) or dead game code we reuse.
- **hook / hook site** — the game instruction we changed to jump into our code.
- **transitional patch** — a `packages/sora*/patches/*.json` file with owner-33 code; Phase 2 retires them.
- **objentry** — the game's model table (68-byte rows: id, owner, costume, file name); looked up by id or by
  (owner, costume).
- **companion files** — a model's `.cosx` / `.exex` files, found again by (owner, costume).
- **friend card / record slot** — the save has 25 friend-card slots; each package fighter's record uses one slot's bytes.
- **feature bit** — a registry flag that switches a behaviour on for one fighter (EX_RUN, REFLECT_GUARD …).
- **per-frame path** — code that runs every frame; must stay cheap.
- **strict mode** — PPSSPP with bad memory reads stopping the game (`--env=STRICT=1`), closer to real hardware.
- **base-image rule** — before any build or patch, Claude confirms the exact base ISO path + sha256 in the project's
  internal question queue.

Full glossary: [learn/GLOSSARY.md](learn/GLOSSARY.md).

## History: how Phase 2 started (§5, the first three work items — all done)

Kept for the record; the sections above say what is true today.

General rules for every item: claim it in `codex/QUESTIONS.md` first; get Claude's base-image confirmation (ISO path
+ sha256) before building or patching; never write the clean dump, the oracle or a disc someone else uses; Python
with `-I`, `--dry` writes nothing, re-runs are safe. Runtime: one emulator owner, disposable profile
(`tools/pkg/engine/launch_isolated.sh`, `--env=STRICT=1`), copies of saves, **CPU Minimal + Order's Sanctuary set
explicitly** in every test battle, a vanilla fighter on the same screen as a control.

### 5.1 EXRUN pilot (P2.4 step 0) — DONE 2026-10-20

**DONE (static + PPSSPP):** [P2.4-exrun-pilot.md](../notes/phase2/P2.4-exrun-pilot.md), disc `dumps/ULUS10566-P24-exrun.iso`
f5c2577c…a16e (still reproduced by `tools/pkg/engine/build_p24_pilot.sh`, which now uses the frozen pilot module in
`tools/pkg/engine/extra/pilot/`). Registry value fixed: ex_run_mult **1.4** (the "1.3984375" below is the old, wrong
value). **Step 1** (TRI + EE_HIT, XSTB v2 in the freed TRI range): [P2.4-tri.md](../notes/phase2/P2.4-tri.md).

Why EXRUN: one hook word, a call-site contract, 25 words, and it runs every frame for every fighter, so it proves the
stub cost on the hottest path. Full plan: P2.4 note §6.

Files: `tools/pkg/equiv.py` (`--allow-site`), `tools/pkg/engine/extra/*` (module v2-pilot), new
`tools/pkg/engine/p24_stubs.py` (guarded EBOOT + overlay writer), `tools/pkg/engine/install_engine.py` (`--no-idx`
with a new `--reg FILE`), `tools/pkg/engine/find_status.py` (status layout 2), host tests in `tools/pkg/engine/test/`.
Disc: `dumps/ULUS10566-P24-exrun.iso` (copy of the oracle).

Steps:
1. Module: split the start-up so the EXTRA.IDX state and the registry/stub state are independent (a layout-R pilot
   disc has no EXTRA.IDX). Load EXTRA.REG (ENGINE.md §6 rules). Publish rows and REG_PTR, then **REG_COUNT last**.
   Then the stub writer: check the XSTB header at 0x089A8B24, check `fallback_lo <= FN_PTR[0] < fallback_hi`, keep the
   old value as `vanilla[0]`, store `&wrap_exrun` (one data word), read back. Counters `stub_calls[n]` in status v2.
2. `wrap_exrun` + `beh_exrun`: owner row has EX_RUN, motion u16 +0x180 == 2, EX predicate FUN_08b34378 → run speed
   +0xBC × `ex_run_mult` (Sora 1.3984375 = the float the old patch built). Then it jumps back into the game at
   0x088374B0 with the registers the game expects, ra untouched.
3. Host tests: owner 33 + motion 2 + EX → ×1.3984375; owner 13, motion ≠ 2, not EX, no registry, feature off →
   unchanged; the writer refuses a pointer outside the fallback range and a wrong magic.
4. EBOOT 0x089A8B24-0x089A8B94 (28 words): header, REG_PTR, REG_COUNT, FN_PTR[0], STUB_0, FALLBACK_0, REG_ROW, 1 spare
   (ENGINE.md v2 item 1). Overlay site B 0x08B2D380: the hook call now goes to the stub at 0x089A8B48 (the store
   after it is unchanged).
5. `install_engine.py dumps/ULUS10566-P24-exrun.iso --no-idx --reg <Sora EXTRA.REG>`
   (EXTRA.REG = `tools/dlc/registry/out/sora.EXTRA.REG`, sha 88540de8…42a6).

Pass checks:
- Static: equiv vs the oracle shows only the 28 EBOOT words, the 1 overlay word, the P0.2 loader words,
  EXTRA.PRX / EXTRA.REG and directory/PVD records; owner-33 compare scan 16 → 15 (0x089A8B34 gone); two module builds same sha.
- Runtime: `find_status.py 41336` → state −1 (no index, normal), reg_state 2, stub_state 2, stub_written 0x1;
  stub_calls[0] stays 0 in menus and rises about 60/s per fighter in battle. `ppexspeed.py` EX / normal = 1.40 ± 0.01,
  and **the same runs on the oracle give the same numbers**. Cloud = 1.00. Module removed (rollback) → Sora 1.00, no
  crash. Module but no EXTRA.REG → reg_state −1, stub_state 1, 1.00. Busy ticks per frame within noise of the oracle.
  One strict battle without bad accesses. Then one EX battle on Mat's Vita (first data-indirect stub on hardware).

### 5.2 Installer row generator (P2.3 step 1)

**DONE 2026-10-20 (static), [P2.3-rowgen.md](../notes/phase2/P2.3-rowgen.md):** `tools/pkg/rowgen.py` (18 tables,
IDENTICAL to packages/sora-R4 and the oracle), test disc `dumps/ULUS10566-P23-rowgen.iso` sha = the oracle, equiv
IDENTICAL. The pass-check command is `rowgen.py check --pkg packages/sora-R4 --registry sora` (not `--check PKG`).
Step 5 below (installer uses rowgen) = P2.3-rowgen §7, waits for install*.py.

Goal: the installer computes the "data-in-code" rows from registry values, instead of carrying hand-written owner-33
addresses. Sora's values do not change, so the disc must stay **IDENTICAL** to the oracle. This proves the generator
before any code moves. Full detail: P2.3 note §2 (D-items) and §4 step 1.

Tables (VA, row, index; Sora's rows already sit in `packages/sora-R4/rows/<table>.json` as `ns img:<IMAGE>` replace rows):

| id | table | where | row | owner 34 |
|---|---|---|---|---|
| D1 | scenario_names | E 0x089CF350 + 4·o | u16 name, u16 manikin name | free |
| D2 | start_preset_table | E 0x089CB7E8 + 4·o | i32 preset | free (−1) |
| D3 | labyrinth_face | M 0x08B4173C + 6·o | u16 icon, u16, i16 | free |
| D5 | name-key pointers ×5 | E 0x089D6CA8[o], B 0x08AFBC68[o], M 0x089EA3C4 / 0x089EC56C / 0x08B57FBC [o−1] | u32 pointer | slot free, key string needs a home |
| D6 | opp_info_name | B 0x08AFB6E8 + 8·o | s32 name, s32 manikin | free (last row) |
| D7 | oq_slot_tables | M full name 0x08A544E0 + 4·o, banner 0x08A6B394 + 2·o, party row 0x08A6CAD0 + 6·o | u32 / u16 / 3 × u16 | free (pair word: no) |
| D8 | unlock_table | E 0x089D7BE0, 20-B rows, −1 end | owner, unlock flag, costume 2, costume 3, SEEN | 1 row left |
| D12 | grwp | system.bin (already a package row) | — | free |
| D14 | immediates | ablt cap E 0x088B1CF0; Jukebox caps M 0x08A36F20/2C/40, 0x08A37078/84/90/98; drop words E 0x088F6C04 / 0x088F9CA4 / 0x08929060 (0x7F only if a package owns 33); friend-card caps E 0x088F523C / 0x088F52A0 | — | computed |

Steps:
1. Add a machine-readable table spec to `tools/dlc/owner_tables.json` (per table: `base_va`, `stride`, `index_base`,
   `fmt`, `max_owner`) — single writer, claim it first (P2.3 Q10).
2. Add the missing registry source fields (P2.3 Q9): `start_preset`, `labyrinth_icon`, `records_icon`,
   `manikin_name` (default = name_index). `pic_slot_party` is redundant (= pic_slot + 1).
3. New tool (proposal: `tools/pkg/rowgen.py`; do not touch `tools/pkg/install*.py` while the pilot helper holds them):
   registry sources + table spec → img: rows in the package row format. A `--check PKG` mode compares with the
   package's rows.
4. Refuse rows where the table has no room for that owner (D4 records_icons, D9 qb_grid_rows, D10 select_panel_list,
   D11 ex_mode_page are full for owner 34 → P2.7), with a clear message.
5. Later, when `install*.py` is free: the installer uses rowgen instead of the stored owner-33 rows.

Pass checks: `rowgen --check packages/sora-R4` = every generated row equals the stored one (va, old_raw, raw);
a disc installed from generated rows → `equiv.py` vs the oracle **IDENTICAL**; `owner_names.py` and `owner_rows.py`
on that disc PASS for 33. Runtime: only the strict smoke (PACKAGE-ACCEPTANCE §E), because the bytes are identical.

### 5.3 The two in-place name rewrites (P2.3 step 2: C1 + C2)

**DONE 2026-10-20 (static + strict runtime), [P2.3-names.md](../notes/phase2/P2.3-names.md):** `tools/pkg/p23_names.py`
(moved 2026-10-21 to `tools/pkg/engine/patches/p23_names.py`, old path = wrapper)
(guarded, `--dry`/`--rollback`/`--sim`), test disc `dumps/ULUS10566-P23-names.iso` (not p23b-names) sha b73af9e1…4e2c;
equiv IDENTICAL with `--allow-site name_index_eboot --allow-site OVL_MENU_APP:0x08a1d7f8-0x08a1d83c` (C2 is 17 words:
code_sites.json `network_name_hook` must widen to 0x08a1d83c); owner-33 compare scan 16 → 14; allow-list bounds 0x088D6254
(the "owner < 35" bound) and 0x088D6270 (the "owner ≥ 33" bound); owner_names 1..33 PASS; Records / Jukebox / Friend Card show
"Sora", controls unchanged, per-frame cost = oracle. C2 words as assembled are in the note (§2). The breakpoint
check below is now: bp at 0x088D6278 (delay slot) → result = a0 ? v0 : a1.

Goal: one name function for the whole game, reading the D1 row; no registry, no new space, vanilla cost.

- **C1 name_index_eboot**, EBOOT FUN_088D6254 (11 words, leaf). Replaces the transitional patch
  `packages/sora-R4/patches/name_index_eboot.json`. New 10 words (described in the P2.3 note): an owner of 35 or
  more is treated as owner 0; the function reads both the game's own table at 0x089CC020 and the D1 row
  (scenario_names[o].name), then returns the D1 value for owners 33 and up.
  Owners 0..32 → vanilla table; 33..34 → the scenario_names row; anything else → table[0] = −1 (vanilla).
- **C2 network_name_hook**, menu FUN_08A1D7F8 (17 words, non-leaf). Replace the owner-33 test with a call to C1 (save the
  argument, call 0x088D6254 with the owner, restore, use the result) + a 2-word owner-0 guard (vanilla owner 0 reads
  0 = "WoL", C1 gives −1). ≈ 17 words, fits. Exact words not assembled yet. Keep the guard unless P2.3 Q4 proves
  owner 0 never reaches it.
- Files: the new words are an engine-base patch, not a Sora patch: a patch file + a guarded writer with the same rules
  as `p24_stubs.py` (assert old words = the R4 words or the new words; `--dry`, `--rollback`; refuse the clean dump
  and the oracle). Put them under `tools/pkg/engine/patches/` once the pilot helper releases `tools/pkg/engine/**`.
  Test disc: `dumps/ULUS10566-p23b-names.iso` (copy of the oracle).

Pass checks:
- Static: equiv shows only 0x088D6254.. and 0x08A1D7FC.. (`--allow-site name_index_eboot,network_name_hook`); owner-33 compare scan
  16 → 14 (0x088D625C and 0x08A1D80C gone; C1's "owner ≥ 33" bound goes on the allow-list); `owner_names.py --owners 33` PASS.
- Runtime (control: Cloud on the same screen): Museum → Records with a save that has battles as Sora → row "Sora";
  breakpoint 0x088D6278 with a0 = 33 → v0 = 63; Communications → Friend Card favourite = Sora → "Sora"; Ghost picker;
  Labyrinth party names; Quick Battle Opponent Info "Lv… Sora"; per-screen tick count (B15) = oracle.
