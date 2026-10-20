"""Sora's EX Mode special = KH2 REFLECT (Mat 2026-10-15: "in EX Mode his block becomes Reflect, which reflects all
damage back at the attacker" / "it reflects everything in KH2"). Design + findings: notes/reflect.md.

DATA part (default; re-runnable, Sora's own file only):
  Sora's guard scripts (motion 470 ground = p_se block 20, 471 air = block 21) get one extra main event:
      op 0x46, frames 0-36 (the guard's own GUARD-hitbox window), condition byte 1 = 2 = "only in EX Mode"
  op 0x46 sets fighter+0x195 bit 0x40 ("send blocked projectiles back at the opponent"; script dispatcher
  FUN_08829930 case 'F'). The projectile/guard code (FUN_08ada0a4 -> FUN_08adaa68 -> FUN_08ada640 -> FUN_08ada2f8)
  then re-aims every projectile his guard repels at his opponent; a reflected projectile keeps its atkp row (the
  caster's own hit data), so the caster takes the damage of his own spell.
  Covers: projectiles whose outcome vs a guard is "repel" (Bravery-type ranged hits). HP magic (atkp kind 3) and
  melee are NOT covered by data — see the CODE part.

CODE part (--apply-code; --code-plan = assemble + size check only). All hook code lives in a CAVE appended to the
BATTLE OVERLAY (OVL_BATTLE_APP.ELF) right after its last byte, at 0x08B62F70 (free up to the EBOOT's second segment at
0x08B63170 = 512 B; no code/data references that range; the game's overlay loader FUN_089331fc reads p_offset +
p_filesz bytes with no size cap, so growing p_filesz loads the cave). The hooks only run in battle, while that
overlay is loaded. (The EBOOT gap 0x089DD3C0-0x089DD4C0 is NOT usable: the same loader writes the overlay's 0x54-byte
ELF header into 0x089DD46C-0x089DD4C0 on every overlay load.)
  hook 1  EBOOT 0x0880a384 (clash resolver FUN_08809f00, before the outcome lookup): if the defender's hit is a guard
          (kind 4) and the defender is Sora in EX Mode -> kind 12 (unbreakable guard: wins vs every attack, incl. HP)
  part 1  MELEE_REFLECT (test221; replaces test184's failed hook 2 at 0x0880a410, which stays original): guarded melee
          Bravery / HP hits go back to the attacker as a FRESH hit through the game's own direct-hit queue:
    C2    EBOOT 0x0880a408 (jal of the defender's FUN_0884a53c apply): defender outcome 3 + incoming melee hitbox hit
          (+0x2c == 1) + touched hit = GUARD + owner == atkp source, main fighter + defender's first clash this frame +
          Sora in EX Mode -> FUN_08808468(Sora, attacker's atkp id | 0x4000, attacker, dir, 1)
    C4    EBOOT 0x08808b74 (FUN_08808ae8's jal FUN_08807860, run next frame by FUN_088076d4): id bit 0x4000 -> strip it,
          atkp SOURCE = the victim (his own move), OWNER/credited = Sora = the game's own "reflected hit" rules:
          Bravery hit: Sora gains / the attacker loses the damage of the attacker's move; HP hit: the attacker takes HP
          damage = his OWN Bravery and his Bravery resets (FUN_088131bc / FUN_08ae5bc8), Sora's Bravery untouched
  hook 3  battle overlay 0x08ada22c (projectile vs hit, FUN_08ada0a4): if the touched hit is Sora's guard in EX Mode
          -> outcome 7 (PROJ_AIM) / 3 (old) for every projectile kind (HP magic included)
  part 2  PROJ_AIM: FUN_08adaa68's outcome jump table grows 7 -> 8 entries (0x08adaaac bound, entry 7 = padding word
          0x08adb32c = C7). C7 = the game's deflect FUN_08ada2f8 aimed at the caster (dir = caster - Sora, normalised)
          instead of FUN_08ada640's random matrix, and (PROJ_ALL) without the "magi row +2 == 0" reflectable check.
          The deflected projectile is Sora's; its next hit has source = caster, owner = Sora (same rules as part 1).
  EX_SND  0x08a3a15c / 0x08a3a374: Cloud's hard-wired EX Burst sounds skipped for owner 33.
  TRINITY_CTL (default ON since test270; TRINITY_CTL=0 = off): Sora's own EX Burst controller TRI written
          over the dead controller-0 variant-1 body 0x08a3a638 (+ table 0x08a3b298), system.bin chrp row 33 +7 = 1 so
          his burst update runs it (no hook site); variant-1-only sites 0x08a3a048 (prompt text) / 0x08a3a094 (early
          banner, owner-33 stub). Off = original bytes + chrp 0. notes/ex-burst-controller.md §14.
  shared  IS_SORA_EX(a0 = fighter): owner byte *(*(fighter+0x2F8)+6) == 33 and FUN_08b34378(fighter) (= in EX Mode)
Disc changes: OVL_BATTLE_APP.ELF grows by the cave (its shstrtab + section headers move behind it; ELF header e_shoff,
phdr filesz/memsz, section 1 size, section 2 offset and the ISO directory record size are updated; the file keeps its
sectors: 780 allocated, 4 spare sectors before OVL_EXTRA_APP.ELF), EBOOT.BIN 2 words x 3 sites, overlay 2 words x 5
sites. Original bytes are checked (all sites before any write); a switch turned off restores its sites' originals;
re-running changes nothing. Cave = 496 B (512 B with PROJ_ALL = False) of the 512 B room.

  python3 -I spot33_reflect.py ISO [--dry] [--code-plan] [--apply-code]   (--apply-code also runs the data part)
"""
import os
import struct
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from comb_patch import pkg_offset, read_at, use_iso  # noqa: E402
from mips_asm import asm  # noqa: E402
from spot33_combos import rebuild_arc  # noqa: E402

FILE = 'obj/p_sev120.objx'
GUARD_MOTIONS = (470, 471)
EVENT = struct.pack('<HHBB6s', 0, 36, 0x46, 0, bytes([0, 2, 0, 0, 0, 0]))   # op 0x46, cond byte 1 = 2 = EX Mode

# ---------------------------------------------------------------------------------------------- code hooks
SECTOR = 2048
EBOOT_ISO = 560 * SECTOR                       # PSP_GAME/SYSDIR/EBOOT.BIN (plain ELF since test 20)
CAVE = 0x08B62F70                              # battle overlay end (0x089DD4C0 + 0x185AB0)
CAVE_END = 0x08B63170                          # EBOOT's second LOAD segment starts here
# This script is the ONE writer of [CAVE, CAVE_END). The 2026-10-15 split (Reflect below 0x08B63100, EX audio cave
# above) is obsolete since 2026-10-16: the EX Burst sound hook (EX_SND) lives in this cave too, so the whole 512 B are
# allocated here (IS_SORA_EX stays first: a re-run recognises its own cave by the first 12 bytes).
OVL_SECTOR, OVL_SIZE, OVL_SECTORS = 185824, 0x185B98, 780      # /PSP_GAME/USRDIR/DATA/OVL_BATTLE_APP.ELF
OVL_BASE, OVL_DATA = 0x089DD4C0, 0x54          # p_vaddr, p_offset
OVL_FILESZ = 0x185AB0                          # original p_filesz
DATA_DIR_SECTOR = 27                           # /PSP_GAME/USRDIR/DATA directory extent


def elf_off(va):
    return 0x1018 + va - 0x8804040


SUB = """
IS_SORA_EX:
    lw t0,0x2f8(a0)
    beq t0,zero,NO
    li v0,0x0
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    bne t0,zero,NO
    nop
    j 0x08b34378
    nop
NO:
    jr ra
    nop
"""
HOOK1 = """
C1:
    li t2,0x4
    bne s0,t2,C1_OUT
    move a0,s3
    jal IS_SORA_EX
    nop
    beq v0,zero,C1_OUT
    nop
    li s0,0xc
C1_OUT:
    j 0x0880a38c
    move a0,s1
"""
# ---- part 1: melee / HP reflect (test221 design, notes/reflect.md §11) -----------------------------------------
# NOT a re-run of the attacker's hit (test184's hook 2 failed: credited fighter stayed the attacker, FUN_088377d0 refused
# hits on a fighter mid-attack, one hit hung the game). Instead a FRESH hit is queued through the game's own direct-hit
# queue FUN_08808468 (EX Burst finishers and script op 8 use it; FUN_088076d4 applies the queue at the start of the next
# hit update via FUN_08808ae8 -> FUN_08807e6c: no clash, no victim-state check). The fresh hit is built by
# FUN_08807860(hit, src, owner, id): atkp SOURCE = the attacker A (his own move row, looked up in his own table), OWNER and
# credited fighter = Sora. That is exactly how the game's own deflected projectiles hit their caster (FUN_08ad9ce4 ->
# FUN_0880b05c(hit, magi+0x108 = caster, proj+0x68 = deflecter, id)), so the damage rules are the game's:
#   Bravery hit: Sora's battle state processes his dealt record (FUN_08ae45b8 -> FUN_08ae6d2c): Sora GAINS, A LOSES the
#                Bravery damage of A's move (Sora's attack vs A's defence); A can be Bravery-broken by his own move.
#   HP hit:      HP damage = FUN_08813510(source = A) = A's OWN Bravery (FUN_088131bc), and because source != owner
#                FUN_08ae5bc8 sends A's battle state (not Sora's) to state 1 (after-HP-attack: A's Bravery resets).
#                Sora's Bravery is untouched. = "A is hit by his own HP attack".
# C2  (EBOOT 0x0880A408, the jal of B's FUN_0884a53c apply in the clash resolver FUN_08809f00; fp = A's hit, s7 = B's
#     touched hit, s3 = B's outcome, sp+0x200 = B): if B's outcome is 3 (guard repelled), the incoming hit is a fighter's
#     melee hitbox (hit +0x2c == 1: class 0x089c6d18 from FUN_0883e108; projectile hits are class 0x089c6ca8 with
#     +0x2c == 0 and are handled by part 2), B's touched hit is a GUARD (atkp kind 4), A = owner == atkp source, A is a
#     main fighter (+0x542 == 0), B has not clashed yet this frame (+0x384 bit 0x20, FUN_0884a53c applies only the
#     first clash per frame) and B is Sora in EX Mode: FUN_08836dac(Sora, A, dir) and
#     FUN_08808468(Sora, A's atkp id | 0x4000, A, dir, 1). Then the original call FUN_0884a53c(s7, fp, s3).
# C4  (EBOOT 0x08808B74, FUN_08808ae8's jal FUN_08807860; s2 = victim): id bit 0x4000 (no atkp id is above 0xd1b — all
#     139 tables on the disc checked) = our mark: strip it and pass the VICTIM as atkp source (a1 = s2).
HOOK2 = """
C2:
    li t2,0x3
    bne s3,t2,C2_GO
    lh t3,0x2c(fp)
    xori t3,t3,0x1
    bne t3,zero,C2_GO
    lw t3,0x34(s7)
    lbu t3,0x4(t3)
    xori t3,t3,0x4
    bne t3,zero,C2_GO
    lw a1,0x18(fp)
    beq a1,zero,C2_GO
    lw t1,0x20(fp)
    bne a1,t1,C2_GO
    lw a0,0x200(sp)
    lbu t1,0x542(a1)
    bne t1,zero,C2_GO
    lw t3,0x384(a0)
    andi t3,t3,0x20
    bne t3,zero,C2_GO
    nop
    addiu sp,sp,-0x30
    sw ra,0x20(sp)
    jal IS_SORA_EX
    nop
    beq v0,zero,C2_RET
    lw a0,0x230(sp)
    lw a1,0x18(fp)
    jal 0x08836dac
    addiu a2,sp,0x10
    lw a0,0x230(sp)
    lh a1,0x24(fp)
    ori a1,a1,0x4000
    lw a2,0x18(fp)
    addiu a3,sp,0x10
    jal 0x08808468
    li t0,0x1
C2_RET:
    lw ra,0x20(sp)
    addiu sp,sp,0x30
C2_GO:
    move a0,s7
    move a1,fp
    j 0x0884a53c
    move a2,s3
"""
HOOK4 = """
C4:
    andi t1,a3,0x4000
    movn a1,s2,t1
    j 0x08807860
    xor a3,a3,t1
"""
# ---- part 2: projectiles (hook 3 + C7) ---------------------------------------------------------------------------
# C3 (overlay 0x08ADA22C in FUN_08ada0a4, replaces jal FUN_08adb330 = projectile-vs-hit outcome): if the touched hit is
# Sora's guard (kind 4 or 12, s1) and he is in EX Mode -> outcome 7 (PROJ_AIM) / 3 (old test219 behaviour), else the
# original table. FUN_08adaa68 (projectile vt+0x2c) dispatches outcomes 0-6 through a jump table at 0x08ADB310;
# PROJ_AIM grows the bound to 8 (0x08ADAAAC sltiu 7 -> 8) and puts C7 into the table's padding word 0x08ADB32C (no
# vanilla table value is 7: the five outcome tables only hold 0-6 / -1). C7 runs inside FUN_08adaa68's frame (s0 =
# projectile, a0 = guarder): dir = normalize(caster+0x80 - Sora+0x80), w = 0, then the game's deflect
# FUN_08ada2f8(proj, Sora, dir, -, t0 = 1 spark, t1 = 0, t2 = 0) - like FUN_08ada640 but aimed instead of random, and
# WITHOUT the "magi row +2 == 0" (reflectable) check. FUN_08ada2f8 makes the projectile Sora's (+0x68), targets his
# target (+0x6c = the caster), drops the old hit; the projectile's next hit (FUN_08ad9ce4) has source = caster, owner =
# Sora -> the caster takes his own spell's damage (same rules as part 1). Exit = FUN_08adaa68's epilogue, v0 = 1
# (= its normal "deflected" return). No caster (+0x68 == 0) -> return 3 (nothing, as before).
HOOK3 = """
C3:
    addiu sp,sp,-0x10
    sw ra,0x0(sp)
    sw a0,0x4(sp)
    sw a1,0x8(sp)
    lw t0,0x100(s0)
    jal IS_SORA_EX
    lw a0,0x1c(t0)
    lw a0,0x4(sp)
    lw a1,0x8(sp)
    lw ra,0x0(sp)
    beq v0,zero,C3_ORIG
    addiu sp,sp,0x10
    xori t0,a1,0x4
    beq t0,zero,C3_REF
    xori t0,a1,0xc
    bne t0,zero,C3_ORIG
    nop
C3_REF:
    jr ra
    li v0,%s
C3_ORIG:
    j 0x08adb330
    nop
"""
HOOK7 = """
C7:
%s    lw a1,0x68(s0)
    beq a1,zero,C7_NONE
    move s1,a0
    addiu a0,sp,0x10
    addiu a1,a1,0x80
    jal 0x089a38e0
    addiu a2,s1,0x80
    addiu a0,sp,0x10
    jal 0x089a3bc8
    addiu a1,sp,0x10
    sw zero,0x1c(sp)
    move a0,s0
    move a1,s1
    addiu a2,sp,0x10
    li t1,0x0
    li t2,0x0
    jal 0x08ada2f8
    li t0,0x1
    j 0x08adad38
    li v0,0x1
C7_NONE:
    j 0x08adad34
    nop
"""
# Switches (each part can be turned off; off = its sites keep / get back their original words):
MELEE_REFLECT = True     # (in-game OK test221, 2026-10-16) part 1 (C2 + C4): guarded melee Bravery / HP hits are sent back (test221; test184 hook 2 retired)
PROJ_AIM = True          # (in-game OK test221, 2026-10-16) part 2 (C7): every projectile his EX guard touches flies back AT the caster (else test219: blocked)
PROJ_ALL = True          # with PROJ_AIM: also projectiles the game marks unreflectable (magi row +2 != 0, e.g. Lightning's);
                         # False = those stay blocked (C7 then checks row +2 like FUN_08adaa68 case 3 does)
C7_ROWCHECK = """    lw t0,0x64(s0)
    lw t0,0x24(t0)
    lh t0,0x2(t0)
    bne t0,zero,C7_NONE
"""                       # (its delay slot = C7's first load, harmless on both paths)
# EX Burst audio (2026-10-16): Cloud's Omnislash routine FUN_08a3a0b8 (battle overlay, shared by Cloud and #33) plays
# the ABSOLUTE ids 2200053 / 2200054 (Cloud's bank) via jal 0x088a24d4 at 0x08a3a15c / 0x08a3a374. #33's burst sounds
# are script-driven now (spot33_weaponsfx EX_BURST), so for owner 33 these calls are skipped (Cloud keeps them). s0 =
# burst controller for the whole function, fighter = *(s0+0); v0 is not used after either call (dumps/ex_snd_disasm.txt).
HOOK_EXSND = """
EX_SND:
    lw t0,0x0(s0)
    beq t0,zero,EXS_PLAY
    nop
    lw t0,0x2f8(t0)
    beq t0,zero,EXS_PLAY
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    beq t0,zero,EXS_SKIP
    nop
EXS_PLAY:
    j 0x088a24d4
    nop
EXS_SKIP:
    jr ra
    nop
"""
# ---- TRINITY_CTL (2026-10-16, notes/ex-burst-controller.md §11-14): Sora's own EX Burst controller ---------------------
# The burst controller of a fighter = system.bin chrp row +6 (index) / +7 (variant). Cloud and #33 are (0, 0) -> update
# FUN_08a39db4 -> variant 0 = Cloud's Omnislash FUN_08a3a0b8. Variant 1 (FUN_08a3a638, 0x08a3a638-0x08a3abc4, 1420 B,
# + its table 0x08a3b298, 160 B) is used by NO chrp row (all 34 checked) and nothing else references it (byte scan of the
# overlay + EBOOT: only FUN_08a39db4's jal at 0x08a39e04). TRINITY_CTL puts TRI there and sets chrp row 33 +7 = 1, so
# Sora's burst update runs TRI with no new hook site. TRI: owner != 33 -> j FUN_08a3a0b8 (Cloud's logic, safety);
# states 0/1 = Cloud's charge (taps < 19, ◯ = FUN_08b326c4, icon flash, grade thresholds + grade effect from TRI_TABLE,
# end at timer >= 180.0 or bar >= 100.0; the shared FUN_08a39db4 keeps the bar easing + CPU taps); at the end of the
# charge the victim is made visible again (FUN_08834df4(1.0, victim) = one-shot op 0x21 [100]) and:
#   grade 4: banner TRI_BANNER_FULL (text 1 = LIMIT BREAK) + bar flash, motion TRI_FULL (8500) -> state 2; after 50.0:
#            banners cleared, banner TRI_BANNER_NAME (text 0 = burst name), bar removed -> state 5
#   grade g < 4: bar removed, motion TRI_INC[g] (Codex v5: 8501/_812A for every grade, once), TRI_FOLLOW queued only
#            if nonzero (now 0 = none) -> state 5
# Burst end, INCOMPLETE only (TRI_EXIT at 0x08a3fca4 in FUN_08a3f448, owner 33 + latched motion 8501): instead of the
#   airborne 8600/_813A + queued 101, Sora goes straight to battle stance: action state 0, motion 1 (_000A) — the
#   game's own neutral exit (same calls as its controller-0x13 path) — at the restored stage position LOWERED by 1.0 m,
#   which undoes the arena-entry lift (FUN_08a3ee44: saved y += 1.0 - height_above_ground when < 1.0), i.e. back on
#   the ground for bursts that started on/near the ground; higher starts stay above ground and the engine's normal
#   airborne check makes him fall (y - 1.0 never goes below the ground). The full route (8500) keeps 8600/_813A.
# Bar-fill voice (Codex controller-candidate/bar-fill-voice.asm, Mat approved "Give me strength!" = voice slot 42 =
#   id 21910042): site 0x08a39ecc in FUN_08a39db4 (the LIMIT bar display setter jal 0x088d9aec = "*(bar) = f12", delay
#   slot or a0,a1,zero kept) -> TRI_BAR_VOICE: does that store for EVERY fighter, then only for owner 33, state 1,
#   grade 4, new fill (state +0x14) == 100.0 and previously DISPLAYED fill < 100.0 -> voice manager
#   FUN_0884ea08(fighter+0xcf0, 21910042, 1) (the game's own voice call, FUN_08b33f8c). Once per charge: the next
#   frame the controller ends the charge (state 2) and the setter is no longer called; a new charge recreates the bar.
#   FIX test271 (Mat test270: never heard): the "previously DISPLAYED fill < 100" test never passed — runtime trace showed
#   the bar element's +0 already equal to the new fill when the callback runs (t2 == f12 every frame) — so the edge is
# HP-attack reflect (test271, Mat test270: Cloud's Cross-Slash / Braver "only blocked, no damage back"): runtime trace
#   vs CPU Cloud showed C2 -> C4 DID reflect, but the guarded hit is the HP attack's first, Bravery part (atkp kind 2,
#   e.g. 0x365 LAND_FINISH1_1): Bravery moves, Cloud recoils, the HP hit (0x367) never comes. C2 now calls TRI_HPROW
#   (in this slot, only when TRINITY_CTL is on): incoming hit row (fp+0x34) kind 2 and not HP -> walk forward in the
#   attacker's own atkp table (sorted ids, max 24 rows) to the next kind-2 row with the HP flag (+8 & 2) and reflect
#   THAT id: the attacker is hit by his own HP attack = HP damage = his own Bravery (FUN_088131bc), Bravery reset.
#   No HP row found / other kinds -> the original id (Bravery reflect as before).
#   Bound (test317, release QA D-313-06): the walk now stays inside the ATTACKER's own atkp table = *(attacker+0x49c)
#   (attacker = hit +0x18; header +4 = row count, rows from +8, as FUN_08837f14 looks them up): a row outside it (the
#   global fallback table) is left alone, and the walk stops at rows + count * 0x44 (and still after 24 rows, as before).
#   now a latch at state +0x60 (the manager zeroes mgr+0x2a0..+0x5e0 at every burst start, FUN_08a3eb70; TRI and the
#   shared cleanup never touch +0x60): first frame with state 1, grade 4, fill == 100.0 -> voice, latch = 1. TRI's grade-4
#   branch also calls TBV_VOICE (same latch), so a charge that ends on the 180-unit timer still says the line once.
# Exit = the manager's own rule (FUN_08a3fe10): the first 8500-8700 motion is latched and the burst ends when it finishes;
# FUN_08a3f448 then plays 8600 on the stage. No Cloud sounds (EX_SND is not reached for #33 any more).
# Variant-1 side sites (only variant 1 reaches them = only #33 through the chrp byte):
#   0x08a3a048: FUN_08a39fa8's variant-1 prompt text 1 -> 2 ("Rapidly tap ◯!" like Cloud)
#   0x08a3a094: vt+0x5c (opening banner) variant != 0/2 -> TRI_B5C: owner 33 -> -1 (no early banner), else 0 (original)
TRINITY_CTL = os.environ.get('TRINITY_CTL', '1') == '1' or '--trinity' in sys.argv    # DEFAULT ON since Mat test270 (Sora + vs CPU Cloud fine, Cloud keeps LIMIT); TRINITY_CTL=0 = off
TRI_BASE, TRI_END = 0x08A3A638, 0x08A3ABC4          # controller-0 variant-1 body = GARLAND's burst (FUN_08a3a638):
TRI_TAB, TRI_TAB_END = 0x08A3B298, 0x08A3B338       # + its table; TRI lived here until test271 -> now always restored
# test272 (notes §21): TRI lives in DEAD EBOOT code FUN_089c1c8c (0x089c1c8c-0x089c2508, 2172 B; no reference from the
# EBOOT, battle, menu or extra overlay). Its first 4 words stay original (probe hook for the dead-code check, disc
# test272p), code from TRI_EB_BASE, the 64-B table at TRI_EB_TAB (last 0x40 B of the range).
TRI_EB_LO, TRI_EB_HI = 0x089C1C8C, 0x089C2508
TRI_EB_BASE, TRI_EB_TAB = 0x089C1C9C, 0x089C24C8
TRI_EB_SHA = 'c14866cbace2279e30ff9e9d4d454e2cd9550fd11c29d33bcd894d7e26083bc9'
TRI_SHA = ('a9e03bfe2030d6d12e66ad2d9edaf02ed7063811af771d5871807fa4ea239226',    # clean bytes of both regions
           '5e034eef0b61ae641cf51456626958ca3e261934e14e798f73fa82f55d4877b3')
TRI_GRADES = [(5, 0x32), (10, 0x33), (15, 0x34), (19, -1)]   # (tap threshold, effect id or -1) = Cloud's table 0x08a3b268
TRI_INC = [8501, 8501, 8501, 8501]                  # motion per incomplete grade 0..3: Codex v5 (Mat approved):
                                                    # EVERY incomplete grade = 8501/_812A once (3 hits, lands in stance)
TRI_FULL, TRI_FOLLOW = 8500, 0                      # TRI_FOLLOW = motion queued after TRI_INC[g]; 0 = none
TRI_BANNER_FULL, TRI_BANNER_NAME = 1, 0             # fighter text indexes (-1 = none)
CHRP_ROW_OWNER, CHRP_VARIANT = 33, 7                # system.bin chrp row of owner 33, byte +7 = burst variant
TRI_TAB_HI, TRI_TAB_LO = (TRI_EB_TAB + 0x8000) >> 16, ((TRI_EB_TAB & 0xFFFF) ^ 0x8000) - 0x8000
TRINITY = """
TRI_DISPATCH:
    lw t0,0x0(a0)
    beq t0,zero,TD_GARLAND
    nop
    lw t0,0x2f8(t0)
    beq t0,zero,TD_GARLAND
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    beq t0,zero,TRI_GO
    nop
TD_GARLAND:
    j 0x08a3a638
    nop
TRI_GO:
    addiu sp,sp,-0x20
    sw s0,0x0(sp)
    sw s1,0x4(sp)
    sw s2,0x8(sp)
    sw ra,0xc(sp)
    sw s3,0x10(sp)
    lui s3,%(hi)s
    addiu s3,s3,%(lo)s
    move s0,a0
    lw a0,0x14(s0)
    lw s1,0x0(a0)
    bne s1,zero,T_S1
    li t0,0x1
    sw t0,0x0(a0)
T_S1:
    lw t1,0x0(a0)
    li t0,0x1
    bne t1,t0,T_S2
    nop
    lw t1,0x4(a0)
    slti t1,t1,0x13
    beq t1,zero,T_END_CHK
    nop
    jal 0x08b326c4
    lw a0,0x0(s0)
    beq v0,zero,T_END_CHK
    lw a0,0x14(s0)
    lw a1,0x4(a0)
    li a2,0x5
    div a1,a2
    mfhi a3
    addu a3,a3,a3
    addu a3,a3,a3
    addu a3,a0,a3
    lw a0,0x44(a3)
    beq a0,zero,T_TAPPED
    li a1,0x3
    jal 0x088d9f5c
    li a2,0x1
T_TAPPED:
    lw a0,0x14(s0)
    lw a1,0x4(a0)
    addiu a1,a1,0x1
    sw a1,0x4(a0)
    lw a2,0x10(a0)
    slti t0,a2,0x4
    beq t0,zero,T_END_CHK
    move t9,s3
    addu t1,a2,a2
    addu t1,t1,t1
    addu t1,t1,t1
    addu t1,t9,t1
    lw t2,0x0(t1)
    bne a1,t2,T_END_CHK
    lw s2,0x4(t1)
    li t0,-0x1
    beq s2,t0,T_GRADE
    nop
    lw a0,0x24(a0)
    beq a0,zero,T_SPAWN
    nop
    jal 0x088a6a78
    nop
T_SPAWN:
    lw a2,0x0(s0)
    lw a0,0x390(a2)
    move a1,s2
    lw a0,0x5c(a0)
    addiu a2,a2,0x4c8
    li a3,0x0
    jal 0x088a9de8
    li t0,0x0
    lw a0,0x14(s0)
    sw v0,0x24(a0)
T_GRADE:
    lw a0,0x14(s0)
    lw a2,0x10(a0)
    addiu a2,a2,0x1
    sw a2,0x10(a0)
T_END_CHK:
    lw a0,0x14(s0)
    lw t1,0x18(a0)
    lui t2,0x4334
    slt t3,t1,t2
    beq t3,zero,T_CHARGE_END
    lw t1,0x14(a0)
    lui t2,0x42c8
    slt t3,t1,t2
    bne t3,zero,T_DONE
    nop
T_CHARGE_END:
    lw a0,0x24(a0)
    beq a0,zero,T_CE1
    nop
    jal 0x088a6c70
    nop
T_CE1:
    lw a0,0x14(s0)
    sw zero,0x24(a0)
    lw a0,0x58(a0)
    beq a0,zero,T_CE2
    nop
    jal 0x088da060
    nop
T_CE2:
    lw a0,0x14(s0)
    sw zero,0x58(a0)
    lw a0,0x4(s0)
    beq a0,zero,T_CE3
    lui a1,0x3f80
    jal 0x08834df4
    mtc1 a1,f12
T_CE3:
    lw a0,0x14(s0)
    lw a2,0x10(a0)
    slti t0,a2,0x4
    bne t0,zero,T_INC
    move t9,s3
    lw a2,0x38(t9)
    lw a1,0x0(s0)
    lui a0,0x89d
    lw a0,0x4dc8(a0)
    li a3,0x1
    jal 0x08856d48
    addiu a0,a0,0x69c0
    lw a0,0x14(s0)
    lw a0,0x5c(a0)
    beq a0,zero,T_F1
    li a1,0x1
    jal 0x088d9f5c
    li a2,0x1
T_F1:
    lw t1,0x14(s0)
    jal TBV_VOICE
    lw t0,0x0(s0)
    move t9,s3
    lw a0,0x0(s0)
    lw a1,0x30(t9)
    mtc1 zero,f12
    mtc1 zero,f13
    addiu a0,a0,0x130
    jal 0x0882fa10
    li a2,0x0
    lw a0,0x14(s0)
    li t0,0x2
    b T_DONE
    sw t0,0x0(a0)
T_INC:
    lw a0,0x5c(a0)
    beq a0,zero,T_I1
    nop
    jal 0x088da060
    nop
T_I1:
    lw a0,0x14(s0)
    sw zero,0x5c(a0)
    lw a2,0x10(a0)
    move t9,s3
    addu t1,a2,a2
    addu t1,t1,t1
    addu t1,t9,t1
    lw a1,0x20(t1)
    lw a0,0x0(s0)
    mtc1 zero,f12
    mtc1 zero,f13
    addiu a0,a0,0x130
    jal 0x0882fa10
    li a2,0x0
    move t9,s3
    lw a1,0x34(t9)
    beq a1,zero,T_I2
    lw a0,0x0(s0)
    mtc1 zero,f12
    mtc1 zero,f13
    jal 0x0882fb90
    addiu a0,a0,0x130
T_I2:
    lw a0,0x14(s0)
    li t0,0x5
    b T_DONE
    sw t0,0x0(a0)
T_S2:
    li t0,0x2
    bne t1,t0,T_DONE
    nop
    lw t1,0x18(a0)
    lui t2,0x4248
    slt t3,t1,t2
    bne t3,zero,T_DONE
    nop
    lui a0,0x89d
    lw a0,0x4dc8(a0)
    jal 0x08856a58
    addiu a0,a0,0x69c0
    move t9,s3
    lw a2,0x3c(t9)
    lw a1,0x0(s0)
    lui a0,0x89d
    lw a0,0x4dc8(a0)
    li a3,0x1
    jal 0x08856d48
    addiu a0,a0,0x69c0
    lw a0,0x14(s0)
    lw a0,0x5c(a0)
    beq a0,zero,T_S2B
    nop
    jal 0x088da060
    nop
T_S2B:
    lw a0,0x14(s0)
    sw zero,0x5c(a0)
    li t0,0x5
    sw t0,0x0(a0)
T_DONE:
    lw a0,0x14(s0)
    lw t1,0x0(a0)
    bne s1,t1,T_TZ
    mtc1 zero,f12
    lwc1 f12,0x18(a0)
    lui a1,0x89d
    lwc1 f13,0x5eac(a1)
    add.s f12,f12,f13
T_TZ:
    swc1 f12,0x18(a0)
    lw s0,0x0(sp)
    lw s1,0x4(sp)
    lw s2,0x8(sp)
    lw s3,0x10(sp)
    lw ra,0xc(sp)
    jr ra
    addiu sp,sp,0x20
TRI_VT5C:
    lw t1,0x8(a0)
    beq t1,zero,V5_M1
    li t0,0x2
    beq t1,t0,V5_M1
    li t0,0x1
    bne t1,t0,V5_ZERO
    lw t0,0x0(a0)
    beq t0,zero,V5_ZERO
    nop
    lw t0,0x2f8(t0)
    beq t0,zero,V5_ZERO
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    bne t0,zero,V5_ZERO
    nop
V5_M1:
    jr ra
    li v0,-0x1
V5_ZERO:
    jr ra
    move v0,zero
TRI_PROMPT:
    lw t0,0x0(s0)
    beq t0,zero,TP_GO
    nop
    lw t0,0x2f8(t0)
    beq t0,zero,TP_GO
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    bne t0,zero,TP_GO
    nop
    li a1,0x2
TP_GO:
    j 0x08a3dbd0
    nop
TRI_EXIT:
    lw t0,0x2f8(a0)
    beq t0,zero,TX_ORIG
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    bne t0,zero,TX_ORIG
    lhu t0,0x1e4(s0)
    li t1,0x2135
    bne t0,t1,TX_ORIG
    nop
    addiu sp,sp,-0x30
    sw ra,0x20(sp)
    jal 0x08834c10
    move a1,zero
    lw a1,0x26c(s0)
    lw t0,0x80(a1)
    lw t1,0x84(a1)
    lw t2,0x88(a1)
    lw t3,0x8c(a1)
    sw t0,0x10(sp)
    sw t1,0x14(sp)
    sw t2,0x18(sp)
    sw t3,0x1c(sp)
    lwc1 f12,0x14(sp)
    lui t0,0xbf80
    mtc1 t0,f13
    add.s f12,f12,f13
    swc1 f12,0x14(sp)
    move a0,a1
    addiu a1,sp,0x10
    jal 0x088359a8
    li a2,0x1
    lw a0,0x26c(s0)
    mtc1 zero,f12
    mtc1 zero,f13
    addiu a0,a0,0x130
    li a1,0x1
    jal 0x0882fa10
    li a2,0x0
    lw ra,0x20(sp)
    addiu sp,sp,0x30
    lui ra,0x8a4
    addiu ra,ra,-0x320
    jr ra
    nop
TX_ORIG:
    j 0x08834c10
    nop
TRI_BAR_VOICE:
    swc1 f12,0(a0)
    lw t0,0(s0)
    beq t0,zero,TBV_DONE
    nop
    lw t1,0x2f8(t0)
    beq t1,zero,TBV_DONE
    nop
    lbu t1,6(t1)
    li t3,33
    bne t1,t3,TBV_DONE
    nop
    lw t1,0x14(s0)
    lw t3,0(t1)
    li t4,1
    bne t3,t4,TBV_DONE
    nop
    lw t3,0x10(t1)
    li t4,4
    bne t3,t4,TBV_DONE
    nop
    lw t3,0x14(t1)
    lui t4,0x42c8
    bne t3,t4,TBV_DONE
    nop
TBV_VOICE:
    lw t3,0x60(t1)
    bne t3,zero,TBV_DONE
    li t3,0x1
    sw t3,0x60(t1)
    addiu a0,t0,0xcf0
    lui a1,0x14e
    ori a1,a1,0x521a
    j 0x0884ea08
    li a2,1
TBV_DONE:
    jr ra
    nop
TRI_HPROW:
    lw t0,0x34(fp)
    lbu t1,0x4(t0)
    xori t1,t1,0x2
    bne t1,zero,HP_RET
    lbu t1,0x8(t0)
    andi t1,t1,0x2
    bne t1,zero,HP_RET
    lw t2,0x18(fp)
    lw t2,0x49c(t2)
    beq t2,zero,HP_RET
    addiu t3,t2,0x8
    sltu t1,t0,t3
    bne t1,zero,HP_RET
    lw t1,0x4(t2)
    li t4,0x44
    mult t1,t4
    mflo t4
    addu t4,t4,t3
    li t5,0x18
HP_LOOP:
    beq t5,zero,HP_RET
    addiu t5,t5,-0x1
    addiu t0,t0,0x44
    sltu t1,t0,t4
    beq t1,zero,HP_RET
    nop
    lbu t1,0x8(t0)
    andi t1,t1,0x2
    beq t1,zero,HP_LOOP
    lbu t1,0x4(t0)
    xori t1,t1,0x2
    bne t1,zero,HP_LOOP
    nop
    jr ra
    lw a1,0x0(t0)
HP_RET:
    jr ra
    nop
"""


# ---- EXITEMS (2026-10-16, Claude equipment helper; notes/ex-equipment.md §3): Sora's own gear builds EX ------------
# Items (rows, names, inventory, Sora-only checks) = spot33_exitems.py; this part = their battle effects, only with
# TRINITY_CTL on (EE_A lives behind TRI in the dead EBOOT function 0x089c1c8c; EE_B + state in the dead function
# 0x089a8b14, sub-range 0x089a8de4-0x089a8f0c owned by THIS script; EE_PROJ behind TRI too). Gauge gain = the game's own event 0x16
# (FUN_08afd170(participant, 0x16, &int) -> EX-gauge listener FUN_08aec558 -> FUN_08aec628: +int to
# *(fighter+0x52c)+0x18, clamp 0..10000, honours the "EX gauge blocked" effects 0x53/0x56) = the route accessory 0x158
# uses in FUN_08aecf30. Participant of fighter F = the entry of *(0x089d69f8)[0..1] whose word 0 is F.
#   EE_HIT  site 0x08ae6ed4 (FUN_08ae6d2c, event 0x10 "Bravery gained from a connected hit" to the attacker's
#           participant): owner 33, the hit is his own (battle state s1+0x10 == participant[0]; no assist hits),
#           damage > 0, NOT in EX Mode (EE_COMBO_IN_EX=1 allows it), Kingdom Key in a slot of his live loadout
#           (*(F+0x30c) record copy, set +0x773, slots +0x10+set*0xc6+0x9a) -> +EE_HIT_GAIN, at most EE_COMBO_CAP per
#           combo (a combo = hits less than EE_COMBO_GAP frames apart, fighter frame counter +0x324).
#   EE_GUARD in C2 (every guarded melee clash, outcome 3, any mode): owner 33; in EX Mode and the incoming row is an
#           HP attack (kind 2 + HP flag, or TRI_HPROW finds its HP row) = HP Reflect -> +EE_HPREF_GAIN (10000 = full
#           refill), INNATE (Mat 2026-10-16: "a HP reflect attack in EX mode should refill the EX gauge"), once per
#           incoming attack (dedup below); every other blocked hit: Protect Belt equipped -> +EE_GUARD_GAIN (1000 =
#           10 % of the bar, Mat 2026-10-17), per hit, no dedup. HP-Reflect dedup = same attacker, same motion +0x180,
#           motion time +0x1a8 not going back, within EE_DUP_FRAMES.
#   EE_PROJ in C7: original collision hit at projectile+0x100 -> EE_GUARD. Kind3 HP magic uses innate
#           full refill and the same caster/motion/time/frame dedup as melee; BRV remains Belt-per-hit.
#           Already-owned projectiles award nothing. Preserve fp and caller s0 across the shared helper.
EXITEMS = TRINITY_CTL and os.environ.get('EXITEMS', '1') == '1'
EE_HIT_GAIN = int(os.environ.get('EE_HIT_GAIN', '100'))
EE_COMBO_CAP = int(os.environ.get('EE_COMBO_CAP', '300'))
EE_COMBO_GAP = int(os.environ.get('EE_COMBO_GAP', '60'))
EE_COMBO_IN_EX = os.environ.get('EE_COMBO_IN_EX', '0') == '1'
EE_GUARD_GAIN = int(os.environ.get('EE_GUARD_GAIN', '1000'))   # Protect Belt: per blocked hit (Mat: 10 % of the bar), no dedup
EE_HPREF_GAIN = int(os.environ.get('EE_HPREF_GAIN', '10000'))   # innate HP-Reflect refill in EX (10000 = full; native add clamps)
EE_DUP_FRAMES = int(os.environ.get('EE_DUP_FRAMES', '180'))
for _v in (EE_HIT_GAIN, EE_COMBO_CAP, EE_GUARD_GAIN, EE_HPREF_GAIN):
    assert 0 <= _v <= 10000, 'EX gains are 0..10000 gauge units'
assert 1 <= EE_COMBO_GAP < 0x7fff and 1 <= EE_DUP_FRAMES < 0x7fff
from spot33_exitems import KK_ID, PB_ID, CP_ID, CROWN_DRAIN  # noqa: E402
EE_B_LO, EE_B_HI = 0x089A8DE4, 0x089A8F0C           # this script's sub-range of the dead function 0x089a8b14 (was 0x089a8da4 until test311)
EE_STATE = EE_B_HI - 0x30                           # 2 x 0x18: combo used, last hit frame, guard attacker/motion/time/frame
EE_DEAD_SHA = '1345b9e14727260640786f74c5a0da3f87f96bc420433447e145e240f01dd10e'   # whole 0x089a8b14-0x089a8f0c
EE_B = """
EE_HAS:
    lw t0,0x30c(a0)
    beq t0,zero,EH_RET
    li v0,0x0
    lb t1,0x773(t0)
    li t2,0xc6
    mult t1,t2
    mflo t1
    addu t0,t0,t1
    li t2,0x4
EH_LOOP:
    lhu t1,0xaa(t0)
    beq t1,a1,EH_YES
    addiu t2,t2,-0x1
    bgtz t2,EH_LOOP
    addiu t0,t0,0x2
EH_RET:
    jr ra
    nop
EH_YES:
    jr ra
    li v0,0x1
EE_PIDX:
    lui t0,0x89d
    lw t0,0x69f8(t0)
    beq t0,zero,EP_NO
    li v0,0x0
    lw t1,0x0(t0)
    beq t1,zero,EP_1
    nop
    lw t2,0x0(t1)
    beq t2,a0,EP_YES
    li v1,0x0
EP_1:
    lw t1,0x4(t0)
    beq t1,zero,EP_NO
    nop
    lw t2,0x0(t1)
    bne t2,a0,EP_NO
    li v1,0x18
EP_YES:
    move v0,t1
    lui t0,0x%(sh)x
    addiu t0,t0,%(sl)s
    addu v1,v1,t0
EP_NO:
    jr ra
    nop
EE_GIVE:
    addiu sp,sp,-0x18
    sw ra,0x10(sp)
    sw a1,0x0(sp)
    li a1,0x16
    jal 0x08afd170
    move a2,sp
    lw ra,0x10(sp)
    jr ra
    addiu sp,sp,0x18
"""
EE_A = """
EE_HIT:
    addiu sp,sp,-0x20
    sw ra,0x10(sp)
    sw a0,0x14(sp)
    sw a2,0x18(sp)
    sw s0,0x1c(sp)
    lw s0,0x0(a0)
    beq s0,zero,HI_OUT
    nop
    lw t0,0x10(s1)
    bne t0,s0,HI_OUT
    lw t0,0x2f8(s0)
    beq t0,zero,HI_OUT
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    bne t0,zero,HI_OUT
    lw t0,0x0(a2)
    blez t0,HI_OUT
    nop
%(exgate)s    move a0,s0
    jal 0x%(has)08x
    li a1,%(kk)d
    beq v0,zero,HI_OUT
    move a0,s0
    jal 0x%(pidx)08x
    nop
    beq v0,zero,HI_OUT
    lw t0,0x324(s0)
    lw t1,0x4(v1)
    lw t2,0x0(v1)
    sw t0,0x4(v1)
    subu t1,t0,t1
    sltiu t1,t1,%(gap)d
    movz t2,zero,t1
    li t3,%(cap)d
    subu t3,t3,t2
    blez t3,HI_OUT
    sw t2,0x0(v1)
    li t4,%(hit)d
    slt t5,t3,t4
    movn t4,t3,t5
    addu t2,t2,t4
    sw t2,0x0(v1)
    move a0,v0
    jal 0x%(give)08x
    move a1,t4
HI_OUT:
    lw a0,0x14(sp)
    lw a2,0x18(sp)
    lw s0,0x1c(sp)
    lw ra,0x10(sp)
    addiu sp,sp,0x20
    j 0x08afd170
    li a1,0x10
EE_GUARD:
    addiu sp,sp,-0x20
    sw ra,0x10(sp)
    sw a0,0x14(sp)
    sw a1,0x18(sp)
    sw s0,0x1c(sp)
    move s0,a0
    lw t0,0x2f8(s0)
    beq t0,zero,EG_OUT
    nop
    lbu t0,0x6(t0)
    xori t0,t0,0x21
    bne t0,zero,EG_OUT
    nop
    jal 0x%(pidx)08x
    nop
    beq v0,zero,EG_OUT
    sw v0,0x0(sp)
    sw v1,0x4(sp)
    jal 0x08b34378
    move a0,s0
    beq v0,zero,EG_BELT
    lw t0,0x34(fp)
    lbu t1,0x4(t0)
    li t2,0x3
    beq t1,t2,EG_HP
    nop
    xori t1,t1,0x2
    bne t1,zero,EG_BELT
    lbu t1,0x8(t0)
    andi t1,t1,0x2
    bne t1,zero,EG_HP
    nop
    jal TRI_HPROW
    li a1,-0x1
    li t1,-0x1
    beq a1,t1,EG_BELT
    nop
EG_HP:
    lw v1,0x4(sp)
    lw t0,0x18(sp)
    lhu t1,0x180(t0)
    lw t2,0x1a8(t0)
    lw t3,0x324(s0)
    lw t4,0x8(v1)
    lw t5,0xc(v1)
    lw t6,0x10(v1)
    lw t7,0x14(v1)
    sw t0,0x8(v1)
    sw t1,0xc(v1)
    sw t2,0x10(v1)
    sw t3,0x14(v1)
    bne t4,t0,EG_FULL
    subu t7,t3,t7
    bne t5,t1,EG_FULL
    slt t6,t2,t6
    bne t6,zero,EG_FULL
    sltiu t7,t7,%(dup)d
    bne t7,zero,EG_BELT
    nop
EG_FULL:
    b EG_GIVE
    li a1,%(hpref)d
EG_BELT:
    move a0,s0
    jal 0x%(has)08x
    li a1,%(pb)d
    beq v0,zero,EG_OUT
    li a1,%(guard)d
EG_GIVE:
    jal 0x%(give)08x
    lw a0,0x0(sp)
EG_OUT:
    lw a0,0x14(sp)
    lw a1,0x18(sp)
    lw s0,0x1c(sp)
    lw ra,0x10(sp)
    jr ra
    addiu sp,sp,0x20
EE_PROJ:
    beq a0,a1,EJ_RET
    nop
    addiu sp,sp,-0x18
    sw ra,0x10(sp)
    sw fp,0x14(sp)
    lw fp,0x100(s0)
    jal EE_GUARD
    nop
    lw fp,0x14(sp)
    lw ra,0x10(sp)
    addiu sp,sp,0x18
EJ_RET:
    jr ra
    nop
"""


# Crown Pendant (item 681, Mat 2026-10-17): EX Mode lasts longer = the EX gauge drain in FUN_08aec000 (battle overlay,
# per frame in EX: drain = 10000 / duration * dt at 0x08aec160 `mul.s f12,f12,f13`) is multiplied by CROWN_DRAIN
# (0.7) when the gauge's fighter (listener s0 +8) has item 681 in his loadout. Site 0x08aec160/64 `mul.s / lwc1 f24`
# -> `jal HELM / lwc1 f24` (in the battle cave, last 12 words); HELM returns with `j 0x08aec168`.
HOOK_HELM = """
HELM:
    .word 0x460d6302
    lw a0,0x8(s0)
    jal 0x%(has)08x
    li a1,%(cp)d
    beq v0,zero,HM_RET
    lui t0,0x%(fh)x
    ori t0,t0,0x%(fl)x
    mtc1 t0,f13
    nop
    .word 0x460d6302
HM_RET:
    j 0x08aec168
    nop
"""


def ee_b_plan():
    """-> (EE_B words, labels) at EE_B_LO"""
    lo = ((EE_STATE & 0xFFFF) ^ 0x8000) - 0x8000
    src = (EE_B % {'sh': (EE_STATE + 0x8000) >> 16, 'sl': ('-0x%x' % -lo) if lo < 0 else '0x%x' % lo,
                   'pb': PB_ID, 'guard': EE_GUARD_GAIN}).strip().split('\n')
    words = asm(src, EE_B_LO)
    labels, pc = {}, EE_B_LO
    for line in src:
        line = line.strip()
        if line.endswith(':'):
            labels[line[:-1]] = pc
        elif line:
            pc += 4
    assert EE_B_LO + 4 * len(words) <= EE_STATE, 'EE_B does not fit before its state words'
    return words, labels


EE_B_WORDS, EE_B_LABELS = ee_b_plan()


def ee_a_source():
    exgate = '' if EE_COMBO_IN_EX else '    jal 0x08b34378\n    move a0,s0\n    bne v0,zero,HI_OUT\n    nop\n'
    return EE_A % {'exgate': exgate, 'has': EE_B_LABELS['EE_HAS'], 'pidx': EE_B_LABELS['EE_PIDX'],
                   'give': EE_B_LABELS['EE_GIVE'], 'kk': KK_ID, 'pb': PB_ID, 'gap': EE_COMBO_GAP + 1,
                   'cap': EE_COMBO_CAP, 'hit': EE_HIT_GAIN, 'guard': EE_GUARD_GAIN, 'hpref': EE_HPREF_GAIN,
                   'dup': EE_DUP_FRAMES}


def ee_b_eboot(f, write):
    """EE_B + zeroed state in 0x089a8de4-0x089a8f0c (clean or ours; EXITEMS off -> clean bytes)"""
    import hashlib
    clean_eb = open(os.path.join(HERE, '../../dumps/extracted/EBOOT.elf'), 'rb').read()
    assert hashlib.sha256(clean_eb[elf_off(0x089A8B14):elf_off(0x089A8F0C)]).hexdigest() == EE_DEAD_SHA
    clean = clean_eb[elf_off(EE_B_LO):elf_off(EE_B_HI)]
    code = b''.join(struct.pack('<I', w) for w in EE_B_WORDS)
    mine = bytearray(clean)
    mine[:len(code)] = code
    mine[EE_STATE - EE_B_LO:] = bytes(EE_B_HI - EE_STATE)
    mine = bytes(mine)
    f.seek(EBOOT_ISO + elf_off(EE_B_LO))
    cur = f.read(EE_B_HI - EE_B_LO)
    older = cur[:0x20] == mine[:0x20]                     # ours with other tunables / live state
    assert cur in (clean, mine) or older, 'EBOOT 0x%08x-0x%08x is neither original nor EE_B: not ours' % (EE_B_LO,
                                                                                                         EE_B_HI)
    want = mine if EXITEMS else clean
    if cur == want:
        print('EE_B EBOOT range 0x%08x: already %s' % (EE_B_LO, 'EE_B' if EXITEMS else 'original'))
    elif write:
        f.seek(EBOOT_ISO + elf_off(EE_B_LO))
        f.write(want)
        print('EE_B EBOOT range 0x%08x: %s' % (EE_B_LO, 'EE_B written' if EXITEMS else 'restored to original'))



def trinity_plan():
    """-> (code words at TRI_EB_BASE, table bytes at TRI_EB_TAB, {label: address})"""
    src = ((TRINITY % {'hi': '0x%x' % TRI_TAB_HI, 'lo': '-0x%x' % -TRI_TAB_LO if TRI_TAB_LO < 0 else '0x%x' % TRI_TAB_LO})
           + (ee_a_source() if EXITEMS else '')).strip().split('\n')
    words = asm(src, TRI_EB_BASE)
    pc, labels = TRI_EB_BASE, {}
    for line in src:
        line = line.strip()
        if line.endswith(':'):
            labels[line[:-1]] = pc
        elif line:
            pc += 4
    assert TRI_EB_BASE + 4 * len(words) <= TRI_EB_TAB, 'TRI does not fit the dead EBOOT range'
    tab = b''.join(struct.pack('<Ii', t, e) for t, e in TRI_GRADES)
    tab += struct.pack('<4I', *TRI_INC) + struct.pack('<IIii', TRI_FULL, TRI_FOLLOW, TRI_BANNER_FULL, TRI_BANNER_NAME)
    assert len(tab) <= TRI_EB_HI - TRI_EB_TAB
    return words, tab, labels


TRI_WORDS, TRI_TAB_BYTES, TRI_LABELS = trinity_plan()
TRI_DISPATCH_ADDR, TRI_VT5C_ADDR, TRI_PROMPT_ADDR = (TRI_LABELS[n] for n in ('TRI_DISPATCH', 'TRI_VT5C', 'TRI_PROMPT'))
TRI_EXIT_ADDR, TRI_BAR_VOICE_ADDR, TRI_HPROW_ADDR = (TRI_LABELS[n] for n in ('TRI_EXIT', 'TRI_BAR_VOICE', 'TRI_HPROW'))
EE_HIT_ADDR, EE_GUARD_ADDR = TRI_LABELS.get('EE_HIT', 0), TRI_LABELS.get('EE_GUARD', 0)
# (address, original words, new words as assembly, switch) — originals from the clean EBOOT / overlay listing; a site
# whose switch is off keeps (or gets back) its original words. 0x0880A410 = test184's old hook 2: always original.
SITES = [(0x0880A384, (0xA3B4020D, 0x02202025), 'j C1\nsb s4,0x20d(sp)', None),         # sb s4,0x20d(sp) / move a0,s1
         (0x0880A410, (0x1256000A, 0x0040F025), None, None),                             # (old hook 2: retired)
         (0x0880A408, (0x0E21294F, 0x02603025), 'jal C2\nor a2,s3,zero', 'MELEE_REFLECT'),  # jal 0x0884a53c / or a2,s3
         (0x08808B74, (0x0E201E18, 0x2408FFFF), 'jal C4\naddiu t0,zero,-0x1', 'MELEE_REFLECT'),  # jal 0x08807860 / t0=-1
         (0x08ADA22C, (0x0E2B6CCC, 0x90840004), 'jal C3\nlbu a0,0x4(a0)', None),         # jal 0x08adb330 / lbu a0,0x4(a0)
         (0x08ADAAAC, (0x2CA30007, 0xAFBF0060), 'sltiu v1,a1,0x8\nsw ra,0x60(sp)', 'PROJ_AIM'),  # jump-table bound 7 -> 8
         (0x08ADB328, (0x08ADAB54, 0x00000000), '.word 0x08adab54\n.word C7', 'PROJ_AIM'),   # table entry 6 / entry 7
         (0x08A3A15C, (0x0E228935, 0x24A591F5), 'jal EX_SND\naddiu a1,a1,-0x6e0b', 'EXSND'),  # EX Burst 2200053 (Cloud only)
         (0x08A3A374, (0x0E228935, 0x24A591F6), 'jal EX_SND\naddiu a1,a1,-0x6e0a', 'EXSND'),  # EX Burst 2200054 (Cloud only)
         (0x08A3A048, (0x0E28F6F4, 0x34050001), 'jal 0x%08x\nori a1,zero,0x1' % TRI_PROMPT_ADDR, 'TRINITY_CTL'),  # prompt: 33 -> text 2
         (0x08A3A094, (0x14850005, 0x00000000), None, None),                             # (old TRI_B5C branch: retired)
         (0x08A3B1BC, (0x08A3A084, 0x00000000), '.word 0x%08x\n.word 0x0' % TRI_VT5C_ADDR, 'TRINITY_CTL'),  # vtable vt+0x5c
         (0x08A39E04, (0x0E28E98E, 0x02002025), 'jal 0x%08x\nor a0,s0,zero' % TRI_DISPATCH_ADDR, 'TRINITY_CTL'),  # variant 1: 33 -> TRI
         (0x08A3FCA4, (0x0E20D304, 0x00003025), 'jal 0x%08x\nor a2,zero,zero' % TRI_EXIT_ADDR, 'TRINITY_CTL'),  # burst end: grounded exit
         (0x08A39ECC, (0x0E2366BB, 0x00A02025), 'jal 0x%08x\nor a0,a1,zero' % TRI_BAR_VOICE_ADDR, 'TRINITY_CTL'),  # bar fill: voice 42
         (0x08AE6ED4, (0x0E2BF45C, 0x34050010), 'jal 0x%08x\nori a1,zero,0x10' % EE_HIT_ADDR, 'EXITEMS'),  # event 0x10 (hit gave Bravery) -> EE_HIT
         (0x08AEC160, (0x460D6302, 0xC6380018), 'jal HELM\nlwc1 f24,0x18(s1)', 'EXITEMS')]  # EX drain -> Crown Pendant  # event 0x10 (hit gave Bravery) -> EE_HIT  # bar fill: voice 42
KNOWN_PATCHED = {0x08ADAAAC: (0x2CA30008,),          # our non-jump site words (sltiu v1,a1,8), for switch-off restores
                 0x08A3A048: (0x34050002,)}          # ori a1,zero,2 (test257-271 prompt patch)
ON = {'MELEE_REFLECT': lambda: MELEE_REFLECT, 'PROJ_AIM': lambda: PROJ_AIM, 'TRINITY_CTL': lambda: TRINITY_CTL,
      'EXITEMS': lambda: EXITEMS,
      'EXSND': lambda: not TRINITY_CTL, None: lambda: True}     # EX_SND only matters when #33 runs Cloud's variant 0


def ours(w, va=None):
    """a word one of our (older) builds put into a site: a j/jal into the cave or into TRI (the variant-1 slot), a cave
    address (jump-table entry), or (with the site address) a branch into TRI (older TRI layouts move TRI_B5C etc.)"""
    if CAVE <= w < CAVE_END or TRI_EB_LO <= w < TRI_EB_HI or EE_B_LO <= w < EE_B_HI:
        return True
    if w >> 26 in (2, 3):
        t = (w & 0x3FFFFFF) << 2 | 0x08000000
        return CAVE <= t < CAVE_END or TRI_BASE <= t < TRI_END or TRI_EB_LO <= t < TRI_EB_HI or EE_B_LO <= t < EE_B_HI
    if va is not None and w >> 26 in (4, 5):
        off = w & 0xFFFF
        t = va + 4 + 4 * (off - 0x10000 if off & 0x8000 else off)
        return TRI_BASE <= t < TRI_END
    return False


def code_plan():
    hook2 = HOOK2
    if TRINITY_CTL:          # HP-attack reflect (test271): kind-2 Bravery hit of an HP attack -> reflect its HP row
        hook2 = hook2.replace('    lh a1,0x24(fp)\n    ori a1,a1,0x4000',
                              '    jal 0x%08x\n    lh a1,0x24(fp)\n    ori a1,a1,0x4000' % TRI_HPROW_ADDR)
        assert hook2 != HOOK2
    hook7 = HOOK7
    if EXITEMS:              # Sora's equipment: guard -> EE_GUARD (C2, after ra is saved), projectile reflect -> EE_PROJ
        h = hook2.replace('    sw ra,0x20(sp)\n', '    sw ra,0x20(sp)\n    jal 0x%08x\n    nop\n' % EE_GUARD_ADDR)
        assert h != hook2
        hook2 = h
        h = hook7.replace('    move s1,a0\n    addiu a0,sp,0x10\n',
                          '    move s1,a0\n    jal 0x%08x\n    move a0,s1\n    lw a1,0x68(s0)\n    addiu a0,sp,0x10\n'
                          % TRI_LABELS['EE_PROJ'])
        assert h != hook7
        hook7 = h
    if EXITEMS:
        fb, = struct.unpack('<I', struct.pack('<f', CROWN_DRAIN))
        helm = HOOK_HELM % dict(has=EE_B_LABELS['EE_HAS'], cp=CP_ID, fh=fb >> 16, fl=fb & 0xFFFF)
    src = (SUB + HOOK1 + (hook2 + HOOK4 if MELEE_REFLECT else '') + HOOK3 % ('0x7' if PROJ_AIM else '0x3') +
           (hook7 % ('' if PROJ_ALL else C7_ROWCHECK) if PROJ_AIM else '') +
           ('' if TRINITY_CTL else HOOK_EXSND) + (helm if EXITEMS else '')).strip().split('\n')
    words = asm(src, CAVE)
    labels, pc = {}, CAVE
    for line in src:
        line = line.split('#')[0].strip()
        if line.endswith(':'):
            labels[line[:-1]] = pc
        elif line:
            pc += 4
    size = 4 * len(words)
    print('cave: %d words = %d bytes at 0x%08x (room up to 0x%08x = %d bytes)%s' %
          (len(words), size, CAVE, CAVE_END, CAVE_END - CAVE, '' if size <= CAVE_END - CAVE else '  ** TOO BIG **'))
    for n in ('IS_SORA_EX', 'C1', 'C2', 'C3', 'C4', 'C7', 'EX_SND'):
        if n in labels:
            print('  %-10s 0x%08x' % (n, labels[n]))
    sites = []
    for va, orig, text, switch in SITES:
        if text is None or not ON[switch]():
            sites.append((va, orig, list(orig)))                 # keep / restore the original instructions
            print('  site 0x%08x: original%s' % (va, ' (%s off)' % switch if switch else ''))
            continue
        t = text
        for n, a in sorted(labels.items(), key=lambda x: -len(x[0])):
            t = t.replace(' ' + n, ' 0x%08x' % a)
        sites.append((va, orig, asm(t.split('\n'), va)))
        print('  site 0x%08x: %08x %08x -> %s' % (va, orig[0], orig[1], ' '.join('%08x' % x for x in sites[-1][2])))
    assert size <= CAVE_END - CAVE, 'cave overflows into the EBOOT second segment at 0x%08x' % CAVE_END
    print('EXITEMS %s: EE_HIT 0x%08x, EE_GUARD 0x%08x (behind TRI), EE_B %d words at 0x%08x, state 0x%08x; gains hit %d '
          'cap %d gap %d in-EX %d guard %d HP-reflect %d dup %d' % (
              'ON' if EXITEMS else 'off', EE_HIT_ADDR, EE_GUARD_ADDR, len(EE_B_WORDS), EE_B_LO, EE_STATE, EE_HIT_GAIN,
              EE_COMBO_CAP, EE_COMBO_GAP, EE_COMBO_IN_EX, EE_GUARD_GAIN, EE_HPREF_GAIN, EE_DUP_FRAMES))
    print('TRINITY_CTL %s: TRI %d words at 0x%08x in dead EBOOT code (room %d words), table %d B at 0x%08x' %
          ('ON' if TRINITY_CTL else 'off', len(TRI_WORDS), TRI_EB_BASE, (TRI_EB_TAB - TRI_EB_BASE) // 4,
           len(TRI_TAB_BYTES), TRI_EB_TAB))
    return words, sites


def trinity_regions(ov):
    """Garland's controller-0 variant-1 code + table in the overlay buffer: ALWAYS the original bytes (TRI lived here
    in test257-271 by mistake). Accepts clean or an older TRI; anything else stops before any write."""
    import hashlib
    clean_ov = open(os.path.join(HERE, '../../dumps/extracted/OVL_BATTLE_APP.ELF'), 'rb').read()
    for (lo, hi), sha in (((TRI_BASE, TRI_END), TRI_SHA[0]), ((TRI_TAB, TRI_TAB_END), TRI_SHA[1])):
        o = OVL_DATA + lo - OVL_BASE
        cur, clean = bytes(ov[o:o + hi - lo]), clean_ov[o:o + hi - lo]
        assert hashlib.sha256(clean).hexdigest() == sha, 'dumps/extracted overlay is not the clean one'
        older = cur[:4] == struct.pack('<I', 0x8C880000) and cur[8:12] == bytes(4) if lo == TRI_BASE \
            else cur[0x40:] == clean[0x40:]                   # old TRI began "lw t0,0(a0) / beq / nop"
        assert cur == clean or older, 'region 0x%08x is neither original nor an old TRI: not ours' % lo
        if cur == clean:
            print('Garland region 0x%08x: original' % lo)
        else:
            ov[o:o + hi - lo] = clean
            print('Garland region 0x%08x: old TRI removed, original restored' % lo)


def trinity_eboot(f, write):
    """TRI in the dead EBOOT function 0x089c1c8c (sha256-checked original; accepts original or ours)"""
    import hashlib
    clean_eb = open(os.path.join(HERE, '../../dumps/extracted/EBOOT.elf'), 'rb').read()
    lo, hi = TRI_EB_LO, TRI_EB_HI
    clean = clean_eb[elf_off(lo):elf_off(hi)]
    assert hashlib.sha256(clean).hexdigest() == TRI_EB_SHA, 'dumps/extracted EBOOT is not the clean one'
    code = b''.join(struct.pack('<I', w) for w in TRI_WORDS)
    mine = bytearray(clean)
    mine[TRI_EB_BASE - lo:TRI_EB_BASE - lo + len(code)] = code
    mine[TRI_EB_TAB - lo:TRI_EB_TAB - lo + len(TRI_TAB_BYTES)] = TRI_TAB_BYTES
    mine = bytes(mine)
    f.seek(EBOOT_ISO + elf_off(lo))
    cur = f.read(hi - lo)
    older = cur[:0x10] == clean[:0x10] and cur[0x10:0x18] == mine[0x10:0x18]     # same dispatcher head
    probe = cur[0x10:] == mine[0x10:]                                              # test272p entry marker
    assert cur in (clean, mine) or older or probe, 'EBOOT 0x%08x-0x%08x is neither original nor TRI: not ours' % (lo, hi)
    want = mine if TRINITY_CTL else clean
    if probe and TRINITY_CTL and cur != mine:
        want = cur[:0x10] + mine[0x10:]                                            # keep a probe marker
    if cur == want:
        print('TRI EBOOT range 0x%08x: already %s' % (lo, 'TRI' if TRINITY_CTL else 'original'))
    elif write:
        f.seek(EBOOT_ISO + elf_off(lo))
        f.write(want)
        print('TRI EBOOT range 0x%08x: %s' % (lo, 'TRI written' if TRINITY_CTL else 'restored to original'))


def trinity_chrp(f, dry=False):
    """system.bin chrp row of owner 33, byte +7 (burst variant): 1 with TRINITY_CTL, else 0 (in place, like
    spot33_soundids.py's chrp edits)"""
    from ablt_patch import arc_chunk, mpk_member
    mst, _ = pkg_offset('general_archive/main/main.bin')
    sysbin, _ = mpk_member(f, mst, 'system.bin')
    chrp, _ = arc_chunk(f, sysbin, 'chrp')
    _, rows = struct.unpack('<II', read_at(f, chrp, 8))
    for r in range(rows):
        at = chrp + 8 + r * 144
        row = read_at(f, at, 8)
        if row[0] != CHRP_ROW_OWNER:
            continue
        assert row[6] == 0 and row[CHRP_VARIANT] in (0, 1), 'chrp row 33 burst bytes %s: unexpected' % row[6:8].hex()
        want = 1 if TRINITY_CTL else 0
        if row[CHRP_VARIANT] == want:
            print('chrp row 33 +7 (burst variant): already %d' % want)
        elif not dry:
            f.seek(at + CHRP_VARIANT)
            f.write(bytes([want]))
            print('chrp row 33 +7 (burst variant): %d -> %d' % (row[CHRP_VARIANT], want))
        return
    if TRINITY_CTL:
        sys.exit('chrp row for owner 33 not found')
    print('chrp row 33 not found: nothing to restore (TRINITY_CTL off)')


def dir_record(f):
    """(offset in the ISO, record bytes) of OVL_BATTLE_APP.ELF in /PSP_GAME/USRDIR/DATA"""
    f.seek(DATA_DIR_SECTOR * SECTOR)
    d = f.read(SECTOR)
    k = 0
    while k < len(d) and d[k]:
        n = d[k + 32]
        if d[k + 33:k + 33 + n].split(b';')[0] == b'OVL_BATTLE_APP.ELF':
            return DATA_DIR_SECTOR * SECTOR + k, d[k:k + d[k]]
        k += d[k]
    sys.exit('OVL_BATTLE_APP.ELF not found in the DATA directory')


def apply_code(iso):
    use_iso(iso)
    words, sites = code_plan()
    cave = b''.join(struct.pack('<I', w) for w in words)
    cave += b'\0' * ((-len(cave)) % 16)
    with open(iso, 'r+b') as f:
        roff, rec = dir_record(f)
        ext, size = struct.unpack_from('<I', rec, 2)[0], struct.unpack_from('<I', rec, 10)[0]
        assert ext == OVL_SECTOR, 'overlay moved? sector %d' % ext
        f.seek(OVL_SECTOR * SECTOR)
        ov = bytearray(f.read(size))
        filesz = struct.unpack_from('<I', ov, 0x34 + 16)[0]
        if filesz == OVL_FILESZ:                                  # not patched yet: append the cave
            assert size == OVL_SIZE and struct.unpack_from('<I', ov, 0x20)[0] == 0x185B20, 'unexpected overlay layout'
            data_end = OVL_DATA + OVL_FILESZ                      # 0x185B04: shstrtab follows
            shoff = struct.unpack_from('<I', ov, 0x20)[0]
            shstr_off, shstr_sz = struct.unpack_from('<II', ov, shoff + 2 * 40 + 16)
            assert shstr_off == data_end, hex(shstr_off)
            shstr = bytes(ov[shstr_off:shstr_off + shstr_sz])
            shdrs = bytearray(ov[shoff:shoff + 3 * 40])
            new = bytearray(ov[:data_end]) + cave
            new_shstr = len(new)
            new += shstr
            new += b'\0' * ((-len(new)) % 4)
            new_shoff = len(new)
            struct.pack_into('<I', shdrs, 40 + 20, OVL_FILESZ + len(cave))       # section 1 size
            struct.pack_into('<I', shdrs, 2 * 40 + 16, new_shstr)               # section 2 (shstrtab) offset
            new += shdrs
            struct.pack_into('<I', new, 0x20, new_shoff)                         # e_shoff
            struct.pack_into('<II', new, 0x34 + 16, OVL_FILESZ + len(cave), OVL_FILESZ + len(cave))   # p_filesz/memsz
            assert len(new) <= OVL_SECTORS * SECTOR
            ov = new
            print('overlay: cave %d B appended at 0x%08x, file %d -> %d B' % (len(cave), CAVE, size, len(ov)))
        else:                                                    # already patched: the cave must be ours
            assert OVL_FILESZ < filesz <= OVL_FILESZ + (CAVE_END - CAVE), 'overlay has another size (0x%x): not ours' % filesz
            old = bytes(ov[OVL_DATA + OVL_FILESZ:OVL_DATA + filesz])
            if old == cave:
                print('overlay: cave already there')
            else:                                                # an older version of this cave: replace it
                assert old[:12] == cave[:12], 'cave at 0x%08x does not start with IS_SORA_EX: not ours' % CAVE
                shoff = struct.unpack_from('<I', ov, 0x20)[0]
                shdrs = bytearray(ov[shoff:shoff + 3 * 40])
                shstr_off, shstr_sz = struct.unpack_from('<II', shdrs, 2 * 40 + 16)
                shstr = bytes(ov[shstr_off:shstr_off + shstr_sz])
                new = bytearray(ov[:OVL_DATA + OVL_FILESZ]) + cave
                new_shstr = len(new)
                new += shstr
                new += b'\0' * ((-len(new)) % 4)
                new_shoff = len(new)
                struct.pack_into('<I', shdrs, 40 + 20, OVL_FILESZ + len(cave))
                struct.pack_into('<I', shdrs, 2 * 40 + 16, new_shstr)
                new += shdrs
                struct.pack_into('<I', new, 0x20, new_shoff)
                struct.pack_into('<II', new, 0x34 + 16, OVL_FILESZ + len(cave), OVL_FILESZ + len(cave))
                ov = new
                print('overlay: older Reflect cave replaced (%d -> %d B)' % (len(old), len(cave)))
        trinity_regions(ov)                                      # overlay buffer only (written below)
        trinity_eboot(f, write=False)                            # check the EBOOT range before any write
        ee_b_eboot(f, write=False)                               # EXITEMS helper range too
        trinity_chrp(f, dry=True)                                # check the chrp byte before any write
        todo = []                                                # check EVERY site before writing any
        for va, orig, new_words in sites:                        # hook sites: EBOOT and battle overlay
            if va >= OVL_BASE:
                o = OVL_DATA + va - OVL_BASE
                cur = struct.unpack_from('<2I', ov, o)
            else:
                o = EBOOT_ISO + elf_off(va)
                f.seek(o)
                cur = struct.unpack('<2I', f.read(8))
            if list(cur) == new_words:
                print('site 0x%08x: already %s' % (va, 'original' if tuple(new_words) == orig else 'patched'))
                continue
            if any(c != w and (ours(c, va + 4 * i) or c in KNOWN_PATCHED.get(va, ())) for i, (c, w) in enumerate(zip(cur, orig))) and \
                    all(c == w or ours(c, va + 4 * i) or c in KNOWN_PATCHED.get(va, ()) for i, (c, w) in enumerate(zip(cur, orig))):
                print('site 0x%08x: older hook of ours replaced' % va)     # older version of our own hook
                cur = orig
            assert tuple(cur) == orig, 'site 0x%08x: unexpected %08x %08x' % (va, cur[0], cur[1])
            todo.append((va, o, orig, new_words))
        for va, o, orig, new_words in todo:
            if va >= OVL_BASE:
                struct.pack_into('<2I', ov, o, *new_words)
            else:
                f.seek(o)
                f.write(struct.pack('<2I', *new_words))
            print('site 0x%08x: %s' % (va, 'restored to original' if tuple(new_words) == orig else 'hooked'))
        f.seek(OVL_SECTOR * SECTOR)
        f.write(bytes(ov) + b'\0' * ((-len(ov)) % SECTOR))
        rec = bytearray(rec)
        struct.pack_into('<I', rec, 10, len(ov))
        struct.pack_into('>I', rec, 14, len(ov))
        f.seek(roff)
        f.write(rec)
        trinity_eboot(f, write=True)
        ee_b_eboot(f, write=True)
        trinity_chrp(f)


# ---------------------------------------------------------------------------------------------- data part
def data_part(iso, dry):
    use_iso(iso)
    st, sz = pkg_offset(FILE)
    with open(iso, 'rb') as f:
        d = read_at(f, st, sz)
    n, = struct.unpack_from('<I', d, 4)
    ch = [struct.unpack_from('<I4sII', d, 16 + k * 16) for k in range(n)]
    i7 = next(k for k, c in enumerate(ch) if c[0] == 7)
    i8 = next(k for k, c in enumerate(ch) if c[0] == 8)
    t7 = d[ch[i7][2]:ch[i7][2] + ch[i7][3]]
    m7, = struct.unpack_from('<I', t7, 4)
    rows = {struct.unpack_from('<H', t7, 8 + k * 8)[0]: struct.unpack_from('<H', t7, 10 + k * 8)[0] for k in range(m7)}
    c = bytearray(d[ch[i8][2]:ch[i8][2] + ch[i8][3]])
    changed = False
    for mot in GUARD_MOTIONS:
        blk = rows[mot]
        m, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % m, c, 8))
        o = offs[blk]
        k = o + 8
        have = False
        for _ in range(c[o + 2]):
            if c[k + 4] == 0x46 and c[k + 7] == 2:
                have = True
            k += 12 + 4 * c[k + 5]
        if have:
            print('motion %d (block %d): EX-only reflect event already there' % (mot, blk))
            continue
        c[k:k] = EVENT
        c[o + 2] += 1
        s1, s2 = struct.unpack_from('<HH', c, o + 4)
        struct.pack_into('<HH', c, o + 4, s1 + len(EVENT), s2 + len(EVENT))
        offs = [x + len(EVENT) if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        print('motion %d (block %d): + op 0x46 frames 0-36, EX Mode only (projectile reflect)' % (mot, blk))
        changed = True
    # KH2 Reflect sound (2026-10-16): EX-only one-shot op 0x03 [snd 81 = KH2 se 177 barrier up] at frame 0 of both guard
    # blocks (one-shot cond byte +5 = 2 = EX Mode, same matcher as EVENT); slot 81 from spot33_sfx.py.
    from spot33_soundids import bank_base
    isnd = next(k for k, cc in enumerate(ch) if cc[1] == b'snd_')
    base = bank_base(d[ch[isnd][2]:ch[isnd][2] + ch[isnd][3]])
    for mot in GUARD_MOTIONS:
        blk = rows[mot]
        m, = struct.unpack_from('<I', c, 4)
        offs = list(struct.unpack_from('<%dI' % m, c, 8))
        o = offs[blk]
        mains_end, size = struct.unpack_from('<HH', c, o + 4)
        k, have = o + mains_end, False
        for _ in range(c[o + 3]):
            if c[k + 2] == 0x03 and c[k + 5] == 2 and struct.unpack_from('<I', c, k + 8)[0] in (2200081, 21900081):
                have = True
            k += 8 + 4 * c[k + 3]
        if have:
            print('motion %d (block %d): EX-only Reflect sound already there' % (mot, blk))
            continue
        ev = struct.pack('<HBB4B3I', 0, 0x03, 3, 0, 2, 0, 0, base + 81, 0, 0)
        c[o + size:o + size] = ev
        c[o + 3] += 1
        struct.pack_into('<H', c, o + 6, size + len(ev))
        offs = [x + len(ev) if x > o else x for x in offs]
        struct.pack_into('<%dI' % m, c, 8, *offs)
        print('motion %d (block %d): + EX-only sound %d (KH2 Reflect barrier up) at frame 0' % (mot, blk, base + 81))
        changed = True
    if not changed or dry:
        return
    out = rebuild_arc(d, {i8: bytes(c)})
    with tempfile.TemporaryDirectory() as t:
        p = os.path.join(t, 'f.objx')
        open(p, 'wb').write(out)
        r = subprocess.run([sys.executable, '-I', os.path.join(HERE, 'pkg_put.py'), iso, FILE, p],
                           check=True, capture_output=True, text=True)
        print(r.stdout.strip())


def main():
    iso = sys.argv[1]
    if '--code-plan' in sys.argv or '--apply-code' in sys.argv:
        if '--apply-code' in sys.argv:
            apply_code(iso)
        else:
            code_plan()
            return
    data_part(iso, '--dry' in sys.argv)


if __name__ == '__main__':
    main()
