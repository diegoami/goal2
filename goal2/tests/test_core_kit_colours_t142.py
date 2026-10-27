"""[derived: T70/0791:1073,0691; designed: owner #412/T142] Original pitch kits."""
import copy
import hashlib
import os
from pathlib import Path
import tempfile
import unittest
from goal2.tests import requires
from goal2.desktop.match_view import Display

COLOURS={'primary':[14,9],'keeper':[12,12]}
def identity(managed=1):
    return dict(countries=['ROMANIA','ITALY'],roles={},managed=managed,kind='Match',colours=copy.deepcopy(COLOURS))

class Protocol(unittest.TestCase):
    def test_optional_colours_are_detached_and_legacy_input_stays_valid(self):
        value=identity();d=Display('kit');d.accept(['kit',0,'start',value])
        self.assertEqual(d.colours,COLOURS)
        value['colours']['primary'][1]=0
        self.assertEqual(d.colours,COLOURS)
        for old in (['one','two'],{k:v for k,v in identity().items() if k!='colours'}):
            legacy=Display('old');legacy.accept(['old',0,'start',old])
            self.assertIsNone(legacy.colours)

    def test_malformed_colour_metadata_is_refused_atomically(self):
        accepted=Display('ok');accepted.accept(['ok',0,'start',identity()])
        self.assertEqual(accepted.colours,COLOURS)
        bad=[None,{}, {'primary':[14,9]}, {'primary':[14,9],'keeper':[12,12],'extra':0}]
        for key in ('primary','keeper'):
            for value in ([True,9],[16,9],[-1,9],[9.0,9],['9',9],[9],(9,9)):
                colours=copy.deepcopy(COLOURS);colours[key]=value;bad.append(colours)
        for colours in bad:
            d=Display('bad');before=d.digest()
            with self.subTest(colours=colours),self.assertRaises(ValueError):
                d.accept(['bad',0,'start',{**identity(),'colours':colours}])
            self.assertEqual((d.sequence,d.countries,d.roles,d.managed,d.colours,d.digest()),(0,None,{},None,None,before))

@requires.need(modules=('unicorn',),files=('e039-r0005-date-call.sav','GOAL.DAT'))
class Genuine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from goal2.desktop.core_model import CoreNewGame
        m,_=CoreNewGame(requires.CACHE/'e039-r0005-date-call.sav',requires.CACHE/'GOAL.DAT',
                       Path(tempfile.gettempdir())/'unused-t142.g2core').start(2028,16,'A Test')
        cls.menu_saved=m.core.save()
        m.driver.round_start(watch=True);m.driver.kick_off(watch=True,speed=0)
        from goal2.core import views
        for _ in range(500):
            frame=views.pitch(m.state,0,0)
            if frame['subtick'] or frame['minute']:break
            with m.core.live_frames():m.driver.live_step()
        else:raise AssertionError('original fixture did not complete a tick')
        cls.saved=m.core.save()

    def core(self):
        from goal2.core import Core
        return Core.load(self.saved,goal_dat=requires.CACHE/'GOAL.DAT')

    def test_fresh_italy_uses_computed_original_blue_without_changing_the_core(self):
        from goal2.core import views
        from goal2.desktop.core_roles import pitch_identity
        c=self.core();before=c.save();mem=views.Memory(c.wait.state)
        raw=views.pitch_identity(c.wait.state);sides=views.match_sides(c.wait.state)
        expected={'primary':[mem.ds_byte(0x832E+t) for t in (0,1)],'keeper':[mem.ds_byte(0x8330+t) for t in (0,1)]}
        self.assertEqual(raw['colours'],expected)
        self.assertEqual(raw['colours']['primary'][sides['teams'].index(16)],9)
        shown=pitch_identity(c.wait.state,raw)
        self.assertEqual(shown['colours'],expected)
        d=Display('genuine');d.accept(['genuine',0,'start',shown]);self.assertEqual(d.colours,expected)
        self.assertEqual(hashlib.sha256(c.save()).hexdigest(),hashlib.sha256(before).hexdigest())

@requires.need(modules=('pygame',))
class Pixels(unittest.TestCase):
    def test_source_kits_and_keepers_ignore_managed_side_without_mutating_frames(self):
        import pygame
        from goal2.desktop import pygame_viewer as viewer
        from goal2.tests.test_pygame_pitch_view import sample,geometry
        pygame.init()
        try:
            screen=pygame.display.set_mode((1440,900));font=pygame.font.Font(None,24)
            # Authored, asymmetric presentation fixture; no original memory is edited.
            frame=sample()
            for slot,point in ((1,(-5,-28)),(2,(-4,-16)),(12,(5,28)),(13,(4,16))):
                frame['players'][slot-1][4:6]=point;frame['players'][slot-1][7]=False
            before=copy.deepcopy(frame)
            cx,cy,sx,sy=geometry((1440,900))
            def count(colour,point):
                x0,y0=round(cx+point[1]*sx),round(cy+point[0]*sy)
                return sum(tuple(screen.get_at((x,y)))[:3]==colour for x in range(x0-18,x0+18) for y in range(y0-18,y0+18))
            for managed in (0,1):
                payload=identity(managed);payload['colours']['keeper']=[10,12]
                d=Display('pixels');d.accept(['pixels',0,'start',payload])
                d.accept(['pixels',1,'pitch',{'rate':60}]);d.accept(['pixels',2,'frame',frame]);d.advance(0)
                viewer.render_pitch(screen,font,d)
                self.assertGreater(count((85,85,255),( -4,-16)),5) # side1/Italy, slot2
                self.assertGreater(count((255,255,85),(4,16)),5)   # side0/Romania, slot13
                self.assertGreater(count((255,85,85),(-5,-28)),5)
                self.assertGreater(count((85,255,85),(5,28)),5)
            self.assertEqual(frame,before)
        finally:pygame.quit()


def native():
    """Actual product Qt window and SDL renderer on an unchanged genuine Italy pose."""
    import argparse,json,subprocess,time
    from goal2.desktop import pygame_viewer as viewer
    from goal2.desktop.core_roles import pitch_identity
    from goal2.core import Core,views
    from goal2.desktop.core_model import CoreModel
    from goal2.desktop.core_window import CoreWindow
    from PySide6.QtWidgets import QApplication
    from PySide6.QtTest import QTest
    import pygame
    parser=argparse.ArgumentParser();parser.add_argument('--native',action='store_true',required=True)
    parser.add_argument('--factor',type=int,choices=(1,2),default=1);parser.add_argument('--out',required=True)
    args=parser.parse_args();folder=Path(args.out);folder.mkdir(parents=True,exist_ok=False)
    os.environ['QT_SCALE_FACTOR']=str(args.factor)
    app=QApplication.instance() or QApplication([])
    assert app.platformName() in ('windows','xcb'),'native Qt platform required'
    requires.require(modules=('unicorn','pygame','PySide6'),files=('e039-r0005-date-call.sav','GOAL.DAT'))
    Genuine.setUpClass()
    core=Core.load(Genuine.saved,goal_dat=requires.CACHE/'GOAL.DAT');before=hashlib.sha256(core.save()).hexdigest()
    menu=Core.load(Genuine.menu_saved,goal_dat=requires.CACHE/'GOAL.DAT')
    window=CoreWindow(CoreModel(menu,requires.CACHE/'GOAL.DAT',folder/'unused.g2core'))
    window.resize(900,640);window.move(0,0);window.show();window.raise_();window.activateWindow();app.processEvents()
    assert QTest.qWaitForWindowActive(window,5000)
    menu_before=hashlib.sha256(menu.save()).hexdigest();window.grab().save(str(folder/'qt-italy.png'))
    raw=pitch_identity(core.wait.state,views.pitch_identity(core.wait.state))
    sides=views.match_sides(core.wait.state);italy=sides['teams'].index(16)
    assert raw['colours']['primary'][italy]==9
    frame=views.pitch(core.wait.state,0,0);frames_before=copy.deepcopy(frame)
    pygame.init()
    try:
        size=(900*args.factor,640*args.factor);screen=pygame.display.set_mode(size)
        assert pygame.display.get_driver() in ('windows','x11','wayland'),'native SDL driver required'
        font=pygame.font.Font(None,24);images=[];pixel_counts=[]
        for managed in (0,1):
            shown={**raw,'managed':managed} # presentation-order control; genuine Core bytes are unchanged
            d=Display('native');d.accept(['native',0,'start',shown]);d.accept(['native',1,'pitch',{'rate':60}])
            d.accept(['native',2,'frame',frame]);d.advance(0)
            # Authored player-hidden projection supplies the real field background for an exact
            # antialiased keeper-glyph oracle; it never edits original Core memory.
            projection=copy.deepcopy(frame)
            from goal2.game.watched_pitch import signed
            off=(signed(frame['sentinel']&255),signed(frame['sentinel']>>8))
            for player in projection['players']:player[4:6]=off;player[7]=True
            backdrop=Display('background');backdrop.accept(['background',0,'start',shown])
            backdrop.accept(['background',1,'pitch',{'rate':60}]);backdrop.accept(['background',2,'frame',projection]);backdrop.advance(0)
            viewer.render_pitch(screen,font,backdrop);background=screen.copy()
            viewer.render_pitch(screen,font,d);pygame.display.flip();app.processEvents()
            field_top=round(size[1]*5/25)
            counts={}
            for index in set(raw['colours']['primary']+raw['colours']['keeper']):
                colour=viewer.DOS_PALETTE[index]
                counts[str(index)]=sum(tuple(screen.get_at((x,y)))[:3]==colour
                    for x in range(size[0]) for y in range(field_top,size[1]-round(size[1]/25)))
            target=folder/f'pitch-managed-{managed}.png';pygame.image.save(screen,str(target))
            assert counts['9']>10
            from goal2.tests.test_pygame_pitch_view import geometry
            cx,cy,sx,sy=geometry(size)
            marker=viewer.mono(max(10,min(round(sy),int(sx/0.6))),True)
            for slot in (1,12):
                player=frame['players'][slot-1];_,team,number,word,px,py,state,hidden=player
                assert not hidden
                point=(round(cx+py*sx),round(cy+px*sy))
                glyph='☻' if frame.get('officials',{}).get('holder')==slot else '☺'
                label=marker.render(glyph,True,viewer.DOS_PALETTE[raw['colours']['keeper'][team]])
                rect=label.get_rect(center=point);expected=background.subsurface(rect).copy();expected.blit(label,(0,0))
                assert pygame.image.tobytes(screen.subsurface(rect),'RGB')==pygame.image.tobytes(expected,'RGB'),f'keeper {slot} bitmap differs'
            images.append(hashlib.sha256(pygame.image.tobytes(screen,'RGB')).hexdigest());pixel_counts.append(counts)
        assert images[0]==images[1],'managed side changed original kits'
        assert frame==frames_before
        assert hashlib.sha256(core.save()).hexdigest()==before
        assert hashlib.sha256(menu.save()).hexdigest()==menu_before
        root=Path(__file__).resolve().parents[2]
        paths=('goal2/core/views.py','goal2/desktop/match_view.py','goal2/desktop/pygame_viewer.py','goal2/tests/test_core_kit_colours_t142.py')
        result=dict(platform=os.sys.platform,qt_platform=app.platformName(),qt_dpr=window.devicePixelRatioF(),
                    sdl_driver=pygame.display.get_driver(),surface_size=list(screen.get_size()),factor=args.factor,
                    countries=raw['countries'],italy_side=italy,colours=raw['colours'],pixel_counts=pixel_counts,
                    same_pixels_both_managed_sides=True,keeper_bitmaps_exact=True,frame_unchanged=True,cores_unchanged=True,
                    head=subprocess.check_output(['git','-c',f'safe.directory={root.as_posix()}','rev-parse','HEAD'],cwd=root,text=True).strip(),
                    source_sha256={p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths},
                    captures={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in folder.glob('*.png')},pass_=True)
        (folder/'receipt.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
    finally:
        pygame.quit();window.close();app.processEvents()

if __name__=='__main__':
    native() if '--native' in os.sys.argv else unittest.main()
