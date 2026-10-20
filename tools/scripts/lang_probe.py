# Guess the per-position XOR key of Dissidia 012 *_lang text tables from letter statistics.
import struct, sys
from collections import Counter
d = open(sys.argv[1], 'rb').read()
first, = struct.unpack_from('<H', d, 0)
n = first // 2
offs = [struct.unpack_from('<H', d, i * 2)[0] for i in range(n)]
print('table1 entries', n, 'first offsets', offs[:4])
# second-level: each table1 offset points at a u16 offset to the string
strs = []
for o in offs:
    s, = struct.unpack_from('<H', d, o)
    strs.append(s)
strs_sorted = sorted(set(strs)) + [len(d)]
blobs = [d[a:b] for a, b in zip(strs_sorted, strs_sorted[1:])]
print('strings', len(blobs), 'lengths', [len(b) for b in blobs[:10]])
key = []
for i in range(48):
    col = [b[i] for b in blobs if len(b) > i + 1]
    if len(col) < 20: break
    best = max(range(256), key=lambda k: sum(1 for c in col if chr(c ^ k).isalpha() or c ^ k == 0x20) )
    key.append(best)
print('key', bytes(key).hex())
for b in blobs[:25]:
    print(repr(bytes(c ^ key[i] if i < len(key) else c for i, c in enumerate(b))))
