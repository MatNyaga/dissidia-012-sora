# Chapter 12 — Lessons learned: things that broke, and why

This is the most valuable chapter. Each story is: **what we saw → why it happened → the rule
now.** Most rules are already built into the scripts. Grouped by topic.

---

## A. Memory: the PSP is small

### A1. The effects file must never grow (the big freeze)
- **Saw:** test171 froze PPSSPP on the very first Bravery attack.
- **Why:** three new KH2 textures made Sora's `effe` chunk +27.9 KB bigger (876,560 B instead of
  848,640). A bisect with Mat proved it: same disc with the old-size `effe` worked; the sound
  bank and model were not the cause. The fighter's effect memory is a fixed budget.
- **Rule:** `effe` stays **exactly 848,640 bytes**. Overwrite textures/meshes Sora never draws.
  Every effect script asserts the size.

### A2. The sound bank got too big → the Break sound and win line vanished
- **Saw:** in Sora vs Sora (tests 209/210), no BREAK sound and no win line.
- **Why:** the Keyblade sounds grew Sora's `snd_` from 538 KB to 606 KB. Two copies in a mirror
  match left no room, and the game didn't load a 436,580-byte shared battle bank (Break = its
  slots 96 and 57).
- **Rule:** keep `snd_` ≤ ~540 KB. `spot33_sndtrim.py` silences unused Cloud slots (→ 498,528 B).

### A3. The keychain v1 crash (model out of memory)
- **Saw:** test183 crashed at battle start: "Invalid Memory Access, PC 0885c8a0".
- **Why:** 4 new bones and their curves made the model +19 KB. The crash is inside a memory
  allocator (`FUN_0885c6cc`): an allocation failed. Same disc without it worked.
- **Rule:** don't grow the model. Reuse what exists.

### A4. Bigger EX Burst motions crashed the same way (test215)
- **Saw:** the identical crash after taking Codex's Trinity motions (2,506,640 → 2,523,344 B).
- **Fix:** `gmo_thin.py` keeps every 2nd key of the win-camera motion (−27 KB). Then it played.
- **Rule:** model ≤ ~2,506,640 bytes. Check the size before every test. (Test 70's 2.82 MB
  two-skin model hung on a white screen.)

---

## B. Copying Cloud: everything with an ID clashes

### B1. Cloud's effects vanished in Cloud vs Sora
- **Why:** Sora's effects package had Cloud's id `0x311C0000`. The game takes one package per id;
  the second fighter got none → no trails, no meteors, no effect sounds.
- **Rule:** own FEP id (`spot33_effects.py` → `0x31280000`) **and** own resource keys (rekey).

### B2. Changing only the sound bank headers made Sora silent (test 82)
- **Why:** the bank moved, but every script still asked for the old numbers. Sound ids are
  absolute numbers *inside the data*.
- **Rule:** move headers and every request together (`spot33_soundids.py`), and run it **last**.

### B3. A CPU Sora drawn as Cloud
- **Why:** the 2P/3P outfit files were still Cloud's. A mirror match uses them.
- **Rule:** `spot33_2p.py` copies 1P over 2P/3P.

---

## C. Effects

### C1. Copying Lightning's thunder froze the game
- **Saw:** test199/200 froze on the first Bravery swing.
- **Why (bisect A/B/C/D):** her effect *tree* uses node kinds Sora's package never has
  (0x150, 0xD0, 0x64). Her textures and meshes alone were fine. Her flipbook in Sora's ANM 10
  also froze Explosion (ANM 10 is shared).
- **Rule:** never transplant foreign trees or flipbooks. Copy *data* (textures, mesh vertices)
  into Sora's own slots.

### C2. Two numbering systems for effects
- **Saw:** "Firaga explosion" id 5 showed a tiny whoosh.
- **Why:** a projectile's effect number is a *bit number*; a script's op 0x19 uses the FEPA *id*.
  Id 5 = Cloud's air-recover whoosh. Firaga's blast = id 22.
- **Rule:** look ids up with `fep_dump.py`.

### C3. Effects that showed in the wrong place, or not at all
- **Why:** a FEPA row attaches to the fighter only if its **model name** is filled in. Copied
  rows had empty names. `hip` at (0,0,0) still didn't show; `root` with negative y (= up) did.
- **Rule:** model name + bone; copy how Cloud's own body effects are anchored.

### C4. "Bigger orbs" pushed them off camera
- **Why:** the 280% was the emitter's *transform* scale, not the sprite size.
- **Rule:** change one field per test; confirm what a field means before tuning it.

### C5. Fireballs that never left
- **Why:** the fireball's effect tree is marked LOOP (it normally dies with its projectile).
  Spawned by id, nothing killed it.
- **Rule:** effects spawned by id must be set to play once (`LOOP_OFF`).

### C6. Blizzaga "all black, kind of white"
- **Why:** a sprite *sheet* (many little pictures) was mapped onto a whole mesh.
- **Rule:** use a texture made to wrap a surface.

---

## D. Animations and moves

### D1. Two clocks: 60 vs 30
- **Why:** scripts count 60 frames a second; animations count 30. Test 51's swings were all late.
- **Rule:** script frame = 2 × animation frame. Tools take script frames.

### D2. The win pose repeated
- **Why:** a motion's frame range is its **loop** range.
- **Rule:** win/loss poses loop only their last few frames.

### D3. Finishers missed (loop flag)
- **Why:** our tool wrote "loop" into every motion.
- **Rule:** copy each slot's own loop flag.

### D4. Finishers missed (the hitbox follows the weapon)
- **Why (bisect):** hit spheres sit on `r_wep`. Sora's swing put the Keyblade elsewhere at the
  hit frame.
- **Rule:** blend the arm chain to Cloud's at the hit (`:match`), or author own hits with
  bigger front spheres where KH2's swing really is.

### D5. The camera "vanished" Sora in the win pose
- **Why:** the game takes the results camera from **motion 86** if it exists. Our first new slot
  became 86.
- **Rule:** motion 86 = a copy of the win pose (`_719A`); new slots start at 87.

### D6. "Stuck after the move"
- **Magnet Burst:** the script's end markers were later than the animation's end → hung in the air.
  **Rule:** last end marker ≤ 2 × the animation's last frame.
- **Upper Slash:** the piece's "motion after the move" was Cloud's *fall* motion → stuck
  falling on the ground. **Rule:** ground moves end in idle (plya +0x1e = 1).

### D7. Combos stopped after a starter
- **Why:** follow-ups come from the action that **started** the chain.
- **Rule:** every starter gets its own full follow-up list.

### D8. The CPU escaped combos
- **Why:** Sora's KH2 hurt clips were half as long as Cloud's (hit-stun seems to follow them),
  and distance grew with every hit.
- **Rule:** hurt clips as long as Cloud's; a lunge on every combo link.

### D9. Copied Cloud blocks don't look like KH2
- **Why:** COPY keeps Cloud's hit pattern (Finishing Leap looked like "Onion Knight's finisher":
  a long multi-hit window with blue sparks).
- **Rule:** AUTHOR own blocks at KH2's real hit moments.

### D10. The keychain was invisible (v2)
- **Why:** the engine computes bones **in list order**; the chain's bone came before its new
  parent.
- **Rule:** a child bone's index must be bigger than its parent's.

### D11. Guessed KH2 labels were wrong
- **Why:** first-pass guesses from motion shapes (Explosion, Aerial Finish, Dodge Slash …).
- **Rule:** check with Mat's KH2 video and KH2's ability ID order; ask Mat when unsure.

### D12. The Firaga fireball died at once
- **Why:** its spawn mode starts it at a *live effect* (the Fire charge glow) that only Cloud's
  Fire slot creates.
- **Rule:** spawn the anchor effect first, or use a spawn mode that doesn't need one.

---

## E. Text and pictures

### E1. Garbage subtitles (test 28)
- **Why:** the XOR key position depends on the **line id**, not the place in the file.
- **Rule:** compare the disc file with the game's decoded copy in RAM before trusting a guess.

### E2. Nobody's cutscene lines played (tests 64–80)
- **Why:** our ATRAC3 files wrote an "end sample" too close to the end of the data (the PSP
  skips 1,093 samples first and then ran past the end); the PSP rejected them
  (`BAD_CODEC_PARAMS`) and that silenced the intro/win/loss lines for **everyone** in the fight.
- **Rule:** pad and write the real sample count. Read PPSSPP's log when audio is silent.

### E3. Growing text tables garbled them
- **Why:** our tool misread the table header; the game decodes every entry in place.
- **Rule:** reuse developer placeholder entries; keep text files the same size.

### E4. Wrong descriptions ("WOL 15")
- **Why:** descriptions come from a *different file* than names.
- **Rule:** names = `ability.bin`, descriptions = `mess_pk_customize_ability_0.bin`.

### E5. The missing blue name band
- **Why:** the band samples a hidden 3×3 grey marker in the name picture's corner.
- **Rule:** keep a picture's helper pixels (`gim_markers.py`).

### E6. Customization froze on a white screen
- **Why:** no `amas` row for owner 33 → a menu loop ran over garbage.
- **Rule:** a new owner needs a row in every per-owner table. Find freezes by pausing the CPU and
  reading `pc`/`ra`.

---

## F. Game code

### F1. The "empty" memory gap wasn't empty
- **Why:** the overlay loader writes the overlay's ELF header right into it on every load.
- **Rule:** before using a cave, read the code that writes near it.

### F2. Re-running a hit on the attacker hung the game (Reflect hook 2)
- **Why:** the hit pipeline checks the victim's state and credits the original attacker;
  forcing it through once caused an endless loop.
- **Rule:** don't re-enter the hit pipeline. Build a damage event directly.

### F3. Ghidra hid code
- **Why:** one function was wrongly marked "never returns".
- **Rule:** if a decompiled function looks too short, check the disassembly.

### F4. ablt doesn't pick the move
- **Why:** it only switches on matching entries in the fighter's own action table.
- **Rule:** the move lives in the battle file's `comb`.

---

## G. Testing and safety

- **G1.** A breakpoint left behind by a killed tool froze the game on every sound. Tools clean up;
  restart PPSSPP if it happens.
- **G2.** Two debugger connections jam PPSSPP. One tool, one connection.
- **G3.** The debugger got slow because of the websocket Origin header, and because of debug-level
  logging. Both fixed.
- **G4.** Rebuilding a disc PPSSPP was running → beeps, no music. Never do that.
- **G5.** `pkill -f` killed our own shell. Kill by process id.
- **G6.** A whole-screen recording caught Mat's private browser. Only ever capture the game window.
- **G7.** Blind button lists wandered into Data Install and the Mognet calendar. Recognise the
  screen before pressing. Never press Square on the results screen (Save Replay).
- **G8.** Speech-to-text and tone detection on game audio fail: the music hides everything. Use
  breakpoints on the sound player instead.
- **G9.** A transcript said "YEAH!" but the clip was a 0.94 s KO groan. Check clip lengths.
- **G10.** The 100% save's quirks (Yuna "Lv 1") are not our bugs. Check before fixing.

---

## H. 2026-10-16 findings (each cost a freeze or a wrong build)

- **H1. "Unused" code needs proof.** The controller slot we called dead was Garland's EX Burst (we read the wrong
  chrp bytes). Check every character row, then prove "dead" with a probe disc (marker stubs + normal play;
  `notes/ex-burst-controller.md` §21). TRI now lives in dead EBOOT code at 0x089c1c8c.
- **H2. Effect files: keep 16-byte alignment.** The engine reads node init blocks with `lv.q` (needs 16-aligned
  memory). A rewrite that shifts later blobs by a non-multiple of 16 froze the game on the first attack
  (PC 0x08964eac, sword-trail draw). `fep.py` only 4-aligns; `spot33_magnet.align_layout()` keeps offset mod 16.
- **H3. Effect node serials must be dense 0..N-1.** The game indexes a table by them; gaps/repeats write past it.
- **H4. Effects draw from the node KEY blocks** (+0x24), not the start-value block. Magnet was invisible (key 0 still
  had the donor's 10 % scale / MDL 79); the barrier drew on its side (key 0 rotation 90°).
- **H5. plya flag bit 0 = "plunge, wait to land".** Magnet had it with no landing motion → Sora hung in the fall pose.
- **H6. CPU AI:** a global brain file (`battle_non_residing.bin` brai) needs an owner row for #33, plus a per-fighter
  `brat` move table; reach windows (plya) decide where the CPU casts. `notes/cpu-ai.md`.
- **H7. EX Mode banner/aura come from the costume files** (`.cosx` +0x38, `.exex`). The mirror-match CPU uses the 2P
  costume, so P2 showed Cloud's "Equipped Ultima Weapon!". `notes/p2-audit.md`.
- **H8. EX damage multiplier = chrp +0x0C flag bits** (Cloud's HP-scaled bonus; 0x400 adds flat ×1.5). `notes/ex-damage.md`.
- **H9. Museum/Records/Icons are data + one hard-coded list** (`collection_param.bin`, uicn, menu code 0x08A40880).
- **H10. Bisect with stacked discs.** test276 (AI only) vs test280 (AI + Magnet) found the Magnet freeze in one play.
- **H11. Placed spells:** magi type 11 = at the target's feet; K8 = pitch (+ down). Codex's Thunder went up (−89.9).
  A no-hit warning row with AI tag 0x14 makes the CPU dodge (Garland's method). `notes/thunder.md`.

## The meta-lessons

1. **Change one thing per test.** Every hard bug was found by bisecting.
2. **Write it down right away** (`notes/`, `HANDOFF.md`). Old discs get deleted; the notes stay.
3. **Scripts, not hand edits.** Re-runnable steps make full rebuilds safe.
4. **Static checks are not proof.** The game decides. Mat decides how it looks.
5. **When stuck, compare with what the game does for its own fighters** (Cloud's anchors,
   Exdeath's area spheres, Lightning's bolt, Onion Knight's camera height).

Next: [Chapter 13 — Open questions and what's next](13-open-questions.md).
