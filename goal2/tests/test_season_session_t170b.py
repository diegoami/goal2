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

if __name__=='__main__':unittest.main()
