# Chapter 2 — A fighter's files, and roster slot #33

**The big idea:** every fighter is a bundle of files plus a few rows in the game's big rule
tables. The game had a hidden, unused fighter number: **#33**. We turned #33 into a full copy of
Cloud, gave it its own files, and then changed those files, bit by bit, into Sora. Because #33
has its *own* files, nothing we do to Sora touches the real Cloud.

---

## 2.1 Owner numbers and code names

Inside the game every fighter has an **owner number** (1 to 34). The word "owner" is used
because the ability table says which fighter "owns" each move.

| owner | code | fighter |
|---|---|---|
| 13 | `sev100` | Cloud |
| 31 | `gst130` | Lightning |
| 33 | `sev120` | (was Aerith, a helper only) → **Sora** |
| 23 | — | Chaos (no saved record) |
| 34 | `org800` | another hidden slot |

How the code names work:
- 3 letters = which Final Fantasy: `one two thr for fiv six sev eht nin ten`, `gst` = guests
  (the 012 newcomers), `org` = originals.
- 3 digits = the role: `100` hero, `200` villain, `110/120/130…` extra characters.
- So `sev100` = FF**7** hero = Cloud. `sev120` = the third FF7 character = Aerith's old key.

Why #33? In Dissidia 012, Aerith is only an **assist helper**, not a playable fighter. Her
number 33 already existed in every table (the character table `chrp` has 34 rows, the
ability table knows owners 1–34). But she had **no battle file** (`obj/p_sev120.objx` did
not exist). An empty seat with a name card on it. Perfect for a new fighter.

---

## 2.2 The files of one fighter (Cloud as the example)

| file | what it is |
|---|---|
| `obj/p_sev100.objx` | the **battle file**: moves, hits, scripts, sounds, effects, camera (1.35 MB) |
| `obj/P_SEV100_1P.gmo` | the **model**: body, weapons, textures and all 86 animations (~2 MB) |
| `obj/P_SEV100_2P.gmo`, `_3P.gmo` | other colour outfits (also used in mirror matches) |
| `obj/P_SEV100_1P.cosx` | 68 bytes of costume info |
| `obj/P_SEV100_1P.exex` | 88 bytes of EX Mode info (probably the EX aura) |
| `obj/p_sev100_a.objx`, `_w.objx` | smaller copies used for the assist (helper) version |
| `voice/EN/battle/voice_P_SEV100_00.scd` | the shout/grunt sound bank |
| `voice/EN/voice_load_P_SEV100.bin` | the list of spoken lines and when to say them |
| `voice/EN/battle/cl_battle_NN.at3` | the spoken lines themselves (one file each) |
| `menu/JP/battle/chara_image/P_SEV100_1P.gim` | the HUD face picture in battle |
| many `menu/...p_sev100_*.gim` | name pictures, select-screen art, faces |

We found this list by watching the game: `tools/scripts/ppnames.py` sets a breakpoint (a
"pause here" marker, see [Chapter 9](09-testing.md)) on the function that opens files, and logs
every name it opens during a fight. Result: `notes/files-loaded-spot33-battle.txt`.

Plus rows in the rule tables:
- **objentry** (`objentry.bin`): 68-byte rows. Owner, which model name to load (`P_SEV100_1P`),
  which battle file name (`p_sev100`).
- **chrp** (in `system.bin`): 144-byte row per character. The voice key `P_SEV100` at +0x74,
  and four voice sound ids at +0x7c…+0x88 (KO, EX Mode, …).
- **ablt**: the ability rows (Chapter 8).
- the Quick Battle grid table, the unlock table, name tables, picture tables (Chapter 8).

---

## 2.3 Inside the battle file (the objx)

The battle file is an **ARC box** with about 19 **chunks**. Think of a binder with labelled tabs.

```
obj/p_sev120.objx  (ARC)
├── p_se type 5   hit-shape table      spheres on bones = where hits can land   (Ch. 4)
├── p_se type 6   bone physics         coat tails that swing by themselves       (Ch. 3)
├── p_se type 7   motion table         "motion id 10000 → script block 43"       (Ch. 4)
├── p_se type 8   animation scripts    "at frame 16–24 turn hitbox on", sounds…  (Ch. 4)
├── p_se type 9   "hibg"               used by battle code; not decoded
├── effe          effects package      textures, particle recipes, effect sounds (Ch. 6)
├── snd_          sound bank (SSCF)    weapon swings, hits, jumps               (Ch. 5)
├── plya          attack pieces        one row per swing                         (Ch. 4)
├── comb          action table         the combo recipes                         (Ch. 4)
├── atkp          hit table            damage + knockback per hit                (Ch. 4)
├── magi          projectiles          fireballs, meteors, shockwaves            (Ch. 4)
├── brat          ?                    not decoded
├── text          in-battle names      "Firaga", "Ars Arcanum" banners           (Ch. 8)
├── wind          banner backgrounds   small GIM pictures
├── spec          menu pictures        EX Burst "tap ◯" picture etc.
└── d_se          dummy + CAMERA model a small GMO with the intro camera paths   (Ch. 3)
```

"p_se" is just the tag the developers gave five different chunks. They are told apart by a
type number (5–9). The game copies each chunk into its own memory block when the fighter loads.

**Why chunks matter:** almost every Sora feature is "edit one chunk of `obj/p_sev120.objx`,
then put the file back with `pkg_put.py`". Many build scripts do exactly that.

---

## 2.4 The story of slot #33 (tests 14–28)

This took about two days (2026-10-12/13). Each step taught us one table.

### Step 1 — Getting #33 onto the grid (tests 14–14b)

- **Test 14:** copied Cloud's `chrp` row and `objentry` rows to owner 33, and swapped #33
  into an existing grid list. Result: **not on the Quick Battle grid.** We had found the wrong
  list. Lesson: the game has *several* owner lists; you must find the one the screen really uses.
- The **unlock table** in the EBOOT (rows of owner + unlock flag) did not include 33.
  We used a cheat code to make #33 "always unlocked". Still not on the grid.
- The real **Quick Battle grid table** was found live in memory: menu overlay address
  `0x08A864D0`, 12-byte rows (picture, name picture, game logo, owner). We replaced Chaos's row
  with owner 33. **A new cell appeared** (with a broken picture). Picking it loaded a battle
  with Cloud's model. **[PROVEN]**

### Step 2 — Making #33 attack (test 15)

- First battle: **#33 had no attacks at all.** Why? Each fighter has a saved **record**
  (level, equipment, learned moves). Owner 33 had no record of its own, so it got a shared
  blank one: nothing equipped.
- Copying Cloud's equipment into it: still nothing. The missing piece was the **learned list**
  (a list inside the record of every ability the fighter knows). After writing learned entries
  too: **#33 attacked.** **[PROVEN]**
- Bad moment: Mat opened Customization for #33 while it had 0 abilities and got **stuck** in
  the menu (it can't be left with nothing). Restart needed.

### Step 3 — Own battle file and own model (tests 16–19)

- **Test 16:** `pkg_add.py` added `obj/p_sev120.objx` (a copy of Cloud's) at the end of the
  disc, and `roster_patch.py set-model` pointed #33's rows at it.
- **Separation check:** we changed one hit in #33's file only (launch straight up). #33 launched
  the foe straight up; real Cloud still blasted them into the wall. **#33 and Cloud are fully
  separate. [PROVEN]**
- **Test 17:** #33 got its own model files `obj/P_SEV120_{1,2,3}P.gmo` (+ `.cosx`, `.exex`,
  HUD picture). As a visible proof, the 1P model was Cloud's black alternate outfit.
- **Tests 18–19:** first "skins": pink hair, then a giant blue sword. Proved the model
  converter works. (Chapter 3.)

### Step 4 — No more cheats (tests 20–21)

The rule is: every change must be a real change on the disc, no cheat codes.
- **Test 20:** the EBOOT on the disc is encrypted. We replaced it with the **decrypted** copy
  (same size slot) and baked the unlock change into it. PPSSPP boots it fine.
- **Test 21:** #33 got its **own saved record**. The save file has exactly 31 fighter records,
  so there was no free one. `tools/scripts/spot33_save.py` puts #33's record into the area of
  "friend card" slot 24 and lowers the friend-card limit from 25 to 24. It also gives #33 a
  starting equipment preset (250) and a level table. Small code changes in the EBOOT make
  owner 33 use that record (Chapter 7).
- **[PROVEN]** Mat confirmed #33 attacks with no cheats. After a win, the game saved; after a
  restart and reload, #33's record was unchanged. Progress survives.

### Step 5 — Names, pictures and voices (tests 22–28)

- **Test 22:** the game turns owner numbers into a short **name key** (`sev100` = Cloud)
  with several tables. Most already mapped 33 → `sev120`. One menu table stopped at owner 32, so
  the loading screen asked for `p_(null)_name.gim`. `spot33_names.py` fixed it.
- **Test 23:** grid picture. #33's row pointed at picture 32, which doesn't exist (junk).
  Pointing it at Cloud's picture 12 worked. (Later Sora got his own pictures, Chapter 8.)
- **Test 24:** own voices. The voice key is plain data in the `chrp` row (+0x74).
  `spot33_voice.py` set it to `P_SEV120` and copied Cloud's voice files under the new name.
- **Tests 25–26:** own weapon sounds (Chapter 5).
- **Test 27:** the entrance animation lives in the model (motions `_900A`/`_902A`).
- **Test 28:** own voice line ids and own subtitles. `dumps/ULUS10566-test28-lines.iso` is
  still the **base disc for every full build** today (Chapter 10), because it holds all of
  these slot-#33 setup steps.

---

## 2.5 Mirror matches and other copies of Cloud

Starting from a copy of Cloud was fast, but every copied thing that has an *ID* can clash
with the real Cloud when both are in one fight. We hit four of these:

| copied thing | what went wrong | fix | chapter |
|---|---|---|---|
| sound bank ids | Cloud's Braver sound came out of Sora's bank | own ids 219000/219100 (`spot33_soundids.py`) | 5 |
| effect package id | the fighter loaded second got NO effects | own FEP id 0x31280000 (`spot33_effects.py`) | 6 |
| effect texture keys | they would share edited textures | "rekey" (`spot33_fx.py`) | 6 |
| 2P/3P outfit files | a CPU Sora in a Sora-vs-Sora fight was drawn as Cloud | copy 1P over 2P/3P (`spot33_2p.py`) | 3 |

**Rule (for any future fighter built from a copy):** give it its own effect package id, its
own sound ids, its own texture keys, and copy its outfit files. Otherwise two fighters can't
share one battle.

---

## 2.6 Limits we know about

| limit | value | what it means |
|---|---|---|
| new files on the disc | ~120 more | each new voice line or picture costs one |
| `chrp` rows | 34 | owners above 34 need a bigger table |
| unlock mask | 32 bits | owner 33 shares bit 0 with Warrior of Light |
| Quick Battle grid | 31 cells + random | #33 replaced Chaos's row |
| saved records | 31 | #33 borrows friend card 24's space |
| ability table | 808 rows, raised to 832 | see Chapter 8 |
| moves in a fighter's action table | 256 | #33 uses about 25 |

Hidden owner spots usable: 33 (done), 34, maybe 23.

---

## 2.7 Where to look

- `notes/roster.md` — every slot-#33 test in detail.
- `tools/scripts/roster_patch.py`, `spot33_save.py`, `spot33_names.py`, `spot33_voice.py`,
  `spot33_2p.py`.
- `notes/files-loaded-spot33-battle.txt` — files a battle opens.

Next: [Chapter 3 — The 3D model, skeleton and animations](03-model-skeleton-animation.md).
