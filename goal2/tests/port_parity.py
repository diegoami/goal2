"""[designed: T151] What "the same match" means between goal2's route, which plays the sealed port, and the original
engine: everything equal except the board screen, which the port does not draw byte-for-byte.

[confirmed: goal2-archaeology experiments/E036-match-port/family.py SCREEN_POINTERS/SCREEN_BYTES and compare.py
--no-screen, milestone m9-port-sealed-engine] The screen is the text page and the two text buffers the far pointers at
DS:A96A, A96E and A972 locate, 4000 bytes each, and the board's digest (`screen_sha256`). The result also names the
engine's input (`image_sha256`: the sealed image) and the ports that ran (`ports`), which the original's has not.
"""
from dataclasses import asdict

from goal2.engine.original_match import Image

SCREEN_POINTERS = (0xA96A, 0xA96E, 0xA972)
SCREEN_BYTES = 4000
PORT_ONLY = ("ports",)
INPUT_IDENTITY = ("image_sha256",)


def _without_screen(value):
    if isinstance(value, dict):
        return {k: _without_screen(v) for k, v in value.items() if k != "screen_sha256"}
    if isinstance(value, (list, tuple)):
        return type(value)(_without_screen(v) for v in value)
    return value


def comparable_result(result):
    return _without_screen({k: v for k, v in result.items() if k not in PORT_ONLY + INPUT_IDENTITY})


def comparable_events(events):
    return [_without_screen(asdict(e) if not isinstance(e, dict) else e) for e in events]


def screen_ranges(memory_component):
    """The linear ranges of the screen in a Memory component's guest memory."""
    image = Image(memory_component)
    return [(image.far(p), image.far(p) + SCREEN_BYTES) for p in SCREEN_POINTERS]


def comparable_memory(memory_component):
    image = Image(memory_component)
    memory = bytearray(image.memory)
    for lo, hi in screen_ranges(memory_component):
        memory[lo:hi] = bytes(hi - lo)
    return bytes(image.header), bytes(memory)


def assert_same_match(test, port_result, port_memory, port_events, result, memory, events):
    """The port's match is the original's: result, events and memory, the screen excepted."""
    test.assertIn("ports", port_result)
    test.assertEqual(comparable_result(port_result), comparable_result(result))
    test.assertEqual(comparable_events(port_events), comparable_events(events))
    test.assertEqual(comparable_memory(port_memory), comparable_memory(memory))
