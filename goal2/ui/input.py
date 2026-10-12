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


def read_key() -> Key:
    """Read one key from stdin and return its Key value.

    Raises EOFError when stdin closes without a full key sequence.
    [designed] Arrow keys arrive as \\x1b[A / \\x1b[B; PageUp/PageDown as
    \\x1b[5~ / \\x1b[6~; Enter as \\n or \\r; Esc as \\x1b.
    """
    ch = sys.stdin.buffer.read(1)
    if not ch:
        raise EOFError("stdin closed")
    # Esc is either a bare \x1b or the start of a sequence
    if ch == b"\x1b":
        # Peek: read up to 5 more bytes to form a sequence
        seq = ch + sys.stdin.buffer.read(5)
        for length in range(2, len(seq) + 1):
            prefix = seq[:length]
            if prefix in _KEY_SEQUENCES:
                # Consume only what was read for this key
                _consume(len(prefix) - 1)
                return _KEY_SEQUENCES[prefix]
        # Bare Esc (no sequence)
        return Key.ESC
    if ch == b"\n" or ch == b"\r":
        return Key.ENTER
    # Unknown byte — treat it as a no-op and read the next key
    return read_key()


def _consume(n: int) -> None:
    """Read and discard n bytes from stdin."""
    if n > 0:
        sys.stdin.buffer.read(n)
