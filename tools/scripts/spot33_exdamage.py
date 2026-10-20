"""Sora's EX Mode Bravery damage x1.5 (Mat: "the brv attacks in Sora's EX mode do very little damage"). Data only.
Research: notes/ex-damage.md.

Bravery damage = atkp power x EX multiplier FUN_08b34244 x attack/defence curve (FUN_08ae45b8). The EX multiplier is
picked by chrp +0x0C bits, only while in EX Mode (FUN_08b34378):
  bit 0x1     x (1 + HP% x spec[+9] / 100)   "Ultima Weapon" (spec row = battle.bin `spec`, key chrp +4)
  bit 0x80000 x (1 + EX gauge% x spec[+10] / 100)
  bit 0x400   x 1.5 flat (overlay float 0x08b3abd8; used by owner 7)
Sora = Cloud's copy: bit 0x1 with spec row 1 (+9 = 1) -> x2.0 at full HP, x1.5 at half, ~x1.0 near KO, and his KH2
multi-hit swings have small powers -> EX barely felt. This sets bit 0x400 in owner 33's chrp row only (0x803 -> 0xC03):
EX Bravery = x1.5 more on top (x3.0 at full HP, x1.5 near KO). The spec row (shared with Cloud) is untouched.

  python3 -I spot33_exdamage.py ISO [--dry]          re-runnable (accepts 0x803 or 0xC03, else stops)
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True

OWNER = 33
FLAT_EX = 0x400
EXPECT = 0x803                      # Cloud's 0x801 + spot33_exguard's stance bit 0x2


def system_part(sysbin):
    from spot33_save import arc_join, arc_split
    head, chs = arc_split(sysbin)
    chrp = next(c for c in chs if c[1] == b'chrp')
    c = bytearray(chrp[2])
    _, nrows = struct.unpack_from('<II', c, 0)
    at = next(8 + r * 144 for r in range(nrows) if c[8 + r * 144] == OWNER)
    bits, = struct.unpack_from('<I', c, at + 0xC)
    assert bits & ~FLAT_EX == EXPECT, 'chrp %d +0x0C = 0x%x (expected 0x%x or 0x%x) - stop' % (
        OWNER, bits, EXPECT, EXPECT | FLAT_EX)
    if bits & FLAT_EX:
        print('chrp %d +0x0C = 0x%x: EX x1.5 already on' % (OWNER, bits))
        return sysbin
    struct.pack_into('<I', c, at + 0xC, bits | FLAT_EX)
    print('chrp %d +0x0C 0x%x -> 0x%x (EX Mode Bravery damage x1.5 on top of Ultima Weapon)' % (OWNER, bits,
                                                                                            bits | FLAT_EX))
    chrp[2] = bytes(c)
    return arc_join(head, chs)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    iso, dry = sys.argv[1], '--dry' in sys.argv[2:]
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    import mpk
    from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, mpk_member, package_entry, read_at
    from pkg_put import PACKAGE_INFO_ISO_SECTOR
    with open(iso, 'rb') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        pkg = PACKAGE_ISO_SECTOR * SECTOR
        off, size = package_entry(info, 'general_archive/main/main.bin')
        main_bin = read_at(f, pkg + off, size)
        so, ss = mpk_member(f, pkg + off, 'system.bin')
    sysbin = main_bin[so - pkg - off:so - pkg - off + ss]
    new = system_part(sysbin)
    if new == sysbin or dry:
        print('system.bin: %s' % ('no change' if new == sysbin else 'would change (--dry: nothing written)'))
        return
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'main.bin')
        open(p, 'wb').write(mpk.replace(main_bin, 'system.bin', new))
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso,
                            'general_archive/main/main.bin', p], check=True, capture_output=True, text=True)
        print(r.stdout.strip())


if __name__ == '__main__':
    main()
