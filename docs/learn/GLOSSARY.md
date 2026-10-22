# Glossary

Every word used in these docs, in plain language. Sorted A–Z. The chapter in brackets is where
it's explained in more detail. The engine and package words of Phase 2 have their own section at
the end: [Phase 2 engine and package terms](#phase-2-engine-and-package-terms).

---

**0x… (hex)** — a number written in base 16 (digits 0–9 then a–f). `0x10` = 16, `0x800` = 2048.
Programmers use it because it lines up with bytes. [1]

**+0x10 (offset)** — "16 bytes from the start of this thing". Used to say where a field sits
inside a row or file. [1]

**ablt** — the **ability table** in `system.bin`. One 40-byte row per equippable ability:
owner, name id, description id, action id, CP cost, type. [8]

**action / action id** — one move recipe in a fighter's `comb` table. Equipping an ability
switches its action on. [4]

**ADPCM / VAG** — the PSP's simple sound compression (about 4× smaller). Sound banks use it. [5]

**Allegrex** — Sony's version of the MIPS CPU inside the PSP. [7]

**amas** — a table of "master this ability to learn that one". Every owner needs a row or the
Customization screen freezes. [8]

**ANM** — a flipbook inside an effects package: steps through frames of a texture sheet. [6]

**anchor (effect)** — where an effect is stuck: a model name + a bone in its FEPA row. Without a
model name it floats in the world. [6]

**ARC** — a box format (`ARC\x01`) holding labelled **chunks**. Fighter files are ARCs. [1]

**assist** — a helper fighter who jumps in for one attack (R+△ in battle). Aerith was only an
assist in 012. [2]

**at3 / ATRAC3** — Sony's sound format for spoken lines. We encode with `tools/atracdenc`. [5]

**atkp** — the **hit table** in a fighter's file: one row per hit with power, reaction and
knockback. [4]

**AUTHOR (spot33_chain)** — writing our own script block: keep a template's "plumbing", add own
hits at KH2's real hit frames. Opposite of COPY. [4]

**bake** — play a KH2 animation through KH2's own (emulated) animation code and save every
bone's position for every frame. [3]

**bank (sound bank)** — a "jukebox": a file holding many numbered sounds. See **SSCF**. [5]

**bank base** — the first sound number a bank answers to (Cloud's weapon bank: 2,200,000). A
sound id = base + slot. [5]

**BAR** — KH2's box format (like ARC). [6]

**battle overlay** — `OVL_BATTLE_APP.ELF`, the fight code, loaded only during battles. [7]

**bind pose** — the pose the skin was glued to the bones in (arms ~45° down in Dissidia). [3]

**binary search** — finding an item in a sorted list by checking the middle and halving. Why
many tables must stay **sorted by id**. [1]

**bisect** — finding which change broke something by testing halves. [9]

**block (script block)** — one animation's script in `p_se` type 8. Its number = the GMO motion
number. [4]

**bone** — one invisible stick of the skeleton. The skin follows bones. [3]

**Bravery / HP** — Dissidia's two attack kinds. Bravery attacks (◯) steal points; HP attacks (□)
turn your Bravery into damage. [4]

**breakpoint** — a "pause here" marker in the debugger. **CPU breakpoint** = when code at an
address runs; **memory breakpoint** = when an address is read or written. [9]

**build / build step** — running scripts to make the final disc; one script = one step. [10]

**byte** — the smallest piece of a file; holds 0–255. [1]

**camera model** — a small GMO inside each battle file (`d_se` type 2) with the intro/win camera
paths. Sora's was Cloud's, so the intro aimed at Cloud's height. [3]

**chrl** — level tables: which ability is learned at which level. [8]

**chrp** — one 144-byte row per character in `system.bin`: voice key, voice sound ids, EX bonuses. [2]

**chunk** — one labelled piece inside an ARC box (`comb`, `atkp`, `snd_`, `effe` …). [1]

**clash** — two fighters using the same id (sound bank, effect package, texture key), so one
steals or loses the other's data. [2]

**code cave** — an unused spot in memory where we put our own code. [7]

**Codex** — OpenAI's coding agent ("ChatGPT" in some notes); Mat's second AI helper, makes
assets offline. [11]

**comb** — a fighter's **action table**: combo recipes listing pieces in order. [4]

**component (effect node)** — one property of an effect node: position, scale, colour, which
mesh to draw … [6]

**COPY (spot33_chain)** — using a Cloud script block as is (keeps Cloud's hit pattern). [4]

**CPU** — the processor. Also "the CPU" = the computer-controlled opponent. [7] [9]

**CRC-32/BZIP2** — the "blender" that turns a file name into its hash number. [1]

**CURRENT-BUILD.md** — `docs/CURRENT-BUILD.md` (a private working file), names the newest disc and the last smoke-tested
one. [10]

**debugger** — a tool to look inside a running program (read memory, pause, step). PPSSPP has a
remote one. [9]

**decompile** — turning machine code back into C-like readable text (Ghidra does this). [7]

**delay slot** — on MIPS, the instruction right after a jump still runs. Hooks must allow for it. [7]

**DPD / DPX / PAX** — KH2's effect file layers (PAX = pack, DPX = effect list, DPD = particle data
with textures and programs). [6]

**dry run** — a script reports what it would change but writes nothing. [10]

**d_se** — a battle-file chunk; type 2 is the fighter's camera model. [3]

**EBOOT (EBOOT.BIN)** — the game's main program. Encrypted on the disc; we use the decrypted copy. [7]

**effe** — the effects chunk of a battle file (an MPK of `.fep`, `.feb`, `.fxseb`). Must stay
**848,640 bytes**. [6]

**effect leaf** — one effect recipe inside a FEP (e.g. `FIGA_HIT_WALL`), a tree of nodes. [6]

**ELF** — a standard program file format (the overlays are ELF files). [7]

**emulator** — a program that pretends to be a console (PPSSPP pretends to be a PSP). [9]

**event / op** — one line of an animation script. Main events run from frame A to B; one-shots
fire once. [4]

**EX Burst** — the super move after EX Mode (Cloud's Omnislash code, Sora's KH2 Limit look). [4]

**EX gauge** — fills during a fight; full → R+□ = EX Mode. Float at `*(fighter+0x52C)+0x18`, 0–10,000. [4]

**EX Mode** — a powered-up state (Sora: Ultima Weapon, "LIGHT!", Reflect guard). [4]

**exex / cosx** — small per-outfit files: EX Mode info (aura) / costume info. [2]

**f32 / float** — a 4-byte number with a decimal point. [1]

**fcurve** — one bone's movement over time for one property (move / turn / size), stored as keys. [3]

**FEP** — Dissidia's **effects package**: textures (TEX), meshes (MDL), flipbooks (ANM) and effect
leaves. Each has a global id. [6]

**FEP id** — the package's global number (Cloud `0x311C0000`, Sora `0x31280000`). Must be unique. [6]

**FEPA (.feb)** — the effect table: "effect id N = leaf L, this size, attached here". [6]

**file offset** — a position in a file on disc (vs. an address in memory). [7]

**Flatpak** — the way PPSSPP is installed on Mat's Linux. Run: `flatpak run org.ppsspp.PPSSPP`. [9]

**FOLLOW / MATCH** — `kh2_combo.py` options for EX Burst shots: copy Cloud's placement around
the foe / blend the weapon to Cloud's sword path at each hit. [3] [4]

**frame** — one moment of an animation (30 per second) or of a script (60 per second). [3]

**function (FUN_…)** — a named piece of code; Ghidra names them by address. [7]

**FXSE (.fxseb)** — the table of sounds tied to effects. [5] [6]

**general skill** — an ability every fighter can use (owner byte 0x40 / 0xFF). [8]

**Ghidra / ghidra-allegrex** — the free reverse-engineering tool and its PSP plugin. [7]

**GIM** — the PSP's picture format (`MIG.00.1PSP`), usually 256 colours. [3] [8]

**global texture** — an effect texture shared by every fighter (keys `0xF00000NN`). Never edit. [6]

**glTF / GLB** — a standard 3D format Blender opens; our workbench format. [3]

**GMO** — the PSP's 3D model format (`OMG.00.1PSP`). A fighter's GMO holds the skin **and** all
animations. [3]

**hash** — a "fingerprint" number made from a file name. PACKAGE_INFO stores hashes, not names. [1]

**hitbox** — an invisible sphere that can hurt the foe while it's switched on. [4]

**hit-shape group** — a numbered set of hit spheres in `p_se` type 5 (e.g. 0x30 = on the
Keyblade, 0x06 = big sphere around the body). [4]

**hook** — a small change in the original code that jumps to our code (a detour). [7]

**hurtbox** — the spheres on your own body that can get hit. [4]

**idempotent / re-runnable** — running a step twice is the same as once. [10]

**IK (inverse kinematics)** — "put the hand here" and the arm angles are worked out. KH2 uses it;
that's why we bake. [3]

**index8** — a picture whose pixels are numbers into a 256-colour palette. [3]

**instruction** — one 4-byte CPU command. [7]

**ISO** — a file that is a copy of a whole disc. Ours: `dumps/ULUS10566.iso` (never written). [1]

**KH2 / KH1.5+2.5** — Kingdom Hearts II (from Mat's own PC copy of the 1.5+2.5 collection), the
source of Sora. [3]

**key / keyframe** — a saved pose at one frame; the in-betweens are filled in automatically. [3]

**key (resource key)** — a texture/mesh's registration number inside a FEP. Must not be shared
with Cloud ("rekey"). [6]

**learned list** — the list in a save record of every ability a fighter knows (max 150). [8]

**little-endian** — the PSP stores the smallest byte first, so `00 00 1c 31` = `0x311C0000`. [1]

**loadout** — the equipped abilities of one set (3 ground + 3 air Bravery, 3 + 3 HP). [8]

**loop flag** — a motion's (or effect tree's) "repeat forever" marker. [3] [6]

**lunge (op 0x39)** — a script event that moves the attacker toward the foe. Keeps combos close. [4]

**magi** — the projectile table: fireballs, meteors, shockwaves. Rows sorted by id. [4]

**magic word** — the first bytes of a file that say its type (`ARC\x01`, `SSCF`, `OMG.00.1PSP`). [1]

**MDL** — a tiny mesh inside an effects package (cards, rings, tubes). [6]

**memory budget** — the fixed amount of memory the game gives a fighter's model / effects / sounds.
Go over and it crashes or freezes. [3] [5] [6]

**menu pak / mess pak** — box formats for menu pictures / menu text. [8]

**mesh / skin** — the visible surface of a model, made of triangles. [3]

**MIPS** — the CPU family of the PSP. [7]

**mirror match** — the same fighter on both sides (Sora vs Sora). Loads two copies → more memory. [5]

**mlng** — a multi-language text block (6 languages; the US game uses block 0). [8]

**model box** — the shared scale + offset all vertex positions are squeezed into. [3]

**motion** — Dissidia's word for one animation inside the GMO. [3]

**motion id** — the game's number for "what the fighter is doing now" (1 idle, 470 block,
10000+ attacks), at fighter +0x180. [3]

**motion slot** — a named place for an animation (`_000A` idle, `_910A` win …). [3]

**MPK** — a box format (`MPK `) with named members. [1]

**node (effect)** — one part of an effect tree (an emitter, a mesh, a flash). [6]

**objentry** — the model table (68-byte rows: id, owner, costume, file name) that says which model and battle
file each owner loads; looked up by id or by (owner, costume). [2]

**objx** — a fighter's **battle file** (`obj/p_sev120.objx` for Sora). [2]

**one-shot** — a script event that fires once at a frame (sound, effect, end). [4]

**op (opcode)** — the number saying what kind of script event a line is (`0x00` hitbox, `0x19`
effect…). [4]

**overlay** — extra code loaded into a shared memory area only when needed (battle or menu). [7]

**owner (number)** — a fighter's number (Cloud 13, Lightning 31, Sora 33). Vanilla playable fighters are
1-32; 34 (Cosmos's number) is the one more free number. Most tables are indexed by it. [2] [14]

**p_se** — the tag of five fighter-file chunks: type 5 hit shapes, 6 bone physics, 7 motion table,
8 scripts, 9 "hibg". [2] [4]

**p_se script** — see **block**: a timed list of events for one animation. [4]

**PACKAGE.BIN** — the 1 GB "filing cabinet" holding 11,043 game files. [1]

**PACKAGE_INFO.BIN** — the cabinet's index cards: hash, sector, size. [1]

**palette** — the list of colours (or bones) that numbers point into. [3]

**parent (bone)** — the bone another bone hangs from. Must come earlier in the bone list. [3]

**piece** — one swing; a `plya` row. [4]

**pkg_put.py** — the tool that puts a file into a disc copy (in place, or at the end). [1]

**plya** — the attack-pieces table: one row per swing with its rules and motion id. [4]

**pose script** — a Python file in `tools/poses/` describing key poses for `pose_author.py`. [3]

**PPSSPP** — the PSP emulator we test in. [9]

**projectile** — something an attack throws (fireball, bolt). See **magi**. [4]

**PROVEN / BUILT / GUESS** — how sure we are: seen working in the game / made but not seen / an
educated guess. [00]

**PSP** — Sony's PlayStation Portable (2004). Very little memory. [1]

**PVD** — the disc's front page with its total size; updated when files are appended. [1]

**quaternion** — a maths way to store a rotation without glitches. Rotation fcurves use them. [3]

**RAM / RAM dump** — the PSP's working memory / a saved copy of all of it. [9]

**reaction** — what a hit does to the foe (flinch, push back, crumple, blow away). atkp +0x05. [4]

**Reflect** — Sora's EX Mode guard (KH2 move): can't be broken, blocks every projectile. Damage
return not working yet. [7]

**register** — a tiny storage slot inside the CPU (`a0`, `s0`, `ra`, `sp`). [7]

**rekey** — giving Sora's effect textures/meshes their own keys so they never share Cloud's. [6]

**retarget** — copy an animation from one skeleton (KH2) to another (Dissidia). [3]

**root** — the bone (or point `0x4000`) for the whole character's position on the floor. [3] [4]

**script frame** — a frame of an animation script, 60 per second (= 2 × motion frame). [3]

**sector** — a 2,048-byte block of a disc. [1]

**skeleton** — all bones together. Dissidia's has 54. [3]

**slot** — a numbered or named place: a sound slot in a bank, a motion slot in a model, a roster
slot (#33), an equipment slot. [2] [3] [5]

**smoke test** — a quick "does it start and not crash" test. [10]

**snd_** — the weapon/body sound bank chunk in a battle file. Keep ≤ ~540 KB. [5]

**spot33_*.py** — our build steps for roster slot #33 (Sora). [10]

**SSCF** — Dissidia's sound bank format (used by `snd_` and the voice `.scd` files). [5]

**stage A/B/C (effects)** — quick fixes / KH2 look inside existing effects / a full KH2 effect
converter. [6]

**STUBS** — Cloud motion slots Sora no longer uses, emptied to save memory. [3]

**swizzle** — the shuffled pixel order the PSP's graphics chip likes. [3]

**system.bin** — the game's big rule book (ARC inside `main.bin`): chrp, ablt, amas, chrl… [1]

**TEX** — a texture inside an effects package. [6]

**texture** — a picture painted on a mesh. [3]

**TexAnm** — texture animation in a GMO (e.g. eyes blinking). [3]

**u8 / u16 / u32** — whole numbers of 1 / 2 / 4 bytes (s16/i32 = can be negative). [1]

**ULUS10566** — the US Dissidia 012 duodecim disc ID. [1]

**variant** — one script block serving several moves; events marked with a variant number only
run in that variant. [4]

**VA (virtual address)** — an address in PSP memory (e.g. `0x0880A384`). [7]

**vertex / vertices** — the corner points of a mesh's triangles. [3]

**VOLD** — the spoken-line list format (`voice_load_<KEY>.bin`): clip, line id, moment, condition. [5]

**vtable** — a table of function addresses an object carries; fighters have `0x08B3A9A8` at
+0x544, which is how tools find them in RAM. [7] [9]

**weight** — how strongly a vertex follows a bone (128 = 100%). [3]

**wep0 / wep1** — the two weapon parts: normal weapon (Kingdom Key) and EX Mode weapon (Ultima
Weapon). [3]

**XOR (scrambling)** — mixing each byte with a byte from a key; doing it again un-mixes it. Used on
subtitles and menu text. [5] [8]

**xdelta** — a patch file holding only the differences between two files. Our release format during the Sora
build; release 1.0 uses the same idea in the standard VCDIFF format (see **VCDIFF** below). [10]

---

## Phase 2 engine and package terms

Added 2026-10-22. The teaching chapter for these terms is
[16 — The engine and the registry](15-engine-and-registry.md). Where a term is explained: [modding/OVERVIEW.md](../modding/OVERVIEW.md) (O),
[ENGINE.md](../ENGINE.md) (E), [PACKAGE-FORMAT.md](../PACKAGE-FORMAT.md) (P),
[modding/TESTING.md](../modding/TESTING.md) (T), or a chapter number.

**16-byte stack rule** — module C code must call game code only through an **aligning thunk** that sets the
stack pointer to a multiple of 16. The compiler keeps only 8; the game's vector stores (`sv.q`) need 16. Breaking it
froze the emulator once. Checked by `tools/qa/acceptance/stack_rule.py`. [7] (T)

**abi_hash** — a hash of the stub list, stored on the disc (today `0x2F2EAE84`). The module refuses a disc whose
stub list it does not know. (E)

**acceptance kit / acceptance list** — the checks every package and release candidate must pass:
`docs/PACKAGE-ACCEPTANCE.md` (the list) and `tools/qa/acceptance/` (the tools). (T)

**allow-site** — a code site that `equiv.py --allow-site ID` is told may differ between two discs. Everything else
must be identical. The count of allowed words is checked exactly (`--expect-words`). (T)

**base-image rule** — inside the project, the exact base ISO of a build (path + SHA-256) is confirmed in
the project's internal question queue (`codex/QUESTIONS.md`, private) before any build or patch. [11]

**CLAIM / DONE** — the lines a helper adds to `codex/QUESTIONS.md` before it starts (what it will touch) and when it
finishes (the results). [11]

**code site / `code_sites.json`** — a named place in the game code that our patches change (for example `p27_grid`),
listed in `tools/pkg/code_sites.json`. Ids are only added, never changed. (T)

**codec (package)** — how a package stores its edits to one kind of shared table, and how the installer merges
them: `odir.v1`, `acab.v1`, `text.v1`, `grid-id.v1`, `positional.v1`, `append.v1`, `pak-fill.v1`, `bytes.v1`. (P §16)

**engine** — the one-time set of changes that lets packages work: the module loader patch, the stub table, the
per-owner tables, the module `EXTRA.PRX`. (O)

**engine package** — the engine stored as a package of its own (`packages/engine`, kind `engine`): `EXTRA.PRX`,
the module loader patch, the menu clock fix and about 890 code words whose "old" value is the clean game's. (O)

**equiv / equivalent** — `tools/pkg/equiv.py` compares two discs the way the game reads them. **Equivalent** = the
game reads the same bytes, and code differs only at the declared allow-sites. (T)

**EXTRA.IDX** — our own file list on the disc (`PSP_GAME/USRDIR/DATA/EXTRA.IDX`). The module answers the game's
file lookups from it first, so the game's own list can stay as shipped. [14] (E)

**EXTRA.PRX** — our own code module, written in C, at `PSP_GAME/USRDIR/DATA/MODULE/EXTRA.PRX`. The game's own module
loader starts it at boot. Engine 2.5.0 today. [7] (O)

**EXTRA.REG** — the registry file (`PSP_GAME/USRDIR/DATA/EXTRA.REG`): one 64-byte **registry row** per package
fighter, plus item, flag and string sections. Built by `tools/dlc/registry.py`. (E)

**fallback** — the copy of the original game instructions a stub jumps to when the module is missing or a package
does not use that feature. So the game stays vanilla without the module. [7] (E)

**feature bit** — a switch in a registry row that turns a behaviour on for one fighter (EX run, Reflect guard,
record slot …). (E)

**format 1.0 / format 1.1** — package format versions. 1.0 (release 1.0, layouts A/B) stores some edits by byte
position and carries owner-33 code patches. 1.1 (layout C) stores every edit by identity and carries no code
patches, so two packages can edit the same table. (P)

**GRD1** — the installer-written block in the EBOOT (`0x089C2140-0x089C2340`) that holds the Quick Battle /
select-grid rows: room for 34 cells per page. **GRID_CAP** is its small guard that limits a grid to 34 entries. (O)

**host test** — a test that runs our code on the PC, not in the emulator. The engine's C code is compiled for the PC;
the old MIPS code it replaced runs in `tools/pkg/engine/test/mips_emu.py`; the game calls of both are compared. [7] (T)

**identity key** — how format 1.1 names an edit: by what it is (owner, text entry, model id, picture id), never by
its final row number or byte offset. Final positions shift when a second package adds rows. (P §16)

**installer** — `tools/pkg/install.py CLEAN.iso OUT.iso PACKAGE …` (developers) or the patch app (players). It never
changes the original file and never overwrites an existing one. [10] (O)

**installer words (I-rows, I-imm)** — rows and instruction constants inside the game's code images that the
installer computes for the whole roster (list sizes, unlock rows, grid bounds …), instead of storing them in a
package. (O)

**KEY_POOL** — a small home in the OXT block (EBOOT `0x089A8D7C`) for the 6-letter key strings of new fighters. (E)

**layout pin** — a package's exact byte layout of a shared container, valid only while that package is the only
editor. With two editors the installer re-packs the container in the standard way. (P §16)

**layout R / A / B / C** — how a disc carries the fighter. **R**: reference build by `build_sora.sh`. **A**: the
first installer output, same shape. **B**: release 1.0; the game's file list stays clean, files via `EXTRA.IDX`.
**C**: the engine layout; no owner-33 code at all. [10] (O)

**menu_clock** — the fix that keeps menus at 333 MHz (it removed most of the menu lag on the Vita); part of the
engine package. (O)

**module** — see **EXTRA.PRX**.

**oracle** — the frozen reference disc `dumps/ULUS10566-P2-oracle-R4.iso` (release 1.0 plus the 1.0.1 fix). Every
Phase 2 disc is compared with it. (T)

**OXT (owner-extension tables)** — small tables in the EBOOT (`0x089A8B94-0x089A8F0C`), indexed by owner, written by
the installer: vanilla values for owners 0-32, package values for 33 and 34. They replaced most "if owner is 33"
checks with no runtime code. [7] (O)

**owner_tables.json** — `tools/dlc/owner_tables.json`, the list of every per-fighter table and code site in the
game, with what a new owner needs there. Read it with `tools/dlc/owner_tables.py --owner 34`. [14]

**P2.n** — Phase 2 task number n (P2.0 to P2.13), listed on [ROADMAP.md](../ROADMAP.md).

**package** — one folder with everything one fighter (or the engine) adds to the clean game: `manifest.json`,
`registry.json`, `files/`, `rows/`. It holds data derived from the game, so it is never published raw. (P)

**patch app** — the program players use (Windows, macOS, Linux): it decrypts the player's own EBOOT, applies the
release patch and checks the result's SHA-256. Source: <https://github.com/MatNyaga/sora-fan-patch>. [10]

**per-frame path** — code that runs every frame (EX run speed, the EX Burst bar, many menu draws). It must stay
cheap: no loops over packages, no file access. (E)

**profile (acceptance)** — a JSON file in `tools/qa/acceptance/profiles/` that says what one kind of disc must look
like (owners, allowed differences, frozen module, reference sha). (T)

**record slot** — where a package fighter's saved record lives: the bytes of one friend-card slot, slot = 57 − owner
(Sora 24, owner 34 23). Each extra fighter lowers the friend-card limit by one. (O)

**REG_ROW** — the EBOOT helper "give me the registry row of owner N" (or 0 when there is none). (E)

**registry row** — one fighter's 64-byte row in `EXTRA.REG`: owner, name index, record slot, pictures, feature bits,
parameters. (E)

**registry source** — the JSON file a registry row is built from (`tools/dlc/registry/<id>.json`; in a 1.1 package:
`registry.json`). Every value is a pair `[value, "where it comes from"]`. (P)

**rowgen** — `tools/pkg/rowgen.py`, the generator of the per-owner rows and installer words for a roster. With only
Sora it reproduces the release bytes exactly. (O)

**SRC1** — the installer-written save-record block in the EBOOT (`0x089C2340-0x089C2508`): friend-card cap and
catch-up markers for every package fighter. (O)

**status block** — the module's state in memory (signature `XTRA`), read with `tools/pkg/engine/find_status.py
PORT` from a running emulator. (E) (T)

**strict mode** — PPSSPP with bad memory reads stopping the game instead of reading 0 (`--env=STRICT=1`), closer to
real hardware. (T)

**stub** — a fixed 4-instruction jump in the EBOOT (`lui at / lw at,FN_PTR / jr at / nop`). It goes into the module
if the module filled the pointer, else into the fallback. The module only writes pointers, never instructions. [7] (E)

**test fighter** — a throw-away Cloud copy on owner 34 (key `tst034`, registry `test34.json`), never released; it
proves that a second fighter needs no new fighter code (task P2.9). (O)

**transitional patch** — a format-1.0 package file with owner-33 code (`patches/*.json`). Phase 2 retires them; Sora's
format-1.1 package has none. (P)

**VCDIFF** — the standard delta format (RFC 3284) of release 1.0's `patch.vcdiff`: only our changes against the
clean disc. [10]

**XSTB** — the header of the stub table, at EBOOT `0x089A8B24`. It tells the module where the stubs, pointers and
fallbacks are. [7] (E)

Back to [00 — Start here](00-START-HERE.md).
