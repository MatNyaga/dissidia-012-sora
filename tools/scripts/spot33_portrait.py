"""Sora's select-screen portrait ONLY (Quick Battle art + main-menu character select art), from
tools/art/approved/qb_art.png = Codex's refined portrait that Mat approved ("I like the image", 2026-10-16;
codex/inbox/20261016-select-portrait). Re-encodes just those two GIM entries with spot33_qbpics' own template/marker
path (keep + put) and leaves every other pack entry byte-identical. Asserts the result equals Codex's verified GIM
(sha256 d964a61b...). Re-runnable ("already").

Why a separate step: make_title_art.py (build) regenerates tools/art/qb_art.png with the old edge treatment, and
spot33_qbpics.py also rewrites icons/names/logos. build_sora.sh copies the approved PNG over qb_art.png after
make_title_art, and runs this after spot33_qbpics as a check.

  python3 -I spot33_portrait.py ISO
"""
import hashlib
import os
import subprocess
import sys
import tempfile

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from gim_put import put  # noqa: E402
from gim_markers import keep  # noqa: E402
import spot33_qbpics as Q  # noqa: E402

ART = os.path.join(ROOT, 'tools', 'art', 'approved', 'qb_art.png')
ART_SHA = '4df846c07b44fd74ab8bc9a66008ec8920f7f226f564fd326596f6cca1fb7e6c'
GIM_SHA = 'd964a61b24b938f850e68cbd18b96c76ca7a76b47b26a921b402e03c9a8707be'
SCENES = [(Q.PACKS, Q.TARGET, 0x700C), (Q.CS_PACKS, Q.CS_TARGET, 0x40E)]     # Quick Battle, main-menu chara select


def main():
    iso = sys.argv[1]
    assert hashlib.sha256(open(ART, 'rb').read()).hexdigest() == ART_SHA, 'approved portrait changed'
    for packs, target, slot in SCENES:
        use_iso(iso)
        f = open(iso, 'rb')
        by_id, raw = {}, {}
        for p in packs:
            st, sz = pkg_offset(p)
            raw[p] = read_at(f, st, sz)
            base, blobs = Q.read_pack(raw[p])
            for i, b in enumerate(blobs):
                if b:
                    by_id[base + i] = b
        f.close()
        base, blobs = Q.read_pack(raw[target])
        new_id, old_id = slot + Q.PIC, slot + Q.CLOUD_PIC
        idx = new_id - base
        img, nmark = keep(by_id[old_id], Image.open(ART).convert('RGBA'))
        gim = put(by_id[old_id], img)
        assert hashlib.sha256(gim).hexdigest() == GIM_SHA, 'encoded portrait differs from Codex-verified GIM'
        if idx < len(blobs) and blobs[idx] == gim:
            print('%s entry %d (id %d): already the approved portrait' % (os.path.basename(target), idx, new_id))
            continue
        assert idx < len(blobs) and blobs[idx], 'entry %d missing: run spot33_qbpics first' % idx
        blobs[idx] = gim
        new = Q.write_pack(raw[target], base, blobs)
        with tempfile.TemporaryDirectory() as t:
            p = os.path.join(t, 'pack.bin')
            open(p, 'wb').write(new)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, target, p],
                               check=True, capture_output=True, text=True)
        print('%s entry %d (id %d) <- approved portrait (%d marker px); %s' % (
            os.path.basename(target), idx, new_id, nmark, r.stdout.strip()))


if __name__ == '__main__':
    main()
