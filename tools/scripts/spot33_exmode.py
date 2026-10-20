"""Own EX Mode transformation animation for #33 (Mat 2026-10-15: "the ex mode animation when he is transitioning from
normal to EX mode and he says light should be the drive animation").
EX Mode start = motion 5000, which shared Cloud's GMO slot _501A (block 38) with the homing dash (241) and 801.
This gives 5000 its own p_se block 103 (= GMO motion 103 = _736A, appended by build_sora.sh SLOTS and filled with
KH2 210 CHANGEFORM) — a copy of block 38's script (op0a / op1e at 10 = the EX switch / op14) — and points the type-7
row of 5000 at it. Block numbers must equal GMO motion indexes, so this runs AFTER spot33_magic.py (blocks 97-102).
Re-runnable.  python3 -I spot33_exmode.py ISO
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402

FILE = 'obj/p_sev120.objx'
MOTION, BLOCK = 5000, 103


def main():
    iso = sys.argv[1]
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    n, = struct.unpack_from('<I', d, 4)
    ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7)
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8)
    t7 = bytearray(d[ch[i7][2]:ch[i7][2] + ch[i7][3]])
    c = bytearray(d[ch[i8][2]:ch[i8][2] + ch[i8][3]])
    m7, = struct.unpack_from('<I', t7, 4)
    row = next(k for k in range(m7) if struct.unpack_from('<H', t7, 8 + k * 8)[0] == MOTION)
    cur, = struct.unpack_from('<H', t7, 10 + row * 8)
    m, = struct.unpack_from('<I', c, 4)
    if cur == BLOCK and m > BLOCK:
        print('motion %d already uses block %d' % (MOTION, BLOCK))
        return
    assert m == BLOCK, 'expected the next free block to be %d (found %d blocks)' % (BLOCK, m)
    offs = list(struct.unpack_from('<%dI' % m, c, 8))
    src = bytearray(c[offs[cur]:offs[cur] + struct.unpack_from('<H', c, offs[cur] + 6)[0]])
    src[0] = BLOCK
    body = bytes(c[8 + 4 * m:])
    body += b'\0' * ((-len(body)) % 4)
    offs = [o + 4 for o in offs] + [8 + 4 * (m + 1) + len(body)]
    c = bytearray(struct.pack('<II', struct.unpack_from('<I', c, 0)[0], m + 1)) + struct.pack('<%dI' % (m + 1), *offs) + body + src
    struct.pack_into('<H', t7, 10 + row * 8, BLOCK)
    print('motion %d: block %d -> own block %d (copy)' % (MOTION, cur, BLOCK))
    out = rebuild_arc(d, {i7: bytes(t7), i8: bytes(c)})
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
