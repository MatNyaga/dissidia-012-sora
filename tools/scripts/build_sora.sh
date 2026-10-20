#!/bin/bash
# Build Sora's model file (obj/P_SEV120_1P.gmo for roster spot #33) from Mat's KH2 extraction, end to end.
#
#   tools/scripts/build_sora.sh [ISO_IN ISO_OUT]
#
# Without arguments: builds dumps/models/sora_final.gmo (+ Blender-ready previews in dumps/models/sora/).
# With ISO_IN ISO_OUT: also copies ISO_IN to ISO_OUT and puts the model into it (spot #33).
# From the CLEAN dump (release path, QA D-313-03), two commands:
#   tools/scripts/bootstrap_base.sh dumps/ULUS10566-base-fromclean.iso      (clean copy + tests 14-28 setup, ~1 min)
#   tools/scripts/build_sora.sh dumps/ULUS10566-base-fromclean.iso dumps/ULUS10566-testNN.iso   (~20-40 min)
# (dumps/ULUS10566-test28-lines.iso still works as ISO_IN; spot33_cloudvanilla.py below removes its Cloud leftover.)
# Steps (docs/GUIDE.md part 6–7 explain each one):
#   1 gmo_resize.py   Cloud's skeleton + all 86 animations get Sora's bone lengths
#   2 gmo2gltf.py     that skeleton → glTF (Blender format) so the fit can read it
#   3 fit_sora.py     Sora's KH2 mesh bent onto that skeleton (arms down, fist, weights)
#   4 add_keyblade.py Kingdom Key into the hand (KH2's own grip, palm bone 178)
#   5 gltf2gmo.py     back to the game's model format
#   6 kh2_retarget.py / pose_author.py / kh2_attack.py / kh2_combo.py: animations into Dissidia slots (MOTIONS)
# With ISO_IN ISO_OUT also: voice bank, menu move names, amas row, name banner.
set -e
cd "$(dirname "$0")/../.."
S=tools/scripts
M=dumps/models
KH2=kh2_export
MSET=$KH2/raw/kh2_sixth/original/obj/P_EX100.mset
# Dissidia motion slot = KH2 mset entry (baked into dumps/kh2anim by tools/kh2bake)
# entry = DISSIDIA_SLOT=KH2_INDEX[@STEP]  (STEP < 1 = slower)
#       | DISSIDIA_SLOT=KH2_INDEX~SPEEDS   (piecewise, e.g. 0.5:1,1:0.4 = normal first half, then 0.4x)
#       | DISSIDIA_SLOT=pose:FILE.py       (hand-made, tools/poses/)
#       | DISSIDIA_SLOT=atk:KH2_INDEX:HIT[,HIT2][:match]  (attack retimed onto the hit frames; :match = weapon chain
#         blended to Cloud's around the hit, because the hitbox follows the weapon — needed for the ground finisher)
#         :env=K=V,K=V (very last) = extra env for kh2_attack.py (MATCH_AT, MATCH_SCALE)
#         :end=N (after the others) = new animation length in frames
#         :mslot=_630A = match to ANOTHER slot's Cloud motion (slot whose script block is a copy, spot33_chain COPY)
#       | DISSIDIA_SLOT=nat:KH2[,KH2…]  (natural speed, no warp/match; the slot's script block is AUTHORED to KH2's own
#         hit moments: kh2_hits.py + spot33_chain.py AUTHOR)
#       | DISSIDIA_SLOT=combo:KH2,KH2,…:HIT,HIT,…  (several KH2 clips chained, every swing on a hit frame)
#       | DISSIDIA_SLOT=burst:KH2,…:HIT,…|-     (combo + root placement and weapon matched to Cloud's EX Burst shot)
#       optional after the KH2 part: :A-B = only KH2 frames A..B, #N = loop the last N frames (#all = whole)
# movement (motion ids from the live log, notes/gmo-format.md "Motion ids"): run 2, jump 100, air 101, land 102,
# double jump 103, ground dodge 400, air dodge 440, block 470, air block 471
# dodge (R+X): 400 _100A = away / sideways (Sora keeps facing the foe; Mat: "R+X backwards dodges forwards") = the
# BACKWARD HOP that opens KH2 Guard Break (660 frames 0-11), stretched to the slot (838 reversed played the stand-up
# first and the roll last — "very off", test 142). 460 _150A = toward the foe (was still Cloud's) = KH2 838 forward roll
MOVES="_010A=8#all _020A=14 _021A=18#all _022A=22:42-55 _023A=806 _100A=combo:660/0-11:- _150A=nat:838 _140A=818@0.5 _160A=168:0-16 _161A=172"
# getting hit: 500/501 ground hit, 550/560/561 air hit, 700 blown away, 701 flying, 702 land + get up, 754 air recover
# hurt clips slowed to Cloud's lengths (30/30/46 frames): hitstun seems to follow the hurt animation — Sora's short
# KH2 clips (13/19/36) let a CPU Sora escape combos (test 129 log: back to idle between hits). STEP < 1 = slower.
HITS="_200A=42@0.43:0-29 _201A=46@0.43:0-29 _210A=58@0.63:0-29 _211A=62@0.63:0-29 _400A=66:5-13 _401A=66:4-7#all _403A=70 _414A=162"
# 600/610 _300A, 601/611 _310A = follow-up hits inside a combo; 750/751/752 _410A/_411A/_413A = blown the other
# way (same build as 700-702); 911 _043A = recoil after hitting a block, 901 _041A = the other recoil
HITS="$HITS _300A=42@0.78:0-45 _310A=46@0.78:0-45 _410A=74 _411A=74:4-7#all _413A=78 _043A=50 _041A=54"
# dash (Triangle): 202/209 start _070A, 200/203 loop _051A, 201 end _052A (air dash seen live: 202 → 203 → 201);
# ground dash 210 loop _071A, 211/212 stop _074A/_072A — KH2 810 (A160) start, 814 (A150 glide) loop, fall / land
DASH="_070A=810 _051A=814#all _052A=18 _071A=814#all _072A=22:0-14 _074A=22:0-14"
# R+Triangle = call the Assist: 240/242/244/800 _500A, 241/801 _501A → KH2 550 CALL_FRIEND (Sora calls a friend)
ASSIST="_500A=550 _501A=550"
MOVES="$MOVES $HITS"   # ASSIST off: R+Triangle (240/241 _500A/_501A) is the homing DASH, not an assist call (Mat)   # DASH off: Mat wants Dissidia's own dash back (KH2 810 start looked like a summon)
# attacks (atk:KH2:hit[,2nd hit]; hit = middle of the hitbox window in SCRIPT frames = 60/s, the tools halve it)
GROUND="_600A=atk:604:14 _601A=atk:608:13 _602A=atk:620:18:match=38 _600B=atk:612:13 _610A=atk:656:31,39 _611A=atk:648:11 _640A=atk:616:15 _702A=atk:644:37"
AIR="_612A=atk:732:13:match=29 _620A=atk:724:12,28:match=22 _620B=atk:728:19:match=37 _621A=atk:732:18:match=34 _630B=nat:768 _720A=nat:668 _705A=nat:660 _707A=nat:788 _630A=atk:776:40,69 _650A=nat:772/0-22,772 _651A=nat:772 _721A=nat:772 _722A=nat:764 _723A=nat:784 _724A=nat:776 _725A=nat:652,664 _727A=nat:652 _728A=nat:664 _729A=nat:688 _730A=nat:228 _731A=nat:252 _732A=nat:240 _733A=nat:232 _734A=nat:256 _735A=nat:244 _726A=nat:776"
# HP attacks: 3-hit ground HP = Fire cast x3, 10-hit ground HP = full KH2 ground combo, 6-hit air HP = KH2 air
# combo, air HP 1 = big aerial finisher, air HP 2 = upward finisher
HP="_700A=combo:224,224,224:41,79,119 _703A=nat:648 _706A=combo:724,728,732,736,768:33,47,63,75,87,141 _704A=atk:776:54 _704B=atk:788:35"
# EX Burst (motions 8000-8600 = Cloud's Omnislash slots _801A-_813A, notes/gmo-format.md "EX Burst"): burst:CLIPS:HITS
# = combo with FOLLOW (root placement + facing from Cloud's shot, so the camera still frames Sora) and MATCH (weapon on
# Cloud's sword path at each hit). HITS '-' = no hit, clip stretched to the slot.
#   _801A opening 2 hits, _801B "tap Circle" power-up (Drive Form pose), _802A/_803A dashes (glide poses),
#   _803B-_807A slashes, _812A final blow (success), _812B 9-hit flurry, _812C other finish, _813A end
# KH2 Limit Form = Ars Arcanum (+ Sonic Rave dash) for every burst shot (notes/kh2-limit.md; Mat: "KH look, not FF7").
# _801A/_801B/_812A are then overwritten by Codex's versions below (gmo_motion take).
BURST="_801A=burst:k884/0-45:14,55 _801B=burst:k844:- _802A=burst:k848:- _803A=burst:k848:- _803B=burst:k888:23 _804A=burst:k892:23 _805A=burst:k896:23 _806A=burst:k900:23 _807A=burst:k904:23 _812A=burst:k908:123 _812B=burst:k884:7,27,50,67,81,95,109,121,133 _812C=burst:k908:104,119 _813A=burst:22:-"
MOVES="$MOVES $GROUND $AIR $HP $BURST"
MOTIONS="$MOVES _000A=0 _910A=pose:tools/poses/win_combo.py _911A=pose:tools/poses/loss_kneel.py _404A=pose:tools/poses/ko_kh2.py _736A=210@1.6:0-30 _900A=pose:tools/poses/intro_spin.py _902A=pose:tools/poses/intro_b.py"
# idle; _910A = WIN (Fire finisher → twirl → shoulder); _911A = LOSS (kneel); intro = shoulder rest + head scratch, then twirl into stance

python3 -I $S/gmo_resize.py dumps/package/01193_1b867bde_t1.gmo $KH2/model/sora.glb $M/cloud_sorasize.gmo
mkdir -p $M/cloud_sorasize
python3 -I $S/gim.py --gmo $M/cloud_sorasize.gmo $M/cloud_sorasize >/dev/null
python3 -I $S/gmo2gltf.py $M/cloud_sorasize.gmo $M/cloud_sorasize >/dev/null
rm -rf $M/sora/fitn $M/sora/keyn $M/sora/keyn2
NATURAL=1 python3 -I $S/fit_sora.py $KH2/model/sora.glb $M/cloud_sorasize/cloud_sorasize.gltf $M/sora/fitn
# Keyblades: wep0 = normal weapon (Cloud: Buster Sword) = Kingdom Key; wep1 = EX Mode weapon (Cloud: Ultima Weapon,
# glowing texture animation) = KH2 Ultima Weapon (EX_KEY=oathkeeper/oblivion to try others)
KH2_ATTACH=${KH2_ATTACH:-off} KEY_SCALE=1.0 python3 -I $S/add_keyblade.py $M/sora/fitn/sora_fit.gltf $KH2/keyblade/kingdom_key.glb $M/sora/keyn wep0 1
GRIP_JSON=$M/sora/fitn/sora_fit.grip.json KH2_ATTACH=off KEY_SCALE=${EX_KEY_SCALE:-0.685} python3 -I $S/add_keyblade.py $M/sora/keyn/sora_fit_key.gltf $KH2/keyblades/${EX_KEY:-ultima_weapon}/${EX_KEY:-ultima_weapon}.gltf $M/sora/keyn2 wep1 1   # Ultima 1.96 m vs Kingdom Key 1.34 m → 0.685 = same length (Mat: it went through him)
REBUILD_WEAPONS=1 NEW_SCALE=1 python3 -I $S/gltf2gmo.py $M/cloud_sorasize.gmo $M/sora/keyn2/sora_fit_key_key.gltf $M/sora_natural.gmo

cp $M/sora_natural.gmo $M/sora_final.gmo
# Rule (notes/hitbox-shapes.md §9): a slot's animation must last >= its script (last op 0x02 / op 0x28 / op 0x0a
# end <= 2 x last frame), else Sora hangs in the last pose (Magnet Burst end=47 did: Mat "stuck after").
# NEW animation slots (motion 87+; 86 = _719A = copy of the win pose: the game takes the results CAMERA from motion 86)
# NEW animation slots (motion 86+), each paired with a p_se block + motion id in spot33_chain.py SLOTS (same order)
SLOTS="_719A=_910A _720A=_630A _721A=_706A _722A=_630A _723A=_640A _724A=_630A _725A=_700A _726A=_704A _727A=_600A _728A=_700A _729A=_706A _730A=_701A _731A=_705A _732A=_701A _733A=_707A _734A=_707A _735A=_707A _736A=_501A"   # _736A = own EX Mode start (spot33_exmode.py); Finishing Leap, Horizontal Slash, Aerial Sweep, Aerial Dive
python3 -I $S/gmo_motion.py append $M/sora_final.gmo $M/sora_final.gmo $SLOTS
for pair in $MOTIONS; do
    dst=${pair%%=*}; rest=${pair#*=}
    if [[ $rest == nat:* ]]; then                         # nat:KH2[,KH2…] = KH2 frames at natural speed (own AUTHOR block)
        NATURAL=1 python3 -I $S/kh2_combo.py $M/sora_final.gmo $M/sora_final.gmo $dst ${rest#nat:} -
        continue
    fi
    if [[ $rest == combo:* ]]; then                       # combo:KH2,KH2,...:HIT,HIT,... (several clips, many hits)
        a=${rest#combo:}
        python3 -I $S/kh2_combo.py $M/sora_final.gmo $M/sora_final.gmo $dst ${a%%:*} ${a#*:}
        continue
    fi
    if [[ $rest == burst:* ]]; then                       # burst:KH2,...:HIT,...|- (EX Burst shot)
        a=${rest#burst:}
        FOLLOW=1 MATCH=1 python3 -I $S/kh2_combo.py $M/sora_final.gmo $M/sora_final.gmo $dst ${a%%:*} ${a#*:}
        continue
    fi
    if [[ $rest == atk:* ]]; then                         # atk:KH2_INDEX:HIT[,HIT2] = attack timed to the hitbox
        a=${rest#atk:}; idx=${a%%:*}; hits=${a#*:}; match=""; mslot=""
        aenv=""; [[ $hits == *:env=* ]] && { aenv=${hits##*:env=}; hits=${hits%:env=*}; }        # extra env K=V,K=V (last)
        aend=""; [[ $hits == *:end=* ]] && { aend=${hits##*:end=}; hits=${hits%:end=*}; }          # new length (frames)
        [[ $hits == *:mslot=* ]] && { mslot=${hits##*:mslot=}; hits=${hits%:mslot=*}; match=1; }   # match to another slot's Cloud motion
        [[ $hits == *:match ]] && { hits=${hits%:match}; match=1; }
        mfrom=""; [[ $hits == *:match=* ]] && { mfrom=${hits##*:match=}; hits=${hits%:match=*}; match=1; }
        bin=$(ls dumps/kh2anim/$(printf %03d $idx)_????.bin 2>/dev/null | head -1)
        if [ -z "$bin" ]; then
            DOTNET_ROOT=$PWD/tools/dotnet-sdk DOTNET_ROLL_FORWARD=Major tools/dotnet-sdk/dotnet tools/kh2bake/bake/out/bake.dll \
                $KH2/model/P_EX100.mdlx $MSET dumps/kh2anim $idx >/dev/null
            bin=$(ls dumps/kh2anim/$(printf %03d $idx)_????.bin | head -1)
        fi
        env ${aenv//,/ } ${aend:+END=$aend} ${match:+MATCH=1} ${mfrom:+MATCH_FROM=$mfrom} ${mslot:+MATCH_SLOT=$mslot MATCH_MODEL=$M/cloud_sorasize.gmo} python3 -I $S/kh2_attack.py $M/sora_final.gmo $bin $M/sora_final.gmo $dst ${hits//,/ }
        continue
    fi
    if [[ $rest == pose:* ]]; then
        python3 -I $S/pose_author.py ${rest#pose:} $M/sora_final.gmo $M/sora_final.gmo $dst
        continue
    fi
    loop=""; rng="-"
    [[ $rest == *#* ]] && { loop=${rest#*#}; rest=${rest%%#*}; }
    [[ $rest == *:* ]] && { rng=${rest#*:}; rest=${rest%%:*}; }
    idx=${rest%%[@~]*}; step=1; speed=""
    [[ $rest == *@* ]] && step=${rest#*@}
    [[ $rest == *~* ]] && speed=${rest#*~}
    suffix=""; [ "$step" != 1 ] && suffix="_s$step"
    [ -n "$speed" ] && suffix="_v$(echo $speed | tr ':,' 'x_')"
    pat="dumps/kh2anim/$(printf %03d $idx)_????$suffix.bin"
    bin=$(ls $pat 2>/dev/null | head -1)
    if [ -z "$bin" ]; then
        env ${speed:+SPEED=$speed} STEP=$step DOTNET_ROOT=$PWD/tools/dotnet-sdk DOTNET_ROLL_FORWARD=Major tools/dotnet-sdk/dotnet tools/kh2bake/bake/out/bake.dll \
            $KH2/model/P_EX100.mdlx $MSET dumps/kh2anim $idx >/dev/null
        bin=$(ls $pat | head -1)
    fi
    env ${loop:+LOOP=$loop} python3 -I $S/kh2_retarget.py $M/sora_final.gmo $M/sora/fitn/sora_fit.map.json $bin $M/sora_final.gmo $dst $rng
done

# empty the slots #33 no longer plays (their pieces moved to new slots: Cross-slash _700A, Braver _704A/_704B/_704C,
# Aerial Flurry _706A/_706B, AIR_MIDDLE1 _630A, Blade Beam _702A, Fire spells _701A) → smaller GMO (2.42 MB in test 145;
# limit somewhere in 2.25-2.82 MB; Mat: "in the win animation he suddenly vanished")
STUBS="_719A=_910A _700A=_401A _704A=_401A _704B=_401A _704C=_401A _706A=_401A _706B=_401A _630A=_401A _702A=_401A _701A=_401A"
python3 -I $S/gmo_motion.py copy $M/sora_final.gmo $M/sora_final.gmo $STUBS
# Codex (ChatGPT) EX animations, Mat 2026-10-15 "use ChatGPT's ex intro animations" (docs/CLAUDE-INTRO-HANDOFF-20261015.md,
# codex/README.md): EX Mode LIGHT! activation (their _740A -> our own EX slot _736A, motion 5000 via spot33_exmode.py),
# EX Burst opening strikes _801A (KH2 K410 retimed) and the approved charge-strain tap-Circle loop _801B. Motion blocks
# only (their GMOs carry an older model snapshot; same 54-bone skeleton). Runs after MOTIONS/STUBS, before keychain.
CX=codex/EX-openings
python3 -I $S/gmo_motion.py take $M/sora_final.gmo $M/sora_final.gmo $CX/exports/codex_ex_activation.gmo _736A=_740A
python3 -I $S/gmo_motion.py take $M/sora_final.gmo $M/sora_final.gmo $CX/exports/codex_ex_burst_opening.gmo _801A=_801A
python3 -I $S/gmo_motion.py take $M/sora_final.gmo $M/sora_final.gmo $CX/charge-strain-v2/exports/codex_charge_strain.gmo _801B=_801B
python3 -I $S/gmo_motion.py take $M/sora_final.gmo $M/sora_final.gmo codex/EX-finisher/exports/codex_ex_break.gmo _812A=_812A   # Codex Ars Arcanum finisher (K416) = the "break"
# Codex timed solo Trinity EX (tools/codex/20261015-ex-timed, strikes on the existing hit windows; test215 ✅ plays
# through): replaces the _812A above + _812B flurry + _812C grand finish. Built by Claude with the bone-51 assert off.
python3 -I $S/gmo_motion.py take $M/sora_final.gmo $M/sora_final.gmo codex/EX-timed/exports/codex-ex-timed.gmo _812A=_812A _812B=_812B _812C=_812C
# model memory: the GMO must stay ≤ ~2,506,640 B (2,523,344 crashed at battle start, test215) → thin the win-camera
# hook motion _719A (every 2nd rotation/root key; -26.9 KB)
python3 -I $S/gmo_thin.py $M/sora_final.gmo $M/sora_final.gmo _719A:2
# victim blown-away clips = Cloud's full tumbles (keys 0-73, range 45-73) on Sora's skeleton, every 2nd key (+~3 KB).
# The EX FINAL BLOW / HIT! scenes show the loser in _400A; our one-pose KH2 66 clip read as "Sora just stands there"
# (Mat, test211/220). Probe 2026-10-16: test243 (2P _400A scrambled) = crumpled loser, test244 (Cloud's _400A) = loser
# tumbles upside-down. NB the CPU in a mirror match uses the 2P model (spot33_2p.py), so patch discs must update 2P/3P too.
python3 -I $S/gmo_motion.py take $M/sora_final.gmo $M/sora_final.gmo $M/cloud_sorasize.gmo _400A=_400A _410A=_410A
python3 -I $S/gmo_thin.py $M/sora_final.gmo $M/sora_final.gmo _400A:2 _410A:2
# test288 full build: today's take+thin gives other bytes (+156 B) than the Mat-approved test245 tumble -> take the
# approved motions themselves (dumps/models/tumble_approved.gmo = test245's 1P model; _400A b77de095… / _410A 009188e2…).
python3 -I $S/gmo_motion.py take $M/sora_final.gmo $M/sora_final.gmo $M/tumble_approved.gmo _400A=_400A _410A=_410A
# (kept, now a no-op: the taken clips already run 45-73)
python3 -I $S/gmo_retime.py $M/sora_final.gmo $M/sora_final.gmo _400A=45-73 _410A=45-73
if [ -n "$2" ]; then
    # ISO_IN must already have spot #33 set up (tests 14-28: roster, save record, names key, voice files):
    # tools/scripts/bootstrap_base.sh makes that base from the clean dump (or the old dumps/ULUS10566-test28-lines.iso)
    cp "$1" "$2"
    # Cloud = vanilla (QA D-313-01): drops the test-24 experiment (action 1020 / hit 0xFF0 in p_sev100.objx + _w,
    # ablt 0x0d00 -> 1020) a test28-lines base still carries; "no change" on a bootstrap base. Reads the clean dump only.
    python3 -I $S/spot33_cloudvanilla.py "$2" dumps/ULUS10566.iso
    # keychain v3 (wep0 pendulum under r_wep, 54 bones; Mat test192: "the keychain is perfect"). v1 (new bones) crashed.
    python3 -I $S/keychain.py $M/sora_final.gmo $M/sora_final_kc.gmo                # keychain (notes/gmo-format.md "Keychain v3")
    # Codex strained-angry face for the EX power-up (face ID 6 atlas; codex/EX-face, test217). Reads the objx only to
    # check the 8101 route; the script byte is set later by spot33_exface.py.
    OX=$(mktemp --suffix=.objx); python3 -I -c "import sys; sys.path.insert(0, '$S'); import fep_edit as E; open('$OX', 'wb').write(E.load_objx('$2', 'obj/p_sev120.objx'))"
    # PACKED variant (Codex, Q-20261015-CODEX-003): strain face in the existing eye atlas, +32 B (no extra thinning)
    OPENBLAS_NUM_THREADS=1 python3 -B codex/EX-face/packed/build_packed.py $M/sora_final_kc.gmo $OX --out $M/exface >/dev/null && cp $M/exface/charge-face-packed.gmo $M/sora_final_kc.gmo; rm -f $OX
    # Reflect cast animation (Codex, tools/codex/20261016-reflect-gap: KH2 spell 284/A362 ground, 292/A371 air, retargeted
    # onto the guard's 0-16 / 0-20; built from the FINAL model incl. keychain wep0 curves → taken after keychain + packed
    # face). EX GUARD ONLY (Mat test247): the cast goes into the dead slots _702A/_706B (EX motions 10318/10319 via the
    # stance table, spot33_exguard.py ISO part at the end), _160A/_161A keep the old guard; 4 dead stubs → _070A copies
    # pay for it. Model 2,497,336 B (notes/reflect.md §14).
    python3 -I $S/spot33_exguard.py --gmo $M/sora_final_kc.gmo $M/sora_final_kc.gmo tools/codex/20261016-reflect-gap/prototype/guard-v2/guard-reflect.gmo
    # EX Burst = KH2 solo Trinity Limit (Codex, Mat approved v5 "I love it, ship it"; Q-20261015-CODEX-004): only these two
    # motions are taken (after keychain + packed face; exguard --gmo touches other slots): _812A = v5 incomplete (3 hits,
    # lands in battle stance, 85 frames), _812C = continuous A870 full Break (138 frames). Scripts: spot33_trinity.py;
    # controller: spot33_reflect.py TRINITY_CTL=1 (notes/ex-burst-controller.md §16, §19). Model 2,487,252 B (test269).
    # (2026-10-16, Mat "I like it, please ship"): Codex READY versions replace the v5/continuous takes: +24-tick ready
    # gesture, same approved tails; _812A f1269014… / _812C e1c79f95… (camera FOV already in their own fcurves).
    # (2026-10-16 11:40Z, Mat "let's try this ship it"): 3-second wind-up (Codex trinity-ready-3s) replaces the 0.4 s
    # one; then (13:07Z, Mat approved) Codex 2 s SOLO staging replaces it: root 4.5 m away from the enemy for 2 s, own camera,
    # exact combo from tick 136; _812A cecf41e3… / _812C e9a305b0…, model 2,499,028 B (test275).
    python3 -I $S/gmo_motion.py take $M/sora_final_kc.gmo $M/sora_final_kc.gmo tools/codex/20261016-trinity-solo-staging/output/trinity-solo-staged.gmo _812A=_812A _812C=_812C
    # Codex's clips carry burst-camera scale (1,1,1) = 1-degree FOV -> brown screen (Mat test259); FOV 45 like Cloud's.
    # gmo_camfov gives the camera bones their OWN scale fcurve (the shared one = every bone; test262 stretched the body
    # 45x). Codex's camera itself frames both fighters (dumps/renders/trinitycam/test263_codexcam_*.png).
    python3 -I $S/gmo_camfov.py $M/sora_final_kc.gmo $M/sora_final_kc.gmo _812A _812C
    # optional (CAMDONOR=1): Cloud-derived camera of test248's timed Trinity instead (dumps/models/camdonor, retimed) —
    # built for Cloud's root path, frames empty space early in both new clips (test263b_camdonor_*.png); interim only
    [ -n "$CAMDONOR" ] && python3 -I $S/gmo_camcopy.py dumps/models/camdonor $M/sora_final_kc.gmo $M/sora_final_kc.gmo _812A _812C
    # approved tumble AGAIN after keychain (build helper, test316): tumble_approved.gmo is test245's FINAL model, its
    # _400A/_410A already carry the keychain curves; taken before keychain.py they got +156 B each (model 2,499,340 B,
    # same as test288). Taken here the model = the played discs' 2,499,028 B byte for byte (checked vs test314).
    python3 -I $S/gmo_motion.py take $M/sora_final_kc.gmo $M/sora_final_kc.gmo $M/tumble_approved.gmo _400A=_400A _410A=_410A
    python3 -I $S/pkg_put.py "$2" obj/P_SEV120_1P.gmo $M/sora_final_kc.gmo         # model + animations
    # battle voice: Cloud's bank with Sora's KH2 clips (tools/voice/sora_battle_voice.txt)
    VB=dumps/voice_sora
    if [ ! -f $VB/map.txt ]; then echo "voice: run the conversion in notes/voice-and-sound.md §8 first"; else
        python3 -I $S/sscf.py rebuild $VB/cloud_voice.scd $VB/map.txt $VB/sora_voice.scd >/dev/null
        python3 -I $S/spot33_voicex.py $VB/sora_voice.scd $VB/sora_voice.scd              # + KH2 "Freeze!" / "Thunder!" (spell voices)
        python3 -I $S/pkg_put.py "$2" voice/EN/battle/voice_P_SEV120_00.scd $VB/sora_voice.scd
    fi
    python3 -I $S/spot33_movenames.py "$2"                                         # menu move names
    python3 -I $S/spot33_amas.py "$2"                                              # Customization works
    python3 -I $S/spot33_banner.py "$2" tools/art/sora_name_banner.png             # "Sora" header
    python3 -I $S/spot33_battlenames.py "$2"                                       # in-battle move/EX names
    python3 -I $S/spot33_breakgauge.py "$2"                                        # EX Burst gauge: yellow fill + "BREAK" label (Sora's own spec chunks; Cloud unchanged)
    python3 -I $S/spot33_vsname.py "$2" tools/art/sora_name_left.png tools/art/sora_encount.png    # VS/loading names
    python3 -I $S/make_title_art.py >/dev/null                                      # KH2 title-art pictures (Mat)
    cp tools/art/approved/qb_art.png tools/art/qb_art.png                           # Mat-approved Codex portrait (tools/art/20261016-select-portrait) wins over the regenerated one
    python3 -I $S/spot33_faces.py "$2"                                             # face pictures (KH2 journal portrait)
    python3 -I $S/spot33_2p.py "$2"                                                # 2P/3P costume slots = Sora too (mirror match)
    python3 -I $S/spot33_p2fix.py "$2"                                             # P2/P3 costume .cosx/.exex = P1 (EX banner/aura; was Cloud's "Equipped Ultima Weapon!") + text 9 renamed; notes/p2-audit.md
    python3 -I $S/spot33_outfits.py "$2" --no-events                               # outfits 2/3 = Limit / Master, 4/5/6 = Valor / Wisdom / Final (Codex drive-outfits textures; new files + objentry rows + EBOOT costume flags 2/3); after spot33_2p + p2fix; notes/outfits.md
    python3 -I $S/spot33_qbpics.py "$2"                                            # Quick Battle select pictures (tools/art/qb_*.png)
    python3 -I $S/spot33_portrait.py "$2"                                          # check: both portrait GIMs = the approved Codex portrait
    python3 -I $S/spot33_menuart.py "$2"                                          # menu faces (helper, test278): Quick Battle party / Labyrinth / Untold Tale / Level Adjust icons (13 menu-code owner-1 sites → 245, new GIMs); after qbpics + portrait. notes/menu-art.md
    python3 -I $S/spot33_charpanel.py "$2"                                       # □ "Characters" panel (Artifacts / Shop / Customization) crashed on owner 33: FUN_08aff218 uses owner 32's free sprite for Sora + Sora icon textures (network pk entry 129 = id 8321); after qbpics/menuart. notes/menu-art.md
    python3 -I $S/spot33_museum.py "$2"                                            # Museum > Character Files: Sora entry 35 (portrait, name, KH2 profile, 3D viewer); after faces/menuart; notes/menu-art.md
    python3 -I $S/spot33_catalog.py "$2"                                           # PP Catalog: Sora 300 PP (flag 925), KH icons set + Sora avatar, KH2 BGM items; notes/unlocks.md
    python3 -I $S/spot33_ownername.py "$2"                                         # owner→name tables: Records, Friend Card (+Ghost), Labyrinth → "Sora" (name 63); notes/unlocks.md
    python3 -I $S/spot33_combos.py "$2"                                            # KH2-style long combos (Mat)
    python3 -I $S/spot33_moves.py "$2"                                             # extra equippable moves (ablt+text+chrl)
    python3 -I $S/spot33_desc.py "$2"                                              # move descriptions (Customization info panel)
    python3 -I $S/spot33_cmdlist.py "$2"                                           # command charts (Customization → Abilities → □): records 0x2100-0x2116 + texts; notes/ability-text.md
    python3 -I $S/spot33_tips.py "$2"                                              # Battle Tips: "Character Info: KINGDOM HEARTS II" (manual_param.bin row 201 + customize_common group 2 texts 178-185); notes/ability-text.md
    python3 -I $S/spot33_speed.py "$2"                                             # later combo hits come out faster
    python3 -I $S/spot33_chain.py "$2"                                             # combo continues past hit 4
    # KH2 magic HP attacks (Firaga / Thundaga / Blizzaga, ground + air; notes/hp-magic.md) — templates from Cloud's clean file
    MG=$(mktemp --suffix=.objx); python3 -I $S/spot33_magic.py "$2" dumps/ULUS10566.iso --out $MG && [ -s $MG ] && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $MG; rm -f $MG
    python3 -I $S/spot33_spellsfx.py "$2"                                          # KH2 Firaga cast sounds (slots 73-75)
    python3 -I $S/spot33_thunder.py "$2"                                           # Thundaga strikes straight down (after spot33_magic; notes/hp-magic.md)
    python3 -I $S/spot33_exmode.py "$2"                                            # EX Mode start (5000) = own slot _736A, KH2 Drive (after spot33_magic)
    python3 -I $S/spot33_exface.py "$2"                                            # EX power-up (8101) uses face ID 6 = Codex strain face
    python3 -I $S/spot33_ablt_cap.py "$2"                                         # ability table 808 → 832 rows
    python3 -I $S/spot33_lines.py "$2" ${LINES:-tools/voice/sora_lines.txt}   # spoken lines (.at3 + subtitles)
    python3 -I $S/spot33_vsvoices.py "$2"                                          # Mat's approved voices (Codex 20261018-approved-voices, test337): 29 fighters' opening line vs Sora (VOLD cond 2/33, lines 1111-1140 + Lightning 1100 re-pointed), Sora mirror (1143), Sora title call (index 34, days 25/29); GAIN_MODE=match (default, test338) = loudness matched to each speaker's native lines (GAIN_MODE=off = test337); after spot33_lines; notes/voice-and-sound.md
    # own effect package id (Cloud's copy had 0x311C0000 → only one of Cloud / Sora got effects; notes/effects-clash.md)
    FX=$(mktemp --suffix=.objx); python3 -I $S/spot33_effects.py "$2" --out $FX && [ -s $FX ] && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $FX; rm -f $FX
    python3 -I $S/spot33_fx.py "$2"                                                # KH2-looking Explosion burst (notes/kh2-effects.md)
    python3 -I $S/spot33_introcam.py "$2"                                          # intro camera framed for Sora's height (notes/gmo-format.md "Intro camera")
    python3 -I $S/spot33_burstfx.py "$2"                                           # KH2 look for the EX Burst effects (notes/kh2-effects.md)
    python3 -I $S/spot33_firefx.py "$2"                                            # KH2 Fire/Firaga look (notes/kh2-effects.md "Firaga")
    # own KH2 sound slots 70+ in #33's snd_ bank (Explosion start / orb / blast; notes/kh2-effects.md)
    SX=$(mktemp --suffix=.objx); python3 -I $S/spot33_sfx.py "$2" --out $SX && [ -s $SX ] && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $SX; rm -f $SX
    python3 -I $S/spot33_magicfx.py "$2"                                           # KH2 Thundaga/Blizzaga look + spell impact sounds (FXSE; after spot33_sfx, before soundids)
    python3 -I $S/spot33_lightningfx.py "$2" dumps/ULUS10566.iso                     # Lightning's Thunder for Thundaga (size-neutral transplant; notes/kh2-effects.md)
    python3 -I $S/spot33_weaponsfx.py "$2"                                         # Keyblade swing/hit, finisher + EX Burst sounds (Codex set, slots 83-95; after spot33_sfx/magicfx)
    python3 -I $S/spot33_trinity.py "$2"                                           # Trinity Limit scripts: 8501 = 3 Bravery hits, 8500 = 10 A870 windows + final HP (after weaponsfx; Codex event contract)
    python3 -I $S/spot33_reflect.py "$2" --apply-code                              # (TRINITY_CTL: Sora's own burst controller, default ON since test270; TRINITY_CTL=0 = off) EX Mode Reflect: guard unbreakable, melee/HP hits + spells sent back (notes/reflect.md §11-12) + EX_SND
    python3 -I $S/spot33_exspeed.py "$2"                                           # EX Mode ground run x1.10 (owner 33; overlay 0x08b2d380 hook -> EBOOT dead code 0x089a8b24); notes/ex-equipment.md §1
    python3 -I $S/spot33_exitems.py "$2"                                           # items 678 Kingdom Key / 679 Protect Belt (Sora only, owned from start); battle effects = spot33_reflect EXITEMS; notes/ex-equipment.md §2-3
    python3 -I $S/spot33_barrier.py "$2" dumps/ULUS10566.iso                       # EX Reflect barrier = KH2 Reflega faceted shell (ground dome / air sphere, one strip <= 384 vertices each, KH2 TEX1 panels, BARRIER_SCALE env) in dead Cross-slash effect slots, effe stays 848640 B, EX-only op 0x19 in guard blocks (after spot33_reflect: needs its EX sound-81 one-shot; spot33_exguard later copies the blocks; notes/kh2-effects.md "Barrier resource audit")
    python3 -I $S/spot33_sndtrim.py "$2"                                           # empty unreferenced Cloud sound slots (mirror-match memory: BREAK sound / win line)
    python3 -I $S/spot33_soundids.py "$2"                                          # LAST: own sound bank ids 219000/219100 (Cloud vs Sora sounds)
    python3 -I $S/spot33_reflectvoice.py "$2"                                      # EX Reflect says "Back off!" (voice slot 7, EX-only; normal guard keeps "Defense!")
    python3 -I $S/spot33_exguard.py "$2"                                           # LAST: EX guard = Reflect cast (stance table jobp 10: 470/471 → 10318/10319 → blocks 60/67 = copies of 20/21)
    python3 -I $S/spot33_exdamage.py "$2"                                          # EX Mode Bravery damage x1.5 extra (chrp 33 +0x0C 0x803 -> 0xC03; Mat: EX Brv too weak); notes/ex-damage.md
    # --- Codex objx->objx candidates, applied ONCE on top of the finished canonical objx (same order as the played discs
    # test262-269). Never rerun spot33_trinity / canonical effect writers after these; they are NOT re-runnable on their
    # own output (Fire v1 re-applied over v2/v3 changes effe again) — rebuild from scratch instead.
    # Trinity ready events (Codex patch_events.py, after spot33_trinity + soundids: final HP 237-247, one impact 21900091
    # @237, no launch speech; the bar-full voice is the controller callback, spot33_reflect TRINITY_CTL)
    TX=$(mktemp -d); python3 -I $S/pkg_get.py "$2" obj/p_sev120.objx $TX/a.objx && python3 -I tools/codex/20261016-trinity-ready-voice/patch_events.py $TX/a.objx $TX/b.objx && python3 -I tools/codex/20261016-trinity-ready-3s/retime_events.py $TX/b.objx $TX/c.objx && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $TX/c.objx; rm -rf $TX
    # Codex Fire v1 (redesign, --kind fire) -> visibility v2 (fire only) -> appearance v3 (smoothed flame texture);
    # canonical Thundaga stays (Thunder v2 crashed in the air, test262b)
    FX=$(mktemp -d); python3 -I $S/pkg_get.py "$2" obj/p_sev120.objx $FX/a.objx && python3 -B tools/codex/20261016-fire-thunder-redesign/build_candidates.py $FX/a.objx --kind fire --out $FX/b.objx >/dev/null && python3 -B tools/codex/20261016-fire-thunder-visibility-v2/revise.py $FX/b.objx --kind fire --out $FX/c.objx >/dev/null && python3 -B tools/codex/20261016-fire-appearance-v3/build.py $FX/c.objx --out $FX/d.objx >/dev/null && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $FX/d.objx; rm -rf $FX
    # Magnet Burst: KH2 look (replaced Codex stopgap magnet-visible-dispatch, which added Explosion swirl/flash).
    # (spot33_magnet reads the clean dump read-only for its donor leaf.)
    python3 -I $S/spot33_magnet.py "$2" dumps/ULUS10566.iso                       # KH2 Magnet Burst (helper, test277): KH2FM P_EX100 swirl disc + Magnega band/texture, orb + inward rings + burst in block 68, dead TEX 19 / MDL 26,28 / leaves 20,39 / FEPA pool 9130-9141; piece 0xb32 flags 0x10012 (stuck-fall fix). Replaces Codex stopgap. After the Fire chain.
    # Codex louder Trinity final hit (Mat "that's good enough, ship it", 12:56Z): +4.45 dB copy of slot 91 appended as
    # slot 96 (shared 91 kept), only block 80's final cue retargeted. After every Trinity event writer.
    FS=$(mktemp -d); python3 -I $S/pkg_get.py "$2" obj/p_sev120.objx $FS/a.objx && python3 -B tools/codex/20261016-trinity-finisher-level/patch_finisher.py $FS/a.objx $FS/b.objx 96 >/dev/null && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $FS/b.objx; rm -rf $FS
    # Codex 2 s solo staging events: shifts blocks 78/80 by -60 ticks (accepts the 180-tick output above). LAST Trinity writer.
    SO=$(mktemp -d); python3 -I $S/pkg_get.py "$2" obj/p_sev120.objx $SO/a.objx && python3 -I tools/codex/20261016-trinity-solo-staging/retime_events.py $SO/a.objx $SO/b.objx && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $SO/b.objx; rm -rf $SO
    python3 -I $S/spot33_ai.py "$2"                                                # CPU AI (helper, test276): own brat attack table, owner 33 in the brain owner table (battle_non_residing.bin), acab + ablt CPU equip rows; notes/cpu-ai.md
    python3 -I $S/spot33_thundaga.py "$2"                                          # Thundaga v2 (test296): warning column on the foe's spot, then 3 bolts drop on that LOCKED spot (dodgeable), smaller impacts, more end lag; Garland method. Must run AFTER spot33_thunder.py (rebuilds rows 0x7C4/5/9/A); notes/thunder.md
    # Fire "fill hollow flame" (Mat chose it on test287): Codex fire-core-readability, TEX 15 index bytes only (same size)
    FC=$(mktemp -d); python3 -I $S/pkg_get.py "$2" obj/p_sev120.objx $FC/a.objx && python3 -B tools/codex/20261016-fire-core-readability/build.py $FC/a.objx --kind core --out $FC/b.objx >/dev/null && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $FC/b.objx; rm -rf $FC
    # Thunder look (Codex thunder-test305-visual-stack: bolt body x1.5 + smaller flashes, 33 effect bytes; guard = Thundaga v2 magi)
    TL=$(mktemp -d); python3 -I $S/pkg_get.py "$2" obj/p_sev120.objx $TL/a.objx && python3 -B tools/codex/20261016-thunder-test305-visual-stack/build.py $TL/a.objx --kind thunder-body --out $TL/b.objx >/dev/null && python3 -B tools/codex/20261016-thunder-test305-visual-stack/build.py $TL/b.objx --kind thunder-flashes --out $TL/c.objx >/dev/null && python3 -I $S/pkg_put.py "$2" obj/p_sev120.objx $TL/c.objx; rm -rf $TL
    python3 -I $S/spot33_outfits.py "$2" --events-only                             # LAST p_se writer: costume-only trail/sound events -> same for every outfit (outfit 1's); notes/outfits.md §3
    python3 -I $S/spot33_assist.py "$2"                                            # Sora as ASSIST (helper, test279): own p_sev120_a.objx + P_SEV120_*P_A.gmo + assist voice bank, objentry kind-8 + assist.bin owner-33 rows (was Aerith); notes/assist.md  [after events-only: assist file copies the costume-neutral events, QA D-313-04]
    python3 -I $S/spot33_music.py "$2"                                             # LAST: KH2 music (Codex 20261016-kh2-music): KH2TR/KH2WT/KH2SS.AT3 appended to DATA/BGM (ISO dir records), bgm_entry ids 131-133 (auto-picked when Sora is the opponent: owner bit 33, weights TR 32/WT 16/SS 16), bgm_name 132-134, Museum records; keeps every track; notes/music.md
    python3 -I $S/spot33_newtag.py "$2"                                            # yellow NEW tag after buying Sora: unlock row 22 SEEN flag 3623 (Chaos's, already set in saves that saw Sora when he was free) -> 3633 (1 EBOOT word; after spot33_outfits/catalog); notes/unlocks.md §5
    python3 -I $S/spot33_savefix.py "$2"                                           # save safety (RR-01/RR-03, test344c = v2): 25-card saves: existing Sora record kept (count -> 24) or card 25 kept (native "receive card" replaces the oldest unlocked one) before Sora's record is set up in slot 24; one-time chrl catch-up FUN_088cbd24(rec,1,level) marked at record +0x777 (0xC1); helper in dead FUN_088cb2c0; after spot33_save/spot33_moves; notes/release-save-safety.md
    python3 -I $S/spot33_jukebox.py "$2"                                           # Museum > Jukebox: Sora voice group (Encounter/vs/Victory/Loss/Battle, owner 33) + "vs Sora" rows for 30 fighters + museum VOLD copies synced; PP Catalog "Encounter Voice - Sora" 180 PP (flag 888, after flag 925); menu list caps 33->34 (10 words); after spot33_vsvoices/catalog/ownername/music; notes/unlocks.md §6
    python3 -I $S/spot33_viewer.py "$2"                                            # RR-09: Museum viewer owner lookup record 34 -> owner 33 (outfits 4-6 in View Character; 38 menu words in place); after spot33_museum/outfits; notes/release-rr-static-b.md
    python3 -I $S/spot33_assistdup.py "$2"                                         # RR-14: assist picker lists Sora once with the Aerith DLC key (17 EBOOT words in FUN_088d5ac8); notes/release-rr-static-b.md
    python3 -I $S/spot33_oqrecord.py "$2"                                          # RR-18: Original Quest "has record" true for Sora (FUN_089293dc, 21 EBOOT words); after spot33_save; notes/release-rr-static-b.md
    python3 -I $S/spot33_unlockflags.py "$2"                                       # RR-08: KH2 BGM / KH icon / Sora avatar catalog flags = 1263..1267 (vanilla sets 1250-1262 itself: fighter Lv30/50/70 + Lv100 owners); migrates discs with the old 1249-1251/1253/1254, re-checks the flags are free; after spot33_catalog/museum/music; notes/unlocks.md §7
    python3 -I $S/spot33_bgmfallback.py "$2"                                       # RR-08 mode 7: Labyrinth battle vs owner 33 whose BGM pool is empty (KH2 tracks not bought) -> stage music via the mode-0/4 picker (EBOOT FUN_0888b544 case 7 + case-0xC words + jump-table entry 12, 27 words in place); every other opponent unchanged; notes/release-rr-static-b.md
    python3 -I $S/spot33_selectblurb.py "$2"                                       # RR-17: Sora's "[Keyblade Master]" blurb = text id 33 (grid row +6 character number) in the 5 "Play as this character?" blurb groups (chara_select 2, creation_room 5, party_setting 5, story_mode 1, update_list 7); after spot33_catalog/ownername/qbpics; notes/release-rr-static-b.md
    python3 -I $S/spot33_jukeboxgate.py "$2"                                       # RR-08: Museum Jukebox lists ignore the vanilla "show all" flag 1372 for the mod's purchase flags (music records 1263..1270, Sora voice character 925, Encounter Voice rows 888) -> KH2 tracks / Sora voices hidden until bought; 45 OVL_MENU_APP words in place; after spot33_jukebox/music/unlockflags; notes/unlocks.md §7
    python3 -I $S/spot33_oqslot.py "$2"                                            # RR-18: Original Quest menus: owner-33 slot name ("Sora" = full-name entry 122 in creation_room 4 / chara_select 0 / party_setting 6 / story_mode 10), slot face (39th icon handle, FUN_08a62530 + FUN_08a53f58 in place), party row face_r/face/name; after spot33_menuart/selectblurb; notes/dlc-phase1.md RR-18
    python3 -I $S/spot33_grwp.py "$2"                                              # real PSP/Vita: system.bin grwp (Max CP growth) row for owner 33; without it battle setup reads NULL+0x16 and crashes on hardware (PPSSPP ignores); notes/dlc-phase1.md "Vita test"
    python3 -I $S/spot33_menuclock.py "$2"                                         # Vita menu lag (test354): title + menus keep 333/333/166 MHz (boot clock read FUN_08860df8 -> 333 setter, menu setter FUN_08860e78 222/222/111 -> 333/333/166; 5 EBOOT words); notes/dlc-phase1.md "Vita menu lag"
    python3 -I $S/spot33_installfix.py "$2"                                      # LAST: mod-added PACKAGE_INFO rows get install tier 0 → game Data Install sizes 1-3 stay valid (P0.9)
fi
echo "done: $M/sora_final.gmo"
