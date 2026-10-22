# Instructions for extracting Sora from KH 1.5+2.5 ReMIX (PC)

Context: I'm modding Dissidia 012 (PSP) to add Sora as a new fighter. Another tool already handles the Dissidia
side (rigging onto Cloud's skeleton, converting to the PSP model/sound formats). I only need the raw Sora assets
exported from the PC copy of Kingdom Hearts 1.5+2.5 ReMIX into open formats. I'm on Linux (Ubuntu-based).

## Rules
- Only READ the game's data files. Don't modify anything in the game folder. Don't run the game's .exe files.
- Get OpenKH only from OpenKH's own GitHub releases page: https://github.com/OpenKH/OpenKh/releases
- Put everything in `kh2_export/` at the project root (folders: raw/, model/, keyblade/, textures/, voice/, sfx/)
- When unsure of a command's flags, run it with --help first instead of guessing.

## Step 1 — Tools
1. Install the .NET 8 runtime (Ubuntu: `sudo apt install dotnet-runtime-8.0`; check with `dotnet --list-runtimes`).
2. Download the latest OpenKH release zip and unpack it to `tools/openkh/` in the project.
3. Install vgmstream-cli (for audio): from https://github.com/vgmstream/vgmstream/releases (Linux CLI build).
4. GUI tools (OpenKh.Tools.Kh2MdlxEditor, Mods Manager) are Windows programs → run them with Wine if needed.

## Step 2 — Extract KH2's data
The PC game keeps KH2 data in `<install>/Image/en/kh2_first.hed` + `.pkg` (also kh2_second … kh2_sixth).
Extract all of them with OpenKH's IdxImg command (check `--help`; something like):
    dotnet OpenKh.Command.IdxImg.dll hed extract "<install>/Image/en/kh2_first.hed" -o kh2_export/raw
Repeat for kh2_second … kh2_sixth. The output has the original files plus a `remastered/` folder with the HD textures.
(Alternative: OpenKH Mods Manager → "Extract game data", or KHPCPatchManager.)

## Step 3 — Sora's model
- Sora's normal KH2 model is `obj/P_EX100.mdlx` (the P_EX100_* files are his forms/outfits — not needed).
- His Kingdom Key Keyblade is a separate weapon model, most likely `obj/W_EX010.mdlx` — confirm by viewing it.
- Export both to FBX (or glTF/DAE) WITH the skeleton/bones and UVs, using OpenKh.Tools.Kh2MdlxEditor's export
  (or Noesis with the "kingdom_hearts_2" plugin; tick "flip UVs"). We don't need his animations.
- Textures: export as PNG. Prefer the HD ones from `remastered/obj/P_EX100.mdlx/` if they match; keep the
  originals too. Note which texture belongs to which mesh/material.
- Save: model/sora.fbx (+ glb if possible), keyblade/kingdom_key.fbx, textures/*.png.
- Quick check: open sora.fbx in Blender, take a screenshot showing the textured model, save as model/check.png.

## Step 4 — Sora's battle voice clips
- Find where KH2 keeps Sora's battle voices (attack shouts, hurt sounds, short battle lines). Search the
  extracted `raw/` tree (folders like voice/us/…; files may be `.win32.scd`, `.scd`, `.vsb` or similar; names
  may contain "ex100", "sora" or "battle"). List what you find before converting.
- Convert them to WAV with vgmstream-cli (`vgmstream-cli -o out.wav in.scd`; for banks with several sounds use
  `-S 0` to get every subsong). English voices only.
- Save to voice/, and write voice/LIST.txt: file name → what is said / what kind of sound (shout, hurt, line).
  About 70 short clips is plenty.

## Step 5 — Keyblade sound effects
- Find the sound banks with Sora's Keyblade swing / hit / jump / landing sounds (look in se/ or similar sound
  folders, and anything tied to P_EX100 or W_EX010). Convert with vgmstream-cli to WAV.
- Save to sfx/, with sfx/LIST.txt describing each sound (swing, hit, heavy hit, jump, land, guard, magic…).

## Step 6 — Hand-off
Write kh2_export/README.md: what was extracted, tool versions, exact commands used, and anything that failed or
looked odd. Don't edit or convert anything further — the Dissidia side takes it from there.
