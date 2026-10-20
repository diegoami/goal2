#!/usr/bin/env python3
"""[designed: T86] Done-when 4: remove each boundary guard in a scratch copy; its named test must fail.

Usage (from the repository root): python3 docs/cloud-270/mutations.py [--only NAME]

The script copies the repository's files (git ls-files, cached and untracked,
excluding ignored files) into a temporary directory once per mutation. It applies
one exact replacement there and runs the named test. That run must fail with
output matching the stated reason. A baseline copy first runs every named test
unmutated and they must pass. The working tree is never modified.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
T = 'goal2.tests.'
C, B, F, W = T + 'test_scenario_contract.', T + 'test_scenario_branches.', T + 'test_scenario_factory.', T + 'test_scenario_walkthrough.'

# (category, name, file, old, new, test, reason regex)
MUTATIONS = [
    ('wrong-ID', 'journal token', 'goal2/game/watched_jobs.py',
     'if identity != token or type(number) is not int', 'if type(number) is not int',
     C + 'FakeWatchedContract.test_wrong_token_packet_is_refused', r'does not match "Invalid watched worker IPC: Watched worker exited \(0\)'),
    ('wrong-ID', 'viewer status token', 'goal2/desktop/watched.py',
     "if (not isinstance(value,dict) or value.get('token') != self.token", 'if (not isinstance(value,dict)',
     B + 'ControllerBranches.test_viewer_status_faults_cancel_without_publication', r"fault='stale-token'\)[\s\S]*?ValueError not raised"),
    ('wrong-ID', 'display packet token', 'goal2/desktop/match_view.py',
     'len(packet) != 4 or packet[0] != self.token', 'len(packet) != 4',
     B + 'ControllerBranches.test_display_refuses_wrong_token_and_out_of_order_packets', r"packet=\['x{48}'[\s\S]*?ValueError not raised"),
    ('wrong-ID', 'quick output bound to its template', 'goal2/desktop/jobs.py',
     'if template!=model.template_bytes or candidate.match_count', 'if candidate.match_count',
     B + 'QuickBranches.test_output_bound_to_another_template_or_count_is_refused', r"fault='wrong-template'\)[\s\S]*?ValueError not raised"),
    ('wrong-ID', 'scenario publication refuses an unmarked owner', 'goal2/scenario/runtime.py',
     "        _require_owner(owner, 'Fictional publication')\n        super().__init__(owner)", '        super().__init__(owner)',
     F + 'ScenarioFactoryTests.test_fiction_is_marked_and_refused_by_career_paths', r'ValueError not raised'),
    ('wrong-ID', 'scenario codec refuses an unmarked file', 'goal2/scenario/factory.py',
     "if not isinstance(payload, dict) or payload.get('format') != MARK:", 'if not isinstance(payload, dict):',
     F + 'ScenarioFactoryTests.test_fiction_is_marked_and_refused_by_career_paths', r"KeyError: 'state'"),
    ('out-of-order', 'journal sequence (gap)', 'goal2/game/watched_jobs.py',
     ' or number != self._sequence or ', ' or ',
     C + 'FakeWatchedContract.test_out_of_order_packet_is_refused', r'does not match "Invalid watched worker IPC: Watched worker exited \(0\)'),
    ('out-of-order', 'journal sequence (repeat)', 'goal2/game/watched_jobs.py',
     ' or number != self._sequence or ', ' or ',
     C + 'FakeWatchedContract.test_repeated_packet_is_refused', r'does not match "Invalid watched worker IPC: Watched worker exited \(0\)'),
    ('out-of-order', 'display packet sequence', 'goal2/desktop/match_view.py',
     'or type(packet[1]) is not int or packet[1] != self.sequence)', 'or type(packet[1]) is not int)',
     B + 'ControllerBranches.test_display_refuses_wrong_token_and_out_of_order_packets', r"packet=\['t{48}', 1[\s\S]*?ValueError not raised"),
    ('out-of-order', 'viewer acknowledgement regression', 'goal2/desktop/watched.py',
     "if self.last_status and value['sequence'] < self.last_status['sequence']:", 'if False:',
     B + 'ControllerBranches.test_viewer_status_faults_cancel_without_publication', r"fault='regress'\)[\s\S]*?ValueError not raised"),
    ('early-publication', 'quick output read only after exit', 'goal2/desktop/jobs.py',
     '        if code is None:\n            if self.interactive', '        if False:\n            if self.interactive',
     C + 'FakeQuickContract.test_early_output_is_not_read_before_exit', r'Friendly worker failed \(None\)'),
    ('early-publication', 'watched completion only after exit', 'goal2/game/watched_jobs.py',
     'if code is not None and not self._buffer and', 'if not self._buffer and',
     B + 'WatchedBranches.test_complete_packet_waits_for_child_exit', r'exited \(None\) without completion'),
    ('early-publication', 'publication waits for the last frame acknowledgement', 'goal2/game/watched_jobs.py',
     'if self._frame_ack != self._frame_sequence - 1:', 'if False:',
     B + 'ControllerBranches.test_unacknowledged_frames_block_publication_until_cancel', r'True is not false'),
    ('stale/duplicate', 'quick stale completion', 'goal2/desktop/jobs.py',
     'if model.state is not self.original or encode(model.state,model.template_bytes)!=self.snapshot:', 'if False:',
     C + 'FakeQuickContract.test_stale_completion_is_refused', r'ValueError not raised'),
    ('stale/duplicate', 'watched stale owner', 'goal2/game/watched_jobs.py',
     "raise ValueError('watched job is stale; active game changed')\n            # [designed] Drain queued",
     'pass\n            # [designed] Drain queued',
     C + 'FakeWatchedContract.test_stale_owner_is_refused', r'ValueError not raised'),
    ('stale/duplicate', 'duplicate completion packet', 'goal2/game/watched_jobs.py',
     ' or self._complete is not None:', ':',
     B + 'WatchedBranches.test_duplicate_mismatched_or_foreign_completion_is_refused', r"fault='duplicate'\)[\s\S]*?ValueError not raised"),
    ('stale/duplicate', 'consumed publication token', 'goal2/game/watched_publication.py',
     'if self._pending is None or token!=self._pending[0]:', 'if False:',
     B + 'WatchedBranches.test_consumed_token_cannot_publish_again', r'TypeError: cannot unpack non-iterable NoneType'),
    ('stale/duplicate', 'duplicate frame acknowledgement', 'goal2/game/watched_jobs.py',
     'not self._frame_ack < sequence < self._frame_sequence', 'not sequence < self._frame_sequence',
     B + 'WatchedBranches.test_frame_acknowledgements_are_cumulative_and_bounded', r"sequence=1\)[\s\S]*?ValueError not raised"),
    ('cancel', 'quick cancel', 'goal2/desktop/jobs.py',
     '"""[designed] Bound termination waits and reap; never publish on close."""',
     '"""[designed] Bound termination waits and reap; never publish on close."""\n        return',
     C + 'FakeQuickContract.test_cancel_never_publishes', r'True is not false'),
    ('cancel', 'watched cancel invalidates the publication token', 'goal2/game/watched_jobs.py',
     '        self.publication.cancel()\n        self.process.terminate()', '        self.process.terminate()',
     C + 'FakeWatchedContract.test_cancel_never_publishes_and_releases_the_token', r'a watched job is already pending'),
    ('redraw', 'a view that advances the session', 'goal2/scenario/model.py',
     '        self.result_text(state)\n', '        self.result_text(state)\n        state.campaign.results.append({})\n',
     # [derived: T86 first run] The real QuickJobs stale guard notices the redraw run's change first.
     W + 'WalkthroughTests.test_redraw_and_view_calls_never_advance_the_session',
     r'Halftime continuation is stale; active game changed'),
]


def copy_tree(target):
    files = subprocess.run(['git', 'ls-files', '--cached', '--others', '--exclude-standard', '-z'], cwd=ROOT,
                           capture_output=True, check=True).stdout.split(b'\0')
    for name in filter(None, files):
        source = ROOT / name.decode()
        if source.is_file():
            destination = target / name.decode()
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)


def run(target, test):
    return subprocess.run([sys.executable, '-B', '-m', 'unittest', test], cwd=target, capture_output=True,
                          text=True, timeout=300)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument('--only')
    args = parser.parse_args(argv)
    chosen = [m for m in MUTATIONS if args.only in (None, m[1])]
    failures = 0
    with tempfile.TemporaryDirectory(prefix='goal2-T86-baseline-') as folder:
        copy_tree(Path(folder))
        for test in sorted({m[5] for m in chosen}):
            result = run(Path(folder), test)
            ok = result.returncode == 0
            failures += not ok
            print(f"baseline {'pass' if ok else 'FAIL'}: {test}")
    for category, name, path, old, new, test, reason in chosen:
        with tempfile.TemporaryDirectory(prefix='goal2-T86-mutant-') as folder:
            copy_tree(Path(folder))
            file = Path(folder) / path
            text = file.read_text()
            if text.count(old) != 1:
                print(f'MUTATION NOT APPLIED ({text.count(old)} matches): {name}');failures += 1;continue
            file.write_text(text.replace(old, new))
            result = run(Path(folder), test)
            output = result.stdout + result.stderr
            ok = result.returncode != 0 and re.search(reason, output) is not None
            failures += not ok
            print(f"{'fails as named' if ok else 'NOT DETECTED'} [{category}] {name} -> {test.removeprefix(T)}"
                  f" ({reason if ok else output[-800:]})")
    print(f'{len(chosen)} mutations, {failures} problems')
    return 1 if failures else 0


if __name__ == '__main__':
    raise SystemExit(main())
