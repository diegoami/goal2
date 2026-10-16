"""[designed: T69] Direct Python desktop management and transactional saves."""
import copy
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from goal2.desktop.model import DesktopModel
from goal2.game.campaign_schedule import start_opening_campaign
from goal2.game.session_save import encode

ROOT=Path(__file__).resolve().parents[2]

class DesktopModelCases(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'desktop.g2save'
        self.model=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',self.path,country=4)
    def test_fresh_country_matches_direct_python_and_reads_are_pure(self):
        direct,_=start_opening_campaign(self.model.goaldat,self.model.template_bytes,managed_country=4,start_year=1990,seed_7b62=4660,seed_8336=33590)
        self.assertEqual(self.model.state,direct)
        before=copy.deepcopy(self.model.state)
        v=self.model.view()
        self.assertEqual(v['country_name'],self.model.goaldat.country_names[4])
        self.assertEqual(len(v['countries']),128)
        self.assertEqual([x['id'] for x in v['players']],self.model.state.managed_squad)
        self.assertEqual(self.model.state,before)
        self.model.new_campaign(13)
        self.assertEqual(self.model.state.managed_country,13)
        self.assertEqual(self.model.state.match_count,0)
    def test_confirm_full_ids_and_bits_is_atomic_and_rejects_unavailable(self):
        self.model.new_campaign(13)
        eleven=self.model.state.managed_squad[-11:];captain=eleven[-1]
        self.model.confirm(eleven,captain,255)
        self.assertEqual(self.model.state.starting_eleven,eleven)
        self.assertEqual(self.model.state.captain,260)
        self.assertEqual(self.model.state.country_tactics,255)
        for ids,cap,tactics in [(eleven[:-1],captain,1),([eleven[0]]*11,captain,1),(eleven,999,1),(eleven,captain,256),(eleven,captain,True)]:
            before=copy.deepcopy(self.model.state)
            with self.assertRaises(ValueError):self.model.confirm(ids,cap,tactics)
            self.assertEqual(self.model.state,before)
        rec=bytearray(self.model.state.players[eleven[0]]);rec[14]=0;self.model.state.players[eleven[0]]=bytes(rec)
        before=copy.deepcopy(self.model.state)
        with self.assertRaisesRegex(ValueError,'unavailable'):self.model.confirm(eleven,captain,0)
        self.assertEqual(self.model.state,before)
        self.assertFalse(self.model.view()['players'][-11]['availability']['available'])
    def test_save_resume_preserves_complete_state_without_regeneration_and_rejects_bad_input(self):
        eleven=self.model.state.managed_squad[-11:]
        self.model.confirm(eleven,eleven[0],165)
        self.model.save(self.path)
        before=copy.deepcopy(self.model.state)
        self.model.new_campaign(13)
        with patch('goal2.desktop.model.start_opening_campaign',side_effect=AssertionError('must not regenerate')):
            self.model.resume(self.path)
        self.assertEqual(self.model.state,before)
        good=self.path.read_bytes()
        self.path.write_bytes(b'bad save')
        with self.assertRaises(ValueError):self.model.resume(self.path)
        self.assertEqual(self.model.state,before)
        self.path.write_bytes(good)
        with patch('goal2.desktop.model.to_savestate',side_effect=ValueError('bad continuation')):
            with self.assertRaisesRegex(ValueError,'bad continuation'):self.model.resume(self.path)
        self.assertEqual(self.model.state,before)
        self.assertEqual(self.path.read_bytes(),good)
        missing=Path(self.folder.name)/'missing.sav'
        with self.assertRaises(ValueError):DesktopModel.open(missing,ROOT/'.cache/GOAL.DAT',self.path)
    def test_malformed_local_template_is_readable_and_never_published(self):
        bad=Path(self.folder.name)/'bad.sav';bad.write_bytes(b'not a zip')
        with self.assertRaisesRegex(ValueError,'Cannot open'):DesktopModel.open(bad,ROOT/'.cache/GOAL.DAT',self.path)
        before=copy.deepcopy(self.model.state)
        bad.write_bytes(encode(self.model.state,b'not a zip'))
        with self.assertRaisesRegex(ValueError,'Cannot resume'):self.model.resume(bad)
        self.assertEqual(self.model.state,before)

    def test_save_failure_and_invalid_new_country_keep_active_state(self):
        before=copy.deepcopy(self.model.state)
        for country in (True,0,129):
            with self.assertRaises(ValueError):self.model.new_campaign(country)
            self.assertEqual(self.model.state,before)
        blocked=Path(self.folder.name)/'not-a-directory';blocked.write_text('blocked')
        with self.assertRaises(ValueError):self.model.save(blocked/'save.g2save')
        self.assertEqual(self.model.state,before)

if __name__=='__main__':unittest.main()
