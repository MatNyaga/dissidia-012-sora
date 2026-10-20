"""Offline speech-to-text for a folder of WAVs (faster-whisper small.en from tools/pylib-stt, model in tools/stt-models).

  python3 -I transcribe.py DIR OUT.tsv
"""
import glob
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'pylib-stt'))
from faster_whisper import WhisperModel  # noqa: E402

model = WhisperModel('small.en', device='cpu', compute_type='int8', download_root=os.path.join(HERE, '..', 'stt-models'))
with open(sys.argv[2], 'w') as out:
    out.write('file\ttext\n')
    for wav in sorted(glob.glob(os.path.join(sys.argv[1], '*.wav'))):
        segs, _ = model.transcribe(wav, language='en', beam_size=5, vad_filter=False)
        text = ' '.join(s.text.strip() for s in segs)
        out.write('%s\t%s\n' % (os.path.basename(wav), text))
        out.flush()
        print(os.path.basename(wav), '|', text)
