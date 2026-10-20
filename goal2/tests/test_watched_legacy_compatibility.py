"""[designed: T51a] Genuine pre-upgrade kit1 v3 saves, then real kit2 and quick continuation."""
import copy
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import unittest
from goal2.engine.original_match import Fixture,Image
from goal2.game import session_save
from goal2.game.eligibility import available_words
from goal2.game.watched_match import run_watched_match
from goal2.game.watched_publication import WatchedPublication
from goal2.game.watched_schema import LEGACY_ENGINE_ID,ENGINE_ID
from goal2.tests.test_watched_publication import Owner
from goal2.tests.test_watched_adapter import direct
from goal2.tests import requires

ROOT=Path(__file__).resolve().parents[2]
SOURCE='9fb725ac914afabfdaa830198fc3a514c87c243f'
FOLDER=ROOT/'.cache'/('watched-legacy-v3-'+SOURCE[:12])


class LegacyCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence=json.loads((ROOT/'docs/evidence/T51a-watched-kit.json').read_text())['legacy']
        requires.require(**requires.WATCHED)
        requires.require(generated={FOLDER.name+'/manifest.json':'python3 tools/export_watched_legacy.py --source '+SOURCE})
        cls.manifest=json.loads((FOLDER/'manifest.json').read_text())
        if cls.manifest!=cls.evidence:raise AssertionError('legacy input/output/source evidence differs')

    def saved(self,name):
        raw=(FOLDER/(name+'.g2save')).read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(),self.evidence['saves'][name])
        self.assertEqual(json.loads(raw)['version'],3)
        state,template=session_save.decode(raw)
        self.assertEqual(state.last_match['engine'],LEGACY_ENGINE_ID)
        self.assertEqual(state.last_match['original']['kit'],'1')
        return raw,state,template

    def select(self,state):
        state=copy.deepcopy(state)
        state.starting_eleven=available_words(state.players,state.managed_squad)[:11]
        state.captain=state.starting_eleven[0]
        return state

    def test_real_legacy_saves_roundtrip_without_relabeling_or_memory_rng_changes(self):
        for name in ('standalone','campaign'):
            with self.subTest(name=name):
                raw,state,template=self.saved(name)
                self.assertEqual(session_save.encode(state,template),raw)
                restored,restored_template=session_save.decode(session_save.encode(state,template))
                self.assertEqual(restored,state);self.assertEqual(restored_template,template)
                self.assertEqual(restored.mem,state.mem)
                self.assertEqual((restored.rng_seed_7b62,restored.rng_seed_8336),
                                 (state.rng_seed_7b62,state.rng_seed_8336))
                if state.campaign:
                    self.assertEqual(state.campaign.results[0]['engine'],LEGACY_ENGINE_ID)
                for engine in ('unknown',ENGINE_ID):
                    damaged=json.loads(raw);damaged['state']['last_match']['engine']=engine
                    before=copy.deepcopy(state)
                    with self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(damaged).encode())
                    self.assertEqual(state,before)

    def test_legacy_campaign_continues_with_current_kit_then_mixed_quick_history(self):
        from goal2.desktop.worker import play
        raw,state,template=self.saved('campaign')
        old_history=copy.deepcopy(state.campaign.results)
        owner=Owner(self.select(state),template);pub=WatchedPublication(owner)
        pending=owner.state.campaign.next_fixture
        fixture=Fixture(pending.side_a,pending.side_b,int(pending.fixture_id.split(':')[1]))
        job=pub.begin(fixture)
        expected,memory,events=direct(job.state,fixture)
        outcome=run_watched_match(job.state,template,fixture,record_draws=True)
        self.assertEqual(outcome.result,expected);self.assertEqual(outcome.memory,memory)
        self.assertEqual([asdict(event) for event in outcome.events],events)
        pub.complete(job.token,outcome)
        self.assertEqual(owner.state.campaign.results[:-1],old_history)
        self.assertEqual([row['engine'] for row in owner.state.campaign.results],[LEGACY_ENGINE_ID,ENGINE_ID])
        self.assertEqual(owner.state.last_match['original']['kit'],'2')
        self.assertEqual(owner.state.last_match['engine'],ENGINE_ID)
        self.assertEqual(owner.state.mem,memory)
        after=Image(memory)
        self.assertEqual(owner.state.rng_seed_7b62,owner.state.campaign.world.results[-1]['seed_after'])
        self.assertEqual(owner.state.rng_seed_8336,outcome.seeds[1])
        self.assertEqual(owner.state.last_match['seeds'],list(outcome.seeds))
        self.assertEqual(outcome.seeds,(after.rd(0x7B62),after.rd(0x8336)))
        mixed=session_save.encode(owner.state,template)
        restored,restored_template=session_save.decode(mixed)
        self.assertEqual(restored,owner.state);self.assertEqual(restored_template,template)
        for index in (0,1):
            bad=json.loads(mixed)
            bad['state']['campaign']['results'][index]['engine']=ENGINE_ID if index==0 else LEGACY_ENGINE_ID
            with self.assertRaises(session_save.SessionSaveError):session_save.decode(json.dumps(bad).encode())
        # [designed] Quick continuation follows the same mixed history when a friendly is pending.
        # This real1990 calendar now reaches its first qualifier, which quick must refuse atomically.
        self.assertNotEqual(restored.campaign.next_fixture.kind,1)
        before=copy.deepcopy(restored)
        with self.assertRaisesRegex(ValueError,'unsupported managed fixture'):play(restored,template)
        self.assertEqual(restored,before)
        # The genuine legacy campaign's next friendly also supports watched -> quick continuation.
        quick=[]
        for prior in (state,session_save.decode(raw)[0]):quick.append(play(self.select(prior),template))
        self.assertEqual(quick[0],quick[1])
        self.assertNotIn('engine',quick[0].last_match)
        self.assertEqual(quick[0].campaign.results[0],old_history[0])
        self.assertEqual(quick[0].mem,state.mem)
        self.assertEqual(quick[0].rng_seed_8336,state.rng_seed_8336)
        resumed,_=session_save.decode(session_save.encode(quick[0],template))
        self.assertEqual(resumed,quick[0]);self.assertEqual(resumed.mem,state.mem)


if __name__=='__main__':unittest.main()
