"""[designed: T170b/#652] Session ownership and detached boundary observations."""
import copy
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from goal2.game import engine_tables
from goal2.engine.original_match.image import Image
from goal2.engine.original_match.machine import MEM_SIZE
from goal2.engine.original_match.route import Keys,RoundStep
from goal2.game.season import SeasonSession,canonical_hash


def state():
    tables=engine_tables.load()
    image=Image.__new__(Image)
    image.header=bytes(0x78);image.load=0x100;image.DS=image.load+0x2581
    image.memory=bytearray(MEM_SIZE);image.tables=tables
    tables.place(image.memory,image.load)
    return image.state(tables)


def step(status,value,fixtures=(),pages=(),match=None,continuation=None):
    return RoundStep(status,copy.deepcopy(value),tuple(fixtures),tuple(pages),match,continuation)


class Session(unittest.TestCase):
    def test_order_keys_deltas_detachment_and_call_reset(self):
        value=state();keys=Keys({"site":13});keys.poll('site')
        match=SimpleNamespace(over=False);token=object()
        fixture={'fixture':1,'score':[2,1]};page={'pages':[{'text':['same']}]}
        first=step('match',value,(),(page,page),match,token)
        final=step('complete',value,(fixture,),(page,page,page))
        other=step('complete',value,(fixture,),(page,))
        with patch('goal2.game.season.route.play_round',side_effect=[first,other]) as play,patch('goal2.game.season.route.resume_round',return_value=final) as resume:
            session=SeasonSession(value,keys=keys)
            original=copy.deepcopy(value);value['initialised'].append([0,2])
            self.assertEqual(session.state,original)
            a=session.advance();self.assertEqual((a.call_number,a.status),(1,'match'))
            self.assertEqual(len(a.news_pages),2)
            self.assertIs(session.pending_match,match)
            for action in (session.advance,lambda:session.resume(object()),lambda:session.resume(match)):
                before=session.observe();self.assertRaises(ValueError,action);self.assertEqual(session.observe(),before)
            self.assertFalse(resume.called)
            a.news_pages[0]['pages'][0]['text'].append('changed')
            first.news_pages[1]['pages'][0]['text'].append('upstreamchanged')
            self.assertEqual(session.observe().news_pages,())
            match.over=True;b=session.resume(match)
            self.assertEqual(len(b.news_pages),1);self.assertEqual(b.played_fixtures[0]['score'],[2,1])
            b.played_fixtures[0]['score'][0]=99
            self.assertEqual(session.observe().played_fixtures,())
            self.assertRaises(ValueError,session.resume,match)
            c=session.advance();self.assertEqual((c.call_number,len(c.played_fixtures),len(c.news_pages)),(2,1,1))
            self.assertIs(play.call_args_list[0].args[2],keys);self.assertIs(play.call_args_list[1].args[2],keys)
            self.assertEqual(keys.read('site'),(13,'waiting'))
            self.assertEqual(c.input_hash,canonical_hash(original))
            self.assertEqual(c.output_hash,canonical_hash(original))
            detached=session.state;detached['header']='bad';self.assertEqual(session.state,original)

    def test_terminal_repeat_and_observation_never_construct_backend(self):
        value=state()
        with patch('goal2.game.season.route.play_round',return_value=step('deferred-rollover',value)) as play:
            session=SeasonSession(value);first=session.advance()
            with patch('goal2.engine.original_match.port.engine.PortMachine',side_effect=AssertionError('backend forbidden')):
                self.assertEqual(session.advance(),session.observe())
                self.assertEqual(session.advance().output_hash,first.output_hash)
                self.assertEqual(session.advance().call_number,1)
            self.assertEqual(play.call_count,1)

    def test_backend_rejection_keeps_session_and_queue_unchanged(self):
        value=state();match=SimpleNamespace(over=True);keys=Keys({'site':13});keys.poll('site')
        with patch('goal2.game.season.route.play_round',return_value=step('match',value,match=match,continuation=object())),patch('goal2.game.season.route.resume_round',side_effect=ValueError('wrong return frame')):
            session=SeasonSession(value,keys=keys);session.advance();before=session.observe()
            self.assertRaises(ValueError,session.resume,match)
            self.assertIs(session.pending_match,match);self.assertEqual(session.observe(),before)
            self.assertEqual(keys.waiting,13)

    def test_malformed_state_and_modified_tables_refuse(self):
        self.assertRaises(ValueError,SeasonSession,{'schema':'wrong'})
        tables=copy.deepcopy(engine_tables.load());tables.ds=bytes([tables.ds[0]^1])+tables.ds[1:]
        self.assertRaises(ValueError,SeasonSession,state(),tables)

def actual_boundaries(raw,waiting=None,expected='match'):
    """Actual PyPy dispatcher, no complete match, no original backend fallback."""
    import builtins,hashlib,sys
    assert sys.implementation.name=='pypy' and sys.version_info[:2]==(3,11)
    original_import=builtins.__import__
    def denied(name,*args,**kwargs):
        if name=='unicorn' or name.startswith('unicorn.'):
            raise ImportError('T170b positive Unicorn denial')
        return original_import(name,*args,**kwargs)
    builtins.__import__=denied
    try:__import__('unicorn')
    except ImportError:pass
    else:raise AssertionError('Unicorn denial inactive')
    from goal2.engine.original_match import route
    from goal2.engine.original_match.machine import REGS,MEM_SIZE,Uc
    assert Uc is None
    image=Image.from_bytes(raw);tables=engine_tables.load();value=image.state(tables)
    keys=Keys(route.DEFAULT_KEYS);keys.waiting=waiting
    reference_keys=Keys(route.DEFAULT_KEYS);reference_keys.waiting=waiting
    reference=route.play_round(value,tables,reference_keys)
    session=SeasonSession(value,tables,keys)
    transition=session.advance();assert transition.status==expected==reference.status
    assert session.state==reference.state
    assert transition.played_fixtures==reference.played_fixtures
    assert transition.news_pages==reference.news_pages
    assert keys.waiting==reference_keys.waiting
    receipt={'status':transition.status,'input_sha256':hashlib.sha256(raw).hexdigest(),
             'input_state_hash':canonical_hash(value),'output_state_hash':transition.output_hash,
             'fixture_count':len(transition.played_fixtures),'news_count':len(transition.news_pages),
             'rng_words':transition.rng_words,'waiting_key':keys.waiting,
             'direct_route_state_equal':True,'direct_deltas_equal':True,'unicorn_denied':True}
    if expected=='match':
        match=session.pending_match
        before=match.m.read(0,MEM_SIZE);registers={name:match.m.reg(name) for name in REGS}
        assert before==reference.match.m.read(0,MEM_SIZE)
        assert registers=={name:reference.match.m.reg(name) for name in REGS}
        for _ in range(3):
            observed=session.observe();detached=session.state
            detached['header']='caller mutation'
            assert observed.news_pages==observed.played_fixtures==()
            assert match.m.read(0,MEM_SIZE)==before
            assert {name:match.m.reg(name) for name in REGS}==registers
        assert session.pending_match is match and not match.over
        receipt.update(full_memory_sha256=hashlib.sha256(before).hexdigest(),
                       all16_registers=registers,observation_full_memory_unchanged=True,
                       observation_all16_unchanged=True,direct_entry_full_memory_equal=True,
                       direct_entry_all16_equal=True)
    elif expected=='deferred-rollover':
        with patch('goal2.engine.original_match.port.engine.PortMachine',side_effect=AssertionError('terminal backend forbidden')):
            for _ in range(3):
                assert session.advance()==session.observe()
                assert session.state==value and session.observe().call_number==1
        receipt['terminal_repeat_backend_denied']=True
    else:
        assert session.pending_match is None
        assert session.observe().played_fixtures==session.observe().news_pages==()
    assert 'unicorn' not in sys.modules
    return receipt


class ActualManagedEntry(unittest.TestCase):
    def test_real_pypy_managed_entry_observation_preserves_full_memory_and_all16(self):
        from goal2.engine.original_match.assets import REFERENCE,reference_image
        from goal2.tests import requires,pypy_engine
        from pathlib import Path
        requires.require(files=(REFERENCE['asset'],))
        raw=reference_image(Path(__file__).resolve().parents[2]/'.cache')
        observed=pypy_engine.call(__name__+':actual_boundaries',raw)
        self.assertEqual(observed['status'],'match')
        self.assertTrue(observed['observation_full_memory_unchanged'])
        self.assertTrue(observed['observation_all16_unchanged'])
        self.assertTrue(observed['direct_entry_full_memory_equal'])
        self.assertTrue(observed['direct_entry_all16_equal'])
        print('T170B_MANAGED '+__import__('json').dumps(observed,sort_keys=True),flush=True)


if __name__=='__main__':unittest.main()
