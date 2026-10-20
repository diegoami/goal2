"""[designed: T86] Scripted session → next-fixture walkthrough through the real controllers.

`run()` drives ScenarioModel with the real QuickJobs, WatchedController and
CompetitiveJobs (scenario runtime, fake children) across all five fictional
fixtures and returns a JSON-ready record. Tokens, paths and timings are left
out, so two runs give byte-identical JSON. `redraw` repeats every read-only call
(view, pool, card, result text, Display lines) between steps and polls; it must
not change the record.
"""
from __future__ import annotations

import time

from goal2.desktop.competitive import CompetitiveJobs
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.watched import WatchedController
from goal2.scenario.model import ScenarioModel
from goal2.scenario.runtime import RUNTIME
from goal2.scenario.worker import command

DEADLINE = 30


def _refusal(action):
    try:
        action()
    except ValueError as exc:
        return str(exc)
    raise AssertionError('expected a refusal')


def run(redraw=0):
    model = ScenarioModel()
    displays = []

    def look():
        for _ in range(redraw):
            model.view();model.pool_view();model.result_text();model.card(model.state.captain)
            for display in displays:
                display.lines();display.visible();display.digest()

    def wait(step):
        deadline = time.monotonic() + DEADLINE
        while time.monotonic() < deadline:
            look()
            if step():
                return
            time.sleep(.01)
        raise TimeoutError('fictional walkthrough step exceeded its deadline')
    record = {'lane': 'goal2 fictional scenario (T86); not original data, not a career'}
    look()
    record['opening'] = {'view': model.view(), 'captain_card': model.card(model.state.captain),
                         'pool': model.pool_view(),
                         'refusals': {'injured_starter': _refusal(lambda: model.confirm(
                             [19] + model.state.starting_eleven[1:], model.state.captain, 0)),
                                      'save': _refusal(lambda: model.save('career.g2save'))}}
    model.exchange(20, 101)
    model.confirm(list(model.state.starting_eleven), model.state.captain, 0x30)
    look()
    record['management'] = {'exchange': [20, 101], 'squad': list(model.state.managed_squad),
                            'eleven': list(model.state.starting_eleven), 'captain': model.state.captain,
                            'tactics': model.state.country_tactics}

    quick = QuickJobs(model, command=command('quick'), runtime=RUNTIME)
    quick.start(halftime=True)
    wait(lambda: quick.poll() is None and quick.halftime is not None)
    halftime = dict(quick.halftime)
    refused = _refusal(lambda: quick.substitute(10, 19))
    quick.substitute(10, 13);quick.continue_match()
    wait(lambda: quick.poll())
    record['fixture_1_quick'] = {'halftime': halftime, 'injured_incoming_refused': refused,
                                 'substitution': [10, 13], 'result': model.result_text(),
                                 'last_match': model.state.last_match, 'next': model.view()['fixture']}

    watch = WatchedController(model, engine_command=command('watched'), viewer_command=command('viewer'),
                              runtime=RUNTIME)
    watch.start()
    displays.append(watch.display)
    wait(lambda: watch.poll())
    record['fixture_2_watched'] = {'display': watch.display.lines(), 'events': len(watch.display.events),
                                   'frames_rendered': watch.frame_ack + 1, 'result': model.result_text(),
                                   'last_match': model.state.last_match, 'next': model.view()['fixture']}
    watch.close();displays.clear()

    for key in ('fixture_3_competitive', 'fixture_4_competitive'):
        jobs = CompetitiveJobs(model, command=command('competitive'), runtime=RUNTIME)
        token = jobs.start()
        wait(lambda: (jobs.poll(token) if jobs.busy else None) is None and not jobs.busy)
        record[key] = {'result': model.result_text(), 'last_match': model.state.last_match,
                       'next': model.view()['fixture'], 'play_label': model.view()['play_label']}
        jobs.close()

    quick = QuickJobs(model, command=command('quick'), runtime=RUNTIME)
    watch = WatchedController(model, engine_command=command('watched'), viewer_command=command('viewer'),
                              runtime=RUNTIME)
    jobs = CompetitiveJobs(model, command=command('competitive'), runtime=RUNTIME)
    record['fixture_5_unsupported'] = {'view': model.view(),
                                       'quick': _refusal(lambda: quick.start()),
                                       'watch': _refusal(lambda: watch.start()),
                                       'competitive': _refusal(lambda: jobs.start()),
                                       'save': _refusal(lambda: model.save('career.g2save'))}
    watch.close();jobs.close()
    record['final'] = {'match_count': model.state.match_count,
                       'completed': list(model.state.campaign.completed_fixture_ids),
                       'results': model.state.campaign.results}
    return record
