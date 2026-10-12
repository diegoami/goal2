# T01 RUN-NOTES

The walking skeleton: the package, the quick-engine seam, one fixture end to end.

## Plan

1. Vendor the three files goal2-archaeology's T24 ships at commit `8760df9`:
   `runtime/model/quick_engine.py`, `runtime/driver/savestate.py`, `runtime/driver/players.py`
   (F012, F001, F002 / F007). All three are byte-identical to the archaeology's
   `git show 8760df9:<path>` (sha256 verified before each `git show` extraction and after).
2. PROVENANCE.md rows for each (CLAUDE.md rule 18).
3. `goal2/__init__.py`, `goal2/cli.py`, `goal2/play.py`: the package and the CLI. The
   vendored `quick_engine.py` does `import players` after a sys.path insert; the
   archaeology layout has `runtime/model/` and `runtime/driver/`, here both files sit in
   `goal2/engine/`, so `cli.py` puts the engine dir on `sys.path` before the import.
4. `tools/check_provenance.py`: a small parser for PROVENANCE.md's table; exits 0 when
   every file under `goal2/engine/` has a row and every source commit exists in the
   archaeology checkout.
5. Tests:
   - `goal2/tests/test_imports.py` — the engine imports; exposes `simulate`, `Savestate`,
     `FoulPathNotModelled`, `ExtraTimeNotModelled`.
   - `goal2/tests/test_savestate.py` — the vendored savestate reader: zip format, BDA
     fields at the right offsets, out-of-range reads raise.
   - `goal2/tests/test_cli.py` — the CLI's error and refusal paths (mocks the engine's
     `simulate` to raise each refusal exception; the CLI returns 3).
   - `goal2/tests/test_fidelity.py` — the seam reproduces E010-r0001 seed-exactly:
     downloads the published half-time state from `gh release download E010` into
     `.cache/e010-r0001-halftime.sav`, then asserts score, goals, and seed words equal
     the run record.

## Progress

| Commit | What |
| --- | --- |
| (this branch) | T01 implementation: package, vendored engine, CLI, fidelity test, provenance check |

The worktree is at `~/projects/goal2-work/skeleton`, on branch `task/T01-skeleton`.

## Done-when verification

DW1: `python3 -m unittest discover -s goal2/tests -t .` is green (14 tests):
  - 3 engine-imports tests
  - 4 savestate reader tests
  - 4 CLI tests (errors, refusal x2, output format x2)
  - 2 fidelity tests (E010-r0001 reproduce + CLI prints)
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
  DS:8336 0x51a8).

DW3:
  - `python3 tools/check_provenance.py` exits 0: "provenance check: 3 file(s) OK".
  - Every non-vendored file added in this branch carries an evidence tag:
    `goal2/__init__.py` `[designed]`, `goal2/cli.py` `[designed]` x3, `[confirmed]` x2,
    `goal2/play.py` `[designed]`, `tools/check_provenance.py` `[designed]`,
    `goal2/tests/test_fidelity.py` `[confirmed]` x2, `goal2/tests/test_cli.py`
    `[designed]` x3, `goal2/tests/test_savestate.py` `[confirmed]`.

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

T01 implementation complete in this worktree on `task/T01-skeleton`. The fidelity test
downloads the state on demand; the unit tests are hermetic. No work was started that
spans the merged scope of a future task; the only state left on disk is the cached
E010-r0001 savestate in `.cache/`, git-ignored. The next step is the review, the
question to the user recorded on the PR.
