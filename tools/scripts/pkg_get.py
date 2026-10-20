"""Read one PACKAGE.BIN file out of an ISO (read-only), e.g. for objx -> objx steps in build_sora.sh.

  python3 -I pkg_get.py ISO PATH OUT        (PATH like obj/p_sev120.objx; OUT must not be the ISO)
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402


def main():
    iso, path, out = sys.argv[1:4]
    assert os.path.abspath(out) != os.path.abspath(iso)
    use_iso(iso)
    st, sz = pkg_offset(path)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    open(out, 'wb').write(d)
    print('%s: %d bytes -> %s' % (path, sz, out))


if __name__ == '__main__':
    main()
