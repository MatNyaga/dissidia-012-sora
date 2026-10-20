"""Drive PPSSPP from boot (or any known menu) into a Quick Battle: #33 vs Lightning, 100% test save.
Each step first RECOGNISES the screen (64x36 grey thumbnail vs tools/scripts/screen_ref/*.png, made from real
screenshots) and only then presses the button for that screen. Unknown or forbidden screens (Extras, Data Install,
Story Mode) → stop and report, nothing pressed. Blind press lists once wandered into Data Install / Story Mode.

  [STOP_AFTER=screen] [EASY=1] [OPP=sora] [CLICK_UNKNOWN=1: from a battle's results → Rematch] python3 -I go_battle.py [OUT_DIR]   (PPSSPP must be running; pictures of each step go to OUT_DIR)
Exit 0 = in battle, 1 = stopped on an unknown/forbidden screen.
"""
import glob
import os
import subprocess
import sys
import time

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
REF = {os.path.basename(f)[:-4]: np.asarray(Image.open(f).convert('L'), float)
       for f in glob.glob(os.path.join(HERE, 'screen_ref', '*.png'))
       if not f.endswith('name_sora.png') and not os.path.basename(f).startswith('crop_')}
ACTIONS = {'autosave_notice': ['cross'], 'copyright': ['cross'], 'title': ['cross'], 'load_list': ['cross'], 'load_done': ['cross'],
           'main_story': ['down', 'cross'], 'battle_menu': ['cross'],
           'grid_lightning': ['down', 'down', 'down', 'right', 'right', 'right', 'right', 'right'],
           'grid_33': ['cross'], 'grid_33b': ['cross'], 'play_as_b': ['cross'], 'play_as': ['cross'], 'cpu_grid': ['cross'], 'cpu_confirm': ['cross'],
           'setup': ['cross'], 'setup_sora': ['cross'], 'vs': ['cross'], 'opp_info': ['cross'], 'results_menu': ['down', 'cross']}
FORBIDDEN = {'extras', 'data_install', 'story_menu'}
PLAYER_STAGE = {'grid_lightning': 'cpu_grid', 'grid_33': 'cpu_grid', 'grid_33b': 'cpu_grid', 'play_as': 'cpu_confirm',
                'play_as_b': 'cpu_confirm'}


def window():
    tree = subprocess.run(['xwininfo', '-root', '-tree'], capture_output=True, text=True).stdout
    return next(ln.split()[0] for ln in tree.splitlines() if 'duodecim' in ln.lower())


def shot(path):
    subprocess.run(['import', '-window', window(), '-resize', '50%', path], check=True,
                   env=dict(os.environ, DISPLAY=os.environ.get('DISPLAY', ':1')))
    return Image.open(path).convert('RGB')


def classify(img):
    t = np.asarray(img.resize((64, 36), Image.BILINEAR).convert('L'), float)
    d = sorted((np.abs(t - r).mean(), k) for k, r in REF.items())
    name, dist = d[0][1], d[0][0]
    if name in PLAYER_STAGE or name in PLAYER_STAGE.values():
        # Player Select label is blue, CPU Select label is pink (top-left, at 50% size)
        a = np.asarray(img, float)[62:95, 45:280]
        pink = a[..., 0].mean() > a[..., 2].mean()
        if pink and name in PLAYER_STAGE:
            name = PLAYER_STAGE[name]
        elif not pink and name in PLAYER_STAGE.values():
            name = {'cpu_grid': 'grid_lightning', 'cpu_confirm': 'play_as'}[name]
    return (name if dist < 22 else None), dist


NAME_SORA = np.asarray(Image.open(os.path.join(HERE, 'screen_ref', 'name_sora.png')).convert('L'), float)


def sora_selected(img):
    """the name area of the select screen (50% screenshot, box 290,110-520,155) shows "Sora" """
    a = np.asarray(img.convert('L').crop((290, 110, 520, 155)), float)
    return np.abs(a - NAME_SORA).mean() < 3      # Sora 0-0.2, Vaan 9, others 15-20


def press(btn):
    subprocess.run(['bash', os.path.join(HERE, 'pp.sh'), 'press', btn], check=True, capture_output=True)


# Setup screen rows (50% screenshot): value text of STAGE and STRENGTH (CPU). Mat 2026-10-15: test battles ALWAYS on
# Order's Sanctuary + CPU Minimal — PPSSPP restarts reset them, and blind presses gave hard CPUs and lost battles.
STAGE_BOX, STRENGTH_BOX = (330, 266, 670, 294), (390, 306, 610, 334)
CROP_STAGE, CROP_MIN = (os.path.join(HERE, 'screen_ref', n) for n in ('crop_stage_os.png', 'crop_strength_min.png'))


def crop_match(img, box, ref_path):
    """distance to the reference crop, plain row or highlighted row (cursor on it = white text on blue: *_hl.png)"""
    a = np.asarray(img.convert('L').crop(box), float)
    refs = [p for p in (ref_path, ref_path[:-4] + '_hl.png') if os.path.exists(p)]
    return min(np.abs(a - np.asarray(Image.open(p).convert('L'), float)).mean() for p in refs)


def easy_setup(out, step):
    """cursor on Enter Battle → STAGE right until Order's Sanctuary, STRENGTH left until Minimal, verify, enter"""
    if not (os.path.exists(CROP_STAGE) and os.path.exists(CROP_MIN)):
        img = shot(os.path.join(out, 'go_%02d_setup.png' % step))
        img.convert('L').crop(STAGE_BOX).save(os.path.join(out, 'crop_stage_now.png'))
        img.convert('L').crop(STRENGTH_BOX).save(os.path.join(out, 'crop_strength_now.png'))
        print('STOP: no setup reference crops yet (screen_ref/crop_*.png); current crops saved in', out)
        return False
    press('down')
    for k in range(37):
        img = shot(os.path.join(out, 'go_%02d_stage%02d.png' % (step, k)))
        if crop_match(img, STAGE_BOX, CROP_STAGE) < 4:
            break
        press('right')
        time.sleep(0.4)
    else:
        print('STOP: Order\'s Sanctuary not found')
        return False
    press('down')
    for k in range(10):
        img = shot(os.path.join(out, 'go_%02d_str%02d.png' % (step, k)))
        if crop_match(img, STRENGTH_BOX, CROP_MIN) < 4:
            break
        press('left')
        time.sleep(0.4)
    else:
        print('STOP: Minimal not found')
        return False
    press('up')
    press('up')
    time.sleep(0.5)
    img = shot(os.path.join(out, 'go_%02d_setup_ok.png' % step))
    ok = crop_match(img, STAGE_BOX, CROP_STAGE) < 4 and crop_match(img, STRENGTH_BOX, CROP_MIN) < 4
    print('setup: Order\'s Sanctuary + Minimal', 'OK' if ok else 'NOT OK')
    return ok


def seek_sora(out, step):
    # fast path: Sora is in the bottom row (6th of 7) — go down to it (down x3 stops / wraps), then walk right
    img = shot(os.path.join(out, 'go_%02d_seekA.png' % step))
    if sora_selected(img):
        return True
    for b in ('down', 'down', 'down'):
        press(b)
        time.sleep(0.3)
    for k in range(9):
        img = shot(os.path.join(out, 'go_%02d_seekB%02d.png' % (step, k)))
        if sora_selected(img):
            return True
        press('right')
        time.sleep(0.4)
    for k in range(60):                        # right wraps inside a row: 12 rights, then down a row
        img = shot(os.path.join(out, 'go_%02d_seek%02d.png' % (step, k)))
        if sora_selected(img):
            return True
        press('down' if k % 12 == 11 else 'right')
        time.sleep(0.6)
    return False


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, 'dumps/screens/go')
    os.makedirs(out, exist_ok=True)
    if os.environ.get('EASY'):        # setup screen: STAGE → Order's Sanctuary (right x11), STRENGTH → weakest (left x4)
        ACTIONS['setup'] = ['down'] + ['right'] * 11 + ['down'] + ['left'] * 4 + ['up', 'up', 'cross']
        # setup_sora (Sora vs CPU Sora, screen_ref saved AFTER the easy settings were made) = already easy: just enter
    unknown, entered, step = 0, False, 0
    while step < 60:
        step += 1
        img = shot(os.path.join(out, 'go_%02d.png' % step))
        name, dist = classify(img)
        print('%02d %-15s %.1f' % (step, name, dist), flush=True)
        if name in FORBIDDEN:
            print('STOP: forbidden screen %s (see %s/go_%02d.png)' % (name, out, step))
            return 1
        if name is None and os.environ.get('CLICK_UNKNOWN') and not entered:
            press('cross')                      # results pages ("Received PP", level up …) after a battle → next
            time.sleep(2.5)
            continue
        if name is None:
            unknown += 1
            if entered and unknown >= 3:
                print('in battle')
                return 0
            if unknown >= 12:
                print('STOP: unknown screen (see %s/go_%02d.png)' % (out, step))
                return 1
            time.sleep(2.5)
            continue
        unknown = 0
        if name in ('grid_33', 'grid_33b'):               # whole-screen match is not reliable on the grid
            name = 'grid_lightning'
        if name == os.environ.get('STOP_AT'):              # stop BEFORE pressing anything on this screen
            print('stopped at', name)
            return 0
        if name == 'cpu_grid' and os.environ.get('OPP') == 'sora':
            # CPU Sora barely attacks (Mat's tip) → better opponent for combo tests: seek #33 on the CPU grid too
            if not seek_sora(out, step):
                print('STOP: could not find #33 on the CPU grid')
                return 1
        if name == 'grid_lightning':
            # the grid cursor REMEMBERS the last pick (2026-10-13 it landed on Cloud of Darkness): walk right one cell
            # at a time until the screen shows #33 selected (grid_33/grid_33b), max 40 steps; never press X blindly
            found = seek_sora(out, step)
            if not found:
                print('STOP: could not find #33 on the grid')
                return 1
            name = 'grid_33b'
            if name == os.environ.get('STOP_AFTER') or os.environ.get('STOP_AFTER') == 'grid_lightning':
                print('stopped with #33 selected')
                return 0
        if name in ('setup', 'setup_sora') and not os.environ.get('ANY_SETTINGS'):
            if not easy_setup(out, step):
                return 1
            press('cross')                                  # Enter Battle
            time.sleep(2.5)
            continue
        for b in ACTIONS[name]:
            press(b)
            time.sleep(0.4)
        if name == os.environ.get('STOP_AFTER'):                 # e.g. STOP_AFTER=grid_lightning
            time.sleep(1.5)
            shot(os.path.join(out, 'go_%02d_stop.png' % step))
            print('stopped after', name)
            return 0
        if name == 'opp_info':
            entered = True
            time.sleep(12)
        time.sleep(2.5)
    return 1


if __name__ == '__main__':
    sys.exit(main())
