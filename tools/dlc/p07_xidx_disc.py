"""P0.7 runtime-check discs: our extra file index EXTRA.IDX, served through EXTRA.PRX's one-word lookup hook.

Phase-0 throwaway test discs only (never a release base). notes/dlc-phase0.md "P0.7" + "P0.7 runtime check".

Source = the P0.2 disc dumps/ULUS10566-p02-module.iso (test338 + EBOOT loader patch + EXTRA.PRX probe). Changes:
 1) MODULE/EXTRA.PRX replaced by tools/dlc/extra/extra.prx (P0.2 probe + xidx: loads EXTRA.IDX at module_start
    and patches 0x08871420 `jal 0x08871288` -> `jal xidx_tramp` in RAM; diagnostics in g_xidx).
 2) New file /PSP_GAME/USRDIR/DATA/EXTRA.IDX (32-B header "XIDX" v1 + sorted 12-B rows, flag 0 + names blob):
    a) OVERRIDE  menu/JP/story_mode/chara2/p_sev120_1p.gim (Sora's 64x64 VS-screen face; row stays in
       PACKAGE_INFO) -> data of menu/JP/story_mode/chara2/p_gst130_1p.gim (Lightning's face, same size 5,408 B).
       Expect: the VS/loading screen before a battle shows LIGHTNING's face for Sora (both sides in Sora vs Sora).
    b) NEW PATH  menu/JP/battle/chara_image/P_SEV120_1P.gim (Sora's 128x128 battle HUD portrait): its row is
       REMOVED from PACKAGE_INFO.BIN and lives only in EXTRA.IDX (same sector/size). Expect: the HUD portrait
       still shows Sora's KH2 face -> a path the disc index no longer has was served by our index.
    No file data is added (both rows point at data already in PACKAGE.BIN).
 Default OUT dumps/ULUS10566-p07b-xidx.iso (p07b = module with the JIT-safe hook guard; the first p07-* discs are
 never written again).
 --bad (control, OUT dumps/ULUS10566-p07b-badidx.iso): same EXTRA.PRX, EXTRA.IDX with a wrong checksum (sum ^
    0xDEADBEEF) and PACKAGE_INFO left as on p02 -> module refuses the index (g_xidx.state = -6), no hook, game =
    p02 (Sora's own VS face, HUD portrait normal).

  tools/dlc/pspenv.sh make -C tools/dlc/extra
  python3 -I tools/dlc/p07_xidx_disc.py [--dry] [--no-sha] [--bad] [SRC] [OUT]
Guards: OUT must be a new ULUS10566-p07*.iso (never SRC, the clean dump, test338 or a p02 disc); SRC must be a
patched p02 disc (loader + site words checked with p02_module_disc.disc_state) whose PACKAGE_INFO still has both
rows; OUT is created by cp --reflink=auto only when missing, an existing OUT must also pass disc_state; --dry
writes nothing. Re-runnable: rows are always taken from SRC; a second run changes nothing.
"""
import hashlib
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
import p02_module_disc as p02  # noqa: E402
from pkghash import pkg_hash  # noqa: E402

SECTOR = 0x800
INFO_SECTOR, PKG_SECTOR = 26000, 186624
PRX = os.path.join(HERE, 'extra/extra.prx')
OVERRIDE = 'menu/JP/story_mode/chara2/p_sev120_1p.gim'
OVERRIDE_SRC = 'menu/JP/story_mode/chara2/p_gst130_1p.gim'
NEWPATH = 'menu/JP/battle/chara_image/P_SEV120_1P.gim'
DATA_DIR = ['PSP_GAME', 'USRDIR', 'DATA']
IDX_NAME = b'EXTRA.IDX'


def info_rows(f):
    f.seek(INFO_SECTOR * SECTOR)
    head = f.read(16)
    assert head[4:8] == b'pack', head
    n, = struct.unpack_from('<I', head, 8)
    body = f.read(n * 12)
    return head, [struct.unpack_from('<III', body, i * 12) for i in range(n)]


def build_idx(src_rows, bad):
    by = {r[0]: r for r in src_rows}
    ov, ovs, nw = by.get(pkg_hash(OVERRIDE)), by.get(pkg_hash(OVERRIDE_SRC)), by.get(pkg_hash(NEWPATH))
    assert ov and ovs and nw, 'SRC PACKAGE_INFO lacks one of the three rows'
    assert ov[2] & 0x0FFFFFFF == ovs[2] & 0x0FFFFFFF, 'override source size differs'
    rows = sorted([(pkg_hash(OVERRIDE), ovs[1] & 0xFFFFF, ovs[2] & 0x0FFFFFFF, OVERRIDE),
                   (pkg_hash(NEWPATH), nw[1] & 0xFFFFF, nw[2] & 0x0FFFFFFF, NEWPATH)])
    s = sum(h ^ sec ^ size for h, sec, size, _ in rows) & 0xFFFFFFFF
    if bad:
        s ^= 0xDEADBEEF
    out = b'XIDX' + struct.pack('<HHIIIIII', 1, 32, len(rows), 0, PKG_SECTOR, s, 0, 0)
    out += b''.join(struct.pack('<III', h, sec, size) for h, sec, size, _ in rows)
    out += b''.join(p.encode() + b'\0' for *_, p in rows)          # names (tools only; not loaded)
    return out, rows


def plan_put(f, path, name, data):
    """Add or replace file NAME in directory PATH (data appended at the ISO end, or in place if it fits)."""
    dsec, dsize = p02.find_dir(f, path)
    recs = p02.read_dir(f, dsec, dsize)
    f.seek(0, 2)
    iso_end = f.tell()
    vol, = struct.unpack_from('<I', p02.read_at(f, 16 * SECTOR + 80, 4))
    assert vol * SECTOR == iso_end, 'PVD volume size != ISO size'
    names = [p02.rec_name(r) for r in recs]
    cur = next((r for r in recs if p02.rec_name(r) == name), None)
    if cur is not None:
        s, z = struct.unpack_from('<I', cur, 2)[0], struct.unpack_from('<I', cur, 10)[0]
        if z == len(data) and p02.read_at(f, s * SECTOR, z) == data:
            return dict(action='same', sector=s, name=name)
        if -(-len(data) // SECTOR) <= -(-z // SECTOR):
            pos, end = s * SECTOR, iso_end
        else:
            pos = end = -(-iso_end // SECTOR) * SECTOR
        newrecs = [p02.new_record(cur, name, pos // SECTOR, len(data)) if p02.rec_name(r) == name else r for r in recs]
        action = 'replace'
    else:
        donor = next(r for r in recs[2:] if not r[25] & 2)
        pos = end = -(-iso_end // SECTOR) * SECTOR
        r = p02.new_record(donor, name, pos // SECTOR, len(data))
        i = next(i for i in range(2, len(recs) + 1) if i == len(recs) or names[i] > name)
        newrecs = recs[:i] + [r] + recs[i:]
        action = 'add'
    d = p02.pack_dir(newrecs, dsize)
    assert d is not None, 'directory %s full' % '/'.join(path)
    return dict(action=action, name=name, dsec=dsec, dir=d, pos=pos, iso_end=iso_end, end=end, data=data,
                new_end=max(iso_end, pos + -(-len(data) // SECTOR) * SECTOR))


def apply_put(f, p):
    if p['action'] == 'same':
        return
    f.seek(p['iso_end'])
    f.write(b'\0' * (p['end'] - p['iso_end']))
    f.seek(p['pos'])
    f.write(p['data'] + b'\0' * ((-len(p['data'])) % SECTOR))
    f.seek(p['dsec'] * SECTOR)
    f.write(p['dir'])
    pv = bytearray(8)
    p02.set_both32(pv, 0, p['new_end'] // SECTOR)
    f.seek(16 * SECTOR + 80)
    f.write(pv)


def info_record(f):
    dsec, dsize = p02.find_dir(f, DATA_DIR)
    recs = p02.read_dir(f, dsec, dsize)
    off = dsec * SECTOR
    raw = p02.read_at(f, dsec * SECTOR, dsize)
    i = raw.find(bytes([16]) + b'PACKAGE_INFO.BIN')
    assert i > 32 and raw[i - 32] == len(next(r for r in recs if p02.rec_name(r) == b'PACKAGE_INFO.BIN'))
    rec_at = off + i - 32
    sec, size = struct.unpack_from('<I', raw, i - 32 + 2)[0], struct.unpack_from('<I', raw, i - 32 + 10)[0]
    assert sec == INFO_SECTOR, sec
    return rec_at, size


def main():
    dry, nosha, bad = '--dry' in sys.argv, '--no-sha' in sys.argv, '--bad' in sys.argv
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    src = os.path.abspath(args[0] if args else os.path.join(ROOT, 'dumps/ULUS10566-p02-module.iso'))
    out = os.path.abspath(args[1] if len(args) > 1 else os.path.join(
        ROOT, 'dumps/ULUS10566-p07b-badidx.iso' if bad else 'dumps/ULUS10566-p07b-xidx.iso'))
    forbidden = {src, os.path.join(ROOT, 'dumps/ULUS10566.iso'),
                 os.path.join(ROOT, 'dumps/ULUS10566-test338-voicesloud.iso'),
                 os.path.join(ROOT, 'dumps/ULUS10566-p07-xidx.iso'),       # first build (may be open in PPSSPP)
                 os.path.join(ROOT, 'dumps/ULUS10566-p07-badidx.iso')}
    if out in forbidden or not os.path.basename(out).startswith('ULUS10566-p07'):
        sys.exit('refusing to write %s (must be a new ULUS10566-p07*.iso)' % out)
    if not os.path.exists(PRX):
        sys.exit('%s missing: run  tools/dlc/pspenv.sh make -C tools/dlc/extra' % PRX)
    prx = open(PRX, 'rb').read()
    assert prx[:4] == b'\x7fELF' and struct.unpack_from('<H', prx, 16)[0] == 0xFFA0, 'extra.prx is not a plain PRX'
    loader = p02.build_loader()
    with open(src, 'rb') as f:
        if p02.disc_state(f, loader) != 'patched':
            sys.exit('source %s is not a patched p02 disc' % src)
        head, src_rows = info_rows(f)
    idx, rows = build_idx(src_rows, bad)
    drop = pkg_hash(NEWPATH)
    new_info = None if bad else [r for r in src_rows if r[0] != drop]
    print('EXTRA.PRX %d B sha256 %s' % (len(prx), hashlib.sha256(prx).hexdigest()))
    print('EXTRA.IDX %d B sha256 %s%s' % (len(idx), hashlib.sha256(idx).hexdigest(), '  (BAD checksum)' if bad else ''))
    for h, sec, size, p in rows:
        print('  row %08x sector %d size %d  %s' % (h, sec, size, p))
    print('PACKAGE_INFO: %s' % ('unchanged (%d rows)' % len(src_rows) if bad else
                                '%d -> %d rows (row %08x %s removed)' % (len(src_rows), len(new_info), drop, NEWPATH)))
    if os.path.exists(out):
        with open(out, 'rb') as f:
            if p02.disc_state(f, loader) != 'patched':
                sys.exit('%s exists and is not a p02-based disc; not touching it' % out)
        print('%s exists' % out)
    elif dry:
        print('[dry] would copy %s -> %s' % (src, out))
    else:
        subprocess.run(['cp', '--reflink=auto', src, out], check=True)
        print('copied %s -> %s' % (src, out))
    target = out if os.path.exists(out) else src
    with open(target, 'rb') as f:
        pp = plan_put(f, p02.MODULE_DIR, p02.DISC_NAME, prx)
    print('MODULE/EXTRA.PRX: %s%s' % (pp['action'], '' if pp['action'] == 'same' else ' at sector %d' % (pp['pos'] // SECTOR)))
    if dry:
        with open(target, 'rb') as f:
            pi = plan_put(f, DATA_DIR, IDX_NAME, idx)
        print('DATA/EXTRA.IDX: %s (planned before the PRX write; real sector may shift)' % pi['action'])
        print('[dry] nothing written')
        return
    with open(out, 'r+b') as f:
        assert p02.disc_state(f, loader) == 'patched'
        apply_put(f, pp)
        pi = plan_put(f, DATA_DIR, IDX_NAME, idx)
        apply_put(f, pi)
        print('DATA/EXTRA.IDX: %s%s' % (pi['action'], '' if pi['action'] == 'same' else ' at sector %d' % (pi['pos'] // SECTOR)))
        if new_info is not None:
            rec_at, old_size = info_record(f)
            body = head[:8] + struct.pack('<I', len(new_info)) + head[12:16] + \
                b''.join(struct.pack('<III', *r) for r in new_info)
            f.seek(INFO_SECTOR * SECTOR)
            f.write(body + b'\0' * max(0, old_size - len(body)))
            f.seek(rec_at + 10)
            f.write(struct.pack('<I', len(body)) + struct.pack('>I', len(body)))
    with open(out, 'rb') as f:
        assert p02.disc_state(f, loader) == 'patched'
        assert plan_put(f, p02.MODULE_DIR, p02.DISC_NAME, prx)['action'] == 'same'
        assert plan_put(f, DATA_DIR, IDX_NAME, idx)['action'] == 'same'
        _, now = info_rows(f)
        assert now == (src_rows if bad else new_info)
        assert info_record(f)[1] == 16 + 12 * len(now)
        f.seek(0, 2)
        size = f.tell()
    print('%s: done (%d bytes)' % (out, size))
    if not nosha:
        print('sha256 %s' % p02.sha256_file(out))


if __name__ == '__main__':
    main()
