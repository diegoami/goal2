"""Computer-opponent stand-ins (A-CPU-1 + A-CPU-2).

[designed: T46] Two pure functions consumed by quick-match setup without state/RNG mutation.
[derived: F007 at0ef880e1f6ec9bc12b3f12c3aaecb4d747d9d5cb] Ability is byte+4, age+1. Per A-CPU-1
stand-in: picks top 11 by ability ignoring formation. Per A-CPU-2 read
side: returns the country's stored tactics byte.
"""
from __future__ import annotations


def pick_computer_eleven(player_records: list[bytes], squad_indices: list[int]) -> list[int]:
    """[designed: assumptions.md A-CPU-1, F007] Return the top 11 squad members by ability.

    Sorts ``squad_indices`` by descending player ability (player_records[i][4])
    per F007, then ascending squad index (tie-break: lower index wins).
    Returns the first 11 of the sorted list.
    Raises ValueError if fewer than 11 squad members are supplied.

    [assumed: Q035] The per-position refinement (best player per formation
    slot) waits for Q035.
    """
    if len(squad_indices) < 11:
        raise ValueError("country must have at least 11 squad members")

    def sort_key(idx: int) -> tuple[int, int]:
        ability = player_records[idx][4]
        return (-ability, idx)

    return sorted(squad_indices, key=sort_key)[:11]


def get_computer_tactics(country_record: bytes) -> int:
    """[designed: assumptions.md A-CPU-2 read side, F010] Return the country's stored tactics byte.

    Returns the byte at ``country_record[0x2D]`` (0..255) per F010, one of
    the 8 tactics bits.
    The country record must be at least 0xBF bytes; offset 0x2D is always
    valid within that bound.
    """
    return country_record[0x2D]
