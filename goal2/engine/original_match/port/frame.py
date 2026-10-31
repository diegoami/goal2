"""The commentary and the match frame (T69, P5b): the commentary ring and ratings 0791:1C78, 1D4A, 1E53, 1EB5, the
squad re-sort 230C, and the frame from the sweep of the 22 players to play_match: 9564 (watched_match_engine, one sweep
over the slots), 970C (the clock), 97D0 (the tick loop), 983F (one half), 98C4 (the kick-off sweeps), 9955 (the
full-time sweeps), 998C (the half's set-up), 9A32 (the half-time sequence) and F098 (play_match).

Written from the listing (static/goal-exe/code/seg_0791_03.asm for 1C78-1EB5, seg_0791_04.asm for 230C,
seg_0791_15.asm for 9564, seg_0791_16.asm for 970C-9A32 and seg_0791_23.asm for F098; the named view
static/goal-exe/named/seg_0791_02.c, _08.c and _12.c); the line comments are the listing's offsets. Every routine
keeps the frame the original builds (`mem.enter`: the locals its callees read, the nested procedures' parent BP) and
pushes what the listing pushes, so the stack of every guest call is the original's, and the kit's hooks at 970C (the
tick) and F098 (play_match) fire at the routines' entry, before the port. A routine that is still the original's (the
display, the menus and the quick result of T73-T77, the movement of T62, the helpers of T60-T68) is called as the
listing calls it (`go`), with the arguments and the return address of its SITES row; tests/test_port_frame.py checks
every row against the listing (the call instruction, its return address, the callee's `ret n`).

The registers the listing leaves are set where a callee or the proof could read them (AX before a call, the results
AX/DX of the small functions); the scratch registers (BX, CX, SI, DI, ES, the flags) are not."""
from .guest import call
from .mem import PortError, s8, s16
from . import Registry

PORTS = Registry("frame", "the commentary and ratings (1C78, 1D4A, 1E53, 1EB5), 230C and the match frame "
                          "(9564, 970C, 97D0, 983F, 98C4, 9955, 998C, 9A32, F098)")
PORTS.variant("clock-reload", "970C's sub-tick reload 0x24 (9771) read as 0x23")
PORTS.variant("rating-sign", "1E53's rating delta (1EA3-1EAB) added with the opposite sign")
PORTS.variant("possession-swapped", "9564's possession test (95DB-95E9) inverted: the other side's counter DS:80F6 + 2k")
PORTS.variant("sort-ties", "230C's swap test (23BB-23BE) `jb` read as `jbe`: equal positions swapped too")
PORTS.variant("ring-players-swapped", "1D4A's two player words (1DC4-1E0C) written to each other's slot of the ring")

# A call of the listing: the call instruction's offset (segment 0791) -> (the callee 'SSSS:OOOO', whether it is a far
# call or `push cs; call near` (the return segment is pushed), the return address, the argument words the callee pops).
SITES = {
    0x1D5C: ("0791:1C78", False, "0791:1D5F", 1),
    0x1D83: ("214B:1C86", True, "0791:1D88", 5),
    0x1E31: ("214B:1C86", True, "0791:1E36", 5),
    0x1EBC: ("0791:1E53", False, "0791:1EBF", 1),
    0x1ECD: ("0791:1D4A", False, "0791:1ED0", 4),
    0x1F1E: ("0791:1829", False, "0791:1F21", 3),
    0x236F: ("1771:3216", True, "0791:2374", 1),
    0x23C4: ("0791:2218", False, "0791:23C7", 1),
    0x23DB: ("214B:007B", True, "0791:23E0", 5),
    0x241C: ("214B:007B", True, "0791:2421", 5),
    0x2581: ("0791:A260", True, "0791:2584", 3),
    0x25E6: ("0791:2218", False, "0791:25E9", 1),
    0x25FE: ("1771:3EF8", True, "0791:2603", 0),
    0x2603: ("0791:0691", False, "0791:2606", 0),
    0x2606: ("0791:20E3", False, "0791:2609", 0),
    0x2609: ("0791:419C", False, "0791:260C", 0),
    0x9592: ("23E4:08DF", True, "0791:9597", 3),
    0x95C6: ("0791:2BE5", True, "0791:95C9", 2),
    0x95F8: ("0791:83A2", True, "0791:95FB", 2),
    0x95FB: ("0791:2FB1", False, "0791:95FE", 0),
    0x95FE: ("0791:2996", False, "0791:9601", 0),
    0x962F: ("23E4:08DF", True, "0791:9634", 3),
    0x963C: ("0791:2CEC", True, "0791:963F", 2),
    0x9659: ("0791:2E36", True, "0791:965C", 3),
    0x9666: ("0791:8AE9", True, "0791:9669", 2),
    0x9669: ("0791:59B3", False, "0791:966C", 0),
    0x9692: ("0791:6188", True, "0791:9695", 2),
    0x96BB: ("0791:2956", True, "0791:96BE", 2),
    0x96C8: ("0791:8AE9", True, "0791:96CB", 2),
    0x96D8: ("0791:2FB1", False, "0791:96DB", 0),
    0x96DB: ("0791:94E8", False, "0791:96DE", 0),
    0x96E4: ("0791:8F10", True, "0791:96E7", 2),
    0x96E7: ("0791:9372", False, "0791:96EA", 0),
    0x976E: ("0791:054C", False, "0791:9771", 2),
    0x979E: ("0791:2B0F", False, "0791:97A1", 1),
    0x97A6: ("0791:2B0F", False, "0791:97A9", 1),
    0x97B6: ("0791:0441", False, "0791:97B9", 1),
    0x97BD: ("0791:0425", False, "0791:97C0", 1),
    0x97C4: ("0791:0441", False, "0791:97C7", 1),
    0x97DA: ("0791:D733", False, "0791:97DD", 0),
    0x97E6: ("0791:0C65", False, "0791:97E9", 0),
    0x97F2: ("0791:15B9", False, "0791:97F5", 0),
    0x980B: ("0791:9564", False, "0791:980E", 0),
    0x9815: ("0791:8CF5", False, "0791:9818", 0),
    0x9821: ("0791:9119", True, "0791:9824", 3),
    0x9825: ("0791:970C", False, "0791:9828", 1),
    0x984F: ("0791:8062", False, "0791:9852", 0),
    0x9852: ("0791:2A15", False, "0791:9855", 0),
    0x985F: ("0791:2929", False, "0791:9862", 1),
    0x9862: ("0791:8CCA", False, "0791:9865", 0),
    0x987C: ("0791:97D0", False, "0791:987F", 1),
    0x98A4: ("0791:9079", True, "0791:98A7", 2),
    0x98B3: ("0791:9079", True, "0791:98B6", 2),
    0x98BB: ("214B:1E8D", True, "0791:98C0", 0),
    0x98CE: ("214B:06B1", True, "0791:98D3", 1),
    0x98F4: ("0791:6BF1", False, "0791:98F7", 2),
    0x9920: ("0791:2B51", True, "0791:9923", 2),
    0x9935: ("0791:6337", False, "0791:9938", 0),
    0x993F: ("0791:9564", False, "0791:9942", 0),
    0x9945: ("0791:28B2", False, "0791:9948", 1),
    0x994C: ("214B:1E8D", True, "0791:9951", 0),
    0x9967: ("0791:2929", False, "0791:996A", 1),
    0x9976: ("0791:9564", False, "0791:9979", 0),
    0x997C: ("0791:28B2", False, "0791:997F", 1),
    0x9983: ("214B:1E8D", True, "0791:9988", 0),
    0x99AF: ("0791:2996", False, "0791:99B2", 0),
    0x99CC: ("0791:2996", False, "0791:99CF", 0),
    0x99D0: ("0791:2996", False, "0791:99D3", 0),
    0x99D8: ("0791:6B65", False, "0791:99DB", 2),
    0x99E2: ("0791:1EB5", False, "0791:99E5", 4),
    0x99E5: ("0791:983F", False, "0791:99E8", 0),
    0x9A7B: ("23E4:08DF", True, "0791:9A80", 3),
    0x9AA5: ("23E4:025D", True, "0791:9AAA", 5),
    0x9AAE: ("0791:0106", True, "0791:9AB1", 1),
    0x9AC1: ("23E4:025D", True, "0791:9AC6", 5),
    0x9AD6: ("23E4:08DF", True, "0791:9ADB", 3),
    0x9AE0: ("0791:ED8A", False, "0791:9AE3", 1),
    0x9B05: ("0791:983F", False, "0791:9B08", 0),
    0xF09E: ("0791:998C", False, "0791:F0A1", 0),
    0xF0A1: ("0791:9955", False, "0791:F0A4", 0),
    0xF0A4: ("0791:9A32", False, "0791:F0A7", 0),
    0xF111: ("0791:9B0C", False, "0791:F114", 0),
    0xF114: ("0791:9B5B", False, "0791:F117", 0),
    0xF179: ("0791:A10A", False, "0791:F17C", 0),
    0xF1A8: ("0791:98C4", False, "0791:F1AB", 0),
    0xF1AB: ("0791:9955", False, "0791:F1AE", 0),
}

CODE_SEGMENT = 0x0791          # the paragraph of the code segment the routines are in (push cs)
ZF = 0x40                      # EFLAGS' zero flag: the set test 23E4:08DF (`test byte ptr es:[bx + di], al`) ends with it


def go(site, *args):
    """The call of the listing at offset `site`, with the argument words pushed in order (the callee pops them)."""
    target, far, ret_to, nargs = SITES[site]
    if len(args) != nargs:
        raise PortError(f"call at 0791:{site:04X}: {len(args)} words, the callee pops {nargs}")
    return call(target, *args, ret_to=ret_to, far=far)


def push(mem, value, at):
    """`push ax`: one word below SP (the frame's dead area, where a callee's own frame goes)."""
    sp = (mem.reg("sp") - 2) & 0xFFFF
    mem.set_reg("sp", sp)
    mem.w16(mem.ss_lin(sp), value, at)


def zero_flag(mem):
    return bool(mem.reg("eflags") & ZF)


def set_ax(mem, value):
    mem.set_reg("ax", value & 0xFFFF)
    return value & 0xFFFF


def set_al(mem, value):
    """`mov al, value`: AH stays what the instructions before left."""
    return set_ax(mem, (mem.reg("ax") & 0xFF00) | (value & 0xFF))


def set_product(mem, a, b):
    """`mul`: DX:AX := a * b (the 16-bit forms the listing uses); returns the product."""
    p = a * b
    mem.set_reg("ax", p & 0xFFFF)
    mem.set_reg("dx", (p >> 16) & 0xFFFF)
    return p


def far_record(mem, pointer, index, size):
    """`les di, [pointer]; add di, index * size` (only the product's low word is added, as `mul` leaves AX): the
    segment and the offset of record `index` of the array the far pointer DS:`pointer` holds."""
    off, seg = mem.farptr(mem.DS * 16 + pointer)
    return seg, (off + ((index * size) & 0xFFFF)) & 0xFFFF


# DS offsets the routines use (each cited where used): the commentary ring DS:7C38 + 6 * DS:80EE (match.py RING), the
# country array DS:A917 (records of 0xBF bytes) and the player array DS:A91B (0x14), the pitch records DS:80E8 + 0x16 s,
# the side's first pitch slot DS:0668 + side (0, 11), the two sides' country words DS:9B34 + 2 side.
RING_COUNT, RING_BASE, COUNTRIES, PLAYERS, PITCH_RECORDS = 0x80EE, 0x7C38, 0xA917, 0xA91B, 0x80E8
FIRST_SLOT, SIDE_COUNTRY, PERF_DELTA, BARS, POSSESSION = 0x0668, 0x9B34, 0x0720, 0x80F2, 0x80F6
QUICK = 0x9A3E                 # the quick-result flag (switch_to_quick_result 92FC sets it)


# -- the commentary ---------------------------------------------------------------------------------------------
@PORTS.port("0791:1C78", ret="ret 2")                      # 1D47 ret 2
def commentary_record_is_new(mem, variant):
    """Whether the proposed line (the parent's arguments: code [bp+4], player words [bp+6], [bp+8], side [bp+0xA])
    differs from the newest record of the ring; stores nothing but its frame."""
    parent = mem.frame(mem.arg(0))                         # 1D4A's BP
    fr = mem.enter(0xE, "0791:1C78")                       # 1C78-1C7B
    ds = mem.DS
    ring = (mem.ds16(RING_COUNT) * 6 + RING_BASE) & 0xFFFF            # 1C7E-1C8A
    fr.w16(-9, ring, "0791:1C8E")
    fr.w16(-7, ds, "0791:1C91")
    side = s8(parent.u8(0xA))                              # 1C97-1C9B mov al, ss:[di + 0xa]; cwde
    prod = mem.ds16((2 * side + SIDE_COUNTRY) & 0xFFFF) * 0xBF         # 1CA0-1CA7
    seg, off = far_record(mem, COUNTRIES, mem.ds16((2 * side + SIDE_COUNTRY) & 0xFFFF), 0xBF)
    fr.w16(-0xD, off, "0791:1CAF")
    fr.w16(-0xB, seg, "0791:1CB2")

    def word(index):                                       # 1CC9-1CD8: es:[di + 2 index - 2]
        return mem.u16(seg * 16 + ((off + ((index << 1) & 0xFFFF) - 2) & 0xFFFF))
    ax = 0
    p2 = parent.u16(8)                                     # 1CB5-1CB8 ([bp+8]: the first named player's slot)
    if p2 == 0:
        ax = 0
        fr.w16(-3, 0, "0791:1CC1")
    else:
        ax = word(p2)
        fr.w16(-3, ax, "0791:1CD8")
    v3 = ax
    p1 = parent.u16(6)                                     # 1CDB-1CDE ([bp+6]: the second's)
    if p1 == 0:
        ax = 0
        fr.w16(-5, 0, "0791:1CE7")
    else:
        ax = word(p1)
        fr.w16(-5, ax, "0791:1CFE")
    v5 = ax
    code = parent.u8(4)                                    # 1D01-1D04
    top = ds * 16 + ring
    ax = (ax & 0xFF00) | code
    differ = 1
    if code == mem.u8(top):                                # 1D0B
        ax = v3                                            # 1D10
        if v3 == mem.u16(top + 1):                         # 1D16
            ax = v5                                        # 1D1C
            if v5 == mem.u16(top + 3):                     # 1D22
                ax = (ax & 0xFF00) | mem.u8(top + 5)       # 1D2B
                differ = 0 if (ax & 0xFF) == parent.u8(0xA) else 1       # 1D32
    ax = (ax & 0xFF00) | differ                            # 1D38 / 1D3C
    fr.w8(-1, differ, "0791:1D3E")
    mem.set_reg("dx", (prod >> 16) & 0xFFFF)               # the DX of 1CA7's mul stays
    return ax                                              # 1D41 mov al, [bp - 1]


@PORTS.port("0791:1E53", ret="ret 2")                      # 1EB2 ret 2
def apply_perf_delta(mem, variant):
    """The rating word (player +0x12) of the player on the pitch slot [bp+8] of the side [bp+0xA] gets the table delta
    DS:0720[code [bp+4]] added; the parent is emit_commentary 1EB5."""
    parent = mem.frame(mem.arg(0))
    fr = mem.enter(8, "0791:1E53")
    ds = mem.DS
    side = s8(parent.u8(0xA))                              # 1E5C-1E61
    slot = (mem.ds8((side + FIRST_SLOT) & 0xFFFF) + parent.u16(8)) & 0xFFFF       # 1E63-1E6C
    prod = slot * 0x16                                     # 1E70-1E73
    rec = ((prod & 0xFFFF) + PITCH_RECORDS) & 0xFFFF       # 1E75-1E77
    fr.w16(-4, rec, "0791:1E7B")
    fr.w16(-2, ds, "0791:1E7E")
    prod = mem.u16(ds * 16 + ((rec + 0xD) & 0xFFFF)) * 0x14            # 1E84-1E8B
    seg, off = far_record(mem, PLAYERS, mem.u16(ds * 16 + ((rec + 0xD) & 0xFFFF)), 0x14)
    fr.w16(-8, off, "0791:1E93")
    fr.w16(-6, seg, "0791:1E96")
    delta = s8(mem.ds8((s8(parent.u8(4)) + PERF_DELTA) & 0xFFFF))      # 1E9C-1EA7 mov al, [di + 0x720]; cwde
    if variant == "rating-sign":
        delta = -delta
    target = seg * 16 + ((off + 0x12) & 0xFFFF)
    mem.w16(target, mem.u16(target) + delta, "0791:1EAB")  # add word ptr es:[di + 0x12], ax
    set_ax(mem, delta)
    mem.set_reg("dx", (prod >> 16) & 0xFFFF)
    return None


@PORTS.port("0791:1D4A", ret="ret 8")                      # 1E50 ret 8
def write_commentary_line(mem, variant):
    """Append a line to the ring unless it repeats the newest (1C78): the code byte [bp+4], player words [bp+6] and
    [bp+8] (indexes into the side's country record), the side byte [bp+0xA]; AL says whether it wrote."""
    fr = mem.enter(0xC, "0791:1D4A")
    ds = mem.DS
    fr.w8(-1, 0, "0791:1D50")
    written = False
    proceed = True
    if mem.ds16(RING_COUNT) != 0:                          # 1D54
        yield go(0x1D5C, fr.bp)                            # 1D5B push bp; call 1C78
        if (mem.reg("ax") & 0xFF) == 0:                    # 1D5F or al, al; jne 1D66
            proceed = False                                # jmp 1E4A
    if proceed:
        side = s8(fr.u8(0xA))                              # 1D66-1D6C
        counter = (2 * side + BARS) & 0xFFFF
        mem.wds16(counter, mem.ds16(counter) + 1, "0791:1D6E")           # inc word ptr [di - 0x7f0e]
        set_ax(mem, 1)                                     # 1D77-1D82
        mem.set_reg("di", RING_COUNT)
        yield go(0x1D83, ds, RING_COUNT, 1, 0xC8, 1)       # 214B:1C86 (DS:80EE := wrap(+1, 1..200))
        ring = (mem.ds16(RING_COUNT) * 6 + RING_BASE) & 0xFFFF           # 1D88-1D94
        fr.w16(-7, ring, "0791:1D98")
        fr.w16(-5, ds, "0791:1D9B")
        side = s8(fr.u8(0xA))                              # 1D9E-1DA4
        index = mem.ds16((2 * side + SIDE_COUNTRY) & 0xFFFF)
        seg, off = far_record(mem, COUNTRIES, index, 0xBF)                # 1DA6-1DB3
        set_product(mem, index, 0xBF)
        fr.w16(-0xB, off, "0791:1DB5")
        fr.w16(-9, seg, "0791:1DB8")
        top = ds * 16 + ring

        def word(i):                                       # es:[di + 2 i - 2]
            return mem.u16(seg * 16 + ((off + ((i << 1) & 0xFFFF) - 2) & 0xFFFF))
        mem.w8(top, fr.u8(4), "0791:1DC1")                 # the code
        first, second = fr.u16(8), fr.u16(6)
        slot_first, slot_second = (1, 3) if variant != "ring-players-swapped" else (3, 1)
        if first > 0:                                      # 1DC4-1DDB
            mem.w16(top + slot_first, word(first), "0791:1DDB")
        else:
            mem.w16(top + slot_first, 0, "0791:1DE6")
        if second > 0:                                     # 1DEA-1E01
            mem.w16(top + slot_second, word(second), "0791:1E01")
        else:
            mem.w16(top + slot_second, 0, "0791:1E0C")
        mem.w8(top + 5, fr.u8(0xA), "0791:1E16")           # the side
        fr.w16(-3, mem.ds16(RING_COUNT), "0791:1E1D")      # 1E1A-1E1D
        set_ax(mem, 1)
        mem.set_reg("di", (fr.bp - 3) & 0xFFFF)
        yield go(0x1E31, mem.reg("ss"), (fr.bp - 3) & 0xFFFF, 1, 0xC8, 1)      # the next index, wrapped, in [bp-3]
        mem.w8(ds * 16 + (((fr.u16(-3) * 6) + RING_BASE) & 0xFFFF), 0xFF, "0791:1E41")   # the next record is empty
        fr.w8(-1, 1, "0791:1E46")
        written = True
    return set_al(mem, 1 if written else 0)                # 1E4A mov al, [bp - 1]


@PORTS.port("0791:1EB5", ret="ret 8")                      # 1F39 ret 8
def emit_commentary(mem, variant):
    """Add the line's rating delta (1E53), write the line (1D4A) and, when new, redraw the newest three lines (1829)."""
    fr = mem.enter(4, "0791:1EB5")
    ds = mem.DS
    yield go(0x1EBC, fr.bp)                                # 1EBB push bp; call 1E53
    first = set_al(mem, fr.u8(0xA))                        # 1EBF-1EC2 mov al, [bp + 0xa]; push ax
    last = (first & 0xFF00) | fr.u8(4)                     # 1EC9-1ECC
    mem.set_reg("ax", last)
    yield go(0x1ECD, first, fr.u16(8), fr.u16(6), last)
    if (mem.reg("ax") & 0xFF) != 0:                        # 1ED0 or al, al; je 1F36
        n = mem.ds16(RING_COUNT)                           # 1ED4-1EDF: [bp-4] := n - 2
        low = (n - 2) & 0xFFFF
        fr.w16(-4, low, "0791:1EDF")
        if s16(n) >= s16(low):                             # 1EE5 cmp ax, [bp - 4]; jl 1F29
            i = n
            fr.w16(-2, i, "0791:1EEA")
            while True:
                if s16(i) > 0:                             # 1EF2 cmp word ptr [bp - 2], 0; jle 1F21
                    row = (4 - (n - i)) & 0xFFFF           # 1EFB-1F19
                    set_ax(mem, 0x21)
                    mem.set_reg("dx", 0)
                    yield go(0x1F1E, i, row, 0x21)         # 1829(i, 4 - (n - i), 0x21): the display
                if i == fr.u16(-4):                        # 1F21-1F27
                    break
                i = (i - 1) & 0xFFFF
                fr.w16(-2, i, "0791:1EEF")
        off, seg = mem.farptr(ds * 16 + 0x7C16)            # 1F29 les ax, ptr [0x7c16]
        set_ax(mem, off)
        mem.set_reg("dx", seg)                             # 1F2D mov dx, es
        mem.wds16(0x7C26, off, "0791:1F2F")
        mem.wds16(0x7C28, seg, "0791:1F32")
    return None                                            # 1F39 ret 8


# -- the squad re-sort ------------------------------------------------------------------------------------------
@PORTS.port("0791:230C", ret="ret")                        # 2619 ret
def resort_pitch_and_bench(mem, variant):
    """Both sides' eleven by position code (the unavailable last: 0xE), then the bench (slots 12..20) by position, each
    swap done by 2218 (the squad words), the byte array and the pitch records; then the marking and the posts."""
    fr = mem.enter(0x1A, "0791:230C")
    ds = mem.DS
    ss = mem.reg("ss")
    fr.w8(-1, 0, "0791:2312")
    i = 0
    while True:
        index = mem.ds16((2 * i + SIDE_COUNTRY) & 0xFFFF)                  # 231B-2327: side i's country
        cseg, coff = far_record(mem, COUNTRIES, index, 0xBF)
        fr.w16(-0x16, coff, "0791:2332")
        fr.w16(-0x14, cseg, "0791:2335")

        def pid(k):                                        # es:[di + 2 k - 2] of the country record: a player index
            return mem.u16(cseg * 16 + ((coff + ((k << 1) & 0xFFFF) - 2) & 0xFFFF))

        def player(k):                                     # the player record of pid(k): segment, offset
            return far_record(mem, PLAYERS, pid(k), 0x14)
        fr.w16(-3, 1, "0791:2338")
        j = 1
        while True:                                        # 2342-2392: the position code of each of the eleven
            pseg, poff = player(j)
            fr.w16(-0x1A, poff, "0791:235B")
            fr.w16(-0x18, pseg, "0791:235E")
            set_product(mem, pid(j), 0x14)
            yield go(0x236F, pid(j))                       # 1771:3216 player_unavailable
            if (mem.reg("ax") & 0xFF) != 0:
                fr.w8(j - 0x13, 0xE, "0791:237B")
            else:
                fr.w8(j - 0x13, mem.u8(pseg * 16 + ((poff + 6) & 0xFFFF)), "0791:238B")
            if j == 0xB:                                   # 238E
                break
            j += 1
            fr.w16(-3, j, "0791:233F")
        fr.w16(-5, 1, "0791:2394")
        k = 1
        while True:                                        # 239E-253E: sort the eleven
            if k + 1 > 0xB:
                break
            j = k + 1
            fr.w16(-3, j, "0791:23AA")
            while True:
                if fr.u8(j - 0x13) < fr.u8(k - 0x13) or (variant == "sort-ties" and fr.u8(j - 0x13) == fr.u8(k - 0x13)):
                    yield go(0x23C4, fr.bp)                # 2218
                    yield go(0x23DB, ss, (fr.bp + j - 0x13) & 0xFFFF, ss, (fr.bp + k - 0x13) & 0xFFFF, 1)
                    base = mem.ds8(FIRST_SLOT + i)
                    yield go(0x241C, ds, (PITCH_RECORDS + 0x16 * (base + j)) & 0xFFFF,
                             ds, (PITCH_RECORDS + 0x16 * (base + k)) & 0xFFFF, 0x16)
                    # 2421-252C: the slots named by DS:830B, 830C, 830D follow their player
                    one, other = (base + j) & 0xFFFF, (base + k) & 0xFFFF
                    for off, at_k, at_j in ((0x830B, "0791:244A", "0791:2478"), (0x830C, "0791:24A4", "0791:24D2"),
                                            (0x830D, "0791:24FE", "0791:252C")):
                        here = mem.ds8(off)
                        if here == one:
                            mem.wds8(off, other, at_k)
                        elif here == other:
                            mem.wds8(off, one, at_j)
                if j == 0xB:                               # 252F
                    break
                j += 1
                fr.w16(-3, j, "0791:23AF")
            if k == 0xA:                                   # 2538
                break
            k += 1
            fr.w16(-5, k, "0791:239B")
        base = mem.ds8(FIRST_SLOT + i)                     # 2541-2550: bind the eleven's pitch players
        high = (base + 0xB) & 0xFFFF
        fr.w16(-0x18, high, "0791:2550")
        low = (base + 1) & 0xFFFF
        if low <= high:
            j = low
            fr.w16(-3, j, "0791:2565")
            while True:
                set_product(mem, j, 0x16)
                yield go(0x2581, j, ds, (PITCH_RECORDS + (j * 0x16 & 0xFFFF)) & 0xFFFF)       # A260
                if j == fr.u16(-0x18):                     # 2587
                    break
                j += 1
                fr.w16(-3, j, "0791:256A")
        fr.w16(-5, 0xC, "0791:258C")
        k = 0xC
        while True:                                        # 2596-25EF: the bench by position
            if k + 1 > 0x14:
                break
            j = k + 1
            fr.w16(-3, j, "0791:259F")
            while True:
                held = mem.u8(player(k)[0] * 16 + ((player(k)[1] + 6) & 0xFFFF))
                other = mem.u8(player(j)[0] * 16 + ((player(j)[1] + 6) & 0xFFFF))
                if other < held:                           # 25E1-25E3 jae 25E9
                    yield go(0x25E6, fr.bp)                # 2218
                if j == 0x14:                              # 25E9
                    break
                j += 1
                fr.w16(-3, j, "0791:25A4")
            if k == 0x13:                                  # 25EF
                break
            k += 1
            fr.w16(-5, k, "0791:2593")
        if i == 1:                                         # 25F5
            break
        i += 1
        fr.w8(-1, i, "0791:2318")
    yield go(0x25FE)                                       # 1771:3EF8 set_marking_words
    yield go(0x2603)                                       # 0691
    yield go(0x2606)                                       # 20E3 assign_marking_slots
    yield go(0x2609)                                       # 419C assign_start_posts
    set_ax(mem, 0)                                         # 260C-2613
    mem.wds16(0x8109, 0, "0791:260E")
    mem.wds16(0x81FB, 0, "0791:2613")
    return None


# -- the frame --------------------------------------------------------------------------------------------------
@PORTS.port("0791:9564", ret="ret")                        # 970B ret
def watched_match_engine(mem, variant):
    """One sweep over the 22 slots: the ball and the holder's step (when play is on), then each slot's player (8AE9), the
    speaker, the ball's picture and the key poll; a call is one pass of the game loop's body."""
    fr = mem.enter(8, "0791:9564")
    ds = mem.DS
    cs = mem.seg(CODE_SEGMENT)
    slot = 1
    fr.w16(-2, 1, "0791:956A")
    while True:
        if mem.ds8(0x8302) != 0:                           # 9574
            ax = set_ax(mem, slot)                         # 957E-9581 mov ax, [bp - 2]; push ax
            push(mem, ax, "0791:9581")
            flag = 0
            if mem.ds8(0x8303) != 0:                       # 9582
                ax = set_al(mem, mem.ds8(0x8327))          # 9589-958C
                mem.set_reg("di", 0x9544)
                yield go(0x9592, ax, cs, 0x9544)           # 23E4:08DF: DS:8327 in the set at 0791:9544
                flag = 1 if zero_flag(mem) else 0          # 9597 je 959D
            set_product(mem, flag, 0x16)                   # 959F-95A3
            mem.set_reg("sp", (mem.reg("sp") + 2) & 0xFFFF)                  # 95A7 pop ax
            set_ax(mem, slot)
            gate = mem.ds8((flag * 0x16 + slot + 0x899) & 0xFFFF)            # 95A8-95AA
            set_ax(mem, gate)                              # 95AE xor ah, ah
            if gate <= mem.ds16(0x8300):                   # 95B0-95B4 jbe 95B9
                if mem.ds8(0x82F7) != 0:                   # 95B9
                    mem.set_reg("di", 0x80FE)
                    yield go(0x95C6, ds, 0x80FE)           # 2BE5(the pitch record of slot 1)
                    direction = mem.reg("ax") & 0xFF       # 95C9 mov dl, al
                    mem.set_reg("dx", (mem.reg("dx") & 0xFF00) | direction)
                    ahead = 1 if s8(mem.ds8(0x82F7)) > 0 else 0              # 95CB-95D6 jg
                    same = 1 if mem.ds8(0x7920 + ahead) == direction else 0  # 95DB-95E7
                    if variant == "possession-swapped":
                        same ^= 1
                    counter = (2 * same + POSSESSION) & 0xFFFF
                    mem.wds16(counter, mem.ds16(counter) + 1, "0791:95EE")   # inc word ptr [di - 0x7f0a]
                mem.set_reg("di", 0x82F6)
                yield go(0x95F8, ds, 0x82F6)               # 83A2 move_ball(the ball)
                yield go(0x95FB)                           # 2FB1
                yield go(0x95FE)                           # 2996
                side = 1 if (mem.reg("ax") & 0xFF) == 0 else 0               # 9601-960B
                set_al(mem, side)
                held = (mem.ds8(FIRST_SLOT + side) + 1) & 0xFFFF             # 960C-9614
                product = set_product(mem, held, 0x16)
                rec = ((product & 0xFFFF) + PITCH_RECORDS) & 0xFFFF          # 961A-961C
                fr.w16(-8, rec, "0791:9620")
                fr.w16(-6, ds, "0791:9623")
                ax = set_al(mem, mem.ds8(0x8327))          # 9626-9629
                mem.set_reg("di", 0x9544)
                yield go(0x962F, ax, cs, 0x9544)           # 08DF
                if not zero_flag(mem):                     # 9634 je 9669
                    yield go(0x963C, ds, rec)              # 2CEC player_at_ball(the holder's record)
                    if (mem.reg("ax") & 0xFF) == 0:        # 9641 or al, al; jne 9669
                        call_update = True
                        if mem.u8(ds * 16 + rec) == mem.ds8(0x82F6):         # 9643-9649
                            yield go(0x9659, mem.ds16(0x82F6), ds, rec)      # 2E36
                            call_update = (mem.reg("ax") & 0xFF) != 0        # 965C or al, al; je 9669
                        if call_update:
                            yield go(0x9666, ds, rec)      # 8AE9 update_player
                yield go(0x9669)                           # 59B3
                if (mem.reg("ax") & 0xFF) == 0:            # 966C jne 969B
                    fr.w16(-4, 1, "0791:9670")
                    k = 1
                    while True:
                        if mem.ds8(0x8302) != 0:           # 967A
                            product = set_product(mem, k, 0x16)
                            yield go(0x9692, ds, ((product & 0xFFFF) + PITCH_RECORDS) & 0xFFFF)   # 6188
                        if k == 0x16:                      # 9695
                            break
                        k += 1
                        fr.w16(-4, k, "0791:9677")
        # 969B: this slot's player
        set_ax(mem, mem.ds8(0x883 + slot))                 # 969E-96A2
        product = set_product(mem, mem.ds8(0x883 + slot), 0x16)
        rec = ((product & 0xFFFF) + PITCH_RECORDS) & 0xFFFF
        fr.w16(-8, rec, "0791:96AF")
        fr.w16(-6, ds, "0791:96B2")
        yield go(0x96BB, ds, rec)                          # 2956 player_unavailable_on_pitch
        if (mem.reg("ax") & 0xFF) == 0:                    # 96BE jne 96CB
            yield go(0x96C8, ds, rec)                      # 8AE9
        if mem.ds8(0x883 + slot) == mem.ds8(0x830B):       # 96CB-96D2
            yield go(0x96D8)                               # 2FB1
        yield go(0x96DB)                                   # 94E8 speaker
        mem.set_reg("di", 0x82F6)
        yield go(0x96E4, ds, 0x82F6)                       # 8F10 draw_ball
        yield go(0x96E7)                                   # 9372 match_key_poll
        if mem.ds8(QUICK) != 0:                            # 96EA jne 9708
            return None
        if fr.u16(-2) != 0x16:                             # 96F3
            slot += 1
            fr.w16(-2, slot, "0791:9571")
            continue
        wait = mem.ds16(0x832A)                            # 96FC
        if wait != 0:
            mem.wds16(0x832A, wait - 2, "0791:9703")
        return None


@PORTS.port("0791:970C", ret="ret 2")                      # 97CD ret 2
def match_clock(mem, variant):
    """The clock, called once per pass of the tick loop 97D0: counts the sub-tick down; at 0 spends one of the minute's
    tenths, counts the minute (DS:831F) and says whether the half's time is up (AL)."""
    fr = mem.enter(6, "0791:970C")
    fr.w8(-1, 0, "0791:9712")
    result = 0
    if mem.ds8(0x8325) != 0:                               # 9716
        if mem.ds16(0x831D) != 0:                          # 9720 cmp word ptr [0x831d], 0; jbe 972E
            mem.wds16(0x831D, mem.ds16(0x831D) - 1, "0791:9727")
        else:
            total = (mem.ds16(0x831B) + mem.ds16(0x8321)) & 0xFFFF           # 972E-9735
            set_ax(mem, total)
            flag = 1 if total == 0 else 0                  # 9737-973D
            set_al(mem, flag)
            mem.wds8(0x8326, flag, "0791:973F")
            if mem.ds8(0x8326) == 0:                       # 9742
                if mem.ds16(0x831B) != 0:                  # 9749 jbe 9756
                    mem.wds16(0x831B, mem.ds16(0x831B) - 1, "0791:9750")
                else:
                    mem.wds16(0x8321, mem.ds16(0x8321) - 1, "0791:9756")
                if mem.ds16(0x831F) < 0x80:                # 975A jae 9766
                    mem.wds16(0x831F, mem.ds16(0x831F) + 1, "0791:9762")    # the minute: the kit's WRITERS
            set_ax(mem, 3)                                 # 9766-976D
            yield go(0x976E, mem.ds16(0x831B), 3)          # 054C draw_big_digits
            mem.wds16(0x831D, 0x23 if variant == "clock-reload" else 0x24, "0791:9771")
            wanted = s8(mem.ds8(0x8319))                   # 9777-977E: cwde, cdq
            ax = set_ax(mem, mem.ds16(0x831B))             # 9780-9783
            mem.set_reg("dx", 0)
            reached = wanted >= 0 and ax == wanted         # 9785-978B: the long compare
            if reached or mem.ds8(0x8326) != 0:            # 978D-9792
                if mem.ds8(0x8326) != 0:                   # 9794
                    set_al(mem, 0x3F)
                    yield go(0x979E, 0x3F)                 # 2B0F(0x3F)
                else:
                    set_al(mem, 0x40)
                    yield go(0x97A6, 0x40)                 # 2B0F(0x40)
                set_ax(mem, 0)                             # 97A9-97AB
                mem.wds16(0x8300, 0, "0791:97AB")
                fr.w8(-1, 1, "0791:97AE")
                result = 1
                set_ax(mem, 3)
                yield go(0x97B6, 3)                        # 0441 match_whistle
                set_ax(mem, 4)
                yield go(0x97BD, 4)                        # 0425 match_delay
                set_ax(mem, 6)
                yield go(0x97C4, 6)                        # 0441
    return set_al(mem, result)                             # 97C7 mov al, [bp - 1]


@PORTS.port("0791:97D0", ret="ret 2")                      # 983C ret 2
def match_tick_loop(mem, variant):
    """The tick loop: the quick result, or the replay or snapshot, one sweep (9564), the offside line and the referee,
    then the clock (970C) until it says the half is over (or, with [bp+4] set, until DS:0C20)."""
    fr = mem.enter(0, "0791:97D0")
    ds = mem.DS
    while True:
        if mem.ds8(QUICK) != 0:                            # 97D3
            yield go(0x97DA)                               # D733 quick_match_engine
        else:
            if mem.ds8(0x7C37) != 0:                       # 97DF
                yield go(0x97E6)                           # 0C65 action_replay
            elif mem.ds8(0x9B55) != 0:                     # 97EB
                yield go(0x97F2)                           # 15B9 snapshot_match_state
            if mem.ds8(0x9B55) != 0:                       # 97F5
                mem.wds8(0x0C20, 0, "0791:97FC")
            mem.wds8(0x9B55, 0, "0791:9801")
            mem.wds8(0x7C37, 0, "0791:9806")
            yield go(0x980B)                               # 9564
            if mem.ds8(QUICK) == 0:                        # 980E
                yield go(0x9815)                           # 8CF5 track_offside_line
                ax = set_al(mem, 0)                        # 9818-981A
                mem.set_reg("di", 0x82EE)
                yield go(0x9821, ax, ds, 0x82EE)           # 9119 move_referee
        yield go(0x9825, fr.bp)                            # 9824 push bp; call 970C
        if (mem.reg("ax") & 0xFF) != 0:                    # 9828 or al, al; jne 9839
            return None
        if fr.u8(4) == 0:                                  # 982C
            continue
        if mem.ds8(0x0C20) != 0:                           # 9832
            continue
        return None


@PORTS.port("0791:983F", ret="ret")                        # 98C3 ret
def run_one_half(mem, variant):
    """One half: the substitution check, the sweeps of the half (97D0), the two sides' and the referee's sprites away."""
    fr = mem.enter(2, "0791:983F")
    ds = mem.DS
    mem.wds8(0x9B41, 0, "0791:9845")
    mem.wds8(0x830E, 0, "0791:984A")
    yield go(0x984F)                                       # 8062 check_substitutions
    yield go(0x9852)                                       # 2A15
    if mem.ds8(QUICK) == 0:                                # 9855
        ax = set_al(mem, 1)                                # 985C-985E
        yield go(0x985F, ax)                               # 2929(1)
        yield go(0x9862)                                   # 8CCA
    mem.wds8(0x8302, 0, "0791:9865")
    mem.wds8(0x9B55, 1, "0791:986A")
    mem.wds8(0x0C20, 0, "0791:986F")
    mem.wds8(0x7C37, 0, "0791:9874")
    ax = set_al(mem, 0)                                    # 9879-987B
    yield go(0x987C, ax)                                   # 97D0(0)
    if mem.ds8(QUICK) == 0:                                # 987F
        fr.w8(-1, 0, "0791:9886")
        i = 0
        while True:
            yield go(0x98A4, ds, (6 * i + 0x82E2) & 0xFFFF)      # 9079(a team's sprites)
            if i == 1:                                     # 98A7
                break
            i += 1
            fr.w8(-1, i, "0791:988C")
        mem.set_reg("di", 0x82EE)
        yield go(0x98B3, ds, 0x82EE)                       # 9079(the referee's)
    mem.wds8(0x8325, 0, "0791:98B6")
    yield go(0x98BB)                                       # 214B:1E8D
    return None


@PORTS.port("0791:98C4", ret="ret")                        # 9954 ret
def kickoff_sweeps(mem, variant):
    """The kick-off: the first sweeps of the half until the players are in place (28B2)."""
    fr = mem.enter(6, "0791:98C4")
    ds = mem.DS
    set_ax(mem, 0xA)
    yield go(0x98CE, 0xA)                                  # 214B:06B1 rand(10)
    ax = set_ax(mem, mem.reg("ax") + 1)                    # 98D3 inc ax
    mem.set_reg("dx", ax)                                  # 98D4 mov dx, ax
    behind = 1 if mem.ds8(0x9B3D) > mem.ds8(0x9B3C) else 0           # 98D6-98E3 ja
    ax = set_ax(mem, mem.ds8(FIRST_SLOT + behind) + ax)    # 98E8-98EE
    taken = set_al(mem, 3)                                 # 98F1
    yield go(0x98F4, ax, taken)                            # 6BF1
    mem.wds8(0x8325, 1, "0791:98F7")
    fr.w16(-2, 1, "0791:98FC")
    i = 1
    while True:                                            # 9906-9933
        product = set_product(mem, i, 0x16)
        rec = ((product & 0xFFFF) + PITCH_RECORDS) & 0xFFFF
        fr.w16(-6, rec, "0791:9914")
        fr.w16(-4, ds, "0791:9917")
        yield go(0x9920, ds, rec)                          # 2B51 slot_is_on_ball_side
        if (mem.reg("ax") & 0xFF) != 0:                    # 9923
            mem.w8(ds * 16 + ((rec + 0x12) & 0xFFFF), 6, "0791:992A")
        if i == 0x16:                                      # 992F
            break
        i += 1
        fr.w16(-2, i, "0791:9903")
    yield go(0x9935)                                       # 6337 repick_kickoff_keeper
    if mem.ds8(QUICK) == 0:                                # 9938
        while True:
            yield go(0x993F)                               # 9564
            ax = set_al(mem, 1)                            # 9942-9944
            yield go(0x9945, ax)                           # 28B2(1)
            if (mem.reg("ax") & 0xFF) != 0:                # 9948 or al, al; je 993F
                break
    yield go(0x994C)                                       # 214B:1E8D
    return None


@PORTS.port("0791:9955", ret="ret")                        # 998B ret
def fulltime_sweeps(mem, variant):
    """After the whistle: the sweeps until the players have left (28B2(4))."""
    mem.enter(0, "0791:9955")
    mem.wds8(0x8325, 0, "0791:9958")
    if mem.ds8(QUICK) == 0:                                # 995D
        ax = set_al(mem, 3)                                # 9964-9966
        yield go(0x9967, ax)                               # 2929(3)
    mem.wds8(0x8302, 0, "0791:996A")
    if mem.ds8(QUICK) == 0:                                # 996F
        while True:
            yield go(0x9976)                               # 9564
            ax = set_al(mem, 4)                            # 9979-997B
            yield go(0x997C, ax)                           # 28B2(4)
            if (mem.reg("ax") & 0xFF) != 0:                # 997F
                break
    yield go(0x9983)                                       # 214B:1E8D
    return None


@PORTS.port("0791:998C", ret="ret")                        # 99F1 ret
def start_of_half(mem, variant):
    """The first half's set-up: the clock to 0x5B/0x2D, the kick-off side, the 'kick-off' line (code 0x3B), then the half."""
    fr = mem.enter(4, "0791:998C")
    mem.wds16(0x831B, 0x5B, "0791:9992")
    mem.wds8(0x8319, 0x2D, "0791:9998")
    side = s8(mem.ds8(0x831A))                             # 999D-99A1
    ax = set_ax(mem, mem.ds8((side + FIRST_SLOT) & 0xFFFF) + 0xA)    # 99A3-99A9
    mem.wds8(0x830B, ax & 0xFF, "0791:99AC")
    yield go(0x99AF)                                       # 2996
    holder = s8(mem.reg("ax") & 0xFF)                      # 99B2 cwde
    index = mem.ds16((2 * holder + SIDE_COUNTRY) & 0xFFFF)
    seg, off = far_record(mem, COUNTRIES, index, 0xBF)
    set_product(mem, index, 0xBF)                          # 99B7-99BE
    fr.w16(-4, off, "0791:99C6")
    fr.w16(-2, seg, "0791:99C9")
    yield go(0x99CC)                                       # 2996
    first = mem.reg("ax")
    push(mem, first, "0791:99CF")                          # push ax: left on the stack for 1EB5's `ret 8`
    yield go(0x99D0)                                       # 2996
    second = mem.reg("ax")
    set_ax(mem, 1)                                         # 99D4
    yield go(0x99D8, second, 1)                            # 6B65 (pops the second and the 1)
    third = mem.reg("ax")                                  # 99DB push ax
    set_ax(mem, 0)                                         # 99DC
    set_al(mem, 0x3B)                                      # 99DF
    # 1EB5's `ret 8` pops four words, the first among them: the call pushes it again, at the address it was pushed
    # at (the slot the callee left), so the stack is the original's
    mem.set_reg("sp", (mem.reg("sp") + 2) & 0xFFFF)
    yield go(0x99E2, first, third, 0, 0x3B)               # 1EB5 emit_commentary(0x3B, 0, 6B65's, first)
    yield go(0x99E5)                                       # 983F
    set_ax(mem, mem.ds16(0x9B3C))                          # 99E8
    mem.wds16(0x832C, mem.ds16(0x9B3C), "0791:99EB")
    return None


@PORTS.port("0791:9A32", ret="ret")                        # 9B0B ret
def pre_half_sequence(mem, variant):
    """Half time: recover the tired (energy 1..30 +2), save the screen, the board (0106), restore it, the team menu when
    the manager is there or a key says so, the second half's kick-off side and the half (983F)."""
    fr = mem.enter(0xA, "0791:9A32")
    ds = mem.DS
    cs = mem.seg(CODE_SEGMENT)
    fr.w16(-2, 1, "0791:9A38")
    j = 1
    while True:
        rec = ((j * 0x16 & 0xFFFF) + PITCH_RECORDS) & 0xFFFF
        fr.w16(-6, rec, "0791:9A50")
        fr.w16(-4, ds, "0791:9A53")
        index = mem.u16(ds * 16 + ((rec + 0xD) & 0xFFFF))
        seg, off = far_record(mem, PLAYERS, index, 0x14)
        set_product(mem, index, 0x14)
        fr.w16(-0xA, off, "0791:9A68")
        fr.w16(-8, seg, "0791:9A6B")
        energy = seg * 16 + ((off + 0xE) & 0xFFFF)
        ax = set_al(mem, mem.u8(energy))                   # 9A6E-9A75
        mem.set_reg("di", 0x99F2)
        yield go(0x9A7B, ax, cs, 0x99F2)                   # 08DF: energy in the set at 0791:99F2 ({1..30})
        if not zero_flag(mem):                             # 9A80 je 9A8A
            mem.w8(energy, mem.u8(energy) + 2, "0791:9A85")
        if j == 0x16:                                      # 9A8A
            break
        j += 1
        fr.w16(-2, j, "0791:9A3F")
    mem.wds8(0x9B41, 1, "0791:9A90")
    screen, backup = mem.farptr(ds * 16 + 0xA96A), mem.farptr(ds * 16 + 0xA972)      # (off, seg)
    set_ax(mem, 0xFA0)
    yield go(0x9AA5, screen[1], screen[0], backup[1], backup[0], 0xFA0)    # 23E4:025D: the screen to the backup
    ax = set_al(mem, 1)
    yield go(0x9AAE, ax)                                   # 0106 draw_match_summary
    screen, backup = mem.farptr(ds * 16 + 0xA96A), mem.farptr(ds * 16 + 0xA972)
    set_ax(mem, 0xFA0)
    yield go(0x9AC1, backup[1], backup[0], screen[1], screen[0], 0xFA0)    # and back
    show = True
    if mem.ds8(0x80FD) == 0:                               # 9AC6
        ax = set_al(mem, mem.ds8(0xA977))                  # 9ACD
        mem.set_reg("di", 0x9A12)
        yield go(0x9AD6, ax, cs, 0x9A12)                   # 08DF: DS:A977 in the set at 0791:9A12 ({13, 27})
        show = not zero_flag(mem)                          # 9ADB je 9AE3
    if show:
        ax = set_al(mem, 0)                                # 9ADD
        yield go(0x9AE0, ax)                               # ED8A in_match_menu(0): half_time (kit: MENU_CONTEXT 9AE3)
    other = 1 if mem.ds8(0x831A) == 0 else 0               # 9AE3-9AEE
    ax = set_ax(mem, mem.ds8(FIRST_SLOT + other) + 0xA)    # 9AF3-9AF9
    mem.wds8(0x830B, ax & 0xFF, "0791:9AFC")
    mem.wds16(0x832A, 0x50, "0791:9AFF")
    yield go(0x9B05)                                       # 983F
    return None


@PORTS.port("0791:F098", ret="ret 2")                      # F1B1 ret 2
def play_match(mem, variant):
    """play_match: the first half's set-up, the second sweeps, half time; the score into the fixture's record and the
    winner byte (+3: 2 a draw, 1 the second side, 0 the first); a level decider goes to extra time and the shoot-out;
    then, unless the quick result was taken, the closing sweeps."""
    fr = mem.enter(4, "0791:F098")                         # F098-F09B; [bp+4] is run_match's BP
    parent = mem.frame(fr.u16(4))
    yield go(0xF09E)                                       # 998C
    yield go(0xF0A1)                                       # 9955
    yield go(0xF0A4)                                       # 9A32

    def record():                                          # les di, ss:[di + 6]: the fixture's result record
        off, seg = mem.farptr(parent.lin(6))
        return off, seg, seg * 16 + off

    def settle(at_draw, at_win):
        """F0C1-F0F2: byte +3 of the record := 2 when its two goal bytes are equal, else 1 when the second is more."""
        off, seg, lin = record()
        fr.w16(-4, off, "0791:F0BB")
        fr.w16(-2, seg, "0791:F0BE")
        first, second = mem.u8(lin), mem.u8(lin + 1)
        set_al(mem, first)                                 # F0C4 mov al, es:[di]
        if first == second:                                # F0CA
            mem.w8(lin + 3, 2, at_draw)
        else:
            set_al(mem, second)                            # F0DD
            winner = 1 if second > first else 0            # F0E4-F0ED ja
            set_al(mem, winner)
            mem.w8(lin + 3, winner, at_win)
    score = set_ax(mem, mem.ds16(0x9B3C))                  # F0A7
    mem.w16(record()[2], score, "0791:F0B1")
    settle("0791:F0D3", "0791:F0F2")
    if mem.ds8(0x7C36) != 0 and mem.u8(record()[2] + 3) == 2:         # F0F6-F10C
        yield go(0xF111)                                   # 9B0C extra time, first half
        yield go(0xF114)                                   # 9B5B and second
        score = set_ax(mem, mem.ds16(0x9B3C))              # F117
        mem.w16(record()[2], score, "0791:F121")
        settle("0791:F143", "0791:F162")
        mem.wds8(0x8323, 0, "0791:F166")
        if mem.u8(record()[2] + 3) == 2:                   # F16B-F177
            yield go(0xF179)                               # A10A penalty_shootout
            winner = 1 if mem.ds8(0x9B3D) > mem.ds8(0x9B3C) else 0       # F17C-F189
            set_al(mem, winner)
            mem.w8(record()[2] + 3, winner, "0791:F192")
    if mem.ds8(QUICK) == 0:                                # F196
        if mem.ds8(0x9B3D) != mem.ds8(0x9B3C):             # F19F-F1A6
            yield go(0xF1A8)                               # 98C4
        yield go(0xF1AB)                                   # 9955
    return None
