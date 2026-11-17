"""[designed: T170y/#770] Confirmed mutation ordering, no career publication."""
import copy
import hashlib
import json
import queue
import threading
import unittest

from goal2.game.prematch_controller import PrematchController
from goal2.game.prematch_view import PrematchView
from goal2.game.season import canonical_hash
from goal2.tests import pypy_engine
from goal2.tests.test_prematch_view_t170x import synthetic
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests import test_season_worker_t170o as wire


class Pure(unittest.TestCase):
    def make(self,send=None):
        sent=[]
        c=PrematchController(send or (lambda action,**v:sent.append((action,v))),7)
        p,d=synthetic();p['request']=10;c.attach(p,d,decision=3)
        return c,sent,p,d

    def reply(self,c,action,request,**values):
        c.receive('season',dict(action=action,request=request,**values))

    def test_single_flight_keeps_old_view_until_verified_preview(self):
        c,sent,p,d=self.make();before=c.view
        c.set_team_tactic(1,True)
        self.assertEqual(sent,[('answer',{'decision':3,'answer':{'edit_only':True,'tactics':{1:True}}})])
        self.assertIs(c.view,before)
        with self.assertRaises(ValueError):c.set_position(2,3)
        self.reply(c,'answer',11);self.assertEqual(sent[-1],('next',{'count':32}))
        newer=copy.deepcopy(d)
        self.reply(c,'next',12,decision=4,events=[{'kind':'decision','data':newer}])
        self.assertEqual(sent[-1],('preview',{'decision':4}));self.assertIs(c.view,before)
        p['request']=13;p['preview']['decision']=4
        c.receive('season',p)
        self.assertEqual(c.status,'ready');self.assertEqual(c.view.decision,4)
        self.assertFalse(c.pending)
        events=c.take_events();events[0]['data']['eleven'].reverse()
        self.assertEqual(c.take_events(),[]);self.assertEqual(c.view.eleven,tuple(range(1,12)))

    def test_helpers_and_captain_none_omission_are_exact_packets(self):
        cases=[('swap',(2,14),{'substitutions':[[2,14]]}),('exchange',(14,2701),{'substitutions':[[14,2701]]}),
               ('set_position',(2701,4),{'positions':{2701:4}}),('club_position',(2701,),{'positions':{2701:'club'}}),
               ('set_own_tactic',(14,1,False),{'own_tactics':{14:{1:False}}}),
               ('set_own_tactic',(14,1,None),{'own_tactics':{14:{1:None}}}),
               ('set_marking',(14,None),{'marking':{14:None}}),('set_marking',(14,0),{'marking':{14:0}})]
        for method,args,fields in cases:
            c,sent,_,_=self.make();getattr(c,method)(*args)
            self.assertEqual(sent[0],('answer',{'decision':3,'answer':dict(edit_only=True,**fields)}))
        for kwargs,answer in (({},{}),({'captain':None},{'captain':None}),({'captain':2},{'captain':2})):
            c,sent,_,_=self.make();c.play(**kwargs)
            self.assertEqual(sent[0],('answer',{'decision':3,'answer':answer}))
            self.reply(c,'answer',11);self.assertEqual(sent[-1],('next',{'count':1}))
            packet=dict(request=12,action='next',decision=None,events=[{'kind':'minute','data':{'minute':0}}],over=False,exhausted=False)
            c.receive('season',packet);self.assertEqual(c.status,'handoff');self.assertEqual(c.handoff,packet)
            self.assertEqual(c.take_events(),[])
            c.handoff['events'].clear();self.assertEqual(len(c.handoff['events']),1)
            with self.assertRaises(ValueError):c.set_marking(14,0)

    def test_pure_refusal_repairs_same_decision_and_native_play_refusal_refreshes(self):
        c,sent,p,d=self.make();before=c.view;c.edit(marking={2:True})
        c.receive('season_error',{'request':11,'error':'invalid marking','lost':False})
        self.assertEqual(c.status,'ready');self.assertIs(c.view,before);self.assertEqual(c.message,'invalid marking')
        c.set_marking(2,0);self.assertEqual(sent[-1][1]['decision'],3)
        c,sent,p,d=self.make();c.play(captain=None);self.reply(c,'answer',11)
        self.reply(c,'next',12,decision=None,events=[{'kind':'refused','data':{'reason':'invalid XI'}}],over=False,exhausted=False)
        self.assertEqual(sent[-1],('next',{'count':1}))
        self.reply(c,'next',13,decision=4,events=[{'kind':'decision','data':d}])
        p['request']=14;p['preview']['decision']=4;c.receive('season',p)
        self.assertEqual(c.status,'ready');self.assertEqual(c.view.decision,4);self.assertEqual(c.message,'invalid XI')

    def test_loss_malformed_stale_send_failure_and_detach_do_not_replay(self):
        for kind,value in [('death',{'code':1}),('error','bad'),
                           ('season_error',{'request':11,'error':'lost','lost':True}),
                           ('season',{'request':10,'action':'answer'}),
                           ('season',{'request':11,'action':'observe'})]:
            c,sent,_,_=self.make();c.set_marking(2,0);c.receive(kind,value)
            self.assertEqual(c.status,'lost');self.assertIsNone(c.view);self.assertEqual(len(sent),1)
            with self.assertRaises(ValueError):c.play()
        c,sent,p,d=self.make();c.set_marking(2,0);self.reply(c,'answer',11)
        self.reply(c,'next',12,decision=4,events=[{'kind':'decision','data':d}])
        p['request']=13;p['preview']['decision']=4;p['preview']['state_hash']='bad';c.receive('season',p)
        self.assertEqual(c.status,'lost');self.assertEqual(len(sent),3)
        def fail(*args,**kw):raise BrokenPipeError('closed')
        c,_,_,_=self.make(fail);c.set_marking(2,0);self.assertEqual(c.status,'lost')
        c,sent,_,_=self.make();c.set_marking(2,0);c.detach();c.receive('season',{'request':11,'action':'answer'})
        self.assertEqual(c.status,'detached');self.assertIsNone(c.view);self.assertEqual(len(sent),1)

    def test_wrong_thread_and_local_invalid_helpers_are_pure(self):
        c,sent,_,_=self.make();errors=[]
        def wrong():
            for action in (lambda:c.set_marking(2,0),lambda:c.receive('death',{})):
                try:action()
                except RuntimeError:errors.append(True)
        t=threading.Thread(target=wrong);t.start();t.join()
        self.assertEqual(len(errors),2);self.assertEqual(c.status,'ready');self.assertEqual(sent,[])
        for action in (lambda:c.edit(),lambda:c.edit(captain=2),lambda:c.set_position(2,True),
                       lambda:c.set_own_tactic(2,1,0),lambda:c.set_marking(2,False)):
            with self.assertRaises(ValueError):action()
        self.assertEqual(sent,[])

    def test_malformed_decision_batches_cannot_play_or_advance_waiting_match(self):
        for events,number in (([{'kind':'decision','data':synthetic()[1]}],None),
                              ([{'kind':'minute','data':{}},{'kind':'decision','data':synthetic()[1]}],4),
                              ([{'kind':'decision','data':dict(context='half_time')}],4),
                              ([],4)):
            c,sent,_,_=self.make();c.set_marking(2,0);self.reply(c,'answer',11)
            self.reply(c,'next',12,decision=number,events=events)
            self.assertEqual(c.status,'lost');self.assertEqual(len(sent),2)
            self.assertEqual(c.take_events(),[])


def actual_run(raw,coordinated=True,invalid_xi=False):
    import sys
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.game.season_worker import SeasonWorker,SeasonRequestError
    from goal2.tests.test_prematch_marking_t170w import initial_state
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    native,_,input_hash=initial_state(raw);worker=SeasonWorker();number=0;replies=[]
    def ask(action,**v):
        nonlocal number
        number+=1
        return worker.dispatch(dict(op='season',action=action,request=number,**v))
    def next_view():
        events=[]
        while True:
            p=ask('next',count=32);events.extend(p['events'])
            if p['decision'] is not None:break
        data=next(e['data'] for e in reversed(events) if e['kind']=='decision')
        return p['decision'],data,ask('preview',decision=p['decision']),events
    ask('open',state=native);ask('advance');ask('configure');n,d,p,_=next_view()
    m=worker.session.pending_match;identity=id(m);boundary=canonical_hash(worker.session.state)
    def sender(action,**v):
        try:replies.append(('season',ask(action,**v)))
        except SeasonRequestError as exc:replies.append(('season_error',{'request':number,'error':str(exc),'lost':False}))
    c=PrematchController(sender,m.opts['managed']);c.attach(p,d,decision=n)
    def pump():
        for _ in range(100):
            if not c.pending:return
            kind,value=replies.pop(0);c.receive(kind,value)
        raise AssertionError('coordinator did not settle')
    out=lambda group:next(w for w in group if m._player(w,6)>=2 and m._player(w,7)>=2 and m._available(w))
    xi,bench,on=out(d['eleven']),out(d['bench']),out(d['pool'])
    other=m._squad(m.opts['second'] if m.side==0 else m.opts['first']);target=next(w for w in other[1:11] if m._available(w))
    commands=[('set_team_tactic',(1,not bool(d['tactics']&1)),{'tactics':{1:not bool(d['tactics']&1)}}),
              ('swap',(xi,bench),{'substitutions':[[xi,bench]]}),
              ('exchange',(xi,on),{'substitutions':[[xi,on]]}),
              ('set_position',(on,2),{'positions':{on:2}}),('club_position',(on,),{'positions':{on:'club'}})]
    commands += [('set_own_tactic',(on,1,v),{'own_tactics':{on:{1:v}}}) for v in (False,True,None)]
    commands += [('set_marking',(on,v),{'marking':{on:v}}) for v in (0,target,None)]
    if invalid_xi:
        keeper=next(w for w in d['eleven'] if m._player(w,6)==0)
        commands=[('swap',(keeper,bench),{'substitutions':[[keeper,bench]]})]
    stages=[];events=[]
    for method,args,fields in commands:
        if coordinated:
            getattr(c,method)(*args);pump();assert c.status=='ready',c.message
            view=c.view;events.extend(c.take_events());n=view.decision
        else:
            ask('answer',decision=n,answer=dict(edit_only=True,**fields));n,d,p,ev=next_view();events.extend(ev)
            view=PrematchView.from_preview(p,d,decision=n,managed_country=m.opts['managed'])
        assert id(worker.session.pending_match)==identity and canonical_hash(worker.session.state)==boundary
        stages.append(dict(view=view.state_hash,memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),
                           all16=[m.m.reg(r) for r in REGS],squad=list(view.squad),pool=list(view.pool)))
    captain=None if invalid_xi else next(w for w in m.waiting['eleven'] if m._available(w))
    if coordinated:
        before=c.view;c.play(captain=65535);pump();assert c.status=='ready' and c.view is before
        c.play(captain=captain);pump();events.extend(c.take_events())
        if invalid_xi:assert c.status=='ready' and c.view.decision>n
        else:
            assert c.status=='handoff' and c.handoff['events']
            events.extend(c.handoff['events'])
        end_status=c.status
    else:
        try:ask('answer',decision=n,answer={'captain':65535})
        except SeasonRequestError:pass
        else:raise AssertionError('bad captain accepted')
        ask('answer',decision=n,answer={'captain':captain})
        if invalid_xi:
            n,d,p,ev=next_view();events.extend(ev);end_status='ready'
        else:
            p=ask('next',count=1);events.extend(p['events']);end_status='handoff'
    return dict(input_sha256=input_hash,stages=stages,events_hash=canonical_hash(events),end_status=end_status,
                memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])


class Actual(unittest.TestCase):
    def test_all_edit_arms_and_captain_play_equal_direct_worker(self):
        raw=reference_raw();actual=pypy_engine.call(__name__+':actual_run',raw)
        direct=pypy_engine.call(__name__+':actual_run',raw,False)
        self.assertEqual(actual,direct)
        print('T170Y_CONTROLLER '+json.dumps(actual,sort_keys=True),flush=True)

    def test_native_invalid_xi_play_returns_to_fresh_view(self):
        raw=reference_raw();actual=pypy_engine.call(__name__+':actual_run',raw,True,True)
        direct=pypy_engine.call(__name__+':actual_run',raw,False,True)
        self.assertEqual(actual,direct);self.assertEqual(actual['end_status'],'ready')


class Pipe(unittest.TestCase):
    make_engine=wire.Pipe.make_engine
    receive=wire.Pipe.receive

    def test_same_process_confirmed_edit_and_first_play_reply_handoff(self):
        from goal2.tests.test_prematch_marking_t170w import initial_state
        native,_,_=initial_state(reference_raw());engine=self.make_engine();engine.season_open(native)
        self.receive('ready');self.receive('season');engine.season_request('advance');self.receive('season')
        engine.season_request('configure');self.receive('season')
        while True:
            engine.season_request('next',count=32);p=self.receive('season')
            if p['decision'] is not None:break
        data=next(e['data'] for e in reversed(p['events']) if e['kind']=='decision')
        engine.season_request('preview',decision=p['decision']);preview=self.receive('season')
        c=PrematchController(engine.season_request,7);c.attach(preview,data,decision=p['decision']);pid=engine.pid
        def pump():
            while c.pending:
                kind,value=self.replies.get(timeout=120);c.receive(kind,value)
        word=next(w for w in c.view.bench if c.view.can_mark(w))
        c.set_marking(word,0);pump();self.assertEqual(c.status,'ready');self.assertEqual(c.view.marking_goal(word),0)
        c.set_marking(word,65535);pump();self.assertEqual(c.status,'ready');self.assertIn('target',c.message)
        c.play(captain=None);pump();self.assertEqual(c.status,'handoff');self.assertTrue(c.handoff['events'])
        self.assertEqual(engine.pid,pid);self.assertTrue(engine.season_active)


if __name__=='__main__':unittest.main()
