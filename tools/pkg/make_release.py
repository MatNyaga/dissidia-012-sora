"""Release delta for players (P1.9 + P1.10 two-stage): clean US disc -> mode-B disc as ONE VCDIFF patch + release.json.

  python3 -I tools/pkg/make_release.py CLEAN.iso TARGET.iso OUT_DIR [--version 1.0] [--older VER=SHA256 ...]
        [--reuse] [--no-verify] [--work-dir DIR] [--map-json PATH]

Two stages (P1.10, Mat: never ship the decrypted vanilla EBOOT):
  1. the player app decrypts the player's OWN ~PSP EBOOT.BIN in memory (pure Rust, tools/installer/core/src/pspcrypt.rs)
     and reads the disc through a "virtual source" = CLEAN with the EBOOT bytes (sector 560) replaced by the plain ELF;
  2. the patch is encoded against exactly that virtual source, so every vanilla EBOOT byte is a COPY from the player's
     own decrypted EBOOT and none is ADD data. Here the virtual source is written to the work dir by the app's own code
     (`sorapatch-cli --virtual-source CLEAN OUT`), checked (plain ELF sha256 0bc8e779... = bootstrap/eboot_plain.py, only
     the EBOOT bytes differ from CLEAN), used as xdelta3 -s, then deleted. release.json = format 2 with a "source" block.

Writes ONLY into OUT_DIR (must be new or contain only our release files):
  patch.vcdiff   `xdelta3 -e -9 -S none -B 2147483648 -s VIRTUAL_SOURCE TARGET` (the player app's pure-Rust decoder refuses
                 -S djw / lzma). -B = whole-disc source window: with xdelta3's default 64 MiB window the unchanged parts
                 of edited vanilla files (menu packs etc., copied far from their original sector) were partly stored
                 as ADD (617 KB of vanilla bytes, 20.4 MB patch); with -B 2 GiB they are COPY (15.6 MB patch). The
                 app's decoder reads COPY bytes on demand (tools/installer/core/src/vcdiff.rs), so RAM stays small.
  release.json   docs/INSTALLER-TECH.md §4 format 2 (input/output sha256 + size, version, output file name, older outputs,
                 source = plain_eboot: EBOOT offset, encrypted + plain size/sha256)
  README.txt     plain words: what this is, what you need, how to apply
CLEAN and TARGET are only opened for reading. Never ships an ISO, game file or package folder.

Checks (printed; the full ADD map goes to --map-json, default tools/pkg/ref/release-<ver>-delta-map.json):
  * VCDIFF instruction split: COPY from source (player's own disc) vs COPY from target vs ADD vs RUN bytes;
  * where every ADD/RUN byte lands in TARGET (ISO file, PACKAGE row with EXTRA.IDX name, ISO structure);
  * vanilla check: (a) ADD bytes inside sectors that are unchanged from the clean disc (must be 0),
    (b) every TARGET sector holding ADD bytes is hashed and looked up among all clean-disc sectors
        (a vanilla file shipped verbatim inside ADD data would show up here; a sector with < 32 ADD bytes is counted
        as incidental: single ADD bytes next to COPYs that happen to equal the source), (c) ADD bytes per changed vanilla file
    (d) vanilla-code check: ADD bytes covered by any 32-byte window that occurs anywhere in the plain vanilla ELF
        (windows with < 5 distinct byte values skipped) must be 0; ADD bytes in TARGET's EBOOT equal to the vanilla byte
        at the same offset are reported (incidental: unchanged bytes inside an edited word).
    All sector checks use the virtual source (what the player's app reads) as the reference "clean" disc.
    FAIL (no longer a warning) if TARGET's EBOOT is plain but the patch source's is not.
Verify (unless --no-verify): `xdelta3 -d -s VIRTUAL_SOURCE` and the app's own decoder (tools/installer sorapatch-cli,
from CLEAN: it decrypts the EBOOT itself) each rebuild TARGET; sha256 must equal TARGET's. Decoded copies go to --work-dir (default: OUT_DIR/../.release-verify, must not
be under /tmp or ~ because the root disk is small) and are deleted afterwards. sorapatch-cli also gets TARGET as input
and must answer "already_patched" without writing anything.
Exit 0 = release written and verified; 1 = a check failed; 2 = usage / input problem.
"""
import argparse
import bisect
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, 'engine'))
import isolib  # noqa: E402
from equiv import Disc, DATA, LAYOUT_FILES  # noqa: E402

SECTOR = 2048
CLEAN_SHA256 = 'df94177d3e194e82800a574b50b61ee3c7be6caa877c8e82242a41af75d1ab6e'
CLEAN_SIZE = 1754529792
DISC_ID = 'ULUS-10566'
TITLE = 'Sora for Dissidia 012'
OTHER_REGIONS = {'ULES-01505': 'European', 'ULJM-05814': 'Japanese'}
PATCH = 'patch.vcdiff'
SOURCE_WINDOW = 2147483648  # xdelta3 -B maximum; >= clean size so every vanilla byte can be a COPY
INCIDENTAL = 32  # ADD bytes per sector below which a clean-matching sector is coincidence, not shipped vanilla data
RELEASE_FILES = {PATCH, 'release.json', 'README.txt'}
INSTALLER = os.path.join(ROOT, 'tools/installer')
CLI = os.path.join(INSTALLER, 'target/release/sorapatch-cli')
EBOOT = 'PSP_GAME/SYSDIR/EBOOT.BIN'
# Same values as tools/scripts/eboot_plain.py (bootstrap) and the cargo test real_eboot_decrypts_to_known_plain_elf.
EBOOT_OFFSET = 560 * SECTOR
ENC_SIZE, ENC_SHA = 4641296, '8fbf3541ab121aff85aae72795760736dfe37706996b2b0f9b81d36fc98f3394'
ELF_SIZE, ELF_SHA = 4640948, '0bc8e779aad2814a3d1bd77346f69ca5e16665845ed053cd0ad44a9cbfaefe6d'
WINDOW = 32  # vanilla-code check window
MANIFEST_FORMAT = 2


def die(msg, code=2):
    print('ERROR: ' + msg)
    sys.exit(code)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            b = f.read(1 << 22)
            if not b:
                return h.hexdigest()
            h.update(b)


def disc_id(path):
    with open(path, 'rb') as f:
        for p, sec, size in isolib.walk_extents(f):
            if p.lstrip('/').split(';')[0] == 'UMD_DATA.BIN':
                return isolib.read_at(f, sec * SECTOR, min(size, 32)).split(b'|')[0].decode('ascii', 'replace')
    return None


# ---------------------------------------------------------------- VCDIFF walk (same rules as core/src/vcdiff.rs)
def code_table():
    NOOP, ADD, RUN, COPY = 0, 1, 2, 3
    t = [((RUN, 0, 0), (NOOP, 0, 0))]
    t += [((ADD, s, 0), (NOOP, 0, 0)) for s in range(18)]
    for m in range(9):
        t.append(((COPY, 0, m), (NOOP, 0, 0)))
        t += [((COPY, s, m), (NOOP, 0, 0)) for s in range(4, 19)]
    for m in range(6):
        t += [((ADD, a, 0), (COPY, c, m)) for a in range(1, 5) for c in range(4, 7)]
    for m in range(6, 9):
        t += [((ADD, a, 0), (COPY, 4, m)) for a in range(1, 5)]
    t += [((COPY, 4, m), (ADD, 1, 0)) for m in range(9)]
    assert len(t) == 256
    return t


def walk_vcdiff(path):
    """-> stats dict, merged ADD/RUN target ranges [(start, end, kind)]."""
    buf = open(path, 'rb').read()
    p = 0

    def vint():
        nonlocal p
        v = 0
        while True:
            c = buf[p]
            p += 1
            v = (v << 7) | (c & 0x7F)
            if not c & 0x80:
                return v

    if buf[:4] != b'\xd6\xc3\xc4\x00':
        raise ValueError('not VCDIFF')
    hdr = buf[4]
    p = 5
    if hdr & 1:
        raise ValueError('header says secondary compression (VCD_DECOMPRESS): app refuses it, use -S none')
    if hdr & 2:
        raise ValueError('custom code table: app refuses it')
    if hdr & 4:
        n = vint()
        p += n
    table = code_table()
    st = dict(windows=0, target=0, copy_src=0, copy_tgt=0, add=0, run=0, n_add=0, n_run=0, n_copy=0,
              max_src_seg=0, max_tgt_win=0, adler_windows=0, patch_size=len(buf))
    ranges = []  # (start, end, kind) kind 'A' add / 'R' run
    tpos = 0
    while p < len(buf):
        win = buf[p]
        p += 1
        if win & 2:
            raise ValueError('VCD_TARGET window: app refuses it')
        sseg_len = sseg_pos = 0
        if win & 1:
            sseg_len = vint()
            sseg_pos = vint()
        enc_len = vint()
        e0 = p
        tlen = vint()
        if buf[p] != 0:
            raise ValueError('window uses secondary compression: app refuses it')
        p += 1
        dlen, ilen, alen = vint(), vint(), vint()
        if win & 4:
            p += 4
            st['adler_windows'] += 1
        d0 = p
        i0, a0 = d0 + dlen, d0 + dlen + ilen
        p = a0 + alen
        if p - e0 != enc_len:
            raise ValueError('window length mismatch')
        st['windows'] += 1
        st['max_src_seg'] = max(st['max_src_seg'], sseg_len)
        st['max_tgt_win'] = max(st['max_tgt_win'], tlen)
        near, nn, same = [0] * 4, 0, [0] * 768
        ip, ap, here = i0, a0, 0
        while ip < a0:
            ops = table[buf[ip]]
            ip += 1
            for kind, size, mode in ops:
                if kind == 0:
                    continue
                if size == 0:
                    v = 0
                    while True:
                        c = buf[ip]
                        ip += 1
                        v = (v << 7) | (c & 0x7F)
                        if not c & 0x80:
                            break
                    size = v
                t0 = tpos + here
                if kind == 1 or kind == 2:
                    k = 'A' if kind == 1 else 'R'
                    if kind == 1:
                        st['add'] += size
                        st['n_add'] += 1
                    else:
                        st['run'] += size
                        st['n_run'] += 1
                    if ranges and ranges[-1][1] == t0 and ranges[-1][2] == k:
                        ranges[-1][1] = t0 + size
                    else:
                        ranges.append([t0, t0 + size, k])
                else:
                    cur = sseg_len + here
                    if mode == 0:
                        a, q = 0, 0
                        while True:
                            c = buf[ap]
                            ap += 1
                            a = (a << 7) | (c & 0x7F)
                            if not c & 0x80:
                                break
                    elif mode == 1:
                        q = 0
                        while True:
                            c = buf[ap]
                            ap += 1
                            q = (q << 7) | (c & 0x7F)
                            if not c & 0x80:
                                break
                        a = cur - q
                    elif mode < 6:
                        q = 0
                        while True:
                            c = buf[ap]
                            ap += 1
                            q = (q << 7) | (c & 0x7F)
                            if not c & 0x80:
                                break
                        a = near[mode - 2] + q
                    else:
                        a = same[(mode - 6) * 256 + buf[ap]]
                        ap += 1
                    near[nn] = a
                    nn = (nn + 1) & 3
                    same[a % 768] = a
                    st['n_copy'] += 1
                    if a < sseg_len:
                        n = min(size, sseg_len - a)
                        st['copy_src'] += n
                        st['copy_tgt'] += size - n
                    else:
                        st['copy_tgt'] += size
                here += size
        if here != tlen:
            raise ValueError('window %d decodes %d bytes, header says %d' % (st['windows'] - 1, here, tlen))
        tpos += tlen
    st['target'] = tpos
    return st, ranges


# ---------------------------------------------------------------- where target bytes live
def target_regions(T):
    """sorted [(start, end, label, group)] for TARGET: PACKAGE rows (EXTRA.IDX first), ISO files, structure."""
    regs = []
    pkg_sec, pkg_size = T.pkg
    for h, (i, sec, size, fl) in T.xrows.items():
        nm = T.xnames.get(h, '%08x' % h)
        grp = 'PACKAGE row via EXTRA.IDX (%s)' % ('override of a vanilla row' if h in T.xover else 'added')
        regs.append(((pkg_sec + sec) * SECTOR, (pkg_sec + sec) * SECTOR + size, 'PACKAGE:' + nm, grp))
    xsecs = {(sec, size) for (_, sec, size, _) in T.xrows.values()}
    for h, (i, sec, size, fl) in T.prows.items():
        if (sec, size) in xsecs:
            continue
        regs.append(((pkg_sec + sec) * SECTOR, (pkg_sec + sec) * SECTOR + size, 'PACKAGE:%08x' % h,
                     'VANILLA PACKAGE_INFO row'))
    for path, (sec, size) in T.files.items():
        if path == DATA + 'PACKAGE.BIN':
            continue
        regs.append((sec * SECTOR, sec * SECTOR + size, path, 'ISO file'))
    regs.sort()
    first = min(s for s, _, _, _ in regs)
    regs.insert(0, (0, first, 'system area + PVD + path tables + directory records', 'ISO structure'))
    return regs


def map_ranges(ranges, regs, clean_size):
    """bytes per region label / group for ADD and RUN ranges; gaps = sector padding between files."""
    starts = [r[0] for r in regs]
    per_label, per_group = {}, {}

    def put(label, group, k, n):
        d = per_label.setdefault(label, {'group': group, 'A': 0, 'R': 0})
        d[k] += n
        g = per_group.setdefault(group, {'A': 0, 'R': 0})
        g[k] += n

    for s, e, k in ranges:
        pos = s
        i = max(0, bisect.bisect_right(starts, pos) - 1)
        while pos < e:
            while i < len(regs) and regs[i][1] <= pos:
                i += 1
            if i < len(regs) and regs[i][0] <= pos:
                end = min(e, regs[i][1])
                put(regs[i][2], regs[i][3], k, end - pos)
            else:
                nxt = regs[i][0] if i < len(regs) else e
                end = min(e, nxt)
                put('(padding between files, %s clean end)' % ('before' if pos < clean_size else 'after'),
                    'padding', k, end - pos)
            pos = end
    return per_label, per_group


def uniform(b):
    return b.count(b[:1]) == len(b)


def sector_checks(clean_path, target_path, ranges, clean_size):
    """(a) ADD bytes in sectors unchanged from clean; (b) ADD-holding target sectors found anywhere on the clean disc."""
    add_secs = {}
    for s, e, k in ranges:
        if k != 'A':
            continue
        for sec in range(s // SECTOR, (e - 1) // SECTOR + 1):
            lo, hi = max(s, sec * SECTOR), min(e, (sec + 1) * SECTOR)
            add_secs[sec] = add_secs.get(sec, 0) + hi - lo
    print('  hashing every clean sector (%d) ...' % (clean_size // SECTOR), flush=True)
    clean_set = set()
    with open(clean_path, 'rb') as f:
        while True:
            b = f.read(SECTOR * 4096)
            if not b:
                break
            for o in range(0, len(b), SECTOR):
                s = b[o:o + SECTOR]
                if not uniform(s):
                    clean_set.add(hashlib.blake2b(s, digest_size=8).digest())
    unchanged_add, found, found_list, uniform_add, incidental, inc_secs = 0, 0, [], 0, 0, 0
    with open(target_path, 'rb') as tf, open(clean_path, 'rb') as cf:
        for sec in sorted(add_secs):
            tf.seek(sec * SECTOR)
            t = tf.read(SECTOR)
            if sec * SECTOR + SECTOR <= clean_size:
                cf.seek(sec * SECTOR)
                if cf.read(SECTOR) == t:
                    unchanged_add += add_secs[sec]
            if uniform(t):
                uniform_add += add_secs[sec]
                continue
            if hashlib.blake2b(t, digest_size=8).digest() in clean_set:
                if add_secs[sec] < INCIDENTAL:
                    incidental += add_secs[sec]
                    inc_secs += 1
                    continue
                found += add_secs[sec]
                if len(found_list) < 50:
                    found_list.append((sec, add_secs[sec]))
    return dict(add_sectors=len(add_secs), add_bytes_in_unchanged_sectors=unchanged_add,
                add_bytes_in_sectors_found_on_clean_disc=found, found_examples=found_list,
                add_bytes_in_uniform_sectors=uniform_add, incidental_add_bytes=incidental,
                incidental_sectors=inc_secs)


def vanilla_code_check(target_path, ranges, plain, t_eboot):
    """ADD bytes inside 32-byte windows found anywhere in the plain vanilla ELF; same-offset equal bytes in TARGET EBOOT."""
    print('  indexing every %d-byte window of the plain vanilla ELF (%d B) ...' % (WINDOW, len(plain)), flush=True)
    win = set()
    for o in range(len(plain) - WINDOW + 1):
        w = plain[o:o + WINDOW]
        win.add(hash(w))
    covered, hit_ranges = 0, []
    t_off, t_size = t_eboot
    same_off, longest_same = 0, 0
    with open(target_path, 'rb') as tf:
        for s, e, k in ranges:
            if k != 'A':
                continue
            tf.seek(s)
            b = tf.read(e - s)
            mark = bytearray(len(b))
            for o in range(len(b) - WINDOW + 1):
                w = b[o:o + WINDOW]
                if hash(w) in win and len(set(w)) >= 5 and w in plain:
                    mark[o:o + WINDOW] = b'\1' * WINDOW
            c = mark.count(1)
            if c:
                covered += c
                if len(hit_ranges) < 20:
                    hit_ranges.append((s, e - s, c))
            lo, hi = max(s, t_off), min(e, t_off + t_size)
            run = 0
            for pos in range(lo, hi):
                fo = pos - t_off
                if fo < len(plain) and b[pos - s] == plain[fo]:
                    same_off += 1
                    run += 1
                    longest_same = max(longest_same, run)
                else:
                    run = 0
    return dict(add_bytes_in_vanilla_elf_windows=covered, examples=hit_ranges,
                eboot_add_bytes_equal_to_vanilla_same_offset=same_off, eboot_longest_equal_run=longest_same)


def changed_vanilla_files(C, T, per_label):
    """ISO files present on both discs whose bytes differ: ADD bytes shipped for each."""
    out = []
    for path, (sec, size) in sorted(T.files.items()):
        if path in LAYOUT_FILES or path not in C.files:
            continue
        cs, cz = C.files[path]
        same = (cz == size and C.sha_extent(cs, cz) == T.sha_extent(sec, size))
        if not same:
            d = per_label.get(path, {'A': 0, 'R': 0})
            out.append(dict(path=path, clean_size=cz, target_size=size, add=d['A'], run=d['R']))
    return out


# ---------------------------------------------------------------- outputs
README = """Sora for Dissidia 012 - fan patch {version}
No Dissidia files are included. Sora's model and sounds are fan-ported from Kingdom Hearts II.
Fan-made, not affiliated with Square Enix or Disney.
Built by Mat with help from AI tools (Claude, Codex).

What is in this folder
  {patch:<14} the patch itself ({psize:,} bytes). It only holds our changes, never the game.
  release.json   the checksums the patch app uses to recognise your file.
  README.txt     this text.

What you need
  Your own copy of the US version of Dissidia 012 as an ISO file (disc code {disc_id}).
  It must be unmodified: size {isize:,} bytes, SHA-256 {isha}.
  About 2 GB of free space for the new file.

How to use it
  Use the "Sora for Dissidia 012" patch app. It checks your file, unlocks the game's
  program file (EBOOT.BIN) from YOUR copy while it works, and builds the new file.
  (Command line, same steps: sorapatch-cli <this folder> "your US ISO")
  Plain xdelta tools (xdelta3, xdeltaUI, DeltaPatcher) can't apply this patch directly:
  it is made against your disc with its program file unlocked, which only the app does.
  Your original file is never changed. The new file should be {osize:,} bytes,
  SHA-256 {osha}.

Before your first start: back up your save
  Copy your save folder somewhere safe (PPSSPP: memstick/PSP/SAVEDATA/ULUS10566...,
  PSP: PSP/SAVEDATA/ULUS10566... on the memory stick).
  Sora's progress uses the space of Friend Card 25, so you can keep 24 Friend Cards.
  If your save already holds 25, the oldest card that is not locked is removed to make
  room (the same way the game makes room for a new card). Lock any card you want to keep.
  Going back to the original game with a save used with Sora is not supported:
  restore your backup instead.

Good to know
  Sora adds 6 new items to the PP Catalog (1,200 PP in total). A save that was at 100 %
  shows a little less (and grey Jukebox / Player Icon stars) until you buy them.
  Friend Cards, ghosts and ad-hoc play with players of the unmodded game are not
  supported. Both players need this same Sora version.

How to play
  Tested on PPSSPP (PC) and on a PS Vita (Adrenaline). Real PSP: not tested yet.
  PPSSPP: open the new file.
  PS Vita (Adrenaline) / PSP (custom firmware): copy it into the ISO folder of the memory
  stick. If the game does not start, turn off game plugins (Adrenaline: Recovery menu).
"""


def build_cli():
    subprocess.run(['nice', 'cargo', 'build', '--release', '-q', '-p', 'sorapatch-cli'], cwd=INSTALLER, check=True)


def make_virtual_source(clean, vpath, csize):
    """Stage 1 with the app's own code: CLEAN + its decrypted EBOOT -> vpath. -> manifest source block."""
    p = subprocess.run([CLI, '--virtual-source', clean, vpath], capture_output=True, text=True)
    if p.returncode != 0:
        die('sorapatch-cli --virtual-source failed: %s %s' % (p.stdout.strip(), p.stderr.strip()), 1)
    src = json.loads(p.stdout.strip().splitlines()[-1])
    want = dict(kind='plain_eboot', file=EBOOT, offset=EBOOT_OFFSET, encrypted_size=ENC_SIZE, encrypted_sha256=ENC_SHA,
                plain_size=ELF_SIZE, plain_sha256=ELF_SHA)
    if src != want:
        die('decrypted EBOOT is not the known plain ELF: %r' % src, 1)
    # Only [offset, offset + plain_size) may differ from CLEAN, and that range must be the plain ELF.
    lo, hi = EBOOT_OFFSET, EBOOT_OFFSET + ELF_SIZE
    if os.path.getsize(vpath) != csize:
        die('virtual source size %d != clean %d' % (os.path.getsize(vpath), csize), 1)
    h = hashlib.sha256()
    with open(clean, 'rb') as cf, open(vpath, 'rb') as vf:
        pos = 0
        while pos < csize:
            n = min(1 << 22, csize - pos)
            c, v = cf.read(n), vf.read(n)
            a, b = max(pos, lo), min(pos + n, hi)
            if a < b:
                h.update(v[a - pos:b - pos])
                c = c[:a - pos] + v[a - pos:b - pos] + c[b - pos:]
            if c != v:
                die('virtual source differs from CLEAN outside the EBOOT bytes near offset %d' % pos, 1)
            pos += n
    if h.hexdigest() != ELF_SHA:
        die('virtual source EBOOT range sha256 %s != %s' % (h.hexdigest(), ELF_SHA), 1)
    return src


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('clean')
    ap.add_argument('target')
    ap.add_argument('out_dir')
    ap.add_argument('--version', default='1.0')
    ap.add_argument('--older', action='append', default=[], metavar='VER=SHA256',
                    help='output sha256 of an older release (player gets "older patch" text)')
    ap.add_argument('--file-name', default=None, help='default "Dissidia 012 + Sora (fan patch VER).iso"')
    ap.add_argument('--reuse', action='store_true', help='keep an existing OUT_DIR/patch.vcdiff (no re-encode)')
    ap.add_argument('--source-window', type=int, default=SOURCE_WINDOW, help='xdelta3 -B (default whole disc)')
    ap.add_argument('--no-verify', action='store_true')
    ap.add_argument('--work-dir', default=None)
    ap.add_argument('--map-json', default=None)
    a = ap.parse_args()

    clean, target, out = (os.path.abspath(x) for x in (a.clean, a.target, a.out_dir))
    home = os.path.realpath(os.path.expanduser('~'))
    work = os.path.abspath(a.work_dir or os.path.join(os.path.dirname(out), '.release-verify'))
    for d in (out, work):
        rd = os.path.realpath(d)
        if rd.startswith('/tmp') or rd == home or rd.startswith(home + os.sep):
            die('%s is on the small root disk (/tmp or ~); use a folder on /data' % d)
    for f in (clean, target):
        if not os.path.isfile(f):
            die('missing ' + f)
        if os.path.realpath(f).startswith(os.path.realpath(out) + os.sep) or \
                os.path.realpath(f).startswith(os.path.realpath(work) + os.sep):
            die('an input ISO lives inside OUT_DIR / work dir')
    if os.path.isdir(out):
        extra = set(os.listdir(out)) - RELEASE_FILES - {PATCH + '.part'}
        if extra:
            die('OUT_DIR holds other files %s; the release folder may only hold %s' % (sorted(extra), sorted(RELEASE_FILES)))
    if os.path.exists(work):
        die('work dir %s exists (left over?); remove it first' % work)
    if shutil.which('xdelta3') is None:
        die('xdelta3 not found (needed: xdelta3 3.x with -S none)')
    older = []
    for o in a.older:
        v, _, s = o.partition('=')
        if len(s) != 64:
            die('--older wants VER=SHA256')
        older.append({'version': v, 'sha256': s.lower()})
    out_name = a.file_name or 'Dissidia 012 + Sora (fan patch %s).iso' % a.version
    map_json = a.map_json or os.path.join(HERE, 'ref', 'release-%s-delta-map.json' % a.version)
    t_start = time.time()

    print('[1/7] inputs')
    csize, tsize = os.path.getsize(clean), os.path.getsize(target)
    csha = sha256_file(clean)
    if csha != CLEAN_SHA256 or csize != CLEAN_SIZE:
        die('CLEAN is not the known clean US disc (sha256 %s, size %d)' % (csha, csize))
    cid = disc_id(clean)
    if cid != DISC_ID:
        die('CLEAN disc id %r != %s' % (cid, DISC_ID))
    tsha = sha256_file(target)
    if tsha == csha:
        die('TARGET == CLEAN')
    print('  clean  %s  %d B  %s' % (csha, csize, cid))
    print('  target %s  %d B  (disc id %s)' % (tsha, tsize, disc_id(target)))

    os.makedirs(work)
    ok = False
    try:
        print('[2/7] stage 1: virtual source = clean disc + its EBOOT decrypted by the app core (pspcrypt.rs)')
        build_cli()
        vsrc = os.path.join(work, 'virtual-source.tmp')
        t0 = time.time()
        source = make_virtual_source(clean, vsrc, csize)
        print('  %s @%d: %d B ~PSP (sha256 %s...) -> plain ELF %d B (sha256 %s... = eboot_plain/bootstrap)  %.0f s' %
              (EBOOT, source['offset'], source['encrypted_size'], source['encrypted_sha256'][:12],
               source['plain_size'], source['plain_sha256'][:12], time.time() - t0))
        print('  only the EBOOT bytes differ from CLEAN: checked')

        print('[3/7] stage 2: encode against the virtual source')
        os.makedirs(out, exist_ok=True)
        patch = os.path.join(out, PATCH)
        if a.reuse and os.path.isfile(patch):
            print('  --reuse: keeping existing %s' % patch)
        else:
            part = patch + '.part'
            cmd = ['nice', 'xdelta3', '-e', '-9', '-S', 'none', '-B', str(a.source_window), '-f', '-s', vsrc, target, part]
            print('  ' + ' '.join(cmd), flush=True)
            t0 = time.time()
            subprocess.run(cmd, check=True)
            os.replace(part, patch)
            print('  %.0f s' % (time.time() - t0))
        psize = os.path.getsize(patch)
        psha = sha256_file(patch)
        print('  patch %s  %d B (%.2f MB)' % (psha, psize, psize / 1e6))

        print('[4/7] VCDIFF walk + ADD map')
        st, ranges = walk_vcdiff(patch)
        if st['target'] != tsize:
            die('patch decodes %d bytes, TARGET has %d' % (st['target'], tsize), 1)
        C, T = Disc(vsrc), Disc(target)
        regs = target_regions(T)
        per_label, per_group = map_ranges(ranges, regs, csize)
        pct = lambda n: 100.0 * n / st['target']  # noqa: E731
        print('  windows %d (max source segment %d B, max target window %d B, Adler-32 on %d)' %
              (st['windows'], st['max_src_seg'], st['max_tgt_win'], st['adler_windows']))
        for k, lab in (('copy_src', 'COPY from source (player disc)'), ('copy_tgt', 'COPY from target (self)'),
                       ('add', 'ADD (bytes inside the patch)'), ('run', 'RUN (repeated byte)')):
            print('  %-32s %14d B  %6.2f %%' % (lab, st[k], pct(st[k])))
        print('  instructions: %d COPY, %d ADD, %d RUN' % (st['n_copy'], st['n_add'], st['n_run']))
        print('  ADD/RUN by kind of target region:')
        for g, d in sorted(per_group.items(), key=lambda x: -x[1]['A']):
            print('    %-50s ADD %12d  RUN %10d' % (g, d['A'], d['R']))
        top = sorted(per_label.items(), key=lambda x: -x[1]['A'])
        print('  largest ADD regions:')
        for lab, d in top[:15]:
            print('    %10d  %s' % (d['A'], lab))

        print('[5/7] vanilla check (reference = virtual source, i.e. the player\'s disc after stage 1)')
        sc = sector_checks(vsrc, target, ranges, csize)
        cv = changed_vanilla_files(C, T, per_label)
        vanilla_pkg_add = per_group.get('VANILLA PACKAGE_INFO row', {'A': 0})['A']
        print('  ADD bytes in sectors unchanged from the source: %d' % sc['add_bytes_in_unchanged_sectors'])
        print('  ADD bytes in sectors whose exact content exists on the source disc: %d %s' %
              (sc['add_bytes_in_sectors_found_on_clean_disc'], sc['found_examples'][:5]))
        print('  incidental (< %d ADD bytes in a source-matching sector): %d bytes in %d sectors' %
              (INCIDENTAL, sc['incidental_add_bytes'], sc['incidental_sectors']))
        print('  ADD bytes in vanilla PACKAGE_INFO rows: %d' % vanilla_pkg_add)
        print('  changed vanilla ISO files (ADD shipped):')
        for d in cv:
            print('    %-40s clean %9d -> %9d B  ADD %9d' % (d['path'], d['clean_size'], d['target_size'], d['add']))
        ce, te = C.file_bytes(EBOOT), T.file_bytes(EBOOT)
        eboot_ok = not (te[:4] == b'\x7fELF' and ce[:4] != b'\x7fELF')
        if not eboot_ok:
            print('  FAIL: TARGET EBOOT is plain but the patch source EBOOT is not (vanilla code would ship)')
        with open(vsrc, 'rb') as vf:
            vf.seek(EBOOT_OFFSET)
            plain = vf.read(ELF_SIZE)
        te_sec, te_size = T.files[EBOOT]
        vc = vanilla_code_check(target, ranges, plain, (te_sec * SECTOR, te_size))
        sc['vanilla_code'] = vc
        sc['eboot_source'] = 'player EBOOT decrypted by the app (format 2 plain_eboot)'
        print('  vanilla-code check: ADD bytes inside %d-byte windows of the plain vanilla ELF: %d %s' %
              (WINDOW, vc['add_bytes_in_vanilla_elf_windows'], vc['examples'][:5]))
        print('  EBOOT: ADD %d B (our edits); of these %d equal the vanilla byte at the same offset (longest run %d B,'
              ' unchanged bytes inside edited words)' % (per_label.get(EBOOT, {'A': 0})['A'],
                                                        vc['eboot_add_bytes_equal_to_vanilla_same_offset'],
                                                        vc['eboot_longest_equal_run']))
        ok_vanilla = (sc['add_bytes_in_unchanged_sectors'] == 0 and sc['add_bytes_in_sectors_found_on_clean_disc'] == 0
                      and vanilla_pkg_add == 0 and eboot_ok and vc['add_bytes_in_vanilla_elf_windows'] == 0)
        print('  verdict: %s' % ('PASS - no vanilla sector content and no vanilla EBOOT code inside ADD data'
                                 if ok_vanilla else 'FAIL'))

        print('[6/7] release.json + README')
        manifest = {
            'format': MANIFEST_FORMAT, 'title': TITLE, 'version': a.version,
            'input': {'disc_id': DISC_ID, 'size': csize, 'sha256': csha},
            'output': {'file_name': out_name, 'size': tsize, 'sha256': tsha},
            'older_outputs': older,
            'other_regions': OTHER_REGIONS,
            'source': source,
        }
        with open(os.path.join(out, 'release.json'), 'w') as f:
            json.dump(manifest, f, indent=2)
            f.write('\n')
        with open(os.path.join(out, 'README.txt'), 'w') as f:
            f.write(README.format(version=a.version, patch=PATCH, psize=psize, disc_id=DISC_ID, isize=csize, isha=csha,
                                  out_name=out_name, osize=tsize, osha=tsha))
        os.makedirs(os.path.dirname(map_json), exist_ok=True)
        with open(map_json, 'w') as f:
            json.dump({'version': a.version, 'manifest_format': MANIFEST_FORMAT, 'source': source,
                       'patch_sha256': psha, 'patch_size': psize, 'clean_sha256': csha,
                       'target_sha256': tsha, 'stats': st, 'add_run_by_group': per_group,
                       'add_run_by_region': dict(top), 'vanilla_check': sc, 'changed_vanilla_files': cv,
                       'add_ranges_count': len(ranges)}, f, indent=1, sort_keys=True)
        print('  %s\n  %s' % (os.path.join(out, 'release.json'), map_json))

        ok = ok_vanilla
        if not a.no_verify:
            print('[7/7] verify')
            tmp = os.path.join(work, 'xdelta3-decoded.tmp')
            t0 = time.time()
            subprocess.run(['nice', 'xdelta3', '-d', '-f', '-s', vsrc, patch, tmp], check=True)
            s1 = sha256_file(tmp)
            os.remove(tmp)
            r1 = s1 == tsha
            print('  xdelta3 -d -s virtual-source  sha256 %s  %s (%.0f s)' %
                  (s1, 'MATCH' if r1 else 'MISMATCH', time.time() - t0))
            os.remove(vsrc)  # from here on only the app's in-memory decryption is used
            t0 = time.time()
            rd = os.path.join(work, 'rust')
            os.makedirs(rd)
            timer = ['/usr/bin/time', '-f', 'PEAK_RSS_KB %M'] if os.path.exists('/usr/bin/time') else []
            p = subprocess.run(timer + [CLI, out, clean, '--out-dir', rd], capture_output=True, text=True)
            rss = [ln for ln in p.stderr.splitlines() if ln.startswith('PEAK_RSS_KB')]
            built = [x for x in os.listdir(rd)]
            s2 = sha256_file(os.path.join(rd, out_name)) if out_name in built else None
            r2 = p.returncode == 0 and s2 == tsha and built == [out_name]
            print('  sorapatch-cli (decrypts the EBOOT itself) build exit %d, files %s, sha256 %s  %s (%.0f s, %s)' %
                  (p.returncode, built, s2, 'MATCH' if r2 else 'MISMATCH', time.time() - t0,
                   rss[0] if rss else 'rss n/a'))
            if not r2:
                print(p.stdout[-2000:], p.stderr[-2000:])
            shutil.rmtree(rd)
            os.makedirs(rd)
            p = subprocess.run([CLI, out, target, '--out-dir', rd], capture_output=True, text=True)
            r3 = p.returncode == 1 and 'already_patched' in p.stdout and os.listdir(rd) == []
            print('  sorapatch-cli on TARGET -> %s (exit %d, nothing written: %s)' %
                  ('already_patched' if 'already_patched' in p.stdout else p.stdout.strip()[:80], p.returncode,
                   os.listdir(rd) == []))
            ok = ok and r1 and r2 and r3
    finally:
        shutil.rmtree(work, ignore_errors=True)
    left = sorted(os.listdir(out))
    print('release folder %s: %s' % (out, left))
    if set(left) - RELEASE_FILES:
        ok = False
        print('  FAIL: unexpected files in the release folder')
    print('%s  (%.0f s)' % ('RELEASE OK' if ok else 'RELEASE CHECK FAILED', time.time() - t_start))
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
