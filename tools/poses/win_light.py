"""Win pose "Light" — "Give me strength!": from his battle stance he stands up and raises the Keyblade to the sky,
looks up at it, holds. Axes: +Y up, +Z forward, +X = Sora's left (right hand on -X)."""


def build(P):
    start = P.kh2(0, 0)                                  # KH2 battle stance (same as his idle)

    stand = P.kh2(2, 0)                                  # KH2 relaxed standing pose
    up = stand.copy()
    up.aim('r_uparm', (-0.25, 1.0, 0.12))                # right arm straight up
    up.aim('r_foarm', (-0.12, 1.0, 0.10))
    up.aim_keyblade((0.0, 1.0, 0.18))                    # Keyblade to the sky
    up.aim('l_uparm', (0.35, -0.9, 0.15))                # left arm down, a bit out
    up.aim('l_foarm', (0.25, -0.8, 0.45))
    up.turn('chest', (1, 0, 0), -8)                      # lean back a little
    up.turn('head', (1, 0, 0), -22)                      # look up at the Keyblade

    high = up.copy()
    high.aim('r_foarm', (-0.05, 1.0, 0.05))
    high.aim_keyblade((0.0, 1.0, 0.08))
    high.turn('head', (1, 0, 0), -6)

    return [(0, start), (18, up), (30, high), (150, high)]
