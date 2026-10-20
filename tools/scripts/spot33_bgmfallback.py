"""Labyrinth battles vs Sora get music while the KH2 tracks are still locked (RR-08 "mode 7", 2026-10-19, static).

Why (EBOOT FUN_0888b544 = battle-start BGM pick, a0 = battle obj, mode = *(u32*)(a0+0x4C), result *(s32*)(a0+0x804),
-1 = no BGM; notes/release-rr-static-b.md RR-08, notes/music.md section 7):
  Mode 7 = Labyrinth (runtime 2026-10-18). Without a scenario record it calls battle-overlay FUN_08ade42c ->
  FUN_08ade8a0 -> FUN_08adeeb4: pool = unlocked bgm_entry rows with the OPPONENT's owner bit (byte 0x09AFC900) AND
  the mode-7 flag bit (+0x0C bit 0/1 by DAT_09AFE05A & 1) - no stage rows. With a scenario record it calls
  FUN_08ade3cc (forced id, else FUN_08ade79c/FUN_08aded20 = owner byte record+2, same rule). Sora's (owner 33) only
  rows are the KH2 tracks 131-133, locked until bought (flags 1263/1264/1265, spot33_unlockflags) -> empty pool ->
  -1 -> a silent battle whenever the Labyrinth opponent is Sora (e.g. the "Face yourself" mirror piece with Sora as
  the player) and the tracks are not bought.

Fix (EBOOT only, in place, no cave, no new callee; strictly vanilla for every other opponent):
  case 7 (0x0888B61C, 22 words) is re-encoded with the same two pickers and the same arguments, then
  `+0x804 = v0; a1 = (opponent owner byte ^ 33) + v0` -> a1 < 0 only when the opponent is owner 33 AND the pick was -1;
  then s2 = 0 and it joins the mode-0/4 path at 0x0888B5B0 (FUN_08889924 stage code -> FUN_08ade458(sp, owner 33,
  stage, NULL) -> FUN_08ade9a4 = owner-33 rows OR stage rows) = the stage's music, exactly what Quick Battle vs CPU
  Sora gets. Once a KH2 track is bought the mode-7 pool is non-empty again and Sora gets his own music (no fallback).
  The 4-word tail lives in case 0xC's words (0x0888B6A4); jump-table entry 12 (0x089CA530) now points at
  0x0888B608, which is the identical 4-instruction "+0x804 = *(s16*)0x09AFDE4E" body of cases 1/2/3/0xB.
  Other opponents (incl. vanilla -1 cases such as Chaos/Feral Chaos pools) are untouched byte-for-byte in effect.

  case 7 new:   addiu s1,s1,0x1060 (s1 = 0x09AFC900) ; lhu a2,0x175A(s1) ; lh a1,0xF3C(s1) ; andi s2,a2,1 ;
                bne a1,a0(-1),SCEN ; _or a2,s2 ; lb a1,0(s1) ; jal 0x08ade42c ; _or a0,sp ; b CHECK ; nop ;
          SCEN: jal 0x088bbd8c ; _or a0,a1 ; or a0,sp ; or a1,v0 ; jal 0x08ade3cc ; _or a2,s2 ;
         CHECK: sw v0,0x804(s0) ; lbu a1,0(s1) ; xori a1,a1,33 ; b TAIL ; _addu a1,a1,v0
  TAIL 0x0888B6A4: bgez a1,0x0888b6c4 (epilogue) ; _ori s2,zero,0 ; b 0x0888b5b0 ; nop

Guards: plain ELF; FUN_0888B544..0x0888B6DC is the clean EBOOT (sha prefix, also = dumps/extracted/EBOOT.elf) outside
our words, and our words are clean or ours; jump table 0x089CA500 (15 entries) clean except entry 12 = clean or ours;
the three battle-overlay callees still start with their clean words; bgm_entry has the owner-33 rows (info only);
refuses the clean dump and an ISO PPSSPP has open. --dry writes nothing, --rollback restores the clean words.
Re-runnable ("already").

  python3 -I spot33_bgmfallback.py ISO [--dry] [--rollback]
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
BATTLE_ISO = 185824 * 0x800                       # OVL_BATTLE_APP.ELF (same sector as spot33_reflect / jukebox)
FUNC = (0x0888B544, 0x0888B6DC)
CLEAN_FUNC_SHA = '4fcb0cae03e7dd61'               # sha256[:16] of the clean EBOOT bytes [FUNC)
CASE7_VA, CASE7_N = 0x0888B61C, 22
CASE7_CLEAN = [0x00803025, 0x26241060, 0x26252790, 0x94B1002A, 0x84850F3C, 0x14A60007, 0x32310001, 0x80850000,
               0x03A02025, 0x0E2B790B, 0x02203025, 0x10000008, 0xAE020804, 0x0E22EF63, 0x00A02025, 0x03A02025,
               0x00402825, 0x0E2B78F3, 0x02203025, 0xAE020804, 0x10000015, 0x00000000]
TAIL_VA, TAIL_N = 0x0888B6A4, 4
TAIL_CLEAN = [0x262425A8, 0x84840006, 0x10000005, 0xAE040804]
JT_VA, JT_N, JT_ENTRY = 0x089CA500, 15, 12
JT_CLEAN = [0x0888B590, 0x0888B5D8, 0x0888B5D8, 0x0888B5D8, 0x0888B590, 0x0888B674, 0x0888B590, 0x0888B61C,
            0x0888B590, 0x0888B6B4, 0x0888B590, 0x0888B5D8, 0x0888B6A4, 0x0888B590, 0x0888B590]
JT_OURS = 0x0888B608                              # case 1/2/3/0xB no-scenario body (same 4 instructions as case 0xC)
SAME_BODY = [0x262425A8, 0x84840006, 0xAE040804, 0x1000002B]   # 0x0888B608..: addiu, lh, sw, b 0x0888b6c4
CASE7 = [
    'addiu s1,s1,0x1060',          # s1 = 0x09AFC900 (opponent setup block, byte 0 = owner)
    'lhu a2,0x175a(s1)',           # DAT_09AFE05A
    'lh a1,0xf3c(s1)',             # DAT_09AFD83C scenario index
    'andi s2,a2,0x1',
    'bne a1,a0,SCEN',              # a0 = -1 since 0x0888B554
    'or a2,s2,zero',
    'lb a1,0x0(s1)',
    'jal 0x08ade42c',
    'or a0,sp,zero',
    'b CHECK',
    'nop',
    'SCEN:',
    'jal 0x088bbd8c',
    'or a0,a1,zero',
    'or a0,sp,zero',
    'or a1,v0,zero',
    'jal 0x08ade3cc',
    'or a2,s2,zero',
    'CHECK:',
    'sw v0,0x804(s0)',
    'lbu a1,0x0(s1)',
    'xori a1,a1,0x21',
    'b 0x%08x' % TAIL_VA,
    'addu a1,a1,v0',
]
TAIL = ['bgez a1,0x0888b6c4', 'ori s2,zero,0x0', 'b 0x0888b5b0', 'nop']
CALLEES = {0x08ADE42C: 0x27BDFFF0, 0x08ADE3CC: 0x27BDFFE0, 0x08ADE458: 0x27BDFFE0, 0x08ADE9A4: None}


def off(va):
    return EBOOT_ISO + 0x1018 + va - 0x8804040


def words(f, va, n):
    f.seek(off(va))
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
    case7, tail = asm(CASE7, CASE7_VA), asm(TAIL, TAIL_VA)
    assert len(case7) == CASE7_N and len(tail) == TAIL_N, (len(case7), len(tail))
    with open(iso, 'rb') as f:
        f.seek(EBOOT_ISO)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF (run eboot_plain first)'
        f.seek(off(FUNC[0]))
        body = bytearray(f.read(FUNC[1] - FUNC[0]))
        cur7, curt = words(f, CASE7_VA, CASE7_N), words(f, TAIL_VA, TAIL_N)
        jt = words(f, JT_VA, JT_N)
        same = words(f, JT_OURS, 4)
        for va, first in CALLEES.items():
            f.seek(BATTLE_ISO + va - 0x089DD4C0 + 0x54)
            w, = struct.unpack('<I', f.read(4))
            assert first is None or w == first, 'battle overlay %08x starts %08x, expected %08x - stop' % (va, w, first)
    st7 = 'ours' if cur7 == case7 else 'vanilla' if cur7 == CASE7_CLEAN else None
    stt = 'ours' if curt == tail else 'vanilla' if curt == TAIL_CLEAN else None
    assert st7 and stt, 'case-7 / tail words are neither vanilla nor ours - stop:\n %s\n %s' % (
        ' '.join('%08x' % w for w in cur7), ' '.join('%08x' % w for w in curt))
    assert jt[:JT_ENTRY] + jt[JT_ENTRY + 1:] == JT_CLEAN[:JT_ENTRY] + JT_CLEAN[JT_ENTRY + 1:], \
        'BGM-mode jump table differs from the clean EBOOT - stop: %s' % ' '.join('%08x' % w for w in jt)
    stj = 'ours' if jt[JT_ENTRY] == JT_OURS else 'vanilla' if jt[JT_ENTRY] == JT_CLEAN[JT_ENTRY] else None
    assert stj, 'jump-table entry 12 = %08x - stop' % jt[JT_ENTRY]
    assert same == SAME_BODY, 'case 1 no-scenario body at %08x changed - stop' % JT_OURS
    for va, n, clean in ((CASE7_VA, CASE7_N, CASE7_CLEAN), (TAIL_VA, TAIL_N, TAIL_CLEAN)):
        k = va - FUNC[0]
        body[k:k + 4 * n] = struct.pack('<%dI' % n, *clean)
    got = hashlib.sha256(bytes(body)).hexdigest()[:16]
    assert got == CLEAN_FUNC_SHA, 'FUN_0888b544 differs from the clean EBOOT outside our words (%s) - stop' % got
    states = {st7, stt, stj}
    assert len(states) == 1, 'half-applied: case7 %s, tail %s, jump table %s - stop (rollback first)' % (st7, stt, stj)
    state = states.pop()
    want = 'vanilla' if rollback else 'ours'
    print('EBOOT FUN_0888b544 mode 7 (Labyrinth) vs owner 33 with an empty pool -> stage-music fallback: %s -> %s%s' % (
        state, want, ' already' if state == want else (' (dry)' if dry else '')))
    if state == want or dry:
        print('dry run, nothing written' if dry else 'nothing to do')
        return
    plan = [(CASE7_VA, CASE7_CLEAN if rollback else case7), (TAIL_VA, TAIL_CLEAN if rollback else tail),
            (JT_VA + 4 * JT_ENTRY, [JT_CLEAN[JT_ENTRY] if rollback else JT_OURS])]
    with open(iso, 'r+b') as f:
        for va, ws in plan:
            f.seek(off(va))
            f.write(struct.pack('<%dI' % len(ws), *ws))
    with open(iso, 'rb') as f:
        for va, ws in plan:
            assert words(f, va, len(ws)) == ws
    print('done: %d EBOOT words (0x%08X x%d, 0x%08X x%d, jump table 0x%08X)' % (
        CASE7_N + TAIL_N + 1, CASE7_VA, CASE7_N, TAIL_VA, TAIL_N, JT_VA + 4 * JT_ENTRY))


if __name__ == '__main__':
    main()
