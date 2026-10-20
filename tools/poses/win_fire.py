"""Win pose "Fire" — "It's over!": he swings the Keyblade out to the side, twirls it (TWIRLS spins), then rests it on his
right shoulder with his left hand on his hip and a cocky head tilt. Axes: +Y up, +Z forward, +X = his left."""

TWIRLS = 3                                               # full spins of the Keyblade (Mat: three)


def build(P):
    start = P.kh2(0, 0)                                  # KH2 battle stance (same as his idle)
    stand = P.kh2(2, 0)                                  # KH2 relaxed standing pose

    out = stand.copy()                                   # Keyblade swung out to his right side
    out.aim('r_uparm', (-0.95, -0.15, 0.25))
    out.aim('r_foarm', (-0.9, 0.0, 0.45))
    out.aim_keyblade((-0.35, 0.1, 0.95))

    keys = [(0, start), (10, out)]
    # TWIRLS full spins of the Keyblade: the hand turns around the forearm in quarter turns, 4 frames each
    axis = out.world()['r_hand'][:3, 3] - out.world()['r_foarm'][:3, 3]
    for k in range(1, 4 * TWIRLS + 1):
        spin = out.copy()
        spin.turn('r_hand', axis, -90 * k)
        keys.append((10 + 4 * k, spin))
    end = 10 + 16 * TWIRLS                               # frame where the last spin finishes

    rest = stand.copy()                                  # Keyblade on the right shoulder
    rest.aim('r_uparm', (-0.55, -0.8, 0.3))              # elbow down at his side
    rest.aim('r_foarm', (0.05, 0.5, 0.85))               # fist forward at shoulder height
    rest.aim_keyblade((-0.15, -0.12, -1.0))              # blade lies back ON the shoulder (Mat: resting on it)
    rest.aim('l_uparm', (0.75, -0.55, -0.25))            # left hand on the hip: elbow out and a bit back,
    rest.aim('l_foarm', (-0.47, -0.85, 0.25))            # hand on the side of the waist (outside the body)
    rest.turn('head', (0, 0, 1), 8)                      # cocky head tilt
    rest.turn('chest', (0, 1, 0), -8)

    settle = rest.copy()
    settle.turn('head', (0, 0, 1), 3)
    keys += [(end + 14, rest), (end + 26, settle), (end + 104, settle)]
    return keys
