"""Host unit test of EXTRA.PRX's boot logic: tools/pkg/engine/extra/extra.c compiled for x86-64 with -DHOST_TEST
(PSP calls mocked in host_test.c), run against real disc data. No emulator, no ISO written.

  python3 -I tools/pkg/engine/test/run_host_test.py [ISO]     (ISO default dumps/ULUS10566-test339-installfix.iso,
                                                              read only: PACKAGE_INFO.BIN + PACKAGE.BIN size)
Cases: the p14 rows (1 override + 1 deliberate unflagged collision), missing / bad header / bad sum / unsorted /
row past PACKAGE.BIN / bad override bits / empty index / all rows rejected / no memory / hook word taken / PPSSPP JIT
marker / unreadable PACKAGE_INFO. Each case checks the status block values the runtime recipe expects.
"""
import json
import os
import shutil
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ENG = os.path.dirname(HERE)
ROOT = os.path.abspath(os.path.join(ENG, '../../..'))
sys.path.insert(0, ENG)
import install_engine as ie  # noqa: E402
import isolib as iso  # noqa: E402
import xidx  # noqa: E402


def run(exe, d, env=None, hashes=()):
    e = dict(os.environ, XDIR=d, **(env or {}))
    out = subprocess.run([exe] + ['%08x' % h for h in hashes], env=e, capture_output=True, text=True, check=True).stdout
    lines = out.splitlines()
    kv = dict(p.split('=', 1) for p in lines[0].split())
    kv.update(dict(p.split('=', 1) for p in lines[-1].split()))
    return kv, lines[1:-1]


def main():
    src = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else
                          os.path.join(ROOT, 'dumps/ULUS10566-test339-installfix.iso'))
    tmp = tempfile.mkdtemp(prefix='xtra_host_')
    try:
        exe = os.path.join(tmp, 'host_test')
        subprocess.run(['gcc', '-O1', '-Wall', '-Wextra', '-DHOST_TEST', '-o', exe, os.path.join(HERE, 'host_test.c')],
                       check=True)
        with open(src, 'rb') as f:
            info_off, info_size = iso.find_file(f, ie.DATA_DIR, b'PACKAGE_INFO.BIN')
            info = iso.read_at(f, info_off * iso.SECTOR, info_size)
            pkg_size = iso.find_file(f, ie.DATA_DIR, b'PACKAGE.BIN')[1]
            disc_info = ie.info_rows(f)
        rows = ie.rows_from_file(os.path.join(HERE, 'p14_rows.json'), disc_info)
        good = [dict(hash=r['hash'], sector=r['sector'], size=r['size'], override=r['override'], path=r['path'])
                for r in rows]
        ov_hash = xidx.pkg_hash('menu/JP/story_mode/chara2/p_sev120_1p.gim')
        rej_hash = xidx.pkg_hash('menu/JP/story_mode/chara2/p_gst130_1p.gim')
        newp = dict(hash=0x00001234, sector=10, size=100, override=False, path='test/new_only.bin')  # not on disc

        def case(name, idx, env=None, info_data=info, pkg=pkg_size, hashes=(), **expect):
            d = os.path.join(tmp, name)
            os.mkdir(d)
            if idx is not None:
                open(os.path.join(d, 'EXTRA.IDX'), 'wb').write(idx)
            if info_data is not None:
                open(os.path.join(d, 'PACKAGE_INFO.BIN'), 'wb').write(info_data)
            if pkg is not None:
                open(os.path.join(d, 'PACKAGE.BIN.size'), 'w').write(str(pkg))
            kv, finds = run(exe, d, env, hashes)
            bad = {k: (kv.get(k), str(v)) for k, v in expect.items() if kv.get(k) != str(v)}
            base_ok = kv['magic'] == '41525458' and kv['self_ok'] == '1' and kv['step'] == '8' and \
                kv['tail'] == 'beadaba7' and kv['api_magic'] == '49504158' and kv['api_status_ok'] == '1'
            print('%-14s %s  state=%s count=%s rejected=%s overrides=%s warn=%s hook=%s%s' % (
                name, 'PASS' if not bad and base_ok else 'FAIL', kv['state'], kv['count'], kv['rejected'],
                kv['overrides'], kv['warn'], kv['hook_word'], ('  ' + str(bad)) if bad else ''))
            for line in finds:
                print('               ' + line)
            return not bad and base_ok, kv, finds

        ok = []
        r, kv, finds = case('p14', xidx.build(good), hashes=(ov_hash, rej_hash), state=2, count=1, file_rows=2,
                            rejected=1, overrides=1, first_rejected='%08x' % rej_hash, info_rows=len(disc_info),
                            pkg_size=pkg_size, warn=0, guard_mode=1, hook_word='ours', hits=1, row_hits0=1,
                            feature=0)
        ok.append(r and finds[0].endswith('sector 242709 size 5408') and finds[1].endswith('miss'))
        ok.append(case('missing', None, state=-1, count=0, hook_word='vanilla', file_rows=0)[0])
        ok.append(case('bad_header', b'XIDX' + b'\0' * 28, state=-2, hook_word='vanilla')[0])
        b = bytearray(xidx.build(good))
        struct.pack_into('<I', b, 0x14, struct.unpack_from('<I', b, 0x14)[0] ^ 0xDEADBEEF)
        ok.append(case('bad_sum', bytes(b), state=-6, count=0, hook_word='vanilla')[0])
        b = bytearray(xidx.build(good + [newp]))
        r0 = b[32:44]
        b[32:44], b[44:56] = b[44:56], r0
        ok.append(case('unsorted', bytes(b), state=-5, hook_word='vanilla')[0])
        far = dict(newp, sector=0xFFFFF, size=0x1000)
        ok.append(case('past_pkg', xidx.build(good + [far]), state=-8, count=0, hook_word='vanilla')[0])
        b = bytearray(xidx.build(good))
        ovo = struct.unpack_from('<I', b, 0x18)[0]
        struct.pack_into('<I', b, ovo, struct.unpack_from('<I', b, ovo)[0] | 0x80000000)
        struct.pack_into('<I', b, 0x14, (struct.unpack_from('<I', b, 0x14)[0] + 0x80000000) & 0xFFFFFFFF)
        ok.append(case('bad_ovr_bits', bytes(b), state=-9, hook_word='vanilla')[0])
        ok.append(case('empty', xidx.build([]), state=1, count=0, hook_word='vanilla')[0])
        ok.append(case('all_rejected', xidx.build([good[1]]), state=1, count=0, rejected=1, hook_word='vanilla')[0])
        ok.append(case('no_memory', xidx.build(good), env=dict(NOMEM='1'), state=-3, hook_word='vanilla')[0])
        ok.append(case('hook_taken', xidx.build(good), env=dict(HOOK='taken'), state=-7, count=0,
                       guard_mode=0, hook_word='vanilla')[0])
        ok.append(case('jit_marker', xidx.build(good), env=dict(HOOK='jit'), state=2, guard_mode=2, warn=4,
                       hook_word='ours')[0])
        r, kv, finds = case('no_info', xidx.build(good + [newp]), info_data=None, hashes=(newp['hash'],), state=2,
                            count=3, rejected=0, warn=1, hook_word='ours')
        ok.append(r and finds[0].endswith('sector 10 size 100'))
        ok.append(case('no_pkg_stat', xidx.build(good), pkg=None, state=2, count=1, warn=2, hook_word='ours')[0])
        print('host test: %d/%d PASS' % (sum(ok), len(ok)))
        sys.exit(0 if all(ok) else 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main()
