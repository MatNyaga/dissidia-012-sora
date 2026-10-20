"""Win pose (_910A): KH2's Fire spell finisher (normal speed, then slow motion), then he swings the Keyblade out,
twirls it and rests it on his right shoulder, left hand on the hip, cocky head tilt (= win_fire.py's ending)."""
import importlib.util
import os

_spec = importlib.util.spec_from_file_location('win_fire', os.path.join(os.path.dirname(__file__), 'win_fire.py'))
win_fire = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(win_fire)


def build(P):
    clip = P.kh2_clip(228, '_v0.5x1_1x0.4')              # Fire finisher: normal first half, slow-mo second half
    keys = [(f, p) for f, p in enumerate(clip)]
    t = len(clip) - 1 + 8                                # small pause after the slow-mo, then the twirl
    fire_keys = win_fire.build(P)                        # [(0, start), (10, out), twirl…, (40, rest), (52, settle), (130, settle)]
    for f, p in fire_keys[1:]:
        keys.append((t + f - 10, p))
    return keys
