"""Sora's spoken battle lines (intro / win / loss) for #33: new .at3 clips + subtitles, from a map file.

Map file lines:  CLIP  WAV  SUBTITLE...
  CLIP = #33's clip name (so_battle_NN, see `voice_lines.py` rows of P_SEV120), WAV = any WAV (KH2 voice),
  SUBTITLE = text shown for every line id that plays this clip ('-' = keep). '#' starts a comment.
  Optional row edit:  @LINE_ID CLIP   = point line id LINE_ID's rows at CLIP (e.g. away from Cloud's shared
  UP09_* clips) and give it CLIP's subtitle.
Each WAV -> mono 44.1 kHz -> ATRAC3 (tools/atracdenc, ATRAC3_MONO=1) -> voice/EN/battle/CLIP.at3 (pkg_put).

  python3 -I spot33_lines.py ISO MAP.txt
"""
import os
import shlex
import struct
import subprocess
import sys
import tempfile
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from voice_lines import VoiceISO  # noqa: E402

ENC = os.path.join(ROOT, 'tools/atracdenc/atracdenc')
KEY = 'P_SEV120'


def at3(wav, out):
    """WAV -> mono ATRAC3 .at3 the PSP accepts. sceAtrac skips the first 1093 samples (codec delay + 1024) and
    rejects a file (SCE_ERROR_ATRAC_BAD_CODEC_PARAMS, test 80: every new clip failed and the whole intro/win
    dialogue went silent) when fact end-sample + 1093 > frames * 1024. atracdenc writes end = frames * 1024, so:
    pad 2048 samples of silence at the end, then write the real sample count into the fact chunk (like Sony's)."""
    with tempfile.TemporaryDirectory() as t:
        mono = os.path.join(t, 'm.wav')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', wav, '-ac', '1', '-ar', '44100',
                        '-sample_fmt', 's16', mono], check=True)
        with wave.open(mono) as w:
            n = w.getnframes()
        padded = os.path.join(t, 'p.wav')
        subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-i', mono, '-af', 'apad=pad_len=2048',
                        '-ac', '1', '-ar', '44100', '-sample_fmt', 's16', padded], check=True)
        subprocess.run([ENC, '-e', 'atrac3', '--container', 'riff', '-i', padded, '-o', out], check=True,
                       capture_output=True, env=dict(os.environ, ATRAC3_MONO='1'))
    d = bytearray(open(out, 'rb').read())
    fa = d.index(b'fact')
    data = d.index(b'data')
    frames = struct.unpack_from('<I', d, data + 4)[0] // 192
    assert n + 1093 <= frames * 1024, (n, frames)
    struct.pack_into('<I', d, fa + 8, n)
    open(out, 'wb').write(bytes(d))

def main():
    iso, mapf = sys.argv[1:3]
    clips, moves, subs_only = {}, [], []
    for ln in open(mapf):
        ln = ln.split('#')[0].strip()
        if not ln:
            continue
        if ln.startswith('!'):                            # !LINE_ID text = just set that subtitle (other characters)
            lid, txt = ln[1:].split(None, 1)
            subs_only.append((int(lid), txt.strip()))
            continue
        if ln.startswith('@'):
            lid, clip = ln[1:].split()
            moves.append((int(lid), clip))
            continue
        clip, wav, sub = ln.split(None, 2)
        clips[clip] = (os.path.join(ROOT, wav), sub.strip())
    vl = VoiceISO(iso)
    rows = vl.rows(KEY)
    for lid, clip in moves:
        for r in rows:
            if r[1] == lid:
                r[0] = clip
    vl.set_rows(KEY, rows)
    for r in rows:
        if r[0] in clips and clips[r[0]][1] != '-':
            vl.subs[r[1]] = clips[r[0]][1]
    for lid, txt in subs_only:
        vl.subs[lid] = txt
    vl.save()
    with tempfile.TemporaryDirectory() as t:
        for clip, (wav, sub) in clips.items():
            out = os.path.join(t, clip + '.at3')
            at3(wav, out)
            r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso,
                                'voice/EN/battle/%s.at3' % clip, out], check=True, capture_output=True, text=True)
            print(clip, '<-', os.path.basename(wav), shlex.quote(sub), '|', r.stdout.strip().split(':')[-1].strip())


if __name__ == '__main__':
    main()
