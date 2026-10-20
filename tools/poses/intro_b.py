"""Intro part 2 (_902A, 69 frames): rarely on screen (the battle starts right after _900A). _900A now ends ON the KH2
battle idle (its frame 150 = loop end), so this is simply the idle from frame 0 — no jump either way. LOOP: the last
48 frames loop."""

LOOP = 47


def build(P):
    idle = P.kh2_clip(0)                                 # KH2 battle idle, 151 frames (loops 150 -> 0)
    return [(k, idle[k]) for k in range(69)]
