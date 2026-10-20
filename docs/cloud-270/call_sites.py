#!/usr/bin/env python3
"""[designed: T86 rework 2] Per-call-site guard sweep: every site is classified, none silently.

Usage (repository root): python3 docs/cloud-270/call_sites.py [--markdown]

Every line in the swept files is a site if it contains a raise or a guard call
(`_require_owner`, `_check_*`, `require_scenario`, `require_available`,
`validate_result`, `validate_resolution`, `validate_halftime`, `swap`). Each site
must match exactly one SITES entry, keyed by file, a text fragment of the line (or,
prefixed with '=', the whole line) and its occurrence among that file's sites carrying it. The entry is one of:
  M  the mutations.py entry that removes this site alone (its control must fail);
  C  covered by another site's named mutation/control, with the reason this site adds no outcome;
  N  not a guard this slice claims, with the reason and the existing owner.
The script exits 1 when a site is unclassified or an entry names no site or no mutation.
"""
import importlib.util
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCENARIO = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'goal2/scenario').glob('*.py'))
REAL = ['goal2/desktop/jobs.py', 'goal2/game/watched_jobs.py', 'goal2/desktop/watched.py',
        'goal2/desktop/competitive.py', 'goal2/game/watched_publication.py', 'goal2/desktop/match_view.py']
PATTERN = re.compile(r'\braise\b|\b_require_owner\(|\b_check_\w+\(|\brequire_scenario\(|\brequire_available\(|'
                     r'\bvalidate_result\(|\bvalidate_resolution\(|\bvalidate_halftime\(|\bswap\(')
RERAISE = 'N', 'bare re-raise after cleanup; the cleanup is the claimed part where listed'
T65 = 'N', 'existing T65 journal bound/shape guard; owned by test_watched_jobs, not claimed by T86'
T82 = 'N', 'existing T82/T83 pitch budget/shape guard; owned by test_watched_pitch_jobs/prove_watched_pitch_jobs'
T66 = 'N', 'existing T66 presentation guard; owned by test_pygame_match_view, not claimed by T86'
WIN = 'N', 'existing #236/#254 Windows status/cleanup handling; owned by test_desktop_watched_sharing'
T64 = 'N', 'T64 original candidate builder; replaced on the scenario path by runtime._completed (owned by test_watched_publication)'
GATE = 'N', 'original optional-runtime gate; the scenario runtime supplies require_* instead (default path unchanged)'

# (file, fragment, occurrence) -> classification
SITES = {
    ('goal2/scenario/__init__.py', 'not a fictional scenario game', 0): ('M', 'require_scenario raises for unmarked values'),
    ('goal2/scenario/__main__.py', 'raise SystemExit(main())', 0): ('N', 'command-line entry point'),
    ('goal2/scenario/factory.py', 'expected next fixture', 0): ('M', 'calendar completes only the next fixture'),
    ('goal2/scenario/factory.py', 'competitive completion needs its resolution', 0): ('M', 'competitive completion needs its resolution'),
    ('goal2/scenario/factory.py', 'validate_resolution(resolution, score', 0): ('M', 'competitive resolution validated'),
    ('goal2/scenario/factory.py', 'friendly completion cannot have', 0): ('M', 'friendly completion has no resolution'),
    ('goal2/scenario/factory.py', "'not a fictional scenario state'", 0): ('M', 'scenario encoder refuses an unmarked state'),
    ('goal2/scenario/factory.py', "'not a fictional scenario state'", 1): ('M', 'decoder refuses an unmarked state'),
    ('goal2/scenario/factory.py', 'invalid fictional player records', 0): ('M', 'decoder refuses malformed records'),
    ('goal2/scenario/factory.py', 'template bytes required', 0): ('M', 'encoder requires template bytes'),
    ('goal2/scenario/factory.py', 'not a fictional scenario file: {exc}', 0): ('M', 'decoder names unreadable files'),
    ('goal2/scenario/factory.py', "'not a fictional scenario file')", 0): ('M', 'scenario codec refuses an unmarked file'),
    ('goal2/scenario/model.py', "require_scenario(state, 'Fictional view')", 0): ('M', 'scenario view refuses an unmarked state'),
    ('goal2/scenario/model.py', 'Invalid managed country or squad', 0): ('M', 'view refuses a malformed squad'),
    ('goal2/scenario/model.py', 'Invalid player record', 0): ('M', 'view refuses a malformed record'),
    ('goal2/scenario/model.py', 'No fictional card', 0): ('M', 'card only for own players'),
    ('goal2/scenario/model.py', 'Choose eleven distinct', 0): ('M', 'confirm needs eleven distinct squad players'),
    ('goal2/scenario/model.py', 'Captain must be', 0): ('M', 'confirm needs the captain in the eleven'),
    ('goal2/scenario/model.py', 'eight-bit', 0): ('M', 'confirm needs eight-bit tactics'),
    ('goal2/scenario/model.py', 'require_available(self.state.players, eleven)', 0): ('M', 'confirm refuses unavailable starters'),
    ('goal2/scenario/model.py', 'invalid pool search', 0): ('M', 'pool refuses an invalid query'),
    ('goal2/scenario/model.py', 'Exchange window is closed', 0): ('M', 'exchange only in a friendly window'),
    ('goal2/scenario/model.py', 'Choose one squad player', 0): ('M', 'exchange needs a squad player and a reserve'),
    ('goal2/scenario/model.py', 'Invalid fictional match result', 0): ('M', 'scenario result text refuses a non-fictional result'),
    ('goal2/scenario/model.py', 'Saving refused', 0): ('M', 'scenario model refuses to save'),
    ('goal2/scenario/model.py', 'Resume refused', 0): ('M', 'scenario model refuses to resume'),
    ('goal2/scenario/runtime.py', 'require_scenario(owner, action)', 0): ('M', 'owner check refuses an unmarked state'),
    ('goal2/scenario/runtime.py', 'foreign template', 0): ('M', 'publication refuses a foreign template'),
    ('goal2/scenario/runtime.py', 'completed watched outcome required', 0): ('M', 'completion must be an outcome'),
    ('goal2/scenario/runtime.py', 'validate_result(result', 0): ('M', 'scenario publication runs validate_result'),
    ('goal2/scenario/runtime.py', 'differs from the pending fixture or is incomplete', 0): ('M', 'completion bound to the pending fixture'),
    ('goal2/scenario/runtime.py', 'completed kind differs', 0): ('M', 'competitive kind bound to the job'),
    ('goal2/scenario/runtime.py', 'declared input image', 0): ('M', 'completion bound to its declared input'),
    ('goal2/scenario/runtime.py', "is not scenario data') from exc", 0): ('M', 'completion memory must be scenario JSON'),
    ('goal2/scenario/runtime.py', 'differs from its result', 0): ('M', 'completion memory must carry the fiction mark'),
    ('goal2/scenario/runtime.py', "_require_owner(owner, 'Fictional publication')", 0): ('M', 'scenario publication refuses an unmarked owner'),
    ('goal2/scenario/runtime.py', 'a watched job is already pending', 0): ('M', 'one pending scenario job'),
    ('goal2/scenario/runtime.py', "_require_owner(self.owner, 'Fictional publication')", 0): ('M', 'begin rechecks the owner'),
    ('goal2/scenario/runtime.py', 'fictional job differs from the scheduled fixture', 0): ('M', 'job bound to the scheduled fixture'),
    ('goal2/scenario/runtime.py', 'already preparing', 0): ('M', 'one scenario preparation'),
    ('goal2/scenario/runtime.py', 'self._check_owner(pending)', 0): ('M', 'owner check before preparation'),
    ('goal2/scenario/runtime.py', '=raise', 0): ('M', 'stale preparation invalidates the token'),
    ('goal2/scenario/runtime.py', "require_scenario(state, 'Fictional quick match')", 0): ('M', 'quick check refuses an unmarked state'),
    ('goal2/scenario/runtime.py', 'Fictional quick match refused: foreign template', 0): ('M', 'quick check refuses a foreign template'),
    ('goal2/scenario/runtime.py', 'Quick supports scheduled friendlies only', 0): ('M', 'quick only for a scheduled friendly'),
    ('goal2/scenario/runtime.py', 'require_available(state.players', 0): ('M', 'quick check refuses unavailable starters'),
    ('goal2/scenario/runtime.py', "=raise ValueError('fictional completion memory is not scenario data')", 0): ('M', 'completion board requires scenario memory'),
    ('goal2/scenario/scripts.py', 'unknown fictional script', 0): ('M', 'unknown script refused'),
    ('goal2/scenario/scripts.py', 'quick friendly cannot play extra time', 0): ('M', 'quick friendly refuses extra time'),
    ('goal2/scenario/scripts.py', "'fictional friendly cannot play extra time'", 0): ('M', 'watched friendly refuses extra time'),
    ('goal2/scenario/walkthrough.py', 'expected a refusal', 0): ('N', 'walkthrough self-check; a missing refusal fails test_scenario_walkthrough'),
    ('goal2/scenario/walkthrough.py', 'exceeded its deadline', 0): ('N', 'walkthrough self-check (deadline)'),
    ('goal2/scenario/worker.py', 'swap(packet', 0): ('N', "fake child's own re-validation; the claimed site is QuickJobs.substitute's swap"),
    ('goal2/scenario/worker.py', 'unknown {role} fault', 0): ('N', 'fake child argument check'),
    ('goal2/scenario/worker.py', 'unknown role', 0): ('N', 'fake child argument check'),
    # Inherited real paths named in seam.md.
    ('goal2/desktop/jobs.py', 'A match is already running', 0): ('M', 'one quick job at a time'),
    ('goal2/desktop/jobs.py', 'Worker cleanup is pending', 0): ('N', '#233 cleanup retry; owned by test_desktop_quick_jobs'),
    ('goal2/desktop/jobs.py', 'Halftime interaction requires a campaign', 0): ('N', 'T47 guard; every scenario state has a calendar, owned by test_desktop_quick_jobs'),
    ('goal2/desktop/jobs.py', 'self._release();raise', 0): RERAISE,
    ('goal2/desktop/jobs.py', 'self.validate_halftime(packet)', 0): ('M', 'halftime preview is validated'),
    ('goal2/desktop/jobs.py', 'Invalid halftime preview', 0): ('M', 'invalid preview cancels the job'),
    ('goal2/desktop/jobs.py', 'Friendly worker failed', 0): ('M', 'quick non-zero exit fails'),
    ('goal2/desktop/jobs.py', 'Friendly completion is stale', 0): ('M', 'quick stale completion'),
    ('goal2/desktop/jobs.py', 'Invalid friendly worker continuation', 0): ('M', 'quick output bound to its template'),
    ('goal2/desktop/jobs.py', 'missing preview fields', 0): ('M', 'preview has exactly the known fields'),
    ('goal2/desktop/jobs.py', 'invalid preview values', 0): ('M', 'preview values are integer lists'),
    ('goal2/desktop/jobs.py', 'preview differs from the pending game', 0): ('M', 'preview matches the pending game'),
    ('goal2/desktop/jobs.py', 'preview fixture changed', 0): ('M', 'halftime preview bound to the fixture'),
    ('goal2/desktop/jobs.py', 'No pending halftime decision', 0): ('M', 'substitution needs a pending decision'),
    ('goal2/desktop/jobs.py', 'swap(self.halftime', 0): ('M', 'substitution validated by swap'),
    ('goal2/desktop/jobs.py', 'already used or is unavailable', 0): ('M', 'halftime continuation used once'),
    ('goal2/desktop/jobs.py', 'Halftime continuation is stale', 0): ('M', 'halftime continuation stale'),
    ('goal2/desktop/jobs.py', "winerror',None)!=32", 0): WIN,
    ('goal2/desktop/jobs.py', 'time.monotonic()>=deadline:raise', 0): WIN,
    ('goal2/game/watched_jobs.py', 'watched IPC packet exceeds limit', 0): T65,
    ('goal2/game/watched_jobs.py', 'invalid watched event shape', 0): T65,
    ('goal2/game/watched_jobs.py', 'invalid or oversized watched memory', 0): T65,
    ('goal2/game/watched_jobs.py', 'raise self._error', 0): ('N', '#254 input preparation error propagation; owned by test_watched_jobs'),
    ('goal2/game/watched_jobs.py', 'TimeoutExpired(self.args', 0): ('N', '#254 bounded wait; owned by test_watched_jobs'),
    ('goal2/game/watched_jobs.py', 'already has a watched bridge', 0): ('N', 'T65 one bridge per owner; owned by test_watched_jobs'),
    ('goal2/game/watched_jobs.py', 'frames must be boolean', 0): ('N', 'argument type check; owned by test_watched_pitch_jobs'),
    ('goal2/game/watched_jobs.py', 'watched bridge is closed or a match is already running', 0): ('M', 'one watched job at a time'),
    ('goal2/game/watched_jobs.py', 'Another match is already pending', 0): ('M', 'pitch job refuses while a match is pending'),
    ('goal2/game/watched_jobs.py', '=raise', 0): RERAISE,
    ('goal2/game/watched_jobs.py', 'stale or consumed watched job token', 0): ('M', '_check_token raises'),
    ('goal2/game/watched_jobs.py', 'self._check_token(token)', 0): ('M', 'poll checks its token'),
    ('goal2/game/watched_jobs.py', "watched job is stale; active game changed", 0): ('M', 'watched stale owner'),
    ('goal2/game/watched_jobs.py', 'watched IPC packet exceeds limit', 1): T65,
    ('goal2/game/watched_jobs.py', 'identity/order differs', 0): ('M', 'journal token'),
    ('goal2/game/watched_jobs.py', 'differs from live event stream', 0): ('M', 'completion events equal the streamed events'),
    ('goal2/game/watched_jobs.py', 'Watched worker failed', 0): ('M', 'error packet is named as the worker failure'),
    ('goal2/game/watched_jobs.py', 'invalid watched IPC record', 0): ('M', 'unknown journal kind refused'),
    ('goal2/game/watched_jobs.py', 'without completion', 0): ('M', 'watched exit without completion fails'),
    ('goal2/game/watched_jobs.py', 'truncated watched IPC record', 0): ('M', 'truncated journal fails'),
    ('goal2/game/watched_jobs.py', 'truncated watched IPC record', 1): ('M', 'partial long record fails'),
    ('goal2/game/watched_jobs.py', 'Invalid watched worker IPC', 0): ('M', 'journal failure cancels the job'),
    ('goal2/game/watched_jobs.py', 'pitch frame total budget exceeded', 0): T82,
    ('goal2/game/watched_jobs.py', 'pitch frame count differs', 0): ('M', 'frame count equals completed ticks'),
    ('goal2/game/watched_jobs.py', '=raise', 1): RERAISE,
    ('goal2/game/watched_jobs.py', 'self._check_token(token)', 1): ('M', 'poll_frames checks its token'),
    ('goal2/game/watched_jobs.py', 'pitch frames were not enabled', 0): T82,
    ('goal2/game/watched_jobs.py', "watched job is stale; active game changed", 1): ('M', 'frame poll stale owner'),
    ('goal2/game/watched_jobs.py', 'pitch frame total budget exceeded', 1): T82,
    ('goal2/game/watched_jobs.py', 'pitch frame packet budget exceeded', 0): T82,
    ('goal2/game/watched_jobs.py', 'pitch frame token differs', 0): ('M', 'frame token refused'),
    ('goal2/game/watched_jobs.py', 'watermark exceeds canonical events', 0): T82,
    ('goal2/game/watched_jobs.py', 'truncated pitch frame record', 0): T82,
    ('goal2/game/watched_jobs.py', 'pitch frame stream is empty', 0): T82,
    ('goal2/game/watched_jobs.py', 'Invalid watched pitch IPC', 0): ('M', 'frame failure cancels the job'),
    ('goal2/game/watched_jobs.py', 'self._check_token(token)', 2): ('M', 'ack_frames checks its token'),
    ('goal2/game/watched_jobs.py', 'stale or invalid pitch frame acknowledgement', 0): ('M', 'duplicate frame acknowledgement'),
    ('goal2/game/watched_jobs.py', 'self._check_token(token)', 3): ('M', 'cancel checks its token'),
    ('goal2/game/watched_jobs.py', 'watched completion preparation', 0): ('N', '#254 bounded completion-thread wait; owned by test_watched_completion'),
    ('goal2/desktop/watched.py', 'WinError', 0): WIN,
    ('goal2/desktop/watched.py', '=raise', 0): WIN,
    ('goal2/desktop/watched.py', '=raise', 1): WIN,
    ('goal2/desktop/watched.py', 'Watch supports scheduled friendlies only', 0): ('M', 'watch only for a scheduled friendly'),
    ('goal2/desktop/watched.py', 'frames must be boolean', 0): ('N', 'argument type check; owned by test_watched_pitch_jobs'),
    ('goal2/desktop/watched.py', 'A match is already running', 0): ('M', 'watch refuses while a match is pending'),
    ('goal2/desktop/watched.py', 'Watch requires pygame-ce', 0): GATE,
    ('goal2/desktop/watched.py', 'Watch requires Unicorn', 0): GATE,
    ('goal2/desktop/watched.py', 'Cannot start original friendly', 0): ('N', 'start-failure message wrapper; cleanup owned by test_desktop_watched_sharing'),
    ('goal2/desktop/watched.py', '=raise', 2): RERAISE,
    ('goal2/desktop/watched.py', 'exceeds bounded journal', 0): T66,
    ('goal2/desktop/watched.py', '=raise', 3): WIN,
    ('goal2/desktop/watched.py', '=raise', 4): WIN,
    ('goal2/desktop/watched.py', 'oversized viewer status', 0): T66,
    ('goal2/desktop/watched.py', 'malformed or stale viewer status', 0): ('M', 'viewer status token'),
    ('goal2/desktop/watched.py', 'Pygame viewer failed', 0): T66,
    ('goal2/desktop/watched.py', "'invalid viewer acknowledgement'", 0): ('M', 'viewer status digest'),
    ('goal2/desktop/watched.py', 'stale viewer acknowledgement', 0): ('M', 'viewer acknowledgement regression'),
    ('goal2/desktop/watched.py', 'invalid rendered pitch acknowledgement', 0): ('N', 'T83 type check of frame_sequence; owned by test_pygame_pitch_view'),
    ('goal2/desktop/watched.py', 'invalid rendered pitch acknowledgement', 1): ('M', 'rendered frame acknowledgement names the delivered frame'),
    ('goal2/desktop/watched.py', 'missing rendered pitch acknowledgement', 0): ('N', 'T83 pitch status shape; owned by test_pygame_pitch_view'),
    ('goal2/desktop/watched.py', 'did not start within 10 seconds', 0): ('N', 'T66 start timeout; owned by test_pygame_match_view'),
    ('goal2/desktop/watched.py', 'Pygame window exited', 0): ('M', 'viewer exit fails the match'),
    ('goal2/desktop/watched.py', '=raise', 5): ('M', 'controller failure cancels the match'),
    ('goal2/desktop/watched.py', '=raise', 6): WIN,
    ('goal2/desktop/watched.py', '=raise', 7): WIN,
    ('goal2/desktop/watched.py', '=raise', 8): RERAISE,
    ('goal2/desktop/competitive.py', 'No supported pending competitive fixture', 0): ('M', 'competitive only for a supported kind'),
    ('goal2/desktop/competitive.py', 'needs an original:<number>', 0): ('C', 'competitive index must be canonical',
        'an id whose suffix does not parse also fails the canonical check with the same message, so removing '
        'this site alone changes no outcome (T86 rework 2 run)'),
    ('goal2/desktop/competitive.py', 'needs an original:<number>', 1): ('M', 'competitive index must be canonical'),
    ('goal2/desktop/competitive.py', 'needs the original runtime', 0): GATE,
    ('goal2/desktop/competitive.py', 'already has a competitive bridge', 0): ('N', 'T80 one bridge per owner; owned by test_desktop_competitive_jobs'),
    ('goal2/desktop/competitive.py', 'competitive bridge is closed', 0): ('M', 'one competitive job at a time'),
    ('goal2/desktop/competitive.py', 'Another match is already running', 0): ('M', 'competitive refuses while another match is pending'),
    ('goal2/desktop/competitive.py', 'Cannot start competitive Play', 0): ('N', 'start-failure message wrapper; owned by test_desktop_competitive_jobs'),
    ('goal2/desktop/competitive.py', 'Competitive Play failed', 0): ('N', 'message prefix wrapper; the wrapped guards are listed for watched_jobs.py'),
    ('goal2/game/watched_publication.py', 'completed watched outcome required', 0): T64,
    ('goal2/game/watched_publication.py', 'validate_result(result', 0): T64,
    ('goal2/game/watched_publication.py', 'kind or budget differs', 0): T64,
    ('goal2/game/watched_publication.py', 'pending fixture or is incomplete', 0): T64,
    ('goal2/game/watched_publication.py', 'declared input image', 0): T64,
    ('goal2/game/watched_publication.py', 'changed engine year', 0): T64,
    ('goal2/game/watched_publication.py', 'returned RNG differs', 0): T64,
    ('goal2/game/watched_publication.py', 'scheduled watched completion changed', 0): T64,
    ('goal2/game/watched_publication.py', 'watched round was not prepared', 0): T64,
    ('goal2/game/watched_publication.py', 'a watched job is already pending', 0): ('N', 'base begin; overridden by ScenarioPublication.begin (its own site is listed)'),
    ('goal2/game/watched_publication.py', 'unknown or consumed watched completion token', 0): ('M', 'consumed publication token'),
    ('goal2/game/watched_publication.py', 'active state changed', 0): ('M', '_check_owner raises'),
    ('goal2/game/watched_publication.py', 'already preparing', 0): ('N', 'base prepare_completion; overridden by ScenarioPublication (its own site is listed)'),
    ('goal2/game/watched_publication.py', 'self._check_owner(pending)', 0): ('N', 'base prepare_completion; overridden by ScenarioPublication (its own site is listed)'),
    ('goal2/game/watched_publication.py', '=raise', 0): ('N', 'base prepare_completion; overridden by ScenarioPublication (its own site is listed)'),
    ('goal2/game/watched_publication.py', 'unknown or consumed watched completion preparation', 0): ('M', 'publication needs the bound preparation'),
    ('goal2/game/watched_publication.py', 'still preparing', 0): ('M', 'publication waits for the finished preparation'),
    ('goal2/game/watched_publication.py', 'raise preparation.error', 0): ('M', 'failed preparation is raised'),
    ('goal2/game/watched_publication.py', 'self._check_owner(pending)', 1): ('M', 'final owner check in publish_prepared'),
    ('goal2/desktop/match_view.py', 'stale or out-of-order viewer packet', 0): ('M', 'display packet token'),
    ('goal2/desktop/match_view.py', 'invalid viewer countries', 0): T66,
    ('goal2/desktop/match_view.py', 'invalid pitch playback rate', 0): T66,
    ('goal2/desktop/match_view.py', 'pitch causal backlog exceeded', 0): T66,
    ('goal2/desktop/match_view.py', 'invalid viewer event', 0): T66,
    ('goal2/desktop/match_view.py', 'invalid viewer completion', 0): T66,
    ('goal2/desktop/match_view.py', 'invalid viewer transition', 0): T66,
}


def sites():
    for name in SCENARIO + REAL:
        for number, line in enumerate((ROOT / name).read_text().splitlines(), 1):
            text = line.strip()
            if not text.startswith(('#', 'def ', 'from ', 'import ', '"""')) and PATTERN.search(text):
                yield name, number, text


def hits(fragment, text):
    return fragment[1:] == text if fragment.startswith('=') else fragment in text


def classify():
    spec = importlib.util.spec_from_file_location('mutations', ROOT / 'docs/cloud-270/mutations.py')
    mutations = importlib.util.module_from_spec(spec);spec.loader.exec_module(mutations)
    named = {m[1]: m for m in mutations.MUTATIONS}
    seen, rows, problems = {}, [], []
    for name, number, text in sites():
        keys = [k for k in SITES if k[0] == name and hits(k[1], text)]
        # occurrence counts only sites matching the same fragment, in file order
        match = []
        for key in keys:
            count = seen.get((name, key[1]), 0)
            if key[2] == count:
                match.append(key)
        for fragment in {k[1] for k in keys}:
            seen[(name, fragment)] = seen.get((name, fragment), 0) + 1
        # prefer the most specific fragment when several entries match this line
        match.sort(key=lambda k: -len(k[1]))
        if not match:
            problems.append(f'UNCLASSIFIED {name}:{number}: {text}');continue
        key = match[0]
        kind, detail, *why = SITES[key]
        if kind in ('M', 'C'):
            if detail not in named:
                problems.append(f'MISSING MUTATION {detail!r} for {name}:{number}')
                continue
            if named[detail][2] != name:
                problems.append(f'MUTATION {detail!r} edits {named[detail][2]}, not {name}:{number}')
            detail = f'mutation "{detail}" → `{named[detail][5].removeprefix(mutations.T)}`' + (f'; {why[0]}' if why else '')
        rows.append((name, number, text, kind, detail, key))
    used = {r[5] for r in rows}
    problems += [f'UNUSED ENTRY {k}' for k in SITES if k not in used]
    return rows, problems


def main(argv=None):
    rows, problems = classify()
    markdown = '--markdown' in (argv if argv is not None else sys.argv[1:])
    if markdown:
        print('| Site | Line | Class | Mutation → control, or reason |\n| --- | --- | --- | --- |')
    for name, number, text, kind, detail, _ in rows:
        if markdown:
            short = text.replace('|', '\\|')[:90]
            print(f'| `{name}:{number}` | `{short}` | {kind} | {detail} |')
        else:
            print(f'{kind} {name}:{number}: {detail}')
    for line in problems:
        print(line)
    counts = {k: sum(1 for r in rows if r[3] == k) for k in ('M', 'C', 'N')}
    print(f"{len(rows)} sites: {counts['M']} with their own mutation, {counts['C']} covered by another named "
          f"mutation, {counts['N']} not claimed; {len(problems)} problems")
    return 1 if problems else 0


if __name__ == '__main__':
    raise SystemExit(main())
