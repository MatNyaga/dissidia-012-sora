"""Museum Jukebox: the mod's PP-bought rows stay hidden until bought, even on saves with the "show all" flag 1372
(RR-08, 2026-10-19, static; notes/unlocks.md section 7 addendum, notes/release-rr-static-b.md RR-08).

Runtime (coordinator, test349 on a copy of the vanilla-made 100 % save "Googolplexic"): Museum -> Jukebox -> Music
listed "128 KHII - Tension Rising", "129 KHII - Working Together", "130 KHII - Sinister Shadows" with only Sinister
Shadows bought (flag 1265 set, 1263/1264 clear: word ptr+0x9C = 0xff8a7ffc).

Cause (menu overlay, clean code; nothing of ours touches these functions' gates):
  Music list FUN_08a36d1c walks collection_param section 6 (8-B records: u16 BGM id, u16 unlock flag, ...) and lists
  a record when its flag is 0xFFFF or set - OR when FUN_08a41098() is true, = flag 1372 (word ptr+0xA8 bit 28), a
  vanilla "list everything" override. The same override is read by the Jukebox voice character list FUN_08a36ee8
  (section 8, u16 flag +0), the voice-row list FUN_08a37024 (collection_voice_param rows, u16 flag +2) and the Museum
  item lists (FUN_08a30480 -> FUN_08a301b0, not touched here). Records 127..129 = ours (flags 1263..1265) are fine;
  the save has 1372 set, so every record is listed whatever was bought. (No constant writer of 1372 exists in the
  EBOOT/menu/battle decompiles and no catalog/unlock/uicn/infp/tuto/Museum/Jukebox/bgm_entry/pbtl row names it, so
  how that save got it is unknown; on such a save vanilla's own unbought PP rows would show too - a 100 % save simply
  has them all.) Old builds (test327..348, flags 1249..1251) leaked the same way: the override ignores record flags.

Fix (OVL_MENU_APP, 3 x 15 words in place, no cave, no new callee): in each of the three list builders the gate
block is re-encoded so the override no longer applies to the mod's own purchase flags; every other row behaves
exactly as before (override on -> listed; override off -> own flag).
  old: lhu a1,FLAG(v0); beq a1,FFFF,L1; _or a0,1; lw a0,0x726c(BASE); srl a2,a1,5; sll a2,a2,2; addu a0,a0,a2;
       lw a0,0(a0); andi a1,a1,31; sllv a1,1,a1; and a0,a0,a1; sltu a0,zero,a0;
       L1: beq OVR,zero,+2; nop; or a0,1
  new: (same up to the word load) sllv a2,1,a1 (sllv only uses the low 5 bits, so no andi; a1 keeps the flag);
       and a0,a0,a2; sltu a0,zero,a0;
       L1: addiu a2,a1,-LO; sltiu a2,a2,N (a2 = flag is ours); sltu a2,a2,OVR (= override and not ours);
       movn a0,1,a2
  FUN_08a36d1c music records: LO 1263, N 8 (the mod's reserved flag block 1263..1270, spot33_unlockflags)
  FUN_08a36ee8 voice characters: LO 925, N 1 (Sora's entry = his unlock flag; only section-8 row with 925)
  FUN_08a37024 voice rows: LO 888, N 1 ("Encounter Voice - Sora", spot33_jukebox; group 33 Encounter/vs rows)
Not touched: the DLC-row tail of the music list (bgm_entry +12 bit 2; our rows are 3 = battle pools only), Jukebox
completion FUN_08a3c9c8 / Museum completion (they never read the override), Player Icons (uicn +4 flag, no override).

Guards: each builder [function) with our block and spot33_jukebox's list-size words normalised to vanilla must hash
to the clean overlay; FUN_08a41098 must be the clean 7 words; the three blocks must all be vanilla or all ours
(half-applied -> stop); refuses the clean dump and an ISO PPSSPP has open. Info: section-6 records >= 127 flags,
Sora's section-8 flag, group-33 Encounter flag. --dry writes nothing, --rollback restores the vanilla words.
Re-runnable ("already").

  python3 -I spot33_jukeboxgate.py ISO [--dry] [--rollback]
"""
import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.dont_write_bytecode = True
from mips_asm import asm  # noqa: E402
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
import spot33_unlockflags as UF  # noqa: E402
import spot33_jukebox as JB  # noqa: E402

SECTOR = 0x800
MUSIC_LO, MUSIC_N = UF.NEW['TR'], 8              # 1263..1270 = the mod's reserved flag block
CHAR_LO, VOICE_LO = JB.SORA_UNLOCK, JB.EV_FLAG   # 925, 888
VAN_MUSEUM = UF.VAN_MUSEUM                        # 127 vanilla music records
OVERRIDE = (0x08A41098, [0x3C04089D, 0x8C84726C, 0x3C051000, 0x8C8400A8, 0x00851024, 0x03E00008, 0x0002102B])
# (name, function [lo, hi), clean sha256[:16] of the function with jukebox words vanilla, block va,
#  vanilla block words, flag offset, base reg, one reg, ffff reg, override reg, LO, N)
SITES = [
    ('FUN_08a36d1c Museum music list', (0x08A36D1C, 0x08A36EE8), 'bad1107a24752516', 0x08A36DB0,
     [0x94450002, 0x10B5000A, 0x02602025, 0x8E84726C, 0x00053142, 0x00063080, 0x00862021, 0x8C840000,
      0x30A5001F, 0x00B32804, 0x00852024, 0x0004202B, 0x13C00002, 0x00000000, 0x02602025],
     2, 's4', 's3', 's5', 'fp', MUSIC_LO, MUSIC_N),
    ('FUN_08a36ee8 Jukebox voice characters', (0x08A36EE8, 0x08A37024), '8334fa17e9e312da', 0x08A36F7C,
     [0x94450000, 0x10B5000A, 0x02E02025, 0x8EC4726C, 0x00053142, 0x00063080, 0x00862021, 0x8C840000,
      0x30A5001F, 0x00B72804, 0x00852024, 0x0004202B, 0x12600002, 0x00000000, 0x02E02025],
     0, 's6', 's7', 's5', 's3', CHAR_LO, 1),
    ('FUN_08a37024 Jukebox voice rows', (0x08A37024, 0x08A37180), '8f481e8b14149a9b', 0x08A370D8,
     [0x94450002, 0x10B5000A, 0x02602025, 0x8E84726C, 0x00053142, 0x00063080, 0x00862021, 0x8C840000,
      0x30A5001F, 0x00B32804, 0x00852024, 0x0004202B, 0x12E00002, 0x00000000, 0x02602025],
     2, 's4', 's3', 's5', 's7', VOICE_LO, 1),
]
N_WORDS = 15


def block(off, base, one, ff, ovr, lo, n, va):
    return asm(['lhu a1,%d(v0)' % off,
                'beq a1,%s,L1' % ff,
                'or a0,%s,zero' % one,
                'lw a0,0x726c(%s)' % base,
                'srl a2,a1,5',
                'sll a2,a2,2',
                'addu a0,a0,a2',
                'lw a0,0x0(a0)',
                'sllv a2,%s,a1' % one,
                'and a0,a0,a2',
                'sltu a0,zero,a0',
                'L1:',
                'addiu a2,a1,%d' % -lo,
                'sltiu a2,a2,%d' % n,
                'sltu a2,a2,%s' % ovr,
                'movn a0,%s,a2' % one], va)


def menu_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def words(f, va, n):
    f.seek(menu_off(va))
    return list(struct.unpack('<%dI' % n, f.read(4 * n)))


def info(iso):
    """data facts the gates rely on (printed; a mismatch is reported, not fatal)"""
    out = []
    cp = UF.get(iso, UF.CPARAM)
    h, offs = UF.sections(cp)
    recs = [struct.unpack_from('<4H', cp, offs[6] + 8 * i) for i in range(h[8])]
    van_in = [i for i, r in enumerate(recs[:VAN_MUSEUM]) if MUSIC_LO <= r[1] < MUSIC_LO + MUSIC_N]
    if van_in:
        out.append('WARNING vanilla music records %s use flags in %d..%d' % (van_in, MUSIC_LO, MUSIC_LO + MUSIC_N - 1))
    out.append('music records >= %d: %s' % (VAN_MUSEUM, ', '.join(
        '%d id %d flag %s' % (i, r[0], 'always' if r[1] == 0xFFFF else r[1]) for i, r in enumerate(recs)
        if i >= VAN_MUSEUM) or 'none'))
    s8 = [struct.unpack_from('<HBB', cp, offs[8] + 4 * i) for i in range(h[10])]
    c925 = [(fl, ow) for fl, ow, _ in s8 if fl == CHAR_LO]
    out.append('Jukebox characters with flag %d: %s' % (CHAR_LO, c925 or 'none'))
    v = UF.get(iso, UF.CVP)
    _one, ng = struct.unpack_from('<HH', v, 0)
    o, n888 = 4 + 8 * ng, {}
    for g in range(ng):
        owner, rows, nb, _m = struct.unpack_from('<HHHh', v, 4 + 8 * g)
        k = sum(1 for r in range(rows) if struct.unpack_from('<H', v, o + 44 * r + 2)[0] == VOICE_LO)
        if k:
            n888[owner] = k
        o += nb
    out.append('Jukebox voice rows with flag %d: %s' % (VOICE_LO, n888 or 'none'))
    return out


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
    jb = {va: (van, ours) for va, van, ours, _w in JB.MENU_SITES}
    states, plan = [], []
    with open(iso, 'rb') as f:
        assert words(f, OVERRIDE[0], len(OVERRIDE[1])) == OVERRIDE[1], 'FUN_08a41098 (flag 1372 test) changed - stop'
        for name, (lo, hi), want_sha, va, van, off, base, one, ff, ovr, flo, fn in SITES:
            ours = block(off, base, one, ff, ovr, flo, fn, va)
            assert len(ours) == N_WORDS == len(van), (name, len(ours))
            f.seek(menu_off(lo))
            body = bytearray(f.read(hi - lo))
            cur = list(struct.unpack_from('<%dI' % N_WORDS, body, va - lo))
            st = 'ours' if cur == ours else 'vanilla' if cur == van else None
            assert st, '%s gate block is neither vanilla nor ours - stop:\n %s' % (name, ' '.join('%08x' % w for w in cur))
            struct.pack_into('<%dI' % N_WORDS, body, va - lo, *van)
            for jva, (jvan, jours) in jb.items():
                if lo <= jva < hi:
                    w, = struct.unpack_from('<I', body, jva - lo)
                    assert w in (jvan, jours), '%s: spot33_jukebox word 0x%08X = %08x - stop' % (name, jva, w)
                    struct.pack_into('<I', body, jva - lo, jvan)
            got = hashlib.sha256(bytes(body)).hexdigest()[:16]
            assert got == want_sha, '%s differs from the clean overlay outside the known words (%s) - stop' % (name, got)
            states.append(st)
            plan.append((name, va, van if rollback else ours, flo, fn))
            print('%s 0x%08X: %s (override skipped for flags %s)' % (
                name, va, st, '%d..%d' % (flo, flo + fn - 1) if fn > 1 else flo))
    assert len(set(states)) == 1, 'half-applied (%s) - stop (rollback first)' % ', '.join(states)
    state, want = states[0], 'vanilla' if rollback else 'ours'
    for line in info(iso):
        print('  ' + line)
    print('OVL_MENU_APP Jukebox gates (flag-1372 override vs mod purchase flags): %s -> %s%s' % (
        state, want, ' already' if state == want else (' (dry)' if dry else '')))
    if state == want or dry:
        print('dry run, nothing written' if dry else 'nothing to do')
        return
    with open(iso, 'r+b') as f:
        for _n, va, ws, _l, _k in plan:
            f.seek(menu_off(va))
            f.write(struct.pack('<%dI' % N_WORDS, *ws))
    with open(iso, 'rb') as f:
        for _n, va, ws, _l, _k in plan:
            assert words(f, va, N_WORDS) == ws
    print('done: %d OVL_MENU_APP words (%s)' % (N_WORDS * len(plan), ', '.join('0x%08X x%d' % (p[1], N_WORDS)
                                                                            for p in plan)))


if __name__ == '__main__':
    main()
