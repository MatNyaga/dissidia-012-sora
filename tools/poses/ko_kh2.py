"""KO pose (_404A = motions 703/704; was still Cloud's stagger-then-collapse). Mat 2026-10-15: "use the standard KH2
[pose] when he is dead before the continue screen". KH2 has no separate death clip: Sora is blown back (A210, KH2 66)
and drops to the ground (A211, KH2 70, frames 14-22 = falling to his lowest point, knee + hand down), and stays there.
Natural speed, then the lowest pose is held to the end of the slot (51 frames, Cloud's length)."""

END = 50


def build(P):
    blow = P.kh2_clip(66)                                # 15 frames
    land = P.kh2_clip(70)
    keys = [(f, p) for f, p in enumerate(blow)]
    t = len(blow)
    for k, f in enumerate(range(14, 23)):
        keys.append((t + k, land[f]))
    keys.append((END, land[22]))                         # stay down
    return keys
