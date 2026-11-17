"""[designed: T170x/#768] Current window data is detached, never a career."""
import copy
import hashlib
import json
import unittest
from dataclasses import FrozenInstanceError
from types import SimpleNamespace

from goal2.engine.original_match.image import Image
from goal2.game import engine_tables
from goal2.game.prematch_view import PrematchView
from goal2.game.season import canonical_hash
from goal2.tests import pypy_engine, requires
from goal2.tests.test_prematch_preview_t170s import reference_raw
from goal2.tests import test_season_worker_t170o as wire


def synthetic():
    """Declared data-only fixture; no backend or original mechanism is simulated."""
    from goal2.tests.test_season_session_t170b import state
    tables=engine_tables.load();image=Image.from_state(state(),tables)
    def write(at,n,size=2):image.memory[at:at+size]=n.to_bytes(size,'little')
    def ds(at,n,size=2):write(image.DS*16+at,n,size)
    for ptr,segment in ((0xA91B,0x5000),(0xA917,0x6000),(0xA923,0x6700),(0xA927,0x6800)):
        ds(ptr,0);ds(ptr+2,segment)
    squad=list(range(1,21));opponents=list(range(21,41));pool=list(range(2701,2781))
    for country,words in ((7,squad),(8,opponents)):
        for i,w in enumerate(words):write(0x60000+191*country+2*i,w)
    write(0x60000+191*7+0x2D,128,1);write(0x60000+191*8+0x2D,1,1)
    write(0x60000+191*7+0x2E,129,1);write(0x67001,1,1);ds(0x6D1A,1)
    for i,w in enumerate(pool):write(0x68000+2*(i+1),w)
    for w in squad+opponents+pool:
        at=0x50000+20*w;write(at,8 if w in opponents else 7,1)
        write(at+6,0 if w in (1,21) else 2,1);write(at+7,5,1);write(at+14,24,1)
    write(0x50000+20*12+14,0,1);write(0x50000+20*13+6,1,1)
    write(0x50000+20*2702,8,1)  # actual player's country, not managed defaults
    ds(0x9B34,7);ds(0x9B36,8);ds(0xC1E,1,1);ds(0xC1F,0,1)
    native=image.state(tables)
    data=dict(context='pre_match',eleven=squad[:11],bench=squad[11:],pool=pool,
              tactics=128,positions=[[w,image.players()[w][6]] for w in squad],
              player_records=[[w,image.players()[w].hex()] for w in squad],
              team_context={'match_set_up':1,'in_match_menu_used':0,'sides':[7,8]})
    packet=dict(action='preview',state=native,preview={'schema':'goal2/prematch-preview/1',
                'decision':3,'state_hash':canonical_hash(native)})
    return packet,data


def build(packet,data,decision=3,country=7):
    return PrematchView.from_preview(packet,data,decision=decision,managed_country=country)


class Pure(unittest.TestCase):
    def test_identity_hash_context_records_and_native_pool_refuse_mismatch(self):
        packet,data=synthetic();before=copy.deepcopy((packet,data))
        mutations=[lambda p,d:p['preview'].update(decision=2),lambda p,d:p['preview'].update(decision=True),
                   lambda p,d:p['preview'].update(schema='wrong'),lambda p,d:p['preview'].update(state_hash='wrong'),
                   lambda p,d:d.update(context='half_time'),lambda p,d:d.update(tactics=0),
                   lambda p,d:d['eleven'].reverse(),lambda p,d:d['pool'].reverse(),
                   lambda p,d:d['positions'][0].__setitem__(1,5),
                   lambda p,d:d['positions'][0].__setitem__(1,False),
                   lambda p,d:d['team_context'].update(match_set_up=True),
                   lambda p,d:d['player_records'][0].__setitem__(1,'00'*20),
                   lambda p,d:d['team_context'].update(match_set_up=0)]
        for mutate in mutations:
            p,d=copy.deepcopy((packet,data));mutate(p,d);snapshot=copy.deepcopy((p,d))
            with self.assertRaises(ValueError):build(p,d)
            self.assertEqual((p,d),snapshot)
        self.assertEqual((packet,data),before)
        for decision,country in ((True,7),(0,7),(3,False),(3,9)):
            with self.assertRaises(ValueError):build(packet,data,decision,country)
        packet['state']['memory']='not compressed native memory'
        packet['preview']['state_hash']=canonical_hash(packet['state'])
        with self.assertRaises(ValueError):build(packet,data)

    def test_detached_immutable_native_order_and_identity_only_display_state(self):
        packet,data=synthetic();view=build(packet,data)
        identities=SimpleNamespace(player_renames={2:'Owner'},manager_name='Manager')
        display=view.display_state(identities)
        self.assertIsNone(display.campaign);self.assertEqual(display.managed_squad,list(range(1,21)))
        self.assertEqual(view.pool,tuple(range(2701,2781)))
        data['pool'].reverse();packet['state']['initialised'].append([0,1])
        display.players[2]=b'changed';display.managed_squad.reverse();display.player_renames[2]='Changed'
        identities.player_renames[2]='Later';context=view.team_context;context['sides'].reverse()
        self.assertEqual(view.record(2)[6],2);self.assertEqual(view.squad,tuple(range(1,21)))
        self.assertEqual(view.team_context['sides'],[7,8]);self.assertEqual(identities.player_renames,{2:'Later'})
        self.assertEqual(view.display_state().player_renames,{})
        with self.assertRaises(FrozenInstanceError):view.decision=4
        with self.assertRaises(TypeError):view.players[2]=bytes(20)

    def test_native_marking_bench_pane_and_target_domains(self):
        packet,data=synthetic();view=build(packet,data)
        self.assertTrue(view.can_mark(14));self.assertFalse(view.can_mark(1))
        self.assertFalse(view.can_mark(12));self.assertFalse(view.can_mark(13))
        self.assertFalse(view.can_mark(2701));self.assertFalse(view.can_mark(14,pane='pool'))
        self.assertEqual(view.marking_targets,tuple(range(22,32)))
        self.assertEqual(view.captain_choices,tuple(range(1,12)))
        with self.assertRaises(ValueError):view.marking_word(2701)
        with self.assertRaises(ValueError):view.marking_word(True)
        image=Image.from_state(packet['state'],engine_tables.load())
        image.memory[image.DS*16+0xC1E]=0
        packet['state']=image.state(engine_tables.load());packet['preview']['state_hash']=canonical_hash(packet['state'])
        data['team_context']['match_set_up']=0
        self.assertFalse(build(packet,data).can_mark(14))

    def test_zero_word_is_not_inheritance_and_defaults_use_player_country(self):
        packet,data=synthetic();view=build(packet,data)
        self.assertIsNone(view.marking_goal(2));self.assertEqual(view.marking_word(2),0)
        self.assertFalse(view.own_value(2701,1));self.assertTrue(view.own_value(2702,1))
        image=Image.from_state(packet['state'],engine_tables.load())
        image.memory[image.far(0xA91B)+20*2+16]=64
        image.memory[image.far(0xA91B)+20*2701+15]=16
        packet['state']=image.state(engine_tables.load());packet['preview']['state_hash']=canonical_hash(packet['state'])
        data['player_records']=[[w,image.players()[w].hex()] for w in range(1,21)]
        zone=build(packet,data)
        self.assertEqual(zone.marking_goal(2),0)
        self.assertIs(zone.own_override(2701,1),False)
        self.assertFalse(zone.own_value(2701,1))
        image.memory[image.DS*16+0x9A42:image.DS*16+0x9A44]=(22).to_bytes(2,'little')
        packet['state']=image.state(engine_tables.load());packet['preview']['state_hash']=canonical_hash(packet['state'])
        self.assertEqual(build(packet,data).marking_goal(2),22)


def real_samples(raw,goaldat):
    """Actual retained worker; private packets only cross the local test pipe."""
    import sys
    from goal2.engine.original_match.machine import MEM_SIZE,REGS,Uc
    from goal2.engine.original_match.image import PLAYERS_PTR,COUNTRIES_PTR
    from goal2.game.season_worker import SeasonWorker
    from goal2.game.state import GameState
    from goal2.tests.test_prematch_marking_t170w import initial_state
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11) and Uc is None
    initial,bad,input_hash=initial_state(raw,unavailable=True);worker=SeasonWorker();counter=0
    def ask(action,**kw):
        nonlocal counter
        counter+=1;return worker.dispatch(dict(op='season',request=counter,action=action,**kw))
    ask('open',state=initial);ask('advance');ask('configure')
    m=worker.session.pending_match;boundary=canonical_hash(worker.session.state)
    def snapshot():
        return (m.m.read(0,MEM_SIZE),tuple(m.m.reg(r) for r in REGS),copy.deepcopy(m.st),
                copy.deepcopy(m.opts),copy.deepcopy(m.inputs),copy.deepcopy(m._replay_actions),m._replay_events,
                copy.deepcopy(m._frame_state()),worker.decision,worker.session.state)
    def next_decision():
        while True:
            p=ask('next',count=32)
            if p['decision'] is not None:
                return p['decision'],next(e['data'] for e in reversed(p['events']) if e['kind']=='decision')
    from goal2.game.player_card import card
    from goal2.game.country_card import card as team_card
    samples=[]
    def capture(n,d):
        before=snapshot();packet=ask('preview',decision=n)
        view=PrematchView.from_preview(packet,d,decision=n,managed_country=m.opts['managed'])
        displayed=view.display_state()
        # Independent current-record oracle reads the actual held machine.
        players=[m.m.read(m.m.far(PLAYERS_PTR)+20*w,20) for w in range(3061)]
        countries=[m.m.read(m.m.far(COUNTRIES_PTR)+191*c,191) for c in range(129)]
        oracle=GameState(players,countries,m.opts['managed'],m._squad(m.opts['managed']),
                         m.m.rd(0x7B62),m.m.rd(0x8336),{},b'',m.memory_component(),
                         starting_eleven=list(d['eleven']),country_tactics=m._tactics())
        assert displayed.players==oracle.players and displayed.countries==oracle.countries
        assert view.pool==tuple(m._pool()) and view.opponents==tuple(m._squad(m.opts['second'] if m.side==0 else m.opts['first']))
        assert view.captain_choices==tuple(w for w in d['eleven'] if m._available(w))
        assert view.marking_targets==tuple(w for w in view.opponents[1:11] if m._available(w))
        for w in view.squad:
            if w:
                assert view.marking_word(w)==m._marking_word(w)
                assert view.marking_goal(w)==(m._marking_word(w) if m._player(w,16)&64 else None)
                assert view.can_mark(w)==bool(m.m.rd(0xC1E,1) and m._player(w,6)>=2 and m._available(w))
        for w in view.squad+view.pool:
            if w:
                assert card(displayed,w,goaldat)==card(oracle,w,goaldat)
        for c in view.sides:
            assert team_card(displayed,c,goaldat,performance_context=view.team_context)==team_card(oracle,c,goaldat,performance_context=d['team_context'])
        assert view.can_mark(bad) is False
        assert snapshot()==before and canonical_hash(worker.session.state)==boundary
        samples.append(dict(packet=packet,data=copy.deepcopy(d),decision=n,managed=m.opts['managed'],
                            record_hash=hashlib.sha256(b''.join(players+countries)).hexdigest(),
                            memory_hash=hashlib.sha256(before[0]).hexdigest(),all16=before[1]))
    n,d=next_decision();capture(n,d)
    out=lambda group:next(w for w in group if m._available(w) and m._player(w,6)>=2)
    xi=out(d['eleven']);bench=out(d['bench']);incoming=out(d['pool'])
    other=m._squad(m.opts['second'] if m.side==0 else m.opts['first'])
    target=next(w for w in other[1:11] if m._available(w))
    edits=[{'substitutions':[[xi,bench]]},{'substitutions':[[bench,incoming]]},{'positions':{incoming:2}},
           {'positions':{incoming:'club'}},{'tactics':{1:not bool(m._tactics()&1)}},
           {'own_tactics':{incoming:{1:False,2:True}}},{'marking':{xi:0}},
           {'marking':{xi:target}},{'marking':{xi:None}}]
    for fields in edits:
        ask('answer',decision=n,answer=dict(edit_only=True,**fields));n,d=next_decision();capture(n,d)
    return dict(samples=samples,input_sha256=input_hash,boundary_hash=boundary)


class Actual(unittest.TestCase):
    def test_current_worker_edits_and_existing_decoders_are_pure(self):
        from pathlib import Path
        from goal2.data.goaldat import load
        path=Path(__file__).resolve().parents[2]/'.cache/GOAL.DAT'
        requires.require(files=(path,));goaldat=load(path.read_bytes())
        result=pypy_engine.call(__name__+':real_samples',reference_raw(),goaldat)
        self.assertEqual(len(result['samples']),10)
        for item in result['samples']:
            view=PrematchView.from_preview(item['packet'],item['data'],decision=item['decision'],managed_country=item['managed'])
            display=view.display_state()
            self.assertEqual(hashlib.sha256(b''.join(display.players+display.countries)).hexdigest(),item['record_hash'])
        # Stale packets cannot be paired with a newer decision, even if roster is unchanged.
        first,last=result['samples'][0],result['samples'][-1]
        with self.assertRaises(ValueError):
            PrematchView.from_preview(first['packet'],last['data'],decision=last['decision'],managed_country=last['managed'])
        print('T170X_VIEW '+json.dumps({'input_sha256':result['input_sha256'],'boundary_hash':result['boundary_hash'],
            'samples':[{k:v for k,v in x.items() if k not in ('packet','data')} for x in result['samples']]},sort_keys=True),flush=True)


class Pipe(unittest.TestCase):
    make_engine=wire.Pipe.make_engine
    receive=wire.Pipe.receive

    def test_parent_wire_preview_is_the_window_view_input(self):
        from goal2.tests.test_prematch_marking_t170w import initial_state
        native,_,_=initial_state(reference_raw())
        engine=self.make_engine();engine.season_open(native)
        self.assertEqual(self.receive('ready')['implementation'],'PyPy');self.receive('season')
        engine.season_request('advance');boundary=self.receive('season')['observation']['output_hash']
        engine.season_request('configure');self.receive('season')
        def current():
            while True:
                engine.season_request('next',count=32);packet=self.receive('season')
                if packet['decision'] is not None:break
            data=next(e['data'] for e in reversed(packet['events']) if e['kind']=='decision')
            engine.season_request('preview',decision=packet['decision']);preview=self.receive('season')
            return packet['decision'],data,preview,PrematchView.from_preview(preview,data,
                decision=packet['decision'],managed_country=7)
        n,data,preview,view=current()
        word=next(w for w in view.bench if view.can_mark(w))
        engine.season_request('answer',decision=n,answer={'edit_only':True,'marking':{word:0}});self.receive('season')
        newer,d2,p2,v2=current();self.assertEqual(v2.marking_goal(word),0)
        self.assertIsNone(v2.display_state().campaign)
        with self.assertRaises(ValueError):
            PrematchView.from_preview(preview,d2,decision=newer,managed_country=7)
        engine.season_request('preview',decision=newer)
        self.assertEqual(self.receive('season')['preview']['state_hash'],v2.state_hash)
        engine.season_request('observe')
        self.assertEqual(self.receive('season')['observation']['output_hash'],boundary)


if __name__=='__main__':unittest.main()
