"""[designed: owner #636] Strict independent request and opportunity packets.
No match is simulated in these controls; natural UI/worker acceptance is separate.
"""
import copy
import unittest
from dataclasses import asdict
from goal2.engine.original_match import Fixture


class Packets(unittest.TestCase):
    def test_request_and_cancel_keep_explicit_desired_boolean(self):
        from goal2.game.watched_jobs import _changes
        for desired in (False, True):
            self.assertEqual(_changes({'request_substitution': desired, 'edit_only': True}),
                             {'request_substitution': desired, 'edit_only': True})

    def test_opportunity_answer_has_its_own_exact_enum(self):
        from goal2.game.watched_jobs import _changes
        for answer in ('accept', 'dismiss', 'timeout'):
            self.assertEqual(_changes({'opportunity': answer}), {'opportunity': answer})

    def test_composite_flags_travel_together(self):
        from goal2.game.engine_process import EngineProcess
        process = EngineProcess(lambda *args: None)
        process._game = b'synthetic';process._life = object();sent = []
        process._send = sent.append
        process.match('watched', Fixture(7, 19, 21), frames=True, bench=True,
                      live_players=True, substitution_control=True)
        self.assertIs(sent[-1]['live_players'], True)
        self.assertIs(sent[-1]['substitution_control'], True)

    def test_false_flag_keeps_exact_legacy_packet(self):
        from goal2.game.engine_process import EngineProcess
        process = EngineProcess(lambda *args: None)
        process._game = b'synthetic';process._life = object();sent = []
        process._send = sent.append
        process.match('watched', Fixture(7, 19, 21), substitution_control=False)
        self.assertEqual(sent[-1], {'op':'match','kind':'watched', 'fixture':asdict(Fixture(7,19,21)),
                                   'options':{},'frames':False,'bench':False})


class Publication(unittest.TestCase):
    def result(self, context, answer):
        from goal2.tests.test_watched_kit_identity import result
        value = result();value['kit'] = '4'
        value['decisions'] = [{'context':context,'minute':30,'answer':answer}]
        return value

    def test_standalone_request_and_cancel_survive_completed_result_validation(self):
        from goal2.game.watched_schema import validate_result
        for desired in (False, True):
            raw = self.result('pause', {'substitutions':[], 'tactics':[], 'positions':[], 'marking':[],
                        'own_tactics':[], 'quick':False, 'speed':None, 'edit_only':True,
                        'request_substitution':desired})
            before = copy.deepcopy(raw)
            validate_result(raw)
            self.assertEqual(raw, before)

    def test_opportunity_outcomes_survive_completed_result_validation(self):
        from goal2.game.watched_schema import validate_result
        for outcome in ('accept','dismiss','timeout'):
            raw = self.result('substitution_opportunity', {'opportunity':outcome})
            before = copy.deepcopy(raw)
            validate_result(raw)
            self.assertEqual(raw, before)




class StrictBoundaries(unittest.TestCase):
    def test_constructor_flags_are_strict_and_need_an_interactive_policy(self):
        from goal2.game.engine_process import EngineProcess
        for flag in (0,1,None,'true',[],{}):
            process=EngineProcess(lambda *args:None);process._game=b'game';process._life=object();sent=[]
            process._send=sent.append
            with self.subTest(flag=flag),self.assertRaises(ValueError):
                process.match('watched',Fixture(7,19,21),frames=True,bench=True,substitution_control=flag)
            self.assertEqual(sent,[])
        for frames,bench in ((False,False),(True,False),(False,True)):
            process=EngineProcess(lambda *args:None);process._game=b'game';process._life=object();process._send=lambda request:self.fail('sent invalid mode')
            with self.assertRaises(ValueError):
                process.match('watched',Fixture(7,19,21),frames=frames,bench=bench,substitution_control=True)

    def test_composite_event_requires_both_snapshot_and_authoritative_boolean(self):
        from goal2.game.watched_jobs import _event
        from goal2.tests.test_live_record_wire_t196 import event
        value=event();value['data']['request_substitution']=False
        self.assertEqual(_event(value,live_players=True,substitution_control=True).data,value['data'])
        for wrong in (None,0,1,'false',[],{}):
            bad=copy.deepcopy(value);bad['data']['request_substitution']=wrong
            with self.subTest(wrong=wrong),self.assertRaises(ValueError):
                _event(bad,live_players=True,substitution_control=True)
        for missing in ('request_substitution','player_records'):
            bad=copy.deepcopy(value);bad['data'].pop(missing)
            with self.assertRaises(ValueError):_event(bad,live_players=True,substitution_control=True)

    def test_opportunity_context_and_timing_are_an_exact_original_profile(self):
        from goal2.game.watched_jobs import _event
        from goal2.tests.test_live_record_wire_t196 import event
        for keeper in (False,True):
            value=event();value['data'].update(context='substitution_opportunity',request_substitution=True,
                keeper_unavailable=keeper,timeout_polls=1000 if keeper else 400,poll_ms=10,substitutions_now=True)
            self.assertEqual(_event(value,live_players=True,substitution_control=True).data,value['data'])
            for field,wrong in [('keeper_unavailable',1),('timeout_polls',True),('timeout_polls',2),('poll_ms',9),
                                ('poll_ms',True),('substitutions_now',1),('context','unrecognized')]:
                bad=copy.deepcopy(value);bad['data'][field]=wrong
                with self.subTest(field=field,wrong=wrong),self.assertRaises(ValueError):
                    _event(bad,live_players=True,substitution_control=True)
            with self.assertRaises(ValueError):_event(value,live_players=True)

    def bridge(self, context='pause', allowed=False):
        from goal2.tests.test_stopped_bench_t188 import EditProtocol
        jobs=EditProtocol.bridge(self,context,allowed);jobs._substitution_control=True
        return jobs

    def test_cancel_is_one_consumed_request_without_a_pair(self):
        jobs=self.bridge()
        jobs.answer('test',[],{'request_substitution':False,'edit_only':True})
        self.assertEqual(jobs.sent,[((3,[]),{'changes':{'request_substitution':False,'edit_only':True}})])
        self.assertEqual(jobs._decisions,4)
        with self.assertRaises(ValueError):jobs.answer('test',[],{'request_substitution':False,'edit_only':True})
        self.assertEqual(len(jobs.sent),1)

    def test_invalid_contexts_and_pairs_do_not_consume_a_waiting_decision(self):
        for context,allowed,pairs,changes in [
            ('pause',False,[[105,112]],{'request_substitution':True,'edit_only':True}),
            ('pause',False,[],{'request_substitution':True}),
            ('half_time',True,[],{'request_substitution':True,'edit_only':True}),
            ('pause',False,[],{'request_substitution':True,'edit_only':True,'positions':{105:3}}),
            ('pause',False,[],{'opportunity':'accept'}),
            ('substitution_opportunity',True,[[105,112]],{'opportunity':'accept'}),
            ('substitution_opportunity',True,[],{}),
        ]:
            jobs=self.bridge(context,allowed);waiting=jobs.waiting
            with self.subTest(context=context,pairs=pairs,changes=changes),self.assertRaises(ValueError):
                jobs.answer('test',pairs,changes)
            self.assertIs(jobs.waiting,waiting);self.assertEqual(jobs.sent,[]);self.assertEqual(jobs._decisions,3)

    def test_opportunity_has_one_dedicated_answer_without_a_pair_report(self):
        jobs=self.bridge('substitution_opportunity',True)
        jobs.answer('test',[],{'opportunity':'timeout'})
        self.assertEqual(jobs.sent,[((3,[]),{'changes':{'opportunity':'timeout'}})])
        self.assertIsNone(jobs.waiting)

    def test_new_completed_profiles_reject_unrelated_or_malformed_fields(self):
        from goal2.game.watched_schema import validate_result
        valid={'substitutions':[],'tactics':[],'positions':[],'marking':[],'own_tactics':[],
               'quick':False,'speed':None,'edit_only':True,'request_substitution':False}
        for field,value in [('request_substitution',1),('request_substitution',None),('edit_only',False),
                ('substitutions',[[1,12]]),('positions',[[1,2]]),('marking',[[1,2]]),
                ('tactics',[[9,True]]),('quick',True),('speed',0),('extra',True)]:
            answer=copy.deepcopy(valid);answer[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                validate_result(Publication.result(self,'pause',answer))
        for context in ('half_time','extra_time','substitution'):
            with self.assertRaises(ValueError):validate_result(Publication.result(self,context,valid))
        for answer in ({'opportunity':False},{'opportunity':'auto'}, {'opportunity':'accept','edit_only':True},
                       {'opportunity':'accept','substitutions':[[1,12]]}):
            with self.assertRaises(ValueError):validate_result(Publication.result(self,'substitution_opportunity',answer))


if __name__ == "__main__": unittest.main(verbosity=2)
