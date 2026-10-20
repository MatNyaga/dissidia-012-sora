"""Catalogue every fighter's battle voice lines: when they play (from voice_load_<KEY>.bin) + what is said.

What is said = the game's own subtitle: general_archive/field/EN/field_lang.bin (MPK) -> battle_voice_name.bin
(format + XOR key: tools/scripts/voice_text.py). Line ids 0..1205 are unused.
Optional speech-to-text (--stt) only for clips without a subtitle.

Usage: python3 -I voice_catalog.py ISO OUT_DIR [--stt]
  OUT_DIR/wav/<clip>.wav    16 kHz mono copies (for listening)
  OUT_DIR/voice_lines.csv   one row per list entry
  OUT_DIR/voice_lines.md    the same, grouped per fighter
Speech-to-text: faster-whisper from tools/pylib-stt (offline; model cached under tools/stt-models).

VOLD row = char[16] clip, u16 line id, u16 moment (high byte: 0 battle start, 1 win, 2 loss; low byte 0x46),
u16 condition, u16 value. Conditions (2026-10-12, from patterns across all fighters):
  0 = general line (value = how hard the fight is, see GENERAL)   5 = general, random pick
  2 = vs a specific opponent (value = owner)    6 = reply to another fighter's line (value = that line id)
  8 = team battle (value 0 first fight, 1 next, 2 later)    7 = another special mode (value 0/1; to confirm)
"""
import csv
import os
import struct
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from ablt_patch import PACKAGE_ISO_SECTOR, SECTOR, arc_chunk, mpk_member, package_entry, read_at  # noqa: E402
from pkg_put import PACKAGE_INFO_ISO_SECTOR  # noqa: E402

NAMES = {1: 'Warrior of Light', 2: 'Garland', 3: 'Firion', 4: 'Emperor', 5: 'Onion Knight', 6: 'Cloud of Darkness',
         7: 'Cecil', 8: 'Golbez', 9: 'Bartz', 10: 'Exdeath', 11: 'Terra', 12: 'Kefka', 13: 'Cloud', 14: 'Sephiroth',
         15: 'Squall', 16: 'Ultimecia', 17: 'Zidane', 18: 'Kuja', 19: 'Tidus', 20: 'Jecht', 21: 'Shantotto',
         22: 'Gabranth', 23: 'Chaos', 24: 'Kain', 25: 'Gilgamesh', 26: 'Tifa', 27: 'Laguna', 28: 'Yuna', 29: 'Vaan',
         30: 'Prishe', 31: 'Lightning', 32: 'Feral Chaos', 33: '#33 (Sora slot)'}
MOMENT = {0: 'battle start', 1: 'win', 2: 'loss'}


GENERAL = {  # (moment, value) for condition 0 — names guessed from the lines themselves (2026-10-12)
    ('battle start', 0): 'general', ('battle start', 2): 'general, tough opponent',
    ('battle start', 3): 'general, very tough opponent', ('win', 0): 'easy win', ('win', 1): 'win, foe was careless',
    ('win', 2): 'win vs tough opponent', ('win', 3): 'close win', ('loss', 0): 'loss to a weaker foe',
    ('loss', 2): 'loss to a stronger foe'}


def condition(c, v, lid_owner, moment=''):
    if c == 2:
        return 'vs %s' % NAMES.get(v, v)
    if c == 6:
        o = lid_owner.get(v)
        return 'reply to line %d (%s)' % (v, NAMES.get(o[0], '?') + ' ' + o[1] if o else '?')
    if c == 5:
        return 'general (random)'
    if c == 0:
        return GENERAL.get((moment, v), 'general [value %d]' % v)
    if c == 8:
        return 'team battle' + ['', ', next fight', ', later fight'][v] if v < 3 else 'team battle [%d]' % v
    return 'cond %d value %d' % (c, v)


def read_subtitles(f, mpk_at):
    from voice_text import decode
    data, size = mpk_member(f, mpk_at, 'battle_voice_name.bin')
    texts, _ = decode(read_at(f, data, size))
    return {k: v.replace('\n', ' ') for k, v in texts.items()}


def main():
    iso, out = sys.argv[1], sys.argv[2]
    stt = '--stt' in sys.argv
    os.makedirs(os.path.join(out, 'wav'), exist_ok=True)
    f = open(iso, 'rb')
    info = read_at(f, PACKAGE_INFO_ISO_SECTOR * SECTOR, 0x21000)
    pkg = PACKAGE_ISO_SECTOR * SECTOR
    off, _ = package_entry(info, 'general_archive/main/main.bin')
    sysbin, _ = mpk_member(f, pkg + off, 'system.bin')
    chrp, _ = arc_chunk(f, sysbin, 'chrp')
    count, = struct.unpack('<I', read_at(f, chrp + 4, 4))
    keys = {}
    for i in range(count):
        row = read_at(f, chrp + 8 + i * 144, 144)
        keys[row[0]] = row[0x74:0x7C].decode('latin1')
    rows = []
    for owner, key in sorted(keys.items()):
        try:
            off, size = package_entry(info, 'voice/EN/voice_load_%s.bin' % key)
        except KeyError:
            continue
        v = read_at(f, pkg + off, size)
        n, = struct.unpack_from('<I', v, 8)
        for i in range(n):
            clip = v[16 + i * 24:32 + i * 24].split(b'\0')[0].decode('latin1')
            lid, moment, c, val = struct.unpack_from('<HHHH', v, 32 + i * 24)
            rows.append(dict(owner=owner, fighter=NAMES.get(owner, owner), clip=clip, line_id=lid,
                             moment=MOMENT.get(moment >> 8, moment), cond=c, value=val))
    lid_owner = {r['line_id']: (r['owner'], r['clip']) for r in rows}
    off, _ = package_entry(info, 'general_archive/field/EN/field_lang.bin')
    subs = read_subtitles(f, pkg + off)
    clips = sorted({r['clip'] for r in rows})
    for clip in clips:
        wav = os.path.join(out, 'wav', clip + '.wav')
        if os.path.exists(wav):
            continue
        try:
            off, size = package_entry(info, 'voice/EN/battle/%s.at3' % clip)
        except KeyError:
            continue
        p = os.path.join(out, 'wav', clip + '.at3')
        open(p, 'wb').write(read_at(f, pkg + off, size))
        subprocess.run(['ffmpeg', '-loglevel', 'error', '-y', '-i', p, '-ac', '1', '-ar', '16000', wav], check=True)
        os.remove(p)
    text = {}
    cache = os.path.join(out, 'transcripts.tsv')
    if os.path.exists(cache):
        for line in open(cache, encoding='utf-8'):
            k, _, t = line.rstrip('\n').partition('\t')
            text[k] = t
    if stt:
        sys.path.insert(0, os.path.join(HERE, '..', 'pylib-stt'))
        from faster_whisper import WhisperModel
        model = WhisperModel('small.en', device='cpu', compute_type='int8',
                             download_root=os.path.join(HERE, '..', 'stt-models'))
        with open(cache, 'a', encoding='utf-8') as log:
            for k, clip in enumerate(clips):
                wav = os.path.join(out, 'wav', clip + '.wav')
                if clip in text or not os.path.exists(wav):
                    continue
                segs, _ = model.transcribe(wav, language='en', beam_size=5, vad_filter=False)
                text[clip] = ' '.join(s.text.strip() for s in segs)
                log.write('%s\t%s\n' % (clip, text[clip]))
                log.flush()
                if k % 50 == 0:
                    print('%d/%d %s: %s' % (k, len(clips), clip, text[clip]), flush=True)
    for r in rows:
        r['when'] = condition(r['cond'], r['value'], lid_owner, r['moment'])
        r['text'] = subs.get(r['line_id']) or ('(heard) ' + text[r['clip']] if text.get(r['clip']) else '')
    cols = ['owner', 'fighter', 'clip', 'line_id', 'moment', 'when', 'cond', 'value', 'text']
    with open(os.path.join(out, 'voice_lines.csv'), 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, cols, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    with open(os.path.join(out, 'voice_lines.md'), 'w', encoding='utf-8') as fh:
        fh.write('# Dissidia 012 battle voice lines (text = the game\'s own subtitles)\n')
        last = None
        for r in rows:
            if r['owner'] != last:
                fh.write('\n## %d %s\n\n| clip | id | moment | when | text |\n|---|---|---|---|---|\n'
                         % (r['owner'], r['fighter']))
                last = r['owner']
            fh.write('| %s | %d | %s | %s | %s |\n' % (r['clip'], r['line_id'], r['moment'], r['when'], r['text']))
    print('rows', len(rows), 'clips', len(clips), 'with subtitle', sum(1 for r in rows if r['line_id'] in subs))


if __name__ == '__main__':
    main()
