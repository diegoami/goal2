"""The GOAL.DAT loader: reads the data file, exposes its ten blocks, runs F002's checks.

The block table is from `static/goal-dat/blocks.tsv` in goal2-archaeology
(F002 R001): the offsets and sizes are the loader's, in file order, and the
records' layouts match the original game's loading code (`GOAL.EXE` 1771:018A,
`seg_1771_01.asm`).

[confirmed: the block sizes, the SHA256, the country/player/manager record
layouts, the three per-country arrays, the two permutations and the squad-20
shape all come from F002 (R001–R011).]
[designed: the loader exposes the data as Python objects; the CLI form is
this rebuild's; the checks are the same ones `tools/static/goaldat.py` in
archaeology runs, but written as a library function so the test suite can
import them.]
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field


SHA256 = "bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca"
SIZE = 44040


# (name, file_offset, size, record_size, records) in file order, from F002 R001.
BLOCKS: list[tuple[str, int, int, int, int]] = [
    ("country_names", 0x0000, 0x0810, 16, 129),
    ("player_names", 0x0810, 0x8387, 11, 3061),
    ("player_initials", 0x8B97, 0x0BF5, 1, 3061),
    ("manager_names", 0x978C, 0x06DB, 13, 135),
    ("manager_initials", 0x9E67, 0x0087, 1, 135),
    ("per_country_3", 0x9EEE, 0x0183, 3, 129),
    ("per_country_a", 0xA071, 0x0081, 1, 129),
    ("per_country_b", 0xA0F2, 0x0081, 1, 129),
    ("per_country_c", 0xA173, 0x0081, 1, 129),
    ("squad_20", 0xA1F4, 0x0A14, 20, 129),
]
# Confirm: every record_size * records == size, and the blocks tile the file.
_total = 0
for _name, _off, _size, _rec, _n in BLOCKS:
    assert _rec * _n == _size, f"block {_name}: {_rec} * {_n} != {_size}"
    _total += _size
assert _total == SIZE, f"block tiles cover {_total}, expected {SIZE}"


@dataclass
class GoalDat:
    """The ten blocks of GOAL.DAT, indexed by record number (0 is a placeholder).
    [confirmed: the block list and indices are F002 R001 — country names records 1..128,
    player names 1..3060, manager names 1..128 + 6 zero records 129..134, the four
    per-country arrays indexed 0..128, the squad-20 array indexed 0..128.]"""
    country_names: list[str] = field(default_factory=list)
    player_names: list[str] = field(default_factory=list)
    player_initials: list[str] = field(default_factory=list)
    manager_names: list[str] = field(default_factory=list)
    manager_initials: list[str] = field(default_factory=list)
    per_country_3: list[tuple[int, int, int]] = field(default_factory=list)
    per_country_a: list[int] = field(default_factory=list)
    per_country_b: list[int] = field(default_factory=list)
    per_country_c: list[int] = field(default_factory=list)
    squad_20: list[list[int]] = field(default_factory=list)


def _pascal_record(data: bytes, off: int, rec: int) -> str:
    """A record of byte 0 = length, the rest the characters (zero-padded).
    [designed: the F002 records have byte 0 = length and the bytes after it
    printable ASCII; the rebuild's loader reads them as such. The exact
    loader address in GOAL.EXE is not cited here — that's an archaeology
    claim, and the round-1 review by luna flagged the unverified `1771:2E93`
    citation. A future task can add the listing line.]"""
    ln = data[off]
    if ln == 0:
        return ""
    if ln > rec - 1:
        ln = rec - 1
    return data[off + 1:off + 1 + ln].decode("cp437")


def load(data: bytes) -> GoalDat:
    """Read GOAL.DAT, verify its SHA256 against the pinned value, return the parsed blocks.

    The SHA256 is the F002 R001 pinned value; it is not a parameter, so a caller
    cannot supply a different hash and bypass the check. Raises ValueError on a
    wrong file (wrong size, wrong SHA256).
    [confirmed: the pinned SHA256 is F002 R001, the released GOAL.DAT.]
    """
    if len(data) != SIZE:
        raise ValueError(f"GOAL.DAT: {len(data)} bytes, expected {SIZE}")
    got = hashlib.sha256(data).hexdigest()
    if got != SHA256:
        raise ValueError(f"GOAL.DAT: sha256 {got} != {SHA256}")
    return _parse(data)


def _parse(data: bytes) -> GoalDat:
    out = GoalDat()
    for name, off, _size, rec, n in BLOCKS:
        if name == "country_names":
            out.country_names = [_pascal_record(data, off + rec * i, rec) for i in range(n)]
        elif name == "player_names":
            out.player_names = [_pascal_record(data, off + rec * i, rec) for i in range(n)]
        elif name == "player_initials":
            out.player_initials = [chr(data[off + i]) if data[off + i] else "" for i in range(n)]
        elif name == "manager_names":
            out.manager_names = [_pascal_record(data, off + rec * i, rec) for i in range(n)]
        elif name == "manager_initials":
            out.manager_initials = [chr(data[off + i]) if data[off + i] else "" for i in range(n)]
        elif name == "per_country_3":
            out.per_country_3 = [
                (data[off + 3 * i], data[off + 3 * i + 1], data[off + 3 * i + 2])
                for i in range(n)
            ]
        elif name == "per_country_a":
            out.per_country_a = [data[off + i] for i in range(n)]
        elif name == "per_country_b":
            out.per_country_b = [data[off + i] for i in range(n)]
        elif name == "per_country_c":
            out.per_country_c = [data[off + i] for i in range(n)]
        elif name == "squad_20":
            out.squad_20 = [list(data[off + 20 * i:off + 20 * (i + 1)]) for i in range(n)]
    return out


# --- The R001–R011 checks (F002). Each returns (ok: bool, text: str). --------

def _check_R001(data: bytes) -> tuple[bool, str]:
    ok = len(data) == SIZE and hashlib.sha256(data).hexdigest() == SHA256
    return ok, (
        f"{len(data)} bytes, sha256 {hashlib.sha256(data).hexdigest()} "
        f"({SIZE} bytes, sha256 {SHA256})"
    )


def _pascal_block(data: bytes, off: int, rec: int, n: int, maxlen: int) -> tuple[list[int], int, int, int]:
    """Records 1..n-1: malformed indices, equal counts, longer, shorter."""
    bad: list[int] = []
    equal = longer = shorter = 0
    for i in range(1, n):
        r = data[off + rec * i:off + rec * (i + 1)]
        ln = r[0]
        k = 1
        while k < rec and 0x20 <= r[k] < 0x7F:
            k += 1
        run = k - 1
        if not (1 <= ln <= maxlen and run >= 1 and (k == rec or r[k] == 0)):
            bad.append(i)
            continue
        if run == ln:
            equal += 1
        elif run > ln:
            longer += 1
        else:
            shorter += 1
    return bad, equal, longer, shorter


def _check_R002(data: bytes) -> tuple[bool, str]:
    name, off, _, rec, n = BLOCKS[0]
    bad, equal, longer, shorter = _pascal_block(data, off, rec, n, 15)
    zero_first = not any(data[off:off + rec])
    ok = not bad and zero_first
    return ok, (
        f"0x{off:04X}: 128 country names, 1..15 chars, record 0 all zero; "
        f"equal {equal}, longer {longer}, shorter {shorter}; first {data[off + 17:off + 17 + data[off + 16]]!r}"
    )


def _check_R003(data: bytes) -> tuple[bool, str]:
    name, off, _, rec, n = BLOCKS[1]
    bad, equal, longer, shorter = _pascal_block(data, off, rec, n, 10)
    zero_first = not any(data[off:off + rec])
    ok = not bad and zero_first
    return ok, (
        f"0x{off:04X}: 3060 player names, 1..10 chars, record 0 all zero; "
        f"equal {equal}, longer {longer}, shorter {shorter}; record 1 {data[off + 12:off + 12 + data[off + 11]]!r}"
    )


def _check_R004(data: bytes) -> tuple[bool, str]:
    _, off, _, _, n = BLOCKS[2]
    letters = data[off + 1:off + n]
    ok = data[off] == 0 and all(65 <= b <= 90 for b in letters)
    return ok, f"0x{off:04X}: 3060 upper-case initials; {len(set(letters))} distinct"


def _check_R005(data: bytes) -> tuple[bool, str]:
    off, sz, rec, n = BLOCKS[3][1], BLOCKS[3][2], BLOCKS[3][3], BLOCKS[3][4]
    bad, equal, longer, shorter = _pascal_block(data, off, rec, 129, 12)
    zero_first = not any(data[off:off + rec])
    tail_zero = not any(data[off + rec * 129:off + sz])
    ok = not bad and zero_first and tail_zero
    return ok, (
        f"0x{off:04X}: 128 manager names + 6 zero records; equal {equal}, "
        f"longer {longer}, shorter {shorter}"
    )


def _check_R006(data: bytes) -> tuple[bool, str]:
    _, off, _, _, n = BLOCKS[4]
    letters = data[off + 1:off + 129]
    ok = (data[off] == 0 and all(65 <= b <= 90 for b in letters)
          and not any(data[off + 129:off + n]))
    return ok, f"0x{off:04X}: 128 upper-case initials + 6 zero bytes"


def _check_R007(data: bytes) -> tuple[bool, str]:
    off, sz, _, n = BLOCKS[5][1], BLOCKS[5][2], BLOCKS[5][3], BLOCKS[5][4]
    vals = list(data[off + 3:off + sz])
    counts = {v: vals.count(v) for v in sorted(set(vals))}
    ok = not any(data[off:off + 3]) and all(9 <= v <= 15 for v in vals)
    return ok, f"0x{off:04X}: 128 per-country triples in 9..15; counts {counts}"


def _check_R008(data: bytes) -> tuple[bool, str]:
    off, sz, _, n = BLOCKS[6][1], BLOCKS[6][2], BLOCKS[6][3], BLOCKS[6][4]
    v = list(data[off:off + sz])
    # F002 R008: byte 0 is 0; bytes 1..128 hold at least two distinct values
    # (i.e. the per-country tactic byte is not constant). The data on the released
    # file holds 34 distinct values, not 128; the F002 text reports the actual
    # count. The check is "not all the same" — a corruption that zeroes or
    # homogenises the block fails it. (R1 on the round-1 review by luna: the
    # prior message said "128 distinct" but the check was `> 1`; this rewrite
    # makes the check and message agree.)
    n_distinct = len(set(v[1:]))
    ok = v[0] == 0 and n_distinct > 1
    return ok, f"0x{off:04X}: byte 0 is 0; bytes 1..128 hold {n_distinct} distinct values in {min(v[1:])}..{max(v[1:])}"


def _check_R009(data: bytes) -> tuple[bool, str]:
    off, sz, _, n = BLOCKS[7][1], BLOCKS[7][2], BLOCKS[7][3], BLOCKS[7][4]
    v = list(data[off:off + sz])
    ok = v[0] == 0 and sorted(v) == list(range(n))
    return ok, f"0x{off:04X}: permutation of 0..128 ({'OK' if ok else 'not a permutation'})"


def _check_R010(data: bytes) -> tuple[bool, str]:
    off, sz, _, n = BLOCKS[8][1], BLOCKS[8][2], BLOCKS[8][3], BLOCKS[8][4]
    v = list(data[off:off + sz])
    ok = v[0] == 0 and sorted(v) == list(range(n))
    return ok, f"0x{off:04X}: permutation of 0..128 ({'OK' if ok else 'not a permutation'})"


def _check_R011(data: bytes) -> tuple[bool, str]:
    off, sz, rec, n = BLOCKS[9][1], BLOCKS[9][2], BLOCKS[9][3], BLOCKS[9][4]
    allv = list(data[off + 20:off + sz])
    sorted_both = 0
    exceptions: list[int] = []
    zeros_ok = True
    for i in range(1, n):
        r = list(data[off + 20 * i:off + 20 * (i + 1)])
        a, b = r[:11], r[11:]
        if a == sorted(a) and b == sorted(b):
            sorted_both += 1
        else:
            exceptions.append(i)
        if r[0] != 0 or r[11] != 0:
            zeros_ok = False
    ok = (not any(data[off:off + 20]) and zeros_ok
          and min(allv) == 0 and max(allv) == 13 and len(set(allv)) == 14)
    return ok, (
        f"0x{off:04X}: 128 squad-20 records; values in 0..13 (14 distinct); "
        f"bytes 0..10 and 11..19 non-decreasing in {sorted_both} of 128; "
        f"first/byte-11 zeros in all"
    )


_CHECKS = [
    ("R001", _check_R001),
    ("R002", _check_R002),
    ("R003", _check_R003),
    ("R004", _check_R004),
    ("R005", _check_R005),
    ("R006", _check_R006),
    ("R007", _check_R007),
    ("R008", _check_R008),
    ("R009", _check_R009),
    ("R010", _check_R010),
    ("R011", _check_R011),
]


def run_checks(data: bytes) -> list[tuple[str, bool, str]]:
    """Every F002 check that the data file is well-formed, with their outcome and one-line text."""
    return [(cid, ok, text) for cid, fn in _CHECKS for (ok, text) in [fn(data)]]
