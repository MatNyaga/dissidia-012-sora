"""P0.9: read the header of a Data Install file (ms0:/PSP/SAVEDATA/ULUS10566Data/DISSINST.DAT) - read-only.

  python3 -I tools/dlc/dissinst_head.py DISSINST.DAT [ISO]

Header (0x1BB78 bytes at file offset 0; EBOOT FUN_0886f7a8 / FUN_0886f5d4 / FUN_0886fac0):
  +0x00 i32 entry count (<= 4050)      +0x04 i32 level 1..3       +0x08 i32 checksum (sum of signed byte + (len - i)
  over the whole plain header with +8 = 0)   +0x0C i32 raw byte total of the installed files   +0x10 u8 seed (8)
  +0x14 i32 version 1   +0x80.. 4050 entries x 0x1C, obfuscated: byte -= x where x = x*5+1 (8-bit, x starts = seed).
  entry: +0 u16 PACKAGE_INFO row index, +2 u16 checksum16 of the stored (encrypted) data, +4 u32 file offset / 0x2000,
  +8 20-byte HMAC-SHA1 of the stored data. File data = Blowfish-encrypted with a fixed key from the EBOOT (not needed
  here and not printed).
With ISO: also checks count / total against that ISO's PACKAGE_INFO (what the game checks at boot).
"""
import os
import struct
import sys

HDR = 0x1BB78


def main():
    d = bytearray(open(sys.argv[1], 'rb').read(HDR))
    assert len(d) == HDR, 'file shorter than the header'
    count, level, ck, total = struct.unpack_from('<iiii', d, 0)
    seed, ver = d[0x10], struct.unpack_from('<i', d, 0x14)[0]
    x = seed
    for i in range(0x80, HDR):
        x = (x * 5 + 1) & 0xFF
        d[i] = (d[i] - x) & 0xFF
    struct.pack_into('<i', d, 8, 0)
    s = 0
    for i, b in enumerate(d):
        s = (s + (b - 256 if b > 127 else b) + (HDR - i)) & 0xFFFFFFFF
    s = s - (1 << 32) if s & 0x80000000 else s
    print('count %d  level %d  version %d  seed %d  total %d (%.1f MB)  checksum %d -> %s' % (
        count, level, ver, seed, total, total / 2**20, ck, 'OK' if s == ck else 'MISMATCH (computed %d)' % s))
    ents = [struct.unpack_from('<HHI', d, 0x80 + 0x1C * k) for k in range(max(0, min(count, 4050)))]
    for k in list(range(min(3, len(ents)))) + list(range(max(3, len(ents) - 2), len(ents))):
        r, c, o = ents[k]
        print('  entry %4d: row %5d  ck16 %04x  offset 0x%x' % (k, r, c, o * 0x2000))
    rows_sorted = all(ents[k][0] < ents[k + 1][0] for k in range(len(ents) - 1))
    offs_up = all(ents[k][2] < ents[k + 1][2] for k in range(len(ents) - 1))
    print('rows ascending: %s  offsets ascending: %s  file size %d' % (rows_sorted, offs_up, os.path.getsize(sys.argv[1])))
    if len(sys.argv) > 2:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from install_plan import iso_file
        with open(sys.argv[2], 'rb') as f:
            info = iso_file(f, '/PSP_GAME/USRDIR/DATA/PACKAGE_INFO.BIN')
        n = struct.unpack_from('<I', info, 8)[0]
        rows = [struct.unpack_from('<3I', info, 16 + 12 * i) for i in range(n)]
        sel = [r for r in rows if 0 < (r[2] >> 28) <= level]
        want_total = sum(r[2] & 0x0FFFFFFF for r in sel)
        ok = len(sel) == count and want_total == total and 1 <= level <= 3 and ver == 1 and s == ck
        print('ISO expects count %d total %d -> install would be %s at boot' % (
            len(sel), want_total, 'ACCEPTED' if ok else 'REJECTED (game reads the disc instead)'))


if __name__ == '__main__':
    main()
