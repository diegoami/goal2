"""Key input abstraction for the TUI.

[designed] The key set is the minimum needed by the country select screen
(T11), the squad screen (T12) and the tactics screen (T13): arrow keys for
cursor movement, PageUp/PageDown for pagination, Enter to confirm, Esc to
cancel. The actual key sequences (ANSI escape sequences) match a plain
Linux terminal.
"""
from __future__ import annotations

import sys
from enum import Enum
from typing import BinaryIO


class Key(Enum):
    """The keys the screen layer understands.

    [designed] Arrow keys move the cursor; PageUp/PageDown jump by a page;
    Enter confirms; Esc cancels.
    """
    UP = "up"
    DOWN = "down"
    ENTER = "enter"
    ESC = "esc"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"


# ANSI escape sequences for special keys (Linux terminal).
_KEY_SEQUENCES: dict[bytes, Key] = {
    b"\x1b[A": Key.UP,
    b"\x1b[B": Key.DOWN,
    b"\x1b[5~": Key.PAGE_UP,
    b"\x1b[6~": Key.PAGE_DOWN,
}


def read_key(_stdin: BinaryIO | None = None) -> Key:
    """Read one key from stdin and return its Key value.

    Raises EOFError when stdin closes without a full key sequence.
    [designed] Arrow keys arrive as \\x1b[A / \\x1b[B; PageUp/PageDown as
    \\x1b[5~ / \\x1b[6~; Enter as \\n or \\r; Esc as \\x1b.

    R1 fix: read byte-by-byte after \\x1b, not read(5) which would
    consume the next key. Build the sequence until it matches or diverges.
    _stdin is for unit-test injection only (not part of the public API).
    """
    buf = _stdin if _stdin is not None else sys.stdin.buffer
    ch = buf.read(1)
    if not ch:
        raise EOFError("stdin closed")
    if ch == b"\x1b":
        seq = ch
        while True:
            nxt = buf.read(1)
            if not nxt:
                return Key.ESC  # EOF mid-escape — treat as bare Esc
            seq += nxt
            if seq in _KEY_SEQUENCES:
                return _KEY_SEQUENCES[seq]
            # If seq is no longer a prefix of any known sequence, it's a bare
            # Esc followed by something else; treat as Esc.
            if not any(s.startswith(seq) for s in _KEY_SEQUENCES):
                return Key.ESC
    if ch == b"\n" or ch == b"\r":
        return Key.ENTER
    # Unknown byte — treat it as a no-op and read the next key
    return read_key(_stdin)
