"""[designed: T47] Real halftime engine/worker, full IDs, no re-entry and saves.
[derived: F027/F029 at0ef880e] Existing managed rebind and persistent squad words.
"""
import copy
import hashlib
from pathlib import Path
import tempfile
import time
import unittest
from goal2.desktop.model import DesktopModel
from goal2.desktop.jobs import QuickJobs
from goal2.desktop.worker import complete
from goal2.engine.savestate import Savestate
from goal2.game.quick_match import begin_full_match
from goal2.game.state import to_savestate
from goal2.game.session_save import encode
from goal2.game.substitutions import plan,swap
from goal2.game.campaign_rounds import prepare as prepare_round
ROOT=Path(__file__).resolve().parents[2]
# [designed] Complete pre-T47 uninterrupted continuations, base65ab461, source
# E010-r0008 template, country4, captain61/tactics165. Explicit JSON save hashes.
GOLDEN=('7415d6828c7947bd75e421190fc6d0b61e0cf78162ad564cca7bd6720666cb13',
        '0287107911367819be773c00a174ad4b7ad59eb6f41bbbf70856a9bfd4238f0a')

class HalftimeCases(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.model=DesktopModel.open(ROOT/'.cache/e010-r0008-halftime.sav',ROOT/'.cache/GOAL.DAT',Path(self.folder.name)/'game.g2save',country=4)
        self.model.confirm(list(self.model.state.starting_eleven),61,165)
    def begin(self):
        state=prepare_round(self.model.state,self.model.template_bytes)
        return begin_full_match(Savestate(to_savestate(state,original=self.model.template_bytes)),state)
    def job(self):
        job=QuickJobs(self.model);self.addCleanup(job.cancel);job.start(halftime=True);return job
    def until(self,job,predicate):
        deadline=time.monotonic()+15
        while time.monotonic()<deadline:
            job.poll()
            if predicate():return
            time.sleep(.01)
        self.fail('worker deadline exceeded')
    def test_no_substitution_split_matches_prechange_complete_state_hashes_for_both_sides(self):
        # [designed: T48] These pre-T47 bytes explicitly cover metadata-free legacy saves.
        self.model.state.campaign.world=None
        for digest in GOLDEN:
            match=self.begin();qm=match.qm;before=copy.deepcopy(self.model.state)
            self.assertEqual(match.state,before);self.assertEqual(self.model.state,before)
            snapshot=match.preview();self.assertEqual(snapshot,match.preview())
            result=match.finish(retain_state=True);self.assertIs(match.qm,qm)
            self.model.state=complete(match.state,result,template=self.model.template_bytes)
            self.assertEqual(hashlib.sha256(encode(self.model.state,self.model.template_bytes)).hexdigest(),digest)
            with self.assertRaisesRegex(ValueError,'already'):match.finish(retain_state=True)
            with self.assertRaisesRegex(ValueError,'already'):match.substitute(61,72)
    def test_unlimited_friendlies_five_other_kinds_no_reentry_and_invalid_choices_are_pure(self):
        for kind in (1,2):
            current=plan(list(range(1,12)),list(range(12,32)),list(range(1,32)),1,kind=kind)
            for n in range(5):current=swap(current,n+1,n+12)
            if kind==1:
                current=swap(current,6,17);self.assertEqual(len(current['changes']),6)
            else:
                before=copy.deepcopy(current)
                with self.assertRaisesRegex(ValueError,'Five'):swap(current,6,17)
                self.assertEqual(current,before)
        original=plan(list(range(1,12)),[12,13],list(range(1,13)),1)
        changed=swap(original,1,12);self.assertEqual(original['captain'],1);self.assertEqual(changed['captain'],12)
        for out,inc,reason in ((12,1,'re-enter'),(2,13,'unavailable'),(True,1,'Choose'),(2,2,'Choose')):
            before=copy.deepcopy(changed)
            with self.assertRaisesRegex(ValueError,reason):swap(changed,out,inc)
            self.assertEqual(changed,before)
    def test_real_swaps_mark_participants_rebind_pitch_keep_positions_and_persist_high_ids(self):
        self.model.exchange(80,2561);self.model.confirm(list(self.model.state.starting_eleven),61,165)
        match=self.begin();qm=match.qm
        outgoing=61;incoming=2561;position=qm._player(incoming)[6];before=copy.deepcopy(match.state)
        seeds=(qm.rng.seed,qm.seed2,qm.rng.draws)
        match.substitute(outgoing,incoming)
        self.assertEqual((qm.rng.seed,qm.seed2,qm.rng.draws),seeds)
        self.assertEqual(match.state,before)
        self.assertTrue(qm._player(outgoing)[16]&4)
        self.assertEqual(qm._player(incoming)[6],position)
        self.assertIn(incoming,[qm.pitch[qm.side_base[match.managed_side]+n]['player'] for n in range(1,12)])
        self.assertNotIn(outgoing,match.plan['eleven'])
        result=match.finish(retain_state=True);state=complete(match.state,result,template=self.model.template_bytes)
        self.assertIn(incoming,state.starting_eleven);self.assertNotIn(outgoing,state.starting_eleven)
        self.assertEqual(state.captain,2561);self.assertEqual(state.managed_squad[:11],state.starting_eleven)
        words=[int.from_bytes(state.countries[4][i:i+2],'little') for i in range(0,40,2)]
        self.assertEqual(words,state.managed_squad)
        self.model.state=state;self.model.save(self.model.save_path);self.model.resume(self.model.save_path)
        self.assertEqual(self.model.state,state)
        second=self.begin();self.assertIn(2561,second.plan['eleven']);self.assertNotIn(61,second.plan['eleven'])
        self.assertFalse(state.players[61][16]&4)
    def test_live_engine_allows_six_friendly_swaps_and_rejects_reentry_atomically(self):
        match=self.begin();starters=list(match.plan['eleven']);bench=list(match.plan['bench'])
        for outgoing,incoming in zip(starters[:6],bench[:6]):
            try:match.substitute(outgoing,incoming)
            except ValueError as exc:self.fail(f'Friendly substitution refused: {exc}')
        self.assertEqual(len(match.plan['changes']),6)
        before=match.preview();seed=match.qm.rng.seed
        with self.assertRaisesRegex(ValueError,'re-enter'):match.substitute(bench[0],starters[0])
        self.assertEqual(match.preview(),before);self.assertEqual(match.qm.rng.seed,seed)
        match.finish(retain_state=True)
        self.assertTrue(set(bench[:6])<=set(match.state.starting_eleven))

    def test_actual_worker_pauses_does_not_publish_or_overwrite_save_and_continues_once(self):
        model=self.model;model.save(model.save_path);saved=model.save_path.read_bytes();before=copy.deepcopy(model.state)
        job=self.job();pid=job.process.pid;self.until(job,lambda:job.halftime is not None)
        self.assertEqual(model.state,before);self.assertTrue(job.busy)
        with self.assertRaisesRegex(ValueError,'Saving during'):model.save(model.save_path)
        self.assertEqual(model.save_path.read_bytes(),saved)
        out=job.halftime['eleven'][0];inc=job.halftime['bench'][0]
        job.substitute(out,inc)
        with self.assertRaisesRegex(ValueError,'re-enter'):job.substitute(inc,out)
        job.continue_match();self.assertEqual(job.process.pid,pid)
        with self.assertRaisesRegex(ValueError,'already'):job.continue_match()
        self.until(job,lambda:not job.busy)
        self.assertEqual(model.state.match_count,1);self.assertEqual(len(model.state.campaign.results),1)
        self.assertIn(inc,model.state.starting_eleven);self.assertNotIn(out,model.state.starting_eleven)
        self.assertIsNone(job.poll());self.assertFalse(model.match_pending)
        model.save(model.save_path)
    def test_bad_preview_failed_worker_and_bad_continuation_leave_game_and_save_untouched(self):
        import json,sys
        model=self.model;model.save(model.save_path);saved=model.save_path.read_bytes()
        before=copy.deepcopy(model.state)
        job=QuickJobs(model,command=[sys.executable,'-c','import time;time.sleep(60)']);self.addCleanup(job.cancel)
        job.start(halftime=True);process=job.process
        (job.directory/'halftime.json').write_text('{"bad":true}')
        with self.assertRaisesRegex(ValueError,'Invalid halftime'):job.poll()
        self.assertFalse(job.busy);self.assertIsNotNone(process.poll())
        for failure in ('crash','command'):
            job=self.job();self.until(job,lambda:job.halftime is not None)
            if failure=='crash':job.process.kill()
            else:(job.directory/'continue.json').write_text(json.dumps([[61,99999]]))
            with self.assertRaisesRegex(ValueError,'worker failed'):
                self.until(job,lambda:not job.busy)
            self.assertEqual(model.state,before);self.assertEqual(model.save_path.read_bytes(),saved)
            self.assertFalse(model.match_pending)

    def test_standalone_mode_refuses_interactive_start_without_changing_state(self):
        self.model.new_friendly(4);before=copy.deepcopy(self.model.state)
        job=QuickJobs(self.model);self.addCleanup(job.cancel)
        with self.assertRaisesRegex(ValueError,'requires a campaign'):job.start(halftime=True)
        self.assertFalse(job.busy);self.assertEqual(self.model.state,before)

    def test_cancel_and_stale_halftime_preserve_the_active_game_and_prior_save(self):
        model=self.model;model.save(model.save_path);saved=model.save_path.read_bytes()
        for stale in (False,True):
            job=self.job();self.until(job,lambda:job.halftime is not None);process=job.process
            if stale:
                model.confirm(list(model.state.starting_eleven),61,90)
                before=copy.deepcopy(model.state)
                with self.assertRaisesRegex(ValueError,'stale'):job.continue_match()
            else:
                before=copy.deepcopy(model.state);start=time.monotonic();job.cancel();self.assertLess(time.monotonic()-start,2)
            self.assertFalse(job.busy);self.assertIsNotNone(process.poll());self.assertEqual(model.state,before)
            self.assertEqual(model.save_path.read_bytes(),saved);self.assertFalse(model.match_pending)

if __name__=='__main__':unittest.main()
