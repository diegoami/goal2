"""[designed: owner#777/T231] Larger-squad metadata and supplied-score policy.

Synthetic scores test the new balance rule, not an original ability formula.
The real-career case reuses private original inputs and publishes no bytes.
"""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from goal2.game import extended_squad as extra
from goal2.game.session_save import encode,decode,SessionSaveError,SQUAD_VERSION
from goal2.tests.test_campaign_state import _save_state,CampaignCalendar
from goal2.tests.test_session_save import _state


def career():
    state=_save_state(CampaignCalendar().campaign())
    state.campaign.reserve_ids=list(range(2561,2641))
    return state


class Metadata(unittest.TestCase):
    def test_empty_capacities_and_private_resize(self):
        state=career();before=copy.deepcopy(state)
        for count in (20,22,24):
            with self.subTest(count=count):
                selected=extra.resized(state,count)
                self.assertEqual(selected.extra_squad,[None]*(count-20))
                self.assertEqual(len(extra.squad_slots(selected)),count)
                self.assertEqual(selected.managed_squad,state.managed_squad)
        self.assertEqual(state,before)

    def test_selected_members_are_removed_from_visible_pool_and_return_when_shrunk(self):
        state=extra.resized(career(),24);state.extra_squad=[2561,2562,2563,2564]
        self.assertEqual(len(extra.visible_pool(state)),76)
        small=extra.resized(state,22)
        self.assertEqual(small.extra_squad,[2561,2562])
        self.assertEqual(len(extra.visible_pool(small)),78)
        self.assertTrue({2563,2564}<=set(extra.visible_pool(small)))
        self.assertEqual(state.extra_squad,[2561,2562,2563,2564])

    def test_malformed_metadata_never_mutates_the_source(self):
        state=career();before=copy.deepcopy(state)
        bad=[{'capacity':True,'players':[]},{'capacity':21,'players':[None]},
             {'capacity':22,'players':[None]},{'capacity':22,'players':[0,None]},
             {'capacity':22,'players':[True,None]},{'capacity':22,'players':[3061,None]},
             {'capacity':22,'players':[121,None]},{'capacity':22,'players':[2561,2561]},
             {'capacity':22,'players':[2500,None]},{'capacity':22,'players':[None,None],'unknown':0}]
        for data in bad:
            with self.subTest(data=data):self.assertRaises(ValueError,extra.from_data,state,data)
            self.assertEqual(state,before)
        for count in (True,21,23,25,'24'):
            self.assertRaises(ValueError,extra.resized,state,count)


def candidate(word,line,strength,available=True):
    return dict(id=word,line=line,strength=strength,available=available)


class Balance(unittest.TestCase):
    def test_four_cover_all_outfield_groups_then_choose_strongest_remaining(self):
        rows=[candidate(1,0,256),candidate(2,1,90),candidate(3,1,89),
              candidate(4,2,80),candidate(5,3,70),candidate(6,3,256,False)]
        self.assertEqual(extra.balanced_extras(rows,4),[2,4,5,3])

    def test_two_choose_two_different_groups_with_stable_pool_order_ties(self):
        rows=[candidate(21,2,100),candidate(22,2,100),candidate(23,1,100),candidate(24,3,100)]
        self.assertEqual(extra.balanced_extras(rows,2),[21,23])
        self.assertEqual(rows[0]['id'],21)

    def test_missing_group_and_insufficient_players_leave_only_real_vacancies(self):
        rows=[candidate(1,1,5),candidate(2,1,4),candidate(3,3,3)]
        self.assertEqual(extra.balanced_extras(rows,4),[1,3,2,None])
        self.assertEqual(extra.balanced_extras([candidate(1,0,256)],2),[None,None])
        self.assertEqual(extra.balanced_extras([candidate(1,2,0)],2),[1,None])

    def test_malformed_candidate_scores_types_ids_and_counts_reject(self):
        bad=[[candidate(True,1,100)],[candidate(0,1,100)],[candidate(1,4,100)],
             [candidate(1,1,-1)],[candidate(1,1,257)],[candidate(1,1,True)],
             [candidate(1,1,100,1)],[candidate(1,1,100),candidate(1,2,99)],
             [dict(id=1,line=1,strength=100)]]
        for rows in bad:
            with self.subTest(rows=rows):self.assertRaises(ValueError,extra.balanced_extras,rows,2)
        for count in (True,1,3,5):self.assertRaises(ValueError,extra.balanced_extras,[],count)


class Saves(unittest.TestCase):
    def test_old_default_and_identity_formats_stay_unchanged(self):
        state=_state();plain=encode(state,b'template');doc=json.loads(plain)
        self.assertEqual(doc['version'],1);self.assertNotIn('extended_squad',doc['state'])
        state.squad_capacity=20;state.extra_squad=[]
        self.assertEqual(encode(state,b'template'),plain)
        state.manager_name='Zoe';named=json.loads(encode(state,b'template'))
        self.assertEqual(named['version'],4);self.assertNotIn('extended_squad',named['state'])
        loaded,_=decode(plain)
        self.assertEqual((loaded.squad_capacity,loaded.extra_squad),(20,[]))

    def test_empty_and_filled_larger_squads_roundtrip_all_members_and_names(self):
        for count in (22,24):
            for filled in (False,True):
                with self.subTest(count=count,filled=filled):
                    state=extra.resized(career(),count);state.manager_name='Zoe'
                    if filled:state.extra_squad=list(range(2561,2561+count-20))
                    raw=encode(state,b'template');self.assertEqual(json.loads(raw)['version'],SQUAD_VERSION)
                    loaded,template=decode(raw)
                    self.assertEqual(loaded,state);self.assertEqual(template,b'template')
                    self.assertEqual(encode(loaded,template),raw)

    def test_version_five_rejects_missing_unknown_and_bad_slot_data(self):
        base=json.loads(encode(extra.resized(career(),22),b'template'))
        for edit in ('missing','unknown','bad-slot','wrong-capacity','old-version'):
            doc=copy.deepcopy(base)
            if edit=='missing':del doc['state']['extended_squad']
            elif edit=='unknown':doc['state']['extended_squad']['unexpected']=1
            elif edit=='bad-slot':doc['state']['extended_squad']['players']=[121,None]
            elif edit=='wrong-capacity':doc['state']['extended_squad']['capacity']=20
            else:doc['version']=4
            with self.subTest(edit=edit):self.assertRaises(SessionSaveError,decode,json.dumps(doc).encode())

    def test_real_current_career_roundtrip_preserves_native_arrays_and_extra_words(self):
        from goal2.tests import requires
        requires.require(files=('e010-r0008-halftime.sav','GOAL.DAT'))
        from goal2.desktop.model import DesktopModel
        from goal2.game.campaign_pool import validate
        with tempfile.TemporaryDirectory() as temp:
            model=DesktopModel.open(requires.CACHE/'e010-r0008-halftime.sav',requires.CACHE/'GOAL.DAT',Path(temp)/'game',country=4)
            source=model.state;selected=extra.resized(source,24)
            selected.extra_squad=validate(selected)[:4]
            raw=encode(selected,model.template_bytes);loaded,_=decode(raw)
            self.assertEqual(loaded,selected)
            self.assertEqual(loaded.mem,source.mem)
            self.assertEqual(loaded.countries,source.countries)
            self.assertEqual(len(loaded.managed_squad),20)
