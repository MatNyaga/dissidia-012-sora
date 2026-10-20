"""P2 / costume 2-3 Sora still had Cloud data (notes/p2-audit.md, 2026-10-16).

Mat: "when Sora is on P2 and goes into EX Mode it says 'Equipped Ultima Weapon'".
The EX Mode entry banner is NOT in the objx scripts: FUN_08aca4d8 shows text index *(u16*)(cosx + 0x38) of the
fighter's COSTUME file obj/<NAME>.cosx. Since test 17 the three costume files are Cloud's (swapped):
  P_SEV120_1P.cosx = Cloud 2P (0x38 = 9 -> entry 10 "My friends are my power!")
  P_SEV120_2P.cosx = Cloud 1P, _3P = Cloud 3P (0x38 = 8 -> entry 9 "Equipped Ultima Weapon!", Cloud's text)
The mirror-match CPU (and any Sora in costume 2/3) loads _2P/_3P. Same for the EX aura file .exex (colours).

This script:
1. copies P_SEV120_1P.cosx and .exex over _2P and _3P (same 68 / 88 bytes, in place; their own sectors);
   guard: the 2P/3P file must be one of Cloud's vanilla costume files or already the 1P data;
2. renames text entry 9 of obj/p_sev120.objx ("Equipped Ultima Weapon!", Cloud's, now unused) to the same line as
   entry 10, so no costume can ever show Cloud's text (in place inside the `text` chunk; never grows).
Only owner-33 files are written. Re-runnable ("already").

  python3 -I spot33_p2fix.py ISO [--dry]
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
import spot33_battlenames as bn  # noqa: E402

COSTUME = 'obj/P_SEV120_%s.%s'
CLOUD = 'obj/P_SEV100_%s.%s'
OBJX = 'obj/p_sev120.objx'
OLD9 = 'Equipped Ultima Weapon!'
EX_LINE = 'My friends are my power!'          # entry 10 = what P1 shows (spot33_battlenames NAMES[10])


def get(iso, path):
    use_iso(iso)
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        return st, read_at(f, st, sz)


def costumes(iso, dry, writes):
    for ext in ('cosx', 'exex'):
        _, one = get(iso, COSTUME % ('1P', ext))
        cloud = {get(iso, CLOUD % (p, ext))[1] for p in ('1P', '2P', '3P')}
        assert one in cloud, '%s is not a Cloud costume file any more - check by hand' % (COSTUME % ('1P', ext))
        if ext == 'cosx':
            idx, = struct.unpack_from('<h', one, 0x38)
            print('1P.cosx EX banner index %d (= text entry %d)' % (idx, idx + 1))
            assert idx == 9, 'expected 1P banner index 9 (entry 10 "%s")' % EX_LINE
        for p in ('2P', '3P'):
            path = COSTUME % (p, ext)
            st, cur = get(iso, path)
            if cur == one:
                print('%s: already the 1P data' % path)
                continue
            assert cur in cloud and len(cur) == len(one), '%s: neither a Cloud costume file nor ours' % path
            note = ''
            if ext == 'cosx':
                note = ' (EX banner index %d -> %d)' % (struct.unpack_from('<h', cur, 0x38)[0], 9)
            print('%s <- 1P data%s%s' % (path, note, ' [dry]' if dry else ''))
            writes.append((st, one))


def text9(iso, dry, writes):
    st, d = get(iso, OBJX)
    assert d[:4] == b'ARC\x01'
    n, = struct.unpack_from('<I', d, 4)
    chunks = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    _, _, coff, csize = next(ch for ch in chunks if ch[1] == b'text')
    c = d[coff:coff + csize]
    assert c[:4] == b'mlng'
    nl, = struct.unpack_from('<I', c, 4)
    offs = list(struct.unpack_from('<%dI' % nl, c, 8))
    sizes = list(struct.unpack_from('<%dI' % nl, c, 8 + 4 * nl))
    blocks = [bytes(c[o:o + s]) for o, s in zip(offs, sizes)]
    raws = bn.parse_block(blocks[0])
    t9, t10 = bn.text_of(raws[9]), bn.text_of(raws[10])
    assert t10 == EX_LINE, 'entry 10 is %r, expected %r (run spot33_battlenames first)' % (t10, EX_LINE)
    if t9 == EX_LINE:
        print('text entry 9: already %r' % EX_LINE)
        return
    assert t9 == OLD9, 'text entry 9 is %r (expected Cloud\'s %r)' % (t9, OLD9)
    raws[9] = bn.encode(EX_LINE)
    blocks[0] = bn.build_block(raws)
    assert bn.text_of(bn.parse_block(blocks[0])[9]) == EX_LINE
    pos = 8 + 8 * nl
    out = bytearray(c[:pos])
    for k, b in enumerate(blocks):
        struct.pack_into('<I', out, 8 + 4 * k, len(out))
        struct.pack_into('<I', out, 8 + 4 * nl + 4 * k, len(b))
        out += b
    assert len(out) <= csize, 'text chunk would grow (%d > %d) - not done' % (len(out), csize)
    out += b'\0' * (csize - len(out))
    # every other language block and every other English entry must be unchanged
    nb = bn.parse_block(blocks[0])
    old = bn.parse_block(bytes(c[offs[0]:offs[0] + sizes[0]]))
    assert len(nb) == len(old) and all(nb[k] == old[k] for k in range(1, len(old)) if k != 9)
    print('text entry 9: %r -> %r (chunk %d/%d B)%s' % (t9, EX_LINE, pos + sum(map(len, blocks)), csize,
                                                        ' [dry]' if dry else ''))
    writes.append((st + coff, bytes(out)))


def main():
    a = [x for x in sys.argv[1:] if not x.startswith('--')]
    dry = '--dry' in sys.argv
    iso = a[0]
    assert not os.path.basename(iso).startswith('ULUS10566.iso'), 'never write the clean ISO'
    writes = []
    costumes(iso, dry, writes)
    text9(iso, dry, writes)
    if dry or not writes:
        print('%d write(s) %s' % (len(writes), 'planned (dry run)' if dry else '- nothing to do'))
        return
    with open(iso, 'r+b') as f:
        for at, data in writes:
            f.seek(at)
            f.write(data)
    print('%d write(s) done' % len(writes))


if __name__ == '__main__':
    main()
