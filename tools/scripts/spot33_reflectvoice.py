"""EX Reflect says "Back off!" (Mat confirmed 2026-10-16; KH2 tt0_sora_029 = existing voice slot 7): in the guard blocks
20/21 (motions 470/471) the frame-0 voice event becomes normal-only (cond byte +5 = 1, keeps slot 37 "Defense!") and an
EX-only copy (cond +5 = 2) plays slot 7. Uses Codex's guarded transformer
codex/inbox/20261016-reflect-gap/reflect_voice_split.py (checks the layout, refuses a conflicting slot, keeps every
non-script chunk byte-identical, idempotent). Slot 7's bank data is checked against the selected clip first.
Needs no new voice/sound slot; objx +32 B.

  python3 -I spot33_reflectvoice.py ISO [--dry]
"""
import os
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'codex', 'inbox', '20261016-reflect-gap'))
sys.dont_write_bytecode = True
import fep_edit as E  # noqa: E402
import sscf  # noqa: E402
import reflect_voice_split as V  # noqa: E402

SLOT = 7
PCM = os.path.join(ROOT, 'dumps', 'voice_sora', 'sora16', 'tt0_sora_029.wav')


def main():
    iso, dry = sys.argv[1], '--dry' in sys.argv
    bank = E.load_objx(iso, 'voice/EN/battle/voice_P_SEV120_00.scd')
    _, off, size, rate = list(sscf.entries(bank))[SLOT]
    smp = sscf.read_wav(PCM, rate)
    assert sscf.encode(smp, (len(smp) + 27) // 28 + 1) == bank[off:off + size], 'voice slot 7 is not the Back off clip'
    d = E.load_objx(iso, 'obj/p_sev120.objx')
    out, rep = V.patch(d, SLOT)
    for r in rep:
        print('motion %d block %d: voices %s' % (r['motion'], r['block'], [(e['params'][0], e['conditions'][1])
              for e in r['one_shots'] if e['op'] == '0x15']))
    if out == d:
        print('nothing to do (EX-only Back off already there)')
        return
    print('objx %+d bytes' % (len(out) - len(d)))
    if dry:
        return
    fd, tmp = tempfile.mkstemp(suffix='.objx')
    os.write(fd, out)
    os.close(fd)
    subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, 'obj/p_sev120.objx', tmp], check=True)
    os.unlink(tmp)


if __name__ == '__main__':
    main()
