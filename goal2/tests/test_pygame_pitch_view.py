"""[designed: T83] Real SDL pixel/causal playback and saved-byte controls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from goal2.desktop.match_view import Display
from goal2.desktop import pygame_viewer as viewer

ROOT = Path(__file__).resolve().parents[2]


def sample(sequence=0, watermark=0):
    # [designed] Asymmetric synthetic oracle derived independently from T81 raw signed contract.
    return dict(version=1, sequence=sequence, watermark=watermark, minute=7+sequence,
        score=[1,0], subtick=36, threshold=45, remaining=91, selector=1,
        attack=[1,-1], sentinel=11, ball=[-4,13,False],
        players=[[s, int(s<=11), s if s<=11 else s-11, 100+s,
                  11,0,13,True] for s in range(1,23)])


def pitch():
    d=Display('owned')
    d.accept(['owned',0,'start',['First','Second']])
    # [designed] Assertion provides a behavioral before-failure rather than import ERROR.
    assert callable(getattr(viewer,'render_pitch',None)), 'numbered pitch renderer missing'
    d.accept(['owned',1,'pitch',{'rate':60}])
    return d


def send(d,kind,value):d.accept(['owned',d.sequence,kind,value])


class PitchPixels(unittest.TestCase):
    def setUp(self):
        import pygame
        pygame.init()
        self.screen=pygame.display.set_mode((1000,720))
        self.font=pygame.font.Font(None,24)

    def tearDown(self):
        import pygame
        pygame.quit()

    def pixel(self,x,y):return tuple(self.screen.get_at((x,y)))[:3]

    def test_independent_axes_team_labels_ball_movement_half_and_rebinding(self):
        import pygame
        d=pitch();f=sample()
        f['players'][0]=[1,1,1,101,-3,-21,0,False]
        f['players'][21]=[22,0,11,122,5,25,13,False]
        send(d,'frame',f);self.assertTrue(d.advance(0));viewer.render_pitch(self.screen,self.font,d)
        pygame.display.flip();d.rendered()
        # [derived: T81] Independent fixed [y,x], positive right/down; no project() oracle reuse.
        for point,color in [((269,231),(245,105,45)),((775,367),(45,135,245))]:
            self.assertEqual(self.pixel(point[0]+8,point[1]),color,'signed team marker pixels differ')
        self.assertEqual(self.pixel(643,214),(255,244,161),'signed ball pixels differ')
        for point,label in [((269,231),'1'),((775,367),'11')]:
            expected=pygame.Surface((28,28));expected.fill((26,100,57))
            pygame.draw.circle(expected,(10,20,27),(14,14),13)
            pygame.draw.circle(expected,(245,105,45) if label=='1' else (45,135,245),(14,14),11)
            text=self.font.render(label,True,(255,255,255));expected.blit(text,text.get_rect(center=(14,14)))
            actual=self.screen.subsurface((point[0]-14,point[1]-14,28,28))
            self.assertEqual(pygame.image.tobytes(actual,'RGB'),pygame.image.tobytes(expected,'RGB'),'readable local slot pixels differ')
        old=pygame.image.tobytes(self.screen,'RGB')
        g=copy.deepcopy(f);g.update(sequence=1,minute=46,remaining=45,selector=0,attack=[-1,1])
        g['players'][0][3]=777;g['players'][0][4:6]=[-2,-20];g['ball']=[-3,14,False]
        send(d,'frame',g);self.assertFalse(d.advance(.001));self.assertEqual(d.consumed,0)
        self.assertTrue(d.advance(1));viewer.render_pitch(self.screen,self.font,d);pygame.display.flip();d.rendered()
        self.assertNotEqual(pygame.image.tobytes(self.screen,'RGB'),old)
        self.assertEqual(self.pixel(280+8,248),(245,105,45),'half/rebind must not rotate or interpolate')
        self.assertEqual(d.frame['players'][0][3],777);self.assertEqual(d.consumed,1)

    def test_field_bounds_visibility_and_unknown_state(self):
        d=pitch();f=sample();f['ball']=[11,0,True]
        send(d,'frame',f);d.advance(0);viewer.render_pitch(self.screen,self.font,d)
        self.assertEqual(self.pixel(93,160),(213,231,204),'left playing-grid boundary')
        self.assertEqual(self.pixel(907,160),(213,231,204),'right playing-grid boundary')
        self.assertEqual(self.pixel(200,146),(213,231,204),'top playing-grid boundary')
        self.assertEqual(self.pixel(200,418),(213,231,204),'bottom playing-grid boundary')
        self.assertEqual(self.pixel(508,469),(18,28,37),'sentinel player must be hidden')
        self.assertNotEqual(self.pixel(500,469),(255,244,161),'sentinel ball must be hidden')
        g=copy.deepcopy(f);g['sequence']=1;g['players'][0][4:8]=[11,1,255,False];g['ball']=[10,2,False]
        send(d,'frame',g);d.advance(1);viewer.render_pitch(self.screen,self.font,d)
        self.assertEqual(self.pixel(519,469),(245,105,45),'non-sentinel out-of-field/unknown state must draw')
        self.assertEqual(self.pixel(522,452),(255,244,161),'non-sentinel ball must draw')

    def test_watermark_minute_terminal_tail_and_bounded_queue(self):
        d=pitch()
        for minute,text in [(0,'Kickoff'),(90,'FULL TIME')]:
            send(d,'event',dict(kind='commentary',minute=minute,score=[0,0],data={'text':text}))
        send(d,'event',dict(kind='end',minute=90,score=[1,0],data={}))
        f=sample(watermark=1);send(d,'frame',f)
        self.assertEqual(d.visible().events,[],'ingress must not leak before first pose')
        d.advance(0);viewer.render_pitch(self.screen,self.font,d)
        self.assertEqual(d.visible().lines()[2],'7 min   1 — 0')
        self.assertNotIn('90 min FULL TIME',d.visible().lines(),'future commentary leaked before watermark')
        self.assertEqual(d.consumed,-1,'selection/queueing must not acknowledge an unseen frame')
        import pygame
        expected=self.font.render('7 min   1 — 0',True,(232,239,229))
        label=pygame.Surface(expected.get_size());label.fill((18,28,37));label.blit(expected,(0,0))
        self.assertEqual(pygame.image.tobytes(self.screen.subsurface((20,62,*expected.get_size())),'RGB'),pygame.image.tobytes(label,'RGB'),'readable min label pixels differ')
        pygame.display.flip();d.rendered();self.assertEqual(d.consumed,0)
        send(d,'complete',{'board':{'statistics':{},'bars':[]},'ratings':[[],[]],'man_of_the_match':'A'})
        self.assertIn('90 min FULL TIME',d.visible().lines());self.assertEqual(d.frame['sequence'],0)
        other=pitch()
        for n in range(64):send(other,'frame',sample(n))
        with self.assertRaisesRegex(ValueError,'backlog'):send(other,'frame',sample(64))
        self.assertEqual(len(other.frames),64)

    def test_accumulated_target_cadence_and_country_color_association(self):
        import pygame
        d=pitch()
        for n in range(5):send(d,'frame',sample(n))
        self.assertTrue(d.advance(0))
        # [designed] Small scheduler lateness must not reset the target and halve playback rate.
        for instant in (.018,.034,.051,.068):
            self.assertTrue(d.advance(instant),'deadline drift reduced the fixed playback target')
        viewer.render_pitch(self.screen,self.font,d)
        for x,name,color in [(40,'First',(45,135,245)),(520,'Second',(245,105,45))]:
            text=self.font.render(name,True,color)
            expected=pygame.Surface(text.get_size());expected.fill((18,28,37));expected.blit(text,(0,0))
            actual=self.screen.subsurface((x,37,*text.get_size()))
            self.assertEqual(pygame.image.tobytes(actual,'RGB'),pygame.image.tobytes(expected,'RGB'),'country names must identify marker colors')

    def test_actual_loop_flips_each_pose_before_consumption_and_closes_while_waiting(self):
        import pygame
        d=pitch()
        for n in range(3):send(d,'frame',sample(n))
        # [designed] Real SDL loop with deterministic due times; close during a long playback wait.
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder);packets=[['owned',0,'start',['First','Second']],['owned',1,'pitch',{'rate':1}]]
            packets += [['owned',n+2,'frame',sample(n)] for n in range(3)]
            (path/'display').write_text(''.join(json.dumps(p)+'\n' for p in packets))
            seen=[];flips=[];states=[];calls=[0];before_flips=[]
            real_render=viewer.render_pitch;real_flip=pygame.display.flip
            def render(*args):
                states[:]=[args[2]];return real_render(*args)
            def flip():
                before_flips.append(states[0].consumed)
                real_flip();flips.append(states[0].frame['sequence'] if states[0].frame else -1)
            def events():
                calls[0]+=1
                return [pygame.event.Event(pygame.QUIT)] if calls[0]==5 else []
            def status(path,value):
                seen.append(value)
                value['test_flip_sequence']=flips[-1]
            with patch.object(sys,'argv',['viewer',folder,'owned']),patch.object(viewer,'render_pitch',render),patch.object(viewer,'status',status),patch('pygame.display.flip',flip),patch('pygame.event.get',events),patch.object(viewer.time,'monotonic',side_effect=[0,1,2,2.1,2.2]):
                self.assertEqual(viewer.main(),0)
            for value in seen:
                self.assertEqual(value['frame_sequence'],value['test_flip_sequence'],'ACK must match actually flipped sample')
            self.assertEqual(seen[0]['frame_sequence'],0,'first flipped sample was not consumed')
            previous=-1
            for seq,before in zip(flips,before_flips):
                if seq!=previous:
                    self.assertEqual(before,previous,'sample acknowledged before SDL flip')
                previous=seq
            self.assertEqual(sorted(set(flips)),[0,1,2])
            self.assertEqual(seen[-1]['kind'],'closed');self.assertEqual(seen[-1]['frame_sequence'],2)


class PitchController(unittest.TestCase):
    def test_bounded_send_does_not_ack_queued_frames_and_validates_consumed_status(self):
        pitch()  # [designed] Before-control asserts feature absence without import ERROR.
        from goal2.desktop.watched import WatchedController
        from goal2.tests.test_pygame_match_view import model
        with tempfile.TemporaryDirectory() as folder:
            m=model(Path(folder)/'save');m.save(m.save_path)
            saved=m.save_path.read_bytes();before=copy.deepcopy(m.state)
            c=WatchedController(m,engine_command=[sys.executable,'-c','import time;time.sleep(60)'],viewer_command=[sys.executable,'-c','import time;time.sleep(60)'])
            try:
                # [designed] Sleep children exercise real ownership/cleanup without original execution.
                c.start();frame=sample()
                initial={'token':c.token,'kind':'ready','sequence':0,'digest':c.digests[0]}
                (c.directory/'status').write_text(json.dumps(initial))
                with patch.object(c.engine,'poll',return_value=[]),patch.object(c.engine,'poll_frames',side_effect=[[frame],[],[],[]]),patch.object(c.engine,'ack_frames') as ack:
                    c.poll();ack.assert_not_called()
                    self.assertEqual(len(c.display.frames),1,'queued frame must remain pending')
                    self.assertTrue(c.busy and m.match_pending)
                    valid=dict(token=c.token,kind='ready',sequence=c.display.sequence,digest=c.display.digest(),frame_sequence=0,frame_digest=viewer.frame_digest(frame))
                    (c.directory/'status').write_text(json.dumps(valid));c.poll()
                    ack.assert_called_once_with(c.engine_token,0)
                    c.poll();ack.assert_called_once()
                    self.assertEqual(len(c.display.frames),0)
                self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
            finally:c.close()
            for bad in (True,-2,1,[],None):
                with self.subTest(ack=bad):
                    c=WatchedController(m,engine_command=[sys.executable,'-c','import time;time.sleep(60)'],viewer_command=[sys.executable,'-c','import time;time.sleep(60)'])
                    try:
                        c.start();child=c.process;engine=c.engine.process
                        status=dict(token=c.token,kind='ready',sequence=c.display.sequence,digest=c.display.digest(),frame_sequence=bad,frame_digest=None)
                        (c.directory/'status').write_text(json.dumps(status))
                        with self.assertRaises(ValueError):c.poll()
                        self.assertFalse(c.busy or m.match_pending)
                        self.assertIsNotNone(child.poll());self.assertIsNotNone(engine.poll())
                        self.assertEqual(m.state,before);self.assertEqual(m.save_path.read_bytes(),saved)
                    finally:c.close()


class SavedByteControls(unittest.TestCase):
    def test_saved_byte_projection_visibility_and_consumption_controls(self):
        import time
        directory=ROOT/'docs/evidence/T83'/f'controls-{time.time_ns()}'
        directory.mkdir(parents=True)
        target=ROOT/'goal2/desktop/pygame_viewer.py';original=target.read_bytes()
        cases=[('axes','CENTER[0] + y * SCALE[0], CENTER[1] + x * SCALE[1]','CENTER[0] + x * SCALE[0], CENTER[1] + y * SCALE[1]','test_independent_axes_team_labels_ball_movement_half_and_rebinding','signed team marker pixels differ'),
               ('player-visibility','            if hidden:\n','            if False:\n','test_field_bounds_visibility_and_unknown_state','sentinel player must be hidden'),
               ('ball-visibility','        if not hidden:\n','        if True:\n','test_field_bounds_visibility_and_unknown_state','sentinel ball must be hidden'),
               ('early-consumption','                pygame.display.flip()','                display.rendered()\n                pygame.display.flip()','test_actual_loop_flips_each_pose_before_consumption_and_closes_while_waiting','sample acknowledged before SDL flip'),
               ('consumption','                display.rendered()','                pass # mutant: no rendered acknowledgement','test_actual_loop_flips_each_pose_before_consumption_and_closes_while_waiting','ACK must match actually flipped sample')]
        receipt=[]
        for name,before,after,test,assertion in cases:
            mutated=original.replace(before.encode(),after.encode());self.assertNotEqual(mutated,original)
            intended=False
            try:
                target.write_bytes(mutated)
                result=subprocess.run([sys.executable,'-B','-m','unittest','goal2.tests.test_pygame_pitch_view.PitchPixels.'+test,'-v'],cwd=ROOT,env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1'),capture_output=True,text=True,timeout=30)
                output=result.stdout+result.stderr;(directory/(name+'.log')).write_text(output)
                self.assertEqual(result.returncode,1,output);self.assertIn('FAIL:',output);self.assertIn(assertion,output);self.assertNotIn('\nERROR:',output)
                intended=True
            finally:
                target.write_bytes(original);self.assertEqual(target.read_bytes(),original)
                receipt.append(dict(name=name,intended_assertion_failed=intended,before=hashlib.sha256(original).hexdigest(),mutated=hashlib.sha256(mutated).hexdigest(),restored=hashlib.sha256(target.read_bytes()).hexdigest()))
                (directory/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n')


if __name__=='__main__':unittest.main()
