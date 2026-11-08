"""#646 extends641's unchanged actual640 journey with full read-only TEAM checks."""
import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest import mock
from goal2.tests import requires


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()


@requires.need(modules=('PySide6','pygame'),slow=True,**requires.HALFTIME)
class ActualTeamLayout(unittest.TestCase):
    def test_existing_actual_journey_retains_full_current_team_panels_and_all_outcome_oracles(self):
        from goal2.ui.s10_team_tactics import TeamTacticsScreen
        from goal2.tests.test_live_team_context_646 import LiveTeamContext
        from goal2.tests.test_live_tactics_worker_641 import ActualLiveTraits
        original_refresh=TeamTacticsScreen.refresh
        observations=[];errors=[]
        private=os.environ.get('GOAL2_646_PRIVATE_PACKETS')
        if private:
            private=Path(private)
            self.assertFalse(private.exists(),'immutable observation output already exists')
            private.parent.mkdir(parents=True,exist_ok=True)

        def inspect(screen):
            answer=screen.answer
            self.assertEqual(len(answer.live_records),20)
            self.assertIsNotNone(answer.team_context,'missing authoritative live TEAM context')
            words=list(answer.words())
            data=dict(eleven=words[:len(answer.eleven)],bench=words[len(answer.eleven):],
                tactics=answer.team_tactics,team_context={**answer.team_context,'sides':list(answer.team_context['sides'])},
                player_records=[[word,answer.live_records[word].hex()] for word in words])
            expected=LiveTeamContext.expected(self,screen.model,data)
            self.assertEqual(screen.skills.panel,expected['team_skills'])
            self.assertEqual(screen.performance.panel,expected['performance'])
            self.assertEqual(screen.performance.isHidden(),expected['performance'] is None)
            self.assertEqual(screen.characteristics.panel,expected['characteristics'])
            self.assertEqual({key:label.text() for key,label in screen.averages.values.items()},
                             {row['field']:row['text'] for row in expected['characteristics']['numbers']})
            record=screen.model.state.countries[screen.model.state.managed_country]
            for field,offset in (('world',0x2B),('continental',0x2A),('top_world',0x29),('top_continental',0x28)):
                self.assertEqual(screen.team_header.ranks[field].text(),str(record[offset]))
            self.assertEqual(len(screen.strip.shown_texts()),20)
            row=dict(context=answer.context,minute=answer.minute,records=20,
                words_sha256=digest(words),records_sha256=digest(data['player_records']),
                team_context=data['team_context'],panels_sha256=digest(expected),
                skills_sha256=digest(expected['team_skills']),performance_sha256=digest(expected['performance']),
                original_projection_equal=True)
            observations.append(row)
            if private:
                with private.open('a',encoding='utf8') as output:
                    output.write(json.dumps(dict(observation=row,data=data),sort_keys=True)+'\n')

        def refresh(screen):
            result=original_refresh(screen)
            if screen.answer is not None:
                # Do not throw an assertion through Qt and strand its event loop.
                # Collect observer failures; the normal journey keeps its inputs
                # and complete assertions, then this test reports the failures.
                try:inspect(screen)
                except Exception as error:errors.append(f'{type(error).__name__}: {error}')
            return result

        with mock.patch.object(TeamTacticsScreen,'refresh',refresh):
            ActualLiveTraits.test_unchanged640request_swap_and_tactic_journey_exposes_current_traits_without_state_writes(self)
        self.assertFalse(errors,errors)
        self.assertTrue(observations)
        self.assertTrue(any(row['context']=='pause' for row in observations))
        self.assertTrue(any(row['context']=='half_time' for row in observations))
        self.assertGreater(len({row['words_sha256'] for row in observations}),1)
        self.assertGreater(len({row['performance_sha256'] for row in observations}),1)
        print('ACTUAL_TEAM_LAYOUT_646 '+json.dumps(dict(observations=observations,
            independent_current_panels_equal=True,all_existing_641_and_640_assertions_retained=True,
            no_new_answer_seed_fixture_limit_or_result_projection=True),sort_keys=True),flush=True)
