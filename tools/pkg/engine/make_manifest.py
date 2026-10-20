"""Write tools/pkg/engine/engine.json (EXTRA.PRX identity + layout) and patches/engine-loader.json (EBOOT patch set).

  tools/dlc/pspenv.sh make -C tools/pkg/engine/extra
  python3 -I tools/pkg/engine/make_manifest.py [--check]     (--check: only compare, exit 1 if the files differ)

The loader patch words come from the P0.2 hand-assembled rewrite (tools/dlc/p02_module_disc.py build_loader, runtime
PASS on PPSSPP): 54 words of FUN_0886eebc (loader rewrite + "try once" mode 2 + stub + "extra.prx") and the boot site
0x0893361C. install_engine.py only reads the JSON (old words checked before writing, so a wrong disc is refused).
"""
import hashlib
import json
import os
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '../../..'))
sys.path.insert(0, os.path.join(ROOT, 'tools/dlc'))
sys.path.insert(0, os.path.join(ROOT, 'tools/scripts'))
import p02_module_disc as p02  # noqa: E402

PRX = os.path.join(HERE, 'extra/extra.prx')
LAYOUT = os.path.join(HERE, 'extra/extra.layout')


def loader_patch():
    new = p02.build_loader()
    words = [dict(va='0x%08X' % (p02.LOADER + 4 * i), old='0x%08X' % o, new='0x%08X' % w)
             for i, (o, w) in enumerate(zip(p02.LOADER_OLD, new))]
    words.append(dict(va='0x%08X' % p02.SITE, old='0x%08X' % p02.SITE_OLD, new='0x%08X' % p02.jal(p02.STUB)))
    ctx = [dict(va='0x%08X' % va, value='0x%08X' % w) for va, w in sorted({**p02.SITE_CTX, **p02.CALLERS}.items())]
    return {
        'id': 'engine-loader',
        'format': 1,
        'what': 'EBOOT: module loader FUN_0886eebc rewritten (same behaviour for libfont/libsuppreacc + mode 2 = one '
                'try, no retry) + stub 0x0886EF60 loading data/module/extra.prx once; boot site 0x0893361C '
                'jal FUN_08862650 -> jal stub (stub tail-jumps to FUN_08862650). Missing/failed EXTRA.PRX = boot '
                'continues (P0.2 runtime PASS).',
        'file': 'EBOOT.BIN (plain ELF)',
        'iso_sector': p02.EBOOT_SECTOR,
        'va_to_file': 'file offset = VA - 0x08804040 + 0x1018',
        'words': words,
        'context': ctx,
        'stub': '0x%08X' % p02.STUB,
        'spare_word': '0x0886EF90',
    }


def package_patch(lp):
    """Same edits in the P1.1 package shape (docs/PACKAGE-FORMAT.md section 8): patches/extra_prx.json."""
    return {
        'format_version': '1.0',
        'site': 'extra_prx',
        'set': 'engine',
        'layouts': ['A', 'B'],
        'note': 'engine loader: FUN_0886eebc rewrite + stub 0x0886ef60 + boot site 0x0893361c (= engine-loader.json)',
        'edits': [dict(image='EBOOT', va=w['va'].lower(), old=w['old'].lower(), new=w['new'].lower())
                  for w in sorted(lp['words'], key=lambda w: int(w['va'], 16)) if w['old'] != w['new']],
    }


def engine_manifest():
    prx = open(PRX, 'rb').read()
    if prx[:4] != b'\x7fELF' or struct.unpack_from('<H', prx, 16)[0] != 0xFFA0:
        sys.exit('extra.prx is not a plain PRX')
    syms, sections = {}, {}
    for line in open(LAYOUT):
        p = line.split()
        if len(p) == 3 and not p[0].startswith('.'):
            syms[p[2]] = '0x%X' % int(p[0], 16)
        elif len(p) == 3:
            sections[p[0]] = dict(size=int(p[1]), offset='0x%X' % int(p[2]))
    return {
        'name': 'EXTRA.PRX',
        'module_name': 'ExtraEngine',
        'version': '1.0.0',
        'disc_path': 'PSP_GAME/USRDIR/DATA/MODULE/EXTRA.PRX',
        'size': len(prx),
        'sha256': hashlib.sha256(prx).hexdigest(),
        'status_block': dict(symbol='g_extra', offset=syms.get('g_extra'), size='0x80', layout=1,
                             signature='u32 "XTRA" at a 16-aligned address A with u32 at A+8 == A'),
        'symbols_from_module_base': syms,
        'sections': sections,
        'loader_patch': 'patches/engine-loader.json',
    }


def main():
    lp = loader_patch()
    out = {os.path.join(HERE, 'engine.json'): engine_manifest(),
           os.path.join(HERE, 'patches/engine-loader.json'): lp,
           os.path.join(HERE, 'patches/extra_prx.json'): package_patch(lp)}
    diff = False
    for path, obj in out.items():
        text = json.dumps(obj, indent=2, sort_keys=True) + '\n'
        old = open(path).read() if os.path.exists(path) else None
        if old != text:
            diff = True
            if '--check' not in sys.argv:
                open(path, 'w').write(text)
        print('%s %s' % ('same   ' if old == text else ('DIFFERS' if '--check' in sys.argv else 'written'),
                         os.path.relpath(path, ROOT)))
    if '--check' in sys.argv and diff:
        sys.exit(1)


if __name__ == '__main__':
    main()
