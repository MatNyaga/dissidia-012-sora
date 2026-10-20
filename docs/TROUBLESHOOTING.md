# Troubleshooting

## Playing

| Problem | What to try |
|---|---|
| The patch app says the file is the wrong version | Only the US version (ULUS-10566) works. European and Japanese copies are different builds. |
| The patch app says the file is modified or incomplete | Make a fresh copy from your own disc. Compressed images (CSO and similar) and archives don't work; use a plain `.iso`. |
| The game won't start on a PS Vita | In Adrenaline, turn off game plugins (hold R at start → Recovery → Plugins). |
| A save shows "corrupted" on a Vita or PSP | Saves made in PPSSPP can do this on hardware, with the original game too. Try a save made on the device. |
| Menus feel slow on a Vita | Known. The game lowers the CPU speed in menus. Release candidate 3 keeps menus at the higher speed, which is much better in testing. |
| Friend card missing after the first start | Sora's record uses friend card slot 25. On a full save, the oldest unlocked card makes room. Lock cards you want to keep before you start. |

## Building

| Problem | What to check |
|---|---|
| Missing `dumps/`, `kh2_export/`, inbox files or art | These are left out on purpose. See [REPRODUCIBILITY.md](REPRODUCIBILITY.md). Don't download game files from an archive you can't trust. |
| `ModuleNotFoundError` with `python3 -I` | Activate your virtual environment and install the package there. User-site packages and `PYTHONPATH` are ignored. |
| OpenKH DLL or .NET error | Check the net8.0 target and the `release2-1691/openkh/Apps` paths in the bake project. Versions aren't resolved automatically. |
| Bootstrap rejects the input size or output | Use your clean US disc (check its hash) and a new output file name. Don't bypass the clean-input check. |
| A build seems to hang or overwrite another test | Check the script's output paths. Never build onto a disc PPSSPP has open, or into a folder another build is using. |
| Effects freeze or trails crash | Compare FEP offset modulo 16, node serials and vertex limits with a known-good build. |
| BREAK or win voices vanish in a mirror match | Look at the shared sound-bank budget and repeated loading. Syntax checks can't catch this. |
| A motion sticks in its last pose | The motion is shorter than the move's last script event, or its cancel/end timing is off. |
| An intro line seems missing | Check which side (player or CPU) speaks, which intro branch ran, and the voice-list condition and line ID. Don't rely on audio correlation alone. |
| pspdev binary needs a newer glibc | Use the Docker wrapper with `PSPDEV_HOST` set. |
| Emulator launcher asks for a profile | Set `PPSSPP_SOURCE_PSP` to a profile to copy, and make sure the destination is a throwaway folder. |
| The patch app rejects a patch | The app expects VCDIFF made with `xdelta3 -S none`. Try the synthetic tests first. |

## Reporting a problem

Give the tool version, the command, input hashes and a short error message. Never attach an ISO, extracted game
files, secrets, private chats or voice reference clips.
