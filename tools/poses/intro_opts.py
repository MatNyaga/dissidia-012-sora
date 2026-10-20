"""Intro OPTIONS for Mat to pick from (2026-10-14 night; Mat: "the animations are not smooth e.g look at how he is
standing. He looks too stiff, maybe create a bunch of gifs and I can give you direction").
Pick with env INTRO_VAR (default 'alive'); build_sora.sh / preview_pose.sh pass the env through.

Why the old intro looked stiff: every standing pose was ONE frozen KH2 frame (P.kh2(2, 0)), so hips, chest and head
never moved. Here the BODY always runs on KH2's own living idles (field idle v2 = index 2, battle idle = index 0)
and only the arms + Keyblade are hand-posed on top (layered per frame). Every option is 80 frames and ends on the
battle idle's loop end (frame 150), so the fight's idle follows without a jump.

  alive      the current choreography (shoulder rest, scratch, swing, 2 spins, point, drop) on the living body
  cocky      Keyblade on the shoulder, looks the foe over, then one smooth arc down into the stance (no spin)
  onespin    shoulder rest, swing out, ONE slower spin, point at the foe, drop into the stance
  call       KH2's own CALL_FRIEND motion (Keyblade raised), then into the stance
  land       KH2's own fall + landing (drops in from above), then the stance
  form       KH2's own Drive-Form power-up start (Keyblade raised, head back), then the stance
"""
import math
import os

END = 80
ARM = {'l_clavicle', 'l_uparm_c', 'l_uparm', 'l_arm_help', 'l_foarm', 'l_hand', 'l_fing1a', 'l_fing3b',
       'r_clavicle', 'r_uparm_c', 'r_uparm', 'r_arm_help', 'r_foarm', 'r_hand', 'r_fing1a', 'r_fing3b',
       'r_wep', 'wep0', 'wep1'}


def stance_tail(P, start):
    """battle idle frames so that frame END = idle frame 150"""
    idle = P.kh2_clip(0)
    s0 = 150 - (END - start)
    return [(start + k, idle[s0 + k]) for k in range(END - start + 1)]


def layered(P, arm_keys, drop_at):
    """body = KH2 field idle (living) until drop_at, blended into the battle idle; arms = arm_keys until drop_at"""
    field = P.kh2_clip(2)                                # KH2 relaxed idle, 91 frames
    tail = stance_tail(P, drop_at + 12)
    body_keys = [(f, field[f % len(field)]) for f in range(drop_at + 1)] + tail
    body = P.interpolate(body_keys)
    arms = P.interpolate(arm_keys + tail)
    out = []
    for f in range(END + 1):
        loc = dict(body[f])
        if f <= drop_at + 12:
            for n in ARM:
                if n in arms[f]:
                    loc[n] = arms[f][n]
        out.append((f, P.Pose(loc)))
    return out


def shoulder(P):
    p = P.kh2(2, 0)
    p.aim('r_uparm', (-0.75, -0.45, 0.45))
    p.aim('r_foarm', (0.15, 0.95, -0.1))
    p.aim_keyblade((-0.3, 0.3, -0.9))
    p.aim('l_uparm', (0.25, -0.95, 0.05))
    p.aim('l_foarm', (0.1, -0.7, 0.6))
    return p


def swung_out(P):
    p = P.kh2(2, 0)
    p.aim('r_uparm', (-0.95, -0.15, 0.25))
    p.aim('r_foarm', (-0.9, 0.0, 0.45))
    p.aim_keyblade((-0.35, 0.1, 0.95))
    p.aim('l_uparm', (0.4, -0.85, 0.2))
    p.aim('l_foarm', (0.25, -0.5, 0.8))
    return p


def pointing(P):
    p = P.kh2(2, 0)
    p.aim('r_uparm', (-0.35, 0.0, 0.95))
    p.aim('r_foarm', (-0.15, 0.05, 1.0))
    p.aim_keyblade((-0.05, 0.12, 1.0))
    p.aim('l_uparm', (0.45, -0.85, -0.25))
    p.aim('l_foarm', (0.2, -0.75, -0.6))
    return p


def spins(P, start, turns, step):
    out = swung_out(P)
    axis = out.world()['r_hand'][:3, 3] - out.world()['r_foarm'][:3, 3]
    n = 8 * turns
    keys = []
    for k in range(n + 1):
        s = out.copy()
        up = 0.12 * math.sin(math.pi * k / n)
        s.aim('r_uparm', (-0.95, -0.15 + up, 0.25))
        s.aim('r_foarm', (-0.9, up, 0.45))
        s.turn('r_hand', axis, -45 * k)
        keys.append((start + step * k, s, 'lin') if k < n else (start + step * k, s))
    return keys, start + step * n


def v_alive(P):
    rest = shoulder(P)
    scratch = rest.copy()
    scratch.aim('l_uparm', (0.6, 0.65, -0.1))
    scratch.aim('l_foarm', (-0.95, 0.1, -0.25))
    scratch2 = scratch.copy()
    scratch2.turn('l_foarm', (0, 0, 1), 12)
    keys = [(0, rest), (6, scratch), (10, scratch2), (14, scratch), (18, rest)]
    sk, t = spins(P, 24, 2, 2)
    keys += [(22, swung_out(P))] + sk + [(t + 6, pointing(P))]
    return layered(P, keys, t + 8)


def v_cocky(P):
    rest = shoulder(P)
    look = rest.copy()
    look.turn('head', (0, 1, 0), -10)
    look.turn('head', (0, 0, 1), 6)
    down = P.kh2(2, 0)                                   # arc down: blade sweeps from the shoulder past his side
    down.aim('r_uparm', (-0.7, -0.6, 0.35))
    down.aim('r_foarm', (-0.6, -0.4, 0.7))
    down.aim_keyblade((-0.6, -0.2, 0.75))
    keys = [(0, rest), (14, look), (34, look), (46, down)]
    return layered(P, keys, 48)


def v_onespin(P):
    rest = shoulder(P)
    keys = [(0, rest), (12, rest), (18, swung_out(P))]
    sk, t = spins(P, 20, 1, 3)
    keys += sk + [(t + 7, pointing(P))]
    return layered(P, keys, t + 10)


def clip_then_stance(P, index, frm, to, speed=1.0, lead=0):
    """KH2 clip frames frm..to (whole body) after `lead` frames of field idle, then into the battle stance"""
    clip = P.kh2_clip(index)
    field = P.kh2_clip(2)
    keys = [(f, field[f]) for f in range(lead)]
    n = int((to - frm) / speed)
    for k in range(n + 1):
        keys.append((lead + k, clip[min(to, frm + int(k * speed))]))
    return P.interpolate(keys + stance_tail(P, lead + n + 12))


def build(P):
    var = os.environ.get('INTRO_VAR', 'alive')
    if var == 'call':
        frames = clip_then_stance(P, 550, 0, 22, 0.6, lead=10)
    elif var == 'land':
        fall, land = P.kh2_clip(18), P.kh2_clip(22)
        keys = [(k, fall[k % len(fall)]) for k in range(10)] + [(10 + k, land[k]) for k in range(min(40, len(land)))]
        frames = P.interpolate(keys + stance_tail(P, 10 + 40 + 10))
    elif var == 'form':
        frames = clip_then_stance(P, 210, 0, 30, 0.8, lead=8)
    else:
        return {'alive': v_alive, 'cocky': v_cocky, 'onespin': v_onespin}[var](P)
    return [(f, P.Pose(frames[f])) for f in range(len(frames))]
