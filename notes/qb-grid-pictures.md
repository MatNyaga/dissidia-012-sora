# Quick Battle character select: how picture numbers become textures

Worked out 2026-10-13 from local Ghidra decompiles of the menu overlay and the EBOOT (never published) and the
original pack files in dumps/ULUS10566.iso.

## Short answer

Nothing looks up a pack entry by index when drawing. Instead:

1. **When the scene loads**, every texture in every pack is registered under one shared
   **texture id** = `pack header u16 at +0x0C` (the pack's id base) + entry index, tagged with the scene's
   **group byte** (0x1D for free battle). Entries with size 0 are skipped.
2. **When drawing**, the menu asks for `(group, id)`, where `id = per-slot base constant + picture field`.

There is no picture → entry table and no name key. The per-slot bases are `li` constants in the overlay.

## Menu pak header (corrected)

```
0x00 "menu pak"
0x08 u16 1 (version)
0x0A u16 count
0x0C u16 id_base      <- first texture id in this pack (was the "u32 ?")
0x0E u16 0
0x10 count x { u32 offset, u32 size }   size 0 = empty slot (id left free for another pack)
```
Each entry is a GIM (starts with 'M', "MIG.00.1PSP"), an 'F' (font) entry, or an "mlng" wrapper that holds one
sub-entry per language (FUN_08870b10 picks the current language's one).

## Loading code (EBOOT)

- Pack lists are `{i32 type, char *path}` pairs ending with type 0xFFFF. Type 0 = gim pack, type 1 = seq pack.
  Free battle list: **0x08AA3D38** (overlay data), used by FUN_08a9d0e8 (the matching unload is a FUN_088d0fd4
  call): it calls FUN_088d00fc with the renderer DAT_089d7830, a heap, buffer size 0xE1000, group 0x1D and the list
  0x08AA3D38.
  List order: menu_pk_free_battle_gim_0..3, menu/JP/menu_lpk_free_battle_gim_0 (the JP is replaced by the language
  folder; the ULUS ISO only has EN), then menu_pk_free_battle_seq_0 and the lpk seq.
- **FUN_088d00fc** allocates a 0xE1000-byte (921,600) temporary buffer, calls **FUN_088d2980**, then frees it.
  FUN_088d2980 reads each pack into that buffer (FUN_08862854), then for type 0, for i in 0..count-1 with size != 0:
  id = (the u16 at pack+0x0C) + i, and if the data starts with 'M' it creates a texture object
  (FUN_088de0e8 → FUN_0899bb68 copies the GIM) with `+8 = id`, `+10 = group`, and links it into the list at
  renderer+0xEBC8. **Each pack file must stay at or under 0xE1000 bytes.** No bounds check was found.
- Lookup: **FUN_088d0984**(renderer, sprite, group, id) → **FUN_088d0684** walks renderer+0xEBC8 for the first
  object with matching group (+10) and id (+8) (FUN_088de1e8), then FUN_088da924 binds it to the sprite.

## Where each picture comes from (QB grid, FUN_08a7fb54 / FUN_08a84458)

The chara-select object (created in **FUN_08aa0d48**, init FUN_08a80d8c) stores a config pointer at obj+0x1C =
scene_obj+0x930. FUN_08aa0d48 fills it: group 0x1D at +4, and the u16 bases:

| what | row field (table 0x08A864D0, 12-byte rows) | code | base (cfg offset) | `li` instruction VA |
|---|---|---|---|---|
| grid cell icon | +0 picture | FUN_08a7fb54 | **0x702F** (cfg+0x36) | 0x08AA0DC8 |
| big art (right) | +0 picture | FUN_08a84458 (397365, 397588) | **0x700C** (cfg+0x38) | 0x08AA0DD4 |
| name image | +2 second picture (-1 = hidden) | FUN_08a84458 (397553) | **0x704F** (cfg+0x3A) | 0x08AA0DE0 |
| game logo | +4 logo | FUN_08a84458 (397384) | **0x706F** (cfg+0x3C) | 0x08AA0DEC |

Row layout correction: `i16 pic, i16 name_pic, i16 logo, i16 ?, i32 owner` (the i32 at +8 is what
FUN_08a7f2b4 / FUN_08a80130 compare with the owner). Cloud row 12 = (12, 12, 6, 13, 13).

Check with Cloud: grid 0x702F+12 = 28731 = gim_2[24] p_sev100_1p (small); art 0x700C+12 = 28696 = gim_1[1]
p_sev100_1p; name 0x704F+12 = 28763 = EN lpk[91] p_sev100_name; logo 0x706F+6 = 28789 = gim_2[82] title07. All match.

Other screens in the same scene use the same bases plus two more:
**0x70B2 = p_*_face_in_name**, **0x70D2 = p_*_face_in_name_r**, 0x708B = map_random/maps. Seen in FUN_08a9acac
(0x801C..0x8024: grid, face, face_r, name, logo), FUN_08aa02f8 / FUN_08aa0fbc (0x9A0..0x9A8: map, art, name, face,
face_r). These are probably party battle and results screens. I did not trace which row field they add; assume the
picture (+0) for face/face_r.

## Id map (original ISO, group 0x1D)

| pack | pkg idx | id_base | count | ids | size | room left under 0xE1000 |
|---|---|---|---|---|---|---|
| menu_pk_free_battle_gim_0 | 3667 | 28672 (0x7000) | 23 | 28672-28694 | 887,536 | 34,064 |
| menu_pk_free_battle_gim_1 | 1261 | 28695 | 12 | 28695-28706 | 802,288 | 119,312 |
| menu_pk_free_battle_gim_2 | 8555 | 28707 | 92 | 28707-28798 | 851,056 | 70,544 |
| menu_pk_free_battle_gim_3 | 6241 | 28799 | 130 | 28799-28928 | 725,056 | 196,544 |
| menu/EN/menu_lpk_free_battle_gim_0 | 3230 | 28672 | 257 | 28672-28928 | 583,744 | 337,856 |

The lpk overlaps all four pk packs. Every id from 28672 to 28928 is used by exactly one pack: where one pack has
an empty slot, another pack fills that id. **There are no free ids below 28929 (0x7101).**

Picture-indexed runs (picture p = 0..31):
- big art 0x700C+p: gim_0[12..22] (one100..six100), gim_1[0..11] (six200..org200), gim_2[0..8] (for110..org210)
- grid icon 0x702F+p: gim_2[12..43]. icon_random/free/delete are at base-1/-2/-3 (gim_2[11], [10], [9]).
- name 0x704F+q: EN lpk[79..110]
- logo 0x706F+l: title01 = lpk[111], title02..13 = gim_2[77..88], title01_b = lpk[124], title02_b/03_b = gim_2[90..91],
  title04_b..12_b and title14_b = gim_3[0..9] (l = 0..25)
- face_in_name 0x70B2+p: gim_3[51..82], face_in_name_r 0x70D2+p: gim_3[83..114]

Picture order: 0 one100 (WoL), 1 one200, 2 two100, 3 two200, 4 thr100, 5 thr200, 6 for100, 7 for200, 8 fiv100,
9 fiv200, 10 six100, 11 six200, 12 sev100 (Cloud), 13 sev200, 14 eht100, 15 eht200, 16 nin100, 17 nin200, 18 ten100,
19 ten200, 20 gst100, 21 gst200, 22 org200, 23 for110, 24 fiv210, 25 sev110, 26 eht110, 27 ten110, 28 gst110,
29 gst120, 30 gst130, 31 org210.

**Picture 32 does not work as-is.** Every slot collides with an existing texture:
- art: 0x700C+32 = 28716 = icon_delete
- grid: 0x702F+32 = 28751 = p_one100_name
- name: 0x704F+32 = 28783 = title01
- face: 28882 = p_one100_face_in_name_r

## Recommendation for owner 33 (Sora)

Keep the bases. Give Sora picture values that land above 28928, and append the new GIMs to the end of
**menu_pk_free_battle_gim_3** (it is language-independent and has the most room among the pk packs). Appending only
adds ids above the current top, so no existing index moves. Fill the in-between entries with size-0 slots (8 header
bytes each). Rebuild the offsets, because the header grows and pushes the data down.

Suggested values (the gaps between ids are fixed by the bases):
- row +0 picture **P = 245** → art id 28929 (gim_3 entry 130), grid 28964 (entry 165), face_in_name 29095 (entry
  296), face_in_name_r 29127 (entry 328)
- row +2 name picture **Q = 179** → name id 28930 (gim_3 entry 131)
- row +4 logo **L = 148** → logo id 28931 (gim_3 entry 132). Or keep any existing logo value (6 = FF7).
- New gim_3 count = 329 (header 0x10 + 329*8). New GIMs: art 66,848 + grid 3,360 + name 5,408 + logo 9,500
  + face 5,416 + face_r 5,420 ≈ 96 KB. New size ≈ 725,056 + 1,592 + 96,000 ≈ 823 KB, under 0xE1000.
- Copy the format of the Cloud GIMs (same size, palette and swizzle): art from gim_1[1], grid from gim_2[24], name from
  lpk[91], logo from gim_2[82], face from gim_3[63], face_r from gim_3[95].
- Picture values are only ever added to the bases. I found no range check on +0/+2/+4 (the only special value is
  name_pic -1 = hide), so 245/179/148 are fine as i16. Keep every id under 0x8000.

If you would rather not have the long run of empty slots, the alternative is to patch the bases. That is worse:
they are `li` immediates shared by six config blocks (0x08A9AD74.., 0x08AA04E0.., 0x08AA0DC8.., 0x08AA1050..,
0x08AA1310.., 0x08AA16E4..), and every existing character's id would move.

Not verified yet:
1. Whether the texture/VRAM heap has room for +96 KB.
2. Which row field the face/face_r screens use.
3. That nothing outside this scene (for example the battle-loading VS screen, which is in another overlay or group)
   reads the picture.

Test in game after building. Also note: the row table has 33 hard-coded rows (loops use < 0x21 / 0x1F, and row 32 is
random), so owner 33's row still has to replace or extend a row, as is done now.

## Done (test 69 `dumps/ULUS10566-test69-qbpics.iso`, 2026-10-13) ✅
`tools/scripts/spot33_qbpics.py ISO` appends 6 GIMs to menu_pk_free_battle_gim_3.bin (130 → 329 entries, 822,624 B,
moved to the ISO end) and sets #33's grid row (row 31) to pic 245 / name 179 / logo 148. Seen in game: grid icon,
big art, "Sora" name, KINGDOM HEARTS II logo on the select screen; VS screen + battle fine (no texture-memory issue
seen). Pictures: `tools/scripts/make_select_art.py` → tools/art/qb_*.png (art = Blender render of the win pose,
`tools/blender/render_portrait.py ... _910A 246 20 768` → dumps/renders/portrait/win_20.png; icon/faces = KH2 journal
face; logo = KH2 title texture pieces). Quantise to 256 colours BEFORE gim_put (its own fallback looks blotchy).
The grid cell shows only about the top 32×35 of the 32×64 icon. Face strips (296/328) not seen on screen yet.

## Quick Battle setup screen (Enter Battle / STAGE / … list): player and CPU banners

Findings from 2026-10-13, after test 69. The grid now works, but on the setup screen owner 33 shows "Lv 7" and a red
"FINAL FANTASY" wordmark instead of a name, and no art.

**Cause.** This screen does not read the grid row. It uses **owner − 1** as the picture number:
`art id = 0x700C + owner − 1` and `name id = 0x704F + owner − 1`.
- For owners 1..32 this happens to equal the row's picture, because every original row has pic == name_pic == owner − 1.
- Owner 33 gives +32. The art becomes 28716 (icon_delete, so no visible art). The name becomes 28783 (lpk title01, the
  FF1 logo, which is the red "FINAL FANTASY" seen).

Ghidra's C output cuts both functions short at a "does not return" call. They are only visible in the disassembly.

- **FUN_08aa44ac**(scene, owner a1, flag a2, …) draws the player banner. `s4 = owner − 1` is set at 0x08AA44B4.
  - art at 0x08AA459C: reads the config base at obj+0x582 (0x700C), adds owner − 1 at 0x08AA45A8, then calls FUN_088d0984.
  - name at 0x08AA45F4: reads the config base at obj+0x584 (0x704F), adds owner − 1 at 0x08AA4600.
- **FUN_08aa6148** is the second banner (CPU / 2P). It uses the same pattern with `s5 = owner − 1` (0x08AA617C).
  The owner − 1 adds are at 0x08AA62A0 and 0x08AA62F8.
- **Where the bases come from:** obj = scene+0x1EE4. Its config is copied from scene_obj+0x97C (FUN_08aa5124), and
  that config is filled by FUN_08aa02f8 / FUN_08aa0fbc: map 0x708B, art 0x700C, name 0x704F, face 0x70B2,
  face_r 0x70D2. Face and face_r are not read on this screen.
- **The banner frame table is also indexed by owner − 1.** It is at **0x08AA8864**, 10-byte rows, 32 rows for owners
  1..32. Fields: +0/+4 are the player banner sprite frames (obj+0xA8; +0 when flag = 0), +2/+6 are the CPU banner
  frames (obj+0xAC), and +8 is stored to obj+0x1E64.
  - Owner 33 reads past the end, into the next table at 0x08AA89A4 (used by 0x08AA6C24), and gets
    (6, 5, 4, 3, 2).
  - It looks harmless: the frames are valid numbers, just a mixed-up banner frame. If the banner background looks
    wrong, this is why. The table cannot be extended in place.

**Fix: remap owner − 1 = 32 to 245 just before the art/name draw.** By that point the table row has already been
read. Each function reloads obj three times without need, so the code can be compacted to free three instructions for
our remap: "if owner − 1 == 32, use 245", done with a conditional move (Allegrex has one; the overlay already uses
conditional moves 661 times). t0 and t1 are dead at these points, and
nothing branches into the rewritten ranges.

Patch: OVL_MENU_APP.ELF at ISO sector 185056, file offset = VA − 0x089DD4C0 + 0x54. The patcher checks the original
words first (same on the clean disc and test69).

| VA range (file offset) | what changes |
|---|---|
| 0x08AA4570..0x08AA4588 (0x0C7104..0x0C711C), FUN_08aa44ac | the same two halfword stores to obj, compacted by dropping the redundant reloads of obj; the 3 freed words remap owner − 1 = 32 → 245 (s4) before the art/name draw |
| 0x08AA6268..0x08AA6280 (0x0C8DFC..0x0C8E14), FUN_08aa6148 | the same for the second banner: the stores and the row +8 read stay, the freed words remap owner − 1 = 32 → 245 (s5) |

In both functions a0 still holds obj (scene+0x1EE4) when the next original instruction (the read of obj field +8) runs.

**Effect, and one texture to add.**
- art = 0x700C + 245 = **28929**. This is the existing gim_3 entry 130, so nothing new is needed.
- name = 0x704F + 245 = **28996**, which is gim_3 **entry 197**, currently an empty filler slot. Put a copy of the
  name GIM (entry 131, 5,408 bytes) there.
- Optional tidy-up: set the grid row's name_pic to 245 too, so both screens use entry 197, and drop entry 131.

**Not done.** The VS / loading / results screens may have their own owner − 1 lookups. Search for
a config-base load from obj followed by an add of owner − 1 in other overlays if they also look wrong.

## Setup screen fixed (test 73 `dumps/ULUS10566-test73-setup.iso`, 2026-10-13) ✅ (band ✗)
spot33_qbpics.py now also: name_pic = 245 (name GIM at gim_3 entry 197, shared by grid + setup), SETUP_PATCH (the
14 words above: owner-1 = 32 → 245 for art/name in FUN_08aa44ac / FUN_08aa6148), and FRAME_PATCH (0x08AA44F8..453C
rewritten: load frame → a1 and obj+0xA8 → a0 directly, dropping the 3-instruction swap; the freed words select
the row 200 bytes back when owner − 1 == 32 → owner 33 uses frame row 12 = Cloud's). Seen: "Lv7 Sora" +
Sora's art on the left, no red logo. Still missing: the blue band behind the player name (test 65 had one; tests
71–73 not — row 23 and row 12 both give no band; cause unknown). CPU-side frame row (FUN_08aa6148, s6 computed
in two branches at 0x08AA61C8 / 0x08AA61E8) not remapped yet — matters only when #33 is the CPU.
Disassembler: tools/scripts/mdis.py ISO START END (tiny MIPS decoder for the menu overlay).

## Menu art = KH2 menu illustration (test 90 `dumps/ULUS10566-test90-menuart.iso`, 2026-10-13)
Mat: pictures in the KH2 opening-menu art style; picked the KH2 menu art of Sora standing in the water looking back
(downloads/menuart/ref.jpg, middle panel; ice cream painted out → ref_noice.png). `make_title_art.py` (default
source = that reference): clean cut-out (border flood fill + white un-mixing, no speckled outline, no white
background), mirrored to face right like the game's faces. Sizes copied from the game's own pictures:
HUD head ≈ 46×50 px oval at x 40, bottom y 100 of 128² (Lightning/Cloud/Squall x 38-86, y 46-100); VS face = tight
face close-up filling 64²; grid icon = tight face in the top 32×48 of 32×64. Mat: "almost" → grid icon tighter,
HUD head centred (both done in test 90; HUD/VS not re-checked on screen yet).
go_battle.py: the grid cursor remembers the last pick → it now walks right until #33 is selected (needs a fresh
grid_33b reference with the new art).

## Missing name bands (setup and VS screens) and missing CPU art: test91 follow-up

Findings from 2026-10-13. Everything was checked statically against dumps/ULUS10566-test91-menuart.iso; nothing has
been run in game.

### Bands: the 3x3 grey marker texel in the name GIM

The coloured band behind a name (blue for the player, red for the CPU) is **not a separate texture or table entry**.
It is made of sprites in the free-battle SEQ files that sample texture UV (1,30)-(2,31) of whatever texture is bound
to the name part, then tint it with vertex colours and an alpha fade:
- menu_pk_free_battle_seq_0 entries 24, 40 and 52
- EN menu_lpk_free_battle_seq_0 entry 6
- example vertex colours: 111a8a (blue), 5b253e / 8018427f (red)

Every original **name** GIM (all 32, 128x32) has a 3x3 opaque grey block of exactly **(128,128,128,255) at
x 0..2, y 29..31**. Sora's name GIM (id 28996) is fully transparent there, so the band samples alpha 0 and disappears.
That explains every missing band:
- setup screen, player and CPU side (the FRAME_PATCH row change could not help)
- VS screen, both sides

Fix the texture, not the code. When building qb_name, copy the marker from Cloud's template. The other Cloud
templates have the same kind of exactly-(128,128,128,255) blocks; copy them too, in case other screens use them:

| texture | marker block(s) in Cloud's GIM (x0,y0..x1,y1) | how many originals have it |
|---|---|---|
| name 128x32 | (0,29)-(2,31) | 32/32 |
| logo 128x64 | (0,61)-(2,63) | 26/26 |
| face_in_name 128x32 | (0,29)-(2,31) and (125,29)-(127,31) | 17/32 (others use wider blocks) |
| face_in_name_r 128x32 | (0,28)-(3,31) | 19/32 |
| grid icon 32x64 | (1,60)-(3,62) | 19/32 |

Simplest rule for spot33_qbpics.py: after pasting Sora's pixels, copy back every template pixel that is exactly
(128,128,128,255) and lies within 8 px of the left or right edge and 4 px of the top or bottom edge. The colour must
stay exactly 128 grey after GIM quantisation, because the band colour is the vertex colour times this texel.

### CPU-side art (and the CPU name locator): FUN_08aa6148 still reads frame row 32

SETUP_PATCH already gives the CPU art the right texture id: the art draw uses s5 with the 32 → 245 remap at
0x08AA6278, so the id is 28929. The problem is the **frame row**. The CPU banner sprite obj+0xAC gets its animation
from table 0x08AA8864, row s5 (+2 when flag = 0, +6 when flag = 1). For owner 33 that is row 32, past the end, which
holds 6,5,4,3,2 from the menu-cursor table at 0x08AA89A4.
- So the CPU sprite plays frame 5, a player-side crop of the art (in SEQ entry 48, 96 animations = 24 characters × 4)
  instead of a CPU one. The art therefore does not show on the right.
- The same row's +8 (read at 0x08AA6270 into obj+0x1E64) is the locator that FUN_08aa7788 uses to place element 0x33.
  Owner 33 gets 2 instead of Cloud's 11.

**Fix (FRAME_PATCH for the CPU side):** rewrite 0x08AA6194..0x08AA6200 (28 words) so both branches share one
"row = table + s5*10; if s5 == 32 use row 12 (Cloud: 26/27, locator 11)" block. A field-offset register t2 (2 or 6),
set after each call, picks the field. The owner-0 special case (s5 = 0, s4 = 1) and the hide/show of obj+0xB4 are
kept. The row pointer s6 stays remapped, so the later read of the row's +8 at 0x08AA6270 also gets Cloud's locator 11.
File offset = VA − 0x089DD4C0 + 0x54. ISO sector 185056. The patcher checks the original words first (test91 still has them).

| VA range (file offset) | what changes |
|---|---|
| 0x08AA6194..0x08AA6200 (0x0C8D28..0x0C8D94), FUN_08aa6148, 28 words | both branches (flag = 0 / flag ≠ 0) now share one row computation: row = table + s5·10, and if s5 == 32 the row 200 bytes back (row 12, Cloud's) is used; a field-offset register (2 or 6, set on each branch) picks the frame field. The two calls (0x088D9CFC, 0x088D9CD8), the owner-0 special case and the hide/show of obj+0xB4 are kept; the branch offsets inside the range are adjusted to the new layout. |

Execution then continues at 0x08AA6204 (the call to FUN_088d9f5c), as before. The only branch
targets inside the range were 0x08AA61C8 and 0x08AA61E0, from 0x08AA61B0, 0x08AA61B8 and 0x08AA6194, and all of those
are rewritten. t0, t1 and t2 are dead at this point.

### Not found

- The VS-screen drawing function was not located. The 5-slot FUN_08b2c330 (config 0x7FF4: grid, face_r, name) is the
  party screen; its owner − 1 tables are at 0x08B2D168 (u16, 32 owners) plus a grid/face_r/name draw at base +
  owner − 1. The marker explanation covers the VS bands no matter which function draws them.
- If the VS screen also shows a wrong portrait or name for owner 33, look there for the same "config base + owner − 1"
  pattern, using the 0x7FF4-style config bases 0x702F, 0x70B2, 0x70D2, 0x704F and 0x706F.

## Done with Mat (test 93 `dumps/ULUS10566-test93-bands.iso`, 2026-10-13 evening) ✅ Mat: "perfect" / "love it"
- Bands fixed by the grey marker texels (tools/scripts/gim_markers.py keep(), templates = Cloud's ORIGINAL GIMs;
  used in spot33_qbpics / spot33_vsname / spot33_faces). CPU_FRAME_PATCH (owner 33 as CPU → Cloud's frame row) →
  CPU-side setup art + red band show.
- Name pictures: select/setup pack name = centred "Sora" (tools/art/qb_name.png, game centres like Vaan);
  VS/loading chara_name = left-aligned (tools/art/sora_name_left.png; all game names start at x 0 there).
- KH2 logo = Mat's KH2 menu picture (downloads/menuart/icon.jpg crop) on an 89×50 white card.
- Faces face LEFT like the art (not mirrored). Crops (cut-out panel coords, eye x85 y85, nose x70 y107, chin y123):
  VS 64² (58,40)-(156,138) — the VS square only shows the LEFT part of the picture, so the face sits left;
  HUD head crop (35,10)-(175,150) → 46 wide oval at x 44, bottom y 100 (Mat: slightly right = perfect);
  grid icon (50,26)-(144,167) → 32×48 (cell shows the top ~32×35); eye strips (58,68)-(152,103).
- Select art: head to thighs (0,0)-(210,400) → 134×256 at x 62, darkened (×0.8, contrast ×1.12), clean 1 px white
  rim + faint shadow (dissidia_style()) — Mat: outline was noisy, art too bright.
- go_battle.py: finds #33 on any grid by reading the name area (screen_ref/name_sora.png, threshold 3), row by row.

## Customization character select (main menu, Triangle → Character Select)

Findings from 2026-10-13, checked against test95-combos (static only, not run).

**It is the same chara-select object as Quick Battle, in another scene.** FUN_08a8799c fills a config at
scene_obj(+0x14C)+0x924 and calls FUN_08a80d8c. That is the same grid code (FUN_08a7fb54 / FUN_08a84458) and the same
**grid row table 0x08A864D0** (row field +0 for icon and art, +2 for name, +4 for logo). The config:
- group **0x22**
- bases: grid icon **0x431** (cfg+0x36, at 0x95A), big art **0x40E** (cfg+0x38), name **0x451** (cfg+0x3A),
  logo **0x471** (cfg+0x3C)

Mode comes from the table at 0x08A87D60, indexed by DAT_09b6cd88; this screen is shared by several main-menu
character selects.

Packs: FUN_08a86760 loads list **0x08A87DD0** through FUN_088d00fc (buffer size 0x180000, group 0x22), so the load buffer is
**0x180000 = 1,572,864 bytes**.

| pack | id_base | count | ids | size (orig = test95) |
|---|---|---|---|---|
| menu_pk_upper_chara_select_gim_0 | 1024 | 35 | 1024–1058 | 1,547,936 (only 24,928 bytes of room) |
| menu_pk_upper_chara_select_gim_1 | 1059 | 104 | 1059–1162 | 1,079,888 |
| menu/EN/menu_lpk_upper_chara_select_gim_0 | 1024 | 139 | 1024–1162 | 359,952 |

The layout is the same as free battle, just based at 0x400 instead of 0x7000:
- art p_one100_1p = 1038 (gim_0[14]); Cloud = 1050
- icons from 1073 (gim_1[14]); icon_random/free/delete = 1072/1071/1070
- names from 1105 (lpk[81])
- logos title01 = 1137 (lpk[113]), title02.. = gim_1[79..]

**Why Sora is wrong there:** grid row 31 now holds pic 245 / name 245 / logo 148, so this scene asks for ids that no
pack has. Every slot comes out empty:
- art 0x40E+245 = **1283**
- icon 0x431+245 = **1318**
- name 0x451+245 = **1350**
- logo 0x471+148 = **1285**

(With the old pic 12 the screen showed Cloud's pictures.)

**Recipe (no code change):** append the same four GIMs that spot33_qbpics.py builds for free battle (same Cloud
templates, same qb_*.png, same 128-grey marker rule) to **menu_pk_upper_chara_select_gim_1.bin** (base 1059, so
index = id − 1059). Fill the gaps with size-0 entries:

| what | id | gim_1 index | template (Cloud, this scene) | size |
|---|---|---|---|---|
| art | 1283 | 224 | gim_0[26] p_sev100_1p | 66,848 |
| logo | 1285 | 226 | FF7 logo: 0x471+6 = 1143 (title07, gim_1[84]) | 9,500 |
| grid icon | 1318 | 259 | gim_1[26] p_sev100_1p | 3,360 |
| name | 1350 | 291 | lpk[93] p_sev100_name | 5,408 |

- The new count is 292. The pack becomes about 1,079,888 + 1,504 + 85,116 ≈ 1.17 MB, under the 0x180000 buffer.
- Do not use gim_0; it has only 24.9 KB of room.
- The free-battle GIMs (gim_3 entries 130/132/165/197) can be copied byte for byte: same formats and sizes as these
  templates. Check this with a diff of Cloud's GIM headers in both scenes before relying on it.

**Next screen (the Customization menu itself, group 5, FUN_08af371c → EBOOT FUN_088d5638) uses owner − 1** with bases
from 0x08B009FC (face_in_name 0xC2A, name 0xC09), and grid icons at 0xC4B + owner − 1 (FUN_08ae10b8 /
FUN_08ae3b14 / FUN_08b03ff8). For owner 33 that is index 32, which already exists in these packs: it is Aerith's old
slot, p_sev120_*.
- name: EN lpk_customize[41], id 3113. Already Sora (spot33_banner).
- **face_in_name: pk_customize[74], id 3146. Still Aerith's.** Replace it in place (5,416 bytes, keep the grey markers).
- **icon: pk_customize[107], id 3179. Still Aerith's.** Replace it in place (3,360 bytes, keep the grey markers).

No code patch is needed in either scene.
