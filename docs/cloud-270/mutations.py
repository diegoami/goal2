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
G = T + 'test_scenario_guards.'

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
    # [designed: T86 rework 1] R1/R2 and the class sweep: every remaining claimed guard.
    ('R1 result-schema', 'scenario publication runs validate_result', 'goal2/scenario/runtime.py',
     '    validate_result(result, competitive=competitive)\n', '',
     G + 'PublicationGuards.test_malformed_result_is_refused_by_result_validation', r'ValueError not raised'),
    ('R2 stale', 'final owner check in publish_prepared', 'goal2/game/watched_publication.py',
     '        self._check_owner(pending)\n        self.owner.view(preparation.candidate)', '        self.owner.view(preparation.candidate)',
     G + 'PublicationGuards.test_publish_refuses_an_owner_changed_after_preparation', r"change='value'\)[\s\S]*?ValueError not raised"),
    ('stale/duplicate', 'owner check before preparation', 'goal2/scenario/runtime.py',
     '            self._check_owner(pending)\n', '            pass\n',
     G + 'PublicationGuards.test_prepare_refuses_an_owner_changed_before_preparation', r'ValueError not raised'),
    ('wrong-ID', 'job bound to the scheduled fixture', 'goal2/scenario/runtime.py',
     "            raise ValueError('fictional job differs from the scheduled fixture')", '            pass',
     G + 'PublicationGuards.test_job_must_be_the_scheduled_fixture', r'ValueError not raised'),
    ('early-publication', 'completion needs exactly one end and full_time', 'goal2/scenario/runtime.py',
     "    if (not kinds or kinds[-1] != 'end' or kinds.count('end') != 1 or kinds.count('full_time') != 1\n            or ",
     '    if (',
     G + 'PublicationGuards.test_incomplete_event_stream_is_refused', r'ValueError not raised'),
    ('wrong-ID', 'completion bound to its declared input', 'goal2/scenario/runtime.py',
     "        raise ValueError('watched completion differs from the declared input image')", '        pass',
     G + 'PublicationGuards.test_foreign_input_image_is_refused', r'ValueError not raised'),
    ('wrong-ID', 'completion memory must carry the fiction mark', 'goal2/scenario/runtime.py',
     "if (not isinstance(memory, dict) or memory.get('mark') != MARK\n            or ", 'if (not isinstance(memory, dict)\n            or ',
     G + 'PublicationGuards.test_unmarked_completion_memory_is_refused', r'ValueError not raised'),
    ('wrong-ID', 'competitive kind bound to the job', 'goal2/scenario/runtime.py',
     "    if competitive and result['kind'] != fixture.kind:", '    if False:',
     # [derived: T86 rework run] Without it the calendar's validate_resolution refuses with another message.
     G + 'PublicationGuards.test_competitive_kind_must_match_the_job',
     r'does not match "Competitive Play failed: Invalid watched worker IPC: invalid competitive resolution fields'),
    ('wrong-ID', 'completion events equal the streamed events', 'goal2/game/watched_jobs.py',
     'if tuple(self.events) != value.events:', 'if False:',
     B + 'WatchedBranches.test_duplicate_mismatched_or_foreign_completion_is_refused', r"fault='mismatch'\)[\s\S]*?ValueError not raised"),
    ('wrong-ID', 'completion bound to the pending fixture', 'goal2/scenario/runtime.py',
     "            or (result['first'], result['second'], result['index'], result['managed'])\n            != (fixture.first, fixture.second, fixture.index, state.managed_country)):",
     '            ):',
     B + 'WatchedBranches.test_duplicate_mismatched_or_foreign_completion_is_refused', r"fault='bad-result'\)[\s\S]*?(does not match|ValueError not raised)"),
    ('wrong-ID', 'viewer status digest', 'goal2/desktop/watched.py',
     "                        or value['digest'] != self.digests[value['sequence']]):", '                        ):',
     G + 'ViewerGuards.test_status_digest_must_match_the_sent_stream', r'ValueError not raised'),
    ('out-of-order', 'viewer status names a sent sequence', 'goal2/desktop/watched.py',
     "                        or not 0 <= value['sequence'] <= self.display.sequence\n", '',
     G + 'ViewerGuards.test_status_cannot_acknowledge_unsent_packets', r'KeyError'),
    ('wrong-ID', 'rendered frame acknowledgement names the delivered frame', 'goal2/desktop/watched.py',
     "receipt is None or value['frame_digest'] != receipt[0]", 'receipt is None',
     G + 'ViewerGuards.test_frame_acknowledgement_must_name_the_delivered_frame', r'ValueError not raised'),
    ('early-publication', 'frame count equals completed ticks', 'goal2/game/watched_jobs.py',
     "if self._frame_sequence != self._complete.result['ticks'] or self._frame_sequence == 0:", 'if False:',
     G + 'ViewerGuards.test_frame_count_must_equal_completed_ticks', r'ValueError not raised'),
    ('cancel', 'viewer close cancels the match', 'goal2/desktop/watched.py',
     "                if value['kind'] == 'closed':\n                    self.cancel()\n", "                if value['kind'] == 'closed':\n",
     B + 'ControllerBranches.test_viewer_close_cancels_the_match', r'fictional child exceeded its deadline'),
    ('early-publication', 'watched exit without completion fails', 'goal2/game/watched_jobs.py',
     'if code != 0 or self._complete is None:', 'if False:',
     C + 'FakeWatchedContract.test_exit_without_completion_fails_the_job', r'does not match'),
    ('early-publication', 'truncated journal fails', 'goal2/game/watched_jobs.py',
     "                raise ValueError('truncated watched IPC record')\n            elif code is not None and len(self._buffer) >= 4:",
     '                pass\n            elif code is not None and len(self._buffer) >= 4:',
     C + 'FakeWatchedContract.test_truncated_record_fails_the_job', r'watched child exceeded its deadline'),
    ('failure', 'watched error packet fails the job', 'goal2/game/watched_jobs.py',
     "                    raise ValueError('Watched worker failed: ' + value)", "                    raise ValueError('ignored: ' + value)",
     C + 'FakeWatchedContract.test_error_packet_fails_the_job', r'does not match'),
    ('failure', 'quick non-zero exit fails', 'goal2/desktop/jobs.py',
     '            if code!=0:', '            if False:',
     C + 'FakeQuickContract.test_failure_leaves_the_active_game', r'FileNotFoundError: .*output\.g2save'),
    ('stale/duplicate', 'one quick job at a time', 'goal2/desktop/jobs.py',
     "if self.busy or getattr(self.model,'match_pending',False):raise ValueError('A match is already running')",
     "if False:raise ValueError('A match is already running')",
     C + 'FakeQuickContract.test_success_publishes_once_and_one_job_at_a_time', r'ValueError not raised'),
    ('stale/duplicate', 'halftime continuation used once', 'goal2/desktop/jobs.py',
     '        if not self.busy or self.halftime is None or self.continued:', '        if not self.busy:',
     B + 'QuickBranches.test_half_time_injury_supported_decision_and_continuation', r'ValueError not raised'),
    ('stale/duplicate', 'halftime continuation stale', 'goal2/desktop/jobs.py',
     'if self.model.state is not self.original or encode(self.model.state,self.model.template_bytes)!=self.snapshot:', 'if False:',
     B + 'QuickBranches.test_stale_half_time_continuation_cancels', r'ValueError not raised'),
    ('wrong-ID', 'halftime preview bound to the fixture', 'goal2/desktop/jobs.py',
     "if packet['teams']!=[fixture.side_a,fixture.side_b]:raise ValueError('preview fixture changed')", 'pass',
     B + 'QuickBranches.test_bad_half_time_preview_cancels', r'ValueError not raised'),
    ('wrong-ID', 'quick output bound to one more match', 'goal2/desktop/jobs.py',
     ' or candidate.match_count!=self.original.match_count+1:', ':',
     B + 'QuickBranches.test_output_bound_to_another_template_or_count_is_refused', r"fault='double-count'\)[\s\S]*?ValueError not raised"),
    ('unsupported', 'quick only for a scheduled friendly', 'goal2/scenario/runtime.py',
     "            raise ValueError('Quick supports scheduled friendlies only in the fictional scenario')", '            pass',
     G + 'ModelAndRuntimeGuards.test_quick_refuses_a_competitive_fixture', r'ValueError not raised'),
    ('wrong-ID', 'quick check refuses a foreign template', 'goal2/scenario/runtime.py',
     "            raise ValueError('Fictional quick match refused: foreign template')", '            pass',
     G + 'ModelAndRuntimeGuards.test_quick_check_refuses_unavailable_starters_and_foreign_templates', r'ValueError not raised'),
    ('unsupported', 'quick check refuses unavailable starters', 'goal2/scenario/runtime.py',
     '        eligibility.require_available(state.players, state.starting_eleven)\n', '',
     G + 'ModelAndRuntimeGuards.test_quick_check_refuses_unavailable_starters_and_foreign_templates', r'ValueError not raised'),
    ('unsupported', 'watch only for a scheduled friendly', 'goal2/desktop/watched.py',
     '        if pending is None or pending.kind != 1:', '        if pending is None:',
     B + 'CompetitiveBranches.test_unsupported_actions_are_refused_and_named', r'does not match|ValueError not raised'),
    ('unsupported', 'competitive only for a supported kind', 'goal2/desktop/competitive.py',
     'if pending is None or pending.kind == 1 or pending.kind not in KINDS:', 'if pending is None or pending.kind == 1:',
     B + 'CompetitiveBranches.test_unsupported_actions_are_refused_and_named', r'does not match|ValueError not raised'),
    ('stale/duplicate', 'competitive refuses while another match is pending', 'goal2/desktop/competitive.py',
     "        if getattr(self.owner, 'match_pending', False):\n", '        if False:\n',
     G + 'ModelAndRuntimeGuards.test_competitive_play_refuses_while_another_match_is_pending', r'ValueError not raised'),
    ('stale/duplicate', 'calendar completes only the next fixture', 'goal2/scenario/factory.py',
     'if pending is None or fixture_id != pending.fixture_id:', 'if pending is None:',
     G + 'ModelAndRuntimeGuards.test_calendar_completes_only_the_next_fixture_with_its_resolution', r'ValueError not raised'),
    ('wrong-ID', 'competitive completion needs its resolution', 'goal2/scenario/factory.py',
     "                raise ValueError('competitive completion needs its resolution')", '                return',
     G + 'ModelAndRuntimeGuards.test_calendar_completes_only_the_next_fixture_with_its_resolution', r'ValueError not raised'),
    ('wrong-ID', 'competitive resolution validated', 'goal2/scenario/factory.py',
     '            validate_resolution(resolution, score, pending.kind)\n', '',
     G + 'ModelAndRuntimeGuards.test_calendar_completes_only_the_next_fixture_with_its_resolution', r'ValueError not raised'),
    ('wrong-ID', 'friendly completion has no resolution', 'goal2/scenario/factory.py',
     "            raise ValueError('friendly completion cannot have competitive resolution')", '            pass',
     G + 'ModelAndRuntimeGuards.test_calendar_completes_only_the_next_fixture_with_its_resolution', r'ValueError not raised'),
    ('fiction mark', 'scenario encoder refuses an unmarked state', 'goal2/scenario/factory.py',
     "    if getattr(state, 'scenario', None) != MARK:\n        raise ValueError('not a fictional scenario state')\n    campaign",
     '    campaign',
     F + 'ScenarioFactoryTests.test_fiction_is_marked_and_refused_by_career_paths', r'ValueError not raised'),
    ('fiction mark', 'scenario model refuses to save', 'goal2/scenario/model.py',
     "        raise ValueError('Saving refused: this is a fictional scenario, not a career')", '        return',
     F + 'ScenarioFactoryTests.test_fiction_is_marked_and_refused_by_career_paths', r'ValueError not raised'),
    ('fiction mark', 'scenario model refuses to resume', 'goal2/scenario/model.py',
     "        raise ValueError('Resume refused: the fictional scenario has no career saves')", '        return',
     F + 'ScenarioFactoryTests.test_fiction_is_marked_and_refused_by_career_paths', r'ValueError not raised'),
    ('fiction mark', 'scenario view refuses an unmarked state', 'goal2/scenario/model.py',
     "        require_scenario(state, 'Fictional view')\n", '',
     G + 'ModelAndRuntimeGuards.test_view_and_result_text_refuse_unmarked_or_foreign_results', r'ValueError not raised'),
    ('fiction mark', 'scenario result text refuses a non-fictional result', 'goal2/scenario/model.py',
     " or match.get('engine') != ENGINE:", ':',
     G + 'ModelAndRuntimeGuards.test_view_and_result_text_refuse_unmarked_or_foreign_results', r'KeyError|ValueError not raised'),
    ('fiction mark', 'publication refuses a foreign template', 'goal2/scenario/runtime.py',
     "    if owner.template_bytes != TEMPLATE:\n", '    if False:\n',
     F + 'ScenarioFactoryTests.test_fiction_is_marked_and_refused_by_career_paths', r'ValueError not raised'),
    ('unsupported', 'exchange only in a friendly window', 'goal2/scenario/model.py',
     "        if not self._window(self.state)['allowed']:\n            raise ValueError('Exchange window is closed')\n", '',
     G + 'ModelAndRuntimeGuards.test_exchange_window_closes_outside_friendlies', r'does not match|ValueError not raised'),
    ('unsupported', 'confirm refuses unavailable starters', 'goal2/scenario/model.py',
     '        eligibility.require_available(self.state.players, eleven)\n', '',
     F + 'ScenarioFactoryTests.test_confirm_validates_like_desktop_model_and_is_atomic', r"unavailable starters'\)[\s\S]*?ValueError not raised"),
    ('DW2', 'real backend reports missing items', 'goal2/scenario/real.py',
     'items = [path for path in NEEDS[lane] if not (ROOT / path).is_file()]', 'items = []',
     G + 'ModelAndRuntimeGuards.test_real_backend_reports_every_missing_item', r'AssertionError'),
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
