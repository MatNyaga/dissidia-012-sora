"""Own (KH2) sound effects for #33: APPEND new slots to the fighter's `snd_` SSCF bank (obj/p_sev120.objx). Scripts
play them with one-shot op 0x03 [2200000 + slot, 0, 0] (spot33_chain.py AUTHOR `ones`); spot33_soundids.py (last
build step) moves the ids to 21900000 + slot with the rest of the bank (it reads the grown count from the header).
DRY RUN unless --out:

  python3 -I spot33_sfx.py ISO [--out NEW.objx]      then: pkg_put.py ISO obj/p_sev120.objx NEW.objx

Bank (sscf.py): 0x20 header, count × 32-B entries (+4 data offset from bank start, +8 size, +0x0C u16 rate,
+0x0E u8 volume 0-100, …), then VAG data. A new entry shifts the data by 32 B → every offset += 32.
Rerun-safe: slots that already exist are skipped (the bank must have exactly `slot` entries before a new one).
"""
import os
import struct
import sys
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402
import sscf  # noqa: E402

FILE = 'obj/p_sev120.objx'
SFX_DIR = os.path.join(HERE, '..', '..', 'kh2_export', 'sfx', 'explosion')
FIRE_DIR = os.path.join(HERE, '..', '..', 'kh2_export', 'sfx', 'firaga')
MAGIC_DIR = os.path.join(HERE, '..', '..', 'kh2_export', 'sfx', 'magic')
REFLECT_DIR = os.path.join(HERE, '..', '..', 'kh2_export', 'sfx', 'reflect')
KEY_DIR = os.path.join(HERE, '..', '..', 'kh2_export', 'sfx', 'keyblade')
TEMPLATE = 37            # entry whose playback params are copied (Cloud's per-hit sound)
# slot: (wav (16-bit mono), volume 0-100, label)
SFX = {70: (os.path.join(SFX_DIR, 'start.wav'), 90, 'Explosion start (KH2 se 999038 = se999_038.wav, guess: 1-based)'),
       71: (os.path.join(SFX_DIR, 'orb.wav'), 100, 'Explosion orb hit = KH2 se000_097 sharp hit (Mat picked option 1; was se999_042 head = bubbly)'),
       72: (os.path.join(SFX_DIR, 'blast.wav'), 100, 'Explosion blast (KH2 se 999042 = se999_042.wav 1.8 s + octave-down boom, saturated; Mat picked v2)'),
       # KH2 Firaga (Mat 2026-10-15; ids from FIRE_3.mag via the effects helper, notes/kh2-effects.md "Firaga")
       73: (os.path.join(FIRE_DIR, 'cast.wav'), 90, 'Firaga cast at the hand (KH2 se 156 = se000_059, 1.3 s)'),
       74: (os.path.join(FIRE_DIR, 'flash.wav'), 90, 'Firaga cast flash (KH2 se 999016 = se999_016, 1.0 s)'),
       75: (os.path.join(FIRE_DIR, 'fly.wav'), 80, 'Firaga fireball flying (KH2 se 116 = se000_055, 1.0 s, no loop)'),
       76: (os.path.join(FIRE_DIR, 'explode.wav'), 100, 'Firaga explosion (KH2 se 118/119 = se000_056, 1.5 s)'),
       # KH2 Thundaga / Blizzaga (Mat 2026-10-15; effects helper's list, notes/kh2-effects.md): 77/78 impacts wired by
       # spot33_magicfx.py (FXSE), 79/80 casts wired by spot33_spellsfx.py
       77: (os.path.join(MAGIC_DIR, 'thunder_hit.wav'), 100, 'Thundaga bolt strike (KH2 se 164 = se000_131, 1.5 s)'),
       78: (os.path.join(MAGIC_DIR, 'ice_hit.wav'), 100, 'Blizzaga ice shatter (KH2 se 124 = se000_004, 1.42 s)'),
       79: (os.path.join(MAGIC_DIR, 'thunder_cast.wav'), 90, 'Thundaga cast / charge (KH2 se 126 = se000_127, 1.2 s)'),
       80: (os.path.join(MAGIC_DIR, 'ice_cast.wav'), 90, 'Blizzaga cast (KH2 se 159 = se000_016, 1.2 s)'),
       # Reflect (EX Mode guard, notes/reflect.md §8; wired later by spot33_reflect.py): KH2 Reflega barrier-up / reflect.
       # Slot allocation (2026-10-15): 81-82 Reflect, 83+ Codex Keyblade audio (codex/keyblade-audio, review answers).
       81: (os.path.join(REFLECT_DIR, 'se_177.wav'), 90, 'Reflect barrier up (KH2 se 177, 1.2 s)'),
       82: (os.path.join(REFLECT_DIR, 'se_139.wav'), 90, 'Reflect hit / bounce (KH2 se 139, 1.2 s)'),
       # Keyblade sounds (Codex, codex/keyblade-audio review-v3 WAVs, 16 kHz; Mat approved the set). Swings 83/84/87/88
       # wired by spot33_weaponsfx.py; 89-95 = finisher effects (not wired yet).
       83: (os.path.join(KEY_DIR, 'weapon-option-A.wav'), 100, 'Kingdom Key swing A (KH2 W_EX010 se500 500000) - hit 1/4/7…'),
       84: (os.path.join(KEY_DIR, 'weapon-option-B.wav'), 100, 'Kingdom Key swing B (se500 500003) - hit 2/5/8…'),
       85: (os.path.join(KEY_DIR, 'weapon-option-C.wav'), 100, 'Kingdom Key option C (se500 500032), unused'),
       86: (os.path.join(KEY_DIR, 'weapon-option-D.wav'), 100, 'Kingdom Key option D (se500 500033), unused'),
       87: (os.path.join(KEY_DIR, 'weapon-option-E.wav'), 100, 'Kingdom Key swing E (se500 500036) - hit 3/6/9…'),
       88: (os.path.join(KEY_DIR, 'weapon-option-F.wav'), 100, 'Kingdom Key heavy last hit (se500 500037) - Ground Rave / Horizontal Slash finisher'),
       89: (os.path.join(KEY_DIR, 'guard-break-effect.wav'), 100, 'Guard Break (KH2 999005)'),
       90: (os.path.join(KEY_DIR, 'finishing-leap-start.wav'), 100, 'Finishing Leap start (KH2 999038)'),
       91: (os.path.join(KEY_DIR, 'finishing-leap-burst.wav'), 100, 'Finishing Leap burst (KH2 999039)'),
       92: (os.path.join(KEY_DIR, 'aerial-finish-effect-1.wav'), 100, 'Aerial Finish 1 (KH2 999007)'),
       93: (os.path.join(KEY_DIR, 'aerial-finish-effect-2.wav'), 100, 'Aerial Finish 2 (KH2 999008)'),
       94: (os.path.join(KEY_DIR, 'aerial-finish-effect-3.wav'), 100, 'Aerial Finish 3 (KH2 999006)'),
       95: (os.path.join(KEY_DIR, 'aerial-finish-effect-4.wav'), 100, 'Aerial Finish 4 (KH2 999151)')}


def arc_chunks(d):
    n, = struct.unpack_from('<I', d, 4)
    return [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]


def grow(bank, sfx):
    count, = struct.unpack_from('<I', bank, 12)
    added = []
    for slot in sorted(sfx):
        if slot < count:
            # refresh in place when the WAV was re-levelled (same length → same ADPCM size) or the volume changed
            path, vol, label = sfx[slot]
            w = wave.open(path)
            raw = w.readframes(w.getnframes())
            blob = sscf.encode(struct.unpack('<%dh' % (len(raw) // 2), raw), (len(raw) // 2 + 27) // 28 + 1)
            e = 0x20 + slot * 32
            o, z = struct.unpack_from('<II', bank, e + 4)
            if z == len(blob) and (bank[o:o + z] != blob or bank[e + 0x0E] != vol):
                bank[o:o + z] = blob
                bank[e + 0x0E] = vol
                added.append(slot)
                print('slot %d: refreshed (%s, vol %d)' % (slot, os.path.basename(path), vol))
            else:
                print('slot %d: already there' % slot)
            continue
        assert slot == count, 'slots must be appended in order: next is %d' % count
        path, vol, label = sfx[slot]
        w = wave.open(path)
        assert w.getsampwidth() == 2 and w.getnchannels() == 1, path + ': 16-bit mono WAV please'
        raw = w.readframes(w.getnframes())
        smp = struct.unpack('<%dh' % (len(raw) // 2), raw)
        blob = sscf.encode(smp, (len(smp) + 27) // 28 + 1)
        ent = bytearray(bank[0x20 + TEMPLATE * 32:0x40 + TEMPLATE * 32])
        hdr_end = 0x20 + count * 32
        for k in range(count):                                   # data moves 32 B down
            o, = struct.unpack_from('<I', bank, 0x20 + k * 32 + 4)
            if o:
                struct.pack_into('<I', bank, 0x20 + k * 32 + 4, o + 32)
        bank[hdr_end:hdr_end] = ent
        struct.pack_into('<IIH', ent, 4, len(bank), len(blob), w.getframerate())
        ent[0x0E] = vol
        bank[hdr_end:hdr_end + 32] = ent
        bank += blob
        count += 1
        struct.pack_into('<I', bank, 12, count)
        struct.pack_into('<I', bank, 8, len(bank))
        added.append(slot)
        print('slot %d <- %s (%s, %d Hz, %.2f s, vol %d, %d B)' % (slot, os.path.basename(path), label,
              w.getframerate(), len(smp) / w.getframerate(), vol, len(blob)))
    return bank, added


def main():
    iso = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    ch = arc_chunks(d)
    k = next(i for i, c in enumerate(ch) if c[1] == b'snd_')
    bank = bytearray(d[ch[k][2]:ch[k][2] + ch[k][3]])
    bank, added = grow(bank, SFX)
    if not added:
        print('nothing to add')
        return
    res = rebuild_arc(d, {k: bytes(bank)})
    print('file %d -> %d bytes' % (len(d), len(res)))
    if out:
        open(out, 'wb').write(res)
        print('written to', out, '(pkg_put.py ISO %s %s)' % (FILE, out))


if __name__ == '__main__':
    main()
