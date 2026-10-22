"""[designed: T83; restyled T94] Real SDL pixel/causal playback and saved-byte controls."""
import copy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from goal2.desktop.match_view import Display
from goal2.desktop import pygame_viewer as viewer
from goal2.tests import requires

ROOT = Path(__file__).resolve().parents[2]


def sample(sequence=0, watermark=0):
    # [designed] Asymmetric synthetic oracle derived independently from T81 raw signed contract.
    return dict(version=1, sequence=sequence, watermark=watermark, minute=7+sequence,
        score=[1,0], subtick=36, threshold=45, remaining=91, selector=1,
        attack=[1,-1], sentinel=11, ball=[-4,13,False],
        players=[[s, int(s<=11), s if s<=11 else s-11, 100+s,
                  11,0,13,True] for s in range(1,23)])


def pitch(identity=None):
    d=Display('owned')
    d.accept(['owned',0,'start',identity or ['First','Second']])
    # [designed] Assertion provides a behavioral before-failure rather than import ERROR.
    assert callable(getattr(viewer,'render_pitch',None)), 'numbered pitch renderer missing'
    d.accept(['owned',1,'pitch',{'rate':60}])
    return d


def send(d,kind,value):d.accept(['owned',d.sequence,kind,value])


# [designed: T94] The accepted palette, restated here rather than read from the viewer.
GOLD,WHITE,GREY,YELLOW,CYAN=(255,187,51),(238,238,238),(170,170,170),(255,255,85),(85,255,255)
IDENTITY={'countries':['First','Second'],'roles':{'101':'B','122':'w'},'managed':0,'kind':'Friendly'}


def geometry(size):
    """[derived: F013 IN_PLAY |x|<=8, |y|<=37; designed: T94 52 px header, 64 px footer, 8 px
    sides, 1.5/2.5 grid units of margin] Restated independently of pygame_viewer.layout."""
    w,h=size[0]-16,size[1]-52-64
    return 8+w/2,52+h/2,w/79,h/19


@requires.need(modules=("pygame",))
class PitchPixels(unittest.TestCase):
    SIZE=(1440,900)

    def setUp(self):
        import pygame
        pygame.init()
        self.screen=pygame.display.set_mode(self.SIZE)
        self.font=pygame.font.Font(None,24)

    def tearDown(self):
        import pygame
        pygame.quit()

    def pixel(self,x,y):return tuple(self.screen.get_at((round(x),round(y))))[:3]

    def point(self,x,y):
        cx,cy,sx,sy=geometry(self.SIZE);x=max(-9.5,min(9.5,x));y=max(-39.5,min(39.5,y))
        return round(cx+y*sx),round(cy+x*sy)

    def count(self,colour,centre,radius=18):
        x0,y0=centre
        width,height=self.SIZE
        return sum(self.pixel(x,y)==colour for x in range(max(0,x0-radius),min(width,x0+radius)) for y in range(max(0,y0-radius),min(height,y0+radius)))

    def glyph(self,text,colour,centre):
        """The exact pixels of a marker label as the viewer's font draws it on black."""
        import pygame
        cx,cy,sx,sy=geometry(self.SIZE)
        # [designed: T96] One glyph per grid cell: 0.6 em advance within a column, the row's height.
        font=viewer.mono(max(10,min(round(sy),int(sx/0.6))),True)
        label=font.render(text,True,colour);rect=label.get_rect(center=centre)
        expected=pygame.Surface(label.get_size());expected.fill((0,0,0));expected.blit(label,(0,0))
        return pygame.image.tobytes(self.screen.subsurface(rect),'RGB'),pygame.image.tobytes(expected,'RGB')

    def test_independent_axes_role_codes_ball_movement_half_and_rebinding(self):
        import pygame
        d=pitch(IDENTITY);f=sample()
        # Slot 2 (outfield; slots 1 and 12 are keepers, always ☺ [confirmed: 0791:0691]).
        f['players'][1]=[2,1,2,101,-3,-21,0,False]
        f['players'][21]=[22,0,11,122,5,25,13,False]
        for n in range(2,21):f['players'][n][7]=True
        f['players'][0][7]=True
        send(d,'frame',f);self.assertTrue(d.advance(0));viewer.render_pitch(self.screen,self.font,d)
        pygame.display.flip();d.rendered()
        # [derived: T81] Signed [y,x], positive right/down: (-3,-21) is up and left of the centre.
        cx,cy,_,_=geometry(self.SIZE);left,right=self.point(-3,-21),self.point(5,25)
        self.assertTrue(left[0]<cx<right[0] and left[1]<cy<right[1])
        # The managed side (team 0) is gold, the other white; each marker is its role code.
        actual,expected=self.glyph('B',WHITE,left);self.assertEqual(actual,expected,'signed team marker pixels differ')
        actual,expected=self.glyph('w',GOLD,right);self.assertEqual(actual,expected,'signed team marker pixels differ')
        self.assertGreater(self.count(YELLOW,self.point(-4,13),6),0,'signed ball pixels differ')
        old=pygame.image.tobytes(self.screen,'RGB')
        g=copy.deepcopy(f);g.update(sequence=1,minute=46,remaining=45,selector=0,attack=[-1,1])
        g['players'][1][3]=777;g['players'][1][4:6]=[-2,-20];g['ball']=[-3,14,False]
        send(d,'frame',g);self.assertFalse(d.advance(.001));self.assertEqual(d.consumed,0)
        self.assertTrue(d.advance(1));viewer.render_pitch(self.screen,self.font,d);pygame.display.flip();d.rendered()
        self.assertNotEqual(pygame.image.tobytes(self.screen,'RGB'),old)
        # A rebound word without a role shows its slot number; no rotation or interpolation.
        actual,expected=self.glyph('2',WHITE,self.point(-2,-20));self.assertEqual(actual,expected,'half/rebind must not rotate or interpolate')
        self.assertEqual(d.frame['players'][1][3],777);self.assertEqual(d.consumed,1)

    def test_field_bounds_visibility_and_unknown_state(self):
        d=pitch(IDENTITY);f=sample();f['ball']=[11,0,True]
        send(d,'frame',f);d.advance(0);viewer.render_pitch(self.screen,self.font,d)
        top_left,bottom_right=self.point(-8,-37),self.point(8,37)
        self.assertEqual(self.pixel(top_left[0],(top_left[1]+bottom_right[1])/2),GREY,'left playing-grid boundary')
        self.assertEqual(self.pixel(bottom_right[0],top_left[1]+40),GREY,'right playing-grid boundary')
        self.assertEqual(self.pixel(top_left[0]+60,top_left[1]),GREY,'top playing-grid boundary')
        self.assertEqual(self.pixel(top_left[0]+60,bottom_right[1]),GREY,'bottom playing-grid boundary')
        # Every sample player is the sentinel (hidden) and the ball is hidden.
        self.assertEqual(self.count(GOLD,self.point(11,0))+self.count(WHITE,self.point(11,0)),0,'sentinel player must be hidden')
        self.assertEqual(self.count(YELLOW,self.point(11,0),8),0,'sentinel ball must be hidden')
        g=copy.deepcopy(f);g['sequence']=1;g['players'][21][4:8]=[11,1,255,False];g['ball']=[10,2,False]
        send(d,'frame',g);d.advance(1);viewer.render_pitch(self.screen,self.font,d)
        self.assertGreater(self.count(GOLD,self.point(11,1)),0,'non-sentinel out-of-field/unknown state must draw')
        self.assertGreater(self.count(YELLOW,self.point(10,2),8),0,'non-sentinel ball must draw')

    def test_two_latest_commentary_lines_full_panel_watermark_and_bounded_queue(self):
        import pygame
        d=pitch(IDENTITY)
        for minute,text in [(0,'Kickoff'),(3,'Corner'),(5,'Shot'),(90,'FULL TIME')]:
            send(d,'event',dict(kind='commentary',minute=minute,score=[0,0],data={'text':text}))
        send(d,'event',dict(kind='end',minute=90,score=[1,0],data={}))
        f=sample(watermark=3);send(d,'frame',f)
        self.assertEqual(d.visible().events,[],'ingress must not leak before first pose')
        d.advance(0)
        visible=d.visible().commentary()
        self.assertEqual(visible,['0′ Kickoff','3′ Corner','5′ Shot'])
        self.assertNotIn('90′ FULL TIME',visible,'future commentary leaked before watermark')
        viewer.render_pitch(self.screen,self.font,d)
        self.assertEqual(d.consumed,-1,'selection/queueing must not acknowledge an unseen frame')
        footer=viewer.mono(22)
        def drawn(line,colour,y):
            label=footer.render(line,True,colour);expected=pygame.Surface(label.get_size());expected.fill((0,0,0));expected.blit(label,(0,0))
            return pygame.image.tobytes(self.screen.subsurface((18,y,*label.get_size())),'RGB')==pygame.image.tobytes(expected,'RGB')
        bottom=self.SIZE[1]-64+6
        self.assertTrue(drawn('3′ Corner',YELLOW,bottom) and drawn('5′ Shot',CYAN,bottom+28),'the latest two lines are shown')
        self.assertFalse(drawn('0′ Kickoff',YELLOW,bottom),'older commentary is hidden by default')
        header=viewer.mono(30,True).render('   7′ / FRIENDLY',True,CYAN)
        self.assertGreater(sum(self.pixel(x,24)==CYAN for x in range(18,900)),0,'minute/score header')
        before=pygame.image.tobytes(self.screen,'RGB')
        viewer.render_pitch(self.screen,self.font,d,0,True)
        self.assertNotEqual(pygame.image.tobytes(self.screen,'RGB'),before,'C opens the full commentary')
        pygame.display.flip();d.rendered();self.assertEqual(d.consumed,0)
        send(d,'complete',{'board':{'statistics':{},'bars':[]},'ratings':[[],[]],'man_of_the_match':'A'})
        self.assertIn('90′ FULL TIME',d.visible().commentary());self.assertEqual(d.frame['sequence'],0)
        other=pitch()
        for n in range(64):send(other,'frame',sample(n))
        with self.assertRaisesRegex(ValueError,'backlog'):send(other,'frame',sample(64))
        self.assertEqual(len(other.frames),64)

    def test_accumulated_target_cadence_and_managed_side_colours(self):
        d=pitch(dict(IDENTITY,managed=1))
        for n in range(5):send(d,'frame',sample(n))
        self.assertTrue(d.advance(0))
        # [designed] Small scheduler lateness must not reset the target and halve playback rate.
        for instant in (.018,.034,.051,.068):
            self.assertTrue(d.advance(instant),'deadline drift reduced the fixed playback target')
        d.frame['players'][1][3]=101
        d.frame['players'][1][7]=False;d.frame['players'][21][7]=False
        d.frame['players'][1][4:6]=[-4,-20];d.frame['players'][21][4:6]=[4,20]
        viewer.render_pitch(self.screen,self.font,d)
        # Managed side 1: team 1 gold, team 0 white; the header names carry the same colours.
        self.assertEqual(*self.glyph('B',GOLD,self.point(-4,-20)),'country names must identify marker colors')
        self.assertEqual(*self.glyph('w',WHITE,self.point(4,20)),'country names must identify marker colors')
        self.assertGreater(sum(self.pixel(x,y)==WHITE for x in range(18,200) for y in range(14,40)),0,'first country in its colour')

    def test_the_pitch_fills_the_window_at_every_size(self):
        for size in ((900,640),(1440,900),(2880,1800)):
            (left,top,w,h),(sx,sy)=viewer.layout(*size)
            self.assertGreaterEqual(w*h/(size[0]*size[1]),.75 if size[0]>=1440 else .7,size)
            self.assertTrue(0<=left and left+w<=size[0] and 0<=top and top+h<=size[1])
            self.assertGreater(sx*37,w*.4);self.assertGreater(sy*8,h*.35)

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


@requires.need(modules=("pygame",))
class ControllerClose(unittest.TestCase):
    def test_close_outlasts_a_cancel_that_times_out_while_the_job_prepares(self):
        """[designed: #311; #254] One cancel is bounded and may time out while the job still
        encodes its input (seen on the Windows runner). close() is final: it cancels again until
        the job is reaped, within CLOSE_DEADLINE, and raises only past it."""
        from goal2.desktop import watched
        from goal2.tests.test_pygame_match_view import model
        with tempfile.TemporaryDirectory() as folder:
            m = model(Path(folder) / 'save')
            for timeouts, deadline, closes in ((2, 30, True), (10**6, 0.2, False)):
                with self.subTest(timeouts=timeouts):
                    c = watched.WatchedController(m, engine_command=[sys.executable, '-c', 'import time;time.sleep(60)'],
                                                  viewer_command=[sys.executable, '-c', 'import time;time.sleep(60)'])
                    c.start();real = c.engine.cancel;calls = [0]
                    def cancel(token):
                        calls[0] += 1
                        if calls[0] <= timeouts:
                            raise subprocess.TimeoutExpired('watched input preparation', 0.5)
                        return real(token)
                    with patch.object(c.engine, 'cancel', cancel), patch.object(watched, 'CLOSE_DEADLINE', deadline):
                        if closes:
                            c.close()
                        else:
                            with self.assertRaises(subprocess.TimeoutExpired):
                                c.close()
                    if not closes:
                        c.close()
                    self.assertFalse(c.engine.busy or m.match_pending)
                    if closes:
                        self.assertEqual(calls[0], 3)


class ControllerCancel(unittest.TestCase):
    def test_cancel_ends_a_match_whose_input_is_still_encoding(self):
        """[designed: #311] On the loaded Windows runner the input encoding outlasted one engine
        cancel (0.5 s, #254), so a protocol error raised TimeoutExpired instead of its own error.
        The controller's cancel reaps the job: here the encoding is slowed to 1.5 s."""
        from goal2.desktop.watched import WatchedController
        from goal2.game import watched_jobs
        from goal2.tests.test_pygame_match_view import model
        real = watched_jobs.encode
        def slow(*args, **kwargs):
            time.sleep(1.5);return real(*args, **kwargs)
        with tempfile.TemporaryDirectory() as folder, patch.object(watched_jobs, 'encode', slow):
            m = model(Path(folder) / 'save')
            c = WatchedController(m, engine_command=[sys.executable, '-c', 'import time;time.sleep(60)'],
                                  viewer_command=[sys.executable, '-c', 'import time;time.sleep(60)'])
            try:
                c.start();c.cancel()
                self.assertFalse(c.engine.busy or m.match_pending)
            finally:
                c.close()


class SavedByteControls(unittest.TestCase):
    def test_saved_byte_projection_visibility_and_consumption_controls(self):
        import time
        # [designed: #275] Receipts go to the git-ignored cache, never into tracked docs/evidence.
        directory=ROOT/'.cache/test-receipts/T83'/f'controls-{time.time_ns()}'
        directory.mkdir(parents=True)
        target=ROOT/'goal2/desktop/pygame_viewer.py';original=target.read_bytes()
        cases=[('axes','        return round(cx + gy * sx), round(cy + gx * sy)','        return round(cx + gx * sx), round(cy + gy * sy)','test_independent_axes_role_codes_ball_movement_half_and_rebinding','signed team marker pixels differ'),
               ('player-visibility','            if not hidden:\n                occupied','            if True:\n                occupied','test_field_bounds_visibility_and_unknown_state','sentinel player must be hidden'),
               ('ball-visibility','        if not hidden and at(bx, by) not in occupied:\n','        if True:\n','test_field_bounds_visibility_and_unknown_state','sentinel ball must be hidden'),
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
