"""Assist picker: Sora listed only once even with the Aerith DLC installed (RR-14, 2026-10-18, static).

Why (EBOOT, static; notes/release-rr-static-b.md RR-14):
  FUN_088d5ac8(list, max, keep_chaos, assist_list) builds the fighter list from the unlock table 0x089D7BE0. With
  assist_list != 0 (only caller: menu FUN_08af4374 = assist picker) it then APPENDS owner 33 (0x21, costume bits
  2|4|8 = 0xE, not NEW) when FUN_0885c304(DAT_089d4e14) != 0. That byte (0x08BAEBB4) is set by FUN_0885c01c when the
  PSN "Aerith" DLC key file dlc_aerith.txt verifies: in vanilla this is how DLC Aerith (assist-only owner 33) got
  into the picker. Since test20 the unlock table row 22 is owner 33 (Sora, flag 925), so with the DLC installed
  and Sora bought the picker lists owner 33 TWICE (two identical Sora assist entries).

Fix (17 words in place, 0x088D5C70..0x088D5CB0; no cave, no new calls): the append now first scans the entries
already written and skips when owner 33 is there. DLC-only (Sora not bought) still gets the one appended entry
(legacy entitlement: the DLC's owner-33 assist slot is now Sora; decision recorded in notes). Without the DLC
nothing changes at all (the DLC branch is never reached).

  new code (t0/t1/a0-a2 are caller-saved; after 0x088D5CB4 only s3 is used):
    lw t0,144(sp) ; sll a1,s3,3 ; addu a0,t0,a1 ; ori a2,zero,0x21
  L: beq t0,a0,APP ; nop ; lw t1,0(t0) ; bne t1,a2,L ; addiu t0,t0,8 ; b END ; nop
  APP: ori a1,zero,0xe ; sw a2,0(a0) ; sh zero,4(a0) ; sh a1,6(a0) ; addiu s3,s3,1 ; nop
  END = 0x088D5CB4 (or v0,s3,zero) unchanged. Same entry bytes as vanilla (owner 33, +4 = 0, +6 = 0xE).

Guards: plain ELF; the whole function 0x088D5AC8..0x088D5CE8 is the clean EBOOT (sha prefix) or clean + exactly
our 17 words; unlock row 22 owner = 33. --dry writes nothing, --rollback restores the vanilla words.

  python3 -I spot33_assistdup.py ISO [--dry] [--rollback]
"""
import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from mips_asm import asm  # noqa: E402

EBOOT_ISO = 560 * 0x800
FUNC = (0x088D5AC8, 0x088D5CE8)
CLEAN_FUNC_SHA = '532893fe49e3294b'   # sha256[:16] of clean EBOOT bytes [FUNC) (checked against dumps/extracted)
START, END = 0x088D5C70, 0x088D5CB4
VANILLA = [0x8FA40090, 0x001328C0, 0x00852021, 0xA4800006, 0x94850006, 0x34060021, 0x34A50002, 0xA4850006,
           0x94850006, 0xAC860000, 0xA4800004, 0x34A50004, 0xA4850006, 0x94850006, 0x26730001, 0x34A50008,
           0xA4850006]
CODE = [
    'lw t0,144(sp)',
    '.word 0x001328c0',          # sll a1,s3,3 (the original word)
    'addu a0,t0,a1',
    'ori a2,zero,0x21',
    'L:',
    'beq t0,a0,APP',
    'nop',
    'lw t1,0(t0)',
    'bne t1,a2,L',
    'addiu t0,t0,8',
    'b 0x088d5cb4',
    'nop',
    'APP:',
    'ori a1,zero,0xe',
    'sw a2,0(a0)',
    'sh zero,4(a0)',
    'sh a1,6(a0)',
    'addiu s3,s3,1',
    'nop',
]
TABLE_VA, ROW = 0x089D7BE0, 22


def off(va):
    return EBOOT_ISO + 0x1018 + va - 0x8804040


def words(f, a, n):
    f.seek(off(a))
    return list(struct.unpack('<%dI' % n, f.read(4 * n)))


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    assert len(args) == 1, __doc__
    iso = args[0]
    dry, rollback = '--dry' in sys.argv, '--rollback' in sys.argv
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    if not dry:
        r = subprocess.run(['pgrep', '-a', '-x', 'PPSSPPSDL'], capture_output=True, text=True)
        assert os.path.abspath(iso) not in r.stdout and os.path.basename(iso) not in r.stdout, \
            'PPSSPP has this ISO open - stop'
    new = asm(CODE, START)
    assert len(new) == len(VANILLA) == (END - START) // 4, (len(new), len(VANILLA))
    n = (END - START) // 4
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF (run eboot_plain first)'
        f.seek(off(FUNC[0]))
        body = bytearray(f.read(FUNC[1] - FUNC[0]))
        cur = words(f, START, n)
        f.seek(off(TABLE_VA + 20 * ROW))
        row_owner = struct.unpack('<i', f.read(4))[0]
    assert row_owner == 33, 'unlock row %d owner = %d, expected 33 (Sora) - stop' % (ROW, row_owner)
    if cur == new:
        state = 'ours'
    elif cur == VANILLA:
        state = 'vanilla'
    else:
        raise SystemExit('FUN_088d5ac8 append block is neither vanilla nor ours - stop: %s' % ' '.join('%08x' % w for w in cur))
    # rest of the function must be the clean code
    k = START - FUNC[0]
    body[k:k + 4 * n] = struct.pack('<%dI' % n, *VANILLA)
    got = hashlib.sha256(bytes(body)).hexdigest()[:16]
    assert got == CLEAN_FUNC_SHA, 'FUN_088d5ac8 differs from the clean EBOOT outside our block (%s) - stop' % got
    want = VANILLA if rollback else new
    print('EBOOT FUN_088d5ac8 assist-list owner-33 append (DLC Aerith path): %s -> %s%s' % (
        state, 'vanilla' if rollback else 'dedupe', ' already' if cur == want else (' (dry)' if dry else '')))
    if cur == want or dry:
        print('dry run, nothing written' if dry else 'nothing to do')
        return
    with open(iso, 'r+b') as f:
        f.seek(off(START))
        f.write(struct.pack('<%dI' % n, *want))
    with open(iso, 'rb') as f:
        assert words(f, START, n) == want
    print('done: %d EBOOT words at 0x%08X' % (n, START))


if __name__ == '__main__':
    main()
