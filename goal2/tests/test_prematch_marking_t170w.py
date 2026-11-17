"""[designed: T170w/#763; confirmed: T137/87d92501, F010/F031]
Native marking goals on one held Match; only metadata/digests enter logs.
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
    def test_inherit_zone_and_word_preserve_exact_types(self):
        class Match:
            def configure_route_entry(self, **fields): pass
            def answer(self, **fields): self.fields=fields
        m=Match();seam=PrematchSeam(m)
        for goal in (None,0,523):
            seam.set_marking(123,goal)
            self.assertEqual(m.fields,{'edit_only':True,'marking':{123:goal}})
        for goal in (False,True,'0',0.0,[],{}):
            self.assertRaises(ValueError,seam.set_marking,123,goal)


def initial_state(raw, unavailable=False):
    from goal2.engine.original_match.image import Image,PLAYERS_PTR,PLAYER_SIZE
    from goal2.game import engine_tables
    tables=engine_tables.load();image=Image.from_bytes(raw);bad=None
    if unavailable:
        country=image.managed_countries()[0]
        bad=next(w for w in image.squad(country)[11:] if image.players()[w][6]>=2)
        # Declared/hash-bound input variant before any SeasonSession/Match exists.
        at=image.far(PLAYERS_PTR)+PLAYER_SIZE*bad
        image.memory[at+14]=0;image.memory[at+16]|=0x80
    return image.state(tables),bad,image.sha256()


def mark_word(image,side,word,country):
    from goal2.engine.original_match import screens as S
    slot=image.squad(country).index(word)+1
    return image.rd(S.MARKING-2+40*side+2*slot)


def reached(status,word,goal):
    return not (status&64) if goal is None else bool(status&64) and word==goal


def marking_sequence(raw,via_seam=True):
    import sys
    from dataclasses import asdict
    from goal2.engine.original_match.image import Image
    from goal2.engine.original_match.machine import REGS,MEM_SIZE,Uc
    from goal2.game import engine_tables
    from goal2.game.season import SeasonSession
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    tables=engine_tables.load();initial,_,source_hash=initial_state(raw)
    session=SeasonSession(initial);assert session.advance().status=='match'
    m=session.pending_match;seam=PrematchSeam(m);events=[];entries=[];calls=[]
    def entered(replay):
        if not replay:entries.append([m.m.stack_word(6),m.m.stack_word(4)&255])
    def called(replay):
        if not replay:
            bp=m.m.stack_word(2);calls.append([m.m.frame_word(bp,8),m.m.frame_word(bp,6)&255])
    m.m.at('1771:4B61',entered);m.m.at('1771:49B8',called)
    def decision():
        for event in m.events():
            events.append(asdict(event))
            if event.kind=='decision':return event.data
        raise AssertionError('missing pre-match decision')
    d=decision();boundary=canonical_hash(session.state)
    out=lambda group:next(w for w in group if m._player(w,6)>=2 and m._available(w))
    words=[out(d['eleven']),out(d['bench'])]
    other=m.opts['second'] if m.opts['managed']==m.opts['first'] else m.opts['first']
    target=next(w for w in reversed(m._squad(other)[1:11]) if w and m._available(w))
    commands=[];stages=[]
    def edited(fields):
        at=len(events);d=decision();preview=m.records_after();image=Image.from_state(preview,tables)
        assert image.squad(m.opts['managed'])==d['eleven']+d['bench']
        actual=[]
        for word,goal in fields['marking'].items():
            status=image.players()[word][16];marked=mark_word(image,m.side,word,m.opts['managed'])
            assert reached(status,marked,goal)
            actual.append([word,status,marked])
        if 'substitutions' in fields:
            for off,on in fields['substitutions']:
                assert on in image.squad(m.opts['managed']) and off in d['pool']
        for word,goal in fields.get('positions',{}).items():
            assert image.players()[word][6]==goal
        if 'own_tactics' in fields:
            from goal2.tests.test_prematch_own_t170v import achieved
            for word,goals in fields['own_tactics'].items():
                assert all(achieved(image.players()[word][15],e,v) for e,v in goals.items())
        assert canonical_hash(session.state)==boundary
        assert not any(e['kind'] in ('minute','tick','substitution') for e in events[at:])
        stages.append(dict(preview_hash=canonical_hash(preview),marks=actual,
                           memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),
                           all16=[m.m.reg(r) for r in REGS]))
    for word in words:
        for goal in (None,0,0,target,target,None):
            fields={'edit_only':True,'marking':{word:goal}};commands.append(fields)
            if via_seam:seam.set_marking(word,goal)
            else:m.answer(**fields)
            edited(fields)
    off=next(w for w in d['bench'] if w!=words[1] and m._player(w,6)>=2 and m._available(w))
    on=out(d['pool'])
    mixed={'edit_only':True,'substitutions':[[off,on]],'positions':{on:2},
           'tactics':{1:not bool(m._tactics()&1)},'own_tactics':{on:{1:False,2:True}},
           'marking':{on:target,words[0]:0}}
    commands.append(mixed);m.answer(**mixed);edited(mixed)
    assert all([w,1] in entries for w in words) and all([w,1] in calls for w in words)
    if via_seam:seam.play()
    else:m.answer()
    after=asdict(next(m.events()))
    return dict(initial=initial,input_sha256=source_hash,boundary_hash=boundary,commands=commands,
                stages=stages,entries=entries,calls=calls,events_hash=canonical_hash(events),
                after_play_events_hash=canonical_hash([after]),
                memory=hashlib.sha256(m.m.read(0,MEM_SIZE)).hexdigest(),all16=[m.m.reg(r) for r in REGS])


def marking_guards(raw):
    from goal2.engine.original_match.machine import REGS
    from goal2.game.season_worker import SeasonWorker,SeasonRequestError
    initial,bad,source_hash=initial_state(raw,unavailable=True)
    worker=SeasonWorker();number=0
    def ask(action,**fields):
        nonlocal number
        number+=1
        return worker.dispatch(dict(op='season',request=number,action=action,**fields))
    ask('open',state=initial);ask('advance');ask('configure')
    while True:
        packet=ask('next',count=32)
        if packet['decision'] is not None:break
    m=worker.session.pending_match;n=packet['decision'];d=m.waiting
    word=next(w for w in d['eleven'] if m._player(w,6)>=2 and m._available(w))
    keeper=next(w for w in d['eleven'] if m._player(w,6)==0)
    assert bad in d['bench'] and not m._available(bad)
    def snapshot():
        return (m.memory_component(),[m.m.reg(r) for r in REGS],copy.deepcopy(m.st),copy.deepcopy(m.opts),
                copy.deepcopy(m.inputs),copy.deepcopy(m._replay_actions),m._replay_events,
                copy.deepcopy(m._frame_state()),worker.decision,worker.session.state)
    cases=[dict(edit_only=True,marking={word:False}),dict(edit_only=True,marking={word:True}),
           dict(edit_only=True,marking={word:65535}),dict(edit_only=True,marking={65535:0}),
           dict(edit_only=True,marking={keeper:None}),dict(edit_only=True,marking={d['pool'][0]:0}),
           dict(edit_only=True,marking={bad:0}),dict(edit_only=True,positions={word:1},marking={word:0}),
           dict(marking={word:0}),dict(edit_only=True,marking={word:0},quick=True)]
    for fields in cases:
        before=snapshot()
        try:ask('answer',decision=n,answer=fields)
        except SeasonRequestError:pass
        else:raise AssertionError('invalid marking input consumed decision')
        assert snapshot()==before
    ask('answer',decision=n,answer={'edit_only':True,'marking':{word:0}})
    while True:
        p=ask('next',count=32)
        if p['decision'] is not None:break
    assert p['decision']!=n
    return dict(cases=len(cases),input_sha256=source_hash,unavailable_word=bad)


class Actual(unittest.TestCase):
    def test_seam_equals_direct_records_memory_registers_and_events(self):
        raw=reference_raw();actual=pypy_engine.call(__name__+':marking_sequence',raw)
        direct=pypy_engine.call(__name__+':marking_sequence',raw,False)
        self.assertEqual(canonical_hash(actual.pop('initial')),canonical_hash(direct.pop('initial')))
        self.assertTrue(actual==direct)
        print('T170W_MARK '+json.dumps(actual,sort_keys=True),flush=True)
    def test_invalid_packets_are_pure_and_repairable(self):
        result=pypy_engine.call(__name__+':marking_guards',reference_raw())
        self.assertEqual(result['cases'],10)
        print('T170W_GUARDS '+json.dumps(result,sort_keys=True),flush=True)


class MarkingPipe(unittest.TestCase):
    make_engine=wire.Pipe.make_engine
    receive=wire.Pipe.receive
    def test_actual_pipe_preserves_goals_repair_and_current_previews(self):
        expected=pypy_engine.call(__name__+':marking_sequence',reference_raw())
        engine=self.make_engine();engine.season_open(expected['initial'])
        self.assertEqual(self.receive('ready')['implementation'],'PyPy');self.receive('season')
        engine.season_request('advance');self.receive('season');engine.season_request('configure');self.receive('season')
        for index,(fields,stage) in enumerate(zip(expected['commands'],expected['stages'])):
            while True:
                engine.season_request('next',count=32);packet=self.receive('season')
                if packet['decision'] is not None:break
            n=packet['decision'];word=next(iter(fields['marking']))
            engine.season_request('preview',decision=n);before=self.receive('season')['preview']['state_hash']
            if index:self.assertEqual(before,expected['stages'][index-1]['preview_hash'])
            engine.season_request('answer',decision=n,answer={'edit_only':True,'marking':{word:False}})
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
        self.assertEqual(canonical_hash(self.receive('season')['events']),expected['after_play_events_hash'])


class FailureBoundary(unittest.TestCase):
    def test_backend_marking_failure_still_invalidates(self):
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
                            answer={'edit_only':True,'marking':{'123':0}}),b'')
        self.assertTrue(sent[-1][1]['lost']);self.assertIsNone(server.season.session)


if __name__=='__main__':unittest.main()
