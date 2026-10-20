"""Test-20 step for the clean bootstrap: put the decrypted (plain ELF) EBOOT on the disc + bake in the unlock row.

  python3 -I eboot_plain.py ISO [--dry]

- PSP_GAME/SYSDIR/EBOOT.BIN (sector 560) on the clean disc is encrypted (~PSP, tag D91613F0, 4,641,296 B).
  It is decrypted with tools/pspdecrypt/pspdecrypt (result must be sha256 0bc8e779... = dumps/extracted/EBOOT.elf,
  4,640,948 B), written in place and the directory record size is set to the ELF size (notes/roster.md "Test 20").
  The 348 bytes of the old file after the ELF are left as they are (the same as test 20/test28-lines).
- Unlock table (EBOOT 0x089D7BE0, file 0x1D4BB8, 20-byte rows owner/flag/costume2/costume3/text): row 22 (Chaos,
  owner 23, flag 925) -> owner 33 flag -1 = always unlocked (roster spot #33; Chaos has no QB row in this mod).
Re-runnable: an EBOOT that is already the plain ELF keeps its other patches; only the unlock row is checked/set.
Never run on the clean dump.
"""
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from pkg_add import dir_record, set_both  # noqa: E402

SECTOR = 0x800
EBOOT_SECTOR = 560
ENC_SIZE, ENC_SHA = 4641296, '8fbf3541ab121aff85aae72795760736dfe37706996b2b0f9b81d36fc98f3394'
ELF_SIZE, ELF_SHA = 4640948, '0bc8e779aad2814a3d1bd77346f69ca5e16665845ed053cd0ad44a9cbfaefe6d'
UNLOCK_ROW = 0x1D4BB8 + 22 * 20
CHAOS_ROW, SPOT33_ROW = (23, 925, -1, -1, 3623), (33, -1, -1, -1, 3623)
PSPDECRYPT = os.path.join(HERE, '../pspdecrypt/pspdecrypt')
FALLBACK = os.path.join(HERE, '../../dumps/extracted/EBOOT.elf')


def decrypt(enc):
    with tempfile.TemporaryDirectory() as t:
        src, dst = os.path.join(t, 'EBOOT.BIN'), os.path.join(t, 'EBOOT.elf')
        open(src, 'wb').write(enc)
        if os.access(PSPDECRYPT, os.X_OK):
            subprocess.run([PSPDECRYPT, src, '-o', dst], check=True, capture_output=True)
            elf = open(dst, 'rb').read()
            how = 'tools/pspdecrypt'
        else:
            elf = open(FALLBACK, 'rb').read()
            how = 'dumps/extracted/EBOOT.elf (pspdecrypt not built)'
    assert hashlib.sha256(elf).hexdigest() == ELF_SHA, 'decrypted EBOOT has the wrong sha256 - stop'
    return elf, how


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not args:
        sys.exit(__doc__)
    iso, dry = args[0], '--dry' in sys.argv[1:]
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    with open(iso, 'rb' if dry else 'r+b') as f:
        rec = dir_record(f, b'EBOOT.BIN')
        f.seek(rec + 2)
        sector, = struct.unpack('<I', f.read(4))
        f.seek(rec + 10)
        size, = struct.unpack('<I', f.read(4))
        assert sector == EBOOT_SECTOR, 'EBOOT.BIN not at sector 560 - wrong disc?'
        f.seek(sector * SECTOR)
        cur = f.read(size)
        writes = []
        if cur[:4] == b'\x7fELF':
            assert size == ELF_SIZE, 'plain EBOOT of unexpected size %d - stop' % size
            elf = bytearray(cur)
            print('EBOOT: already the plain ELF (%d B)' % size)
        else:
            assert size == ENC_SIZE and hashlib.sha256(cur).hexdigest() == ENC_SHA, \
                'EBOOT is neither the clean encrypted file nor a plain ELF - stop'
            dec, how = decrypt(cur)
            elf = bytearray(dec)
            writes.append('decrypt')
            print('EBOOT: encrypted %d B -> plain ELF %d B (%s, sha256 %s...)' % (size, len(elf), how, ELF_SHA[:12]))
        row = struct.unpack_from('<5i', elf, UNLOCK_ROW)
        if row[0] == 33 and row[1] in (-1, 925):   # costume flags 1/1 later (spot33_outfits); flag 925 = PP Catalog (spot33_catalog)
            print('unlock row 22: already owner 33, unlock flag %d (costume flags %d/%d)' % row[1:4])
        else:
            assert row == CHAOS_ROW, 'unlock row 22 = %r (expected Chaos %r) - stop' % (row, CHAOS_ROW)
            struct.pack_into('<5i', elf, UNLOCK_ROW, *SPOT33_ROW)
            writes.append('unlock')
            print('unlock row 22: %r -> %r (spot #33 always unlocked)' % (row, SPOT33_ROW))
        if not writes:
            print('EBOOT: no change')
            return
        if dry:
            print('--dry: nothing written')
            return
        f.seek(sector * SECTOR)
        f.write(elf)
        set_both(f, rec + 10, len(elf))
    print('EBOOT written (%s)' % ', '.join(writes))


if __name__ == '__main__':
    main()
