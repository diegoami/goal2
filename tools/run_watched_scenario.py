#!/usr/bin/env python3
"""[designed: T51a] Select one existing E034 scenario without changing pinned files or assertions."""
import ast
from pathlib import Path
import sys


def selected_source(raw, index):
    tree = ast.parse(raw)
    found = 0
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "scenarios" for t in node.targets):
            if not isinstance(node.value, ast.List) or not 0 <= index < len(node.value.elts):
                raise ValueError("scenario index outside accepted literal list")
            node.value.elts = [node.value.elts[index]]
            found += 1
    if found != 1:
        raise ValueError("expected exactly one accepted scenarios list")
    return ast.fix_missing_locations(tree)


def main():
    file, index = Path(sys.argv[1]), int(sys.argv[2])
    sys.argv = [str(file)] + sys.argv[3:]
    exec(compile(selected_source(file.read_text(), index), str(file), "exec"),
         {"__name__": "__main__", "__file__": str(file)})


if __name__ == "__main__":
    main()
