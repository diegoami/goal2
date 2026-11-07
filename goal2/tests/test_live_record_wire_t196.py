"""T196: bounded live record packets and opt-in wire controls. No match is simulated here."""
import collections,copy,queue,unittest
from dataclasses import asdict
from types import SimpleNamespace
from unittest.mock import patch
from goal2.engine.original_match import Fixture


def event():
    words=list(range(101,121))
    return {'kind':'decision','minute':45,'score':(0,0),'data':{
        'context':'half_time','eleven':words[:11],'bench':words[11:],
        'player_records':[[w,bytes([7]*20).hex()] for w in words]}}

class Packets(unittest.TestCase):
    def test_validation_preserves_packet_words_and_record_values(self):
        from goal2.game.watched_jobs import _event
        value=event();before=copy.deepcopy(value)
        result=_event(value,live_players=True)
        self.assertEqual(result.data,before['data'])
        self.assertEqual(value,before)

    def test_required_reply_rejects_missing_or_malformed_records(self):
        from goal2.game.watched_jobs import _event
        bad=[]
        value=event();value['data'].pop('player_records');bad.append(value)
        for change in ('short','badhex','duplicate','order','outsider','boolword','extra','dict','pair','bytes','roster'):
            value=event();rows=value['data']['player_records']
            if change=='short':rows[0][1]='00'*19
            elif change=='badhex':rows[0][1]='zz'*20
            elif change=='duplicate':rows[1][0]=rows[0][0]
            elif change=='order':rows.reverse()
            elif change=='outsider':rows[0][0]=999
            elif change=='boolword':rows[0][0]=True
            elif change=='extra':rows.append([121,'00'*20])
            elif change=='dict':value['data']['player_records']={101:'00'*20}
            elif change=='pair':rows[0].append(7)
            elif change=='bytes':rows[0][1]=bytes(20)
            elif change=='roster':value['data']['eleven']=None
            bad.append(value)
        for value in bad:
            with self.subTest(value=value),self.assertRaises(ValueError):_event(value,live_players=True)

    def test_legacy_event_without_records_remains_accepted(self):
        from goal2.game.watched_jobs import _event
        value=event();value['data'].pop('player_records')
        self.assertEqual(_event(value).data,value['data'])

class Client(unittest.TestCase):
    def request(self, **options):
        from goal2.game.engine_process import EngineProcess
        process=EngineProcess(lambda *args:None)
        process._game=b'synthetic-game';process._life=object();sent=[]
        process._send=sent.append
        process.match('watched',Fixture(7,19,21),**options)
        return sent[-1]

    def test_default_and_false_have_exact_legacy_request_shape(self):
        expected={'op':'match','kind':'watched','fixture':asdict(Fixture(7,19,21)),
                  'options':{},'frames':False,'bench':False}
        self.assertEqual(self.request(),expected)
        self.assertEqual(self.request(live_players=False),expected)

    def test_true_is_a_separate_opt_in_and_invalid_flags_fail(self):
        self.assertIs(self.request(live_players=True)['live_players'],True)
        for flag in (0,1,None,'yes',[]):
            with self.subTest(flag=flag),self.assertRaises(ValueError):self.request(live_players=flag)

    def test_low_level_decoder_requires_the_requested_snapshot_before_delivering_an_event(self):
        from goal2.game.engine_process import EngineProcess
        process=EngineProcess(lambda *args:None);process._game=b'synthetic-game';process._life=object()
        process._send=lambda request:None
        process.match('watched',Fixture(7,19,21),live_players=True)
        value=event();value['data'].pop('player_records')
        with self.assertRaisesRegex(ValueError,'records|snapshot'):
            process._decode(process._life,{'kind':'event','value':value},b'')
        self.assertEqual(process._events,[])

class Server(unittest.TestCase):
    def server(self):
        from goal2.game.engine_server import Server
        server=object.__new__(Server);server.game=(SimpleNamespace(),b'synthetic')
        server.inbox=queue.Queue();server.send=lambda *args:None
        return server

    def request(self,**extra):
        return {'op':'match','kind':'watched','fixture':asdict(Fixture(7,19,21)),**extra}

    def test_server_forwards_only_the_requested_opt_in_to_shared_driver(self):
        outcome=SimpleNamespace(result={},events=(),seeds=(1,2),engine_year=1992,memory=b'memory')
        for flag in (None,False,True):
            request=self.request(**({} if flag is None else {'live_players':flag}))
            with patch('goal2.game.watched_match.prepare_watched',return_value=object()),patch(
                    'goal2.game.watched_match._drive_match',return_value=outcome) as drive:
                self.server()._match(request)
            if flag:self.assertIs(drive.call_args.kwargs.get('live_players'),True)
            else:self.assertNotIn('live_players',drive.call_args.kwargs)

    def test_server_rejects_invalid_opt_in_before_preparation(self):
        for flag in (0,1,None,'yes',[]):
            with self.subTest(flag=flag),patch('goal2.game.watched_match.prepare_watched') as prepare:
                with self.assertRaisesRegex(ValueError,'live|match'):
                    self.server()._match(self.request(live_players=flag))
                prepare.assert_not_called()

class BridgeFailure(unittest.TestCase):
    def test_requested_missing_snapshot_fails_before_event_or_publication(self):
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.engine.original_match.match import Event
        job=object.__new__(WatchedJobs)
        value=event();value['data'].pop('player_records')
        job._match=SimpleNamespace(replies=collections.deque([('event',Event(**value))]))
        job._live_players=True;job._complete=None;job.events=[];job._sent=True;job._bench=False
        job._check_token=lambda token:None;job._check_owner=lambda:None
        failed=[];published=[];job._fail=failed.append;job._maybe_publish=published.append
        with self.assertRaisesRegex(ValueError,'records|snapshot'):job.poll('test-token')
        self.assertEqual(failed,['test-token']);self.assertEqual(published,[]);self.assertEqual(job.events,[])



def direct_live_reference(state,raw,fixture,competitive=False):
    """Child-side same-route reference; the port runs only under verified PyPy."""
    from goal2.game.watched_match import _drive_match,prepare_watched,FRIENDLY_SUBSTITUTIONS
    if competitive:
        from goal2.game.competitive_match import prepare_competitive
        image=prepare_competitive(state,raw,fixture);budget=(5,5)
    else:image=prepare_watched(state,raw,fixture);budget=FRIENDLY_SUBSTITUTIONS
    return _drive_match(state,image,fixture,reference_seed=257,delay_byte=0,record_draws=True,
                        substitutions=budget,live_players=True)

from goal2.tests import requires
@requires.need(slow=True,**requires.WATCHED)
class ActualLiveWorker(unittest.TestCase):
    def test_friendly_and_competitive_records_outcome_and_career_equal_the_live_reference(self):
        import time
        from goal2.tests.test_campaign_competitive_match import state
        from goal2.tests.test_campaign_competitive_publication import campaign
        from goal2.tests.test_watched_publication import Owner
        from goal2.tests.test_pypy_worker_t152 import pypy
        from goal2.tests import pypy_engine
        from goal2.game.watched_jobs import WatchedJobs
        from goal2.desktop.competitive import CompetitiveJobs
        from goal2.game.watched_publication import WatchedPublication,CompetitivePublication
        pypy()
        for competitive in (False,True):
            with self.subTest(competitive=competitive):
                if competitive:initial,raw,fixture=campaign(42,200)
                else:initial,raw=state();fixture=Fixture(7,19,21)
                owner=Owner(copy.deepcopy(initial),raw);other=Owner(copy.deepcopy(initial),raw)
                publication=(CompetitivePublication if competitive else WatchedPublication)(other)
                prepared=publication.begin(fixture)
                reference=pypy_engine.start('goal2.tests.test_live_record_wire_t196:direct_live_reference',
                    prepared.state,raw,fixture,competitive)
                jobs=(CompetitiveJobs if competitive else WatchedJobs)(owner)
                try:
                    options=dict(reference_seed=257,delay_byte=0,record_draws=True,live_players=True)
                    token=jobs.start(**options) if competitive else jobs.start(fixture,**options)
                    deadline=time.monotonic()+600
                    seen=[]
                    while jobs.busy:
                        self.assertLess(time.monotonic(),deadline,'live-record worker did not finish')
                        seen.extend(jobs.poll(token));time.sleep(.001)
                    expected=reference.result(timeout=600)
                    self.assertEqual(jobs.outcome,expected,'full result/events/memory/RNG/seeds/year')
                    publication.complete(prepared.token,expected)
                    self.assertEqual(owner.state,other.state,'same once-only full career publication')
                    decisions=[e.data for e in seen if e.kind=='decision']
                    self.assertTrue(decisions)
                    changed_energy=changed_performance=False
                    for decision in decisions:
                        pairs=decision['player_records']
                        self.assertEqual([w for w,_ in pairs],decision['eleven']+decision['bench'])
                        self.assertEqual(len(pairs),20)
                        for word,encoded in pairs:
                            record=bytes.fromhex(encoded)
                            changed_energy|=record[14]!=initial.players[word][14]
                            changed_performance|=record[18:20]!=initial.players[word][18:20]
                    self.assertTrue(changed_energy);self.assertTrue(changed_performance)
                    with self.assertRaises(ValueError):jobs.poll(token)
                finally:jobs.close()

MISSING_SNAPSHOT_CHILD="""
import sys
from goal2.game.engine_server import read_packet,write_packet
from goal2.game.session_save import _json_value
out=sys.stdout.buffer
write_packet(out,{'kind':'ready','value':{'implementation':'synthetic-fault'}})
while True:
 packet=read_packet(sys.stdin.buffer)
 if packet is None:break
 request,payload=packet
 if request['op']=='open':write_packet(out,{'kind':'opened'})
 elif request['op']=='match':
  write_packet(out,{'kind':'event','value':_json_value({'kind':'decision','minute':45,'score':(0,0),
   'data':{'context':'half_time','eleven':list(range(1,12)),'bench':list(range(12,21))}})})
 elif request['op']=='quit':break
"""

@requires.need(**requires.WATCHED)
class MissingSnapshotProcess(unittest.TestCase):
    def test_real_fault_process_cannot_publish_or_replace_the_career(self):
        import sys,time
        from goal2.tests.test_campaign_competitive_match import state
        from goal2.tests.test_watched_publication import Owner
        from goal2.game.watched_jobs import WatchedJobs
        initial,raw=state();owner=Owner(initial,raw);before=copy.deepcopy(initial)
        jobs=WatchedJobs(owner,command=[sys.executable,'-u','-c',MISSING_SNAPSHOT_CHILD])
        try:
            token=jobs.start(Fixture(7,19,21),live_players=True)
            deadline=time.monotonic()+30
            with self.assertRaisesRegex(ValueError,'records|snapshot'):
                while jobs.busy:
                    self.assertLess(time.monotonic(),deadline,'fault process did not fail')
                    jobs.poll(token);time.sleep(.001)
            self.assertIsNone(jobs.outcome)
            self.assertIs(owner.state,initial);self.assertEqual(owner.state,before)
        finally:jobs.close()

if __name__=='__main__':unittest.main()
