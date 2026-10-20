"""Mat's approved voice lines (Codex package codex/inbox/20261018-approved-voices) on a TEST disc:
1. every playable speaker's battle-opening line against Sora (VOLD row: moment 0x0046, condition 2, value 33),
2. Sora's mirror line (Sora vs Sora: Sora's own VOLD row condition 2 value 33),
3. Sora as a TITLE CALLER ("Square Enix presents" half + "Dissidia Duodecim" half) on days 25 and 29,
4. (test340) Sora's OWN matchup lines ("Sora vs <opponent>", speaker 33): Sora's existing vs-<opponent> row (a
   generic KH2 clip, ids 1015..1046, cloned from Cloud's list) is re-pointed to so_vs_<opp>, id 1150 + opponent
   owner -> still one cond-2 row per opponent (native pattern); the KH2 clips stay for the general intros.
   Opponent owners come from SPEAKERS (manifest Vaan/Prishe owners are swapped, see below), not the manifest.
   Kain (owner 24, P_FOR110) now approved -> speaker line like the others.
   Tidus's vs-Sora id moved 1129 -> 1144: every fighter (Sora too) has a native reply row cond 6 value 1129
   (a line no chrp list owns), so Sora answered Tidus with the stray "Don't worry, we'll take care of them."
notes/voice-and-sound.md "Approved voices vs Sora (test337)" + "test340".

How the game picks a battle-start line (battle overlay FUN_08b00b2c, from FUN_08b0e40c via FUN_08b0d7f4):
the fighter's OWN loose list voice/EN/voice_load_<chrp+0x74 key>.bin (loaded to fighter+0xd4) is searched for
rows with the wanted (moment, condition, value) — up to 8 matches, random pick. Reply (cond 6 = the other line's
id) is tried first when the caller passes a line id; team/series modes use cond 8/7; otherwise, when the battle's
encounter (encounter/*.enc +8) is non-zero, cond 2 with value = opponent's owner byte (*(fighter+0x5a4) = chrp row
byte 0 = 33 for Sora), else cond 0/3 by strength. No match -> cond 5 (general random). So a vs-33 row plays on every
"vs-specific" intro against Sora (native fighters had none -> general lines). voice_load_parameter.mpk holds a
second copy of each list for the Museum (menu FUN_08a384ac) only; battle never reads it -> left unchanged.
Native pattern: every fighter has one cond-2 row per opponent (1..32); only 30 of 1024 have a reply row, so no
Sora reply is added (Lightning's existing test-28 pair 1100 -> Sora reply 1101 "Come on!" stays).

Title call (menu overlay OVL_MENU_APP): FUN_089dfd6c picks an index from the day-of-month table 0x089E07D8 (31 u32)
+ overrides; FUN_089deaa8 plays voice/JP->EN/event/title_call/<SQE[i]>.at3 and <DDD[i]>.at3 when i < 0x22, SQE table
0x089E08B0 [34], DDD table 0x089E0938 [34] (ga/em/co have no DDD half). Sora = new index 34:
  sltiu bound 0x22 -> 0x23 (0x089DEC04); DDD table base 0x0938 -> 0x0504 (0x089DECD0, same lui 0x089e);
  new 35-entry DDD table at 0x089E0504 (the old DDD strings area) + all DDD strings re-packed 13 bytes apart
  (region 0x089E0504..0x089E06F0 and the old DDD table words 0x089E093C..0x089E09BF; only the tables point at them —
  checked: no other menu-overlay code reference, 0x089E06F1 onward untouched); SQE[34] = old DDD[0] slot 0x089E0938;
  day 25 (Exdeath, keeps 15) and day 29 (Kuja, keeps 19) -> 34. Kefka keeps 16/26; nobody loses their only day.
  Other gates unchanged (save flag 0x1de68 & 0x100, PSP clock sane vs the save's timestamps).

Audio: approved originals (24 kHz mono PCM16, SHA-256 checked against the package manifest; no gain/pitch/timing
edits) -> spot33_lines.at3() (ATRAC3 mono 44.1 kHz, 192-byte frames, 2048 tail pad, fact = real samples,
n + 1093 <= frames*1024) -> decoded back and checked (mono, 44100, length, correlation with the source).
HELD (not written): Cosmos and Aerith (no battle voice list: Cosmos = owner 34 P_ORG800 has no voice_load file;
Aerith was assist-only and owner 33 is now Sora — assists have no voice_load list), Sora-vs-Chaos round 3 (no native
selector can say "vs Chaos AND final round": cond 7/8 series rows ignore the opponent), the approved alternates
(Cecil option3, Jecht ending17, Chaos take22), Chaos's own line (owner 23 P_ORG200 = story boss; Codex HOLD until
the boss routing is verified), Sora's Chaos round 1/2, Aerith-assist and Cosmos-story lines (dedicated triggers
unverified, Codex HOLD). Warrior of Light's Sora line approved 13:40 UTC (test342) -> 30 Sora lines.

LEVEL (GAIN_MODE=match, default since test338; Mat "Raise them please"): each clip is matched to the median
loudness of the speaker's own native lines (title halves: native title_call median; mirror: Sora's so_battle lines)
with one static gain + a 5 ms look-ahead / 80 ms release peak limiter, decoded peak <= -1 dBFS, decoded loudness
within 1 LU of target. GAIN_MODE=off reproduces test337 (approved PCM untouched); GAIN_TRIM=-3 = 3 dB quieter
targets (less limiting).

Guarded + re-runnable: every target must be stock (test336 state) or exactly this script's output; --dry writes
nothing (it still encodes into a temp dir to prove the audio).

  python3 -I spot33_vsvoices.py ISO [--dry] [--no-title]
"""
import array
import hashlib
import json
import os
import struct
import subprocess
import sys
import tempfile
import wave

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, HERE)
from roster_patch import MENU_FILEOFF, MENU_ISO_SECTOR, MENU_VADDR  # noqa: E402
from spot33_lines import at3  # noqa: E402
from voice_lines import VoiceISO  # noqa: E402

PKG = os.path.join(ROOT, 'codex/inbox/20261018-approved-voices')
GAIN_MODE = os.environ.get('GAIN_MODE', 'match')   # match (default, test338) | off (test337: no level change)
assert GAIN_MODE in ('match', 'off'), GAIN_MODE
LIM_MED_MAX = float(os.environ.get('LIM_MED_MAX', '6'))  # dB: max median limiting on speech (gentle)
GAIN_TRIM = float(os.environ.get('GAIN_TRIM', '0'))  # dB added to every match target (e.g. -3 = quieter, less limiting)
START, VS = 0x0046, 2
SORA = 33
SECTOR = 0x800

# owner, chrp voice key, clip prefix (checked against the speaker's first clip), manifest character, subtitle.
# Owners from the VOLD mirror rows (cond 2 value = own owner). NOTE: manifest owners for Prishe (30) / Vaan (29) are
# swapped (voice_catalog.py NAMES has the same swap): P_GST110 = Prishe = 29, P_GST120 = Vaan = 30.
SPEAKERS = [
    (1, 'P_ONE100', 'wo', 'Warrior of Light', 'Your light is strong. Let your blade prove your resolve.'),
    (2, 'P_ONE200', 'ga', 'Garland', 'A curious blade, boy. Let us see if it can withstand mine.'),
    (3, 'P_TWO100', 'fn', 'Firion', "If you're fighting for a dream, then show me your resolve."),
    (4, 'P_TWO200', 'em', 'Emperor', 'A key is of little use before a throne. Kneel.'),
    (5, 'P_THR100', 'on', 'Onion Knight', "That weapon looks tricky. I'll just have to be quicker."),
    (6, 'P_THR200', 'cd', 'Cloud of Darkness', 'Your little light will vanish into the darkness.'),
    (7, 'P_FOR100', 'ce', 'Cecil', 'You carry a bright light. Show me the courage behind it.'),
    (8, 'P_FOR200', 'gb', 'Golbez', 'A bright heart alone will not shield you from darkness.'),
    (9, 'P_FIV100', 'bu', 'Bartz', "Now that's a weapon I haven't tried. Let's see it in action!"),
    (10, 'P_FIV200', 'ed', 'Exdeath', 'No key can seal the Void. Your light ends here.'),
    (11, 'P_SIX100', 'ti', 'Terra', "Your heart feels warm. I hope we don't have to hurt each other."),
    (12, 'P_SIX200', 'cf', 'Kefka', 'A key? What a joke! Show me what it opens!'),
    (13, 'P_SEV100', 'cl', 'Cloud', 'An unusual weapon. Show me what it can do.'),
    (14, 'P_SEV200', 'sf', 'Sephiroth', 'Such a bright heart. Let us see how long it lasts.'),
    (15, 'P_EHT100', 'sq', 'Squall', "You've got confidence. Let's see if your guard holds."),
    (16, 'P_EHT200', 'am', 'Ultimecia', 'Even your precious light... will fade with time.'),
    (17, 'P_NIN100', 'zi', 'Zidane', "Nice key! Let's see if you're quick enough to keep it."),
    (18, 'P_NIN200', 'kj', 'Kuja', 'A hero with a key? How quaint. Let the curtain rise.'),
    (19, 'P_TEN100', 'td', 'Tidus', 'Hey! Nice moves! Think you can keep up with me?'),
    (20, 'P_TEN200', 'je', 'Jecht', "You've got guts, kid. Now let's see what you've got."),
    (21, 'P_GST100', 'sh', 'Shantotto', 'A key in hand, a heart so bright! Come earn a lesson in this fight!'),
    (22, 'P_GST200', 'gs', 'Gabranth', 'Your cause may be noble! Your resolve will be judged!'),
    (24, 'P_FOR110', 'ca', 'Kain', 'Keep your eyes on the sky. Your courage will be tested.'),
    (25, 'P_FIV210', 'gi', 'Gilgamesh', 'A blade like that belongs in my collection!'),
    (26, 'P_SEV110', 'tf', 'Tifa', "You've got plenty of heart. Now show me your strength."),
    (27, 'P_EHT110', 'la', 'Laguna', "That's one big key! Hope you know how to use it."),
    (28, 'P_TEN110', 'yu', 'Yuna', "You fight for someone, don't you? Then don't hold back."),
    (29, 'P_GST110', 'pr', 'Prishe', "That's a big key for a little guy. Come on, show me some fight!"),
    (30, 'P_GST120', 'va', 'Vaan', "A key for a sword? All right! Show me what you've got!"),
    (31, 'P_GST130', 'li', 'Lightning', 'A new face? Fine.'),
    (33, 'P_SEV120', 'so', 'Sora mirror', '...Another... Keyblade?'),
]
# Display-text normalisation vs the manifest text (subtitle font/style only; audio untouched): curly quotes -> ',
# Gilgamesh caps (delivery direction) -> sentence case, "Keyblade???" -> "Keyblade?", "light ... will" -> "light...".
LIGHTNING_LID, LIGHTNING_OLD_CLIP = 1100, 'li_battle_93'     # test-28 row (wrong audio: "My blade'll fix this.")


TIDUS_OLD_LID, TIDUS_LID = 1129, 1144                        # 1129 = native reply target of every fighter


def line_id(owner):
    if owner == 19:
        return TIDUS_LID
    return LIGHTNING_LID if owner == 31 else 1110 + owner     # 1111..1142 (+1143 mirror); 0..1205 are free ids


def clip_name(prefix):
    return '%s_vs_sora' % prefix


# Sora speaking (owner 33) against each opponent: manifest character 'Sora vs <name>' -> opponent owner + clip.
SORA_KEY = 'P_SEV120'
SORA_VS_OWNERS = {who: o for o, _, _, who, _ in SPEAKERS if o != SORA}
SORA_VS_OWNERS['Feral Chaos'] = 32                           # P_ORG210 (ch_ clips, same prefix as Chaos)
SORA_VS_PREFIX = {o: p for o, _, p, _, _ in SPEAKERS if o != SORA}
SORA_VS_PREFIX[32] = 'fc'
SORA_OLD_IDS = range(1015, 1047)
OPP_KEY = {o: k for o, k, _, _, _ in SPEAKERS}
OPP_KEY[32] = 'P_ORG210'                             # the cloned generic vs rows (Cloud's list, test 28)


def sora_line_id(opp):
    return 1150 + opp                                        # 1151..1182, free (ids, replies and subtitles)


def sora_clip(opp):
    return 'so_vs_%s' % SORA_VS_PREFIX[opp]


def subtitle_text(t):
    """display normalisation only (subtitle font): curly quotes -> straight"""
    return t.replace('’', "'").replace('‘', "'").replace('“', '"').replace('”', '"')


def sora_lines(assets):
    """[(opponent owner, manifest entry, subtitle)] for every approved routable 'Sora vs <opponent>' line"""
    out = []
    for who, a in sorted(assets.items()):
        if not who.startswith('Sora vs ') or who in HELD or who == 'Sora vs Chaos round3':
            continue
        name = who[len('Sora vs '):]
        assert name in SORA_VS_OWNERS, (who, 'no routable opponent; add it to HELD or SORA_VS_OWNERS')
        assert a.get('owner') == SORA and a.get('opponent') == name, (who, a.get('owner'), a.get('opponent'))
        out.append((SORA_VS_OWNERS[name], a, subtitle_text(a['text'])))
    return sorted(out, key=lambda x: x[0])


TITLE_FILES = {'title_so_SQE': 'Sora publisher', 'title_so_DDD': 'Sora title'}
TITLE_PATH = 'voice/EN/event/title_call/%s.at3'
HELD = {'Cosmos': 'no battle voice list (owner 34 P_ORG800 has no voice_load file; not a fighter)',
        'Aerith': 'assist-only in vanilla, owner 33 is now Sora; assists have no voice_load list',
        'Sora vs Chaos round3': 'no native selector for "vs Chaos AND final round" (cond 7/8 ignore the opponent)',
        'Chaos': 'owner 23 P_ORG200 = story boss; boss/round routing unverified (Codex HOLD)',
        'Sora vs Chaos round 1': 'dedicated round trigger unverified (Codex HOLD)',
        'Sora vs Chaos round 2': 'dedicated round trigger unverified (Codex HOLD)',
        'Sora vs Aerith assist acknowledgment': 'assist call has no voice row selector (Codex HOLD)',
        'Sora vs Cosmos story line': 'story event, not a battle row (Codex HOLD)'}

# --- title-call overlay layout -------------------------------------------------------------------------------------
NAMES = 'wo ga fn em on cd ce gb ca bu ed gi ti cf cl sf tf la sq am zi kj td yu je pr sh va gs li co ch na ae'.split()
NO_DDD = {'ga', 'em', 'co'}
SORA_INDEX = 34
SLTIU_VA, SLTIU_OLD, SLTIU_NEW = 0x089DEC04, 0x2CA60022, 0x2CA60023
DDDBASE_VA, DDDBASE_OLD, DDDBASE_NEW = 0x089DECD0, 0x24C60938, 0x24C60504
SQE_TABLE, DDD_TABLE_OLD, DDD_TABLE_NEW = 0x089E08B0, 0x089E0938, 0x089E0504
DAY_TABLE = 0x089E07D8
DAYS = {25: 10, 29: 21}                          # day -> vanilla index (Exdeath 15/25, Kuja 19/29)
REGION_A = (0x089E0504, 0x089E06F1)              # old DDD strings (16-byte slots), ends where 0x089E06F1 data starts
REGION_B = (0x089E093C, 0x089E09C0)              # old DDD table words 1..33 (word 0 = new SQE[34])
SQE_STR = 0x089E02E4                             # SQE strings stay (16-byte slots)


def menu_off(va):
    return MENU_ISO_SECTOR * SECTOR + va - MENU_VADDR + MENU_FILEOFF


def old_title_bytes():
    """vanilla bytes of region A, region B, SQE[34] slot (= old DDD[0])"""
    a = bytearray(REGION_A[1] - REGION_A[0])
    ddd_ptr = {}
    k = 0
    for n in NAMES:
        if n in NO_DDD:
            continue
        at = REGION_A[0] + 16 * k
        s = ('title_%s_DDD' % n).encode() + b'\0'
        a[at - REGION_A[0]:at - REGION_A[0] + len(s)] = s
        ddd_ptr[n] = at
        k += 1
    words = [ddd_ptr.get(n, 0) for n in NAMES]
    b = struct.pack('<33I', *words[1:])
    return bytes(a), b, struct.pack('<I', words[0])


def new_title_bytes():
    """region A = new DDD table (35 words) + packed strings; region B = rest of the strings; SQE[34] pointer"""
    strings = [('title_%s_DDD' % n) for n in NAMES if n not in NO_DDD] + list(TITLE_FILES)
    a = bytearray(REGION_A[1] - REGION_A[0])
    b = bytearray(REGION_B[1] - REGION_B[0])
    ptr = {}
    at = DDD_TABLE_NEW + 4 * (len(NAMES) + 1)
    for s in strings:
        raw = s.encode() + b'\0'
        if at + len(raw) > REGION_A[1] and at < REGION_B[0]:
            at = REGION_B[0]
        buf, base = (a, REGION_A[0]) if at < REGION_A[1] else (b, REGION_B[0])
        assert at + len(raw) <= (REGION_A[1] if buf is a else REGION_B[1]), 'title strings do not fit'
        buf[at - base:at - base + len(raw)] = raw
        ptr[s] = at
        at += len(raw)
    table = [ptr.get('title_%s_DDD' % n, 0) for n in NAMES] + [ptr['title_so_DDD']]
    a[0:4 * len(table)] = struct.pack('<%dI' % len(table), *table)
    return bytes(a), bytes(b), struct.pack('<I', ptr['title_so_SQE'])


def title_plan(iso):
    """[(file offset, va, new bytes, done)] for the overlay; asserts every site is vanilla or ours"""
    old_a, old_b, old_s = old_title_bytes()
    new_a, new_b, new_s = new_title_bytes()
    sites = [(SLTIU_VA, struct.pack('<I', SLTIU_OLD), struct.pack('<I', SLTIU_NEW)),
             (DDDBASE_VA, struct.pack('<I', DDDBASE_OLD), struct.pack('<I', DDDBASE_NEW)),
             (REGION_A[0], old_a, new_a), (REGION_B[0], old_b, new_b), (DDD_TABLE_OLD, old_s, new_s)]
    for day, idx in sorted(DAYS.items()):
        sites.append((DAY_TABLE + 4 * (day - 1), struct.pack('<I', idx), struct.pack('<I', SORA_INDEX)))
    plan = []
    with open(iso, 'rb') as f:
        f.seek(menu_off(SQE_TABLE))
        sqe = struct.unpack('<34I', f.read(4 * 34))
        assert sqe == tuple(SQE_STR + 16 * i for i in range(34)), 'SQE table is not vanilla'
        for va, old, new in sites:
            f.seek(menu_off(va))
            cur = f.read(len(old))
            assert cur in (old, new), 'title-call site %08x is neither vanilla nor ours' % va
            plan.append((menu_off(va), va, new, cur == new))
    return plan


# --- audio ---------------------------------------------------------------------------------------------------------
def manifest_assets():
    m = json.load(open(os.path.join(PKG, 'manifest.json')))
    out = {}
    for a in m['assets']:
        if a['role'] == 'main':
            assert a['character'] not in out, a['character']
            out[a['character']] = a
    return out


def checked_source(asset):
    """prepare_audio.py's guard, read-only: SHA-256 vs manifest, mono PCM16"""
    p = os.path.join(PKG, asset['file'])
    assert hashlib.sha256(open(p, 'rb').read()).hexdigest() == asset['sha256'], 'hash mismatch: ' + p
    with wave.open(p) as w:
        assert w.getnchannels() == 1 and w.getsampwidth() == 2, p
    return p


def pcm(path, rate):
    r = subprocess.run(['ffmpeg', '-nostdin', '-hide_banner', '-loglevel', 'error', '-i', path, '-ac', '1', '-ar',
                        str(rate), '-f', 's16le', '-'], check=True, capture_output=True)
    return array.array('h', r.stdout)


def decode_check(src, at3_path, level=True, clip_ok=False):
    """decoded clip: ATRAC3 mono 44.1 kHz, fact = source samples, speech-band spectrogram matches, level kept"""
    d = open(at3_path, 'rb').read()
    fmt = d.index(b'fmt ')
    tag, ch, rate = struct.unpack_from('<HHI', d, fmt + 8)
    align, = struct.unpack_from('<H', d, fmt + 20)
    assert (tag, ch, rate, align) == (0x270, 1, 44100, 192), (tag, ch, rate, align)
    fa = d.index(b'fact')
    n_fact, = struct.unpack_from('<I', d, fa + 8)
    frames = struct.unpack_from('<I', d, d.index(b'data') + 4)[0] // 192
    assert n_fact + 1093 <= frames * 1024
    s = np.array(pcm(src, 44100), dtype=np.float64)
    x = np.array(pcm(at3_path, 44100), dtype=np.float64)
    assert len(x) >= len(s), (len(x), len(s))
    assert abs(n_fact - len(s)) <= 2, (n_fact, len(s))
    n = 1 << int(np.ceil(np.log2(len(s) + len(x))))
    cc = np.fft.irfft(np.fft.rfft(x, n) * np.conj(np.fft.rfft(s, n)), n)
    lag = int(np.argmax(cc[:4096]))        # codec delay (ffmpeg does not skip it)
    y = x[lag:lag + len(s)]
    s = s[:len(y)]

    def spec(v):                           # log spectrogram 0..8 kHz (ATRAC3 keeps the speech band, not the phase)
        w = np.hanning(1024)
        return np.log1p(np.array([np.abs(np.fft.rfft(v[i:i + 1024] * w))[:186] for i in range(0, len(v) - 1024, 512)]))
    if level:
        corr = float(np.corrcoef(spec(s).ravel(), spec(y).ravel())[0, 1])
    else:                                  # vs the approved original after level matching: compare each frame's
        a, b = spec(s), spec(y)            # spectral SHAPE (frame mean removed; dynamics are intentionally changed)
        keep = a.mean(1) > a.mean(1).max() - 3.0
        a = a[keep] - a[keep].mean(1, keepdims=True)
        b = b[keep] - b[keep].mean(1, keepdims=True)
        corr = float(np.corrcoef(a.ravel(), b.ravel())[0, 1])
    rms_db = 20 * np.log10((np.sqrt(np.mean(y ** 2)) + 1e-9) / (np.sqrt(np.mean(s ** 2)) + 1e-9))
    peak = int(np.abs(x).max())
    assert corr > (0.9 if level else 0.85), 'decoded clip does not match its source (spectrogram corr %.3f)' % corr
    assert abs(rms_db) < 1.0 or not level, 'level changed by %.2f dB' % rms_db
    assert peak < 32767 or clip_ok, 'decoded clip clips'
    return dict(bytes=len(d), samples=n_fact, seconds=round(n_fact / 44100, 3), corr=round(corr, 3), lag=lag,
                rms_db=round(float(rms_db), 2),
                peak=peak)


# --- loudness match (GAIN_MODE=match, default; GAIN_MODE=off = test337: approved PCM untouched) -------------------
# Mat 2026-10-18 "Raise them please": the approved lines measured 11-14 dB quieter than native dialogue.
# Level = BS.1770-style integrated loudness (K-weighting, 400 ms blocks / 100 ms hop, -70 LUFS absolute and -10 LU
# relative gate). Target = median loudness of the speaker's own native battle-start clips (<prefix>_battle_*; Sora
# mirror -> Sora's so_battle_* lines; title halves -> every native title_call file), measured from the disc.
# Processing = one static gain + a look-ahead peak limiter (5 ms look-ahead = attack ramp, 80 ms release, no
# make-up, ceiling -1.5 dBFS before the codec; decoded peak must be <= -1 dBFS, else the ceiling steps down 0.5 dB).
# Timing, pitch, pauses untouched (same sample count, gain-only per sample).
FS = 44100
CEILINGS = (-1.5, -2.0, -2.5, -3.0)
PEAK_MAX = 10 ** (-1 / 20) * 32768                    # -1 dBFS on the decoded clip


def _biquads(fs):
    import math
    G, Q, fc = 3.999843853973347, 0.7071752369554196, 1681.974450955533
    A, w0 = 10 ** (G / 40), 2 * math.pi * fc / fs
    al, c = math.sin(w0) / (2 * Q), math.cos(w0)
    b1 = [A * ((A + 1) + (A - 1) * c + 2 * math.sqrt(A) * al), -2 * A * ((A - 1) + (A + 1) * c),
          A * ((A + 1) + (A - 1) * c - 2 * math.sqrt(A) * al)]
    a1 = [(A + 1) - (A - 1) * c + 2 * math.sqrt(A) * al, 2 * ((A - 1) - (A + 1) * c),
          (A + 1) - (A - 1) * c - 2 * math.sqrt(A) * al]
    Q2, fc2 = 0.5003270373238773, 38.13547087602444
    w2 = 2 * math.pi * fc2 / fs
    al2, c2 = math.sin(w2) / (2 * Q2), math.cos(w2)
    return (b1, a1), ([1.0, -2.0, 1.0], [1 + al2, -2 * c2, 1 - al2])


def loudness(x, fs=FS):
    """integrated loudness (LUFS-like) of float samples in -1..1"""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        from scipy.signal import lfilter
    y = x
    for b, a in _biquads(fs):
        y = lfilter(b, a, y)
    blk, hop = int(0.4 * fs), int(0.1 * fs)
    if len(y) < blk:
        y = np.concatenate([y, np.zeros(blk - len(y))])
    z = np.array([np.mean(y[i:i + blk] ** 2) for i in range(0, len(y) - blk + 1, hop)])
    lk = -0.691 + 10 * np.log10(z + 1e-20)
    z = z[lk > -70]
    rel = -0.691 + 10 * np.log10(np.mean(z)) - 10
    z = z[(-0.691 + 10 * np.log10(z)) > rel]
    return float(-0.691 + 10 * np.log10(np.mean(z)))


def fpcm(path):
    return np.array(pcm(path, FS), dtype=np.float64) / 32768


def limit(x, ceiling_db):
    """look-ahead peak limiter: gain never above what each sample needs, smooth attack over the look-ahead,
    exponential release; returns (y, gain curve)"""
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        from scipy.ndimage import minimum_filter1d
    ceil = 10 ** (ceiling_db / 20)
    la = int(0.005 * FS)
    need = np.minimum(1.0, ceil / np.maximum(np.abs(x), 1e-12))
    m = minimum_filter1d(need, size=2 * la + 1, mode='nearest')     # min over +-la samples
    rel = float(np.exp(-1.0 / (0.080 * FS)))
    r = np.empty_like(m)
    g = 1.0
    for i, v in enumerate(m.tolist()):                                # release: recover toward 1 at 80 ms
        g = 1.0 - (1.0 - g) * rel
        if v < g:
            g = v
        r[i] = g
    h = la // 2                                                       # +-la/2 average <= every need in window
    k = np.ones(2 * h + 1) / (2 * h + 1)
    s = np.convolve(np.pad(r, h, mode='edge'), k, mode='valid')
    s = np.minimum(s, need)                                           # exact guarantee (no-op in practice)
    return x * s, s


def _band(y, hz=11500.0):
    """measurement only: drop what ATRAC3 (66 kbps mono) discards anyway, so the aim matches the decoded clip"""
    n = len(y)
    f = np.fft.rfft(y)
    f[int(hz * n / FS):] = 0
    return np.fft.irfft(f, n)


def match_level(src, target, out_wav, ceiling_db):
    """static gain + limiter so the result's loudness is target (+-0.1 LU, codec band); writes 16-bit 44.1 kHz.
    If that needs more than LIM_MED_MAX dB median limiting on the speech, the gain backs off to the cap ('capped')."""
    x = fpcm(src)
    act = np.abs(x) > 0.01
    l0 = loudness(x)

    def run(g):
        y, s = limit(x * 10 ** (g / 20), ceiling_db)
        gr = -20 * np.log10(s)
        return y, gr, loudness(_band(y)), float(np.median(gr[act])) if act.any() else 0.0

    gain = target - l0
    for _ in range(10):
        y, gr, ly, med = run(gain)
        if abs(target - ly) < 0.1:
            break
        gain += target - ly
    capped = med > LIM_MED_MAX
    if capped:                                       # bisect down to the limiter cap
        lo, hi = target - l0 - 12, gain
        for _ in range(14):
            mid = (lo + hi) / 2
            if run(mid)[3] > LIM_MED_MAX:
                hi = mid
            else:
                lo = mid
        gain = lo
        y, gr, ly, med = run(gain)
    q = np.clip(np.round(y * 32768), -32767, 32767).astype('<i2')
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(FS)
        w.writeframes(q.tobytes())
    return dict(src_lufs=round(l0, 1), gain=round(gain, 2), lim_max=round(float(gr.max()), 1),
                lim_med=round(med, 1), lim_1db=round(float(np.mean(gr > 1) * 100), 1), ceiling=ceiling_db,
                capped=capped)


def native_target(vl, cache, key, prefix):
    """median loudness of the speaker's own native battle-start clips"""
    rows = vl.rows(key)
    clips = {r[0] for r in rows if r[2] == START and r[0].startswith(prefix + '_battle_')}
    if key == SORA_KEY:          # the 32 vs rows re-pointed to so_vs_* keep counting (their clip files stay) -> the
        clips |= {'so_battle_%d' % i for i in range(41, 73)}     # target is the same before/after -> re-run = same
    clips = sorted(clips)
    return median_loudness(vl, cache, ['voice/EN/battle/%s.at3' % c for c in clips])


def title_target(vl, cache):
    names = ['title_%s_SQE' % n for n in NAMES] + ['title_%s_DDD' % n for n in NAMES if n not in NO_DDD]
    return median_loudness(vl, cache, [TITLE_PATH % n for n in names])


def median_loudness(vl, cache, paths):
    vals = []
    with tempfile.TemporaryDirectory() as t:
        for p in paths:
            if p not in cache:
                f = os.path.join(t, 'n.at3')
                open(f, 'wb').write(vl.file(p))
                cache[p] = loudness(fpcm(f))
            vals.append(cache[p])
    assert len(vals) >= 5, paths
    return float(np.median(vals)), len(vals)


def iso_file(vl, path):
    try:
        return vl.file(path)
    except KeyError:
        return None


def put(iso, path, data):
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'x.bin')
        open(p, 'wb').write(data)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, path, p],
                           check=True, capture_output=True, text=True)
        print('   ', r.stdout.strip())


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    if len(args) != 1:
        sys.exit(__doc__)
    iso = args[0]
    dry, no_title = '--dry' in sys.argv, '--no-title' in sys.argv
    assets = manifest_assets()
    for who in HELD:
        assert who not in [w for *_, w, _ in SPEAKERS], who + ' is held'
    soras = sora_lines(assets)
    vl = VoiceISO(iso)
    all_rows = {key: vl.rows(key) for key in [k for _, k, _, _, _ in SPEAKERS] + ['P_ORG200', 'P_ORG210']}
    other_ids = {}                                   # every row id AND every reply target (cond 6 value)
    for key, rows in all_rows.items():
        for r in rows:
            other_ids.setdefault(r[1], set()).add(key)
            if r[3] == 6:
                other_ids.setdefault(r[4], set()).add(key + ' reply')
    new_rows = {k: [list(r) for r in rows] for k, rows in all_rows.items()}
    notes, ours_clips, subs, drop_subs = {}, set(), {}, set()

    def free_id(lid, mine, listener):
        """lid must not be another row's id; a reply row (cond 6 value lid) only matters in the LISTENER's list (the
        one fighter who can hear this line: Sora for vs-Sora lines, the opponent for Sora's lines). Chaos (P_ORG200)
        replies to 1128 (Kuja's vs-Sora id) but never fights in a Kuja-vs-Sora intro -> harmless."""
        users = {u for u in other_ids.get(lid, ()) if u not in mine and
                 (not u.endswith(' reply') or u == listener + ' reply')}
        assert not users, ('line id %d already used by' % lid, users)

    # ---------- VOLD rows + subtitles (plan + guards) ----------
    for owner, key, pfx, who, text in SPEAKERS:
        a = assets[who]
        if who != 'Sora mirror':
            assert a['mapping']['intended_trigger'] == 'speaker battle opening vs Sora owner33', who
        rows = new_rows[key]
        assert rows[0][0].startswith(pfx + '_'), (key, rows[0][0], 'speaker check failed')
        mirror = [r for r in rows if r[3] == VS and r[4] == owner]
        assert owner == SORA or mirror, (key, 'no mirror row -> owner mismatch')
        lid, clip = line_id(owner), clip_name(pfx)
        want = [clip, lid, START, VS, SORA]
        hits = [i for i, r in enumerate(rows) if r[2] == START and r[3] == VS and r[4] == SORA]
        if not hits:
            free_id(lid, {key, SORA_KEY + ' reply'} if owner == 31 else set(), SORA_KEY)
            rows.append(want)
            notes.setdefault(key, []).append('add %s' % clip)
        else:
            assert len(hits) == 1, (key, 'several vs-33 rows')
            r = rows[hits[0]]
            if r == want:
                ours_clips.add(clip)
            elif owner == 31 and r == [LIGHTNING_OLD_CLIP, LIGHTNING_LID, START, VS, SORA]:
                rows[hits[0]] = want
                notes.setdefault(key, []).append('re-point %s -> %s' % (LIGHTNING_OLD_CLIP, clip))
            elif owner == 19 and r == [clip, TIDUS_OLD_LID, START, VS, SORA]:     # test337..339 id
                free_id(lid, set(), SORA_KEY)
                rows[hits[0]] = want
                ours_clips.add(clip)                 # same clip file, only the id moves
                notes.setdefault(key, []).append('re-id %d -> %d' % (TIDUS_OLD_LID, lid))
                if vl.subs.get(TIDUS_OLD_LID) == text:
                    drop_subs.add(TIDUS_OLD_LID)
            else:
                sys.exit('%s: unexpected vs-33 row %r (neither stock nor ours)' % (key, r))
        cur = vl.subs.get(lid)
        assert cur in (None, text), ('subtitle %d is %r' % (lid, cur))
        subs[lid] = text

    rows = new_rows[SORA_KEY]                        # Sora speaking: re-point the cloned generic vs-<opp> row
    for opp, a, text in soras:
        lid, clip = sora_line_id(opp), sora_clip(opp)
        want = [clip, lid, START, VS, opp]
        hits = [i for i, r in enumerate(rows) if r[2] == START and r[3] == VS and r[4] == opp]
        assert len(hits) == 1, (SORA_KEY, opp, 'expected exactly one vs row', [rows[i] for i in hits])
        r = rows[hits[0]]
        if r == want:
            ours_clips.add(clip)
        elif r[0].startswith('so_battle_') and r[1] in SORA_OLD_IDS:
            free_id(lid, set(), OPP_KEY[opp])
            rows[hits[0]] = want
            notes.setdefault(SORA_KEY, []).append('vs %d: %s -> %s' % (opp, r[0], clip))
        else:
            sys.exit('%s: unexpected vs-%d row %r (neither stock nor ours)' % (SORA_KEY, opp, r))
        cur = vl.subs.get(lid)
        assert cur in (None, text), ('subtitle %d is %r' % (lid, cur))
        subs[lid] = text
    vold_changes = {k: ('; '.join(notes[k]), new_rows[k]) for k in notes}

    title_files = {} if no_title else {n: assets[w] for n, w in TITLE_FILES.items()}
    plan = [] if no_title else title_plan(iso)

    # ---------- audio: encode + decode-check (also in --dry) ----------
    report = []
    with tempfile.TemporaryDirectory() as t:
        encoded = {}
        jobs = [('voice/EN/battle/%s.at3' % clip_name(pfx), assets[who], 'line %d %s' % (line_id(o), who),
                 ('native', key, pfx)) for o, key, pfx, who, _ in SPEAKERS]
        jobs += [('voice/EN/battle/%s.at3' % sora_clip(o), a, 'Sora line %d vs %d' % (sora_line_id(o), o),
                  ('native', SORA_KEY, 'so')) for o, a, _ in soras]
        jobs += [(TITLE_PATH % n, a, 'title call %s' % n, ('title',)) for n, a in title_files.items()]
        cache, levels = {}, []
        for path, a, label, tsel in jobs:
            src = checked_source(a)
            out = os.path.join(t, os.path.basename(path))
            if GAIN_MODE == 'off':
                at3(src, out)
                info = decode_check(src, out)
            else:
                target, n_ref = native_target(vl, cache, tsel[1], tsel[2]) if tsel[0] == 'native' else \
                    title_target(vl, cache)
                target += GAIN_TRIM
                wav = os.path.join(t, os.path.basename(path) + '.wav')
                for ceiling in CEILINGS:                              # step down if the codec overshoots -1 dBFS
                    lv = match_level(src, target, wav, ceiling)
                    at3(wav, out)
                    info = decode_check(wav, out, clip_ok=True)       # vs the processed PCM: codec only
                    lv['dec_lufs'] = round(loudness(fpcm(out)), 2)
                    lv['dec_peak_db'] = round(20 * np.log10(info['peak'] / 32768), 2)
                    if info['peak'] <= PEAK_MAX:
                        break
                assert info['peak'] <= PEAK_MAX, (path, 'decoded peak above -1 dBFS at every ceiling')
                assert lv['capped'] or abs(lv['dec_lufs'] - target) <= 1.0, (path, lv, target)
                lv['corr_orig'] = decode_check(src, out, level=False)['corr']   # speech vs the approved original
                lv.update(target=round(target, 2), n_ref=n_ref, label=label)
                levels.append(lv)
            data = open(out, 'rb').read()
            cur = iso_file(vl, path)
            if cur is not None and cur != data:
                # an existing file at our path must be our own earlier output (same row already ours)
                clip = os.path.basename(path)[:-4]
                ours = clip in ours_clips or (path.startswith('voice/EN/event') and all(d for *_, d in plan))
                assert ours, path + ' exists on the disc and is not ours'
            encoded[path] = (data, cur == data)
            report.append((label, path, info, 'already' if cur == data else ('replace' if cur else 'new')))

        for label, path, info, state in report:
            print('%-30s %-46s %6d B %5.2f s spec %.3f lvl %+.2f dB peak %5d  %s' % (
                label, path, info['bytes'], info['seconds'], info['corr'], info['rms_db'], info['peak'], state))
        for lv in levels:
            print('level %-30s src %6.1f -> target %6.1f (median of %2d native) gain %+5.1f dB  decoded %6.2f  peak '
                  '%5.2f dBFS  limiter max %4.1f / median %4.1f dB, >1 dB on %4.1f%%  speech corr %.3f%s' % (
                      lv['label'], lv['src_lufs'], lv['target'], lv['n_ref'], lv['gain'], lv['dec_lufs'],
                      lv['dec_peak_db'], lv['lim_max'], lv['lim_med'], lv['lim_1db'], lv['corr_orig'],
                      '  CAPPED (%.1f dB under target)' % (lv['target'] - lv['dec_lufs']) if lv['capped'] else ''))
        print('GAIN_MODE=%s GAIN_TRIM=%+.1f LIM_MED_MAX=%.1f' % (GAIN_MODE, GAIN_TRIM, LIM_MED_MAX))
        for key, (what, _) in vold_changes.items():
            print('VOLD %-9s %s' % (key, what))
        for at, va, data, done in plan:
            print('title-call %08x: %s' % (va, 'already' if done else 'patch (%d bytes)' % len(data)))
        print('held:', '; '.join('%s = %s' % kv for kv in HELD.items()))
        print('alternates kept in the package, not inserted: Cecil option3, Jecht ending17, Chaos take22')
        print('Sora matchup lines: %d (%s)' % (len(soras), ' '.join(str(o) for o, _, _ in soras)))
        if dry:
            print('--dry: nothing written')
            return

        # ---------- write ----------
        for path, (data, done) in encoded.items():
            if not done:
                put(iso, path, data)
        for key, (what, rows) in vold_changes.items():
            vl.set_rows(key, rows)
        for lid, text in subs.items():
            vl.subs[lid] = text
        for lid in drop_subs:
            del vl.subs[lid]
        vl.save()                                  # writes changed VOLD files + field_lang.bin (only if changed)
        if plan:
            with open(iso, 'r+b') as f:
                for at, va, data, done in plan:
                    if not done:
                        f.seek(at)
                        f.write(data)
    print('done')


if __name__ == '__main__':
    main()
