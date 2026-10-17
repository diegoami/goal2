"""[designed: T49] Behavioral fixtures for F023's source table rules and pure reads."""
import copy
from pathlib import Path
import unittest
from unittest.mock import patch
from goal2.game.standings import TableFixture, group_table, opening_group


def fixture(i,a,b,kind=2):return TableFixture(str(i),kind,a,b)
def score(i,a,b,x,y):return {'fixture_id':str(i),'teams':[a,b],'score':[x,y]}


class Standings(unittest.TestCase):
    def table(self,fixtures,results,slots=(1,2,3,4),stage=2,places=1):
        return group_table(slots,fixtures,results,stage=stage,places=places)

    def test_points_win_draw_loss_and_stage_filter(self):
        fs=[fixture(1,1,2),fixture(2,3,4),fixture(3,1,3,1)]
        rs=[score(1,1,2,0,0),score(2,3,4,1,0),score(3,1,3,99,0)]
        rows=self.table(fs,rs);self.assertEqual([r.country for r in rows], [3,2,1,4])
        by={r.country:r for r in rows}
        self.assertEqual((by[3].played,by[3].won,by[3].drawn,by[3].lost,by[3].points),(1,1,0,0,2))
        self.assertEqual((by[1].played,by[1].drawn,by[1].points,by[1].goals_for),(1,1,1,0))
        self.assertEqual((by[4].lost,by[4].points),(1,0))
        self.assertEqual([r.country for r in rows if r.advances],[3])

    def test_goal_difference_then_goals_scored(self):
        fs=[fixture(1,1,2),fixture(2,3,4)]
        rows=self.table(fs,[score(1,1,2,2,0),score(2,3,4,1,0)])
        self.assertEqual([r.country for r in rows],[1,3,4,2])
        rows=self.table(fs,[score(1,1,2,2,1),score(2,3,4,1,0)])
        self.assertEqual([r.country for r in rows],[1,3,2,4])
        self.assertEqual([(r.points,r.goal_difference) for r in rows[:2]],[(2,1),(2,1)])

    def test_all_equal_and_indirect_exchange_order_is_retained(self):
        rows=self.table([],[],slots=(4,3,2,1),places=2)
        self.assertEqual([r.country for r in rows],[4,3,2,1])
        fs=[fixture(1,3,4),fixture(2,1,2)]
        rows=self.table(fs,[score(1,3,4,1,0),score(2,1,2,0,0)])
        self.assertEqual([r.country for r in rows],[3,2,1,4])

    def test_results_arrival_order_is_irrelevant_and_reads_are_pure(self):
        fs=[fixture(1,3,4),fixture(2,1,2),fixture(3,1,3)]
        rs=[score(1,3,4,1,0),score(2,1,2,0,0),score(3,1,3,1,0)]
        before=copy.deepcopy((fs,rs))
        self.assertEqual(self.table(fs,rs),self.table(fs,list(reversed(rs))))
        self.assertEqual((fs,rs),before)
        tied_fixtures=[fixture(1,3,4),fixture(2,1,2)]
        tied_results=[score(1,3,4,0,0),score(2,1,2,0,0)]
        self.assertEqual([r.country for r in self.table(tied_fixtures,tied_results)],[3,4,1,2])
        self.assertEqual(self.table(tied_fixtures,tied_results),self.table(tied_fixtures,list(reversed(tied_results))))
        # [confirmed: F023] No ID-based tiebreak even for arbitrary participant identities.
        self.assertEqual([r.country for r in self.table([],[],slots=(40,30,20,10))],[40,30,20,10])

    def test_byte_goal_counters_and_supported_stage_kinds(self):
        for stage in (2,3,5,7):
            fs=[fixture(1,1,2,stage),fixture(2,1,3,stage)]
            rows=self.table(fs,[score(1,1,2,250,0),score(2,1,3,10,0)],stage=stage)
            one=next(r for r in rows if r.country==1)
            self.assertEqual((one.goals_for,one.points),(4,4))

    def test_replay_malformed_and_wrong_endpoint_rejection(self):
        fs=[fixture(1,1,2)];rs=[score(1,1,2,1,0)]
        for bad in (rs+rs,[score(2,1,2,1,0)],[score(1,2,1,1,0)],
                    [score(1,1,2,-1,0)],[score(1,1,2,True,0)]):
            with self.assertRaises(ValueError):self.table(fs,bad)
        for slots in ((1,1,2,3),(1,2,3),(True,2,3,4)):
            with self.assertRaises(ValueError):self.table([],[],slots=slots)
        with self.assertRaises(ValueError):self.table(fs+fs,rs)

    def test_opening_group_recovers_saved_source_slots_without_rng(self):
        from goal2.desktop.model import DesktopModel
        from goal2.game.campaign_schedule import build_opening_campaign
        root=Path(__file__).resolve().parents[2]
        model=DesktopModel.open(root/'.cache/e010-r0008-halftime.sav',root/'.cache/GOAL.DAT',root/'.cache/unused-standings.g2save',country=4)
        for start in (1990,1992):
            from goal2.game.campaign_schedule import start_opening_campaign
            model.state,opening=start_opening_campaign(model.goaldat,model.template_bytes,managed_country=4,start_year=start,seed_7b62=4660,seed_8336=33590)
            wanted=next(g for g in opening.groups if 4 in g.countries_by_slot)
            before=copy.deepcopy(model.state)
            with patch('goal2.engine.quick_engine.LCG.rand',side_effect=AssertionError('table reads must not draw')):
                got=opening_group(model.state,model.template_bytes)
                view=model.competition_table()
            self.assertEqual(got['slots'],wanted.countries_by_slot)
            self.assertEqual((got['continent'],got['group']),(wanted.continent,wanted.group))
            self.assertEqual([r['country'] for r in view['rows']],list(wanted.countries_by_slot))
            self.assertEqual(model.state,before)
        model.state.campaign.world=None
        self.assertIsNone(opening_group(model.state,model.template_bytes))
        self.assertIsNone(model.competition_table())

if __name__=='__main__':unittest.main()
