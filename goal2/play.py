"""The CLI entry point: `python -m goal2.play <savestate>`.

The actual implementation lives in `goal2.cli` so it is reachable as both `python -m goal2.play`
(T01's contract) and `python -m goal2.cli` (the pyproject script entry). [designed]
"""
from goal2.cli import main


if __name__ == "__main__":
    main()
