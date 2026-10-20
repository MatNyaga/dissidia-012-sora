"""New KH2 music tracks (Mat: Tension Rising, Working Together, Sinister Shadows), every existing track kept.
notes/music.md has the formats. Assets = Codex delivery codex/inbox/20261016-kh2-music/encoded/*.AT3 (sha256-guarded).

What it changes (all appends; vanilla rows/strings/records/files stay byte-identical):
  ISO9660   PSP_GAME/USRDIR/DATA/BGM/KH2TR.AT3, KH2WT.AT3, KH2SS.AT3 (Codex KH2_xx.AT3): data appended at the ISO end, directory
            records inserted in sorted order into the existing 4-sector BGM directory (re-packed, records never cross a
            sector; stops if they don't fit), PVD volume size updated. The game opens DISC0:/PSP_GAME/USRDIR/DATA/BGM/<name>.
            The AT3 fmt chunk is rewritten into the native 52-byte Sony layout (codec config word for 2048-B frames);
            fact/smpl/data stay Codex's bytes (smpl samplerData = 24 like the native files).
  main.bin  bgm_entry.bin: rows for BGM ids 131/132/133 (text ids 132/133/134), volume 100, no unlock flags, stage
            mask 0; AUTO (default): owner mask bit 33 = picked automatically when Sora is the opponent (the game's
            "opponent series" music), flags 3, weight TR 32 / WT 16 / SS 16 (>= 92.8 % KH2 vs Sora on any stage). MUSIC_AUTO=0: flags 1, weight 1, masks 0
            (= test319). Rows already written in the other form are rewritten in place (re-runnable both ways).
  main_lang bgm_name.bin (EN): text ids 132..134 = "KHII - <title>" (count 132 -> 135, offsets shifted, same XOR).
  collection_param.bin section 6 (Museum > Music): records (id, 0xFFFF always unlocked, seconds, 0xFFFF).

  python3 -I spot33_music.py ISO [--dry] [--tracks N] [--rollback]
    --tracks N   only the first N tracks (order TR, WT, SS; default 3). Re-running with a larger N adds the rest.
    --rollback   remove every KH2 row/name/record/directory record again; the appended audio is cut off the ISO end
                 when it is the last thing on the disc (then the ISO is byte-identical to before the first run).
Re-runnable: prints "already" for everything that is in place. Never writes dumps/ULUS10566.iso.
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
from voice_text import KEY  # noqa: E402

ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
ASSETS = os.path.join(ROOT, 'codex', 'inbox', '20261016-kh2-music', 'encoded')
# (disc/table file name, sha256 of Codex's file, BGM id, text id, name, volume, Codex file name)
# Disc names are 9 characters (Codex's KH2_xx.AT3 = 10): three 10-char records (58 B each) do not fit the 4-sector
# BGM directory after re-packing, 9-char ones (56 B) do (sector use 2038/2046/2020/2002). More tracks later = the
# directory must be relocated (parent record + both path tables), see notes/music.md.
TRACKS = [
    ('KH2TR.AT3', '8593526111d8a7eb663780f6f7fec8ab0cd055874470102115392f6ae61d239b', 131, 132,
     'KHII - Tension Rising', 100, 'KH2_TR.AT3'),
    ('KH2WT.AT3', 'd1d13c455d25b1833c1a573cac51c8f5442bcb7cd4ee80fed9863ed0a1e7fa65', 132, 133,
     'KHII - Working Together', 100, 'KH2_WT.AT3'),
    ('KH2SS.AT3', '8a2088c72aba5b041dcb972331a004e431e5fb8eb507aa653b8511336054b763', 133, 134,
     'KHII - Sinister Shadows', 100, 'KH2_SS.AT3'),
]
MUSEUM_EXTRA = 10          # Museum plays to the loop end + 10 s (one loop seam audible), like vanilla ~= file length

MAIN, LANG, PARAM = 'general_archive/main/main.bin', 'general_archive/main/EN/main_lang.bin', 'collection_param.bin'
VAN = dict(bent='a48cef089eff3233477fd4690140239d1bc0829d146e120406b713006b64c58e',      # clean dump = test316
           names='b4189d9f7a8c44abcaef98cdc4cb7b73f75269a763d8d807ab08ec4d85282ba2',
           museum='90daf3de5fbcbcafefd93215f073aaa73f3ca91a407dd62850841aad0ae282c6')
VAN_ROWS, VAN_NAMES, VAN_MUSEUM = 131, 132, 127
BGM_DIR = ['PSP_GAME', 'USRDIR', 'DATA', 'BGM']
BGM_DIR_SIZE, BGM_DIR_FILES = 8192, 134
DONOR = b'INSTALL_OK.AT3'                      # record template (date, flags, XA system use)
# native B01_01.AT3 fmt chunk (52 B): 0xFFFE, 2 ch, 44100, 12059 B/s, block 560, cb 34, ..., GUID, 01 00 28 45 00*8
NATIVE_FMT = bytes.fromhex('feff020044ac00001b2f0000300200002200080003000000bfaa23e958cb7144a119fffa01e4ce62'
                           '010028450000000000000000')
AT3P_GUID = bytes.fromhex('bfaa23e958cb7144a119fffa01e4ce62')


# ---------- AT3 ----------
def chunks(raw):
    assert raw[:4] == b'RIFF' and raw[8:12] == b'WAVE'
    out, off = [], 12
    while off + 8 <= len(raw):
        tag, size = raw[off:off + 4], struct.unpack_from('<I', raw, off + 4)[0]
        out.append((tag, raw[off + 8:off + 8 + size]))
        off += 8 + size + (size & 1)
    assert off == len(raw), 'trailing bytes in RIFF'
    return out


def prepare(t):
    name, sha = t[6], t[1]
    raw = open(os.path.join(ASSETS, name), 'rb').read()
    assert hashlib.sha256(raw).hexdigest() == sha, '%s changed (sha256)' % name
    ch = dict(chunks(raw))
    assert [t for t, _ in chunks(raw)] == [b'fmt ', b'fact', b'smpl', b'data'], [t for t, _ in chunks(raw)]
    fmt, fact, smpl, data = ch[b'fmt '], ch[b'fact'], ch[b'smpl'], ch[b'data']
    tag, nch, rate, _, block = struct.unpack_from('<HHIIH', fmt, 0)
    assert (tag, nch, rate) == (0xFFFE, 2, 44100) and fmt[24:40] == AT3P_GUID, (tag, nch, rate)
    assert block % 8 == 0 and 8 <= block <= 8192 and len(data) % block == 0, block
    nf = bytearray(NATIVE_FMT)
    struct.pack_into('<IH', nf, 8, block * 44100 // 2048, block)
    cfg = block // 8 - 1
    nf[42:44] = bytes([0x28 | (cfg >> 8), cfg & 0xFF])         # stereo + frame size (native: 560 -> 28 45)
    end_sample, delay = struct.unpack('<II', fact)
    assert struct.unpack_from('<I', smpl, 28)[0] == 1 and len(smpl) == 60
    ns = bytearray(smpl)
    struct.pack_into('<I', ns, 32, 24)                           # samplerData 24 like Sony's files
    loop_start, loop_end = struct.unpack_from('<II', ns, 44)
    assert delay <= loop_start < loop_end <= end_sample + delay, (loop_start, loop_end, end_sample, delay)
    body = b'WAVE'
    for t, d in ((b'fmt ', bytes(nf)), (b'fact', fact), (b'smpl', bytes(ns)), (b'data', data)):
        body += t + struct.pack('<I', len(d)) + d + b'\0' * (len(d) & 1)
    out = b'RIFF' + struct.pack('<I', len(body)) + body
    assert dict(chunks(out))[b'data'] == data
    seconds = int((loop_end - delay) / 44100 + 0.5) + MUSEUM_EXTRA
    info = dict(kbps=block * 8 * 44100 / 2048 / 1000, intro=(loop_start - delay) / 44100,
                loop_end=(loop_end - delay) / 44100, total=end_sample / 44100, seconds=seconds)
    return out, info


# ---------- ISO9660 ----------
def set_both32(buf, at, v):
    struct.pack_into('<I', buf, at, v)
    struct.pack_into('>I', buf, at + 4, v)


def rec_name(r):
    return bytes(r[33:33 + r[32]])


def read_dir(f, sector, size):
    raw = read_at(f, sector * SECTOR, size)
    recs = []
    for s in range(0, size, SECTOR):
        o = s
        while o < s + SECTOR and raw[o]:
            recs.append(bytes(raw[o:o + raw[o]]))
            o += raw[o]
        assert not any(raw[o:s + SECTOR]), 'junk after the last record in a directory sector'
    return recs


def pack_dir(recs, size):
    out, cur = bytearray(), bytearray()
    for r in recs:
        if len(cur) + len(r) > SECTOR:
            out += cur + b'\0' * (SECTOR - len(cur))
            cur = bytearray()
        cur += r
    out += cur + b'\0' * (SECTOR - len(cur))
    return bytes(out) if len(out) <= size else None


def find_dir(f, path):
    pvd = read_at(f, 16 * SECTOR, SECTOR)
    assert pvd[1:6] == b'CD001' and pvd[0] == 1
    rec = pvd[156:156 + 34]
    for part in path:
        sec, size = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
        rec = next((r for r in read_dir(f, sec, size) if rec_name(r) == part.encode() and r[25] & 2), None)
        assert rec, 'directory %s not found' % part
    return struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]


def new_record(donor, name, sector, size):
    nl = len(name)
    head = 33 + nl + (33 + nl) % 2                     # pad byte so the system-use field starts even
    su = donor[33 + donor[32] + (33 + donor[32]) % 2:]
    r = bytearray(head + len(su))
    r[1:33] = donor[1:33]
    r[0], r[32] = len(r), nl
    set_both32(r, 2, sector)
    set_both32(r, 10, size)
    r[33:33 + nl] = name
    r[head:] = su
    return bytes(r)


# ---------- tables ----------
# Auto music (Mat: "code that chooses OST based off the environment or the opponent"): battle start FUN_0888b544 picks a
# weighted-random row whose OWNER mask (+16, 64 bits, bit = fighter owner id: Cloud 13, Lightning 31, ...) has the
# opponent's (setup block 2 byte 0) bit, or whose stage-code mask (+24) has the stage's bit (mode 5 also the player's
# owner). No vanilla row has owner bit 33 -> vs Sora the game only had stage-bound rows. AUTO rows: owner bit 33 (+20
# bit 1), flags 3 (both flag pools, mode 7 picks by bit0/bit1), weight TR 32 / WT 16 / SS 16 (2:1:1, Tension Rising =
# main theme). The weight byte is read SIGNED (lb / (char)) -> max 127; sum is an int (no overflow). Vanilla stage-tied
# weight per stage <= 5 (stage bits 0-9/14-18; Order's Sanctuary bit 11 = 4) -> KH2 share >= 64/69 = 92.8 % vs Sora on
# any stage; worst mixed pool (mode 5: stage 5 + the other fighter's 8) 64/77 = 83 %. Max qualifying rows 8+3 < cap 32.
# test320 used 2/1/1 (Claude runtime: KH2 2 of 8 on Order's Sanctuary) -> those rows are accepted and rewritten.
# MUSIC_AUTO=0 env = the test319 rows (flags 1, weight 1, masks 0).
AUTO_WEIGHT = {'KH2TR.AT3': 32, 'KH2WT.AT3': 16, 'KH2SS.AT3': 16}
OLD_AUTO_WEIGHTS = [{'KH2TR.AT3': 2, 'KH2WT.AT3': 1, 'KH2SS.AT3': 1}]     # test320
SORA_OWNER = 33
# UNLOCK (2026-10-17, Mat: "buy BGM from the PP Catalog ... add the Kingdom Hearts 2 music there"): each KH2 row's
# first unlock-flag slot (+4) and its Museum record flag = the PP Catalog item's flag (spot33_catalog.py BGM items,
# 240 PP like the 012 tracks). Until bought: not in the Quick Battle/Creation BGM pickers, not in the Museum list,
# and the auto pick vs Sora only sees stage rows (stage music). MUSIC_UNLOCK=0 env = always available (old rows).
UNLOCK_FLAGS = {'KH2TR.AT3': 1249, 'KH2WT.AT3': 1250, 'KH2SS.AT3': 1251}


def unlock_on():
    return os.environ.get('MUSIC_UNLOCK', '1') != '0'


def track_flag(t, unlock=None):
    return UNLOCK_FLAGS[t[0]] if (unlock_on() if unlock is None else unlock) else -1


def bent_row(t, auto=None, weights=None, unlock=None):
    weights = weights or AUTO_WEIGHT
    assert all(0 < w <= 127 for w in weights.values())
    if auto is None:
        auto = os.environ.get('MUSIC_AUTO', '1') != '0'
    name, _, bid, tid, _, vol = t[:6]
    fl = track_flag(t, unlock)
    if auto:
        own = 1 << SORA_OWNER
        r = struct.pack('<HH4hBbBBIII', bid, tid, fl, -1, -1, -1, 3, vol, weights[name], 0,
                        own & 0xFFFFFFFF, own >> 32, 0)
    else:
        r = struct.pack('<HH4hBbBBIII', bid, tid, fl, -1, -1, -1, 1, vol, 1, 0, 0, 0, 0)
    return r + name.encode().ljust(16, b'\0')


def names_decode(b):
    n, = struct.unpack_from('<H', b, 0)
    offs = struct.unpack_from('<%dH' % n, b, 2)
    out = []
    for k in range(n):                       # text id k = position k+1
        if offs[k] == 0:
            out.append(None)
            continue
        p = offs[k] * 2
        ln, = struct.unpack_from('<H', b, p)
        out.append(bytes(c ^ KEY[(2 * (k + 1) + 18 + j) % 32] for j, c in enumerate(b[p + 2:p + 2 + ln])))
    return out


def names_encode(raws):
    n = len(raws)
    head = bytearray(2 + 2 * n)
    struct.pack_into('<H', head, 0, n)
    body = bytearray()
    for k, raw in enumerate(raws):
        if raw is None:
            continue
        struct.pack_into('<H', head, 2 + 2 * k, (len(head) + len(body)) // 2)
        body += struct.pack('<H', len(raw)) + bytes(c ^ KEY[(2 * (k + 1) + 18 + j) % 32] for j, c in enumerate(raw))
        body += b'\0' * (len(body) & 1)
    return bytes(head + body)


def enc_name(t):
    return (t[4] + '\0').encode('utf-16-le')


def sha(b):
    return hashlib.sha256(b).hexdigest()


def patch_bent(b, want):
    """want = list of our rows that must follow the vanilla rows"""
    assert b[:4] == b'BENT', b[:4]
    n, = struct.unpack_from('<I', b, 8)
    assert len(b) == 16 + 44 * n
    van = bytearray(b[:16 + 44 * VAN_ROWS])
    struct.pack_into('<I', van, 8, VAN_ROWS)
    assert n >= VAN_ROWS and sha(bytes(van)) == VAN['bent'], 'bgm_entry vanilla rows differ (not the clean table)'
    have = [b[16 + 44 * i:16 + 44 * (i + 1)] for i in range(VAN_ROWS, n)]
    assert all(h in [bent_row(t, a, w, u) for a in (True, False) for w in [None] + OLD_AUTO_WEIGHTS
                     for u in (True, False)]
               for h, t in zip(have, TRACKS)) and \
        len(have) <= len(TRACKS), 'bgm_entry has extra rows that are not ours'
    ids = {struct.unpack_from('<H', b, 16 + 44 * i)[0] for i in range(VAN_ROWS)}
    assert not ids & {t[2] for t in TRACKS}, 'BGM id clash'
    out = bytearray(bytes(van) + b''.join(want))
    struct.pack_into('<I', out, 8, VAN_ROWS + len(want))
    return bytes(out), len(have)


def patch_names(b, want):
    raws = names_decode(b)
    assert names_encode(raws) == b, 'bgm_name does not re-encode exactly'
    assert len(raws) >= VAN_NAMES and sha(names_encode(raws[:VAN_NAMES])) == VAN['names'], 'bgm_name vanilla differs'
    have = raws[VAN_NAMES:]
    ours = [enc_name(t) for t in TRACKS]
    assert have == ours[:len(have)], 'bgm_name has extra entries that are not ours'
    assert [t[3] for t in TRACKS] == list(range(VAN_NAMES, VAN_NAMES + len(TRACKS)))
    out = names_encode(raws[:VAN_NAMES] + want)
    chk = names_decode(out)
    assert chk[:VAN_NAMES] == raws[:VAN_NAMES] and chk[VAN_NAMES:] == want
    return out, len(have)


def patch_museum(d, want):
    h = list(struct.unpack_from('<20H', d, 0))
    assert h[0] == 2 and h[1] == 9, h[:2]
    o6 = 40 + sum(h[11:17])
    n, size = h[8], h[17]
    assert size == 8 * n and n >= VAN_MUSEUM and sha(d[o6:o6 + 8 * VAN_MUSEUM]) == VAN['museum'], 'Museum list differs'
    have = [d[o6 + 8 * i:o6 + 8 * i + 8] for i in range(VAN_MUSEUM, n)]
    assert [r[:2] for r in have] == [struct.pack('<H', t[2]) for t in TRACKS][:len(have)], 'Museum extra not ours'
    assert all(struct.unpack_from('<H', r, 2)[0] in (0xFFFF, UNLOCK_FLAGS[t[0]]) for r, t in zip(have, TRACKS))
    h[8], h[17] = VAN_MUSEUM + len(want), 8 * (VAN_MUSEUM + len(want))
    out = struct.pack('<20H', *h) + d[40:o6 + 8 * VAN_MUSEUM] + b''.join(want) + d[o6 + size:]
    # every other section and the string block unchanged
    assert out[o6 + 8 * (VAN_MUSEUM + len(want)):] == d[o6 + size:] and out[40:o6] == d[40:o6]
    return out, len(have)


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


def mpk_swap(arcb, member, new):
    out = mpk.replace(arcb, member, new)
    old = {n: arcb[o:o + s] for n, o, s in mpk.entries(arcb)}
    got = {n: out[o:o + s] for n, o, s in mpk.entries(out)}
    assert list(old) == list(got) and got[member] == new
    assert all(got[k] == v for k, v in old.items() if k != member)
    return out


def tables(iso, sel, dry):
    """sel = tracks to have (prefix of TRACKS)"""
    infos = {t[0]: prepare(t)[1] for t in sel}
    mainb = get(iso, MAIN)
    m = {n: mainb[o:o + s] for n, o, s in mpk.entries(mainb)}
    nb, had = patch_bent(m['bgm_entry.bin'], [bent_row(t) for t in sel])
    print('bgm_entry.bin: rows %d -> %d (ids %s), auto music vs owner %d: %s' % (
        VAN_ROWS + had, VAN_ROWS + len(sel), [t[2] for t in sel], SORA_OWNER,
        'ON (flags 3, weights %s)' % [AUTO_WEIGHT[t[0]] for t in sel] if os.environ.get('MUSIC_AUTO', '1') != '0'
        else 'off'))
    langb = get(iso, LANG)
    lm = {n: langb[o:o + s] for n, o, s in mpk.entries(langb)}
    nn, hadn = patch_names(lm['bgm_name.bin'], [enc_name(t) for t in sel])
    print('bgm_name.bin: names %d -> %d (text ids %s: %s)' % (VAN_NAMES + hadn, VAN_NAMES + len(sel),
                                                            [t[3] for t in sel], [t[4] for t in sel]))
    pd = get(iso, PARAM)
    recs = [struct.pack('<4H', t[2], track_flag(t) & 0xFFFF, infos[t[0]]['seconds'], 0xFFFF) for t in sel]
    print('unlock: %s' % ('PP Catalog flags %s' % [UNLOCK_FLAGS[t[0]] for t in sel] if unlock_on() else 'always'))
    npd, hadm = patch_museum(pd, recs)
    print('collection_param section 6: records %d -> %d (seconds %s)' % (
        VAN_MUSEUM + hadm, VAN_MUSEUM + len(sel), [infos[t[0]]['seconds'] for t in sel]))
    for path, old, new in ((MAIN, mainb, mpk_swap(mainb, 'bgm_entry.bin', nb) if nb != m['bgm_entry.bin'] else mainb),
                           (LANG, langb, mpk_swap(langb, 'bgm_name.bin', nn) if nn != lm['bgm_name.bin'] else langb),
                           (PARAM, pd, npd)):
        if new == old:
            print('  %s: already' % path)
        elif not dry:
            put_file(iso, path, new)
        else:
            print('  %s: %d -> %d bytes (dry)' % (path, len(old), len(new)))
    return infos


def iso_files(iso, sel, dry, rollback=False):
    with open(iso, 'rb') as f:
        dsec, dsize = find_dir(f, BGM_DIR)
        assert dsize == BGM_DIR_SIZE, dsize
        recs = read_dir(f, dsec, dsize)
        f.seek(0, 2)
        iso_end = f.tell()
        vol, = struct.unpack_from('<I', read_at(f, 16 * SECTOR + 80, 4))
        assert vol * SECTOR == iso_end, 'PVD volume size != ISO size'
        names = [rec_name(r) for r in recs]
        assert names[:2] == [b'\0', b'\1']
        ours = {t[0].encode(): t for t in TRACKS}
        nvan = len([n for n in names[2:] if n not in ours])
        assert nvan == BGM_DIR_FILES, nvan
        donor = recs[names.index(DONOR)]
        present = {}
        for r in recs:
            n = rec_name(r)
            if n in ours:
                present[n] = (struct.unpack_from('<I', r, 2)[0], struct.unpack_from('<I', r, 10)[0])
    if rollback:
        keep = [r for r in recs if rec_name(r) not in ours]
        data = pack_dir(keep, dsize)
        print('BGM directory: removing %s' % sorted(n.decode() for n in present))
        cut = None
        if present:
            lo = min(s for s, _ in present.values()) * SECTOR
            hi = max(s * SECTOR + -(-z // SECTOR) * SECTOR for s, z in present.values())
            span = sum(-(-z // SECTOR) * SECTOR for _, z in present.values())
            if hi == iso_end and hi - lo == span:
                cut = lo
        if not dry:
            with open(iso, 'r+b') as f:
                f.seek(dsec * SECTOR)
                f.write(data)
                if cut is not None:
                    f.truncate(cut)
                    pv = bytearray(read_at(f, 16 * SECTOR + 80, 8))
                    set_both32(pv, 0, cut // SECTOR)
                    f.seek(16 * SECTOR + 80)
                    f.write(pv)
        print('  audio %s' % ('cut off the ISO end (%d -> %d bytes)' % (iso_end, cut) if cut is not None
                              else 'left as unused bytes (not at the ISO end)'))
        return
    add = []
    for t in sel:
        blob, info = prepare(t)
        n = t[0].encode()
        if n in present:
            s, z = present[n]
            with open(iso, 'rb') as f:
                assert z == len(blob) and read_at(f, s * SECTOR, z) == blob, '%s on disc differs' % t[0]
            print('%s: already on disc (sector %d, %d B)' % (t[0], s, z))
            continue
        add.append((n, blob, info))
    if not add:
        return
    end = -(-iso_end // SECTOR) * SECTOR
    newrecs, pos = list(recs), end
    for n, blob, info in add:
        r = new_record(donor, n, pos // SECTOR, len(blob))
        i = next(i for i in range(2, len(newrecs) + 1) if i == len(newrecs) or rec_name(newrecs[i]) > n)
        newrecs.insert(i, r)
        print('%s: %d B (%.1f kbps, intro %.2f s, loop end %.2f s, file %.2f s) -> sector %d, record after %s' % (
            n.decode(), len(blob), info['kbps'], info['intro'], info['loop_end'], info['total'], pos // SECTOR,
            rec_name(newrecs[i - 1]).decode()))
        pos += -(-len(blob) // SECTOR) * SECTOR
    data = pack_dir(newrecs, dsize)
    assert data is not None, 'BGM directory full (4 sectors) - would need relocation'
    assert read_dir_bytes(data) == newrecs
    print('BGM directory: %d -> %d records, sector use %s; ISO %d -> %d bytes' % (
        len(recs), len(newrecs), sector_use(data), iso_end, pos))
    if dry:
        return
    with open(iso, 'r+b') as f:
        f.seek(iso_end)
        f.write(b'\0' * (end - iso_end))
        for n, blob, info in add:
            f.write(blob + b'\0' * ((-len(blob)) % SECTOR))
        assert f.tell() == pos
        f.seek(dsec * SECTOR)
        f.write(data)
        pv = bytearray(8)
        set_both32(pv, 0, pos // SECTOR)
        f.seek(16 * SECTOR + 80)
        f.write(pv)


def read_dir_bytes(data):
    recs = []
    for s in range(0, len(data), SECTOR):
        o = s
        while o < s + SECTOR and data[o]:
            recs.append(bytes(data[o:o + data[o]]))
            o += data[o]
    return recs


def sector_use(data):
    use = []
    for s in range(0, len(data), SECTOR):
        o = s
        while o < s + SECTOR and data[o]:
            o += data[o]
        use.append(o - s)
    return use


def rollback_tables(iso, dry):
    mainb = get(iso, MAIN)
    m = {n: mainb[o:o + s] for n, o, s in mpk.entries(mainb)}
    nb, had = patch_bent(m['bgm_entry.bin'], [])
    langb = get(iso, LANG)
    lm = {n: langb[o:o + s] for n, o, s in mpk.entries(langb)}
    nn, hadn = patch_names(lm['bgm_name.bin'], [])
    pd = get(iso, PARAM)
    npd, hadm = patch_museum(pd, [])
    print('rollback: bgm_entry -%d rows, bgm_name -%d, Museum -%d records' % (had, hadn, hadm))
    if dry:
        return
    if had:
        put_file(iso, MAIN, mpk_swap(mainb, 'bgm_entry.bin', nb))
    if hadn:
        put_file(iso, LANG, mpk_swap(langb, 'bgm_name.bin', nn))
    if hadm:
        put_file(iso, PARAM, npd)


def main():
    args = sys.argv[1:]
    iso = [a for a in args if not a.startswith('--') and not a.isdigit()][0]
    dry, rollback = '--dry' in args, '--rollback' in args
    n = int(args[args.index('--tracks') + 1]) if '--tracks' in args else len(TRACKS)
    assert 1 <= n <= len(TRACKS)
    assert os.path.basename(iso) != 'ULUS10566.iso', 'never write the clean dump'
    if rollback:
        rollback_tables(iso, dry)
        iso_files(iso, [], dry, rollback=True)
    else:
        sel = TRACKS[:n]
        tables(iso, sel, dry)
        iso_files(iso, sel, dry)
    print('dry run, nothing written' if dry else 'done')


if __name__ == '__main__':
    main()
