"""[designed: #236] Fixed-source original Qt acceptance with animated mode/capture only."""
from pathlib import Path
import json,os,platform,runpy,sys,traceback,unittest
from PySide6.QtCore import QCoreApplication,QEvent,QTimer,qVersion
from PySide6.QtWidgets import QApplication
out=Path(os.environ['GOAL2_NATIVE_OBSERVATIONS']);out.mkdir(parents=True,exist_ok=False)
callbacks=[];original_hook=sys.excepthook

def callback_error(kind,error,tb):
    callbacks.append(''.join(traceback.format_exception(kind,error,tb)));traceback.print_exception(kind,error,tb)
sys.excepthook=callback_error
# Real Windows runs the deterministic suite without runtime sharing mocks.
first=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_desktop_watched_sharing'))
assert first.wasSuccessful(),'deterministic Windows sharing suite failed'
from goal2.desktop.watched import WatchedController
from goal2.desktop.window import ManagementWindow
controllers=[];frames=[];windows=[];qt_captures=[];original_init=WatchedController.__init__;original_poll=WatchedController.poll;original_run_path=runpy.run_path;original_window_init=ManagementWindow.__init__

def window_init(self,*args,**kwargs):
    original_window_init(self,*args,**kwargs);windows.append(self)
ManagementWindow.__init__=window_init

def controller_init(self,*args,**kwargs):
    if kwargs.get('viewer_command')is None:kwargs['viewer_command']=[sys.executable,str(Path(__file__).with_name('viewer-observer.py'))]
    original_init(self,*args,**kwargs);controllers.append(self)
WatchedController.__init__=controller_init

original_cancel=WatchedController.cancel;cancel_count=[0]
def observe_cancel(self,*args,**kwargs):
    cancel_count[0]+=1
    if self.errors is not None:
        try:
            raw=Path(self.errors.name).read_bytes();(out/('viewer-stderr-'+str(cancel_count[0])+'.log')).write_bytes(raw)
            if raw:print('NATIVE OWNED VIEWER STDERR BEFORE CLEANUP',raw.decode(errors='replace'),flush=True)
        except OSError as exc:print('NATIVE observational stderr read',repr(exc),flush=True)
    return original_cancel(self,*args,**kwargs)
WatchedController.cancel=observe_cancel

def capture_qt(window,number):
    assert window.isVisible()
    file=out/('qt-complete-'+str(number)+'.png');assert window.grab().save(str(file))
    ratio=window.devicePixelRatioF();assert ratio==float(os.environ['QT_SCALE_FACTOR'])
    qt_captures.append({'file':file.name,'ratio':ratio,'logical_size':[window.width(),window.height()]})

def poll(self):
    result=original_poll(self)
    if result:
        assert self.frames_enabled and self.display.frame_sequence>=1000
        assert self.frame_ack==self.display.frame_sequence and not self.display.frames
        assert self.last_status['frame_sequence']==self.frame_ack
        frames.append({'frames':self.display.frame_sequence+1,'final_ack':self.frame_ack,'frame_digest':self.last_status['frame_digest']})
        print('PASS actual fixed-source publication after final rendered-frame ack',json.dumps(frames[-1]),flush=True)
        for window in windows:
            if window.model is self.model:QTimer.singleShot(0,lambda w=window,n=len(frames):capture_qt(w,n))
    return result
WatchedController.poll=poll

def animated(path,*args,**kwargs):
    if Path(path).resolve()==Path('tools/desktop-ui/watched.py').resolve():
        text=Path(path).read_text();old='original_start(frames=False,**kw)';assert text.count(old)==1
        namespace={'__name__':'<main-owned animated acceptance>','__file__':str(Path(path).resolve())}
        exec(compile(text.replace(old,'original_start(frames=True,**kw)'),str(path),'exec'),namespace);return namespace
    return original_run_path(path,*args,**kwargs)
runpy.run_path=animated
before=list(sys.path)
second=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_pygame_match_view.OriginalQtAcceptance'))
assert second.wasSuccessful()and len(frames)==2
assert sys.path==before,'#234 acceptance import context leaked'
app=QApplication.instance();assert app is not None
QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
ratio=app.primaryScreen().devicePixelRatio();assert ratio==float(os.environ['QT_SCALE_FACTOR'])
assert not callbacks,callbacks
assert len(qt_captures)==2,qt_captures
assert controllers and all(c.process is None and c.folder is None and c.directory is None and c.stream is None and c.errors is None and not c.engine.busy and not c._pending_owned for c in controllers),'owned viewer resources retained after successful close'
assert not app.topLevelWidgets(),'owned Qt widgets remain after deferred cleanup'
sdl=[json.loads(p.read_text())for p in out.glob('goal2-viewer-*.json')];assert len([r for r in sdl if r['stage']=='complete'])==2 and all(r['driver']=='windows'for r in sdl)
report={'result':'PASS','platform':platform.platform(),'python':sys.version,'qt':qVersion(),'qpa':app.platformName(),'actual_qt_ratio':ratio,'requested_qt_scale':os.environ['QT_SCALE_FACTOR'],'frames':frames,'qt_captures':qt_captures,'deterministic_tests':first.testsRun,'original_acceptance_tests':second.testsRun,'callbacks':callbacks,'owned_resources_closed':True,'clean_widgets':True,'sdl':sdl,'claim':'Actual fixed-source Qt/SDL; only original acceptance mode frames=True and observational captures added; production status read/write/cleanup untouched'}
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report));sys.excepthook=original_hook
