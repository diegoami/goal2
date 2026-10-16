"""[designed: T45] National-pool identity, views, windows and persistence."""
import copy
import json
import unittest
from dataclasses import replace
from pathlib import Path
from goal2.game import campaign_pool as pool
from goal2.game.session_save import encode, decode, SessionSaveError
from goal2.web.server import WebSession

ROOT = Path(__file__).resolve().parents[2]

class PoolCases(unittest.TestCase):
    def setUp(self):
        self.session = WebSession.load(ROOT/'.cache/e010-r0008-halftime.sav', ROOT/'.cache/GOAL.DAT')
        self.session.new_campaign({'country':4,'start_year':1990,'seed_7b62':4660,'seed_8336':33590})
        self.state = self.session.state
    def test_generated_identities_names_filter_position_order_and_read_purity(self):
        before=copy.deepcopy(self.state)
        view=pool.view(self.state,self.session.goaldat)
        self.assertEqual(len(view['squad']),20)
        self.assertEqual(len(view['reserves']),80)
        self.assertEqual(set(x['id'] for x in view['reserves']),set(range(2561,2641)))
        self.assertTrue(all(x['name']==self.session.goaldat.player_names[x['id']] for x in view['reserves']))
        self.assertEqual([(x['position'],x['id']) for x in view['reserves']],sorted((x['position'],x['id']) for x in view['reserves']))
        row=view['reserves'][0]
        filtered=pool.view(self.state,self.session.goaldat,query=row['name'],position=row['position'])
        self.assertIn(row,filtered['reserves'])
        self.assertTrue(all(row['name'].casefold() in x['name'].casefold() and x['position']==row['position'] for x in filtered['reserves']))
        self.assertEqual(self.state,before)
    def test_exchange_preserves_records_full_ids_xi_captain_country_words_and_roundtrip(self):
        out=self.state.starting_eleven[0]; incoming=2561
        self.state.captain=out
        records=list(self.state.players)
        pool.exchange(self.state,out,incoming)
        self.assertEqual(self.state.players,records)
        self.assertIn(incoming,self.state.starting_eleven)
        self.assertEqual(self.state.captain,incoming)
        self.assertEqual(self.state.campaign.reserve_ids[0],out)
        self.assertEqual(int.from_bytes(self.state.countries[4][:2],'little'),incoming)
        raw=encode(self.state,self.session.template_bytes)
        self.assertEqual(json.loads(raw)['state']['campaign']['reserve_ids'],self.state.campaign.reserve_ids)
        resumed,_=decode(raw)
        self.assertEqual(resumed,self.state)
        pool.exchange(resumed,incoming,out)
        self.assertEqual(resumed.managed_squad,list(range(61,81)))
        self.assertEqual(resumed.campaign.reserve_ids,list(range(2561,2641)))
    def test_bad_ids_unavailable_foreign_duplicate_overlap_and_counts_reject_atomically(self):
        for out,inc in [(61,True),(True,2561),(61,61),(2561,2562),(61,99999)]:
            before=copy.deepcopy(self.state)
            with self.assertRaises(ValueError):pool.exchange(self.state,out,inc)
            self.assertEqual(self.state,before)
        for field,value in [('country',33),('energy',0),('status',128)]:
            candidate=copy.deepcopy(self.state);rec=bytearray(candidate.players[2561]);rec[{'country':0,'energy':14,'status':16}[field]]=value;candidate.players[2561]=bytes(rec)
            before=copy.deepcopy(candidate)
            with self.assertRaises(ValueError):pool.exchange(candidate,61,2561)
            self.assertEqual(candidate,before)
        for reserves in ([2561]*80,list(range(2561,2640)),[61]+list(range(2562,2641))):
            candidate=copy.deepcopy(self.state);candidate.campaign.reserve_ids=reserves
            with self.assertRaises(ValueError):pool.validate(candidate)
    def test_legacy_canonical_save_infers_only_membership_and_invalid_pool_save_rejects(self):
        doc=json.loads(encode(self.state,self.session.template_bytes))
        del doc['state']['campaign']['reserve_ids']
        resumed,_=decode(json.dumps(doc).encode())
        self.assertEqual(resumed,self.state)
        doc['state']['campaign']['reserve_ids']=[2561]*80
        with self.assertRaises(SessionSaveError):decode(json.dumps(doc).encode())
        pool.exchange(self.state,61,2561)
        doc=json.loads(encode(self.state,self.session.template_bytes));del doc['state']['campaign']['reserve_ids']
        with self.assertRaises(SessionSaveError):decode(json.dumps(doc).encode())
    def test_provisional_window_tour_competitive_exhausted_and_standalone(self):
        self.assertTrue(pool.window(self.state)['allowed'])
        fixtures=self.state.campaign.fixtures
        self.state.campaign.fixtures=(replace(fixtures[0],away_country=33),replace(fixtures[1],away_country=34))+fixtures[2:]
        self.state.campaign.complete_fixture(fixtures[0].fixture_id)
        self.assertFalse(pool.window(self.state)['allowed'])
        before=copy.deepcopy(self.state)
        with self.assertRaises(ValueError):pool.exchange(self.state,61,2561)
        self.assertEqual(self.state,before)
        self.state.campaign.completed_fixture_ids=[x.fixture_id for x in self.state.campaign.fixtures[:2]]
        self.assertFalse(pool.window(self.state)['allowed'])
        self.state.campaign.fixtures=self.state.campaign.fixtures[:2]
        self.assertFalse(pool.window(self.state)['allowed'])
        self.state.campaign=None
        with self.assertRaises(ValueError):pool.validate(self.state)

if __name__=='__main__':unittest.main()
