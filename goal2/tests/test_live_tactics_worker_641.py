"""#641 fresh observer on UNCHANGED640actual inputs; requires accepted696adoption.
No new input/seed/fixture/limit, no result/event filtering, no prepared Match state.
"""
import copy
import hashlib
import json
import unittest
from types import SimpleNamespace
from unittest import mock
from goal2.tests import requires


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@requires.need(modules=('PySide6','pygame'),slow=True,**requires.HALFTIME)
class ActualLiveTraits(unittest.TestCase):
    def test_unchanged640request_swap_and_tactic_journey_exposes_current_traits_without_state_writes(self):
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        from goal2.ui.match_day import MatchDay
        from goal2.desktop.country_card import characteristic_view
        from goal2.tests.test_live_tactics_characteristics_641 import expected_panel
        from goal2.tests.test_substitution_actual_636 import run_journey
        observations=[];current_data={};first_order=None;changed_order=False;changed_traits=False;first_panel=None
        initial_panel=None;initial_players=None;traits_changed_from_input=False;energy_changed_from_input=False
        real_refresh=TeamTacticsScreen.refresh
        real_bench=MatchDay.live_bench
        test=self

        def check(screen,data,label):
            nonlocal first_order,changed_order,changed_traits,first_panel,traits_changed_from_input,energy_changed_from_input
            expected=expected_panel(screen.model,data)
            test.assertIsNotNone(initial_panel)
            traits_changed_from_input|=expected['descriptors']!=initial_panel['descriptors']
            energy_changed_from_input|=any(bytes.fromhex(raw)[14]!=initial_players[w][14] for w,raw in data['player_records'])
            test.assertTrue(screen.characteristics.panel==expected,'current traits differ from independent Core projection')
            test.assertTrue(screen.characteristics.cells.grid==characteristic_view(expected['descriptors']))
            words=list(data['eleven'])+list(data['bench'])
            test.assertEqual(len(words),20)
            test.assertEqual([w for w,_ in data['player_records']],words)
            test.assertTrue(all(screen.answer.live_records[w]==bytes.fromhex(raw) for w,raw in data['player_records']))
            if first_order is None:first_order=words
            else:changed_order|=words!=first_order
            if first_panel is None:first_panel=expected
            else:changed_traits|=expected!=first_panel
            observations.append(dict(label=label,context=screen.answer.context,minute=screen.answer.minute,
                records=20,members_sha256=digest(words),records_sha256=digest(data['player_records']),
                panel_sha256=digest(expected),cells_sha256=digest(screen.characteristics.cells.grid),
                injured_records=sum(bytes.fromhex(raw)[14]==0 for _,raw in data['player_records']),
                edited=bool(data.get('edited')),tactics=data['tactics'],core_equal=True))

        def refresh(screen):
            answer=screen.answer
            data=current_data.get(id(answer)) if answer is not None else None
            before=copy.deepcopy(screen.model.state)
            identities=tuple(id(v) for v in (screen.model.state,screen.model.state.players,screen.model.state.countries,screen.model.state.mem))
            result=real_refresh(screen)
            if data is not None:check(screen,data,'current-S10-refresh')
            test.assertTrue(screen.model.state==before,'trait read changed the career')
            test.assertEqual(tuple(id(v) for v in (screen.model.state,screen.model.state.players,screen.model.state.countries,screen.model.state.mem)),identities)
            return result

        def bench(day,pitch,decision):
            nonlocal initial_panel,initial_players
            if initial_panel is None:
                initial=day.controller.given._snapshot
                starters=list(initial.starting_eleven)
                words=starters+[w for w in initial.managed_squad if w not in starters]
                test.assertEqual(len(words),20)
                initial_players=list(initial.players)
                initial_data=dict(eleven=words[:11],bench=words[11:],tactics=initial.country_tactics,
                    player_records=[[w,initial_players[w].hex()] for w in words])
                initial_panel=expected_panel(SimpleNamespace(state=initial),initial_data)
            answer=real_bench(day,pitch,decision)
            current_data[id(answer)]=copy.deepcopy(decision.data)
            test.assertEqual(len(answer.live_records),20)
            before=copy.deepcopy(day.model.state);packet=copy.deepcopy(decision.data)
            events=digest(day.controller.events)
            frozen=(day.controller.bridge._frame_sequence,len(day.controller.choices),answer.minute,tuple(answer.score),answer.left)
            # An unshown observer constructs the REAL S10 panel at each actual
            # held boundary; it adds no navigation/answer/timer or engine operation.
            observer=TeamTacticsScreen(day.window,day.model,answer=answer,apply=lambda *args:None)
            try:check(observer,decision.data,'unshown-read-only-observer')
            finally:observer.deleteLater()
            test.assertTrue(day.model.state==before,'observer changed the career')
            test.assertEqual(decision.data,packet)
            test.assertEqual(digest(day.controller.events),events)
            test.assertEqual((day.controller.bridge._frame_sequence,len(day.controller.choices),answer.minute,tuple(answer.score),answer.left),frozen)
            return answer

        with mock.patch.object(TeamTacticsScreen,'refresh',refresh),mock.patch.object(MatchDay,'live_bench',bench):
            result=run_journey(self,'accept')
        self.assertTrue(observations)
        self.assertTrue(changed_order,'accepted actual swap must change the authoritative XI/bench order')
        self.assertTrue(changed_traits,'natural match/accepted swap must change current traits')
        self.assertTrue(any(row['edited'] for row in observations))
        self.assertTrue(traits_changed_from_input,'current descriptors/cells must differ from declared kickoff input')
        self.assertTrue(energy_changed_from_input,'natural current records must differ in energy from declared kickoff input')
        self.assertTrue(all(result[key] for key in ('result_equal','events_equal','memory_equal','career_equal')))
        print('ACTUAL_LIVE_TRAITS_641 '+json.dumps(dict(method='unchanged640actualrequest/tactic/swap inputs with fresh readonly panel observers',
            source_commit=result['source_commit'],observations=observations,record_checks=sum(r['records'] for r in observations),
            accepted_order_changed=changed_order,traits_changed_after_first_stop=changed_traits,
            traits_changed_vs_declared_kickoff_input=traits_changed_from_input,natural_energy_changed_vs_declared_kickoff_input=energy_changed_from_input,
            full_same_choice_result_events_rng_memory_career_equal=True,state_event_identity_unchanged=True,
            no_extra_input_seed_fixture_limit_or_event_projection=True),sort_keys=True),flush=True)

if __name__=='__main__':unittest.main()
