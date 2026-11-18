"""[designed: owner#777/T233] Selected extras are members, vacancies are slots."""
import copy,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from goal2.tests import requires
from goal2.tests.test_assistant_pipe_t183c import model
from goal2.game import extended_squad as extended,campaign_pool


@requires.need(**requires.HALFTIME)
class Management(unittest.TestCase):
    def setUp(self):self.model=model()

    def filled(self,capacity=24,count=None):
        m=self.model;m.resize_squad(capacity)
        words=campaign_pool.validate(m.state)[:capacity-20 if count is None else count]
        for index,word in enumerate(words):
            record=bytearray(m.state.players[word]);record[14]=100;record[16]&=~0xA4
            m.state.players[word]=bytes(record)
            m.fill_extra(index,word)
        return words

    def coherent(self):
        state=self.model.state;pool=campaign_pool.validate(state);extended.validate(state)
        self.assertEqual(len(state.managed_squad),20);self.assertEqual(len(pool),80)
        self.assertEqual(len(set(state.managed_squad+pool)),100)

    def test_nullable_capacity_views_and_search_are_pure(self):
        m=self.model;default=m.view();before=copy.deepcopy(m.state)
        m.resize_squad(20);self.assertEqual(m.state,before);self.assertEqual(m.view(),default)
        for capacity in (22,24):
            m.resize_squad(capacity);before=copy.deepcopy(m.state)
            self.assertEqual(m.state.extra_squad,[None]*(capacity-20))
            v=m.view();self.assertEqual(v['squad_capacity'],capacity)
            self.assertEqual(v['squad_slots'],m.state.managed_squad+[None]*(capacity-20))
            self.assertEqual(len(v['players']),20);m.pool_view();self.assertEqual(m.state,before)
        words=self.filled(count=3);before=copy.deepcopy(m.state)
        v=m.view();self.assertEqual(len(v['players']),23)
        self.assertEqual(v['squad_slots'][-4:],words+[None])
        pool=m.pool_view();self.assertEqual(len(pool['reserves']),77);self.assertEqual(len(pool['squad']),23)
        self.assertFalse(set(words)&{r['id'] for r in pool['reserves']})
        for word in words:
            row=next(r for r in pool['squad'] if r['id']==word)
            self.assertNotIn(word,{r['id'] for r in m.pool_view(query=row['name'],position=row['position'])['reserves']})
        self.assertEqual(m.state,before);self.coherent()

    def test_selected_extra_swaps_preserve_membership_records_rng_and_captain(self):
        m=self.model;words=self.filled();state=m.state
        captain=state.starting_eleven[0];state.captain=captain
        members=set(state.managed_squad+words);records=list(state.players)
        seeds=(state.rng_seed_7b62,state.rng_seed_8336)
        # A selected player remains selectable when outside recruitment closes.
        with patch.object(campaign_pool,'window',return_value={'allowed':False,'reason':'controlled closed window'}):
            m.swap(captain,words[0])
            self.assertEqual(m.state.captain,words[0]);self.assertIn(words[0],m.state.starting_eleven)
            self.assertEqual(m.state.extra_squad[0],captain)
            self.coherent();self.assertEqual(set(extended.squad_slots(m.state)),members)
            m.swap(words[0],captain)
        self.assertEqual(m.state.players,records);self.assertEqual((m.state.rng_seed_7b62,m.state.rng_seed_8336),seeds)
        self.assertEqual(set(extended.squad_slots(m.state)),members);self.assertEqual(m.state.captain,captain)

    def test_extra_outside_exchange_and_shrinking_preserve_native_arrays(self):
        m=self.model;words=self.filled()
        incoming=next(r['id'] for r in m.pool_view()['reserves'] if r['availability']['available'])
        native=list(m.state.managed_squad);pool=list(m.state.campaign.reserve_ids)
        m.exchange(words[-1],incoming)
        self.assertEqual(m.state.extra_squad[-1],incoming)
        self.assertEqual(m.state.managed_squad,native);self.assertEqual(m.state.campaign.reserve_ids,pool)
        self.assertIn(words[-1],{r['id'] for r in m.pool_view()['reserves']})
        m.resize_squad(22);self.assertEqual(m.state.extra_squad,words[:2]);self.coherent()
        m.resize_squad(24);self.assertEqual(m.state.extra_squad,words[:2]+[None,None])
        m.resize_squad(20);self.assertEqual(m.state.extra_squad,[])
        self.assertNotIn('squad_capacity',m.view());self.coherent()

    def test_invalid_slots_words_windows_and_validation_fail_atomically(self):
        m=self.model;m.resize_squad(22)
        for capacity in (True,21,23,'24'):
            before=copy.deepcopy(m.state)
            self.assertRaises(ValueError,m.resize_squad,capacity);self.assertEqual(m.state,before)
        pool=campaign_pool.validate(m.state)
        for slot,word in ((True,pool[0]),(-1,pool[0]),(2,pool[0]),(0,True),(0,3061),(0,m.state.managed_squad[0])):
            before=copy.deepcopy(m.state)
            self.assertRaises(ValueError,m.fill_extra,slot,word);self.assertEqual(m.state,before)
        with patch.object(campaign_pool,'window',return_value={'allowed':False,'reason':'controlled closed window'}):
            before=copy.deepcopy(m.state);self.assertRaisesRegex(ValueError,'closed',m.fill_extra,0,pool[0]);self.assertEqual(m.state,before)
        record=bytearray(m.state.players[pool[0]]);record[14]=0;m.state.players[pool[0]]=bytes(record)
        before=copy.deepcopy(m.state);self.assertRaisesRegex(ValueError,'unavailable',m.fill_extra,0,pool[0]);self.assertEqual(m.state,before)
        words=self.filled(22)
        for operation,args in ((m.fill_extra,(1,words[0])),(m.exchange,(words[0],words[1])),(m.swap,(words[0],words[1]))):
            before=copy.deepcopy(m.state);self.assertRaises(ValueError,operation,*args);self.assertEqual(m.state,before)
        before=copy.deepcopy(m.state)
        with patch.object(m,'view',side_effect=ValueError('candidate rejected')):
            self.assertRaisesRegex(ValueError,'candidate',m.swap,m.state.starting_eleven[0],words[0])
        self.assertEqual(m.state,before)

    def test_real_save_reload_preserves_partial_slots_and_selected_promotions(self):
        m=self.model;words=self.filled(count=2);m.swap(m.state.starting_eleven[2],words[0]);before=copy.deepcopy(m.state)
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'expanded.g2save';m.save(path);m.resize_squad(20)
            with patch('goal2.desktop.model.start_opening_campaign',side_effect=AssertionError('no regeneration')):m.resume(path)
        self.assertEqual(m.state,before);self.assertEqual(m.state.extra_squad[-2:],[None,None]);self.coherent()
