"""Append extra KH2 voice lines to Sora's battle voice bank (an SSCF file) — slots after the 43 existing ones.
Mat 2026-10-15: "Sora says fire when he's doing blizzard" -> Blizzaga = KH2 "Freeze!", Thundaga = "Thunder!"
(Thundaga used slot 15 = "LIGHT!"). Spell scripts point at these slots via spot33_spellsfx.py VOICE.
Entries copy slot 29's ("FIRE!") playback params. Re-runnable (existing slots are skipped).

  python3 -I spot33_voicex.py IN_BANK.scd OUT_BANK.scd
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import spot33_sfx  # noqa: E402

VDIR = os.path.join(HERE, '..', '..', 'dumps', 'voice_sora', 'sora16')
VOICES = {43: (os.path.join(VDIR, 'tt0_sora_013.wav'), 100, 'Freeze! (KH2 tt0_sora_013) — Blizzaga'),
          44: (os.path.join(VDIR, 'tt0_sora_014.wav'), 100, 'Thunder! (KH2 tt0_sora_014) — Thundaga')}


def main():
    bank = bytearray(open(sys.argv[1], 'rb').read())
    assert bank[:4] == b'SSCF', 'not an SSCF bank'
    spot33_sfx.TEMPLATE = 29
    bank, added = spot33_sfx.grow(bank, VOICES)
    open(sys.argv[2], 'wb').write(bank)
    print('voice bank: %d new slots %s' % (len(added), added))


if __name__ == '__main__':
    main()
