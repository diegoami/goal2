"""Player roles as the original's one-letter codes. [designed: owner, 2026-10-21; #283, #286]

[confirmed: goal2-archaeology F002 R011 and F024 at a737716a] A player's field +6 holds the
position he is placed in, +7 his club position, both 0..13. The original prints a position
through the 14-byte table at DS:69A8, `G S C B B D 80 M M F W W 9B 24`, code page 437
(80 = Ç, 9B = ¢, 24 = $). [confirmed: F028; screenshots m244-squad] DS:0D5C gives each value's
line, 0 goalkeeper, 1 defence (1..4), 2 midfield (5..11, wingers included), 3 attack (12, 13),
and the squad strip colours the code by that line.
[designed: owner, 2026-10-21] Lower case marks the left back, left midfielder and left winger
(values 3, 7, 10); the original prints them as their right-hand letter.
No overall ability is ever shown (#286).
"""
from goal2.game.state import _wrap_raw

CODE_TABLE = 0x69A8
NAME_TABLE = 0x69B6  # [confirmed: F002] fourteen Pascal names, 19 bytes apart
LINE_TABLE = 0x0D5C
LEFT = (3, 7, 10)
LINES = ('goalkeeper', 'defence', 'midfield', 'attack')


def tables(state):
    """The original's code and line tables, read from the game's own memory."""
    raw = _wrap_raw(state.vga, state.mem)
    codes = raw.ds_bytes(CODE_TABLE, 14).decode('cp437')
    lines = tuple(raw.ds_bytes(LINE_TABLE, 14))
    if len(codes) != 14 or any(line > 3 for line in lines):
        raise ValueError('original role tables are not loaded')
    return tuple(c.lower() if value in LEFT else c for value, c in enumerate(codes)), lines


def names(state):
    """The original's fourteen position names (goalkeeper … striker)."""
    raw = _wrap_raw(state.vga, state.mem);out = []
    for value in range(14):
        record = raw.ds_bytes(NAME_TABLE + 19 * value, 19)
        if not 0 < record[0] <= 18:raise ValueError('original position names are not loaded')
        out.append(record[1:1 + record[0]].decode('cp437'))
    return tuple(out)


def role(state, value, *, cache=None):
    """(code, line name) of position value 0..13; ('?', 'unknown') outside that domain."""
    codes, lines = cache or tables(state)
    if type(value) is not int or not 0 <= value <= 13:
        return '?', 'unknown'
    return codes[value], LINES[lines[value]]
