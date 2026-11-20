"""[designed: T170ac/#810] Explicit native pacing, decisions and resume."""
import copy
import queue
import threading
import unittest

from goal2.game.native_driver import NativeMatchDriver
from goal2.game.native_season import SeasonHandoff
from goal2.tests.test_season_pitch_t170ab import frame


def event(kind='minute',data=None):return dict(kind=kind,minute=0,score=(0,0),data={} if data is None else data)


class Owner:
    frames_enabled=True
    def __init__(self):
        self.queue=queue.Queue();self.sent=[];self.number=10;self.closed=False;self.adopted=[];self.handoffs=0
        self.packet=dict(request=10,action='next',events=[event('kick_off')],frames=[],event_count=3,
                         decision=None,over=False,exhausted=False)
    def send(self,action,**values):self.sent.append((action,copy.deepcopy(values)))
    def handoff(self):
        self.handoffs+=1
        if self.handoffs!=1:raise ValueError('handoff already consumed')
        self.connection=SeasonHandoff(self.send,self.queue,self.packet);return self.connection
    def close(self):self.closed=True
    def adopt_resume(self,value,connection):
        assert connection is self.connection
        self.adopted.append(copy.deepcopy(value));return 'boundary'
    def reply(self,action='next',**values):
        self.number+=1;packet=dict(request=self.number,action=action,**values)
        self.queue.put(('season',packet));return packet
    def batch(self,frames=(),events=(),decision=None,total=3,over=False,exhausted=False):
        return self.reply(events=list(events),frames=list(frames),decision=decision,event_count=total,
                          over=over,exhausted=exhausted)


class Pacing(unittest.TestCase):
    def test_clock_and_paint_bound_execution_and_preserve_absolute_offsets(self):
        owner=Owner();driver=NativeMatchDriver(owner)
        self.assertEqual(driver.event_base,2);self.assertEqual(owner.handoffs,1)
        self.assertEqual(owner.sent,[]);driver.tick(0);self.assertEqual(owner.sent,[('next',{'count':1})])
        owner.batch(frames=[frame(0,3)]);sample=driver.tick(0)
        self.assertEqual(sample['sequence'],0);self.assertEqual(driver.shown(),[event('kick_off')])
        sample['players'][0][3]=99;self.assertNotEqual(driver.frame['players'][0][3],99)
        driver.tick(999);self.assertEqual(len(owner.sent),1)
        with self.assertRaises(ValueError):driver.painted(1)
        self.assertTrue(driver.painted(0));self.assertFalse(driver.painted(0))
        driver.tick(0);owner.batch(frames=[frame(1,3)])
        self.assertIsNone(driver.tick(.001));self.assertEqual(driver.tick(.02)['sequence'],1)
        self.assertEqual(driver.painted_sequence,0);driver.painted(1)
        driver.set_held(True);before=list(owner.sent);driver.tick(100);self.assertEqual(owner.sent,before)
        driver.set_held(False);driver.tick(100);self.assertEqual(len(owner.sent),3)
        driver.step_speed(99);self.assertEqual(driver.speed,5);driver.step_speed(-99);self.assertEqual(driver.speed,0)

    def test_quick_consumes_samples_but_never_defaults_a_decision(self):
        owner=Owner();driver=NativeMatchDriver(owner);driver.quick_result();driver.tick(0)
        self.assertEqual(owner.sent[-1],('next',{'count':32}))
        owner.batch(frames=[frame(0,3),frame(1,3)]);self.assertIsNone(driver.tick(0))
        self.assertEqual(len(driver.frames),2);self.assertEqual(driver.painted_sequence,-1)
        owner.batch(events=[event('decision',{'context':'set_piece','role':2})],decision=7,total=4)
        driver.tick(0);self.assertEqual(driver.status,'decision');count=len(owner.sent)
        driver.tick(999);self.assertEqual(len(owner.sent),count)
        with self.assertRaises(ValueError):driver.answer([])
        driver.answer({'taker':None});self.assertEqual(owner.sent[-1],('answer',{'decision':7,'answer':{'taker':None}}))
        with self.assertRaises(ValueError):driver.answer({})
        owner.reply('answer');driver.tick(0);self.assertEqual(owner.sent[-1],('next',{'count':32}))

    def test_pause_waits_for_paint_serializes_and_stopped_edits_stay_explicit(self):
        owner=Owner();driver=NativeMatchDriver(owner);driver.tick(0)
        self.assertTrue(driver.request_pause());self.assertFalse(driver.request_pause())
        owner.batch(frames=[frame(0,3)]);driver.tick(0)
        self.assertEqual(owner.sent[-1][0],'next');driver.painted(0);driver.tick(1)
        self.assertEqual(owner.sent[-1],('pause',{}));self.assertFalse(driver.request_pause())
        owner.reply('pause',paused=True);driver.tick(1)
        owner.batch(events=[event('decision',{'context':'pause'})],decision=7,total=4);driver.tick(1)
        self.assertEqual(driver.waiting['decision'],7)
        driver.answer({'edit_only':True,'tactics':{1:True}});owner.reply('answer');driver.tick(1)
        owner.batch(events=[event('decision',{'context':'pause','edited':True})],decision=8,total=5);driver.tick(1)
        self.assertEqual(driver.status,'decision');self.assertEqual(driver.waiting['decision'],8)
        driver.answer({});self.assertEqual(owner.sent[-1],('answer',{'decision':8,'answer':{}}))
        self.assertEqual(driver.pause_requests,1)

    def test_pause_drop_and_pure_answer_refusal_do_not_replay(self):
        owner=Owner();driver=NativeMatchDriver(owner);driver.request_pause();driver.tick(0)
        owner.reply('pause',paused=False,reason='over');driver.tick(0)
        self.assertEqual(driver.dropped_pauses,1);self.assertEqual(driver.message,'over')
        owner.batch(events=[event('decision',{'context':'half_time'})],decision=7,total=4);driver.tick(0)
        driver.answer({});owner.number+=1
        owner.queue.put(('season_error',dict(request=owner.number,error='pure control',lost=False)))
        driver.tick(0);self.assertEqual(driver.status,'decision');self.assertEqual(driver.waiting['decision'],7)
        self.assertEqual(sum(a=='answer' for a,_ in owner.sent),1)

    def test_completion_requires_final_drain_and_resume_once_without_duplicate_delta_path(self):
        owner=Owner();driver=NativeMatchDriver(owner)
        with self.assertRaises(ValueError):driver.resume()
        driver.tick(0);owner.batch(events=[event('end')],total=4,over=True);driver.tick(0)
        self.assertNotEqual(driver.status,'complete');owner.batch(total=4,over=True,exhausted=True);driver.tick(0)
        self.assertEqual(driver.status,'complete');self.assertEqual(len(driver.shown()),2)
        driver.resume()
        with self.assertRaises(ValueError):driver.resume()
        owner.reply('resume',state={'native':'only'},observation={'source':'only'});driver.tick(0)
        self.assertEqual(driver.status,'resumed');self.assertEqual(len(owner.adopted),1)
        driver.tick(999);driver.close();self.assertFalse(owner.closed)

    def test_corrupt_stale_loss_close_and_thread_controls(self):
        for corrupt in ('request','counter','frame','early_end'):
            owner=Owner();driver=NativeMatchDriver(owner);driver.tick(0)
            value=owner.batch(frames=[frame(0,3)])
            # The stand-in queue owns its packet; mutate it before owner delivery.
            if corrupt=='request':value['request']=True
            elif corrupt=='counter':value['event_count']=99
            elif corrupt=='frame':value['frames'][0]['sequence']=1
            else:value['exhausted']=True
            driver.tick(0);self.assertEqual(driver.status,'lost');self.assertTrue(owner.closed)
            count=len(owner.sent);driver.tick(100);self.assertEqual(len(owner.sent),count)
        owner=Owner();driver=NativeMatchDriver(owner);errors=[]
        def other():
            for call in (lambda:driver.tick(0),lambda:driver.painted(0),driver.request_pause,driver.resume,driver.close):
                try:call()
                except RuntimeError:errors.append(True)
        thread=threading.Thread(target=other);thread.start();thread.join(1);self.assertEqual(len(errors),5)
        driver.close();owner.batch(frames=[frame(0,3)]);driver.tick(1)
        self.assertEqual(driver.status,'closed');self.assertEqual(driver.frames,[])


class ResumeOwner(unittest.TestCase):
    def test_terminal_resume_stays_terminal_and_delivers_observation_once(self):
        from goal2.tests.test_native_season_t170aa import Pure,boundary
        helper=Pure();native,engine,p,data,keeper=helper.make();self.addCleanup(helper.doCleanups)
        helper.prematch(native,engine,p,data);native.controller.play(captain=None)
        engine.emit('answer');native.controller.receive(*native.replies.get_nowait())
        engine.emit('next',events=[event('minute')],decision=None,over=False,exhausted=False)
        native.controller.receive(*native.replies.get_nowait());connection=native.handoff()
        native.take_observations();packet=dict(request=8,action='resume',**boundary(p['state'],1,'deferred-rollover'))
        self.assertEqual(native.adopt_resume(packet,connection),'terminal')
        self.assertEqual(len(native.take_observations()),1);self.assertEqual(native.take_observations(),[])
        with self.assertRaises(ValueError):native.advance()
        with self.assertRaises(ValueError):connection.send('next',count=1)

    def test_same_call_adoption_and_old_connection_cannot_reach_next_match(self):
        from goal2.tests.test_native_season_t170aa import Pure,seed,boundary
        from goal2.game.season import canonical_hash
        from goal2.game import engine_tables
        from goal2.engine.original_match.image import Image,GAME_PTR,FIXTURES_PTR
        helper=Pure();native,engine,p,data,keeper=helper.make()
        # Move the helper's cleanup into this testcase, rather than leaving its owner alive.
        self.addCleanup(helper.doCleanups)
        helper.prematch(native,engine,p,data);native.controller.play(captain=None)
        engine.emit('answer');native.controller.receive(*native.replies.get_nowait())
        engine.emit('next',events=[event('minute')],decision=None,over=False,exhausted=False)
        native.controller.receive(*native.replies.get_nowait());old=native.handoff()
        native.take_observations();before=native.boundary_state
        good=dict(request=8,action='resume',**boundary(before,1,'complete'))
        bad=copy.deepcopy(good);bad['observation']['input_hash']='0'*64
        with self.assertRaises(ValueError):native.adopt_resume(bad,old)
        self.assertEqual(native.boundary_state,before);self.assertEqual(native.status,'handed_off')
        image=Image.from_state(before,engine_tables.load());game=image.far(GAME_PTR)
        image.memory[game+0x26:game+0x28]=(2).to_bytes(2,'little')
        image.memory[game+0x28:game+0x2A]=(3).to_bytes(2,'little')
        at=image.far(FIXTURES_PTR)+8;image.memory[at:at+8]=bytes((254,0,1,0,7,0,8,0))
        newer=image.state(engine_tables.load());good=dict(request=8,action='resume',**boundary(newer,1,'match'))
        good['observation']['input_hash']=canonical_hash(before)
        self.assertEqual(native.adopt_resume(good,old),'configuring')
        self.assertEqual(native.fixture.index,2);self.assertEqual(len(native.take_observations()),1)
        self.assertEqual(native.take_observations(),[])
        with self.assertRaises(ValueError):native.adopt_resume(good,old)
        with self.assertRaises(ValueError):old.send('next',count=1)
        engine._number=8;engine.emit('configure');native.poll()
        engine.emit('next',events=[event('decision',data)],decision=4,over=False,exhausted=False);native.poll()
        preview=copy.deepcopy(p);preview['state']=newer;preview['preview'].update(decision=4,state_hash=canonical_hash(newer))
        engine.emit('preview',**{k:v for k,v in preview.items() if k!='action'});native.poll()
        self.assertEqual(native.status,'prematch')
        native.controller.play(captain=None);engine.emit('answer');native.controller.receive(*native.replies.get_nowait())
        engine.emit('next',events=[event('minute')],decision=None,over=False,exhausted=False)
        native.controller.receive(*native.replies.get_nowait());second=native.handoff()
        with self.assertRaises(ValueError):old.send('observe')
        second.send('observe');self.assertEqual(engine.calls[-1],('observe',{}))


class PauseTransport(unittest.TestCase):
    def test_public_pause_is_guarded_and_typed_without_consuming_the_stream(self):
        from goal2.tests.test_season_pitch_t170ab import Worker,Packets,batch
        from goal2.game.season_worker import SeasonRequestError
        from goal2.engine.original_match.match import MatchError
        from goal2.game.engine_server import ProtocolError
        from unittest.mock import Mock,patch
        worker,match,ask=Worker().make();match.pause=Mock()
        with self.assertRaises(SeasonRequestError):ask('pause')
        ask('configure',frames=True);before=(worker.frame_sequence,worker.event_count,worker.decision)
        self.assertTrue(ask('pause')['paused']);match.pause.assert_called_once_with()
        self.assertEqual((worker.frame_sequence,worker.event_count,worker.decision),before)
        match.pause=Mock(side_effect=MatchError('native pause unavailable'))
        denied=ask('pause');self.assertFalse(denied['paused']);self.assertEqual(denied['reason'],'native pause unavailable')
        self.assertEqual((worker.frame_sequence,worker.event_count,worker.decision),before)
        for value in (dict(paused=True),dict(paused=False,reason='native guard')):
            parent=Packets().parent();parent._decode(parent._life,dict(kind='season',value=batch()),b'')
            with patch.object(parent,'_send'):parent.season_request('pause')
            kind,result=parent._decode(parent._life,dict(kind='season',value=dict(request=3,action='pause',**value)),b'')
            self.assertEqual(kind,'season');self.assertEqual(result['paused'],value['paused'])
        parent=Packets().parent();parent._decode(parent._life,dict(kind='season',value=batch()),b'')
        with patch.object(parent,'_send'):parent.season_request('pause')
        with self.assertRaises(ProtocolError):parent._decode(parent._life,dict(kind='season',value=dict(request=3,action='pause',paused=1)),b'')


if __name__=='__main__':unittest.main()
