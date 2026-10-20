"""Find and decode EXTRA.PRX's status block in a running game (PPSSPP remote debugger, read only).

  python3 -I tools/pkg/engine/find_status.py PORT [ADDR]      (ADDR = known block address: skip the search)
  python3 -I tools/pkg/engine/find_status.py --selftest      (decoder test on a fake block, no emulator)

Search: user RAM 0x08800000-0x0A000000 (high RAM first, where the module loads) for the u32 "XTRA" at a 16-aligned
address A whose word A+8 equals A (self pointer) and whose last word A+0x7C is ~"XTRA". Prints every field, the
live rows and the API block. The game is not written. Layout v1 = tools/pkg/engine/extra/extra.c struct
extra_status, docs/ENGINE.md.
"""
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../../..'))

MAGIC, TAIL = 0x41525458, 0xBEADABA7
FIELDS = ['magic', 'layout_size', 'self', 'base', 'version', 'state', 'warn', 'rows', 'count', 'file_rows',
          'rejected', 'overrides', 'lookups', 'hits', 'last_hit', 'last_hash', 'hook_at', 'hook_word', 'guard_seen',
          'guard_mode', 'boot_max', 'boot_total', 'api', 'info_rows', 'first_rejected', 'pkg_size',
          'row_hits0', 'row_hits1', 'row_hits2', 'row_hits3', 'step', 'tail']
STATES = {0: 'starting (or died in module_start: see step)', 1: 'index OK but no live rows -> no hook',
          2: 'LIVE: rows loaded + hook written', -1: 'no EXTRA.IDX -> vanilla', -2: 'bad header', -3: 'no memory',
          -4: 'short read', -5: 'bad row (sort/sector/flag/size)', -6: 'bad checksum',
          -7: 'hook word not vanilla (someone else patched 0x08871420)', -8: 'row past the end of PACKAGE.BIN',
          -9: 'bad override bitmap'}
WARN = {1: 'PACKAGE_INFO unreadable, collision check skipped', 2: 'PACKAGE.BIN size unknown, bounds check skipped',
        4: 'JIT marker accepted at the hook', 8: 'hook read-back differs (JIT marker over our jal is fine)'}
USER_LO, USER_HI = 0x08800000, 0x0A000000


def find(buf, base):
    out = []
    i = buf.find(struct.pack('<I', MAGIC))
    while i >= 0:
        a = base + i
        if a % 16 == 0 and i + 0x80 <= len(buf):
            w = struct.unpack_from('<32I', buf, i)
            if w[2] == a and w[31] == TAIL:
                out.append(a)
        i = buf.find(struct.pack('<I', MAGIC), i + 1)
    return out


def decode(raw):
    w = struct.unpack('<32I', raw[:0x80])
    d = dict(zip(FIELDS, w))
    d['layout'], d['size'] = d['layout_size'] & 0xFFFF, d['layout_size'] >> 16
    d['state'] = struct.unpack('<i', struct.pack('<I', d['state']))[0]
    return d


def report(d, read=None):
    print('status block 0x%08X  layout %d size 0x%X  engine %d.%d.%d  module_start 0x%08X (base = this - 0x124)' % (
        d['self'], d['layout'], d['size'], d['version'] >> 16, d['version'] >> 8 & 0xFF, d['version'] & 0xFF,
        d['base']))
    print('state %d = %s;  step %d/8' % (d['state'], STATES.get(d['state'], '?'), d['step']))
    print('warn 0x%X%s' % (d['warn'], ''.join('\n  - ' + t for b, t in WARN.items() if d['warn'] & b)))
    print('rows: file %d, live %d at 0x%08X, rejected %d (first %08x), overrides %d; disc PACKAGE_INFO rows scanned %d;'
          ' PACKAGE.BIN %d B' % (d['file_rows'], d['count'], d['rows'], d['rejected'], d['first_rejected'],
                                 d['overrides'], d['info_rows'], d['pkg_size']))
    print('lookups %d, hits %d (rows 0-3: %d %d %d %d), last hit %08x, last hash %08x' % (
        d['lookups'], d['hits'], d['row_hits0'], d['row_hits1'], d['row_hits2'], d['row_hits3'], d['last_hit'],
        d['last_hash']))
    print('hook 0x%08X: written/read back 0x%08X, guard saw 0x%08X, guard mode %d; boot free max %d total %d; api 0x%08X'
          % (d['hook_at'], d['hook_word'], d['guard_seen'], d['guard_mode'], d['boot_max'], d['boot_total'], d['api']))
    if read is None:
        return
    if d['count'] and d['rows']:
        raw = read(d['rows'], 12 * min(d['count'], 16))
        for i in range(len(raw) // 12):
            print('  row %d: %08x sector %d size %d' % ((i,) + struct.unpack_from('<III', raw, 12 * i)))
    if d['api']:
        a = struct.unpack('<12I', read(d['api'], 48))
        print('api: magic %s ver %d size %d registry 0x%08X count %d find_row 0x%08X feature 0x%08X status 0x%08X' % (
            struct.pack('<I', a[0]), a[1] & 0xFFFF, a[1] >> 16, a[2], a[3], a[4], a[5], a[6]))
    hw = struct.unpack('<I', read(d['hook_at'], 4))[0]
    print('word at 0x%08X now: 0x%08X (%s)' % (d['hook_at'], hw, 'our jal' if hw == d['hook_word'] and hw else
                                              'vanilla jal 0x08871288' if hw == 0x0E21C4A2 else
                                              'JIT marker' if hw >> 26 == 0x1A else 'other'))


def selftest():
    a = 0x09B8E1E0
    w = [0] * 32
    w[0], w[1], w[2], w[3], w[4], w[5], w[31], w[30] = MAGIC, 1 | 0x80 << 16, a, 0x09B8DB24, 0x10000, 2, TAIL, 8
    blk = struct.pack('<32I', *w)
    buf = b'\0' * 0x1E0 + blk + b'XTRA' + b'\0' * 60
    found = find(buf, 0x09B8E000)
    assert found == [a], found
    d = decode(blk)
    assert d['state'] == 2 and d['layout'] == 1 and d['size'] == 0x80
    report(d)
    print('selftest OK')


def main():
    if '--selftest' in sys.argv:
        return selftest()
    sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
    import websocket
    import ppdbg
    port = sys.argv[1]
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=90, suppress_origin=True)

    def read(addr, size):
        return ppdbg.read(ws, addr, size)
    if len(sys.argv) > 2:
        hits = [int(sys.argv[2], 0)]
    else:
        hits, step = [], 0x40000
        ranges = list(range(0x09800000, USER_HI, step)) + list(range(USER_LO, 0x09800000, step))
        for base in ranges:
            hits += find(read(base, min(step + 0x80, USER_HI - base)), base)
            if hits:
                break
    if not hits:
        sys.exit('no XTRA status block in user RAM: EXTRA.PRX not loaded/started (check the PPSSPP log for '
                 'sceKernelLoadModule(...EXTRA.PRX))')
    for a in hits:
        report(decode(read(a, 0x80)), read)


if __name__ == '__main__':
    main()
