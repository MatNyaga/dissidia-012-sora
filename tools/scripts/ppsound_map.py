"""Map a fighter's sound-bank slots to moves: run with a "tones" bank (slot i = sine at 500 + 75*i Hz),
press a list of moves at logged times while recording the game's audio, then see which tones follow each move.

Usage: python3 -I ppsound_map.py PORT OUT_PREFIX          (in battle, nobody touching the controls)
       python3 -I ppsound_map.py analyze OUT_PREFIX
Writes OUT_PREFIX.wav (parec @DEFAULT_MONITOR@) and OUT_PREFIX.json (move -> time).
"""
import json
import subprocess
import sys
import time
import wave

BASE, STEP, SLOTS = 500, 75, 70
MOVES = [                                   # (label, [(button, frames, wait after)])
    ('idle', []),
    ('jump', [('cross', 12, 0)]),
    ('air bravery (jump+circle)', [('cross', 12, 0.35), ('circle', 12, 0)]),
    ('ground bravery (circle)', [('circle', 12, 0)]),
    ('ground bravery again', [('circle', 12, 0)]),
    ('ground HP (square)', [('square', 12, 0)]),
    ('air HP (jump+square)', [('cross', 12, 0.35), ('square', 12, 0)]),
    ('dash (triangle)', [('triangle', 12, 0)]),
    ('guard (R)', [('rtrigger', 12, 0)]),
]
GAP = 3.5


def run(port, prefix):
    import websocket
    ws = websocket.create_connection('ws://127.0.0.1:%s/debugger' % port, timeout=40, suppress_origin=True)
    rec = subprocess.Popen(['parec', '-d', '@DEFAULT_MONITOR@', '--format=s16le', '--rate=44100', '--channels=2',
                            '--file-format=wav', prefix + '.wav'])
    t0 = time.time()
    log = []
    time.sleep(1.5)
    for rnd in range(2):
        for label, seq in MOVES:
            log.append((label, round(time.time() - t0, 3)))
            for button, frames, after in seq:
                ws.send(json.dumps({'event': 'input.buttons.press', 'button': button, 'duration': frames}))
                time.sleep(after)
            time.sleep(GAP)
    time.sleep(1)
    rec.terminate()
    rec.wait()
    json.dump(log, open(prefix + '.json', 'w'), indent=1)
    print('recorded', len(log), 'moves')


def analyze(prefix):
    import numpy as np
    w = wave.open(prefix + '.wav')
    a = np.frombuffer(w.readframes(w.getnframes()), dtype='<i2').reshape(-1, 2).mean(1)
    sr, win, hop = w.getframerate(), 4096, 1024
    f = np.fft.rfftfreq(win, 1 / sr)
    frames = []
    for i in range(0, len(a) - win, hop):
        X = np.abs(np.fft.rfft(a[i:i + win] * np.hanning(win)))
        frames.append(X)
    frames = np.array(frames)
    times = np.arange(len(frames)) * hop / sr
    bins = [int(round((BASE + STEP * s) * win / sr)) for s in range(SLOTS)]
    # tone present = bin clearly above its neighbours (+-3 bins away) and above the frame median
    hits = np.zeros((len(frames), SLOTS), bool)
    for s, b in enumerate(bins):
        peak = frames[:, b - 1:b + 2].max(1)
        side = np.maximum(frames[:, b - 6:b - 3].mean(1), frames[:, b + 4:b + 7].mean(1)) + 1
        med = np.median(frames[:, 10:600], axis=1) + 1
        hits[:, s] = (peak > 6 * side) & (peak > 20 * med)
    # need 3 consecutive frames
    sus = hits[:-2] & hits[1:-1] & hits[2:]
    log = json.load(open(prefix + '.json'))
    for k, (label, t) in enumerate(log):
        t_end = log[k + 1][1] if k + 1 < len(log) else times[-1]
        sel = (times[:-2] >= t) & (times[:-2] < t_end)
        slots = [s for s in range(SLOTS) if sus[sel, s].any()]
        print('%-28s t=%5.1f  slots %s' % (label, t, slots))


if __name__ == '__main__':
    if sys.argv[1] == 'analyze':
        analyze(sys.argv[2])
    else:
        run(sys.argv[1], sys.argv[2])
        analyze(sys.argv[2])
