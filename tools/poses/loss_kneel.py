"""Loss pose (_911A, played on the LOSER on the results screen): hit, staggers, drops to one knee with the Keyblade
planted in the ground, head down, then keeps catching his breath (the breathing loops).
Axes: +Y up, +Z forward, +X = his left (right hand on -X)."""

LOOP = 40                                                # last 40 frames = one breath, repeated
HIP = 0.56                                               # hip height (m): right knee just on the floor


def kneel(P, lift=0.0, head=0.0):
    p = P.kh2(2, 0)                                      # start from his relaxed standing pose
    p.hip_height(HIP + lift)
    p.aim('r_femur', (-0.05, -1.0, 0.12))                # right knee on the ground
    p.aim('r_tibia', (0.0, 0.0, -1.0))                   # right shin lies flat back along the floor
    p.aim('r_foot', (0.0, 0.15, -1.0))                   # right foot flat behind him (toes not in the floor)
    p.aim('l_femur', (0.12, 0.56, 0.82))                 # left foot planted in front
    p.aim('l_tibia', (0.0, -1.0, 0.08))
    p.aim('l_foot', (0.0, -0.35, 0.95))
    p.turn('waist', (1, 0, 0), 6 - lift * 40)            # leaning forward a bit, tired
    p.turn('chest', (1, 0, 0), 10 - lift * 40)
    p.aim('r_uparm', (-0.3, -0.35, 0.88))                # right hand on the Keyblade, planted in front
    p.aim('r_foarm', (-0.1, -0.25, 0.96))
    p.aim_keyblade((-0.1, -0.7, 0.7))                    # at an angle, tip just touching the ground
    p.aim('l_uparm', (0.3, -0.55, 0.78))                 # left forearm resting on the left knee
    p.aim('l_foarm', (-0.15, -0.35, 0.92))
    p.turn('neck', (1, 0, 0), 18 + head)
    p.turn('head', (1, 0, 0), 14 + head)                 # head down
    return p


def build(P):
    start = P.kh2(0, 0)
    hit = P.kh2(42, 8)                                   # KH2 "hit from the front" reaction
    sag = kneel(P, lift=0.12, head=-10)                  # on the way down
    down = kneel(P)
    breathe = kneel(P, lift=0.015, head=-4)              # chest rises a little
    return [(0, start), (8, hit), (22, sag), (34, down), (50, down), (70, breathe), (90, down)]
