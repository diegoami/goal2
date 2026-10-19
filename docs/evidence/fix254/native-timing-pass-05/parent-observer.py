"""[designed: #254] Actual original Qt/SDL acceptance; observational wrappers only.
The existing original-acceptance helper switches its accepted frames option on.
No status, sharing, renderer output, packet or model behavior is substituted.
"""
from pathlib import Path
import ctypes,json,os,platform,runpy,sys,time,traceback,unittest
from ctypes import wintypes
from PySide6.QtCore import QCoreApplication,QEvent,QTimer,qVersion
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication
out=Path(os.environ['GOAL2_NATIVE_OBSERVATIONS']);out.mkdir(parents=True,exist_ok=False)
callbacks=[]
def callback_error(kind,error,tb):
    callbacks.append(''.join(traceback.format_exception(kind,error,tb)));traceback.print_exception(kind,error,tb)
sys.excepthook=callback_error
# [designed: #254] Fault-injection units are separate from the unmocked actual match path below.
first=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_desktop_watched_sharing'))
assert first.wasSuccessful()and not first.skipped
from goal2.desktop.watched import WatchedController
from goal2.desktop import watched as watched_module
from goal2.desktop.window import ManagementWindow
u=ctypes.WinDLL('user32',use_last_error=True);u.GetWindowRect.argtypes=(wintypes.HWND,ctypes.POINTER(wintypes.RECT));u.GetWindowRect.restype=wintypes.BOOL
controllers=[];windows=[];frames=[];qt_captures=[];complete_acks=[];stderr_links=[];controller_errors=[]
timing={'starts':[],'slow_polls':[],'slow_status_opens':[],'heartbeat_gaps':[],'status_opens':0,'maximum_status_open':0.,'maximum_poll':0.,'maximum_status_read':0.,'maximum_status_close':0.,'slow_status_reads':[],'slow_status_closes':[],'slow_status_exists':[],'missing_status':[],'maximum_status_exists':0.}
status_open=watched_module._open_status
class ObservedStatus:
    def __init__(self,stream):self.stream=stream
    def __enter__(self):self.stream.__enter__();return self
    def __exit__(self,*args):
        began=time.monotonic()
        try:return self.stream.__exit__(*args)
        finally:
            end=time.monotonic();elapsed=end-began;timing['maximum_status_close']=max(timing['maximum_status_close'],elapsed)
            if elapsed>=.02:timing['slow_status_closes'].append({'start':began,'end':end,'seconds':elapsed})
    def read(self,*args):
        began=time.monotonic()
        try:return self.stream.read(*args)
        finally:
            end=time.monotonic();elapsed=end-began;timing['maximum_status_read']=max(timing['maximum_status_read'],elapsed)
            if elapsed>=.02:timing['slow_status_reads'].append({'start':began,'end':end,'seconds':elapsed})
def timed_status_open(path):
    started=time.monotonic()
    try:return ObservedStatus(status_open(path))
    finally:
        finished=time.monotonic();elapsed=finished-started;timing['status_opens']+=1;timing['maximum_status_open']=max(timing['maximum_status_open'],elapsed)
        if elapsed>=.02:timing['slow_status_opens'].append({'start':started,'end':finished,'seconds':elapsed})
watched_module._open_status=timed_status_open

path_exists=Path.exists
def observed_exists(path):
    began=time.monotonic();result=path_exists(path);finished=time.monotonic()
    if path.name=='status'and path.parent.name.startswith('goal2-viewer-'):
        elapsed=finished-began;timing['maximum_status_exists']=max(timing['maximum_status_exists'],elapsed)
        if elapsed>=.02:timing['slow_status_exists'].append({'start':began,'end':finished,'seconds':elapsed,'exists':result})
        if not result:
            row={'start':began,'end':finished,'seconds':elapsed}
            try:
                with status_open(path)as stream:value=json.loads(stream.read(4097))
                row.update(native_readable=True,read_handle_closed=stream.closed,kind=value.get('kind'),sequence=value.get('sequence'),frame_sequence=value.get('frame_sequence'))
            except Exception as error:row.update(native_readable=False,native_error=repr(error),winerror=getattr(error,'winerror',None))
            timing['missing_status'].append(row)
    return result
Path.exists=observed_exists

init=WatchedController.__init__;poll=WatchedController.poll;start=WatchedController.start;close=WatchedController.close_viewer;window_init=ManagementWindow.__init__;run_path=runpy.run_path

def observe_init(self,*a,**kw):
    if kw.get('viewer_command')is None:kw['viewer_command']=[sys.executable,str(Path(__file__).with_name('viewer-observer.py'))]
    init(self,*a,**kw);controllers.append(self);self._native_beats=[]
WatchedController.__init__=observe_init

def observe_window(self,*a,**kw):
    window_init(self,*a,**kw);windows.append(self)
    size=(900,640)if os.environ['QT_SCALE_FACTOR']=='2'else(1050,780)
    self.resize(*size);self.move(20,20)
    timer=QTimer(self);timer.setInterval(5)
    def beat():
        if self.watched.busy:
            now=time.monotonic();beats=self.watched._native_beats
            if beats and now-beats[-1]>=.1:timing['heartbeat_gaps'].append({'start':beats[-1],'end':now,'seconds':now-beats[-1],'frame_ack':self.watched.frame_ack,'sequence':self.watched.display.sequence})
            beats.append(now)
    timer.timeout.connect(beat);timer.start();self._native_heartbeat=timer
ManagementWindow.__init__=observe_window

def observe_start(self,*a,**kw):
    self._native_beats=[time.monotonic()];began=time.monotonic();result=start(self,*a,**kw);timing['starts'].append({'start':began,'end':time.monotonic(),'seconds':time.monotonic()-began})
    number=len(stderr_links)
    for role,handle in(('viewer',self.errors),('engine',self.engine._errors)):
        if handle is not None:
            destination=out/(role+'-stderr-'+str(number)+'.log');os.link(handle.name,destination);stderr_links.append(destination)
    return result
WatchedController.start=observe_start

def capture_qt(window,number):
    assert window.isVisible();app=QApplication.instance();window.raise_();window.activateWindow();app.processEvents()
    file=out/('qt-complete-'+str(number)+'.png');assert window.grab().save(str(file))
    ratio=window.devicePixelRatioF();assert ratio==float(os.environ['QT_SCALE_FACTOR'])
    size=[window.width(),window.height()];assert size==([900,640]if ratio==2 else[1050,780])
    rect=wintypes.RECT();assert u.GetWindowRect(int(window.winId()),ctypes.byref(rect))
    qt_captures.append({'file':file.name,'ratio':ratio,'logical_size':size,'qt_available':[window.screen().availableGeometry().width(),window.screen().availableGeometry().height()],'native_rect':[rect.left,rect.top,rect.right,rect.bottom],'active':window.isActiveWindow()})

def observe_poll(self):
    began=time.monotonic()
    try:result=poll(self)
    except Exception as error:
        controller_errors.append({'error':repr(error),'traceback':traceback.format_exc()})
        (out/'controller-errors.json').write_text(json.dumps(controller_errors,indent=2)+'\n')
        print('NATIVE REAL CONTROLLER ERROR',traceback.format_exc(),flush=True)
        raise
    finished=time.monotonic();elapsed=finished-began;timing['maximum_poll']=max(timing['maximum_poll'],elapsed)
    if elapsed>=.05:timing['slow_polls'].append({'start':began,'end':finished,'seconds':elapsed,'busy':self.busy,'frame_ack':self.frame_ack,'sequence':self.display.sequence if self.display else None})
    if result:
        assert self.frames_enabled and self.display.frame_sequence>=1000
        assert self.frame_ack==self.display.frame_sequence and not self.display.frames
        assert self.last_status['frame_sequence']==self.frame_ack
        beats=[*self._native_beats,time.monotonic()];gap=max((b-a for a,b in zip(beats,beats[1:])),default=0)
        frames.append({'frames':self.display.frame_sequence+1,'final_ack':self.frame_ack,'frame_digest':self.last_status['frame_digest'],'heartbeats':len(beats),'maximum_heartbeat_gap':gap})
        print('PASS actual publication after final rendered-frame ACK',json.dumps(frames[-1]),flush=True)
        for w in windows:
            if w.model is self.model:QTimer.singleShot(0,lambda w=w,n=len(frames):capture_qt(w,n))
    return result
WatchedController.poll=observe_poll

def observe_close(self):
    # [designed: #254; confirmed: T79 concrete preflight] Final frame precedes complete-board ACK.
    if self.process is not None and self.process.poll()is None and not self.engine.busy and self.display is not None and self.display.result is not None:
        deadline=time.monotonic()+30
        while self.last_status is None or self.last_status['sequence']!=self.display.sequence or self.last_status['digest']!=self.display.digest():
            assert time.monotonic()<deadline,'complete-board ACK deadline'
            QApplication.instance().processEvents();QTest.qWait(10);poll(self)
        complete_acks.append({'sequence':self.last_status['sequence'],'digest':self.last_status['digest']})
    return close(self)
WatchedController.close_viewer=observe_close

def animated(path,*a,**kw):
    if Path(path).resolve()==Path('tools/desktop-ui/watched.py').resolve():
        text=Path(path).read_text();old='original_start(frames=False,**kw)';assert text.count(old)==1
        namespace={'__name__':'<main-owned animated acceptance>','__file__':str(Path(path).resolve())}
        exec(compile(text.replace(old,'original_start(frames=True,**kw)'),str(path),'exec'),namespace);return namespace
    return run_path(path,*a,**kw)
runpy.run_path=animated
before=list(sys.path)
second=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromName('goal2.tests.test_pygame_match_view.OriginalQtAcceptance'))
app=QApplication.instance();assert app is not None
QCoreApplication.sendPostedEvents(None,QEvent.Type.DeferredDelete);app.processEvents()
sdl=[json.loads(p.read_text())for p in out.glob('goal2-viewer-*.json')]
clean=all(c.process is None and c.folder is None and c.directory is None and c.stream is None and c.errors is None and not c.engine.busy and not c._pending_owned for c in controllers)
report={'claim':'[designed: #254] Actual Qt/SDL original parity/save/resume acceptance; mode frames=True and capture/ACK observation only; preceding fault-injection units separate','result':'PASS','platform':platform.platform(),'python':sys.version,'qt':qVersion(),'qpa':app.platformName(),'requested_qt_scale':os.environ['QT_SCALE_FACTOR'],'actual_qt_ratio':app.primaryScreen().devicePixelRatio(),'controller_errors':controller_errors,'frames':frames,'complete_acks':complete_acks,'qt_captures':qt_captures,'sdl':sdl,'deterministic_tests':first.testsRun,'original_acceptance_tests':second.testsRun,'callbacks':callbacks,'owned_resources_closed':clean,'clean_widgets':not app.topLevelWidgets(),'import_context_restored':sys.path==before}
checks=[second.wasSuccessful()and not second.skipped,len(frames)==2,len(complete_acks)==2,len(qt_captures)==2,not callbacks,clean,not app.topLevelWidgets(),sys.path==before,all(x['maximum_heartbeat_gap']<1 and x['heartbeats']>5 for x in frames),len([x for x in sdl if x['stage']=='complete'])==2,all(x['driver']=='windows'for x in sdl)]
if not all(checks):report['result']='FAIL';report['checks']=checks
report['native_timing']=timing;(out/'timing.json').write_text(json.dumps(timing,indent=2)+'\n')
(out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report),flush=True);assert all(checks),'native actual-match acceptance failed'
