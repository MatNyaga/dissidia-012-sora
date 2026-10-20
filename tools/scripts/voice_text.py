"""Battle voice subtitles: general_archive/field/EN/field_lang.bin (MPK) -> battle_voice_name.bin.

Format (cracked 2026-10-12 by comparing the disc file with the decoded copy in RAM):
  "OFF4", u32 count (3261 = one per voice line id; ids 0..1205 unused),
  count x u32 offset in 4-byte units from file start (0 = no subtitle),
  entries: u32 byte length (UTF-16LE text + NUL, padded to 4), then the text, XOR-scrambled:
  byte j of the text of line id L ^= KEY[(2*L + 20 + j) % 32]. Length fields are not scrambled.
  (In the original file ids 1206..3260 are all used, so "2*k from file order" fits too — but the game uses the
  id: test 28 with new low ids showed garbage subtitles when encoded by file order. Mat spotted it, 2026-10-12.)

Usage:
  python3 -I voice_text.py dump FILE.bin                    (FILE = battle_voice_name.bin)
  python3 -I voice_text.py set FILE.bin OUT.bin ID=TEXT ...  (new or replaced subtitles; ids must be < count)
Library: decode(bytes) -> {id: text}; encode({id: text}, count) -> bytes.
"""
import struct
import sys

KEY = bytes.fromhex('57a6bfc833009a5727f24c4ba7367d929d73ce8498edab90285e4284b132da2d')


def decode(d):
    assert d[:4] == b'OFF4', 'not an OFF4 table'
    n, = struct.unpack_from('<I', d, 4)
    offs = struct.unpack_from('<%dI' % n, d, 8)
    out = {}
    for lid, o in enumerate(offs):
        if not o:
            continue
        p = o * 4
        ln, = struct.unpack_from('<I', d, p)
        raw = bytes(c ^ KEY[(2 * lid + 20 + j) % 32] for j, c in enumerate(d[p + 4:p + 4 + ln]))
        out[lid] = raw.decode('utf-16-le').split('\0')[0]
    return out, n


def encode(texts, count):
    head = 8 + 4 * count
    offs = [0] * count
    body = bytearray()
    for lid in sorted(texts):
        raw = texts[lid].encode('utf-16-le') + b'\0\0'
        raw += b'\0' * ((-len(raw)) % 4)
        offs[lid] = (head + len(body)) // 4
        body += struct.pack('<I', len(raw)) + bytes(c ^ KEY[(2 * lid + 20 + j) % 32] for j, c in enumerate(raw))
    return b'OFF4' + struct.pack('<I', count) + struct.pack('<%dI' % count, *offs) + bytes(body)


def main():
    cmd, path = sys.argv[1], sys.argv[2]
    texts, n = decode(open(path, 'rb').read())
    if cmd == 'dump':
        for lid in sorted(texts):
            print('%d\t%s' % (lid, texts[lid].replace('\n', '\\n')))
    elif cmd == 'set':
        for a in sys.argv[4:]:
            lid, _, t = a.partition('=')
            texts[int(lid)] = t
        open(sys.argv[3], 'wb').write(encode(texts, n))
    else:
        sys.exit(__doc__)


if __name__ == '__main__':
    main()
