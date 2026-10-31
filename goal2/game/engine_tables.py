"""[designed: owner, 2026-10-31, CLAUDE.md rule 14; T150] The sealed match engine's constant tables,
vendored with the engine in goal2/engine/tables/ (ds.hex, code_data.hex and their manifest).

[confirmed: goal2-archaeology m9-port-sealed-engine (#629 there), docs/handover/T80.md] They are GOAL.EXE's
initialised data DS:0000..7B6F and the code segments' data areas; `port.tables.load` refuses a folder whose
tables differ from the manifest's digests.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from goal2.engine.original_match.port import tables as port_tables

FOLDER = Path(__file__).resolve().parents[1] / "engine" / "tables"
TablesError = port_tables.TablesError


@lru_cache(maxsize=None)
def load(folder=FOLDER):
    """The vendored tables (TablesError when they differ from their manifest)."""
    return port_tables.load(folder)
