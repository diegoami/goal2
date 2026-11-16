"""The original's delay 214B:1E09, served at its entry (T223, #428, #455).

Evidence (goal2-archaeology at 53d7ef5 unless a commit is named):
- [confirmed: static/goal-exe/code/seg_214B_04.asm 1E09-1E57] `214B:1E09(n)` is the game's own calibrated delay, not
  Turbo Pascal's Crt.Delay: `push bp; mov bp, sp; sub sp, 8`; if n is 0 it returns at once (`cmp [bp+6], 0; jbe`);
  else [bp-8] := n and, for [bp-2] from 1 to n, it counts the dword [bp-4]:[bp-6] up from 0 until it equals the
  calibrated count DS:AA01:DS:A9FF (`add/adc`, `les ax, [bp-6]; mov dx, es; cmp dx, [AA01]; cmp ax, [A9FF]`); then
  `mov ax, [bp-2]; cmp ax, [bp-8]`, `mov sp, bp; pop bp; retf 2`. It reads no clock: no BIOS tick (0040:006C), no
  port, no interrupt. Its only effects are the registers, the flags and the four locals and the saved BP it leaves
  below SP. [confirmed: seg_214B_04.asm 1DA7-1E08] DS:A9FF/AA01 is the calibration 214B:1DA7 stores (the passes of
  one BIOS tick / 55); [confirmed: goal2/tests/test_core_exe_boot_t222.py] 4279 (10B7h) in the recording and in
  the GOAL.EXE boot, after which the core's BIOS tick never advances (goal2/core/exeboot.py: the boot alone counts
  ticks). The task's hazard "the tick ends the loop early" therefore has no reader here; Done-when 1's equality run
  checks it.
- [derived: the listing above] The loop leaves AX = n, DX = ES = the count's high word, the flags of the equal
  `cmp` (CF, AF, SF, OF clear; ZF, PF set), SP 6 above the entry's (`retf 2`), BP the caller's, and at SS:SP-2 the
  saved BP, SP-4 [bp-2] = n, SP-6 [bp-4] = the count's high word, SP-8 [bp-6] = its low word, SP-10 [bp-8] = n.
  With n = 0: the flags of `cmp 0, 0` (the same), the saved BP, and nothing else (test_core_delay_t223.Serve visits
  n = 0, 1 and 3, with counts whose high word is 0 and 1).
- [confirmed: #455 comment 2026-10-27T09:15:47Z; seg_214B_04.asm 1EA1-1EB9, 1EF1-1F84, 1F87-1FFD; seg_0791_01.asm
  0441-045A] The callers that make a sound: 214B:1EA1 (a tone, the delay, speaker off: return 214B:1EB2, a beep),
  214B:1EF1 play_note (the note's delay: return 214B:1F81), called by play_jingle 214B:1F87 (returns 214B:1FDE,
  214B:1FEE), which match_whistle 0791:0441 calls (return 0791:0457): the whistle. The core ignores the speaker
  (runner.py NG-10): these delays are silent waits.

[designed: T223] The core serves every delay at its entry: it writes what the loop would leave and returns, and tells
a listener (`Core.on_delay`, if any) the milliseconds asked and the sound. It never waits: a wall-time wait is the
watched window's (goal2/desktop/core_model.py). `Core.delays_served = False` executes the loop instead (the equality
test, goal2/tests/test_core_delay_t223.py).
"""

DELAY = "214B:1E09"
COUNT_LOW, COUNT_HIGH = 0xA9FF, 0xAA01     # 1DFE, 1E01: the calibrated passes of one millisecond
# [confirmed: the listings above] the return address of the delay call -> the sound it times
BEEP_RETURN, NOTE_RETURN = "214B:1EB2", "214B:1F81"
JINGLE_RETURNS = ("214B:1FDE", "214B:1FEE")
WHISTLE_RETURN = "0791:0457"
# the arithmetic flags of x86 (CF PF AF ZF SF OF) and those an equal `cmp` sets (ZF, PF)
ARITH_FLAGS, EQUAL_FLAGS = 0x08D5, 0x0044


def sound(m):
    """The sound the delay times, from the original's own frames at 1E09's entry (its caller's BP is still in BP):
    'whistle' (a note of match_whistle's jingle), 'tune' (another note), 'beep', or None (a plain wait)."""
    caller = m.where(m.stack_word(2), m.stack_word(0))
    if caller == BEEP_RETURN:
        return "beep"
    if caller != NOTE_RETURN:
        return None
    bp = m.reg("bp")                       # play_note's frame
    if _far_caller(m, bp) in JINGLE_RETURNS and _far_caller(m, m.frame_word(bp, 0)) == WHISTLE_RETURN:
        return "whistle"
    return "tune"


def _far_caller(m, bp):
    return m.where(m.frame_word(bp, 4), m.frame_word(bp, 2))


def asked(m):
    """The milliseconds the call at 1E09's entry asks for: its argument, the word above the far return."""
    return m.stack_word(4)


def serve(m):
    """Leave 214B:1E09 as its loop would (the module docstring): registers, flags, the locals below SP, `retf 2`."""
    n = asked(m)
    ss, sp, bp = m.reg("ss"), m.reg("sp"), m.reg("bp")
    high = m.rd(COUNT_HIGH)

    def put(off, value):
        m.write(ss * 16 + ((sp - off) & 0xFFFF), (value & 0xFFFF).to_bytes(2, "little"))
    put(2, bp)                             # push bp
    if n:
        put(4, n)                          # [bp-2]: the last pass
        put(6, high)                       # [bp-4]: the count's high word
        put(8, m.rd(COUNT_LOW))            # [bp-6]: its low word
        put(10, n)                         # [bp-8]: n
        m.set_reg("ax", n)                 # 1E4C mov ax, [bp-2]
        m.set_reg("dx", high)              # 1E3E mov dx, es
        m.set_reg("es", high)              # 1E3B les ax, [bp-6]
    m.set_reg("eflags", (m.reg("eflags") & ~ARITH_FLAGS) | EQUAL_FLAGS)
    m.return_from(True, 2)                 # mov sp, bp; pop bp (BP unchanged); retf 2
    return n


# [confirmed: code/seg_0791_20.asm CC2E-CC70; F030] wait_or_key(n): [bp-4] := n, then for [bp-2] from 1 to n a poll
# (call far 214B:0723 at CC4F, returning to CC54) and, with no key, 214B:1E09(10).
WAIT_OR_KEY_POLL, WAIT_OR_KEY_MS = "0791:CC54", 10


def timed_left_ms(core):
    """At a poll wait of wait_or_key (site 0791:CC54; the CPU at 214B:0723's entry, BP wait_or_key's), the
    milliseconds of delay the prompt still asks for if no key comes: this poll's delay and one per poll left,
    ([bp-4] - [bp-2] + 1) x 10. 0 at any other wait (0B7C's last poll 0BE1 has no delay after it)."""
    wait = core.wait
    if wait is None or not wait.poll or wait.site != WAIT_OR_KEY_POLL:
        return 0
    m = core.m
    bp = m.reg("bp")
    n, i = m.frame_word(bp, -4 & 0xFFFF), m.frame_word(bp, -2 & 0xFFFF)
    return max(0, n - i + 1) * WAIT_OR_KEY_MS
