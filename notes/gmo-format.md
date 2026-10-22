# GMO model format (Dissidia 012 character skins) — worked out 2026-10-12

Body model of a fighter = `obj/<objentry name>.gmo` (Cloud: obj/P_SEV100_1P.gmo = pkg 1193, 2,017,616 bytes;
_2P/_3P = alternate outfits, pkg 2343 / 1964). #33 = obj/P_SEV120_{1,2,3}P.gmo (added in test 17).

## Container
16-byte header "OMG.00.1PSP". Chunks: u16 type, u16 header size, u32 total size.
- Block chunks (type < 0x8000): header = 8 + u32 + u32 + zero-padded name; children follow the header.
  0x02 file, 0x03 model, 0x04 bone, 0x05 part, 0x06 mesh, 0x07 array (raw vertex data, no children),
  0x08 material, 0x09 layer, 0x0A texture (holds args incl. an embedded GIM), 0x0B motion, 0x0C fcurve, 0x0F blind.
- Argument chunks (type & 0x8000): 8-byte header + data. References = u32 (block type << 16) | 0x1000/0x2000 | index.

## Layout of a fighter GMO
file "file-0"
  model "_000A"  (~1.7 MB)  = 54 bones + **86 motions** (8450 fcurves) — the ANIMATIONS. Identical in Cloud 1P/2P/3P.
  model "model-0" (~320 KB) = the SKIN: 54 bones (same names), parts p_sev100 (body) / wep0 / wep1 (weapons),
                              4 materials, ~6 textures, blind "TexAnm" (texture animation, e.g. eyes).
⇒ A Sora skin = Cloud's _000A unchanged + a new model-0 whose meshes are weighted to Cloud's bone names.

## model-0 details
- model args 0x8015: mask 0x180 → position offset[3] + scale[3]; mask 0x003 → UV offset[2] + scale[2].
  Vertex value = raw / 32768 × scale + offset. Cloud: pos offset (0.243, 0.982, 0.572) scale 0.982 → ~1.8 tall, Y up.
- bone args: 0x8041 parent ref, 0x8048 translate[3], 0x804B rotate quaternion (x,y,z,w), 0x80F1 "DISTANCE"+float,
  0x804E draw-part ref (bones p_sev100, wep0, wep1 draw the 3 parts), 0x8044/0x8045 on 3 bones (?).
  Bones (54): camera2_include, camera_include, root, hip, l/r_femur_c, l/r_femur, l/r_tibia, l/r_foot, l/r_toe,
  skirt1a–4a, belt, belt1a/b, p_sev100, waist, chest, l/r_clavicle, l/r_uparm_c, l/r_uparm, l/r_arm_help, l/r_foarm,
  l/r_hand, l/r_fing1a, l/r_fing3b, shldarmor, neck, head, hair, r_wep, wep0, wep1, trans_include.
- mesh args: 0x8061 material ref; 0x8062 bone palette (count + model-0 bone indices, ≤ 8);
  0x8066 draw = (array ref (PART-local index), primitive (3 triangles, 4 strips), indices per list, list count, u16 indices…).
  Meshes without 0x8062 are rigid and follow the bone that draws their part.
- array: u32 PSP GE vertex type, u32 vertex count, u32 morph count, u32 0, then vertices.
  Seen types 0x0E00131A (1 weight), 0x0E00531A (2), 0x1000931A (3), 0x1000D31A (4), 0x1201131A:
  weights u8 (128 = 1.0), UV u16, colour 4444, position s16. Total 5155 vertices in Cloud's skin.
- material: arg 0x8085 (colours), child layer with 0x8091 texture ref.
- texture: 0x8012 original file name (e.g. p_sev100_wep01.tga), 0x8013 embedded GIM.

## GIM (textures)
"MIG.00.1PSP"; blocks u16 id, u16 0, u32 size, u32 next, u32 data offset; 0x02 root, 0x03 picture (children at +0x10),
0x04 image, 0x05 palette. Image header: format (0 5650, 1 5551, 2 4444, 3 8888, 4 index4, 5 index8), pixel order
(1 = swizzled 16 B × 8 rows), width, height, pixel start/end. Cloud's textures: index8, order 0, 256×256 etc.

## Tools
- tools/scripts/gmo.py FILE [--bones|--tree]: structure dump.
- tools/scripts/gmo2gltf.py FILE OUT_DIR: model-0 → glTF 2.0 (skeleton, skin weights, UVs, materials) for Blender.
- tools/scripts/gim.py FILE OUT.png | --gmo FILE OUT_DIR: textures → PNG.
- Export of Cloud 1P: dumps/models/cloud_1p/ (verified: mesh renders as Cloud in bind pose; textures decode).
- tools/scripts/gltf2gmo.py BASE.gmo SKIN.gltf OUT.gmo: glTF → new model-0 (body meshes ≤ 8 bones, triangle lists,
  weights u8 one per palette bone, UV u16, colour 4444, pos s16; PNG → GIM index8 + RGBA8888 palette), keeps the base's
  _000A (animations), model-0 bones, materials, weapon parts and TexAnm. Mesh name "part|…" picks the part.
- tools/scripts/pkg_put.py ISO PATH FILE: put any file into the ISO (in place if it fits, else appended).
- tools/scripts/drive_qb.sh ISO OUT_DIR: launch PPSSPP and drive into a #33 Quick Battle (screenshots).

## Lessons from the in-game tests (test 18, 2026-10-12)
1. Array block header: u32 #3 = total size, u32 #4 = header + 16 (= where vertex data starts). With #4 = header
   size the game reads vertices 16 bytes early → exploded spikes. (fcurve blocks use the same rule.)
2. Weapons (parts wep0/wep1) are RIGID meshes (no 0x8062 palette) in their own bone space: bones wep0/wep1 have
   0x8044 = attach to bone r_wep (index 50) and 0x8045 = offset matrix; 0x804E = part to draw. Rebuilding them as
   skinned meshes in model space put a black slab next to Cloud → importer copies the base weapon parts unchanged
   (REBUILD_WEAPONS=1 is not working yet).
3. Because weapon parts are copied, the model-level 0x8015 position/UV scale must stay the base's (KEEP_SCALE is
   automatic): the new body must fit in Cloud's box (offset 0.243/0.982/0.572, scale 0.982).
4. Materials: copy the base's materials (sword material has an extra 0x8083 grey colour); only the layer's texture
   ref changes.
Result: pink-haired Cloud on #33 renders, animates and fights correctly (dumps/screens/test18-pink-hair-spot33.png).
Round trip without edits: 1881/1881 triangles, UV ranges equal.

## Skinning (found 2026-10-12, fixed in both tools)
- Mesh palettes (0x8062) do NOT index model-0's 54 bones. They index the **skinning list of the part's draw bone**:
  bone p_sev100 (draws part 0 = body) has **0x8044 = 30 skin bones** (waist, chest, neck, head, hair, r_clavicle,
  r_uparm, r_arm_help, r_foarm, r_hand, r_fing3b, r_fing1a, l_clavicle, l_uparm, l_foarm, l_hand, l_fing1a,
  l_fing3b, l_arm_help, shldarmor, belt, hip, r_femur, r_tibia, r_foot, r_toe, l_femur, l_tibia, l_foot, l_toe)
  and **0x8045 = 30 inverse bind matrices** (column-major 4×4, after a u32 count).
- The mesh is modelled in the BIND pose (arms ~45°, hands at ±0.5, 1.09); bone TRS in model-0 = rest pose with arms
  down. Weapon bones wep0/wep1: 0x8044 = [r_wep], 0x8045 = 1 offset matrix (rigid weapon follows r_wep).
- gmo2gltf.py writes 0x8045 as glTF inverseBindMatrices and maps palette → skin list → bone name: verified bind
  positions = mesh centroids per bone. Blender import OK (tools/blender/render_check.py, dumps/renders/cloud.png).
- gltf2gmo.py maps glTF joints → index in the base's skin list (bones outside it fall back to their nearest listed
  ancestor). Round trip: 861/861 body vertices keep their dominant bone.

## For the Sora skin
Export Cloud's skin (gmo2gltf.py) → in Blender, fit Sora's mesh to Cloud's armature (same 54 bone names, A-pose,
~1.8 tall; Sora shorter is fine) and weight-paint to those bones; keep ≤ 4 weights per vertex; textures
power-of-two ≤ 512 px; name meshes "p_sev100|…" → gltf2gmo.py with Cloud's GMO as base → pkg_put.py into
obj/P_SEV120_1P.gmo. Keyblade = weapon part: name its meshes "wep1|…" (and/or "wep0|…"), weight 100% to r_wep,
place it in Cloud's hand in the bind pose (like the exported sword), run with REBUILD_WEAPONS=1 (and NEW_SCALE=1
if anything sticks out of Cloud's box — the importer warns).

## Weapon import (test 19 ✅, 2026-10-12)
Weapon parts are rigid: vertex type 0x0E00131A (one weight = 128), no 0x8062 palette; positions in the same bind
space as the body (r_wep's inverse bind = wep bones' 0x8045 offset matrix). gltf2gmo.py REBUILD_WEAPONS=1 rebuilds
them from "wep0|…"/"wep1|…" meshes. Proof: sword made 1.6× longer and tinted blue → #33 holds a giant blue Buster
Sword that follows his hand (dumps/screens/test19-big-blue-sword.png, ISO dumps/ULUS10566-test19-weapon.iso).
Default scale = base's (copied parts depend on it); NEW_SCALE=1 recomputes when every part is rebuilt.

## Sora body (2026-10-13) — test 29 `dumps/ULUS10566-test29-sora.iso` (= test 28 + Sora GMO on #33)
KH2 export: `kh2_export/` (README there; model/sora.glb = P_EX100, keyblade/kingdom_key.glb = W_EX010, 228 / 12 bones).
- Cloud's motions carry translate channels for most bones (`0x48` in 9–86 of 86 motions) → bone lengths come from
  Cloud's animations, so Sora must be fitted to Cloud's joints (not the other way round, for now).
- `tools/scripts/fit_sora.py SORA.glb CLOUD.gltf OUT_DIR [TEX]`: per-bone affine fit (segment table: Sora joint A→B
  onto Cloud joint A→B; stretch along, `PERP` across; shoe squashed so the sole stays on the floor; head unscaled),
  moved with Sora's own weights, re-weighted to Cloud bones (BONE_MAP_L; right side = Bone+29 legs / +92 arms).
  Keeps Cloud's materials 0–3 + 6 images (weapon parts / TexAnm eye animation use them); Sora = materials 4–5
  (extras.base_material = 2, new in gltf2gmo.py), textures 256².
- Build: `fit_sora.py kh2_export/model/sora.glb dumps/models/cloud_1p/01193_1b867bde_t1.gltf dumps/models/sora/fit`
  → `gltf2gmo.py dumps/package/01193_1b867bde_t1.gmo dumps/models/sora/fit/sora_fit.gltf dumps/models/sora_body.gmo`
  (2,175,528 bytes, model-0 481 KB vs Cloud 320 KB, 48 meshes, palettes up to 8 bones)
  → `pkg_put.py ISO obj/P_SEV120_1P.gmo dumps/models/sora_body.gmo`.
- gmo2gltf.py fixed: palettes > 4 bones kept only weights 0–3 (arms looked like sticks); now keeps the 4 largest.
  Renders: dumps/renders/sora_fit_*.png (fit), sora_rt_*.png (GMO read back) — clean.
- Still Cloud's sword (weapon parts copied). Open risks for the in-game test: 8-weight vertices (Cloud uses ≤ 5),
  bigger model-0, 8 textures instead of 6.
Test 29 ✅ (in game, 2026-10-13): Sora renders and animates on #33 (entrance, close-up, fighting) —
dumps/screens/test29/. 8-bone palettes, the bigger model-0 and 8 textures are all fine. (ISO deleted; test 30 has it.)

## Keyblade — test 30 ✅ `dumps/ULUS10566-test30-key.iso` (= test 29 + Kingdom Key)
- Cloud's weapon parts: **wep0 = Buster Sword (normal; texture p_sev100_wep01, grey)**, **wep1 = Ultima Weapon (EX Mode;
  p_sev100_wep02 + animated glow p_sev100_wep02a via TexAnm "2_WEP")** — checked 2026-10-13 (test 57 had them swapped).
- `tools/scripts/add_keyblade.py SKIN.gltf kingdom_key.glb OUT_DIR [wep0,wep1] [FLIP]`: Keyblade grip (its Bone0)
  → r_wep, long axis → Buster Sword axis (PCA), ×1.1, teeth side FLIP=1 (used: teeth down like the sword's edge).
  Material template 1 (Cloud's sword), texture 256×128. Both parts replaced → `REBUILD_WEAPONS=1 NEW_SCALE=1`.
- dumps/models/sora_key.gmo (2,224,020 bytes, model-0 530 KB, 9 textures) → obj/P_SEV120_1P.gmo.
- In game: Sora holds the Kingdom Key (guard + chain visible), follows the hand in combos (dumps/screens/test30/).

## Real size + fist — test 31 ✅ (size) / test 32 `dumps/ULUS10566-test32-fist.iso` (fist; not seen in game yet)
- Cloud's motions key every non-moving bone's translation as a 1-key constant (= bone length in the parent frame);
  only camera2_include, camera_include, root, r_wep, trans_include (and belt/shldarmor slightly) really move.
  fcurve formats: 0x80 (1 key / step), 0x81 linear vec3, 0x84 quaternion keys (x, y, z, w); keys = half frame + values.
- `tools/scripts/gmo_resize.py BASE.gmo sora.glb OUT.gmo`: per-bone length ratios Sora/Cloud (RATIO_L table),
  scales rest 0x8048 (both models), DISTANCE, every translate fcurve (in place, file size unchanged), recomputes the
  inverse binds; hip drops 0.070 (root Y −0.070, draw bones p_sev100/wep0/wep1 +0.070). Shoulders ×0.52, thigh ×0.79.
  → dumps/models/cloud_sorasize.gmo (+ .joints.json); gmo2gltf → dumps/models/cloud_sorasize/.
- fit_sora.py NATURAL=1 (no widening) on that skeleton → Sora 1.69 m. Hand pose baked in: right fist (CURL r),
  left relaxed; writes sora_fit.grip.json (fist centre + axis) which add_keyblade.py uses (KEY_SCALE=1.0).
- Previews: `gmo_anim2gltf.py MODEL.gmo SKIN.gltf OUT.gltf _000A …` + `tools/blender/render_anim.py`
  (front/side/back/rside/top, focus bone). Build recipe: scratch build_nat.sh steps =
  fit_sora (NATURAL) → add_keyblade (KEY_SCALE=1.0, wep0,wep1, FLIP 1) → REBUILD_WEAPONS=1 NEW_SCALE=1 gltf2gmo
  (base cloud_sorasize.gmo) → pkg_put obj/P_SEV120_1P.gmo.
- Mat (2026-10-13): looks good; Keyblade clips the hood in Cloud's win pose; idle looks like crossed hands (Cloud's
  two-handed sword idle on Sora's narrow shoulders). Both → Sora's own KH2 animations (next).
- Beeps Mat heard = menu error sounds from my blind Circle/Square presses on the VS screen. Use Cross there.

## KH2 animations → Dissidia (2026-10-13) — tests 33 ✅ (stance), 34 (grip fix)
- `tools/kh2bake/bake` (C#, .NET 8 SDK in tools/dotnet-sdk, run with DOTNET_ROLL_FORWARD=Major): uses OpenKH's
  `OpenKh.Kh2AnimEmu.dll` (emulates KH2's own animation code incl. IK/constraints; the FK-only Kh2MotionEngine is
  NOT enough). `bake MDLX MSET OUT_DIR list|all|IDX…` → per-frame bone world matrices (KH2 cm, Y up; glTF = 0.01×).
  Time unit = 1/60 s (frame f → 60/fps·f). Slots = motion id ×4 + variant (v0 = battle with weapon).
  Named list: dumps/kh2anim/list_named.txt (89 slots in P_EX100.mset: IDLE 0, RUN 8, EX000–004 ground combo,
  EX010–016 air combo, REFLECT 164 (guard), magic 224–292, CALL_SUMMON 554, CHANGEFORM 210 …).
  Forms/other msets: P_EX100_BTLF/MAGF/TRIF/ULTF/KH1F (Drive forms), _LAST, _HTLF …
- `tools/scripts/kh2anim.py`: load baked frames, pose the KH2 mesh (OBJ) — checked the IK-correct stance.
- `tools/scripts/kh2_retarget.py MODEL.gmo sora_fit.map.json BAKED.bin OUT.gmo _000A [a-b] [KEEP_LEN]`:
  Dissidia bone world(t) = K_s(t)·A_s⁻¹·bind_c (K = KH2 skinning matrix, A = fit map of the driving KH2 bone),
  local rotations solved down the hierarchy, root carries the hip. Writes a whole new motion block
  (0x80B1/0x80B2/0x80B4, 0x80B3 entries, fcurves 0x84 quats / 0x81 root / 0x80 constants). _000A = idle ✅.
- Keyblade: KH2's "attach to palm bone 178 + weapon bone 0" guess made it hang down below the hands (Mat's
  screenshots, test 33) → wrong. Kept the fist-axis grip (blade out of the thumb side = points up in the KH2
  stance, like KH2). Fist loosened (CURL r 65/85/50) and the grip auto-centred in the hole (centre_in_fist).
- Win pose `_910A/_911A` is still Cloud's (Keyblade over the shoulder, hand floating) → needs a KH2/hand-made pose.
- One command: `tools/scripts/build_sora.sh [ISO_IN ISO_OUT]` (MOTIONS list inside = slot=KH2 index).

## Win poses + hand-made animation (2026-10-13) — test 37 `dumps/ULUS10566-test37-winposes.iso`
- Baker speed control: env STEP=0.5 (half speed) or SPEED="0.5:1,1:0.4" (normal first half, then 0.4×).
- `tools/scripts/pose_author.py POSE.py MODEL.gmo OUT.gmo SLOT`: key poses from helpers (kh2(index, frame) as a base,
  aim(bone, dir), aim_keyblade(dir), turn(bone, axis, deg), move_root) → eased slerp in-betweens → motion slot.
  Pose files in tools/poses/. Preview: `tools/scripts/preview_pose.sh POSE.py LABEL` → dumps/renders/poses/pose_LABEL.gif.
- Mat picked: _910A = hand-made "Fire" (twirl → Keyblade on shoulder, hand on hip; line "It's over!"),
  _911A = KH2 MAGIC_FIRE_FINISH (228) normal speed then slow-mo. Hand-made "Light" = too simple (dropped for now);
  summon (554) liked but too short. Gallery: dumps/renders/poses/index.html.
- build_sora.sh MOTIONS syntax: SLOT=IDX, SLOT=IDX@STEP, SLOT=IDX~SPEEDS, SLOT=pose:FILE.py.
- KH2 battle voice clips transcribed (dumps/kh2anim/voice_text.tsv, tools/scripts/transcribe.py): "It's over!",
  "Back off!", "Give me strength!", "LIGHT!" … — win lines will come from KH2 story voices (Mat).
- Intro (test 38 `dumps/ULUS10566-test38-intro.iso`): _900A = tools/poses/intro_a.py (Keyblade on shoulder, left hand
  scratching the back of his head, grin), _902A = intro_b.py (swing off the shoulder, twirl, into KH2 stance = idle
  frame 0). Cloud's camera curves kept. Preview of any slot: `tools/scripts/preview_slot.sh MODEL.gmo SLOT LABEL`.

## Motion play range = LOOP range (found 2026-10-13, Mat saw the win pose repeat)
Keys of Cloud's _910A run 0–175 but 0x80B1 says 111–175; _911A keys 0–80, range 38–80. The game plays from frame 0 to
the end once, then loops the 0x80B1 range. kh2_retarget.write_motion now always keys from 0 and, for slots whose old
range started > 0 (win poses), loops only the last LOOP_TAIL (6) frames → the final pose holds.
Win "Fire": left hand on hip fixed (was through the torso). Test 39 `dumps/ULUS10566-test39-winfix.iso` (+ intro).
Recording the game window only: `tools/scripts/record_game.sh [SECONDS]` → dumps/screens/rec_*.mp4 (ffmpeg -window_id).

## Win vs loss (confirmed live 2026-10-13, tools/scripts/ppwinwatch.py)
Results scene FUN_08b0a090: task +0xC flag = 1 → motion id 1200 on fighter task[8]; 0 → id 1210 on task[9].
Logged: Lightning (31) beat #33 → flag 0, 1210 played on #33 (the loser). Motion table in the fighter file (p_se type 7
chunk, rows u16 id, u16 motion index, …): 1100→82 _900A, 1110→83 _902A, 1200→84 _910A (WIN), 1210→85 _911A (LOSS),
901→6, 911→7, 1120→0. So _910A = win pose, _911A = defeat pose (not "win 2"). EX Mode is not involved.
Now: _910A = tools/poses/win_combo.py (KH2 Fire finisher normal→slow, then twirl → Keyblade on shoulder; Mat: "perfect"),
_911A = loss_kneel.py (hit → one knee, Keyblade planted, breathing loop LOOP=40). Fist tightened: CURL r 85/100/65,
thumb 50/55 (Mat saw open fingers in the idle). Test 41.
Win twirl: 3 spins (win_fire.py TWIRLS = 3, Mat's request) → test 42 `dumps/ULUS10566-test42-spins.iso`.
Intro timing (recording 2026-10-13, test 37): only _900A is really on screen (~2.3–2.7 s, after a white fade);
the battle starts right after, so _902A is (almost) never seen. → intro_a.py does the whole intro and ends in the KH2
stance (idle frame 0) at frame 66; intro_b.py = first 69 idle frames. Test 43.
Guard roll fix (test 44): with the tight fist the finger centroid sits on the handle → random roll (guard bar
through the hand in the win hold). add_keyblade.py now rolls the guard towards the palm normal (fit map of (0,-1,0),
written by fit_sora.py as grip.json 'palm_normal'); the finger centroid is only a fallback.
Test 45: intro stays standing ("ready", Keyblade low/forward) until frame 70 and drops into the stance at 72–78
(the intro camera is game code aimed at standing height — camera bones in the motions are all constant 0 — so it
does not follow a crouch). Loss legs fixed with `tools/blender/ground_check.py MODEL.gltf ANIM FRAMES` (lowest point
per body part above the floor): HIP 0.56, right shin flat, right foot flat, left knee higher → all within ±1 cm.
Check every new pose with ground_check.py.
Test 46: intro has NO crouch at all (Mat: camera saw only his hair, worst in the short intro after Retry). _900A ends standing "ready" and holds; _902A holds the same pose; the crouch happens when the idle starts with the fight.
Test 47: win hold fist moved forward/out (r_foarm (-0.25,0.8,0.55)) → guard 5 cm clear of the head
(`tools/blender/clip_check.py MODEL.gltf ANIM FRAMES [PARTS]` = Keyblade-to-body distance). _902A = transition
ready → stance (frames 6–20) then idle frames 102–150 (ends where the idle starts); pose scripts can set LOOP, which
write_motion now honours for any slot (so only the idle part of _902A loops).

## Motion ids → GMO slots and the KH2 movement set (2026-10-13, tests 48–49)
Live logging: `tools/scripts/ppplay.py PORT OWNER STEPS…` presses inputs (buttons, combos "rtrigger+cross",
analog "stick=X,Y") AND logs the fighter's motion id (u16 at fighter+0x180) on ONE debugger connection (PPSSPP serves
one at a time — a second logger connection stalls). Motion id → GMO motion = fighter file p_se type-7 table.
| id | slot | what | KH2 (build_sora.sh) |
|---|---|---|---|
| 1 | _000A | idle | 0 IDLE |
| 2 | _010A | run (analog stick; d-pad does not move) | 8 RUN, loop all |
| 100/101/102 | _020A/_021A/_022A | jump / in air / land | 14 JUMP / 18 FALL loop / 22 LAND 0-14 |
| 103 | _023A | double jump | 806 (B003 flip) |
| 400 / 440 | _100A / _140A | dodge (R+X) ground / air | 838 (A180 dodge roll) / 818 @0.5 (A151) |
| 470 / 471 | _160A / _161A | block (R) ground / air | 164 REFLECT / 172 REFLECT_AIR |
| 500 / 501 | _200A / _201A | hit standing | 42 / 46, frames 0-12 |
| 550,560 / 561 | _210A / _211A | hit in the air | 58 / 62 |
| 700 / 701 / 702 | _400A / _401A / _403A | blown away / flying / land + get up | 66 / 66:4-7 loop / 70 |
| 754 | _414A | air recover | 162 |
All animations are in place (no root travel; the game moves the body). Test 49: CPU Average beat Sora up for 35 s,
all reactions played, no glitches (dumps/screens/test49/hits_sheet.png).

## Attacks — KH2 swings timed to the game's hitboxes (test 51 `dumps/ULUS10566-test51-attacks.iso`, 2026-10-13)
Cloud's attack pieces (plya) → motion id → slot → hit windows (script op 0x00/0x43, frames of the animation):
LAND_NEAR1 _600A 16-24 | NEAR2 _601A 16-22 | NEAR3 _602A 34-42 | NEAR1_2 _600B 10-16 | MIDDLE1 _610A 24-38,36-42 |
MIDDLE2 _611A 6-16 | MIDDLE3 _612A 26-32 (air) | NEAR4 _640A 20-30 | LONG1 _702A 34-40 | AIR_NEAR1 _620A 18-26,34-42 |
AIR_NEAR2 _620B 32-42 | AIR_NEAR3 _621A 30-38 | AIR_MIDDLE1_1 _630B 18-46 | AIR_MIDDLE1 _630A 20-60,66-72 |
BR_A_REN1/2 _650A 10-16 / _651A 16-22 | HP: LAND_FINISH1 _700A 38-44,76-82,116-122 | FINISH3 _703A (10 hits) |
AIR_FINISH1 _704A 44-64 | FINISH2 _704B 26-44 | FINISH3 _706A (6 hits) | FINISH2 _705A / METEO _707A no hitbox events.
KH2 attacks (dumps/kh2anim/list_named.txt): EX000–EX022 (A300–A322) ground (end in stance), EX030–EX046 (A330–A346)
air (end in air pose). `tools/scripts/kh2_attack.py MODEL BAKED OUT SLOT HIT [HIT2]`: impact = fastest Keyblade-tip
frame(s) of the solved pose; piecewise-linear time warp impact → hit frame, KH2 end → slot's old end (combo windows
keep the game's timing); two impacts only if ≥ 6 KH2 frames apart. build_sora.sh `SLOT=atk:IDX:HIT[,HIT2]`
(GROUND/AIR lists). In game: ground/air attacks play and connect (dumps/screens/test51/atk_sheet.png). HP attacks
are still Cloud's.
**Correction (same day): script frames run at 60 per second, motion frames at 30.** Hit windows above are script
frames; Cloud's own sword peaks sit at half of them (`tools/scripts/gmo_fk.py MODEL MOTION r_wep`: _600A 16-24 → peak
9, _700A 38/76/116 → 19/39/58). kh2_attack.py / kh2_combo.py now take script frames and halve them. Test 51's
attacks were timed to the doubled frames (swings late) → fixed in test 52.

## EX Mode weapon (test 57 `dumps/ULUS10566-test57-exkey.iso`, 2026-10-13) ✅
- wep0 = normal weapon, wep1 = EX Mode weapon (Cloud: Buster Sword / Ultima Weapon). Sora: wep0 = Kingdom Key,
  wep1 = KH2 **Ultima Weapon** (W_EX010_N0). Seen in game: Kingdom Key normally, Ultima Weapon in EX Mode (+ green
  tint = Cloud's EX aura, from the .exex effect entry / TexAnm). Oathkeeper + Oblivion exported too (EX_KEY=...).
- `tools/scripts/kh2_mdlx2gltf.py MODEL.mdlx TEX OUT_DIR NAME`: any KH2 model → glTF without Blender (OpenKH decoder
  adapted; bone translations cm→m only). Exports in kh2_export/keyblades/{ultima_weapon,oathkeeper,oblivion}/.
  add_keyblade.py: any keyblade glTF, texture name per keyblade, GRIP_JSON for a second pass.
- **EX gauge (US)**: float at *(fighter + 0x52C) + 0x18, 0..10000 (from the EU CWCheat "player EX Max", same
  offsets). Write 10000, then R+Square while NOT being hit (R+Square during a hit = EX Revenge). Motion 3000 = EX
  Revenge pose. ppplay find_fighter(ws, owner) gives the fighter.
- .exex (P_*_1P.exex): u32 version 2, u32 count, count × 80-byte entries, each initialised by LAB_08842f70
  (Cloud: 1 entry, u16 41 = bone? + colour + floats) — probably the EX aura; not changed.

## Motion flag 0x80B4 = loop (found 2026-10-13, tests 58+)
Cloud: 1 on _000A (idle), _010A (run), _051A, _070A; 0 on one-shots (attacks, hits, dodges, intro…); absent on 12
(_020A/_021A/_023A jumps, _910A/_911A, …). kh2_retarget.write_motion used to write 1 everywhere → combo FINISHERS
missed (Mat: ground 4th / air 3rd hit). Now copies the slot's own value (or leaves it out). Air finisher (10022)
lands after the fix (4/5 tries). Ground 4th hit (10224 = our own variant of MIDDLE3 on _612A) still misses → bisecting.
Combo test harness: `tools/scripts/test_combo.sh BASE.iso MODEL.gmo [BUTTONS] [TRIES]` (builds a disc, drives into a
battle, runs `ppcombo.py`: puts #33 1.5 m in front of Lightning, presses, logs both motion ids; O5xx/6xx/7xx = hit).
`tools/scripts/motion_mix.py` = take bones from another GMO's motion for a frame window (bisecting).
Bisect results so far (5 tries each, correct flags): Cloud's root+hip only → 10224 reached 1×, missed; Cloud's whole
body except root (spine, arms, legs, r_wep) → reached 3×, missed. Cloud's _612A animates only root:T (lunges +0.3 m
forward right at the hit frame 14), r_wep:R and shldarmor:T — no trans_include. Next: root+hip+r_wep together, and the
whole Cloud motion as a control (7 tries each).
Control: whole Cloud _612A (gmo_motion take) → finisher lands 4/4. root+hip+r_wep from Cloud → 1/5. Next: every bone
from Cloud but written by kh2_retarget.write_motion (tests whether the pose or the curve encoding matters).
All bones from Cloud via write_motion → 4/4 land (pose matters, not encoding).
Root→weapon chain (root,hip,waist,chest,r_clavicle,r_uparm_c,r_uparm,r_foarm,r_hand,r_wep) from Cloud → 3/3 land. ⇒ the hitbox follows the WEAPON's world position (r_wep). Fix: blend that chain to Cloud's around the hit frames (kh2_attack.py MATCH).
Result (test 59 `dumps/ULUS10566-test59-finishers.iso`): ground finisher lands 3/3 when reached, air finisher lands
too. kh2_attack.py MATCH=1 (build_sora.sh `atk:IDX:HIT:match`) blends CHAIN (root…r_wep) to the slot's original
motion on hit frames −2…+3 with 4-frame ramps. If another KH2 attack ever misses: add `:match` to its slot.

## EX Burst (2026-10-13, tests 59–60) ✅
- Trigger (US, owner 33 vs Lightning 31): `tools/scripts/ppexburst.py PORT 33 31 SECS` (env TRIES, SHOTS=dir = one
  picture of the game window per motion change, MASH=frames per Circle tap). Fills the EX gauge, R+Square = EX Mode,
  teleports next to the opponent, HP attack, R+Square while it hits → burst, then taps Circle. Stops by itself when a
  win/loss pose (1200/1210) shows (it once tapped into the replay-save dialog), waits ≤ 60 s for the battle.
- Motion ids (p_se type 7, pkg 3394) → script block = GMO motion index → Cloud's slot:
  8000 _801A (opening, hits script 12-16 / 52-58), 8101 _801B ("Rapidly tap ◯" + Limit bar, no hit),
  path 1: 8102 _802A, 8103 _803B, 8104-8106 _804A-_806A (variant 1), 8107 _807A, 8108 _812B (9 hits 4-136);
  path 2: 8109 _803A, 8110-8112 _804A-_806A (variant 2, hit 0x77F), 8501 _812A (final blow, hit 120-126);
  8500 _812C (hits 92-122), 8600 _813A. Slashes: op43 hit 0x3AF at script 20-26. Both paths seen in game (path 2
  once in test 59, path 1 four times — not tap speed; reason unknown).
- Cloud's burst shots place him with the ROOT bone (metres around the enemy: _802A z −4.75, _812A z −6…−13,
  _805A y +1.7), camera = camera bones copied by write_motion. So Sora's shots use `burst:` entries in
  build_sora.sh = kh2_combo.py with FOLLOW=1 (root X/Z + facing from Cloud's shot, KH2 height change added) and
  MATCH=1 (root→weapon chain blended to Cloud's at every hit). Test 60 `dumps/ULUS10566-test60-burst.iso`: whole
  burst plays with Sora's KH2 moves, framed by the camera, hits land (Critical, Bravery rises). Clips: _801A 644+664,
  _801B 210 (Drive Form pose, held), _802A 814 / _803A 822 (glide poses), _803B-_807A 724/728/732/736/768, _812A 776,
  _812B ground combo ×2, _812C 788, _813A 22. Previews: dumps/renders/poses/slot_burst_*.gif; in-game pictures
  dumps/renders/exburst/test60_burst_shots.png.
- Still Cloud's: banner names "Limit Break" / "Omnislash" (and "The power of mako!" EX Mode, "Braver", "Crushing
  Blow", "Cross-Slash"), Cloud's voice lines in the burst? (not checked), the VS screen says "Cloud Strife" for #33.

## In-battle banners (test 62 `dumps/ULUS10566-test62-banners.iso`, 2026-10-13) ✅
- Move/EX names in battle are NOT ability.bin (menu "Cross-slash" vs banner "Cross-Slash"): they are the fighter
  file's `text` chunk ("mlng", 6 language blocks, US uses block 0). Format + font codes: header of
  `tools/scripts/spot33_battlenames.py` (XOR like ability.bin, entry 0 = end of data in u16 units — dropping it gave
  garbage in test 61; codes = ASCII+0x1F capitals, +0x19 small, +0x26 digits, LEB128 when ≥ 0x80).
- Cloud's: 1 Omnislash (burst), 2 LIMIT BREAK, 3 Rapidly tap ◯!, 4 Cross-Slash (ground HP), 5 Meteorain,
  6 Finishing Touch, 7 Braver (air HP), 8 Omnislash Version 5, 9 Equipped Ultima Weapon!, 10 The power of mako! (EX Mode).
- Sora's (build_sora.sh step): 1 Ars Arcanum, 4 Firaga, 5 Ragnarok, 6 Finishing Leap, 7 Aerial Finish, 8 Sonic Rave,
  10 My friends are my power! Seen in game: EX Mode, Firaga, LIMIT BREAK, Ars Arcanum (dumps/renders/exburst/test62_banners.png).
- `wind` chunk = banner backgrounds (blue/pink); type-3 `spec` chunk = burst UI picture (◯ button, LIMIT bar).
- Still Cloud: VS screen / loading name "Cloud Strife" for #33 (encount/name pictures + name table, notes/roster.md test 22).

## EX Mode "form change" lead (2026-10-13, unfinished)
- Terra's P_SIX100_1P.gmo has TWO model blocks: model-0 and **model-0-0000** (her Trance form), each with a body
  part p_six100 + wep0. Cloud/Squall/Tidus GMOs have only model-0 (parts body, wep0, wep1). No separate EX .gmo files.
- .exex/.cosx show no obvious switch flag. EX Mode start script (motion 5000): Cloud block 38 = op0a, op1e, op14(0,2);
  Terra block 41 adds op1b(0x3f) and op14(0,3)+op14(1,3). op14 appears on many attacks/hits too (not the switch).
- Test 67 (Terra's GMO as #33's model, Cloud's fighter file): no crash, but #33 lost on its own within ~1 min
  twice, EX Mode never reached → inconclusive; disc deleted. Next idea: give Sora's GMO a model-0-0000 copy and
  watch which model the renderer draws in EX Mode (or find the code that reads the model count).
- Tool: tools/scripts/go_battle.sh/.py = screen-recognising driver (refs in tools/scripts/screen_ref/); use it
  instead of blind press lists. After a battle ends do NOT press Square (= Save Replay).
- KH2 form models available for an EX look (same rig as P_EX100): P_EX100_ULTF (Final), _BTLF (Valor), _MAGF (Wisdom),
  _TRIF (Master), _KH1F (Limit Form, KH1 outfit), _HTLF (Anti) in kh2_export/raw/*/original/obj/ (+ _NM/_TR/_WI world
  variants). Mat still to pick (my pick: Final Form). Needs the EX model-switch (model-0-0000 lead above).
- Test 70 (2026-10-13): Sora GMO + silver copy as model-0-0000 (tools/scripts/gmo_add_exmodel.py) = 2,821,156 B →
  game hangs on a white screen after "Enter Battle" (never reaches VS). Terra's 2-model GMO is 2,097,744 B; Sora's
  1-model GMO 2,248,956 B. ⇒ fighter GMO size limit is somewhere in 2.25–2.82 MB. A form model needs smaller
  textures (e.g. drop/shrink texture-1, file15/17/19, share textures) — or swap textures only.

## Dash + remaining Cloud motions (test 78 `dumps/ULUS10566-test78-dash.iso`, 2026-10-13)
- Triangle in the air = dash: motions 202 (_070A start) → 203 (_051A loop) → 201 (_052A end) (seen live with
  ppplay). build_sora.sh DASH: _070A=810 (KH2 A160), _051A=814#all (A150 glide pose), _052A=18 FALL, ground dash
  _071A=814#all, _072A/_074A=22 LAND 0-14 (ground dash ids 209–212 not seen live yet).
- Still Cloud's motion (resized), ids → slot: 220/221/243 _060A/_061A, 240/242/244/800 _500A, 241/801 _501A,
  300/822 _170A, 410 _120A, 460 _150A, 600/610 _300A, 601/611 _310A, 703/704 _404A, 750 _410A, 751 _411A,
  752 _413A, 810/820 _510A, 811 _511A, 812/815/816 _512A, 813/821 _520A, 901 _041A, 911 _043A (911 = recoil after
  hitting a block). Previews of Cloud's versions on Sora: dumps/renders/poses/slot_cl_*.gif. Several (_5xx) look
  like attacks (probably Chase / wall-rush) → need hit timing like the attacks.
- Test 79 (`dumps/ULUS10566-test79-hits.iso`): HITS += _300A=42 _310A=46 (600/601 combo follow-up hits),
  _410A=74 _411A=74:4-7#all _413A=78 (750-752 blown-the-other-way set, built like 700-702), _043A=50 (911 recoil
  after hitting a block), _041A=54 (901). 60 s of Lightning beating idle Sora: 500 501 560 561 700 701 750 751
  seen, no glitches (dumps/screens/test79/h_sheet.png). Still Cloud: _060A/_061A, _120A, _150A, _170A, _404A, _5xx.
- Live ids: Triangle on the ground while running = ground dash 209 → 210 → 211 (DASH map ✓). R+Triangle = call the
  Assist: 240 (_500A), assist slash hits (Lightning's Bravery drops) — once followed by 911. Test 80
  (`dumps/ULUS10566-test80-assist.iso`): ASSIST _500A=550 / _501A=550 (KH2 CALL_FRIEND). Plays, no glitches.
  Still Cloud: _060A/_061A (220/221/243), _120A (410), _150A (460), _170A (300/822), _404A (703/704),
  _510A-_520A (810-822, assist-related?).
- Test 80 sanity (2026-10-13): EX Mode, Firaga banner, EX Burst ("LIMIT BREAK", Ultima Weapon) all fine.
  Burst tests: use `EASY=1 tools/scripts/go_battle.sh ISO` (stage Order's Sanctuary, CPU strength lowest) — on random
  stages / Average CPU the HP attack rarely lands and Sora loses fast. ppexburst.py now also starts when #33 is busy
  being hit (after 3 s).

## Intro camera — live findings 2026-10-14 night (test160, camera helper; NOT solved yet)
- Live view camera = eye point, eye + unit look dir, up (0,1,0,0), 16-B vectors; copies at 0x08baead0 / 0x08c11500
  (+ heap). Written via FUN_088a5f1c (vector copies FUN_089a3868); main view camera object = *(0x089d5ec0) (+0x720
  view, +0x7e0 lens/zoom), its writes come from 0x0885e9f0 (FUN_0885e9xx set eye/dir/up + FUN_0885e860 update).
- Both fighters play motion 1100 (_900A) AT THE SAME TIME (u16 fighter+0x180: 1100 for ~5.5 s, then 1110 _902A
  ~3 s, then 1). The shots cut between the two fighters.
- Snapshot during the bad "only hair" close-up (rec_20261014-231812.mp4 ~19-31 s, frozen while paused): eye 0.66 m
  above Sora's feet, 2.2 m away, pitched up ~22°. Medium shot before it framed him fine.
- Candidate sources ruled out / open:
  - Bone camera (FUN_0886b6bc: camera bones camera_include / camera2_include of the current motion; model+0xe8/+0xec =
    bone 1 / 0; used by FUN_08805a38 when fighter+0x580 & 0x100 and & 0x40/0x80, and by camera-manager mode
    FUN_08b3e6d0 with camr entries). Cloud's AND Sora's _900A have NO camera_include curve and camera2_include = 0
    → the intro is most likely NOT bone-driven (unproven: watch fighter+0x580 during the intro).
  - battle.bin `camr` chunk (package 06409 MPK member battle.bin, chunk at +0x4520, 1472 B): header floats
    0x10-0x390 (distances 1.5/3/6, fov 50, 0.89/0.25 screen fractions…), 10 entries × 0x38 from +0x390 (+0x30 look
    distance, +0x34 flags: 4 = add fighter pos, 2 = add other fighter, 8 = keep bone up). Not per-character.
  - 1.7 m = const 0x089c7540 × zoom FUN_0887357c(main camera object + 0x7e0; the object pointer is at 0x089d5ec0): half-size of a box around the focused fighter
    (FUN_0881d900 area, struct 0x08b632a0: +0x80 fighter ptr, +0xc0 fighter pos + 0.9, +0x90 = 1.7). Not char-specific.
- Camera manager OBJ_CAMERA_MANAGER (FUN_08b3ca24): 8 camera slots (+0x6d0), blends, mode objects per camera
  (+0x108 mode, +300 mode table, FUN_08b3b3ec(cam, mode)).
- NEXT (needs the game): break on writes to the eye at 0x08baead0's SOURCE during the close-up (watch
  *(0x089d5ec0)+0x720 write PC 0x089a2b18, ra 0x0885e9f0 → step up one more caller via sp/ra chain), or poke
  candidate height values live during the intro and watch the eye change. Tools: scratchpad cam/catch.py (snapshots
  at chosen seconds after 1100 starts), cam/mbp.py (memory-write breakpoint logger, starts from opp_info, cleans up).
- Correction: the writes at *(0x089d5ec0)+0x720 (PC 0x089a2b18, ra 0x0885e9f0) are FUN_0885e860 rebuilding the view
  matrix every frame, not the source. The eye SOURCE = the caller of FUN_0885eaa8 (set eye) on the main camera:
  FUN_08805a38 (bone camera), FUN_08b3ca24 (camera manager blend), or two other callers.
  Next live test: CPU breakpoint on FUN_0885eaa8 (0x0885eaa8) during the close-up, log ra → which path drives the
  intro, then follow that path's height input.

## Intro camera — SOLVED 2026-10-15 (test161, tools/scripts/spot33_introcam.py)
- The intro camera is NOT in the body GMO and NOT in the motion's camera bones. Every fighter file has its own small
  CAMERA model: objx chunk `d_se` type 2 = GMO "OMG.00.1PSP" (24 KB), bones dummy / camera2_include /
  camera_include, 9 camera motions (_010A _020A _200A _201A _202A _203A _500A _501A _510A).
- Chain: battle-start script FUN_08b10210 → FUN_08b3ae14(0, fighter+0x5ac camera, path id = the s16 at cmd+2, 0, 7)
  (camr entry 7) → FUN_08b3efcc / FUN_0880fd34 (path id → camera motion via the table at holder+0x94 → +0x1c, holder
  = camera data +0x1e0, model +0x98) → each frame FUN_08b3eb6c → FUN_0880fec8 → FUN_0886b6bc reads the camera bone:
  translate = eye (relative to the fighter), rotation (-Z look, +Y up), scale z = FOV. Camera data object: +0 eye,
  +0x20 eye goal, +0x40 target, +0x60 target goal, +0x80 up (FUN_08b3e954 blends goals).
- Intro paths: _200A (80 f, with body motion 1100), _203A (68 f, with 1110: the close-up, FOV 50 → 16 → 50),
  _201A/_202A (shorter intro after Retry). Keys: fmt 0x82 = Hermite, per key frame + 3 × (value, in, out) halves.
- Sora's camera model was Cloud's copy → close-up aimed at Cloud's face (≈1.58 m) = over Sora's hair. Onion Knight
  (own camera model) aims ≈1.17 m.
- Fix: spot33_introcam.py scales the camera POSITION keys (values + tangents) of _200A-_203A by Sora/Cloud head height
  (1.406 / 1.586 = 0.887) about the fighter's feet; rotations + FOV unchanged → same framing as Cloud's, at Sora's size.
  Re-runnable (always starts from Cloud's p_sev100.objx camera model in the same ISO). Proof: test161 recording
  dumps/screens/rec_20261015-012218.mp4, sheet dumps/screens/introcam161/sheet.jpg (row 4: face close-up).
- Build line (after spot33_fx.py): `python3 -I $S/spot33_introcam.py "$2"`.
- Not done: win/loss cameras (_010A/_020A = results, frames 140-400) are still Cloud-height too — same scaling would
  apply (add them to SLOTS after a look).

## Keychain bones (2026-10-15, tools/scripts/keychain.py — static + Blender previews only, NOT seen in game yet)
Mat: "keychain bones so that it's not part of the rigid keyblade". Before: chain + Mickey token were rigid wep0
vertices (100% r_wep) → straight out behind the grip in every pose.
- Chain = wep0 mesh-49 (98 verts, 0.198–0.52 m behind the grip along the blade axis); token = 62 verts of the blade
  mesh (mesh-48) below 0.49 m (split at the largest gap; the pommel cap just behind the grip stays rigid).
- Weapon parts are drawn through the draw bone's skinning list like the body: wep0 0x8044 = [r_wep] → extended to
  [r_wep, kchain1..4] + 0x8045 inverse binds; the chain mesh gets palette 1-4 (2-bone blends at the links), the
  token a new mesh on kchain4 (palette [4]). Vertex positions/UVs unchanged (same model box).
- Bones: 4 NEW bones appended at indices 54-57 (kchain1 parent r_wep at the pommel, kchain2/3 links, kchain4 token
  pivot), in BOTH models (_000A + model-0). Appended rather than re-using free bones because every free bone
  (hair, r/l_arm_help, shldarmor, belt are in no body palette; skirt*/belt1* are free too) comes BEFORE r_wep (50)
  in the list — if the engine evaluates bones in list order a child of r_wep must come after it.
- Side find: p_se type 6 (644 B) = the engine's own bone PHYSICS: 8 chain entries on bones 15/16 (skirt2b/a),
  18/19 (skirt3b/a), 24/25 (skirt1b/a), 22/23 (belt1b/a) with ±angle limits and 2 parameter groups (gravity/damping
  floats at +0x24/+0x4c). Cloud's coat tails. Alternative later: hang the chain on such engine-simulated bones
  (real in-game swing) — needs re-parenting + bone-order check in game.
- Motion: build-time verlet chain (gravity 9.8, damping 0.96, 4 substeps, 45-frame settle, loops simulated twice)
  driven by the motion's own r_wep world track; written as kchain1-4 rotation keys every KEY_STEP frames
  (+ constant translate, shared scale curve). Default motions _000A _900A _902A _910A _911A.
- Motions WITHOUT chain curves rely on the engine leaving bones without curves at their rest pose (straight chain =
  old look). Unverified in game; if it misbehaves, give every motion a constant rest curve set (~450 B/motion).
- Size: +18.9 KB (default, KEY_STEP 2) → 2,517,912 B; lite (KEY_STEP=3, _000A _900A _910A) +11.1 KB → 2,510,064 B.
  The GMO size limit is unknown (build_sora.sh comment: 2.25-2.82 MB; the win-pose "vanish" once happened when big).
- Previews (before | after): dumps/renders/keychain/keychain__910A.gif, keychain__000A.gif, keychain__900A.gif
  (dumps/models/keychain/preview.sh MOTION renders them; textures from dumps/models/sora/rtn, wep1 hidden).
- Build: run LAST on the model (after MOTIONS + STUBS), into a separate file so the pose/preview tools that read
  sora_final.gmo don't meet the new bones:  keychain.py sora_final.gmo sora_final_kc.gmo → pkg_put that.

### Keychain v1 → v2 in game (2026-10-15 night)
- v1 (58 bones, +19 KB) CRASHED at battle start: PPSSPP "Invalid Memory Access at 0000100c, PC 0885c8a0" in
  FUN_0885c6cc = a heap allocator (free-list walk). Address 0x100c = NULL + 0x100c → an allocation FAILED and the
  caller used the null result: most likely the fighter's model memory budget (size), not the bone count as such.
  Same disc with the 54-bone model (test189-nokc, 2,499,324 B) works.
- v2 (tools/scripts/keychain.py now; dumps/models/keychain/keychain_v2_4bones.py): 54 bones, re-uses belt(28) →
  shldarmor(38) → hair(41) → r_arm_help(45) (in no Sora palette, already in the body skinning list at 20/19/4/7),
  belt re-parented to r_wep; chain + token become body-part meshes; every motion's curves for those bones rewritten
  in place to the chain rest pose, their old per-frame curves DELETED (dead), wep0 blade array compacted →
  NET −3,384 B (2,495,940 B), smaller than the working model. Motions validated (104, no bad fcurve refs).
- Test disc dumps/ULUS10566-test190-kc2.iso (= test189 + kc2 in 1P/2P/3P): battle start OK (no crash), intro, battle,
  win pose all play (recordings dumps/screens/rec_20261015-034824.mp4 / -040026.mp4). BUT the chain is NOT visible
  anywhere near the Keyblade (win pose close-ups, Keyblade on the shoulder / held out): the engine evaluates bones in
  LIST ORDER, belt (28) is computed before its new parent r_wep (50) → chain collapsed/elsewhere. Our own
  gmo2gltf.py has the same order assumption (IndexError) — preview used dumps/models/keychain/gmo2gltf_anyorder.py.
- ⇒ Any keychain bone must have an index > 50 (r_wep). Only wep0 (51), wep1 (52), trans_include (53) qualify.
  Next idea (v3, not built): wep0 = ONE pendulum bone under r_wep (its own transform may be unused for drawing: the
  blade is skinned through its list [r_wep]; but gmo_resize shifts draw bones, so check in game that the blade does
  not move), chain+token rigid on it via the body skinning list slot of 'belt' (count unchanged). Alternative: swap
  bone indices (r_wep ↔ a free bone) = rewrite every bone-index reference (motions, skin lists, AND objx hit shapes /
  FEP attach bones / magi bones) — large and risky.

### Keychain v3 — wep0 pendulum (2026-10-15, tools/scripts/keychain.py; test disc dumps/ULUS10566-test192-kc3.iso)
- Offline check of wep0's role: no mesh is skinned to wep0 (body palettes index the p_sev100 list, which has no
  wep0; wep0/wep1 parts use their lists [r_wep]). wep0 = the Keyblade part's DRAW bone (0x804E part 1) with rest
  (0, -1.016, 0) under root = the character origin; gmo_resize only kept the draw bones at that origin. Its own
  transform should not move the blade — unverified in game (culling / anything that reads the draw bone's position).
- v3: wep0 re-parented root -> r_wep (index 51 > 50: order OK; our in-order gmo2gltf.py works again), rest translate
  = the pommel in r_wep's frame, no rotation arg (identity). Chain (98 v) + token (62 v) = 2 body-part meshes RIGID on
  the body skinning-list slot of 'belt' (slot 20; entry -> wep0, inverse bind -> wep0's bind; no Sora mesh used it).
  wep0 part: blade only (array compacted). Motions: wep0 translate = pommel in place (170 curves), 6 re-pointed;
  baked 4-link verlet chain; the pivot->end direction is wep0's rotation (keys every 3 frames) in _000A _900A _902A
  _910A _911A. One rigid piece (no bend), but it hangs and swings.
- Size: 2,499,324 -> 2,503,532 (+4,208 B; v1 +19 KB crashed). Bones 54, list counts unchanged. 104 motions valid.
- Previews dumps/renders/keychain/keychain_v3__910A.gif / __000A.gif / __900A.gif.
- In-game TODO: battle start (no crash), blade still in the hand (wep0 moved), chain hangs in idle/win, EX Mode
  (Ultima Weapon part still draws through wep1 — the chain now hangs from the pommel there too).
