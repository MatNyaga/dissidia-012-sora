#!/bin/bash
# Clean disc -> base disc for build_sora.sh (release QA D-313-03). Replaces the private intermediate
# dumps/ULUS10566-test28-lines.iso: it replays the roster-spot-#33 setup of tests 14-28 (notes/roster.md,
# notes/voice-and-sound.md §5-6, notes/character-file.md tests 4-10) on a COPY of the clean dump, WITHOUT leaving the
# test-24 Cloud experiment in Cloud's files (D-313-01).
#
#   tools/scripts/bootstrap_base.sh [OUT_ISO]          default OUT_ISO = dumps/ULUS10566-base-fromclean.iso
#   tools/scripts/build_sora.sh OUT_ISO dumps/ULUS10566-testNN.iso
#
# The clean dump dumps/ULUS10566.iso is only READ and copied (cp), never written. OUT_ISO must not exist yet.
# ~2 min. Output = test28-lines minus the Cloud experiment, except (by design, both replaced by build_sora.sh):
#   obj/P_SEV120_1P.gmo = Cloud's 2P model (test 17 state; the test-18/19 pink test skin + test-27 entry swap are
#   not replayed), and the order of files appended at the disc end differs (same contents).
#
# Steps (test number = where it was first done):
#   4-10 Sora's battle file is a copy of Cloud's file WITH the move experiment (Sora's Combo Plus is action 1020,
#        hit 0xFF0 NEW_MIDDLE3 is used by spot33_combos). So the experiment is replayed on Cloud's two files
#        (comb_add, own_hit, atkp_patch), copied to obj/p_sev120.objx (16), and Cloud is restored from the clean
#        dump at the end (spot33_cloudvanilla.py). Cloud's ablt row 209 is never pointed at 1020 here.
#   14   roster_patch: chrp 33 = Cloud's row, objentry #33 rows = Cloud's, select list 32 -> 33, QB row Chaos -> 33
#   15   ablt rows 617-620 (owner 33 idx 0-3) = Cloud rows 209/216/219/222, row 617 action 1020
#   16   pkg_add obj/p_sev120.objx (copy of the experiment file), objentry model p_sev120, NEW_MIDDLE3 up-launch
#   17   pkg_add P_SEV120_{1,2,3}P .gmo/.exex/chara_image .gim (1P = Cloud 2P, 2P = Cloud 1P, 3P = Cloud 3P),
#        cosx data = Cloud's (same mapping), objentry #33 names P_SEV120_*
#   20   eboot_plain.py: decrypted EBOOT (tools/pspdecrypt) + unlock row 22 -> owner 33
#   21   spot33_save.py (own save record, preset 250, chrl)       22  spot33_names.py ("sev120" key + pictures)
#   23   roster_patch qb-row: #33 uses Cloud's grid picture 12     24  spot33_voice.py (voice bank + lines "so_")
#   28   voice_lines.py test28 (own line ids 1000+, Lightning vs-#33 line)
#   then spot33_cloudvanilla.py (Cloud's objx + _w byte-identical to clean, ablt 0x0d00 = 313)
set -euo pipefail
cd "$(dirname "$0")/../.."
S=tools/scripts
CLEAN=dumps/ULUS10566.iso
OUT=${1:-dumps/ULUS10566-base-fromclean.iso}
P="python3 -I"

[ -f "$CLEAN" ] || { echo "clean dump $CLEAN not found"; exit 1; }
[ "$(stat -c %s "$CLEAN")" = 1754529792 ] || { echo "$CLEAN is not the expected clean ULUS10566 dump (size)"; exit 1; }
[ -e "$OUT" ] && { echo "$OUT already exists - refusing to overwrite (pick a new name)"; exit 1; }
case "$(realpath -m "$OUT")" in "$(realpath "$CLEAN")") echo "OUT is the clean dump"; exit 1;; esac

echo "== copy $CLEAN -> $OUT (clean dump is only read)"
cp "$CLEAN" "$OUT"
chmod u+w "$OUT"

echo "== tests 4-10: move experiment on Cloud's files (temporary; restored at the end)"
for PK in 3394 5973; do $P $S/comb_add.py "$OUT" $PK 1020 0x5be 0x5bf 0x5c2 0x5c3; done
$P $S/own_hit.py "$OUT" 0x5c3 0xff0 0x27f0 0xff0 NEW_MIDDLE3 1020 3394 5973
for PK in 3394 5973; do
    $P $S/atkp_patch.py "$OUT" set-power $PK NEW_MIDDLE3 150
    $P $S/atkp_patch.py "$OUT" copy-knockback $PK LAND_NEAR3 NEW_MIDDLE3
done

echo "== test 14: roster spot #33"
$P $S/roster_patch.py "$OUT" copy-chrp 13 33
$P $S/roster_patch.py "$OUT" copy-objentry 13 p_sev100 33 p_sev120
$P $S/roster_patch.py "$OUT" select-swap 32 33
$P $S/roster_patch.py "$OUT" qb-row 23 33 32 6

echo "== test 15: ablt rows 617-620 for owner 33"
$P $S/ablt_patch.py "$OUT" copy-row 209 617 33 0
$P $S/ablt_patch.py "$OUT" copy-row 216 618 33 1
$P $S/ablt_patch.py "$OUT" copy-row 219 619 33 2
$P $S/ablt_patch.py "$OUT" copy-row 222 620 33 3
$P $S/ablt_patch.py "$OUT" set-action 617 1020

echo "== test 16: own battle file obj/p_sev120.objx"
$P $S/pkg_add.py "$OUT" obj/p_sev120.objx 3394
$P $S/roster_patch.py "$OUT" set-model 33 p_sev100 p_sev120
$P $S/atkp_patch.py "$OUT" set-float obj/p_sev120.objx NEW_MIDDLE3 0x1c 0
$P $S/atkp_patch.py "$OUT" set-float obj/p_sev120.objx NEW_MIDDLE3 0x20 40

echo "== test 17: own model/costume/portrait files"
$P $S/pkg_add.py "$OUT" obj/P_SEV120_1P.gmo 2343        # Cloud 2P
$P $S/pkg_add.py "$OUT" obj/P_SEV120_2P.gmo 1193        # Cloud 1P
$P $S/pkg_add.py "$OUT" obj/P_SEV120_3P.gmo 1964        # Cloud 3P
$P $S/pkg_add.py "$OUT" obj/P_SEV120_1P.exex 8702
$P $S/pkg_add.py "$OUT" obj/P_SEV120_2P.exex 1215
$P $S/pkg_add.py "$OUT" obj/P_SEV120_3P.exex 5793
$P $S/pkg_add.py "$OUT" menu/JP/battle/chara_image/P_SEV120_1P.gim 7565
$P $S/pkg_add.py "$OUT" menu/JP/battle/chara_image/P_SEV120_2P.gim 5711
$P $S/pkg_add.py "$OUT" menu/JP/battle/chara_image/P_SEV120_3P.gim 7840
$P $S/pkg_add.py "$OUT" --replace 2224 9994             # P_SEV120_1P.cosx <- Cloud 2P
$P $S/pkg_add.py "$OUT" --replace 9740 2307             # P_SEV120_2P.cosx <- Cloud 1P
$P $S/pkg_add.py "$OUT" --replace 7497 7332             # P_SEV120_3P.cosx <- Cloud 3P
$P $S/roster_patch.py "$OUT" set-name 33 P_SEV100_1P P_SEV120_1P
$P $S/roster_patch.py "$OUT" set-name 33 P_SEV100_1P P_SEV120_1P_PUB
$P $S/roster_patch.py "$OUT" set-name 33 P_SEV100_1P P_SEV120_2P_PUB
$P $S/roster_patch.py "$OUT" set-name 33 P_SEV100_1P P_SEV120_3P_PUB
$P $S/roster_patch.py "$OUT" set-name 33 P_SEV100_2P P_SEV120_2P
$P $S/roster_patch.py "$OUT" set-name 33 P_SEV100_3P P_SEV120_3P

echo "== test 20: plain EBOOT + unlock"
$P $S/eboot_plain.py "$OUT"
echo "== test 21: own save record"
$P $S/spot33_save.py "$OUT"
echo "== test 22: name key sev120"
$P $S/spot33_names.py "$OUT"
echo "== test 23: Quick Battle grid picture 12"
$P $S/roster_patch.py "$OUT" qb-row 33 33 12 6
echo "== test 24: own voice files"
$P $S/spot33_voice.py "$OUT"
echo "== test 28: own line ids + subtitles"
$P $S/voice_lines.py test28 "$OUT"

echo "== Cloud back to vanilla (D-313-01)"
$P $S/spot33_cloudvanilla.py "$OUT" "$CLEAN"
$P $S/spot33_cloudvanilla.py "$OUT" "$CLEAN" --dry | tail -1
echo "base ready: $OUT"
sha256sum "$OUT"
