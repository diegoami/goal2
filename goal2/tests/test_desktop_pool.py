"""[designed: T71] Desktop's pool adapter preserves T45 identities and refusals."""
import copy
from dataclasses import replace
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from goal2.desktop.model import DesktopModel
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.worker import play
from goal2.game import campaign_pool
ROOT=Path(__file__).resolve().parents[2]

class DesktopPoolCases(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.model=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',Path(self.folder.name)/'game.g2save',country=4)
    def test_view_filters_are_pure_and_exchange_matches_t45_full_identity_repair(self):
        model=self.model;before=copy.deepcopy(model.state)
        view=model.pool_view();self.assertEqual(len(view['reserves']),80);self.assertEqual(len(view['squad']),20)
        row=next(r for r in view['reserves'] if r['id']==2561)
        filtered=model.pool_view(query=row['name'].swapcase(),position=row['position'])
        self.assertIn(row,filtered['reserves']);self.assertEqual(model.state,before)
        outgoing=model.state.starting_eleven[0]
        model.confirm(list(model.state.starting_eleven),outgoing,165)
        direct=copy.deepcopy(model.state);campaign_pool.exchange(direct,outgoing,2561)
        records=list(model.state.players);seeds=(model.state.rng_seed_7b62,model.state.rng_seed_8336)
        model.exchange(outgoing,2561);self.assertEqual(model.state,direct)
        self.assertEqual(model.state.players,records);self.assertEqual(model.state.captain,2561)
        self.assertIn(2561,model.state.starting_eleven);self.assertIn(outgoing,model.state.campaign.reserve_ids)
        self.assertEqual((model.state.rng_seed_7b62,model.state.rng_seed_8336),seeds)
        model.save(model.save_path)
        with patch('goal2.desktop.model.start_opening_campaign',side_effect=AssertionError('no regeneration')):model.resume(model.save_path)
        self.assertEqual(model.state,direct)
        model.state=play(model.state,model.template_bytes)
        transition=model.state.match_state['campaign_energy']['pool']
        self.assertEqual(transition['confidence_draws'],160)
        self.assertEqual(model.state.match_count,1)
        snapshot=copy.deepcopy(model.state);model.pool_view();model.view();self.assertEqual(model.state,snapshot)
    def test_invalid_unavailable_closed_and_validation_failure_are_atomic(self):
        model=self.model
        for out,inc in ((61,61),(True,2561),(61,99999),(2561,2562)):
            before=copy.deepcopy(model.state)
            with self.assertRaises(ValueError):model.exchange(out,inc)
            self.assertEqual(model.state,before)
        rec=bytearray(model.state.players[2561]);rec[14]=0;rec[16]=0x80;model.state.players[2561]=bytes(rec)
        before=copy.deepcopy(model.state)
        with self.assertRaisesRegex(ValueError,'unavailable'):model.exchange(61,2561)
        self.assertEqual(model.state,before)
        with patch.object(model,'view',side_effect=ValueError('candidate view failed')):
            with self.assertRaises(ValueError):model.exchange(61,2562)
        self.assertEqual(model.state,before)
        fs=model.state.campaign.fixtures
        model.state.campaign.fixtures=(replace(fs[0],away_country=33),replace(fs[1],home_country=4,away_country=34))+fs[2:]
        model.state.campaign.complete_fixture(fs[0].fixture_id)
        before=copy.deepcopy(model.state)
        self.assertFalse(model.pool_view()['window']['allowed'])
        with self.assertRaisesRegex(ValueError,'tour'):model.exchange(61,2562)
        self.assertEqual(model.state,before)
        model.new_friendly(4);before=copy.deepcopy(model.state)
        self.assertIsNone(model.pool_view())
        with self.assertRaisesRegex(ValueError,'campaign'):model.exchange(61,2562)
        self.assertEqual(model.state,before)
    def test_exchange_invalidates_inflight_candidate_without_publication(self):
        import time
        job=QuickJobs(self.model);self.addCleanup(job.cancel);job.start()
        self.model.exchange(61,2561);before=copy.deepcopy(self.model.state)
        with self.assertRaisesRegex(ValueError,'stale'):
            deadline=time.monotonic()+15
            while time.monotonic()<deadline:
                job.poll();time.sleep(.02)
            self.fail('worker did not finish')
        self.assertEqual(self.model.state,before)

if __name__=='__main__':unittest.main()
