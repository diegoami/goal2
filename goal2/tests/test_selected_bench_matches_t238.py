"""T238: selected bench requests use the same game and fixture as the worker."""
import copy
import io
import json
from dataclasses import asdict, replace
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

from goal2.game import extended_squad
from goal2.game.engine_process import EngineProcess
from goal2.game.engine_server import Server
from goal2.game.extended_save import to_data
from goal2.game.extended_schema import ExtendedSelection
from goal2.game.extended_match import prepare_extended_watched
from goal2.game.watched_match import prepare_watched, sealed
from goal2.tests.test_campaign_competitive_publication import campaign
from goal2.tests import pypy_engine, requires


class SelectedBenchMatches(unittest.TestCase):
    def test_public_preparation_uses_current_pool_for_larger_squad(self):
        state, template, fixture = campaign(index=42, kind=1)
        state = extended_squad.resized(state, 22)
        state.campaign.reserve_ids = list(reversed(state.campaign.reserve_ids))
        state.extra_squad[1] = state.campaign.reserve_ids[0]
        expected, extras = prepare_extended_watched(state, template, fixture)
        actual = prepare_watched(state, template, fixture)
        self.assertEqual(extras, (state.extra_squad[1],))
        self.assertTrue(actual.memory_component() == expected.memory_component())

    def test_client_refuses_malformed_selection_before_starting_process(self):
        _, _, fixture = campaign(index=42, kind=1)
        process = EngineProcess(lambda *_: None)
        try:
            with self.assertRaisesRegex(ValueError, 'selected-bench'):
                process.match('watched', fixture, selected_bench={})
            self.assertIsNone(process.process)
        finally:
            process.close()

    def test_worker_rejects_missing_mismatched_and_unexpected_profiles_before_play(self):
        ordinary, template, fixture = campaign(index=42, kind=1)
        state = extended_squad.resized(ordinary, 22)
        state.extra_squad[1] = state.campaign.reserve_ids[0]
        profile = bound_profile(state, template, fixture)
        moved = dict(profile, slots=profile['slots'][::-1])
        tampered = dict(profile, image_sha256='0' * 64)
        worker = Server(io.BytesIO(), io.BytesIO())
        request = dict(kind='watched', fixture=asdict(fixture))
        with patch('goal2.game.watched_match._drive_match') as drive:
            for game, fields in (
                (state, {}), (state, {'selected_bench': moved}), (state, {'selected_bench': tampered}),
                (ordinary, {'selected_bench': profile}), (ordinary, {'selected_bench': None}),
            ):
                worker.game = game, template
                with self.assertRaisesRegex(ValueError, 'selected-bench'):
                    worker._match(dict(request, **fields))
                self.assertIs(worker.game[0], game)
            drive.assert_not_called()


def bound_profile(state, template, fixture, *, competitive=False):
    image, _ = prepare_extended_watched(state, template, fixture, competitive=competitive)
    selection = ExtendedSelection.from_prepared(state, fixture, sealed(image))
    return to_data(selection, state.extra_squad)


def selected_state(count, competitive):
    state, template, fixture = campaign(index=42, kind=2 if competitive else 1)
    if count is None:
        return state, template, fixture, []
    state = extended_squad.resized(state, 22)
    pairs = []

    def available(word):
        record = state.players[word]
        return 0 < record[14] < 128 and not record[16] & 0xA4

    for off in reversed(state.starting_eleven):
        if len(pairs) == count:
            break
        role = state.players[off][6]
        if role == 0 or not available(off):
            continue
        on = next((word for word in state.campaign.reserve_ids if available(word)
                   and state.players[word][6] == role and word not in {on for _, on in pairs}), None)
        if on is not None:
            pairs.append((off, on))
    if len(pairs) != count:
        raise AssertionError('fixture could not select all intended substitutes')
    if pairs:
        state.captain = pairs[0][0]
    extras = [on for _, on in pairs]
    state.extra_squad = [None] * (state.squad_capacity - 20 - count) + extras
    return state, template, fixture, pairs


def direct_sdk(state, template, fixture, pairs, competitive):
    from goal2.engine.original_match import Image, Match
    from goal2.engine.original_match.machine import REGS
    from goal2.game.watched_match import FRIENDLY_SUBSTITUTIONS, WatchedOutcome, _complete_memory

    image, extras = prepare_extended_watched(state, template, fixture, competitive=competitive)
    options = dict(managed=state.managed_country, captain=state.captain or None, delay_byte=0,
                   substitutions=(5, 5) if competitive else FRIENDLY_SUBSTITUTIONS,
                   engine='port', ticks=bool(pairs), record_draws=True)
    if state.squad_capacity != 20:
        options['live_players'] = True
    if extras:
        options['extra_players'] = list(extras)
    match = Match(sealed(image), fixture, **options)
    events = []
    for event in match.events():
        if event.kind == 'tick':
            continue
        events.append(copy.deepcopy(event))
        if event.kind == 'decision':
            chosen = pairs if event.data['context'] == 'half_time' else []
            match.answer(substitutions=sorted(chosen, key=lambda p: event.data['eleven'].index(p[0])))
    memory = _complete_memory(match.memory_component(), image)
    after = Image(memory)
    outcome = WatchedOutcome(match.result(), memory, tuple(events),
                             (after.rd(0x7B62), after.rd(0x8336)), image.year())
    return outcome, {name: match.m.reg(name) for name in REGS}


# Observe only the real SDK's register values at the production serialization point.
OBSERVE_REGISTERS = """
import json
from pathlib import Path
import sys
from goal2.engine.original_match.machine import REGS
from goal2.game import engine_server, watched_match
class ObservedMatch(watched_match.Match):
    def memory_component(self):
        Path(sys.argv[1]).write_text(json.dumps({name: self.m.reg(name) for name in REGS}))
        return super().memory_component()
watched_match.Match = ObservedMatch
sys.exit(engine_server.main())
"""


@requires.need(slow=True)
class ActualSelectedBenchMatches(unittest.TestCase):
    def run_pipe(self, jobs, fixture, pairs):
        explicit_fixture = (fixture,) if jobs.KIND == 'watched' else ()
        token = jobs.start(*explicit_fixture, delay_byte=0, record_draws=True,
                           frames=bool(pairs), bench=bool(pairs))
        deadline = time.monotonic() + 900
        events = []
        answered = False
        while jobs.busy:
            self.assertLess(time.monotonic(), deadline, 'worker did not finish its match')
            events.extend(jobs.poll(token))
            if not jobs.busy:
                break
            if pairs:
                frames = jobs.poll_frames(token)
                if frames:
                    jobs.ack_frames(token, frames[-1]['sequence'])
                if jobs.waiting is not None:
                    data = jobs.waiting.data
                    chosen = []
                    if data['context'] == 'half_time' and not answered:
                        self.assertTrue({on for _, on in pairs} <= set(data['bench']))
                        chosen = sorted(pairs, key=lambda pair: data['eleven'].index(pair[0]))
                        answered = True
                    jobs.answer(token, chosen)
            time.sleep(.002)
        self.assertIsNotNone(jobs.outcome)
        self.assertEqual(answered, bool(pairs))
        self.assertEqual(tuple(events), jobs.outcome.events)
        return jobs.outcome

    def test_real_pipe_matches_direct_sdk_and_publishes_selected_squad_once(self):
        from goal2.desktop.competitive import CompetitiveJobs
        from goal2.desktop.fixtures_page import snapshot
        from goal2.desktop.model import DesktopModel
        from goal2.engine.original_match import Image
        from goal2.game import campaign_pool
        from goal2.game.engine_python import engine_python
        from goal2.game.session_save import decode, encode
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.game.watched_publication import CompetitivePublication
        from goal2.tests.test_assistant_pipe_t183c import model
        from goal2.tests.test_watched_publication import Owner

        with tempfile.TemporaryDirectory() as folder:
            registers = Path(folder) / 'regs.json'
            command = [engine_python(), '-c', OBSERVE_REGISTERS, str(registers)]
            owner = DesktopModel(model().goaldat, b'', Path(folder) / 'career.g2save')
            watched = WatchedJobs(owner, command=command)
            competitive_jobs = CompetitiveJobs(owner, command=command)
            worker_pid = None
            try:
                for count, competitive in ((0, False), (None, False), (1, False), (2, True)):
                    with self.subTest(count=count, competitive=competitive):
                        state, template, fixture, pairs = selected_state(count, competitive)
                        owner.state, owner.template_bytes = state, template
                        before = copy.deepcopy(state)
                        jobs = competitive_jobs if competitive else watched
                        registers.unlink(missing_ok=True)
                        expected = pypy_engine.start(__name__ + ':direct_sdk',
                                                     before, template, fixture, pairs, competitive)
                        outcome = self.run_pipe(jobs, fixture, pairs)
                        direct, regs = expected.result(timeout=900)
                        if worker_pid is None:
                            worker_pid = jobs.shared.engine.pid
                        self.assertIsNotNone(worker_pid)
                        self.assertEqual(jobs.shared.engine.pid, worker_pid)
                        self.assertEqual(outcome.events, direct.events)
                        self.assertEqual(outcome.result, direct.result)
                        self.assertTrue(outcome.memory == direct.memory)
                        self.assertEqual(outcome.seeds, direct.seeds)
                        self.assertEqual(json.loads(registers.read_text()), regs)
                        self.assertEqual(state, before)
                        self.assertEqual(owner.state.match_count, before.match_count + 1)
                        self.assertEqual(owner.state.campaign.completed_fixture_ids, [f'original:{fixture.index}'])
                        self.assertFalse(snapshot(owner)['error'])
                        if count is not None:
                            selected = set(before.managed_squad + [w for w in before.extra_squad if w is not None])
                            self.assertEqual(set(owner.state.managed_squad + [
                                w for w in owner.state.extra_squad if w is not None]), selected)
                            self.assertEqual([w is None for w in owner.state.extra_squad],
                                             [w is None for w in before.extra_squad])
                            self.assertEqual(owner.state.starting_eleven, owner.state.managed_squad[:11])
                            self.assertEqual(campaign_pool.validate(owner.state), owner.state.campaign.reserve_ids)
                            if pairs:
                                swaps = [(sw['off'], sw['on']) for sw in outcome.result['substitutions']
                                         if sw['team'] == 0]
                                self.assertCountEqual(swaps, pairs)
                                self.assertEqual(owner.state.captain, dict(pairs)[before.captain])
                            saved = encode(owner.state, template)
                            self.assertEqual(json.loads(saved)['version'], 6)
                            self.assertEqual(decode(saved), (owner.state, template))
                            if competitive:
                                # A valid result paired with different returned bytes is
                                # refused before the original owner or save can change.
                                other = Owner(state, template)
                                publication = CompetitivePublication(other)
                                job = publication.begin(fixture)
                                after = Image(outcome.memory)
                                row = next(r for r in outcome.result['players'] if r['confidence'][1] is not None)
                                after.memory[after.far(0xA91B) + 20 * row['player'] + 12] ^= 1
                                bad = replace(outcome, memory=after.memory_component())
                                with self.assertRaisesRegex(ValueError, 'consequences differ'):
                                    publication.complete(job.token, bad)
                                self.assertIs(other.state, state)
                                self.assertEqual(other.state, before)
                                with self.assertRaisesRegex(ValueError, 'consumed'):
                                    publication.complete(job.token, outcome)
                        else:
                            self.assertNotIn('selected_bench', owner.state.last_match)
                            self.assertFalse(any('player_records' in ev.data for ev in outcome.events))
                        with self.assertRaisesRegex(ValueError, 'stale or consumed'):
                            jobs.poll(jobs.token)
                        print('T238 pipe/direct', count, competitive, len(outcome.events), flush=True)
            finally:
                competitive_jobs.close()
                watched.close()
