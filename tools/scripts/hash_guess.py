# Try common 32-bit string hashes on file paths found in the code, against PACKAGE_INFO hashes.
import re, struct, sys, zlib
info = open(sys.argv[1], 'rb').read()
n, = struct.unpack_from('<I', info, 8)
hashes = {struct.unpack_from('<I', info, 16 + i * 12)[0] for i in range(n)}
names = set()
for path in sys.argv[2:]:
    for line in open(path, errors='ignore'):
        line = line.strip()
        if re.fullmatch(r'[\w./-]+\.\w{2,5}', line) and '%' not in line:
            names.add(line)
M = 0xFFFFFFFF
def fnv1(s):
    h = 0x811C9DC5
    for c in s: h = (h * 0x01000193) & M; h ^= c
    return h
def fnv1a(s):
    h = 0x811C9DC5
    for c in s: h ^= c; h = (h * 0x01000193) & M
    return h
def djb2(s):
    h = 5381
    for c in s: h = (h * 33 + c) & M
    return h
def sdbm(s):
    h = 0
    for c in s: h = (c + (h << 6) + (h << 16) - h) & M
    return h
def oaat(s):
    h = 0
    for c in s:
        h = (h + c) & M; h = (h + (h << 10)) & M; h ^= h >> 6
    h = (h + (h << 3)) & M; h ^= h >> 11; h = (h + (h << 15)) & M
    return h
def mul31(s):
    h = 0
    for c in s: h = (h * 31 + c) & M
    return h
def crc(s): return zlib.crc32(s) & M
def crcinv(s): return (~zlib.crc32(s)) & M
funcs = dict(crc=crc, crcinv=crcinv, fnv1=fnv1, fnv1a=fnv1a, djb2=djb2, sdbm=sdbm, oaat=oaat, mul31=mul31)
variants = dict(asis=lambda s: s, lower=str.lower, upper=str.upper)
prefixes = ['', 'data/', '/', 'disc0:/PSP_GAME/USRDIR/data/']
print(len(names), 'names,', len(hashes), 'hashes')
for fn, f in funcs.items():
    for vn, v in variants.items():
        for p in prefixes:
            hits = [nm for nm in names if f(v(p + nm).encode()) in hashes]
            if hits: print(fn, vn, repr(p), len(hits), hits[:5])
