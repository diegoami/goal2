"""[designed: T170ag/#828] Completed reads cannot stand in for menu decisions."""
import copy
from dataclasses import FrozenInstanceError
from types import SimpleNamespace
import unittest

from goal2.game.completed_view import CompletedMatchView,CompletedMatchSnapshot,completed_result_hash
from goal2.game.native_driver import NativeMatchDriver
from goal2.game.season import canonical_hash
from goal2.tests.test_native_driver_t170ac import Owner,event
from goal2.tests.test_prematch_view_t170x import synthetic


def sample():
    from goal2.engine.original_match.image import Image,GAME_PTR,FIXTURES_PTR
    from goal2.game import engine_tables
    from goal2.game.watched_schema import RESULT_KEYS,KIT2_KEYS
    p,_=synthetic();image=Image.from_state(p['state'],engine_tables.load())
    def put(at,n,size=2):image.memory[at:at+size]=n.to_bytes(size,'little')
    put(image.DS*16+FIXTURES_PTR,0);put(image.DS*16+FIXTURES_PTR+2,0x7000)
    put(image.far(GAME_PTR)+0x26,1);put(image.far(GAME_PTR)+0x28,2)
    image.memory[0x70000:0x70008]=bytes([254,0,1,0,7,0,8,0])
    image.memory[image.DS*16+0xC1F]=0
    native=image.state(engine_tables.load())
    board=dict(statistics={n:[0,0] for n in ('corners','free_kicks','penalties','shots','on_target','saves',
        'fouls','bookings','red_cards','injuries')},bars=[[0,0],[0,0]],man_of_the_match=0,
        final_score=[1,0],screen_sha256='0'*64,ticks=1,seed=0)
    result={k:[] for k in ('goals','goals_disallowed','bookings','sendings_off','injuries','substitutions',
                           'commentary','decisions','inputs')}
    result.update(first=7,second=8,managed=7,index=1,kind=1,score=[1,0],half_time_score=[0,0],
        goal_counts=[1,0],man_of_the_match=0,man_of_the_match_name='',board=board,ticks=1,
        kickoff_seed=0,seed_after=0,image_sha256='0'*64,kit='4',draws=0,draws_digest='0'*64,
        squads_after={'7':list(range(1,21)),'8':list(range(21,41))},winner=0,score_90=None,
        extra_time=False,substitution_budget=[5,5],shootout=None,ports={'names':['all'],'calls':{}},players=[])
    for word in range(1,41):
        raw=image.players()[word];status=raw[16]
        result['players'].append(dict(player=word,team=int(word>20),confidence=[raw[12]]*2,
            energy=[raw[14]]*2,status=[status]*2,suspended=bool(status&128),
            carried_booking=bool(status&8),injured=raw[14]==0))
    result['decisions']=[dict(context='pre_match',minute=0,answer={'captain':None})]
    assert set(result)==RESULT_KEYS|KIT2_KEYS|{'ports'}
    packet=dict(request=9,action='completed_preview',state=native,result=result,
        preview=dict(schema='goal2/completed-preview/1',managed_country=7,event_count=4,frame_sequence=1,
                     state_hash=canonical_hash(native),result_hash=canonical_hash(result)))
    return packet


def build(packet,**changes):
    args=dict(request=9,event_count=4,frame_sequence=1,managed_country=7,fixture=(7,8,1,1),
              score=[1,0],board=copy.deepcopy(packet['result']['board']))
    args.update(changes);return CompletedMatchView.from_packet(packet,**args)


class Snapshot(unittest.TestCase):
    def test_native_history_tuples_survive_immutability_and_hash_binds_their_type(self):
        p=sample();p['result']['decisions'].append(dict(context='pre_match',minute=0,
            answer={'tactics':[(1,True)],'positions':[(2,'club')]}))
        p['preview']['result_hash']=completed_result_hash(p['result']);view=build(p)
        self.assertEqual(view.result,p['result'])
        self.assertIsInstance(view.result['decisions'][-1]['answer']['tactics'][0],tuple)
        p['result']['decisions'][-1]['answer']['tactics'][0]=[1,True]
        with self.assertRaises(ValueError):build(p)

    def test_strict_identity_counters_hashes_native_records_and_final_board(self):
        packet=sample();view=build(packet)
        self.assertEqual(view.snapshot.result,packet['result']);self.assertEqual(view.squad,tuple(range(1,21)))
        for mutate in (lambda p:p.update(request=True),lambda p:p['preview'].update(event_count=True),
            lambda p:p['preview'].update(frame_sequence=2),lambda p:p['preview'].update(managed_country=8),
            lambda p:p['preview'].update(state_hash='bad'),lambda p:p['preview'].update(result_hash='bad'),
            lambda p:p.update(decision=1),lambda p:p['result'].update(score=[0,0])):
            p=copy.deepcopy(packet);mutate(p)
            with self.assertRaises(ValueError):build(p)
        for field,value in (('managed',8),('index',2),('kind',2),('seed_after',1),
                            ('squads_after',{'7':list(reversed(range(1,21))),'8':list(range(21,41))}),
                            ('players',[]),('decisions','wrong')):
            p=copy.deepcopy(packet);p['result'][field]=value;p['preview']['result_hash']=canonical_hash(p['result'])
            with self.subTest(field=field),self.assertRaises(ValueError):build(p)
        for values in ({'request':False},{'event_count':3},{'frame_sequence':0},{'fixture':(8,7,1,1)},
                       {'score':[2,0]},{'board':dict(packet['result']['board'],ticks=2)}):
            with self.assertRaises(ValueError):build(packet,**values)

    def test_completed_native_context_and_result_are_detached_without_historical_relabelling(self):
        packet=sample();view=build(packet);state=view.display_state()
        self.assertEqual(view.team_context['in_match_menu_used'],0);self.assertIsNone(state.campaign)
        self.assertEqual(view.board,packet['result']['board']);self.assertEqual(view.opponents,tuple(range(21,41)))
        result=view.result;result['board']['statistics']['corners'].reverse();result['score'][0]=99
        state.players[1]=b'changed';packet['state']['header']='changed'
        self.assertEqual(view.result['score'],[1,0]);self.assertEqual(len(view.record(1)),20)
        with self.assertRaises(FrozenInstanceError):view.snapshot=None
        from goal2.game.watched_schema import validate_result
        with self.assertRaises(ValueError):validate_result(view.result) # Native captain history is not a legacy save.


def completed():
    packet=sample();owner=Owner();owner.managed_country=7
    owner.fixture=SimpleNamespace(side_a=7,side_b=8,index=1,kind=1)
    d=NativeMatchDriver(owner);d.tick(0)
    owner.batch(events=[event('full_time',packet['result']['board'])],total=4);d.tick(0)
    owner.batch(events=[dict(event('end'),score=[1,0])],total=5,over=True);d.tick(0)
    owner.batch(total=5,over=True,exhausted=True);d.tick(0)
    packet['preview'].update(event_count=5,frame_sequence=0)
    return owner,d,packet


def reply(owner,packet):
    return owner.reply('completed_preview',**{k:copy.deepcopy(v) for k,v in packet.items() if k not in ('request','action')})


class Driver(unittest.TestCase):
    def test_unpainted_completion_thread_and_rehashed_board_corruption(self):
        import threading
        from goal2.tests.test_season_pitch_t170ab import frame
        owner=Owner();owner.managed_country=7;owner.fixture=SimpleNamespace(side_a=7,side_b=8,index=1,kind=1)
        d=NativeMatchDriver(owner);d.quick_result();d.tick(0);d.quick=False;p=sample()
        owner.batch(frames=[frame(0,3)],events=[event('full_time',p['result']['board']),
            dict(event('end'),score=[1,0])],total=5,over=True,exhausted=True)
        self.assertIsNotNone(d.tick(0))
        with self.assertRaises(ValueError):d.request_completed_view()
        d.painted(0);d.tick(1);self.assertEqual(d.status,'complete')
        errors=[]
        def other():
            for call in (d.request_completed_view,lambda:d.completed_view):
                try:call()
                except RuntimeError:errors.append(True)
        t=threading.Thread(target=other);t.start();t.join(1);self.assertEqual(len(errors),2)
        owner,d,p=completed();d.request_completed_view()
        p['result']['board']['statistics']['corners'][0]=1
        p['preview']['result_hash']=canonical_hash(p['result']);reply(owner,p);d.tick(0)
        self.assertEqual(d.status,'lost');self.assertIsNone(d.completed_view)

    def test_explicit_covered_repeated_read_and_resume_invalidation(self):
        owner,d,p=completed();p['preview']['frame_sequence']=0
        sent=len(owner.sent)
        self.assertEqual(d.status,'complete');self.assertIsNone(d.completed_view)
        d.request_completed_view();d.set_held(True)
        with self.assertRaises(ValueError):d.resume()
        with self.assertRaises(ValueError):d.request_completed_view()
        before=(d.events,d.frames,d.shown_count);reply(owner,p);d.tick(0)
        self.assertEqual(d.status,'complete');self.assertIsNotNone(d.completed_view)
        self.assertEqual((d.events,d.frames,d.shown_count),before);self.assertEqual(len(owner.sent),sent+1)
        d.request_completed_view();reply(owner,p);d.tick(0);self.assertEqual(len(owner.sent),sent+2)
        d.resume();self.assertIsNone(d.completed_view)
        owner.reply('resume',state={'native':'only'},observation={'source':'only'});d.tick(0)
        self.assertEqual(d.status,'resumed');self.assertEqual(len(owner.adopted),1)

    def test_phase_refusal_repair_loss_and_close_never_fabricate_decisions(self):
        owner=Owner();d=NativeMatchDriver(owner)
        with self.assertRaises(ValueError):d.request_completed_view()
        owner,d,p=completed();p['preview']['frame_sequence']=0;d.request_completed_view();owner.number+=1
        owner.queue.put(('season_error',dict(request=owner.number,error='pure refusal',lost=False)))
        d.tick(0);self.assertEqual(d.status,'complete');self.assertIsNone(d.waiting)
        d.request_completed_view();reply(owner,p);d.tick(0);d.set_held(True)
        owner.queue.put(('death','lost'));d.tick(0);self.assertEqual(d.status,'lost');self.assertIsNone(d.completed_view)
        owner,d,p=completed();d.request_completed_view();d.close();reply(owner,p);d.tick(0)
        self.assertIsNone(d.completed_view);self.assertTrue(owner.closed)


class WorkerGuards(unittest.TestCase):
    def test_only_configured_exhausted_over_without_decision_can_read_and_detach(self):
        from goal2.game.season_worker import SeasonWorker,SeasonRequestError
        w=SeasonWorker();p=sample();reads=[]
        def ask(**kw):return w.dispatch(dict(op='season',request=9,action='completed_preview',**kw))
        with self.assertRaises(SeasonRequestError):ask()
        m=SimpleNamespace(over=False,waiting=None,opts={'managed':7},
            records_after=lambda:(reads.append('state') or copy.deepcopy(p['state'])),
            result=lambda:(reads.append('result') or copy.deepcopy(p['result'])))
        w.session=SimpleNamespace(pending_match=m)
        for configured,over,exhausted,decision,waiting in (
            (False,True,True,None,None),(True,False,False,None,None),(True,True,False,None,None),
            (True,True,True,1,{'context':'half_time'}),(True,True,True,None,{'context':'half_time'})):
            w.seam=object() if configured else None;w.stream=iter(()) if configured else None
            m.over=over;w.exhausted=exhausted;w.decision=decision;m.waiting=waiting
            with self.assertRaises(SeasonRequestError):ask()
            self.assertEqual(reads,[])
        w.seam=object();w.stream=iter(());m.over=w.exhausted=True;w.decision=m.waiting=None
        w.event_count=4;w.frame_sequence=1
        got=ask();self.assertEqual(got,p)
        got['result']['score'][0]=99;got['state']['header']='changed'
        self.assertEqual(ask(),p);self.assertEqual(reads,['state','result']*2)
        with self.assertRaises(SeasonRequestError):ask(decision=1)
        w.dispatch(dict(op='season',request=10,action='discard'))
        with self.assertRaises(SeasonRequestError):ask()


class Wire(unittest.TestCase):
    def test_parent_rejects_corrupt_completion_and_retains_busy_exclusion(self):
        import json
        from unittest.mock import patch
        from goal2.game.engine_process import EngineProcess
        from goal2.game.engine_server import ProtocolError
        for corrupt in (None,'request','schema','counter','result','hash','observation','json'):
            engine=EngineProcess(lambda *args:None);engine._life=object();engine._season_active=True
            engine._season_pitch=True;engine._season_pitch_events=4;engine._season_pitch_sequence=1
            with patch.object(engine,'_send'):
                with self.assertRaises(ValueError):engine.season_request('completed_preview',decision=1)
                self.assertFalse(engine.busy);engine.season_request('completed_preview')
                with self.assertRaises(ValueError):engine.season_request('resume')
            p=sample();native=p.pop('state');p['request']=1
            if corrupt=='request':p['request']=True
            elif corrupt=='schema':p['preview']['schema']='wrong'
            elif corrupt=='counter':p['preview']['event_count']=3
            elif corrupt=='result':p['result']['board']['ticks']=2
            elif corrupt=='hash':p['preview']['state_hash']='bad'
            elif corrupt=='observation':p['observation']={}
            payload=b'bad-json' if corrupt=='json' else json.dumps(native).encode()
            if corrupt is None:
                kind,decoded=engine._decode(engine._life,dict(kind='season',value=p),payload)
                self.assertEqual(kind,'season');self.assertEqual(decoded['state'],native);self.assertFalse(engine.busy)
            else:
                with self.assertRaises(ProtocolError):engine._decode(engine._life,dict(kind='season',value=p),payload)


if __name__=='__main__':unittest.main()
