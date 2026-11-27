"""[designed: owner#777/T232] Original-strength extras on one copied request."""
import copy,unittest
from unittest.mock import patch
from goal2.tests import requires
from goal2.tests.pypy_engine import call
from goal2.tests import test_assistant_pipe_t183c as previous


def native_extras(value,places):
    from goal2.game.best_twenty import recommend
    from goal2.tests import test_best_twenty_t183a as original
    with patch.object(original,'recommend',side_effect=lambda state:recommend(state,extra_places=places)):
        return original.native(value)


@requires.need(**requires.HALFTIME)
class NativeExtras(unittest.TestCase):
    def test_state_is_exactly_original_twenty_and_extra_groups_are_balanced(self):
        from goal2.engine.original_match import Image
        from goal2.game import engine_tables
        value=previous.state();base=call('goal2.tests.test_best_twenty_t183a:native',value)
        for places in (2,):
            with self.subTest(places=places):
                answer=call(__name__+':native_extras',value,places)
                self.assertEqual(answer['state'],base['state'])
                self.assertEqual(answer['squad'],base['squad']);self.assertEqual(answer['pool'],base['pool'])
                self.assertEqual(len(answer['extra_squad']),places)
                words=[w for w in answer['extra_squad'] if w is not None]
                self.assertEqual(len(words),places);self.assertEqual(len(set(words)),places)
                self.assertTrue(set(words)<=set(answer['pool']))
                image=Image.from_state(answer['state'],engine_tables.load());players=image.far(0xA91B)
                lines=[image.memory[image.DS*16+0xD5C+image.memory[players+20*w+6]] for w in words]
                self.assertNotIn(0,lines)
                counts=[lines.count(line) for line in (1,2,3)]
                self.assertLessEqual(max(counts)-min(counts),1)

    def test_original_instruction_strengths_choose_exact_same_additional_words(self):
        from goal2.tests.test_best_twenty_t183a import OriginalAction,records
        from goal2.core.screens import INSERT
        from goal2.engine.original_match import Image
        from goal2.engine.original_match.machine import Machine
        from goal2.game import engine_tables
        from goal2.game.extended_squad import balanced_extras
        d=OriginalAction().source();tables=engine_tables.load()
        value=Image.from_memory_component(d.wait.state.memory_component()).state(tables)
        answer=call(__name__+':native_extras',value,2)
        d.goto('select-squad');d.press(INSERT,expect=('select-squad',))
        image=Image.from_memory_component(d.wait.state.memory_component())
        expected=records(image);actual=records(Image.from_state(answer['state'],tables))
        self.assertEqual(actual,expected)
        m=Machine(image.memory,image.load);ss,sp=m.seg(0x3052),0x3000;rows=[]
        for word in expected['pool']:
            m.far_call('1771:377E',(word,),'0791:E788',ss,sp);m.set_reg('bp',0x3456);m.run(m.lin('0791:E788'))
            strength=m.reg('ax')
            m.far_call('1771:3216',(word,),'0791:E788',ss,sp);m.set_reg('bp',0x3456);m.run(m.lin('0791:E788'))
            available=not bool(m.reg('ax')&255)
            position=image.memory[image.far(0xA91B)+20*word+6]
            rows.append(dict(id=word,line=image.memory[image.DS*16+0xD5C+position],strength=strength,available=available))
        self.assertEqual(answer['extra_squad'],balanced_extras(rows,2))

    def test_candidate_installs_only_valid_requested_extra_metadata(self):
        from goal2.game.extended_squad import resized,validate
        from goal2.game.best_twenty_state import prepare,candidate
        m=previous.model();m.state=resized(m.state,22);p=prepare(m.state);before=copy.deepcopy(m.state)
        answer=call(__name__+':native_extras',p.native,2);selected=candidate(p,answer)
        self.assertEqual(selected.extra_squad,answer['extra_squad']);validate(selected)
        self.assertEqual(m.state,before)
        for value in ([None], [answer['squad'][0],None],[True,None],
                      [answer['pool'][0],answer['pool'][0]]):
            bad=copy.deepcopy(answer);bad['extra_squad']=value
            with self.subTest(value=value):self.assertRaises(ValueError,candidate,p,bad)
        missing=copy.deepcopy(answer);del missing['extra_squad']
        self.assertRaises(ValueError,candidate,p,missing)


@requires.need(**requires.HALFTIME)
class PipeExtras(unittest.TestCase):
    engine=previous.PipeCase.engine
    wait=previous.PipeCase.wait

    def test_real_shared_pipe_matches_direct_and_default_remains_compatible(self):
        value=previous.state();e,q=self.engine(denied=True)
        for places in (2,0):
            expected=call(__name__+':native_extras',value,places)
            number=e.assistant(value,extra_places=places);reply=self.wait(q,'assistant')
            self.assertEqual(reply['request'],number);self.assertEqual(reply['result'],expected)
            if places:self.assertEqual(len(reply['result']['extra_squad']),places)
            else:self.assertNotIn('extra_squad',reply['result'])
            if 'pid' in locals():self.assertEqual(e.pid,pid)
            pid=e.pid

    def test_invalid_count_refuses_without_starting_the_child(self):
        e,q=self.engine()
        for places in (True,1,3,4,5,'4'):
            with self.subTest(places=places):self.assertRaises(ValueError,e.assistant,previous.state(),extra_places=places)
        self.assertIsNone(e.process)

    def test_completed_extra_reply_can_be_cancelled_without_publishing(self):
        e,q=self.engine('cancel');number=e.assistant(previous.state(),extra_places=2)
        self.assertTrue(e.cancel_assistant(number));reply=self.wait(q,'assistant_cancelled')
        self.assertEqual(reply['request'],number);self.assertFalse(e.busy)


def fake_extras(mode):
    """Host schema control only; plays no native operation."""
    import os,sys,json
    from goal2.game.engine_server import read_packet,write_packet
    from goal2.game.season import canonical_hash
    incoming,out=sys.stdin.buffer,sys.stdout.buffer
    write_packet(out,{'kind':'ready','value':{'implementation':'schema control','version':[3,11],'pid':os.getpid()}})
    while True:
        packet=read_packet(incoming)
        if packet is None:return
        header,payload=packet
        if header['op']=='quit':return
        if header['op']!='assistant':continue
        state=json.loads(payload.decode('utf8'))
        result=dict(allowed=True,refusal=None,country=4,manager=1,squad=list(range(61,81)),
                    pool=list(range(2561,2641)),changed=False,recruited=[],calls={'0791:DC7E':1})
        words=[2561,2562]
        if mode=='count':words=words[:1]
        elif mode=='duplicate':words=[2561,2561]
        elif mode=='bool':words=[True,None]
        elif mode=='foreign':words=[3060,None]
        if mode!='missing':result['extra_squad']=words
        write_packet(out,{'kind':'assistant','value':dict(request=header['request'],input_hash=header['input_hash'],
                     output_hash=canonical_hash(state),result=result)},payload)


@requires.need(**requires.HALFTIME)
class ReplyGuards(unittest.TestCase):
    wait=previous.PipeCase.wait
    def test_malformed_or_unsolicited_extra_selection_fails_closed(self):
        import queue,sys
        from goal2.game.engine_process import EngineProcess
        for mode in ('count','duplicate','bool','foreign','missing','unrequested'):
            with self.subTest(mode=mode):
                q=queue.Queue();e=EngineProcess(lambda k,v:q.put((k,v)),command=[sys.executable,'-u','-m',__name__,'--fake',mode])
                try:
                    e.assistant(previous.state(),extra_places=0 if mode=='unrequested' else 2)
                    reply=self.wait(q,'death')
                    self.assertIn('assistant',reply['error'])
                    self.assertFalse(e.busy)
                finally:e.close()


if __name__=='__main__':
    import sys
    if len(sys.argv)==3 and sys.argv[1]=='--fake':fake_extras(sys.argv[2])


# Exercise the real owner bridge in expanded mode, retaining the established
# Qt lifecycle controls rather than treating a pipe result as UI publication.
import sys
if sys.implementation.name != "pypy":
    from goal2.tests import test_ui_assistant_t183c as ui_previous


    @requires.need(**requires.HALFTIME)
    class ExpandedOwnerUI(unittest.TestCase):
        setUpClass=classmethod(ui_previous.AssistantUI.setUpClass.__func__)
        tearDownClass=classmethod(ui_previous.AssistantUI.tearDownClass.__func__)
        cleanup=ui_previous.AssistantUI.cleanup
        key=ui_previous.AssistantUI.key
        until=ui_previous.AssistantUI.until
        finished=ui_previous.AssistantUI.finished
        gated=ui_previous.AssistantUI.gated
        click_assistant=ui_previous.AssistantUI.click_assistant

        def setUp(self):
            from goal2.game.extended_squad import resized
            ui_previous.AssistantUI.setUp(self)
            self.model.state=resized(self.model.state,22)

        def test_actual_a_publishes_balanced_extras_with_capacity_feedback(self):
            from PySide6.QtCore import Qt
            from goal2.game.best_twenty_state import prepare,candidate
            from goal2.tests.ui_assertions import assert_fits
            p=prepare(self.model.state)
            expected=candidate(p,call(__name__+':native_extras',p.native,2))
            self.key(Qt.Key.Key_A);self.finished()
            self.assertEqual(self.model.state,expected)
            self.assertEqual(len(self.model.state.extra_squad),2)
            self.assertIn('Filled 2 of 2',self.screen.note.text())
            self.assertIn('22',self.screen.note.text())
            assert_fits(self,self.win)

        def test_capacity_change_while_preparing_cannot_publish(self):
            from goal2.game.extended_squad import resized
            entered,release,control=self.gated()
            try:
                with control:
                    self.click_assistant();self.assertTrue(entered.wait(5))
                    self.model.state=resized(self.model.state,20)
                    expected=copy.deepcopy(self.model.state)
                    release.set();self.finished()
                self.assertEqual(self.model.state,expected)
                self.assertEqual(self.model.state.extra_squad,[])
                self.assertIn('career changed',self.screen.note.text())
            finally:release.set()

        def test_cancel_before_send_preserves_all_empty_extra_places(self):
            ui_previous.AssistantUI.test_heartbeat_and_cancel_before_send_never_publish(self)

        def test_career_replacement_cannot_publish_expanded_candidate(self):
            ui_previous.AssistantUI.test_close_and_career_replacement_cannot_publish_old_reply(self)
