"""[designed: T45] Ordered reserve effects, real exchanged IDs and continuation."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from goal2.game import campaign_pool as pool, campaign_energy
from goal2.game.session_save import encode,decode
from goal2.engine.quick_engine import LCG
from goal2.tests import test_campaign_pool as cases
from goal2.tests import requires

@requires.need(**requires.HALFTIME)
class PoolFlow(unittest.TestCase):
    setUp=cases.PoolCases.setUp
    # [designed] Reuse the real-data setup, without inheriting its test methods.
    def test_literal_pool_draw_bounds_order_and_status(self):
        self.state.campaign.reserve_ids=list(range(2561,2641))
        records={w:bytearray(self.state.players[w]) for w in self.state.campaign.reserve_ids}
        for rec in records.values():rec[12:15]=bytes((16,16,0));rec[16]=0x80
        calls=[]
        class Draws:
            draws=0
            values=iter([1,8,1,4,1]*80)
            def rand(self,bound):
                self.draws+=1;calls.append(bound)
                return next(self.values)
        qm=SimpleNamespace(rng=Draws(),state=SimpleNamespace(ds_bytes=lambda o,n:{0xe82:bytes((16,13)),0xe84:bytes((32,24)),0xf3e:bytes((2,))}[o]),playerrec=records)
        qm._player=lambda w:qm.playerrec[w]
        meta=pool.finish(qm,self.state)
        self.assertEqual(calls,[2,8,3,4,4]*80)
        self.assertEqual(meta['recovery_draws'],240)
        self.assertEqual(meta['confidence_draws'],160)
        self.assertEqual(tuple(records[2561][12:15]),(13,9,9))
        self.assertEqual(records[2561][16],0)
        with self.assertRaisesRegex(ValueError,'already'):pool.finish(qm,self.state)
    def test_real_exchanged_player_and_ordered_prefix_continue_identically_after_resume(self):
        pool.exchange(self.state,61,2561)
        resumed,_=decode(encode(self.state,self.session.template_bytes))
        other=type(self.session)(resumed,self.session.goaldat,self.session.template,self.session.template_bytes)
        outgoing_before=self.state.players[61]
        captures=[];trace=[];original=campaign_energy.finish
        def finish(qm,state,**kw):
            recover=campaign_energy.recover_player
            def spy(record,flag,rng,**kwargs):
                trace.append(bool(flag))
                return recover(record,flag,rng,**kwargs)
            before=qm.rng.seed
            with patch.object(campaign_energy,'recover_player',side_effect=spy):meta=original(qm,state,**kw)
            captures.append((before,qm.rng.seed,meta));return meta
        for session in (self.session,other):
            v=session.view()
            with patch.object(campaign_energy,'finish',side_effect=finish):session.play({'play_token':v['play_token'],'fixture_id':v['campaign']['next_fixture']['fixture_id']})
        self.assertEqual(other.state,self.session.state)
        self.state=self.session.state
        self.assertIn(2561,self.state.starting_eleven)
        self.assertEqual(captures[0],captures[1])
        self.assertEqual(trace[:81],[False]*80+[True])
        before,after,meta=captures[0];expected=before
        for _ in range(416):expected=(expected*0x7abd+0x1b0f)&65535
        self.assertEqual(after,expected)
        self.assertEqual(meta['pool']['recovery_draws'],160)
        self.assertEqual(meta['pool']['confidence_draws'],160)
        self.assertNotEqual(self.state.players[61],outgoing_before)
    def test_reserve_failure_and_stateless_simulation_do_not_publish(self):
        from goal2.game.quick_match import run_full_match
        from goal2.game.state import to_savestate
        from goal2.engine.savestate import Savestate
        before=copy.deepcopy(self.state);v=self.session.view()
        with patch.object(pool,'finish',side_effect=ValueError('reserve failure')):
            with self.assertRaisesRegex(ValueError,'reserve failure'):self.session.play({'play_token':v['play_token'],'fixture_id':v['campaign']['next_fixture']['fixture_id']})
        self.assertEqual(self.state,before)
        run_full_match(Savestate(to_savestate(self.state,original=self.session.template_bytes)),self.state)
        self.assertEqual(self.state,before)

if __name__=='__main__':unittest.main()
