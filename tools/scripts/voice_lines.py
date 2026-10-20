"""Edit battle voice line lists (voice/EN/voice_load_<KEY>.bin, "VOLD") and their subtitles
(general_archive/field/EN/field_lang.bin -> battle_voice_name.bin, see voice_text.py) inside an ISO.

VOLD row (24 bytes): char[16] clip, u16 line id (= subtitle id), u16 moment (0x0046 battle start, 0x0146 win,
0x0246 loss), u16 condition, u16 value (see voice_catalog.py: 2 = vs owner, 6 = reply to line id, 5 = random ...).
Free line ids: 0..1205 (unused by the game).

Library use (see main() for the test-28 recipe):
  vl = VoiceISO(iso); rows = vl.rows('P_SEV120'); vl.set_rows('P_SEV120', rows); vl.subs[1000] = 'text'; vl.save()
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, package_entry, read_at  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402
import mpk  # noqa: E402
import voice_text  # noqa: E402

MOMENT = {'start': 0x0046, 'win': 0x0146, 'loss': 0x0246}
FIELD_LANG = 'general_archive/field/EN/field_lang.bin'


class VoiceISO:
    def __init__(self, iso):
        self.iso = iso
        self.f = open(iso, 'rb')
        self.info = read_at(self.f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
        self.changed = {}
        self.field_lang = self.file(FIELD_LANG)
        member = [(n, o, s) for n, o, s in mpk.entries(self.field_lang) if n == 'battle_voice_name.bin'][0]
        self.subs, self.sub_count = voice_text.decode(self.field_lang[member[1]:member[1] + member[2]])
        self.subs_orig = dict(self.subs)

    def file(self, path):
        off, size = package_entry(self.info, path)
        return read_at(self.f, PACKAGE_ISO_SECTOR * SECTOR + off, size)

    def rows(self, key):
        v = self.changed.get('voice/EN/voice_load_%s.bin' % key) or self.file('voice/EN/voice_load_%s.bin' % key)
        n, = struct.unpack_from('<I', v, 8)
        out = []
        for i in range(n):
            clip = v[16 + i * 24:32 + i * 24].split(b'\0')[0].decode('latin1')
            out.append([clip] + list(struct.unpack_from('<HHHH', v, 32 + i * 24)))
        return out

    def set_rows(self, key, rows):
        path = 'voice/EN/voice_load_%s.bin' % key
        v = self.changed.get(path) or self.file(path)
        body = b''.join(r[0].encode('latin1').ljust(16, b'\0') + struct.pack('<HHHH', *r[1:]) for r in rows)
        out = bytearray(v[:16]) + body
        struct.pack_into('<I', out, 8, len(rows))
        self.changed[path] = bytes(out)

    def save(self):
        if self.subs != self.subs_orig:
            d = self.field_lang
            entries = list(mpk.entries(d))
            new_sub = voice_text.encode(self.subs, self.sub_count)
            # rebuild the MPK: same names/order, members 16-aligned
            count, = struct.unpack_from('<I', d, 8)
            first = min(o for _, o, _ in entries)
            out = bytearray(d[:first])
            for i, (name, o, s) in enumerate(entries):
                data = new_sub if name == 'battle_voice_name.bin' else d[o:o + s]
                out += b'\0' * ((-len(out)) % 16)
                struct.pack_into('<II', out, 16 + i * 16 + 4, len(out), len(data))
                out += data
            out += b'\0' * ((-len(out)) % 16)
            self.changed[FIELD_LANG] = bytes(out)
        self.f.close()
        with tempfile.TemporaryDirectory() as tmp:
            for path, data in self.changed.items():
                p = os.path.join(tmp, os.path.basename(path))
                open(p, 'wb').write(data)
                r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), self.iso, path, p],
                                   check=True, capture_output=True, text=True)
                print(r.stdout.strip())


def test28(iso):
    """#33 gets its own line ids (1000+) with '[33] ' subtitles; Lightning gets a new vs-#33 line (id 1100);
    #33 gets a reply to it (id 1101)."""
    vl = VoiceISO(iso)
    rows = vl.rows('P_SEV120')
    remap = {}
    for r in rows:
        if r[1] >= 1206:
            remap.setdefault(r[1], 1000 + len(remap))
    for r in rows:
        old = r[1]
        if old in remap:
            r[1] = remap[old]
            vl.subs[r[1]] = '[33] ' + vl.subs_orig.get(old, '')
    rows.append(['so_battle_21', 1101, MOMENT['start'], 6, 1100])
    vl.subs[1101] = '[33 reply] Got it, Lightning!'
    vl.set_rows('P_SEV120', rows)
    li = vl.rows('P_GST130')
    li.append(['li_battle_93', 1100, MOMENT['start'], 2, 33])
    vl.subs[1100] = '[Lightning vs 33] A new face? Fine.'
    vl.set_rows('P_GST130', li)
    print('#33 rows: %d (ids %d-%d), Lightning rows: %d' % (len(rows), 1000, 999 + len(remap), len(li)))
    vl.save()


if __name__ == '__main__':
    if sys.argv[1] == 'test28':
        test28(sys.argv[2])
    else:
        sys.exit(__doc__)
