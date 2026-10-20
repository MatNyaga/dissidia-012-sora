"""Give roster spot #33 its own voice files (grunts bank + spoken battle lines).

How a fighter's voices are found (2026-10-12):
- system.bin/chrp row +0x74 char[8] = voice key (Cloud "P_SEV100"; #33 was a copy of Cloud's row).
- voice/EN/battle/voice_<KEY>_00.scd = SCD sound bank (attack shouts / grunts).
- voice/EN/voice_load_<KEY>.bin = "VOLD" list: u32 magic, u32 date, u32 count, u32 0, then count x 24-byte rows:
  char[16] clip name (e.g. "cl_battle_21"), u16 line id, u16 ?, u16 condition, u16 condition 2.
  Each clip = voice/EN/battle/<name>.at3 (spoken lines: intros, wins, taunts, ...).

This sets #33's key to P_SEV120, copies Cloud's bank and list under it, renames the list's "cl_battle_" clips to
"<PREFIX>_battle_" and adds copies of those .at3 files under the new names (to be replaced by Sora's lines).

Usage: python3 -I spot33_voice.py ISO [PREFIX]      (writes to ISO!  default PREFIX "so")
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, arc_chunk, mpk_member, package_entry, read_at  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402

OWNER, SRC_KEY, KEY = 33, b'P_SEV100', b'P_SEV120'


def pkg_file(f, info, path):
    off, size = package_entry(info, path)
    return read_at(f, PACKAGE_ISO_SECTOR * SECTOR + off, size)


def main():
    iso = sys.argv[1]
    prefix = (sys.argv[2] if len(sys.argv) > 2 else 'so').encode()
    assert len(prefix) == 2, 'prefix must be 2 letters (keeps names the same length)'
    with open(iso, 'r+b') as f:
        info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        off, _ = package_entry(info, 'general_archive/main/main.bin')
        sysbin, _ = mpk_member(f, PACKAGE_ISO_SECTOR * SECTOR + off, 'system.bin')
        chrp, _ = arc_chunk(f, sysbin, 'chrp')
        count, = struct.unpack('<I', read_at(f, chrp + 4, 4))
        for i in range(count):
            row = chrp + 8 + i * 144
            if read_at(f, row, 1)[0] == OWNER:
                name = read_at(f, row + 0x74, 8)
                if name == KEY:
                    print('chrp: owner 33 voice key already %s' % KEY.decode())
                else:
                    assert name == SRC_KEY, name
                    f.seek(row + 0x74)
                    f.write(KEY)
                    print('chrp: owner 33 voice key %s -> %s' % (name.decode(), KEY.decode()))
                break
        else:
            sys.exit('owner 33 not in chrp')
        src, dst = SRC_KEY.decode(), KEY.decode()
        bank = pkg_file(f, info, 'voice/EN/battle/voice_%s_00.scd' % src)
        vold = bytearray(pkg_file(f, info, 'voice/EN/voice_load_%s.bin' % src))
        assert vold[:4] == b'VOLD'
        n, = struct.unpack_from('<I', vold, 8)
        clips = []
        for i in range(n):
            name = bytes(vold[16 + i * 24:32 + i * 24]).split(b'\0')[0]
            if name.startswith(b'cl_battle_'):
                new = prefix + name[2:]
                vold[16 + i * 24:16 + i * 24 + len(new)] = new
                if new not in [c[1] for c in clips]:
                    clips.append((name, new))
        files = [('voice/EN/battle/voice_%s_00.scd' % dst, bank), ('voice/EN/voice_load_%s.bin' % dst, bytes(vold))]
        for old, new in clips:
            files.append(('voice/EN/battle/%s.at3' % new.decode(),
                          pkg_file(f, info, 'voice/EN/battle/%s.at3' % old.decode())))
    print('%d voice lines renamed cl_ -> %s_' % (len(clips), prefix.decode()))
    with tempfile.TemporaryDirectory() as tmp:
        for path, data in files:
            p = os.path.join(tmp, os.path.basename(path))
            open(p, 'wb').write(data)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                               check=True, capture_output=True, text=True)
        print('%d files put into the ISO (last: %s)' % (len(files), r.stdout.strip()))


if __name__ == '__main__':
    main()
