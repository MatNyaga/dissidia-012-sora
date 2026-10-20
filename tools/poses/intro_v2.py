"""Intro (_900A, 80 frames = 2.7 s — the only intro part really on screen; the battle starts right after it).
Rewrite 2026-10-14 night (Mat: "the keyblade spin looks stiff and there are few animations to have him transition to
his battle stance"):
  0-11  Keyblade resting on his right shoulder, small relaxed bob, then lifts it off the shoulder
  11-16 swings it out to his right side (chest follows the swing)
  16-48 two Keyblade spins at CONSTANT speed (45-degree keys, 'lin' segments; the old quarter-turn keys each eased
        in and out, so the spin ticked) with the arm rising and falling a little and the chest counter-turning
  48-54 catches it and points the Keyblade at the foe
  54-69 drops into the KH2 battle stance in steps (half crouch, a small overshoot below the stance, settle)
  69-80 KH2's own battle idle, frames 139-150 = the end of its loop, so the fight's idle (frame 0) follows seamlessly
Axes: +Y up, +Z forward, +X = his left."""

import math

SPIN_TURNS = 2
STEP = 2                                                 # frames per 45 degrees of spin (2 turns = 32 frames)
END = 80                                                 # intro length (frames); ends on idle frame 150


def shoulder_rest(P):
    p = P.kh2(2, 0)                                      # KH2 relaxed standing pose
    p.aim('r_uparm', (-0.75, -0.45, 0.45))               # elbow out, fist at the front of the shoulder
    p.aim('r_foarm', (0.15, 0.95, -0.1))
    p.aim_keyblade((-0.3, 0.3, -0.9))                    # blade back over the shoulder
    p.aim('l_uparm', (0.35, -0.9, 0.1))
    p.aim('l_foarm', (0.2, -0.6, 0.75))
    return p


def build(P):
    rest = shoulder_rest(P)
    bob = rest.copy()                                    # weight shift: chest dips, head nods
    bob.turn('chest', (1, 0, 0), 4)
    bob.turn('head', (1, 0, 0), -5)
    bob.move_root(dy=-0.02)

    lift = rest.copy()                                   # Keyblade lifted off the shoulder, up and back
    lift.aim('r_uparm', (-0.8, 0.3, 0.2))
    lift.aim('r_foarm', (-0.2, 0.9, 0.2))
    lift.aim_keyblade((-0.2, 0.6, -0.75))
    lift.turn('chest', (0, 1, 0), 10)                    # winding up: chest turns to his right

    out = P.kh2(2, 0)                                    # Keyblade swung out to his right side
    out.aim('r_uparm', (-0.95, -0.15, 0.25))
    out.aim('r_foarm', (-0.9, 0.0, 0.45))
    out.aim_keyblade((-0.35, 0.1, 0.95))
    out.aim('l_uparm', (0.4, -0.85, 0.2))
    out.aim('l_foarm', (0.25, -0.5, 0.8))
    out.turn('chest', (0, 1, 0), -8)                     # follow-through of the swing

    keys = [(0, rest), (5, bob), (11, lift), (16, out)]
    axis = out.world()['r_hand'][:3, 3] - out.world()['r_foarm'][:3, 3]
    n = 8 * SPIN_TURNS
    for k in range(n + 1):                               # constant-speed spin, 45 degrees per key
        spin = out.copy()
        lift_arm = 0.12 * math.sin(3.14159 * k / n)   # arm rises a little mid-spin, then comes down
        spin.aim('r_uparm', (-0.95, -0.15 + lift_arm, 0.25))
        spin.aim('r_foarm', (-0.9, lift_arm, 0.45))
        spin.turn('r_hand', axis, -45 * k)
        spin.turn('chest', (0, 1, 0), 4 * math.sin(6.28318 * k / 8))   # small counter-turn per spin
        keys.append((16 + STEP * k, spin, 'lin') if k < n else (16 + STEP * k, spin))
    t = 16 + STEP * n                                    # = 48

    point = P.kh2(2, 0)                                  # catch: Keyblade pointed at the foe, left hand back
    point.aim('r_uparm', (-0.35, 0.0, 0.95))
    point.aim('r_foarm', (-0.15, 0.05, 1.0))
    point.aim_keyblade((-0.05, 0.12, 1.0))
    point.aim('l_uparm', (0.45, -0.85, -0.25))
    point.aim('l_foarm', (0.2, -0.75, -0.6))
    point.turn('chest', (0, 1, 0), 12)                   # right shoulder forward
    point.turn('head', (0, 1, 0), -6)

    idle = P.kh2_clip(0)                                 # KH2 battle idle, 151 frames (loops 150 -> 0)
    s0 = 150 - (END - (16 + STEP * 8 * SPIN_TURNS + 21))   # idle frame reached at the stance key
    stance = idle[s0]
    drop = point.copy()                                  # knees start to bend, Keyblade comes down and across
    drop.move_root(dy=-0.08)
    drop.aim('r_foarm', (-0.4, -0.2, 0.9))
    drop.aim_keyblade((-0.4, 0.0, 0.9))
    over = stance.copy()                                 # a little below the stance, then settle up into it
    over.move_root(dy=-0.03)
    over.turn('chest', (1, 0, 0), 3)

    keys += [(t + 6, point), (t + 11, drop), (t + 17, over), (t + 21, stance)]
    for k in range(1, 151 - s0):                         # KH2 breathing idle to the end of its loop
        keys.append((t + 21 + k, idle[s0 + k]))
    return keys                                          # last key = frame END = idle frame 150
