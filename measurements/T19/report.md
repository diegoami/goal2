# T19 — the LCG draw-order divergence of `goal2.engine.new_game` against E006-r0001

Written by `measurements/T19/divergence.py`; re-running it rewrites this file with
the same numbers. Fixtures (git-ignored, rule 19):

- GOAL.DAT sha256 `bc5e5c04434d31f350eb7803afc3810333393e049d50dde559797a5b068c60ca`
- E006-r0001 main-screen savestate sha256 `e0afff6751747233f6ab8b9ba73dab0790b7509f15257ed7ae24f528b935657d`
- oracle: `experiments/E006-q004-skills/summarise.py` in the goal2-archaeology checkout (found at
  `/home/diego/projects/goal2-archaeology/experiments/E006-q004-skills/summarise.py`, commit `3d82ead8010d5bb02f14912535dde062cce4d518`), cited below by line as
  `experiments/E006-q004-skills/summarise.py:L<n>`
- managed country: 7 (E006-r0001, [confirmed: F007])

## 1. The four numbers

- overall differing bytes: **11002 of 61220** (3061 records x 0x14 bytes)
- LCG-field differing bytes (+0x01/+0x02/+0x05/+0x0C): **7510 of 12244** (3061 records x 4 fields)
- first diverging record and field: **record 1 (squad player of country 1, slot 1), byte +0x01**

Per-field differing-byte counts (of 3061 records; squads = records 1..2560,
managed = records 2561..2640):

| field | differs (all) | differs (squads) | differs (managed) | shape |
|---|---|---|---|---|
| +0x00 | 0 | 0 | 0 | equal |
| +0x01 | 2479 | 2408 | 71 | scattered (best shift +2 match rate 0.08) |
| +0x02 | 2462 | 2386 | 76 | scattered (best shift -2 match rate 0.08) |
| +0x03 | 75 | 0 | 75 | scattered (best shift -20 match rate 0.13) |
| +0x04 | 1330 | 1250 | 80 | scattered (best shift -1 match rate 0.40) |
| +0x05 | 2490 | 2415 | 75 | scattered (best shift -1 match rate 0.07) |
| +0x06 | 0 | 0 | 0 | equal |
| +0x07 | 0 | 0 | 0 | equal |
| +0x08 | 0 | 0 | 0 | equal |
| +0x09 | 0 | 0 | 0 | equal |
| +0x0a | 0 | 0 | 0 | equal |
| +0x0b | 0 | 0 | 0 | equal |
| +0x0c | 79 | 0 | 79 | scattered (best shift -2 match rate 0.06) |
| +0x0d | 556 | 497 | 59 | scattered (best shift -20 match rate 0.15) |
| +0x0e | 556 | 497 | 59 | scattered (best shift -20 match rate 0.15) |
| +0x0f | 975 | 948 | 27 | scattered (best shift -20 match rate 0.36) |
| +0x10 | 0 | 0 | 0 | equal |
| +0x11 | 0 | 0 | 0 | equal |
| +0x12 | 0 | 0 | 0 | equal |
| +0x13 | 0 | 0 | 0 | equal |

## 2. The oracle's LCG call sequence (each call cited)

`experiments/E006-q004-skills/summarise.py` is the oracle that reproduces 30720/30720 bytes per field
over E006's 12 completed games. Its LCG call sequence, per player record:

- squads, `model_player` (`experiments/E006-q004-skills/summarise.py` L129-172), 7 draws per record,
  seed = country number (`model_squads` L184):
  1. `draw(16)` -> +0x05 (L132)
  2. `draw(7)` -> age a (L133)
  3. `draw(7)` -> age b (L134)
  4. `draw(3)` -> peak a (L137)
  5. `draw(3)` -> peak b (L138)
  6. +0x03 = rating + 0x7F, no draw (L141)
  7. `draw(32)` -> +0x0C (L151)
  8. `draw(2*T)` -> +0x0D/+0x0E, T from DS:0E82 (L161, L167)
- managed country, `model_extra` (L194-216), same `model_player` with `flag=0,
  `managed=True`, 9 draws per record plus one redraw draw, seed = the word the
  routine starts at (L199):
  1. `draw(16)` -> +0x05 (L132 via L203)
  2. `draw(7)`, 3. `draw(7)` -> the 96D3 age (L133-134), kept for the 56
     position-loop players (L201-203) and the 4 tail players (L214-215)
  4. `draw(3)`, 5. `draw(3)` -> peak (L137-138)
  6. `draw(10)` -> +0x03 = rating + 0x7F - 10 - d (L143-144)
  7. `draw(32)` -> +0x0C (L151)
  8. `draw(T+1)`, 9. `draw(3*T)` -> +0x0D/+0x0E, managed branch (L163-164)
  10. for the 20 squad-slot players only (L204-213): one extra `draw(3)` after
      the record, the age redrawn as DS:118C[gk] + rand(3) (L206) and +0x04
      recomputed (L208-212)

Replication check (this script re-runs that sequence on the same fixtures; equal
counts out of 2560 squad records and 80 managed records, modelled fields):

| field | squads equal (of 2560) | managed equal (of 80) |
|---|---|---|
| +0x00 | 2560 | 80 |
| +0x01 | 2560 | 80 |
| +0x02 | 2560 | 80 |
| +0x03 | 2560 | 80 |
| +0x04 | 2560 | 80 |
| +0x05 | 2560 | 80 |
| +0x06 | 2560 | 80 |
| +0x07 | 2560 | 80 |
| +0x0c | 2560 | 80 |
| +0x0d | 2560 | 80 |
| +0x0e | 2560 | 80 |
| +0x0f | 2560 | 80 |
| +0x12 | 2560 | 80 |
| +0x13 | 2560 | 80 |

The seed(s) from which the 80 managed records reproduce exactly: 0xf5db;
the seed the last squad's LCG (country 128) is left at is 0x18bc; LCG
steps from that word to each managed seed:
- 0x18bc -> 0xf5db: 1 step(s)

## 3. Root cause

Four divergences. The first three are measured by a cumulative ablation chain
over the squad records (each step reverts one aspect of the oracle to
`new_game.py`'s encoding; step 3 reproduces the model's 2560 squad records
byte-for-byte: yes):

1. [confirmed: experiments/E006-q004-skills/summarise.py L120-121 vs `goal2/engine/new_game.py:31,34`;
   ds_2581_01.hex row 1180 (118A=0x1C, 118B=0x1F) and row 0E80 (0E80=0x1B,
   0E81=0x1E)] The goalkeeper/outfield indexing of the age and peak base tables
   is inverted. The oracle indexes the pair by `gk` directly: goalkeeper (gk=1)
   gets 0x1F (DS:118B) and 0x1E (DS:0E81); outfield gets 0x1C (DS:118A) and
   0x1B (DS:0E80). `new_game.py`'s tuples give the goalkeeper 0x1C and 0x1B.
   Every age and peak is therefore off by exactly 3 in one direction or the
   other (0x1F-0x1C = 0x1E-0x1B = 3); this alone breaks +0x01 and +0x02 in all
   2560 squad records (step 1 below) and is why the first diverging byte of the
   whole array is record 1's +0x01.
2. [confirmed: experiments/E006-q004-skills/summarise.py L132-138 vs `goal2/engine/new_game.py:99-107,125`]
   A draw-order swap: the oracle draws the +0x05 `rand(16)` FIRST (L132), before
   the age's two `rand(7)` (L133-134); `new_game.py` draws the two `rand(7)`
   first and the `rand(16)` fifth (`new_game.py:125`). Moving one draw shifts
   the stream position of every later draw, so the peak draws and everything
   downstream read different stream values (step 2 below).
3. [confirmed: experiments/E006-q004-skills/summarise.py L146,149 vs `goal2/engine/new_game.py:114,117`]
   The +0x04 current-ability bound: the oracle compares the age against
   `peak + 3` (a literal 3) and sets `k = 16 - (age - (peak + 3))`; `new_game.py`
   uses `peak + pot` (the +0x03 potential byte) in both places (step 3 below).
4. [confirmed: experiments/E006-q004-skills/summarise.py L201-216 vs `goal2/engine/new_game.py:171-227`]
   The managed-country (98C4) call sequence is different, not shifted: the
   oracle makes the full 96D3 sequence (the two `rand(7)` age draws included)
   for ALL 80 players - 9 draws per record - and redraws the youth age with ONE
   extra `draw(3)` after the record, only for the 20 squad-slot players (L206),
   with +0x04 recomputed (L208-212); `new_game.py:182` draws the youth age (one
   `rand(3)`) first for every record and never draws the `rand(7)` pair - 8
   draws per record - so after the first record the seed stream itself is
   misaligned.

| field | step 1 (bases) differs | step 2 (+ order) differs | step 3 (+ bound; = the model) differs |
|---|---|---|---|
| +0x00 | 0 | 0 | 0 |
| +0x01 | 2560 | 2408 | 2408 |
| +0x02 | 2560 | 2386 | 2386 |
| +0x03 | 0 | 0 | 0 |
| +0x04 | 0 | 1456 | 1250 |
| +0x05 | 0 | 2415 | 2415 |
| +0x06 | 0 | 0 | 0 |
| +0x07 | 0 | 0 | 0 |
| +0x0c | 0 | 0 | 0 |
| +0x0d | 0 | 497 | 497 |
| +0x0e | 0 | 497 | 497 |
| +0x0f | 0 | 948 | 948 |
| +0x12 | 0 | 0 | 0 |
| +0x13 | 0 | 0 | 0 |

For the 80 managed records, re-running the model's own 98C4 call sequence on the
oracle's seed 0xf5db reproduces the model's managed records
byte-for-byte (consistency: yes), which pins divergence 4 as
the managed records' only cause:

| field | model-style 98C4 on oracle seed differs (of 80) | model differs (of 80) |
|---|---|---|
| +0x00 | 0 | 0 |
| +0x01 | 71 | 71 |
| +0x02 | 76 | 76 |
| +0x03 | 75 | 75 |
| +0x04 | 80 | 80 |
| +0x05 | 75 | 75 |
| +0x06 | 0 | 0 |
| +0x07 | 0 | 0 |
| +0x0c | 79 | 79 |
| +0x0d | 59 | 59 |
| +0x0e | 59 | 59 |
| +0x0f | 27 | 27 |
| +0x12 | 0 | 0 |
| +0x13 | 0 | 0 |

What is NOT a divergence:

- [derived: section 2's seed search] The seed initialisation. The squads' seed =
  country matches (`new_game.py:255`, oracle L184), and the only seed from which
  the 80 managed records reproduce exactly is 0xf5db - the very
  word `goal2/engine/new_game.py:295` starts from. [derived: the step count in
  section 2] The word the last squad leaves (0x18bc) is that seed
  minus one LCG step, bounding the draws between the squad loop and 98C4 at one;
  which routine makes that draw stays unestablished (F007 "What this does not
  establish"), and T20 needs only the start word, which is pinned.
- [confirmed: F004; `goal2/engine/quick_engine.py:49-53` == experiments/E006-q004-skills/summarise.py
  L96-105] The LCG formula itself: step then `((seed*n) >> 16) + 1` in both.
- [derived: section 1, fields +0x00/+0x06/+0x07/+0x12/+0x13 at 0 differing
  bytes] The country, position and fitness writers and the rating are
  byte-exact already.

## 4. What T20 must change (named; no source touched here)

1. [derived: section 3.1] Index the age and peak bases so the goalkeeper (gk=1)
   reads 0x1F/0x1E and the outfield reads 0x1C/0x1B (`DS_118A`/`DS_0E80` in
   `goal2/engine/new_game.py:31,34`). The `DataTables` pins in
   `goal2/tests/test_new_game.py:115-119` assert the current inverted tuples and
   change with this.
2. [derived: section 3.2] In the 96D3 path, draw the +0x05 `rand(16)` before the
   age's two `rand(7)`.
3. [derived: section 3.3] In the +0x04 computation of both paths, compare the age
   against `peak + 3`, not `peak + pot` (also `k = 16 - (age - (peak + 3))`).
4. [derived: section 3.4] In the 98C4 path, make the full 96D3 draw sequence (the
   `rand(7)` age pair and the `rand(10)` for +0x03 included, managed `rand(T+1)`
   and `rand(3*T)`) for every record, then, for the 20 squad-slot records only,
   one extra `rand(3)` with the age redrawn as DS:118C[gk] + rand(3) and +0x04
   recomputed.
5. [confirmed: section 2's replication] With 1-4 the sequence reproduces every
   modelled byte of all 3061 records; the four fields of issue #11 and the
   dependent +0x04/+0x0D/+0x0E/+0x0F go to 0 differing bytes. The
   `LCGDrawOrderRegression` pins (`goal2/tests/test_new_game.py:301-313`) are the
   current model's output and change with this (T20 scope).
