"""EX Burst power-up (tap Circle, motion 8101 / _801B) shows Codex's strained-angry face: in the p_se type-8 block that
type 7 maps motion 8101 to, the face-state event op 0x14 [0, 2] becomes [0, 6] (eye/face ID 6 = EX_STRAIN, added to the
model by codex/inbox/20261015-ex-strained-face/build_face.py). Same size; re-runnable (already 6 = nothing to do).
Needs the model WITH the strain atlas (face ID 6), else the face channel has no ID 6.

  python3 -I spot33_exface.py ISO [--dry]
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import fep_edit as E  # noqa: E402

FILE = 'obj/p_sev120.objx'
MOTION, OLD, NEW = 8101, 2, 6


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    d = bytearray(E.load_objx(iso, FILE))
    ent = E.arc_entries(d)
    t7 = next(e for e in ent if e[0] == 7 and e[1] == b'p_se')
    t8 = next(e for e in ent if e[0] == 8 and e[1] == b'p_se')
    rows = [struct.unpack_from('<4H', d, t7[2] + 8 + 8 * i) for i in range(struct.unpack_from('<I', d, t7[2] + 4)[0])]
    blk = next(r[1] for r in rows if r[0] == MOTION)
    off = t8[2] + struct.unpack_from('<I', d, t8[2] + 8 + blk * 4)[0]
    assert struct.unpack_from('<H', d, off)[0] == blk
    cur, hits = off + 8, []
    for _ in range(d[off + 2]):
        n = d[cur + 5]
        if d[cur + 4] == 0x14 and n == 2 and struct.unpack_from('<2I', d, cur + 12) in ((0, OLD), (0, NEW)):
            hits.append(cur + 16)
        cur += 12 + 4 * n
    assert len(hits) == 1, hits
    if struct.unpack_from('<I', d, hits[0])[0] == NEW:
        print('nothing to do (motion %d block %d face state already %d)' % (MOTION, blk, NEW))
        return
    struct.pack_into('<I', d, hits[0], NEW)
    print('motion %d block %d: face state %d -> %d' % (MOTION, blk, OLD, NEW))
    if dry:
        return
    fd, tmp = tempfile.mkstemp(suffix='.objx')
    os.write(fd, bytes(d))
    os.close(fd)
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, tmp], check=True)
    os.unlink(tmp)


if __name__ == '__main__':
    main()
