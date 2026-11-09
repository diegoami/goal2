"""[designed: T170c2/#566] A completed sealed round reaches the campaign whole, once, or not at all.

No network, no Qt, no backend: the route is replaced exactly as in T170b's session controls, so these
controls own only the publication contract.
"""
import ast
import copy
import dataclasses
import inspect
import unittest
from types import SimpleNamespace
from unittest.mock import patch,PropertyMock
from goal2.engine.original_match.image import Image
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.engine.original_match.route import RoundStep
from goal2.game import engine_tables,season_publication
from goal2.game.season import SeasonSession,canonical_hash
from goal2.game.season_publication import SeasonCampaign,SeasonPublication,PUBLISHABLE


def state(mark=0):
    """A valid state/2 whose main RNG word (DS:7B62) is `mark`, so different marks hash differently."""
    tables=engine_tables.load()
    image=Image.__new__(Image)
    image.header=bytes(0x78);image.load=0x100;image.DS=image.load+0x2581
    image.memory=bytearray(MEM_SIZE);image.tables=tables
    tables.place(image.memory,image.load)
    image.memory[image.DS*16+0x7B62]=mark
    return image.state(tables)


def step(status,value,fixtures=(),pages=(),match=None,continuation=None):
    return RoundStep(status,copy.deepcopy(value),tuple(fixtures),tuple(pages),match,continuation)


class Rig:
    """A session at call 1 'complete' (state 0 -> state 1), a campaign holding state 0, and a publication."""
    def __init__(self,test,view=None,first='complete',second=None):
        self.start=state(0);self.after=state(7)
        self.fixture={'fixture':1,'score':[2,1]}
        steps=[step(first,self.after,(self.fixture,))]
        if second is not None:steps.append(second)
        self.play=patch('goal2.game.season.route.play_round',side_effect=steps)
        self.play.start();test.addCleanup(self.play.stop)
        self.session=SeasonSession(self.start)
        self.campaign=SeasonCampaign(self.start,view=view)
        self.publication=SeasonPublication(self.campaign)
        self.before=self.campaign.canonical_hash


class Publication(unittest.TestCase):
    def test_completed_call_publishes_once_and_campaign_hash_is_the_declared_output(self):
        rig=Rig(self);obs=rig.session.advance()
        self.assertEqual(obs.status,'complete');self.assertNotEqual(obs.input_hash,obs.output_hash)
        self.assertEqual(rig.campaign.canonical_hash,obs.input_hash)
        job=rig.publication.begin(obs)
        self.assertEqual(rig.campaign.canonical_hash,obs.input_hash)  # begin installs nothing
        preparation=rig.publication.prepare_completion(job.token,rig.session)
        self.assertEqual(rig.campaign.canonical_hash,obs.input_hash)  # nor does preparation
        preparation.run()
        self.assertEqual(rig.campaign.canonical_hash,obs.input_hash)  # nor a finished candidate
        record=rig.publication.publish_prepared(job.token,preparation)
        self.assertEqual(rig.campaign.canonical_hash,obs.output_hash)
        self.assertEqual(rig.campaign.state,rig.session.state)
        self.assertEqual(rig.campaign.published,(record,))
        self.assertEqual((record.call_number,record.status,record.input_hash,record.output_hash),
                         (1,'complete',obs.input_hash,obs.output_hash))
        self.assertEqual(rig.campaign.revision,1)

    def test_complete_is_the_synchronous_form_and_rollover_boundary_publishes(self):
        for status in PUBLISHABLE:
            rig=Rig(self,first=status);obs=rig.session.advance()
            job=rig.publication.begin(obs);rig.publication.complete(job.token,rig.session)
            self.assertEqual(rig.campaign.canonical_hash,obs.output_hash)

    def test_same_call_twice_is_refused_by_name_and_changes_nothing(self):
        rig=Rig(self);obs=rig.session.advance()
        rig.publication.complete(rig.publication.begin(obs).token,rig.session)
        held=(rig.campaign.state,rig.campaign.published,rig.campaign.revision)
        with self.assertRaisesRegex(ValueError,'season call 1 is already published'):
            rig.publication.begin(obs)
        # A fresh observation of the same completed call is the same call.
        with self.assertRaisesRegex(ValueError,'season call 1 is already published'):
            rig.publication.begin(rig.session.observe())
        # A second publication object over the same campaign meets the campaign's own ledger.
        with self.assertRaisesRegex(ValueError,'season call 1 is already published'):
            SeasonPublication(rig.campaign).begin(obs)
        self.assertEqual((rig.campaign.state,rig.campaign.published,rig.campaign.revision),held)

    def test_ledger_refuses_a_repeat_even_when_the_hash_chain_cannot(self):
        # A call that changed nothing has output == input, so the campaign still "starts from" its input
        # after publishing it; only the ledger can tell that it is a repeat.
        rig=Rig(self)
        rig.play.stop();patcher=patch('goal2.game.season.route.play_round',return_value=step('complete',rig.start))
        patcher.start();self.addCleanup(patcher.stop)
        obs=rig.session.advance();self.assertEqual(obs.input_hash,obs.output_hash)
        rig.publication.complete(rig.publication.begin(obs).token,rig.session)
        self.assertEqual(len(rig.campaign.published),1)
        with self.assertRaisesRegex(ValueError,'season call 1 is already published'):
            rig.publication.begin(obs)
        self.assertEqual(len(rig.campaign.published),1)

    def test_consumed_token_and_preparation_cannot_publish_again(self):
        rig=Rig(self);obs=rig.session.advance();job=rig.publication.begin(obs)
        preparation=rig.publication.prepare_completion(job.token,rig.session);preparation.run()
        rig.publication.publish_prepared(job.token,preparation)
        held=rig.campaign.published
        with self.assertRaisesRegex(ValueError,'unknown or consumed'):
            rig.publication.publish_prepared(job.token,preparation)
        with self.assertRaisesRegex(ValueError,'unknown or consumed'):
            rig.publication.complete(job.token,rig.session)
        self.assertEqual(rig.campaign.published,held)

    def test_failure_between_preparation_and_publication_leaves_the_campaign_as_it_was(self):
        failing=[True]
        def view(candidate):
            # The campaign's validating hook runs on the finished candidate, immediately before the swap.
            self.assertEqual(candidate.record.call_number,1)
            if failing[0]:raise RuntimeError('injected between preparation and publication')
        rig=Rig(self,view=view);obs=rig.session.advance()
        before=(rig.campaign.state,rig.campaign.canonical_hash,rig.campaign.published,rig.campaign.revision)
        job=rig.publication.begin(obs)
        preparation=rig.publication.prepare_completion(job.token,rig.session);preparation.run()
        self.assertIsNone(preparation.error);self.assertIsNotNone(preparation.candidate)
        with self.assertRaisesRegex(RuntimeError,'injected'):
            rig.publication.publish_prepared(job.token,preparation)
        self.assertEqual((rig.campaign.state,rig.campaign.canonical_hash,rig.campaign.published,rig.campaign.revision),before)
        self.assertEqual(rig.campaign.canonical_hash,rig.before)
        with self.assertRaisesRegex(ValueError,'unknown or consumed'):  # the token died with the failure
            rig.publication.publish_prepared(job.token,preparation)
        # Nothing was half-installed: the same call now publishes whole, once.
        failing[0]=False
        rig.publication.complete(rig.publication.begin(obs).token,rig.session)
        self.assertEqual(rig.campaign.canonical_hash,obs.output_hash);self.assertEqual(len(rig.campaign.published),1)

    def test_failure_while_preparing_is_held_and_raised_at_publication_without_effect(self):
        rig=Rig(self);obs=rig.session.advance()
        forged=dataclasses.replace(obs,output_hash='0'*64)
        job=rig.publication.begin(forged)
        preparation=rig.publication.prepare_completion(job.token,rig.session);preparation.run()
        self.assertIsInstance(preparation.error,ValueError)
        with self.assertRaisesRegex(ValueError,'season call 1'):
            rig.publication.publish_prepared(job.token,preparation)
        self.assertEqual(rig.campaign.canonical_hash,rig.before);self.assertEqual(rig.campaign.published,())

    def test_state_that_does_not_hash_to_the_declared_output_is_never_installed(self):
        rig=Rig(self);obs=rig.session.advance();job=rig.publication.begin(obs)
        with patch.object(SeasonSession,'state',new_callable=PropertyMock,return_value=state(11)):
            preparation=rig.publication.prepare_completion(job.token,rig.session)
        preparation.run()
        self.assertRegex(str(preparation.error),'differs from the observation')
        with self.assertRaisesRegex(ValueError,'season call 1'):
            rig.publication.publish_prepared(job.token,preparation)
        self.assertEqual((rig.campaign.canonical_hash,rig.campaign.published),(rig.before,()))

    def test_unfinished_preparation_cannot_publish(self):
        rig=Rig(self);obs=rig.session.advance();job=rig.publication.begin(obs)
        preparation=rig.publication.prepare_completion(job.token,rig.session)
        with self.assertRaisesRegex(ValueError,'still preparing'):
            rig.publication.publish_prepared(job.token,preparation)
        self.assertEqual(rig.campaign.canonical_hash,rig.before)
        preparation.run();rig.publication.publish_prepared(job.token,preparation)  # the pending job survived the refusal
        self.assertEqual(rig.campaign.canonical_hash,obs.output_hash)

    def test_cancelled_preparation_publishes_nothing(self):
        rig=Rig(self);obs=rig.session.advance();job=rig.publication.begin(obs)
        preparation=rig.publication.prepare_completion(job.token,rig.session);preparation.run()
        rig.publication.cancel()
        with self.assertRaisesRegex(ValueError,'unknown or consumed'):
            rig.publication.publish_prepared(job.token,preparation)
        self.assertEqual(rig.campaign.canonical_hash,rig.before);self.assertEqual(rig.campaign.published,())
        self.assertEqual(rig.campaign.revision,0)
        rig.publication.complete(rig.publication.begin(obs).token,rig.session)  # a cancel is not a ledger entry
        self.assertEqual(rig.campaign.canonical_hash,obs.output_hash)

    def test_pending_and_unready_calls_are_refused_by_name(self):
        rig=Rig(self,first='match')
        ready=rig.session.observe()
        with self.assertRaisesRegex(ValueError,'season call 0 is ready'):
            rig.publication.begin(ready)
        obs=rig.session.advance();self.assertEqual(obs.status,'match')
        with self.assertRaisesRegex(ValueError,'season call 1 is match, not complete'):
            rig.publication.begin(obs)
        self.assertEqual((rig.campaign.canonical_hash,rig.campaign.published),(rig.before,()))

    def test_rejected_resume_leaves_the_call_pending_and_unpublishable(self):
        match=SimpleNamespace(over=True)
        pending=step('match',state(7),match=match,continuation=object())
        with patch('goal2.game.season.route.play_round',return_value=pending),\
             patch('goal2.game.season.route.resume_round',side_effect=ValueError('wrong return frame')):
            session=SeasonSession(state(0));campaign=SeasonCampaign(state(0))
            publication=SeasonPublication(campaign);session.advance()
            self.assertRaises(ValueError,session.resume,match)
            with self.assertRaisesRegex(ValueError,'season call 1 is match, not complete'):
                publication.begin(session.observe())
        self.assertEqual((campaign.canonical_hash,campaign.published),(canonical_hash(state(0)),()))

    def test_unknown_status_is_refused_by_name(self):
        rig=Rig(self);obs=rig.session.advance()
        with self.assertRaisesRegex(ValueError,'season call 1 is rejected, not complete'):
            rig.publication.begin(dataclasses.replace(obs,status='rejected'))
        self.assertEqual(rig.campaign.published,())

    def test_call_that_moved_on_after_begin_publishes_nothing(self):
        match=SimpleNamespace(over=False)
        rig=Rig(self,second=step('match',state(9),match=match,continuation=object()))
        obs=rig.session.advance();job=rig.publication.begin(obs)
        rig.session.advance()  # the session moved to call 2 before preparation read it
        preparation=rig.publication.prepare_completion(job.token,rig.session);preparation.run()
        with self.assertRaisesRegex(ValueError,'season call 1 changed since it was begun'):
            rig.publication.publish_prepared(job.token,preparation)
        self.assertEqual((rig.campaign.canonical_hash,rig.campaign.published),(rig.before,()))

    def test_call_that_does_not_start_from_the_campaign_is_refused(self):
        rig=Rig(self);obs=rig.session.advance()
        elsewhere=SeasonCampaign(state(3))
        with self.assertRaisesRegex(ValueError,'season call 1 does not start from the campaign'):
            SeasonPublication(elsewhere).begin(obs)
        self.assertEqual(elsewhere.published,())

    def test_campaign_changed_after_begin_is_stale_and_publishes_nothing(self):
        rig=Rig(self);obs=rig.session.advance();job=rig.publication.begin(obs)
        rival=SeasonPublication(rig.campaign);rival.complete(rival.begin(obs).token,rig.session)
        with self.assertRaisesRegex(ValueError,'stale'):
            rig.publication.prepare_completion(job.token,rig.session)
        self.assertEqual(len(rig.campaign.published),1)
        with self.assertRaisesRegex(ValueError,'unknown or consumed'):  # a stale job is cancelled
            rig.publication.complete(job.token,rig.session)
        self.assertEqual(len(rig.campaign.published),1)

    def test_session_stays_the_owner_and_publication_never_touches_the_match_or_route(self):
        rig=Rig(self);obs=rig.session.advance()
        observed=rig.session.observe();held=rig.session.state
        with patch('goal2.game.season.route.play_round',side_effect=AssertionError('route call forbidden')) as play,\
             patch('goal2.game.season.route.resume_round',side_effect=AssertionError('resume forbidden')) as resume,\
             patch('goal2.engine.original_match.port.engine.PortMachine',side_effect=AssertionError('backend forbidden')),\
             patch.object(SeasonSession,'pending_match',new_callable=PropertyMock,side_effect=AssertionError('Match forbidden')),\
             patch.object(SeasonSession,'advance',side_effect=AssertionError('advance forbidden')),\
             patch.object(SeasonSession,'resume',side_effect=AssertionError('resume forbidden')):
            rig.publication.complete(rig.publication.begin(obs).token,rig.session)
        self.assertFalse(play.called or resume.called)
        self.assertEqual(rig.session.observe(),observed);self.assertEqual(rig.session.state,held)
        # Nothing is shared: mutating either side's copy changes neither.
        detached=rig.campaign.state;detached['header']='caller mutation'
        self.assertNotEqual(rig.campaign.state['header'],'caller mutation')
        mutable=rig.session.state;mutable['header']='caller mutation'
        self.assertEqual(rig.campaign.canonical_hash,obs.output_hash)
        self.assertEqual(rig.session.observe(),observed)

    def test_module_imports_no_route_match_or_backend_and_names_no_private_session_state(self):
        tree=ast.parse(inspect.getsource(season_publication))
        imported=[n.module if isinstance(n,ast.ImportFrom) else a.name
                  for n in ast.walk(tree) if isinstance(n,(ast.Import,ast.ImportFrom))
                  for a in (n.names if isinstance(n,ast.Import) else [None])]
        self.assertFalse([m for m in imported if m and ('route' in m or 'port' in m or 'watched' in m or 'engine_server' in m or 'ui' in m.split('.'))],imported)
        names={n.attr for n in ast.walk(tree) if isinstance(n,ast.Attribute)}
        self.assertFalse(names&{'pending_match','_continuation','_pending_match','_keys','_tables','play_round','resume_round','advance','resume'})


if __name__=='__main__':
    unittest.main()
