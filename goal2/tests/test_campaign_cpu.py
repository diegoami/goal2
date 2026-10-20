"""[designed: T46] CPU stand-in correction and actual campaign setup boundaries."""
import copy
from dataclasses import replace
from pathlib import Path
import unittest
from unittest.mock import patch
from goal2.ai.cpu import pick_computer_eleven
from goal2.game.computer import prepare
from goal2.game.quick_match import resolve_full_matchup,run_full_match
from goal2.game.state import to_savestate
from goal2.game.session_save import encode,decode
from goal2.engine.quick_engine import QuickMatch
from goal2.engine.savestate import Savestate
from goal2.web.server import WebSession
from goal2.tests import requires
ROOT=Path(__file__).resolve().parents[2]

@requires.need(**requires.HALFTIME)
class CampaignCPU(unittest.TestCase):
    def setUp(self):
        self.session=WebSession.load(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT')
        self.session.new_campaign({'country':4,'start_year':1990,'seed_7b62':4660,'seed_8336':33590})
    def test_literal_ability_is_not_age_and_ties_use_full_id(self):
        records=[bytes(20)]
        for i in range(1,21):
            r=bytearray(20);r[1]=16 if i<=11 else 40;r[4]=99 if i<=11 else 1;records.append(bytes(r))
        self.assertEqual(pick_computer_eleven(records,list(range(1,21))),list(range(1,12)))
        for i in range(1,21):
            r=bytearray(records[i]);r[4]=99;records[i]=bytes(r)
        self.assertEqual(pick_computer_eleven(records,list(range(20,0,-1))),list(range(1,12)))
    def test_pure_preparation_filters_unavailable_ability_not_age_and_preserves_all_state(self):
        state=self.session.state
        for i in range(1,21):
            r=bytearray(state.players[i]);r[1]=16 if i<=11 else 40;r[4]=99 if i<=11 else 1;r[14]=16;r[16]=0;state.players[i]=bytes(r)
        r=bytearray(state.players[1]);r[14]=0;state.players[1]=bytes(r)
        before=copy.deepcopy(state);result=prepare(state,1)
        self.assertEqual(result['eleven'],tuple(range(2,13)))
        self.assertEqual(result['squad'],tuple(range(2,13))+(1,)+tuple(range(13,21)))
        self.assertEqual(result['tactics'],state.countries[1][45])
        self.assertEqual(state,before)
    def test_malformed_squad_foreign_players_human_side_and_too_few_reject(self):
        state=self.session.state
        with self.assertRaisesRegex(ValueError,'human'):prepare(state,4)
        for slot,word in ((1,1),(0,0),(0,2561)):
            candidate=copy.deepcopy(state);r=bytearray(candidate.countries[1]);r[slot*2:slot*2+2]=word.to_bytes(2,'little');candidate.countries[1]=bytes(r)
            before=copy.deepcopy(candidate)
            with self.assertRaises(ValueError):prepare(candidate,1)
            template=Savestate(to_savestate(candidate,original=self.session.template_bytes))
            with self.assertRaises(ValueError):resolve_full_matchup(template,candidate)
            self.assertEqual(candidate,before)
        for i in range(1,11):
            r=bytearray(state.players[i]);r[14]=0;state.players[i]=bytes(r)
        with self.assertRaisesRegex(ValueError,'opponent'):prepare(state,1)
    def test_runner_and_preview_use_current_opponent_for_both_managed_sides(self):
        for side in (0,1):
            state=copy.deepcopy(self.session.state)
            if side:state.campaign.complete_fixture(state.campaign.fixtures[0].fixture_id)
            f=state.campaign.next_fixture;opponent=f.side_b if side==0 else f.side_a
            own=(list(state.starting_eleven),state.captain,state.country_tactics)
            expected=prepare(state,opponent);before=copy.deepcopy(state)
            template=Savestate(to_savestate(state,original=self.session.template_bytes))
            self.assertEqual(resolve_full_matchup(template,state),((f.side_a,f.side_b),side,opponent))
            seen=[]
            def inspect(qm,minute,countdown):
                if minute==0:
                    seen.append((tuple(qm.teams),tuple(qm._country(opponent)['squad']),qm._country(opponent)['tactics'],qm._country(opponent)['managed']))
                    self.assertEqual([qm.pitch[qm.side_base[side]+i]['player'] for i in range(1,12)],own[0])
                    self.assertEqual(qm._country(4)['tactics'],own[2])
                    self.assertEqual([qm.pitch[qm.side_base[1-side]+i]['player'] for i in range(1,12)],list(expected['eleven']))
            with patch.object(QuickMatch,'d733',inspect):run_full_match(template,state)
            self.assertEqual(seen,[((f.side_a,f.side_b),expected['squad'],expected['tactics'],opponent)])
            self.assertEqual(state,before)
    def test_match_local_tactics_do_not_overwrite_stored_next_setup(self):
        state=self.session.state;country=bytearray(state.countries[1]);country[45]=165;state.countries[1]=bytes(country)
        raw=Savestate(to_savestate(state,original=self.session.template_bytes));starts=[]
        def inspect(qm,minute,countdown):
            if minute==0:starts.append(qm._country(1)['tactics'])
            qm._country(1)['tactics']=90
        before=bytes(state.countries[1])
        with patch.object(QuickMatch,'d733',inspect):run_full_match(raw,state,retain_state=True)
        self.assertEqual(starts,[165]);self.assertEqual(state.countries[1],before)
        self.assertEqual(prepare(state,1)['tactics'],165)
    def test_real_saved_and_uninterrupted_preparation_and_two_matches_match(self):
        state,raw=decode(encode(self.session.state,self.session.template_bytes))
        other=WebSession(state,self.session.goaldat,Savestate(raw),raw)
        for _ in range(2):
            for session in (self.session,other):
                f=session.state.campaign.next_fixture;opponent=f.side_b if f.side_a==4 else f.side_a
                session.prepared=prepare(session.state,opponent)
                v=session.view();session.play({'play_token':v['play_token'],'fixture_id':f.fixture_id})
            self.assertEqual(self.session.prepared,other.prepared)
            self.assertEqual(self.session.state,other.state)

if __name__=='__main__':unittest.main()
