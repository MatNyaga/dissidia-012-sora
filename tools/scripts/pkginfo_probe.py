# Probe PACKAGE_INFO.BIN entry layout: header 16 bytes, then N x 12-byte entries.
import struct, sys
data = open(sys.argv[1], 'rb').read()
magic, = struct.unpack_from('<I', data, 0)
n, = struct.unpack_from('<I', data, 8)
print('magic %08x name %r count %d' % (magic, data[4:8], n))
ents = [struct.unpack_from('<III', data, 16 + i * 12) for i in range(n)]
for e in ents[:8]:
    print(' '.join('%08x' % w for w in e), '|', ' '.join('{:032b}'.format(w) for w in e[1:]))
from collections import Counter
w1 = [e[1] for e in ents]; w2 = [e[2] for e in ents]
print('w1 max %08x min %08x' % (max(w1), min(w1)))
print('w2 max %08x  top nibbles' % max(w2), Counter(w >> 28 for w in w2))
print('w2 low 8 bits', Counter(w & 0xff for w in w2).most_common(8))
print('w1 top 12 bits nonzero:', sum(1 for w in w1 if w >> 20))
print('sum w1 = %d  (PACKAGE.BIN is 1034358784)' % sum(w1))
s = sorted(ents, key=lambda e: e[1])
fits = 0; samples = []
for a, b in zip(s, s[1:]):
    gap = (b[1] - a[1]) * 0x800
    for name, sz in (('low28', a[2] & 0x0fffffff), ('low30', a[2] & 0x3fffffff)):
        pass
    sz = a[2] & 0x0fffffff
    if sz <= gap and gap - sz < 0x800: fits += 1
    elif len(samples) < 6: samples.append(('%08x' % a[2], gap))
print('size=low28 fits gap exactly (padding <2KB): %d / %d' % (fits, len(s) - 1))
print('misfits sample', samples)
print('dup offsets', len(s) - len(set(e[1] for e in s)))
