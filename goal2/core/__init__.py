"""goal2's core: the original game's own code run under Unicorn from a main-screen savestate (docs/core.md).

[designed: owner, 2026-10-22, #308] Importing it needs nothing but the standard library and the vendored kit;
`Core.start` needs the optional `unicorn` package (goal2[watched]) and says so when it is missing.

    from goal2.core import Core
    wait = Core.start(open(".cache/e006-r0001-main.sav", "rb").read())
    wait.site, wait.text, wait.state.managed, wait.state.year()
    wait = wait.core.press(0x1B)              # Esc: the key code 214B:08DD stores at DS:A976
    blob = wait.core.save(); core = Core.load(blob)
"""
from .runner import BudgetExceeded, Core, CoreError, InterruptError, KeyWait, StateView, DEFAULT_BUDGET

__all__ = ["Core", "KeyWait", "StateView", "CoreError", "BudgetExceeded", "InterruptError", "DEFAULT_BUDGET"]
