"""[designed: T215] Unconditional layout assertions for every UI screen and capture."""
from pathlib import Path


def assert_no_exemptions(testcase):
    """The foundation has no transitional layout exemption modules."""
    for name in ("reflow_pending.py", "grid_pending.py"):
        testcase.assertFalse(Path(__file__).with_name(name).exists(), name)


def screen_key(window, capture=None):
    if capture is not None:
        return capture
    current = getattr(window, "current", None)
    screen = current() if current is not None else None
    name = type(screen).__name__ if screen is not None else type(window).__name__
    return f"{name}@{window.width()}x{window.height()}"


def context(window, message=None, capture=None):
    return screen_key(window, capture) + (f" {message}" if message is not None else "")


def assert_fits(testcase, window, message=None, capture=None):
    from goal2.desktop import fixed_page
    testcase.assertEqual(fixed_page.problems(window), [], context(window, message, capture))


def assert_on_grid(testcase, window, message=None, capture=None):
    from goal2.ui import grid_check
    testcase.assertEqual(grid_check.violations(window), [], context(window, message, capture))


def assert_fills(testcase, window, widget, fraction, message=None):
    testcase.assertGreaterEqual(widget.height(), fraction * window.page.height(), context(window, message))


def assert_room(testcase, window, have, need, message=None):
    testcase.assertGreaterEqual(have, need, context(window, message))
