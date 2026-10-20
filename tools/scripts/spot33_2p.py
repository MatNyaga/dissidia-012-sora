"""#33's other costume slots (2P/3P = mirror match + LOOK alt costumes) still held Cloud: a CPU Sora in a Sora-vs-Sora
battle was drawn as Cloud with the Buster Sword and a Cloud HUD face (test 121, 2026-10-14). Copy the 1P model and
HUD picture over 2P and 3P (same data; no own alt colours yet).

  python3 -I spot33_2p.py ISO      (run after the model and spot33_faces.py)
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402

FILES = ['obj/P_SEV120_%s.gmo', 'menu/JP/battle/chara_image/P_SEV120_%s.gim']


def main():
    iso = sys.argv[1]
    for pat in FILES:
        use_iso(iso)
        st, sz = pkg_offset(pat % '1P')
        with open(iso, 'rb') as f:
            data = read_at(f, st, sz)
        for p in ('2P', '3P'):
            use_iso(iso)
            st2, sz2 = pkg_offset(pat % p)
            with open(iso, 'rb') as f:
                if read_at(f, st2, sz2) == data:
                    print('%s: already the 1P data' % (pat % p))
                    continue
            with tempfile.TemporaryDirectory() as t:
                tmp = os.path.join(t, os.path.basename(pat % p))
                open(tmp, 'wb').write(data)
                r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, pat % p, tmp],
                                   check=True, capture_output=True, text=True)
                print(r.stdout.strip())


if __name__ == '__main__':
    main()
