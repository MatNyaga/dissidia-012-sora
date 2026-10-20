"""Give #33's effect package (obj/p_sev120.objx chunk `effe`) its own FEP id, so it no longer clashes with Cloud's.

Why (notes/effects-clash.md):
- Every fighter's `effe` MPK holds a FEP whose header +0x10 u32 is a global id (Cloud = 0x311C0000, i.e. 3143 << 18).
- FUN_08943124 refuses to register a FEP whose id (& 0xFFFC0000) is already loaded (FUN_0894349c). #33's effe is a
  byte copy of Cloud's, so in Cloud vs Sora the second one loaded gets no FEP. All of that fighter's effects (weapon
  trails 8888/9999, magi visuals like the Meteorain meteors, and the FXSE sounds tied to them) silently do nothing.
- Inside the FEP, resources refer to each other by id | (index << 10), so every such u32 must move with the header.

Fix: rewrite the header id and every internal id reference from OLD_ID to NEW_ID.
- 3146 << 18 = 0x31280000, free on the whole disc. The sev series is 100 = 3143, 200 = 3144, 110 = 3145.
- Same size; only effe bytes change. Rerun-safe: it reports "already" once the header carries NEW_ID.
- References are aligned u32 in the table area (offset < 0x10000), with (v & 0xFFFC0000) == OLD_ID and the low
  10 bits = 0. That is 226 on Cloud's copy. Matches further in, in texture data, are noise and are left alone.
--names also renames, same length, the MPK member names p_sev100.* → p_sev120.* and the FEP's
"P_SEV100_*_LEAF_0" debug names. Neither is used for lookups as far as the code shows (members are taken by index),
so it is cosmetic.
--fepa-model also renames the FEPA (.feb) +0x88 model names p_sev100_1p → p_sev120_1p. That makes the
motion-slot-bound Cloud effects auto-play on Sora's moves (FUN_088aa844 compares 8 chars with the model name), which
is probably NOT wanted while Sora reuses Cloud's slots for KH2 moves. Off by default.

Usage (read-only on the ISO):
  python3 -I spot33_effects.py ISO                  dry run: list what would change (file + ISO offsets)
  python3 -I spot33_effects.py ISO --out NEW.objx   also write a patched copy of the file (then pkg_put.py)
  extra flags: --names, --fepa-model
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from mpk import entries  # noqa: E402

FILE = 'obj/p_sev120.objx'
OLD_ID, NEW_ID = 0x311C0000, 0x31280000
TABLE_END = 0x10000


def main():
    iso = sys.argv[1]
    out = sys.argv[sys.argv.index('--out') + 1] if '--out' in sys.argv else None
    names, fepa_model = '--names' in sys.argv, '--fepa-model' in sys.argv
    use_iso(iso)
    start, size = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = bytearray(read_at(f, start, size))
    n, = struct.unpack_from('<I', d, 4)
    ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    _, _, eoff, esize = next(c for c in ch if c[1] == b'effe')
    mem = {nm: (eoff + o, s) for nm, o, s in entries(bytes(d[eoff:eoff + esize]))}
    fep = next(v for k, v in mem.items() if k.endswith('.fep'))
    feb = next(v for k, v in mem.items() if k.endswith('.feb'))
    changes = []                                   # (file offset, old bytes, new bytes, what)
    fo, fs = fep
    head, = struct.unpack_from('<I', d, fo + 0x10)
    if head & 0xFFFC0000 == NEW_ID:
        print('FEP id already 0x%08X' % NEW_ID)
    elif head & 0xFFFC0000 != OLD_ID:
        sys.exit('unexpected FEP id 0x%08X' % head)
    else:
        for o in range(0, min(fs, TABLE_END) - 3, 4):
            v, = struct.unpack_from('<I', d, fo + o)
            if v & 0xFFFC0000 == OLD_ID and v & 0x3FF == 0:
                nv = (v & 0x3FFFF) | NEW_ID
                changes.append((fo + o, struct.pack('<I', v), struct.pack('<I', nv), 'fep id ref'))
    if names:
        for nm, (o, s) in mem.items():
            p = d.find(nm.encode(), eoff, eoff + 0x100)
            if 'sev100' in nm and p > 0:
                changes.append((p, nm.encode(), nm.replace('sev100', 'sev120').encode(), 'mpk member name'))
        p = fo
        while True:
            p = d.find(b'P_SEV100_', p, fo + fs)
            if p < 0:
                break
            changes.append((p, b'P_SEV100_', b'P_SEV120_', 'fep leaf name'))
            p += 9
    if fepa_model:
        bo, bs = feb
        cnt, = struct.unpack_from('<I', d, bo + 12)
        for k in range(cnt):
            p = bo + 0x10 + k * 0x104 + 0x88
            if d[p:p + 11].lower() == b'p_sev100_1p':
                changes.append((p, bytes(d[p:p + 11]), b'p_sev120_1p', 'fepa model name'))
    kinds = {}
    for o, old, new, what in changes:
        kinds[what] = kinds.get(what, 0) + 1
    for o, old, new, what in changes[:8]:
        print('  file +0x%06X  ISO 0x%08X  %s -> %s  (%s)' % (o, start + o, old.hex(), new.hex(), what))
    if len(changes) > 8:
        print('  ... %d more' % (len(changes) - 8))
    print('changes:', kinds or 'none')
    if out:
        for o, old, new, what in changes:
            assert d[o:o + len(old)] == old, hex(o)
            d[o:o + len(new)] = new
        open(out, 'wb').write(d)
        print('patched copy written to', out, '(put it in with: pkg_put.py ISO %s %s)' % (FILE, out))


if __name__ == '__main__':
    main()
