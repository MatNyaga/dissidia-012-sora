"""DIAGNOSTIC ONLY (not for release): owner 33's assist loads CLOUD's stock assist files, to bisect "Sora as assist:
the assist gauge never fills" (Mat, test301) -- notes/assist.md section 6.

Keeps every owner-33 table spot33_assist.py set up (assist.bin row/records, objentry kind-8 row bytes) and only
swaps what the assist object is built from:
  - objentry rows P_SEV120_{1,2,3}P_A: name -> P_SEV100_xP_A, model -> p_sev100_a (Cloud's stock files)
  - eqaa 396 (owner 33's assist loadout): -> copy of Cloud's eqaa 301 (owner 13, idx 1/7/10/13 = 314/321/326/328)
  - assist.bin owner-33 action list -> 314/321/326/328 (Cloud's assist comb)
Gauge fills with this disc  -> the fault is in the Sora assist FILES (objx / GMO / voice) built by spot33_assist.py.
Gauge still empty           -> the fault is on the owner-33 TABLE side (assist.bin / eqaa / chrp / menu pick).

  python3 -I diag_assist_cloudfiles.py ISO [--dry]       (main.bin only; needs spot33_assist.py already applied)
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True


def main(argv):
    iso, dry = argv[0], '--dry' in argv
    assert os.path.basename(iso) != 'ULUS10566.iso'
    import mpk
    from comb_patch import pkg_offset, read_at, use_iso
    from spot33_save import arc_join, arc_split
    use_iso(iso)
    with open(iso, 'rb') as f:
        st, sz = pkg_offset('general_archive/main/main.bin')
        mb = read_at(f, st, sz)
    mem = {n: bytearray(mb[o:o + s]) for n, o, s in mpk.entries(mb)}
    ob = mem['objentry.bin']
    n = struct.unpack_from('<I', ob, 4)[0]
    for i in range(n):
        at = 8 + 68 * i
        r = ob[at:at + 68]
        if r[6] == 33 and r[8] == 8:
            nm = r[0x24:0x34].split(b'\0')[0]
            assert nm in (b'P_SEV120_1P_A', b'P_SEV120_2P_A', b'P_SEV120_3P_A', b'P_SEV100_1P_A', b'P_SEV100_2P_A',
                          b'P_SEV100_3P_A'), nm
            assert struct.unpack_from('<H', r, 2)[0] == 6, 'run spot33_assist.py first'
            ob[at + 0x24:at + 0x34] = nm.replace(b'SEV120', b'SEV100').ljust(16, b'\0')
            ob[at + 0x34:at + 0x44] = b'p_sev100_a'.ljust(16, b'\0')
            print('objentry row %d: %s -> %s / p_sev100_a' % (i, nm.decode(), nm.decode().replace('SEV120', 'SEV100')))
    head, chs = arc_split(bytes(mem['system.bin']))
    for c in chs:
        if c[1] == b'eqaa':
            e = bytearray(c[2])
            rows = {struct.unpack_from('<h', e, 8 + 94 * k)[0]: 8 + 94 * k for k in range(struct.unpack_from('<I', e, 4)[0])}
            src = e[rows[301]:rows[301] + 94]
            assert struct.unpack_from('<h', src, 2)[0] == 13
            e[rows[396] + 2:rows[396] + 94] = src[2:]
            c[2] = bytes(e)
            print('eqaa 396 <- copy of Cloud\'s eqaa 301 (owner 13, idx 1/7/10/13)')
    mem['system.bin'] = bytearray(arc_join(head, chs))
    ab = mem['assist.bin']
    cnt = struct.unpack_from('<I', ab, 4)[0]
    lst = 8 + 104 * cnt + 4
    for k, a in zip((122, 123, 124, 125), (314, 321, 326, 328)):
        struct.pack_into('<H', ab, lst + 2 * k, a)
    print('assist.bin owner-33 action list -> 314/321/326/328')
    new = mb
    for name in ('objentry.bin', 'system.bin', 'assist.bin'):
        new = mpk.replace(new, name, bytes(mem[name]))
    assert len(new) == len(mb), 'main.bin size changed'
    if dry:
        print('--dry: nothing written')
        return
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'main.bin')
        open(p, 'wb').write(new)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, 'general_archive/main/main.bin',
                            p], check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main(sys.argv[1:])
