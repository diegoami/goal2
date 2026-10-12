# T01 RUN-NOTES

The walking skeleton: the package, the quick-engine seam, one fixture end to end.

## Plan

1. Vendor the three files goal2-archaeology's T24 ships at commit `8760df9`:
   `runtime/model/quick_engine.py`, `runtime/driver/savestate.py`, `runtime/driver/players.py`
   (F012, F001, F002 / F007). All three are byte-identical to the archaeology's
   `git show 8760df9:<path>` (sha256 verified before each `git show` extraction and after).
   [confirmed: each file is `git show 8760df9:<path>`; the sha256s are pinned in
   PROVENANCE.md.]
2. PROVENANCE.md rows for each. [designed: the table's columns are this rebuild's
   format; the source commit is `[confirmed]` per row.]
3. `goal2/__init__.py`, `goal2/cli.py`, `goal2/play.py`: the package and the CLI. The
   vendored `quick_engine.py` does `import players` after a sys.path insert; the
   archaeology layout has `runtime/model/` and `runtime/driver/`, here both files sit in
   `goal2/engine/`, so `cli.py` puts the engine dir on `sys.path` before the import.
   [designed: the package layout, the engine-dir import, and the entry-point shim
   are this rebuild's choices; the vendored engine's import is `[confirmed]`.]
4. `tools/check_provenance.py`: a small parser for PROVENANCE.md's table; exits 0 when
   every file under `goal2/engine/` has a row and every source commit exists in the
   archaeology checkout. [designed: the table parser, the recursive walk, and the
   `git cat-file -e` commit check are this rebuild's; rule 18 is `[confirmed]`.]
5. Tests: [designed: the test layout, the E010 release download, and the test
   mechanics are this rebuild's choices.]
   - `goal2/tests/test_imports.py` — the engine imports; exposes `simulate`, `Savestate`,
     `FoulPathNotModelled`, `ExtraTimeNotModelled`. [confirmed: the names come from
     the vendored modules at 8760df9.]
   - `goal2/tests/test_savestate.py` — the vendored savestate reader: zip format, BDA
     fields at the right offsets, out-of-range reads raise. [confirmed: the layout
     constants are F001's calibration on DOSBox-X 2024.03.01.]
   - `goal2/tests/test_cli.py` — the CLI's error and refusal paths (mocks the engine's
     `simulate` to raise each refusal exception; the CLI returns 3). [designed: the
     error/refusal contract is this rebuild's; the engine's exceptions are
     `[confirmed]`.]
   - `goal2/tests/test_fidelity.py` — the seam reproduces E010-r0001 seed-exactly:
     downloads the published half-time state from `gh release download E010` into
     `.cache/e010-r0001-halftime.sav`, then asserts score, goals, and seed words equal
     the run record. [confirmed: the expected values are the E010-r0001 run record's
     observations step 50; the comparison is the same shape `check_model.py` uses.]

## Progress

| Commit | What |
| --- | --- |
| `e961c8f` | T01 implementation: package, vendored engine, CLI, fidelity test, provenance check |
| (this commit) | T01 rework 1: fix R1–R5 from sol-6.1's review |

The worktree is at `~/projects/goal2-work/skeleton`, on branch `task/T01-skeleton`.

## Done-when verification

DW1: `python3 -m unittest discover -s goal2/tests -t .` is green (20 tests):
  - 3 engine-imports tests
  - 4 savestate reader tests
  - 6 CLI tests (errors, refusal x2, output format x2, entry point x2)
  - 2 fidelity tests (E010-r0001 reproduce + CLI prints; full goal sequence and full output)
  - 4 provenance tests (well-known, nested unlisted, same-basename, row-orphaned)
  - 1 init test (empty init for the tests package)
  - Plus the existing harness test in `tests/test_agent_permissions.py` (5 tests).

DW2: `python3 -m goal2.play .cache/e010-r0001-halftime.sav` prints:
  ```
  score: 1-0
  goals (team, minute, player):
    team 0, minute 85, player 538
  seed DS:7B62: 0x63d7
  seed DS:8336: 0x51a8
  ```
  The values are the E010-r0001 run record's (runs/E010/E010-r0001.json, observation
  step 50: full-time score 1 0, scorer 538 at minute 85, seed DS:7B62 0x63d7, seed
  DS:8336 0x51a8). The entry point also propagates non-zero exits (DW2 misses this:
  `python3 -m goal2.play /no/such/path.sav` exits 2, not 0 — R4 fix).

DW3:
  - `python3 tools/check_provenance.py` exits 0: "provenance check: 3 file(s) OK".
    The check now walks `goal2/engine/` recursively (R1), matches rows by repo-relative
    path (R2), and excludes `__pycache__/` and `*.pyc` (Python's compile cache). The
    regression tests in `goal2/tests/test_provenance.py` exercise the bypasses R1/R2
    covered.
  - Every behaviour claim in a new non-vendored file carries an evidence tag (R5):
    `goal2/__init__.py` `[designed]`, `goal2/cli.py` `[designed]` x3, `[confirmed]` x2,
    `goal2/play.py` `[designed]`, `tools/check_provenance.py` `[designed]` x2,
    `goal2/tests/test_fidelity.py` `[confirmed]` x2, `goal2/tests/test_cli.py`
    `[designed]` x4, `goal2/tests/test_savestate.py` `[confirmed]` x2,
    `goal2/tests/test_imports.py` `[confirmed]` x3, `[designed]` x1,
    `goal2/tests/test_provenance.py` `[confirmed]` x1.

## Fail-before (CLAUDE.md rule 21)

A test that has never failed proves nothing. The fidelity test would fail before the
seam wiring in three independent ways, each of which I verified during the build:

1. **No vendored engine.** Before writing `goal2/cli.py`, an `import` of `goal2.cli`
   raised `ModuleNotFoundError: No module named 'engine'`. The import-only test
   (`test_imports.py`) fails with the same error.
2. **No CLI wrapper.** Without `goal2/play.py`, `python -m goal2.play` fails with
   `No module named goal2.play`. The fidelity test's `test_cli_prints_e010_r0001_outcome`
   fails for the same reason.
3. **No state.** Without `.cache/e010-r0001-halftime.sav`, the test's `setUpClass`
   tries to `gh release download` it; on a clean machine (no `gh` login) it skips with
   the reason "E010-r0001 halftime state not in ... and could not be downloaded". The
   test is therefore a *positive* test only when both the engine and the state are
   in place; the run from a fresh checkout (no state) skips with the reason — never
   a silent pass.

The CLI's output format was also chosen to match `check_model.py` (line 92 of the
archaeology's `experiments/E010-q010-quick-engine/check_model.py`): score, goals
per team, both seed words.

## Hazards and how I addressed them

- **Never commit a savestate (rule 19).** `.cache/` is in `.gitignore`; the test
  downloads the state on demand.
- **Never edit a vendored file (rule 18).** The three vendored files are byte-identical
  to `git show 8760df9:<path>` (sha256 d79c63... / ed0e1c... / 1e0d671... match the
  archaeology's tree); PROVENANCE.md records the source commit.
- **Determinism.** No `time`, no `random`, no environment-dependent I/O outside the
  download step. The model itself is deterministic from its input state.
- **A fidelity test that has never failed proves nothing (rule 20).** See the
  fail-before section above.

## END block

T01 rework 1 complete. The reviewer (sol-6.1) flagged 5 blocking findings; each is
addressed in a commit on this branch with a regression test (or, for R3, the existing
test tightened to a full comparison). The branch head is ready for the round-2 review.

## Rework 1 — sol-6.1's findings and their fixes

| Finding | File:line | What | Fix |
| --- | --- | --- | --- |
| R1 (blocking) | `tools/check_provenance.py:103` | `ENGINE.iterdir()` checked only direct children; a vendored file under a subdirectory passed without a row. | Switched to `ENGINE.rglob("*")` and skipped `__pycache__` and `*.pyc` (Python's compile cache, not vendored). |
| R2 (blocking) | `tools/check_provenance.py:97–119` | Rows were matched by basename, so a row for `other/quick_engine.py` could cover `goal2/engine/quick_engine.py`. | Matched by repo-relative path under `goal2/engine/`, with `_normalize` for cross-platform paths. Same-basename collisions are now distinguishable. |
| R3 (blocking) | `goal2/tests/test_fidelity.py:77–95` | The model assertion filtered team-1 goals; the CLI assertion used `assertIn` on substrings. An extra team-1 goal would not fail either test. | The model assertion now compares the full goal sequence (both teams, in engine order); the CLI assertion compares the full output (a single `assertEqual` against the exact text). |
| R4 (blocking) | `goal2/play.py:9–10` | `main()`'s return value was discarded, so `python -m goal2.play /no/such/path.sav` exited 0 instead of 2. | `play.py` now does `sys.exit(main())`. New entry-point tests in `test_cli.py` assert the exit code for both the file-error and the engine-refusal paths. |
| R5 (blocking) | `goal2/tests/test_imports.py:1`, `goal2/cli.py:1–5`, `RUN-NOTES.md:16–29` (prior version) | Several behaviour claims in new non-vendored files had no evidence tag. | Added tags to every claim in `test_imports.py`, `cli.py`, `test_savestate.py`'s `test_video_mode_and_ticks`, and `test_cli.py`'s `CliEntryPoint`. The "Blocking means" item in the brief now lists rule 17. |

The rework is the same branch, the same worktree, the same PR. The next step is the
round-2 review.
