"""Dump KH2 motion triggers (ANB sub-entry type 16) of P_EX100.mset: python3 -I kh2_triggers.py OUT.json IDX... (notes/kh2-finishers.md)"""
import struct, sys, json
import os
d = open(os.environ.get('MSET', './kh2_export/raw/kh2_sixth/original/obj/P_EX100.mset'), 'rb').read()   # MSET=…P_EX100_KH1F.mset for Limit Form
def bar(d):
    n = struct.unpack_from('<I', d, 4)[0]
    return [struct.unpack_from('<HH4sII', d, 16 + 16 * i) for i in range(n)]
def trig(tr):
    nr, nf, fo = struct.unpack_from('<BBH', tr, 0)
    R, F = [], []
    p = 4
    for _ in range(nr):
        s, e, t, ps = struct.unpack_from('<hhBB', tr, p); p += 6
        R.append((s, e, t, list(struct.unpack_from('<%dh' % ps, tr, p)))); p += 2 * ps
    p = fo
    for _ in range(nf):
        f, t, ps = struct.unpack_from('<hBB', tr, p); p += 4
        F.append((f, t, list(struct.unpack_from('<%dh' % ps, tr, p)))); p += 2 * ps
    return R, F
E = bar(d); out = {}
for i, (t, dup, name, off, size) in enumerate(E):
    if t != 17 or size == 0: continue
    sub = d[off:off + size]
    for s in bar(sub):
        if s[0] == 16:
            R, F = trig(sub[s[3]:s[3] + s[4]])
            out[i] = dict(name=name.decode(), R=R, F=F)
json.dump(out, open(sys.argv[1], 'w'))
want = [int(x) for x in sys.argv[2:]]
for i in want:
    if i not in out: print(i, 'no triggers'); continue
    o = out[i]
    print(i, o['name'], 'R:', ' '.join('[%d-%d t%d %s]' % (s, e, t, p) for s, e, t, p in o['R'] if t != 23))
    print('    F:', ' '.join('[f%d t%d %s]' % (f, t, p) for f, t, p in o['F']))
