"""[designed] POSIX terminal input policy and restoration regressions."""
from __future__ import annotations

import io
import os
import select
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

try:
    import pty
    import termios
except ImportError:  # POSIX-only integration cases are skipped below.
    pty = None
    termios = None

from goal2.ui import input as key_input
from goal2.ui.input import Key


_CHILD = r'''
import io, os, sys
from goal2.ui.input import read_key, terminal_input
mode = sys.argv[1]
try:
    with terminal_input():
        print("READY", flush=True)
        if mode == "error":
            raise RuntimeError("expected input test failure")
        if mode == "eof":
            read_key(io.BytesIO())
        if mode == "interrupt":
            os.read(0, 1)
            os.kill(os.getpid(), 2)
        count = int(sys.argv[2])
        for _ in range(count):
            print("KEY " + read_key().name, flush=True)
except KeyboardInterrupt:
    print("INTERRUPTED", flush=True)
'''


@unittest.skipUnless(os.name == "posix" and pty is not None and termios is not None,
                     "real pseudo-terminals require POSIX")
class PtyInput(unittest.TestCase):
    """Exercise real terminal bytes while stdin stays open."""

    def start_child(self, mode="read", count=1):
        master, slave = pty.openpty()
        saved = termios.tcgetattr(slave)
        child = subprocess.Popen(
            [sys.executable, "-c", _CHILD, mode, str(count)],
            stdin=slave, stdout=slave, stderr=slave, close_fds=True,
            cwd=Path(__file__).resolve().parents[2],
        )
        self.addCleanup(self.stop_child, child, master, slave)
        ready = self.read_until(master, b"READY\r\n", 2)
        self.assertIn(b"READY", ready)
        return child, master, slave, saved

    @staticmethod
    def read_until(fd, marker, timeout):
        end = time.monotonic() + timeout
        data = bytearray()
        while marker not in data and time.monotonic() < end:
            remaining = end - time.monotonic()
            ready, _, _ = select.select([fd], [], [], remaining)
            if not ready:
                break
            try:
                data.extend(os.read(fd, 4096))
            except OSError:
                break
        return bytes(data)

    @staticmethod
    def stop_child(child, master, slave):
        if child.poll() is None:
            child.kill()
        try:
            child.wait(timeout=2)
        finally:
            for fd in (master, slave):
                try:
                    os.close(fd)
                except OSError:
                    pass

    def current_attrs(self, slave):
        return termios.tcgetattr(slave)

    def test_arrow_and_space_are_immediate_without_newline(self):
        child, master, slave, saved = self.start_child(count=2)
        active = self.current_attrs(slave)
        self.assertFalse(active[3] & termios.ICANON)
        self.assertFalse(active[3] & termios.ECHO)
        self.assertTrue(active[3] & termios.ISIG)
        os.write(master, b"\x1b[A ")
        output = self.read_until(master, b"KEY SPACE\r\n", 2)
        self.assertIn(b"KEY UP", output)
        self.assertIn(b"KEY SPACE", output)
        self.assertEqual(child.wait(timeout=2), 0)
        self.assertEqual(self.current_attrs(slave), saved)

    def test_bare_escape_is_bounded_while_input_stays_open(self):
        child, master, slave, saved = self.start_child()
        start = time.monotonic()
        os.write(master, b"\x1b")
        output = self.read_until(master, b"KEY ESC\r\n", 2)
        elapsed = time.monotonic() - start
        self.assertIn(b"KEY ESC", output)
        self.assertLess(elapsed, 1.5)
        self.assertEqual(child.wait(timeout=2), 0)
        self.assertEqual(self.current_attrs(slave), saved)

    def test_incomplete_escape_is_bounded_while_input_stays_open(self):
        child, master, slave, saved = self.start_child()
        os.write(master, b"\x1b[")
        output = self.read_until(master, b"KEY ESC\r\n", 2)
        self.assertIn(b"KEY ESC", output)
        self.assertEqual(child.wait(timeout=2), 0)
        self.assertEqual(self.current_attrs(slave), saved)

    def test_complete_sequence_preserves_next_key(self):
        child, master, slave, saved = self.start_child(count=2)
        os.write(master, b"\x1b[5~ ")
        output = self.read_until(master, b"KEY SPACE\r\n", 2)
        self.assertIn(b"KEY PAGE_UP", output)
        self.assertIn(b"KEY SPACE", output)
        self.assertEqual(child.wait(timeout=2), 0)
        self.assertEqual(self.current_attrs(slave), saved)

    def test_restores_attributes_after_exception(self):
        child, master, slave, saved = self.start_child(mode="error")
        child.wait(timeout=2)
        self.assertEqual(self.current_attrs(slave), saved)

    def test_restores_attributes_after_keyboard_interrupt(self):
        child, master, slave, saved = self.start_child(mode="interrupt")
        os.write(master, b"i")
        output = self.read_until(master, b"INTERRUPTED\r\n", 2)
        self.assertIn(b"INTERRUPTED", output)
        self.assertEqual(child.wait(timeout=2), 0)
        self.assertEqual(self.current_attrs(slave), saved)

    def test_restores_attributes_after_eof(self):
        child, master, slave, saved = self.start_child(mode="eof")
        self.assertNotEqual(child.wait(timeout=2), 0)
        self.assertEqual(self.current_attrs(slave), saved)


class InputContext(unittest.TestCase):
    def test_non_posix_keeps_injected_stream_reading(self):
        with patch.object(key_input.os, "name", "nt"):
            with patch.object(key_input.select, "select") as selector:
                self.assertEqual(key_input.read_key(io.BytesIO(b" ")), Key.SPACE)
            selector.assert_not_called()

    def test_missing_stdin_does_not_call_terminal_attributes(self):
        with patch.object(key_input.sys, "stdin", None):
            with patch.object(key_input, "termios", create=True) as terminal:
                with key_input.terminal_input():
                    pass
            terminal.tcgetattr.assert_not_called()
            terminal.tcsetattr.assert_not_called()

    def test_redirected_input_does_not_call_terminal_attributes(self):
        stream = io.BytesIO(b" \n")
        with patch.object(key_input.sys, "stdin", stream):
            with patch.object(key_input, "termios", create=True) as terminal:
                with key_input.terminal_input():
                    self.assertEqual(key_input.read_key(), Key.SPACE)
                    self.assertEqual(key_input.read_key(), Key.ENTER)
            terminal.tcgetattr.assert_not_called()
            terminal.tcsetattr.assert_not_called()

    def test_loop_cli_wraps_interactive_screen_chain(self):
        from goal2 import loop

        with tempfile.TemporaryDirectory() as directory:
            state_path = Path(directory) / "state"
            data_path = Path(directory) / "data"
            state_path.write_bytes(b"state")
            data_path.write_bytes(b"data")
            with (patch.object(loop, "load_goaldat", return_value="goaldat"),
                  patch.object(loop, "from_savestate", return_value="state"),
                  patch.object(loop, "run_main_loop") as run,
                  patch.object(loop, "terminal_input") as context):
                events = []
                manager = context.return_value
                manager.__enter__.side_effect = lambda: events.append("enter")
                manager.__exit__.side_effect = lambda *args: events.append("exit") or False

                def run_chain(*args, **kwargs):
                    self.assertEqual(events, ["enter"])
                    events.append("run")
                    self.assertTrue(callable(kwargs["on_save"]))
                    return 7

                run.side_effect = run_chain
                self.assertEqual(loop.main(["loop", str(state_path), str(data_path)]), 7)
            context.assert_called_once_with()
            run.assert_called_once()
            self.assertEqual(run.call_args.args, ("goaldat", "state", b"state"))
            self.assertTrue(callable(run.call_args.kwargs["on_save"]))
            self.assertEqual(events, ["enter", "run", "exit"])


if __name__ == "__main__":
    unittest.main()
