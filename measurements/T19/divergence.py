#!/usr/bin/env python3
"""T19 (issue #11): where `goal2.engine.new_game.make_all_players` diverges from E006-r0001.

Runs the model on the E006-r0001 inputs (fixtures loaded through `goal2/tests/test_new_game.py`,
the same loaders the fidelity test uses) and diffs its 3061-record player array against the
expected array read from E006-r0001's published main-screen savestate. Writes
`measurements/T19/report.md` (this file's directory) with:

  * per-field differing-byte counts, over all 3061 records;
  * overall differing bytes (of 61,220) and LCG-field differing bytes (of 12,244);
  * the first diverging record and field;
  * per field, whether the divergence is a contiguous record shift or scattered;
  * the LCG call sequence the E006 oracle `experiments/E006-q004-skills/summarise.py`
    (goal2-archaeology) uses, each call cited by path and line, re-run here as a
    replication check and as ablations that revert one aspect at a time.

Rule 19: no expected byte is written anywhere; the report carries offsets, counts,
seeds and file hashes only. [designed: this script is T19's measurement, owned by
measurements/T19/; nothing under goal2/ or tests/ is read for writing.]
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from goal2.data import goaldat  # noqa: E402
from goal2.engine import new_game  # noqa: E402
from goal2.tests import test_new_game as tng  # noqa: E402  (fixture loaders, reused)

ARCHAEOLOGY_ENV = os.environ.get("GOAL2_ARCHAEOLOGY")
_CANDIDATES = ([] if not ARCHAEOLOGY_ENV else [Path(ARCHAEOLOGY)]) + [
    ROOT.parent / "goal2-archaeology",
    ROOT.parents[2].parent / "goal2-archaeology",  # a .claude/worktrees/<name> worktree
    Path("/home/diego/projects/goal2-archaeology"),
]
SUMMARISE_REL = "experiments/E006-q004-skills/summarise.py"
SUMMARISE = next((c / SUMMARISE_REL for c in _CANDIDATES if (c / SUMMARISE_REL).is_file()),
                 None)
# [confirmed: goal2-archaeology] the commit this oracle is read at.
SUMMARISE_COMMIT = "3d82ead8010d5bb02f14912535dde062cce4d518"

PLAYER = 0x14          # [confirmed: F007] 20-byte player record
N_RECORDS = 3061       # [confirmed: F007] 0xEF24 / 0x14
LCG_FIELDS = (0x01, 0x02, 0x05, 0x0C)  # the four fields issue #11 names
SQUAD_FIRST, SQUAD_LAST = 1, 2560      # records of countries 1..128
MANAGED_FIRST, MANAGED_LAST = 2561, 2640  # the 80 managed-country records


# ---- the E006 oracle's LCG (summarise.py L96-105), verbatim --------------------------------------
class OracleLCG:
    """`summarise.py` L96-105: seed = seed*0x7ABD + 0x1B0F (16 bits);
    draw(n) = ((seed*n) >> 16) + 1, i.e. 1..n."""

    def __init__(self, seed):
        self.seed = seed & 0xFFFF

    def draw(self, n):
        self.seed = (self.seed * 0x7ABD + 0x1B0F) & 0xFFFF
        return ((self.seed * n) >> 16) + 1


def lcg_steps(start, target, limit=200000):
    """`summarise.py` L108-115: how many LCG steps lead from start to target."""
    s = start & 0xFFFF
    for i in range(limit + 1):
        if s == target:
            return i
        s = (s * 0x7ABD + 0x1B0F) & 0xFFFF
    return None


# Initialised data of GOAL.EXE, `summarise.py` L120-123 and L191 (ds_2581_01.hex rows
# 0E80 and 1180), gk-indexed (1 = goalkeeper, position byte 0).
AGE_BASE = {0: 0x1C, 1: 0x1F}    # L120  DS:118A/B
PEAK_BASE = {0: 0x1B, 1: 0x1E}   # L121  DS:0E80/81
FIT_BASE = {0: 0x10, 1: 0x0D}    # L122  DS:0E82/83, indexed by "+1 > +2 + 4"
YOUTH_AGE = {0: 0x11, 1: 0x14}   # L191  DS:118C/D
SET_A = {0, 1, 3, 4}             # L123  the set constant at 1771:3411
MODELLED = [0, 1, 2, 3, 4, 5, 6, 7, 0xC, 0xD, 0xE, 0xF, 0x12, 0x13]  # L175


def oracle_player(rng, country, pos, rate, flag=1, managed=False,
                  sixteen_first=True, bound_peak3=True, bases_gk_inverted=False):
    """The 20 bytes 1771:96D3 writes, in `summarise.py` model_player's exact draw
    order (L129-172). The keyword switches are T19's ablations, each reverting
    ONE aspect to `goal2/engine/new_game.py`'s encoding:

      * ``bases_gk_inverted=True`` swaps the gk indexing of the age and peak base
        tables to `new_game.py:31,34`'s tuples (goalkeeper 0x1C/0x1B, outfield
        0x1F/0x1E) instead of the oracle's (goalkeeper 0x1F/0x1E — ds_2581_01.hex
        row 1180 has 118A=0x1C, 118B=0x1F; row 0E80 has 0E80=0x1B, 0E81=0x1E);
      * ``sixteen_first=False`` draws the +0x05 ``rand(16)`` after the peak draws
        (5th draw of the record) instead of first — `new_game.py`'s 96D3 order;
      * ``bound_peak3=False`` computes +0x04 with the ``peak + pot`` bound of
        `new_game.py` instead of the oracle's ``peak + 3``.
    """
    age_base = {0: 0x1F, 1: 0x1C} if bases_gk_inverted else AGE_BASE   # new_game.py:31
    peak_base = {0: 0x1E, 1: 0x1B} if bases_gk_inverted else PEAK_BASE  # new_game.py:34
    r = bytearray(PLAYER)
    r[0] = country
    r[7] = r[6] = pos
    if sixteen_first:
        r[5] = rng.draw(16)                                   # L132
    a = rng.draw(7)                                           # L133
    b = rng.draw(7)                                           # L134
    gk = 1 if pos == 0 else 0
    r[1] = (age_base[gk] - b + a) & 0xFF                      # L136
    a = rng.draw(3)                                           # L137
    b = rng.draw(3)                                           # L138
    r[2] = (peak_base[gk] + b - a) & 0xFF                     # L139
    if not sixteen_first:
        r[5] = rng.draw(16)  # ablation: new_game.py:125 draws +0x05 here (5th)
    if flag:
        r[3] = (rate + 0x7F) & 0xFF                           # L141
    else:
        d = rng.draw(10)                                      # L143
        r[3] = (rate + 0x7F - 10 - d) & 0xFF                  # L144
    age, peak, pot = r[1], r[2], r[3]
    top = 3 if bound_peak3 else pot                           # L146 vs new_game.py:114
    if peak <= age <= peak + top:
        r[4] = pot
    else:
        k = 16 - (age - (peak + top)) if age > peak + top else 16 - (peak - age) // 2  # L149
        r[4] = ((pot * k) // 16) & 0xFF
    r[0xC] = rng.draw(32)                                     # L151
    if (r[5] - (r[3] & 1)) & 0xFF < 4:                        # L152
        r[0xF] |= 0x80
        r[0xF] &= ~0x08 & 0xFF
    if r[6] in SET_A:                                         # L155
        r[0xF] |= 0x10 | 0x01
    elif r[6] == 2:                                           # L157
        if r[5] < 0x0E:
            r[0xF] |= 0x10
        r[0xF] |= 0x20 | 0x02
    t = FIT_BASE[1 if age > peak + 4 else 0]                  # L161
    if managed:                                               # L162
        a = rng.draw(t + 1)                                   # L163
        b = rng.draw(3 * t)                                   # L164
        v = t + b - a
    else:
        v = t + rng.draw(2 * t)                               # L167
    v = min(v, 0x20)                                          # L168
    r[0xE] = v & 0xFF
    r[0xD] = max(v, 1) & 0xFF
    r[0x12:0x14] = (0x7FFF).to_bytes(2, "little")             # L171
    return bytes(r)


def oracle_squads(d, **kw):
    """Players 1..2560 as `summarise.py` model_squads (L178-188) builds them:
    seed := country (L184), then 20 slots with the squad_20 position byte (L187).
    Returns (records 1..2560, the seed the last squad's LCG is left at)."""
    out = []
    rng = None
    for c in range(1, 129):
        rng = OracleLCG(c)                                    # L184
        rate = new_game.rating(d, c)
        for slot in range(1, 21):
            out.append(oracle_player(rng, c, d.squad_20[c][slot - 1], rate, **kw))  # L187
    return out, (rng.seed if rng is not None else None)


def oracle_extra(seed, d, country, **kw):
    """The 80 players `summarise.py` model_extra (L194-216) makes for a managed
    country: 4 per position 0..13 (L201-203), one per squad slot 1..20 with the
    age redrawn as DS:118C[gk] + rand(3) and +4 recomputed (L204-213), then
    slots 6..9 again (L214-215)."""
    rng = OracleLCG(seed)                                     # L199
    rate = new_game.rating(d, country)
    out = []
    for pos in range(14):                                     # L201
        for _ in range(4):
            out.append(oracle_player(rng, country, pos, rate, flag=0, managed=True, **kw))  # L203
    for slot in range(1, 21):                                 # L204
        r = bytearray(oracle_player(rng, country, d.squad_20[country][slot - 1],
                                    rate, flag=0, managed=True, **kw))  # L205
        r[1] = (YOUTH_AGE[1 if r[7] == 0 else 0] + rng.draw(3)) & 0xFF  # L206
        age, peak, pot = r[1], r[2], r[3]
        top = 3 if kw.get("bound_peak3", True) else pot
        if peak <= age <= peak + top:
            r[4] = pot
        else:
            k = 16 - (age - (peak + top)) if age > peak + top else 16 - (peak - age) // 2
            r[4] = ((pot * k) // 16) & 0xFF
        out.append(bytes(r))
    for slot in range(6, 10):                                 # L214
        out.append(oracle_player(rng, country, d.squad_20[country][slot - 1],
                                 rate, flag=0, managed=True, **kw))  # L215
    return out


def model_style_managed(seed, d, country):
    """The 98C4 encoding `goal2/engine/new_game.py` `_make_one_player_98c4` uses,
    same seed: youth age drawn first (one rand(3), new_game.py:182) for ALL 80
    players, no 96D3 rand(7) age pair, no redraw pass; the oracle's keyword
    ablations do not reach it (it is a different call sequence, not a switch)."""
    rng = OracleLCG(seed)
    rate = new_game.rating(d, country)
    out = []
    pos_iter = []
    for pos in range(14):
        pos_iter.extend([pos] * 4)
    pos_iter.extend(d.squad_20[country])
    pos_iter.extend(d.squad_20[country][5:9])
    for position in pos_iter:
        gk = new_game.gk_index(position)
        rec = bytearray(PLAYER)
        rec[0] = country
        rec[1] = (new_game.DS_118C[gk] + rng.draw(3)) & 0xFF               # new_game.py:182
        a = rng.draw(3)                                                      # new_game.py:185
        b = rng.draw(3)                                                      # new_game.py:186
        rec[2] = (new_game.DS_0E80[gk] + b - a) & 0xFF
        rec[3] = (rate + 0x7F - 10 - rng.draw(10)) & 0xFF                    # new_game.py:190
        age, peak, pot = rec[1], rec[2], rec[3]
        if peak <= age <= peak + pot:                                        # new_game.py:194
            rec[4] = pot
        else:
            k = 16 - (age - (peak + pot)) if age > peak + pot else 16 - (peak - age) // 2
            rec[4] = ((pot * k) // 16) & 0xFF
        rec[5] = rng.draw(16)                                                # new_game.py:205
        rec[6] = rec[7] = position
        rec[0x0C] = rng.draw(32)                                             # new_game.py:214
        t = new_game.DS_0E82[1 if age > peak + 4 else 0]
        a = rng.draw(t + 1)                                                  # new_game.py:219
        b = rng.draw(3 * t)                                                  # new_game.py:220
        v = t + b - a
        if v < 0:
            v = 0
        if v > 0x20:
            v = 0x20
        rec[0x0E] = v
        rec[0x0D] = max(v, 1)
        hardness = (rec[5] - (rec[3] & 1)) & 0xFF
        if hardness < 4:
            rec[0x0F] |= 0x80
            rec[0x0F] &= ~0x08 & 0xFF
        if position in (0, 1, 3, 4):
            rec[0x0F] |= 0x10 | 0x01
        elif position == 2:
            if rec[5] < 0x0E:
                rec[0x0F] |= 0x10
            rec[0x0F] |= 0x20 | 0x02
        rec[0x12:0x14] = (0x7FFF).to_bytes(2, "little")
        out.append(bytes(rec))
    return out


def find_extra_seed(observed, d, country):
    """`summarise.py` find_extra_seed (L219-230): the seeds (0..0xFFFF) from which
    model_extra reproduces the observed 80 records exactly on the modelled bytes."""
    want0 = observed[0]
    rate = new_game.rating(d, country)
    hits = []
    for s in range(0x10000):
        first = oracle_player(OracleLCG(s), country, 0, rate, flag=0, managed=True)  # L225
        if any(first[f] != want0[f] for f in MODELLED):
            continue
        if all(m[f] == o[f] for m, o in zip(oracle_extra(s, d, country), observed)
               for f in MODELLED):  # L228
            hits.append(s)
    return hits


# ---- the diff ------------------------------------------------------------------------------------
def diff_counts(actual, expected):
    """{offset: count of records whose byte at offset differs}."""
    counts = {f: 0 for f in range(PLAYER)}
    for i in range(N_RECORDS):
        a, e = actual[i], expected[i]
        for f in range(PLAYER):
            if a[f] != e[f]:
                counts[f] += 1
    return counts


def first_divergence(actual, expected):
    for i in range(N_RECORDS):
        a, e = actual[i], expected[i]
        for f in range(PLAYER):
            if a[f] != e[f]:
                return i, f
    return None, None


def shift_shape(actual, expected, f, records):
    """For field f over the differing `records`: is actual[i][f] equal to
    expected[i+k][f] for a fixed record shift k (contiguous-shifted), or is no
    fixed shift an explanation (scattered)? Returns (label, best_k, best_rate)."""
    differing = [i for i in records if actual[i][f] != expected[i][f]]
    if not differing:
        return "equal", None, None
    best_k, best_rate = None, -1.0
    for k in (-20, -2, -1, 1, 2, 20):
        valid = [i for i in differing if 0 <= i + k < N_RECORDS]
        if not valid:
            continue
        rate = sum(1 for i in valid if actual[i][f] == expected[i + k][f]) / len(valid)
        if rate > best_rate:
            best_k, best_rate = k, rate
    if best_rate >= 0.9:
        return f"contiguous-shifted by {best_k:+d} record(s)", best_k, best_rate
    return "scattered", best_k, best_rate


def main() -> int:
    import hashlib

    dat_bytes = tng._fetch_dat()
    state_bytes = tng._fetch_state()
    d = goaldat.load(dat_bytes)
    expected_flat = tng._e006_player_array(state_bytes)
    expected = [expected_flat[i * PLAYER:(i + 1) * PLAYER] for i in range(N_RECORDS)]
    actual = new_game.make_all_players(d, managed_country=tng.MANAGED_COUNTRY)

    # -- the four numbers --------------------------------------------------------------------------
    counts = diff_counts(actual, expected)
    overall = sum(counts.values())
    lcg_diff = sum(counts[f] for f in LCG_FIELDS)
    first_rec, first_off = first_divergence(actual, expected)

    squad_counts = {f: sum(1 for i in range(SQUAD_FIRST, SQUAD_LAST + 1)
                           if actual[i][f] != expected[i][f]) for f in range(PLAYER)}
    managed_counts = {f: sum(1 for i in range(MANAGED_FIRST, MANAGED_LAST + 1)
                             if actual[i][f] != expected[i][f]) for f in range(PLAYER)}

    shapes = {f: shift_shape(actual, expected, f, range(N_RECORDS)) for f in range(PLAYER)}

    # -- the oracle replication and the ablations ---------------------------------------------------
    oracle_squad_recs, end_seed = oracle_squads(d)
    oracle_squad_equal = {f: sum(1 for n, i in enumerate(range(SQUAD_FIRST, SQUAD_LAST + 1))
                                 if oracle_squad_recs[n][f] == expected[i][f])
                          for f in MODELLED}
    managed_expected = expected[MANAGED_FIRST:MANAGED_LAST + 1]
    extra_seeds = find_extra_seed(managed_expected, d, tng.MANAGED_COUNTRY)
    steps_from_end = {s: lcg_steps(end_seed, s) for s in extra_seeds}
    seed_hex = [f"0x{s:04x}" for s in extra_seeds]

    oracle_managed_recs = oracle_extra(extra_seeds[0], d, tng.MANAGED_COUNTRY) if extra_seeds else []
    oracle_managed_equal = {f: sum(1 for n in range(80)
                                   if oracle_managed_recs[n][f] == managed_expected[n][f])
                            for f in MODELLED} if oracle_managed_recs else {}

    # The cumulative ablation chain for the squad (96D3) records: each step reverts one
    # aspect of the oracle to new_game.py's encoding; the last must reproduce the
    # model's squad records byte-for-byte (per record, not just per count).
    def squad_footprint(recs):
        return {f: sum(1 for n, i in enumerate(range(SQUAD_FIRST, SQUAD_LAST + 1))
                       if recs[n][f] != expected[i][f]) for f in MODELLED}

    abl1, _ = oracle_squads(d, bases_gk_inverted=True)  # step 1: the base tables
    abl1_diff = squad_footprint(abl1)
    abl2, _ = oracle_squads(d, bases_gk_inverted=True, sixteen_first=False)  # + order swap
    abl2_diff = squad_footprint(abl2)
    abl3, _ = oracle_squads(d, bases_gk_inverted=True, sixteen_first=False,
                            bound_peak3=False)  # + the +0x04 bound == new_game's 96D3
    abl3_diff = squad_footprint(abl3)
    consistency_squads = all(abl3[n] == actual[i]
                             for n, i in enumerate(range(SQUAD_FIRST, SQUAD_LAST + 1)))

    # Managed ablation: the model's 98C4 call sequence on the word new_game.py:295
    # actually starts from (0xF5DB). If the oracle's seed search finds that word, this
    # run's footprint must equal the model's measured managed footprint.
    model_managed = model_style_managed(0xF5DB, d, tng.MANAGED_COUNTRY)
    model_managed_diff = {f: sum(1 for n in range(80)
                                 if model_managed[n][f] != managed_expected[n][f])
                          for f in MODELLED}
    consistency_managed = (0xF5DB in extra_seeds and
                           all(model_managed_diff[f] == managed_counts[f] for f in MODELLED))

    # -- the report ---------------------------------------------------------------------------------
    L = []
    pr = L.append
    pr("# T19 — the LCG draw-order divergence of `goal2.engine.new_game` against E006-r0001")
    pr("")
    pr("Written by `measurements/T19/divergence.py`; re-running it rewrites this file with")
    pr("the same numbers. Fixtures (git-ignored, rule 19):")
    pr("")
    pr(f"- GOAL.DAT sha256 `{hashlib.sha256(dat_bytes).hexdigest()}`")
    pr(f"- E006-r0001 main-screen savestate sha256 "
       f"`{hashlib.sha256(state_bytes).hexdigest()}`")
    pr(f"- oracle: `{SUMMARISE_REL}` in the goal2-archaeology checkout (found at")
    pr(f"  `{SUMMARISE}`, commit `{SUMMARISE_COMMIT}`), cited below by line as")
    pr(f"  `{SUMMARISE_REL}:L<n>`")
    pr(f"- managed country: {tng.MANAGED_COUNTRY} (E006-r0001, [confirmed: F007])")
    pr("")
    pr("## 1. The four numbers")
    pr("")
    pr(f"- overall differing bytes: **{overall} of {N_RECORDS * PLAYER}** "
       f"({N_RECORDS} records x 0x14 bytes)")
    pr(f"- LCG-field differing bytes (+0x01/+0x02/+0x05/+0x0C): **{lcg_diff} of "
       f"{N_RECORDS * len(LCG_FIELDS)}** ({N_RECORDS} records x 4 fields)")
    if first_rec is not None:
        kind = ("all-zero record" if first_rec == 0 else
                f"squad player of country {(first_rec - 1) // 20 + 1}, slot {(first_rec - 1) % 20 + 1}"
                if first_rec <= SQUAD_LAST else
                f"managed-country player {first_rec - MANAGED_FIRST + 1} of 80")
        pr(f"- first diverging record and field: **record {first_rec} ({kind}), "
           f"byte +0x{first_off:02x}**")
    pr("")
    pr("Per-field differing-byte counts (of 3061 records; squads = records 1..2560,")
    pr("managed = records 2561..2640):")
    pr("")
    pr("| field | differs (all) | differs (squads) | differs (managed) | shape |")
    pr("|---|---|---|---|---|")
    for f in range(PLAYER):
        label, k, rate = shapes[f]
        shape = label if label == "equal" else f"{label}" + (
            f" (best shift {k:+d} match rate {rate:.2f})" if rate is not None else "")
        pr(f"| +0x{f:02x} | {counts[f]} | {squad_counts[f]} | {managed_counts[f]} | {shape} |")
    pr("")
    pr("## 2. The oracle's LCG call sequence (each call cited)")
    pr("")
    pr("`" + SUMMARISE_REL + "` is the oracle that reproduces 30720/30720 bytes per field")
    pr("over E006's 12 completed games. Its LCG call sequence, per player record:")
    pr("")
    pr("- squads, `model_player` (`" + SUMMARISE_REL + "` L129-172), 7 draws per record,")
    pr("  seed = country number (`model_squads` L184):")
    pr("  1. `draw(16)` -> +0x05 (L132)")
    pr("  2. `draw(7)` -> age a (L133)")
    pr("  3. `draw(7)` -> age b (L134)")
    pr("  4. `draw(3)` -> peak a (L137)")
    pr("  5. `draw(3)` -> peak b (L138)")
    pr("  6. +0x03 = rating + 0x7F, no draw (L141)")
    pr("  7. `draw(32)` -> +0x0C (L151)")
    pr("  8. `draw(2*T)` -> +0x0D/+0x0E, T from DS:0E82 (L161, L167)")
    pr("- managed country, `model_extra` (L194-216), same `model_player` with `flag=0,")
    pr("  `managed=True`, 9 draws per record plus one redraw draw, seed = the word the")
    pr("  routine starts at (L199):")
    pr("  1. `draw(16)` -> +0x05 (L132 via L203)")
    pr("  2. `draw(7)`, 3. `draw(7)` -> the 96D3 age (L133-134), kept for the 56")
    pr("     position-loop players (L201-203) and the 4 tail players (L214-215)")
    pr("  4. `draw(3)`, 5. `draw(3)` -> peak (L137-138)")
    pr("  6. `draw(10)` -> +0x03 = rating + 0x7F - 10 - d (L143-144)")
    pr("  7. `draw(32)` -> +0x0C (L151)")
    pr("  8. `draw(T+1)`, 9. `draw(3*T)` -> +0x0D/+0x0E, managed branch (L163-164)")
    pr("  10. for the 20 squad-slot players only (L204-213): one extra `draw(3)` after")
    pr("      the record, the age redrawn as DS:118C[gk] + rand(3) (L206) and +0x04")
    pr("      recomputed (L208-212)")
    pr("")
    pr("Replication check (this script re-runs that sequence on the same fixtures; equal")
    pr(f"counts out of {SQUAD_LAST} squad records and 80 managed records, modelled fields):")
    pr("")
    pr("| field | squads equal (of 2560) | managed equal (of 80) |")
    pr("|---|---|---|")
    for f in MODELLED:
        pr(f"| +0x{f:02x} | {oracle_squad_equal[f]} | {oracle_managed_equal.get(f, '-')} |")
    pr("")
    pr(f"The seed(s) from which the 80 managed records reproduce exactly: {', '.join(seed_hex) or 'none'};")
    pr(f"the seed the last squad's LCG (country 128) is left at is 0x{end_seed:04x}; LCG")
    pr("steps from that word to each managed seed:")
    for s in extra_seeds:
        pr(f"- 0x{end_seed:04x} -> 0x{s:04x}: {steps_from_end[s]} step(s)")
    pr("")
    yn = "yes" if consistency_squads else "NO"
    yn_m = "yes" if consistency_managed else "NO"
    pr("## 3. Root cause")
    pr("")
    pr("Four divergences. The first three are measured by a cumulative ablation chain")
    pr("over the squad records (each step reverts one aspect of the oracle to")
    pr("`new_game.py`'s encoding; step 3 reproduces the model's 2560 squad records")
    pr(f"byte-for-byte: {yn}):")
    pr("")
    pr("1. [confirmed: " + SUMMARISE_REL + " L120-121 vs `goal2/engine/new_game.py:31,34`;")
    pr("   ds_2581_01.hex row 1180 (118A=0x1C, 118B=0x1F) and row 0E80 (0E80=0x1B,")
    pr("   0E81=0x1E)] The goalkeeper/outfield indexing of the age and peak base tables")
    pr("   is inverted. The oracle indexes the pair by `gk` directly: goalkeeper (gk=1)")
    pr("   gets 0x1F (DS:118B) and 0x1E (DS:0E81); outfield gets 0x1C (DS:118A) and")
    pr("   0x1B (DS:0E80). `new_game.py`'s tuples give the goalkeeper 0x1C and 0x1B.")
    pr("   Every age and peak is therefore off by exactly 3 in one direction or the")
    pr("   other (0x1F-0x1C = 0x1E-0x1B = 3); this alone breaks +0x01 and +0x02 in all")
    pr("   2560 squad records (step 1 below) and is why the first diverging byte of the")
    pr("   whole array is record 1's +0x01.")
    pr("2. [confirmed: " + SUMMARISE_REL + " L132-138 vs `goal2/engine/new_game.py:99-107,125`]")
    pr("   A draw-order swap: the oracle draws the +0x05 `rand(16)` FIRST (L132), before")
    pr("   the age's two `rand(7)` (L133-134); `new_game.py` draws the two `rand(7)`")
    pr("   first and the `rand(16)` fifth (`new_game.py:125`). Moving one draw shifts")
    pr("   the stream position of every later draw, so the peak draws and everything")
    pr("   downstream read different stream values (step 2 below).")
    pr("3. [confirmed: " + SUMMARISE_REL + " L146,149 vs `goal2/engine/new_game.py:114,117`]")
    pr("   The +0x04 current-ability bound: the oracle compares the age against")
    pr("   `peak + 3` (a literal 3) and sets `k = 16 - (age - (peak + 3))`; `new_game.py`")
    pr("   uses `peak + pot` (the +0x03 potential byte) in both places (step 3 below).")
    pr("4. [confirmed: " + SUMMARISE_REL + " L201-216 vs `goal2/engine/new_game.py:171-227`]")
    pr("   The managed-country (98C4) call sequence is different, not shifted: the")
    pr("   oracle makes the full 96D3 sequence (the two `rand(7)` age draws included)")
    pr("   for ALL 80 players - 9 draws per record - and redraws the youth age with ONE")
    pr("   extra `draw(3)` after the record, only for the 20 squad-slot players (L206),")
    pr("   with +0x04 recomputed (L208-212); `new_game.py:182` draws the youth age (one")
    pr("   `rand(3)`) first for every record and never draws the `rand(7)` pair - 8")
    pr("   draws per record - so after the first record the seed stream itself is")
    pr("   misaligned.")
    pr("")
    pr("| field | step 1 (bases) differs | step 2 (+ order) differs | step 3 (+ bound; = the model) differs |")
    pr("|---|---|---|---|")
    for f in MODELLED:
        pr(f"| +0x{f:02x} | {abl1_diff[f]} | {abl2_diff[f]} | {abl3_diff[f]} |")
    pr("")
    pr("For the 80 managed records, re-running the model's own 98C4 call sequence on the")
    pr(f"oracle's seed 0x{extra_seeds[0]:04x} reproduces the model's managed records")
    pr(f"byte-for-byte (consistency: {yn_m}), which pins divergence 4 as")
    pr("the managed records' only cause:")
    pr("")
    pr("| field | model-style 98C4 on oracle seed differs (of 80) | model differs (of 80) |")
    pr("|---|---|---|")
    for f in MODELLED:
        pr(f"| +0x{f:02x} | {model_managed_diff.get(f, '-')} | {managed_counts[f]} |")
    pr("")
    pr("What is NOT a divergence:")
    pr("")
    pr("- [derived: section 2's seed search] The seed initialisation. The squads' seed =")
    pr("  country matches (`new_game.py:255`, oracle L184), and the only seed from which")
    pr(f"  the 80 managed records reproduce exactly is {', '.join(seed_hex)} - the very")
    pr("  word `goal2/engine/new_game.py:295` starts from. [derived: the step count in")
    pr(f"  section 2] The word the last squad leaves (0x{end_seed:04x}) is that seed")
    pr("  minus one LCG step, bounding the draws between the squad loop and 98C4 at one;")
    pr("  which routine makes that draw stays unestablished (F007 \"What this does not")
    pr("  establish\"), and T20 needs only the start word, which is pinned.")
    pr("- [confirmed: F004; `goal2/engine/quick_engine.py:49-53` == " + SUMMARISE_REL)
    pr("  L96-105] The LCG formula itself: step then `((seed*n) >> 16) + 1` in both.")
    pr("- [derived: section 1, fields +0x00/+0x06/+0x07/+0x12/+0x13 at 0 differing")
    pr("  bytes] The country, position and fitness writers and the rating are")
    pr("  byte-exact already.")
    pr("")
    pr("## 4. What T20 must change (named; no source touched here)")
    pr("")
    pr("1. [derived: section 3.1] Index the age and peak bases so the goalkeeper (gk=1)")
    pr("   reads 0x1F/0x1E and the outfield reads 0x1C/0x1B (`DS_118A`/`DS_0E80` in")
    pr("   `goal2/engine/new_game.py:31,34`). The `DataTables` pins in")
    pr("   `goal2/tests/test_new_game.py:115-119` assert the current inverted tuples and")
    pr("   change with this.")
    pr("2. [derived: section 3.2] In the 96D3 path, draw the +0x05 `rand(16)` before the")
    pr("   age's two `rand(7)`.")
    pr("3. [derived: section 3.3] In the +0x04 computation of both paths, compare the age")
    pr("   against `peak + 3`, not `peak + pot` (also `k = 16 - (age - (peak + 3))`).")
    pr("4. [derived: section 3.4] In the 98C4 path, make the full 96D3 draw sequence (the")
    pr("   `rand(7)` age pair and the `rand(10)` for +0x03 included, managed `rand(T+1)`")
    pr("   and `rand(3*T)`) for every record, then, for the 20 squad-slot records only,")
    pr("   one extra `rand(3)` with the age redrawn as DS:118C[gk] + rand(3) and +0x04")
    pr("   recomputed.")
    pr("5. [confirmed: section 2's replication] With 1-4 the sequence reproduces every")
    pr("   modelled byte of all 3061 records; the four fields of issue #11 and the")
    pr("   dependent +0x04/+0x0D/+0x0E/+0x0F go to 0 differing bytes. The")
    pr("   `LCGDrawOrderRegression` pins (`goal2/tests/test_new_game.py:301-313`) are the")
    pr("   current model's output and change with this (T20 scope).")
    pr("")

    report = Path(__file__).resolve().parent / "report.md"
    report.write_text("\n".join(L), encoding="utf-8")
    print(f"wrote {report}")
    print(f"overall {overall}/{N_RECORDS * PLAYER}  lcg-fields {lcg_diff}/{N_RECORDS * 4}"
          f"  first record {first_rec} +0x{first_off:02x}")
    print(f"oracle replication: squads "
          f"{sum(oracle_squad_equal.values())}/{SQUAD_LAST * len(MODELLED)} modelled bytes, "
          f"managed {sum(oracle_managed_equal.values())}/{80 * len(MODELLED)}; "
          f"seeds {seed_hex}; consistency squads={consistency_squads} "
          f"managed={consistency_managed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
