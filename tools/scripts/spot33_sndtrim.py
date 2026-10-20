"""Shrink #33's snd_ bank: every slot that nothing references any more gets a 2-block silent sample (32 B).

Why (2026-10-15, test209/210): the Keyblade slots grew Sora's bank 538 KB → 606 KB; in a Sora mirror match the
game then no longer loaded a 436 KB shared battle sound bank → the BREAK sound and the win voice line went missing
(test204 vs test210 break logs, scratch break_watch). Cloud's leftovers (EX shouts, sword hits now replaced by the
Keyblade set) are ~317 KB of the bank.

A slot counts as referenced when its absolute id (2200000/21900000 + slot) appears as an aligned u32 anywhere in
Sora's objx outside snd_ (script events op 0x03/0x11, …) or in an FXSE record (effe member 2: {base, slot, …}).
Slot numbers and entry params stay; only data shrinks, so ids never move. KEEP = slots kept anyway.
Run late: after every step that adds sound references (spot33_weaponsfx / magicfx / reflect), any place before or
after spot33_soundids (both bases handled). Re-runnable ("nothing to trim").

  python3 -I spot33_sndtrim.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fep_edit as E  # noqa: E402
import sscf  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402

FILE = 'obj/p_sev120.objx'
BASES = (2200000, 21900000)
KEEP = {81, 82}          # Reflect barrier / bounce (notes/reflect.md §8: EX-only sounds, wiring planned)
SILENT = bytes(sscf.encode([0] * 28, 2))


def referenced(d, count):
    used = set()
    for t, tag, o, z in E.arc_entries(d):
        if tag == b'snd_':
            continue
        blob = d[o:o + z]
        for k in range(0, len(blob) - 3, 4):
            v, = struct.unpack_from('<I', blob, k)
            for b in BASES:
                if b <= v < b + count:
                    used.add(v - b)
    fx = E.mpk_member(d, 2)
    for k in range(16, len(fx) - 19, 20):
        b, s = struct.unpack_from('<II', fx, k)
        if b in BASES and s < count:
            used.add(s)
    return used


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    d = E.load_objx(iso, FILE)
    ents = E.arc_entries(d)
    k = next(i for i, c in enumerate(ents) if c[1] == b'snd_')
    bank = d[ents[k][2]:ents[k][2] + ents[k][3]]
    count, = struct.unpack_from('<I', bank, 12)
    used = referenced(d, count) | KEEP
    items = list(sscf.entries(bank))
    trim = [i for i, o, z, r in items if i not in used and z and bank[o:o + z] != SILENT]
    if not trim:
        print('nothing to trim (%d B, %d slots)' % (len(bank), count))
        return
    hdr = 0x20 + count * 32
    new = bytearray(bank[:hdr])
    placed = {}                                       # entries may share one sample (same offset/size) → keep shared
    for i, o, z, r in sorted(items, key=lambda x: x[1]):
        if not z:                                     # empty entries stay empty
            continue
        key = ('silent',) if i in trim else (o, z)
        if key not in placed:
            while len(new) % 16:
                new.append(0)
            data = SILENT if i in trim else bank[o:o + z]
            placed[key] = (len(new), len(data))
            new += data
        struct.pack_into('<II', new, 0x20 + i * 32 + 4, *placed[key])
    struct.pack_into('<I', new, 8, len(new))
    print('trimmed slots %s: bank %d -> %d B' % (trim, len(bank), len(new)))
    for i, o, z, r in sscf.entries(bytes(new)):         # untouched slots kept byte-identical
        if i not in trim and items[i][2]:
            assert bytes(new[o:o + z]) == bank[items[i][1]:items[i][1] + items[i][2]]
    if dry:
        return
    res = rebuild_arc(d, {k: bytes(new)})
    fd, tmp = tempfile.mkstemp(suffix='.objx')
    os.write(fd, res)
    os.close(fd)
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, tmp], check=True)
    os.unlink(tmp)


if __name__ == '__main__':
    main()
