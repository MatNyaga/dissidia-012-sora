"""Intro (_900A, 80 frames = 2.7 s — the only intro part really on screen; the battle starts right after it).
v3 2026-10-14 night (Mat on the v2 GIF, tools/poses/intro_v2.py: "would be fine if his left hand was not just still and
he moved slower and he was breathing, let's try have his other hand point at the opponent while the keyblade is
spinning on the other hand, obviously lower because it would be heavier and him slanting in that direction"):
  body   always KH2's own breathing idles (field idle v2 -> battle idle), never one frozen frame; only the arms and
         Keyblade are posed on top (intro_opts.layered)
  0-16   Keyblade resting on his right shoulder, looks at the foe
  16-24  swings it off the shoulder, LOW at his right side (heavy), left hand comes up
  24-56  ONE slow constant-speed spin (4 frames per 45 degrees) at hip height while his LEFT hand points at the foe
         and he leans toward the foe
  56-62  catches it, left hand drops back
  62-80  settles into the KH2 battle stance (idle frames ending on 150 = the fight's idle start)
Axes: +Y up, +Z forward (= toward the foe), +X = his left."""
import importlib.util
import math
import os

_spec = importlib.util.spec_from_file_location('intro_opts', os.path.join(os.path.dirname(__file__), 'intro_opts.py'))
O = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(O)

STEP = 4                    # frames per 45 degrees of spin (slower)
LEAN = 4                    # degrees he leans forward (weight of the Keyblade) while it spins


def low_out(P):
    p = P.kh2(2, 0)                                      # Keyblade low at his right side, forearm forward/down
    p.aim('r_uparm', (-0.75, -0.62, 0.2))
    p.aim('r_foarm', (-0.55, -0.35, 0.75))
    p.aim_keyblade((-0.45, -0.05, 0.9))
    return p


def point_left(p, k=0):
    # Mat: "arm to the side … I mean beside him … and have his arm move a little": left arm hangs relaxed beside his
    # body, elbow soft, and swings gently (counter to the spin) — k = spin step 0..8
    sw = math.sin(math.pi * k / 4)
    p.aim('l_uparm', (0.22, -0.96, 0.08 + 0.10 * sw))
    p.aim('l_foarm', (0.12, -0.88, 0.40 + 0.12 * sw))
    return p


def build(P):
    rest = O.shoulder(P)
    look = rest.copy()
    look.turn('head', (0, 1, 0), -6)

    lift = rest.copy()
    lift.aim('r_uparm', (-0.8, 0.2, 0.25))
    lift.aim('r_foarm', (-0.3, 0.75, 0.55))
    lift.aim_keyblade((-0.3, 0.4, -0.85))

    out = point_left(low_out(P))
    axis = out.world()['r_hand'][:3, 3] - out.world()['r_foarm'][:3, 3]
    keys = [(0, rest), (10, look), (16, lift)]
    t0 = 24
    for k in range(9):                                   # one spin, constant speed, 45 degrees per key
        s = point_left(low_out(P), k)
        sway = 0.06 * math.sin(math.pi * k / 8)          # forearm dips a little with the weight mid-spin
        s.aim('r_foarm', (-0.55, -0.35 - sway, 0.75))
        s.turn('r_hand', axis, -45 * k)
        keys.append((t0 + STEP * k, s, 'lin') if k < 8 else (t0 + STEP * k, s))
    t = t0 + STEP * 8                                    # 56

    catch = O.pointing(P)                                # Keyblade caught, forward; left hand back down
    catch.aim('l_uparm', (0.4, -0.85, 0.05))
    catch.aim('l_foarm', (0.2, -0.65, 0.6))
    keys.append((t + 6, catch))
    frames = O.layered(P, keys, t + 6)                   # body: field idle (breathing) -> battle idle tail

    def lean_w(f):                                       # 0 -> 1 while he raises the hand, 1 -> 0 after the catch
        if f < 16 or f > t + 10:
            return 0.0
        if f < 26:
            return (f - 16) / 10.0
        if f > t:
            return 1 - (f - t) / 10.0
        return 1.0
    out_frames = []
    for f, p in frames:
        w = lean_w(f)
        if w > 0:
            e = w * w * (3 - 2 * w)
            p = p.copy()
            p.turn('waist', (1, 0, 0), LEAN * e)         # lean forward toward the foe
            p.turn('waist', (0, 0, 1), -3 * e)           # weight shifts onto the Keyblade side
        out_frames.append((f, p))
    return out_frames
