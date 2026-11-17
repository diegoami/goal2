"""[designed: T170v/#756] Accepted native own overrides on one held Match.

[confirmed: archaeology46315dcf, F010/F031] False/True/None differ; original
inheritance uses player.country, including pool words. Only digests enter logs.
"""
import copy
import hashlib
import io
import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from goal2.game.prematch_seam import PrematchSeam
from goal2.game.season import canonical_hash
from goal2.tests import pypy_engine
from goal2.tests import test_season_worker_t170o as wire
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests.test_season_session_t170b import state, step


class Mapping(unittest.TestCase):
    def test_exact_three_values_and_invalid_types(self):
        class Match:
            def configure_route_entry(self,**fields): pass
            def answer(self,**fields): self.fields=fields
        m=Match();seam=PrematchSeam(m)
        for value in (False,True,None):
            seam.set_own_tactic(2564,1,value)
            self.assertEqual(m.fields,{'edit_only':True,'own_tactics':{2564:{1:value}}})
        for element,value in ((True,False),(5,True),(0,None),(1,0),(1,1),(1,'true')):
            self.assertRaises(ValueError,seam.set_own_tactic,121,element,value)


def achieved(byte,element,value):
    has=bool(byte & (1 << (element+3)));bit=bool(byte & (1 << (element-1)))
    return not has if value is None else has and bit is value


def own_sequence(raw,via_seam=True):
    import sys
    from dataclasses import asdict
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import REGS,MEM_SIZE,Uc
    from goal2.engine.original_match.match import OWN_TACTICS,TACTICS
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    tables=engine_tables.load();initial=Image.from_bytes(raw).state(tables)
    session=SeasonSession(initial);assert session.advance().status=='match'
    m=session.pending_match;seam=PrematchSeam(m);events=[];entries=[]
    def entry(replay):
        if not replay:entries.append([m.m.stack_word(6),m.m.stack_word(4)&255])
    m.m.at('1771:4B61',entry)
    def decision():
        for event in m.events():
            events.append(asdict(event))
            if event.kind=='decision':return event.data
        raise AssertionError('missing pre-match decision')
    d=decision();boundary=canonical_hash(session.state)
    out=lambda group:next(w for w in group if m._player(w,6)>=2)
    keeper=lambda group:next(w for w in group if m._player(w,6)==0)
    words=[out(d['eleven']),out(d['bench']),out(d['pool']),keeper(d['eleven']),keeper(d['pool'])]
    commands=[];stages=[]
    def edited(fields):
        at=len(events);d=decision();preview=m.records_after();image=Image.from_state(preview,tables)
        assert image.squad(m.opts['managed'])==d['eleven']+d['bench']
        actual=[]
        for word,goals in fields['own_tactics'].items():
            byte=image.players()[word][OWN_TACTICS]
            assert all(achieved(byte,e,v) for e,v in goals.items())
            country=m._player(word,0);default=m.m.read(m._country(country)+TACTICS,1)[0]
            for e,v in goals.items():
                if v is None:assert bool(byte & (1 << (e-1)))==bool(default & (1 << (e-1)))
            actual.append([word,country,byte,default])
        assert canonical_hash(session.state)==boundary
        assert not any(e['kind'] in ('minute','tick','substitution') for e in events[at:])
        stages.append(dict(preview_hash=canonical_hash(preview),records=actual,
                           memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),
                           all16=[m.m.reg(r) for r in REGS]))
    for word in words:
        for value in (False,True,None,None):
            fields={'edit_only':True,'own_tactics':{word:{1:value}}};commands.append(fields)
            if via_seam:seam.set_own_tactic(word,1,value)
            else:m.answer(**fields)
            edited(fields)
    # Positive mixed position/team/default/own edit; no role change in the XI.
    mixed={'edit_only':True,'positions':{words[1]:'club'},'tactics':{1:not bool(m._tactics()&1)},
           'own_tactics':{words[2]:{2:False},words[1]:{3:True}}}
    commands.append(mixed);m.answer(**mixed);edited(mixed)
    for word in words:assert any(e[0]==word for e in entries)
    if via_seam:seam.play()
    else:m.answer()
    after=asdict(next(m.events()))
    return dict(initial=initial,boundary_hash=boundary,commands=commands,stages=stages,entries=entries,
                events_hash=canonical_hash(events),after_play=after,
                memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])


def own_guards(raw):
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import REGS
    from goal2.game import engine_tables
    from goal2.game.season_worker import SeasonWorker,SeasonRequestError
    worker=SeasonWorker();number=0
    def ask(action,**fields):
        nonlocal number
        number+=1
        return worker.dispatch(dict(op='season',request=number,action=action,**fields))
    ask('open',state=Image.from_bytes(raw).state(engine_tables.load()));ask('advance');ask('configure')
    while True:
        packet=ask('next',count=32)
        if packet['decision'] is not None:break
    m=worker.session.pending_match;word=m.waiting['eleven'][2];n=packet['decision']
    def snapshot():
        return (m.memory_component(),[m.m.reg(r) for r in REGS],copy.deepcopy(m.st),copy.deepcopy(m.opts),
                copy.deepcopy(m.inputs),copy.deepcopy(m._replay_actions),m._replay_events,
                copy.deepcopy(m._frame_state()),worker.decision,worker.session.state)
    cases=[dict(edit_only=True,own_tactics={word:{1:1}}),dict(edit_only=True,own_tactics={65535:{1:True}}),
           dict(edit_only=True,own_tactics={word:{5:True}}),dict(own_tactics={word:{1:False}}),
           dict(edit_only=True,own_tactics={word:{1:True}},marking={word:0}),
           dict(edit_only=True,own_tactics={word:{1:True}},quick=True)]
    for fields in cases:
        before=snapshot()
        try:ask('answer',decision=n,answer=fields)
        except SeasonRequestError:pass
        else:raise AssertionError('invalid own input consumed decision')
        assert snapshot()==before
    ask('answer',decision=n,answer={'edit_only':True,'own_tactics':{word:{1:False}}})
    while True:
        p=ask('next',count=32)
        if p['decision'] is not None:break
    assert p['decision']!=n
    return len(cases)


class Actual(unittest.TestCase):
    def test_repeated_false_true_inherit_and_mixed_edits_equal_direct_answers(self):
        raw=reference_raw();actual=pypy_engine.call(__name__+':own_sequence',raw)
        direct=pypy_engine.call(__name__+':own_sequence',raw,False)
        self.assertEqual(canonical_hash(actual.pop('initial')),canonical_hash(direct.pop('initial')))
        self.assertEqual(actual,direct)
        print('T170V_OWN '+json.dumps({'stages':actual['stages'],'entries':actual['entries'],
              'memory':actual['memory'],'all16':actual['all16']},sort_keys=True),flush=True)

    def test_invalid_packets_are_pure_and_repairable(self):
        self.assertEqual(pypy_engine.call(__name__+':own_guards',reference_raw()),6)


class OwnPipe(unittest.TestCase):
    make_engine=wire.Pipe.make_engine
    receive=wire.Pipe.receive
    def test_actual_pipe_keeps_three_values_repair_and_current_previews(self):
        expected=pypy_engine.call(__name__+':own_sequence',reference_raw())
        engine=self.make_engine();engine.season_open(expected['initial'])
        self.assertEqual(self.receive('ready')['implementation'],'PyPy');self.receive('season')
        engine.season_request('advance');self.receive('season');engine.season_request('configure');self.receive('season')
        for index,(fields,stage) in enumerate(zip(expected['commands'],expected['stages'])):
            while True:
                engine.season_request('next',count=32);packet=self.receive('season')
                if packet['decision'] is not None:break
            n=packet['decision'];word=next(iter(fields['own_tactics']))
            engine.season_request('preview',decision=n);before=self.receive('season')['preview']['state_hash']
            if index:self.assertEqual(before,expected['stages'][index-1]['preview_hash'])
            engine.season_request('answer',decision=n,answer={'edit_only':True,'own_tactics':{word:{1:1}}})
            self.assertFalse(self.receive('season_error')['lost']);self.assertTrue(engine.season_active)
            engine.season_request('preview',decision=n)
            self.assertEqual(self.receive('season')['preview']['state_hash'],before)
            engine.season_request('answer',decision=n+1,answer=fields)
            self.assertFalse(self.receive('season_error')['lost'])
            engine.season_request('answer',decision=n,answer=fields);self.receive('season')
        while True:
            engine.season_request('next',count=32);packet=self.receive('season')
            if packet['decision'] is not None:break
        engine.season_request('preview',decision=packet['decision'])
        self.assertEqual(self.receive('season')['preview']['state_hash'],expected['stages'][-1]['preview_hash'])
        engine.season_request('observe')
        self.assertEqual(self.receive('season')['observation']['output_hash'],expected['boundary_hash'])
        engine.season_request('answer',decision=packet['decision'],answer={});self.receive('season')
        engine.season_request('next',count=1)
        self.assertEqual(self.receive('season')['events'],[expected['after_play']])


class FailureBoundary(unittest.TestCase):
    def test_backend_own_failure_still_invalidates(self):
        from goal2.game.engine_server import Server
        server=Server(io.BytesIO(),io.BytesIO());sent=[];server.send=lambda *args:sent.append(args)
        server.season.dispatch(dict(op='season',request=1,action='open',state=state()))
        match=SimpleNamespace(waiting={'context':'pre_match'})
        def fail(**fields):raise RuntimeError('backend failure')
        match.answer=fail
        with patch('goal2.game.season.route.play_round',return_value=step('match',state(),match=match)):
            server.season.dispatch(dict(op='season',request=2,action='advance'))
        server.season.decision=1
        server._season(dict(op='season',request=3,action='answer',decision=1,
                            answer={'edit_only':True,'own_tactics':{'1':{'1':True}}}),b'')
        self.assertTrue(sent[-1][1]['lost']);self.assertIsNone(server.season.session)


if __name__=='__main__':unittest.main()
