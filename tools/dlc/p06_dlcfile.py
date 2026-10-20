"""P0.6 test DLC files (plain, unencrypted) for the game's own costume-DLC loader. Reads an ISO, never writes it.

Loader facts (notes/dlc.md appendix A, notes/dlc-phase0.md P0.6): the menu program asks for dlc/obj/dlc_%03doe.bin
(000..255) at ms0:/PSP/GAME/ULUS10566/<crc>.edat, crc = pkghash CRC of the lower-cased internal name. One file =
8-byte header + ONE 68-byte objentry row at +8 (FUN_08862254 -> FUN_08847068: bsearch the u16 id, memcpy 0x44).
The id MUST already exist (no match = write to address 0), so we overwrite Cloud's placeholder row id 1297
`P_SEV100_3P_PUB` (owner 13, +7 = 1, no files on disc, = the real-DLC placeholder for Cloud's 4th costume).

Stage A (default test, `A-costume4-disc/`): row 1297 := copy of Cloud's costume-3 row (id 552, `P_SEV100_3P`) with
  +7 = 4 (costume 4), +9 = 0 (files from the disc). Visible: Cloud gets a 4th costume in every costume picker
  (bits 4..12 of the costume mask = "a row with +7 = k exists"); picking it shows the costume-3 look.
Stage B (`B-costume4-ms0/`): same row with +9 = 1 = "model from Memory Stick" -> obj/P_SEV100_3P.gmo/.cosx/.exex are
  read from ms0 by their CRC names (copies of the disc files are written next to the row file). Visible: costume 4
  looks like costume 3 if the ms0 model loaded; if the ms0 read fails the game falls back to costume 1's row
  (FUN_088450a8 -> FUN_08844fe4) and costume 4 looks like Cloud's normal outfit.

  python3 -I tools/dlc/p06_dlcfile.py [--dry] [ISO]      ISO default dumps/ULUS10566-test338-voicesloud.iso
Writes only under tools/dlc/p06_files/{A-costume4-disc,B-costume4-ms0}/PSP/GAME/ULUS10566/. Re-runnable.
"""
import hashlib
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
from pkghash import pkg_hash  # noqa: E402
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from ablt_patch import mpk_member  # noqa: E402

OUT = os.path.join(HERE, 'p06_files')
STICK = 'PSP/GAME/ULUS10566'
TARGET_ID, DONOR_ID = 1297, 552
TARGET_NAME, DONOR_NAME = b'P_SEV100_3P_PUB', b'P_SEV100_3P'
CLOUD = 13
HEADER = struct.pack('<II', 0x0C, 1)            # objentry.bin header style (word 0 = 0x0C, count); loader skips it
ROWFILE = 'dlc/obj/dlc_000oe.bin'
MODEL_FILES = ['obj/P_SEV100_3P.gmo', 'obj/P_SEV100_3P.cosx', 'obj/P_SEV100_3P.exex']


def objentry(iso):
    use_iso(iso)
    st, _ = pkg_offset('general_archive/main/main.bin')
    with open(iso, 'rb') as f:
        o, n = mpk_member(f, st, 'objentry.bin')
        ob = read_at(f, o, n)
    cnt, = struct.unpack_from('<I', ob, 4)
    return {struct.unpack_from('<H', ob, 8 + 68 * i)[0]: ob[8 + 68 * i:8 + 68 * i + 68] for i in range(cnt)}


def name(r):
    return r[0x24:0x34].split(b'\0')[0]


def pkg_file(iso, path):
    use_iso(iso)
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        return read_at(f, st, sz)


def put(path, data, dry):
    rel = os.path.relpath(path, ROOT)
    if os.path.exists(path) and open(path, 'rb').read() == data:
        print('  same     %s (%d B)' % (rel, len(data)))
        return
    print('  %s %s (%d B, sha256 %s)' % ('[dry]   ' if dry else 'write   ', rel, len(data),
                                       hashlib.sha256(data).hexdigest()[:16]))
    if not dry:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        open(path, 'wb').write(data)


def main():
    dry = '--dry' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    iso = os.path.abspath(args[0] if args else os.path.join(ROOT, 'dumps/ULUS10566-test338-voicesloud.iso'))
    rows = objentry(iso)
    tgt, don = rows.get(TARGET_ID), rows.get(DONOR_ID)
    assert tgt is not None and name(tgt) == TARGET_NAME and tgt[6] == CLOUD and tgt[7] == 1 and tgt[9] == 0, tgt
    assert don is not None and name(don) == DONOR_NAME and don[6] == CLOUD and don[7] == 3 and don[8] == 0, don
    assert not any(r[6] == CLOUD and r[7] == 4 for r in rows.values()), 'Cloud already has a costume-4 row'
    crc = pkg_hash(ROWFILE)
    assert crc == 0xA590D742
    print('%s: %d unique objentry ids; target id %d %s -> costume 4 = %s' % (
        os.path.relpath(iso, ROOT), len(rows), TARGET_ID, TARGET_NAME.decode(), DONOR_NAME.decode()))
    for stage, ms0 in (('A-costume4-disc', 0), ('B-costume4-ms0', 1)):
        r = bytearray(don)
        struct.pack_into('<H', r, 0, TARGET_ID)
        r[7], r[9] = 4, ms0
        data = HEADER + bytes(r)
        assert len(data) == 76
        print('%s: row %s' % (stage, bytes(r).hex()))
        d = os.path.join(OUT, stage, STICK)
        put(os.path.join(d, '%08x.edat' % crc), data, dry)
        if ms0:
            for p in MODEL_FILES:
                put(os.path.join(d, '%08x.edat' % pkg_hash(p)), pkg_file(iso, p), dry)
                print('           = %s' % p)
    print('[dry] nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
