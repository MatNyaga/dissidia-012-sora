"""RR-08 (2026-10-18): move the mod's PP Catalog unlock flags to bits a vanilla game never sets (notes/unlocks.md §7).

Problem (runtime, coordinator, test348 on a copy of a vanilla-made 100 % save): flags 1250, 1251, 1253, 1254 were
already set, so 2 of the 3 KHII tracks and both KH icon items counted as bought before paying.
Cause (static, clean dump): menu overlay FUN_08a2b07c (called from menu FUN_089e1a64 and FUN_089e3db8)
  - highest level of owners 1..32 (not 23) > 29 / 49 / 69  -> sets flags 1250 / 1251 / 1252 (word 39 bits 2/3/4);
  - table 0x08A2E8AC (owner, level, flag): owners 8, 10, 24..31 at level 100 -> flags 1253..1262.
  system.bin "infp" rows then turn 1250..1255/1257..1261 into the info flags 1301..1312. So every save that got a
  fighter to Lv30 "owned" KHII Working Together, Lv50 Sinister Shadows, and owners 8/10 at Lv100 the icon items.
  (1249 is not set by vanilla, but it sits in the same block; all five move together.)
New flags 1263..1267: the 8-bit gap 1263..1270 between those level flags and the icon flags 1271..1284. Evidence:
  clear on the 100 % save; FUN_08a2b07c's masks/table stop at 1262 (guarded byte-identical below); no catalog item,
  unlock row, collection_param flag (sections 0/6/8), Jukebox row, uicn row, infp/tuto row, bgm_entry row, party
  battle (pbtl) row, EBOOT comflag table or ori/addiu-from-zero code immediate uses them (checked on every run);
  the only constant-offset writes of flag word 39 in EBOOT/battle/menu code are FUN_08a2b07c's (decompiler scan).

  TR 1249 -> 1263, WT 1250 -> 1264, SS 1251 -> 1265, "[KINGDOM HEARTS II] Set of 3" 1253 -> 1266,
  "[Avatar] Sora" 1254 -> 1267

Places (each one: ours with the old numbers -> rewritten, ours with the new numbers -> "already", anything else -> stop):
  update_list_param.bin  our 2 icon items (tab 3 end) + 3 BGM items (tab 4 end), field "flag set when bought"
  main.bin/system.bin    uicn rows 413..416 unlock flag (+4) (ICONS_FREE builds: flag 1 -> left alone)
  main.bin/bgm_entry.bin rows 131..133 first unlock slot (+4) (MUSIC_UNLOCK=0 builds: -1 -> left alone)
  collection_param.bin   section 6 Museum music records 127..129 flag (+2)
spot33_catalog/museum/music already write the new numbers; this step migrates discs built before (test327..test348)
and re-checks the evidence. Same sizes, in place; nothing else changes.

Saves: a save that BOUGHT an item on a test327..348 build keeps the old bit, so after this fix that item shows as not
bought again (dev saves only; never released). Old bits 1250..1254 are vanilla's own and stay as the game set them.

  python3 -I spot33_unlockflags.py ISO [--dry] [--rollback]
Refuses the clean dump and an ISO PPSSPP has open; --dry writes nothing; --rollback puts the old numbers back.
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
import mpk  # noqa: E402
from comb_patch import SECTOR, pkg_offset, read_at, use_iso  # noqa: E402
from spot33_save import arc_split  # noqa: E402

NEW = {'TR': 1263, 'WT': 1264, 'SS': 1265, 'KH': 1266, 'AV': 1267}
OLD = {'TR': 1249, 'WT': 1250, 'SS': 1251, 'KH': 1253, 'AV': 1254}
PARAM, CPARAM, CVP, MAIN = ('update_list_param.bin', 'collection_param.bin', 'collection_voice_param.bin',
                            'general_archive/main/main.bin')
PBTL = ('party_battle-pbtl.bin',)          # the prologus_* names in the code are not on this disc
# our catalog items without the flag field (index 6): (cost, name text, help, ?, vis1, vis2) + (new .. arg2), key
ITEMS = [((150, 169, 107, -1, -1, -1), (-1, -1, -1, -1, -1, -1), 'KH'),
         ((150, 170, 109, -1, -1, -1), (-1, -1, -1, -1, -1, -1), 'AV'),
         ((240, 111, 33, -1, -1, -1), (-1, -1, 7, 132, 7, 132), 'TR'),
         ((240, 111, 33, -1, -1, -1), (-1, -1, 7, 133, 7, 133), 'WT'),
         ((240, 111, 33, -1, -1, -1), (-1, -1, 7, 134, 7, 134), 'SS')]
VAN_TABS = (117, 44, 31, 93, 41)
VAN_ICONS, ICON_ROWS = 413, [(413, 414, 'KH', 2993), (414, 415, 'KH', 2994), (415, 416, 'KH', 2995),
                             (416, 417, 'AV', 2996)]
VAN_BGM_ROWS, BGM_ROWS = 131, [(131, 132, 'TR'), (132, 133, 'WT'), (133, 134, 'SS')]
VAN_MUSEUM = 127
# vanilla level-flag setter (menu overlay): function + its (owner, level, flag) table, clean bytes
MENU_SECTOR, MENU_VADDR, MENU_FILEOFF = 185056, 0x089DD4C0, 0x54
LEVEL_FUNC = (0x08A2B07C, 0x08A2B190, 'd7449b093b5d24d5')
LEVEL_TABLE = (0x08A2E8AC, 0x08A2E930, '8ae2e5b4c8f2021e')
EBOOT_SECTOR, UNLOCK_VA = 560, 0x089D7BE0
COMFLAG_VA = (0x089CDB18, 0x089CDB28)
CODE_FILES = {'EBOOT': (560, 4640948), 'OVL_BATTLE_APP': (185824, 1596824), 'OVL_MENU_APP': (185056, 1556096)}


def eboot_off(va):
    return EBOOT_SECTOR * SECTOR + 0x1018 + va - 0x8804040


def menu_off(va):
    return MENU_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def get(iso, path):
    use_iso(iso)
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        return read_at(f, st, sz)


def put_file(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'x.bin')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('   ', r.stdout.strip())


def i16(v):
    return v - 0x10000 if v >= 0x8000 else v


# ---------------------------------------------------------------- the four places
def catalog(d, src, dst):
    """-> (new bytes, [(name, from, to)]); our items are the last 2 of tab 3 and the last 3 of tab 4"""
    head = struct.unpack_from('<8h', d, 0)
    cnt = list(head[1:6])
    assert head[0] == 4 and head[6] == 32 and head[7] == -1, head
    n = sum(cnt)
    assert len(d) == 16 + 28 * n + 32 * 64, len(d)
    assert cnt[0] in (VAN_TABS[0], VAN_TABS[0] + 1) and cnt[1:3] == list(VAN_TABS[1:3]), cnt   # +1 = Encounter Voice
    if cnt[3:] == list(VAN_TABS[3:]):
        return d, []                                 # spot33_catalog not applied: nothing of ours here
    assert cnt[3:] == [VAN_TABS[3] + 2, VAN_TABS[4] + 3], 'catalog tabs 3/4 = %s - not ours' % cnt[3:]
    t3 = sum(cnt[:4]) - 2
    t4 = n - 3
    pos = [t3, t3 + 1, t4, t4 + 1, t4 + 2]
    out, log = bytearray(d), []
    for p, (pre, post, key) in zip(pos, ITEMS):
        it = struct.unpack_from('<I12h', d, 16 + 28 * p)
        assert it[:6] == pre and it[7:] == post and it[6] in (src[key], dst[key]), \
            'catalog item %d = %s is not our %s item - stop' % (p, it, key)
        log.append(('catalog %s item #%d' % (key, p), it[6], dst[key]))
        struct.pack_into('<h', out, 16 + 28 * p + 4 + 2 * 5, dst[key])     # u32 cost + 5 x s16, then the flag
        assert struct.unpack_from('<I12h', out, 16 + 28 * p) == pre + (dst[key],) + post
    return bytes(out), log


def main_bin(m, src, dst):
    """system.bin uicn rows 413..416 + bgm_entry rows 131..133, in place inside main.bin"""
    out, log = bytearray(m), []
    ents = {n: (o, s) for n, o, s in mpk.entries(m)}
    so, ss = ents['system.bin']
    sysb = m[so:so + ss]
    count, = struct.unpack_from('<I', sysb, 4)
    for i in range(count):
        one, tag, off, size = struct.unpack_from('<I4sII', sysb, 16 + 16 * i)
        if tag == b'uicn':
            break
    else:
        raise AssertionError('system.bin has no uicn chunk')
    u = sysb[off:off + size]
    one_, n = struct.unpack_from('<HH', u, 0)
    assert one_ == 1 and len(u) == 4 + 8 * n and n in (VAN_ICONS, VAN_ICONS + len(ICON_ROWS)), (one_, n, len(u))
    if n > VAN_ICONS:
        for idx, no, key, viewed in ICON_ROWS:
            r = struct.unpack_from('<4H', u, 4 + 8 * idx)
            assert r[0] == idx and r[1] == no and r[3] == viewed and r[2] in (src[key], dst[key], 1), \
                'uicn row %d = %s is not ours - stop' % (idx, r)
            if r[2] == 1:
                log.append(('uicn row %d (ICONS_FREE: owned from the start)' % idx, 1, 1))
                continue
            log.append(('uicn row %d (icon %d)' % (idx, no), r[2], dst[key]))
            struct.pack_into('<H', out, so + off + 4 + 8 * idx + 4, dst[key])
    bo, bs = ents['bgm_entry.bin']
    b = m[bo:bo + bs]
    assert b[:4] == b'BENT', b[:4]
    nb, = struct.unpack_from('<I', b, 8)
    assert len(b) == 16 + 44 * nb and VAN_BGM_ROWS <= nb <= VAN_BGM_ROWS + len(BGM_ROWS), nb
    for k in range(nb - VAN_BGM_ROWS):
        bid, tid, key = BGM_ROWS[k]
        r = struct.unpack_from('<HH4h', b, 16 + 44 * (VAN_BGM_ROWS + k))
        assert r[:2] == (bid, tid) and r[3:] == (-1, -1, -1) and r[2] in (src[key], dst[key], -1), \
            'bgm_entry row %d = %s is not ours - stop' % (VAN_BGM_ROWS + k, r)
        if r[2] == -1:
            log.append(('bgm_entry row %d (MUSIC_UNLOCK=0: always)' % (VAN_BGM_ROWS + k), -1, -1))
            continue
        log.append(('bgm_entry row %d (bgm %d)' % (VAN_BGM_ROWS + k, bid), r[2], dst[key]))
        struct.pack_into('<h', out, bo + 16 + 44 * (VAN_BGM_ROWS + k) + 4, dst[key])
    return bytes(out), log


def sections(cp):
    h = struct.unpack_from('<20H', cp, 0)
    assert h[0] == 2 and h[1] == 9, h[:2]
    offs = [40]
    for sz in h[11:20]:
        offs.append(offs[-1] + sz)
    return h, offs


def museum(cp, src, dst):
    h, offs = sections(cp)
    n = h[8]
    assert h[17] == 8 * n and VAN_MUSEUM <= n <= VAN_MUSEUM + len(BGM_ROWS), (n, h[17])
    out, log = bytearray(cp), []
    for k in range(n - VAN_MUSEUM):
        bid, _, key = BGM_ROWS[k]
        o = offs[6] + 8 * (VAN_MUSEUM + k)
        r = struct.unpack_from('<4H', cp, o)
        assert r[0] == bid and r[3] == 0xFFFF and i16(r[1]) in (src[key], dst[key], -1), \
            'Museum music record %d = %s is not ours - stop' % (VAN_MUSEUM + k, r)
        if i16(r[1]) == -1:
            log.append(('Museum music record %d (always)' % (VAN_MUSEUM + k), -1, -1))
            continue
        log.append(('Museum music record %d (bgm %d)' % (VAN_MUSEUM + k, bid), r[1], dst[key]))
        struct.pack_into('<H', out, o + 2, dst[key])
    return bytes(out), log


# ---------------------------------------------------------------- evidence: nobody else uses the target flags
def users(iso, flags, files):
    """places other than our own rows that use any of FLAGS (empty list = free)"""
    fl, hits = set(flags), []
    d = files[PARAM]
    cnt = struct.unpack_from('<5h', d, 2)
    n = sum(cnt)
    ours = set()
    if list(cnt[3:]) == [VAN_TABS[3] + 2, VAN_TABS[4] + 3]:
        t3 = sum(cnt[:4]) - 2
        ours = {t3, t3 + 1, n - 3, n - 2, n - 1}
    for i in range(n):
        it = struct.unpack_from('<I12h', d, 16 + 28 * i)
        if i not in ours and fl & set(it[4:8]):
            hits.append('catalog item %d %s' % (i, it))
    with open(iso, 'rb') as f:
        for i in range(40):                                        # EBOOT unlock table
            f.seek(eboot_off(UNLOCK_VA + 20 * i))
            r = struct.unpack('<5i', f.read(20))
            if r[0] == -1:
                break
            if fl & set(r[1:]):
                hits.append('unlock row %d %s' % (i, r))
        for t in COMFLAG_VA:              # "comflag" lists (FUN_08901d48): (key, -> 8 x s16 flags) pairs, key <= 0 ends
            for k in range(32):
                f.seek(eboot_off(t + 8 * k))
                c, p = struct.unpack('<iI', f.read(8))
                if c <= 0:
                    break
                f.seek(eboot_off(p))
                hits += ['comflag table 0x%08X %d' % (t, v) for v in struct.unpack('<8h', f.read(16)) if v in fl]
        for name, (a, b, want) in (('FUN_08a2b07c', LEVEL_FUNC), ('level table 0x08A2E8AC', LEVEL_TABLE)):
            f.seek(menu_off(a))
            got = hashlib.sha256(f.read(b - a)).hexdigest()[:16]
            if got != want:
                hits.append('%s is not the clean code/table (%s) - cannot vouch for flags 1263..1267' % (name, got))
        for name, (sec, size) in CODE_FILES.items():               # ori/addiu rX, zero, FLAG
            f.seek(sec * SECTOR)
            code = f.read(size)
            ws = struct.unpack('<%dI' % (len(code) // 4), code[:len(code) // 4 * 4])
            hits += ['%s +0x%X immediate %d' % (name, 4 * k, w & 0xFFFF) for k, w in enumerate(ws)
                     if (w >> 26) in (0x09, 0x0D) and ((w >> 21) & 31) == 0 and (w & 0xFFFF) in fl]
    cp = files[CPARAM]
    h, offs = sections(cp)
    for i in range(h[2]):                                          # section 0: unlock / viewed
        if fl & set(struct.unpack_from('<2H', cp, offs[0] + 48 * i + 8)):
            hits.append('Museum record %d' % i)
    for i in range(min(h[8], VAN_MUSEUM)):                         # section 6 (vanilla music records)
        if struct.unpack_from('<H', cp, offs[6] + 8 * i + 2)[0] in fl:
            hits.append('Museum music record %d' % i)
    for i in range(h[10]):                                         # section 8: Jukebox characters
        if struct.unpack_from('<H', cp, offs[8] + 4 * i)[0] in fl:
            hits.append('Jukebox character %d' % i)
    v = files[CVP]                      # Jukebox: u16 1, u16 groups, 8-B group heads, then 44-B rows (+2 flag)
    one, ng = struct.unpack_from('<HH', v, 0)
    assert one == 1, one
    o = 4 + 8 * ng
    for g in range(ng):
        owner, rows, nbytes, _m = struct.unpack_from('<HHHh', v, 4 + 8 * g)
        assert nbytes == 44 * rows, (owner, rows, nbytes)
        for r in range(rows):
            if struct.unpack_from('<H', v, o + 44 * r + 2)[0] in fl:
                hits.append('Jukebox group %d row %d' % (owner, r))
        o += nbytes
    assert o == len(v), (o, len(v))
    m = files[MAIN]
    ents = {n_: (o_, s_) for n_, o_, s_ in mpk.entries(m)}
    so, ss = ents['system.bin']
    _, chunks = arc_split(m[so:so + ss])
    ch = {c[1]: c[2] for c in chunks}
    u = ch[b'uicn']
    for i in range(min(struct.unpack_from('<H', u, 2)[0], VAN_ICONS)):
        if fl & set(struct.unpack_from('<2H', u, 4 + 8 * i + 4)):
            hits.append('uicn row %d' % i)
    ip = ch[b'infp']                                               # u16 2, u16 n, (kind, if-flag, set-flag, -1)
    for i in range(struct.unpack_from('<H', ip, 2)[0]):
        if fl & set(struct.unpack_from('<3h', ip, 4 + 8 * i)[1:]):
            hits.append('infp row %d' % i)
    tu = ch[b'tuto']                                               # 'TUTO', n @8, 16-B rows, flag +6
    for i in range(struct.unpack_from('<I', tu, 8)[0]):
        if struct.unpack_from('<h', tu, 16 + 16 * i + 6)[0] in fl:
            hits.append('tuto row %d' % i)
    bo, bs = ents['bgm_entry.bin']
    for i in range(VAN_BGM_ROWS):
        if fl & set(struct.unpack_from('<4h', m, bo + 16 + 44 * i + 4)):
            hits.append('bgm_entry row %d' % i)
    for p in PBTL:                                                 # party battles: +2..+8 prerequisite / win / lose
        d = files[p]
        for i in range(struct.unpack_from('<h', d, 8)[0]):
            if fl & set(struct.unpack_from('<4h', d, 0x14 + 200 * i + 2)):
                hits.append('%s row %d' % (p, i))
    return hits


# ---------------------------------------------------------------- main
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
    with open(iso, 'rb') as f:
        f.seek(EBOOT_SECTOR * SECTOR)
        assert f.read(4) == b'\x7fELF', 'EBOOT is not the plain ELF (run eboot_plain first)'
    src, dst = (NEW, OLD) if rollback else (OLD, NEW)
    files = {p: get(iso, p) for p in (PARAM, CPARAM, CVP, MAIN) + PBTL}
    if not rollback:
        hits = users(iso, sorted(NEW.values()), files)
        assert not hits, 'flags %s are used elsewhere - stop: %s' % (sorted(NEW.values()), hits)
        print('flags %s free: no other catalog item / unlock row / comflag / Museum section 0,6,8 / Jukebox row / '
              'uicn / infp / tuto / bgm_entry / pbtl row / code immediate; vanilla level setter FUN_08a2b07c + '
              'table clean (stops at 1262)' % sorted(NEW.values()))
    new_files, total = {}, 0
    for path, fn, data in ((PARAM, catalog, files[PARAM]), (MAIN, main_bin, files[MAIN]),
                           (CPARAM, museum, files[CPARAM])):
        nd, log = fn(data, src, dst)
        assert len(nd) == len(data)
        for what, a, b in log:
            print('  %-48s %5d -> %5d%s' % (what, i16(a), b, ' already' if i16(a) == b else ''))
        if not log:
            print('  %s: none of our rows (step not applied yet) - nothing to do' % path)
        if nd != data:
            new_files[path] = nd
            total += sum(1 for _, a, b in log if i16(a) != b)
    print('%s: %d flag fields to change (%s)' % ('rollback' if rollback else 'migrate', total,
                                                 ', '.join(new_files) or 'already'))
    if dry:
        print('dry run, nothing written')
        return
    for path, nd in new_files.items():
        put_file(iso, path, nd)
    for path, nd in new_files.items():
        assert get(iso, path) == nd, '%s read-back differs' % path
    print('done')


if __name__ == '__main__':
    main()
