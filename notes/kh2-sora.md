# Getting a Sora model from KH2 (research, 2026-10-12)

## Route
1. **KH 1.5+2.5 ReMIX on PC.** On Linux: Steam + Proton, or Heroic (Epic). Install to /data.
2. **Extract the game data with OpenKH.** Recommended: OpenKh.Tools.ModsManager → PC release → detect install →
   "Extract Game Data" (15–30 min) [Panacea/Mod Manager guide; openkh.dev ModsManager docs].
   Game files must be unpatched. Older alternative: KHPCPatchManager (drag the .hed).
   OpenKH needs the .NET 8 runtime; CLI tools run anywhere, GUI tools are Windows-first → use Wine/Proton on Linux.
   Linux setup guide: github.com/KHOmega/KH-PC-and-Linux-Setup.
3. **Sora's model:** KH2 models are .mdlx files; Sora should be `obj/P_EX100.mdlx` (forms/outfits are P_EX100_* —
   from memory, not confirmed by the searches). We do NOT need his animations (.mset): Cloud's animations are reused.
4. **MDLX → FBX:** OpenKH's KH2 MDLX editor (OpenKh.Tools.Kh2MdlxEditor) exports to FBX (per a KH modding tutorial);
   alternatives: Noesis + "kingdom_hearts_2_v2" plugin (Windows; export FBX, tick Flip UVs), Soraiko's MDLX Viewer.
   OpenKH repo also has OpenKh.AssimpUtils / PAMtoFBXConverter.
5. **Blender (our side):** import Sora FBX + our Cloud glTF (gmo2gltf.py), pose/scale Sora to Cloud's A-pose
   (Cloud ≈ 1.8 tall), bind to Cloud's 54-bone armature (Automatic Weights, then fix), ≤ 4 weights/vertex,
   textures downscaled to power-of-two ≤ 512 (PC textures are HD DDS), meshes named "p_sev100|…",
   export glTF → gltf2gmo.py (base = Cloud's GMO) → pkg_put.py → obj/P_SEV120_1P.gmo.
6. Keyblade: separate weapon part; our importer can't rebuild weapons yet (rigid-part path TODO).

## Notes
- Fan Sora costumes for 012 by Ultima Espio (2011–13) show this works; someone else's work.
- A public xdelta patch would carry data derived from KH2's Sora, keep the patch to
  our changes; community norm for fan mods, but be aware.
- Space: /data has ~825 GB free.

## Sources
- OpenKH repo: https://github.com/OpenKH/OpenKh (tools list, Linux/Wine note, .NET 8)
- OpenKH Mods Manager docs: https://openkh.dev/tool/GUI.ModsManager/
- Mod manager setup guide: https://tommadness.github.io/KH2Randomizer/setup/Panacea-ModLoader/
- KHPCPatchManager: https://github.com/AntonioDePau/KHPCPatchManager
- Linux setup: https://github.com/KHOmega/KH-PC-and-Linux-Setup/blob/main/refined-windows-setup.md
- KH2 file types (MDLX → OpenKh.Tools.KH2MdlxEditor): https://openkh.dev/kh2/file-type.html
- MDLX → FBX workflow (tutorial): https://github.com/Cagaroo/KH3D-Modding-Tutorials
- Noesis KH2 plugin / viewers: https://archive.vg-resource.com/thread-19286.html
