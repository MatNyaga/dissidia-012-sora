# Audio

Sora's voice, sound effects and music are fan-ported from Kingdom Hearts II. None of the audio is in this
repository.

## Voices

- **75 recordings** were selected for the mod, including **35 new Sora lines** (battle intros, wins, and matchup
  lines against other fighters) and the matching lines from the other fighters.
- The final voice package is in release 1.0. In testing, CPU Sora says his matchup lines, Lightning's
  "vs Sora" line plays in battle, and Garland's "vs Sora" line is listed and plays in the Jukebox.
- Sora also has a **Jukebox** voice entry, bought in the PP Catalog like the other fighters' voice sets.
- Not covered yet: Chaos's round-specific lines, Aerith-assist lines and Cosmos story scenes. These keep the
  game's normal behaviour for now.

Roster numbers used in voice routing: Prishe **29**, Vaan **30**, Sora **33**. A line's speaker and the opponent it
reacts to are separate fields, so check both directions. To route a line at run time you also need its line ID and
the condition in the voice list (VOLD); the file name alone isn't enough.

[`manifests/audio-selection.json`](../manifests/audio-selection.json) lists the selected clips by ID, owner and
source-file hash. It leaves out the audio itself, dialogue text and personal paths. Being on that list doesn't mean
the clip may be redistributed.

## Sound effects and music

Keyblade swings, magic, Reflect and finisher sounds go into Sora's sound bank. Three KH2 music tracks can be bought in
the PP Catalog and play in battle and the Jukebox. Input lists for both are in
[REPRODUCIBILITY.md](REPRODUCIBILITY.md#audio-inputs).

## How audio is prepared

1. Keep the original clips unchanged.
2. Make mono 16-bit PCM copies for the voice tools, and note every trim, gain and limiter setting.
3. Map each clip to its slot in a build made from the confirmed clean disc, then encode and patch a throwaway copy.
4. Check in the game: subtitles, speaker, which side speaks, timing, loudness, and playback in repeated battles.

New sound slots, line IDs and memory budgets are shared resources, so plan them before using them. When you record
in-game evidence, account for the music: matching audio by correlation alone has given misleading results before.
