# How the mod works

The whole process in plain words. Each part says **what** we did, **why**, and **which tool** does it. For the
exact formats, see [ARCHITECTURE.md](ARCHITECTURE.md) and the specs linked from the [README](../README.md).

> This tour follows the Sora build (October 2026, before Phase 2). For the current picture start at the
> [README](../README.md) and the [roadmap](ROADMAP.md); the long version is the learning path
> [learn/00-START-HERE.md](learn/00-START-HERE.md), and the engine is explained in
> [modding/OVERVIEW.md](modding/OVERVIEW.md).

## Part 1: The goal and the rules

- **Goal:** add Sora (Kingdom Hearts II) to Dissidia 012 as a real fighter: his own model, size, stance, moves,
  voice, sounds, EX Mode, EX Burst and a parry (the Reflect barrier).
- **Rule 1:** we never share game files. What we share is a **patch** that only holds our changes. Players apply it
  to their own copy of the game.
- **Rule 2:** every change is a real change on the disc image, not a cheat code.
- **Rule 3:** the clean game file is never touched. Every test is a **copy** with changes.

## Part 2: What's inside the game disc

Think of the disc image (`.iso`) as a box of folders.

| Thing | What it is | Our tools |
|---|---|---|
| `EBOOT.BIN` | the main program (the game's code) | Ghidra to read it, `mips_asm.py` for small code changes |
| `OVL_BATTLE_APP.ELF` | the fighting code, loaded for battles | Ghidra |
| `PACKAGE.BIN` | one giant file holding about 11,000 smaller files | `unpack_package.py`, `pkg_put.py` |
| `PACKAGE_INFO.BIN` | the table of contents for `PACKAGE.BIN` (file names stored as hashes) | `pkghash.py` |

`pkg_put.py ISO PATH FILE` is the tool used most. It puts one file into a disc copy, for example
`obj/P_SEV120_1P.gmo` (Sora's model). If the new file is bigger than the old one, it goes at the end of the disc
and the table of contents points there.

## Part 3: A fighter is a bundle of files

Every fighter has a short code name. Cloud is `sev100`.

| File | What's in it |
|---|---|
| `obj/p_sev100.objx` | the **battle file**: move list, hits, damage, effects, weapon sounds |
| `obj/P_SEV100_1P.gmo` | the **model**: body, weapon, textures and all 86 animations |
| `voice/EN/...P_SEV100...` | voice shouts, spoken lines and the list of when to say what |
| `system.bin` tables | stats, names, which save record, which voice key |

## Part 4: Sora's roster spot (#33)

The game has a hidden spot, #33, that it only used for an assist character. We turned it into a playable fighter
with the code name `sev120`:

- it shows on the character select grid (bottom row),
- it has its **own** files (copies of Cloud's at first), its own save record, name, pictures and voices.

So #33 started as a copy of Cloud. Everything we change for Sora only changes #33, never the real Cloud.
Tools: `roster_patch.py`, `spot33_save.py`, `spot33_names.py`, `spot33_voice.py`.

## Part 5: How moves work

A move is a chain of small tables inside the battle file:

```
comb  (move list: "this button = this move")
  └─ plya  (attack pieces: one per swing, says which animation to play)
       └─ p_se scripts (when in the animation the hitbox appears)
            └─ atkp  (the hit: damage, knockback, flight time)
```

With these we edit damage and knockback and build **brand-new moves** out of existing pieces (`comb_add.py`,
`own_hit.py`, `atkp_patch.py`). Sora's combos use this together with his own KH2 animations (Part 8).

## Part 6: Sora's body (the model)

### 6a. Getting Sora out of KH2
Sora's model, Keyblades, textures, voice clips and sounds are extracted from your own copy of KH2 with OpenKH into
`kh2_export/` (for example `model/sora.glb` and `keyblade/kingdom_key.glb`).

### 6b. The skeleton problem
A model has **bones** (an invisible stick figure) and a **skin** (the mesh) glued to them. Dissidia can only animate
a Dissidia skeleton (Cloud's has 54 bones); KH2 Sora has 228. So we keep Cloud's skeleton and glue Sora's skin onto
it.

### 6c. Making the skeleton Sora-sized: `gmo_resize.py`
Cloud is taller with broad shoulders. `gmo_resize.py` changes the bone lengths in the skeleton **and in all 86
animations** to Sora's (shoulders ×0.52, thighs ×0.79 and so on), and lowers the hips so his feet still touch the
floor. Sora ends up his real height and Cloud's moves still work on him.

### 6d. Gluing Sora's skin on: `fit_sora.py`
- KH2 Sora is in a T-pose (arms straight out); Dissidia expects arms 45° down, so the script bends his arms.
- Every KH2 bone is matched to the nearest Dissidia bone.
- His right hand is closed into a fist (Dissidia hands never move their fingers).
- Textures are shrunk to 256×256, because the PSP has very little memory.
- It writes `sora_fit.map.json`, which the animation importer needs (Part 8).

### 6e. The Keyblade: `add_keyblade.py`
Cloud's sword is a separate rigid part that follows his right hand. We swap it for the Kingdom Key, with the handle
through Sora's fist.

### 6f. Back to the game's format: `gltf2gmo.py`
glTF (the format Blender opens) is converted back to the game's GMO format, and `pkg_put.py` puts it on the disc copy.

**Parts 6 and 8 in one command:**
```sh
bash tools/scripts/build_sora.sh INPUT.iso OUTPUT.iso
```

## Part 7: Checking without the game (previews)

Before an in-game test, renders show whether a model or animation looks right:

- `gmo2gltf.py` turns a game model back into glTF, and `gmo_anim2gltf.py` adds any of the game's animations to it.
- A Blender script renders front, side, back and top views of any frame, without opening a window.
- `tools/scripts/preview_kh2_motion.sh INDEX LABEL` makes an animated GIF of a KH2 animation on Sora, so you can
  pick animations before using them.

## Part 8: KH2 animations in Dissidia

KH2 doesn't store animations as simple bone angles per frame. It uses tricks like **IK**, which places hands and
feet on targets and works out the arm and leg angles. Rebuilding that by hand would take weeks, but OpenKH includes
an emulator of KH2's own animation code, so:

1. **Bake:** `tools/kh2bake/bake`, a small C# program, plays a KH2 animation through that emulator and saves the
   exact bone positions for every frame.
2. **Retarget:** `kh2_retarget.py` copies the pose of each KH2 bone onto its Dissidia bone, frame by frame, using
   the map from Part 6d, and writes it into a Dissidia animation slot.

Dissidia animation slots have code names (`_000A` idle, `_900A` entrance, `_910A` win, and so on). To give Sora a
move, we put a KH2 animation in a slot and point his move tables (Part 5) at it.

## Part 9: Voices and sounds

Shouts and grunts live in a sound bank (`.scd`), spoken lines are `.at3` files, and a list says when each line plays
(battle start, win, against a certain fighter, reply to another line) together with the subtitles.
Tools: `sscf.py`, `voice_lines.py`, `voice_text.py`. More in [AUDIO.md](AUDIO.md).

## Part 10: How a test works

1. Build a test disc: copy the last good ISO and put the changed files in (`pkg_put.py` or `build_sora.sh`).
2. Run it in PPSSPP with a throwaway profile.
3. Quick Battle → Sora → a CPU opponent, stage Order's Sanctuary, CPU strength Minimal. Set these each time; a
   restart resets them.
4. PPSSPP's remote debugger lets scripts (`ppctl.py`, `ppdbg.py`) drive the game and read memory.
   `tools/scripts/record_game.sh` records only the game window.
5. Real-hardware checks run on a PS Vita with Adrenaline (see [TEST-ON-VITA.md](TEST-ON-VITA.md)).

## Part 11: What's done and what's next

Done: Sora's own model, size and Keyblade; KH2 animations for his stance, movement, combos, magic, intro, win and
loss; his own moves and finishers; voices and Keyblade sounds; EX Mode with the Reflect barrier; the Trinity Limit
EX Burst; menus, saves, unlocks and CPU behaviour; the package format, the engine module and the patch app.

Since then: release 1.0 shipped on 20 October 2026, and the multi-fighter engine (Phase 2) is being built; Sora as
package #1 on it is in progress. See the [roadmap](ROADMAP.md). Full glossary: [learn/GLOSSARY.md](learn/GLOSSARY.md).

## Glossary

| Word | Meaning |
|---|---|
| ISO | the disc image file |
| GMO | the game's 3D model file (it also holds the animations) |
| glTF / GLB | a standard 3D format that Blender opens |
| bone / skeleton | the invisible stick figure inside a model that animations move |
| skin / mesh | the visible surface glued to the bones |
| animation / motion | bone angles over time; Dissidia calls them motions (`_000A` …) |
| IK | inverse kinematics: the animation says where a hand or foot goes, and the arm or leg angles are worked out |
| bake | play an animation and record the result frame by frame |
| retarget | copy an animation from one skeleton to another |
| texture | the picture painted on the model |
| patch (VCDIFF / xdelta) | a file that says "change these bytes", so the game's own files are never shared |
