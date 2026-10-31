"""E032's pilot, moved in (T58): the player's run step `0791:8889` and the move test `0791:86D0` it calls, with the
helpers 2BE5, 2974, 045D, 2CC5, 2DCA, the set test 23E4:08DF and the draws 214B:06B1, 06FA (through 214B:0688).

From experiments/E032-match-engine-inventory/pilot_movement.py, written against the port's memory view; the line
comments are the listing's offsets (static/goal-exe/code/seg_0791_14.asm, seg_0791_05.asm, seg_0791_04.asm,
seg_0791_01.asm, seg_23E4_01.asm, seg_214B_01.asm). 8889 is called only from 8AE9 update_player, with 8AE9's BP (a
nested procedure: its one argument word), and 86D0 only from 8889 (8AC6), so one port covers both. Every write names
the instruction that makes it in the original."""
from .mem import s8
from . import Registry

PORTS = Registry("pilot", "E032's pilot: the player's run step 0791:8889 with 86D0 and their helpers")
PORTS.variant("coin-swapped", "the coin's two axis orders swapped (8A33)")
PORTS.variant("bound-36", "2DCA's row bound 0x25 read as 0x24")
PORTS.variant("no-picture", "86D0 never blocked by the pitch picture (87E8-8855)")

SEED_PTR = 0xA978         # the far pointer to the main seed word (214B:06B7, 0700)
SEED_WRITE = "214B:069F"  # 0688's stosw: the seed := seed * 0x7ABD + 0x1B0F
CS_STATES = 0x8869        # 897B: the set of states {5, 7, 8, 11} in 8889's own code segment


def rand(mem, n):
    """214B:06B1 rand(n) through 0688 (seg_214B_01.asm 0688-06AE): the seed word at [DS:A978] stepped, (new*n>>16)+1."""
    lin = mem.ds_far(SEED_PTR)
    new = (mem.u16(lin) * 0x7ABD + 0x1B0F) & 0xFFFF       # 0694-069A
    mem.w16(lin, new, SEED_WRITE)                         # 069F
    return (((new * n) >> 16) + 1) & 0xFFFF               # 06A0-06A4


def coin(mem):
    """214B:06FA: rand(2) == 1 (0706-0717)."""
    return 1 if rand(mem, 2) == 1 else 0


def in_set(mem, set_lin, element):
    """23E4:08DF: bit e of byte e>>3 (08E5-08FA)."""
    return bool(mem.u8(set_lin + (element >> 3)) & (1 << (element & 7)))


def pitch_slot_side(mem, rec):
    """2974: slot +6 < 0x0C (297D-2988)."""
    return 1 if mem.u8(rec + 6) < 0x0C else 0


def attack_direction(mem, rec):
    """2BE5 (2BEB-2C19)."""
    half = s8(mem.ds8(0x8319))                    # sign-extended to a long
    left = mem.ds16(0x831B)                       # zero-extended to a long
    flag = 1 if (half < 0 or left > half) else 0  # 2BF9-2C07: dx=0 against bx, then unsigned ax > cx
    return s8(mem.ds8(0x7920 + (flag ^ pitch_slot_side(mem, rec))))


def is_keeper_slot(slot):
    """045D: word 1 or 0x0C (0463-0473)."""
    return slot in (1, 0x0C)


def on_target(mem, rec):
    """2CC5: word +0 == word +7 (2CCE-2CDE)."""
    return mem.u16(rec) == mem.u16(rec + 7)


def on_pitch(word, variant):
    """2DCA: |s8 lo| <= 8 and |s8 hi| <= 0x25 (2DD0-2DF2)."""
    bound = 0x24 if variant == "bound-36" else 0x25
    return abs(s8(word & 0xFF)) <= 8 and abs(s8(word >> 8)) <= bound


def can_move(mem, rec, variant):
    """86D0: one step in direction +0xF, and whether the cell is free."""
    mem.w16(rec, mem.u16(rec + 2), "0791:86F0")           # 86E1-86F0: position := the drawn position
    f = mem.u8(rec + 0xF)
    if f == 1:
        mem.w8(rec, mem.u8(rec) - 1, "0791:8711")
    elif f == 2:
        mem.w8(rec, mem.u8(rec) + 1, "0791:8725")
    elif f == 3:
        mem.w8(rec + 1, mem.u8(rec + 1) - 1, "0791:8739")
    elif f == 4:
        mem.w8(rec + 1, mem.u8(rec + 1) + 1, "0791:874E")
    if mem.u8(rec + 0xF) == 5:                            # 875D
        return True
    if not on_pitch(mem.u16(rec), variant):               # 8772-877C
        return False
    if mem.ds8(0x8325) == 0:                              # 877F
        return True
    slot = mem.u8(rec + 6)
    if slot == mem.ds8(0x830C) or slot == mem.ds8(0x830B):   # 8798, 87B0
        return True
    poff, pseg = mem.farptr(mem.DS * 16 + 0xA91B)         # 87C4-87D8: the player's position code +6
    player = mem.u16(rec + 0xD)
    if mem.u8(mem.addr(pseg, poff + ((player * 0x14) & 0xFFFF)) + 6) == 0:
        return True
    if variant == "no-picture":
        return True
    boff, bseg = mem.farptr(mem.DS * 16 + 0x7C16)         # 87E8-8813: the pitch picture's cell
    cell = (boff + ((s8(mem.u8(rec)) * 0xA0) & 0xFFFF) + ((s8(mem.u8(rec + 1)) * 2) & 0xFFFF)) & 0xFFFF
    if mem.u8(mem.addr(bseg, cell + 0x90F)) == 0x0D:
        return True
    ch = mem.u8(mem.addr(bseg, cell + 0x90E))            # 8845-8855: a character of the set DS:0648 blocks
    return not in_set(mem, mem.DS * 16 + 0x648, ch)


@PORTS.port("0791:8889", ret="ret 2")                     # 8AE6 ret 2 (the parent BP)
def player_run_step(mem, variant):
    parent = mem.frame(mem.arg(0))                        # 8AE9's BP
    rec = parent.far(6)                                   # 8899: les di, ss:[di + 6], the pitch record
    skip = False
    if mem.ds8(0x8302) != 0:                              # 888F
        own = s8(mem.u8(rec + 1)) * attack_direction(mem, rec)        # 88A0-88B2
        ball = s8(mem.ds8(0x82F7)) * attack_direction(mem, rec)       # 88BF-88C9
        if ball > own:                                    # 88CC jle 88D3, else 89E5
            skip = True
    if not skip:
        slot = mem.u8(rec + 6)
        if slot == mem.ds8(0x830B) or slot == mem.ds8(0x830C):        # 88DE, 88F2
            skip = True
    if not skip:
        a = attack_direction(mem, rec) > 0                # 8905-8912
        c = s8(mem.u8(rec + 8)) > 0                       # 891B-8928
        if a != c:
            skip = True
    if not skip:
        idx = 1 if pitch_slot_side(mem, rec) == 0 else 0                # 8939-8946
        line = abs(s8(mem.ds8(0x82E3 + 6 * idx)))                        # 8951-895C
        if abs(s8(mem.u8(rec + 8))) < line:               # 8965-8972 jl 89E5
            pass
        elif not in_set(mem, mem.addr(mem.seg(0x791), CS_STATES), mem.u8(rec + 0x12)):   # 897B-898A
            pass
        elif is_keeper_slot(mem.u8(rec + 6)):             # 898C-899F
            pass
        else:
            d = attack_direction(mem, rec)                # 89AB
            idx = 1 if pitch_slot_side(mem, rec) == 0 else 0
            mem.w8(rec + 8, s8(mem.ds8(0x82E3 + 6 * idx)) - d, "0791:89E1")   # 89D2-89E1
    # 89E5: the target test, the coin, the run direction, and the move with its retries
    dx = s8((mem.u8(rec + 7) - mem.u8(rec)) & 0xFF)       # 89EC-89FD
    dy = s8((mem.u8(rec + 8) - mem.u8(rec + 1)) & 0xFF)   # 8A07-8A0B
    if on_target(mem, rec):                               # 8A18-8A26
        mem.w8(rec + 0xF, 5, "0791:8A26")
    else:
        c = coin(mem)                                     # 8A2E
        if variant == "coin-swapped":
            c ^= 1
        if c:                                             # 8A33 je 8A7F
            if abs(dx) > 0:
                mem.w8(rec + 0xF, (1 if dx > 0 else 0) + 1, "0791:8A5B")
            else:
                mem.w8(rec + 0xF, (1 if dy > 0 else 0) + 3, "0791:8A79")
        else:
            if abs(dy) > 0:
                mem.w8(rec + 0xF, (1 if dy > 0 else 0) + 3, "0791:8AA5")
            else:
                mem.w8(rec + 0xF, (1 if dx > 0 else 0) + 1, "0791:8AC1")
    while not can_move(mem, rec, variant):                # 8AC5-8AE1
        mem.w8(rec + 0xF, rand(mem, 5), "0791:8ADD")
