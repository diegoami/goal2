"""The 12 skills: derived from three record bytes (+4, +5, +7) via the class and profile tables.

The player screen draws 12 skill bars (F008). Each bar's length is
`profile[12 * (+5) + c] * ((+4) + 1) // 256`, where `c = class[12 * (+7) + i]`
for skill i (1..12). The class table (14 positions × 12 rows) is at
`DS:6D25` in the savestate; the profile table (16 profiles × 12 classes,
values 5..26) is at `DS:6DCD`. Both are in the savestate's data segment
(`DS:6D20..6EB3`, 404 bytes).

The class table is 1-indexed: the entries for position p, skill i (1..12)
are at `DS:6D25 + 12*p + i`. The first byte of each position block
(`DS:6D25 + 12*p`) is unused. The profile table is also 1-indexed: the
entry for profile p, class c (1..12) is at `DS:6DCD + 12*p + c`. The
first byte of each profile block is unused.

The 12 skills, in the order F008 names them: keeping, kicking, tackling,
heading, marking, passing, crossing, feinting, control, dribbling,
shooting, penalties. `goal kicking` is NOT shown (F008: the template
holds the name `kicking` once and `goal kicking` nowhere; the 12 shown
are the 13 in `GOAL.HLP` without `goal kicking`).

[confirmed: F008 is the per-field source; the formula, the table offsets
and the 12-skill order are the listing traces the finding cites.]
[designed: the Python encoding of F008's analysis is this rebuild's;
the fidelity test (E007-r0009..r0012) is the arbiter.]
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from goal2.engine.savestate import Savestate


# [confirmed: F008] The 12 skills, in the order the player screen draws them.
SKILL_NAMES = (
    "keeping", "kicking", "tackling", "heading", "marking", "passing",
    "crossing", "feinting", "control", "dribbling", "shooting", "penalties",
)
N_SKILLS = 12

# [confirmed: F008] The class table is at DS:6D25, 14 positions × 12 rows
# (1-indexed: entries at DS:6D25 + 12*p + i for i=1..12).
CLASS_TABLE_OFFSET = 0x6D25
CLASS_TABLE_POSITIONS = 14
CLASS_TABLE_ROWS = 12

# [confirmed: F008] The profile table is at DS:6DCD, 16 profiles × 12 classes
# (1-indexed: entries at DS:6DCD + 12*p + c for c=1..12).
PROFILE_TABLE_OFFSET = 0x6DCD
PROFILE_TABLE_PROFILES = 16
PROFILE_TABLE_CLASSES = 12


def load_class_table(state: "Savestate") -> bytes:
    """[confirmed: F008] Read the 14-position class table from DS:6D25 of the savestate.
    The entries are 1-indexed: `class[12 * position + i]` (for i=1..12) gives the
    class index for skill i at that position. The first byte of each position
    block (index 12*position) is unused. Returns 14*12+1 = 169 bytes so the
    last entry (position 13, skill 12, offset 168) is included.
    """
    return state.ds_bytes(CLASS_TABLE_OFFSET, CLASS_TABLE_POSITIONS * CLASS_TABLE_ROWS + 1)


def load_profile_table(state: "Savestate") -> bytes:
    """[confirmed: F008] Read the 16-profile table from DS:6DCD of the savestate.
    The entries are 1-indexed: `profile[12 * profile_index + class]` (for class
    1..12) gives the curve value for that profile and class (values 5..26).
    The first byte of each profile block is unused. Returns 17*12+1 = 205
    bytes so the last entry (profile 16, class 12, offset 204) is included.
    """
    return state.ds_bytes(
        PROFILE_TABLE_OFFSET,
        (PROFILE_TABLE_PROFILES + 1) * PROFILE_TABLE_CLASSES + 1,
    )


def skills(
    record: bytes,
    class_table: bytes,
    profile_table: bytes,
) -> list[int]:
    """[confirmed: F008] The 12 skill bar lengths for a player record.
    `bar[i] = profile[12 * (+5) + class[12 * (+7) + i + 1]] * ((+4) + 1) // 256`.

    The record is the 20-byte player record. `+4` is the current ability
    (the scale), `+5` is the profile (0..16), `+7` is the position (0..13).
    Returns 12 bar lengths, each 0..25.

    The class table and profile table are both 1-indexed (F008): the class
    for skill i (1..12) at position p is at `class_table[12*p + i]`, and the
    profile value for class c (1..12) at profile p is at
    `profile_table[12*p + c]`.
    """
    ability = record[4]  # +4 current ability, the scale
    profile_idx = record[5]  # +5 profile, 0..16
    position = record[7]  # +7 position, 0..13 (not +6, per F008)
    bars = []
    for i in range(N_SKILLS):
        # Class table is 1-indexed: skill i (1..12) is at offset 12*position + i.
        class_idx = class_table[12 * position + i + 1]
        # Profile table is 1-indexed: class c (1..12) is at offset 12*profile + c.
        profile_value = profile_table[12 * profile_idx + class_idx]
        bar = (profile_value * (ability + 1)) // 256
        bars.append(bar)
    return bars
