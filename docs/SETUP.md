# Setup and build

This page is for people who want to rebuild the mod from source. Players don't need it: use the
[patch app](https://github.com/MatNyaga/sora-fan-patch) instead.

**Heads-up:** a fresh clone can't do a full build yet. You need your own game files and several outside tools, and a
few helper scripts are still missing from this snapshot. [REPRODUCIBILITY.md](REPRODUCIBILITY.md) has the full list.

## What you need

- **Linux** with Bash and GNU coreutils (that is what the project was built on).
- **Your own clean US disc image** (ULUS-10566): 1,754,529,792 bytes, SHA-256
  `df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e`. The size alone doesn't prove a clean copy,
  so always check the hash.
- **Python 3** with NumPy and Pillow for the model and image tools. SciPy, websocket-client and faster-whisper are
  used by some audio and debugger helpers. There is no pinned lock file yet; this list comes from the imports.

Use a virtual environment rather than your system Python:

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install numpy pillow scipy websocket-client
```

The build scripts call `python3 -I`, which ignores user-site packages and `PYTHONPATH`. Install everything into the
activated environment and run from there. Speech recognition is optional; keep its models local.

Other tools, by task:

| Task | What you need |
|---|---|
| Core disc and model build | Bash, Python, GNU coreutils, your local asset folders, `tools/pspdecrypt/pspdecrypt` |
| KH2 animation baking | .NET 8 and the OpenKH assemblies; `tools/kh2bake/bake/bake.csproj` expects them in `tools/openkh/release2-1691/openkh/Apps` |
| Audio conversion | FFmpeg, an ATRAC3 encoder (`tools/atracdenc`), vgmstream for decoding your own source files |
| Reverse engineering (optional) | Ghidra with an Allegrex (PSP CPU) extension and a matching Java |
| Testing in the emulator | PPSSPP with a throwaway copy of a profile, never your real save folder |
| PSP module builds | the pspdev toolchain; the Docker wrapper uses Ubuntu 24.04 and needs `PSPDEV_HOST` |
| Patch app core and CLI | Rust and Cargo; `xdelta3` for the synthetic end-to-end tests |
| Patch app window | Tauri, GTK and WebKit libraries plus generated icons |

Third-party tools are not included. Get each one from its own project and note its version, archive hash and
licence. Don't assume the newest version works; the .NET project expects one specific OpenKH folder layout.

## Preparing your local files

Follow [ASSETS.md](ASSETS.md). Create `dumps/`, `kh2_export/` and the tool folders you need; Git ignores them. Extract
`PACKAGE_INFO.BIN` and `PACKAGE.BIN` from your own disc with an ISO tool, then unpack them:

```sh
python3 -I tools/scripts/unpack_package.py LOCAL_PACKAGE_INFO.BIN LOCAL_PACKAGE.BIN dumps/package
```

Replace the two placeholders with your extracted files. The model build then expects, among others,
`dumps/package/01193_1b867bde_t1.gmo`, `kh2_export/model/sora.glb`, `kh2_export/keyblade/kingdom_key.glb`, the
Ultima Weapon glTF folder and `kh2_export/raw/kh2_sixth/original/obj/P_EX100.mset`. Effects, audio, textures and
baked motions are needed too.

## Full build

Only do this once your local files are in place and your clean disc's hash matches. Never patch the clean disc
itself, and never write to a disc that PPSSPP has open.

From the repository root:

```sh
bash tools/scripts/bootstrap_base.sh dumps/ULUS10566-base-fromclean.iso
bash tools/scripts/build_sora.sh dumps/ULUS10566-base-fromclean.iso dumps/ULUS10566-local-test.iso
sha256sum dumps/ULUS10566-local-test.iso
```

- `bootstrap_base.sh` reads `dumps/ULUS10566.iso`, refuses to overwrite an existing output, sets up roster spot 33
  and its starting moves, decrypts the EBOOT and restores Cloud's files.
- `build_sora.sh` builds the model and motion data, copies the input disc and applies every feature patch in order.
- **Pick new output names for both steps.** The full builder has no safe dry run; even without arguments it still
  generates model outputs.

The project's own builds from a clean disc were byte-identical when repeated. That hasn't been re-checked from a
fresh clone of this snapshot.

## Notes

- Paths in the scripts are relative to the repository root. Run tools from there unless a script says otherwise.
- PSP toolchain and emulator launchers need `PSPDEV_HOST` and `PPSSPP_SOURCE_PSP` set explicitly.
- From a clean clone, `bash tools/repository/smoke.sh` checks the committed source with synthetic data only. It
  needs an already filled Cargo cache, because it runs Cargo offline.
