"""The CLI entry point: `python -m goal2.play <savestate>`.

The actual implementation lives in `goal2.cli` so it is reachable as both `python -m goal2.play`
(T01's contract) and `python -m goal2.cli` (the pyproject script entry). The `play` entry
point propagates the underlying exit code (`main()` returns 0 / 2 / 3 for success, file
errors, and model refusals respectively; `sys.exit` makes that the process's status).
[designed]
"""
import sys

from goal2.cli import main


if __name__ == "__main__":
    sys.exit(main())
