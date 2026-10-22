# Chapter 3 — The 3D model, skeleton and animations

**The big idea:** a fighter's body is a **puppet**. Inside is an invisible stick figure (the
**skeleton**, made of **bones**). The visible body (the **skin**) is glued to the bones. An
**animation** is a list of instructions: "at this moment, turn this bone this much". The game
only knows how to move a *Dissidia* puppet, so we kept Cloud's stick figure, resized it to
Sora's body, glued Sora's KH2 skin onto it, and then taught it KH2's moves.

---

## 3.1 Words you need first

- **Mesh / skin:** the visible surface, made of many small triangles. The corners of the
  triangles are **vertices** (one is a *vertex*).
- **Bone:** an invisible stick. Bones hang from each other (hand → forearm → upper arm → chest).
  The bone it hangs from is its **parent**. The whole tree is the **skeleton**.
- **Weight:** how strongly a vertex follows a bone. A vertex near the elbow might follow the
  upper arm 50% and the forearm 50%, so the skin bends smoothly.
- **Bind pose:** the pose the skin was glued on in. Dissidia's is arms about 45° down.
- **Texture:** a picture painted onto the mesh (like wrapping paper).
- **Animation = motion:** Dissidia calls each animation a *motion*. It moves bones over time.
- **Frame:** one moment of an animation. Dissidia motions run at 30 frames per second.
- **Keyframe (key):** a saved pose at one frame. The frames between keys are filled in
  automatically ("in-betweens"). Like a flip book where you draw only some pages and the
  machine draws the rest.
- **fcurve:** one bone's movement over time for one property (turn, move, or size), stored
  as a list of keys. A motion is a bundle of fcurves.

---

## 3.2 The GMO file (the game's model format)

The model file is a **GMO** (magic word `OMG.00.1PSP`). Inside are nested blocks:

```
file "file-0"
├── model "_000A"        ~1.7 MB   54 bones + 86 MOTIONS (the animations)
└── model "model-0"      ~320 KB   the SKIN
    ├── 54 bones (same names)
    ├── part p_sev100  = the body
    ├── part wep0      = normal weapon      (Cloud: Buster Sword   → Sora: Kingdom Key)
    ├── part wep1      = EX Mode weapon     (Cloud: Ultima Weapon  → Sora: KH2 Ultima Weapon)
    ├── meshes, materials, ~6 textures
    └── "TexAnm"       texture animation (for example the eyes blinking)
```

So a fighter's GMO holds **both** the body and all of its animations. That's why the model
file is ~2 MB, and why the animations count against the same memory budget (see 3.10).

### The 54 bones

Some you will see a lot:

| index | bone | job |
|---|---|---|
| 2 | `root` | the whole character's position on the floor |
| 3 | `hip` | hips |
| 27 / 29 | `waist` / `chest` | spine |
| 39 | `neck` | |
| 41 | `hair` | |
| 50 | **`r_wep`** | the right hand's weapon holder. **Hitboxes follow it.** |
| 51 / 52 | `wep0` / `wep1` | draw bones of the two weapon parts |
| 53 | `trans_include` | last bone |
| — | `camera_include`, `camera2_include` | bones that can carry a camera |

### How the skin is stored (short version)

- Vertex positions are squeezed into small whole numbers and stretched back with one
  shared **scale + offset** (the "model box"). So the whole body must fit inside the box.
- Each mesh lists up to 8 bones it uses (its "palette"). Weights are bytes where 128 = 100%.
- Textures are **GIM** pictures: 256 colours (a palette) and pixels stored in a shuffled
  ("swizzled") order the PSP's graphics chip likes.
- Weapons are **rigid**: they don't bend, they just follow `r_wep`.

Tools: `gmo.py` (print the structure), `gmo2gltf.py` (export to glTF for Blender), `gim.py`
(textures to PNG), `gltf2gmo.py` (glTF back to GMO).

**glTF / GLB** is a standard 3D format that Blender opens. It's our "workbench" format.

### First lessons (tests 18–19)

1. A header field says where the vertex data starts. We wrote it 16 bytes too early → the
   game read garbage → **exploding spikes**. Fixed in the importer. (Same rule for fcurves.)
2. Rebuilding the sword as a bendy (skinned) mesh drew a **black slab** next to Cloud.
   Weapons must stay rigid in their own bone space.
3. Copy the original's materials; only swap the texture.
4. Result **[PROVEN]**: a pink-haired Cloud (test 18) and a giant blue sword (test 19) both
   animated and fought correctly.

---

## 3.3 Getting Sora out of Kingdom Hearts 2

- Source: Mat's own copy of **Kingdom Hearts 1.5+2.5 ReMIX (PC)**, extracted with **OpenKH**
  (a community toolkit for KH files) into `kh2_export/`.
- What we got: `model/sora.glb` (KH2's `P_EX100`, 228 bones), `keyblade/kingdom_key.glb`
  (12 bones), HD textures, 70 voice clips, 44 Keyblade sounds, and the raw game files in
  `kh2_export/raw/` (animations `.mset`, effects `.a.us`, magic `.mag`, sound banks `.scd`).
- How to redo the extraction: `notes/kh2-extraction-instructions.md`.

---

## 3.4 The skeleton problem

KH2 Sora has **228 bones**. Dissidia's code only knows Cloud's **54**. And Cloud's animations
don't only turn bones; they also store each bone's **length** in every motion (as a fixed
number). If you just glue a short Sora onto Cloud's skeleton, Cloud's long bones stretch him.

So the order is:

```
1. gmo_resize.py   Cloud's skeleton + ALL 86 motions get Sora's bone LENGTHS
                   (shoulders ×0.52, thighs ×0.79 …; hips drop 7 cm so feet touch the floor)
                   → Sora's real height, 1.69 m, and Cloud's moves still work on him
2. gmo2gltf.py     that resized skeleton → glTF
3. fit_sora.py     Sora's KH2 mesh bent onto it:
                   - T-pose (arms straight out) → Dissidia's arms 45° down
                   - every KH2 bone matched to the nearest Dissidia bone
                     (e.g. KH2 "Bone78" → l_uparm)
                   - right hand closed into a FIST (Dissidia fingers never move)
                   - textures shrunk to 256×256 (the PSP has very little memory)
                   - writes sora_fit.map.json = how each KH2 bone was moved (needed later)
4. add_keyblade.py Kingdom Key in the fist (wep0), KH2 Ultima Weapon (wep1, EX Mode,
                   scaled 0.685 so it's the same length — at full size it went through him)
5. gltf2gmo.py     back to GMO, with the resized skeleton + animations kept
```

**[PROVEN]** Test 29: Sora renders and animates on #33. Test 30: holds the Kingdom Key.
Test 31: real size. Test 57: Ultima Weapon appears in EX Mode (with Cloud's green EX glow).

Little stories:
- KH2's own "attach the Keyblade to palm bone 178" made it **hang below the hands** in Mat's
  screenshots. We kept our fist-axis grip instead.
- With a tight fist, the finger centre sat on the handle, so the guard **rolled randomly**.
  `add_keyblade.py` now turns the guard toward the palm direction.
- Mat saw open fingers in the idle → fist tightened. Mat saw the left fist open in the intro →
  `fit_sora.py` CURL settings for the left hand.

---

## 3.5 Motions: how an animation is stored

One motion block holds:
- **frame range** (`0x80B1`): start and end frame,
- **fps** (`0x80B2`): 30,
- **loop flag** (`0x80B4`): 1 = loop (idle, run), 0 = play once (attacks, hits),
- one entry per bone and channel (translate = move, rotate = turn, scale = size) pointing at
  an **fcurve**.

fcurve kinds: `0x80` = constant or steps, `0x81` = straight-line moves between keys,
`0x84` = rotation keys (quaternions — a maths way to store a turn without glitches),
`0x82` = smooth curves with in/out handles (used by cameras).

### Motion slots and motion ids

Each motion has a slot name like `_000A`. The game itself thinks in **motion ids** (a number
for "what am I doing now", stored at fighter memory +0x180). A table in the battle file
(`p_se` type 7) turns an id into a script block, and **the script block number = the GMO motion
number**. Logged live with `ppplay.py`:

| id | slot | what |
|---|---|---|
| 1 | `_000A` | idle |
| 2 | `_010A` | run |
| 100 / 101 / 102 / 103 | `_020A` `_021A` `_022A` `_023A` | jump / in air / land / double jump |
| 400 / 460 / 440 | `_100A` / `_150A` / `_140A` | dodge away / toward / in the air |
| 470 / 471 | `_160A` / `_161A` | block on the ground / in the air |
| 500, 501 / 550–561 | `_200A`… / `_210A`… | getting hit standing / in the air |
| 700 / 701 / 702 | `_400A` `_401A` `_403A` | blown away / flying / land + get up |
| 1100 / 1110 | `_900A` / `_902A` | battle intro |
| 1200 / 1210 | `_910A` / `_911A` | **win** / **loss** (proven with `ppwinwatch.py`) |
| 5000 | `_736A` (own slot) | EX Mode start |
| 8000–8600 | `_801A`…`_813A` | EX Burst shots |
| 10000+ | `_600A`… and new slots | attacks |

### Lesson: the frame range is the LOOP range

Mat saw the win pose **repeat**. Why: the game plays from frame 0 to the end once, then loops
the part given in `0x80B1`. Cloud's win pose keys run 0–175 but the range says 111–175.
Our tool wrote the whole range → the whole pose looped. Now win poses loop only their last
6 frames, so the final pose holds.

### Lesson: two clocks

**Script frames run at 60 per second. Motion frames run at 30.** Cloud's hit window 16–24
(script) matches his sword peak at motion frame 9. Our first KH2 attacks (test 51) were timed
to the doubled numbers, so every swing came **late**. All our tools now take script frames
and halve them.

### Lesson: the loop flag

Our retarget tool wrote "loop = 1" into every motion. Result: combo **finishers missed**
(Mat saw the ground 4th hit and air 3rd hit not land). Fix: copy each slot's own flag.

---

## 3.6 Bringing KH2 animations over

KH2 doesn't store animations as simple "bone angles per frame". It uses tricks like **IK**
(*inverse kinematics*: "put the hand *here*" and the arm angles are worked out). Rebuilding
that by hand would take weeks.

So we use KH2's own animation code, emulated:

1. **Bake** — `tools/kh2bake/bake` (a small C# program) runs OpenKH's
   `OpenKh.Kh2AnimEmu.dll` (an emulator of KH2's real animation code, IK included) and saves
   every bone's exact position for every frame → `dumps/kh2anim/NNN_name.bin`.
   `dumps/kh2anim/list_named.txt` lists Sora's 89 animations (IDLE 0, RUN 8, ground combo
   EX000–004, air combo EX030–033, REFLECT 164, magic 224–292, …).
2. **Retarget** — `kh2_retarget.py` copies each KH2 bone's pose onto its Dissidia bone, frame
   by frame, using the map from `fit_sora.py`, and writes a new Dissidia motion.

**[PROVEN]** Test 33: KH2 battle idle in `_000A`. Tests 48–49: run, jump, land, dodge, block,
hits, blown away, get up — all KH2. Test 49: CPU beat Sora up for 35 s, every reaction
played, no glitches.

### The kinds of animation entries in the build

`tools/scripts/build_sora.sh` has lists like `MOVES`, `HITS`, `GROUND`, `AIR`, `HP`, `BURST`.
Each entry is `SLOT=SOMETHING`:

| entry | means |
|---|---|
| `_000A=0` | KH2 animation 0, as is |
| `_200A=42@0.43:0-29` | KH2 42, played at 0.43× speed, only frames 0–29 |
| `_010A=8#all` | loop the whole thing |
| `_910A=pose:tools/poses/win_combo.py` | a **hand-made** animation (pose script) |
| `_600A=atk:604:14` | KH2 attack 604, retimed so the swing lands on script frame 14 |
| `_602A=atk:620:18:match=38` | same, plus the weapon chain blended to Cloud's at the hit |
| `_720A=nat:668` | KH2 668 at **natural** speed; the script is written to fit it instead |
| `_706A=combo:724,728,…:33,47,…` | several KH2 clips chained, one swing per hit frame |
| `_812B=burst:k884:7,27,…` | EX Burst shot (also copies Cloud's placement around the foe) |
| `kNNN` | an animation from KH2's **Limit Form** set (`P_EX100_KH1F.mset`) |

### Hand-made poses

`pose_author.py` builds animations from key poses written in Python
(`tools/poses/*.py`): "aim this bone that way", "use KH2 frame N as a base", "turn the
hip 30°". It fills the in-betweens smoothly. Used for the win pose, loss pose, intro, KO.

Check tools for poses (in Blender, offline):
- `tools/blender/ground_check.py` — are the feet on the floor?
- `tools/blender/clip_check.py` — does the Keyblade go through the body?
- `tools/scripts/preview_pose.sh`, `preview_slot.sh`, `preview_kh2_motion.sh` — GIF previews in
  `dumps/renders/poses/`.

---

## 3.7 Why some finishers missed: the hitbox follows the weapon

Even with the loop flag fixed, the ground 4th hit still missed. We **bisected** (tested halves
to find the cause, see Chapter 9):

- Whole Cloud motion in that slot → lands 4/4.
- Only Cloud's root + hip → 1/5. Everything except root → 3/5.
- The chain **root → hip → spine → right arm → hand → `r_wep`** from Cloud → 3/3.

**[PROVEN] The hit spheres sit on `r_wep`, so they move with the weapon's world position.**
If Sora's KH2 swing puts the Keyblade somewhere else at the hit moment, the hit is somewhere
else. Fix: `:match` in the build = blend that arm chain to Cloud's for a few frames around the
hit. Later moves use a different fix: animations at natural speed (`nat:`) and **own script
blocks with bigger hit spheres** placed where KH2's swing really is (Chapter 4).

---

## 3.8 The intro, win, loss and KO

- **Intro:** only `_900A` is really on screen. After a white flash the game goes to the idle.
  Current intro = Codex's "slow flourish" (`tools/poses/intro_spin.py`, Chapter 11).
- **Win (`_910A`):** hand-made "Fire" finisher → 3 spins → Keyblade on the shoulder. Mat: "perfect".
- **Loss (`_911A`):** hit → one knee → Keyblade planted, breathing loop.
- **EX Burst KO:** Mat saw the beaten foe "just stand there". The victim is held in motion 700
  (`_400A`) through the whole final-blow scene, and the scene seems to restart the clip near
  frame 0, which was the upright flinch. Fix: `_400A=66:5-13` (only the flung-back frames).

### The intro camera (solved 2026-10-15)

The close-up in the intro showed only Sora's **hair**. We looked everywhere: model, motions'
camera bones (all zero), costume files… The answer: **every battle file carries its own small
camera model** (chunk `d_se` type 2, a 24 KB GMO with 9 camera motions). Sora's was Cloud's
copy, so it aimed at Cloud's face height (~1.58 m). `spot33_introcam.py` scales the intro
camera paths by head-height ratio **0.887** (1.406 / 1.586) from the feet. **[PROVEN]** test161
recording shows the face close-up.

### The win camera bug ("he suddenly vanished")

Mat: "in the win animation he suddenly vanished". Recording showed Sora didn't vanish; the
**camera** cut away after 4.5 s. Cause: the game takes the results camera from **GMO motion
number 86** if it exists. Cloud has exactly 86 motions (0–85), so none. Our first added slot
(Finishing Leap) became motion 86 and carried Cloud's swing camera.
Fix: motion 86 = `_719A` = a copy of the win pose. All new slots start at 87. **[PROVEN]** test 149.

---

## 3.9 Adding new animation slots

Nothing in the game counts motions, so `gmo_motion.py append` can add `_720A`, `_721A`, … at
the end of the model block. Each one is paired with a new script block and a new motion id in
`spot33_chain.py` SLOTS (same order). Then pieces point at the new id (Chapter 4).

The build also **empties** Cloud slots Sora no longer plays (`STUBS`: replaced with a tiny
copy) to save memory.

---

## 3.10 The memory budget (why the model must stay small)

The PSP has very little memory. The fighter's model gets a fixed share. Too big and the game
fails. Evidence so far:

| model size | result |
|---|---|
| 2,248,956 B (Sora, one model) | works |
| ~2,499,324 B (test189) | works |
| 2,503,532 B (keychain v3) | works |
| 2,506,640 B (test214) | works |
| 2,517,912 B (keychain v1, 58 bones) | **crash at battle start** |
| 2,523,344 B (test215 first try: + Codex's EX Burst motions) | **crash at battle start** |
| 2,496,488 B (test215 after `gmo_thin.py` on `_719A`) | works, burst plays through |
| 2,821,156 B (two models, test 70) | **white screen hang** after "Enter Battle" |

The crash message both times: `Invalid Memory Access … PC 0885c8a0` in `FUN_0885c6cc`, which
is a memory allocator. An allocation **failed** and the code used the empty result.

**[GUESS, strong evidence]** The line is between 2,506,640 and 2,517,912 bytes.
**Rule (HANDOFF): keep the model at or under ~2,506,640 bytes.** Check the size before every
test. Tools that help: `STUBS` (empty unused slots) and `gmo_thin.py` (keeps every 2nd key of
the smooth curves in chosen motions; the build runs it on `_719A`, the win-camera copy, and
saves ~27 KB).

---

## 3.11 The keychain story (v1 crash → v2 invisible → v3 works)

Mat wanted the Keyblade's chain to **hang and swing**, not stick out straight.

- **v1:** added 4 new bones (54 → 58) and gave the chain mesh to them. **Crashed** at battle
  start: the model grew +19 KB, over the memory budget (3.10).
- **v2:** no new bones; reused 4 bones Sora's skin doesn't use (belt, shldarmor, hair,
  r_arm_help) and hung them under `r_wep`. Smaller than before. No crash. **But the chain was
  invisible.** Why: **the engine computes bones in list order.** `belt` is number 28; its new
  parent `r_wep` is number 50. When belt was computed, its parent wasn't yet → the chain ended
  up somewhere else. **Rule: a bone must come after its parent in the list.**
- **v3:** only bones after 50 qualify: `wep0` (51). `wep0` is only the *draw* bone of the
  weapon part; nothing is skinned to it. So it became one pendulum bone under `r_wep`, with the
  chain and Mickey token as one rigid piece on it. A swing is simulated when building (gravity,
  damping) and baked into keys for idle, intro, win and loss. +4.2 KB.
  **[PROVEN]** Mat (test192): "the keychain is perfect".

Side find: `p_se` type 6 in the battle file is the engine's own **bone physics**: Cloud's coat
tails are chains of bones that swing by themselves in game. An idea for later.

---

## 3.12 EX Mode "form change" (not done yet)

Terra's model file holds **two** skins: `model-0` and `model-0-0000` (her Trance form). So the
engine can switch skins. Test 70: Sora + a silver copy as `model-0-0000` → 2.82 MB → white
screen hang (too big). A form change needs much smaller textures, or texture swaps only.
**[UNKNOWN]** which code picks the second model. KH2 form models are ready in `kh2_export/raw/`
(Final, Valor, Wisdom, Master, Limit, Anti).

---

## 3.13 Hurt animations and "escapes"

Sora's KH2 hurt clips are much **shorter** than Cloud's (13 vs 30 frames). A CPU Sora escaped
combos (it went back to idle between hits). **[GUESS, worked]** hit-stun follows the hurt
animation's length. Fix: hurt clips slowed to Cloud's lengths (`42@0.43:0-29` …). After that,
3/5 then 4/4 full 12-hit combos landed (test 130–132).

---

## 3.14 Where to look

- `notes/gmo-format.md` — the format and every model test (long; bottom = newest).
- `tools/scripts/gmo_resize.py`, `fit_sora.py`, `add_keyblade.py`, `gltf2gmo.py`,
  `kh2_retarget.py`, `kh2_attack.py`, `kh2_combo.py`, `pose_author.py`, `gmo_motion.py`,
  `keychain.py`, `gmo_thin.py`, `spot33_introcam.py`.
- `tools/poses/` — hand-made animations.
- `dumps/renders/poses/index.html` — preview gallery.

Next: [Chapter 4 — Moves and combos](04-moves-and-combos.md).
