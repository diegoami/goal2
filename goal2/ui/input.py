"""Key input abstraction for the TUI.

[designed] The key set is the minimum needed by the country select screen
(T11), the squad screen (T12) and the tactics screen (T13): arrow keys for
cursor movement, PageUp/PageDown for pagination, Enter to confirm, Esc to
cancel. The actual key sequences (ANSI escape sequences) match a plain
Linux terminal.
"""
from __future__ import annotations

import os
import select
import sys
import time
from contextlib import contextmanager
from enum import Enum
from typing import BinaryIO, Iterator

try:  # [designed] Keep imports usable on platforms without POSIX terminal APIs.
    import termios
    import tty
except ImportError:  # pragma: no cover - exercised on non-POSIX platforms.
    termios = None
    tty = None


# [designed: T25] Use 150 ms for the absolute continuation window: the task
# specifies a finite wait but supplies no original timeout measurement.
ESCAPE_TIMEOUT = 0.15


class Key(Enum):
    """The keys the screen layer understands.

    [designed] Arrow keys move the cursor; PageUp/PageDown jump by a page;
    Enter confirms; Esc cancels; Space toggles the current tactic.
    """
    UP = "up"
    DOWN = "down"
    ENTER = "enter"
    ESC = "esc"
    PAGE_UP = "page_up"
    PAGE_DOWN = "page_down"
    SPACE = "space"


# [designed] ANSI escape sequences for the supported special keys.
_KEY_SEQUENCES: dict[bytes, Key] = {
    b"\x1b[A": Key.UP,
    b"\x1b[B": Key.DOWN,
    b"\x1b[5~": Key.PAGE_UP,
    b"\x1b[6~": Key.PAGE_DOWN,
}


@contextmanager
def terminal_input() -> Iterator[None]:
    """[designed] Use cbreak input on a POSIX TTY and restore its exact state."""
    stream = sys.stdin
    if (os.name != "posix" or termios is None or tty is None or stream is None
            or not getattr(stream, "isatty", lambda: False)()):
        yield
        return
    fd = stream.fileno()
    saved = termios.tcgetattr(fd)
    try:
        # [designed: T25] cbreak disables canonical input and echo, preserving ISIG.
        tty.setcbreak(fd, termios.TCSANOW)
        yield
    finally:
        termios.tcsetattr(fd, termios.TCSANOW, saved)


def _windows_ready(fd: int) -> bool:
    """[designed: #278] Whether a Windows descriptor has a byte to read without blocking: a
    pipe through PeekNamedPipe, the console through msvcrt.kbhit."""
    import ctypes
    import msvcrt
    available = ctypes.c_ulong(0)
    handle = msvcrt.get_osfhandle(fd)
    if ctypes.windll.kernel32.PeekNamedPipe(ctypes.c_void_p(handle), None, 0, None, ctypes.byref(available), None):
        return available.value > 0
    return bool(msvcrt.kbhit())


def _read_byte(stream: BinaryIO, fd: int | None, timeout: float | None) -> bytes:
    """[designed: T25] Read descriptors directly to avoid buffered/select races.
    [designed: #278] Windows has no select on pipes or the console, so a timed read polls."""
    if fd is not None and os.name == "nt":
        if timeout is not None:
            deadline = time.monotonic() + timeout
            while not _windows_ready(fd):
                if time.monotonic() >= deadline:
                    return b""
                time.sleep(0.005)
        return os.read(fd, 1)
    if fd is not None:
        readable, _, _ = select.select([fd], [], [], timeout)
        if not readable:
            return b""
        return os.read(fd, 1)
    return stream.read(1)


def read_key(_stdin: BinaryIO | None = None) -> Key:
    """Read one key from stdin; a timed-out Escape continuation returns ``ESC``.

    [designed: T25] Raises EOFError when stdin closes before a key. Arrow sequences
    are ``\x1b[A`` / ``\x1b[B`` and PageUp/PageDown are ``\x1b[5~`` / ``\x1b[6~``.
    Escape continuation bytes share an absolute ``ESCAPE_TIMEOUT`` window.
    [designed: T25] ``_stdin`` supports injected streams; descriptor-backed streams use
    select/os.read (on Windows a polled read), while in-memory streams retain their ordinary
    read path.
    """
    stream = _stdin if _stdin is not None else getattr(sys.stdin, "buffer", sys.stdin)
    try:
        fd = stream.fileno()
    except (AttributeError, OSError, ValueError):
        fd = None

    while True:
        ch = _read_byte(stream, fd, None)
        if not ch:
            raise EOFError("stdin closed")
        if ch == b"\x1b":
            seq = ch
            deadline = time.monotonic() + ESCAPE_TIMEOUT
            while any(candidate.startswith(seq) for candidate in _KEY_SEQUENCES):
                remaining = max(0.0, deadline - time.monotonic())
                nxt = _read_byte(stream, fd, remaining)
                if not nxt:
                    return Key.ESC
                seq += nxt
                if seq in _KEY_SEQUENCES:
                    return _KEY_SEQUENCES[seq]
            return Key.ESC
        if ch in (b"\n", b"\r"):
            return Key.ENTER
        if ch == b" ":
            return Key.SPACE
        # [designed: T25] Ignore unknown bytes without recursing on long streams.
